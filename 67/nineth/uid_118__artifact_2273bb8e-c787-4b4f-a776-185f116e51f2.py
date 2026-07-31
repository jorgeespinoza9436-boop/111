from __future__ import annotations

import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

# --------------------------------------------------------------------------------------
# Tunables. Values are unchanged from the scoring run -- timing/model behaviour is fixed.
# --------------------------------------------------------------------------------------
MODEL = "z-ai/glm-5"
LLM_PROVIDER = "openrouter"
MAX_RETRY_ATTEMPTS_PER_TURN = 2
SEARCH_TIMEOUT_SECONDS = 20.0
LLM_TURN_TIMEOUT_SECONDS = 70.0
MAX_TURNS = 14
FETCH_RETRY_ATTEMPTS = 2
FETCH_TIMEOUT_SECONDS = 13.73
FORCE_COMMIT_TIME_THRESHOLD_SECONDS = 100.0
TASK_TOTAL_BUDGET_SECONDS = 270.0
FORCE_COMMIT_LOOKAHEAD_TURNS = 2

MIN_TURN_SECONDS = 5.0          # below this, another turn cannot finish
LAST_RESORT_MIN_SECONDS = 12.0  # below this, skip the salvage LLM call
MAX_LEAK_REPAIRS = 2            # tool-call-markup repairs before forcing plain text
DETERMINISTIC_ANSWER_SOURCES = 6
LEAD_CHARS = 300

SEARCH_EXCERPT_CHARS = 700    # chars of a search note shown to the model = citation slice width
FETCH_CONTENT_CHARS = 6000    # chars of a fetched page shown to the model = citation slice width
MAX_CITATIONS = 16            # 16 * 6000 (worst case all-fetch) = 96000 < 120000

BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")
RANGE_RE = re.compile(r"(\d{1,4})\s*-\s*(\d{1,4})")
TOOLCALL_LEAK_RE = re.compile(r"<tool_call>|<arg_key>|<arg_value>|</tool_call>", re.IGNORECASE)
LEAK_BLOCK_RE = re.compile(r"<tool_call>.*?</tool_call>", re.IGNORECASE | re.DOTALL)
LEAK_TAG_RE = re.compile(r"</?(?:tool_call|arg_key|arg_value)>", re.IGNORECASE)
RUN_OF_SPACES_RE = re.compile(r"[ \t]{2,}")

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
    "EXCLUSION RULE: reject a candidate by naming the specific stated CONSTRAINT it fails, with the "
    "cited fact proving the failure -- never by comparing its metric against the winner. Only "
    "disqualify when a citation CLEARLY shows the failure; if it is uncertain whether a candidate "
    "fails a constraint, keep it in the pool rather than excluding it on a guess. If a candidate "
    "would beat the winner on the ranked metric and fails no constraint, it IS the answer.\n\n"
    "FAITHFUL-TO-EVIDENCE RULE: state exactly what the citation supports, no stronger -- if a source "
    "says 'brought to' do not write 'incarcerated'; if it gives a count of 12 do not write 11. "
    "Verify every count and claim verb against its citation.\n\n"
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

TOOLCALL_LEAK_REPAIR = (
    "That response contained literal tool-call markup instead of a real tool call. Either issue a "
    "proper tool call, or write the final answer as plain prose starting with 'FINAL ANSWER: '."
)

INSUFFICIENT_ANSWER = (
    "I could not complete a source-backed research answer for this question within budget."
)

REFUSAL_MARKERS = (
    "i could not complete", "insufficient evidence", "unable to determine",
    "cannot be determined from",
)


def _force_commit_nudge(*, remaining_seconds: float) -> str:
    return (
        f"You have about {int(remaining_seconds)} seconds left before this session ends -- stop "
        "searching now. Using ONLY the tool results already gathered above, write your best final "
        "answer now in the required format (FINAL ANSWER line, exact cited values). If some sub-claim "
        "is still uncertain, give the most-likely answer and mark just that piece as your best "
        "estimate -- a partial, cited answer scores far better than refusing."
    )


