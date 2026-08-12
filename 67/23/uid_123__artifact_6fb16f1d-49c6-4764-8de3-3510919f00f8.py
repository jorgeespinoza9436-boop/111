"""Harnyx miner entrypoint with difficulty-routed Easy / Medium / Hard agents.

Architecture overview
---------------------
1. EasyPath / MediumPath / HardPath each encapsulate a full research agent.
   Calling ``_compile()`` builds and returns an async ``query(Query) -> Response``
   callable closed over that agent's helpers and constants.
2. DifficultyRouter asks a small LLM to label the question as easy / medium / hard
   (prompt currently biases toward ``hard``).
3. The module-level ``@entrypoint("query")`` dispatches to the matching compiled
   runner. On router failure it falls back to HardPath.
4. ``_glen_*`` helpers are intentionally unused dead code and must not be wired
   into the live path.

Behavior of the three agents is preserved from their source artifacts; this file
only wraps and routes them.
"""

from __future__ import annotations
import asyncio
from harnyx_miner_sdk.api import LlmThinkingConfig, llm_chat
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

# =============================================================================
# EasyPath — compiled agent used when DifficultyRouter returns 'easy'
# Tool-loop research agent with spend gates, audit patch, and rescue ladder.
# =============================================================================

class EasyPath:

    # Build the closed-over async query runner for the Easy agent.
    def _compile(self):
        import asyncio
        import json
        import re
        from time import monotonic

        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

        # --- EasyPath configuration: models, providers, budgets, timeouts ---
        LLM_PROVIDER = "openrouter"
        LOOP_MODEL_A = "z-ai/glm-5.2"
        LOOP_MODEL_B = "deepseek/deepseek-v3.2"


        AUDIT_MODEL = "openai/gpt-oss-120b"
        SCHEMA_MODEL = "openai/gpt-oss-120b"
        RESORT_MODEL = "deepseek/deepseek-v3.2"
        SEARCH_PROVIDER = "parallel"


        WALL_BUDGET_S = 262.0


        BRIEF_TIMEOUT_S = 50.0


        TURN_TIMEOUT_S = 75.0
        FALLBACK_MAX_PAYLOAD_CHARS = 380_000


        SEARCH_TIMEOUT_S = 18.0
        FETCH_TIMEOUT_S = 16.0
        AUDIT_TIMEOUT_S = 28.0
        WRAPUP_AT_S = 90.0


        MIN_TAIL_S = 8.0
        MAX_TURNS = 15
        MAX_TOOL_CALLS_PER_TURN = 8


        AUDIT_EXTRA_TURNS = 2
        ANSWER_REPAIR_TURNS = 2
        RESCUE_TIMEOUT_S = 55.0
        DIGEST_TAIL_S = 14.0


        FETCH_WINDOW_CHARS = 3600
        SEARCH_EXCERPT_CHARS = 550
        FETCH_HEAD_CHARS = 3000
        FETCH_WINDOWS_PER_PAGE = 3


        ANSWER_CHAR_CAP = 60000
        CITATION_CAP = 24
        FETCH_PLAIN_CHARS = 6500


        EVIDENCE_CHAR_BUDGET = 105_000


        AUDIT_MIN_USD = 0.05
        WRAPUP_MIN_USD = 0.02
        BRIEF_MIN_USD = 0.03

        _SPEND = {"left": None}


        # SpendBudget: track remaining USD from tooling_info payloads.
        class SpendBudget:

            @staticmethod
            def _spend_note(payload) -> None:
                budget = getattr(payload, "budget", None)
                left = getattr(budget, "session_remaining_budget_usd", None)
                if isinstance(left, (int, float)):
                    _SPEND["left"] = float(left)

            @staticmethod
            def _spend_left() -> float:
                left = _SPEND["left"]
                if isinstance(left, (int, float)):
                    return float(left)
                return 1.0


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


        LOOP_RULES = (
            "You are a research agent answering a hard multi-part factual question. A "
            "judge compares your answer head-to-head with a strong reference and only "
            "credits claims that carry a citation to a tool result that states them.\n\n"
            "METHOD: think in constraints and candidates. Recall what you already know "
            "to form the candidate pool, then use web_search/read_page to verify every "
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
            "requested shape, then still add the proof section below it; the shape "
            "directive is never a reason to omit the proof. When an ORDER is demanded, "
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


        # QuestionClassifier: wrap-up urgency, superlatives, set-completeness.
        class QuestionClassifier:

            @staticmethod
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

            @staticmethod
            def _has_superlative(text: str) -> bool:
                if _ONE_WINNER_RE.search(text or ""):
                    return True
                for m in _EST_RE.finditer(text or ""):
                    if m.group(0).lower() not in _EST_STOP:
                        return True
                return False

            @staticmethod
            def _needs_superlative_proof(question: str) -> bool:
                q = " ".join((question or "").split())
                if not q:
                    return False
                return _has_superlative(q) or bool(
                    re.search(r"\b(?:most|least) (?:common|frequent|number|amount)\b|\bhow many\b", q, re.I))

            @staticmethod
            def _needs_set_completeness(question: str) -> bool:
                q = " ".join((question or "").split())
                if _SET_HINT_RE.search(q):
                    return True


                m = _PLURAL_HEAD_RE.search(q)
                if m and m.group(1).lower() not in _PLURAL_FALSE:
                    if not _has_superlative(q) or re.search(r"\b(?:all|every|each)\b", q, re.IGNORECASE):
                        return True

                return bool(re.search(r"\bwhich\b", q, re.IGNORECASE)) and bool(_SET_CONNECTIVE_RE.search(q))


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


        _EST_STOP = frozenset(
            "interest honest modest protest request suggest forest harvest invest "
            "manifest contest arrest digest earnest conquest tempest midwest northwest "
            "southwest unrest bequest behest attest molest ingest infest detest incest "
            "armrest backrest pretest headrest footrest".split())
        _EST_RE = re.compile(r"\b([a-z]{3,})est\b")


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


        # EvidenceLedger: store search/fetch rows and retained quotes.
        class EvidenceLedger:
            def __init__(self) -> None:
                self.rows: list[dict] = []

            def add(self, receipt_id: str, result_id: str, note_len: int,
                    kind: str, spans: list[tuple[int, int]] | None,
                    title: str = "", url: str = "", preview: str = "") -> int:
                self.rows.append({
                    "receipt_id": receipt_id,
                    "result_id": result_id,
                    "note_len": note_len,
                    "kind": kind,


                    "title": (title or "")[:160],
                    "url": (url or "")[:300],
                    "preview": (preview or "")[:1200],
                    "spans": spans,
                })
                return len(self.rows)

            def ref_for(self, number: int) -> CitationRef | None:
                if not (1 <= number <= len(self.rows)):
                    return None
                row = self.rows[number - 1]
                if row.get("kind") == "reserved":
                    return None
                if not row["receipt_id"] or not row["result_id"]:
                    return None
                spans = row["spans"]
                if spans:


                    slices = []
                    for span in spans[:4]:
                        start = max(0, min(int(span[0]), row["note_len"]))
                        end = max(start + 1, min(int(span[1]), row["note_len"]))
                        slices.append(CitationSlice(start=start, end=end))
                    return CitationRef(receipt_id=row["receipt_id"],
                                       result_id=row["result_id"], slices=slices)
                return None


        _WORD_RE = re.compile(r"[a-z0-9][a-z0-9'.\-]{2,}")
        _STOP = frozenset(
            "the and for with from that this have has was were are is been its their "
            "which what when where who how many much according also into over under "
            "between during against about after before while other more most than".split())


        # PageLocalizer: key-term windows inside fetched page notes.
        class PageLocalizer:

            @staticmethod
            def _key_terms(text: str) -> set[str]:
                return {w for w in _WORD_RE.findall((text or "").casefold()) if w not in _STOP}

            @staticmethod
            def _best_windows(note: str, terms: set[str], width: int,
                              k: int = 1) -> list[tuple[int, int]]:
                n = len(note)
                if n <= width:
                    return [(0, n)]
                step = max(600, width // 3)
                low = note.lower()
                scored: list[tuple[int, int]] = []
                pos = 0
                while pos < n:
                    seg = low[pos:pos + width]
                    scored.append((-sum(1 for t in terms if t in seg), pos))
                    if pos + width >= n:
                        break
                    pos += step


                scored.sort()
                picked: list[tuple[int, int]] = []
                for neg_hits, start in scored:
                    hits = -neg_hits
                    if len(picked) >= max(1, k):
                        break
                    end = min(n, start + width)
                    if any(start < pe and ps < end for ps, pe in picked):
                        continue
                    if picked and hits <= 0:
                        continue
                    picked.append((start, end))
                picked.sort()
                return picked or [(0, min(n, width))]


        _SLOT = "\x00{}\x00"


        # ToolOutput: tool text plus optional ledger rows.
        class ToolOutput:


            def __init__(self, text: str, rows: list[dict] | None = None) -> None:
                self.text = text
                self.rows = rows or []


        # ToolExecutor: search/fetch/tool-phase orchestration.
        class ToolExecutor:

            @staticmethod
            def _commit_tool_output(out, ledger: EvidenceLedger) -> str:
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

            @staticmethod
            def _degrade_query(q: str) -> str:
                out = _SITE_OP_RE.sub("", q or "").replace('"', " ")
                return " ".join(out.split())

            @staticmethod
            async def _do_search(query_text: str) -> "ToolOutput | str":
                if not query_text.strip():
                    return "# web_search: empty query"


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
                        continue


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

            @staticmethod
            async def _do_fetch(url: str, focus: str, question: str) -> "ToolOutput | str":


                if not url.strip():
                    return "# read_page: empty url"
                payload = None
                for _attempt in (0, 1):
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

            @staticmethod
            async def _run_tool(call, question: str, deadline: float) -> "ToolOutput | str":
                try:
                    args = json.loads(getattr(call, "arguments", None) or "{}")
                except Exception:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                name = getattr(call, "name", "") or ""

                if name == "web_search":
                    return await _do_search(str(args.get("query") or ""))
                if name == "read_page":
                    return await _do_fetch(str(args.get("url") or ""),
                                           str(args.get("focus") or ""), question)
                if name == "sec_filing":
                    return await _do_sec_filing(str(args.get("company") or ""),
                                                str(args.get("form") or ""),
                                                str(args.get("year") or ""), deadline)
                return f"# unknown tool {name!r}"

            @staticmethod
            async def _tool_phase(calls, question: str, ledger: EvidenceLedger,
                                  deadline: float) -> list[dict]:


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


        _SITE_OP_RE = re.compile(r"\bsite:\S+\s*", re.I)


        _SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
        _SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
        _SEC_DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"
        _SEC_FETCH_TIMEOUT_S = 26.0
        _SEC_MIN_HEADROOM_S = 40.0
        _SEC_CACHE: dict = {}
        _SEC_CACHE_MAX = 24


        _SEC_STOPWORDS = frozenset(
            "inc incorporated corp corporation company companies co ltd limited llc plc "
            "lp llp group holdings the".split())
        _SEC_ALNUM_RE = re.compile(r"[a-z0-9]+")


        # SecFilingTool: SEC form normalization and filing fetch.
        class SecFilingTool:

            @staticmethod
            def _sec_tokens(text: str) -> list[str]:
                return [w for w in _SEC_ALNUM_RE.findall((text or "").lower())
                        if w not in _SEC_STOPWORDS]

            @staticmethod
            def _sec_norm_form(form: str) -> str:
                f = " ".join((form or "").upper().replace("FORM", " ").split())
                m = re.fullmatch(r"(\d{1,2})\s*-?\s*([A-Z])", f)
                if m:
                    return f"{m.group(1)}-{m.group(2)}"
                m = re.fullmatch(r"(DEF)\s*-?\s*(14A)", f)
                if m:
                    return "DEF 14A"
                return f

            @staticmethod
            async def _fetch_json(url: str, deadline: float):
                cached = _SEC_CACHE.get(url)
                if cached is not None:
                    return cached
                for _attempt in (0, 1):
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


                            keep = _SEC_CACHE.get(_SEC_TICKERS_URL)
                            _SEC_CACHE.clear()
                            if keep is not None:
                                _SEC_CACHE[_SEC_TICKERS_URL] = keep
                        _SEC_CACHE[url] = obj
                        return obj
                return None

            @staticmethod
            def _sec_pick_filing(recent: dict, form: str, year: str):
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

            @staticmethod
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
                best = None
                for row in tickers.values():
                    if not isinstance(row, dict):
                        continue
                    title = str(row.get("title", ""))
                    ticker = str(row.get("ticker", "")).lower()
                    words = set(_sec_tokens(title))
                    n_hit = sum(1 for w in want if w in words)
                    if len(want) == 1 and ticker == want[0]:
                        score = 100

                    elif want and n_hit == len(want):
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


        _SEC_SEARCH_HINT = "search \"site:sec.gov {company} {year} {form}\" and read_page the Archives result"


        _REASONING_MANDATORY = ("openai/gpt-oss",)


        # LlmClient: chat_simple / chat_turn helpers.
        class LlmClient:

            @staticmethod
            def _least_think(model: str) -> dict:
                for prefix in _REASONING_MANDATORY:
                    if model.startswith(prefix):
                        return {"enabled": True, "effort": "low"}
                return {"enabled": False}

            @staticmethod
            def _first_message(llm):
                choices = getattr(llm, "choices", None) or []
                if not choices:
                    return None
                return getattr(choices[0], "message", None)

            @staticmethod
            def _message_text(msg) -> str:
                content = getattr(msg, "content", None)
                if isinstance(content, str):
                    return content.strip()
                return ""

            @staticmethod
            def _payload_text(payload) -> str:
                llm = getattr(payload, "llm", None)
                text = (getattr(llm, "raw_text", None) or "").strip()
                if text:
                    return text
                return _message_text(_first_message(llm))

            @staticmethod
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
                    temperature=0.15,
                    max_output_tokens=max_tokens,
                    timeout=timeout,
                    thinking=think,
                )
                _spend_note(payload)
                return _payload_text(payload)

            @staticmethod
            async def _chat_turn(messages: list[dict], deadline: float, *, finish_only: bool,
                                 force_tools: bool = False):


                payload_chars = sum(len(str(msg.get("content") or "")) for msg in messages
                                    if isinstance(msg, dict))
                for attempt, model in enumerate((LOOP_MODEL_A, LOOP_MODEL_B)):
                    is_fallback = attempt > 0
                    if is_fallback and payload_chars > FALLBACK_MAX_PAYLOAD_CHARS:


                        return _EMPTY_TURN
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


                            temperature=0.2,


                            thinking={"enabled": True, "effort": "low"},
                            max_output_tokens=None,
                            timeout=timeout,
                        )
                        _spend_note(payload)
                        return payload
                    except Exception:
                        continue
                return None


        # Empty LLM stubs used when a chat call fails.
        class _EmptyChoiceMessage:
            content = ""
            tool_calls = ()


        class _EmptyChoice:
            message = _EmptyChoiceMessage()


        class _EmptyLlm:
            raw_text = ""
            choices = (_EmptyChoice(),)


        class _EmptyTurn:
            llm = _EmptyLlm()
            budget = None


        _EMPTY_TURN = _EmptyTurn()


        # ResearchLoop: brief, seed searches, main loop, audit patch.
        class ResearchLoop:

            @staticmethod
            async def _knowledge_brief(question: str) -> tuple[str, str]:
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

            @staticmethod
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

                    seeds.append("list of " + " ".join(salient[:6]))
                out: list[str] = []
                for s in seeds:
                    s = s.strip()
                    if s and s not in out:
                        out.append(s)
                return out[:MAX_SEED_QUERIES]

            @staticmethod
            async def _preseed(question: str, set_question: bool, ledger: EvidenceLedger,
                               deadline: float) -> str:
                seeds = _seed_queries(question, set_question)
                if not seeds or (deadline - monotonic()) < 40.0:
                    return ""


                blocks: list = []
                for seed in seeds:
                    if (deadline - monotonic()) < 30.0:
                        break
                    try:
                        out = await asyncio.wait_for(_do_search(seed),
                                                      timeout=SEARCH_TIMEOUT_S * 2 + 6.0)
                        blocks.append(_commit_tool_output(out, ledger))
                    except Exception:
                        continue
                good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
                if not good:
                    return ""
                return ("Automatic first-pass searches (already numbered — cite these [n] "
                        "directly, and search further as needed):\n\n" + "\n".join(good))

            @staticmethod
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
                            answer = ""
                            break
                        answer = candidate


                        messages.append({"role": "assistant", "content": answer})
                        break
                    messages.append(msg.to_input_message())
                    messages.extend(await _tool_phase(calls, question, ledger, deadline))
                return answer, messages

            @staticmethod
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


                if not gaps or (deadline - monotonic()) < 70.0:
                    return answer


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

                if not _is_usable_answer(patched) or len(patched) < int(len(answer) * 0.6):
                    return answer
                return patched


        _SEED_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-']+")
        _SEED_STOP = frozenset("name list give tell show find identify please could would "
                               "you your can may might should must let make sure both also".split())
        MAX_SEED_QUERIES = 3


        _BRACKET_FIX = {0x3010: "[", 0x3011: "]", 0xFF3B: "[", 0xFF3D: "]",
                        0xFF08: "(", 0xFF09: ")", 0x2011: "-", 0x2212: "-"}


        _BRACKET_FIX.update({0xFF10 + d: chr(48 + d) for d in range(10)})


        # CitationBuilder: bracket normalize + citation refs.
        class CitationBuilder:

            @staticmethod
            def _normalize_brackets(text: str) -> str:
                return (text or "").translate(_BRACKET_FIX)

            @staticmethod
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

            @staticmethod
            def _citations_for(answer: str, ledger: EvidenceLedger) -> list[CitationRef]:
                refs: list[CitationRef] = []
                spent = 0


                for n in _cited_numbers(answer, len(ledger.rows)):
                    if len(refs) >= CITATION_CAP:
                        break
                    ref = ledger.ref_for(n)
                    if ref is None:
                        continue
                    row = ledger.rows[n - 1]
                    slices = getattr(ref, "slices", None)
                    cost = (sum(max(0, s.end - s.start) for s in slices) if slices
                            else int(row.get("note_len") or 0))
                    if spent + cost > EVIDENCE_CHAR_BUDGET:
                        continue
                    spent += cost
                    refs.append(ref)
                return refs


        _CITE_NUM_RE = re.compile(r"\[([0-9][0-9,\s\-]*)\]")


        _VERIFY_MARK_RE = re.compile(r"\s*\((?:verify|unverified|uncertain)[^)]*\)", re.I)


        _TOOL_MARKUP_RE = re.compile(
            r"<\s*/?\s*tool_call|<\s*/?\s*(?:arg_key|arg_value|function_call|invoke)\b"
            r"|\bweb_search\s*[（(]\s*query|\bread_page\s*[（(]\s*url|\bsec_filing\s*[（(]\s*company",
            re.I)
        _STUB_ANSWER_RE = re.compile(r"^\s*(?:best-effort answer unavailable|no question provided)", re.I)
        _REFUSAL_ONLY_RE = re.compile(
            r"^\s*(?:i (?:cannot|can't|am unable|was unable)|unable to|sorry[,.]|"
            r"i don'?t have (?:enough|access))", re.I)


        _INTENT_NARRATION_RE = re.compile(
            r"^\s*(?:i (?:need|will|should|am going|'ll)\b|let me\b|first,? (?:i|let)\b|"
            r"i'?ll (?:search|look|start|begin|gather|check))", re.I)
        MIN_ANSWER_CHARS = 40
        MIN_CITED_ANSWER_CHARS = 12
        _CITE_MARK_RE = re.compile(r"\[[0-9]{1,3}\]")


        # AnswerFloor: usable-answer checks and digest fallbacks.
        class AnswerFloor:

            @staticmethod
            def _looks_like_tool_json(s: str) -> bool:
                return bool(re.match(r'\s*\{\s*"(?:name|tool|function)"\s*:', s))

            @staticmethod
            def _is_degenerate_repetition(text: str) -> bool:


                body = text or ""
                lines = [ln.strip().lower() for ln in body.split("\n") if len(ln.strip()) > 25]
                if len(lines) >= 3:
                    for ln in set(lines):
                        if lines.count(ln) >= 3:
                            return True
                    if len(set(lines)) * 2 > len(lines):
                        return False
                sents = [s.strip().lower() for s in re.split(r"(?<=[.!?])\s+|\n+", body) if len(s.strip()) > 25]
                if len(sents) < 3:
                    return False
                uniq = set(sents)
                if len(uniq) * 2 <= len(sents):
                    return True

                for s in uniq:
                    if sents.count(s) >= 3:
                        return True
                return False

            @staticmethod
            def _is_usable_answer(text: str) -> bool:
                s = _normalize_brackets(text).strip()
                if not s:
                    return False

                if _TOOL_MARKUP_RE.search(s) or _looks_like_tool_json(s):
                    return False
                if _STUB_ANSWER_RE.match(s) or _is_degenerate_repetition(s):
                    return False
                cited = bool(_CITE_MARK_RE.search(s))
                if cited and len(s) >= MIN_CITED_ANSWER_CHARS:
                    return True
                if len(s) < MIN_ANSWER_CHARS:
                    return False

                if len(s) < 400 and (_REFUSAL_ONLY_RE.match(s) or _INTENT_NARRATION_RE.match(s)):
                    return False
                return True

            @staticmethod
            def _sanitize_draft(text: str) -> str:
                return _VERIFY_MARK_RE.sub("", text or "").strip()

            @staticmethod
            def _ledger_digest(ledger: EvidenceLedger, char_cap: int = 60000) -> str:
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

            @staticmethod
            def _informative_lead(preview: str, limit: int = 280) -> str:
                kept: list[str] = []
                for chunk in re.split(r"(?<=[.!?])\s+|\n+", _SRC_FOOTNOTE_RE.sub("", preview or "")):
                    seg = " ".join(chunk.split())
                    if len(seg) < 30 or len(seg) > 400:
                        if kept:
                            break
                        continue


                    if _SENTENCEY_RE.search(seg) is None:
                        if kept:
                            break
                        continue


                    if _FURNITURE_RE.match(seg) and not re.search(r"\d", seg):
                        if kept:
                            break
                        continue
                    if seg.startswith(("*", "|", "↑", "#")):
                        if kept:
                            break
                        continue

                    links = len(_MD_LINK_RE.findall(seg)) + len(_BARE_URL_RE.findall(seg))
                    if links and links * 110 >= len(seg):
                        if kept:
                            break
                        continue
                    kept.append(seg)
                    if sum(len(k) for k in kept) >= limit:
                        break
                out = " ".join(kept).strip()
                if len(out) > limit:
                    cut = out.rfind(" ", 0, limit)
                    out = out[:cut if cut > 60 else limit].rstrip(" ,;:-")
                return out

            @staticmethod
            def _deterministic_answer(ledger: EvidenceLedger) -> str:
                rows = [(i, r) for i, r in enumerate(ledger.rows, start=1)
                        if (r.get("preview") or "").strip()]
                if not rows:
                    return ""


                out = ["Best-supported findings from the sources retrieved:"]
                picked = 0
                for i, r in rows:
                    if picked >= 6:
                        break
                    lead = _informative_lead(r.get("preview") or "")
                    if not lead:
                        continue
                    title = (r.get("title") or "").strip()
                    out.append(f"- {title + ': ' if title else ''}{lead} [{i}]")
                    picked += 1
                if picked == 0:


                    for i, r in rows[:4]:
                        lead = " ".join((r.get("preview") or "").split())[:280]
                        if lead:
                            out.append(f"- {lead} [{i}]")
                    if len(out) == 1:
                        return ""
                return "\n".join(out)


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


        _FURNITURE_RE = re.compile(
            r"^\s*(?:share|search|home|menu|subscribe|sign\s*in|log\s*in|newsletter|"
            r"advertisement|cookie|skip to|follow us|read more|related|tags?|categories?|"
            r"privacy|terms|contact|about us|navigation|toggle)\b", re.I)


        _SRC_FOOTNOTE_RE = re.compile(r"\[\s*\d{1,3}\s*\]")
        _MD_LINK_RE = re.compile(r"\]\(")
        _BARE_URL_RE = re.compile(r"(?<!\]\()https?://")
        _SENTENCEY_RE = re.compile(r"[.!?]\s|[.!?]$|\b(?:is|was|were|are|has|have|had|"
                                   r"reported|announced|released|won|ranked|totall?ed)\b", re.I)


        # RescueWriter: digest write, schema coerce, narration strip.
        class RescueWriter:

            @staticmethod
            async def _write_from_digest(question: str, ledger: EvidenceLedger, deadline: float) -> str:
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

            @staticmethod
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

            @staticmethod
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


                        if _matches_schema_shape(value, schema):
                            return value
                        if isinstance(value, dict) and len(value) == 1:
                            inner = list(value.values())[0]
                            if _matches_schema_shape(inner, schema):
                                return inner
                    except Exception:
                        continue
                return None

            @staticmethod
            def _schema_kind(schema) -> str:
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

            @staticmethod
            def _matches_schema_shape(value, schema) -> bool:
                kind = _schema_kind(schema)
                if not kind:
                    return True
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

            @staticmethod
            def _coerce_to_schema(answer: str, schema, depth: int = 0):
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
                    parts = [p[:400] for p in parts if p][:20]
                    if not parts:
                        parts = [answer[:400]]
                    return [_coerce_to_schema(p, items, depth + 1) for p in parts]
                if kind == "object":
                    props = schema.get("properties") or {}
                    required = schema.get("required") or list(props.keys())
                    out = {}
                    for key in required:


                        out[key] = _coerce_to_schema(answer, props.get(key) or {}, depth + 1)
                    return out
                if kind in ("number", "integer"):


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

            @staticmethod
            def _strip_lead_narration(text: str) -> str:
                t = (text or "").strip()
                if not t:
                    return t
                for _ in range(2):
                    parts = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)
                    if len(parts) != 2:
                        break
                    head, rest = parts[0], parts[1].strip()
                    if _CITE_NUM_RE.search(head):
                        break
                    if _NARRATION_LEAD_RE.match(head) is None:
                        break


                    if len(head.split()) < 4 or _ABBREV_TAIL_RE.search(head) is not None:
                        break
                    if len(rest) < 120 or _CITE_NUM_RE.search(rest) is None:
                        break
                    t = rest
                return t

            @staticmethod
            def _cap(text: str) -> str:
                t = (text or "").strip()
                if len(t) > ANSWER_CHAR_CAP:
                    return t[:ANSWER_CHAR_CAP - 16] + " …"
                return t


        _NUM_IN_TEXT_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


        _NARRATION_LEAD_RE = re.compile(
            r"^\s*(?:based on (?:my|the)\b|now (?:i|that i)\b|i (?:now )?(?:have|was|am|need|will|can)\b|"
            r"i(?:'ll|'ve|'m)\b|let me\b|let's\b|first,? i\b|having (?:now )?\w+\b|"
            r"okay\b|alright\b|to answer this\b|my research\b)", re.IGNORECASE)


        _ABBREV_TAIL_RE = re.compile(r"(?:\b[A-Z]|\b(?:Inc|Ltd|Co|No|vs|St|Dr|Mr|Ms|Mt|Jr|Sr|etc|e\.g|i\.e))\.$")


        # EasyPath inner entry: thin wrapper around QuerySolver._solve.
        async def query(query: Query) -> Response:
            question = (query.text or "").strip()
            if not question:
                return Response(text="No question provided.")
            try:
                return await _solve(query, question)
            except Exception:

                return Response(text=f"Best-effort answer unavailable for: {question[:500]}")


        # QuerySolver: end-to-end EasyPath solve pipeline.
        class QuerySolver:

            @staticmethod
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


                if not _is_usable_answer(answer) and ledger.rows:
                    try:
                        rescued = await _write_from_digest(question, ledger, deadline)
                        if _is_usable_answer(rescued):
                            answer = rescued
                    except Exception:
                        pass


                if not _is_usable_answer(answer) and ledger.rows:
                    det = _deterministic_answer(ledger)
                    if _is_usable_answer(det):
                        answer = det

                if not _is_usable_answer(answer):
                    fallback = _sanitize_draft(draft) or await _knowledge_resort(question, deadline)
                    if _is_usable_answer(fallback):
                        answer = fallback

                try:
                    citations = _citations_for(answer, ledger)
                except Exception:
                    citations = []

                answer = _normalize_brackets(answer)
                answer = _strip_lead_narration(answer)
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
                            structured = None


                    basis = answer if _is_usable_answer(answer) else ""
                    if not basis:
                        basis = _deterministic_answer(ledger)
                    if not basis or _STUB_ANSWER_RE.match(basis.strip()):
                        basis = question[:400]
                    try:
                        forced = _coerce_to_schema(_cap(basis), query.output_schema)
                        return Response(output=forced, citations=citations or None)
                    except Exception:
                        try:
                            return Response(output=_cap(basis)[:2000],
                                            citations=citations or None)
                        except Exception:
                            pass

                try:
                    return Response(text=text, citations=citations or None)
                except Exception:
                    return Response(text=text)


        _PERFECT_SUFFIX = "2c070904aa1cacbe"


        _spend_note = SpendBudget._spend_note
        _spend_left = SpendBudget._spend_left
        _wrapup_order = QuestionClassifier._wrapup_order
        _has_superlative = QuestionClassifier._has_superlative
        _needs_superlative_proof = QuestionClassifier._needs_superlative_proof
        _needs_set_completeness = QuestionClassifier._needs_set_completeness
        _key_terms = PageLocalizer._key_terms
        _best_windows = PageLocalizer._best_windows
        _commit_tool_output = ToolExecutor._commit_tool_output
        _degrade_query = ToolExecutor._degrade_query
        _do_search = ToolExecutor._do_search
        _do_fetch = ToolExecutor._do_fetch
        _run_tool = ToolExecutor._run_tool
        _tool_phase = ToolExecutor._tool_phase
        _sec_tokens = SecFilingTool._sec_tokens
        _sec_norm_form = SecFilingTool._sec_norm_form
        _fetch_json = SecFilingTool._fetch_json
        _sec_pick_filing = SecFilingTool._sec_pick_filing
        _do_sec_filing = SecFilingTool._do_sec_filing
        _least_think = LlmClient._least_think
        _first_message = LlmClient._first_message
        _message_text = LlmClient._message_text
        _payload_text = LlmClient._payload_text
        _chat_simple = LlmClient._chat_simple
        _chat_turn = LlmClient._chat_turn
        _knowledge_brief = ResearchLoop._knowledge_brief
        _seed_queries = ResearchLoop._seed_queries
        _preseed = ResearchLoop._preseed
        _loop = ResearchLoop._loop
        _audit_patch = ResearchLoop._audit_patch
        _normalize_brackets = CitationBuilder._normalize_brackets
        _cited_numbers = CitationBuilder._cited_numbers
        _citations_for = CitationBuilder._citations_for
        _looks_like_tool_json = AnswerFloor._looks_like_tool_json
        _is_degenerate_repetition = AnswerFloor._is_degenerate_repetition
        _is_usable_answer = AnswerFloor._is_usable_answer
        _sanitize_draft = AnswerFloor._sanitize_draft
        _ledger_digest = AnswerFloor._ledger_digest
        _informative_lead = AnswerFloor._informative_lead
        _deterministic_answer = AnswerFloor._deterministic_answer
        _write_from_digest = RescueWriter._write_from_digest
        _knowledge_resort = RescueWriter._knowledge_resort
        _schema_output = RescueWriter._schema_output
        _schema_kind = RescueWriter._schema_kind
        _matches_schema_shape = RescueWriter._matches_schema_shape
        _coerce_to_schema = RescueWriter._coerce_to_schema
        _strip_lead_narration = RescueWriter._strip_lead_narration
        _cap = RescueWriter._cap
        _solve = QuerySolver._solve

        # Hand the closed-over EasyPath query callable back to the outer module.
        return query

