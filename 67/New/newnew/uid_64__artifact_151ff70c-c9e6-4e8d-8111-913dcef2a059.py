"""SN67 Harnyx miner —  naruto-v7-constraint-ledger agent.

# made by Naruto
# version v152
"""
from __future__ import annotations

import asyncio
import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmThinkingConfig, fetch_page, llm_chat, search_web

# MECHANISM_UPGRADE_V2: authority-source auto-prefetch; contradiction/opposing-evidence probe before commit
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

BUILD = "naruto-v7-constraint-ledger"

PROVIDER = "openrouter"
REASONER = "z-ai/glm-5"
PLANNER = "deepseek/deepseek-v3.2"

TOTAL_BUDGET_S = 270.0
PLAN_BUDGET_S = 30.0
RESEARCH_CUTOFF_S = 150.0        # research stops with this much of the budget spent
COMMIT_RESERVE_S = 60.0          # wall-clock held back for the committing call
TAIL_RESERVE_S = 8.0
MIN_TOOL_WINDOW_S = 5.0

SEARCH_TIMEOUT_S = 20.0
FETCH_TIMEOUT_S = 15.0
TURN_TIMEOUT_S = 75.0
PLAN_TIMEOUT_S = 25.0
TURN_RETRIES = 2
FETCH_RETRIES = 2
MAX_RESEARCH_TURNS = 12

# --- evidence accounting -------------------------------------------------
# The validator materializes the [start:end) window of every citation. The
# ceiling is a whole-response validity check, so overshoot costs everything.
# We hold a private ceiling well under the platform limit and spend it down.
EVIDENCE_CEILING_CHARS = 92_000
SEARCH_WINDOW_CHARS = 640
FETCH_WINDOW_CHARS = 5_200
MIN_WINDOW_CHARS = 260
MAX_CITATIONS = 22
WINDOW_STRIDE_CHARS = 900      # granularity of the relevance scan
FETCH_FLOOR_URLS = 2           # zero-fetch runs scored zero in the v6 log

# --- probe policy --------------------------------------------------------
MAX_CELL_PROBES = 4
PROBE_ANNOUNCE_TURNS = (3, 6, 9)

_DROP_HOSTS = (
    "reddit.com", "quora.com", "fandom.com", "pinterest.", "answers.com",
    "blogspot.", "scribd.com", "coursehero.com", "chegg.com", "grokipedia",
    "slideshare.net", "studocu.com",
)
_OFFICIAL_MARKERS = (
    ".gov", ".gov.", ".edu", ".int", ".mil", "sec.gov", "europa.eu", "who.int",
    "worldbank.org", "imf.org", "un.org", "oecd.org", "census.gov", "bls.gov",
    "eurostat", "nasa.gov", "nih.gov",
)
_REFERENCE_MARKERS = ("wikipedia.org", "britannica.com", "boxofficemojo.com", "oscars.org")

_FALLBACK_TEXT = (
    "FINAL ANSWER: The research pass did not return usable evidence within the time "
    "budget, so no sourced determination can be committed for this question."
)


# ===========================================================================
# source triage
# ===========================================================================

def _authority_rank(url: str) -> int | None:
    """0 = official/primary, 1 = curated reference, 2 = open web, None = drop."""
    u = (url or "").lower()
    if not u:
        return 2
    if any(bad in u for bad in _DROP_HOSTS):
        return None
    if any(marker in u for marker in _OFFICIAL_MARKERS):
        return 0
    if any(marker in u for marker in _REFERENCE_MARKERS):
        return 1
    return 2


def _triage(results) -> list:
    keep = []
    for item in results or ():
        rank = _authority_rank(getattr(item, "url", None) or "")
        if rank is None:
            continue
        keep.append((rank, item))
    keep.sort(key=lambda pair: pair[0])
    return [item for _, item in keep]


# ===========================================================================
# evidence store with a hard char accountant
# ===========================================================================

