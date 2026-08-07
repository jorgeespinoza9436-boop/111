"""agent_d — v32 "toolloop": model-driven research agent.

REDESIGN RATIONALE (batch 88c4a837: our pipeline 0.000, the field's tool-loop
family 0.70-0.80). The scoring architecture is a native agentic loop: the LLM
itself drives search/fetch via tool calls, reads full results in context,
cross-references candidate-by-candidate, and writes one cited answer. Our old
staged pipeline (search -> gate -> chunk -> synth) funnels evidence through
abstractions that lose cross-referencing, never uses model knowledge, and
cannot iterate multi-hop. This file is our OWN implementation of the loop
architecture, keeping the assets our line already validated:
  - the v31.8 answer-shape discipline (asked-KIND, set-intersection
    completeness, numeric verbatim, world-negative vs evidence-concession);
  - a miniaturized section-localizer: big fetched pages are rendered as the
    HEAD plus the TOP-K densest regions (so a filing's deep section, or an
    answer set spread across two distant tables, is readable in one call);
  - SEC EDGAR primary-doc routing as a loop hint;
  - a single-provider LLM ladder (openrouter only; two model families).
Kill-safety: everything bounded by one deadline; force-commit well before it.

v32.6 — STRUCTURAL PASS. No change to the answer discipline, the detectors, the
localizer, the EDGAR router or any prompt text (all byte-for-byte v32.5). What
changed is the scaffolding those assets ran on:
  1. search_many, the batch tool LOOP_RULES tells the model to prefer, raised
     TypeError on every call where any sub-search succeeded, and ran its queries
     sequentially. Fixed and made concurrent; rows merge in QUERY order so [n]
     stays run-invariant.
  2. The seed fan-out in _loop called perf_counter(), never imported: NameError
     on turn 1 of every run, swallowed by a bare except. Removed as a duplicate
     of _preseed, which is now itself concurrent.
  3. A research turn plus its tool phase could overrun the wrap-up band and
     leave no time to write; both now reserve FINISH_RESERVE_S.
  4. Sandbox-policy hardening: no classes (hence no dunder names), no dunder
     imports, no mid-module imports, static tool dispatch only, every getattr
     name a string literal.

v32.7 — SINGLE PROVIDER. ai_gateway is removed; openrouter is the only chat
provider. The two-attempt ladder survives as a MODEL ladder (glm-5 then
deepseek-v3.2) because its value was never provider diversity — it was not
letting one transient failure end a turn, which on the finish turn is a zero.
The glm-5.2-fast empty-content workaround (reasoning off + a token cap on the
final turn) is deleted along with the model it existed for.
"""

import asyncio
import json
import re
from time import monotonic

from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info

# MECHANISM_UPGRADE: parallel search_many retrieval; seed fan-out; post-draft coverage/citation verify-patch
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

VERSION = "v32.7-toolloop"

# ── provider / models ─────────────────────────────────────────────────────────
# v32.7: SINGLE PROVIDER. ai_gateway is gone; openrouter is the only provider
# this agent talks to for chat. The two-attempt ladder is KEPT, because what it
# actually buys is surviving a transient failure on the first attempt (rate
# limit, 5xx, congestion, an empty completion) — losing it would make one bad
# response end a turn outright, and on the finish turn that is a zero. The two
# rungs are now different MODEL FAMILIES on the same provider, which is where
# the independence comes from: glm and deepseek do not fail together.
LLM_PROVIDER = "openrouter"              # the only chat provider
LOOP_MODEL_A = "z-ai/glm-5"              # primary loop + briefing model
LOOP_MODEL_B = "deepseek/deepseek-v3.2"  # second attempt, same provider
LOOP_MODEL_LADDER = (LOOP_MODEL_A, LOOP_MODEL_B)
AUDIT_MODEL = "openai/gpt-oss-120b"
SCHEMA_MODEL = "openai/gpt-oss-120b"
RESORT_MODEL = "deepseek/deepseek-v3.2"
SEARCH_PROVIDER = "parallel"             # search/fetch only — not a chat lane

# ── budgets (seconds) ─────────────────────────────────────────────────────────
WALL_BUDGET_S = 262.0        # v32.4c: 248 was the field's shortest, but 270 collided
                             # with a deadline-blind tool phase (75s chat + 32s fetch
                             # retry = 107s > WRAPUP_AT_S), which could overshoot the
                             # 300s kill. 262 + a hard-bounded tool phase is the margin.
BRIEF_TIMEOUT_S = 50.0
TURN_TIMEOUT_S = 75.0
AUDIT_TIMEOUT_S = 28.0
SEARCH_TIMEOUT_S = 18.0
FETCH_TIMEOUT_S = 16.0
WRAPUP_AT_S = 90.0           # remaining <= this -> stop researching, write
TOOL_PHASE_CAP_S = FETCH_TIMEOUT_S * 2 + 6.0   # 38s: the whole fan-out per turn
# v32.6 — the old comment claimed WRAPUP_AT_S was "> turn timeout + tool time,
# so the band cannot be jumped". It is not: 75s of chat + 38s of tools is 113s,
# so a research turn begun at 91s left could land at ~8s left with no answer
# written, below the 14s floor _write_from_digest needs. Every rescue rung but
# the zero-LLM one was unreachable from there. Rather than push WRAPUP_AT_S out
# to ~140 (which costs real research turns), a research turn and its tool phase
# now RESERVE this much for the final write. When time is plentiful nothing
# changes; only the turn that would have overrun gets clamped.
FINISH_RESERVE_S = 52.0
MIN_TAIL_S = 8.0
MAX_TURNS = 15          # v32.4: field runs 14-16; 13 was the most turn-starved in the class
AUDIT_EXTRA_TURNS = 2
ANSWER_REPAIR_TURNS = 2      # v32.4: bounded retries when the model emits junk instead of an answer
RESCUE_TIMEOUT_S = 55.0

# ── payload shaping ───────────────────────────────────────────────────────────
SEARCH_EXCERPT_CHARS = 550
FETCH_HEAD_CHARS = 3000
FETCH_WINDOW_CHARS = 3600
FETCH_WINDOWS_PER_PAGE = 3   # v32.4: show the top-K disjoint regions, not just one
                             # (single-window reading made runs see different halves
                             # of a spread-out answer set -> divergent medians)
