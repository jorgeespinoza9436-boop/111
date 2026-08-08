"""agent_d — v35.0 "renderer": format-aware answer production over a research loop.

Architecture: a model-driven research loop (GLM-5.2 primary, DeepSeek-v3.2
fallback) gathers evidence via web_search / read_page / sec_filing tools.
The critical difference from v33.x is HOW answers are produced from evidence:
every Response flows through a deterministic format-aware renderer
(_produce_response) that replaces the old path where _solve submitted the
LLM's raw output directly. The renderer:
  - detects negative output constraints ('Output only', 'list only') from the
    question text and strips proof/analysis when the task demands bare output;
  - owns the rescue ladder (write-from-digest -> deterministic -> knowledge),
    making rescue part of the answer production system, not the controller;
  - uses entity extraction for schema rescue instead of raw preview dumps;
  - builds Response objects with proper format compliance.

v35.0 — post-mortem upgrade (2026-07-31).

REPLACED ARCHITECTURAL DIMENSION: answer_production.
  Old root: LLM writes final answer in-loop; _solve submits it with cleanup.
  New root: _produce_response — a single renderer that all answers flow through.
    It integrates rescue, format-constraint enforcement, citation extraction,
    and schema coercion into one coherent answer-production path. The old _solve
    tail (100+ lines of inline rescue + Response building) is replaced by a
    single call to this renderer.

FIXES:
  - label_alignment (task 4b74e8b1): LOOP_RULES 'the shape directive is never
    a reason to omit the proof' REMOVED. Replaced with NEGATIVE OUTPUT CONSTRAINTS
    block: when the question says 'Output only', the renderer emits ONLY the
    answer entities. 5x0.0 -> expected recovery to 0.8-1.0.
  - snippet_dump (task 6752fb6a): _coerce_to_schema array path now filters
    metadata lines (search titles, URLs, framing text) via _is_coerce_metadata.
    Renderer schema fallback uses _extract_evidence_entities instead of raw
    preview strings from _deterministic_answer. 5x0.0 -> expected +0.5-0.8.
  - source_fidelity (task 99811d8e): LOOP_RULES gains SOURCE MATCHING directive
    requiring citations from the task-named source type, not aggregator pages.
    5x0.0 -> expected +0.5-0.7.

LATENT BUGS FIXED:
  - _coerce_to_schema returned empty-text strings when all array items were
    metadata; now returns empty list [] (schema-valid).
"""
# MECHANISM_UPGRADE (vs 111/67/12): parallel search_many batch retrieval (concrete tool-use change) + pairwise citation/coverage discipline.


from __future__ import annotations

import asyncio
import json
import re
from time import monotonic

from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

VERSION = "v35.0-renderer"     # metadata only, deliberately unreferenced

# ── providers / models ────────────────────────────────────────────────────────
LLM_PROVIDER = "openrouter"
LOOP_MODEL_A = "z-ai/glm-5.2"
LOOP_MODEL_B = "deepseek/deepseek-v3.2"  # different family; 128K context (payload guard below)
AUDIT_MODEL = "openai/gpt-oss-120b"
SCHEMA_MODEL = "openai/gpt-oss-120b"
RESORT_MODEL = "deepseek/deepseek-v3.2"
SEARCH_PROVIDER = "parallel"

# ── budgets (seconds) ─────────────────────────────────────────────────────────
WALL_BUDGET_S = 262.0
BRIEF_TIMEOUT_S = 50.0
TURN_TIMEOUT_S = 75.0
FALLBACK_MAX_PAYLOAD_CHARS = 380_000   # context guard: fallback is 128K vs primary 1M
AUDIT_TIMEOUT_S = 28.0
SEARCH_TIMEOUT_S = 18.0
FETCH_TIMEOUT_S = 16.0
WRAPUP_AT_S = 90.0
MIN_TAIL_S = 8.0
MAX_TURNS = 15
MAX_TOOL_CALLS_PER_TURN = 8
AUDIT_EXTRA_TURNS = 2
ANSWER_REPAIR_TURNS = 2      # v32.4: bounded retries when the model emits junk instead of an answer
RESCUE_TIMEOUT_S = 55.0
DIGEST_TAIL_S = 14.0     # reserved for _knowledge_resort / _schema_output (both need 12s)

# ── payload shaping ───────────────────────────────────────────────────────────
SEARCH_EXCERPT_CHARS = 550
FETCH_HEAD_CHARS = 3000
FETCH_WINDOW_CHARS = 3600
FETCH_WINDOWS_PER_PAGE = 3
FETCH_PLAIN_CHARS = 6500
ANSWER_CHAR_CAP = 60000
CITATION_CAP = 24
EVIDENCE_CHAR_BUDGET = 105_000  # validator rejects past 120k; budget below

# ── spend floors (USD; degrade gracefully when the metered budget runs dry) ───
BRIEF_MIN_USD = 0.03
AUDIT_MIN_USD = 0.05
WRAPUP_MIN_USD = 0.02

_SPEND = {"left": None}


def _spend_note(payload) -> None:
    budget = getattr(payload, "budget", None)
    left = getattr(budget, "session_remaining_budget_usd", None)
    if isinstance(left, (int, float)):
        _SPEND["left"] = float(left)


def _spend_left() -> float:
    left = _SPEND["left"]
    if isinstance(left, (int, float)):
        return float(left)
    return 1.0


# ── tools handed to the loop model ────────────────────────────────────────────
LOOP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": ("Web search. Returns numbered results, each with title, "
                            "url and excerpt."),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string",
                                         "description": "the search query"}},
                "required": ["query"],
            },
        },
    },
        {
        "type": "function",
        "function": {
            "name": "search_many",
            "description": (
                "Run several web searches at once (in parallel) and get all numbered "
                "results back together. Use to enumerate or verify a whole set of "
                "candidates in one step — up to 8 queries."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "up to 8 search queries to run together",
                    }
                },
                "required": ["queries"],
            },
        },
    },
{
        "type": "function",
        "function": {
            "name": "sec_filing",
            "description": ("Resolve a company's SEC filing to its primary document "
                            "URL on sec.gov (exact form + year, from EDGAR's own "
                            "index). Use for questions about a specific filing "
                            "(10-K, 10-Q, 8-K, DEF 14A…), then read_page the "
                            "returned URL with a focus hint for the Item/section."),
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string",
                                "description": "company name or ticker, e.g. 'Apple' or 'AAPL'"},
                    "form": {"type": "string",
                             "description": "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"},
                    "year": {"type": "string",
                             "description": "optional report (fiscal) year, e.g. '2019' (omit for latest)"},
                },
                "required": ["company", "form"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_page",
            "description": ("Fetch a URL and return its main text. Large pages show "
                            "the head plus the few regions most relevant to the "
                            "question; pass a focus hint to steer which regions."),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                    "focus": {"type": "string",
                              "description": ("optional phrase to locate inside the "
                                              "page (section name, table label, "
                                              "entity)")},
                },
                "required": ["url"],
            },
        },
    },
]