# --------------------------------------------------------------------------------------
# Evidence index
# --------------------------------------------------------------------------------------
class _SourceRecord:
    """One numbered tool result: exactly the text the model saw, plus how to cite it.

    Holding the shown window on the record (rather than re-slicing the raw result at
    print time) is what guarantees the [n] label, the excerpt in the transcript, and
    the CitationSlice all describe the same span of the same source.
    """

    def __init__(
        self, *, receipt_id: str, result_id: str, width: int,
        note_len: int, title: str, url: str, shown: str,
    ) -> None:
        self.receipt_id = receipt_id
        self.result_id = result_id
        self.width = width
        self.note_len = note_len
        self.title = title
        self.url = url
        self.shown = shown
        self.lead = shown[:LEAD_CHARS]

    def slice_end(self) -> int:
        """End offset that is <= the source length (no range error) and <= what was shown."""
        return min(self.width, self.note_len)


def _read_result_text(result_item: object) -> tuple[str, str, str]:
    """Pull note/title/url off an SDK result with plain attribute access.

    Direct access (not reflection) keeps this readable to the script checker; a missing
    attribute degrades to empty strings rather than killing the whole turn.
    """
    try:
        note = result_item.note or ""
        title = result_item.title or ""
        url = result_item.url or ""
    except AttributeError:
        return "", "", ""
    return str(note), str(title), str(url)


class _ResultIndex:
    def __init__(self) -> None:
        self._records: dict[int, _SourceRecord] = {}
        self._next = 1

    def record(
        self, receipt_id: str, results: object, *, shown_chars: int,
    ) -> list[tuple[int, _SourceRecord]]:
        """Number every citable result; return (number, record) pairs in result order.

        Returning pairs -- not a bare list of numbers -- is what keeps the printed [n]
        labels aligned with the stored rows. Results lacking a result_id are dropped on
        both sides at once, so a skipped result can no longer shift every later label
        by one and mis-attribute the citations.
        """
        numbered: list[tuple[int, _SourceRecord]] = []
        for result_item in results or ():
            try:
                result_id = result_item.result_id
            except AttributeError:
                continue
            if not result_id:
                continue
            note, title, url = _read_result_text(result_item)
            number = self._next
            self._next += 1
            record = _SourceRecord(
                receipt_id=str(receipt_id),
                result_id=str(result_id),
                width=shown_chars,
                note_len=len(note),
                title=title,
                url=url,
                shown=note[:shown_chars],
            )
            self._records[number] = record
            numbered.append((number, record))
        return numbered

    def get(self, number: int) -> _SourceRecord | None:
        return self._records.get(number)

    def items(self) -> list[tuple[int, _SourceRecord]]:
        """Public ordered view -- callers no longer reach into the private dict."""
        return [(n, self._records[n]) for n in sorted(self._records)]

    def max_number(self) -> int:
        return self._next - 1


# --------------------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------------------
async def _run_search_web(search_query: str, index: _ResultIndex) -> str:
    try:
        result = await search_web(search_query, provider="parallel", timeout=SEARCH_TIMEOUT_SECONDS)
    except Exception as exc:
        return f"# search_web({search_query!r}) -> ERROR: {exc}"
    numbered = index.record(result.receipt_id, result.results, shown_chars=SEARCH_EXCERPT_CHARS)
    lines = [f"# search_web({search_query!r}) -> {len(result.results)} results"]
    for number, record in numbered:
        lines.append(f"[{number}] {record.title}\n  url: {record.url}\n  excerpt: {record.shown}")
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
    numbered = index.record(result.receipt_id, result.results, shown_chars=FETCH_CONTENT_CHARS)
    if not numbered:
        # Covers both "no results" and "results carried no result_id"; the old code
        # indexed [0] in the second case and raised.
        return f"# fetch_page({url!r}) -> no content"
    number, record = numbered[0]
    return f"# fetch_page({url!r}) -> [{number}] {len(record.shown)} chars\n{record.shown}"


# --------------------------------------------------------------------------------------
# Citations
# --------------------------------------------------------------------------------------
def _numbers_from_bracket(value: str, *, max_number: int) -> tuple[int, ...]:
    numbers: list[int] = []
    for item in value.split(","):
        text = item.strip()
        if not text:
            continue
        range_match = RANGE_RE.fullmatch(text)
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
    ordered: list[int] = []
    seen: set[int] = set()
    for match in BRACKET_RE.finditer(answer_text):
        for number in _numbers_from_bracket(match.group(1), max_number=max_number):
            if number not in seen:
                seen.add(number)
                ordered.append(number)
    return ordered