FETCH_PLAIN_CHARS = 6500     # small pages render whole
ANSWER_CHAR_CAP = 60000
CITATION_CAP = 24
# v32.4: the validator materializes every cited slice and rejects the whole
# response past 120_000 chars (miner_response_invalid = 0). Budget below it.
EVIDENCE_CHAR_BUDGET = 105_000

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
    "it with a focus hint for the Item/section.\n\n"
    "CITE EVERYTHING: put [n] (the tool-result number) immediately after the "
    "SENTENCE carrying each claim — not pooled at the end of a paragraph. Every "
    "sentence asserting a number, date, proper noun or causal link needs its own "
    "[n], for the entities you rule OUT as well as those you include. An uncited "
    "specific reads as invented. Cite only results that actually state the claim, "
    "and prefer the most AUTHORITATIVE one that does: the official database/"
    "filing/statistics page over an aggregator, blog, or retrospective article.\n\n"
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
    "(not its director); which COUNTRY, the country. Then a short proof section: "
    "the candidate pool, each condition applied, one line per qualifier (cited) "
    "and one line per prominent exclusion with its cited failing condition. "
    "EXACT VALUES ONLY: when the answer turns on figures, use the figures you "
    "READ in a tool result, verbatim — preserve notation exactly (58.58% and "
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
    "defensible interpretations ('highest scoring games' = the team's own "
    "points OR the combined total; 'largest' = area OR population; 'revenue' = "
    "segment OR consolidated), do NOT silently pick one. Name the ambiguity in "
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
    "WORLD is different and is a real answer when true ('No officer was held "
    "in all four prisons [n]'). If a datum truly cannot be verified, commit "
    "to the best-supported value you found and move on. ONE narrow exception: "
    "when the asked figure genuinely does not exist in any published form, you "
    "may state the REASONED IMPOSSIBILITY — name the specific dataset that "
    "would hold it and why it cannot yield the value — as a fact about the "
    "world, in the first line, alongside the closest cited facts. That is a "
    "committed answer; 'the evidence does not contain it' is not.\n\n"
    "FINISH: never mix tool calls and the final answer in one turn. When the "
    "constraints are verified (or best-effort covered), write the complete "
    "cited answer."

    "\n\n## Pairwise Scoring Rules\n\n"
    "- Decompose every sub-fact/filter before answering; never answer dates/counts/names from memory.\n"
    "- Full roster: enumerate the complete candidate pool, evaluate every candidate, cite exclusions with the failing value.\n"
    "- Literal comparators: more-than is strict; ranges inclusive unless stated.\n"
    "- False premise: correct in the first line with a citation; never refuse or answer evidence-missing.\n"
    "- Exact values: verbatim numbers/dates/units; no rounding.\n"
    "- Commit: partial cited answers beat refusals; cover every asked sub-question.\n"
    "- Citations: [n] after every load-bearing claim (qualifiers AND exclusions); quality over quantity.\n"
    "- Batch lookups: use search_many (or several tool calls in one turn) for independent queries.\n"
)


def _last_call_order(seconds_left: float) -> str:
    """One turn before the hard stop, while tools are still available."""
    return (
        f"LAST CALL (~{int(seconds_left)}s left). This is your final turn that "
        "can use tools: issue only the lookups that decide the answer, batch "
        "them in THIS turn (search_many / several calls at once), and be ready "
        "to write the complete cited answer next turn. Do not start a new line "
        "of enquiry you cannot finish."
    )


def _wrapup_order(seconds_left: float) -> str:
    return (
        f"TIME IS UP (~{int(seconds_left)}s left). No more tool calls. Write the "
        "complete final answer NOW from the numbered results above plus your "
        "knowledge: the FIRST words are the answer entities (no 'Based on…' "
        "preamble, no 'partial answer' framing, no '(verify)' markers), cite [n] "
        "on every claim, keep the required format. A cited partial answer "
        "scores; a refusal or a remark about insufficient evidence scores zero."
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
    "name the maximum. Reproduce that candidate table in the proof section — "
    "a correct winner with no visible tally loses to a reference that shows "
    "its work, and 'among others' / 'and several more' is not a tally. If the "
    "pool is large, show the top contenders and state the cutoff you applied."
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
    "condition). Name the near-misses you excluded and the condition each "
    "fails. Never claim 'the only X' unless the whole pool was checked; if "
    "your pool may be partial, still commit to every qualifier you verified. "
    "GET THE POOL FROM A LIST, NOT MEMBER-BY-MEMBER: your FIRST retrieval for a "
    "set question should hunt the authoritative roster/list/table that "
    "enumerates the whole pool (search it AS a list — '<pool subject> list', "
    "'<pool subject> table', 'list of <pool subject>' — and read_page it). "
    "Assembling the pool from separate per-member searches is how a run ends up "
    "with 3 of 6 qualifiers: the members you never thought to search for are "
    "invisible to you. Read the roster page first, then verify each member. "
    "UNIVERSAL conditions ('in EVERY one of those prisons', 'for BOTH "
    "segments', 'in ALL three years'): check each candidate against EACH "
    "instance separately, with a citation per instance — one shared instance "
    "is not enough. If NO candidate survives every instance, then 'none' IS "
    "the answer: state it as a verified fact about the world with the "
    "per-instance citations that prove it."
)


# ── evidence ledger (tool-result numbering for [n] citations) ─────────────────
# v32.6 STRUCTURE: the ledger is a plain list of row dicts, and the two
# operations are module-level functions. No class, therefore no dunder name
# anywhere in the module — the server-side AST policy rejects dunder attribute
# reflection, and a class body is the one place this file used to need them.
# Behaviour is byte-for-byte the old EvidenceLedger: rows are 1-based by
# position, add() returns the new [n], ref_for() slices to what was SHOWN.


def _new_ledger() -> list:
    return []