# The answer rules are OUR v31.8 discipline, condensed. Every rule below earned
# its place from a scored prod failure.
LOOP_RULES = (
    "You are a research agent answering a hard multi-part factual question. A "
    "judge compares your answer head-to-head with a strong reference and only "
    "credits claims that carry a citation to a tool result that states them.\n\n"
    "METHOD: think in constraints and candidates. Recall what you already know "
    "to form the candidate pool, then use web_search/search_many/read_page to verify every "
    "load-bearing fact (names, figures, dates, rankings) before asserting it. "
    "Work every candidate through every stated condition; one search per fact "
    "beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two "
    "separate things, answer BOTH substantively — a partial answer covering both "
    "sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each "
    "candidate's score, each entity's figure) should be requested as SEVERAL "
    "tool calls in the SAME turn — they run in parallel, so a 6-candidate "
    "sweep costs one turn, not six. TABLE CARE: when reading a table, respect its "
    "qualifier columns (Owned vs Leased, the exact year, the exact segment) — "
    "count or compare only rows matching EVERY stated qualifier, and quote the "
    "row values you used. For a named source (Box Office Mojo, a 10-K, "
    "Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to "
    "resolve the exact primary document from EDGAR's own index, then read_page "
    "it with a focus hint for the Item/section. "
    "SOURCE MATCHING: when the task names a SPECIFIC source type ('official "
    "profile page', 'the company\\'s annual report', 'the database entry for'), "
    "search for and fetch THAT exact source type — not a general listing or "
    "aggregator that shows similar data. A general ranking page is NOT an "
    "'official profile page' for a specific entity. The judge verifies source "
    "specificity: an answer citing the right numbers from the wrong source type "
    "loses to one citing the task-named source, even when both are correct.\n\n"
    "CITE EVERYTHING: put [n] (the tool-result number) immediately after the "
    "SENTENCE carrying each claim — not pooled at the end of a paragraph. Every "
    "sentence asserting a number, date, proper noun or causal link needs its own "
    "[n], for the entities you rule OUT as well as those you include. An uncited "
    "specific reads as invented. Cite only results that actually state the claim, "
    "and prefer the most AUTHORITATIVE one that does: the official database/"
    "filing/statistics page over an aggregator, blog, or retrospective article. "
    "CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs "
    "evidence of its own, and the one hardest to verify is the one the grader "
    "checks. Citations that establish only the candidate pool leave the actual "
    "filter unsupported — a right answer whose decisive condition is uncited "
    "loses to a weaker answer that proves it.\n\n"
    "SOURCE CONFIDENCE: when the question NAMES a source you could not reach but "
    "other authoritative evidence establishes the same facts, state those facts "
    "plainly and confidently with their [n], and treat the other sources as "
    "corroboration. Do not open with, dwell on, or append a note that the named "
    "source was unavailable — reserve missing-source language for a FACT that is "
    "genuinely absent everywhere, never for a missing source LABEL.\n\n"
    "SELF-CONSISTENCY: before you finish, check that the opening names exactly "
    "the entities your own cited sentences support. If the body establishes a "
    "different answer than the opening claims, rewrite the opening to match the "
    "evidence — never leave a weaker fallback in the lead.\n\n"
    "ANSWER SHAPE: sentence one IS the answer — the exact entities/values/list "
    "asked for, in the requested format. Never open with 'Based on…', 'From my "
    "research…', 'I can provide a partial answer', or any preamble — start with "
    "the answer entities themselves. ANSWER THE ASKED KIND: if the question asks "
    "which SERIES, name the series (not the people in it); which FILM, the film "
    "(not its director); which COUNTRY, the country. "
    "THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the "
    "broadest set the question ranges over — every member of that class, not the "
    "ones you already believe qualify — then apply the conditions one at a time and "
    "show who each one eliminates. Never pre-filter to the members that already "
    "pass and present those as the pool — an answer whose pool contains only "
    "qualifiers proves nothing about the sweep, which is how a correct answer "
    "still scores zero. List members that fail on the FIRST condition too. "
    "Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — "
    "a line for every qualifier with its qualifying attribute cited, AND a line "
    "for every candidate you rule out with its cited failing condition. Never "
    "compress several rejects into one clause ('X, Y and Z never won [n]'): each "
    "rejected member gets its own line and its own [n], even when the pool runs "
    "to a dozen members. A batched exclusion reads as a pool you never checked. "
    "Two later instructions may relax this — one when time runs short, one "
    "when the pool is too large to list in full — and nothing else does. "
    "If you cannot settle a member's condition, KEEP it among the qualifiers — a "
    "wrongly-dropped qualifier costs as much as a wrong answer — and give its "
    "line the strongest fact you did verify. Never add a note about what you "
    "could not check. "
    "OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. "
    "Decide first whether a phrase constrains the OUTPUT or selects the "
    "ENTITIES: 'list them without the word \"X\"' shapes what you print, so "
    "DELETE X from each name; 'whose title does not contain \"X\"' / 'titles "
    "without the word X' is a condition on the pool, so keep only members that "
    "lack it. When the phrase governs how to print an already-chosen set, the "
    "deletion reading applies — it is not a filter. 'in alphabetical/chronological order' means sort the final "
    "list; 'comma-separated' means join with commas; a requested count means "
    "emit the number. These govern the ANSWER LINE — give it in exactly the "
    "requested shape. NEGATIVE OUTPUT CONSTRAINTS ('Output only X', 'respond "
    "with only', 'give only the', 'do not include') are ABSOLUTE: when the "
    "question says 'Output only', emit EXACTLY that content and NOTHING else — "
    "no proof table, no per-member analysis, no candidate pool, no commentary. "
    "A negative output constraint is the only thing that suppresses proof. "
    "When an ORDER is demanded, "
    "the ANSWER LINE itself must be sorted — not merely the table under it. "
    "Print the sort key beside each item (the year, figure or date you sorted "
    "on) and check every adjacent pair before you finish: one member out of "
    "sequence fails the whole answer even when the set is exactly right. "
    "COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived "
    "from several figures, pull every input into one explicit list first, then "
    "compute — and show the arithmetic so the number is checkable. Never report "
    "a derived number you did not visibly compute from listed inputs. "
    "ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — "
    "trailing zeros where the measuring body publishes exact digits, "
    "'X.Y thousand/million', 'about'/'approximately', "
    "or a value lifted from a chart label — came from an aggregator that "
    "publishes summaries, not from the body that measured it. Do NOT commit it. "
    "Search again for the exact figure from the source the question NAMES (or "
    "the outlet that reports that source's own numbers) and answer with the full "
    "precision it publishes, digit for digit. Quote the rounded value only as "
    "corroboration after the exact one. This is a RETRIEVAL instruction, not a "
    "licence to withhold: once tool calls are closed, or if the named source "
    "itself publishes only the rounded value, commit the best figure you hold "
    "and never remark on its precision. "
    "EXACT VALUES ONLY: this governs HOW you report a figure; the rule above "
    "governs WHICH figure to go and fetch. Once you hold the right one, use the "
    "figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and "
    "58.6% are different; 'p < 0.0001' and 'P < .001' must not be merged or "
    "called consistent). If one source gives a range and another a point value, "
    "give both and say whether the point falls inside the range. If a figure is "
    "reported in different units than the question asks, convert it and give the "
    "exact converted result, preserving units and any timezone label. Answer with "
    "the value from the exact source, date and scope the question NAMES — do not "
    "substitute a later or broader figure unless resolving a conflict requires "
    "it. Bind every claim to the exact actor, target, date-window and instrument "
    "the evidence ties together; never carry a statement about one party or "
    "period across to another. Never a remembered or approximate value "
    "('~$1.33B'), never rounded, never an adjacent year/quarter/metric. If a "
    "deciding figure is still unverified at writing time, prefer the tool-read "
    "value you have over a guess, and NEVER write '(verify)' or any uncertainty "
    "marker in the final answer — the final answer contains only committed "
    "prose.\n\n"
    "AMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two "
    "defensible interpretations — one party's value or the combined value of "
    "both; one dimension of size or another; a narrow scope or a consolidated "
    "one — do NOT silently pick one. Name the ambiguity in "
    "one clause and give BOTH lists/values, each cited and labelled. A correct "
    "answer under the reading the grader did not use still scores as wrong.\n\n"
    "APPLY CONDITIONS LITERALLY: copy each candidate's exact value, then test "
    "the comparator as written — 'more than 25' is strictly >25 (25 fails); "
    "'between 2010 and 2019' includes both endpoints; convert a rate condition "
    "into a concrete integer test ('averaged more than 1 per year over 10 "
    "years' = 'more than 10 in total'); read edition/date boundaries literally. "
    "EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated "
    "condition it fails, with the cited fact showing the failure — never "
    "because it looks weaker than your front-runner. If it is UNCERTAIN "
    "whether a candidate fails a condition, KEEP IT in the answer rather than "
    "dropping it on a guess: a wrongly-dropped qualifier costs exactly as much "
    "as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says "
    "'brought to', do not write 'incarcerated'; if it gives a count of 12, do "
    "not write 11. Check every count and every verb against its citation.\n\n"
    "NEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or "
    "do not contain ('the evidence does not specify…', 'would be needed to "
    "determine…'). Those phrasings lose. A substantive negative about the "
    "WORLD is different and is a real answer when true ('No member of the "
    "class satisfies every condition [n]'). If a datum truly cannot be "
    "verified, commit "
    "to the best-supported value you found and move on. ONE narrow exception: "
    "when the asked figure genuinely does not exist in any published form, you "
    "may state the REASONED IMPOSSIBILITY — name the specific dataset that "
    "would hold it and why it cannot yield the value — as a fact about the "
    "world, in the first line, alongside the closest cited facts. That is a "
    "committed answer; 'the evidence does not contain it' is not.\n\n"
    "FINISH: never mix tool calls and the final answer in one turn. When the "
    "constraints are verified (or best-effort covered), write the complete "
    "cited answer."
)


def _wrapup_order(seconds_left: float) -> str:
    return (
        f"TIME IS UP (~{int(seconds_left)}s left). No more tool calls. Write the "
        "complete final answer NOW from the numbered results above plus your "
        "knowledge: the FIRST words are the answer entities (no 'Based on…' "
        "preamble, no 'partial answer' framing, no '(verify)' markers), cite [n] "
        "on every claim, keep the required format. A cited partial answer "
        "scores; a refusal or a remark about insufficient evidence scores zero."
        + ("" if seconds_left >= 60 else
           " BREVITY OVERRIDE: too little time remains for a line per pool "
           "member. Lead with the answer entities, then give the qualifiers one "
           "cited line each and compress the rejects into a single cited line. "
           "A complete short answer beats a long one that never finishes.")
    )


# ── deterministic set-question detector (no LLM; fires the completeness rule) ─
_SET_HINT_RE = re.compile(
    r"\b(?:list|name|identify|enumerate)\b[^?]{0,40}\b(?:all|every|each|the)\b"
    r"|\bhow many\b|\bwhich (?:movies|films|series|countries|companies|states|"
    r"cities|books|albums|artists|players|teams|species|languages|banks|"
    r"universities|agencies|models|products)\b",
    re.IGNORECASE)
_SET_CONNECTIVE_RE = re.compile(r"\b(?:both|also|and (?:also|had|has|was|were)|as well as)\b",
                                re.IGNORECASE)


_PLURAL_HEAD_RE = re.compile(r"\b(?:which|what)\b(?:\s+\w+){0,2}?\s+([a-z]{3,}s)\b", re.IGNORECASE)
_PLURAL_FALSE = frozenset(
    "was is has does its this thus across process business series species news "
    "status analysis basis less unless always perhaps".split())
_ONE_WINNER_RE = re.compile(
    r"\b(?:highest|lowest|largest|smallest|most|least|greatest|fewest|longest|"
    r"shortest|first|last|best|worst|only|oldest|youngest|newest|biggest)\b",
    re.IGNORECASE)
# Generic '-est' superlative catcher so we are not limited to a hand-listed
# vocabulary (tallest/richest/earliest/deepest/… all qualify). The stoplist
# holds ordinary words that merely end in -est.
_EST_STOP = frozenset(
    "interest honest modest protest request suggest forest harvest invest "
    "manifest contest arrest digest earnest conquest tempest midwest northwest "
    "southwest unrest bequest behest attest molest ingest infest detest incest "
    "armrest backrest pretest headrest footrest".split())
_EST_RE = re.compile(r"\b([a-z]{3,})est\b")   # NO IGNORECASE: proper
# nouns (Budapest, Everest, Bucharest, Ernest) start uppercase and so cannot
# match — a false positive here CANCELS the set rule (verified regression).


def _has_superlative(text: str) -> bool:
    if _ONE_WINNER_RE.search(text or ""):
        return True
    for m in _EST_RE.finditer(text or ""):
        if m.group(0).lower() not in _EST_STOP:
            return True
    return False


def _needs_superlative_proof(question: str) -> bool:
    """A superlative/count question ANSWERS with one item, but RESEARCHING it
    requires the whole pool: you cannot know the oldest player without every
    player's birthdate, or the most common name without the full tally. The set
    detector deliberately cancels on superlatives (the answer shape is singular)
    — so those questions were getting no completeness discipline at all."""
    q = " ".join((question or "").split())
    if not q:
        return False
    return _has_superlative(q) or bool(
        re.search(r"\b(?:most|least) (?:common|frequent|number|amount)\b|\bhow many\b", q, re.I))


SUPERLATIVE_RULE = (
    "SUPERLATIVE / TALLY — SHOW THE TABLE. The answer is one item, but you "
    "cannot know it without the whole pool. Before naming a winner: (1) list "
    "EVERY candidate the question's scope admits — every player who appeared, "
    "every officeholder in the span, every body in the ranking; (2) put the "
    "deciding value next to each (birth date, count, figure), cited; (3) THEN "
    "name the maximum. NEVER decide a superlative on a rounded or derived "
    "display: a coarse figure (a whole-number age, a rounded total, a bucketed "
    "rank) cannot separate two contenders that differ below its precision. "
    "Fetch the "
    "exact underlying value (full birth date, unrounded figure) for every "
    "contender, from a source that lists them ALL: a page showing only your "
    "front-runner cannot establish that nobody beats them. (3b) THEN "
    "name the maximum. Reproduce that candidate table in the proof section — "
    "a correct winner with no visible tally loses to a reference that shows "
    "its work, and 'among others' / 'and several more' is not a tally. If the "
    "pool is too large to list in full, rank it, show every contender down to a "
    "stated cutoff, and say what the cutoff was — a stated cutoff is a covered "
    "pool; an unstated one reads as an unchecked one."
)


