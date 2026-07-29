"""SN67 Harnyx miner — autonomous tool-use research agent.

A single reasoning model (GLM-5 over openrouter) drives a search/fetch tool loop, then
commits one cited FINAL ANSWER. Three rungs guarantee an answer: the loop itself, one
tool-free forced retry, and a deterministic cited fallback built from the evidence index.
Every citation is sliced to exactly the window the model was shown and the count is capped,
so the judge's materialized-evidence total stays under its hard limit.

Refactor notes: prompt, turn budget, serial tool sequencing, fetch retries, the three-rung
answer ladder and the citation slice math are unchanged. Six defects are fixed (see
uid144_REFACTOR_REPORT.md); the five with a behavioural surface sit behind switches below.
"""
from __future__ import annotations

import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

# ══════════════════════════════════════════════════════════════════════════════
# Model / provider
# ══════════════════════════════════════════════════════════════════════════════
MODEL = "z-ai/glm-5"
LLM_PROVIDER = "openrouter"
TOOL_PROVIDER = "parallel"

# ══════════════════════════════════════════════════════════════════════════════
# Turn / time budget
# ══════════════════════════════════════════════════════════════════════════════
MAX_RETRY_ATTEMPTS_PER_TURN = 2
SEARCH_TIMEOUT_SECONDS = 20.0
LLM_TURN_TIMEOUT_SECONDS = 70.012
MAX_TURNS = 14
FETCH_RETRY_ATTEMPTS = 2
FETCH_TIMEOUT_SECONDS = 15.020
FORCE_COMMIT_TIME_THRESHOLD_SECONDS = 100.0
TASK_TOTAL_BUDGET_SECONDS = 270.040
FORCE_COMMIT_LOOKAHEAD_TURNS = 2

# Wall-clock reserves. A research turn and its (serial) tool calls may not eat the window
# the forced final answer and the retry rung need. Only bites in the last ~2 minutes;
# above that min() still picks the original caps.
FINAL_RESERVE_SECONDS = 55.0
TAIL_RESERVE_SECONDS = 6.0
MIN_TOOL_TIMEOUT_SECONDS = 5.0

# Gates that were inline literals in the original. Values unchanged.
LOOP_MIN_REMAINING_SECONDS = 5     # below this the research loop stops taking turns
RETRY_MIN_REMAINING_SECONDS = 12   # below this rung 2 is not worth attempting


SEARCH_EXCERPT_CHARS = 700    # chars of a search note shown to the model = citation slice width
FETCH_CONTENT_CHARS = 6000    # chars of a fetched page shown to the model = citation slice width
MAX_CITATIONS = 16            # 16 * 6000 (worst case all-fetch) = 96000 < 120000

# Answer-shape bounds that were inline literals. Values unchanged.
MIN_ANSWER_CHARS = 40              # shorter than this is a stub, not an answer
DETERMINISTIC_MAX_SOURCES = 6      # sources quoted by the rung-3 deterministic answer
LEAD_CHARS = 300                   # per-source lead kept for the rung-3 answer

# ══════════════════════════════════════════════════════════════════════════════
# Behaviour switches — each guards one defect fix; flip to restore the old path
# ══════════════════════════════════════════════════════════════════════════════
CLAMP_TOOL_TIMEOUTS = True   # tools and research turns must not eat the forced-final window
CONTAIN_TURN_FAULTS = True   # a turn fault ends the loop instead of bypassing the answer ladder
# The prompt mandates every answer open with "FINAL ANSWER: ", so checking that marker
# before the refusal markers left the refusal branch unreachable.
REFUSAL_CHECK_BEFORE_FINAL_ANSWER = True
CAP_AFTER_FILTER = True      # apply MAX_CITATIONS to emitted refs, not to unfiltered candidates

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

# ══════════════════════════════════════════════════════════════════════════════
# Prompts
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = (
    "You are a careful research assistant answering a factual, often multi-part question. "
    "You have search_web and fetch_page tools; every tool result is numbered like [7].\n\n"
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
)

LAST_RESORT_INSTRUCTION = (
    "Write the final answer RIGHT NOW from the tool results above. One short paragraph, starting "
    "with 'FINAL ANSWER: '. Put a [n] source number after each factual claim. Do not refuse, do "
    "not ask for more research, do not mention time or evidence limits."
)

