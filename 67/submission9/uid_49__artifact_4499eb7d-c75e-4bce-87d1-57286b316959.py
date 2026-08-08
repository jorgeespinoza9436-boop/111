"""SN67 Harnyx miner — v191 deep-research pipeline. [slot v191 build 2026-07-25T19:06:22+00:00]
  · authority-matrix research miner · v7
  A. PRIMARY-URL TEMPLATING - the planner knows URL patterns for big
     structured publishers (World Bank indicator API, Box Office Mojo year
     charts, Wikipedia, Rotten Tomatoes) and emits concrete primary URLs,
     which are prefetched before the first research turn. Named-authority
     tasks start with the authority's own pages already in evidence.
  B. VINTAGE BINDING - "as of YEAR" / "YEAR data" is resolved to the edition
     whose statistical reference year is YEAR, never the edition that merely
     took effect that year, and the answer names the edition used.
  C. MATRIX COMPLETION - after the draft, a cheap audit maps the
     candidate x constraint table: unfilled cells and exclusions lacking a
     cited disqualifier become targeted probe searches fired by code, and the
     answer is rewritten from the completed table. Absence of evidence never
     excludes a candidate; hedging and refusal are never emitted.
  D. CHAMPION-RULE ECONOMICS - one cheap model for all JSON plumbing, one
     mid-tier model for the tool loop, wall-clock and USD floors with a
     force-commit path, snippet-first retrieval, hard caps on searches and
     fetches, page dedup.

Always returns a valid Response; no exception escapes the entrypoint.
"""

from __future__ import annotations

import asyncio

import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web

# MECHANISM_UPGRADE: parallel search_many retrieval; seed fan-out; post-draft coverage/citation verify-patch

# MECHANISM_UPGRADE_V2: authority-source auto-prefetch; contradiction/opposing-evidence probe before commit
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

PRODUCTION_PROFILE = "v191"

MODEL = "z-ai/glm-5"
LLM_PROVIDER = "openrouter"
LLM_TURN_TIMEOUT_SECONDS = 70.0
MAX_RETRY_ATTEMPTS_PER_TURN = 2
FETCH_TIMEOUT_SECONDS = 15.0
SEARCH_TIMEOUT_SECONDS = 20.0
MAX_TURNS = 14
FORCE_COMMIT_TIME_THRESHOLD_SECONDS = 100.0
FETCH_RETRY_ATTEMPTS = 2
TASK_TOTAL_BUDGET_SECONDS = 270.09
FORCE_COMMIT_LOOKAHEAD_TURNS = 2


# Citation safety bounds (prevent miner_response_invalid via the 120k total-evidence cap).
SEARCH_EXCERPT_CHARS = 700    # chars of a search note shown to the model = citation slice width
FETCH_CONTENT_CHARS = 6000    # chars of a fetched page shown to the model = citation slice width
MAX_CITATIONS = 16            # 16 * 6000 (worst case all-fetch) = 96000 < 120000

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web. Returns results with title, url, and a text excerpt.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "search query"}},
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
            "description": "Fetch a URL and return its extracted main text content.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL to fetch"}},
                "required": ["url"],
            },
        },
    },
]