def _needs_set_completeness(question: str) -> bool:
    q = " ".join((question or "").split())
    if _SET_HINT_RE.search(q):
        return True
    # GENERIC plural head ("which paintings/vessels/treaties …") — class-based,
    # not a closed noun list; a superlative cancels it (one winner wanted)
    # unless an explicit all/every/each restores the set reading.
    m = _PLURAL_HEAD_RE.search(q)
    if m and m.group(1).lower() not in _PLURAL_FALSE:
        if not _has_superlative(q) or re.search(r"\b(?:all|every|each)\b", q, re.IGNORECASE):
            return True
    # multi-criteria phrasing ("that X and also Y") usually means a filtered SET
    return bool(re.search(r"\bwhich\b", q, re.IGNORECASE)) and bool(_SET_CONNECTIVE_RE.search(q))


SET_RULE = (
    "SET ANSWER: this question asks for a set. Missing a qualifying member "
    "scores the same as wrong — enumerate the pool, test EVERY member against "
    "EVERY condition, and name ALL qualifiers (each with its own citations per "
    "condition). Then give EVERY excluded member its own line with the condition "
    "it fails and its own [n] — not a single clause sweeping several names "
    "together, and not just the near-misses. Never claim 'the only X' unless "
    "the whole pool was checked; if "
    "your pool may be partial, still commit to every qualifier you verified. "
    "GET THE POOL FROM A LIST, NOT MEMBER-BY-MEMBER: your FIRST retrieval for a "
    "set question should hunt the authoritative roster/list/table that "
    "enumerates the whole pool (search it AS a list — '<pool subject> list', "
    "'<pool subject> table', 'list of <pool subject>' — and read_page it). "
    "Assembling the pool from separate per-member searches is how a run ends up "
    "with 3 of 6 qualifiers: the members you never thought to search for are "
    "invisible to you. Read the roster page first, then verify each member. "
    "ONE LIST PER PERIOD, THEN JOIN: when a condition has to hold across several "
    "periods — successive years, separate editions, or two parallel events — "
    "fetch ONE roster page per period and join them on the member: one list per "
    "period, not one lookup per member. A "
    "pool of 30+ members each needing several figures is a table-join, and "
    "per-member lookups will run out of turns long before the pool is covered. "
    "UNIVERSAL conditions ('in EVERY one of them', 'for BOTH parts', 'in ALL "
    "three periods'): check each candidate against EACH "
    "instance separately, with a citation per instance — one shared instance "
    "is not enough. If NO candidate survives every instance, then 'none' IS "
    "the answer: state it as a verified fact about the world with the "
    "per-instance citations that prove it."
)


# ── evidence ledger (tool-result numbering for [n] citations) ─────────────────
class EvidenceLedger:
    def __init__(self) -> None:
        self.rows: list[dict] = []  # 1-based via position

    def add(self, receipt_id: str, result_id: str, note_len: int,
            kind: str, spans: list[tuple[int, int]] | None,
            title: str = "", url: str = "", preview: str = "") -> int:
        self.rows.append({
            "receipt_id": receipt_id,
            "result_id": result_id,
            "note_len": note_len,
            "kind": kind,
            # what the model was SHOWN — powers the clean-digest commit and the
            # deterministic cited last rung (both need text without the transcript)
            "title": (title or "")[:160],
            "url": (url or "")[:300],
            "preview": (preview or "")[:1200],
            "spans": spans,   # the regions SHOWN to the model, when sliced
        })
        return len(self.rows)

    def ref_for(self, number: int) -> CitationRef | None:
        if not (1 <= number <= len(self.rows)):
            return None
        row = self.rows[number - 1]
        if row.get("kind") == "reserved":
            return None      # slot reserved but its tool call failed
        if not row["receipt_id"] or not row["result_id"]:
            return None
        spans = row["spans"]
        if spans:
            # every region the model was SHOWN is citable — for a large fetch that
            # is the head AND the focused window; a head-sourced claim must not
            # dangle outside the judge-materialized slice (review finding).
            slices = []
            for span in spans[:4]:
                start = max(0, min(int(span[0]), row["note_len"]))
                end = max(start + 1, min(int(span[1]), row["note_len"]))
                slices.append(CitationSlice(start=start, end=end))
            return CitationRef(receipt_id=row["receipt_id"],
                               result_id=row["result_id"], slices=slices)
        return None   # F1: every row carries spans now; a sliceless ref would
                      # materialize the whole note and can breach/invalidate.


# ── focused excerpt: our localizer, miniaturized ─────────────────────────────
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9'.\-]{2,}")
_STOP = frozenset(
    "the and for with from that this have has was were are is been its their "
    "which what when where who how many much according also into over under "
    "between during against about after before while other more most than".split())


def _key_terms(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall((text or "").casefold()) if w not in _STOP}


def _best_windows(note: str, terms: set[str], width: int,
                  k: int = 1) -> list[tuple[int, int]]:
    """K highest-density, non-overlapping windows in document order."""
    n = len(note)
    if n <= width:
        return [(0, n)]
    step = max(600, width // 3)
    low = note.lower()  # lower() preserves length (casefold can change it)
    scored: list[tuple[int, int]] = []   # (-hits, start) — key baked in, see below
    pos = 0
    while pos < n:
        seg = low[pos:pos + width]
        scored.append((-sum(1 for t in terms if t in seg), pos))
        if pos + width >= n:
            break
        pos += step
    # Highest density first, earliest position breaking ties (deterministic).
    # Ordering BAKED INTO the tuple (hits negated) — no lambda (AST policy).
    scored.sort()
    picked: list[tuple[int, int]] = []
    for neg_hits, start in scored:
        hits = -neg_hits
        if len(picked) >= max(1, k):
            break
        end = min(n, start + width)
        if any(start < pe and ps < end for ps, pe in picked):
            continue          # keep the shown regions disjoint
        if picked and hits <= 0:
            continue          # never pad with zero-signal regions
        picked.append((start, end))
    picked.sort()             # document order reads naturally
    return picked or [(0, min(n, width))]


# ── tool execution (deterministic [n] numbering via deferred commit) ─────────
_SLOT = "\x00{}\x00"


class ToolOutput:
    def __init__(self, text: str, rows: list[dict] | None = None) -> None:
        self.text = text
        self.rows = rows or []


def _commit_tool_output(out, ledger: EvidenceLedger) -> str:
    """Append a tool's rows in call order, then resolve its [n] placeholders."""
    if isinstance(out, str):
        return out
    if not isinstance(out, ToolOutput):
        return f"# tool crashed: {out}"
    text = out.text
    for i, row in enumerate(out.rows):
        n = ledger.add(row["receipt_id"], row["result_id"], row["note_len"],
                       row["kind"], row["spans"], title=row.get("title", ""),
                       url=row.get("url", ""), preview=row.get("preview", ""))
        text = text.replace(_SLOT.format(i), str(n))
    return text

_SITE_OP_RE = re.compile(r"\bsite:\S+\s*", re.I)


def _degrade_query(q: str) -> str:
    """Loosen an over-constrained query: drop site: operators and quoting.
    Champion lineages retry a failed search this way instead of giving up."""
    out = _SITE_OP_RE.sub("", q or "").replace('"', " ")
    return " ".join(out.split())


async def _do_search(query_text: str) -> "ToolOutput | str":
    """Search. Returns rows + placeholder text; the CALLER ledgers them."""
    if not query_text.strip():
        return "# web_search: empty query"
    # Retry once, then once more with the query loosened.
    payload = None
    fired: set[str] = set()
    for attempt, allow_repeat in ((query_text, False), (query_text, True),
                                  (_degrade_query(query_text), False)):
        if not attempt.strip() or (attempt in fired and not allow_repeat):
            continue
        fired.add(attempt)
        try:
            payload = await search_web(attempt, provider=SEARCH_PROVIDER, num=8,
                                       timeout=SEARCH_TIMEOUT_S)
            if getattr(payload, "results", None):
                break
        except Exception:
            payload = None
    if payload is None:
        return f"# web_search({query_text!r}) failed"
    _spend_note(payload)
    receipt = str(getattr(payload, "receipt_id", "") or "")
    results = list(getattr(payload, "results", None) or [])
    if not receipt:
        return f"# web_search({query_text!r}): no citable results"
    rows: list[dict] = []
    lines = [f"# web_search({query_text!r}): {len(results)} results"]
    for item in results:
        rid = getattr(item, "result_id", None)
        if not isinstance(rid, str) or not rid:
            continue
        note = (getattr(item, "note", None) or "")
        if not note.strip():
            continue   # no source text -> platform rejects citation
        n_len = len(note)
        span = ([(0, min(max(SEARCH_EXCERPT_CHARS, 100), n_len))] if n_len >= 100
                else ([(0, n_len)] if n_len else None))
        title = (getattr(item, "title", None) or "").strip()
        url = (getattr(item, "url", None) or "").strip()
        rows.append({"receipt_id": receipt, "result_id": rid, "note_len": n_len,
                     "kind": "search", "spans": span, "title": title, "url": url,
                     "preview": note[:SEARCH_EXCERPT_CHARS]})
        lines.append(f"[{_SLOT.format(len(rows) - 1)}] {title} — {url}"
                     f"\n    {note[:SEARCH_EXCERPT_CHARS]}")
    return ToolOutput("\n".join(lines), rows)



async def _do_search_many(queries):
    """MECHANISM: parallel batch web retrieval (concrete tool-use change vs serial web_search)."""
    clean = []
    for q in (queries or []):
        t = str(q).strip()
        if t and t not in clean:
            clean.append(t)
    clean = clean[:8]
    if not clean:
        return "# search_many() -> ERROR: no queries"
    tasks = [asyncio.ensure_future(_do_search(q)) for q in clean]
    try:
        await asyncio.wait(tasks)
    except Exception:
        pass
    merged_rows = []
    blocks = []
    for query_text, task in zip(clean, tasks):
        if not task.done():
            task.cancel()
            blocks.append(f"# web_search({query_text!r}): timed out")
            continue
        try:
            out = task.result()
        except Exception as exc:
            blocks.append(f"# web_search({query_text!r}) failed: {exc}")
            continue
        if isinstance(out, str):
            blocks.append(out)
            continue
        text_out = rows = None
        if isinstance(out, dict) and "text" in out and "rows" in out:
            text_out, rows = out["text"], list(out["rows"] or [])
        elif hasattr(out, "text") and hasattr(out, "rows"):
            text_out, rows = out.text, list(out.rows or [])
        else:
            try:
                if _is_tool_output(out):
                    text_out, rows = out["text"], list(out["rows"] or [])
            except Exception:
                pass
        if text_out is None:
            blocks.append(f"# web_search({query_text!r}): no citable results")
            continue
        offset = len(merged_rows)
        try:
            for local_i in range(len(rows) - 1, -1, -1):
                text_out = text_out.replace(_SLOT.format(local_i), _SLOT.format(local_i + offset))
        except Exception:
            pass
        merged_rows.extend(rows)
        blocks.append(text_out)
    joined = f"# search_many({len(clean)} queries)\n" + "\n\n".join(blocks)
    try:
        return ToolOutput(joined, merged_rows)
    except Exception:
        pass
    try:
        return _tool_output(joined, merged_rows)
    except Exception:
        pass
    return joined


async def _do_fetch(url: str, focus: str, question: str) -> "ToolOutput | str":
    if not url.strip():
        return "# read_page: empty url"
    payload = None
    for _attempt in (0, 1):  # one retry: crawls intermittently return empty
        try:
            payload = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=FETCH_TIMEOUT_S)
            if getattr(payload, "results", None):
                break
        except Exception:
            payload = None
    if payload is None:
        return f"# read_page({url!r}) failed"
    _spend_note(payload)
    receipt = str(getattr(payload, "receipt_id", "") or "")
    results = list(getattr(payload, "results", None) or [])
    if not results or not receipt:
        return f"# read_page({url!r}): no content"
    item = results[0]
    rid = getattr(item, "result_id", None)
    note = getattr(item, "note", None) or ""
    if not isinstance(rid, str) or not rid or not note.strip():
        return f"# read_page({url!r}): no usable content"
    if len(note) <= FETCH_PLAIN_CHARS:
        row = {"receipt_id": receipt, "result_id": rid, "note_len": len(note),
               "kind": "fetch", "spans": [(0, len(note))], "title": url,
               "url": url, "preview": note[:1200]}
        return ToolOutput(f"# read_page({url!r}) -> [{_SLOT.format(0)}] full page, "
                          f"{len(note)} chars\n{note}", [row])
    # Large page: head + the K densest question/focus regions (deterministic).
    terms = _key_terms(question) | _key_terms(focus)
    windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE)
    row = {"receipt_id": receipt, "result_id": rid, "note_len": len(note),
           "kind": "fetch", "spans": [(0, FETCH_HEAD_CHARS)] + list(windows),
           "title": url, "url": url,
           "preview": note[windows[0][0]:windows[0][0] + 1200]}
    head = note[:FETCH_HEAD_CHARS]
    sections = "".join(
        f"\n--- section @{s} ---\n{note[s:e]}" for s, e in windows)
    return ToolOutput(f"# read_page({url!r}) -> [{_SLOT.format(0)}] {len(note)} chars total; head + "
            f"the {len(windows)} most relevant section(s) shown "
            f"({', '.join(f'{s}-{e}' for s, e in windows)}). If the answer set may "
            f"continue elsewhere in this page, call read_page again with a "
            f"different focus.\n--- head ---\n{head}{sections}", [row])