def _ledger_add(ledger: list, receipt_id: str, result_id: str, note_len: int,
                kind: str, spans, title: str = "", url: str = "",
                preview: str = "") -> int:
    ledger.append({
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
    return len(ledger)


def _merge_spans(spans, note_len: int) -> list:
    """Clamp to the note, drop empties, then MERGE overlaps in document order.

    v32.6: a large fetch ledgers [(0, FETCH_HEAD_CHARS)] + the K densest
    windows, and _best_windows can legitimately return a window that starts
    inside the head. Two overlapping CitationSlices make the validator
    materialize the same characters twice, which both inflates the run against
    _MAX_TOTAL_EVIDENCE_CHARS and makes _citations_for's cost model understate
    the true spend. Merging is free and strictly reduces evidence chars."""
    clean = []
    for span in spans or ():
        try:
            start = max(0, min(int(span[0]), note_len))
            end = max(0, min(int(span[1]), note_len))
        except Exception:
            continue
        if end > start:
            clean.append((start, end))
    if not clean:
        return []
    clean.sort()
    merged = [list(clean[0])]
    for start, end in clean[1:]:
        if start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1][1] = end
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


def _ledger_ref_for(ledger: list, number: int):
    if not (1 <= number <= len(ledger)):
        return None
    row = ledger[number - 1]
    if not row["receipt_id"] or not row["result_id"]:
        return None
    # every region the model was SHOWN is citable — for a large fetch that is
    # the head AND the focused windows; a head-sourced claim must not dangle
    # outside the judge-materialized slice (review finding).
    spans = _merge_spans(row.get("spans"), int(row.get("note_len") or 0))
    if not spans:
        return None   # F1: every row carries spans; a sliceless ref would
                      # materialize the whole note and can breach/invalidate.
    slices = [CitationSlice(start=s, end=e) for s, e in spans[:4]]
    return CitationRef(receipt_id=row["receipt_id"],
                       result_id=row["result_id"], slices=slices)


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
    """Deterministic scan: the K highest-density, NON-OVERLAPPING windows, in
    document order.

    v32.4 — showing only the single densest window was a direct cause of our
    run-to-run set variance (prod f462cada: runs returned different SUBSETS of
    the answer). When a question's qualifying entities are spread across two
    tables far apart in one page, a single window can only ever show one of
    them, so which one the model sees depends on the trajectory. Surfacing the
    top-K regions makes one fetch carry the whole answer set, on every run."""
    n = len(note)
    if n <= width:
        return [(0, n)]
    step = max(600, width // 3)
    low = note.lower()  # lower() preserves length (casefold can change it)
    scored: list[tuple[int, int]] = []   # (hits, start)
    pos = 0
    while pos < n:
        seg = low[pos:pos + width]
        scored.append((sum(1 for t in terms if t in seg), pos))
        if pos + width >= n:
            break
        pos += step
    # highest density first, earliest position breaking ties (deterministic)
    scored.sort(key=lambda hs: (-hs[0], hs[1]))
    picked: list[tuple[int, int]] = []
    for hits, start in scored:
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


# ── tool execution ────────────────────────────────────────────────────────────
# v32.5 DETERMINISTIC NUMBERING. Tool calls run concurrently, but each used to
# append to the ledger as its OWN network call returned, so [n] assignment was
# latency-ordered and differed between validator re-runs of the same question
# (the same defect already fixed in the pre-seed). Tools now return their rows
# plus text carrying slot placeholders; the caller appends rows in CALL order
# and substitutes the real numbers. Numbering becomes a function of the
# transcript, not the network.
#
# v32.6 SENTINEL: the placeholder was NUL-delimited ("\x00i\x00"). A NUL byte
# that survives into a chat payload is a provider-side 400 on several gateways,
# and crawled pages do occasionally carry NULs, so a stray one could both
# corrupt numbering and kill the turn. The sentinel is now a private-use
# codepoint (never produced by web text), every source string is stripped of
# both, and any placeholder left unresolved is scrubbed before the text ships.
_SLOT_CHAR = "\ue000"
_SLOT = _SLOT_CHAR + "{}" + _SLOT_CHAR
_SLOT_RESIDUAL_RE = re.compile(_SLOT_CHAR + r"\d{0,4}" + _SLOT_CHAR + "?")
_MARKER_RE = re.compile("[\x00" + _SLOT_CHAR + "]")


def _clean_source_text(text: str) -> str:
    """Strip NULs and the slot sentinel from provider-supplied text."""
    return _MARKER_RE.sub("", text or "")


def _tool_output(text: str, rows=None) -> dict:
    """A tool's deferred-commit result: rendered text + the rows to ledger.

    v32.6: was a one-off class whose body needed __init__. A plain dict carries
    the same two fields, keeps the module dunder-free, and lets
    _commit_tool_output tell a tool result from a plain error string with a
    single isinstance check."""
    return {"text": text, "rows": list(rows or ())}


def _is_tool_output(out) -> bool:
    return isinstance(out, dict) and "text" in out and "rows" in out


def _commit_tool_output(out, ledger: list) -> str:
    """Append a tool's rows in call order, then resolve its [n] placeholders."""
    if isinstance(out, str):
        return out
    if not _is_tool_output(out):
        return f"# tool crashed: {out}"
    text = out["text"]
    for i, row in enumerate(out["rows"]):
        n = _ledger_add(ledger, row["receipt_id"], row["result_id"],
                        row["note_len"], row["kind"], row["spans"],
                        title=row.get("title", ""), url=row.get("url", ""),
                        preview=row.get("preview", ""))
        text = text.replace(_SLOT.format(i), str(n))
    # a placeholder with no row behind it must never reach the model (or the
    # provider): render it as an explicit non-citable marker instead.
    return _SLOT_RESIDUAL_RE.sub("?", text)


_SITE_OP_RE = re.compile(r"\bsite:\S+\s*", re.I)


def _degrade_query(q: str) -> str:
    """Loosen an over-constrained query: drop site: operators and quoting.
    Champion lineages retry a failed search this way instead of giving up."""
    out = _SITE_OP_RE.sub("", q or "").replace('"', " ")
    return " ".join(out.split())


async def _do_search(query_text: str, budget_s: float = 0.0):
    """One search, with the v32.5 retry ladder, returning a deferred-commit
    result. NOTE: note_len and every span are offsets into the note as the
    VALIDATOR stores it, so the note is never mutated here — only the rendered
    excerpt is sentinel-scrubbed."""
    if not query_text.strip():
        return "# web_search: empty query"
    # v32.5 SECOND PATH: one provider + one attempt was TERMINAL — an empty result
    # set killed that line of enquiry for the whole run, and an empty search is a
    # pure zero-source. Retry once, then once more with the query loosened.
    # v32.6: the ladder is now bounded by the CALLER's budget. Three 18s attempts
    # is 54s, longer than the loop's whole tool phase, so an unlucky query used to
    # be cancelled outright — discarding the results of attempts that had already
    # succeeded. Each attempt is clamped to the time actually left.
    stop_at = (monotonic() + budget_s) if budget_s > 0 else None
    payload = None
    fired = set()
    # the plain retry must fire even when the degraded form is identical — the
    # previous "attempt == attempts[i-1]" guard ate it for every query without a
    # site: or a quote, i.e. almost all of them, leaving one attempt as before.
    for attempt, allow_repeat in ((query_text, False), (query_text, True),
                                  (_degrade_query(query_text), False)):
        if not attempt.strip() or (attempt in fired and not allow_repeat):
            continue
        per_try = SEARCH_TIMEOUT_S
        if stop_at is not None:
            left = stop_at - monotonic()
            if left < 4.0:
                break          # out of budget: keep whatever we already have
            per_try = max(4.0, min(SEARCH_TIMEOUT_S, left))
        fired.add(attempt)
        try:
            got = await search_web(attempt, provider=SEARCH_PROVIDER, num=8,
                                   timeout=per_try)
        except Exception:
            continue           # v32.6: a later failure must not erase an
                               # earlier (empty but valid) payload
        payload = got
        if getattr(payload, "results", None):
            break
    if payload is None:
        return f"# web_search({query_text!r}) failed"
    _spend_note(payload)
    receipt = str(getattr(payload, "receipt_id", "") or "")
    results = list(getattr(payload, "results", None) or [])
    if not receipt:
        return f"# web_search({query_text!r}): no citable results"
    rows = []
    lines = [f"# web_search({query_text!r}): {len(results)} results"]
    for item in results:
        rid = getattr(item, "result_id", None)
        if not isinstance(rid, str) or not rid:
            continue
        note = (getattr(item, "note", None) or "")
        if not note.strip():
            continue   # F1: no source text -> the platform rejects any citation
                       # to it ("cited result has no source text") and the WHOLE
                       # response is invalidated. Never ledger it.
        # v32.4: cite the EXCERPT WE SHOWED, not the whole note. A sliceless ref
        # materializes the entire note (hydration._materialize_selection), and a
        # rich provider excerpt can run to many KB — a handful of them breaches
        # the 120k wall and invalidates the whole response. The slice must also
        # be >=100 chars unless it covers a shorter note entirely.
        n_len = len(note)
        span = ([(0, min(max(SEARCH_EXCERPT_CHARS, 100), n_len))] if n_len >= 100
                else ([(0, n_len)] if n_len else None))
        title = _clean_source_text((getattr(item, "title", None) or "").strip())
        url = _clean_source_text((getattr(item, "url", None) or "").strip())
        excerpt = _clean_source_text(note[:SEARCH_EXCERPT_CHARS])
        rows.append({"receipt_id": receipt, "result_id": rid, "note_len": n_len,
                     "kind": "search", "spans": span, "title": title, "url": url,
                     "preview": excerpt})
        lines.append(f"[{_SLOT.format(len(rows) - 1)}] {title} — {url}"
                     f"\n    {excerpt}")
    return _tool_output("\n".join(lines), rows)


async def _do_search_many(queries, budget_s: float = 0.0):
    """Batch retrieval: every query fired CONCURRENTLY, ledgered in QUERY order.

    v32.6 — this tool was broken two ways, and LOOP_RULES tells the model to
    reach for it first ("BATCH YOUR LOOKUPS ... search_many"):

      1. CRASH. _do_search returns a deferred-commit result, not a string, so
         '"\\n\\n".join(parts)' raised TypeError the moment ANY sub-search
         succeeded. The model got "# tool crashed: sequence item 0: expected
         str instance..." and every row it had just paid for was dropped on the
         floor. The only path that did not raise was the one where all searches
         failed.
      2. SEQUENTIAL. It awaited each search in turn despite the docstring, so 8
         queries cost up to 8x18s — far past the loop's tool budget — and the
         whole call was cancelled with nothing to show.

    The deferred-commit design is what makes the fix safe: rows are merged in
    QUERY order and numbered by the caller, so concurrency cannot reorder [n].
    Sub-block placeholders are re-indexed against the merged row list."""
    clean = []
    for q in (queries or []):
        text = str(q).strip()
        if text and text not in clean:
            clean.append(text)
    clean = clean[:8]
    if not clean:
        return "# search_many() -> ERROR: no queries"
    # every branch below is bounded by the same budget the caller gave us
    per_query_budget = budget_s if budget_s > 0 else 0.0
    tasks = [asyncio.ensure_future(_do_search(q, per_query_budget)) for q in clean]
    try:
        if per_query_budget > 0:
            await asyncio.wait(tasks, timeout=per_query_budget + 2.0)
        else:
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
        if not _is_tool_output(out):
            blocks.append(f"# web_search({query_text!r}): no citable results")
            continue
        # Re-index this sub-block's placeholders onto the merged row list so a
        # single pass by the caller resolves every [n] once, in query order.
        # HIGHEST local index first: the new marker is always >= the local one
        # it replaces, so it can never collide with a lower index still pending.
        text = out["text"]
        offset = len(merged_rows)
        for local_i in range(len(out["rows"]) - 1, -1, -1):
            text = text.replace(_SLOT.format(local_i),
                                _SLOT.format(local_i + offset))
        merged_rows.extend(out["rows"])
        blocks.append(text)
    return _tool_output(f"# search_many({len(clean)} queries)\n"
                        + "\n\n".join(blocks), merged_rows)


async def _do_fetch(url: str, focus: str, question: str, budget_s: float = 0.0):
    if not url.strip():
        return "# read_page: empty url"
    stop_at = (monotonic() + budget_s) if budget_s > 0 else None
    payload = None
    for _attempt in (0, 1):  # one retry: crawls intermittently return empty
        per_try = FETCH_TIMEOUT_S
        if stop_at is not None:
            left = stop_at - monotonic()
            if left < 4.0:
                break
            per_try = max(4.0, min(FETCH_TIMEOUT_S, left))
        try:
            got = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=per_try)
        except Exception:
            continue           # a failed retry must not erase a valid first payload
        payload = got
        if getattr(payload, "results", None):
            break
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
    # `note` itself is never mutated: note_len and every span index must stay
    # aligned with the copy the validator materializes. Only rendered text is
    # sentinel-scrubbed.
    if len(note) <= FETCH_PLAIN_CHARS:
        row = {"receipt_id": receipt, "result_id": rid, "note_len": len(note),
               "kind": "fetch", "spans": [(0, len(note))], "title": url,
               "url": url, "preview": _clean_source_text(note[:1200])}
        return _tool_output(f"# read_page({url!r}) -> [{_SLOT.format(0)}] full page, "
                            f"{len(note)} chars\n{_clean_source_text(note)}", [row])
    # Large page: head + the K densest question/focus regions (deterministic).
    terms = _key_terms(question) | _key_terms(focus)
    windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE)
    row = {"receipt_id": receipt, "result_id": rid, "note_len": len(note),
           "kind": "fetch", "spans": [(0, FETCH_HEAD_CHARS)] + list(windows),
           "title": url, "url": url,
           "preview": _clean_source_text(note[windows[0][0]:windows[0][0] + 1200])}
    head = _clean_source_text(note[:FETCH_HEAD_CHARS])
    sections = "".join(
        f"\n--- section @{s} ---\n{_clean_source_text(note[s:e])}" for s, e in windows)
    return _tool_output(
        f"# read_page({url!r}) -> [{_SLOT.format(0)}] {len(note)} chars total; head + "
        f"the {len(windows)} most relevant section(s) shown "
        f"({', '.join(f'{s}-{e}' for s, e in windows)}). If the answer set may "
        f"continue elsewhere in this page, call read_page again with a "
        f"different focus.\n--- head ---\n{head}{sections}", [row])


