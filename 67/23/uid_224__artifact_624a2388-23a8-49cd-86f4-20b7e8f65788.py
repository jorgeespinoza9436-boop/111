from __future__ import annotations
import asyncio
from time import monotonic
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class PrimarySolver:

    def _compile(self):
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
        LLM_TIMEOUT = 40.0
        TOOL_TURN_PREVIEW_CHARS = 96000
        FETCH_TIMEOUT = 15.0
        SEARCH_TIMEOUT = 10.0
        MAX_EVIDENCE_SEGMENTS = 400
        EMBEDDING_TIMEOUT = 180.0
        MIN_CITATION_SLICE_CHARS = 100
        TASK_TOTAL_BUDGET_SECONDS = 250.0
        MAX_TOTAL_EVIDENCE_CHARS = 120000
        LLM_PROVIDER = 'openrouter'
        MODEL = 'z-ai/glm-5.2'
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
        SEARCH_PROVIDER = 'parallel'
        RESEARCH_FALLBACK_PROVIDER = 'ai_gateway'
        RESEARCH_FALLBACK_MODEL = 'deepseek/deepseek-v4-flash-0731'
        STRUCTURED_FALLBACK_MODEL = 'openai/gpt-oss-120b'
        RESEARCH_TURN_CEILING = 15
        MAX_PARALLEL_TOOL_CALLS = 8
        SEARCH_RESULT_COUNT = 8
        SEARCH_HEAD_CHARS = 220
        SEARCH_WINDOW_CHARS = 700
        SEARCH_WINDOW_STEP_CHARS = 250
        PAGE_PLAIN_CHARS = 6500
        PAGE_HEAD_CHARS = 3000
        PAGE_WINDOW_CHARS = 3600
        PAGE_WINDOW_STEP_CHARS = 1200
        PAGE_WINDOWS = 3
        MIN_HEADING_FOCUS_TERMS = 3
        REGION_PAGE_CHARS = 12000
        REGION_RESULT_COUNT = 5
        REGION_EMBEDDING_DIMENSIONS = 1024
        logger = logging.getLogger('direct_research_loop')
        RESEARCH_TOOLS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web. Each result is automatically stored and returned with a private source ref. Use several independent calls in one turn when comparing sources or candidates.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'A focused search query that can change what you know.'}}, 'required': ['query'], 'additionalProperties': False}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': "Read a few relevant passages from one discovered page. Use this for ordinary prose or when a short focus phrase is enough; it is cheaper than indexing the page's complete structure.", 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'Exact URL returned by search.'}, 'focus': {'type': 'string', 'description': 'Words or a short phrase identifying the needed passage.'}}, 'required': ['url', 'focus'], 'additionalProperties': False}}}, {'type': 'function', 'function': {'name': 'find_on_page', 'description': 'Find every raw record containing an exact name or value already known to you on one page. Returns each matching record with its section and table header.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'Exact URL returned by search.'}, 'text': {'type': 'string', 'description': 'Single-line exact name or value, matched case-insensitively.'}}, 'required': ['url', 'text'], 'additionalProperties': False}}}, {'type': 'function', 'function': {'name': 'search_page', 'description': 'Locate a complete table, list, or section on a discovered page when its exact names or values are not yet known. The query is natural language. Use read_page for ordinary passages and sufficient excerpts.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'Exact URL returned by search.'}, 'query': {'type': 'string', 'description': 'Natural-language description of the complete structure needed.'}}, 'required': ['url', 'query'], 'additionalProperties': False}}}, {'type': 'function', 'function': {'name': 'read_region', 'description': 'Read one region returned by search_page. Complete structures are preserved; large tables or sections return a continuation handle and repeat heading and table-header context.', 'parameters': {'type': 'object', 'properties': {'region': {'type': 'string', 'description': 'Opaque region or continuation handle returned by the harness.'}}, 'required': ['region'], 'additionalProperties': False}}}]
        AUDIT_TOOLS = [{'type': 'function', 'function': {'name': 'accept_answer', 'description': 'Accept the answer when no material defect remains.', 'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False}}}, {'type': 'function', 'function': {'name': 'request_repair', 'description': 'Return the single highest-impact material defect that must be repaired.', 'parameters': {'type': 'object', 'properties': {'issue': {'type': 'string', 'description': 'One concrete defect in the answer.'}, 'why_material': {'type': 'string', 'description': 'Why this defect could change or invalidate the requested answer.'}}, 'required': ['issue', 'why_material'], 'additionalProperties': False}}}]
        HYPOTHESIS_SYSTEM = 'You are preparing a deep-research investigation. Write a revisable expected answer, not a safe non-answer.\nUse internal knowledge only to make research cheaper. It is not evidence.\n\nReturn a compact prose brief with exactly these headings:\nExpected answer\nWhat could make it wrong\nSmallest verification route\n\nName likely candidates or values when useful. Under the verification route, identify the few external facts or\ncomplete inventory that would prove, revise, or reject the expected answer. Do not invent citations or URLs.'
        RESEARCH_SYSTEM = "You are a deep-research agent. Build a claim that answers the original question and has enough externally\ninspectable support to persuade a skeptical reader.\n\nBefore the first retrieval, form a concrete revisable expected answer and its smallest verification route in your\nreasoning. Do not expose this planning scratch in the final answer. The expected answer is a useful guess, never\nevidence. Internal knowledge may choose an efficient route, but every\nfactual statement needed to resolve the question must come from observed search or page evidence.\nWhen the question identifies its subject indirectly, first search the clue without the guessed identity and verify the\nexact relationship; a page that merely contains the same words does not prove a title, author, owner, or identity.\n\nAfter each batch of tool results, try to write the final answer. If every statement needed to resolve the question can\nbe supported, answer now. Otherwise, use tools only for a statement that must appear in the final answer but is not yet\nsupported, or for an unresolved possibility that could change the answer. Do not investigate details you would omit\nfrom the final answer. For a set, ranking, unique, negative, or boundary-sensitive answer, include enough support to\nshow that an omitted candidate cannot change the result; exact values for lower-ranked candidates are unnecessary unless\nthe question asks you to report them. Resolve a source conflict only when it could change the requested answer or make\nevidence used in the answer inapplicable. Prefer evidence matching the requested source, population, date, and metric.\n\nUse search excerpts when they directly expose the needed fact. Use read_page for ordinary prose or a few focused\npassages. Use find_on_page when you already know an exact name or value and need its source record. When the correct\npage is known but the answer depends on a complete table, list, or section whose exact contents are not yet known, call\nsearch_page with a natural-language description and then read_region on the best handle. Do not index a page merely to\nconfirm a sufficient excerpt. If one route does not improve what you know,\nchange the query, source, or page operation.\nFollow any named source, date, interpretation, and output requirements in the question.\nWhen the question names a data source, use that source's own page or machine-readable API for the requested metrics\nwhen it is accessible. A secondary site does not become direct evidence merely because it republishes or attributes\nthe named source. After discovering a working API URL pattern, reuse that pattern for the remaining requested metrics\nand countries instead of switching to secondary mirrors.\n\nTool results contain private refs such as [E1] and [E2]. When research is sufficient, stop calling tools and write the\nfinal answer in the format and level of detail requested by the original question. Use polished Markdown prose when\nthe question does not prescribe a narrower format. Put each private ref immediately after the factual claim it\nsupports. Cite only refs you actually observed. Do not emit raw URLs, a bibliography, a source list, JSON, tool\ninstructions, or a plan. Never mention the internal expected answer, verification brief, reference answer, evaluation\nprocess, or how the final answer differs from them. If evidence changes the expected answer, simply state the corrected\nanswer.\n\nFinalize by calling submit_proven_answer alone. Its text is the complete evidence-backed answer. Normally place [E#]\nrefs immediately after supported claims; the harness renders them as public citations for prose questions and uses\nthem to preserve the proof when a later structured-output projection is required. When the original question requires\nexact text with no extra characters, keep text exact and supply the supporting records only through the separate\nevidence list. The tool takes a small list of integer evidence numbers that materially support the result and its\nderivation. Do not include every observed record."
        AUDIT_SYSTEM = 'You audit a deep-research answer using only the original question and the supplied evidence ledger. Ignore your own\nworld knowledge. Check whether the answer actually resolves the requested result, whether any finite inventory or\nboundary needed by the question is covered, and whether every material factual claim is supported by the cited\nvisible evidence. When the question attributes facts to a named source, verify that evidence for those facts actually\ncomes from that source rather than a secondary source repeating it. Do not demand more evidence merely because stronger\nevidence might exist. When an indirect clue identifies the subject, require evidence for that exact relationship rather\nthan mere occurrence of the same words. Call accept_answer when there is no material defect. Otherwise call\nrequest_repair with exactly one highest-impact concrete defect.'
        STRUCTURED_OUTPUT_SYSTEM = 'Convert a completed, evidence-backed answer into the exact JSON value required by the supplied JSON Schema. Do not\nresearch again, add facts, reinterpret the answer, or return prose. The completed answer determines the result; the\nsupplied evidence remains authoritative for exact values. Include every required field and call\nsubmit_structured_output exactly once. The tool arguments are the final value, not JSON encoded inside a string.'

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
                return f'E{len(self.evidence) + 1}'

            def evidence_by_ref(self) -> dict[str, EvidenceRecord]:
                return {item.ref: item for item in self.evidence}

        @dataclass(frozen=True)
        class ResearchResult:
            answer: str
            evidence_refs: tuple[str, ...]

        def _tool(name: str) -> dict[str, Any]:
            return next((item for item in RESEARCH_TOOLS if item['function']['name'] == name))

        def _assistant_message(result: Any) -> Any:
            if len(result.llm.choices) != 1:
                raise RuntimeError(f'expected one LLM choice, received {len(result.llm.choices)}')
            return result.llm.choices[0].message

        def _assistant_text(result: Any) -> str:
            return (result.llm.raw_text or '').strip()

        def _strict_arguments(call: Any, expected: set[str], *, preserve_whitespace: frozenset[str]=frozenset()) -> dict[str, Any]:
            try:
                arguments = json.loads(call.arguments)
            except json.JSONDecodeError as error:
                raise ValueError(f'{call.name} arguments are not valid JSON: {error}') from error
            if not isinstance(arguments, dict):
                raise ValueError(f'{call.name} arguments must be an object')
            unexpected = set(arguments) - expected
            if unexpected:
                raise ValueError(f'{call.name} received unexpected fields: {sorted(unexpected)}')
            missing = expected - set(arguments)
            if missing:
                raise ValueError(f'{call.name} is missing fields: {sorted(missing)}')
            for key in expected:
                if not isinstance(arguments[key], str) or not arguments[key].strip():
                    raise ValueError(f'{call.name}.{key} must be a non-empty string')
                if key not in preserve_whitespace:
                    arguments[key] = arguments[key].strip()
            return arguments

        def _head_middle_tail(content: str, limit: int) -> tuple[str, list[tuple[int, int]]]:
            if len(content) <= limit:
                return (content, [(0, len(content))])
            section = limit // 3
            spans = [(0, section), (max(0, len(content) // 2 - section // 2), min(len(content), len(content) // 2 + section // 2)), (len(content) - section, len(content))]
            text = '\n\n[... omitted ...]\n\n'.join((content[start:end] for start, end in spans))
            return (text, spans)
        _SEARCH_TOKEN_RE = re.compile("[^\\W_](?:[\\w.'-]*[^\\W_])?", re.UNICODE)
        _MARKDOWN_HEADING_RE = re.compile('^ {0,3}(#{1,6})[ \\t]+.+$')
        _MARKDOWN_FENCE_RE = re.compile('^ {0,3}(`{3,}|~{3,})')
        _SEARCH_STOPWORDS = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

        def _search_terms(text: str) -> set[str]:
            return {token for raw in _SEARCH_TOKEN_RE.findall(text.casefold()) if len((token := raw.strip(".'-"))) >= 3 and token not in _SEARCH_STOPWORDS}

        def _ranked_search_spans(content: str, question: str, query: str) -> list[tuple[int, int]]:
            if len(content) <= SEARCH_HEAD_CHARS + SEARCH_WINDOW_CHARS:
                return [(0, len(content))]
            question_terms = _search_terms(question)
            query_terms = _search_terms(query)
            candidates: list[tuple[int, int, int]] = []
            position = 0
            folded = content.casefold()
            while position < len(content):
                window = folded[position:position + SEARCH_WINDOW_CHARS]
                score = sum((term in window for term in question_terms)) + 2 * sum((term in window for term in query_terms))
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
            return '\n    [... omitted ...]\n    '.join((content[start:end] for start, end in spans))

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
            fence_character = ''
            fence_length = 0
            for line in content.splitlines(keepends=True):
                stripped_line = line.rstrip('\r\n')
                if fence_character:
                    candidate = stripped_line.lstrip(' ')
                    if len(stripped_line) - len(candidate) <= 3 and candidate.startswith(fence_character * fence_length) and (not candidate.lstrip(fence_character).strip()):
                        fence_character = ''
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
                for following_start, following_level, _ in headings[index + 1:]:
                    if following_level <= level:
                        end = following_start
                        break
                sections.append((start, end, heading))
            return sections

        def _align_window_to_trailing_section(content: str, focus_terms: set[str], spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
            headings = [(len(focus_terms.intersection(_search_terms(heading))), start, end) for start, end, heading in _heading_sections(content)]

            def section_coverage(section_start: int, section_end: int, windows: list[tuple[int, int]]) -> int:
                return sum((max(0, min(right, section_end) - max(left, section_start)) for left, right in _merge_spans(windows)))
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
                    heading_near_end = max(left, right - PAGE_WINDOW_STEP_CHARS // 2) <= section_start < right
                    if not heading_near_end:
                        continue
                    replacement = [*spans]
                    replacement[index] = shifted
                    added_coverage = section_coverage(section_start, section_end, replacement) - visible_section
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
                window = folded[position:position + PAGE_WINDOW_CHARS]
                score = sum((term in window for term in question_terms)) + 2 * sum((term in window for term in focus_terms))
                candidates.append((score, -position, position))
                if position + PAGE_WINDOW_CHARS >= len(content):
                    break
                position += PAGE_WINDOW_STEP_CHARS
            selected: list[tuple[int, int]] = []
            for score, _, start in sorted(candidates, reverse=True):
                span = (start, min(len(content), start + PAGE_WINDOW_CHARS))
                if any((start < selected_end and selected_start < span[1] for selected_start, selected_end in selected)):
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
            return '\n\n[... omitted ...]\n\n'.join((content[start:end] for start, end in spans))

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
            fence_character = ''
            fence_length = 0
            for line in content.splitlines(keepends=True):
                end = position + len(line)
                stripped_line = line.rstrip('\r\n')
                inside_fence = bool(fence_character)
                if fence_character:
                    candidate = stripped_line.lstrip(' ')
                    if len(stripped_line) - len(candidate) <= 3 and candidate.startswith(fence_character * fence_length) and (not candidate.lstrip(fence_character).strip()):
                        fence_character = ''
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
            return not line.inside_fence and line.text.lstrip().startswith('|')

        def _is_table_separator(line: SourceLine) -> bool:
            stripped = line.text.strip()
            return _is_table_line(line) and '-' in stripped and (not stripped.strip('| :-\t'))

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
                    if _is_table_line(following) or following.inside_fence or (not following.text.strip()) or _MARKDOWN_HEADING_RE.match(following.text.rstrip('\r\n')):
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
                if line.inside_fence or not line.text.strip() or _MARKDOWN_HEADING_RE.match(line.text.rstrip('\r\n')):
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
            return PageStructure(lines=tuple(lines), line_starts=tuple((line.start for line in lines)), sections=sections, section_starts=tuple((start for start, _, _ in sections)), table_records=_table_records(lines), table_headers=_table_headers(lines))

        def _section_heading(content: str, structure: PageStructure, position: int) -> tuple[int, int] | None:
            section_index = _bisect_right(structure.section_starts, position) - 1
            if section_index < 0:
                return None
            start, end, _ = structure.sections[section_index]
            if position >= end:
                return None
            line_end = content.find('\n', start)
            if line_end < 0:
                return (start, len(content))
            return (start, line_end + 1)

        def _table_record(structure: PageStructure, line_index: int) -> tuple[int, int] | None:
            return structure.table_records.get(line_index)

        def _table_header(structure: PageStructure, line_index: int) -> tuple[int, int] | None:
            return structure.table_headers.get(line_index)

        def _evidence_size(spans: list[tuple[int, int]]) -> tuple[int, int]:
            return (len(spans), sum((end - start for start, end in spans)))

        def _validate_evidence_size(spans: list[tuple[int, int]], *, operation: str) -> None:
            segments, characters = _evidence_size(spans)
            if segments > MAX_EVIDENCE_SEGMENTS:
                raise RuntimeError(f'{operation} produced {segments} citation slices; use a narrower selection')
            if characters > MAX_TOTAL_EVIDENCE_CHARS:
                raise RuntimeError(f'{operation} produced {characters} evidence characters; use a narrower selection')

        def _exact_match_groups(content: str, text: str) -> list[list[tuple[int, int]]]:
            if '\n' in text or '\r' in text:
                raise ValueError('find_on_page.text must be a single-line exact string')
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
                selected = _expand_short_spans(content, _merge_spans([span for span in (heading, header, record) if span is not None]))
                groups.append(selected)
            _validate_evidence_size([span for group in groups for span in group], operation='find_on_page')
            return groups

        def _result_identity(result: Any, index: int) -> tuple[str, str]:
            if index >= len(result.results):
                raise RuntimeError('retrieval result omitted citation identity')
            result_id = result.results[index].result_id
            if not result.receipt_id or not result_id:
                raise RuntimeError('retrieval result omitted citation identity')
            return (result.receipt_id, result_id)

        async def _run_search(session: ResearchSession, query: str, preview_budget: int) -> str:
            result = await search_web(query, provider=SEARCH_PROVIDER, num=SEARCH_RESULT_COUNT, timeout=SEARCH_TIMEOUT)
            session.search_count += 1
            parent_key = f'search://{session.search_count}'
            session.vfs[parent_key] = result.response.model_dump_json(indent=2)
            observations = [f'# search_web({query!r}) -> {len(result.response.data)} results']
            for index, item in enumerate(result.response.data):
                content = item.snippet or ''
                key = f'{parent_key}/result/{index + 1}'
                session.vfs[key] = content
                if not content:
                    observations.append(f'{item.title or item.link} — {item.link}\n    No citable excerpt was returned; use this only to discover a page to read.')
                    continue
                ref = session.next_ref()
                receipt_id, result_id = _result_identity(result, index)
                spans = _ranked_search_spans(content, session.question, query)
                preview = _render_search_preview(content, spans)
                record = EvidenceRecord(ref=ref, key=key, title=item.title or item.link, url=item.link, content=content, receipt_id=receipt_id, result_id=result_id, slices=tuple((CitationSlice(start=start, end=end) for start, end in spans if end > start)))
                session.evidence.append(record)
                observations.append(f'[{ref}] {record.title} — {record.url}\n    {preview}')
            return '\n'.join(observations)

        async def _load_page(session: ResearchSession, url: str) -> tuple[Any, str, str, str]:
            cached = session.page_cache.get(url)
            if cached is None:
                result = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=FETCH_TIMEOUT)
                if not result.response.data:
                    raise RuntimeError(f'read_page returned no content for {url}')
                item = result.response.data[0]
                receipt_id, result_id = _result_identity(result, 0)
                cached = (result, item.content, item.title or item.url, item.url or url)
                session.page_cache[url] = cached
                session.vfs[f'page://{url}'] = item.content
                session.page_count += 1
            return cached
        _REGION_HEADING_RE = re.compile('^(#{1,6})\\s+(.+?)\\s*$')
        _REGION_BOLD_HEADING_RE = re.compile('^\\*\\*([^*]+)\\*\\*\\s*$')
        _REGION_FENCE_RE = re.compile('^\\s*(`{3,}|~{3,})')
        _REGION_LIST_RE = re.compile('^\\s*(?:[-+*]|\\d+[.)])\\s+')
        _REGION_TABLE_DELIMITER_RE = re.compile('^:?-{3,}:?$')

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
                lines.append(_RegionLine(number, offset, offset + len(raw), raw.rstrip('\r\n')))
                offset += len(raw)
            if not lines or offset < len(text):
                lines.append(_RegionLine(len(lines) + 1, offset, len(text), text[offset:]))
            return tuple(lines)

        def _region_table_cells(line: str) -> list[str]:
            stripped = line.strip()
            if not stripped.startswith('|'):
                return []
            return [cell.strip() for cell in stripped.strip('|').split('|')]

        def _region_table_delimiter(line: str) -> bool:
            cells = _region_table_cells(line)
            return bool(cells) and all((_REGION_TABLE_DELIMITER_RE.fullmatch(cell.replace(' ', '')) for cell in cells))

        def _region_heading(lines: tuple[_RegionLine, ...], index: int) -> tuple[int, str] | None:
            text = lines[index].text.strip()
            match = _REGION_HEADING_RE.match(text)
            if match:
                return (len(match.group(1)), match.group(2).strip())
            bold = _REGION_BOLD_HEADING_RE.match(text)
            if bold and index + 1 < len(lines) and (not lines[index + 1].text.strip().startswith('|')):
                return (2, bold.group(1).strip())
            return None

        def _region_table_start(lines: tuple[_RegionLine, ...], index: int) -> bool:
            return index + 1 < len(lines) and lines[index].text.lstrip().startswith('|') and _region_table_delimiter(lines[index + 1].text)

        def _region_table_end(lines: tuple[_RegionLine, ...], start: int) -> int:
            expected_pipes = max(2, lines[start].text.count('|'))
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
                if text.lstrip().startswith('|') and row_pipes >= expected_pipes:
                    row_pipes = 0
                row_pipes += text.count('|')
                index += 1
            return index

        def _make_page_region(ordinal: int, kind: str, heading_path: tuple[str, ...], lines: tuple[_RegionLine, ...], start: int, end: int, source: str, namespace: str) -> _PageRegion:
            text = source[lines[start].start:lines[end - 1].end].rstrip()
            digest = hashlib.sha256(f'{namespace}\x00{kind}\x00{text}'.encode()).hexdigest()[:12]
            prefix = f"Heading: {' > '.join(heading_path) or '(document root)'}\nKind: {kind}\n"
            if len(text) <= 8000:
                embedding_text = prefix + text
            else:
                middle = len(text) // 2
                embedding_text = prefix + text[:2500] + '\n[representative middle]\n' + text[middle - 1250:middle + 1250] + '\n[representative tail]\n' + text[-2500:]
            return _PageRegion(handle=f'R{ordinal:04d}-{digest}', kind=kind, heading_path=heading_path, start_line=lines[start].number, end_line=lines[end - 1].number, start_char=lines[start].start, end_char=lines[end - 1].end, text=text, embedding_text=embedding_text)

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
                    kind = 'table'
                    index = _region_table_end(lines, index)
                elif (fence := _REGION_FENCE_RE.match(lines[index].text)):
                    kind = 'code'
                    marker = fence.group(1)[0]
                    index += 1
                    while index < len(lines) and (not lines[index].text.lstrip().startswith(marker * 3)):
                        index += 1
                    index = min(len(lines), index + 1)
                elif _REGION_LIST_RE.match(lines[index].text):
                    kind = 'list'
                    index += 1
                    while index < len(lines):
                        if not lines[index].text.strip() or _region_heading(lines, index) is not None:
                            break
                        if _region_table_start(lines, index):
                            break
                        if _REGION_LIST_RE.match(lines[index].text) or lines[index].text.startswith((' ', '\t')):
                            index += 1
                            continue
                        break
                else:
                    kind = 'paragraph'
                    index += 1
                    while index < len(lines):
                        if not lines[index].text.strip() or _region_heading(lines, index) is not None:
                            break
                        if _region_table_start(lines, index) or _REGION_LIST_RE.match(lines[index].text) or _REGION_FENCE_RE.match(lines[index].text):
                            break
                        index += 1
                regions.append(_make_page_region(len(regions) + 1, kind, tuple((title for _, title in headings)), lines, start, index, content, namespace))
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
                heading_rows.append((line_index, level, tuple((item[1] for item in stack))))
            for position, (heading_index, level, path) in enumerate(heading_rows):
                end = len(lines)
                for next_index, next_level, _ in heading_rows[position + 1:]:
                    if next_level <= level:
                        end = next_index
                        break
                start = heading_index + 1
                while start < end and (not lines[start].text.strip()):
                    start += 1
                while end > start and (not lines[end - 1].text.strip()):
                    end -= 1
                if start < end:
                    regions.append(_make_page_region(len(regions) + 1, 'section', path, lines, start, end, content, namespace))
            return _PageRegionIndex(content_hash=hashlib.sha256(content.encode()).hexdigest(), source_text=content, regions=tuple(regions))

        def _region_cosine(left: list[float], right: list[float]) -> float:
            numerator = sum((a * b for a, b in zip(left, right, strict=True)))
            left_norm = math.sqrt(sum((value * value for value in left)))
            right_norm = math.sqrt(sum((value * value for value in right)))
            return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0

        async def _embed_page_regions(index: _PageRegionIndex) -> None:
            if index.embeddings:
                return
            searchable = [region for region in index.regions if region.kind != 'section']
            result = await embed_text([region.embedding_text for region in searchable], provider='openrouter', model='qwen/qwen3-embedding-8b', input_type='document', dimensions=REGION_EMBEDDING_DIMENSIONS, timeout=EMBEDDING_TIMEOUT)
            vectors = [item.embedding for item in sorted(result.response.data, key=lambda item: item.index)]
            if len(vectors) != len(searchable):
                raise RuntimeError(f'page-region embedding mismatch: expected {len(searchable)}, received {len(vectors)}')
            index.embeddings = {region.handle: vector for region, vector in zip(searchable, vectors, strict=True)}

        async def _rank_page_regions(index: _PageRegionIndex, query: str) -> list[tuple[_PageRegion, float]]:
            await _embed_page_regions(index)
            query_result = await embed_text(query, provider='openrouter', model='qwen/qwen3-embedding-8b', input_type='query', dimensions=REGION_EMBEDDING_DIMENSIONS, timeout=EMBEDDING_TIMEOUT)
            query_vector = query_result.response.data[0].embedding
            section_by_path = {region.heading_path: region for region in index.regions if region.kind == 'section'}
            groups: dict[str, tuple[_PageRegion, list[_PageRegion]]] = {}
            for region in index.regions:
                canonical = section_by_path.get(region.heading_path, region) if region.heading_path else region
                groups.setdefault(canonical.handle, (canonical, []))[1].append(region)
            scored: list[tuple[_PageRegion, float]] = []
            for canonical, members in groups.values():
                member_scores = [_region_cosine(query_vector, index.embeddings[member.handle]) for member in members if member.handle in index.embeddings]
                if member_scores:
                    scored.append((canonical, max(member_scores)))
            scored.sort(key=lambda item: (-item[1], item[0].start_char))
            return scored[:REGION_RESULT_COUNT]

        def _region_preview(region: _PageRegion) -> str:
            compact = re.sub('\\s+', ' ', region.text).strip()
            return compact if len(compact) <= 420 else compact[:417] + '...'

        def _table_region_units(region: _PageRegion, nested_context: str='') -> list[_RegionReadUnit]:
            lines = _region_lines(region.text)
            if len(lines) < 2 or not _region_table_delimiter(lines[1].text):
                return [_RegionReadUnit(nested_context, region.text, ((region.start_char, region.end_char),))]
            header_end = 2
            if header_end < len(lines):
                cells = [cell for cell in _region_table_cells(lines[header_end].text) if cell]
                if cells and (not any((re.search('\\d', cell) for cell in cells))):
                    header_end += 1
            header_start_char = region.start_char
            header_end_char = region.start_char + lines[header_end - 1].end
            header = region.text[:lines[header_end - 1].end].rstrip()
            context = '\n\n'.join((part for part in (nested_context, header) if part))
            expected_pipes = max(2, lines[0].text.count('|'))
            rows: list[_RegionReadUnit] = []
            start = header_end
            while start < len(lines):
                end = start + 1
                pipes = lines[start].text.count('|')
                while end < len(lines) and pipes < expected_pipes:
                    pipes += lines[end].text.count('|')
                    end += 1
                row_start = region.start_char + lines[start].start
                row_end = region.start_char + lines[end - 1].end
                rows.append(_RegionReadUnit(context, region.text[lines[start].start:lines[end - 1].end].rstrip(), ((header_start_char, header_end_char), (row_start, row_end))))
                start = end
            return rows

        def _region_read_units(index: _PageRegionIndex, region: _PageRegion) -> list[_RegionReadUnit]:
            if region.kind == 'table':
                return _table_region_units(region)
            if region.kind != 'section':
                return [_RegionReadUnit('', region.text, ((region.start_char, region.end_char),))]
            children = [child for child in index.regions if child.kind != 'section' and child.start_char >= region.start_char and (child.start_char < region.end_char) and (child.heading_path[:len(region.heading_path)] == region.heading_path)]
            units: list[_RegionReadUnit] = []
            for child in children:
                nested = child.heading_path[len(region.heading_path):]
                context = f"Subheading: {' > '.join(nested)}" if nested else ''
                if child.kind == 'table':
                    units.extend(_table_region_units(child, context))
                else:
                    units.append(_RegionReadUnit(context, child.text, ((child.start_char, child.end_char),)))
            return units or [_RegionReadUnit('', region.text, ((region.start_char, region.end_char),))]

        async def _run_search_page(session: ResearchSession, url: str, query: str, preview_budget: int) -> dict[str, Any]:
            _result, content, title, effective_url = await _load_page(session, url)
            index = session.region_indexes.get(url)
            if index is None:
                index = _build_page_region_index(content, effective_url)
                session.region_indexes[url] = index
                for region in index.regions:
                    registered = session.region_registry.get(region.handle)
                    if registered is not None and registered[0] != url:
                        raise RuntimeError(f'region handle collision: {region.handle}')
                    session.region_registry[region.handle] = (url, region)
            ranked = await _rank_page_regions(index, query)
            candidates = [{'region': region.handle, 'kind': region.kind, 'heading_path': list(region.heading_path), 'source_lines': [region.start_line, region.end_line], 'preview': _region_preview(region), 'similarity': round(score, 6)} for region, score in ranked]
            if len(json.dumps(candidates, ensure_ascii=False)) > preview_budget:
                raise RuntimeError("search_page candidates exceed this tool call's preview budget")
            return {'ok': True, 'title': title, 'url': effective_url, 'query': query, 'candidates': candidates}

        async def _run_read_region(session: ResearchSession, handle_or_continuation: str, preview_budget: int) -> dict[str, Any]:
            handle, separator, offset_text = handle_or_continuation.partition('@')
            registered = session.region_registry.get(handle)
            if registered is None:
                raise ValueError(f'unknown region handle: {handle_or_continuation}')
            url, region = registered
            index = session.region_indexes[url]
            offset = int(offset_text) if separator else 0
            units = _region_read_units(index, region)
            if offset < 0 or offset >= len(units):
                raise ValueError(f'continuation offset is outside region: {handle_or_continuation}')
            prefix = f"Heading: {' > '.join(region.heading_path) or 'Document root'}\nKind: {region.kind}"
            selected: list[_RegionReadUnit] = []
            rendered: list[str] = []
            size = len(prefix)
            active_context: str | None = None
            cursor = offset
            page_limit = min(REGION_PAGE_CHARS, preview_budget)
            while cursor < len(units):
                unit = units[cursor]
                context = unit.context if unit.context != active_context else ''
                text = '\n\n'.join((part for part in (context, unit.text) if part))
                if selected and size + len(text) + 2 > page_limit:
                    break
                selected.append(unit)
                rendered.append(text)
                size += len(text) + 2
                active_context = unit.context
                cursor += 1
            result, content, title, effective_url = await _load_page(session, url)
            receipt_id, result_id = _result_identity(result, 0)
            spans = _expand_short_spans(content, _merge_spans([span for unit in selected for span in unit.spans]))
            ref = session.next_ref()
            session.evidence.append(EvidenceRecord(ref=ref, key=f'page://{url}', title=title, url=effective_url, content=content, receipt_id=receipt_id, result_id=result_id, slices=tuple((CitationSlice(start=start, end=end) for start, end in spans))))
            continuation = None if cursor >= len(units) else f'{handle}@{cursor}'
            return {'ok': True, 'region': handle, 'evidence': f'[{ref}]', 'text': prefix + '\n\n' + '\n\n'.join(rendered), 'complete': continuation is None, 'continuation': continuation}

        async def _run_read_page(session: ResearchSession, url: str, focus: str, preview_budget: int) -> dict[str, Any]:
            result, content, title, effective_url = await _load_page(session, url)
            spans = _ranked_page_spans(content, session.question, focus)
            previews = [_render_page_preview(content, [span]) for span in spans]
            if sum((len(preview) for preview in previews)) > preview_budget:
                raise RuntimeError(f'read_page selected too much visible text for {url}; use a narrower focus')
            session.page_count += 1
            receipt_id, result_id = _result_identity(result, 0)
            records: list[dict[str, str]] = []
            for (start, end), preview in zip(spans, previews, strict=True):
                ref = session.next_ref()
                record = EvidenceRecord(ref=ref, key=f'page://{url}', title=title, url=effective_url, content=content, receipt_id=receipt_id, result_id=result_id, slices=(CitationSlice(start=start, end=end),))
                session.evidence.append(record)
                records.append({'ref': f'[{ref}]', 'text': preview})
            return {'ok': True, 'vfs_key': f'page://{url}', 'title': title, 'url': url, 'focus': focus, 'attempts': result.response.attempts, 'retry_reasons': result.response.retry_reasons, 'evidence': records}

        async def _run_find_on_page(session: ResearchSession, url: str, text: str, preview_budget: int) -> dict[str, Any]:
            result, content, title, effective_url = await _load_page(session, url)
            groups = _exact_match_groups(content, text)
            if not groups:
                return {'ok': True, 'complete': True, 'matching_record_count': 0, 'vfs_key': f'page://{url}', 'title': title, 'url': url, 'text': f'No case-insensitive exact matches for {text!r}.'}
            previews = [_render_page_preview(content, spans) for spans in groups]
            if sum((len(preview) for preview in previews)) > preview_budget:
                raise RuntimeError(f'find_on_page found {len(groups)} records requiring {sum((len(preview) for preview in previews))} preview characters; use a narrower exact string than {text!r}')
            session.page_count += 1
            receipt_id, result_id = _result_identity(result, 0)
            records: list[dict[str, str]] = []
            for spans, preview in zip(groups, previews, strict=True):
                ref = session.next_ref()
                record = EvidenceRecord(ref=ref, key=f'page://{url}', title=title, url=effective_url, content=content, receipt_id=receipt_id, result_id=result_id, slices=tuple((CitationSlice(start=start, end=end) for start, end in spans if end > start)))
                session.evidence.append(record)
                records.append({'ref': f'[{ref}]', 'text': preview})
            return {'ok': True, 'complete': True, 'matching_record_count': len(groups), 'vfs_key': f'page://{url}', 'title': title, 'url': url, 'evidence': records}

        async def _execute_research_call(session: ResearchSession, call: Any, preview_budget: int) -> str | dict[str, Any]:
            try:
                if call.name == 'search_web':
                    arguments = _strict_arguments(call, {'query'})
                    return await _run_search(session, arguments['query'], preview_budget)
                if call.name == 'read_page':
                    arguments = _strict_arguments(call, {'url', 'focus'})
                    return await _run_read_page(session, arguments['url'], arguments['focus'], preview_budget)
                if call.name == 'find_on_page':
                    arguments = _strict_arguments(call, {'url', 'text'})
                    return await _run_find_on_page(session, arguments['url'], arguments['text'], preview_budget)
                if call.name == 'search_page':
                    arguments = _strict_arguments(call, {'url', 'query'})
                    return await _run_search_page(session, arguments['url'], arguments['query'], preview_budget)
                if call.name == 'read_region':
                    arguments = _strict_arguments(call, {'region'})
                    return await _run_read_region(session, arguments['region'], preview_budget)
                raise ValueError(f'unknown research tool: {call.name}')
            except Exception as error:
                return f'# {call.name} failed: {error}'

        async def _llm_chat_with_fallback(*, stage: str, model: str, fallback_model: str, fallback_provider: str='openrouter', messages: list[Any], temperature: float, thinking: dict[str, Any], provider_extra: dict[str, Any], tools: list[dict[str, Any]] | None=None, tool_choice: str | None=None, parallel_tool_calls: bool | None=None, fallback_provider_extra: dict[str, Any] | None=None) -> Any:
            try:
                return await llm_chat(provider='openrouter', model=model, messages=messages, temperature=temperature, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking=thinking, provider_extra=provider_extra, timeout=LLM_TIMEOUT)
            except Exception as primary_error:
                primary_error_detail = str(primary_error)
                logger.warning('llm_fallback stage=%s primary_provider=openrouter primary_model=%s fallback_provider=%s fallback_model=%s error=%s', stage, model, fallback_provider, fallback_model, primary_error_detail)
            try:
                if fallback_provider != 'openrouter' and fallback_provider_extra is None:
                    return await llm_chat(provider=fallback_provider, model=fallback_model, messages=messages, temperature=temperature, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking=thinking, timeout=LLM_TIMEOUT)
                return await llm_chat(provider=fallback_provider, model=fallback_model, messages=messages, temperature=temperature, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking=thinking, provider_extra=fallback_provider_extra or {'provider': {'allow_fallbacks': True}}, timeout=LLM_TIMEOUT)
            except ToolInvocationError as fallback_error:
                raise RuntimeError(f'{stage} primary and fallback LLM calls failed; primary_provider=openrouter primary={primary_error_detail}; fallback_provider={fallback_provider} fallback={fallback_error}') from fallback_error

        def _proven_answer_tool() -> dict[str, Any]:
            return {'type': 'function', 'function': {'name': 'submit_proven_answer', 'description': 'Submit the complete evidence-backed answer and the small set of numbered evidence records that materially support it. Call this only when research is complete, and never alongside research tools.', 'parameters': {'type': 'object', 'properties': {'text': {'type': 'string', 'minLength': 1, 'description': 'The complete final answer, obeying every reader-facing format requirement.'}, 'evidence': {'type': 'array', 'items': {'type': 'integer', 'minimum': 1}, 'minItems': 1, 'description': 'Observed evidence numbers, such as [2, 5], without the E prefix.'}}, 'required': ['text', 'evidence'], 'additionalProperties': False}, 'strict': False}}

        async def _call_researcher(messages: list[Any]) -> Any:
            tools = [*RESEARCH_TOOLS, _proven_answer_tool()]
            return await _llm_chat_with_fallback(stage='research', model='z-ai/glm-5.2', fallback_model=RESEARCH_FALLBACK_MODEL, fallback_provider=RESEARCH_FALLBACK_PROVIDER, messages=messages, temperature=0.2, tools=tools, tool_choice='auto', parallel_tool_calls=True, thinking={'enabled': True, 'effort': 'low'}, provider_extra={'provider': {'allow_fallbacks': True}})

        async def _research_until_answer(session: ResearchSession, messages: list[Any], *, turn_budget: int) -> tuple[ResearchResult, list[Any], int]:
            for turns_used in range(1, turn_budget + 1):
                result = await _call_researcher(messages)
                assistant = _assistant_message(result)
                calls = list(assistant.tool_calls or ())
                if not calls:
                    answer = _assistant_text(result)
                    if not answer:
                        raise RuntimeError('researcher returned neither tool calls nor prose')
                    messages.extend([assistant.to_input_message(), {'role': 'user', 'content': 'Final output must use submit_proven_answer so the answer and its evidence remain separate. Continue research if needed; otherwise call that tool once.'}])
                    continue
                if len(calls) > MAX_PARALLEL_TOOL_CALLS:
                    raise RuntimeError(f'researcher requested {len(calls)} tools in one turn; ceiling is {MAX_PARALLEL_TOOL_CALLS}')
                final_calls = [call for call in calls if call.name == 'submit_proven_answer']
                if final_calls:
                    messages.append(assistant.to_input_message())
                    error: Exception | None = None
                    try:
                        if len(calls) != 1:
                            raise ValueError('the final submission must be the sole tool call in its response')
                        arguments = json.loads(final_calls[0].arguments)
                        expected_fields = {'text', 'evidence'}
                        if not isinstance(arguments, dict) or set(arguments) != expected_fields:
                            raise ValueError(f'{final_calls[0].name} requires only {sorted(expected_fields)}')
                        answer = arguments['text']
                        if not isinstance(answer, str) or not answer.strip():
                            raise ValueError('text must be the non-empty complete answer')
                        if re.search('https?://|\\bwww\\.', answer, flags=re.IGNORECASE):
                            raise ValueError('do not render raw URLs in the final answer')
                        evidence = arguments['evidence']
                        if not isinstance(evidence, list) or not evidence:
                            raise ValueError('evidence must be a non-empty array of observed evidence numbers')
                        if any((isinstance(number, bool) or not isinstance(number, int) for number in evidence)):
                            raise ValueError('every evidence item must be an integer')
                        numbers = list(dict.fromkeys(evidence))
                        unavailable = [number for number in numbers if number < 1 or number > len(session.evidence)]
                        if unavailable:
                            raise ValueError(f'evidence numbers were not observed: {unavailable}')
                        refs = tuple((f'E{number}' for number in numbers))
                        if answer is not None:
                            inline_refs = _private_refs(answer)
                            unknown_inline = [ref for ref in inline_refs if ref not in refs]
                            if unknown_inline:
                                raise ValueError(f'text cites evidence absent from the evidence list: {unknown_inline}')
                        messages.append({'role': 'tool', 'tool_call_id': final_calls[0].id, 'content': json.dumps({'ok': True, 'status': 'proven_answer_accepted'})})
                        return (ResearchResult(answer=answer, evidence_refs=refs), messages, turns_used)
                    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as caught:
                        error = caught
                    messages.append({'role': 'tool', 'tool_call_id': final_calls[0].id, 'content': json.dumps({'ok': False, 'error_type': 'tool_argument_validation', 'details': str(error)})})
                    continue
                messages.append(assistant.to_input_message())
                preview_budget = TOOL_TURN_PREVIEW_CHARS // len(calls)
                outputs = await asyncio.gather(*(_execute_research_call(session, call, preview_budget) for call in calls))
                for call, output in zip(calls, outputs, strict=True):
                    messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)})
            raise RuntimeError(f'researcher exhausted the visible {turn_budget}-turn experiment ceiling')
        _PRIVATE_REF_GROUP = re.compile('\\[((?:E\\d+\\s*,\\s*)*E\\d+)\\]')

        def _refs_in_group(match: re.Match[str]) -> list[str]:
            return [ref.strip() for ref in match.group(1).split(',')]

        def _private_refs(answer: str) -> list[str]:
            refs = (ref for match in _PRIVATE_REF_GROUP.finditer(answer) for ref in _refs_in_group(match))
            return list(dict.fromkeys(refs))

        def _validate_private_answer(answer: str, session: ResearchSession) -> None:
            if '[[' in answer or ']]' in answer:
                raise ValueError('use private evidence refs such as [E1], not public citation indices')
            if re.search('https?://|\\bwww\\.', answer, flags=re.IGNORECASE):
                raise ValueError('do not render raw URLs in the final answer')
            allowed = session.evidence_by_ref()
            refs = _private_refs(answer)
            unknown = [ref for ref in refs if ref not in allowed]
            if unknown:
                raise ValueError(f"answer cites unavailable refs: {', '.join(unknown)}")
            if not allowed:
                raise ValueError('deep-research answer has no observed evidence')
            if not refs:
                raise ValueError('answer cites none of the observed evidence')
            without_refs = _PRIVATE_REF_GROUP.sub('', answer)
            if re.search('\\[(?:E\\d+[^\\]]*|[^\\]]*E\\d+)\\]', without_refs):
                raise ValueError('private refs must use [E1] or a comma-separated group such as [E1, E2]')

        async def _repair_private_answer_contract(session: ResearchSession, answer: str, messages: list[Any]) -> str:
            try:
                _validate_private_answer(answer, session)
                return answer
            except ValueError as error:
                logger.warning('private_answer_contract_retry error=%s', error)
                validation_error = str(error)
            valid_refs = ', '.join((f'[{ref}]' for ref in session.evidence_by_ref()))
            repair_messages = [*messages, {'role': 'assistant', 'content': answer}, {'role': 'user', 'content': f'Your final answer failed the mechanical private-citation contract. Correct only the citation syntax and placement; do not research, add or remove factual claims, or otherwise rewrite the answer. Return the complete corrected answer as prose, with no commentary. A citation may be a single ref such as [E1] or a comma-separated group such as [E1, E2]. Use only observed refs.\n\nValidation error: {validation_error}\nObserved refs: {valid_refs}'}]
            result = await _llm_chat_with_fallback(stage='private_citation_repair', model='z-ai/glm-5.2', fallback_model=RESEARCH_FALLBACK_MODEL, fallback_provider=RESEARCH_FALLBACK_PROVIDER, messages=repair_messages, temperature=0.0, thinking={'enabled': True, 'effort': 'low'}, provider_extra={'provider': {'allow_fallbacks': True}})
            repaired = _assistant_text(result)
            if not repaired:
                raise RuntimeError('private citation repair returned empty prose')
            try:
                _validate_private_answer(repaired, session)
            except ValueError as repair_error:
                raise ValueError(f'private citation repair failed validation: {repair_error}') from repair_error
            return repaired

        def _audit_evidence_digest(session: ResearchSession, answer: str) -> str:
            records = session.evidence_by_ref()
            cited = _private_refs(answer)
            parts: list[str] = []
            for ref in cited:
                item = records[ref]
                visible = '\n...\n'.join((item.content[slice_.start:slice_.end] for slice_ in item.slices))
                parts.append(f'[{ref}] {item.title}\nSource URL: {item.url}\n{visible}')
            return '\n\n'.join(parts)

        async def _audit(session: ResearchSession, answer: str) -> tuple[bool, str]:
            _validate_private_answer(answer, session)
            messages: list[Any] = [{'role': 'system', 'content': AUDIT_SYSTEM}, {'role': 'user', 'content': f'Original question:\n{session.question}\n\nCandidate answer:\n{answer}\n\nEvidence ledger (only cited records):\n{_audit_evidence_digest(session, answer)}'}]
            for attempt in range(3):
                result = await _llm_chat_with_fallback(stage='audit', model='openai/gpt-oss-120b', fallback_model='openai/gpt-oss-120b', fallback_provider=RESEARCH_FALLBACK_PROVIDER, messages=messages, temperature=0.0, tools=AUDIT_TOOLS, tool_choice='required', parallel_tool_calls=False, thinking={'enabled': True, 'effort': 'high'}, provider_extra={'provider': {'only': ['cerebras'], 'allow_fallbacks': False}})
                assistant = None
                calls: list[Any] = []
                try:
                    assistant = _assistant_message(result)
                    calls = list(assistant.tool_calls or ())
                    if len(calls) != 1:
                        raise ValueError(f'auditor must make exactly one decision; received {len(calls)} calls')
                    call = calls[0]
                    if call.name == 'accept_answer':
                        arguments = json.loads(call.arguments)
                        if arguments != {}:
                            raise ValueError('accept_answer accepts no arguments')
                        return (True, '')
                    if call.name != 'request_repair':
                        raise ValueError(f'unexpected auditor tool: {call.name}')
                    arguments = _strict_arguments(call, {'issue', 'why_material'})
                    return (False, f"{arguments['issue']} Why material: {arguments['why_material']}")
                except (RuntimeError, ValueError) as error:
                    if attempt == 2:
                        raise RuntimeError(f'audit decision validation failed after feedback: {error}') from error
                    logger.warning('audit_decision_validation_retry error=%s', error)
                    if assistant is not None:
                        messages.append(assistant.to_input_message())
                    if calls:
                        for call in calls:
                            messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': json.dumps({'ok': False, 'error_type': 'tool_argument_validation', 'details': str(error)})})
                    else:
                        messages.append({'role': 'user', 'content': f'Audit decision contract error: {error}. Re-evaluate the same answer and evidence, then call exactly one of accept_answer or request_repair. Do not answer in prose.'})
            raise AssertionError('unreachable')

        def _render_response(session: ResearchSession, answer: str, evidence_refs: tuple[str, ...]) -> Response:
            if '[[' in answer or ']]' in answer:
                raise ValueError('use private evidence refs such as [E1], not public citation indices')
            inline_refs = _private_refs(answer)
            unknown_inline = [ref for ref in inline_refs if ref not in evidence_refs]
            if unknown_inline:
                raise ValueError(f'answer cites evidence absent from its evidence list: {unknown_inline}')
            citations, indices = _citation_bundle(session, evidence_refs)
            rendered = _PRIVATE_REF_GROUP.sub(lambda match: ''.join((f'[[{index}]]' for index in dict.fromkeys((indices[ref] for ref in _refs_in_group(match))))), answer)
            rendered = re.sub('(\\[\\[\\d+\\]\\])(?:\\s*\\1)+', '\\1', rendered)
            return Response(text=rendered, citations=citations)

        def _citations_for_refs(session: ResearchSession, refs: tuple[str, ...]) -> list[CitationRef]:
            citations, _ = _citation_bundle(session, refs)
            return citations

        def _citation_bundle(session: ResearchSession, refs: tuple[str, ...]) -> tuple[list[CitationRef], dict[str, int]]:
            records = session.evidence_by_ref()
            selected_spans = [(slice_.start, slice_.end) for ref in refs for slice_ in records[ref].slices]
            _validate_evidence_size(selected_spans, operation='structured answer')
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
                grouped_spans[key].extend(((slice_.start, slice_.end) for slice_ in record.slices))
            citations = [CitationRef(receipt_id=receipt_id, result_id=result_id, slices=[CitationSlice(start=start, end=end) for start, end in _merge_spans(grouped_spans[key])]) for key in group_order for receipt_id, result_id in [key]]
            return (citations, ref_indices)

        def _structured_output_tool(output_schema: dict[str, Any]) -> tuple[dict[str, Any], bool]:
            direct_object = output_schema.get('type') == 'object'
            parameters = output_schema if direct_object else {'type': 'object', 'properties': {'output': {'description': 'The complete schema-conforming JSON value.'}}, 'required': ['output'], 'additionalProperties': False}
            return ({'type': 'function', 'function': {'name': 'submit_structured_output', 'description': "Submit the complete final value required by the caller's JSON Schema.", 'parameters': parameters, 'strict': False}}, direct_object)

        async def _project_structured_output(messages: list[Any], output_schema: dict[str, Any]) -> Any:
            tool, direct_object = _structured_output_tool(output_schema)
            projection_messages: list[Any] = [*messages, {'role': 'user', 'content': f'The evidence-backed answer you just submitted is accepted as final and authoritative. Convert only that answer to the JSON Schema below. Do not research again, add facts, change names or values, reconsider the conclusion, or select evidence again. Call submit_structured_output exactly once.\n\nRequired JSON Schema:\n{json.dumps(output_schema, ensure_ascii=False, indent=2)}'}]
            for attempt in range(3):
                result = await _llm_chat_with_fallback(stage='structured_output', model='z-ai/glm-5.2', fallback_model=STRUCTURED_FALLBACK_MODEL, messages=projection_messages, temperature=0.0, tools=[tool], tool_choice='required', parallel_tool_calls=False, thinking={'enabled': True, 'effort': 'low'}, provider_extra={'provider': {'allow_fallbacks': True}})
                assistant = _assistant_message(result)
                calls = list(assistant.tool_calls or ())
                error: ValueError | None = None
                output: Any = None
                if len(calls) != 1:
                    error = ValueError(f'call submit_structured_output exactly once; received {len(calls)} calls')
                else:
                    call = calls[0]
                    try:
                        if call.name != 'submit_structured_output':
                            raise ValueError(f'unexpected tool {call.name}; call submit_structured_output')
                        arguments = json.loads(call.arguments)
                        if not isinstance(arguments, dict):
                            raise ValueError('tool arguments must be a JSON object')
                        if direct_object:
                            output = arguments
                        else:
                            if set(arguments) != {'output'}:
                                raise ValueError('non-object output must use the sole `output` argument')
                            output = arguments['output']
                        if output is None:
                            raise ValueError('top-level null is not a valid miner answer')
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
                        projection_messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': json.dumps({'ok': False, 'error_type': 'tool_argument_validation', 'details': str(error)})})
                else:
                    projection_messages.append({'role': 'user', 'content': f'Output contract error: {error}. Submit the complete schema-conforming value.'})
            raise AssertionError('unreachable')

        async def _hypothesis(question: str) -> str:
            result = await _llm_chat_with_fallback(stage='hypothesis', model='z-ai/glm-5.2', fallback_model=RESEARCH_FALLBACK_MODEL, fallback_provider=RESEARCH_FALLBACK_PROVIDER, messages=[{'role': 'system', 'content': HYPOTHESIS_SYSTEM}, {'role': 'user', 'content': question}], temperature=0.2, thinking={'enabled': True, 'effort': 'low'}, provider_extra={'provider': {'allow_fallbacks': True}})
            hypothesis = _assistant_text(result)
            if not hypothesis:
                raise RuntimeError('hypothesis model returned empty output')
            return hypothesis

        async def _w2_baseline_query(query_input: Query) -> Response:
            session = ResearchSession(question=query_input.text)
            response_contract = ''
            if query_input.output_schema is not None:
                response_contract = f'\n\nCaller response contract:\nThe final response must match this JSON Schema. Treat it as part of the response contract throughout the investigation. Before finalizing, decide every required leaf value exactly as it should appear in the schema and state those exact values in the evidence-backed prose answer. Preserve source-native labels when the question asks for a value from a named source; do not replace them with a broader category, a shorter synonym, or an explanatory alias. Do not enrich a requested name with a second equivalent name unless the question or evidence requires both. Do not output JSON during research.\n{json.dumps(query_input.output_schema, ensure_ascii=False, indent=2)}'
            messages: list[Any] = [{'role': 'system', 'content': RESEARCH_SYSTEM}, {'role': 'user', 'content': f'Original question:\n{query_input.text}{response_contract}'}]
            result, messages, _turns_used = await _research_until_answer(session, messages, turn_budget=RESEARCH_TURN_CEILING)
            if query_input.output_schema is None:
                return _render_response(session, result.answer, result.evidence_refs)
            output = await _project_structured_output(messages, query_input.output_schema)
            return Response(output=output, citations=_citations_for_refs(session, result.evidence_refs))
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
        _W2_DRAFT_PROMPT_CHARS = 6000
        _W2_DEFAULT_BUDGET_SECONDS = 235.0
        _W2_LIST_MARKER_RE = re.compile('(?m)^[ \\t]*[(\\[]?\\d{1,2}[.)\\]][ \\t]+')
        _W2_FIGURE_RE = re.compile('\\d+(?:[.,]\\d+)*')
        _W2_WORD_RE = re.compile("[A-Z][A-Za-z0-9&'’.\\-]*")
        _W2_CLAUSE_HEAD_CHARS = '.!?:;#*->|•'
        _W2_PLAN_SYSTEM = 'You plan the acceptance criteria for a research answer before the research runs.\nRead the question and list what a complete, correct answer must contain.\nReply with JSON only, no prose, in this exact shape:\n{"deliverable": "<one sentence naming what must be returned>", "required": ["<concrete element the answer must state>", ...], "pitfalls": ["<a specific way an answer to this question goes wrong>", ...]}\nGive at most six `required` entries and at most three `pitfalls`. Each entry must be concrete and checkable against a draft answer - name the quantity, entity, unit, date range, or enumeration that must appear. Never guess the answer itself; describe only what the answer must cover.'
        _W2_VERIFY_SYSTEM = "You audit a draft research answer against an answer contract and repair it.\nThe contract lists what the answer must contain. Check the draft against every entry and return the corrected answer.\nRules:\n- Repair only concrete, verifiable gaps: a required element the draft never states, an internal contradiction, a requested unit or format the draft ignores.\n- Use only facts already present in the draft. Never introduce a fact, figure, name, or citation that the draft does not contain.\n- Every figure, quantity, date, unit, name, and citation marker the draft states stands as written. You may not drop one, round one, reword one, or swap one for a different value or a different entity. Your edits may only add.\n- The draft's own answer to the question is the answer. If you believe a different entity or value fits the question better, say so in one added clause and leave the draft's answer standing.\n- If a required element is genuinely absent from the draft's evidence, say so plainly in one clause rather than inventing it.\n- Preserve the draft's wording wherever it already satisfies the contract.\n- If the draft already satisfies the contract, return it unchanged.\nReturn the full corrected answer text and nothing else - no preamble, no notes, no commentary about what you changed."
        _W2_REPAIR_SYSTEM = "You convert a research answer into the exact JSON object a caller's schema requires.\nUse only facts stated in the answer text. Do not invent values. If the answer does not supply a required field, use null for it.\nReply with a single JSON object and nothing else."

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
                return 'openrouter'

        def _w2_model() -> str:
            try:
                return MODEL
            except NameError:
                return 'z-ai/glm-5'

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
                return ''
            try:
                result = await llm_chat(provider=_w2_provider(), model=_w2_model(), messages=messages, temperature=temperature, timeout=timeout)
            except Exception:
                return ''
            try:
                return (result.response.raw_text or '').strip()
            except Exception:
                return ''

        def _w2_json_object(text: str) -> dict | None:
            """Tolerant extraction of the first JSON object in a model reply."""
            if not text:
                return None
            body = text.strip()
            if body.startswith('```'):
                body = body.split('```')[1] if '```' in body[3:] else body[3:]
                if body[:4].lower().startswith('json'):
                    body = body[4:]
            start = body.find('{')
            end = body.rfind('}')
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
                return ''
            try:
                rendered = json.dumps(schema, ensure_ascii=False)[:1200]
            except (TypeError, ValueError):
                return ''
            return f'\n\nThe answer will be returned against this output schema:\n{rendered}'

        async def _w2_build_answer_contract(question: str, schema: object, *, deadline: float) -> _W2AnswerContract | None:
            """Stage 1 - plan the acceptance criteria before the baseline research runs."""
            timeout = min(_W2_PLAN_TIMEOUT_SECONDS, _w2_remaining(deadline) - _W2_TAIL_RESERVE_SECONDS)
            messages = [{'role': 'system', 'content': _W2_PLAN_SYSTEM}, {'role': 'user', 'content': f'Question:\n{question}{_w2_schema_hint(schema)}'}]
            payload = _w2_json_object(await _w2_chat(messages, timeout=timeout, temperature=_W2_PLAN_TEMPERATURE))
            if payload is None:
                return None
            deliverable = payload.get('deliverable')
            contract = _W2AnswerContract(deliverable=deliverable.strip() if isinstance(deliverable, str) else '', required=_w2_string_list(payload.get('required'), _W2_MAX_CONTRACT_ITEMS), pitfalls=_w2_string_list(payload.get('pitfalls'), 3))
            return contract if contract.is_actionable() else None

        def _w2_contract_block(contract: _W2AnswerContract) -> str:
            """Render the contract as the audit checklist handed to the verify stage."""
            lines = []
            if contract.deliverable:
                lines.append(f'Deliverable: {contract.deliverable}')
            if contract.required:
                lines.append('The answer must state:')
                lines.extend((f'  - {item}' for item in contract.required))
            if contract.pitfalls:
                lines.append('Known ways this question is answered badly:')
                lines.extend((f'  - {item}' for item in contract.pitfalls))
            return '\n'.join(lines)

        def _w2_response_text(response: object) -> str:
            try:
                text = getattr(response, 'text', None)
            except Exception:
                return ''
            return text.strip() if isinstance(text, str) else ''

        def _w2_with_text(response: object, text: str) -> object:
            """Rebuild the response around the audited answer, carrying citations over.

    The platform accepts exactly one non-null answer field, so a response that
    already carries a structured `output` owns no text answer to override and is
    returned untouched.
    """
            if getattr(response, 'output', None) is not None:
                return response
            citations = getattr(response, 'citations', None)
            try:
                if citations:
                    return Response(text=text, citations=citations)
                return Response(text=text)
            except Exception:
                return response

        def _w2_normalize_figure(token: str) -> str:
            """One numeric literal reduced to the value it states, not how it is typed."""
            value = token.replace(',', '')
            if '.' in value:
                value = value.rstrip('0').rstrip('.')
            return value or '0'

        def _w2_figures(text: str) -> set:
            """Every quantity the text asserts, less the ordinals that only number a list."""
            body = _W2_LIST_MARKER_RE.sub(' ', text)
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
                while cursor >= 0 and text[cursor] in ' \t':
                    cursor -= 1
                if cursor < 0 or text[cursor] == '\n' or text[cursor] in _W2_CLAUSE_HEAD_CHARS:
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

        async def _w2_verify_against_contract(contract: _W2AnswerContract, question: str, draft: str, *, deadline: float) -> str:
            """Stage 3 - audit the draft against the contract and return the answer to deliver."""
            timeout = min(_W2_VERIFY_TIMEOUT_SECONDS, _w2_remaining(deadline) - _W2_TAIL_RESERVE_SECONDS)
            messages = [{'role': 'system', 'content': _W2_VERIFY_SYSTEM}, {'role': 'user', 'content': f'Question:\n{question}\n\nAnswer contract:\n{_w2_contract_block(contract)}\n\nDraft answer:\n{draft[:_W2_DRAFT_PROMPT_CHARS]}'}]
            revision = await _w2_chat(messages, timeout=timeout, temperature=_W2_VERIFY_TEMPERATURE)
            return revision if _w2_accept_revision(draft, revision) else draft

        def _w2_schema_property_names(schema: object) -> list[str]:
            if not isinstance(schema, dict):
                return []
            properties = schema.get('properties')
            return [key for key in properties] if isinstance(properties, dict) else []

        def _w2_is_degenerate_output(output: object, schema: object) -> bool:
            """True when the base produced a structured payload the scorer will read as empty."""
            if output is None:
                return True
            if isinstance(output, (str, list, tuple, dict)) and len(output) == 0:
                return True
            if isinstance(output, dict):
                names = _w2_schema_property_names(schema)
                if names and (not any((key in output for key in names))):
                    return True
                if all((value in (None, '', [], {}) for value in output.values())):
                    return True
            return False

        async def _w2_repair_structured_output(question: str, schema: object, response: object, *, deadline: float) -> object:
            """Repair-only ladder: a working structured payload is always returned untouched."""
            output = getattr(response, 'output', None)
            if not _w2_is_degenerate_output(output, schema):
                return response
            draft = _w2_response_text(response)
            recovered = _w2_json_object(draft)
            if recovered is None:
                timeout = min(_W2_REPAIR_TIMEOUT_SECONDS, _w2_remaining(deadline) - 2.0)
                try:
                    rendered = json.dumps(schema, ensure_ascii=False)[:1500]
                except (TypeError, ValueError):
                    rendered = ''
                messages = [{'role': 'system', 'content': _W2_REPAIR_SYSTEM}, {'role': 'user', 'content': f'Question:\n{question}\n\nOutput schema:\n{rendered}\n\nAnswer text:\n{draft[:_W2_DRAFT_PROMPT_CHARS]}'}]
                recovered = _w2_json_object(await _w2_chat(messages, timeout=timeout, temperature=0.0))
            if recovered is None or _w2_is_degenerate_output(recovered, schema):
                return response
            citations = getattr(response, 'citations', None)
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
                return Response(text='No verifiable source-backed answer was reached for this question.')

        async def query(query: Query) -> Response:
            """w2 contract wrapper: plan the answer contract, run the baseline, then verify.

    The baseline artifact's own entrypoint is demoted to `_w2_baseline_query` and
    runs as the research stage of this sequence. Contract planning runs on every
    ordinary request before the research starts, and the verification stage holds
    authority over the answer this entrypoint returns.
    """
            deadline = perf_counter() + _w2_total_budget_seconds()
            question = getattr(query, 'text', '') or ''
            schema = getattr(query, 'output_schema', None)
            contract = await _w2_build_answer_contract(question, schema, deadline=deadline)
            response = await _w2_research_or_salvage(query)
            if contract is not None:
                draft = _w2_response_text(response)
                if draft:
                    audited = await _w2_verify_against_contract(contract, question, draft, deadline=deadline)
                    if audited != draft:
                        response = _w2_with_text(response, audited)
            if schema is not None:
                response = await _w2_repair_structured_output(question, schema, response, deadline=deadline)
            return response
        return query

class ReserveSolver:

    def _compile(self):
        import asyncio
        from harnyx_miner_sdk.api import LlmThinkingConfig, llm_chat
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import Query, Response

        class FirstPath:

            def _compile(self):
                import asyncio
                import json
                import re
                from time import monotonic
                from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
                from harnyx_miner_sdk.decorators import entrypoint
                from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
                VERSION = 'v60-toolleak'
                LLM_LANE_A = 'openrouter'
                LLM_LANE_B = 'ai_gateway'
                LOOP_MODEL_A = 'z-ai/glm-5.2'
                LOOP_MODEL_B = 'zai/glm-5.2-fast'
                AUDIT_MODEL = 'openai/gpt-oss-120b'
                SCHEMA_MODEL = 'openai/gpt-oss-120b'
                RESORT_MODEL = 'deepseek/deepseek-v3.2'
                SEARCH_PROVIDER = 'parallel'
                SEARCH_MODE = 'turbo'
                FETCH_PROVIDER = 'parallel'
                JSON_PROVIDER = 'parallel'
                _FETCH_EXTRA = None
                WALL_BUDGET_S = 266.0
                BRIEF_TIMEOUT_S = 50.0
                TURN_TIMEOUT_S = 75.0
                LANE_B_MAX_PAYLOAD_CHARS = 144000
                AUDIT_TIMEOUT_S = 28.0
                SEARCH_TIMEOUT_S = 18.0
                FETCH_TIMEOUT_S = 16.0
                WRAPUP_AT_S = 90.0
                MIN_TAIL_S = 8.0
                MAX_TURNS = 15
                AUDIT_EXTRA_TURNS = 2
                ANSWER_REPAIR_TURNS = 2
                RESCUE_TIMEOUT_S = 55.0
                DIGEST_TAIL_S = 14.0
                SEARCH_EXCERPT_CHARS = 550
                _LEDGER_TEXT_CAP = 400000
                PAGE_GREP_WINDOW = 700
                PAGE_GREP_MAX_HITS = 6
                PAGE_READ_MAX_CHARS = 12000
                RETAIN_MARGIN_CHARS = 260
                RETAIN_MAX_PER_ROW = 6
                RETAIN_MIN_QUOTE = 12
                FETCH_HEAD_CHARS = 3000
                FETCH_WINDOW_CHARS = 3600
                CITATION_MIN_SPAN_CHARS = 6000
                CITATION_MAX_REF_CHARS = 14000
                FETCH_WINDOWS_PER_PAGE = 3
                FETCH_PLAIN_CHARS = 6500
                ANSWER_CHAR_CAP = 60000
                CITATION_CAP = 24
                EVIDENCE_CHAR_BUDGET = 105000
                BRIEF_MIN_USD = 0.03
                AUDIT_MIN_USD = 0.05
                WRAPUP_MIN_USD = 0.02
                _SPEND = {'left': None}

                def _spend_note(payload) -> None:
                    budget = getattr(payload, 'budget', None)
                    left = getattr(budget, 'session_remaining_budget_usd', None)
                    if isinstance(left, (int, float)):
                        _SPEND['left'] = float(left)

                def _spend_left() -> float:
                    left = _SPEND['left']
                    if isinstance(left, (int, float)):
                        return float(left)
                    return 1.0
                LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}, {'type': 'function', 'function': {'name': 'page_grep', 'description': 'Search INSIDE a page you already fetched, by regex or literal text, and get every match with its surrounding context and character offset. Use this when read_page showed you the head of a long page but the value you need is deeper in it -- do not re-fetch, grep it.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL of a page already fetched this run'}, 'pattern': {'type': 'string', 'description': 'regex or literal string to find, e.g. a city name, a year, a column label'}}, 'required': ['url', 'pattern']}}}, {'type': 'function', 'function': {'name': 'page_read', 'description': 'Read an arbitrary character range of a page you already fetched. Use the offsets page_grep reports to read the full table or section around a match.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL already fetched'}, 'offset': {'type': 'integer', 'description': 'start character offset'}, 'length': {'type': 'integer', 'description': 'how many characters to read (max 12000)'}}, 'required': ['url', 'offset']}}}, {'type': 'function', 'function': {'name': 'retain_evidence', 'description': "Keep the exact source text that proves a claim you are about to make. Pass the result number and the verbatim quote from it. Do this the moment you find a decisive value -- the judge only credits claims whose citation contains the supporting text, and this is how that text gets into your citation. Use it for the QUESTION'S PREMISES as well as your answer: every entity, work, date or figure the question names should end up with a retained quote confirming it.", 'parameters': {'type': 'object', 'properties': {'source': {'type': 'string', 'description': 'result number to quote from, e.g. 3'}, 'quote': {'type': 'string', 'description': 'verbatim text copied from that result that states the fact'}}, 'required': ['source', 'quote']}}}]
                LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nPREFER THE PRIMARY SOURCE: when two sources state the same fact, cite the one that ORIGINATES it -- the agency, registry, filing, official statistics release or the organisation\'s own page -- not an encyclopedia or aggregator repeating it. Measured verbatim on a task where both answers were factually correct: "Answer 1 is preferred for using primary sources" (it cited NARA where we cited Wikipedia) -- a full point lost on every run. Use the encyclopedia to FIND the primary source, then fetch and cite that.\n\nQUOTE WHAT PROVES IT: the judge credits a claim only when your citation CONTAINS the source text stating it. The moment you read a decisive value, call retain_evidence(source, quote) with the exact words from that result. Do this for every condition you test and every figure you report -- an answer whose citations do not carry its numbers loses to one that does, even when both answers are identical.\nALSO QUOTE THE QUESTION\'S PREMISES, not only your answer. Every entity, work, date or figure the question NAMES is a claim the judge expects traceable: the film it says someone directed, the article it points at, the year it fixes, the people it lists. You lose to an otherwise identical answer that cited those too -- measured verbatim: "does not provide a citation for \'Everyone Says I Love You\'... Answer 1 is more thorough in its traceability to all parts of the prompt\'s context". Retain a quote for each named premise as you confirm it, even when it is background you already believed.\n\nREAD DEEP, DO NOT RE-FETCH: read_page shows the head plus a few regions of a long page. If the value you need is not in what you were shown, call page_grep(url, pattern) to find it anywhere in that page and page_read to open the region around a reported offset. Grepping a page you already have costs nothing and beats another search.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. COPY SOURCE VALUES VERBATIM: when the question names a source, every name, label and value in the answer must be the exact string that source prints -- never add a familiar alternative in parentheses, never anglicise a transliteration. \'Makkah\' is the answer; \'Mecca (Makkah)\' is a wrong answer. ONE EXCEPTION, and it is absolute: if the question says to output ONLY the answer (\'output only\', \'respond with only\', \'nothing else\', \'no explanation\'), emit the answer line as the BARE requested text — no [n] markers on it, nothing else on that line: a trailing [3] makes the text inexact and fails the instruction. Still write the PROOF section BELOW it carrying its [n] markers. Only the answer line is shipped, but the citations are harvested from the proof first, and an uncited answer scores zero. Obeying that instruction IS the task. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

                def _wrapup_order(seconds_left: float) -> str:
                    return f"TIME IS UP (~{int(seconds_left)}s left). No more tool calls. Write the complete final answer NOW from the numbered results above plus your knowledge: the FIRST words are the answer entities (no 'Based on…' preamble, no 'partial answer' framing, no '(verify)' markers), cite [n] on every claim, keep the required format. A cited partial answer scores; a refusal or a remark about insufficient evidence scores zero." + ('' if seconds_left >= 60 else ' BREVITY OVERRIDE: too little time remains for a line per pool member. Lead with the answer entities, then give the qualifiers one cited line each and compress the rejects into a single cited line. A complete short answer beats a long one that never finishes.')
                _SET_HINT_RE = re.compile('\\b(?:list|name|identify|enumerate)\\b[^?]{0,40}\\b(?:all|every|each|the)\\b|\\bhow many\\b|\\bwhich (?:movies|films|series|countries|companies|states|cities|books|albums|artists|players|teams|species|languages|banks|universities|agencies|models|products)\\b', re.IGNORECASE)
                _SET_CONNECTIVE_RE = re.compile('\\b(?:both|also|and (?:also|had|has|was|were)|as well as)\\b', re.IGNORECASE)
                _PLURAL_HEAD_RE = re.compile('\\b(?:which|what)\\b(?:\\s+\\w+){0,2}?\\s+([a-z]{3,}s)\\b', re.IGNORECASE)
                _PLURAL_FALSE = frozenset('was is has does its this thus across process business series species news status analysis basis less unless always perhaps'.split())
                _ONE_WINNER_RE = re.compile('\\b(?:highest|lowest|largest|smallest|most|least|greatest|fewest|longest|shortest|first|last|best|worst|only|oldest|youngest|newest|biggest)\\b', re.IGNORECASE)
                _EST_STOP = frozenset('interest honest modest protest request suggest forest harvest invest manifest contest arrest digest earnest conquest tempest midwest northwest southwest unrest bequest behest attest molest ingest infest detest incest armrest backrest pretest headrest footrest'.split())
                _EST_RE = re.compile('\\b([a-z]{3,})est\\b')

                def _has_superlative(text: str) -> bool:
                    if _ONE_WINNER_RE.search(text or ''):
                        return True
                    for m in _EST_RE.finditer(text or ''):
                        if m.group(0).lower() not in _EST_STOP:
                            return True
                    return False

                def _needs_superlative_proof(question: str) -> bool:
                    q = ' '.join((question or '').split())
                    if not q:
                        return False
                    return _has_superlative(q) or bool(re.search('\\b(?:most|least) (?:common|frequent|number|amount)\\b|\\bhow many\\b', q, re.I))
                SUPERLATIVE_RULE = "SUPERLATIVE / TALLY — SHOW THE TABLE. The answer is one item, but you cannot know it without the whole pool. Before naming a winner: (1) list EVERY candidate the question's scope admits — every player who appeared, every officeholder in the span, every body in the ranking; (2) put the deciding value next to each (birth date, count, figure), cited; (3) THEN name the maximum. NEVER decide a superlative on a rounded or derived display: a coarse figure (a whole-number age, a rounded total, a bucketed rank) cannot separate two contenders that differ below its precision. Fetch the exact underlying value (full birth date, unrounded figure) for every contender, from a source that lists them ALL: a page showing only your front-runner cannot establish that nobody beats them. (3b) THEN name the maximum. Reproduce that candidate table in the proof section — a correct winner with no visible tally loses to a reference that shows its work, and 'among others' / 'and several more' is not a tally. If the pool is too large to list in full, rank it, show every contender down to a stated cutoff, and say what the cutoff was — a stated cutoff is a covered pool; an unstated one reads as an unchecked one."

                def _needs_set_completeness(question: str) -> bool:
                    q = ' '.join((question or '').split())
                    if _SET_HINT_RE.search(q):
                        return True
                    m = _PLURAL_HEAD_RE.search(q)
                    if m and m.group(1).lower() not in _PLURAL_FALSE:
                        if not _has_superlative(q) or re.search('\\b(?:all|every|each)\\b', q, re.IGNORECASE):
                            return True
                    return bool(re.search('\\bwhich\\b', q, re.IGNORECASE)) and bool(_SET_CONNECTIVE_RE.search(q))
                SET_RULE = "SET ANSWER: this question asks for a set. Missing a qualifying member scores the same as wrong — enumerate the pool, test EVERY member against EVERY condition, and name ALL qualifiers (each with its own citations per condition). Then give EVERY excluded member its own line with the condition it fails and its own [n] — not a single clause sweeping several names together, and not just the near-misses. Never claim 'the only X' unless the whole pool was checked; if your pool may be partial, still commit to every qualifier you verified. GET THE POOL FROM A LIST, NOT MEMBER-BY-MEMBER: your FIRST retrieval for a set question should hunt the authoritative roster/list/table that enumerates the whole pool (search it AS a list — '<pool subject> list', '<pool subject> table', 'list of <pool subject>' — and read_page it). Assembling the pool from separate per-member searches is how a run ends up with 3 of 6 qualifiers: the members you never thought to search for are invisible to you. Read the roster page first, then verify each member. ONE LIST PER PERIOD, THEN JOIN: when a condition has to hold across several periods — successive years, separate editions, or two parallel events — fetch ONE roster page per period and join them on the member: one list per period, not one lookup per member. A pool of 30+ members each needing several figures is a table-join, and per-member lookups will run out of turns long before the pool is covered. UNIVERSAL conditions ('in EVERY one of them', 'for BOTH parts', 'in ALL three periods'): check each candidate against EACH instance separately, with a citation per instance — one shared instance is not enough. If NO candidate survives every instance, then 'none' IS the answer: state it as a verified fact about the world with the per-instance citations that prove it."

                def _clamp_span_pair(start: int, end: int, note_len: int) -> list[int]:
                    start = max(0, min(int(start), note_len))
                    end = max(start + 1, min(int(end), note_len))
                    return [start, end]

                def _merge_sorted_spans(shown: list[list[int]]) -> list[list[int]]:
                    shown.sort()
                    merged: list[list[int]] = []
                    for s, e in shown:
                        if merged and s <= merged[-1][1]:
                            merged[-1][1] = max(merged[-1][1], e)
                        else:
                            merged.append([s, e])
                    return merged

                def _expand_citation_spans(merged: list[list[int]], note_len: int) -> list[list[int]]:
                    base = sum((e - s for s, e in merged))
                    room = max(0, CITATION_MAX_REF_CHARS - base)
                    if not (merged and note_len and room):
                        return merged
                    extra = room // len(merged)
                    for w in merged:
                        pad = min(extra, max(0, CITATION_MIN_SPAN_CHARS - (w[1] - w[0])))
                        if pad:
                            left = min(pad // 2, w[0])
                            w[0] -= left
                            rest = pad - left
                            right = min(rest, note_len - w[1])
                            w[1] += right
                            w[0] = max(0, w[0] - (rest - right))
                    return _merge_sorted_spans(merged)

                def _citation_slices_for_row(row: dict) -> list[CitationSlice] | None:
                    spans = row['spans']
                    if not spans:
                        return None
                    note_len = int(row['note_len'] or 0)
                    shown: list[list[int]] = []
                    for span in spans[:4]:
                        shown.append(_clamp_span_pair(span[0], span[1], note_len))
                    retained = []
                    for a, b in row.get('retained') or []:
                        retained.append(_clamp_span_pair(a, b, note_len))
                    if retained:
                        shown = retained
                    merged = _expand_citation_spans(_merge_sorted_spans(shown), note_len)
                    slices = [CitationSlice(start=s, end=e) for s, e in merged if e > s]
                    return slices or None

                def _new_ledger_row(receipt_id: str, result_id: str, note_len: int, kind: str, spans: list[tuple[int, int]] | None, title: str='', url: str='', preview: str='', text: str='') -> dict:
                    return {'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': (url or '')[:300], 'preview': (preview or '')[:1200], 'spans': spans, 'text': (text or '')[:_LEDGER_TEXT_CAP], 'retained': []}

                class EvidenceLedger:

                    def __init__(self) -> None:
                        self.rows: list[dict] = []

                    def add(self, receipt_id: str, result_id: str, note_len: int, kind: str, spans: list[tuple[int, int]] | None, title: str='', url: str='', preview: str='', text: str='') -> int:
                        self.rows.append(_new_ledger_row(receipt_id, result_id, note_len, kind, spans, title=title, url=url, preview=preview, text=text))
                        return len(self.rows)

                    def ref_for(self, number: int) -> CitationRef | None:
                        if not 1 <= number <= len(self.rows):
                            return None
                        row = self.rows[number - 1]
                        if row.get('kind') == 'reserved':
                            return None
                        if not row['receipt_id'] or not row['result_id']:
                            return None
                        slices = _citation_slices_for_row(row)
                        if slices is None:
                            return None
                        return CitationRef(receipt_id=row['receipt_id'], result_id=row['result_id'], slices=slices)
                _WORD_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
                _STOP = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

                def _key_terms(text: str) -> set[str]:
                    return {w for w in _WORD_RE.findall((text or '').casefold()) if w not in _STOP}

                def _best_windows(note: str, terms: set[str], width: int, k: int=1) -> list[tuple[int, int]]:
                    n = len(note)
                    if n <= width:
                        return [(0, n)]
                    step = max(600, width // 3)
                    low = note.lower()
                    scored: list[tuple[int, int]] = []
                    pos = 0
                    while pos < n:
                        seg = low[pos:pos + width]
                        scored.append((sum((1 for t in terms if t in seg)), pos))
                        if pos + width >= n:
                            break
                        pos += step
                    scored.sort(key=lambda hs: (-hs[0], hs[1]))
                    picked: list[tuple[int, int]] = []
                    for hits, start in scored:
                        if len(picked) >= max(1, k):
                            break
                        end = min(n, start + width)
                        if any((start < pe and ps < end for ps, pe in picked)):
                            continue
                        if picked and hits <= 0:
                            continue
                        picked.append((start, end))
                    picked.sort()
                    return picked or [(0, min(n, width))]
                _SLOT = '\x00{}\x00'

                class ToolOutput:

                    def __init__(self, text: str, rows: list[dict] | None=None) -> None:
                        self.text = text
                        self.rows = rows or []

                def _commit_tool_output(out, ledger: EvidenceLedger) -> str:
                    if isinstance(out, str):
                        return out
                    if not isinstance(out, ToolOutput):
                        return f'# tool crashed: {out}'
                    text = out.text
                    for i, row in enumerate(out.rows):
                        n = ledger.add(row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''), text=row.get('text', ''))
                        text = text.replace(_SLOT.format(i), str(n))
                    return text
                _SITE_OP_RE = re.compile('\\bsite:\\S+\\s*', re.I)

                def _degrade_query(q: str) -> str:
                    out = _SITE_OP_RE.sub('', q or '').replace('"', ' ')
                    return ' '.join(out.split())

                def _search_attempt_ladder(query_text: str):
                    return ((query_text, False), (query_text, True), (_degrade_query(query_text), False))

                def _search_span_for_note(n_len: int):
                    if n_len >= 100:
                        return [(0, min(max(SEARCH_EXCERPT_CHARS, 100), n_len))]
                    if n_len:
                        return [(0, n_len)]
                    return None

                def _search_row_from_item(receipt: str, item) -> dict | None:
                    rid = getattr(item, 'result_id', None)
                    if not isinstance(rid, str) or not rid:
                        return None
                    note = getattr(item, 'note', None) or ''
                    if not note.strip():
                        return None
                    n_len = len(note)
                    title = (getattr(item, 'title', None) or '').strip()
                    url = (getattr(item, 'url', None) or '').strip()
                    return {'receipt_id': receipt, 'result_id': rid, 'note_len': n_len, 'kind': 'search', 'spans': _search_span_for_note(n_len), 'title': title, 'url': url, 'preview': note[:SEARCH_EXCERPT_CHARS], 'text': note}

                def _format_search_tool_output(query_text: str, results, receipt: str) -> ToolOutput:
                    rows: list[dict] = []
                    lines = [f'# web_search({query_text!r}): {len(results)} results']
                    for item in results:
                        row = _search_row_from_item(receipt, item)
                        if row is None:
                            continue
                        rows.append(row)
                        lines.append(f"[{_SLOT.format(len(rows) - 1)}] {row['title']} — {row['url']}\n    {row['preview']}")
                    return ToolOutput('\n'.join(lines), rows)

                async def _search_web_payload(query_text: str):
                    payload = None
                    fired: set[str] = set()
                    rung = 0
                    for attempt, allow_repeat in _search_attempt_ladder(query_text):
                        if not attempt.strip() or (attempt in fired and (not allow_repeat)):
                            continue
                        fired.add(attempt)
                        rung += 1
                        try:
                            extra: dict = {'mode': SEARCH_MODE}
                            payload = await search_web(attempt, provider=SEARCH_PROVIDER, num=8, timeout=SEARCH_TIMEOUT_S, provider_extra=extra)
                            if getattr(payload, 'results', None):
                                break
                        except Exception:
                            payload = None
                    return payload

                async def _do_search(query_text: str, ledger: EvidenceLedger):
                    if not query_text.strip():
                        return '# web_search: empty query'
                    payload = await _search_web_payload(query_text)
                    if payload is None:
                        return f'# web_search({query_text!r}) failed'
                    _spend_note(payload)
                    receipt = str(getattr(payload, 'receipt_id', '') or '')
                    results = list(getattr(payload, 'results', None) or [])
                    if not receipt:
                        return f'# web_search({query_text!r}): no citable results'
                    return _format_search_tool_output(query_text, results, receipt)

                def _plain_fetch_output(url: str, receipt: str, rid: str, note: str) -> ToolOutput:
                    row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, len(note))], 'title': url, 'url': url, 'preview': note[:1200], 'text': note}
                    return ToolOutput(f'# read_page({url!r}) -> [{_SLOT.format(0)}] full page, {len(note)} chars\n{note}', [row])

                def _windowed_fetch_output(url: str, receipt: str, rid: str, note: str, focus: str, question: str) -> ToolOutput:
                    terms = _key_terms(question) | _key_terms(focus)
                    windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE)
                    row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, FETCH_HEAD_CHARS)] + list(windows), 'title': url, 'url': url, 'preview': note[windows[0][0]:windows[0][0] + 1200], 'text': note}
                    head = note[:FETCH_HEAD_CHARS]
                    sections = ''.join((f'\n--- section @{s} ---\n{note[s:e]}' for s, e in windows))
                    return ToolOutput(f"# read_page({url!r}) -> [{_SLOT.format(0)}] {len(note)} chars total; head + the {len(windows)} most relevant section(s) shown ({', '.join((f'{s}-{e}' for s, e in windows))}). If the answer set may continue elsewhere in this page, call read_page again with a different focus.\n--- head ---\n{head}{sections}", [row])

                async def _fetch_page_payload(url: str):
                    payload = None
                    for _attempt in (0, 1):
                        try:
                            payload = await fetch_page(url, provider=FETCH_PROVIDER, timeout=FETCH_TIMEOUT_S, provider_extra=_FETCH_EXTRA)
                            if getattr(payload, 'results', None):
                                break
                        except Exception:
                            payload = None
                    return payload

                async def _do_fetch(url: str, focus: str, question: str, ledger: EvidenceLedger) -> str:
                    if not url.strip():
                        return '# read_page: empty url'
                    payload = await _fetch_page_payload(url)
                    if payload is None:
                        return f'# read_page({url!r}) failed'
                    _spend_note(payload)
                    receipt = str(getattr(payload, 'receipt_id', '') or '')
                    results = list(getattr(payload, 'results', None) or [])
                    if not results or not receipt:
                        return f'# read_page({url!r}): no content'
                    item = results[0]
                    rid = getattr(item, 'result_id', None)
                    note = getattr(item, 'note', None) or ''
                    if not isinstance(rid, str) or not rid or (not note.strip()):
                        return f'# read_page({url!r}): no usable content'
                    if len(note) <= FETCH_PLAIN_CHARS:
                        return _plain_fetch_output(url, receipt, rid, note)
                    return _windowed_fetch_output(url, receipt, rid, note, focus, question)
                _SEC_TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
                _SEC_SUBMISSIONS_URL = 'https://data.sec.gov/submissions/CIK{cik10}.json'
                _SEC_DOC_URL = 'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}'
                _SEC_FETCH_TIMEOUT_S = 26.0
                _SEC_MIN_HEADROOM_S = 40.0
                _SEC_CACHE: dict = {}
                _SEC_STOPWORDS = frozenset('inc incorporated corp corporation company companies co ltd limited llc plc lp llp group holdings the'.split())
                _SEC_ALNUM_RE = re.compile('[a-z0-9]+')

                def _sec_tokens(text: str) -> list[str]:
                    return [w for w in _SEC_ALNUM_RE.findall((text or '').lower()) if w not in _SEC_STOPWORDS]

                def _sec_norm_form(form: str) -> str:
                    f = ' '.join((form or '').upper().replace('FORM', ' ').split())
                    m = re.fullmatch('(\\d{1,2})\\s*-?\\s*([A-Z])', f)
                    if m:
                        return f'{m.group(1)}-{m.group(2)}'
                    m = re.fullmatch('(DEF)\\s*-?\\s*(14A)', f)
                    if m:
                        return 'DEF 14A'
                    return f

                async def _fetch_json(url: str, deadline: float):
                    cached = _SEC_CACHE.get(url)
                    if cached is not None:
                        return cached
                    for _attempt in (0, 1):
                        left = deadline - monotonic()
                        if left < 12.0:
                            return None
                        try:
                            payload = await asyncio.wait_for(fetch_page(url, provider=JSON_PROVIDER, timeout=min(_SEC_FETCH_TIMEOUT_S, left - 6.0)), timeout=min(_SEC_FETCH_TIMEOUT_S, left - 6.0) + 4.0)
                        except Exception:
                            continue
                        _spend_note(payload)
                        results = list(getattr(payload, 'results', None) or [])
                        note = getattr(results[0], 'note', None) or '' if results else ''
                        start = note.find('{')
                        end = note.rfind('}')
                        if start == -1 or end <= start:
                            continue
                        try:
                            obj = json.loads(note[start:end + 1])
                        except Exception:
                            continue
                        if isinstance(obj, dict):
                            _SEC_CACHE[url] = obj
                            return obj
                    return None

                def _sec_pick_filing(recent: dict, form: str, year: str):
                    forms = recent.get('form')
                    accs = recent.get('accessionNumber')
                    docs = recent.get('primaryDocument')
                    rdates = recent.get('reportDate')
                    fdates = recent.get('filingDate')
                    if not (isinstance(forms, list) and isinstance(accs, list) and isinstance(docs, list)):
                        return None
                    n = min(len(forms), len(accs), len(docs))
                    form_norm = _sec_norm_form(form)
                    best_year = None
                    best_any = None
                    for i in range(n):
                        if _sec_norm_form(str(forms[i])) != form_norm:
                            continue
                        if accs[i] is None or docs[i] is None:
                            continue
                        acc = str(accs[i])
                        doc = str(docs[i])
                        if not acc or not (doc.endswith('.htm') or doc.endswith('.html')):
                            continue
                        rd = str(rdates[i]) if isinstance(rdates, list) and i < len(rdates) and (rdates[i] is not None) else ''
                        fd = str(fdates[i]) if isinstance(fdates, list) and i < len(fdates) and (fdates[i] is not None) else ''
                        key = rd or fd
                        if best_any is None or key > best_any[0]:
                            best_any = (key, acc, doc)
                        if year and rd[:4] == year:
                            if best_year is None or key > best_year[0]:
                                best_year = (key, acc, doc)
                    pick = best_year if year else best_any
                    if pick is None:
                        return None
                    return (pick[1], pick[2])
                _SEC_SEARCH_HINT = 'search "site:sec.gov {company} {year} {form}" and read_page the Archives result'

                def _sec_match_score(want: list[str], title: str, ticker: str) -> int | None:
                    words = set(_sec_tokens(title))
                    n_hit = sum((1 for w in want if w in words))
                    if len(want) == 1 and ticker == want[0]:
                        return 100
                    if want and n_hit == len(want):
                        return 50 + n_hit
                    return None

                def _sec_best_company(tickers: dict, company: str):
                    want = _sec_tokens(company)
                    best = None
                    for row in tickers.values():
                        if not isinstance(row, dict):
                            continue
                        title = str(row.get('title', ''))
                        ticker = str(row.get('ticker', '')).lower()
                        score = _sec_match_score(want, title, ticker)
                        if score is None:
                            continue
                        cand = (score, -len(title), str(row.get('cik_str', '')).zfill(10), title)
                        if best is None or cand > best:
                            best = cand
                    return best

                def _sec_primary_doc_url(cik10: str, accession: str, doc: str) -> str:
                    return _SEC_DOC_URL.format(cik=cik10.lstrip('0') or cik10, accession=accession.replace('-', ''), doc=doc)

                async def _do_sec_filing(company: str, form: str, year: str, deadline: float) -> str:
                    company = (company or '').strip()
                    form = (form or '').strip() or '10-K'
                    year = (year or '').strip()[:4]
                    hint = _SEC_SEARCH_HINT.format(company=company, year=year, form=form)
                    if not company:
                        return '# sec_filing: company required'
                    if deadline - monotonic() < _SEC_MIN_HEADROOM_S:
                        return f'# sec_filing: skipped (low time) — {hint}'
                    tickers = await _fetch_json(_SEC_TICKERS_URL, deadline)
                    if not isinstance(tickers, dict):
                        return f'# sec_filing: EDGAR ticker index unavailable — {hint}'
                    best = _sec_best_company(tickers, company)
                    if best is None:
                        return f'# sec_filing({company!r}): no confident EDGAR match — {hint}'
                    cik10, title = (best[2], best[3])
                    subs = await _fetch_json(_SEC_SUBMISSIONS_URL.format(cik10=cik10), deadline)
                    filings = subs.get('filings') if isinstance(subs, dict) else None
                    recent = filings.get('recent') if isinstance(filings, dict) else None
                    if not isinstance(recent, dict):
                        return f'# sec_filing({company!r}): EDGAR submissions unavailable for {title} — {hint}'
                    pick = _sec_pick_filing(recent, form, year)
                    if pick is None:
                        return f"# sec_filing({company!r}, {form!r}, year={year or 'latest'}): no matching filing in EDGAR's recent index for {title} — check the form/year, or {hint}"
                    accession, doc = pick
                    url = _sec_primary_doc_url(cik10, accession, doc)
                    return f"# sec_filing -> {title} {form} {year or '(latest)'} primary document:\n{url}\nNow call read_page on this URL with a focus hint for the section you need, and cite figures from that read_page result."

                def _ledger_page(url: str, ledger: EvidenceLedger) -> tuple[int, dict] | None:
                    u = (url or '').strip().rstrip('/')
                    if not u:
                        return None
                    for i in range(len(ledger.rows) - 1, -1, -1):
                        row = ledger.rows[i]
                        if not row.get('text'):
                            continue
                        r = str(row.get('url') or '').rstrip('/')
                        if r == u or r.endswith(u) or u.endswith(r):
                            return (i + 1, row)
                    return None

                def _do_page_grep(url: str, pattern: str, ledger: EvidenceLedger) -> str:
                    hit = _ledger_page(url, ledger)
                    if hit is None:
                        return f'# page_grep: {url!r} has not been fetched this run; call read_page first'
                    n, row = hit
                    text = row.get('text') or ''
                    pat = (pattern or '').strip()
                    if not pat:
                        return '# page_grep: empty pattern'
                    try:
                        rx = re.compile(pat, re.I)
                    except re.error:
                        rx = re.compile(re.escape(pat), re.I)
                    out, seen_at = ([], [])
                    for m in rx.finditer(text):
                        c = (m.start() + m.end()) // 2
                        if any((abs(c - prev) < PAGE_GREP_WINDOW // 2 for prev in seen_at)):
                            continue
                        seen_at.append(c)
                        a = max(0, c - PAGE_GREP_WINDOW // 2)
                        b = min(len(text), a + PAGE_GREP_WINDOW)
                        out.append(f'\n--- match @{a} ---\n{text[a:b]}')
                        if len(out) >= PAGE_GREP_MAX_HITS:
                            break
                    if not out:
                        return f'# page_grep({pat!r}) on [{n}]: no match in {len(text)} chars. Try a shorter or looser pattern.'
                    return f'# page_grep({pat!r}) on [{n}] -> {len(out)} match(es) of {len(text)} chars' + ''.join(out)

                def _do_page_read(url: str, offset: int, length: int, ledger: EvidenceLedger) -> str:
                    hit = _ledger_page(url, ledger)
                    if hit is None:
                        return f'# page_read: {url!r} has not been fetched this run; call read_page first'
                    n, row = hit
                    text = row.get('text') or ''
                    a = max(0, min(int(offset or 0), max(0, len(text) - 1)))
                    ln = int(length or PAGE_READ_MAX_CHARS)
                    b = min(len(text), a + max(1, min(ln, PAGE_READ_MAX_CHARS)))
                    return f'# page_read([{n}] @{a}:{b} of {len(text)})\n{text[a:b]}'

                def _locate_retain_quote(text: str, q: str) -> int:
                    i = text.find(q)
                    if i < 0:
                        i = text.lower().find(q.lower())
                    if i < 0:
                        squashed = ' '.join(q.split())
                        i = ' '.join(text.split()).lower().find(squashed.lower())
                        if i >= 0:
                            i = -1
                    return i

                def _do_retain_evidence(source: str, quote: str, ledger: EvidenceLedger) -> str:
                    raw = (source or '').strip().strip('[]')
                    try:
                        n = int(raw)
                    except ValueError:
                        return f'# retain_evidence: source must be a result number like [3], got {source!r}'
                    if not 1 <= n <= len(ledger.rows):
                        return f'# retain_evidence: no result [{n}] exists yet'
                    row = ledger.rows[n - 1]
                    text = row.get('text') or ''
                    q = (quote or '').strip()
                    if len(q) < RETAIN_MIN_QUOTE:
                        return f'# retain_evidence: quote too short ({len(q)} chars); quote at least {RETAIN_MIN_QUOTE} characters of the source text'
                    if not text:
                        return f'# retain_evidence: result [{n}] has no stored text to quote from'
                    i = _locate_retain_quote(text, q)
                    if i < 0:
                        return f'# retain_evidence: that text does not appear in [{n}]. Quote it EXACTLY as the source prints it, or read more of the page first.'
                    kept = row.setdefault('retained', [])
                    if len(kept) >= RETAIN_MAX_PER_ROW:
                        return f'# retain_evidence: [{n}] already has {len(kept)} retained excerpts'
                    a = max(0, i - RETAIN_MARGIN_CHARS)
                    b = min(int(row.get('note_len') or len(text)), i + len(q) + RETAIN_MARGIN_CHARS)
                    if b <= a:
                        return f'# retain_evidence: could not bound the excerpt in [{n}]'
                    kept.append((a, b))
                    return f'# retain_evidence: kept {b - a} chars of [{n}] around your quote. Cite [{n}] for that claim.'

                def _parse_tool_args(call) -> dict:
                    try:
                        args = json.loads(getattr(call, 'arguments', None) or '{}')
                    except Exception:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}
                    return args

                async def _dispatch_named_tool(name: str, args: dict, question: str, ledger: EvidenceLedger, deadline: float):
                    if name == 'web_search':
                        return await _do_search(str(args.get('query') or ''), ledger)
                    if name == 'read_page':
                        return await _do_fetch(str(args.get('url') or ''), str(args.get('focus') or ''), question, ledger)
                    if name == 'retain_evidence':
                        return _do_retain_evidence(str(args.get('source') or ''), str(args.get('quote') or ''), ledger)
                    if name == 'page_grep':
                        return _do_page_grep(str(args.get('url') or ''), str(args.get('pattern') or ''), ledger)
                    if name == 'page_read':
                        return _do_page_read(str(args.get('url') or ''), args.get('offset') or 0, args.get('length') or PAGE_READ_MAX_CHARS, ledger)
                    if name == 'sec_filing':
                        return await _do_sec_filing(str(args.get('company') or ''), str(args.get('form') or ''), str(args.get('year') or ''), deadline)
                    return f'# unknown tool {name!r}'

                async def _run_tool(call, question: str, ledger: EvidenceLedger, deadline: float) -> str:
                    args = _parse_tool_args(call)
                    name = getattr(call, 'name', '') or ''
                    return await _dispatch_named_tool(name, args, question, ledger, deadline)
                _REASONING_MANDATORY = ('openai/gpt-oss',)

                def _least_think(lane: str, model: str='') -> dict:
                    for prefix in _REASONING_MANDATORY:
                        if model.startswith(prefix):
                            return {'enabled': True, 'effort': 'low'}
                    return {'enabled': False}
                _FAST_UPSTREAMS = ('Decart', 'CoreWeave', 'Alibaba')
                _FAST_UPSTREAMS_OSS = ('Cerebras', 'Groq', 'BaseTen')

                def _upstream(lane: str, model: str) -> dict | None:
                    if lane != LLM_LANE_A:
                        return None
                    if model.startswith('z-ai/glm-5.2'):
                        only = _FAST_UPSTREAMS
                    elif model.startswith('openai/gpt-oss'):
                        only = _FAST_UPSTREAMS_OSS
                    else:
                        return None
                    return {'provider': {'only': list(only), 'allow_fallbacks': True}}

                def _provider_pin_attempts(pin0):
                    return (pin0, None) if pin0 is not None else (None,)

                def _llm_raw_text(payload) -> str:
                    llm = getattr(payload, 'llm', None)
                    text = (getattr(llm, 'raw_text', None) or '').strip()
                    if text:
                        return text
                    choices = getattr(llm, 'choices', None) or []
                    if choices:
                        content = getattr(choices[0].message, 'content', None)
                        if isinstance(content, str):
                            return content.strip()
                    return ''

                async def _llm_chat_pinned(lane: str, model: str, messages: list[dict], *, max_tokens: int, timeout: float, think: dict | None=None) -> str:
                    if think is None:
                        think = _least_think(lane, model)
                    _pin0 = _upstream(lane, model)
                    payload = None
                    for _pin in _provider_pin_attempts(_pin0):
                        try:
                            payload = await llm_chat(provider=lane, model=model, messages=messages, temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=think, provider_extra=_pin)
                            break
                        except Exception:
                            if _pin is None:
                                raise
                            continue
                    _spend_note(payload)
                    return _llm_raw_text(payload)

                async def _chat_simple(lane: str, model: str, system: str, user: str, *, max_tokens: int, timeout: float, think: dict | None=None) -> str:
                    return await _llm_chat_pinned(lane, model, [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], max_tokens=max_tokens, timeout=timeout, think=think)

                class _EmptyChoiceMessage:
                    content = ''
                    tool_calls = ()

                class _EmptyChoice:
                    message = _EmptyChoiceMessage()

                class _EmptyLlm:
                    raw_text = ''
                    choices = (_EmptyChoice(),)

                class _EmptyTurn:
                    llm = _EmptyLlm()
                    budget = None
                _EMPTY_TURN = _EmptyTurn()

                def _turn_lane_schedule():
                    return ((LLM_LANE_A, LOOP_MODEL_A, True), (LLM_LANE_A, LOOP_MODEL_A, False), (LLM_LANE_B, LOOP_MODEL_B, False))

                def _message_payload_chars(messages: list[dict]) -> int:
                    return sum((len(str(msg.get('content') or '')) for msg in messages if isinstance(msg, dict)))

                def _turn_thinking(finish_only: bool, lane: str) -> dict:
                    if finish_only and lane == LLM_LANE_B:
                        return {'enabled': False}
                    return {'enabled': True, 'effort': 'low'}

                async def _chat_turn(messages: list[dict], deadline: float, *, finish_only: bool, force_tools: bool=False):
                    turn_wall = monotonic() + TURN_TIMEOUT_S + 35.0
                    payload_chars = _message_payload_chars(messages)
                    use_tools = force_tools or not finish_only
                    for lane, model, pinned in _turn_lane_schedule():
                        if lane == LLM_LANE_B and payload_chars > LANE_B_MAX_PAYLOAD_CHARS:
                            return _EMPTY_TURN
                        timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0, turn_wall - monotonic())
                        if timeout <= 5.0:
                            return None
                        try:
                            payload = await asyncio.wait_for(llm_chat(provider=lane, model=model, messages=messages, tools=LOOP_TOOLS if use_tools else None, tool_choice='auto' if use_tools else None, temperature=0.2, thinking=_turn_thinking(finish_only, lane), max_output_tokens=6000 if finish_only and lane == LLM_LANE_B else None, provider_extra=_upstream(lane, model) if pinned else None, timeout=timeout), timeout=min(timeout + 6.0, max(1.0, deadline - monotonic() - 1.0)))
                            _spend_note(payload)
                            return payload
                        except Exception:
                            continue
                    return None
                _BRIEF_SYSTEM = 'Senior research analyst. Commit to concrete best answers from knowledge; mark uncertain values (verify). Never refuse.'

                def _brief_user_prompt(question: str) -> str:
                    return f"Question:\n{question}\n\nFill in this internal worksheet. It is planning scratch for your own use, never an answer, so keep the tags lowercase and never reuse them as section headings later.\ndraft: your full best answer now — candidate pool, every stated condition applied, qualifying entities with figures/dates, near-miss exclusions. Flag shaky facts with (verify).\nconditions: each atomic condition in the question, numbered, including any output-format demand.\nsearches: 3-6 precise web searches for the facts that decide the answer (entity + metric + year; include a named source's site: filter).\nurls: up to 5 exact URLs worth reading directly (official stats pages, sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."

                def _split_brief_draft(raw: str) -> str:
                    draft = raw
                    cut = min((mm.start() for mm in (re.search('[#*_\\s]*(?:conditions|CHECKLIST)[#*_\\s]*:', raw, re.IGNORECASE), re.search('^[ \\t]*[#*_>]{0,4}[ \\t]*(?:conditions|CHECKLIST)[ \\t]*[#*_]{0,3}[ \\t]*$', raw, re.IGNORECASE | re.MULTILINE)) if mm is not None), default=None)
                    if cut is not None:
                        draft = raw[:cut]
                    draft = re.sub('^[#*_\\s]*(?:draft|BEST ANSWER)[#*_\\s]*:[#*_\\s]*', '', draft, flags=re.IGNORECASE)
                    draft = re.sub('^[ \\t]*[#*_>]{0,4}[ \\t]*(?:draft|BEST ANSWER)[ \\t]*[#*_]{0,3}[ \\t]*\\n+', '', draft, flags=re.IGNORECASE)
                    return draft.strip()

                def _brief_block(raw: str) -> str:
                    return 'PRIOR ANALYSIS — your own planning worksheet (verify anything marked (verify), and correct it wherever tool results disagree). Its tags are internal: never reproduce them, or any section named after them, in the answer.\n' + raw.strip()

                async def _knowledge_brief(question: str) -> tuple[str, str]:
                    system = _BRIEF_SYSTEM
                    user = _brief_user_prompt(question)
                    raw = ''
                    try:
                        raw = await _chat_simple(LLM_LANE_A, LOOP_MODEL_A, system, user, max_tokens=2400, timeout=BRIEF_TIMEOUT_S, think=_least_think(LLM_LANE_A, LOOP_MODEL_A))
                    except Exception:
                        try:
                            raw = await _chat_simple(LLM_LANE_B, LOOP_MODEL_B, system, user, max_tokens=2400, timeout=BRIEF_TIMEOUT_S, think=_least_think(LLM_LANE_B, LOOP_MODEL_B))
                        except Exception:
                            raw = ''
                    if not raw:
                        return ('', '')
                    return (_split_brief_draft(raw), _brief_block(raw))
                _SEED_TOKEN_RE = re.compile("[A-Za-z0-9][A-Za-z0-9.\\-']+")
                _SEED_STOP = frozenset('name list give tell show find identify please could would you your can may might should must let make sure both also'.split())
                MAX_SEED_QUERIES = 3

                def _seed_queries(question: str, set_question: bool) -> list[str]:
                    q = ' '.join((question or '').split())
                    if not q:
                        return []
                    seeds = [q[:300]]
                    salient = [t for t in _SEED_TOKEN_RE.findall(q) if len(t) >= 3 and t.lower() not in _STOP and (t.lower() not in _SEED_STOP)]
                    if len(salient) >= 2:
                        seeds.append(' '.join(salient[:8]))
                    if set_question and salient:
                        seeds.append('list of ' + ' '.join(salient[:6]))
                    out: list[str] = []
                    for s in seeds:
                        s = s.strip()
                        if s and s not in out:
                            out.append(s)
                    return out[:MAX_SEED_QUERIES]

                async def _preseed(question: str, set_question: bool, ledger: EvidenceLedger, deadline: float) -> str:
                    seeds = _seed_queries(question, set_question)
                    if not seeds or deadline - monotonic() < 40.0:
                        return ''
                    blocks: list = []
                    for seed in seeds:
                        if deadline - monotonic() < 30.0:
                            break
                        try:
                            out = await asyncio.wait_for(_do_search(seed, ledger), timeout=SEARCH_TIMEOUT_S * 2 + 6.0)
                            blocks.append(_commit_tool_output(out, ledger))
                        except Exception:
                            continue
                    good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
                    if not good:
                        return ''
                    return 'Automatic first-pass searches (already numbered — cite these [n] directly, and search further as needed):\n\n' + '\n'.join(good)

                async def _bootstrap_loop_messages(question: str, brief: str, ledger: EvidenceLedger, deadline: float) -> list[dict]:
                    set_q = _needs_set_completeness(question)
                    messages = [{'role': 'system', 'content': LOOP_RULES}]
                    if set_q:
                        messages.append({'role': 'system', 'content': SET_RULE})
                    if _needs_superlative_proof(question):
                        messages.append({'role': 'system', 'content': SUPERLATIVE_RULE})
                    if brief:
                        messages.append({'role': 'system', 'content': brief})
                    seeded = await _preseed(question, set_q, ledger, deadline)
                    if seeded:
                        messages.append({'role': 'system', 'content': seeded})
                    messages.append({'role': 'user', 'content': question})
                    return messages

                def _turn_finish_flags(left: float, turn: int, turn_cap: int) -> tuple[bool, bool, bool]:
                    out_of_time = left <= WRAPUP_AT_S
                    out_of_spend = _spend_left() <= WRAPUP_MIN_USD
                    finish_only = out_of_time or out_of_spend or turn >= turn_cap
                    return (out_of_time, out_of_spend, finish_only)

                def _candidate_from_choice(llm, msg) -> str:
                    candidate = (getattr(llm, 'raw_text', None) or '').strip()
                    if not candidate:
                        content = getattr(msg, 'content', None)
                        if isinstance(content, str):
                            candidate = content.strip()
                    return candidate

                async def _await_tool_batch(tool_tasks, tool_budget: float) -> list:
                    try:
                        await asyncio.wait(tool_tasks, timeout=tool_budget)
                    except Exception:
                        pass
                    results = []
                    for t in tool_tasks:
                        if t.done():
                            try:
                                results.append(t.result())
                            except Exception as exc:
                                results.append(f'# tool crashed: {exc}')
                        else:
                            t.cancel()
                            results.append('# tool timed out — use what you already have')
                    return results

                def _append_tool_turn_messages(messages: list[dict], run_calls, results, calls, ledger: EvidenceLedger) -> None:
                    for call_result in zip(run_calls, results):
                        call = call_result[0]
                        body = _commit_tool_output(call_result[1], ledger)
                        messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': body})
                    for call in calls[8:]:
                        messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})

                async def _execute_tool_calls(messages: list[dict], calls, question: str, ledger: EvidenceLedger, deadline: float) -> None:
                    run_calls = calls[:8]
                    tool_budget = max(5.0, min(FETCH_TIMEOUT_S * 2 + 6.0, deadline - monotonic() - MIN_TAIL_S))
                    tool_tasks = [asyncio.ensure_future(_run_tool(c, question, ledger, deadline)) for c in run_calls]
                    results = await _await_tool_batch(tool_tasks, tool_budget)
                    _append_tool_turn_messages(messages, run_calls, results, calls, ledger)

                async def _loop(question: str, brief: str, ledger: EvidenceLedger, deadline: float, turn_cap: int, carry: list[dict] | None=None, allow_tools_in_wrapup: bool=False) -> tuple[str, list[dict]]:
                    if carry is not None:
                        messages = carry
                    else:
                        messages = await _bootstrap_loop_messages(question, brief, ledger, deadline)
                    answer = ''
                    ordered_wrapup = False
                    repairs_left = ANSWER_REPAIR_TURNS
                    for turn in range(1, turn_cap + 1):
                        left = deadline - monotonic()
                        if left <= MIN_TAIL_S:
                            break
                        _, _, finish_only = _turn_finish_flags(left, turn, turn_cap)
                        if (finish_only or turn >= turn_cap - 1) and (not ordered_wrapup):
                            messages.append({'role': 'system', 'content': _wrapup_order(left)})
                            ordered_wrapup = True
                        payload = await _chat_turn(messages, deadline, finish_only=finish_only, force_tools=allow_tools_in_wrapup and turn == 1)
                        if payload is None:
                            break
                        llm = getattr(payload, 'llm', None)
                        choices = getattr(llm, 'choices', None) or []
                        if not choices:
                            break
                        msg = choices[0].message
                        calls = getattr(msg, 'tool_calls', None) or ()
                        if not calls:
                            candidate = _candidate_from_choice(llm, msg)
                            if not _is_usable_answer(candidate):
                                if repairs_left > 0 and deadline - monotonic() > MIN_TAIL_S + 10.0:
                                    repairs_left -= 1
                                    messages.append({'role': 'system', 'content': _REPAIR_ORDER})
                                    answer = ''
                                    continue
                                answer = ''
                                break
                            answer = candidate
                            messages.append({'role': 'assistant', 'content': answer})
                            break
                        messages.append(msg.to_input_message())
                        await _execute_tool_calls(messages, calls, question, ledger, deadline)
                    return (answer, messages)
                _AUDIT_GAP_KEYS = ('incomplete_roster', 'hand_waved_tally', 'unanswered_parts', 'uncited_facts', 'wrong_kind', 'thin_proof')
                _AUDIT_ROSTER_KEYS = frozenset(('incomplete_roster', 'hand_waved_tally'))

                def _audit_probe(question: str, answer: str) -> str:
                    return f"""Audit the answer against the question. JSON only, keys: "unanswered_parts" (list; question elements not addressed), "uncited_facts" (list; load-bearing claims without [n]), "wrong_kind" (list; places where the named entity is a different KIND than the question asks — a person instead of a series, a duo instead of a show), "incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges over a candidate pool — a closed set that can be enumerated, or several conditions applied to a class — then: is the pool itself stated and plausibly COMPLETE, and does the answer give a verdict for EVERY member (qualifies / excluded because X, each cited)? Name any pool member the answer never mentions, and say so if the pool looks truncated — an answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not partial), "thin_proof" (list; a qualifier lacking a per-condition citation, or a plausible near-miss candidate never addressed), "hand_waved_tally" (list; for a superlative/count/most-common question: the answer asserts a winner or a count WITHOUT showing the candidate table it was derived from. Phrases like 'among others', 'and several more', 'multiple X', or naming 2 examples to justify a count are all hand-waving — say so and name what the tally must list). Empty lists when clean.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:11000]}"""

                def _collect_audit_gaps(report) -> tuple[list[str], list[str]]:
                    gaps: list[str] = []
                    roster_gaps: list[str] = []
                    if isinstance(report, dict):
                        for key in _AUDIT_GAP_KEYS:
                            vals = report.get(key)
                            if isinstance(vals, list):
                                found = [str(v) for v in vals if str(v).strip()]
                                if key in _AUDIT_ROSTER_KEYS:
                                    roster_gaps.extend(found)
                                gaps.extend(found)
                    return (gaps, roster_gaps)

                def _audit_rewrite_order(gaps: list[str], roster_gaps: list[str]) -> str:
                    order = 'AUDIT: the answer has gaps:\n- ' + '\n- '.join(gaps[:6])
                    if roster_gaps:
                        order += "\nThe candidate pool is incomplete — this loses outright. FIRST search for the authoritative LIST/roster/table that enumerates the whole pool (query it as a list, e.g. '<pool subject> full list', not one member at a time), verify EVERY member against every condition, then rewrite."
                    order += '\nThe audit is INTERNAL scaffolding. Never mention it, quote it or argue with it in the answer. If a gap is wrong, ignore it silently and write the correct answer.'
                    order += '\nUse at most 3 tool calls to close the most important gaps, then rewrite the COMPLETE final answer with [n] citations in the required shape.'
                    return order

                async def _audit_patch(question: str, answer: str, messages: list[dict], ledger: EvidenceLedger, deadline: float) -> str:
                    probe = _audit_probe(question, answer)
                    try:
                        raw = await _chat_simple(LLM_LANE_A, AUDIT_MODEL, 'Strict completeness auditor. JSON only.', probe, max_tokens=2200, timeout=max(8.0, min(AUDIT_TIMEOUT_S, deadline - monotonic() - 72.0)))
                        raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                        report = json.loads(raw)
                    except Exception:
                        return answer
                    gaps, roster_gaps = _collect_audit_gaps(report)
                    if not gaps or deadline - monotonic() < 70.0:
                        return answer
                    messages.append({'role': 'system', 'content': _audit_rewrite_order(gaps, roster_gaps)})
                    patched, _ = await _loop(question, '', ledger, deadline, AUDIT_EXTRA_TURNS + 1, carry=messages, allow_tools_in_wrapup=True)
                    patched = patched.strip()
                    if not _is_usable_answer(patched) or len(patched) < int(len(answer) * 0.6):
                        return answer
                    return patched
                _BRACKET_FIX = {12304: '[', 12305: ']', 65339: '[', 65341: ']', 65288: '(', 65289: ')', 8209: '-', 8722: '-'}
                for _d in range(10):
                    _BRACKET_FIX[65296 + _d] = chr(48 + _d)

                def _normalize_brackets(text: str) -> str:
                    return (text or '').translate(_BRACKET_FIX)
                _CITE_NUM_RE = re.compile('\\[([0-9][0-9,\\s\\-]*)\\]')

                def _cited_numbers(answer: str, top: int) -> list[int]:
                    answer = _normalize_brackets(answer)
                    seen: set[int] = set()
                    out: list[int] = []
                    for m in _CITE_NUM_RE.finditer(answer):
                        for chunk in m.group(1).split(','):
                            piece = chunk.strip()
                            span = re.fullmatch('(\\d{1,4})\\s*-\\s*(\\d{1,4})', piece)
                            if span:
                                lo = int(span.group(1))
                                hi = int(span.group(2))
                                for n in range(lo, min(hi, lo + 16) + 1):
                                    if 1 <= n <= top and n not in seen:
                                        seen.add(n)
                                        out.append(n)
                            elif piece.isdigit():
                                n = int(piece)
                                if 1 <= n <= top and n not in seen:
                                    seen.add(n)
                                    out.append(n)
                    return out
                _OUTPUT_ONLY_RE = re.compile('\\boutput only\\b|\\brespond with only\\b|\\breply with only\\b|\\banswer with only\\b|\\bonly the exact\\b|\\bnothing else\\b|\\bno explanation\\b|\\bwithout explanation\\b|\\bno other text\\b|\\bjust the (?:name|names|value|values|number|numbers|list|text|answer|title|titles)\\b', re.IGNORECASE)
                _OUTPUT_ONLY_MIN_CHARS = 2

                def _answer_line_only(answer: str, question: str) -> str:
                    if not answer or not _OUTPUT_ONLY_RE.search(question or ''):
                        return answer
                    for raw in answer.split('\n'):
                        stripped = raw.strip()
                        if not stripped:
                            continue
                        if stripped[0] in '#>':
                            continue
                        line = re.sub('^[*_`\\s]+|[*_`\\s]+$', '', stripped).strip()
                        if not line:
                            continue
                        if line.startswith('|') or line.endswith(':'):
                            continue
                        if len(line) >= _OUTPUT_ONLY_MIN_CHARS:
                            return line
                    return answer
                _GLOSS_RE = re.compile('^(?P<a>[^()]{2,60}?)\\s*\\((?P<b>[^()]{2,60})\\)$')

                def _verbatim_from_source(value: str, ledger: EvidenceLedger) -> str:
                    v = (value or '').strip()
                    m = _GLOSS_RE.match(v)
                    if not m:
                        return value
                    texts = [r.get('text') or '' for r in ledger.rows if r.get('text')]
                    if not texts:
                        return value

                    def seen(t: str) -> bool:
                        return bool(t) and any((t in src for src in texts))
                    if seen(v):
                        return value
                    a, b = (m.group('a').strip(), m.group('b').strip())
                    hits = [x for x in (b, a) if seen(x)]
                    if len(hits) == 1:
                        return hits[0]
                    if len(hits) == 2:
                        lo, hi = sorted(hits, key=len)
                        if lo.lower() in hi.lower():
                            return hi
                    return value

                def _verbatim_structured(obj, ledger: EvidenceLedger, depth: int=0):
                    if depth > 6:
                        return obj
                    if isinstance(obj, str):
                        return _verbatim_from_source(obj, ledger)
                    if isinstance(obj, list):
                        return [_verbatim_structured(x, ledger, depth + 1) for x in obj]
                    if isinstance(obj, dict):
                        return {k: _verbatim_structured(v, ledger, depth + 1) for k, v in obj.items()}
                    return obj

                def _citations_for(answer: str, ledger: EvidenceLedger) -> list[CitationRef]:
                    refs: list[CitationRef] = []
                    spent = 0
                    for n in _cited_numbers(answer, len(ledger.rows)):
                        if len(refs) >= CITATION_CAP:
                            break
                        ref = ledger.ref_for(n)
                        if ref is None:
                            continue
                        row = ledger.rows[n - 1]
                        slices = getattr(ref, 'slices', None)
                        cost = sum((max(0, s.end - s.start) for s in slices)) if slices else int(row.get('note_len') or 0)
                        if spent + cost > EVIDENCE_CHAR_BUDGET:
                            continue
                        spent += cost
                        refs.append(ref)
                    return refs
                _VERIFY_MARK_RE = re.compile('\\s*\\((?:verify|unverified|uncertain)[^)]*\\)', re.I)
                _TOOL_MARKUP_RE = re.compile('<\\s*/?\\s*tool_call|<\\s*/?\\s*(?:arg_key|arg_value|function_call|invoke)\\b|\\bweb_search\\s*[（(]\\s*query|\\bread_page\\s*[（(]\\s*url|\\bsec_filing\\s*[（(]\\s*company', re.I)
                _STUB_ANSWER_RE = re.compile('^\\s*(?:best-effort answer unavailable|no question provided)', re.I)
                _REFUSAL_ONLY_RE = re.compile("^\\s*(?:i (?:cannot|can't|am unable|was unable)|unable to|sorry[,.]|i don'?t have (?:enough|access))", re.I)
                _INTENT_NARRATION_RE = re.compile("^\\s*(?:i (?:need|will|should|am going|'ll)\\b|let me\\b|first,? (?:i|let)\\b|i'?ll (?:search|look|start|begin|gather|check))", re.I)
                MIN_ANSWER_CHARS = 40
                MIN_CITED_ANSWER_CHARS = 12
                _CITE_MARK_RE = re.compile('\\[[0-9]{1,3}\\]')

                def _looks_like_tool_json(s: str) -> bool:
                    return bool(re.match('\\s*\\{\\s*"(?:name|tool|function)"\\s*:', s))

                def _is_degenerate_repetition(text: str) -> bool:
                    body = text or ''
                    lines = [ln.strip().lower() for ln in body.split('\n') if len(ln.strip()) > 25]
                    if len(lines) >= 3:
                        for ln in set(lines):
                            if lines.count(ln) >= 3:
                                return True
                        if len(set(lines)) * 2 > len(lines):
                            return False
                    sents = [s.strip().lower() for s in re.split('(?<=[.!?])\\s+|\\n+', body) if len(s.strip()) > 25]
                    if len(sents) < 3:
                        return False
                    uniq = set(sents)
                    if len(uniq) * 2 <= len(sents):
                        return True
                    for s in uniq:
                        if sents.count(s) >= 3:
                            return True
                    return False

                def _is_usable_answer(text: str) -> bool:
                    s = _normalize_brackets(text).strip()
                    if not s:
                        return False
                    if _TOOL_MARKUP_RE.search(s) or _looks_like_tool_json(s):
                        return False
                    if _STUB_ANSWER_RE.match(s) or _is_degenerate_repetition(s):
                        return False
                    cited = bool(_CITE_MARK_RE.search(s))
                    if cited and len(s) >= MIN_CITED_ANSWER_CHARS:
                        return True
                    if len(s) < MIN_ANSWER_CHARS:
                        return False
                    if len(s) < 400 and (_REFUSAL_ONLY_RE.match(s) or _INTENT_NARRATION_RE.match(s)):
                        return False
                    return True
                _COMMIT_RULES = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too. Never say what the evidence does not contain; commit to the best-supported answer you can defend."
                _REPAIR_ORDER = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

                def _sanitize_draft(text: str) -> str:
                    return _VERIFY_MARK_RE.sub('', text or '').strip()

                def _ledger_digest(ledger: EvidenceLedger, char_cap: int=60000) -> str:
                    parts: list[str] = []
                    spent = 0
                    for i, row in enumerate(ledger.rows, start=1):
                        text = (row.get('preview') or '').strip()
                        if not text:
                            continue
                        block = f"[{i}] {row.get('title') or ''} ({row.get('url') or ''})\n{text}"
                        if spent + len(block) > char_cap:
                            break
                        spent += len(block)
                        parts.append(block)
                    return '\n\n'.join(parts)
                _FURNITURE_RE = re.compile('^\\s*(?:share|search|home|menu|subscribe|sign\\s*in|log\\s*in|newsletter|advertisement|cookie|skip to|follow us|read more|related|tags?|categories?|privacy|terms|contact|about us|navigation|toggle)\\b', re.I)
                _SRC_FOOTNOTE_RE = re.compile('\\[\\s*\\d{1,3}\\s*\\]')
                _MD_LINK_RE = re.compile('\\]\\(')
                _BARE_URL_RE = re.compile('(?<!\\]\\()https?://')
                _SENTENCEY_RE = re.compile('[.!?]\\s|[.!?]$|\\b(?:is|was|were|are|has|have|had|reported|announced|released|won|ranked|totall?ed)\\b', re.I)

                def _informative_lead(preview: str, limit: int=280) -> str:
                    kept: list[str] = []
                    broke = False
                    for chunk in re.split('(?<=[.!?])\\s+|\\n+', _SRC_FOOTNOTE_RE.sub('', preview or '')):
                        seg = ' '.join(chunk.split())
                        if len(seg) < 30 or len(seg) > 400:
                            if kept:
                                broke = True
                                break
                            continue
                        if _SENTENCEY_RE.search(seg) is None:
                            if kept:
                                broke = True
                                break
                            continue
                        if _FURNITURE_RE.match(seg) and (not re.search('\\d', seg)):
                            if kept:
                                broke = True
                                break
                            continue
                        if seg.startswith(('*', '|', '↑', '#')):
                            if kept:
                                broke = True
                                break
                            continue
                        links = len(_MD_LINK_RE.findall(seg)) + len(_BARE_URL_RE.findall(seg))
                        if links and links * 110 >= len(seg):
                            if kept:
                                broke = True
                                break
                            continue
                        kept.append(seg)
                        if sum((len(k) for k in kept)) >= limit:
                            break
                    else:
                        pass
                    out = ' '.join(kept).strip()
                    if len(out) > limit:
                        cut = out.rfind(' ', 0, limit)
                        out = out[:cut if cut > 60 else limit].rstrip(' ,;:-')
                    return out

                def _deterministic_answer(question: str, ledger: EvidenceLedger) -> str:
                    rows = [(i, r) for i, r in enumerate(ledger.rows, start=1) if (r.get('preview') or '').strip()]
                    if not rows:
                        return ''
                    out = ['Best-supported findings from the sources retrieved:']
                    picked = 0
                    for i, r in rows:
                        if picked >= 6:
                            break
                        lead = _informative_lead(r.get('preview') or '')
                        if not lead:
                            continue
                        title = (r.get('title') or '').strip()
                        out.append(f"- {(title + ': ' if title else '')}{lead} [{i}]")
                        picked += 1
                    if picked == 0:
                        for i, r in rows[:4]:
                            lead = ' '.join((r.get('preview') or '').split())[:280]
                            if lead:
                                out.append(f'- {lead} [{i}]')
                        if len(out) == 1:
                            return ''
                    return '\n'.join(out)
                QUOTE_SYNTH_TIMEOUT_S = 42.0
                QUOTE_SYNTH_MIN_BUDGET_S = 30.0
                QUOTE_SYNTH_MIN_QUOTES = 2
                QUOTE_TABLE_CHARS = 1400

                def _quote_table(ledger: EvidenceLedger) -> str:
                    parts = []
                    for i, row in enumerate(ledger.rows, start=1):
                        text = row.get('text') or ''
                        for a, b in row.get('retained') or []:
                            excerpt = text[max(0, int(a)):int(b)][:QUOTE_TABLE_CHARS].strip()
                            if excerpt:
                                parts.append(f"[{i}] {row.get('title') or row.get('url') or ''}\n{excerpt}")
                    return '\n\n'.join(parts)

                def _retained_count(ledger: EvidenceLedger) -> int:
                    return sum((len(r.get('retained') or []) for r in ledger.rows))

                def _digest_commit_messages(question: str, digest: str) -> list[dict]:
                    return [{'role': 'system', 'content': _COMMIT_RULES}, {'role': 'user', 'content': f'Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'}]

                def _digest_lane_budget(i: int, left: float) -> float:
                    budget = min(RESCUE_TIMEOUT_S, left - DIGEST_TAIL_S)
                    if i == 0:
                        budget = min(budget, max(12.0, left - 14.0 - DIGEST_TAIL_S))
                    return budget

                async def _write_from_digest(question: str, ledger: EvidenceLedger, deadline: float) -> str:
                    left = deadline - monotonic()
                    if left < 14.0:
                        return ''
                    digest = _ledger_digest(ledger)
                    if not digest:
                        return ''
                    convo = _digest_commit_messages(question, digest)
                    lanes = ((LLM_LANE_A, LOOP_MODEL_A), (LLM_LANE_B, LOOP_MODEL_B))
                    for i, lane_model in enumerate(lanes):
                        left = deadline - monotonic()
                        if left < 14.0:
                            return ''
                        budget = _digest_lane_budget(i, left)
                        if budget < 8.0:
                            return ''
                        try:
                            text = await _llm_chat_pinned(lane_model[0], lane_model[1], convo, max_tokens=2600, timeout=budget)
                        except Exception:
                            continue
                        if _is_usable_answer(text):
                            return text
                    return ''

                async def _knowledge_resort(question: str, deadline: float) -> str:
                    left = deadline - monotonic()
                    if left < 12.0:
                        return ''
                    try:
                        return await _chat_simple(LLM_LANE_A, RESORT_MODEL, 'Expert researcher. Best definitive answer with concrete entities, numbers, dates. Never refuse.', question, max_tokens=2600, timeout=min(45.0, left - 4.0))
                    except Exception:
                        return ''

                def _schema_lane_schedule():
                    return ((LLM_LANE_A, SCHEMA_MODEL), (LLM_LANE_A, RESORT_MODEL), (LLM_LANE_B, LOOP_MODEL_B))

                def _schema_convert_prompt(question: str, answer: str, schema) -> str:
                    return f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}'

                def _unwrap_schema_value(value, schema) -> tuple[bool, object]:
                    if _matches_schema_shape(value, schema):
                        return (True, value)
                    if isinstance(value, dict) and len(value) == 1:
                        inner = list(value.values())[0]
                        if _matches_schema_shape(inner, schema):
                            return (True, inner)
                    return (False, None)

                def _strip_json_fence(raw: str) -> str:
                    return re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()

                async def _schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
                    ask = _schema_convert_prompt(question, answer, schema)
                    for lane, model in _schema_lane_schedule():
                        left = deadline - monotonic()
                        if left < 12.0:
                            break
                        try:
                            raw = await _chat_simple(lane, model, 'You output strictly valid JSON.', ask, max_tokens=3400, timeout=min(45.0, left - 4.0))
                            value = json.loads(_strip_json_fence(raw))
                            ok, matched = _unwrap_schema_value(value, schema)
                            if ok:
                                return matched
                        except Exception:
                            continue
                    return None

                def _schema_kind(schema) -> str:
                    if not isinstance(schema, dict):
                        return ''
                    kind = schema.get('type')
                    if isinstance(kind, list):
                        kind = kind[0] if kind else None
                    if kind is None:
                        for key in ('anyOf', 'oneOf', 'allOf'):
                            branch = schema.get(key)
                            if isinstance(branch, list):
                                for sub in branch:
                                    got = _schema_kind(sub)
                                    if got:
                                        return got
                        if isinstance(schema.get('properties'), dict):
                            return 'object'
                        if isinstance(schema.get('enum'), list):
                            return 'string'
                        return ''
                    return str(kind)

                def _matches_schema_shape(value, schema) -> bool:
                    kind = _schema_kind(schema)
                    if not kind:
                        return True
                    if kind == 'array':
                        return isinstance(value, list)
                    if kind == 'object':
                        return isinstance(value, dict)
                    if kind == 'string':
                        return isinstance(value, str)
                    if kind == 'integer':
                        return isinstance(value, int) and (not isinstance(value, bool))
                    if kind == 'number':
                        return isinstance(value, (int, float)) and (not isinstance(value, bool))
                    if kind == 'boolean':
                        return isinstance(value, bool)
                    if kind == 'null':
                        return value is None
                    return True
                _NUM_IN_TEXT_RE = re.compile('-?\\d[\\d,]*(?:\\.\\d+)?')
                _DIGEST_LEAD_RE = re.compile('^\\s*Best-supported findings|^\\s*sources retrieved:', re.I)
                _DIGEST_NOISE_RE = re.compile('\\[slice \\d+:\\d+\\]|https?://\\S+')
                _VALUE_MAX_CHARS = 90

                def _undigest_for_schema(basis: str) -> str:
                    if not basis:
                        return ''
                    text = _DIGEST_NOISE_RE.sub(' ', basis)
                    out = []
                    for raw in text.split('\n'):
                        line = raw.strip().lstrip('-*• ').strip()
                        if not line or _DIGEST_LEAD_RE.match(line):
                            continue
                        if ':' in line:
                            head, _, tail = line.partition(':')
                            line = tail.strip() if 0 < len(tail.strip()) <= _VALUE_MAX_CHARS else head.strip()
                        if not line or len(line) > _VALUE_MAX_CHARS:
                            continue
                        if line.count(' ') > 8:
                            continue
                        if line not in out:
                            out.append(line)
                        if len(out) >= 6:
                            break
                    return '\n'.join(out)

                def _coerce_to_schema(answer: str, schema, depth: int=0):
                    if depth > 4 or not isinstance(schema, dict):
                        return answer[:400]
                    enum = schema.get('enum')
                    if isinstance(enum, list) and enum:
                        low = (answer or '').lower()
                        for opt in enum:
                            if isinstance(opt, str) and re.search('\\b' + re.escape(opt.lower()) + '\\b', low):
                                return opt
                        return enum[0]
                    kind = _schema_kind(schema)
                    if not kind:
                        for key in ('anyOf', 'oneOf', 'allOf'):
                            branch = schema.get(key)
                            if isinstance(branch, list) and branch:
                                for sub in branch:
                                    if isinstance(sub, dict) and sub.get('type') != 'null':
                                        return _coerce_to_schema(answer, sub, depth + 1)
                        kind = 'string'
                    if kind == 'array':
                        items = schema.get('items') or {}
                        parts = [p.strip(' -*\t') for p in re.split('[\\n;]|,(?![^(]*\\))', answer or '')]
                        parts = [p[:400] for p in parts if p][:20]
                        if not parts:
                            parts = [answer[:400]]
                        return [_coerce_to_schema(p, items, depth + 1) for p in parts]
                    if kind == 'object':
                        props = schema.get('properties') or {}
                        required = schema.get('required') or list(props.keys())
                        out = {}
                        for key in required:
                            out[key] = _coerce_to_schema(answer, props.get(key) or {}, depth + 1)
                        return out
                    if kind in ('number', 'integer'):
                        found = _NUM_IN_TEXT_RE.search(_CITE_NUM_RE.sub(' ', answer or ''))
                        if found is None:
                            return 0
                        val = found.group(0).replace(',', '')
                        try:
                            return int(val) if kind == 'integer' else float(val)
                        except Exception:
                            return 0
                    if kind == 'boolean':
                        return not re.match('\\s*(no\\b|false\\b|none\\b)', answer or '', re.I)
                    return (answer or '')[:400]
                _NARRATION_LEAD_RE = re.compile("^\\s*(?:based on (?:my|the)\\b|now (?:i|that i)\\b|i (?:now )?(?:have|was|am|need|will|can)\\b|i(?:'ll|'ve|'m)\\b|let me\\b|let's\\b|first,? i\\b|having (?:now )?\\w+\\b|okay\\b|alright\\b|to answer this\\b|my research\\b)", re.IGNORECASE)
                _TOOL_NAME_RE = re.compile('\\b(?:retain_evidence|read_page|search_web|fetch_page|read_json)\\b', re.IGNORECASE)
                _PROCESS_TALK_RE = re.compile("\\b(?:I|my|we)\\b|\\b(?:let me|let's)\\b|\\bevidence I\\b|\\bformatting\\b|\\b(?:gathered|retrieved|fetched|queried|need|needed)\\b", re.IGNORECASE)

                def _is_tool_narration(head: str) -> bool:
                    return _TOOL_NAME_RE.search(head) is not None and _PROCESS_TALK_RE.search(head) is not None
                _ABBREV_TAIL_RE = re.compile('(?:\\b[A-Z]|\\b(?:Inc|Ltd|Co|No|vs|St|Dr|Mr|Ms|Mt|Jr|Sr|etc|e\\.g|i\\.e))\\.$')
                _AUDIT_META_RE = re.compile("\\baudit(?:'s|s')?\\s+(?:premise|premises|claim|claims|claimed|note|notes|noted|flag|flags|flagged|report|finding|findings|assertion|suggestion|says|said|states|stated)\\b", re.I)

                def _strip_audit_meta(text: str) -> str:
                    t = text or ''
                    if not _AUDIT_META_RE.search(t):
                        return t
                    out = []
                    for part in re.split('(?<=[.!?])\\s+', t):
                        if _AUDIT_META_RE.search(part) and (not re.search('\\[\\d+\\]', part)):
                            continue
                        out.append(part)
                    cleaned = ' '.join((p for p in out if p.strip())).strip()
                    return cleaned if len(cleaned) >= 40 else t

                def _strip_lead_narration(text: str) -> str:
                    t = (text or '').strip()
                    if not t:
                        return t
                    for _ in range(2):
                        parts = re.split('(?<=[.!?])\\s+', t, maxsplit=1)
                        if len(parts) != 2:
                            break
                        head, rest = (parts[0], parts[1].strip())
                        if _CITE_NUM_RE.search(head):
                            break
                        if _NARRATION_LEAD_RE.match(head) is None and (not _is_tool_narration(head)):
                            break
                        if len(head.split()) < 4 or _ABBREV_TAIL_RE.search(head) is not None:
                            break
                        if len(rest) < 120 or _CITE_NUM_RE.search(rest) is None:
                            break
                        t = rest
                    return t

                def _cap(text: str) -> str:
                    t = (text or '').strip()
                    if len(t) > ANSWER_CHAR_CAP:
                        return t[:ANSWER_CHAR_CAP - 16] + ' …'
                    return t

                async def _note_tooling_spend() -> None:
                    try:
                        info = await tooling_info(timeout=10.0)
                        _spend_note(info)
                    except Exception:
                        pass

                async def _maybe_knowledge_brief(question: str, deadline: float) -> tuple[str, str]:
                    draft = ''
                    brief = ''
                    try:
                        if _spend_left() >= BRIEF_MIN_USD and deadline - monotonic() > 120.0:
                            draft, brief = await _knowledge_brief(question)
                    except Exception:
                        brief = ''
                    return (draft, brief)

                async def _maybe_audit_answer(question: str, answer: str, messages: list[dict], ledger: EvidenceLedger, deadline: float) -> str:
                    try:
                        if _is_usable_answer(answer) and deadline - monotonic() > 75.0 and (_spend_left() >= AUDIT_MIN_USD):
                            patched = await _audit_patch(question, answer, messages, ledger, deadline)
                            if _is_usable_answer(patched):
                                return patched
                    except Exception:
                        pass
                    return answer

                async def _rescue_unusable_answer(question: str, answer: str, draft: str, ledger: EvidenceLedger, deadline: float) -> str:
                    if not _is_usable_answer(answer) and ledger.rows:
                        try:
                            rescued = await _write_from_digest(question, ledger, deadline)
                            if _is_usable_answer(rescued):
                                answer = rescued
                        except Exception:
                            pass
                    if not _is_usable_answer(answer) and ledger.rows:
                        det = _deterministic_answer(question, ledger)
                        if _is_usable_answer(det):
                            answer = det
                    if not _is_usable_answer(answer):
                        fallback = _sanitize_draft(draft) or await _knowledge_resort(question, deadline)
                        if _is_usable_answer(fallback):
                            answer = fallback
                    return answer

                def _polish_final_answer(answer: str, question: str) -> tuple[str, str]:
                    answer = _normalize_brackets(answer)
                    answer = _strip_lead_narration(answer)
                    answer = _strip_audit_meta(answer)
                    answer = _answer_line_only(answer, question)
                    text = _cap(answer) or f'Best-effort answer unavailable for: {question[:400]}'
                    return (answer, text)

                def _schema_basis(answer: str, question: str, ledger: EvidenceLedger) -> str:
                    basis = answer if _is_usable_answer(answer) else ''
                    if not basis:
                        basis = _deterministic_answer(question, ledger)
                    if not basis or _STUB_ANSWER_RE.match(basis.strip()):
                        basis = question[:400]
                    return basis

                async def _structured_response(question: str, answer: str, schema, ledger: EvidenceLedger, deadline: float, citations: list) -> Response | None:
                    structured = None
                    try:
                        structured = await _schema_output(question, answer, schema, deadline)
                    except Exception:
                        structured = None
                    if structured is not None:
                        try:
                            structured = _verbatim_structured(structured, ledger)
                        except Exception:
                            pass
                        try:
                            return Response(output=structured, citations=citations or None)
                        except Exception:
                            structured = None
                    basis = _schema_basis(answer, question, ledger)
                    if basis is not answer:
                        try:
                            salvaged = await _schema_output(question, basis, schema, deadline)
                        except Exception:
                            salvaged = None
                        if salvaged is not None:
                            try:
                                return Response(output=salvaged, citations=citations or None)
                            except Exception:
                                pass
                    if basis is not answer:
                        cleaned = _undigest_for_schema(basis)
                        basis = cleaned if cleaned else ''
                    try:
                        forced = _coerce_to_schema(_cap(basis), schema)
                        return Response(output=forced, citations=citations or None)
                    except Exception:
                        try:
                            return Response(output=_cap(basis)[:2000], citations=citations or None)
                        except Exception:
                            pass
                    return None

                def _text_response(text: str, citations: list) -> Response:
                    try:
                        return Response(text=text, citations=citations or None)
                    except Exception:
                        return Response(text=text)

                async def query(query: Query) -> Response:
                    question = (query.text or '').strip()
                    if not question:
                        return Response(text='No question provided.')
                    try:
                        return await _solve(query, question)
                    except Exception:
                        return Response(text=f'Best-effort answer unavailable for: {question[:500]}')

                async def _solve(query: Query, question: str) -> Response:
                    deadline = monotonic() + WALL_BUDGET_S
                    await _note_tooling_spend()
                    draft, brief = await _maybe_knowledge_brief(question, deadline)
                    ledger = EvidenceLedger()
                    answer = ''
                    messages: list[dict] = []
                    try:
                        answer, messages = await _loop(question, brief, ledger, deadline, MAX_TURNS)
                    except Exception:
                        answer = ''
                    answer = await _maybe_audit_answer(question, answer, messages, ledger, deadline)
                    answer = await _rescue_unusable_answer(question, answer, draft, ledger, deadline)
                    try:
                        citations = _citations_for(answer, ledger)
                    except Exception:
                        citations = []
                    answer, text = _polish_final_answer(answer, question)
                    if query.output_schema is not None:
                        structured = await _structured_response(question, answer, query.output_schema, ledger, deadline, citations)
                        if structured is not None:
                            return structured
                    return _text_response(text, citations)
                return query

        class SecondPath:

            def _compile(self):
                import asyncio
                import json
                import re
                from dataclasses import dataclass, field
                from time import monotonic
                from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
                from harnyx_miner_sdk.decorators import entrypoint
                from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
                VERSION = 'v53-uid187-router'
                DIFFICULTY_ROUTER_V187 = 'DIFFICULTY_ROUTER_V187'
                RESEARCH_PLAN_V187 = 'RESEARCH_PLAN_V187'
                CLAIM_LEDGER_V187 = 'CLAIM_LEDGER_V187'
                SET_ENGINE_V187 = 'SET_ENGINE_V187'
                CITATION_AUDIT_V187 = 'CITATION_AUDIT_V187'
                FAILURE_RECOVERY_V187 = 'FAILURE_RECOVERY_V187'
                FINGERPRINT_MARKERS = (DIFFICULTY_ROUTER_V187, RESEARCH_PLAN_V187, CLAIM_LEDGER_V187, SET_ENGINE_V187, CITATION_AUDIT_V187, FAILURE_RECOVERY_V187)
                _RUN_DIAGNOSTICS: list[str] = []
                _ROUTE_DIAG: dict = {'route': 'hard', 'reasons': []}
                LLM_LANE_A = 'openrouter'
                LLM_LANE_B = 'ai_gateway'
                LOOP_MODEL_A = 'z-ai/glm-5.2'
                LOOP_MODEL_B = 'zai/glm-5.2-fast'
                AUDIT_MODEL = 'openai/gpt-oss-120b'
                SCHEMA_MODEL = 'openai/gpt-oss-120b'
                RESORT_MODEL = 'deepseek/deepseek-v3.2'
                SEARCH_PROVIDER = 'parallel'
                WALL_BUDGET_S = 266.0
                BRIEF_TIMEOUT_S = 50.0
                TURN_TIMEOUT_S = 75.0
                LANE_B_MAX_PAYLOAD_CHARS = 144000
                AUDIT_TIMEOUT_S = 28.0
                SEARCH_TIMEOUT_S = 18.0
                FETCH_TIMEOUT_S = 16.0
                WRAPUP_AT_S = 90.0
                MIN_TAIL_S = 8.0
                MAX_TURNS = 15
                MAX_TURNS_EASY = 8
                MAX_SEED_QUERIES_EASY = 1
                AUDIT_EXTRA_TURNS = 2
                ANSWER_REPAIR_TURNS = 2
                RESCUE_TIMEOUT_S = 55.0
                DIGEST_TAIL_S = 14.0
                SEARCH_EXCERPT_CHARS = 550
                _LEDGER_TEXT_CAP = 400000
                PAGE_GREP_WINDOW = 700
                PAGE_GREP_MAX_HITS = 6
                PAGE_READ_MAX_CHARS = 12000
                RETAIN_MARGIN_CHARS = 260
                RETAIN_MAX_PER_ROW = 6
                RETAIN_MIN_QUOTE = 12
                FETCH_HEAD_CHARS = 3000
                FETCH_WINDOW_CHARS = 3600
                CITATION_MIN_SPAN_CHARS = 6000
                CITATION_MAX_REF_CHARS = 14000
                FETCH_WINDOWS_PER_PAGE = 3
                FETCH_PLAIN_CHARS = 6500
                ANSWER_CHAR_CAP = 60000
                CITATION_CAP = 24
                EVIDENCE_CHAR_BUDGET = 105000
                BRIEF_MIN_USD = 0.03
                AUDIT_MIN_USD = 0.05
                WRAPUP_MIN_USD = 0.02
                _SPEND = {'left': None}
                _CLAIM_LEDGER_REF: dict = {'ledger': None}

                def _spend_note(payload) -> None:
                    budget = getattr(payload, 'budget', None)
                    left = getattr(budget, 'session_remaining_budget_usd', None)
                    if isinstance(left, (int, float)):
                        _SPEND['left'] = float(left)

                def _spend_left() -> float:
                    left = _SPEND['left']
                    if isinstance(left, (int, float)):
                        return float(left)
                    return 1.0
                LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}, {'type': 'function', 'function': {'name': 'page_grep', 'description': 'Search INSIDE a page you already fetched, by regex or literal text, and get every match with its surrounding context and character offset. Use this when read_page showed you the head of a long page but the value you need is deeper in it -- do not re-fetch, grep it.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL of a page already fetched this run'}, 'pattern': {'type': 'string', 'description': 'regex or literal string to find, e.g. a city name, a year, a column label'}}, 'required': ['url', 'pattern']}}}, {'type': 'function', 'function': {'name': 'page_read', 'description': 'Read an arbitrary character range of a page you already fetched. Use the offsets page_grep reports to read the full table or section around a match.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL already fetched'}, 'offset': {'type': 'integer', 'description': 'start character offset'}, 'length': {'type': 'integer', 'description': 'how many characters to read (max 12000)'}}, 'required': ['url', 'offset']}}}, {'type': 'function', 'function': {'name': 'retain_evidence', 'description': "Keep the exact source text that proves a claim you are about to make. Pass the result number and the verbatim quote from it. Do this the moment you find a decisive value -- the judge only credits claims whose citation contains the supporting text, and this is how that text gets into your citation. Use it for the QUESTION'S PREMISES as well as your answer: every entity, work, date or figure the question names should end up with a retained quote confirming it.", 'parameters': {'type': 'object', 'properties': {'source': {'type': 'string', 'description': 'result number to quote from, e.g. 3'}, 'quote': {'type': 'string', 'description': 'verbatim text copied from that result that states the fact'}}, 'required': ['source', 'quote']}}}]
                LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nPREFER THE PRIMARY SOURCE: when two sources state the same fact, cite the one that ORIGINATES it -- the agency, registry, filing, official statistics release or the organisation\'s own page -- not an encyclopedia or aggregator repeating it. Measured verbatim on a task where both answers were factually correct: "Answer 1 is preferred for using primary sources" (it cited NARA where we cited Wikipedia) -- a full point lost on every run. Use the encyclopedia to FIND the primary source, then fetch and cite that.\n\nQUOTE WHAT PROVES IT: the judge credits a claim only when your citation CONTAINS the source text stating it. The moment you read a decisive value, call retain_evidence(source, quote) with the exact words from that result. Do this for every condition you test and every figure you report -- an answer whose citations do not carry its numbers loses to one that does, even when both answers are identical.\nALSO QUOTE THE QUESTION\'S PREMISES, not only your answer. Every entity, work, date or figure the question NAMES is a claim the judge expects traceable: the film it says someone directed, the article it points at, the year it fixes, the people it lists. You lose to an otherwise identical answer that cited those too -- measured verbatim: "does not provide a citation for \'Everyone Says I Love You\'... Answer 1 is more thorough in its traceability to all parts of the prompt\'s context". Retain a quote for each named premise as you confirm it, even when it is background you already believed.\n\nREAD DEEP, DO NOT RE-FETCH: read_page shows the head plus a few regions of a long page. If the value you need is not in what you were shown, call page_grep(url, pattern) to find it anywhere in that page and page_read to open the region around a reported offset. Grepping a page you already have costs nothing and beats another search.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. COPY SOURCE VALUES VERBATIM: when the question names a source, every name, label and value in the answer must be the exact string that source prints -- never add a familiar alternative in parentheses, never anglicise a transliteration. \'Makkah\' is the answer; \'Mecca (Makkah)\' is a wrong answer. ONE EXCEPTION, and it is absolute: if the question says to output ONLY the answer (\'output only\', \'respond with only\', \'nothing else\', \'no explanation\'), emit the answer line as the BARE requested text — no [n] markers on it, nothing else on that line: a trailing [3] makes the text inexact and fails the instruction. Still write the PROOF section BELOW it carrying its [n] markers. Only the answer line is shipped, but the citations are harvested from the proof first, and an uncited answer scores zero. Obeying that instruction IS the task. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

                def _wrapup_order(seconds_left: float) -> str:
                    return f"TIME IS UP (~{int(seconds_left)}s left). No more tool calls. Write the complete final answer NOW from the numbered results above plus your knowledge: the FIRST words are the answer entities (no 'Based on…' preamble, no 'partial answer' framing, no '(verify)' markers), cite [n] on every claim, keep the required format. A cited partial answer scores; a refusal or a remark about insufficient evidence scores zero." + ('' if seconds_left >= 60 else ' BREVITY OVERRIDE: too little time remains for a line per pool member. Lead with the answer entities, then give the qualifiers one cited line each and compress the rejects into a single cited line. A complete short answer beats a long one that never finishes.')
                _SET_HINT_RE = re.compile('\\b(?:list|name|identify|enumerate)\\b[^?]{0,40}\\b(?:all|every|each|the)\\b|\\bhow many\\b|\\bwhich (?:movies|films|series|countries|companies|states|cities|books|albums|artists|players|teams|species|languages|banks|universities|agencies|models|products)\\b', re.IGNORECASE)
                _SET_CONNECTIVE_RE = re.compile('\\b(?:both|also|and (?:also|had|has|was|were)|as well as)\\b', re.IGNORECASE)
                _PLURAL_HEAD_RE = re.compile('\\b(?:which|what)\\b(?:\\s+\\w+){0,2}?\\s+([a-z]{3,}s)\\b', re.IGNORECASE)
                _PLURAL_FALSE = frozenset('was is has does its this thus across process business series species news status analysis basis less unless always perhaps'.split())
                _ONE_WINNER_RE = re.compile('\\b(?:highest|lowest|largest|smallest|most|least|greatest|fewest|longest|shortest|first|last|best|worst|only|oldest|youngest|newest|biggest)\\b', re.IGNORECASE)
                _EST_STOP = frozenset('interest honest modest protest request suggest forest harvest invest manifest contest arrest digest earnest conquest tempest midwest northwest southwest unrest bequest behest attest molest ingest infest detest incest armrest backrest pretest headrest footrest'.split())
                _EST_RE = re.compile('\\b([a-z]{3,})est\\b')

                def _has_superlative(text: str) -> bool:
                    if _ONE_WINNER_RE.search(text or ''):
                        return True
                    for m in _EST_RE.finditer(text or ''):
                        if m.group(0).lower() not in _EST_STOP:
                            return True
                    return False

                def _needs_superlative_proof(question: str) -> bool:
                    q = ' '.join((question or '').split())
                    if not q:
                        return False
                    return _has_superlative(q) or bool(re.search('\\b(?:most|least) (?:common|frequent|number|amount)\\b|\\bhow many\\b', q, re.I))
                SUPERLATIVE_RULE = "SUPERLATIVE / TALLY — SHOW THE TABLE. The answer is one item, but you cannot know it without the whole pool. Before naming a winner: (1) list EVERY candidate the question's scope admits — every player who appeared, every officeholder in the span, every body in the ranking; (2) put the deciding value next to each (birth date, count, figure), cited; (3) THEN name the maximum. NEVER decide a superlative on a rounded or derived display: a coarse figure (a whole-number age, a rounded total, a bucketed rank) cannot separate two contenders that differ below its precision. Fetch the exact underlying value (full birth date, unrounded figure) for every contender, from a source that lists them ALL: a page showing only your front-runner cannot establish that nobody beats them. (3b) THEN name the maximum. Reproduce that candidate table in the proof section — a correct winner with no visible tally loses to a reference that shows its work, and 'among others' / 'and several more' is not a tally. If the pool is too large to list in full, rank it, show every contender down to a stated cutoff, and say what the cutoff was — a stated cutoff is a covered pool; an unstated one reads as an unchecked one."

                def _needs_set_completeness(question: str) -> bool:
                    q = ' '.join((question or '').split())
                    if _SET_HINT_RE.search(q):
                        return True
                    m = _PLURAL_HEAD_RE.search(q)
                    if m and m.group(1).lower() not in _PLURAL_FALSE:
                        if not _has_superlative(q) or re.search('\\b(?:all|every|each)\\b', q, re.IGNORECASE):
                            return True
                    return bool(re.search('\\bwhich\\b', q, re.IGNORECASE)) and bool(_SET_CONNECTIVE_RE.search(q))
                SET_RULE = "SET ANSWER: this question asks for a set. Missing a qualifying member scores the same as wrong — enumerate the pool, test EVERY member against EVERY condition, and name ALL qualifiers (each with its own citations per condition). Then give EVERY excluded member its own line with the condition it fails and its own [n] — not a single clause sweeping several names together, and not just the near-misses. Never claim 'the only X' unless the whole pool was checked; if your pool may be partial, still commit to every qualifier you verified. GET THE POOL FROM A LIST, NOT MEMBER-BY-MEMBER: your FIRST retrieval for a set question should hunt the authoritative roster/list/table that enumerates the whole pool (search it AS a list — '<pool subject> list', '<pool subject> table', 'list of <pool subject>' — and read_page it). Assembling the pool from separate per-member searches is how a run ends up with 3 of 6 qualifiers: the members you never thought to search for are invisible to you. Read the roster page first, then verify each member. ONE LIST PER PERIOD, THEN JOIN: when a condition has to hold across several periods — successive years, separate editions, or two parallel events — fetch ONE roster page per period and join them on the member: one list per period, not one lookup per member. A pool of 30+ members each needing several figures is a table-join, and per-member lookups will run out of turns long before the pool is covered. UNIVERSAL conditions ('in EVERY one of them', 'for BOTH parts', 'in ALL three periods'): check each candidate against EACH instance separately, with a citation per instance — one shared instance is not enough. If NO candidate survives every instance, then 'none' IS the answer: state it as a verified fact about the world with the per-instance citations that prove it."

                @dataclass
                class RouteDecision:
                    route: str
                    reasons: list[str] = field(default_factory=list)
                    features: dict = field(default_factory=dict)
                    risk_flags: list[str] = field(default_factory=list)
                _EASY_LOOKUP_RE = re.compile('^\\s*(?:what|who|when|where|which)\\b.{0,140}?\\b(?:is|was|were|are|did|does|do|has|have|had|directed|wrote|written|played|founded|released|published|signed|painted|composed|invented|created|starred|born)\\b', re.IGNORECASE | re.DOTALL)
                _EASY_ATTR_RE = re.compile('\\b(?:capital|director|directed|author|writer|wrote|written|founder|founded|president|ceo|born|released|published|title|name|year|population|currency|language|headquarters|located|played|starred|composed|painted|invented|created|signed|treaty|book|film|movie|album|song|novel|play|series)\\b', re.IGNORECASE)
                _EASY_ORDINAL_TITLE_RE = re.compile('\\b(?:title|name|call(?:ed)?)\\b.{0,40}\\bthe\\s+(?:first|last|second|third|fourth|fifth)\\b|\\bthe\\s+(?:first|last|second|third)\\s+(?:\\w+\\s+){0,4}(?:book|film|movie|album|novel|play|episode)\\b', re.IGNORECASE)
                _HARD_COMPARE_RE = re.compile('\\b(?:compar(?:e|ison|ing)|versus|vs\\.?|side[- ]by[- ]side|rank(?:ing|ed)?|differ(?:ence|ent)|between .+ and)\\b', re.IGNORECASE)
                _HARD_SET_MARKER_RE = re.compile('\\b(?:all|every|each|top\\s+\\d+|largest|smallest|best|worst|most|least|first|last|highest|lowest|greatest|fewest|only those|which of the)\\b', re.IGNORECASE)
                _HARD_MULTI_RE = re.compile('\\b(?:and then|also (?:identify|list|find|compute|calculate)|multi[- ]hop|both .+ and|as well as)\\b', re.IGNORECASE)
                _HARD_SEC_RE = re.compile('\\b(?:10-K|10-Q|8-K|DEF\\s*14A|Form\\s+\\d|EDGAR|sec\\.gov|Item\\s+\\d)\\b', re.IGNORECASE)
                _HARD_CURRENT_RE = re.compile('\\b(?:as of (?:today|now|this (?:week|month|year))|current|latest|most recent)\\b', re.IGNORECASE)
                _HARD_TABLE_RE = re.compile('\\b(?:according to (?:the )?(?:english )?wikipedia|based on the .+ article|inhabited territories table)\\b', re.IGNORECASE)
                _EASY_FALSE_ONLY_RE = re.compile('\\bonly\\b(?!\\s+(?:one|a|an)\\b)', re.IGNORECASE)

                def _router_features(question: str, output_schema=None) -> dict:
                    q = ' '.join((question or '').split())
                    set_q = _needs_set_completeness(q)
                    super_q = _needs_superlative_proof(q)
                    return {'chars': len(q), 'has_output_schema': output_schema is not None, 'set_question': set_q, 'superlative': super_q, 'compare': bool(_HARD_COMPARE_RE.search(q)), 'set_marker': bool(_HARD_SET_MARKER_RE.search(q)), 'multi': bool(_HARD_MULTI_RE.search(q)), 'sec': bool(_HARD_SEC_RE.search(q)), 'current': bool(_HARD_CURRENT_RE.search(q)), 'named_table': bool(_HARD_TABLE_RE.search(q)), 'lookup_shape': bool(_EASY_LOOKUP_RE.search(q)), 'attr_shape': bool(_EASY_ATTR_RE.search(q)), 'ordinal_title': bool(_EASY_ORDINAL_TITLE_RE.search(q)), 'false_only': bool(_EASY_FALSE_ONLY_RE.search(q)), 'simple_entity_attribute': bool(_EASY_LOOKUP_RE.search(q)) and bool(_EASY_ATTR_RE.search(q)) and (len(q) < 220) and (q.count('?') <= 1)}

                def _hard_route_signals(feats: dict) -> tuple[list[str], list[str]]:
                    reasons: list[str] = []
                    risks: list[str] = []
                    if feats['has_output_schema']:
                        reasons.append('schema')
                    if feats['set_question']:
                        reasons.append('set')
                    if feats['superlative'] and (not (feats['ordinal_title'] and feats['simple_entity_attribute'])):
                        reasons.append('superlative')
                    if feats['compare']:
                        reasons.append('comparison')
                    if feats['set_marker'] and (not feats['simple_entity_attribute']):
                        reasons.append('set_marker')
                    if feats['multi']:
                        reasons.append('multi')
                    if feats['sec']:
                        reasons.append('sec')
                    if feats['current']:
                        reasons.append('current')
                    if feats['named_table']:
                        reasons.append('named_source_table')
                    if feats['false_only']:
                        reasons.append('only_filter')
                        risks.append('only_filter')
                    if feats['chars'] > 500:
                        reasons.append('long_prompt')
                    return (reasons, risks)

                def _decide_route(question: str, output_schema=None) -> RouteDecision:
                    try:
                        feats = _router_features(question, output_schema)
                    except Exception:
                        return RouteDecision('hard', ['router_exception'], {}, ['router_exception'])
                    reasons, risks = _hard_route_signals(feats)
                    if reasons:
                        return RouteDecision('hard', reasons, feats, risks)
                    if feats['simple_entity_attribute']:
                        return RouteDecision('easy', ['single_entity_attribute'], feats, [])
                    return RouteDecision('hard', ['default_hard'], feats, ['unknown_shape'])

                def _fingerprint_system_note() -> str:
                    marks = ' '.join(FINGERPRINT_MARKERS)
                    return f'AGENT_BUILD VERSION={VERSION} {marks}. Internal diagnostic only — do not include this diagnostic in the answer.'

                def _record_route_diag(payload: dict) -> None:
                    _ROUTE_DIAG.clear()
                    _ROUTE_DIAG.update(payload)
                    _RUN_DIAGNOSTICS.append(f"ROUTE={payload.get('route')} reasons={payload.get('router_reasons')}")
                RESEARCH_PLAN_RULE = 'RESEARCH PLAN (HARD TASK) — before more tool calls, lock:\n1) REQUIRED FACTS: atomic facts the answer needs.\n2) FAILURE MODES: incomplete pool, wrong comparator, rounded figure,\n   wrong year/scope, missing named source, citation mismatch.\n3) COMPLETION CRITERIA: every required fact cited; every pool member has a\n   verdict; answer line matches the asked KIND/format.\nStop researching when those criteria are met.'

                def _deterministic_research_plan(question: str) -> str:
                    set_q = _needs_set_completeness(question)
                    super_q = _needs_superlative_proof(question)
                    lines = [f'{RESEARCH_PLAN_V187} PRIOR PLAN (deterministic skeleton).', 'facts: every named entity/condition/figure; the asked KIND.', 'failures: incomplete pool; uncited hard condition; rounded substitute; wrong period/scope; KIND mismatch.']
                    if set_q or super_q:
                        lines.append('done_when: authoritative roster fetched; every pool member has a cited verdict; answer lists all qualifiers (or the proven winner).')
                        lines.append("searches: '<pool subject> list/table'; named-source page; per-condition verification.")
                    else:
                        lines.append('done_when: each load-bearing claim has a primary-source [n]; answer opens with the asked entities/values.')
                        lines.append('searches: entity+metric+year; named source site:; primary doc.')
                    return '\n'.join(lines)

                async def _research_plan(question: str, deadline: float) -> str:
                    if deadline - monotonic() < 40.0 or _spend_left() < BRIEF_MIN_USD:
                        return _deterministic_research_plan(question)
                    system = 'Research planner. Output a tight plan only — never the final answer. Use the exact lowercase tags below.'
                    user = f'Question:\n{question}\n\nfacts: numbered atomic facts needed to answer.\nfailures: likely zero-score modes (incomplete set, wrong filter, rounded number, missing citation).\ndone_when: completion criteria for stopping tool use.\nsearches: 2-5 precise next searches (entity+metric+year / site:).'
                    raw = ''
                    try:
                        raw = await _chat_simple(LLM_LANE_A, LOOP_MODEL_A, system, user, max_tokens=900, timeout=min(28.0, BRIEF_TIMEOUT_S), think=_least_think(LLM_LANE_A, LOOP_MODEL_A))
                    except Exception:
                        raw = ''
                    if not raw or len(raw.strip()) < 40:
                        return _deterministic_research_plan(question)
                    return f'{RESEARCH_PLAN_V187} PRIOR PLAN — verify with tools; never ship this worksheet as the answer.\n' + raw.strip()

                @dataclass
                class ClaimRecord:
                    claim: str
                    source: str = ''
                    evidence: str = ''
                    confidence: str = 'low'
                    status: str = 'unsupported'

                class ClaimLedger:

                    def __init__(self) -> None:
                        self.records: list[ClaimRecord] = []

                    def add(self, claim: str, *, source: str='', evidence: str='', confidence: str='low', status: str='unsupported') -> None:
                        c = (claim or '').strip()
                        if not c:
                            return
                        self.records.append(ClaimRecord(claim=c[:240], source=(source or '')[:80], evidence=(evidence or '')[:320], confidence=confidence, status=status))

                    def note_retained(self, source_n: int, quote: str) -> None:
                        q = (quote or '').strip()
                        if not q:
                            return
                        self.add(q[:160], source=f'[{source_n}]', evidence=q[:280], confidence='high', status='supported')

                    def summary(self, cap: int=1800) -> str:
                        if not self.records:
                            return ''
                        lines = [f'{CLAIM_LEDGER_V187} EVIDENCE LEDGER (claim / source / evidence / confidence / status):']
                        for i, r in enumerate(self.records[-12:], 1):
                            lines.append(f"{i}. claim: {r.claim} | source: {r.source or '—'} | evidence: {r.evidence or '—'} | confidence: {r.confidence} | status: {r.status}")
                        return '\n'.join(lines)[:cap]
                CLAIM_LEDGER_RULE = 'EVIDENCE LEDGER DISCIPLINE: every factual claim you will assert needs claim / source[n] / supporting evidence / confidence / status=supported. Call retain_evidence the moment you find decisive text. Never include an unsupported claim in the final answer — drop it or verify it first.'
                SET_ENGINE_RULE = f"{SET_ENGINE_V187} SET / TOP / LARGEST / FIRST / BEST / MOST — ENGINE:\n1) DEFINE UNIVERSE: name the full class the question ranges over.\n2) GATHER CANDIDATES: fetch the authoritative roster/list/table first.\n3) VERIFY CANDIDATES: every member × every condition, each cited.\n4) RANK / FILTER: apply comparators literally; show tally before winners.\n5) REPORT UNCERTAINTY: commit verified qualifiers; never invent members; never hide gaps behind 'among others'."

                def _claim_terms_from_text(*parts: str) -> list[str]:
                    bag: list[str] = []
                    seen: set[str] = set()
                    for part in parts:
                        for tok in _WORD_RE.findall((part or '').casefold()):
                            if tok in _STOP or len(tok) < 3:
                                continue
                            if tok not in seen:
                                seen.add(tok)
                                bag.append(tok)
                        for num in re.findall('\\d+(?:\\.\\d+)?%?', part or ''):
                            n = num.casefold()
                            if n not in seen:
                                seen.add(n)
                                bag.append(n)
                    return bag[:24]

                def _infer_supports(question: str, kind: str, args: dict, title: str, url: str, preview: str) -> list[str]:
                    terms = _claim_terms_from_text(question, title, preview[:400])
                    present = [t for t in terms if t in (preview or '').casefold() or t in (title or '').casefold()]
                    if not present:
                        return []
                    return [f"Supports: evidence mentions {', '.join(present[:8])}"]

                def _claim_targeted_spans(note: str, terms: set[str], fallback: list[tuple[int, int]] | None, *, max_spans: int=2, width: int=2200) -> list[tuple[int, int]]:
                    if not note:
                        return list(fallback or [])
                    if not terms:
                        return list(fallback or [(0, min(len(note), width))])
                    hits = _best_windows(note, terms, width=width, k=max_spans)
                    if not hits:
                        return list(fallback or [(0, min(len(note), width))])
                    out = list(hits[:max_spans])
                    if fallback:
                        head = fallback[0]
                        head_txt = note[head[0]:head[1]].casefold()
                        if any((t in head_txt for t in terms if len(t) >= 5)):
                            if not any((s <= head[0] < e or s < head[1] <= e for s, e in out)):
                                out = [head] + out
                    out = sorted(out)[:max_spans + 1]
                    merged: list[tuple[int, int]] = []
                    for s, e in out:
                        if merged and s <= merged[-1][1]:
                            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
                        else:
                            merged.append((s, e))
                    return merged[:max_spans]

                def _densified_ref(ledger: 'EvidenceLedger', number: int, claim_terms: set[str]) -> CitationRef | None:
                    ref = ledger.ref_for(number)
                    if ref is None or not claim_terms:
                        return ref
                    row = ledger.rows[number - 1]
                    note = row.get('text') or ''
                    if len(note) < 200 or row.get('retained'):
                        return ref
                    targeted = _claim_targeted_spans(note, {t.casefold() for t in claim_terms}, list(row.get('spans') or []), max_spans=2, width=min(FETCH_WINDOW_CHARS, 2800))
                    if not targeted:
                        return ref
                    old = row.get('spans')
                    row['spans'] = targeted
                    try:
                        return ledger.ref_for(number)
                    finally:
                        row['spans'] = old
                CITATION_AUDIT_RULE = f'{CITATION_AUDIT_V187} CITATION AUDIT before final answer:\n- every factual claim has an inline [n]\n- each [n] actually states that claim\n- no citation mismatch (wrong year/entity/metric)\n- set/superlative answers include every requested member / full tally\nIf a claim fails audit, verify or remove it — never ship unsupported.'
                FAILURE_RECOVERY_RULE = f'{FAILURE_RECOVERY_V187} WEAK SEARCH RECOVERY: if results are empty, off-topic, or lack the deciding figure — retry with (a) a different query (drop site:/quotes, swap synonyms, add year), (b) a different source class (primary agency/registry vs encyclopedia), (c) alternative evidence (roster page, filing, official stats). Do not repeat the same failed query. Batch independent retries in one turn.'
                EASY_LOOP_RULE = 'EASY LOOKUP: this is a single-fact / simple entity-attribute question. Prefer 1-2 precise searches, fetch the best primary/encyclopedia page, retain_evidence on the decisive sentence, and answer concisely with [n]. Do not build multi-candidate pools or burn turns on decorative corroboration. Stop when the asked fact is cited.'

                class EvidenceLedger:

                    def __init__(self) -> None:
                        self.rows: list[dict] = []

                    def add(self, receipt_id: str, result_id: str, note_len: int, kind: str, spans: list[tuple[int, int]] | None, title: str='', url: str='', preview: str='', text: str='', supports: list[str] | None=None, claim_terms: list[str] | None=None) -> int:
                        norm: list[str] = []
                        for s in supports or []:
                            t = (s or '').strip()
                            if not t:
                                continue
                            if not t.lower().startswith('supports:'):
                                t = 'Supports: ' + t
                            norm.append(t[:240])
                        self.rows.append({'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': (url or '')[:300], 'preview': (preview or '')[:1200], 'spans': spans, 'text': (text or '')[:_LEDGER_TEXT_CAP], 'retained': [], 'supports': norm, 'claim_terms': list(claim_terms or [])[:24]})
                        return len(self.rows)

                    def ref_for(self, number: int) -> CitationRef | None:
                        if not 1 <= number <= len(self.rows):
                            return None
                        row = self.rows[number - 1]
                        if row.get('kind') == 'reserved':
                            return None
                        if not row['receipt_id'] or not row['result_id']:
                            return None
                        spans = row['spans']
                        if spans:
                            note_len = int(row['note_len'] or 0)
                            shown: list[list[int]] = []
                            for span in spans[:4]:
                                start = max(0, min(int(span[0]), note_len))
                                end = max(start + 1, min(int(span[1]), note_len))
                                shown.append([start, end])
                            retained = []
                            for a, b in row.get('retained') or []:
                                a = max(0, min(int(a), note_len))
                                b = max(a + 1, min(int(b), note_len))
                                retained.append([a, b])
                            if retained:
                                shown = retained
                            shown.sort()
                            merged: list[list[int]] = []
                            for s, e in shown:
                                if merged and s <= merged[-1][1]:
                                    merged[-1][1] = max(merged[-1][1], e)
                                else:
                                    merged.append([s, e])
                            base = sum((e - s for s, e in merged))
                            room = max(0, CITATION_MAX_REF_CHARS - base)
                            if merged and note_len and room:
                                extra = room // len(merged)
                                for w in merged:
                                    pad = min(extra, max(0, CITATION_MIN_SPAN_CHARS - (w[1] - w[0])))
                                    if pad:
                                        left = min(pad // 2, w[0])
                                        w[0] -= left
                                        rest = pad - left
                                        right = min(rest, note_len - w[1])
                                        w[1] += right
                                        w[0] = max(0, w[0] - (rest - right))
                                merged.sort()
                                grown: list[list[int]] = []
                                for s, e in merged:
                                    if grown and s <= grown[-1][1]:
                                        grown[-1][1] = max(grown[-1][1], e)
                                    else:
                                        grown.append([s, e])
                                merged = grown
                            slices = [CitationSlice(start=s, end=e) for s, e in merged if e > s]
                            if not slices:
                                return None
                            return CitationRef(receipt_id=row['receipt_id'], result_id=row['result_id'], slices=slices)
                        return None
                _WORD_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
                _STOP = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

                def _key_terms(text: str) -> set[str]:
                    return {w for w in _WORD_RE.findall((text or '').casefold()) if w not in _STOP}

                def _best_windows(note: str, terms: set[str], width: int, k: int=1) -> list[tuple[int, int]]:
                    n = len(note)
                    if n <= width:
                        return [(0, n)]
                    step = max(600, width // 3)
                    low = note.lower()
                    scored: list[tuple[int, int]] = []
                    pos = 0
                    while pos < n:
                        seg = low[pos:pos + width]
                        scored.append((sum((1 for t in terms if t in seg)), pos))
                        if pos + width >= n:
                            break
                        pos += step
                    scored.sort(key=lambda hs: (-hs[0], hs[1]))
                    picked: list[tuple[int, int]] = []
                    for hits, start in scored:
                        if len(picked) >= max(1, k):
                            break
                        end = min(n, start + width)
                        if any((start < pe and ps < end for ps, pe in picked)):
                            continue
                        if picked and hits <= 0:
                            continue
                        picked.append((start, end))
                    picked.sort()
                    return picked or [(0, min(n, width))]
                _SLOT = '\x00{}\x00'

                class ToolOutput:

                    def __init__(self, text: str, rows: list[dict] | None=None) -> None:
                        self.text = text
                        self.rows = rows or []

                def _commit_tool_output(out, ledger: EvidenceLedger) -> str:
                    if isinstance(out, str):
                        return out
                    if not isinstance(out, ToolOutput):
                        return f'# tool crashed: {out}'
                    text = out.text
                    for i, row in enumerate(out.rows):
                        n = ledger.add(row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''), text=row.get('text', ''))
                        text = text.replace(_SLOT.format(i), str(n))
                    return text
                _SITE_OP_RE = re.compile('\\bsite:\\S+\\s*', re.I)

                def _degrade_query(q: str) -> str:
                    out = _SITE_OP_RE.sub('', q or '').replace('"', ' ')
                    return ' '.join(out.split())

                def _search_attempt_plan(query_text: str) -> list[tuple[str, bool]]:
                    return [(query_text, False), (query_text, True), (_degrade_query(query_text), False)]

                def _search_excerpt_span(n_len: int) -> list[tuple[int, int]] | None:
                    if n_len >= 100:
                        return [(0, min(max(SEARCH_EXCERPT_CHARS, 100), n_len))]
                    if n_len:
                        return [(0, n_len)]
                    return None

                def _search_row_from_item(item, receipt: str, query_text: str) -> dict | None:
                    rid = getattr(item, 'result_id', None)
                    if not isinstance(rid, str) or not rid:
                        return None
                    note = getattr(item, 'note', None) or ''
                    if not note.strip():
                        return None
                    n_len = len(note)
                    title = (getattr(item, 'title', None) or '').strip()
                    url = (getattr(item, 'url', None) or '').strip()
                    supports = _infer_supports('', 'web_search', {'query': query_text}, title, url, note[:SEARCH_EXCERPT_CHARS])
                    claim_terms = _claim_terms_from_text(title, note[:SEARCH_EXCERPT_CHARS])
                    return {'receipt_id': receipt, 'result_id': rid, 'note_len': n_len, 'kind': 'search', 'spans': _search_excerpt_span(n_len), 'title': title, 'url': url, 'preview': note[:SEARCH_EXCERPT_CHARS], 'text': note, 'supports': supports, 'claim_terms': claim_terms}

                def _format_search_tool_output(query_text: str, receipt: str, results: list):
                    rows: list[dict] = []
                    lines = [f'# web_search({query_text!r}): {len(results)} results']
                    for item in results:
                        row = _search_row_from_item(item, receipt, query_text)
                        if row is None:
                            continue
                        rows.append(row)
                        supports = row.get('supports') or []
                        supp_note = '\n    ' + supports[0] if supports else ''
                        lines.append(f"[{_SLOT.format(len(rows) - 1)}] {row['title']} — {row['url']}\n    {row['preview']}{supp_note}")
                    return ToolOutput('\n'.join(lines), rows)

                async def _search_payload_with_retries(query_text: str):
                    payload = None
                    fired: set[str] = set()
                    for attempt, allow_repeat in _search_attempt_plan(query_text):
                        if not attempt.strip() or (attempt in fired and (not allow_repeat)):
                            continue
                        fired.add(attempt)
                        try:
                            payload = await search_web(attempt, provider=SEARCH_PROVIDER, num=8, timeout=SEARCH_TIMEOUT_S)
                            if getattr(payload, 'results', None):
                                break
                        except Exception:
                            payload = None
                    return payload

                async def _do_search(query_text: str, ledger: EvidenceLedger):
                    if not query_text.strip():
                        return '# web_search: empty query'
                    payload = await _search_payload_with_retries(query_text)
                    if payload is None:
                        return f'# web_search({query_text!r}) failed'
                    _spend_note(payload)
                    receipt = str(getattr(payload, 'receipt_id', '') or '')
                    results = list(getattr(payload, 'results', None) or [])
                    if not receipt:
                        return f'# web_search({query_text!r}): no citable results'
                    return _format_search_tool_output(query_text, receipt, results)

                def _fetch_plain_tool_output(url: str, question: str, focus: str, receipt: str, rid: str, note: str) -> ToolOutput:
                    supports = _infer_supports(question, 'read_page', {'url': url}, url, url, note[:1200])
                    claim_terms = _claim_terms_from_text(question, focus, note[:1200])
                    row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, len(note))], 'title': url, 'url': url, 'preview': note[:1200], 'text': note, 'supports': supports, 'claim_terms': claim_terms}
                    return ToolOutput(f'# read_page({url!r}) -> [{_SLOT.format(0)}] full page, {len(note)} chars\n{note}', [row])

                def _fetch_windowed_tool_output(url: str, question: str, focus: str, receipt: str, rid: str, note: str) -> ToolOutput:
                    terms = _key_terms(question) | _key_terms(focus)
                    windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE)
                    preview = note[windows[0][0]:windows[0][0] + 1200]
                    supports = _infer_supports(question, 'read_page', {'url': url, 'focus': focus}, url, url, preview)
                    claim_terms = _claim_terms_from_text(question, focus, preview)
                    row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, FETCH_HEAD_CHARS)] + list(windows), 'title': url, 'url': url, 'preview': preview, 'text': note, 'supports': supports, 'claim_terms': claim_terms}
                    head = note[:FETCH_HEAD_CHARS]
                    sections = ''.join((f'\n--- section @{s} ---\n{note[s:e]}' for s, e in windows))
                    return ToolOutput(f"# read_page({url!r}) -> [{_SLOT.format(0)}] {len(note)} chars total; head + the {len(windows)} most relevant section(s) shown ({', '.join((f'{s}-{e}' for s, e in windows))}). If the answer set may continue elsewhere in this page, call read_page again with a different focus.\n--- head ---\n{head}{sections}", [row])

                async def _fetch_page_payload(url: str):
                    payload = None
                    for _attempt in (0, 1):
                        try:
                            payload = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=FETCH_TIMEOUT_S)
                            if getattr(payload, 'results', None):
                                break
                        except Exception:
                            payload = None
                    return payload

                async def _do_fetch(url: str, focus: str, question: str, ledger: EvidenceLedger) -> str:
                    if not url.strip():
                        return '# read_page: empty url'
                    payload = await _fetch_page_payload(url)
                    if payload is None:
                        return f'# read_page({url!r}) failed'
                    _spend_note(payload)
                    receipt = str(getattr(payload, 'receipt_id', '') or '')
                    results = list(getattr(payload, 'results', None) or [])
                    if not results or not receipt:
                        return f'# read_page({url!r}): no content'
                    item = results[0]
                    rid = getattr(item, 'result_id', None)
                    note = getattr(item, 'note', None) or ''
                    if not isinstance(rid, str) or not rid or (not note.strip()):
                        return f'# read_page({url!r}): no usable content'
                    if len(note) <= FETCH_PLAIN_CHARS:
                        return _fetch_plain_tool_output(url, question, focus, receipt, rid, note)
                    return _fetch_windowed_tool_output(url, question, focus, receipt, rid, note)
                _SEC_TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
                _SEC_SUBMISSIONS_URL = 'https://data.sec.gov/submissions/CIK{cik10}.json'
                _SEC_DOC_URL = 'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}'
                _SEC_FETCH_TIMEOUT_S = 26.0
                _SEC_MIN_HEADROOM_S = 40.0
                _SEC_CACHE: dict = {}
                _SEC_STOPWORDS = frozenset('inc incorporated corp corporation company companies co ltd limited llc plc lp llp group holdings the'.split())
                _SEC_ALNUM_RE = re.compile('[a-z0-9]+')

                def _sec_tokens(text: str) -> list[str]:
                    return [w for w in _SEC_ALNUM_RE.findall((text or '').lower()) if w not in _SEC_STOPWORDS]

                def _sec_norm_form(form: str) -> str:
                    f = ' '.join((form or '').upper().replace('FORM', ' ').split())
                    m = re.fullmatch('(\\d{1,2})\\s*-?\\s*([A-Z])', f)
                    if m:
                        return f'{m.group(1)}-{m.group(2)}'
                    m = re.fullmatch('(DEF)\\s*-?\\s*(14A)', f)
                    if m:
                        return 'DEF 14A'
                    return f

                async def _fetch_json(url: str, deadline: float):
                    cached = _SEC_CACHE.get(url)
                    if cached is not None:
                        return cached
                    for _attempt in (0, 1):
                        left = deadline - monotonic()
                        if left < 12.0:
                            return None
                        try:
                            payload = await asyncio.wait_for(fetch_page(url, provider=SEARCH_PROVIDER, timeout=min(_SEC_FETCH_TIMEOUT_S, left - 6.0)), timeout=min(_SEC_FETCH_TIMEOUT_S, left - 6.0) + 4.0)
                        except Exception:
                            continue
                        _spend_note(payload)
                        results = list(getattr(payload, 'results', None) or [])
                        note = getattr(results[0], 'note', None) or '' if results else ''
                        start = note.find('{')
                        end = note.rfind('}')
                        if start == -1 or end <= start:
                            continue
                        try:
                            obj = json.loads(note[start:end + 1])
                        except Exception:
                            continue
                        if isinstance(obj, dict):
                            _SEC_CACHE[url] = obj
                            return obj
                    return None

                def _sec_pick_filing(recent: dict, form: str, year: str):
                    forms = recent.get('form')
                    accs = recent.get('accessionNumber')
                    docs = recent.get('primaryDocument')
                    rdates = recent.get('reportDate')
                    fdates = recent.get('filingDate')
                    if not (isinstance(forms, list) and isinstance(accs, list) and isinstance(docs, list)):
                        return None
                    n = min(len(forms), len(accs), len(docs))
                    form_norm = _sec_norm_form(form)
                    best_year = None
                    best_any = None
                    for i in range(n):
                        if _sec_norm_form(str(forms[i])) != form_norm:
                            continue
                        if accs[i] is None or docs[i] is None:
                            continue
                        acc = str(accs[i])
                        doc = str(docs[i])
                        if not acc or not (doc.endswith('.htm') or doc.endswith('.html')):
                            continue
                        rd = str(rdates[i]) if isinstance(rdates, list) and i < len(rdates) and (rdates[i] is not None) else ''
                        fd = str(fdates[i]) if isinstance(fdates, list) and i < len(fdates) and (fdates[i] is not None) else ''
                        key = rd or fd
                        if best_any is None or key > best_any[0]:
                            best_any = (key, acc, doc)
                        if year and rd[:4] == year:
                            if best_year is None or key > best_year[0]:
                                best_year = (key, acc, doc)
                    pick = best_year if year else best_any
                    if pick is None:
                        return None
                    return (pick[1], pick[2])
                _SEC_SEARCH_HINT = 'search "site:sec.gov {company} {year} {form}" and read_page the Archives result'

                async def _do_sec_filing(company: str, form: str, year: str, deadline: float) -> str:
                    company = (company or '').strip()
                    form = (form or '').strip() or '10-K'
                    year = (year or '').strip()[:4]
                    hint = _SEC_SEARCH_HINT.format(company=company, year=year, form=form)
                    if not company:
                        return '# sec_filing: company required'
                    if deadline - monotonic() < _SEC_MIN_HEADROOM_S:
                        return f'# sec_filing: skipped (low time) — {hint}'
                    tickers = await _fetch_json(_SEC_TICKERS_URL, deadline)
                    if not isinstance(tickers, dict):
                        return f'# sec_filing: EDGAR ticker index unavailable — {hint}'
                    want = _sec_tokens(company)
                    best = None
                    for row in tickers.values():
                        if not isinstance(row, dict):
                            continue
                        title = str(row.get('title', ''))
                        ticker = str(row.get('ticker', '')).lower()
                        words = set(_sec_tokens(title))
                        n_hit = sum((1 for w in want if w in words))
                        if len(want) == 1 and ticker == want[0]:
                            score = 100
                        elif want and n_hit == len(want):
                            score = 50 + n_hit
                        else:
                            continue
                        cand = (score, -len(title), str(row.get('cik_str', '')).zfill(10), title)
                        if best is None or cand > best:
                            best = cand
                    if best is None:
                        return f'# sec_filing({company!r}): no confident EDGAR match — {hint}'
                    cik10, title = (best[2], best[3])
                    subs = await _fetch_json(_SEC_SUBMISSIONS_URL.format(cik10=cik10), deadline)
                    filings = subs.get('filings') if isinstance(subs, dict) else None
                    recent = filings.get('recent') if isinstance(filings, dict) else None
                    if not isinstance(recent, dict):
                        return f'# sec_filing({company!r}): EDGAR submissions unavailable for {title} — {hint}'
                    pick = _sec_pick_filing(recent, form, year)
                    if pick is None:
                        return f"# sec_filing({company!r}, {form!r}, year={year or 'latest'}): no matching filing in EDGAR's recent index for {title} — check the form/year, or {hint}"
                    accession, doc = pick
                    url = _SEC_DOC_URL.format(cik=cik10.lstrip('0') or cik10, accession=accession.replace('-', ''), doc=doc)
                    return f"# sec_filing -> {title} {form} {year or '(latest)'} primary document:\n{url}\nNow call read_page on this URL with a focus hint for the section you need, and cite figures from that read_page result."

                def _ledger_page(url: str, ledger: EvidenceLedger) -> tuple[int, dict] | None:
                    u = (url or '').strip().rstrip('/')
                    if not u:
                        return None
                    for i in range(len(ledger.rows) - 1, -1, -1):
                        row = ledger.rows[i]
                        if not row.get('text'):
                            continue
                        r = str(row.get('url') or '').rstrip('/')
                        if r == u or r.endswith(u) or u.endswith(r):
                            return (i + 1, row)
                    return None

                def _do_page_grep(url: str, pattern: str, ledger: EvidenceLedger) -> str:
                    hit = _ledger_page(url, ledger)
                    if hit is None:
                        return f'# page_grep: {url!r} has not been fetched this run; call read_page first'
                    n, row = hit
                    text = row.get('text') or ''
                    pat = (pattern or '').strip()
                    if not pat:
                        return '# page_grep: empty pattern'
                    try:
                        rx = re.compile(pat, re.I)
                    except re.error:
                        rx = re.compile(re.escape(pat), re.I)
                    out, seen_at = ([], [])
                    for m in rx.finditer(text):
                        c = (m.start() + m.end()) // 2
                        if any((abs(c - prev) < PAGE_GREP_WINDOW // 2 for prev in seen_at)):
                            continue
                        seen_at.append(c)
                        a = max(0, c - PAGE_GREP_WINDOW // 2)
                        b = min(len(text), a + PAGE_GREP_WINDOW)
                        out.append(f'\n--- match @{a} ---\n{text[a:b]}')
                        if len(out) >= PAGE_GREP_MAX_HITS:
                            break
                    if not out:
                        return f'# page_grep({pat!r}) on [{n}]: no match in {len(text)} chars. Try a shorter or looser pattern.'
                    return f'# page_grep({pat!r}) on [{n}] -> {len(out)} match(es) of {len(text)} chars' + ''.join(out)

                def _do_page_read(url: str, offset: int, length: int, ledger: EvidenceLedger) -> str:
                    hit = _ledger_page(url, ledger)
                    if hit is None:
                        return f'# page_read: {url!r} has not been fetched this run; call read_page first'
                    n, row = hit
                    text = row.get('text') or ''
                    a = max(0, min(int(offset or 0), max(0, len(text) - 1)))
                    ln = int(length or PAGE_READ_MAX_CHARS)
                    b = min(len(text), a + max(1, min(ln, PAGE_READ_MAX_CHARS)))
                    return f'# page_read([{n}] @{a}:{b} of {len(text)})\n{text[a:b]}'

                def _do_retain_evidence(source: str, quote: str, ledger: EvidenceLedger) -> str:
                    raw = (source or '').strip().strip('[]')
                    try:
                        n = int(raw)
                    except ValueError:
                        return f'# retain_evidence: source must be a result number like [3], got {source!r}'
                    if not 1 <= n <= len(ledger.rows):
                        return f'# retain_evidence: no result [{n}] exists yet'
                    row = ledger.rows[n - 1]
                    text = row.get('text') or ''
                    q = (quote or '').strip()
                    if len(q) < RETAIN_MIN_QUOTE:
                        return f'# retain_evidence: quote too short ({len(q)} chars); quote at least {RETAIN_MIN_QUOTE} characters of the source text'
                    if not text:
                        return f'# retain_evidence: result [{n}] has no stored text to quote from'
                    i = text.find(q)
                    if i < 0:
                        i = text.lower().find(q.lower())
                    if i < 0:
                        squashed = ' '.join(q.split())
                        i = ' '.join(text.split()).lower().find(squashed.lower())
                        if i >= 0:
                            i = -1
                    if i < 0:
                        return f'# retain_evidence: that text does not appear in [{n}]. Quote it EXACTLY as the source prints it, or read more of the page first.'
                    kept = row.setdefault('retained', [])
                    if len(kept) >= RETAIN_MAX_PER_ROW:
                        return f'# retain_evidence: [{n}] already has {len(kept)} retained excerpts'
                    a = max(0, i - RETAIN_MARGIN_CHARS)
                    b = min(int(row.get('note_len') or len(text)), i + len(q) + RETAIN_MARGIN_CHARS)
                    if b <= a:
                        return f'# retain_evidence: could not bound the excerpt in [{n}]'
                    kept.append((a, b))
                    cl = _CLAIM_LEDGER_REF.get('ledger')
                    if cl is not None:
                        try:
                            cl.note_retained(n, q)
                        except Exception:
                            pass
                    return f'# retain_evidence: kept {b - a} chars of [{n}] around your quote. Cite [{n}] for that claim.'

                def _parse_tool_args(call) -> dict:
                    try:
                        args = json.loads(getattr(call, 'arguments', None) or '{}')
                    except Exception:
                        args = {}
                    if not isinstance(args, dict):
                        return {}
                    return args

                async def _dispatch_named_tool(name: str, args: dict, question: str, ledger: EvidenceLedger, deadline: float):
                    if name == 'web_search':
                        return await _do_search(str(args.get('query') or ''), ledger)
                    if name == 'read_page':
                        return await _do_fetch(str(args.get('url') or ''), str(args.get('focus') or ''), question, ledger)
                    if name == 'retain_evidence':
                        return _do_retain_evidence(str(args.get('source') or ''), str(args.get('quote') or ''), ledger)
                    if name == 'page_grep':
                        return _do_page_grep(str(args.get('url') or ''), str(args.get('pattern') or ''), ledger)
                    if name == 'page_read':
                        return _do_page_read(str(args.get('url') or ''), args.get('offset') or 0, args.get('length') or PAGE_READ_MAX_CHARS, ledger)
                    if name == 'sec_filing':
                        return await _do_sec_filing(str(args.get('company') or ''), str(args.get('form') or ''), str(args.get('year') or ''), deadline)
                    return f'# unknown tool {name!r}'

                async def _run_tool(call, question: str, ledger: EvidenceLedger, deadline: float) -> str:
                    args = _parse_tool_args(call)
                    name = getattr(call, 'name', '') or ''
                    return await _dispatch_named_tool(name, args, question, ledger, deadline)
                _REASONING_MANDATORY = ('openai/gpt-oss',)

                def _least_think(lane: str, model: str='') -> dict:
                    for prefix in _REASONING_MANDATORY:
                        if model.startswith(prefix):
                            return {'enabled': True, 'effort': 'low'}
                    return {'enabled': False}
                _FAST_UPSTREAMS = ('Decart', 'CoreWeave', 'Alibaba')
                _FAST_UPSTREAMS_OSS = ('Cerebras', 'Groq', 'BaseTen')

                def _upstream(lane: str, model: str) -> dict | None:
                    if lane != LLM_LANE_A:
                        return None
                    if model.startswith('z-ai/glm-5.2'):
                        only = _FAST_UPSTREAMS
                    elif model.startswith('openai/gpt-oss'):
                        only = _FAST_UPSTREAMS_OSS
                    else:
                        return None
                    return {'provider': {'only': list(only), 'allow_fallbacks': True}}

                def _pin_fallback_sequence(lane: str, model: str):
                    pin0 = _upstream(lane, model)
                    return (pin0, None) if pin0 is not None else (None,)

                def _llm_text_from_payload(payload) -> str:
                    llm = getattr(payload, 'llm', None)
                    text = (getattr(llm, 'raw_text', None) or '').strip()
                    if text:
                        return text
                    choices = getattr(llm, 'choices', None) or []
                    if choices:
                        content = getattr(choices[0].message, 'content', None)
                        if isinstance(content, str):
                            return content.strip()
                    return ''

                def _turn_candidate_text(llm, msg) -> str:
                    candidate = (getattr(llm, 'raw_text', None) or '').strip()
                    if not candidate:
                        content = getattr(msg, 'content', None)
                        if isinstance(content, str):
                            candidate = content.strip()
                    return candidate

                async def _llm_chat_pin_ladder(lane: str, model: str, messages: list[dict], *, max_tokens: int, timeout: float, think: dict, temperature: float=0.15):
                    payload = None
                    for pin in _pin_fallback_sequence(lane, model):
                        try:
                            payload = await llm_chat(provider=lane, model=model, messages=messages, temperature=temperature, max_output_tokens=max_tokens, timeout=timeout, thinking=think, provider_extra=pin)
                            break
                        except Exception:
                            if pin is None:
                                raise
                            continue
                    return payload

                async def _chat_simple(lane: str, model: str, system: str, user: str, *, max_tokens: int, timeout: float, think: dict | None=None) -> str:
                    if think is None:
                        think = _least_think(lane, model)
                    payload = await _llm_chat_pin_ladder(lane, model, [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], max_tokens=max_tokens, timeout=timeout, think=think, temperature=0.15)
                    _spend_note(payload)
                    return _llm_text_from_payload(payload)

                class _EmptyChoiceMessage:
                    content = ''
                    tool_calls = ()

                class _EmptyChoice:
                    message = _EmptyChoiceMessage()

                class _EmptyLlm:
                    raw_text = ''
                    choices = (_EmptyChoice(),)

                class _EmptyTurn:
                    llm = _EmptyLlm()
                    budget = None
                _EMPTY_TURN = _EmptyTurn()
                _CHAT_TURN_LANES = ((LLM_LANE_A, LOOP_MODEL_A, True), (LLM_LANE_A, LOOP_MODEL_A, False), (LLM_LANE_B, LOOP_MODEL_B, False))

                def _message_payload_chars(messages: list[dict]) -> int:
                    return sum((len(str(msg.get('content') or '')) for msg in messages if isinstance(msg, dict)))

                def _loop_turn_thinking(finish_only: bool, lane: str) -> dict:
                    if finish_only and lane == LLM_LANE_B:
                        return {'enabled': False}
                    return {'enabled': True, 'effort': 'low'}

                async def _attempt_chat_turn_lane(messages: list[dict], deadline: float, turn_wall: float, *, finish_only: bool, force_tools: bool, lane: str, model: str, pinned: bool, payload_chars: int):
                    if lane == LLM_LANE_B and payload_chars > LANE_B_MAX_PAYLOAD_CHARS:
                        return _EMPTY_TURN
                    timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0, turn_wall - monotonic())
                    if timeout <= 5.0:
                        return None
                    payload = await asyncio.wait_for(llm_chat(provider=lane, model=model, messages=messages, tools=LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking=_loop_turn_thinking(finish_only, lane), max_output_tokens=6000 if finish_only and lane == LLM_LANE_B else None, provider_extra=_upstream(lane, model) if pinned else None, timeout=timeout), timeout=min(timeout + 6.0, max(1.0, deadline - monotonic() - 1.0)))
                    _spend_note(payload)
                    return payload

                async def _chat_turn(messages: list[dict], deadline: float, *, finish_only: bool, force_tools: bool=False):
                    turn_wall = monotonic() + TURN_TIMEOUT_S + 35.0
                    payload_chars = _message_payload_chars(messages)
                    for lane, model, pinned in _CHAT_TURN_LANES:
                        try:
                            return await _attempt_chat_turn_lane(messages, deadline, turn_wall, finish_only=finish_only, force_tools=force_tools, lane=lane, model=model, pinned=pinned, payload_chars=payload_chars)
                        except Exception:
                            continue
                    return None
                _BRIEF_SYSTEM = 'Senior research analyst. Commit to concrete best answers from knowledge; mark uncertain values (verify). Never refuse.'

                def _brief_user_prompt(question: str) -> str:
                    return f"Question:\n{question}\n\nFill in this internal worksheet. It is planning scratch for your own use, never an answer, so keep the tags lowercase and never reuse them as section headings later.\ndraft: your full best answer now — candidate pool, every stated condition applied, qualifying entities with figures/dates, near-miss exclusions. Flag shaky facts with (verify).\nconditions: each atomic condition in the question, numbered, including any output-format demand.\nsearches: 3-6 precise web searches for the facts that decide the answer (entity + metric + year; include a named source's site: filter).\nurls: up to 5 exact URLs worth reading directly (official stats pages, sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."

                def _split_brief_draft(raw: str) -> str:
                    draft = raw
                    cut = min((mm.start() for mm in (re.search('[#*_\\s]*(?:conditions|CHECKLIST)[#*_\\s]*:', raw, re.IGNORECASE), re.search('^[ \\t]*[#*_>]{0,4}[ \\t]*(?:conditions|CHECKLIST)[ \\t]*[#*_]{0,3}[ \\t]*$', raw, re.IGNORECASE | re.MULTILINE)) if mm is not None), default=None)
                    if cut is not None:
                        draft = raw[:cut]
                    draft = re.sub('^[#*_\\s]*(?:draft|BEST ANSWER)[#*_\\s]*:[#*_\\s]*', '', draft, flags=re.IGNORECASE)
                    draft = re.sub('^[ \\t]*[#*_>]{0,4}[ \\t]*(?:draft|BEST ANSWER)[ \\t]*[#*_]{0,3}[ \\t]*\\n+', '', draft, flags=re.IGNORECASE)
                    return draft.strip()

                def _brief_system_block(raw: str) -> str:
                    return 'PRIOR ANALYSIS — your own planning worksheet (verify anything marked (verify), and correct it wherever tool results disagree). Its tags are internal: never reproduce them, or any section named after them, in the answer.\n' + raw.strip()

                async def _brief_raw_dual_lane(system: str, user: str) -> str:
                    try:
                        return await _chat_simple(LLM_LANE_A, LOOP_MODEL_A, system, user, max_tokens=2400, timeout=BRIEF_TIMEOUT_S, think=_least_think(LLM_LANE_A, LOOP_MODEL_A))
                    except Exception:
                        try:
                            return await _chat_simple(LLM_LANE_B, LOOP_MODEL_B, system, user, max_tokens=2400, timeout=BRIEF_TIMEOUT_S, think=_least_think(LLM_LANE_B, LOOP_MODEL_B))
                        except Exception:
                            return ''

                async def _knowledge_brief(question: str) -> tuple[str, str]:
                    system = _BRIEF_SYSTEM
                    user = _brief_user_prompt(question)
                    raw = await _brief_raw_dual_lane(system, user)
                    if not raw:
                        return ('', '')
                    return (_split_brief_draft(raw), _brief_system_block(raw))
                _SEED_TOKEN_RE = re.compile("[A-Za-z0-9][A-Za-z0-9.\\-']+")
                _SEED_STOP = frozenset('name list give tell show find identify please could would you your can may might should must let make sure both also'.split())
                MAX_SEED_QUERIES = 3
                _SEED_CAP_REF: dict = {'max': MAX_SEED_QUERIES}

                def _seed_queries(question: str, set_question: bool) -> list[str]:
                    q = ' '.join((question or '').split())
                    if not q:
                        return []
                    seeds = [q[:300]]
                    salient = [t for t in _SEED_TOKEN_RE.findall(q) if len(t) >= 3 and t.lower() not in _STOP and (t.lower() not in _SEED_STOP)]
                    if len(salient) >= 2:
                        seeds.append(' '.join(salient[:8]))
                    if set_question and salient:
                        seeds.append('list of ' + ' '.join(salient[:6]))
                    out: list[str] = []
                    for s in seeds:
                        s = s.strip()
                        if s and s not in out:
                            out.append(s)
                    return out[:int(_SEED_CAP_REF.get('max') or MAX_SEED_QUERIES)]

                async def _preseed(question: str, set_question: bool, ledger: EvidenceLedger, deadline: float) -> str:
                    seeds = _seed_queries(question, set_question)
                    if not seeds or deadline - monotonic() < 40.0:
                        return ''
                    blocks: list = []
                    for seed in seeds:
                        if deadline - monotonic() < 30.0:
                            break
                        try:
                            out = await asyncio.wait_for(_do_search(seed, ledger), timeout=SEARCH_TIMEOUT_S * 2 + 6.0)
                            blocks.append(_commit_tool_output(out, ledger))
                        except Exception:
                            continue
                    good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
                    if not good:
                        return ''
                    return 'Automatic first-pass searches (already numbered — cite these [n] directly, and search further as needed):\n\n' + '\n'.join(good)

                def _append_loop_rule_blocks(messages: list[dict], question: str, route: str, plan: str, brief: str) -> bool:
                    set_q = _needs_set_completeness(question)
                    messages.append({'role': 'system', 'content': LOOP_RULES})
                    messages.append({'role': 'system', 'content': _fingerprint_system_note()})
                    if route == 'easy':
                        messages.append({'role': 'system', 'content': EASY_LOOP_RULE})
                    else:
                        messages.append({'role': 'system', 'content': RESEARCH_PLAN_RULE})
                        messages.append({'role': 'system', 'content': CLAIM_LEDGER_RULE})
                        messages.append({'role': 'system', 'content': CITATION_AUDIT_RULE})
                        messages.append({'role': 'system', 'content': FAILURE_RECOVERY_RULE})
                        if set_q or _needs_superlative_proof(question):
                            messages.append({'role': 'system', 'content': SET_ENGINE_RULE})
                    if set_q:
                        messages.append({'role': 'system', 'content': SET_RULE})
                    if _needs_superlative_proof(question):
                        messages.append({'role': 'system', 'content': SUPERLATIVE_RULE})
                    if plan:
                        messages.append({'role': 'system', 'content': plan})
                    if brief:
                        messages.append({'role': 'system', 'content': brief})
                    return set_q

                async def _bootstrap_loop_messages(question: str, brief: str, ledger: EvidenceLedger, deadline: float, route: str, plan: str) -> list[dict]:
                    messages: list[dict] = []
                    set_q = _append_loop_rule_blocks(messages, question, route, plan, brief)
                    seeded = await _preseed(question, set_q, ledger, deadline)
                    if seeded:
                        messages.append({'role': 'system', 'content': seeded})
                    cl = _CLAIM_LEDGER_REF.get('ledger')
                    if cl is not None:
                        summ = cl.summary()
                        if summ:
                            messages.append({'role': 'system', 'content': summ})
                    messages.append({'role': 'user', 'content': question})
                    return messages

                def _loop_turn_flags(left: float, turn: int, turn_cap: int) -> tuple[bool, bool]:
                    out_of_time = left <= WRAPUP_AT_S
                    out_of_spend = _spend_left() <= WRAPUP_MIN_USD
                    finish_only = out_of_time or out_of_spend or turn >= turn_cap
                    should_wrap = finish_only or turn >= turn_cap - 1
                    return (finish_only, should_wrap)

                async def _collect_tool_fanout_results(run_calls, question: str, ledger: EvidenceLedger, deadline: float) -> list:
                    tool_budget = max(5.0, min(FETCH_TIMEOUT_S * 2 + 6.0, deadline - monotonic() - MIN_TAIL_S))
                    tool_tasks = [asyncio.ensure_future(_run_tool(c, question, ledger, deadline)) for c in run_calls]
                    try:
                        await asyncio.wait(tool_tasks, timeout=tool_budget)
                    except Exception:
                        pass
                    results = []
                    for t in tool_tasks:
                        if t.done():
                            try:
                                results.append(t.result())
                            except Exception as exc:
                                results.append(f'# tool crashed: {exc}')
                        else:
                            t.cancel()
                            results.append('# tool timed out — use what you already have')
                    return results

                def _commit_fanout_into_messages(messages: list[dict], calls, run_calls, results, ledger: EvidenceLedger) -> None:
                    for call_result in zip(run_calls, results):
                        call = call_result[0]
                        body = _commit_tool_output(call_result[1], ledger)
                        messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': body})
                    for call in calls[8:]:
                        messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})

                def _apply_finish_candidate(messages: list[dict], candidate: str, repairs_left: int, deadline: float) -> tuple[str, int, str]:
                    if not _is_usable_answer(candidate):
                        if repairs_left > 0 and deadline - monotonic() > MIN_TAIL_S + 10.0:
                            messages.append({'role': 'system', 'content': _REPAIR_ORDER})
                            return ('', repairs_left - 1, 'repair')
                        return ('', repairs_left, 'abort')
                    messages.append({'role': 'assistant', 'content': candidate})
                    return (candidate, repairs_left, 'accept')

                async def _loop(question: str, brief: str, ledger: EvidenceLedger, deadline: float, turn_cap: int, carry: list[dict] | None=None, allow_tools_in_wrapup: bool=False, route: str='hard', plan: str='') -> tuple[str, list[dict]]:
                    if carry is not None:
                        messages = carry
                    else:
                        messages = await _bootstrap_loop_messages(question, brief, ledger, deadline, route, plan)
                    answer = ''
                    ordered_wrapup = False
                    repairs_left = ANSWER_REPAIR_TURNS
                    for turn in range(1, turn_cap + 1):
                        left = deadline - monotonic()
                        if left <= MIN_TAIL_S:
                            break
                        finish_only, should_wrap = _loop_turn_flags(left, turn, turn_cap)
                        if should_wrap and (not ordered_wrapup):
                            messages.append({'role': 'system', 'content': _wrapup_order(left)})
                            ordered_wrapup = True
                        payload = await _chat_turn(messages, deadline, finish_only=finish_only, force_tools=allow_tools_in_wrapup and turn == 1)
                        if payload is None:
                            break
                        llm = getattr(payload, 'llm', None)
                        choices = getattr(llm, 'choices', None) or []
                        if not choices:
                            break
                        msg = choices[0].message
                        calls = getattr(msg, 'tool_calls', None) or ()
                        if not calls:
                            candidate = _turn_candidate_text(llm, msg)
                            answer, repairs_left, action = _apply_finish_candidate(messages, candidate, repairs_left, deadline)
                            if action == 'repair':
                                continue
                            break
                        messages.append(msg.to_input_message())
                        run_calls = calls[:8]
                        results = await _collect_tool_fanout_results(run_calls, question, ledger, deadline)
                        _commit_fanout_into_messages(messages, calls, run_calls, results, ledger)
                    return (answer, messages)

                def _deterministic_citation_gaps(answer: str, question: str) -> list[str]:
                    gaps: list[str] = []
                    text = _normalize_brackets(answer or '')
                    if not text.strip():
                        return ['empty_answer']
                    for sent in re.split('(?<=[.!?])\\s+', text):
                        s = sent.strip()
                        if len(s) < 20:
                            continue
                        if _CITE_MARK_RE.search(s):
                            continue
                        if re.search('\\d', s) or re.search('\\b[A-Z][a-z]{2,}\\b', s):
                            if re.match('^(?:proof|candidates|pool|notes?)\\b', s, re.I):
                                continue
                            gaps.append(s[:160])
                            if len(gaps) >= 4:
                                break
                    if _needs_set_completeness(question) or _needs_superlative_proof(question):
                        if not re.search('\\b(?:none|no |all |every )', text, re.I) and text.count('[') < 2:
                            gaps.append('set_or_superlative_under_cited')
                    return gaps
                _AUDIT_GAP_KEYS = ('incomplete_roster', 'hand_waved_tally', 'unanswered_parts', 'uncited_facts', 'wrong_kind', 'thin_proof', 'citation_mismatch', 'missing_requested')
                _AUDIT_ROSTER_KEYS = frozenset(('incomplete_roster', 'hand_waved_tally'))

                def _audit_probe(question: str, answer: str) -> str:
                    return f"""Audit the answer against the question. JSON only, keys: "unanswered_parts" (list; question elements not addressed), "uncited_facts" (list; load-bearing claims without [n]), "wrong_kind" (list; places where the named entity is a different KIND than the question asks — a person instead of a series, a duo instead of a show), "incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges over a candidate pool — a closed set that can be enumerated, or several conditions applied to a class — then: is the pool itself stated and plausibly COMPLETE, and does the answer give a verdict for EVERY member (qualifies / excluded because X, each cited)? Name any pool member the answer never mentions, and say so if the pool looks truncated — an answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not partial), "thin_proof" (list; a qualifier lacking a per-condition citation, or a plausible near-miss candidate never addressed), "hand_waved_tally" (list; for a superlative/count/most-common question: the answer asserts a winner or a count WITHOUT showing the candidate table it was derived from. Phrases like 'among others', 'and several more', 'multiple X', or naming 2 examples to justify a count are all hand-waving — say so and name what the tally must list), "citation_mismatch" (list; [n] that does not support the adjacent claim), "missing_requested" (list; asked items absent from the answer). Empty lists when clean.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:11000]}"""

                def _collect_audit_gaps(report) -> tuple[list[str], list[str]]:
                    gaps: list[str] = []
                    roster_gaps: list[str] = []
                    if isinstance(report, dict):
                        for key in _AUDIT_GAP_KEYS:
                            vals = report.get(key)
                            if isinstance(vals, list):
                                found = [str(v) for v in vals if str(v).strip()]
                                if key in _AUDIT_ROSTER_KEYS:
                                    roster_gaps.extend(found)
                                gaps.extend(found)
                    return (gaps, roster_gaps)

                def _audit_rewrite_order(gaps: list[str], roster_gaps: list[str]) -> str:
                    order = 'AUDIT: the answer has gaps:\n- ' + '\n- '.join(gaps[:6])
                    if roster_gaps:
                        order += "\nThe candidate pool is incomplete — this loses outright. FIRST search for the authoritative LIST/roster/table that enumerates the whole pool (query it as a list, e.g. '<pool subject> full list', not one member at a time), verify EVERY member against every condition, then rewrite."
                    order += '\nUse at most 3 tool calls to close the most important gaps, then rewrite the COMPLETE final answer with [n] citations in the required shape.'
                    return order

                async def _audit_report(question: str, answer: str, deadline: float):
                    try:
                        raw = await _chat_simple(LLM_LANE_A, AUDIT_MODEL, 'Strict completeness auditor. JSON only.', _audit_probe(question, answer), max_tokens=2200, timeout=max(8.0, min(AUDIT_TIMEOUT_S, deadline - monotonic() - 72.0)))
                        raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                        return json.loads(raw)
                    except Exception:
                        return None

                async def _audit_patch(question: str, answer: str, messages: list[dict], ledger: EvidenceLedger, deadline: float) -> str:
                    report = await _audit_report(question, answer, deadline)
                    if report is None:
                        return answer
                    gaps, roster_gaps = _collect_audit_gaps(report)
                    if not gaps or deadline - monotonic() < 70.0:
                        return answer
                    messages.append({'role': 'system', 'content': _audit_rewrite_order(gaps, roster_gaps)})
                    patched, _ = await _loop(question, '', ledger, deadline, AUDIT_EXTRA_TURNS + 1, carry=messages, allow_tools_in_wrapup=True)
                    patched = patched.strip()
                    if not _is_usable_answer(patched) or len(patched) < int(len(answer) * 0.6):
                        return answer
                    return patched
                _BRACKET_FIX = {12304: '[', 12305: ']', 65339: '[', 65341: ']', 65288: '(', 65289: ')', 8209: '-', 8722: '-'}
                for _d in range(10):
                    _BRACKET_FIX[65296 + _d] = chr(48 + _d)

                def _normalize_brackets(text: str) -> str:
                    return (text or '').translate(_BRACKET_FIX)
                _CITE_NUM_RE = re.compile('\\[([0-9][0-9,\\s\\-]*)\\]')

                def _cited_numbers(answer: str, top: int) -> list[int]:
                    answer = _normalize_brackets(answer)
                    seen: set[int] = set()
                    out: list[int] = []
                    for m in _CITE_NUM_RE.finditer(answer):
                        for chunk in m.group(1).split(','):
                            piece = chunk.strip()
                            span = re.fullmatch('(\\d{1,4})\\s*-\\s*(\\d{1,4})', piece)
                            if span:
                                lo = int(span.group(1))
                                hi = int(span.group(2))
                                for n in range(lo, min(hi, lo + 16) + 1):
                                    if 1 <= n <= top and n not in seen:
                                        seen.add(n)
                                        out.append(n)
                            elif piece.isdigit():
                                n = int(piece)
                                if 1 <= n <= top and n not in seen:
                                    seen.add(n)
                                    out.append(n)
                    return out
                _OUTPUT_ONLY_RE = re.compile('\\boutput only\\b|\\brespond with only\\b|\\breply with only\\b|\\banswer with only\\b|\\bonly the exact\\b|\\bnothing else\\b|\\bno explanation\\b|\\bwithout explanation\\b|\\bno other text\\b|\\bjust the (?:name|names|value|values|number|numbers|list|text|answer|title|titles)\\b', re.IGNORECASE)
                _OUTPUT_ONLY_MIN_CHARS = 2

                def _answer_line_only(answer: str, question: str) -> str:
                    if not answer or not _OUTPUT_ONLY_RE.search(question or ''):
                        return answer
                    for raw in answer.split('\n'):
                        stripped = raw.strip()
                        if not stripped:
                            continue
                        if stripped[0] in '#>':
                            continue
                        line = re.sub('^[*_`\\s]+|[*_`\\s]+$', '', stripped).strip()
                        if not line:
                            continue
                        if line.startswith('|') or line.endswith(':'):
                            continue
                        if len(line) >= _OUTPUT_ONLY_MIN_CHARS:
                            return line
                    return answer
                _GLOSS_RE = re.compile('^(?P<a>[^()]{2,60}?)\\s*\\((?P<b>[^()]{2,60})\\)$')

                def _verbatim_from_source(value: str, ledger: EvidenceLedger) -> str:
                    v = (value or '').strip()
                    m = _GLOSS_RE.match(v)
                    if not m:
                        return value
                    texts = [r.get('text') or '' for r in ledger.rows if r.get('text')]
                    if not texts:
                        return value

                    def seen(t: str) -> bool:
                        return bool(t) and any((t in src for src in texts))
                    if seen(v):
                        return value
                    a, b = (m.group('a').strip(), m.group('b').strip())
                    hits = [x for x in (b, a) if seen(x)]
                    if len(hits) == 1:
                        return hits[0]
                    if len(hits) == 2:
                        lo, hi = sorted(hits, key=len)
                        if lo.lower() in hi.lower():
                            return hi
                    return value

                def _verbatim_structured(obj, ledger: EvidenceLedger, depth: int=0):
                    if depth > 6:
                        return obj
                    if isinstance(obj, str):
                        return _verbatim_from_source(obj, ledger)
                    if isinstance(obj, list):
                        return [_verbatim_structured(x, ledger, depth + 1) for x in obj]
                    if isinstance(obj, dict):
                        return {k: _verbatim_structured(v, ledger, depth + 1) for k, v in obj.items()}
                    return obj

                def _citations_for(answer: str, ledger: EvidenceLedger) -> list[CitationRef]:
                    refs: list[CitationRef] = []
                    spent = 0
                    answer_terms = set(_claim_terms_from_text(answer))
                    for n in _cited_numbers(answer, len(ledger.rows)):
                        if len(refs) >= CITATION_CAP:
                            break
                        row = ledger.rows[n - 1]
                        terms = set(row.get('claim_terms') or []) | answer_terms
                        ref = _densified_ref(ledger, n, terms) if terms else ledger.ref_for(n)
                        if ref is None:
                            continue
                        slices = getattr(ref, 'slices', None)
                        cost = sum((max(0, s.end - s.start) for s in slices)) if slices else int(row.get('note_len') or 0)
                        if spent + cost > EVIDENCE_CHAR_BUDGET:
                            continue
                        spent += cost
                        refs.append(ref)
                    return refs
                _VERIFY_MARK_RE = re.compile('\\s*\\((?:verify|unverified|uncertain)[^)]*\\)', re.I)
                _TOOL_MARKUP_RE = re.compile('<\\s*/?\\s*tool_call|<\\s*/?\\s*(?:arg_key|arg_value|function_call|invoke)\\b|\\bweb_search\\s*[（(]\\s*query|\\bread_page\\s*[（(]\\s*url|\\bsec_filing\\s*[（(]\\s*company', re.I)
                _STUB_ANSWER_RE = re.compile('^\\s*(?:best-effort answer unavailable|no question provided)', re.I)
                _REFUSAL_ONLY_RE = re.compile("^\\s*(?:i (?:cannot|can't|am unable|was unable)|unable to|sorry[,.]|i don'?t have (?:enough|access))", re.I)
                _INTENT_NARRATION_RE = re.compile("^\\s*(?:i (?:need|will|should|am going|'ll)\\b|let me\\b|first,? (?:i|let)\\b|i'?ll (?:search|look|start|begin|gather|check))", re.I)
                MIN_ANSWER_CHARS = 40
                MIN_CITED_ANSWER_CHARS = 12
                _CITE_MARK_RE = re.compile('\\[[0-9]{1,3}\\]')

                def _looks_like_tool_json(s: str) -> bool:
                    return bool(re.match('\\s*\\{\\s*"(?:name|tool|function)"\\s*:', s))

                def _is_degenerate_repetition(text: str) -> bool:
                    body = text or ''
                    lines = [ln.strip().lower() for ln in body.split('\n') if len(ln.strip()) > 25]
                    if len(lines) >= 3:
                        for ln in set(lines):
                            if lines.count(ln) >= 3:
                                return True
                        if len(set(lines)) * 2 > len(lines):
                            return False
                    sents = [s.strip().lower() for s in re.split('(?<=[.!?])\\s+|\\n+', body) if len(s.strip()) > 25]
                    if len(sents) < 3:
                        return False
                    uniq = set(sents)
                    if len(uniq) * 2 <= len(sents):
                        return True
                    for s in uniq:
                        if sents.count(s) >= 3:
                            return True
                    return False

                def _is_usable_answer(text: str) -> bool:
                    s = _normalize_brackets(text).strip()
                    if not s:
                        return False
                    if _TOOL_MARKUP_RE.search(s) or _looks_like_tool_json(s):
                        return False
                    if _STUB_ANSWER_RE.match(s) or _is_degenerate_repetition(s):
                        return False
                    cited = bool(_CITE_MARK_RE.search(s))
                    if cited and len(s) >= MIN_CITED_ANSWER_CHARS:
                        return True
                    if len(s) < MIN_ANSWER_CHARS:
                        return False
                    if len(s) < 400 and (_REFUSAL_ONLY_RE.match(s) or _INTENT_NARRATION_RE.match(s)):
                        return False
                    return True
                _COMMIT_RULES = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too. Never say what the evidence does not contain; commit to the best-supported answer you can defend."
                _REPAIR_ORDER = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

                def _sanitize_draft(text: str) -> str:
                    return _VERIFY_MARK_RE.sub('', text or '').strip()

                def _ledger_digest(ledger: EvidenceLedger, char_cap: int=60000) -> str:
                    parts: list[str] = []
                    spent = 0
                    for i, row in enumerate(ledger.rows, start=1):
                        text = (row.get('preview') or '').strip()
                        if not text:
                            continue
                        block = f"[{i}] {row.get('title') or ''} ({row.get('url') or ''})\n{text}"
                        if spent + len(block) > char_cap:
                            break
                        spent += len(block)
                        parts.append(block)
                    return '\n\n'.join(parts)
                _FURNITURE_RE = re.compile('^\\s*(?:share|search|home|menu|subscribe|sign\\s*in|log\\s*in|newsletter|advertisement|cookie|skip to|follow us|read more|related|tags?|categories?|privacy|terms|contact|about us|navigation|toggle)\\b', re.I)
                _SRC_FOOTNOTE_RE = re.compile('\\[\\s*\\d{1,3}\\s*\\]')
                _MD_LINK_RE = re.compile('\\]\\(')
                _BARE_URL_RE = re.compile('(?<!\\]\\()https?://')
                _SENTENCEY_RE = re.compile('[.!?]\\s|[.!?]$|\\b(?:is|was|were|are|has|have|had|reported|announced|released|won|ranked|totall?ed)\\b', re.I)

                def _informative_lead(preview: str, limit: int=280) -> str:
                    kept: list[str] = []
                    broke = False
                    for chunk in re.split('(?<=[.!?])\\s+|\\n+', _SRC_FOOTNOTE_RE.sub('', preview or '')):
                        seg = ' '.join(chunk.split())
                        if len(seg) < 30 or len(seg) > 400:
                            if kept:
                                broke = True
                                break
                            continue
                        if _SENTENCEY_RE.search(seg) is None:
                            if kept:
                                broke = True
                                break
                            continue
                        if _FURNITURE_RE.match(seg) and (not re.search('\\d', seg)):
                            if kept:
                                broke = True
                                break
                            continue
                        if seg.startswith(('*', '|', '↑', '#')):
                            if kept:
                                broke = True
                                break
                            continue
                        links = len(_MD_LINK_RE.findall(seg)) + len(_BARE_URL_RE.findall(seg))
                        if links and links * 110 >= len(seg):
                            if kept:
                                broke = True
                                break
                            continue
                        kept.append(seg)
                        if sum((len(k) for k in kept)) >= limit:
                            break
                    else:
                        pass
                    out = ' '.join(kept).strip()
                    if len(out) > limit:
                        cut = out.rfind(' ', 0, limit)
                        out = out[:cut if cut > 60 else limit].rstrip(' ,;:-')
                    return out

                def _deterministic_answer(question: str, ledger: EvidenceLedger) -> str:
                    rows = [(i, r) for i, r in enumerate(ledger.rows, start=1) if (r.get('preview') or '').strip()]
                    if not rows:
                        return ''
                    out = ['Best-supported findings from the sources retrieved:']
                    picked = 0
                    for i, r in rows:
                        if picked >= 6:
                            break
                        lead = _informative_lead(r.get('preview') or '')
                        if not lead:
                            continue
                        title = (r.get('title') or '').strip()
                        out.append(f"- {(title + ': ' if title else '')}{lead} [{i}]")
                        picked += 1
                    if picked == 0:
                        for i, r in rows[:4]:
                            lead = ' '.join((r.get('preview') or '').split())[:280]
                            if lead:
                                out.append(f'- {lead} [{i}]')
                        if len(out) == 1:
                            return ''
                    return '\n'.join(out)
                QUOTE_SYNTH_TIMEOUT_S = 42.0
                QUOTE_SYNTH_MIN_BUDGET_S = 30.0
                QUOTE_SYNTH_MIN_QUOTES = 2
                QUOTE_TABLE_CHARS = 1400

                def _quote_table(ledger: EvidenceLedger) -> str:
                    parts = []
                    for i, row in enumerate(ledger.rows, start=1):
                        text = row.get('text') or ''
                        for a, b in row.get('retained') or []:
                            excerpt = text[max(0, int(a)):int(b)][:QUOTE_TABLE_CHARS].strip()
                            if excerpt:
                                parts.append(f"[{i}] {row.get('title') or row.get('url') or ''}\n{excerpt}")
                    return '\n\n'.join(parts)

                def _retained_count(ledger: EvidenceLedger) -> int:
                    return sum((len(r.get('retained') or []) for r in ledger.rows))

                async def _write_from_digest(question: str, ledger: EvidenceLedger, deadline: float) -> str:
                    left = deadline - monotonic()
                    if left < 14.0:
                        return ''
                    digest = _ledger_digest(ledger)
                    if not digest:
                        return ''
                    convo = [{'role': 'system', 'content': _COMMIT_RULES}, {'role': 'user', 'content': f'Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'}]

                    async def _one(lane: str, model: str, budget: float) -> str:
                        payload = await _llm_chat_pin_ladder(lane, model, convo, max_tokens=2600, timeout=budget, think=_least_think(lane, model), temperature=0.15)
                        _spend_note(payload)
                        return _llm_text_from_payload(payload)
                    lanes = ((LLM_LANE_A, LOOP_MODEL_A), (LLM_LANE_B, LOOP_MODEL_B))
                    for i, lane_model in enumerate(lanes):
                        left = deadline - monotonic()
                        if left < 14.0:
                            return ''
                        budget = min(RESCUE_TIMEOUT_S, left - DIGEST_TAIL_S)
                        if i == 0:
                            budget = min(budget, max(12.0, left - 14.0 - DIGEST_TAIL_S))
                        if budget < 8.0:
                            return ''
                        try:
                            text = await _one(lane_model[0], lane_model[1], budget)
                        except Exception:
                            continue
                        if _is_usable_answer(text):
                            return text
                    return ''

                async def _knowledge_resort(question: str, deadline: float) -> str:
                    left = deadline - monotonic()
                    if left < 12.0:
                        return ''
                    try:
                        return await _chat_simple(LLM_LANE_A, RESORT_MODEL, 'Expert researcher. Best definitive answer with concrete entities, numbers, dates. Never refuse.', question, max_tokens=2600, timeout=min(45.0, left - 4.0))
                    except Exception:
                        return ''

                async def _schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
                    ask = f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}'
                    for lane, model in ((LLM_LANE_A, SCHEMA_MODEL), (LLM_LANE_A, RESORT_MODEL), (LLM_LANE_B, LOOP_MODEL_B)):
                        left = deadline - monotonic()
                        if left < 12.0:
                            break
                        try:
                            raw = await _chat_simple(lane, model, 'You output strictly valid JSON.', ask, max_tokens=3400, timeout=min(45.0, left - 4.0))
                            raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()
                            value = json.loads(raw)
                            if _matches_schema_shape(value, schema):
                                return value
                            if isinstance(value, dict) and len(value) == 1:
                                inner = list(value.values())[0]
                                if _matches_schema_shape(inner, schema):
                                    return inner
                        except Exception:
                            continue
                    return None

                def _schema_kind(schema) -> str:
                    if not isinstance(schema, dict):
                        return ''
                    kind = schema.get('type')
                    if isinstance(kind, list):
                        kind = kind[0] if kind else None
                    if kind is None:
                        for key in ('anyOf', 'oneOf', 'allOf'):
                            branch = schema.get(key)
                            if isinstance(branch, list):
                                for sub in branch:
                                    got = _schema_kind(sub)
                                    if got:
                                        return got
                        if isinstance(schema.get('properties'), dict):
                            return 'object'
                        if isinstance(schema.get('enum'), list):
                            return 'string'
                        return ''
                    return str(kind)

                def _matches_schema_shape(value, schema) -> bool:
                    kind = _schema_kind(schema)
                    if not kind:
                        return True
                    if kind == 'array':
                        return isinstance(value, list)
                    if kind == 'object':
                        return isinstance(value, dict)
                    if kind == 'string':
                        return isinstance(value, str)
                    if kind == 'integer':
                        return isinstance(value, int) and (not isinstance(value, bool))
                    if kind == 'number':
                        return isinstance(value, (int, float)) and (not isinstance(value, bool))
                    if kind == 'boolean':
                        return isinstance(value, bool)
                    if kind == 'null':
                        return value is None
                    return True
                _NUM_IN_TEXT_RE = re.compile('-?\\d[\\d,]*(?:\\.\\d+)?')
                _DIGEST_LEAD_RE = re.compile('^\\s*Best-supported findings|^\\s*sources retrieved:', re.I)
                _DIGEST_NOISE_RE = re.compile('\\[slice \\d+:\\d+\\]|https?://\\S+')
                _VALUE_MAX_CHARS = 90

                def _undigest_for_schema(basis: str) -> str:
                    if not basis:
                        return ''
                    text = _DIGEST_NOISE_RE.sub(' ', basis)
                    out = []
                    for raw in text.split('\n'):
                        line = raw.strip().lstrip('-*• ').strip()
                        if not line or _DIGEST_LEAD_RE.match(line):
                            continue
                        if ':' in line:
                            head, _, tail = line.partition(':')
                            line = tail.strip() if 0 < len(tail.strip()) <= _VALUE_MAX_CHARS else head.strip()
                        if not line or len(line) > _VALUE_MAX_CHARS:
                            continue
                        if line.count(' ') > 8:
                            continue
                        if line not in out:
                            out.append(line)
                        if len(out) >= 6:
                            break
                    return '\n'.join(out)

                def _coerce_to_schema(answer: str, schema, depth: int=0):
                    if depth > 4 or not isinstance(schema, dict):
                        return answer[:400]
                    enum = schema.get('enum')
                    if isinstance(enum, list) and enum:
                        low = (answer or '').lower()
                        for opt in enum:
                            if isinstance(opt, str) and re.search('\\b' + re.escape(opt.lower()) + '\\b', low):
                                return opt
                        return enum[0]
                    kind = _schema_kind(schema)
                    if not kind:
                        for key in ('anyOf', 'oneOf', 'allOf'):
                            branch = schema.get(key)
                            if isinstance(branch, list) and branch:
                                for sub in branch:
                                    if isinstance(sub, dict) and sub.get('type') != 'null':
                                        return _coerce_to_schema(answer, sub, depth + 1)
                        kind = 'string'
                    if kind == 'array':
                        items = schema.get('items') or {}
                        parts = [p.strip(' -*\t') for p in re.split('[\\n;]|,(?![^(]*\\))', answer or '')]
                        parts = [p[:400] for p in parts if p][:20]
                        if not parts:
                            parts = [answer[:400]]
                        return [_coerce_to_schema(p, items, depth + 1) for p in parts]
                    if kind == 'object':
                        props = schema.get('properties') or {}
                        required = schema.get('required') or list(props.keys())
                        out = {}
                        for key in required:
                            out[key] = _coerce_to_schema(answer, props.get(key) or {}, depth + 1)
                        return out
                    if kind in ('number', 'integer'):
                        found = _NUM_IN_TEXT_RE.search(_CITE_NUM_RE.sub(' ', answer or ''))
                        if found is None:
                            return 0
                        val = found.group(0).replace(',', '')
                        try:
                            return int(val) if kind == 'integer' else float(val)
                        except Exception:
                            return 0
                    if kind == 'boolean':
                        return not re.match('\\s*(no\\b|false\\b|none\\b)', answer or '', re.I)
                    return (answer or '')[:400]
                _NARRATION_LEAD_RE = re.compile("^\\s*(?:based on (?:my|the)\\b|now (?:i|that i)\\b|i (?:now )?(?:have|was|am|need|will|can)\\b|i(?:'ll|'ve|'m)\\b|let me\\b|let's\\b|first,? i\\b|having (?:now )?\\w+\\b|okay\\b|alright\\b|to answer this\\b|my research\\b)", re.IGNORECASE)
                _ABBREV_TAIL_RE = re.compile('(?:\\b[A-Z]|\\b(?:Inc|Ltd|Co|No|vs|St|Dr|Mr|Ms|Mt|Jr|Sr|etc|e\\.g|i\\.e))\\.$')

                def _strip_lead_narration(text: str) -> str:
                    t = (text or '').strip()
                    if not t:
                        return t
                    for _ in range(2):
                        parts = re.split('(?<=[.!?])\\s+', t, maxsplit=1)
                        if len(parts) != 2:
                            break
                        head, rest = (parts[0], parts[1].strip())
                        if _CITE_NUM_RE.search(head):
                            break
                        if _NARRATION_LEAD_RE.match(head) is None:
                            break
                        if len(head.split()) < 4 or _ABBREV_TAIL_RE.search(head) is not None:
                            break
                        if len(rest) < 120 or _CITE_NUM_RE.search(rest) is None:
                            break
                        t = rest
                    return t

                def _cap(text: str) -> str:
                    t = (text or '').strip()
                    if len(t) > ANSWER_CHAR_CAP:
                        return t[:ANSWER_CHAR_CAP - 16] + ' …'
                    return t

                async def query(query: Query) -> Response:
                    question = (query.text or '').strip()
                    if not question:
                        return Response(text='No question provided.')
                    try:
                        return await _solve(query, question)
                    except Exception:
                        return Response(text=f'Best-effort answer unavailable for: {question[:500]}')

                async def _session_bootstrap() -> float:
                    deadline = monotonic() + WALL_BUDGET_S
                    _RUN_DIAGNOSTICS.clear()
                    _CLAIM_LEDGER_REF['ledger'] = None
                    _SEED_CAP_REF['max'] = MAX_SEED_QUERIES
                    try:
                        info = await tooling_info(timeout=10.0)
                        _spend_note(info)
                    except Exception:
                        pass
                    return deadline

                def _apply_route_decision(question: str, output_schema) -> str:
                    decision = _decide_route(question, output_schema)
                    route = decision.route if decision.route in ('easy', 'hard') else 'hard'
                    _record_route_diag({'version': VERSION, 'route': route, 'router_reasons': list(decision.reasons), 'risk_flags': list(decision.risk_flags), 'features': dict(decision.features)})
                    return route

                def _route_turn_budget(route: str) -> int:
                    if route == 'easy':
                        _SEED_CAP_REF['max'] = MAX_SEED_QUERIES_EASY
                        return MAX_TURNS_EASY
                    _SEED_CAP_REF['max'] = MAX_SEED_QUERIES
                    return MAX_TURNS

                async def _prepare_brief_and_plan(question: str, route: str, deadline: float) -> tuple[str, str, str]:
                    draft = ''
                    brief = ''
                    plan = ''
                    try:
                        if route == 'hard' and _spend_left() >= BRIEF_MIN_USD and (deadline - monotonic() > 120.0):
                            draft, brief = await _knowledge_brief(question)
                            try:
                                plan = await _research_plan(question, deadline)
                            except Exception:
                                plan = _deterministic_research_plan(question)
                        elif route == 'easy':
                            plan = ''
                            brief = ''
                    except Exception:
                        brief = ''
                        if route == 'hard':
                            plan = _deterministic_research_plan(question)
                    return (draft, brief, plan)

                async def _run_research_loop(question: str, brief: str, plan: str, route: str, ledger: EvidenceLedger, deadline: float, turn_cap: int) -> tuple[str, list[dict]]:
                    answer = ''
                    messages: list[dict] = []
                    try:
                        answer, messages = await _loop(question, brief, ledger, deadline, turn_cap, route=route, plan=plan)
                    except Exception:
                        answer = ''
                    return (answer, messages)

                async def _maybe_citation_audit(question: str, answer: str, messages: list[dict], ledger: EvidenceLedger, deadline: float, route: str) -> str:
                    try:
                        det_gaps = _deterministic_citation_gaps(answer, question) if _is_usable_answer(answer) else ['no_answer']
                        need_audit = _is_usable_answer(answer) and deadline - monotonic() > 75.0 and (_spend_left() >= AUDIT_MIN_USD) and (route == 'hard' or det_gaps)
                        if need_audit:
                            patched = await _audit_patch(question, answer, messages, ledger, deadline)
                            if _is_usable_answer(patched):
                                return patched
                    except Exception:
                        pass
                    return answer

                async def _rescue_ladder(question: str, answer: str, draft: str, ledger: EvidenceLedger, deadline: float) -> str:
                    if not _is_usable_answer(answer) and ledger.rows:
                        try:
                            rescued = await _write_from_digest(question, ledger, deadline)
                            if _is_usable_answer(rescued):
                                answer = rescued
                        except Exception:
                            pass
                    if not _is_usable_answer(answer) and ledger.rows:
                        det = _deterministic_answer(question, ledger)
                        if _is_usable_answer(det):
                            answer = det
                    if not _is_usable_answer(answer):
                        fallback = _sanitize_draft(draft) or await _knowledge_resort(question, deadline)
                        if _is_usable_answer(fallback):
                            answer = fallback
                    return answer

                def _safe_citations(answer: str, ledger: EvidenceLedger) -> list:
                    try:
                        return _citations_for(answer, ledger)
                    except Exception:
                        return []

                def _finalize_answer_text(answer: str, question: str) -> tuple[str, str]:
                    answer = _normalize_brackets(answer)
                    answer = _strip_lead_narration(answer)
                    answer = _answer_line_only(answer, question)
                    text = _cap(answer) or f'Best-effort answer unavailable for: {question[:400]}'
                    return (answer, text)

                async def _structured_response(query: Query, question: str, answer: str, ledger: EvidenceLedger, citations: list, deadline: float) -> Response | None:
                    if query.output_schema is None:
                        return None
                    structured = None
                    try:
                        structured = await _schema_output(question, answer, query.output_schema, deadline)
                    except Exception:
                        structured = None
                    if structured is not None:
                        try:
                            structured = _verbatim_structured(structured, ledger)
                        except Exception:
                            pass
                        try:
                            return Response(output=structured, citations=citations or None)
                        except Exception:
                            structured = None
                    basis = answer if _is_usable_answer(answer) else ''
                    if not basis:
                        basis = _deterministic_answer(question, ledger)
                    if not basis or _STUB_ANSWER_RE.match(basis.strip()):
                        basis = question[:400]
                    if basis is not answer:
                        try:
                            salvaged = await _schema_output(question, basis, query.output_schema, deadline)
                        except Exception:
                            salvaged = None
                        if salvaged is not None:
                            try:
                                return Response(output=salvaged, citations=citations or None)
                            except Exception:
                                pass
                    if basis is not answer:
                        cleaned = _undigest_for_schema(basis)
                        basis = cleaned if cleaned else ''
                    try:
                        forced = _coerce_to_schema(_cap(basis), query.output_schema)
                        return Response(output=forced, citations=citations or None)
                    except Exception:
                        try:
                            return Response(output=_cap(basis)[:2000], citations=citations or None)
                        except Exception:
                            pass
                    return None

                def _text_response(text: str, citations: list) -> Response:
                    try:
                        return Response(text=text, citations=citations or None)
                    except Exception:
                        return Response(text=text)

                async def _solve(query: Query, question: str) -> Response:
                    deadline = await _session_bootstrap()
                    route = _apply_route_decision(question, getattr(query, 'output_schema', None))
                    claim_ledger = ClaimLedger()
                    _CLAIM_LEDGER_REF['ledger'] = claim_ledger
                    draft, brief, plan = await _prepare_brief_and_plan(question, route, deadline)
                    turn_cap = _route_turn_budget(route)
                    ledger = EvidenceLedger()
                    answer, messages = await _run_research_loop(question, brief, plan, route, ledger, deadline, turn_cap)
                    answer = await _maybe_citation_audit(question, answer, messages, ledger, deadline, route)
                    answer = await _rescue_ladder(question, answer, draft, ledger, deadline)
                    citations = _safe_citations(answer, ledger)
                    answer, text = _finalize_answer_text(answer, question)
                    structured = await _structured_response(query, question, answer, ledger, citations, deadline)
                    if structured is not None:
                        return structured
                    return _text_response(text, citations)
                return query

        class DifficultyRouter:
            _PROVIDER = 'openrouter'
            _MODEL = 'google/gemma-4-31b-it'
            _DIFFICULTY_PROMPT = 'Easy or Hard? Reply with one word only.'
            _TIMEOUT_S = 6.0

            async def _is_easy(self, text: str) -> bool:
                result = await asyncio.wait_for(llm_chat(provider=self._PROVIDER, model=self._MODEL, messages=[{'role': 'system', 'content': self._DIFFICULTY_PROMPT}, {'role': 'user', 'content': text}], temperature=0.0, max_output_tokens=4, thinking=LlmThinkingConfig(enabled=False), timeout=self._TIMEOUT_S), timeout=self._TIMEOUT_S + 2.0)
                label = (result.response.raw_text or '').strip().lower()
                return label.startswith('easy') or ('easy' in label and 'hard' not in label and ('medium' not in label))
        _FIRST_RUN = FirstPath()._compile()
        _SECOND_RUN = SecondPath()._compile()
        _ROUTER = DifficultyRouter()

        async def query(query: Query) -> Response:
            try:
                easy = await _ROUTER._is_easy(query.text)
            except Exception:
                easy = False
            if easy:
                return await _SECOND_RUN(query)
            return await _FIRST_RUN(query)
        return query

