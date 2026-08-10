"""Experiment: one researcher owns the answer and its numbered evidence.

Hypothesis
==========
The accumulated harness repeatedly reconstructs one answer across task analysis,
research state, writing, audit, schema materialization, and evidence projection.
This experiment makes one persistent researcher responsible for investigation,
answer revision, final output, and selection of already-numbered evidence.

Experimental contract
=====================
1. One GLM-5.2 conversation forms a revisable expected answer in reasoning,
   searches the web, reads pages, revises the answer, and finalizes it.
   Independent calls from one turn run in
   parallel; tool responses are replayed in call order.
2. Search results are plain numbered evidence records with a 220-character head
   and one 700-character query-ranked window. Each independently displayed page
   window receives its own evidence number instead of making one citation cover
   every window returned by a read. For exact inventory work,
   ``find_on_page`` makes each matching raw record a separate evidence item and
   carries its Markdown heading and table header with it. Fenced code is not
   treated as document structure. Each visible item has a small stable ref such
   as [E3]; the harness already owns its exact CitationRef and VFS content.
3. The same researcher always finalizes its investigation as an evidence-backed
   prose answer through submit_proven_answer(text, evidence). For a caller JSON
   Schema, the harness accepts that answer as authoritative, then asks the same
   conversation to project it through submit_structured_output. Retrieval is not
   available during projection, and the proven answer owns the evidence list.
4. There is no separate task-contract model, expected-answer model, writer,
   auditor, schema materializer, or post-answer evidence projector in variant A.
5. Each LLM boundary gets 40 seconds for its primary route and one 40-second
   model/provider fallback. Every fallback is logged; two failures surface.

Lexical ranking selects display spans; it does not accept, reject, summarize,
or alter evidence. This experiment does not replace the active candidate or
impose an output-token cap.
"""

from __future__ import annotations


LLM_TIMEOUT = 40.0
TOOL_TURN_PREVIEW_CHARS = 96_000
FETCH_TIMEOUT = 15.0
SEARCH_TIMEOUT = 10.0
MAX_EVIDENCE_SEGMENTS = 400
EMBEDDING_TIMEOUT = 180.0
MIN_CITATION_SLICE_CHARS = 100
TASK_TOTAL_BUDGET_SECONDS = 250.0
MAX_TOTAL_EVIDENCE_CHARS = 120_000

LLM_PROVIDER = "openrouter"
MODEL = "z-ai/glm-5.2"

from time import perf_counter
import asyncio
import hashlib
import json
import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any

from harnyx_miner_sdk.api import embed_text, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
from harnyx_miner_sdk.structured_output import validate_output_against_schema
from harnyx_miner_sdk.tools.proxy import ToolInvocationError

SEARCH_PROVIDER = "parallel"
RESEARCH_FALLBACK_PROVIDER = "ai_gateway"
RESEARCH_FALLBACK_MODEL = "deepseek/deepseek-v4-flash-0731"
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
REGION_PAGE_CHARS = 12_000
REGION_RESULT_COUNT = 5
REGION_EMBEDDING_DIMENSIONS = 1_024

logger = logging.getLogger("direct_research_loop")

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
                "Read a few relevant passages from one discovered page. Use this for ordinary prose or when a short "
                "focus phrase is enough; it is cheaper than indexing the page's complete structure."
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
                "Find every raw record containing an exact name or value already known to you on one page. "
                "Returns each matching record with its section and table header."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Exact URL returned by search."},
                    "text": {
                        "type": "string",
                        "description": "Single-line exact name or value, matched case-insensitively.",
                    },
                },
                "required": ["url", "text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_page",
            "description": (
                "Locate a complete table, list, or section on a discovered page when its exact names or values are not "
                "yet known. The query is natural language. Use read_page for ordinary passages and sufficient excerpts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Exact URL returned by search."},
                    "query": {
                        "type": "string",
                        "description": "Natural-language description of the complete structure needed.",
                    },
                },
                "required": ["url", "query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_region",
            "description": (
                "Read one region returned by search_page. Complete structures are preserved; large tables or sections "
                "return a continuation handle and repeat heading and table-header context."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Opaque region or continuation handle returned by the harness.",
                    },
                },
                "required": ["region"],
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

Before the first retrieval, form a concrete revisable expected answer and its smallest verification route in your
reasoning. Do not expose this planning scratch in the final answer. The expected answer is a useful guess, never
evidence. Internal knowledge may choose an efficient route, but every
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

Use search excerpts when they directly expose the needed fact. Use read_page for ordinary prose or a few focused
passages. Use find_on_page when you already know an exact name or value and need its source record. When the correct
page is known but the answer depends on a complete table, list, or section whose exact contents are not yet known, call
search_page with a natural-language description and then read_region on the best handle. Do not index a page merely to
confirm a sufficient excerpt. If one route does not improve what you know,
change the query, source, or page operation.
Follow any named source, date, interpretation, and output requirements in the question.
When the question names a data source, use that source's own page or machine-readable API for the requested metrics
when it is accessible. A secondary site does not become direct evidence merely because it republishes or attributes
the named source. After discovering a working API URL pattern, reuse that pattern for the remaining requested metrics
and countries instead of switching to secondary mirrors.

Tool results contain private refs such as [E1] and [E2]. When research is sufficient, stop calling tools and write the
final answer in the format and level of detail requested by the original question. Use polished Markdown prose when
the question does not prescribe a narrower format. Put each private ref immediately after the factual claim it
supports. Cite only refs you actually observed. Do not emit raw URLs, a bibliography, a source list, JSON, tool
instructions, or a plan. Never mention the internal expected answer, verification brief, reference answer, evaluation
process, or how the final answer differs from them. If evidence changes the expected answer, simply state the corrected
answer.