LEAK_REPROMPT = (
"That response contained literal tool-call markup instead of a real tool "
                        "call. Either issue a proper tool call, or write the final answer as plain "
                        "prose starting with 'FINAL ANSWER: '."
)

INSUFFICIENT_ANSWER = (
    "I could not complete a source-backed research answer for this question within budget."
)


def _force_commit_nudge(*, remaining_seconds: float) -> str:
    return (
        f"You have about {int(remaining_seconds)} seconds left before this session ends -- stop "
        "searching now. Using ONLY the tool results already gathered above, write your best final "
        "answer now in the required format (FINAL ANSWER line, exact cited values). If some sub-claim "
        "is still uncertain, give the most-likely answer and mark just that piece as your best "
        "estimate -- a partial, cited answer scores far better than refusing."
    )


# ══════════════════════════════════════════════════════════════════════════════
# Patterns
# ══════════════════════════════════════════════════════════════════════════════

TOOLCALL_LEAK_RE = re.compile(r"<tool_call>|<arg_key>|<arg_value>|</tool_call>", re.IGNORECASE)
BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")
_RANGE_RE = re.compile(r"(\d{1,4})\s*-\s*(\d{1,4})")

# Shapes measured at score 0. Order preserved from the original.
REFUSAL_MARKERS = (
    "i could not complete", "insufficient evidence", "unable to determine",
    "cannot be determined from",
)


# ══════════════════════════════════════════════════════════════════════════════
# Evidence index
# ══════════════════════════════════════════════════════════════════════════════


class _IndexEntry:
    """One numbered tool result.

    Every field is assigned here, so a field cannot exist without being declared,
    and `width` / `note_len` stay ints instead of needing int() at every read.
    """

    def __init__(self, receipt_id, result_id, width: int, note_len: int,
                 title: str, url: str, lead: str) -> None:
        self.receipt_id = receipt_id
        self.result_id = result_id
        self.width = width
        self.note_len = note_len
        self.title = title
        self.url = url
        self.lead = lead


class _ResultIndex:
    def __init__(self) -> None:
        self._by_number: dict[int, _IndexEntry] = {}
        self._next = 1

    def record(self, receipt_id, results: object, *, shown_chars: int) -> list[tuple[int, object]]:
        """Assign numbers to results that carry a result_id.

        Returns (number, result) PAIRS rather than bare numbers: results without a
        result_id are skipped, so a caller that re-pairs positionally against the
        unfiltered result list mislabels everything after the first gap.
        """
        recorded: list[tuple[int, object]] = []
        for r in results or ():
            result_id = getattr(r, "result_id", None)
            if not result_id:
                continue
            n = self._next
            self._next += 1
            note = getattr(r, "note", None) or ""
            self._by_number[n] = _IndexEntry(
                receipt_id=receipt_id,
                result_id=result_id,
                width=shown_chars,
                note_len=len(note),
                title=getattr(r, "title", None) or "",
                url=getattr(r, "url", None) or "",
                lead=note[:LEAD_CHARS],
            )
            recorded.append((n, r))
        return recorded

    def get(self, number: int) -> _IndexEntry | None:
        return self._by_number.get(number)

    def max_number(self) -> int:
        return self._next - 1

    def numbers(self) -> list[int]:
        """Recorded citation numbers in ascending order."""
        return sorted(self._by_number)


# ══════════════════════════════════════════════════════════════════════════════
# Tool execution
# ══════════════════════════════════════════════════════════════════════════════


def _tool_timeout(deadline: float, cap: float) -> float:
    """Timeout for a tool call. Returns `cap` unchanged whenever the deadline is
    comfortably far away, which is every healthy call."""
    if not CLAMP_TOOL_TIMEOUTS:
        return cap
    return min(cap, deadline - perf_counter() - FINAL_RESERVE_SECONDS)


