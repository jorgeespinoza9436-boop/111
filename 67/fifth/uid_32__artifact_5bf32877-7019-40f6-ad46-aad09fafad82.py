"""SN67 Harnyx miner — autonomous tool-use research pipeline. [slot 29 build 2026-07-24T15:00:00+00:00]"""
from __future__ import annotations

import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

LLM_PROVIDER = "openrouter"
MODEL = "z-ai/glm-5"
MAX_RETRY_ATTEMPTS_PER_TURN = 2
FETCH_RETRY_ATTEMPTS = 2
SYNTH_RESERVE_SECONDS = 80.0
MAX_TURNS = 16
SYNTH_RETRY_MIN_SECONDS = 25.0
FETCH_TIMEOUT_SECONDS = 15.0
TASK_TOTAL_BUDGET_SECONDS = 270.0
FETCH_FAIL_DOMAIN_BUDGET = 2
DIGEST_NOTE_CHARS = 400
DIGEST_TOTAL_CHARS = 18_000
LLM_TURN_TIMEOUT_SECONDS = 90.0
SEARCH_TIMEOUT_SECONDS = 20.0
MIN_ANSWER_CHARS = 400
HARD_MIN_ANSWER_CHARS = 200
CITATION_BUDGET_CHARS = 90_000
CITATION_SLICE_MIN_CHARS = 4_000
CITATION_ANCHOR_CONTEXT_CHARS = 160
CITATION_ANCHOR_LEAD_CHARS = 800

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

SYSTEM_PROMPT = """# Research Assistant Instructions

You are a careful research assistant answering a factual multi-part question.

## Tools

You have `search_web` and `fetch_page` tools. Call them as many times as needed to verify every sub-claim before answering — do not guess ages, dates, or line counts from memory; look them up. Every tool result is numbered like `[7]` when shown to you.

## Citations

When you write your final answer, put the source number in brackets immediately after **every** factual claim (a number, date, name, or yes/no determination) — e.g. `Keats died at age 25 [7]` or `the total is 4,000 [7, 12].` Cite a claim for entities that qualify AND entities that don't — every stated fact needs its own citation, not just a summary source list at the end. A claim with no bracket after it is assumed uncited.

When (and only when) you are confident in every fact, write your final answer with inline citations as described. Do not call a tool and answer in the same turn.
"""

SYNTHESIS_SYSTEM_PROMPT = """# Synthesis Instructions

You are a careful research assistant. The research phase for this question is over: tools are DISABLED, and any tool-call syntax you emit will be shipped verbatim to the grader as your final answer, scoring zero. Using ONLY the numbered evidence excerpts provided, write your best final answer now.

## Commit Rule

Scoring is pairwise against a competitor's answer — an answer that refuses or defers scores zero and loses outright. If some sub-claims are uncertain, commit to what the evidence supports and note the uncertainty inline; a partial, cited answer scores far better than no answer.

## Citations

Put the evidence number in brackets immediately after every factual claim — e.g. `the total is 4,000 [7, 12].` A claim with no bracket after it is assumed uncited.
"""

FORCED_COMMIT_SUFFIX = """

## Forced Commit

Your previous draft refused, stalled, or was cut short. That scores **zero**. Rewrite now: commit to the best evidence-supported answer, cite every claim, and do not emit tool-call syntax or apologies.
"""

INSUFFICIENT_ANSWER = (
    "I could not complete a source-backed research answer for this question within budget."
)

TOOL_MARKUP_RE = re.compile(
    r"<\s*/?\s*(tool_call|arg_key|arg_value)\b[^>]*>", re.IGNORECASE,
)
ABSTENTION_MARKERS = (
    "i could not", "i cannot", "i was unable", "unable to", "cannot answer",
    "insufficient evidence", "no evidence", "could not find", "cannot determine",
    "cannot be determined", "i don't have", "i do not have", "not enough information",
)


