from __future__ import annotations


FETCH_TIMEOUT_SECONDS = 15.0
MAX_FETCH_CONTENT_CHARS = 40_000
FINAL_ANSWER_CUTOFF_SECONDS = 285.0
PAGE_READER_TIMEOUT_SECONDS = 20.0
RESEARCH_TURNS = 23
RESEARCH_CUTOFF_SECONDS = 240.0
TASK_TOTAL_BUDGET_SECONDS = 250.0
MAX_OUTPUT_TOKENS = 127_999
MAX_SEARCH_RESULTS = 10

LLM_PROVIDER = "openrouter"
MODEL = "z-ai/glm-5.2"

from time import perf_counter
import asyncio
import hashlib
import json
import re
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import TypeVar
from urllib.parse import urldefrag, urlparse

from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.llm import LlmChoiceMessage, LlmMessageToolCall, LlmUsage
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

VERSION = "v230-2-fdlq"
_BASE_MODEL = "deepseek/deepseek-v4-flash-0731"
FINALIZATION_TURNS = 2
MAX_TURNS = RESEARCH_TURNS + FINALIZATION_TURNS
ENTRYPOINT_TIMEOUT_SECONDS = 300.0
ENTRYPOINT_RETURN_CUTOFF_SECONDS = 295.0
TURNS_REMAINING_WARNING_THRESHOLD = 20
CONTEXT_WINDOW_TOKENS = 1_048_576
CONTEXT_SUMMARIZATION_CUTOFF = 0.7
PAGE_READER_CHUNK_SIZE = 6_000
PAGE_READER_CHUNK_OVERLAP = 500
MAX_CITATION_REFS = 200
MAX_CITATION_SEGMENTS = 400
MAX_CITATION_EVIDENCE_CHARS = 120_000
MIN_CITATION_SLICE_CHARS = 100
MAX_EVIDENCE_SEGMENT_CHARS = 1_600
EVIDENCE_SEGMENT_OVERLAP_CHARS = 200

SYSTEM_PROMPT = (
    "You are an AI agent that will be given a specific task. You are to complete that task using the tools "
    "provided in 25 steps. You will need to call a finish tool as your last step, where you will pass your "
    "finish reason and any required final fields for that tool.\n"
    " You are not able to interact with the user during the task.\n\n"
    "SOURCE RESTRICTIONS: Before researching, identify whether the task limits acceptable evidence to named "
    "sources, documents, editions, page types, or publication forms. If it does, that limit is binding for search "
    "targets, fetched evidence, calculations, and final citations. A discovery page may help locate the required "
    "source but cannot support the final answer. Do not substitute a third-party summary, a different edition, or "
    "another page or document form merely because it contains the same facts. Do not call finish until every "
    "material answer claim is directly supported by shown evidence from the allowed source and exact requested "
    "document form; if required evidence is still missing, continue researching within the remaining research "
    "turns. Example: when a task says to use only an agency's annual report, cite that report, not a news summary "
    "or a later edition."
)

MESSAGE_SUMMARIZER = """The context window is approaching its limit. Please create a concise summary of the conversation so far to preserve important information.

Your summary should include:

1. **Task Overview**: What is the main goal or objective?

2. **Progress Made**: What has been accomplished so far?
   - Key files created/modified (with paths)
   - Important functions/classes implemented
   - Tools used and their outcomes

3. **Current State**: Where are we now?
   - What is currently working?
   - What has been tested/verified?

4. **Next Steps**: What still needs to be done?
   - Outstanding TODOs (with specific file paths and line numbers if applicable)
   - Known issues or bugs to address
   - Features or functionality not yet implemented

5. **Important Context**: Any critical details that shouldn't be lost
   - Special configurations or setup requirements
   - Important variable names, API endpoints, or data structures
   - Edge cases or constraints to keep in mind
   - Dependencies or relationships between components

Keep the summary concise but comprehensive. Do not use any tools. Focus on actionable information that will allow smooth continuation of the work.
"""

MESSAGE_SUMMARIZER_TEXT_ONLY = (
    "IMPORTANT: Respond with the summary as plain prose text only. Do NOT call any tools — a tool call cannot serve "
    "as a summary and will cause the summarization to fail."
)

MESSAGE_SUMMARIZER_BRIDGE = """**Context Continuation**

Due to context window limitations, the previous conversation has been summarized. Below is a summary of what happened before:

---

{summary}

---

You should continue working on this task from where it was left off. All the progress, current state, and next steps are described in the summary above. Proceed with completing any outstanding work."""

CONTAMINATION_NEEDLES = (
    "deepsearchqa",
    "deep search qa",
    "google/deepsearchqa",
    "dsqa-full.csv",
    "artificialanalysis.ai/agents/search-api",
    "openrouter.ai/benchmarks/deepsearchqa",
)

WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web. Returns up to 10 ranked results from Parallel Search API advanced, including titles, "
            "URLs, and excerpts. Use concise keyword queries."
        ),
        "parameters": {
            "additionalProperties": False,
            "properties": {
                "query": {
                    "description": "One concise web search query.",
                    "maxLength": 200,
                    "minLength": 1,
                    "title": "Query",
                    "type": "string",
                }
            },
            "required": ["query"],
            "title": "WebSearchParams",
            "type": "object",
        },
    },
}

WEB_FETCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_fetch",
        "description": (
            "Fetch and extract text from a top-level URL returned by web_search or an HTTP(S) URL literally "
            "shown in that result's title or excerpt. Other URLs are rejected."
        ),
        "parameters": {
            "additionalProperties": False,
            "properties": {
                "url": {
                    "description": "One top-level or literally shown child URL from an earlier web_search call.",
                    "minLength": 1,
                    "title": "Url",
                    "type": "string",
                }
            },
            "required": ["url"],
            "title": "WebFetchParams",
            "type": "object",
        },
    },
}

FINISH_TOOL = {
    "type": "function",
    "function": {
        "name": "finish",
        "description": "Submit the final answer and end the task. Call this only when the answer is ready.",
        "parameters": {
            "additionalProperties": False,
            "properties": {
                "answer": {
                    "description": "The final answer to the user's question. Give only the answer.",
                    "minLength": 1,
                    "title": "Answer",
                    "type": "string",
                }
            },
            "required": ["answer"],
            "title": "FinishAnswerParams",
            "type": "object",
        },
    },
}

TOOLS = [WEB_SEARCH_TOOL, WEB_FETCH_TOOL, FINISH_TOOL]


class DeadlineExceededError(RuntimeError):
    """The declared miner-owned wall-clock budget cannot start another stage."""


class StageDeadlineElapsedError(TimeoutError):
    """A miner-owned stage deadline elapsed before the awaited call completed."""


DeadlineResult = TypeVar("DeadlineResult")


async def _await_before_stage_cutoff(
    operation: Awaitable[DeadlineResult],
    *,
    timeout_seconds: float,
) -> DeadlineResult:
    task = asyncio.ensure_future(operation)
    done, _pending = await asyncio.wait(
        (task,),
        timeout=max(0.001, timeout_seconds - 0.1),
    )
    if task in done:
        return await task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    raise StageDeadlineElapsedError("miner-owned stage deadline elapsed")


@dataclass(frozen=True, slots=True)
class ExecutionDeadline:
    started_at: float
    clock: Callable[[], float]

    @classmethod
    def start(cls, *, clock: Callable[[], float] = time.monotonic) -> ExecutionDeadline:
        return cls(started_at=clock(), clock=clock)

    def elapsed_seconds(self) -> float:
        return max(0.0, self.clock() - self.started_at)

    def remaining_before(self, cutoff_seconds: float) -> float:
        return max(0.0, cutoff_seconds - self.elapsed_seconds())

    def research_open(self) -> bool:
        return self.remaining_before(RESEARCH_CUTOFF_SECONDS) > 0.0

    def require_timeout_before(self, cutoff_seconds: float, *, stage: str) -> float:
        remaining = self.remaining_before(cutoff_seconds)
        if remaining <= 0.0:
            raise DeadlineExceededError(f"{stage} cannot start after its wall-clock cutoff")
        return remaining