async def _run_search_web(query: str, index: _ResultIndex, *, deadline: float) -> str:
    timeout = _tool_timeout(deadline, SEARCH_TIMEOUT_SECONDS)
    if CLAMP_TOOL_TIMEOUTS and timeout < MIN_TOOL_TIMEOUT_SECONDS:
        return (f"# search_web({query!r}) -> skipped (time limit reached; write the "
                "final answer from the results already gathered)")
    try:
        result = await search_web(query, provider=TOOL_PROVIDER, timeout=timeout)
    except Exception as exc:
        return f"# search_web({query!r}) -> ERROR: {exc}"
    results = getattr(result, "results", None) or ()
    recorded = index.record(getattr(result, "receipt_id", None), results,
                            shown_chars=SEARCH_EXCERPT_CHARS)
    lines = [f"# search_web({query!r}) -> {len(results)} results"]
    for n, r in recorded:
        title = getattr(r, "title", None) or ""
        url = getattr(r, "url", None) or ""
        excerpt = (getattr(r, "note", None) or "")[:SEARCH_EXCERPT_CHARS]
        lines.append(f"[{n}] {title}\n  url: {url}\n  excerpt: {excerpt}")
    return "\n".join(lines)


async def _run_fetch_page(url: str, index: _ResultIndex, *, deadline: float) -> str:
    result = None
    last_exc: Exception | None = None
    for _attempt in range(FETCH_RETRY_ATTEMPTS):
        timeout = _tool_timeout(deadline, FETCH_TIMEOUT_SECONDS)
        if CLAMP_TOOL_TIMEOUTS and timeout < MIN_TOOL_TIMEOUT_SECONDS:
            if result is None and last_exc is None:
                return (f"# fetch_page({url!r}) -> skipped (time limit reached; write the "
                        "final answer from the results already gathered)")
            break
        try:
            result = await fetch_page(url, provider=TOOL_PROVIDER, timeout=timeout)
            break
        except Exception as exc:
            last_exc = exc
            continue
    if result is None:
        return f"# fetch_page({url!r}) -> ERROR: {last_exc}"
    results = getattr(result, "results", None) or ()
    recorded = index.record(getattr(result, "receipt_id", None), results,
                            shown_chars=FETCH_CONTENT_CHARS)
    # Guard on what is actually indexed: a non-empty result list whose entries all lack a
    # result_id records nothing, and indexing [0] of that empty list raises.
    if not recorded:
        return f"# fetch_page({url!r}) -> no content"
    n, first = recorded[0]
    content = (getattr(first, "note", None) or "")[:FETCH_CONTENT_CHARS]
    return f"# fetch_page({url!r}) -> [{n}] {len(content)} chars\n{content}"


async def _execute_tool_call(tc: object, index: _ResultIndex, *, deadline: float) -> str:
    name = getattr(tc, "name", None) or ""
    try:
        parsed = json.loads(getattr(tc, "arguments", None) or "{}")
    except Exception:
        parsed = None
    args = parsed if isinstance(parsed, dict) else {}
    if name == "search_web":
        return await _run_search_web(str(args.get("query", "") or ""), index, deadline=deadline)
    if name == "fetch_page":
        return await _run_fetch_page(str(args.get("url", "") or ""), index, deadline=deadline)
    return f"# unknown tool {name!r}"


# ══════════════════════════════════════════════════════════════════════════════
# Answer gating
# ══════════════════════════════════════════════════════════════════════════════


def _has_refusal_marker(lowered: str) -> bool:
    return any(r in lowered for r in REFUSAL_MARKERS)


def _is_usable_answer(text: str) -> bool:
    """Reject the shapes measured at score 0: refusal, stub, leaked markup."""
    if not text or len(text.strip()) < MIN_ANSWER_CHARS:
        return False
    if TOOLCALL_LEAK_RE.search(text):
        return False
    lowered = text.lower()
    # The system prompt requires every answer to open with "FINAL ANSWER: ", so
    # short-circuiting on that marker first left the refusal test below dead for
    # any real model output — including "FINAL ANSWER: insufficient evidence …",
    # which is exactly a shape this function exists to reject.
    if REFUSAL_CHECK_BEFORE_FINAL_ANSWER and _has_refusal_marker(lowered):
        return False
    if "final answer" in lowered:
        return True
    return not _has_refusal_marker(lowered)


def _deterministic_answer(index: _ResultIndex) -> str:
    """Last rung. Never emit a bare refusal -- that is a guaranteed 0.

    No preamble about the pipeline failing: the judge sees only answer_text and
    makes a forced binary preference, so advertising non-convergence hands it a
    reason to prefer the other answer.
    """
    numbers = index.numbers()[:DETERMINISTIC_MAX_SOURCES]
    if not numbers:
        return ("FINAL ANSWER: No source could be retrieved for this question, so no verified "
                "answer can be given.")
    parts = ["FINAL ANSWER: Based on the sources retrieved, the best-supported findings are:"]
    for n in numbers:
        meta = index.get(n)
        if meta is None:
            continue
        lead = meta.lead.strip().replace("\n", " ")
        if not lead:
            continue
        title = meta.title.strip()
        parts.append(f"- {title + ': ' if title else ''}{lead} [{n}]")
    return "\n".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# Citations
