"""Micro experiment: answer-first research with ranked retrieval views.

Hypothesis
==========
Query-ranked search windows preserve decisive passages without replaying each
full note, but one repeat still researched an exact value that could not change
the requested top-two answer. Trying to write the answer after each tool batch
should make the missing answer sentence, rather than an accumulating state DTO,
control the next action. Question/focus-ranked page windows should expose the
same useful regions without replaying generic head/middle/tail previews.

Experimental contract
=====================
1. GLM-5.2 writes a revisable expected answer and a compact verification brief.
2. The same model receives that brief in one persistent conversation.  It may
   search the web or read a page.  Independent calls from one turn run in
   parallel; tool responses are replayed in call order.
3. Search results are plain numbered evidence blocks with a 220-character head
   and one 700-character query-ranked window. Pages at most 6.5 KB are shown in
   full; larger pages expose a 3 KB head plus up to three question/focus-ranked
   3.6 KB windows. When the strongest matching Markdown heading falls at the end
   of a selected window and most of its section would be cut off, that window is
   aligned to the heading. For exact inventory work, ``find_on_page`` returns
   every raw record containing a literal string together with its Markdown
   section and table header. Fenced code is not treated as document structure,
   and overlapping spans are merged.
   The harness still stores every full result and citation identity; the model
   never manages VFS state or evidence DTOs.
4. A response with no tool calls is the final reader-facing answer.  It must cite
   observed private refs after the factual claims they support. A comma-separated
   group such as [S1, P2] is valid. If the final prose violates this mechanical
   contract, the same conversation receives the exact validation error and gets
   one tool-free correction attempt before the failure is surfaced.
5. GPT-OSS performs one bounded audit.  A material rejection is returned to the
   same research conversation for one repair; a second rejection fails loudly.
6. Each LLM boundary gets 40 seconds for its primary route and one 40-second
   model/provider fallback. Every fallback is logged; two failures surface.

Lexical ranking selects display spans; it does not accept, reject, summarize,
or alter evidence. The prompt changes stopping semantics without adding research
state. Models and audit behavior remain unchanged. This experiment does not
replace the active candidate, switch architecture, or impose an output-token
cap.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
from harnyx_miner_sdk.structured_output import validate_output_against_schema

SEARCH_PROVIDER = "parallel"
SEARCH_TIMEOUT = 10.0
FETCH_TIMEOUT = 15.0
LLM_TIMEOUT = 40.0
RESEARCH_FALLBACK_PROVIDER = "ai_gateway"
RESEARCH_FALLBACK_MODEL = "thinkingmachines/inkling"
STRUCTURED_FALLBACK_MODEL = "openai/gpt-oss-120b"
RESEARCH_TURN_CEILING = 15
MAX_PARALLEL_TOOL_CALLS = 8
SEARCH_RESULT_COUNT = 8
SEARCH_HEAD_CHARS = 220
SEARCH_WINDOW_CHARS = 700
SEARCH_WINDOW_STEP_CHARS = 250
PAGE_PLAIN_CHARS = 6_500
PAGE_HEAD_CHARS = 3_000
PAGE_WINDOW_CHARS = 3_600
PAGE_WINDOW_STEP_CHARS = 1_200
PAGE_WINDOWS = 3
MIN_HEADING_FOCUS_TERMS = 3
TOOL_TURN_PREVIEW_CHARS = 96_000
MIN_CITATION_SLICE_CHARS = 100
MAX_EVIDENCE_SEGMENTS = 400
MAX_TOTAL_EVIDENCE_CHARS = 120_000

logger = logging.getLogger("direct_research_loop")


def _bisect_right(values: list[int], target: int) -> int:
    low = 0
    high = len(values)
    while low < high:
        middle = (low + high) // 2
        if target < values[middle]:
            high = middle
        else:
            low = middle + 1
    return low

RESEARCH_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Search the web. Each result is automatically stored and returned with a private source ref. "
                "Use several independent calls in one turn when comparing sources or candidates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A focused search query that can change what you know.",
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_page",
            "description": (
                "Read relevant regions of a page when search excerpts do not expose the needed context. "
                "Give a short focus phrase describing the fact, row, heading, or boundary to find."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Exact URL returned by search."},
                    "focus": {
                        "type": "string",
                        "description": "Words or a short phrase identifying the needed passage.",
                    },
                },
                "required": ["url", "focus"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_on_page",
            "description": (
                "Find every raw record containing an exact name or value on one page. "
                "Returns each matching record once with its Markdown section and table header. "
                "Use this for complete inventories on long pages instead of repeatedly reading broad windows."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Exact URL returned by search."},
                    "text": {
                        "type": "string",
                        "description": "Single-line exact name or value to find, matched case-insensitively.",
                    },
                },
                "required": ["url", "text"],
                "additionalProperties": False,
            },
        },
    },
]

AUDIT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "accept_answer",
            "description": "Accept the answer when no material defect remains.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_repair",
            "description": "Return the single highest-impact material defect that must be repaired.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue": {"type": "string", "description": "One concrete defect in the answer."},
                    "why_material": {
                        "type": "string",
                        "description": "Why this defect could change or invalidate the requested answer.",
                    },
                },
                "required": ["issue", "why_material"],
                "additionalProperties": False,
            },
        },
    },
]

HYPOTHESIS_SYSTEM = """\
You are preparing a deep-research investigation. Write a revisable expected answer, not a safe non-answer.
Use internal knowledge only to make research cheaper. It is not evidence.

Return a compact prose brief with exactly these headings:
Expected answer
What could make it wrong
Smallest verification route

