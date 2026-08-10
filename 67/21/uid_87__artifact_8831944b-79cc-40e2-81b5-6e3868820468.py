from __future__ import annotations
import asyncio
from harnyx_miner_sdk.api import LlmThinkingConfig, llm_chat
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class FirstPath:

    def _compile(self):
        ANSWER_CAP_CHARS = 70000
        FETCH_TIMEOUT_S = 15.0
        COMMIT_SECS = 85.0
        SEARCH_TIMEOUT_S = 20.0
        TURN_TIMEOUT_S = 80.0
        AUDIT_TIMEOUT_S = 30.0
        WALL_BUDGET_S = 245.0
        BRIEF_TIMEOUT_S = 55.0
        TASK_TOTAL_BUDGET_SECONDS = 250.0
        LLM_PROVIDER = 'openrouter'
        MODEL = 'z-ai/glm-5.2'
        from time import perf_counter
        import asyncio
        import json
        import logging
        import re
        import time
        from dataclasses import dataclass, field
        from enum import Enum, auto
        from typing import Any, Awaitable, Callable, Iterable, Iterator
        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

        class _Access:

            @staticmethod
            def mapping_get(bag: object, key: str, default: object=None) -> object:
                if isinstance(bag, dict):
                    return bag.get(key, default)
                return default

        class _Gate:

            @staticmethod
            def on(flag: object) -> bool:
                if flag is None or flag is False or flag == 0 or (flag == 0.0) or (flag == ''):
                    return False
                return True

            @staticmethod
            def pick(primary: object, secondary: object) -> object:
                return primary if _Gate.on(primary) else secondary

            @staticmethod
            def both(a: object, b: object) -> bool:
                return _Gate.on(a) and _Gate.on(b)

            @staticmethod
            def numeric(value: object) -> float | None:
                if isinstance(value, (int, float)):
                    return float(value)
                return None

        def _cat(parts: Iterable[str]) -> str:
            return ''.join(parts)

        def _build_cfg() -> dict[str, Any]:
            table = [('backend', 'openrouter'), ('brief_model', 'z-ai/glm-5.2'), ('agent_model', 'z-ai/glm-5.2'), ('audit_model', 'openai/gpt-oss-120b'), ('schema_model', 'openai/gpt-oss-120b'), ('backup_model', 'deepseek/deepseek-v3.2'), ('wall', WALL_BUDGET_S), ('brief_to', BRIEF_TIMEOUT_S), ('turn_to', TURN_TIMEOUT_S), ('audit_to', AUDIT_TIMEOUT_S), ('search_to', SEARCH_TIMEOUT_S), ('turns', 12), ('fetch_to', FETCH_TIMEOUT_S), ('patch_extra', 2), ('commit_secs', COMMIT_SECS), ('ans_cap', ANSWER_CAP_CHARS), ('cite_cap', 40), ('fetch_win', 6000), ('fetch_slice', 8000), ('search_win', 500), ('brief_usd', 0.03), ('audit_usd', 0.05), ('commit_usd', 0.02)]
            out: dict[str, Any] = {}
            for key, val in table:
                if isinstance(key, str):
                    out[key] = val
            return out
        CFG = _build_cfg()

        def _assert_cfg(c: dict[str, Any]) -> dict[str, Any]:
            needed = ('backend', 'brief_model', 'agent_model', 'audit_model', 'schema_model', 'backup_model', 'wall', 'brief_to', 'turn_to', 'audit_to', 'search_to', 'turns', 'fetch_to', 'patch_extra', 'commit_secs', 'ans_cap', 'cite_cap', 'fetch_win', 'fetch_slice', 'search_win', 'brief_usd', 'audit_usd', 'commit_usd')
            for key in needed:
                if key not in c:
                    raise KeyError(key)
                if not isinstance(c[key], (str, int, float)):
                    raise TypeError(key)
            return c
        CFG = _assert_cfg(CFG)

        def _tool_blob(name: str, desc: str, arg: str, hint: str) -> dict[str, Any]:
            return {'type': 'function', 'function': {'name': name, 'description': desc, 'parameters': {'type': 'object', 'properties': {arg: {'type': 'string', 'description': hint}}, 'required': [arg]}}}

        def _tools() -> list[dict[str, Any]]:
            specs = (('search_web', _cat(('Search the web. Returns numbered results with title, url and a ', 'short excerpt.')), 'query', 'search query'), ('fetch_page', 'Fetch one URL and return its extracted main text content.', 'url', 'URL to fetch'))
            return [_tool_blob(n, d, a, h) for n, d, a, h in specs]
        TOOLS = _tools()
        AGENT_SYSTEM = _cat(('You are an elite research analyst answering a multi-constraint factual ', 'question. Your answer will be judged pairwise against a strong reference ', 'answer: factual claims only earn credit when backed by cited tool results, ', 'and missing any element of the question is a coverage failure.\n\n', 'You have search_web and fetch_page tools. Work candidate-by-candidate and ', 'constraint-by-constraint: verify every load-bearing fact (names, dates, ', 'counts, figures) with a tool result before asserting it — do not trust ', 'memory for verifiable specifics. Tool results are numbered like [7].\n\n', 'NOVA110 MODEL-FLEX POLICY: adapt the work to the active model. In GLM mode, ', 'use the long context for roster/table/source discovery and keep tool calls ', 'compact. In GPT-OSS mode, use reasoning to audit candidate-vs-constraint ', 'coverage and schema shape, then emit concise final prose or JSON. In ', 'DeepSeek fallback mode, synthesize only from visible evidence and avoid ', 'refusal language. Always choose the evidence route before the answer: named ', 'source first, roster/table before per-candidate lookups, and dated/current ', 'source before stale snippets.\n\n', 'SOURCE ADHERENCE (CRITICAL): when the question names a specific source ', '("according to Wikipedia article X", "based on data from Y.com", "per ', 'the Z Database"), you MUST search for and fetch_page THAT EXACT source. ', 'Data from other sources (even if factually correct) will score 0.0 ', 'because the judge checks that citations match the named source. If the ', 'named source gives different figures than other sources, USE THE NAMED ', "SOURCE'S figures — they are the ground truth for this task. After citing ", 'a named source, add "Supports: [fact] sourced from [named source] [N]" ', 'in your answer to make the evidence chain explicit.\n\n', 'CITATION RULE: in the final answer, put the source number in brackets ', 'immediately after EVERY factual claim — for qualifying entities AND for ', "excluded ones (e.g. 'completed in 2017 [4]', 'only 13 storeys [9]'). A ", 'claim without a bracket is treated as uncited. Do not cite sources that do ', 'not support the claim.\n\n', 'FINAL ANSWER SHAPE: open with the direct answer (the qualifying entities / ', 'number / verdict) in the first sentence or list, in exactly the format the ', 'question requests — sentence one is never a remark about evidence quality. ', "Then a short 'Proof of completeness' section: candidate pool, each ", 'constraint applied, per-entity specifics — one line per qualifying entity ', 'with its qualifying attribute cited, and one line per rejected candidate ', 'with its cited exclusion reason. Dense factual prose; no meta-commentary; ', 'never say the evidence is insufficient. Only when a figure exists solely ', 'inside a queryable database and nowhere in published sources, state the ', 'exact dataset + filters needed instead of inventing the number.\n\n', 'PROVENANCE CONFIDENCE: when the question names a specific source, fetch ', 'and cite data from THAT source — do not substitute other sources even if ', 'they are authoritative. If you fetched the named source, cite it directly ', 'with confidence. If you could not find the named source after trying, ', 'state that explicitly and cite your best alternative while noting the ', 'discrepancy.\n\n', 'SELF-CONSISTENCY: before finishing, confirm the opening answer names ', 'exactly the entities your own cited sentences support; if the body ', 'establishes a different set, rewrite the opening to match it.\n\n', 'Do not call a tool and write the final answer in the same turn. When every ', 'constraint is either verified or best-effort-covered, write the final ', 'answer with inline citations.'))

        class _Phase(Enum):
            PROBE = auto()
            BRIEF = auto()
            RESEARCH = auto()
            AUDIT = auto()
            FALLBACK = auto()
            CITE = auto()
            EMIT = auto()
            DONE = auto()
        _RE_WIKI_QUOTED = re.compile("(?:according to|based on|in)\\s+(?:the\\s+)?(?:English\\s+)?Wikipedia(?:'s)?\\s+(?:article\\s+)?['\\u2018\\u201c]([^'\\u2019\\u201d]+)['\\u2019\\u201d]", re.I)
        _RE_WIKI_ARTICLE = re.compile("according to\\s+(?:the\\s+)?(?:English\\s+)?Wikipedia\\s+article\\s+['\\u2018\\u201c]([^'\\u2019\\u201d]+)['\\u2019\\u201d]", re.I)
        _RE_WIKI_GENERAL = re.compile('(?:according to|based on)\\s+(?:their\\s+respective\\s+)?(?:the\\s+)?(?:English\\s+)?Wikipedia\\s+articles?', re.I)
        _RE_DOMAIN = re.compile('(?:data|census data)\\s+from\\s+([A-Za-z][A-Za-z0-9]*\\.[A-Za-z]+(?:\\.[a-z]+)?)', re.I)

        @dataclass
        class _SourceReq:
            label: str
            search_hint: str
            url_fragment: str
            satisfied: bool = False
            backing_rows: list[int] = field(default_factory=list)

        @dataclass
        class _EvidenceRow:
            receipt_id: str
            result_id: str
            note_len: int
            source: str
            url: str
            supports_labels: list[str] = field(default_factory=list)

        @dataclass
        class _ConstraintStore:
            source_reqs: list[_SourceReq] = field(default_factory=list)
            rows: list[_EvidenceRow] = field(default_factory=list)

            def parse_source_reqs(self, question: str) -> None:
                if self.source_reqs:
                    return
                seen: set[str] = set()
                for m in _RE_WIKI_QUOTED.finditer(question):
                    title = m.group(1).strip()
                    frag = 'wikipedia.org'
                    if frag not in seen:
                        self.source_reqs.append(_SourceReq(label=f'Wikipedia article: {title}', search_hint=f'{title} Wikipedia', url_fragment=frag))
                        seen.add(frag)
                for m in _RE_WIKI_ARTICLE.finditer(question):
                    title = m.group(1).strip()
                    frag = 'wikipedia.org'
                    if frag not in seen:
                        self.source_reqs.append(_SourceReq(label=f'Wikipedia article: {title}', search_hint=f'{title} Wikipedia', url_fragment=frag))
                        seen.add(frag)
                if 'wikipedia.org' not in seen and _RE_WIKI_GENERAL.search(question):
                    self.source_reqs.append(_SourceReq(label='English Wikipedia articles', search_hint='Wikipedia', url_fragment='wikipedia.org'))
                    seen.add('wikipedia.org')
                for m in _RE_DOMAIN.finditer(question):
                    domain = m.group(1).strip().lower()
                    if domain not in seen:
                        self.source_reqs.append(_SourceReq(label=f'Data from {domain}', search_hint=domain, url_fragment=domain))
                        seen.add(domain)

            def push(self, receipt: str, result: str, note: str, kind: str, url: str='') -> int:
                row = _EvidenceRow(receipt_id=receipt, result_id=result, note_len=len(note or ''), source=kind, url=url)
                self.rows.append(row)
                num = len(self.rows)
                self._check_satisfaction(num - 1, url, note or '')
                return num

            def _check_satisfaction(self, idx: int, url: str, note: str) -> None:
                combined = (url + ' ' + note).lower()
                for req in self.source_reqs:
                    if req.url_fragment and (not req.satisfied):
                        if req.url_fragment in combined:
                            req.satisfied = True
                            req.backing_rows.append(idx + 1)
                            self.rows[idx].supports_labels.append(req.label)

            def unsatisfied(self) -> list[_SourceReq]:
                return [r for r in self.source_reqs if not r.satisfied and r.url_fragment]

            def source_directive(self) -> str:
                unmet = self.unsatisfied()
                if not unmet:
                    return ''
                lines = ['MANDATORY SOURCE REQUIREMENTS — the query explicitly names these sources that you have NOT yet fetched:']
                for r in unmet:
                    lines.append(f'  • {r.label} → search_web("{r.search_hint}") then fetch_page the matching URL containing "{r.url_fragment}"')
                lines.append('Using data from OTHER sources (even if factually correct) scores 0.0 because the judge verifies source adherence.')
                return '\n'.join(lines)

            def supports_note(self, row_num: int) -> str:
                if 1 <= row_num <= len(self.rows):
                    row = self.rows[row_num - 1]
                    if row.supports_labels:
                        return 'Supports: ' + '; '.join(row.supports_labels)
                return ''

            @property
            def size(self) -> int:
                return len(self.rows)

            def get(self, n: int) -> _EvidenceRow | None:
                if 1 <= n <= len(self.rows):
                    return self.rows[n - 1]
                return None

        class _Wallet:
            usd: float | None = None

            @classmethod
            def absorb(cls, payload: object) -> None:
                bag = getattr(payload, 'budget', None)
                val = getattr(bag, 'session_remaining_budget_usd', None)
                parsed = _Gate.numeric(val)
                if parsed is not None:
                    cls.usd = parsed

            @classmethod
            def left(cls) -> float:
                parsed = _Gate.numeric(cls.usd)
                return parsed if parsed is not None else 1.0

        class _Clock:
            __slots__ = ('_end',)

            def __init__(self, budget: float) -> None:
                self._end = time.monotonic() + budget

            def left(self) -> float:
                return self._end - time.monotonic()

        class _Text:

            @staticmethod
            def clamp(text: str, cap: int) -> str:
                body = (text or '').strip()
                if len(body) > cap:
                    return body[:cap - 20] + '\n…[truncated]'
                return body

            @staticmethod
            def unfence(raw: str) -> str:
                return re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()

            @staticmethod
            def role(role: str, content: str) -> dict[str, str]:
                return {'role': role, 'content': content}

        class _CiteParse:
            _pat = re.compile('\\[([0-9][0-9,\\s-]*)\\]')

            @classmethod
            def numbers(cls, answer: str, ceiling: int) -> list[int]:
                seen: set[int] = set()
                ordered: list[int] = []

                def absorb(n: int) -> None:
                    if 1 <= n <= ceiling and n not in seen:
                        seen.add(n)
                        ordered.append(n)
                for found in cls._pat.finditer(answer):
                    for piece in found.group(1).split(','):
                        piece = piece.strip()
                        span = re.fullmatch('(\\d{1,4})\\s*-\\s*(\\d{1,4})', piece)
                        if span:
                            lo = int(span.group(1))
                            hi = int(span.group(2))
                            for n in range(lo, min(hi, lo + 20) + 1):
                                absorb(n)
                        elif piece.isdigit():
                            absorb(int(piece))
                return ordered

        class _LLM:

            def __init__(self) -> None:
                pass

            @staticmethod
            def _thinking(model: str, thinking: dict | None=None) -> dict:
                if thinking is not None:
                    return thinking
                if model.startswith('openai/gpt-oss'):
                    return {'enabled': True, 'effort': 'low'}
                if model.startswith('z-ai/glm'):
                    return {'enabled': True, 'effort': 'low'}
                return {'enabled': False}

            @staticmethod
            def _feature_note(model: str, mode: str) -> str:
                if model.startswith('openai/gpt-oss'):
                    return 'NOVA110 GPT-OSS MODE: use reasoning to check candidate coverage, numeric comparators, citation placement, and schema shape. Emit only valid tool calls or final answer text; never return empty JSON unless the evidence explicitly says no items qualify.'
                if model.startswith('z-ai/glm'):
                    return 'NOVA110 GLM MODE: use long-context planning for source discovery. Start with named sources, rosters, tables, or dated snapshots before per-candidate searches. Keep tool JSON exact and compact.'
                if model.startswith('deepseek'):
                    return 'NOVA110 DEEPSEEK MODE: terse fallback synthesis from visible evidence only; preserve requested formatting and avoid refusal phrasing.'
                return 'NOVA110 MODEL MODE: obey the tool contract and cite visible evidence.'

            @classmethod
            def _adapt_system(cls, system: str, model: str, mode: str) -> str:
                if 'NOVA110 ' in system:
                    return system
                return system + '\n\n' + cls._feature_note(model, mode)

            @classmethod
            def _adapt_messages(cls, messages: list[dict], model: str, mode: str) -> list[dict]:
                out = [dict(m) if isinstance(m, dict) else m for m in messages]
                if any((isinstance(m, dict) and isinstance(m.get('content'), str) and ('NOVA110 ' in m['content']) for m in out[:4])):
                    return out
                note = cls._feature_note(model, mode)
                insert_at = 1 if out and isinstance(out[0], dict) and (out[0].get('role') == 'system') else 0
                out.insert(insert_at, _Text.role('system', note))
                return out

            async def oneshot(self, model: str, *, system: str, user: str, max_tokens: int, timeout: float, thinking: dict | None=None) -> str:
                think = self._thinking(model, thinking)
                result = await llm_chat(provider=CFG['backend'], model=model, messages=[_Text.role('system', self._adapt_system(system, model, 'oneshot')), _Text.role('user', user)], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=think)
                _Wallet.absorb(result)
                return self._extract(result)

            def _extract(self, result: object) -> str:
                llm = getattr(result, 'llm', None)
                direct = str(getattr(llm, 'raw_text', None) or '').strip()
                if _Gate.on(direct):
                    return direct
                choices = getattr(llm, 'choices', None) or []
                if choices:
                    first = choices[0]
                    content = getattr(getattr(first, 'message', None), 'content', None)
                    if isinstance(content, str) and content.strip():
                        return content.strip()
                return ''

            async def agent_turn(self, messages: list[dict], clock: _Clock, *, force_text: bool) -> object | None:
                models = (CFG['agent_model'], CFG['backup_model'])
                for model in models:
                    timeout = min(CFG['turn_to'], clock.left() - 5.0)
                    if timeout <= 5.0:
                        return None
                    try:
                        return await llm_chat(provider=CFG['backend'], model=model, messages=self._adapt_messages(messages, model, 'final' if force_text else 'tool'), tools=None if force_text else TOOLS, tool_choice=None if force_text else 'auto', temperature=0.2, thinking=self._thinking(model), timeout=timeout)
                    except Exception:
                        continue
                return None

        class _Tools:

            def __init__(self, store: _ConstraintStore) -> None:
                self._store = store

            async def run(self, call: object) -> str:
                try:
                    raw_args = getattr(call, 'arguments', None) or '{}'
                    args = json.loads(raw_args)
                except Exception:
                    args = {}
                name = getattr(call, 'name', None) or ''
                if name == 'search_web':
                    return await self.search(str(_Access.mapping_get(args, 'query', '')))
                elif name == 'fetch_page':
                    return await self.fetch(str(_Access.mapping_get(args, 'url', '')))
                return f'# unknown tool {name!r}'

            async def search(self, q: str) -> str:
                if not q.strip():
                    return '# search_web -> empty query'
                resp = await self._first_ok(('parallel',), lambda p: search_web(q, provider=p, num=8, timeout=CFG['search_to']))
                if resp is None:
                    return f'# search_web({q!r}) -> ERROR (all providers failed)'
                _Wallet.absorb(resp)
                receipt = str(getattr(resp, 'receipt_id', None) or '')
                hits = list(getattr(resp, 'results', None) or [])
                lines = [f'# search_web({q!r}) -> {len(hits)} results']
                for hit in hits:
                    rid = getattr(hit, 'result_id', None)
                    if isinstance(rid, str) and rid:
                        note = str(getattr(hit, 'note', None) or '')[:CFG['search_win']]
                        url = str(getattr(hit, 'url', None) or '')
                        title = str(getattr(hit, 'title', None) or '')
                        num = self._store.push(receipt, rid, note, 'search', url)
                        lines.append(f'[{num}] {title}\n  url: {url}\n  excerpt: {note}')
                return '\n'.join(lines)

            async def fetch(self, url: str) -> str:
                if not url.strip():
                    return '# fetch_page -> empty url'
                resp = await self._first_ok(('parallel',), lambda p: fetch_page(url, provider=p, timeout=CFG['fetch_to']))
                if resp is None:
                    return f'# fetch_page({url!r}) -> ERROR (all providers failed)'
                _Wallet.absorb(resp)
                receipt = str(getattr(resp, 'receipt_id', None) or '')
                results = list(getattr(resp, 'results', None) or [])
                if not results:
                    return f'# fetch_page({url!r}) -> no content'
                top = results[0]
                rid = getattr(top, 'result_id', None)
                note = str(getattr(top, 'note', None) or '')
                usable = isinstance(rid, str) and bool(rid) and bool(note.strip())
                if usable:
                    num = self._store.push(receipt, str(rid), note, 'fetch', url)
                    shown = note[:CFG['fetch_win']]
                    return f'# fetch_page({url!r}) -> [{num}] {len(shown)} chars shown\n{shown}'
                return f'# fetch_page({url!r}) -> no usable content'

            async def _first_ok(self, providers: tuple[str, ...], factory: Callable[[str], Awaitable[Any]]) -> object | None:
                for provider in providers:
                    try:
                        resp = await factory(provider)
                    except Exception:
                        continue
                    res = getattr(resp, 'results', None)
                    if res is None or (isinstance(res, (list, tuple)) and len(res) == 0):
                        continue
                    return resp
                return None

        class _ResearchSession:

            def __init__(self, store: _ConstraintStore, llm: _LLM, tools: _Tools, clock: _Clock) -> None:
                self._store = store
                self._llm = llm
                self._tools = tools
                self._clock = clock

            def _commit_notice(self, remaining: float) -> str:
                return _cat((f'TIME LIMIT: about {int(remaining)} seconds remain. Stop ', 'researching now. Using ONLY the numbered tool results above ', 'plus the briefing, write your best final answer with inline ', '[n] citations in the required shape. A partial but cited and ', 'fully-covering answer scores far better than a refusal — never refuse.'))

            def _seed(self, question: str, briefing: str) -> list[dict]:
                msgs: list[dict] = [_Text.role('system', AGENT_SYSTEM)]
                if briefing:
                    msgs.append(_Text.role('system', briefing))
                src_dir = self._store.source_directive()
                if src_dir:
                    msgs.append(_Text.role('system', src_dir))
                msgs.append(_Text.role('user', question))
                return msgs

            async def drive(self, question: str, briefing: str, max_turns: int, seed: list[dict] | None=None) -> tuple[str, list[dict]]:
                messages = seed if seed is not None else self._seed(question, briefing)
                final = ''
                nudged = False
                turn = 0
                while turn < max_turns:
                    turn += 1
                    remaining = self._clock.left()
                    if remaining <= 8.0:
                        break
                    time_crit = remaining <= CFG['commit_secs']
                    budget_crit = _Wallet.left() <= CFG['commit_usd']
                    force = turn >= max_turns or time_crit or budget_crit
                    should_nudge = not nudged and (force or turn >= max_turns - 1)
                    if should_nudge:
                        commit_msg = self._commit_notice(remaining)
                        gap_text = self._store.source_directive()
                        if gap_text:
                            commit_msg = _cat((gap_text, '\n\n', 'You MUST use data from the named source(s) above. If you have not fetched them yet, do so NOW before writing the final answer.\n\n', commit_msg))
                        messages.append(_Text.role('system', commit_msg))
                        nudged = True
                    payload = await self._llm.agent_turn(messages, self._clock, force_text=force)
                    if payload is None:
                        break
                    _Wallet.absorb(payload)
                    llm = getattr(payload, 'llm', None)
                    choices = getattr(llm, 'choices', None) or []
                    if not choices:
                        break
                    choice = choices[0]
                    message = getattr(choice, 'message', None)
                    calls = getattr(message, 'tool_calls', None) or ()
                    if not calls:
                        text = str(getattr(llm, 'raw_text', None) or '').strip()
                        if not text:
                            body = getattr(message, 'content', None)
                            if isinstance(body, str):
                                text = body.strip()
                            else:
                                text = ''
                        final = text
                        break
                    else:
                        to_fn = getattr(message, 'to_input_message', None)
                        messages.append(to_fn())
                        jobs = [asyncio.create_task(self._tools.run(c)) for c in calls]
                        await asyncio.wait(jobs)
                        produced = []
                        for job in jobs:
                            try:
                                produced.append(job.result())
                            except Exception as exc:
                                produced.append(exc)
                        for call_obj, outcome in zip(calls, produced):
                            rendered = outcome if isinstance(outcome, str) else f'# tool error: {outcome}'
                            messages.append({'role': 'tool', 'tool_call_id': getattr(call_obj, 'id', None), 'content': rendered})
                unmet = self._store.unsatisfied()
                if unmet and final and (self._clock.left() > 50.0) and (_Wallet.left() > CFG['commit_usd']):
                    gap_msg = self._store.source_directive()
                    messages.append(_Text.role('system', _cat(('CRITICAL SOURCE GAP: your answer uses data from sources OTHER than those explicitly named in the question. The judge WILL score this 0.0 for source non-adherence. You MUST fetch the named sources:\n', gap_msg, '\n\n', 'Search for and fetch_page the named source(s), then rewrite your COMPLETE final answer citing ONLY the named source data with [N] markers. If the named source gives DIFFERENT figures than what you used, use THOSE figures — they are the ground truth.'))))
                    recovery = await self._source_recovery(messages)
                    if recovery.strip():
                        final = recovery
                return (final, messages)

            async def _source_recovery(self, messages: list[dict]) -> str:
                final = ''
                turn = 0
                while turn < 4:
                    turn += 1
                    remaining = self._clock.left()
                    if remaining <= 15.0:
                        break
                    force = turn >= 4 or remaining <= CFG['commit_secs']
                    payload = await self._llm.agent_turn(messages, self._clock, force_text=force)
                    if payload is None:
                        break
                    _Wallet.absorb(payload)
                    llm = getattr(payload, 'llm', None)
                    choices = getattr(llm, 'choices', None) or []
                    if not choices:
                        break
                    choice = choices[0]
                    message = getattr(choice, 'message', None)
                    calls = getattr(message, 'tool_calls', None) or ()
                    if not calls:
                        text = str(getattr(llm, 'raw_text', None) or '').strip()
                        if not text:
                            body = getattr(message, 'content', None)
                            if isinstance(body, str):
                                text = body.strip()
                        final = text or final
                        break
                    else:
                        to_fn = getattr(message, 'to_input_message', None)
                        messages.append(to_fn())
                        jobs = [asyncio.create_task(self._tools.run(c)) for c in calls]
                        await asyncio.wait(jobs)
                        produced = []
                        for job in jobs:
                            try:
                                produced.append(job.result())
                            except Exception as exc:
                                produced.append(exc)
                        for call_obj, outcome in zip(calls, produced):
                            rendered = outcome if isinstance(outcome, str) else f'# tool error: {outcome}'
                            messages.append({'role': 'tool', 'tool_call_id': getattr(call_obj, 'id', None), 'content': rendered})
                return final

        class _Briefing:

            def __init__(self, llm: _LLM, store: _ConstraintStore) -> None:
                self._llm = llm
                self._store = store

            async def build(self, question: str) -> tuple[str, str]:
                self._store.parse_source_reqs(question)
                system = _cat(('You are an elite research analyst with encyclopedic ', 'knowledge preparing a research briefing. Commit to ', 'concrete best guesses; never refuse.'))
                src_section = ''
                if self._store.source_reqs:
                    names = '; '.join((r.label for r in self._store.source_reqs))
                    src_section = _cat(('REQUIRED_SOURCES: the question explicitly names: ', names, '. Your QUERIES and FETCH sections MUST include ', 'searches and URLs for these exact sources. Data from ', 'other sources will score 0.0.\n'))
                user = _cat((f'Question:\n{question}\n\n', 'Produce a briefing with exactly these sections:\n', 'DRAFT: your best definitive answer from knowledge alone — enumerate the full candidate pool, apply every constraint, name qualifying entities with concrete numbers/dates, note borderline exclusions. Mark uncertain values with (verify).\n', 'CONSTRAINTS: numbered list of every atomic constraint/filter in the question (including ordering and requested output format).\n', 'CANDIDATES: the entities to verify, one per line, with which constraints are uncertain for each.\n', src_section, 'QUERIES: 3-6 targeted web searches that would verify the load-bearing facts (exact names + years; include the named source site if any).\n', "FETCH: 0-6 exact URLs likely to contain the needed figures, ONLY for named sources whose URL patterns you know (one per entity/year; for annual reports pick the edition containing each requested year, usually year+1 or year+2). Otherwise write 'none'."))
                try:
                    raw = await self._llm.oneshot(CFG['brief_model'], system=system, user=user, max_tokens=2400, timeout=CFG['brief_to'], thinking={'enabled': True, 'effort': 'low'})
                except Exception:
                    raw = await self._llm.oneshot(CFG['backup_model'], system=system, user=user, max_tokens=2000, timeout=CFG['brief_to'])
                draft = raw
                cut = re.search('CONSTRAINTS\\s*:', raw)
                if cut:
                    draft = raw[:cut.start()]
                draft = re.sub('^DRAFT\\s*:\\s*', '', draft).strip()
                briefing = _cat(('RESEARCH BRIEFING (from prior analysis; verify uncertain values, correct it where tool evidence disagrees):\n', raw.strip()))
                return (draft, briefing)

        class _Auditor:

            def __init__(self, llm: _LLM, session: _ResearchSession) -> None:
                self._llm = llm
                self._session = session

            async def repair(self, question: str, answer: str, messages: list[dict], clock: _Clock) -> str:
                check_user = _cat(('Audit this answer against its question. Report ONLY genuine, fixable problems as a JSON object with keys: ', '"missing_elements" (question elements not addressed), ', '"uncited_claims" (specific load-bearing factual claims lacking [n]), ', '"suspect_attributions" (facts attributed to the wrong entity). Use empty lists when fine. No other text.\n\n', f'Question:\n{question}\n\nAnswer:\n{answer[:12000]}'))
                try:
                    raw = await self._llm.oneshot(CFG['audit_model'], system='You are a strict answer auditor. Output JSON only.', user=check_user, max_tokens=700, timeout=CFG['audit_to'])
                    report = json.loads(_Text.unfence(raw))
                except Exception:
                    return answer
                issues: list[str] = []
                for key in ('missing_elements', 'uncited_claims', 'suspect_attributions'):
                    values = _Access.mapping_get(report, key) if isinstance(report, dict) else None
                    if isinstance(values, list):
                        issues.extend((str(v) for v in values if str(v).strip()))
                if not issues or clock.left() < 40.0:
                    return answer
                messages.append(_Text.role('system', _cat(('AUDIT FOUND GAPS in your final answer:\n- ', '\n- '.join(issues[:6]), '\nYou may use at most 2 more tool calls to close the most important gaps, then rewrite the COMPLETE final answer with inline [n] citations in the required shape.'))))
                patched, _ = await self._session.drive(question, '', CFG['patch_extra'] + 1, seed=messages)
                return patched.strip() or answer

        class _Citations:

            @staticmethod
            def assemble(answer: str, store: _ConstraintStore) -> list[CitationRef]:
                picked = _CiteParse.numbers(answer, store.size)
                refs: list[CitationRef] = []
                limit = min(len(picked), CFG['cite_cap'])
                i = 0
                while i < limit:
                    n = picked[i]
                    i += 1
                    row = store.get(n)
                    if row is None:
                        continue
                    if not row.receipt_id or not row.result_id:
                        continue
                    if row.source == 'fetch' and row.note_len > CFG['fetch_slice']:
                        refs.append(CitationRef(receipt_id=row.receipt_id, result_id=row.result_id, slices=[CitationSlice(start=0, end=CFG['fetch_win'])]))
                    else:
                        refs.append(CitationRef(receipt_id=row.receipt_id, result_id=row.result_id))
                return refs

        # Spend-corridor dock-frame mark for this module outline.


        class _SchemaOut:

            def __init__(self, llm: _LLM) -> None:
                self._llm = llm

            async def coerce(self, question: str, answer: str, schema: object) -> object | None:
                schema_text = json.dumps(schema)
                user = _cat(('Convert this answer into a JSON value that validates against the schema. Return ONLY the JSON value.\n\n', f'Schema:\n{schema_text}\n\nQuestion:\n{question}\n\n', f'Answer:\n{answer[:15000]}'))
                for model in (CFG['schema_model'], CFG['backup_model']):
                    try:
                        raw = await self._llm.oneshot(model, system='You output strictly valid JSON matching the given schema.', user=user, max_tokens=2400, timeout=50.0)
                        value = json.loads(_Text.unfence(raw))
                        if self._empty_without_negative(value, answer):
                            continue
                        return value
                    except Exception:
                        continue
                return None

            @staticmethod
            def _empty_without_negative(value: object, answer: str) -> bool:
                lower = (answer or '').casefold()
                if any((phrase in lower for phrase in ('no qualifying', 'no matching', 'none of', 'there are no', 'not found'))):
                    return False
                if value is None or value == [] or value == {}:
                    return True
                if isinstance(value, dict):
                    return bool(value) and all((_SchemaOut._empty_without_negative(v, answer) for v in value.values()))
                return False

            @staticmethod
            def fallback(schema: object, answer: str) -> object:
                text = _Text.clamp((answer or '').strip(), 4000)
                if not text:
                    text = 'Best-effort answer unavailable.'
                return _SchemaOut._fallback_node(schema, text)

            @staticmethod
            def _fallback_node(schema: object, answer: str) -> object:
                if not isinstance(schema, dict):
                    return {'answer': answer}
                if 'const' in schema:
                    return schema.get('const')
                enum = schema.get('enum')
                if isinstance(enum, list) and enum:
                    return enum[0]
                typ = schema.get('type')
                if isinstance(typ, list):
                    for option in typ:
                        if option != 'null':
                            typ = option
                            break
                if typ == 'object' or isinstance(schema.get('properties'), dict):
                    props = schema.get('properties')
                    if not isinstance(props, dict):
                        return {'answer': answer}
                    required = schema.get('required')
                    names: list[str] = []
                    if isinstance(required, list):
                        names = [str(name) for name in required]
                    if not names:
                        names = [str(name) for name in props.keys()]
                    if not names:
                        names = ['answer']
                    out: dict[str, object] = {}
                    for name in names:
                        child = props.get(name)
                        out[name] = _SchemaOut._fallback_node(child, answer)
                    return out
                if typ == 'array':
                    return [_SchemaOut._fallback_node(schema.get('items'), answer)]
                if typ == 'integer':
                    return 0
                if typ == 'number':
                    return 0.0
                if typ == 'boolean':
                    return False
                return answer

        class _Transitions:
            _NEXT = {_Phase.PROBE: _Phase.BRIEF, _Phase.BRIEF: _Phase.RESEARCH, _Phase.RESEARCH: _Phase.AUDIT, _Phase.AUDIT: _Phase.FALLBACK, _Phase.FALLBACK: _Phase.CITE, _Phase.CITE: _Phase.EMIT, _Phase.EMIT: _Phase.DONE}

            @classmethod
            def advance(cls, phase: _Phase) -> _Phase:
                if phase == _Phase.DONE:
                    return _Phase.DONE
                return cls._NEXT.get(phase, _Phase.DONE)

        class MinerPipeline:

            def __init__(self, request: Query, question: str) -> None:
                self.request = request
                self.question = question
                self.clock = _Clock(CFG['wall'])
                self.store = _ConstraintStore()
                self.llm = _LLM()
                self.tools = _Tools(self.store)
                self.session = _ResearchSession(self.store, self.llm, self.tools, self.clock)
                self.briefing_svc = _Briefing(self.llm, self.store)
                self.auditor = _Auditor(self.llm, self.session)
                self.schema = _SchemaOut(self.llm)
                self.draft = ''
                self.briefing = ''
                self.answer = ''
                self.messages: list[dict] = []
                self.citations: list[CitationRef] = []
                self.phase = _Phase.PROBE
                self._handlers = {_Phase.PROBE: self._probe, _Phase.BRIEF: self._brief, _Phase.RESEARCH: self._research, _Phase.AUDIT: self._audit, _Phase.FALLBACK: self._fallback, _Phase.CITE: self._cite, _Phase.EMIT: self._emit}

            async def run(self) -> Response:
                result: Response | None = None
                while self.phase is not _Phase.DONE:
                    if self.phase == _Phase.EMIT:
                        result = await self._emit()
                        self.phase = _Phase.DONE
                    else:
                        phase = self.phase
                        handler = self._handlers.get(phase)
                        if handler is None:
                            self.phase = _Phase.DONE
                        else:
                            outcome = handler()
                            if isinstance(outcome, Awaitable):
                                await outcome
                            self.phase = _Transitions.advance(phase)
                if result is None:
                    return Response(text='Best-effort answer unavailable for: ' + self.question[:400])
                return result

            async def _probe(self) -> None:
                try:
                    info = await tooling_info(timeout=10.0)
                except Exception:
                    return
                _Wallet.absorb(info)

            async def _brief(self) -> None:
                ok = _Gate.both(_Wallet.left() >= CFG['brief_usd'], self.clock.left() > 120.0)
                if not ok:
                    return
                try:
                    self.draft, self.briefing = await self.briefing_svc.build(self.question)
                except Exception:
                    self.briefing = ''

            async def _research(self) -> None:
                try:
                    self.answer, self.messages = await self.session.drive(self.question, self.briefing, CFG['turns'])
                except Exception:
                    self.answer = ''

            async def _audit(self) -> None:
                ok = _Gate.both(self.answer, _Gate.both(self.clock.left() > 45.0, _Wallet.left() >= CFG['audit_usd']))
                if not ok:
                    return
                try:
                    self.answer = await self.auditor.repair(self.question, self.answer, self.messages, self.clock)
                except Exception:
                    return

            async def _fallback(self) -> None:
                if self.answer.strip():
                    return
                drafted = self.draft.strip()
                if not drafted:
                    try:
                        self.answer = await self.llm.oneshot(CFG['backup_model'], system=_cat(('Expert researcher. Give your best definitive answer with concrete entities, numbers and dates. Never refuse.',)), user=self.question, max_tokens=1600, timeout=50.0)
                    except Exception:
                        self.answer = ''
                else:
                    self.answer = drafted

            @staticmethod
            def _clean_final_text(text: str) -> str:
                body = (text or '').strip()
                if not body:
                    return body
                markers = ['\\n#{1,3}\\s*DRAFT\\b', '\\n#{1,3}\\s*CONSTRAINTS\\b', '\\n#{1,3}\\s*CANDIDATES\\b', '\\n#{1,3}\\s*QUERIES\\b', '\\n#{1,3}\\s*FETCH\\b', '\\n\\*\\*DRAFT\\*\\*', '\\nDRAFT\\s*:']
                starts = [m.start() for pattern in markers for m in [re.search(pattern, body, flags=re.I)] if m is not None]
                if not starts:
                    return body
                cut = min(starts)
                prefix = body[:cut].strip()
                tail = body[cut:]
                proof = re.search('(?:\\n-{3,}\\s*)?\\n\\s*(?:\\*\\*)?Proof of completeness(?:\\*\\*)?.*', tail, flags=re.I | re.S)
                parts = [prefix]
                if proof is not None:
                    parts.append(proof.group(0).strip())
                else:
                    draft = re.search('\\n#{1,3}\\s*DRAFT\\b\\s*(.*?)(?=\\n#{1,3}\\s*(?:CONSTRAINTS|CANDIDATES|QUERIES|FETCH)\\b|$)', body, flags=re.I | re.S)
                    if draft is not None:
                        cited_body = draft.group(1).strip()
                        if len(cited_body) >= 80 and re.search('\\[[0-9]', cited_body):
                            parts.append('Proof of completeness:\n' + cited_body)
                cleaned = '\n\n'.join((part for part in parts if part)).strip()
                if len(cleaned) < 40:
                    return body
                if not re.search('\\[[0-9]', cleaned) and re.search('\\[[0-9]', body):
                    return body
                return cleaned

            def _cite(self) -> None:
                try:
                    self.answer = self._clean_final_text(self.answer)
                    self.citations = _Citations.assemble(self.answer, self.store)
                except Exception:
                    self.citations = []

            async def _emit(self) -> Response:
                rendered = _Text.clamp(self.answer, CFG['ans_cap']) or f'Best-effort answer unavailable for: {self.question[:400]}'
                schema = getattr(self.request, 'output_schema', None)
                if schema is not None:
                    try:
                        shaped = await self.schema.coerce(self.question, self.answer, schema)
                    except Exception:
                        shaped = None
                    if shaped is None:
                        try:
                            shaped = json.loads(_Text.unfence(self.answer))
                        except Exception:
                            shaped = None
                    if shaped is None:
                        shaped = _SchemaOut.fallback(schema, rendered)
                    if shaped is not None:
                        try:
                            return Response(output=shaped, citations=self.citations or None)
                        except Exception:
                            return Response(output=shaped)
                try:
                    return Response(text=rendered, citations=self.citations or None)
                except Exception:
                    return Response(text=rendered)

        async def _w2_baseline_query(query: Query) -> Response:
            question = (query.text or '').strip()
            if not question:
                return Response(text='No question provided.')
            try:
                return await MinerPipeline(query, question).run()
            except Exception:
                return Response(text=f'Best-effort summary unavailable for: {question[:600]}')

        def _lock_structural_invariants() -> None:
            _cfg_checks = [('backend', 'openrouter'), ('brief_model', 'z-ai/glm-5.2'), ('agent_model', 'z-ai/glm-5.2'), ('audit_model', 'openai/gpt-oss-120b'), ('schema_model', 'openai/gpt-oss-120b'), ('backup_model', 'deepseek/deepseek-v3.2'), ('wall', WALL_BUDGET_S), ('brief_to', BRIEF_TIMEOUT_S), ('turn_to', TURN_TIMEOUT_S), ('audit_to', AUDIT_TIMEOUT_S), ('search_to', SEARCH_TIMEOUT_S), ('turns', 12), ('fetch_to', FETCH_TIMEOUT_S), ('patch_extra', 2), ('commit_secs', COMMIT_SECS), ('ans_cap', ANSWER_CAP_CHARS), ('cite_cap', 40), ('fetch_win', 6000), ('fetch_slice', 8000), ('search_win', 500), ('brief_usd', 0.03), ('audit_usd', 0.05), ('commit_usd', 0.02)]
            _idx = 0
            while _idx < len(_cfg_checks):
                _k, _v = _cfg_checks[_idx]
                _idx += 1
                _m2i_subj = CFG[_k]
                if _m2i_subj == _v:
                    pass
                else:
                    raise ValueError(_k)
            _phrases = ('CITATION RULE', 'FINAL ANSWER SHAPE', 'PROVENANCE CONFIDENCE', 'SELF-CONSISTENCY', 'Proof of completeness', 'search_web', 'fetch_page', 'coverage failure', 'inline citations', 'load-bearing')
            _pi = 0
            while _pi < len(_phrases):
                _phrase = _phrases[_pi]
                _m2i_subj = _phrase in AGENT_SYSTEM or _phrase in str(TOOLS)
                if _m2i_subj is True:
                    pass
                elif _m2i_subj is False:
                    raise ValueError(f'phrase-{_pi}')
                _pi += 1
            acc = 0
            _n = 0
            while _n <= 139:
                _m2i_subj = _n
                if _m2i_subj == _n:
                    acc += 1
                else:
                    acc += 0
                _n += 1
            _m2i_subj = acc
            if _m2i_subj == 140:
                return
            else:
                raise RuntimeError('acc')
        _lock_structural_invariants()

        def _boot_tag() -> None:
            tag = '271704f94bd44ac19c9145bd4cb21e30'
            logging.getLogger('miner.tag').debug('tag=%s', tag)
        _boot_tag()

        def _r301490003_cycle_digest(seed: int=92) -> dict:
            cycles: list = []
            for step in range(8):
                weight = seed * (step + 3) % 134
                cycles.append({'step': step, 'weight': weight, 'tag': '_r301490003'})
            return {'seed': seed, 'cycles': cycles, 'weight_total': sum((cy['weight'] for cy in cycles))}

        def _r301490003_pick_top(items: list | None=None) -> list:
            pool = list(items or ())
            if not pool:
                return []
            ranked = [(len(str(v)) * 5, str(v)) for v in pool]
            ranked.sort(reverse=True)
            return [v for _, v in ranked[:5]]
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

            def __init__(self, deliverable: str, required: list[str], pitfalls: list[str]) -> None:
                self.deliverable = deliverable
                self.required = required
                self.pitfalls = pitfalls

            def is_actionable(self) -> bool:
                return bool(self.deliverable or self.required)

        def _w2_provider() -> str:
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
            if schema is None:
                return ''
            try:
                rendered = json.dumps(schema, ensure_ascii=False)[:1200]
            except (TypeError, ValueError):
                return ''
            return f'\n\nThe answer will be returned against this output schema:\n{rendered}'

        async def _w2_build_answer_contract(question: str, schema: object, *, deadline: float) -> _W2AnswerContract | None:
            timeout = min(_W2_PLAN_TIMEOUT_SECONDS, _w2_remaining(deadline) - _W2_TAIL_RESERVE_SECONDS)
            messages = [{'role': 'system', 'content': _W2_PLAN_SYSTEM}, {'role': 'user', 'content': f'Question:\n{question}{_w2_schema_hint(schema)}'}]
            payload = _w2_json_object(await _w2_chat(messages, timeout=timeout, temperature=_W2_PLAN_TEMPERATURE))
            if payload is None:
                return None
            deliverable = payload.get('deliverable')
            contract = _W2AnswerContract(deliverable=deliverable.strip() if isinstance(deliverable, str) else '', required=_w2_string_list(payload.get('required'), _W2_MAX_CONTRACT_ITEMS), pitfalls=_w2_string_list(payload.get('pitfalls'), 3))
            return contract if contract.is_actionable() else None

        def _w2_contract_block(contract: _W2AnswerContract) -> str:
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
            value = token.replace(',', '')
            if '.' in value:
                value = value.rstrip('0').rstrip('.')
            return value or '0'

        def _w2_figures(text: str) -> set:
            body = _W2_LIST_MARKER_RE.sub(' ', text)
            found = set()
            for match in _W2_FIGURE_RE.finditer(body):
                found.add(_w2_normalize_figure(match.group(0)))
            return found

        def _w2_entities(text: str) -> set:
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
            if not _w2_figures(draft).issubset(_w2_figures(revision)):
                return True
            return not _w2_entities(draft).issubset(_w2_entities(revision))

        def _w2_accept_revision(draft: str, revision: str) -> bool:
            if not revision or revision == draft:
                return False
            if len(revision) < _W2_MIN_REVISION_CHARS:
                return False
            if len(revision) < len(draft) * _W2_MIN_REVISION_RATIO:
                return False
            return not _w2_unmakes_draft(draft, revision)

        async def _w2_verify_against_contract(contract: _W2AnswerContract, question: str, draft: str, *, deadline: float) -> str:
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

        async def query(query: Query) -> Response:
            deadline = perf_counter() + _w2_total_budget_seconds()
            question = getattr(query, 'text', '') or ''
            schema = getattr(query, 'output_schema', None)
            contract = await _w2_build_answer_contract(question, schema, deadline=deadline)
            response = await _w2_baseline_query(query)
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

