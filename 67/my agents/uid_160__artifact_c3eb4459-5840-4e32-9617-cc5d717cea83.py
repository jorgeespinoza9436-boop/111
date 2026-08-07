"""SN67 Harnyx miner — autonomous tool-use research pipeline. [slot 10 build 2026-07-23T15:00:00+00:00]"""
from __future__ import annotations
import json
import re
import asyncio
from time import perf_counter
from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
LLM_PROVIDER = "openrouter"
MODEL = "z-ai/glm-5"
TASK_TOTAL_BUDGET_SECONDS = 270.0
DIGEST_TOTAL_CHARS = 18_000
FETCH_RETRY_ATTEMPTS = 2
FETCH_TIMEOUT_SECONDS = 15.0
MAX_TURNS = 16
MIN_ANSWER_CHARS = 400
SYNTH_RETRY_MIN_SECONDS = 25.0
SEARCH_TIMEOUT_SECONDS = 20.0
MAX_RETRY_ATTEMPTS_PER_TURN = 2
SYNTH_RESERVE_SECONDS = 80.0
LLM_TURN_TIMEOUT_SECONDS = 90.0
DIGEST_NOTE_CHARS = 400
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
    "You are a careful research assistant answering a factual multi-part question. "
    "You have search_web, search_many, and fetch_page tools. Call them as many times as needed to "
    "verify every sub-claim before answering -- do not guess ages, dates, or line "
    "counts from memory; look them up. Every tool result is numbered like [7] when "
    "shown to you.\n\n"
    "CITATION RULE: when you write your final answer, put the source number in "
    "brackets immediately after EVERY factual claim (a number, date, name, or "
    "yes/no determination) -- e.g. 'Keats died at age 25 [7]' or 'the total is "
    "4,000 [7, 12].' Cite a claim for entities that qualify AND entities that "
    "don't -- every stated fact needs its own citation, not just a summary source "
    "list at the end. A claim with no bracket after it is assumed uncited.\n\n"
    "When (and only when) you are confident in every fact, write your final answer "
    "with inline citations as described. Do not call a tool and answer in the same turn."

    "\n\n"
    "## Pairwise Scoring Rules\n\n"
    "- **Decompose** the question into every distinct sub-fact and filter; never answer from memory for dates, counts, rankings, or names.\n"
    "- **Full roster:** for which/list/superlative questions, enumerate the COMPLETE candidate pool, evaluate EVERY candidate, cite each qualifier, and show closest excluded item(s) with the cited value that fails.\n"
    "- **Literal comparators:** `more than 25` is strict >; ranges inclusive unless stated; convert rate conditions into concrete integer tests.\n"
    "- **False premise:** if the premise is false, say so in the first line and give the correct cited fact — never refuse or answer `evidence missing`.\n"
    "- **Exact values:** copy numbers/dates/names verbatim with units; never round.\n"
    "- **Commit:** a partial, cited answer scores far higher than a refusal. Cover every asked sub-question.\n"
    "- **Citations:** put `[n]` after every load-bearing claim (qualifiers AND exclusions); quality over quantity — no citation spam.\n"
    "- **Batch lookups:** use `search_many` (or several tool calls in one turn) for independent candidate/metric queries.\n"
)
SYNTHESIS_SYSTEM_PROMPT = (
    "You are a careful research assistant. The research phase for this question is "
    "over: tools are DISABLED, and any tool-call syntax you emit will be shipped "
    "verbatim to the grader as your final answer, scoring zero. Using ONLY the "
    "numbered evidence excerpts provided, write your best final answer now.\n\n"
    "COMMIT RULE: scoring is pairwise against a competitor's answer -- an answer "
    "that refuses or defers scores zero and loses outright. If some sub-claims are "
    "uncertain, commit to what the evidence supports and note the uncertainty "
    "inline; a partial, cited answer scores far better than no answer.\n\n"
    "CITATION RULE: put the evidence number in brackets immediately after every "
    "factual claim -- e.g. 'the total is 4,000 [7, 12].' A claim with no bracket "
    "after it is assumed uncited."

    "\n\n"
    "## Pairwise Scoring Rules\n\n"
    "- Cover every asked sub-question with cited values; cite exclusions as well as winners.\n"
    "- False premise: correct in the first line with a citation; never refuse.\n"
    "- Prefer partial cited answers over completeness-without-evidence.\n"
)
FORCED_COMMIT_SUFFIX = (
    "\n\n*** FORCED COMMIT ***\nYour previous draft refused, stalled, or was cut "
    "short. That scores ZERO. Rewrite now: commit to the best evidence-supported "
    "answer, cite every claim, and do not emit tool-call syntax or apologies."
    " Cite exclusions as well as winners. Every load-bearing number/date/name needs its own [n]."
)
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
    numbers = index.record(result.receipt_id, result.results, kind="fetch")
    if not result.results:
        return f"# fetch_page({url!r}) -> no content"
    n = numbers[0]
    content = (result.results[0].note or "")[:6000]
    return f"# fetch_page({url!r}) -> [{n}] {len(content)} chars\n{content}"
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
BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")