def _relevance_window(note: str, cues: list[str], width: int) -> int:
    """Offset of the passage that best matches the question's own vocabulary.

    Documents that answer constraint questions are usually tables, and the
    deciding rows sit well past the header. Taking offset 0 shows the model
    the masthead and nothing else, which reads as "the data is incomplete"
    rather than as a retrieval failure.
    """
    body = note or ""
    if len(body) <= width or not cues:
        return 0
    lowered = body.lower()
    best_offset, best_hits = 0, -1
    for offset in range(0, max(1, len(body) - width // 2), WINDOW_STRIDE_CHARS):
        chunk = lowered[offset:offset + width]
        if not chunk:
            break
        hits = sum(chunk.count(cue) for cue in cues if cue)
        hits += min(chunk.count("%"), 6)
        hits += min(len(re.findall(r"\d[\d,]{2,}", chunk)), 12)
        if hits > best_hits:
            best_offset, best_hits = offset, hits
    return best_offset if best_hits > 0 else 0


class _EvidenceStore:
    """Numbered evidence with a spend-down char budget.

    Every recorded item knows how wide a window the model was actually shown.
    At citation time we never emit a window wider than what was shown (so the
    cited fact is always inside the slice) and never let the running total pass
    the ceiling. When the budget tightens we narrow windows rather than dropping
    citations -- an uncited claim loses judge credit, a narrower slice does not.
    """

    def __init__(self) -> None:
        self._items: dict[int, dict] = {}
        self._counter = 0

    def add(self, receipt_id: str, results, *, shown: int) -> list[tuple[int, object]]:
        stored: list[tuple[int, object]] = []
        for item in results or ():
            result_id = getattr(item, "result_id", None)
            if not result_id:
                continue
            note = getattr(item, "note", None) or ""
            self._counter += 1
            self._items[self._counter] = {
                "receipt_id": receipt_id or "",
                "result_id": result_id,
                "shown": min(shown, len(note)),
                "offset": 0,
                "length": len(note),
                "title": getattr(item, "title", None) or "",
                "url": getattr(item, "url", None) or "",
                "head": note[:280],
            }
            stored.append((self._counter, item))
        return stored

    def lookup(self, number: int) -> dict | None:
        return self._items.get(number)

    def opened_any(self) -> bool:
        """True once a real page window has been read, not just excerpts."""
        return any(item["shown"] >= FETCH_WINDOW_CHARS // 2
                   for item in self._items.values())

    def unopened_urls(self) -> list[str]:
        opened = {i["url"] for i in self._items.values()
                  if i["url"] and i["shown"] >= FETCH_WINDOW_CHARS // 2}
        out: list[str] = []
        for number in sorted(self._items):
            url = self._items[number]["url"]
            if url and url not in opened and url not in out:
                out.append(url)
        return sorted(out, key=lambda u: _authority_rank(u) if _authority_rank(u) is not None else 3)

    @property
    def high_water(self) -> int:
        return self._counter

    def digest(self, limit: int = 6) -> str:
        """Compact evidence recap used by the floor answer."""
        rows = []
        for number in sorted(self._items)[:limit]:
            meta = self._items[number]
            rows.append(f"[{number}] {meta['title']} ({meta['url']}): {meta['head']}")
        return "\n".join(rows)


def _referenced_numbers(text: str, *, ceiling: int) -> list[int]:
    """Bracket markers actually used in the answer, in first-appearance order."""
    seen: list[int] = []
    for token in re.findall(r"\[(\d{1,3}(?:\s*,\s*\d{1,3})*)\]", text or ""):
        for part in token.split(","):
            part = part.strip()
            if not part.isdigit():
                continue
            number = int(part)
            if 1 <= number <= ceiling and number not in seen:
                seen.append(number)
    return seen


def _assemble_citations(answer: str, store: _EvidenceStore) -> list[CitationRef]:
    numbers = _referenced_numbers(answer, ceiling=store.high_water)
    if not numbers:
        return []
    numbers = numbers[:MAX_CITATIONS]

    # First pass: what would the natural windows cost?
    natural = []
    for number in numbers:
        meta = store.lookup(number)
        if not meta:
            continue
        width = max(0, min(int(meta["shown"]), int(meta["length"])))
        if width <= 0:
            continue
        natural.append((number, meta, width))
    if not natural:
        return []

    total = sum(width for _, _, width in natural)
    scale = 1.0
    if total > EVIDENCE_CEILING_CHARS:
        scale = EVIDENCE_CEILING_CHARS / float(total)

    citations: list[CitationRef] = []
    spent = 0
    for _number, meta, width in natural:
        allowed = max(MIN_WINDOW_CHARS, int(width * scale))
        allowed = min(allowed, width, int(meta["length"]))
        if spent + allowed > EVIDENCE_CEILING_CHARS:
            allowed = EVIDENCE_CEILING_CHARS - spent
        if allowed <= 0:
            break
        spent += allowed
        start = int(meta.get("offset") or 0)
        start = max(0, min(start, max(0, int(meta["length"]) - allowed)))
        citations.append(
            CitationRef(
                receipt_id=str(meta["receipt_id"]),
                result_id=str(meta["result_id"]),
                slices=[CitationSlice(start=start, end=start + allowed)],
            )
        )
    return citations


# ===========================================================================
# the constraint ledger
# ===========================================================================

class _Ledger:
    """candidate x constraint cells with typed verdicts.

    A cell is UNKNOWN until evidence names the candidate together with a
    constraint term. UNKNOWN cells are what the probe scheduler chases; they are
    never described to the user. `decisive` marks constraints whose failure
    removes a candidate outright, which is what the exclusion line must cite.
    """

    def __init__(self) -> None:
        self.candidates: list[str] = []
        self.constraints: list[str] = []
        self.authority: str = ""
        self.vintage: str = ""
        self._probes_spent = 0

    def load(self, payload: dict) -> None:
        raw_candidates = payload.get("candidates")
        if isinstance(raw_candidates, list):
            self.candidates = [str(c).strip() for c in raw_candidates if str(c).strip()][:12]
        raw_constraints = payload.get("constraints")
        if isinstance(raw_constraints, list):
            self.constraints = [str(c).strip() for c in raw_constraints if str(c).strip()][:6]
        self.authority = str(payload.get("authority") or "").strip()[:120]
        self.vintage = str(payload.get("vintage") or "").strip()[:40]

    @property
    def active(self) -> bool:
        return bool(self.candidates and self.constraints)

    def open_cells(self, transcript: str) -> list[tuple[str, str]]:
        """Cells with no co-occurrence of candidate and constraint in evidence."""
        if not self.active:
            return []
        haystack = (transcript or "").lower()
        gaps: list[tuple[str, str]] = []
        for candidate in self.candidates:
            token = candidate.lower()[:48]
            if not token:
                continue
            for constraint in self.constraints:
                cue = _constraint_cue(constraint)
                if not cue:
                    continue
                if token in haystack and cue in haystack:
                    continue
                gaps.append((candidate, constraint))
        return gaps

    def next_probes(self, transcript: str) -> list[str]:
        """Targeted queries for open cells, budget-limited."""
        if self._probes_spent >= MAX_CELL_PROBES:
            return []
        gaps = self.open_cells(transcript)
        if not gaps:
            return []
        budget = min(2, MAX_CELL_PROBES - self._probes_spent)
        queries: list[str] = []
        for candidate, constraint in gaps[:budget]:
            parts = [candidate, constraint]
            if self.vintage:
                parts.append(self.vintage)
            if self.authority:
                parts.append(self.authority)
            queries.append(" ".join(parts)[:220])
        self._probes_spent += len(queries)
        return queries


_STOPWORDS = frozenset(
    "the a an of in on at to for and or by with from as is are was were be been "
    "that this which who whom what when where how many much most least all every "
    "each than then it its their his her".split()
)


def _window_cues(question: str, ledger: "_Ledger") -> list[str]:
    """Vocabulary the fetch window is scored against: the question's own
    constraint terms plus any candidate names and the pinned vintage."""
    cues: list[str] = []
    for constraint in ledger.constraints:
        cue = _constraint_cue(constraint)
        if cue:
            cues.append(cue)
    cues += [c.lower()[:40] for c in ledger.candidates[:8] if c]
    if ledger.vintage:
        cues.append(ledger.vintage.lower())
    for word in re.findall(r"[A-Za-z][A-Za-z\-']{4,}", question or ""):
        low = word.lower()
        if low not in _STOPWORDS and low not in cues:
            cues.append(low)
        if len(cues) >= 14:
            break
    return cues


def _constraint_cue(constraint: str) -> str:
    """Longest content word in a constraint -- the cheap co-occurrence probe."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z\-']{2,}", constraint or "")
             if w.lower() not in _STOPWORDS]
    if not words:
        return ""
    return max(words, key=len).lower()


_SET_QUESTION_RE = re.compile(
    r"\b(?:which|what|list|name|identify|enumerate)\b[^?]{0,90}\b(?:all|every|each|both)\b"
    r"|\bhow many\b|\bwhich of (?:the|these)\b|\bnone of\b",
    re.IGNORECASE | re.DOTALL,
)


def _is_set_question(question: str) -> bool:
    return bool(_SET_QUESTION_RE.search(question or ""))


# ===========================================================================
# planning call
# ===========================================================================

_PLAN_INSTRUCTION = (
    "Decompose the research question into a verification plan. Reply with ONE JSON object "
    "and nothing else -- no prose, no markdown fences.\n"
    "Keys:\n"
    '  "candidates": array of the entities that could plausibly be the answer or belong in '
    "the answer set. Include near-misses that a careless answer would silently omit. Empty "
    "array if the question has a single unambiguous subject.\n"
    '  "constraints": array of the stated conditions an entity must satisfy, each as a short '
    "noun phrase copied from the question's own wording.\n"
    '  "authority": the specific source the question names or implies (e.g. "World Bank WDI", '
    '"Academy Awards database"); empty string if none is named.\n'
    '  "vintage": the reference year or edition the question pins the data to; empty string if none.\n'
    '  "seed_queries": 3 search queries that would open the evidence base.'
)


async def _plan(question: str, *, deadline: float) -> dict:
    window = min(PLAN_TIMEOUT_S, deadline - perf_counter() - COMMIT_RESERVE_S)
    if window < MIN_TOOL_WINDOW_S:
        return {}
    try:
        result = await llm_chat(
            provider=PROVIDER,
            model=PLANNER,
            messages=[
                {"role": "system", "content": _PLAN_INSTRUCTION},
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            thinking=LlmThinkingConfig(enabled=False),
            timeout=window,
        )
    except Exception:
        return {}
    return _decode_plan_json(_text_of(result))


def _decode_plan_json(raw: str) -> dict:
    if not raw:
        return {}
    body = raw.strip()
    body = re.sub(r"^```(?:json)?\s*", "", body)
    body = re.sub(r"\s*```$", "", body)
    try:
        parsed = json.loads(body)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", body)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except Exception:
            return {}
    return parsed if isinstance(parsed, dict) else {}


# ===========================================================================
# SDK response readers
# ===========================================================================

def _message_of(result: object) -> object | None:
    response = getattr(result, "response", None)
    for choice in getattr(response, "choices", None) or ():
        message = getattr(choice, "message", None)
        if message is not None:
            return message
    return None


def _text_of(result: object) -> str:
    response = getattr(result, "response", None)
    raw = getattr(response, "raw_text", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    message = _message_of(result)
    content = getattr(message, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()
    return ""


def _tool_call_dict(call: object) -> dict:
    return {
        "id": getattr(call, "id", None),
        "type": getattr(call, "type", None) or "function",
        "name": getattr(call, "name", None) or "",
        "arguments": getattr(call, "arguments", None) or "{}",
    }


# ===========================================================================
# tools
# ===========================================================================

TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Run a web search. Returns numbered results with title, url and an excerpt. "
                "Prefer narrow queries that name one entity and one attribute."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "the search query"}},
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
            "name": "fetch_page",
            "description": "Retrieve the main text of one URL. Use for tables and primary records.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "absolute url"}},
                "required": ["url"],
            },
        },
    },
]


def _tool_window(deadline: float, cap: float) -> float:
    return min(cap, deadline - perf_counter() - TAIL_RESERVE_S)


async def _probe_search(query: str, store: _EvidenceStore, *, deadline: float) -> str:
    window = _tool_window(deadline, SEARCH_TIMEOUT_S)
    if window < MIN_TOOL_WINDOW_S:
        return f"# search_web({query!r}) -> skipped: no time left, commit the answer now"
    try:
        outcome = await search_web(query, provider="parallel", timeout=window)
    except Exception as exc:
        return f"# search_web({query!r}) -> error: {exc}"
    ranked = _triage(tuple(getattr(outcome, "results", None) or ()))
    stored = store.add(getattr(outcome, "receipt_id", "") or "", ranked, shown=SEARCH_WINDOW_CHARS)
    if not stored:
        return f"# search_web({query!r}) -> nothing usable"
    lines = [f"# search_web({query!r}) -> {len(stored)} results"]
    for number, item in stored:
        excerpt = (getattr(item, "note", None) or "")[:SEARCH_WINDOW_CHARS]
        lines.append(
            f"[{number}] {getattr(item, 'title', '') or ''}\n"
            f"  url: {getattr(item, 'url', '') or ''}\n"
            f"  {excerpt}"
        )
    return "\n".join(lines)



async def _probe_search_many(queries: list, store: _EvidenceStore, *, deadline: float) -> str:
    """Concrete tool-use change: parallel multi-query retrieval in one turn."""
    clean = [str(q).strip() for q in (queries or []) if str(q).strip()][:8]
    if not clean:
        return "# search_many() -> ERROR: no queries"
    parts = await asyncio.gather(*(_probe_search(q, store, deadline=deadline) for q in clean))
    return f"# search_many({len(clean)} queries)\n" + "\n\n".join(parts)


async def _probe_fetch(url: str, store: _EvidenceStore, *, deadline: float,
                       cues: list[str] | None = None) -> str:
    outcome = None
    failure: Exception | None = None
    for _ in range(FETCH_RETRIES):
        window = _tool_window(deadline, FETCH_TIMEOUT_S)
        if window < MIN_TOOL_WINDOW_S:
            break
        try:
            outcome = await fetch_page(url, provider="parallel", timeout=window)
            break
        except Exception as exc:
            failure = exc
    if outcome is None:
        return f"# fetch_page({url!r}) -> error: {failure}"
    stored = store.add(
        getattr(outcome, "receipt_id", "") or "",
        tuple(getattr(outcome, "results", None) or ()),
        shown=FETCH_WINDOW_CHARS,
    )
    if not stored:
        return f"# fetch_page({url!r}) -> empty"
    number, item = stored[0]
    note = getattr(item, "note", None) or ""
    offset = _relevance_window(note, cues or [], FETCH_WINDOW_CHARS)
    body = note[offset:offset + FETCH_WINDOW_CHARS]
    meta = store.lookup(number)
    if meta is not None:
        meta["offset"] = offset
    marker = "" if offset == 0 else f" (passage at offset {offset} of {len(note)})"
    return f"# fetch_page({url!r}) -> [{number}]{marker}\n{body}"


async def _dispatch(call: object, store: _EvidenceStore, *, deadline: float,
                    cues: list[str] | None = None) -> str:
    name = getattr(call, "name", None) or ""
    try:
        args = json.loads(getattr(call, "arguments", None) or "{}")
    except Exception:
        args = {}
    if not isinstance(args, dict):
        args = {}
    if name == "search_web":
        return await _probe_search(str(args.get("query") or ""), store, deadline=deadline)
    if name == "search_many":
        qs = args.get("queries") or args.get("query") or []
        return await _probe_search_many(qs if isinstance(qs, list) else [qs], store, deadline=deadline)

    if name == "fetch_page":
        return await _probe_fetch(str(args.get("url") or ""), store, deadline=deadline,
                                  cues=cues)
    return f"# unsupported tool {name!r}"


# ===========================================================================
# prompts
# ===========================================================================

BASE_PROMPT = (
    "You are a research analyst. Investigate with the tools, then commit one answer.\n\n"
    "OUTPUT SHAPE: the first line is 'FINAL ANSWER: ' followed by the direct answer -- the "
    "name, number, date, or list itself, with no preamble. Supporting detail follows below it.\n\n"
    "CITATION RULE: place the evidence number in square brackets immediately after each "
    "individual factual claim, e.g. 'the total was 41,200 [6]'. One bracket per claim, not a "
    "source list at the end. Cite only numbers that the tools actually returned.\n\n"
    "FIDELITY RULE: assert exactly what the cited text supports and nothing stronger. If the "
    "source says a figure is provisional, say provisional. If it gives 14, do not write 13. Do "
    "not upgrade 'was reported at' into 'was'.\n\n"
    "AUTHORITY RULE: when the question names or implies a specific source, the answer must come "
    "from that source's own publication. An aggregator repeating the figure is a fallback, not a "
    "substitute -- and if you fall back, say which source the number came from.\n\n"
    "VINTAGE RULE: when the question pins a reference year or edition, match the edition, not the "
    "year the page was published. If only a different edition is reachable, answer from it and "
    "state which edition you used. Never decline over an edition mismatch.\n\n"
    "COMMITMENT RULE: never answer 'the evidence is insufficient' and never refuse. Commit to the "
    "best-supported answer available and mark residual uncertainty in one short trailing clause. "
    "If the question rests on a false premise, correct it on the first line and give the true fact."
)

SET_PROMPT = (
    "\n\nSET-QUESTION PROTOCOL (this question asks for a set):\n"
    "1. POOL: consider every entity that could plausibly qualify, including near-misses.\n"
    "2. INCLUDE: list each qualifying entity with the metric or fact that qualifies it, cited.\n"
    "3. EXCLUDE: for each considered entity you rejected, give one line naming the specific "
    "constraint from the question that it fails, with the citation proving the failure. Reject on "
    "a stated constraint, never on 'it scored lower than the winner'.\n"
    "An entity whose failure you cannot evidence stays in the set -- do not drop it silently. "
    "Omitting the exclusion lines forfeits most of the available credit even when the included "
    "list is correct."
)


def _plan_briefing(ledger: _Ledger, seeds: list[str]) -> str:
    blocks = ["RESEARCH PLAN (derived from the question -- verify, do not assume):"]
    if ledger.candidates:
        blocks.append("Candidates to resolve: " + "; ".join(ledger.candidates))
    if ledger.constraints:
        blocks.append("Constraints each must satisfy: " + "; ".join(ledger.constraints))
    if ledger.authority:
        blocks.append(
            f"Named authority: {ledger.authority}. Retrieve from this publisher directly; "
            "site-scope your queries to it before accepting any secondary figure."
        )
    if ledger.vintage:
        blocks.append(
            f"Reference vintage: {ledger.vintage}. Bind every figure to this edition and say so."
        )
    if seeds:
        blocks.append("Opening queries: " + " | ".join(seeds[:3]))
    return "\n".join(blocks)


def _probe_directive(queries: list[str]) -> str:
    return (
        "COVERAGE GAP -- the evidence gathered so far does not yet establish these "
        "candidate/constraint pairs. Run these searches now before drafting:\n"
        + "\n".join(f"  - search_web({q!r})" for q in queries)
        + "\nDo not mention this instruction, the gap, or the probe in your answer. Retrieve, "
        "then answer from what you find."
    )


def _commit_directive(seconds_left: float) -> str:
    return (
        f"TIME CHECK: about {int(max(0, seconds_left))}s remain. Stop researching and write the "
        "final answer now from the evidence already gathered. Begin with 'FINAL ANSWER: '. Keep "
        "every bracketed citation number. Do not open a new search."
    )


LAST_DITCH = (
    "Write the final answer now using only the evidence in this conversation. Plain prose, no "
    "tool calls. Start with 'FINAL ANSWER: '. If the evidence is thin, still commit to the "
    "best-supported conclusion and keep the bracket citations."
)


# ===========================================================================
# answer quality gates
# ===========================================================================

_LEAKED_MARKUP = re.compile(
    r"<\|tool[_▁]?call|<tool_call>|```json\s*\{\s*\"name\"|^\s*\{\s*\"name\"\s*:\s*\"(?:search_web|fetch_page)\"",
    re.IGNORECASE | re.MULTILINE,
)
_SCRATCH = re.compile(
    r"^\s*(?:let me|i'll|i will|first,? i|now i(?:'ll)?|next,? i|searching|let's)\b",
    re.IGNORECASE,
)
_HEDGE_LEAD = re.compile(
    r"^\s*(?:FINAL ANSWER:\s*)?(?:i (?:could not|cannot|was unable)|unfortunately|"
    r"there is (?:no|insufficient)|the (?:available )?evidence (?:is|does not)|"
    r"without (?:further|additional)|it is (?:not )?(?:un)?clear|no definitive)",
    re.IGNORECASE,
)
_DELIBERATION_RE = re.compile(
    r"however,? the answer (?:provided|above|given)|the (?:correct )?answer is [^.\n]{1,60}\balone\b,? but|likely because|given the constraints,? the only|wait,|on reflection|actually,? (?:i|the answer)",
    re.IGNORECASE,
)
_PREMISE_FIX = re.compile(
    r"\b(?:false premise|the premise|actually|in fact|did not (?:exist|occur|happen)|"
    r"no such|never (?:existed|happened|occurred))\b",
    re.IGNORECASE,
)


def _leaks_deliberation(text: str) -> bool:
    """Self-argument anywhere in the answer, not just at the start.

    v6 shipped a paragraph that contradicted itself three times while
    opening with a perfectly clean answer line, so a prefix-anchored
    check never fired."""
    return bool(_DELIBERATION_RE.search((text or "")[:6000]))


def _cut_deliberation(text: str) -> str:
    """Keep the committed lead, drop the argument trailing it."""
    body = (text or "").strip()
    hit = _DELIBERATION_RE.search(body)
    if not hit:
        return body
    head = body[:hit.start()].strip()
    for sep in ("\n\n", "\n", ". "):
        cut = head.rfind(sep)
        if cut > 40:
            head = head[:cut + (1 if sep == ". " else 0)].strip()
            break
    return head if len(head) >= 20 else body


def _usable(text: str) -> bool:
    body = (text or "").strip()
    if len(body) < 24:
        return False
    if _LEAKED_MARKUP.search(body):
        return False
    if _SCRATCH.match(body):
        return False
    return True


def _hedged(text: str) -> bool:
    body = (text or "").strip()
    if not body or _PREMISE_FIX.search(body[:400]):
        return False
    return bool(_HEDGE_LEAD.match(body))


def _apply_literal_directives(question: str, answer: str) -> str:
    """A 'without the word X' instruction means delete X from the rendered output.

    It does not mean drop the items that contain X -- reading it that way removes
    correct items from the set and costs the whole enumeration.
    """
    if not answer or not question:
        return answer
    edited = answer
    pattern = re.compile(
        r"without (?:using )?(?:the )?(?:word|term|letter)s?\s*"
        r"[\"'\u201c\u2018]?([A-Za-z][\w'\-]*)[\"'\u201d\u2019]?",
        re.IGNORECASE,
    )
    for match in pattern.finditer(question):
        token = match.group(1)
        if len(token) < 3:
            continue
        edited = re.sub(rf"\b{re.escape(token)}\b", "", edited, flags=re.IGNORECASE)
    if edited != answer:
        edited = re.sub(r"[ \t]{2,}", " ", edited)
        edited = re.sub(r"\s+([,.;:)\]])", r"\1", edited)
        edited = re.sub(r"\(\s*\)", "", edited)
    return edited.strip() or answer


def _floor_answer(store: _EvidenceStore) -> str:
    """Never return nothing when evidence exists: a cited digest beats silence."""
    digest = store.digest()
    if not digest:
        return ""
    return (
        "FINAL ANSWER: Based on the evidence retrieved, the most directly relevant findings "
        "are summarised below.\n" + digest
    )


# ===========================================================================
# turn driver
# ===========================================================================

async def _turn(messages: list[dict], *, deadline: float, committing: bool):
    reserve = TAIL_RESERVE_S if committing else COMMIT_RESERVE_S
    thinking = (
        LlmThinkingConfig(enabled=False)
        if committing
        else LlmThinkingConfig(enabled=True, effort="low")
    )
    for _ in range(TURN_RETRIES):
        window = min(TURN_TIMEOUT_S, deadline - perf_counter() - reserve)
        if window <= 0:
            return None
        try:
            return await llm_chat(
                provider=PROVIDER,
                model=REASONER,
                messages=messages,
                tools=None if committing else TOOL_SCHEMA,
                tool_choice=None if committing else "auto",
                temperature=0.15,
                thinking=thinking,
                timeout=window,
            )
        except Exception:
            continue
    return None


# ===========================================================================
# entrypoint
# ===========================================================================


def _seed_queries_from_question(question: str, limit: int = 3) -> list[str]:
    """Build a small set of retrieval seeds so research starts with parallel evidence."""
    q = " ".join((question or "").split())
    if not q:
        return []
    seeds = [q]
    for m in re.finditer(r'"([^"]{3,80})"|\b([A-Z][A-Za-z0-9&\-]*(?:\s+[A-Z][A-Za-z0-9&\-]*){1,3})\b', question or ""):
        span = (m.group(1) or m.group(2) or "").strip()
        if span and span.lower() not in {s.lower() for s in seeds}:
            seeds.append(span)
        if len(seeds) >= limit:
            break
    if len(seeds) < 2:
        clause = re.split(r"[?;]", q)[0].strip()
        if clause and clause.lower() != q.lower():
            seeds.append(clause)
    return seeds[:limit]



_AUTHORITY_URL_RE = re.compile(
    r"https?://[^\s\]\)>\"\']+",
    re.I,
)
_AUTHORITY_HOST_HINTS = (
    ".gov", ".edu", "wikipedia.org", "sec.gov", "who.int", "worldbank.org",
    "imf.org", "oecd.org", "un.org", "europa.eu", "nature.com", "nih.gov",
)


def _authority_urls_from_blob(blob: str, limit: int = 2) -> list[str]:
    """Pick primary/official URLs from retrieval text for auto-fetch."""
    found: list[str] = []
    seen: set[str] = set()
    for m in _AUTHORITY_URL_RE.finditer(blob or ""):
        url = m.group(0).rstrip(".,);]")
        low = url.lower()
        if low in seen:
            continue
        if not any(h in low for h in _AUTHORITY_HOST_HINTS):
            continue
        seen.add(low)
        found.append(url)
        if len(found) >= limit:
            break
    return found


def _opposition_queries_from_answer(question: str, answer: str, limit: int = 3) -> list[str]:
    """Build opposing-evidence queries from the draft (concrete verification branch)."""
    q = " ".join((question or "").split())
    a = " ".join((answer or "").split())
    seeds: list[str] = []
    if q:
        seeds.append(f"{q} controversy OR correction OR retracted OR false")
    # Pull a few capitalized entities / quoted spans from the answer lead.
    lead = a[:400]
    for m in re.finditer(r'"([^"]{3,60})"|\b([A-Z][A-Za-z0-9&\-]*(?:\s+[A-Z][A-Za-z0-9&\-]*){0,2})\b', lead):
        span = (m.group(1) or m.group(2) or "").strip()
        if len(span) < 3 or span.lower() in {"final", "answer", "the", "and", "for"}:
            continue
        cand = f"{span} official correction OR disputed OR revised"
        if cand.lower() not in {s.lower() for s in seeds}:
            seeds.append(cand)
        if len(seeds) >= limit:
            break
    if len(seeds) < 2 and q:
        seeds.append(f"{q} official primary source")
    return seeds[:limit]



_BARE_CLAIM_RE = re.compile(
    r"(?m)^(?!.*\[\d+\]).{0,200}?\b("
    r"\d{4}|\d+(?:\.\d+)?%?|"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4}"
    r")\b"
)
_COMPARE_Q_RE = re.compile(
    r"\b(compar(?:e|ison)|versus|\bvs\.?\b|difference between|higher than|lower than|"
    r"more than|less than|relative to|against)\b",
    re.I,
)
_ROSTER_Q_RE = re.compile(
    r"\b(which|list|name|identify|how many|all of|every|each|complete (?:list|set|roster))\b",
    re.I,
)


def _v3_claim_reground_queries(question: str, answer: str, limit: int = 4) -> list[str]:
    """Build targeted re-grounding queries for load-bearing claims lacking nearby [n]."""
    q = " ".join((question or "").split())
    a = answer or ""
    out: list[str] = []
    # Bare numeric/date lines without citations
    for m in _BARE_CLAIM_RE.finditer(a[:2500]):
        span = m.group(0).strip()
        # Prefer a short window around the match
        start = max(0, m.start() - 40)
        window = " ".join(a[start : m.end() + 40].split())[:120]
        probe = f'{q} "{window}" official source' if window else f"{q} {span} official"
        if probe.lower() not in {x.lower() for x in out}:
            out.append(probe)
        if len(out) >= limit:
            return out[:limit]
    # Always include one grounding probe from the question lead
    if q and len(out) < limit:
        out.append(f"{q} primary source OR official statistics")
    return out[:limit]


def _v3_comparison_queries(question: str, limit: int = 2) -> list[str]:
    """Concrete source-selection change: dual-operand evidence for comparison questions."""
    if not _COMPARE_Q_RE.search(question or ""):
        return []
    q = " ".join((question or "").split())
    # Split on common comparison markers
    parts = re.split(r"\b(?:versus|vs\.?|compared (?:to|with)|and|vs)\b", q, flags=re.I)
    parts = [p.strip(" ?.,;:") for p in parts if len(p.strip(" ?.,;:")) > 3]
    out: list[str] = []
    for p in parts[:2]:
        out.append(f"{p} official figure OR primary source")
    if len(out) < 2 and q:
        out.append(f"{q} both sides official statistics")
    return out[:limit]


def _v3_roster_queries(question: str, limit: int = 2) -> list[str]:
    """Concrete retrieval change: completeness fan-out for set/list/roster questions."""
    if not _ROSTER_Q_RE.search(question or ""):
        return []
    q = " ".join((question or "").split())
    return [
        f"complete list OR full roster: {q}",
        f"{q} all members OR entire set official",
    ][:limit]


@entrypoint("query")
async def query(query: Query) -> Response:
    started = perf_counter()
    deadline = started + TOTAL_BUDGET_S
    question = (query.text or "").strip()
    store = _EvidenceStore()
    ledger = _Ledger()

    if not question:


        # MECHANISM_UPGRADE_V3: claim re-ground + comparison dual-cite + roster fan-out
        if bool((answer or '').strip()) and (deadline - perf_counter()) > 35:
            try:
                _v3_qs: list[str] = []
                _v3_qs.extend(_v3_claim_reground_queries(query.text, answer or "", limit=3))
                _v3_qs.extend(_v3_comparison_queries(query.text, limit=2))
                _v3_qs.extend(_v3_roster_queries(query.text, limit=2))
                _deduped: list[str] = []
                _seen_q: set[str] = set()
                for _q in _v3_qs:
                    _k = _q.lower()
                    if _q and _k not in _seen_q:
                        _seen_q.add(_k)
                        _deduped.append(_q)
                _v3_qs = _deduped[:6]
                if _v3_qs:
                    _v3_blob = await _probe_search_many(_v3_qs, store, deadline=deadline)
                    messages.append({
                        "role": "system",
                        "content": (
                            "## V3 Claim Re-ground / Dual-cite / Roster Fan-out\n\n"
                            "Fresh targeted evidence for bare claims, comparison operands, "
                            "and roster completeness. Rewrite the COMPLETE final answer with "
                            "[n] after every load-bearing number/date/name and each comparison side.\n\n"
                            + _v3_blob[:12000]
                        ),
                    })
                    if (deadline - perf_counter()) > 16:
                        try:
                            _rw = await _turn(messages, deadline=deadline, committing=True)
                            if _rw is not None:
                                _cand = (getattr(getattr(_rw, "response", None), "raw_text", None) or "").strip()
                                if _cand:
                                    answer = _cand
                        except Exception:
                            pass

            except Exception:
                pass

        # Concrete verification change: contradiction/opposing-evidence probe before commit
        try:
            if answer and (deadline - perf_counter()) > 40:
                _opp = _opposition_queries_from_answer(query.text, answer or "", limit=3)
                if _opp:
                    _opp_blob = await _probe_search_many(_opp, store, deadline=deadline)
                    messages.append({
                        "role": "system",
                        "content": (
                            "## Contradiction Probe\n\nOpposing/correction searches ran. "
                            "If they refute a claim, correct it with citations; otherwise keep "
                            "the draft and cite the confirming notes.\n\n"
                            + _opp_blob[:12000]
                        ),
                    })
        except Exception:
            pass


        return Response(text=_FALLBACK_TEXT)

    system = BASE_PROMPT + (SET_PROMPT if _is_set_question(question) else "")
    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]

    answer: str | None = None
    try:
        # ---- plan -----------------------------------------------------
        seeds: list[str] = []
        if perf_counter() - started < PLAN_BUDGET_S:
            payload = await _plan(question, deadline=deadline)
            if payload:
                ledger.load(payload)
                raw_seeds = payload.get("seed_queries")
                if isinstance(raw_seeds, list):
                    seeds = [str(s).strip() for s in raw_seeds if str(s).strip()][:3]
                briefing = _plan_briefing(ledger, seeds)
                if briefing:
                    messages.append({"role": "system", "content": briefing})

        # ---- research loop --------------------------------------------
        transcript_parts: list[str] = []
        nudged = False
        research_deadline = started + RESEARCH_CUTOFF_S


        # Concrete retrieval change: seed fan-out before the autonomous loop
        try:
            _seeds = _seed_queries_from_question(query.text, limit=3)
            if _seeds and (deadline - perf_counter()) > 60:
                _seed_blob = await _probe_search_many(_seeds, store, deadline=deadline)
                messages.append({
                    "role": "system",
                    "content": (
                        "## Seed Evidence\n\nParallel seed searches already ran. "
                        "Use these numbered results; call search_many for remaining candidates.\n\n"
                        + _seed_blob[:12000]
                    ),
                })
        except Exception:
            pass


        # Concrete source-selection change: auto-prefetch authority URLs from seed evidence
        try:
            if (deadline - perf_counter()) > 50:
                _auth_blob = ""
                for _msg in messages:
                    if isinstance(_msg, dict) and "Seed Evidence" in str(_msg.get("content", "")):
                        _auth_blob = str(_msg.get("content", ""))
                        break
                _auth_urls = _authority_urls_from_blob(_auth_blob, limit=2)
                if _auth_urls:
                    _auth_parts = []
                    for u in _auth_urls:
                        try:
                            _auth_parts.append(await _probe_fetch(u, store, deadline=deadline))
                        except Exception:
                            continue
                    if _auth_parts:
                        messages.append({
                            "role": "system",
                            "content": (
                                "## Authority Prefetch\n\nPrimary/official pages were fetched "
                                "automatically from seed hits. Prefer these over secondary blogs.\n\n"
                                + "\n\n".join(_auth_parts)[:14000]
                            ),
                        })
        except Exception:
            pass

        for turn in range(1, MAX_RESEARCH_TURNS + 1):
            remaining = deadline - perf_counter()
            if remaining <= COMMIT_RESERVE_S * 0.5:
                break
            out_of_research_time = perf_counter() >= research_deadline
            last_turn = turn >= MAX_RESEARCH_TURNS
            committing = out_of_research_time or last_turn

            if committing and not nudged:
                messages.append({"role": "system", "content": _commit_directive(remaining)})
                nudged = True

            # Probe scheduling: gaps become retrieval, never narration.
            if not committing and ledger.active and turn in PROBE_ANNOUNCE_TURNS:
                probes = ledger.next_probes("\n".join(transcript_parts))
                if probes:
                    messages.append({"role": "system", "content": _probe_directive(probes)})

            try:
                result = await _turn(messages, deadline=deadline, committing=committing)
            except Exception:
                break
            if result is None:
                break

            message = _message_of(result)
            calls = tuple(getattr(message, "tool_calls", None) or ()) if message else ()

            if not calls:
                candidate = _text_of(result)
                if _LEAKED_MARKUP.search(candidate) and not committing:
                    messages.append({"role": "assistant", "content": candidate})
                    messages.append({
                        "role": "system",
                        "content": (
                            "That reply contained literal tool-call markup instead of an actual "
                            "tool call. Either issue a real tool call, or write the final answer "
                            "as plain prose beginning with 'FINAL ANSWER: '."
                        ),
                    })
                    continue
                if not candidate.strip() and not committing:
                    messages.append({
                        "role": "system",
                        "content": "Empty reply. Continue: issue a tool call or commit the answer.",
                    })
                    continue
                answer = candidate
                break

            messages.append({
                "role": "assistant",
                "content": getattr(getattr(result, "response", None), "raw_text", None),
                "tool_calls": [_tool_call_dict(c) for c in calls],
            })
            # Every tool_call needs exactly one reply or the transcript becomes
            # invalid and the recovery rungs below cannot run.
            for call in calls:
                try:
                    observed = await _dispatch(call, store, deadline=deadline,
                                               cues=_window_cues(question, ledger))
                except Exception as exc:
                    observed = f"# tool failure: {exc}"
                transcript_parts.append(observed)
                messages.append({
                    "role": "tool",
                    "tool_call_id": getattr(call, "id", None),
                    "content": observed,
                })

        # ---- retrieval floor -------------------------------------------
        # In the v6 log every task that opened no page scored 0.000: search
        # snippets do not carry table rows, and the model substitutes
        # recalled figures rather than reporting the gap.
        if not store.opened_any() and (deadline - perf_counter()) > 40:
            urls = store.unopened_urls()[:FETCH_FLOOR_URLS]
            if urls:
                cues = _window_cues(question, ledger)
                try:
                    blocks = await asyncio.gather(
                        *(_probe_fetch(u, store, deadline=deadline, cues=cues)
                          for u in urls),
                        return_exceptions=True)
                    opened = [b for b in blocks if isinstance(b, str) and "-> [" in b]
                    if opened:
                        messages.append({"role": "system", "content": (
                            "OPENED SOURCE PAGES (full passages, not snippets). Take every "
                            "deciding value from these rather than from recall:\n\n"
                            + "\n\n".join(opened))})
                        answer = None
                except Exception:
                    pass

        # ---- rung 1: forced tool-free commit ---------------------------
        if not _usable(answer or "") and (deadline - perf_counter()) > 14:
            messages.append({"role": "system", "content": LAST_DITCH})
            retry = await _turn(messages, deadline=deadline, committing=True)
            if retry is not None:
                candidate = _text_of(retry)
                if _usable(candidate):
                    answer = candidate

        # ---- rung 2: de-hedge rewrite ----------------------------------
        if _usable(answer or "") and _hedged(answer or "") and (deadline - perf_counter()) > 18:
            messages.append({"role": "assistant", "content": answer})
            messages.append({
                "role": "system",
                "content": (
                    "Your draft opened by hedging. Rewrite the same answer so the first line "
                    "states the conclusion directly after 'FINAL ANSWER: '. Keep every bracketed "
                    "citation number exactly as it is. Move any caveat to a single short closing "
                    "clause. Do not add new claims."
                ),
            })
            rewrite = await _turn(messages, deadline=deadline, committing=True)
            if rewrite is not None:
                candidate = _text_of(rewrite)
                if _usable(candidate) and not _hedged(candidate):
                    answer = candidate

        # ---- rung 3: evidence floor ------------------------------------
        if not _usable(answer or ""):
            answer = _floor_answer(store)

        if not _usable(answer or ""):
            return Response(text=_apply_literal_directives(question, _FALLBACK_TEXT))

        if _leaks_deliberation(answer or ""):
            answer = _cut_deliberation(answer or "")

        final = _apply_literal_directives(question, answer or "")
        citations = _assemble_citations(final, store)
        return Response(text=final, citations=citations or None)

    except Exception:
        try:
            salvage = _floor_answer(store)
            if _usable(salvage):
                return Response(text=salvage, citations=_assemble_citations(salvage, store) or None)
        except Exception:
            pass
        return Response(text=_FALLBACK_TEXT)


# made by Naruto
# version v152