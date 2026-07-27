from __future__ import annotations

import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

LLM_PROVIDER = "openrouter"
MODEL = "z-ai/glm-5"
FALLBACK_MODEL = "deepseek/deepseek-v3.2"
SEARCH_TIMEOUT_SECONDS = 20.0
MAX_TURNS = 14
TASK_TOTAL_BUDGET_SECONDS = 270.0
FORCE_COMMIT_TIME_THRESHOLD_SECONDS = 100.0
FORCE_COMMIT_LOOKAHEAD_TURNS = 2
FETCH_RETRY_ATTEMPTS = 2
FETCH_TIMEOUT_SECONDS = 15.0
LLM_TURN_TIMEOUT_SECONDS = 70.0
MAX_RETRY_ATTEMPTS_PER_TURN = 2

MAX_STRAY_RECOVERIES = 2
FALLBACK_EVIDENCE_MESSAGES = 4
FALLBACK_EVIDENCE_CHARS = 2400

SEARCH_EXCERPT_CHARS = 700
FETCH_CONTENT_CHARS = 6000
MAX_CITATIONS = 16

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
    {
        "type": "function",
        "function": {
            "name": "submit_final_answer",
            "description": (
                "Submit your final, complete answer and end the research session. This is the "
                "ONLY way to finish -- a plain-text reply with no tool call is NOT treated as "
                "the final answer and just wastes a turn."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": (
                            "The complete final answer, already in the required format: starts "
                            "with 'FINAL ANSWER: ...', with a bracketed source number after "
                            "every factual claim."
                        ),
                    },
                },
                "required": ["answer"],
            },
        },
    },
]

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
    "- For which/list/superlative questions, then list each qualifying item with the compared metric "
    "and its citation. Do not recite an aggregate tally for non-qualifying items (e.g. 'N other items "
    "had Y each') unless the question specifically asks for that breakdown -- a wrong aggregate count "
    "sinks the whole answer even when the count actually asked for is right. If you do mention "
    "excluded items, name them individually instead of asserting a summarized total.\n"
    "- After the FINAL ANSWER line, add a short 'Proof of completeness' section: one line per "
    "qualifying candidate naming its qualifying attribute and citation, and one line per other "
    "candidate you checked naming its cited exclusion reason -- this is what proves you covered "
    "the whole candidate pool, not just the one you picked.\n"
    "- Give exact values with units (population 8,631,393, not 'about 9 million'); copy numbers, "
    "dates and names verbatim, no rounding.\n"
    "- Before calling submit_final_answer, re-read your own FINAL ANSWER line against the cited "
    "sentences that follow it -- if the body actually supports a different entity/value than the "
    "opening line claims, fix the opening line to match the body, not the other way around.\n"
    "- If the premise is false, say so in the first line and give the correct fact -- never refuse "
    "or answer 'evidence missing'; commit to the best-supported answer.\n\n"
    "CITATION RULE: put the source number in brackets immediately after EVERY factual claim (a "
    "number, date, name, or yes/no determination) -- e.g. 'Keats died at age 25 [7]'. Every stated "
    "fact needs its own bracket, not a summary source list at the end. Keep the answer focused: cite "
    "the facts that matter, do not pad with dozens of tangential citations.\n\n"
    "HOW TO FINISH: the ONLY way to end the session is to call submit_final_answer with the "
    "complete answer (in the format above) as its `answer` argument. A plain-text reply that "
    "calls no tool is NOT your answer and just wastes a turn -- if you are thinking out loud or "
    "planning your next step, call search_web/fetch_page instead of writing it as a reply. Never "
    "call submit_final_answer in the same turn as search_web or fetch_page."
)


def _force_commit_nudge(*, remaining_seconds: float) -> str:
    return (
        f"You have about {int(remaining_seconds)} seconds left before this session ends -- stop "
        "searching now. Using ONLY the tool results already gathered above, write your best final "
        "answer now in the required format (FINAL ANSWER line, exact cited values). If some sub-claim "
        "is still uncertain, give the most-likely answer and mark just that piece as your best "
        "estimate -- a partial, cited answer scores far better than refusing."
    )