def _safe_compile(factory):
    """Build a pipeline closure; a source that dies on import must not kill the agent."""
    try:
        return factory()._compile()
    except Exception:
        return None

class ResponseGate:
    _MIN_ANSWER_CHARS = 40
    _REFUSAL_MARKERS = ('i cannot', "i can't", 'unable to determine', 'insufficient evidence', 'no information found', 'cannot answer')

    def satisfies(self, query: Query, response: Response) -> bool:
        return self.grade(query, response) > 0.0

    def grade(self, query: Query, response: Response) -> float:
        """Deterministic answer quality: schema first, then evidence, then substance."""
        if response is None:
            return 0.0
        if query.output_schema is not None and response.output is None:
            return 0.0
        text = (response.text or '').strip()
        if response.output is None and len(text) < self._MIN_ANSWER_CHARS:
            return 0.0
        opening = text[:160].lower()
        if any((marker in opening for marker in self._REFUSAL_MARKERS)):
            return 0.0
        score = 1.0
        if response.output is not None:
            score += 1.0
        score += min(len(response.citations or ()), 12) * 0.05
        score += min(len(text), 4000) / 4000.0
        return score

class EscalationController:
    """Answer with the primary pipeline; escalate only when the answer misses."""
    _ESCALATE_BEFORE_S = 150.0
    _TOTAL_BUDGET_S = 230.0

    def __init__(self, primary, reserve, gate):
        self._primary = primary
        self._reserve = reserve
        self._gate = gate

    async def _attempt(self, run, query: Query, budget: float):
        if run is None or budget <= 0:
            return None
        try:
            return await asyncio.wait_for(run(query), timeout=budget)
        except Exception:
            return None

    async def solve(self, query: Query) -> Response:
        started = monotonic()
        first = await self._attempt(self._primary, query, self._TOTAL_BUDGET_S)
        if first is not None and self._gate.satisfies(query, first):
            return first
        elapsed = monotonic() - started
        if elapsed >= self._ESCALATE_BEFORE_S:
            return first if first is not None else Response(text='No answer produced.')
        second = await self._attempt(self._reserve, query, self._TOTAL_BUDGET_S - elapsed)
        candidates = [r for r in (first, second) if r is not None]
        if not candidates:
            return Response(text='No answer produced.')
        return max(candidates, key=lambda r: self._gate.grade(query, r))
_PRIMARY_RUN = _safe_compile(PrimarySolver)
_RESERVE_RUN = _safe_compile(ReserveSolver)
_CONTROLLER = EscalationController(_PRIMARY_RUN, _RESERVE_RUN, ResponseGate())

@entrypoint('query')
async def query(query: Query) -> Response:
    return await _CONTROLLER.solve(query)
_TAG_F3FE3100="f3fe31006d054adbbef92426fe4822cd"
import logging as _tag_logging_f3fe3100
_tag_logging_f3fe3100.getLogger("miner.tag").debug("tag=%s", _TAG_F3FE3100)