Finalize by calling submit_proven_answer alone. Its text is the complete evidence-backed answer. Normally place [E#]
refs immediately after supported claims; the harness renders them as public citations for prose questions and uses
them to preserve the proof when a later structured-output projection is required. When the original question requires
exact text with no extra characters, keep text exact and supply the supporting records only through the separate
evidence list. The tool takes a small list of integer evidence numbers that materially support the result and its
derivation. Do not include every observed record."""

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
    region_indexes: dict[str, Any] = field(default_factory=dict)
    region_registry: dict[str, tuple[str, Any]] = field(default_factory=dict)
    search_count: int = 0
    page_count: int = 0

    def next_ref(self) -> str:
        return f"E{len(self.evidence) + 1}"

    def evidence_by_ref(self) -> dict[str, EvidenceRecord]:
        return {item.ref: item for item in self.evidence}


@dataclass(frozen=True)
class ResearchResult:
    answer: str
    evidence_refs: tuple[str, ...]


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
        (len(focus_terms.intersection(_search_terms(heading))), start, end)
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


def _bisect_right(values: tuple[int, ...], target: int) -> int:
    low = 0
    high = len(values)
    while low < high:
        middle = (low + high) // 2
        if target < values[middle]:
            high = middle
        else:
            low = middle + 1
    return low


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


def _exact_match_groups(content: str, text: str) -> list[list[tuple[int, int]]]:
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
        return []

    groups: list[list[tuple[int, int]]] = []
    for record, line_index in matching_records.items():
        heading = _section_heading(content, structure, record[0])
        header = _table_header(structure, line_index)
        selected = _expand_short_spans(
            content,
            _merge_spans([span for span in (heading, header, record) if span is not None]),
        )
        groups.append(selected)
    _validate_evidence_size(
        [span for group in groups for span in group],
        operation="find_on_page",
    )
    return groups


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
        ref = session.next_ref()
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
        session.page_count += 1
    return cached


_REGION_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_REGION_BOLD_HEADING_RE = re.compile(r"^\*\*([^*]+)\*\*\s*$")
_REGION_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_REGION_LIST_RE = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+")
_REGION_TABLE_DELIMITER_RE = re.compile(r"^:?-{3,}:?$")


@dataclass(frozen=True)
class _RegionLine:
    number: int
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class _PageRegion:
    handle: str
    kind: str
    heading_path: tuple[str, ...]
    start_line: int
    end_line: int
    start_char: int
    end_char: int
    text: str
    embedding_text: str


@dataclass
class _PageRegionIndex:
    content_hash: str
    source_text: str
    regions: tuple[_PageRegion, ...]
    embeddings: dict[str, list[float]] = field(default_factory=dict)


@dataclass(frozen=True)
class _RegionReadUnit:
    context: str
    text: str
    spans: tuple[tuple[int, int], ...]


def _region_lines(text: str) -> tuple[_RegionLine, ...]:
    lines: list[_RegionLine] = []
    offset = 0
    for number, raw in enumerate(text.splitlines(keepends=True), start=1):
        lines.append(_RegionLine(number, offset, offset + len(raw), raw.rstrip("\r\n")))
        offset += len(raw)
    if not lines or offset < len(text):
        lines.append(_RegionLine(len(lines) + 1, offset, len(text), text[offset:]))
    return tuple(lines)


def _region_table_cells(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _region_table_delimiter(line: str) -> bool:
    cells = _region_table_cells(line)
    return bool(cells) and all(
        _REGION_TABLE_DELIMITER_RE.fullmatch(cell.replace(" ", "")) for cell in cells
    )


def _region_heading(lines: tuple[_RegionLine, ...], index: int) -> tuple[int, str] | None:
    text = lines[index].text.strip()
    match = _REGION_HEADING_RE.match(text)
    if match:
        return len(match.group(1)), match.group(2).strip()
    bold = _REGION_BOLD_HEADING_RE.match(text)
    if bold and index + 1 < len(lines) and not lines[index + 1].text.strip().startswith("|"):
        return 2, bold.group(1).strip()
    return None


def _region_table_start(lines: tuple[_RegionLine, ...], index: int) -> bool:
    return (
        index + 1 < len(lines)
        and lines[index].text.lstrip().startswith("|")
        and _region_table_delimiter(lines[index + 1].text)
    )


def _region_table_end(lines: tuple[_RegionLine, ...], start: int) -> int:
    expected_pipes = max(2, lines[start].text.count("|"))
    index = start + 2
    row_pipes = 0
    while index < len(lines):
        if _region_heading(lines, index) is not None:
            break
        text = lines[index].text
        if not text.strip():
            if row_pipes >= expected_pipes or row_pipes == 0:
                break
            index += 1
            continue
        if text.lstrip().startswith("|") and row_pipes >= expected_pipes:
            row_pipes = 0
        row_pipes += text.count("|")
        index += 1
    return index


def _make_page_region(
    ordinal: int,
    kind: str,
    heading_path: tuple[str, ...],
    lines: tuple[_RegionLine, ...],
    start: int,
    end: int,
    source: str,
    namespace: str,
) -> _PageRegion:
    text = source[lines[start].start : lines[end - 1].end].rstrip()
    digest = hashlib.sha256(f"{namespace}\0{kind}\0{text}".encode()).hexdigest()[:12]
    prefix = f"Heading: {' > '.join(heading_path) or '(document root)'}\nKind: {kind}\n"
    if len(text) <= 8_000:
        embedding_text = prefix + text
    else:
        middle = len(text) // 2
        embedding_text = (
            prefix
            + text[:2_500]
            + "\n[representative middle]\n"
            + text[middle - 1_250 : middle + 1_250]
            + "\n[representative tail]\n"
            + text[-2_500:]
        )
    return _PageRegion(
        handle=f"R{ordinal:04d}-{digest}",
        kind=kind,
        heading_path=heading_path,
        start_line=lines[start].number,
        end_line=lines[end - 1].number,
        start_char=lines[start].start,
        end_char=lines[end - 1].end,
        text=text,
        embedding_text=embedding_text,
    )


def _build_page_region_index(content: str, namespace: str) -> _PageRegionIndex:
    lines = _region_lines(content)
    headings: list[tuple[int, str]] = []
    regions: list[_PageRegion] = []
    index = 0
    while index < len(lines):
        heading = _region_heading(lines, index)
        if heading is not None:
            level, title = heading
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, title))
            index += 1
            continue
        if not lines[index].text.strip():
            index += 1
            continue
        start = index
        if _region_table_start(lines, index):
            kind = "table"
            index = _region_table_end(lines, index)
        elif fence := _REGION_FENCE_RE.match(lines[index].text):
            kind = "code"
            marker = fence.group(1)[0]
            index += 1
            while index < len(lines) and not lines[index].text.lstrip().startswith(marker * 3):
                index += 1
            index = min(len(lines), index + 1)
        elif _REGION_LIST_RE.match(lines[index].text):
            kind = "list"
            index += 1
            while index < len(lines):
                if not lines[index].text.strip() or _region_heading(lines, index) is not None:
                    break
                if _region_table_start(lines, index):
                    break
                if _REGION_LIST_RE.match(lines[index].text) or lines[index].text.startswith((" ", "\t")):
                    index += 1
                    continue
                break
        else:
            kind = "paragraph"
            index += 1
            while index < len(lines):
                if not lines[index].text.strip() or _region_heading(lines, index) is not None:
                    break
                if (
                    _region_table_start(lines, index)
                    or _REGION_LIST_RE.match(lines[index].text)
                    or _REGION_FENCE_RE.match(lines[index].text)
                ):
                    break
                index += 1
        regions.append(
            _make_page_region(
                len(regions) + 1,
                kind,
                tuple(title for _, title in headings),
                lines,
                start,
                index,
                content,
                namespace,
            )
        )

    heading_rows: list[tuple[int, int, tuple[str, ...]]] = []
    stack: list[tuple[int, str]] = []
    for line_index in range(len(lines)):
        heading = _region_heading(lines, line_index)
        if heading is None:
            continue
        level, title = heading
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        heading_rows.append((line_index, level, tuple(item[1] for item in stack)))
    for position, (heading_index, level, path) in enumerate(heading_rows):
        end = len(lines)
        for next_index, next_level, _ in heading_rows[position + 1 :]:
            if next_level <= level:
                end = next_index
                break
        start = heading_index + 1
        while start < end and not lines[start].text.strip():
            start += 1
        while end > start and not lines[end - 1].text.strip():
            end -= 1
        if start < end:
            regions.append(
                _make_page_region(
                    len(regions) + 1,
                    "section",
                    path,
                    lines,
                    start,
                    end,
                    content,
                    namespace,
                )
            )
    return _PageRegionIndex(
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        source_text=content,
        regions=tuple(regions),
    )


def _region_cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


async def _embed_page_regions(index: _PageRegionIndex) -> None:
    if index.embeddings:
        return
    searchable = [region for region in index.regions if region.kind != "section"]
    result = await embed_text(
        [region.embedding_text for region in searchable],
        provider="openrouter",
        model="qwen/qwen3-embedding-8b",
        input_type="document",
        dimensions=REGION_EMBEDDING_DIMENSIONS,
        timeout=EMBEDDING_TIMEOUT,
    )
    vectors = [item.embedding for item in sorted(result.response.data, key=lambda item: item.index)]
    if len(vectors) != len(searchable):
        raise RuntimeError(
            f"page-region embedding mismatch: expected {len(searchable)}, received {len(vectors)}"
        )
    index.embeddings = {
        region.handle: vector for region, vector in zip(searchable, vectors, strict=True)
    }


async def _rank_page_regions(index: _PageRegionIndex, query: str) -> list[tuple[_PageRegion, float]]:
    await _embed_page_regions(index)
    query_result = await embed_text(
        query,
        provider="openrouter",
        model="qwen/qwen3-embedding-8b",
        input_type="query",
        dimensions=REGION_EMBEDDING_DIMENSIONS,
        timeout=EMBEDDING_TIMEOUT,
    )
    query_vector = query_result.response.data[0].embedding
    section_by_path = {
        region.heading_path: region for region in index.regions if region.kind == "section"
    }
    groups: dict[str, tuple[_PageRegion, list[_PageRegion]]] = {}
    for region in index.regions:
        canonical = section_by_path.get(region.heading_path, region) if region.heading_path else region
        groups.setdefault(canonical.handle, (canonical, []))[1].append(region)
    scored: list[tuple[_PageRegion, float]] = []
    for canonical, members in groups.values():
        member_scores = [
            _region_cosine(query_vector, index.embeddings[member.handle])
            for member in members
            if member.handle in index.embeddings
        ]
        if member_scores:
            scored.append((canonical, max(member_scores)))
    scored.sort(key=lambda item: (-item[1], item[0].start_char))
    return scored[:REGION_RESULT_COUNT]


def _region_preview(region: _PageRegion) -> str:
    compact = re.sub(r"\s+", " ", region.text).strip()
    return compact if len(compact) <= 420 else compact[:417] + "..."


def _table_region_units(region: _PageRegion, nested_context: str = "") -> list[_RegionReadUnit]:
    lines = _region_lines(region.text)
    if len(lines) < 2 or not _region_table_delimiter(lines[1].text):
        return [_RegionReadUnit(nested_context, region.text, ((region.start_char, region.end_char),))]
    header_end = 2
    if header_end < len(lines):
        cells = [cell for cell in _region_table_cells(lines[header_end].text) if cell]
        if cells and not any(re.search(r"\d", cell) for cell in cells):
            header_end += 1
    header_start_char = region.start_char
    header_end_char = region.start_char + lines[header_end - 1].end
    header = region.text[: lines[header_end - 1].end].rstrip()
    context = "\n\n".join(part for part in (nested_context, header) if part)
    expected_pipes = max(2, lines[0].text.count("|"))
    rows: list[_RegionReadUnit] = []
    start = header_end
    while start < len(lines):
        end = start + 1
        pipes = lines[start].text.count("|")
        while end < len(lines) and pipes < expected_pipes:
            pipes += lines[end].text.count("|")
            end += 1
        row_start = region.start_char + lines[start].start
        row_end = region.start_char + lines[end - 1].end
        rows.append(
            _RegionReadUnit(
                context,
                region.text[lines[start].start : lines[end - 1].end].rstrip(),
                ((header_start_char, header_end_char), (row_start, row_end)),
            )
        )
        start = end
    return rows


def _region_read_units(index: _PageRegionIndex, region: _PageRegion) -> list[_RegionReadUnit]:
    if region.kind == "table":
        return _table_region_units(region)
    if region.kind != "section":
        return [_RegionReadUnit("", region.text, ((region.start_char, region.end_char),))]
    children = [
        child
        for child in index.regions
        if child.kind != "section"
        and child.start_char >= region.start_char
        and child.start_char < region.end_char
        and child.heading_path[: len(region.heading_path)] == region.heading_path
    ]
    units: list[_RegionReadUnit] = []
    for child in children:
        nested = child.heading_path[len(region.heading_path) :]
        context = f"Subheading: {' > '.join(nested)}" if nested else ""
        if child.kind == "table":
            units.extend(_table_region_units(child, context))
        else:
            units.append(
                _RegionReadUnit(context, child.text, ((child.start_char, child.end_char),))
            )
    return units or [_RegionReadUnit("", region.text, ((region.start_char, region.end_char),))]


async def _run_search_page(
    session: ResearchSession,
    url: str,
    query: str,
    preview_budget: int,
) -> dict[str, Any]:
    _result, content, title, effective_url = await _load_page(session, url)
    index = session.region_indexes.get(url)
    if index is None:
        index = _build_page_region_index(content, effective_url)
        session.region_indexes[url] = index
        for region in index.regions:
            registered = session.region_registry.get(region.handle)
            if registered is not None and registered[0] != url:
                raise RuntimeError(f"region handle collision: {region.handle}")
            session.region_registry[region.handle] = (url, region)
    ranked = await _rank_page_regions(index, query)
    candidates = [
        {
            "region": region.handle,
            "kind": region.kind,
            "heading_path": list(region.heading_path),
            "source_lines": [region.start_line, region.end_line],
            "preview": _region_preview(region),
            "similarity": round(score, 6),
        }
        for region, score in ranked
    ]
    if len(json.dumps(candidates, ensure_ascii=False)) > preview_budget:
        raise RuntimeError("search_page candidates exceed this tool call's preview budget")
    return {
        "ok": True,
        "title": title,
        "url": effective_url,
        "query": query,
        "candidates": candidates,
    }


async def _run_read_region(
    session: ResearchSession,
    handle_or_continuation: str,
    preview_budget: int,
) -> dict[str, Any]:
    handle, separator, offset_text = handle_or_continuation.partition("@")
    registered = session.region_registry.get(handle)
    if registered is None:
        raise ValueError(f"unknown region handle: {handle_or_continuation}")
    url, region = registered
    index = session.region_indexes[url]
    offset = int(offset_text) if separator else 0
    units = _region_read_units(index, region)
    if offset < 0 or offset >= len(units):
        raise ValueError(f"continuation offset is outside region: {handle_or_continuation}")
    prefix = f"Heading: {' > '.join(region.heading_path) or 'Document root'}\nKind: {region.kind}"
    selected: list[_RegionReadUnit] = []
    rendered: list[str] = []
    size = len(prefix)
    active_context: str | None = None
    cursor = offset
    page_limit = min(REGION_PAGE_CHARS, preview_budget)
    while cursor < len(units):
        unit = units[cursor]
        context = unit.context if unit.context != active_context else ""
        text = "\n\n".join(part for part in (context, unit.text) if part)
        if selected and size + len(text) + 2 > page_limit:
            break
        selected.append(unit)
        rendered.append(text)
        size += len(text) + 2
        active_context = unit.context
        cursor += 1
    result, content, title, effective_url = await _load_page(session, url)
    receipt_id, result_id = _result_identity(result, 0)
    spans = _expand_short_spans(
        content,
        _merge_spans([span for unit in selected for span in unit.spans]),
    )
    ref = session.next_ref()
    session.evidence.append(
        EvidenceRecord(
            ref=ref,
            key=f"page://{url}",
            title=title,
            url=effective_url,
            content=content,
            receipt_id=receipt_id,
            result_id=result_id,
            slices=tuple(CitationSlice(start=start, end=end) for start, end in spans),
        )
    )
    continuation = None if cursor >= len(units) else f"{handle}@{cursor}"
    return {
        "ok": True,
        "region": handle,
        "evidence": f"[{ref}]",
        "text": prefix + "\n\n" + "\n\n".join(rendered),
        "complete": continuation is None,
        "continuation": continuation,
    }


async def _run_read_page(session: ResearchSession, url: str, focus: str, preview_budget: int) -> dict[str, Any]:
    result, content, title, effective_url = await _load_page(session, url)
    spans = _ranked_page_spans(content, session.question, focus)
    previews = [_render_page_preview(content, [span]) for span in spans]
    if sum(len(preview) for preview in previews) > preview_budget:
        raise RuntimeError(f"read_page selected too much visible text for {url}; use a narrower focus")
    session.page_count += 1
    receipt_id, result_id = _result_identity(result, 0)
    records: list[dict[str, str]] = []
    for (start, end), preview in zip(spans, previews, strict=True):
        ref = session.next_ref()
        record = EvidenceRecord(
            ref=ref,
            key=f"page://{url}",
            title=title,
            url=effective_url,
            content=content,
            receipt_id=receipt_id,
            result_id=result_id,
            slices=(CitationSlice(start=start, end=end),),
        )
        session.evidence.append(record)
        records.append({"ref": f"[{ref}]", "text": preview})
    return {
        "ok": True,
        "vfs_key": f"page://{url}",
        "title": title,
        "url": url,
        "focus": focus,
        "attempts": result.response.attempts,
        "retry_reasons": result.response.retry_reasons,
        "evidence": records,
    }


async def _run_find_on_page(session: ResearchSession, url: str, text: str, preview_budget: int) -> dict[str, Any]:
    result, content, title, effective_url = await _load_page(session, url)
    groups = _exact_match_groups(content, text)
    if not groups:
        return {
            "ok": True,
            "complete": True,
            "matching_record_count": 0,
            "vfs_key": f"page://{url}",
            "title": title,
            "url": url,
            "text": f"No case-insensitive exact matches for {text!r}.",
        }

    previews = [_render_page_preview(content, spans) for spans in groups]
    if sum(len(preview) for preview in previews) > preview_budget:
        raise RuntimeError(
            f"find_on_page found {len(groups)} records requiring "
            f"{sum(len(preview) for preview in previews)} preview characters; "
            f"use a narrower exact string than {text!r}"
        )
    session.page_count += 1
    receipt_id, result_id = _result_identity(result, 0)
    records: list[dict[str, str]] = []
    for spans, preview in zip(groups, previews, strict=True):
        ref = session.next_ref()
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
        records.append({"ref": f"[{ref}]", "text": preview})
    return {
        "ok": True,
        "complete": True,
        "matching_record_count": len(groups),
        "vfs_key": f"page://{url}",
        "title": title,
        "url": url,
        "evidence": records,
    }


async def _execute_research_call(session: ResearchSession, call: Any, preview_budget: int) -> str | dict[str, Any]:
    try:
        if call.name == "search_web":
            arguments = _strict_arguments(call, {"query"})
            return await _run_search(session, arguments["query"], preview_budget)
        if call.name == "read_page":
            arguments = _strict_arguments(call, {"url", "focus"})
            return await _run_read_page(
                session,
                arguments["url"],
                arguments["focus"],
                preview_budget,
            )
        if call.name == "find_on_page":
            arguments = _strict_arguments(call, {"url", "text"})
            return await _run_find_on_page(
                session,
                arguments["url"],
                arguments["text"],
                preview_budget,
            )
        if call.name == "search_page":
            arguments = _strict_arguments(call, {"url", "query"})
            return await _run_search_page(
                session,
                arguments["url"],
                arguments["query"],
                preview_budget,
            )
        if call.name == "read_region":
            arguments = _strict_arguments(call, {"region"})
            return await _run_read_region(session, arguments["region"], preview_budget)
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
    except ToolInvocationError as fallback_error:
        raise RuntimeError(
            f"{stage} primary and fallback LLM calls failed; "
            f"primary_provider=openrouter primary={primary_error_detail}; "
            f"fallback_provider={fallback_provider} fallback={fallback_error}"
        ) from fallback_error


def _proven_answer_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "submit_proven_answer",
            "description": (
                "Submit the complete evidence-backed answer and the small set of numbered evidence records that "
                "materially support it. Call this only when research is complete, and never alongside research tools."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "minLength": 1,
                        "description": "The complete final answer, obeying every reader-facing format requirement.",
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 1},
                        "minItems": 1,
                        "description": "Observed evidence numbers, such as [2, 5], without the E prefix.",
                    },
                },
                "required": ["text", "evidence"],
                "additionalProperties": False,
            },
            "strict": False,
        },
    }


async def _call_researcher(messages: list[Any]) -> Any:
    tools = [*RESEARCH_TOOLS, _proven_answer_tool()]
    return await _llm_chat_with_fallback(
        stage="research",
        model="z-ai/glm-5.2",
        fallback_model=RESEARCH_FALLBACK_MODEL,
        fallback_provider=RESEARCH_FALLBACK_PROVIDER,
        messages=messages,
        temperature=0.2,
        tools=tools,
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
) -> tuple[ResearchResult, list[Any], int]:
    for turns_used in range(1, turn_budget + 1):
        result = await _call_researcher(messages)
        assistant = _assistant_message(result)
        calls = list(assistant.tool_calls or ())
        if not calls:
            answer = _assistant_text(result)
            if not answer:
                raise RuntimeError("researcher returned neither tool calls nor prose")
            messages.extend(
                [
                    assistant.to_input_message(),
                    {
                        "role": "user",
                        "content": (
                            "Final output must use submit_proven_answer so the answer and its evidence remain separate. "
                            "Continue research if needed; otherwise call that tool once."
                        ),
                    },
                ]
            )
            continue
        if len(calls) > MAX_PARALLEL_TOOL_CALLS:
            raise RuntimeError(
                f"researcher requested {len(calls)} tools in one turn; ceiling is {MAX_PARALLEL_TOOL_CALLS}"
            )

        final_calls = [call for call in calls if call.name == "submit_proven_answer"]
        if final_calls:
            messages.append(assistant.to_input_message())
            error: Exception | None = None
            try:
                if len(calls) != 1:
                    raise ValueError("the final submission must be the sole tool call in its response")
                arguments = json.loads(final_calls[0].arguments)
                expected_fields = {"text", "evidence"}
                if not isinstance(arguments, dict) or set(arguments) != expected_fields:
                    raise ValueError(f"{final_calls[0].name} requires only {sorted(expected_fields)}")
                answer = arguments["text"]
                if not isinstance(answer, str) or not answer.strip():
                    raise ValueError("text must be the non-empty complete answer")
                if re.search(r"https?://|\bwww\.", answer, flags=re.IGNORECASE):
                    raise ValueError("do not render raw URLs in the final answer")
                evidence = arguments["evidence"]
                if not isinstance(evidence, list) or not evidence:
                    raise ValueError("evidence must be a non-empty array of observed evidence numbers")
                if any(isinstance(number, bool) or not isinstance(number, int) for number in evidence):
                    raise ValueError("every evidence item must be an integer")
                numbers = list(dict.fromkeys(evidence))
                unavailable = [number for number in numbers if number < 1 or number > len(session.evidence)]
                if unavailable:
                    raise ValueError(f"evidence numbers were not observed: {unavailable}")
                refs = tuple(f"E{number}" for number in numbers)
                if answer is not None:
                    inline_refs = _private_refs(answer)
                    unknown_inline = [ref for ref in inline_refs if ref not in refs]
                    if unknown_inline:
                        raise ValueError(
                            f"text cites evidence absent from the evidence list: {unknown_inline}"
                        )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": final_calls[0].id,
                        "content": json.dumps({"ok": True, "status": "proven_answer_accepted"}),
                    }
                )
                return ResearchResult(answer=answer, evidence_refs=refs), messages, turns_used
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as caught:
                error = caught
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": final_calls[0].id,
                    "content": json.dumps(
                        {
                            "ok": False,
                            "error_type": "tool_argument_validation",
                            "details": str(error),
                        }
                    ),
                }
            )
            continue

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


_PRIVATE_REF_GROUP = re.compile(r"\[((?:E\d+\s*,\s*)*E\d+)\]")


def _refs_in_group(match: re.Match[str]) -> list[str]:
    return [ref.strip() for ref in match.group(1).split(",")]


def _private_refs(answer: str) -> list[str]:
    refs = (ref for match in _PRIVATE_REF_GROUP.finditer(answer) for ref in _refs_in_group(match))
    return list(dict.fromkeys(refs))


def _validate_private_answer(answer: str, session: ResearchSession) -> None:
    if "[[" in answer or "]]" in answer:
        raise ValueError("use private evidence refs such as [E1], not public citation indices")
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
    if re.search(r"\[(?:E\d+[^\]]*|[^\]]*E\d+)\]", without_refs):
        raise ValueError("private refs must use [E1] or a comma-separated group such as [E1, E2]")


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
                "such as [E1] or a comma-separated group such as [E1, E2]. Use only observed refs.\n\n"
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
    messages: list[Any] = [
        {"role": "system", "content": AUDIT_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Original question:\n{session.question}\n\nCandidate answer:\n{answer}\n\n"
                f"Evidence ledger (only cited records):\n{_audit_evidence_digest(session, answer)}"
            ),
        },
    ]
    for attempt in range(3):
        result = await _llm_chat_with_fallback(
            stage="audit",
            model="openai/gpt-oss-120b",
            fallback_model="openai/gpt-oss-120b",
            fallback_provider=RESEARCH_FALLBACK_PROVIDER,
            messages=messages,
            temperature=0.0,
            tools=AUDIT_TOOLS,
            tool_choice="required",
            parallel_tool_calls=False,
            thinking={"enabled": True, "effort": "high"},
            provider_extra={"provider": {"only": ["cerebras"], "allow_fallbacks": False}},
        )
        assistant = None
        calls: list[Any] = []
        try:
            assistant = _assistant_message(result)
            calls = list(assistant.tool_calls or ())
            if len(calls) != 1:
                raise ValueError(f"auditor must make exactly one decision; received {len(calls)} calls")
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
        except (RuntimeError, ValueError) as error:
            if attempt == 2:
                raise RuntimeError(f"audit decision validation failed after feedback: {error}") from error
            logger.warning("audit_decision_validation_retry error=%s", error)
            if assistant is not None:
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
                        "content": (
                            f"Audit decision contract error: {error}. Re-evaluate the same answer and evidence, "
                            "then call exactly one of accept_answer or request_repair. Do not answer in prose."
                        ),
                    }
                )
    raise AssertionError("unreachable")


def _render_response(
    session: ResearchSession,
    answer: str,
    evidence_refs: tuple[str, ...],
) -> Response:
    if "[[" in answer or "]]" in answer:
        raise ValueError("use private evidence refs such as [E1], not public citation indices")
    inline_refs = _private_refs(answer)
    unknown_inline = [ref for ref in inline_refs if ref not in evidence_refs]
    if unknown_inline:
        raise ValueError(f"answer cites evidence absent from its evidence list: {unknown_inline}")
    citations, indices = _citation_bundle(session, evidence_refs)
    rendered = _PRIVATE_REF_GROUP.sub(
        lambda match: "".join(
            f"[[{index}]]"
            for index in dict.fromkeys(indices[ref] for ref in _refs_in_group(match))
        ),
        answer,
    )
    rendered = re.sub(r"(\[\[\d+\]\])(?:\s*\1)+", r"\1", rendered)
    return Response(text=rendered, citations=citations)


def _citations_for_refs(session: ResearchSession, refs: tuple[str, ...]) -> list[CitationRef]:
    citations, _ = _citation_bundle(session, refs)
    return citations


def _citation_bundle(
    session: ResearchSession,
    refs: tuple[str, ...],
) -> tuple[list[CitationRef], dict[str, int]]:
    records = session.evidence_by_ref()
    selected_spans = [
        (slice_.start, slice_.end)
        for ref in refs
        for slice_ in records[ref].slices
    ]
    _validate_evidence_size(selected_spans, operation="structured answer")
    group_order: list[tuple[str, str]] = []
    group_indices: dict[tuple[str, str], int] = {}
    grouped_spans: dict[tuple[str, str], list[tuple[int, int]]] = {}
    ref_indices: dict[str, int] = {}
    for ref in refs:
        record = records[ref]
        key = (record.receipt_id, record.result_id)
        if key not in grouped_spans:
            group_order.append(key)
            group_indices[key] = len(group_order)
            grouped_spans[key] = []
        ref_indices[ref] = group_indices[key]
        grouped_spans[key].extend((slice_.start, slice_.end) for slice_ in record.slices)
    citations = [
        CitationRef(
            receipt_id=receipt_id,
            result_id=result_id,
            slices=[CitationSlice(start=start, end=end) for start, end in _merge_spans(grouped_spans[key])],
        )
        for key in group_order
        for receipt_id, result_id in [key]
    ]
    return citations, ref_indices


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


async def _project_structured_output(
    messages: list[Any],
    output_schema: dict[str, Any],
) -> Any:
    tool, direct_object = _structured_output_tool(output_schema)
    projection_messages: list[Any] = [
        *messages,
        {
            "role": "user",
            "content": (
                "The evidence-backed answer you just submitted is accepted as final and authoritative. Convert only "
                "that answer to the JSON Schema below. Do not research again, add facts, change names or values, "
                "reconsider the conclusion, or select evidence again. Call submit_structured_output exactly once.\n\n"
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
            messages=projection_messages,
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
        projection_messages.append(assistant.to_input_message())
        if calls:
            for call in calls:
                projection_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            {"ok": False, "error_type": "tool_argument_validation", "details": str(error)}
                        ),
                    }
                )
        else:
            projection_messages.append(
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


async def _w2_baseline_query(query_input: Query) -> Response:
    session = ResearchSession(question=query_input.text)
    response_contract = ""
    if query_input.output_schema is not None:
        response_contract = (
            "\n\nCaller response contract:\n"
            "The final response must match this JSON Schema. Treat it as part of the response contract throughout "
            "the investigation. Before finalizing, decide every required leaf value exactly as it should appear in "
            "the schema and state those exact values in the evidence-backed prose answer. Preserve source-native "
            "labels when the question asks for a value from a named source; do not replace them with a broader "
            "category, a shorter synonym, or an explanatory alias. Do not enrich a requested name with a second "
            "equivalent name unless the question or evidence requires both. Do not output JSON during research.\n"
            f"{json.dumps(query_input.output_schema, ensure_ascii=False, indent=2)}"
        )
    messages: list[Any] = [
        {"role": "system", "content": RESEARCH_SYSTEM},
        {
            "role": "user",
            "content": f"Original question:\n{query_input.text}{response_contract}",
        },
    ]
    result, messages, _turns_used = await _research_until_answer(
        session,
        messages,
        turn_budget=RESEARCH_TURN_CEILING,
    )
    if query_input.output_schema is None:
        return _render_response(session, result.answer, result.evidence_refs)
    output = await _project_structured_output(messages, query_input.output_schema)
    return Response(
        output=output,
        citations=_citations_for_refs(session, result.evidence_refs),
    )


# --- w2 answer-contract wrapper (begin) ---
# The base artifact's `query` entrypoint is demoted to `_w2_baseline_query` and a
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


def _w2_provider() -> str:
    """Resolve the base's LLM provider without globals(); the validator rejects it."""
    try:
        return LLM_PROVIDER
    except NameError:
        return "openrouter"


def _w2_model() -> str:
    try:
        return MODEL
    except NameError:
        return "z-ai/glm-5"


def _w2_total_budget_seconds() -> float:
    try:
        return float(TASK_TOTAL_BUDGET_SECONDS)
    except (NameError, TypeError, ValueError):
        return _W2_DEFAULT_BUDGET_SECONDS


def _w2_remaining(deadline: float) -> float:
    return deadline - perf_counter()


async def _w2_chat(messages: list[dict[str, object]], *, timeout: float, temperature: float) -> str:
    """One bounded LLM call on the platform ABI; empty string on any failure."""
    if timeout <= 0:
        return ""
    try:
        result = await llm_chat(
            provider=_w2_provider(), model=_w2_model(), messages=messages,
            temperature=temperature, timeout=timeout,
        )
    except Exception:
        return ""
    try:
        return (result.response.raw_text or "").strip()
    except Exception:
        return ""


def _w2_json_object(text: str) -> dict | None:
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


def _w2_string_list(value: object, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    items = []
    for entry in value:
        if isinstance(entry, str) and entry.strip():
            items.append(entry.strip())
        if len(items) >= limit:
            break
    return items


def _w2_schema_hint(schema: object) -> str:
    """Render the caller's output schema for the planning prompt."""
    if schema is None:
        return ""
    try:
        rendered = json.dumps(schema, ensure_ascii=False)[:1_200]
    except (TypeError, ValueError):
        return ""
    return f"\n\nThe answer will be returned against this output schema:\n{rendered}"


async def _w2_build_answer_contract(
    question: str, schema: object, *, deadline: float,
) -> _W2AnswerContract | None:
    """Stage 1 - plan the acceptance criteria before the baseline research runs."""
    timeout = min(_W2_PLAN_TIMEOUT_SECONDS, _w2_remaining(deadline) - _W2_TAIL_RESERVE_SECONDS)
    messages = [
        {"role": "system", "content": _W2_PLAN_SYSTEM},
        {"role": "user", "content": f"Question:\n{question}{_w2_schema_hint(schema)}"},
    ]
    payload = _w2_json_object(await _w2_chat(
        messages, timeout=timeout, temperature=_W2_PLAN_TEMPERATURE,
    ))
    if payload is None:
        return None
    deliverable = payload.get("deliverable")
    contract = _W2AnswerContract(
        deliverable=deliverable.strip() if isinstance(deliverable, str) else "",
        required=_w2_string_list(payload.get("required"), _W2_MAX_CONTRACT_ITEMS),
        pitfalls=_w2_string_list(payload.get("pitfalls"), 3),
    )
    return contract if contract.is_actionable() else None


def _w2_contract_block(contract: _W2AnswerContract) -> str:
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


def _w2_response_text(response: object) -> str:
    try:
        text = getattr(response, "text", None)
    except Exception:
        return ""
    return text.strip() if isinstance(text, str) else ""


def _w2_with_text(response: object, text: str) -> object:
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


def _w2_normalize_figure(token: str) -> str:
    """One numeric literal reduced to the value it states, not how it is typed."""
    value = token.replace(",", "")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    return value or "0"


def _w2_figures(text: str) -> set:
    """Every quantity the text asserts, less the ordinals that only number a list."""
    body = _W2_LIST_MARKER_RE.sub(" ", text)
    found = set()
    for match in _W2_FIGURE_RE.finditer(body):
        found.add(_w2_normalize_figure(match.group(0)))
    return found


def _w2_entities(text: str) -> set:
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


def _w2_unmakes_draft(draft: str, revision: str) -> bool:
    """True when the revision fails to carry forward something the draft asserted."""
    if not _w2_figures(draft).issubset(_w2_figures(revision)):
        return True
    return not _w2_entities(draft).issubset(_w2_entities(revision))


def _w2_accept_revision(draft: str, revision: str) -> bool:
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
    return not _w2_unmakes_draft(draft, revision)


async def _w2_verify_against_contract(
    contract: _W2AnswerContract, question: str, draft: str, *, deadline: float,
) -> str:
    """Stage 3 - audit the draft against the contract and return the answer to deliver."""
    timeout = min(_W2_VERIFY_TIMEOUT_SECONDS, _w2_remaining(deadline) - _W2_TAIL_RESERVE_SECONDS)
    messages = [
        {"role": "system", "content": _W2_VERIFY_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\nAnswer contract:\n{_w2_contract_block(contract)}"
                f"\n\nDraft answer:\n{draft[:_W2_DRAFT_PROMPT_CHARS]}"
            ),
        },
    ]
    revision = await _w2_chat(messages, timeout=timeout, temperature=_W2_VERIFY_TEMPERATURE)
    return revision if _w2_accept_revision(draft, revision) else draft


def _w2_schema_property_names(schema: object) -> list[str]:
    if not isinstance(schema, dict):
        return []
    properties = schema.get("properties")
    return [key for key in properties] if isinstance(properties, dict) else []


def _w2_is_degenerate_output(output: object, schema: object) -> bool:
    """True when the base produced a structured payload the scorer will read as empty."""
    if output is None:
        return True
    if isinstance(output, (str, list, tuple, dict)) and len(output) == 0:
        return True
    if isinstance(output, dict):
        names = _w2_schema_property_names(schema)
        if names and not any(key in output for key in names):
            return True
        if all(value in (None, "", [], {}) for value in output.values()):
            return True
    return False


async def _w2_repair_structured_output(
    question: str, schema: object, response: object, *, deadline: float,
) -> object:
    """Repair-only ladder: a working structured payload is always returned untouched."""
    output = getattr(response, "output", None)
    if not _w2_is_degenerate_output(output, schema):
        return response
    draft = _w2_response_text(response)
    recovered = _w2_json_object(draft)
    if recovered is None:
        timeout = min(_W2_REPAIR_TIMEOUT_SECONDS, _w2_remaining(deadline) - 2.0)
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
        recovered = _w2_json_object(await _w2_chat(messages, timeout=timeout, temperature=0.0))
    if recovered is None or _w2_is_degenerate_output(recovered, schema):
        return response
    citations = getattr(response, "citations", None)
    try:
        if citations:
            return Response(output=recovered, citations=citations)
        return Response(output=recovered)
    except Exception:
        return response


async def _w2_research_or_salvage(query_input: Query) -> Response:
    """Stage 2 - the research stage, held so no tool failure can leave the entrypoint.

    A hosted tool call that overruns its own `timeout=` raises out of the research
    stage, and the platform charges an escaping exception to the miner. The stage
    therefore always resolves to a response the later stages can still work on.
    """
    try:
        return await _w2_baseline_query(query_input)
    except Exception:
        return Response(text="No verifiable source-backed answer was reached for this question.")


@entrypoint("query")
async def query(query: Query) -> Response:
    """w2 contract wrapper: plan the answer contract, run the baseline, then verify.

    The baseline artifact's own entrypoint is demoted to `_w2_baseline_query` and
    runs as the research stage of this sequence. Contract planning runs on every
    ordinary request before the research starts, and the verification stage holds
    authority over the answer this entrypoint returns.
    """
    deadline = perf_counter() + _w2_total_budget_seconds()
    question = getattr(query, "text", "") or ""
    schema = getattr(query, "output_schema", None)

    contract = await _w2_build_answer_contract(question, schema, deadline=deadline)
    response = await _w2_research_or_salvage(query)

    if contract is not None:
        draft = _w2_response_text(response)
        if draft:
            audited = await _w2_verify_against_contract(
                contract, question, draft, deadline=deadline,
            )
            if audited != draft:
                response = _w2_with_text(response, audited)
    if schema is not None:
        response = await _w2_repair_structured_output(
            question, schema, response, deadline=deadline,
        )
    return response
# --- w2 answer-contract wrapper (end) ---
# slot: 03 FB_526bfbe6_w2 2026-08-09T09:19:56+00:00