Name likely candidates or values when useful. Under the verification route, identify the few external facts or
complete inventory that would prove, revise, or reject the expected answer. Do not invent citations or URLs."""

RESEARCH_SYSTEM = """\
You are a deep-research agent. Build a claim that answers the original question and has enough externally
inspectable support to persuade a skeptical reader.

The expected answer is a useful guess, never evidence. Internal knowledge may choose an efficient route, but every
factual statement needed to resolve the question must come from observed search or page evidence.
When the question identifies its subject indirectly, first search the clue without the guessed identity and verify the
exact relationship; a page that merely contains the same words does not prove a title, author, owner, or identity.

After each batch of tool results, try to write the final answer. If every statement needed to resolve the question can
be supported, answer now. Otherwise, use tools only for a statement that must appear in the final answer but is not yet
supported, or for an unresolved possibility that could change the answer. Do not investigate details you would omit
from the final answer. For a set, ranking, unique, negative, or boundary-sensitive answer, include enough support to
show that an omitted candidate cannot change the result; exact values for lower-ranked candidates are unnecessary unless
the question asks you to report them. Resolve a source conflict only when it could change the requested answer or make
evidence used in the answer inapplicable. Prefer evidence matching the requested source, population, date, and metric.

Use search excerpts when they directly expose the needed fact; read a page only when surrounding text, a table, a
boundary case, or source provenance is missing. When you need every occurrence of an exact name or value on a long
page, use find_on_page rather than repeatedly reading broad windows. If one route does not improve what you know,
change the query, source, or page operation.
Follow any named source, date, interpretation, and output requirements in the question.