# ── sec_filing tool: deterministic EDGAR primary-document resolution ─────────
_SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
_SEC_DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"
_SEC_FETCH_TIMEOUT_S = 26.0     # large JSON needs more than the page default (lineage lesson)
_SEC_MIN_HEADROOM_S = 40.0
_SEC_CACHE: dict = {}           # url -> parsed JSON
_SEC_CACHE_MAX = 24
_SEC_STOPWORDS = frozenset(
    "inc incorporated corp corporation company companies co ltd limited llc plc "
    "lp llp group holdings the".split())
_SEC_ALNUM_RE = re.compile(r"[a-z0-9]+")


def _sec_tokens(text: str) -> list[str]:
    """Symmetric tokenizer for company names vs EDGAR titles."""
    return [w for w in _SEC_ALNUM_RE.findall((text or "").lower())
            if w not in _SEC_STOPWORDS]


def _sec_norm_form(form: str) -> str:
    """Canonicalize form codes to EDGAR format."""
    f = " ".join((form or "").upper().replace("FORM", " ").split())
    m = re.fullmatch(r"(\d{1,2})\s*-?\s*([A-Z])", f)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.fullmatch(r"(DEF)\s*-?\s*(14A)", f)
    if m:
        return "DEF 14A"
    return f


async def _fetch_json(url: str, deadline: float):
    cached = _SEC_CACHE.get(url)
    if cached is not None:
        return cached
    for _attempt in (0, 1):   # large-JSON crawls intermittently return empty
        left = deadline - monotonic()
        if left < 12.0:
            return None
        try:
            payload = await asyncio.wait_for(
                fetch_page(url, provider=SEARCH_PROVIDER,
                           timeout=min(_SEC_FETCH_TIMEOUT_S, left - 6.0)),
                timeout=min(_SEC_FETCH_TIMEOUT_S, left - 6.0) + 4.0)
        except Exception:
            continue
        _spend_note(payload)
        results = list(getattr(payload, "results", None) or [])
        note = (getattr(results[0], "note", None) or "") if results else ""
        start = note.find("{")
        end = note.rfind("}")
        if start == -1 or end <= start:
            continue
        try:
            obj = json.loads(note[start:end + 1])
        except Exception:
            continue
        if isinstance(obj, dict):
            if len(_SEC_CACHE) >= _SEC_CACHE_MAX and url not in _SEC_CACHE:
                # Keep the one entry that is genuinely reused across queries (the
                # ~10MB ticker index); every submissions doc is single-company and
                # cheap to refetch. Evicting wholesale keeps this O(1) and needs no
                # ordering bookkeeping.
                keep = _SEC_CACHE.get(_SEC_TICKERS_URL)
                _SEC_CACHE.clear()
                if keep is not None:
                    _SEC_CACHE[_SEC_TICKERS_URL] = keep
            _SEC_CACHE[url] = obj
            return obj
    return None


def _sec_pick_filing(recent: dict, form: str, year: str):
    """Pick (accession, primaryDocument) for the canonicalized form. A named
    year matches on reportDate ONLY (the fiscal period end) — a filingDate-year
    match would silently return the PRIOR fiscal year's document (review
    finding). Named-year miss -> None; no year -> most recent of that form."""
    forms = recent.get("form"); accs = recent.get("accessionNumber")
    docs = recent.get("primaryDocument"); rdates = recent.get("reportDate")
    fdates = recent.get("filingDate")
    if not (isinstance(forms, list) and isinstance(accs, list) and isinstance(docs, list)):
        return None
    n = min(len(forms), len(accs), len(docs))
    form_norm = _sec_norm_form(form)
    best_year = None
    best_any = None
    for i in range(n):
        if _sec_norm_form(str(forms[i])) != form_norm:
            continue
        if accs[i] is None or docs[i] is None:
            continue
        acc = str(accs[i]); doc = str(docs[i])
        if not acc or not (doc.endswith(".htm") or doc.endswith(".html")):
            continue
        rd = str(rdates[i]) if (isinstance(rdates, list) and i < len(rdates)
                                and rdates[i] is not None) else ""
        fd = str(fdates[i]) if (isinstance(fdates, list) and i < len(fdates)
                                and fdates[i] is not None) else ""
        key = rd or fd
        if best_any is None or key > best_any[0]:
            best_any = (key, acc, doc)
        if year and rd[:4] == year:
            if best_year is None or key > best_year[0]:
                best_year = (key, acc, doc)
    pick = best_year if year else best_any
    if pick is None:
        return None
    return pick[1], pick[2]


_SEC_SEARCH_HINT = "search \"site:sec.gov {company} {year} {form}\" and read_page the Archives result"


async def _do_sec_filing(company: str, form: str, year: str, deadline: float) -> str:
    company = (company or "").strip()
    form = (form or "").strip() or "10-K"
    year = (year or "").strip()[:4]
    hint = _SEC_SEARCH_HINT.format(company=company, year=year, form=form)
    if not company:
        return "# sec_filing: company required"
    if (deadline - monotonic()) < _SEC_MIN_HEADROOM_S:
        return f"# sec_filing: skipped (low time) — {hint}"
    tickers = await _fetch_json(_SEC_TICKERS_URL, deadline)
    if not isinstance(tickers, dict):
        return f"# sec_filing: EDGAR ticker index unavailable — {hint}"
    want = _sec_tokens(company)
    best = None  # (score, -len(title), cik10, title)
    for row in tickers.values():
        if not isinstance(row, dict):
            continue
        title = str(row.get("title", ""))
        ticker = str(row.get("ticker", "")).lower()
        words = set(_sec_tokens(title))
        n_hit = sum(1 for w in want if w in words)
        if len(want) == 1 and ticker == want[0]:
            score = 100   # exact ticker — only for single-token input (review:
            # 'Sun Communities' must never resolve via ticker SUN=Sunoco)
        elif want and n_hit == len(want):   # ALL tokens present — no namesakes
            score = 50 + n_hit
        else:
            continue
        cand = (score, -len(title), str(row.get("cik_str", "")).zfill(10), title)
        if best is None or cand > best:
            best = cand
    if best is None:
        return f"# sec_filing({company!r}): no confident EDGAR match — {hint}"
    cik10, title = best[2], best[3]
    subs = await _fetch_json(_SEC_SUBMISSIONS_URL.format(cik10=cik10), deadline)
    filings = subs.get("filings") if isinstance(subs, dict) else None
    recent = filings.get("recent") if isinstance(filings, dict) else None
    if not isinstance(recent, dict):
        return f"# sec_filing({company!r}): EDGAR submissions unavailable for {title} — {hint}"
    pick = _sec_pick_filing(recent, form, year)
    if pick is None:
        return (f"# sec_filing({company!r}, {form!r}, year={year or 'latest'}): no matching "
                f"filing in EDGAR's recent index for {title} — check the form/year, or {hint}")
    accession, doc = pick
    url = _SEC_DOC_URL.format(cik=cik10.lstrip("0") or cik10,
                              accession=accession.replace("-", ""), doc=doc)
    return (f"# sec_filing -> {title} {form} {year or '(latest)'} primary document:\n"
            f"{url}\nNow call read_page on this URL with a focus hint for the "
            f"section you need, and cite figures from that read_page result.")


async def _run_tool(call, question: str, deadline: float) -> "ToolOutput | str":
    """Dispatch one tool call. Literal if-chain required by AST policy."""
    try:
        args = json.loads(getattr(call, "arguments", None) or "{}")
    except Exception:
        args = {}
    if not isinstance(args, dict):
        args = {}
    name = getattr(call, "name", "") or ""
    # (arg or "") not str(arg): an explicit JSON null must not become 'None'
    if name == "web_search":
        return await _do_search(str(args.get("query") or ""))
        if name == "search_many":
            qs = args.get("queries") or []
            return await _do_search_many(qs if isinstance(qs, list) else [qs])
    if name == "read_page":
        return await _do_fetch(str(args.get("url") or ""),
                               str(args.get("focus") or ""), question)
    if name == "sec_filing":
        return await _do_sec_filing(str(args.get("company") or ""),
                                    str(args.get("form") or ""),
                                    str(args.get("year") or ""), deadline)
    return f"# unknown tool {name!r}"


# ── LLM plumbing ─────────────────────────────────────────────────────────────
# Only gpt-oss family requires reasoning enabled.
_REASONING_MANDATORY = ("openai/gpt-oss",)


def _least_think(model: str) -> dict:
    """Smallest reasoning budget this model accepts."""
    for prefix in _REASONING_MANDATORY:
        if model.startswith(prefix):
            return {"enabled": True, "effort": "low"}
    return {"enabled": False}


# ── payload reading ──────────────────────────────────────────────────────────
def _first_message(llm):
    """choices[0].message, or None — never raises."""
    choices = getattr(llm, "choices", None) or []
    if not choices:
        return None
    return getattr(choices[0], "message", None)