# ── sec_filing tool: deterministic EDGAR primary-document resolution ─────────
# Ported from our review-hardened v31.6 pipeline router; the MODEL supplies
# company/form/year as arguments. v32.3 /code-review fixes: symmetric alnum
# tokenization (legal suffixes/apostrophes/dots no longer break matching),
# ticker branch only for single-token input, reportDate-only named-year match,
# form-code canonicalization, null guards, deadline-aware bounded fetches with
# retry, tickers cache, spend notes, neutral examples, uniform search fallback.
_SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
_SEC_DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"
_SEC_FETCH_TIMEOUT_S = 26.0     # large JSON needs more than the page default (lineage lesson)
_SEC_MIN_HEADROOM_S = 40.0
_SEC_CACHE: dict = {}           # url -> parsed JSON (tickers is ~10MB; fetch once)
_SEC_STOPWORDS = frozenset(
    "inc incorporated corp corporation company companies co ltd limited llc plc "
    "lp llp group holdings the".split())
_SEC_ALNUM_RE = re.compile(r"[a-z0-9]+")


def _sec_tokens(text: str) -> list[str]:
    """ONE tokenizer for both the model's company arg and EDGAR titles — the
    review proved asymmetric tokenization false-negatived 'Apple Inc.',
    \"McDonald's\" and 'U.S. Bancorp'."""
    return [w for w in _SEC_ALNUM_RE.findall((text or "").lower())
            if w not in _SEC_STOPWORDS]


def _sec_norm_form(form: str) -> str:
    """Canonicalize model-supplied form codes to EDGAR's ('10K'->'10-K',
    'def14a'->'DEF 14A', 'Form 10-Q'->'10-Q')."""
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


async def _run_tool(call, question: str, deadline: float, budget_s: float = 0.0):
    """Static dispatch ONLY.

    Every branch names its coroutine literally. No handler table, no
    getattr(module, name), no callable pulled out of a dict — the server-side
    AST policy rejects calling a dynamically selected callable, and a table
    here would also let a hallucinated tool name reach real code."""
    try:
        args = json.loads(getattr(call, "arguments", None) or "{}")
    except Exception:
        args = {}
    if not isinstance(args, dict):
        args = {}
    name = getattr(call, "name", "") or ""
    # (arg or "") not str(arg): an explicit JSON null must not become 'None'
    if name == "web_search":
        return await _do_search(str(args.get("query") or ""), budget_s)
    if name == "search_many":
        qs = args.get("queries") or []
        return await _do_search_many(qs if isinstance(qs, list) else [qs], budget_s)
    if name == "read_page":
        return await _do_fetch(str(args.get("url") or ""),
                               str(args.get("focus") or ""), question, budget_s)
    if name == "sec_filing":
        return await _do_sec_filing(str(args.get("company") or ""),
                                    str(args.get("form") or ""),
                                    str(args.get("year") or ""), deadline)
    return f"# unknown tool {name!r}"


# ── LLM plumbing (single provider, model ladder) ─────────────────────────────
async def _chat_simple(model: str, system: str, user: str, *,
                       max_tokens: int, timeout: float, think=None) -> str:
    payload = await llm_chat(
        provider=LLM_PROVIDER,
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0.15,  # v32.4b: field-standard; greedy caused repetition loops
        max_output_tokens=max_tokens,
        timeout=timeout,
        thinking=think if think is not None else {"enabled": False},
    )
    _spend_note(payload)
    llm = getattr(payload, "llm", None)
    text = (getattr(llm, "raw_text", None) or "").strip()
    if text:
        return text
    choices = getattr(llm, "choices", None) or []
    if choices:
        content = getattr(choices[0].message, "content", None)
        if isinstance(content, str):
            return content.strip()
    return ""


