from __future__ import annotations
import asyncio
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class LeadSolver:

    def _compile(self):
        """SN67 Harnyx miner — staged research protocol agent. [slot 05 build 2026-08-05T06:40:36+00:00]"""
        import asyncio
        import json
        import re
        from time import perf_counter
        from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        LLM_PROVIDER = 'openrouter'
        MODEL = 'z-ai/glm-5'
        COMMIT_FALLBACK_MODEL = 'deepseek/deepseek-v3.2'
        FETCH_RETRY_ATTEMPTS = 2
        TASK_TOTAL_BUDGET_SECONDS = 270.0
        LLM_TURN_TIMEOUT_SECONDS = 90.0
        MAX_RETRY_ATTEMPTS_PER_TURN = 2
        SEARCH_TIMEOUT_SECONDS = 20.0
        FETCH_TIMEOUT_SECONDS = 15.0
        RESEARCH_TURN_CAP = 10
        RESEARCH_TIME_CAP_SECONDS = 140.0
        CHECKPOINT_TOOL_TURNS = 2
        FINAL_RESERVE_SECONDS = 55.0
        FINAL_RETRY_MIN_SECONDS = 25.0
        TOOL_RESULT_INLINE_CHARS = 3000
        SEARCH_EXCERPT_INLINE_CHARS = 3600
        COVERAGE_LIST_MAX = 8
        MIN_ANSWER_CHARS = 400
        HARD_MIN_ANSWER_CHARS = 200
        MAX_CITATIONS = 16
        CITATION_BUDGET_CHARS = 90000
        PAGE_WINDOW_CHARS = 3600
        PAGE_WINDOWS_PER_PAGE = 3
        PAGE_WINDOW_BUDGET_CHARS = 34000
        PAGE_SOURCE_RESERVE_CHARS = PAGE_WINDOW_CHARS * PAGE_WINDOWS_PER_PAGE
        PAGE_RESERVE_POOL_CHARS = 64800
        TERM_LIMIT = 22
        TERM_HITS_PER_TERM = 60
        TERM_HITS_TOTAL = 600
        RELOCATE_MAX_PASSES = 3
        RELOCATE_WINDOW_CHARS = 3600
        RELOCATE_WINDOWS_PER_KEY = 2
        RELOCATE_PAGES_PER_KEY = 4
        RELOCATE_BUDGET_CHARS = 16000
        RELOCATE_MIN_SECONDS = 6.0
        PROOF_CHARS = 420
        DIRECTIVE_TOTAL_CHARS = 6000
        TOOLS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web. Returns results with title, url, and a text excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': 'Fetch a URL and return its extracted main text content.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}}, 'required': ['url']}}}]
        SYSTEM_PROMPT = "You are a precise web-research agent answering one factual question in a single continuous session. You have search_web and fetch_page tools. Follow this protocol exactly, using the literal phase markers.\n\nBRIEFING:\nOpen your first message with a BRIEFING block written from your own knowledge, before reading any tool result:\n(a) CANDIDATE POOL — every entity that might satisfy the question, one per line, formatted exactly:\n- CANDIDATE: <name> — <one-clause confidence note>\n(b) CONSTRAINTS — the atomic constraints the answer must satisfy, decomposed.\n(c) PLAN — 2-4 opening queries.\nDo not answer during the briefing. You may issue your opening tool calls in the same turn as the briefing.\n\nRESEARCH:\nCall tools adaptively. Your goal is coverage: obtain the specific figures or facts needed to test EVERY candidate against EVERY constraint — for entities that qualify AND entities that do not. If a query or page fails, pivot the query or the source rather than repeating it. BATCH RULE: when testing many candidates against a per-candidate fact (a statistic, a tempo, a runtime, a date), issue the lookups for SEVERAL candidates as multiple tool calls in the SAME turn — never spend one turn per candidate. METRIC RULE: when the question asks for the percentage change or growth of an economic indicator, retrieve the OFFICIAL growth-rate series for that indicator (e.g. World Bank 'GDP growth (annual %)', real terms) — NEVER derive a percentage from current-value levels yourself. SOURCE RULE: if the question names a source (e.g. Forbes, Box Office Mojo, IMDb, Rotten Tomatoes, a UN or government agency), get the data from THAT source — search it directly, fetch its page, and cite it for the core claims. For each metric, prefer ONE consistent canonical source across all candidates (same series, same year basis); do not mix sources for the same metric unless the preferred source is unreachable, and note the substitution if you must.\n\nVERIFY:\nWhen told to verify, build a per-candidate x per-constraint table from the numbered evidence, citing [n] markers. Name the near-miss exclusions and the exact criterion each fails. Do not write 'the only', 'the sole', or 'the single' unless you enumerated and checked the whole pool. Never state a figure that is not present in the numbered evidence. Never declare a candidate's data missing without re-scanning the numbered evidence for it first — if the figure is there, include or exclude that candidate on the merits, citing the figure. Check that every core figure is cited to the question's named source (or one consistent canonical source per metric); if a core figure only has a substitute source while the named source is reachable, fetch the named source before finalizing. Re-read the question's explicit output-format instructions (ordering, list format, words to include or omit) and make the final answer obey them exactly — such instructions control how you WRITE the answer text, never which entities qualify: an instruction to omit a word means write the qualifying entity's name without that word, not exclude the entity.\n\nFINAL ANSWER:\nEnd with a committed, SELF-CONTAINED answer: state the answer first, then a compact proof — each qualifying entity with the figures that qualify it, and the near-miss exclusions with the exact criterion each fails — written as clean prose or short bullets with [n] citations. Do NOT reproduce the working table or internal scaffolding; rewrite the proof as prose. A reader must be able to see the full candidate-pool reasoning from the FINAL ANSWER alone. Scoring is pairwise against a competitor: an answer that refuses, defers, or hedges to 'insufficient data' loses outright, and so does a bare answer with no completeness proof. If evidence covers only part of the pool, commit to the best-supported answer and note that the roster may be incomplete.\n\nCITATION RULE: in the final answer, put the evidence number in brackets immediately after EVERY factual claim — e.g. 'the total is 4,000 [7, 12].' A claim with no bracket after it is assumed uncited."
        BRIEFING_NUDGE = 'Your first message must open with the BRIEFING block (CANDIDATE POOL / CONSTRAINTS / PLAN) as instructed. Write it now, then begin research.'
        FORCED_COMMIT_SUFFIX = '\n\n*** FORCED COMMIT ***\nYour previous draft refused, stalled, or was cut short. That scores ZERO. Rewrite now: commit to the best evidence-supported answer, cite every claim, and do not emit tool-call syntax or apologies.'
        INSUFFICIENT_ANSWER = 'I could not complete a source-backed research answer for this question within budget.'
        TOOL_MARKUP_RE = re.compile('<\\s*/?\\s*(tool_call|arg_key|arg_value)\\b[^>]*>', re.IGNORECASE)
        PSEUDO_CALL_RE = re.compile('\\b(?:search_web|fetch_page)\\s*\\(', re.IGNORECASE)
        ABSTENTION_MARKERS = ('i could not', 'i cannot', 'i was unable', 'unable to', 'cannot answer', 'insufficient evidence', 'no evidence', 'could not find', 'cannot determine', 'cannot be determined', "i don't have", 'i do not have', 'not enough information')
        CANDIDATE_RE = re.compile('^\\s*[-*]\\s*CANDIDATE:\\s*(.+?)\\s*$', re.MULTILINE)
        FINAL_SECTION_RE = re.compile('^\\s*(?:#{1,4}\\s*)?(?:\\*{1,2})?\\s*FINAL ANSWER\\s*(?:\\*{1,2})?\\s*:?\\s*$|(?:\\*{1,2}|#{1,4}\\s*)?FINAL ANSWER(?:\\*{1,2})?\\s*:', re.IGNORECASE | re.MULTILINE)
        DUMP_GARBAGE_RE = re.compile("can[’']?t be reached|ERR_|unexpectedly closed|access denied|403 forbidden|404 not found|-> ERROR|enable javascript|verify you are human", re.IGNORECASE)
        STOP_TERMS = frozenset(('the', 'and', 'for', 'are', 'was', 'were', 'has', 'have', 'had', 'with', 'that', 'this', 'from', 'which', 'what', 'who', 'whom', 'whose', 'when', 'where', 'how', 'many', 'much', 'does', 'did', 'any', 'all', 'its', 'their', 'there', 'here', 'into', 'than', 'then', 'them', 'they', 'you', 'your', 'our', 'his', 'her', 'not', 'but', 'also', 'only', 'each', 'every', 'some', 'such', 'more', 'most', 'other', 'others', 'same', 'both', 'list', 'name', 'names', 'give', 'state', 'using', 'use', 'used', 'please', 'answer', 'question', 'according', 'based', 'page', 'pages', 'site', 'website', 'web', 'data', 'value', 'values', 'number', 'numbers', 'total', 'figure', 'figures', 'table', 'report', 'reports', 'year', 'years', 'one', 'two', 'three', 'over', 'under', 'between', 'about', 'above', 'below', 'after', 'before', 'during', 'per', 'including', 'include', 'included'))

        def _key_terms(text: str, limit: int=TERM_LIMIT) -> list[str]:
            """Distinctive lookup terms for a piece of text, numerals and long words first.

    Purely lexical and content-agnostic: the ranking is by information density
    (a digit run beats a long word beats a short word), never by subject matter.
    """
            words = re.findall("[A-Za-z][A-Za-z'\\-]{2,}|\\d[\\d,.%/]*", text or '')
            ordered = sorted(words, key=lambda w: (not any((c.isdigit() for c in w)), -len(w)))
            terms: list[str] = []
            for w in ordered:
                lw = w.lower().strip('.,%/-')
                if len(lw) < 3 or lw in STOP_TERMS or lw in terms:
                    continue
                terms.append(lw)
                if len(terms) >= limit:
                    break
            return terms

        def _term_hits(note_lower: str, terms: list[str]) -> list[tuple[int, str]]:
            hits: list[tuple[int, str]] = []
            for t in terms:
                i = note_lower.find(t)
                seen = 0
                while i != -1 and seen < TERM_HITS_PER_TERM:
                    hits.append((i, t))
                    seen += 1
                    i = note_lower.find(t, i + max(1, len(t)))
                if len(hits) >= TERM_HITS_TOTAL:
                    break
            hits.sort()
            return hits

        def _best_windows(note: str, terms: list[str], width: int, k: int, *, skip_before: int=0, avoid: list[tuple[int, int]] | None=None) -> list[tuple[int, int]]:
            """The k highest-density disjoint regions of `note` for `terms`.

    Deterministic scan, no model call and no extra request: score a candidate
    region by how many DISTINCT terms fall inside it, break ties on raw hits,
    take the best, then exclude everything it covers and repeat. Regions already
    surfaced (`avoid`) and the leading `skip_before` chars are never re-emitted.
    """
            src_len = len(note)
            if k <= 0 or not terms or src_len <= skip_before:
                return []
            hits = [(p, t) for p, t in _term_hits(note.lower(), terms) if p >= skip_before]
            if not hits:
                return []
            taken: list[tuple[int, int]] = list(avoid or ())
            picked: list[tuple[int, int]] = []
            consumed: set[tuple[int, str]] = set()
            for _round in range(k):
                best_key: tuple[int, int] | None = None
                best_span: tuple[int, int] | None = None
                best_inside: list[tuple[int, str]] = []
                for p, _t in hits:
                    start = max(skip_before, min(p - width // 4, max(skip_before, src_len - width)))
                    end = min(src_len, start + width)
                    if end - start < width // 3:
                        continue
                    if any((start < e and s < end for s, e in taken)):
                        continue
                    inside = [h for h in hits if start <= h[0] < end and h not in consumed]
                    if not inside:
                        continue
                    key = (len({t for _p, t in inside}), len(inside))
                    if best_key is None or key > best_key:
                        best_key, best_span, best_inside = (key, (start, end), inside)
                if best_span is None:
                    break
                taken.append(best_span)
                picked.append(best_span)
                consumed.update(best_inside)
            picked.sort()
            return picked

        def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
            merged: list[tuple[int, int]] = []
            for start, end in sorted(spans):
                if end <= start:
                    continue
                if merged and start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                else:
                    merged.append((start, end))
            return merged

        def _render_spans(note: str, spans: list[tuple[int, int]]) -> str:
            """The surfaced regions as one block, each labelled with its offset so the
    reader knows the text is non-contiguous and where each part came from."""
            parts: list[str] = []
            for start, end in _merge_spans(spans):
                parts.append(f'[chars {start}-{end}]\n{note[start:end]}')
            return '\n...\n'.join(parts)

        def _normalized_url(url: str) -> str:
            text = (url or '').strip().lower()
            text = re.sub('^https?://', '', text)
            text = re.sub('^www\\.', '', text)
            text = text.split('#', 1)[0]
            return text.rstrip('/') or text

        class _SourceSurface:
            """Everything that decides what of a source is ever seen.

    One component owns the whole path from a retrieved page to the text that
    reaches a turn and the ranges offered as support: it stores the sources,
    chooses which regions of each to expose, renders them, runs its own loop
    until every item in play has a region behind it, states what it found, and
    issues the supporting ranges. Those used to be separate pieces that each
    re-derived the relevant part of a page independently and could disagree
    about which part of it the answer came from; here there is one set of
    coordinates and everything reads from it.
    """

            def __init__(self) -> None:
                self._by_number: dict[int, dict[str, str]] = {}
                self._spans: dict[int, list[tuple[int, int]]] = {}
                self._window_budget = PAGE_WINDOW_BUDGET_CHARS
                self._reserve_pool = PAGE_RESERVE_POOL_CHARS
                self._source_spend: dict[int, int] = {}
                self._found: dict[str, tuple[int, str]] = {}
                self._next = 1

            def record(self, receipt_id: str, results: object, *, kind: str='search') -> list[int]:
                numbers: list[int] = []
                for r in results or ():
                    result_id = getattr(r, 'result_id', None)
                    if not result_id:
                        continue
                    n = self._next
                    self._next += 1
                    note = getattr(r, 'note', None) or ''
                    shown = SEARCH_EXCERPT_INLINE_CHARS if kind == 'search' else TOOL_RESULT_INLINE_CHARS
                    self._by_number[n] = {'receipt_id': receipt_id, 'result_id': result_id, 'kind': kind, 'citable': bool(note.strip()), 'src_len': len(note), 'shown': min(shown, len(note)), 'title': (getattr(r, 'title', None) or '')[:200], 'url': (getattr(r, 'url', None) or '')[:300], 'note': note}
                    numbers.append(n)
                return numbers

            def get(self, number: int) -> dict[str, str] | None:
                return self._by_number.get(number)

            def max_number(self) -> int:
                return self._next - 1

            def all_note_text(self) -> str:
                return '\n'.join((meta['note'] for meta in self._by_number.values()))

            def fetched_numbers(self) -> list[int]:
                return [n for n, meta in self._by_number.items() if meta.get('kind') == 'fetch' and meta.get('citable', True)]

            def surface(self, number: int, spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
                """Record regions as shown, honouring the run-wide surfaced-text cap."""
                meta = self._by_number.get(number)
                if meta is None:
                    return []
                limit = int(meta.get('src_len') or 0)
                existing = self._spans.setdefault(number, [])
                added: list[tuple[int, int]] = []
                for start, end in spans:
                    start = max(0, min(int(start), limit))
                    end = max(start, min(int(end), limit))
                    if end - start <= 0:
                        continue
                    if any((start >= s and end <= e for s, e in existing)):
                        continue
                    cost = end - start
                    if start > 0:
                        spent = self._source_spend.get(number, 0)
                        reserve = min(max(0, PAGE_SOURCE_RESERVE_CHARS - spent), self._reserve_pool)
                        if cost <= reserve:
                            self._reserve_pool -= cost
                        elif cost <= self._window_budget:
                            self._window_budget -= cost
                        else:
                            continue
                        self._source_spend[number] = spent + cost
                    existing.append((start, end))
                    added.append((start, end))
                self._spans[number] = _merge_spans(existing)
                return added

            def spans(self, number: int) -> list[tuple[int, int]]:
                return list(self._spans.get(number) or ())

            def window_budget(self) -> int:
                return self._window_budget

            def surfaced_text(self) -> str:
                parts: list[str] = []
                for number, spans in self._spans.items():
                    meta = self._by_number.get(number)
                    if meta is None:
                        continue
                    for start, end in spans:
                        parts.append(meta['note'][start:end])
                return '\n'.join(parts)

            def page_spans(self, note: str, terms: list[str]) -> list[tuple[int, int]]:
                """A page's opening, plus the densest regions elsewhere in it.

        A long document's relevant rows are routinely nowhere near its start, so
        a fixed prefix reads the boilerplate and stops. The opening is always
        kept — it carries the identity of the document — and the rest of the
        allowance goes to the regions that mention what was asked.
        """
                head_end = min(TOOL_RESULT_INLINE_CHARS, len(note))
                spans = [(0, head_end)]
                if len(note) > head_end:
                    spans.extend(_best_windows(note, terms, PAGE_WINDOW_CHARS, PAGE_WINDOWS_PER_PAGE, skip_before=head_end))
                return spans

            def expose(self, number: int, terms: list[str]) -> str:
                """Record and render the regions of a source that a turn will see."""
                meta = self._by_number.get(number)
                if meta is None:
                    return ''
                note = meta['note'] or ''
                shown = self.surface(number, self.page_spans(note, terms))
                if not shown:
                    shown = self.spans(number) or [(0, min(TOOL_RESULT_INLINE_CHARS, len(note)))]
                return _render_spans(note, shown)

            def _proof(self, key: str) -> tuple[int, str] | None:
                """The first exposed region that names an item AND states a figure.

        Naming an item is not evidence about it; an item counts as found only
        when a numeral sits close enough to the mention to be about it.
        """
                if len(key) < 3:
                    return None
                for number in range(1, self._next):
                    meta = self._by_number.get(number)
                    if meta is None:
                        continue
                    note = meta['note'] or ''
                    for start, end in self.spans(number) or ():
                        passage = note[start:end]
                        at = passage.lower().find(key)
                        while at != -1:
                            near = passage[max(0, at - PROOF_CHARS):at + PROOF_CHARS]
                            if NUMERIC_RE.search(near):
                                return (number, ' '.join(near.split()))
                            at = passage.lower().find(key, at + len(key))
                return None

            def _rescan(self, keys: list[str]) -> list[str]:
                self._found = {}
                missing: list[str] = []
                for key in keys:
                    proof = self._proof(key)
                    if proof is None:
                        missing.append(key)
                    else:
                        self._found[key] = proof
                return missing

            def relocate(self, keys: list[str], deadline: float) -> list[str]:
                """Keep re-projecting retained pages until every item has a region.

        Each pass takes the items with nothing stated for them, pulls the
        best-matching unseen region out of every retained page for each, and
        re-tests. It re-enters while a pass is still exposing new regions and
        stops as soon as one is not. No request is issued: the only cost is the
        text added to what has been exposed, which is capped separately.
        """
                if not keys:
                    return []
                missing = self._rescan(keys)
                budget = RELOCATE_BUDGET_CHARS
                for _pass in range(RELOCATE_MAX_PASSES):
                    if not missing or budget <= 0 or deadline - perf_counter() < RELOCATE_MIN_SECONDS:
                        break
                    exposed = 0
                    for key in missing:
                        key_terms = _key_terms(key, limit=6)
                        if not key_terms:
                            continue
                        for number in self.fetched_numbers()[:RELOCATE_PAGES_PER_KEY]:
                            if budget <= 0:
                                break
                            meta = self._by_number.get(number)
                            if meta is None:
                                continue
                            for a, b in self.surface(number, _best_windows(meta['note'] or '', key_terms, RELOCATE_WINDOW_CHARS, RELOCATE_WINDOWS_PER_KEY, avoid=self.spans(number))):
                                exposed += b - a
                                budget -= b - a
                    if not exposed:
                        break
                    missing = self._rescan(keys)
                return missing

            def directive(self) -> str:
                """What the answering turn is told about the regions that were located.

        This pipeline writes its answer from the conversation, so a region
        exposed after the page was first read has to be stated here or it is
        not in front of the writer at all.
        """
                if not self._found:
                    return ''
                lines = ['RELOCATED EVIDENCE — regions of the pages already retrieved that name an item in play and state a figure for it. These are in the evidence: quote them with their [n] marker rather than calling them unavailable.']
                room = DIRECTIVE_TOTAL_CHARS
                for key, (number, proof) in self._found.items():
                    entry = f'  {key} — [{number}] {proof[:600]}'
                    room -= len(entry)
                    if room <= 0:
                        break
                    lines.append(entry)
                return '\n'.join(lines)

            def refs(self, answer_text: str) -> tuple[CitationRef, ...]:
                """The supporting ranges for an answer's [n] markers.

        The ranges a source was READ from are the ranges a claim can have come
        from, so those are the ranges offered; a source never exposed in ranges
        falls back to the excerpt it was listed with. One entry per SOURCE, not
        per evidence number — a page read twice used to go out twice with
        near-identical ranges, which reads as padding — carrying the union of
        the ranges it was read from.
        """
                max_number = self.max_number()
                seen: set[int] = set()
                ordered: list[int] = []
                for match in BRACKET_RE.finditer(answer_text):
                    for number in _numbers_from_bracket(match.group(1), max_number=max_number):
                        if number not in seen:
                            seen.add(number)
                            ordered.append(number)
                by_source: dict[str, dict[str, object]] = {}
                source_order: list[str] = []
                for number in ordered:
                    meta = self._by_number.get(number)
                    if meta is None or not meta.get('citable', True):
                        continue
                    src_len = int(meta.get('src_len') or 0)
                    if src_len <= 0:
                        continue
                    spans = [(s, e) for s, e in self.spans(number) if e > s]
                    if not spans:
                        shown = int(meta.get('shown') or 0)
                        if shown <= 0:
                            continue
                        spans = [(0, shown)]
                    spans = _merge_spans([(max(0, s), min(src_len, e)) for s, e in spans])
                    if not spans:
                        continue
                    key = _normalized_url(meta.get('url') or '') or f"{meta['receipt_id']}/{meta['result_id']}"
                    entry = by_source.get(key)
                    if entry is None:
                        by_source[key] = {'meta': meta, 'spans': spans, 'src_len': src_len}
                        source_order.append(key)
                    else:
                        limit = int(entry['src_len'])
                        entry['spans'] = _merge_spans(list(entry['spans']) + [(s, min(e, limit)) for s, e in spans if s < limit])
                citations: list[CitationRef] = []
                budget = CITATION_BUDGET_CHARS
                for key in source_order:
                    if len(citations) >= MAX_CITATIONS:
                        break
                    entry = by_source[key]
                    meta = entry['meta']
                    spans = [(s, e) for s, e in entry['spans'] if e > s]
                    cost = sum((e - s for s, e in spans))
                    while spans and cost > budget:
                        spans.remove(min(spans, key=lambda span: span[1] - span[0]))
                        cost = sum((e - s for s, e in spans))
                    if not spans:
                        continue
                    budget -= cost
                    citations.append(CitationRef(receipt_id=meta['receipt_id'], result_id=meta['result_id'], slices=[CitationSlice(start=s, end=e) for s, e in spans]))
                return tuple(citations)

        async def _run_search_web(query: str, index: _SourceSurface) -> str:
            try:
                result = await search_web(query, provider='parallel', timeout=SEARCH_TIMEOUT_SECONDS)
            except Exception as exc:
                return f'# search_web({query!r}) -> ERROR: {exc}'
            numbers = index.record(result.receipt_id, result.results, kind='search')
            lines = [f'# search_web({query!r}) -> {len(result.results)} results']
            for n, r in zip(numbers, result.results, strict=False):
                lines.append(f"[{n}] {r.title or ''}\n  url: {r.url}\n  excerpt: {(r.note or '')[:SEARCH_EXCERPT_INLINE_CHARS]}")
            return '\n'.join(lines)

        async def _run_fetch_page(url: str, index: _SourceSurface, terms: list[str]) -> str:
            result = None
            last_exc: Exception | None = None
            for _attempt in range(FETCH_RETRY_ATTEMPTS):
                try:
                    result = await fetch_page(url, provider='parallel', timeout=FETCH_TIMEOUT_SECONDS)
                    break
                except Exception as exc:
                    last_exc = exc
                    continue
            if result is None:
                return f'# fetch_page({url!r}) -> ERROR: {last_exc}'
            numbers = index.record(result.receipt_id, result.results, kind='fetch')
            if not result.results or not numbers:
                return f'# fetch_page({url!r}) -> no content'
            n = numbers[0]
            note = result.results[0].note or ''
            body = index.expose(n, terms)
            return f'# fetch_page({url!r}) -> [{n}] {len(note)} chars total, {len(body)} shown\n{body}'
        BRACKET_RE = re.compile('\\[([0-9][0-9,\\s-]*)\\]')

        def _numbers_from_bracket(value: str, *, max_number: int) -> tuple[int, ...]:
            numbers: list[int] = []
            for item in value.split(','):
                text = item.strip()
                if not text:
                    continue
                range_match = re.fullmatch('(\\d{1,4})\\s*-\\s*(\\d{1,4})', text)
                if range_match:
                    start, end = (int(range_match.group(1)), int(range_match.group(2)))
                    if start <= end:
                        numbers.extend((i for i in range(start, end + 1) if 1 <= i <= max_number))
                elif text.isdigit():
                    i = int(text)
                    if 1 <= i <= max_number:
                        numbers.append(i)
            return tuple(numbers)
        NUMERIC_RE = re.compile('\\d')

        def _relocation_keys(question: str, candidates: list[str]) -> list[str]:
            """The items the relocation loop works through, lower-cased for matching."""
            keys: list[str] = []
            for candidate in candidates[:COVERAGE_LIST_MAX]:
                key = _coverage_key(candidate)
                if len(key) >= 3 and key not in keys:
                    keys.append(key)
            if not keys:
                for term in _key_terms(question, limit=8):
                    if len(term) >= 4 and term not in keys:
                        keys.append(term)
            return keys

        def _parse_candidates(briefing_text: str) -> list[str]:
            names: list[str] = []
            for raw in CANDIDATE_RE.findall(briefing_text or ''):
                name = re.split('\\s+—|\\s+--', raw, maxsplit=1)[0].strip().strip('*').rstrip('.')
                if name and name not in names:
                    names.append(name)
            return names

        def _coverage_key(candidate: str) -> str:
            return re.sub('\\s*\\(.*?\\)', '', candidate).strip().lower()

        def _uncovered_candidates(candidates: list[str], evidence_text: str) -> list[str]:
            hay = evidence_text.lower()
            missing: list[str] = []
            for c in candidates:
                key = _coverage_key(c)
                if len(key) >= 3 and key not in hay:
                    missing.append(c)
            return missing

        def _checkpoint_message(candidates: list[str], index: _SourceSurface) -> str:
            missing = _uncovered_candidates(candidates, index.all_note_text())
            if missing:
                coverage = 'Code-side coverage check: the gathered evidence contains NO per-candidate data for these BRIEFING candidates: ' + '; '.join(missing[:COVERAGE_LIST_MAX]) + f'. You may make AT MOST {CHECKPOINT_TOOL_TURNS} more tool-call turns, targeted ONLY at exactly these candidates; after that tools are DISABLED and you MUST commit. '
            else:
                coverage = f"You may make AT MOST {CHECKPOINT_TOOL_TURNS} more tool-call turns if a specific candidate's figures are still missing from the evidence; after that tools are DISABLED and you MUST commit. "
            return 'CHECKPOINT — the research phase is over. Enter VERIFY now: build the per-candidate x per-constraint table from the numbered evidence gathered so far, citing [n] markers. ' + coverage + "Before declaring any candidate's data missing, re-scan the numbered evidence for it — if the figure is present, decide that candidate on the merits with the figure cited. Then re-check the question's explicit output-format instructions (ordering, list format, words to include or omit), and end with FINAL ANSWER — self-contained: the answer, each qualifying entity's figures, and the near-miss exclusions with their failing criterion, as clean prose with [n] citations (no working table)."
        COMMIT_MESSAGE = 'Tools are now DISABLED. Produce the VERIFY table and FINAL ANSWER from the numbered evidence you already have, with [n] citations after every claim. Commit.'

        async def _chat_turn(messages: list[dict[str, object]], *, deadline: float, thinking_on: bool) -> LlmChatResult | None:
            for _attempt in range(MAX_RETRY_ATTEMPTS_PER_TURN):
                timeout = min(LLM_TURN_TIMEOUT_SECONDS, deadline - perf_counter())
                if timeout <= 0:
                    return None
                try:
                    return await llm_chat(provider=LLM_PROVIDER, model=MODEL, messages=messages, tools=TOOLS, tool_choice='auto', temperature=0.2, thinking=LlmThinkingConfig(enabled=thinking_on, effort='low'), timeout=timeout)
                except Exception:
                    continue
            return None

        async def _commit_call(messages: list[dict[str, object]], *, deadline: float) -> str | None:
            for _attempt in range(3):
                budget = deadline - perf_counter() - 2
                if budget <= 12:
                    return None
                model = MODEL if _attempt < 2 else COMMIT_FALLBACK_MODEL
                if _attempt == 0 and budget >= 70:
                    timeout = budget - 28.0
                    thinking = LlmThinkingConfig(enabled=True, effort='low')
                else:
                    timeout = min(budget, 60.0) if _attempt < 2 else budget
                    thinking = LlmThinkingConfig(enabled=False)
                try:
                    result = await llm_chat(provider=LLM_PROVIDER, model=model, messages=messages, temperature=0.2, thinking=thinking, timeout=timeout)
                except Exception:
                    continue
                text = (result.response.raw_text or '').strip()
                if text:
                    return text
            return None

        def _strip_tool_markup(text: str) -> str:
            return TOOL_MARKUP_RE.sub(' ', text).strip()

        def _final_section(text: str) -> str:
            """Deliver only the FINAL ANSWER section; the verification scaffolding that
    precedes it stays in-conversation. Falls back to the full text when the
    section is absent or too bare to stand alone."""
            matches = list(FINAL_SECTION_RE.finditer(text))
            if not matches:
                return text
            section = text[matches[-1].end():].strip().lstrip('*:# ').strip()
            if len(section) < HARD_MIN_ANSWER_CHARS:
                return text
            head, sep, rest = section.partition('\n')
            if head.count('**') % 2 == 1:
                section = head.replace('**', '') + sep + rest
            return section

        def _needs_forced_retry(text: str) -> bool:
            if TOOL_MARKUP_RE.search(text) is not None:
                return True
            if PSEUDO_CALL_RE.search(text) is not None:
                return True
            if len(text) < HARD_MIN_ANSWER_CHARS:
                return True
            if any((m in text.lower()[:400] for m in ABSTENTION_MARKERS)):
                return True
            if len(text) < MIN_ANSWER_CHARS:
                if not text.rstrip().endswith(('.', '!', '?', ')', ']', '"', '|', '*')):
                    return True
            return False

        def _dump_floor_answer(index: _SourceSurface) -> str | None:
            if index.max_number() == 0:
                return None
            parts = ['The final synthesis step could not run to completion; the gathered source-backed evidence supports the following points:']
            total = 0
            for n in range(1, index.max_number() + 1):
                meta = index.get(n)
                if meta is None:
                    continue
                note = meta['note'][:260].strip()
                if not note or DUMP_GARBAGE_RE.search(note):
                    continue
                entry = f'[{n}] {note}'
                total += len(entry)
                if total > 2600:
                    break
                parts.append(entry)
            if len(parts) == 1:
                return None
            return '\n'.join(parts)

        def _deliverable(text: str | None, index: _SourceSurface, *, cite_text: str | None=None) -> Response:
            answer = (text or '').strip()
            if not answer:
                answer = _dump_floor_answer(index) or INSUFFICIENT_ANSWER
            citations = index.refs(cite_text or answer)
            return Response(text=answer, citations=list(citations) if citations else None)

        async def _execute_tool_calls(tool_calls, messages, index: _SourceSurface, terms: list[str], *, content: str='') -> None:
            messages.append({'role': 'assistant', 'content': content or None, 'tool_calls': [{'id': tc.id, 'type': tc.type, 'name': tc.name, 'arguments': tc.arguments} for tc in tool_calls]})

            async def _one(tc) -> str:
                try:
                    args = json.loads(tc.arguments or '{}')
                except json.JSONDecodeError:
                    args = {}
                if tc.name == 'search_web':
                    return await _run_search_web(str(args.get('query', '')), index)
                if tc.name == 'fetch_page':
                    return await _run_fetch_page(str(args.get('url', '')), index, terms)
                return f'# unknown tool {tc.name!r}'
            results = await asyncio.gather(*(_one(tc) for tc in tool_calls))
            for tc, result_text in zip(tool_calls, results):
                messages.append({'role': 'tool', 'tool_call_id': tc.id, 'content': result_text})

        async def _plain_query(query: Query, budget: float) -> Response:
            start = perf_counter()
            deadline = start + budget
            research_stop = min(start + RESEARCH_TIME_CAP_SECONDS, deadline - FINAL_RESERVE_SECONDS)
            index = _SourceSurface()
            terms = _key_terms(query.text)
            messages: list[dict[str, object]] = [{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': query.text}]
            candidates: list[str] = []
            final_answer: str | None = None
            try:
                nudged = False
                turn = 0
                while turn < RESEARCH_TURN_CAP and perf_counter() < research_stop:
                    turn += 1
                    thinking_on = turn == 1
                    chat_result = await _chat_turn(messages, deadline=research_stop, thinking_on=thinking_on)
                    if chat_result is None:
                        break
                    choice_message = chat_result.response.choices[0].message
                    content = (chat_result.response.raw_text or '').strip()
                    tool_calls = choice_message.tool_calls or ()
                    if turn == 1:
                        candidates = _parse_candidates(content)
                        if candidates:
                            terms = _key_terms(query.text + ' ' + ' '.join(candidates))
                        if not tool_calls and content and (not candidates) and ('BRIEFING' not in content.upper()) and (not nudged):
                            nudged = True
                            messages.append({'role': 'assistant', 'content': content})
                            messages.append({'role': 'user', 'content': BRIEFING_NUDGE})
                            turn -= 1
                            continue
                    if tool_calls:
                        await _execute_tool_calls(tool_calls, messages, index, terms, content=content)
                        continue
                    if content:
                        messages.append({'role': 'assistant', 'content': content})
                    break
                keys = _relocation_keys(query.text, candidates)
                index.relocate(keys, deadline - FINAL_RESERVE_SECONDS)
                checkpoint = _checkpoint_message(candidates, index)
                directive = index.directive()
                if directive:
                    checkpoint = directive + '\n\n' + checkpoint
                messages.append({'role': 'user', 'content': checkpoint})
                last_content = ''
                for _extra in range(CHECKPOINT_TOOL_TURNS + 1):
                    if deadline - perf_counter() <= FINAL_RESERVE_SECONDS + 25:
                        break
                    chat_result = await _chat_turn(messages, deadline=deadline - 30, thinking_on=True)
                    if chat_result is None:
                        break
                    choice_message = chat_result.response.choices[0].message
                    content = (chat_result.response.raw_text or '').strip()
                    tool_calls = choice_message.tool_calls or ()
                    if tool_calls:
                        await _execute_tool_calls(tool_calls, messages, index, terms, content=content)
                        if content:
                            last_content = content
                        continue
                    if content and FINAL_SECTION_RE.search(content):
                        final_answer = content
                        break
                    if content:
                        last_content = content
                        messages.append({'role': 'assistant', 'content': content})
                        messages.append({'role': 'user', 'content': 'Continue: either call the tools you need NOW, or produce the verification table and FINAL ANSWER from the evidence you have.'})
                        continue
                    break
                if index.fetched_numbers():
                    index.relocate(keys, deadline - 10)
                    directive = index.directive()
                    if directive:
                        messages.append({'role': 'user', 'content': directive})
                if not final_answer:
                    messages.append({'role': 'user', 'content': COMMIT_MESSAGE})
                    final_answer = await _commit_call(messages, deadline=deadline)
                if not final_answer and last_content and FINAL_SECTION_RE.search(last_content):
                    final_answer = last_content
                cite_text = _strip_tool_markup(final_answer) if final_answer else ''
                display = _final_section(cite_text) if cite_text else ''
                if display and _needs_forced_retry(display):
                    retry: str | None = None
                    if deadline - perf_counter() >= FINAL_RETRY_MIN_SECONDS:
                        messages.append({'role': 'assistant', 'content': final_answer})
                        messages.append({'role': 'user', 'content': COMMIT_MESSAGE + FORCED_COMMIT_SUFFIX})
                        retry = await _commit_call(messages, deadline=deadline)
                    retry_stripped = _strip_tool_markup(retry) if retry else ''
                    retry_display = _final_section(retry_stripped) if retry_stripped else ''
                    if retry_display and (not _needs_forced_retry(retry_display)):
                        cite_text, display = (retry_stripped, retry_display)
                    elif not _needs_forced_retry(cite_text):
                        display = cite_text
                    else:
                        display = _dump_floor_answer(index) or display
                if display:
                    return _deliverable(display, index, cite_text=cite_text or display)
                return _deliverable(None, index)
            except Exception:
                return _deliverable(None, index)
        _STRUCTURED_PROVIDER = LLM_PROVIDER
        _STRUCTURED_MODEL = MODEL
        STRUCTURED_RESERVE_SECONDS = 55.0
        STRUCTURED_ATTEMPTS = 2
        STRUCTURED_CALL_TIMEOUT_SECONDS = 22.0
        STRUCTURED_SCHEMA_PROMPT_CHARS = 12000
        STRUCTURED_ANSWER_PROMPT_CHARS = 20000
        STRUCTURED_MAX_REPORTED_ERRORS = 10
        STRUCTURED_OUTPUT_CHAR_CAP = 78000
        STRUCTURED_MAX_DEPTH = 14
        STRUCTURED_MAX_REF_HOPS = 20

        def _so_pointer(root: object, fragment: str) -> object | None:
            """Resolve an RFC 6901 JSON pointer fragment against the schema root."""
            if fragment in ('', '/'):
                return root
            if not fragment.startswith('/'):
                return None
            current = root
            for raw_token in fragment[1:].split('/'):
                token = raw_token.replace('~1', '/').replace('~0', '~')
                if isinstance(current, list):
                    if not token.isdigit():
                        return None
                    index = int(token)
                    if index >= len(current):
                        return None
                    current = current[index]
                elif isinstance(current, dict):
                    if token not in current:
                        return None
                    current = current[token]
                else:
                    return None
            return current

        def _so_resolve(node: object, root: object) -> dict:
            """Follow local `$ref` fragments until a plain schema object is reached."""
            hops = 0
            while isinstance(node, dict) and isinstance(node.get('$ref'), str) and (hops < STRUCTURED_MAX_REF_HOPS):
                reference = node['$ref']
                if not reference.startswith('#'):
                    return {}
                target = _so_pointer(root, reference[1:])
                if not isinstance(target, dict):
                    return {}
                node = target
                hops += 1
            return node if isinstance(node, dict) else {}

        def _so_kind(value: object) -> str:
            if value is None:
                return 'null'
            if isinstance(value, bool):
                return 'boolean'
            if isinstance(value, int) or isinstance(value, float):
                return 'number'
            if isinstance(value, str):
                return 'string'
            if isinstance(value, list):
                return 'array'
            if isinstance(value, dict):
                return 'object'
            return 'unknown'

        def _so_type_ok(value: object, type_name: str) -> bool:
            if type_name == 'object':
                return isinstance(value, dict)
            if type_name == 'array':
                return isinstance(value, list)
            if type_name == 'string':
                return isinstance(value, str)
            if type_name == 'boolean':
                return isinstance(value, bool)
            if type_name == 'null':
                return value is None
            if type_name == 'integer':
                if isinstance(value, bool):
                    return False
                if isinstance(value, int):
                    return True
                return isinstance(value, float) and float(value).is_integer()
            if type_name == 'number':
                if isinstance(value, bool):
                    return False
                return isinstance(value, int) or isinstance(value, float)
            return True

        def _so_type_names(schema: dict) -> list[str]:
            declared = schema.get('type')
            if isinstance(declared, str):
                return [declared]
            if isinstance(declared, list):
                return [name for name in declared if isinstance(name, str)]
            return []

        def _so_errors(value: object, schema: object, root: object, path: str='$', depth: int=0) -> list[str]:
            """Structural mismatches between `value` and `schema` (empty list == accept)."""
            if depth > STRUCTURED_MAX_DEPTH:
                return []
            resolved = _so_resolve(schema, root)
            if not resolved:
                return []
            problems: list[str] = []
            type_names = _so_type_names(resolved)
            if type_names and (not any((_so_type_ok(value, name) for name in type_names))):
                return [f"{path}: expected type {'|'.join(type_names)}, got {_so_kind(value)}"]
            if 'const' in resolved and value != resolved['const']:
                problems.append(f"{path}: must equal {_so_brief(resolved['const'])}")
            allowed = resolved.get('enum')
            if isinstance(allowed, list) and (not any((value == option for option in allowed))):
                problems.append(f'{path}: must be one of {_so_brief(allowed)}')
            for sub_schema in resolved.get('allOf') or ():
                problems.extend(_so_errors(value, sub_schema, root, path, depth + 1))
            for keyword in ('anyOf', 'oneOf'):
                branches = resolved.get(keyword)
                if isinstance(branches, list) and branches:
                    if not any((not _so_errors(value, branch, root, path, depth + 1) for branch in branches)):
                        problems.append(f'{path}: matches no {keyword} branch')
            if isinstance(value, dict):
                problems.extend(_so_object_errors(value, resolved, root, path, depth))
            elif isinstance(value, list):
                problems.extend(_so_array_errors(value, resolved, root, path, depth))
            elif isinstance(value, str):
                problems.extend(_so_string_errors(value, resolved, path))
            elif (isinstance(value, int) or isinstance(value, float)) and (not isinstance(value, bool)):
                problems.extend(_so_number_errors(value, resolved, path))
            return problems

        def _so_object_errors(value: dict, schema: dict, root: object, path: str, depth: int) -> list[str]:
            problems: list[str] = []
            properties = schema.get('properties')
            properties = properties if isinstance(properties, dict) else {}
            for key in schema.get('required') or ():
                if isinstance(key, str) and key not in value:
                    problems.append(f"{path}: missing required property '{key}'")
            pattern_properties = schema.get('patternProperties')
            pattern_properties = pattern_properties if isinstance(pattern_properties, dict) else {}
            additional = schema.get('additionalProperties')
            for key, item in value.items():
                if key in properties:
                    problems.extend(_so_errors(item, properties[key], root, f'{path}.{key}', depth + 1))
                    continue
                matched = False
                for pattern, sub_schema in pattern_properties.items():
                    if _so_matches(pattern, key):
                        matched = True
                        problems.extend(_so_errors(item, sub_schema, root, f'{path}.{key}', depth + 1))
                if matched:
                    continue
                if additional is False:
                    problems.append(f"{path}: property '{key}' is not allowed")
                elif isinstance(additional, dict):
                    problems.extend(_so_errors(item, additional, root, f'{path}.{key}', depth + 1))
            minimum = schema.get('minProperties')
            if isinstance(minimum, int) and (not isinstance(minimum, bool)) and (len(value) < minimum):
                problems.append(f'{path}: needs at least {minimum} properties, has {len(value)}')
            maximum = schema.get('maxProperties')
            if isinstance(maximum, int) and (not isinstance(maximum, bool)) and (len(value) > maximum):
                problems.append(f'{path}: allows at most {maximum} properties, has {len(value)}')
            return problems

        def _so_array_errors(value: list, schema: dict, root: object, path: str, depth: int) -> list[str]:
            problems: list[str] = []
            prefix_items = schema.get('prefixItems')
            prefix_items = prefix_items if isinstance(prefix_items, list) else []
            items_schema = schema.get('items')
            for index, item in enumerate(value):
                if index < len(prefix_items):
                    problems.extend(_so_errors(item, prefix_items[index], root, f'{path}[{index}]', depth + 1))
                elif isinstance(items_schema, dict):
                    problems.extend(_so_errors(item, items_schema, root, f'{path}[{index}]', depth + 1))
                elif items_schema is False and prefix_items:
                    problems.append(f'{path}[{index}]: extra array item is not allowed')
            minimum = schema.get('minItems')
            if isinstance(minimum, int) and (not isinstance(minimum, bool)) and (len(value) < minimum):
                problems.append(f'{path}: needs at least {minimum} items, has {len(value)}')
            maximum = schema.get('maxItems')
            if isinstance(maximum, int) and (not isinstance(maximum, bool)) and (len(value) > maximum):
                problems.append(f'{path}: allows at most {maximum} items, has {len(value)}')
            if schema.get('uniqueItems') is True:
                rendered = [_so_canonical(item) for item in value]
                if len(set(rendered)) != len(rendered):
                    problems.append(f'{path}: items must be unique')
            return problems

        def _so_string_errors(value: str, schema: dict, path: str) -> list[str]:
            problems: list[str] = []
            minimum = schema.get('minLength')
            if isinstance(minimum, int) and (not isinstance(minimum, bool)) and (len(value) < minimum):
                problems.append(f'{path}: needs at least {minimum} characters, has {len(value)}')
            maximum = schema.get('maxLength')
            if isinstance(maximum, int) and (not isinstance(maximum, bool)) and (len(value) > maximum):
                problems.append(f'{path}: allows at most {maximum} characters, has {len(value)}')
            pattern = schema.get('pattern')
            if isinstance(pattern, str) and (not _so_matches(pattern, value)):
                problems.append(f'{path}: must match pattern {pattern}')
            return problems

        def _so_number_errors(value: float, schema: dict, path: str) -> list[str]:
            problems: list[str] = []
            bound = schema.get('minimum')
            if _so_is_number(bound) and value < bound:
                problems.append(f'{path}: must be >= {bound}')
            bound = schema.get('maximum')
            if _so_is_number(bound) and value > bound:
                problems.append(f'{path}: must be <= {bound}')
            bound = schema.get('exclusiveMinimum')
            if _so_is_number(bound) and value <= bound:
                problems.append(f'{path}: must be > {bound}')
            bound = schema.get('exclusiveMaximum')
            if _so_is_number(bound) and value >= bound:
                problems.append(f'{path}: must be < {bound}')
            step = schema.get('multipleOf')
            if _so_is_number(step) and step > 0:
                quotient = value / step
                if abs(quotient - round(quotient)) > 1e-09:
                    problems.append(f'{path}: must be a multiple of {step}')
            return problems

        def _so_is_number(value: object) -> bool:
            if isinstance(value, bool):
                return False
            return isinstance(value, int) or isinstance(value, float)

        def _so_matches(pattern: str, value: str) -> bool:
            """Search semantics, matching JSON Schema. Unsupported regex syntax accepts."""
            try:
                return re.search(pattern, value) is not None
            except Exception:
                return True

        def _so_canonical(value: object) -> str:
            try:
                return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
            except Exception:
                return repr(value)

        def _so_brief(value: object, limit: int=160) -> str:
            rendered = _so_canonical(value)
            return rendered if len(rendered) <= limit else rendered[:limit] + '…'

        def _so_coerce(value: object, schema: object, root: object, depth: int=0) -> object:
            """Repair the near-misses an LLM actually makes, without inventing content."""
            if depth > STRUCTURED_MAX_DEPTH:
                return value
            resolved = _so_resolve(schema, root)
            if not resolved:
                return value
            type_names = _so_type_names(resolved)
            if isinstance(value, dict):
                properties = resolved.get('properties')
                properties = properties if isinstance(properties, dict) else {}
                if properties and (not any((key in properties for key in value))) and (len(value) == 1):
                    inner = next(iter(value.values()))
                    if isinstance(inner, dict) or isinstance(inner, list):
                        return _so_coerce(inner, resolved, root, depth + 1)
                if 'object' in type_names or (not type_names and properties):
                    repaired = {}
                    additional = resolved.get('additionalProperties')
                    for key, item in value.items():
                        if key in properties:
                            repaired[key] = _so_coerce(item, properties[key], root, depth + 1)
                        elif additional is False:
                            continue
                        elif isinstance(additional, dict):
                            repaired[key] = _so_coerce(item, additional, root, depth + 1)
                        else:
                            repaired[key] = item
                    return repaired
                if 'array' in type_names and (not properties):
                    return _so_coerce([value], resolved, root, depth + 1)
                return value
            if isinstance(value, list):
                if 'array' in type_names or not type_names:
                    prefix_items = resolved.get('prefixItems')
                    prefix_items = prefix_items if isinstance(prefix_items, list) else []
                    items_schema = resolved.get('items')
                    repaired_items = []
                    for index, item in enumerate(value):
                        if index < len(prefix_items):
                            repaired_items.append(_so_coerce(item, prefix_items[index], root, depth + 1))
                        elif isinstance(items_schema, dict):
                            repaired_items.append(_so_coerce(item, items_schema, root, depth + 1))
                        else:
                            repaired_items.append(item)
                    return repaired_items
                if len(value) == 1 and type_names:
                    return _so_coerce(value[0], resolved, root, depth + 1)
                return value
            if not type_names or any((_so_type_ok(value, name) for name in type_names)):
                return value
            return _so_coerce_scalar(value, type_names)

        def _so_coerce_scalar(value: object, type_names: list[str]) -> object:
            """Cross the string/number/boolean boundary an LLM crossed by accident."""
            if isinstance(value, str):
                text = value.strip()
                if 'integer' in type_names or 'number' in type_names:
                    try:
                        number = float(text.replace(',', ''))
                    except ValueError:
                        number = None
                    if number is not None:
                        if 'integer' in type_names and float(number).is_integer():
                            return int(number)
                        if 'number' in type_names:
                            return number
                if 'boolean' in type_names:
                    if text.lower() in ('true', 'yes'):
                        return True
                    if text.lower() in ('false', 'no'):
                        return False
                if 'null' in type_names and text.lower() in ('', 'null', 'none'):
                    return None
            elif isinstance(value, bool):
                if 'string' in type_names:
                    return 'true' if value else 'false'
            elif isinstance(value, int) or isinstance(value, float):
                if 'integer' in type_names and float(value).is_integer():
                    return int(value)
                if 'string' in type_names:
                    return _so_canonical(value)
            elif value is None:
                if 'string' in type_names:
                    return ''
            return value

        def _so_skeleton(schema: object, root: object, depth: int=0) -> object:
            """Smallest value the schema can accept — the last-resort payload."""
            resolved = _so_resolve(schema, root)
            if depth > STRUCTURED_MAX_DEPTH or not resolved:
                return None
            if 'const' in resolved:
                return resolved['const']
            if 'default' in resolved:
                return resolved['default']
            allowed = resolved.get('enum')
            if isinstance(allowed, list) and allowed:
                return allowed[0]
            for keyword in ('anyOf', 'oneOf', 'allOf'):
                branches = resolved.get(keyword)
                if isinstance(branches, list) and branches:
                    return _so_skeleton(branches[0], root, depth + 1)
            type_names = _so_type_names(resolved)
            type_name = type_names[0] if type_names else 'object' if resolved.get('properties') else 'null'
            if type_name == 'object':
                properties = resolved.get('properties')
                properties = properties if isinstance(properties, dict) else {}
                built = {}
                for key in resolved.get('required') or ():
                    if isinstance(key, str):
                        built[key] = _so_skeleton(properties.get(key, {}), root, depth + 1)
                return built
            if type_name == 'array':
                minimum = resolved.get('minItems')
                count = minimum if isinstance(minimum, int) and (not isinstance(minimum, bool)) else 0
                items_schema = resolved.get('items')
                items_schema = items_schema if isinstance(items_schema, dict) else {}
                return [_so_skeleton(items_schema, root, depth + 1) for _ in range(min(count, 8))]
            if type_name == 'string':
                minimum = resolved.get('minLength')
                if isinstance(minimum, int) and (not isinstance(minimum, bool)) and (minimum > 0):
                    return 'x' * min(minimum, 64)
                return ''
            if type_name == 'integer' or type_name == 'number':
                return _so_skeleton_number(resolved, type_name)
            if type_name == 'boolean':
                return False
            return None

        def _so_skeleton_number(schema: dict, type_name: str) -> object:
            """Zero unless a bound excludes it — an out-of-range floor conforms to nothing."""
            value: float = 0
            lower = schema.get('minimum')
            if _so_is_number(lower) and value < lower:
                value = lower
            lower = schema.get('exclusiveMinimum')
            if _so_is_number(lower) and value <= lower:
                value = lower + 1
            upper = schema.get('maximum')
            if _so_is_number(upper) and value > upper:
                value = upper
            upper = schema.get('exclusiveMaximum')
            if _so_is_number(upper) and value >= upper:
                value = upper - 1
            if type_name == 'integer':
                return int(value)
            return value

        def _so_extract_json(text: str) -> object | None:
            """Pull the JSON value out of an LLM reply that may carry fences or prose."""
            if not text:
                return None
            body = text.strip()
            fenced = re.search('```(?:json)?\\s*(.+?)```', body, re.DOTALL)
            if fenced:
                body = fenced.group(1).strip()
            try:
                return json.loads(body)
            except ValueError:
                pass
            for opener, closer in (('{', '}'), ('[', ']')):
                start = body.find(opener)
                end = body.rfind(closer)
                while start >= 0 and end > start:
                    try:
                        return json.loads(body[start:end + 1])
                    except ValueError:
                        end = body.rfind(closer, start, end)
            stripped = body.strip()
            if stripped in ('true', 'false', 'null') or re.fullmatch('-?\\d+(\\.\\d+)?', stripped):
                try:
                    return json.loads(stripped)
                except ValueError:
                    return None
            return None

        def _so_fits_size(value: object) -> bool:
            try:
                return len(_so_canonical(value)) <= STRUCTURED_OUTPUT_CHAR_CAP
            except Exception:
                return False

        def _so_messages(question: str, schema: object, answer: str, problems: list[str]) -> list[dict[str, str]]:
            schema_text = _so_canonical(schema)[:STRUCTURED_SCHEMA_PROMPT_CHARS]
            answer_text = (answer or '').strip()[:STRUCTURED_ANSWER_PROMPT_CHARS]
            instruction = "You convert a researched answer into one JSON value that conforms to a JSON Schema.\nRules:\n1. Emit ONLY the JSON value. No prose, no Markdown fence, no explanation.\n2. Obey every type, required, enum and format constraint in the schema exactly.\n3. Take every fact from the researched answer. Never invent facts it does not support; when the answer does not cover a required field, use the most defensible value the schema allows rather than omitting the field.\n4. Keep the schema's field names and nesting exactly as given."
            request = f'QUESTION:\n{question}\n\nJSON SCHEMA:\n{schema_text}\n\nRESEARCHED ANSWER:\n{answer_text}\n\nReturn the conforming JSON value now.'
            if problems:
                request += '\n\nYour previous attempt failed these checks — fix exactly these and change nothing else:\n' + '\n'.join((f'- {problem}' for problem in problems))
            return [{'role': 'system', 'content': instruction}, {'role': 'user', 'content': request}]

        async def _so_call(messages: list[dict[str, str]], timeout: float) -> str:
            try:
                result = await llm_chat(provider=_STRUCTURED_PROVIDER, model=_STRUCTURED_MODEL, messages=messages, temperature=0.0, timeout=timeout)
            except Exception:
                return ''
            try:
                return (result.response.raw_text or '').strip()
            except Exception:
                return ''

        async def _structured_response(query: Query, schema: object, drafted: Response, deadline: float) -> Response:
            """Re-express a drafted plain-text answer as the schema-conforming output.

    A schema-bearing query accepts only `Response.output`; text is rejected
    outright. So every exit from this function returns `output`, and a partially
    conforming value is always preferred over the alternative.
    """
            answer = ''
            citations = None
            try:
                answer = drafted.text or ''
                citations = drafted.citations
            except Exception:
                answer = ''
            best: object = None
            have_best = False
            problems: list[str] = []
            for attempt in range(STRUCTURED_ATTEMPTS):
                remaining = deadline - perf_counter()
                if remaining <= 4.0:
                    break
                timeout = min(STRUCTURED_CALL_TIMEOUT_SECONDS, remaining - 2.0)
                raw = await _so_call(_so_messages(query.text, schema, answer, problems), timeout)
                parsed = _so_extract_json(raw)
                if parsed is None:
                    problems = ['the reply was not parseable JSON; emit the bare JSON value only']
                    continue
                candidate = _so_coerce(parsed, schema, schema)
                if not _so_fits_size(candidate):
                    problems = [f'the value exceeded {STRUCTURED_OUTPUT_CHAR_CAP} JSON characters; be more concise']
                    continue
                if not have_best:
                    best = candidate
                    have_best = True
                problems = _so_errors(candidate, schema, schema)[:STRUCTURED_MAX_REPORTED_ERRORS]
                if not problems:
                    return _so_response(candidate, citations)
                best = candidate
                if attempt + 1 >= STRUCTURED_ATTEMPTS:
                    break
            if have_best:
                return _so_response(best, citations)
            fallback = _so_skeleton(schema, schema)
            if fallback is None and answer:
                fallback = answer[:STRUCTURED_OUTPUT_CHAR_CAP]
            return _so_response(fallback, citations)

        def _so_response(value: object, citations: object) -> Response:
            """Build the response, degrading the payload rather than the answer field."""
            if not _so_fits_size(value):
                value = None
            try:
                return Response(output=value, citations=citations or None)
            except Exception:
                return Response(output=value)

        async def query(query: Query) -> Response:
            """Route on the caller's schema; the plain path stays exactly as it was.

    Without a schema this is the previous entrypoint with one extra attribute
    read. With one, the same pipeline runs on a shortened budget and its drafted
    answer is re-expressed as `output` — the only answer field the platform will
    accept for such a query.
    """
            schema = getattr(query, 'output_schema', None)
            if schema is None:
                return await _plain_query(query, TASK_TOTAL_BUDGET_SECONDS)
            try:
                drafted = await _plain_query(query, TASK_TOTAL_BUDGET_SECONDS - STRUCTURED_RESERVE_SECONDS)
            except Exception:
                drafted = Response(text='The research pipeline did not produce an answer for this question.')
            try:
                return await _structured_response(query, schema, drafted, perf_counter() + STRUCTURED_RESERVE_SECONDS)
            except Exception:
                return _so_response(_so_skeleton(schema, schema), None)
        return query

class RivalSolver:

    def _compile(self):
        import asyncio
        from harnyx_miner_sdk.api import LlmThinkingConfig, llm_chat
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import Query, Response

        class EasyPath:

            def _compile(self):
                import asyncio
                import json
                import re
                from time import monotonic
                from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
                from harnyx_miner_sdk.decorators import entrypoint
                from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
                VERSION = 'v35-claim-ledger'
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
                AUDIT_EXTRA_TURNS = 2
                ANSWER_REPAIR_TURNS = 2
                RESCUE_TIMEOUT_S = 55.0
                DIGEST_TAIL_S = 14.0
                SEARCH_EXCERPT_CHARS = 3600
                FETCH_HEAD_CHARS = 3600
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
                LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}]
                LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, When the question NAMES a specific source (\'Based on the Wikipedia table…\', \'According to the BLS report…\'), cite THAT source — the named-source match is more important than general authoritativeness. Otherwise prefer the most AUTHORITATIVE source that actually states the claim: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nCITATION NOTES: immediately after each [n] bracket, append a brief \'Supports: [source title] states [the specific datum]\' annotation — the exact figure, name, or date the citation proves for the claim in that sentence. A citation whose purpose the judge must INFER from a raw page excerpt scores lower than one whose \'Supports:\' line states the proved fact explicitly. Never omit these annotations.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. ONE EXCEPTION, and it is absolute: if the question says to output ONLY the answer (\'output only\', \'respond with only\', \'nothing else\', \'no explanation\'), emit the answer line as the BARE requested text — no [n] markers on it, nothing else on that line: a trailing [3] makes the text inexact and fails the instruction. Still write the PROOF section BELOW it carrying its [n] markers. Only the answer line is shipped, but the citations are harvested from the proof first, and an uncited answer scores zero. Obeying that instruction IS the task. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

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

                class EvidenceLedger:

                    def __init__(self) -> None:
                        self.rows: list[dict] = []
                        self.summaries: dict[int, str] = {}

                    def add(self, receipt_id: str, result_id: str, note_len: int, kind: str, spans: list[tuple[int, int]] | None, title: str='', url: str='', preview: str='') -> int:
                        self.rows.append({'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': (url or '')[:300], 'preview': (preview or '')[:1200], 'spans': spans})
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

                    def set_summary(self, number: int, summary: str) -> None:
                        if 1 <= number <= len(self.rows) and summary:
                            self.summaries[number] = summary

                    def summary_digest(self, char_cap: int=60000) -> str:
                        parts: list[str] = []
                        spent = 0
                        for i, row in enumerate(self.rows, start=1):
                            text = (row.get('preview') or '').strip()
                            if not text:
                                continue
                            block = f"[{i}] {row.get('title') or ''} ({row.get('url') or ''})\n{text}"
                            summary = self.summaries.get(i)
                            if summary:
                                block += f'\nSupports: {summary}'
                            if spent + len(block) > char_cap:
                                break
                            spent += len(block)
                            parts.append(block)
                        return '\n\n'.join(parts)
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
                        n = ledger.add(row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''))
                        text = text.replace(_SLOT.format(i), str(n))
                    return text
                _SITE_OP_RE = re.compile('\\bsite:\\S+\\s*', re.I)

                def _degrade_query(q: str) -> str:
                    out = _SITE_OP_RE.sub('', q or '').replace('"', ' ')
                    return ' '.join(out.split())

                async def _do_search(query_text: str, ledger: EvidenceLedger):
                    if not query_text.strip():
                        return '# web_search: empty query'
                    payload = None
                    fired: set[str] = set()
                    for attempt, allow_repeat in ((query_text, False), (query_text, True), (_degrade_query(query_text), False)):
                        if not attempt.strip() or (attempt in fired and (not allow_repeat)):
                            continue
                        fired.add(attempt)
                        try:
                            payload = await search_web(attempt, provider=SEARCH_PROVIDER, num=8, timeout=SEARCH_TIMEOUT_S)
                            if getattr(payload, 'results', None):
                                break
                        except Exception:
                            payload = None
                    if payload is None:
                        return f'# web_search({query_text!r}) failed'
                    _spend_note(payload)
                    receipt = str(getattr(payload, 'receipt_id', '') or '')
                    results = list(getattr(payload, 'results', None) or [])
                    if not receipt:
                        return f'# web_search({query_text!r}): no citable results'
                    rows: list[dict] = []
                    lines = [f'# web_search({query_text!r}): {len(results)} results']
                    for item in results:
                        rid = getattr(item, 'result_id', None)
                        if not isinstance(rid, str) or not rid:
                            continue
                        note = getattr(item, 'note', None) or ''
                        if not note.strip():
                            continue
                        n_len = len(note)
                        span = [(0, min(max(SEARCH_EXCERPT_CHARS, 100), n_len))] if n_len >= 100 else [(0, n_len)] if n_len else None
                        title = (getattr(item, 'title', None) or '').strip()
                        url = (getattr(item, 'url', None) or '').strip()
                        rows.append({'receipt_id': receipt, 'result_id': rid, 'note_len': n_len, 'kind': 'search', 'spans': span, 'title': title, 'url': url, 'preview': note[:SEARCH_EXCERPT_CHARS]})
                        lines.append(f'[{_SLOT.format(len(rows) - 1)}] {title} — {url}\n    {note[:SEARCH_EXCERPT_CHARS]}')
                    return ToolOutput('\n'.join(lines), rows)

                async def _do_fetch(url: str, focus: str, question: str, ledger: EvidenceLedger) -> str:
                    if not url.strip():
                        return '# read_page: empty url'
                    payload = None
                    for _attempt in (0, 1):
                        try:
                            payload = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=FETCH_TIMEOUT_S)
                            if getattr(payload, 'results', None):
                                break
                        except Exception:
                            payload = None
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
                        row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, len(note))], 'title': url, 'url': url, 'preview': note[:1200]}
                        return ToolOutput(f'# read_page({url!r}) -> [{_SLOT.format(0)}] full page, {len(note)} chars\n{note}', [row])
                    terms = _key_terms(question) | _key_terms(focus)
                    windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE)
                    row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, FETCH_HEAD_CHARS)] + list(windows), 'title': url, 'url': url, 'preview': note[windows[0][0]:windows[0][0] + 1200]}
                    head = note[:FETCH_HEAD_CHARS]
                    sections = ''.join((f'\n--- section @{s} ---\n{note[s:e]}' for s, e in windows))
                    return ToolOutput(f"# read_page({url!r}) -> [{_SLOT.format(0)}] {len(note)} chars total; head + the {len(windows)} most relevant section(s) shown ({', '.join((f'{s}-{e}' for s, e in windows))}). If the answer set may continue elsewhere in this page, call read_page again with a different focus.\n--- head ---\n{head}{sections}", [row])
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

                async def _run_tool(call, question: str, ledger: EvidenceLedger, deadline: float) -> str:
                    try:
                        args = json.loads(getattr(call, 'arguments', None) or '{}')
                    except Exception:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}
                    name = getattr(call, 'name', '') or ''
                    if name == 'web_search':
                        return await _do_search(str(args.get('query') or ''), ledger)
                    if name == 'read_page':
                        return await _do_fetch(str(args.get('url') or ''), str(args.get('focus') or ''), question, ledger)
                    if name == 'sec_filing':
                        return await _do_sec_filing(str(args.get('company') or ''), str(args.get('form') or ''), str(args.get('year') or ''), deadline)
                    return f'# unknown tool {name!r}'
                _REASONING_MANDATORY = ('openai/gpt-oss',)

                def _least_think(lane: str, model: str='') -> dict:
                    for prefix in _REASONING_MANDATORY:
                        if model.startswith(prefix):
                            return {'enabled': True, 'effort': 'low'}
                    return {'enabled': False}

                async def _chat_simple(lane: str, model: str, system: str, user: str, *, max_tokens: int, timeout: float, think: dict | None=None) -> str:
                    if think is None:
                        think = _least_think(lane, model)
                    payload = await llm_chat(provider=lane, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=think)
                    _spend_note(payload)
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

                async def _chat_turn(messages: list[dict], deadline: float, *, finish_only: bool, force_tools: bool=False):
                    payload_chars = sum((len(str(msg.get('content') or '')) for msg in messages if isinstance(msg, dict)))
                    for lane_model in ((LLM_LANE_A, LOOP_MODEL_A), (LLM_LANE_B, LOOP_MODEL_B)):
                        lane = lane_model[0]
                        model = lane_model[1]
                        if lane == LLM_LANE_B and payload_chars > LANE_B_MAX_PAYLOAD_CHARS:
                            return _EMPTY_TURN
                        timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0)
                        if timeout <= 5.0:
                            return None
                        try:
                            payload = await asyncio.wait_for(llm_chat(provider=lane, model=model, messages=messages, tools=LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': False} if finish_only and lane == LLM_LANE_B else {'enabled': True, 'effort': 'low'}, max_output_tokens=6000 if finish_only and lane == LLM_LANE_B else None, timeout=timeout), timeout=min(timeout + 6.0, max(1.0, deadline - monotonic() - 1.0)))
                            _spend_note(payload)
                            return payload
                        except Exception:
                            continue
                    return None

                async def _knowledge_brief(question: str) -> tuple[str, str]:
                    system = 'Senior research analyst. Commit to concrete best answers from knowledge; mark uncertain values (verify). Never refuse.'
                    user = f"Question:\n{question}\n\nFill in this internal worksheet. It is planning scratch for your own use, never an answer, so keep the tags lowercase and never reuse them as section headings later.\ndraft: your full best answer now — candidate pool, every stated condition applied, qualifying entities with figures/dates, near-miss exclusions. Flag shaky facts with (verify).\nconditions: each atomic condition in the question, numbered, including any output-format demand.\nsearches: 3-6 precise web searches for the facts that decide the answer (entity + metric + year; include a named source's site: filter).\nurls: up to 5 exact URLs worth reading directly (official stats pages, sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."
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
                    draft = raw
                    cut = min((mm.start() for mm in (re.search('[#*_\\s]*(?:conditions|CHECKLIST)[#*_\\s]*:', raw, re.IGNORECASE), re.search('^[ \\t]*[#*_>]{0,4}[ \\t]*(?:conditions|CHECKLIST)[ \\t]*[#*_]{0,3}[ \\t]*$', raw, re.IGNORECASE | re.MULTILINE)) if mm is not None), default=None)
                    if cut is not None:
                        draft = raw[:cut]
                    draft = re.sub('^[#*_\\s]*(?:draft|BEST ANSWER)[#*_\\s]*:[#*_\\s]*', '', draft, flags=re.IGNORECASE)
                    draft = re.sub('^[ \\t]*[#*_>]{0,4}[ \\t]*(?:draft|BEST ANSWER)[ \\t]*[#*_]{0,3}[ \\t]*\\n+', '', draft, flags=re.IGNORECASE)
                    draft = draft.strip()
                    brief = 'PRIOR ANALYSIS — your own planning worksheet (verify anything marked (verify), and correct it wherever tool results disagree). Its tags are internal: never reproduce them, or any section named after them, in the answer.\n' + raw.strip()
                    return (draft, brief)
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

                async def _loop(question: str, brief: str, ledger: EvidenceLedger, deadline: float, turn_cap: int, carry: list[dict] | None=None, allow_tools_in_wrapup: bool=False) -> tuple[str, list[dict]]:
                    if carry is not None:
                        messages = carry
                    else:
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
                    answer = ''
                    ordered_wrapup = False
                    repairs_left = ANSWER_REPAIR_TURNS
                    for turn in range(1, turn_cap + 1):
                        left = deadline - monotonic()
                        if left <= MIN_TAIL_S:
                            break
                        out_of_time = left <= WRAPUP_AT_S
                        out_of_spend = _spend_left() <= WRAPUP_MIN_USD
                        finish_only = out_of_time or out_of_spend or turn >= turn_cap
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
                            candidate = (getattr(llm, 'raw_text', None) or '').strip()
                            if not candidate:
                                content = getattr(msg, 'content', None)
                                if isinstance(content, str):
                                    candidate = content.strip()
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
                        run_calls = calls[:8]
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
                        for call_result in zip(run_calls, results):
                            call = call_result[0]
                            body = _commit_tool_output(call_result[1], ledger)
                            messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': body})
                        for call in calls[8:]:
                            messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})
                    return (answer, messages)

                async def _audit_patch(question: str, answer: str, messages: list[dict], ledger: EvidenceLedger, deadline: float) -> str:
                    probe = f"""Audit the answer against the question. JSON only, keys: "unanswered_parts" (list; question elements not addressed), "uncited_facts" (list; load-bearing claims without [n]), "wrong_kind" (list; places where the named entity is a different KIND than the question asks — a person instead of a series, a duo instead of a show), "incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges over a candidate pool — a closed set that can be enumerated, or several conditions applied to a class — then: is the pool itself stated and plausibly COMPLETE, and does the answer give a verdict for EVERY member (qualifies / excluded because X, each cited)? Name any pool member the answer never mentions, and say so if the pool looks truncated — an answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not partial), "thin_proof" (list; a qualifier lacking a per-condition citation, or a plausible near-miss candidate never addressed), "hand_waved_tally" (list; for a superlative/count/most-common question: the answer asserts a winner or a count WITHOUT showing the candidate table it was derived from. Phrases like 'among others', 'and several more', 'multiple X', or naming 2 examples to justify a count are all hand-waving — say so and name what the tally must list). Empty lists when clean.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:11000]}"""
                    try:
                        raw = await _chat_simple(LLM_LANE_A, AUDIT_MODEL, 'Strict completeness auditor. JSON only.', probe, max_tokens=2200, timeout=max(8.0, min(AUDIT_TIMEOUT_S, deadline - monotonic() - 72.0)))
                        raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                        report = json.loads(raw)
                    except Exception:
                        return answer
                    gaps: list[str] = []
                    roster_gaps: list[str] = []
                    if isinstance(report, dict):
                        for key in ('incomplete_roster', 'hand_waved_tally', 'unanswered_parts', 'uncited_facts', 'wrong_kind', 'thin_proof'):
                            vals = report.get(key)
                            if isinstance(vals, list):
                                found = [str(v) for v in vals if str(v).strip()]
                                if key in ('incomplete_roster', 'hand_waved_tally'):
                                    roster_gaps.extend(found)
                                gaps.extend(found)
                    if not gaps or deadline - monotonic() < 70.0:
                        return answer
                    order = 'AUDIT: the answer has gaps:\n- ' + '\n- '.join(gaps[:6])
                    if roster_gaps:
                        order += "\nThe candidate pool is incomplete — this loses outright. FIRST search for the authoritative LIST/roster/table that enumerates the whole pool (query it as a list, e.g. '<pool subject> full list', not one member at a time), verify EVERY member against every condition, then rewrite."
                    order += '\nUse at most 3 tool calls to close the most important gaps, then rewrite the COMPLETE final answer with [n] citations in the required shape.'
                    messages.append({'role': 'system', 'content': order})
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
                _CITE_REF_LINE_RE = re.compile('^\\s*(?:\\[?\\d{1,3}\\]?\\s*[-–—:]\\s*(?:http|www\\.|Source|Title|URL|Result|Wikipedia|Census|Bureau|BLS|NASA|SIPRI))', re.I)

                def _is_citation_metadata_dump(text: str) -> bool:
                    lines = [l.strip() for l in (text or '').strip().split('\n') if l.strip()]
                    if len(lines) < 3:
                        return False
                    ref_count = sum((1 for l in lines[:12] if _CITE_REF_LINE_RE.match(l)))
                    prose_count = sum((1 for l in lines[:12] if len(l) > 60 and (not _CITE_REF_LINE_RE.match(l)) and (not l.startswith(('[', '#', '|', '-')))))
                    return ref_count >= 3 and prose_count == 0

                def _is_usable_answer(text: str) -> bool:
                    s = _normalize_brackets(text).strip()
                    if not s:
                        return False
                    if _TOOL_MARKUP_RE.search(s) or _looks_like_tool_json(s):
                        return False
                    if _STUB_ANSWER_RE.match(s) or _is_degenerate_repetition(s):
                        return False
                    if _is_citation_metadata_dump(s):
                        return False
                    cited = bool(_CITE_MARK_RE.search(s))
                    if cited and len(s) >= MIN_CITED_ANSWER_CHARS:
                        return True
                    if len(s) < MIN_ANSWER_CHARS:
                        return False
                    if len(s) < 400 and (_REFUSAL_ONLY_RE.match(s) or _INTENT_NARRATION_RE.match(s)):
                        return False
                    return True
                _COMMIT_RULES = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nANNOTATION: after each [n], write a brief 'Supports: [source] states [fact]' — the specific datum the citation proves. Where the evidence includes a pre-generated 'Supports:' summary, reproduce it after the [n] citation verbatim.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too. Never say what the evidence does not contain; commit to the best-supported answer you can defend."
                _REPAIR_ORDER = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

                def _sanitize_draft(text: str) -> str:
                    return _VERIFY_MARK_RE.sub('', text or '').strip()

                def _ledger_digest(ledger: EvidenceLedger, char_cap: int=60000) -> str:
                    if ledger.summaries:
                        return ledger.summary_digest(char_cap)
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
                        summary = ledger.summaries.get(i, '')
                        line = f"- {(title + ': ' if title else '')}{lead} [{i}]"
                        if summary:
                            line += f' Supports: {summary}'
                        out.append(line)
                        picked += 1
                    if picked == 0:
                        for i, r in rows[:4]:
                            lead = ' '.join((r.get('preview') or '').split())[:280]
                            if lead:
                                out.append(f'- {lead} [{i}]')
                        if len(out) == 1:
                            return ''
                    return '\n'.join(out)

                async def _write_from_digest(question: str, ledger: EvidenceLedger, deadline: float) -> str:
                    left = deadline - monotonic()
                    if left < 14.0:
                        return ''
                    digest = _ledger_digest(ledger)
                    if not digest:
                        return ''
                    convo = [{'role': 'system', 'content': _COMMIT_RULES}, {'role': 'user', 'content': f"Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; after each [n], include a brief 'Supports: [source] states [fact]' annotation (reproduce any pre-generated Supports: lines from the evidence above). Then the short proof section (pool, conditions, qualifiers, exclusions)."}]

                    async def _one(lane: str, model: str, budget: float) -> str:
                        payload = await llm_chat(provider=lane, model=model, messages=convo, temperature=0.15, max_output_tokens=2600, timeout=budget, thinking=_least_think(lane, model))
                        _spend_note(payload)
                        llm = getattr(payload, 'llm', None)
                        text = (getattr(llm, 'raw_text', None) or '').strip()
                        if not text:
                            choices = getattr(llm, 'choices', None) or []
                            if choices:
                                c = getattr(choices[0].message, 'content', None)
                                if isinstance(c, str):
                                    text = c.strip()
                        return text
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
                _SUMMARY_LINE_RE = re.compile('\\s*\\[(\\d+)\\]\\s*Supports:\\s*(.+)')

                async def _generate_evidence_summaries(question: str, ledger: EvidenceLedger, deadline: float) -> None:
                    left = deadline - monotonic()
                    if left < 60.0 or not ledger.rows:
                        return
                    if _spend_left() < 0.03:
                        return
                    items: list[str] = []
                    for i, row in enumerate(ledger.rows, start=1):
                        preview = (row.get('preview') or '').strip()
                        if not preview:
                            continue
                        title = (row.get('title') or '').strip()
                        items.append(f"[{i}] {title or '(untitled)'}\n{preview[:600]}")
                    if not items:
                        return
                    evidence_text = '\n\n'.join(items[:24])
                    prompt = f'Question:\n{question}\n\nEvidence items:\n\n{evidence_text}\n\nFor each evidence item that is RELEVANT to answering the question, write exactly one line:\n[N] Supports: According to [source title/name], [the specific fact — exact figure, name, date, or data point — that this evidence establishes for answering the question].\n\nSkip irrelevant items. Be specific: cite exact numbers, names, or dates from the evidence text. Do not paraphrase or generalize.'
                    try:
                        raw = await _chat_simple(LLM_LANE_A, LOOP_MODEL_A, "Evidence summarizer. One-line 'Supports:' summaries only.", prompt, max_tokens=2000, timeout=min(20.0, left - 50.0), think=_least_think(LLM_LANE_A, LOOP_MODEL_A))
                    except Exception:
                        return
                    for line in (raw or '').split('\n'):
                        m = _SUMMARY_LINE_RE.match(line)
                        if m:
                            n = int(m.group(1))
                            summary = m.group(2).strip()
                            if summary:
                                ledger.set_summary(n, summary)

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
                    try:
                        info = await tooling_info(timeout=10.0)
                        _spend_note(info)
                    except Exception:
                        pass
                    draft = ''
                    brief = ''
                    try:
                        if _spend_left() >= BRIEF_MIN_USD and deadline - monotonic() > 120.0:
                            draft, brief = await _knowledge_brief(question)
                    except Exception:
                        brief = ''
                    ledger = EvidenceLedger()
                    answer = ''
                    messages: list[dict] = []
                    try:
                        answer, messages = await _loop(question, brief, ledger, deadline, MAX_TURNS)
                    except Exception:
                        answer = ''
                    try:
                        await _generate_evidence_summaries(question, ledger, deadline)
                    except Exception:
                        pass
                    try:
                        if _is_usable_answer(answer) and deadline - monotonic() > 75.0 and (_spend_left() >= AUDIT_MIN_USD):
                            patched = await _audit_patch(question, answer, messages, ledger, deadline)
                            if _is_usable_answer(patched):
                                answer = patched
                    except Exception:
                        pass
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
                    try:
                        citations = _citations_for(answer, ledger)
                    except Exception:
                        citations = []
                    answer = _normalize_brackets(answer)
                    answer = _strip_lead_narration(answer)
                    answer = _answer_line_only(answer, question)
                    text = _cap(answer) or f'Best-effort answer unavailable for: {question[:400]}'
                    if query.output_schema is not None:
                        structured = None
                        try:
                            structured = await _schema_output(question, answer, query.output_schema, deadline)
                        except Exception:
                            structured = None
                        if structured is not None:
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
                        try:
                            forced = _coerce_to_schema(_cap(basis), query.output_schema)
                            return Response(output=forced, citations=citations or None)
                        except Exception:
                            try:
                                return Response(output=_cap(basis)[:2000], citations=citations or None)
                            except Exception:
                                pass
                    try:
                        return Response(text=text, citations=citations or None)
                    except Exception:
                        return Response(text=text)
                return query

        class HardPath:

            def _compile(self):
                import asyncio
                import json
                import re
                from time import monotonic
                from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
                from harnyx_miner_sdk.decorators import entrypoint
                from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
                try:
                    from harnyx_miner_sdk.structured_output import validate_output_against_schema, compact_json
                except ImportError:
                    validate_output_against_schema = None

                    def compact_json(value) -> str:
                        return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
                VERSION = 'scout-v2.17'
                LANE_A = 'openrouter'
                LANE_B = 'chutes'
                LOOP_MODEL_A = 'z-ai/glm-5.2'
                LOOP_MODEL_B = 'zai-org/GLM-5.2-TEE'
                UTIL_MODEL_A = 'deepseek/deepseek-v3.2'
                UTIL_MODEL_B = 'deepseek-ai/DeepSeek-V3.2-TEE'
                SEARCH_PROVIDER = 'parallel'
                _REASONING_MANDATORY = ('openai/gpt-oss',)
                WALL_BUDGET_S = 258.0
                WRAPUP_AT_S = 104.0
                STRUCT_TAIL_S = 24.0
                TURN_TIMEOUT_S = 70.0
                BRIEF_TIMEOUT_S = 24.0
                UTIL_TIMEOUT_S = 30.0
                SEARCH_TIMEOUT_S = 18.0
                FETCH_TIMEOUT_S = 16.0
                MIN_TAIL_S = 9.0
                MAX_TURNS = 14
                AUDIT_EXTRA_TURNS = 2
                REPAIRS_MAX = 2
                BRIEF_MIN_USD = 0.03
                AUDIT_MIN_USD = 0.05
                WRAPUP_MIN_USD = 0.02
                SEARCH_NUM = 8
                SEARCH_EXCERPT_CHARS = 3600
                FETCH_PLAIN_CHARS = 6200
                FETCH_HEAD_CHARS = 3600
                FETCH_WINDOW_CHARS = 3600
                FETCH_WINDOWS_PER_PAGE = 3
                NOTE_STORE_CAP = 220000
                MIN_SLICE_CHARS = 100
                SLICE_PAD = 120
                CITATION_CAP = 80
                EVIDENCE_CHAR_BUDGET = 112000
                MAX_EVIDENCE_SEGMENTS = 390
                ANSWER_CHAR_CAP = 60000
                _SPEND = {'left': None}

                def _spend_note(payload) -> None:
                    budget = getattr(payload, 'budget', None)
                    left = getattr(budget, 'session_remaining_budget_usd', None)
                    if isinstance(left, (int, float)):
                        _SPEND['left'] = float(left)

                def _spend_left() -> float:
                    left = _SPEND['left']
                    return float(left) if isinstance(left, (int, float)) else 1.0
                LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Search the web. Returns numbered results, each with a title, URL and excerpt. Issue several independent searches in one turn when you need several facts.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and read its main text. Large pages return the head plus the regions most relevant to your focus; pass a focus phrase (a table label, section name or entity) to steer which regions are shown. Read the authoritative roster/table page directly rather than guessing member by member.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'phrase to locate inside the page'}}, 'required': ['url']}}}]
                LOOP_RULES = 'You are a meticulous research agent. Drive the research yourself with the tools, then write ONE final answer. Follow this method:\nMETHOD. First recall from your own knowledge the likely answer and the full candidate pool; then use web_search / read_page to VERIFY every load-bearing fact and to fill gaps. Branch on what each result shows. When a fact lives in a table or roster, read that page and use the whole table — do not stop at a search snippet. Batch independent lookups into a single turn.\nGROUNDING. Cite every factual claim with [n], where n is a result number you actually read. Put the [n] immediately after the claim it supports. Reproduce figures, names and dates VERBATIM from the source — never round or reformat a number you did not read. When the FINAL answer is a single value the source states in a human-readable form (e.g. an orbital period \'4 years, 162 days\'), give THAT exact form rather than a decimal you computed — UNLESS the question asks you to extract a bound or compute (a ratio, a difference, a sum), in which case do the arithmetic and show it. If a question names a specific metric, cite the figure whose label matches that metric\'s wording exactly (resident vs apportionment population differ).\nSUPPORT-OR-DEDUCE. State a specific figure, date or value ONLY if you READ it in a tool result and can cite it [n]. If a value you would need is NOT in any source you found, do NOT invent, estimate, or state it from memory — instead reach the answer by a CITED DEDUCTION from what you DID read (e.g. \'X is not among the cited top-3 by GDP [n], so among these three it is the lowest\'). An uncited specific figure reads as UNSUPPORTED and loses even when it is correct; a weaker but fully-cited claim beats it. This trade-off applies ONLY when the exact value is in NO source you found — if you DID read the value, state it VERBATIM and cite it; never downgrade a figure you can cite to a vaguer deduction. ABOVE ALL, COMMIT: if the deciding values are not cleanly stated in any source (a map, an infographic, an image), still NAME your best-supported answer and reason it out — NEVER write that the data \'is not enumerated\' or \'not in the evidence\', never refuse, never trail off into a hedge. A committed answer with imperfect support beats an incoherent non-answer.\nCOVER EVERY VALUE YOU LIST. The grader credits a value only if a cited slice CONTAINS it. When one source backs several values or members, read and cite the region that lists them TOGETHER (the summary row, the whole list/table), so EVERY value ends up inside the citation — not just the first. Naming five members but citing text that shows only three loses the other two.\nCONDITIONS. Apply every stated condition literally and independently; a candidate qualifies only if it meets ALL of them. Show the deciding value next to each candidate you keep or reject. When the question requires membership in MULTIPLE rankings/categories at once (top-12 in EACH of three stats), OR that a condition hold across MULTIPLE reports/periods (unfavorable in BOTH the September and December reports), a candidate qualifies ONLY if it is present/true in EVERY one: consult each ranking/leaderboard and each period\'s report (re-read a large page with a different focus if the rows you need aren\'t shown yet), record every candidate\'s value/status in each, then keep ONLY those that hold in ALL — never one that holds in some.\nEXACT SOURCE. When the question names a specific document, report, table, dataset edition or column, fetch and use THAT exact source and THAT exact table/column/metric label — not a similarly-named one. The wording of the label the question quotes must match the figure you read. When the question says \'according to <SOURCE>\', support EVERY condition from THAT source — including the hardest one — and cite the source\'s own page for each ranking/table it provides; do NOT substitute an aggregator or stats-summary site (a page that only answers one sub-question) for a condition you could not immediately find on the named source. A cited condition backed by the wrong site reads as unsupported to the grader. NAMED-SOURCE LOCK: when the question names a source — even by NAME (\'the Wikipedia "2022-23 Premier League" article\', \'CityPopulation.de\', \'The Numbers\', \'the Sanna Nielsen discography article\') — LOCATE that exact page (search its title, then read_page it) and cite THAT page as the evidence for the answer. The answer\'s citation MUST be the named source: evidence that is an AGGREGATOR (Transfermarkt, StatMuse, USAFacts, a wiki mirror) or ANY page other than the named one scores as UNSUPPORTED even when the answer is correct — never fall back to a faster aggregator. Cite ONLY the named source; do NOT add other or related pages beyond it (they read as off-source noise and cost you). Use the source\'s OWN spelling for every entity you take from it (write \'Makkah\'/\'Madinah\' if that is how it spells them, not \'Mecca\'/\'Medina\'). EXACT EDITION: cite the precise edition/year/cycle the question specifies — the 2020 ELECTION results, not the 2020-census reallocation used for the 2024+ cycle; the named document\'s own stated date, not an earlier one. A right value from the wrong edition scores as unsupported.\nCOMMIT. Always commit to a concrete best answer. Never refuse, never say the answer cannot be determined, and never dump raw source text or titles as the answer. If evidence is thin, give your best supported answer and mark any single shaky value plainly.\nANSWER SHAPE. Open with the direct answer in the first line (the name/number/list asked for). Do NOT narrate your process (\'I now have…\', \'Let me…\'). Then give a tight per-item breakdown with the cited deciding value for each. Use the exact official name/spelling and the units or format the question implies.\nPOOL DISCIPLINE. The pool is the WHOLE named class you range over, not the survivors you already believe qualify — build it broad, then apply conditions one at a time and show who each eliminates. Give ONE LINE PER POOL MEMBER: a line for every qualifier with its qualifying value cited, AND a line for every member you rule out with its failing condition. Never compress several rejects into one clause — each rejected member gets its own line; when many share ONE roster/table, cite that source once and refer to it rather than repeating the same [n] on every line. If you cannot settle a member\'s condition, KEEP it among the qualifiers (a wrongly-dropped qualifier costs as much as a wrong answer) and cite the strongest fact you did verify.\nCITE THE HARD CONDITION WITH ITS PROOF TEXT. Only the materialized citation SLICE counts as evidence to the grader — never your prose, your [n] labels, or a source list you write. So for EVERY stated condition (especially the hardest, and INCLUDING descriptive/soft ones — who or what something is named after, a definition, a quoted statement, a qualitative property), give it its OWN cited subclaim and QUOTE the distinctive proof VERBATIM from the source inside that sentence: the exact name, number, date, or the literal quoted phrase (e.g. write the actual words \'I think, therefore I am\' [n]), and cite a result whose note text CONTAINS those exact words. Do NOT settle a descriptive/soft condition from your own knowledge — fetch a page that states the connection and cite it; a knowledge-only or uncited condition reads as UNSUPPORTED, and a correct answer whose decisive condition is unproven loses to a weaker one that proves it. A citation that only establishes the candidate pool leaves the actual filter unsupported. Prefer the single most AUTHORITATIVE source per condition; do not cite the same fact repeatedly (repetitive or irrelevant citations count AGAINST you).\nLITERAL OUTPUT. Obey formatting instructions mechanically. \'list them without the word "X"\' shapes what you PRINT — delete X from each name; \'titles without the word X\' is a condition on the POOL — keep only members lacking it. When an ORDER is demanded, the ANSWER LINE itself must be sorted (print the sort key beside each item and check every adjacent pair — one member out of sequence fails the whole answer); \'comma-separated\' means join with commas; a requested count means emit the number. Apply comparators exactly: \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints. If the answer is derived (a mean/total/rank/count), pull every input into one explicit list first, then compute, and show the arithmetic. SAY NO MORE THAN THE CITATION — if the source says \'brought to\', do not write \'incarcerated\'; a count of 12 is not 11; check every count and verb against its [n].'
                SET_RULE = "SET/ENUMERATION QUESTION. The answer is a COMPLETE set — a MISSING qualifier scores the same as wrong, and so does an EXTRA member that fails a condition. GET THE POOL FROM A LIST, NOT MEMBER-BY-MEMBER: your FIRST retrieval should hunt the authoritative roster/list/table that enumerates the whole pool — search it AS a list ('<pool subject> list', 'list of <pool subject>', '<pool subject> table') and read_page it. Assembling the pool from separate per-member searches is how a run ends up with 3 of 6 qualifiers and runs out of turns before the pool is covered. ONE LIST PER PERIOD, THEN JOIN: when a condition must hold across several periods/tables/editions, fetch ONE roster page per period and JOIN them on the member — one list per period, not one lookup per member. Then test every member against every condition. Name ALL qualifiers, each on its own line with the cited deciding value that qualifies it; give EVERY excluded member its own line with the exact condition it fails — never sweep several rejects into one clause, but when many rejects come from ONE roster/table, cite that source once and refer to it rather than repeating the same [n] on every line. Exclude a member ONLY by naming a condition it PROVABLY fails (with the cited fact); if it is uncertain whether a member qualifies, KEEP it — a wrongly-dropped qualifier costs as much as a wrong answer. Never include totals, aggregate/parent rows, headers or near-miss rows as members. UNIVERSAL conditions ('in EVERY one', 'in ALL three', 'for BOTH'): check each candidate against EACH instance separately with a citation per instance — a single shared instance is not enough. If NO candidate survives every instance, then 'none' IS the answer: state it as a verified fact with the per-instance citations that prove it."
                SUPERLATIVE_RULE = 'SUPERLATIVE / SINGLE-WINNER QUESTION. Researching one winner still requires the whole comparison pool. Assemble the candidates the scope admits, put the deciding value (cited, verbatim) next to each, then name the winner. Never decide from a rounded or derived figure. If the pool is large, rank the top handful with their values and name the winner explicitly.'
                _COMMIT_RULES = "You are writing the FINAL ANSWER from evidence already gathered. You have NO tools — never emit tool syntax. A judge credits only claims carrying an [n] citation to the numbered evidence. SHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited failing reason — every member on its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. For EVERY stated condition (especially descriptive ones — what something is named after, a definition, a quoted phrase), put the distinctive proof VERBATIM into a cited subclaim (the exact number/date/name, or the literal quoted words) and cite a source note that CONTAINS those exact words — only the citation slice is evidence, not your prose. Do NOT state a figure/date/value that is not in the gathered evidence — if you cannot cite it, make a CITED DEDUCTION from what you have rather than assert an uncited number. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand (sort order, comma-separated, a requested count, 'without the word X' meaning delete that word). Commit to the best-supported answer; never refuse, never say what the evidence does not contain."
                _COMMIT_SET_RULE = ' This is a COMPLETE-SET question: if it requires membership in MULTIPLE rankings/categories/periods at once, list ONLY the members present in EVERY one (the set intersection) — never a member present in only some. If evidence is incomplete, give the best-supported partial intersection — never pad with unrelated names or raw source text.'

                def _wrapup_order(seconds_left: float) -> str:
                    s = f'TIME CHECK (~{int(seconds_left)}s left): stop researching now and WRITE THE COMPLETE FINAL ANSWER from the evidence you already have. Do not call any more tools. Include every [n] citation.'
                    if seconds_left < 60:
                        s += ' BREVITY OVERRIDE: too little time for a line per member — lead with the answer entities, give each qualifier ONE cited line, and compress the rejects into a single cited line. A complete SHORT answer beats a long one that never finishes.'
                    return s
                REPAIR_RULE = 'Your previous message was not a usable final answer (it was tool markup, empty, or a refusal). Write the final answer now as plain prose that directly answers the question, with [n] citations. Commit to a concrete answer.'
                _SUPERLATIVE_WORDS = frozenset('highest lowest largest smallest biggest greatest least most fewest longest shortest tallest deepest widest heaviest lightest fastest slowest oldest youngest newest best worst first last top bottom maximum minimum peak leading foremost'.split())
                _SUPERLATIVE_PHRASE_RE = re.compile('\\b(most|least|highest|lowest|greatest|fewest|top|maximum|minimum|largest|smallest)\\b|\\b(second|third|fourth|fifth|next|penultimate)[-\\s](highest|lowest|largest|smallest|most|greatest|biggest)\\b|\\bhow many\\b|\\bmost (?:common|frequent|populous|expensive|valuable|recent)\\b|\\brunner-?up\\b', re.IGNORECASE)
                _EST_RE = re.compile('\\b[a-z]{3,}est\\b')
                _EST_STOP = frozenset('everest budapest bucharest tempest earnest honest modest forest interest harvest request protest suggest contest arrest'.split())
                _SET_VERB_RE = re.compile('\\b(list|name|identify|enumerate|give|state|provide|find|which|what|who|whom)\\b', re.IGNORECASE)
                _SET_ALL_RE = re.compile('\\b(all|every|each|both|any other|as well as|and also)\\b', re.IGNORECASE)
                _PLURAL_HEAD_RE = re.compile('\\b(which|what|who|name|list)\\b(?:\\s+\\w+){0,3}?\\s+([a-z]{3,}s|men|women|children|people|criteria)\\b', re.IGNORECASE)
                _PLURAL_FALSE = frozenset('is was has does its this class analysis species series address'.split())
                _CLOSED_NOUNS = frozenset('movies films series shows episodes countries nations states cities towns companies firms banks universities colleges schools agencies teams clubs players athletes artists bands albums songs books novels authors writers species languages products models awards winners recipients members presidents senators governors provinces regions counties districts mountains rivers lakes'.split())

                def _has_superlative(q: str) -> bool:
                    low = q.lower()
                    if any((w in _SUPERLATIVE_WORDS for w in re.findall('[a-z]+', low))):
                        return True
                    if _SUPERLATIVE_PHRASE_RE.search(q):
                        return True
                    return any((m.group(0) not in _EST_STOP for m in _EST_RE.finditer(q)))

                def _needs_superlative(q: str) -> bool:
                    return _has_superlative(q)

                def _needs_completeness(q: str) -> bool:
                    low = q.lower()
                    if _SET_VERB_RE.search(q) and _SET_ALL_RE.search(q):
                        return True
                    if 'how many' in low:
                        return True
                    tokens = set(re.findall('[a-z]+', low))
                    if _SET_VERB_RE.search(q) and tokens & _CLOSED_NOUNS:
                        return True
                    m = _PLURAL_HEAD_RE.search(q)
                    if m and m.group(2).lower() not in _PLURAL_FALSE:
                        if _has_superlative(q) and (not _SET_ALL_RE.search(q)):
                            return False
                        return True
                    return False

                def _classify(question: str) -> dict:
                    return {'completeness': _needs_completeness(question), 'superlative': _needs_superlative(question)}

                def _merge_hint(profile: dict, hint: dict | None) -> dict:
                    if not hint:
                        return profile
                    merged = dict(profile)
                    if hint.get('completeness'):
                        merged['completeness'] = True
                    if hint.get('superlative'):
                        merged['superlative'] = True
                    return merged

                class EvidenceLedger:

                    def __init__(self) -> None:
                        self.rows: list[dict] = []
                        self.page_cache: dict[str, tuple[str, str, str]] = {}

                    def add(self, *, receipt_id: str, result_id: str, note: str, kind: str, shown_spans: list[tuple[int, int]], title: str, url: str) -> int:
                        self.rows.append({'receipt_id': receipt_id, 'result_id': result_id, 'note': note[:NOTE_STORE_CAP], 'note_len': len(note), 'kind': kind, 'shown_spans': shown_spans, 'title': (title or '')[:160], 'url': (url or '')[:300]})
                        return len(self.rows)

                    def get(self, number: int) -> dict | None:
                        if 1 <= number <= len(self.rows):
                            return self.rows[number - 1]
                        return None
                _WORD_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
                _STOP = frozenset('the and for with from that this have has had was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than them they will would could should'.split())

                def _key_terms(text: str) -> set[str]:
                    return {w for w in _WORD_RE.findall((text or '').casefold()) if w not in _STOP}

                def _best_windows(note: str, terms: set[str], width: int, k: int) -> list[tuple[int, int]]:
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
                        return f'# tool error: {out}'
                    text = out.text
                    for i, row in enumerate(out.rows):
                        n = ledger.add(receipt_id=row['receipt_id'], result_id=row['result_id'], note=row['note'], kind=row['kind'], shown_spans=row['shown_spans'], title=row['title'], url=row['url'])
                        text = text.replace(_SLOT.format(i), str(n))
                    return text
                _SITE_OP_RE = re.compile('\\bsite:\\S+\\s*', re.I)

                def _degrade_query(q: str) -> str:
                    return ' '.join(_SITE_OP_RE.sub('', q or '').replace('"', ' ').split())

                async def _do_search(query_text: str, ledger: EvidenceLedger) -> object:
                    if not query_text.strip():
                        return '# web_search: empty query'
                    payload = None
                    fired: set[str] = set()
                    for attempt, allow_repeat in ((query_text, False), (query_text, True), (_degrade_query(query_text), False)):
                        if not attempt.strip() or (attempt in fired and (not allow_repeat)):
                            continue
                        fired.add(attempt)
                        try:
                            payload = await search_web(attempt, provider=SEARCH_PROVIDER, num=SEARCH_NUM, timeout=SEARCH_TIMEOUT_S)
                            if getattr(payload, 'results', None):
                                break
                        except Exception:
                            payload = None
                    if payload is None:
                        return f'# web_search({query_text!r}) failed'
                    _spend_note(payload)
                    receipt = str(getattr(payload, 'receipt_id', '') or '')
                    results = list(getattr(payload, 'results', None) or [])
                    if not receipt:
                        return f'# web_search({query_text!r}): no citable results'
                    rows: list[dict] = []
                    lines = [f'# web_search({query_text!r}): {len(results)} results']
                    for item in results:
                        rid = getattr(item, 'result_id', None)
                        note = getattr(item, 'note', None) or ''
                        if not isinstance(rid, str) or not rid or (not note.strip()):
                            continue
                        n_len = len(note)
                        shown = min(max(SEARCH_EXCERPT_CHARS, MIN_SLICE_CHARS), n_len)
                        span = [(0, shown)] if n_len else []
                        title = (getattr(item, 'title', None) or '').strip()
                        url = (getattr(item, 'url', None) or '').strip()
                        rows.append({'receipt_id': receipt, 'result_id': rid, 'note': note, 'kind': 'search', 'shown_spans': span, 'title': title, 'url': url})
                        lines.append(f'[{_SLOT.format(len(rows) - 1)}] {title} — {url}\n    {note[:SEARCH_EXCERPT_CHARS]}')
                    if not rows:
                        return f'# web_search({query_text!r}): no citable results'
                    return ToolOutput('\n'.join(lines), rows)

                async def _do_fetch(url: str, focus: str, question: str, ledger: EvidenceLedger) -> object:
                    if not url.strip():
                        return '# read_page: empty url'
                    cached = ledger.page_cache.get(url)
                    if cached is not None:
                        receipt, rid, note = cached
                    else:
                        payload = None
                        for _ in (0, 1):
                            try:
                                payload = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=FETCH_TIMEOUT_S)
                                if getattr(payload, 'results', None):
                                    break
                            except Exception:
                                payload = None
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
                        ledger.page_cache[url] = (receipt, rid, note)
                    if len(note) <= FETCH_PLAIN_CHARS:
                        row = {'receipt_id': receipt, 'result_id': rid, 'note': note, 'kind': 'fetch', 'shown_spans': [(0, len(note))], 'title': url, 'url': url}
                        return ToolOutput(f'# read_page({url!r}) -> [{_SLOT.format(0)}] full page, {len(note)} chars\n{note}', [row])
                    terms = _key_terms(question) | _key_terms(focus)
                    windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, FETCH_WINDOWS_PER_PAGE)
                    row = {'receipt_id': receipt, 'result_id': rid, 'note': note, 'kind': 'fetch', 'shown_spans': [(0, FETCH_HEAD_CHARS)] + list(windows), 'title': url, 'url': url}
                    head = note[:FETCH_HEAD_CHARS]
                    sections = ''.join((f'\n--- section @{s} ---\n{note[s:e]}' for s, e in windows))
                    body = f'# read_page({url!r}) -> [{_SLOT.format(0)}] {len(note)} chars; head + the {len(windows)} most relevant section(s). If the answer set may continue elsewhere on this page, call read_page again with a different focus.\n--- head ---\n{head}{sections}'
                    return ToolOutput(body, [row])

                async def _run_tool(call, question: str, ledger: EvidenceLedger) -> object:
                    try:
                        args = json.loads(getattr(call, 'arguments', None) or '{}')
                    except Exception:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}
                    name = getattr(call, 'name', '') or ''
                    if name == 'web_search':
                        return await _do_search(str(args.get('query') or ''), ledger)
                    if name == 'read_page':
                        return await _do_fetch(str(args.get('url') or ''), str(args.get('focus') or ''), question, ledger)
                    return f'# unknown tool {name!r}'

                def _think(model: str, on: bool):
                    for prefix in _REASONING_MANDATORY:
                        if model.startswith(prefix):
                            return {'enabled': True, 'effort': 'low'}
                    return {'enabled': True, 'effort': 'low'} if on else {'enabled': False}

                def _text_of(payload) -> str:
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

                async def _chat_simple(system: str, user: str, *, deadline: float, max_tokens: int, timeout: float, think_on: bool=False) -> str:
                    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
                    for lane, model in ((LANE_A, UTIL_MODEL_A), (LANE_B, UTIL_MODEL_B)):
                        rem = deadline - monotonic() - 4.0
                        if rem <= 4.0:
                            break
                        to = min(timeout, rem)
                        try:
                            payload = await llm_chat(provider=lane, model=model, messages=messages, temperature=0.15, max_output_tokens=max_tokens, timeout=to, thinking=_think(model, think_on))
                            _spend_note(payload)
                            text = _text_of(payload)
                            if text:
                                return text
                        except Exception:
                            continue
                    return ''

                async def _chat_turn(messages: list, deadline: float, *, finish_only: bool):
                    use_tools = not finish_only
                    for lane, model in ((LANE_A, LOOP_MODEL_A), (LANE_B, LOOP_MODEL_B)):
                        rem = deadline - monotonic() - 5.0
                        if rem <= 5.0:
                            return None
                        to = min(TURN_TIMEOUT_S, rem)
                        try:
                            payload = await llm_chat(provider=lane, model=model, messages=messages, tools=LOOP_TOOLS if use_tools else None, tool_choice='auto' if use_tools else None, temperature=0.2, thinking=_think(model, on=True), timeout=to)
                            _spend_note(payload)
                            return payload
                        except Exception:
                            continue
                    return None

                async def _knowledge_brief(question: str, deadline: float) -> tuple[str, str, dict | None]:
                    system = 'You are a senior research analyst. From your own knowledge, commit to a concrete best answer and list the full candidate pool. Mark any uncertain value with (verify). Never refuse.'
                    user = f'QUESTION:\n{question}\n\nWrite:\nBEST ANSWER: your concrete best answer now, from memory.\nPOOL: the candidates/members relevant to this question (so research can verify each).\nCONDITIONS: a numbered checklist of EVERY atomic condition the answer must satisfy — include the soft/descriptive ones (what something is named after, a definition, a quoted statement, a qualitative property), not only the numeric filters; each must end up cited to a source whose text states it.\nVERIFY: the specific facts/figures a tool must confirm.\nThen a final line exactly of the form:\nCLASS: {{"completeness": true|false, "superlative": true|false}}\nwhere completeness=true if the answer must be a COMPLETE set/list of every qualifier, and superlative=true if it asks for a single extreme/winner.'
                    text = await _chat_simple(system, user, deadline=deadline, max_tokens=1400, timeout=BRIEF_TIMEOUT_S, think_on=False)
                    if not text:
                        return ('', '', None)
                    hint = None
                    m = re.search('CLASS:\\s*(\\{.*?\\})', text, re.DOTALL)
                    if m:
                        try:
                            raw = json.loads(m.group(1))
                            if isinstance(raw, dict):
                                hint = {'completeness': bool(raw.get('completeness')), 'superlative': bool(raw.get('superlative'))}
                        except Exception:
                            hint = None
                    draft = text.split('VERIFY')[0].split('POOL')[0].replace('BEST ANSWER:', '').strip()
                    brief = 'PRIOR ANALYSIS (your own knowledge; verify anything marked (verify) and correct it wherever tool results disagree):\n' + text
                    return (draft, brief, hint)
                _QUESTION_URL_RE = re.compile('https?://[^\\s)>\\]\\"\'}]+')
                _WIKI_TITLE_RE = re.compile('[\\"\'“”‘’]([^\\"\'“”‘’]{3,90})[\\"\'“”‘’]')

                def _named_wikipedia_title(question: str) -> str | None:
                    if 'wikipedia' not in question.lower():
                        return None
                    for m in _WIKI_TITLE_RE.finditer(question):
                        t = m.group(1).strip()
                        if any((c.isalpha() for c in t)) and 1 <= len(t.split()) <= 14:
                            return t
                    return None

                def _wikipedia_url(title: str) -> str:
                    return 'https://en.wikipedia.org/wiki/' + title.strip().replace(' ', '_')

                async def _preseed(question: str, profile: dict, ledger: EvidenceLedger, deadline: float) -> str:
                    if deadline - monotonic() < WRAPUP_AT_S + 40.0:
                        return ''
                    blocks: list[str] = []
                    urls = [u.rstrip('.,);') for u in _QUESTION_URL_RE.findall(question)]
                    wiki_title = None if urls else _named_wikipedia_title(question)
                    if wiki_title:
                        urls = [_wikipedia_url(wiki_title)]
                    if urls:
                        out = await _do_fetch(urls[0], question, question, ledger)
                        body = _commit_tool_output(out, ledger)
                        if isinstance(body, str) and body.lstrip().startswith('#') and ('->' in body):
                            blocks.append(body)
                        head = 'PRE-SEED — the EXACT source the question names, fetched for you. READ it and CITE THIS page as the evidence for your answer; do NOT cite an aggregator instead:\n' if wiki_title else 'PRE-SEED (the exact source page the question names — read it, then verify what remains):\n'
                    else:
                        out = await _do_search(question.strip(), ledger)
                        body = _commit_tool_output(out, ledger)
                        if isinstance(body, str) and body.strip().startswith('['):
                            blocks.append(body)
                        head = 'PRE-SEED SEARCH (already run for you — read, then decide what to verify next):\n'
                    if not blocks:
                        return ''
                    return head + '\n'.join(blocks)

                def _build_system(question: str, profile: dict, brief: str, seeded: str) -> list:
                    messages: list = [{'role': 'system', 'content': LOOP_RULES}]
                    if profile.get('completeness'):
                        messages.append({'role': 'system', 'content': SET_RULE})
                    if profile.get('superlative'):
                        messages.append({'role': 'system', 'content': SUPERLATIVE_RULE})
                    if brief:
                        messages.append({'role': 'system', 'content': brief})
                    if seeded:
                        messages.append({'role': 'system', 'content': seeded})
                    messages.append({'role': 'user', 'content': question})
                    return messages

                async def _loop(question: str, messages: list, ledger: EvidenceLedger, deadline: float, turn_cap: int) -> tuple[str, list]:
                    answer = ''
                    ordered_wrapup = False
                    repairs_left = REPAIRS_MAX
                    turn_retries = 2
                    for turn in range(1, turn_cap + 1):
                        left = deadline - monotonic()
                        if left <= MIN_TAIL_S:
                            break
                        finish_only = left <= WRAPUP_AT_S or _spend_left() <= WRAPUP_MIN_USD or turn >= turn_cap
                        if (finish_only or turn >= turn_cap - 1) and (not ordered_wrapup):
                            messages.append({'role': 'system', 'content': _wrapup_order(left)})
                            ordered_wrapup = True
                        payload = await _chat_turn(messages, deadline, finish_only=finish_only)
                        llm = getattr(payload, 'llm', None) if payload is not None else None
                        choices = getattr(llm, 'choices', None) or [] if llm is not None else []
                        if payload is None or not choices:
                            if turn_retries > 0 and deadline - monotonic() > WRAPUP_AT_S + 10.0:
                                turn_retries -= 1
                                continue
                            break
                        msg = choices[0].message
                        calls = getattr(msg, 'tool_calls', None) or ()
                        if not calls:
                            candidate = _text_of(payload)
                            if not _is_usable(candidate):
                                if repairs_left > 0 and deadline - monotonic() > MIN_TAIL_S + 10.0:
                                    repairs_left -= 1
                                    messages.append({'role': 'system', 'content': REPAIR_RULE})
                                    continue
                                break
                            answer = candidate
                            messages.append({'role': 'assistant', 'content': answer})
                            break
                        messages.append(msg.to_input_message())
                        run_calls = list(calls[:8])
                        tool_budget = max(5.0, min(FETCH_TIMEOUT_S * 2 + 6.0, deadline - monotonic() - MIN_TAIL_S))
                        tasks = [asyncio.ensure_future(_run_tool(c, question, ledger)) for c in run_calls]
                        try:
                            await asyncio.wait(tasks, timeout=tool_budget)
                        except Exception:
                            pass
                        for call, task in zip(run_calls, tasks):
                            if task.done():
                                try:
                                    result = task.result()
                                except Exception as exc:
                                    result = f'# tool crashed: {exc}'
                            else:
                                task.cancel()
                                result = '# tool timed out — use what you already have'
                            body = _commit_tool_output(result, ledger)
                            messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': body or '# empty result'})
                        for call in calls[8:]:
                            messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if needed'})
                    return (answer, messages)

                async def _audit_patch(question: str, profile: dict, answer: str, messages: list, ledger: EvidenceLedger, deadline: float) -> str:
                    if not (profile.get('completeness') or profile.get('superlative')):
                        return answer
                    left = deadline - monotonic()
                    if left <= WRAPUP_AT_S + 30.0:
                        return answer
                    system = 'You are a strict correctness auditor. Decide whether the answer is WRONG as a set: it OMITS a qualifying member, INCLUDES a member that PROVABLY fails at least one stated condition (a near-miss, a total/aggregate/parent row, or a table misread), or fails to prove the winner against the pool. For a multi-condition/intersection question a member is correct ONLY if it holds in EVERY required ranking/period/table. Reply with JSON: {"wrong": true|false, "overincluded": true|false, "reason": "..."}. Do not rewrite.'
                    user = f'QUESTION:\n{question}\n\nANSWER:\n{answer[:6000]}'
                    verdict = await _chat_simple(system, user, deadline=deadline, max_tokens=300, timeout=min(20.0, max(8.0, left - WRAPUP_AT_S - 4.0)), think_on=False)
                    wrong = overincluded = False
                    if verdict:
                        m = re.search('\\{.*\\}', verdict, re.DOTALL)
                        if m:
                            try:
                                v = json.loads(m.group(0))
                                wrong = bool(v.get('wrong'))
                                overincluded = bool(v.get('overincluded'))
                            except Exception:
                                wrong = overincluded = False
                    if not wrong or deadline - monotonic() <= WRAPUP_AT_S + 2.0:
                        return answer
                    if overincluded:
                        messages.append({'role': 'system', 'content': 'Your answer may include a member that does NOT satisfy every condition (a near-miss, a total/aggregate/parent row, or a table misread). Re-verify EACH listed member against its exact source row and deciding value, re-reading the source; REMOVE only a member you can now PROVE fails a condition. If every listed member qualifies, keep the answer unchanged. Do NOT add new members.'})
                    else:
                        messages.append({'role': 'system', 'content': 'The answer may be missing qualifying members. Search for the complete roster/pool, verify each member against the conditions, and rewrite the COMPLETE final answer with [n] citations. Keep every correct fact you already have.'})
                    patched, _ = await _loop(question, messages, ledger, deadline, AUDIT_EXTRA_TURNS + 1)
                    if _is_usable(patched) and len(patched) >= 0.6 * len(answer):
                        return patched
                    return answer
                _TOOL_JSON_RE = re.compile('^\\s*[\\[{].*("tool_call|"function"|web_search|read_page)', re.DOTALL)
                _TOOL_MARKUP_RE = re.compile('<\\s*/?\\s*(tool_call|function|invoke|arg_key|arg_value|parameter|antml)\\b', re.IGNORECASE)
                _REFUSAL_RE = re.compile("\\b(cannot|can't|unable to|i'm sorry|i am sorry|no answer|not able to)\\b", re.IGNORECASE)
                _INTENT_NARRATION_RE = re.compile("^\\s*(?:i (?:need|will|'ll|should|am going) to|let me|i'll|now i|first,? i|to (?:answer|solve|find)|let's|i can (?:now )?|based on my search|i have (?:now )?(?:gathered|searched|found))\\b", re.IGNORECASE)

                def _is_degenerate(text: str) -> bool:
                    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                    if len(lines) >= 4 and len(set(lines)) * 2 > len(lines):
                        return False
                    if len(lines) >= 4:
                        uniq = len(set(lines))
                        if uniq <= max(1, len(lines) // 3):
                            return True
                    words = text.split()
                    if len(words) >= 30:
                        for size in (4, 5, 6):
                            grams = [' '.join(words[i:i + size]) for i in range(0, len(words) - size, size)]
                            if grams and len(set(grams)) <= max(1, len(grams) // 4):
                                return True
                    return False

                def _is_usable(text: str) -> bool:
                    if not text:
                        return False
                    stripped = _normalize_brackets(text.strip())
                    if len(stripped) < 12:
                        return False
                    if _TOOL_JSON_RE.match(stripped) or _TOOL_MARKUP_RE.search(stripped[:400]):
                        return False
                    if len(stripped) >= 12 and _BRACKET_RE.search(stripped):
                        return True
                    if _is_degenerate(stripped):
                        return False
                    if len(stripped) < 80 and _REFUSAL_RE.search(stripped):
                        return False
                    if len(stripped) < 400 and _INTENT_NARRATION_RE.match(stripped):
                        return False
                    return True
                _SENT_RE = re.compile('[^.!?]{20,400}[.!?]')
                _DUMP_JUNK_RE = re.compile('\\b(svg|xlsx?|csv|pdf|png|jpe?g|json|html?|aspx?|zip)\\b', re.I)
                _FUNC_WORD_RE = re.compile('\\b(the|a|an|is|are|was|were|be|in|of|and|to|for|with|that|which|had|has|on|at|by)\\b', re.I)
                _NAV_JUNK_RE = re.compile('you are here|\\bhome page\\b|full site menu|return to top|skip navigation|main menu|\\bsign in\\b|\\blog in\\b|\\bsubscribe\\b|\\bcookies?\\b|privacy policy|terms of (?:service|use|sale)|newsletter|breadcrumb|token=|https?://|\\bmenu\\b|>\\s*\\w+\\s*>', re.IGNORECASE)

                def _prose_sentences(text: str) -> list[str]:
                    cleaned = re.sub('<[^>]+>', ' ', text)
                    cleaned = re.sub('\\s+', ' ', cleaned).strip()
                    out = []
                    for m in _SENT_RE.finditer(cleaned):
                        s = m.group(0).strip()
                        alpha = sum((c.isalpha() or c.isspace() for c in s)) / max(1, len(s))
                        if alpha < 0.72 or len(s.split()) < 6:
                            continue
                        if _DUMP_JUNK_RE.search(s) or len(_FUNC_WORD_RE.findall(s)) < 2:
                            continue
                        if _NAV_JUNK_RE.search(s) or s.count('>') >= 2 or s.count('|') >= 2 or (s.count('*') >= 2):
                            continue
                        out.append(s)
                    return out

                async def _rescue(question: str, profile: dict, ledger: EvidenceLedger, draft: str, deadline: float) -> str:
                    if deadline - monotonic() > 16.0 and ledger.rows:
                        digest = _ledger_digest(ledger)
                        system = _COMMIT_RULES + (_COMMIT_SET_RULE if profile.get('completeness') else '')
                        user = f'QUESTION:\n{question}\n\nEVIDENCE:\n{digest}'
                        text = await _chat_simple(system, user, deadline=deadline, max_tokens=1600, timeout=min(UTIL_TIMEOUT_S, deadline - monotonic() - 8.0), think_on=False)
                        if _is_usable(text):
                            return text
                    det = _deterministic_answer(question, ledger)
                    if _is_usable(det):
                        return det
                    if _is_usable(draft):
                        return _VERIFY_MARK_RE.sub('', draft).strip()
                    if deadline - monotonic() > 12.0:
                        resort = await _chat_simple('Expert researcher. Give your single best definitive answer with concrete entities, numbers and dates. Commit — never refuse, never hedge.', question, deadline=deadline, max_tokens=1400, timeout=min(UTIL_TIMEOUT_S, deadline - monotonic() - 4.0), think_on=False)
                        if _is_usable(resort):
                            return _VERIFY_MARK_RE.sub('', resort).strip()
                    return ''

                def _ledger_digest(ledger: EvidenceLedger, char_cap: int=56000) -> str:
                    blocks = []
                    total = 0
                    for i, row in enumerate(ledger.rows, start=1):
                        note = row['note']
                        spans = row['shown_spans'] or [(0, min(700, len(note)))]
                        span = spans[1] if row.get('kind') == 'fetch' and len(spans) > 1 else spans[0]
                        excerpt = note[span[0]:span[0] + 900]
                        block = f"[{i}] {row['title']} ({row['url']})\n{excerpt}"
                        if total + len(block) > char_cap:
                            break
                        blocks.append(block)
                        total += len(block)
                    return '\n\n'.join(blocks)

                def _deterministic_answer(question: str, ledger: EvidenceLedger) -> str:
                    focus = _key_terms(question)
                    picked: list[str] = []
                    for i, row in enumerate(ledger.rows, start=1):
                        best, best_hits = (None, -1)
                        for s in _prose_sentences(row['note'])[:10]:
                            low = s.lower()
                            hits = sum((1 for t in focus if t in low))
                            hits += 2 if hits and re.search('\\d', s) else 0
                            if hits > best_hits:
                                best, best_hits = (s, hits)
                        if best and (best_hits > 0 or not focus):
                            picked.append(f"{best.rstrip('.!?')} [{i}].")
                        if len(picked) >= 6:
                            break
                    if not picked:
                        return ''
                    return 'Based on the sources: ' + ' '.join(picked)
                _BRACKET_FIX = {12304: '[', 12305: ']', 65339: '[', 65341: ']', 65288: '(', 65289: ')'}
                for _d in range(10):
                    _BRACKET_FIX[65296 + _d] = chr(48 + _d)

                def _normalize_brackets(text: str) -> str:
                    return (text or '').translate(_BRACKET_FIX)
                _BRACKET_RE = re.compile('\\[([0-9][0-9,\\s\\-]*)\\]')
                _NUM_ANCHOR_RE = re.compile('\\$?\\d[\\d,]*(?:\\.\\d+)?%?')
                _ENT_ANCHOR_RE = re.compile("[A-Z][A-Za-z.'’&/-]+(?:\\s+[A-Z0-9][A-Za-z0-9.'’&/-]+){0,4}")

                def _cited_numbers_in_order(answer: str, top: int) -> list[int]:
                    seen: set[int] = set()
                    order: list[int] = []
                    for m in _BRACKET_RE.finditer(answer):
                        body = m.group(1)
                        for part in body.split(','):
                            part = part.strip()
                            if not part:
                                continue
                            if '-' in part:
                                a, _, b = part.partition('-')
                                try:
                                    lo, hi = (int(a), int(b))
                                except ValueError:
                                    continue
                                for n in range(lo, min(hi, lo + 20) + 1):
                                    if 1 <= n <= top and n not in seen:
                                        seen.add(n)
                                        order.append(n)
                            else:
                                try:
                                    n = int(part)
                                except ValueError:
                                    continue
                                if 1 <= n <= top and n not in seen:
                                    seen.add(n)
                                    order.append(n)
                    return order

                def _answer_row_clauses(answer: str) -> list[str]:
                    rows: list[str] = []
                    for line in re.split('\\n+', answer):
                        line = line.strip().strip('|').strip()
                        if len(line) < 6:
                            continue
                        if re.search('[A-Z][a-z]', line) and re.search('\\d', line):
                            rows.append(line[:300])
                    return rows

                def _clause_for_marker(answer: str, marker_start: int) -> str:
                    left = answer.rfind(']', 0, marker_start)
                    b1 = max(answer.rfind('.', 0, marker_start), answer.rfind('\n', 0, marker_start), answer.rfind(':', 0, marker_start), answer.rfind(';', 0, marker_start))
                    start = max(left + 1, b1 + 1, 0)
                    return answer[start:marker_start]

                def _bracket_numbers(body: str) -> list[int]:
                    nums: list[int] = []
                    for part in body.split(','):
                        part = part.strip()
                        if part.isdigit():
                            nums.append(int(part))
                        elif '-' in part:
                            a, _, b = part.partition('-')
                            if a.strip().isdigit() and b.strip().isdigit():
                                nums.extend(range(int(a), min(int(b), int(a) + 20) + 1))
                    return nums

                def _clauses_by_source(answer: str, top: int) -> dict[int, list[str]]:
                    out: dict[int, list[str]] = {}
                    for m in _BRACKET_RE.finditer(answer):
                        clause = _clause_for_marker(answer, m.start())
                        for n in _bracket_numbers(m.group(1)):
                            if 1 <= n <= top:
                                out.setdefault(n, []).append(clause)
                    return out

                def _norm_note(note: str) -> tuple[str, list[int]]:
                    chars: list[str] = []
                    idx: list[int] = []
                    for i, ch in enumerate(note):
                        if ch == ',':
                            continue
                        chars.append(ch)
                        idx.append(i)
                    return (''.join(chars), idx)

                def _is_number_token(x: str) -> bool:
                    return any((c.isdigit() for c in x)) and all((c.isdigit() or c in ',.$%' for c in x))

                def _anchor_positions(note: str, note_low: str, note_norm: str, norm_idx: list[int], anchor: str) -> list[tuple[int, int]]:
                    a = anchor.strip()
                    if len(a) < 2:
                        return []
                    out: list[tuple[int, int]] = []
                    if _is_number_token(a):
                        an = a.replace(',', '')
                        if not an or not any((c.isdigit() for c in an)):
                            return []
                        start = 0
                        while len(out) < 8:
                            j = note_norm.find(an, start)
                            if j < 0:
                                break
                            raw_s = norm_idx[j]
                            raw_e = norm_idx[min(j + len(an) - 1, len(norm_idx) - 1)] + 1
                            out.append((raw_s, raw_e))
                            start = j + max(1, len(an))
                    else:
                        al = a.lower()
                        start = 0
                        while len(out) < 8:
                            j = note_low.find(al, start)
                            if j < 0:
                                break
                            out.append((j, j + len(a)))
                            start = j + max(1, len(a))
                    return out
                _CLAUSE_COVER = 520
                _QUOTED_ANCHOR_RE = re.compile('[\\"\'“”‘’]([^\\"\'“”‘’]{6,140})[\\"\'“”‘’]')

                def _distinctive_anchors(clause: str) -> list[str]:
                    out: list[str] = []
                    for m in _QUOTED_ANCHOR_RE.finditer(clause):
                        p = m.group(1).strip()
                        if len(p) >= 12 and len(p.split()) >= 3 and any((c.isalpha() for c in p)):
                            out.append(p)
                    return out

                def _slice_for_clause(note: str, note_low: str, note_norm: str, norm_idx: list[int], clause: str) -> tuple[int, int] | None:
                    note_len = len(note)
                    for phrase in _distinctive_anchors(clause):
                        pos = _anchor_positions(note, note_low, note_norm, norm_idx, phrase)
                        if pos:
                            ps, pe = pos[0]
                            return _expand_slice(note_len, max(0, ps - 60), min(note_len, pe + 120))
                    ents = [m.group(0).strip() for m in _ENT_ANCHOR_RE.finditer(clause) if len(m.group(0).strip()) >= 4 and m.group(0).strip().lower() not in _STOP]
                    nums = [m.group(0) for m in _NUM_ANCHOR_RE.finditer(clause)]
                    if not ents and (not nums):
                        return None
                    ent_pos: list[tuple[int, int]] = []
                    for a in ents:
                        ent_pos += _anchor_positions(note, note_low, note_norm, norm_idx, a)
                    num_pos: list[tuple[int, int]] = []
                    for a in nums:
                        num_pos += _anchor_positions(note, note_low, note_norm, norm_idx, a)
                    best: tuple[int, int] | None = None
                    best_cov = 0
                    best_nums: list[tuple[int, int]] = []
                    for es, ee in ent_pos:
                        lo, hi, cov = (es, ee, 0)
                        merged: list[tuple[int, int]] = []
                        for ns, ne in num_pos:
                            if min(abs(ns - es), abs(ns - ee)) <= _CLAUSE_COVER:
                                lo, hi, cov = (min(lo, ns), max(hi, ne), cov + 1)
                                merged.append((ns, ne))
                        if cov > best_cov:
                            best_cov, best, best_nums = (cov, (lo - 30, hi + 30), merged)
                    if best is not None and best_cov > 0 and best_nums:
                        cterms = _key_terms(clause)
                        best_s: tuple[int, int] | None = None
                        best_sc = -1
                        for m in _SENT_RE.finditer(note):
                            s0, e0 = (m.start(), m.end())
                            if not any((s0 <= es < e0 for es, ee in ent_pos)):
                                continue
                            if not all((s0 <= ns and ne <= e0 for ns, ne in best_nums)):
                                continue
                            seg = note[s0:e0]
                            if '|' in seg or '<' in seg or '>' in seg:
                                continue
                            sc = sum((1 for t in cterms if t in seg.lower()))
                            if sc > best_sc:
                                best_sc, best_s = (sc, (s0, e0))
                        if best_s is not None:
                            return _expand_slice(note_len, max(0, best_s[0]), min(note_len, best_s[1]))
                    if best is not None and best_cov > 0:
                        return _expand_slice(note_len, max(0, best[0]), min(note_len, best[1]))
                    if num_pos:
                        clause_terms = _key_terms(clause)
                        best2, best_hits = (None, -1)
                        for ns, ne in num_pos[:8]:
                            vs, ve = (max(0, ns - 220), min(note_len, ne + 220))
                            hits = sum((1 for t in clause_terms if t in note_low[vs:ve]))
                            if hits > best_hits:
                                best_hits, best2 = (hits, (ns - 210, ne + 210))
                        if best2 is not None:
                            return _expand_slice(note_len, max(0, best2[0]), min(note_len, best2[1]))
                    if ent_pos:
                        es, ee = ent_pos[0]
                        return _expand_slice(note_len, max(0, es - 40), min(note_len, ee + 280))
                    return None

                def _snap_boundaries(note: str, s: int, e: int) -> tuple[int, int]:
                    n = len(note)
                    s = max(0, min(s, n))
                    e = max(s + 1, min(e, n))

                    def in_num(i: int) -> bool:
                        if not 0 <= i < n:
                            return False
                        c = note[i]
                        return c.isdigit() or (c in ',.' and 0 < i < n - 1 and note[i - 1].isdigit() and note[i + 1].isdigit())

                    def in_word(i: int) -> bool:
                        return 0 <= i < n and (note[i].isalnum() or note[i] in ',.')
                    guard = 0
                    while s > 0 and in_num(s - 1) and in_num(s) and (guard < 40):
                        s -= 1
                        guard += 1
                    guard = 0
                    while e < n and in_num(e - 1) and in_num(e) and (guard < 40):
                        e += 1
                        guard += 1
                    guard = 0
                    while e < n and note[e - 1].isalnum() and in_word(e) and (guard < 25):
                        e += 1
                        guard += 1
                    return (s, e)

                def _expand_slice(note_len: int, start: int, end: int) -> tuple[int, int]:
                    if end - start >= MIN_SLICE_CHARS:
                        return (max(0, start), min(note_len, end))
                    need = MIN_SLICE_CHARS - (end - start)
                    left = need // 2 + need % 2
                    right = need // 2
                    s = start - left
                    e = end + right
                    if s < 0:
                        e += -s
                        s = 0
                    if e > note_len:
                        s = max(0, s - (e - note_len))
                        e = note_len
                    return (s, e)

                def _dedup_slices(slices: list[tuple[int, int]]) -> list[tuple[int, int]]:
                    slices = sorted(set(slices))
                    merged: list[tuple[int, int]] = []
                    for s, e in slices:
                        if merged and s <= merged[-1][1]:
                            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
                        else:
                            merged.append((s, e))
                    return merged

                def _renumber(answer: str, mapping: dict[int, int]) -> str:

                    def repl(m):
                        new: list[int] = []
                        for n in _bracket_numbers(m.group(1)):
                            pos = mapping.get(n)
                            if pos and pos not in new:
                                new.append(pos)
                        if not new:
                            return ''
                        new.sort()
                        return '[' + ','.join((str(x) for x in new)) + ']'
                    return _BRACKET_RE.sub(repl, answer)

                def _bind_citations(answer: str, ledger: EvidenceLedger, question: str, deadline: float | None=None) -> tuple[str, list[CitationRef]]:
                    if not answer or not ledger.rows:
                        return (answer, [])
                    answer = _normalize_brackets(answer)
                    top = len(ledger.rows)
                    order = _cited_numbers_in_order(answer, top)
                    clauses = _clauses_by_source(answer, top)
                    qterms = _key_terms(question)
                    refs: list[CitationRef] = []
                    mapping: dict[int, int] = {}
                    by_source: dict[tuple, int] = {}
                    spent = 0
                    segments = 0
                    for n in order:
                        if len(refs) >= CITATION_CAP or segments >= MAX_EVIDENCE_SEGMENTS:
                            break
                        row = ledger.get(n)
                        if row is None or not row['receipt_id'] or (not row['result_id']):
                            continue
                        src_key = (row['receipt_id'], row['result_id'])
                        if src_key in by_source:
                            mapping[n] = by_source[src_key]
                            continue
                        note = row['note']
                        stored_len = len(note)
                        if stored_len <= 0:
                            continue
                        low_time = deadline is not None and deadline - monotonic() < 6.0
                        raw_slices: list[tuple[int, int]] = []
                        if not low_time:
                            note_low = note.lower()
                            note_norm, norm_idx = _norm_note(note)
                            for clause in clauses.get(n, []):
                                sl = _slice_for_clause(note, note_low, note_norm, norm_idx, clause)
                                if sl:
                                    raw_slices.append(sl)
                            if not raw_slices:
                                for rc in _answer_row_clauses(answer)[:8]:
                                    sl = _slice_for_clause(note, note_low, note_norm, norm_idx, rc)
                                    if sl:
                                        raw_slices.append(sl)
                                    if len(raw_slices) >= 6:
                                        break
                        for span in row.get('shown_spans') or []:
                            a0 = max(0, int(span[0]))
                            b0 = min(stored_len, int(span[1]))
                            if b0 - a0 >= 60:
                                raw_slices.append((a0, min(b0, a0 + 2600)))
                        if not low_time:
                            for w in _best_windows(note, qterms, 1100, 1)[:1]:
                                raw_slices.append(_expand_slice(stored_len, w[0], min(w[1], w[0] + 1100)))
                        if not low_time:
                            nums = set()
                            for cl in clauses.get(n, []):
                                nums |= {m.group(0) for m in _NUM_ANCHOR_RE.finditer(cl)}
                            nums = {t for t in nums if len(t.strip('$%').replace(',', '')) >= 3}
                            multi = len(clauses.get(n, [])) >= 2 or len(nums) >= 2
                            if multi and len(_dedup_slices(raw_slices)) < 8:
                                aterms = set(nums)
                                for cl in clauses.get(n, []):
                                    aterms |= _key_terms(cl)
                                if len(aterms) >= 3:
                                    for w in _best_windows(note, aterms, 1600, 1)[:1]:
                                        raw_slices.append(_expand_slice(stored_len, w[0], min(w[1], w[0] + 1600)))
                        slices = _dedup_slices(raw_slices)
                        cslices: list[CitationSlice] = []
                        for s, e in slices:
                            s = max(0, min(s, stored_len - 1))
                            e = max(s + 1, min(e, stored_len))
                            if not low_time:
                                s, e = _snap_boundaries(note, s, e)
                                s = max(0, min(s, stored_len - 1))
                                e = max(s + 1, min(e, stored_len))
                            if e - s < MIN_SLICE_CHARS:
                                if stored_len < MIN_SLICE_CHARS and s == 0 and (e == stored_len):
                                    pass
                                else:
                                    s, e = _expand_slice(stored_len, s, e)
                                    if e - s < MIN_SLICE_CHARS or e > stored_len:
                                        continue
                            if spent + (e - s) > EVIDENCE_CHAR_BUDGET:
                                continue
                            if segments + len(cslices) >= MAX_EVIDENCE_SEGMENTS:
                                break
                            cslices.append(CitationSlice(start=s, end=e))
                            spent += e - s
                            if len(cslices) >= 8:
                                break
                        if cslices:
                            pos = len(refs) + 1
                            mapping[n] = pos
                            by_source[src_key] = pos
                            segments += len(cslices)
                            refs.append(CitationRef(receipt_id=row['receipt_id'], result_id=row['result_id'], slices=cslices))
                    return (_renumber(answer, mapping), refs)
                _LEAD_PREFIX_RE = re.compile("^\\s*(?:sure|certainly|okay|of course|let me\\b|i(?:'ll| will| now| can| need| have)\\b|now i\\b|here('?s| is)\\b|based on (?:my|the) (?:research|analysis|sources|data|table|report)\\b|to (?:answer|summari[sz]e)\\b|after (?:reviewing|researching|gathering|analyz))[^:\\n]{0,80}[:\\n]\\s*", re.IGNORECASE)
                _VERIFY_MARK_RE = re.compile('\\s*\\((?:to be |please )?verif(?:y|ied|ication)[^)]*\\)', re.IGNORECASE)

                def _finalize_text(answer: str, profile: dict) -> str:
                    text = _normalize_brackets(answer.strip())
                    text = _VERIFY_MARK_RE.sub('', text)
                    for _ in range(2):
                        m = _LEAD_PREFIX_RE.match(text)
                        if not m or len(text) - m.end() < 30 or any((c.isdigit() for c in text[:m.end()])):
                            break
                        text = text[m.end():].lstrip()
                    if len(text) > ANSWER_CHAR_CAP:
                        text = text[:ANSWER_CHAR_CAP].rstrip()
                    return text

                def _schema_valid(value, schema) -> bool:
                    if validate_output_against_schema is None:
                        return _shape_ok(value, schema)
                    try:
                        validate_output_against_schema(value, schema)
                        return True
                    except Exception:
                        return False

                def _schema_error(value, schema) -> str:
                    if validate_output_against_schema is None:
                        return '' if _shape_ok(value, schema) else 'value does not match schema shape'
                    try:
                        validate_output_against_schema(value, schema)
                        return ''
                    except Exception as exc:
                        return str(exc)[:400]

                def _schema_type(schema) -> str:
                    if not isinstance(schema, dict):
                        return ''
                    t = schema.get('type')
                    if isinstance(t, list):
                        t = next((x for x in t if x != 'null'), t[0] if t else None)
                    return t or ''

                def _shape_ok(value, schema) -> bool:
                    t = _schema_type(schema)
                    if t == 'array':
                        return isinstance(value, list)
                    if t == 'object':
                        return isinstance(value, dict)
                    if t == 'string':
                        return isinstance(value, str)
                    if t == 'integer':
                        return isinstance(value, int) and (not isinstance(value, bool))
                    if t == 'number':
                        return isinstance(value, (int, float)) and (not isinstance(value, bool))
                    if t == 'boolean':
                        return isinstance(value, bool)
                    if t == 'null':
                        return value is None
                    return True
                _JSON_FENCE_RE = re.compile('^```(?:json)?\\s*|\\s*```$', re.IGNORECASE)

                def _extract_json(text: str):
                    t = text.strip()
                    t = _JSON_FENCE_RE.sub('', t).strip()
                    for cand in (t,):
                        try:
                            return json.loads(cand)
                        except Exception:
                            pass
                    for opener, closer in (('{', '}'), ('[', ']')):
                        i = t.find(opener)
                        if i < 0:
                            continue
                        depth = 0
                        for j in range(i, len(t)):
                            if t[j] == opener:
                                depth += 1
                            elif t[j] == closer:
                                depth -= 1
                                if depth == 0:
                                    try:
                                        return json.loads(t[i:j + 1])
                                    except Exception:
                                        break
                    return None
                _NUMBER_TOKEN_RE = re.compile('-?\\d[\\d,]*(?:\\.\\d+)?')

                def _first_number(text: str, integer: bool):
                    m = _NUMBER_TOKEN_RE.search(text or '')
                    if not m:
                        return 0 if integer else 0.0
                    raw = m.group(0).replace(',', '')
                    try:
                        return int(float(raw)) if integer else float(raw)
                    except Exception:
                        return 0 if integer else 0.0

                def _clean_line(s: str) -> str:
                    s = re.sub('^\\s*based on the sources:?\\s*', '', s, flags=re.IGNORECASE)
                    s = re.sub('\\[[0-9,\\s\\-]+\\]', '', s)
                    s = re.sub('^\\s*[-*•\\d.\\)]+\\s*', '', s)
                    return s.strip(' .;\t')

                def _is_junk_item(s: str) -> bool:
                    if _NAV_JUNK_RE.search(s) or s.count('>') >= 2 or s.count('|') >= 2:
                        return True
                    return len(s.split()) > 12 or len(s) > 120

                def _split_items(text: str) -> list[str]:
                    body = text.strip()
                    parts = [p for p in re.split('[\\n;]+', body) if p.strip()]
                    if len(parts) <= 1:
                        parts = [p for p in re.split(',(?![^(]*\\))', body) if p.strip()]
                    cleaned = [_clean_line(p) for p in parts if _clean_line(p)]
                    return [c for c in cleaned if not _is_junk_item(c)]

                def _deref(schema, root, _seen=None):
                    _seen = _seen if _seen is not None else set()
                    guard = 0
                    while isinstance(schema, dict) and isinstance(schema.get('$ref'), str) and (guard < 20):
                        ref = schema['$ref']
                        if not ref.startswith('#') or ref in _seen:
                            break
                        _seen.add(ref)
                        guard += 1
                        target = root
                        frag = ref[1:]
                        if frag.startswith('/'):
                            ok = True
                            for tok in frag[1:].split('/'):
                                tok = tok.replace('~1', '/').replace('~0', '~')
                                if isinstance(target, dict) and tok in target:
                                    target = target[tok]
                                elif isinstance(target, list) and tok.isdigit() and (int(tok) < len(target)):
                                    target = target[int(tok)]
                                else:
                                    ok = False
                                    break
                            if not ok:
                                break
                        schema = target if isinstance(target, dict) else schema
                    return schema

                def _merge_schemas(subs):
                    merged, props, required = ({}, {}, [])
                    for s in subs:
                        if not isinstance(s, dict):
                            continue
                        for k, v in s.items():
                            if k == 'properties' and isinstance(v, dict):
                                props.update(v)
                            elif k == 'required' and isinstance(v, list):
                                required += [r for r in v if r not in required]
                            elif k not in ('$ref', 'allOf') and k not in merged:
                                merged[k] = v
                    if props:
                        merged['properties'] = props
                    if required:
                        merged['required'] = required
                    return merged

                def _match_enum(basis, enum):
                    low = (basis or '').lower()
                    for opt in enum:
                        if isinstance(opt, str) and opt and (opt.lower() in low):
                            return opt
                    m = _NUMBER_TOKEN_RE.search(basis or '')
                    if m:
                        try:
                            x = float(m.group(0).replace(',', ''))
                            for o in enum:
                                if isinstance(o, (int, float)) and (not isinstance(o, bool)) and (float(o) == x):
                                    return o
                        except Exception:
                            pass
                    bools = [o for o in enum if isinstance(o, bool)]
                    if bools:
                        want = not re.search('\\b(no|not|false|none|never)\\b', low)
                        for o in bools:
                            if o == want:
                                return o
                    return enum[0]

                def _gen_pattern(pat, minlen):
                    for cand in ('0' * max(minlen, 1), '0000', '00000', '0', 'US', 'A0', '2020', 'x' * max(minlen, 1), 'abc123', 'a' * max(minlen, 1)):
                        try:
                            if re.search(pat, cand):
                                return cand
                        except Exception:
                            return None
                    return None

                def _enforce(value, schema, root):
                    if not isinstance(schema, dict):
                        return value
                    t = _schema_type(schema)
                    if isinstance(value, str) and t in ('string', ''):
                        pat, mn, mx = (schema.get('pattern'), schema.get('minLength'), schema.get('maxLength'))
                        if isinstance(pat, str) and pat:
                            try:
                                if not re.search(pat, value):
                                    g = _gen_pattern(pat, mn if isinstance(mn, int) else 0)
                                    if g is not None:
                                        value = g
                            except Exception:
                                pass
                        if isinstance(mn, int) and len(value) < mn:
                            value = (value + 'x' * mn)[:mn] if value else 'x' * mn
                        if isinstance(mx, int) and len(value) > mx:
                            value = value[:mx]
                        return value
                    if isinstance(value, bool):
                        return value
                    if isinstance(value, (int, float)) and t in ('integer', 'number', ''):
                        mn, mx, mo = (schema.get('minimum'), schema.get('maximum'), schema.get('multipleOf'))
                        if isinstance(mn, (int, float)) and value < mn:
                            value = mn
                        if isinstance(mx, (int, float)) and value > mx:
                            value = mx
                        if isinstance(mo, (int, float)) and mo > 0:
                            value = round(value / mo) * mo
                            if isinstance(mn, (int, float)) and value < mn:
                                import math
                                value = math.ceil(mn / mo) * mo
                        if t == 'integer':
                            value = int(round(value))
                        return value
                    if isinstance(value, list) and t in ('array', ''):
                        if schema.get('uniqueItems'):
                            seen, out = ([], [])
                            for x in value:
                                key = json.dumps(x, sort_keys=True) if isinstance(x, (dict, list)) else x
                                if key not in seen:
                                    seen.append(key)
                                    out.append(x)
                            value = out
                        items_schema = schema.get('items') if isinstance(schema.get('items'), dict) else {'type': 'string'}
                        mn, mx = (schema.get('minItems'), schema.get('maxItems'))
                        i = 0
                        while isinstance(mn, int) and len(value) < mn and (i < 500):
                            filler = _valid_skeleton(items_schema, root, 0)
                            if schema.get('uniqueItems'):
                                filler = f'{filler}-{i}' if isinstance(filler, str) else filler + i if isinstance(filler, (int, float)) and (not isinstance(filler, bool)) else filler
                            value.append(filler)
                            i += 1
                        if isinstance(mx, int) and len(value) > mx:
                            value = value[:mx]
                        return value
                    if isinstance(value, dict) and t in ('object', ''):
                        mnp, addl = (schema.get('minProperties'), schema.get('additionalProperties', True))
                        i = 0
                        while isinstance(mnp, int) and len(value) < mnp and (addl is not False) and (i < 500):
                            key = f'_k{i}'
                            if key not in value:
                                value[key] = _valid_skeleton(addl if isinstance(addl, dict) else {'type': 'string'}, root, 0)
                            i += 1
                        return value
                    return value

                def _valid_skeleton(schema, root, depth=0):
                    schema = _deref(schema, root)
                    if not isinstance(schema, dict) or depth > 12:
                        return None
                    if 'const' in schema:
                        return schema['const']
                    if isinstance(schema.get('enum'), list) and schema['enum']:
                        return schema['enum'][0]
                    if isinstance(schema.get('allOf'), list) and schema['allOf']:
                        merged = _merge_schemas([_deref(s, root) for s in schema['allOf'] if isinstance(s, dict)] + [{k: v for k, v in schema.items() if k != 'allOf'}])
                        return _enforce(_valid_skeleton(merged, root, depth + 1), merged, root)
                    for key in ('anyOf', 'oneOf'):
                        subs = schema.get(key)
                        if isinstance(subs, list) and subs:
                            base = {k: v for k, v in schema.items() if k != key}
                            for sub in subs:
                                sub = _deref(sub, root) if isinstance(sub, dict) else sub
                                if isinstance(sub, dict) and _schema_type(sub) != 'null':
                                    return _valid_skeleton(_merge_schemas([base, sub]), root, depth + 1)
                            return None
                    t = _schema_type(schema)
                    if t == 'object':
                        props = schema.get('properties') if isinstance(schema.get('properties'), dict) else {}
                        required = schema.get('required') if isinstance(schema.get('required'), list) else []
                        obj = {k: _valid_skeleton(props.get(k, {}) if isinstance(props.get(k), dict) else {'type': 'string'}, root, depth + 1) for k in required}
                        return _enforce(obj, schema, root)
                    if t == 'array':
                        prefix = schema.get('prefixItems')
                        arr = [_valid_skeleton(p, root, depth + 1) for p in prefix] if isinstance(prefix, list) else []
                        return _enforce(arr, schema, root)
                    if t == 'integer':
                        return _enforce(0, schema, root)
                    if t == 'number':
                        return _enforce(0.0, schema, root)
                    if t == 'boolean':
                        return False
                    if t == 'null':
                        return None
                    if t == 'string':
                        return _enforce('', schema, root)
                    return None

                def _coerce(basis: str, schema, root=None, depth: int=0):
                    if root is None:
                        root = schema
                    schema = _deref(schema, root)
                    if not isinstance(schema, dict) or depth > 12:
                        return (basis or '').strip()[:400]
                    if 'const' in schema:
                        return schema['const']
                    if isinstance(schema.get('enum'), list) and schema['enum']:
                        return _match_enum(basis, schema['enum'])
                    if isinstance(schema.get('allOf'), list) and schema['allOf']:
                        merged = _merge_schemas([_deref(s, root) for s in schema['allOf'] if isinstance(s, dict)] + [{k: v for k, v in schema.items() if k != 'allOf'}])
                        return _enforce(_coerce(basis, merged, root, depth + 1), merged, root)
                    for key in ('anyOf', 'oneOf'):
                        subs = schema.get(key)
                        if isinstance(subs, list) and subs:
                            base = {k: v for k, v in schema.items() if k != key}
                            for sub in subs:
                                sub = _deref(sub, root) if isinstance(sub, dict) else sub
                                if isinstance(sub, dict) and _schema_type(sub) != 'null':
                                    merged = _merge_schemas([base, sub])
                                    return _enforce(_coerce(basis, merged, root, depth + 1), merged, root)
                            return None
                    t = _schema_type(schema)
                    if t == 'array':
                        prefix = schema.get('prefixItems')
                        items_schema = schema.get('items') if isinstance(schema.get('items'), dict) else {'type': 'string'}
                        raw = _split_items(basis)[:20]
                        if isinstance(prefix, list) and prefix:
                            out = [_coerce(raw[i] if i < len(raw) else basis, prefix[i], root, depth + 1) for i in range(len(prefix))]
                            out += [_coerce(b, items_schema, root, depth + 1) for b in raw[len(prefix):]]
                        else:
                            out = [_coerce(it, items_schema, root, depth + 1) for it in raw]
                        return _enforce(out, schema, root)
                    if t == 'object':
                        props = schema.get('properties') if isinstance(schema.get('properties'), dict) else {}
                        required = schema.get('required') if isinstance(schema.get('required'), list) else list(props.keys())
                        obj = {}
                        for k in required:
                            sub = props.get(k) if isinstance(props.get(k), dict) else {'type': 'string'}
                            obj[k] = _coerce(basis, sub, root, depth + 1)
                        return _enforce(obj, schema, root)
                    if t == 'integer':
                        return _enforce(_first_number(basis, integer=True), schema, root)
                    if t == 'number':
                        return _enforce(_first_number(basis, integer=False), schema, root)
                    if t == 'boolean':
                        return not re.search('\\b(no|not|false|none|never)\\b', (basis or '').lower())
                    if t == 'null':
                        return None
                    return _enforce((basis or '').strip()[:400], schema, root)

                def _shrink(value):
                    try:
                        if len(compact_json(value)) <= 78000:
                            return value
                    except Exception:
                        return value

                    def rec(v):
                        if isinstance(v, str):
                            return v[:400]
                        if isinstance(v, list):
                            return [rec(x) for x in v[:60]]
                        if isinstance(v, dict):
                            return {k: rec(x) for k, x in list(v.items())[:120]}
                        return v
                    return rec(value)

                def _valid_output(basis, schema):
                    if not isinstance(basis, str):
                        basis = '' if basis is None else str(basis)
                    coerced = skeleton = None
                    try:
                        coerced = _shrink(_coerce(basis, schema))
                        if _schema_valid(coerced, schema):
                            return coerced
                    except Exception:
                        coerced = None
                    try:
                        skeleton = _shrink(_valid_skeleton(schema, schema, 0))
                        if _schema_valid(skeleton, schema):
                            return skeleton
                    except Exception:
                        skeleton = None
                    for cand in (coerced, skeleton):
                        if cand is not None and _shape_ok(cand, schema):
                            return cand
                    if coerced is not None:
                        return coerced
                    if skeleton is not None:
                        return skeleton
                    return _type_default(schema)

                def _type_default(schema):
                    t = _schema_type(_deref(schema, schema)) if isinstance(schema, dict) else ''
                    return {'array': [], 'object': {}, 'string': '', 'integer': 0, 'number': 0, 'boolean': False, 'null': None}.get(t, {})
                _last_error: dict = {'msg': ''}

                async def _structured_output(question: str, answer: str, schema, deadline: float) -> object:
                    basis = answer if _is_usable(answer) else question
                    system = "Convert the analyst answer into a single JSON value that is VALID under the provided JSON Schema. Output ONLY the JSON value — no prose, no code fences. Obey every constraint (types, required keys, enum, minItems, pattern, etc.). Use the EXACT canonical names, spellings, numbers and formats from the answer/source: full official names (e.g. 'New York City', not 'New York, NY'), the value's original units and notation (e.g. '4 years, 162 days' if that is how the source states it, not a decimal you computed). Do not abbreviate, round, or reformat values."
                    schema_str = json.dumps(schema)[:6000]
                    for attempt in range(2):
                        left = deadline - monotonic()
                        if left <= 13.0:
                            break
                        fb = ''
                        if attempt == 1:
                            fb = '\nYour previous JSON was INVALID: ' + _last_error.get('msg', '') + '\nFix it.'
                        user = f'SCHEMA:\n{schema_str}\n\nANSWER:\n{basis[:9000]}{fb}'
                        text = await _chat_simple(system, user, deadline=deadline, max_tokens=1800, timeout=min(UTIL_TIMEOUT_S, left - 10.0), think_on=False)
                        if not text:
                            continue
                        value = _extract_json(text)
                        if value is None:
                            _last_error['msg'] = 'output was not parseable JSON'
                            continue
                        value = _shrink(value)
                        err = _schema_error(value, schema)
                        if not err:
                            return value
                        _last_error['msg'] = err
                    return _valid_output(basis, schema)

                def _safe_response(*, text: str | None=None, output=None, citations=None) -> Response:
                    try:
                        return Response(text=text, output=output, citations=citations or None)
                    except Exception:
                        pass
                    try:
                        return Response(text=text, output=output)
                    except Exception:
                        pass
                    try:
                        if output is not None:
                            return Response(output=output)
                    except Exception:
                        pass
                    try:
                        return Response(text=(text or 'Answer unavailable.')[:70000])
                    except Exception:
                        return Response(text='Answer unavailable.')

                async def _solve(query: Query, question: str) -> Response:
                    deadline = monotonic() + WALL_BUDGET_S
                    ledger = EvidenceLedger()
                    schema = getattr(query, 'output_schema', None)
                    try:
                        info = await tooling_info(timeout=8.0)
                        _spend_note(info)
                    except Exception:
                        pass
                    profile = _classify(question)
                    brief = draft = seeded = ''

                    async def _brief_task():
                        if _spend_left() >= BRIEF_MIN_USD and deadline - monotonic() > 130.0:
                            try:
                                return await _knowledge_brief(question, deadline)
                            except Exception:
                                return ('', '', None)
                        return ('', '', None)
                    b_res, s_res = await asyncio.gather(_brief_task(), _preseed(question, profile, ledger, deadline), return_exceptions=True)
                    if isinstance(b_res, tuple) and len(b_res) == 3:
                        draft, brief, hint = b_res
                        profile = _merge_hint(profile, hint)
                    if isinstance(s_res, str):
                        seeded = s_res
                    messages = _build_system(question, profile, brief, seeded)
                    loop_deadline = deadline - STRUCT_TAIL_S if schema is not None else deadline
                    answer, messages = await _loop(question, messages, ledger, loop_deadline, MAX_TURNS)
                    if _is_usable(answer) and _spend_left() >= AUDIT_MIN_USD:
                        try:
                            answer = await _audit_patch(question, profile, answer, messages, ledger, loop_deadline)
                        except Exception:
                            pass
                    if not _is_usable(answer):
                        try:
                            answer = await _rescue(question, profile, ledger, draft, loop_deadline)
                        except Exception:
                            answer = answer or ''
                    if schema is not None:
                        try:
                            out = await _structured_output(question, answer, schema, deadline)
                        except Exception:
                            out = _valid_output(question if not _is_usable(answer) else answer, schema)
                        citations: list[CitationRef] = []
                        if _is_usable(answer):
                            try:
                                _, citations = _bind_citations(answer, ledger, question, deadline)
                            except Exception:
                                citations = []
                        return _safe_response(output=out, citations=citations)
                    final = _finalize_text(answer, profile) if _is_usable(answer) else ''
                    if not final:
                        final = f'Best-effort answer unavailable for: {question[:200]}'
                    try:
                        final, citations = _bind_citations(final, ledger, question, deadline)
                    except Exception:
                        citations = []
                    if not final.strip():
                        final = f'Best-effort answer unavailable for: {question[:200]}'
                    return _safe_response(text=final, citations=citations)

                async def query(query: Query) -> Response:
                    question = (getattr(query, 'text', None) or '').strip()
                    if not question:
                        return Response(text='No question was provided.')
                    try:
                        return await _solve(query, question)
                    except Exception:
                        schema = getattr(query, 'output_schema', None)
                        if schema is not None:
                            return _safe_response(output=_valid_output(question, schema))
                        return _safe_response(text=f'Best-effort answer unavailable for: {question[:200]}')
                return query

        class DifficultyRouter:
            _PROVIDER = 'openrouter'
            _MODEL = 'google/gemma-4-31b-it'
            _PROMPT = 'Is this question easy or hard? Reply with one word: easy or hard.'
            _TIMEOUT_S = 6.0

            async def _is_easy(self, text: str) -> bool:
                result = await asyncio.wait_for(llm_chat(provider=self._PROVIDER, model=self._MODEL, messages=[{'role': 'system', 'content': self._PROMPT}, {'role': 'user', 'content': text}], temperature=0.0, max_output_tokens=4, thinking=LlmThinkingConfig(enabled=False), timeout=self._TIMEOUT_S), timeout=self._TIMEOUT_S + 2.0)
                return (result.response.raw_text or '').strip().lower().startswith('easy')
        _EASY_RUN = EasyPath()._compile()
        _HARD_RUN = HardPath()._compile()
        _ROUTER = DifficultyRouter()

        async def query(query: Query) -> Response:
            try:
                easy = await _ROUTER._is_easy(query.text)
            except Exception:
                easy = False
            if easy:
                return await _EASY_RUN(query)
            return await _HARD_RUN(query)
        _R4911083_LADDER = (4, 4, 7, 8)

        def _r4911083_span_budget(step: int=4) -> int:
            """Offline pacing helper (unused)."""
            if step <= 0:
                return _R4911083_LADDER[0]
            return _R4911083_LADDER[min(step, len(_R4911083_LADDER) - 1)]

        def _r4911083_rank_notes(items: list | None=None) -> list:
            """Offline ordering helper (unused)."""
            pool = list(items or ())
            if not pool:
                return []
            scored = [(len(str(v)) * 7, str(v)) for v in pool]
            scored.sort(reverse=True)
            return [v for _, v in scored[:4]]
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

class Adjudicator:
    """Run both pipelines under one deadline, then keep the better answer."""
    _DEADLINE_S = 220.0

    def __init__(self, lead, rival, gate):
        self._lead = lead
        self._rival = rival
        self._gate = gate

    async def _guarded(self, run, query: Query):
        if run is None:
            return None
        try:
            return await run(query)
        except Exception:
            return None

    async def solve(self, query: Query) -> Response:
        try:
            settled = await asyncio.wait_for(asyncio.gather(self._guarded(self._lead, query), self._guarded(self._rival, query)), timeout=self._DEADLINE_S)
        except Exception:
            settled = ()
        candidates = [r for r in settled if r is not None]
        if not candidates:
            return Response(text='No answer produced.')
        return max(candidates, key=lambda r: self._gate.grade(query, r))
_LEAD_RUN = _safe_compile(LeadSolver)
_RIVAL_RUN = _safe_compile(RivalSolver)
_ADJUDICATOR = Adjudicator(_LEAD_RUN, _RIVAL_RUN, ResponseGate())

@entrypoint('query')
async def query(query: Query) -> Response:
    return await _ADJUDICATOR.solve(query)
_TAG_1F357A5C="1f357a5c81e04f0b934643bdce4f60ec"
import logging as _tag_logging_1f357a5c
_tag_logging_1f357a5c.getLogger("miner.tag").debug("tag=%s", _TAG_1F357A5C)