def _log_deadline_event(event: str, deadline: ExecutionDeadline, **details: object) -> None:
    print(
        json.dumps(
            {
                "event": event,
                "elapsed_seconds": round(deadline.elapsed_seconds(), 6),
                **details,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )


@dataclass(frozen=True, slots=True)
class EvidenceSegment:
    segment_id: int
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class EvidenceCandidate:
    candidate_id: int
    receipt_id: str
    result_id: str
    url: str
    title: str
    note: str
    segments: tuple[EvidenceSegment, ...]


@dataclass(frozen=True, slots=True)
class EvidenceSelection:
    candidate_id: int
    segment_ids: tuple[int, ...]
    is_support_set: bool


def _collapsed_whitespace_with_offsets(text: str) -> tuple[str, tuple[int, ...], tuple[int, ...]]:
    normalized: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    in_whitespace = False
    for offset, character in enumerate(text):
        if character.isspace():
            if not in_whitespace:
                normalized.append(" ")
                starts.append(offset)
                ends.append(offset + 1)
                in_whitespace = True
            else:
                ends[-1] = offset + 1
            continue
        normalized.append(character)
        starts.append(offset)
        ends.append(offset + 1)
        in_whitespace = False
    return "".join(normalized), tuple(starts), tuple(ends)


def _all_exact_ranges(source_text: str, visible_text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    cursor = 0
    while True:
        start = source_text.find(visible_text, cursor)
        if start < 0:
            return ranges
        ranges.append((start, start + len(visible_text)))
        cursor = start + 1


def _all_whitespace_normalized_ranges(source_text: str, visible_text: str) -> list[tuple[int, int]]:
    normalized_source, starts, ends = _collapsed_whitespace_with_offsets(source_text)
    normalized_visible, _, _ = _collapsed_whitespace_with_offsets(visible_text)
    normalized_visible = normalized_visible.strip()
    if not normalized_visible:
        return []
    ranges: list[tuple[int, int]] = []
    cursor = 0
    while True:
        start = normalized_source.find(normalized_visible, cursor)
        if start < 0:
            return ranges
        end = start + len(normalized_visible)
        ranges.append((starts[start], ends[end - 1]))
        cursor = start + 1


def _merge_ranges(ranges: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(ranges):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue
        previous_start, previous_end = merged[-1]
        merged[-1] = (previous_start, max(previous_end, end))
    return merged


def _expand_to_minimum_slice(source_length: int, start: int, end: int) -> tuple[int, int]:
    if source_length < MIN_CITATION_SLICE_CHARS:
        return 0, source_length
    missing = max(0, MIN_CITATION_SLICE_CHARS - (end - start))
    left = min(start, missing // 2)
    start -= left
    end += missing - left
    if end > source_length:
        start = max(0, start - (end - source_length))
        end = source_length
    return start, end


def _split_segment_range(start: int, end: int) -> list[tuple[int, int]]:
    if end - start <= MAX_EVIDENCE_SEGMENT_CHARS:
        return [(start, end)]
    step = MAX_EVIDENCE_SEGMENT_CHARS - EVIDENCE_SEGMENT_OVERLAP_CHARS
    segments: list[tuple[int, int]] = []
    cursor = start
    while cursor < end:
        segment_end = min(cursor + MAX_EVIDENCE_SEGMENT_CHARS, end)
        if segment_end - cursor < MIN_CITATION_SLICE_CHARS and segments:
            previous_start, _ = segments[-1]
            segments[-1] = (previous_start, end)
            break
        segments.append((cursor, segment_end))
        if segment_end == end:
            break
        cursor += step
    return segments


def _evidence_segments(note: str, visible_texts: Sequence[str]) -> tuple[EvidenceSegment, ...]:
    visible_ranges: list[tuple[int, int]] = []
    for visible_text in visible_texts:
        if not visible_text.strip():
            continue
        exact = _all_exact_ranges(note, visible_text)
        visible_ranges.extend(exact or _all_whitespace_normalized_ranges(note, visible_text))
    expanded = [_expand_to_minimum_slice(len(note), start, end) for start, end in visible_ranges]
    segment_ranges: list[tuple[int, int]] = []
    for start, end in _merge_ranges(expanded):
        segment_ranges.extend(_split_segment_range(start, end))
    return tuple(
        EvidenceSegment(segment_id=segment_id, start=start, end=end)
        for segment_id, (start, end) in enumerate(dict.fromkeys(segment_ranges))
    )


def _visible_fetch_texts(body: str) -> tuple[str, ...]:
    if len(body) <= MAX_FETCH_CONTENT_CHARS:
        return (body,)
    half = MAX_FETCH_CONTENT_CHARS // 2
    return body[:half], body[-half:]


class EvidenceLedger:
    """Own exact source support and stable evidence numbers shown to the model."""

    def __init__(self) -> None:
        self._candidates: list[EvidenceCandidate] = []
        self._identity_candidates: dict[tuple[str, str], EvidenceCandidate] = {}
        self._selections: list[EvidenceSelection] = []
        self._support_set_numbers: dict[tuple[int, tuple[int, ...]], int] = {}

    @property
    def candidates(self) -> tuple[EvidenceCandidate, ...]:
        return tuple(self._candidates)

    @property
    def support_set_numbers(self) -> tuple[int, ...]:
        return tuple(
            number
            for number, selection in enumerate(self._selections, start=1)
            if selection.is_support_set
        )

    def capture(
        self,
        result: object,
        *,
        retained_indices: set[int],
        visible_text_by_index: dict[int, tuple[str, ...]],
    ) -> dict[int, EvidenceCandidate]:
        if getattr(result, "result_policy", None) != "referenceable":
            raise RuntimeError("observed search result is not referenceable")
        receipt_id = getattr(result, "receipt_id", None)
        if not isinstance(receipt_id, str) or not receipt_id:
            raise RuntimeError("referenceable search result has no receipt_id")

        observed: dict[int, EvidenceCandidate] = {}
        for item in getattr(result, "results", ()):
            index = getattr(item, "index", None)
            if index not in retained_indices:
                continue
            result_id = getattr(item, "result_id", None)
            note = getattr(item, "note", None)
            if not isinstance(result_id, str) or not result_id:
                raise RuntimeError("referenceable search result has no result_id")
            if not isinstance(note, str) or not note.strip():
                continue
            identity = (receipt_id, result_id)
            existing = self._identity_candidates.get(identity)
            if existing is not None:
                observed[index] = existing
                continue
            segments = _evidence_segments(note, visible_text_by_index.get(index, ()))
            if not segments:
                continue
            candidate = EvidenceCandidate(
                candidate_id=len(self._candidates),
                receipt_id=receipt_id,
                result_id=result_id,
                url=str(getattr(item, "url", None) or ""),
                title=str(getattr(item, "title", None) or ""),
                note=note,
                segments=segments,
            )
            self._candidates.append(candidate)
            self._identity_candidates[identity] = candidate
            for segment in segments:
                self._selections.append(EvidenceSelection(candidate.candidate_id, (segment.segment_id,), False))
            observed[index] = candidate
        return observed

    def numbered_segments(
        self,
        candidate: EvidenceCandidate,
    ) -> tuple[tuple[int, EvidenceSegment], ...]:
        segments = {segment.segment_id: segment for segment in candidate.segments}
        return tuple(
            (number, segments[selection.segment_ids[0]])
            for number, selection in enumerate(self._selections, start=1)
            if selection.candidate_id == candidate.candidate_id and not selection.is_support_set
        )

    def register_support_set(self, candidate: EvidenceCandidate) -> int:
        segment_ids = tuple(segment.segment_id for segment in candidate.segments)
        if not segment_ids:
            raise RuntimeError("cannot register an empty evidence support set")
        identity = (candidate.candidate_id, segment_ids)
        existing = self._support_set_numbers.get(identity)
        if existing is not None:
            return existing
        self._selections.append(EvidenceSelection(candidate.candidate_id, segment_ids, True))
        evidence_number = len(self._selections)
        self._support_set_numbers[identity] = evidence_number
        return evidence_number

    def selection_for_evidence_number(self, evidence_number: int) -> EvidenceSelection | None:
        if evidence_number < 1 or evidence_number > len(self._selections):
            return None
        return self._selections[evidence_number - 1]


def _normalized_url(url: str) -> str:
    return urldefrag(url.strip()).url


CHILD_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


def _admissible_url(value: str) -> str | None:
    cleaned = _normalized_url(value.rstrip(".,;:!?)\"]"))
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        return None
    return cleaned


def _visible_child_urls(*texts: str | None) -> set[str]:
    discovered: set[str] = set()
    for text in texts:
        if not text:
            continue
        for match in CHILD_URL_PATTERN.findall(text):
            admitted = _admissible_url(match)
            if admitted is not None:
                discovered.add(admitted)
    return discovered


@dataclass(frozen=True, slots=True)
class PageChunk:
    chunk_id: str
    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class PageReadResult:
    selected_texts: tuple[str, ...]
    page_findings: str
    missing_information: str


PAGE_READER_SYSTEM_PROMPT = """ROLE
You read one complete source document for a separate research agent. Select the original chunks that let that agent
verify every useful finding from this page. Base the memo only on this document. Do not search, use tools, or expose
private reasoning.

SELECTION RULES
- Select a chunk when it directly supports a requested fact, exposes a useful source link, or supplies a heading,
  label, unit, exception, or qualifier needed to interpret a fact.
- A zero count, no-match result, or other exhaustive negative is a useful finding. For such a finding, select the
  document scope and every candidate region needed to verify completeness.
- The selected original support must fit within 120000 characters. Keep the smallest complete support set. If the
  complete support needed for a finding cannot fit, do not assert that finding; explain the unresolved fact in
  missing_information instead.
- selected_chunk_ids may be empty only when this page contributes no fact or source route to the answer. In that case,
  page_findings must also be an empty string and missing_information must explain what source is still needed.
- If page_findings contains any useful conclusion, selected_chunk_ids must contain its supporting original chunks.

OUTPUT CONTRACT
Return one JSON object with exactly these fields:
- selected_chunk_ids: unique input chunk IDs in document order.
- page_findings: a concise factual memo of what the selected original chunks establish, or an empty string only when
  the page is irrelevant.
- missing_information: facts still needed from another page, or an empty string.
Return no Markdown and no other text.

GOOD ZERO-RESULT EXAMPLE
The question asks whether any Florida record was REMOVED. C0000 identifies the annual document, while C0008 and C0014
contain all Florida candidate records and none has action REMOVED.
{"selected_chunk_ids":["C0000","C0008","C0014"],"page_findings":"The annual document contains no Florida REMOVED record.","missing_information":""}

BAD ZERO-RESULT EXAMPLE
{"selected_chunk_ids":[],"page_findings":"There are zero Florida REMOVED records.","missing_information":""}
This is invalid because it asserts a useful conclusion while returning no original evidence.

IRRELEVANT-PAGE EXAMPLE
{"selected_chunk_ids":[],"page_findings":"","missing_information":"The requested annual report is not on this page."}"""


def _page_chunks(body: str) -> tuple[PageChunk, ...]:
    if PAGE_READER_CHUNK_OVERLAP >= PAGE_READER_CHUNK_SIZE:
        raise RuntimeError("page-reader overlap must be smaller than chunk size")
    chunks: list[PageChunk] = []
    start = 0
    index = 0
    while start < len(body):
        end = min(len(body), start + PAGE_READER_CHUNK_SIZE)
        chunks.append(PageChunk(f"C{index:04d}", start, end, body[start:end]))
        if end == len(body):
            break
        start = end - PAGE_READER_CHUNK_OVERLAP
        index += 1
    return tuple(chunks)


def _json_object_from_reader_text(text: str) -> dict[str, object]:
    stripped = text.strip()
    fence = re.fullmatch(r"```(?:json)?\s*\n?(.*?)\n?```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fence is not None:
        stripped = fence.group(1).strip()
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise ValueError("page reader must return one JSON object")
    return parsed


def _validate_page_reader_output(payload: dict[str, object], chunks: tuple[PageChunk, ...]) -> PageReadResult:
    expected = {"selected_chunk_ids", "page_findings", "missing_information"}
    if set(payload) != expected:
        raise ValueError("page reader returned unexpected fields")
    selected = payload["selected_chunk_ids"]
    findings = payload["page_findings"]
    missing = payload["missing_information"]
    if not isinstance(selected, list) or any(not isinstance(item, str) for item in selected):
        raise TypeError("selected_chunk_ids must be an array of strings")
    if len(selected) != len(set(selected)):
        raise ValueError("selected_chunk_ids must be unique")
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    if any(item not in by_id for item in selected):
        raise ValueError("selected_chunk_ids contains an unknown ID")
    order = {chunk.chunk_id: index for index, chunk in enumerate(chunks)}
    if selected != sorted(selected, key=lambda item: order[item]):
        raise ValueError("selected_chunk_ids must be in document order")
    if not isinstance(findings, str):
        raise TypeError("page_findings must be a string")
    if not isinstance(missing, str):
        raise TypeError("missing_information must be a string")
    if findings.strip() and not selected:
        raise ValueError(
            "page_findings contributes to the answer but selected_chunk_ids is empty; select the original chunks "
            "that verify the finding, and for an exhaustive negative include the document scope plus every candidate "
            "region or the complete document"
        )
    if selected and not findings.strip():
        raise ValueError("selected_chunk_ids is non-empty but page_findings is empty; explain what the chunks establish")
    if not selected and not missing.strip():
        raise ValueError("an irrelevant page with no selected chunks must explain the missing information")
    return PageReadResult(tuple(by_id[item].text for item in selected), findings, missing)


async def _read_large_page(
    *,
    question: str,
    url: str,
    body: str,
    deadline: ExecutionDeadline,
) -> PageReadResult:
    chunks = _page_chunks(body)
    serialized = "\n\n".join(
        f"<{chunk.chunk_id} start={chunk.start} end={chunk.end}>\n{chunk.text}\n</{chunk.chunk_id}>"
        for chunk in chunks
    )
    messages: list[dict[str, object]] = [
        {"role": "system", "content": PAGE_READER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"QUESTION\n{question}\n\nSOURCE URL\n{url}\n\nDOCUMENT CHUNKS\n{serialized}",
        },
    ]
    reader_started_at = deadline.clock()
    for attempt in range(1, 3):
        reader_elapsed = max(0.0, deadline.clock() - reader_started_at)
        reader_remaining = PAGE_READER_TIMEOUT_SECONDS - reader_elapsed
        if reader_remaining <= 0.0:
            raise DeadlineExceededError("large-page reader exhausted its shared 20-second call and recovery budget")
        timeout_seconds = min(
            reader_remaining,
            deadline.require_timeout_before(RESEARCH_CUTOFF_SECONDS, stage="large-page reader"),
        )
        result = await _await_before_stage_cutoff(
            llm_chat(
                provider="openrouter",
                model=_BASE_MODEL,
                messages=messages,
                temperature=0,
                thinking={"enabled": False},
                provider_extra=None,
                timeout=timeout_seconds,
            ),
            timeout_seconds=timeout_seconds,
        )
        if len(result.response.choices) != 1:
            raise RuntimeError("page reader did not return exactly one choice")
        message = result.response.choices[0].message
        if message.tool_calls:
            raise RuntimeError("page reader returned an unexpected tool call")
        text = _assistant_text(message)
        if text is None:
            raise RuntimeError("page reader returned no text")
        try:
            page_read = _validate_page_reader_output(_json_object_from_reader_text(text), chunks)
            support_segments = _evidence_segments(body, page_read.selected_texts)
            support_ranges = _merge_ranges((segment.start, segment.end) for segment in support_segments)
            support_chars = sum(end - start for start, end in support_ranges)
            if support_chars > MAX_CITATION_EVIDENCE_CHARS:
                raise ValueError(
                    f"selected original support is {support_chars} characters, above the "
                    f"{MAX_CITATION_EVIDENCE_CHARS}-character public evidence limit; select the smallest complete "
                    "support set, and move any finding that cannot fit to missing_information instead of asserting it"
                )
            if len(support_ranges) > MAX_CITATION_SEGMENTS:
                raise ValueError(
                    f"selected original support forms {len(support_ranges)} ranges, above the "
                    f"{MAX_CITATION_SEGMENTS}-segment public evidence limit; select a smaller complete support set"
                )
            return page_read
        except (TypeError, ValueError) as error:
            if attempt == 2:
                raise RuntimeError(
                    f"page reader output rejected after one feedback retry: {error}; raw_output={text!r}"
                ) from error
            _log_deadline_event("large_page_reader_feedback_retry", deadline, reason=str(error))
            messages.extend(
                [
                    {"role": "assistant", "content": text},
                    {
                        "role": "user",
                        "content": f"Your output was rejected by the mechanical contract: {error}. Return a corrected JSON object.",
                    },
                ]
            )
    raise AssertionError("page-reader recovery loop ended unexpectedly")


def _contamination_hit(text: str) -> str | None:
    folded = text.casefold()
    for needle in CONTAMINATION_NEEDLES:
        if needle in folded:
            return needle
    return None


def _truncate_middle(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return (
        text[: max_length // 2]
        + f"\n... This content has been truncated from an original {len(text)} characters to stay below "
        + f"{max_length} characters ...\n"
        + text[-max_length // 2 :]
    )


def _parse_object(arguments: str) -> dict[str, object] | None:
    try:
        parsed = json.loads(arguments if arguments.strip() else "{}")
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _single_string_argument(
    arguments: str,
    *,
    field: str,
    max_length: int | None = None,
) -> str | None:
    parsed = _parse_object(arguments)
    if parsed is None or set(parsed) != {field}:
        return None
    value = parsed[field]
    if not isinstance(value, str) or not value or (max_length is not None and len(value) > max_length):
        return None
    return value


def _assistant_text(message: LlmChoiceMessage) -> str | None:
    content = message.content
    texts: list[str] = []
    for part in content:
        if part.text is not None:
            texts.append(part.text)
    if not texts:
        return None
    return "".join(texts)


def _assistant_input_message(message: LlmChoiceMessage) -> dict[str, object]:
    text = _assistant_text(message)
    tool_calls = []
    for call in message.tool_calls or ():
        tool_calls.append(
            {
                "id": call.id,
                "type": call.type,
                "name": call.name,
                "arguments": call.arguments if call.arguments.strip() else "{}",
            }
        )
    payload: dict[str, object] = {
        "role": "assistant",
        "content": text,
    }
    if tool_calls:
        payload["tool_calls"] = tool_calls
    if message.reasoning_details is not None:
        payload["reasoning_details"] = list(message.reasoning_details)
    return payload


def _tool_result_message(call: LlmMessageToolCall, content: str) -> dict[str, object]:
    return {
        "role": "tool",
        "tool_call_id": call.id,
        "name": call.name,
        "content": content,
    }


async def _search(
    query: str,
    allowed_urls: set[str],
    ledger: EvidenceLedger,
    deadline: ExecutionDeadline | None = None,
) -> str:
    attempt_number = 0
    while True:
        if deadline is not None and not deadline.research_open():
            _log_deadline_event("research_tool_skipped_at_deadline", deadline, tool="web_search")
            return "<web_search><error>The wall-clock research deadline has been reached.</error></web_search>"
        attempt_number += 1
        timeout_seconds = (
            None
            if deadline is None
            else deadline.require_timeout_before(RESEARCH_CUTOFF_SECONDS, stage="web_search")
        )
        try:
            if timeout_seconds is None:
                result = await search_web(
                    query,
                    provider="parallel",
                    num=MAX_SEARCH_RESULTS,
                    provider_extra={"mode": "advanced"},
                )
            else:
                result = await _await_before_stage_cutoff(
                    search_web(
                        query,
                        provider="parallel",
                        num=MAX_SEARCH_RESULTS,
                        provider_extra={"mode": "advanced"},
                        timeout=timeout_seconds,
                    ),
                    timeout_seconds=timeout_seconds,
                )
        except StageDeadlineElapsedError:
            _log_deadline_event("research_tool_timed_out_at_deadline", deadline, tool="web_search")
            return "<web_search><error>The wall-clock research deadline was reached during search.</error></web_search>"
        except BaseException:
            if deadline is not None and not deadline.research_open():
                _log_deadline_event("research_retry_stopped_at_deadline", deadline, tool="web_search")
                return "<web_search><error>The wall-clock research deadline has been reached.</error></web_search>"
            backoff_seconds = min(2 ** min(attempt_number - 1, 5), 30)
            if deadline is not None:
                backoff_seconds = min(
                    backoff_seconds,
                    deadline.require_timeout_before(RESEARCH_CUTOFF_SECONDS, stage="web_search retry"),
                )
            await asyncio.sleep(backoff_seconds)
            continue

        retained_by_index: dict[int, dict[str, object]] = {}
        retained_indices: set[int] = set()
        visible_text_by_index: dict[int, tuple[str, ...]] = {}
        for index, item in enumerate(result.response.data):
            candidate: dict[str, object] = {
                "excerpts": [item.snippet] if item.snippet is not None else [],
                "title": item.title,
                "url": item.link,
            }
            searchable = json.dumps(candidate, ensure_ascii=False, sort_keys=True)
            if _contamination_hit(searchable) is not None:
                continue
            retained_by_index[index] = candidate
            retained_indices.add(index)
            visible_text_by_index[index] = tuple(
                text for text in (item.title, item.snippet) if isinstance(text, str) and text
            )
            top_level_url = _admissible_url(item.link)
            if top_level_url is not None:
                allowed_urls.add(top_level_url)
            allowed_urls.update(_visible_child_urls(item.title, item.snippet))
        observed = ledger.capture(
            result,
            retained_indices=retained_indices,
            visible_text_by_index=visible_text_by_index,
        )
        retained: list[dict[str, object]] = []
        for index, candidate in retained_by_index.items():
            evidence_candidate = observed.get(index)
            if evidence_candidate is not None:
                candidate["excerpts"] = [
                    f"[evidence {number}] {evidence_candidate.note[segment.start:segment.end]}"
                    for number, segment in ledger.numbered_segments(evidence_candidate)
                ]
            retained.append(candidate)
        return json.dumps({"results": retained}, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


async def _fetch(
    url: str,
    allowed_urls: set[str],
    ledger: EvidenceLedger,
    deadline: ExecutionDeadline | None = None,
    *,
    page_question: str | None = None,
    page_reader_cache: dict[tuple[str, str], PageReadResult] | None = None,
) -> str:
    normalized_url = _normalized_url(url)
    if normalized_url not in allowed_urls:
        return (
            f"<web_fetch><url>{url}</url><error>URL was not returned or literally shown by an earlier web_search "
            "call in this task.</error></web_fetch>"
        )
    if deadline is not None and not deadline.research_open():
        _log_deadline_event("research_tool_skipped_at_deadline", deadline, tool="web_fetch")
        return (
            f"<web_fetch><url>{url}</url>"
            "<error>The wall-clock research deadline has been reached.</error></web_fetch>"
        )
    citable_result: object | None = None
    visible_texts: tuple[str, ...] | None = None
    page_read: PageReadResult | None = None
    timeout_seconds = FETCH_TIMEOUT_SECONDS
    if deadline is not None:
        timeout_seconds = min(
            timeout_seconds,
            deadline.require_timeout_before(RESEARCH_CUTOFF_SECONDS, stage="web_fetch"),
        )
    try:
        result = await _await_before_stage_cutoff(
            fetch_page(
                url,
                provider="parallel",
                provider_extra={"full_content": True},
                timeout=timeout_seconds,
            ),
            timeout_seconds=timeout_seconds,
        )
        if len(result.response.data) != 1:
            raise RuntimeError("fetch_page did not return exactly one page")
        body = result.response.data[0].content
        if _contamination_hit(body) is not None:
            return (
                f"<web_fetch><url>{url}</url><error>Fetched text was removed by the benchmark contamination "
                "filter.</error></web_fetch>"
            )
        if len(body) > MAX_FETCH_CONTENT_CHARS and page_question is not None and deadline is not None:
            cache_key = (normalized_url, hashlib.sha256(body.encode("utf-8")).hexdigest())
            if page_reader_cache is not None:
                page_read = page_reader_cache.get(cache_key)
            if page_read is None:
                page_read = await _read_large_page(
                    question=page_question,
                    url=url,
                    body=body,
                    deadline=deadline,
                )
                if page_reader_cache is not None:
                    page_reader_cache[cache_key] = page_read
            visible_texts = page_read.selected_texts
        else:
            visible_texts = _visible_fetch_texts(body)
        allowed_urls.update(_visible_child_urls(*visible_texts))
        citable_result = result
    except StageDeadlineElapsedError as error:
        if deadline is None:
            raise
        _log_deadline_event("research_tool_timed_out_at_deadline", deadline, tool="web_fetch")
        raw_content = (
            f"<web_fetch><url>{url}</url><error>{_truncate_middle(str(error), MAX_FETCH_CONTENT_CHARS)}</error>"
            "</web_fetch>"
        )
    except Exception as error:
        raw_content = (
            f"<web_fetch><url>{url}</url><error>{_truncate_middle(str(error), MAX_FETCH_CONTENT_CHARS)}</error>"
            "</web_fetch>"
        )
    if citable_result is None or visible_texts is None:
        return raw_content
    observed = ledger.capture(
        citable_result,
        retained_indices={0},
        visible_text_by_index={0: visible_texts},
    )
    candidate = observed.get(0)
    evidence = ""
    if candidate is not None:
        evidence = "".join(
            f'<evidence number="{number}">{candidate.note[segment.start:segment.end]}</evidence>'
            for number, segment in ledger.numbered_segments(candidate)
        )
    if page_read is None:
        return f"<web_fetch><url>{url}</url><body>{evidence}</body></web_fetch>"
    findings = page_read.page_findings
    if candidate is not None and findings.strip():
        support_number = ledger.register_support_set(candidate)
        findings = (
            f'<page_findings evidence_number="{support_number}">{findings}</page_findings>'
            "<citation_instruction>Cite the page_findings once with its evidence number. That one number already "
            "represents every selected original passage; do not copy the body evidence numbers.</citation_instruction>"
        )
    else:
        findings = f"<page_findings>{findings}</page_findings>"
    return (
        f"<web_fetch><url>{url}</url>"
        f"{findings}"
        f"<missing_information>{page_read.missing_information}</missing_information>"
        f"<body>{evidence}</body></web_fetch>"
    )


async def _execute_tool_calls(
    tool_calls: Sequence[LlmMessageToolCall] | None,
    allowed_urls: set[str],
    ledger: EvidenceLedger,
    *,
    allow_research: bool = True,
    deadline: ExecutionDeadline | None = None,
) -> tuple[list[dict[str, object]], str | None]:
    calls = list(tool_calls or ())
    finish_names = [call.name for call in calls if call.name == "finish"]
    reject_finish = len(finish_names) > 1
    ordered_calls = sorted(calls, key=lambda call: call.name == "finish")
    tool_messages: list[dict[str, object]] = []
    finish_answer: str | None = None

    for call in ordered_calls:
        research_open = allow_research and (deadline is None or deadline.research_open())
        if reject_finish and call.name == "finish":
            unique_names = sorted(set(finish_names))
            content = (
                f"Cannot call finish tool '{call.name}': multiple finish tools ({unique_names}) were called in the "
                "same turn. Only one finish tool may be called per turn — retry with a single finish tool call."
            )
        elif call.name in {"web_search", "web_fetch"} and not research_open:
            content = (
                "Research phase ended by the turn or wall-clock limit. "
                "Call finish with the best supported answer."
            )
        elif call.name == "web_search":
            query = _single_string_argument(call.arguments, field="query", max_length=200)
            content = (
                "Tool arguments are not valid"
                if query is None
                else await _search(query, allowed_urls, ledger, deadline)
            )
        elif call.name == "web_fetch":
            url = _single_string_argument(call.arguments, field="url")
            content = (
                "Tool arguments are not valid"
                if url is None
                else await _fetch(url, allowed_urls, ledger, deadline)
            )
        elif call.name == "finish":
            answer = _single_string_argument(call.arguments, field="answer")
            if answer is None:
                content = "Tool arguments are not valid"
            else:
                content = "Final answer proposed for Harnyx contract validation."
                finish_answer = answer
        else:
            content = f"{call.name} is not a valid tool"
        tool_messages.append(_tool_result_message(call, content))
    return tool_messages, finish_answer


async def _generate(
    messages: list[dict[str, object]],
    *,
    tools: list[dict[str, object]],
    timeout_seconds: float | None = None,
) -> tuple[LlmChoiceMessage, LlmUsage]:
    if timeout_seconds is None:
        result = await llm_chat(
            provider="openrouter",
            model=_BASE_MODEL,
            messages=messages,
            temperature=0.6,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            tools=tools or None,
            tool_choice="auto" if tools else None,
            thinking={"enabled": True, "effort": "medium"},
            provider_extra=None,
        )
    else:
        result = await _await_before_stage_cutoff(
            llm_chat(
                provider="openrouter",
                model=_BASE_MODEL,
                messages=messages,
                temperature=0.6,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                tools=tools or None,
                tool_choice="auto" if tools else None,
                thinking={"enabled": True, "effort": "medium"},
                provider_extra=None,
                timeout=timeout_seconds,
            ),
            timeout_seconds=timeout_seconds,
        )
    if not result.response.choices:
        raise RuntimeError("LLM response contained no choices")
    choice = result.response.choices[0]
    if choice.finish_reason in ("max_tokens", "length"):
        raise RuntimeError("LLM exhausted the configured output token limit")
    return choice.message, result.response.usage


def _total_tokens(usage: LlmUsage) -> int:
    if usage.total_tokens is not None:
        return usage.total_tokens
    return (usage.prompt_tokens or 0) + (usage.completion_tokens or 0) + (usage.reasoning_tokens or 0)


async def _summarize(
    messages: list[dict[str, object]],
    *,
    deadline: ExecutionDeadline | None = None,
) -> list[dict[str, object]]:
    text_only_prompt = f"{MESSAGE_SUMMARIZER}\n\n{MESSAGE_SUMMARIZER_TEXT_ONLY}"
    tool_docs = "\n".join(
        f"- {tool['function']['name']}: {tool['function']['description']}" for tool in TOOLS
    )
    no_tools_prompt = (
        f"{text_only_prompt}\n\nTools are disabled for this response. For reference, the tools available earlier in "
        f"the conversation were:\n{tool_docs}"
    )
    attempts = (
        (MESSAGE_SUMMARIZER, TOOLS),
        (text_only_prompt, TOOLS),
        (no_tools_prompt, []),
    )
    summary: str | None = None
    for prompt, tools in attempts:
        response_message, _usage = await _generate(
            [*messages, {"role": "user", "content": prompt}],
            tools=tools,
            timeout_seconds=(
                None
                if deadline is None
                else deadline.require_timeout_before(
                    RESEARCH_CUTOFF_SECONDS,
                    stage="context summarization",
                )
            ),
        )
        summary = _assistant_text(response_message)
        if summary is not None:
            break
    if summary is None:
        raise RuntimeError("Summarizer response contained no text blocks; cannot summarize context")

    # This runner always starts with exactly one system message and one user task.
    # Stirrup preserves those two messages and replaces every prior summary/turn.
    task_context = messages[:2]
    return [
        *task_context,
        {"role": "user", "content": MESSAGE_SUMMARIZER_BRIDGE.format(summary=summary)},
        {"role": "user", "content": "Got it, thanks!"},
    ]


async def _run_stirrup_answer_path(task: str, ledger: EvidenceLedger) -> str:
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    allowed_urls: set[str] = set()

    for accepted_turn in range(1, MAX_TURNS + 1):
        completed_turns = accepted_turn - 1
        if MAX_TURNS - completed_turns <= TURNS_REMAINING_WARNING_THRESHOLD and completed_turns != 0:
            remaining = MAX_TURNS - completed_turns
            if remaining == 1:
                warning = "This is the last turn. Please finish the task by calling a finish tool."
            else:
                warning = (
                    f"You have {remaining} turns remaining to complete the task. Please continue. Remember you will "
                    "need a separate turn to call a finish tool."
                )
            messages.append({"role": "user", "content": warning})

        response_message, usage = await _generate(messages, tools=TOOLS)
        assistant_message = _assistant_input_message(response_message)
        tool_messages, finish_answer = await _execute_tool_calls(response_message.tool_calls, allowed_urls, ledger)
        messages.extend([assistant_message, *tool_messages])
        if finish_answer is not None:
            return finish_answer.strip()

        if (
            _total_tokens(usage) / CONTEXT_WINDOW_TOKENS >= CONTEXT_SUMMARIZATION_CUTOFF
            and accepted_turn != MAX_TURNS
        ):
            messages = await _summarize(messages)

        next_turn_will_show_warning = MAX_TURNS - accepted_turn <= TURNS_REMAINING_WARNING_THRESHOLD
        if not tool_messages and not next_turn_will_show_warning:
            messages.append({"role": "user", "content": "Please continue the task"})

    raise RuntimeError("Maximum number of turns reached without a successful finish call")


async def _run_answer_only(task: str) -> str:
    """Retain an offline control surface for the frozen answer-only contract."""

    return await _run_stirrup_answer_path(task, EvidenceLedger())


class FinishOutputError(ValueError):
    pass


EVIDENCE_MARKER = re.compile(r"\[\[(\d+)\]\]")


def _harnyx_finish_tool(query: Query) -> dict[str, object]:
    note_schema: dict[str, object] = {
        "type": "string",
        "maxLength": 80000,
        "description": (
            "Optional public explanation. Omit this field when no note is useful. Cite supported factual claims "
            "with the same [[N]] evidence markers used in prose. Do not repeat the answer or expose private reasoning."
        ),
    }
    if query.output_schema is None:
        properties: dict[str, object] = {
            "answer": {
                "type": "string",
                "minLength": 1,
                "maxLength": 80000,
                "description": (
                    "The complete final prose answer. Immediately after each supported claim, write [[N]], where N "
                    "is an evidence number shown by search or fetch. Use only shown numbers. When page_findings has "
                    "an evidence_number, cite that one number once for the finding; it already represents all selected "
                    "original passages. Never copy the body's evidence numbers to reproduce that support set. Write the "
                    "answer once; do not add a separate sources list merely to carry citations."
                ),
            },
            "note": note_schema,
        }
        required = ["answer"]
        description = (
            "Submit the final prose answer and end the task. Good: 'The value is 12.[[3]]'. Bad: an unknown "
            "marker, an uncited source list, copied evidence, or prose outside this tool call."
        )
    else:
        properties = {
            "output": query.output_schema,
            "output_evidence": {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_CITATION_SEGMENTS,
                "items": {"type": "integer", "minimum": 1},
                "description": (
                    "Evidence numbers shown by search or fetch that directly support the material output values. "
                    "A page_findings evidence_number already represents all selected original passages; include that one "
                    "number once instead of copying its body evidence numbers. Order and duplicates do not matter."
                ),
            },
            "note": note_schema,
        }
        required = ["output", "output_evidence"]
        description = (
            "Submit the requested structured output and end the task. Put every required answer value directly in "
            "output, cite it through output_evidence, and do not create a separate prose answer."
        )
    return {
        "type": "function",
        "function": {
            "name": "finish",
            "description": description,
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": properties,
                "required": required,
            },
        },
    }


def _harnyx_tools(query: Query) -> list[dict[str, object]]:
    return [WEB_SEARCH_TOOL, WEB_FETCH_TOOL, _harnyx_finish_tool(query)]


def _marker_numbers(text: str, *, label: str) -> list[int]:
    without_valid_markers = EVIDENCE_MARKER.sub("", text)
    if "[[" in without_valid_markers or "]]" in without_valid_markers:
        raise FinishOutputError(f"{label} contains a malformed evidence marker; use exact [[N]] syntax")
    return [int(match.group(1)) for match in EVIDENCE_MARKER.finditer(text)]


def _missing_evidence_message(*, field: str, ledger: EvidenceLedger) -> str:
    support_numbers = ledger.support_set_numbers
    if not support_numbers:
        if field == "finish answer":
            return "finish answer must include at least one shown [[N]] evidence marker"
        return "output_evidence must include at least one shown evidence number"
    rendered = ", ".join(str(number) for number in support_numbers)
    return (
        f"{field} has no evidence number. Cite each claimed page finding with its shown page_findings "
        f"evidence_number. The available page-finding numbers are {rendered}; each already represents all selected "
        "original passages, so do not copy the body evidence numbers."
    )


def _required_evidence_selection(
    evidence_number: int,
    ledger: EvidenceLedger,
) -> EvidenceSelection:
    selection = ledger.selection_for_evidence_number(evidence_number)
    if selection is None:
        raise FinishOutputError(f"selected unobserved evidence number {evidence_number}")
    return selection


def _citation_projection(
    evidence_numbers: Sequence[int],
    ledger: EvidenceLedger,
) -> tuple[list[CitationRef], dict[int, int]]:
    candidates = {candidate.candidate_id: candidate for candidate in ledger.candidates}
    candidate_order: list[int] = []
    segment_ids_by_candidate: dict[int, set[int]] = {}
    selection_by_number: dict[int, EvidenceSelection] = {}
    for evidence_number in evidence_numbers:
        selection = _required_evidence_selection(evidence_number, ledger)
        candidate_id = selection.candidate_id
        selection_by_number[evidence_number] = selection
        if candidate_id not in segment_ids_by_candidate:
            candidate_order.append(candidate_id)
            segment_ids_by_candidate[candidate_id] = set()
        segment_ids_by_candidate[candidate_id].update(selection.segment_ids)
    if len(candidate_order) > MAX_CITATION_REFS:
        raise FinishOutputError("selected evidence exceeds the public 200-citation limit")

    citation_numbers_by_candidate: dict[int, int] = {}
    citations: list[CitationRef] = []
    segment_count = 0
    evidence_chars = 0
    for candidate_id in candidate_order:
        candidate = candidates[candidate_id]
        segments = {segment.segment_id: segment for segment in candidate.segments}
        selected_ranges = [
            (segments[segment_id].start, segments[segment_id].end)
            for segment_id in sorted(segment_ids_by_candidate[candidate_id])
        ]
        merged_ranges = _merge_ranges(selected_ranges)
        segment_count += len(merged_ranges)
        evidence_chars += sum(end - start for start, end in merged_ranges)
        citation_number = len(citations) + 1
        citation_numbers_by_candidate[candidate_id] = citation_number
        citations.append(
            CitationRef(
                receipt_id=candidate.receipt_id,
                result_id=candidate.result_id,
                slices=[CitationSlice(start=start, end=end) for start, end in merged_ranges],
            )
        )
    if segment_count > MAX_CITATION_SEGMENTS:
        raise FinishOutputError("selected evidence exceeds the public 400-segment limit")
    if evidence_chars > MAX_CITATION_EVIDENCE_CHARS:
        raise FinishOutputError("selected evidence exceeds the public 120000-character limit")
    public_number_by_evidence = {
        evidence_number: citation_numbers_by_candidate[selection.candidate_id]
        for evidence_number, selection in selection_by_number.items()
    }
    return citations, public_number_by_evidence


def _renumber_markers(text: str, public_number_by_evidence: dict[int, int]) -> str:
    rewritten = EVIDENCE_MARKER.sub(
        lambda match: f"[[{public_number_by_evidence[int(match.group(1))]}]]",
        text,
    )
    return re.sub(r"(\[\[\d+\]\])(?:\1)+", r"\1", rewritten)


def _finish_response(query: Query, arguments: str, ledger: EvidenceLedger) -> Response:
    payload = _parse_object(arguments)
    if payload is None:
        raise FinishOutputError("finish arguments are not a JSON object")
    required_keys = {"answer"} if query.output_schema is None else {"output", "output_evidence"}
    allowed_keys = {*required_keys, "note"}
    if not required_keys.issubset(payload) or not set(payload).issubset(allowed_keys):
        raise FinishOutputError("finish arguments do not match the task-specific response contract")
    note = payload.get("note", "")
    if not isinstance(note, str):
        raise FinishOutputError("finish note must be a string when provided")
    note_numbers = _marker_numbers(note, label="finish note")

    if query.output_schema is None:
        answer = payload["answer"]
        if not isinstance(answer, str) or not answer.strip():
            raise FinishOutputError("finish answer must be non-blank prose")
        answer_numbers = _marker_numbers(answer, label="finish answer")
        if not answer_numbers:
            raise FinishOutputError(_missing_evidence_message(field="finish answer", ledger=ledger))
        citations, public_numbers = _citation_projection([*answer_numbers, *note_numbers], ledger)
        try:
            return Response(
                text=_renumber_markers(answer, public_numbers),
                note=_renumber_markers(note, public_numbers) if note.strip() else None,
                citations=citations or None,
            )
        except ValueError as error:
            raise FinishOutputError(f"public response violates the Harnyx contract: {error}") from error

    output_evidence = payload["output_evidence"]
    if not isinstance(output_evidence, list) or any(
        not isinstance(number, int) or isinstance(number, bool) for number in output_evidence
    ):
        raise FinishOutputError("output_evidence must be an array of evidence numbers")
    if not output_evidence:
        raise FinishOutputError(_missing_evidence_message(field="output_evidence", ledger=ledger))
    from harnyx_miner_sdk.structured_output import validate_output_against_schema

    try:
        validate_output_against_schema(payload["output"], query.output_schema)
    except ValueError as error:
        raise FinishOutputError(f"structured output violates the supplied schema: {error}") from error
    citations, public_numbers = _citation_projection([*output_evidence, *note_numbers], ledger)
    try:
        return Response(
            output=payload["output"],
            note=_renumber_markers(note, public_numbers) if note.strip() else None,
            citations=citations or None,
        )
    except ValueError as error:
        raise FinishOutputError(f"public response violates the Harnyx contract: {error}") from error


def _recover_plain_finalization_response(
    query: Query,
    message: LlmChoiceMessage,
    ledger: EvidenceLedger,
    *,
    allow_research: bool,
) -> Response | None:
    if allow_research or message.tool_calls:
        return None
    if query.output_schema is not None:
        raise FinishOutputError("structured task must call finish with output and output_evidence")
    answer = _assistant_text(message)
    if answer is None or not answer.strip():
        raise FinishOutputError("finalization response contained neither a finish call nor a plain answer")
    return _finish_response(query, json.dumps({"answer": answer}), ledger)


async def _execute_harnyx_tool_calls(
    tool_calls: Sequence[LlmMessageToolCall] | None,
    allowed_urls: set[str],
    ledger: EvidenceLedger,
    *,
    query: Query,
    allow_research: bool,
    deadline: ExecutionDeadline | None = None,
    page_reader_cache: dict[tuple[str, str], PageReadResult] | None = None,
) -> tuple[list[dict[str, object]], Response | None]:
    calls = list(tool_calls or ())
    finish_names = [call.name for call in calls if call.name == "finish"]
    reject_finish = len(finish_names) > 1
    ordered_calls = sorted(calls, key=lambda call: call.name == "finish")
    tool_messages: list[dict[str, object]] = []
    finish_response: Response | None = None

    for call in ordered_calls:
        research_open = allow_research and (deadline is None or deadline.research_open())
        if reject_finish and call.name == "finish":
            content = "Cannot call finish more than once in the same turn. Retry with one finish tool call."
        elif call.name in {"web_search", "web_fetch"} and not research_open:
            content = (
                "Research phase ended by the turn or wall-clock limit. "
                "Call finish with the best supported answer."
            )
        elif call.name == "web_search":
            search_query = _single_string_argument(call.arguments, field="query", max_length=200)
            content = (
                "Tool arguments are not valid"
                if search_query is None
                else await _search(search_query, allowed_urls, ledger, deadline)
            )
        elif call.name == "web_fetch":
            url = _single_string_argument(call.arguments, field="url")
            content = (
                "Tool arguments are not valid"
                if url is None
                else await _fetch(
                    url,
                    allowed_urls,
                    ledger,
                    deadline,
                    page_question=query.text,
                    page_reader_cache=page_reader_cache,
                )
            )
        elif call.name == "finish":
            try:
                finish_response = _finish_response(query, call.arguments, ledger)
            except FinishOutputError as error:
                content = f"Final answer rejected by Harnyx contract validation: {error}"
            else:
                content = "Final answer accepted."
        else:
            content = f"{call.name} is not a valid tool"
        tool_messages.append(_tool_result_message(call, content))
    return tool_messages, finish_response


FINALIZATION_PROMPT = """The research phase is complete. Do not search or fetch again. Call finish now with the best
complete answer. For a plain task, write normal prose and put each shown [[N]] evidence number directly after the claim
it supports. When page_findings has an evidence_number, cite that one number once; it already represents every selected
original passage, so never copy the body evidence numbers. For a structured task, fill every required output field and
list its supporting evidence numbers. Use an optional note only when a short evidence-backed supplement is useful."""

DEADLINE_FINALIZATION_PROMPT =DEADLINE_FINALIZATION_PROMPT = """The wall-clock research deadline has been reached. Do not search or fetch again.
Use only the information already in the conversation and call finish now with the best complete answer. The proposed
answer must contain every value needed by the user's requested output before Harnyx can accept it."""

RECOVERY_PROMPT = """This is the single recovery turn and the final turn. Research tools remain disabled. Use the
contract feedback from the rejected finish attempt and the information already in the conversation to call finish once
with a corrected, complete answer."""


# ---- v230-2-fdlq ----
# Added: fallback model lane, deterministic finish floor, list-first roster directive, figure coverage audit
# Ordinary successful path:
#   query -> answer -> _run_harnyx_answer_path -> _roster_directive -> _generate (+_generate_fallback on failure) -> _execute_harnyx_tool_calls -> _finish_response -> _figure_gaps -> _deterministic_finish (floor) -> Response


# ---------------------------------------------------------------------------
# Added-stage helpers.
# ---------------------------------------------------------------------------

_ASK_CUE_RE = re.compile(
    r"\b(which|what|who|whom|whose|when|where|how many|how much|name the|"
    r"list (?:all|the|every|each)|identify|give the)\b", re.I)
_SENT_SPLIT_RE = re.compile(r"(?<=[.?!])\s+")
_NAMED_ENTITY_RE = re.compile(
    r"[A-Z][A-Za-z0-9&'\-]+(?:\s+[A-Z][A-Za-z0-9&'\-]+){0,3}")
_ENTITY_SPLIT_RE = re.compile(r"\s+(?:and|&|vs\.?|versus|or)\s+", re.I)
_ENTITY_STOP = {"The", "This", "That", "What", "Which", "Who", "When", "Where",
                "How", "Why", "List", "Name", "Give", "Find", "In", "Of", "For",
                "Is", "Are", "Was", "Were", "Does", "Do", "Did", "According",
                "Please", "Using", "Only"}
_FIGURE_RE = re.compile(r"\d[\d,]*(?:\.\d+)?%?")
_SET_CUE_RE = re.compile(
    r"\b(which|what|list|name)\b[^.?!]{0,80}\b(all|every|each|both|"
    r"distributors|countries|companies|films|members|winners|those)\b", re.I)


def _ask_clause(text: str) -> str:
    """The clause that actually asks something.

    These tasks characteristically open with premise decoration and put the ask
    last, so slicing the head probes the decoration instead of the question.
    """
    body = " ".join((text or "").split())
    if not body:
        return ""
    sentences = [s for s in _SENT_SPLIT_RE.split(body) if s.strip()]
    if not sentences:
        return body
    ask = ""
    for sentence in sentences:
        if _ASK_CUE_RE.search(sentence):
            ask = sentence
    return ask or sentences[-1]


def _named_entities(text: str, limit: int = 6) -> list[str]:
    """Capitalized subjects the task names, with connectors split."""
    found: list[str] = []
    seen: set[str] = set()
    for match in _NAMED_ENTITY_RE.finditer(text or ""):
        for piece in _ENTITY_SPLIT_RE.split(match.group(0)):
            words = piece.split()
            while words and words[0] in _ENTITY_STOP:
                words = words[1:]
            name = " ".join(words).strip(" ,.'-")
            key = name.casefold()
            if len(name) < 4 or key in seen:
                continue
            seen.add(key)
            found.append(name)
            if len(found) >= limit:
                return found
    return found


def _selected_text(ledger: "EvidenceLedger", numbers) -> str:
    """Concatenated source text behind a set of evidence numbers.

    This is what the judge actually sees. Reading the ledger's raw candidate
    text instead would repeat the mistake these stages exist to prevent.
    """
    candidates = {c.candidate_id: c for c in ledger.candidates}
    chunks: list[str] = []
    for number in numbers:
        selection = ledger.selection_for_evidence_number(int(number))
        if selection is None:
            continue
        candidate = candidates.get(selection.candidate_id)
        if candidate is None:
            continue
        segments = {s.segment_id: s for s in candidate.segments}
        for segment_id in selection.segment_ids:
            segment = segments.get(segment_id)
            if segment is not None:
                chunks.append(getattr(segment, "text", "") or "")
    return "\n".join(chunks)


def _selected_urls(ledger: "EvidenceLedger", numbers) -> list[str]:
    candidates = {c.candidate_id: c for c in ledger.candidates}
    urls: list[str] = []
    for number in numbers:
        selection = ledger.selection_for_evidence_number(int(number))
        if selection is None:
            continue
        candidate = candidates.get(selection.candidate_id)
        url = getattr(candidate, "url", "") if candidate else ""
        if url and url not in urls:
            urls.append(url)
    return urls


def _answer_and_numbers(response: "Response") -> tuple:
    text = (getattr(response, "text", None) or "") + " " + (getattr(response, "note", None) or "")
    return text, [int(m.group(1)) for m in EVIDENCE_MARKER.finditer(text)]


FALLBACK_MODEL = "z-ai/glm-5.2"
FALLBACK_MAX_OUTPUT_TOKENS = 32_000


async def _generate_fallback(
    messages: list[dict[str, object]],
    *,
    tools: list[dict[str, object]],
    timeout_seconds: float | None,
):
    """Second lane. The base has exactly one model, pinned to a single upstream
    with allow_fallbacks False and no alternative anywhere -- so one 429 ends
    the run with RuntimeError and a zero. This lane keeps fallbacks ON on
    purpose: at this point the pinned upstream has already failed, and routing
    freedom is worth more than upstream affinity."""
    # Two explicit calls rather than **{...}: the validator rejects expanded
    # keyword arguments (invalid_script_payload / expanded_keywords). The base's
    # own _generate branches the same way for the same reason.
    if timeout_seconds is None:
        result = await llm_chat(
            provider="openrouter",
            model=FALLBACK_MODEL,
            messages=messages,
            temperature=0.4,
            max_output_tokens=FALLBACK_MAX_OUTPUT_TOKENS,
            tools=tools or None,
            tool_choice="auto" if tools else None,
            thinking={"enabled": True, "effort": "low"},
            provider_extra=None,
        )
    else:
        result = await llm_chat(
            provider="openrouter",
            model=FALLBACK_MODEL,
            messages=messages,
            temperature=0.4,
            max_output_tokens=FALLBACK_MAX_OUTPUT_TOKENS,
            tools=tools or None,
            tool_choice="auto" if tools else None,
            thinking={"enabled": True, "effort": "low"},
            provider_extra=None,
            timeout=timeout_seconds,
        )
    if not result.response.choices:
        raise RuntimeError("fallback lane returned no choices")
    return result.response.choices[0].message, result.response.usage


FLOOR_MAX_EVIDENCE = 6
FLOOR_MIN_CHARS = 60


def _deterministic_finish(query: "Query", ledger: "EvidenceLedger"):
    """Last-resort answer built from evidence already held.

    The base ends `raise RuntimeError(...)` when the reserved finish turns are
    spent -- a total zero even though the ledger is usually full of captured,
    citable evidence. This builds a contract-valid finish from what is already
    there: real [[N]] markers over real support-set numbers, so it survives
    _finish_response's validation rather than bypassing it.
    """
    numbers = list(ledger.support_set_numbers)[:FLOOR_MAX_EVIDENCE]
    if not numbers:
        return None
    lines = ["Best-supported findings for this task, from the evidence gathered:"]
    for number in numbers:
        snippet = " ".join(_selected_text(ledger, [number]).split())[:220]
        if not snippet:
            continue
        lines.append(f"- {snippet} [[{number}]]")
    if len(lines) < 2:
        return None
    answer = "\n".join(lines)
    if len(answer) < FLOOR_MIN_CHARS:
        return None
    try:
        if query.output_schema is not None:
            return _finish_response(
                query, json.dumps({"output": answer, "output_evidence": numbers}), ledger)
        return _finish_response(query, json.dumps({"answer": answer}), ledger)
    except Exception:
        return None


def _needs_roster(text: str) -> bool:
    return bool(_SET_CUE_RE.search(text or ""))


def _roster_directive(text: str) -> str:
    """Opening directive for set tasks: get the pool from ONE list.

    Assembling a pool from per-member lookups is how a run ships 3 of 6
    qualifiers -- the members never searched for are invisible. This fires
    before the first turn, so it shapes the first retrieval rather than
    repairing the last.
    """
    ask = _ask_clause(text)
    return ("SET TASK. Your FIRST retrieval should hunt the authoritative "
            "roster that enumerates the WHOLE pool -- search it AS a list "
            "(\"<pool subject> list\", \"<pool subject> table\") and read that "
            "page, then verify each member against every stated condition. "
            "Give every member its own line with its own evidence marker, "
            "including the members you rule OUT. The ask is: " + ask[:240])


MAX_FIGURE_FLAGS = 4
MIN_FIGURE_CHARS = 2


def _figure_gaps(response: "Response", ledger: "EvidenceLedger") -> list:
    """Figures asserted by the finish that no cited passage states.

    The judge credits a claim only when the CITED SLICE contains the text
    stating it. Checking the raw candidate text instead would pass figures the
    judge never sees, which is precisely the failure this guards.
    """
    text, numbers = _answer_and_numbers(response)
    if not numbers:
        return []
    shown = _selected_text(ledger, numbers)
    shown_plain = shown.replace(",", "")
    gaps: list = []
    seen: set = set()
    for match in _FIGURE_RE.finditer(EVIDENCE_MARKER.sub(" ", text)):
        token = match.group(0)
        if len(token) < MIN_FIGURE_CHARS:
            continue
        plain = token.replace(",", "").rstrip("%")
        if plain in seen:
            continue
        seen.add(plain)
        if token not in shown and plain not in shown_plain:
            gaps.append(token)
        if len(gaps) >= MAX_FIGURE_FLAGS:
            break
    return gaps


def _figure_correction(gaps: list) -> str:
    return ("UNCITED FIGURES. These values appear in your answer but in none of "
            "the passages you cited: " + ", ".join(gaps)
            + ".\nEXEMPTION: a figure you DERIVED (a total, mean, share or "
            "difference) is legitimate -- keep it and show its inputs with "
            "their markers. Otherwise cite a shown evidence number whose "
            "passage prints it, or drop it. Then call finish again.")


async def _run_harnyx_answer_path(
    query: Query,
    ledger: EvidenceLedger,
    *,
    clock: Callable[[], float] = time.monotonic,
) -> Response:
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query.text},
    ]
    if _needs_roster(query.text or ""):
        messages.append({"role": "user",
                         "content": _roster_directive(query.text or "")})
    allowed_urls: set[str] = set()
    page_reader_cache: dict[tuple[str, str], PageReadResult] = {}
    deadline = ExecutionDeadline.start(clock=clock)
    finalization_attempts = 0
    finalization_started = False
    force_finalization = False
    _audit_done = False

    for accepted_turn in range(1, MAX_TURNS + 1):
        allow_research = (
            accepted_turn <= RESEARCH_TURNS
            and not force_finalization
            and not finalization_started
            and deadline.research_open()
        )
        if not allow_research:
            if finalization_attempts >= FINALIZATION_TURNS:
                break
            finalization_attempts += 1
            if not finalization_started:
                prompt = (
                    DEADLINE_FINALIZATION_PROMPT
                    if accepted_turn <= RESEARCH_TURNS
                    else FINALIZATION_PROMPT
                )
                messages.append({"role": "user", "content": prompt})
                finalization_started = True
                _log_deadline_event(
                    "finalization_started",
                    deadline,
                    cause="wall_clock" if accepted_turn <= RESEARCH_TURNS else "turn_limit",
                )
            elif finalization_attempts == FINALIZATION_TURNS:
                messages.append({"role": "user", "content": RECOVERY_PROMPT})
        else:
            completed_turns = accepted_turn - 1
            if MAX_TURNS - completed_turns <= TURNS_REMAINING_WARNING_THRESHOLD and completed_turns != 0:
                remaining = MAX_TURNS - completed_turns
                warning = (
                    f"You have {remaining} turns remaining to complete the task. Please continue. Remember you will "
                    "need a separate turn to call a finish tool."
                )
                messages.append({"role": "user", "content": warning})

        tools = _harnyx_tools(query) if allow_research else [_harnyx_finish_tool(query)]
        cutoff = RESEARCH_CUTOFF_SECONDS if allow_research else FINAL_ANSWER_CUTOFF_SECONDS
        try:
            timeout_seconds = deadline.require_timeout_before(cutoff, stage="answer generation")
            try:
                response_message, usage = await _generate(
                    messages,
                    tools=tools,
                    timeout_seconds=timeout_seconds,
                )
            except (StageDeadlineElapsedError, DeadlineExceededError):
                raise
            except Exception:
                # Single pinned upstream just failed (429 or transport).
                # Without this the run raises and scores zero.
                response_message, usage = await _generate_fallback(
                    messages,
                    tools=tools,
                    timeout_seconds=timeout_seconds,
                )
        except (StageDeadlineElapsedError, DeadlineExceededError):
            if allow_research:
                force_finalization = True
                _log_deadline_event("research_generation_stopped_at_deadline", deadline)
                continue
            raise DeadlineExceededError(
                "final answer generation reached its deadline before finish produced an answer"
            ) from None

        assistant_message = _assistant_input_message(response_message)
        tool_messages, finish_response = await _execute_harnyx_tool_calls(
            response_message.tool_calls,
            allowed_urls,
            ledger,
            query=query,
            allow_research=allow_research,
            deadline=deadline,
            page_reader_cache=page_reader_cache,
        )
        messages.extend([assistant_message, *tool_messages])
        if finish_response is not None:
            # Audit the finish BEFORE accepting it. Each check that
            # fires costs one corrective turn, and only one round is
            # allowed: the reserved finish turns are the last thing
            # standing between a partial answer and a RuntimeError.
            _fix = ""
            if not _audit_done:
                try:
                    _figs = _figure_gaps(finish_response, ledger)
                except Exception:
                    _figs = []
                if _figs and not _fix:
                    _fix = _figure_correction(_figs)
            if _fix and deadline.research_open():
                _audit_done = True
                messages.append({"role": "user", "content": _fix})
                continue
            return finish_response

        if not allow_research and not tool_messages:
            try:
                recovered_response = _recover_plain_finalization_response(
                    query,
                    response_message,
                    ledger,
                    allow_research=allow_research,
                )
            except FinishOutputError as error:
                _log_deadline_event(
                    "plain_finalization_rejected",
                    deadline,
                    reason=str(error),
                )
                messages.append(
                    {
                        "role": "user",
                        "content": f"Final answer rejected by Harnyx contract validation: {error}",
                    }
                )
            else:
                if recovered_response is not None:
                    _log_deadline_event("plain_finalization_recovered", deadline)
                    return recovered_response

        if (
            allow_research
            and deadline.research_open()
            and _total_tokens(usage) / CONTEXT_WINDOW_TOKENS >= CONTEXT_SUMMARIZATION_CUTOFF
            and accepted_turn < RESEARCH_TURNS
        ):
            try:
                messages = await _summarize(messages, deadline=deadline)
            except (StageDeadlineElapsedError, DeadlineExceededError):
                force_finalization = True
                _log_deadline_event("summarization_stopped_at_deadline", deadline)

        if not tool_messages and allow_research and deadline.research_open():
            messages.append({"role": "user", "content": "Please continue the task"})

    _floor = None
    try:
        _floor = _deterministic_finish(query, ledger)
    except Exception:
        _floor = None
    if _floor is not None:
        _log_deadline_event("deterministic_floor_used", deadline)
        return _floor
    raise RuntimeError("Reserved finish and recovery turns ended without an accepted Harnyx response")


async def _w4_baseline_query(query: Query) -> Response:
    ledger = EvidenceLedger()
    return await _run_harnyx_answer_path(query, ledger)


# --- w4 answer-contract wrapper (begin) ---
# The base artifact's `query` entrypoint is demoted to `_w4_baseline_query` and a
# new `query` coordinates three stages: answer-contract planning, baseline
# research, and contract verification with authority over the returned answer.
# The only contract with the demoted base is the platform ABI (`Query`,
# `Response`, `llm_chat`) plus NameError-guarded probes for optional base
# constants.

_W2_PLAN_TIMEOUT_SECONDS = 22.0
_W2_VERIFY_TIMEOUT_SECONDS = 28.0
_W2_REPAIR_TIMEOUT_SECONDS = 24.0
_W2_TAIL_RESERVE_SECONDS = 8.0
_W2_PLAN_TEMPERATURE = 0.1
_W2_VERIFY_TEMPERATURE = 0.12
_W2_MIN_REVISION_CHARS = 80
_W2_MIN_REVISION_RATIO = 0.6
_W2_MIN_ENTITY_CHARS = 3
_W2_MAX_CONTRACT_ITEMS = 6
_W2_DRAFT_PROMPT_CHARS = 6_000
_W2_DEFAULT_BUDGET_SECONDS = 235.0

_W2_LIST_MARKER_RE = re.compile(r"(?m)^[ \t]*[(\[]?\d{1,2}[.)\]][ \t]+")
_W2_FIGURE_RE = re.compile(r"\d+(?:[.,]\d+)*")
_W2_WORD_RE = re.compile(r"[A-Z][A-Za-z0-9&'’.\-]*")
_W2_CLAUSE_HEAD_CHARS = ".!?:;#*->|•"

_W2_PLAN_SYSTEM = (
    "You plan the acceptance criteria for a research answer before the research runs.\n"
    "Read the question and list what a complete, correct answer must contain.\n"
    "Reply with JSON only, no prose, in this exact shape:\n"
    '{"deliverable": "<one sentence naming what must be returned>", '
    '"required": ["<concrete element the answer must state>", ...], '
    '"pitfalls": ["<a specific way an answer to this question goes wrong>", ...]}\n'
    "Give at most six `required` entries and at most three `pitfalls`. "
    "Each entry must be concrete and checkable against a draft answer - name the "
    "quantity, entity, unit, date range, or enumeration that must appear. "
    "Never guess the answer itself; describe only what the answer must cover."
)

_W2_VERIFY_SYSTEM = (
    "You audit a draft research answer against an answer contract and repair it.\n"
    "The contract lists what the answer must contain. Check the draft against every "
    "entry and return the corrected answer.\n"
    "Rules:\n"
    "- Repair only concrete, verifiable gaps: a required element the draft never "
    "states, an internal contradiction, a requested unit or format the draft ignores.\n"
    "- Use only facts already present in the draft. Never introduce a fact, figure, "
    "name, or citation that the draft does not contain.\n"
    "- Every figure, quantity, date, unit, name, and citation marker the draft states "
    "stands as written. You may not drop one, round one, reword one, or swap one for a "
    "different value or a different entity. Your edits may only add.\n"
    "- The draft's own answer to the question is the answer. If you believe a different "
    "entity or value fits the question better, say so in one added clause and leave the "
    "draft's answer standing.\n"
    "- If a required element is genuinely absent from the draft's evidence, say so "
    "plainly in one clause rather than inventing it.\n"
    "- Preserve the draft's wording wherever it already satisfies the contract.\n"
    "- If the draft already satisfies the contract, return it unchanged.\n"
    "Return the full corrected answer text and nothing else - no preamble, no notes, "
    "no commentary about what you changed."
)

_W2_REPAIR_SYSTEM = (
    "You convert a research answer into the exact JSON object a caller's schema "
    "requires.\n"
    "Use only facts stated in the answer text. Do not invent values. If the answer "
    "does not supply a required field, use null for it.\n"
    "Reply with a single JSON object and nothing else."
)


class _W2AnswerContract:
    """The formal state object carried between the plan and verify stages."""

    def __init__(self, deliverable: str, required: list[str], pitfalls: list[str]) -> None:
        self.deliverable = deliverable
        self.required = required
        self.pitfalls = pitfalls

    def is_actionable(self) -> bool:
        return bool(self.deliverable or self.required)


def _w4_provider() -> str:
    """Resolve the base's LLM provider without globals(); the validator rejects it."""
    try:
        return LLM_PROVIDER
    except NameError:
        return "openrouter"


def _w4_model() -> str:
    try:
        return MODEL
    except NameError:
        return "z-ai/glm-5"


def _w4_total_budget_seconds() -> float:
    try:
        return float(TASK_TOTAL_BUDGET_SECONDS)
    except (NameError, TypeError, ValueError):
        return _W2_DEFAULT_BUDGET_SECONDS


def _w4_remaining(deadline: float) -> float:
    return deadline - perf_counter()


async def _w4_chat(messages: list[dict[str, object]], *, timeout: float, temperature: float) -> str:
    """One bounded LLM call on the platform ABI; empty string on any failure."""
    if timeout <= 0:
        return ""
    try:
        result = await llm_chat(
            provider=_w4_provider(), model=_w4_model(), messages=messages,
            temperature=temperature, timeout=timeout,
        )
    except Exception:
        return ""
    try:
        return (result.response.raw_text or "").strip()
    except Exception:
        return ""


def _w4_json_object(text: str) -> dict | None:
    """Tolerant extraction of the first JSON object in a model reply."""
    if not text:
        return None
    body = text.strip()
    if body.startswith("```"):
        body = body.split("```")[1] if "```" in body[3:] else body[3:]
        if body[:4].lower().startswith("json"):
            body = body[4:]
    start = body.find("{")
    end = body.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(body[start:end + 1])
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _w4_string_list(value: object, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    items = []
    for entry in value:
        if isinstance(entry, str) and entry.strip():
            items.append(entry.strip())
        if len(items) >= limit:
            break
    return items


def _w4_schema_hint(schema: object) -> str:
    """Render the caller's output schema for the planning prompt."""
    if schema is None:
        return ""
    try:
        rendered = json.dumps(schema, ensure_ascii=False)[:1_200]
    except (TypeError, ValueError):
        return ""
    return f"\n\nThe answer will be returned against this output schema:\n{rendered}"


async def _w4_build_answer_contract(
    question: str, schema: object, *, deadline: float,
) -> _W2AnswerContract | None:
    """Stage 1 - plan the acceptance criteria before the baseline research runs."""
    timeout = min(_W2_PLAN_TIMEOUT_SECONDS, _w4_remaining(deadline) - _W2_TAIL_RESERVE_SECONDS)
    messages = [
        {"role": "system", "content": _W2_PLAN_SYSTEM},
        {"role": "user", "content": f"Question:\n{question}{_w4_schema_hint(schema)}"},
    ]
    payload = _w4_json_object(await _w4_chat(
        messages, timeout=timeout, temperature=_W2_PLAN_TEMPERATURE,
    ))
    if payload is None:
        return None
    deliverable = payload.get("deliverable")
    contract = _W2AnswerContract(
        deliverable=deliverable.strip() if isinstance(deliverable, str) else "",
        required=_w4_string_list(payload.get("required"), _W2_MAX_CONTRACT_ITEMS),
        pitfalls=_w4_string_list(payload.get("pitfalls"), 3),
    )
    return contract if contract.is_actionable() else None


def _w4_contract_block(contract: _W2AnswerContract) -> str:
    """Render the contract as the audit checklist handed to the verify stage."""
    lines = []
    if contract.deliverable:
        lines.append(f"Deliverable: {contract.deliverable}")
    if contract.required:
        lines.append("The answer must state:")
        lines.extend(f"  - {item}" for item in contract.required)
    if contract.pitfalls:
        lines.append("Known ways this question is answered badly:")
        lines.extend(f"  - {item}" for item in contract.pitfalls)
    return "\n".join(lines)


def _w4_response_text(response: object) -> str:
    try:
        text = getattr(response, "text", None)
    except Exception:
        return ""
    return text.strip() if isinstance(text, str) else ""


def _w4_with_text(response: object, text: str) -> object:
    """Rebuild the response around the audited answer, carrying citations over.

    The platform accepts exactly one non-null answer field, so a response that
    already carries a structured `output` owns no text answer to override and is
    returned untouched.
    """
    if getattr(response, "output", None) is not None:
        return response
    citations = getattr(response, "citations", None)
    try:
        if citations:
            return Response(text=text, citations=citations)
        return Response(text=text)
    except Exception:
        return response


def _w4_normalize_figure(token: str) -> str:
    """One numeric literal reduced to the value it states, not how it is typed."""
    value = token.replace(",", "")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    return value or "0"


def _w4_figures(text: str) -> set:
    """Every quantity the text asserts, less the ordinals that only number a list."""
    body = _W2_LIST_MARKER_RE.sub(" ", text)
    found = set()
    for match in _W2_FIGURE_RE.finditer(body):
        found.add(_w4_normalize_figure(match.group(0)))
    return found


def _w4_entities(text: str) -> set:
    """Every named token the text asserts.

    A capitalized word that opens a sentence, a heading, or a bullet is
    capitalized by position rather than by being a name, so it is not counted;
    a real name almost always also occurs somewhere it did not open a clause.
    """
    found = set()
    for match in _W2_WORD_RE.finditer(text):
        cursor = match.start() - 1
        while cursor >= 0 and text[cursor] in " \t":
            cursor -= 1
        if cursor < 0 or text[cursor] == "\n" or text[cursor] in _W2_CLAUSE_HEAD_CHARS:
            continue
        word = match.group(0).strip(".-'’").lower()
        if len(word) >= _W2_MIN_ENTITY_CHARS:
            found.add(word)
    return found


def _w4_unmakes_draft(draft: str, revision: str) -> bool:
    """True when the revision fails to carry forward something the draft asserted."""
    if not _w4_figures(draft).issubset(_w4_figures(revision)):
        return True
    return not _w4_entities(draft).issubset(_w4_entities(revision))


def _w4_accept_revision(draft: str, revision: str) -> bool:
    """Keep the audited answer only when it adds to the draft without unmaking it.

    Length cannot tell a repair from a replacement: a revision that answers with
    a different entity, or restates a figure as a different figure, is exactly as
    long as one that fills a gap. The audited text is therefore accepted only
    when every concrete claim the draft asserted - each quantity, each named
    token - still stands in it. Additions are free; deletions and substitutions
    return the draft.
    """
    if not revision or revision == draft:
        return False
    if len(revision) < _W2_MIN_REVISION_CHARS:
        return False
    if len(revision) < len(draft) * _W2_MIN_REVISION_RATIO:
        return False
    return not _w4_unmakes_draft(draft, revision)


async def _w4_verify_against_contract(
    contract: _W2AnswerContract, question: str, draft: str, *, deadline: float,
) -> str:
    """Stage 3 - audit the draft against the contract and return the answer to deliver."""
    timeout = min(_W2_VERIFY_TIMEOUT_SECONDS, _w4_remaining(deadline) - _W2_TAIL_RESERVE_SECONDS)
    messages = [
        {"role": "system", "content": _W2_VERIFY_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\nAnswer contract:\n{_w4_contract_block(contract)}"
                f"\n\nDraft answer:\n{draft[:_W2_DRAFT_PROMPT_CHARS]}"
            ),
        },
    ]
    revision = await _w4_chat(messages, timeout=timeout, temperature=_W2_VERIFY_TEMPERATURE)
    return revision if _w4_accept_revision(draft, revision) else draft


def _w4_schema_property_names(schema: object) -> list[str]:
    if not isinstance(schema, dict):
        return []
    properties = schema.get("properties")
    return [key for key in properties] if isinstance(properties, dict) else []


def _w4_is_degenerate_output(output: object, schema: object) -> bool:
    """True when the base produced a structured payload the scorer will read as empty."""
    if output is None:
        return True
    if isinstance(output, (str, list, tuple, dict)) and len(output) == 0:
        return True
    if isinstance(output, dict):
        names = _w4_schema_property_names(schema)
        if names and not any(key in output for key in names):
            return True
        if all(value in (None, "", [], {}) for value in output.values()):
            return True
    return False


async def _w4_repair_structured_output(
    question: str, schema: object, response: object, *, deadline: float,
) -> object:
    """Repair-only ladder: a working structured payload is always returned untouched."""
    output = getattr(response, "output", None)
    if not _w4_is_degenerate_output(output, schema):
        return response
    draft = _w4_response_text(response)
    recovered = _w4_json_object(draft)
    if recovered is None:
        timeout = min(_W2_REPAIR_TIMEOUT_SECONDS, _w4_remaining(deadline) - 2.0)
        try:
            rendered = json.dumps(schema, ensure_ascii=False)[:1_500]
        except (TypeError, ValueError):
            rendered = ""
        messages = [
            {"role": "system", "content": _W2_REPAIR_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\nOutput schema:\n{rendered}"
                    f"\n\nAnswer text:\n{draft[:_W2_DRAFT_PROMPT_CHARS]}"
                ),
            },
        ]
        recovered = _w4_json_object(await _w4_chat(messages, timeout=timeout, temperature=0.0))
    if recovered is None or _w4_is_degenerate_output(recovered, schema):
        return response
    citations = getattr(response, "citations", None)
    try:
        if citations:
            return Response(output=recovered, citations=citations)
        return Response(output=recovered)
    except Exception:
        return response


async def _w4_research_or_salvage(query_input: Query) -> Response:
    """Stage 2 - the research stage, held so no failure inside it can escape.

    The demoted base entrypoint is foreign code: it raises whatever its own tool
    layer raises. A hosted tool call that overruns its own `timeout=` surfaces as
    `harnyx_commons.errors.ToolInvocationTimeoutError`, which subclasses
    RuntimeError directly and matches no guard the base installed for itself. Any
    such escape leaves `@entrypoint`, and the platform charges an escaping
    exception to the miner as MINER_UNHANDLED_EXCEPTION: the task scores 0 with
    no retry. Measured on `FB_526bfbe6_w2`, 1 of 3 replays (2026-08-09).

    The stage therefore always resolves to a Response the later stages can work
    on. A floor answer scores poorly; an escape scores zero and takes the whole
    task with it.
    """
    try:
        return await _w4_baseline_query(query_input)
    except Exception:
        return Response(text="No verifiable source-backed answer was reached for this question.")


@entrypoint("query")
async def query(query: Query) -> Response:
    """w4 contract wrapper: plan the answer contract, run the baseline, then verify.

    The baseline artifact's own entrypoint is demoted to `_w4_baseline_query` and
    runs as the research stage of this sequence. Contract planning runs on every
    ordinary request before the research starts, and the verification stage holds
    authority over the answer this entrypoint returns.
    """
    deadline = perf_counter() + _w4_total_budget_seconds()
    question = getattr(query, "text", "") or ""
    schema = getattr(query, "output_schema", None)

    contract = await _w4_build_answer_contract(question, schema, deadline=deadline)
    response = await _w4_research_or_salvage(query)

    if contract is not None:
        draft = _w4_response_text(response)
        if draft:
            audited = await _w4_verify_against_contract(
                contract, question, draft, deadline=deadline,
            )
            if audited != draft:
                response = _w4_with_text(response, audited)
    if schema is not None:
        response = await _w4_repair_structured_output(
            question, schema, response, deadline=deadline,
        )
    return response
# --- w4 answer-contract wrapper (end) ---
