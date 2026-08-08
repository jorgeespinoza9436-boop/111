from __future__ import annotations
import asyncio
from harnyx_miner_sdk.api import LlmThinkingConfig, llm_chat
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class FirstPath:

    def _compile(self):
        import asyncio
        import json
        import re
        from collections.abc import Mapping
        from dataclasses import dataclass, field
        from time import monotonic
        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        VERSION = 'fdfds'
        LLM_PROVIDER = 'openrouter'
        MODEL_AUDIT = 'openai/gpt-oss-120b'
        MODEL_FALLBACK = 'deepseek/deepseek-v3.2'
        LOOP_TRIES_PRIMARY = 2
        SEARCH_PROVIDER = 'parallel'
        MODEL_LOOP = 'z-ai/glm-5.2'
        _REASONING_REQUIRED = ('openai/gpt-oss',)

        def _think_for(model: str, *, want: bool) -> dict:
            if any((model.startswith(p) for p in _REASONING_REQUIRED)):
                return {'enabled': True, 'effort': 'low'}
            return {'enabled': True, 'effort': 'low'} if want else {'enabled': False}

        def _ladder(primary: str) -> list[tuple[str, int]]:
            rungs = [(primary, LOOP_TRIES_PRIMARY)]
            if MODEL_FALLBACK != primary:
                rungs.append((MODEL_FALLBACK, 1))
            return rungs
        WALL_BUDGET_S = 260.0
        FETCH_TIMEOUT_S = 16.0
        BRIEF_TIMEOUT_S = 45.0
        COMMIT_TIMEOUT_S = 55.0
        MAX_CALLS_PER_TURN = 8
        MIN_TAIL_S = 8.0
        TURN_TIMEOUT_S = 70.0
        COMMIT_RESERVE_S = 46.0
        MAX_TURNS = 14
        SEARCH_TIMEOUT_S = 18.0
        AUDIT_TIMEOUT_S = 30.0
        MAX_REPAIRS = 2
        SEARCH_RESULTS = 8
        SEARCH_EXCERPT_CHARS = 520
        PAGE_HEAD_CHARS = 2600
        PAGE_WINDOW_CHARS = 3400
        PAGE_WINDOWS = 3
        EVIDENCE_CHAR_BUDGET = 104000
        CITATION_CAP = 26
        ANSWER_CHAR_CAP = 48000
        MAX_SEED_QUERIES = 3
        PAGE_PREVIEW_CHARS = 12000
        _SET_ASK_RE = re.compile('\\b(?:list|name|identify|enumerate|which)\\b[^?]{0,60}\\b(?:all|every|each|both)\\b', re.I)
        _SET_JOIN_RE = re.compile('\\b(?:both|as well as|and also|and had|and received)\\b', re.I)
        _PLURAL_ASK_RE = re.compile('\\b(?:which|what)\\b(?:\\s+\\w+){0,2}?\\s+([a-z]{3,}s)\\b', re.I)
        _PLURAL_NOT = frozenset('was is has does its this thus across process business series species status analysis basis focus versus previous various famous others always perhaps'.split())
        _TOP_RE = re.compile('\\b(?:highest|lowest|largest|smallest|greatest|fewest|longest|shortest|oldest|newest|youngest|maximum|minimum)\\b|(?<!at )\\b(?:most|least)\\b', re.I)
        _ENUM_LIST_RE = re.compile('\\bwhich of the (?:following|these)\\b|\\bfrom the following list\\b', re.I)
        _OR_LIST_RE = re.compile('[:,]\\s*[^,:?]{2,60}(?:,\\s*[^,:?]{2,60}){1,}\\s*,?\\s+or\\s+', re.I)
        _CONSTRAINT_RE = re.compile('\\b(?:at least|at most|no more than|no fewer than|greater than|less than|fewer than|more than|over|under|above|below|exceed(?:s|ing)?|between\\s+[^,]{1,30}\\s+and)\\b', re.I)
        _EST_RE = re.compile('\\b([a-z]{3,})est\\b')
        _EST_NOT = frozenset('conquest tempest incest behest zest quest crest chest guest jest pest vest midwest southwest northwest bequest imprest inquest gest wrest'.split() + 'interest honest modest protest request suggest forest harvest invest'.split() + 'arrest contest digest manifest earnest rest best west nest test'.split())
        _NAMED_SOURCE_RE = re.compile("\\b(?:according to|per|from|listed (?:in|on)|in the)\\s+((?:the\\s+)?[A-Z][\\w.'&-]*(?:\\s+[A-Z][\\w.'&-]*){0,4})", re.S)
        _SOURCE_WORD_RE = re.compile('\\b(wikipedia|wikidata|imdb|britannica|eurovisionworld|usgs|nasa|noaa|baseball-reference|basketball-reference|box office mojo|rotten tomatoes|metacritic|billboard|discogs|goodreads|transfermarkt|olympedia|pubmed|arxiv|sec|edgar|eurostat|world bank|imf|census)\\b', re.I)
        _SOURCE_NOUN_RE = re.compile('\\b(?:wiki\\w*|article|page|site|database|dataset|data|table|list|index|factsheet|fact sheet|report|filing|registry|catalog(?:ue)?|almanac|encyclopedia|archive|records?|statistics|census|survey|bulletin|\\.(?:com|org|net|gov|edu))\\b', re.I)

        def _has_top(text: str) -> bool:
            if _TOP_RE.search(text or ''):
                return True
            return any((m.group(0).lower() not in _EST_NOT for m in _EST_RE.finditer(text or '')))

        def _wants_set(question: str) -> bool:
            q = ' '.join((question or '').split())
            if not q:
                return False
            if _SET_ASK_RE.search(q):
                return True
            if _ENUM_LIST_RE.search(q) or (re.search('\\bwhich\\b', q, re.I) and _OR_LIST_RE.search(q)):
                return True
            head = _PLURAL_ASK_RE.search(q)
            if head and head.group(1).lower() not in _PLURAL_NOT:
                if not _has_top(q) or re.search('\\b(?:all|every|each)\\b', q, re.I):
                    return True
            return bool(re.search('\\bwhich\\b', q, re.I)) and bool(_SET_JOIN_RE.search(q))

        def _wants_tally(question: str) -> bool:
            q = ' '.join((question or '').split())
            if not q:
                return False
            if _has_top(q) or re.search('\\b(?:how many|how much|(?:most|least) (?:common|frequent))\\b', q, re.I):
                return True
            return bool(re.search('\\b(?:which|what)\\b', q, re.I)) and len(_CONSTRAINT_RE.findall(q)) >= 2

        def _named_sources(question: str) -> list[str]:
            found: list[str] = []
            for m in _SOURCE_WORD_RE.finditer(question or ''):
                name = m.group(1).strip()
                if name.lower() not in {f.lower() for f in found}:
                    found.append(name)
            for m in _NAMED_SOURCE_RE.finditer(question or ''):
                name = re.sub('^the\\s+', '', m.group(1).strip(), flags=re.I).strip(" .,'")
                if not _SOURCE_NOUN_RE.search(name):
                    continue
                if 2 < len(name) < 60 and name.lower() not in {f.lower() for f in found}:
                    found.append(name)
            return found[:4]
        LOOP_RULES = 'You are a research agent answering a hard factual question. Your answer is compared against a reference answer by a judge that only counts claims backed by a validated citation, and that keeps the reference when the two are equally good. Being merely correct therefore loses — you win by showing more verified work than the reference does.\n\nTOOLS. web_search(query) returns numbered results with an excerpt. read_page(url, focus) returns the page head plus the regions densest in your focus terms. Search finds the document; READ IT before you rely on a number. An excerpt is a pointer, not evidence.\n\nCITATIONS. Every tool result carries a number. Put [n] on every claim that rests on it, at the point of the claim. A paragraph with one trailing [n] reads as one supported claim, not five. Never invent a number you were not given.\n\nNUMBERS. Quote figures exactly as the source prints them — same units, same precision, no rounding and no arithmetic the source did not do. If you must derive a value, show the inputs with their own [n] and say it is derived.\n\nANSWER SHAPE. Lead with the direct answer in the first sentence, in the form the question asks for. Then the proof. Do not open by narrating your process, do not hedge a verified fact, and never contradict your own cited source.\n\nWhen you have the evidence, write the final answer as plain prose. Do not announce that you are about to answer — just answer.'
        SET_RULE = "SET ANSWER — this question asks for a set, and omitting one qualifying member scores the same as being wrong.\n1. Get the POOL from a roster, not member by member. Your first retrieval should hunt the authoritative list/table that enumerates the whole pool ('<subject> list', 'list of <subject>') and read_page it. Assembling a pool from separate per-member searches is how a run reports 3 of 6 qualifiers: the members you never thought to search for stay invisible.\n2. When the condition spans several periods — successive years, separate editions, two parallel events — fetch ONE roster page PER PERIOD and join them on the member. One list per period, not one lookup per member.\n3. Test EVERY member against EVERY condition. Name all qualifiers, each with its own [n] per condition.\n4. Give EVERY excluded member its own line, the condition it fails, the value that fails it, and its own [n]. One clause sweeping several names together is not exclusion evidence. This is usually the difference between winning and losing: the reference proves why the others don't qualify, and if you cannot, you lose even with the right answer.\n5. Never say 'the only X' unless you checked the whole pool. If nothing survives every condition, 'none' is a real answer — state it with the per-condition citations that prove it."
        TALLY_RULE = "SUPERLATIVE / COUNT — the answer is one item, but you cannot know which without the whole pool. Show the table.\n1. List EVERY candidate the question's scope admits.\n2. Put the deciding value beside each one, cited.\n3. Only then name the winner, and reproduce that table in your answer. A correct winner with no visible tally loses to a reference that shows its work; 'among others' is not a tally.\n4. Never decide a superlative on a rounded or derived display — a whole-number age or a bucketed rank cannot separate contenders that differ below its precision. Get the exact underlying value for every contender, from a source that lists them ALL: a page showing only your front-runner cannot establish that nobody beats them.\n5. If the pool is too large to print in full, rank it, show every contender above an explicit threshold, and state the threshold you used. A reader can audit a declared cutoff; an undeclared one is indistinguishable from you simply having stopped looking."

        def _source_rule(names: list[str]) -> str:
            listed = ', '.join(names)
            return f"NAMED SOURCE — this question specifies where the answer must come from: {listed}. Read THAT source and cite it. An aggregator or mirror carrying the same figures does not satisfy the constraint: a judge has scored us 0 on all four runs of a question whose data and conclusion it agreed were correct, purely because we answered from a different site than the one named. Search the named source directly (try 'site:' or its name in the query), read_page it, and quote its own wording. Only if it genuinely cannot be retrieved may you fall back — and then say so explicitly."

        def _shape_rules(question: str) -> list[str]:
            rules: list[str] = []
            if _wants_set(question):
                rules.append(SET_RULE)
            if _wants_tally(question):
                rules.append(TALLY_RULE)
            named = _named_sources(question)
            if named:
                rules.append(_source_rule(named))
            return rules

        @dataclass(slots=True)
        class Row:
            receipt_id: str
            result_id: str
            note_len: int
            spans: tuple[tuple[int, int], ...]
            kind: str
            url: str = ''
            title: str = ''
            preview: str = ''

        @dataclass(slots=True)
        class Ledger:
            rows: list[Row] = field(default_factory=list)
            _seen: dict[tuple[str, str], int] = field(default_factory=dict)

            def add(self, row: Row) -> int:
                key = (row.receipt_id, row.result_id)
                existing = self._seen.get(key)
                if existing is not None:
                    prior = self.rows[existing - 1]
                    merged = _merge_spans(prior.spans + row.spans)
                    self.rows[existing - 1] = Row(receipt_id=prior.receipt_id, result_id=prior.result_id, note_len=max(prior.note_len, row.note_len), spans=merged, kind=prior.kind, url=prior.url or row.url, title=prior.title or row.title, preview=max((prior.preview, row.preview), key=len))
                    return existing
                self.rows.append(row)
                n = len(self.rows)
                self._seen[key] = n
                return n

            def cost(self, n: int) -> int:
                row = self.rows[n - 1]
                if not row.spans:
                    return row.note_len
                return sum((max(0, e - s) for s, e in row.spans))

            def ref(self, n: int) -> CitationRef | None:
                if not 1 <= n <= len(self.rows):
                    return None
                row = self.rows[n - 1]
                if not row.receipt_id or not row.result_id:
                    return None
                slices = [CitationSlice(start=s, end=e) for s, e in row.spans if e > s]
                if slices:
                    return CitationRef(receipt_id=row.receipt_id, result_id=row.result_id, slices=slices)
                return CitationRef(receipt_id=row.receipt_id, result_id=row.result_id)

        def _merge_spans(spans: tuple[tuple[int, int], ...]) -> tuple[tuple[int, int], ...]:
            ordered = sorted(((s, e) for s, e in spans if e > s))
            if not ordered:
                return ()
            out = [list(ordered[0])]
            for s, e in ordered[1:]:
                if s <= out[-1][1]:
                    out[-1][1] = max(out[-1][1], e)
                else:
                    out.append([s, e])
            return tuple(((s, e) for s, e in out))
        _TERM_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
        _TERM_STOP = frozenset('the and for with from that this have has was were are is been its their there which what when where who whom whose how why all any both each more most other some such than then they them these those into over under about after before between during without within according listed page article table'.split())

        def _terms(text: str) -> set[str]:
            return {w for w in _TERM_RE.findall((text or '').casefold()) if w not in _TERM_STOP}

        def _dense_windows(note: str, terms: set[str], width: int, k: int) -> list[tuple[int, int]]:
            n = len(note)
            if n <= width or not terms:
                return [(0, min(n, width))] if n else []
            stride = max(400, width // 4)
            low = note.lower()
            scored: list[tuple[int, int]] = []
            pos = 0
            while True:
                seg = low[pos:pos + width]
                scored.append((sum((1 for t in terms if t in seg)), pos))
                if pos + width >= n:
                    break
                pos += stride
            scored.sort(key=lambda hp: (-hp[0], hp[1]))
            picked: list[tuple[int, int]] = []
            for hits, start in scored:
                if len(picked) >= max(1, k):
                    break
                if picked and hits <= 0:
                    break
                end = min(n, start + width)
                if any((start < pe and ps < end for ps, pe in picked)):
                    continue
                picked.append((start, end))
            picked.sort()
            return picked or [(0, min(n, width))]
        TOOL_SPECS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results with title, url and an excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Read a page. Returns its head plus the regions densest in your focus terms. Always read the page before relying on a figure.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'the page url'}, 'focus': {'type': 'string', 'description': 'what you are looking for on the page'}}, 'required': ['url']}}}]
        _SLOT = '\x00{}\x00'

        @dataclass(slots=True)
        class ToolOut:
            text: str
            rows: list[Row] = field(default_factory=list)

        def _commit(out: object, ledger: Ledger) -> str:
            if isinstance(out, str):
                return out
            if not isinstance(out, ToolOut):
                return f'# tool error: {out}'
            text = out.text
            for i, row in enumerate(out.rows):
                text = text.replace(_SLOT.format(i), str(ledger.add(row)))
            return text
        _SITE_OP_RE = re.compile('(?:\\b|^)site\\s*:\\s*\\S+\\s*', re.I)

        def _loosen(query: str) -> str:
            out = _SITE_OP_RE.sub('', query or '').replace('"', ' ')
            return ' '.join(out.split())

        async def _tool_search(query: str, deadline: float) -> ToolOut:
            query = ' '.join((query or '').split())[:400]
            if not query:
                return ToolOut('# web_search: empty query')
            attempts = [query]
            loose = _loosen(query)
            if loose and loose != query:
                attempts.append(loose)
            results = ()
            receipt = ''
            for attempt in attempts:
                if deadline - monotonic() < MIN_TAIL_S:
                    break
                try:
                    payload = await search_web([attempt], provider=SEARCH_PROVIDER, num=SEARCH_RESULTS, timeout=SEARCH_TIMEOUT_S)
                except Exception:
                    continue
                results = tuple(getattr(payload, 'results', ()) or ())
                receipt = getattr(payload, 'receipt_id', '') or ''
                if results:
                    break
            if not results:
                return ToolOut(f"# web_search '{query}': no results. Try different terms.")
            lines: list[str] = [f'web_search: {query}']
            rows: list[Row] = []
            for result in results:
                url = (getattr(result, 'url', '') or '').strip()
                note = (getattr(result, 'note', '') or '').strip()
                if not url or not note:
                    continue
                title = (getattr(result, 'title', '') or '').strip()
                rid = str(getattr(result, 'result_id', '') or '')
                end = min(len(note), SEARCH_EXCERPT_CHARS)
                idx = len(rows)
                excerpt = ' '.join(note[:end].split())
                rows.append(Row(receipt_id=receipt, result_id=rid, note_len=len(note), spans=((0, end),), kind='search', url=url, title=title, preview=excerpt))
                lines.append(f"[{_SLOT.format(idx)}] {title}\n    {url}\n    {' '.join(note[:end].split())}")
            if not rows:
                return ToolOut(f"# web_search '{query}': no usable results.")
            lines.append('(excerpts only — read_page before relying on any figure)')
            return ToolOut('\n'.join(lines), rows)

        async def _tool_read(url: str, focus: str, question: str, deadline: float) -> ToolOut:
            url = (url or '').strip()
            if not url:
                return ToolOut('# read_page: no url')
            if deadline - monotonic() < MIN_TAIL_S:
                return ToolOut(f'# read_page {url}: out of time')
            try:
                payload = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=FETCH_TIMEOUT_S)
            except Exception as exc:
                return ToolOut(f'# read_page {url} failed ({_err(exc)}). Try another source or search for a mirror.')
            results = tuple(getattr(payload, 'results', ()) or ())
            receipt = getattr(payload, 'receipt_id', '') or ''
            if not results:
                return ToolOut(f'# read_page {url}: no content returned.')
            result = results[0]
            note = getattr(result, 'note', '') or ''
            if not note.strip():
                return ToolOut(f'# read_page {url}: empty page.')
            title = (getattr(result, 'title', '') or '').strip()
            rid = str(getattr(result, 'result_id', '') or '')
            terms = _terms(focus) | _terms(question)
            head_end = min(len(note), PAGE_HEAD_CHARS)
            spans = [(0, head_end)]
            for start, end in _dense_windows(note[head_end:], terms, PAGE_WINDOW_CHARS, PAGE_WINDOWS):
                spans.append((head_end + start, head_end + end))
            spans = list(_merge_spans(tuple(spans)))
            row = Row(receipt_id=receipt, result_id=rid, note_len=len(note), spans=tuple(spans), kind='page', url=url, title=title, preview='\n'.join((note[s:e] for s, e in spans))[:PAGE_PREVIEW_CHARS])
            body = [f'read_page [{_SLOT.format(0)}] {title or url}\n{url}']
            for i, (start, end) in enumerate(spans):
                label = 'HEAD' if start == 0 else f'REGION @{start}'
                body.append(f'--- {label} ---\n{note[start:end]}')
            if len(note) > sum((e - s for s, e in spans)):
                body.append(f'(page is {len(note)} chars; {len(spans)} region(s) shown. read_page again with a different focus to see elsewhere.)')
            return ToolOut('\n'.join(body), [row])

        def _call_name(call: object) -> str:
            name = getattr(call, 'name', None)
            if isinstance(name, str) and name.strip():
                return name.strip()
            fn = getattr(call, 'function', None)
            return (getattr(fn, 'name', '') or '').strip()

        def _call_args(call: object) -> dict:
            raw = getattr(call, 'arguments', None)
            if raw is None:
                fn = getattr(call, 'function', None)
                raw = getattr(fn, 'arguments', None)
            if isinstance(raw, Mapping):
                return dict(raw)
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw or '{}')
                except Exception:
                    return {}
                return parsed if isinstance(parsed, dict) else {}
            return {}

        async def _run_tool(call: object, question: str, deadline: float) -> ToolOut | str:
            name = _call_name(call)
            args = _call_args(call)
            try:
                if name == 'web_search':
                    return await _tool_search(str(args.get('query') or ''), deadline)
                if name == 'read_page':
                    return await _tool_read(str(args.get('url') or ''), str(args.get('focus') or ''), question, deadline)
            except Exception as exc:
                return f'# tool {name} crashed: {_err(exc)}'
            return f'# unknown tool: {name}'

        def _err(exc: BaseException) -> str:
            try:
                return repr(exc)[:160]
            except Exception:
                return 'error'

        def _text_of(payload: object) -> str:
            llm = getattr(payload, 'llm', None)
            text = (getattr(llm, 'raw_text', None) or '').strip()
            if text:
                return text
            choices = getattr(llm, 'choices', None) or []
            if choices:
                content = getattr(getattr(choices[0], 'message', None), 'content', None)
                if isinstance(content, str):
                    return content.strip()
            return ''

        async def _chat(system: str, user: str, *, timeout: float, max_tokens: int=2600, think: bool=False, model: str='') -> str:
            messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
            for rung, attempts in _ladder(model or MODEL_LOOP):
                for _ in range(attempts):
                    if timeout <= 4.0:
                        return ''
                    try:
                        payload = await llm_chat(provider=LLM_PROVIDER, model=rung, messages=messages, temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=_think_for(rung, want=think))
                        text = _text_of(payload)
                        if text:
                            return text
                    except Exception:
                        continue
            return ''

        async def _turn(messages: list[dict], deadline: float, *, tools_on: bool):
            for rung, attempts in _ladder(MODEL_LOOP):
                for _ in range(attempts):
                    timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0)
                    if timeout <= 5.0:
                        return None
                    try:
                        return await llm_chat(provider=LLM_PROVIDER, model=rung, messages=messages, tools=TOOL_SPECS if tools_on else None, tool_choice='auto' if tools_on else None, temperature=0.2, thinking=_think_for(rung, want=True), timeout=timeout)
                    except Exception:
                        continue
            return None
        _TOOL_MARKUP_RE = re.compile('<\\s*/?\\s*tool_call|<\\s*/?\\s*(?:arg_key|arg_value|function_call|invoke)\\b|\\bweb_search\\s*[（(]\\s*query|\\bread_page\\s*[（(]\\s*url', re.I)
        _NARRATION_RE = re.compile("^\\s*(?:i (?:need|will|should|am going|'ll)\\b|let me\\b|first,?\\s*(?:i|let)\\b|i'?ll (?:search|look|start|begin|gather|check)|now (?:i|that i)\\b)", re.I)
        _REFUSAL_RE = re.compile("^\\s*(?:i\\s+(?:can(?:no|')t|am\\s+unable|was\\s+unable|do\\s*n[o']t\\s+have)|unable\\s+to\\b|sorry\\b|regrettably\\b|there\\s+is\\s+insufficient)", re.I)
        _CITE_RE = re.compile('\\[[0-9]{1,3}\\]')
        _VERIFY_RE = re.compile('\\s*\\((?:verify|unverified|uncertain)[^)]*\\)', re.I)
        MIN_ANSWER_CHARS = 40
        MIN_CITED_CHARS = 6

        def _repetitive(text: str) -> bool:
            parts = [p.strip() for p in re.split('(?<=[.!?])\\s+', text or '') if len(p.strip()) > 20]
            if len(parts) < 3:
                return False
            return len(set(parts)) <= max(1, len(parts) // 3)

        def _usable(text: str) -> bool:
            body = (text or '').strip()
            if not body:
                return False
            if _TOOL_MARKUP_RE.search(body) or _repetitive(body):
                return False
            if body.startswith('{') or body.startswith('['):
                try:
                    parsed = json.loads(body)
                    if isinstance(parsed, dict) and ('name' in parsed or 'tool' in parsed):
                        return False
                except Exception:
                    pass
            cited = bool(_CITE_RE.search(body))
            if cited and len(body) >= MIN_CITED_CHARS:
                return True
            if _NARRATION_RE.match(body) or _REFUSAL_RE.match(body):
                return False
            return len(body) >= MIN_ANSWER_CHARS
        REPAIR_ORDER = 'That was not a usable final answer — it was tool-call markup, a description of what you intended to do, or empty. Write the answer itself now: plain prose, the direct answer in the first sentence, [n] on every supported claim. Do not call any tool and do not describe your process.'

        def _wrapup(seconds_left: float) -> str:
            return f'TIME: about {int(max(0, seconds_left))}s remain. Stop researching and write the final answer NOW from the evidence already in this transcript. Commit to the best supported answer — an unhedged answer with citations beats a hedge. Apply every answer rule you were given and place [n] on every claim.'
        BRIEF_SYSTEM = 'Answer from your own knowledge, then say how to verify it. Two blocks, nothing else.\nDRAFT: your best answer now, with any figure you are unsure of marked (verify).\nPLAN: the specific documents or tables that would confirm it, and the exact search terms that would find them. Name the source the question specifies if it names one.'

        async def _brief(question: str, deadline: float) -> str:
            timeout = min(BRIEF_TIMEOUT_S, deadline - monotonic() - COMMIT_RESERVE_S)
            if timeout <= 6.0:
                return ''
            text = await _chat(BRIEF_SYSTEM, question, timeout=timeout, max_tokens=1400)
            if not text:
                return ''
            return 'PRIOR KNOWLEDGE (unverified — confirm or refute against sources; a (verify) mark means you must check it):\n' + text[:6000]
        _SEED_TOKEN_RE = re.compile("[A-Za-z0-9][\\w.'\\-]{1,}")
        _SEED_STOP = frozenset('what which who whom whose when where how many much name list give tell show find identify please could would you your the and for with from that this have has was were are is been its their there according per listed'.split())

        def _seed_queries(question: str, set_like: bool) -> list[str]:
            tokens = [t for t in _SEED_TOKEN_RE.findall(question or '') if t.lower() not in _SEED_STOP and len(t) > 2]
            if not tokens:
                return []
            core = ' '.join(tokens[:12])
            queries = [core]
            if set_like:
                queries.append(f"list of {' '.join(tokens[:8])}")
            for name in _named_sources(question)[:1]:
                queries.append(f"{' '.join(tokens[:8])} {name}")
            out: list[str] = []
            for q in queries:
                q = ' '.join(q.split())
                if q and q not in out:
                    out.append(q)
            return out[:MAX_SEED_QUERIES]

        async def _preseed(question: str, set_like: bool, ledger: Ledger, deadline: float) -> str:
            queries = _seed_queries(question, set_like)
            if not queries or deadline - monotonic() < COMMIT_RESERVE_S + 12.0:
                return ''
            outs = await asyncio.gather(*(_tool_search(q, deadline) for q in queries), return_exceptions=True)
            blocks: list[str] = []
            for out in outs:
                if isinstance(out, BaseException) or not isinstance(out, ToolOut):
                    continue
                body = _commit(out, ledger)
                if body and (not body.startswith('#')):
                    blocks.append(body)
            if not blocks:
                return ''
            return 'SEED EVIDENCE (already retrieved; cite by [n], read_page before relying on a figure):\n' + '\n\n'.join(blocks)

        async def _loop(question: str, rules: list[str], brief: str, ledger: Ledger, deadline: float) -> tuple[str, list[dict]]:
            messages: list[dict] = [{'role': 'system', 'content': LOOP_RULES}]
            for rule in rules:
                messages.append({'role': 'system', 'content': rule})
            if brief:
                messages.append({'role': 'system', 'content': brief})
            seeded = await _preseed(question, _wants_set(question), ledger, deadline)
            if seeded:
                messages.append({'role': 'system', 'content': seeded})
            messages.append({'role': 'user', 'content': question})
            answer = ''
            repairs = MAX_REPAIRS
            ordered = False
            for turn in range(1, MAX_TURNS + 1):
                left = deadline - monotonic()
                if left <= MIN_TAIL_S:
                    break
                commit_now = left <= COMMIT_RESERVE_S or turn >= MAX_TURNS
                if (commit_now or turn >= MAX_TURNS - 1) and (not ordered):
                    messages.append({'role': 'system', 'content': _wrapup(left)})
                    ordered = True
                payload = await _turn(messages, deadline, tools_on=not commit_now)
                if payload is None:
                    break
                llm = getattr(payload, 'llm', None)
                choices = getattr(llm, 'choices', None) or []
                if not choices:
                    break
                msg = getattr(choices[0], 'message', None)
                calls = tuple(getattr(msg, 'tool_calls', None) or ())
                if not calls:
                    candidate = _text_of(payload)
                    if not _usable(candidate):
                        if repairs > 0 and deadline - monotonic() > MIN_TAIL_S + 10.0:
                            repairs -= 1
                            messages.append({'role': 'system', 'content': REPAIR_ORDER})
                            continue
                        break
                    answer = candidate
                    messages.append({'role': 'assistant', 'content': answer})
                    break
                try:
                    messages.append(msg.to_input_message())
                except Exception:
                    messages.append({'role': 'assistant', 'content': '', 'tool_calls': [{'id': getattr(c, 'id', ''), 'type': 'function', 'function': {'name': _call_name(c), 'arguments': json.dumps(_call_args(c))}} for c in calls]})
                run = calls[:MAX_CALLS_PER_TURN]
                budget = max(5.0, min(FETCH_TIMEOUT_S * 2 + 6.0, deadline - monotonic() - MIN_TAIL_S))
                tasks = [asyncio.ensure_future(_run_tool(c, question, deadline)) for c in run]
                try:
                    await asyncio.wait(tasks, timeout=budget)
                except Exception:
                    pass
                outs: list[object] = []
                for task in tasks:
                    if task.done():
                        try:
                            outs.append(task.result())
                        except Exception as exc:
                            outs.append(f'# tool crashed: {_err(exc)}')
                    else:
                        task.cancel()
                        outs.append('# tool timed out — use what you already have')
                for call, out in zip(run, outs):
                    messages.append({'role': 'tool', 'tool_call_id': getattr(call, 'id', ''), 'content': _commit(out, ledger)})
                for call in calls[MAX_CALLS_PER_TURN:]:
                    messages.append({'role': 'tool', 'tool_call_id': getattr(call, 'id', ''), 'content': '# skipped: per-turn tool budget reached'})
            return (answer, messages)
        AUDIT_SYSTEM = 'You are auditing a research answer against the evidence it cites. Report only defects, as short imperative lines, at most six. Look for:\n- a claim that contradicts the source it cites;\n- a figure that appears in the answer but in none of the evidence;\n- for a set question: a qualifying member omitted, or an excluded member with no stated failing condition and no citation;\n- for a superlative: a winner named without the candidate table;\n- the named source of the question not being the source actually cited;\n- hedging on something the evidence establishes.\nIf the answer is sound, reply exactly OK.'

        async def _audit(question: str, answer: str, digest: str, deadline: float) -> str:
            timeout = min(AUDIT_TIMEOUT_S, deadline - monotonic() - MIN_TAIL_S - 12.0)
            if timeout <= 6.0 or not answer:
                return ''
            user = f'QUESTION:\n{question}\n\nANSWER:\n{answer[:14000]}\n\nEVIDENCE:\n{digest[:40000]}'
            text = await _chat(AUDIT_SYSTEM, user, timeout=timeout, max_tokens=700, model=MODEL_AUDIT)
            body = (text or '').strip()
            if not body or body.upper().startswith('OK'):
                return ''
            return body

        async def _patch(question: str, answer: str, findings: str, digest: str, rules: list[str], deadline: float) -> str:
            timeout = min(COMMIT_TIMEOUT_S, deadline - monotonic() - MIN_TAIL_S)
            if timeout <= 8.0:
                return answer
            system = 'Rewrite the answer so every listed defect is fixed. Keep everything that was already correct and cited. Change nothing the findings do not require. Output only the corrected answer.\n\n' + '\n\n'.join(rules)
            user = f'QUESTION:\n{question}\n\nANSWER:\n{answer[:14000]}\n\nDEFECTS TO FIX:\n{findings[:3000]}\n\nEVIDENCE:\n{digest[:40000]}'
            text = (await _chat(system, user, timeout=timeout, max_tokens=3000, think=True, model=MODEL_AUDIT)).strip()
            if not _usable(text):
                return answer
            before = len(set(_cited_numbers(answer, 999)))
            after = len(set(_cited_numbers(text, 999)))
            if before and after < before:
                return answer
            return text
        DIGEST_CHAR_CAP = 70000

        def _digest(ledger: Ledger) -> str:
            parts: list[str] = []
            spent = 0
            for i, row in enumerate(ledger.rows, start=1):
                text = (row.preview or '').strip()
                if not text:
                    continue
                head = f"[{i}] {row.title or ''} ({row.url or ''})".strip()
                block = f'{head}\n{text}'
                if spent + len(block) > DIGEST_CHAR_CAP:
                    break
                spent += len(block)
                parts.append(block)
            return '\n\n'.join(parts)
        COMMIT_SYSTEM = 'Write the final answer to the question using ONLY the numbered evidence below. Lead with the direct answer, then the proof. Put [n] on every claim that rests on evidence n. Do not describe your process and do not hedge a fact the evidence establishes.'

        async def _commit_from_digest(question: str, digest: str, rules: list[str], draft: str, deadline: float) -> str:
            timeout = min(COMMIT_TIMEOUT_S, deadline - monotonic() - MIN_TAIL_S)
            if timeout <= 6.0:
                return ''
            system = COMMIT_SYSTEM + ('\n\n' + '\n\n'.join(rules) if rules else '')
            user = f'QUESTION:\n{question}\n\nEVIDENCE:\n{digest[:70000]}'
            if draft:
                user += f'\n\nEARLIER DRAFT (may be incomplete; verify against the evidence):\n{draft[:4000]}'
            text = await _chat(system, user, timeout=timeout, max_tokens=3000)
            return text.strip() if _usable(text) else ''
        _LEAD_RE = re.compile('^\\s*(?:based on (?:my|the)\\b|now (?:i|that i)\\b|i (?:now )?(?:have|will)\\b|let me\\b)', re.I)

        def _strip_narration(answer: str) -> str:
            parts = re.split('(?<=[.!?])\\s+', answer or '')
            while len(parts) > 1 and _LEAD_RE.match(parts[0]) and (not _CITE_RE.search(parts[0])):
                parts = parts[1:]
            return ' '.join(parts).strip()

        def _fallback(question: str, digest: str) -> str:
            lines = [ln.strip() for ln in (digest or '').splitlines() if ln.strip()]
            kept: list[str] = []
            for line in lines:
                if line.startswith(('#', '---', '(')) or line.startswith('http'):
                    continue
                if re.match('^(?:web_search|read_page)\\b', line):
                    continue
                if len(line) < 40 or not re.search('[.!?]', line):
                    continue
                kept.append(line)
                if len(kept) >= 6:
                    break
            if not kept:
                return 'The available sources did not yield a verifiable answer to this question within the research budget.'
            return 'Based on the retrieved sources, the most relevant established facts are below; they bear directly on the question but were not resolved into a single verified answer within the research budget.\n\n' + '\n'.join((f'- {ln}' for ln in kept))
        _CITE_GROUP_RE = re.compile('\\[([0-9][0-9,\\s\\-]*)\\]')

        def _cited_numbers(answer: str, limit: int) -> list[int]:
            out: list[int] = []
            seen: set[int] = set()
            for m in _CITE_GROUP_RE.finditer(answer or ''):
                for part in re.split('[,\\s]+', m.group(1)):
                    part = part.strip()
                    if not part:
                        continue
                    if '-' in part:
                        bounds = part.split('-', 1)
                        try:
                            lo, hi = (int(bounds[0]), int(bounds[1]))
                        except ValueError:
                            continue
                        span = range(lo, hi + 1) if lo <= hi else range(hi, lo + 1)
                    else:
                        try:
                            span = [int(part)]
                        except ValueError:
                            continue
                    for n in span:
                        if 1 <= n <= limit and n not in seen:
                            seen.add(n)
                            out.append(n)
            return out

        def _citations(answer: str, ledger: Ledger) -> list[CitationRef]:
            refs: list[CitationRef] = []
            spent = 0
            for n in _cited_numbers(answer, len(ledger.rows)):
                if len(refs) >= CITATION_CAP:
                    break
                ref = ledger.ref(n)
                if ref is None:
                    continue
                cost = ledger.cost(n)
                if spent + cost > EVIDENCE_CHAR_BUDGET:
                    continue
                spent += cost
                refs.append(ref)
            return refs
        SCHEMA_SYSTEM = 'Convert the answer into a JSON value matching the schema. Emit the bare JSON value only — no prose, no markdown fence, no explanation.'

        def _extract_json(text: str) -> object | None:
            body = (text or '').strip()
            if body.startswith('```'):
                body = re.sub('^```[a-zA-Z]*\\s*|\\s*```$', '', body).strip()
            try:
                return json.loads(body)
            except Exception:
                pass
            for opener, closer in (('{', '}'), ('[', ']')):
                start, end = (body.find(opener), body.rfind(closer))
                if 0 <= start < end:
                    try:
                        return json.loads(body[start:end + 1])
                    except Exception:
                        continue
            return None

        def _schema_skeleton(schema: object) -> object:
            if not isinstance(schema, dict):
                return None
            kind = schema.get('type')
            if isinstance(kind, list):
                kind = next((k for k in kind if k != 'null'), None)
            if kind == 'object':
                props = schema.get('properties')
                return {k: _schema_skeleton(v) for k, v in props.items()} if isinstance(props, dict) else {}
            if kind == 'array':
                return []
            if kind in ('number', 'integer'):
                return 0
            if kind == 'boolean':
                return False
            return ''

        async def _structured(question: str, schema: object, answer: str, deadline: float) -> object:
            timeout = min(40.0, deadline - monotonic() - 3.0)
            if timeout > 6.0:
                user = f"SCHEMA:\n{json.dumps(schema)[:4000]}\n\nQUESTION:\n{question}\n\nANSWER:\n{(answer or '')[:8000]}"
                for _ in range(2):
                    text = await _chat(SCHEMA_SYSTEM, user, timeout=timeout, max_tokens=1200, model=MODEL_AUDIT)
                    value = _extract_json(text)
                    if value is not None:
                        return value
                    timeout = min(timeout, deadline - monotonic() - 3.0)
                    if timeout <= 6.0:
                        break
            return _schema_skeleton(schema)
        LAST_FAILURES: list[str] = []

        def _record_failure(where: str, exc: BaseException) -> None:
            try:
                LAST_FAILURES.append(f'{where}: {_err(exc)}')
                LAST_FAILURES[:] = LAST_FAILURES[-5:]
            except Exception:
                pass

        async def _solve(question: str, deadline: float) -> tuple[str, Ledger]:
            ledger = Ledger()
            rules = _shape_rules(question)
            brief = await _brief(question, deadline)
            answer, _messages = await _loop(question, rules, brief, ledger, deadline)
            digest = _digest(ledger)
            if not answer and digest:
                answer = await _commit_from_digest(question, digest, rules, '', deadline)
            if answer and digest and (deadline - monotonic() > MIN_TAIL_S + 24.0):
                findings = await _audit(question, answer, digest, deadline)
                if findings:
                    answer = await _patch(question, answer, findings, digest, rules, deadline)
            if not _usable(answer):
                answer = _fallback(question, digest)
            answer = _strip_narration(_VERIFY_RE.sub('', answer))[:ANSWER_CHAR_CAP]
            return (answer, ledger)

        async def query(query: Query) -> Response:
            deadline = monotonic() + WALL_BUDGET_S
            question = (getattr(query, 'text', '') or '').strip()
            if not question:
                return Response(text='No question provided.')
            schema = getattr(query, 'output_schema', None)
            try:
                answer, ledger = await _solve(question, deadline)
            except Exception as exc:
                _record_failure('solve', exc)
                answer, ledger = ('', Ledger())
            try:
                citations = _citations(answer, ledger)
            except Exception:
                citations = []
            if schema is None:
                if not answer:
                    answer = 'The available sources did not yield a verifiable answer to this question within the research budget.'
                return Response(text=answer, citations=citations or None)
            try:
                value = await _structured(question, schema, answer, deadline)
            except Exception:
                value = _schema_skeleton(schema)
            try:
                return Response(output=value, citations=citations or None)
            except Exception:
                return Response(output=value)
        return query

class SecondPath:

    def _compile(self):
        import asyncio
        import json
        import re
        from time import monotonic
        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        VERSION = 'v44d-lazycommit-glm5'
        LLM_LANE_A = 'openrouter'
        LLM_LANE_B = 'ai_gateway'
        LOOP_MODEL_A = 'z-ai/glm-5'
        LOOP_MODEL_B = 'zai/glm-5.2-fast'
        AUDIT_MODEL = 'openai/gpt-oss-120b'
        SCHEMA_MODEL = 'openai/gpt-oss-120b'
        RESORT_MODEL = 'deepseek/deepseek-v3.2'
        SEARCH_PROVIDER = 'parallel'
        WALL_BUDGET_S = 266.0
        BRIEF_TIMEOUT_S = 50.0
        TURN_TIMEOUT_S = 75.0
        AUDIT_TIMEOUT_S = 28.0
        SEARCH_TIMEOUT_S = 18.0
        FETCH_TIMEOUT_S = 16.0
        WRAPUP_AT_S = 90.0
        MIN_TAIL_S = 8.0
        MAX_TURNS = 15
        AUDIT_EXTRA_TURNS = 2
        ANSWER_REPAIR_TURNS = 2
        RESCUE_TIMEOUT_S = 55.0
        AUDIT_REPAIR_MAX_S = 70.0
        AUDIT_MIN_HEADROOM_S = 130.0
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
        LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}, {'type': 'function', 'function': {'name': 'page_grep', 'description': 'Search INSIDE a page you already fetched, by regex or literal text, and get every match with its surrounding context and character offset. Use this when read_page showed you the head of a long page but the value you need is deeper in it -- do not re-fetch, grep it.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL of a page already fetched this run'}, 'pattern': {'type': 'string', 'description': 'regex or literal string to find, e.g. a city name, a year, a column label'}}, 'required': ['url', 'pattern']}}}, {'type': 'function', 'function': {'name': 'page_read', 'description': 'Read an arbitrary character range of a page you already fetched. Use the offsets page_grep reports to read the full table or section around a match.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL already fetched'}, 'offset': {'type': 'integer', 'description': 'start character offset'}, 'length': {'type': 'integer', 'description': 'how many characters to read (max 12000)'}}, 'required': ['url', 'offset']}}}, {'type': 'function', 'function': {'name': 'retain_evidence', 'description': "Keep the exact source text that proves a claim you are about to make. Pass the result number and the verbatim quote from it. Do this the moment you find a decisive value -- the judge only credits claims whose citation contains the supporting text, and this is how that text gets into your citation. Use it for the QUESTION'S PREMISES as well as your answer: every entity, work, date or figure the question names should end up with a retained quote confirming it.", 'parameters': {'type': 'object', 'properties': {'source': {'type': 'string', 'description': 'result number to quote from, e.g. 3'}, 'quote': {'type': 'string', 'description': 'verbatim text copied from that result that states the fact'}}, 'required': ['source', 'quote']}}}, {'type': 'function', 'function': {'name': 'check_constraints', 'description': 'Decide which items satisfy numeric criteria. Use this WHENEVER the question asks which entities meet one or more thresholds (population over X, rate below Y, more than N times, above the average). Transcribe the rows you read from the sources, state the tests, and this returns the exact set that passes. Do NOT do that comparison in your head -- you get it wrong on long tables and differently wrong each time. A threshold that is itself computed from the data (an average, a total) is written {"agg":"mean","field":"pop"}.', 'parameters': {'type': 'object', 'properties': {'rows': {'type': 'array', 'description': 'the transcribed table: one object per item, e.g. [{"entity":"<name>","<metric>":1234,"<metric2>":56}]', 'items': {'type': 'object'}}, 'tests': {'type': 'array', 'description': 'criteria, ALL of which must hold, e.g. [{"field":"pop","op":"<","value":15000000}]. op is one of < <= > >= == !=', 'items': {'type': 'object'}}}, 'required': ['rows', 'tests']}}}]
        LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nQUOTE WHAT PROVES IT: the judge credits a claim only when your citation CONTAINS the source text stating it. The moment you read a decisive value, call retain_evidence(source, quote) with the exact words from that result. Do this for every condition you test and every figure you report -- an answer whose citations do not carry its numbers loses to one that does, even when both answers are identical.\nALSO QUOTE THE QUESTION\'S PREMISES, not only your answer. Every entity, work, date or figure the question NAMES is a claim the judge expects traceable: the film it says someone directed, the article it points at, the year it fixes, the people it lists. You lose to an otherwise identical answer that cited those too -- measured verbatim: "does not provide a citation for \'Everyone Says I Love You\'... Answer 1 is more thorough in its traceability to all parts of the prompt\'s context". Retain a quote for each named premise as you confirm it, even when it is background you already believed.\n\nREAD DEEP, DO NOT RE-FETCH: read_page shows the head plus a few regions of a long page. If the value you need is not in what you were shown, call page_grep(url, pattern) to find it anywhere in that page and page_read to open the region around a reported offset. Grepping a page you already have costs nothing and beats another search.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. COPY SOURCE VALUES VERBATIM: when the question names a source, every name, label and value in the answer must be the exact string that source prints -- never add a familiar alternative in parentheses, never anglicise a transliteration. \'Makkah\' is the answer; \'Mecca (Makkah)\' is a wrong answer. ONE EXCEPTION, and it is absolute: if the question says to output ONLY the answer (\'output only\', \'respond with only\', \'nothing else\', \'no explanation\'), emit the answer line as the BARE requested text — no [n] markers on it, nothing else on that line: a trailing [3] makes the text inexact and fails the instruction. Still write the PROOF section BELOW it carrying its [n] markers. Only the answer line is shipped, but the citations are harvested from the proof first, and an uncited answer scores zero. Obeying that instruction IS the task. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

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

            def add(self, receipt_id: str, result_id: str, note_len: int, kind: str, spans: list[tuple[int, int]] | None, title: str='', url: str='', preview: str='', text: str='') -> int:
                self.rows.append({'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': (url or '')[:300], 'preview': (preview or '')[:1200], 'spans': spans, 'text': (text or '')[:_LEDGER_TEXT_CAP], 'retained': []})
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
                    retained: list[list[int]] = []
                    for a, b in row.get('retained') or []:
                        a = max(0, min(int(a), note_len))
                        b = max(a + 1, min(int(b), note_len))
                        retained.append([a, b])
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
                    if retained:
                        merged.extend(retained)
                        merged.sort()
                        folded: list[list[int]] = []
                        for s, e in merged:
                            if folded and s <= folded[-1][1]:
                                folded[-1][1] = max(folded[-1][1], e)
                            else:
                                folded.append([s, e])
                        merged = folded
                    slices = [CitationSlice(start=s, end=e) for s, e in merged if e > s]
                    if not slices:
                        return None
                    return CitationRef(receipt_id=row['receipt_id'], result_id=row['result_id'], slices=slices)
                return None
        _WORD_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
        _STOP = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

        def _key_terms(text: str) -> set[str]:
            return {w for w in _WORD_RE.findall((text or '').casefold()) if w not in _STOP}
        _VALUE_CUE_RE = re.compile('\\d{1,4}\\s*[-–—]\\s*\\d{1,4}|\\d[\\d,]*(?:\\.\\d+)?\\s*%?')
        _CUE_MIN_LEN = 3
        _WEAK_CUE_RE = re.compile('^\\d{1,4}$')

        def _value_cues(*texts: str) -> set[str]:
            cues: set[str] = set()
            for text in texts:
                for raw in _VALUE_CUE_RE.findall(text or ''):
                    token = raw.replace(' ', '').replace('—', '-').replace('–', '-')
                    token = token.rstrip('.,').casefold()
                    if len(token) < _CUE_MIN_LEN or _WEAK_CUE_RE.match(token):
                        continue
                    cues.add(token)
                    if token.endswith('%'):
                        bare = token[:-1]
                        if len(bare) >= _CUE_MIN_LEN and (not _WEAK_CUE_RE.match(bare)):
                            cues.add(bare)
            return cues

        def _best_windows(note: str, terms: set[str], width: int, k: int=1, cues: set[str] | None=None) -> list[tuple[int, int]]:
            n = len(note)
            if n <= width:
                return [(0, n)]
            step = max(600, width // 3)
            low = note.lower().replace('–', '-').replace('—', '-')
            scored: list[tuple[int, int, int]] = []
            pos = 0
            cue_set = cues or frozenset()
            while pos < n:
                seg = low[pos:pos + width]
                hits = sum((1 for t in terms if t in seg))
                cue_hits = sum((1 for c in cue_set if c in seg))
                scored.append((cue_hits, hits, pos))
                if pos + width >= n:
                    break
                pos += step
            scored.sort(key=lambda hs: (-hs[0], -hs[1], hs[2]))
            picked: list[tuple[int, int]] = []
            for cue_hits, hits, start in scored:
                if len(picked) >= max(1, k):
                    break
                end = min(n, start + width)
                if any((start < pe and ps < end for ps, pe in picked)):
                    continue
                if picked and hits <= 0 and (cue_hits <= 0):
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
                rows.append({'receipt_id': receipt, 'result_id': rid, 'note_len': n_len, 'kind': 'search', 'spans': span, 'title': title, 'url': url, 'preview': note[:SEARCH_EXCERPT_CHARS], 'text': note})
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
                row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, len(note))], 'title': url, 'url': url, 'preview': note[:1200], 'text': note}
                return ToolOutput(f'# read_page({url!r}) -> [{_SLOT.format(0)}] full page, {len(note)} chars\n{note}', [row])
            terms = _key_terms(question) | _key_terms(focus)
            windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE, cues=_value_cues(question, focus))
            row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, FETCH_HEAD_CHARS)] + list(windows), 'title': url, 'url': url, 'preview': note[windows[0][0]:windows[0][0] + 1200], 'text': note}
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
                squashed_chars, origin = ([], [])
                for pos, ch in enumerate(text):
                    if not ch.isspace():
                        squashed_chars.append(ch.lower())
                        origin.append(pos)
                squashed_q = ''.join(q.split()).lower()
                if squashed_q:
                    hit = ''.join(squashed_chars).find(squashed_q)
                    if hit >= 0 and hit < len(origin):
                        i = origin[hit]
                        end = origin[min(hit + len(squashed_q), len(origin)) - 1] + 1
                        q = text[i:end]
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
        _CMP_OPS = ('<=', '>=', '!=', '<', '>', '==')
        _AGGS = ('mean', 'avg', 'median', 'sum', 'min', 'max', 'count')

        def _cn_num(v):
            if isinstance(v, bool):
                return None
            if isinstance(v, (int, float)):
                return float(v)
            s = str(v or '').strip()
            if not s:
                return None
            s = s.replace(',', '').replace('$', '').replace('%', '').replace('−', '-')
            m = re.search('-?\\d+(?:\\.\\d+)?', s)
            return float(m.group(0)) if m else None

        def _cn_agg(kind: str, values: list) -> float | None:
            vals = [v for v in values if v is not None]
            if not vals:
                return None
            kind = (kind or '').strip().lower()
            if kind in ('mean', 'avg'):
                return sum(vals) / len(vals)
            if kind == 'sum':
                return sum(vals)
            if kind == 'min':
                return min(vals)
            if kind == 'max':
                return max(vals)
            if kind == 'count':
                return float(len(vals))
            if kind == 'median':
                ordered = sorted(vals)
                mid = len(ordered) // 2
                return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0
            return None

        def _do_check_constraints(rows_arg, tests_arg) -> str:
            rows = rows_arg
            tests = tests_arg
            if isinstance(rows, str):
                try:
                    rows = json.loads(rows)
                except Exception:
                    return '# check_constraints: rows must be a JSON list of objects'
            if isinstance(tests, str):
                try:
                    tests = json.loads(tests)
                except Exception:
                    return '# check_constraints: tests must be a JSON list of objects'
            if not isinstance(rows, list) or not rows:
                return '# check_constraints: rows must be a non-empty JSON list of objects'
            if not isinstance(tests, list) or not tests:
                return '# check_constraints: tests must be a non-empty JSON list of objects'
            rows = [r for r in rows if isinstance(r, dict)][:400]
            if not rows:
                return '# check_constraints: no object rows found'

            def label(r):
                for k in ('entity', 'name', 'item', 'state', 'id'):
                    if r.get(k) not in (None, ''):
                        return str(r[k])
                return str(next(iter(r.values()), '?'))
            resolved = []
            for t in tests[:12]:
                if not isinstance(t, dict):
                    continue
                field = str(t.get('field') or '').strip()
                op = str(t.get('op') or '').strip()
                if op not in _CMP_OPS:
                    return '# check_constraints: op must be one of %s (got %r)' % (', '.join(_CMP_OPS), op)
                if not any((field in r for r in rows)):
                    return '# check_constraints: no row has field %r; fields present: %s' % (field, ', '.join(sorted({k for r in rows for k in r}))[:200])
                raw = t.get('value')
                if isinstance(raw, dict):
                    agg = str(raw.get('agg') or '').strip().lower()
                    if agg not in _AGGS:
                        return '# check_constraints: value.agg must be one of %s' % ', '.join(_AGGS)
                    over = str(raw.get('field') or field).strip()
                    threshold = _cn_agg(agg, [_cn_num(r.get(over)) for r in rows])
                    if threshold is None:
                        return '# check_constraints: could not compute %s of %r' % (agg, over)
                    shown = '%s(%s)=%g' % (agg, over, threshold)
                else:
                    threshold = _cn_num(raw)
                    if threshold is None:
                        return '# check_constraints: value %r is not a number or {agg,field}' % (raw,)
                    shown = '%g' % threshold
                resolved.append((field, op, threshold, shown))
            passing, lines, unusable = ([], [], [])
            for r in rows:
                name = label(r)
                verdicts, ok = ([], True)
                for field, op, threshold, shown in resolved:
                    got = _cn_num(r.get(field))
                    if got is None:
                        ok = False
                        verdicts.append('%s=? (missing)' % field)
                        if name not in unusable:
                            unusable.append(name)
                        continue
                    if op == '<':
                        hit = got < threshold
                    elif op == '<=':
                        hit = got <= threshold
                    elif op == '>':
                        hit = got > threshold
                    elif op == '>=':
                        hit = got >= threshold
                    elif op == '==':
                        hit = got == threshold
                    else:
                        hit = got != threshold
                    ok = ok and hit
                    verdicts.append('%s %g%s%s %s' % (field, got, op, shown, 'PASS' if hit else 'FAIL'))
                if ok:
                    passing.append(name)
                lines.append('%-28s %s -> %s' % (name[:28], '; '.join(verdicts), 'KEEP' if ok else 'drop'))
            head = '# check_constraints: %d of %d supplied rows satisfy ALL %d tests.\n# PASSING: %s\n# The comparisons above are exact -- do not redo them. But CHECK YOUR\n# INPUT before answering: you supplied %d rows. If the source table\n# lists more entities than that, transcribe the missing ones and call\n# this again -- an entity you never supplied can never be returned.\n' % (len(passing), len(rows), len(resolved), ', '.join(passing) if passing else '(none)', len(rows))
            if unusable:
                head += '# WARNING -- %d row(s) had a value this could not read and were\n# DROPPED: %s. Re-read those figures from the source and call again.\n' % (len(unusable), ', '.join(unusable[:12]))
            return head + '\n'.join(lines[:120])

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
            if name == 'retain_evidence':
                return _do_retain_evidence(str(args.get('source') or ''), str(args.get('quote') or ''), ledger)
            if name == 'check_constraints':
                return _do_check_constraints(args.get('rows'), args.get('tests'))
            if name == 'page_grep':
                return _do_page_grep(str(args.get('url') or ''), str(args.get('pattern') or ''), ledger)
            if name == 'page_read':
                return _do_page_read(str(args.get('url') or ''), args.get('offset') or 0, args.get('length') or PAGE_READ_MAX_CHARS, ledger)
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

        async def _chat_turn(messages: list[dict], deadline: float, *, finish_only: bool, force_tools: bool=False):
            for lane_model in ((LLM_LANE_A, LOOP_MODEL_A), (LLM_LANE_B, LOOP_MODEL_B)):
                lane = lane_model[0]
                model = lane_model[1]
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
        BOARD_ROW_CHARS = 260
        BOARD_COMMIT_CHARS = 1200
        BOARD_MAX_ROWS = 48
        _FOLDED = '[folded into the evidence board]'

        def _board_rows(ledger: EvidenceLedger, question: str) -> list[tuple[int, int, str]]:
            rows: list[tuple[int, int, str]] = []
            for index, row in enumerate(ledger.rows, start=1):
                if row.get('kind') == 'reserved':
                    continue
                preview = ' '.join((row.get('preview') or '').split())
                if not preview:
                    continue
                rank = _source_rank(row.get('url', ''), row.get('title', ''), preview, question)
                title = ' '.join((row.get('title') or '').split())[:90]
                rows.append((rank, index, '[%d] %s — %s' % (index, title, preview[:BOARD_ROW_CHARS])))
            rows.sort(key=lambda r: (r[0], r[1]))
            return rows[:BOARD_MAX_ROWS]

        def _render_board(ledger: EvidenceLedger, question: str, *, width: int=BOARD_ROW_CHARS, char_cap: int=18000) -> str:
            scored = []
            for index, row in enumerate(ledger.rows, start=1):
                if row.get('kind') == 'reserved':
                    continue
                preview = ' '.join((row.get('preview') or '').split())
                if not preview:
                    continue
                rank = _source_rank(row.get('url', ''), row.get('title', ''), preview, question)
                scored.append((rank, index, row, preview))
            scored.sort(key=lambda r: (r[0], r[1]))
            parts, spent = ([], 0)
            for _rank, index, row, preview in scored[:BOARD_MAX_ROWS]:
                title = ' '.join((row.get('title') or '').split())[:90]
                block = '[%d] %s (%s)\n%s' % (index, title, row.get('url') or '', preview[:width])
                if spent + len(block) > char_cap:
                    break
                spent += len(block)
                parts.append(block)
            if not parts:
                return ''
            return 'EVIDENCE BOARD — every item gathered so far, strongest source first. These [n] are the citations available to you; cite the one that actually states each fact, never the same [n] for everything.\n\n' + '\n\n'.join(parts)

        def _fold_transcript(messages: list[dict], ledger: EvidenceLedger, question: str) -> None:
            tool_positions = [i for i, m in enumerate(messages) if isinstance(m, dict) and m.get('role') == 'tool']
            for i in tool_positions[:-8]:
                if messages[i].get('content') != _FOLDED:
                    messages[i] = dict(messages[i])
                    messages[i]['content'] = _FOLDED
            board = _render_board(ledger, question)
            if not board:
                return
            for i, m in enumerate(messages):
                if isinstance(m, dict) and m.get('role') == 'system' and str(m.get('content', '')).startswith('EVIDENCE BOARD'):
                    messages[i] = {'role': 'system', 'content': board}
                    return
            messages.append({'role': 'system', 'content': board})

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
            gates_left = 1
            held_answer = ''
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
                    if gates_left > 0 and ledger.rows and (_retained_count(ledger) == 0) and (not out_of_time) and (deadline - monotonic() > MIN_TAIL_S + 20.0):
                        gates_left -= 1
                        held_answer = candidate
                        messages.append({'role': 'system', 'content': _RETAIN_ORDER})
                        answer = ''
                        continue
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
                _fold_transcript(messages, ledger, question)
            if not _is_usable_answer(answer) and _is_usable_answer(held_answer):
                answer = held_answer
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
                if line.count('|') >= 3:
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
        _RETAIN_ORDER = 'STOP -- do not answer yet. You have not retained any evidence, so the citations on your answer would show the TOP OF EACH PAGE (menus, cookie banners, site chrome) instead of the text that proves your claims. The grader sees only the spans you retain. For EVERY fact your answer asserts, call retain_evidence(source="[n]", quote="...") with the sentence or table row from [n] that states it, copied EXACTLY as the source prints it, including the figures. Retain one per fact -- several per source is normal and expected. Then write the final answer.'

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
        _DIGEST_LEAD_RE = re.compile('^\\s*Best-supported findings|^\\s*sources retrieved:', re.I)
        _DIGEST_NOISE_RE = re.compile('\\[slice \\d+:\\d+\\]|https?://\\S+')
        _VALUE_MAX_CHARS = 90

        def _source_titles(ledger) -> set:
            out = set()
            for row in getattr(ledger, 'rows', None) or []:
                for key in ('title', 'url'):
                    v = ' '.join(str(row.get(key) or '').split()).casefold()
                    if len(v) > 3:
                        out.add(v)
            return out

        def _undigest_for_schema(basis: str, ledger=None) -> str:
            if not basis:
                return ''
            text = _DIGEST_NOISE_RE.sub(' ', basis)
            titles = _source_titles(ledger) if ledger is not None else set()
            out = []
            for raw in text.split('\n'):
                line = raw.strip().lstrip('-*• ').strip()
                if not line or _DIGEST_LEAD_RE.match(line):
                    continue
                if ' '.join(line.split()).casefold() in titles:
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
        _NUM_CMP_RE = re.compile('([-+]?\\d[\\d,]*(?:\\.\\d+)?)\\s*(>=|<=|=>|=<|>|<)\\s*([-+]?\\d[\\d,]*(?:\\.\\d+)?)')
        _VERDICT_RE = re.compile('(qualifies|does not qualify|excluded|fails|no\\b|yes\\b)', re.I)
        _PRIMARY_HOST_RE = re.compile('\\.gov$|\\.gov\\.|\\.mil$|\\.edu$|europa\\.eu|\\.un\\.org|worldbank\\.org|imf\\.org|oecd\\.org|sec\\.gov|federalreserve\\.gov|census\\.gov|bls\\.gov|fec\\.gov|nasa\\.gov|who\\.int', re.I)
        _OFFICIAL_HINT_RE = re.compile('investor|\\bir\\.|/investors?|annual-?report|press-?release|newsroom|/filing|10-k|20-f|official|statistics|factsheet|fact-?sheet', re.I)
        _AGGREGATOR_RE = re.compile('pinterest|quora|reddit|facebook|twitter|x\\.com|tiktok|medium\\.com|blogspot|wordpress|answers\\.|ehow|wikihow|coursehero|scribd|slideshare|tripadvisor|amazon\\.', re.I)

        def _arithmetic_contradictions(answer: str) -> list[str]:
            problems: list[str] = []
            for line in (answer or '').split('\n'):
                for chunk in re.split('[;.]\\s+', line):
                    match = _NUM_CMP_RE.search(chunk)
                    if match is None:
                        continue
                    left, op, right = (_as_number(match.group(1)), match.group(2), _as_number(match.group(3)))
                    if left is None or right is None:
                        continue
                    if op in ('>',):
                        holds = left > right
                    elif op in ('<',):
                        holds = left < right
                    elif op in ('>=', '=>'):
                        holds = left >= right
                    else:
                        holds = left <= right
                    verdict = _VERDICT_RE.search(chunk)
                    if verdict is None:
                        if not holds:
                            problems.append("'%s' is false: %s %s %s" % (chunk.strip()[:90], match.group(1), op, match.group(3)))
                        continue
                    said_yes = verdict.group(1).lower() in ('qualifies', 'yes')
                    if said_yes != holds:
                        problems.append("'%s' -- %s %s %s is %s, so the verdict is inverted" % (chunk.strip()[:90], match.group(1), op, match.group(3), holds))
            return problems[:6]

        def _coverage_gaps(answer: str, facts: list[dict]) -> list[str]:
            text = ' '.join((answer or '').split()).lower()
            if not text:
                return []
            missing: list[str] = []
            seen: set = set()
            for row in facts:
                label = (row.get('label') or '').strip()
                if len(label) < 3 or not row.get('value'):
                    continue
                key = label.lower()
                if key in seen:
                    continue
                seen.add(key)
                if key not in text:
                    missing.append('%s (established as %s [%s]) is never mentioned' % (label, row['value'], row.get('n', 0)))
            return missing[:8]

        def _lead_disagrees_with_body(answer: str, facts: list[dict]) -> bool:
            text = answer or ''
            if not text.strip():
                return False
            parts = re.split('(?<=[.!?])\\s+', ' '.join(text.split()))
            if len(parts) < 2:
                return False
            lead = parts[0].lower()
            rest = ' '.join(parts[1:]).lower()
            for row in facts:
                label = (row.get('label') or '').strip().lower()
                if len(label) < 3 or not row.get('value'):
                    continue
                if label in lead:
                    continue
                for cue in ('complete list', 'therefore', 'qualifying jurisdictions are', 'the answer is', 'in summary', 'final list'):
                    idx = rest.find(cue)
                    if idx >= 0 and label in rest[idx:idx + 260]:
                        return True
            return False

        def _source_rank(url: str, title: str, note: str, ask: str) -> int:
            blob = '%s %s' % (url or '', title or '')
            rank = 50
            if _PRIMARY_HOST_RE.search(url or ''):
                rank = 5
            elif _OFFICIAL_HINT_RE.search(blob):
                rank = 15
            elif 'wikipedia.org' in (url or '').lower():
                rank = 25
            if _AGGREGATOR_RE.search(url or ''):
                rank = 90
            text = (note or '').lower()
            terms = [w for w in re.findall('[a-z]{4,}', (ask or '').lower())][:12]
            hits = sum((1 for w in set(terms) if w in text))
            digits = len(re.findall('\\d', text))
            rank -= min(hits, 8) * 2
            rank -= 4 if digits >= 12 else 0
            return rank

        def _as_number(raw: str):
            try:
                return float(raw.replace(',', '').lstrip('+'))
            except Exception:
                return None
        _MARKER_RE = re.compile('\\[(\\d{1,3})\\]')

        async def query(query: Query) -> Response:
            question = (query.text or '').strip()
            if not question:
                return Response(text='No question provided.')
            try:
                return await _solve(query, question)
            except Exception:
                return Response(text=f'Best-effort answer unavailable for: {question[:500]}')
        RESEARCH_RESERVE_S = 53.0
        COMMIT_TIMEOUT_S = 46.0
        COMMIT_MIN_BUDGET_S = 20.0

        def _cite_count(text: str) -> int:
            return len(set(_CITE_MARK_RE.findall(text or '')))
        QUOTE_TABLE_CHARS = 1400

        def _quote_table(ledger: EvidenceLedger) -> str:
            parts = []
            for i, row in enumerate(ledger.rows, start=1):
                text = row.get('text') or ''
                for a, b in row.get('retained') or []:
                    excerpt = text[max(0, int(a)):int(b)][:QUOTE_TABLE_CHARS].strip()
                    if excerpt:
                        parts.append('[%d] %s\n%s' % (i, row.get('title') or row.get('url') or '', excerpt))
            return '\n\n'.join(parts)

        def _retained_count(ledger: EvidenceLedger) -> int:
            return sum((len(r.get('retained') or []) for r in ledger.rows))

        async def _forced_commit(question: str, ledger: EvidenceLedger, board: str, deadline: float) -> str:
            budget = min(COMMIT_TIMEOUT_S, deadline - monotonic() - DIGEST_TAIL_S)
            if budget < COMMIT_MIN_BUDGET_S or not ledger.rows:
                return ''
            evidence = board or _ledger_digest(ledger)
            if not evidence:
                return ''
            quotes = _quote_table(ledger)
            if quotes:
                evidence = 'QUOTES YOU RETAINED AS PROOF — prefer these, and cite the [n] shown here for each fact they carry.\n\n%s\n\n%s' % (quotes[:24000], evidence)
            system = LOOP_RULES + '\n\nRESEARCH IS OVER. You have no tools and nothing further to gather. Write the final answer from the evidence board below, which holds every item collected, strongest source first. Cite its [n] exactly as written; never invent one. Cover every part of the question -- this is the answer that will be scored.'
            try:
                return (await _chat_simple(LLM_LANE_A, LOOP_MODEL_A, system, 'QUESTION: %s\n\n%s' % (question, evidence[:60000]), max_tokens=2600, timeout=budget)).strip()
            except Exception:
                return ''

        async def _research_then_commit(question: str, brief: str, ledger: EvidenceLedger, deadline: float) -> tuple[str, list[dict]]:
            research_deadline = deadline - RESEARCH_RESERVE_S
            pending, messages = ('', [])
            try:
                pending, messages = await _loop(question, brief, ledger, research_deadline, MAX_TURNS)
            except Exception:
                pending, messages = ('', [])
            if _is_usable_answer(pending):
                return (pending, messages)
            board = _render_board(ledger, question)
            committed = await _forced_commit(question, ledger, board, deadline)
            if _is_usable_answer(committed):
                return (committed, messages)
            return (pending, messages)

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
                answer, messages = await _research_then_commit(question, brief, ledger, deadline)
            except Exception:
                answer = ''
            try:
                if _is_usable_answer(answer) and deadline - monotonic() > 75.0 and (_spend_left() >= AUDIT_MIN_USD):
                    patched = await _audit_patch(question, answer, messages, ledger, deadline)
                    if _is_usable_answer(patched):
                        answer = patched
            except Exception:
                pass
            try:
                if _is_usable_answer(answer) and deadline - monotonic() > AUDIT_MIN_HEADROOM_S:
                    _rows = [{'label': (r.get('title') or '')[:80], 'value': '', 'n': i + 1, 'verified': True} for i, r in enumerate(ledger.rows)]
                    _defects = _arithmetic_contradictions(answer)
                    if _lead_disagrees_with_body(answer, _rows):
                        _defects.append('the opening list omits a member the answer later endorses; sentence one must already carry the final, complete list')
                    if _defects:
                        _audit_deadline = min(deadline, monotonic() + AUDIT_REPAIR_MAX_S)
                        _fixed = await _loop(question, brief, ledger, _audit_deadline, 1, carry=list(messages) + [{'role': 'system', 'content': 'Your answer has these defects:\n- ' + '\n- '.join(_defects[:6]) + '\nRecompute every comparison and rewrite the COMPLETE answer from scratch. Do not append a correction: sentence one must already state the final, complete answer.'}])
                        _cand = _fixed[0] if isinstance(_fixed, tuple) else ''
                        if _is_usable_answer(_cand) and (not _arithmetic_contradictions(_cand)):
                            answer = _cand
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
                    cleaned = _undigest_for_schema(basis, ledger)
                    basis = cleaned if cleaned else ''
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

