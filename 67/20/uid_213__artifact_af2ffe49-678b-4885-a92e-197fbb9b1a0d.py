from __future__ import annotations
import asyncio
from harnyx_miner_sdk.api import LlmThinkingConfig, llm_chat
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class FirstPath:

    def _compile(self):
        TASK_TOTAL_BUDGET_SECONDS = 250.0
        import asyncio
        import json
        import re
        from time import perf_counter
        from harnyx_miner_sdk.api import LlmThinkingConfig, fetch_page, llm_chat, search_web, tooling_info
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        from harnyx_miner_sdk.safe_exec import safe_exec
        _AGENT_VARIANT = 'v69_scorelift'
        LLM_PROVIDER = 'openrouter'
        SEARCH_PROVIDER = 'parallel'
        SEARCH_FALLBACK_PROVIDER = 'desearch'
        MODEL = 'z-ai/glm-5.2'
        AUDIT_MODEL = 'openai/gpt-oss-120b'
        SCHEMA_MODEL = 'openai/gpt-oss-120b'
        COMMIT_FALLBACK_MODEL = 'deepseek/deepseek-v3.2'
        CLASSIFIER_MODEL = 'google/gemma-4-31b-it'
        CLASSIFIER_TIMEOUT_SECONDS = 12.0
        FORCE_COMMIT_REMAINING_SECONDS = 90.0
        LLM_TURN_RETRIES = 2
        FETCH_RETRIES = 2
        SEARCH_TIMEOUT_SECONDS = 20.0
        BRIEFING_TIMEOUT_SECONDS = 34.0
        MAX_TURNS = 16
        BRIEFING_MIN_REMAINING = 210.0
        EASY_MAX_TURNS = 7
        TASK_BUDGET_SECONDS = 262.0
        LLM_TURN_TIMEOUT_SECONDS = 75.0
        FINAL_COMMIT_TIMEOUT_SECONDS = 45.0
        FETCH_TIMEOUT_SECONDS = 15.0
        CONCISE_RECOMMIT_MIN_REMAINING = 30.0
        AUDIT_TIMEOUT_SECONDS = 28.0
        AUDIT_MIN_REMAINING = 55.0
        BESTOFN_SYNTH = 1
        BESTOFN_MIN_REMAINING = 115.0
        PRESEED_MIN_REMAINING = 200.0
        MAX_COMMIT_RETRIES = 1
        MAX_SEARCH_FETCH_CALLS = 32
        SEARCH_EXCERPT_CHARS = 700
        SEARCH_AI_EXCERPT_CHARS = 2800
        SEARCH_AI_MAX_RESULTS = 5
        SEARCH_AI_COUNT = 10
        FETCH_EXCERPT_CHARS = 6000
        FETCH_EXTRACT_CHARS = 9000
        _EXTRACT_MODE = {'on': False}
        MAX_CITATIONS = 28
        CITATION_CHAR_BUDGET = 105000
        CITE_MIN_MARKERS = 2
        CITE_FLOOR_N = 4
        TEMPERATURE = 0.2
        MIN_DRAFT_USD = 0.03
        MIN_AUDIT_USD = 0.05
        FORCE_COMMIT_BUDGET_USD = 0.03
        _THINK_OFF = LlmThinkingConfig(enabled=False)
        _THINK_LOW = LlmThinkingConfig(enabled=True, effort='low')

        def _think_for(model):
            return _THINK_LOW if 'gpt-oss' in model else _THINK_OFF
        _SPEND = {'left': None}

        def _spend_note(result):
            b = getattr(result, 'budget', None)
            left = getattr(b, 'session_remaining_budget_usd', None)
            if isinstance(left, (int, float)):
                _SPEND['left'] = float(left)

        def _spend_left():
            v = _SPEND['left']
            return float(v) if isinstance(v, (int, float)) else 1.0
        _SEARCH_TOOL = {'type': 'function', 'function': {'name': 'search_web', 'description': 'Keyword web search. Returns numbered results with title, url, and a short excerpt. Best for a specific named fact.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'search query'}}, 'required': ['query']}}}
        _FETCH_TOOL = {'type': 'function', 'function': {'name': 'fetch_page', 'description': "Fetch a URL: normal pages AND structured JSON APIs (e.g. Wikipedia REST 'https://en.wikipedia.org/api/rest_v1/page/summary/<Title>' or action API '/w/api.php?...&format=json') for exact facts.", 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch (page or JSON API)'}}, 'required': ['url']}}}
        _COMPUTE_TOOL = {'type': 'function', 'function': {'name': 'compute', 'description': "Evaluate exact arithmetic in Python. Assign the answer to `result`, e.g. 'result = 113/130*100'. Use for ALL percentage/ratio/difference/sum/threshold/comparison math.", 'parameters': {'type': 'object', 'properties': {'code': {'type': 'string', 'description': 'Python that assigns the answer to `result`'}}, 'required': ['code']}}}
        TOOLS_ALL = [_SEARCH_TOOL, _FETCH_TOOL, _COMPUTE_TOOL]
        TOOLS_COMPUTE_ONLY = [_COMPUTE_TOOL]
        BRIEFING_PROMPT = "You are planning the research for a factual question. Do NOT answer it yet. Output a short plan with exactly these sections:\nCANDIDATE POOL: the complete set of items the answer ranges over (or the single target entity); if not given, name the set you will enumerate -- list each candidate.\nLOAD-BEARING FACTS: each exact name/date/count/figure to verify, with the EXACT YEAR/time-point.\nQUERIES: 3-6 precise search_web queries (exact names + years; for a hard/obscure fact, plan SEVERAL angles -- exact phrase, entity+metric+year, and a primary-source 'site:' query).\nOFFICIAL SOURCES: specific primary/official pages/APIs to fetch directly (or 'none').\nThen output a CLASSIFY block on its own lines, exactly these six labels:\nCLASSIFY\nDIFFICULTY: easy or hard  (easy = a single well-known fact with one clear answer; hard = multiple candidates/constraints, enumeration, numeric computation, multi-hop chaining, comparison, or an obscure/uncertain fact)\nANSWER_TYPE: single_fact or enumerate or numeric or multi_hop\nCANDIDATES: <integer number of candidate entities>\nCONSTRAINTS: <integer number of atomic constraints in the question>\nPREMISE_RISK: none or possible  (possible if it asserts 'the only/first/sole/no other X' that could have near-misses or be false)\nDRAFT_CONFIDENCE: high or low  (your confidence in the best answer from knowledge alone)\nBe concrete and terse."
        SYSTEM_BASE = "You are a careful research analyst answering a factual question. Tools: search_web(query) for web search, fetch_page(url) for full pages AND structured JSON APIs, and compute(code) for exact arithmetic. Every tool result is numbered like [7]. A strict judge FACT-CHECKS EVERY FIGURE against your cited sources and gives NO credit to any claim without a [n] citation.\n\nHOW TO RESEARCH: decompose into each sub-fact / condition / hop and VERIFY each with a tool result before asserting it -- never guess dates, counts, rankings, or names from memory.\n- SEARCH with search_web: for a targeted figure use exact names+years; for a HARD/OBSCURE fact fire SEVERAL search_web queries in the SAME turn from different angles (exact phrase, entity+metric+year, and a 'site:<official-domain>' query) -- they run in parallel, so a multi-angle sweep costs one turn. If a fact is missing, REFORMULATE and search again; never guess a load-bearing fact while budget/time remain.\n- STRUCTURED SOURCES: for exact structured facts, fetch a primary/official page or JSON API directly (e.g. Wikipedia REST 'https://en.wikipedia.org/api/rest_v1/page/summary/<Title>' or the action API '/w/api.php?action=query&format=json&prop=extracts&explaintext=1&titles=<Title>').\n- MULTI-HOP: resolve chained questions hop by hop -- find and CITE the bridge entity before the next hop.\n- YEAR PRECISION: use the exact year in queries; confirm every figure is for that year.\n- SOURCE AUTHORITY: prefer official/primary and major-reference sources over aggregators/quiz-sites/forums.\n- METRIC/GROWTH: for a %-change or growth rate, retrieve the OFFICIAL growth-rate series (not derived from two levels); use compute on cited figures.\n- NAMED SOURCE: if the question names a source (Forbes, Box Office Mojo, IMDb, UN, World Bank, a Wikipedia list...), take the deciding figures from THAT source and cite it.\n- Confirm an answer-deciding number/date/count from a SECOND authoritative source. Use compute for ALL arithmetic.\n\nHOW TO ANSWER (once every sub-fact is verified):\n- Line 1 = 'FINAL ANSWER: <the fully-resolved answer>'. Give exact values with units, verbatim (population 8,631,393, not 'about 9 million'). NEVER open with a remark about evidence quality.\n- Then a SHORT 'Proof:' -- one tight cited line per load-bearing fact, a [n] after EVERY claim (names, numbers, dates, the verdict). A claim with no bracket earns ZERO credit; never cite a source that does not support it.\n- ONLY the text from 'FINAL ANSWER:' onward is delivered to the judge, so it must stand alone as clean prose -- do not paste working notes/tables, tool-call syntax, or a draft heading.\n- VERIFY BEFORE COMMITTING: re-read the criteria and your own cited proof; make line 1 name EXACTLY what the proof supports; confirm no claim contradicts its own cited source.\n- If the premise is genuinely false on clear evidence, say so on line 1 with the correct fact. NEVER refuse or say evidence is missing -- commit the best-supported answer the evidence allows.\n\nDo not call a tool and write the final answer in the same turn."
        _LEAN_DIRECTIVE = '\n\nDIRECT QUESTION: this has a single, well-defined best answer. Answer it directly and precisely from verified sources. Do NOT enumerate a candidate pool, do NOT volunteer speculative near-misses or alternative interpretations, and do NOT hedge -- give the single best-supported answer with 1-3 short cited proof lines.'
        _PREMISE_NOTE = "\nThe question asserts a uniqueness/superlative ('the only/first/sole'). Give the well-known correct answer and verify it; declare the premise false ONLY on clear, direct contrary evidence -- do not hedge with weak or speculative near-misses."
        _DISCRETE_CITE_NOTE = '\n\nDISCRETE CITATION: attach a SEPARATE [n] to EACH decisive value (each year, figure, candidate) -- never one citation covering several distinct values; the grader validates each figure against its own cited source.'
        _JUDGE_CONTRACT = "\n\nSCORING (a pairwise judge fact-checks EVERY figure against your cited source): a CITED claim beats a correct but UNCITED one -- even true facts asserted from memory LOSE, so bind every figure/name/date to a [n] whose source actually states it. Reproduce numbers VERBATIM (58.58% is not 58.6%; keep exact notation and units). Bind each claim to the EXACT actor, target, date and instrument the evidence supports -- never carry a value across entities or years. If a premise is false, say so AND give the corrected fact (saying only 'the premise is false' scores as an empty answer). A committed, cited partial answer beats any refusal."
        _HARD_ADDENDUM = "\n\nMULTI-CONSTRAINT / SET / COMPARISON question -- completeness and rigor decide the score:\n- You MAY reason through a per-candidate x per-constraint verification TABLE as scratch, then deliver only the clean 'FINAL ANSWER:' section (rewrite the proof as prose, not the raw table).\n- PROOF OF COMPLETENESS: enumerate the full CANDIDATE POOL, apply EACH constraint with a citation, give one cited line per QUALIFYING item and one per key EXCLUDED near-miss with the exact criterion it fails.\n- CROSS-SOURCE RECONCILIATION: when sources disagree on a figure/date, prefer the primary/most-recent source, state the adopted value with its citation, and note the conflict briefly.\n- RANKING/SUPERLATIVE: look up the deciding value for EVERY candidate before naming a winner.\n- Aim to DOMINATE a strong reference answer: at least as correct, MORE complete, and better cited."

        def _force_commit_nudge(remaining):
            return f"About {int(remaining)}s left -- STOP searching now. Using ONLY the tool results already gathered above, write your best final answer now ('FINAL ANSWER:' line first, exact cited values, a [n] after every claim). A partial, committed, fully-cited answer scores far better than refusing."

        def _commit_directive():
            return "-- FORCED COMMIT -- Your previous reply was not a usable committed answer. Using ONLY the evidence above, WRITE YOUR SINGLE BEST GROUNDED ANSWER now as plain prose: a 'FINAL ANSWER:' line resolving every condition, then cited justification with a [n] after every claim. Never say 'cannot answer'. No draft heading, no tool-call syntax, no raw table."
        _SYNTH_DIRECTIVE = "Using ONLY the numbered evidence gathered above, write the COMPLETE FINAL ANSWER now, independently: a 'FINAL ANSWER:' line resolving every condition, then a short 'Proof:' with a [n] after every claim. Clean prose."
        _INSUFFICIENT = 'Based on the evidence gathered, the best-supported answer is stated above.'
        _BRACKET_RE = re.compile('\\[([0-9][0-9,\\s-]*)\\]')
        _MARKUP_MARKERS = ('<tool_call', '<arg_key', '<arg_value', '<|tool', '</tool', '<function')
        _ABSTAIN_MARKERS = ('cannot answer', 'could not answer', 'cannot be determined', "can't be determined", 'insufficient evidence', 'insufficient information', 'evidence is missing', 'no results found', 'not enough information', 'unable to determine', 'unable to find', 'could not find', "couldn't find", "i don't have enough", 'cannot confirm', 'unable to answer', 'not able to determine', 'i was unable', 'could not complete', 'within the time budget', 'within budget', 'ran out of time', 'none of the')
        _DRAFT_LEAD_RE = re.compile("^\\s*(?:#{1,6}\\s*|\\*{1,3}\\s*|_{1,3}\\s*)*(?:draft|research\\s+briefing|working\\s+notes|scratch(?:pad)?|now i (?:have|need)|let me (?:compile|now|finalize|verify)|based on my (?:research|analysis)|i (?:now )?have all|i'?ve (?:now )?(?:got|gathered)|perfect[!.,]|okay,? (?:now|let))\\b[\\s:*#_>-]*", re.I)
        _FINAL_MARK_RE = re.compile('(?:#{1,6}\\s*|\\*{1,3}\\s*)*final\\s+answer\\s*[:\\-—]', re.I)
        _FINAL_ANY_RE = re.compile('(?:#{1,6}\\s*|\\*{1,3}\\s*)*final\\s+answer\\s*[:\\-—]', re.I)

        def _strip_draft(text):
            if not text:
                return text
            t = text.strip()
            if _DRAFT_LEAD_RE.match(t):
                marks = list(_FINAL_MARK_RE.finditer(t))
                if marks:
                    return t[marks[-1].start():].strip()
                return _DRAFT_LEAD_RE.sub('', t, count=1).strip()
            return t

        def _final_section(text):
            if not text:
                return text
            ms = list(_FINAL_ANY_RE.finditer(text))
            if not ms:
                return text
            sec = text[ms[-1].start():].strip().lstrip('#* \t').strip()
            if len(sec) < 60:
                return text
            return sec
        _INTENT_NARRATION_RE = re.compile("^\\s*(?:#{1,6}\\s*|\\*+\\s*)*(?:i(?:'|’)?ll|i will|i(?:'|’)?m going to|i am going to|i need to|i(?:'|’)?d|i can|i should|i must|let me|let(?:'|’)?s|first,?\\s+i|next,?\\s+i|now i(?:'|’)?ll|to answer this,?\\s+i)\\s+(?:now\\s+|then\\s+|go\\s+ahead\\s+and\\s+|start\\s+by\\s+|first\\s+)?(?:fetch|search|look|check|gather|retrieve|find|get|pull|query|verify|confirm|compute|calculate|start|begin|use|call|browse|read|open|access|examine|investigate|determine|cross-?reference)\\b", re.I)

        def _invalid_final(text):
            t = (text or '').strip()
            if len(t) < 40:
                return True
            if any((m in text for m in _MARKUP_MARKERS)):
                return True
            if _DRAFT_LEAD_RE.match(t) or _INTENT_NARRATION_RE.match(t):
                return True
            lead = t[:90].lower()
            if any((a in lead for a in _ABSTAIN_MARKERS)):
                return True
            if _FINAL_MARK_RE.match(t) and re.search('\\[\\d', t):
                return False
            return any((a in t[:400].lower() for a in _ABSTAIN_MARKERS))

        class _Index:

            def __init__(self):
                self._by_n = {}
                self._next = 1

            def record(self, receipt_id, results, *, width, start=0, source='search'):
                nums = []
                for r in results or ():
                    rid = getattr(r, 'result_id', None)
                    if not rid:
                        continue
                    n = self._next
                    self._next += 1
                    self._by_n[n] = (receipt_id, rid, start, width, getattr(r, 'note', '') or '', source)
                    nums.append(n)
                return nums

            def get(self, n):
                return self._by_n.get(n)

            def top(self):
                return self._next - 1

            def all_notes(self):
                return '\n'.join((v[4] for v in self._by_n.values()))

            def floor_refs(self, n_floor):
                items = sorted(self._by_n.items(), key=lambda kv: (kv[1][5] != 'fetch', kv[0]))
                out = []
                for _n, meta in items:
                    receipt_id, rid = (meta[0], meta[1])
                    if receipt_id and rid:
                        out.append(CitationRef(receipt_id=receipt_id, result_id=rid))
                    if len(out) >= n_floor:
                        break
                return out

        def _cite_numbers(fragment, top):
            out = []
            for part in fragment.split(','):
                t = part.strip()
                m = re.fullmatch('(\\d{1,4})\\s*-\\s*(\\d{1,4})', t)
                if m and int(m.group(1)) <= int(m.group(2)):
                    out.extend((i for i in range(int(m.group(1)), int(m.group(2)) + 1) if 1 <= i <= top))
                elif t.isdigit() and 1 <= int(t) <= top:
                    out.append(int(t))
            return out
        _SLICE_BOILER_RE = re.compile('cookie|subscribe now|newsletter|advertisement|sign in\\b|accept cookies', re.I)

        def _slice_quality(text):
            if not text:
                return 0.0
            q = 1.0
            pipes = text.count('|') * 100.0 / len(text)
            if pipes > 6:
                q *= 0.3
            elif pipes > 3:
                q *= 0.6
            letters = sum((1 for c in text if c.isalpha()))
            if letters * 1.0 / len(text) < 0.45:
                q *= 0.45
            if _SLICE_BOILER_RE.search(text[:400]):
                q *= 0.6
            return q

        def _best_slice(note, start, width):
            note_len = len(note)
            if note_len <= width:
                return (0, note_len)
            a_s = max(0, min(start, note_len - 1))
            a_e = min(a_s + width, note_len)
            aq = _slice_quality(note[a_s:a_e])
            if a_s == 0 or aq >= 0.6:
                return (a_s, a_e)
            hq = _slice_quality(note[:width])
            if hq > aq:
                return (0, width)
            return (a_s, a_e)

        def _citations_from_text(text, index):
            seen, ordered = (set(), [])
            for m in _BRACKET_RE.finditer(text):
                for n in _cite_numbers(m.group(1), index.top()):
                    if n not in seen:
                        seen.add(n)
                        ordered.append(n)
            refs, total = ([], 0)
            for n in ordered:
                if len(refs) >= MAX_CITATIONS:
                    break
                meta = index.get(n)
                if not meta:
                    continue
                receipt_id, result_id, start, width, note, _source = meta
                note_len = len(note)
                if note_len <= 0:
                    continue
                s, e = _best_slice(note, start, width)
                if e <= s:
                    continue
                if total + (e - s) > CITATION_CHAR_BUDGET:
                    continue
                total += e - s
                refs.append(CitationRef(receipt_id=receipt_id, result_id=result_id, slices=[CitationSlice(start=s, end=e)]))
            return refs

        def _citations_with_floor(text, index):
            refs = _citations_from_text(_normalize_brackets(text), index)
            if refs:
                return refs
            return index.floor_refs(CITE_FLOOR_N)
        _FULLWIDTH_TABLE = str.maketrans({'０': '0', '１': '1', '２': '2', '３': '3', '４': '4', '５': '5', '６': '6', '７': '7', '８': '8', '９': '9', '［': '[', '］': ']', '【': '[', '】': ']', '〔': '[', '〕': ']', '（': '(', '）': ')', '，': ','})

        def _normalize_brackets(text):
            return text.translate(_FULLWIDTH_TABLE) if text else text

        def _bind_citations(text, index):
            text = _normalize_brackets(text or '')
            order, seen = ([], set())
            for m in _BRACKET_RE.finditer(text):
                for n in _cite_numbers(m.group(1), index.top()):
                    if n not in seen and index.get(n):
                        seen.add(n)
                        order.append(n)
            refs, mapping, total = ([], {}, 0)
            for n in order:
                if len(refs) >= MAX_CITATIONS:
                    break
                meta = index.get(n)
                if not meta:
                    continue
                receipt_id, result_id, start, width, note, _source = meta
                if len(note) <= 0:
                    continue
                s, e = _best_slice(note, start, width)
                if e <= s or total + (e - s) > CITATION_CHAR_BUDGET:
                    continue
                total += e - s
                mapping[n] = len(refs) + 1
                refs.append(CitationRef(receipt_id=receipt_id, result_id=result_id, slices=[CitationSlice(start=s, end=e)]))
            if not refs:
                return (text, index.floor_refs(CITE_FLOOR_N))

            def _repl(m):
                mapped = []
                for n in _cite_numbers(m.group(1), index.top()):
                    if n in mapping and str(mapping[n]) not in mapped:
                        mapped.append(str(mapping[n]))
                return '[' + ', '.join(mapped) + ']' if mapped else ''
            return (_BRACKET_RE.sub(_repl, text), refs)

        async def _do_search(query_text, index):
            res = None
            for provider in (SEARCH_PROVIDER, SEARCH_FALLBACK_PROVIDER):
                try:
                    candidate = await search_web(query_text, provider=provider, timeout=SEARCH_TIMEOUT_SECONDS)
                except Exception:
                    continue
                if candidate is not None and getattr(candidate, 'results', None):
                    _spend_note(candidate)
                    res = candidate
                    break
            if res is None:
                return f'# search_web({query_text!r}) ERROR: no results from any provider'
            nums = index.record(res.receipt_id, res.results, width=SEARCH_EXCERPT_CHARS, source='search')
            lines = [f'# search_web({query_text!r}) -> {len(res.results)} results']
            for n, r in zip(nums, res.results):
                lines.append(f"[{n}] {getattr(r, 'title', '') or ''}\n  url: {getattr(r, 'url', '')}\n  excerpt: {(getattr(r, 'note', '') or '')[:SEARCH_EXCERPT_CHARS]}")
            return '\n'.join(lines)

        def _seed_queries(q):
            ql = (q or '').strip()
            seeds = [ql[:200]]
            if _is_set_question(q) or _needs_superlative_proof(q) or _is_comparison(q):
                subj = re.sub('^\\s*(which|what|who|name|list|how many|of the|among|identify|find)\\b[\\s,]*', '', ql, flags=re.I)
                subj = re.split('\\b(that|which|who|whose|with|where|when|are|were|is|was|had|have|has|satisfy|satisfies|meet|meets|between|from|according|in the|during|before|after)\\b', subj, 1, flags=re.I)[0].strip(' ,.')
                if len(subj) >= 4:
                    seeds.append('list of ' + subj[:80])
            out = []
            for s in seeds:
                s = s.strip()
                if s and s not in out:
                    out.append(s)
            return out[:2]

        async def _preseed(q, index, deadline):
            if deadline - perf_counter() < PRESEED_MIN_REMAINING or _spend_left() < MIN_DRAFT_USD:
                return ('', 0)
            qs = _seed_queries(q)
            if not qs:
                return ('', 0)
            outs = await asyncio.gather(*[_do_search(s, index) for s in qs], return_exceptions=True)
            blocks = [o for o in outs if isinstance(o, str) and 'ERROR' not in o[:40]]
            if not blocks:
                return ('', 0)
            return ('PRESEED EVIDENCE (already numbered -- cite these [n]; verify and extend with tools as needed. For a set/ranking question, treat any list/roster below as the candidate POOL and check every member):\n' + '\n'.join(blocks), len(qs))
        _FETCH_STOP = {'the', 'and', 'for', 'with', 'that', 'which', 'what', 'who', 'from', 'according', 'between', 'their', 'were', 'was', 'this', 'than', 'into', 'over', 'under', 'when', 'where', 'list', 'name', 'many', 'have', 'has'}

        def _window_start(body, question, width):
            if len(body) <= width:
                return 0
            terms = [w for w in re.findall('[A-Za-z0-9]{4,}', question or '') if w.lower() not in _FETCH_STOP]
            low = body.lower()
            for t in terms[:14]:
                i = low.find(t.lower())
                if i != -1:
                    return max(0, i - width // 4)
            return 0

        async def _do_fetch(url, index, question=''):
            res = None
            for provider in (SEARCH_PROVIDER, SEARCH_FALLBACK_PROVIDER):
                for _ in range(FETCH_RETRIES):
                    try:
                        candidate = await fetch_page(url, provider=provider, timeout=FETCH_TIMEOUT_SECONDS)
                    except Exception:
                        candidate = None
                    if candidate is not None and getattr(candidate, 'results', None):
                        _spend_note(candidate)
                        res = candidate
                        break
                if res is not None:
                    break
            if res is None or not getattr(res, 'results', None):
                return f'# fetch_page({url!r}) -> no content'
            full = getattr(res.results[0], 'note', '') or ''
            width = FETCH_EXTRACT_CHARS if _EXTRACT_MODE['on'] else FETCH_EXCERPT_CHARS
            start = _window_start(full, question, width)
            body = full[start:start + width]
            nums = index.record(res.receipt_id, res.results, width=len(body), start=start, source='fetch')
            return f'# fetch_page({url!r}) -> [{nums[0]}] {len(body)} chars\n{body}'

        def _do_compute(code):
            try:
                return f'# compute -> result = {safe_exec(code, {})!r}'
            except Exception as exc:
                return f'# compute ERROR: {exc}'

        async def _turn(messages, *, deadline, tools, force_text):
            for _ in range(LLM_TURN_RETRIES):
                timeout = min(LLM_TURN_TIMEOUT_SECONDS, deadline - perf_counter())
                if timeout <= 0:
                    return None
                try:
                    r = await llm_chat(provider=LLM_PROVIDER, model=MODEL, messages=messages, tools=tools, tool_choice='auto' if tools else None, temperature=TEMPERATURE, thinking=_THINK_OFF, timeout=timeout)
                except Exception:
                    continue
                _spend_note(r)
                return r
            return None

        async def _briefing(question, deadline):
            timeout = min(BRIEFING_TIMEOUT_SECONDS, deadline - perf_counter())
            if timeout <= 8:
                return ''
            try:
                r = await llm_chat(provider=LLM_PROVIDER, model=MODEL, messages=[{'role': 'system', 'content': BRIEFING_PROMPT}, {'role': 'user', 'content': question}], temperature=TEMPERATURE, thinking=_THINK_OFF, timeout=timeout)
            except Exception:
                return ''
            if r:
                _spend_note(r)
            return (r.response.raw_text or '').strip() if r else ''
        _CLASSIFIER_PROMPT = "Classify a research question's difficulty for a web-research agent. Reply with EXACTLY one word: hard or easy.\nhard = needs multiple candidates/sources, enumeration, numeric computation, multi-hop chaining, comparison/ranking, an authoritative table, or an obscure/uncertain fact.\neasy = a single well-known fact with one clear, direct answer.\nWhen in doubt, answer hard. One word only."

        async def _quick_classify(q, deadline):
            timeout = min(CLASSIFIER_TIMEOUT_SECONDS, deadline - perf_counter())
            if timeout <= 5 or _spend_left() < MIN_DRAFT_USD:
                return None
            try:
                r = await llm_chat(provider=LLM_PROVIDER, model=CLASSIFIER_MODEL, messages=[{'role': 'system', 'content': _CLASSIFIER_PROMPT}, {'role': 'user', 'content': q}], temperature=0.0, thinking=_think_for(CLASSIFIER_MODEL), timeout=timeout)
            except Exception:
                return None
            if r:
                _spend_note(r)
            t = ((r.response.raw_text if r else '') or '').strip().lower()
            if 'hard' in t:
                return True
            if 'easy' in t:
                return False
            return None

        async def _commit_llm(messages, deadline, directive):
            msgs = messages + [{'role': 'system', 'content': directive}]
            for model in (MODEL, COMMIT_FALLBACK_MODEL):
                timeout = min(FINAL_COMMIT_TIMEOUT_SECONDS, deadline - perf_counter())
                if timeout <= 6:
                    break
                try:
                    r = await llm_chat(provider=LLM_PROVIDER, model=model, messages=msgs, tools=None, temperature=TEMPERATURE, thinking=_think_for(model), timeout=timeout)
                except Exception:
                    continue
                if r:
                    _spend_note(r)
                t = _strip_draft((r.response.raw_text or '').strip()) if r else ''
                if t and (not _invalid_final(t)):
                    return t
            return ''

        async def _forced_final(messages, deadline):
            return await _commit_llm(messages, deadline, _commit_directive())

        # Spend-corridor hull ridge seal for this module outline.


        async def _synth_pass(messages, deadline, temperature):
            timeout = min(FINAL_COMMIT_TIMEOUT_SECONDS, deadline - perf_counter())
            if timeout <= 8:
                return ''
            msgs = messages + [{'role': 'system', 'content': _SYNTH_DIRECTIVE}]
            try:
                r = await llm_chat(provider=LLM_PROVIDER, model=MODEL, messages=msgs, tools=None, temperature=temperature, thinking=_THINK_OFF, timeout=timeout)
            except Exception:
                return ''
            if r:
                _spend_note(r)
            return _strip_draft((r.response.raw_text or '').strip()) if r else ''

        def _answer_key(text):
            disp = _final_section(text or '')
            m = _FINAL_ANY_RE.search(disp)
            line = disp[m.end():] if m else disp
            line = line.split('\n', 1)[0]
            line = re.split('\\bproof\\b|\\bbecause\\b|\\bsince\\b', line, maxsplit=1, flags=re.I)[0]
            line = _BRACKET_RE.sub('', line)
            line = re.sub('[^a-z0-9, ]', ' ', line.lower())
            toks = sorted((t for t in line.split() if len(t) > 2))
            return ' '.join(toks)[:400]

        def _select_best(cands, is_set):
            valid = [c for c in cands if c and (not _invalid_final(c))]
            if not valid:
                return ''
            if len(valid) == 1:
                return valid[0]

            def ncit(c):
                return len({n for m in _BRACKET_RE.finditer(c) for n in _cite_numbers(m.group(1), 9999)})
            if is_set:
                return max(valid, key=lambda c: (ncit(c), len(_final_section(c))))
            from collections import Counter
            keys = [_answer_key(c) for c in valid]
            counts = Counter((k for k in keys if k))
            if counts:
                top_key, top_n = counts.most_common(1)[0]
                if top_n >= 2:
                    agree = [c for c, k in zip(valid, keys) if k == top_key]
                    return max(agree, key=ncit)
            return max(valid, key=ncit)
        _CITE_DIRECTIVE = 'CITATION GAP: your answer is under-sourced and earns NO credit for uncited claims. Using ONLY the numbered evidence above, RESTATE the complete FINAL ANSWER with a [n] citation immediately after EVERY factual claim. Keep the same answer and format; just add the citations. Clean prose.'

        async def _cite_recommit(messages, prior, deadline):
            timeout = min(FINAL_COMMIT_TIMEOUT_SECONDS, deadline - perf_counter())
            if timeout <= 8:
                return ''
            msgs = messages + [{'role': 'assistant', 'content': prior[:1500]}, {'role': 'system', 'content': _CITE_DIRECTIVE}]
            for model in (MODEL, COMMIT_FALLBACK_MODEL):
                timeout = min(FINAL_COMMIT_TIMEOUT_SECONDS, deadline - perf_counter())
                if timeout <= 8:
                    break
                try:
                    r = await llm_chat(provider=LLM_PROVIDER, model=model, messages=msgs, tools=None, temperature=TEMPERATURE, thinking=_think_for(model), timeout=timeout)
                except Exception:
                    continue
                if r:
                    _spend_note(r)
                t = _strip_draft((r.response.raw_text or '').strip()) if r else ''
                if t:
                    return t
            return ''

        async def _audit_and_patch(question, answer, messages, deadline):
            timeout = min(AUDIT_TIMEOUT_SECONDS, deadline - perf_counter())
            if timeout <= 8:
                return ''
            audit_user = f'Audit this answer against the question. Report ONLY genuine, fixable problems as a JSON object with keys: "uncited_claims", "contradictions" (a claim conflicting with its OWN cited source), "wrong_source" (an aggregator used where the question named a specific primary source), "missing_elements" (a question part or a qualifying set member not addressed). Empty lists when fine. No other text.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:9000]}'
            try:
                r = await llm_chat(provider=LLM_PROVIDER, model=AUDIT_MODEL, messages=[{'role': 'system', 'content': 'You are a strict answer auditor. Output JSON only.'}, {'role': 'user', 'content': audit_user}], temperature=0.0, thinking=_THINK_LOW, timeout=timeout)
            except Exception:
                return ''
            if r:
                _spend_note(r)
            raw = (r.response.raw_text or '').strip() if r else ''
            try:
                raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw, flags=re.I | re.M).strip()
                report = json.loads(raw[raw.find('{'):raw.rfind('}') + 1])
            except Exception:
                return ''
            issues = []
            for k in ('uncited_claims', 'contradictions', 'wrong_source', 'missing_elements'):
                v = report.get(k) if isinstance(report, dict) else None
                if isinstance(v, list):
                    issues.extend((str(x) for x in v if str(x).strip()))
            if not issues or deadline - perf_counter() < 35:
                return ''
            patch = 'AUDIT found fixable gaps in your final answer:\n- ' + '\n- '.join(issues[:6]) + '\nRewrite the COMPLETE FINAL ANSWER fixing ONLY these, keeping everything already correct (do NOT drop a correct qualifying item). Put a [n] after every claim, obey the output format. Clean prose, no table.'
            return await _commit_llm(messages + [{'role': 'assistant', 'content': answer[:1500]}], deadline, patch)
        GAP_RESEARCH_TURNS = 3
        GAP_RESEARCH_MIN_REMAINING = 80.0

        async def _audit_gaps(question, answer, deadline):
            timeout = min(AUDIT_TIMEOUT_SECONDS, deadline - perf_counter())
            if timeout <= 8:
                return []
            audit_user = f'Audit this answer for DECISIVE gaps that a fact-checking judge would penalize. Report ONLY genuine, fixable gaps as JSON with keys: "missing_members" (a qualifying set/roster member OR question part not addressed), "uncited_decisive_values" (a per-item deciding value -- a year/figure/count -- asserted WITHOUT a [n] to a real source), "wrong_source" (an aggregator used where a specific authority was named). Each entry = a SHORT search-ready phrase naming exactly what to look up. Empty lists if fine. JSON only.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:9000]}'
            try:
                r = await llm_chat(provider=LLM_PROVIDER, model=AUDIT_MODEL, messages=[{'role': 'system', 'content': 'You are a strict answer auditor. Output JSON only.'}, {'role': 'user', 'content': audit_user}], temperature=0.0, thinking=_THINK_LOW, timeout=timeout)
            except Exception:
                return []
            if r:
                _spend_note(r)
            raw = (r.response.raw_text or '').strip() if r else ''
            try:
                raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw, flags=re.I | re.M).strip()
                rep = json.loads(raw[raw.find('{'):raw.rfind('}') + 1])
            except Exception:
                return []
            gaps = []
            for k in ('missing_members', 'uncited_decisive_values', 'wrong_source'):
                v = rep.get(k) if isinstance(rep, dict) else None
                if isinstance(v, list):
                    gaps.extend((str(x) for x in v if str(x).strip()))
            return gaps[:6]

        async def _gap_research_patch(q, final, messages, index, deadline, is_set):
            if not final or _invalid_final(final) or deadline - perf_counter() < GAP_RESEARCH_MIN_REMAINING or (_spend_left() < MIN_AUDIT_USD):
                return final
            gaps = await _audit_gaps(q, final, deadline)
            if not gaps:
                return final
            nudge = 'AUDIT found DECISIVE gaps that will LOSE points -- fetch and CITE each before finalizing:\n- ' + '\n- '.join(gaps) + '\nUse search_web + fetch_page to get the AUTHORITATIVE source for EACH, then commit the COMPLETE FINAL ANSWER with a [n] after every decisive value (every qualifying member AND every ruled-out near-miss with its cited failing value). Do NOT drop anything already correct.'
            gmsgs = messages + [{'role': 'assistant', 'content': final[:1500]}, {'role': 'system', 'content': nudge}]
            used = 0
            for _ in range(GAP_RESEARCH_TURNS):
                remaining = deadline - perf_counter()
                if remaining < 45 or _spend_left() < MIN_AUDIT_USD:
                    break
                force_text = used >= GAP_RESEARCH_TURNS - 1 or remaining < 60
                result = await _turn(gmsgs, deadline=deadline, tools=None if force_text else TOOLS_ALL, force_text=force_text)
                if result is None:
                    break
                msg = result.response.choices[0].message
                calls = msg.tool_calls or ()
                if calls:
                    gmsgs.append({'role': 'assistant', 'content': result.response.raw_text or '', 'tool_calls': [{'id': c.id, 'type': c.type, 'name': c.name, 'arguments': c.arguments} for c in calls]})
                    outs = await asyncio.gather(*[_run_tool(c, index, q) for c in calls], return_exceptions=True)
                    for c, tr in zip(calls, outs):
                        gmsgs.append({'role': 'tool', 'tool_call_id': c.id, 'content': tr if isinstance(tr, str) else f'# {c.name} ERROR: {tr}'})
                    used += 1
                    continue
                cand = _strip_draft(_content_to_text(msg, result.response.raw_text or '').strip())
                if cand and (not _invalid_final(cand)):
                    return _select_best([final, cand], is_set) if is_set else cand
                break
            fixed = await _commit_llm(gmsgs, deadline, 'Now commit the COMPLETE FINAL ANSWER from ALL evidence above; a [n] after every decisive value; do not drop a correct item.')
            if fixed and (not _invalid_final(fixed)):
                return _select_best([final, fixed], is_set) if is_set else fixed
            return final
        _CONCISE_DIRECTIVE = "Your previous answer ran long and was CUT OFF. Rewrite it NOW as a COMPLETE, CONCISE answer: a 'FINAL ANSWER:' line, then AT MOST 4-5 short cited lines, a [n] after every claim. Under 170 words, and make sure it ENDS. No tool-call syntax, no draft heading, no table."

        def _looks_truncated(text):
            t = (text or '').rstrip()
            if len(t) < 350:
                return False
            return t[-1].isalnum() or t[-1] in ',;:-—'

        async def _concise_recommit(messages, prior, deadline):
            timeout = min(FINAL_COMMIT_TIMEOUT_SECONDS, deadline - perf_counter())
            if timeout <= 6:
                return ''
            msgs = messages + [{'role': 'assistant', 'content': prior[:1200]}, {'role': 'system', 'content': _CONCISE_DIRECTIVE}]
            try:
                r = await llm_chat(provider=LLM_PROVIDER, model=MODEL, messages=msgs, tools=None, temperature=TEMPERATURE, thinking=_THINK_OFF, timeout=timeout)
            except Exception:
                return ''
            if r:
                _spend_note(r)
            return _strip_draft((r.response.raw_text or '').strip()) if r else ''
        _SET_DIRECTIVE = "\nSET/ENUMERATE QUESTION -- it asks for the COMPLETE set; completeness decides the score. Get the POOL from an authoritative LIST/roster/table FIRST (search 'list of <the pool>'), not member-by-member. Then deliver FOUR parts:\n(1) LIST -- name every qualifying item.\n(2) SCOPE & BASIS -- restate how any relative/fuzzy criterion became an exact checkable boundary (e.g. 'within 2 years of 1946' = 1944-1948).\n(3) INCLUSION PROOF -- ONE line per listed item with a [n] showing it meets EVERY criterion.\n(4) COMPLETENESS & EXCLUSIONS -- name key near-miss candidates excluded and the exact criterion each fails, cited.\nKeep an uncertain member IN rather than drop it. An answer showing only part (1) scores WORSE than all four."
        _SUPERLATIVE_RULE = '\nSUPERLATIVE/RANKING QUESTION -- do NOT name the winner from memory. Build the full candidate table: look up the DECIDING value for EVERY plausible candidate with a [n], THEN name the extreme. Never decide a superlative on a rounded figure (get the exact value). Cite the deciding value for the winner AND the closest runner-up.'
        _EST_STOP = frozenset({'west', 'east', 'best', 'test', 'rest', 'guest', 'forest', 'honest', 'request', 'interest', 'protest', 'invest', 'harvest', 'modest', 'nearest', 'earnest', 'suggest', 'contest', 'conquest', 'midwest', 'northwest', 'southwest', 'everest', 'budapest', 'bucharest'})
        _NUMERIC_DIRECTIVE = '\nNUMERIC/COMPUTE QUESTION -- retrieve each raw figure from a cited source, then use the compute tool for EVERY calculation. Never do mental math; state the computed result and cite the inputs.'
        _MULTIHOP_DIRECTIVE = '\nMULTI-HOP QUESTION -- resolve hop by hop: find and CITE the bridge entity first, then search using ITS exact name for the next hop. Verify each hop before the next.'
        _SET_Q_RE = re.compile('\\b(list all|name all|name every|how many|which .{0,45}?\\b(satisfy|satisfies|meet|meets|have|has|are|were|match|matches|qualify|qualifies|contain|contains|rank|include)|all (of )?the .{0,45}?\\b(that|which|who|with)|every .{0,35}?\\b(that|which|with)|each of (the )?)\\b', re.I)
        _NUMERIC_Q_RE = re.compile('\\b(how many|how much|what percentage|percent|average|mean|median|the sum|total number|difference between|ratio|growth rate|per capita|how far|how old|how long|how tall|times (as|more|larger|bigger|greater))\\b', re.I)
        _MULTIHOP_Q_RE = re.compile('\\bthe\\s+\\w+\\s+of\\s+the\\s+\\w+\\s+(that|who|which|whose)\\b|\\bwho\\s+(directed|wrote|founded|created|composed|played|married)\\b.{0,60}\\b(that|who|which|whose)\\b', re.I)
        _COMPARISON_RE = re.compile('\\b(compare|comparison|versus|vs\\.?|difference between|which (?:one )?(?:is|has|was|had) (?:the )?(?:more|less|higher|lower|greater|bigger|smaller|older|younger|longer|shorter|larger|closest|nearest))\\b', re.I)
        _SUPERLATIVE_ONLY_RE = re.compile('\\b(the only|the first|the sole|the single|the last|no other|the unique)\\b', re.I)
        _HEDGE_RE = re.compile("\\b(however|although|it is unclear|it'?s unclear|ambiguous|arguably|it depends|more than one|multiple (?:answers|candidates|possibilities)|also (?:uses|qualifies|applies|counts|meets))\\b", re.I)

        def _is_set_question(q):
            return bool(_SET_Q_RE.search(q or ''))

        def _is_numeric_question(q):
            return bool(_NUMERIC_Q_RE.search(q or ''))

        def _is_multihop_question(q):
            return bool(_MULTIHOP_Q_RE.search(q or ''))

        def _is_comparison(q):
            return bool(_COMPARISON_RE.search(q or ''))

        def _has_superlative_only(q):
            return bool(_SUPERLATIVE_ONLY_RE.search(q or ''))
        _SUPERLATIVE_WORD_RE = re.compile('\\b(most|least|highest|lowest|largest|smallest|greatest|fewest|longest|shortest|oldest|newest|biggest|maximum|minimum|the top|ranked|\\d+(?:st|nd|rd|th)\\s+(?:highest|largest|most|longest|oldest)|second\\s+(?:highest|largest|most|longest|oldest))\\b', re.I)

        def _needs_superlative_proof(q):
            ql = (q or '').lower()
            if _SUPERLATIVE_WORD_RE.search(ql):
                return True
            for m in re.finditer('\\b(\\w+est)\\b', ql):
                w = m.group(1)
                if len(w) >= 5 and w not in _EST_STOP:
                    return True
            return False

        def _structural_hard(q):
            return _is_set_question(q) or _is_numeric_question(q) or _is_multihop_question(q) or _is_comparison(q) or _needs_superlative_proof(q)

        def _route_directive(q):
            d = ''
            if _is_set_question(q):
                d += _SET_DIRECTIVE
            if _is_numeric_question(q):
                d += _NUMERIC_DIRECTIVE
            if _is_multihop_question(q):
                d += _MULTIHOP_DIRECTIVE
            if _needs_superlative_proof(q):
                d += _SUPERLATIVE_RULE
            return d

        def _parse_difficulty(brief):
            if not brief:
                return {}
            up = brief.upper()
            seg = brief[up.rfind('CLASSIF'):] if 'CLASSIF' in up else brief

            def g(label, pat):
                m = re.search(label + '\\s*:?\\s*(' + pat + ')', seg, re.I)
                return m.group(1).lower() if m else None

            def gi(label):
                m = re.search(label + '\\s*:?\\s*(\\d+)', seg, re.I)
                return int(m.group(1)) if m else None
            return {'difficulty': g('DIFFICULTY', 'easy|hard'), 'answer_type': g('ANSWER_TYPE', 'single_fact|enumerate|numeric|multi_hop'), 'candidates': gi('CANDIDATES'), 'constraints': gi('CONSTRAINTS'), 'premise_risk': g('PREMISE_RISK', 'none|possible'), 'draft_confidence': g('DRAFT_CONFIDENCE', 'high|low')}

        def _briefing_hard(cls):
            if not cls:
                return None
            if cls.get('difficulty') == 'hard':
                return True
            if cls.get('answer_type') in ('enumerate', 'numeric', 'multi_hop'):
                return True
            if (cls.get('candidates') or 0) >= 2 or (cls.get('constraints') or 0) >= 2:
                return True
            if cls.get('draft_confidence') == 'low':
                return True
            if cls.get('difficulty') == 'easy':
                return False
            return None

        def classify_hard(q, cls):
            return bool(_structural_hard(q)) or _briefing_hard(cls) is True

        def _needs_escalation(text):
            disp = _final_section(text or '')
            if _HEDGE_RE.search(disp):
                return True
            if len(_BRACKET_RE.findall(disp)) == 0:
                return True
            return False
        _STRICT_FMT_RE = re.compile('output only|only (?:output|return|provide|give)|return only|exactly the text|the exact text from|comma[- ]separated|separated by commas|semicolon[- ]separated|without the (?:word|term)|omit(?:ting)? the (?:word|term)|excluding the (?:word|term)|in alphabetical order|in chronological order|alphabetical(?:ly)? order|chronological(?:ly)? order|sorted (?:by|in|alphabetically|chronologically)', re.I)

        def _has_strict_format(q):
            return bool(_STRICT_FMT_RE.search(q or ''))

        def _answer_value_text(answer):
            disp = _final_section(answer or '')
            m = _FINAL_ANY_RE.search(disp)
            line = disp[m.end():] if m else disp
            line = line.split('\n', 1)[0]
            line = re.split('\\bproof\\b|\\bbecause\\b|\\bsince\\b', line, maxsplit=1, flags=re.I)[0]
            line = _BRACKET_RE.sub('', line)
            line = re.sub('\\s{2,}', ' ', line)
            return line.strip(' \t*:#—-.,;').strip()

        def _apply_output_directives(question, text):
            out = text or ''
            for m in re.finditer('(?:without|omit(?:ting)?|excluding) the (?:word|term)\\s*["“‘\\\']?([A-Za-z][\\w\\-]*)["”’\\\']?', question or '', re.I):
                w = m.group(1)
                if len(w) >= 3:
                    out = re.sub('\\b%s\\b' % re.escape(w), '', out, flags=re.I)
            if out != (text or ''):
                out = re.sub('\\s{2,}', ' ', out)
                out = re.sub('\\s+([,.;:)])', '\\1', out).strip()
            return out.strip() or (text or '')
        _NUM_IN_TEXT_RE = re.compile('-?\\d[\\d,]*(?:\\.\\d+)?')

        def _schema_kind(schema):
            if not isinstance(schema, dict):
                return ''
            k = schema.get('type')
            if isinstance(k, list):
                k = k[0] if k else None
            if k is None:
                for key in ('anyOf', 'oneOf', 'allOf'):
                    b = schema.get(key)
                    if isinstance(b, list):
                        for sub in b:
                            got = _schema_kind(sub)
                            if got:
                                return got
                if isinstance(schema.get('properties'), dict):
                    return 'object'
                if isinstance(schema.get('enum'), list):
                    return 'string'
                return ''
            return str(k)

        def _matches_schema_shape(value, schema):
            kind = _schema_kind(schema)
            if kind == 'array':
                if not isinstance(value, list):
                    return False
            elif kind == 'object':
                if not isinstance(value, dict):
                    return False
                for req in schema.get('required') or []:
                    if req not in value:
                        return False
            elif kind == 'string':
                if not isinstance(value, str):
                    return False
            elif kind == 'integer':
                if isinstance(value, bool) or not isinstance(value, int):
                    return False
            elif kind == 'number':
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    return False
            elif kind == 'boolean':
                if not isinstance(value, bool):
                    return False
            elif kind == 'null':
                if value is not None:
                    return False
            return True

        def _coerce_to_schema(answer, schema, depth=0):
            if depth > 5 or not isinstance(schema, dict):
                return (_answer_value_text(answer) or (answer or '').strip())[:400]
            enum = schema.get('enum')
            if isinstance(enum, list) and enum:
                av = (_answer_value_text(answer) or answer or '').lower()
                for e in enum:
                    if isinstance(e, str) and e.lower() in av:
                        return e
                return enum[0]
            kind = _schema_kind(schema)
            val = _answer_value_text(answer) or (answer or '').strip()
            if kind == 'object':
                props = schema.get('properties')
                if isinstance(props, dict) and props:
                    return {name: _coerce_to_schema(answer, sub if isinstance(sub, dict) else {}, depth + 1) for name, sub in props.items()}
                return {}
            if kind == 'array':
                items = schema.get('items') if isinstance(schema.get('items'), dict) else {}
                parts = [p.strip() for p in re.split(',|;|\\band\\b', val) if p.strip()]
                if not parts:
                    parts = [val] if val else []
                ik = _schema_kind(items) if items else 'string'
                if ik in ('integer', 'number'):
                    nums = []
                    for p in parts:
                        mm = _NUM_IN_TEXT_RE.search(p)
                        if mm:
                            n = mm.group(0).replace(',', '')
                            nums.append(int(float(n)) if ik == 'integer' else float(n))
                    return nums
                if ik == 'object' and isinstance(items, dict):
                    return [_coerce_to_schema(answer, items, depth + 1)]
                return parts
            if kind == 'integer':
                mm = _NUM_IN_TEXT_RE.search(val)
                return int(float(mm.group(0).replace(',', ''))) if mm else 0
            if kind == 'number':
                mm = _NUM_IN_TEXT_RE.search(val)
                return float(mm.group(0).replace(',', '')) if mm else 0.0
            if kind == 'boolean':
                return not bool(re.search("\\b(no|not|false|none|isn'?t|aren'?t)\\b", val, re.I))
            if kind == 'null':
                return None
            return (val or (answer or '').strip())[:400]

        def _structured_directive(schema):
            return '\n\nSTRUCTURED OUTPUT REQUIRED: the deliverable is a JSON value matching this schema, so research the EXACT value for EVERY field. In your FINAL ANSWER, state each field name and its precise value (exact names / numbers / dates), each with a [n] citation. SCHEMA:\n' + json.dumps(schema)[:1500]
        _NAMED_SOURCE_RE = re.compile('\\b(?:according to|per|from|based on|using|on|by)\\b[^.?!]{0,60}?\\b(wikipedia|the wikipedia (?:table|list|page|article)|basketball[- ]?reference|box office mojo|imdb|rotten tomatoes|billboard|forbes|companiesmarketcap|statista|nasa|planetary fact sheet|world bank|united nations|\\bun\\b|census|fandom|wisdom panel|the table|the list|the fact sheet|the dataset|the chart|data\\.\\w+)\\b|\\bthe (?:wikipedia )?(?:table|list|fact sheet|dataset|chart) (?:titled|named|called|\\")|\\b(?:column|row)s?\\b.{0,40}\\b(?:table|list)\\b|https?://\\S+|\\broot url\\s*:|\\bon (?:the )?(?:website|web page|webpage|page|site) (?:at|of)\\b|\\bon the (?:official )?\\w+ (?:website|page|site)\\b', re.I)
        _AUTHORITY_RE = re.compile("\\b(?:according to|per|based on|as (?:reported|listed|shown|recorded|published|given)(?:\\s+(?:by|in|on))?|from|using|sourced from|drawn from)\\s+(?:the\\s+)?(?:[A-Z][\\w.&'’-]*(?:[- ](?:of\\s+|the\\s+)?[A-Z0-9][\\w.&'’-]*){0,6}|[A-Z]{2,6}\\b)")
        _SOURCE_TABLE_RE = re.compile("\\bTable\\s+[0-9IVXA-Z][\\w.\\-]*|\\b(?:the|its|that|this)\\s+[\\w' ]{0,45}?\\b(?:table|list|roster|dataset|data\\s?set|database|index|census|survey|review|almanac|registry|leaderboard|standings|filing|10-?[KQ]|fact\\s?sheet)\\b", re.I)

        def _authority_source(q):
            return bool(_AUTHORITY_RE.search(q or '')) or bool(_SOURCE_TABLE_RE.search(q or ''))

        def _named_source(q):
            return bool(_NAMED_SOURCE_RE.search(q or '')) or _authority_source(q)
        _EXTRACTION_DIRECTIVE = "\n\nAUTHORITATIVE-SOURCE DISCIPLINE -- this question names (or implies) a SPECIFIC authority/table/dataset the grader will FACT-CHECK your decisive figures against. A correct answer cited to the WRONG source (an aggregator, a news summary, a search snippet) scores ZERO. Steps: (1) identify the EXACT named authority (e.g. Baseball-Reference, the BLS state table, NARA, Box Office Mojo, 'Table 1.1 of ...'); (2) fetch_page that authority's OWN primary page / table / JSON API -- NOT statmuse/aggregators/news write-ups; if unsure of the URL, search the authority's name + the exact table, then fetch the primary page; (3) read the WHOLE relevant table/fact-sheet and copy every needed row/figure VERBATIM; (4) ROUNDED FIGURE = WRONG SOURCE: if a decisive number reads as rounded/approximate, you are on a summary -- keep digging for the primary table with the exact value; (5) apply each filter/condition to the EXTRACTED rows and use the compute tool for any top-N / comparison / threshold / arithmetic; (6) CITE THE DECISIVE CONDITION: attach [n] to the fetched authority for EACH candidate's deciding value -- not merely the source that lists the candidate pool. A right answer whose decisive per-candidate figure is uncited (or cited to a non-authority) gets NO credit. NEVER output raw 'search findings', a list of result titles, or a partial sentence as the answer -- only the extracted, computed result.\nEXACT FULL NAME: give the fully-qualified name -- include the standard designation/prefix (e.g. 'HMS'/'USS' for ships, 'Mount' for peaks) AND the current + any alternate/former name (e.g. 'HMS Leander', 'Allahabad (now Prayagraj)'). Copy every number/date verbatim from the source. A right entity with the wrong/short form scores 0."
        _GARBAGE_RE = re.compile('best[- ]?supported findings|from the sources retrieved|search (?:results|findings)|here are the (?:search |top )?results|results retrieved|no (?:direct )?answer found|\\|\\s*url\\s*:|\\bvia [A-Za-z.]+\\.net\\b', re.I)

        def _looks_garbage(s):
            t = (s or '').strip()
            if not t:
                return False
            if _GARBAGE_RE.search(t):
                return True
            if t.count('http') >= 3 and len(re.sub('\\S+', '', t)) < len(t) * 0.1:
                return True
            return False

        def _values_text(obj):
            out = []

            def walk(x):
                if isinstance(x, str):
                    out.append(x)
                elif isinstance(x, dict):
                    for v in x.values():
                        walk(v)
                elif isinstance(x, (list, tuple)):
                    for v in x:
                        walk(v)
            walk(obj)
            return ' '.join(out)
        _ANTI_GARBAGE_DIRECTIVE = "REJECTED: your previous answer was raw search findings / result titles / snippets, not an extracted answer -- that scores ZERO. Using the numbered evidence you already fetched, EXTRACT the specific value(s) the question asks for (exact names with full designation, exact numbers verbatim), apply the filter/ranking with the compute tool, and give ONLY the final answer with [n] citations. If you have not fetched the named source's actual page/table yet, do so now, then answer."
        _ENTITY_RE = re.compile("\\b([A-Z][A-Za-z.'&\\-]+(?:\\s+(?:of|the|and|de|von)?\\s*[A-Z][A-Za-z.'&\\-]+){0,3})\\b")
        _ENT_STOP = {'the', 'which', 'what', 'who', 'how', 'list', 'name', 'according', 'using', 'based', 'of', 'in', 'on', 'for', 'final', 'answer', 'candidate', 'pool'}

        def _enumerated_entities(q):
            ents, seen = ([], [])
            for p in re.split('[,;]| and | or ', q or ''):
                m = _ENTITY_RE.search(p.strip())
                if m:
                    e = m.group(1).strip()
                    if len(e) > 2 and e.split()[0].lower() not in _ENT_STOP and (e not in seen):
                        seen.append(e)
                        ents.append(e)
            return ents if len(ents) >= 3 else []

        def _candidates_from_brief(brief):
            if not brief:
                return []
            m = re.search('CANDIDATE POOL\\s*:?(.*?)(?:\\n\\s*[A-Z][A-Z /\\-]{4,}\\s*:|\\Z)', brief, re.S | re.I)
            if not m:
                return []
            seg = m.group(1)
            ents, seen = ([], [])
            for p in re.split('[,;\\n]|\\band\\b|\\bor\\b', seg):
                mm = _ENTITY_RE.search(p.strip())
                if mm:
                    e = mm.group(1).strip()
                    if len(e) > 2 and e.split()[0].lower() not in _ENT_STOP and (e not in seen):
                        seen.append(e)
                        ents.append(e)
            return ents[:12] if len(ents) >= 3 else []

        def _missing_entities(entities, evidence_text):
            low = (evidence_text or '').lower()
            out = []
            for e in entities:
                key = re.sub('\\s*\\(.*?\\)', '', e).strip().lower()
                if len(key) >= 3 and key not in low:
                    out.append(e)
            return out

        def _content_to_text(msg, raw):
            if raw:
                return raw
            c = getattr(msg, 'content', None)
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                out = []
                for part in c:
                    if isinstance(part, str):
                        out.append(part)
                    elif isinstance(part, dict):
                        out.append(part.get('text') or part.get('content') or '')
                    else:
                        out.append(getattr(part, 'text', '') or '')
                return ''.join(out)
            return ''

        async def _run_tool(c, index, question=''):
            try:
                args = json.loads(c.arguments or '{}')
            except json.JSONDecodeError:
                args = {}
            if c.name == 'search_web':
                return await _do_search(str(args.get('query', '')), index)
            if c.name == 'fetch_page':
                return await _do_fetch(str(args.get('url', '')), index, question)
            if c.name == 'compute':
                return _do_compute(args.get('code', ''))
            return f'# unknown tool {c.name!r}'

        async def _knowledge_answer(question, deadline):
            sys = "Answer with your single best SPECIFIC answer from knowledge. Line 1 = 'FINAL ANSWER: <answer>'. Never refuse or say 'cannot be determined'. Be concise."
            for model in (MODEL, COMMIT_FALLBACK_MODEL):
                timeout = min(FINAL_COMMIT_TIMEOUT_SECONDS, deadline - perf_counter())
                if timeout <= 5:
                    break
                try:
                    r = await llm_chat(provider=LLM_PROVIDER, model=model, messages=[{'role': 'system', 'content': sys}, {'role': 'user', 'content': question}], temperature=TEMPERATURE, thinking=_think_for(model), timeout=timeout)
                except Exception:
                    continue
                if r:
                    _spend_note(r)
                t = _strip_draft((r.response.raw_text or '').strip()) if r else ''
                if t and (not _invalid_final(t)):
                    return t
            return ''

        async def _structured_output(question, answer, schema, deadline):
            timeout = min(30.0, deadline - perf_counter())
            if timeout <= 5:
                return None
            user = 'Convert the ANSWER into JSON strictly matching this schema. Output ONLY the JSON.\nSCHEMA:\n' + json.dumps(schema)[:2200] + '\n\nANSWER:\n' + (answer or '')[:2500]
            for model in (SCHEMA_MODEL, MODEL):
                try:
                    r = await llm_chat(provider=LLM_PROVIDER, model=model, messages=[{'role': 'system', 'content': 'You output strictly valid JSON matching the given schema. JSON only.'}, {'role': 'user', 'content': user}], temperature=0.0, thinking=_think_for(model), timeout=timeout)
                    if r:
                        _spend_note(r)
                    t = (r.response.raw_text or '').strip() if r else ''
                    for op, cl in (('{', '}'), ('[', ']')):
                        i, j = (t.find(op), t.rfind(cl))
                        if i != -1 and j > i:
                            return json.loads(t[i:j + 1])
                except Exception:
                    continue
            return None

        async def _deliver_structured(q, answer, schema, refs, deadline):
            out = None
            try:
                out = await _structured_output(q, answer, schema, deadline)
            except Exception:
                out = None
            if out is None or not _matches_schema_shape(out, schema):
                out = _coerce_to_schema(answer or '', schema)
            if _looks_garbage(_values_text(out)):
                out = _coerce_to_schema(answer or '', schema)
            for cand in (out, _coerce_to_schema(answer or '', schema), _coerce_to_schema('', schema)):
                try:
                    return Response(output=cand, citations=refs or None)
                except Exception:
                    try:
                        return Response(output=cand)
                    except Exception:
                        continue
            return Response(output=(_answer_value_text(answer) or (answer or 'n/a'))[:400])

        async def _w2_baseline_query(query: Query) -> Response:
            deadline = perf_counter() + TASK_BUDGET_SECONDS
            index = _Index()
            q = query.text
            schema = getattr(query, 'output_schema', None)
            structured = schema is not None
            strict_fmt = not structured and _has_strict_format(q)
            try:
                info = await tooling_info(timeout=10.0)
                _spend_note(info)
            except Exception:
                pass
            structural = _structural_hard(q)
            brief = ''
            if structural or structured:
                hard = True
            else:
                qc = await _quick_classify(q, deadline)
                if qc is None:
                    if deadline - perf_counter() > BRIEFING_MIN_REMAINING and _spend_left() >= MIN_DRAFT_USD:
                        brief = await _briefing(q, deadline)
                    hard = classify_hard(q, _parse_difficulty(brief))
                else:
                    hard = qc
            if hard and (not brief) and (deadline - perf_counter() > BRIEFING_MIN_REMAINING) and (_spend_left() >= MIN_DRAFT_USD):
                brief = await _briefing(q, deadline)
            cls = _parse_difficulty(brief)
            extract = _named_source(q)
            _EXTRACT_MODE['on'] = extract
            is_set = _is_set_question(q) or cls.get('answer_type') == 'enumerate'
            premise_risk = _has_superlative_only(q) or cls.get('premise_risk') == 'possible'
            if hard:
                sys_content = SYSTEM_BASE + _HARD_ADDENDUM + _route_directive(q)
            else:
                sys_content = SYSTEM_BASE + _LEAN_DIRECTIVE + (_PREMISE_NOTE if premise_risk else '')
            sys_content += _DISCRETE_CITE_NOTE
            sys_content += _JUDGE_CONTRACT
            if extract:
                sys_content += _EXTRACTION_DIRECTIVE
            if structured:
                sys_content += _structured_directive(schema)
            messages = [{'role': 'system', 'content': sys_content}, {'role': 'user', 'content': q}]
            if brief:
                up = brief.upper()
                plan = brief[:up.rfind('CLASSIF')] if 'CLASSIF' in up else brief
                if plan.strip():
                    messages.append({'role': 'system', 'content': 'RESEARCH PLAN (follow it; verify every fact with tools):\n' + plan[:2400]})
            pool_entities = _enumerated_entities(q) or _candidates_from_brief(brief) if hard else []
            max_turns = MAX_TURNS if hard else EASY_MAX_TURNS
            final = None
            last_good = None
            commit_retries = 0
            nudged = False
            entity_nudged = False
            search_fetch_used = 0
            try:
                if hard or is_set or _needs_superlative_proof(q):
                    seed_block, seed_n = await _preseed(q, index, deadline)
                    if seed_block:
                        messages.append({'role': 'system', 'content': seed_block})
                        search_fetch_used += seed_n
                for turn in range(1, max_turns + 1):
                    remaining = deadline - perf_counter()
                    if remaining <= 5:
                        break
                    turns_left = max_turns - turn + 1
                    time_up = remaining <= FORCE_COMMIT_REMAINING_SECONDS
                    budget_low = _spend_left() <= FORCE_COMMIT_BUDGET_USD
                    force_text = turns_left <= 1 or time_up or budget_low
                    search_capped = search_fetch_used >= MAX_SEARCH_FETCH_CALLS
                    tools = None if force_text else TOOLS_COMPUTE_ONLY if search_capped else TOOLS_ALL
                    if (turns_left <= 2 or time_up) and (not nudged):
                        messages.append({'role': 'system', 'content': _force_commit_nudge(remaining)})
                        nudged = True
                    result = await _turn(messages, deadline=deadline, tools=tools, force_text=force_text)
                    if result is None:
                        break
                    msg = result.response.choices[0].message
                    calls = msg.tool_calls or ()
                    if calls:
                        messages.append({'role': 'assistant', 'content': result.response.raw_text or '', 'tool_calls': [{'id': c.id, 'type': c.type, 'name': c.name, 'arguments': c.arguments} for c in calls]})
                        outs = await asyncio.gather(*[_run_tool(c, index, q) for c in calls], return_exceptions=True)
                        for c, tr in zip(calls, outs):
                            tr = tr if isinstance(tr, str) else f'# {c.name} ERROR: {tr}'
                            if c.name in ('search_web', 'fetch_page') and 'ERROR' not in tr:
                                search_fetch_used += 1
                            messages.append({'role': 'tool', 'tool_call_id': c.id, 'content': tr})
                        continue
                    cand = _strip_draft(_content_to_text(msg, result.response.raw_text or '').strip())
                    if hard and pool_entities and (not entity_nudged) and (not force_text) and (remaining > 45):
                        missing = _missing_entities(pool_entities, index.all_notes())
                        if missing:
                            messages.append({'role': 'assistant', 'content': cand or '(pending)'})
                            messages.append({'role': 'system', 'content': 'COVERAGE GAP: the gathered evidence has NO per-candidate data for: ' + ', '.join(missing[:8]) + '. Search each (name + the deciding criterion) NOW before finalizing. Then commit the FINAL ANSWER.'})
                            entity_nudged = True
                            continue
                    invalid = _invalid_final(cand)
                    if not invalid:
                        last_good = cand
                    if invalid and commit_retries < MAX_COMMIT_RETRIES and (remaining > 15):
                        messages.append({'role': 'assistant', 'content': cand or '(no answer produced)'})
                        messages.append({'role': 'system', 'content': _commit_directive()})
                        commit_retries += 1
                        continue
                    final = cand if not invalid else last_good or cand
                    break
                if not final:
                    final = last_good
                final = _strip_draft(final) if final else final
                if not final or _invalid_final(final):
                    forced = await _forced_final(messages, deadline)
                    if forced and (not _invalid_final(forced)):
                        final = forced
                if not hard and final and (not _invalid_final(final)) and _needs_escalation(final) and (deadline - perf_counter() > AUDIT_MIN_REMAINING) and (_spend_left() >= MIN_AUDIT_USD):
                    esc_msgs = messages + [{'role': 'assistant', 'content': final[:1500]}, {'role': 'system', 'content': _HARD_ADDENDUM + _route_directive(q)}]
                    esc = await _commit_llm(esc_msgs, deadline, 'Your previous answer hedged. Re-resolve it decisively: if the premise holds, commit the single correct answer directly with citations; if it is genuinely false on CLEAR evidence, state that with a full completeness proof. Cite every claim.')
                    if esc and (not _invalid_final(esc)):
                        final = _select_best([final, esc], is_set)
                        hard = True
                _clean_answer = bool(final) and (not _invalid_final(final)) and (not is_set) and (not _needs_escalation(final)) and (len(_BRACKET_RE.findall(_final_section(final))) >= CITE_MIN_MARKERS)
                verify_needed = hard and (not _clean_answer)
                if verify_needed and index.top() > 0 and final and (not _invalid_final(final)) and (deadline - perf_counter() > BESTOFN_MIN_REMAINING) and (_spend_left() >= MIN_AUDIT_USD):
                    extra = await asyncio.gather(*[_synth_pass(messages, deadline, 0.35 + 0.15 * i) for i in range(BESTOFN_SYNTH - 1)], return_exceptions=True)
                    cands = [final] + [c for c in extra if isinstance(c, str)]
                    best = _select_best(cands, is_set)
                    if best and (not _invalid_final(best)):
                        final = best
                if final and _looks_truncated(final) and (deadline - perf_counter() > CONCISE_RECOMMIT_MIN_REMAINING):
                    concise = await _concise_recommit(messages, final, deadline)
                    if concise and (not _invalid_final(concise)) and (not _looks_truncated(concise)):
                        final = concise
                if not final or _invalid_final(final):
                    ka = await _knowledge_answer(q, deadline)
                    if ka and (not _invalid_final(ka)):
                        final = ka
                if (hard or is_set) and final and (not _invalid_final(final)) and (deadline - perf_counter() > GAP_RESEARCH_MIN_REMAINING) and (_spend_left() >= MIN_AUDIT_USD):
                    final = await _gap_research_patch(q, final, messages, index, deadline, is_set)
                if extract and final and _looks_garbage(final) and (deadline - perf_counter() > AUDIT_MIN_REMAINING) and (_spend_left() >= MIN_AUDIT_USD):
                    fixed = await _commit_llm(messages + [{'role': 'assistant', 'content': final[:1500]}], deadline, _ANTI_GARBAGE_DIRECTIVE)
                    if fixed and (not _invalid_final(fixed)) and (not _looks_garbage(fixed)):
                        final = fixed
                refs = _citations_with_floor(final or '', index)
                if structured:
                    return await _deliver_structured(q, final or q, schema, refs, deadline)
                if not final or _invalid_final(final):
                    return Response(text=final.strip() if final and final.strip() else _INSUFFICIENT)
                display = _normalize_brackets(_final_section(final))
                if _invalid_final(display) and (not _invalid_final(final)):
                    display = _normalize_brackets(final)
                if index.top() > 0 and len(_BRACKET_RE.findall(display)) < CITE_MIN_MARKERS and (deadline - perf_counter() > AUDIT_MIN_REMAINING) and (_spend_left() >= MIN_AUDIT_USD):
                    recited = await _cite_recommit(messages, display, deadline)
                    if recited and (not _invalid_final(recited)):
                        rc = _final_section(recited)
                        rc_disp = rc if not _invalid_final(rc) else recited
                        if len(_BRACKET_RE.findall(rc_disp)) >= max(CITE_MIN_MARKERS, len(_BRACKET_RE.findall(display))):
                            final, display = (recited, rc_disp)
                display, refs = _bind_citations(display, index)
                if strict_fmt:
                    val = _apply_output_directives(q, _answer_value_text(display) or display)
                    if val and val.strip():
                        return Response(text=val.strip(), citations=refs or None)
                return Response(text=display, citations=refs or None)
            except Exception:
                if structured:
                    try:
                        return Response(output=_coerce_to_schema(last_good or q, schema))
                    except Exception:
                        pass
                return Response(text=last_good or _INSUFFICIENT)
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
        import json
        import re
        from time import perf_counter
        from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        LLM_PROVIDER = 'openrouter'
        MODEL = 'z-ai/glm-5.2'
        COMMIT_FALLBACK_MODEL = 'deepseek/deepseek-v3.2'
        SEARCH_TIMEOUT_SECONDS = 20.0
        FETCH_RETRY_ATTEMPTS = 2
        FETCH_TIMEOUT_SECONDS = 15.0
        MAX_RETRY_ATTEMPTS_PER_TURN = 2
        LLM_TURN_TIMEOUT_SECONDS = 90.0
        TASK_TOTAL_BUDGET_SECONDS = 235.0
        RESEARCH_TURN_CAP = 10
        RESEARCH_TIME_CAP_SECONDS = 140.0
        CHECKPOINT_TOOL_TURNS = 2
        FINAL_RESERVE_SECONDS = 55.0
        FINAL_RETRY_MIN_SECONDS = 25.0
        TOOL_RESULT_INLINE_CHARS = 2600
        PAGE_WINDOW_CHARS = 3600
        PAGE_WINDOWS_PER_PAGE = 3
        PAGE_WINDOW_BUDGET_CHARS = 34000
        PAGE_SOURCE_RESERVE_CHARS = PAGE_WINDOW_CHARS * PAGE_WINDOWS_PER_PAGE
        PAGE_RESERVE_POOL_CHARS = 64800
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
        COMMIT_DIGEST_SOURCES_MAX = 16
        COMMIT_DIGEST_NOTE_CHARS = 1200
        COMMIT_DIGEST_TOTAL_CHARS = 26000
        COMMIT_DIGEST_IDENTITY_CHARS = 320
        LOCALISE_MAX_PASSES = 3
        LOCALISE_WINDOW_CHARS = 1600
        LOCALISE_WINDOWS_PER_ROLE = 2
        LOCALISE_PAGES_PER_ROLE = 4
        LOCALISE_BUDGET_CHARS = 16000
        LOCALISE_MIN_SECONDS = 6.0
        REVISE_MIN_SECONDS = 26.0
        REVISE_CALL_TIMEOUT_SECONDS = 40.0
        REVISE_CONTEXT_CHARS = 11000
        REVISE_MIN_KEEP_CHARS = 200
        ROLE_PROOF_CHARS = 420
        ROLE_LIST_MAX = 8
        TOOLS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web. Returns results with title, url, and a text excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': 'Fetch a URL and return its extracted main text content.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}}, 'required': ['url']}}}]
        SYSTEM_PROMPT = "You are a precise web-research agent answering one factual question in a single continuous session. You have search_web and fetch_page tools. Follow this protocol exactly, using the literal phase markers.\n\nBRIEFING:\nOpen your first message with a BRIEFING block written from your own knowledge, before reading any tool result:\n(a) CANDIDATE POOL — every entity that might satisfy the question, one per line, formatted exactly:\n- CANDIDATE: <name> — <one-clause confidence note>\n(b) CONSTRAINTS — the atomic constraints the answer must satisfy, decomposed.\n(c) PLAN — 2-4 opening queries.\nDo not answer during the briefing. You may issue your opening tool calls in the same turn as the briefing.\n\nRESEARCH:\nCall tools adaptively. Your goal is coverage: obtain the specific figures or facts needed to test EVERY candidate against EVERY constraint — for entities that qualify AND entities that do not. If a query or page fails, pivot the query or the source rather than repeating it. METRIC RULE: when the question asks for the percentage change or growth of an economic indicator, retrieve the OFFICIAL growth-rate series for that indicator (e.g. World Bank 'GDP growth (annual %)', real terms) — NEVER derive a percentage from current-value levels yourself. SOURCE RULE: if the question names a source (e.g. Forbes, Box Office Mojo, IMDb, Rotten Tomatoes, a UN or government agency), get the data from THAT source — search it directly, fetch its page, and cite it for the core claims. For each metric, prefer ONE consistent canonical source across all candidates (same series, same year basis); do not mix sources for the same metric unless the preferred source is unreachable, and note the substitution if you must.\n\nVERIFY:\nWhen told to verify, build a per-candidate x per-constraint table from the numbered evidence, citing [n] markers. Name the near-miss exclusions and the exact criterion each fails. Do not write 'the only', 'the sole', or 'the single' unless you enumerated and checked the whole pool. Never state a figure that is not present in the numbered evidence. Never declare a candidate's data missing without re-scanning the numbered evidence for it first — if the figure is there, include or exclude that candidate on the merits, citing the figure. Check that every core figure is cited to the question's named source (or one consistent canonical source per metric); if a core figure only has a substitute source while the named source is reachable, fetch the named source before finalizing. Re-read the question's explicit output-format instructions (ordering, list format, words to include or omit) and make the final answer obey them exactly — such instructions control how you WRITE the answer text, never which entities qualify: an instruction to omit a word means write the qualifying entity's name without that word, not exclude the entity.\n\nFINAL ANSWER:\nEnd with a committed, SELF-CONTAINED answer: state the answer first, then a compact proof — each qualifying entity with the figures that qualify it, and the near-miss exclusions with the exact criterion each fails — written as clean prose or short bullets with [n] citations. Do NOT reproduce the working table or internal scaffolding; rewrite the proof as prose. A reader must be able to see the full candidate-pool reasoning from the FINAL ANSWER alone. Scoring is pairwise against a competitor: an answer that refuses, defers, or hedges to 'insufficient data' loses outright, and so does a bare answer with no completeness proof. If evidence covers only part of the pool, commit to the best-supported answer and note that the roster may be incomplete.\n\nCITATION RULE: in the final answer, put the evidence number in brackets immediately after EVERY factual claim — e.g. 'the total is 4,000 [7, 12].' A claim with no bracket after it is assumed uncited."
        BRIEFING_NUDGE = 'Your first message must open with the BRIEFING block (CANDIDATE POOL / CONSTRAINTS / PLAN) as instructed. Write it now, then begin research.'
        FORCED_COMMIT_SUFFIX = '\n\n*** FORCED COMMIT ***\nYour previous draft refused, stalled, or was cut short. That scores ZERO. Rewrite now: commit to the best evidence-supported answer, cite every claim, and do not emit tool-call syntax or apologies.'
        INSUFFICIENT_ANSWER = 'I could not complete a source-backed research answer for this question within budget.'
        TOOL_MARKUP_RE = re.compile('<\\s*/?\\s*(tool_call|arg_key|arg_value)\\b[^>]*>', re.IGNORECASE)
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

        class _ResultIndex:

            def __init__(self) -> None:
                self._by_number: dict[int, dict[str, str]] = {}
                self._spans: dict[int, list[tuple[int, int]]] = {}
                self._window_budget = PAGE_WINDOW_BUDGET_CHARS
                self._reserve_pool = PAGE_RESERVE_POOL_CHARS
                self._source_spend: dict[int, int] = {}
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
                    note = meta['note']
                    for start, end in spans:
                        parts.append(note[start:end])
                return '\n'.join(parts)

            def fetched_numbers(self) -> list[int]:
                return [n for n, meta in self._by_number.items() if meta.get('kind') == 'fetch' and meta.get('citable', True)]

        async def _run_search_web(query: str, index: _ResultIndex) -> str:
            try:
                result = await search_web(query, provider='parallel', timeout=SEARCH_TIMEOUT_SECONDS)
            except Exception as exc:
                return f'# search_web({query!r}) -> ERROR: {exc}'
            numbers = index.record(result.receipt_id, result.results, kind='search')
            lines = [f'# search_web({query!r}) -> {len(result.results)} results']
            for n, r in zip(numbers, result.results, strict=False):
                lines.append(f"[{n}] {r.title or ''}\n  url: {r.url}\n  excerpt: {(r.note or '')[:SEARCH_EXCERPT_INLINE_CHARS]}")
            return '\n'.join(lines)

        def _page_spans(note: str, terms: list[str]) -> list[tuple[int, int]]:
            head_end = min(TOOL_RESULT_INLINE_CHARS, len(note))
            spans = [(0, head_end)]
            if len(note) > head_end:
                spans.extend(_best_windows(note, terms, PAGE_WINDOW_CHARS, PAGE_WINDOWS_PER_PAGE, skip_before=head_end))
            return spans

        async def _run_fetch_page(url: str, index: _ResultIndex, terms: list[str]) -> str:
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
            shown = index.surface(n, _page_spans(note, terms))
            if not shown:
                shown = index.spans(n) or [(0, min(TOOL_RESULT_INLINE_CHARS, len(note)))]
            body = _render_spans(note, shown)
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

        def _anchored_slice_bounds(note: str, claims: list[str], window: int) -> tuple[int, int]:
            src_len = len(note)
            if src_len <= window:
                return (0, src_len)
            hay = note.lower()
            tokens: list[str] = []
            for claim in claims[:3]:
                tokens.extend(_anchor_tokens(claim))
            positions: list[int] = []
            year_positions: set[int] = set()
            for t in tokens:
                is_year = bool(re.fullmatch('(19|20)\\d\\d', t))
                i = hay.find(t)
                while i != -1 and len(positions) < 400:
                    positions.append(i)
                    if is_year:
                        year_positions.add(i)
                    i = hay.find(t, i + 1)
            if not positions:
                return (0, window)
            positions.sort()
            best_start, best_cnt = (0, 0)
            for p in positions:
                start = max(0, min(p - CITATION_ANCHOR_LEAD_CHARS, src_len - window))
                end = start + window
                cnt = sum((3 if q in year_positions else 1 for q in positions if start <= q <= end))
                if cnt > best_cnt:
                    best_cnt, best_start = (cnt, start)
            return (best_start, best_start + window)

        def _citations_from_inline_markers(answer_text: str, index: _ResultIndex) -> tuple[CitationRef, ...]:
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

        def _checkpoint_message(candidates: list[str], index: _ResultIndex) -> str:
            missing = _uncovered_candidates(candidates, index.all_note_text())
            if missing:
                coverage = 'Code-side coverage check: the gathered evidence contains NO per-candidate data for these BRIEFING candidates: ' + '; '.join(missing[:COVERAGE_LIST_MAX]) + f'. You may make AT MOST {CHECKPOINT_TOOL_TURNS} more tool-call turns, targeted ONLY at exactly these candidates; after that tools are DISABLED and you MUST commit. '
            else:
                coverage = f"You may make AT MOST {CHECKPOINT_TOOL_TURNS} more tool-call turns if a specific candidate's figures are still missing from the evidence; after that tools are DISABLED and you MUST commit. "
            return 'CHECKPOINT — the research phase is over. Enter VERIFY now: build the per-candidate x per-constraint table from the numbered evidence gathered so far, citing [n] markers. ' + coverage + "Before declaring any candidate's data missing, re-scan the numbered evidence for it — if the figure is present, decide that candidate on the merits with the figure cited. Then re-check the question's explicit output-format instructions (ordering, list format, words to include or omit), and end with FINAL ANSWER — self-contained: the answer, each qualifying entity's figures, and the near-miss exclusions with their failing criterion, as clean prose with [n] citations (no working table)."
        COMMIT_MESSAGE = 'Tools are now DISABLED. Produce the VERIFY table and FINAL ANSWER from the numbered evidence you already have, with [n] citations after every claim. Commit.'

        def _digest_numbers(index: _ResultIndex) -> list[int]:
            fetched: list[int] = []
            searched: list[int] = []
            for n in range(1, index.max_number() + 1):
                meta = index.get(n)
                if meta is None or not meta.get('citable', True):
                    continue
                if meta.get('kind') == 'fetch':
                    fetched.append(n)
                else:
                    searched.append(n)
            return sorted((fetched + searched)[:COMMIT_DIGEST_SOURCES_MAX])

        def _digest_spans(note: str, spans: list[tuple[int, int]], terms: list[str], window: int) -> list[tuple[int, int]]:
            spans = _merge_spans([(s, e) for s, e in spans if e > s])
            if not spans:
                return []
            total = sum((e - s for s, e in spans))
            if total <= window:
                return spans
            identity = min(COMMIT_DIGEST_IDENTITY_CHARS, window, spans[0][1] - spans[0][0])
            kept: list[tuple[int, int]] = [(spans[0][0], spans[0][0] + identity)] if identity > 0 else []
            left = window - identity
            scored: list[tuple[int, tuple[int, int]]] = []
            for start, end in spans:
                hits = _term_hits(note[start:end].lower(), terms)
                scored.append((len({t for _p, t in hits}), (start, end)))
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
                    left -= sum((e - s for s, e in picked))
                else:
                    kept.append((start, start + left))
                    left = 0
            return _merge_spans(kept)

        def _evidence_digest(index: _ResultIndex, terms: list[str]) -> str:
            numbers = _digest_numbers(index)
            if not numbers:
                return ''
            window = max(COMMIT_DIGEST_NOTE_CHARS, COMMIT_DIGEST_TOTAL_CHARS // len(numbers))
            parts = ['NUMBERED EVIDENCE (the sources gathered for this question; cite by these numbers):']
            for n in numbers:
                meta = index.get(n)
                if meta is None:
                    continue
                note = meta['note'] or ''
                spans = index.spans(n)
                if not spans:
                    head_end = min(window, len(note))
                    spans = _merge_spans([(0, head_end)] + _best_windows(note, terms, min(window, PAGE_WINDOW_CHARS), 1, skip_before=head_end))
                budgeted = _digest_spans(note, spans, terms, window)
                body = _render_spans(note, budgeted).strip()
                parts.append(f"[{n}] {meta.get('title') or ''}\n  url: {meta.get('url') or ''}\n{body}")
            return '\n\n'.join(parts)

        def _commit_context(question: str, candidates: list[str], index: _ResultIndex, *, terms: list[str] | None=None, notice: str='', draft: str | None=None, suffix: str='') -> list[dict[str, object]] | None:
            digest = _evidence_digest(index, terms or _key_terms(question))
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
            if len(text) < HARD_MIN_ANSWER_CHARS:
                return True
            if any((m in text.lower()[:400] for m in ABSTENTION_MARKERS)):
                return True
            if len(text) < MIN_ANSWER_CHARS:
                if not text.rstrip().endswith(('.', '!', '?', ')', ']', '"', '|', '*')):
                    return True
            return False

        def _dump_floor_answer(index: _ResultIndex) -> str | None:
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

        def _deliverable(text: str | None, index: _ResultIndex, *, cite_text: str | None=None) -> Response:
            answer = (text or '').strip()
            if not answer:
                answer = _dump_floor_answer(index) or INSUFFICIENT_ANSWER
            citations = _citations_from_inline_markers(cite_text or answer, index)
            return Response(text=answer, citations=list(citations) if citations else None)

        async def _execute_tool_calls(tool_calls, messages, index: _ResultIndex, terms: list[str], *, content: str='') -> None:
            messages.append({'role': 'assistant', 'content': content or None, 'tool_calls': [{'id': tc.id, 'type': tc.type, 'name': tc.name, 'arguments': tc.arguments} for tc in tool_calls]})
            for tc in tool_calls:
                try:
                    args = json.loads(tc.arguments or '{}')
                except json.JSONDecodeError:
                    args = {}
                if tc.name == 'search_web':
                    result_text = await _run_search_web(str(args.get('query', '')), index)
                elif tc.name == 'fetch_page':
                    result_text = await _run_fetch_page(str(args.get('url', '')), index, terms)
                else:
                    result_text = f'# unknown tool {tc.name!r}'
                messages.append({'role': 'tool', 'tool_call_id': tc.id, 'content': result_text})
        ROLE_CLAUSE_RE = re.compile('(?<=[?.;:])\\s+|\\s+(?:and|then|also|finally|additionally)\\s+(?=which|what|how|who|when|where|name|list|identify|give|state)', re.IGNORECASE)
        NUMERIC_RE = re.compile('\\d')

        class _Role:
            __slots__ = ('label', 'terms')

            def __init__(self, label: str, terms: list[str]) -> None:
                self.label = label
                self.terms = terms

        def _question_roles(question: str, candidates: list[str]) -> list[_Role]:
            roles: list[_Role] = []
            seen: set[str] = set()
            for clause in ROLE_CLAUSE_RE.split(question or ''):
                clause = clause.strip()
                if len(clause) < 12:
                    continue
                terms = _key_terms(clause, limit=10)
                if len(terms) < 2:
                    continue
                key = '|'.join(sorted(terms[:4]))
                if key in seen:
                    continue
                seen.add(key)
                roles.append(_Role(clause[:90], terms))
            for candidate in candidates[:ROLE_LIST_MAX]:
                terms = _key_terms(candidate, limit=6)
                if not terms:
                    continue
                key = '|'.join(sorted(terms[:4]))
                if key in seen:
                    continue
                seen.add(key)
                roles.append(_Role(candidate[:90], terms))
            return roles[:ROLE_LIST_MAX + 4]

        def _role_stated(role: _Role, index: _ResultIndex) -> bool:
            wanted = min(2, len(role.terms))
            for number in range(1, index.max_number() + 1):
                meta = index.get(number)
                if meta is None:
                    continue
                note = meta['note'] or ''
                for start, end in index.spans(number) or ():
                    passage = note[start:end].lower()
                    if not passage:
                        continue
                    hit_at = [passage.find(t) for t in role.terms]
                    hits = [p for p in hit_at if p >= 0]
                    if len(hits) < wanted:
                        continue
                    for p in hits:
                        near = passage[max(0, p - ROLE_PROOF_CHARS):p + ROLE_PROOF_CHARS]
                        if NUMERIC_RE.search(near):
                            return True
            return False

        def _localise(index: _ResultIndex, roles: list[_Role], deadline: float) -> list[_Role]:
            open_roles = [r for r in roles if not _role_stated(r, index)]
            budget = LOCALISE_BUDGET_CHARS
            for _pass in range(LOCALISE_MAX_PASSES):
                if not open_roles or budget <= 0 or deadline - perf_counter() < LOCALISE_MIN_SECONDS:
                    break
                surfaced = 0
                for role in open_roles:
                    for number in index.fetched_numbers()[:LOCALISE_PAGES_PER_ROLE]:
                        if budget <= 0:
                            break
                        meta = index.get(number)
                        if meta is None:
                            continue
                        note = meta['note'] or ''
                        already = index.spans(number)
                        found = _best_windows(note, role.terms, LOCALISE_WINDOW_CHARS, LOCALISE_WINDOWS_PER_ROLE, avoid=already)
                        added = index.surface(number, found)
                        for span_start, span_end in added:
                            surfaced += span_end - span_start
                            budget -= span_end - span_start
                if not surfaced:
                    break
                open_roles = [r for r in open_roles if not _role_stated(r, index)]
            return open_roles

        def _localise_notice(roles: list[_Role], open_roles: list[_Role]) -> str:
            if not roles:
                return ''
            if not open_roles:
                return 'LOCALISED EVIDENCE: every part of the question now has a passage in the numbered evidence that names it and states a figure for it. Quote those figures — do not describe them as unavailable.'
            names = '; '.join((r.label for r in open_roles[:ROLE_LIST_MAX]))
            return "LOCALISED EVIDENCE: the numbered evidence below now includes, for each part of the question, the regions of each retrieved page that mention it — not just each page's opening. Parts with no passage stating a figure yet: " + names + '. Re-scan the numbered evidence for those before treating any of them as missing.'

        def _unreported(roles: list[_Role], index: _ResultIndex, answer: str) -> list[tuple[_Role, str]]:
            hay = (answer or '').lower()
            missing: list[tuple[_Role, str]] = []
            for role in roles:
                if not _role_stated(role, index):
                    continue
                wanted = min(2, len(role.terms))
                if sum((1 for t in role.terms if t in hay)) >= wanted:
                    continue
                passage = ''
                for number in range(1, index.max_number() + 1):
                    meta = index.get(number)
                    if meta is None:
                        continue
                    note = meta['note'] or ''
                    for start, end in index.spans(number) or ():
                        body = note[start:end]
                        low = body.lower()
                        hit = [low.find(t) for t in role.terms]
                        hit = [p for p in hit if p >= 0]
                        if len(hit) < wanted:
                            continue
                        at = min(hit)
                        near = body[max(0, at - ROLE_PROOF_CHARS):at + ROLE_PROOF_CHARS]
                        if NUMERIC_RE.search(near):
                            passage = f'[{number}] {near.strip()}'
                            break
                    if passage:
                        break
                if passage:
                    missing.append((role, passage))
            return missing

        async def _revise(question: str, answer: str, gaps: list[tuple[_Role, str]], deadline: float) -> str:
            budget = deadline - perf_counter() - 3
            if budget <= 10 or not gaps:
                return answer
            room = REVISE_CONTEXT_CHARS
            blocks: list[str] = []
            for role, passage in gaps[:ROLE_LIST_MAX]:
                chunk = f'NOT REPORTED — {role.label}\n{passage[:max(0, min(room, 1400))]}'
                room -= len(chunk)
                blocks.append(chunk)
                if room <= 0:
                    break
            messages = [{'role': 'system', 'content': 'You revise a research answer that was written before part of its evidence was located. Below are passages that ARE in the evidence and that the draft does not report.\nRules:\n1. Keep everything the draft already gets right, in its structure and order.\n2. Add the located figures where they belong, each with its [n] marker.\n3. Remove any statement that something is unavailable when a passage below states it.\n4. Output the complete revised answer and nothing else — no preamble, no notes about what you changed.'}, {'role': 'user', 'content': f'QUESTION:\n{question}\n\nDRAFT ANSWER:\n{answer[:REVISE_CONTEXT_CHARS]}\n\nLOCATED PASSAGES THE DRAFT DOES NOT REPORT:\n\n' + '\n\n---\n\n'.join(blocks) + '\n\nReturn the complete revised answer now.'}]
            try:
                result = await llm_chat(provider=LLM_PROVIDER, model=MODEL, messages=messages, temperature=0.1, thinking=LlmThinkingConfig(enabled=False), timeout=min(REVISE_CALL_TIMEOUT_SECONDS, budget))
                revised = (result.response.raw_text or '').strip()
            except Exception:
                revised = ''
            if len(revised) < max(REVISE_MIN_KEEP_CHARS, int(len(answer) * 0.5)):
                return answer
            if _needs_forced_retry(revised):
                return answer
            return revised

        async def _localised_answer(question: str, roles: list[_Role], index: _ResultIndex, answer: str, deadline: float) -> str:
            _localise(index, roles, deadline)
            gaps = _unreported(roles, index, answer)
            if not gaps or deadline - perf_counter() < REVISE_MIN_SECONDS:
                return answer
            return await _revise(question, answer, gaps, deadline)

        async def _plain_query(query: Query, budget: float) -> Response:
            start = perf_counter()
            deadline = start + budget
            research_stop = min(start + RESEARCH_TIME_CAP_SECONDS, deadline - FINAL_RESERVE_SECONDS)
            index = _ResultIndex()
            terms = _key_terms(query.text)
            messages: list[dict[str, object]] = [{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': query.text}]
            candidates: list[str] = []
            final_answer: str | None = None
            notice = ''
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
                roles = _question_roles(query.text, candidates)
                open_roles = _localise(index, roles, deadline - FINAL_RESERVE_SECONDS)
                notice = _localise_notice(roles, open_roles)
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
                if index.fetched_numbers():
                    open_roles = _localise(index, roles, deadline - 10)
                    notice = _localise_notice(roles, open_roles)
                if not final_answer:
                    commit_messages = _commit_context(query.text, candidates, index, terms=terms, notice=notice)
                    if commit_messages is None:
                        messages.append({'role': 'user', 'content': COMMIT_MESSAGE})
                        commit_messages = messages
                    final_answer = await _commit_call(commit_messages, deadline=deadline)
                if not final_answer and last_content and FINAL_SECTION_RE.search(last_content):
                    final_answer = last_content
                cite_text = _strip_tool_markup(final_answer) if final_answer else ''
                display = _final_section(cite_text) if cite_text else ''
                if display and _needs_forced_retry(display):
                    retry: str | None = None
                    if deadline - perf_counter() >= FINAL_RETRY_MIN_SECONDS:
                        retry_messages = _commit_context(query.text, candidates, index, terms=terms, notice=notice, draft=final_answer, suffix=FORCED_COMMIT_SUFFIX)
                        if retry_messages is None:
                            messages.append({'role': 'assistant', 'content': final_answer})
                            messages.append({'role': 'user', 'content': COMMIT_MESSAGE + FORCED_COMMIT_SUFFIX})
                            retry_messages = messages
                        retry = await _commit_call(retry_messages, deadline=deadline)
                    retry_stripped = _strip_tool_markup(retry) if retry else ''
                    retry_display = _final_section(retry_stripped) if retry_stripped else ''
                    if retry_display and (not _needs_forced_retry(retry_display)):
                        cite_text, display = (retry_stripped, retry_display)
                    elif not _needs_forced_retry(cite_text):
                        display = cite_text
                    else:
                        display = _dump_floor_answer(index) or display
                if display:
                    decided = await _localised_answer(query.text, roles, index, display, deadline - 4)
                    cited_from = cite_text or display if decided == display else decided
                    return _deliverable(decided, index, cite_text=cited_from)
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

        async def _w2_baseline_query(query: Query) -> Response:
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