async def _run_search_many(queries: list, index: _ResultIndex) -> str:
    clean = [str(q).strip() for q in (queries or []) if str(q).strip()][:8]
    if not clean:
        return "# search_many() -> ERROR: no queries"
    parts = await asyncio.gather(*(_run_search_web(q, index) for q in clean))
    return f"# search_many({len(clean)} queries)\n" + "\n\n".join(parts)


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
def _strip_tool_markup(text: str) -> str:
    return TOOL_MARKUP_RE.sub(" ", text).strip()
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
                elif tc.name == "search_many":
                    qs = args.get("queries") or []
                    result_text = await _run_search_many(qs if isinstance(qs, list) else [qs], index)
                elif tc.name == "fetch_page":
                    result_text = await _run_fetch_page(args.get("url", ""), index)
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


        # Budget-gated pairwise coverage audit → optional tools-off rewrite
        if final_answer and (deadline - perf_counter()) > 40:
            try:
                audit = await llm_chat(
                    provider=LLM_PROVIDER,
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": "# Strict Answer Auditor\n\nOutput JSON only with keys missing_elements, uncited_claims, suspect_attributions (arrays)."},
                        {"role": "user", "content": f"Audit vs question. JSON only.\n\nQuestion:\n{query.text}\n\nAnswer:\n{final_answer[:12000]}"},
                    ],
                    tools=None,
                    temperature=0.1,
                    max_output_tokens=700,
                    thinking=LlmThinkingConfig(enabled=False),
                    timeout=min(25.0, max(5.0, deadline - perf_counter() - 8)),
                )
                raw = (audit.response.raw_text or "").strip()
                cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I | re.M).strip()
                report = json.loads(cleaned)
                issues = []
                for key in ("missing_elements", "uncited_claims", "suspect_attributions"):
                    vals = report.get(key) if isinstance(report, dict) else None
                    if isinstance(vals, list):
                        issues.extend(str(v) for v in vals if str(v).strip())
                if issues and (deadline - perf_counter()) > 20:
                    patched = await _synthesis_call(
                        query.text + "\n\nAUDIT GAPS:\n- " + "\n- ".join(issues[:6])
                        + "\n\nRewrite the COMPLETE final answer with inline [n] citations including exclusions.",
                        index,
                        deadline=deadline,
                        forced=True,
                    )
                    if patched and not _needs_forced_retry(patched):
                        final_answer = patched
            except Exception:
                pass


        return _deliverable(_strip_tool_markup(final_answer) if final_answer else None, index)
    except Exception:
        return _deliverable(None, index)
_TAG="800ff8a8fde74f44b2ae759fe1d0baf1"
import logging as _tag_logging
_tag_logging.getLogger("miner.tag").debug("tag=%s", _TAG)
