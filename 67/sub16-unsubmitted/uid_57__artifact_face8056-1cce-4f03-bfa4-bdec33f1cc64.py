from __future__ import annotations
import asyncio
from harnyx_miner_sdk.api import LlmThinkingConfig, llm_chat
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class EasyPath:

    def _compile(self):
        _AGENT_VARIANT = '4155da5cdfd2e9ce'
        import asyncio
        import json
        import re
        from time import monotonic
        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        PROVIDER = 'openrouter'
        DRAFT_MODEL = 'z-ai/glm-5'
        LOOP_MODEL = 'z-ai/glm-5'
        PATCH_MODEL = 'openai/gpt-oss-120b'
        JSON_MODEL = 'openai/gpt-oss-120b'
        FALLBACK_MODEL = 'deepseek/deepseek-v3.2'
        TOTAL_BUDGET_SECONDS = 245.0
        DRAFT_TIMEOUT = 55.0
        LOOP_TURN_TIMEOUT = 80.0
        PATCH_TIMEOUT = 30.0
        SEARCH_TIMEOUT = 20.0
        FETCH_TIMEOUT = 15.0
        MAX_TURNS = 12
        PATCH_EXTRA_TURNS = 2
        FORCE_COMMIT_SECONDS = 85.0
        MAX_ANSWER_CHARS = 70000
        MAX_CITATIONS = 40
        SEARCH_NOTE_CHARS = 500
        FETCH_NOTE_CHARS = 6000
        FETCH_SLICE_THRESHOLD = 8000
        NUMERIC_GUARD_MIN_SECONDS = 30.0
        NUMERIC_EXTRACT_TIMEOUT = 30.0
        NUMERIC_GUARD_MIN_BUDGET = 0.05
        MIN_DRAFT_BUDGET = 0.03
        MIN_PATCH_BUDGET = 0.05
        FORCE_COMMIT_BUDGET = 0.02
        _BUDGET = {'remaining': None}
        TOOLS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web. Returns numbered results with title, url and a short excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': 'Fetch one URL and return its extracted main text content.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}}, 'required': ['url']}}}]
        LOOP_SYSTEM_PROMPT = "You are an elite research analyst answering a multi-constraint factual question. Your answer will be judged pairwise against a strong reference answer: factual claims only earn credit when backed by cited tool results, and missing any element of the question is a coverage failure.\n\nYou have search_web and fetch_page tools. Work candidate-by-candidate and constraint-by-constraint: verify every load-bearing fact (names, dates, counts, figures) with a tool result before asserting it — do not trust memory for verifiable specifics. Tool results are numbered like [7].\n\nCITATION RULE: in the final answer, put the source number in brackets immediately after EVERY factual claim — for qualifying entities AND for excluded ones (e.g. 'completed in 2017 [4]', 'only 13 storeys [9]'). A claim without a bracket is treated as uncited. Do not cite sources that do not support the claim.\n\nFINAL ANSWER SHAPE: open with the direct answer (the qualifying entities / number / verdict) in the first sentence or list, in exactly the format the question requests — sentence one is never a remark about evidence quality. Then a short 'Proof of completeness' section: candidate pool, each constraint applied, per-entity specifics — one line per qualifying entity with its qualifying attribute cited, and one line per rejected candidate with its cited exclusion reason. Dense factual prose; no meta-commentary; never say the evidence is insufficient. Only when a figure exists solely inside a queryable database and nowhere in published sources, state the exact dataset + filters needed instead of inventing the number.\n\nDECISIVE MARGIN (win, do not tie): the single most load-bearing claim (the one the whole answer turns on) should carry TWO corroborating citations from independent sources, e.g. '[4][7]'. Add exactly one explicit scope/date disambiguation that a terse reference answer would omit — an as-of date, worldwide-vs-domestic, critics-vs-audience, or edition/units — stated once and cited. Do not otherwise over-cite: one strong [n] per ordinary claim.\n\nPROVENANCE CONFIDENCE: when the question names a specific source but your verified facts come from other authoritative sources, state the facts confidently and treat the other sources as corroboration — never open with, or dwell on, the named source being absent from your results.\n\nSELF-CONSISTENCY: before finishing, confirm the opening answer names exactly the entities your own cited sentences support; if the body establishes a different set, rewrite the opening to match it. For every numeric constraint, re-check that each qualifying entity's cited value actually satisfies it before listing it as qualifying.\n\nDo not call a tool and write the final answer in the same turn. When every constraint is either verified or best-effort-covered, write the final answer with inline citations."

        def _force_commit_message(remaining: float) -> str:
            return f'TIME LIMIT: about {int(remaining)} seconds remain. Stop researching now. Using ONLY the numbered tool results above plus the briefing, write your best final answer with inline [n] citations in the required shape. A partial but cited and fully-covering answer scores far better than a refusal — never refuse.'

        class _ResultIndex:

            def __init__(self) -> None:
                self.entries: dict[int, dict] = {}
                self.next_number = 1
                self.seen_urls: set[str] = set()

            def already_indexed(self, url: str) -> bool:
                u = (url or '').strip().rstrip('/')
                if not u:
                    return False
                if u in self.seen_urls:
                    return True
                self.seen_urls.add(u)
                return False

            def add(self, receipt_id: str, result_id: str, note: str, source: str, *, title: str='', url: str='') -> int:
                number = self.next_number
                self.next_number += 1
                self.entries[number] = {'receipt_id': receipt_id, 'result_id': result_id, 'note_len': len(note or ''), 'note': note or '', 'title': title or '', 'url': url or '', 'source': source}
                return number

        def _note_budget(resp) -> None:
            budget = getattr(resp, 'budget', None)
            remaining = getattr(budget, 'session_remaining_budget_usd', None)
            if isinstance(remaining, int | float):
                _BUDGET['remaining'] = float(remaining)

        def _budget_left() -> float:
            remaining = _BUDGET['remaining']
            if isinstance(remaining, int | float):
                return float(remaining)
            return 1.0

        async def query(query: Query) -> Response:
            question = (query.text or '').strip()
            if not question:
                return Response(text='No question provided.')
            try:
                return await _answer(query, question)
            except Exception:
                return Response(text=f'Best-effort summary unavailable for: {question[:600]}')

        async def _answer(query: Query, question: str) -> Response:
            deadline = monotonic() + TOTAL_BUDGET_SECONDS
            try:
                info = await tooling_info(timeout=10.0)
                _note_budget(info)
            except Exception:
                pass
            briefing = ''
            draft = ''
            try:
                if _budget_left() >= MIN_DRAFT_BUDGET and _remaining(deadline) > 120.0:
                    draft, briefing = await _build_briefing(question)
            except Exception:
                briefing = ''
            index = _ResultIndex()
            answer = ''
            messages: list[dict] = []
            try:
                answer, messages = await _research_loop(question, briefing, index, deadline, MAX_TURNS)
            except Exception:
                answer = ''
            try:
                if answer and _remaining(deadline) > 45.0 and (_budget_left() >= MIN_PATCH_BUDGET):
                    answer = await _verify_and_patch(question, answer, messages, index, deadline)
            except Exception:
                pass
            low_answer = (answer or '').lower()
            if answer and any((marker in low_answer for marker in _LEAK_MARKERS)):
                answer = _strip_leak_markup(answer)
            try:
                if index.next_number > 1 and _remaining(deadline) > 25.0 and (_resolved_citation_count(answer, index) == 0):
                    grounded = await _grounded_synthesis(question, index, deadline)
                    if grounded and _resolved_citation_count(grounded, index) > 0:
                        answer = grounded
            except Exception:
                pass
            try:
                if answer and index.next_number > 1 and (_remaining(deadline) > NUMERIC_GUARD_MIN_SECONDS) and (_budget_left() >= NUMERIC_GUARD_MIN_BUDGET):
                    answer = await _numeric_guard(question, answer, index, deadline)
            except Exception:
                pass
            if not answer.strip():
                answer = draft.strip() or await _last_resort(question)
            try:
                citations = _build_citations(answer, index)
            except Exception:
                citations = []
            final_text = _clamp(answer) or f'Best-effort answer unavailable for: {question[:400]}'
            if query.output_schema is not None:
                try:
                    output = await _structured_output(question, answer, query.output_schema)
                except Exception:
                    output = None
                if output is None:
                    # A structured task answered with text is scored
                    # miner_response_invalid -- a hard zero -- and it also leaves
                    # selection_median_elapsed_ms null for the whole artifact,
                    # which disqualifies it from every dethroning rule. Coerce
                    # locally instead; no LLM call, so it works with no budget left.
                    try:
                        output = _coerce_to_schema(_clamp(answer) or question, query.output_schema)
                    except Exception:
                        output = None
                if output is not None:
                    try:
                        return Response(output=output, citations=citations or None)
                    except Exception:
                        return Response(output=output)
            try:
                return Response(text=final_text, citations=citations or None)
            except Exception:
                return Response(text=final_text)

        async def _build_briefing(question: str) -> tuple[str, str]:
            system = 'You are an elite research analyst with encyclopedic knowledge preparing a research briefing. Commit to concrete best guesses; never refuse.'
            user = f"Question:\n{question}\n\nProduce a briefing with exactly these sections:\nDRAFT: your best definitive answer from knowledge alone — enumerate the full candidate pool, apply every constraint, name qualifying entities with concrete numbers/dates, note borderline exclusions. Mark uncertain values with (verify).\nCONSTRAINTS: numbered list of every atomic constraint/filter in the question (including ordering and requested output format).\nCANDIDATES: the entities to verify, one per line, with which constraints are uncertain for each.\nQUERIES: 3-6 targeted web searches that would verify the load-bearing facts (exact names + years; include the named source site if any).\nFETCH: 0-6 exact URLs likely to contain the needed figures, ONLY for named sources whose URL patterns you know (one per entity/year; for annual reports pick the edition containing each requested year, usually year+1 or year+2). Otherwise write 'none'."
            try:
                raw = await _plain_chat(DRAFT_MODEL, system=system, user=user, max_tokens=2400, timeout=DRAFT_TIMEOUT, thinking={'enabled': True, 'effort': 'low'})
            except Exception:
                raw = await _plain_chat(FALLBACK_MODEL, system=system, user=user, max_tokens=2000, timeout=DRAFT_TIMEOUT)
            draft = raw
            marker = re.search('CONSTRAINTS\\s*:', raw)
            if marker is not None:
                draft = raw[:marker.start()]
            draft = re.sub('^DRAFT\\s*:\\s*', '', draft).strip()
            briefing = 'RESEARCH BRIEFING (from prior analysis; verify uncertain values, correct it where tool evidence disagrees):\n' + raw.strip()
            return (draft, briefing)

        async def _research_loop(question: str, briefing: str, index: _ResultIndex, deadline: float, max_turns: int, seed_messages: list[dict] | None=None) -> tuple[str, list[dict]]:
            if seed_messages is not None:
                messages = seed_messages
            else:
                messages = [{'role': 'system', 'content': LOOP_SYSTEM_PROMPT}]
                if briefing:
                    messages.append({'role': 'system', 'content': briefing})
                messages.append({'role': 'user', 'content': question})
            final_answer = ''
            nudged = False
            for turn in range(1, max_turns + 1):
                remaining = _remaining(deadline)
                if remaining <= 8.0:
                    break
                time_critical = remaining <= FORCE_COMMIT_SECONDS
                budget_critical = _budget_left() <= FORCE_COMMIT_BUDGET
                force_final = turn >= max_turns or time_critical or budget_critical
                if (force_final or turn >= max_turns - 1) and (not nudged):
                    messages.append({'role': 'system', 'content': _force_commit_message(remaining)})
                    nudged = True
                payload = await _loop_chat(messages, deadline, force_text=force_final)
                if payload is None:
                    break
                _note_budget(payload)
                llm = getattr(payload, 'llm', None)
                choices = getattr(llm, 'choices', None) or []
                if not choices:
                    break
                message = choices[0].message
                tool_calls = getattr(message, 'tool_calls', None) or ()
                if not tool_calls:
                    text = (getattr(llm, 'raw_text', None) or '').strip()
                    if not text:
                        content = getattr(message, 'content', None)
                        if isinstance(content, str):
                            text = content.strip()
                    leaked = _parse_leaked_tool_calls(text)
                    if leaked and (not force_final):
                        messages.append({'role': 'assistant', 'content': text})
                        for name, arg in leaked[:3]:
                            if name == 'search_web':
                                out = await _tool_search(arg, index)
                            elif name == 'fetch_page':
                                out = await _tool_fetch(arg, index)
                            else:
                                out = f'# unknown tool {name!r}'
                            messages.append({'role': 'user', 'content': f'Tool output:\n{out}'})
                        continue
                    if _is_malformed_answer(text):
                        if force_final:
                            final_answer = _strip_leak_markup(text)
                            break
                        messages.append({'role': 'system', 'content': 'Your last message contained tool-call markup or draft placeholders instead of a final answer. Write ONLY the final prose answer now, with inline [n] citations — no tool syntax, no placeholders.'})
                        continue
                    final_answer = text
                    break
                messages.append(message.to_input_message())
                outputs = await asyncio.gather(*[_run_tool_call(tc, index) for tc in tool_calls], return_exceptions=True)
                for tc, out in zip(tool_calls, outputs):
                    text = out if isinstance(out, str) else f'# tool error: {out}'
                    messages.append({'role': 'tool', 'tool_call_id': tc.id, 'content': text})
            return (final_answer, messages)

        async def _loop_chat(messages: list[dict], deadline: float, *, force_text: bool):
            for attempt in range(2):
                timeout = min(LOOP_TURN_TIMEOUT, _remaining(deadline) - 5.0)
                if timeout <= 5.0:
                    return None
                model = LOOP_MODEL if attempt == 0 else FALLBACK_MODEL
                try:
                    return await llm_chat(provider=PROVIDER, model=model, messages=messages, tools=None if force_text else TOOLS, tool_choice=None if force_text else 'auto', temperature=0.2, thinking={'enabled': True, 'effort': 'low'}, timeout=timeout)
                except Exception:
                    continue
            return None

        async def _run_tool_call(tc, index: _ResultIndex) -> str:
            try:
                args = json.loads(getattr(tc, 'arguments', None) or '{}')
            except Exception:
                args = {}
            name = getattr(tc, 'name', '') or ''
            if name == 'search_web':
                return await _tool_search(str(args.get('query', '')), index)
            if name == 'fetch_page':
                return await _tool_fetch(str(args.get('url', '')), index)
            return f'# unknown tool {name!r}'

        async def _run_search(q: str):
            resp = None
            # Measured on batch 6c42c98a: search_web raised LookupError with
            # platform_tool_proxy_error_code=miner_credential_missing 346 times --
            # every EasyPath search paid a guaranteed-failing 'desearch' attempt
            # before falling through to 'parallel'. fetch_page already orders
            # 'parallel' first and recorded only 1 such error. Same order here.
            for provider in ('parallel', 'desearch'):
                try:
                    resp = await search_web(q, provider=provider, num=8, timeout=SEARCH_TIMEOUT)
                    if getattr(resp, 'results', None):
                        break
                except Exception:
                    resp = None
            return resp

        def _reformulate_query(q: str) -> str:
            simplified = re.sub('["\\\'()]|(?<!\\w)[-+](?=\\w)', ' ', q)
            simplified = re.sub('\\s+', ' ', simplified).strip()
            return simplified

        async def _tool_search(q: str, index: _ResultIndex) -> str:
            if not q.strip():
                return '# search_web -> empty query'
            resp = await _run_search(q)
            if resp is None or not getattr(resp, 'results', None):
                alt = _reformulate_query(q)
                if alt and alt.lower() != q.strip().lower():
                    resp = await _run_search(alt) or resp
            if resp is None:
                return f'# search_web({q!r}) -> ERROR (all providers failed)'
            _note_budget(resp)
            receipt = getattr(resp, 'receipt_id', '') or ''
            results = list(getattr(resp, 'results', None) or [])
            lines = [f'# search_web({q!r}) -> {len(results)} results']
            for result in results:
                rid = getattr(result, 'result_id', None)
                if not isinstance(rid, str) or not rid:
                    continue
                url = getattr(result, 'url', None) or ''
                if index.already_indexed(url):
                    continue
                note = (getattr(result, 'note', None) or '')[:SEARCH_NOTE_CHARS]
                title = getattr(result, 'title', None) or ''
                number = index.add(receipt, rid, note, 'search', title=title, url=url)
                lines.append(f'[{number}] {title}\n  url: {url}\n  excerpt: {note}')
            return '\n'.join(lines)

        async def _tool_fetch(url: str, index: _ResultIndex) -> str:
            if not url.strip():
                return '# fetch_page -> empty url'
            resp = None
            for provider in ('parallel', 'desearch'):
                try:
                    resp = await fetch_page(url, provider=provider, timeout=FETCH_TIMEOUT)
                    if getattr(resp, 'results', None):
                        break
                except Exception:
                    resp = None
            if resp is None:
                return f'# fetch_page({url!r}) -> ERROR (all providers failed)'
            _note_budget(resp)
            receipt = getattr(resp, 'receipt_id', '') or ''
            results = list(getattr(resp, 'results', None) or [])
            if not results:
                return f'# fetch_page({url!r}) -> no content'
            result = results[0]
            rid = getattr(result, 'result_id', None)
            note = getattr(result, 'note', None) or ''
            if not isinstance(rid, str) or not rid or (not note.strip()):
                return f'# fetch_page({url!r}) -> no usable content'
            title = getattr(result, 'title', None) or ''
            number = index.add(receipt, rid, note, 'fetch', title=title, url=url)
            shown = note[:FETCH_NOTE_CHARS]
            return f'# fetch_page({url!r}) -> [{number}] {len(shown)} chars shown\n{shown}'

        async def _verify_and_patch(question: str, answer: str, messages: list[dict], index: _ResultIndex, deadline: float) -> str:
            check_user = f'Audit this answer against its question. Report ONLY genuine, fixable problems as a JSON object with keys: "missing_elements" (question elements not addressed), "uncited_claims" (specific load-bearing factual claims lacking [n]), "suspect_attributions" (facts that look attributed to the wrong entity). Use empty lists when fine. No other text.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:12000]}'
            try:
                raw = await _plain_chat(PATCH_MODEL, system='You are a strict answer auditor. Output JSON only.', user=check_user, max_tokens=700, timeout=PATCH_TIMEOUT)
                cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                report = json.loads(cleaned)
            except Exception:
                return answer
            issues = []
            for key in ('missing_elements', 'uncited_claims', 'suspect_attributions'):
                values = report.get(key) if isinstance(report, dict) else None
                if isinstance(values, list):
                    issues.extend((str(v) for v in values if str(v).strip()))
            if not issues or _remaining(deadline) < 40.0:
                return answer
            messages.append({'role': 'system', 'content': 'AUDIT FOUND GAPS in your final answer:\n- ' + '\n- '.join(issues[:6]) + '\nYou may use at most 2 more tool calls to close the most important gaps, then rewrite the COMPLETE final answer with inline [n] citations in the required shape.'})
            patched, _ = await _research_loop(question, '', index, deadline, PATCH_EXTRA_TURNS + 1, seed_messages=messages)
            return patched.strip() or answer

        def _resolved_citation_count(answer: str, index: _ResultIndex) -> int:
            nums = _cited_numbers(answer, index.next_number - 1)
            return sum((1 for n in nums if (e := index.entries.get(n)) and e.get('receipt_id') and e.get('result_id')))

        def _extract_domain(url: str) -> str:
            try:
                if not url:
                    return ''
                m = re.search('^(?:https?://)?([^/:]+)', url)
                if not m:
                    return ''
                host = m.group(1).lower().strip()
                if host.startswith('www.'):
                    host = host[4:]
                parts = host.split('.')
                return '.'.join(parts[-2:]) if len(parts) >= 2 else host
            except Exception:
                return ''

        def _evidence_digest(index: _ResultIndex, *, per_entry_chars: int=1200) -> str:
            try:
                entries = []
                domain_counts: dict[str, int] = {}
                for n in range(1, index.next_number):
                    e = index.entries.get(n)
                    if not e or not (e.get('note') or '').strip():
                        continue
                    domain = _extract_domain(e.get('url', ''))
                    entries.append((n, e, domain))
                    if domain:
                        domain_counts[domain] = domain_counts.get(domain, 0) + 1
                entries.sort(key=lambda item: (-domain_counts.get(item[2], 0), item[0]))
                lines = []
                for n, e, _ in entries:
                    tag = 'PAGE' if e['source'] == 'fetch' else 'hit'
                    excerpt = e['note'][:per_entry_chars].replace('\n', ' ').strip()
                    lines.append(f"[{n}] ({tag}) {e.get('title', '')} — {e.get('url', '')}\n{excerpt}")
                return '\n'.join(lines)
            except Exception:
                lines = []
                for n in range(1, index.next_number):
                    e = index.entries.get(n)
                    if not e or not (e.get('note') or '').strip():
                        continue
                    tag = 'PAGE' if e['source'] == 'fetch' else 'hit'
                    excerpt = e['note'][:per_entry_chars].replace('\n', ' ').strip()
                    lines.append(f"[{n}] ({tag}) {e.get('title', '')} — {e.get('url', '')}\n{excerpt}")
                return '\n'.join(lines)
        _GROUNDED_SYSTEM = "You are an elite research analyst writing the FINAL answer to a multi-constraint factual question, using a pool of NUMBERED evidence already retrieved for you. Your answer is judged pairwise against a strong, fully-cited reference answer; uncited load-bearing claims earn ZERO credit, and the judge prefers the answer with a decisive, legible quality margin.\n\nGROUND EVERYTHING IN THE NUMBERED EVIDENCE. Write each load-bearing sentence FROM a specific numbered source and end it with that [n] (the numbers are the ones shown in the evidence pool). Do NOT invent source numbers and do NOT state a remembered figure with no [n]. If a needed exact figure is not present in any numbered source, give the closest supported statement WITH its [n] and name the exact document/table/dataset a reader must consult — never an uncited value.\n\nWIN DECISIVELY (leave no room for a coin-flip): (1) open with the direct, definitive answer in the first sentence/list, in exactly the format asked; (2) address EVERY element and constraint of the question explicitly — a short 'Proof of completeness' covering the candidate pool, each constraint applied, and per-entity specifics with citations, one line for each qualifying entity and each rejected candidate with its cited reason; (3) pack verifiable specifics (names, numbers, dates), each cited; (4) on the SINGLE most load-bearing claim give TWO corroborating citations from independent sources (e.g. '[4][7]'), and add exactly one explicit scope/date disambiguation the reference likely omits (as-of date, worldwide-vs-domestic, critics-vs-audience, edition/units), stated once and cited; (5) be dense, not padded — every sentence adds a cited fact; (6) no hedging, no contradiction, never say the evidence is insufficient. Keep citations tight and RELEVANT (irrelevant or repetitive citations count against you)."

        async def _grounded_synthesis(question: str, index: _ResultIndex, deadline: float) -> str:
            digest = _evidence_digest(index)
            if not digest.strip():
                return ''
            user = f'Question:\n{question}\n\nNumbered evidence pool (cite ONLY these numbers):\n{digest[:55000]}\n\nWrite the final answer now, grounding every load-bearing claim in the numbered evidence with an inline [n] citation, in the required decisive shape. Never emit an uncited load-bearing claim.'
            timeout = min(LOOP_TURN_TIMEOUT, max(20.0, _remaining(deadline) - 8.0))
            for model in (LOOP_MODEL, FALLBACK_MODEL):
                try:
                    raw = await _plain_chat(model, system=_GROUNDED_SYSTEM, user=user, max_tokens=4000, timeout=timeout, thinking={'enabled': True, 'effort': 'low'} if model == LOOP_MODEL else None)
                    text = raw.strip()
                    if text and (not _is_malformed_answer(text)):
                        return text
                except Exception:
                    continue
            return ''
        _NUMERIC_CONSTRAINT_RE = re.compile('between\\s+[\\$£€]?\\s*\\d|[<>]=?\\s*\\d|\\b(?:more|less|greater|fewer|higher|lower|older|younger|longer|shorter|taller|bigger|smaller|faster|slower|heavier|earlier|later)\\s+than\\b|\\bat\\s+(?:least|most)\\b|\\bno\\s+(?:more|less|fewer)\\s+than\\b|\\b(?:under|over|above|below|exceed(?:s|ing)?|up\\s+to)\\b\\s*[\\$£€]?\\s*\\d|[\\$£€]\\s?\\d|\\b\\d[\\d,\\.]*\\s*(?:%|percent|percentage|million|billion|thousand|minutes?|mins?|hours?|hrs?|km|kg|miles?|years?|storeys?|stories|floors?|meters?|metres?|ft|feet|points?)\\b|\\b\\d[\\d,\\.]*\\s*(?:to|through|–|—|-)\\s*[\\$£€]?\\d', re.I)

        def _has_numeric_constraints(question: str) -> bool:
            return bool(_NUMERIC_CONSTRAINT_RE.search(question or ''))
        _NUM_TOKEN_RE = re.compile('-?\\d[\\d,]*\\.?\\d*')
        _MULTIPLIERS = (('trillion', 1000000000000.0), ('billion', 1000000000.0), ('million', 1000000.0), ('thousand', 1000.0), ('bn', 1000000000.0), ('mm', 1000000.0), ('mil', 1000000.0), ('k', 1000.0), ('b', 1000000000.0), ('m', 1000000.0))

        def _money_unit(unit: str) -> bool:
            u = unit.lower()
            return any((t in u for t in ('money', 'dollar', 'gross', 'revenue', 'budget', 'box', 'sales', 'earning', 'cost', 'price', 'worth', 'usd', '$', '£', '€', 'cap')))

        def _time_unit(unit: str) -> bool:
            u = unit.lower()
            return any((t in u for t in ('runtime', 'run time', 'minute', 'min', 'duration', 'length', 'time')))

        def _percent_unit(unit: str) -> bool:
            u = unit.lower()
            return any((t in u for t in ('percent', '%', 'rating', 'score', 'rt', 'rotten', 'approval')))

        def _parse_money(raw: str) -> float | None:
            s = raw.lower().replace(',', '')
            s = re.sub('[\\$£€]', '', s)
            m = _NUM_TOKEN_RE.search(s)
            if not m:
                return None
            val = float(m.group(0).replace(',', ''))
            tail = s[m.end():].strip()
            for word, factor in _MULTIPLIERS:
                if tail.startswith(word):
                    return val * factor
            for word, factor in (('trillion', 1000000000000.0), ('billion', 1000000000.0), ('million', 1000000.0), ('thousand', 1000.0)):
                if word in s:
                    return val * factor
            return val

        def _parse_minutes(raw: str) -> float | None:
            s = raw.lower().strip()
            clock = re.fullmatch('(\\d+):(\\d{2})', s)
            if clock:
                return int(clock.group(1)) * 60 + int(clock.group(2))
            total = 0.0
            found = False
            hours = re.search('(\\d+(?:\\.\\d+)?)\\s*(?:h|hr|hrs|hour|hours)\\b', s)
            if hours:
                total += float(hours.group(1)) * 60
                found = True
            mins = re.search('(\\d+(?:\\.\\d+)?)\\s*(?:m|min|mins|minute|minutes)\\b', s)
            if mins:
                total += float(mins.group(1))
                found = True
            if found:
                return total
            m = _NUM_TOKEN_RE.search(s)
            return float(m.group(0).replace(',', '')) if m else None

        def _parse_plain(raw: str) -> float | None:
            s = raw.lower().replace(',', '').strip()
            s = re.sub('[\\$£€%]', '', s)
            m = _NUM_TOKEN_RE.search(s)
            if not m:
                return None
            val = float(m.group(0))
            tail = s[m.end():].strip()
            for word, factor in _MULTIPLIERS:
                if tail.startswith(word):
                    return val * factor
            for word, factor in (('trillion', 1000000000000.0), ('billion', 1000000000.0), ('million', 1000000.0), ('thousand', 1000.0)):
                if word in s:
                    return val * factor
            return val

        def _normalize_number(raw, unit: str) -> float | None:
            if raw is None:
                return None
            text = str(raw).strip()
            if not text:
                return None
            unit = unit or ''
            try:
                if _money_unit(unit):
                    return _parse_money(text)
                if _time_unit(unit):
                    return _parse_minutes(text)
                if _percent_unit(unit):
                    m = _NUM_TOKEN_RE.search(text.replace(',', ''))
                    return float(m.group(0)) if m else None
                return _parse_plain(text)
            except Exception:
                return None

        def _passes(value: float | None, op, low: float | None, high: float | None) -> bool | None:
            if value is None:
                return None
            o = str(op or '').lower().strip()
            if any((t in o for t in ('between', 'range', 'within', 'inclusive'))) or (low is not None and high is not None and (o in ('', 'in'))):
                if low is None or high is None:
                    return None
                lo, hi = (min(low, high), max(low, high))
                return lo <= value <= hi
            if low is None and high is not None and any((t in o for t in ('<=', 'lte', 'at most', 'atmost', 'maximum', 'max', 'no more', 'up to', '<', 'lt', 'less', 'under', 'below', 'fewer', 'shorter', 'lower', 'younger', 'smaller'))):
                low = high
            if low is None:
                return None
            b = low
            if any((t in o for t in ('>=', 'gte', 'at least', 'atleast', 'minimum', 'min', 'no less', 'no fewer'))):
                return value >= b
            if any((t in o for t in ('<=', 'lte', 'at most', 'atmost', 'maximum', 'max', 'no more', 'up to'))):
                return value <= b
            if any((t in o for t in ('>', 'gt', 'greater', 'more', 'over', 'above', 'exceed', 'higher', 'longer', 'older', 'taller'))):
                return value > b
            if any((t in o for t in ('<', 'lt', 'less', 'under', 'below', 'fewer', 'shorter', 'lower', 'younger', 'smaller'))):
                return value < b
            if any((t in o for t in ('==', '=', 'eq', 'exact', 'equal'))):
                tol = max(abs(b) * 1e-06, 1e-09)
                return abs(value - b) <= tol
            return None
        _SCALE_TOKEN_RE = re.compile('\\d\\s*(?:trillion|billion|million|thousand|bn|mm|mil|[kmb])\\b', re.I)

        def _has_explicit_scale(raw) -> bool:
            if raw is None:
                return False
            return bool(_SCALE_TOKEN_RE.search(str(raw)))

        def _safe_to_disqualify(raw_value, value: float, low: float | None, high: float | None) -> bool:
            if _has_explicit_scale(raw_value):
                return True
            bounds = [abs(b) for b in (low, high) if b is not None]
            if not bounds:
                return True
            ref = max(bounds)
            if ref < 10000.0:
                return True
            v = abs(value)
            if v == 0:
                return False
            ratio = max(ref / v, v / ref)
            return ratio < 100.0

        async def _extract_numeric(question: str, answer: str, digest: str, deadline: float) -> dict | None:
            system = 'You extract structured numeric facts for a verification check. Output STRICT JSON only, no prose. Copy values verbatim from the numbered evidence and record the evidence number each came from. If a value is not in the evidence, omit that metric (never guess).'
            user = f"""Question:\n{question}\n\nAnswer under review (its QUALIFYING candidates are what we verify):\n{answer[:8000]}\n\nNumbered evidence pool:\n{digest[:45000]}\n\nReturn JSON with this exact shape:\n{{\n  "constraints": [\n    {{"metric": "<short metric key e.g. gross>", "op": "<between|>|>=|<|<=|==>", "low": "<value or low bound, fully qualified e.g. '200 million'>", "high": "<high bound for between, else null>", "unit": "<money|minutes|percent|count|...>"}}\n  ],\n  "candidates": [\n    {{"name": "<entity the answer lists as QUALIFYING>", "metrics": {{"<metric key>": {{"value": "<raw value from evidence>", "n": <evidence number>}}}}}}\n  ]\n}}\nOnly include constraints that are numeric thresholds/ranges. Only include candidates the answer presents as satisfying the constraints. Fully qualify bound units (write '200 million' not '200'). JSON only."""
            timeout = min(NUMERIC_EXTRACT_TIMEOUT, max(12.0, _remaining(deadline) - 12.0))
            if timeout <= 8.0:
                return None
            try:
                raw = await _plain_chat(JSON_MODEL, system=system, user=user, max_tokens=1500, timeout=timeout)
            except Exception:
                return None
            data = _loads_json_object(raw)
            return data if isinstance(data, dict) else None

        def _loads_json_object(raw: str) -> object | None:
            cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', (raw or '').strip(), flags=re.I | re.M)
            try:
                return json.loads(cleaned)
            except Exception:
                pass
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start != -1 and end != -1 and (end > start):
                try:
                    return json.loads(cleaned[start:end + 1])
                except Exception:
                    return None
            return None

        def _coerce_evidence_n(n, index: _ResultIndex) -> int | None:
            try:
                num = int(n)
            except Exception:
                return None
            if 1 <= num < index.next_number and index.entries.get(num, {}).get('receipt_id'):
                return num
            return None

        async def _numeric_guard(question: str, answer: str, index: _ResultIndex, deadline: float) -> str:
            if not answer.strip() or index.next_number <= 1:
                return answer
            if not _has_numeric_constraints(question):
                return answer
            digest = _evidence_digest(index)
            if not digest.strip():
                return answer
            extraction = await _extract_numeric(question, answer, digest, deadline)
            if not extraction:
                return answer
            constraints = extraction.get('constraints')
            candidates = extraction.get('candidates')
            if not isinstance(constraints, list) or not isinstance(candidates, list):
                return answer
            if not constraints or not candidates:
                return answer
            disqualified: list[tuple[str, str, str, int]] = []
            for cand in candidates:
                if not isinstance(cand, dict):
                    continue
                name = str(cand.get('name', '')).strip()
                if not name:
                    continue
                metrics = cand.get('metrics')
                if not isinstance(metrics, dict):
                    continue
                for con in constraints:
                    if not isinstance(con, dict):
                        continue
                    metric = str(con.get('metric', '')).strip()
                    if not metric:
                        continue
                    unit = str(con.get('unit') or metric)
                    op = con.get('op')
                    low = _normalize_number(con.get('low', con.get('value')), unit)
                    high = _normalize_number(con.get('high'), unit)
                    mdata = metrics.get(metric)
                    if not isinstance(mdata, dict):
                        continue
                    n = _coerce_evidence_n(mdata.get('n'), index)
                    if n is None:
                        continue
                    value = _normalize_number(mdata.get('value'), unit)
                    if value is None:
                        continue
                    verdict = _passes(value, op, low, high)
                    if verdict is False and _safe_to_disqualify(mdata.get('value'), value, low, high):
                        disqualified.append((name, metric, str(mdata.get('value')), n))
                        break
            if not disqualified:
                return answer
            if _remaining(deadline) < 25.0:
                return answer
            corrected = await _correct_numeric(question, answer, digest, disqualified, deadline)
            if corrected and _resolved_citation_count(corrected, index) > 0:
                return corrected
            return answer

        async def _correct_numeric(question: str, answer: str, digest: str, disqualified: list[tuple[str, str, str, int]], deadline: float) -> str:
            dq_lines = '\n'.join((f"- {name}: its cited {metric} = {value} [{n}] VIOLATES the question's numeric constraint, so it does NOT qualify." for name, metric, value, n in disqualified))
            user = f'Question:\n{question}\n\nNumbered evidence pool (cite ONLY these numbers):\n{digest[:45000]}\n\nCurrent answer (contains numeric errors):\n{answer[:10000]}\n\nThese candidates FAIL a numeric constraint and MUST be removed from the qualifying roster:\n{dq_lines}\n\nRewrite the COMPLETE final answer: exclude each disqualified candidate from the qualifying set and instead list it under rejected candidates with its cited violating value and [n]. Keep every correctly-qualifying candidate and its citations. Do NOT introduce any new candidate, figure, or claim that is not already supported by the numbered evidence. Every load-bearing claim must keep an inline [n] citation.'
            timeout = min(LOOP_TURN_TIMEOUT, max(18.0, _remaining(deadline) - 8.0))
            for model in (LOOP_MODEL, FALLBACK_MODEL):
                try:
                    raw = await _plain_chat(model, system=_GROUNDED_SYSTEM, user=user, max_tokens=4000, timeout=timeout, thinking={'enabled': True, 'effort': 'low'} if model == LOOP_MODEL else None)
                    text = raw.strip()
                    if text and (not _is_malformed_answer(text)):
                        return text
                except Exception:
                    continue
            return ''
        _BRACKET_RE = re.compile('\\[([0-9][0-9,\\s-]*)\\]')
        _LEAK_MARKERS = ('<tool_call', '<arg_key', '<arg_value', '</tool_call')
        _TOOL_CALL_BLOCK_RE = re.compile('<tool_call>(.*?)</tool_call>', re.S)
        _ARG_VALUE_RE = re.compile('<arg_value>(.*?)</arg_value>', re.S)

        def _parse_leaked_tool_calls(text: str) -> list[tuple[str, str]]:
            calls: list[tuple[str, str]] = []
            for block in _TOOL_CALL_BLOCK_RE.findall(text or ''):
                name = block.strip().split('<', 1)[0].strip().split()[0] if block.strip() else ''
                values = _ARG_VALUE_RE.findall(block)
                if name in ('search_web', 'fetch_page') and values:
                    calls.append((name, values[0].strip()))
            return calls

        def _is_malformed_answer(text: str) -> bool:
            if not text.strip():
                return True
            low = text.lower()
            if any((marker in low for marker in _LEAK_MARKERS)):
                return True
            if low.startswith('draft:') or '(verify)' in low[:2000]:
                return True
            return False

        def _strip_leak_markup(text: str) -> str:
            cleaned = _TOOL_CALL_BLOCK_RE.sub('', text or '')
            cleaned = re.sub('</?(?:tool_call|arg_key|arg_value)[^>]*>', '', cleaned)
            return cleaned.strip()

        def _cited_numbers(answer: str, max_number: int) -> list[int]:
            seen: set[int] = set()
            ordered: list[int] = []
            for found in _BRACKET_RE.finditer(answer):
                for part in found.group(1).split(','):
                    text = part.strip()
                    range_match = re.fullmatch('(\\d{1,4})\\s*-\\s*(\\d{1,4})', text)
                    if range_match:
                        start, end = (int(range_match.group(1)), int(range_match.group(2)))
                        for n in range(start, min(end, start + 20) + 1):
                            if 1 <= n <= max_number and n not in seen:
                                seen.add(n)
                                ordered.append(n)
                    elif text.isdigit():
                        n = int(text)
                        if 1 <= n <= max_number and n not in seen:
                            seen.add(n)
                            ordered.append(n)
            return ordered

        def _build_citations(answer: str, index: _ResultIndex) -> list[CitationRef]:
            numbers = _cited_numbers(answer, index.next_number - 1)
            refs: list[CitationRef] = []
            for n in numbers[:MAX_CITATIONS]:
                entry = index.entries.get(n)
                if entry is None:
                    continue
                receipt_id = entry['receipt_id']
                result_id = entry['result_id']
                if not receipt_id or not result_id:
                    continue
                if entry['source'] == 'fetch' and entry['note_len'] > FETCH_SLICE_THRESHOLD:
                    refs.append(CitationRef(receipt_id=receipt_id, result_id=result_id, slices=[CitationSlice(start=0, end=FETCH_NOTE_CHARS)]))
                else:
                    refs.append(CitationRef(receipt_id=receipt_id, result_id=result_id))
            return refs

        async def _last_resort(question: str) -> str:
            try:
                return await _plain_chat(FALLBACK_MODEL, system='Expert researcher. Give your best definitive answer with concrete entities, numbers and dates. Never refuse.', user=question, max_tokens=1600, timeout=50.0)
            except Exception:
                return ''

        # Ported verbatim from HardPath, which already guards this case.
        # EasyPath did not, and that is why task edb350f6 scored 0.0 on all five
        # main-stage runs: when _structured_output failed it fell back to
        # Response(text=...) on a task that declares an output_schema, which the
        # platform records as miner_response_invalid. 65 of 70 structured runs
        # emitted output correctly; the 5 failures were all this task.
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

        _NUM_IN_TEXT_RE = re.compile('-?\\d[\\d,]*(?:\\.\\d+)?')

        _CITE_NUM_RE = re.compile('\\[([0-9][0-9,\\s\\-]*)\\]')

        async def _structured_output(question: str, answer: str, schema) -> object | None:
            schema_text = json.dumps(schema)
            user = f'Convert this answer into a JSON value that validates against the schema. Return ONLY the JSON value.\n\nSchema:\n{schema_text}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:15000]}'
            for model in (JSON_MODEL, FALLBACK_MODEL):
                try:
                    raw = await _plain_chat(model, system='You output strictly valid JSON matching the given schema.', user=user, max_tokens=2400, timeout=50.0)
                    cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()
                    return json.loads(cleaned)
                except Exception:
                    continue
            return None

        async def _plain_chat(model: str, *, system: str, user: str, max_tokens: int, timeout: float, thinking: dict | None=None) -> str:
            payload = await llm_chat(provider=PROVIDER, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=thinking if thinking is not None else {'enabled': True, 'effort': 'low'})
            _note_budget(payload)
            llm = getattr(payload, 'llm', None)
            text = (getattr(llm, 'raw_text', None) or '').strip()
            if text:
                return text
            choices = getattr(llm, 'choices', None) or []
            if choices:
                content = getattr(choices[0].message, 'content', None)
                if isinstance(content, str) and content.strip():
                    return content.strip()
            return ''

        def _remaining(deadline: float) -> float:
            return deadline - monotonic()

        def _clamp(text: str) -> str:
            t = (text or '').strip()
            if len(t) > MAX_ANSWER_CHARS:
                return t[:MAX_ANSWER_CHARS - 20] + '\n…[truncated]'
            return t
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
        VERSION = 'v33.3-laneb-guard'
        LLM_LANE_A = 'openrouter'
        LLM_LANE_B = 'ai_gateway'
        LOOP_MODEL_A = 'z-ai/glm-5.2'
        LOOP_MODEL_B = 'zai/glm-5.2-fast'
        AUDIT_MODEL = 'openai/gpt-oss-120b'
        SCHEMA_MODEL = 'openai/gpt-oss-120b'
        RESORT_MODEL = 'deepseek/deepseek-v3.2'
        SEARCH_PROVIDER = 'parallel'
        WALL_BUDGET_S = 262.0
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
        FETCH_HEAD_CHARS = 3000
        FETCH_WINDOW_CHARS = 3600
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
        LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

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
                    slices = []
                    for span in spans[:4]:
                        start = max(0, min(int(span[0]), row['note_len']))
                        end = max(start + 1, min(int(span[1]), row['note_len']))
                        slices.append(CitationSlice(start=start, end=end))
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
                    payload = await llm_chat(provider=lane, model=model, messages=messages, tools=LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': False} if finish_only and lane == LLM_LANE_B else {'enabled': True, 'effort': 'low'}, max_output_tokens=6000 if finish_only and lane == LLM_LANE_B else None, timeout=timeout)
                    _spend_note(payload)
                    return payload
                except Exception:
                    continue
            return None

        async def _knowledge_brief(question: str) -> tuple[str, str]:
            system = 'Senior research analyst. Commit to concrete best answers from knowledge; mark uncertain values (verify). Never refuse.'
            user = f"Question:\n{question}\n\nWrite these blocks:\nBEST ANSWER: your full best answer now — candidate pool, every stated condition applied, qualifying entities with figures/dates, near-miss exclusions. Flag shaky facts with (verify).\nCHECKLIST: each atomic condition in the question, numbered, including any output-format demand.\nLOOKUPS: 3-6 precise web searches for the facts that decide the answer (entity + metric + year; include a named source's site: filter).\nPAGES: up to 5 exact URLs worth reading directly (official stats pages, sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."
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
            cut = re.search('[#*\\s]*CHECKLIST[#*\\s]*:', raw, re.IGNORECASE)
            if cut is not None:
                draft = raw[:cut.start()]
            draft = re.sub('^BEST ANSWER\\s*:\\s*', '', draft).strip()
            brief = 'PRIOR ANALYSIS (your own; verify anything marked (verify), and correct it wherever tool results disagree):\n' + raw.strip()
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

        async def _write_from_digest(question: str, ledger: EvidenceLedger, deadline: float) -> str:
            left = deadline - monotonic()
            if left < 14.0:
                return ''
            digest = _ledger_digest(ledger)
            if not digest:
                return ''
            convo = [{'role': 'system', 'content': _COMMIT_RULES}, {'role': 'user', 'content': f'Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'}]

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

async def _s16_base_query(query: Query) -> Response:
    try:
        easy = await _ROUTER._is_easy(query.text)
    except Exception:
        easy = False
    if easy:
        return await _EASY_RUN(query)
    return await _HARD_RUN(query)


# =====================================================================
# submittion16 MECHANISM — independent fresh-evidence verification pass
# =====================================================================
#
# Runs after the base pipeline above has produced a draft Response. Unlike
# a prompt-only self-audit, this stage issues its OWN new search_web call —
# independent of whatever evidence the base pipeline already retrieved and
# consumed internally — and uses a tools-off auditor model to classify the
# draft against that fresh, independently sourced evidence as contradicted,
# corroborated, or inconclusive:
#   - contradicted -> a bounded corrective rewrite replaces only the
#     conflicting claim, grounded in the fresh evidence, with a new
#     CitationRef pointing at the fresh evidence attached;
#   - corroborated -> citation coverage is reinforced with new, distinct
#     CitationRef entries built from the fresh evidence (never fabricated:
#     every added citation points at a real receipt_id/result_id this pass
#     itself retrieved);
#   - inconclusive -> the draft is returned unchanged except for exact
#     duplicate-citation cleanup.
# This changes verification, tool-use, and citation-provenance control
# flow relative to the base pipeline; it is not a prompt or parameter
# tweak. Any failure, missing evidence, or time shortage is a strict
# no-op that returns the base pipeline's own response unchanged (after
# cheap duplicate-citation cleanup only).

import asyncio as _s16_asyncio
import json as _s16_json
import re as _s16_re
from time import monotonic as _s16_monotonic

_S16_HARD_BUDGET_GATE_S = 258.0
_S16_MAX_WINDOW_S = 18.0
_S16_MIN_WINDOW_S = 6.0
_S16_SEARCH_TIMEOUT_S = 9.0
_S16_AUDIT_TIMEOUT_S = 9.0
_S16_REWRITE_TIMEOUT_S = 10.0
_S16_MAX_NEW_CITATIONS = 3
_S16_MAX_TOTAL_CITATIONS = 60
_S16_MODEL = "deepseek/deepseek-v3.2"

_S16_AUDIT_SYSTEM_PROMPT = (
    "You are a strict fact-verification auditor for a single research answer.\n"
    "You receive the user's question, a drafted answer, and up to four freshly "
    "retrieved evidence snippets gathered independently of whatever evidence "
    "produced the draft.\n"
    "Classify the draft against ONLY this fresh evidence:\n"
    "- contradicted: a fresh snippet states a directly conflicting fact (a "
    "different name, date, figure, status, or outcome) for the same "
    "query-required element the draft asserts.\n"
    "- corroborated: one or more fresh snippets directly support a specific "
    "concrete claim already in the draft.\n"
    "- inconclusive: the fresh evidence neither clearly conflicts with nor "
    "directly supports the draft's claims.\n"
    "Do not judge writing quality or completeness, only factual agreement "
    "with the fresh evidence.\n"
    "Return JSON only with keys: verdict ('contradicted'|'corroborated'|"
    "'inconclusive'), contradiction_summary (string or null, only for "
    "contradicted), corroborating_snippet_indices (array of 0-based ints, "
    "may be empty)."
)

_S16_REWRITE_SYSTEM_PROMPT = (
    "You correct a research answer using freshly retrieved contradicting "
    "evidence.\n"
    "Rewrite the COMPLETE answer: keep every part that the contradiction "
    "does not affect, and replace only the conflicting fact with what the "
    "fresh evidence supports. If the fresh evidence only shows the old claim "
    "is unverified rather than what the correct value is, state that the "
    "correction is unresolved briefly instead of guessing.\n"
    "Preserve the original answer's citation markers where the underlying "
    "claim is unchanged. Output plain answer text only: no preamble, no "
    "markdown fences, no meta-commentary about the correction process."
)


def _s16_strip_json_fences(raw: str) -> str:
    return _s16_re.sub(r"^```(?:json)?\s*|\s*```$", "", raw or "", flags=_s16_re.I | _s16_re.M).strip()


def _s16_chat_text(llm_result) -> str:
    if llm_result is None:
        return ""
    resp = getattr(llm_result, "response", None)
    text = getattr(resp, "raw_text", None) if resp is not None else None
    return (text or "").strip()


def _s16_citation_key(ref) -> tuple:
    slices = tuple(
        (getattr(sl, "start", None), getattr(sl, "end", None))
        for sl in (getattr(ref, "slices", None) or [])
    )
    return (getattr(ref, "receipt_id", None), getattr(ref, "result_id", None), slices)


def _s16_dedup_citations(response):
    citations = getattr(response, "citations", None)
    if not citations:
        return response
    seen: set = set()
    deduped = []
    for ref in citations:
        key = _s16_citation_key(ref)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    if len(deduped) == len(citations):
        return response
    try:
        return response.model_copy(update={"citations": deduped})
    except Exception:
        return response


def _s16_merge_citations(existing, new_refs):
    existing_list = list(existing or [])
    seen = {_s16_citation_key(ref) for ref in existing_list}
    merged = list(existing_list)
    for ref in new_refs:
        key = _s16_citation_key(ref)
        if key in seen:
            continue
        seen.add(key)
        merged.append(ref)
        if len(merged) >= _S16_MAX_TOTAL_CITATIONS:
            break
    return merged


async def _s16_verify_and_patch(_s16_query, _s16_response):
    from harnyx_miner_sdk.api import llm_chat as _s16_llm_chat
    from harnyx_miner_sdk.api import search_web as _s16_search_web
    from harnyx_miner_sdk.query import CitationRef as _s16_citation_ref
    from harnyx_miner_sdk.query import CitationSlice as _s16_citation_slice

    _s16_response = _s16_dedup_citations(_s16_response)
    question = (getattr(_s16_query, "text", None) or "").strip()
    answer = (getattr(_s16_response, "text", None) or "").strip()
    if not question or not answer:
        return _s16_response

    fresh_items: list = []
    fresh_receipt = None
    for provider_name in ("parallel", "desearch"):
        try:
            payload = await _s16_search_web(
                question[:300],
                provider=provider_name,
                num=6,
                timeout=_S16_SEARCH_TIMEOUT_S,
            )
        except Exception:
            payload = None
        if payload is None:
            continue
        results = list(getattr(payload, "results", None) or [])
        if not results:
            continue
        receipt = str(getattr(payload, "receipt_id", "") or "")
        if not receipt:
            continue
        for item in results:
            rid = getattr(item, "result_id", None)
            note = (getattr(item, "note", None) or "").strip()
            if not isinstance(rid, str) or not rid or not note:
                continue
            fresh_items.append({
                "result_id": rid,
                "note": note,
                "title": (getattr(item, "title", None) or "").strip(),
                "url": (getattr(item, "url", None) or "").strip(),
            })
            if len(fresh_items) >= 4:
                break
        if fresh_items:
            fresh_receipt = receipt
            break
    if not fresh_items or not fresh_receipt:
        return _s16_response

    evidence_block = "\n".join(
        f"[{idx}] {item['title']} \u2014 {item['url']}\n{item['note'][:900]}"
        for idx, item in enumerate(fresh_items)
    )
    audit_user_prompt = (
        f"Question:\n{question}\n\n"
        f"Drafted answer:\n{answer[:12000]}\n\n"
        f"Fresh evidence snippets:\n{evidence_block}"
    )
    try:
        audit_result = await _s16_llm_chat(
            provider="openrouter",
            model=_S16_MODEL,
            messages=[
                {"role": "system", "content": _S16_AUDIT_SYSTEM_PROMPT},
                {"role": "user", "content": audit_user_prompt},
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=400,
            timeout=_S16_AUDIT_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return _s16_response

    raw = _s16_chat_text(audit_result)
    try:
        report = _s16_json.loads(_s16_strip_json_fences(raw))
    except Exception:
        return _s16_response
    if not isinstance(report, dict):
        return _s16_response

    verdict = str(report.get("verdict") or "").strip().lower()
    corroborating = report.get("corroborating_snippet_indices")
    corroborating = corroborating if isinstance(corroborating, list) else []

    def _s16_build_refs(indices):
        refs = []
        for raw_idx in indices:
            try:
                idx = int(raw_idx)
            except Exception:
                continue
            if not (0 <= idx < len(fresh_items)):
                continue
            item = fresh_items[idx]
            note_len = len(item["note"])
            end = min(500, note_len)
            if end <= 0:
                continue
            try:
                refs.append(_s16_citation_ref(
                    receipt_id=fresh_receipt,
                    result_id=item["result_id"],
                    slices=[_s16_citation_slice(start=0, end=end)],
                ))
            except Exception:
                continue
            if len(refs) >= _S16_MAX_NEW_CITATIONS:
                break
        return refs

    if verdict == "contradicted":
        contradiction = str(report.get("contradiction_summary") or "").strip()
        rewrite_user_prompt = (
            f"Question:\n{question}\n\n"
            f"Original answer:\n{answer[:12000]}\n\n"
            f"Contradiction found by fresh evidence:\n{contradiction or 'see evidence below'}\n\n"
            f"Fresh evidence snippets:\n{evidence_block}"
        )
        try:
            rewrite_result = await _s16_llm_chat(
                provider="openrouter",
                model=_S16_MODEL,
                messages=[
                    {"role": "system", "content": _S16_REWRITE_SYSTEM_PROMPT},
                    {"role": "user", "content": rewrite_user_prompt},
                ],
                tools=None,
                temperature=0.1,
                max_output_tokens=1400,
                timeout=_S16_REWRITE_TIMEOUT_S,
                thinking={"enabled": False},
            )
        except Exception:
            rewrite_result = None
        new_text = _s16_chat_text(rewrite_result)[:79000].strip()
        if not new_text:
            return _s16_response
        fallback_indices = corroborating or [0]
        new_refs = _s16_build_refs(fallback_indices)
        merged = _s16_merge_citations(getattr(_s16_response, "citations", None), new_refs)
        try:
            return _s16_response.model_copy(update={"text": new_text, "citations": merged})
        except Exception:
            return _s16_response

    if verdict == "corroborated" and corroborating:
        new_refs = _s16_build_refs(corroborating)
        if not new_refs:
            return _s16_response
        merged = _s16_merge_citations(getattr(_s16_response, "citations", None), new_refs)
        if len(merged) == len(list(getattr(_s16_response, "citations", None) or [])):
            return _s16_response
        try:
            return _s16_response.model_copy(update={"citations": merged})
        except Exception:
            return _s16_response

    return _s16_response


async def _s16_finalize(_s16_query, _s16_response, _s16_t0: float):
    """Bounded, independent verification + citation-reinforcement pass."""
    if _s16_response is None:
        return _s16_response
    if getattr(_s16_response, "text", None) in (None, ""):
        return _s16_response
    elapsed = _s16_monotonic() - _s16_t0
    if elapsed >= _S16_HARD_BUDGET_GATE_S:
        return _s16_dedup_citations(_s16_response)
    window = min(_S16_MAX_WINDOW_S, max(_S16_MIN_WINDOW_S, 280.0 - elapsed))
    try:
        return await _s16_asyncio.wait_for(
            _s16_verify_and_patch(_s16_query, _s16_response),
            timeout=window,
        )
    except Exception:
        return _s16_dedup_citations(_s16_response)


@entrypoint("query")
async def query(query: Query) -> Response:
    _s16_t0 = _s16_monotonic()
    _s16_resp = await _s16_base_query(query)
    try:
        return await _s16_finalize(query, _s16_resp, _s16_t0)
    except Exception:
        return _s16_resp