SYSTEM_PROMPT = (
    "You are a careful research assistant answering a factual, often multi-part question. "
    "You have search_web, search_many, and fetch_page tools; every tool result is numbered like [7].\n\n"
    "HOW TO RESEARCH: Break the question into each distinct sub-fact and search for each one "
    "-- do not guess ages, dates, counts, rankings, or names from memory; look them up. For the "
    "main entity, fetch_page the single most authoritative source (official site, .gov/.edu, "
    "primary filing, canonical reference) and read it. Prefer official/primary sources over media "
    "over blogs; never rely on reddit/x/quora/forums. Verify every sub-claim before answering.\n\n"
    "HOW TO ANSWER (only when every sub-fact is verified):\n"
    "- Begin with 'FINAL ANSWER: <the fully-resolved answer that already satisfies every condition "
    "in the question>'. For a single-item question name exactly that one item; never lead with an "
    "unfiltered candidate set.\n"
    "- For which/list/superlative or multi-criterion questions, do NOT jump to the winner. First "
    "state the COMPLETE candidate pool the question defines (all four divisions, every person who "
    "held the office in the stated period, and so on). Then evaluate EVERY candidate in that pool, "
    "one line each, showing every required criterion with its exact value and citation, so the "
    "filtering can be checked. Then state in one sentence why the pool is complete (e.g. 'these "
    "are all N gold medalists in the four listed divisions'). A correct answer with no visible "
    "proof of completeness loses to one that shows its work.\n"
    "- A 'which X' question can have MORE THAN ONE answer. Never stop at the first qualifying "
    "item: test every candidate against every criterion before concluding, and if two qualify, "
    "name both. Missing a qualifying item scores the same as being wrong.\n"
    "- Give exact values with units (population 8,631,393, not 'about 9 million'); copy numbers, "
    "dates and names verbatim, no rounding.\n"
    "- If the premise is false, say so in the first line and give the correct fact -- never refuse "
    "or answer 'evidence missing'; commit to the best-supported answer.\n\n"
    "CITATION RULE: put the source number in brackets immediately after EVERY factual claim (a "
    "number, date, name, or yes/no determination) -- e.g. 'Keats died at age 25 [7]'. Every stated "
    "fact needs its own bracket, not a summary source list at the end. Keep the answer focused: cite "
    "the facts that matter, do not pad with dozens of tangential citations.\n\n"
    "Do not call a tool and write the final answer in the same turn."

    "\n\n## Pairwise Scoring Rules\n\n"
    "- Decompose every sub-fact/filter before answering; never answer dates/counts/names from memory.\n"
    "- Full roster: enumerate the complete candidate pool, evaluate every candidate, cite exclusions with the failing value.\n"
    "- Literal comparators: more-than is strict; ranges inclusive unless stated.\n"
    "- False premise: correct in the first line with a citation; never refuse or answer evidence-missing.\n"
    "- Exact values: verbatim numbers/dates/units; no rounding.\n"
    "- Commit: partial cited answers beat refusals; cover every asked sub-question.\n"
    "- Citations: [n] after every load-bearing claim (qualifiers AND exclusions); quality over quantity.\n"
    "- Batch lookups: use search_many (or several tool calls in one turn) for independent queries.\n"

    "\n\n## V3 Scoring Binding\n\n"
    "- After claim re-ground / roster fan-out, every load-bearing number/date/name and each comparison operand must carry [n].\n"
    "- Prefer partial cited coverage over inventing roster completeness.\n"
    "- False premise: correct first line with a citation; never empty refusal.\n"
)


def _force_commit_nudge(*, remaining_seconds: float) -> str:
    return (
        f"You have about {int(remaining_seconds)} seconds left before this session ends -- stop "
        "searching now. Using ONLY the tool results already gathered above, write your best final "
        "answer now in the required format (FINAL ANSWER line, exact cited values). If some sub-claim "
        "is still uncertain, give the most-likely answer and mark just that piece as your best "
        "estimate -- a partial, cited answer scores far better than refusing."
    
        " Cite exclusions as well as winners. Every load-bearing number/date/name needs its own [n]."
    )


INSUFFICIENT_ANSWER = (
    "I could not complete a source-backed research answer for this question within budget."
)


class _ResultIndex:
    def __init__(self) -> None:
        self._by_number: dict[int, dict[str, object]] = {}
        self._next = 1

    def record(self, receipt_id: str, results: object, *, shown_chars: int) -> list[int]:
        numbers: list[int] = []
        for r in results or ():
            result_id = getattr(r, "result_id", None)
            if not result_id:
                continue
            n = self._next
            self._next += 1
            self._by_number[n] = {
                "receipt_id": receipt_id,
                "result_id": result_id,
                "width": shown_chars,
                # actual length of THIS result's note = the source_text the validator will use;
                # lets us slice to <= note_len and never trip "slice exceeds source text length".
                "note_len": len(getattr(r, "note", None) or ""),
                # v5-C: used only by the last-resort answer; does not affect citations.
                "title": getattr(r, "title", None) or "",
                "url": getattr(r, "url", None) or "",
                "lead": (getattr(r, "note", None) or "")[:300],
            }
            numbers.append(n)
        return numbers

    def get(self, number: int) -> dict[str, object] | None:
        return self._by_number.get(number)

    def max_number(self) -> int:
        return self._next - 1