Tool results contain private refs such as [S1] and [P2]. When research is sufficient, stop calling tools and write the
final answer in the format and level of detail requested by the original question. Use polished Markdown prose when
the question does not prescribe a narrower format. Put each private ref immediately after the factual claim it
supports. Cite only refs you actually observed. Do not emit raw URLs, a bibliography, a source list, JSON, tool
instructions, or a plan. Never mention the internal expected answer, verification brief, reference answer, evaluation
process, or how the final answer differs from them. If evidence changes the expected answer, simply state the corrected
answer."""

AUDIT_SYSTEM = """\
You audit a deep-research answer using only the original question and the supplied evidence ledger. Ignore your own
world knowledge. Check whether the answer actually resolves the requested result, whether any finite inventory or
boundary needed by the question is covered, and whether every material factual claim is supported by the cited
visible evidence. When the question attributes facts to a named source, verify that evidence for those facts actually
comes from that source rather than a secondary source repeating it. Do not demand more evidence merely because stronger
evidence might exist. When an indirect clue identifies the subject, require evidence for that exact relationship rather
than mere occurrence of the same words. Call accept_answer when there is no material defect. Otherwise call
request_repair with exactly one highest-impact concrete defect."""

STRUCTURED_OUTPUT_SYSTEM = """\
Convert a completed, evidence-backed answer into the exact JSON value required by the supplied JSON Schema. Do not
research again, add facts, reinterpret the answer, or return prose. The completed answer determines the result; the
supplied evidence remains authoritative for exact values. Include every required field and call
submit_structured_output exactly once. The tool arguments are the final value, not JSON encoded inside a string."""


@dataclass(frozen=True)
class EvidenceRecord:
    ref: str
    key: str
    title: str
    url: str
    content: str
    receipt_id: str
    result_id: str
    slices: tuple[CitationSlice, ...]


@dataclass
class ResearchSession:
    question: str
    vfs: dict[str, str] = field(default_factory=dict)
    evidence: list[EvidenceRecord] = field(default_factory=list)
    page_cache: dict[str, tuple[Any, str, str, str]] = field(default_factory=dict)
    search_count: int = 0
    page_count: int = 0

    def next_ref(self, prefix: str) -> str:
        if prefix == "S":
            return f"S{sum(item.ref.startswith('S') for item in self.evidence) + 1}"
        return f"P{sum(item.ref.startswith('P') for item in self.evidence) + 1}"

    def evidence_by_ref(self) -> dict[str, EvidenceRecord]:
        return {item.ref: item for item in self.evidence}


def _tool(name: str) -> dict[str, Any]:
    return next(item for item in RESEARCH_TOOLS if item["function"]["name"] == name)


def _assistant_message(result: Any) -> Any:
    if len(result.llm.choices) != 1:
        raise RuntimeError(f"expected one LLM choice, received {len(result.llm.choices)}")
    return result.llm.choices[0].message


def _assistant_text(result: Any) -> str:
    return (result.llm.raw_text or "").strip()


def _strict_arguments(
    call: Any,
    expected: set[str],
    *,
    preserve_whitespace: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    try:
        arguments = json.loads(call.arguments)
    except json.JSONDecodeError as error:
        raise ValueError(f"{call.name} arguments are not valid JSON: {error}") from error
    if not isinstance(arguments, dict):
        raise ValueError(f"{call.name} arguments must be an object")
    unexpected = set(arguments) - expected
    if unexpected:
        raise ValueError(f"{call.name} received unexpected fields: {sorted(unexpected)}")
    missing = expected - set(arguments)
    if missing:
        raise ValueError(f"{call.name} is missing fields: {sorted(missing)}")
    for key in expected:
        if not isinstance(arguments[key], str) or not arguments[key].strip():
            raise ValueError(f"{call.name}.{key} must be a non-empty string")
        if key not in preserve_whitespace:
            arguments[key] = arguments[key].strip()
    return arguments


def _head_middle_tail(content: str, limit: int) -> tuple[str, list[tuple[int, int]]]:
    if len(content) <= limit:
        return content, [(0, len(content))]
    section = limit // 3
    spans = [
        (0, section),
        (max(0, len(content) // 2 - section // 2), min(len(content), len(content) // 2 + section // 2)),
        (len(content) - section, len(content)),
    ]
    text = "\n\n[... omitted ...]\n\n".join(content[start:end] for start, end in spans)
    return text, spans


_SEARCH_TOKEN_RE = re.compile(r"[^\W_](?:[\w.'-]*[^\W_])?", re.UNICODE)
_MARKDOWN_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+.+$")
_MARKDOWN_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_SEARCH_STOPWORDS = frozenset(
    "the and for with from that this have has was were are is been its their which what when where who how many much "
    "according also into over under between during against about after before while other more most than".split()
)


def _search_terms(text: str) -> set[str]:
    return {
        token
        for raw in _SEARCH_TOKEN_RE.findall(text.casefold())
        if len(token := raw.strip(".'-")) >= 3 and token not in _SEARCH_STOPWORDS
    }


def _ranked_search_spans(content: str, question: str, query: str) -> list[tuple[int, int]]:
    if len(content) <= SEARCH_HEAD_CHARS + SEARCH_WINDOW_CHARS:
        return [(0, len(content))]

    question_terms = _search_terms(question)
    query_terms = _search_terms(query)
    candidates: list[tuple[int, int, int]] = []
    position = 0
    folded = content.casefold()
    while position < len(content):
        window = folded[position : position + SEARCH_WINDOW_CHARS]
        score = sum(term in window for term in question_terms) + 2 * sum(
            term in window for term in query_terms
        )
        candidates.append((score, -position, position))
        if position + SEARCH_WINDOW_CHARS >= len(content):
            break
        position += SEARCH_WINDOW_STEP_CHARS

    _, _, best_start = max(candidates)
    spans = [(0, min(SEARCH_HEAD_CHARS, len(content)))]
    best_span = (best_start, min(len(content), best_start + SEARCH_WINDOW_CHARS))
    if best_span[0] <= spans[0][1]:
        spans[0] = (0, max(spans[0][1], best_span[1]))
    else:
        spans.append(best_span)
    return spans


def _render_search_preview(content: str, spans: list[tuple[int, int]]) -> str:
    if len(spans) == 1 and spans[0] == (0, len(content)):
        return content
    return "\n    [... omitted ...]\n    ".join(content[start:end] for start, end in spans)


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _expand_short_spans(content: str, spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    expanded: list[tuple[int, int]] = []
    for start, end in spans:
        missing = MIN_CITATION_SLICE_CHARS - (end - start)
        if missing <= 0:
            expanded.append((start, end))
            continue
        left = min(start, missing // 2)
        right = min(len(content) - end, missing - left)
        left += min(start - left, missing - left - right)
        expanded.append((start - left, end + right))
    return _merge_spans(expanded)


def _heading_sections(content: str) -> list[tuple[int, int, str]]:
    headings: list[tuple[int, int, str]] = []
    position = 0
    fence_character = ""
    fence_length = 0
    for line in content.splitlines(keepends=True):
        stripped_line = line.rstrip("\r\n")
        if fence_character:
            candidate = stripped_line.lstrip(" ")
            if (
                len(stripped_line) - len(candidate) <= 3
                and candidate.startswith(fence_character * fence_length)
                and not candidate.lstrip(fence_character).strip()
            ):
                fence_character = ""
                fence_length = 0
            position += len(line)
            continue

        fence = _MARKDOWN_FENCE_RE.match(stripped_line)
        if fence:
            marker = fence.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            position += len(line)
            continue

        heading = _MARKDOWN_HEADING_RE.match(stripped_line)
        if heading:
            headings.append((position, len(heading.group(1)), stripped_line.casefold()))
        position += len(line)

    sections: list[tuple[int, int, str]] = []
    for index, (start, level, heading) in enumerate(headings):
        end = len(content)
        for following_start, following_level, _ in headings[index + 1 :]:
            if following_level <= level:
                end = following_start
                break
        sections.append((start, end, heading))
    return sections


def _align_window_to_trailing_section(
    content: str,
    focus_terms: set[str],
    spans: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    headings = [
        (len(focus_terms & _search_terms(heading)), start, end)
        for start, end, heading in _heading_sections(content)
    ]

    def section_coverage(section_start: int, section_end: int, windows: list[tuple[int, int]]) -> int:
        return sum(
            max(0, min(right, section_end) - max(left, section_start))
            for left, right in _merge_spans(windows)
        )

    best: tuple[tuple[int, int, int], int, tuple[int, int]] | None = None
    for score, section_start, section_end in headings:
        if score < MIN_HEADING_FOCUS_TERMS:
            continue
        visible_section = section_coverage(section_start, section_end, spans)
        omitted_section = section_end - section_start - visible_section
        if omitted_section <= visible_section:
            continue
        shifted = (section_start, min(len(content), section_start + PAGE_WINDOW_CHARS))
        for index, (left, right) in enumerate(spans):
            heading_near_end = (
                max(left, right - PAGE_WINDOW_STEP_CHARS // 2) <= section_start < right
            )
            if not heading_near_end:
                continue
            replacement = [*spans]
            replacement[index] = shifted
            added_coverage = (
                section_coverage(section_start, section_end, replacement) - visible_section
            )
            if added_coverage <= 0:
                continue
            rank = (score, added_coverage, -section_start)
            if best is None or rank > best[0]:
                best = (rank, index, shifted)

    if best is None:
        return spans
    _, index, shifted = best
    aligned = [*spans]
    aligned[index] = shifted
    return aligned


def _ranked_page_spans(content: str, question: str, focus: str) -> list[tuple[int, int]]:
    if len(content) <= PAGE_PLAIN_CHARS:
        return [(0, len(content))]

    question_terms = _search_terms(question)
    focus_terms = _search_terms(focus)
    folded = content.casefold()
    candidates: list[tuple[int, int, int]] = []
    position = 0
    while position < len(content):
        window = folded[position : position + PAGE_WINDOW_CHARS]
        score = sum(term in window for term in question_terms) + 2 * sum(
            term in window for term in focus_terms
        )
        candidates.append((score, -position, position))
        if position + PAGE_WINDOW_CHARS >= len(content):
            break
        position += PAGE_WINDOW_STEP_CHARS

    selected: list[tuple[int, int]] = []
    for score, _, start in sorted(candidates, reverse=True):
        span = (start, min(len(content), start + PAGE_WINDOW_CHARS))
        if any(start < selected_end and selected_start < span[1] for selected_start, selected_end in selected):
            continue
        if selected and score <= 0:
            break
        selected.append(span)
        if len(selected) >= PAGE_WINDOWS:
            break
    selected = _align_window_to_trailing_section(content, focus_terms, selected)
    return _merge_spans([(0, min(PAGE_HEAD_CHARS, len(content))), *selected])


def _render_page_preview(content: str, spans: list[tuple[int, int]]) -> str:
    if spans == [(0, len(content))]:
        return content
    return "\n\n[... omitted ...]\n\n".join(content[start:end] for start, end in spans)


@dataclass(frozen=True)
class SourceLine:
    start: int
    end: int
    text: str
    inside_fence: bool


@dataclass(frozen=True)
class PageStructure:
    lines: tuple[SourceLine, ...]
    line_starts: tuple[int, ...]
    sections: tuple[tuple[int, int, str], ...]
    section_starts: tuple[int, ...]
    table_records: dict[int, tuple[int, int]]
    table_headers: dict[int, tuple[int, int]]


def _source_lines(content: str) -> list[SourceLine]:
    lines: list[SourceLine] = []
    position = 0
    fence_character = ""
    fence_length = 0
    for line in content.splitlines(keepends=True):
        end = position + len(line)
        stripped_line = line.rstrip("\r\n")
        inside_fence = bool(fence_character)
        if fence_character:
            candidate = stripped_line.lstrip(" ")
            if (
                len(stripped_line) - len(candidate) <= 3
                and candidate.startswith(fence_character * fence_length)
                and not candidate.lstrip(fence_character).strip()
            ):
                fence_character = ""
                fence_length = 0
        else:
            fence = _MARKDOWN_FENCE_RE.match(stripped_line)
            if fence:
                marker = fence.group(1)
                fence_character = marker[0]
                fence_length = len(marker)
                inside_fence = True
        lines.append(SourceLine(position, end, line, inside_fence))
        position = end
    if position < len(content):
        lines.append(SourceLine(position, len(content), content[position:], bool(fence_character)))
    return lines


def _line_containing(structure: PageStructure, position: int) -> int:
    return max(0, _bisect_right(structure.line_starts, position) - 1)


def _is_table_line(line: SourceLine) -> bool:
    return not line.inside_fence and line.text.lstrip().startswith("|")


def _is_table_separator(line: SourceLine) -> bool:
    stripped = line.text.strip()
    return _is_table_line(line) and "-" in stripped and not stripped.strip("| :-\t")


def _table_records(lines: list[SourceLine]) -> dict[int, tuple[int, int]]:
    records: dict[int, tuple[int, int]] = {}
    index = 0
    while index < len(lines):
        if not _is_table_line(lines[index]):
            index += 1
            continue
        end_index = index + 1
        while end_index < len(lines):
            following = lines[end_index]
            if (
                _is_table_line(following)
                or following.inside_fence
                or not following.text.strip()
                or _MARKDOWN_HEADING_RE.match(following.text.rstrip("\r\n"))
            ):
                break
            end_index += 1
        span = (lines[index].start, lines[end_index - 1].end)
        for record_line in range(index, end_index):
            records[record_line] = span
        index = end_index
    return records


def _table_headers(lines: list[SourceLine]) -> dict[int, tuple[int, int]]:
    headers: dict[int, tuple[int, int]] = {}
    active_header: tuple[int, int] | None = None
    pending_header_index: int | None = None
    for index, line in enumerate(lines):
        if (
            line.inside_fence
            or not line.text.strip()
            or _MARKDOWN_HEADING_RE.match(line.text.rstrip("\r\n"))
        ):
            active_header = None
            pending_header_index = None
            continue
        if _is_table_separator(line):
            if pending_header_index is not None:
                active_header = (lines[pending_header_index].start, line.end)
            continue
        if _is_table_line(line):
            if active_header is None:
                pending_header_index = index
            else:
                headers[index] = active_header
            continue
        if active_header is not None:
            headers[index] = active_header
    return headers


def _page_structure(content: str) -> PageStructure:
    lines = _source_lines(content)
    sections = tuple(_heading_sections(content))
    return PageStructure(
        lines=tuple(lines),
        line_starts=tuple(line.start for line in lines),
        sections=sections,
        section_starts=tuple(start for start, _, _ in sections),
        table_records=_table_records(lines),
        table_headers=_table_headers(lines),
    )


def _section_heading(content: str, structure: PageStructure, position: int) -> tuple[int, int] | None:
    section_index = _bisect_right(structure.section_starts, position) - 1
    if section_index < 0:
        return None
    start, end, _ = structure.sections[section_index]
    if position >= end:
        return None
    line_end = content.find("\n", start)
    if line_end < 0:
        return start, len(content)
    return start, line_end + 1


def _table_record(structure: PageStructure, line_index: int) -> tuple[int, int] | None:
    return structure.table_records.get(line_index)


def _table_header(structure: PageStructure, line_index: int) -> tuple[int, int] | None:
    return structure.table_headers.get(line_index)


def _evidence_size(spans: list[tuple[int, int]]) -> tuple[int, int]:
    return len(spans), sum(end - start for start, end in spans)


def _validate_evidence_size(spans: list[tuple[int, int]], *, operation: str) -> None:
    segments, characters = _evidence_size(spans)
    if segments > MAX_EVIDENCE_SEGMENTS:
        raise RuntimeError(f"{operation} produced {segments} citation slices; use a narrower selection")
    if characters > MAX_TOTAL_EVIDENCE_CHARS:
        raise RuntimeError(f"{operation} produced {characters} evidence characters; use a narrower selection")


def _exact_match_spans(content: str, text: str) -> tuple[int, list[tuple[int, int]]]:
    if "\n" in text or "\r" in text:
        raise ValueError("find_on_page.text must be a single-line exact string")
    pattern = re.compile(re.escape(text), flags=re.IGNORECASE)
    structure = _page_structure(content)
    matching_records: dict[tuple[int, int], int] = {}
    for line_index, line in enumerate(structure.lines):
        if pattern.search(line.text) is None:
            continue
        record = _table_record(structure, line_index) or (line.start, line.end)
        matching_records.setdefault(record, line_index)
    if not matching_records:
        return 0, []

    spans: list[tuple[int, int]] = []
    for record, line_index in matching_records.items():
        heading = _section_heading(content, structure, record[0])
        header = _table_header(structure, line_index)
        spans.extend(span for span in (heading, header, record) if span is not None)
    selected = _expand_short_spans(content, _merge_spans(spans))
    _validate_evidence_size(selected, operation="find_on_page")
    return len(matching_records), selected


def _result_identity(result: Any, index: int) -> tuple[str, str]:
    if index >= len(result.results):
        raise RuntimeError("retrieval result omitted citation identity")
    result_id = result.results[index].result_id
    if not result.receipt_id or not result_id:
        raise RuntimeError("retrieval result omitted citation identity")
    return result.receipt_id, result_id


async def _run_search(session: ResearchSession, query: str, preview_budget: int) -> str:
    result = await search_web(
        query,
        provider=SEARCH_PROVIDER,
        num=SEARCH_RESULT_COUNT,
        timeout=SEARCH_TIMEOUT,
    )
    session.search_count += 1
    parent_key = f"search://{session.search_count}"
    session.vfs[parent_key] = result.response.model_dump_json(indent=2)
    observations = [f"# search_web({query!r}) -> {len(result.response.data)} results"]
    for index, item in enumerate(result.response.data):
        content = item.snippet or ""
        key = f"{parent_key}/result/{index + 1}"
        session.vfs[key] = content
        if not content:
            observations.append(
                f"{item.title or item.link} — {item.link}\n"
                "    No citable excerpt was returned; use this only to discover a page to read."
            )
            continue
        ref = session.next_ref("S")
        receipt_id, result_id = _result_identity(result, index)
        spans = _ranked_search_spans(content, session.question, query)
        preview = _render_search_preview(content, spans)
        record = EvidenceRecord(
            ref=ref,
            key=key,
            title=item.title or item.link,
            url=item.link,
            content=content,
            receipt_id=receipt_id,
            result_id=result_id,
            slices=tuple(CitationSlice(start=start, end=end) for start, end in spans if end > start),
        )
        session.evidence.append(record)
        observations.append(f"[{ref}] {record.title} — {record.url}\n    {preview}")
    return "\n".join(observations)


async def _load_page(session: ResearchSession, url: str) -> tuple[Any, str, str, str]:
    cached = session.page_cache.get(url)
    if cached is None:
        result = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=FETCH_TIMEOUT)
        if not result.response.data:
            raise RuntimeError(f"read_page returned no content for {url}")
        item = result.response.data[0]
        receipt_id, result_id = _result_identity(result, 0)
        cached = (result, item.content, item.title or item.url, item.url or url)
        session.page_cache[url] = cached
        session.vfs[f"page://{url}"] = item.content
    return cached


async def _run_read_page(session: ResearchSession, url: str, focus: str, preview_budget: int) -> dict[str, Any]:
    result, content, title, effective_url = await _load_page(session, url)
    spans = _ranked_page_spans(content, session.question, focus)
    preview = _render_page_preview(content, spans)
    session.page_count += 1
    ref = session.next_ref("P")
    receipt_id, result_id = _result_identity(result, 0)
    record = EvidenceRecord(
        ref=ref,
        key=f"page://{url}",
        title=title,
        url=effective_url,
        content=content,
        receipt_id=receipt_id,
        result_id=result_id,
        slices=tuple(CitationSlice(start=start, end=end) for start, end in spans if end > start),
    )
    session.evidence.append(record)
    return {
        "ok": True,
        "ref": f"[{ref}]",
        "vfs_key": record.key,
        "title": title,
        "url": url,
        "focus": focus,
        "attempts": result.response.attempts,
        "retry_reasons": result.response.retry_reasons,
        "text": preview,
    }


async def _run_find_on_page(session: ResearchSession, url: str, text: str, preview_budget: int) -> dict[str, Any]:
    result, content, title, effective_url = await _load_page(session, url)
    matching_record_count, spans = _exact_match_spans(content, text)
    if not spans:
        return {
            "ok": True,
            "complete": True,
            "matching_record_count": 0,
            "vfs_key": f"page://{url}",
            "title": title,
            "url": url,
            "text": f"No case-insensitive exact matches for {text!r}.",
        }

    preview = _render_page_preview(content, spans)
    if len(preview) > preview_budget:
        raise RuntimeError(
            f"find_on_page found {matching_record_count} records requiring {len(preview)} preview characters; "
            f"use a narrower exact string than {text!r}"
        )
    session.page_count += 1
    ref = session.next_ref("P")
    receipt_id, result_id = _result_identity(result, 0)
    record = EvidenceRecord(
        ref=ref,
        key=f"page://{url}",
        title=title,
        url=effective_url,
        content=content,
        receipt_id=receipt_id,
        result_id=result_id,
        slices=tuple(CitationSlice(start=start, end=end) for start, end in spans if end > start),
    )
    session.evidence.append(record)
    return {
        "ok": True,
        "complete": True,
        "matching_record_count": matching_record_count,
        "ref": f"[{ref}]",
        "vfs_key": record.key,
        "title": title,
        "url": url,
        "text": preview,
    }


async def _execute_research_call(session: ResearchSession, call: Any, preview_budget: int) -> str | dict[str, Any]:
    try:
        if call.name == "search_web":
            arguments = _strict_arguments(call, {"query"})
            return await _run_search(session, arguments["query"], preview_budget)
        if call.name == "read_page":
            arguments = _strict_arguments(call, {"url", "focus"})
            return await _run_read_page(session, arguments["url"], arguments["focus"], preview_budget)
        if call.name == "find_on_page":
            arguments = _strict_arguments(call, {"url", "text"}, preserve_whitespace=frozenset({"text"}))
            return await _run_find_on_page(session, arguments["url"], arguments["text"], preview_budget)
        raise ValueError(f"unknown research tool: {call.name}")
    except Exception as error:
        return f"# {call.name} failed: {error}"


async def _llm_chat_with_fallback(
    *,
    stage: str,
    model: str,
    fallback_model: str,
    fallback_provider: str = "openrouter",
    messages: list[Any],
    temperature: float,
    thinking: dict[str, Any],
    provider_extra: dict[str, Any],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | None = None,
    parallel_tool_calls: bool | None = None,
    fallback_provider_extra: dict[str, Any] | None = None,
) -> Any:
    try:
        return await llm_chat(
            provider="openrouter",
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking=thinking,
            provider_extra=provider_extra,
            timeout=LLM_TIMEOUT,
        )
    except Exception as primary_error:
        primary_error_detail = str(primary_error)
        logger.warning(
            "llm_fallback stage=%s primary_provider=openrouter primary_model=%s "
            "fallback_provider=%s fallback_model=%s error=%s",
            stage,
            model,
            fallback_provider,
            fallback_model,
            primary_error_detail,
        )
    try:
        if fallback_provider != "openrouter" and fallback_provider_extra is None:
            return await llm_chat(
                provider=fallback_provider,
                model=fallback_model,
                messages=messages,
                temperature=temperature,
                tools=tools,
                tool_choice=tool_choice,
                parallel_tool_calls=parallel_tool_calls,
                thinking=thinking,
                timeout=LLM_TIMEOUT,
            )
        return await llm_chat(
            provider=fallback_provider,
            model=fallback_model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking=thinking,
            provider_extra=fallback_provider_extra or {"provider": {"allow_fallbacks": True}},
            timeout=LLM_TIMEOUT,
        )
    except Exception as fallback_error:
        raise RuntimeError(
            f"{stage} primary and fallback LLM calls failed; "
            f"primary_provider=openrouter primary={primary_error_detail}; "
            f"fallback_provider={fallback_provider} fallback={fallback_error}"
        ) from fallback_error


async def _call_researcher(messages: list[Any]) -> Any:
    return await _llm_chat_with_fallback(
        stage="research",
        model="z-ai/glm-5.2",
        fallback_model=RESEARCH_FALLBACK_MODEL,
        fallback_provider=RESEARCH_FALLBACK_PROVIDER,
        messages=messages,
        temperature=0.2,
        tools=RESEARCH_TOOLS,
        tool_choice="auto",
        parallel_tool_calls=True,
        thinking={"enabled": True, "effort": "low"},
        provider_extra={"provider": {"allow_fallbacks": True}},
    )


async def _research_until_answer(
    session: ResearchSession,
    messages: list[Any],
    *,
    turn_budget: int,
) -> tuple[str, list[Any], int]:
    for turns_used in range(1, turn_budget + 1):
        result = await _call_researcher(messages)
        assistant = _assistant_message(result)
        calls = list(assistant.tool_calls or ())
        if not calls:
            answer = _assistant_text(result)
            if not answer:
                raise RuntimeError("researcher returned neither tool calls nor prose")
            return answer, messages, turns_used
        if len(calls) > MAX_PARALLEL_TOOL_CALLS:
            raise RuntimeError(
                f"researcher requested {len(calls)} tools in one turn; ceiling is {MAX_PARALLEL_TOOL_CALLS}"
            )

        messages.append(assistant.to_input_message())
        preview_budget = TOOL_TURN_PREVIEW_CHARS // len(calls)
        outputs = await asyncio.gather(*(_execute_research_call(session, call, preview_budget) for call in calls))
        for call, output in zip(calls, outputs, strict=True):
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": output if isinstance(output, str) else json.dumps(output, ensure_ascii=False),
                }
            )
    raise RuntimeError(f"researcher exhausted the visible {turn_budget}-turn experiment ceiling")


_PRIVATE_REF_GROUP = re.compile(r"\[((?:[SP]\d+\s*,\s*)*[SP]\d+)\]")


def _refs_in_group(match: re.Match[str]) -> list[str]:
    return [ref.strip() for ref in match.group(1).split(",")]


def _private_refs(answer: str) -> list[str]:
    refs = (ref for match in _PRIVATE_REF_GROUP.finditer(answer) for ref in _refs_in_group(match))
    return list(dict.fromkeys(refs))


def _validate_private_answer(answer: str, session: ResearchSession) -> None:
    if "[[" in answer or "]]" in answer:
        raise ValueError("use private refs such as [S1], not public citation indices")
    if re.search(r"https?://|\bwww\.", answer, flags=re.IGNORECASE):
        raise ValueError("do not render raw URLs in the final answer")
    allowed = session.evidence_by_ref()
    refs = _private_refs(answer)
    unknown = [ref for ref in refs if ref not in allowed]
    if unknown:
        raise ValueError(f"answer cites unavailable refs: {', '.join(unknown)}")
    if not allowed:
        raise ValueError("deep-research answer has no observed evidence")
    if not refs:
        raise ValueError("answer cites none of the observed evidence")
    without_refs = _PRIVATE_REF_GROUP.sub("", answer)
    if re.search(r"\[(?:[SP]\d+[^\]]*|[^\]]*[SP]\d+)\]", without_refs):
        raise ValueError("private refs must use [S1] or a comma-separated group such as [S1, P2]")


async def _repair_private_answer_contract(
    session: ResearchSession,
    answer: str,
    messages: list[Any],
) -> str:
    try:
        _validate_private_answer(answer, session)
        return answer
    except ValueError as error:
        logger.warning("private_answer_contract_retry error=%s", error)
        validation_error = str(error)

    valid_refs = ", ".join(f"[{ref}]" for ref in session.evidence_by_ref())
    repair_messages = [
        *messages,
        {"role": "assistant", "content": answer},
        {
            "role": "user",
            "content": (
                "Your final answer failed the mechanical private-citation contract. Correct only the citation syntax "
                "and placement; do not research, add or remove factual claims, or otherwise rewrite the answer. "
                "Return the complete corrected answer as prose, with no commentary. A citation may be a single ref "
                "such as [S1] or a comma-separated group such as [S1, P2]. Use only observed refs.\n\n"
                f"Validation error: {validation_error}\n"
                f"Observed refs: {valid_refs}"
            ),
        },
    ]
    result = await _llm_chat_with_fallback(
        stage="private_citation_repair",
        model="z-ai/glm-5.2",
        fallback_model=RESEARCH_FALLBACK_MODEL,
        fallback_provider=RESEARCH_FALLBACK_PROVIDER,
        messages=repair_messages,
        temperature=0.0,
        thinking={"enabled": True, "effort": "low"},
        provider_extra={"provider": {"allow_fallbacks": True}},
    )
    repaired = _assistant_text(result)
    if not repaired:
        raise RuntimeError("private citation repair returned empty prose")
    try:
        _validate_private_answer(repaired, session)
    except ValueError as repair_error:
        raise ValueError(f"private citation repair failed validation: {repair_error}") from repair_error
    return repaired


def _audit_evidence_digest(session: ResearchSession, answer: str) -> str:
    records = session.evidence_by_ref()
    cited = _private_refs(answer)
    parts: list[str] = []
    for ref in cited:
        item = records[ref]
        visible = "\n...\n".join(item.content[slice_.start : slice_.end] for slice_ in item.slices)
        parts.append(f"[{ref}] {item.title}\nSource URL: {item.url}\n{visible}")
    return "\n\n".join(parts)


async def _audit(session: ResearchSession, answer: str) -> tuple[bool, str]:
    _validate_private_answer(answer, session)
    result = await _llm_chat_with_fallback(
        stage="audit",
        model="openai/gpt-oss-120b",
        fallback_model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": AUDIT_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Original question:\n{session.question}\n\nCandidate answer:\n{answer}\n\n"
                    f"Evidence ledger (only cited records):\n{_audit_evidence_digest(session, answer)}"
                ),
            },
        ],
        temperature=0.0,
        tools=AUDIT_TOOLS,
        tool_choice="required",
        parallel_tool_calls=False,
        thinking={"enabled": True, "effort": "high"},
        provider_extra={"provider": {"only": ["cerebras"], "allow_fallbacks": False}},
    )
    calls = list(_assistant_message(result).tool_calls or ())
    if len(calls) != 1:
        raise RuntimeError(f"auditor must make exactly one decision; received {len(calls)} calls")
    call = calls[0]
    if call.name == "accept_answer":
        arguments = json.loads(call.arguments)
        if arguments != {}:
            raise ValueError("accept_answer accepts no arguments")
        return True, ""
    if call.name != "request_repair":
        raise ValueError(f"unexpected auditor tool: {call.name}")
    arguments = _strict_arguments(call, {"issue", "why_material"})
    return False, f"{arguments['issue']} Why material: {arguments['why_material']}"


def _render_response(session: ResearchSession, answer: str) -> Response:
    _validate_private_answer(answer, session)
    records = session.evidence_by_ref()
    cited = _private_refs(answer)
    selected_spans = [
        (slice_.start, slice_.end)
        for ref in cited
        for slice_ in records[ref].slices
    ]
    _validate_evidence_size(selected_spans, operation="final answer")
    citations: list[CitationRef] = []
    indices: dict[str, int] = {}
    for ref in cited:
        item = records[ref]
        citations.append(
            CitationRef(
                receipt_id=item.receipt_id,
                result_id=item.result_id,
                slices=list(item.slices),
            )
        )
        indices[ref] = len(citations)
    rendered = _PRIVATE_REF_GROUP.sub(
        lambda match: "".join(f"[[{indices[ref]}]]" for ref in _refs_in_group(match)),
        answer,
    )
    return Response(text=rendered, citations=citations)


def _structured_output_tool(output_schema: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    direct_object = output_schema.get("type") == "object"
    parameters = (
        output_schema
        if direct_object
        else {
            "type": "object",
            "properties": {"output": {"description": "The complete schema-conforming JSON value."}},
            "required": ["output"],
            "additionalProperties": False,
        }
    )
    return (
        {
            "type": "function",
            "function": {
                "name": "submit_structured_output",
                "description": "Submit the complete final value required by the caller's JSON Schema.",
                "parameters": parameters,
                "strict": False,
            },
        },
        direct_object,
    )


async def _materialize_structured_output(
    session: ResearchSession,
    answer: str,
    output_schema: dict[str, Any],
) -> Any:
    tool, direct_object = _structured_output_tool(output_schema)
    evidence_backed_answer = _PRIVATE_REF_GROUP.sub("", answer).strip()
    messages: list[Any] = [
        {"role": "system", "content": STRUCTURED_OUTPUT_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Original question:\n{session.question}\n\n"
                f"Completed evidence-backed answer:\n{evidence_backed_answer}\n\n"
                "Authoritative cited evidence:\n"
                f"{_audit_evidence_digest(session, answer)}\n\n"
                "Required JSON Schema:\n"
                f"{json.dumps(output_schema, ensure_ascii=False, indent=2)}"
            ),
        },
    ]
    for attempt in range(3):
        result = await _llm_chat_with_fallback(
            stage="structured_output",
            model="z-ai/glm-5.2",
            fallback_model=STRUCTURED_FALLBACK_MODEL,
            messages=messages,
            temperature=0.0,
            tools=[tool],
            tool_choice="required",
            parallel_tool_calls=False,
            thinking={"enabled": True, "effort": "low"},
            provider_extra={"provider": {"allow_fallbacks": True}},
        )
        assistant = _assistant_message(result)
        calls = list(assistant.tool_calls or ())
        error: ValueError | None = None
        output: Any = None
        if len(calls) != 1:
            error = ValueError(f"call submit_structured_output exactly once; received {len(calls)} calls")
        else:
            call = calls[0]
            try:
                if call.name != "submit_structured_output":
                    raise ValueError(f"unexpected tool {call.name}; call submit_structured_output")
                arguments = json.loads(call.arguments)
                if not isinstance(arguments, dict):
                    raise ValueError("tool arguments must be a JSON object")
                if direct_object:
                    output = arguments
                else:
                    if set(arguments) != {"output"}:
                        raise ValueError("non-object output must use the sole `output` argument")
                    output = arguments["output"]
                if output is None:
                    raise ValueError("top-level null is not a valid miner answer")
                validate_output_against_schema(output, output_schema)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as caught:
                error = ValueError(str(caught))
        if error is None:
            return output
        if attempt == 2:
            raise error
        messages.append(assistant.to_input_message())
        if calls:
            for call in calls:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            {"ok": False, "error_type": "tool_argument_validation", "details": str(error)}
                        ),
                    }
                )
        else:
            messages.append(
                {
                    "role": "user",
                    "content": f"Output contract error: {error}. Submit the complete schema-conforming value.",
                }
            )
    raise AssertionError("unreachable")


async def _hypothesis(question: str) -> str:
    result = await _llm_chat_with_fallback(
        stage="hypothesis",
        model="z-ai/glm-5.2",
        fallback_model=RESEARCH_FALLBACK_MODEL,
        fallback_provider=RESEARCH_FALLBACK_PROVIDER,
        messages=[
            {"role": "system", "content": HYPOTHESIS_SYSTEM},
            {"role": "user", "content": question},
        ],
        temperature=0.2,
        thinking={"enabled": True, "effort": "low"},
        provider_extra={"provider": {"allow_fallbacks": True}},
    )
    hypothesis = _assistant_text(result)
    if not hypothesis:
        raise RuntimeError("hypothesis model returned empty output")
    return hypothesis


@entrypoint("query")
async def query(query_input: Query) -> Response:
    hypothesis = await _hypothesis(query_input.text)
    session = ResearchSession(question=query_input.text)
    messages: list[Any] = [
        {"role": "system", "content": RESEARCH_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Original question:\n{query_input.text}\n\n"
                f"Revisable expected answer and verification brief:\n{hypothesis}"
            ),
        },
    ]
    answer, messages, turns_used = await _research_until_answer(
        session,
        messages,
        turn_budget=RESEARCH_TURN_CEILING,
    )
    remaining_turns = RESEARCH_TURN_CEILING - turns_used
    while True:
        answer = await _repair_private_answer_contract(session, answer, messages)
        accepted, issue = await _audit(session, answer)
        if accepted:
            break
        if remaining_turns <= 0:
            raise RuntimeError(f"audit rejected answer after research ceiling: {issue}")
        messages.extend(
            [
                {"role": "assistant", "content": answer},
                {
                    "role": "user",
                    "content": (
                        "The evidence audit found one material defect. Repair only that defect. First decide whether "
                        "the disputed statement is necessary to produce the result requested by the original question. "
                        "If it is unnecessary, delete it and any explanation that depends only on it; do not research "
                        "a replacement. If it is necessary, correct it from existing observed evidence when possible, "
                        "and use focused additional research only when the required claim remains unsupported. Do not "
                        "add new factual claims unless the requested result requires them. Then return the complete "
                        "corrected answer.\n\n"
                        f"Audit finding: {issue}"
                    ),
                },
            ]
        )
        answer, messages, turns_used = await _research_until_answer(
            session,
            messages,
            turn_budget=remaining_turns,
        )
        remaining_turns -= turns_used
    response = _render_response(session, answer)
    if query_input.output_schema is None:
        return response
    output = await _materialize_structured_output(session, answer, query_input.output_schema)
    return Response(output=output, citations=response.citations)