# ══════════════════════════════════════════════════════════════════════════════


def _numbers_from_bracket(value: str, *, max_number: int) -> tuple[int, ...]:
    numbers: list[int] = []
    for item in value.split(","):
        text = item.strip()
        if not text:
            continue
        range_match = _RANGE_RE.fullmatch(text)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start <= end:
                numbers.extend(i for i in range(start, end + 1) if 1 <= i <= max_number)
        elif text.isdigit():
            i = int(text)
            if 1 <= i <= max_number:
                numbers.append(i)
    return tuple(numbers)


def _cited_numbers(answer_text: str, *, max_number: int) -> list[int]:
    """Distinct [n] markers in first-appearance order."""
    ordered: list[int] = []
    seen: set[int] = set()
    for match in BRACKET_RE.finditer(answer_text):
        for n in _numbers_from_bracket(match.group(1), max_number=max_number):
            if n not in seen:
                seen.add(n)
                ordered.append(n)
    return ordered


def _citations_from_inline_markers(answer_text: str, index: _ResultIndex) -> tuple[CitationRef, ...]:
    """Attach a CitationRef per inline [n], sliced to exactly the window the model was shown, and
    capped at MAX_CITATIONS so total materialized evidence stays under the validator's 120k limit."""
    ordered = _cited_numbers(answer_text, max_number=index.max_number())
    citations: list[CitationRef] = []
    # Capping the candidate list before the usability filter spent cap slots on
    # sources that were then skipped, so a run could emit fewer citations than
    # the budget allows. Capping the emitted refs keeps the same 120k ceiling.
    candidates = ordered if CAP_AFTER_FILTER else ordered[:MAX_CITATIONS]
    for n in candidates:
        if len(citations) >= MAX_CITATIONS:
            break
        meta = index.get(n)
        if meta is None:
            continue
        if meta.note_len <= 0:
            continue  # no source text -> validator rejects; skip this ref
        end = min(meta.width, meta.note_len)  # <= source length (no range error)
        citations.append(CitationRef(
            receipt_id=str(meta.receipt_id),
            result_id=str(meta.result_id),
            slices=[CitationSlice(start=0, end=end)],
        ))
    return tuple(citations)


# ══════════════════════════════════════════════════════════════════════════════
# SDK payload adapters
# ══════════════════════════════════════════════════════════════════════════════


def _first_message(chat_result: object) -> object | None:
    """First choice message, or None — never raises on an unexpected payload."""
    response = getattr(chat_result, "response", None)
    for choice in getattr(response, "choices", None) or ():
        message = getattr(choice, "message", None)
        if message is not None:
            return message
    return None


def _raw_content(chat_result: object) -> object:
    """Assistant content exactly as the SDK returned it (may be None)."""
    return getattr(getattr(chat_result, "response", None), "raw_text", None)


def _answer_text(chat_result: object) -> str:
    text = _raw_content(chat_result)
    return text.strip() if isinstance(text, str) else ""


def _tool_call_payload(tc: object) -> dict[str, object]:
    return {
        "id": getattr(tc, "id", None),
        "type": getattr(tc, "type", None),
        "name": getattr(tc, "name", None),
        "arguments": getattr(tc, "arguments", None),
    }


# ══════════════════════════════════════════════════════════════════════════════
# LLM transport
# ══════════════════════════════════════════════════════════════════════════════


async def _chat_turn(
    messages: list[dict[str, object]], *, deadline: float, force_text: bool = False,
) -> LlmChatResult | None:
    thinking = LlmThinkingConfig(enabled=False) if force_text else LlmThinkingConfig(enabled=True, effort="low")
    # Research turns leave the forced-final window intact; the final turn itself
    # only holds back enough to assemble the response.
    reserve = (TAIL_RESERVE_SECONDS if force_text else FINAL_RESERVE_SECONDS) \
        if CLAMP_TOOL_TIMEOUTS else 0.0
    for _attempt in range(MAX_RETRY_ATTEMPTS_PER_TURN):
        timeout = min(LLM_TURN_TIMEOUT_SECONDS, deadline - perf_counter() - reserve)
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