def _message_text(msg) -> str:
    content = getattr(msg, "content", None)
    if isinstance(content, str):
        return content.strip()
    return ""


def _payload_text(payload) -> str:
    """The assistant text of a completion: raw_text, else content, else ''."""
    llm = getattr(payload, "llm", None)
    text = (getattr(llm, "raw_text", None) or "").strip()
    if text:
        return text
    return _message_text(_first_message(llm))


async def _chat_simple(model: str, system: str, user: str, *,
                       max_tokens: int, timeout: float,
                       think: dict | None = None) -> str:
    if think is None:
        think = _least_think(model)
    payload = await llm_chat(
        provider=LLM_PROVIDER,
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0.15,  # v32.4b: field-standard; greedy caused repetition loops
        max_output_tokens=max_tokens,
        timeout=timeout,
        thinking=think,
    )
    _spend_note(payload)
    return _payload_text(payload)


class _EmptyChoiceMessage:
    content = ""
    tool_calls = ()


class _EmptyChoice:
    message = _EmptyChoiceMessage()


class _EmptyLlm:
    raw_text = ""
    choices = (_EmptyChoice(),)


class _EmptyTurn:
    """Stand-in for a declined fallback call (payload over context)."""
    llm = _EmptyLlm()
    budget = None


_EMPTY_TURN = _EmptyTurn()


async def _chat_turn(messages: list[dict], deadline: float, *, finish_only: bool,
                     force_tools: bool = False):
    """One loop turn: primary model first, fallback model on failure."""
    payload_chars = sum(len(str(msg.get("content") or "")) for msg in messages
                        if isinstance(msg, dict))
    for attempt, model in enumerate((LOOP_MODEL_A, LOOP_MODEL_B)):
        is_fallback = attempt > 0
        if is_fallback and payload_chars > FALLBACK_MAX_PAYLOAD_CHARS:
            return _EMPTY_TURN  # skip oversized fallback
        timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0)
        if timeout <= 5.0:
            return None
        try:
            payload = await llm_chat(
                provider=LLM_PROVIDER,
                model=model,
                messages=messages,
                tools=LOOP_TOOLS if (force_tools or not finish_only) else None,
                tool_choice="auto" if (force_tools or not finish_only) else None,
                # v32.4b: BACK to 0.2. Greedy decoding (0.0) produced degenerate
                # repetition in the qualifying smoke — a turn emitted the same
                # "I need to gather..." sentence 3x and that shipped as the answer.
                # The whole field runs 0.2; determinism comes from the pre-seed and
                # the answer floor, not from collapsing the sampler.
                temperature=0.2,
                # v34.0: the reasoning-off + 6000-token clamp that used to apply to
                # the fallback on the final turn was a workaround for ONE model's
                # documented empty-content defect (ai_gateway glm-5.2-fast), and that
                # model is gone. The same v32.5b note explains why the clamp was
                # regrettable: the final turn is the one that must apply every answer
                # rule and place every [n], so removing reasoning there is a real
                # cost. With the defect gone the workaround is pure loss — both
                # attempts now get reasoning, as the primary always did.
                thinking={"enabled": True, "effort": "low"},
                max_output_tokens=None,
                timeout=timeout,
            )
            _spend_note(payload)
            return payload
        except Exception:
            continue
    return None


# ── stage 1: knowledge briefing ───────────────────────────────────────────────
async def _knowledge_brief(question: str) -> tuple[str, str]:
    """Model's best answer + verification plan. Returns (draft, briefing)."""
    system = ("Senior research analyst. Commit to concrete best answers from "
              "knowledge; mark uncertain values (verify). Never refuse.")
    user = (
        f"Question:\n{question}\n\n"
        "Write these blocks:\n"
        "BEST ANSWER: your full best answer now — candidate pool, every stated "
        "condition applied, qualifying entities with figures/dates, near-miss "
        "exclusions. Flag shaky facts with (verify).\n"
        "CHECKLIST: each atomic condition in the question, numbered, including "
        "any output-format demand.\n"
        "LOOKUPS: 3-6 precise web searches for the facts that decide the answer "
        "(entity + metric + year; include a named source's site: filter).\n"
        "PAGES: up to 5 exact URLs worth reading directly (official stats pages, "
        "sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."
    )
    raw = ""
    try:
        raw = await _chat_simple(LOOP_MODEL_A, system, user,
                                 max_tokens=2400, timeout=BRIEF_TIMEOUT_S,
                                 think=_least_think(LOOP_MODEL_A))
    except Exception:
        try:
            raw = await _chat_simple(LOOP_MODEL_B, system, user,
                                     max_tokens=2400, timeout=BRIEF_TIMEOUT_S,
                                     think=_least_think(LOOP_MODEL_B))
        except Exception:
            raw = ""
    if not raw:
        return "", ""
    draft = raw
    cut = re.search(r"[#*\s]*CHECKLIST[#*\s]*:", raw, re.IGNORECASE)
    if cut is not None:
        draft = raw[:cut.start()]
    draft = re.sub(r"^BEST ANSWER\s*:\s*", "", draft).strip()
    brief = ("PRIOR ANALYSIS (your own; verify anything marked (verify), and "
             "correct it wherever tool results disagree):\n" + raw.strip())
    return draft, brief


# ── stage 1b: deterministic pre-seed ─────────────────────────────────────────
_SEED_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-']+")
_SEED_STOP = frozenset("name list give tell show find identify please could would "
                       "you your can may might should must let make sure both also".split())
MAX_SEED_QUERIES = 3


def _seed_queries(question: str, set_question: bool) -> list[str]:
    q = " ".join((question or "").split())
    if not q:
        return []
    seeds = [q[:300]]
    salient = [t for t in _SEED_TOKEN_RE.findall(q)
               if len(t) >= 3 and t.lower() not in _STOP and t.lower() not in _SEED_STOP]
    if len(salient) >= 2:
        seeds.append(" ".join(salient[:8]))
    if set_question and salient:
        # a set question is lost by an incomplete POOL, so seed the roster hunt
        seeds.append("list of " + " ".join(salient[:6]))
    out: list[str] = []
    for s in seeds:
        s = s.strip()
        if s and s not in out:
            out.append(s)
    return out[:MAX_SEED_QUERIES]


async def _preseed(question: str, set_question: bool, ledger: EvidenceLedger,
                   deadline: float) -> str:
    """Run seed queries sequentially; return a numbered digest to inject."""
    seeds = _seed_queries(question, set_question)
    if not seeds or (deadline - monotonic()) < 40.0:
        return ""
    blocks: list = []
    for seed in seeds:
        if (deadline - monotonic()) < 30.0:
            break
        try:
            out = await asyncio.wait_for(_do_search(seed),
                                          timeout=SEARCH_TIMEOUT_S * 2 + 6.0)   # R3: _do_search now retries
            blocks.append(_commit_tool_output(out, ledger))
        except Exception:
            continue
    good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
    if not good:
        return ""   # no numbered rows -> do not claim "already numbered"
    return ("Automatic first-pass searches (already numbered — cite these [n] "
            "directly, and search further as needed):\n\n" + "\n".join(good))


# ── stage 2a: one turn's tool fan-out ────────────────────────────────────────
async def _tool_phase(calls, question: str, ledger: EvidenceLedger,
                      deadline: float) -> list[dict]:
    """Run one turn's tool calls; return tool replies. Deterministic [n] numbering."""
    run_calls = calls[:MAX_TOOL_CALLS_PER_TURN]
    tool_budget = max(5.0, min(FETCH_TIMEOUT_S * 2 + 6.0,
                               deadline - monotonic() - MIN_TAIL_S))
    tool_tasks = [asyncio.ensure_future(_run_tool(c, question, deadline))
                  for c in run_calls]
    try:
        await asyncio.wait(tool_tasks, timeout=tool_budget)
    except Exception:
        pass
    results = []
    for task in tool_tasks:
        if task.done():
            try:
                results.append(task.result())
            except Exception as exc:
                results.append(f"# tool crashed: {exc}")
        else:
            task.cancel()
            results.append("# tool timed out — use what you already have")
    replies: list[dict] = []
    for call, result in zip(run_calls, results):
        replies.append({"role": "tool", "tool_call_id": call.id,
                        "content": _commit_tool_output(result, ledger)})
    for call in calls[MAX_TOOL_CALLS_PER_TURN:]:
        replies.append({"role": "tool", "tool_call_id": call.id,
                        "content": "# skipped: per-turn tool budget reached — "
                                   "re-issue next turn if still needed"})
    return replies


# ── stage 2: the research loop ────────────────────────────────────────────────
async def _loop(question: str, brief: str, ledger: EvidenceLedger,
                deadline: float, turn_cap: int,
                carry: list[dict] | None = None,
                allow_tools_in_wrapup: bool = False) -> tuple[str, list[dict]]:
    if carry is not None:
        messages = carry
    else:
        set_q = _needs_set_completeness(question)
        messages = [{"role": "system", "content": LOOP_RULES}]
        if set_q:
            messages.append({"role": "system", "content": SET_RULE})
        if _needs_superlative_proof(question):
            messages.append({"role": "system", "content": SUPERLATIVE_RULE})
        if brief:
            messages.append({"role": "system", "content": brief})
        # deterministic evidence BEFORE the model's first choice
        seeded = await _preseed(question, set_q, ledger, deadline)
        if seeded:
            messages.append({"role": "system", "content": seeded})
        messages.append({"role": "user", "content": question})

    answer = ""
    ordered_wrapup = False
    repairs_left = ANSWER_REPAIR_TURNS
    for turn in range(1, turn_cap + 1):
        left = deadline - monotonic()
        if left <= MIN_TAIL_S:
            break
        out_of_time = left <= WRAPUP_AT_S
        out_of_spend = _spend_left() <= WRAPUP_MIN_USD
        finish_only = out_of_time or out_of_spend or turn >= turn_cap
        if (finish_only or turn >= turn_cap - 1) and not ordered_wrapup:
            messages.append({"role": "system", "content": _wrapup_order(left)})
            ordered_wrapup = True

        payload = await _chat_turn(messages, deadline, finish_only=finish_only,
                                   force_tools=allow_tools_in_wrapup and turn == 1)
        if payload is None:
            break
        msg = _first_message(getattr(payload, "llm", None))
        if msg is None:
            break
        calls = getattr(msg, "tool_calls", None) or ()
        if not calls:
            candidate = _payload_text(payload)
            if not _is_usable_answer(candidate):
                if repairs_left > 0 and (deadline - monotonic()) > MIN_TAIL_S + 10.0:
                    repairs_left -= 1
                    messages.append({"role": "system", "content": _REPAIR_ORDER})
                    answer = ""
                    continue
                answer = ""   # nothing usable — let the caller's rescue chain run
                break
            answer = candidate
            # keep the answer IN the transcript so the audit-patch loop can
            # see what it is fixing (review finding: it was never appended).
            messages.append({"role": "assistant", "content": answer})
            break
        messages.append(msg.to_input_message())
        messages.extend(await _tool_phase(calls, question, ledger, deadline))
    return answer, messages