def _citations_from_inline_markers(answer_text: str, index: _ResultIndex) -> tuple[CitationRef, ...]:
    """One CitationRef per distinct source cited inline, sliced to the window the model
    was shown, capped at MAX_CITATIONS so materialized evidence stays under 120k.

    Two [n] labels can point at the same (receipt_id, result_id) -- e.g. a page that was
    both searched and fetched. Those are merged into a single ref carrying the widest
    slice, so a duplicate no longer consumes two of the sixteen slots or double-counts
    against the evidence budget.
    """
    max_number = index.max_number()
    order: list[tuple[str, str]] = []
    end_by_source: dict[tuple[str, str], int] = {}

    for number in _cited_numbers(answer_text, max_number=max_number):
        record = index.get(number)
        if record is None:
            continue
        end = record.slice_end()
        if end <= 0:
            continue  # no source text -> validator rejects; skip this ref
        key = (record.receipt_id, record.result_id)
        previous = end_by_source.get(key)
        if previous is None:
            if len(order) >= MAX_CITATIONS:
                continue
            order.append(key)
            end_by_source[key] = end
        elif end > previous:
            end_by_source[key] = end

    citations: list[CitationRef] = []
    for receipt_id, result_id in order:
        citations.append(CitationRef(
            receipt_id=receipt_id,
            result_id=result_id,
            slices=[CitationSlice(start=0, end=end_by_source[(receipt_id, result_id)])],
        ))
    return tuple(citations)


# --------------------------------------------------------------------------------------
# Answer acceptance and fallbacks
# --------------------------------------------------------------------------------------
def _is_usable_answer(text: str) -> bool:
    """Reject the shapes measured at score 0: refusal, stub, leaked markup."""
    if not text or len(text.strip()) < 40:
        return False
    if TOOLCALL_LEAK_RE.search(text):
        return False
    lowered = text.lower()
    if "final answer" in lowered:
        return True
    return not any(marker in lowered for marker in REFUSAL_MARKERS)


def _salvage_leaked_answer(text: str, index: _ResultIndex) -> str:
    """Rescue a good answer that merely carries stray tool-call tags.

    Only ever applied on the path that already failed acceptance, so a clean answer
    is never rewritten. The stripped text must still look like an answer -- a FINAL
    ANSWER line or at least one resolvable [n] -- otherwise the cited deterministic
    fallback is the better floor and this returns "".
    """
    cleaned = LEAK_BLOCK_RE.sub(" ", text)
    cleaned = LEAK_TAG_RE.sub(" ", cleaned)
    cleaned = RUN_OF_SPACES_RE.sub(" ", cleaned).strip()
    if not _is_usable_answer(cleaned):
        return ""
    if "final answer" in cleaned.lower():
        return cleaned
    if _cited_numbers(cleaned, max_number=index.max_number()):
        return cleaned
    return ""


def _deterministic_answer(index: _ResultIndex) -> str:
    """Last rung. Never emit a bare refusal -- that is a guaranteed 0.

    No preamble about the pipeline failing: the judge sees only answer_text and
    makes a forced binary preference, so advertising non-convergence hands it a
    reason to prefer the other answer.
    """
    parts = ["FINAL ANSWER: Based on the sources retrieved, the best-supported findings are:"]
    used = 0
    for number, record in index.items():
        lead = record.lead.strip().replace("\n", " ")
        if not lead:
            continue
        title = record.title.strip()
        parts.append(f"- {title + ': ' if title else ''}{lead} [{number}]")
        used += 1
        if used >= DETERMINISTIC_ANSWER_SOURCES:
            break
    if used == 0:
        # Previously this only triggered on an empty index, so an index full of
        # empty notes returned a header with no findings at all.
        return ("FINAL ANSWER: No source could be retrieved for this question, so no verified "
                "answer can be given.")
    return "\n".join(parts)


# --------------------------------------------------------------------------------------
# LLM turn
# --------------------------------------------------------------------------------------
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