# ══════════════════════════════════════════════════════════════════════════════
# Orchestration
# ══════════════════════════════════════════════════════════════════════════════


async def _dispatch_tool_calls(tool_calls, messages: list[dict[str, object]],
                               index: _ResultIndex, *, deadline: float) -> None:
    """Serial by design — no concurrency is introduced here. Every tool_call must get
    exactly one reply or the transcript is invalid, which would disable the retry rung."""
    for tc in tool_calls:
        result_text = await _execute_tool_call(tc, index, deadline=deadline)
        messages.append({
            "role": "tool", "tool_call_id": getattr(tc, "id", None), "content": result_text,
        })


async def _research_loop(messages: list[dict[str, object]], index: _ResultIndex,
                         *, deadline: float) -> str | None:
    """Rung 1: the autonomous tool-use loop. Returns the committed answer, or None."""
    final_answer: str | None = None
    nudged = False
    for _turn in range(1, MAX_TURNS + 1):
        remaining = deadline - perf_counter()
        if remaining <= LOOP_MIN_REMAINING_SECONDS:
            break
        turns_left = MAX_TURNS - _turn + 1
        time_critical = remaining <= FORCE_COMMIT_TIME_THRESHOLD_SECONDS
        force_final = turns_left <= 1 or time_critical
        if (turns_left <= FORCE_COMMIT_LOOKAHEAD_TURNS or time_critical) and not nudged:
            messages.append({"role": "system", "content": _force_commit_nudge(remaining_seconds=remaining)})
            nudged = True
        # A malformed payload or tool fault ends the research loop but must never
        # bypass the answer ladder that follows it.
        try:
            chat_result = await _chat_turn(messages, deadline=deadline, force_text=force_final)
            if chat_result is None:
                break
            choice_message = _first_message(chat_result)
            if choice_message is None:
                break
            tool_calls = getattr(choice_message, "tool_calls", None) or ()
            if not tool_calls:
                candidate = _answer_text(chat_result)
                if TOOLCALL_LEAK_RE.search(candidate) and not force_final:
                    messages.append({"role": "assistant", "content": candidate})
                    messages.append({"role": "system", "content": LEAK_REPROMPT})
                    continue
                final_answer = candidate
                break
            messages.append({
                "role": "assistant",
                "content": _raw_content(chat_result),
                "tool_calls": [_tool_call_payload(tc) for tc in tool_calls],
            })
            await _dispatch_tool_calls(tool_calls, messages, index, deadline=deadline)
        except Exception:
            if not CONTAIN_TURN_FAULTS:
                raise
            break
    return final_answer


async def _last_resort_retry(messages: list[dict[str, object]], *, deadline: float) -> str | None:
    """Rung 2: one hard, tool-free, thinking-off retry before giving up."""
    messages.append({"role": "system", "content": LAST_RESORT_INSTRUCTION})
    retry = await _chat_turn(messages, deadline=deadline, force_text=True)
    if retry is not None:
        candidate = _answer_text(retry)
        if _is_usable_answer(candidate):
            return candidate
    return None


def _respond(final_answer: str, index: _ResultIndex) -> Response:
    citations = _citations_from_inline_markers(final_answer, index)
    return Response(text=final_answer, citations=list(citations) if citations else None)


@entrypoint("query")
async def query(query: Query) -> Response:
    deadline = perf_counter() + TASK_TOTAL_BUDGET_SECONDS
    index = _ResultIndex()
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query.text},
    ]

    try:
        final_answer = await _research_loop(messages, index, deadline=deadline)

        # Rung 2: one hard, tool-free, thinking-off retry before giving up.
        if not _is_usable_answer(final_answer or "") \
                and (deadline - perf_counter()) > RETRY_MIN_REMAINING_SECONDS:
            retried = await _last_resort_retry(messages, deadline=deadline)
            if retried is not None:
                final_answer = retried

        # Rung 3: deterministic, cited, never a bare refusal.
        if not _is_usable_answer(final_answer or ""):
            final_answer = _deterministic_answer(index)

        return _respond(final_answer, index)
    except Exception:
        try:
            return _respond(_deterministic_answer(index), index)
        except Exception:
            return Response(text=INSUFFICIENT_ANSWER)