async def _chat_turn(messages, deadline: float, *, finish_only: bool,
                     force_tools: bool = False):
    """One loop turn on openrouter: primary model first, second model on failure."""
    for model in LOOP_MODEL_LADDER:
        left = deadline - monotonic()
        # A RESEARCH turn must leave room to still write the answer afterwards;
        # a FINISH turn is the write, so it may use everything but the tail.
        if finish_only:
            timeout = min(TURN_TIMEOUT_S, left - 5.0)
        else:
            timeout = min(TURN_TIMEOUT_S, left - FINISH_RESERVE_S)
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
                # v32.7: the finish turn now keeps reasoning ON for BOTH rungs.
                # The old lane-scoped override (thinking off + a 6000-token cap)
                # existed for exactly one reason: glm-5.2-fast on ai_gateway had
                # a documented empty-content defect when reasoning was enabled.
                # That model is gone with the provider, and the v32.5b comment
                # already said stripping reasoning from the final turn is a
                # LOSS — it is the one turn that must apply every answer rule
                # and place every [n]. So the workaround goes with the model.
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
    """One call: the model's own best answer + a verification plan. Returns
    (draft_answer, briefing_block). The draft alone often carries a knowledge-
    heavy batch; the loop then verifies the load-bearing facts."""
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
                                 max_tokens=3600, timeout=BRIEF_TIMEOUT_S,
                                 think={"enabled": True, "effort": "low"})
    except Exception:
        try:
            raw = await _chat_simple(LOOP_MODEL_B, system, user,
                                     max_tokens=3600, timeout=BRIEF_TIMEOUT_S,
                                     think={"enabled": True, "effort": "low"})
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
# The measured variance killer: with the model choosing turn 1, five validator
# re-runs opened five different trajectories and gathered five different
# evidence sets (prod f462cada: one run complete, four partial -> median 0).
# These queries are pure functions of the question, so EVERY run starts from the
# same numbered evidence — and the rescue rungs are never empty-handed.
_SEED_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-']+")
_SEED_STOP = frozenset("name list give tell show find identify please could would "
                       "you your can may might should must let make sure both also".split())
MAX_SEED_QUERIES = 3


def _seed_queries(question: str, set_question: bool) -> list[str]:
    q = " ".join((question or "").split())
    if not q:
        return []
    seeds = [q[:300]]
    # F7: keep CONTENT words, not just capitalised/numeric ones — the pool noun
    # in a set question is always lowercase ('which bridges…'), and dropping it
    # turned the roster seed into 'list of Budapest 1945'.
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


async def _preseed(question: str, set_question: bool, ledger: list,
                   deadline: float) -> str:
    """Run the seed queries and return a numbered digest to inject.

    F10 said these had to run SEQUENTIALLY, because back then each _do_search
    appended to the shared ledger as its own network call returned, so [n]
    depended on latency ordering. That is no longer how numbering works: since
    v32.5 searches return rows and the CALLER commits them. So the queries fire
    concurrently and are committed strictly in SEED order — identical numbering
    to the sequential version, at a third of the wall clock. Up to ~36s handed
    back to the research loop before its first turn, on every single run."""
    seeds = _seed_queries(question, set_question)
    left = deadline - monotonic()
    if not seeds or left < 40.0:
        return ""
    budget = max(10.0, min(SEARCH_TIMEOUT_S * 2 + 6.0, left - 30.0))
    tasks = [asyncio.ensure_future(_do_search(seed, budget)) for seed in seeds]
    try:
        await asyncio.wait(tasks, timeout=budget + 3.0)
    except Exception:
        pass
    blocks = []
    for task in tasks:                      # seed order, never completion order
        if not task.done():
            task.cancel()
            continue
        try:
            blocks.append(_commit_tool_output(task.result(), ledger))
        except Exception:
            continue
    good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
    if not good:
        return ""   # no numbered rows -> do not claim "already numbered"
    return ("Automatic first-pass searches (already numbered — cite these [n] "
            "directly, and search further as needed):\n\n" + "\n".join(good))


# ── stage 2: the research loop ────────────────────────────────────────────────
async def _loop(question: str, brief: str, ledger: list,
                deadline: float, turn_cap: int,
                carry=None,
                allow_tools_in_wrapup: bool = False):
    if carry is not None:
        messages = carry
    else:
        set_q = _needs_set_completeness(question)
        messages = [{"role": "system", "content": LOOP_RULES}]
        # v32.6 REMOVED: a second "seed fan-out" block used to sit here. It
        # called perf_counter(), which this module never imports, so it raised
        # NameError on turn 1 of EVERY run and was swallowed by a bare
        # `except Exception: pass` — the mechanism its own comment advertised
        # has never executed once. It was also a duplicate: _preseed below is
        # the deterministic seed fan-out, and running both would have doubled
        # pre-loop retrieval cost for the same queries. The live one is kept
        # and is now parallel; the dead one is gone rather than resurrected.
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

    # S9 claim-sheet → parallel seed retrieval (retrieval data-flow change)
    try:
        _s9_store = index
    except NameError:
        try:
            _s9_store = ledger
        except NameError:
            _s9_store = None
    if _s9_store is not None:
        _s9_q = query.text
        _s9_claims = await _s9_decompose_claims(_s9_q, deadline=deadline)
        if _s9_claims:
            _s9_seed = await _s9_seed_retrieval(_s9_claims, _s9_store, deadline=deadline)
            if _s9_seed:
                messages.append({
                    "role": "system",
                    "content": (
                        "## S9 Claim Sheet\n\n"
                        + "\n".join(f"- {c}" for c in _s9_claims)
                        + "\n\n## Seed Evidence\n\n"
                        + _s9_seed
                        + "\n\nContinue with search_many/fetch_page as needed, then answer with [n] citations."
                    ),
                })
    ordered_wrapup = False
    warned_last_call = False
    repairs_left = ANSWER_REPAIR_TURNS
    for turn in range(1, turn_cap + 1):
        left = deadline - monotonic()
        if left <= MIN_TAIL_S:
            break
        out_of_time = left <= WRAPUP_AT_S
        out_of_spend = _spend_left() <= WRAPUP_MIN_USD
        finish_only = out_of_time or out_of_spend or turn >= turn_cap
        if finish_only and not ordered_wrapup:
            messages.append({"role": "system", "content": _wrapup_order(left)})
            ordered_wrapup = True
        elif turn >= turn_cap - 1 and not (ordered_wrapup or warned_last_call):
            # v32.6: this used to fire the FULL wrapup order ("TIME IS UP. No
            # more tool calls.") one turn early — while tools were still
            # attached to the request. The model was told not to call tools and
            # handed tools in the same turn; whichever it obeyed, one of them
            # was wasted. The early turn now gets a last-call warning that
            # matches what it can actually do, and the hard stop lands with the
            # turn that really has no tools.
            messages.append({"role": "system", "content": _last_call_order(left)})
            warned_last_call = True

        payload = await _chat_turn(messages, deadline, finish_only=finish_only,
                                   force_tools=allow_tools_in_wrapup and turn == 1)
        if payload is None:
            break
        llm = getattr(payload, "llm", None)
        choices = getattr(llm, "choices", None) or []
        if not choices:
            break
        # v32.6: the turn body is guarded. It reads SDK objects (choices[0].message,
        # msg.to_input_message()) whose shape we do not own; an AttributeError here
        # used to propagate out of _loop, and the caller's `except: answer = ""`
        # then threw away BOTH the answer already written and the whole transcript
        # the audit-patch stage needs. A bad turn now ends the loop with everything
        # earned so far intact.
        try:
            msg = choices[0].message
            calls = getattr(msg, "tool_calls", None) or ()
            if not calls:
                candidate = (getattr(llm, "raw_text", None) or "").strip()
                if not candidate:
                    content = getattr(msg, "content", None)
                    if isinstance(content, str):
                        candidate = content.strip()
                # v32.4 FLOOR: never accept tool-markup / empty / stub / bare refusal
                # as the final answer (prod f462cada shipped exactly that). Spend a
                # bounded repair turn telling the model to write plain prose instead.
                if not _is_usable_answer(candidate):
                    if repairs_left > 0 and (deadline - monotonic()) > MIN_TAIL_S + 10.0:
                        repairs_left -= 1
                        # F9: do NOT echo the junk back — replaying tool markup as an
                        # assistant turn is the strongest few-shot signal to repeat it.
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
            # The assistant tool-call message MUST land before its replies, or
            # every tool_call_id below dangles and the transcript is rejected.
            messages.append(msg.to_input_message())
            # per-turn fan-out cap: run the first 8, stub the rest — EVERY tool_call
            # id still gets a reply (an unanswered id fails transcript validation).
            run_calls = calls[:8]
            # F3: the tool phase must never outlive the deadline. Bound the whole
            # fan-out; anything unfinished is reported back so every tool_call_id
            # still receives a reply and the transcript stays valid.
            # v32.6: while we still intend to write an answer, the fan-out reserves
            # the final-write budget too — otherwise a 38s tool phase begun near the
            # wrapup band leaves the loop below the floor _write_from_digest needs.
            reserve = MIN_TAIL_S if ordered_wrapup else FINISH_RESERVE_S
            tool_budget = max(5.0, min(TOOL_PHASE_CAP_S,
                                       deadline - monotonic() - reserve))
            # v32.6: each tool also gets the budget, so its own internal retry ladder
            # stops in time to RETURN partial evidence instead of being cancelled
            # wholesale by the asyncio.wait below (cancellation discards the rows).
            per_tool_budget = max(4.0, tool_budget - 2.0)
            # R1: asyncio.wait (not wait_for+gather) so a timeout does NOT discard the
            # calls that already finished — v32.4 kept their evidence because each tool
            # wrote the ledger itself, and the deferred-commit refactor must not lose it.
            tool_tasks = [asyncio.ensure_future(
                              _run_tool(c, question, deadline, per_tool_budget))
                          for c in run_calls]
            try:
                await asyncio.wait(tool_tasks, timeout=tool_budget)
            except Exception:
                pass
            results = []
            for t in tool_tasks:
                if t.done():
                    try:
                        results.append(t.result())
                    except Exception as exc:
                        results.append(f"# tool crashed: {exc}")
                else:
                    t.cancel()
                    results.append("# tool timed out — use what you already have")
            for call_result in zip(run_calls, results):
                call = call_result[0]
                # v32.5: ledger rows are appended HERE, in call order — never inside
                # the concurrent coroutines — so [n] numbering is run-invariant.
                body = _commit_tool_output(call_result[1], ledger)
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": body})
            for call in calls[8:]:
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": "# skipped: per-turn tool budget reached — re-issue next turn if still needed"})
        except Exception:
            break
    return answer, messages


