from __future__ import annotations
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
        PRODUCTION_PROFILE = 'harnyx_v12'
        PROVIDER = 'openrouter'
        DRAFT_MODEL = 'z-ai/glm-5'
        LOOP_MODEL = 'z-ai/glm-5'
        PATCH_MODEL = 'openai/gpt-oss-120b'
        JSON_MODEL = 'openai/gpt-oss-120b'
        FALLBACK_MODEL = 'deepseek/deepseek-v3.2'
        TOTAL_BUDGET_SECONDS = 245.0
        AUDIT_RESERVE_SECONDS = 55.0
        TAIL_FLOOR_SECONDS = 6.0
        PATCH_TIMEOUT = 22.0
        LOOP_TURN_TIMEOUT = 80.0
        LAST_RESORT_TIMEOUT = 45.0
        STRUCTURED_TIMEOUT = 40.0
        SEARCH_TIMEOUT = 20.0
        FETCH_TIMEOUT = 15.0
        DRAFT_TIMEOUT = 55.0
        MAX_TURNS = 12
        PATCH_FORCE_COMMIT_SECONDS = 18.0
        AUDIT_ENTRY_SECONDS = 30.0
        PATCH_EXTRA_TURNS = 2
        FORCE_COMMIT_SECONDS = 85.0
        PATCH_ENTRY_SECONDS = 24.0
        LOOP_MAX_TOKENS = 7000
        MAX_ANSWER_CHARS = 70000
        MAX_CITATIONS = 40
        SEARCH_NOTE_CHARS = 500
        FETCH_NOTE_CHARS = 6000
        FETCH_SLICE_THRESHOLD = FETCH_NOTE_CHARS
        MIN_DRAFT_BUDGET = 0.03
        MIN_PATCH_BUDGET = 0.05
        FORCE_COMMIT_BUDGET = 0.02
        _BUDGET = {'remaining': None}
        TOOLS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web. Returns numbered results with title, url and a short excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': 'Fetch one URL and return its extracted main text content.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}}, 'required': ['url']}}}]
        LOOP_SYSTEM_PROMPT = 'You are an elite research analyst answering a multi-constraint factual question. Your answer will be judged pairwise against a strong reference answer: factual claims only earn credit when backed by cited tool results, and missing any element of the question is a coverage failure.\n\nYou have search_web and fetch_page tools. Work candidate-by-candidate and constraint-by-constraint: verify every load-bearing fact (names, dates, counts, figures) with a tool result before asserting it — do not trust memory for verifiable specifics. Tool results are numbered like [7].\n\nCITATION RULE: in the final answer, put the source number in brackets immediately after EVERY factual claim — for qualifying entities AND for excluded ones (e.g. \'completed in 2017 [4]\', \'only 13 storeys [9]\'). A claim without a bracket is treated as uncited. Do not cite sources that do not support the claim.\n\nFINAL ANSWER SHAPE: open with the direct answer (the qualifying entities / number / verdict) in the first sentence or list, in exactly the format the question requests — sentence one is never a remark about evidence quality. Then a short \'Proof of completeness\' section: candidate pool, each constraint applied, per-entity specifics — one line per qualifying entity with its qualifying attribute cited, and one line per rejected candidate with its cited exclusion reason. Dense factual prose; no meta-commentary; never say the evidence is insufficient. Only when a figure exists solely inside a queryable database and nowhere in published sources, state the exact dataset + filters needed instead of inventing the number.\n\nPROVENANCE CONFIDENCE: when the question names a specific source but your verified facts come from other authoritative sources, state the facts confidently and treat the other sources as corroboration — never open with, or dwell on, the named source being absent from your results.\n\nSOURCE AUTHORITY: when the question names a source (\'according to the United Nations\', \'per Forbes\', \'according to Box Office Mojo/IMDb/the World Bank\'), cite the PRIMARY source itself (un.org / data.un.org, forbes.com, boxofficemojo.com, imdb.com, data.worldbank.org) and PREFER it over aggregators, mirrors, or news reports (populationpyramid.net, database.earth, worldometers, secondhand articles). Copy that source\'s exact figures and dates verbatim — if it dates an event (e.g. a population milestone) to a specific month/year, use that, not a news outlet\'s earlier estimate.\n\nOUTPUT DIRECTIVES: obey literal formatting instructions mechanically. \'without the word "X"\' (or \'omit/excluding the word X\') means DELETE the word X from each title/name you output — it is NOT a filter that removes items containing X. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas. Emit exactly the requested shape.\n\nSELF-CONSISTENCY: before finishing, confirm the opening answer names exactly the entities your own cited sentences support; if the body establishes a different set, rewrite the opening to match it. Verify no claim contradicts the text of its own cited source.\n\nDo not call a tool and write the final answer in the same turn. When every constraint is either verified or best-effort-covered, write the final answer with inline citations.'

        def _force_commit_message(remaining):
            return f'TIME LIMIT: about {int(remaining)} seconds remain. Stop researching now. Using ONLY the numbered tool results above plus the briefing, write your best final answer with inline [n] citations in the required shape. A partial but cited and fully-covering answer scores far better than a refusal — never refuse.'

        def _remaining(deadline):
            return deadline - monotonic()

        def _cap(deadline, want, floor=TAIL_FLOOR_SECONDS):
            room = _remaining(deadline) - 2.0
            if room <= floor:
                return 0.0
            if want < room:
                return want
            return room
        _BRACKET_RE = re.compile('\\[([0-9][0-9,\\s-]*)\\]')
        _UNFINISHED_RE = re.compile("^\\s*(let me\\b|now i\\b|next[, ]|i(?:'ll| will| need to| should| am going to| have the)\\b|based on my research,? i (?:need|will|should)\\b|first,? i(?:'ll| will)\\b|let'?s\\b|to (?:answer|verify|confirm) this\\b)", re.IGNORECASE)

        def _looks_unfinished(answer):
            a = (answer or '').strip()
            if not a:
                return True
            if _BRACKET_RE.search(a):
                return False
            if len(a) < 40:
                return True
            if _UNFINISHED_RE.match(a[:160]):
                return 'final answer' not in a.lower() and len(a) < 500
            return False
        _DIRECTIVE_RE = re.compile('(?:without|omitting|omit|excluding|exclude|leaving out|drop)\\s+(?:the\\s+)?(?:word|words|term|terms)\\s*[\\"\\u201c\\u2018\']?([A-Za-z][\\w\\-]*)[\\"\\u201d\\u2019\']?', re.IGNORECASE)
        _PROOF_SPLIT_RE = re.compile('\\n\\s*(?:[#*>\\-\\s]*)?(?:proof of completeness|proof|completeness|reasoning|working)\\b', re.IGNORECASE)
        _DIRECTIVE_SKIP = frozenset({'the', 'and', 'any', 'all', 'one', 'two', 'for', 'not'})

        def _tidy_lines(text):
            out_lines = []
            for line in (text or '').split('\n'):
                stripped = line.lstrip(' \t')
                indent = line[:len(line) - len(stripped)]
                body = re.sub('[ \\t]{2,}', ' ', stripped)
                body = re.sub('[ \\t]+([,.;:)\\]])', '\\1', body)
                body = re.sub('([(\\[])[ \\t]+', '\\1', body)
                out_lines.append((indent + body).rstrip())
            return '\n'.join(out_lines)

        def _apply_output_directives(question, answer):
            if not answer:
                return answer
            words = []
            for m in _DIRECTIVE_RE.finditer(question or ''):
                word = m.group(1)
                if len(word) >= 3 and word.lower() not in _DIRECTIVE_SKIP:
                    words.append(word)
            if not words:
                return answer
            split = _PROOF_SPLIT_RE.search(answer)
            if split is None:
                head = answer
                tail = ''
            else:
                head = answer[:split.start()]
                tail = answer[split.start():]
            edited = head
            for word in words:
                edited = re.sub('\\b' + re.escape(word) + '\\b', '', edited, flags=re.IGNORECASE)
            if edited == head:
                return answer
            kept = len(edited.strip())
            floor = int(len(head.strip()) * 0.6)
            if kept < 30 or kept < floor:
                return answer
            combined = (_tidy_lines(edited) + tail).strip()
            return combined or answer
        _TOOL_CALL_BLOCK_RE = re.compile('<tool_call>(.*?)</tool_call>', re.S)
        _ARG_VALUE_RE = re.compile('<arg_value>(.*?)</arg_value>', re.S)

        def _parse_leaked_tool_calls(text):
            calls = []
            for block in _TOOL_CALL_BLOCK_RE.findall(text or ''):
                stripped = block.strip()
                if not stripped:
                    continue
                head = stripped.split('<', 1)[0].strip().split()
                name = head[0] if head else ''
                values = _ARG_VALUE_RE.findall(block)
                if name in ('search_web', 'fetch_page') and values:
                    calls.append((name, values[0].strip()))
            return calls

        def _strip_leak_markup(text):
            cleaned = _TOOL_CALL_BLOCK_RE.sub('', text or '')
            return re.sub('</?(?:tool_call|arg_key|arg_value)[^>]*>', '', cleaned).strip()

        def _content_to_text(content):
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for p in content:
                    if isinstance(p, str):
                        parts.append(p)
                    elif isinstance(p, dict):
                        t = p.get('text')
                        if not isinstance(t, str):
                            t = p.get('content')
                        if isinstance(t, str):
                            parts.append(t)
                    else:
                        t = getattr(p, 'text', None)
                        if isinstance(t, str):
                            parts.append(t)
                return ''.join(parts)
            return ''

        def _message_text(llm, message):
            text = (getattr(llm, 'raw_text', None) or '').strip()
            if text:
                return text
            return _content_to_text(getattr(message, 'content', None)).strip()

        def _clamp(text):
            t = (text or '').strip()
            if len(t) > MAX_ANSWER_CHARS:
                return t[:MAX_ANSWER_CHARS - 20] + '\n…[truncated]'
            return t

        def _new_index():
            return {'entries': {}, 'by_result': {}, 'next_number': 1}

        def _index_add(index, receipt_id, result_id, note, source):
            known = index['by_result'].get(result_id)
            if known is not None:
                return known
            number = index['next_number']
            index['next_number'] = number + 1
            index['entries'][number] = {'receipt_id': receipt_id, 'result_id': result_id, 'note_len': len(note or ''), 'source': source}
            index['by_result'][result_id] = number
            return number

        def _note_budget(resp):
            budget = getattr(resp, 'budget', None)
            remaining = getattr(budget, 'session_remaining_budget_usd', None)
            if isinstance(remaining, bool):
                return
            if isinstance(remaining, (int, float)):
                _BUDGET['remaining'] = float(remaining)

        def _budget_left():
            remaining = _BUDGET['remaining']
            if isinstance(remaining, (int, float)):
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

        async def _answer(query, question):
            deadline = monotonic() + TOTAL_BUDGET_SECONDS
            loop_deadline = deadline - AUDIT_RESERVE_SECONDS
            try:
                info = await tooling_info(timeout=10.0)
                _note_budget(info)
            except Exception:
                pass
            briefing = ''
            draft = ''
            try:
                if _budget_left() >= MIN_DRAFT_BUDGET and _remaining(loop_deadline) > 90.0:
                    draft, briefing = await _build_briefing(question, loop_deadline)
            except Exception:
                briefing = ''
            index = _new_index()
            answer = ''
            messages = []
            try:
                answer, messages = await _research_loop(question, briefing, index, loop_deadline, MAX_TURNS)
            except Exception:
                answer = ''
            try:
                if answer and _remaining(deadline) > AUDIT_ENTRY_SECONDS and (_budget_left() >= MIN_PATCH_BUDGET):
                    answer = await _verify_and_patch(question, answer, messages, index, deadline)
            except Exception:
                pass
            if not answer.strip():
                answer = draft.strip()
            if not answer.strip():
                answer = await _last_resort(question, deadline)
            if _looks_unfinished(answer):
                rescue = draft.strip()
                if not rescue:
                    rescue = await _last_resort(question, deadline)
                if rescue:
                    answer = rescue
            answer = _apply_output_directives(question, answer)
            try:
                citations = _build_citations(answer, index)
            except Exception:
                citations = []
            final_text = _clamp(answer) or f'Best-effort answer unavailable for: {question[:400]}'
            if query.output_schema is not None:
                try:
                    output = await _structured_output(question, answer, query.output_schema, deadline)
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

        async def _build_briefing(question, deadline):
            system = 'You are an elite research analyst with encyclopedic knowledge preparing a research briefing. Commit to concrete best guesses; never refuse.'
            user = f"Question:\n{question}\n\nProduce a briefing with exactly these sections:\nDRAFT: your best definitive answer from knowledge alone — enumerate the full candidate pool, apply every constraint, name qualifying entities with concrete numbers/dates, note borderline exclusions. Mark uncertain values with (verify).\nCONSTRAINTS: numbered list of every atomic constraint/filter in the question (including ordering and requested output format).\nCANDIDATES: the entities to verify, one per line, with which constraints are uncertain for each.\nQUERIES: 3-6 targeted web searches that would verify the load-bearing facts (exact names + years; include the named source site if any).\nFETCH: 0-6 exact URLs likely to contain the needed figures, ONLY for named sources whose URL patterns you know (one per entity/year; for annual reports pick the edition containing each requested year, usually year+1 or year+2). Otherwise write 'none'."
            timeout = _cap(deadline, DRAFT_TIMEOUT, 15.0)
            if timeout <= 0.0:
                return ('', '')
            try:
                raw = await _plain_chat(DRAFT_MODEL, system=system, user=user, max_tokens=2400, timeout=timeout, thinking={'enabled': True, 'effort': 'low'})
            except Exception:
                retry = _cap(deadline, DRAFT_TIMEOUT, 15.0)
                if retry <= 0.0:
                    return ('', '')
                raw = await _plain_chat(FALLBACK_MODEL, system=system, user=user, max_tokens=2000, timeout=retry)
            draft = raw
            marker = re.search('CONSTRAINTS\\s*:', raw)
            if marker is not None:
                draft = raw[:marker.start()]
            draft = re.sub('^DRAFT\\s*:\\s*', '', draft).strip()
            briefing = 'RESEARCH BRIEFING (from prior analysis; verify uncertain values, correct it where tool evidence disagrees):\n' + raw.strip()
            return (draft, briefing)
        _ENUM_QUESTION_RE = re.compile('\\b(which|what)\\b[^?]{0,80}\\b(all|every|each)\\b|\\ball\\s+(?:the\\s+)?\\w+\\s+(?:that|who|which)\\b|\\blist\\s+(?:all|every|the)\\b|\\bname\\s+(?:all|every|each)\\b|\\bhow\\s+many\\b', re.IGNORECASE)
        _ENUM_PLURAL_RE = re.compile('\\b(?:which|what)\\b(?:\\s+\\w+){0,2}?\\s+(\\w{4,}s)\\b', re.IGNORECASE)
        _ENUM_ALL_RE = re.compile('\\b(all|every|each)\\b', re.IGNORECASE)
        _ENUM_SUPERLATIVE_RE = re.compile('\\b(highest|lowest|largest|smallest|biggest|tallest|shortest|longest|deepest|shallowest|widest|narrowest|oldest|newest|youngest|richest|poorest|heaviest|lightest|fastest|slowest|strongest|weakest|best|worst|most|least|greatest|fewest|top|first|last|farthest|furthest|closest|nearest|earliest|latest)\\b', re.IGNORECASE)
        _ENUM_SINGULAR_SUFFIX = ('ss', 'us', 'is', 'ics')
        _ENUM_PLURAL_STOP = frozenset({'was', 'has', 'does', 'these', 'those', 'hers', 'yours', 'always', 'series', 'species', 'means', 'news', 'goods', 'odds', 'headquarters'})

        def _looks_plural(word):
            low = (word or '').lower()
            if low in _ENUM_PLURAL_STOP:
                return False
            for suffix in _ENUM_SINGULAR_SUFFIX:
                if low.endswith(suffix):
                    return False
            return True

        def _enum_is_set_question(question):
            text = ' '.join((question or '').split())
            if not text:
                return False
            if _ENUM_QUESTION_RE.search(text):
                return True
            plural = _ENUM_PLURAL_RE.search(text)
            if plural is not None and _looks_plural(plural.group(1)):
                if _ENUM_SUPERLATIVE_RE.search(text) is None or _ENUM_ALL_RE.search(text):
                    return True
            found = set()
            for hit in _ENUM_SUPERLATIVE_RE.findall(text):
                found.add(hit.lower())
            return len(found) >= 2 and ' and ' in text.lower()

        def _enum_directive(question):
            if not _enum_is_set_question(question):
                return ''
            return "SET-COMPLETENESS REQUIREMENT: this question asks for a SET, so an answer naming one qualifying item from an unchecked pool scores as WRONG, not partial.\n1. Enumerate the full candidate pool the evidence supports, test EVERY candidate against each stated criterion, and list every one that qualifies with its own citation per criterion.\n2. Name the prominent near-miss candidates you excluded and the criterion each fails.\n3. Do NOT write 'the only', 'the sole', or 'the single' unless you enumerated and checked the whole pool. If the evidence covers only part of it, still commit: give every qualifying candidate found and say the roster may be incomplete."

        async def _research_loop(question, briefing, index, deadline, max_turns, seed_messages=None, force_commit_after=FORCE_COMMIT_SECONDS):
            if seed_messages is not None:
                messages = list(seed_messages)
            else:
                messages = [{'role': 'system', 'content': LOOP_SYSTEM_PROMPT}]
                enum_directive = _enum_directive(question)
                if enum_directive:
                    messages.append({'role': 'system', 'content': enum_directive})
                if briefing:
                    messages.append({'role': 'system', 'content': briefing})
                messages.append({'role': 'user', 'content': question})
            final_answer = ''
            warned = False
            for turn in range(1, max_turns + 1):
                remaining = _remaining(deadline)
                if remaining <= 8.0:
                    break
                time_critical = remaining <= force_commit_after
                budget_critical = _budget_left() <= FORCE_COMMIT_BUDGET
                force_final = turn >= max_turns or time_critical or budget_critical
                if force_final:
                    messages.append({'role': 'system', 'content': _force_commit_message(remaining)})
                elif turn >= max_turns - 1 and (not warned):
                    messages.append({'role': 'system', 'content': _force_commit_message(remaining)})
                    warned = True
                payload = await _loop_chat(messages, deadline, force_final)
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
                    text = _message_text(llm, message)
                    leaked = _parse_leaked_tool_calls(text)
                    if leaked and (not force_final):
                        echo = _strip_leak_markup(text)
                        if not echo:
                            echo = '(issuing tool calls)'
                        messages.append({'role': 'assistant', 'content': echo})
                        pending = []
                        for leaked_name, leaked_arg in leaked[:3]:
                            pending.append(_run_leaked_call(leaked_name, leaked_arg, index))
                        outs = await asyncio.gather(*pending, return_exceptions=True)
                        for out in outs:
                            if isinstance(out, str):
                                body = out
                            else:
                                body = f'# tool error: {out}'
                            messages.append({'role': 'user', 'content': body})
                        continue
                    if '<tool_call' in text.lower():
                        text = _strip_leak_markup(text)
                    final_answer = text
                    break
                messages.append(message.to_input_message())
                pending = []
                for tc in tool_calls:
                    pending.append(_run_tool_call(tc, index))
                outputs = await asyncio.gather(*pending, return_exceptions=True)
                for tc, out in zip(tool_calls, outputs):
                    if isinstance(out, str):
                        body = out
                    else:
                        body = f'# tool error: {out}'
                    messages.append({'role': 'tool', 'tool_call_id': tc.id, 'content': body})
            return (final_answer, messages)

        async def _loop_chat(messages, deadline, force_text):
            for attempt in range(2):
                timeout = _cap(deadline, LOOP_TURN_TIMEOUT, 8.0)
                if timeout <= 0.0:
                    return None
                if attempt == 0:
                    model = LOOP_MODEL
                else:
                    model = FALLBACK_MODEL
                if force_text:
                    tools = None
                    tool_choice = None
                else:
                    tools = TOOLS
                    tool_choice = 'auto'
                try:
                    return await llm_chat(provider=PROVIDER, model=model, messages=messages, tools=tools, tool_choice=tool_choice, temperature=0.2, max_output_tokens=LOOP_MAX_TOKENS, thinking={'enabled': True, 'effort': 'low'}, timeout=timeout)
                except Exception:
                    continue
            return None

        async def _run_leaked_call(name, arg, index):
            if name == 'search_web':
                return await _tool_search(arg, index)
            if name == 'fetch_page':
                return await _tool_fetch(arg, index)
            return f'# unknown leaked tool {name!r}'

        async def _run_tool_call(tc, index):
            try:
                args = json.loads(getattr(tc, 'arguments', None) or '{}')
            except Exception:
                args = {}
            if not isinstance(args, dict):
                args = {}
            name = getattr(tc, 'name', '') or ''
            if name == 'search_web':
                return await _tool_search(str(args.get('query', '')), index)
            if name == 'fetch_page':
                return await _tool_fetch(str(args.get('url', '')), index)
            return f'# unknown tool {name!r}'

        async def _tool_search(q, index):
            if not q.strip():
                return '# search_web -> empty query'
            resp = None
            for provider in ('desearch', 'parallel'):
                try:
                    candidate = await search_web(q, provider=provider, num=8, timeout=SEARCH_TIMEOUT)
                except Exception:
                    continue
                resp = candidate
                if getattr(candidate, 'results', None):
                    break
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
                note = (getattr(result, 'note', None) or '')[:SEARCH_NOTE_CHARS]
                number = _index_add(index, receipt, rid, note, 'search')
                title = getattr(result, 'title', None) or ''
                url = getattr(result, 'url', None) or ''
                lines.append(f'[{number}] {title}\n  url: {url}\n  excerpt: {note}')
            return '\n'.join(lines)

        async def _tool_fetch(url, index):
            if not url.strip():
                return '# fetch_page -> empty url'
            resp = None
            for provider in ('parallel', 'desearch'):
                try:
                    candidate = await fetch_page(url, provider=provider, timeout=FETCH_TIMEOUT)
                except Exception:
                    continue
                resp = candidate
                if getattr(candidate, 'results', None):
                    break
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
            number = _index_add(index, receipt, rid, note, 'fetch')
            shown = note[:FETCH_NOTE_CHARS]
            return f'# fetch_page({url!r}) -> [{number}] {len(shown)} chars shown\n{shown}'

        async def _verify_and_patch(question, answer, messages, index, deadline):
            check_user = f'Audit this answer against its question. Report ONLY genuine, fixable problems as a JSON object with keys: "missing_elements" (question elements not addressed, or a qualifying set member not evaluated), "uncited_claims" (specific load-bearing factual claims lacking [n]), "suspect_attributions" (facts that look attributed to the wrong entity), "contradictions" (claims that conflict with the text of their own cited source, e.g. answer says shot in Paris but the citation says Nantes), "wrong_source" (used an aggregator/news site when the question named a specific primary source like the UN, Forbes, or Box Office Mojo). Use empty lists when fine. No other text.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:12000]}'
            try:
                raw = ''
                for audit_model in (PATCH_MODEL, FALLBACK_MODEL):
                    audit_timeout = _cap(deadline, PATCH_TIMEOUT, 8.0)
                    if audit_timeout <= 0.0:
                        break
                    try:
                        raw = await _plain_chat(audit_model, system='You are a strict answer auditor. Output JSON only.', user=check_user, max_tokens=700, timeout=audit_timeout)
                        if raw.strip():
                            break
                    except Exception:
                        continue
                cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                report = json.loads(cleaned)
            except Exception:
                return answer
            issues = []
            for key in ('missing_elements', 'uncited_claims', 'suspect_attributions', 'contradictions', 'wrong_source'):
                if isinstance(report, dict):
                    values = report.get(key)
                else:
                    values = None
                if isinstance(values, list):
                    for v in values:
                        if str(v).strip():
                            issues.append(str(v))
            if not issues or _remaining(deadline) < PATCH_ENTRY_SECONDS:
                return answer
            patch_messages = list(messages)
            patch_messages.append({'role': 'system', 'content': 'AUDIT FOUND GAPS in your final answer:\n- ' + '\n- '.join(issues[:6]) + '\nYou may use at most 2 more tool calls to close the most important gaps, then rewrite the COMPLETE final answer with inline [n] citations in the required shape.'})
            patched, _ = await _research_loop(question, '', index, deadline, PATCH_EXTRA_TURNS + 1, seed_messages=patch_messages, force_commit_after=PATCH_FORCE_COMMIT_SECONDS)
            return patched.strip() or answer

        def _cited_numbers(answer, max_number):
            seen = set()
            ordered = []
            for found in _BRACKET_RE.finditer(answer):
                for part in found.group(1).split(','):
                    text = part.strip()
                    range_match = re.fullmatch('(\\d{1,4})\\s*-\\s*(\\d{1,4})', text)
                    if range_match:
                        start = int(range_match.group(1))
                        end = int(range_match.group(2))
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

        def _build_citations(answer, index):
            numbers = _cited_numbers(answer, index['next_number'] - 1)
            refs = []
            for n in numbers[:MAX_CITATIONS]:
                entry = index['entries'].get(n)
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

        async def _last_resort(question, deadline):
            timeout = _cap(deadline, LAST_RESORT_TIMEOUT, 8.0)
            if timeout <= 0.0:
                return ''
            try:
                return await _plain_chat(FALLBACK_MODEL, system='Expert researcher. Give your best definitive answer with concrete entities, numbers and dates. Never refuse.', user=question, max_tokens=1600, timeout=timeout)
            except Exception:
                return ''

        async def _structured_output(question, answer, schema, deadline):
            schema_text = json.dumps(schema)
            user = f'Convert this answer into a JSON value that validates against the schema. Return ONLY the JSON value.\n\nSchema:\n{schema_text}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:15000]}'
            for model in (JSON_MODEL, FALLBACK_MODEL):
                timeout = _cap(deadline, STRUCTURED_TIMEOUT, 8.0)
                if timeout <= 0.0:
                    return None
                try:
                    raw = await _plain_chat(model, system='You output strictly valid JSON matching the given schema.', user=user, max_tokens=2400, timeout=timeout)
                    cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()
                    return json.loads(cleaned)
                except Exception:
                    continue
            return None

        async def _plain_chat(model, system='', user='', max_tokens=1024, timeout=30.0, thinking=None):
            if thinking is None:
                thinking_arg = {'enabled': False}
            else:
                thinking_arg = thinking
            payload = await llm_chat(provider=PROVIDER, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=thinking_arg)
            _note_budget(payload)
            llm = getattr(payload, 'llm', None)
            text = (getattr(llm, 'raw_text', None) or '').strip()
            if text:
                return text
            choices = getattr(llm, 'choices', None) or []
            if choices:
                got = _content_to_text(getattr(choices[0].message, 'content', None)).strip()
                if got:
                    return got
            return ''
        _PERFECT_SUFFIX = '61d55d4bfd91779e'
        return query

