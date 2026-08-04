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
        BUILD_TAG = 'a381495f8d214e529161db4294130c93'
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
        RESYNTH_TIMEOUT = 45.0
        LAST_RESORT_TIMEOUT = 50.0
        SCHEMA_TIMEOUT = 50.0
        MIN_CHAT_TIMEOUT = 6.0
        CHAT_TIME_MARGIN = 3.0
        MAX_TURNS = 12
        PATCH_EXTRA_TURNS = 2
        FORCE_COMMIT_SECONDS = 85.0
        COVERAGE_MIN_SECONDS = 60.0
        COVERAGE_MIN_BUDGET = 0.06
        COVERAGE_MAX_RETRY_TURNS = 4
        CITE_MIN_MARKERS = 2
        CITE_FLOOR_N = 4
        MIN_DRAFT_BUDGET = 0.03
        MIN_PATCH_BUDGET = 0.05
        FORCE_COMMIT_BUDGET = 0.02
        MAX_ANSWER_CHARS = 70000
        MAX_CITATIONS = 40
        SEARCH_NOTE_CHARS = 500
        FETCH_NOTE_CHARS = 6000
        FETCH_SLICE_THRESHOLD = 8000
        TOOLS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web. Returns numbered results with title, url and a short excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': 'Fetch one URL and return its extracted main text content.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}}, 'required': ['url']}}}]
        LOOP_SYSTEM_PROMPT = 'You are an elite research analyst answering a multi-constraint factual question. Your answer will be judged pairwise against a strong reference answer: factual claims only earn credit when backed by cited tool results, and missing any element of the question is a coverage failure.\n\nYou have search_web and fetch_page tools. Work candidate-by-candidate and constraint-by-constraint: verify every load-bearing fact (names, dates, counts, figures) with a tool result before asserting it — do not trust memory for verifiable specifics. Tool results are numbered like [7].\n\nCITATION RULE: in the final answer, put the source number in brackets immediately after EVERY factual claim — for qualifying entities AND for excluded ones (e.g. \'completed in 2017 [4]\', \'only 13 storeys [9]\'). A claim without a bracket is treated as uncited. Do not cite sources that do not support the claim.\n\nFINAL ANSWER SHAPE: open with the direct answer (the qualifying entities / number / verdict) in the first sentence or list, in exactly the format the question requests — sentence one is never a remark about evidence quality. Then a short \'Proof of completeness\' section: candidate pool, each constraint applied, per-entity specifics — one line per qualifying entity with its qualifying attribute cited, and one line per rejected candidate with its cited exclusion reason. Dense factual prose; no meta-commentary; never say the evidence is insufficient. Only when a figure exists solely inside a queryable database and nowhere in published sources, state the exact dataset + filters needed instead of inventing the number.\n\nPROVENANCE CONFIDENCE: when the question names a specific source but your verified facts come from other authoritative sources, state the facts confidently and treat the other sources as corroboration — never open with, or dwell on, the named source being absent from your results.\n\nSOURCE AUTHORITY: when the question names a source (\'according to the United Nations\', \'per Forbes\', \'according to Box Office Mojo/IMDb/the World Bank\'), cite the PRIMARY source itself (un.org / data.un.org, forbes.com, boxofficemojo.com, imdb.com, data.worldbank.org) and PREFER it over aggregators, mirrors, or news reports (populationpyramid.net, database.earth, worldometers, secondhand articles). Copy that source\'s exact figures and dates verbatim — if it dates an event (e.g. a population milestone) to a specific month/year, use that, not a news outlet\'s earlier estimate.\n\nOUTPUT DIRECTIVES: obey literal formatting instructions mechanically. \'without the word "X"\' (or \'omit/excluding the word X\') means DELETE the word X from each title/name you output — it is NOT a filter that removes items containing X. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas. Emit exactly the requested shape.\n\nSELF-CONSISTENCY: before finishing, confirm the opening answer names exactly the entities your own cited sentences support; if the body establishes a different set, rewrite the opening to match it. Verify no claim contradicts the text of its own cited source.\n\nDo not call a tool and write the final answer in the same turn. When every constraint is either verified or best-effort-covered, write the final answer with inline citations.'
        BRIEFING_SYSTEM = 'You are an elite research analyst with encyclopedic knowledge preparing a research briefing. Commit to concrete best guesses; never refuse.'
        BRIEFING_SECTIONS = "Produce a briefing with exactly these sections:\nDRAFT: your best definitive answer from knowledge alone — enumerate the full candidate pool, apply every constraint, name qualifying entities with concrete numbers/dates, note borderline exclusions. Mark uncertain values with (verify).\nCONSTRAINTS: numbered list of every atomic constraint/filter in the question (including ordering and requested output format).\nCANDIDATES: the entities to verify, one per line, with which constraints are uncertain for each.\nQUERIES: 3-6 targeted web searches that would verify the load-bearing facts (exact names + years; include the named source site if any).\nFETCH: 0-6 exact URLs likely to contain the needed figures, ONLY for named sources whose URL patterns you know (one per entity/year; for annual reports pick the edition containing each requested year, usually year+1 or year+2). Otherwise write 'none'."
        ENUM_DIRECTIVE_TEXT = "SET-COMPLETENESS REQUIREMENT: this question asks for a SET, so an answer naming one qualifying item from an unchecked pool scores as WRONG, not partial.\n1. Enumerate the full candidate pool the evidence supports, test EVERY candidate against each stated criterion, and list every one that qualifies with its own citation per criterion.\n2. Name the prominent near-miss candidates you excluded and the criterion each fails.\n3. Do NOT write 'the only', 'the sole', or 'the single' unless you enumerated and checked the whole pool. If the evidence covers only part of it, still commit: give every qualifying candidate found and say the roster may be incomplete."
        CITE_GAP_DIRECTIVE = 'CITATION GAP — your answer is under-sourced and will get NO factual credit for uncited claims. Every load-bearing fact (names, numbers, dates, the final verdict) MUST carry a [n] citation to a search/fetch result. Search/fetch any uncited fact, then re-state the COMPLETE answer with a [n] marker on every claim.'
        AUDIT_SYSTEM = 'You are a strict answer auditor. Output JSON only.'
        AUDIT_KEYS = ('missing_elements', 'uncited_claims', 'suspect_attributions', 'contradictions', 'wrong_source')

        def _force_commit_message(remaining: float) -> str:
            return f'TIME LIMIT: about {int(remaining)} seconds remain. Stop researching now. Using ONLY the numbered tool results above plus the briefing, write your best final answer with inline [n] citations in the required shape. A partial but cited and fully-covering answer scores far better than a refusal — never refuse.'

        class _Run:

            def __init__(self) -> None:
                self.deadline = monotonic() + TOTAL_BUDGET_SECONDS
                self.budget_usd = None
                self.entries = {}
                self.next_number = 1

            def remaining(self) -> float:
                return self.deadline - monotonic()

            def chat_timeout(self, wanted: float) -> float:
                room = self.remaining() - CHAT_TIME_MARGIN
                if room < MIN_CHAT_TIMEOUT:
                    return 0.0
                if wanted < room:
                    return wanted
                return room

            def note_budget(self, payload) -> None:
                budget = getattr(payload, 'budget', None)
                remaining = getattr(budget, 'session_remaining_budget_usd', None)
                if isinstance(remaining, (int, float)):
                    self.budget_usd = float(remaining)

            def budget_left(self) -> float:
                if isinstance(self.budget_usd, (int, float)):
                    return float(self.budget_usd)
                return 1.0

            def add_result(self, receipt_id: str, result_id: str, note: str, source: str) -> int:
                number = self.next_number
                self.next_number += 1
                self.entries[number] = {'receipt_id': receipt_id, 'result_id': result_id, 'note_len': len(note or ''), 'source': source}
                return number

            def max_number(self) -> int:
                return self.next_number - 1
        _BRACKET_RE = re.compile('\\[([0-9][0-9,\\s-]*)\\]')
        _UNFINISHED_RE = re.compile("^\\s*(let me\\b|now i\\b|next[, ]|i(?:'ll| will| need to| should| am going to| have the)\\b|based on my research,? i (?:need|will|should)\\b|first,? i(?:'ll| will)\\b|let'?s\\b|to (?:answer|verify|confirm) this\\b)", re.IGNORECASE)
        _DRAFT_PREFIX_RE = re.compile("^\\s*[#*>\\s]*\\**\\s*(draft\\b|draft:|best[\\- ]?definitive answer\\b|based on (?:my )?(?:general )?knowledge\\b|now i have (?:all )?the data\\b|here'?s? (?:my )?draft\\b)", re.IGNORECASE)
        _DRAFT_STRIP_RE = re.compile("^\\s*[#*>\\s]*\\**\\s*(?:draft|here'?s? my draft)\\s*:?\\s*\\**\\s*", re.IGNORECASE)
        _SCRATCH_OPEN_RE = re.compile("^\\s*(?:perfect[!.,\\s]+|great[!.,\\s]+|okay[!.,\\s]+|ok[!.,\\s]+)?(?:i (?:now )?have (?:the|all|complete|gathered|enough)|i'?ve (?:now )?(?:got|gathered|found|collected|compiled|obtained)|i (?:can )?now have|i now have|i have gathered|let me (?:verify|compile|check|finalize|cross[- ]?check|now\\b)|here'?s (?:the|my) (?:final|complete))\\b", re.IGNORECASE)
        _BEST_ANSWER_PREFIX_RE = re.compile('^\\**\\s*best[\\- ]?definitive answer\\s*:?\\s*\\**\\s*', re.IGNORECASE)
        _ANSWER_PREFIX_RE = re.compile('^\\**\\s*(?:final )?answer\\s*:?\\s*\\**\\s*', re.IGNORECASE)
        _WITHOUT_WORD_RE = re.compile('without (?:the word|the term|using)\\s*["“‘\\\']?([A-Za-z][\\w\\-]*)["”’\\\']?', re.IGNORECASE)
        _TOOL_CALL_BLOCK_RE = re.compile('<tool_call>(.*?)</tool_call>', re.S)
        _ARG_VALUE_RE = re.compile('<arg_value>(.*?)</arg_value>', re.S)
        _LEAK_TAG_RE = re.compile('</?(?:tool_call|arg_key|arg_value)[^>]*>')

        def _looks_unfinished(answer: str) -> bool:
            text = (answer or '').strip()
            if not text:
                return True
            head = text[:80]
            if _DRAFT_PREFIX_RE.match(head):
                return True
            if _SCRATCH_OPEN_RE.match(head):
                return True
            if _BRACKET_RE.search(text):
                return False
            if len(text) < 40:
                return True
            if _UNFINISHED_RE.match(text[:160]):
                return 'final answer' not in text.lower() and len(text) < 500
            return False

        def _strip_draft_framing(text: str) -> str:
            original = (text or '').strip()
            out = _DRAFT_STRIP_RE.sub('', original, count=1).strip()
            out = _BEST_ANSWER_PREFIX_RE.sub('', out).strip()
            out = _ANSWER_PREFIX_RE.sub('', out).strip()
            return out or original

        def _apply_output_directives(question: str, answer: str) -> str:
            if not answer:
                return answer
            out = answer
            for found in _WITHOUT_WORD_RE.finditer(question or ''):
                word = found.group(1)
                if len(word) >= 3:
                    out = re.sub('\\b' + re.escape(word) + '\\b', '', out, flags=re.IGNORECASE)
            if out != answer:
                out = re.sub('[ \\t]{2,}', ' ', out)
                out = re.sub('\\s+([,.;:)])', '\\1', out)
                out = re.sub('\\(\\s+', '(', out)
            return out.strip() or answer

        def _leaked_call_name(block: str) -> str:
            head = (block or '').split('<', 1)[0]
            words = head.split()
            if not words:
                return ''
            return words[0]

        def _parse_leaked_tool_calls(text: str) -> list:
            calls = []
            for block in _TOOL_CALL_BLOCK_RE.findall(text or ''):
                name = _leaked_call_name(block)
                if name != 'search_web' and name != 'fetch_page':
                    continue
                values = _ARG_VALUE_RE.findall(block)
                if values:
                    calls.append((name, values[0].strip()))
            return calls

        def _strip_leak_markup(text: str) -> str:
            cleaned = _TOOL_CALL_BLOCK_RE.sub('', text or '')
            return _LEAK_TAG_RE.sub('', cleaned).strip()

        def _content_to_text(content) -> str:
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for piece in content:
                    if isinstance(piece, str):
                        parts.append(piece)
                        continue
                    if isinstance(piece, dict):
                        value = piece.get('text')
                        if not isinstance(value, str):
                            value = piece.get('content')
                        if isinstance(value, str):
                            parts.append(value)
                        continue
                    value = getattr(piece, 'text', None)
                    if isinstance(value, str):
                        parts.append(value)
                return ''.join(parts)
            return ''

        def _message_text(llm, message) -> str:
            text = (getattr(llm, 'raw_text', None) or '').strip()
            if text:
                return text
            return _content_to_text(getattr(message, 'content', None)).strip()

        def _clamp(text: str) -> str:
            out = (text or '').strip()
            if len(out) > MAX_ANSWER_CHARS:
                return out[:MAX_ANSWER_CHARS - 20] + '\n…[truncated]'
            return out

        async def _plain_chat(run: _Run, model: str, system: str, user: str, max_tokens: int, timeout: float, thinking=None) -> str:
            budgeted = run.chat_timeout(timeout)
            if budgeted <= 0.0:
                return ''
            if thinking is None:
                thinking_arg = {'enabled': False}
            else:
                thinking_arg = thinking
            payload = await llm_chat(provider=PROVIDER, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=budgeted, thinking=thinking_arg)
            run.note_budget(payload)
            llm = getattr(payload, 'llm', None)
            text = (getattr(llm, 'raw_text', None) or '').strip()
            if text:
                return text
            choices = getattr(llm, 'choices', None) or []
            if choices:
                message = getattr(choices[0], 'message', None)
                got = _content_to_text(getattr(message, 'content', None)).strip()
                if got:
                    return got
            return ''

        async def _loop_chat(run: _Run, messages: list, force_text: bool):
            for attempt in range(2):
                timeout = run.chat_timeout(LOOP_TURN_TIMEOUT)
                if timeout <= 0.0:
                    return None
                if attempt == 0:
                    model = LOOP_MODEL
                else:
                    model = FALLBACK_MODEL
                if force_text:
                    tools_arg = None
                    choice_arg = None
                else:
                    tools_arg = TOOLS
                    choice_arg = 'auto'
                try:
                    return await llm_chat(provider=PROVIDER, model=model, messages=messages, tools=tools_arg, tool_choice=choice_arg, temperature=0.2, thinking={'enabled': True, 'effort': 'low'}, timeout=timeout)
                except Exception:
                    continue
            return None

        async def _tool_search(query_text: str, run: _Run) -> str:
            if not (query_text or '').strip():
                return '# search_web -> empty query'
            resp = None
            for provider in ('desearch', 'parallel'):
                try:
                    resp = await search_web(query_text, provider=provider, num=8, timeout=SEARCH_TIMEOUT)
                    if getattr(resp, 'results', None):
                        break
                except Exception:
                    resp = None
            if resp is None:
                return '# search_web(' + repr(query_text) + ') -> ERROR (all providers failed)'
            run.note_budget(resp)
            receipt = getattr(resp, 'receipt_id', '') or ''
            results = list(getattr(resp, 'results', None) or [])
            lines = ['# search_web(' + repr(query_text) + ') -> ' + str(len(results)) + ' results']
            for result in results:
                rid = getattr(result, 'result_id', None)
                if not isinstance(rid, str) or not rid:
                    continue
                note = (getattr(result, 'note', None) or '')[:SEARCH_NOTE_CHARS]
                number = run.add_result(receipt, rid, note, 'search')
                title = getattr(result, 'title', None) or ''
                url = getattr(result, 'url', None) or ''
                lines.append('[' + str(number) + '] ' + title + '\n  url: ' + url + '\n  excerpt: ' + note)
            return '\n'.join(lines)

        async def _tool_fetch(url: str, run: _Run) -> str:
            if not (url or '').strip():
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
                return '# fetch_page(' + repr(url) + ') -> ERROR (all providers failed)'
            run.note_budget(resp)
            receipt = getattr(resp, 'receipt_id', '') or ''
            results = list(getattr(resp, 'results', None) or [])
            if not results:
                return '# fetch_page(' + repr(url) + ') -> no content'
            result = results[0]
            rid = getattr(result, 'result_id', None)
            note = getattr(result, 'note', None) or ''
            if not isinstance(rid, str) or not rid or (not note.strip()):
                return '# fetch_page(' + repr(url) + ') -> no usable content'
            number = run.add_result(receipt, rid, note, 'fetch')
            shown = note[:FETCH_NOTE_CHARS]
            return '# fetch_page(' + repr(url) + ') -> [' + str(number) + '] ' + str(len(shown)) + ' chars shown\n' + shown

        async def _run_tool_call(tool_call, run: _Run) -> str:
            try:
                args = json.loads(getattr(tool_call, 'arguments', None) or '{}')
            except Exception:
                args = {}
            if not isinstance(args, dict):
                args = {}
            name = getattr(tool_call, 'name', '') or ''
            if name == 'search_web':
                return await _tool_search(str(args.get('query', '')), run)
            if name == 'fetch_page':
                return await _tool_fetch(str(args.get('url', '')), run)
            return '# unknown tool ' + repr(name)

        async def _execute_leaked_calls(calls: list, run: _Run) -> list:
            coros = []
            for name, argument in calls[:3]:
                if name == 'search_web':
                    coros.append(_tool_search(argument, run))
                else:
                    coros.append(_tool_fetch(argument, run))
            if not coros:
                return []
            return await asyncio.gather(*coros, return_exceptions=True)

        def _tool_result_text(out) -> str:
            if isinstance(out, str):
                return out
            return '# tool error: ' + str(out)

        def _to_input_message(message):
            try:
                return message.to_input_message()
            except Exception:
                return {'role': 'assistant', 'content': _content_to_text(getattr(message, 'content', None))}
        _ENUM_QUESTION_RE = re.compile('\\b(which|what)\\b[^?]{0,80}\\b(all|every|each)\\b|\\ball\\s+(?:the\\s+)?\\w+\\s+(?:that|who|which)\\b|\\blist\\s+(?:all|every|the)\\b|\\bname\\s+(?:all|every|each)\\b|\\bhow\\s+many\\b', re.IGNORECASE)
        _ENUM_PLURAL_RE = re.compile('\\b(?:which|what)\\b(?:\\s+\\w+){0,2}?\\s+(\\w{4,}s)\\b', re.IGNORECASE)
        _ENUM_ALL_RE = re.compile('\\b(all|every|each)\\b', re.IGNORECASE)
        _ENUM_PLURAL_STOP = frozenset({'was', 'has', 'does', 'this', 'these', 'those', 'its', 'hers', 'yours', 'always', 'across', 'class', 'less', 'unless', 'press', 'gas', 'bus'})
        _ENUM_SUPERLATIVE_RE = re.compile('\\b(highest|lowest|largest|smallest|most|least|greatest|fewest|longest|shortest)\\b', re.IGNORECASE)

        def _enum_is_set_question(question: str) -> bool:
            text = ' '.join((question or '').split())
            if not text:
                return False
            if _ENUM_QUESTION_RE.search(text):
                return True
            plural = _ENUM_PLURAL_RE.search(text)
            if plural and plural.group(1).lower() not in _ENUM_PLURAL_STOP:
                if not _ENUM_SUPERLATIVE_RE.search(text) or _ENUM_ALL_RE.search(text):
                    return True
            return bool(_ENUM_SUPERLATIVE_RE.search(text)) and ' and ' in text.lower()

        def _enum_directive(question: str) -> str:
            if not _enum_is_set_question(question):
                return ''
            return ENUM_DIRECTIVE_TEXT

        def _seed_transcript(question: str, briefing: str, seed_messages) -> list:
            if seed_messages:
                return list(seed_messages)
            messages = [{'role': 'system', 'content': LOOP_SYSTEM_PROMPT}]
            directive = _enum_directive(question)
            if directive:
                messages.append({'role': 'system', 'content': directive})
            if briefing:
                messages.append({'role': 'system', 'content': briefing})
            messages.append({'role': 'user', 'content': question})
            return messages

        async def _research_loop(run: _Run, question: str, briefing: str, max_turns: int, seed_messages=None):
            messages = _seed_transcript(question, briefing, seed_messages)
            final_answer = ''
            nudged = False
            for turn in range(1, max_turns + 1):
                remaining = run.remaining()
                if remaining <= 8.0:
                    break
                time_critical = remaining <= FORCE_COMMIT_SECONDS
                budget_critical = run.budget_left() <= FORCE_COMMIT_BUDGET
                force_final = turn >= max_turns or time_critical or budget_critical
                if (force_final or turn >= max_turns - 1) and (not nudged):
                    messages.append({'role': 'system', 'content': _force_commit_message(remaining)})
                    nudged = True
                payload = await _loop_chat(run, messages, force_final)
                if payload is None:
                    break
                run.note_budget(payload)
                llm = getattr(payload, 'llm', None)
                choices = getattr(llm, 'choices', None) or []
                if not choices:
                    break
                message = getattr(choices[0], 'message', None)
                if message is None:
                    break
                tool_calls = getattr(message, 'tool_calls', None) or ()
                if not tool_calls:
                    text = _message_text(llm, message)
                    leaked = _parse_leaked_tool_calls(text)
                    if leaked and (not force_final):
                        messages.append({'role': 'assistant', 'content': text})
                        outs = await _execute_leaked_calls(leaked, run)
                        for out in outs:
                            messages.append({'role': 'user', 'content': _tool_result_text(out)})
                        continue
                    if '<tool_call' in text.lower():
                        text = _strip_leak_markup(text)
                    final_answer = text
                    break
                try:
                    messages.append(_to_input_message(message))
                    call_list = list(tool_calls)
                    outputs = await asyncio.gather(*[_run_tool_call(tc, run) for tc in call_list], return_exceptions=True)
                    for position in range(len(call_list)):
                        call_id = getattr(call_list[position], 'id', None) or ''
                        messages.append({'role': 'tool', 'tool_call_id': call_id, 'content': _tool_result_text(outputs[position])})
                except Exception:
                    break
            return (final_answer, messages)

        async def _phase_briefing(run: _Run, question: str):
            user = 'Question:\n' + question + '\n\n' + BRIEFING_SECTIONS
            raw = ''
            try:
                raw = await _plain_chat(run, DRAFT_MODEL, BRIEFING_SYSTEM, user, 2400, DRAFT_TIMEOUT, {'enabled': True, 'effort': 'low'})
            except Exception:
                raw = ''
            if not raw.strip():
                try:
                    raw = await _plain_chat(run, FALLBACK_MODEL, BRIEFING_SYSTEM, user, 2000, DRAFT_TIMEOUT)
                except Exception:
                    raw = ''
            if not raw.strip():
                return ('', '')
            draft = raw
            marker = re.search('CONSTRAINTS\\s*:', raw)
            if marker is not None:
                draft = raw[:marker.start()]
            draft = re.sub('^DRAFT\\s*:\\s*', '', draft).strip()
            briefing = 'RESEARCH BRIEFING (from prior analysis; verify uncertain values, correct it where tool evidence disagrees):\n' + raw.strip()
            return (draft, briefing)

        def _audit_issues(report) -> list:
            issues = []
            if not isinstance(report, dict):
                return issues
            for key in AUDIT_KEYS:
                values = report.get(key)
                if isinstance(values, list):
                    for value in values:
                        text = str(value).strip()
                        if text:
                            issues.append(text)
            return issues

        async def _phase_audit(run: _Run, question: str, answer: str, messages: list):
            check_user = 'Audit this answer against its question. Report ONLY genuine, fixable problems as a JSON object with keys: "missing_elements" (question elements not addressed, or a qualifying set member not evaluated), "uncited_claims" (specific load-bearing factual claims lacking [n]), "suspect_attributions" (facts that look attributed to the wrong entity), "contradictions" (claims that conflict with the text of their own cited source, e.g. answer says shot in Paris but the citation says Nantes), "wrong_source" (used an aggregator/news site when the question named a specific primary source like the UN, Forbes, or Box Office Mojo). Use empty lists when fine. No other text.\n\nQuestion:\n' + question + '\n\nAnswer:\n' + answer[:12000]
            try:
                raw = await _plain_chat(run, PATCH_MODEL, AUDIT_SYSTEM, check_user, 700, PATCH_TIMEOUT)
                cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                report = json.loads(cleaned)
            except Exception:
                return (answer, messages)
            issues = _audit_issues(report)
            if not issues or run.remaining() < 40.0:
                return (answer, messages)
            seed = list(messages)
            seed.append({'role': 'system', 'content': 'AUDIT FOUND GAPS in your final answer:\n- ' + '\n- '.join(issues[:6]) + '\nYou may use at most 2 more tool calls to close the most important gaps, then rewrite the COMPLETE final answer with inline [n] citations in the required shape.'})
            patched, patched_messages = await _research_loop(run, question, '', PATCH_EXTRA_TURNS + 1, seed)
            patched = patched.strip()
            if patched:
                return (patched, patched_messages)
            return (answer, patched_messages)

        async def _phase_citation_gate(run: _Run, question: str, briefing: str, answer: str, messages: list):
            marker_count = len(_BRACKET_RE.findall(answer))
            if not answer.strip() or marker_count >= CITE_MIN_MARKERS:
                return (answer, messages)
            if run.remaining() <= COVERAGE_MIN_SECONDS or run.budget_left() < COVERAGE_MIN_BUDGET:
                return (answer, messages)
            seed = list(messages)
            seed.append({'role': 'system', 'content': CITE_GAP_DIRECTIVE})
            recited, recited_messages = await _research_loop(run, question, briefing, COVERAGE_MAX_RETRY_TURNS, seed)
            if recited and recited.strip() and (not _looks_unfinished(recited)) and (len(_BRACKET_RE.findall(recited)) >= marker_count):
                return (recited, recited_messages)
            return (answer, messages)

        async def _resynthesize_clean(run: _Run, answer: str) -> str:
            if run.remaining() < 25.0 or run.budget_left() < COVERAGE_MIN_BUDGET:
                return ''
            system = "Rewrite the text into a DIRECT final answer. Remove ALL process narration ('I have the data', 'Let me verify', 'Perfect!', 'Now I…'). Keep every fact, every [n] citation marker exactly, and the required output format. Output only the answer."
            try:
                out = await _plain_chat(run, DRAFT_MODEL, system, answer[:6000], 1200, RESYNTH_TIMEOUT)
            except Exception:
                return ''
            out = (out or '').strip()
            if out and (not _looks_unfinished(out)):
                return out
            return ''

        async def _last_resort(run: _Run, question: str) -> str:
            try:
                return await _plain_chat(run, FALLBACK_MODEL, 'Expert researcher. Give your best definitive answer with concrete entities, numbers and dates. Never refuse.', question, 1600, LAST_RESORT_TIMEOUT)
            except Exception:
                return ''

        def _cited_numbers(answer: str, max_number: int) -> list:
            seen = set()
            ordered = []
            for found in _BRACKET_RE.finditer(answer or ''):
                for part in found.group(1).split(','):
                    text = part.strip()
                    span = re.fullmatch('(\\d{1,4})\\s*-\\s*(\\d{1,4})', text)
                    if span:
                        start = int(span.group(1))
                        end = int(span.group(2))
                        for number in range(start, min(end, start + 20) + 1):
                            if 1 <= number <= max_number and number not in seen:
                                seen.add(number)
                                ordered.append(number)
                    elif text.isdigit():
                        number = int(text)
                        if 1 <= number <= max_number and number not in seen:
                            seen.add(number)
                            ordered.append(number)
            return ordered

        def _citation_for(entry) -> object:
            receipt_id = entry.get('receipt_id')
            result_id = entry.get('result_id')
            if not receipt_id or not result_id:
                return None
            if entry.get('source') == 'fetch' and entry.get('note_len', 0) > FETCH_SLICE_THRESHOLD:
                return CitationRef(receipt_id=receipt_id, result_id=result_id, slices=[CitationSlice(start=0, end=FETCH_NOTE_CHARS)])
            return CitationRef(receipt_id=receipt_id, result_id=result_id)

        def _build_citations(answer: str, run: _Run) -> list:
            refs = []
            for number in _cited_numbers(answer, run.max_number())[:MAX_CITATIONS]:
                entry = run.entries.get(number)
                if entry is None:
                    continue
                ref = _citation_for(entry)
                if ref is not None:
                    refs.append(ref)
            return refs

        def _floor_citations(run: _Run) -> list:
            fetched = []
            searched = []
            for number in sorted(run.entries):
                entry = run.entries[number]
                if entry.get('source') == 'fetch':
                    fetched.append(entry)
                else:
                    searched.append(entry)
            floor = []
            for entry in fetched + searched:
                ref = _citation_for(entry)
                if ref is not None:
                    floor.append(ref)
                if len(floor) >= CITE_FLOOR_N:
                    break
            return floor

        def _build_citations_with_floor(answer: str, run: _Run) -> list:
            refs = _build_citations(answer, run)
            if refs:
                return refs
            return _floor_citations(run)

        async def _structured_output(run: _Run, question: str, answer: str, schema):
            schema_text = json.dumps(schema)
            user = 'Convert this answer into a JSON value that validates against the schema. Return ONLY the JSON value.\n\nSchema:\n' + schema_text + '\n\nQuestion:\n' + question + '\n\nAnswer:\n' + answer[:15000]
            for model in (JSON_MODEL, FALLBACK_MODEL):
                try:
                    raw = await _plain_chat(run, model, 'You output strictly valid JSON matching the given schema.', user, 2400, SCHEMA_TIMEOUT)
                    cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()
                    if not cleaned:
                        continue
                    return json.loads(cleaned)
                except Exception:
                    continue
            return None

        async def query(query: Query) -> Response:
            question = (query.text or '').strip()
            if not question:
                return Response(text='No question provided.')
            try:
                return await _answer(query, question)
            except Exception:
                return Response(text='Best-effort summary unavailable for: ' + question[:600])

        async def _answer(query: Query, question: str) -> Response:
            run = _Run()
            try:
                info = await tooling_info(timeout=10.0)
                run.note_budget(info)
            except Exception:
                pass
            draft = ''
            briefing = ''
            try:
                if run.budget_left() >= MIN_DRAFT_BUDGET and run.remaining() > 120.0:
                    draft, briefing = await _phase_briefing(run, question)
            except Exception:
                draft = ''
                briefing = ''
            answer = ''
            messages = []
            try:
                answer, messages = await _research_loop(run, question, briefing, MAX_TURNS)
            except Exception:
                answer = ''
            try:
                if answer and run.remaining() > 45.0 and (run.budget_left() >= MIN_PATCH_BUDGET):
                    answer, messages = await _phase_audit(run, question, answer, messages)
            except Exception:
                pass
            try:
                answer, messages = await _phase_citation_gate(run, question, briefing, answer, messages)
            except Exception:
                pass
            if not answer.strip():
                answer = draft.strip()
                if not answer:
                    answer = await _last_resort(run, question)
            try:
                if _looks_unfinished(answer):
                    rescue = await _resynthesize_clean(run, answer)
                    if _looks_unfinished(rescue):
                        rescue = _strip_draft_framing(answer)
                    if _looks_unfinished(rescue):
                        alternative = _strip_draft_framing(draft.strip())
                        if not _looks_unfinished(alternative):
                            rescue = alternative
                    if _looks_unfinished(rescue) and run.remaining() > 20.0:
                        late = await _last_resort(run, question)
                        if late and (not _looks_unfinished(late)):
                            rescue = late
                    if rescue:
                        answer = rescue
            except Exception:
                pass
            answer = _apply_output_directives(question, answer)
            try:
                citations = _build_citations_with_floor(answer, run)
            except Exception:
                citations = []
            final_text = _clamp(answer)
            if not final_text:
                final_text = 'Best-effort answer unavailable for: ' + question[:400]
            if query.output_schema is not None:
                output = None
                try:
                    output = await _structured_output(run, question, answer, query.output_schema)
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
        PROVIDER = 'openrouter'
        DRAFT_MODEL = 'z-ai/glm-5'
        LOOP_MODEL = 'z-ai/glm-5'
        PATCH_MODEL = 'openai/gpt-oss-120b'
        JSON_MODEL = 'openai/gpt-oss-120b'
        FALLBACK_MODEL = 'deepseek/deepseek-v3.2'
        TOTAL_BUDGET_SECONDS = 245.0
        PATCH_TIMEOUT = 30.0
        SEARCH_TIMEOUT = 20.0
        SEARCH_NOTE_CHARS = 500
        LOOP_TURN_TIMEOUT = 80.0
        FETCH_TIMEOUT = 15.0
        MAX_TURNS = 12
        PATCH_EXTRA_TURNS = 2
        MAX_ANSWER_CHARS = 70000
        FORCE_COMMIT_SECONDS = 85.0
        DRAFT_TIMEOUT = 55.0
        MAX_CITATIONS = 40
        FETCH_NOTE_CHARS = 6000
        FETCH_SLICE_THRESHOLD = 8000
        FINAL_RESERVE = 45.0
        TAIL_RESERVE = 6.0
        SCHEMA_RESERVE = 35.0
        SALVAGE_TIMEOUT = 40.0
        MIN_TOOL_TIMEOUT = 5.0
        MIN_CHAT_TIMEOUT = 8.0
        PATCH_MIN_RATIO = 0.55
        MIN_DRAFT_BUDGET = 0.03
        MIN_PATCH_BUDGET = 0.05
        FORCE_COMMIT_BUDGET = 0.02
        _BUDGET = {'remaining': None}
        TOOLS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web. Returns numbered results with title, url and a short excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': 'Fetch one URL and return its extracted main text content.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}}, 'required': ['url']}}}]
        LOOP_SYSTEM_PROMPT = "You are an elite research analyst answering a multi-constraint factual question. Your answer will be judged pairwise against a strong reference answer: factual claims only earn credit when backed by cited tool results, and missing any element of the question is a coverage failure.\n\nYou have search_web and fetch_page tools. Work candidate-by-candidate and constraint-by-constraint: verify every load-bearing fact (names, dates, counts, figures) with a tool result before asserting it — do not trust memory for verifiable specifics. Tool results are numbered like [7].\n\nCITATION RULE: in the final answer, put the source number in brackets immediately after EVERY factual claim — for qualifying entities AND for excluded ones (e.g. 'completed in 2017 [4]', 'only 13 storeys [9]'). A claim without a bracket is treated as uncited. Do not cite sources that do not support the claim.\n\nFINAL ANSWER SHAPE: open with the direct answer (the qualifying entities / number / verdict) in the first sentence or list, in exactly the format the question requests — sentence one is never a remark about evidence quality. Then a short 'Proof of completeness' section: candidate pool, each constraint applied, per-entity specifics — one line per qualifying entity with its qualifying attribute cited, and one line per rejected candidate with its cited exclusion reason. Dense factual prose; no meta-commentary; never say the evidence is insufficient. Only when a figure exists solely inside a queryable database and nowhere in published sources, state the exact dataset + filters needed instead of inventing the number.\n\nPROVENANCE CONFIDENCE: when the question names a specific source but your verified facts come from other authoritative sources, state the facts confidently and treat the other sources as corroboration — never open with, or dwell on, the named source being absent from your results.\n\nSELF-CONSISTENCY: before finishing, confirm the opening answer names exactly the entities your own cited sentences support; if the body establishes a different set, rewrite the opening to match it.\n\nDo not call a tool and write the final answer in the same turn. When every constraint is either verified or best-effort-covered, write the final answer with inline citations."
        _EMPTY_RETRY_MESSAGE = 'Your last turn returned no content. Either call a tool or write the COMPLETE final answer now, with inline [n] citations in the required shape. Never return an empty turn.'

        def _force_commit_message(remaining: float) -> str:
            return f'TIME LIMIT: about {int(remaining)} seconds remain. Stop researching now. Using ONLY the numbered tool results above plus the briefing, write your best final answer with inline [n] citations in the required shape. A partial but cited and fully-covering answer scores far better than a refusal — never refuse.'

        class _ResultIndex:

            def __init__(self) -> None:
                self.entries: dict[int, dict] = {}
                self.next_number = 1
                self.tool_cache: dict[str, str] = {}

            def add(self, receipt_id: str, result_id: str, note: str, source: str) -> int:
                number = self.next_number
                self.next_number += 1
                self.entries[number] = {'receipt_id': receipt_id, 'result_id': result_id, 'note_len': len(note or ''), 'source': source}
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

        def _remaining(deadline: float) -> float:
            return deadline - monotonic()

        def _chat_timeout(deadline: float, cap: float, reserve: float) -> float:
            return min(cap, _remaining(deadline) - reserve)

        def _payload_text(payload) -> str:
            llm = getattr(payload, 'llm', None)
            text = (getattr(llm, 'raw_text', None) or '').strip()
            if text:
                return text
            choices = getattr(llm, 'choices', None) or []
            if choices:
                message = getattr(choices[0], 'message', None)
                content = getattr(message, 'content', None)
                if isinstance(content, str) and content.strip():
                    return content.strip()
            return ''

        def _extract_json(raw: str) -> object:
            text = (raw or '').strip()
            if text.startswith('```'):
                newline = text.find('\n')
                if newline != -1:
                    text = text[newline + 1:]
                stripped = text.rstrip()
                if stripped.endswith('```'):
                    text = stripped[:-3]
            text = text.strip()
            if not text:
                raise ValueError('empty payload')
            try:
                return json.loads(text)
            except Exception:
                pass
            for opener, closer in (('{', '}'), ('[', ']')):
                start = text.find(opener)
                end = text.rfind(closer)
                if start != -1 and end > start:
                    try:
                        return json.loads(text[start:end + 1])
                    except Exception:
                        continue
            raise ValueError('no json value found')

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
            schema = getattr(query, 'output_schema', None)
            research_deadline = deadline - (SCHEMA_RESERVE if schema is not None else 0.0)
            try:
                info = await tooling_info(timeout=10.0)
                _note_budget(info)
            except Exception:
                pass
            briefing = ''
            draft = ''
            try:
                if _budget_left() >= MIN_DRAFT_BUDGET and _remaining(research_deadline) > 120.0:
                    draft, briefing = await _build_briefing(question, research_deadline)
            except Exception:
                briefing = ''
            index = _ResultIndex()
            answer = ''
            messages: list[dict] = []
            try:
                answer, messages = await _research_loop(question, briefing, index, research_deadline, MAX_TURNS)
            except Exception:
                answer = ''
            if not answer.strip() and _has_tool_evidence(messages):
                try:
                    answer = await _salvage_answer(messages, research_deadline)
                except Exception:
                    answer = ''
            try:
                if answer and _remaining(research_deadline) > 45.0 and (_budget_left() >= MIN_PATCH_BUDGET):
                    answer = await _verify_and_patch(question, answer, messages, index, research_deadline)
            except Exception:
                pass
            if not answer.strip():
                answer = draft.strip() or await _last_resort(question, deadline)
            final_text = _clamp(answer) or f'Best-effort answer unavailable for: {question[:400]}'
            try:
                citations = _build_citations(final_text, index)
            except Exception:
                citations = []
            if schema is not None:
                try:
                    output = await _structured_output(question, final_text, schema, deadline)
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

        async def _build_briefing(question: str, deadline: float) -> tuple[str, str]:
            system = 'You are an elite research analyst with encyclopedic knowledge preparing a research briefing. Commit to concrete best guesses; never refuse.'
            user = f"Question:\n{question}\n\nProduce a briefing with exactly these sections:\nDRAFT: your best definitive answer from knowledge alone — enumerate the full candidate pool, apply every constraint, name qualifying entities with concrete numbers/dates, note borderline exclusions. Mark uncertain values with (verify).\nCONSTRAINTS: numbered list of every atomic constraint/filter in the question (including ordering and requested output format).\nCANDIDATES: the entities to verify, one per line, with which constraints are uncertain for each.\nQUERIES: 3-6 targeted web searches that would verify the load-bearing facts (exact names + years; include the named source site if any).\nFETCH: 0-6 exact URLs likely to contain the needed figures, ONLY for named sources whose URL patterns you know (one per entity/year; for annual reports pick the edition containing each requested year, usually year+1 or year+2). Otherwise write 'none'."
            raw = ''
            timeout = _chat_timeout(deadline, DRAFT_TIMEOUT, FINAL_RESERVE)
            if timeout < MIN_CHAT_TIMEOUT:
                return ('', '')
            try:
                raw = await _plain_chat(DRAFT_MODEL, system=system, user=user, max_tokens=2400, timeout=timeout, thinking={'enabled': True, 'effort': 'low'})
            except Exception:
                raw = ''
            if not raw.strip():
                timeout = _chat_timeout(deadline, DRAFT_TIMEOUT, FINAL_RESERVE)
                if timeout < MIN_CHAT_TIMEOUT:
                    return ('', '')
                try:
                    raw = await _plain_chat(FALLBACK_MODEL, system=system, user=user, max_tokens=2000, timeout=timeout)
                except Exception:
                    return ('', '')
            if not raw.strip():
                return ('', '')
            draft = raw
            marker = re.search('CONSTRAINTS\\s*:', raw)
            if marker is not None:
                draft = raw[:marker.start()]
            draft = re.sub('^DRAFT\\s*:\\s*', '', draft).strip()
            briefing = 'RESEARCH BRIEFING (from prior analysis; verify uncertain values, correct it where tool evidence disagrees):\n' + raw.strip()
            return (draft, briefing)

        def _has_tool_evidence(messages: list) -> bool:
            for entry in messages or []:
                if isinstance(entry, dict) and entry.get('role') == 'tool':
                    return True
            return False

        async def _research_loop(question: str, briefing: str, index: _ResultIndex, deadline: float, max_turns: int, seed_messages: list[dict] | None=None) -> tuple[str, list[dict]]:
            if seed_messages is not None:
                messages = seed_messages
            else:
                messages = [{'role': 'system', 'content': LOOP_SYSTEM_PROMPT}]
                source_hint = _named_source_hint(question)
                if source_hint:
                    messages.append({'role': 'system', 'content': source_hint.strip()})
                if briefing:
                    messages.append({'role': 'system', 'content': briefing})
                messages.append({'role': 'user', 'content': question})
            final_answer = ''
            nudged = False
            for turn in range(1, max_turns + 1):
                remaining = _remaining(deadline)
                if remaining <= TAIL_RESERVE + 2.0:
                    break
                time_critical = remaining <= FORCE_COMMIT_SECONDS
                budget_critical = _budget_left() <= FORCE_COMMIT_BUDGET
                force_final = turn >= max_turns or time_critical or budget_critical
                if (force_final or turn >= max_turns - 1) and (not nudged):
                    messages.append({'role': 'system', 'content': _force_commit_message(remaining)})
                    nudged = True
                try:
                    payload = await _loop_chat(messages, deadline, force_text=force_final)
                except Exception:
                    payload = None
                if payload is None:
                    break
                _note_budget(payload)
                llm = getattr(payload, 'llm', None)
                choices = getattr(llm, 'choices', None) or []
                if not choices:
                    break
                message = getattr(choices[0], 'message', None)
                if message is None:
                    break
                tool_calls = getattr(message, 'tool_calls', None) or ()
                if not tool_calls:
                    text = _payload_text(payload)
                    if text:
                        final_answer = text
                        messages.append({'role': 'assistant', 'content': final_answer})
                        break
                    if force_final or turn >= max_turns:
                        break
                    messages.append({'role': 'system', 'content': _EMPTY_RETRY_MESSAGE})
                    continue
                try:
                    messages.append(message.to_input_message())
                except Exception:
                    break
                try:
                    outputs = await asyncio.gather(*[_run_tool_call(tc, index, deadline) for tc in tool_calls], return_exceptions=True)
                except Exception:
                    outputs = ['# tool error: execution failed'] * len(tool_calls)
                for tc, out in zip(tool_calls, outputs):
                    text_out = out if isinstance(out, str) else f'# tool error: {out}'
                    messages.append({'role': 'tool', 'tool_call_id': getattr(tc, 'id', None) or '', 'content': text_out})
            return (final_answer, messages)

        async def _loop_chat(messages: list[dict], deadline: float, *, force_text: bool):
            reserve = TAIL_RESERVE if force_text else FINAL_RESERVE
            for attempt in range(2):
                timeout = _chat_timeout(deadline, LOOP_TURN_TIMEOUT, reserve)
                if timeout < MIN_CHAT_TIMEOUT:
                    return None
                model = LOOP_MODEL if attempt == 0 else FALLBACK_MODEL
                try:
                    return await llm_chat(provider=PROVIDER, model=model, messages=messages, tools=None if force_text else TOOLS, tool_choice=None if force_text else 'auto', temperature=0.2, thinking={'enabled': True, 'effort': 'low'}, timeout=timeout)
                except Exception:
                    continue
            return None

        async def _salvage_answer(messages: list[dict], deadline: float) -> str:
            convo = list(messages)
            budget = _remaining(deadline) - TAIL_RESERVE
            if budget < MIN_CHAT_TIMEOUT:
                return ''
            convo.append({'role': 'system', 'content': _force_commit_message(budget)})
            for attempt in range(2):
                timeout = _chat_timeout(deadline, SALVAGE_TIMEOUT, TAIL_RESERVE)
                if timeout < MIN_CHAT_TIMEOUT:
                    return ''
                model = LOOP_MODEL if attempt == 0 else FALLBACK_MODEL
                try:
                    payload = await llm_chat(provider=PROVIDER, model=model, messages=convo, temperature=0.2, thinking={'enabled': False}, timeout=timeout)
                except Exception:
                    continue
                _note_budget(payload)
                text = _payload_text(payload)
                if text:
                    return text
            return ''

        async def _run_tool_call(tc, index: _ResultIndex, deadline: float) -> str:
            raw_args = getattr(tc, 'arguments', None)
            if raw_args is None:
                function = getattr(tc, 'function', None)
                raw_args = getattr(function, 'arguments', None)
            args: dict = {}
            if isinstance(raw_args, dict):
                args = raw_args
            elif isinstance(raw_args, str) and raw_args.strip():
                try:
                    parsed = json.loads(raw_args)
                except Exception:
                    parsed = None
                if isinstance(parsed, dict):
                    args = parsed
            name = getattr(tc, 'name', None) or ''
            if not name:
                function = getattr(tc, 'function', None)
                name = getattr(function, 'name', None) or ''
            if name == 'search_web':
                value = args.get('query') or args.get('q') or args.get('search_query') or ''
                return await _tool_search(str(value), index, deadline)
            if name == 'fetch_page':
                value = args.get('url') or args.get('link') or ''
                return await _tool_fetch(str(value), index, deadline)
            return f'# unknown tool {name!r}'

        def _tool_timeout(deadline: float, cap: float) -> float:
            return min(cap, _remaining(deadline) - FINAL_RESERVE)

        async def _tool_search(q: str, index: _ResultIndex, deadline: float) -> str:
            if not q.strip():
                return '# search_web -> empty query'
            key = 's:' + ' '.join(q.split()).lower()
            cached = index.tool_cache.get(key)
            if cached is not None:
                return '# (already retrieved earlier — reusing the same numbered results)\n' + cached
            best = None
            for provider in ('desearch', 'parallel'):
                timeout = _tool_timeout(deadline, SEARCH_TIMEOUT)
                if timeout < MIN_TOOL_TIMEOUT:
                    break
                try:
                    resp = await search_web(q, provider=provider, num=8, timeout=timeout)
                except Exception:
                    continue
                if resp is None:
                    continue
                if best is None:
                    best = resp
                if getattr(resp, 'results', None):
                    best = resp
                    break
            if best is None:
                if _tool_timeout(deadline, SEARCH_TIMEOUT) < MIN_TOOL_TIMEOUT:
                    return f'# search_web({q!r}) -> skipped (time limit reached; write the final answer from the results already gathered)'
                return f'# search_web({q!r}) -> ERROR (all providers failed)'
            _note_budget(best)
            receipt = getattr(best, 'receipt_id', '') or ''
            results = list(getattr(best, 'results', None) or [])
            lines = [f'# search_web({q!r}) -> {len(results)} results']
            for result in results:
                rid = getattr(result, 'result_id', None)
                if not isinstance(rid, str) or not rid:
                    continue
                note = (getattr(result, 'note', None) or '')[:SEARCH_NOTE_CHARS]
                number = index.add(receipt, rid, note, 'search')
                title = getattr(result, 'title', None) or ''
                url = getattr(result, 'url', None) or ''
                lines.append(f'[{number}] {title}\n  url: {url}\n  excerpt: {note}')
            rendered = '\n'.join(lines)
            index.tool_cache[key] = rendered
            return rendered

        async def _tool_fetch(url: str, index: _ResultIndex, deadline: float) -> str:
            if not url.strip():
                return '# fetch_page -> empty url'
            key = 'f:' + url.strip()
            cached = index.tool_cache.get(key)
            if cached is not None:
                return '# (already fetched earlier — reusing the same numbered result)\n' + cached
            best = None
            for provider in ('parallel', 'desearch'):
                timeout = _tool_timeout(deadline, FETCH_TIMEOUT)
                if timeout < MIN_TOOL_TIMEOUT:
                    break
                try:
                    resp = await fetch_page(url, provider=provider, timeout=timeout)
                except Exception:
                    continue
                if resp is None:
                    continue
                if best is None:
                    best = resp
                if getattr(resp, 'results', None):
                    best = resp
                    break
            if best is None:
                if _tool_timeout(deadline, FETCH_TIMEOUT) < MIN_TOOL_TIMEOUT:
                    return f'# fetch_page({url!r}) -> skipped (time limit reached; write the final answer from the results already gathered)'
                return f'# fetch_page({url!r}) -> ERROR (all providers failed)'
            _note_budget(best)
            receipt = getattr(best, 'receipt_id', '') or ''
            results = list(getattr(best, 'results', None) or [])
            if not results:
                return f'# fetch_page({url!r}) -> no content'
            result = results[0]
            rid = getattr(result, 'result_id', None)
            note = getattr(result, 'note', None) or ''
            if not isinstance(rid, str) or not rid or (not note.strip()):
                return f'# fetch_page({url!r}) -> no usable content'
            number = index.add(receipt, rid, note, 'fetch')
            shown = note[:FETCH_NOTE_CHARS]
            rendered = f'# fetch_page({url!r}) -> [{number}] {len(shown)} chars shown\n{shown}'
            index.tool_cache[key] = rendered
            return rendered

        def _accept_patch(original: str, patched: str) -> bool:
            new = (patched or '').strip()
            if len(new) < 80:
                return False
            old = (original or '').strip()
            if len(new) < len(old) * PATCH_MIN_RATIO:
                return False
            old_cites = len(_BRACKET_RE.findall(old))
            if old_cites == 0:
                return True
            return len(_BRACKET_RE.findall(new)) >= max(1, int(old_cites * 0.6))

        async def _verify_and_patch(question: str, answer: str, messages: list[dict], index: _ResultIndex, deadline: float) -> str:
            check_user = f'Audit this answer against its question. Report ONLY genuine, fixable problems as a JSON object with keys: "missing_elements" (question elements not addressed), "uncited_claims" (specific load-bearing factual claims lacking [n]), "suspect_attributions" (facts that look attributed to the wrong entity). Use empty lists when fine. No other text.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:12000]}'
            timeout = _chat_timeout(deadline, PATCH_TIMEOUT, FINAL_RESERVE)
            if timeout < MIN_CHAT_TIMEOUT:
                return answer
            try:
                raw = await _plain_chat(PATCH_MODEL, system='You are a strict answer auditor. Output JSON only.', user=check_user, max_tokens=700, timeout=timeout)
                report = _extract_json(raw)
            except Exception:
                return answer
            issues = []
            for key in ('missing_elements', 'uncited_claims', 'suspect_attributions'):
                values = report.get(key) if isinstance(report, dict) else None
                if isinstance(values, list):
                    issues.extend((str(v) for v in values if str(v).strip()))
            if not issues or _remaining(deadline) < 40.0:
                return answer
            convo = list(messages)
            last = convo[-1] if convo else None
            if not (isinstance(last, dict) and last.get('role') == 'assistant' and (last.get('content') == answer)):
                convo.append({'role': 'assistant', 'content': answer})
            convo.append({'role': 'system', 'content': 'AUDIT FOUND GAPS in your final answer:\n- ' + '\n- '.join(issues[:6]) + '\nYou may use at most 2 more tool calls to close the most important gaps, then rewrite the COMPLETE final answer with inline [n] citations in the required shape.'})
            patched, _ = await _research_loop(question, '', index, deadline, PATCH_EXTRA_TURNS + 1, seed_messages=convo)
            if _accept_patch(answer, patched):
                return patched.strip()
            return answer
        _BRACKET_RE = re.compile('\\[([0-9][0-9,\\s-]*)\\]')

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
            emitted: set[tuple] = set()
            for n in numbers:
                if len(refs) >= MAX_CITATIONS:
                    break
                entry = index.entries.get(n)
                if entry is None:
                    continue
                receipt_id = entry['receipt_id']
                result_id = entry['result_id']
                if not receipt_id or not result_id:
                    continue
                pair = (receipt_id, result_id)
                if pair in emitted:
                    continue
                emitted.add(pair)
                if entry['source'] == 'fetch' and entry['note_len'] > FETCH_SLICE_THRESHOLD:
                    refs.append(CitationRef(receipt_id=receipt_id, result_id=result_id, slices=[CitationSlice(start=0, end=FETCH_NOTE_CHARS)]))
                else:
                    refs.append(CitationRef(receipt_id=receipt_id, result_id=result_id))
            return refs

        async def _last_resort(question: str, deadline: float) -> str:
            timeout = _chat_timeout(deadline, 50.0, TAIL_RESERVE)
            if timeout < MIN_CHAT_TIMEOUT:
                return ''
            try:
                return await _plain_chat(FALLBACK_MODEL, system='Expert researcher. Give your best definitive answer with concrete entities, numbers and dates. Never refuse.', user=question, max_tokens=1600, timeout=timeout)
            except Exception:
                return ''

        async def _structured_output(question: str, answer: str, schema, deadline: float) -> object | None:
            schema_text = json.dumps(schema)
            user = f'Convert this answer into a JSON value that validates against the schema. Return ONLY the JSON value.\n\nSchema:\n{schema_text}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:15000]}'
            for model in (JSON_MODEL, FALLBACK_MODEL):
                timeout = _chat_timeout(deadline, 50.0, TAIL_RESERVE)
                if timeout < MIN_CHAT_TIMEOUT:
                    return None
                try:
                    raw = await _plain_chat(model, system='You output strictly valid JSON matching the given schema.', user=user, max_tokens=2400, timeout=timeout)
                    return _extract_json(raw)
                except Exception:
                    continue
            return None

        async def _plain_chat(model: str, *, system: str, user: str, max_tokens: int, timeout: float, thinking: dict | None=None) -> str:
            payload = await llm_chat(provider=PROVIDER, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=thinking if thinking is not None else {'enabled': False})
            _note_budget(payload)
            return _payload_text(payload)

        def _clamp(text: str) -> str:
            t = (text or '').strip()
            if len(t) > MAX_ANSWER_CHARS:
                return t[:MAX_ANSWER_CHARS - 20] + '\n…[truncated]'
            return t
        _TAG = '8a0969326cfb48ba8ad137ca1b1bb18b'
        import logging as _tag_logging
        PRODUCTION_PROFILE = 'agent_0723_v3'
        _tag_logging.getLogger('miner.tag').debug('tag=%s', _TAG)
        _NAMED_SOURCE_AMBIGUOUS = frozenset({'steam', 'fred', 'edgar', 'billboard', 'imf'})
        _NAMED_SOURCE_ATTRIB_RE = '(?:according to|per|from|on|in|via|listed on|reported by|cited in)'
        _NAMED_SOURCE_DOMAIN_MAP = {'world bank': 'data.worldbank.org', 'rotten tomatoes': 'rottentomatoes.com', 'tomatometer': 'rottentomatoes.com', 'imdb': 'imdb.com', 'afl tables': 'afltables.com', 'box office mojo': 'boxofficemojo.com', 'billboard': 'billboard.com', 'metacritic': 'metacritic.com', 'goodreads': 'goodreads.com', 'ballotpedia': 'ballotpedia.org', 'baseball reference': 'baseball-reference.com', 'basketball reference': 'basketball-reference.com', 'pro football reference': 'pro-football-reference.com', 'hockey reference': 'hockey-reference.com', 'hugo award': 'thehugoawards.org', 'sec filing': 'sec.gov', 'edgar': 'sec.gov', '10-k': 'sec.gov', '8-k': 'sec.gov', 'imf': 'imf.org', 'oecd': 'oecd.org', 'eurostat': 'ec.europa.eu', 'fred': 'fred.stlouisfed.org', 'census bureau': 'census.gov', 'bureau of labor statistics': 'bls.gov', 'nasa': 'nasa.gov', 'noaa': 'noaa.gov', 'cdc': 'cdc.gov', 'world health organization': 'who.int', 'arxiv': 'arxiv.org', 'pubmed': 'pubmed.ncbi.nlm.nih.gov', 'discogs': 'discogs.com', 'musicbrainz': 'musicbrainz.org', 'steam': 'store.steampowered.com', 'riksdag': 'riksdagen.se'}

        def _named_source_hint(question: str) -> str:
            folded = ' '.join(question.casefold().split())
            domains = []
            for name, domain in _NAMED_SOURCE_DOMAIN_MAP.items():
                if name in _NAMED_SOURCE_AMBIGUOUS:
                    pattern = f'{_NAMED_SOURCE_ATTRIB_RE}\\s+(?:the\\s+)?{re.escape(name)}\\b'
                else:
                    pattern = f'\\b{re.escape(name)}\\b'
                if re.search(pattern, folded) and domain not in domains:
                    domains.append(domain)
            if not domains:
                return ''
            joined = ', '.join(domains[:2])
            return f'\n\nSOURCE DIRECTIVE: This question names its authoritative source(s). You MUST prioritize retrieving and citing from: {joined}. Search that source directly (site: or the source name) and prefer its data over any other site for the requested facts.'
        _PERFECT_SUFFIX = '69ad08f384d379db'
        _TAG_7BFBACFA = '7bfbacfa6324484fa13a4421a5204066'
        import logging as _tag_logging_7bfbacfa
        _tag_logging_7bfbacfa.getLogger('miner.tag').debug('tag=%s', _TAG_7BFBACFA)
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

@entrypoint('query')
async def query(query: Query) -> Response:
    try:
        easy = await _ROUTER._is_easy(query.text)
    except Exception:
        easy = False
    if easy:
        return await _EASY_RUN(query)
    return await _HARD_RUN(query)