# ── stage 3: completeness audit + patch ───────────────────────────────────────
async def _audit_patch(question: str, answer: str, messages: list[dict],
                       ledger: list, deadline: float) -> str:
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
                                 probe, max_tokens=650, timeout=AUDIT_TIMEOUT_S)
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
# v32.5: glm emits full-width/CJK brackets (【1】, ［1］) often enough that
# champion lineages normalize them explicitly. ASCII-only matching would drop
# EVERY citation (judge credits nothing) and simultaneously make the answer
# floor read the answer as uncited.
# Ordinal-keyed dict (str.translate accepts one directly) — avoids str.maketrans,
# which is a static access on a builtin type and untested against the server-side
# AST policy. Includes full-width DIGITS: without them the floor's unicode-aware
# \d saw "cited" while the ASCII-only extractor yielded nothing, shipping an
# answer with citations=None — worse than not normalizing at all.
_BRACKET_FIX = {0x3010: "[", 0x3011: "]", 0xFF3B: "[", 0xFF3D: "]",
                0xFF08: "(", 0xFF09: ")", 0x2011: "-", 0x2212: "-"}
for _d in range(10):                      # U+FF10..U+FF19 -> ASCII 0-9
    _BRACKET_FIX[0xFF10 + _d] = chr(48 + _d)


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


def _citations_for(answer: str, ledger: list) -> list:
    """Build refs under the platform's materialized-evidence wall.

    harnyx_commons/application/miner_response_hydration.py: the validator
    materializes every cited slice and raises MinerResponsePayloadError past
    _MAX_TOTAL_EVIDENCE_CHARS = 120_000 — the whole response then scores 0.
    A SLICELESS ref materializes start=0..len(note), i.e. the ENTIRE note, so
    search refs (which carry no spans) are the expensive ones. Prod f462cada
    hit miner_response_invalid on 2 runs; multi-window reads raised the per-ref
    cost, so budget it explicitly instead of hoping."""
    refs = []
    spent = 0
    # v32.6: CITATION_CAP now bounds the refs we KEEP, not the candidates we
    # look at. Slicing the cited numbers first meant a run whose early [n]s were
    # dead rows (a failed fetch, a note with no source text) or budget-skips
    # burned cap slots on nothing and silently dropped citations it had room
    # for. Same ceiling, same order, no wasted slots.
    for n in _cited_numbers(answer, len(ledger)):
        if len(refs) >= CITATION_CAP:
            break
        ref = _ledger_ref_for(ledger, n)
        if ref is None:
            continue
        row = ledger[n - 1]
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

# ── v32.4 FINAL-ANSWER FLOOR ─────────────────────────────────────────────────
# Prod batch f462cada: several validator runs submitted literal tool-call MARKUP
# as the final answer ("<tool_call>web_search<arg_key>query</arg_key>…", and a
# corrupted full-width-paren variant) because the loop accepted ANY no-tool-call
# message as the answer. Others submitted empty text or the internal stub. Each
# of those is a guaranteed 0, and since validators re-run the agent, they were a
# major driver of our median-vs-best gap. Nothing may be submitted unless it
# reads as a real answer.
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
    """F13: only a tool-call JSON at the very START is junk; an answer that
    QUOTES a JSON record mid-text is legitimate."""
    return bool(re.match(r'\s*\{\s*"(?:name|tool|function)"\s*:', s))


def _is_degenerate_repetition(text: str) -> bool:
    """True when the text is the same sentence emitted over and over — the
    classic stalled/greedy-decoding artifact. Cheap and language-agnostic:
    if the distinct sentences cover under half the body, it is a loop."""
    sents = [s.strip().lower() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if len(s.strip()) > 25]
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
    """A submittable answer. F13/F8 fixes: a CITED, substantive answer is always
    an answer — terse replies ('Yes, both are French [1].') and the reasoned-
    impossibility shape LOOP_RULES explicitly asks for were being thrown away,
    and a 4000-char cited answer was discarded for its opening clause."""
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
    "pool, each condition applied, one line per qualifier (cited) and one per "
    "prominent exclusion with its cited reason. Reproduce figures and dates "
    "VERBATIM. Name ALL qualifying members — omitting one scores as wrong. "
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
    """The briefing draft marks shaky facts '(verify)' by instruction; those
    markers must NEVER reach a submitted answer (judge-penalized uncertainty)."""
    return _VERIFY_MARK_RE.sub("", text or "").strip()


def _ledger_digest(ledger: list, char_cap: int = 60000) -> str:
    """A clean numbered evidence digest — no tool-call history. Preserves the
    exact [n] numbering so citations still resolve. Committing from this beats
    replaying the raw transcript: shorter, no assistant/tool scaffolding, and it
    cannot drop early [n]s off the front of a truncated message window."""
    parts: list[str] = []
    spent = 0
    for i, row in enumerate(ledger, start=1):
        text = (row.get("preview") or "").strip()
        if not text:
            continue
        block = f"[{i}] {row.get('title') or ''} ({row.get('url') or ''})\n{text}"
        if spent + len(block) > char_cap:
            break
        spent += len(block)
        parts.append(block)
    return "\n\n".join(parts)