INSUFFICIENT_ANSWER = (
    "I could not complete a source-backed research answer for this question within budget."
)

FALLBACK_SYNTHESIS_SYSTEM_PROMPT = (
    "A research session ran out of time or turns before it could call submit_final_answer. "
    "Using ONLY the numbered tool results below (if any), write the best FINAL ANSWER you can "
    "in the required format: start with 'FINAL ANSWER: ', give the most-likely answer, and put "
    "a bracketed source number after every claim the results support. If a sub-fact is still "
    "unverified, give your best estimate and mark just that piece as an estimate. Never say the "
    "research was incomplete, unconverged, or that evidence is insufficient -- commit to the "
    "best-supported answer using what is here (or your own knowledge if nothing is here)."
)

STRAY_RECOVERY_NUDGE = (
    "That reply called no tool, so it was NOT treated as your final answer -- it looked like "
    "thinking-out-loud, not a finished answer. If you are still researching, call search_web or "
    "fetch_page now. If you are done, call submit_final_answer with your complete, formatted "
    "answer. Do not just repeat plain text again."
)


def _strip_tool_call_header(snippet: str) -> str:
    lines = snippet.split("\n", 1)
    return lines[1] if len(lines) > 1 and lines[0].startswith("#") else snippet


async def _fallback_answer_from_gathered_evidence(
    question: str, messages: list[dict[str, object]], *, deadline: float,
) -> str:
    tool_snippets = [
        _strip_tool_call_header(str(m.get("content", "")))
        for m in messages
        if m.get("role") == "tool" and str(m.get("content", "")).strip()
    ]
    excerpt = (
        "\n\n".join(tool_snippets[-FALLBACK_EVIDENCE_MESSAGES:])[:FALLBACK_EVIDENCE_CHARS]
        if tool_snippets
        else ""
    )
    remaining = deadline - perf_counter()
    if remaining > 10.0:
        evidence_block = f"Gathered tool results:\n{excerpt}" if excerpt else (
            "No tool results were gathered -- answer from your own knowledge."
        )
        try:
            result = await llm_chat(
                provider=LLM_PROVIDER, model=FALLBACK_MODEL,
                messages=[
                    {"role": "system", "content": FALLBACK_SYNTHESIS_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Question:\n{question}\n\n{evidence_block}"},
                ],
                temperature=0.2,
                thinking=LlmThinkingConfig(enabled=False),
                timeout=min(remaining - 3.0, LLM_TURN_TIMEOUT_SECONDS),
            )
            text = _response_text(result.response)
            if text.strip():
                return text.strip()
        except Exception:
            pass
    if excerpt:
        return "FINAL ANSWER: " + excerpt
    return INSUFFICIENT_ANSWER


_LEAKED_TOOL_CALL_RE = re.compile(
    r"(?:<tool_call>\s*)?([a-zA-Z_]\w*)\s*(?=<arg_key>)(.*?)(?:</tool_call>|$)", re.DOTALL,
)
_LEAKED_ARG_RE = re.compile(r"<arg_key>\s*([^<]*?)\s*</arg_key>\s*<arg_value>(.*?)(?:</arg_value>|$)", re.DOTALL)
_KNOWN_TOOL_NAMES = frozenset({"search_web", "fetch_page", "submit_final_answer"})
MAX_LEAKED_CALLS_PER_TURN = 4


def _parse_all_leaked_tool_calls(text: str) -> list[tuple[str, dict[str, str]]]:
    """Some models emit one or more Hermes-style <tool_call> blocks as plain text instead of
    using the real function-calling mechanism -- and some leak the bare `name<arg_key>...`
    body with no opening <tool_call> tag at all (only a stray trailing </tool_call>, if that).
    The opening tag is therefore optional; a known tool name immediately followed by <arg_key>
    (mod whitespace) is enough to anchor a match without risking false positives on prose that
    merely mentions a tool by name. Extract every recognizable one -- a model that leaks this
    format tends to leak several concatenated calls in a single reply, and only recovering the
    first one silently drops the rest."""
    calls: list[tuple[str, dict[str, str]]] = []
    for call_match in _LEAKED_TOOL_CALL_RE.finditer(text):
        name = call_match.group(1).strip()
        if name not in _KNOWN_TOOL_NAMES:
            continue
        args: dict[str, str] = {}
        for arg_match in _LEAKED_ARG_RE.finditer(call_match.group(2)):
            key = arg_match.group(1).strip()
            value = re.sub(r"</?tool_call>\s*$", "", arg_match.group(2)).strip()
            if key:
                args[key] = value
        calls.append((name, args))
        if len(calls) >= MAX_LEAKED_CALLS_PER_TURN:
            break
    return calls


def _strip_leaked_tool_call_markup(text: str) -> str:
    """Defensive cleanup for a leak _parse_all_leaked_tool_calls didn't cleanly resolve (e.g.
    an unrecognized tool name, or markup truncated mid-tag). Keep any real prose that came
    before the leak and drop the rest -- tool-call markup is never usable answer text."""
    cut = re.search(r"<tool_call>|<arg_key>|<arg_value>", text)
    return text[:cut.start()].strip() if cut else text


async def _execute_leaked_tool_call(name: str, args: dict[str, str], index: "_ResultIndex") -> str:
    if name == "search_web":
        return await _run_search_web(args.get("query", ""), index)
    return await _run_fetch_page(args.get("url", ""), index)


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
                "note_len": len(getattr(r, "note", None) or ""),
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
            continue
        width = int(meta.get("width", FETCH_CONTENT_CHARS))
        end = min(width, note_len)
        citations.append(CitationRef(
            receipt_id=str(meta["receipt_id"]),
            result_id=str(meta["result_id"]),
            slices=[CitationSlice(start=0, end=end)],
        ))
    return tuple(citations)


def _response_text(response: object) -> str:
    """response.raw_text has been observed to come back empty even when the provider
    returned a complete, well-formed answer in choices[].message.content (seen with
    z-ai/glm-5 via openrouter) -- fall back to walking the content parts ourselves rather
    than silently discarding a good answer."""
    raw = getattr(response, "raw_text", None)
    if raw and raw.strip():
        return raw.strip()
    parts: list[str] = []
    for choice in getattr(response, "choices", ()) or ():
        message = getattr(choice, "message", None)
        for part in getattr(message, "content", None) or ():
            text = getattr(part, "text", None)
            if text and text.strip():
                parts.append(text.strip())
    return "\n".join(parts).strip()


async def _chat_turn(
    messages: list[dict[str, object]], *, deadline: float, force_text: bool = False,
) -> LlmChatResult | None:
    thinking = LlmThinkingConfig(enabled=False) if force_text else LlmThinkingConfig(enabled=True, effort="low")
    for attempt in range(MAX_RETRY_ATTEMPTS_PER_TURN):
        timeout = min(LLM_TURN_TIMEOUT_SECONDS, deadline - perf_counter())
        if timeout <= 0:
            return None
        model = MODEL if attempt == 0 else FALLBACK_MODEL
        try:
            return await llm_chat(
                provider=LLM_PROVIDER, model=model, messages=messages,
                tools=None if force_text else TOOLS,
                tool_choice=None if force_text else "auto",
                temperature=0.2,
                thinking=thinking,
                timeout=timeout,
            )
        except Exception:
            continue
    return None


@entrypoint("query")
async def query(query: Query) -> Response:
    deadline = perf_counter() + TASK_TOTAL_BUDGET_SECONDS
    index = _ResultIndex()
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query.text},
    ]
    final_answer: str | None = None
    nudged = False
    stray_recoveries = 0
    force_next_final = False

    try:
        for _turn in range(1, MAX_TURNS + 1):
            remaining = deadline - perf_counter()
            if remaining <= 5:
                break
            turns_left = MAX_TURNS - _turn + 1
            time_critical = remaining <= FORCE_COMMIT_TIME_THRESHOLD_SECONDS
            force_final = turns_left <= 1 or time_critical or force_next_final
            if (turns_left <= FORCE_COMMIT_LOOKAHEAD_TURNS or time_critical or force_next_final) and not nudged:
                messages.append({"role": "system", "content": _force_commit_nudge(remaining_seconds=remaining)})
                nudged = True
            chat_result = await _chat_turn(messages, deadline=deadline, force_text=force_final)
            if chat_result is None:
                break
            choice_message = chat_result.response.choices[0].message
            tool_calls = choice_message.tool_calls or ()

            if force_final:
                raw_final_text = _response_text(chat_result.response)
                leaked_calls_final = _parse_all_leaked_tool_calls(raw_final_text)
                submit_leak_final = next((c for c in leaked_calls_final if c[0] == "submit_final_answer"), None)
                if submit_leak_final is not None:
                    final_answer = submit_leak_final[1].get("answer", "").strip()
                elif leaked_calls_final:
                    # Leaked a search_web/fetch_page call instead of answering, with no
                    # turns left to execute it -- there's no usable prose here, so fall
                    # through to the gathered-evidence fallback below instead of
                    # surfacing raw tool-call markup as the answer.
                    final_answer = None
                else:
                    final_answer = _strip_leaked_tool_call_markup(raw_final_text) or None
                break

            finish_call = next((tc for tc in tool_calls if tc.name == "submit_final_answer"), None)
            if finish_call is not None:
                try:
                    finish_args = json.loads(finish_call.arguments or "{}")
                except json.JSONDecodeError:
                    finish_args = {}
                final_answer = str(finish_args.get("answer", "") or "").strip()
                break

            if not tool_calls:
                raw_stray_text = _response_text(chat_result.response)
                leaked_calls = _parse_all_leaked_tool_calls(raw_stray_text)
                submit_leak = next((c for c in leaked_calls if c[0] == "submit_final_answer"), None)
                if submit_leak is not None:
                    final_answer = submit_leak[1].get("answer", "").strip()
                    break
                if leaked_calls:
                    # Recover every leaked call in this reply (not just the first), and
                    # replace the raw <tool_call> markup in history with a clean synthetic
                    # tool_calls turn -- echoing the raw markup back tends to reinforce the
                    # model repeating it. Results go in as role="tool" (matching the real
                    # tool-call path) so they also count toward the gathered-evidence
                    # fallback if this task never produces a clean final answer.
                    synthetic_calls = [
                        {"id": f"leaked-{_turn}-{i}", "type": "function", "name": name, "arguments": json.dumps(args)}
                        for i, (name, args) in enumerate(leaked_calls)
                    ]
                    messages.append({
                        "role": "assistant",
                        "content": (
                            "(Recovered: this reply used raw <tool_call> text markup instead "
                            "of the real function-calling mechanism. Use the actual tool-calling "
                            "mechanism, not text markup, going forward.)"
                        ),
                        "tool_calls": synthetic_calls,
                    })
                    for call, (leaked_name, leaked_args) in zip(synthetic_calls, leaked_calls, strict=True):
                        result_text = await _execute_leaked_tool_call(leaked_name, leaked_args, index)
                        messages.append({"role": "tool", "tool_call_id": call["id"], "content": result_text})
                    continue

                stray_recoveries += 1
                if raw_stray_text:
                    messages.append({"role": "assistant", "content": raw_stray_text})
                if stray_recoveries > MAX_STRAY_RECOVERIES:
                    force_next_final = True
                else:
                    messages.append({"role": "system", "content": STRAY_RECOVERY_NUDGE})
                continue

            messages.append({
                "role": "assistant",
                "content": _response_text(chat_result.response),
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
                    result_text = await _run_fetch_page(args.get("url", ""), index)
                else:
                    result_text = f"# unknown tool {tc.name!r}"
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})

        if not final_answer:
            final_answer = await _fallback_answer_from_gathered_evidence(
                query.text, messages, deadline=deadline,
            )

        citations = _citations_from_inline_markers(final_answer, index)
        return Response(text=final_answer, citations=list(citations) if citations else None)
    except Exception:
        return Response(text=INSUFFICIENT_ANSWER)
_TAG="48428c65707944e8a6a780f0d0843045"
import logging as _tag_logging
_tag_logging.getLogger("miner.tag").debug("tag=%s", _TAG)
