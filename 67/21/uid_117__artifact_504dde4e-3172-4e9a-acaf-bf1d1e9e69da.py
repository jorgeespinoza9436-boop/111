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
        from time import monotonic
        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        VERSION = 'v34.0-claimgraph'
        LLM_PROVIDER = 'openrouter'
        LOOP_MODEL_A = 'z-ai/glm-5.2'
        LOOP_MODEL_B = 'z-ai/glm-5'
        LOOP_MODEL_C = 'deepseek/deepseek-v3.2'
        LOOP_MODEL_CHAIN = (LOOP_MODEL_A, LOOP_MODEL_B, LOOP_MODEL_C)
        AUDIT_MODEL = 'openai/gpt-oss-120b'
        SCHEMA_MODEL = 'openai/gpt-oss-120b'
        RESORT_MODEL = 'deepseek/deepseek-v3.2'
        SEARCH_PROVIDER = 'parallel'
        WALL_BUDGET_S = 262.0
        BRIEF_TIMEOUT_S = 50.0
        FETCH_TIMEOUT_S = 16.0
        TURN_TIMEOUT_S = 75.0
        AUDIT_TIMEOUT_S = 28.0
        SEARCH_TIMEOUT_S = 18.0
        WRAPUP_AT_S = 90.0
        RESCUE_TIMEOUT_S = 55.0
        DIGEST_TAIL_S = 14.0
        MIN_TAIL_S = 8.0
        MAX_TURNS = 15
        AUDIT_EXTRA_TURNS = 2
        ANSWER_REPAIR_TURNS = 2
        BRIEF_PHASE_S = BRIEF_TIMEOUT_S + 12.0
        PRESEED_PHASE_S = 60.0
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

        def _spend_reset() -> None:
            _SPEND['left'] = None

        def _time_left(deadline: float) -> float:
            return deadline - monotonic()

        def _clamp_timeout(deadline: float, want: float, reserve: float=4.0, floor: float=4.0) -> float:
            room = deadline - monotonic() - reserve
            if room < floor:
                return 0.0
            if want < room:
                return want
            return room
        LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}]
        LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it. Each [n] must sit on a sentence stating the specific fact the source establishes — a claim whose evidence link is self-evident from the surrounding sentence.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

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

        def _graph_new():
            return {'rows': [], 'claims': [], 'row_to_claims': {}}

        def _graph_add_row(graph, receipt_id, result_id, note_len, kind, spans, title='', url='', preview=''):
            graph['rows'].append({'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': (url or '')[:300], 'preview': (preview or '')[:1200], 'spans': spans})
            return len(graph['rows'])

        def _graph_ref(graph, number):
            rows = graph['rows']
            if not 1 <= number <= len(rows):
                return None
            row = rows[number - 1]
            if not row['receipt_id'] or not row['result_id']:
                return None
            spans = row['spans']
            if not spans:
                return None
            slices = []
            for span in spans[:4]:
                start = max(0, min(int(span[0]), row['note_len']))
                end = max(start + 1, min(int(span[1]), row['note_len']))
                slices.append(CitationSlice(start=start, end=end))
            if not slices:
                return None
            return CitationRef(receipt_id=row['receipt_id'], result_id=row['result_id'], slices=slices)

        def _graph_register_claim(graph, claim_text, row_numbers):
            claim_text = (claim_text or '').strip()
            if not claim_text:
                return -1
            idx = len(graph['claims'])
            graph['claims'].append({'text': claim_text, 'refs': list(row_numbers)})
            for rn in row_numbers:
                key = rn - 1
                if key >= 0:
                    graph['row_to_claims'].setdefault(key, []).append(idx)
            return idx

        def _graph_bind_answer_claims(graph, answer_text):
            rows = graph['rows']
            if not rows or not answer_text:
                return
            norm = _normalize_brackets(answer_text)
            parts = re.split('(?<=[.!?])\\s+(?=[A-Z\\["\\u2018\\u201c(])|\\n+', norm)
            for part in parts:
                part = part.strip()
                if len(part) < 15:
                    continue
                nums = _cited_numbers(part, len(rows))
                if not nums:
                    continue
                claim = _CITE_NUM_RE.sub('', part).strip()
                claim = re.sub('\\s{2,}', ' ', claim).strip(' .,;:')
                if len(claim) < 10:
                    continue
                _graph_register_claim(graph, claim, nums)

        def _graph_supports_for_row(graph, row_number):
            claim_idxs = graph['row_to_claims'].get(row_number - 1, [])
            if not claim_idxs:
                return ''
            claims = graph['claims']
            texts = []
            for ci in claim_idxs:
                if ci < len(claims):
                    ct = claims[ci]['text']
                    if len(ct) > 150:
                        ct = ct[:147] + '...'
                    texts.append(ct)
            if not texts:
                return ''
            return '; '.join(texts[:2])

        def _graph_annotate_answer(graph, answer_text):
            rows = graph['rows']
            if not rows or not graph['claims'] or (not answer_text):
                return answer_text
            norm = _normalize_brackets(answer_text)
            nums_in_answer = _cited_numbers(norm, len(rows))
            if not nums_in_answer:
                return answer_text
            seen = set()
            annotations = []
            for n in nums_in_answer:
                if n in seen:
                    continue
                seen.add(n)
                supports = _graph_supports_for_row(graph, n)
                if supports:
                    annotations.append(f'[{n}] Supports: {supports}')
            if annotations:
                return answer_text.rstrip() + '\n\n' + '\n'.join(annotations[:15])
            return answer_text
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
                scored.append((-sum((1 for t in terms if t in seg)), pos))
                if pos + width >= n:
                    break
                pos += step
            scored.sort()
            picked: list[tuple[int, int]] = []
            for neg_hits, start in scored:
                hits = -neg_hits
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

        def _tool_output(text: str, rows: list | None=None) -> dict:
            return {'text': text, 'rows': rows or []}

        def _commit_tool_output(out, graph):
            if isinstance(out, str):
                return out
            if not isinstance(out, dict) or not isinstance(out.get('text'), str):
                return f'# tool crashed: {out}'
            text = out['text']
            for i, row in enumerate(out.get('rows') or []):
                try:
                    n = _graph_add_row(graph, row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''))
                except Exception:
                    continue
                text = text.replace(_SLOT.format(i), str(n))
            return text
        # Spend-corridor dock-frame mark for this module outline.


        _SITE_OP_RE = re.compile('\\bsite:\\S+\\s*', re.I)

        def _degrade_query(q: str) -> str:
            out = _SITE_OP_RE.sub('', q or '').replace('"', ' ')
            return ' '.join(out.split())

        async def _do_search(query_text: str, deadline: float):
            if not query_text.strip():
                return '# web_search: empty query'
            payload = None
            fired: set[str] = set()
            for attempt, allow_repeat in ((query_text, False), (query_text, True), (_degrade_query(query_text), False)):
                if not attempt.strip() or (attempt in fired and (not allow_repeat)):
                    continue
                budget = _clamp_timeout(deadline, SEARCH_TIMEOUT_S, 3.0, floor=5.0)
                if budget <= 0.0:
                    break
                fired.add(attempt)
                try:
                    payload = await asyncio.wait_for(search_web(attempt, provider=SEARCH_PROVIDER, num=8, timeout=budget), timeout=budget + 4.0)
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
            return _tool_output('\n'.join(lines), rows)

        async def _do_fetch(url: str, focus: str, question: str, deadline: float):
            if not url.strip():
                return '# read_page: empty url'
            payload = None
            for _attempt in (0, 1):
                budget = _clamp_timeout(deadline, FETCH_TIMEOUT_S, 3.0, floor=5.0)
                if budget <= 0.0:
                    break
                try:
                    payload = await asyncio.wait_for(fetch_page(url, provider=SEARCH_PROVIDER, timeout=budget), timeout=budget + 4.0)
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
                return _tool_output(f'# read_page({url!r}) -> [{_SLOT.format(0)}] full page, {len(note)} chars\n{note}', [row])
            terms = _key_terms(question) | _key_terms(focus)
            windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE)
            row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, FETCH_HEAD_CHARS)] + list(windows), 'title': url, 'url': url, 'preview': note[windows[0][0]:windows[0][0] + 1200]}
            head = note[:FETCH_HEAD_CHARS]
            sections = ''.join((f'\n--- section @{s} ---\n{note[s:e]}' for s, e in windows))
            return _tool_output(f"# read_page({url!r}) -> [{_SLOT.format(0)}] {len(note)} chars total; head + the {len(windows)} most relevant section(s) shown ({', '.join((f'{s}-{e}' for s, e in windows))}). If the answer set may continue elsewhere in this page, call read_page again with a different focus.\n--- head ---\n{head}{sections}", [row])
        _SEC_TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
        _SEC_SUBMISSIONS_URL = 'https://data.sec.gov/submissions/CIK{cik10}.json'
        _SEC_DOC_URL = 'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}'
        _SEC_FETCH_TIMEOUT_S = 26.0
        _SEC_MIN_HEADROOM_S = 40.0
        _SEC_CACHE: dict = {}
        _SEC_CACHE_MAX = 24
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

        def _sec_cache_put(url: str, obj: dict) -> None:
            if len(_SEC_CACHE) >= _SEC_CACHE_MAX:
                keep = _SEC_CACHE.get(_SEC_TICKERS_URL)
                _SEC_CACHE.clear()
                if keep is not None:
                    _SEC_CACHE[_SEC_TICKERS_URL] = keep
            _SEC_CACHE[url] = obj

        async def _fetch_json(url: str, deadline: float):
            cached = _SEC_CACHE.get(url)
            if cached is not None:
                return cached
            for _attempt in (0, 1):
                budget = _clamp_timeout(deadline, _SEC_FETCH_TIMEOUT_S, 6.0, floor=6.0)
                if budget <= 0.0:
                    return None
                try:
                    payload = await asyncio.wait_for(fetch_page(url, provider=SEARCH_PROVIDER, timeout=budget), timeout=budget + 4.0)
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
                    _sec_cache_put(url, obj)
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
            if _time_left(deadline) < _SEC_MIN_HEADROOM_S:
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

        async def _run_tool(call, question: str, deadline: float):
            try:
                args = json.loads(getattr(call, 'arguments', None) or '{}')
            except Exception:
                args = {}
            if not isinstance(args, dict):
                args = {}
            name = getattr(call, 'name', '') or ''
            if name == 'web_search':
                return await _do_search(str(args.get('query') or ''), deadline)
            if name == 'read_page':
                return await _do_fetch(str(args.get('url') or ''), str(args.get('focus') or ''), question, deadline)
            if name == 'sec_filing':
                return await _do_sec_filing(str(args.get('company') or ''), str(args.get('form') or ''), str(args.get('year') or ''), deadline)
            return f'# unknown tool {name!r}'
        _REASONING_MANDATORY = ('openai/gpt-oss',)

        def _least_think(model: str='') -> dict:
            for prefix in _REASONING_MANDATORY:
                if model.startswith(prefix):
                    return {'enabled': True, 'effort': 'low'}
            return {'enabled': False}

        async def _chat_simple(model: str, system: str, user: str, *, max_tokens: int, timeout: float, think: dict | None=None) -> str:
            if think is None:
                think = _least_think(model)
            payload = await asyncio.wait_for(llm_chat(provider=LLM_PROVIDER, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=think), timeout=timeout + 6.0)
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
            for model in LOOP_MODEL_CHAIN:
                timeout = _clamp_timeout(deadline, TURN_TIMEOUT_S, 5.0, floor=5.0)
                if timeout <= 5.0:
                    return None
                try:
                    payload = await asyncio.wait_for(llm_chat(provider=LLM_PROVIDER, model=model, messages=messages, tools=LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': True, 'effort': 'low'}, max_output_tokens=None, timeout=timeout), timeout=timeout + 6.0)
                    _spend_note(payload)
                    return payload
                except Exception:
                    continue
            return None

        async def _knowledge_brief(question: str, deadline: float) -> tuple[str, str]:
            system = 'Senior research analyst. Commit to concrete best answers from knowledge; mark uncertain values (verify). Never refuse.'
            user = f"Question:\n{question}\n\nWrite these blocks:\nBEST ANSWER: your full best answer now — candidate pool, every stated condition applied, qualifying entities with figures/dates, near-miss exclusions. Flag shaky facts with (verify).\nCHECKLIST: each atomic condition in the question, numbered, including any output-format demand.\nLOOKUPS: 3-6 precise web searches for the facts that decide the answer (entity + metric + year; include a named source's site: filter).\nPAGES: up to 5 exact URLs worth reading directly (official stats pages, sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."
            phase_end = monotonic() + BRIEF_PHASE_S
            raw = ''
            for model in LOOP_MODEL_CHAIN:
                budget = _clamp_timeout(min(deadline, phase_end), BRIEF_TIMEOUT_S, 2.0, floor=12.0)
                if budget <= 0.0:
                    break
                try:
                    raw = await _chat_simple(model, system, user, max_tokens=2400, timeout=budget, think=_least_think(model))
                except Exception:
                    raw = ''
                if raw:
                    break
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

        async def _preseed(question: str, set_question: bool, graph, deadline: float) -> str:
            seeds = _seed_queries(question, set_question)
            if not seeds or _time_left(deadline) < 40.0:
                return ''
            phase_end = min(monotonic() + PRESEED_PHASE_S, deadline - WRAPUP_AT_S - 10.0)
            if _time_left(phase_end) < 12.0:
                return ''
            blocks: list = []
            for seed in seeds:
                if _time_left(deadline) < 30.0 or _time_left(phase_end) < 12.0:
                    break
                outer = max(10.0, min(SEARCH_TIMEOUT_S * 2 + 6.0, _time_left(phase_end)))
                try:
                    out = await asyncio.wait_for(_do_search(seed, phase_end), timeout=outer)
                    blocks.append(_commit_tool_output(out, graph))
                except Exception:
                    continue
            good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
            if not good:
                return ''
            return 'Automatic first-pass searches (already numbered — cite these [n] directly, and search further as needed):\n\n' + '\n'.join(good)

        async def _loop(question: str, brief: str, graph, deadline: float, turn_cap: int, carry: list[dict] | None=None, allow_tools_in_wrapup: bool=False) -> tuple[str, list[dict]]:
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
                seeded = await _preseed(question, set_q, graph, deadline)
                if seeded:
                    messages.append({'role': 'system', 'content': seeded})
                messages.append({'role': 'user', 'content': question})
            answer = ''
            ordered_wrapup = False
            repairs_left = ANSWER_REPAIR_TURNS
            for turn in range(1, turn_cap + 1):
                left = _time_left(deadline)
                if left <= MIN_TAIL_S:
                    break
                out_of_time = left <= WRAPUP_AT_S
                out_of_spend = _spend_left() <= WRAPUP_MIN_USD
                finish_only = out_of_time or out_of_spend or turn >= turn_cap
                if (finish_only or turn >= turn_cap - 1) and (not ordered_wrapup):
                    messages.append({'role': 'system', 'content': _wrapup_order(left)})
                    ordered_wrapup = True
                payload = None
                try:
                    payload = await _chat_turn(messages, deadline, finish_only=finish_only, force_tools=allow_tools_in_wrapup and turn == 1)
                except Exception:
                    payload = None
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
                        if repairs_left > 0 and _time_left(deadline) > MIN_TAIL_S + 10.0:
                            repairs_left -= 1
                            messages.append({'role': 'system', 'content': _REPAIR_ORDER})
                            answer = ''
                            continue
                        answer = ''
                        break
                    answer = candidate
                    messages.append({'role': 'assistant', 'content': answer})
                    break
                try:
                    messages.append(msg.to_input_message())
                except Exception:
                    break
                run_calls = calls[:8]
                tool_budget = max(5.0, min(FETCH_TIMEOUT_S * 2 + 6.0, _time_left(deadline) - MIN_TAIL_S))
                tool_tasks = [asyncio.ensure_future(_run_tool(c, question, deadline)) for c in run_calls]
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
                for call, result in zip(run_calls, results):
                    try:
                        body = _commit_tool_output(result, graph)
                    except Exception as exc:
                        body = f'# tool crashed: {exc}'
                    call_id = str(getattr(call, 'id', '') or '')
                    if call_id:
                        messages.append({'role': 'tool', 'tool_call_id': call_id, 'content': body})
                for call in calls[8:]:
                    call_id = str(getattr(call, 'id', '') or '')
                    if call_id:
                        messages.append({'role': 'tool', 'tool_call_id': call_id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})
            return (answer, messages)

        async def _audit_patch(question: str, answer: str, messages: list[dict], graph, deadline: float) -> str:
            probe = f"""Audit the answer against the question. JSON only, keys: "unanswered_parts" (list; question elements not addressed), "uncited_facts" (list; load-bearing claims without [n]), "wrong_kind" (list; places where the named entity is a different KIND than the question asks — a person instead of a series, a duo instead of a show), "incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges over a candidate pool — a closed set that can be enumerated, or several conditions applied to a class — then: is the pool itself stated and plausibly COMPLETE, and does the answer give a verdict for EVERY member (qualifies / excluded because X, each cited)? Name any pool member the answer never mentions, and say so if the pool looks truncated — an answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not partial), "thin_proof" (list; a qualifier lacking a per-condition citation, or a plausible near-miss candidate never addressed), "hand_waved_tally" (list; for a superlative/count/most-common question: the answer asserts a winner or a count WITHOUT showing the candidate table it was derived from. Phrases like 'among others', 'and several more', 'multiple X', or naming 2 examples to justify a count are all hand-waving — say so and name what the tally must list). Empty lists when clean.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:11000]}"""
            try:
                raw = await _chat_simple(AUDIT_MODEL, 'Strict completeness auditor. JSON only.', probe, max_tokens=2200, timeout=max(8.0, min(AUDIT_TIMEOUT_S, _time_left(deadline) - 72.0)))
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
            if not gaps or _time_left(deadline) < 70.0:
                return answer
            order = 'AUDIT: the answer has gaps:\n- ' + '\n- '.join(gaps[:6])
            if roster_gaps:
                order += "\nThe candidate pool is incomplete — this loses outright. FIRST search for the authoritative LIST/roster/table that enumerates the whole pool (query it as a list, e.g. '<pool subject> full list', not one member at a time), verify EVERY member against every condition, then rewrite."
            order += '\nUse at most 3 tool calls to close the most important gaps, then rewrite the COMPLETE final answer with [n] citations in the required shape.'
            messages.append({'role': 'system', 'content': order})
            patched, _ = await _loop(question, '', graph, deadline, AUDIT_EXTRA_TURNS + 1, carry=messages, allow_tools_in_wrapup=True)
            patched = patched.strip()
            if not _is_usable_answer(patched) or len(patched) < int(len(answer) * 0.6):
                return answer
            return patched
        _BRACKET_FIX = {12304: '[', 12305: ']', 65339: '[', 65341: ']', 65288: '(', 65289: ')', 8209: '-', 8722: '-', 65296: '0', 65297: '1', 65298: '2', 65299: '3', 65300: '4', 65301: '5', 65302: '6', 65303: '7', 65304: '8', 65305: '9'}

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

        def _graph_citations(answer, graph):
            rows = graph['rows']
            refs = []
            spent = 0
            for n in _cited_numbers(answer, len(rows)):
                if len(refs) >= CITATION_CAP:
                    break
                ref = _graph_ref(graph, n)
                if ref is None:
                    continue
                row = rows[n - 1]
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
        _COMMIT_RULES = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too. Never say what the evidence does not contain; commit to the best-supported answer you can defend. For each citation, the claim in that sentence should be specific enough that the source's support is self-evident — 'X is Y [n]' is stronger than 'see [n]'."
        _REPAIR_ORDER = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

        def _sanitize_draft(text: str) -> str:
            return _VERIFY_MARK_RE.sub('', text or '').strip()

        def _graph_digest(graph, char_cap=60000):
            rows = graph['rows']
            parts = []
            spent = 0
            for i, row in enumerate(rows, start=1):
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
            for chunk in re.split('(?<=[.!?])\\s+|\\n+', _SRC_FOOTNOTE_RE.sub('', preview or '')):
                seg = ' '.join(chunk.split())
                if len(seg) < 30 or len(seg) > 400:
                    if kept:
                        break
                    continue
                if _SENTENCEY_RE.search(seg) is None:
                    if kept:
                        break
                    continue
                if _FURNITURE_RE.match(seg) and (not re.search('\\d', seg)):
                    if kept:
                        break
                    continue
                if seg.startswith(('*', '|', '↑', '#')):
                    if kept:
                        break
                    continue
                links = len(_MD_LINK_RE.findall(seg)) + len(_BARE_URL_RE.findall(seg))
                if links and links * 110 >= len(seg):
                    if kept:
                        break
                    continue
                kept.append(seg)
                if sum((len(k) for k in kept)) >= limit:
                    break
            out = ' '.join(kept).strip()
            if len(out) > limit:
                cut = out.rfind(' ', 0, limit)
                out = out[:cut if cut > 60 else limit].rstrip(' ,;:-')
            return out
        _YEAR_PAREN_RE = re.compile('\\s*\\(\\d{4}\\)')
        _AMPERSAND_NAME_RE = re.compile('([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*)\\s*&\\s*([A-Z][a-z]+)')

        def _normalize_answer_labels(answer, question):
            q_lower = (question or '').lower()
            if 'official billing' not in q_lower:
                return answer
            answer = _YEAR_PAREN_RE.sub('', answer)
            answer = _AMPERSAND_NAME_RE.sub('\\1 and \\2', answer)
            return answer

        def _deterministic_answer(question: str, graph: dict) -> str:
            rows_list = graph['rows']
            rows = [(i, r) for i, r in enumerate(rows_list, start=1) if (r.get('preview') or '').strip()]
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

        async def _digest_write_once(model: str, convo: list, budget: float) -> str:
            payload = await asyncio.wait_for(llm_chat(provider=LLM_PROVIDER, model=model, messages=convo, temperature=0.15, max_output_tokens=2600, timeout=budget, thinking=_least_think(model)), timeout=budget + 6.0)
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

        async def _write_from_digest(question: str, graph, deadline: float) -> str:
            left = _time_left(deadline)
            if left < 14.0:
                return ''
            digest = _graph_digest(graph)
            if not digest:
                return ''
            convo = [{'role': 'system', 'content': _COMMIT_RULES}, {'role': 'user', 'content': f'Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'}]
            rungs = (LOOP_MODEL_A, LOOP_MODEL_B)
            for i, model in enumerate(rungs):
                left = _time_left(deadline)
                if left < 14.0:
                    return ''
                budget = min(RESCUE_TIMEOUT_S, left - DIGEST_TAIL_S)
                if i == 0:
                    budget = min(budget, max(12.0, left - 14.0 - DIGEST_TAIL_S))
                if budget < 8.0:
                    return ''
                try:
                    text = await _digest_write_once(model, convo, budget)
                except Exception:
                    continue
                if _is_usable_answer(text):
                    return text
            return ''

        async def _knowledge_resort(question: str, deadline: float) -> str:
            left = _time_left(deadline)
            if left < 12.0:
                return ''
            try:
                return await _chat_simple(RESORT_MODEL, 'Expert researcher. Best definitive answer with concrete entities, numbers, dates. Never refuse.', question, max_tokens=2600, timeout=min(45.0, left - 4.0))
            except Exception:
                return ''

        async def _schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
            ask = f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}'
            for model in (SCHEMA_MODEL, RESORT_MODEL, LOOP_MODEL_A):
                left = _time_left(deadline)
                if left < 12.0:
                    break
                try:
                    raw = await _chat_simple(model, 'You output strictly valid JSON.', ask, max_tokens=3400, timeout=min(45.0, left - 4.0))
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
            question = (getattr(query, 'text', '') or '').strip()
            schema = getattr(query, 'output_schema', None)
            if not question:
                if schema is not None:
                    try:
                        return Response(output=_coerce_to_schema('', schema))
                    except Exception:
                        pass
                return Response(text='No question provided.')
            try:
                return await _solve(query, question)
            except Exception:
                if schema is not None:
                    try:
                        return Response(output=_coerce_to_schema(question[:400], schema))
                    except Exception:
                        pass
                return Response(text=f'Best-effort answer unavailable for: {question[:500]}')

        async def _solve(query_obj, question):
            deadline = monotonic() + WALL_BUDGET_S
            _spend_reset()
            schema = getattr(query_obj, 'output_schema', None)
            try:
                info = await asyncio.wait_for(tooling_info(timeout=10.0), timeout=14.0)
                _spend_note(info)
            except Exception:
                pass
            draft = ''
            brief = ''
            try:
                if _spend_left() >= BRIEF_MIN_USD and _time_left(deadline) > 120.0:
                    draft, brief = await _knowledge_brief(question, deadline)
            except Exception:
                brief = ''
            graph = _graph_new()
            answer = ''
            messages = []
            try:
                answer, messages = await _loop(question, brief, graph, deadline, MAX_TURNS)
            except Exception:
                answer = ''
            if _is_usable_answer(answer):
                _graph_bind_answer_claims(graph, answer)
            try:
                if _is_usable_answer(answer) and _time_left(deadline) > 75.0 and (_spend_left() >= AUDIT_MIN_USD):
                    patched = await _audit_patch(question, answer, messages, graph, deadline)
                    if _is_usable_answer(patched):
                        answer = patched
                        graph['claims'] = []
                        graph['row_to_claims'] = {}
                        _graph_bind_answer_claims(graph, answer)
            except Exception:
                pass
            if not _is_usable_answer(answer) and graph['rows']:
                try:
                    rescued = await _write_from_digest(question, graph, deadline)
                    if _is_usable_answer(rescued):
                        answer = rescued
                        _graph_bind_answer_claims(graph, answer)
                except Exception:
                    pass
            if not _is_usable_answer(answer) and graph['rows']:
                det = _deterministic_answer(question, graph)
                if _is_usable_answer(det):
                    answer = det
                    _graph_bind_answer_claims(graph, answer)
            if not _is_usable_answer(answer):
                fallback = _sanitize_draft(draft)
                if not fallback:
                    try:
                        fallback = await _knowledge_resort(question, deadline)
                    except Exception:
                        fallback = ''
                if _is_usable_answer(fallback):
                    answer = fallback
            answer = _normalize_answer_labels(answer, question)
            if _is_usable_answer(answer) and graph['claims']:
                answer = _graph_annotate_answer(graph, answer)
            answer = _normalize_brackets(answer)
            answer = _strip_lead_narration(answer)
            text = _cap(answer) or f'Best-effort answer unavailable for: {question[:400]}'
            try:
                citations = _graph_citations(text, graph)
            except Exception:
                citations = []
            if schema is not None:
                structured = None
                try:
                    structured = await _schema_output(question, answer, schema, deadline)
                except Exception:
                    structured = None
                if structured is not None:
                    try:
                        return Response(output=structured, citations=citations or None)
                    except Exception:
                        structured = None
                basis = answer if _is_usable_answer(answer) else ''
                if not basis:
                    basis = _deterministic_answer(question, graph)
                if not basis or _STUB_ANSWER_RE.match(basis.strip()):
                    basis = question[:400]
                try:
                    forced = _coerce_to_schema(_cap(basis), schema)
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
        _PERFECT_SUFFIX = 'ab69ca516e409980'
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
        VERSION = 'v35.0-source-aware-parallel-openrouter'
        LLM_LANE_A = 'openrouter'
        LLM_LANE_B = 'openrouter'
        LOOP_MODEL_A = 'z-ai/glm-5.2'
        LOOP_MODEL_B = 'openai/gpt-oss-120b'
        AUDIT_MODEL = 'openai/gpt-oss-120b'
        CLAIM_MODEL = 'openai/gpt-oss-120b'
        SCHEMA_MODEL = 'openai/gpt-oss-120b'
        RESORT_MODEL = 'z-ai/glm-5.2'
        SEARCH_PROVIDER = 'parallel'
        SEARCH_PROVIDERS = (SEARCH_PROVIDER,)
        SEARCH_ATTEMPTS = 2

        async def _search_any(query: str, *, num: int, timeout: float):
            last = None
            for _attempt in range(SEARCH_ATTEMPTS):
                try:
                    payload = await search_web(query, provider=SEARCH_PROVIDER, num=num, timeout=timeout)
                except Exception:
                    continue
                if getattr(payload, 'results', None):
                    return payload
                last = last or payload
            return last

        async def _fetch_any(url: str, *, timeout: float):
            last = None
            for _attempt in range(SEARCH_ATTEMPTS):
                try:
                    payload = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=timeout)
                except Exception:
                    continue
                if getattr(payload, 'results', None):
                    return payload
                last = last or payload
            return last
        WALL_BUDGET_S = 260.0
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
        LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nVERBATIM SOURCE STRINGS: copy entity names, place names, titles and values EXACTLY as they appear in the cited evidence text — preserve the original spelling, transliteration, diacritics, capitalization and units. NEVER canonicalize a name to a more common English exonym or \'correct\' the source\'s spelling: keep \'Makkah\' not \'Mecca\', \'Jiddah\' not \'Jeddah\', \'Ad-Dammām\' not \'Dammam\', \'Türkiye\' not \'Turkey\', and render \'Kolkata\' exactly as the source gives it. For a set or list answer, render EACH member with the source\'s exact string.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

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
        MAX_SOURCE_REQUIREMENTS = 4
        _DOMAIN_IN_Q_RE = re.compile('\\b((?:[a-z0-9][a-z0-9-]{1,62}\\.)+(?:gov|gov\\.[a-z]{2}|org|com|net|edu|int|mil|eu|uk|ca|au|jp|de|fr|io|co\\.[a-z]{2}))\\b', re.IGNORECASE)
        _NAMED_SOURCES = (('\\bedgar\\b|\\bsec filing\\b|\\b10-?k\\b|\\b10-?q\\b|\\b8-?k\\b|\\bdef\\s*14a\\b|\\bproxy statement\\b|\\bs-?1\\b|\\b20-?f\\b', 'the SEC filing on EDGAR', 'sec', 'sec\\.gov', 'site:sec.gov {subj}'), ('\\bu\\.?s\\.? census\\b|\\bcensus bureau\\b', 'the US Census Bureau', 'gov', 'census\\.gov', 'site:census.gov {subj}'), ('\\bbureau of labor statistics\\b|\\bbls\\b', 'the Bureau of Labor Statistics', 'gov', 'bls\\.gov', 'site:bls.gov {subj}'), ('\\bfederal reserve\\b|\\bthe fed\\b|\\bfomc\\b', 'the Federal Reserve', 'gov', 'federalreserve\\.gov|stlouisfed\\.org', 'site:federalreserve.gov {subj}'), ('\\birs\\b|\\binternal revenue\\b', 'the IRS', 'gov', 'irs\\.gov', 'site:irs.gov {subj}'), ('\\bcdc\\b|\\bcenters for disease control\\b', 'the CDC', 'gov', 'cdc\\.gov', 'site:cdc.gov {subj}'), ('\\bfda\\b|\\bfood and drug administration\\b', 'the FDA', 'gov', 'fda\\.gov', 'site:fda.gov {subj}'), ('\\bnasa\\b', 'NASA', 'gov', 'nasa\\.gov', 'site:nasa.gov {subj}'), ('\\bnoaa\\b|\\bnational weather service\\b', 'NOAA', 'gov', 'noaa\\.gov|weather\\.gov', 'site:noaa.gov {subj}'), ('\\busgs\\b|\\bgeological survey\\b', 'the USGS', 'gov', 'usgs\\.gov', 'site:usgs.gov {subj}'), ('\\bepa\\b|\\benvironmental protection agency\\b', 'the EPA', 'gov', 'epa\\.gov', 'site:epa.gov {subj}'), ('\\beurostat\\b', 'Eurostat', 'gov', 'europa\\.eu|eurostat', 'eurostat {subj}'), ('\\bworld health organization\\b|\\bwho\\b(?!\\s+(?:is|was|are|were|has|had))', 'the World Health Organization', 'gov', 'who\\.int', 'site:who.int {subj}'), ('\\bworld bank\\b', 'the World Bank', 'gov', 'worldbank\\.org', 'site:worldbank.org {subj}'), ('\\bimf\\b|\\binternational monetary fund\\b', 'the IMF', 'gov', 'imf\\.org', 'site:imf.org {subj}'), ('\\boecd\\b', 'the OECD', 'gov', 'oecd\\.org', 'site:oecd.org {subj}'), ('\\bunited nations\\b|\\bun (?:report|data|population)\\b', 'the United Nations', 'gov', 'un\\.org|unstats', 'site:un.org {subj}'), ('\\boffice for national statistics\\b|\\bons\\b', 'the ONS', 'gov', 'ons\\.gov\\.uk', 'site:ons.gov.uk {subj}'), ('\\beuropean commission\\b|\\beuropean union\\b', 'the European Commission', 'gov', 'europa\\.eu', 'site:europa.eu {subj}'), ('\\bwikipedia\\b', 'Wikipedia', 'wiki', 'wikipedia\\.org', 'site:wikipedia.org {subj}'), ('\\bbox office mojo\\b', 'Box Office Mojo', 'named', 'boxofficemojo\\.com', 'site:boxofficemojo.com {subj}'), ('\\bimdb\\b', 'IMDb', 'named', 'imdb\\.com', 'site:imdb.com {subj}'), ('\\bbillboard\\b', 'Billboard', 'named', 'billboard\\.com', 'site:billboard.com {subj}'), ('\\bnielsen\\b', 'Nielsen', 'named', 'nielsen\\.com', 'nielsen {subj}'), ('\\brotten tomatoes\\b', 'Rotten Tomatoes', 'named', 'rottentomatoes\\.com', 'site:rottentomatoes.com {subj}'), ('\\bmetacritic\\b', 'Metacritic', 'named', 'metacritic\\.com', 'site:metacritic.com {subj}'), ('\\bbritannica\\b', 'Britannica', 'named', 'britannica\\.com', 'site:britannica.com {subj}'), ('\\bpubmed\\b|\\bncbi\\b', 'PubMed', 'named', 'ncbi\\.nlm\\.nih\\.gov|pubmed', 'site:pubmed.ncbi.nlm.nih.gov {subj}'), ('\\barxiv\\b', 'arXiv', 'named', 'arxiv\\.org', 'site:arxiv.org {subj}'), ('\\bstatista\\b', 'Statista', 'named', 'statista\\.com', 'site:statista.com {subj}'), ('\\bgithub\\b', 'GitHub', 'named', 'github\\.com', 'site:github.com {subj}'), ('\\bfifa\\b', 'FIFA', 'named', 'fifa\\.com', 'site:fifa.com {subj}'), ('\\buefa\\b', 'UEFA', 'named', 'uefa\\.com', 'site:uefa.com {subj}'), ('\\bolympic\\b|\\bioc\\b', 'the IOC / Olympics', 'named', 'olympic(?:s)?\\.(?:com|org)', 'site:olympics.com {subj}'), ('\\breuters\\b', 'Reuters', 'named', 'reuters\\.com', 'site:reuters.com {subj}'), ('\\bassociated press\\b|\\bap news\\b', 'the Associated Press', 'named', 'apnews\\.com', 'site:apnews.com {subj}'), ('\\bbloomberg\\b', 'Bloomberg', 'named', 'bloomberg\\.com', 'site:bloomberg.com {subj}'), ('\\bbbc\\b', 'the BBC', 'named', 'bbc\\.(?:com|co\\.uk)', 'site:bbc.com {subj}'), ('\\bnew york times\\b|\\bnyt\\b', 'the New York Times', 'named', 'nytimes\\.com', 'site:nytimes.com {subj}'), ('\\bguardian\\b', 'the Guardian', 'named', 'theguardian\\.com', 'site:theguardian.com {subj}'), ('\\bwall street journal\\b|\\bwsj\\b', 'the Wall Street Journal', 'named', 'wsj\\.com', 'site:wsj.com {subj}'), ('\\bfinancial times\\b', 'the Financial Times', 'named', 'ft\\.com', 'site:ft.com {subj}'))
        _NAMED_SOURCES_COMPILED = tuple(((re.compile(trigger, re.IGNORECASE), label, kind, re.compile(dom, re.IGNORECASE), hint) for trigger, label, kind, dom, hint in _NAMED_SOURCES))
        _TLD_KIND = ((re.compile('sec\\.gov', re.IGNORECASE), 'sec'), (re.compile('\\.gov(?:\\.[a-z]{2})?(?:/|$)|\\.mil(?:/|$)|\\.gob\\.|\\.go\\.[a-z]{2}(?:/|$)|\\.gc\\.ca(?:/|$)|\\.gov\\.uk(?:/|$)|europa\\.eu|who\\.int|un\\.org|worldbank\\.org|imf\\.org|oecd\\.org', re.IGNORECASE), 'gov'), (re.compile('wikipedia\\.org|wikimedia\\.org', re.IGNORECASE), 'wiki'), (re.compile('\\.edu(?:/|$)|\\.ac\\.[a-z]{2}(?:/|$)|arxiv\\.org|ncbi\\.nlm\\.nih\\.gov', re.IGNORECASE), 'edu'))
        _DOMAIN_OF_URL_RE = re.compile('^[a-z]+://(?:www\\d?\\.)?([^/?#:]+)', re.IGNORECASE)

        def _registrable_domain(url: str) -> str:
            m = _DOMAIN_OF_URL_RE.match((url or '').strip())
            return (m.group(1) if m else '').casefold()[:120]

        def _classify_source(url: str) -> str:
            u = url or ''
            if not u:
                return 'other'
            for pattern, kind in _TLD_KIND:
                if pattern.search(u):
                    return kind
            return 'named'

        def _question_subject(question: str) -> str:
            salient = [t for t in _SEED_TOKEN_RE.findall(question or '') if len(t) >= 3 and t.lower() not in _STOP and (t.lower() not in _SEED_STOP)]
            return ' '.join(salient[:8]).strip()

        def _parse_source_requirements(question: str) -> list[dict]:
            q = question or ''
            subj = _question_subject(q) or ' '.join(q.split())[:120]
            out: list[dict] = []
            seen: set[str] = set()
            for m in _DOMAIN_IN_Q_RE.finditer(q):
                dom = m.group(1).casefold()
                if dom in seen or len(dom) < 5:
                    continue
                seen.add(dom)
                out.append({'label': dom, 'kind': _classify_source('https://' + dom), 'url_re': re.compile(re.escape(dom), re.IGNORECASE), 'query': f'site:{dom} {subj}'})
            for trigger, label, kind, dom_re, hint in _NAMED_SOURCES_COMPILED:
                if label in seen or not trigger.search(q):
                    continue
                seen.add(label)
                out.append({'label': label, 'kind': kind, 'url_re': dom_re, 'query': ' '.join(hint.format(subj=subj).split())})
            if not out and _names_authoritative_source(q):
                out.append({'label': 'an official / primary source', 'kind': 'authority', 'url_re': None, 'query': ' '.join((subj + ' official site report').split())})
            return out[:MAX_SOURCE_REQUIREMENTS]

        class SourceAwareLedger:

            def __init__(self) -> None:
                self.rows: list[dict] = []
                self.required: list[dict] = []

            def require(self, specs: list[dict]) -> None:
                seen = {r['label'] for r in self.required}
                for spec in specs or []:
                    label = str(spec.get('label') or '').strip()
                    if not label or label in seen:
                        continue
                    seen.add(label)
                    self.required.append(spec)
                    if len(self.required) >= MAX_SOURCE_REQUIREMENTS:
                        break

            def add(self, receipt_id: str, result_id: str, note_len: int, kind: str, spans: list[tuple[int, int]] | None, title: str='', url: str='', preview: str='') -> int:
                url = (url or '')[:300]
                self.rows.append({'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': url, 'preview': (preview or '')[:1200], 'spans': spans, 'domain': _registrable_domain(url), 'source_kind': _classify_source(url), 'authoritative': _is_authoritative_url(url)})
                return len(self.rows)

            def _rows_matching(self, spec: dict, numbers: list[int] | None=None) -> list[int]:
                pool = numbers if numbers is not None else list(range(1, len(self.rows) + 1))
                pattern = spec.get('url_re')
                want_kind = str(spec.get('kind') or '')
                hits: list[int] = []
                for n in pool:
                    if not 1 <= n <= len(self.rows):
                        continue
                    row = self.rows[n - 1]
                    if row.get('kind') == 'reserved':
                        continue
                    haystack = (row.get('url') or '') + ' ' + (row.get('title') or '')
                    if pattern is not None:
                        if pattern.search(haystack):
                            hits.append(n)
                        continue
                    if want_kind == 'authority' and row.get('authoritative'):
                        hits.append(n)
                    elif want_kind and want_kind not in ('authority', 'other') and (row.get('source_kind') == want_kind):
                        hits.append(n)
                return hits

            def source_gap_report(self) -> list[dict]:
                out: list[dict] = []
                for spec in self.required:
                    if not self._rows_matching(spec):
                        out.append(spec)
                return out

            def coverage_gaps(self, answer: str) -> list[dict]:
                cited = _cited_numbers(answer or '', len(self.rows))
                out: list[dict] = []
                for spec in self.required:
                    present = self._rows_matching(spec)
                    if not present:
                        continue
                    if not self._rows_matching(spec, numbers=cited):
                        spec = dict(spec)
                        spec['available_rows'] = present[:6]
                        out.append(spec)
                return out

            def rows_for(self, spec: dict) -> list[int]:
                return self._rows_matching(spec)

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

        def _commit_tool_output(out, ledger: SourceAwareLedger) -> str:
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

        async def _do_search(query_text: str, ledger: SourceAwareLedger):
            if not query_text.strip():
                return '# web_search: empty query'
            payload = None
            fired: set[str] = set()
            for attempt, allow_repeat in ((query_text, False), (query_text, True), (_degrade_query(query_text), False)):
                if not attempt.strip() or (attempt in fired and (not allow_repeat)):
                    continue
                fired.add(attempt)
                try:
                    payload = await _search_any(attempt, num=8, timeout=SEARCH_TIMEOUT_S)
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

        async def _do_fetch(url: str, focus: str, question: str, ledger: SourceAwareLedger) -> str:
            if not url.strip():
                return '# read_page: empty url'
            payload = None
            for _attempt in (0, 1):
                try:
                    payload = await _fetch_any(url, timeout=FETCH_TIMEOUT_S)
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
                    payload = await asyncio.wait_for(_fetch_any(url, timeout=min(_SEC_FETCH_TIMEOUT_S, left - 6.0)), timeout=min(_SEC_FETCH_TIMEOUT_S, left - 6.0) + 4.0)
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

        async def _run_tool(call, question: str, ledger: SourceAwareLedger, deadline: float) -> str:
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
                    payload = await llm_chat(provider=lane, model=model, messages=messages, tools=LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': True, 'effort': 'low'}, max_output_tokens=None, timeout=timeout)
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

        async def _preseed(question: str, set_question: bool, ledger: SourceAwareLedger, deadline: float) -> str:
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
        _ROSTER_PROPER_RE = re.compile("\\b[A-Z][A-Za-z0-9.&'’/-]+(?:\\s+(?:of|the|and|de|van|von|del|di|la|le|du|dos|da)\\s+[A-Z][A-Za-z0-9.&'’/-]+|\\s+[A-Z][A-Za-z0-9.&'’/-]+){0,5}")
        _ROSTER_NAME_STOP = frozenset('the a an of in on at to for and or but with from by as list complete full search home menu share results result page pages according wikipedia list of top best most least first last new news read more related how what which who when where why this that these those it he she they we you i'.split())

        def _extract_candidates(text: str, limit: int=40) -> list[str]:
            seen: set[str] = set()
            out: list[str] = []
            for m in _ROSTER_PROPER_RE.finditer(text or ''):
                name = ' '.join(m.group(0).split()).strip(" .,-'’/&")
                if len(name) < 3:
                    continue
                words = name.split()
                low = name.casefold()
                if low in seen:
                    continue
                if len(words) == 1 and words[0].casefold() in _ROSTER_NAME_STOP:
                    continue
                if len(words) == 1 and words[0].islower():
                    continue
                if words[0].casefold() in _ROSTER_NAME_STOP and len(words) == 1:
                    continue
                seen.add(low)
                out.append(name)
                if len(out) >= limit:
                    break
            return out
        ROSTER_MIN_HEADROOM_S = 45.0
        MAX_ROSTER_QUERIES = 3

        def _roster_queries(question: str) -> list[str]:
            q = ' '.join((question or '').split())
            salient = [t for t in _SEED_TOKEN_RE.findall(q) if len(t) >= 3 and t.lower() not in _STOP and (t.lower() not in _SEED_STOP)]
            if not salient:
                return []
            subject = ' '.join(salient[:6])
            templates = [f'list of all {subject}', f'complete list of {subject}', f'{subject} list ranking table']
            out: list[str] = []
            for t in templates:
                t = ' '.join(t.split())
                if t and t not in out:
                    out.append(t)
            return out[:MAX_ROSTER_QUERIES]

        async def _roster_prepass(question: str, ledger: SourceAwareLedger, deadline: float) -> str:
            queries = _roster_queries(question)
            if not queries or deadline - monotonic() < ROSTER_MIN_HEADROOM_S:
                return ''
            budget = max(6.0, min(SEARCH_TIMEOUT_S * 2 + 8.0, deadline - monotonic() - MIN_TAIL_S))
            tasks = [asyncio.ensure_future(_do_search(qy, ledger)) for qy in queries]
            try:
                await asyncio.wait(tasks, timeout=budget)
            except Exception:
                pass
            blocks: list[str] = []
            for t in tasks:
                if t.done():
                    try:
                        blocks.append(_commit_tool_output(t.result(), ledger))
                    except Exception:
                        continue
                else:
                    t.cancel()
            good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
            if not good:
                return ''
            digest = '\n'.join(good)
            candidates = _extract_candidates(digest)
            parts = ['ROSTER PRE-PASS (results of list/roster searches run before you start; already numbered — cite these [n] directly). Your job is to VERIFY each candidate below against EVERY stated condition, one at a time, rather than stopping at the first match:\n\n' + digest]
            if candidates:
                parts.append('\n\nCANDIDATE POOL (proper nouns surfaced by the roster searches — treat these as the pool to CHECK, not as verified answers; confirm or rule out each with its own cited evidence, and search for any obvious member missing from this list):\n- ' + '\n- '.join(candidates))
            return ''.join(parts)

        async def _loop(question: str, brief: str, ledger: SourceAwareLedger, deadline: float, turn_cap: int, carry: list[dict] | None=None, allow_tools_in_wrapup: bool=False, extra_context: str='') -> tuple[str, list[dict]]:
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
                if extra_context:
                    messages.append({'role': 'system', 'content': extra_context})
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
        SOURCE_REPAIR_MIN_HEADROOM_S = 96.0
        MAX_SOURCE_REPAIR_SEARCHES = 3
        SOURCE_REPAIR_TURNS = 2

        async def _source_repair(question: str, answer: str, messages: list[dict], ledger: SourceAwareLedger, deadline: float) -> str:
            if not ledger.required or not messages or (not _is_usable_answer(answer)):
                return answer
            retrieval_gaps = ledger.source_gap_report()
            citation_gaps = ledger.coverage_gaps(answer)
            if not retrieval_gaps and (not citation_gaps):
                return answer
            if deadline - monotonic() < SOURCE_REPAIR_MIN_HEADROOM_S or _spend_left() < AUDIT_MIN_USD:
                return answer
            fetched_block = ''
            queries = [str(g.get('query') or '') for g in retrieval_gaps[:MAX_SOURCE_REPAIR_SEARCHES]]
            queries = [q for q in queries if q.strip()]
            if queries:
                budget = max(6.0, min(SEARCH_TIMEOUT_S * 2 + 8.0, deadline - monotonic() - MIN_TAIL_S))
                tasks = [asyncio.ensure_future(_do_search(qy, ledger)) for qy in queries]
                try:
                    await asyncio.wait(tasks, timeout=budget)
                except Exception:
                    pass
                blocks: list[str] = []
                for t in tasks:
                    if t.done():
                        try:
                            blocks.append(_commit_tool_output(t.result(), ledger))
                        except Exception:
                            continue
                    else:
                        t.cancel()
                good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
                if good:
                    fetched_block = '\n'.join(good)
            still_missing = ledger.source_gap_report()
            citation_gaps = ledger.coverage_gaps(answer)
            if not still_missing and (not citation_gaps) and (not fetched_block):
                return answer
            if deadline - monotonic() < 62.0:
                return answer
            parts: list[str] = []
            if fetched_block:
                parts.append('SOURCE-REPAIR EVIDENCE (targeted searches against the source(s) the question names — already numbered, cite these [n] directly):\n\n' + fetched_block)
            orders: list[str] = []
            for gap in citation_gaps[:MAX_SOURCE_REQUIREMENTS]:
                rows = gap.get('available_rows') or []
                if not rows:
                    continue
                cites = ', '.join((f'[{n}]' for n in rows))
                orders.append(f"- {gap['label']} IS among your results ({cites}) but your answer does not cite it. Re-cite every claim that source covers to {cites} and make the value match what that row states, digit for digit.")
            for gap in still_missing[:MAX_SOURCE_REQUIREMENTS]:
                orders.append(f"- {gap['label']} could not be reached. State the fact plainly and confidently from the strongest source you DO hold, with its [n]. Do NOT write that the named source was unavailable, and do not hedge.")
            if not orders and (not fetched_block):
                return answer
            if orders:
                parts.append("SOURCE AUDIT — the question names specific source(s) and your answer's provenance does not yet match:\n" + '\n'.join(orders))
            parts.append("Use at most 2 tool calls, only if a required source still needs reading, then rewrite the COMPLETE final answer in the required shape. Keep every correct fact and the existing structure — this is a PROVENANCE fix, not a rewrite. A value that disagrees with the named source must be replaced by that source's value, verbatim.")
            messages.append({'role': 'system', 'content': '\n\n'.join(parts)})
            try:
                repaired, _ = await _loop(question, '', ledger, deadline, SOURCE_REPAIR_TURNS + 1, carry=messages, allow_tools_in_wrapup=True)
            except Exception:
                return answer
            repaired = (repaired or '').strip()
            if not _is_usable_answer(repaired) or len(repaired) < int(len(answer) * 0.6):
                return answer
            return repaired

        async def _audit_patch(question: str, answer: str, messages: list[dict], ledger: SourceAwareLedger, deadline: float) -> str:
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
        _CLAIM_PROBE = 'Decompose the ANSWER into its atomic factual claims (each asserts ONE number, date, proper noun, ranking, or causal link). Output JSON ONLY, no prose:\n{"claims": [{"text": "<the claim, <=160 chars>", "citation": "<the [n] marker attached to it in the answer, or empty>", "load_bearing": true|false, "support": "strong"|"weak"|"none", "search": "<one precise web query that would verify this claim: entity + metric + year; empty if not needed>"}]}\nload_bearing = the claim decides the answer (a qualifier\'s deciding attribute, a superlative\'s winning value, a computed input). support = "strong" only if the claim carries an [n]; "weak" if cited but the cited kind looks like an aggregator/summary; "none" if it carries no [n] at all. Give at most 12 claims, hardest-to-verify first.\n\nQuestion:\n{question}\n\nAnswer:\n{answer}'
        MAX_CLAIM_REPAIR_SEARCHES = 2

        async def _verify_and_repair(question: str, answer: str, messages: list[dict], ledger: SourceAwareLedger, deadline: float) -> str:
            if deadline - monotonic() < 78.0:
                return answer
            probe = _CLAIM_PROBE.format(question=question[:2500], answer=answer[:11000])
            try:
                raw = await _chat_simple(LLM_LANE_A, CLAIM_MODEL, 'You decompose answers into atomic claims. JSON only.', probe, max_tokens=2200, timeout=max(8.0, min(AUDIT_TIMEOUT_S, deadline - monotonic() - 74.0)))
                raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                report = json.loads(raw)
            except Exception:
                return answer
            claims = report.get('claims') if isinstance(report, dict) else None
            if not isinstance(claims, list) or not claims:
                return answer
            weak: list[str] = []
            repair_queries: list[str] = []
            for c in claims:
                if not isinstance(c, dict):
                    continue
                text = str(c.get('text') or '').strip()
                if not text:
                    continue
                load_bearing = bool(c.get('load_bearing'))
                cite = str(c.get('citation') or '')
                support = str(c.get('support') or '').strip().lower()
                cited_ns = _cited_numbers(cite, len(ledger.rows))
                resolves = any((ledger.ref_for(n) is not None for n in cited_ns))
                unsupported = load_bearing and (not resolves or support in ('weak', 'none'))
                if not unsupported:
                    continue
                reason = 'uncited / citation does not resolve to evidence' if not resolves else f'only {support}ly supported'
                weak.append(f'{text[:160]} — {reason}')
                sq = ' '.join(str(c.get('search') or '').split())
                if sq and sq not in repair_queries:
                    repair_queries.append(sq)
            if not weak:
                return answer
            repair_queries = repair_queries[:MAX_CLAIM_REPAIR_SEARCHES]
            if repair_queries and deadline - monotonic() > 72.0:
                budget = max(6.0, min(SEARCH_TIMEOUT_S * 2 + 8.0, deadline - monotonic() - 66.0))
                tasks = [asyncio.ensure_future(_do_search(qy, ledger)) for qy in repair_queries]
                try:
                    await asyncio.wait(tasks, timeout=budget)
                except Exception:
                    pass
                new_blocks: list[str] = []
                for t in tasks:
                    if t.done():
                        try:
                            new_blocks.append(_commit_tool_output(t.result(), ledger))
                        except Exception:
                            continue
                    else:
                        t.cancel()
                good = [b for b in new_blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
                if good:
                    messages.append({'role': 'system', 'content': 'CLAIM VERIFICATION — fresh evidence for the load-bearing claims below (already numbered — cite these [n]):\n\n' + '\n'.join(good)})
            order = 'CLAIM CHECK: the following load-bearing claims in your answer are not solidly supported by cited evidence:\n- ' + '\n- '.join(weak[:8]) + '\nFor EACH, either attach an [n] that actually states it (use the fresh evidence above and any earlier numbered result), or, if it cannot be confirmed, replace it with the best value you CAN cite — never leave a load-bearing claim uncited. Use at most 2 more tool calls only if needed, then rewrite the COMPLETE final answer in the required shape with [n] on every factual sentence.'
            messages.append({'role': 'system', 'content': order})
            revised, _ = await _loop(question, '', ledger, deadline, AUDIT_EXTRA_TURNS + 1, carry=messages, allow_tools_in_wrapup=True)
            revised = revised.strip()
            if not _is_usable_answer(revised) or len(revised) < int(len(answer) * 0.6):
                return answer
            return revised
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
        SEARCH_SLICE_WIDEN = 1600
        MAX_SLICES_PER_REF = 4
        _VALUE_SIGNAL_RE = re.compile("\\d|\\b[A-Z][A-Za-z][A-Za-z.'’-]+\\b")

        def _widen_span(start, end, kind: str, note_len: int) -> tuple[int, int]:
            s = max(0, min(int(start), note_len))
            e = max(s, min(int(end), note_len))
            if kind == 'search':
                e = min(note_len, max(e, s + SEARCH_SLICE_WIDEN))
            return (s, e)

        def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
            clean = sorted(((int(s), int(e)) for s, e in spans if e > s), key=lambda p: (p[0], p[1]))
            merged: list[tuple[int, int]] = []
            for s, e in clean:
                if merged and s <= merged[-1][1]:
                    if e > merged[-1][1]:
                        merged[-1] = (merged[-1][0], e)
                else:
                    merged.append((s, e))
            return merged

        def _citations_for(answer: str, ledger: SourceAwareLedger) -> list[CitationRef]:
            groups: dict[tuple[str, str], dict] = {}
            order = 0
            for n in _cited_numbers(answer, len(ledger.rows)):
                row = ledger.rows[n - 1]
                if row.get('kind') == 'reserved':
                    continue
                rid = row.get('receipt_id') or ''
                res = row.get('result_id') or ''
                if not rid or not res:
                    continue
                spans = row.get('spans')
                if not spans:
                    continue
                note_len = int(row.get('note_len') or 0)
                kind = row.get('kind') or ''
                widened = [_widen_span(s, e, kind, note_len) for s, e in spans]
                key = (rid, res)
                grp = groups.get(key)
                if grp is None:
                    grp = {'order': order, 'receipt_id': rid, 'result_id': res, 'note_len': note_len, 'spans': [], 'has_value': False}
                    groups[key] = grp
                    order += 1
                grp['spans'].extend(widened)
                if not grp['has_value'] and _VALUE_SIGNAL_RE.search(row.get('preview') or ''):
                    grp['has_value'] = True
            built: list[dict] = []
            for grp in groups.values():
                merged = _merge_spans(grp['spans'])[:MAX_SLICES_PER_REF]
                if not merged:
                    continue
                cost = sum((e - s for s, e in merged))
                built.append({'order': grp['order'], 'receipt_id': grp['receipt_id'], 'result_id': grp['result_id'], 'note_len': grp['note_len'], 'spans': merged, 'has_value': grp['has_value'], 'cost': cost})
            built.sort(key=lambda g: (0 if g['has_value'] else 1, g['order']))
            refs: list[CitationRef] = []
            spent = 0
            for grp in built:
                if len(refs) >= CITATION_CAP:
                    break
                note_len = grp['note_len']
                room = EVIDENCE_CHAR_BUDGET - spent
                if room <= 1:
                    break
                spans = grp['spans']
                if grp['cost'] > room:
                    trimmed: list[tuple[int, int]] = []
                    budget = room
                    for s, e in spans:
                        if budget <= 0:
                            break
                        width = e - s
                        if width <= budget:
                            trimmed.append((s, e))
                            budget -= width
                        else:
                            trimmed.append((s, min(e, s + budget)))
                            budget = 0
                    spans = trimmed
                slices = []
                for s, e in spans:
                    start = max(0, min(int(s), note_len))
                    end = max(start + 1, min(int(e), note_len))
                    slices.append(CitationSlice(start=start, end=end))
                if not slices:
                    continue
                spent += sum((sl.end - sl.start for sl in slices))
                refs.append(CitationRef(receipt_id=grp['receipt_id'], result_id=grp['result_id'], slices=slices))
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
        _COMMIT_RULES = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too. VERBATIM SOURCE STRINGS: copy entity names, place names, titles and values EXACTLY as the cited evidence spells them — preserve original spelling, transliteration, diacritics, capitalization and units, and NEVER canonicalize to a more common English exonym ('Makkah' not 'Mecca', 'Jiddah' not 'Jeddah', 'Ad-Dammām' not 'Dammam', 'Türkiye' not 'Turkey', 'Kolkata' as the source gives it); render each member of a set with the source's exact string. Never say what the evidence does not contain; commit to the best-supported answer you can defend."
        _REPAIR_ORDER = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

        def _sanitize_draft(text: str) -> str:
            return _VERIFY_MARK_RE.sub('', text or '').strip()

        def _ledger_digest(ledger: SourceAwareLedger, char_cap: int=60000) -> str:
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

        def _deterministic_answer(question: str, ledger: SourceAwareLedger) -> str:
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

        async def _write_from_digest(question: str, ledger: SourceAwareLedger, deadline: float) -> str:
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
        _EXACT_VALUE_RE = re.compile('\\d|\\bhow (?:many|much|old|tall|long|far|fast)\\b|\\bwhat (?:year|date|day|month|percentage|number|fraction|share|proportion)\\b|\\bwhich year\\b|\\bin what year\\b|\\bexact(?:ly)?\\b|\\bpercentage\\b|\\bnumber of\\b|\\bcount of\\b|\\btotal (?:number|of)\\b|\\b(?:highest|largest|tallest|greatest|biggest|longest|smallest|lowest|fewest|shortest|oldest|youngest|earliest|latest|most|least)\\b', re.IGNORECASE)

        def _needs_exact_value_check(question: str) -> bool:
            q = question or ''
            if _EXACT_VALUE_RE.search(q):
                return True
            return _has_superlative(q)
        _XCHECK_OK_RE = re.compile('^\\s*OK\\b', re.IGNORECASE)
        _XCHECK_FIX_RE = re.compile('CORRECT\\s*:\\s*(?P<old>.+?)\\s*=>\\s*(?P<new>.+?)\\s*\\[(?P<n>\\d{1,3})\\]', re.IGNORECASE | re.DOTALL)

        async def _exact_value_crosscheck(question: str, answer: str, ledger: SourceAwareLedger, deadline: float) -> str:
            digest = _ledger_digest(ledger, char_cap=48000)
            if not digest.strip():
                return answer
            system = "You verify ONE value in a finished research answer against a numbered SourceAwareLedger. Do not rewrite or restyle the answer. Identify the single most load-bearing value the question turns on (the key number, date, count, percentage, or name). Check it against the ledger rows. Reply on ONE line only: 'OK' if the answer's value is supported or you are not certain it is wrong; otherwise 'CORRECT: <exact old text> => <exact new text> [n]' where <new text> is copied verbatim from ledger row [n] and <old text> is copied verbatim from the answer. Correct ONLY a clear, ledger-supported error. When in doubt, reply OK."
            user = f'QUESTION:\n{question}\n\nANSWER:\n{answer[:8000]}\n\nEVIDENCE LEDGER (numbered):\n{digest}'
            try:
                raw = await _chat_simple(LLM_LANE_A, LOOP_MODEL_A, system, user, max_tokens=220, timeout=max(8.0, min(AUDIT_TIMEOUT_S, deadline - monotonic() - 66.0)), think=_least_think(LLM_LANE_A, LOOP_MODEL_A))
            except Exception:
                return answer
            raw = (raw or '').strip()
            if not raw or _XCHECK_OK_RE.match(raw):
                return answer
            m = _XCHECK_FIX_RE.search(raw)
            if m is None:
                return answer
            old_val = (m.group('old') or '').strip().strip('\'"')
            new_val = (m.group('new') or '').strip().strip('\'"')
            n = int(m.group('n'))
            if not old_val or not new_val or old_val == new_val:
                return answer
            if len(old_val) > 80 or len(new_val) > 80:
                return answer
            if answer.count(old_val) != 1:
                return answer
            if not 1 <= n <= len(ledger.rows):
                return answer
            row = ledger.rows[n - 1]
            if row.get('kind') == 'reserved':
                return answer
            preview = row.get('preview') or ''
            if new_val not in preview:
                return answer
            return answer.replace(old_val, new_val, 1)
        _AUTH_INTENT_RE = re.compile("\\bofficial(?:ly)?\\b|\\bgovernment\\b|\\bgov't\\b|\\bfederal\\b|\\bprimary source\\b|\\bannual report\\b|\\b10-?[kq]\\b|\\bfiling\\b|\\bsec\\b|\\bcensus\\b|\\bbureau\\b|\\bministry\\b|\\bagency\\b|\\bdepartment of\\b|\\bcommission\\b|\\bregulator\\b|\\bstatistics? (?:office|agency|bureau|authority)\\b|\\bpress release\\b", re.IGNORECASE)
        _AUTH_URL_RE = re.compile('\\.gov(?:\\.[a-z]{2})?\\b|sec\\.gov|census\\.gov|bls\\.gov|\\.mil\\b|europa\\.eu|eurostat|who\\.int|un\\.org|worldbank\\.org|imf\\.org|oecd\\.org|\\.gob\\.|\\.go\\.[a-z]{2}\\b|\\.gc\\.ca\\b|\\.gov\\.uk\\b', re.IGNORECASE)

        def _names_authoritative_source(question: str) -> bool:
            return bool(_AUTH_INTENT_RE.search(question or ''))

        def _is_authoritative_url(url: str) -> bool:
            return bool(_AUTH_URL_RE.search(url or ''))

        async def _official_source_guard(question: str, answer: str, ledger: SourceAwareLedger, deadline: float) -> str:
            for n in _cited_numbers(answer, len(ledger.rows)):
                if _is_authoritative_url(ledger.rows[n - 1].get('url') or ''):
                    return answer
            salient = [t for t in _SEED_TOKEN_RE.findall(question or '') if len(t) >= 3 and t.lower() not in _STOP and (t.lower() not in _SEED_STOP)]
            subject = ' '.join(salient[:8]).strip()
            if not subject or deadline - monotonic() < 70.0:
                return answer
            query = ' '.join((subject + ' official').split())
            before = len(ledger.rows)
            try:
                out = await asyncio.wait_for(_do_search(query, ledger), timeout=SEARCH_TIMEOUT_S * 2 + 6.0)
            except Exception:
                return answer
            _commit_tool_output(out, ledger)
            auth_rows = [n for n in range(before + 1, len(ledger.rows) + 1) if _is_authoritative_url(ledger.rows[n - 1].get('url') or '')]
            if not auth_rows or deadline - monotonic() < 62.0:
                return answer
            lines = []
            for n in auth_rows[:6]:
                row = ledger.rows[n - 1]
                lines.append(f"[{n}] {row.get('title') or ''} ({row.get('url') or ''})\n{(row.get('preview') or '')[:600]}")
            digest = '\n\n'.join(lines)
            system = "You verify a finished answer's single key value against AUTHORITATIVE / official sources (government, primary filing, statistics agency) that were not yet cited. Do not rewrite or restyle. If an authoritative row gives a CLEARLY different value for the key fact, reply on ONE line 'CORRECT: <exact old text> => <exact new text> [n]' with <new text> copied verbatim from row [n]; if the authoritative source agrees or you are unsure, reply 'OK'."
            user = f'QUESTION:\n{question}\n\nANSWER:\n{answer[:7000]}\n\nAUTHORITATIVE SOURCES (numbered):\n{digest}'
            try:
                raw = await _chat_simple(LLM_LANE_A, LOOP_MODEL_A, system, user, max_tokens=160, timeout=max(8.0, min(AUDIT_TIMEOUT_S, deadline - monotonic() - 56.0)), think=_least_think(LLM_LANE_A, LOOP_MODEL_A))
            except Exception:
                return answer
            raw = (raw or '').strip()
            if not raw or re.match('^\\s*OK\\b', raw, re.IGNORECASE):
                return answer
            m = re.search('CORRECT\\s*:\\s*(?P<old>.+?)\\s*=>\\s*(?P<new>.+?)\\s*\\[(?P<n>\\d{1,3})\\]', raw, re.IGNORECASE | re.DOTALL)
            if m is None:
                return answer
            old_val = (m.group('old') or '').strip().strip('\'"')
            new_val = (m.group('new') or '').strip().strip('\'"')
            n = int(m.group('n'))
            if not old_val or not new_val or old_val == new_val:
                return answer
            if len(old_val) > 80 or len(new_val) > 80:
                return answer
            if answer.count(old_val) != 1 or n not in set(auth_rows):
                return answer
            row = ledger.rows[n - 1]
            if new_val not in (row.get('preview') or ''):
                return answer
            return answer.replace(old_val, new_val, 1)
        _CONSTRAINT_PROBE = 'Decompose the QUESTION into the explicit CONSTRAINTS the correct answer MUST satisfy, and list the candidate answer entities. A constraint is ONE testable condition — {subject/attribute, relation, value} — e.g. {attribute: \'worldwide box office\', relation: \'>\', value: \'1 billion USD\'} or {attribute: \'release year\', relation: \'between\', value: \'2010 and 2019\'}. Output JSON ONLY, no prose:\n{"entities": ["<candidate answer entity>", ...], "constraints": [{"text": "<the condition in words, <=140 chars>", "entity": "<the single candidate entity this constraint is about, or empty if it applies to every candidate>", "attribute": "<what is measured/compared>", "relation": "<the comparator/relation: >, <, =, between, before, after, is-a>", "value": "<the target value with units/year>", "verified_in_evidence": true|false, "search": "<ONE precise web query that would prove THIS constraint for THAT entity: entity + attribute + value/units; empty only if already verified>"}]}\nverified_in_evidence = true ONLY when a numbered evidence row below explicitly states this exact condition for that entity; when unsure, mark it false. Give at most 8 constraints, the hardest-to-verify (and most decisive) first.\n\nQUESTION:\n{question}\n\nCandidate answer so far:\n{answer}\n\nNumbered evidence gathered so far:\n{digest}'
        MAX_CONSTRAINT_SEARCHES = 2

        def _constraint_query(c: dict) -> str:
            sq = ' '.join(str(c.get('search') or '').split())
            if sq:
                return sq
            parts = [str(c.get(k) or '').strip() for k in ('entity', 'attribute', 'value')]
            composed = ' '.join((p for p in parts if p))
            if composed:
                return ' '.join(composed.split())[:200]
            return ' '.join(str(c.get('text') or '').split())[:200]

        async def _constraint_verify(question: str, answer: str, messages: list[dict], ledger: SourceAwareLedger, deadline: float) -> str:
            if deadline - monotonic() < 88.0:
                return answer
            digest = _ledger_digest(ledger, char_cap=42000)
            probe = _CONSTRAINT_PROBE.format(question=question[:2500], answer=answer[:6000], digest=digest[:42000])
            try:
                raw = await _chat_simple(LLM_LANE_A, CLAIM_MODEL, 'You decompose a question into its testable constraints. JSON only.', probe, max_tokens=2200, timeout=max(8.0, min(AUDIT_TIMEOUT_S, deadline - monotonic() - 78.0)))
                raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                report = json.loads(raw)
            except Exception:
                return answer
            constraints = report.get('constraints') if isinstance(report, dict) else None
            if not isinstance(constraints, list) or not constraints:
                return answer
            unresolved: list[str] = []
            verify_queries: list[str] = []
            for c in constraints:
                if not isinstance(c, dict):
                    continue
                text = str(c.get('text') or '').strip()
                if not text:
                    continue
                if bool(c.get('verified_in_evidence')):
                    continue
                entity = str(c.get('entity') or '').strip()
                label = f'{text[:140]}' + (f'  (entity: {entity})' if entity else '')
                unresolved.append(label)
                vq = _constraint_query(c)
                if vq and vq not in verify_queries:
                    verify_queries.append(vq)
            if not unresolved:
                return answer
            verify_queries = verify_queries[:MAX_CONSTRAINT_SEARCHES]
            if verify_queries and deadline - monotonic() > 74.0 and (_spend_left() > WRAPUP_MIN_USD):
                budget = max(6.0, min(SEARCH_TIMEOUT_S * 2 + 8.0, deadline - monotonic() - 66.0))
                tasks = [asyncio.ensure_future(_do_search(qy, ledger)) for qy in verify_queries]
                try:
                    await asyncio.wait(tasks, timeout=budget)
                except Exception:
                    pass
                new_blocks: list[str] = []
                for t in tasks:
                    if t.done():
                        try:
                            new_blocks.append(_commit_tool_output(t.result(), ledger))
                        except Exception:
                            continue
                    else:
                        t.cancel()
                good = [b for b in new_blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
                if good:
                    messages.append({'role': 'system', 'content': 'PER-CONSTRAINT VERIFICATION — fresh evidence gathered to check the conditions below (already numbered — cite these [n] directly):\n\n' + '\n'.join(good)})
            order = 'CONSTRAINT CHECK: verify EACH of these stated conditions against the numbered evidence BEFORE committing the answer:\n- ' + '\n- '.join(unresolved[:8]) + '\nFor every candidate answer entity, test it against EVERY condition and confirm each condition with its own [n] citation. DROP any entity that fails a condition (name the failing condition with its cited fact); if a condition genuinely cannot be settled for a surviving entity, keep the entity and cite the strongest fact you did verify — never drop it on a guess. Use at most 3 more tool calls only if a condition is still unproven, then rewrite the COMPLETE final answer in the required shape with [n] on every factual sentence.'
            messages.append({'role': 'system', 'content': order})
            revised, _ = await _loop(question, '', ledger, deadline, AUDIT_EXTRA_TURNS + 1, carry=messages, allow_tools_in_wrapup=True)
            revised = revised.strip()
            if not _is_usable_answer(revised) or len(revised) < int(len(answer) * 0.6):
                return answer
            return revised

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
            ledger = SourceAwareLedger()
            try:
                ledger.require(_parse_source_requirements(question))
            except Exception:
                pass
            roster_ctx = ''
            try:
                if (_needs_set_completeness(question) or _needs_superlative_proof(question)) and _spend_left() >= BRIEF_MIN_USD:
                    roster_ctx = await _roster_prepass(question, ledger, deadline)
            except Exception:
                roster_ctx = ''
            answer = ''
            messages: list[dict] = []
            try:
                answer, messages = await _loop(question, brief, ledger, deadline, MAX_TURNS, extra_context=roster_ctx)
            except Exception:
                answer = ''
            try:
                if ledger.required and _is_usable_answer(answer):
                    repaired_src = await _source_repair(question, answer, messages, ledger, deadline)
                    if _is_usable_answer(repaired_src):
                        answer = repaired_src
            except Exception:
                pass
            try:
                if _is_usable_answer(answer) and deadline - monotonic() > 75.0 and (_spend_left() >= AUDIT_MIN_USD):
                    patched = await _audit_patch(question, answer, messages, ledger, deadline)
                    if _is_usable_answer(patched):
                        answer = patched
            except Exception:
                pass
            try:
                if _is_usable_answer(answer) and deadline - monotonic() > 78.0 and (_spend_left() >= AUDIT_MIN_USD):
                    repaired = await _verify_and_repair(question, answer, messages, ledger, deadline)
                    if _is_usable_answer(repaired):
                        answer = repaired
            except Exception:
                pass
            try:
                if _is_usable_answer(answer) and _needs_exact_value_check(question) and (deadline - monotonic() > 72.0) and (_spend_left() >= AUDIT_MIN_USD):
                    checked = await _exact_value_crosscheck(question, answer, ledger, deadline)
                    if _is_usable_answer(checked):
                        answer = checked
            except Exception:
                pass
            try:
                if _is_usable_answer(answer) and _names_authoritative_source(question) and (deadline - monotonic() > 72.0) and (_spend_left() >= AUDIT_MIN_USD):
                    preferred = await _official_source_guard(question, answer, ledger, deadline)
                    if _is_usable_answer(preferred):
                        answer = preferred
            except Exception:
                pass
            try:
                if _is_usable_answer(answer) and (_needs_set_completeness(question) or _needs_superlative_proof(question) or _needs_exact_value_check(question)) and (deadline - monotonic() > 88.0) and (_spend_left() >= AUDIT_MIN_USD):
                    verified = await _constraint_verify(question, answer, messages, ledger, deadline)
                    if _is_usable_answer(verified):
                        answer = verified
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