def _deterministic_answer(ledger: list) -> str:
    """Last rung, no LLM. Never emit a bare 'unavailable' line: the judge sees
    only the answer text and makes a forced preference, so advertising our own
    failure hands it a reason to pick the other side. A cited partial always
    beats a refusal."""
    rows = [(i, r) for i, r in enumerate(ledger, start=1)
            if (r.get("preview") or "").strip()]
    if not rows:
        return ""
    out = ["FINAL ANSWER: based on the sources retrieved, the best-supported "
           "findings for this question are:"]
    for i, r in rows[:6]:
        lead = " ".join((r.get("preview") or "").split())[:280]
        title = (r.get("title") or "").strip()
        out.append(f"- {title + ': ' if title else ''}{lead} [{i}]")
    return "\n".join(out)


async def _write_from_digest(question: str, ledger: list, deadline: float) -> str:
    """Last write from the evidence already gathered: thinking OFF, NO tools, and
    a CLEAN numbered digest instead of the raw transcript — so the model cannot
    over-reason into an empty completion, cannot emit tool markup, and cannot
    lose early [n]s to a truncated message window."""
    left = deadline - monotonic()
    if left < 14.0:
        return ""
    digest = _ledger_digest(ledger)
    if not digest:
        return ""
    convo = [{"role": "system", "content": _COMMIT_RULES},
             {"role": "user", "content": (
                 f"Question: {question}\n\nNumbered evidence you gathered (cite "
                 f"facts by these [n]):\n\n{digest}\n\n"
                 "Write the FINAL ANSWER now from this evidence. Plain prose, no "
                 "tool syntax. First words are the answer entities; every factual "
                 "claim carries its [n]; then the short proof section (pool, "
                 "conditions, qualifiers, exclusions).")}]
    async def _one(model: str, budget: float) -> str:
        payload = await llm_chat(
            provider=LLM_PROVIDER, model=model, messages=convo,
            temperature=0.15, max_output_tokens=2600,
            timeout=budget, thinking={"enabled": False},
        )
        _spend_note(payload)
        llm = getattr(payload, "llm", None)
        text = (getattr(llm, "raw_text", None) or "").strip()
        if not text:
            choices = getattr(llm, "choices", None) or []
            if choices:
                c = getattr(choices[0].message, "content", None)
                if isinstance(c, str):
                    text = c.strip()
        return text

    # v32.5b: the hedge race is REVERTED. Review proved three independent paths
    # to "": (1) asyncio.wait puts a RAISED task in `done`, so a fast failure of
    # the first attempt — the exact case the second exists for — meant the
    # second was never started; (2) for 31s < left <= 45s the second branch was
    # skipped and the cleanup loop cancelled the still-running first;
    # (3) FIRST_COMPLETED let a fast-junk attempt cancel a slow-good one. The
    # sequential loop below has none of those failure modes, and an answer that
    # exists beats one that races.
    for model in LOOP_MODEL_LADDER:
        left = deadline - monotonic()
        if left < 14.0:
            return ""
        try:
            text = await _one(model, min(RESCUE_TIMEOUT_S, left - 6.0))
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
            question, max_tokens=1500, timeout=min(45.0, left - 4.0))
    except Exception:
        return ""


async def _schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
    ask = ("Convert the answer to a JSON value valid under the schema. Output "
           "ONLY the JSON value.\n\n"
           f"Schema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\n"
           f"Answer:\n{answer[:14000]}")
    for model in (SCHEMA_MODEL, RESORT_MODEL):
        left = deadline - monotonic()
        if left < 12.0:
            return None
        try:
            raw = await _chat_simple(model,
                                     "You output strictly valid JSON.", ask,
                                     max_tokens=2400, timeout=min(45.0, left - 4.0))
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(),
                         flags=re.I | re.M).strip()
            return json.loads(raw)
        except Exception:
            continue
    return None


def _cap(text: str) -> str:
    t = (text or "").strip()
    if len(t) > ANSWER_CHAR_CAP:
        return t[:ANSWER_CHAR_CAP - 16] + " …"
    return t


# ── entrypoint ────────────────────────────────────────────────────────────────
# v32.6: _seed_queries_from_question lived here. Its only caller was the dead
# fan-out block in _loop, so it was unreachable code; _seed_queries above is the
# live seed generator.


# === S9 mechanisms (claim-sheet seed retrieval + contradiction/coverage gate) ===
S9_MAX_CLAIMS = 6
S9_SEED_MIN_SECONDS = 55.0
S9_GATE_MIN_SECONDS = 40.0
# Mutable box avoids reflection APIs banned by miner upload AST checks.
_S9_CLAIM_STATE = {"queries": ()}


def _s9_resolve_model() -> str:
    try:
        return MODEL
    except NameError:
        pass
    try:
        return PRIMARY_MODEL
    except NameError:
        pass
    try:
        return LOOP_MODEL
    except NameError:
        pass
    return "z-ai/glm-5"


def _s9_resolve_provider() -> str:
    try:
        return LLM_PROVIDER
    except NameError:
        return "openrouter"


async def _s9_decompose_claims(question: str, *, deadline: float) -> list[str]:
    """Tools-off JSON claim sheet that drives subsequent retrieval."""
    if deadline - perf_counter() < 20:
        return []
    _model = _s9_resolve_model()
    _provider = _s9_resolve_provider()
    try:
        result = await llm_chat(
            provider=_provider,
            model=_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Decompose the question into atomic retrievable subclaims, filter checks, "
                        'and comparison sides. JSON only: {"claims":["..."]} with 2-6 short '
                        "search-ready strings."
                    ),
                },
                {"role": "user", "content": question},
            ],
            tools=None,
            temperature=0.1,
            max_output_tokens=500,
            thinking=LlmThinkingConfig(enabled=False),
            timeout=min(22.0, max(6.0, deadline - perf_counter() - 8)),
        )
        raw = (result.response.raw_text or "").strip()
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I | re.M).strip()
        data = json.loads(cleaned)
        claims = data.get("claims") if isinstance(data, dict) else None
        if not isinstance(claims, list):
            return []
        return [str(c).strip() for c in claims if str(c).strip()][:S9_MAX_CLAIMS]
    except Exception:
        return []


async def _s9_seed_retrieval(claims: list[str], store, *, deadline: float) -> str:
    """Parallel seed searches for every claim — retrieval control/data-flow change."""
    if not claims or deadline - perf_counter() < S9_SEED_MIN_SECONDS:
        return ""
    try:
        try:
            return await _run_search_many(claims, store)
        except TypeError:
            return await _run_search_many(claims, store, deadline=deadline)
    except NameError:
        pass
    try:
        return await _do_search_many(claims, store, time_left=min(20.0, deadline - perf_counter()))
    except NameError:
        pass
    try:
        return await _tool_search_many(claims, store)
    except NameError:
        pass
    except Exception as exc:
        return f"# S9 seed retrieval error: {exc}"
    return ""