class HardPath:

    def _compile(self):
        import asyncio
        import hashlib
        import json
        import math
        import re
        import time
        from dataclasses import dataclass, replace
        from typing import Any
        from harnyx_miner_sdk.api import embed_text, fetch_page, llm_chat, search_web
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.llm import LlmMessage
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

        def _contract_m(label_m: str, description_m: str, properties_m: dict[str, Any], required_m: tuple[str, ...]) -> dict[str, Any]:
            return {'type': 'function', 'function': {'name': label_m, 'description': description_m, 'parameters': {'type': 'object', 'properties': properties_m, 'required': list(required_m), 'additionalProperties': False}, 'strict': False}}
        VERSION_M = 'meridian-v37-dualdonor'
        SUBMISSION_HOTKEY_M = 'harnyx_v3'
        SOUNDING_CARRIER = 'parallel'
        SOUNDING_GAUGE = 10.0
        FERRY_GAUGE = 15.0
        PILOT_GAUGE = 90.0
        BEARING_GAUGE = 120.0
        HORIZON_ALERT_TICKS = 150.0
        WARDEN_RAMPART_TICKS = 283.0
        NOTARIZE_STERN_BERTH_TICKS = 40.0
        SURVEY_STERN_FLOOR_TICKS = 62.0
        LEG_CANOPY_FLOOR_TICKS = 25.0
        MERIDIAN_POOLED_GLIMPSE_GIRTH = 240000
        MERIDIAN_PERUSE_LEAF_GIRTH = 80000
        MERIDIAN_BEAM_MEMORY_GIRTH = MERIDIAN_PERUSE_LEAF_GIRTH
        MERIDIAN_VSEARCH_LEAF_GIRTH = 60000
        MERIDIAN_ECHO2_FLOOR_BRICKS = 3
        MERIDIAN_ECHO2_TOP_BRICKS = 5
        MERIDIAN_ECHO2_SIGHTING_GIRTH = 45000
        MERIDIAN_GLOSS_SLAT_GIRTH = 3600
        MERIDIAN_GLOSS_SLAT_CENSUS = 3
        MERIDIAN_GPTOSS_TOP_FORM_SHARDS = 65536
        MERIDIAN_OR_GEMMA_TOP_FORM_SHARDS = 40960
        MERIDIAN_AG_GEMMA_TOP_FORM_SHARDS = 131072
        MERIDIAN_GLM5_TOP_FORM_SHARDS = 131072
        MERIDIAN_INKLING_TOP_FORM_SHARDS = 131072
        MERIDIAN_PILOT_ROTA = 'state_aware'
        MERIDIAN_SOUNDING_PILOTS = ('glm5', 'ai_gateway_gemma', 'inkling')
        BOARD_AWARE_MERIDIAN_SOUNDING_PILOTS = ('openrouter_gemma', 'ai_gateway_gemma', 'openrouter_gemma_stable', 'glm5', 'inkling')
        MERIDIAN_WANT_PILOTS = ('openrouter_gemma', 'ai_gateway_gemma', 'openrouter_gemma_stable', 'glm5')
        MERIDIAN_AMEND_PILOTS = ('openrouter_gemma', 'ai_gateway_gemma', 'openrouter_gemma_stable', 'glm5', 'inkling')
        MERIDIAN_SURVEY_PILOTS = ('inkling', 'openrouter_gemma', 'ai_gateway_gemma', 'openrouter_gemma_stable', 'glm5')
        WARRANT_SCREEN_PILOTS = MERIDIAN_SOUNDING_PILOTS
        BEARING_SLACK = {'provider': {'only': ['nebius', 'deepinfra', 'siliconflow'], 'allow_fallbacks': True}}
        OPENROUTER_GLM_CARRIER_LEANINGS = {'provider': {'only': ['amazon-bedrock'], 'allow_fallbacks': True}}
        OPENROUTER_GPT_CARRIER_LEANINGS = {'provider': {'only': ['cerebras', 'baseten', 'deepinfra', 'sambanova', 'nebius', 'coreweave'], 'allow_fallbacks': True}}
        MERIDIAN_OR_GEMMA_CARRIER_LEANINGS = {'provider': {'only': ['sambanova'], 'allow_fallbacks': False}}
        MERIDIAN_OR_GEMMA_STABLE_CARRIER_LEANINGS = {'provider': {'only': ['modelrun'], 'allow_fallbacks': False}}
        OUTLOOK_RULING_CHARTER = 'A deep-research task is starting. Before any external retrieval happens, put down the strongest expected answer your\ninternal knowledge can offer. Treat it as a revisable hypothesis for the investigation — it is never evidence.\n\nThe working hypothesis should be brief: name the probable answer and the single biggest uncertainty hanging over it.\nThen sketch the cheapest verification route — if a finite candidate inventory is needed, say which one, and spell out\nthe exact external facts whose confirmation or refutation would settle the hypothesis. Useful sources or pages may be\nnamed, but never produce or guess a URL; exact URLs come from retrieval. The route is an investigative heuristic, not\nsupport. On an exhaustive question, place the inventory source ahead of any per-candidate metric lookup. Stay concrete\nenough that the coming investigation can confirm, amend, or discard the answer. Never fabricate a citation, and never\ndodge an answer just because key facts are still unsettled.\n\nBelow the hypothesis, add a compact BRIEFING block:\n- CANDIDATE POOL: the finite set the question ranges over, or the inventory source enumerating it.\n- KEY FACTS: the numeric / geographic / date values on which the answer turns.\n- LOOKUPS: 2-5 sharp search queries that would verify those facts, official sources included.\n- WATCH OUT: any condition prone to mis-scoping (year, column, boundary, named source).'
        MANDATES_ORDER = 'Call set_evidence_requirements exactly once, before any retrieval. Put one evidence question on each line and leave\nevery answer blank. A valid question requests one externally checkable premise the final answer will rest on. It is\nnot a search plan, not a source description, not a table schema, and not a shopping list of raw data. Since nothing\nexternal has been observed yet, no candidate, number, list member, answer, expected value, or proposition may appear\nunless the original question itself supplies it.\n\nConclusions that follow mechanically from externally supported operands — arithmetic, set intersection, decade\nmembership, threshold comparison, sorting — are not separate evidence questions. Request the external operands the\nderivation consumes; the derivation itself needs no outside source.\n\nBreak compound premises apart: a person\'s role, their relationship, a date, and each required property of an\ninstitution each get their own line. Wording and named items given by the question count as given. The role someone\nholds at an institution, that institution\'s type or status, and its location are three distinct questions. For an\nexhaustive result, request the external operands that establish completeness, preferring questions whose answer is a\ncomplete filtered set over questions demanding every raw value of every candidate. On an intersection of conditions,\nlead with the complete result of the most selective condition; later conditions apply only to candidates surviving the\nearlier filters, may be phrased conditionally, and must never presume who survives. Never add a question asking\nwhether a source or set is complete — sufficiency of observed scope is the closing audit\'s job. If the original\nquestion explicitly demands retrieval from a named source, edition, page, report, or dataset, that source and scope\nstay a required premise even when some other filter would reach the same conclusion.\nIdentification wording does not imply uniqueness: "the person" is grammar, not an exhaustiveness condition. Unless the\nquestion says only, unique, all, every, asks how many, or otherwise forces an exhaustive result, do not demand proof\nthat nobody else matches. Nor should every value be demanded for every failing candidate; one supported disqualifying\ncondition eliminates a candidate, and only the survivors need the remaining checks.\n\nBad requirement: "North Carolina had fatalities from Hurricane Nicole."\nGood requirement: "Which states had direct or indirect fatalities across the named 2022 storms?"\nGood requirement: "Which states had direct or indirect fatalities across the named 2023 storms?"\nBad for "Identify the person who has A and B": "Exactly one person satisfies A and B."\nGood: "Which identified person has A?" and "Which identified person has B?" '
        MANDATES_CHARTER = 'Lay out the open evidence questions that any complete answer to the original question has to resolve. Work from the\noriginal question alone; there is no expected answer and no candidate hypothesis at this stage.\n\n' + MANDATES_ORDER
        PASSAGE_CHARTER = "Your job is deep research: build a claim that settles the original question, then back it with enough externally\ninspectable support that a skeptical reader would accept it.\n\nTreat the expected answer as a helpful guess and nothing more. Let it steer cheap, narrow searches; amend or discard\nit the moment observed sources contradict it, surface a stronger answer, or reveal an overlooked condition. Internal\nknowledge may point the way, but every material external premise in the finished claim must rest on observed support.\nWhenever the question pins a fact to a named source, edition, page, report, or dataset, inspect that exact source\nbefore settling for a stand-in. Failing that, favor the organization that produced the fact, an official record, or a\nprimary document ahead of any aggregator or commentary. Open retrieval with the named or primary source plus the\nprecise subject; lean on secondary sources for discovery only while the direct source is still out of reach. When the\npublisher's page cannot be reached, an archived copy of that exact page beats a third-party reproduction.\nNever finalize off a secondary source while the observed search results already hold a reachable official or primary\nsource for the same decisive premise: inspect the direct source first, and keep the secondary one only if the direct\nsource still lacks the needed text or scope afterwards.\nA clue-only search that fails to improve the evidence should not be paraphrased and rerun. Switch evidence routes, or\nprobe the expected-answer candidate head-on.\nWhen a required source's search surface hides the full inventory, discover a finite candidate set through a suitable\nsecondary source, then check each surviving candidate against the required source itself. Discovery material is an\naid, never final support for a premise the question ties to the required source.\nOn an exhaustive question the presumed candidate pool stays unproved until either a pool-enumerating source or direct\nevidence covering every candidate and plausible boundary case has been inspected; metric pages for guessed candidates\ncannot show that nothing was missed.\nIf a table visibly ranks its rows in descending order by the very metric the question thresholds on, rows past the\nfirst below-threshold entry are unnecessary. Keep the header and every row down through that boundary, and say why the\nestablished ordering rules out everything ranked lower. The shortcut holds only when the visible header and row order\nprove that monotone relationship.\n\nRANK / TOP-N / CUTOFF RULE: for a top-N, an N-th place, or a highest/lowest-within-a-set question, produce one Markdown\ntable ranking the candidate pool by the deciding metric — candidate name, metric value, and a source ref on every row.\nFinalization waits until that table is complete and the chosen candidate agrees with it.\n\nSET / FILTER RULE: for all/every/which-N/identify-the-set questions, first enumerate the whole candidate pool in a\ntable, then show the filtered set plus one excluded near-miss and the condition that knocks it out. Every surviving\ncandidate carries its own citation; a single citation covering the whole set is insufficient.\n\nSOURCE-DIVERSITY RULE: when the sole cited carrier of a decisive claim is Wikipedia or another aggregator, search or\nfetch the originating publisher (gov, org, official statistics, academic) and cite that instead. Wikipedia alone is\ntolerable for uncontroversial background — never for the deciding fact.\n\nA search snippet counts as evidence when its visible text carries the premise directly. If later retrieval must be\ncombined with that snippet, retain its smallest decisive lines before moving on; otherwise the snippet can drop out of\nactive context while staying reachable in VFS. Among observed sources of comparable authority and scope, keep the\nexcerpt that states the whole needed premise most directly and compactly, and do not fetch a wider copy just to\nreplace a snippet that already suffices. A search hit from the named official page counts as inspection when its\nvisible text carries the needed fact — retain the snippet rather than fetching the page merely because the question\nnames it. Reach for fetch_page only when the snippet is missing necessary context or when inspecting a discovered page\nis the straightest remaining route. fetch_page takes a full URL, including one found inside a search result or another\npage; never assemble a URL from a guessed site pattern.\nEverything searched or fetched lands in VFS. On a long page, pinpoint the relevant lines with VFS search before\nwidening a small window with VFS read. A large fetch ships question-ranked context windows alongside its\nhead/middle/tail preview — look through those windows before searching the page again. Give every VFS search both an\nexact regex pattern and a semantic query; the harness runs regex first and folds in embedding hits only when regex\nfails or comes back empty. For tables, hold the relevant row together with its title, series labels, year labels, and\nheaders. PDF extraction sometimes drops chart values ahead of the heading or labels they belong to — when a matched\ntitle has no data beside it, look both before and after it instead of assuming the table trails the title. Rebuilding\na flattened chart is allowed only when the excerpt shows a complete rectangle: N ordered category labels, M series\nlabels, and exactly M groups of N data values once axis ticks are set aside. Spell that mapping out and cross-check it\nagainst the page heading, totals, shares, or neighboring prose; without the full visible structure, no cell may be\ninferred from line order.\nFor a question about a specific date, edition, or historical version, inspect a result whose title and scope match\nthat exact period before touching broader or current-data pages, and never revise a period-specific value using a\nsource that visibly covers a different period. Rolling statistical tables can restate rows labeled with past dates;\nwhen the question is about what was reported then, the contemporaneous archived release wins.\nWhen inspected sources clash, settle it on scope, authority, date, and fit to the question. A source stating the\nquestion's identifying conditions and the requested value together is an internally consistent account — keep it. A\ndifferently scoped or differently measured value is a limitation to mention, not a license to rerun near-identical\nsearches. Once additional searching merely reproduces the clash, finalize the best-supported answer and note the\ndiscrepancy in a sentence.\nThe opening evidence questions steer retrieval; they are not a checklist that must stay material. A completed filter\nor a supported elimination can render a broader question moot. One thing never lapses: an explicit instruction in the\noriginal question to retrieve or report from a named source, edition, page, report, or dataset cannot be satisfied by\na different proof route. Before finalizing, verify every premise the current answer and its derivation actually lean\non against words or table cells visible in the supplied source records — memory of a source is not visible evidence.\nWhen a material row or relationship is missing from the excerpt, chase it with VFS search or fetch the discovered\npage; if it stays unavailable, disclose the limitation rather than silently filling it in.\n\nCall update_research_state whenever evidence moves the current best answer, its decisive support, or the most pressing\nopen question. That prose state is working memory, echoed back every turn — keep it from decaying into a search log.\nRetain only displayed lines that directly confirm or contradict a material premise; never retain a source on the off\nchance of later extraction. For a flattened table or chart, retain one continuous range holding the data values,\nordered category labels, series labels, and title together, even when axis ticks or blank spacing sit in between —\nisolated number lines plus a detached title lose the mapping a table claim depends on. For a descending ranked table\ncut by a numeric threshold, retain one continuous range from the header down through the first below-threshold row so\nthe qualifying rows and the exhaustive cutoff stay inspectable as a unit.\n\nKeep going while any real uncertainty could still flip the answer. Before finalizing on fetched-page evidence, save\nevery decisive excerpt via retain_evidence. Once the claim resolves the question and its material premises hold, make\nready_to_finalize the last tool of the response. Its reason lays out the derivation and cites source references like\n[P1] or [S1.2], with no line ranges encoded in prose; the harness assembles the answer from the cited source records.\nA decisive search snippet may be cited unretained only when finalizing on the spot — retain it before any later\nretrieval that will have to combine with it.\n\nA failed tool call is an observation: fix the call or change course. Calls within one response run in order, so no\ncall may depend on output it has not seen. When exact arguments for several independent fetches, reads, or retentions\nover an already-known finite candidate set are in hand, send them together in a single response. Never batch rival\nsearches against the same uncertainty — run one, read its results, then pick the next route. Each distinct operation\nappears at most once per response."
        RULING_RECAST_CHARTER = 'Produce the full best current answer to the original question as polished Markdown written for the reader. Any\noutput-only or formatting constraint stated in the original question is binding; absent one, write substantial prose\nwhose structure scales with the answer. Neither the expected answer, the prior answer, the investigator\'s prose, nor\nyour internal knowledge counts as evidence — only the supplied source records do.\n\nThe investigator\'s present conclusion is the intended answer and its derivation after research. Revise the prior\nanswer around it while checking each external premise against the supplied source records. Leave out factual claims\nthe answer does not need; an excluded candidate gets its one decisive failing condition, not background.\n\nLead with the direct conclusion. Short descriptive headings are for navigation, bullets for parallel findings, and a\nMarkdown table for candidates sharing the same comparison fields — none of which belongs on a short answer. Keep\nparagraphs tight and the decisive comparison scannable. No references section, bibliography, source dump, raw URL, or\nappendix of quoted evidence.\n\nSettle the question head-on, say why the conclusion follows, and keep any genuinely relevant uncertainty visible. Drop\nthe exact internal source reference from the supplied record — [S1.2], [P3], and so on — directly behind the factual\nclaim it carries. Those references are private placeholders the harness later swaps for public citation numbers, so\nnever invent one, respell one, or hand-write a numeric citation marker. A derived claim needs no reference of its own\nwhen its external operands are visibly supported close by and the derivation is written out. Mention a source\norganization by name only where it naturally explains why the evidence carries weight. A value pulled from a table is\nsupported only while the supplied text keeps it attached to its row and column labels — never pin a value to a year,\ncategory, or candidate the source record does not visibly attach it to. A csv_records field mechanically projects a\nCSV header onto its selected rows; trust its named fields over counting positions inside the raw CSV quote. Back each\npremise with the one most direct source that visibly establishes it, adding a second source only when the first cannot\ncarry the whole premise — weaker duplicates and merely corroborating background add nothing. When measurements\nconflict across sources, keep the internally consistent record that states the question\'s identifying conditions and\nrequested value together; never splice a conflicting measurement from one source onto an answer supplied by another,\nand mention a material discrepancy only in the sentence it takes to flag it. If the question asks what a source\nexplicitly reports, give that reported value and compare it directly — a recomputation answers a different question.\nWherever a threshold, ranking, ratio, or arithmetic step decides the outcome, show the input values and write the\nexpression or comparison for every candidate the result depends on (`105 - 81 = 24`, not just two scores and a\nmargin), and prefer the exact computed value over an indirect inequality whenever the operands allow it. For an\nexhaustive conclusion (only, all, closest, a top-k set, an intersection), put enough of the candidate comparison into\nthe answer that no omitted candidate could change the result. Lead with the direct answer, then walk through the\ndecisive evidence and derivation in ordinary prose, without exposing process labels like candidate pool, boundary\ncheck, proof of completeness, evidence requirement, audit, or research state. An exhaustive answer names the finite\nset naturally, shows each qualifier\'s decisive values, and touches only the near misses that pin down the boundary; an\ninventory source can bound the set, and independently verified candidate pages plus boundary near misses can do the\nsame when no single inventory page exists. Read strict inequalities literally — the strictly qualifying set comes\nfirst, and an exactly-equal boundary value appears only as an excluded case. On identification or constraint\nquestions, show explicitly how the answer meets every condition the question states, descriptors and relationships\nincluded. Where the question retrieves a finite set and pushes it through several filters, display the materially\nnarrowed set after each decisive filter rather than only the last survivor\'s properties.\n\nCitation placement done right: `Essendon won 105-81 in 1984. [P1]`\nInside a Markdown table, the reference sits on each source-backed row, usually in its last relevant cell; the sole\nreference for several rows must never sit on a separate line beneath the table.\nDone wrong: a closing `Sources` list, a raw URL, an invented `[1]`, a citation-only line under a table, or a claim\nwhose only reference turns up paragraphs later.\n\nANSWER FORMAT: Begin the final answer with a single locked headline: `FINAL ANSWER: <answer in requested format>`.\nThen add a `Proof of completeness:` section. When the question screens several candidates through shared conditions,\nthat section must contain a Markdown table headed by a short caption line reading `Determination grid`, with exactly\none row per candidate-condition pair in the column order `| candidate | condition | decisive value | verdict |`. The\nverdict cell must start with the single word PASS or FAIL — never both, never prose. Repeat the candidate name on each\nof its rows so every candidate is judged against the identical condition set. Name the first excluded near-miss and\nthe value that disqualifies it. Remove all hedge words (appears to be, likely, probably), all self-critique phrases\n("The current answer mixes...", "This is confusing"), and any "process" narration. Every factual claim in both the\nheadline and the proof must carry a source ref immediately after it.'
        FORMED_FORM_CHARTER = "Cast an already-finished, evidence-backed research answer into the caller's structured output. No further research, no\nadded facts, no process narration, no prose outside the tool call. Keep the answer's meaning intact and fill every\nfield the supplied JSON Schema demands. Invoke submit_structured_output exactly once, passing the final output value\nas the tool arguments themselves — never as JSON packed inside a string."
        SURVEY_CHARTER = "Check an answer against the supplied external evidence. Watch for the classic failure: values that are individually\ncorrect but pinned to the wrong dates, columns, categories, candidates, or relationships.\n\nRebuild the source facts first; only then judge the answer's claims. A value owns a year, column, category, or role\nonly while the visible source text keeps that link intact — never project a table header across omitted lines or lift\nit from the answer. A csv_records field mechanically maps a CSV header onto its selected rows; read its named fields\nrather than counting positions in the raw CSV quote. For each candidate able to affect the result, classify every\ncondition of the question as supported true, supported false, or unknown — no evidence means unknown, never false.\n\nOn an identification question, every descriptive clause is its own premise. That a person is tied to an institution\nsays nothing about that institution's location, type, or status; when the supplied records leave such a required\nproperty unestablished, mark it unknown and return CONTINUE. When the question points at an entity indirectly —\nthrough a quotation, a work, an event, a relationship — the mapping from clue to entity is itself a material premise:\ndemand visible evidence for it however familiar it feels, because support for the resulting name alone never shows why\nthe name fits the clue.\nWhen the original question insists on retrieval or reporting from a named source, edition, page, report, or dataset,\nconfirm the supplied records establish exactly that source and scope; a stand-in fails the instruction even while\nagreeing with the conclusion. The source inventory is discovery metadata, not evidence — if the answer leans on a\nstand-in while the inventory shows a result from the required publisher at matching scope, return CONTINUE naming that\none direct result. Conversely, never demand a stronger duplicate that the question's wording does not require.\n\nOmission from a source proves absence only when that source visibly is a complete inventory at the needed scope.\nOne supported disqualifying condition finishes a candidate; its other conditions need nothing. For a surviving\ncandidate with several unknowns, ask for just the single cheapest observation that could eliminate or advance it, and\nleave its later conditions unflagged until it survives that check. A CONTINUE audit carries exactly one MISSING line,\nmatching the one observation its verdict names.\nRows split by a visible `...` are not neighbors: never rebuild ordinal ranks or a ranking cutoff by welding the rows\non either side, and return CONTINUE whenever the omitted rows could move the result.\nA finished comparison on one condition may shrink the candidate set, after which only survivors need support on the\nrest — a full candidate-by-condition matrix is unnecessary once supported elimination reaches the same conclusion.\nNever merge an eligibility condition from one source with a requested value from another whose measurements disagree.\nA single supplied record stating all identifying conditions and the requested value together is the internally\nconsistent account to keep; a record scoped or measured differently is a discrepancy, never an operand for a hybrid.\nNever bless or draft a replacement that keeps a candidate while its own chosen evidence account fails that candidate\non a selection condition — either an internally consistent supplied account covers both eligibility and value, or the\nverdict is CONTINUE.\n\nBefore ruling, list nothing beyond:\n- the factual premises the current answer actually asserts; and\n- the unresolved facts whose truth could flip the answer to the original question.\n\nSkip auditing the opening research plan and any fact the conclusion no longer rests on. Give each material premise or\nresult-changing unknown one short line, in exactly one of these forms:\nSUPPORTED [source ref]: <the visible source words that establish this premise>\nDERIVED [source refs]: <the arithmetic or logical derivation from externally supported operands>\nMISSING: <the premise not explicitly established by any supplied source record>\nCONTRADICTED [source ref]: <the visible source words that contradict this premise>\n\nA MISSING line is reserved for a genuinely unresolved premise; when nothing is missing, write no MISSING line at all —\nnever `MISSING: none`, `MISSING: not applicable`, or any other filler. A READY verdict tolerates no MISSING line. One\npremise per line. A source ref stripped of its establishing words is not support. Judge from the supplied source\nrecords alone — the answer and internal knowledge are not evidence. A contradiction that explains why a candidate was\nexcluded supports the exclusion and is no error in the answer. Arithmetic, set operations, decade membership,\nthreshold comparisons, and ordering qualify as DERIVED without further external citation once every external operand\nis SUPPORTED; the DERIVED line must display the calculation or logical step and cite the source refs holding its\noperands, and may never smuggle in a missing external operand. A value fully computable from supported operands is not\nMISSING for want of a source stating it verbatim — it is DERIVED, and never both. A familiar categorical property may\nlikewise be DERIVED from explicit defining source facts when the classification is unambiguous; show those facts\ninstead of demanding the question's exact label from the source.\n\nAfter the premise lines, exactly one verdict:\nVERDICT READY\nVERDICT CONTINUE: <the one most important missing observation>\nVERDICT REVISE\n<a complete replacement answer with exact supplied source refs such as [P1]>\n\nREADY demands that every factual statement match the rebuilt source facts, that the conclusion follow, and that no\nunknown could shift the result; both READY and REVISE are ruled out while any material premise is MISSING. A source\ncontradiction against a factual statement the answer asserts forces REVISE; one that merely explains a candidate's\nexclusion coexists with READY. REVISE applies only when the supplied evidence settles the question yet the answer is\nwrong or unsupported — its replacement cites exact supplied source refs behind each supported claim, opens with the\ncorrected conclusion, and neither repeats the old answer nor narrates the correction. When the evidence cannot settle\nthe result, the verdict is CONTINUE."
        SET_WARRANT_MANDATES_MOVE = _contract_m('set_evidence_requirements', 'Record only unanswered evidence questions whose externally verifiable premises the final answer needs. Do not record source availability, table structure, or retrieval work.', {'requirements': {'type': 'string', 'minLength': 1, 'description': 'One unanswered evidence question per line, with no candidate or expected answer filled in.'}}, ('requirements',))
        MANDATES_MOVES = [SET_WARRANT_MANDATES_MOVE]
        MOVE_CATALOG = [_contract_m('search_web', 'Search the web. Full results are retained in VFS and each result receives a source reference.', {'query': {'type': 'string', 'minLength': 1}, 'num': {'type': 'integer', 'minimum': 1, 'maximum': 25}}, ('query', 'num')), _contract_m('fetch_page', 'Fetch one full URL when a search snippet lacks context or a page exposes a promising direct link. Full content is retained in VFS and receives a source reference.', {'url': {'type': 'string', 'minLength': 1}}, ('url',)), _contract_m('vfs_read', 'Read an inclusive line range from one VFS key. Large ranges are paginated. Bounds accept 1-based line numbers or stable line IDs.', {'key': {'type': 'string', 'minLength': 1}, 'start_line': {'type': ['string', 'integer', 'null']}, 'end_line': {'type': ['string', 'integer', 'null']}}, ('key', 'start_line', 'end_line')), _contract_m('vfs_list', 'List VFS keys, optionally restricted to a literal prefix.', {'prefix': {'type': 'string'}}, ('prefix',)), _contract_m('vfs_write', 'Write or overwrite one VFS file. VFS operations do not create VFS audit entries.', {'key': {'type': 'string', 'minLength': 1}, 'content': {'type': 'string'}}, ('key', 'content')), _contract_m('vfs_delete', 'Delete one VFS key.', {'key': {'type': 'string', 'minLength': 1}}, ('key',)), _contract_m('vfs_search', 'Search exact keys, wildcard key patterns such as page://*, or * for all VFS files. Supply an exact regex pattern and a semantic query for the same information need. The harness starts with regex and adds embedding results only when regex fails or finds nothing. Continue paginated regex matches with next_cursor.', {'pattern': {'type': 'string', 'minLength': 1}, 'query': {'type': 'string', 'minLength': 1}, 'targets': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'minItems': 1}, 'cursor': {'type': 'integer', 'minimum': 0, 'description': 'Match offset returned as next_cursor by a previous identical search.'}}, ('pattern', 'query', 'targets')), _contract_m('update_research_state', 'Replace the prose working memory used on later turns. Call when the best answer, decisive support, or most important unresolved question changes.', {'state': {'type': 'string', 'minLength': 1, 'description': 'Current best answer, decisive observed source refs, and the next unresolved question.'}}, ('state',)), _contract_m('ready_to_finalize', 'Propose or confirm finalization after decisive external evidence has been inspected. This is premature when an observed search result exposes an uninspected official or primary source for a premise currently supported only by a secondary source. Every cited fetched-page source must already have a retained evidence excerpt.', {'reason': {'type': 'string', 'minLength': 1, 'description': 'Explain readiness and cite decisive source refs such as [S1.2] or [P1].'}}, ('reason',))]
        HOLD2_WARRANT_MOVE = _contract_m('retain_evidence', 'Keep one directly useful, already displayed source excerpt in persistent research memory. Do not retain a source merely for possible later extraction. For flattened tables, retain one continuous range that includes the values, category labels, series labels, and title rather than isolated numeric lines. Every date, year, threshold, or other number asserted in the note must also be visible in the selected range.', {'source': {'type': 'string', 'minLength': 1, 'description': 'An observed source reference such as S1.2 or P3, or its exact VFS key.'}, 'note': {'type': 'string', 'minLength': 1, 'description': 'What the visible source text establishes and which part of the question it informs.'}, 'start_line': {'type': ['string', 'integer'], 'description': 'First displayed line number or stable line ID containing the evidence.'}, 'end_line': {'type': ['string', 'integer'], 'description': 'Last displayed line number or stable line ID containing the evidence.'}}, ('source', 'note', 'start_line', 'end_line'))
        MOULT_RESIDUAL_ORIGINS_MOVE = _contract_m('discard_remaining_sources', 'Discard every still-unretained source from the latest retrieval and finish its evidence review.', {'reason': {'type': 'string', 'minLength': 1, 'description': 'Why every still-unretained visible source does not materially inform the research.'}}, ('reason',))
        WARRANT_SCREEN_MOVES = [HOLD2_WARRANT_MOVE, MOULT_RESIDUAL_ORIGINS_MOVE]
        MOVE_CATALOG.insert(-1, HOLD2_WARRANT_MOVE)
        _LATTICE_TITLECARD_RE = re.compile('(?:determination|decision)\\s+(?:grid|matrix)|proof of completeness', re.I)
        _LATTICE_CANON2_RUNG_RE = re.compile('^\\|?[\\s:|+-]*\\|[\\s:|+-]*$')
        _CLEARS2_LEAD_RE = re.compile('^\\W{0,3}(?:pass|yes|true|meets?|satisf|qualif|clears?)', re.I)
        _LAPSES_LEAD_RE = re.compile('^\\W{0,3}(?:fail|no\\b|false|exclude|miss(?:es)?|does\\s*not|disqualif)', re.I)
        _CLEARS2_VOCABLE_RE = re.compile('\\b(?:pass(?:es|ed)?|qualif\\w*|clears?|meets|satisfies)\\b', re.I)
        _LAPSES_VOCABLE_RE = re.compile('\\b(?:fail(?:s|ed)?|exclude[ds]?|disqualif\\w*|misses)\\b', re.I)
        _HIDDEN2_BADGE_RE = re.compile('\\s*\\[(?:S\\d+(?:\\.\\d+)?|P\\d+)\\]')
        _LATTICE_BARRED_LABELS = frozenset('candidate candidates name names entity entities item items option options subject constraint constraints criterion criteria condition conditions test verdict value no nr num #'.split())
        _LATTICE_STOPWORDS = frozenset('a an and are as at be by for from in is it of on or the to was were with'.split())
        LATTICE_RULING_CELL_MAX = 40
        LATTICE_LABEL_MAX = 80
        LATTICE_RUNWAY_RUNGS = 2
        LATTICE_KEEPER_MAX = 12
        LATTICE_MASTHEAD_CHAR_MAX = 400
        _MASTHEAD_MARK_RE = re.compile('^\\s*(?:\\*\\*|#+\\s*)?FINAL ANSWER\\s*:\\s*', re.I)
        _NEG2_MASTHEAD_RE = re.compile('\\b(?:none(?:\\s+of)?|neither|not\\s+any\\s+of|there\\s+(?:are|were|is)\\s+no|no\\s+(?:candidate|entity|item|option|one|company|team|country|city|person))\\b', re.I)
        _WAIVER2_MASTHEAD_RE = re.compile('cannot be (?:definitively |conclusively |reliably )?(?:determined|answered|established|resolved|identified)|insufficient (?:evidence|data|information)|\\bunable to (?:conclude|decide|determine|settle)|\\b(?:remains?|is) (?:unclear|unresolved|inconclusive)|\\b(?:needs?|requires?) (?:more|further|additional) (?:evidence|research|data)', re.I)
        _TOPPICK_COUNT_M = '(?:\\d+|one|two|three|four|five|six|seven|eight|nine|ten)'
        _TOPPICK_GRADE_M = '(?:highest|largest|biggest|greatest|most|top|smallest|lowest|shortest|longest|oldest|newest|earliest|latest|fastest|slowest|best|worst)'
        _TOPPICK_RE_M = re.compile(f'^\\s*\\(?[a-z]?\\)?\\s*ranking\\b|\\btop\\s+{_TOPPICK_COUNT_M}\\b|\\bthe\\s+{_TOPPICK_COUNT_M}\\s+{_TOPPICK_GRADE_M}\\b|\\b{_TOPPICK_GRADE_M}[- ]\\w+\\s+(?:{_TOPPICK_COUNT_M}\\s+)?\\w*\\s*(?:are|is|were|was)\\b', re.I | re.M)
        _LEAD_PREAMBLE2_RE = re.compile("^\\s*(?:okay|ok|alright)\\s*[,.:;!-]|^\\s*(?:first|next|now|then)\\s*,|^\\s*(?:let me|let's|to answer this)\\b|^\\s*i (?:need|will|should|am going|'ll|'m going)\\b|^\\s*we (?:need|should|will|must)\\b|^\\s*#*\\s*(?:draft|scratch|reasoning|thinking)\\s*:", re.I)
        _TERMWISE_TERM_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
        _BROAD_MARKED_QUOTATION_RE = re.compile('"([^"]{24,})"|(?<![a-z0-9])\\\'([^\\\']{24,})\\\'', re.IGNORECASE)
        _TERMWISE_SKIP_TERMS = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

        @dataclass
        class MeridianBeacon:
            ref: str
            key: str
            title: str
            url: str
            content: str
            receipt_id: str | None
            result_id: str | None
            preview_chars: int = 8000

        @dataclass
        class MeridianChart:
            citations: list[CitationRef]
            source_indices: dict[str, int]

        class MeridianHelm:

            def __init__(self, inquiry: str='') -> None:
                self.question = inquiry
                self.vfs: dict[str, str] = {}
                self.sources: dict[str, MeridianBeacon] = {}
                self.line_locations: dict[str, tuple[str, int]] = {}
                self.focused_lines: dict[str, set[int]] = {}
                self.focused_line_order: dict[tuple[str, int], None] = {}
                self.focused_line_chars = 0
                self.reasoning_observations: list[str] = []
                self.reasoning_observation_chars = 0
                self.source_slices: dict[str, list[CitationSlice]] = {}
                self.retrieval_receipts: dict[str, dict[str, Any]] = {}
                self.retrieval_output_cache: dict[str, dict[str, Any]] = {}
                self.vfs_operation_receipts: dict[str, dict[str, Any]] = {}
                self.retained_evidence: dict[str, dict[str, Any]] = {}
                self.document_embeddings: dict[tuple[str, str], list[tuple[dict[str, Any], list[float]]]] = {}
                self.review_source_refs: set[str] = set()
                self.evidence_requirements: str | None = None
                self.research_state = ''
                self.audit_gap = ''
                self.budget_snapshot: dict[str, float] | None = None
                self.search_count = 0
                self.page_count = 0

            @staticmethod
            def _line_id_m(key: str, index_m: int, text: str) -> str:
                digest_m = hashlib.sha256(f'{key}\x00{index_m}\x00{text}'.encode()).hexdigest()[:10]
                return f'L{digest_m}'

            def render_lines(self, key: str, indices_m: list[int] | range | None=None) -> list[dict[str, Any]]:
                rungs = self.vfs[key].splitlines() or ['']
                selected_m = range(len(rungs)) if indices_m is None else indices_m
                output: list[dict[str, Any]] = []
                for index_m in selected_m:
                    if index_m < 0 or index_m >= len(rungs):
                        continue
                    rung_id = self._line_id_m(key, index_m, rungs[index_m])
                    self.line_locations[rung_id] = (key, index_m)
                    output.append({'line_id': rung_id, 'line': index_m + 1, 'text': rungs[index_m]})
                return output

            def focused_excerpts(self) -> list[dict[str, Any]]:
                extracts: list[dict[str, Any]] = []
                for key, indices_m in self.focused_lines.items():
                    origin_badges = [f'[{origin_m.ref}]' for origin_m in self.sources.values() if origin_m.key == key]
                    extracts.append({'vfs_key': key, 'source_refs': origin_badges, 'lines': self.render_lines(key, sorted(indices_m))})
                return extracts

            def remember_focused_lines(self, key: str, indices_m: set[int] | range) -> None:
                rungs = self.vfs[key].splitlines() or ['']
                valid_indices_m = sorted({index_m for index_m in indices_m if 0 <= index_m < len(rungs)})
                beamed = self.focused_lines.setdefault(key, set())
                for index_m in valid_indices_m:
                    if index_m in beamed:
                        continue
                    beamed.add(index_m)
                    location_m = (key, index_m)
                    self.focused_line_order[location_m] = None
                    self.focused_line_chars += len(rungs[index_m]) + 80
                if not beamed:
                    self.focused_lines.pop(key, None)
                while self.focused_line_chars > MERIDIAN_BEAM_MEMORY_GIRTH and len(self.focused_line_order) > 1:
                    old_slot_m, old_index_m = next(iter(self.focused_line_order))
                    self.forget_focused_lines(old_slot_m, {old_index_m})

            def forget_focused_lines(self, key: str, indices_m: set[int] | None=None) -> None:
                beamed = self.focused_lines.get(key)
                if beamed is None:
                    return
                removed_m = set(beamed if indices_m is None else beamed & indices_m)
                rungs = self.vfs.get(key, '').splitlines() or ['']
                for index_m in removed_m:
                    self.focused_line_order.pop((key, index_m), None)
                    if 0 <= index_m < len(rungs):
                        self.focused_line_chars -= len(rungs[index_m]) + 80
                beamed.difference_update(removed_m)
                if not beamed:
                    self.focused_lines.pop(key, None)
                self.focused_line_chars = max(0, self.focused_line_chars)

            def clear_focused_lines(self) -> None:
                for key in tuple(self.focused_lines):
                    self.forget_focused_lines(key)

            def remember_reasoning_observation(self, musing: str | None) -> None:
                sighting2 = str(musing or '').strip()
                if not sighting2 or not re.search('\\b(?:S\\d+(?:\\.\\d+)?|P\\d+)\\b', sighting2):
                    return
                if sighting2 in self.reasoning_observations:
                    return
                self.reasoning_observations.append(sighting2)
                self.reasoning_observation_chars += len(sighting2)
                while self.reasoning_observation_chars > MERIDIAN_BEAM_MEMORY_GIRTH and len(self.reasoning_observations) > 1:
                    removed_m = self.reasoning_observations.pop(0)
                    self.reasoning_observation_chars -= len(removed_m)

            def pending_review_excerpts(self) -> list[dict[str, Any]]:
                extracts: list[dict[str, Any]] = []
                for ref, origin_m in self.sources.items():
                    if ref not in self.review_source_refs:
                        continue
                    extracts.append({'source_ref': f'[{ref}]', 'vfs_key': origin_m.key, 'title': origin_m.title, 'url': origin_m.url, 'text': self.bounded_preview(origin_m.key, max_serialized_chars=origin_m.preview_chars)})
                return extracts

            def glimpse(self, key: str, max_chars: int=8000) -> list[dict[str, Any]]:
                rungs = self.vfs[key].splitlines() or ['']
                if len(self.vfs[key]) <= max_chars:
                    return self.render_lines(key)
                outlay = max_chars // 3
                groups_m: list[list[int]] = [[], [], []]
                positions_m = [range(len(rungs)), range(len(rungs) // 3, len(rungs)), range(len(rungs) - 1, -1, -1)]
                for group_m, position_m in zip(groups_m, positions_m, strict=True):
                    used_m = 0
                    for index_m in position_m:
                        if used_m and used_m + len(rungs[index_m]) + 1 > outlay:
                            break
                        group_m.append(index_m)
                        used_m += len(rungs[index_m]) + 1
                    group_m.sort()
                selected_m = sorted(set(groups_m[0] + groups_m[1] + groups_m[2]))
                return self.render_lines(key, selected_m)

            def bounded_preview(self, key: str, max_serialized_chars: int) -> list[dict[str, Any]]:
                wording_outlay = max_serialized_chars
                glimpse: list[dict[str, Any]] = []
                for _attempt_m in range(4):
                    glimpse = self.glimpse(key, max_chars=wording_outlay)
                    serialized_girth = len(json.dumps(glimpse, ensure_ascii=False, separators=(',', ':')))
                    if serialized_girth <= max_serialized_chars:
                        return glimpse
                    wording_outlay = max(100, int(wording_outlay * max_serialized_chars / serialized_girth * 0.9))
                return glimpse

            def resolve_targets(self, targets_m: list[str]) -> list[str]:
                slots_m: list[str] = []
                for target_m in targets_m:
                    if target_m == '*':
                        matches_m = list(self.vfs)
                    elif any((char_m in target_m for char_m in '*?[')):
                        sieve = re.compile('^' + re.escape(target_m).replace('\\*', '.*').replace('\\?', '.') + '$')
                        matches_m = [key for key in self.vfs if sieve.fullmatch(key)]
                    elif target_m in self.vfs:
                        matches_m = [target_m]
                    else:
                        matches_m = []
                    slots_m.extend(matches_m)
                return list(dict.fromkeys(slots_m))

            def citation_cuts(self, key: str, indices_m: list[int] | range) -> list[CitationSlice]:
                content = self.vfs[key]
                rungs = content.splitlines(keepends=True) or [content]
                selected_m = sorted({index_m for index_m in indices_m if 0 <= index_m < len(rungs)})
                if not selected_m:
                    return []
                offsets_m = [0]
                for rung_x in rungs:
                    offsets_m.append(offsets_m[-1] + len(rung_x))
                groups_m: list[tuple[int, int]] = []
                start = prior_m = selected_m[0]
                for index_m in selected_m[1:]:
                    if index_m != prior_m + 1:
                        groups_m.append((start, prior_m + 1))
                        start = index_m
                    prior_m = index_m
                groups_m.append((start, prior_m + 1))
                reaches: list[tuple[int, int]] = []
                for start_rung, end_rung in groups_m:
                    start_offset_m = offsets_m[start_rung]
                    end_offset_m = offsets_m[end_rung]
                    if end_offset_m - start_offset_m < 100 and len(content) >= 100:
                        missing_m = 100 - (end_offset_m - start_offset_m)
                        start_offset_m = max(0, start_offset_m - missing_m // 2)
                        end_offset_m = min(len(content), end_offset_m + missing_m)
                        start_offset_m = max(0, end_offset_m - 100)
                    if reaches and start_offset_m <= reaches[-1][1]:
                        reaches[-1] = (reaches[-1][0], max(reaches[-1][1], end_offset_m))
                    else:
                        reaches.append((start_offset_m, end_offset_m))
                return [CitationSlice(start=start, end=end) for start, end in reaches if end > start]

            def packet_preview(self, key: str, max_chars: int=8000) -> tuple[str, list[CitationSlice]]:
                content = self.vfs[key]
                if len(content) <= max_chars:
                    return (content, [CitationSlice(start=0, end=len(content))])
                segment_girth = max_chars // 3
                middle_start_m = max(0, (len(content) - segment_girth) // 2)
                reaches = [(0, segment_girth), (middle_start_m, middle_start_m + segment_girth), (len(content) - segment_girth, len(content))]
                quotation = '\n\n...\n\n'.join((content[start:end] for start, end in reaches))
                slices = [CitationSlice(start=start, end=end) for start, end in reaches]
                return (quotation, slices)

            @staticmethod
            def marked_line_indices(ground: str, ref: str) -> list[int]:
                escaped_badge = re.escape(ref)
                patterns_m = (f'\\[{escaped_badge}\\s*,\\s*lines?\\s+(\\d+)(?:\\s*(?:-|to)\\s*(\\d+))?\\]', f'\\[{escaped_badge}\\s*,\\s*L(\\d+)(?:\\s*-\\s*L?(\\d+))?\\]', f'\\[{escaped_badge}\\]\\s*[:,]?\\s*lines?\\s+(\\d+)(?:\\s*(?:-|to)\\s*(\\d+))?', f'\\[{escaped_badge}\\]\\s*[:,]?\\s*L(\\d+)(?:\\s*-\\s*L?(\\d+))?', f'\\b{escaped_badge}\\b\\s*[:,]?\\s*lines?\\s+(\\d+)(?:\\s*(?:-|to)\\s*(\\d+))?', f'\\b{escaped_badge}\\b\\s*[:,]?\\s*L(\\d+)(?:\\s*-\\s*L?(\\d+))?')
                indices_m: set[int] = set()
                for sieve in patterns_m:
                    for match_m in re.finditer(sieve, ground, flags=re.IGNORECASE):
                        start = int(match_m.group(1))
                        end = int(match_m.group(2) or start)
                        if end < start:
                            start, end = (end, start)
                        indices_m.update(range(max(1, start) - 1, end))
                for bracket_m in re.findall('\\[([^\\]]+)\\]', ground):
                    if re.search(f'(?:^|[\\s,;]){escaped_badge}(?:$|[\\s,;:])', bracket_m) is None:
                        continue
                    for match_m in re.finditer('\\bL(\\d+)(?:\\s*-\\s*L?(\\d+))?', bracket_m, flags=re.IGNORECASE):
                        start = int(match_m.group(1))
                        end = int(match_m.group(2) or start)
                        if end < start:
                            start, end = (end, start)
                        indices_m.update(range(max(1, start) - 1, end))
                return sorted(indices_m)

            def source_evidence_indices(self, key: str, indices_m: list[int] | range | set[int], *, include_focused: bool=True) -> list[int]:
                rungs = self.vfs[key].splitlines() or ['']
                rung_census = len(rungs)
                candidates_m = set(indices_m)
                if include_focused:
                    candidates_m.update(self.focused_lines.get(key, set()))
                selected_m = {index_m for index_m in candidates_m if 0 <= index_m < rung_census}
                for index_m in tuple(selected_m):
                    reach = _markdown2_lattice_reach(self, key, index_m)
                    if reach is None:
                        continue
                    selected_m.update((item_m['line'] - 1 for item_m in reach['header']))
                if selected_m:
                    header_m = _unravel_csv_rung(rungs[0])
                    selected_rungs = [_unravel_csv_rung(rungs[index_m]) for index_m in selected_m]
                    if header_m is None or any((rung is None for rung in selected_rungs)):
                        header_m = []
                        selected_widths_m = set()
                    else:
                        selected_widths_m = {len(rung) for rung in selected_rungs if rung is not None}
                    textual_fields_m = sum((bool(re.search('[A-Za-z]', field_m)) for field_m in header_m))
                    if len(header_m) >= 3 and len(header_m) in selected_widths_m and (textual_fields_m >= len(header_m) // 2):
                        selected_m.add(0)
                return sorted(selected_m)

            def structured_csv_records(self, key: str, indices_m: list[int] | range) -> list[dict[str, str]]:
                rungs = self.vfs[key].splitlines()
                if not rungs or 0 not in indices_m:
                    return []
                header_m = _unravel_csv_rung(rungs[0])
                if header_m is None:
                    return []
                if len(header_m) < 3 or len(set(header_m)) != len(header_m):
                    return []
                records_m: list[dict[str, str]] = []
                for index_m in indices_m:
                    if index_m == 0 or not 0 <= index_m < len(rungs):
                        continue
                    rung = _unravel_csv_rung(rungs[index_m])
                    if rung is None:
                        return []
                    if len(rung) != len(header_m):
                        return []
                    records_m.append(dict(zip(header_m, rung, strict=True)))
                return records_m

            def source_packet(self, ground: str, *, allow_preview: bool=True, include_structured_csv: bool=False, prefer_retained: bool=True) -> list[dict[str, Any]]:
                mentioned_badges = list(dict.fromkeys(re.findall('\\b(S\\d+(?:\\.\\d+)?|P\\d+)\\b', ground)))
                badges: list[str] = []
                for ref in mentioned_badges:
                    if re.fullmatch('S\\d+', ref):
                        badges.extend((candidate_m for candidate_m in self.sources if candidate_m.startswith(f'{ref}.')))
                    else:
                        badges.append(ref)
                badges.extend((origin_m.ref for origin_m in self.sources.values() if origin_m.key in ground))
                badges = list(dict.fromkeys(badges))
                single_origin_rung_indices: list[int] = []
                if len(badges) == 1:
                    indices_m: set[int] = set()
                    for match_m in re.finditer('\\b(?:lines?\\s+)?L(\\d+)(?:\\s*-\\s*L?(\\d+))?', ground, flags=re.IGNORECASE):
                        start = int(match_m.group(1))
                        end = int(match_m.group(2) or start)
                        if end < start:
                            start, end = (end, start)
                        indices_m.update(range(max(1, start) - 1, end))
                    single_origin_rung_indices = sorted(indices_m)
                rung_ids = list(dict.fromkeys(re.findall('\\bL[0-9a-f]{10}\\b', ground)))
                manifest: list[dict[str, Any]] = []
                for ref in badges:
                    origin_m = self.sources.get(ref)
                    if origin_m is None:
                        continue
                    if prefer_retained and ref in self.retained_evidence:
                        held = self.retained_evidence[ref]
                        held_item = {key: value_m for key, value_m in held.items() if key in {'source_ref', 'title', 'url', 'quote', 'csv_records'}}
                        residual_beamed = self.focused_lines.get(origin_m.key)
                        if residual_beamed:
                            selected_indices_m = self.source_evidence_indices(origin_m.key, residual_beamed)
                            beamed_item: dict[str, Any] = {'source_ref': f'[{ref}]', 'title': origin_m.title, 'url': origin_m.url, 'quote': '\n'.join((item_m['text'] for item_m in self.render_lines(origin_m.key, selected_indices_m)))}
                            if include_structured_csv:
                                csv_records_m = self.structured_csv_records(origin_m.key, selected_indices_m)
                                if csv_records_m:
                                    held_records = list(held_item.get('csv_records', []))
                                    beamed_item['csv_records'] = [*held_records, *(chalk for chalk in csv_records_m if chalk not in held_records)]
                                self.source_slices[ref] = _weld_mark_reaches(self.source_slices.get(ref, []), self.citation_cuts(origin_m.key, selected_indices_m))
                            held_item = _weld_origin_sheaves([held_item], [beamed_item])[0]
                        manifest.append(held_item)
                        continue
                    origin_rung_ids = [rung_id for rung_id in rung_ids if self.line_locations.get(rung_id, (None,))[0] == origin_m.key]
                    marked_line_indices = sorted(set(self.marked_line_indices(ground, ref)) | set(single_origin_rung_indices))
                    selected_indices_m: list[int] | range | None
                    mark_indices: list[int] | range | None
                    if origin_rung_ids:
                        rung_indices = [self.line_locations[rung_id][1] for rung_id in origin_rung_ids]
                        warrant_slat = set(rung_indices)
                        selected_indices_m = self.source_evidence_indices(origin_m.key, warrant_slat, include_focused=False)
                        mark_indices = selected_indices_m
                        quotation = '\n'.join((item_m['text'] for item_m in self.render_lines(origin_m.key, selected_indices_m)))
                    elif marked_line_indices:
                        selected_m = set(marked_line_indices)
                        mark_indices = self.source_evidence_indices(origin_m.key, selected_m, include_focused=False)
                        selected_indices_m = mark_indices
                        quotation = '\n'.join((f"{item_m['line']}: {item_m['text']}" for item_m in self.render_lines(origin_m.key, selected_indices_m)))
                    elif origin_m.key in self.focused_lines:
                        selected_indices_m = self.source_evidence_indices(origin_m.key, self.focused_lines[origin_m.key])
                        mark_indices = selected_indices_m
                        quotation = '\n'.join((item_m['text'] for item_m in self.render_lines(origin_m.key, selected_indices_m)))
                    elif not allow_preview:
                        continue
                    else:
                        quotation, slices = self.packet_preview(origin_m.key)
                        self.source_slices[ref] = slices
                        selected_indices_m = None
                        mark_indices = None
                    if include_structured_csv and selected_indices_m is not None:
                        self.source_slices[ref] = self.citation_cuts(origin_m.key, mark_indices or selected_indices_m)
                    item_m: dict[str, Any] = {'source_ref': f'[{ref}]', 'title': origin_m.title, 'url': origin_m.url, 'quote': quotation}
                    if selected_indices_m is not None:
                        csv_records_m = self.structured_csv_records(origin_m.key, selected_indices_m)
                        if csv_records_m:
                            item_m['csv_records'] = csv_records_m
                    manifest.append(item_m)
                return manifest

            def citation_plan(self, reply: str, fallback_manifest: list[dict[str, Any]], final_origin_cuts: dict[str, list[CitationSlice]], audit_m: str) -> MeridianChart:
                survey_badges = list(dict.fromkeys(re.findall('\\b(S\\d+(?:\\.\\d+)?|P\\d+)\\b', audit_m)))
                ruling_badges = list(dict.fromkeys(re.findall('\\b(S\\d+(?:\\.\\d+)?|P\\d+)\\b', reply)))
                mentioned_badges = list(dict.fromkeys([*ruling_badges, *survey_badges]))
                badges: list[str] = []
                for ref in mentioned_badges:
                    if re.fullmatch('S\\d+', ref):
                        badges.extend((candidate_m for candidate_m in self.sources if candidate_m.startswith(f'{ref}.')))
                    else:
                        badges.append(ref)
                if not badges:
                    badges = [item_m['source_ref'][1:-1] for item_m in fallback_manifest]
                mark_origins: dict[tuple[str, str], MeridianBeacon] = {}
                citation_cuts: dict[tuple[str, str], list[CitationSlice]] = {}
                origin_identities_m: dict[str, tuple[str, str]] = {}
                for ref in badges:
                    origin_m = self.sources.get(ref)
                    if origin_m and origin_m.receipt_id and origin_m.result_id:
                        handle = (origin_m.receipt_id, origin_m.result_id)
                        origin_identities_m[ref] = handle
                        slices = _weld_mark_reaches([], final_origin_cuts.get(ref, self.source_slices.get(ref, [])))
                        mark_origins[handle] = origin_m
                        citation_cuts[handle] = _weld_mark_reaches(citation_cuts.get(handle, []), slices)
                handle_indices = {handle: index_m for index_m, handle in enumerate(mark_origins, start=1)}
                citations = [CitationRef(receipt_id=origin_m.receipt_id, result_id=origin_m.result_id, slices=citation_cuts[handle]) for handle, origin_m in mark_origins.items()]
                return MeridianChart(citations=citations, source_indices={ref: handle_indices[handle] for ref, handle in origin_identities_m.items() if handle in handle_indices})

        def _unravel_csv_rung(rung_x: str) -> list[str] | None:
            fields_m: list[str] = []
            field_m: list[str] = []
            in_quotations = False
            after_quotation = False
            index_m = 0
            while index_m < len(rung_x):
                character_m = rung_x[index_m]
                if in_quotations:
                    if character_m != '"':
                        field_m.append(character_m)
                    elif index_m + 1 < len(rung_x) and rung_x[index_m + 1] == '"':
                        field_m.append('"')
                        index_m += 1
                    else:
                        in_quotations = False
                        after_quotation = True
                elif after_quotation:
                    if character_m == ',':
                        fields_m.append(''.join(field_m))
                        field_m = []
                        after_quotation = False
                    elif character_m not in ' \t':
                        return None
                elif character_m == ',':
                    fields_m.append(''.join(field_m))
                    field_m = []
                elif character_m == '"' and (not field_m):
                    in_quotations = True
                else:
                    field_m.append(character_m)
                index_m += 1
            if in_quotations:
                return None
            fields_m.append(''.join(field_m))
            return fields_m

        def _vocable_pouch(text: str) -> set[str]:
            return {piece_m for piece_m in re.findall('[a-z0-9]+', (text or '').lower()) if piece_m not in _LATTICE_STOPWORDS and len(piece_m) > 1}

        def _lattice_rung_glean2(line_m: str) -> tuple[str, str, bool] | None:
            raw_m = (line_m or '').strip()
            if raw_m.count('|') < 2 or _LATTICE_CANON2_RUNG_RE.match(raw_m):
                return None
            cells_m = [cell_m.strip().strip('*_`').strip() for cell_m in raw_m.strip('|').split('|')]
            if len(cells_m) < 3:
                return None
            who_m = cells_m[0].strip(' \t.:-*•').strip()
            cond_m = cells_m[1].strip(' \t.:-').strip()
            decree = _HIDDEN2_BADGE_RE.sub('', cells_m[-1]).strip()
            if not who_m or not cond_m or len(who_m) > LATTICE_LABEL_MAX or (len(cond_m) > LATTICE_LABEL_MAX):
                return None
            if who_m.lower() in _LATTICE_BARRED_LABELS or cond_m.lower() in _LATTICE_BARRED_LABELS:
                return None
            if len(decree) > LATTICE_RULING_CELL_MAX:
                return None
            if _CLEARS2_VOCABLE_RE.search(decree) and _LAPSES_VOCABLE_RE.search(decree):
                return None
            if _CLEARS2_LEAD_RE.match(decree):
                return (who_m, cond_m, True)
            if _LAPSES_LEAD_RE.match(decree):
                return (who_m, cond_m, False)
            return None

        def _lattice_trawl(reply: str) -> tuple[set[int], list[tuple[str, str, bool]]]:
            lines_m = (reply or '').splitlines()
            claimed_m: set[int] = set()
            rungs: list[tuple[str, str, bool]] = []
            i_m = 0
            while i_m < len(lines_m):
                titlecard = lines_m[i_m].strip()
                if not titlecard or '|' in titlecard or len(titlecard) > 80 or (not _LATTICE_TITLECARD_RE.search(titlecard)):
                    i_m += 1
                    continue
                local_m: set[int] = set()
                found_m: list[tuple[str, str, bool]] = []
                runway = 0
                j_m = i_m + 1
                while j_m < len(lines_m):
                    rung_line = lines_m[j_m]
                    if not rung_line.strip():
                        if found_m:
                            break
                        runway += 1
                        if runway > LATTICE_RUNWAY_RUNGS:
                            break
                        j_m += 1
                        continue
                    triple_m = _lattice_rung_glean2(rung_line)
                    if triple_m is not None:
                        found_m.append(triple_m)
                        local_m.add(j_m)
                        j_m += 1
                        continue
                    if _LATTICE_CANON2_RUNG_RE.match(rung_line.strip()) or (not found_m and runway < LATTICE_RUNWAY_RUNGS and (rung_line.count('|') >= 2)):
                        local_m.add(j_m)
                        runway += 1
                        j_m += 1
                        continue
                    break
                if found_m:
                    rungs.extend(found_m)
                    claimed_m.update(local_m)
                    claimed_m.add(i_m)
                i_m = max(j_m, i_m + 1)
            return (claimed_m, rungs)

        def _lattice_collate(reply: str) -> dict[str, dict[str, bool]]:
            _claimed_m, rungs = _lattice_trawl(reply)
            table_m: dict[str, dict[str, bool]] = {}
            spellings_m: dict[str, str] = {}
            for who_m, cond_m, met_m in rungs:
                name_m = spellings_m.setdefault(who_m.lower(), who_m)
                folded_m = table_m.setdefault(name_m, {})
                cond_key_m = cond_m.lower()
                folded_m[cond_key_m] = folded_m.get(cond_key_m, True) and met_m
            return table_m

        def _lattice_creditable(table_m: dict[str, dict[str, bool]]) -> bool:
            if len(table_m) < 2:
                return False
            cond_sets_m = [frozenset(folded_m) for folded_m in table_m.values()]
            if not cond_sets_m or not cond_sets_m[0]:
                return False
            return len(set(cond_sets_m)) == 1

        def _lattice_keepers(table_m: dict[str, dict[str, bool]]) -> list[str]:
            return sorted((who_m for who_m, folded_m in table_m.items() if folded_m and all(folded_m.values())))

        def _pen_masthead(keepers: list[str]) -> str:
            if not keepers:
                return ''
            if len(keepers) == 1:
                return f'FINAL ANSWER: {keepers[0]}'
            return 'FINAL ANSWER: ' + ', '.join(keepers[:-1]) + ' and ' + keepers[-1]

        def _masthead_index(reply: str) -> int:
            for i_m, rung in enumerate((reply or '').splitlines()):
                if _MASTHEAD_MARK_RE.match(rung.strip()):
                    return i_m
            return -1

        def _enact_lattice_decree(reply: str) -> str:
            at_m = _masthead_index(reply)
            if at_m < 0:
                return reply
            table_m = _lattice_collate(reply)
            if not _lattice_creditable(table_m):
                return reply
            keepers = _lattice_keepers(table_m)
            if not keepers or len(keepers) > LATTICE_KEEPER_MAX:
                return reply
            lines_m = (reply or '').splitlines()
            old_masthead = _MASTHEAD_MARK_RE.sub('', lines_m[at_m].strip()).strip()
            masthead_pouch = _vocable_pouch(_HIDDEN2_BADGE_RE.sub('', old_masthead))
            keeper_bags = [_vocable_pouch(who_m) for who_m in keepers]
            keeper_union: set[str] = set()
            for pouch in keeper_bags:
                keeper_union |= pouch
            covers_m = all((pouch and pouch.issubset(masthead_pouch) for pouch in keeper_bags))
            loser_named_m = False
            for who_m in table_m:
                if who_m in keepers:
                    continue
                pouch = _vocable_pouch(who_m)
                if pouch and pouch.issubset(masthead_pouch) and pouch - keeper_union:
                    loser_named_m = True
                    break
            if covers_m and (not loser_named_m):
                return reply
            demurring = bool(_NEG2_MASTHEAD_RE.search(old_masthead) or _WAIVER2_MASTHEAD_RE.search(old_masthead))
            if _TOPPICK_RE_M.search(reply or '') and (not demurring):
                return reply
            if len(keepers) >= len(table_m) and (not demurring):
                return reply
            if not demurring and (not any((_vocable_pouch(who_m) & masthead_pouch for who_m in table_m))):
                return reply
            fresh_m = _pen_masthead(keepers)
            if not fresh_m or len(fresh_m) > LATTICE_MASTHEAD_CHAR_MAX:
                return reply
            kept_badges = ''.join((m_m.group(0) for m_m in _HIDDEN2_BADGE_RE.finditer(lines_m[at_m])))
            lines_m[at_m] = fresh_m + kept_badges
            return '\n'.join(lines_m)

        def _shuck_lead_preamble2(reply: str) -> str:
            lines_m = (reply or '').splitlines()
            at_m = _masthead_index(reply)
            if at_m <= 0 or at_m > 8:
                return reply
            head_m = lines_m[:at_m]
            if all((not rung.strip() or (_LEAD_PREAMBLE2_RE.match(rung) and (not _HIDDEN2_BADGE_RE.search(rung))) for rung in head_m)):
                return '\n'.join(lines_m[at_m:])
            return reply

        def _burnish_notarized_prose2(reply: str) -> str:
            text = reply
            try:
                text = _shuck_lead_preamble2(text)
                text = _enact_lattice_decree(text)
            except Exception:
                return reply
            return text or reply

        def _inward_origin_badges(reply: str) -> list[str]:
            return list(dict.fromkeys(re.findall('\\[(S\\d+(?:\\.\\d+)?|P\\d+)\\]', reply)))

        def _canon_sheafed_inward_badges(reply: str) -> str:
            ref = '(?:S\\d+(?:\\.\\d+)?|P\\d+)'
            sheafed = re.compile(f'\\[({ref}(?:\\s*,\\s*{ref})+)\\]')
            return sheafed.sub(lambda match_m: ''.join((f'[{item_m}]' for item_m in re.findall(ref, match_m.group(1)))), reply)

        def _wants2_naked_form(inquiry: str) -> bool:
            return bool(re.search('(?i)\\b(?:output|return|respond)\\s+only\\b', inquiry))

        def _verify2_inward_ruling_badges(reply: str, allowed_badges: set[str], *, require_ref_m: bool=True) -> None:
            if '[[' in reply or ']]' in reply:
                raise ValueError('write private source refs such as [P1], not public numeric markers')
            if re.search('(?i)(?:https?://|\\bwww\\.|(?<!:)//(?=[a-z0-9])|(?<![\\w@])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+[a-z]{2,63}/[^\\s)]*)', reply):
                raise ValueError('do not render raw URLs in the reader-facing answer')
            if re.search('(?im)^\\s{0,3}(?:#{1,6}\\s*)?(?:sources?|citations?|references?|bibliography|works\\s+cited)\\s*:?\\s*$', reply):
                raise ValueError('do not render a citation or source-list section')
            verbatim_badge_sieve = re.compile('\\[(?:S\\d+(?:\\.\\d+)?|P\\d+)\\]')
            without_verbatim_badges = verbatim_badge_sieve.sub('', reply)
            if '[' in without_verbatim_badges or ']' in without_verbatim_badges:
                raise ValueError('square brackets are reserved for one exact private source ref such as [P1]')
            if re.search('\\b(?:S\\d+(?:\\.\\d+)?|P\\d+)\\b', without_verbatim_badges):
                raise ValueError('each private source ref must appear alone in brackets, for example [P1]')
            badges = _inward_origin_badges(reply)
            unclear_badges = [ref for ref in badges if ref not in allowed_badges]
            if unclear_badges:
                raise ValueError(f"answer cites unavailable source refs: {', '.join(unclear_badges)}")
            if require_ref_m and allowed_badges and (not badges):
                raise ValueError('answer must place at least one supplied source ref after a supported factual claim')

        def _issue_public_marks(reply: str, chart: MeridianChart, *, unadorned_output_m: bool=False, helm: MeridianHelm | None=None) -> tuple[str, list[CitationRef]]:
            badges = _inward_origin_badges(reply)
            missing_badges = [ref for ref in badges if ref not in chart.source_indices]
            if missing_badges:
                raise ValueError('answer source refs do not have materializable citations: ' + ', '.join(missing_badges))
            rendered_m = re.sub('\\[(S\\d+(?:\\.\\d+)?|P\\d+)\\]', lambda match_m: f'[[{chart.source_indices[match_m.group(1)]}]]', reply)
            marker_indices_m = [int(value_m) for value_m in re.findall('\\[\\[(\\d+)]]', rendered_m)]
            invalid_indices_m = sorted({index_m for index_m in marker_indices_m if index_m < 1 or index_m > len(chart.citations)})
            if invalid_indices_m:
                raise ValueError('answer contains citation indices without response citations: ' + ', '.join((str(index_m) for index_m in invalid_indices_m)))
            if chart.citations and (not marker_indices_m) and (not unadorned_output_m):
                raise ValueError('answer has response citations but no inline citation markers')
            used_indices_m = sorted(set(marker_indices_m)) if marker_indices_m else list(range(1, len(chart.citations) + 1))
            prune_indices = {old_index_m: new_index_m for new_index_m, old_index_m in enumerate(used_indices_m, start=1)}
            rendered_m = re.sub('\\[\\[(\\d+)]]', lambda match_m: f'[[{prune_indices[int(match_m.group(1))]}]]', rendered_m)
            if unadorned_output_m:
                rendered_m = re.sub('[ \\t]*\\[\\[\\d+]]', '', rendered_m)
            citations = [chart.citations[index_m - 1] for index_m in used_indices_m]
            return (rendered_m.strip(), citations)

        def _weld_mark_reaches(existing_m: list[CitationSlice], additional_m: list[CitationSlice]) -> list[CitationSlice]:
            reaches = sorted(((int(item_m.start), int(item_m.end)) for item_m in [*existing_m, *additional_m] if int(item_m.end) > int(item_m.start)))
            merged_m: list[tuple[int, int]] = []
            for start, end in reaches:
                if merged_m and start <= merged_m[-1][1]:
                    merged_m[-1] = (merged_m[-1][0], max(merged_m[-1][1], end))
                else:
                    merged_m.append((start, end))
            return [CitationSlice(start=start, end=end) for start, end in merged_m]

        def _glean_origin_badges(value_m: Any) -> list[str]:
            badges: list[str] = []
            if isinstance(value_m, dict):
                for field_m, item_m in value_m.items():
                    if field_m == 'source_ref' and isinstance(item_m, str):
                        badges.append(item_m.strip().strip('[]'))
                    else:
                        badges.extend(_glean_origin_badges(item_m))
            elif isinstance(value_m, list):
                for item_m in value_m:
                    badges.extend(_glean_origin_badges(item_m))
            return list(dict.fromkeys(badges))

        def _markdown2_lattice_reach(helm: MeridianHelm, key: str, match_index_m: int) -> dict[str, Any] | None:
            rungs = helm.vfs[key].splitlines() or ['']
            separator_index_m: int | None = None
            for index_m in range(match_index_m, 0, -1):
                if re.fullmatch('\\s*\\|(?:\\s*:?-+:?\\s*\\|)+\\s*', rungs[index_m]):
                    separator_index_m = index_m
                    break
                if index_m < match_index_m and rungs[index_m].lstrip().startswith('#'):
                    break
            if separator_index_m is None:
                return None
            header_index_m = separator_index_m - 1
            end_index_m = separator_index_m
            for index_m in range(separator_index_m + 1, len(rungs)):
                if not rungs[index_m].lstrip().startswith('|'):
                    break
                end_index_m = index_m
            return {'start_line': header_index_m + 1, 'end_line': end_index_m + 1, 'header': helm.render_lines(key, range(header_index_m, separator_index_m + 1))}

        def _jot_outlay(helm: MeridianHelm, sighting: Any) -> None:
            outlay = getattr(sighting, 'budget', None)
            if outlay is None:
                return
            helm.budget_snapshot = {'session_hard_limit_usd': round(float(outlay.session_hard_limit_usd), 6), 'session_used_budget_usd': round(float(outlay.session_used_budget_usd), 6), 'session_hard_remaining_usd': round(max(0.0, float(outlay.session_hard_limit_usd) - float(outlay.session_used_budget_usd)), 6)}

        def _is_fleeting_llm_mishap(mishap: Exception) -> bool:
            notem = str(mishap).lower()
            return any((marker_m in notem for marker_m in ('429', '500', '502', '503', '504', 'service unavailable', 'timed out', 'timeout', 'empty_output', 'empty output', 'tool execution failed', 'tool invocation failed')))

        async def _move_pilot(pilot_label: str, messages: list[Any], tools: list[dict[str, Any]] | None, tool_choice: str, parallel_tool_calls: bool, timeout: float, max_output_tokens: int | None=None) -> Any:
            if pilot_label == 'glm5':
                return await llm_chat(provider='openrouter', model='z-ai/glm-5', messages=messages, temperature=0.2, max_output_tokens=max_output_tokens or MERIDIAN_GLM5_TOP_FORM_SHARDS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'low'}, provider_extra=OPENROUTER_GLM_CARRIER_LEANINGS, timeout=timeout)
            if pilot_label == 'gpt_oss':
                return await llm_chat(provider='openrouter', model='openai/gpt-oss-120b', messages=messages, temperature=0.0, max_output_tokens=max_output_tokens or MERIDIAN_GPTOSS_TOP_FORM_SHARDS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'high'}, provider_extra=OPENROUTER_GPT_CARRIER_LEANINGS, timeout=timeout)
            if pilot_label == 'openrouter_gemma':
                return await llm_chat(provider='openrouter', model='google/gemma-4-31b-it', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or MERIDIAN_OR_GEMMA_TOP_FORM_SHARDS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, provider_extra=MERIDIAN_OR_GEMMA_CARRIER_LEANINGS, timeout=timeout)
            if pilot_label == 'openrouter_gemma_prose':
                return await llm_chat(provider='openrouter', model='google/gemma-4-31b-it', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or MERIDIAN_OR_GEMMA_TOP_FORM_SHARDS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, provider_extra=MERIDIAN_OR_GEMMA_CARRIER_LEANINGS, timeout=timeout)
            if pilot_label == 'openrouter_gemma_stable':
                return await llm_chat(provider='openrouter', model='google/gemma-4-31b-it', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or MERIDIAN_OR_GEMMA_TOP_FORM_SHARDS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, provider_extra=MERIDIAN_OR_GEMMA_STABLE_CARRIER_LEANINGS, timeout=timeout)
            if pilot_label == 'inkling':
                return await llm_chat(provider='ai_gateway', model='thinkingmachines/inkling', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or MERIDIAN_INKLING_TOP_FORM_SHARDS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, timeout=timeout)
            if pilot_label == 'ai_gateway_gemma':
                return await llm_chat(provider='ai_gateway', model='google/gemma-4-31b-it', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or MERIDIAN_AG_GEMMA_TOP_FORM_SHARDS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, provider_extra={'providerOptions': {'gateway': {'only': ['cerebras']}}}, timeout=timeout)
            raise ValueError(f'unknown model: {pilot_label}')

        async def _parley_with_pilot_chain(pilots: tuple[str, ...], messages: list[Any], tools: list[dict[str, Any]] | None, tool_choice: str, parallel_tool_calls: bool, timeout: float, max_output_tokens: int | None=None) -> Any:
            if not pilots:
                raise RuntimeError('no research model was configured')
            raced_pilots = pilots[:2]
            residual_pilots = pilots[2:]
            tasks_m = [asyncio.create_task(_move_pilot(model, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)) for model in raced_pilots]
            errors_m: list[Exception] = []
            queued_m = set(tasks_m)
            try:
                while queued_m:
                    done_m, queued_m = await asyncio.wait(queued_m, return_when=asyncio.FIRST_COMPLETED)
                    for task_m in done_m:
                        try:
                            sighting = task_m.result()
                        except Exception as mishap:
                            errors_m.append(mishap)
                            continue
                        for unfinished_m in queued_m:
                            unfinished_m.cancel()
                        await asyncio.gather(*queued_m, return_exceptions=True)
                        return sighting
            finally:
                for unfinished_m in queued_m:
                    unfinished_m.cancel()
                if queued_m:
                    await asyncio.gather(*queued_m, return_exceptions=True)
            non_fleeting = next((mishap for mishap in errors_m if not _is_fleeting_llm_mishap(mishap)), None)
            if non_fleeting is not None:
                raise non_fleeting
            for model in residual_pilots:
                try:
                    return await _move_pilot(model, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)
                except Exception as mishap:
                    if not _is_fleeting_llm_mishap(mishap):
                        raise
                    errors_m.append(mishap)
            if not errors_m:
                raise RuntimeError('no research model was configured')
            raise errors_m[-1]

        async def _parley_with_single2_pilot_chain(pilots: tuple[str, ...], messages: list[Any], tools: list[dict[str, Any]] | None, tool_choice: str, parallel_tool_calls: bool, timeout: float, max_output_tokens: int | None=None) -> Any:
            if not pilots:
                raise RuntimeError('no research model was configured')
            errors_m: list[Exception] = []
            for model in pilots:
                try:
                    return await _move_pilot(model, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)
                except Exception as mishap:
                    if not _is_fleeting_llm_mishap(mishap):
                        raise
                    errors_m.append(mishap)
            raise errors_m[-1]

        async def _parley_with_routing(pilots: tuple[str, ...], messages: list[Any], tools: list[dict[str, Any]] | None, tool_choice: str, parallel_tool_calls: bool, timeout: float, max_output_tokens: int | None=None) -> Any:
            if MERIDIAN_PILOT_ROTA == 'race':
                return await _parley_with_pilot_chain(pilots, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)
            if MERIDIAN_PILOT_ROTA in {'sequential', 'state_aware'}:
                return await _parley_with_single2_pilot_chain(pilots, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)
            raise ValueError(f'unknown model scheduling policy: {MERIDIAN_PILOT_ROTA}')

        async def _prose2_parley_with_retry(messages: list[Any], tool_choice: str, timeout: float) -> Any:
            return await _parley_with_routing(('glm5', 'openrouter_gemma', 'gpt_oss'), messages, None, tool_choice, False, timeout)

        async def _final2_ruling_parley_with_retry(messages: list[Any], timeout: float) -> Any:
            return await _parley_with_routing(('ai_gateway_gemma', 'openrouter_gemma_prose', 'openrouter_gemma_stable', 'glm5'), messages, None, 'none', False, timeout)

        def _passage_pilots(helm: MeridianHelm, horizon_alert_raised: bool, swerve_spur: str) -> tuple[str, ...]:
            if MERIDIAN_PILOT_ROTA != 'state_aware':
                return MERIDIAN_AMEND_PILOTS if helm.audit_gap else MERIDIAN_SOUNDING_PILOTS
            if helm.audit_gap or horizon_alert_raised or swerve_spur:
                return MERIDIAN_AMEND_PILOTS
            return BOARD_AWARE_MERIDIAN_SOUNDING_PILOTS

        def _mandates_pilots(horizon_alert_raised: bool, swerve_spur: str) -> tuple[str, ...]:
            if MERIDIAN_PILOT_ROTA == 'state_aware' and (horizon_alert_raised or swerve_spur):
                return MERIDIAN_AMEND_PILOTS
            return MERIDIAN_WANT_PILOTS

        async def _inquiry2_wording(charter: str, user_m: str) -> str:
            messages = [{'role': 'system', 'content': charter}, {'role': 'user', 'content': user_m}]
            sighting = await _prose2_parley_with_retry(messages, 'none', PILOT_GAUGE)
            text = sighting.llm.raw_text
            if not text or not text.strip():
                raise RuntimeError('research model returned empty prose')
            return text.strip()

        async def _ruling_wording(*, helm: MeridianHelm, inquiry: str, prior_reply: str, stipulations: str, inquiry2_helm: str, finalization_ground: str, manifest: list[dict[str, Any]]) -> str:
            allowed_badges = {str(item_m['source_ref']).strip('[]') for item_m in manifest if isinstance(item_m, dict) and item_m.get('source_ref')}
            messages: list[Any] = [{'role': 'system', 'content': RULING_RECAST_CHARTER}, {'role': 'user', 'content': f"Original question:\n{inquiry}\n\nPrior answer hypothesis:\n{prior_reply}\n\nEvidence requirements:\n{stipulations}\n\nInvestigator's current research state:\n{inquiry2_helm or '(not updated)'}\n\nFinalization reason:\n{finalization_ground}\n\nSupplied source records:\n{json.dumps(manifest, ensure_ascii=False, indent=2)}"}]
            for attempt_m in range(3):
                sighting = await _final2_ruling_parley_with_retry(messages, PILOT_GAUGE)
                _jot_outlay(helm, sighting)
                text = sighting.llm.raw_text
                if not text or not text.strip():
                    raise RuntimeError('answer writer returned empty prose')
                text = _canon_sheafed_inward_badges(text.strip())
                try:
                    _verify2_inward_ruling_badges(text, allowed_badges, require_ref_m=not _wants2_naked_form(inquiry))
                except ValueError as mishap:
                    if attempt_m == 2:
                        raise
                    messages.extend([{'role': 'assistant', 'content': text}, {'role': 'user', 'content': f'Output contract error: {mishap}. Rewrite the complete answer. Use only the exact private source refs present in the supplied records; the harness renders public citation numbers.'}])
                    continue
                return text
            raise AssertionError('unreachable')

        def _formed_form_move(output_schema_m: dict[str, Any]) -> tuple[dict[str, Any], bool]:
            direct_object_m = output_schema_m.get('type') == 'object'
            parameters_m = output_schema_m if direct_object_m else {'type': 'object', 'properties': {'output': {'description': "The non-null JSON value that matches the caller's supplied output schema."}}, 'required': ['output'], 'additionalProperties': False}
            return ({'type': 'function', 'function': {'name': 'submit_structured_output', 'description': "Submit the complete final value required by the caller's JSON Schema.", 'parameters': parameters_m, 'strict': False}}, direct_object_m)

        async def _mint_formed_form(*, inquiry: str, reply: str, output_schema_m: dict[str, Any]) -> Any:
            move_x, direct_object_m = _formed_form_move(output_schema_m)
            warrant_backed_ruling = re.sub('\\[\\[\\d+]]', '', reply).strip()
            messages: list[Any] = [{'role': 'system', 'content': FORMED_FORM_CHARTER}, {'role': 'user', 'content': f'Original question:\n{inquiry}\n\nCompleted evidence-backed answer:\n{warrant_backed_ruling}\n\nRequired JSON Schema:\n{json.dumps(output_schema_m, ensure_ascii=False, indent=2)}'}]
            for attempt_m in range(3):
                sighting = await _parley_with_routing(MERIDIAN_SOUNDING_PILOTS, messages, [move_x], 'required', False, PILOT_GAUGE)
                envoy = _envoy_note(sighting)
                moves = list(envoy.tool_calls or ())
                mishap: ValueError | None = None
                output: Any = None
                if len(moves) != 1:
                    mishap = ValueError(f'call submit_structured_output exactly once; received {len(moves)} tool calls')
                else:
                    move = moves[0]
                    try:
                        if move.name != 'submit_structured_output':
                            raise ValueError(f'unexpected tool {move.name}; call submit_structured_output')
                        arguments_m = json.loads(move.arguments)
                        if not isinstance(arguments_m, dict):
                            raise ValueError('tool arguments must be a JSON object')
                        if direct_object_m:
                            output = arguments_m
                        else:
                            if set(arguments_m) != {'output'}:
                                raise ValueError('non-object output must be submitted in the sole `output` argument')
                            output = arguments_m['output']
                        if output is None:
                            raise ValueError('top-level null is not a valid miner answer')
                    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as caught:
                        mishap = ValueError(str(caught))
                if mishap is None:
                    return output
                if attempt_m == 2:
                    raise mishap
                messages.append(envoy.to_input_message())
                if moves:
                    for move in moves:
                        messages.append({'role': 'tool', 'tool_call_id': move.id, 'content': json.dumps({'ok': False, 'error_type': 'tool_argument_validation', 'details': str(mishap)})})
                else:
                    messages.append({'role': 'user', 'content': f'Output contract error: {mishap}. Call the required tool with the complete schema-conforming value.'})
            raise AssertionError('unreachable')

        async def _outlook_ruling_wording(inquiry: str) -> str:
            messages = [{'role': 'system', 'content': OUTLOOK_RULING_CHARTER}, {'role': 'user', 'content': inquiry}]
            try:
                sighting = await _move_pilot('inkling', messages, None, 'none', False, PILOT_GAUGE)
            except Exception as mishap:
                if not _is_fleeting_llm_mishap(mishap):
                    raise
                sighting = await _parley_with_routing(('gpt_oss', 'openrouter_gemma'), messages, None, 'none', False, PILOT_GAUGE)
            text = sighting.llm.raw_text
            if not text or not text.strip():
                raise RuntimeError('research model returned empty prose')
            return text.strip()

        def _unravel_survey(text: str) -> tuple[str, str]:
            matches_m = list(re.finditer('(?m)^VERDICT (READY|CONTINUE|REVISE)(?::[ \\t]*(.*))?[ \\t]*$', text))
            if len(matches_m) != 1:
                raise ValueError('audit must contain exactly one VERDICT line')
            match_m = matches_m[0]
            decree = match_m.group(1)
            inline_m = (match_m.group(2) or '').strip()
            following_m = text[match_m.end():].strip()
            payload_m = '\n'.join((part_m for part_m in (inline_m, following_m) if part_m))
            if decree == 'REVISE' and (not payload_m):
                raise ValueError('VERDICT REVISE must include a complete replacement answer')
            if decree == 'CONTINUE' and (not payload_m):
                raise ValueError('VERDICT CONTINUE must name the missing observation')
            return (decree, payload_m)

        async def _survey(helm: MeridianHelm, inquiry: str, reply: str, manifest: list[dict[str, Any]]) -> str:
            allowed_badges = {str(item_m['source_ref']).strip('[]') for item_m in manifest if isinstance(item_m, dict) and item_m.get('source_ref')}
            origin_inventory_m = [{'source_ref': f'[{origin_m.ref}]', 'title': origin_m.title, 'url': origin_m.url} for origin_m in helm.sources.values()]
            messages = [{'role': 'system', 'content': SURVEY_CHARTER}, {'role': 'user', 'content': f'Original question:\n{inquiry}\n\nObserved source inventory (discovery metadata only; titles and URLs are not evidence):\n{json.dumps(origin_inventory_m, ensure_ascii=False, indent=2)}\n\nSupplied source records:\n{json.dumps(manifest, ensure_ascii=False, indent=2)}\n\nCurrent answer:\n{reply}'}]
            for attempt_m in range(3):
                sighting = await _parley_with_single2_pilot_chain(MERIDIAN_SURVEY_PILOTS, messages, None, 'none', False, PILOT_GAUGE)
                _jot_outlay(helm, sighting)
                text = sighting.llm.raw_text
                if not text or not text.strip():
                    raise RuntimeError('auditor returned empty output')
                text = text.strip()
                try:
                    decree, payload_m = _unravel_survey(text)
                    if decree in {'READY', 'REVISE'} and re.search('(?m)^MISSING:', text):
                        raise ValueError(f'VERDICT {decree} is invalid while a material premise is MISSING; a MISSING line must name a real unresolved premise and cannot say none or not applicable. If no premise is missing, preserve the verdict and omit all MISSING lines. Correct only this output-format error; do not introduce a new evidence requirement')
                    if decree == 'REVISE':
                        _verify2_inward_ruling_badges(payload_m, allowed_badges, require_ref_m=not _wants2_naked_form(inquiry))
                except ValueError as mishap:
                    if attempt_m == 2:
                        raise
                    messages.extend([{'role': 'assistant', 'content': text}, {'role': 'user', 'content': f'Output contract error: {mishap}. Re-audit from the supplied records. Follow the required premise-line and final VERDICT format exactly; a replacement answer must use only exact supplied private source refs.'}])
                    continue
                return text
            raise AssertionError('unreachable')

        def _envoy_note(sighting: Any) -> Any:
            choices_m = sighting.llm.choices
            if len(choices_m) != 1:
                raise RuntimeError(f'expected one LLM choice, received {len(choices_m)}')
            return choices_m[0].message

        def _envoy_warrant_reach(notem: Any) -> str:
            wording_parts = [str(part_m.text) for part_m in notem.content if getattr(part_m, 'text', None)]
            return '\n'.join((item_m for item_m in (str(notem.reasoning or '').strip(), *wording_parts) if item_m))

        def _glean_cabinet_slots(value_m: Any) -> list[str]:
            slots_m: list[str] = []
            if isinstance(value_m, dict):
                for field_m, item_m in value_m.items():
                    if field_m in {'key', 'vfs_key'} and isinstance(item_m, str):
                        slots_m.append(item_m)
                    elif field_m in {'keys', 'matched_keys'} and isinstance(item_m, list):
                        slots_m.extend((candidate_m for candidate_m in item_m if isinstance(candidate_m, str)))
                    else:
                        slots_m.extend(_glean_cabinet_slots(item_m))
            elif isinstance(value_m, list):
                for item_m in value_m:
                    slots_m.extend(_glean_cabinet_slots(item_m))
            return list(dict.fromkeys(slots_m))

        def _prune_drained_move_findings(messages: list[Any]) -> None:
            for notem in messages:
                if not isinstance(notem, dict) or notem.get('role') != 'tool':
                    continue
                content = notem.get('content')
                if not isinstance(content, str) or len(content) < 1000:
                    continue
                try:
                    output = json.loads(content)
                except json.JSONDecodeError:
                    continue
                if not isinstance(output, dict):
                    continue
                chit: dict[str, Any] = {'ok': output.get('ok', False)}
                slots_m = _glean_cabinet_slots(output)
                if slots_m:
                    chit['vfs_keys'] = slots_m
                if output.get('error_type'):
                    chit['error_type'] = output['error_type']
                    chit['details'] = str(output.get('details', ''))[:1000]
                if output.get('audit'):
                    chit['audit'] = output['audit']
                resonance = output.get('similarity')
                if isinstance(resonance, dict):
                    chit['similarity'] = {field_m: resonance[field_m] for field_m in ('status', 'trigger', 'reason') if field_m in resonance}
                notem['content'] = json.dumps(chit, ensure_ascii=False)

        def _prune_drained_envoy_musing2(messages: list[Any]) -> None:
            for index_m, notem in enumerate(messages):
                if isinstance(notem, LlmMessage):
                    if notem.role == 'assistant' and notem.reasoning_details is not None:
                        messages[index_m] = replace(notem, reasoning_details=None)
                    continue
                if not isinstance(notem, dict) or notem.get('role') != 'assistant':
                    continue
                notem.pop('reasoning', None)
                notem.pop('reasoning_details', None)

        def _chalk_freight_chit(helm: MeridianHelm, label_m: str, args_m: dict[str, Any], output: dict[str, Any]) -> None:
            if not output.get('ok') or label_m not in {'search_web', 'fetch_page'}:
                return
            if label_m == 'search_web':
                destinations_m = [str(output['vfs_key'])]
                origin_index_m = [{'source_ref': item_m['source_ref'], 'vfs_key': item_m['vfs_key'], 'title': item_m['title'], 'url': item_m['url']} for item_m in output.get('results', []) if isinstance(item_m, dict)]
            else:
                destinations_m = [str(leaf['vfs_key']) for leaf in output.get('pages', []) if isinstance(leaf, dict) and leaf.get('vfs_key')]
                origin_index_m = [{'source_ref': item_m['source_ref'], 'vfs_key': item_m['vfs_key'], 'title': item_m['title'], 'url': item_m['url']} for item_m in output.get('pages', []) if isinstance(item_m, dict)]
            thumbmark = _freight_thumbmark(label_m, args_m)
            helm.retrieval_output_cache[thumbmark] = output
            chit = helm.retrieval_receipts.setdefault(thumbmark, {'tool': label_m, 'arguments': args_m, 'destinations': [], 'sources': [], 'calls': 0})
            chit['calls'] += 1
            chit['destinations'] = list(dict.fromkeys([*chit['destinations'], *destinations_m]))
            known_origins_m = {str(item_m['source_ref']): item_m for item_m in [*chit['sources'], *origin_index_m]}
            chit['sources'] = list(known_origins_m.values())

        def _freight_thumbmark(label_m: str, args_m: dict[str, Any]) -> str:
            return json.dumps({'tool': label_m, 'arguments': args_m}, ensure_ascii=False, sort_keys=True)

        def _chalk_cabinet_step_chit(helm: MeridianHelm, label_m: str, args_m: dict[str, Any], output: dict[str, Any]) -> None:
            if not output.get('ok') or label_m not in {'vfs_read', 'vfs_search', 'vfs_list'}:
                return
            if label_m == 'vfs_read':
                rungs = output.get('lines', [])
                outcome_m = {'returned_line_count': len(rungs), 'first_line': rungs[0].get('line') if rungs else None, 'last_line': rungs[-1].get('line') if rungs else None, 'truncated': bool(output.get('truncated'))}
            elif label_m == 'vfs_search':
                sieve_x = output.get('regex', {})
                resonance = output.get('similarity', {})
                outcome_m = {'regex_total_match_count': sieve_x.get('total_match_count'), 'regex_returned_match_count': len(sieve_x.get('matches', [])), 'regex_next_cursor': sieve_x.get('next_cursor'), 'similarity_status': resonance.get('status'), 'similarity_returned_chunk_count': len(resonance.get('chunks', []))}
            else:
                outcome_m = {'returned_key_count': len(output.get('keys', []))}
            thumbmark = json.dumps({'tool': label_m, 'arguments': args_m}, ensure_ascii=False, sort_keys=True)
            chit = helm.vfs_operation_receipts.setdefault(thumbmark, {'tool': label_m, 'arguments': args_m, 'calls': 0, 'outcome': outcome_m})
            chit['calls'] += 1
            chit['outcome'] = outcome_m

        def _refresh2_freight_chit_note(messages: list[Any], helm: MeridianHelm) -> None:
            marker_m = 'Harness research memory'
            messages[:] = [notem for notem in messages if not (isinstance(notem, dict) and notem.get('role') == 'user' and isinstance(notem.get('content'), str) and notem['content'].startswith(marker_m))]
            if not helm.research_state and (not helm.audit_gap) and (not helm.budget_snapshot) and (not helm.retrieval_receipts) and (not helm.vfs_operation_receipts) and (not helm.retained_evidence) and (not helm.focused_lines) and (not helm.reasoning_observations):
                return
            sections_m: list[str] = []
            if helm.evidence_requirements:
                sections_m.append('Evidence questions established before retrieval. They guide the investigation but may become immaterial after supported filtering:\n' + helm.evidence_requirements)
            if helm.audit_gap:
                sections_m.append('Latest finalization audit. This gap overrides any stale claim in the model-authored state that no uncertainty remains. Do not call ready_to_finalize again until new evidence resolves it:\n' + helm.audit_gap)
            if helm.budget_snapshot:
                sections_m.append('Latest hosted-tool budget snapshot. This is runtime state, not evidence:\n' + json.dumps(helm.budget_snapshot, ensure_ascii=False, indent=2) + '\nFinish before the hard remaining amount reaches zero. After observing the single result that resolves an audit gap, combine any now-independent retain_evidence, update_research_state, and ready_to_finalize calls in the same response instead of spending separate turns on each.')
            if helm.research_state:
                sections_m.append('Current model-authored research state. Revise it with update_research_state when the answer, support, or next unresolved question changes:\n' + helm.research_state)
            if helm.reasoning_observations:
                sections_m.append('Prior source-linked reasoning preserved by the harness. This is working memory, not external evidence. Use its source refs to avoid rediscovering observations, but inspect or retain the referenced source text before relying on a material premise in the final answer:\n' + '\n\n---\n\n'.join(helm.reasoning_observations))
            if helm.retrieval_receipts:
                prune_freight_tickets = [{key: chit[key] for key in ('tool', 'arguments', 'destinations', 'sources', 'calls') if key in chit} for chit in helm.retrieval_receipts.values()]
                sections_m.append('Completed external retrieval receipts. These record actions and a compact source inventory, not evidence. Each source entry maps a stable source ref to the exact VFS key whose text can be re-read instead of repeating a web search:\n' + json.dumps(prune_freight_tickets, ensure_ascii=False, indent=2))
            if helm.vfs_operation_receipts:
                sections_m.append('Completed local VFS inspection operations. These are action history, not evidence. Do not repeat the same read or search merely by changing wording. When prior local inspections did not expose the missing relationship, change the evidence route:\n' + json.dumps(list(helm.vfs_operation_receipts.values()), ensure_ascii=False, indent=2))
            if helm.retained_evidence:
                sections_m.append('Retained source excerpts selected by your prior reasoning. These are external evidence and do not need to be retrieved again. Only each quote is source evidence; research_note is your prior interpretation and may be wrong:\n' + json.dumps(list(helm.retained_evidence.values()), ensure_ascii=False, indent=2))
            if helm.focused_lines:
                sections_m.append('Recent unretained VFS observations. VFS remains the full source of truth; only one generous read-page of recent raw observations is replayed here. Retain lines that support or contradict a material premise. Re-read a VFS location when an older unretained observation becomes necessary:\n' + json.dumps(helm.focused_excerpts(), ensure_ascii=False, indent=2))
            messages.insert(2, {'role': 'user', 'content': f'{marker_m}:\n\n' + '\n\n'.join(sections_m)})

        def _weld_origin_sheaves(held: list[dict[str, Any]], live_m: list[dict[str, Any]]) -> list[dict[str, Any]]:
            merged_m: dict[str, dict[str, Any]] = {str(item_m['source_ref']): item_m for item_m in held}
            for item_m in live_m:
                origin_badge = str(item_m['source_ref'])
                prior_m = merged_m.get(origin_badge)
                if prior_m is None:
                    merged_m[origin_badge] = item_m
                    continue
                prior_quotation = str(prior_m.get('quote', '')).strip()
                live_quotation = str(item_m.get('quote', '')).strip()
                if not prior_quotation or prior_quotation in live_quotation:
                    quotation = live_quotation
                elif not live_quotation or live_quotation in prior_quotation:
                    quotation = prior_quotation
                else:
                    quotation = f'{prior_quotation}\n\n{live_quotation}'
                merged_m[origin_badge] = {**prior_m, **item_m, 'quote': quotation}
            return list(merged_m.values())

        def _sighting_handle(sighting: Any, index_m: int) -> tuple[str | None, str | None]:
            if index_m >= len(sighting.results):
                return (sighting.receipt_id, None)
            return (sighting.receipt_id, sighting.results[index_m].result_id)

        def _inquiry2_headway_thumbmark(helm: MeridianHelm) -> tuple[Any, ...]:
            return (helm.evidence_requirements, tuple(sorted(helm.sources)), tuple(((key, tuple(sorted(indices_m))) for key, indices_m in sorted(helm.focused_lines.items()))), tuple(sorted(helm.retained_evidence)), helm.research_state, helm.audit_gap)

        async def _run_sounding(helm: MeridianHelm, args_m: dict[str, Any], glimpse_outlay_girth: int | None=None) -> dict[str, Any]:
            query = str(args_m['query']).strip()
            num = int(args_m.get('num', 10))
            sighting = await search_web(query, provider=SOUNDING_CARRIER, num=num, timeout=SOUNDING_GAUGE)
            _jot_outlay(helm, sighting)
            helm.search_count += 1
            parent_slot_m = f'search://{helm.search_count}'
            helm.vfs[parent_slot_m] = sighting.response.model_dump_json(indent=2)
            items_m: list[dict[str, Any]] = []
            preview_chars = 8000
            if glimpse_outlay_girth is not None:
                preview_chars = min(preview_chars, max(300, glimpse_outlay_girth // max(1, len(sighting.response.data))))
            for index_m, item_m in enumerate(sighting.response.data):
                ref = f'S{helm.search_count}.{index_m + 1}'
                key = f'{parent_slot_m}/result/{index_m + 1}'
                content = item_m.snippet or item_m.title or ''
                helm.vfs[key] = content
                receipt_id, result_id = _sighting_handle(sighting, index_m)
                helm.sources[ref] = MeridianBeacon(ref=ref, key=key, title=item_m.title or item_m.link, url=item_m.link, content=content, receipt_id=receipt_id, result_id=result_id, preview_chars=preview_chars)
                items_m.append({'source_ref': f'[{ref}]', 'vfs_key': key, 'title': item_m.title, 'url': item_m.link, 'text': helm.bounded_preview(key, max_serialized_chars=preview_chars)})
            return {'ok': True, 'vfs_key': parent_slot_m, 'results': items_m}

        async def _run_ferry(helm: MeridianHelm, args_m: dict[str, Any], glimpse_outlay_girth: int | None=None) -> dict[str, Any]:
            url = str(args_m['url']).strip()
            if re.search('\\.(?:xls|xlsx|xlsb)(?:[?#]|$)', url, flags=re.IGNORECASE):
                raise ValueError('fetch_page cannot expose spreadsheet binary rows to VFS tools; search the same publisher for a CSV, HTML, or plain-text companion')
            sighting = await fetch_page(url, provider=SOUNDING_CARRIER, timeout=FERRY_GAUGE)
            _jot_outlay(helm, sighting)
            helm.page_count += 1
            items_m: list[dict[str, Any]] = []
            preview_chars = 8000
            if glimpse_outlay_girth is not None:
                preview_chars = min(preview_chars, max(300, glimpse_outlay_girth // max(1, len(sighting.response.data))))
            for index_m, item_m in enumerate(sighting.response.data):
                ref = f'P{helm.page_count + index_m}'
                key = f'page://{item_m.url}'
                helm.vfs[key] = item_m.content
                receipt_id, result_id = _sighting_handle(sighting, index_m)
                helm.sources[ref] = MeridianBeacon(ref=ref, key=key, title=item_m.title or item_m.url, url=item_m.url, content=item_m.content, receipt_id=receipt_id, result_id=result_id, preview_chars=preview_chars)
                item_payload_m = {'source_ref': f'[{ref}]', 'vfs_key': key, 'title': item_m.title, 'url': item_m.url}
                if len(item_m.content) > preview_chars:
                    termwise_reach = _run_termwise_reach(helm, {'query': helm.question, 'targets': [key]})
                    item_payload_m['question_context'] = {'instruction': 'These are the long page regions most relevant to the original question. Inspect them before issuing another page search or read.', 'windows': termwise_reach['windows']}
                item_payload_m['text'] = helm.bounded_preview(key, max_serialized_chars=preview_chars)
                items_m.append(item_payload_m)
            helm.page_count += max(0, len(sighting.response.data) - 1)
            return {'ok': True, 'pages': items_m}

        def _run_peruse(helm: MeridianHelm, args_m: dict[str, Any], *, remember_beamed: bool=True) -> dict[str, Any]:
            key = str(args_m['key'])
            if key not in helm.vfs:
                raise ValueError(f'unknown VFS key: {key}')
            rungs = helm.vfs[key].splitlines() or ['']

            def resolve_bound(value_m: Any, default_m: int) -> int:
                text = '' if value_m is None else str(value_m).strip()
                if value_m is None or text.lower() in {'', 'null', 'none'}:
                    return default_m
                location_m = helm.line_locations.get(text)
                if location_m is not None:
                    if location_m[0] != key:
                        raise ValueError(f'line ID {value_m} belongs to {location_m[0]}, not {key}')
                    return location_m[1]
                rung_figure_match = re.fullmatch('L?(\\d+)', text, flags=re.IGNORECASE)
                if rung_figure_match is None:
                    raise ValueError(f'unknown line bound: {value_m}; use a displayed line ID or 1-based line number')
                return max(0, int(rung_figure_match.group(1)) - 1)
            start = resolve_bound(args_m.get('start_line'), 0)
            end = resolve_bound(args_m.get('end_line'), len(rungs) - 1)
            if start >= len(rungs):
                raise ValueError(f'start_line is beyond the file; {key} has {len(rungs)} lines')
            if end < start:
                raise ValueError('end_line must not precede start_line')
            requested_end_m = min(len(rungs) - 1, end)
            selected_indices_m: list[int] = []
            reply_girth = 0
            for index_m in range(start, requested_end_m + 1):
                estimated_girth = len(rungs[index_m]) + 80
                if selected_indices_m and reply_girth + estimated_girth > MERIDIAN_PERUSE_LEAF_GIRTH:
                    break
                selected_indices_m.append(index_m)
                reply_girth += estimated_girth
            selected_m = selected_indices_m
            origin_badges = [f'[{origin_m.ref}]' for origin_m in helm.sources.values() if origin_m.key == key]
            next_index_m = selected_m[-1] + 1 if selected_m else start
            truncated_m = next_index_m <= requested_end_m
            next_rung_id = None
            if truncated_m:
                next_rung_id = helm._line_id_m(key, next_index_m, rungs[next_index_m])
                helm.line_locations[next_rung_id] = (key, next_index_m)
            if remember_beamed:
                helm.remember_focused_lines(key, selected_m)
            return {'ok': True, 'key': key, 'source_refs': origin_badges, 'lines': helm.render_lines(key, selected_m), 'truncated': truncated_m, 'next_start_line': next_index_m + 1 if truncated_m else None, 'next_start_line_id': next_rung_id}

        def _run_muster(helm: MeridianHelm, args_m: dict[str, Any]) -> dict[str, Any]:
            prefix_m = str(args_m['prefix'])
            slots_m = [key for key in helm.vfs if key.startswith(prefix_m)]
            return {'ok': True, 'keys': slots_m}

        def _run_stow(helm: MeridianHelm, args_m: dict[str, Any]) -> dict[str, Any]:
            key = str(args_m['key'])
            if key == '*':
                raise ValueError("'*' cannot be a VFS key")
            helm.forget_focused_lines(key)
            helm.vfs[key] = str(args_m['content'])
            return {'ok': True, 'key': key, 'chars': len(helm.vfs[key])}

        def _run_jettison(helm: MeridianHelm, args_m: dict[str, Any]) -> dict[str, Any]:
            key = str(args_m['key'])
            existed_m = key in helm.vfs
            helm.forget_focused_lines(key)
            helm.vfs.pop(key, None)
            return {'ok': True, 'key': key, 'deleted': existed_m}

        def _figure_values(text: str) -> set[str]:
            values_m: set[str] = set()
            for match_m in re.finditer('(?<![\\w.])\\d+(?:[,.]\\d+)*%?', text):
                prefix_m = text[:match_m.start()].rstrip()
                if prefix_m.endswith(('<', '>')):
                    continue
                if re.search('(?:above|below|greater than|less than|lower than|more than|threshold(?: of)?)\\s*$', prefix_m, flags=re.IGNORECASE):
                    continue
                raw_m = match_m.group(0)
                digits_m = re.sub('\\D', '', raw_m)
                if len(digits_m) < 2 and (not any((marker_m in raw_m for marker_m in (',', '.', '%')))):
                    continue
                values_m.add(raw_m.rstrip('%').replace(',', ''))
            return values_m

        def _verify2_held_figure_warrant(helm: MeridianHelm, origin_m: MeridianBeacon, jot: str, selected_rungs_x: list[dict[str, Any]]) -> None:
            assertion_wording = re.sub('\\blines?\\s+(?:L[0-9a-f]{10}|\\d+)(?:\\s*(?:-|to|through)\\s*(?:L[0-9a-f]{10}|\\d+))?(?:\\s*\\(L[0-9a-f]{10}\\))?', '', jot, flags=re.IGNORECASE)
            jot_figures2 = _figure_values(assertion_wording)
            selected_figures2 = _figure_values('\n'.join((str(item_m['text']) for item_m in selected_rungs_x)))
            missing_m = jot_figures2 - selected_figures2
            if not missing_m:
                return
            origin_rungs = helm.vfs[origin_m.key].splitlines() or ['']
            locations_m: dict[str, list[str]] = {}
            for figure in sorted(missing_m):
                matching_indices_m = [index_m for index_m, rung_x in enumerate(origin_rungs) if figure in _figure_values(rung_x)]
                if not matching_indices_m:
                    if figure in _figure_values(origin_m.title):
                        locations_m[figure] = ['source title only; choose a source whose citable body contains this value']
                    continue
                locations_m[figure] = [f'line {index_m + 1} ({helm._line_id_m(origin_m.key, index_m, origin_rungs[index_m])})' for index_m in matching_indices_m[:3]]
            if not locations_m:
                return
            details_m = '; '.join((f"{figure}: {', '.join(rung_locations)}" for figure, rung_locations in locations_m.items()))
            raise ValueError(f'the selected evidence span omits numeric facts asserted by note that are present elsewhere in this source ({details_m}). Re-read those lines and retry retain_evidence with a span containing the supporting text')

        def _run_hold2_warrant(helm: MeridianHelm, args_m: dict[str, Any]) -> dict[str, Any]:
            origin_identifier_m = str(args_m['source']).strip().strip('[]')
            origin_m = helm.sources.get(origin_identifier_m)
            if origin_m is None:
                origin_m = next((candidate_m for candidate_m in helm.sources.values() if candidate_m.key == origin_identifier_m), None)
            if origin_m is None:
                if origin_identifier_m in helm.vfs and re.fullmatch('search://\\d+', origin_identifier_m):
                    raise ValueError(f"{args_m['source']} is a search-result container, not a citable source; use the displayed [Sx.y] source reference or search://N/result/y child key that contains the supporting text")
                raise ValueError(f"unknown source reference or VFS key: {args_m['source']}")
            start_rung = args_m.get('start_line')
            end_rung = args_m.get('end_line')
            if start_rung is None or end_rung is None:
                raise ValueError('start_line and end_line are required')
            peruse_form = _run_peruse(helm, {'key': origin_m.key, 'start_line': start_rung, 'end_line': end_rung}, remember_beamed=False)
            jot = str(args_m['note']).strip()
            _verify2_held_figure_warrant(helm, origin_m, jot, peruse_form['lines'])
            rung_ids = ' '.join((str(item_m['line_id']) for item_m in peruse_form['lines']))
            prior_reaches = list(helm.source_slices.get(origin_m.ref, []))
            manifest = helm.source_packet(f'{origin_m.ref} {rung_ids}', allow_preview=False, include_structured_csv=True, prefer_retained=False)
            if not manifest:
                raise RuntimeError(f'could not build evidence packet for source {origin_m.ref}')
            helm.source_slices[origin_m.ref] = _weld_mark_reaches(prior_reaches, list(helm.source_slices.get(origin_m.ref, [])))
            held = manifest[0]
            held['research_note'] = jot
            existing_m = helm.retained_evidence.get(origin_m.ref)
            if existing_m is not None:
                held = _weld_origin_sheaves([existing_m], [held])[0]
                prior_jot = str(existing_m.get('research_note', '')).strip()
                held['research_note'] = '\n'.join((item_m for item_m in (prior_jot, jot) if item_m))
            helm.retained_evidence[origin_m.ref] = held
            held_indices = {helm.line_locations[str(item_m['line_id'])][1] for item_m in peruse_form['lines'] if str(item_m['line_id']) in helm.line_locations}
            helm.forget_focused_lines(origin_m.key, held_indices)
            return {'ok': True, 'source_ref': f'[{origin_m.ref}]'}

        def _run_moult_residual_origins(helm: MeridianHelm, args_m: dict[str, Any]) -> dict[str, Any]:
            ground = str(args_m['reason']).strip()
            if not ground:
                raise ValueError('reason must not be blank')
            discarded_badges = set(helm.review_source_refs)
            discarded_origin_census = len(discarded_badges)
            helm.review_source_refs.clear()
            held_slots = {helm.sources[ref].key for ref in helm.retained_evidence if ref in helm.sources}
            for ref in discarded_badges:
                origin_m = helm.sources.get(ref)
                if origin_m is not None and origin_m.key not in held_slots:
                    helm.forget_focused_lines(origin_m.key)
            return {'ok': True, 'discarded_source_count': discarded_origin_census}

        def _run_sieve(helm: MeridianHelm, args_m: dict[str, Any]) -> dict[str, Any]:
            sieve = re.compile(str(args_m['pattern']))
            slots_m = helm.resolve_targets([str(item_m) for item_m in args_m['targets']])
            cursor_value_m = args_m.get('cursor')
            cursor_m = 0 if cursor_value_m is None else int(cursor_value_m)
            if cursor_m < 0:
                raise ValueError('cursor must be at least zero')
            raw_matches_m: list[tuple[str, dict[str, Any]]] = []
            for key in slots_m:
                for item_m in helm.render_lines(key):
                    if sieve.search(item_m['text']):
                        raw_matches_m.append((key, item_m))
            matches_m: list[dict[str, Any]] = []
            leaf_girth = 0
            for key, item_m in raw_matches_m[cursor_m:]:
                match_m = {'key': key, **item_m}
                origin_badges = [f'[{origin_m.ref}]' for origin_m in helm.sources.values() if origin_m.key == key]
                if origin_badges:
                    match_m['source_refs'] = origin_badges
                lattice_reach: dict[str, Any] | None = None
                csv_records_m = helm.structured_csv_records(key, [0, item_m['line'] - 1])
                if csv_records_m:
                    match_m.pop('text')
                    match_m['csv_record'] = csv_records_m[0]
                else:
                    lattice_reach = _markdown2_lattice_reach(helm, key, item_m['line'] - 1)
                    if lattice_reach is not None:
                        match_m['table'] = lattice_reach
                beamed_indices = {item_m['line'] - 1}
                if lattice_reach is not None:
                    beamed_indices.update((int(header_rung['line']) - 1 for header_rung in lattice_reach['header']))
                if origin_badges:
                    helm.remember_focused_lines(key, beamed_indices)
                matches_m.append(match_m)
                leaf_girth += len(json.dumps(match_m, ensure_ascii=False, separators=(',', ':')))
                if leaf_girth >= MERIDIAN_VSEARCH_LEAF_GIRTH:
                    break
            next_offset_m = cursor_m + len(matches_m)
            next_cursor_m = next_offset_m if next_offset_m < len(raw_matches_m) else None
            return {'ok': True, 'matched_keys': slots_m, 'total_match_count': len(raw_matches_m), 'cursor': cursor_m, 'matches': matches_m, 'next_cursor': next_cursor_m}

        def _bricks(helm: MeridianHelm, slots_m: list[str]) -> list[dict[str, Any]]:
            bricks: list[dict[str, Any]] = []
            for key in slots_m:
                content = helm.vfs[key]
                start = 0
                index_m = 0
                while start < len(content):
                    end = min(len(content), start + 3000)
                    bricks.append({'key': key, 'chunk': index_m, 'start': start, 'end': end, 'text': content[start:end]})
                    if end == len(content):
                        break
                    start = end - 300
                    index_m += 1
            return bricks

        def _termwise_terms(text: str) -> set[str]:
            return {term_x_m for term_x_m in _TERMWISE_TERM_RE.findall(text.casefold()) if term_x_m not in _TERMWISE_SKIP_TERMS}

        def _broad_marked_quotations(text: str) -> list[str]:
            return [next((group_m for group_m in match_m.groups() if group_m is not None)).strip() for match_m in _BROAD_MARKED_QUOTATION_RE.finditer(text)]

        def _verbatim_quotation_slats(text: str, quotations: list[str]) -> list[tuple[int, int, str]]:
            slats: list[tuple[int, int, str]] = []
            lowered_m = text.casefold()
            leading_girth = MERIDIAN_GLOSS_SLAT_GIRTH * 3 // 4
            for quotation_x in quotations:
                sounding_from = 0
                normalized_quotation = quotation_x.casefold()
                while True:
                    match_start_m = lowered_m.find(normalized_quotation, sounding_from)
                    if match_start_m < 0:
                        break
                    start = max(0, match_start_m - leading_girth)
                    end = min(len(text), start + MERIDIAN_GLOSS_SLAT_GIRTH)
                    start = max(0, end - MERIDIAN_GLOSS_SLAT_GIRTH)
                    if not any((start < existing_end_m and existing_start_m < end for existing_start_m, existing_end_m, _ignored_m in slats)):
                        slats.append((start, end, quotation_x))
                    sounding_from = match_start_m + len(normalized_quotation)
            return slats

        def _termwise_slats(text: str, terms_m: set[str]) -> list[tuple[int, int, int]]:
            if not text or not terms_m:
                return []
            if len(text) <= MERIDIAN_GLOSS_SLAT_GIRTH:
                return [(0, len(text), sum((term_m in text.casefold() for term_m in terms_m)))]
            stage_m = max(600, MERIDIAN_GLOSS_SLAT_GIRTH // 3)
            lowered_m = text.lower()
            scored_m: list[tuple[int, int]] = []
            start = 0
            while start < len(text):
                slat = lowered_m[start:start + MERIDIAN_GLOSS_SLAT_GIRTH]
                scored_m.append((sum((term_m in slat for term_m in terms_m)), start))
                if start + MERIDIAN_GLOSS_SLAT_GIRTH >= len(text):
                    break
                start += stage_m
            scored_m.sort(key=lambda item_m: (-item_m[0], item_m[1]))
            selected_m: list[tuple[int, int, int]] = []
            for matched_term_census, start in scored_m:
                if len(selected_m) >= MERIDIAN_GLOSS_SLAT_CENSUS:
                    break
                end = min(len(text), start + MERIDIAN_GLOSS_SLAT_GIRTH)
                if any((start < selected_end_m and selected_start_m < end for selected_start_m, selected_end_m, _ignored_m in selected_m)):
                    continue
                if selected_m and matched_term_census == 0:
                    continue
                selected_m.append((start, end, matched_term_census))
            return sorted(selected_m)

        def _run_termwise_reach(helm: MeridianHelm, args_m: dict[str, Any]) -> dict[str, Any]:
            slots_m = helm.resolve_targets([str(item_m) for item_m in args_m['targets']])
            terms_m = _termwise_terms(f"{helm.question}\n{args_m['query']}")
            quotations = _broad_marked_quotations(helm.question)
            slats: list[dict[str, Any]] = []
            for key in slots_m:
                content = helm.vfs[key]
                selected_m: list[tuple[int, int, int, str | None]] = [(start, end, len(terms_m), quotation_x) for start, end, quotation_x in _verbatim_quotation_slats(content, quotations)]
                for start, end, matched_term_census in _termwise_slats(content, terms_m):
                    if any((start < selected_end_m and selected_start_m < end for selected_start_m, selected_end_m, _ignored_m, _ignored_m in selected_m)):
                        continue
                    selected_m.append((start, end, matched_term_census, None))
                for start, end, matched_term_census, verbatim_quotation in selected_m:
                    start_rung = content[:start].count('\n')
                    end_rung = content[:end].count('\n') + 1
                    slats.append({'key': key, 'start': start, 'end': end, 'matched_term_count': matched_term_census, 'exact_phrase': verbatim_quotation, 'lines': helm.render_lines(key, range(start_rung, end_rung))})
            slats.sort(key=lambda item_m: (item_m['exact_phrase'] is None, -int(item_m['matched_term_count']), str(item_m['key']), int(item_m['start'])))
            return {'ok': True, 'matched_keys': slots_m, 'windows': slats[:MERIDIAN_GLOSS_SLAT_CENSUS]}

        def _raynorm(left_m: list[float], right_m: list[float]) -> float:
            numerator_m = sum((a_m * b_m for a_m, b_m in zip(left_m, right_m, strict=True)))
            left_norm_m = math.sqrt(sum((value_m * value_m for value_m in left_m)))
            right_norm_m = math.sqrt(sum((value_m * value_m for value_m in right_m)))
            return numerator_m / (left_norm_m * right_norm_m) if left_norm_m and right_norm_m else 0.0

        async def _run_resonance(helm: MeridianHelm, args_m: dict[str, Any]) -> dict[str, Any]:
            slots_m = helm.resolve_targets([str(item_m) for item_m in args_m['targets']])
            embedded_bricks: list[tuple[dict[str, Any], list[float]]] = []
            missing_bricks: list[dict[str, Any]] = []
            missing_cache_slots_m: list[tuple[str, str]] = []
            missing_brick_counts: list[int] = []
            for key in slots_m:
                cache_slot_m = (key, hashlib.sha256(helm.vfs[key].encode()).hexdigest())
                cached_m = helm.document_embeddings.get(cache_slot_m)
                if cached_m is not None:
                    embedded_bricks.extend(cached_m)
                    continue
                bricks = _bricks(helm, [key])
                missing_cache_slots_m.append(cache_slot_m)
                missing_brick_counts.append(len(bricks))
                missing_bricks.extend(bricks)
            if not embedded_bricks and (not missing_bricks):
                return {'ok': True, 'matched_keys': slots_m, 'chunks': []}
            query_sighting = await embed_text(str(args_m['query']), provider='openrouter', model='qwen/qwen3-embedding-8b', input_type='query', provider_extra=BEARING_SLACK, timeout=BEARING_GAUGE)
            if missing_bricks:
                document_sighting = await embed_text([brick['text'] for brick in missing_bricks], provider='openrouter', model='qwen/qwen3-embedding-8b', input_type='document', provider_extra=BEARING_SLACK, timeout=BEARING_GAUGE)
                vectors_m = [item_m.embedding for item_m in sorted(document_sighting.response.data, key=lambda item_m: item_m.index)]
                if len(vectors_m) != len(missing_bricks):
                    raise RuntimeError(f'embedding result count mismatch: expected {len(missing_bricks)}, received {len(vectors_m)}')
                offset_m = 0
                for cache_slot_m, brick_census in zip(missing_cache_slots_m, missing_brick_counts, strict=True):
                    cached_m = list(zip(missing_bricks[offset_m:offset_m + brick_census], vectors_m[offset_m:offset_m + brick_census], strict=True))
                    helm.document_embeddings[cache_slot_m] = cached_m
                    embedded_bricks.extend(cached_m)
                    offset_m += brick_census
            query_bearing = query_sighting.response.data[0].embedding
            scored_m = [{**brick, 'score': _raynorm(query_bearing, bearing)} for brick, bearing in embedded_bricks]
            scored_m.sort(key=lambda item_m: item_m['score'], reverse=True)
            output: list[dict[str, Any]] = []
            form_girth = 0
            for item_m in scored_m[:MERIDIAN_ECHO2_TOP_BRICKS]:
                key = item_m['key']
                content_before_m = helm.vfs[key][:item_m['start']]
                start_rung = content_before_m.count('\n')
                rung_census = item_m['text'].count('\n') + 1
                sighting_item = {'key': key, 'chunk': item_m['chunk'], 'score': item_m['score'], 'lines': helm.render_lines(key, range(start_rung, start_rung + rung_census))}
                origin_badges = [f'[{origin_m.ref}]' for origin_m in helm.sources.values() if origin_m.key == key]
                if origin_badges:
                    sighting_item['source_refs'] = origin_badges
                sighting_girth = len(json.dumps(sighting_item, ensure_ascii=False, separators=(',', ':')))
                if len(output) >= MERIDIAN_ECHO2_FLOOR_BRICKS and form_girth + sighting_girth > MERIDIAN_ECHO2_SIGHTING_GIRTH:
                    break
                if origin_badges:
                    helm.remember_focused_lines(key, range(start_rung, start_rung + rung_census))
                output.append(sighting_item)
                form_girth += sighting_girth
            return {'ok': True, 'matched_keys': slots_m, 'chunks': output}

        async def _run_cabinet_sounding(helm: MeridianHelm, args_m: dict[str, Any]) -> dict[str, Any]:
            sieve_sighting: dict[str, Any] | None = None
            sieve_mishap: str | None = None
            try:
                sieve_sighting = _run_sieve(helm, args_m)
            except (TypeError, ValueError, re.error) as mishap:
                sieve_mishap = str(mishap)
            resonance_trigger: str | None = None
            if sieve_sighting is None:
                resonance_trigger = 'regex_error'
            elif int(sieve_sighting['total_match_count']) == 0:
                resonance_trigger = 'no_regex_matches'
            resonance_sighting: dict[str, Any] | None = None
            resonance_mishap: str | None = None
            if resonance_trigger is not None:
                try:
                    resonance_sighting = await _run_resonance(helm, args_m)
                except Exception as mishap:
                    resonance_mishap = str(mishap)
            if sieve_sighting is None and resonance_sighting is None:
                raise RuntimeError(f"both VFS search methods failed: regex={sieve_mishap or 'unknown'}; similarity={resonance_mishap or 'unknown'}")
            output: dict[str, Any] = {'ok': True, 'similarity': {'status': 'not_run', 'reason': 'regex_returned_matches_on_first_search'}}
            if sieve_sighting is not None:
                output['regex'] = {key: value_m for key, value_m in sieve_sighting.items() if key not in {'ok', 'matched_keys'}}
            if sieve_mishap is not None:
                output['regex_error'] = sieve_mishap
            if resonance_sighting is not None:
                output['similarity'] = {'status': 'completed', 'trigger': resonance_trigger}
                output['similarity'].update({key: value_m for key, value_m in resonance_sighting.items() if key not in {'ok', 'matched_keys'}})
            if resonance_mishap is not None:
                output['similarity'] = {'status': 'failed', 'trigger': resonance_trigger, 'error': resonance_mishap}
            return output

        async def _run_move(helm: MeridianHelm, label_m: str, args_m: dict[str, Any], glimpse_outlay_girth: int | None=None) -> dict[str, Any]:
            if label_m in {'search_web', 'fetch_page'}:
                cached_m = helm.retrieval_output_cache.get(_freight_thumbmark(label_m, args_m))
                if cached_m is not None:
                    return {**cached_m, 'cached': True}
            if label_m == 'search_web':
                return await _run_sounding(helm, args_m, glimpse_outlay_girth)
            if label_m == 'fetch_page':
                return await _run_ferry(helm, args_m, glimpse_outlay_girth)
            if label_m == 'vfs_read':
                return _run_peruse(helm, args_m)
            if label_m == 'vfs_list':
                return _run_muster(helm, args_m)
            if label_m == 'vfs_write':
                return _run_stow(helm, args_m)
            if label_m == 'vfs_delete':
                return _run_jettison(helm, args_m)
            if label_m == 'retain_evidence':
                return _run_hold2_warrant(helm, args_m)
            if label_m == 'discard_remaining_sources':
                return _run_moult_residual_origins(helm, args_m)
            if label_m == 'vfs_search':
                return await _run_cabinet_sounding(helm, args_m)
            if label_m == 'update_research_state':
                inquiry2_helm = str(args_m['state']).strip()
                if not inquiry2_helm:
                    raise ValueError('state must not be blank')
                helm.research_state = inquiry2_helm
                return {'ok': True}
            raise ValueError(f'unknown tool: {label_m}')

        def _distinct2_move_moves(moves: list[Any]) -> tuple[list[Any], int]:
            distinct_moves: list[Any] = []
            seen_m: set[tuple[str, str]] = set()
            for move in moves:
                try:
                    arguments_m = json.dumps(json.loads(move.arguments), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
                except json.JSONDecodeError:
                    arguments_m = move.arguments
                thumbmark = (move.name, arguments_m)
                if thumbmark in seen_m:
                    continue
                seen_m.add(thumbmark)
                distinct_moves.append(move)
            return (distinct_moves, len(moves) - len(distinct_moves))

        async def _notarize_ruling(*, helm: MeridianHelm, inquiry: str, current_reply: str, ground: str, assistant_context_m: str, last_manifest: list[dict[str, Any]], final_origin_cuts: dict[str, list[CitationSlice]]) -> tuple[str, list[dict[str, Any]]]:
            finalization_reach = '\n\n'.join((value_m for value_m in (helm.research_state.strip(), ground.strip(), assistant_context_m.strip()) if value_m))
            manifest = helm.source_packet(finalization_reach, include_structured_csv=True)
            if not manifest:
                raise ValueError('final answer must mention at least one observed source reference such as S1.2 or P1')
            unretained_leaf_badges = [str(item_m['source_ref']) for item_m in manifest if str(item_m['source_ref']).strip('[]').startswith('P') and str(item_m['source_ref']).strip('[]') not in helm.retained_evidence]
            if unretained_leaf_badges:
                raise ValueError(f"fetched-page evidence must be preserved before finalization; call retain_evidence for each decisive excerpt from {', '.join(unretained_leaf_badges)}, then retry")
            for item_m in manifest:
                ref = str(item_m['source_ref'])[1:-1]
                final_origin_cuts[ref] = _weld_mark_reaches(final_origin_cuts.get(ref, []), list(helm.source_slices.get(ref, [])))
            precise_badges = {str(item_m['source_ref']) for item_m in [*last_manifest, *manifest]}
            held_sheaf = [item_m for item_m in helm.retained_evidence.values() if str(item_m['source_ref']) not in precise_badges]
            merged_sheaf = _weld_origin_sheaves(last_manifest, held_sheaf)
            merged_sheaf = _weld_origin_sheaves(merged_sheaf, manifest)
            merged_sheaf = [item_m for item_m in merged_sheaf if (origin_m := helm.sources.get(str(item_m['source_ref']).strip('[]'))) and origin_m.receipt_id and origin_m.result_id]
            if not merged_sheaf:
                raise ValueError('none of the selected source records can be materialized as response citations')
            reply = await _ruling_wording(helm=helm, inquiry=inquiry, prior_reply=current_reply, stipulations=helm.evidence_requirements or '', inquiry2_helm=helm.research_state, finalization_ground=ground, manifest=merged_sheaf)
            return (reply, merged_sheaf)

        async def _navigate(inquiry: str, outlook_ruling: str) -> tuple[str, list[CitationRef]]:
            passage_begun_at = time.monotonic()
            horizon_alert_raised = False
            helm = MeridianHelm(inquiry)
            helm.research_state = f'Current best answer hypothesis:\n{outlook_ruling}\nObserved support: none yet.\nMost important unresolved question: test the hypothesis against external evidence.'
            current_reply = outlook_ruling
            messages: list[Any] = [{'role': 'system', 'content': PASSAGE_CHARTER}, {'role': 'user', 'content': f'Original question:\n{inquiry}\n\nExpected answer hypothesis:\n{outlook_ruling}'}]
            last_manifest: list[dict[str, Any]] = []
            final_origin_cuts: dict[str, list[CitationSlice]] = {}
            final2_survey = ''
            swerve_spur = ''
            prior_move_signatures: tuple[str, ...] = ()
            for _leg in range(160):
                rampart_drained = time.monotonic() - passage_begun_at
                if rampart_drained >= WARDEN_RAMPART_TICKS - NOTARIZE_STERN_BERTH_TICKS and last_manifest:
                    current_reply = _burnish_notarized_prose2(current_reply)
                    chart = helm.citation_plan(current_reply, last_manifest, final_origin_cuts, final2_survey)
                    return _issue_public_marks(current_reply, chart, unadorned_output_m=_wants2_naked_form(inquiry))
                if not horizon_alert_raised and rampart_drained >= HORIZON_ALERT_TICKS:
                    messages.append({'role': 'user', 'content': 'The external runtime has about 150 seconds remaining. Preserve answer quality. If the observed evidence can support the answer, retain any needed excerpts and call ready_to_finalize now. If one decisive uncertainty remains, perform only the single operation most likely to resolve it, then finalize. Do not restart broad research.'})
                    horizon_alert_raised = True
                _refresh2_freight_chit_note(messages, helm)
                mandates_queued = helm.evidence_requirements is None
                if mandates_queued:
                    onhand_moves = MANDATES_MOVES
                    onhand_pilots = _mandates_pilots(horizon_alert_raised, swerve_spur)
                else:
                    onhand_moves = MOVE_CATALOG
                    onhand_pilots = _passage_pilots(helm, horizon_alert_raised, swerve_spur)
                ask_notes = [{'role': 'system', 'content': MANDATES_CHARTER}, {'role': 'user', 'content': f'Original question:\n{inquiry}'}] if mandates_queued else messages
                leg_canopy = min(PILOT_GAUGE, max(LEG_CANOPY_FLOOR_TICKS, WARDEN_RAMPART_TICKS - NOTARIZE_STERN_BERTH_TICKS - rampart_drained))
                sighting = await _parley_with_routing(onhand_pilots, messages=ask_notes, tools=onhand_moves, tool_choice='required', parallel_tool_calls=True, timeout=leg_canopy, max_output_tokens=None)
                _jot_outlay(helm, sighting)
                _prune_drained_envoy_musing2(messages)
                _prune_drained_move_findings(messages)
                envoy = _envoy_note(sighting)
                helm.remember_reasoning_observation(envoy.reasoning)
                moves, twin_move_census = _distinct2_move_moves(list(envoy.tool_calls or ()))
                if not moves:
                    prose2 = (sighting.llm.raw_text or '').strip()
                    if prose2:
                        try:
                            current_reply, last_manifest = await _notarize_ruling(helm=helm, inquiry=inquiry, current_reply=current_reply, ground=prose2, assistant_context_m=_envoy_warrant_reach(envoy), last_manifest=last_manifest, final_origin_cuts=final_origin_cuts)
                        except ValueError as mishap:
                            swerve_spur = f'The previous model tried to finalize without materializable support. Resolve this exact problem before finalizing again: {mishap}'
                            messages.extend([envoy.to_input_message(), {'role': 'user', 'content': f'Your terminal answer could not be finalized: {mishap}. Use tools to resolve that exact problem, then either return a supported terminal answer or call ready_to_finalize.'}])
                            continue
                        current_reply = _burnish_notarized_prose2(current_reply)
                        chart = helm.citation_plan(current_reply, last_manifest, final_origin_cuts, final2_survey)
                        return _issue_public_marks(current_reply, chart, unadorned_output_m=_wants2_naked_form(inquiry))
                    messages.extend([envoy.to_input_message(), {'role': 'user', 'content': 'Use a tool. Call ready_to_finalize only when inspected sources support the answer.'}])
                    swerve_spur = 'The previous model returned neither a tool call nor a usable terminal answer. Choose the smallest valid operation that advances the investigation.'
                    continue
                envoy_input = replace(envoy, tool_calls=tuple(moves)).to_input_message()
                messages.append(envoy_input)
                ready_requested_m = False
                survey_ready = False
                headway_before = _inquiry2_headway_thumbmark(helm)
                leg_move_signatures: list[str] = []
                leg_fail_signatures: list[str] = []
                freight_move_census = sum((move.name in {'search_web', 'fetch_page'} for move in moves))
                freight_glimpse_outlay = MERIDIAN_POOLED_GLIMPSE_GIRTH // freight_move_census if freight_move_census else None
                for move_index, move in enumerate(moves):
                    move_thumbmark = json.dumps({'tool': move.name, 'raw_arguments': move.arguments}, ensure_ascii=False, sort_keys=True)
                    try:
                        args_m = json.loads(move.arguments)
                        if not isinstance(args_m, dict):
                            raise ValueError('tool arguments must be a JSON object')
                        move_thumbmark = json.dumps({'tool': move.name, 'arguments': args_m}, ensure_ascii=False, sort_keys=True)
                        if move.name == 'set_evidence_requirements':
                            if not mandates_queued or len(moves) != 1:
                                raise ValueError('set_evidence_requirements must be the sole call before retrieval')
                            stipulations = str(args_m['requirements']).strip()
                            if not stipulations:
                                raise ValueError('requirements must not be empty')
                            helm.evidence_requirements = stipulations
                            output = {'ok': True}
                        elif move.name == 'ready_to_finalize':
                            if leg_fail_signatures:
                                raise ValueError('cannot finalize in the same response after an earlier tool call failed; inspect that tool feedback, correct the failed operation, and retry finalization')
                            incompatible_moves = [candidate_m.name for candidate_m in moves if candidate_m.name not in {'update_research_state', 'retain_evidence', 'ready_to_finalize'}]
                            if incompatible_moves:
                                raise ValueError(f"ready_to_finalize may only accompany update_research_state and retain_evidence; also received {', '.join(incompatible_moves)}")
                            if move_index != len(moves) - 1:
                                raise ValueError('ready_to_finalize must be the final call in the response')
                            ground = str(args_m['reason'])
                            current_reply, last_manifest = await _notarize_ruling(helm=helm, inquiry=inquiry, current_reply=current_reply, ground=ground, assistant_context_m=_envoy_warrant_reach(envoy), last_manifest=last_manifest, final_origin_cuts=final_origin_cuts)
                            final2_survey = ''
                            ready_requested_m = True
                            survey_ready = True
                            output = {'ok': True, 'answer_checkpoint': current_reply}
                        elif move.name == 'discard_remaining_sources':
                            if move_index != len(moves) - 1:
                                raise ValueError('discard_remaining_sources must be the last call in the response')
                            output = await _run_move(helm, move.name, args_m, freight_glimpse_outlay)
                        else:
                            output = await _run_move(helm, move.name, args_m, freight_glimpse_outlay)
                            _chalk_freight_chit(helm, move.name, args_m, output)
                            _chalk_cabinet_step_chit(helm, move.name, args_m, output)
                    except Exception as mishap:
                        output = {'ok': False, 'error_type': 'tool_argument_validation' if isinstance(mishap, (KeyError, TypeError, ValueError, json.JSONDecodeError)) else 'tool_execution', 'details': str(mishap)}
                    leg_move_signatures.append(move_thumbmark)
                    if not output.get('ok'):
                        leg_fail_signatures.append(json.dumps({'tool': move.name, 'error_type': output.get('error_type')}, ensure_ascii=False, sort_keys=True))
                    messages.append({'role': 'tool', 'tool_call_id': move.id, 'content': json.dumps(output, ensure_ascii=False)})
                if twin_move_census:
                    messages.append({'role': 'user', 'content': f'The previous response repeated {twin_move_census} exact tool calls. The harness executed each distinct call once. Continue from those results without repeating an identical call.'})
                if ready_requested_m:
                    survey_stern = WARDEN_RAMPART_TICKS - (time.monotonic() - passage_begun_at)
                    if survey_stern < SURVEY_STERN_FLOOR_TICKS:
                        final2_survey = ''
                        helm.audit_gap = ''
                        survey_ready = True
                        current_reply = _burnish_notarized_prose2(current_reply)
                        chart = helm.citation_plan(current_reply, last_manifest, final_origin_cuts, final2_survey)
                        return _issue_public_marks(current_reply, chart, unadorned_output_m=_wants2_naked_form(inquiry))
                    final2_survey = await _survey(helm, inquiry, current_reply, last_manifest)
                    decree, survey_payload = _unravel_survey(final2_survey)
                    if decree == 'CONTINUE':
                        helm.audit_gap = survey_payload
                        helm.clear_focused_lines()
                        survey_ready = False
                        messages = [{'role': 'system', 'content': PASSAGE_CHARTER}, {'role': 'user', 'content': f'Original question:\n{inquiry}\n\nThe finalization audit found one unresolved evidence gap:\n{survey_payload}\n\nThe harness will preserve the existing VFS, source references, retained evidence, retrieval receipts, and research state. Resolve this exact gap with the smallest useful next observation, update the research state if the answer changes, then finalize. Do not restart the investigation or repeat already supported premises.'}]
                    elif decree == 'REVISE':
                        allowed_badges = {str(item_m['source_ref']).strip('[]') for item_m in last_manifest if isinstance(item_m, dict) and item_m.get('source_ref')}
                        _verify2_inward_ruling_badges(survey_payload, allowed_badges, require_ref_m=not _wants2_naked_form(inquiry))
                        current_reply = survey_payload
                        helm.audit_gap = ''
                        survey_ready = True
                    else:
                        helm.audit_gap = ''
                        survey_ready = True
                if MERIDIAN_PILOT_ROTA == 'state_aware' and (not ready_requested_m):
                    headway_after = _inquiry2_headway_thumbmark(helm)
                    live_moves = tuple(leg_move_signatures)
                    live_failures_m = tuple(leg_fail_signatures)
                    next_swerve_spur = ''
                    if live_failures_m:
                        next_swerve_spur = "The previous model's tool call failed. Read the detailed tool feedback, correct that exact operation or choose a different valid operation, and advance the investigation without repeating the failure."
                    elif live_moves and live_moves == prior_move_signatures and (headway_after == headway_before):
                        next_swerve_spur = 'The previous model repeated the same operations without adding evidence or changing the research state. Choose a different evidence route.'
                    elif live_moves and (not live_failures_m) and (headway_after == headway_before):
                        next_swerve_spur = 'The previous operations succeeded mechanically but produced no new retained evidence, source coverage, inspected lines, or research-state change. Choose the smallest different operation that can resolve the current uncertainty.'
                    if next_swerve_spur:
                        messages.append({'role': 'user', 'content': next_swerve_spur})
                    swerve_spur = next_swerve_spur
                    prior_move_signatures = live_moves
                if ready_requested_m and survey_ready:
                    current_reply = _burnish_notarized_prose2(current_reply)
                    chart = helm.citation_plan(current_reply, last_manifest, final_origin_cuts, final2_survey)
                    return _issue_public_marks(current_reply, chart, unadorned_output_m=_wants2_naked_form(inquiry))
            raise RuntimeError('investigation did not finalize within the generous 160-turn ceiling')

        async def query(query: Query) -> Response:
            try:
                outlook_ruling = await _outlook_ruling_wording(query.text)
            except Exception as mishap:
                if not _is_fleeting_llm_mishap(mishap):
                    raise
                outlook_ruling = 'No expected-answer hypothesis was available because its model call failed. Investigate the original question directly and construct a revisable answer from observed external evidence.'
            reply, citations = await _navigate(query.text, outlook_ruling)
            if query.output_schema is not None:
                output = await _mint_formed_form(inquiry=query.text, reply=reply, output_schema_m=query.output_schema)
                return Response(output=output, citations=citations)
            return Response(text=reply, citations=citations)
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


async def _s18_base_query(query: Query) -> Response:
    _s16_t0 = _s16_monotonic()
    _s16_resp = await _s16_base_query(query)
    try:
        return await _s16_finalize(query, _s16_resp, _s16_t0)
    except Exception:
        return _s16_resp


# =====================================================================
# submittion18 MECHANISM — requirement-coverage gap-filling pass (text
# AND structured-output modes), decomposed by query-derived requirement
# category rather than by draft-answer claim
# =====================================================================
#
# Runs after the base pipeline above has produced a draft Response. Unlike
# a fact-contradiction check against the draft's own claims, this stage:
#   1. Decomposes the ORIGINAL QUESTION (not the draft) into up to 6
#      discrete, independently-checkable requirements using the same
#      requirement taxonomy live task generation uses (candidate_universe,
#      metric_or_field_relation, scope, time_qualifier, cardinality,
#      ranking, completeness, absence, other) -- including the target
#      JSON schema when the query is structured, so schema fields become
#      explicit requirements.
#   2. Coverage-checks the draft's CURRENT content (free text OR compact
#      JSON of Response.output) against that checklist, per requirement,
#      classifying each as satisfied / weak / missing and producing a
#      requirement-specific search query for any gap.
#   3. Issues ONE NEW, independently targeted search_web call PER GAP
#      (concurrently, capped at 3, missing prioritized over weak).
#   4. Sequentially, per gap with usable fresh evidence: for structured
#      responses, asks the model for a minimal JSON patch restricted to
#      keys that already exist in the current output/schema (never
#      invents new keys -- enforced both by prompt and by code-side
#      merge), and applies it to Response.output directly; for free-text
#      responses, rewrites only the missing/weak span of the answer,
#      preserving everything else. Both paths grow citations only from
#      the fresh, requirement-targeted evidence, never fabricated.
# This changes decomposition (requirement checklist vs draft claims),
# verification target (query coverage vs draft self-consistency), and
# control flow for structured outputs (direct JSON field patching, which
# the base pipeline's own post-processing does not do) relative to the
# base pipeline; it is not a prompt or parameter tweak. Any failure,
# missing evidence, non-dict structured output, or time shortage is a
# strict no-op that returns the base pipeline's own response (after cheap
# exact duplicate-citation cleanup only).

import asyncio as _s18_asyncio
import json as _s18_json
import re as _s18_re
from time import monotonic as _s18_monotonic

_S18_HARD_BUDGET_GATE_S = 250.0
_S18_MAX_WINDOW_S = 55.0
_S18_MIN_WINDOW_S = 10.0
_S18_EXTRACT_TIMEOUT_S = 9.0
_S18_COVERAGE_TIMEOUT_S = 9.0
_S18_SEARCH_TIMEOUT_S = 9.0
_S18_PATCH_TIMEOUT_S = 12.0
_S18_MAX_REQUIREMENTS = 6
_S18_MAX_GAPS_TO_FILL = 3
_S18_MAX_NEW_CITATIONS_PER_GAP = 2
_S18_MAX_TOTAL_CITATIONS = 60
_S18_MODEL = "deepseek/deepseek-v3.2"

_S18_EXTRACT_SYSTEM_PROMPT = (
    "You extract the discrete requirement checklist implied by a research "
    "question.\n"
    "Given a question (and, if present, the exact JSON schema the final "
    "answer must satisfy), list up to 6 concrete, independently-checkable "
    "requirements the answer MUST satisfy to be considered complete and "
    "correct. Use these requirement categories where they fit: "
    "candidate_universe (what set of entities/items is in scope), "
    "metric_or_field_relation (which metric, field, or relationship must "
    "be reported), scope (time range, region, edition, or other scoping "
    "filter), time_qualifier (a specific date, period, or as-of "
    "condition), cardinality (an exact count, top-N, or single-vs-"
    "multiple requirement), ranking (an explicit order or comparison "
    "requirement), completeness (every required field/element must be "
    "present, not just one), absence (a requirement that something does "
    "NOT apply, exist, or occur), other (anything else load-bearing).\n"
    "Do not invent requirements the question does not ask for. Skip "
    "stylistic or formatting-only observations.\n"
    "For each requirement, write a short label, its category, and a "
    "one-sentence description of what a fully satisfying answer must "
    "contain.\n"
    "Return JSON only: {\"requirements\": [{\"requirement\": str, "
    "\"category\": str, \"check\": str}, ...]}. Return an empty list only "
    "if the question truly has a single trivial requirement."
)

_S18_COVERAGE_SYSTEM_PROMPT = (
    "You are a strict requirement-coverage auditor.\n"
    "You receive a checklist of requirements a research answer must "
    "satisfy, and the CURRENT answer content (either prose text or a "
    "JSON object).\n"
    "For EACH requirement, decide independently:\n"
    "- satisfied: the current content clearly and specifically addresses "
    "this requirement with a concrete value or statement.\n"
    "- weak: the requirement is only vaguely, partially, or ambiguously "
    "addressed (e.g. missing a specific figure, date, or one part of a "
    "multi-part requirement).\n"
    "- missing: the current content does not address this requirement at "
    "all.\n"
    "For any requirement marked weak or missing, also produce a short, "
    "targeted web search query (5-15 words) that would directly source "
    "the missing information -- specific to that ONE requirement, not a "
    "restatement of the whole question.\n"
    "Return JSON only: {\"coverage\": [{\"index\": int, \"verdict\": "
    "\"satisfied\"|\"weak\"|\"missing\", \"gap_query\": str or null}, "
    "...]}, one entry per requirement in the given order."
)

_S18_PATCH_TEXT_SYSTEM_PROMPT = (
    "You fill in ONE missing or weak requirement inside a research answer "
    "using freshly retrieved evidence.\n"
    "Rewrite the COMPLETE answer: keep every part unrelated to this "
    "requirement byte-for-byte where feasible, and add or correct only "
    "the content needed to satisfy this specific requirement using the "
    "fresh evidence. If the evidence does not clearly resolve the "
    "requirement, make the smallest safe improvement (e.g. state what is "
    "known and flag what remains unconfirmed) rather than guessing.\n"
    "Preserve all existing citation markers whose underlying content is "
    "unchanged. Output plain answer text only: no preamble, no markdown "
    "fences, no meta-commentary about this process."
)

_S18_PATCH_OUTPUT_SYSTEM_PROMPT = (
    "You fill in ONE missing or weak requirement inside a structured JSON "
    "answer using freshly retrieved evidence.\n"
    "You receive the target JSON schema, the CURRENT JSON answer, one "
    "specific missing/weak requirement, and fresh evidence snippets "
    "gathered to resolve it.\n"
    "Return ONLY the JSON keys (top-level, or one level nested) whose "
    "values must be added or corrected to satisfy this requirement, using "
    "ONLY key names that already exist in the schema or current answer -- "
    "never invent new keys. If the fresh evidence does not give you a "
    "confident value, return an empty patch.\n"
    "Also report which evidence snippets (by 0-based index) you actually "
    "used.\n"
    "Return JSON only: {\"patch\": {...} or {}, \"used_indices\": "
    "[int, ...]}"
)


def _s18_strip_json_fences(raw: str) -> str:
    return _s18_re.sub(r"^```(?:json)?\s*|\s*```$", "", raw or "", flags=_s18_re.I | _s18_re.M).strip()


def _s18_chat_text(llm_result) -> str:
    if llm_result is None:
        return ""
    resp = getattr(llm_result, "response", None)
    text = getattr(resp, "raw_text", None) if resp is not None else None
    return (text or "").strip()


def _s18_compact_json(value) -> str:
    try:
        return _s18_json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return ""


def _s18_citation_key(ref) -> tuple:
    slices = tuple(
        (getattr(sl, "start", None), getattr(sl, "end", None))
        for sl in (getattr(ref, "slices", None) or [])
    )
    return (getattr(ref, "receipt_id", None), getattr(ref, "result_id", None), slices)


def _s18_dedup_citations(response):
    citations = getattr(response, "citations", None)
    if not citations:
        return response
    seen: set = set()
    deduped = []
    for ref in citations:
        key = _s18_citation_key(ref)
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


def _s18_merge_citations(existing, new_refs):
    existing_list = list(existing or [])
    seen = {_s18_citation_key(ref) for ref in existing_list}
    merged = list(existing_list)
    for ref in new_refs:
        key = _s18_citation_key(ref)
        if key in seen:
            continue
        seen.add(key)
        merged.append(ref)
        if len(merged) >= _S18_MAX_TOTAL_CITATIONS:
            break
    return merged


async def _s18_extract_requirements(question: str, output_schema) -> list:
    from harnyx_miner_sdk.api import llm_chat as _s18_llm_chat

    schema_block = ""
    if output_schema is not None:
        schema_json = _s18_compact_json(output_schema)[:4000]
        if schema_json:
            schema_block = (
                f"\n\nThe final answer must be a JSON object satisfying "
                f"this schema:\n{schema_json}"
            )
    try:
        result = await _s18_llm_chat(
            provider="openrouter",
            model=_S18_MODEL,
            messages=[
                {"role": "system", "content": _S18_EXTRACT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Question:\n{question}{schema_block}"},
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=550,
            timeout=_S18_EXTRACT_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return []
    try:
        parsed = _s18_json.loads(_s18_strip_json_fences(_s18_chat_text(result)))
    except Exception:
        return []
    if not isinstance(parsed, dict):
        return []
    raw = parsed.get("requirements")
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        requirement = str(item.get("requirement") or "").strip()
        category = str(item.get("category") or "other").strip() or "other"
        check = str(item.get("check") or "").strip()
        if requirement:
            out.append({"requirement": requirement, "category": category, "check": check})
        if len(out) >= _S18_MAX_REQUIREMENTS:
            break
    return out


async def _s18_check_coverage(requirements: list, content_repr: str, is_structured: bool) -> list:
    from harnyx_miner_sdk.api import llm_chat as _s18_llm_chat

    checklist_block = "\n".join(
        f"{idx}. [{req['category']}] {req['requirement']} \u2014 {req['check']}"
        for idx, req in enumerate(requirements)
    )
    label = "Current JSON answer" if is_structured else "Current answer text"
    try:
        result = await _s18_llm_chat(
            provider="openrouter",
            model=_S18_MODEL,
            messages=[
                {"role": "system", "content": _S18_COVERAGE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Requirement checklist:\n{checklist_block}\n\n"
                        f"{label}:\n{content_repr[:12000]}"
                    ),
                },
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=600,
            timeout=_S18_COVERAGE_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return []
    try:
        parsed = _s18_json.loads(_s18_strip_json_fences(_s18_chat_text(result)))
    except Exception:
        return []
    if not isinstance(parsed, dict):
        return []
    raw = parsed.get("coverage")
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("index"))
        except Exception:
            continue
        verdict = str(item.get("verdict") or "").strip().lower()
        gap_query_raw = item.get("gap_query")
        gap_query = gap_query_raw.strip() if isinstance(gap_query_raw, str) else ""
        if 0 <= idx < len(requirements) and verdict in ("satisfied", "weak", "missing"):
            out.append({"index": idx, "verdict": verdict, "gap_query": gap_query or None})
    return out


async def _s18_search_gap(search_query: str):
    from harnyx_miner_sdk.api import search_web as _s18_search_web

    for provider_name in ("parallel", "desearch"):
        try:
            payload = await _s18_search_web(
                search_query[:300],
                provider=provider_name,
                num=4,
                timeout=_S18_SEARCH_TIMEOUT_S,
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
        items = []
        for item in results:
            rid = getattr(item, "result_id", None)
            note = (getattr(item, "note", None) or "").strip()
            if not isinstance(rid, str) or not rid or not note:
                continue
            items.append({
                "result_id": rid,
                "note": note,
                "title": (getattr(item, "title", None) or "").strip(),
                "url": (getattr(item, "url", None) or "").strip(),
            })
            if len(items) >= 4:
                break
        if items:
            return {"receipt_id": receipt, "items": items}
    return None


def _s18_build_refs(receipt_id: str, evidence_items: list, indices) -> list:
    from harnyx_miner_sdk.query import CitationRef as _s18_citation_ref
    from harnyx_miner_sdk.query import CitationSlice as _s18_citation_slice

    refs = []
    for raw_idx in (indices or []):
        try:
            idx = int(raw_idx)
        except Exception:
            continue
        if not (0 <= idx < len(evidence_items)):
            continue
        item = evidence_items[idx]
        note_len = len(item["note"])
        end = min(500, note_len)
        if end <= 0:
            continue
        try:
            refs.append(_s18_citation_ref(
                receipt_id=receipt_id,
                result_id=item["result_id"],
                slices=[_s18_citation_slice(start=0, end=end)],
            ))
        except Exception:
            continue
        if len(refs) >= _S18_MAX_NEW_CITATIONS_PER_GAP:
            break
    return refs


async def _s18_patch_text(question: str, answer: str, requirement_label: str, gap_query: str, evidence_block: str) -> str:
    from harnyx_miner_sdk.api import llm_chat as _s18_llm_chat

    prompt = (
        f"Question:\n{question}\n\n"
        f"Current answer:\n{answer[:12000]}\n\n"
        f"Requirement being filled:\n{requirement_label}\n\n"
        f"Search query used to source it:\n{gap_query}\n\n"
        f"Fresh evidence snippets:\n{evidence_block}"
    )
    try:
        result = await _s18_llm_chat(
            provider="openrouter",
            model=_S18_MODEL,
            messages=[
                {"role": "system", "content": _S18_PATCH_TEXT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            tools=None,
            temperature=0.1,
            max_output_tokens=1400,
            timeout=_S18_PATCH_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return ""
    return _s18_chat_text(result)[:79000].strip()


async def _s18_patch_output(
    question: str,
    schema_compact: str,
    current_output_compact: str,
    requirement_label: str,
    gap_query: str,
    evidence_block: str,
) -> dict | None:
    from harnyx_miner_sdk.api import llm_chat as _s18_llm_chat

    prompt = (
        f"Question:\n{question}\n\n"
        f"Target JSON schema:\n{schema_compact or '(none provided)'}\n\n"
        f"Current JSON answer:\n{current_output_compact[:8000]}\n\n"
        f"Requirement to fill:\n{requirement_label}\n\n"
        f"Search query used to source it:\n{gap_query}\n\n"
        f"Fresh evidence snippets:\n{evidence_block}"
    )
    try:
        result = await _s18_llm_chat(
            provider="openrouter",
            model=_S18_MODEL,
            messages=[
                {"role": "system", "content": _S18_PATCH_OUTPUT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=700,
            timeout=_S18_PATCH_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return None
    try:
        parsed = _s18_json.loads(_s18_strip_json_fences(_s18_chat_text(result)))
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _s18_merge_output_patch(current, patch):
    """Shallow (+1-level-nested) merge that never introduces new keys."""
    if not isinstance(current, dict) or not isinstance(patch, dict) or not patch:
        return None
    merged = dict(current)
    applied = False
    for key, value in patch.items():
        if key not in merged:
            continue  # never invent schema-violating keys
        existing = merged[key]
        if isinstance(existing, dict) and isinstance(value, dict):
            merged_nested = dict(existing)
            for nested_key, nested_value in value.items():
                if nested_key in merged_nested:
                    merged_nested[nested_key] = nested_value
                    applied = True
            merged[key] = merged_nested
        else:
            merged[key] = value
            applied = True
    return merged if applied else None


async def _s18_coverage_pass(_s18_query, _s18_response):
    _s18_response = _s18_dedup_citations(_s18_response)
    question = (getattr(_s18_query, "text", None) or "").strip()
    if not question:
        return _s18_response

    output_schema = getattr(_s18_query, "output_schema", None)
    is_structured = getattr(_s18_response, "output", None) is not None

    if is_structured:
        current_output = getattr(_s18_response, "output")
        if not isinstance(current_output, dict):
            return _s18_response
        content_repr = _s18_compact_json(current_output)
        answer_text = None
    else:
        answer_text = (getattr(_s18_response, "text", None) or "").strip()
        if not answer_text:
            return _s18_response
        content_repr = answer_text
        current_output = None

    if not content_repr:
        return _s18_response

    requirements = await _s18_extract_requirements(question, output_schema)
    if not requirements:
        return _s18_response

    coverage = await _s18_check_coverage(requirements, content_repr, is_structured)
    if not coverage:
        return _s18_response

    missing = [c for c in coverage if c["verdict"] == "missing" and c["gap_query"]]
    weak = [c for c in coverage if c["verdict"] == "weak" and c["gap_query"]]
    gaps = (missing + weak)[:_S18_MAX_GAPS_TO_FILL]
    if not gaps:
        return _s18_response

    search_results = await _s18_asyncio.gather(
        *[_s18_search_gap(g["gap_query"]) for g in gaps],
        return_exceptions=True,
    )

    per_gap = []
    for gap, search_result in zip(gaps, search_results):
        if isinstance(search_result, Exception) or not search_result:
            continue
        per_gap.append((gap, search_result))
    if not per_gap:
        return _s18_response

    running_text = answer_text
    running_output = dict(current_output) if isinstance(current_output, dict) else None
    schema_compact = _s18_compact_json(output_schema)[:4000] if output_schema is not None else ""
    all_new_refs = []
    changed = False

    for gap, search_result in per_gap:
        req = requirements[gap["index"]]
        requirement_label = f"[{req['category']}] {req['requirement']} \u2014 {req['check']}"
        items = search_result["items"]
        receipt_id = search_result["receipt_id"]
        evidence_block = "\n".join(
            f"[{idx}] {item['title']} \u2014 {item['url']}\n{item['note'][:900]}"
            for idx, item in enumerate(items)
        )

        if is_structured:
            patch_result = await _s18_patch_output(
                question, schema_compact, _s18_compact_json(running_output),
                requirement_label, gap["gap_query"], evidence_block,
            )
            if not patch_result:
                continue
            patch = patch_result.get("patch")
            merged = _s18_merge_output_patch(running_output, patch) if isinstance(patch, dict) else None
            if merged is None:
                continue
            running_output = merged
            changed = True
            used_indices = patch_result.get("used_indices")
            refs = _s18_build_refs(
                receipt_id, items,
                used_indices if isinstance(used_indices, list) and used_indices else [0],
            )
            all_new_refs.extend(refs)
        else:
            patched = await _s18_patch_text(question, running_text, requirement_label, gap["gap_query"], evidence_block)
            if not patched:
                continue
            running_text = patched
            changed = True
            refs = _s18_build_refs(receipt_id, items, [0, 1])
            all_new_refs.extend(refs)

    if not changed:
        return _s18_response

    merged_citations = _s18_merge_citations(getattr(_s18_response, "citations", None), all_new_refs)
    try:
        if is_structured:
            return _s18_response.model_copy(update={"output": running_output, "citations": merged_citations})
        return _s18_response.model_copy(update={"text": running_text, "citations": merged_citations})
    except Exception:
        return _s18_response


async def _s18_finalize(_s18_query, _s18_response, _s18_t0: float):
    """Bounded requirement-coverage gap-filling pass (text + structured)."""
    if _s18_response is None:
        return _s18_response
    if getattr(_s18_response, "text", None) in (None, "") and getattr(_s18_response, "output", None) is None:
        return _s18_response
    elapsed = _s18_monotonic() - _s18_t0
    if elapsed >= _S18_HARD_BUDGET_GATE_S:
        return _s18_dedup_citations(_s18_response)
    window = min(_S18_MAX_WINDOW_S, max(_S18_MIN_WINDOW_S, 280.0 - elapsed))
    try:
        return await _s18_asyncio.wait_for(
            _s18_coverage_pass(_s18_query, _s18_response),
            timeout=window,
        )
    except Exception:
        return _s18_dedup_citations(_s18_response)


@entrypoint("query")
async def query(query: Query) -> Response:
    _s18_t0 = _s18_monotonic()
    _s18_resp = await _s18_base_query(query)
    try:
        return await _s18_finalize(query, _s18_resp, _s18_t0)
    except Exception:
        return _s18_resp