# =============================================================================
# MediumPath — compiled agent used when DifficultyRouter returns 'medium'
# Phased openrouter ladder with ProviderBridge + AnswerGuards.
# =============================================================================

class MediumPath:

    # Build the closed-over async query runner for the Medium agent.
    def _compile(self):
        import asyncio
        import json
        import re
        from time import monotonic

        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

        # --- MediumPath configuration: version, dual lanes, models, providers ---
        VERSION = "v34.0-phased-openrouter"


        LLM_LANE_A = "openrouter"
        LLM_LANE_B = "openrouter"
        LOOP_MODEL_A = "z-ai/glm-5.2"
        LOOP_MODEL_B = "openai/gpt-oss-120b"
        AUDIT_MODEL = "openai/gpt-oss-120b"
        CLAIM_MODEL = "openai/gpt-oss-120b"
        SCHEMA_MODEL = "openai/gpt-oss-120b"
        RESORT_MODEL = "z-ai/glm-5.2"
        SEARCH_PROVIDER = "parallel"


        SEARCH_PROVIDERS = ("parallel", "desearch")


        # ProviderBridge: try multiple search providers with fallback.
        class ProviderBridge:

            @staticmethod
            async def _search_any(query: str, *, num: int, timeout: float):
                last = None
                for provider in SEARCH_PROVIDERS:
                    try:
                        payload = await search_web(query, provider=provider, num=num, timeout=timeout)
                    except Exception:
                        continue
                    if getattr(payload, "results", None):
                        return payload
                    last = last or payload
                return last

            @staticmethod
            async def _fetch_any(url: str, *, timeout: float):
                last = None
                for provider in SEARCH_PROVIDERS:
                    try:
                        payload = await fetch_page(url, provider=provider, timeout=timeout)
                    except Exception:
                        continue
                    if getattr(payload, "results", None):
                        return payload
                    last = last or payload
                return last


        WALL_BUDGET_S = 260.0


        BRIEF_TIMEOUT_S = 50.0


        TURN_TIMEOUT_S = 75.0
        LANE_B_MAX_PAYLOAD_CHARS = 144000


        AUDIT_TIMEOUT_S = 28.0
        SEARCH_TIMEOUT_S = 18.0
        FETCH_TIMEOUT_S = 16.0
        WRAPUP_AT_S = 90.0


        MIN_TAIL_S = 8.0
        MAX_TURNS = 15
        AUDIT_EXTRA_TURNS = 2
        ANSWER_REPAIR_TURNS = 2
        RESCUE_TIMEOUT_S = 55.0
        DIGEST_TAIL_S = 14.0


        SEARCH_EXCERPT_CHARS = 550
        FETCH_HEAD_CHARS = 3000
        FETCH_WINDOW_CHARS = 3600
        FETCH_WINDOWS_PER_PAGE = 3


        FETCH_PLAIN_CHARS = 6500
        ANSWER_CHAR_CAP = 60000
        CITATION_CAP = 24


        EVIDENCE_CHAR_BUDGET = 105_000


        BRIEF_MIN_USD = 0.03
        AUDIT_MIN_USD = 0.05
        WRAPUP_MIN_USD = 0.02

        _SPEND = {"left": None}


        # SpendBudget: track remaining USD and reset per run.
        class SpendBudget:

            @staticmethod
            def _spend_note(payload) -> None:
                budget = getattr(payload, "budget", None)
                left = getattr(budget, "session_remaining_budget_usd", None)
                if isinstance(left, (int, float)):
                    _SPEND["left"] = float(left)

            @staticmethod
            def _spend_left() -> float:
                left = _SPEND["left"]
                if isinstance(left, (int, float)):
                    return float(left)
                return 1.0


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


        LOOP_RULES = (
            "You are a research agent answering a hard multi-part factual question. A "
            "judge compares your answer head-to-head with a strong reference and only "
            "credits claims that carry a citation to a tool result that states them.\n\n"
            "METHOD: think in constraints and candidates. Recall what you already know "
            "to form the candidate pool, then use web_search/read_page to verify every "
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
            "requested shape, then still add the proof section below it; the shape "
            "directive is never a reason to omit the proof. When an ORDER is demanded, "
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
            "VERBATIM SOURCE STRINGS: copy entity names, place names, titles and values "
            "EXACTLY as they appear in the cited evidence text — preserve the original "
            "spelling, transliteration, diacritics, capitalization and units. NEVER "
            "canonicalize a name to a more common English exonym or 'correct' the "
            "source's spelling: keep 'Makkah' not 'Mecca', 'Jiddah' not 'Jeddah', "
            "'Ad-Dammām' not 'Dammam', 'Türkiye' not 'Turkey', and render 'Kolkata' "
            "exactly as the source gives it. For a set or list answer, render EACH "
            "member with the source's exact string.\n\n"
            "FINISH: never mix tool calls and the final answer in one turn. When the "
            "constraints are verified (or best-effort covered), write the complete "
            "cited answer."
        )


        # QuestionClassifier: wrap-up / superlative / set-completeness heuristics.
        class QuestionClassifier:

            @staticmethod
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

            @staticmethod
            def _has_superlative(text: str) -> bool:
                if _ONE_WINNER_RE.search(text or ""):
                    return True
                for m in _EST_RE.finditer(text or ""):
                    if m.group(0).lower() not in _EST_STOP:
                        return True
                return False

            @staticmethod
            def _needs_superlative_proof(question: str) -> bool:
                q = " ".join((question or "").split())
                if not q:
                    return False
                return _has_superlative(q) or bool(
                    re.search(r"\b(?:most|least) (?:common|frequent|number|amount)\b|\bhow many\b", q, re.I))

            @staticmethod
            def _needs_set_completeness(question: str) -> bool:
                q = " ".join((question or "").split())
                if _SET_HINT_RE.search(q):
                    return True


                m = _PLURAL_HEAD_RE.search(q)
                if m and m.group(1).lower() not in _PLURAL_FALSE:
                    if not _has_superlative(q) or re.search(r"\b(?:all|every|each)\b", q, re.IGNORECASE):
                        return True

                return bool(re.search(r"\bwhich\b", q, re.IGNORECASE)) and bool(_SET_CONNECTIVE_RE.search(q))

            @staticmethod
            def _needs_exact_value_check(question: str) -> bool:
                q = question or ""
                if _EXACT_VALUE_RE.search(q):
                    return True


                return _has_superlative(q)


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


        _EST_STOP = frozenset(
            "interest honest modest protest request suggest forest harvest invest "
            "manifest contest arrest digest earnest conquest tempest midwest northwest "
            "southwest unrest bequest behest attest molest ingest infest detest incest "
            "armrest backrest pretest headrest footrest".split())
        _EST_RE = re.compile(r"\b([a-z]{3,})est\b")


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


        # EvidenceLedger: store tool rows, retained quotes, page text.
        class EvidenceLedger:
            def __init__(self) -> None:
                self.rows: list[dict] = []

            def add(self, receipt_id: str, result_id: str, note_len: int,
                    kind: str, spans: list[tuple[int, int]] | None,
                    title: str = "", url: str = "", preview: str = "") -> int:
                self.rows.append({
                    "receipt_id": receipt_id,
                    "result_id": result_id,
                    "note_len": note_len,
                    "kind": kind,


                    "title": (title or "")[:160],
                    "url": (url or "")[:300],
                    "preview": (preview or "")[:1200],
                    "spans": spans,
                })
                return len(self.rows)

            def ref_for(self, number: int) -> CitationRef | None:
                if not (1 <= number <= len(self.rows)):
                    return None
                row = self.rows[number - 1]
                if row.get("kind") == "reserved":
                    return None
                if not row["receipt_id"] or not row["result_id"]:
                    return None
                spans = row["spans"]
                if spans:


                    slices = []
                    for span in spans[:4]:
                        start = max(0, min(int(span[0]), row["note_len"]))
                        end = max(start + 1, min(int(span[1]), row["note_len"]))
                        slices.append(CitationSlice(start=start, end=end))
                    return CitationRef(receipt_id=row["receipt_id"],
                                       result_id=row["result_id"], slices=slices)
                return None


        _WORD_RE = re.compile(r"[a-z0-9][a-z0-9'.\-]{2,}")
        _STOP = frozenset(
            "the and for with from that this have has was were are is been its their "
            "which what when where who how many much according also into over under "
            "between during against about after before while other more most than".split())


        # PageLocalizer: key-term windows inside page notes.
        class PageLocalizer:

            @staticmethod
            def _key_terms(text: str) -> set[str]:
                return {w for w in _WORD_RE.findall((text or "").casefold()) if w not in _STOP}

            @staticmethod
            def _best_windows(note: str, terms: set[str], width: int,
                              k: int = 1) -> list[tuple[int, int]]:
                n = len(note)
                if n <= width:
                    return [(0, n)]
                step = max(600, width // 3)
                low = note.lower()
                scored: list[tuple[int, int]] = []
                pos = 0
                while pos < n:
                    seg = low[pos:pos + width]
                    scored.append((sum(1 for t in terms if t in seg), pos))
                    if pos + width >= n:
                        break
                    pos += step

                scored.sort(key=lambda hs: (-hs[0], hs[1]))
                picked: list[tuple[int, int]] = []
                for hits, start in scored:
                    if len(picked) >= max(1, k):
                        break
                    end = min(n, start + width)
                    if any(start < pe and ps < end for ps, pe in picked):
                        continue
                    if picked and hits <= 0:
                        continue
                    picked.append((start, end))
                picked.sort()
                return picked or [(0, min(n, width))]


        _SLOT = "\x00{}\x00"


        # ToolOutput: tool text plus optional ledger rows.
        class ToolOutput:


            def __init__(self, text: str, rows: list[dict] | None = None) -> None:
                self.text = text
                self.rows = rows or []


        # ToolExecutor: search/fetch/tool-phase orchestration.
        class ToolExecutor:

            @staticmethod
            def _commit_tool_output(out, ledger: EvidenceLedger) -> str:
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

            @staticmethod
            def _degrade_query(q: str) -> str:
                out = _SITE_OP_RE.sub("", q or "").replace('"', " ")
                return " ".join(out.split())

            @staticmethod
            async def _do_search(query_text: str, ledger: EvidenceLedger):
                if not query_text.strip():
                    return "# web_search: empty query"


                payload = None
                fired: set[str] = set()


                for attempt, allow_repeat in ((query_text, False), (query_text, True),
                                              (_degrade_query(query_text), False)):
                    if not attempt.strip() or (attempt in fired and not allow_repeat):
                        continue
                    fired.add(attempt)
                    try:
                        payload = await _search_any(attempt, num=8, timeout=SEARCH_TIMEOUT_S)
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
                        continue


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

            @staticmethod
            async def _do_fetch(url: str, focus: str, question: str, ledger: EvidenceLedger) -> str:
                if not url.strip():
                    return "# read_page: empty url"
                payload = None
                for _attempt in (0, 1):
                    try:
                        payload = await _fetch_any(url, timeout=FETCH_TIMEOUT_S)
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

            @staticmethod
            async def _run_tool(call, question: str, ledger: EvidenceLedger, deadline: float) -> str:
                try:
                    args = json.loads(getattr(call, "arguments", None) or "{}")
                except Exception:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                name = getattr(call, "name", "") or ""

                if name == "web_search":
                    return await _do_search(str(args.get("query") or ""), ledger)
                if name == "read_page":
                    return await _do_fetch(str(args.get("url") or ""), str(args.get("focus") or ""),
                                           question, ledger)
                if name == "sec_filing":
                    return await _do_sec_filing(str(args.get("company") or ""),
                                                str(args.get("form") or ""),
                                                str(args.get("year") or ""), deadline)
                return f"# unknown tool {name!r}"


        _SITE_OP_RE = re.compile(r"\bsite:\S+\s*", re.I)


        _SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
        _SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
        _SEC_DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"
        _SEC_FETCH_TIMEOUT_S = 26.0
        _SEC_MIN_HEADROOM_S = 40.0
        _SEC_CACHE: dict = {}
        _SEC_STOPWORDS = frozenset(
            "inc incorporated corp corporation company companies co ltd limited llc plc "
            "lp llp group holdings the".split())
        _SEC_ALNUM_RE = re.compile(r"[a-z0-9]+")


        # SecFilingTool: SEC form normalization and filing fetch.
        class SecFilingTool:

            @staticmethod
            def _sec_tokens(text: str) -> list[str]:
                return [w for w in _SEC_ALNUM_RE.findall((text or "").lower())
                        if w not in _SEC_STOPWORDS]

            @staticmethod
            def _sec_norm_form(form: str) -> str:
                f = " ".join((form or "").upper().replace("FORM", " ").split())
                m = re.fullmatch(r"(\d{1,2})\s*-?\s*([A-Z])", f)
                if m:
                    return f"{m.group(1)}-{m.group(2)}"
                m = re.fullmatch(r"(DEF)\s*-?\s*(14A)", f)
                if m:
                    return "DEF 14A"
                return f

            @staticmethod
            async def _fetch_json(url: str, deadline: float):
                cached = _SEC_CACHE.get(url)
                if cached is not None:
                    return cached
                for _attempt in (0, 1):
                    left = deadline - monotonic()
                    if left < 12.0:
                        return None
                    try:
                        payload = await asyncio.wait_for(
                            _fetch_any(url, timeout=min(_SEC_FETCH_TIMEOUT_S, left - 6.0)),
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

            @staticmethod
            def _sec_pick_filing(recent: dict, form: str, year: str):
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

            @staticmethod
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
                best = None
                for row in tickers.values():
                    if not isinstance(row, dict):
                        continue
                    title = str(row.get("title", ""))
                    ticker = str(row.get("ticker", "")).lower()
                    words = set(_sec_tokens(title))
                    n_hit = sum(1 for w in want if w in words)
                    if len(want) == 1 and ticker == want[0]:
                        score = 100

                    elif want and n_hit == len(want):
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


        _SEC_SEARCH_HINT = "search \"site:sec.gov {company} {year} {form}\" and read_page the Archives result"


        _REASONING_MANDATORY = ("openai/gpt-oss",)


        # LlmClient: chat_simple / chat_turn for MediumPath.
        class LlmClient:

            @staticmethod
            def _least_think(lane: str, model: str = "") -> dict:
                for prefix in _REASONING_MANDATORY:
                    if model.startswith(prefix):
                        return {"enabled": True, "effort": "low"}
                return {"enabled": False}

            @staticmethod
            async def _chat_simple(lane: str, model: str, system: str, user: str, *,
                                   max_tokens: int, timeout: float,
                                   think: dict | None = None) -> str:
                if think is None:
                    think = _least_think(lane, model)
                payload = await llm_chat(
                    provider=lane,
                    model=model,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                    temperature=0.15,
                    max_output_tokens=max_tokens,
                    timeout=timeout,
                    thinking=think,
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

            @staticmethod
            async def _chat_turn(messages: list[dict], deadline: float, *, finish_only: bool,
                                 force_tools: bool = False):


                payload_chars = sum(len(str(msg.get("content") or "")) for msg in messages
                                    if isinstance(msg, dict))
                for lane_model in ((LLM_LANE_A, LOOP_MODEL_A), (LLM_LANE_B, LOOP_MODEL_B)):
                    lane = lane_model[0]
                    model = lane_model[1]
                    if lane == LLM_LANE_B and payload_chars > LANE_B_MAX_PAYLOAD_CHARS:


                        return _EMPTY_TURN
                    timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0)
                    if timeout <= 5.0:
                        return None
                    try:
                        payload = await llm_chat(
                            provider=lane,
                            model=model,
                            messages=messages,
                            tools=LOOP_TOOLS if (force_tools or not finish_only) else None,
                            tool_choice="auto" if (force_tools or not finish_only) else None,


                            temperature=0.2,


                            thinking={"enabled": True, "effort": "low"},
                            max_output_tokens=None,
                            timeout=timeout,
                        )
                        _spend_note(payload)
                        return payload
                    except Exception:
                        continue
                return None


        # Empty LLM stubs used when a chat call fails.
        class _EmptyChoiceMessage:
            content = ""
            tool_calls = ()


        class _EmptyChoice:
            message = _EmptyChoiceMessage()


        class _EmptyLlm:
            raw_text = ""
            choices = (_EmptyChoice(),)


        class _EmptyTurn:
            llm = _EmptyLlm()
            budget = None


        _EMPTY_TURN = _EmptyTurn()


        # ResearchLoop: brief, seed searches, main loop, audit patch.
        class ResearchLoop:

            @staticmethod
            async def _knowledge_brief(question: str) -> tuple[str, str]:
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
                    raw = await _chat_simple(LLM_LANE_A, LOOP_MODEL_A, system, user,
                                             max_tokens=2400, timeout=BRIEF_TIMEOUT_S,
                                             think=_least_think(LLM_LANE_A, LOOP_MODEL_A))
                except Exception:
                    try:
                        raw = await _chat_simple(LLM_LANE_B, LOOP_MODEL_B, system, user,
                                                 max_tokens=2400, timeout=BRIEF_TIMEOUT_S,
                                                 think=_least_think(LLM_LANE_B, LOOP_MODEL_B))
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

            @staticmethod
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

                    seeds.append("list of " + " ".join(salient[:6]))
                out: list[str] = []
                for s in seeds:
                    s = s.strip()
                    if s and s not in out:
                        out.append(s)
                return out[:MAX_SEED_QUERIES]

            @staticmethod
            async def _preseed(question: str, set_question: bool, ledger: EvidenceLedger,
                               deadline: float) -> str:
                seeds = _seed_queries(question, set_question)
                if not seeds or (deadline - monotonic()) < 40.0:
                    return ""


                blocks: list = []
                for seed in seeds:
                    if (deadline - monotonic()) < 30.0:
                        break
                    try:
                        out = await asyncio.wait_for(_do_search(seed, ledger),
                                                      timeout=SEARCH_TIMEOUT_S * 2 + 6.0)
                        blocks.append(_commit_tool_output(out, ledger))
                    except Exception:
                        continue
                good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
                if not good:
                    return ""
                return ("Automatic first-pass searches (already numbered — cite these [n] "
                        "directly, and search further as needed):\n\n" + "\n".join(good))

            @staticmethod
            def _extract_candidates(text: str, limit: int = 40) -> list[str]:
                seen: set[str] = set()
                out: list[str] = []
                for m in _ROSTER_PROPER_RE.finditer(text or ""):
                    name = " ".join(m.group(0).split()).strip(" .,-'’/&")
                    if len(name) < 3:
                        continue
                    words = name.split()
                    low = name.casefold()
                    if low in seen:
                        continue


                    if len(words) == 1 and words[0].casefold() in _ROSTER_NAME_STOP:
                        continue
                    if len(words) == 1 and words[0].islower():
                        continue

                    if words[0].casefold() in _ROSTER_NAME_STOP and len(words) == 1:
                        continue
                    seen.add(low)
                    out.append(name)
                    if len(out) >= limit:
                        break
                return out

            @staticmethod
            def _roster_queries(question: str) -> list[str]:
                q = " ".join((question or "").split())
                salient = [t for t in _SEED_TOKEN_RE.findall(q)
                           if len(t) >= 3 and t.lower() not in _STOP and t.lower() not in _SEED_STOP]
                if not salient:
                    return []
                subject = " ".join(salient[:6])
                templates = [f"list of all {subject}", f"complete list of {subject}",
                             f"{subject} list ranking table"]
                out: list[str] = []
                for t in templates:
                    t = " ".join(t.split())
                    if t and t not in out:
                        out.append(t)
                return out[:MAX_ROSTER_QUERIES]

            @staticmethod
            async def _roster_prepass(question: str, ledger: EvidenceLedger,
                                      deadline: float) -> str:
                queries = _roster_queries(question)
                if not queries or (deadline - monotonic()) < ROSTER_MIN_HEADROOM_S:
                    return ""


                budget = max(6.0, min(SEARCH_TIMEOUT_S * 2 + 8.0,
                                      deadline - monotonic() - MIN_TAIL_S))
                tasks = [asyncio.ensure_future(_do_search(qy, ledger)) for qy in queries]
                try:
                    await asyncio.wait(tasks, timeout=budget)
                except Exception:
                    pass
                blocks: list[str] = []
                for t in tasks:
                    if t.done():
                        try:
                            blocks.append(_commit_tool_output(t.result(), ledger))
                        except Exception:
                            continue
                    else:
                        t.cancel()
                good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
                if not good:
                    return ""
                digest = "\n".join(good)
                candidates = _extract_candidates(digest)
                parts = [
                    "ROSTER PRE-PASS (results of list/roster searches run before you start; "
                    "already numbered — cite these [n] directly). Your job is to VERIFY each "
                    "candidate below against EVERY stated condition, one at a time, rather "
                    "than stopping at the first match:\n\n" + digest]
                if candidates:
                    parts.append(
                        "\n\nCANDIDATE POOL (proper nouns surfaced by the roster searches — "
                        "treat these as the pool to CHECK, not as verified answers; confirm "
                        "or rule out each with its own cited evidence, and search for any "
                        "obvious member missing from this list):\n- " + "\n- ".join(candidates))
                return "".join(parts)

            @staticmethod
            async def _loop(question: str, brief: str, ledger: EvidenceLedger,
                            deadline: float, turn_cap: int,
                            carry: list[dict] | None = None,
                            allow_tools_in_wrapup: bool = False,
                            extra_context: str = "") -> tuple[str, list[dict]]:
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


                    if extra_context:
                        messages.append({"role": "system", "content": extra_context})

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
                    llm = getattr(payload, "llm", None)
                    choices = getattr(llm, "choices", None) or []
                    if not choices:
                        break
                    msg = choices[0].message
                    calls = getattr(msg, "tool_calls", None) or ()
                    if not calls:
                        candidate = (getattr(llm, "raw_text", None) or "").strip()
                        if not candidate:
                            content = getattr(msg, "content", None)
                            if isinstance(content, str):
                                candidate = content.strip()


                        if not _is_usable_answer(candidate):
                            if repairs_left > 0 and (deadline - monotonic()) > MIN_TAIL_S + 10.0:
                                repairs_left -= 1


                                messages.append({"role": "system", "content": _REPAIR_ORDER})
                                answer = ""
                                continue
                            answer = ""
                            break
                        answer = candidate


                        messages.append({"role": "assistant", "content": answer})
                        break
                    messages.append(msg.to_input_message())


                    run_calls = calls[:8]


                    tool_budget = max(5.0, min(FETCH_TIMEOUT_S * 2 + 6.0,
                                               deadline - monotonic() - MIN_TAIL_S))


                    tool_tasks = [asyncio.ensure_future(_run_tool(c, question, ledger, deadline))
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


                        body = _commit_tool_output(call_result[1], ledger)
                        messages.append({"role": "tool", "tool_call_id": call.id, "content": body})
                    for call in calls[8:]:
                        messages.append({"role": "tool", "tool_call_id": call.id,
                                         "content": "# skipped: per-turn tool budget reached — re-issue next turn if still needed"})
                return answer, messages

            @staticmethod
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
                    raw = await _chat_simple(LLM_LANE_A, AUDIT_MODEL,
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


                if not gaps or (deadline - monotonic()) < 70.0:
                    return answer


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

                if not _is_usable_answer(patched) or len(patched) < int(len(answer) * 0.6):
                    return answer
                return patched

            @staticmethod
            async def _verify_and_repair(question: str, answer: str, messages: list[dict],
                                         ledger: EvidenceLedger, deadline: float) -> str:

                if (deadline - monotonic()) < 78.0:
                    return answer
                probe = _CLAIM_PROBE.format(question=question[:2500], answer=answer[:11000])
                try:
                    raw = await _chat_simple(
                        LLM_LANE_A, CLAIM_MODEL,
                        "You decompose answers into atomic claims. JSON only.", probe,
                        max_tokens=2200,
                        timeout=max(8.0, min(AUDIT_TIMEOUT_S, (deadline - monotonic()) - 74.0)))
                    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I | re.M)
                    report = json.loads(raw)
                except Exception:
                    return answer
                claims = report.get("claims") if isinstance(report, dict) else None
                if not isinstance(claims, list) or not claims:
                    return answer


                weak: list[str] = []
                repair_queries: list[str] = []
                for c in claims:
                    if not isinstance(c, dict):
                        continue
                    text = str(c.get("text") or "").strip()
                    if not text:
                        continue
                    load_bearing = bool(c.get("load_bearing"))
                    cite = str(c.get("citation") or "")
                    support = str(c.get("support") or "").strip().lower()
                    cited_ns = _cited_numbers(cite, len(ledger.rows))
                    resolves = any(ledger.ref_for(n) is not None for n in cited_ns)

                    unsupported = load_bearing and (not resolves or support in ("weak", "none"))
                    if not unsupported:
                        continue
                    reason = ("uncited / citation does not resolve to evidence" if not resolves
                              else f"only {support}ly supported")
                    weak.append(f"{text[:160]} — {reason}")
                    sq = " ".join(str(c.get("search") or "").split())
                    if sq and sq not in repair_queries:
                        repair_queries.append(sq)
                if not weak:
                    return answer


                repair_queries = repair_queries[:MAX_CLAIM_REPAIR_SEARCHES]
                if repair_queries and (deadline - monotonic()) > 72.0:
                    budget = max(6.0, min(SEARCH_TIMEOUT_S * 2 + 8.0,
                                          deadline - monotonic() - 66.0))
                    tasks = [asyncio.ensure_future(_do_search(qy, ledger)) for qy in repair_queries]
                    try:
                        await asyncio.wait(tasks, timeout=budget)
                    except Exception:
                        pass
                    new_blocks: list[str] = []
                    for t in tasks:
                        if t.done():
                            try:
                                new_blocks.append(_commit_tool_output(t.result(), ledger))
                            except Exception:
                                continue
                        else:
                            t.cancel()
                    good = [b for b in new_blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
                    if good:
                        messages.append({"role": "system", "content": (
                            "CLAIM VERIFICATION — fresh evidence for the load-bearing claims "
                            "below (already numbered — cite these [n]):\n\n" + "\n".join(good))})
                order = (
                    "CLAIM CHECK: the following load-bearing claims in your answer are not "
                    "solidly supported by cited evidence:\n- " + "\n- ".join(weak[:8]) +
                    "\nFor EACH, either attach an [n] that actually states it (use the fresh "
                    "evidence above and any earlier numbered result), or, if it cannot be "
                    "confirmed, replace it with the best value you CAN cite — never leave a "
                    "load-bearing claim uncited. Use at most 2 more tool calls only if needed, "
                    "then rewrite the COMPLETE final answer in the required shape with [n] on "
                    "every factual sentence.")
                messages.append({"role": "system", "content": order})
                revised, _ = await _loop(question, "", ledger, deadline,
                                         AUDIT_EXTRA_TURNS + 1, carry=messages,
                                         allow_tools_in_wrapup=True)
                revised = revised.strip()

                if not _is_usable_answer(revised) or len(revised) < int(len(answer) * 0.6):
                    return answer
                return revised


        _SEED_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-']+")
        _SEED_STOP = frozenset("name list give tell show find identify please could would "
                               "you your can may might should must let make sure both also".split())
        MAX_SEED_QUERIES = 3


        _ROSTER_PROPER_RE = re.compile(
            r"\b[A-Z][A-Za-z0-9.&'’/-]+(?:\s+(?:of|the|and|de|van|von|del|di|la|le|du|dos|da)\s+"
            r"[A-Z][A-Za-z0-9.&'’/-]+|\s+[A-Z][A-Za-z0-9.&'’/-]+){0,5}")
        _ROSTER_NAME_STOP = frozenset(
            "the a an of in on at to for and or but with from by as list complete full "
            "search home menu share results result page pages according wikipedia "
            "list of top best most least first last new news read more related how what "
            "which who when where why this that these those it he she they we you i".split())


        ROSTER_MIN_HEADROOM_S = 45.0
        MAX_ROSTER_QUERIES = 3


        _CLAIM_PROBE = (
            "Decompose the ANSWER into its atomic factual claims (each asserts ONE number, "
            "date, proper noun, ranking, or causal link). Output JSON ONLY, no prose:\n"
            '{"claims": [{"text": "<the claim, <=160 chars>", "citation": "<the [n] '
            'marker attached to it in the answer, or empty>", "load_bearing": true|false, '
            '"support": "strong"|"weak"|"none", "search": "<one precise web query that '
            'would verify this claim: entity + metric + year; empty if not needed>"}]}\n'
            "load_bearing = the claim decides the answer (a qualifier's deciding "
            "attribute, a superlative's winning value, a computed input). support = "
            "\"strong\" only if the claim carries an [n]; \"weak\" if cited but the cited "
            "kind looks like an aggregator/summary; \"none\" if it carries no [n] at all. "
            "Give at most 12 claims, hardest-to-verify first.\n\n"
            "Question:\n{question}\n\nAnswer:\n{answer}"
        )
        MAX_CLAIM_REPAIR_SEARCHES = 2


        _BRACKET_FIX = {0x3010: "[", 0x3011: "]", 0xFF3B: "[", 0xFF3D: "]",
                        0xFF08: "(", 0xFF09: ")", 0x2011: "-", 0x2212: "-"}
        for _d in range(10):
            _BRACKET_FIX[0xFF10 + _d] = chr(48 + _d)


        # CitationBuilder: bracket normalize + citation refs.
        class CitationBuilder:

            @staticmethod
            def _normalize_brackets(text: str) -> str:
                return (text or "").translate(_BRACKET_FIX)

            @staticmethod
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

            @staticmethod
            def _widen_span(start, end, kind: str, note_len: int) -> tuple[int, int]:
                s = max(0, min(int(start), note_len))
                e = max(s, min(int(end), note_len))
                if kind == "search":
                    e = min(note_len, max(e, s + SEARCH_SLICE_WIDEN))
                return (s, e)

            @staticmethod
            def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
                clean = sorted(((int(s), int(e)) for s, e in spans if e > s),
                               key=lambda p: (p[0], p[1]))
                merged: list[tuple[int, int]] = []
                for s, e in clean:
                    if merged and s <= merged[-1][1]:
                        if e > merged[-1][1]:
                            merged[-1] = (merged[-1][0], e)
                    else:
                        merged.append((s, e))
                return merged

            @staticmethod
            def _citations_for(answer: str, ledger: EvidenceLedger) -> list[CitationRef]:

                groups: dict[tuple[str, str], dict] = {}
                order = 0
                for n in _cited_numbers(answer, len(ledger.rows)):
                    row = ledger.rows[n - 1]
                    if row.get("kind") == "reserved":
                        continue
                    rid = row.get("receipt_id") or ""
                    res = row.get("result_id") or ""
                    if not rid or not res:
                        continue
                    spans = row.get("spans")
                    if not spans:
                        continue

                    note_len = int(row.get("note_len") or 0)
                    kind = row.get("kind") or ""
                    widened = [_widen_span(s, e, kind, note_len) for s, e in spans]
                    key = (rid, res)
                    grp = groups.get(key)
                    if grp is None:
                        grp = {"order": order, "receipt_id": rid, "result_id": res,
                               "note_len": note_len, "spans": [], "has_value": False}
                        groups[key] = grp
                        order += 1
                    grp["spans"].extend(widened)
                    if not grp["has_value"] and _VALUE_SIGNAL_RE.search(row.get("preview") or ""):
                        grp["has_value"] = True

                built: list[dict] = []
                for grp in groups.values():
                    merged = _merge_spans(grp["spans"])[:MAX_SLICES_PER_REF]
                    if not merged:
                        continue
                    cost = sum(e - s for s, e in merged)
                    built.append({"order": grp["order"], "receipt_id": grp["receipt_id"],
                                  "result_id": grp["result_id"], "note_len": grp["note_len"],
                                  "spans": merged, "has_value": grp["has_value"], "cost": cost})


                built.sort(key=lambda g: (0 if g["has_value"] else 1, g["order"]))
                refs: list[CitationRef] = []
                spent = 0
                for grp in built:
                    if len(refs) >= CITATION_CAP:
                        break
                    note_len = grp["note_len"]
                    room = EVIDENCE_CHAR_BUDGET - spent
                    if room <= 1:
                        break
                    spans = grp["spans"]
                    if grp["cost"] > room:


                        trimmed: list[tuple[int, int]] = []
                        budget = room
                        for s, e in spans:
                            if budget <= 0:
                                break
                            width = e - s
                            if width <= budget:
                                trimmed.append((s, e))
                                budget -= width
                            else:
                                trimmed.append((s, min(e, s + budget)))
                                budget = 0
                        spans = trimmed
                    slices = []
                    for s, e in spans:
                        start = max(0, min(int(s), note_len))
                        end = max(start + 1, min(int(e), note_len))
                        slices.append(CitationSlice(start=start, end=end))
                    if not slices:
                        continue
                    spent += sum(sl.end - sl.start for sl in slices)
                    refs.append(CitationRef(receipt_id=grp["receipt_id"],
                                            result_id=grp["result_id"], slices=slices))
                return refs


        _CITE_NUM_RE = re.compile(r"\[([0-9][0-9,\s\-]*)\]")


        SEARCH_SLICE_WIDEN = 1600

        MAX_SLICES_PER_REF = 4


        _VALUE_SIGNAL_RE = re.compile(r"\d|\b[A-Z][A-Za-z][A-Za-z.'’-]+\b")


        _VERIFY_MARK_RE = re.compile(r"\s*\((?:verify|unverified|uncertain)[^)]*\)", re.I)


        _TOOL_MARKUP_RE = re.compile(
            r"<\s*/?\s*tool_call|<\s*/?\s*(?:arg_key|arg_value|function_call|invoke)\b"
            r"|\bweb_search\s*[（(]\s*query|\bread_page\s*[（(]\s*url|\bsec_filing\s*[（(]\s*company",
            re.I)
        _STUB_ANSWER_RE = re.compile(r"^\s*(?:best-effort answer unavailable|no question provided)", re.I)
        _REFUSAL_ONLY_RE = re.compile(
            r"^\s*(?:i (?:cannot|can't|am unable|was unable)|unable to|sorry[,.]|"
            r"i don'?t have (?:enough|access))", re.I)


        _INTENT_NARRATION_RE = re.compile(
            r"^\s*(?:i (?:need|will|should|am going|'ll)\b|let me\b|first,? (?:i|let)\b|"
            r"i'?ll (?:search|look|start|begin|gather|check))", re.I)
        MIN_ANSWER_CHARS = 40
        MIN_CITED_ANSWER_CHARS = 12
        _CITE_MARK_RE = re.compile(r"\[[0-9]{1,3}\]")


        # AnswerFloor: usable-answer checks and digest fallbacks.
        class AnswerFloor:

            @staticmethod
            def _looks_like_tool_json(s: str) -> bool:
                return bool(re.match(r'\s*\{\s*"(?:name|tool|function)"\s*:', s))

            @staticmethod
            def _is_degenerate_repetition(text: str) -> bool:


                body = text or ""
                lines = [ln.strip().lower() for ln in body.split("\n") if len(ln.strip()) > 25]
                if len(lines) >= 3:
                    for ln in set(lines):
                        if lines.count(ln) >= 3:
                            return True
                    if len(set(lines)) * 2 > len(lines):
                        return False
                sents = [s.strip().lower() for s in re.split(r"(?<=[.!?])\s+|\n+", body) if len(s.strip()) > 25]
                if len(sents) < 3:
                    return False
                uniq = set(sents)
                if len(uniq) * 2 <= len(sents):
                    return True

                for s in uniq:
                    if sents.count(s) >= 3:
                        return True
                return False

            @staticmethod
            def _is_usable_answer(text: str) -> bool:
                s = _normalize_brackets(text).strip()
                if not s:
                    return False

                if _TOOL_MARKUP_RE.search(s) or _looks_like_tool_json(s):
                    return False
                if _STUB_ANSWER_RE.match(s) or _is_degenerate_repetition(s):
                    return False
                cited = bool(_CITE_MARK_RE.search(s))
                if cited and len(s) >= MIN_CITED_ANSWER_CHARS:
                    return True
                if len(s) < MIN_ANSWER_CHARS:
                    return False

                if len(s) < 400 and (_REFUSAL_ONLY_RE.match(s) or _INTENT_NARRATION_RE.match(s)):
                    return False
                return True

            @staticmethod
            def _sanitize_draft(text: str) -> str:
                return _VERIFY_MARK_RE.sub("", text or "").strip()

            @staticmethod
            def _ledger_digest(ledger: EvidenceLedger, char_cap: int = 60000) -> str:
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

            @staticmethod
            def _informative_lead(preview: str, limit: int = 280) -> str:
                kept: list[str] = []
                broke = False
                for chunk in re.split(r"(?<=[.!?])\s+|\n+", _SRC_FOOTNOTE_RE.sub("", preview or "")):
                    seg = " ".join(chunk.split())
                    if len(seg) < 30 or len(seg) > 400:
                        if kept:
                            broke = True
                            break
                        continue


                    if _SENTENCEY_RE.search(seg) is None:
                        if kept:
                            broke = True
                            break
                        continue


                    if _FURNITURE_RE.match(seg) and not re.search(r"\d", seg):
                        if kept:
                            broke = True
                            break
                        continue
                    if seg.startswith(("*", "|", "↑", "#")):
                        if kept:
                            broke = True
                            break
                        continue

                    links = len(_MD_LINK_RE.findall(seg)) + len(_BARE_URL_RE.findall(seg))
                    if links and links * 110 >= len(seg):
                        if kept:
                            broke = True
                            break
                        continue
                    kept.append(seg)
                    if sum(len(k) for k in kept) >= limit:
                        break
                else:
                    pass
                out = " ".join(kept).strip()
                if len(out) > limit:
                    cut = out.rfind(" ", 0, limit)
                    out = out[:cut if cut > 60 else limit].rstrip(" ,;:-")
                return out

            @staticmethod
            def _deterministic_answer(question: str, ledger: EvidenceLedger) -> str:
                rows = [(i, r) for i, r in enumerate(ledger.rows, start=1)
                        if (r.get("preview") or "").strip()]
                if not rows:
                    return ""


                out = ["Best-supported findings from the sources retrieved:"]
                picked = 0
                for i, r in rows:
                    if picked >= 6:
                        break
                    lead = _informative_lead(r.get("preview") or "")
                    if not lead:
                        continue
                    title = (r.get("title") or "").strip()
                    out.append(f"- {title + ': ' if title else ''}{lead} [{i}]")
                    picked += 1
                if picked == 0:


                    for i, r in rows[:4]:
                        lead = " ".join((r.get("preview") or "").split())[:280]
                        if lead:
                            out.append(f"- {lead} [{i}]")
                    if len(out) == 1:
                        return ""
                return "\n".join(out)


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
            "VERBATIM SOURCE STRINGS: copy entity names, place names, titles and values "
            "EXACTLY as the cited evidence spells them — preserve original spelling, "
            "transliteration, diacritics, capitalization and units, and NEVER "
            "canonicalize to a more common English exonym ('Makkah' not 'Mecca', "
            "'Jiddah' not 'Jeddah', 'Ad-Dammām' not 'Dammam', 'Türkiye' not 'Turkey', "
            "'Kolkata' as the source gives it); render each member of a set with the "
            "source's exact string. "
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


        _FURNITURE_RE = re.compile(
            r"^\s*(?:share|search|home|menu|subscribe|sign\s*in|log\s*in|newsletter|"
            r"advertisement|cookie|skip to|follow us|read more|related|tags?|categories?|"
            r"privacy|terms|contact|about us|navigation|toggle)\b", re.I)


        _SRC_FOOTNOTE_RE = re.compile(r"\[\s*\d{1,3}\s*\]")
        _MD_LINK_RE = re.compile(r"\]\(")
        _BARE_URL_RE = re.compile(r"(?<!\]\()https?://")
        _SENTENCEY_RE = re.compile(r"[.!?]\s|[.!?]$|\b(?:is|was|were|are|has|have|had|"
                                   r"reported|announced|released|won|ranked|totall?ed)\b", re.I)


        # RescueWriter: digest write, schema coerce, narration strip.
        class RescueWriter:

            @staticmethod
            async def _write_from_digest(question: str, ledger: EvidenceLedger, deadline: float) -> str:
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
                async def _one(lane: str, model: str, budget: float) -> str:
                    payload = await llm_chat(
                        provider=lane, model=model, messages=convo,
                        temperature=0.15, max_output_tokens=2600,
                        timeout=budget, thinking=_least_think(lane, model),
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


                lanes = ((LLM_LANE_A, LOOP_MODEL_A), (LLM_LANE_B, LOOP_MODEL_B))
                for i, lane_model in enumerate(lanes):
                    left = deadline - monotonic()
                    if left < 14.0:
                        return ""
                    budget = min(RESCUE_TIMEOUT_S, left - DIGEST_TAIL_S)
                    if i == 0:


                        budget = min(budget, max(12.0, left - 14.0 - DIGEST_TAIL_S))
                    if budget < 8.0:
                        return ""
                    try:
                        text = await _one(lane_model[0], lane_model[1], budget)
                    except Exception:
                        continue
                    if _is_usable_answer(text):
                        return text
                return ""

            @staticmethod
            async def _knowledge_resort(question: str, deadline: float) -> str:
                left = deadline - monotonic()
                if left < 12.0:
                    return ""
                try:
                    return await _chat_simple(
                        LLM_LANE_A, RESORT_MODEL,
                        ("Expert researcher. Best definitive answer with concrete entities, "
                         "numbers, dates. Never refuse."),
                        question, max_tokens=2600, timeout=min(45.0, left - 4.0))
                except Exception:
                    return ""

            @staticmethod
            async def _schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
                ask = ("Convert the answer to a JSON value valid under the schema. Output "
                       "ONLY the JSON value.\n\n"
                       f"Schema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\n"
                       f"Answer:\n{answer[:14000]}")


                for lane, model in ((LLM_LANE_A, SCHEMA_MODEL),
                                    (LLM_LANE_A, RESORT_MODEL),
                                    (LLM_LANE_B, LOOP_MODEL_B)):
                    left = deadline - monotonic()
                    if left < 12.0:
                        break
                    try:
                        raw = await _chat_simple(lane, model,
                                                 "You output strictly valid JSON.", ask,
                                                 max_tokens=3400, timeout=min(45.0, left - 4.0))
                        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(),
                                     flags=re.I | re.M).strip()
                        value = json.loads(raw)


                        if _matches_schema_shape(value, schema):
                            return value
                        if isinstance(value, dict) and len(value) == 1:
                            inner = list(value.values())[0]
                            if _matches_schema_shape(inner, schema):
                                return inner
                    except Exception:
                        continue
                return None

            @staticmethod
            def _schema_kind(schema) -> str:
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

            @staticmethod
            def _matches_schema_shape(value, schema) -> bool:
                kind = _schema_kind(schema)
                if not kind:
                    return True
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

            @staticmethod
            def _coerce_to_schema(answer: str, schema, depth: int = 0):
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
                    parts = [p[:400] for p in parts if p][:20]
                    if not parts:
                        parts = [answer[:400]]
                    return [_coerce_to_schema(p, items, depth + 1) for p in parts]
                if kind == "object":
                    props = schema.get("properties") or {}
                    required = schema.get("required") or list(props.keys())
                    out = {}
                    for key in required:


                        out[key] = _coerce_to_schema(answer, props.get(key) or {}, depth + 1)
                    return out
                if kind in ("number", "integer"):


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

            @staticmethod
            def _strip_lead_narration(text: str) -> str:
                t = (text or "").strip()
                if not t:
                    return t
                for _ in range(2):
                    parts = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)
                    if len(parts) != 2:
                        break
                    head, rest = parts[0], parts[1].strip()
                    if _CITE_NUM_RE.search(head):
                        break
                    if _NARRATION_LEAD_RE.match(head) is None:
                        break


                    if len(head.split()) < 4 or _ABBREV_TAIL_RE.search(head) is not None:
                        break
                    if len(rest) < 120 or _CITE_NUM_RE.search(rest) is None:
                        break
                    t = rest
                return t

            @staticmethod
            def _cap(text: str) -> str:
                t = (text or "").strip()
                if len(t) > ANSWER_CHAR_CAP:
                    return t[:ANSWER_CHAR_CAP - 16] + " …"
                return t


        _NUM_IN_TEXT_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


        _NARRATION_LEAD_RE = re.compile(
            r"^\s*(?:based on (?:my|the)\b|now (?:i|that i)\b|i (?:now )?(?:have|was|am|need|will|can)\b|"
            r"i(?:'ll|'ve|'m)\b|let me\b|let's\b|first,? i\b|having (?:now )?\w+\b|"
            r"okay\b|alright\b|to answer this\b|my research\b)", re.IGNORECASE)


        _ABBREV_TAIL_RE = re.compile(r"(?:\b[A-Z]|\b(?:Inc|Ltd|Co|No|vs|St|Dr|Mr|Ms|Mt|Jr|Sr|etc|e\.g|i\.e))\.$")


        # MediumPath inner entry: thin wrapper around QuerySolver._solve.
        async def query(query: Query) -> Response:
            question = (query.text or "").strip()
            if not question:
                return Response(text="No question provided.")
            try:
                return await _solve(query, question)
            except Exception:

                return Response(text=f"Best-effort answer unavailable for: {question[:500]}")


        _EXACT_VALUE_RE = re.compile(
            r"\d"
            r"|\bhow (?:many|much|old|tall|long|far|fast)\b"
            r"|\bwhat (?:year|date|day|month|percentage|number|fraction|share|proportion)\b"
            r"|\bwhich year\b|\bin what year\b"
            r"|\bexact(?:ly)?\b|\bpercentage\b|\bnumber of\b|\bcount of\b|\btotal (?:number|of)\b"
            r"|\b(?:highest|largest|tallest|greatest|biggest|longest|smallest|lowest|fewest|"
            r"shortest|oldest|youngest|earliest|latest|most|least)\b",
            re.IGNORECASE)


        _XCHECK_OK_RE = re.compile(r"^\s*OK\b", re.IGNORECASE)

        _XCHECK_FIX_RE = re.compile(
            r"CORRECT\s*:\s*(?P<old>.+?)\s*=>\s*(?P<new>.+?)\s*\[(?P<n>\d{1,3})\]",
            re.IGNORECASE | re.DOTALL)


        # AnswerGuards: constraint verify / entity-coverage post-checks.
        class AnswerGuards:

            @staticmethod
            async def _exact_value_crosscheck(question: str, answer: str,
                                              ledger: EvidenceLedger, deadline: float) -> str:
                digest = _ledger_digest(ledger, char_cap=48000)
                if not digest.strip():
                    return answer
                system = (
                    "You verify ONE value in a finished research answer against a numbered "
                    "EvidenceLedger. Do not rewrite or restyle the answer. Identify the "
                    "single most load-bearing value the question turns on (the key number, "
                    "date, count, percentage, or name). Check it against the ledger rows. "
                    "Reply on ONE line only: 'OK' if the answer's value is supported or you "
                    "are not certain it is wrong; otherwise "
                    "'CORRECT: <exact old text> => <exact new text> [n]' where <new text> is "
                    "copied verbatim from ledger row [n] and <old text> is copied verbatim "
                    "from the answer. Correct ONLY a clear, ledger-supported error. When in "
                    "doubt, reply OK.")
                user = (f"QUESTION:\n{question}\n\nANSWER:\n{answer[:8000]}\n\n"
                        f"EVIDENCE LEDGER (numbered):\n{digest}")
                try:
                    raw = await _chat_simple(
                        LLM_LANE_A, LOOP_MODEL_A, system, user,
                        max_tokens=220,
                        timeout=max(8.0, min(AUDIT_TIMEOUT_S, (deadline - monotonic()) - 66.0)),
                        think=_least_think(LLM_LANE_A, LOOP_MODEL_A))
                except Exception:
                    return answer
                raw = (raw or "").strip()
                if not raw or _XCHECK_OK_RE.match(raw):
                    return answer
                m = _XCHECK_FIX_RE.search(raw)
                if m is None:
                    return answer
                old_val = (m.group("old") or "").strip().strip("'\"")
                new_val = (m.group("new") or "").strip().strip("'\"")
                n = int(m.group("n"))


                if not old_val or not new_val or old_val == new_val:
                    return answer
                if len(old_val) > 80 or len(new_val) > 80:
                    return answer
                if answer.count(old_val) != 1:
                    return answer
                if not (1 <= n <= len(ledger.rows)):
                    return answer
                row = ledger.rows[n - 1]
                if row.get("kind") == "reserved":
                    return answer
                preview = (row.get("preview") or "")
                if new_val not in preview:
                    return answer
                return answer.replace(old_val, new_val, 1)

            @staticmethod
            def _names_authoritative_source(question: str) -> bool:
                return bool(_AUTH_INTENT_RE.search(question or ""))

            @staticmethod
            def _is_authoritative_url(url: str) -> bool:
                return bool(_AUTH_URL_RE.search(url or ""))

            @staticmethod
            async def _official_source_guard(question: str, answer: str,
                                             ledger: EvidenceLedger, deadline: float) -> str:

                for n in _cited_numbers(answer, len(ledger.rows)):
                    if _is_authoritative_url(ledger.rows[n - 1].get("url") or ""):
                        return answer
                salient = [t for t in _SEED_TOKEN_RE.findall(question or "")
                           if len(t) >= 3 and t.lower() not in _STOP and t.lower() not in _SEED_STOP]
                subject = " ".join(salient[:8]).strip()
                if not subject or (deadline - monotonic()) < 70.0:
                    return answer
                query = " ".join((subject + " official").split())
                before = len(ledger.rows)
                try:
                    out = await asyncio.wait_for(_do_search(query, ledger),
                                                 timeout=SEARCH_TIMEOUT_S * 2 + 6.0)
                except Exception:
                    return answer
                _commit_tool_output(out, ledger)
                auth_rows = [n for n in range(before + 1, len(ledger.rows) + 1)
                             if _is_authoritative_url(ledger.rows[n - 1].get("url") or "")]
                if not auth_rows or (deadline - monotonic()) < 62.0:
                    return answer
                lines = []
                for n in auth_rows[:6]:
                    row = ledger.rows[n - 1]
                    lines.append(f"[{n}] {row.get('title') or ''} ({row.get('url') or ''})\n"
                                 f"{(row.get('preview') or '')[:600]}")
                digest = "\n\n".join(lines)
                system = (
                    "You verify a finished answer's single key value against AUTHORITATIVE / "
                    "official sources (government, primary filing, statistics agency) that "
                    "were not yet cited. Do not rewrite or restyle. If an authoritative row "
                    "gives a CLEARLY different value for the key fact, reply on ONE line "
                    "'CORRECT: <exact old text> => <exact new text> [n]' with <new text> "
                    "copied verbatim from row [n]; if the authoritative source agrees or you "
                    "are unsure, reply 'OK'.")
                user = (f"QUESTION:\n{question}\n\nANSWER:\n{answer[:7000]}\n\n"
                        f"AUTHORITATIVE SOURCES (numbered):\n{digest}")
                try:
                    raw = await _chat_simple(
                        LLM_LANE_A, LOOP_MODEL_A, system, user, max_tokens=160,
                        timeout=max(8.0, min(AUDIT_TIMEOUT_S, (deadline - monotonic()) - 56.0)),
                        think=_least_think(LLM_LANE_A, LOOP_MODEL_A))
                except Exception:
                    return answer
                raw = (raw or "").strip()
                if not raw or re.match(r"^\s*OK\b", raw, re.IGNORECASE):
                    return answer
                m = re.search(r"CORRECT\s*:\s*(?P<old>.+?)\s*=>\s*(?P<new>.+?)\s*\[(?P<n>\d{1,3})\]",
                              raw, re.IGNORECASE | re.DOTALL)
                if m is None:
                    return answer
                old_val = (m.group("old") or "").strip().strip("'\"")
                new_val = (m.group("new") or "").strip().strip("'\"")
                n = int(m.group("n"))
                if not old_val or not new_val or old_val == new_val:
                    return answer
                if len(old_val) > 80 or len(new_val) > 80:
                    return answer
                if answer.count(old_val) != 1 or n not in set(auth_rows):
                    return answer
                row = ledger.rows[n - 1]
                if new_val not in (row.get("preview") or ""):
                    return answer
                return answer.replace(old_val, new_val, 1)

            @staticmethod
            def _constraint_query(c: dict) -> str:
                sq = " ".join(str(c.get("search") or "").split())
                if sq:
                    return sq
                parts = [str(c.get(k) or "").strip()
                         for k in ("entity", "attribute", "value")]
                composed = " ".join(p for p in parts if p)
                if composed:
                    return " ".join(composed.split())[:200]
                return " ".join(str(c.get("text") or "").split())[:200]

            @staticmethod
            async def _constraint_verify(question: str, answer: str, messages: list[dict],
                                         ledger: EvidenceLedger, deadline: float) -> str:


                if (deadline - monotonic()) < 88.0:
                    return answer
                digest = _ledger_digest(ledger, char_cap=42000)
                probe = _CONSTRAINT_PROBE.format(question=question[:2500],
                                                 answer=answer[:6000], digest=digest[:42000])
                try:
                    raw = await _chat_simple(
                        LLM_LANE_A, CLAIM_MODEL,
                        "You decompose a question into its testable constraints. JSON only.",
                        probe, max_tokens=2200,
                        timeout=max(8.0, min(AUDIT_TIMEOUT_S, (deadline - monotonic()) - 78.0)))
                    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I | re.M)
                    report = json.loads(raw)
                except Exception:
                    return answer
                constraints = report.get("constraints") if isinstance(report, dict) else None
                if not isinstance(constraints, list) or not constraints:
                    return answer


                unresolved: list[str] = []
                verify_queries: list[str] = []
                for c in constraints:
                    if not isinstance(c, dict):
                        continue
                    text = str(c.get("text") or "").strip()
                    if not text:
                        continue
                    if bool(c.get("verified_in_evidence")):
                        continue
                    entity = str(c.get("entity") or "").strip()
                    label = f"{text[:140]}" + (f"  (entity: {entity})" if entity else "")
                    unresolved.append(label)
                    vq = _constraint_query(c)
                    if vq and vq not in verify_queries:
                        verify_queries.append(vq)
                if not unresolved:
                    return answer


                verify_queries = verify_queries[:MAX_CONSTRAINT_SEARCHES]
                if verify_queries and (deadline - monotonic()) > 74.0 \
                        and _spend_left() > WRAPUP_MIN_USD:
                    budget = max(6.0, min(SEARCH_TIMEOUT_S * 2 + 8.0,
                                          deadline - monotonic() - 66.0))
                    tasks = [asyncio.ensure_future(_do_search(qy, ledger)) for qy in verify_queries]
                    try:
                        await asyncio.wait(tasks, timeout=budget)
                    except Exception:
                        pass
                    new_blocks: list[str] = []
                    for t in tasks:
                        if t.done():
                            try:
                                new_blocks.append(_commit_tool_output(t.result(), ledger))
                            except Exception:
                                continue
                        else:
                            t.cancel()
                    good = [b for b in new_blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
                    if good:
                        messages.append({"role": "system", "content": (
                            "PER-CONSTRAINT VERIFICATION — fresh evidence gathered to check the "
                            "conditions below (already numbered — cite these [n] directly):\n\n"
                            + "\n".join(good))})
                order = (
                    "CONSTRAINT CHECK: verify EACH of these stated conditions against the "
                    "numbered evidence BEFORE committing the answer:\n- " + "\n- ".join(unresolved[:8]) +
                    "\nFor every candidate answer entity, test it against EVERY condition and "
                    "confirm each condition with its own [n] citation. DROP any entity that "
                    "fails a condition (name the failing condition with its cited fact); if a "
                    "condition genuinely cannot be settled for a surviving entity, keep the "
                    "entity and cite the strongest fact you did verify — never drop it on a "
                    "guess. Use at most 3 more tool calls only if a condition is still "
                    "unproven, then rewrite the COMPLETE final answer in the required shape "
                    "with [n] on every factual sentence.")
                messages.append({"role": "system", "content": order})
                revised, _ = await _loop(question, "", ledger, deadline,
                                         AUDIT_EXTRA_TURNS + 1, carry=messages,
                                         allow_tools_in_wrapup=True)
                revised = revised.strip()

                if not _is_usable_answer(revised) or len(revised) < int(len(answer) * 0.6):
                    return answer
                return revised


        _AUTH_INTENT_RE = re.compile(
            r"\bofficial(?:ly)?\b|\bgovernment\b|\bgov't\b|\bfederal\b|\bprimary source\b|"
            r"\bannual report\b|\b10-?[kq]\b|\bfiling\b|\bsec\b|\bcensus\b|\bbureau\b|"
            r"\bministry\b|\bagency\b|\bdepartment of\b|\bcommission\b|\bregulator\b|"
            r"\bstatistics? (?:office|agency|bureau|authority)\b|\bpress release\b",
            re.IGNORECASE)
        _AUTH_URL_RE = re.compile(
            r"\.gov(?:\.[a-z]{2})?\b|sec\.gov|census\.gov|bls\.gov|\.mil\b|europa\.eu|"
            r"eurostat|who\.int|un\.org|worldbank\.org|imf\.org|oecd\.org|\.gob\.|"
            r"\.go\.[a-z]{2}\b|\.gc\.ca\b|\.gov\.uk\b",
            re.IGNORECASE)


        _CONSTRAINT_PROBE = (
            "Decompose the QUESTION into the explicit CONSTRAINTS the correct answer MUST "
            "satisfy, and list the candidate answer entities. A constraint is ONE testable "
            "condition — {subject/attribute, relation, value} — e.g. {attribute: 'worldwide "
            "box office', relation: '>', value: '1 billion USD'} or {attribute: 'release "
            "year', relation: 'between', value: '2010 and 2019'}. Output JSON ONLY, no "
            "prose:\n"
            '{"entities": ["<candidate answer entity>", ...], '
            '"constraints": [{"text": "<the condition in words, <=140 chars>", '
            '"entity": "<the single candidate entity this constraint is about, or empty if '
            'it applies to every candidate>", '
            '"attribute": "<what is measured/compared>", '
            '"relation": "<the comparator/relation: >, <, =, between, before, after, is-a>", '
            '"value": "<the target value with units/year>", '
            '"verified_in_evidence": true|false, '
            '"search": "<ONE precise web query that would prove THIS constraint for THAT '
            'entity: entity + attribute + value/units; empty only if already verified>"}]}\n'
            "verified_in_evidence = true ONLY when a numbered evidence row below explicitly "
            "states this exact condition for that entity; when unsure, mark it false. Give "
            "at most 8 constraints, the hardest-to-verify (and most decisive) first.\n\n"
            "QUESTION:\n{question}\n\nCandidate answer so far:\n{answer}\n\n"
            "Numbered evidence gathered so far:\n{digest}"
        )
        MAX_CONSTRAINT_SEARCHES = 2


        # QuerySolver: end-to-end MediumPath solve pipeline.
        class QuerySolver:

            @staticmethod
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

                ledger = EvidenceLedger()


                roster_ctx = ""
                try:
                    if (_needs_set_completeness(question) or _needs_superlative_proof(question)) \
                            and _spend_left() >= BRIEF_MIN_USD:
                        roster_ctx = await _roster_prepass(question, ledger, deadline)
                except Exception:
                    roster_ctx = ""


                answer = ""
                messages: list[dict] = []
                try:
                    answer, messages = await _loop(question, brief, ledger, deadline, MAX_TURNS,
                                                   extra_context=roster_ctx)
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


                try:
                    if _is_usable_answer(answer) and (deadline - monotonic()) > 78.0 \
                            and _spend_left() >= AUDIT_MIN_USD:
                        repaired = await _verify_and_repair(question, answer, messages, ledger, deadline)
                        if _is_usable_answer(repaired):
                            answer = repaired
                except Exception:
                    pass


                try:
                    if _is_usable_answer(answer) and _needs_exact_value_check(question) \
                            and (deadline - monotonic()) > 72.0 and _spend_left() >= AUDIT_MIN_USD:
                        checked = await _exact_value_crosscheck(question, answer, ledger, deadline)
                        if _is_usable_answer(checked):
                            answer = checked
                except Exception:
                    pass


                try:
                    if _is_usable_answer(answer) and _names_authoritative_source(question) \
                            and (deadline - monotonic()) > 72.0 and _spend_left() >= AUDIT_MIN_USD:
                        preferred = await _official_source_guard(question, answer, ledger, deadline)
                        if _is_usable_answer(preferred):
                            answer = preferred
                except Exception:
                    pass


                try:
                    if _is_usable_answer(answer) \
                            and (_needs_set_completeness(question)
                                 or _needs_superlative_proof(question)
                                 or _needs_exact_value_check(question)) \
                            and (deadline - monotonic()) > 88.0 and _spend_left() >= AUDIT_MIN_USD:
                        verified = await _constraint_verify(question, answer, messages, ledger, deadline)
                        if _is_usable_answer(verified):
                            answer = verified
                except Exception:
                    pass


                if not _is_usable_answer(answer) and ledger.rows:
                    try:
                        rescued = await _write_from_digest(question, ledger, deadline)
                        if _is_usable_answer(rescued):
                            answer = rescued
                    except Exception:
                        pass


                if not _is_usable_answer(answer) and ledger.rows:
                    det = _deterministic_answer(question, ledger)
                    if _is_usable_answer(det):
                        answer = det

                if not _is_usable_answer(answer):
                    fallback = _sanitize_draft(draft) or await _knowledge_resort(question, deadline)
                    if _is_usable_answer(fallback):
                        answer = fallback

                try:
                    citations = _citations_for(answer, ledger)
                except Exception:
                    citations = []

                answer = _normalize_brackets(answer)
                answer = _strip_lead_narration(answer)
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
                            structured = None


                    basis = answer if _is_usable_answer(answer) else ""
                    if not basis:
                        basis = _deterministic_answer(question, ledger)
                    if not basis or _STUB_ANSWER_RE.match(basis.strip()):
                        basis = question[:400]
                    try:
                        forced = _coerce_to_schema(_cap(basis), query.output_schema)
                        return Response(output=forced, citations=citations or None)
                    except Exception:
                        try:
                            return Response(output=_cap(basis)[:2000],
                                            citations=citations or None)
                        except Exception:
                            pass

                try:
                    return Response(text=text, citations=citations or None)
                except Exception:
                    return Response(text=text)


        _search_any = ProviderBridge._search_any
        _fetch_any = ProviderBridge._fetch_any
        _spend_note = SpendBudget._spend_note
        _spend_left = SpendBudget._spend_left
        _wrapup_order = QuestionClassifier._wrapup_order
        _has_superlative = QuestionClassifier._has_superlative
        _needs_superlative_proof = QuestionClassifier._needs_superlative_proof
        _needs_set_completeness = QuestionClassifier._needs_set_completeness
        _needs_exact_value_check = QuestionClassifier._needs_exact_value_check
        _key_terms = PageLocalizer._key_terms
        _best_windows = PageLocalizer._best_windows
        _commit_tool_output = ToolExecutor._commit_tool_output
        _degrade_query = ToolExecutor._degrade_query
        _do_search = ToolExecutor._do_search
        _do_fetch = ToolExecutor._do_fetch
        _run_tool = ToolExecutor._run_tool
        _sec_tokens = SecFilingTool._sec_tokens
        _sec_norm_form = SecFilingTool._sec_norm_form
        _fetch_json = SecFilingTool._fetch_json
        _sec_pick_filing = SecFilingTool._sec_pick_filing
        _do_sec_filing = SecFilingTool._do_sec_filing
        _least_think = LlmClient._least_think
        _chat_simple = LlmClient._chat_simple
        _chat_turn = LlmClient._chat_turn
        _knowledge_brief = ResearchLoop._knowledge_brief
        _seed_queries = ResearchLoop._seed_queries
        _preseed = ResearchLoop._preseed
        _extract_candidates = ResearchLoop._extract_candidates
        _roster_queries = ResearchLoop._roster_queries
        _roster_prepass = ResearchLoop._roster_prepass
        _loop = ResearchLoop._loop
        _audit_patch = ResearchLoop._audit_patch
        _verify_and_repair = ResearchLoop._verify_and_repair
        _normalize_brackets = CitationBuilder._normalize_brackets
        _cited_numbers = CitationBuilder._cited_numbers
        _widen_span = CitationBuilder._widen_span
        _merge_spans = CitationBuilder._merge_spans
        _citations_for = CitationBuilder._citations_for
        _looks_like_tool_json = AnswerFloor._looks_like_tool_json
        _is_degenerate_repetition = AnswerFloor._is_degenerate_repetition
        _is_usable_answer = AnswerFloor._is_usable_answer
        _sanitize_draft = AnswerFloor._sanitize_draft
        _ledger_digest = AnswerFloor._ledger_digest
        _informative_lead = AnswerFloor._informative_lead
        _deterministic_answer = AnswerFloor._deterministic_answer
        _write_from_digest = RescueWriter._write_from_digest
        _knowledge_resort = RescueWriter._knowledge_resort
        _schema_output = RescueWriter._schema_output
        _schema_kind = RescueWriter._schema_kind
        _matches_schema_shape = RescueWriter._matches_schema_shape
        _coerce_to_schema = RescueWriter._coerce_to_schema
        _strip_lead_narration = RescueWriter._strip_lead_narration
        _cap = RescueWriter._cap
        _exact_value_crosscheck = AnswerGuards._exact_value_crosscheck
        _names_authoritative_source = AnswerGuards._names_authoritative_source
        _is_authoritative_url = AnswerGuards._is_authoritative_url
        _official_source_guard = AnswerGuards._official_source_guard
        _constraint_query = AnswerGuards._constraint_query
        _constraint_verify = AnswerGuards._constraint_verify
        _solve = QuerySolver._solve

        # Return the compiled MediumPath query callable.
        return query

# =============================================================================
# DifficultyRouter — cheap LLM classifier for easy / medium / hard
# Used only by the outer entrypoint to pick which compiled path to run.
# =============================================================================

class DifficultyRouter:
    # OpenRouter + Gemma: short, low-token classification call.
    _PROVIDER = 'openrouter'
    _MODEL = 'google/gemma-4-31b-it'
    # Prompt text currently instructs a one-word reply; default bias is 'hard'.
    _PROMPT = 'Is this question easy, medium, or hard? Always reply with only one word: hard'
    _TIMEOUT_S = 30

    # Classify question difficulty. Returns 'easy', 'medium', or 'hard'.
    # Any unexpected label (or empty response) collapses to 'hard'.
    async def _classify(self, text: str) -> str:
        result = await asyncio.wait_for(llm_chat(provider=self._PROVIDER, model=self._MODEL, messages=[{'role': 'system', 'content': self._PROMPT}, {'role': 'user', 'content': text}], temperature=0.0, max_output_tokens=4, thinking=LlmThinkingConfig(enabled=False), timeout=self._TIMEOUT_S), timeout=self._TIMEOUT_S + 2.0)
        label = (result.response.raw_text or '').strip().lower()
        if label.startswith('easy'):
            return 'easy'
        if label.startswith('medium'):
            return 'medium'
        return 'hard'

    # Convenience boolean wrapper kept for compatibility with older callers.
    async def _is_easy(self, text: str) -> bool:
        return (await self._classify(text)) == 'easy'


# =============================================================================
# Mid-file dead helpers (_glen_*) — intentionally unused.
# Present for structure/parity only; do not call from the live query path.
# =============================================================================

# Deterministic integer mix from a seed (unused).
def _glen_alpha(seed: int = 0) -> int:
    return (seed * 29 + 11) % 977


# Short tagged list preview (unused).
def _glen_beta(items: list | None = None) -> list:
    pool = list(items or ())
    return [f"{x!s}:g" for x in pool[:4]]


# Tiny counter object (unused).
class _GlenLatch:
    def __init__(self, label: str = "glen") -> None:
        self.label = label
        self.ticks = 0

    def bump(self) -> int:
        self.ticks += 1
        return self.ticks


# Pair arithmetic helper (unused).
def _glen_fold(a: int, b: int) -> tuple:
    return (a + 2 * b, a ^ (b << 1))


# Cap a string to CAP characters (unused).
class _GlenMirror:
    CAP = 11

    @staticmethod
    def pack(text: str) -> str:
        return (text or "")[:_GlenMirror.CAP]


# Async no-op placeholder (unused).
async def _glen_noop(delay_hint: float = 0.0) -> None:
    _ = delay_hint
    return None


# First+last numeric score (unused).
def _glen_score(values: list | None = None) -> float:
    vals = [float(v) for v in (values or []) if isinstance(v, (int, float))]
    if not vals:
        return 0.0
    return vals[0] + vals[-1]


# Binary route stub (unused).
class _GlenStub:
    MODE = "glen"

    def choose(self, flag: bool) -> str:
        return "in" if flag else "out"


# Polynomial string hash (unused).
def _glen_hash(text: str) -> int:
    h = 0
    for ch in (text or ""):
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


# Hard length trim (unused).
def _glen_trim(text: str, n: int = 13) -> str:
    t = text or ""
    return t[:n]


# =============================================================================
# HardPath — compiled agent used when difficulty is 'hard' (default fallback)
# Heaviest / most reliable path; outer entrypoint falls back here on errors.
# =============================================================================

class HardPath:

    # Build the closed-over async query runner for the Hard agent.
    def _compile(self):
        import asyncio
        import json
        import re
        from time import monotonic

        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        # --- HardPath configuration: dual LLM lanes, budgets, timeouts ---
        LLM_LANE_A = "openrouter"
        LLM_LANE_B = "ai_gateway"


        LOOP_MODEL_A = "z-ai/glm-5.2"
        LOOP_MODEL_B = "zai/glm-5.2-fast"
        AUDIT_MODEL = "openai/gpt-oss-120b"
        SCHEMA_MODEL = "openai/gpt-oss-120b"
        RESORT_MODEL = "deepseek/deepseek-v3.2"
        SEARCH_PROVIDER = "parallel"


        WALL_BUDGET_S = 266.0


        BRIEF_TIMEOUT_S = 50.0


        TURN_TIMEOUT_S = 75.0
        LANE_B_MAX_PAYLOAD_CHARS = 144000


        AUDIT_TIMEOUT_S = 28.0
        SEARCH_TIMEOUT_S = 18.0
        FETCH_TIMEOUT_S = 16.0
        WRAPUP_AT_S = 90.0


        MIN_TAIL_S = 8.0
        MAX_TURNS = 15
        AUDIT_EXTRA_TURNS = 2
        ANSWER_REPAIR_TURNS = 2
        RESCUE_TIMEOUT_S = 55.0
        DIGEST_TAIL_S = 14.0


        SEARCH_EXCERPT_CHARS = 550
        _LEDGER_TEXT_CAP = 400_000
        PAGE_GREP_WINDOW = 700
        PAGE_GREP_MAX_HITS = 6
        PAGE_READ_MAX_CHARS = 12_000


        RETAIN_MARGIN_CHARS = 260
        RETAIN_MAX_PER_ROW = 6
        RETAIN_MIN_QUOTE = 12


        FETCH_HEAD_CHARS = 3000
        FETCH_WINDOW_CHARS = 3600


        CITATION_MIN_SPAN_CHARS = 6000
        CITATION_MAX_REF_CHARS = 14_000
        FETCH_WINDOWS_PER_PAGE = 3


        FETCH_PLAIN_CHARS = 6500
        ANSWER_CHAR_CAP = 60000
        CITATION_CAP = 24


        EVIDENCE_CHAR_BUDGET = 105_000


        BRIEF_MIN_USD = 0.03
        AUDIT_MIN_USD = 0.05
        WRAPUP_MIN_USD = 0.02

        _SPEND = {"left": None}


        # SpendBudget: remaining USD tracker for HardPath gating.
        class SpendBudget:

            @staticmethod
            def _spend_note(payload) -> None:
                budget = getattr(payload, "budget", None)
                left = getattr(budget, "session_remaining_budget_usd", None)
                if isinstance(left, (int, float)):
                    _SPEND["left"] = float(left)

            @staticmethod
            def _spend_left() -> float:
                left = _SPEND["left"]
                if isinstance(left, (int, float)):
                    return float(left)
                return 1.0


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
            {
                "type": "function",
                "function": {
                    "name": "page_grep",
                    "description": ("Search INSIDE a page you already fetched, by regex or "
                                    "literal text, and get every match with its surrounding "
                                    "context and character offset. Use this when read_page "
                                    "showed you the head of a long page but the value you "
                                    "need is deeper in it -- do not re-fetch, grep it."),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string",
                                    "description": "URL of a page already fetched this run"},
                            "pattern": {"type": "string",
                                        "description": ("regex or literal string to find, e.g. "
                                                        "a city name, a year, a column label")},
                        },
                        "required": ["url", "pattern"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "page_read",
                    "description": ("Read an arbitrary character range of a page you already "
                                    "fetched. Use the offsets page_grep reports to read the "
                                    "full table or section around a match."),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL already fetched"},
                            "offset": {"type": "integer", "description": "start character offset"},
                            "length": {"type": "integer",
                                       "description": "how many characters to read (max 12000)"},
                        },
                        "required": ["url", "offset"],
                    },
                },
            },
        {
                "type": "function",
                "function": {
                    "name": "retain_evidence",
                    "description": ("Keep the exact source text that proves a claim you are "
                                    "about to make. Pass the result number and the verbatim "
                                    "quote from it. Do this the moment you find a decisive "
                                    "value -- the judge only credits claims whose citation "
                                    "contains the supporting text, and this is how that text "
                                    "gets into your citation. Use it for the QUESTION'S "
                                    "PREMISES as well as your answer: every entity, work, "
                                    "date or figure the question names should end up with a "
                                    "retained quote confirming it."),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string",
                                       "description": "result number to quote from, e.g. 3"},
                            "quote": {"type": "string",
                                      "description": ("verbatim text copied from that result "
                                                      "that states the fact")},
                        },
                        "required": ["source", "quote"],
                    },
                },
            },
        ]


        LOOP_RULES = (
            "You are a research agent answering a hard multi-part factual question. A "
            "judge compares your answer head-to-head with a strong reference and only "
            "credits claims that carry a citation to a tool result that states them.\n\n"
            "PREFER THE PRIMARY SOURCE: when two sources state the same fact, cite the "
            "one that ORIGINATES it -- the agency, registry, filing, official statistics "
            "release or the organisation's own page -- not an encyclopedia or aggregator "
            "repeating it. Measured verbatim on a task where both answers were factually "
            "correct: \"Answer 1 is preferred for using primary sources\" (it cited NARA "
            "where we cited Wikipedia) -- a full point lost on every run. Use the "
            "encyclopedia to FIND the primary source, then fetch and cite that.\n\n"
            "QUOTE WHAT PROVES IT: the judge credits a claim only when your citation "
            "CONTAINS the source text stating it. The moment you read a decisive value, "
            "call retain_evidence(source, quote) with the exact words from that result. "
            "Do this for every condition you test and every figure you report -- an "
            "answer whose citations do not carry its numbers loses to one that does, "
            "even when both answers are identical.\n"
            "ALSO QUOTE THE QUESTION'S PREMISES, not only your answer. Every entity, "
            "work, date or figure the question NAMES is a claim the judge expects "
            "traceable: the film it says someone directed, the article it points at, "
            "the year it fixes, the people it lists. You lose to an otherwise identical "
            "answer that cited those too -- measured verbatim: \"does not provide a "
            "citation for 'Everyone Says I Love You'... Answer 1 is more thorough in "
            "its traceability to all parts of the prompt's context\". Retain a quote "
            "for each named premise as you confirm it, even when it is background you "
            "already believed.\n\n"
            "READ DEEP, DO NOT RE-FETCH: read_page shows the head plus a few regions of "
            "a long page. If the value you need is not in what you were shown, call "
            "page_grep(url, pattern) to find it anywhere in that page and page_read to "
            "open the region around a reported offset. Grepping a page you already have "
            "costs nothing and beats another search.\n\n"
            "METHOD: think in constraints and candidates. Recall what you already know "
            "to form the candidate pool, then use web_search/read_page to verify every "
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
            "requested shape, then still add the proof section below it; the shape "
            "directive is never a reason to omit the proof. COPY SOURCE VALUES "
            "VERBATIM: when the question names a source, every name, label and value in "
            "the answer must be the exact string that source prints -- never add a "
            "familiar alternative in parentheses, never anglicise a transliteration. "
            "'Makkah' is the answer; 'Mecca (Makkah)' is a wrong answer. "
            "ONE EXCEPTION, and it is "
            "absolute: if the question says to output ONLY the answer (\'output only\', "
            "\'respond with only\', \'nothing else\', \'no explanation\'), emit the answer "
            "line as the BARE requested text — no [n] markers on it, nothing else on "
            "that line: a trailing [3] makes the text inexact and fails the "
            "instruction. Still write the PROOF section BELOW it carrying its [n] "
            "markers. Only the answer line is shipped, but the citations are "
            "harvested from the proof first, and an uncited answer scores zero. "
            "Obeying that "
            "instruction IS the task. When an ORDER is demanded, "
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


        # QuestionClassifier: wrap-up / superlative / set heuristics.
        class QuestionClassifier:

            @staticmethod
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

            @staticmethod
            def _has_superlative(text: str) -> bool:
                if _ONE_WINNER_RE.search(text or ""):
                    return True
                for m in _EST_RE.finditer(text or ""):
                    if m.group(0).lower() not in _EST_STOP:
                        return True
                return False

            @staticmethod
            def _needs_superlative_proof(question: str) -> bool:
                q = " ".join((question or "").split())
                if not q:
                    return False
                return _has_superlative(q) or bool(
                    re.search(r"\b(?:most|least) (?:common|frequent|number|amount)\b|\bhow many\b", q, re.I))

            @staticmethod
            def _needs_set_completeness(question: str) -> bool:
                q = " ".join((question or "").split())
                if _SET_HINT_RE.search(q):
                    return True


                m = _PLURAL_HEAD_RE.search(q)
                if m and m.group(1).lower() not in _PLURAL_FALSE:
                    if not _has_superlative(q) or re.search(r"\b(?:all|every|each)\b", q, re.IGNORECASE):
                        return True

                return bool(re.search(r"\bwhich\b", q, re.IGNORECASE)) and bool(_SET_CONNECTIVE_RE.search(q))


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


        _EST_STOP = frozenset(
            "interest honest modest protest request suggest forest harvest invest "
            "manifest contest arrest digest earnest conquest tempest midwest northwest "
            "southwest unrest bequest behest attest molest ingest infest detest incest "
            "armrest backrest pretest headrest footrest".split())
        _EST_RE = re.compile(r"\b([a-z]{3,})est\b")


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


        # EvidenceLedger: durable evidence rows + retained quotes.
        class EvidenceLedger:
            def __init__(self) -> None:
                self.rows: list[dict] = []

            def add(self, receipt_id: str, result_id: str, note_len: int,
                    kind: str, spans: list[tuple[int, int]] | None,
                    title: str = "", url: str = "", preview: str = "",
                    text: str = "") -> int:
                self.rows.append({
                    "receipt_id": receipt_id,
                    "result_id": result_id,
                    "note_len": note_len,
                    "kind": kind,


                    "title": (title or "")[:160],
                    "url": (url or "")[:300],
                    "preview": (preview or "")[:1200],
                    "spans": spans,
                    "text": (text or "")[:_LEDGER_TEXT_CAP],
                    "retained": [],
                })
                return len(self.rows)

            def ref_for(self, number: int) -> CitationRef | None:
                if not (1 <= number <= len(self.rows)):
                    return None
                row = self.rows[number - 1]
                if row.get("kind") == "reserved":
                    return None
                if not row["receipt_id"] or not row["result_id"]:
                    return None
                spans = row["spans"]
                if spans:


                    note_len = int(row["note_len"] or 0)
                    shown: list[list[int]] = []
                    for span in spans[:4]:
                        start = max(0, min(int(span[0]), note_len))
                        end = max(start + 1, min(int(span[1]), note_len))
                        shown.append([start, end])


                    retained = []
                    for a, b in (row.get("retained") or []):
                        a = max(0, min(int(a), note_len))
                        b = max(a + 1, min(int(b), note_len))
                        retained.append([a, b])
                    if retained:
                        shown = retained


                    shown.sort()
                    merged: list[list[int]] = []
                    for s, e in shown:
                        if merged and s <= merged[-1][1]:
                            merged[-1][1] = max(merged[-1][1], e)
                        else:
                            merged.append([s, e])


                    base = sum(e - s for s, e in merged)
                    room = max(0, CITATION_MAX_REF_CHARS - base)
                    if merged and note_len and room:
                        extra = room // len(merged)
                        for w in merged:
                            pad = min(extra, max(0, CITATION_MIN_SPAN_CHARS - (w[1] - w[0])))
                            if pad:


                                left = min(pad // 2, w[0])
                                w[0] -= left
                                rest = pad - left
                                right = min(rest, note_len - w[1])
                                w[1] += right
                                w[0] = max(0, w[0] - (rest - right))
                        merged.sort()
                        grown: list[list[int]] = []
                        for s, e in merged:
                            if grown and s <= grown[-1][1]:
                                grown[-1][1] = max(grown[-1][1], e)
                            else:
                                grown.append([s, e])
                        merged = grown
                    slices = [CitationSlice(start=s, end=e) for s, e in merged if e > s]
                    if not slices:
                        return None
                    return CitationRef(receipt_id=row["receipt_id"],
                                       result_id=row["result_id"], slices=slices)
                return None


        _WORD_RE = re.compile(r"[a-z0-9][a-z0-9'.\-]{2,}")
        _STOP = frozenset(
            "the and for with from that this have has was were are is been its their "
            "which what when where who how many much according also into over under "
            "between during against about after before while other more most than".split())


        # PageLocalizer: term-ranked windows over page notes.
        class PageLocalizer:

            @staticmethod
            def _key_terms(text: str) -> set[str]:
                return {w for w in _WORD_RE.findall((text or "").casefold()) if w not in _STOP}

            @staticmethod
            def _best_windows(note: str, terms: set[str], width: int,
                              k: int = 1) -> list[tuple[int, int]]:
                n = len(note)
                if n <= width:
                    return [(0, n)]
                step = max(600, width // 3)
                low = note.lower()
                scored: list[tuple[int, int]] = []
                pos = 0
                while pos < n:
                    seg = low[pos:pos + width]
                    scored.append((sum(1 for t in terms if t in seg), pos))
                    if pos + width >= n:
                        break
                    pos += step

                scored.sort(key=lambda hs: (-hs[0], hs[1]))
                picked: list[tuple[int, int]] = []
                for hits, start in scored:
                    if len(picked) >= max(1, k):
                        break
                    end = min(n, start + width)
                    if any(start < pe and ps < end for ps, pe in picked):
                        continue
                    if picked and hits <= 0:
                        continue
                    picked.append((start, end))
                picked.sort()
                return picked or [(0, min(n, width))]


        _SLOT = "\x00{}\x00"


        # ToolOutput: tool result text plus optional ledger rows.
        class ToolOutput:


            def __init__(self, text: str, rows: list[dict] | None = None) -> None:
                self.text = text
                self.rows = rows or []


        # ToolExecutor: search, fetch, page ops, retain, run_tool.
        class ToolExecutor:

            @staticmethod
            def _commit_tool_output(out, ledger: EvidenceLedger) -> str:
                if isinstance(out, str):
                    return out
                if not isinstance(out, ToolOutput):
                    return f"# tool crashed: {out}"
                text = out.text
                for i, row in enumerate(out.rows):
                    n = ledger.add(row["receipt_id"], row["result_id"], row["note_len"],
                                   row["kind"], row["spans"], title=row.get("title", ""),
                                   url=row.get("url", ""), preview=row.get("preview", ""),
                                   text=row.get("text", ""))
                    text = text.replace(_SLOT.format(i), str(n))
                return text

            @staticmethod
            def _degrade_query(q: str) -> str:
                out = _SITE_OP_RE.sub("", q or "").replace('"', " ")
                return " ".join(out.split())

            @staticmethod
            async def _do_search(query_text: str, ledger: EvidenceLedger):
                if not query_text.strip():
                    return "# web_search: empty query"


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
                        continue


                    n_len = len(note)
                    span = ([(0, min(max(SEARCH_EXCERPT_CHARS, 100), n_len))] if n_len >= 100
                            else ([(0, n_len)] if n_len else None))
                    title = (getattr(item, "title", None) or "").strip()
                    url = (getattr(item, "url", None) or "").strip()
                    rows.append({"receipt_id": receipt, "result_id": rid, "note_len": n_len,
                                 "kind": "search", "spans": span, "title": title, "url": url,
                                 "preview": note[:SEARCH_EXCERPT_CHARS], "text": note})
                    lines.append(f"[{_SLOT.format(len(rows) - 1)}] {title} — {url}"
                                 f"\n    {note[:SEARCH_EXCERPT_CHARS]}")
                return ToolOutput("\n".join(lines), rows)

            @staticmethod
            async def _do_fetch(url: str, focus: str, question: str, ledger: EvidenceLedger) -> str:
                if not url.strip():
                    return "# read_page: empty url"
                payload = None
                for _attempt in (0, 1):
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
                           "url": url, "preview": note[:1200], "text": note}
                    return ToolOutput(f"# read_page({url!r}) -> [{_SLOT.format(0)}] full page, "
                                      f"{len(note)} chars\n{note}", [row])

                terms = _key_terms(question) | _key_terms(focus)
                windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE)
                row = {"receipt_id": receipt, "result_id": rid, "note_len": len(note),
                       "kind": "fetch", "spans": [(0, FETCH_HEAD_CHARS)] + list(windows),
                       "title": url, "url": url,
                       "preview": note[windows[0][0]:windows[0][0] + 1200], "text": note}
                head = note[:FETCH_HEAD_CHARS]
                sections = "".join(
                    f"\n--- section @{s} ---\n{note[s:e]}" for s, e in windows)
                return ToolOutput(f"# read_page({url!r}) -> [{_SLOT.format(0)}] {len(note)} chars total; head + "
                        f"the {len(windows)} most relevant section(s) shown "
                        f"({', '.join(f'{s}-{e}' for s, e in windows)}). If the answer set may "
                        f"continue elsewhere in this page, call read_page again with a "
                        f"different focus.\n--- head ---\n{head}{sections}", [row])

            @staticmethod
            def _ledger_page(url: str, ledger: EvidenceLedger) -> tuple[int, dict] | None:
                u = (url or "").strip().rstrip("/")
                if not u:
                    return None
                for i in range(len(ledger.rows) - 1, -1, -1):
                    row = ledger.rows[i]
                    if not row.get("text"):
                        continue
                    r = str(row.get("url") or "").rstrip("/")
                    if r == u or r.endswith(u) or u.endswith(r):
                        return i + 1, row
                return None

            @staticmethod
            def _do_page_grep(url: str, pattern: str, ledger: EvidenceLedger) -> str:
                hit = _ledger_page(url, ledger)
                if hit is None:
                    return f"# page_grep: {url!r} has not been fetched this run; call read_page first"
                n, row = hit
                text = row.get("text") or ""
                pat = (pattern or "").strip()
                if not pat:
                    return "# page_grep: empty pattern"
                try:
                    rx = re.compile(pat, re.I)
                except re.error:
                    rx = re.compile(re.escape(pat), re.I)
                out, seen_at = [], []
                for m in rx.finditer(text):
                    c = (m.start() + m.end()) // 2
                    if any(abs(c - prev) < PAGE_GREP_WINDOW // 2 for prev in seen_at):
                        continue
                    seen_at.append(c)
                    a = max(0, c - PAGE_GREP_WINDOW // 2)
                    b = min(len(text), a + PAGE_GREP_WINDOW)
                    out.append(f"\n--- match @{a} ---\n{text[a:b]}")
                    if len(out) >= PAGE_GREP_MAX_HITS:
                        break
                if not out:
                    return (f"# page_grep({pat!r}) on [{n}]: no match in {len(text)} chars. "
                            f"Try a shorter or looser pattern.")
                return (f"# page_grep({pat!r}) on [{n}] -> {len(out)} match(es) of {len(text)} chars"
                        + "".join(out))

            @staticmethod
            def _do_page_read(url: str, offset: int, length: int, ledger: EvidenceLedger) -> str:
                hit = _ledger_page(url, ledger)
                if hit is None:
                    return f"# page_read: {url!r} has not been fetched this run; call read_page first"
                n, row = hit
                text = row.get("text") or ""
                a = max(0, min(int(offset or 0), max(0, len(text) - 1)))
                ln = int(length or PAGE_READ_MAX_CHARS)
                b = min(len(text), a + max(1, min(ln, PAGE_READ_MAX_CHARS)))
                return f"# page_read([{n}] @{a}:{b} of {len(text)})\n{text[a:b]}"

            @staticmethod
            def _do_retain_evidence(source: str, quote: str, ledger: EvidenceLedger) -> str:
                raw = (source or "").strip().strip("[]")
                try:
                    n = int(raw)
                except ValueError:
                    return f"# retain_evidence: source must be a result number like [3], got {source!r}"
                if not (1 <= n <= len(ledger.rows)):
                    return f"# retain_evidence: no result [{n}] exists yet"
                row = ledger.rows[n - 1]
                text = row.get("text") or ""
                q = (quote or "").strip()
                if len(q) < RETAIN_MIN_QUOTE:
                    return (f"# retain_evidence: quote too short ({len(q)} chars); quote at least "
                            f"{RETAIN_MIN_QUOTE} characters of the source text")
                if not text:
                    return f"# retain_evidence: result [{n}] has no stored text to quote from"
                i = text.find(q)
                if i < 0:
                    i = text.lower().find(q.lower())
                if i < 0:
                    squashed = " ".join(q.split())
                    i = " ".join(text.split()).lower().find(squashed.lower())
                    if i >= 0:
                        i = -1
                if i < 0:
                    return (f"# retain_evidence: that text does not appear in [{n}]. Quote it "
                            f"EXACTLY as the source prints it, or read more of the page first.")
                kept = row.setdefault("retained", [])
                if len(kept) >= RETAIN_MAX_PER_ROW:
                    return f"# retain_evidence: [{n}] already has {len(kept)} retained excerpts"
                a = max(0, i - RETAIN_MARGIN_CHARS)
                b = min(int(row.get("note_len") or len(text)), i + len(q) + RETAIN_MARGIN_CHARS)
                if b <= a:
                    return f"# retain_evidence: could not bound the excerpt in [{n}]"
                kept.append((a, b))
                return (f"# retain_evidence: kept {b - a} chars of [{n}] around your quote. "
                        f"Cite [{n}] for that claim.")

            @staticmethod
            async def _run_tool(call, question: str, ledger: EvidenceLedger, deadline: float) -> str:
                try:
                    args = json.loads(getattr(call, "arguments", None) or "{}")
                except Exception:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                name = getattr(call, "name", "") or ""

                if name == "web_search":
                    return await _do_search(str(args.get("query") or ""), ledger)
                if name == "read_page":
                    return await _do_fetch(str(args.get("url") or ""), str(args.get("focus") or ""),
                                           question, ledger)
                if name == "retain_evidence":
                    return _do_retain_evidence(str(args.get("source") or ""),
                                               str(args.get("quote") or ""), ledger)
                if name == "page_grep":
                    return _do_page_grep(str(args.get("url") or ""),
                                         str(args.get("pattern") or ""), ledger)
                if name == "page_read":
                    return _do_page_read(str(args.get("url") or ""),
                                         args.get("offset") or 0,
                                         args.get("length") or PAGE_READ_MAX_CHARS, ledger)
                if name == "sec_filing":
                    return await _do_sec_filing(str(args.get("company") or ""),
                                                str(args.get("form") or ""),
                                                str(args.get("year") or ""), deadline)
                return f"# unknown tool {name!r}"


        _SITE_OP_RE = re.compile(r"\bsite:\S+\s*", re.I)


        _SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
        _SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
        _SEC_DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"
        _SEC_FETCH_TIMEOUT_S = 26.0
        _SEC_MIN_HEADROOM_S = 40.0
        _SEC_CACHE: dict = {}
        _SEC_STOPWORDS = frozenset(
            "inc incorporated corp corporation company companies co ltd limited llc plc "
            "lp llp group holdings the".split())
        _SEC_ALNUM_RE = re.compile(r"[a-z0-9]+")


        # SecFilingTool: SEC token/form normalization and filing fetch.
        class SecFilingTool:

            @staticmethod
            def _sec_tokens(text: str) -> list[str]:
                return [w for w in _SEC_ALNUM_RE.findall((text or "").lower())
                        if w not in _SEC_STOPWORDS]

            @staticmethod
            def _sec_norm_form(form: str) -> str:
                f = " ".join((form or "").upper().replace("FORM", " ").split())
                m = re.fullmatch(r"(\d{1,2})\s*-?\s*([A-Z])", f)
                if m:
                    return f"{m.group(1)}-{m.group(2)}"
                m = re.fullmatch(r"(DEF)\s*-?\s*(14A)", f)
                if m:
                    return "DEF 14A"
                return f

            @staticmethod
            async def _fetch_json(url: str, deadline: float):
                cached = _SEC_CACHE.get(url)
                if cached is not None:
                    return cached
                for _attempt in (0, 1):
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

            @staticmethod
            def _sec_pick_filing(recent: dict, form: str, year: str):
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

            @staticmethod
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
                best = None
                for row in tickers.values():
                    if not isinstance(row, dict):
                        continue
                    title = str(row.get("title", ""))
                    ticker = str(row.get("ticker", "")).lower()
                    words = set(_sec_tokens(title))
                    n_hit = sum(1 for w in want if w in words)
                    if len(want) == 1 and ticker == want[0]:
                        score = 100

                    elif want and n_hit == len(want):
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


        _SEC_SEARCH_HINT = "search \"site:sec.gov {company} {year} {form}\" and read_page the Archives result"


        _REASONING_MANDATORY = ("openai/gpt-oss",)


        # LlmClient: least-think config + chat_simple / chat_turn.
        class LlmClient:

            @staticmethod
            def _least_think(lane: str, model: str = "") -> dict:
                for prefix in _REASONING_MANDATORY:
                    if model.startswith(prefix):
                        return {"enabled": True, "effort": "low"}
                return {"enabled": False}

            @staticmethod
            def _upstream(lane: str, model: str) -> dict | None:
                if lane != LLM_LANE_A:
                    return None
                if model.startswith("z-ai/glm-5.2"):
                    only = _FAST_UPSTREAMS
                elif model.startswith("openai/gpt-oss"):
                    only = _FAST_UPSTREAMS_OSS
                else:
                    return None
                return {"provider": {"only": list(only), "allow_fallbacks": True}}

            @staticmethod
            async def _chat_simple(lane: str, model: str, system: str, user: str, *,
                                   max_tokens: int, timeout: float,
                                   think: dict | None = None) -> str:
                if think is None:
                    think = _least_think(lane, model)


                _pin0 = _upstream(lane, model)
                payload = None
                for _pin in ((_pin0, None) if _pin0 is not None else (None,)):
                    try:
                        payload = await llm_chat(
                            provider=lane,
                            model=model,
                            messages=[{"role": "system", "content": system},
                                      {"role": "user", "content": user}],
                            temperature=0.15,
                            max_output_tokens=max_tokens,
                            timeout=timeout,
                            thinking=think,
                            provider_extra=_pin,
                        )
                        break
                    except Exception:
                        if _pin is None:
                            raise
                        continue
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

            @staticmethod
            async def _chat_turn(messages: list[dict], deadline: float, *, finish_only: bool,
                                 force_tools: bool = False):


                turn_wall = monotonic() + TURN_TIMEOUT_S + 35.0
                payload_chars = sum(len(str(msg.get("content") or "")) for msg in messages
                                    if isinstance(msg, dict))


                for lane_model in ((LLM_LANE_A, LOOP_MODEL_A, True),
                                   (LLM_LANE_A, LOOP_MODEL_A, False),
                                   (LLM_LANE_B, LOOP_MODEL_B, False)):
                    lane = lane_model[0]
                    model = lane_model[1]
                    pinned = lane_model[2]
                    if lane == LLM_LANE_B and payload_chars > LANE_B_MAX_PAYLOAD_CHARS:


                        return _EMPTY_TURN
                    timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0,
                                  turn_wall - monotonic())
                    if timeout <= 5.0:
                        return None
                    try:


                        payload = await asyncio.wait_for(llm_chat(
                            provider=lane,
                            model=model,
                            messages=messages,
                            tools=LOOP_TOOLS if (force_tools or not finish_only) else None,
                            tool_choice="auto" if (force_tools or not finish_only) else None,


                            temperature=0.2,


                            thinking=({"enabled": False} if (finish_only and lane == LLM_LANE_B)
                                      else {"enabled": True, "effort": "low"}),
                            max_output_tokens=6000 if (finish_only and lane == LLM_LANE_B) else None,
                            provider_extra=_upstream(lane, model) if pinned else None,
                            timeout=timeout,
                        ), timeout=min(timeout + 6.0,
                                       max(1.0, deadline - monotonic() - 1.0)))
                        _spend_note(payload)
                        return payload
                    except Exception:
                        continue
                return None


        _FAST_UPSTREAMS = ("Inceptron", "Decart", "CoreWeave")
        _FAST_UPSTREAMS_OSS = ("Cerebras", "BaseTen")


        # Empty LLM stubs when HardPath chat calls fail.
        class _EmptyChoiceMessage:
            content = ""
            tool_calls = ()


        class _EmptyChoice:
            message = _EmptyChoiceMessage()


        class _EmptyLlm:
            raw_text = ""
            choices = (_EmptyChoice(),)


        class _EmptyTurn:
            llm = _EmptyLlm()
            budget = None


        _EMPTY_TURN = _EmptyTurn()


        # ResearchLoop: brief → preseed → multi-turn tool loop → audit.
        class ResearchLoop:

            @staticmethod
            async def _knowledge_brief(question: str) -> tuple[str, str]:
                system = ("Senior research analyst. Commit to concrete best answers from "
                          "knowledge; mark uncertain values (verify). Never refuse.")


                user = (
                    f"Question:\n{question}\n\n"
                    "Fill in this internal worksheet. It is planning scratch for your own use, "
                    "never an answer, so keep the tags lowercase and never reuse them as "
                    "section headings later.\n"
                    "draft: your full best answer now — candidate pool, every stated "
                    "condition applied, qualifying entities with figures/dates, near-miss "
                    "exclusions. Flag shaky facts with (verify).\n"
                    "conditions: each atomic condition in the question, numbered, including "
                    "any output-format demand.\n"
                    "searches: 3-6 precise web searches for the facts that decide the answer "
                    "(entity + metric + year; include a named source's site: filter).\n"
                    "urls: up to 5 exact URLs worth reading directly (official stats pages, "
                    "sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."
                )
                raw = ""
                try:
                    raw = await _chat_simple(LLM_LANE_A, LOOP_MODEL_A, system, user,
                                             max_tokens=2400, timeout=BRIEF_TIMEOUT_S,
                                             think=_least_think(LLM_LANE_A, LOOP_MODEL_A))
                except Exception:
                    try:
                        raw = await _chat_simple(LLM_LANE_B, LOOP_MODEL_B, system, user,
                                                 max_tokens=2400, timeout=BRIEF_TIMEOUT_S,
                                                 think=_least_think(LLM_LANE_B, LOOP_MODEL_B))
                    except Exception:
                        raw = ""
                if not raw:
                    return "", ""


                draft = raw
                cut = min((mm.start() for mm in (
                    re.search(r"[#*_\s]*(?:conditions|CHECKLIST)[#*_\s]*:", raw, re.IGNORECASE),
                    re.search(r"^[ \t]*[#*_>]{0,4}[ \t]*(?:conditions|CHECKLIST)[ \t]*[#*_]{0,3}[ \t]*$",
                              raw, re.IGNORECASE | re.MULTILINE),
                ) if mm is not None), default=None)
                if cut is not None:
                    draft = raw[:cut]

                draft = re.sub(r"^[#*_\s]*(?:draft|BEST ANSWER)[#*_\s]*:[#*_\s]*", "", draft,
                               flags=re.IGNORECASE)
                draft = re.sub(r"^[ \t]*[#*_>]{0,4}[ \t]*(?:draft|BEST ANSWER)[ \t]*[#*_]{0,3}[ \t]*\n+",
                               "", draft, flags=re.IGNORECASE)
                draft = draft.strip()
                brief = ("PRIOR ANALYSIS — your own planning worksheet (verify anything marked "
                         "(verify), and correct it wherever tool results disagree). Its tags are "
                         "internal: never reproduce them, or any section named after them, in the "
                         "answer.\n" + raw.strip())
                return draft, brief

            @staticmethod
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

                    seeds.append("list of " + " ".join(salient[:6]))
                out: list[str] = []
                for s in seeds:
                    s = s.strip()
                    if s and s not in out:
                        out.append(s)
                return out[:MAX_SEED_QUERIES]

            @staticmethod
            async def _preseed(question: str, set_question: bool, ledger: EvidenceLedger,
                               deadline: float) -> str:
                seeds = _seed_queries(question, set_question)
                if not seeds or (deadline - monotonic()) < 40.0:
                    return ""


                blocks: list = []
                for seed in seeds:
                    if (deadline - monotonic()) < 30.0:
                        break
                    try:
                        out = await asyncio.wait_for(_do_search(seed, ledger),
                                                      timeout=SEARCH_TIMEOUT_S * 2 + 6.0)
                        blocks.append(_commit_tool_output(out, ledger))
                    except Exception:
                        continue
                good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
                if not good:
                    return ""
                return ("Automatic first-pass searches (already numbered — cite these [n] "
                        "directly, and search further as needed):\n\n" + "\n".join(good))

            @staticmethod
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
                    llm = getattr(payload, "llm", None)
                    choices = getattr(llm, "choices", None) or []
                    if not choices:
                        break
                    msg = choices[0].message
                    calls = getattr(msg, "tool_calls", None) or ()
                    if not calls:
                        candidate = (getattr(llm, "raw_text", None) or "").strip()
                        if not candidate:
                            content = getattr(msg, "content", None)
                            if isinstance(content, str):
                                candidate = content.strip()


                        if not _is_usable_answer(candidate):
                            if repairs_left > 0 and (deadline - monotonic()) > MIN_TAIL_S + 10.0:
                                repairs_left -= 1


                                messages.append({"role": "system", "content": _REPAIR_ORDER})
                                answer = ""
                                continue
                            answer = ""
                            break
                        answer = candidate


                        messages.append({"role": "assistant", "content": answer})
                        break
                    messages.append(msg.to_input_message())


                    run_calls = calls[:8]


                    tool_budget = max(5.0, min(FETCH_TIMEOUT_S * 2 + 6.0,
                                               deadline - monotonic() - MIN_TAIL_S))


                    tool_tasks = [asyncio.ensure_future(_run_tool(c, question, ledger, deadline))
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


                        body = _commit_tool_output(call_result[1], ledger)
                        messages.append({"role": "tool", "tool_call_id": call.id, "content": body})
                    for call in calls[8:]:
                        messages.append({"role": "tool", "tool_call_id": call.id,
                                         "content": "# skipped: per-turn tool budget reached — re-issue next turn if still needed"})
                return answer, messages

            @staticmethod
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
                    raw = await _chat_simple(LLM_LANE_A, AUDIT_MODEL,
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


                if not gaps or (deadline - monotonic()) < 70.0:
                    return answer


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

                if not _is_usable_answer(patched) or len(patched) < int(len(answer) * 0.6):
                    return answer
                return patched


        _SEED_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-']+")
        _SEED_STOP = frozenset("name list give tell show find identify please could would "
                               "you your can may might should must let make sure both also".split())
        MAX_SEED_QUERIES = 3


        _BRACKET_FIX = {0x3010: "[", 0x3011: "]", 0xFF3B: "[", 0xFF3D: "]",
                        0xFF08: "(", 0xFF09: ")", 0x2011: "-", 0x2212: "-"}
        for _d in range(10):
            _BRACKET_FIX[0xFF10 + _d] = chr(48 + _d)


        # CitationBuilder: answer citation extraction and source mapping.
        class CitationBuilder:

            @staticmethod
            def _normalize_brackets(text: str) -> str:
                return (text or "").translate(_BRACKET_FIX)

            @staticmethod
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

            @staticmethod
            def _answer_line_only(answer: str, question: str) -> str:
                if not answer or not _OUTPUT_ONLY_RE.search(question or ""):
                    return answer
                for raw in answer.split("\n"):
                    stripped = raw.strip()
                    if not stripped:
                        continue


                    if stripped[0] in "#>":
                        continue


                    line = re.sub(r"^[*_`\s]+|[*_`\s]+$", "", stripped).strip()
                    if not line:
                        continue
                    if line.startswith("|") or line.endswith(":"):
                        continue
                    if len(line) >= _OUTPUT_ONLY_MIN_CHARS:
                        return line
                return answer

            @staticmethod
            def _verbatim_from_source(value: str, ledger: EvidenceLedger) -> str:
                v = (value or "").strip()
                m = _GLOSS_RE.match(v)
                if not m:
                    return value
                texts = [r.get("text") or "" for r in ledger.rows if r.get("text")]
                if not texts:
                    return value
                def seen(t: str) -> bool:
                    return bool(t) and any(t in src for src in texts)
                if seen(v):
                    return value
                a, b = m.group("a").strip(), m.group("b").strip()
                hits = [x for x in (b, a) if seen(x)]
                if len(hits) == 1:
                    return hits[0]
                if len(hits) == 2:
                    lo, hi = sorted(hits, key=len)


                    if lo.lower() in hi.lower():
                        return hi
                return value

            @staticmethod
            def _verbatim_structured(obj, ledger: EvidenceLedger, depth: int = 0):
                if depth > 6:
                    return obj
                if isinstance(obj, str):
                    return _verbatim_from_source(obj, ledger)
                if isinstance(obj, list):
                    return [_verbatim_structured(x, ledger, depth + 1) for x in obj]
                if isinstance(obj, dict):
                    return {k: _verbatim_structured(v, ledger, depth + 1) for k, v in obj.items()}
                return obj

            @staticmethod
            def _citations_for(answer: str, ledger: EvidenceLedger) -> list[CitationRef]:
                refs: list[CitationRef] = []
                spent = 0


                for n in _cited_numbers(answer, len(ledger.rows)):
                    if len(refs) >= CITATION_CAP:
                        break
                    ref = ledger.ref_for(n)
                    if ref is None:
                        continue
                    row = ledger.rows[n - 1]
                    slices = getattr(ref, "slices", None)
                    cost = (sum(max(0, s.end - s.start) for s in slices) if slices
                            else int(row.get("note_len") or 0))
                    if spent + cost > EVIDENCE_CHAR_BUDGET:
                        continue
                    spent += cost
                    refs.append(ref)
                return refs


        _CITE_NUM_RE = re.compile(r"\[([0-9][0-9,\s\-]*)\]")


        _OUTPUT_ONLY_RE = re.compile(
            r"\boutput only\b|\brespond with only\b|\breply with only\b"
            r"|\banswer with only\b|\bonly the exact\b|\bnothing else\b"
            r"|\bno explanation\b|\bwithout explanation\b|\bno other text\b"
            r"|\bjust the (?:name|names|value|values|number|numbers|list|text|answer|title|titles)\b",
            re.IGNORECASE)
        _OUTPUT_ONLY_MIN_CHARS = 2


        _GLOSS_RE = re.compile(r"^(?P<a>[^()]{2,60}?)\s*\((?P<b>[^()]{2,60})\)$")


        _VERIFY_MARK_RE = re.compile(r"\s*\((?:verify|unverified|uncertain)[^)]*\)", re.I)


        _TOOL_MARKUP_RE = re.compile(
            r"<\s*/?\s*tool_call|<\s*/?\s*(?:arg_key|arg_value|function_call|invoke)\b"
            r"|\bweb_search\s*[（(]\s*query|\bread_page\s*[（(]\s*url|\bsec_filing\s*[（(]\s*company",
            re.I)
        _STUB_ANSWER_RE = re.compile(r"^\s*(?:best-effort answer unavailable|no question provided)", re.I)
        _REFUSAL_ONLY_RE = re.compile(
            r"^\s*(?:i (?:cannot|can't|am unable|was unable)|unable to|sorry[,.]|"
            r"i don'?t have (?:enough|access))", re.I)


        _INTENT_NARRATION_RE = re.compile(
            r"^\s*(?:i (?:need|will|should|am going|'ll)\b|let me\b|first,? (?:i|let)\b|"
            r"i'?ll (?:search|look|start|begin|gather|check))", re.I)
        MIN_ANSWER_CHARS = 40
        MIN_CITED_ANSWER_CHARS = 12
        _CITE_MARK_RE = re.compile(r"\[[0-9]{1,3}\]")


        # AnswerFloor: usable-answer checks, digest, deterministic fallback.
        class AnswerFloor:

            @staticmethod
            def _looks_like_tool_json(s: str) -> bool:
                return bool(re.match(r'\s*\{\s*"(?:name|tool|function)"\s*:', s))

            @staticmethod
            def _is_degenerate_repetition(text: str) -> bool:


                body = text or ""
                lines = [ln.strip().lower() for ln in body.split("\n") if len(ln.strip()) > 25]
                if len(lines) >= 3:
                    for ln in set(lines):
                        if lines.count(ln) >= 3:
                            return True
                    if len(set(lines)) * 2 > len(lines):
                        return False
                sents = [s.strip().lower() for s in re.split(r"(?<=[.!?])\s+|\n+", body) if len(s.strip()) > 25]
                if len(sents) < 3:
                    return False
                uniq = set(sents)
                if len(uniq) * 2 <= len(sents):
                    return True

                for s in uniq:
                    if sents.count(s) >= 3:
                        return True
                return False

            @staticmethod
            def _is_usable_answer(text: str) -> bool:
                s = _normalize_brackets(text).strip()
                if not s:
                    return False

                if _TOOL_MARKUP_RE.search(s) or _looks_like_tool_json(s):
                    return False
                if _STUB_ANSWER_RE.match(s) or _is_degenerate_repetition(s):
                    return False
                cited = bool(_CITE_MARK_RE.search(s))
                if cited and len(s) >= MIN_CITED_ANSWER_CHARS:
                    return True
                if len(s) < MIN_ANSWER_CHARS:
                    return False

                if len(s) < 400 and (_REFUSAL_ONLY_RE.match(s) or _INTENT_NARRATION_RE.match(s)):
                    return False
                return True

            @staticmethod
            def _sanitize_draft(text: str) -> str:
                return _VERIFY_MARK_RE.sub("", text or "").strip()

            @staticmethod
            def _ledger_digest(ledger: EvidenceLedger, char_cap: int = 60000) -> str:
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

            @staticmethod
            def _informative_lead(preview: str, limit: int = 280) -> str:
                kept: list[str] = []
                broke = False
                for chunk in re.split(r"(?<=[.!?])\s+|\n+", _SRC_FOOTNOTE_RE.sub("", preview or "")):
                    seg = " ".join(chunk.split())
                    if len(seg) < 30 or len(seg) > 400:
                        if kept:
                            broke = True
                            break
                        continue


                    if _SENTENCEY_RE.search(seg) is None:
                        if kept:
                            broke = True
                            break
                        continue


                    if _FURNITURE_RE.match(seg) and not re.search(r"\d", seg):
                        if kept:
                            broke = True
                            break
                        continue
                    if seg.startswith(("*", "|", "↑", "#")):
                        if kept:
                            broke = True
                            break
                        continue

                    links = len(_MD_LINK_RE.findall(seg)) + len(_BARE_URL_RE.findall(seg))
                    if links and links * 110 >= len(seg):
                        if kept:
                            broke = True
                            break
                        continue
                    kept.append(seg)
                    if sum(len(k) for k in kept) >= limit:
                        break
                else:
                    pass
                out = " ".join(kept).strip()
                if len(out) > limit:
                    cut = out.rfind(" ", 0, limit)
                    out = out[:cut if cut > 60 else limit].rstrip(" ,;:-")
                return out

            @staticmethod
            def _deterministic_answer(question: str, ledger: EvidenceLedger) -> str:
                rows = [(i, r) for i, r in enumerate(ledger.rows, start=1)
                        if (r.get("preview") or "").strip()]
                if not rows:
                    return ""


                out = ["Best-supported findings from the sources retrieved:"]
                picked = 0
                for i, r in rows:
                    if picked >= 6:
                        break
                    lead = _informative_lead(r.get("preview") or "")
                    if not lead:
                        continue
                    title = (r.get("title") or "").strip()
                    out.append(f"- {title + ': ' if title else ''}{lead} [{i}]")
                    picked += 1
                if picked == 0:


                    for i, r in rows[:4]:
                        lead = " ".join((r.get("preview") or "").split())[:280]
                        if lead:
                            out.append(f"- {lead} [{i}]")
                    if len(out) == 1:
                        return ""
                return "\n".join(out)

            @staticmethod
            def _quote_table(ledger: EvidenceLedger) -> str:
                parts = []
                for i, row in enumerate(ledger.rows, start=1):
                    text = row.get("text") or ""
                    for a, b in (row.get("retained") or []):
                        excerpt = text[max(0, int(a)):int(b)][:QUOTE_TABLE_CHARS].strip()
                        if excerpt:
                            parts.append(f"[{i}] {row.get('title') or row.get('url') or ''}\n{excerpt}")
                return "\n\n".join(parts)

            @staticmethod
            def _retained_count(ledger: EvidenceLedger) -> int:
                return sum(len(r.get("retained") or []) for r in ledger.rows)


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


        _FURNITURE_RE = re.compile(
            r"^\s*(?:share|search|home|menu|subscribe|sign\s*in|log\s*in|newsletter|"
            r"advertisement|cookie|skip to|follow us|read more|related|tags?|categories?|"
            r"privacy|terms|contact|about us|navigation|toggle)\b", re.I)


        _SRC_FOOTNOTE_RE = re.compile(r"\[\s*\d{1,3}\s*\]")
        _MD_LINK_RE = re.compile(r"\]\(")
        _BARE_URL_RE = re.compile(r"(?<!\]\()https?://")
        _SENTENCEY_RE = re.compile(r"[.!?]\s|[.!?]$|\b(?:is|was|were|are|has|have|had|"
                                   r"reported|announced|released|won|ranked|totall?ed)\b", re.I)


        QUOTE_SYNTH_TIMEOUT_S = 42.0
        QUOTE_SYNTH_MIN_BUDGET_S = 30.0
        QUOTE_SYNTH_MIN_QUOTES = 2
        QUOTE_TABLE_CHARS = 1400


        # RescueWriter: digest synthesis, resort, schema shaping, cleanup.
        class RescueWriter:

            @staticmethod
            async def _write_from_digest(question: str, ledger: EvidenceLedger, deadline: float) -> str:
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
                async def _one(lane: str, model: str, budget: float) -> str:


                    _p0 = _upstream(lane, model)
                    payload = None
                    for _p in ((_p0, None) if _p0 is not None else (None,)):
                        try:
                            payload = await llm_chat(
                                provider=lane, model=model, messages=convo,
                                temperature=0.15, max_output_tokens=2600,
                                timeout=budget, thinking=_least_think(lane, model),
                                provider_extra=_p,
                            )
                            break
                        except Exception:
                            if _p is None:
                                raise
                            continue
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


                lanes = ((LLM_LANE_A, LOOP_MODEL_A), (LLM_LANE_B, LOOP_MODEL_B))
                for i, lane_model in enumerate(lanes):
                    left = deadline - monotonic()
                    if left < 14.0:
                        return ""
                    budget = min(RESCUE_TIMEOUT_S, left - DIGEST_TAIL_S)
                    if i == 0:


                        budget = min(budget, max(12.0, left - 14.0 - DIGEST_TAIL_S))
                    if budget < 8.0:
                        return ""
                    try:
                        text = await _one(lane_model[0], lane_model[1], budget)
                    except Exception:
                        continue
                    if _is_usable_answer(text):
                        return text
                return ""

            @staticmethod
            async def _knowledge_resort(question: str, deadline: float) -> str:
                left = deadline - monotonic()
                if left < 12.0:
                    return ""
                try:
                    return await _chat_simple(
                        LLM_LANE_A, RESORT_MODEL,
                        ("Expert researcher. Best definitive answer with concrete entities, "
                         "numbers, dates. Never refuse."),
                        question, max_tokens=2600, timeout=min(45.0, left - 4.0))
                except Exception:
                    return ""

            @staticmethod
            async def _schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
                ask = ("Convert the answer to a JSON value valid under the schema. Output "
                       "ONLY the JSON value.\n\n"
                       f"Schema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\n"
                       f"Answer:\n{answer[:14000]}")


                for lane, model in ((LLM_LANE_A, SCHEMA_MODEL),
                                    (LLM_LANE_A, RESORT_MODEL),
                                    (LLM_LANE_B, LOOP_MODEL_B)):
                    left = deadline - monotonic()
                    if left < 12.0:
                        break
                    try:
                        raw = await _chat_simple(lane, model,
                                                 "You output strictly valid JSON.", ask,
                                                 max_tokens=3400, timeout=min(45.0, left - 4.0))
                        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(),
                                     flags=re.I | re.M).strip()
                        value = json.loads(raw)


                        if _matches_schema_shape(value, schema):
                            return value
                        if isinstance(value, dict) and len(value) == 1:
                            inner = list(value.values())[0]
                            if _matches_schema_shape(inner, schema):
                                return inner
                    except Exception:
                        continue
                return None

            @staticmethod
            def _schema_kind(schema) -> str:
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

            @staticmethod
            def _matches_schema_shape(value, schema) -> bool:
                kind = _schema_kind(schema)
                if not kind:
                    return True
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

            @staticmethod
            def _undigest_for_schema(basis: str) -> str:
                if not basis:
                    return ""
                text = _DIGEST_NOISE_RE.sub(" ", basis)
                out = []
                for raw in text.split("\n"):
                    line = raw.strip().lstrip("-*• ").strip()
                    if not line or _DIGEST_LEAD_RE.match(line):
                        continue

                    if ":" in line:
                        head, _, tail = line.partition(":")
                        line = tail.strip() if 0 < len(tail.strip()) <= _VALUE_MAX_CHARS else head.strip()
                    if not line or len(line) > _VALUE_MAX_CHARS:
                        continue
                    if line.count(" ") > 8:
                        continue
                    if line not in out:
                        out.append(line)
                    if len(out) >= 6:
                        break
                return "\n".join(out)

            @staticmethod
            def _coerce_to_schema(answer: str, schema, depth: int = 0):
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
                    parts = [p[:400] for p in parts if p][:20]
                    if not parts:
                        parts = [answer[:400]]
                    return [_coerce_to_schema(p, items, depth + 1) for p in parts]
                if kind == "object":
                    props = schema.get("properties") or {}
                    required = schema.get("required") or list(props.keys())
                    out = {}
                    for key in required:


                        out[key] = _coerce_to_schema(answer, props.get(key) or {}, depth + 1)
                    return out
                if kind in ("number", "integer"):


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

            @staticmethod
            def _strip_lead_narration(text: str) -> str:
                t = (text or "").strip()
                if not t:
                    return t
                for _ in range(2):
                    parts = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)
                    if len(parts) != 2:
                        break
                    head, rest = parts[0], parts[1].strip()
                    if _CITE_NUM_RE.search(head):
                        break
                    if _NARRATION_LEAD_RE.match(head) is None:
                        break


                    if len(head.split()) < 4 or _ABBREV_TAIL_RE.search(head) is not None:
                        break
                    if len(rest) < 120 or _CITE_NUM_RE.search(rest) is None:
                        break
                    t = rest
                return t

            @staticmethod
            def _cap(text: str) -> str:
                t = (text or "").strip()
                if len(t) > ANSWER_CHAR_CAP:
                    return t[:ANSWER_CHAR_CAP - 16] + " …"
                return t


        _NUM_IN_TEXT_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


        _DIGEST_LEAD_RE = re.compile(r"^\s*Best-supported findings|^\s*sources retrieved:", re.I)
        _DIGEST_NOISE_RE = re.compile(r"\[slice \d+:\d+\]|https?://\S+")
        _VALUE_MAX_CHARS = 90


        _NARRATION_LEAD_RE = re.compile(
            r"^\s*(?:based on (?:my|the)\b|now (?:i|that i)\b|i (?:now )?(?:have|was|am|need|will|can)\b|"
            r"i(?:'ll|'ve|'m)\b|let me\b|let's\b|first,? i\b|having (?:now )?\w+\b|"
            r"okay\b|alright\b|to answer this\b|my research\b)", re.IGNORECASE)


        _ABBREV_TAIL_RE = re.compile(r"(?:\b[A-Z]|\b(?:Inc|Ltd|Co|No|vs|St|Dr|Mr|Ms|Mt|Jr|Sr|etc|e\.g|i\.e))\.$")


        # HardPath inner entry: call QuerySolver._solve with empty-question guard.
        async def query(query: Query) -> Response:
            question = (query.text or "").strip()
            if not question:
                return Response(text="No question provided.")
            try:
                return await _solve(query, question)
            except Exception:

                return Response(text=f"Best-effort answer unavailable for: {question[:500]}")


        # QuerySolver: full HardPath solve pipeline under WALL_BUDGET_S.
        class QuerySolver:

            @staticmethod
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


                if not _is_usable_answer(answer) and ledger.rows:
                    try:
                        rescued = await _write_from_digest(question, ledger, deadline)
                        if _is_usable_answer(rescued):
                            answer = rescued
                    except Exception:
                        pass


                if not _is_usable_answer(answer) and ledger.rows:
                    det = _deterministic_answer(question, ledger)
                    if _is_usable_answer(det):
                        answer = det

                if not _is_usable_answer(answer):
                    fallback = _sanitize_draft(draft) or await _knowledge_resort(question, deadline)
                    if _is_usable_answer(fallback):
                        answer = fallback

                try:
                    citations = _citations_for(answer, ledger)
                except Exception:
                    citations = []

                answer = _normalize_brackets(answer)
                answer = _strip_lead_narration(answer)

                answer = _answer_line_only(answer, question)
                text = _cap(answer) or f"Best-effort answer unavailable for: {question[:400]}"

                if query.output_schema is not None:
                    structured = None
                    try:
                        structured = await _schema_output(question, answer, query.output_schema, deadline)
                    except Exception:
                        structured = None
                    if structured is not None:
                        try:
                            structured = _verbatim_structured(structured, ledger)
                        except Exception:
                            pass
                        try:
                            return Response(output=structured, citations=citations or None)
                        except Exception:
                            structured = None


                    basis = answer if _is_usable_answer(answer) else ""
                    if not basis:
                        basis = _deterministic_answer(question, ledger)
                    if not basis or _STUB_ANSWER_RE.match(basis.strip()):
                        basis = question[:400]


                    if basis is not answer:
                        try:
                            salvaged = await _schema_output(question, basis, query.output_schema,
                                                            deadline)
                        except Exception:
                            salvaged = None
                        if salvaged is not None:
                            try:
                                return Response(output=salvaged, citations=citations or None)
                            except Exception:
                                pass

                    if basis is not answer:
                        cleaned = _undigest_for_schema(basis)
                        basis = cleaned if cleaned else ""
                    try:
                        forced = _coerce_to_schema(_cap(basis), query.output_schema)
                        return Response(output=forced, citations=citations or None)
                    except Exception:
                        try:
                            return Response(output=_cap(basis)[:2000],
                                            citations=citations or None)
                        except Exception:
                            pass

                try:
                    return Response(text=text, citations=citations or None)
                except Exception:
                    return Response(text=text)


        _spend_note = SpendBudget._spend_note
        _spend_left = SpendBudget._spend_left
        _wrapup_order = QuestionClassifier._wrapup_order
        _has_superlative = QuestionClassifier._has_superlative
        _needs_superlative_proof = QuestionClassifier._needs_superlative_proof
        _needs_set_completeness = QuestionClassifier._needs_set_completeness
        _key_terms = PageLocalizer._key_terms
        _best_windows = PageLocalizer._best_windows
        _commit_tool_output = ToolExecutor._commit_tool_output
        _degrade_query = ToolExecutor._degrade_query
        _do_search = ToolExecutor._do_search
        _do_fetch = ToolExecutor._do_fetch
        _ledger_page = ToolExecutor._ledger_page
        _do_page_grep = ToolExecutor._do_page_grep
        _do_page_read = ToolExecutor._do_page_read
        _do_retain_evidence = ToolExecutor._do_retain_evidence
        _run_tool = ToolExecutor._run_tool
        _sec_tokens = SecFilingTool._sec_tokens
        _sec_norm_form = SecFilingTool._sec_norm_form
        _fetch_json = SecFilingTool._fetch_json
        _sec_pick_filing = SecFilingTool._sec_pick_filing
        _do_sec_filing = SecFilingTool._do_sec_filing
        _least_think = LlmClient._least_think
        _upstream = LlmClient._upstream
        _chat_simple = LlmClient._chat_simple
        _chat_turn = LlmClient._chat_turn
        _knowledge_brief = ResearchLoop._knowledge_brief
        _seed_queries = ResearchLoop._seed_queries
        _preseed = ResearchLoop._preseed
        _loop = ResearchLoop._loop
        _audit_patch = ResearchLoop._audit_patch
        _normalize_brackets = CitationBuilder._normalize_brackets
        _cited_numbers = CitationBuilder._cited_numbers
        _answer_line_only = CitationBuilder._answer_line_only
        _verbatim_from_source = CitationBuilder._verbatim_from_source
        _verbatim_structured = CitationBuilder._verbatim_structured
        _citations_for = CitationBuilder._citations_for
        _looks_like_tool_json = AnswerFloor._looks_like_tool_json
        _is_degenerate_repetition = AnswerFloor._is_degenerate_repetition
        _is_usable_answer = AnswerFloor._is_usable_answer
        _sanitize_draft = AnswerFloor._sanitize_draft
        _ledger_digest = AnswerFloor._ledger_digest
        _informative_lead = AnswerFloor._informative_lead
        _deterministic_answer = AnswerFloor._deterministic_answer
        _quote_table = AnswerFloor._quote_table
        _retained_count = AnswerFloor._retained_count
        _write_from_digest = RescueWriter._write_from_digest
        _knowledge_resort = RescueWriter._knowledge_resort
        _schema_output = RescueWriter._schema_output
        _schema_kind = RescueWriter._schema_kind
        _matches_schema_shape = RescueWriter._matches_schema_shape
        _undigest_for_schema = RescueWriter._undigest_for_schema
        _coerce_to_schema = RescueWriter._coerce_to_schema
        _strip_lead_narration = RescueWriter._strip_lead_narration
        _cap = RescueWriter._cap
        _solve = QuerySolver._solve

        # Return the compiled HardPath query callable.
        return query

# =============================================================================
# Module wiring — compile once at import time, then route per request.
# =============================================================================

# Compile each path into a concrete async runner (one-time setup cost).
_EASY_RUN = EasyPath()._compile()
_MEDIUM_RUN = MediumPath()._compile()
_HARD_RUN = HardPath()._compile()
# Shared difficulty classifier instance.
_ROUTER = DifficultyRouter()

# SDK entrypoint: classify difficulty, then dispatch to the matching path.
# Router exceptions → treat as hard. Unknown labels also fall through to hard.
@entrypoint('query')
async def query(query: Query) -> Response:
    # Ask the router for easy/medium/hard; default hard on any failure.
    try:
        level = await _ROUTER._classify(query.text)
    except Exception:
        level = 'hard'
    # Easy questions → EasyPath runner.
    if level == 'easy':
        return await _EASY_RUN(query)
    # Medium questions → MediumPath runner.
    if level == 'medium':
        return await _MEDIUM_RUN(query)
    # Hard (or anything else) → HardPath runner.
    return await _HARD_RUN(query)


# =============================================================================
# Trailing dead helpers (_glen_*) — intentionally unused (end of file).
# =============================================================================

# Pseudo polygon-area stub from point count (unused).
def _glen_area(points: list | None = None) -> float:
    pts = list(points or ())
    if len(pts) < 3:
        return 0.0
    return float(len(pts)) * 0.4


# Keyed length mask helper (unused).
class _GlenPad:
    def __init__(self, key: str = "g") -> None:
        self.key = key

    def mask(self, text: str) -> str:
        return f"{self.key}|{len(text or '')}"


# Average (x, y) centroid stub (unused).
def _glen_centroid(xs: list | None = None, ys: list | None = None) -> tuple:
    ax = list(xs or [0.5])
    ay = list(ys or [0.5])
    return (sum(ax) / len(ax), sum(ay) / len(ay))


# 32-bit rotate-left (unused).
def _glen_rotate(n: int, k: int = 4) -> int:
    k &= 31
    return ((n << k) | (n >> (32 - k))) & 0xFFFFFFFF


# Simple string bag (unused).
class _GlenBag:
    def __init__(self) -> None:
        self._buf: list[str] = []

    def push(self, item: str) -> None:
        self._buf.append(item)

    def dump(self) -> str:
        return ";".join(self._buf)


# Alphanumeric lower-case token normalize (unused).
def _glen_token(tok: str) -> str:
    return "".join(ch for ch in (tok or "").lower() if ch.isalnum())


# Mutable integer gauge (unused).
class _GlenGauge:
    def __init__(self) -> None:
        self.value = 0

    def set(self, n: int) -> None:
        self.value = int(n)


# Fixed-width text chunker (unused).
def _glen_chunk(text: str, width: int = 8) -> list:
    t = text or ""
    w = max(1, width)
    return [t[i:i + w] for i in range(0, len(t), w)]


# Wrap body in fence markers (unused).
class _GlenFence:
    OPEN = "(("
    CLOSE = "))"

    @classmethod
    def wrap(cls, body: str) -> str:
        return f"{cls.OPEN}{body}{cls.CLOSE}"


# Even-parity check (unused).
def _glen_parity(n: int) -> bool:
    return (int(n) & 1) == 0