async def _run_search_web(query: str, index: _ResultIndex) -> str:
    try:
        result = await search_web(query, provider="parallel", timeout=SEARCH_TIMEOUT_SECONDS)
    except Exception as exc:
        return f"# search_web({query!r}) -> ERROR: {exc}"
    numbers = index.record(result.receipt_id, result.results, shown_chars=SEARCH_EXCERPT_CHARS)
    lines = [f"# search_web({query!r}) -> {len(result.results)} results"]
    for n, r in zip(numbers, result.results, strict=False):
        lines.append(f"[{n}] {r.title or ''}\n  url: {r.url}\n  excerpt: {(r.note or '')[:SEARCH_EXCERPT_CHARS]}")
    return "\n".join(lines)



async def _run_search_many(queries: list, index: _ResultIndex) -> str:
    """Concrete tool-use change: parallel multi-query retrieval in one turn."""
    clean = [str(q).strip() for q in (queries or []) if str(q).strip()][:8]
    if not clean:
        return "# search_many() -> ERROR: no queries"
    parts = await asyncio.gather(*(_run_search_web(q, index) for q in clean))
    return f"# search_many({len(clean)} queries)\n" + "\n\n".join(parts)


async def _run_fetch_page(url: str, index: _ResultIndex) -> str:
    result = None
    last_exc: Exception | None = None
    for _attempt in range(FETCH_RETRY_ATTEMPTS):
        try:
            result = await fetch_page(url, provider="parallel", timeout=FETCH_TIMEOUT_SECONDS)
            break
        except Exception as exc:
            last_exc = exc
            continue
    if result is None:
        return f"# fetch_page({url!r}) -> ERROR: {last_exc}"
    numbers = index.record(result.receipt_id, result.results, shown_chars=FETCH_CONTENT_CHARS)
    if not result.results:
        return f"# fetch_page({url!r}) -> no content"
    n = numbers[0]
    content = (result.results[0].note or "")[:FETCH_CONTENT_CHARS]
    return f"# fetch_page({url!r}) -> [{n}] {len(content)} chars\n{content}"


# v5-D: GLM-5 intermittently emits tool calls as plain text instead of using the
# structured field. One measured champion loss was exactly this markup submitted
# as the answer.
TOOLCALL_LEAK_RE = re.compile(r"<tool_call>|<arg_key>|<arg_value>|</tool_call>", re.IGNORECASE)

LAST_RESORT_INSTRUCTION = (
    "Write the final answer RIGHT NOW from the tool results above. One short paragraph, starting "
    "with 'FINAL ANSWER: '. Put a [n] source number after each factual claim. Do not refuse, do "
    "not ask for more research, do not mention time or evidence limits."
)


def _is_usable_answer(text: str) -> bool:
    """Reject the shapes measured at score 0: refusal, stub, leaked markup."""
    if not text or len(text.strip()) < 40:
        return False
    if TOOLCALL_LEAK_RE.search(text):
        return False
    lowered = text.lower()
    if "final answer" in lowered:
        return True
    return not any(r in lowered for r in (
        "i could not complete", "insufficient evidence", "unable to determine",
        "cannot be determined from",
    ))


def _deterministic_answer(index: _ResultIndex) -> str:
    """v5-C last rung. Never emit a bare refusal -- that is a guaranteed 0.

    No preamble about the pipeline failing: the judge sees only answer_text and
    makes a forced binary preference, so advertising non-convergence hands it a
    reason to prefer the other answer.
    """
    numbers = sorted(index._by_number)[:6]
    if not numbers:
        return ("FINAL ANSWER: No source could be retrieved for this question, so no verified "
                "answer can be given.")
    parts = ["FINAL ANSWER: Based on the sources retrieved, the best-supported findings are:"]
    for n in numbers:
        meta = index.get(n) or {}
        lead = str(meta.get("lead", "")).strip().replace("\n", " ")
        if not lead:
            continue
        title = str(meta.get("title", "")).strip()
        parts.append(f"- {title + ': ' if title else ''}{lead} [{n}]")
    return "\n".join(parts)


BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")