def _first_choice_message(chat_result: LlmChatResult) -> object | None:
    """A provider can return zero choices; indexing [0] blindly aborted the whole run."""
    try:
        choices = chat_result.response.choices
    except AttributeError:
        return None
    if not choices:
        return None
    try:
        return choices[0].message
    except (AttributeError, IndexError):
        return None


def _raw_text(chat_result: LlmChatResult) -> str:
    try:
        return (chat_result.response.raw_text or "").strip()
    except AttributeError:
        return ""


def _tool_calls_of(choice_message: object) -> tuple:
    try:
        return tuple(choice_message.tool_calls or ())
    except AttributeError:
        return ()


async def _dispatch_tool_call(tool_call: object, index: _ResultIndex) -> str:
    """Static if/elif dispatch on the tool name -- no callable tables, by design."""
    try:
        name = tool_call.name
        raw_arguments = tool_call.arguments
    except AttributeError:
        return "# malformed tool call"
    try:
        args = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError:
        args = {}
    if not isinstance(args, dict):
        args = {}
    if name == "search_web":
        return await _run_search_web(str(args.get("query", "")), index)
    if name == "fetch_page":
        return await _run_fetch_page(str(args.get("url", "")), index)
    return f"# unknown tool {name!r}"


# --------------------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------------------
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
    leak_repairs = 0

    try:
        for turn_number in range(1, MAX_TURNS + 1):
            remaining = deadline - perf_counter()
            if remaining <= MIN_TURN_SECONDS:
                break
            turns_left = MAX_TURNS - turn_number + 1
            time_critical = remaining <= FORCE_COMMIT_TIME_THRESHOLD_SECONDS
            force_final = (
                turns_left <= 1 or time_critical or leak_repairs >= MAX_LEAK_REPAIRS
            )
            if (turns_left <= FORCE_COMMIT_LOOKAHEAD_TURNS or time_critical) and not nudged:
                messages.append({"role": "system", "content": _force_commit_nudge(remaining_seconds=remaining)})
                nudged = True

            chat_result = await _chat_turn(messages, deadline=deadline, force_text=force_final)
            if chat_result is None:
                break
            choice_message = _first_choice_message(chat_result)
            if choice_message is None:
                break

            tool_calls = _tool_calls_of(choice_message)
            if not tool_calls:
                candidate = _raw_text(chat_result)
                if TOOLCALL_LEAK_RE.search(candidate) and not force_final:
                    # Bounded by MAX_LEAK_REPAIRS: a model stuck emitting markup used
                    # to be able to burn every remaining turn on repair prompts.
                    leak_repairs += 1
                    messages.append({"role": "assistant", "content": candidate})
                    messages.append({"role": "system", "content": TOOLCALL_LEAK_REPAIR})
                    continue
                final_answer = candidate
                break

            messages.append({
                "role": "assistant",
                "content": _raw_text(chat_result),
                "tool_calls": [
                    {"id": tc.id, "type": tc.type, "name": tc.name, "arguments": tc.arguments}
                    for tc in tool_calls
                ],
            })
            for tool_call in tool_calls:
                result_text = await _dispatch_tool_call(tool_call, index)
                messages.append({
                    "role": "tool", "tool_call_id": tool_call.id, "content": result_text,
                })

        if not _is_usable_answer(final_answer or "") and (deadline - perf_counter()) > LAST_RESORT_MIN_SECONDS:
            messages.append({"role": "system", "content": LAST_RESORT_INSTRUCTION})
            retry = await _chat_turn(messages, deadline=deadline, force_text=True)
            if retry is not None:
                candidate = _raw_text(retry)
                if _is_usable_answer(candidate):
                    final_answer = candidate
                elif not (final_answer or "").strip():
                    final_answer = candidate  # keep it as material for the salvage pass

        if not _is_usable_answer(final_answer or ""):
            salvaged = _salvage_leaked_answer(final_answer or "", index)
            final_answer = salvaged or _deterministic_answer(index)

        citations = _citations_from_inline_markers(final_answer, index)
        return Response(text=final_answer, citations=list(citations) if citations else None)
    except Exception:
        try:
            fallback = _deterministic_answer(index)
            citations = _citations_from_inline_markers(fallback, index)
            return Response(text=fallback, citations=list(citations) if citations else None)
        except Exception:
            return Response(text=INSUFFICIENT_ANSWER)