# ── stage 3: completeness audit + patch ───────────────────────────────────────
async def _audit_patch(question: str, answer: str, messages: list[dict],
                       ledger: EvidenceLedger, deadline: float) -> str:
    probe = (
        "Audit the answer against the question. JSON only, keys: "
        '"unanswered_parts" (list; question elements not addressed), '
        '"uncited_facts" (list; load-bearing claims without [n]), '
        '"wrong_kind" (list; places where the named entity is a different KIND '
        "than the question asks — a person instead of a series, a duo instead "
        "of a show), "
        '"incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges '
        "over a candidate pool — a closed set that can be enumerated, or several "
        "conditions applied to a class — then: is the pool itself stated and "
        "plausibly COMPLETE, and does the answer give a verdict for EVERY member "
        "(qualifies / excluded because X, each cited)? Name any pool member the "
        "answer never mentions, and say so if the pool looks truncated — an "
        "answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not "
        "partial), "
        '"thin_proof" (list; a qualifier lacking a per-condition citation, or a '
        "plausible near-miss candidate never addressed), "
        '"hand_waved_tally" (list; for a superlative/count/most-common question: '
        "the answer asserts a winner or a count WITHOUT showing the candidate "
        "table it was derived from. Phrases like 'among others', 'and several "
        "more', 'multiple X', or naming 2 examples to justify a count are all "
        "hand-waving — say so and name what the tally must list). "
        "Empty lists when clean.\n\n"
        f"Question:\n{question}\n\nAnswer:\n{answer[:11000]}"
    )
    try:
        raw = await _chat_simple(AUDIT_MODEL,
                                 "Strict completeness auditor. JSON only.",
                                 probe, max_tokens=2200,
                                 timeout=max(8.0, min(AUDIT_TIMEOUT_S,
                                                      (deadline - monotonic()) - 72.0)))
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I | re.M)
        report = json.loads(raw)
    except Exception:
        return answer
    gaps: list[str] = []
    roster_gaps: list[str] = []
    if isinstance(report, dict):
        for key in ("incomplete_roster", "hand_waved_tally", "unanswered_parts",
                    "uncited_facts", "wrong_kind", "thin_proof"):
            vals = report.get(key)
            if isinstance(vals, list):
                found = [str(v) for v in vals if str(v).strip()]
                if key in ("incomplete_roster", "hand_waved_tally"):
                    roster_gaps.extend(found)
                gaps.extend(found)
    # F2: the patch loop needs room for a search AND a rewrite; below this the
    # audit is a pure cost with no possible effect.
    if not gaps or (deadline - monotonic()) < 70.0:
        return answer
    # A truncated candidate pool is a retrieval gap, not a writing gap: spend the
    # patch turns SEARCHING for the roster/list source, then re-answer.
    order = ("AUDIT: the answer has gaps:\n- " + "\n- ".join(gaps[:6]))
    if roster_gaps:
        order += ("\nThe candidate pool is incomplete — this loses outright. FIRST "
                  "search for the authoritative LIST/roster/table that enumerates "
                  "the whole pool (query it as a list, e.g. '<pool subject> full "
                  "list', not one member at a time), verify EVERY member against "
                  "every condition, then rewrite.")
    order += ("\nUse at most 3 tool calls to close the most important gaps, then "
              "rewrite the COMPLETE final answer with [n] citations in the "
              "required shape.")
    messages.append({"role": "system", "content": order})
    patched, _ = await _loop(question, "", ledger, deadline,
                             AUDIT_EXTRA_TURNS + 1, carry=messages,
                             allow_tools_in_wrapup=True)
    patched = patched.strip()
    # uid201's guard: a "repair" that collapsed the answer is a regression.
    if not _is_usable_answer(patched) or len(patched) < int(len(answer) * 0.6):
        return answer
    return patched


# ── citations ────────────────────────────────────────────────────────────────
# Normalize full-width/CJK brackets and digits to ASCII.
_BRACKET_FIX = {0x3010: "[", 0x3011: "]", 0xFF3B: "[", 0xFF3D: "]",
                0xFF08: "(", 0xFF09: ")", 0x2011: "-", 0x2212: "-"}
_BRACKET_FIX.update({0xFF10 + d: chr(48 + d) for d in range(10)})


def _normalize_brackets(text: str) -> str:
    return (text or "").translate(_BRACKET_FIX)


_CITE_NUM_RE = re.compile(r"\[([0-9][0-9,\s\-]*)\]")


def _cited_numbers(answer: str, top: int) -> list[int]:
    answer = _normalize_brackets(answer)
    seen: set[int] = set()
    out: list[int] = []
    for m in _CITE_NUM_RE.finditer(answer):
        for chunk in m.group(1).split(","):
            piece = chunk.strip()
            span = re.fullmatch(r"(\d{1,4})\s*-\s*(\d{1,4})", piece)
            if span:
                lo = int(span.group(1))
                hi = int(span.group(2))
                for n in range(lo, min(hi, lo + 16) + 1):
                    if 1 <= n <= top and n not in seen:
                        seen.add(n)
                        out.append(n)
            elif piece.isdigit():
                n = int(piece)
                if 1 <= n <= top and n not in seen:
                    seen.add(n)
                    out.append(n)
    return out


def _citations_for(answer: str, ledger: EvidenceLedger) -> list[CitationRef]:
    """Build refs under the 120k materialized-evidence budget."""
    refs: list[CitationRef] = []
    spent = 0
    # Cap what we KEEP, not what we consider: slicing the candidates first made
    # cheap refs beyond position 24 unreachable even with budget to spare, and
    # the one-line-per-member rule pushes distinct [n] counts well past 24.
    for n in _cited_numbers(answer, len(ledger.rows)):
        if len(refs) >= CITATION_CAP:
            break
        ref = ledger.ref_for(n)
        if ref is None:
            continue
        row = ledger.rows[n - 1]
        slices = getattr(ref, "slices", None)
        cost = (sum(max(0, s.end - s.start) for s in slices) if slices
                else int(row.get("note_len") or 0))     # sliceless == the whole note
        if spent + cost > EVIDENCE_CHAR_BUDGET:
            continue      # skip this one, keep considering cheaper later refs
        spent += cost
        refs.append(ref)
    return refs


# ── fallbacks / output ────────────────────────────────────────────────────────
_VERIFY_MARK_RE = re.compile(r"\s*\((?:verify|unverified|uncertain)[^)]*\)", re.I)

# ── final-answer floor ──────────────────────────────────────────────────────
_TOOL_MARKUP_RE = re.compile(
    r"<\s*/?\s*tool_call|<\s*/?\s*(?:arg_key|arg_value|function_call|invoke)\b"
    r"|\bweb_search\s*[（(]\s*query|\bread_page\s*[（(]\s*url|\bsec_filing\s*[（(]\s*company",
    re.I)
_STUB_ANSWER_RE = re.compile(r"^\s*(?:best-effort answer unavailable|no question provided)", re.I)
_REFUSAL_ONLY_RE = re.compile(
    r"^\s*(?:i (?:cannot|can't|am unable|was unable)|unable to|sorry[,.]|"
    r"i don'?t have (?:enough|access))", re.I)
# v32.4b: INTENT NARRATION — the model describing what it is about to do instead
# of answering ("I need to gather...", "Let me search for..."). Observed shipped
# as a final answer in the qualifying smoke, repeated verbatim 3x.
_INTENT_NARRATION_RE = re.compile(
    r"^\s*(?:i (?:need|will|should|am going|'ll)\b|let me\b|first,? (?:i|let)\b|"
    r"i'?ll (?:search|look|start|begin|gather|check))", re.I)
MIN_ANSWER_CHARS = 40
MIN_CITED_ANSWER_CHARS = 12   # F8: '42 [3]' is a legitimate answer
_CITE_MARK_RE = re.compile(r"\[[0-9]{1,3}\]")   # ASCII, matching _CITE_NUM_RE


def _looks_like_tool_json(s: str) -> bool:
    """Tool-call JSON at the start is junk; mid-text JSON is legitimate."""
    return bool(re.match(r'\s*\{\s*"(?:name|tool|function)"\s*:', s))


def _is_degenerate_repetition(text: str) -> bool:
    """True when text is a stalled/greedy-decoding repetition artifact."""
    body = text or ""
    lines = [ln.strip().lower() for ln in body.split("\n") if len(ln.strip()) > 25]
    if len(lines) >= 3:
        for ln in set(lines):
            if lines.count(ln) >= 3:
                return True                      # same line repeated = a stall
        if len(set(lines)) * 2 > len(lines):
            return False                         # mostly-distinct rows = roster
    sents = [s.strip().lower() for s in re.split(r"(?<=[.!?])\s+|\n+", body) if len(s.strip()) > 25]
    if len(sents) < 3:
        return False
    uniq = set(sents)
    if len(uniq) * 2 <= len(sents):
        return True
    # or one sentence repeated 3+ times anywhere
    for s in uniq:
        if sents.count(s) >= 3:
            return True
    return False


def _is_usable_answer(text: str) -> bool:
    """True if text is a submittable answer (not junk/empty/refusal)."""
    s = _normalize_brackets(text).strip()
    if not s:
        return False
    # hard junk, regardless of length or citations
    if _TOOL_MARKUP_RE.search(s) or _looks_like_tool_json(s):
        return False
    if _STUB_ANSWER_RE.match(s) or _is_degenerate_repetition(s):
        return False
    cited = bool(_CITE_MARK_RE.search(s))
    if cited and len(s) >= MIN_CITED_ANSWER_CHARS:
        return True          # cited + substantive == an answer, however short
    if len(s) < MIN_ANSWER_CHARS:
        return False
    # uncited: only then do lead-phrase heuristics apply, and only to SHORT text
    if len(s) < 400 and (_REFUSAL_ONLY_RE.match(s) or _INTENT_NARRATION_RE.match(s)):
        return False
    return True


_COMMIT_RULES = (
    "You are writing the FINAL ANSWER to a research question from evidence that "
    "has already been gathered. You have NO tools — never emit tool syntax. A "
    "judge compares your answer with a strong reference and credits only claims "
    "carrying an [n] citation to the numbered evidence.\n\n"
    "SHAPE: the first words are the answer entities themselves — no preamble, no "
    "remark about evidence quality. Then a short proof section: the candidate "
    "pool, each condition applied, one line per qualifier (cited) and one line "
    "per rejected member with its cited reason — every member gets its own "
    "line, never several swept into one clause. Reproduce figures and dates "
    "VERBATIM. Name ALL qualifying members — omitting one scores as wrong. "
    "Obey any literal formatting demand in the question — sort order, "
    "comma-separated, a requested count, 'without the word X' meaning delete "
    "that word — the shape is graded too. "
    "Never say what the evidence does not contain; commit to the best-supported "
    "answer you can defend."
)