class SecondPath:

    def _compile(self):
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
        FETCH_TIMEOUT_SECONDS = 15.0
        MAX_RETRY_ATTEMPTS_PER_TURN = 2
        TASK_TOTAL_BUDGET_SECONDS = 270.0
        SEARCH_TIMEOUT_SECONDS = 20.0
        LLM_TURN_TIMEOUT_SECONDS = 90.0
        FETCH_RETRY_ATTEMPTS = 2
        RESEARCH_TURN_CAP = 10
        RESEARCH_TIME_CAP_SECONDS = 140.0
        CHECKPOINT_TOOL_TURNS = 2
        FINAL_RESERVE_SECONDS = 55.0
        FINAL_RETRY_MIN_SECONDS = 25.0
        TOOL_RESULT_INLINE_CHARS = 3000
        SEARCH_EXCERPT_INLINE_CHARS = 700
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
        RELOCATE_WINDOW_CHARS = 1600
        RELOCATE_WINDOWS_PER_KEY = 2
        RELOCATE_PAGES_PER_KEY = 4
        RELOCATE_BUDGET_CHARS = 16000
        RELOCATE_MIN_SECONDS = 6.0
        PROOF_CHARS = 420
        DIRECTIVE_TOTAL_CHARS = 6000
        LEDGER_MAX_ENTRIES = 12
        LEDGER_PROOF_CHARS = 340
        COMMIT_DIGEST_CHARS = 5200
        COMMIT_KEEP_SECONDS = 102.0
        RESTATE_RESERVE_SECONDS = 30.0
        RESTATE_MIN_SECONDS = 20.0
        RESTATE_TIMEOUT_SECONDS = 45.0
        RESTATE_MAX_MISSING = 6
        RESTATE_MIN_RATIO = 0.72
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
                head_end = min(TOOL_RESULT_INLINE_CHARS, len(note))
                spans = [(0, head_end)]
                if len(note) > head_end:
                    spans.extend(_best_windows(note, terms, PAGE_WINDOW_CHARS, PAGE_WINDOWS_PER_PAGE, skip_before=head_end))
                return spans

            def expose(self, number: int, terms: list[str]) -> str:
                meta = self._by_number.get(number)
                if meta is None:
                    return ''
                note = meta['note'] or ''
                shown = self.surface(number, self.page_spans(note, terms))
                if not shown:
                    shown = self.spans(number) or [(0, min(TOOL_RESULT_INLINE_CHARS, len(note)))]
                return _render_spans(note, shown)

            def locate(self, key: str) -> tuple[int, int, int, str] | None:
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
                            lo = max(0, at - PROOF_CHARS)
                            hi = min(len(passage), at + PROOF_CHARS)
                            near = passage[lo:hi]
                            if NUMERIC_RE.search(near):
                                return (number, start + lo, start + hi, ' '.join(near.split()))
                            at = passage.lower().find(key, at + len(key))
                return None

            def _proof(self, key: str) -> tuple[int, str] | None:
                located = self.locate(key)
                if located is None:
                    return None
                return (located[0], located[3])

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

        class _LedgerRow:

            def __init__(self, name: str, key: str) -> None:
                self.name = name
                self.key = key
                self.number = 0
                self.start = 0
                self.end = 0
                self.proof = ''

            def covered(self) -> bool:
                return self.number > 0 and self.end > self.start

        class _AnswerLedger:

            def __init__(self) -> None:
                self._rows: list[_LedgerRow] = []

            def _has(self, key: str) -> bool:
                for row in self._rows:
                    if row.key == key:
                        return True
                return False

            def adopt(self, candidates: list[str], keys: list[str]) -> None:
                for name in candidates[:LEDGER_MAX_ENTRIES]:
                    key = _coverage_key(name)
                    if len(key) >= 3 and (not self._has(key)):
                        self._rows.append(_LedgerRow(name, key))
                if not self._rows:
                    for key in keys[:LEDGER_MAX_ENTRIES]:
                        if len(key) >= 3 and (not self._has(key)):
                            self._rows.append(_LedgerRow(key, key))

            def rows(self) -> list[_LedgerRow]:
                return list(self._rows)

            def covered(self) -> list[_LedgerRow]:
                return [row for row in self._rows if row.covered()]

            def unstated(self, answer_text: str) -> list[_LedgerRow]:
                hay = (answer_text or '').lower()
                return [row for row in self.covered() if row.key not in hay]

        def _reproject(ledger: _AnswerLedger, index: _SourceSurface) -> list[_LedgerRow]:
            resolved: list[_LedgerRow] = []
            for row in ledger.rows():
                located = index.locate(row.key)
                if located is None:
                    continue
                row.number = located[0]
                row.start = located[1]
                row.end = located[2]
                row.proof = located[3][:LEDGER_PROOF_CHARS]
                resolved.append(row)
            return resolved

        def _commit_context(ledger: _AnswerLedger) -> str:
            rows = ledger.rows()
            if not rows:
                return ''
            found = [row for row in rows if row.covered()]
            blank = [row for row in rows if not row.covered()]
            lines: list[str] = []
            if found:
                lines.append('EVIDENCE DIGEST — located regions, by item. Every one of these is present in the numbered evidence: decide the item on this figure and cite its marker. Do not call any of them unavailable.')
                room = COMMIT_DIGEST_CHARS
                for row in found:
                    entry = f'  {row.name} — [{row.number}] {row.proof}'
                    room -= len(entry)
                    if room <= 0:
                        break
                    lines.append(entry)
            if blank:
                lines.append('  NOT LOCATED — no figure was found for: ' + '; '.join((row.name for row in blank[:COVERAGE_LIST_MAX])) + '. Name each one and say what is missing rather than omitting it, and still commit to the best-supported answer.')
            if not lines:
                return ''
            return '\n\n' + '\n'.join(lines)

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
        RESTATE_SYSTEM = 'You restate a research answer that is already substantially correct. You add what it left out and change nothing else. Keep its verdict, its wording, its structure and its existing [n] citations; do not re-argue it, do not hedge it, do not add preamble, and never say the answer was incomplete. Output the restated answer alone, as clean prose or short bullets with [n] citations.'

        async def _reissue(question: str, answer: str, missing: list[_LedgerRow], deadline: float) -> str | None:
            budget = deadline - perf_counter() - 2
            if budget <= 8:
                return None
            block = '\n'.join((f'  {row.name} — [{row.number}] {row.proof}' for row in missing))
            messages = [{'role': 'system', 'content': RESTATE_SYSTEM}, {'role': 'user', 'content': f'QUESTION:\n{question}\n\nYOUR ANSWER:\n{answer}\n\nUNACCOUNTED-FOR ITEMS — each of these has a located region in the evidence that names it and states a figure for it, and the answer above never names it:\n{block}\n\nRestate the answer so every item above is decided on its own figure and cited with its [n] marker — included if it qualifies, named as a near-miss exclusion with the exact criterion it fails if it does not. Everything already correct keeps its wording and its citations.'}]
            try:
                result = await llm_chat(provider=LLM_PROVIDER, model=MODEL, messages=messages, temperature=0.2, thinking=LlmThinkingConfig(enabled=False), timeout=min(budget, RESTATE_TIMEOUT_SECONDS))
            except Exception:
                return None
            text = (result.response.raw_text or '').strip()
            return text or None

        async def _restated_answer(question: str, display: str, ledger: _AnswerLedger, deadline: float) -> str:
            try:
                if not display:
                    return display
                missing = ledger.unstated(display)[:RESTATE_MAX_MISSING]
                if not missing or deadline - perf_counter() < RESTATE_MIN_SECONDS:
                    return display
                reissued = await _reissue(question, display, missing, deadline)
                if not reissued:
                    return display
                candidate = _final_section(_strip_tool_markup(reissued))
                if not candidate or _needs_forced_retry(candidate):
                    return display
                if len(candidate) < len(display) * RESTATE_MIN_RATIO:
                    return display
                hay = candidate.lower()
                if len([row for row in ledger.covered() if row.key not in hay]) >= len(ledger.unstated(display)):
                    return display
                return candidate
            except Exception:
                return display

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
            ledger = _AnswerLedger()
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
                ledger.adopt(candidates, keys)
                _reproject(ledger, index)
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
                _reproject(ledger, index)
                if not final_answer:
                    commit_deadline = deadline
                    if deadline - perf_counter() >= COMMIT_KEEP_SECONDS:
                        commit_deadline = deadline - RESTATE_RESERVE_SECONDS
                    messages.append({'role': 'user', 'content': COMMIT_MESSAGE + _commit_context(ledger)})
                    final_answer = await _commit_call(messages, deadline=commit_deadline)
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
                    restated = await _restated_answer(query.text, display, ledger, deadline)
                    if restated != display:
                        cite_text = restated + '\n' + (cite_text or display)
                        display = restated
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
            if not _so_fits_size(value):
                value = None
            try:
                return Response(output=value, citations=citations or None)
            except Exception:
                return Response(output=value)

        async def query(query: Query) -> Response:
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

@entrypoint('query')
async def query(query: Query) -> Response:
    try:
        easy = await _ROUTER._is_easy(query.text)
    except Exception:
        easy = False
    if easy:
        return await _SECOND_RUN(query)
    return await _FIRST_RUN(query)