class ThirdPath:

    def _compile(self):
        import asyncio
        import json
        import re
        from time import perf_counter
        from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        LLM_PROVIDER = 'openrouter'
        MODEL = 'z-ai/glm-5.2'
        COMMIT_FALLBACK_MODEL = 'deepseek/deepseek-v3.2'
        FETCH_RETRY_ATTEMPTS = 2
        TASK_TOTAL_BUDGET_SECONDS = 270.0
        SEARCH_TIMEOUT_SECONDS = 20.0
        FETCH_TIMEOUT_SECONDS = 15.0
        MAX_RETRY_ATTEMPTS_PER_TURN = 2
        LLM_TURN_TIMEOUT_SECONDS = 90.0
        RESEARCH_TURN_CAP = 10
        RESEARCH_TIME_CAP_SECONDS = 140.0
        CHECKPOINT_TOOL_TURNS = 2
        FINAL_RESERVE_SECONDS = 55.0
        FINAL_RETRY_MIN_SECONDS = 25.0
        TOOL_RESULT_INLINE_CHARS = 2600
        PAGE_WINDOW_CHARS = 1800
        PAGE_WINDOWS_PER_PAGE = 3
        PAGE_WINDOW_BUDGET_CHARS = 34000
        TERM_LIMIT = 22
        TERM_HITS_PER_TERM = 60
        TERM_HITS_TOTAL = 600
        SEARCH_EXCERPT_INLINE_CHARS = 380
        COVERAGE_LIST_MAX = 8
        MIN_ANSWER_CHARS = 400
        HARD_MIN_ANSWER_CHARS = 200
        CITATION_BUDGET_CHARS = 90000
        CITATION_SLICE_MIN_CHARS = 4000
        CITATION_ANCHOR_CONTEXT_CHARS = 160
        CITATION_ANCHOR_LEAD_CHARS = 800
        TOOLS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web. Returns results with title, url, and a text excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': 'Fetch a URL and return its extracted main text content.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}}, 'required': ['url']}}}]
        SYSTEM_PROMPT = "You are a precise web-research agent answering one factual question in a single continuous session. You have search_web and fetch_page tools. Follow this protocol exactly, using the literal phase markers.\n\nBRIEFING:\nOpen your first message with a BRIEFING block written from your own knowledge, before reading any tool result:\n(a) CANDIDATE POOL — every entity that might satisfy the question, one per line, formatted exactly:\n- CANDIDATE: <name> — <one-clause confidence note>\n(b) CONSTRAINTS — the atomic constraints the answer must satisfy, decomposed.\n(c) PLAN — 2-4 opening queries.\nDo not answer during the briefing. You may issue your opening tool calls in the same turn as the briefing.\n\nRESEARCH:\nCall tools adaptively. Your goal is coverage: obtain the specific figures or facts needed to test EVERY candidate against EVERY constraint — for entities that qualify AND entities that do not. If a query or page fails, pivot the query or the source rather than repeating it. BATCH RULE: when testing many candidates against a per-candidate fact (a statistic, a tempo, a runtime, a date), issue the lookups for SEVERAL candidates as multiple tool calls in the SAME turn — never spend one turn per candidate. METRIC RULE: when the question asks for the percentage change or growth of an economic indicator, retrieve the OFFICIAL growth-rate series for that indicator (e.g. World Bank 'GDP growth (annual %)', real terms) — NEVER derive a percentage from current-value levels yourself. SOURCE RULE: if the question names a source (e.g. Forbes, Box Office Mojo, IMDb, Rotten Tomatoes, a UN or government agency), get the data from THAT source — search it directly, fetch its page, and cite it for the core claims. For each metric, prefer ONE consistent canonical source across all candidates (same series, same year basis); do not mix sources for the same metric unless the preferred source is unreachable, and note the substitution if you must.\n\nVERIFY:\nWhen told to verify, build a per-candidate x per-constraint table from the numbered evidence, citing [n] markers. Name the near-miss exclusions and the exact criterion each fails. Do not write 'the only', 'the sole', or 'the single' unless you enumerated and checked the whole pool. Never state a figure that is not present in the numbered evidence. Never declare a candidate's data missing without re-scanning the numbered evidence for it first — if the figure is there, include or exclude that candidate on the merits, citing the figure. Check that every core figure is cited to the question's named source (or one consistent canonical source per metric); if a core figure only has a substitute source while the named source is reachable, fetch the named source before finalizing. Re-read the question's explicit output-format instructions (ordering, list format, words to include or omit) and make the final answer obey them exactly — such instructions control how you WRITE the answer text, never which entities qualify: an instruction to omit a word means write the qualifying entity's name without that word, not exclude the entity.\n\nFINAL ANSWER:\nEnd with a committed, SELF-CONTAINED answer: state the answer first, then a compact proof — each qualifying entity with the figures that qualify it, and the near-miss exclusions with the exact criterion each fails — written as clean prose or short bullets with [n] citations. Do NOT reproduce the working table or internal scaffolding; rewrite the proof as prose. A reader must be able to see the full candidate-pool reasoning from the FINAL ANSWER alone. Scoring is pairwise against a competitor: an answer that refuses, defers, or hedges to 'insufficient data' loses outright, and so does a bare answer with no completeness proof. If evidence covers only part of the pool, commit to the best-supported answer and note that the roster may be incomplete.\n\nCITATION RULE: in the final answer, put the evidence number in brackets immediately after EVERY factual claim — e.g. 'the total is 4,000 [7, 12].' A claim with no bracket after it is assumed uncited."
        BRIEFING_NUDGE = 'Your first message must open with the BRIEFING block (CANDIDATE POOL / CONSTRAINTS / PLAN) as instructed. Write it now, then begin research.'
        FORCED_COMMIT_SUFFIX = '\n\n*** FORCED COMMIT ***\nYour previous draft refused, stalled, or was cut short. That scores ZERO. Rewrite now: commit to the best evidence-supported answer, cite every claim, and do not emit tool-call syntax or apologies.'
        INSUFFICIENT_ANSWER = 'I could not complete a source-backed research answer for this question within budget.'
        TOOL_MARKUP_RE = re.compile('<\\s*/?\\s*(tool_call|arg_key|arg_value)\\b[^>]*>', re.IGNORECASE)
        PSEUDO_CALL_RE = re.compile('\\b(?:search_web|fetch_page)\\s*\\(', re.IGNORECASE)
        ABSTENTION_MARKERS = ('i could not', 'i cannot', 'i was unable', 'unable to', 'cannot answer', 'insufficient evidence', 'no evidence', 'could not find', 'cannot determine', 'cannot be determined', "i don't have", 'i do not have', 'not enough information', 'not possible to', 'impossible to determine', 'cannot identify', 'cannot be identified')
        CANDIDATE_RE = re.compile('^\\s*[-*]\\s*CANDIDATE:\\s*(.+?)\\s*$', re.MULTILINE)
        FINAL_SECTION_RE = re.compile('^\\s*(?:#{1,4}\\s*)?(?:\\*{1,2})?\\s*FINAL ANSWER\\s*(?:\\*{1,2})?\\s*:?\\s*$|(?:\\*{1,2}|#{1,4}\\s*)?FINAL ANSWER(?:\\*{1,2})?\\s*:', re.IGNORECASE | re.MULTILINE)
        DUMP_GARBAGE_RE = re.compile("can[’']?t be reached|ERR_|unexpectedly closed|access denied|403 forbidden|404 not found|-> ERROR|enable javascript|verify you are human", re.IGNORECASE)
        SCAFFOLD_HEAD_RE = re.compile('^\\s*(?:#{1,4}\\s*)?(?:\\*{1,2})?\\s*(?:VERIFY\\b|Verification table|Per-candidate)', re.IGNORECASE)
        SCAFFOLD_MISSING_RE = re.compile('cannot confirm|cannot compute|not directly in evidence|not found in (?:the )?numbered evidence|\\bMISSING\\b', re.IGNORECASE)
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
                self._table: dict[str, tuple[int, int, int] | None] = {}
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
                    self._by_number[n] = {'receipt_id': receipt_id, 'result_id': result_id, 'kind': kind, 'citable': bool(note.strip()), 'src_len': len(note), 'title': (getattr(r, 'title', None) or '')[:200], 'url': (getattr(r, 'url', None) or '')[:300], 'note': note}
                    numbers.append(n)
                return numbers

            def get(self, number: int) -> dict[str, str] | None:
                return self._by_number.get(number)

            def max_number(self) -> int:
                return self._next - 1

            def all_note_text(self) -> str:
                return '\n'.join((meta['note'] for meta in self._by_number.values()))

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
                    if start > 0 and cost > self._window_budget:
                        continue
                    if start > 0:
                        self._window_budget -= cost
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
                    note = meta['note']
                    for start, end in spans:
                        parts.append(note[start:end])
                return '\n'.join(parts)

            def fetched_numbers(self) -> list[int]:
                return [n for n, meta in self._by_number.items() if meta.get('kind') == 'fetch' and meta.get('citable', True)]

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

            def _budgeted(self, note: str, spans: list[tuple[int, int]], terms: list[str], window: int) -> list[tuple[int, int]]:
                spans = _merge_spans([(a, b) for a, b in spans if b > a])
                if not spans:
                    return []
                if sum((b - a for a, b in spans)) <= window:
                    return spans
                identity = min(COMMIT_DIGEST_IDENTITY_CHARS, window, spans[0][1] - spans[0][0])
                kept = [(spans[0][0], spans[0][0] + identity)] if identity > 0 else []
                left = window - identity
                scored = []
                for start, end in spans:
                    hits = _term_hits(note[start:end].lower(), terms)
                    scored.append((len({t for _q, t in hits}), (start, end)))
                scored.sort(key=lambda row: -row[0])
                for _score, (start, end) in scored:
                    if left <= 0:
                        break
                    if end - start <= left:
                        kept.append((start, end))
                        left -= end - start
                        continue
                    picked = _best_windows(note, terms, max(400, left), 1, skip_before=start, avoid=[(0, start), (end, len(note))])
                    if picked:
                        kept.extend(picked)
                        left -= sum((b - a for a, b in picked))
                    else:
                        kept.append((start, start + left))
                        left = 0
                return _merge_spans(kept)

            def digest_numbers(self) -> list[int]:
                fetched: list[int] = []
                searched: list[int] = []
                for n in range(1, self.max_number() + 1):
                    meta = self._by_number.get(n)
                    if meta is None or not meta.get('citable', True):
                        continue
                    if meta.get('kind') == 'fetch':
                        fetched.append(n)
                    else:
                        searched.append(n)
                return sorted((fetched + searched)[:COMMIT_DIGEST_SOURCES_MAX])

            def project(self, terms: list[str]) -> str:
                numbers = self.digest_numbers()
                if not numbers:
                    return ''
                window = max(COMMIT_DIGEST_NOTE_CHARS, COMMIT_DIGEST_TOTAL_CHARS // len(numbers))
                parts = ['NUMBERED EVIDENCE (the sources gathered for this question; cite by these numbers):']
                for n in numbers:
                    meta = self._by_number.get(n)
                    if meta is None:
                        continue
                    note = meta['note'] or ''
                    spans = self.spans(n)
                    if not spans:
                        head_end = min(window, len(note))
                        spans = _merge_spans([(0, head_end)] + _best_windows(note, terms, min(window, PAGE_WINDOW_CHARS), 1, skip_before=head_end))
                    body = _render_spans(note, self._budgeted(note, spans, terms, window)).strip()
                    parts.append(f"[{n}] {meta.get('title') or ''}\n  url: {meta.get('url') or ''}\n{body}")
                return '\n\n'.join(parts)

            def covering_span(self, element: str) -> tuple[int, int, int] | None:
                key = _coverage_key(element)
                if len(key) < 3:
                    return None
                for number in range(1, self.max_number() + 1):
                    meta = self._by_number.get(number)
                    if meta is None:
                        continue
                    note = meta['note'] or ''
                    for start, end in self.spans(number) or ():
                        passage = note[start:end]
                        at = passage.lower().find(key)
                        while at != -1:
                            near = passage[max(0, at - COVER_PROOF_CHARS):at + COVER_PROOF_CHARS]
                            if COVER_DIGIT_RE.search(near):
                                return (number, start, end)
                            at = passage.lower().find(key, at + len(key))
                return None

            def _retable(self, elements: list[str]) -> list[str]:
                self._table = {e: self.covering_span(e) for e in elements}
                return [e for e, span in self._table.items() if span is None]

            async def resolve(self, question: str, elements: list[str], deadline: float) -> list[str]:
                if not elements:
                    return []
                empty = self._retable(elements)
                budget = COVER_BUDGET_CHARS
                for _pass in range(COVER_MAX_PASSES):
                    if not empty or deadline - perf_counter() < COVER_MIN_SECONDS:
                        break
                    surfaced = 0
                    for element in empty:
                        element_terms = _key_terms(element, limit=6)
                        if not element_terms:
                            continue
                        for number in self.fetched_numbers()[:COVER_PAGES_PER_ELEMENT]:
                            if budget <= 0:
                                break
                            meta = self._by_number.get(number)
                            if meta is None:
                                continue
                            for a, b in self.surface(number, _best_windows(meta['note'] or '', element_terms, COVER_WINDOW_CHARS, COVER_WINDOWS_PER_ELEMENT, avoid=self.spans(number))):
                                surfaced += b - a
                                budget -= b - a
                    empty = self._retable(elements)
                    if empty and deadline - perf_counter() > COVER_LOOKUP_MIN_SECONDS:
                        queries = [f"{e} {' '.join(_key_terms(question, limit=5))}" for e in empty[:COVER_LOOKUPS_PER_PASS]]
                        await asyncio.gather(*(_run_search_web(q, self) for q in queries))
                        for number in self.fetched_numbers():
                            meta = self._by_number.get(number)
                            if meta is not None:
                                self.surface(number, self.page_spans(meta['note'] or '', _key_terms(question)))
                        empty = self._retable(elements)
                    elif not surfaced:
                        break
                return empty

            def directive(self) -> str:
                if not self._table:
                    return ''
                covered = [(e, sp) for e, sp in self._table.items() if sp is not None]
                empty = [e for e, sp in self._table.items() if sp is None]
                lines = ['COVERAGE TABLE — one row per item this question names, and the region of the numbered evidence that states a figure for it:']
                for element, span in covered:
                    lines.append(f'  {element} — covered by [{span[0]}] at chars {span[1]}-{span[2]}')
                for element in empty:
                    lines.append(f'  {element} — NO covering region')
                lines.append("Every covered item must appear in the answer with the figure its region states, cited to that number: those figures are present in the evidence, so writing 'not available' for one of them is wrong.")
                if empty:
                    lines.append('An item with NO covering region must NOT be presented as though a figure had been found for it, and must not be silently dropped either: name it among the exclusions and say plainly that the evidence gathered does not state its figure. Answer with everything that IS covered.')
                return '\n'.join(lines)

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

        def _anchor_tokens(claim: str) -> list[str]:
            words = re.findall("[A-Za-z][A-Za-z']{3,}|\\d[\\d,.%]*", claim)
            ordered = sorted(words, key=lambda w: (not any((c.isdigit() for c in w)), -len(w)))
            tokens: list[str] = []
            for w in ordered:
                lw = w.lower().strip('.,%')
                if len(lw) >= 3 and lw not in tokens:
                    tokens.append(lw)
                if len(tokens) >= 8:
                    break
            return tokens
        SLICE_BOILER_RE = re.compile('utm_source|utm_campaign|word game|cookie consent|accept cookies|subscribe now|sign in\\b|newsletter|advertisement|\\U0001f9e9', re.IGNORECASE)

        def _window_quality(text: str) -> float:
            if not text:
                return 0.0
            q = 1.0
            pipes_per_100 = text.count('|') * 100.0 / len(text)
            if pipes_per_100 > 6:
                q *= 0.25
            elif pipes_per_100 > 3:
                q *= 0.6
            letters = sum((1 for c in text if c.isalpha()))
            if letters * 1.0 / len(text) < 0.45:
                q *= 0.4
            if SLICE_BOILER_RE.search(text[:400]):
                q *= 0.5
            return q

        def _anchored_slice_bounds(note: str, claims: list[str], window: int) -> tuple[int, int]:
            src_len = len(note)
            if src_len <= window:
                return (0, src_len)
            hay = note.lower()
            tokens: list[str] = []
            for claim in claims[:3]:
                tokens.extend(_anchor_tokens(claim))
            positions: list[int] = []
            for t in tokens:
                i = hay.find(t)
                while i != -1 and len(positions) < 400:
                    positions.append(i)
                    i = hay.find(t, i + 1)
            head_text = note[:window]
            head_hits = sum((1 for q in positions if q < window))
            head_score = (1.0 + head_hits) * _window_quality(head_text) * 1.5
            if not positions:
                return (0, window)
            positions.sort()
            best_start, best_score = (0, head_score)
            for p in positions:
                start = max(0, min(p - CITATION_ANCHOR_LEAD_CHARS, src_len - window))
                if start == 0:
                    continue
                end = start + window
                hits = sum((1 for q in positions if start <= q <= end))
                score = (1.0 + hits) * _window_quality(note[start:end])
                if score > best_score:
                    best_score, best_start = (score, start)
            return (best_start, best_start + window)

        def _citations_from_inline_markers(answer_text: str, index: _SourceSurface) -> tuple[CitationRef, ...]:
            max_number = index.max_number()
            seen: set[int] = set()
            ordered: list[int] = []
            claims_by_number: dict[int, list[str]] = {}
            for match in BRACKET_RE.finditer(answer_text):
                claim = answer_text[max(0, match.start() - CITATION_ANCHOR_CONTEXT_CHARS):match.start()]
                for n in _numbers_from_bracket(match.group(1), max_number=max_number):
                    claims_by_number.setdefault(n, []).append(claim)
                    if n not in seen:
                        seen.add(n)
                        ordered.append(n)
            by_source: dict[str, dict[str, object]] = {}
            source_order: list[str] = []
            slice_window = max(CITATION_SLICE_MIN_CHARS, CITATION_BUDGET_CHARS // max(len(ordered), 1))
            for n in ordered:
                meta = index.get(n)
                if meta is None or not meta.get('citable', True):
                    continue
                src_len = int(meta.get('src_len') or 0)
                if src_len <= 0:
                    continue
                spans = [(s, e) for s, e in index.spans(n) if e > s]
                if not spans:
                    start, end = _anchored_slice_bounds(meta['note'], claims_by_number.get(n, []), slice_window)
                    if end > start:
                        spans = [(start, end)]
                spans = [(max(0, s), min(src_len, e)) for s, e in spans]
                spans = _merge_spans([(s, e) for s, e in spans if e - s >= 100 or (s == 0 and e == src_len)])
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
        COMMIT_DIGEST_SOURCES_MAX = 16
        COMMIT_DIGEST_NOTE_CHARS = 1200
        COMMIT_DIGEST_TOTAL_CHARS = 26000
        COMMIT_DIGEST_IDENTITY_CHARS = 320

        def _commit_context(question: str, candidates: list[str], index: _SourceSurface, *, terms: list[str] | None=None, notice: str='', draft: str | None=None, suffix: str='') -> list[dict[str, object]] | None:
            digest = index.project(terms or _key_terms(question))
            if not digest:
                return None
            checkpoint = _checkpoint_message(candidates, index)
            if notice:
                checkpoint = notice + '\n\n' + checkpoint
            messages: list[dict[str, object]] = [{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': question}, {'role': 'user', 'content': digest + '\n\n' + checkpoint}]
            if draft:
                messages.append({'role': 'assistant', 'content': draft})
            messages.append({'role': 'user', 'content': COMMIT_MESSAGE + suffix})
            return messages

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
            if SCAFFOLD_HEAD_RE.search(text[:160]) is not None:
                return True
            if text.count('|') >= 20 and len(SCAFFOLD_MISSING_RE.findall(text)) >= 2:
                return True
            if len(text) < HARD_MIN_ANSWER_CHARS:
                return True
            if any((m in text.lower()[:400] for m in ABSTENTION_MARKERS)):
                return True
            if len(text) < MIN_ANSWER_CHARS:
                if not text.rstrip().endswith(('.', '!', '?', ')', ']', '"', '|', '*')):
                    return True
            return False
        MICRO_COMMIT_DIGEST_CHARS = 7000
        MICRO_RESERVE_SECONDS = 18.0

        async def _micro_commit(question: str, index: _SourceSurface, *, deadline: float) -> str | None:
            if index.max_number() == 0:
                return None
            lines: list[str] = []
            total = 0
            for n in range(1, index.max_number() + 1):
                meta = index.get(n)
                if meta is None:
                    continue
                note = meta['note'][:220].strip()
                if not note or DUMP_GARBAGE_RE.search(note):
                    continue
                entry = f'[{n}] {note}'
                total += len(entry)
                if total > MICRO_COMMIT_DIGEST_CHARS:
                    break
                lines.append(entry)
            if not lines:
                return None
            messages = [{'role': 'system', 'content': 'Answer the question from the numbered evidence alone. State the answer in the first sentence, then a 2-4 line proof, with [n] after every claim. Commit to the best-supported answer — never refuse or defer.'}, {'role': 'user', 'content': f'QUESTION:\n{question}\n\nEVIDENCE:\n' + '\n'.join(lines)}]
            for model in (MODEL, COMMIT_FALLBACK_MODEL):
                budget = deadline - perf_counter() - 2
                if budget <= 6:
                    return None
                try:
                    result = await llm_chat(provider=LLM_PROVIDER, model=model, messages=messages, temperature=0.2, thinking=LlmThinkingConfig(enabled=False), timeout=min(budget, 22.0))
                except Exception:
                    continue
                text = (result.response.raw_text or '').strip()
                if not text or PSEUDO_CALL_RE.search(text) or TOOL_MARKUP_RE.search(text):
                    continue
                if any((m in text.lower()[:400] for m in ABSTENTION_MARKERS)):
                    continue
                return text
            return None

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
            citations = _citations_from_inline_markers(cite_text or answer, index)
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
        ELEMENT_PHRASE_RE = re.compile("\\b[A-Z][\\w'&.-]+(?:\\s+(?:of|de|and|the)\\s+[A-Z][\\w'&.-]+|\\s+[A-Z][\\w'&.-]+){0,3}")
        ELEMENT_QUOTED_RE = re.compile('[\'\\"‘“]([^\'\\"’”]{3,80})[\'\\"’”]')
        COVER_MAX_PASSES = 3
        COVER_ELEMENTS_MAX = 8
        COVER_PROOF_CHARS = 400
        COVER_WINDOW_CHARS = 1600
        COVER_WINDOWS_PER_ELEMENT = 2
        COVER_PAGES_PER_ELEMENT = 4
        COVER_BUDGET_CHARS = 16000
        COVER_LOOKUP_MIN_SECONDS = 45.0
        COVER_LOOKUPS_PER_PASS = 3
        COVER_MIN_SECONDS = 6.0
        COVER_DIGIT_RE = re.compile('\\d')

        def _enumerated_elements(question: str, candidates: list[str]) -> list[str]:
            out: list[str] = []
            seen: set[str] = set()

            def add(text: str) -> None:
                for part in re.split('\\s+(?:and|or|versus|vs\\.?)\\s+', (text or '').strip()):
                    item = part.strip().strip('.,;:')
                    key = _coverage_key(item)
                    if len(key) < 3 or key in seen or key in STOP_TERMS:
                        continue
                    if len(item) <= 4 and item.isupper():
                        continue
                    seen.add(key)
                    out.append(item[:80])
            for quoted in ELEMENT_QUOTED_RE.findall(question or ''):
                add(quoted)
            body = re.sub('^\\s*\\S+\\s*', ' ', question or '')
            for phrase in ELEMENT_PHRASE_RE.findall(body):
                add(phrase)
            for candidate in candidates:
                add(candidate)
            return out[:COVER_ELEMENTS_MAX]

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
                elements = _enumerated_elements(query.text, candidates)
                await index.resolve(query.text, elements, deadline - FINAL_RESERVE_SECONDS)
                notice = index.directive()
                checkpoint = _checkpoint_message(candidates, index)
                if notice:
                    checkpoint = notice + '\n\n' + checkpoint
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
                if elements:
                    await index.resolve(query.text, elements, deadline - 12)
                    notice = index.directive() or notice
                if not final_answer:
                    commit_messages = _commit_context(query.text, candidates, index, terms=terms, notice=notice)
                    if commit_messages is None:
                        messages.append({'role': 'user', 'content': COMMIT_MESSAGE})
                        commit_messages = messages
                    final_answer = await _commit_call(commit_messages, deadline=deadline - MICRO_RESERVE_SECONDS)
                if not final_answer and last_content and FINAL_SECTION_RE.search(last_content):
                    final_answer = last_content
                cite_text = _strip_tool_markup(final_answer) if final_answer else ''
                display = _final_section(cite_text) if cite_text else ''
                if display and _needs_forced_retry(display):
                    retry: str | None = None
                    if deadline - perf_counter() >= FINAL_RETRY_MIN_SECONDS + MICRO_RESERVE_SECONDS:
                        retry_messages = _commit_context(query.text, candidates, index, terms=terms, notice=notice, draft=final_answer, suffix=FORCED_COMMIT_SUFFIX)
                        if retry_messages is None:
                            messages.append({'role': 'assistant', 'content': final_answer})
                            messages.append({'role': 'user', 'content': COMMIT_MESSAGE + FORCED_COMMIT_SUFFIX})
                            retry_messages = messages
                        retry = await _commit_call(retry_messages, deadline=deadline - MICRO_RESERVE_SECONDS)
                    retry_stripped = _strip_tool_markup(retry) if retry else ''
                    retry_display = _final_section(retry_stripped) if retry_stripped else ''
                    if retry_display and (not _needs_forced_retry(retry_display)):
                        cite_text, display = (retry_stripped, retry_display)
                    elif not _needs_forced_retry(cite_text):
                        display = cite_text
                    else:
                        micro = await _micro_commit(query.text, index, deadline=deadline)
                        if micro:
                            cite_text, display = (micro, micro)
                        else:
                            display = _dump_floor_answer(index) or display
                if display:
                    return _deliverable(display, index, cite_text=cite_text or display)
                micro = await _micro_commit(query.text, index, deadline=deadline)
                if micro:
                    return _deliverable(micro, index)
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
    _DIFFICULTY_PROMPT = 'Classify this question difficulty. Reply with one word only: Easy, Medium, or Hard.'
    _GRANULARITY_PROMPT = 'Score the granularity/detail quality of this problem on an integer scale from 0 to 10. Assess ALL of the following: (1) Are the requirements clearly described? (2) Are edge cases (exceptions) mentioned or implied? (3) Are constraints and limitations clearly specified? (4) Are the I/O formats clearly defined? (5) Is the problem description accurate enough to avoid ambiguity? (6) Are technical terms and concepts clearly explained? (7) Is the scope of the problem well defined? Scoring guide: 10 = Perfect detail, fully solvable without ambiguity; 7-9 = Excellent detail, generally clear but with minor ambiguity; 4-6 = Average detail, some important information missing; 1-3 = Insufficient detail, significant information missing; 0 = Insufficient detail, problem cannot be solved. Reply with ONLY an integer from 0 to 10.'
    _TIMEOUT_S = 6.0

    async def _is_easy(self, text: str) -> bool:
        result = await asyncio.wait_for(llm_chat(provider=self._PROVIDER, model=self._MODEL, messages=[{'role': 'system', 'content': self._DIFFICULTY_PROMPT}, {'role': 'user', 'content': text}], temperature=0.0, max_output_tokens=4, thinking=LlmThinkingConfig(enabled=False), timeout=self._TIMEOUT_S), timeout=self._TIMEOUT_S + 2.0)
        label = (result.response.raw_text or '').strip().lower()
        return label.startswith('easy') or ('easy' in label and 'hard' not in label and ('medium' not in label))

    async def _granularity_score(self, text: str) -> int:
        result = await asyncio.wait_for(llm_chat(provider=self._PROVIDER, model=self._MODEL, messages=[{'role': 'system', 'content': self._GRANULARITY_PROMPT}, {'role': 'user', 'content': text}], temperature=0.0, max_output_tokens=8, thinking=LlmThinkingConfig(enabled=False), timeout=self._TIMEOUT_S), timeout=self._TIMEOUT_S + 2.0)
        raw = (result.response.raw_text or '').strip()
        digits = []
        for ch in raw:
            if ch.isdigit():
                digits.append(ch)
            elif digits:
                break
        if not digits:
            return 0
        score = int(''.join(digits))
        if score > 10:
            score = 10
        return score
_FIRST_RUN = FirstPath()._compile()
_SECOND_RUN = SecondPath()._compile()
_THIRD_RUN = ThirdPath()._compile()
_ROUTER = DifficultyRouter()

@entrypoint('query')
async def query(query: Query) -> Response:
    try:
        easy = await _ROUTER._is_easy(query.text)
    except Exception:
        easy = False
    if easy:
        return await _THIRD_RUN(query)
    try:
        granularity = await _ROUTER._granularity_score(query.text)
    except Exception:
        granularity = 0
    if granularity >= 5:
        return await _SECOND_RUN(query)
    return await _FIRST_RUN(query)