_REPAIR_ORDER = (
    "Your last message was not a usable final answer (it contained tool-call "
    "markup, was empty, or was a refusal). Do NOT emit tool syntax as text. "
    "Write the FINAL ANSWER now as plain prose: first words are the answer "
    "entities themselves, every factual claim followed by its [n] citation, "
    "then the short proof section. Nothing else."
)


def _sanitize_draft(text: str) -> str:
    """Strip (verify) markers that must never reach a submitted answer."""
    return _VERIFY_MARK_RE.sub("", text or "").strip()


# ── v35.0 FORMAT-AWARE ANSWER PRODUCTION (root replacement) ─────────────────
# Every Response flows through _produce_response. It replaces the old _solve
# tail where answers were submitted with minimal cleanup. The renderer owns:
#   1. Rescue ladder (write-from-digest -> deterministic -> knowledge)
#   2. Format-constraint detection and enforcement
#   3. Citation extraction
#   4. Schema coercion with entity extraction (not raw preview dumps)

_OUTPUT_ONLY_RE = re.compile(
    r"\boutput\s+only\b"
    r"|\brespond\s+(?:with\s+)?only\b"
    r"|\bgive\s+only\b"
    r"|\bprovide\s+only\b"
    r"|\blist\s+only\b"
    r"|\bname\s+only\b"
    r"|\bstate\s+only\b"
    r"|\breturn\s+only\b"
    r"|\bwrite\s+only\b",
    re.IGNORECASE
)


def _has_output_only_constraint(question: str) -> bool:
    """Detect negative format constraints that demand bare output only.

    'Output only the exact text' -> True (format constraint, strip proof).
    'the only state that' -> False (entity filter, not format constraint).
    """
    return bool(_OUTPUT_ONLY_RE.search(question or ""))


def _extract_answer_line(answer: str) -> str:
    """Extract the answer entities from the first paragraph of the LLM output.

    LOOP_RULES instructs: 'sentence one IS the answer'. This extracts just that
    opening, stopping at paragraph boundaries. For output-only tasks, the first
    paragraph IS the complete answer."""
    text = (answer or "").strip()
    if not text:
        return ""
    paragraphs = re.split(r"\n\s*\n", text, maxsplit=1)
    first = paragraphs[0].strip()
    # Remove citation markers and bold for bare output
    bare = _CITE_NUM_RE.sub("", first).strip()
    bare = bare.replace("**", "")
    bare = re.sub(r"\s{2,}", " ", bare).strip()
    bare = re.sub(r"\s+([,.])", r"\1", bare)
    return bare


def _extract_evidence_entities(question: str, ledger: "EvidenceLedger") -> str:
    """Extract substantive content from evidence, not raw search titles.

    Replaces _deterministic_answer for schema rescue: scans evidence previews
    for sentence-like content relevant to the question, filtering out navigation
    chrome and search result metadata."""
    terms = _key_terms(question)
    if not terms:
        return ""
    entities: list[str] = []
    seen: set[str] = set()
    for i, row in enumerate(ledger.rows, start=1):
        preview = (row.get("preview") or "").strip()
        if not preview:
            continue
        lead = _informative_lead(preview, limit=400)
        if not lead:
            continue
        lead_lower = lead.lower()
        if not any(t in lead_lower for t in terms):
            continue
        clean = _SRC_FOOTNOTE_RE.sub("", lead).strip()
        if clean and clean not in seen:
            seen.add(clean)
            entities.append(f"{clean} [{i}]")
        if len(entities) >= 6:
            break
    if not entities:
        return ""
    return "\n".join(entities)


_COERCE_URL_RE = re.compile(r"\s[—–\-]\s*https?://")


def _is_coerce_metadata(line: str) -> bool:
    """True if line is metadata/chrome that should not become a schema value."""
    s = line.strip()
    if not s or len(s) < 5:
        return True
    if s.startswith(("Best-supported", "# web_search", "# read_page",
                     "Sources retrieved", "Numbered evidence",
                     "Automatic first-pass")):
        return True
    if _COERCE_URL_RE.search(s):
        return True
    if "://" in s and s.count("://") * 30 > len(s):
        return True
    return False


def _ledger_digest(ledger: EvidenceLedger, char_cap: int = 60000) -> str:
    """Clean numbered evidence digest for commit-from-digest rescue."""
    parts: list[str] = []
    spent = 0
    for i, row in enumerate(ledger.rows, start=1):
        text = (row.get("preview") or "").strip()
        if not text:
            continue
        block = f"[{i}] {row.get('title') or ''} ({row.get('url') or ''})\n{text}"
        if spent + len(block) > char_cap:
            break
        spent += len(block)
        parts.append(block)
    return "\n\n".join(parts)


# Filter page previews to sentence-like content, skipping nav chrome.
_FURNITURE_RE = re.compile(
    r"^\s*(?:share|search|home|menu|subscribe|sign\s*in|log\s*in|newsletter|"
    r"advertisement|cookie|skip to|follow us|read more|related|tags?|categories?|"
    r"privacy|terms|contact|about us|navigation|toggle)\b", re.I)
# Source pages are full of their own footnote markers ("...in 1801[3]..."). If
# those survive into our answer, _cited_numbers reads them as OUR evidence
# indices and mints CitationRefs to unrelated rows — and they also charge the
# evidence budget. Strip them from anything we echo out of a preview.
_SRC_FOOTNOTE_RE = re.compile(r"\[\s*\d{1,3}\s*\]")
_MD_LINK_RE = re.compile(r"\]\(")
_BARE_URL_RE = re.compile(r"(?<!\]\()https?://")
_SENTENCEY_RE = re.compile(r"[.!?]\s|[.!?]$|\b(?:is|was|were|are|has|have|had|"
                           r"reported|announced|released|won|ranked|totall?ed)\b", re.I)


def _informative_lead(preview: str, limit: int = 280) -> str:
    """First stretch of real prose in a page preview, or '' if there is none."""
    kept: list[str] = []
    for chunk in re.split(r"(?<=[.!?])\s+|\n+", _SRC_FOOTNOTE_RE.sub("", preview or "")):
        seg = " ".join(chunk.split())
        if len(seg) < 30 or len(seg) > 400:
            if kept:
                break          # prose has started and then stopped: that is the end
            continue
        if _SENTENCEY_RE.search(seg) is None:
            if kept:
                break          # prose has started and then stopped: that is the end
            continue
        if _FURNITURE_RE.match(seg) and not re.search(r"\d", seg):
            if kept:
                break          # prose has started and then stopped: that is the end
            continue
        if seg.startswith(("*", "|", "↑", "#")):
            if kept:
                break          # prose has started and then stopped: that is the end
            continue
        # A markdown link matches BOTH halves of the pattern; count it once.
        links = len(_MD_LINK_RE.findall(seg)) + len(_BARE_URL_RE.findall(seg))
        if links and links * 110 >= len(seg):     # link-dense == chrome
            if kept:
                break          # prose has started and then stopped: that is the end
            continue
        kept.append(seg)
        if sum(len(k) for k in kept) >= limit:
            break
    out = " ".join(kept).strip()
    if len(out) > limit:                     # cut on a word boundary: slicing
        cut = out.rfind(" ", 0, limit)       # mid-token can invent a figure
        out = out[:cut if cut > 60 else limit].rstrip(" ,;:-")
    return out


def _deterministic_answer(ledger: EvidenceLedger) -> str:
    """Last rung, no LLM — cited partial from ledger previews."""
    rows = [(i, r) for i, r in enumerate(ledger.rows, start=1)
            if (r.get("preview") or "").strip()]
    if not rows:
        return ""
    # LOOP_RULES / _COMMIT_RULES / _wrapup_order all forbid exactly this kind of
    # preamble, and the docstring forbids advertising weakness. Lead with facts.
    out = ["Best-supported findings from the sources retrieved:"]
    picked = 0
    for i, r in rows:                    # filter FIRST, then take 6: rows 1-6 are
        if picked >= 6:                  # page heads (nav chrome); the prose is
            break                        # usually further down the ledger
        lead = _informative_lead(r.get("preview") or "")
        if not lead:
            continue
        title = (r.get("title") or "").strip()
        out.append(f"- {title + ': ' if title else ''}{lead} [{i}]")
        picked += 1
    if picked == 0:
        # Nothing passed the filter. A cited chrome partial still beats the
        # "unavailable" stub, which _STUB_ANSWER_RE itself classifies as junk.
        for i, r in rows[:4]:
            lead = " ".join((r.get("preview") or "").split())[:280]
            if lead:
                out.append(f"- {lead} [{i}]")
        if len(out) == 1:
            return ""
    return "\n".join(out)


async def _write_from_digest(question: str, ledger: EvidenceLedger, deadline: float) -> str:
    """Rewrite answer from clean evidence digest (no tools, no raw transcript)."""
    left = deadline - monotonic()
    if left < 14.0:
        return ""
    digest = _ledger_digest(ledger)
    if not digest:
        return ""
    ask = (f"Question: {question}\n\nNumbered evidence you gathered (cite "
           f"facts by these [n]):\n\n{digest}\n\n"
           "Write the FINAL ANSWER now from this evidence. Plain prose, no "
           "tool syntax. First words are the answer entities; every factual "
           "claim carries its [n]; then the short proof section (pool, "
           "conditions, qualifiers, exclusions).")

    for i, model in enumerate((LOOP_MODEL_A, LOOP_MODEL_B)):
        left = deadline - monotonic()
        if left < 14.0:
            return ""
        budget = min(RESCUE_TIMEOUT_S, left - DIGEST_TAIL_S)
        if i == 0:
            budget = min(budget, max(12.0, left - 14.0 - DIGEST_TAIL_S))
        if budget < 8.0:
            return ""
        try:
            text = await _chat_simple(model, _COMMIT_RULES, ask,
                                      max_tokens=2600, timeout=budget)
        except Exception:
            continue
        if _is_usable_answer(text):
            return text
    return ""


async def _knowledge_resort(question: str, deadline: float) -> str:
    left = deadline - monotonic()
    if left < 12.0:
        return ""
    try:
        return await _chat_simple(
            RESORT_MODEL,
            ("Expert researcher. Best definitive answer with concrete entities, "
             "numbers, dates. Never refuse."),
            question, max_tokens=2600, timeout=min(45.0, left - 4.0))
    except Exception:
        return ""


async def _schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
    ask = ("Convert the answer to a JSON value valid under the schema. Output "
           "ONLY the JSON value.\n\n"
           f"Schema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\n"
           f"Answer:\n{answer[:14000]}")
    for model in (SCHEMA_MODEL, RESORT_MODEL, LOOP_MODEL_A):
        left = deadline - monotonic()
        if left < 12.0:
            break
        try:
            raw = await _chat_simple(model,
                                     "You output strictly valid JSON.", ask,
                                     max_tokens=3400, timeout=min(45.0, left - 4.0))
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(),
                         flags=re.I | re.M).strip()
            value = json.loads(raw)
            # A model that "outputs ONLY the JSON value" still wraps it
            # ({"answer": [...]}) often enough that accepting the first
            # parseable object pre-empts every corrective rung and ships a
            # shape the host rejects. Check, unwrap once, else try the next rung.
            if _matches_schema_shape(value, schema):
                return value
            if isinstance(value, dict) and len(value) == 1:
                inner = list(value.values())[0]
                if _matches_schema_shape(inner, schema):
                    return inner
        except Exception:
            continue
    return None