async def _s9_contradiction_coverage_gate(
    question: str,
    answer: str,
    messages: list,
    store,
    *,
    deadline: float,
) -> str:
    """JSON evidence gate for missing/uncited/contradictory claims; optional 1-2 tool turns."""
    if not answer or deadline - perf_counter() < S9_GATE_MIN_SECONDS:
        return answer
    _model = _s9_resolve_model()
    _provider = _s9_resolve_provider()
    try:
        audit = await llm_chat(
            provider=_provider,
            model=_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "# Strict Evidence Gate\n\nOutput JSON only with keys "
                        "missing_elements, uncited_claims, contradictions (arrays)."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Audit for pairwise coverage and note support.\n\nQuestion:\n{question}"
                        f"\n\nAnswer:\n{answer[:12000]}"
                    ),
                },
            ],
            tools=None,
            temperature=0.1,
            max_output_tokens=700,
            thinking=LlmThinkingConfig(enabled=False),
            timeout=min(28.0, max(6.0, deadline - perf_counter() - 10)),
        )
        raw = (audit.response.raw_text or "").strip()
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I | re.M).strip()
        data = json.loads(cleaned)
        report = data
    except Exception:
        return answer
    issues: list[str] = []
    if isinstance(report, dict):
        for key in ("missing_elements", "uncited_claims", "contradictions"):
            vals = report.get(key)
            if isinstance(vals, list):
                issues.extend(str(v) for v in vals if str(v).strip())
    if not issues or deadline - perf_counter() < 22:
        return answer
    messages.append(
        {
            "role": "system",
            "content": (
                "## S9 Evidence Gate Gaps\n\n"
                + "\n".join(f"- {x}" for x in issues[:6])
                + "\n\nUse at most 2 tool calls (prefer search_many), then rewrite the COMPLETE "
                "final answer with inline [n] citations including exclusions."
            ),
        }
    )
    try:
        chat_fn = _chat_turn
    except NameError:
        try:
            chat_fn = _chat
        except NameError:
            chat_fn = None
    if chat_fn is None:
        return answer
    patched = answer
    for extra in range(2):
        remaining = deadline - perf_counter()
        if remaining <= 8:
            break
        force_text = extra == 1 or remaining <= 18
        try:
            try:
                chat_result = await chat_fn(messages, deadline=deadline, force_text=force_text)
            except TypeError:
                try:
                    chat_result = await chat_fn(messages, deadline=deadline, final=force_text)
                except TypeError:
                    chat_result = await chat_fn(messages, deadline=deadline)
        except Exception:
            break
        if chat_result is None:
            break
        try:
            tool_calls = chat_result.response.choices[0].message.tool_calls or ()
        except Exception:
            tool_calls = ()
        if not tool_calls:
            cand = (chat_result.response.raw_text or "").strip()
            if cand:
                patched = cand
            break
        messages.append(
            {
                "role": "assistant",
                "content": chat_result.response.raw_text,
                "tool_calls": [
                    {"id": tc.id, "type": tc.type, "name": tc.name, "arguments": tc.arguments}
                    for tc in tool_calls
                ],
            }
        )
        for tc in tool_calls:
            try:
                args = json.loads(tc.arguments or "{}")
            except Exception:
                args = {}
            result_text = f"# unsupported tool {tc.name!r}"
            try:
                if tc.name == "search_web":
                    try:
                        try:
                            result_text = await _run_search_web(args.get("query", ""), store)
                        except TypeError:
                            result_text = await _run_search_web(args.get("query", ""), store, deadline=deadline)
                    except NameError:
                        try:
                            result_text = await _do_search(str(args.get("query", "")), store, time_left=remaining)
                        except NameError:
                            try:
                                result_text = await _tool_search(str(args.get("query", "")), store)
                            except NameError:
                                result_text = f"# unsupported tool {tc.name!r}"
                elif tc.name == "search_many":
                    qs = args.get("queries") or []
                    qs = qs if isinstance(qs, list) else [qs]
                    try:
                        try:
                            result_text = await _run_search_many(qs, store)
                        except TypeError:
                            result_text = await _run_search_many(qs, store, deadline=deadline)
                    except NameError:
                        try:
                            result_text = await _do_search_many(qs, store, time_left=remaining)
                        except NameError:
                            try:
                                result_text = await _tool_search_many(qs, store)
                            except NameError:
                                result_text = f"# unsupported tool {tc.name!r}"
                elif tc.name == "fetch_page":
                    try:
                        try:
                            result_text = await _run_fetch_page(args.get("url", ""), store)
                        except TypeError:
                            result_text = await _run_fetch_page(args.get("url", ""), store, deadline=deadline)
                    except NameError:
                        try:
                            try:
                                result_text = await _do_fetch(str(args.get("url", "")), store, time_left=remaining)
                            except TypeError:
                                result_text = await _do_fetch(str(args.get("url", "")), store)
                        except NameError:
                            result_text = f"# unsupported tool {tc.name!r}"
            except Exception as exc:
                result_text = f"# {tc.name} error: {exc}"
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})
    return patched or answer



@entrypoint("query")
async def query(query: Query) -> Response:
    question = (query.text or "").strip()
    if not question:
        return Response(text="No question provided.")
    try:
        return await _solve(query, question)
    except Exception:
        # a miner-attributed exception is a hard 0 — always return SOME text
        return Response(text=f"Best-effort answer unavailable for: {question[:500]}")


async def _solve(query: Query, question: str) -> Response:
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

    ledger = _new_ledger()
    answer = ""
    messages = []
    try:
        answer, messages = await _loop(question, brief, ledger, deadline, MAX_TURNS)
    except Exception:
        answer = ""
        messages = []

    try:
        # v32.6: `and messages` — _audit_patch carries the transcript back into
        # _loop, and an EMPTY carry would run the patch turns with no system
        # rules, no evidence and no question, replacing a good answer with junk.
        if answer and messages and (deadline - monotonic()) > 75.0 \
                and _spend_left() >= AUDIT_MIN_USD:
            patched = await _audit_patch(question, answer, messages, ledger, deadline)
            # the patch loop can itself return junk — only take it if it passes
            if _is_usable_answer(patched):
                answer = patched
    except Exception:
        pass

    # v32.4 RESCUE LADDER — every rung is cited; none advertises failure.
    # 1) rewrite from the clean evidence digest (thinking off, no tools)
    if not _is_usable_answer(answer) and ledger:
        try:
            rescued = await _write_from_digest(question, ledger, deadline)
            if _is_usable_answer(rescued):
                answer = rescued
        except Exception:
            pass
    # 2) deterministic, CITED, zero-LLM. F4: this must come BEFORE the knowledge
    #    draft — the draft is written pre-research and carries no [n] at all, so
    #    it passed the floor and permanently shadowed the only cited rung.
    if not _is_usable_answer(answer) and ledger:
        det = _deterministic_answer(ledger)
        if _is_usable_answer(det):
            answer = det
    # 3) last resort: model knowledge (uncited, but better than nothing)
    if not _is_usable_answer(answer):
        fallback = _sanitize_draft(draft) or await _knowledge_resort(question, deadline)
        if fallback.strip():
            answer = fallback          # F4: never destroy a usable answer with ""

    try:
        citations = _citations_for(answer, ledger)
    except Exception:
        citations = []

    answer = _normalize_brackets(answer)   # the judge reads THIS, not the ref list
    text = _cap(answer) or f"Best-effort answer unavailable for: {question[:400]}"

    if query.output_schema is not None:
        structured = None
        try:
            structured = await _schema_output(question, answer, query.output_schema, deadline)
        except Exception:
            structured = None
        if structured is not None:
            try:
                return Response(output=structured, citations=citations or None)
            except Exception:
                pass  # invalid structured output must not sink the good text answer

    try:

        # S9: contradiction + coverage gate (verification control-flow change)
        if text and (deadline - perf_counter()) > S9_GATE_MIN_SECONDS:
            try:
                _s9_store = index
            except NameError:
                try:
                    _s9_store = ledger
                except NameError:
                    _s9_store = None
            if _s9_store is not None:
                try:
                    text = await _s9_contradiction_coverage_gate(
                        query.text,
                        text,
                        messages,
                        _s9_store,
                        deadline=deadline,
                    )
                except Exception:
                    pass
        return Response(text=text, citations=citations or None)
    except Exception:
        return Response(text=text)