class _ResultIndex:
    def __init__(self) -> None:
        self._by_number: dict[int, dict[str, str]] = {}
        self._next = 1

    def record(self, receipt_id: str, results: object, *, kind: str = "search") -> list[int]:
        numbers: list[int] = []
        for r in results or ():
            result_id = getattr(r, "result_id", None)
            if not result_id:
                continue
            n = self._next
            self._next += 1
            note = (getattr(r, "note", None) or "")
            self._by_number[n] = {
                "receipt_id": receipt_id,
                "result_id": result_id,
                "kind": kind,
                "citable": bool(note.strip()),
                "src_len": len(note),
                "title": (getattr(r, "title", None) or "")[:200],
                "url": (getattr(r, "url", None) or "")[:300],
                "note": note,
            }
            numbers.append(n)
        return numbers

    def get(self, number: int) -> dict[str, str] | None:
        return self._by_number.get(number)

    def max_number(self) -> int:
        return self._next - 1

    def digest(self) -> str:
        parts: list[str] = []
        total = 0
        for n in range(1, self._next):
            meta = self._by_number[n]
            if not meta.get("citable", True):
                continue
            note = meta["note"][:DIGEST_NOTE_CHARS]
            entry = f"[{n}] {meta['title']}\n  url: {meta['url']}\n  excerpt: {note}"
            total += len(entry)
            if total > DIGEST_TOTAL_CHARS:
                break
            parts.append(entry)
        return "\n".join(parts)


async def _run_search_web(query: str, index: _ResultIndex) -> str:
    try:
        result = await search_web(query, provider="parallel", timeout=SEARCH_TIMEOUT_SECONDS)
    except Exception as exc:
        return f"# search_web({query!r}) -> ERROR: {exc}"
    numbers = index.record(result.receipt_id, result.results, kind="search")
    lines = [f"# search_web({query!r}) -> {len(result.results)} results"]
    for n, r in zip(numbers, result.results, strict=False):
        lines.append(f"[{n}] {r.title or ''}\n  url: {r.url}\n  excerpt: {(r.note or '')[:500]}")
    return "\n".join(lines)


def _fetch_domain(url: str) -> str:
    try:
        from urllib.parse import urlsplit
        return (urlsplit(url).netloc or "").lower().removeprefix("www.")
    except Exception:
        return ""


class _FetchLedger:
    """Per-run fetch outcome memory so budget is not wasted re-attempting
    URLs and hosts that have already proven unfetchable."""

    def __init__(self) -> None:
        self.failed_urls: set[str] = set()
        self.domain_fail: dict[str, int] = {}
        self.domain_ok: dict[str, int] = {}

    def blocked_reason(self, url: str) -> str | None:
        if url in self.failed_urls:
            return (
                "this exact URL already failed this run. Do not request it again; "
                "answer from search snippets or a different source."
            )
        dom = _fetch_domain(url)
        if (
            self.domain_fail.get(dom, 0) >= FETCH_FAIL_DOMAIN_BUDGET
            and self.domain_ok.get(dom, 0) == 0
        ):
            return (
                f"{dom} has failed {self.domain_fail[dom]} times this run with no "
                "successes and is treated as unfetchable. Do not fetch this site "
                "again; answer from search snippets or an alternative source."
            )
        return None

    def note_ok(self, url: str) -> None:
        dom = _fetch_domain(url)
        self.domain_ok[dom] = self.domain_ok.get(dom, 0) + 1

    def note_fail(self, url: str) -> None:
        self.failed_urls.add(url)
        dom = _fetch_domain(url)
        self.domain_fail[dom] = self.domain_fail.get(dom, 0) + 1


async def _run_fetch_page(url: str, index: _ResultIndex, ledger: _FetchLedger) -> str:
    reason = ledger.blocked_reason(url)
    if reason is not None:
        return f"# fetch_page({url!r}) -> SKIPPED: {reason}"
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
        ledger.note_fail(url)
        return (
            f"# fetch_page({url!r}) -> ERROR: {last_exc}. The page may not exist or may "
            "block automated fetching. Do not retry this URL; if you constructed it "
            "yourself, search for the correct page instead of guessing another URL."
        )
    ledger.note_ok(url)
    numbers = index.record(result.receipt_id, result.results, kind="fetch")
    if not result.results:
        return f"# fetch_page({url!r}) -> no content"
    n = numbers[0]
    content = (result.results[0].note or "")[:6000]
    return f"# fetch_page({url!r}) -> [{n}] {len(content)} chars\n{content}"


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