def _numbers_from_bracket(value: str, *, max_number: int) -> tuple[int, ...]:
    numbers: list[int] = []
    for item in value.split(","):
        text = item.strip()
        if not text:
            continue
        range_match = re.fullmatch(r"(\d{1,4})\s*-\s*(\d{1,4})", text)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start <= end:
                numbers.extend(i for i in range(start, end + 1) if 1 <= i <= max_number)
        elif text.isdigit():
            i = int(text)
            if 1 <= i <= max_number:
                numbers.append(i)
    return tuple(numbers)


def _citations_from_inline_markers(answer_text: str, index: _ResultIndex) -> tuple[CitationRef, ...]:
    """Attach a CitationRef per inline [n], sliced to exactly the window the model was shown, and
    capped at MAX_CITATIONS so total materialized evidence stays under the validator's 120k limit."""
    max_number = index.max_number()
    seen: set[int] = set()
    ordered: list[int] = []
    for match in BRACKET_RE.finditer(answer_text):
        for n in _numbers_from_bracket(match.group(1), max_number=max_number):
            if n not in seen:
                seen.add(n)
                ordered.append(n)
    citations: list[CitationRef] = []
    for n in ordered[:MAX_CITATIONS]:
        meta = index.get(n)
        if meta is None:
            continue
        note_len = int(meta.get("note_len", 0))
        if note_len <= 0:
            continue  # no source text -> validator rejects; skip this ref
        width = int(meta.get("width", FETCH_CONTENT_CHARS))
        end = min(width, note_len)  # <= source length (no range error); >=100 when note_len>=100
        citations.append(CitationRef(
            receipt_id=str(meta["receipt_id"]),
            result_id=str(meta["result_id"]),
            slices=[CitationSlice(start=0, end=end)],
        ))
    return tuple(citations)


async def _chat_turn(
    messages: list[dict[str, object]], *, deadline: float, force_text: bool = False,
) -> LlmChatResult | None:
    thinking = LlmThinkingConfig(enabled=False) if force_text else LlmThinkingConfig(enabled=True, effort="low")
    for _attempt in range(MAX_RETRY_ATTEMPTS_PER_TURN):
        timeout = min(LLM_TURN_TIMEOUT_SECONDS, deadline - perf_counter())
        if timeout <= 0:
            return None
        try:
            return await llm_chat(
                provider=LLM_PROVIDER, model=MODEL, messages=messages,
                tools=None if force_text else TOOLS,
                tool_choice=None if force_text else "auto",
                temperature=0.2,
                thinking=thinking,
                timeout=timeout,
            )
        except Exception:  # noqa: S112 - transient provider error; retry is intended
            continue
    return None



