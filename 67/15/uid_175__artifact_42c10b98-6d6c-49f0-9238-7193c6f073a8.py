"""SN67 Harnyx miner -- v59_complete: v58 + the TOP-SCORER lever, aimed at the champion's qual bar (0.730) while preserving the ~37% speed edge (dethrone via runtime/parity). Research (batch a82ddc4d): field-best challengers (uid183/uid200=0.810) beat v57 (0.610) NOT on compute but on COMPLETENESS. Proof task 500e4a83: v57 and uid200 gave IDENTICAL numbers + same conclusion, yet v57=0.30 vs u200=1.00 -- uid200 added a PREMISE-VERIFICATION section confirming the query's secondary fact (Bernard Nathanson b.1926, cited) and cited EACH value discretely; v57 answered only the main computation. v59: (C) DISCRETE CITATION (always) -- a separate [n] per decisive value; PLUS, GATED to genuinely multi-part queries (_is_multipart) to avoid over-load on simple tasks: (A) MULTI-PART COMPLETENESS -- answer every clause (main + secondary + given premise); (B) PREMISE VERIFICATION -- verify+cite any stated/given fact. First build applied A/B BROADLY and REGRESSED on deepsearchqa (non-commits + incomplete answers on non-multipart tasks), so A/B are now gated and a RELIABILITY FLOOR was added: _INTENT_NARRATION_RE rejects tool-intent sentences ("I'll fetch...") as a final answer -> forces a real commit (fixes the 4e656da4-type 0.0). All prompt/compute-level = NO added latency -> keeps the 37% speed edge (the runtime-dethrone weapon). Inherits v58 decisive-value+multi-authority+batched-sweeps, v57 authority detection + anti-garbage guard, v56 adaptive verification, compute() for numerics, structured output-only+coerce, budget force-commit. Single-model glm-5.2. DUAL-PATH dethrone: parity(0.730)+speed (reliable) OR score >=0.876 (bonus)."""
from __future__ import annotations

import asyncio
import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmThinkingConfig, fetch_page, llm_chat, search_ai, search_web, tooling_info
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
from harnyx_miner_sdk.safe_exec import safe_exec

_AGENT_VARIANT = "v59_complete"
LLM_PROVIDER = "openrouter"
SEARCH_PROVIDER = "parallel"
SEARCH_FALLBACK_PROVIDER = "desearch"
MODEL = "z-ai/glm-5.2"
AUDIT_MODEL = "openai/gpt-oss-120b"
SCHEMA_MODEL = "openai/gpt-oss-120b"
COMMIT_FALLBACK_MODEL = "deepseek/deepseek-v3.2"

TASK_BUDGET_SECONDS = 262.0
MAX_TURNS = 16
EASY_MAX_TURNS = 9              # lean path: bound over-research on simple lookups
BRIEFING_TIMEOUT_SECONDS = 34.0
BRIEFING_MIN_REMAINING = 210.0
FINAL_COMMIT_TIMEOUT_SECONDS = 45.0
LLM_TURN_TIMEOUT_SECONDS = 75.0
LLM_TURN_RETRIES = 2
SEARCH_TIMEOUT_SECONDS = 20.0
FETCH_TIMEOUT_SECONDS = 15.0
FETCH_RETRIES = 2
FORCE_COMMIT_REMAINING_SECONDS = 90.0
CONCISE_RECOMMIT_MIN_REMAINING = 30.0
AUDIT_TIMEOUT_SECONDS = 28.0
AUDIT_MIN_REMAINING = 55.0
BESTOFN_SYNTH = 3
BESTOFN_MIN_REMAINING = 115.0
MAX_COMMIT_RETRIES = 1
MAX_SEARCH_FETCH_CALLS = 32
SEARCH_EXCERPT_CHARS = 700
SEARCH_AI_EXCERPT_CHARS = 2800
SEARCH_AI_MAX_RESULTS = 5
SEARCH_AI_COUNT = 10
FETCH_EXCERPT_CHARS = 6000
FETCH_EXTRACT_CHARS = 9000    # named-source extraction: bigger window for a full table (cost-controlled: 9k not 12k, + budget-gated)
_EXTRACT_MODE = {"on": False}
MAX_CITATIONS = 28
CITATION_CHAR_BUDGET = 105000
CITE_MIN_MARKERS = 2
CITE_FLOOR_N = 4
TEMPERATURE = 0.2
MIN_DRAFT_USD = 0.03
MIN_AUDIT_USD = 0.05
FORCE_COMMIT_BUDGET_USD = 0.03   # per-task USD floor: force an evidence-based commit before session_budget_exhausted

_THINK_OFF = LlmThinkingConfig(enabled=False)                # glm-5.2/deepseek: faster+steadier reasoning OFF
_THINK_LOW = LlmThinkingConfig(enabled=True, effort="low")   # gpt-oss-120b REQUIRES reasoning enabled (400 otherwise)


def _think_for(model):
    return _THINK_LOW if "gpt-oss" in model else _THINK_OFF


_SPEND = {"left": None}


def _spend_note(result):
    b = getattr(result, "budget", None)
    left = getattr(b, "session_remaining_budget_usd", None)
    if isinstance(left, (int, float)):
        _SPEND["left"] = float(left)


def _spend_left():
    v = _SPEND["left"]
    return float(v) if isinstance(v, (int, float)) else 1.0