def _anchor_tokens(claim: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z']{3,}|\d[\d,.%]*", claim)
    ordered = sorted(words, key=lambda w: (not any(c.isdigit() for c in w), -len(w)))
    tokens: list[str] = []
    for w in ordered:
        lw = w.lower().strip(".,%")
        if len(lw) >= 3 and lw not in tokens:
            tokens.append(lw)
        if len(tokens) >= 8:
            break
    return tokens


def _anchored_slice_bounds(note: str, claims: list[str], window: int) -> tuple[int, int]:
    src_len = len(note)
    if src_len <= window:
        return 0, src_len
    hay = note.lower()
    tokens: list[str] = []
    for claim in claims[:3]:
        tokens.extend(_anchor_tokens(claim))
    positions: list[int] = []
    for t in tokens:
        i = hay.find(t)
        while i != -1 and len(positions) < 400:
            positions.append(i)
            i = hay.find(t, i + 1)
    if not positions:
        return 0, window
    positions.sort()
    best_start, best_cnt = 0, 0
    for p in positions:
        start = max(0, min(p - CITATION_ANCHOR_LEAD_CHARS, src_len - window))
        end = start + window
        cnt = sum(1 for q in positions if start <= q <= end)
        if cnt > best_cnt:
            best_cnt, best_start = cnt, start
    return best_start, best_start + window


def _citations_from_inline_markers(answer_text: str, index: _ResultIndex) -> tuple[CitationRef, ...]:
    max_number = index.max_number()
    seen: set[int] = set()
    ordered: list[int] = []
    claims_by_number: dict[int, list[str]] = {}
    for match in BRACKET_RE.finditer(answer_text):
        claim = answer_text[max(0, match.start() - CITATION_ANCHOR_CONTEXT_CHARS):match.start()]
        for n in _numbers_from_bracket(match.group(1), max_number=max_number):
            claims_by_number.setdefault(n, []).append(claim)
            if n not in seen:
                seen.add(n)
                ordered.append(n)
    citations: list[CitationRef] = []
    budget = CITATION_BUDGET_CHARS
    slice_window = max(CITATION_SLICE_MIN_CHARS, CITATION_BUDGET_CHARS // max(len(ordered), 1))
    for n in ordered:
        meta = index.get(n)
        if meta is None or not meta.get("citable", True):
            continue
        src_len = int(meta.get("src_len") or 0)
        if src_len <= 0:
            continue
        start, end = _anchored_slice_bounds(meta["note"], claims_by_number.get(n, []), slice_window)
        if end - start < 100 and not (start == 0 and end == src_len):
            continue
        if end - start > budget:
            continue
        budget -= end - start
        citations.append(CitationRef(
            receipt_id=meta["receipt_id"], result_id=meta["result_id"],
            slices=[CitationSlice(start=start, end=end)],
        ))
    return tuple(citations)


async def _chat_turn(messages: list[dict[str, object]], *, deadline: float) -> LlmChatResult | None:
    for _attempt in range(MAX_RETRY_ATTEMPTS_PER_TURN):
        timeout = min(LLM_TURN_TIMEOUT_SECONDS, deadline - perf_counter())
        if timeout <= 0:
            return None
        try:
            return await llm_chat(
                provider=LLM_PROVIDER, model=MODEL, messages=messages,
                tools=TOOLS, tool_choice="auto", temperature=0.2,
                thinking=LlmThinkingConfig(enabled=True, effort="low"),
                timeout=timeout,
            )
        except Exception:
            continue
    return None


async def _synthesis_call(
    question: str, index: _ResultIndex, *, deadline: float, forced: bool = False,
) -> str | None:
    system = SYNTHESIS_SYSTEM_PROMPT + (FORCED_COMMIT_SUFFIX if forced else "")
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\nNumbered evidence excerpts gathered "
                f"during research:\n{index.digest()}"
            ),
        },
    ]
    for _attempt in range(MAX_RETRY_ATTEMPTS_PER_TURN):
        budget = deadline - perf_counter() - 2
        if budget <= 12:
            return None
        if _attempt == 0 and budget >= 70:
            timeout = budget - 28.0
            thinking = LlmThinkingConfig(enabled=True, effort="low")
        else:
            timeout = budget
            thinking = LlmThinkingConfig(enabled=False)
        try:
            result = await llm_chat(
                provider=LLM_PROVIDER, model=MODEL, messages=messages,
                temperature=0.2, thinking=thinking, timeout=timeout,
            )
        except Exception:
            continue
        text = (result.response.raw_text or "").strip()
        if text:
            return text
    return None