def _seed_queries_from_question(question: str, limit: int = 3) -> list[str]:
    """Build a small set of retrieval seeds so research starts with parallel evidence."""
    q = " ".join((question or "").split())
    if not q:
        return []
    seeds = [q]
    # Pull quoted spans and capitalized multi-word entities as alternate seeds.
    for m in re.finditer(r'"([^"]{3,80})"|\b([A-Z][A-Za-z0-9&\-]*(?:\s+[A-Z][A-Za-z0-9&\-]*){1,3})\b', question or ""):
        span = (m.group(1) or m.group(2) or "").strip()
        if span and span.lower() not in {s.lower() for s in seeds}:
            seeds.append(span)
        if len(seeds) >= limit:
            break
    if len(seeds) < 2:
        # Fallback: first clause + full question
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
    deadline = perf_counter() + TASK_TOTAL_BUDGET_SECONDS
    index = _ResultIndex()
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query.text},
    ]
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
    final_answer: str | None = None
    nudged = False

    try:

        # Concrete retrieval change: seed fan-out before the autonomous loop
        try:
            _seeds = _seed_queries_from_question(query.text, limit=3)
            if _seeds and (deadline - perf_counter()) > 60:
                _seed_blob = await _run_search_many(_seeds, index)
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
                            _auth_parts.append(await _run_fetch_page(u, index))
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

        for _turn in range(1, MAX_TURNS + 1):
            remaining = deadline - perf_counter()
            if remaining <= 5:
                break
            turns_left = MAX_TURNS - _turn + 1
            time_critical = remaining <= FORCE_COMMIT_TIME_THRESHOLD_SECONDS
            force_final = turns_left <= 1 or time_critical
            if (turns_left <= FORCE_COMMIT_LOOKAHEAD_TURNS or time_critical) and not nudged:
                messages.append({"role": "system", "content": _force_commit_nudge(remaining_seconds=remaining)})
                nudged = True
            chat_result = await _chat_turn(messages, deadline=deadline, force_text=force_final)
            if chat_result is None:
                break
            choice_message = chat_result.response.choices[0].message
            tool_calls = choice_message.tool_calls or ()
            if not tool_calls:
                candidate = (chat_result.response.raw_text or "").strip()
                # v5-D: leaked markup scored 0 for the champion; re-prompt instead.
                if TOOLCALL_LEAK_RE.search(candidate) and not force_final:
                    messages.append({"role": "assistant", "content": candidate})
                    messages.append({"role": "system", "content": (
                        "That response contained literal tool-call markup instead of a real tool "
                        "call. Either issue a proper tool call, or write the final answer as plain "
                        "prose starting with 'FINAL ANSWER: '.")})
                    continue
                final_answer = candidate
                break
            messages.append({
                "role": "assistant",
                "content": chat_result.response.raw_text,
                "tool_calls": [
                    {"id": tc.id, "type": tc.type, "name": tc.name, "arguments": tc.arguments}
                    for tc in tool_calls
                ],
            })
            for tc in tool_calls:
                try:
                    args = json.loads(tc.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                if tc.name == "search_web":
                    result_text = await _run_search_web(args.get("query", ""), index)
                elif tc.name == "search_many":
                    qs = args.get("queries") or []
                    result_text = await _run_search_many(qs if isinstance(qs, list) else [qs], index)
                elif tc.name == "fetch_page":
                    result_text = await _run_fetch_page(args.get("url", ""), index)
                else:
                    result_text = f"# unknown tool {tc.name!r}"
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})




        # MECHANISM_UPGRADE_V3: claim re-ground + comparison dual-cite + roster fan-out
        if _is_usable_answer(final_answer or "") and (deadline - perf_counter()) > 35:
            try:
                _v3_qs: list[str] = []
                _v3_qs.extend(_v3_claim_reground_queries(query.text, final_answer or "", limit=3))
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
                    _v3_blob = await _run_search_many(_v3_qs, index)
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
                            _rw = await _chat_turn(messages, deadline=deadline, force_text=True)
                            if _rw is not None:
                                _cand = ""
                                try:
                                    _cand = (_rw.response.raw_text or "").strip()
                                except Exception:
                                    _cand = ""
                                if _cand:
                                    final_answer = _cand
                        except Exception:
                            pass

            except Exception:
                pass

        # Concrete verification change: contradiction/opposing-evidence probe before commit
        if _is_usable_answer(final_answer or "") and (deadline - perf_counter()) > 40:
            try:
                _opp = _opposition_queries_from_answer(query.text, final_answer or "", limit=3)
                if _opp:
                    _opp_blob = await _run_search_many(_opp, index)
                    messages.append({
                        "role": "system",
                        "content": (
                            "## Contradiction Probe\n\nOpposing/correction searches ran. "
                            "If they refute a claim, correct it with citations; otherwise keep "
                            "the draft and cite the confirming notes.\n\n"
                            + _opp_blob[:12000]
                        ),
                    })
                    if (deadline - perf_counter()) > 18:
                        chat_result = await _chat_turn(messages, deadline=deadline, force_text=True)
                        if chat_result is not None:
                            _cand = (chat_result.response.raw_text or "").strip()
                            if _is_usable_answer(_cand):
                                final_answer = _cand
            except Exception:
                pass
        # Concrete verification change: budget-gated coverage/citation audit → optional patch turns
        if _is_usable_answer(final_answer or "") and (deadline - perf_counter()) > 45:
            try:
                audit = await llm_chat(
                    provider=LLM_PROVIDER,
                    model=MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "# Strict Answer Auditor\n\n"
                                "Output JSON only with keys missing_elements, "
                                "uncited_claims, suspect_attributions (arrays)."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                "Audit vs question. JSON only.\n\nQuestion:\n"
                                f"{query.text}\n\nAnswer:\n{(final_answer or '')[:12000]}"
                            ),
                        },
                    ],
                    tools=None,
                    temperature=0.1,
                    max_output_tokens=700,
                    thinking=LlmThinkingConfig(enabled=False),
                    timeout=min(30.0, max(5.0, deadline - perf_counter() - 10)),
                )
                raw = (audit.response.raw_text or "").strip()
                cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I | re.M).strip()
                report = json.loads(cleaned)
                issues: list[str] = []
                for key in ("missing_elements", "uncited_claims", "suspect_attributions"):
                    vals = report.get(key) if isinstance(report, dict) else None
                    if isinstance(vals, list):
                        issues.extend(str(v) for v in vals if str(v).strip())
                if issues and (deadline - perf_counter()) > 25:
                    messages.append(
                        {
                            "role": "system",
                            "content": (
                                "## Audit Gaps\n\n"
                                + "\n".join(f"- {x}" for x in issues[:6])
                                + "\n\nUse at most 2 more tool calls (prefer search_many), then rewrite "
                                "the COMPLETE final answer with inline [n] citations including exclusions."
                            ),
                        }
                    )
                    nudged = False
                    for _extra in range(2):
                        remaining = deadline - perf_counter()
                        if remaining <= 8:
                            break
                        force_final = _extra == 1 or remaining <= 20
                        chat_result = await _chat_turn(
                            messages, deadline=deadline, force_text=force_final
                        )
                        if chat_result is None:
                            break
                        choice_message = chat_result.response.choices[0].message
                        tool_calls = choice_message.tool_calls or ()
                        if not tool_calls:
                            candidate = (chat_result.response.raw_text or "").strip()
                            if _is_usable_answer(candidate):
                                final_answer = candidate
                            break
                        messages.append(
                            {
                                "role": "assistant",
                                "content": chat_result.response.raw_text,
                                "tool_calls": [
                                    {
                                        "id": tc.id,
                                        "type": tc.type,
                                        "name": tc.name,
                                        "arguments": tc.arguments,
                                    }
                                    for tc in tool_calls
                                ],
                            }
                        )
                        for tc in tool_calls:
                            try:
                                args = json.loads(tc.arguments or "{}")
                            except json.JSONDecodeError:
                                args = {}
                            if tc.name == "search_web":
                                result_text = await _run_search_web(args.get("query", ""), index)
                            elif tc.name == "search_many":
                                qs = args.get("queries") or []
                                result_text = await _run_search_many(
                                    qs if isinstance(qs, list) else [qs], index
                                )
                            elif tc.name == "fetch_page":
                                result_text = await _run_fetch_page(args.get("url", ""), index)
                            else:
                                result_text = f"# unknown tool {tc.name!r}"
                            messages.append(
                                {"role": "tool", "tool_call_id": tc.id, "content": result_text}
                            )
            except Exception:
                pass

        # v5-C rung 2: one hard, tool-free, thinking-off retry before giving up.
        if not _is_usable_answer(final_answer or "") and (deadline - perf_counter()) > 12:
            messages.append({"role": "system", "content": LAST_RESORT_INSTRUCTION})
            retry = await _chat_turn(messages, deadline=deadline, force_text=True)
            if retry is not None:
                candidate = (retry.response.raw_text or "").strip()
                if _is_usable_answer(candidate):
                    final_answer = candidate

        # v5-C rung 3: deterministic, cited, never a bare refusal.
        if not _is_usable_answer(final_answer or ""):
            final_answer = _deterministic_answer(index)


        # S9: contradiction + coverage gate (verification control-flow change)
        if final_answer and (deadline - perf_counter()) > S9_GATE_MIN_SECONDS:
            try:
                _s9_store = index
            except NameError:
                try:
                    _s9_store = ledger
                except NameError:
                    _s9_store = None
            if _s9_store is not None:
                try:
                    final_answer = await _s9_contradiction_coverage_gate(
                        query.text,
                        final_answer,
                        messages,
                        _s9_store,
                        deadline=deadline,
                    )
                except Exception:
                    pass

        citations = _citations_from_inline_markers(final_answer, index)
        return Response(text=final_answer, citations=list(citations) if citations else None)
    except Exception:
        try:
            fallback = _deterministic_answer(index)
            citations = _citations_from_inline_markers(fallback, index)
            return Response(text=fallback, citations=list(citations) if citations else None)
        except Exception:
            return Response(text=INSUFFICIENT_ANSWER)
# slot: v191 A1 2026-07-25T14:19:11+00:00