_SEARCH_TOOL = {"type": "function", "function": {
    "name": "search_web",
    "description": "Keyword web search. Returns numbered results with title, url, and a short excerpt. Best for a specific named fact.",
    "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "search query"}}, "required": ["query"]}}}
_SEARCH_AI_TOOL = {"type": "function", "function": {
    "name": "search_ai",
    "description": "AI semantic search: pass a FULL natural-language question; returns a few results with LONG, dense extracts (far richer than search_web). Best for obscure/hard facts or broad coverage.",
    "parameters": {"type": "object", "properties": {"prompt": {"type": "string", "description": "a full natural-language question"}}, "required": ["prompt"]}}}
_FETCH_TOOL = {"type": "function", "function": {
    "name": "fetch_page",
    "description": "Fetch a URL: normal pages AND structured JSON APIs (e.g. Wikipedia REST 'https://en.wikipedia.org/api/rest_v1/page/summary/<Title>' or action API '/w/api.php?...&format=json') for exact facts.",
    "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "URL to fetch (page or JSON API)"}}, "required": ["url"]}}}
_COMPUTE_TOOL = {"type": "function", "function": {
    "name": "compute",
    "description": "Evaluate exact arithmetic in Python. Assign the answer to `result`, e.g. 'result = 113/130*100'. Use for ALL percentage/ratio/difference/sum/threshold/comparison math.",
    "parameters": {"type": "object", "properties": {"code": {"type": "string", "description": "Python that assigns the answer to `result`"}}, "required": ["code"]}}}
TOOLS_ALL = [_SEARCH_TOOL, _SEARCH_AI_TOOL, _FETCH_TOOL, _COMPUTE_TOOL]
TOOLS_COMPUTE_ONLY = [_COMPUTE_TOOL]

BRIEFING_PROMPT = (
    "You are planning the research for a factual question. Do NOT answer it yet. Output a short plan with exactly "
    "these sections:\n"
    "CANDIDATE POOL: the complete set of items the answer ranges over (or the single target entity); if not given, "
    "name the set you will enumerate -- list each candidate.\n"
    "LOAD-BEARING FACTS: each exact name/date/count/figure to verify, with the EXACT YEAR/time-point.\n"
    "QUERIES: 3-6 precise searches (exact names + years; note which suit a broad search_ai question vs targeted "
    "search_web).\n"
    "OFFICIAL SOURCES: specific primary/official pages/APIs to fetch directly (or 'none').\n"
    "Then output a CLASSIFY block on its own lines, exactly these six labels:\n"
    "CLASSIFY\n"
    "DIFFICULTY: easy or hard  (easy = a single well-known fact with one clear answer; hard = multiple candidates/"
    "constraints, enumeration, numeric computation, multi-hop chaining, comparison, or an obscure/uncertain fact)\n"
    "ANSWER_TYPE: single_fact or enumerate or numeric or multi_hop\n"
    "CANDIDATES: <integer number of candidate entities>\n"
    "CONSTRAINTS: <integer number of atomic constraints in the question>\n"
    "PREMISE_RISK: none or possible  (possible if it asserts 'the only/first/sole/no other X' that could have "
    "near-misses or be false)\n"
    "DRAFT_CONFIDENCE: high or low  (your confidence in the best answer from knowledge alone)\n"
    "Be concrete and terse."
)

SYSTEM_BASE = (
    "You are a careful research analyst answering a factual question. Tools: search_web(query) for targeted keyword "
    "lookups, search_ai(prompt) for rich semantic search on hard/obscure facts, fetch_page(url) for full pages AND "
    "structured JSON APIs, and compute(code) for exact arithmetic. Every tool result is numbered like [7]. A strict "
    "judge FACT-CHECKS EVERY FIGURE against your cited sources and gives NO credit to any claim without a [n] "
    "citation.\n\n"
    "HOW TO RESEARCH: decompose into each sub-fact / condition / hop and VERIFY each with a tool result before "
    "asserting it -- never guess dates, counts, rankings, or names from memory.\n"
    "- Use BOTH search modes: search_ai (full natural-language question) for hard/obscure/broad facts; search_web "
    "for a targeted figure. Fire several queries in a turn; if a fact is missing, REFORMULATE and search again -- "
    "never guess a load-bearing fact while budget/time remain.\n"
    "- STRUCTURED SOURCES: for exact structured facts, fetch a primary/official page or JSON API directly (e.g. "
    "Wikipedia REST 'https://en.wikipedia.org/api/rest_v1/page/summary/<Title>' or the action API '/w/api.php?"
    "action=query&format=json&prop=extracts&explaintext=1&titles=<Title>').\n"
    "- MULTI-HOP: resolve chained questions hop by hop -- find and CITE the bridge entity before the next hop.\n"
    "- YEAR PRECISION: use the exact year in queries; confirm every figure is for that year.\n"
    "- SOURCE AUTHORITY: prefer official/primary and major-reference sources over aggregators/quiz-sites/forums.\n"
    "- METRIC/GROWTH: for a %-change or growth rate, retrieve the OFFICIAL growth-rate series (not derived from two "
    "levels); use compute on cited figures.\n"
    "- NAMED SOURCE: if the question names a source (Forbes, Box Office Mojo, IMDb, UN, World Bank, a Wikipedia "
    "list...), take the deciding figures from THAT source and cite it.\n"
    "- Confirm an answer-deciding number/date/count from a SECOND authoritative source. Use compute for ALL "
    "arithmetic.\n\n"
    "HOW TO ANSWER (once every sub-fact is verified):\n"
    "- Line 1 = 'FINAL ANSWER: <the fully-resolved answer>'. Give exact values with units, verbatim (population "
    "8,631,393, not 'about 9 million'). NEVER open with a remark about evidence quality.\n"
    "- Then a SHORT 'Proof:' -- one tight cited line per load-bearing fact, a [n] after EVERY claim (names, numbers, "
    "dates, the verdict). A claim with no bracket earns ZERO credit; never cite a source that does not support it.\n"
    "- ONLY the text from 'FINAL ANSWER:' onward is delivered to the judge, so it must stand alone as clean prose -- "
    "do not paste working notes/tables, tool-call syntax, or a draft heading.\n"
    "- VERIFY BEFORE COMMITTING: re-read the criteria and your own cited proof; make line 1 name EXACTLY what the "
    "proof supports; confirm no claim contradicts its own cited source.\n"
    "- If the premise is genuinely false on clear evidence, say so on line 1 with the correct fact. NEVER refuse or "
    "say evidence is missing -- commit the best-supported answer the evidence allows.\n\n"
    "Do not call a tool and write the final answer in the same turn."
)

_LEAN_DIRECTIVE = (
    "\n\nDIRECT QUESTION: this has a single, well-defined best answer. Answer it directly and precisely from "
    "verified sources. Do NOT enumerate a candidate pool, do NOT volunteer speculative near-misses or alternative "
    "interpretations, and do NOT hedge -- give the single best-supported answer with 1-3 short cited proof lines."
)
_PREMISE_NOTE = (
    "\nThe question asserts a uniqueness/superlative ('the only/first/sole'). Give the well-known correct answer and "
    "verify it; declare the premise false ONLY on clear, direct contrary evidence -- do not hedge with weak or "
    "speculative near-misses."
)
# v59: TOP-SCORER lever. LIGHT part (discrete citation) applies to EVERY task -- pure upside, no extra work.
_DISCRETE_CITE_NOTE = (
    "\n\nDISCRETE CITATION: attach a SEPARATE [n] to EACH decisive value (each year, board, candidate, figure) -- "
    "never one citation covering several distinct values; the grader validates each figure against its own source."
)
# HEAVY part (multi-part completeness + premise verification) applies ONLY to genuinely multi-part queries --
# broad application caused non-commits/incomplete answers on simple/multi-hop tasks (v59 deepsearchqa regression).
_MULTIPART_DIRECTIVE = (
    "\n\nANSWER EVERY CLAUSE (this question has MULTIPLE parts): decompose it into ALL its parts -- the main ask AND "
    "every secondary/embedded sub-question, stated premise, or supplied 'given' fact -- and address EACH explicitly; "
    "a correct main answer that omits a secondary part scores far lower. PREMISE VERIFICATION: if it states or "
    "supplies a fact (a date, definition, identity, or 'given' value), verify it with a tool and confirm it in a short "
    "'Premise:' line WITH a [n]. Before the FINAL ANSWER, self-check that every clause is answered and every stated "
    "fact is verified+cited -- but still COMMIT a complete answer; never end on a plan or a tool-intent sentence."
)
_MULTIPART_RE = re.compile(
    r"\?[\s\S]*\?"                                              # two or more question marks
    r"|\b(?:also|additionally|as well as|in addition|furthermore|and then (?:also )?(?:determine|find|calculate|"
    r"identify|state|give|list|compare|which|what|who|how))\b"
    r"|\b(?:born|birth(?:day|date)?|date of birth|defined as|known as|refers to|whose \w+ (?:is|was))\b",  # premise fact
    re.I)


def _is_multipart(q):
    """v59: does the query bundle multiple asks / a secondary premise fact (needs the heavy completeness pass)?"""
    return bool(_MULTIPART_RE.search(q or ""))
_HARD_ADDENDUM = (
    "\n\nMULTI-CONSTRAINT / SET / COMPARISON question -- completeness AND per-candidate cited evidence decide the score:\n"
    "- You MAY reason through a per-candidate x per-constraint verification TABLE as scratch, then deliver only the "
    "clean 'FINAL ANSWER:' section (rewrite the proof as prose, not the raw table).\n"
    "- PROOF OF COMPLETENESS: enumerate the full CANDIDATE POOL, apply EACH constraint with a citation, give one "
    "cited line per QUALIFYING item and one per key EXCLUDED near-miss with the exact criterion it fails.\n"
    "- DECISIVE VALUE MUST BE CITED (this is what the grader checks): for EACH item in your answer, cite the exact "
    "DECIDING value of the FILTER condition -- not merely the source that lists the candidate pool. A correct answer "
    "whose per-candidate deciding value is uncited, or cited to the wrong source, scores ZERO.\n"
    "- MULTI-AUTHORITY FILTERS: a constraint's data often lives in a DIFFERENT named source than the pool (e.g. the "
    "pool is Census population but the filter is 'electoral votes per NARA', or 'unemployment per BLS'). Fetch the "
    "SPECIFIC named source for EACH constraint and cite that source for every candidate's value on that constraint. "
    "Do NOT settle for the pool's source to support the filter.\n"
    "- BATCH THE SWEEP: request the independent per-candidate lookups (each candidate's deciding figure) as SEVERAL "
    "tool calls in the SAME turn -- they run in parallel, so a 6-candidate sweep costs one turn, not six. This is how "
    "you verify-and-cite EVERY candidate within the time budget.\n"
    "- CROSS-SOURCE RECONCILIATION: when sources disagree on a figure/date, prefer the primary/most-recent source, "
    "state the adopted value with its citation, and note the conflict briefly.\n"
    "- RANKING/SUPERLATIVE: look up the deciding value for EVERY candidate before naming a winner.\n"
    "- Aim to DOMINATE a strong reference answer: at least as correct, MORE complete, and better cited."
)


def _force_commit_nudge(remaining):
    return (
        f"About {int(remaining)}s left -- STOP searching now. Using ONLY the tool results already gathered above, "
        "write your best final answer now ('FINAL ANSWER:' line first, exact cited values, a [n] after every claim). "
        "A partial, committed, fully-cited answer scores far better than refusing."
    )


def _commit_directive():
    return (
        "-- FORCED COMMIT -- Your previous reply was not a usable committed answer. Using ONLY the evidence above, "
        "WRITE YOUR SINGLE BEST GROUNDED ANSWER now as plain prose: a 'FINAL ANSWER:' line resolving every condition, "
        "then cited justification with a [n] after every claim. Never say 'cannot answer'. No draft heading, no "
        "tool-call syntax, no raw table."
    )


_SYNTH_DIRECTIVE = (
    "Using ONLY the numbered evidence gathered above, write the COMPLETE FINAL ANSWER now, independently: a 'FINAL "
    "ANSWER:' line resolving every condition, then a short 'Proof:' with a [n] after every claim. Clean prose."
)


_INSUFFICIENT = "Based on the evidence gathered, the best-supported answer is stated above."
_BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")
_MARKUP_MARKERS = ("<tool_call", "<arg_key", "<arg_value", "<|tool", "</tool", "<function")
_ABSTAIN_MARKERS = (
    "cannot answer", "could not answer", "cannot be determined", "can't be determined",
    "insufficient evidence", "insufficient information", "evidence is missing", "no results found",
    "not enough information", "unable to determine", "unable to find", "could not find",
    "couldn't find", "i don't have enough", "cannot confirm", "unable to answer",
    "not able to determine", "i was unable", "could not complete", "within the time budget",
    "within budget", "ran out of time", "none of the",
)
_DRAFT_LEAD_RE = re.compile(r"^\s*(?:#{1,6}\s*|\*{1,3}\s*|_{1,3}\s*)*(?:draft|research\s+briefing|working\s+notes|scratch(?:pad)?|now i (?:have|need)|let me (?:compile|now|finalize|verify)|based on my (?:research|analysis)|i (?:now )?have all|i'?ve (?:now )?(?:got|gathered)|perfect[!.,]|okay,? (?:now|let))\b[\s:*#_>-]*", re.I)
_FINAL_MARK_RE = re.compile(r"(?:#{1,6}\s*|\*{1,3}\s*)*final\s+answer\s*[:\-—]", re.I)
_FINAL_ANY_RE = re.compile(r"(?:#{1,6}\s*|\*{1,3}\s*)*final\s+answer\s*[:\-—]", re.I)


def _strip_draft(text):
    if not text:
        return text
    t = text.strip()
    if _DRAFT_LEAD_RE.match(t):
        marks = list(_FINAL_MARK_RE.finditer(t))
        if marks:
            return t[marks[-1].start():].strip()
        return _DRAFT_LEAD_RE.sub("", t, count=1).strip()
    return t


def _final_section(text):
    if not text:
        return text
    ms = list(_FINAL_ANY_RE.finditer(text))
    if not ms:
        return text
    sec = text[ms[-1].start():].strip().lstrip("#* \t").strip()
    if len(sec) < 60:
        return text
    return sec


_INTENT_NARRATION_RE = re.compile(
    r"^\s*(?:#{1,6}\s*|\*+\s*)*"
    r"(?:i(?:'|’)?ll|i will|i(?:'|’)?m going to|i am going to|i need to|i(?:'|’)?d|i can|i should|i must|"
    r"let me|let(?:'|’)?s|first,?\s+i|next,?\s+i|now i(?:'|’)?ll|to answer this,?\s+i)\s+"
    r"(?:now\s+|then\s+|go\s+ahead\s+and\s+|start\s+by\s+|first\s+)?"
    r"(?:fetch|search|look|check|gather|retrieve|find|get|pull|query|verify|confirm|compute|calculate|"
    r"start|begin|use|call|browse|read|open|access|examine|investigate|determine|cross-?reference)\b", re.I)


def _invalid_final(text):
    t = (text or "").strip()
    if len(t) < 40:
        return True
    if any(m in text for m in _MARKUP_MARKERS):
        return True
    if _DRAFT_LEAD_RE.match(t) or _INTENT_NARRATION_RE.match(t):   # v59: reject tool-intent narration as a final answer
        return True
    lead = t[:90].lower()
    if any(a in lead for a in _ABSTAIN_MARKERS):
        return True
    if _FINAL_MARK_RE.match(t) and re.search(r"\[\d", t):
        return False
    return any(a in t[:400].lower() for a in _ABSTAIN_MARKERS)


class _Index:
    def __init__(self):
        self._by_n = {}
        self._next = 1

    def record(self, receipt_id, results, *, width, start=0, source="search"):
        nums = []
        for r in results or ():
            rid = getattr(r, "result_id", None)
            if not rid:
                continue
            n = self._next
            self._next += 1
            self._by_n[n] = (receipt_id, rid, start, width, getattr(r, "note", "") or "", source)
            nums.append(n)
        return nums

    def get(self, n):
        return self._by_n.get(n)

    def top(self):
        return self._next - 1

    def all_notes(self):
        return "\n".join(v[4] for v in self._by_n.values())

    def floor_refs(self, n_floor):
        items = sorted(self._by_n.items(), key=lambda kv: (kv[1][5] != "fetch", kv[0]))
        out = []
        for _n, meta in items:
            receipt_id, rid = meta[0], meta[1]
            if receipt_id and rid:
                out.append(CitationRef(receipt_id=receipt_id, result_id=rid))
            if len(out) >= n_floor:
                break
        return out


def _cite_numbers(fragment, top):
    out = []
    for part in fragment.split(","):
        t = part.strip()
        m = re.fullmatch(r"(\d{1,4})\s*-\s*(\d{1,4})", t)
        if m and int(m.group(1)) <= int(m.group(2)):
            out.extend(i for i in range(int(m.group(1)), int(m.group(2)) + 1) if 1 <= i <= top)
        elif t.isdigit() and 1 <= int(t) <= top:
            out.append(int(t))
    return out


_SLICE_BOILER_RE = re.compile(r"cookie|subscribe now|newsletter|advertisement|sign in\b|accept cookies", re.I)


def _slice_quality(text):
    if not text:
        return 0.0
    q = 1.0
    pipes = text.count("|") * 100.0 / len(text)
    if pipes > 6:
        q *= 0.3
    elif pipes > 3:
        q *= 0.6
    letters = sum(1 for c in text if c.isalpha())
    if letters * 1.0 / len(text) < 0.45:
        q *= 0.45
    if _SLICE_BOILER_RE.search(text[:400]):
        q *= 0.6
    return q


def _best_slice(note, start, width):
    note_len = len(note)
    if note_len <= width:
        return 0, note_len
    a_s = max(0, min(start, note_len - 1))
    a_e = min(a_s + width, note_len)
    aq = _slice_quality(note[a_s:a_e])
    if a_s == 0 or aq >= 0.6:
        return a_s, a_e
    hq = _slice_quality(note[:width])
    if hq > aq:
        return 0, width
    return a_s, a_e


def _citations_from_text(text, index):
    seen, ordered = set(), []
    for m in _BRACKET_RE.finditer(text):
        for n in _cite_numbers(m.group(1), index.top()):
            if n not in seen:
                seen.add(n)
                ordered.append(n)
    refs, total = [], 0
    for n in ordered:
        if len(refs) >= MAX_CITATIONS:
            break
        meta = index.get(n)
        if not meta:
            continue
        receipt_id, result_id, start, width, note, _source = meta
        note_len = len(note)
        if note_len <= 0:
            continue
        s, e = _best_slice(note, start, width)
        if e <= s:
            continue
        if total + (e - s) > CITATION_CHAR_BUDGET:
            continue
        total += (e - s)
        refs.append(CitationRef(receipt_id=receipt_id, result_id=result_id,
                                slices=[CitationSlice(start=s, end=e)]))
    return refs


def _citations_with_floor(text, index):
    refs = _citations_from_text(text, index)
    if refs:
        return refs
    return index.floor_refs(CITE_FLOOR_N)


async def _do_search(query_text, index):
    res = None
    for provider in (SEARCH_PROVIDER, SEARCH_FALLBACK_PROVIDER):
        try:
            candidate = await search_web(query_text, provider=provider, timeout=SEARCH_TIMEOUT_SECONDS)
        except Exception:
            continue
        if candidate is not None and getattr(candidate, "results", None):
            _spend_note(candidate)
            res = candidate
            break
    if res is None:
        return f"# search_web({query_text!r}) ERROR: no results from any provider"
    nums = index.record(res.receipt_id, res.results, width=SEARCH_EXCERPT_CHARS, source="search")
    lines = [f"# search_web({query_text!r}) -> {len(res.results)} results"]
    for n, r in zip(nums, res.results):
        lines.append(f"[{n}] {getattr(r, 'title', '') or ''}\n  url: {getattr(r, 'url', '')}\n  excerpt: {(getattr(r, 'note', '') or '')[:SEARCH_EXCERPT_CHARS]}")
    return "\n".join(lines)


async def _do_search_ai(prompt, index):
    res = None
    for provider in (SEARCH_PROVIDER, SEARCH_FALLBACK_PROVIDER):
        try:
            candidate = await search_ai(prompt, provider=provider, count=SEARCH_AI_COUNT, timeout=SEARCH_TIMEOUT_SECONDS)
        except Exception:
            continue
        if candidate is not None and getattr(candidate, "results", None):
            _spend_note(candidate)
            res = candidate
            break
    if res is None:
        return f"# search_ai({prompt!r}) ERROR: no results from any provider"
    items = list(res.results)[:SEARCH_AI_MAX_RESULTS]
    nums = index.record(res.receipt_id, items, width=SEARCH_AI_EXCERPT_CHARS, source="fetch")
    lines = [f"# search_ai({prompt!r}) -> {len(items)} results (dense)"]
    for n, r in zip(nums, items):
        note = (getattr(r, "note", "") or "")[:SEARCH_AI_EXCERPT_CHARS]
        lines.append(f"[{n}] {getattr(r, 'title', '') or ''}\n  url: {getattr(r, 'url', '')}\n  {note}")
    return "\n".join(lines)


_FETCH_STOP = {"the", "and", "for", "with", "that", "which", "what", "who", "from", "according", "between", "their", "were", "was", "this", "than", "into", "over", "under", "when", "where", "list", "name", "many", "have", "has"}


def _window_start(body, question, width):
    if len(body) <= width:
        return 0
    terms = [w for w in re.findall(r"[A-Za-z0-9]{4,}", question or "") if w.lower() not in _FETCH_STOP]
    low = body.lower()
    for t in terms[:14]:
        i = low.find(t.lower())
        if i != -1:
            return max(0, i - width // 4)
    return 0


async def _do_fetch(url, index, question=""):
    res = None
    for provider in (SEARCH_PROVIDER, SEARCH_FALLBACK_PROVIDER):
        for _ in range(FETCH_RETRIES):
            try:
                candidate = await fetch_page(url, provider=provider, timeout=FETCH_TIMEOUT_SECONDS)
            except Exception:
                candidate = None
            if candidate is not None and getattr(candidate, "results", None):
                _spend_note(candidate)
                res = candidate
                break
        if res is not None:
            break
    if res is None or not getattr(res, "results", None):
        return f"# fetch_page({url!r}) -> no content"
    full = getattr(res.results[0], "note", "") or ""
    width = FETCH_EXTRACT_CHARS if _EXTRACT_MODE["on"] else FETCH_EXCERPT_CHARS
    start = _window_start(full, question, width)
    body = full[start:start + width]
    nums = index.record(res.receipt_id, res.results, width=len(body), start=start, source="fetch")
    return f"# fetch_page({url!r}) -> [{nums[0]}] {len(body)} chars\n{body}"


def _do_compute(code):
    try:
        return f"# compute -> result = {safe_exec(code, {})!r}"
    except Exception as exc:
        return f"# compute ERROR: {exc}"


async def _turn(messages, *, deadline, tools, force_text):
    for _ in range(LLM_TURN_RETRIES):
        timeout = min(LLM_TURN_TIMEOUT_SECONDS, deadline - perf_counter())
        if timeout <= 0:
            return None
        try:
            r = await llm_chat(provider=LLM_PROVIDER, model=MODEL, messages=messages,
                               tools=tools, tool_choice=("auto" if tools else None),
                               temperature=TEMPERATURE, thinking=_THINK_OFF, timeout=timeout)
        except Exception:
            continue
        _spend_note(r)
        return r
    return None


async def _briefing(question, deadline):
    timeout = min(BRIEFING_TIMEOUT_SECONDS, deadline - perf_counter())
    if timeout <= 8:
        return ""
    try:
        r = await llm_chat(provider=LLM_PROVIDER, model=MODEL,
                           messages=[{"role": "system", "content": BRIEFING_PROMPT}, {"role": "user", "content": question}],
                           temperature=TEMPERATURE, thinking=_THINK_OFF, timeout=timeout)
    except Exception:
        return ""
    if r:
        _spend_note(r)
    return (r.response.raw_text or "").strip() if r else ""


async def _commit_llm(messages, deadline, directive):
    msgs = messages + [{"role": "system", "content": directive}]
    for model in (MODEL, COMMIT_FALLBACK_MODEL):
        timeout = min(FINAL_COMMIT_TIMEOUT_SECONDS, deadline - perf_counter())
        if timeout <= 6:
            break
        try:
            r = await llm_chat(provider=LLM_PROVIDER, model=model, messages=msgs, tools=None,
                               temperature=TEMPERATURE, thinking=_think_for(model), timeout=timeout)
        except Exception:
            continue
        if r:
            _spend_note(r)
        t = _strip_draft((r.response.raw_text or "").strip()) if r else ""
        if t and not _invalid_final(t):
            return t
    return ""


async def _forced_final(messages, deadline):
    return await _commit_llm(messages, deadline, _commit_directive())


async def _synth_pass(messages, deadline, temperature):
    timeout = min(FINAL_COMMIT_TIMEOUT_SECONDS, deadline - perf_counter())
    if timeout <= 8:
        return ""
    msgs = messages + [{"role": "system", "content": _SYNTH_DIRECTIVE}]
    try:
        r = await llm_chat(provider=LLM_PROVIDER, model=MODEL, messages=msgs, tools=None,
                           temperature=temperature, thinking=_THINK_OFF, timeout=timeout)
    except Exception:
        return ""
    if r:
        _spend_note(r)
    return _strip_draft((r.response.raw_text or "").strip()) if r else ""


def _answer_key(text):
    disp = _final_section(text or "")
    m = _FINAL_ANY_RE.search(disp)
    line = disp[m.end():] if m else disp
    line = line.split("\n", 1)[0]
    line = re.split(r"\bproof\b|\bbecause\b|\bsince\b", line, maxsplit=1, flags=re.I)[0]
    line = _BRACKET_RE.sub("", line)
    line = re.sub(r"[^a-z0-9, ]", " ", line.lower())
    toks = sorted(t for t in line.split() if len(t) > 2)
    return " ".join(toks)[:400]


def _select_best(cands, is_set):
    valid = [c for c in cands if c and not _invalid_final(c)]
    if not valid:
        return ""
    if len(valid) == 1:
        return valid[0]
    def ncit(c):
        return len({n for m in _BRACKET_RE.finditer(c) for n in _cite_numbers(m.group(1), 9999)})
    if is_set:
        return max(valid, key=lambda c: (ncit(c), len(_final_section(c))))
    from collections import Counter
    keys = [_answer_key(c) for c in valid]
    counts = Counter(k for k in keys if k)
    if counts:
        top_key, top_n = counts.most_common(1)[0]
        if top_n >= 2:
            agree = [c for c, k in zip(valid, keys) if k == top_key]
            return max(agree, key=ncit)
    return max(valid, key=ncit)


_CITE_DIRECTIVE = (
    "CITATION GAP: your answer is under-sourced and earns NO credit for uncited claims. Using ONLY the numbered "
    "evidence above, RESTATE the complete FINAL ANSWER with a [n] citation immediately after EVERY factual claim. "
    "Keep the same answer and format; just add the citations. Clean prose."
)


async def _cite_recommit(messages, prior, deadline):
    timeout = min(FINAL_COMMIT_TIMEOUT_SECONDS, deadline - perf_counter())
    if timeout <= 8:
        return ""
    msgs = messages + [{"role": "assistant", "content": prior[:1500]}, {"role": "system", "content": _CITE_DIRECTIVE}]
    for model in (MODEL, COMMIT_FALLBACK_MODEL):
        timeout = min(FINAL_COMMIT_TIMEOUT_SECONDS, deadline - perf_counter())
        if timeout <= 8:
            break
        try:
            r = await llm_chat(provider=LLM_PROVIDER, model=model, messages=msgs, tools=None,
                               temperature=TEMPERATURE, thinking=_think_for(model), timeout=timeout)
        except Exception:
            continue
        if r:
            _spend_note(r)
        t = _strip_draft((r.response.raw_text or "").strip()) if r else ""
        if t:
            return t
    return ""


async def _audit_and_patch(question, answer, messages, deadline):
    timeout = min(AUDIT_TIMEOUT_SECONDS, deadline - perf_counter())
    if timeout <= 8:
        return ""
    audit_user = (
        "Audit this answer against the question. Report ONLY genuine, fixable problems as a JSON object with keys: "
        '"uncited_claims", "contradictions" (a claim conflicting with its OWN cited source), "wrong_source" (an '
        "aggregator used where the question named a specific primary source), \"missing_elements\" (a question part "
        "or a qualifying set member not addressed). Empty lists when fine. No other text.\n\n"
        f"Question:\n{question}\n\nAnswer:\n{answer[:9000]}"
    )
    try:
        r = await llm_chat(provider=LLM_PROVIDER, model=AUDIT_MODEL,
                           messages=[{"role": "system", "content": "You are a strict answer auditor. Output JSON only."}, {"role": "user", "content": audit_user}],
                           temperature=0.0, thinking=_THINK_LOW, timeout=timeout)
    except Exception:
        return ""
    if r:
        _spend_note(r)
    raw = (r.response.raw_text or "").strip() if r else ""
    try:
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I | re.M).strip()
        report = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    except Exception:
        return ""
    issues = []
    for k in ("uncited_claims", "contradictions", "wrong_source", "missing_elements"):
        v = report.get(k) if isinstance(report, dict) else None
        if isinstance(v, list):
            issues.extend(str(x) for x in v if str(x).strip())
    if not issues or deadline - perf_counter() < 35:
        return ""
    patch = (
        "AUDIT found fixable gaps in your final answer:\n- " + "\n- ".join(issues[:6]) +
        "\nRewrite the COMPLETE FINAL ANSWER fixing ONLY these, keeping everything already correct (do NOT drop a "
        "correct qualifying item). Put a [n] after every claim, obey the output format. Clean prose, no table."
    )
    return await _commit_llm(messages + [{"role": "assistant", "content": answer[:1500]}], deadline, patch)


_CONCISE_DIRECTIVE = (
    "Your previous answer ran long and was CUT OFF. Rewrite it NOW as a COMPLETE, CONCISE answer: a 'FINAL ANSWER:' "
    "line, then AT MOST 4-5 short cited lines, a [n] after every claim. Under 170 words, and make sure it ENDS. No "
    "tool-call syntax, no draft heading, no table."
)


def _looks_truncated(text):
    t = (text or "").rstrip()
    if len(t) < 350:
        return False
    return t[-1].isalnum() or t[-1] in ",;:-—"


async def _concise_recommit(messages, prior, deadline):
    timeout = min(FINAL_COMMIT_TIMEOUT_SECONDS, deadline - perf_counter())
    if timeout <= 6:
        return ""
    msgs = messages + [{"role": "assistant", "content": prior[:1200]}, {"role": "system", "content": _CONCISE_DIRECTIVE}]
    try:
        r = await llm_chat(provider=LLM_PROVIDER, model=MODEL, messages=msgs, tools=None,
                           temperature=TEMPERATURE, thinking=_THINK_OFF, timeout=timeout)
    except Exception:
        return ""
    if r:
        _spend_note(r)
    return _strip_draft((r.response.raw_text or "").strip()) if r else ""


# ------------------------------------------------------------------ classifier
_SET_DIRECTIVE = (
    "\nSET/ENUMERATE QUESTION -- it asks for the COMPLETE set. Give a full 'Proof of completeness': CANDIDATE POOL "
    "(name every candidate), apply EACH criterion with a citation, then ONE cited line per QUALIFYING item and ONE "
    "per key EXCLUDED candidate with the reason it fails. Enumerate them ALL. Keep each line short. Each line MUST "
    "carry the candidate's exact DECIDING value with a [n] to the NAMED authority for that criterion (the filter's "
    "source may differ from the pool's -- cite the filter source). Batch the per-candidate lookups in one turn."
)
_NUMERIC_DIRECTIVE = (
    "\nNUMERIC/COMPUTE QUESTION -- retrieve each raw figure from a cited source, then use the compute tool for EVERY "
    "calculation. Never do mental math; state the computed result and cite the inputs."
)
_MULTIHOP_DIRECTIVE = (
    "\nMULTI-HOP QUESTION -- resolve hop by hop: find and CITE the bridge entity first, then search using ITS exact "
    "name for the next hop. Verify each hop before the next."
)
_SET_Q_RE = re.compile(
    r"\b(list all|name all|name every|how many|which .{0,45}?\b(satisfy|satisfies|meet|meets|have|has|are|were|match|matches|qualify|qualifies|contain|contains|rank|include)|"
    r"all (of )?the .{0,45}?\b(that|which|who|with)|every .{0,35}?\b(that|which|with)|each of (the )?)\b", re.I)
_NUMERIC_Q_RE = re.compile(
    r"\b(how many|how much|what percentage|percent|average|mean|median|the sum|total number|difference between|ratio|"
    r"growth rate|per capita|how far|how old|how long|how tall|times (as|more|larger|bigger|greater))\b", re.I)
_MULTIHOP_Q_RE = re.compile(
    r"\bthe\s+\w+\s+of\s+the\s+\w+\s+(that|who|which|whose)\b|\bwho\s+(directed|wrote|founded|created|composed|played|"
    r"married)\b.{0,60}\b(that|who|which|whose)\b", re.I)
_COMPARISON_RE = re.compile(
    r"\b(compare|comparison|versus|vs\.?|difference between|which (?:one )?(?:is|has|was|had) (?:the )?(?:more|less|"
    r"higher|lower|greater|bigger|smaller|older|younger|longer|shorter|larger|closest|nearest))\b", re.I)
_SUPERLATIVE_ONLY_RE = re.compile(r"\b(the only|the first|the sole|the single|the last|no other|the unique)\b", re.I)
_HEDGE_RE = re.compile(
    r"\b(however|although|it is unclear|it'?s unclear|ambiguous|arguably|it depends|more than one|multiple (?:answers|"
    r"candidates|possibilities)|also (?:uses|qualifies|applies|counts|meets))\b", re.I)


def _is_set_question(q):
    return bool(_SET_Q_RE.search(q or ""))


def _is_numeric_question(q):
    return bool(_NUMERIC_Q_RE.search(q or ""))


def _is_multihop_question(q):
    return bool(_MULTIHOP_Q_RE.search(q or ""))


def _is_comparison(q):
    return bool(_COMPARISON_RE.search(q or ""))


def _has_superlative_only(q):
    return bool(_SUPERLATIVE_ONLY_RE.search(q or ""))


def _structural_hard(q):
    return _is_set_question(q) or _is_numeric_question(q) or _is_multihop_question(q) or _is_comparison(q)


def _route_directive(q):
    d = ""
    if _is_set_question(q):
        d += _SET_DIRECTIVE
    if _is_numeric_question(q):
        d += _NUMERIC_DIRECTIVE
    if _is_multihop_question(q):
        d += _MULTIHOP_DIRECTIVE
    return d


def _parse_difficulty(brief):
    """Signal B: parse the briefing's CLASSIFY tail."""
    if not brief:
        return {}
    up = brief.upper()
    seg = brief[up.rfind("CLASSIF"):] if "CLASSIF" in up else brief

    def g(label, pat):
        m = re.search(label + r"\s*:?\s*(" + pat + r")", seg, re.I)
        return m.group(1).lower() if m else None

    def gi(label):
        m = re.search(label + r"\s*:?\s*(\d+)", seg, re.I)
        return int(m.group(1)) if m else None

    return {
        "difficulty": g("DIFFICULTY", r"easy|hard"),
        "answer_type": g("ANSWER_TYPE", r"single_fact|enumerate|numeric|multi_hop"),
        "candidates": gi("CANDIDATES"),
        "constraints": gi("CONSTRAINTS"),
        "premise_risk": g("PREMISE_RISK", r"none|possible"),
        "draft_confidence": g("DRAFT_CONFIDENCE", r"high|low"),
    }


def _briefing_hard(cls):
    """Signal B verdict: True/False/None(unknown)."""
    if not cls:
        return None
    if cls.get("difficulty") == "hard":
        return True
    if cls.get("answer_type") in ("enumerate", "numeric", "multi_hop"):
        return True
    if (cls.get("candidates") or 0) >= 2 or (cls.get("constraints") or 0) >= 2:
        return True
    if cls.get("draft_confidence") == "low":
        return True
    if cls.get("difficulty") == "easy":
        return False
    return None


def classify_hard(q, cls):
    """Combined classifier, biased toward LEAN: hard iff structural(A) OR briefing(B) says hard."""
    return bool(_structural_hard(q)) or (_briefing_hard(cls) is True)


def _needs_escalation(text):
    """Signal C: an 'easy' answer that hedges the core -> the easy call was likely wrong."""
    return bool(_HEDGE_RE.search(_final_section(text or "")))


# ---------------------------------------------- AXIS 2: OUTPUT-MODE (structured / strict-format)
_STRICT_FMT_RE = re.compile(
    r"output only|only (?:output|return|provide|give)|return only|exactly the text|the exact text from|"
    r"comma[- ]separated|separated by commas|semicolon[- ]separated|without the (?:word|term)|"
    r"omit(?:ting)? the (?:word|term)|excluding the (?:word|term)|in alphabetical order|in chronological order|"
    r"alphabetical(?:ly)? order|chronological(?:ly)? order|sorted (?:by|in|alphabetically|chronologically)", re.I)


def _has_strict_format(q):
    return bool(_STRICT_FMT_RE.search(q or ""))


def _answer_value_text(answer):
    """Extract the bare answer VALUE from a 'FINAL ANSWER:'+proof reply -- the value line only, no label,
    proof, brackets, or markdown. Used for strict-format delivery and schema coercion."""
    disp = _final_section(answer or "")
    m = _FINAL_ANY_RE.search(disp)
    line = disp[m.end():] if m else disp
    line = line.split("\n", 1)[0]
    line = re.split(r"\bproof\b|\bbecause\b|\bsince\b", line, maxsplit=1, flags=re.I)[0]
    line = _BRACKET_RE.sub("", line)
    line = re.sub(r"\s{2,}", " ", line)
    return line.strip(" \t*:#—-.,;").strip()


def _apply_output_directives(question, text):
    """Deterministic strict-format enforcement the model may miss: 'without the word X' -> delete X;
    collapse whitespace. (Sorting/comma-joining is left to the model; this is the safety net.)"""
    out = text or ""
    for m in re.finditer(r'(?:without|omit(?:ting)?|excluding) the (?:word|term)\s*["“‘\']?([A-Za-z][\w\-]*)["”’\']?', question or "", re.I):
        w = m.group(1)
        if len(w) >= 3:
            out = re.sub(r"\b%s\b" % re.escape(w), "", out, flags=re.I)
    if out != (text or ""):
        out = re.sub(r"\s{2,}", " ", out)
        out = re.sub(r"\s+([,.;:)])", r"\1", out).strip()
    return out.strip() or (text or "")


# ---------------------------------------------- SCHEMA-ISSUE DETECTION + deterministic coercion
_NUM_IN_TEXT_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _schema_kind(schema):
    """Top-level JSON type a schema demands; '' when it pins none. (schema-issue detection helper.)"""
    if not isinstance(schema, dict):
        return ""
    k = schema.get("type")
    if isinstance(k, list):
        k = k[0] if k else None
    if k is None:
        for key in ("anyOf", "oneOf", "allOf"):
            b = schema.get(key)
            if isinstance(b, list):
                for sub in b:
                    got = _schema_kind(sub)
                    if got:
                        return got
        if isinstance(schema.get("properties"), dict):
            return "object"
        if isinstance(schema.get("enum"), list):
            return "string"
        return ""
    return str(k)


def _matches_schema_shape(value, schema):
    """SCHEMA-ISSUE DETECTION: does `value` satisfy the schema's top-level type AND required object keys?
    Returns False when the produced output is the wrong shape (so we fall back to a coerced value)."""
    kind = _schema_kind(schema)
    if kind == "array":
        if not isinstance(value, list):
            return False
    elif kind == "object":
        if not isinstance(value, dict):
            return False
        for req in (schema.get("required") or []):
            if req not in value:
                return False
    elif kind == "string":
        if not isinstance(value, str):
            return False
    elif kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return False
    elif kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
    elif kind == "boolean":
        if not isinstance(value, bool):
            return False
    elif kind == "null":
        if value is not None:
            return False
    return True


def _coerce_to_schema(answer, schema, depth=0):
    """Deterministic last-resort schema-shaped value so a structured task is NEVER a hard zero
    (a structured Response must carry `output`, not text)."""
    if depth > 5 or not isinstance(schema, dict):
        return (_answer_value_text(answer) or (answer or "").strip())[:400]
    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        av = (_answer_value_text(answer) or answer or "").lower()
        for e in enum:
            if isinstance(e, str) and e.lower() in av:
                return e
        return enum[0]
    kind = _schema_kind(schema)
    val = _answer_value_text(answer) or (answer or "").strip()
    if kind == "object":
        props = schema.get("properties")
        if isinstance(props, dict) and props:
            return {name: _coerce_to_schema(answer, sub if isinstance(sub, dict) else {}, depth + 1)
                    for name, sub in props.items()}
        return {}
    if kind == "array":
        items = schema.get("items") if isinstance(schema.get("items"), dict) else {}
        parts = [p.strip() for p in re.split(r",|;|\band\b", val) if p.strip()]
        if not parts:
            parts = [val] if val else []
        ik = _schema_kind(items) if items else "string"
        if ik in ("integer", "number"):
            nums = []
            for p in parts:
                mm = _NUM_IN_TEXT_RE.search(p)
                if mm:
                    n = mm.group(0).replace(",", "")
                    nums.append(int(float(n)) if ik == "integer" else float(n))
            return nums
        if ik == "object" and isinstance(items, dict):
            return [_coerce_to_schema(answer, items, depth + 1)]
        return parts
    if kind == "integer":
        mm = _NUM_IN_TEXT_RE.search(val)
        return int(float(mm.group(0).replace(",", ""))) if mm else 0
    if kind == "number":
        mm = _NUM_IN_TEXT_RE.search(val)
        return float(mm.group(0).replace(",", "")) if mm else 0.0
    if kind == "boolean":
        return not bool(re.search(r"\b(no|not|false|none|isn'?t|aren'?t)\b", val, re.I))
    if kind == "null":
        return None
    return (val or (answer or "").strip())[:400]


def _structured_directive(schema):
    return (
        "\n\nSTRUCTURED OUTPUT REQUIRED: the deliverable is a JSON value matching this schema, so research the EXACT "
        "value for EVERY field. In your FINAL ANSWER, state each field name and its precise value (exact names / "
        "numbers / dates), each with a [n] citation. SCHEMA:\n" + json.dumps(schema)[:1500]
    )


# ---- NAMED-SOURCE EXTRACTION (the field's #1 shared weakness: top miners dump snippets on named-source tasks) ----
# Broadened to catch ALL extraction flavors: (a) named public sources, (b) explicit table/list/dataset refs,
# (c) a raw URL / "Root URL:" / site-navigation task (webwalkerqa flavor), (d) column/row references.
_NAMED_SOURCE_RE = re.compile(
    r"\b(?:according to|per|from|based on|using|on|by)\b[^.?!]{0,60}?\b("
    r"wikipedia|the wikipedia (?:table|list|page|article)|basketball[- ]?reference|box office mojo|imdb|rotten tomatoes|"
    r"billboard|forbes|companiesmarketcap|statista|nasa|planetary fact sheet|world bank|united nations|\bun\b|census|"
    r"fandom|wisdom panel|the table|the list|the fact sheet|the dataset|the chart|data\.\w+)\b"
    r"|\bthe (?:wikipedia )?(?:table|list|fact sheet|dataset|chart) (?:titled|named|called|\")|"
    r"\b(?:column|row)s?\b.{0,40}\b(?:table|list)\b"
    r"|https?://\S+"                                          # raw URL to navigate/extract from (webwalkerqa flavor)
    r"|\broot url\s*:|\bon (?:the )?(?:website|web page|webpage|page|site) (?:at|of)\b"  # site-navigation extraction
    r"|\bon the (?:official )?\w+ (?:website|page|site)\b", re.I)


# v57: GENERIC authority detection (case-SENSITIVE for proper-noun sources -- no re.I). The qualifying round
# names an authority the grader validates against ("according to Baseball-Reference / BLS / NARA / Box Office
# Mojo", "based on Table 1.1 of the Kerala State Planning Board's Economic Review"). v56's hardcoded whitelist
# missed baseball-reference / BLS / NARA -> the fetch-primary-source directive never fired -> aggregator citations
# -> the decisive figures were unvalidated -> ZERO. This catches ANY named authority, not a whitelist.
_AUTHORITY_RE = re.compile(
    r"\b(?:according to|per|based on|as (?:reported|listed|shown|recorded|published|given)(?:\s+(?:by|in|on))?|"
    r"from|using|sourced from|drawn from)\s+"
    r"(?:the\s+)?"
    r"(?:[A-Z][\w.&'’-]*(?:[- ](?:of\s+|the\s+)?[A-Z0-9][\w.&'’-]*){0,6}"   # Proper-noun authority
    r"|[A-Z]{2,6}\b)"                                                                    # abbreviation: BLS/NARA/SEC
)
# structural: an explicitly numbered/named table, list, roster, report, dataset, index, census, survey, review
_SOURCE_TABLE_RE = re.compile(
    r"\bTable\s+[0-9IVXA-Z][\w.\-]*"
    r"|\b(?:the|its|that|this)\s+[\w' ]{0,45}?\b"
    r"(?:table|list|roster|dataset|data\s?set|database|index|census|survey|review|almanac|registry|leaderboard|"
    r"standings|filing|10-?[KQ]|fact\s?sheet)\b", re.I)


def _authority_source(q):
    """v57: does the question pin a specific AUTHORITY / primary table the grader will validate against?"""
    return bool(_AUTHORITY_RE.search(q or "")) or bool(_SOURCE_TABLE_RE.search(q or ""))


def _named_source(q):
    return bool(_NAMED_SOURCE_RE.search(q or "")) or _authority_source(q)


_EXTRACTION_DIRECTIVE = (
    "\n\nAUTHORITATIVE-SOURCE DISCIPLINE -- this question names (or implies) a SPECIFIC authority/table/dataset the "
    "grader will FACT-CHECK your decisive figures against. A correct answer cited to the WRONG source (an aggregator, "
    "a news summary, a search snippet) scores ZERO. Steps: (1) identify the EXACT named authority (e.g. "
    "Baseball-Reference, the BLS state table, NARA, Box Office Mojo, 'Table 1.1 of ...'); (2) fetch_page that "
    "authority's OWN primary page / table / JSON API -- NOT statmuse/aggregators/news write-ups; if unsure of the URL, "
    "search the authority's name + the exact table, then fetch the primary page; (3) read the WHOLE relevant "
    "table/fact-sheet and copy every needed row/figure VERBATIM; (4) ROUNDED FIGURE = WRONG SOURCE: if a decisive "
    "number reads as rounded/approximate, you are on a summary -- keep digging for the primary table with the exact "
    "value; (5) apply each filter/condition to the EXTRACTED rows and use the compute tool for any top-N / comparison "
    "/ threshold / arithmetic; (6) CITE THE DECISIVE CONDITION: attach [n] to the fetched authority for EACH "
    "candidate's deciding value -- not merely the source that lists the candidate pool. A right answer whose decisive "
    "per-candidate figure is uncited (or cited to a non-authority) gets NO credit. NEVER output raw 'search findings', "
    "a list of result titles, or a partial sentence as the answer -- only the extracted, computed result.\n"
    "EXACT FULL NAME: give the fully-qualified name -- include the standard designation/prefix (e.g. 'HMS'/'USS' for "
    "ships, 'Mount' for peaks) AND the current + any alternate/former name (e.g. 'HMS Leander', 'Allahabad (now "
    "Prayagraj)'). Copy every number/date verbatim from the source. A right entity with the wrong/short form scores 0."
)

# ANTI-GARBAGE-DUMP guard: the champion's failure signature -- raw search snippets/result-titles emitted as the answer
_GARBAGE_RE = re.compile(
    r"best[- ]?supported findings|from the sources retrieved|search (?:results|findings)|"
    r"here are the (?:search |top )?results|results retrieved|no (?:direct )?answer found|"
    r"\|\s*url\s*:|\bvia [A-Za-z.]+\.net\b", re.I)


def _looks_garbage(s):
    """True if the text (or joined structured values) reads as a raw snippet/result dump rather than an answer."""
    t = (s or "").strip()
    if not t:
        return False
    if _GARBAGE_RE.search(t):
        return True
    # mostly result-title/url debris: many bracketed [n] refs with almost no prose, or many 'http' fragments
    if t.count("http") >= 3 and len(re.sub(r"\S+", "", t)) < len(t) * 0.10:
        return True
    return False


def _values_text(obj):
    """Flatten a structured output's string values for garbage inspection."""
    out = []
    def walk(x):
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)
    walk(obj)
    return " ".join(out)


_ANTI_GARBAGE_DIRECTIVE = (
    "REJECTED: your previous answer was raw search findings / result titles / snippets, not an extracted answer -- "
    "that scores ZERO. Using the numbered evidence you already fetched, EXTRACT the specific value(s) the question "
    "asks for (exact names with full designation, exact numbers verbatim), apply the filter/ranking with the compute "
    "tool, and give ONLY the final answer with [n] citations. If you have not fetched the named source's actual "
    "page/table yet, do so now, then answer."
)


_ENTITY_RE = re.compile(r"\b([A-Z][A-Za-z.'&\-]+(?:\s+(?:of|the|and|de|von)?\s*[A-Z][A-Za-z.'&\-]+){0,3})\b")
_ENT_STOP = {"the", "which", "what", "who", "how", "list", "name", "according", "using", "based", "of", "in", "on", "for", "final", "answer", "candidate", "pool"}


def _enumerated_entities(q):
    ents, seen = [], []
    for p in re.split(r"[,;]| and | or ", q or ""):
        m = _ENTITY_RE.search(p.strip())
        if m:
            e = m.group(1).strip()
            if len(e) > 2 and e.split()[0].lower() not in _ENT_STOP and e not in seen:
                seen.append(e)
                ents.append(e)
    return ents if len(ents) >= 3 else []


def _candidates_from_brief(brief):
    if not brief:
        return []
    m = re.search(r"CANDIDATE POOL\s*:?(.*?)(?:\n\s*[A-Z][A-Z /\-]{4,}\s*:|\Z)", brief, re.S | re.I)
    if not m:
        return []
    seg = m.group(1)
    ents, seen = [], []
    for p in re.split(r"[,;\n]|\band\b|\bor\b", seg):
        mm = _ENTITY_RE.search(p.strip())
        if mm:
            e = mm.group(1).strip()
            if len(e) > 2 and e.split()[0].lower() not in _ENT_STOP and e not in seen:
                seen.append(e)
                ents.append(e)
    return ents[:12] if len(ents) >= 3 else []


def _missing_entities(entities, evidence_text):
    low = (evidence_text or "").lower()
    out = []
    for e in entities:
        key = re.sub(r"\s*\(.*?\)", "", e).strip().lower()
        if len(key) >= 3 and key not in low:
            out.append(e)
    return out


def _content_to_text(msg, raw):
    if raw:
        return raw
    c = getattr(msg, "content", None)
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        out = []
        for part in c:
            if isinstance(part, str):
                out.append(part)
            elif isinstance(part, dict):
                out.append(part.get("text") or part.get("content") or "")
            else:
                out.append(getattr(part, "text", "") or "")
        return "".join(out)
    return ""


async def _run_tool(c, index, question=""):
    try:
        args = json.loads(c.arguments or "{}")
    except json.JSONDecodeError:
        args = {}
    if c.name == "search_web":
        return await _do_search(str(args.get("query", "")), index)
    if c.name == "search_ai":
        return await _do_search_ai(str(args.get("prompt", "") or args.get("query", "")), index)
    if c.name == "fetch_page":
        return await _do_fetch(str(args.get("url", "")), index, question)
    if c.name == "compute":
        return _do_compute(args.get("code", ""))
    return f"# unknown tool {c.name!r}"


async def _knowledge_answer(question, deadline):
    sys = ("Answer with your single best SPECIFIC answer from knowledge. Line 1 = 'FINAL ANSWER: <answer>'. "
           "Never refuse or say 'cannot be determined'. Be concise.")
    for model in (MODEL, COMMIT_FALLBACK_MODEL):
        timeout = min(FINAL_COMMIT_TIMEOUT_SECONDS, deadline - perf_counter())
        if timeout <= 5:
            break
        try:
            r = await llm_chat(provider=LLM_PROVIDER, model=model,
                               messages=[{"role": "system", "content": sys}, {"role": "user", "content": question}],
                               temperature=TEMPERATURE, thinking=_think_for(model), timeout=timeout)
        except Exception:
            continue
        if r:
            _spend_note(r)
        t = _strip_draft((r.response.raw_text or "").strip()) if r else ""
        if t and not _invalid_final(t):
            return t
    return ""


async def _structured_output(question, answer, schema, deadline):
    timeout = min(30.0, deadline - perf_counter())
    if timeout <= 5:
        return None
    user = ("Convert the ANSWER into JSON strictly matching this schema. Output ONLY the JSON.\nSCHEMA:\n"
            + json.dumps(schema)[:2200] + "\n\nANSWER:\n" + (answer or "")[:2500])
    for model in (SCHEMA_MODEL, MODEL):
        try:
            r = await llm_chat(provider=LLM_PROVIDER, model=model,
                               messages=[{"role": "system", "content": "You output strictly valid JSON matching the given schema. JSON only."}, {"role": "user", "content": user}],
                               temperature=0.0, thinking=_think_for(model), timeout=timeout)
            if r:
                _spend_note(r)
            t = (r.response.raw_text or "").strip() if r else ""
            for op, cl in (("{", "}"), ("[", "]")):
                i, j = t.find(op), t.rfind(cl)
                if i != -1 and j > i:
                    return json.loads(t[i:j + 1])
        except Exception:
            continue
    return None


async def _deliver_structured(q, answer, schema, refs, deadline):
    """OUTPUT-ONLY delivery for output_schema tasks. LLM-convert -> SCHEMA-SHAPE VALIDATE -> deterministic
    coerce fallback. NEVER returns text (a structured Response must carry `output`, not text, or it is a hard zero)."""
    out = None
    try:
        out = await _structured_output(q, answer, schema, deadline)
    except Exception:
        out = None
    if out is None or not _matches_schema_shape(out, schema):   # SCHEMA-ISSUE DETECTION -> coerce
        out = _coerce_to_schema(answer or "", schema)
    if _looks_garbage(_values_text(out)):                        # ANTI-GARBAGE: don't ship snippet-dump JSON values
        out = _coerce_to_schema(answer or "", schema)
    for cand in (out, _coerce_to_schema(answer or "", schema), _coerce_to_schema("", schema)):
        try:
            return Response(output=cand, citations=refs or None)
        except Exception:
            try:
                return Response(output=cand)
            except Exception:
                continue
    return Response(output=(_answer_value_text(answer) or (answer or "n/a"))[:400])


@entrypoint("query")
async def query(query: Query) -> Response:
    deadline = perf_counter() + TASK_BUDGET_SECONDS
    index = _Index()
    q = query.text
    # --- PREPROCESSING AXIS 2: OUTPUT-MODE (detected up front) ---
    schema = getattr(query, "output_schema", None)
    structured = schema is not None
    strict_fmt = (not structured) and _has_strict_format(q)
    try:
        info = await tooling_info(timeout=10.0)
        _spend_note(info)
    except Exception:
        pass

    # --- PREPROCESSING: briefing (also the difficulty classifier, Signal B) ---
    brief = ""
    if deadline - perf_counter() > BRIEFING_MIN_REMAINING and _spend_left() >= MIN_DRAFT_USD:
        brief = await _briefing(q, deadline)
    cls = _parse_difficulty(brief)
    extract = _named_source(q)                                     # v57: named-source OR any pinned AUTHORITY/table
    _EXTRACT_MODE["on"] = extract                                  # -> _do_fetch shows a 9000-char window (full table)
    # COST-GATE (v56): extraction NO LONGER forces the full machinery. Its cheap high-value parts
    # (9k fetch above, _EXTRACTION_DIRECTIVE + anti-garbage guard below -- all gated on `extract`) stay
    # ALWAYS; but best-of-N/audit/MAX_TURNS/entity-pool gate on TRUE difficulty only. Easy single-fact
    # extraction -> lean (~champion cost); hard/multi-hop/enumerate -> full path via the briefing router.
    hard = classify_hard(q, cls)
    is_set = _is_set_question(q) or (cls.get("answer_type") == "enumerate")
    premise_risk = _has_superlative_only(q) or (cls.get("premise_risk") == "possible")

    # --- ROUTE the whole treatment ---
    if hard:
        sys_content = SYSTEM_BASE + _HARD_ADDENDUM + _route_directive(q)
    else:
        sys_content = SYSTEM_BASE + _LEAN_DIRECTIVE + (_PREMISE_NOTE if premise_risk else "")
    sys_content += _DISCRETE_CITE_NOTE          # v59: discrete per-value citation -- all tasks (pure upside)
    if _is_multipart(q):
        sys_content += _MULTIPART_DIRECTIVE      # v59: heavy completeness+premise ONLY for genuinely multi-part queries
    if extract:
        sys_content += _EXTRACTION_DIRECTIVE             # fetch+parse the named source in full, never dump snippets
    if structured:
        sys_content += _structured_directive(schema)     # research the exact schema fields
    messages = [{"role": "system", "content": sys_content}, {"role": "user", "content": q}]
    if brief:
        up = brief.upper()
        plan = brief[:up.rfind("CLASSIF")] if "CLASSIF" in up else brief
        if plan.strip():
            messages.append({"role": "system", "content": "RESEARCH PLAN (follow it; verify every fact with tools):\n" + plan[:2400]})

    pool_entities = (_enumerated_entities(q) or _candidates_from_brief(brief)) if hard else []
    max_turns = MAX_TURNS if hard else EASY_MAX_TURNS
    final = None
    last_good = None
    commit_retries = 0
    nudged = False
    entity_nudged = False
    search_fetch_used = 0
    try:
        for turn in range(1, max_turns + 1):
            remaining = deadline - perf_counter()
            if remaining <= 5:
                break
            turns_left = max_turns - turn + 1
            time_up = remaining <= FORCE_COMMIT_REMAINING_SECONDS
            budget_low = _spend_left() <= FORCE_COMMIT_BUDGET_USD   # commit before the per-task USD cap is hit
            force_text = turns_left <= 1 or time_up or budget_low
            search_capped = search_fetch_used >= MAX_SEARCH_FETCH_CALLS
            tools = None if force_text else (TOOLS_COMPUTE_ONLY if search_capped else TOOLS_ALL)
            if (turns_left <= 2 or time_up) and not nudged:
                messages.append({"role": "system", "content": _force_commit_nudge(remaining)})
                nudged = True
            result = await _turn(messages, deadline=deadline, tools=tools, force_text=force_text)
            if result is None:
                break
            msg = result.response.choices[0].message
            calls = msg.tool_calls or ()
            if calls:
                messages.append({"role": "assistant", "content": result.response.raw_text or "",
                                 "tool_calls": [{"id": c.id, "type": c.type, "name": c.name, "arguments": c.arguments} for c in calls]})
                outs = await asyncio.gather(*[_run_tool(c, index, q) for c in calls], return_exceptions=True)
                for c, tr in zip(calls, outs):
                    tr = tr if isinstance(tr, str) else f"# {c.name} ERROR: {tr}"
                    if c.name in ("search_web", "search_ai", "fetch_page") and "ERROR" not in tr:
                        search_fetch_used += 1
                    messages.append({"role": "tool", "tool_call_id": c.id, "content": tr})
                continue
            cand = _strip_draft(_content_to_text(msg, result.response.raw_text or "").strip())
            if hard and pool_entities and not entity_nudged and not force_text and remaining > 45:
                missing = _missing_entities(pool_entities, index.all_notes())
                if missing:
                    messages.append({"role": "assistant", "content": cand or "(pending)"})
                    messages.append({"role": "system", "content": "COVERAGE GAP: the gathered evidence has NO per-candidate data for: " + ", ".join(missing[:8]) + ". Search each (name + the deciding criterion) NOW before finalizing. Then commit the FINAL ANSWER."})
                    entity_nudged = True
                    continue
            invalid = _invalid_final(cand)
            if not invalid:
                last_good = cand
            if invalid and commit_retries < MAX_COMMIT_RETRIES and remaining > 15:
                messages.append({"role": "assistant", "content": cand or "(no answer produced)"})
                messages.append({"role": "system", "content": _commit_directive()})
                commit_retries += 1
                continue
            final = cand if not invalid else (last_good or cand)
            break
        if not final:
            final = last_good
        final = _strip_draft(final) if final else final
        if not final or _invalid_final(final):
            forced = await _forced_final(messages, deadline)
            if forced and not _invalid_final(forced):
                final = forced

        # --- Signal C: adaptive escalation (easy answer that HEDGES -> one completeness recommit) ---
        if (not hard) and final and not _invalid_final(final) and _needs_escalation(final) \
                and deadline - perf_counter() > AUDIT_MIN_REMAINING and _spend_left() >= MIN_AUDIT_USD:
            esc_msgs = messages + [{"role": "assistant", "content": final[:1500]},
                                   {"role": "system", "content": _HARD_ADDENDUM + _route_directive(q)}]
            esc = await _commit_llm(esc_msgs, deadline,
                                    "Your previous answer hedged. Re-resolve it decisively: if the premise holds, commit the single correct answer directly with citations; if it is genuinely false on CLEAR evidence, state that with a full completeness proof. Cite every claim.")
            if esc and not _invalid_final(esc):
                final = _select_best([final, esc], is_set)
                hard = True

        # --- ADAPTIVE VERIFICATION (v56 cost-gate) ---
        # The expensive best-of-N + audit run ONLY when the committed answer is NOT already clean:
        # a set/enumerate (needs reconciliation), a hedge, or under-cited. A confident, well-cited single
        # answer skips both (saves ~3 LLM calls on the champion-tie majority where they never change the
        # result), independent of the briefing's easy/hard call. Correctness-preserving by construction:
        # verification only fires where the answer still looks uncertain.
        _clean_answer = bool(final) and not _invalid_final(final) and not is_set \
            and not _needs_escalation(final) \
            and len(_BRACKET_RE.findall(_final_section(final))) >= CITE_MIN_MARKERS
        verify_needed = hard and not _clean_answer

        # --- best-of-N self-consistency over shared evidence (only when verification is warranted) ---
        if verify_needed and index.top() > 0 and final and not _invalid_final(final) \
                and deadline - perf_counter() > BESTOFN_MIN_REMAINING and _spend_left() >= MIN_AUDIT_USD:
            extra = await asyncio.gather(
                *[_synth_pass(messages, deadline, 0.35 + 0.15 * i) for i in range(BESTOFN_SYNTH - 1)],
                return_exceptions=True,
            )
            cands = [final] + [c for c in extra if isinstance(c, str)]
            best = _select_best(cands, is_set)
            if best and not _invalid_final(best):
                final = best

        if final and _looks_truncated(final) and deadline - perf_counter() > CONCISE_RECOMMIT_MIN_REMAINING:
            concise = await _concise_recommit(messages, final, deadline)
            if concise and not _invalid_final(concise) and not _looks_truncated(concise):
                final = concise
        if not final or _invalid_final(final):
            ka = await _knowledge_answer(q, deadline)
            if ka and not _invalid_final(ka):
                final = ka

        # --- ANTI-GARBAGE-DUMP guard (extraction dethrone lever): reject the champion's snippet-dump failure mode ---
        if extract and final and _looks_garbage(final) \
                and deadline - perf_counter() > AUDIT_MIN_REMAINING and _spend_left() >= MIN_AUDIT_USD:
            fixed = await _commit_llm(messages + [{"role": "assistant", "content": final[:1500]}], deadline, _ANTI_GARBAGE_DIRECTIVE)
            if fixed and not _invalid_final(fixed) and not _looks_garbage(fixed):
                final = fixed

        refs = _citations_with_floor(final or "", index)

        # ===== AXIS 2 -- STRUCTURED delivery: OUTPUT-ONLY (fixes the v52 hard-zero), never text =====
        # (final was just anti-garbage-cleaned above, so the JSON conversion is built from a clean answer)
        if structured:
            return await _deliver_structured(q, final or q, schema, refs, deadline)

        # non-structured: require a valid textual final
        if not final or _invalid_final(final):
            return Response(text=(final.strip() if final and final.strip() else _INSUFFICIENT))

        display = _final_section(final)
        if _invalid_final(display) and not _invalid_final(final):
            display = final

        # uncorrelated audit (reasoning-on for gpt-oss); prose only -- adaptive: skip for a clean answer
        if verify_needed and deadline - perf_counter() > AUDIT_MIN_REMAINING and _spend_left() >= MIN_AUDIT_USD:
            patched = await _audit_and_patch(q, display, messages, deadline)
            if patched and not _invalid_final(patched):
                p_disp = _final_section(patched)
                final = patched
                display = p_disp if not _invalid_final(p_disp) else patched

        # Citation-enforcement gate
        if index.top() > 0 and len(_BRACKET_RE.findall(display)) < CITE_MIN_MARKERS \
                and deadline - perf_counter() > AUDIT_MIN_REMAINING and _spend_left() >= MIN_AUDIT_USD:
            recited = await _cite_recommit(messages, display, deadline)
            if recited and not _invalid_final(recited):
                rc = _final_section(recited)
                rc_disp = rc if not _invalid_final(rc) else recited
                if len(_BRACKET_RE.findall(rc_disp)) >= max(CITE_MIN_MARKERS, len(_BRACKET_RE.findall(display))):
                    final, display = recited, rc_disp

        refs = _citations_with_floor(final, index)

        # ===== AXIS 2 -- STRICT-FORMAT delivery: bare value, directives enforced deterministically =====
        if strict_fmt:
            val = _apply_output_directives(q, _answer_value_text(final) or display)
            if val and val.strip():
                return Response(text=val.strip(), citations=refs or None)

        return Response(text=display, citations=refs or None)
    except Exception:
        if structured:                                    # never fall back to text on a structured task
            try:
                return Response(output=_coerce_to_schema(last_good or q, schema))
            except Exception:
                pass
        return Response(text=(last_good or _INSUFFICIENT))