def _strip_tool_markup(text: str) -> str:
    return TOOL_MARKUP_RE.sub(" ", text).strip()


def _needs_forced_retry(text: str) -> bool:
    if TOOL_MARKUP_RE.search(text) is not None:
        return True
    if len(text) < HARD_MIN_ANSWER_CHARS:
        return True
    if len(text) < MIN_ANSWER_CHARS:
        head = text.lower()
        if any(m in head[:400] for m in ABSTENTION_MARKERS):
            return True
        if not text.rstrip().endswith((".", "!", "?", ")", "]", '"', "|", "*")):
            return True
    return False


def _dump_floor_answer(index: _ResultIndex) -> str | None:
    if index.max_number() == 0:
        return None
    parts = [
        "The final synthesis step could not run to completion; the gathered "
        "source-backed evidence supports the following points:",
    ]
    total = 0
    for n in range(1, index.max_number() + 1):
        meta = index.get(n)
        if meta is None:
            continue
        note = meta["note"][:260].strip()
        if not note:
            continue
        entry = f"[{n}] {note}"
        total += len(entry)
        if total > 2600:
            break
        parts.append(entry)
    if len(parts) == 1:
        return None
    return "\n".join(parts)


def _deliverable(text: str | None, index: _ResultIndex) -> Response:
    answer = (text or "").strip()
    if not answer:
        answer = _dump_floor_answer(index) or INSUFFICIENT_ANSWER
    citations = _citations_from_inline_markers(answer, index)
    return Response(text=answer, citations=list(citations) if citations else None)


@entrypoint("query")
async def query(query: Query) -> Response:
    deadline = perf_counter() + TASK_TOTAL_BUDGET_SECONDS
    tool_stop = deadline - SYNTH_RESERVE_SECONDS
    index = _ResultIndex()
    fetch_ledger = _FetchLedger()
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query.text},
    ]
    final_answer: str | None = None

    try:
        for _turn in range(1, MAX_TURNS + 1):
            if tool_stop - perf_counter() <= 5:
                break
            chat_result = await _chat_turn(messages, deadline=tool_stop)
            if chat_result is None:
                break
            choice_message = chat_result.response.choices[0].message
            tool_calls = choice_message.tool_calls or ()
            if not tool_calls:
                final_answer = (chat_result.response.raw_text or "").strip()
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
                elif tc.name == "fetch_page":
                    result_text = await _run_fetch_page(args.get("url", ""), index, fetch_ledger)
                else:
                    result_text = f"# unknown tool {tc.name!r}"
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})

        if not final_answer:
            final_answer = await _synthesis_call(query.text, index, deadline=deadline)

        if final_answer and _needs_forced_retry(final_answer):
            retry: str | None = None
            if deadline - perf_counter() >= SYNTH_RETRY_MIN_SECONDS:
                retry = await _synthesis_call(query.text, index, deadline=deadline, forced=True)
            if retry and not _needs_forced_retry(retry):
                final_answer = retry
            else:
                stripped = _strip_tool_markup(final_answer)
                if stripped and not _needs_forced_retry(stripped):
                    final_answer = stripped
                else:
                    final_answer = _dump_floor_answer(index) or stripped

        return _deliverable(_strip_tool_markup(final_answer) if final_answer else None, index)
    except Exception:
        return _deliverable(None, index)
# slot: 29 B5_fetch 2026-07-24T15:00:00+00:00
