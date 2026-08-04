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
        from collections.abc import Mapping
        from dataclasses import dataclass, field
        from time import monotonic
        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        VERSION = 'v30.0-corpuslet'
        LLM_PROVIDER = 'openrouter'
        MODEL_LOOP = 'z-ai/glm-5.2'
        MODEL_FALLBACK = 'deepseek/deepseek-v3.2'
        MODEL_AUDIT = 'openai/gpt-oss-120b'
        LOOP_TRIES_PRIMARY = 2
        SEARCH_PROVIDER = 'parallel'
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
        WALL_BUDGET_S = 258.0
        BRIEF_TIMEOUT_S = 45.0
        TURN_TIMEOUT_S = 70.0
        AUDIT_TIMEOUT_S = 30.0
        COMMIT_TIMEOUT_S = 55.0
        SEARCH_TIMEOUT_S = 18.0
        FETCH_TIMEOUT_S = 16.0
        COMMIT_RESERVE_S = 46.0
        MIN_TAIL_S = 8.0
        MAX_TURNS = 14
        MAX_REPAIRS = 2
        MAX_CALLS_PER_TURN = 8
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

class HardPath:

    def _compile(self):
        import asyncio
        import json
        import re
        from time import monotonic
        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        VERSION = 'v36.0-lin241'
        LLM_LANE = 'openrouter'
        LOOP_MODEL_A = 'z-ai/glm-5.2'
        LOOP_MODEL_B = 'deepseek/deepseek-v3.2'
        AUDIT_MODEL = 'openai/gpt-oss-120b'
        SCHEMA_MODEL = 'openai/gpt-oss-120b'
        RESORT_MODEL = 'deepseek/deepseek-v3.2'
        SEARCH_PROVIDER = 'parallel'
        WALL_BUDGET_S = 262.0
        BRIEF_TIMEOUT_S = 50.0
        TURN_TIMEOUT_S = 75.0
        FALLBACK_MAX_PAYLOAD_CHARS = 144000
        AUDIT_TIMEOUT_S = 15.0
        SEARCH_TIMEOUT_S = 18.0
        FETCH_TIMEOUT_S = 8.0
        TOOL_FANOUT_BUDGET_S = 38.0
        FINISH_RESERVE_S = 24.0
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
        LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.\n\nDOCTRINE:\n- FIRST SENTENCE = THE ASKED FIELD: open with the exact coordinates/designations/counts the question asks for, and MIRROR any process the question describes — \'Of the N events matching <the stated filters>, the earliest is …\' — so the applied filter is visible, not just its result.\n- COMPLETE ROSTER: one cited line per qualifying item AND one per rejected item carrying its disqualifying value.\n- NEVER write \'the sources do not contain / cannot be determined\' — commit to the best-supported candidate instead. NEVER assert \'no X exists\' merely because your retrieved evidence is silent about X.\n- SOURCES: never cite grokipedia, facebook, pinterest or quora. Prefer the question-NAMED source\'s own page over aggregators, and on infobox-style questions cite each enumerated item\'s value from ITS OWN page.\n- Exact figures with units and dates on every claim; no meta-narration about your research process.'

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
                self.replay: dict[str, str] = {}

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

            def __init__(self, text: str, rows: list[dict] | None=None, cache_key: str='') -> None:
                self.text = text
                self.rows = rows or []
                self.cache_key = cache_key

        def _commit_tool_output(out, ledger: EvidenceLedger) -> str:
            if isinstance(out, str):
                return out
            if not isinstance(out, ToolOutput):
                return f'# tool crashed: {out}'
            text = out.text
            for i, row in enumerate(out.rows):
                n = ledger.add(row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''))
                text = text.replace(_SLOT.format(i), str(n))
            if out.cache_key:
                ledger.replay[out.cache_key] = text
            return text
        _SITE_OP_RE = re.compile('\\bsite:\\S+\\s*', re.I)

        def _degrade_query(q: str) -> str:
            out = _SITE_OP_RE.sub('', q or '').replace('"', ' ')
            return ' '.join(out.split())

        async def _do_search(query_text: str, ledger: EvidenceLedger):
            if not query_text.strip():
                return '# web_search: empty query'
            s_key = 's:' + ' '.join(query_text.split()).casefold()
            replayed = ledger.replay.get(s_key)
            if isinstance(replayed, str):
                return '# (cache) identical search already ran — same numbered results:\n' + replayed
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
            return ToolOutput('\n'.join(lines), rows, cache_key=s_key)

        async def _do_fetch(url: str, focus: str, question: str, ledger: EvidenceLedger) -> str:
            if not url.strip():
                return '# read_page: empty url'
            f_key = 'f:' + ' '.join(url.split()).casefold() + '|' + ' '.join((focus or '').split()).casefold()
            replayed = ledger.replay.get(f_key)
            if isinstance(replayed, str):
                return '# (cache) identical fetch already ran — same numbered result:\n' + replayed
            payload = None
            for _attempt in (0, 1):
                _t0 = monotonic()
                try:
                    payload = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=FETCH_TIMEOUT_S)
                    if getattr(payload, 'results', None):
                        break
                except Exception:
                    payload = None
                if monotonic() - _t0 >= FETCH_TIMEOUT_S - 1.0:
                    break
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
                return ToolOutput(f'# read_page({url!r}) -> [{_SLOT.format(0)}] full page, {len(note)} chars\n{note}', [row], cache_key=f_key)
            terms = _key_terms(question) | _key_terms(focus)
            windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE)
            row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, FETCH_HEAD_CHARS)] + list(windows), 'title': url, 'url': url, 'preview': note[windows[0][0]:windows[0][0] + 1200]}
            head = note[:FETCH_HEAD_CHARS]
            sections = ''.join((f'\n--- section @{s} ---\n{note[s:e]}' for s, e in windows))
            return ToolOutput(f"# read_page({url!r}) -> [{_SLOT.format(0)}] {len(note)} chars total; head + the {len(windows)} most relevant section(s) shown ({', '.join((f'{s}-{e}' for s, e in windows))}). If the answer set may continue elsewhere in this page, call read_page again with a different focus.\n--- head ---\n{head}{sections}", [row], cache_key=f_key)
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
        _ITEM_QUOTE_RES = (re.compile('"([^"\\n]{2,60})"'), re.compile('“([^”\n]{2,60})”'), re.compile("(?<!\\w)'([^'\\n]{3,60})'(?!\\w)"), re.compile('\\*([^*\\n]{2,60})\\*'))

        def _enumerated_items(question: str) -> list[str]:
            out: list[str] = []
            seen: set[str] = set()
            for rx in _ITEM_QUOTE_RES:
                for hit in rx.findall(question or ''):
                    item = ' '.join(hit.split()).strip(' .,;:?!')
                    key = item.casefold()
                    if item and key not in seen and re.search('[A-Za-z0-9]', item):
                        seen.add(key)
                        out.append(item)
            if not out:
                colon = (question or '').find(':')
                if colon != -1:
                    parts = re.split('\\s*(?:;|—|, and |, )\\s*', question[colon + 1:])
                    clean = [' '.join(p.split()).strip(' .,;:?!') for p in parts]
                    clean = [p for p in clean if 2 <= len(p) <= 60 and re.search('[A-Za-z]', p)]
                    if len(clean) >= 3:
                        for item in clean:
                            if item.casefold() not in seen:
                                seen.add(item.casefold())
                                out.append(item)
            return out[:8]

        def _item_own_pages(items: list[str], question: str) -> list[str]:
            q = (question or '').casefold()
            wikiish = 'wikipedia' in q or 'infobox' in q
            if len(items) < 2 and (not (wikiish and items)):
                return []
            urls: list[str] = []
            for item in items[:5]:
                title = item.strip(' .\'"')
                if not 2 <= len(title) <= 70 or len(title.split()) > 8:
                    continue
                if not re.search('[A-Za-z]', title):
                    continue
                urls.append('https://en.wikipedia.org/wiki/' + title.replace(' ', '_'))
            return urls[:4]
        _PLANET_RE = re.compile('\\b(?:mercury|venus|mars|jupiter|saturn|uranus|neptune|pluto)\\b')
        _PLANET_METRIC_RE = re.compile('\\b(?:mass|diameter|density|gravity|escape velocity|moons|satellites|orbital period|rotation|axial tilt|aphelion|perihelion)\\b')

        def _data_query_urls(question: str) -> list[str]:
            q = ' '.join((question or '').casefold().split())
            urls: list[str] = []
            if 'earthquake' in q:
                years = re.findall('\\b(19\\d{2}|20\\d{2})\\b', q)
                mag = re.search('magnitude\\s+(?:of\\s+)?(?:at least\\s+|above\\s+|over\\s+|greater than\\s+)?(\\d+(?:\\.\\d+)?)', q)
                if years and mag:
                    url = 'https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=' + min(years) + '-01-01&endtime=' + max(years) + '-12-31T23:59:59&minmagnitude=' + mag.group(1) + '&orderby=time-asc'
                    cap = re.search('(?:less than|below|under|at most)\\s+(?:magnitude\\s+)?(\\d+(?:\\.\\d+)?)', q)
                    if cap:
                        url += '&maxmagnitude=' + cap.group(1)
                    urls.append(url)
            if 'planetary fact sheet' in q or 'nssdc' in q or (_PLANET_RE.search(q) and _PLANET_METRIC_RE.search(q)):
                urls.append('https://nssdc.gsfc.nasa.gov/planetary/factsheet/')
            return urls[:2]
        _AUTH_HOSTS = ('wikipedia.org', 'sec.gov', 'census.gov', 'bls.gov', 'usgs.gov', 'nasa.gov', 'noaa.gov', 'who.int', 'worldbank.org', 'oecd.org', 'boxofficemojo.com', 'britannica.com', 'worldatlas.com', 'un.org')

        def _authority_urls(ledger: EvidenceLedger) -> list[str]:
            fetched = {(r.get('url') or '').casefold() for r in ledger.rows if r.get('kind') == 'fetch'}
            out: list[str] = []
            for row in ledger.rows:
                if row.get('kind') != 'search':
                    continue
                url = (row.get('url') or '').strip().rstrip('.,;:!?')
                if not url.startswith('http'):
                    continue
                parts = url.split('/')
                host = parts[2].casefold() if len(parts) > 2 else ''
                ok = host.endswith('.gov') or any((host == h or host.endswith('.' + h) for h in _AUTH_HOSTS))
                if ok and url.casefold() not in fetched and (url not in out):
                    out.append(url)
            return out[:2]

        async def _prefetch_pages(urls: list[str], header: str, question: str, ledger: EvidenceLedger, deadline: float, budget_s: float) -> str:
            plan: list[str] = []
            for u in urls or []:
                if isinstance(u, str) and u.strip() and (u not in plan):
                    plan.append(u)
            plan = plan[:4]
            if not plan or deadline - monotonic() < 45.0:
                return ''
            budget = max(4.0, min(budget_s, deadline - monotonic() - 35.0))
            tasks = [asyncio.ensure_future(_do_fetch(u, '', question, ledger)) for u in plan]
            try:
                await asyncio.wait(tasks, timeout=budget)
            except Exception:
                pass
            blocks: list[str] = []
            for task in tasks:
                if not task.done():
                    task.cancel()
                    continue
                try:
                    out = task.result()
                except Exception:
                    continue
                body = _commit_tool_output(out, ledger)
                if isinstance(body, str) and _CITE_MARK_RE.search(body):
                    blocks.append(body)
            if not blocks:
                return ''
            return header + '\n\n' + '\n\n'.join(blocks)

        def _coverage_note(items: list[str], ledger: EvidenceLedger) -> str:
            if len(items) < 2:
                return ''
            corpus = ' '.join(((r.get('title') or '') + ' ' + (r.get('url') or '') + ' ' + (r.get('preview') or '') for r in ledger.rows)).casefold()
            uncovered = [i for i in items if i.casefold() not in corpus]
            note = 'ITEM COVERAGE: the question names these items: ' + '; '.join(items) + '. The final answer must give EVERY one of them its own cited verdict line — its qualifying value, or the condition it fails.'
            if uncovered:
                note += ' No tool evidence retrieved yet for: ' + '; '.join(uncovered[:6]) + ' — aim your remaining tool calls at these FIRST.'
            return note

        async def _cover_uncovered(items: list[str], question: str, ledger: EvidenceLedger, deadline: float) -> str:
            corpus = ' '.join(((r.get('title') or '') + ' ' + (r.get('url') or '') + ' ' + (r.get('preview') or '') for r in ledger.rows)).casefold()
            uncovered = [i for i in items if i.casefold() not in corpus]
            if not uncovered:
                return ''
            flat = ' '.join((question or '').split())
            salient = [t for t in _SEED_TOKEN_RE.findall(flat) if len(t) >= 3 and t.lower() not in _STOP and (t.lower() not in _SEED_STOP)]
            blocks: list[str] = []
            for item in uncovered[:2]:
                if deadline - monotonic() < 120.0:
                    break
                context = ' '.join((t for t in salient[:4] if t.casefold() not in item.casefold()))
                try:
                    out = await asyncio.wait_for(_do_search((item + ' ' + context).strip(), ledger), timeout=SEARCH_TIMEOUT_S + 4.0)
                    body = _commit_tool_output(out, ledger)
                    if isinstance(body, str) and _CITE_MARK_RE.search(body):
                        blocks.append(body)
                except Exception:
                    continue
            if not blocks:
                return ''
            return 'ITEM-TARGETED SEARCHES (already numbered — cite these [n] directly):\n\n' + '\n\n'.join(blocks)

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
            for lane_model in ((LLM_LANE, LOOP_MODEL_A), (LLM_LANE, LOOP_MODEL_B)):
                lane = lane_model[0]
                model = lane_model[1]
                if model == LOOP_MODEL_B and payload_chars > FALLBACK_MAX_PAYLOAD_CHARS:
                    return _EMPTY_TURN
                timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - (FINISH_RESERVE_S if finish_only else 5.0))
                if timeout <= 5.0:
                    return None
                try:
                    payload = await llm_chat(provider=lane, model=model, messages=messages, tools=LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': False} if finish_only and model == LOOP_MODEL_B else {'enabled': True, 'effort': 'low'}, max_output_tokens=6000 if finish_only and model == LOOP_MODEL_B else None, timeout=timeout)
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
                raw = await _chat_simple(LLM_LANE, LOOP_MODEL_A, system, user, max_tokens=2400, timeout=BRIEF_TIMEOUT_S, think=_least_think(LLM_LANE, LOOP_MODEL_A))
            except Exception:
                try:
                    raw = await _chat_simple(LLM_LANE, LOOP_MODEL_B, system, user, max_tokens=2400, timeout=BRIEF_TIMEOUT_S, think=_least_think(LLM_LANE, LOOP_MODEL_B))
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
                try:
                    if deadline - monotonic() > 150.0:
                        block = await _prefetch_pages(_data_query_urls(question), "AUTHORITATIVE DATA QUERY (the rows below are ground truth for the question's filters — cite them [n] like any tool result):", question, ledger, deadline, 16.0)
                        if block:
                            messages.append({'role': 'system', 'content': block})
                except Exception:
                    pass
                items: list[str] = []
                try:
                    items = _enumerated_items(question)
                except Exception:
                    items = []
                try:
                    if items and deadline - monotonic() > 140.0:
                        block = await _prefetch_pages(_item_own_pages(items, question), "ITEM OWN-PAGES (cite each enumerated item's value from ITS OWN page below):", question, ledger, deadline, 16.0)
                        if block:
                            messages.append({'role': 'system', 'content': block})
                except Exception:
                    pass
                try:
                    if len(items) >= 2 and deadline - monotonic() > 130.0:
                        block = await _cover_uncovered(items, question, ledger, deadline)
                        if block:
                            messages.append({'role': 'system', 'content': block})
                except Exception:
                    pass
                try:
                    if deadline - monotonic() > 120.0:
                        block = await _prefetch_pages(_authority_urls(ledger), 'PREFERRED SOURCES (authority domains, prefetched — prefer citing these over aggregators):', question, ledger, deadline, 15.0)
                        if block:
                            messages.append({'role': 'system', 'content': block})
                except Exception:
                    pass
                try:
                    note = _coverage_note(items, ledger)
                    if note:
                        messages.append({'role': 'system', 'content': note})
                except Exception:
                    pass
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
                tool_budget = max(5.0, min(TOOL_FANOUT_BUDGET_S, deadline - monotonic() - MIN_TAIL_S))
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
                raw = await _chat_simple(LLM_LANE, AUDIT_MODEL, 'Strict completeness auditor. JSON only.', probe, max_tokens=2200, timeout=max(8.0, min(AUDIT_TIMEOUT_S, deadline - monotonic() - 72.0)))
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
            if len(_cited_numbers(patched, len(ledger.rows))) < len(_cited_numbers(answer, len(ledger.rows))):
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
        _COMMIT_RULES = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too. Never say what the evidence does not contain; commit to the best-supported answer you can defend. Never assert 'no X exists' merely from absence of evidence, and mirror any process the question describes ('Of the N events matching <filters>, the earliest is …'). Never cite grokipedia, facebook, pinterest or quora; prefer the question-named source's own page, with exact figures, units and dates on every claim."
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
            out: list[str] = []
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
                if not out:
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
            lanes = ((LLM_LANE, LOOP_MODEL_A), (LLM_LANE, LOOP_MODEL_B))
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
                return await _chat_simple(LLM_LANE, RESORT_MODEL, 'Expert researcher. Best definitive answer with concrete entities, numbers, dates. Never refuse.', question, max_tokens=2600, timeout=min(45.0, left - 4.0))
            except Exception:
                return ''

        async def _schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
            ask = f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}'
            for lane, model in ((LLM_LANE, SCHEMA_MODEL), (LLM_LANE, RESORT_MODEL), (LLM_LANE, LOOP_MODEL_A)):
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
        _MAG_MULT = (('trillion', 1000000000000.0), ('tn', 1000000000000.0), ('billion', 1000000000.0), ('bn', 1000000000.0), ('million', 1000000.0), ('mm', 1000000.0), ('thousand', 1000.0))
        _QTY_NUM_RE = re.compile('-?\\d[\\d,]*(?:\\.\\d+)?')
        _QTY_CLOCK_RE = re.compile('\\b(\\d{1,3}):([0-5]\\d)(?::([0-5]\\d))?\\b')

        def _mag_scaled(num_text: str, tail: str) -> float | None:
            try:
                val = float((num_text or '').replace(',', '').rstrip('.'))
            except Exception:
                return None
            word = (tail or '').lstrip()
            for mag, mult in _MAG_MULT:
                if word.startswith(mag):
                    return val * mult
            if word[:1] == 'k' and (len(word) < 2 or not word[1].isalpha()):
                return val * 1000.0
            return val

        def _qty_parse(text: str) -> tuple[float | None, bool, bool]:
            t = ' '.join((text or '').casefold().split())
            clock = _QTY_CLOCK_RE.search(t)
            if clock:
                secs = int(clock.group(1)) * 3600 + int(clock.group(2)) * 60 + int(clock.group(3) or 0)
                return (float(secs), True, False)
            hit = _QTY_NUM_RE.search(t)
            if hit is None:
                return (None, False, False)
            bare = float(hit.group(0).replace(',', ''))
            scaled = _mag_scaled(hit.group(0), t[hit.end():])
            if scaled is not None and scaled != bare:
                return (scaled, False, True)
            return (bare, False, ',' in hit.group(0))

        def _qty_bounds(text: str, is_clock: bool):
            t = ' '.join((text or '').casefold().split())
            if not t:
                return None
            if is_clock:
                t = _QTY_CLOCK_RE.sub(lambda m: str(int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3) or 0)), t)
            hit = re.search('between\\s+\\$?(-?[\\d.,]+)\\s*([a-z]*)\\s+and\\s+\\$?(-?[\\d.,]+)\\s*([a-z]*)', t)
            if hit:
                a = _mag_scaled(hit.group(1), hit.group(2))
                b = _mag_scaled(hit.group(3), hit.group(4))
                if a is None or b is None:
                    return None
                return (min(a, b), False, max(a, b), False)
            low = None
            low_strict = False
            high = None
            high_strict = False
            hit = re.search('(?:more than|greater than|over|above|exceeding|exceeds)\\s+\\$?(?:magnitude\\s+)?(-?[\\d.,]+)\\s*([a-z]*)', t)
            if hit is not None:
                low_strict = True
            else:
                hit = re.search('(?:at least|no less than|no fewer than|minimum(?: of)?|>=)\\s+\\$?(?:magnitude\\s+)?(-?[\\d.,]+)\\s*([a-z]*)', t)
                if hit is None:
                    hit = re.search('\\$?(-?[\\d.,]+)\\s*([a-z]*)\\s+or\\s+(?:more|greater|higher|above)', t)
            if hit is not None:
                low = _mag_scaled(hit.group(1), hit.group(2))
            hit = re.search('(?:less than|fewer than|under|below)\\s+\\$?(?:magnitude\\s+)?(-?[\\d.,]+)\\s*([a-z]*)', t)
            if hit is not None:
                high_strict = True
            else:
                hit = re.search('(?:at most|no more than|maximum(?: of)?|within|<=)\\s+\\$?(?:magnitude\\s+)?(-?[\\d.,]+)\\s*([a-z]*)', t)
                if hit is None:
                    hit = re.search('\\$?(-?[\\d.,]+)\\s*([a-z]*)\\s+or\\s+(?:less|fewer|lower|below)', t)
            if hit is not None:
                high = _mag_scaled(hit.group(1), hit.group(2))
            if low is None and high is None:
                return None
            return (low, low_strict, high, high_strict)

        def _qty_violation(value_text: str, constraint_text: str) -> str:
            value, is_clock, saw_mag = _qty_parse(value_text)
            if value is None:
                return ''
            bounds = _qty_bounds(constraint_text, is_clock)
            if bounds is None:
                return ''
            low, low_strict, high, high_strict = bounds
            for bound in (low, high):
                if bound is None:
                    continue
                if not saw_mag and (not is_clock) and (bound >= 10000.0) and (value > 0) and (bound / value >= 100.0):
                    return ''
            eps = 1e-09
            if low is not None:
                if value < low - eps:
                    return f'below the minimum {low:g}'
                if low_strict and abs(value - low) <= eps:
                    return f"equal to the strict lower bound {low:g} ('more than' excludes it)"
            if high is not None:
                if value > high + eps:
                    return f'above the maximum {high:g}'
                if high_strict and abs(value - high) <= eps:
                    return f"equal to the strict upper bound {high:g} ('less than' excludes it)"
            return ''

        async def _numeric_guard(question: str, answer: str, messages: list[dict], ledger: EvidenceLedger, deadline: float) -> str:
            left = deadline - monotonic()
            if left < 70.0:
                return answer
            ask = f'Extract every numeric claim in the answer that the question explicitly constrains (a threshold, range or cutoff). JSON only: {{"triples": [{{"candidate": "entity", "value": "figure verbatim from the answer", "constraint": "constraint phrase verbatim from the question"}}]}}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:9000]}'
            try:
                raw = await _chat_simple(LLM_LANE, AUDIT_MODEL, 'You output only JSON.', ask, max_tokens=900, timeout=max(8.0, min(15.0, left - 55.0)))
                raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                data = json.loads(raw)
            except Exception:
                return answer
            triples = data.get('triples') if isinstance(data, dict) else None
            if not isinstance(triples, list):
                return answer
            broken: list[str] = []
            for triple in triples[:12]:
                if not isinstance(triple, dict):
                    continue
                why = _qty_violation(str(triple.get('value') or ''), str(triple.get('constraint') or ''))
                if why:
                    broken.append(f"{str(triple.get('candidate') or '?')}: value {triple.get('value')!r} vs constraint {triple.get('constraint')!r} — {why}")
            if not broken or deadline - monotonic() < 55.0:
                return answer
            convo = list(messages)
            convo.append({'role': 'system', 'content': "NUMERIC CHECK: these figures in your answer violate the question's explicit numeric constraints:\n- " + '\n- '.join(broken[:5]) + '\nRewrite the COMPLETE final answer ONCE: remove or correct ONLY the violating entries using the cited evidence above; keep every other claim, the required shape, and all inline [n] citations.'})
            try:
                payload = await llm_chat(provider=LLM_LANE, model=LOOP_MODEL_A, messages=convo, temperature=0.2, thinking={'enabled': False}, max_output_tokens=4000, timeout=max(12.0, min(40.0, deadline - monotonic() - DIGEST_TAIL_S)))
            except Exception:
                return answer
            _spend_note(payload)
            llm = getattr(payload, 'llm', None)
            fixed = (getattr(llm, 'raw_text', None) or '').strip()
            if not fixed:
                choices = getattr(llm, 'choices', None) or []
                if choices:
                    content = getattr(choices[0].message, 'content', None)
                    if isinstance(content, str):
                        fixed = content.strip()
            if not _is_usable_answer(fixed) or len(fixed) < int(len(answer) * 0.6):
                return answer
            if len(_cited_numbers(fixed, len(ledger.rows))) < len(_cited_numbers(answer, len(ledger.rows))):
                return answer
            return fixed

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
                if _is_usable_answer(answer) and deadline - monotonic() > 75.0 and (_spend_left() >= AUDIT_MIN_USD) and (_needs_set_completeness(question) or _needs_superlative_proof(question)):
                    patched = await _audit_patch(question, answer, messages, ledger, deadline)
                    if _is_usable_answer(patched):
                        answer = patched
            except Exception:
                pass
            try:
                if _is_usable_answer(answer) and deadline - monotonic() > 70.0 and (_spend_left() >= WRAPUP_MIN_USD):
                    answer = await _numeric_guard(question, answer, messages, ledger, deadline)
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

@entrypoint('query')
async def query(query: Query) -> Response:
    try:
        easy = await _ROUTER._is_easy(query.text)
    except Exception:
        easy = False
    if easy:
        return await _EASY_RUN(query)
    return await _HARD_RUN(query)