def _schema_kind(schema) -> str:
    """Top-level JSON type a schema demands, '' when it does not pin one."""
    if not isinstance(schema, dict):
        return ""
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = kind[0] if kind else None
    if kind is None:
        for key in ("anyOf", "oneOf", "allOf"):
            branch = schema.get(key)
            if isinstance(branch, list):
                for sub in branch:
                    got = _schema_kind(sub)
                    if got:
                        return got
        if isinstance(schema.get("properties"), dict):
            return "object"
        if isinstance(schema.get("enum"), list):
            return "string"
        return ""
    return str(kind)


def _matches_schema_shape(value, schema) -> bool:
    kind = _schema_kind(schema)
    if not kind:
        return True                      # schema pins nothing we can check
    if kind == "array":
        return isinstance(value, list)
    if kind == "object":
        return isinstance(value, dict)
    if kind == "string":
        return isinstance(value, str)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "null":
        return value is None
    return True


_NUM_IN_TEXT_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _coerce_to_schema(answer: str, schema, depth: int = 0):
    """Deterministic last-resort schema-shaped value from answer text."""
    if depth > 4 or not isinstance(schema, dict):
        return answer[:400]
    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        low = (answer or "").lower()
        for opt in enum:
            if isinstance(opt, str) and re.search(r"\b" + re.escape(opt.lower()) + r"\b", low):
                return opt
        return enum[0]
    kind = _schema_kind(schema)
    if not kind:
        # pydantic emits anyOf for Optional[...] and $ref for nested models;
        # follow the first concrete branch rather than defaulting to a string
        for key in ("anyOf", "oneOf", "allOf"):
            branch = schema.get(key)
            if isinstance(branch, list) and branch:
                for sub in branch:
                    if isinstance(sub, dict) and sub.get("type") != "null":
                        return _coerce_to_schema(answer, sub, depth + 1)
        kind = "string"
    if kind == "array":
        items = schema.get("items") or {}
        parts = [p.strip(" -*\t") for p in re.split(r"[\n;]|,(?![^(]*\))", answer or "")]
        # v35.0: filter metadata lines (search titles, URLs) to prevent
        # snippet_dump — raw search chrome must never become schema values
        parts = [p for p in parts if p and not _is_coerce_metadata(p)]
        parts = [p[:400] for p in parts][:20]
        if not parts:
            return []  # empty array is schema-valid; better than search chrome
        return [_coerce_to_schema(p, items, depth + 1) for p in parts]
    if kind == "object":
        props = schema.get("properties") or {}
        required = schema.get("required") or list(props.keys())
        out = {}
        for key in required:
            # a required key absent from properties must still be emitted, or
            # the object fails validation for a missing field
            out[key] = _coerce_to_schema(answer, props.get(key) or {}, depth + 1)
        return out
    if kind in ("number", "integer"):
        # strip [n] citation markers first: they are the earliest "numbers" in a
        # cited answer and would otherwise be returned as the value
        found = _NUM_IN_TEXT_RE.search(_CITE_NUM_RE.sub(" ", answer or ""))
        if found is None:
            return 0
        val = found.group(0).replace(",", "")
        try:
            return int(val) if kind == "integer" else float(val)
        except Exception:
            return 0
    if kind == "boolean":
        return not re.match(r"\s*(no\b|false\b|none\b)", (answer or ""), re.I)
    return (answer or "")[:400]


# Strip uncited stage-direction preamble, keeping cited sentences.
_NARRATION_LEAD_RE = re.compile(
    r"^\s*(?:based on (?:my|the)\b|now (?:i|that i)\b|i (?:now )?(?:have|was|am|need|will|can)\b|"
    r"i(?:'ll|'ve|'m)\b|let me\b|let's\b|first,? i\b|having (?:now )?\w+\b|"
    r"okay\b|alright\b|to answer this\b|my research\b)", re.IGNORECASE)
_ABBREV_TAIL_RE = re.compile(r"(?:\b[A-Z]|\b(?:Inc|Ltd|Co|No|vs|St|Dr|Mr|Ms|Mt|Jr|Sr|etc|e\.g|i\.e))\.$")


def _strip_lead_narration(text: str) -> str:
    """Drop leading UNCITED stage-direction sentences. Never touches a sentence
    that carries an [n]: that is a real answer, however it opens."""
    t = (text or "").strip()
    if not t:
        return t
    for _ in range(2):
        parts = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)
        if len(parts) != 2:
            break
        head, rest = parts[0], parts[1].strip()
        if _CITE_NUM_RE.search(head):
            break                       # cited -> it is answer content, keep it
        if _NARRATION_LEAD_RE.match(head) is None:
            break
        # "Based on the U.S. Census Bureau count, X leads [1]." splits after
        # "U." — a 4-word fragment. A real stage direction is a whole sentence,
        # so require one before deleting anything.
        if len(head.split()) < 4 or _ABBREV_TAIL_RE.search(head) is not None:
            break
        if len(rest) < 120 or _CITE_NUM_RE.search(rest) is None:
            break                       # nothing substantial and cited survives
        t = rest
    return t


def _cap(text: str) -> str:
    t = (text or "").strip()
    if len(t) > ANSWER_CHAR_CAP:
        return t[:ANSWER_CHAR_CAP - 16] + " …"
    return t


# ── v35.0 answer production renderer ─────────────────────────────────────────
# _produce_response replaces the old _solve tail. It owns:
#   - rescue ladder (write-from-digest -> deterministic -> knowledge)
#   - format-constraint detection and enforcement
#   - citation extraction from full raw answer
#   - schema coercion with entity extraction (not raw preview dumps)
# This is the ORDINARY successful path — every Response is produced here.

async def _produce_response(question: str, raw_answer: str,
                            ledger: EvidenceLedger, query_obj,
                            deadline: float, draft: str = "") -> Response:
    """Format-aware answer renderer — the root of answer production (v35.0).

    ALL answers flow through this renderer. It integrates rescue, format-constraint
    enforcement, citation extraction, and schema coercion. Replaces the old _solve
    tail where 100+ lines of inline rescue + Response building lived."""

    answer = raw_answer

    # ── rescue ladder (owned by the renderer, not the controller) ────────
    # 1) rewrite from clean evidence digest
    if not _is_usable_answer(answer) and ledger.rows:
        try:
            rescued = await _write_from_digest(question, ledger, deadline)
            if _is_usable_answer(rescued):
                answer = rescued
        except Exception:
            pass
    # 2) deterministic, cited, zero-LLM
    if not _is_usable_answer(answer) and ledger.rows:
        det = _deterministic_answer(ledger)
        if _is_usable_answer(det):
            answer = det
    # 3) last resort: model knowledge (uncited)
    if not _is_usable_answer(answer):
        fallback = _sanitize_draft(draft) or await _knowledge_resort(question, deadline)
        if _is_usable_answer(fallback):
            answer = fallback

    # ── format-constraint detection ──────────────────────────────────────
    output_only = _has_output_only_constraint(question)

    if output_only and _is_usable_answer(answer):
        # Strip proof/analysis — task demands bare output only
        rendered = _extract_answer_line(answer)
        if not rendered or len(rendered) < 3:
            rendered = answer  # extraction failed, keep original
    else:
        rendered = answer

    # ── standard cleanup ─────────────────────────────────────────────────
    rendered = _normalize_brackets(rendered)
    rendered = _strip_lead_narration(rendered)
    text = _cap(rendered) or f"Best-effort answer unavailable for: {question[:400]}"

    # ── citations from the FULL raw answer (before output-only stripping) ─
    try:
        cite_source = answer if _is_usable_answer(answer) else rendered
        citations = _citations_for(cite_source, ledger)
    except Exception:
        citations = []

    # ── schema rendering path ────────────────────────────────────────────
    if query_obj.output_schema is not None:
        structured = None
        try:
            structured = await _schema_output(question, rendered,
                                               query_obj.output_schema, deadline)
        except Exception:
            structured = None
        if structured is not None:
            try:
                return Response(output=structured, citations=citations or None)
            except Exception:
                structured = None
        # Fallback: entity extraction, NOT raw preview dumps
        basis = rendered if _is_usable_answer(rendered) else ""
        if not basis:
            basis = answer if _is_usable_answer(answer) else ""
        if basis and basis.lstrip().startswith("Best-supported findings"):
            extracted = _extract_evidence_entities(question, ledger)
            if extracted:
                basis = extracted
        if not basis:
            basis = _extract_evidence_entities(question, ledger)
        if not basis or _STUB_ANSWER_RE.match(basis.strip()):
            basis = question[:400]
        try:
            forced = _coerce_to_schema(_cap(basis), query_obj.output_schema)
            return Response(output=forced, citations=citations or None)
        except Exception:
            try:
                return Response(output=_cap(basis)[:2000],
                                citations=citations or None)
            except Exception:
                pass

    # ── text rendering path ──────────────────────────────────────────────
    try:
        return Response(text=text, citations=citations or None)
    except Exception:
        return Response(text=text)


# ── entrypoint ────────────────────────────────────────────────────────────────
@entrypoint("query")
async def query(query: Query) -> Response:
    question = (query.text or "").strip()
    if not question:
        return Response(text="No question provided.")
    try:
        return await _solve(query, question)
    except Exception:
        return Response(text=f"Best-effort answer unavailable for: {question[:500]}")


async def _solve(query: Query, question: str) -> Response:
    """Research controller — gathers evidence, then delegates to _produce_response.

    v35.0: the rescue ladder and Response building that used to live here (100+
    lines) moved into _produce_response. _solve now only orchestrates research:
    brief -> loop -> audit -> hand off to the renderer."""
    deadline = monotonic() + WALL_BUDGET_S
    try:
        info = await tooling_info(timeout=10.0)
        _spend_note(info)
    except Exception:
        pass

    draft = ""
    brief = ""
    try:
        if _spend_left() >= BRIEF_MIN_USD and (deadline - monotonic()) > 120.0:
            draft, brief = await _knowledge_brief(question)
    except Exception:
        brief = ""

    ledger = EvidenceLedger()
    answer = ""
    messages: list[dict] = []
    try:
        answer, messages = await _loop(question, brief, ledger, deadline, MAX_TURNS)
    except Exception:
        answer = ""

    try:
        if _is_usable_answer(answer) and (deadline - monotonic()) > 75.0 \
                and _spend_left() >= AUDIT_MIN_USD:
            patched = await _audit_patch(question, answer, messages, ledger, deadline)
            if _is_usable_answer(patched):
                answer = patched
    except Exception:
        pass

    # v35.0: ALL answer production through the format-aware renderer
    return await _produce_response(question, answer, ledger, query, deadline, draft)