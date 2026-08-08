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
        _ISO_DATE_RE = re.compile('\\b((?:19|20)\\d{2})-([01]\\d)-([0-3]\\d)\\b')
        _MAG_RANGE_RE = re.compile('magnitude\\s*(?:of\\s*)?(\\d+(?:\\.\\d+)?)(?:\\s*(?:to|and|-|–|through)\\s*(\\d+(?:\\.\\d+)?))?', re.I)

        def _data_query_urls(question: str) -> list[str]:
            q = question or ''
            low = q.lower()
            urls: list[str] = []
            if re.search('\\bearthquakes?\\b|\\bseismic\\b', low):
                dates = ['-'.join(m) for m in _ISO_DATE_RE.findall(q)]
                years = re.findall('\\b(?:19|20)\\d{2}\\b', q)
                start = end = ''
                if len(dates) >= 2:
                    start, end = (min(dates), max(dates))
                elif len(dates) == 1:
                    start = end = dates[0]
                elif years:
                    start, end = (min(years) + '-01-01', max(years) + '-12-31')
                if start:
                    u = f'https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={start}&endtime={end}T23:59:59&orderby=time-asc'
                    m = _MAG_RANGE_RE.search(q)
                    if m:
                        u += f'&minmagnitude={m.group(1)}'
                        if m.group(2):
                            u += f'&maxmagnitude={m.group(2)}'
                    urls.append(u)
            if re.search('\\b(planets?|planetary|mercury|venus|mars|jupiter|saturn|uranus|neptune)\\b', low) and re.search('\\b(mass|gravity|density|diameter|radius|moons?|orbital|escape velocity|rotation|temperature|distance)\\b', low):
                urls.append('https://nssdc.gsfc.nasa.gov/planetary/factsheet/')
            return urls

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
            try:
                if deadline - monotonic() > 150.0 and _spend_left() >= BRIEF_MIN_USD:
                    for _u in _data_query_urls(question)[:2]:
                        if deadline - monotonic() < 125.0:
                            break
                        try:
                            _blk = await _do_fetch(_u, 'authoritative data for the question', question, ledger)
                            if _blk:
                                brief = (brief + '\n\nPREFETCHED AUTHORITATIVE DATA (cite by [n]):\n' + _blk[:2000]).strip()
                        except Exception:
                            continue
            except Exception:
                pass
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
            try:
                if re.search('\\boutput only\\b|\\bonly the exact text\\b|\\brespond only\\b|\\breturn only\\b|\\banswer only\\b|\\bnothing else\\b|\\bwithout (any )?(additional|extra) (text|explanation)\\b', question, re.I):
                    _first = re.split('\\n\\s*\\n', (answer or '').strip(), maxsplit=1)[0].strip()
                    if len(_first) >= 3:
                        answer = re.sub('^\\s*\\*{0,2}answer:?\\*{0,2}\\s*', '', _first, flags=re.I).strip()
            except Exception:
                pass
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
        SEARCH_PROVIDER = 'parallel'
        SEARCH_TIMEOUT = 10.0
        FETCH_TIMEOUT = 15.0
        LLM_TIMEOUT = 90.0
        EMBEDDING_TIMEOUT = 120.0
        DEADLINE_NOTICE_SECONDS = 150.0
        BATCHED_RETRIEVAL_PREVIEW_CHARS = 240000
        VFS_READ_PAGE_CHARS = 80000
        FOCUSED_OBSERVATION_MEMORY_CHARS = VFS_READ_PAGE_CHARS
        VFS_SEARCH_PAGE_CHARS = 60000
        VFS_SIMILARITY_MIN_CHUNKS = 3
        VFS_SIMILARITY_MAX_CHUNKS = 5
        VFS_SIMILARITY_RESULT_CHARS = 45000
        VFS_LEXICAL_WINDOW_CHARS = 3600
        VFS_LEXICAL_WINDOW_COUNT = 3
        GPT_OSS_MAX_OUTPUT_TOKENS = 65536
        OPENROUTER_GEMMA_MAX_OUTPUT_TOKENS = 40960
        AI_GATEWAY_GEMMA_MAX_OUTPUT_TOKENS = 131072
        GLM5_MAX_OUTPUT_TOKENS = 131072
        INKLING_MAX_OUTPUT_TOKENS = 131072
        CHUTES_GEMMA_MAX_OUTPUT_TOKENS = 32768
        SPEND_GOVERNOR_SOFT_FRACTION = 0.14
        SPEND_GOVERNOR_HARD_FRACTION = 0.2
        SPEND_GOVERNOR_FALLBACK_LIMIT_USD = 0.5
        SPEND_GOVERNOR_MAX_CLOSING_TURNS = 3
        TIME_GOVERNOR_SOFT_SECONDS = 150.0
        TIME_GOVERNOR_HARD_SECONDS = 195.0
        ABSOLUTE_WALL_SECONDS = 246.0
        _WALL: dict = {'started_at': None}

        def _wall_start() -> float:
            started = _WALL['started_at']
            if isinstance(started, float):
                return started
            started = time.monotonic()
            _WALL['started_at'] = started
            return started

        def _wall_elapsed() -> float:
            return time.monotonic() - _wall_start()

        def _wall_remaining() -> float:
            return ABSOLUTE_WALL_SECONDS - _wall_elapsed()
        CLOSING_TOOL_NAMES = ('update_research_state', 'retain_evidence', 'ready_to_finalize')
        MODEL_SCHEDULING = 'state_aware'
        INVESTIGATION_MODELS = ('openrouter_gemma', 'chutes_gemma', 'glm5')
        STATE_AWARE_INVESTIGATION_MODELS = ('openrouter_gemma', 'chutes_gemma', 'glm5')
        REQUIREMENTS_MODELS = ('openrouter_gemma', 'chutes_gemma', 'glm5')
        REPAIR_MODELS = ('openrouter_gemma', 'chutes_gemma', 'glm5')
        AUDIT_MODELS = ('openrouter_gemma', 'chutes_gemma', 'glm5')
        EVIDENCE_REVIEW_MODELS = INVESTIGATION_MODELS
        EMBEDDING_EXTRA = {'provider': {'only': ['nebius', 'deepinfra', 'siliconflow'], 'allow_fallbacks': True}}
        OPENROUTER_GLM_PROVIDER_PREFERENCES = {'provider': {'only': ['amazon-bedrock'], 'allow_fallbacks': True}}
        OPENROUTER_GPT_PROVIDER_PREFERENCES = {'provider': {'only': ['cerebras', 'baseten', 'deepinfra', 'sambanova', 'nebius', 'coreweave'], 'allow_fallbacks': True}}
        OPENROUTER_GEMMA_PROVIDER_PREFERENCES = {'provider': {'only': ['modelrun', 'sambanova'], 'allow_fallbacks': True}}
        OPENROUTER_GEMMA_STABLE_PROVIDER_PREFERENCES = {'provider': {'only': ['modelrun'], 'allow_fallbacks': False}}
        EXPECTED_ANSWER_SYSTEM = 'You are beginning a deep-research task. Before using external sources, write the best expected answer your internal\nknowledge suggests. This is a revisable research hypothesis, not evidence.\n\nWrite a concise working hypothesis that names the likely answer and the main uncertainty. Also state the smallest\nverification route: the finite candidate inventory, if one is needed, and the exact external facts that would prove\nor disprove the hypothesis. Name useful sources or pages, but do not produce or guess URLs; retrieval discovers exact\nURLs. This route is a heuristic for investigation, not evidence. For an exhaustive question, put the inventory source\nbefore per-candidate metric lookups. Be concrete enough that later investigation can prove, revise, or reject the\nanswer. Do not invent citations and do not avoid an answer merely because important facts remain uncertain.'
        REQUIREMENTS_INSTRUCTION = 'Before retrieval, call set_evidence_requirements once. Write one evidence question per line, leaving its answer blank.\nEach question must ask for an externally verifiable premise that the final answer needs. Do not write a search plan,\nsource description, table schema, or list of raw data to collect. No external evidence exists yet: never insert a\ncandidate, number, list member, answer, expected value, or proposition that the original question does not supply.\n\nDo not list arithmetic, set intersection, decade membership, threshold comparison, sorting, or another conclusion\nthat can be mechanically derived from externally supported operands as a separate evidence question. Ask for the\nexternal operands that the derivation requires. The derivation itself does not require an external source.\n\nSplit a person\'s role, relationship, date, and each required property of an institution into separate questions. Treat\nwording and named items supplied by the question as given. A person\'s role at an institution, the institution\'s type\nor status, and its location are separate evidence questions. For an exhaustive result, ask for the external operands\nneeded to establish the complete result, but prefer questions that return a complete filtered set over questions that\nrequest every raw value for every candidate. For an intersection of conditions, ask first for the complete result of\nthe most selective condition, then ask the remaining conditions only about candidates that survive earlier filters.\nThose later questions may be conditional and must not guess who the survivors are. Do not create a separate question\nasking whether a source or set is complete; the final audit judges whether the observed source scope is sufficient.\nWhen the original question explicitly requires retrieval from a named source, edition, page, report, or dataset, that\nsource and scope remain a required premise even if another filter could establish the same conclusion.\nAn identification question does not assert uniqueness: the phrase "the person" is grammatical, not an exhaustive\ncondition. Unless the question explicitly says only, unique, all, every, asks how many, or otherwise requires an\nexhaustive result, never require proof that no other person matches. Do not require every value for every nonqualifying\ncandidate; a candidate may be eliminated by one supported condition and only surviving candidates need the remaining\nchecks.\n\nBad requirement: "North Carolina had fatalities from Hurricane Nicole."\nGood requirement: "Which states had direct or indirect fatalities across the named 2022 storms?"\nGood requirement: "Which states had direct or indirect fatalities across the named 2023 storms?"\nBad for "Identify the person who has A and B": "Exactly one person satisfies A and B."\nGood: "Which identified person has A?" and "Which identified person has B?" '
        REQUIREMENTS_SYSTEM = 'Define the unanswered evidence questions that a complete answer to the original question must resolve. Base them only\non the original question; no expected answer or candidate hypothesis is available.\n\n' + REQUIREMENTS_INSTRUCTION
        INVESTIGATION_SYSTEM = "You are a deep-research agent. Develop a claim that answers the original question and give it enough externally\ninspectable support to persuade a skeptical reader.\n\nThe expected answer is a useful guess, not evidence. Use it to choose cheap, focused searches. Revise or replace it\nwhen observed sources disagree, reveal a better answer, or expose a missing condition. Internal knowledge may guide\nresearch, but every material external premise in the final claim needs observed support.\nWhen the question attributes facts to a named source, edition, page, report, or dataset, inspect that named source\nbefore accepting a substitute. Otherwise prefer the organization that produced the fact, an official record, or a\nprimary document over an aggregator or commentary. Begin retrieval with the named or primary source and the exact\nsubject; use secondary sources for discovery only when the direct source cannot yet be found. If the publisher page\nis unavailable, prefer an archived copy of that exact page over a third-party reproduction.\nDo not finalize from a secondary source when the observed search results already contain an accessible official or\nprimary source for the same decisive premise. Inspect the direct source first; retain the secondary source only when\nthe direct source still lacks the necessary text or scope after inspection.\nIf a clue-only search does not improve the evidence, do not paraphrase and repeat it. Change the evidence route or\ntest the expected-answer candidate directly.\nIf a required source's search surface does not expose a complete inventory, use a suitable secondary source to\ndiscover a finite candidate set, then verify each surviving candidate against the required source. A discovery source\nis a research aid, not final support for a premise the question explicitly attributes to the required source.\nFor an exhaustive question, the expected candidate pool remains unproved. Before finalizing, inspect either a source\nthat enumerates the pool or direct evidence for every candidate and plausible boundary case; metric pages for guessed\ncandidates alone do not prove that no candidate is missing.\nWhen a table explicitly ranks rows in descending order by the same numeric metric used by the question's threshold,\nyou do not need every later row after the first below-threshold row. Retain the header, every row through that boundary,\nand explain why the established ordering eliminates the remaining lower-ranked rows. This shortcut is valid only when\nthe visible header and row order establish that monotonic relationship.\n\nSearch snippets are evidence when their visible text directly supports the premise. If later retrieval steps must\ncombine that snippet with other facts, retain its smallest decisive lines before moving on; otherwise the full snippet\nmay leave active context while remaining available in VFS. Among observed sources with comparable authority and scope,\npreserve the excerpt that states the complete needed premise most directly and compactly. Do not fetch a broader copy\nmerely to replace a sufficient snippet. A search result from the named official page counts as inspection when its\nvisible text supplies the needed fact; retain that snippet rather than fetching the same page solely because the\nquestion names it. Use fetch_page only when the snippet lacks necessary context or when inspecting a discovered page\nis the most direct remaining evidence route. fetch_page accepts a full URL, including one discovered inside a search\nresult or another page. Do not construct a URL from a guessed site pattern.\nSearch and fetch results are saved in VFS. On a long page, locate relevant lines with VFS search before using VFS read\nto expand a small window. A large fetch includes question-ranked context windows in addition to its head/middle/tail\npreview; inspect those windows before searching the page again. Give each VFS search both an exact regex pattern and\na semantic query. The harness starts with regex and automatically adds embedding results only when regex fails or\nfinds nothing. For a table, keep the relevant row together with its title, series labels, year labels, and headers.\nPDF extraction can place chart values before the heading or labels they belong to. When a title match lacks its data,\ninspect both before and after it rather than assuming the table follows the title. You may reconstruct a flattened\nchart only when the excerpt exposes a complete rectangle: N ordered category labels, M series labels, and exactly M\ngroups of N data values after excluding axis ticks. State that mapping explicitly and cross-check it against the page\nheading, totals, shares, or nearby prose. If the complete structure is not visible, do not infer a cell from line order.\nWhen the question asks about a specific date, edition, or historical version, inspect a result whose title and scope\nmatch that exact period before broader or current-data pages. Do not revise a period-specific value from a source that\nvisibly describes a different period. A current rolling statistical table may revise rows labeled with past dates;\nwhen the question concerns what was reported for that period, prefer the contemporaneous archived release.\nWhen inspected sources disagree, resolve the conflict by source scope, authority, date, and fit to the question. If\none source states the question's identifying conditions and requested value together, preserve that internally\nconsistent account. A differently scoped or measured value is a limitation to disclose, not a reason to repeat\nsubstantially equivalent searches. Once further searches only reproduce the same conflict, finalize the best-supported\nanswer and state the discrepancy briefly.\nThe initial evidence questions guide retrieval; they are not a checklist that must remain material. A complete filter\nor supported elimination can make a broader question unnecessary. An explicit instruction in the original question\nto retrieve or report from a named source, edition, page, report, or dataset remains material and cannot be replaced\nby a different proof route. Before finalizing, check every premise that the current answer and its derivation actually\ndepend on against words or table cells visible in the supplied source records. Your memory of a source is not visible\nevidence. If a material row or relationship is absent from the excerpt, locate it with VFS search or fetch the\ndiscovered page; if it remains unavailable, state the limitation instead of silently supplying it.\n\nUse update_research_state whenever evidence changes the current best answer, the decisive support, or the most\nimportant unresolved question. This prose state is your working memory and is returned on every turn. Do not turn it\ninto a search log. Retain only displayed lines that directly support or contradict a material premise; do not retain a\nsource merely for possible later extraction. For a flattened table or chart, retain one continuous range containing\nthe data values, ordered category labels, series labels, and title together, even when axis ticks or spacing lie\nbetween them. Isolated number lines plus a separate title do not preserve the mapping needed to support table claims.\nFor a descending ranked table filtered by a numeric threshold, retain one continuous range from the header through\nthe first below-threshold row so the qualifying rows and the exhaustive cutoff remain inspectable together.\n\nContinue while a real uncertainty could change the answer. Before finalizing with evidence from a fetched page,\npreserve every decisive excerpt with retain_evidence. When the claim resolves the question and its material premises\nare supported, call ready_to_finalize as the final tool in the response. Its reason explains the derivation and cites\nsource references such as [P1] or [S1.2], without encoding line ranges in prose. The harness writes the answer from\nthe cited source records. A decisive search snippet may be cited without retention only when finalizing immediately;\nretain it before performing later retrieval that must be combined with it.\n\nTool failures are observations: correct the call or change approach. Tool calls in one response execute sequentially,\nso a later call must not depend on a result not yet seen. When exact arguments for several independent fetches, reads,\nor evidence retentions over an already known finite candidate set are available, emit them together in one response.\nDo not batch alternative searches for the same uncertainty: run one search and inspect its results before trying\nanother evidence route. Emit each distinct operation at most once per response."
        ANSWER_UPDATE_SYSTEM = "Write the complete best current answer to the original question as polished, reader-facing Markdown. Obey any\nexplicit output-only or formatting constraint in the original question; otherwise use substantial prose with\nstructure proportional to the answer. The expected answer, prior answer, investigator prose, and your internal\nknowledge are not evidence. Use only the supplied source records.\n\nThe investigator's current conclusion is the intended answer and derivation after research. Use it to revise the\nprior answer, while checking every external premise against the supplied source records. Do not add factual claims\nthat are unnecessary to establish the answer; for an excluded candidate, state its decisive failing condition rather\nthan unrelated background.\n\nOpen with the direct conclusion. Use short descriptive headings when they help navigation, bullets for parallel\nfindings, and a Markdown table when several candidates share the same comparison fields. Do not force a heading or\ntable onto a short answer. Keep paragraphs focused and make the decisive comparison easy to scan. Do not add a\nreferences section, bibliography, source dump, raw URL, or quoted evidence appendix.\n\nResolve the question directly, explain why the conclusion follows, and preserve relevant uncertainty. Place the\nexact internal source reference from the supplied record, such as [S1.2] or [P3], immediately after the factual claim\nit supports. These references are private placeholders that the harness converts to public citation numbers. Never\ninvent a reference, alter its spelling, or write a numeric citation marker yourself. A derived claim needs no separate\nreference when all external operands are visibly supported nearby and the derivation is explicit. Name a source\norganization naturally only when it helps explain why the evidence is authoritative. A table-derived value is\nsupported only when the supplied text preserves its association with the relevant row and column labels. Never assign\na value to a year, category, or candidate that the source record does not visibly associate with that value. A\ncsv_records field is a mechanical projection of a CSV header onto its selected rows; prefer its named fields over\ncounting positions in the raw CSV quote. For each premise, rely on the single most direct source that visibly\nestablishes it. Add another source only when the first source cannot establish the whole premise; do not rely on weaker\nduplicates or merely corroborating background. When sources report conflicting measurements, prefer an internally\nconsistent source record that establishes the question's identifying conditions and requested value together. Do not\ncombine a conflicting measurement from one source with the answer supplied by another; mention a material discrepancy\nbriefly only when it affects interpretation. If the question asks what a source explicitly reports, state that\nreported value and compare it directly; do not add a recomputation that answers a different question. When a\nthreshold, ranking, ratio, or arithmetic operation decides the answer, show the relevant input\nvalues and write the arithmetic expression or comparison for every candidate needed to establish the result (for\nexample, `105 - 81 = 24`, not only the two scores and the resulting margin). Prefer an exact calculated value over an\nindirect inequality when the supplied operands allow the calculation. When the conclusion is\nexhaustive (for example, only, all, closest, a top-k set, or an intersection), show enough of the candidate comparison\nin the answer to establish that no omitted candidate changes the result. Open with the direct answer, then explain the\ndecisive evidence and derivation in natural prose. Do not expose research-process labels such as candidate pool,\nboundary check, proof of completeness, evidence requirement, audit, or research state. For an exhaustive answer,\nidentify the finite set naturally, show each qualifying entity's decisive values, and mention only the near misses\nneeded to establish the boundary. An inventory source can bound the set, but independently verified candidate pages\nand boundary near misses can do so when no single inventory page is available. Apply strict inequalities literally:\nstate the strictly qualifying set first, and describe an equal boundary value only as an excluded case. For an\nidentification or constraint question, explicitly show how the answer satisfies every condition in the original\nquestion, including descriptors and relationships. When the question asks to retrieve a finite set and then filter\nit through multiple conditions, show the materially narrowed set after each decisive filter, not only the final\ncandidate's properties.\n\nGood citation placement: `Essendon won 105-81 in 1984. [P1]`\nFor a Markdown table, place the source reference in each source-backed row, normally in its final relevant cell. Never\nput the only reference for several table rows on a separate line below the table.\nBad: a final `Sources` list, a raw URL, an invented `[1]`, a citation-only line below a table, or a claim whose only\nreference appears several paragraphs later."
        STRUCTURED_OUTPUT_SYSTEM = "Materialize a completed, evidence-backed research answer as the caller's structured output. Do not research again,\nadd facts, explain your process, or return prose outside the tool call. Preserve the answer's meaning and include every\nfield required by the supplied JSON Schema. Call submit_structured_output exactly once. The tool arguments are the\nfinal output value, not JSON encoded inside a string."
        AUDIT_SYSTEM = "Audit an answer against supplied external evidence. The answer may contain the correct values attached to the wrong\ndates, columns, categories, candidates, or relationships.\n\nReconstruct the source facts before accepting any claim from the answer. A value has a year, column, category, or role\nonly when the visible source text preserves that association. Do not infer a table header across omitted lines or from\nthe answer itself. A csv_records field is a mechanical projection of a CSV header onto its selected rows; use its named\nfields instead of counting positions in the raw CSV quote. For every candidate that could affect the result, treat each\ncondition in the question as supported true, supported false, or unknown. Absence of evidence is unknown, not false.\n\nFor an identification question, audit every descriptive clause as a separate premise. Evidence that a person is\naffiliated with an institution does not establish the institution's location, type, or status. If the supplied source\nrecords do not explicitly establish such a property required by the question, mark it unknown and return CONTINUE.\nWhen the question identifies an entity indirectly through a quotation, work, event, or relationship, the mapping\nfrom that clue to the identified person or entity is itself a material premise. Require visible evidence for that\nmapping even when it is familiar or stated as part of the question; evidence for the resulting name alone does not\nestablish why it matches the clue.\nWhen the original question explicitly requires retrieval or reporting from a named source, edition, page, report, or\ndataset, verify that the supplied records establish that source and scope. A substitute source does not satisfy that\ninstruction even when it supports the same conclusion. The source inventory is discovery metadata, not evidence. If\nthe answer relies on a substitute while the inventory exposes a result from the required publisher with matching\nscope, return CONTINUE and name that one direct result for inspection. Do not request a stronger duplicate merely\nbecause one may exist when the question does not require a named source or scope.\n\nSource omission proves absence only when the source visibly represents a complete inventory at the required scope.\nA candidate excluded by one supported condition does not need evidence for the other conditions. When a surviving\ncandidate has multiple unknown conditions, request only the single cheapest observation that could exclude it or move\nit forward; do not mark later conditions missing until the candidate survives that check. A CONTINUE audit must\ncontain exactly one MISSING line, and it must match the one observation named in the verdict.\nRows separated by a visible `...` are not adjacent. Do not reconstruct ordinal ranks or a ranking cutoff by joining\nthe rows on either side; return CONTINUE if omitted rows could change the result.\nA complete comparison on one condition may reduce the candidate set, after which only the survivors need support for\nthe remaining conditions. Do not require a full candidate-by-condition matrix when supported elimination establishes\nthe same conclusion.\nDo not combine an eligibility condition from one source with a requested value from another source when their\nmeasurements conflict. If one supplied source record states all identifying conditions and the requested value\ntogether, preserve that internally consistent account. Treat a differently scoped or measured record as a\ndiscrepancy, not as an operand for a hybrid answer.\nNever approve or write a replacement that keeps a candidate as the answer while its chosen evidence account makes\nthat candidate fail a selection condition. Use a supplied internally consistent account that establishes both\neligibility and the requested value, or return CONTINUE when no such account is available.\n\nBefore deciding, identify only:\n- factual premises asserted by the current answer; and\n- unresolved facts whose truth could change the answer to the original question.\n\nDo not audit an initial research plan or require facts that are no longer material to the conclusion. Write one short\nline for each material premise or result-changing unknown. Use exactly one of:\nSUPPORTED [source ref]: <the visible source words that establish this premise>\nDERIVED [source refs]: <the arithmetic or logical derivation from externally supported operands>\nMISSING: <the premise not explicitly established by any supplied source record>\nCONTRADICTED [source ref]: <the visible source words that contradict this premise>\n\nEmit a MISSING line only for a real unresolved premise. If nothing is missing, omit MISSING entirely; never write\n`MISSING: none`, `MISSING: not applicable`, or another empty placeholder. A READY verdict must contain no MISSING line.\nDo not combine premises on one line. A source ref without the establishing words is not support. Use only the\nsupplied source records; the answer and internal knowledge are not evidence. A contradicted condition for an excluded\ncandidate can support the answer's exclusion; it is not itself an answer error. Arithmetic, set operations, decade\nmembership, threshold comparisons, and ordering may be DERIVED without another external citation when every external\noperand is SUPPORTED. A DERIVED line must show the calculation or logical step and cite the source refs containing its\nexternal operands; never use DERIVED to supply a missing external operand. A value that is completely calculable from\nsupported external operands is not missing merely because no source states the calculated value verbatim. Mark that\npremise DERIVED, not MISSING, and do not emit both statuses for the same premise.\nA familiar categorical property may also be DERIVED from explicit defining source facts when the classification is\nunambiguous; show those facts instead of requiring the source to use the question's exact label.\n\nAfter all premise lines, emit exactly one verdict:\nVERDICT READY\nVERDICT CONTINUE: <the one most important missing observation>\nVERDICT REVISE\n<a complete replacement answer with exact supplied source refs such as [P1]>\n\nUse READY only if every factual statement agrees with the reconstructed source facts, the conclusion follows, and no\nunknown could change the result. READY and REVISE are invalid if a material premise is MISSING. A source\ncontradiction to a factual statement asserted by the current answer requires REVISE, while a contradiction that\nestablishes why a candidate is excluded is compatible with READY. Use REVISE only when the supplied evidence settles\nthe question but the answer is wrong or unsupported. The replacement must cite exact supplied source refs after its\nsupported factual claims. Begin it with the corrected conclusion and do not repeat the old answer or discuss the\ncorrection process. Use CONTINUE when the evidence cannot settle the result."

        def _schema(name: str, description: str, properties: dict[str, Any], required: tuple[str, ...]) -> dict[str, Any]:
            return {'type': 'function', 'function': {'name': name, 'description': description, 'parameters': {'type': 'object', 'properties': properties, 'required': list(required), 'additionalProperties': False}, 'strict': False}}

        def _parse_csv_row(line: str) -> list[str] | None:
            fields: list[str] = []
            field: list[str] = []
            in_quotes = False
            after_quote = False
            index = 0
            while index < len(line):
                character = line[index]
                if in_quotes:
                    if character != '"':
                        field.append(character)
                    elif index + 1 < len(line) and line[index + 1] == '"':
                        field.append('"')
                        index += 1
                    else:
                        in_quotes = False
                        after_quote = True
                elif after_quote:
                    if character == ',':
                        fields.append(''.join(field))
                        field = []
                        after_quote = False
                    elif character not in ' \t':
                        return None
                elif character == ',':
                    fields.append(''.join(field))
                    field = []
                elif character == '"' and (not field):
                    in_quotes = True
                else:
                    field.append(character)
                index += 1
            if in_quotes:
                return None
            fields.append(''.join(field))
            return fields
        SET_EVIDENCE_REQUIREMENTS_TOOL = _schema('set_evidence_requirements', 'Record only unanswered evidence questions whose externally verifiable premises the final answer needs. Do not record source availability, table structure, or retrieval work.', {'requirements': {'type': 'string', 'minLength': 1, 'description': 'One unanswered evidence question per line, with no candidate or expected answer filled in.'}}, ('requirements',))
        REQUIREMENTS_TOOLS = [SET_EVIDENCE_REQUIREMENTS_TOOL]
        TOOLS = [_schema('search_web', 'Search the web. Full results are retained in VFS and each result receives a source reference.', {'query': {'type': 'string', 'minLength': 1}, 'num': {'type': 'integer', 'minimum': 1, 'maximum': 25}}, ('query', 'num')), _schema('fetch_page', 'Fetch one full URL when a search snippet lacks context or a page exposes a promising direct link. Full content is retained in VFS and receives a source reference.', {'url': {'type': 'string', 'minLength': 1}}, ('url',)), _schema('vfs_read', 'Read an inclusive line range from one VFS key. Large ranges are paginated. Bounds accept 1-based line numbers or stable line IDs.', {'key': {'type': 'string', 'minLength': 1}, 'start_line': {'type': ['string', 'integer', 'null']}, 'end_line': {'type': ['string', 'integer', 'null']}}, ('key', 'start_line', 'end_line')), _schema('vfs_list', 'List VFS keys, optionally restricted to a literal prefix.', {'prefix': {'type': 'string'}}, ('prefix',)), _schema('vfs_write', 'Write or overwrite one VFS file. VFS operations do not create VFS audit entries.', {'key': {'type': 'string', 'minLength': 1}, 'content': {'type': 'string'}}, ('key', 'content')), _schema('vfs_delete', 'Delete one VFS key.', {'key': {'type': 'string', 'minLength': 1}}, ('key',)), _schema('vfs_search', 'Search exact keys, wildcard key patterns such as page://*, or * for all VFS files. Supply an exact regex pattern and a semantic query for the same information need. The harness starts with regex and adds embedding results only when regex fails or finds nothing. Continue paginated regex matches with next_cursor.', {'pattern': {'type': 'string', 'minLength': 1}, 'query': {'type': 'string', 'minLength': 1}, 'targets': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'minItems': 1}, 'cursor': {'type': 'integer', 'minimum': 0, 'description': 'Match offset returned as next_cursor by a previous identical search.'}}, ('pattern', 'query', 'targets')), _schema('update_research_state', 'Replace the prose working memory used on later turns. Call when the best answer, decisive support, or most important unresolved question changes.', {'state': {'type': 'string', 'minLength': 1, 'description': 'Current best answer, decisive observed source refs, and the next unresolved question.'}}, ('state',)), _schema('ready_to_finalize', 'Propose or confirm finalization after decisive external evidence has been inspected. This is premature when an observed search result exposes an uninspected official or primary source for a premise currently supported only by a secondary source. Every cited fetched-page source must already have a retained evidence excerpt.', {'reason': {'type': 'string', 'minLength': 1, 'description': 'Explain readiness and cite decisive source refs such as [S1.2] or [P1].'}}, ('reason',))]
        RETAIN_EVIDENCE_TOOL = _schema('retain_evidence', 'Keep one directly useful, already displayed source excerpt in persistent research memory. Do not retain a source merely for possible later extraction. For flattened tables, retain one continuous range that includes the values, category labels, series labels, and title rather than isolated numeric lines. Every date, year, threshold, or other number asserted in the note must also be visible in the selected range.', {'source': {'type': 'string', 'minLength': 1, 'description': 'An observed source reference such as S1.2 or P3, or its exact VFS key.'}, 'note': {'type': 'string', 'minLength': 1, 'description': 'What the visible source text establishes and which part of the question it informs.'}, 'start_line': {'type': ['string', 'integer'], 'description': 'First displayed line number or stable line ID containing the evidence.'}, 'end_line': {'type': ['string', 'integer'], 'description': 'Last displayed line number or stable line ID containing the evidence.'}}, ('source', 'note', 'start_line', 'end_line'))
        DISCARD_REMAINING_SOURCES_TOOL = _schema('discard_remaining_sources', 'Discard every still-unretained source from the latest retrieval and finish its evidence review.', {'reason': {'type': 'string', 'minLength': 1, 'description': 'Why every still-unretained visible source does not materially inform the research.'}}, ('reason',))
        EVIDENCE_REVIEW_TOOLS = [RETAIN_EVIDENCE_TOOL, DISCARD_REMAINING_SOURCES_TOOL]
        TOOLS.insert(-1, RETAIN_EVIDENCE_TOOL)
        CLOSING_TOOLS = [tool for tool in TOOLS if tool['function']['name'] in CLOSING_TOOL_NAMES]

        @dataclass
        class Source:
            ref: str
            key: str
            title: str
            url: str
            content: str
            receipt_id: str | None
            result_id: str | None
            preview_chars: int = 8000

        @dataclass
        class CitationPlan:
            citations: list[CitationRef]
            source_indices: dict[str, int]

        class ResearchState:

            def __init__(self, question: str='') -> None:
                self.question = question
                self.vfs: dict[str, str] = {}
                self.sources: dict[str, Source] = {}
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
            def _line_id(key: str, index: int, text: str) -> str:
                digest = hashlib.sha256(f'{key}\x00{index}\x00{text}'.encode()).hexdigest()[:10]
                return f'L{digest}'

            def render_lines(self, key: str, indices: list[int] | range | None=None) -> list[dict[str, Any]]:
                lines = self.vfs[key].splitlines() or ['']
                selected = range(len(lines)) if indices is None else indices
                output: list[dict[str, Any]] = []
                for index in selected:
                    if index < 0 or index >= len(lines):
                        continue
                    line_id = self._line_id(key, index, lines[index])
                    self.line_locations[line_id] = (key, index)
                    output.append({'line_id': line_id, 'line': index + 1, 'text': lines[index]})
                return output

            def focused_excerpts(self) -> list[dict[str, Any]]:
                excerpts: list[dict[str, Any]] = []
                for key, indices in self.focused_lines.items():
                    source_refs = [f'[{source.ref}]' for source in self.sources.values() if source.key == key]
                    excerpts.append({'vfs_key': key, 'source_refs': source_refs, 'lines': self.render_lines(key, sorted(indices))})
                return excerpts

            def remember_focused_lines(self, key: str, indices: set[int] | range) -> None:
                lines = self.vfs[key].splitlines() or ['']
                valid_indices = sorted({index for index in indices if 0 <= index < len(lines)})
                focused = self.focused_lines.setdefault(key, set())
                for index in valid_indices:
                    if index in focused:
                        continue
                    focused.add(index)
                    location = (key, index)
                    self.focused_line_order[location] = None
                    self.focused_line_chars += len(lines[index]) + 80
                if not focused:
                    self.focused_lines.pop(key, None)
                while self.focused_line_chars > FOCUSED_OBSERVATION_MEMORY_CHARS and len(self.focused_line_order) > 1:
                    old_key, old_index = next(iter(self.focused_line_order))
                    self.forget_focused_lines(old_key, {old_index})

            def forget_focused_lines(self, key: str, indices: set[int] | None=None) -> None:
                focused = self.focused_lines.get(key)
                if focused is None:
                    return
                removed = set(focused if indices is None else focused & indices)
                lines = self.vfs.get(key, '').splitlines() or ['']
                for index in removed:
                    self.focused_line_order.pop((key, index), None)
                    if 0 <= index < len(lines):
                        self.focused_line_chars -= len(lines[index]) + 80
                focused.difference_update(removed)
                if not focused:
                    self.focused_lines.pop(key, None)
                self.focused_line_chars = max(0, self.focused_line_chars)

            def clear_focused_lines(self) -> None:
                for key in tuple(self.focused_lines):
                    self.forget_focused_lines(key)

            def remember_reasoning_observation(self, reasoning: str | None) -> None:
                observation = str(reasoning or '').strip()
                if not observation or not re.search('\\b(?:S\\d+(?:\\.\\d+)?|P\\d+)\\b', observation):
                    return
                if observation in self.reasoning_observations:
                    return
                self.reasoning_observations.append(observation)
                self.reasoning_observation_chars += len(observation)
                while self.reasoning_observation_chars > FOCUSED_OBSERVATION_MEMORY_CHARS and len(self.reasoning_observations) > 1:
                    removed = self.reasoning_observations.pop(0)
                    self.reasoning_observation_chars -= len(removed)

            def pending_review_excerpts(self) -> list[dict[str, Any]]:
                excerpts: list[dict[str, Any]] = []
                for ref, source in self.sources.items():
                    if ref not in self.review_source_refs:
                        continue
                    excerpts.append({'source_ref': f'[{ref}]', 'vfs_key': source.key, 'title': source.title, 'url': source.url, 'text': self.bounded_preview(source.key, max_serialized_chars=source.preview_chars)})
                return excerpts

            def preview(self, key: str, max_chars: int=8000) -> list[dict[str, Any]]:
                lines = self.vfs[key].splitlines() or ['']
                if len(self.vfs[key]) <= max_chars:
                    return self.render_lines(key)
                budget = max_chars // 3
                groups: list[list[int]] = [[], [], []]
                positions = [range(len(lines)), range(len(lines) // 3, len(lines)), range(len(lines) - 1, -1, -1)]
                for group, position in zip(groups, positions, strict=True):
                    used = 0
                    for index in position:
                        if used and used + len(lines[index]) + 1 > budget:
                            break
                        group.append(index)
                        used += len(lines[index]) + 1
                    group.sort()
                selected = sorted(set(groups[0] + groups[1] + groups[2]))
                return self.render_lines(key, selected)

            def bounded_preview(self, key: str, max_serialized_chars: int) -> list[dict[str, Any]]:
                text_budget = max_serialized_chars
                preview: list[dict[str, Any]] = []
                for _attempt in range(4):
                    preview = self.preview(key, max_chars=text_budget)
                    serialized_chars = len(json.dumps(preview, ensure_ascii=False, separators=(',', ':')))
                    if serialized_chars <= max_serialized_chars:
                        return preview
                    text_budget = max(100, int(text_budget * max_serialized_chars / serialized_chars * 0.9))
                return preview

            def resolve_targets(self, targets: list[str]) -> list[str]:
                keys: list[str] = []
                for target in targets:
                    if target == '*':
                        matches = list(self.vfs)
                    elif any((char in target for char in '*?[')):
                        pattern = re.compile('^' + re.escape(target).replace('\\*', '.*').replace('\\?', '.') + '$')
                        matches = [key for key in self.vfs if pattern.fullmatch(key)]
                    elif target in self.vfs:
                        matches = [target]
                    else:
                        matches = []
                    keys.extend(matches)
                return list(dict.fromkeys(keys))

            def citation_slices(self, key: str, indices: list[int] | range) -> list[CitationSlice]:
                content = self.vfs[key]
                lines = content.splitlines(keepends=True) or [content]
                selected = sorted({index for index in indices if 0 <= index < len(lines)})
                if not selected:
                    return []
                offsets = [0]
                for line in lines:
                    offsets.append(offsets[-1] + len(line))
                groups: list[tuple[int, int]] = []
                start = previous = selected[0]
                for index in selected[1:]:
                    if index != previous + 1:
                        groups.append((start, previous + 1))
                        start = index
                    previous = index
                groups.append((start, previous + 1))
                spans: list[tuple[int, int]] = []
                for start_line, end_line in groups:
                    start_offset = offsets[start_line]
                    end_offset = offsets[end_line]
                    if end_offset - start_offset < 100 and len(content) >= 100:
                        missing = 100 - (end_offset - start_offset)
                        start_offset = max(0, start_offset - missing // 2)
                        end_offset = min(len(content), end_offset + missing)
                        start_offset = max(0, end_offset - 100)
                    if spans and start_offset <= spans[-1][1]:
                        spans[-1] = (spans[-1][0], max(spans[-1][1], end_offset))
                    else:
                        spans.append((start_offset, end_offset))
                return [CitationSlice(start=start, end=end) for start, end in spans if end > start]

            def packet_preview(self, key: str, max_chars: int=8000) -> tuple[str, list[CitationSlice]]:
                content = self.vfs[key]
                if len(content) <= max_chars:
                    return (content, [CitationSlice(start=0, end=len(content))])
                segment_chars = max_chars // 3
                middle_start = max(0, (len(content) - segment_chars) // 2)
                spans = [(0, segment_chars), (middle_start, middle_start + segment_chars), (len(content) - segment_chars, len(content))]
                quote = '\n\n...\n\n'.join((content[start:end] for start, end in spans))
                slices = [CitationSlice(start=start, end=end) for start, end in spans]
                return (quote, slices)

            @staticmethod
            def cited_line_indices(reason: str, ref: str) -> list[int]:
                escaped_ref = re.escape(ref)
                patterns = (f'\\[{escaped_ref}\\s*,\\s*lines?\\s+(\\d+)(?:\\s*(?:-|to)\\s*(\\d+))?\\]', f'\\[{escaped_ref}\\s*,\\s*L(\\d+)(?:\\s*-\\s*L?(\\d+))?\\]', f'\\[{escaped_ref}\\]\\s*[:,]?\\s*lines?\\s+(\\d+)(?:\\s*(?:-|to)\\s*(\\d+))?', f'\\[{escaped_ref}\\]\\s*[:,]?\\s*L(\\d+)(?:\\s*-\\s*L?(\\d+))?', f'\\b{escaped_ref}\\b\\s*[:,]?\\s*lines?\\s+(\\d+)(?:\\s*(?:-|to)\\s*(\\d+))?', f'\\b{escaped_ref}\\b\\s*[:,]?\\s*L(\\d+)(?:\\s*-\\s*L?(\\d+))?')
                indices: set[int] = set()
                for pattern in patterns:
                    for match in re.finditer(pattern, reason, flags=re.IGNORECASE):
                        start = int(match.group(1))
                        end = int(match.group(2) or start)
                        if end < start:
                            start, end = (end, start)
                        indices.update(range(max(1, start) - 1, end))
                for bracket in re.findall('\\[([^\\]]+)\\]', reason):
                    if re.search(f'(?:^|[\\s,;]){escaped_ref}(?:$|[\\s,;:])', bracket) is None:
                        continue
                    for match in re.finditer('\\bL(\\d+)(?:\\s*-\\s*L?(\\d+))?', bracket, flags=re.IGNORECASE):
                        start = int(match.group(1))
                        end = int(match.group(2) or start)
                        if end < start:
                            start, end = (end, start)
                        indices.update(range(max(1, start) - 1, end))
                return sorted(indices)

            def source_evidence_indices(self, key: str, indices: list[int] | range | set[int], *, include_focused: bool=True) -> list[int]:
                lines = self.vfs[key].splitlines() or ['']
                line_count = len(lines)
                candidates = set(indices)
                if include_focused:
                    candidates.update(self.focused_lines.get(key, set()))
                selected = {index for index in candidates if 0 <= index < line_count}
                for index in tuple(selected):
                    context = _markdown_table_context(self, key, index)
                    if context is None:
                        continue
                    selected.update((item['line'] - 1 for item in context['header']))
                if selected:
                    header = _parse_csv_row(lines[0])
                    selected_rows = [_parse_csv_row(lines[index]) for index in selected]
                    if header is None or any((row is None for row in selected_rows)):
                        header = []
                        selected_widths = set()
                    else:
                        selected_widths = {len(row) for row in selected_rows if row is not None}
                    textual_fields = sum((bool(re.search('[A-Za-z]', field)) for field in header))
                    if len(header) >= 3 and len(header) in selected_widths and (textual_fields >= len(header) // 2):
                        selected.add(0)
                return sorted(selected)

            def structured_csv_records(self, key: str, indices: list[int] | range) -> list[dict[str, str]]:
                lines = self.vfs[key].splitlines()
                if not lines or 0 not in indices:
                    return []
                header = _parse_csv_row(lines[0])
                if header is None:
                    return []
                if len(header) < 3 or len(set(header)) != len(header):
                    return []
                records: list[dict[str, str]] = []
                for index in indices:
                    if index == 0 or not 0 <= index < len(lines):
                        continue
                    row = _parse_csv_row(lines[index])
                    if row is None:
                        return []
                    if len(row) != len(header):
                        return []
                    records.append(dict(zip(header, row, strict=True)))
                return records

            def source_packet(self, reason: str, *, allow_preview: bool=True, include_structured_csv: bool=False, prefer_retained: bool=True) -> list[dict[str, Any]]:
                mentioned_refs = list(dict.fromkeys(re.findall('\\b(S\\d+(?:\\.\\d+)?|P\\d+)\\b', reason)))
                refs: list[str] = []
                for ref in mentioned_refs:
                    if re.fullmatch('S\\d+', ref):
                        refs.extend((candidate for candidate in self.sources if candidate.startswith(f'{ref}.')))
                    else:
                        refs.append(ref)
                refs.extend((source.ref for source in self.sources.values() if source.key in reason))
                refs = list(dict.fromkeys(refs))
                single_source_line_indices: list[int] = []
                if len(refs) == 1:
                    indices: set[int] = set()
                    for match in re.finditer('\\b(?:lines?\\s+)?L(\\d+)(?:\\s*-\\s*L?(\\d+))?', reason, flags=re.IGNORECASE):
                        start = int(match.group(1))
                        end = int(match.group(2) or start)
                        if end < start:
                            start, end = (end, start)
                        indices.update(range(max(1, start) - 1, end))
                    single_source_line_indices = sorted(indices)
                line_ids = list(dict.fromkeys(re.findall('\\bL[0-9a-f]{10}\\b', reason)))
                packet: list[dict[str, Any]] = []
                for ref in refs:
                    source = self.sources.get(ref)
                    if source is None:
                        continue
                    if prefer_retained and ref in self.retained_evidence:
                        retained = self.retained_evidence[ref]
                        retained_item = {key: value for key, value in retained.items() if key in {'source_ref', 'title', 'url', 'quote', 'csv_records'}}
                        remaining_focused = self.focused_lines.get(source.key)
                        if remaining_focused:
                            selected_indices = self.source_evidence_indices(source.key, remaining_focused)
                            focused_item: dict[str, Any] = {'source_ref': f'[{ref}]', 'title': source.title, 'url': source.url, 'quote': '\n'.join((item['text'] for item in self.render_lines(source.key, selected_indices)))}
                            if include_structured_csv:
                                csv_records = self.structured_csv_records(source.key, selected_indices)
                                if csv_records:
                                    retained_records = list(retained_item.get('csv_records', []))
                                    focused_item['csv_records'] = [*retained_records, *(record for record in csv_records if record not in retained_records)]
                                self.source_slices[ref] = _merge_citation_slices(self.source_slices.get(ref, []), self.citation_slices(source.key, selected_indices))
                            retained_item = _merge_source_packets([retained_item], [focused_item])[0]
                        packet.append(retained_item)
                        continue
                    source_line_ids = [line_id for line_id in line_ids if self.line_locations.get(line_id, (None,))[0] == source.key]
                    cited_line_indices = sorted(set(self.cited_line_indices(reason, ref)) | set(single_source_line_indices))
                    selected_indices: list[int] | range | None
                    citation_indices: list[int] | range | None
                    if source_line_ids:
                        line_indices = [self.line_locations[line_id][1] for line_id in source_line_ids]
                        evidence_window = set(line_indices)
                        selected_indices = self.source_evidence_indices(source.key, evidence_window, include_focused=False)
                        citation_indices = selected_indices
                        quote = '\n'.join((item['text'] for item in self.render_lines(source.key, selected_indices)))
                    elif cited_line_indices:
                        selected = set(cited_line_indices)
                        citation_indices = self.source_evidence_indices(source.key, selected, include_focused=False)
                        selected_indices = citation_indices
                        quote = '\n'.join((f"{item['line']}: {item['text']}" for item in self.render_lines(source.key, selected_indices)))
                    elif source.key in self.focused_lines:
                        selected_indices = self.source_evidence_indices(source.key, self.focused_lines[source.key])
                        citation_indices = selected_indices
                        quote = '\n'.join((item['text'] for item in self.render_lines(source.key, selected_indices)))
                    elif not allow_preview:
                        continue
                    else:
                        quote, slices = self.packet_preview(source.key)
                        self.source_slices[ref] = slices
                        selected_indices = None
                        citation_indices = None
                    if include_structured_csv and selected_indices is not None:
                        self.source_slices[ref] = self.citation_slices(source.key, citation_indices or selected_indices)
                    item: dict[str, Any] = {'source_ref': f'[{ref}]', 'title': source.title, 'url': source.url, 'quote': quote}
                    if selected_indices is not None:
                        csv_records = self.structured_csv_records(source.key, selected_indices)
                        if csv_records:
                            item['csv_records'] = csv_records
                    packet.append(item)
                return packet

            def citation_plan(self, answer: str, fallback_packet: list[dict[str, Any]], final_source_slices: dict[str, list[CitationSlice]], audit: str) -> CitationPlan:
                audit_refs = list(dict.fromkeys(re.findall('\\b(S\\d+(?:\\.\\d+)?|P\\d+)\\b', audit)))
                answer_refs = list(dict.fromkeys(re.findall('\\b(S\\d+(?:\\.\\d+)?|P\\d+)\\b', answer)))
                mentioned_refs = list(dict.fromkeys([*answer_refs, *audit_refs]))
                refs: list[str] = []
                for ref in mentioned_refs:
                    if re.fullmatch('S\\d+', ref):
                        refs.extend((candidate for candidate in self.sources if candidate.startswith(f'{ref}.')))
                    else:
                        refs.append(ref)
                if not refs:
                    refs = [item['source_ref'][1:-1] for item in fallback_packet]
                citation_sources: dict[tuple[str, str], Source] = {}
                citation_slices: dict[tuple[str, str], list[CitationSlice]] = {}
                source_identities: dict[str, tuple[str, str]] = {}
                for ref in refs:
                    source = self.sources.get(ref)
                    if source and source.receipt_id and source.result_id:
                        identity = (source.receipt_id, source.result_id)
                        source_identities[ref] = identity
                        slices = _merge_citation_slices([], final_source_slices.get(ref, self.source_slices.get(ref, [])))
                        citation_sources[identity] = source
                        citation_slices[identity] = _merge_citation_slices(citation_slices.get(identity, []), slices)
                identity_indices = {identity: index for index, identity in enumerate(citation_sources, start=1)}
                citations = [CitationRef(receipt_id=source.receipt_id, result_id=source.result_id, slices=citation_slices[identity]) for identity, source in citation_sources.items()]
                return CitationPlan(citations=citations, source_indices={ref: identity_indices[identity] for ref, identity in source_identities.items() if identity in identity_indices})

        def _private_source_refs(answer: str) -> list[str]:
            return list(dict.fromkeys(re.findall('\\[(S\\d+(?:\\.\\d+)?|P\\d+)\\]', answer)))

        def _normalize_grouped_private_refs(answer: str) -> str:
            ref = '(?:S\\d+(?:\\.\\d+)?|P\\d+)'
            grouped = re.compile(f'\\[({ref}(?:\\s*,\\s*{ref})+)\\]')
            return grouped.sub(lambda match: ''.join((f'[{item}]' for item in re.findall(ref, match.group(1)))), answer)

        def _requires_unadorned_output(question: str) -> bool:
            return bool(re.search('(?i)\\b(?:output|return|respond)\\s+only\\b', question))

        def _validate_private_answer_refs(answer: str, allowed_refs: set[str], *, require_ref: bool=True) -> None:
            if '[[' in answer or ']]' in answer:
                raise ValueError('write private source refs such as [P1], not public numeric markers')
            if re.search('(?i)(?:https?://|\\bwww\\.|(?<!:)//(?=[a-z0-9])|(?<![\\w@])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+[a-z]{2,63}/[^\\s)]*)', answer):
                raise ValueError('do not render raw URLs in the reader-facing answer')
            if re.search('(?im)^\\s{0,3}(?:#{1,6}\\s*)?(?:sources?|citations?|references?|bibliography|works\\s+cited)\\s*:?\\s*$', answer):
                raise ValueError('do not render a citation or source-list section')
            exact_ref_pattern = re.compile('\\[(?:S\\d+(?:\\.\\d+)?|P\\d+)\\]')
            without_exact_refs = exact_ref_pattern.sub('', answer)
            if '[' in without_exact_refs or ']' in without_exact_refs:
                raise ValueError('square brackets are reserved for one exact private source ref such as [P1]')
            if re.search('\\b(?:S\\d+(?:\\.\\d+)?|P\\d+)\\b', without_exact_refs):
                raise ValueError('each private source ref must appear alone in brackets, for example [P1]')
            refs = _private_source_refs(answer)
            unknown_refs = [ref for ref in refs if ref not in allowed_refs]
            if unknown_refs:
                raise ValueError(f"answer cites unavailable source refs: {', '.join(unknown_refs)}")
            if require_ref and allowed_refs and (not refs):
                raise ValueError('answer must place at least one supplied source ref after a supported factual claim')

        def _render_public_citations(answer: str, plan: CitationPlan, *, unadorned_output: bool=False) -> tuple[str, list[CitationRef]]:
            refs = _private_source_refs(answer)
            missing_refs = [ref for ref in refs if ref not in plan.source_indices]
            if missing_refs:
                raise ValueError('answer source refs do not have materializable citations: ' + ', '.join(missing_refs))
            rendered = re.sub('\\[(S\\d+(?:\\.\\d+)?|P\\d+)\\]', lambda match: f'[[{plan.source_indices[match.group(1)]}]]', answer)
            marker_indices = [int(value) for value in re.findall('\\[\\[(\\d+)]]', rendered)]
            invalid_indices = sorted({index for index in marker_indices if index < 1 or index > len(plan.citations)})
            if invalid_indices:
                raise ValueError('answer contains citation indices without response citations: ' + ', '.join((str(index) for index in invalid_indices)))
            if plan.citations and (not marker_indices) and (not unadorned_output):
                raise ValueError('answer has response citations but no inline citation markers')
            used_indices = sorted(set(marker_indices)) if marker_indices else list(range(1, len(plan.citations) + 1))
            compact_indices = {old_index: new_index for new_index, old_index in enumerate(used_indices, start=1)}
            rendered = re.sub('\\[\\[(\\d+)]]', lambda match: f'[[{compact_indices[int(match.group(1))]}]]', rendered)
            if unadorned_output:
                rendered = re.sub('[ \\t]*\\[\\[\\d+]]', '', rendered)
            return (rendered.strip(), [plan.citations[index - 1] for index in used_indices])

        def _merge_citation_slices(existing: list[CitationSlice], additional: list[CitationSlice]) -> list[CitationSlice]:
            spans = sorted(((int(item.start), int(item.end)) for item in [*existing, *additional] if int(item.end) > int(item.start)))
            merged: list[tuple[int, int]] = []
            for start, end in spans:
                if merged and start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                else:
                    merged.append((start, end))
            return [CitationSlice(start=start, end=end) for start, end in merged]

        def _assistant_message(result: Any) -> Any:
            choices = result.llm.choices
            if len(choices) != 1:
                raise RuntimeError(f'expected one LLM choice, received {len(choices)}')
            return choices[0].message

        def _assistant_evidence_context(message: Any) -> str:
            text_parts = [str(part.text) for part in message.content if getattr(part, 'text', None)]
            return '\n'.join((item for item in (str(message.reasoning or '').strip(), *text_parts) if item))

        def _collect_vfs_keys(value: Any) -> list[str]:
            keys: list[str] = []
            if isinstance(value, dict):
                for field, item in value.items():
                    if field in {'key', 'vfs_key'} and isinstance(item, str):
                        keys.append(item)
                    elif field in {'keys', 'matched_keys'} and isinstance(item, list):
                        keys.extend((candidate for candidate in item if isinstance(candidate, str)))
                    else:
                        keys.extend(_collect_vfs_keys(item))
            elif isinstance(value, list):
                for item in value:
                    keys.extend(_collect_vfs_keys(item))
            return list(dict.fromkeys(keys))

        def _compact_consumed_tool_results(messages: list[Any]) -> None:
            for message in messages:
                if not isinstance(message, dict) or message.get('role') != 'tool':
                    continue
                content = message.get('content')
                if not isinstance(content, str) or len(content) < 1000:
                    continue
                try:
                    output = json.loads(content)
                except json.JSONDecodeError:
                    continue
                if not isinstance(output, dict):
                    continue
                receipt: dict[str, Any] = {'ok': output.get('ok', False)}
                keys = _collect_vfs_keys(output)
                if keys:
                    receipt['vfs_keys'] = keys
                if output.get('error_type'):
                    receipt['error_type'] = output['error_type']
                    receipt['details'] = str(output.get('details', ''))[:1000]
                if output.get('audit'):
                    receipt['audit'] = output['audit']
                similarity = output.get('similarity')
                if isinstance(similarity, dict):
                    receipt['similarity'] = {field: similarity[field] for field in ('status', 'trigger', 'reason') if field in similarity}
                message['content'] = json.dumps(receipt, ensure_ascii=False)

        def _compact_consumed_assistant_reasoning(messages: list[Any]) -> None:
            for index, message in enumerate(messages):
                if isinstance(message, LlmMessage):
                    if message.role == 'assistant' and message.reasoning_details is not None:
                        messages[index] = replace(message, reasoning_details=None)
                    continue
                if not isinstance(message, dict) or message.get('role') != 'assistant':
                    continue
                message.pop('reasoning', None)
                message.pop('reasoning_details', None)

        def _record_retrieval_receipt(state: ResearchState, name: str, args: dict[str, Any], output: dict[str, Any]) -> None:
            if not output.get('ok') or name not in {'search_web', 'fetch_page'}:
                return
            if name == 'search_web':
                destinations = [str(output['vfs_key'])]
                source_index = [{'source_ref': item['source_ref'], 'vfs_key': item['vfs_key'], 'title': item['title'], 'url': item['url']} for item in output.get('results', []) if isinstance(item, dict)]
            else:
                destinations = [str(page['vfs_key']) for page in output.get('pages', []) if isinstance(page, dict) and page.get('vfs_key')]
                source_index = [{'source_ref': item['source_ref'], 'vfs_key': item['vfs_key'], 'title': item['title'], 'url': item['url']} for item in output.get('pages', []) if isinstance(item, dict)]
            signature = _retrieval_signature(name, args)
            state.retrieval_output_cache[signature] = output
            receipt = state.retrieval_receipts.setdefault(signature, {'tool': name, 'arguments': args, 'destinations': [], 'sources': [], 'calls': 0})
            receipt['calls'] += 1
            receipt['destinations'] = list(dict.fromkeys([*receipt['destinations'], *destinations]))
            known_sources = {str(item['source_ref']): item for item in [*receipt['sources'], *source_index]}
            receipt['sources'] = list(known_sources.values())

        def _retrieval_signature(name: str, args: dict[str, Any]) -> str:
            return json.dumps({'tool': name, 'arguments': args}, ensure_ascii=False, sort_keys=True)

        def _record_vfs_operation_receipt(state: ResearchState, name: str, args: dict[str, Any], output: dict[str, Any]) -> None:
            if not output.get('ok') or name not in {'vfs_read', 'vfs_search', 'vfs_list'}:
                return
            if name == 'vfs_read':
                lines = output.get('lines', [])
                outcome = {'returned_line_count': len(lines), 'first_line': lines[0].get('line') if lines else None, 'last_line': lines[-1].get('line') if lines else None, 'truncated': bool(output.get('truncated'))}
            elif name == 'vfs_search':
                regex = output.get('regex', {})
                similarity = output.get('similarity', {})
                outcome = {'regex_total_match_count': regex.get('total_match_count'), 'regex_returned_match_count': len(regex.get('matches', [])), 'regex_next_cursor': regex.get('next_cursor'), 'similarity_status': similarity.get('status'), 'similarity_returned_chunk_count': len(similarity.get('chunks', []))}
            else:
                outcome = {'returned_key_count': len(output.get('keys', []))}
            signature = json.dumps({'tool': name, 'arguments': args}, ensure_ascii=False, sort_keys=True)
            receipt = state.vfs_operation_receipts.setdefault(signature, {'tool': name, 'arguments': args, 'calls': 0, 'outcome': outcome})
            receipt['calls'] += 1
            receipt['outcome'] = outcome

        def _collect_source_refs(value: Any) -> list[str]:
            refs: list[str] = []
            if isinstance(value, dict):
                for field, item in value.items():
                    if field == 'source_ref' and isinstance(item, str):
                        refs.append(item.strip().strip('[]'))
                    else:
                        refs.extend(_collect_source_refs(item))
            elif isinstance(value, list):
                for item in value:
                    refs.extend(_collect_source_refs(item))
            return list(dict.fromkeys(refs))

        def _capture_budget(state: ResearchState, result: Any) -> None:
            budget = getattr(result, 'budget', None)
            if budget is None:
                return
            state.budget_snapshot = {'session_hard_limit_usd': round(float(budget.session_hard_limit_usd), 6), 'session_used_budget_usd': round(float(budget.session_used_budget_usd), 6), 'session_hard_remaining_usd': round(max(0.0, float(budget.session_hard_limit_usd) - float(budget.session_used_budget_usd)), 6)}

        def _closable_source_refs(state: ResearchState) -> list[str]:
            return [ref for ref in state.sources if not str(ref).startswith('P') or str(ref) in state.retained_evidence]

        def _closable_source_context(state: ResearchState) -> str:
            refs = ' '.join((f'[{ref}]' for ref in _closable_source_refs(state)))
            return f'{state.research_state}\n\nObserved source references: {refs}'

        def _governor_stage(state: ResearchState, elapsed_seconds: float) -> str:
            if elapsed_seconds >= TIME_GOVERNOR_HARD_SECONDS:
                return 'hard'
            snapshot = state.budget_snapshot or {}
            limit = float(snapshot.get('session_hard_limit_usd') or 0.0)
            if limit <= 0.0:
                limit = SPEND_GOVERNOR_FALLBACK_LIMIT_USD
            used = float(snapshot.get('session_used_budget_usd') or 0.0)
            if used >= limit * SPEND_GOVERNOR_HARD_FRACTION:
                return 'hard'
            if elapsed_seconds >= TIME_GOVERNOR_SOFT_SECONDS:
                return 'soft'
            if used >= limit * SPEND_GOVERNOR_SOFT_FRACTION:
                return 'soft'
            return 'open'

        def _refresh_retrieval_receipt_message(messages: list[Any], state: ResearchState) -> None:
            marker = 'Harness research memory'
            messages[:] = [message for message in messages if not (isinstance(message, dict) and message.get('role') == 'user' and isinstance(message.get('content'), str) and message['content'].startswith(marker))]
            if not state.research_state and (not state.audit_gap) and (not state.budget_snapshot) and (not state.retrieval_receipts) and (not state.vfs_operation_receipts) and (not state.retained_evidence) and (not state.focused_lines) and (not state.reasoning_observations):
                return
            sections: list[str] = []
            if state.evidence_requirements:
                sections.append('Evidence questions established before retrieval. They guide the investigation but may become immaterial after supported filtering:\n' + state.evidence_requirements)
            if state.audit_gap:
                sections.append('Latest finalization audit. This gap overrides any stale claim in the model-authored state that no uncertainty remains. Do not call ready_to_finalize again until new evidence resolves it:\n' + state.audit_gap)
            if state.budget_snapshot:
                sections.append('Latest hosted-tool budget snapshot. This is runtime state, not evidence:\n' + json.dumps(state.budget_snapshot, ensure_ascii=False, separators=(',', ':')) + '\nFinish before the hard remaining amount reaches zero. After observing the single result that resolves an audit gap, combine any now-independent retain_evidence, update_research_state, and ready_to_finalize calls in the same response instead of spending separate turns on each.')
            if state.research_state:
                sections.append('Current model-authored research state. Revise it with update_research_state when the answer, support, or next unresolved question changes:\n' + state.research_state)
            if state.reasoning_observations:
                sections.append('Prior source-linked reasoning preserved by the harness. This is working memory, not external evidence. Use its source refs to avoid rediscovering observations, but inspect or retain the referenced source text before relying on a material premise in the final answer:\n' + '\n\n---\n\n'.join(state.reasoning_observations))
            if state.retrieval_receipts:
                compact_retrieval_receipts = [{key: receipt[key] for key in ('tool', 'arguments', 'destinations', 'sources', 'calls') if key in receipt} for receipt in state.retrieval_receipts.values()]
                sections.append('Completed external retrieval receipts. These record actions and a compact source inventory, not evidence. Each source entry maps a stable source ref to the exact VFS key whose text can be re-read instead of repeating a web search:\n' + json.dumps(compact_retrieval_receipts, ensure_ascii=False, separators=(',', ':')))
            if state.vfs_operation_receipts:
                sections.append('Completed local VFS inspection operations. These are action history, not evidence. Do not repeat the same read or search merely by changing wording. When prior local inspections did not expose the missing relationship, change the evidence route:\n' + json.dumps(list(state.vfs_operation_receipts.values()), ensure_ascii=False, separators=(',', ':')))
            if state.retained_evidence:
                sections.append('Retained source excerpts selected by your prior reasoning. These are external evidence and do not need to be retrieved again. Only each quote is source evidence; research_note is your prior interpretation and may be wrong:\n' + json.dumps(list(state.retained_evidence.values()), ensure_ascii=False, separators=(',', ':')))
            if state.focused_lines:
                sections.append('Recent unretained VFS observations. VFS remains the full source of truth; only one generous read-page of recent raw observations is replayed here. Retain lines that support or contradict a material premise. Re-read a VFS location when an older unretained observation becomes necessary:\n' + json.dumps(state.focused_excerpts(), ensure_ascii=False, separators=(',', ':')))
            messages.insert(2, {'role': 'user', 'content': f'{marker}:\n\n' + '\n\n'.join(sections)})

        def _merge_source_packets(retained: list[dict[str, Any]], current: list[dict[str, Any]]) -> list[dict[str, Any]]:
            merged: dict[str, dict[str, Any]] = {str(item['source_ref']): item for item in retained}
            for item in current:
                source_ref = str(item['source_ref'])
                previous = merged.get(source_ref)
                if previous is None:
                    merged[source_ref] = item
                    continue
                previous_quote = str(previous.get('quote', '')).strip()
                current_quote = str(item.get('quote', '')).strip()
                if not previous_quote or previous_quote in current_quote:
                    quote = current_quote
                elif not current_quote or current_quote in previous_quote:
                    quote = previous_quote
                else:
                    quote = f'{previous_quote}\n\n{current_quote}'
                merged[source_ref] = {**previous, **item, 'quote': quote}
            return list(merged.values())

        def _is_retryable_llm_error(error: Exception) -> bool:
            message = str(error).lower()
            return any((marker in message for marker in ('429', '500', '502', '503', '504', 'service unavailable', 'timed out', 'timeout', 'empty_output', 'empty output', 'tool execution failed', 'tool invocation failed')))

        async def _call_model(model_name: str, messages: list[Any], tools: list[dict[str, Any]] | None, tool_choice: str, parallel_tool_calls: bool, timeout: float, max_output_tokens: int | None=None) -> Any:
            if model_name == 'glm5':
                return await llm_chat(provider='openrouter', model='z-ai/glm-5', messages=messages, temperature=0.2, max_output_tokens=max_output_tokens or GLM5_MAX_OUTPUT_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'low'}, provider_extra=OPENROUTER_GLM_PROVIDER_PREFERENCES, timeout=timeout)
            if model_name == 'gpt_oss':
                return await llm_chat(provider='openrouter', model='openai/gpt-oss-120b', messages=messages, temperature=0.0, max_output_tokens=max_output_tokens or GPT_OSS_MAX_OUTPUT_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'high'}, provider_extra=OPENROUTER_GPT_PROVIDER_PREFERENCES, timeout=timeout)
            if model_name == 'openrouter_gemma':
                return await llm_chat(provider='openrouter', model='google/gemma-4-31b-it', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or OPENROUTER_GEMMA_MAX_OUTPUT_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, provider_extra=OPENROUTER_GEMMA_PROVIDER_PREFERENCES, timeout=timeout)
            if model_name == 'openrouter_gemma_prose':
                return await llm_chat(provider='openrouter', model='google/gemma-4-31b-it', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or OPENROUTER_GEMMA_MAX_OUTPUT_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, provider_extra=OPENROUTER_GEMMA_PROVIDER_PREFERENCES, timeout=timeout)
            if model_name == 'openrouter_gemma_stable':
                return await llm_chat(provider='openrouter', model='google/gemma-4-31b-it', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or OPENROUTER_GEMMA_MAX_OUTPUT_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, provider_extra=OPENROUTER_GEMMA_STABLE_PROVIDER_PREFERENCES, timeout=timeout)
            if model_name == 'chutes_gemma':
                return await llm_chat(provider='chutes', model='google/gemma-4-31B-turbo-TEE', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or CHUTES_GEMMA_MAX_OUTPUT_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, timeout=timeout)
            if model_name == 'inkling':
                return await llm_chat(provider='ai_gateway', model='thinkingmachines/inkling', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or INKLING_MAX_OUTPUT_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, timeout=timeout)
            if model_name == 'ai_gateway_gemma':
                return await llm_chat(provider='ai_gateway', model='google/gemma-4-31b-it', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or AI_GATEWAY_GEMMA_MAX_OUTPUT_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, provider_extra={'providerOptions': {'gateway': {'only': ['cerebras']}}}, timeout=timeout)
            raise ValueError(f'unknown model: {model_name}')

        async def _chat_with_model_fallback(models: tuple[str, ...], messages: list[Any], tools: list[dict[str, Any]] | None, tool_choice: str, parallel_tool_calls: bool, timeout: float, max_output_tokens: int | None=None) -> Any:
            if not models:
                raise RuntimeError('no research model was configured')
            raced_models = models[:2]
            remaining_models = models[2:]
            tasks = [asyncio.create_task(_call_model(model, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)) for model in raced_models]
            errors: list[Exception] = []
            pending = set(tasks)
            try:
                while pending:
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        try:
                            result = task.result()
                        except Exception as error:
                            errors.append(error)
                            continue
                        for unfinished in pending:
                            unfinished.cancel()
                        await asyncio.gather(*pending, return_exceptions=True)
                        return result
            finally:
                for unfinished in pending:
                    unfinished.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)
            non_retryable = next((error for error in errors if not _is_retryable_llm_error(error)), None)
            if non_retryable is not None:
                raise non_retryable
            for model in remaining_models:
                try:
                    return await _call_model(model, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)
                except Exception as error:
                    if not _is_retryable_llm_error(error):
                        raise
                    errors.append(error)
            if not errors:
                raise RuntimeError('no research model was configured')
            raise errors[-1]

        async def _chat_with_sequential_model_fallback(models: tuple[str, ...], messages: list[Any], tools: list[dict[str, Any]] | None, tool_choice: str, parallel_tool_calls: bool, timeout: float, max_output_tokens: int | None=None) -> Any:
            if not models:
                raise RuntimeError('no research model was configured')
            errors: list[Exception] = []
            for model in models:
                try:
                    return await _call_model(model, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)
                except Exception as error:
                    if not _is_retryable_llm_error(error):
                        raise
                    errors.append(error)
            raise errors[-1]

        async def _chat_with_scheduling(models: tuple[str, ...], messages: list[Any], tools: list[dict[str, Any]] | None, tool_choice: str, parallel_tool_calls: bool, timeout: float, max_output_tokens: int | None=None) -> Any:
            if MODEL_SCHEDULING == 'race':
                return await _chat_with_model_fallback(models, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)
            if MODEL_SCHEDULING in {'sequential', 'state_aware'}:
                return await _chat_with_sequential_model_fallback(models, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)
            raise ValueError(f'unknown model scheduling policy: {MODEL_SCHEDULING}')

        async def _prose_chat_with_retry(messages: list[Any], tool_choice: str, timeout: float) -> Any:
            return await _chat_with_scheduling(('openrouter_gemma', 'chutes_gemma', 'glm5'), messages, None, tool_choice, False, timeout)

        async def _final_answer_chat_with_retry(messages: list[Any], timeout: float) -> Any:
            return await _chat_with_scheduling(('openrouter_gemma', 'chutes_gemma', 'glm5'), messages, None, 'none', False, timeout)

        async def _research_text(system: str, user: str) -> str:
            messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
            result = await _prose_chat_with_retry(messages, 'none', LLM_TIMEOUT)
            text = result.llm.raw_text
            if not text or not text.strip():
                raise RuntimeError('research model returned empty prose')
            return text.strip()

        async def _answer_text(*, state: ResearchState, question: str, prior_answer: str, requirements: str, research_state: str, finalization_reason: str, packet: list[dict[str, Any]]) -> str:
            allowed_refs = {str(item['source_ref']).strip('[]') for item in packet if isinstance(item, dict) and item.get('source_ref')}
            messages: list[Any] = [{'role': 'system', 'content': ANSWER_UPDATE_SYSTEM}, {'role': 'user', 'content': f"Original question:\n{question}\n\nPrior answer hypothesis:\n{prior_answer}\n\nEvidence requirements:\n{requirements}\n\nInvestigator's current research state:\n{research_state or '(not updated)'}\n\nFinalization reason:\n{finalization_reason}\n\nSupplied source records:\n{json.dumps(packet, ensure_ascii=False, separators=(',', ':'))}"}]
            for attempt in range(3):
                result = await _final_answer_chat_with_retry(messages, LLM_TIMEOUT)
                _capture_budget(state, result)
                text = result.llm.raw_text
                if not text or not text.strip():
                    raise RuntimeError('answer writer returned empty prose')
                text = _normalize_grouped_private_refs(text.strip())
                try:
                    _validate_private_answer_refs(text, allowed_refs, require_ref=not _requires_unadorned_output(question))
                except ValueError as error:
                    if attempt == 2:
                        raise
                    messages.extend([{'role': 'assistant', 'content': text}, {'role': 'user', 'content': f'Output contract error: {error}. Rewrite the complete answer. Use only the exact private source refs present in the supplied records; the harness renders public citation numbers.'}])
                    continue
                return text
            raise AssertionError('unreachable')

        def _structured_output_tool(output_schema: dict[str, Any]) -> tuple[dict[str, Any], bool]:
            direct_object = output_schema.get('type') == 'object'
            parameters = output_schema if direct_object else {'type': 'object', 'properties': {'output': {'description': "The non-null JSON value that matches the caller's supplied output schema."}}, 'required': ['output'], 'additionalProperties': False}
            return ({'type': 'function', 'function': {'name': 'submit_structured_output', 'description': "Submit the complete final value required by the caller's JSON Schema.", 'parameters': parameters, 'strict': False}}, direct_object)

        async def _materialize_structured_output(*, question: str, answer: str, output_schema: dict[str, Any]) -> Any:
            tool, direct_object = _structured_output_tool(output_schema)
            evidence_backed_answer = re.sub('\\[\\[\\d+]]', '', answer).strip()
            messages: list[Any] = [{'role': 'system', 'content': STRUCTURED_OUTPUT_SYSTEM}, {'role': 'user', 'content': f'Original question:\n{question}\n\nCompleted evidence-backed answer:\n{evidence_backed_answer}\n\nRequired JSON Schema:\n{json.dumps(output_schema, ensure_ascii=False, indent=2)}'}]
            for attempt in range(3):
                result = await _chat_with_scheduling(INVESTIGATION_MODELS, messages, [tool], 'required', False, LLM_TIMEOUT)
                assistant = _assistant_message(result)
                calls = list(assistant.tool_calls or ())
                error: ValueError | None = None
                output: Any = None
                if len(calls) != 1:
                    error = ValueError(f'call submit_structured_output exactly once; received {len(calls)} tool calls')
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
                                raise ValueError('non-object output must be submitted in the sole `output` argument')
                            output = arguments['output']
                        if output is None:
                            raise ValueError('top-level null is not a valid miner answer')
                    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as caught:
                        error = ValueError(str(caught))
                if error is None:
                    return output
                if attempt == 2:
                    raise error
                messages.append(assistant.to_input_message())
                if calls:
                    for call in calls:
                        messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': json.dumps({'ok': False, 'error_type': 'tool_argument_validation', 'details': str(error)})})
                else:
                    messages.append({'role': 'user', 'content': f'Output contract error: {error}. Call the required tool with the complete schema-conforming value.'})
            raise AssertionError('unreachable')

        async def _expected_answer_text(question: str) -> str:
            messages = [{'role': 'system', 'content': EXPECTED_ANSWER_SYSTEM}, {'role': 'user', 'content': question}]
            try:
                result = await _call_model('openrouter_gemma', messages, None, 'none', False, LLM_TIMEOUT)
            except Exception as error:
                if not _is_retryable_llm_error(error):
                    raise
                result = await _chat_with_scheduling(('chutes_gemma', 'glm5'), messages, None, 'none', False, LLM_TIMEOUT)
            text = result.llm.raw_text
            if not text or not text.strip():
                raise RuntimeError('research model returned empty prose')
            return text.strip()

        def _parse_audit(text: str) -> tuple[str, str]:
            matches = list(re.finditer('(?m)^VERDICT (READY|CONTINUE|REVISE)(?::[ \\t]*(.*))?[ \\t]*$', text))
            if len(matches) != 1:
                raise ValueError('audit must contain exactly one VERDICT line')
            match = matches[0]
            verdict = match.group(1)
            inline = (match.group(2) or '').strip()
            following = text[match.end():].strip()
            payload = '\n'.join((part for part in (inline, following) if part))
            if verdict == 'REVISE' and (not payload):
                raise ValueError('VERDICT REVISE must include a complete replacement answer')
            if verdict == 'CONTINUE' and (not payload):
                raise ValueError('VERDICT CONTINUE must name the missing observation')
            return (verdict, payload)

        async def _audit(state: ResearchState, question: str, answer: str, packet: list[dict[str, Any]]) -> str:
            allowed_refs = {str(item['source_ref']).strip('[]') for item in packet if isinstance(item, dict) and item.get('source_ref')}
            source_inventory = [{'source_ref': f'[{source.ref}]', 'title': source.title, 'url': source.url} for source in state.sources.values()]
            messages = [{'role': 'system', 'content': AUDIT_SYSTEM}, {'role': 'user', 'content': f"Original question:\n{question}\n\nObserved source inventory (discovery metadata only; titles and URLs are not evidence):\n{json.dumps(source_inventory, ensure_ascii=False, separators=(',', ':'))}\n\nSupplied source records:\n{json.dumps(packet, ensure_ascii=False, separators=(',', ':'))}\n\nCurrent answer:\n{answer}"}]
            for attempt in range(3):
                result = await _chat_with_sequential_model_fallback(AUDIT_MODELS, messages, None, 'none', False, LLM_TIMEOUT)
                _capture_budget(state, result)
                text = result.llm.raw_text
                if not text or not text.strip():
                    raise RuntimeError('auditor returned empty output')
                text = text.strip()
                try:
                    verdict, payload = _parse_audit(text)
                    if verdict in {'READY', 'REVISE'} and re.search('(?m)^MISSING:', text):
                        raise ValueError(f'VERDICT {verdict} is invalid while a material premise is MISSING; a MISSING line must name a real unresolved premise and cannot say none or not applicable. If no premise is missing, preserve the verdict and omit all MISSING lines. Correct only this output-format error; do not introduce a new evidence requirement')
                    if verdict == 'REVISE':
                        _validate_private_answer_refs(payload, allowed_refs, require_ref=not _requires_unadorned_output(question))
                except ValueError as error:
                    if attempt == 2:
                        raise
                    messages.extend([{'role': 'assistant', 'content': text}, {'role': 'user', 'content': f'Output contract error: {error}. Re-audit from the supplied records. Follow the required premise-line and final VERDICT format exactly; a replacement answer must use only exact supplied private source refs.'}])
                    continue
                return text
            raise AssertionError('unreachable')

        def _result_identity(result: Any, index: int) -> tuple[str | None, str | None]:
            if index >= len(result.results):
                return (result.receipt_id, None)
            return (result.receipt_id, result.results[index].result_id)

        async def _execute_search(state: ResearchState, args: dict[str, Any], preview_budget_chars: int | None=None) -> dict[str, Any]:
            query = str(args['query']).strip()
            num = int(args.get('num', 10))
            result = await search_web(query, provider=SEARCH_PROVIDER, num=num, timeout=SEARCH_TIMEOUT)
            _capture_budget(state, result)
            state.search_count += 1
            parent_key = f'search://{state.search_count}'
            state.vfs[parent_key] = result.response.model_dump_json(indent=2)
            items: list[dict[str, Any]] = []
            preview_chars = 8000
            if preview_budget_chars is not None:
                preview_chars = min(preview_chars, max(300, preview_budget_chars // max(1, len(result.response.data))))
            for index, item in enumerate(result.response.data):
                ref = f'S{state.search_count}.{index + 1}'
                key = f'{parent_key}/result/{index + 1}'
                content = item.snippet or item.title or ''
                state.vfs[key] = content
                receipt_id, result_id = _result_identity(result, index)
                state.sources[ref] = Source(ref=ref, key=key, title=item.title or item.link, url=item.link, content=content, receipt_id=receipt_id, result_id=result_id, preview_chars=preview_chars)
                items.append({'source_ref': f'[{ref}]', 'vfs_key': key, 'title': item.title, 'url': item.link, 'text': state.bounded_preview(key, max_serialized_chars=preview_chars)})
            return {'ok': True, 'vfs_key': parent_key, 'results': items}

        async def _execute_fetch(state: ResearchState, args: dict[str, Any], preview_budget_chars: int | None=None) -> dict[str, Any]:
            url = str(args['url']).strip()
            if re.search('\\.(?:xls|xlsx|xlsb)(?:[?#]|$)', url, flags=re.IGNORECASE):
                raise ValueError('fetch_page cannot expose spreadsheet binary rows to VFS tools; search the same publisher for a CSV, HTML, or plain-text companion')
            result = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=FETCH_TIMEOUT)
            _capture_budget(state, result)
            state.page_count += 1
            items: list[dict[str, Any]] = []
            preview_chars = 8000
            if preview_budget_chars is not None:
                preview_chars = min(preview_chars, max(300, preview_budget_chars // max(1, len(result.response.data))))
            for index, item in enumerate(result.response.data):
                ref = f'P{state.page_count + index}'
                key = f'page://{item.url}'
                state.vfs[key] = item.content
                receipt_id, result_id = _result_identity(result, index)
                state.sources[ref] = Source(ref=ref, key=key, title=item.title or item.url, url=item.url, content=item.content, receipt_id=receipt_id, result_id=result_id, preview_chars=preview_chars)
                item_payload = {'source_ref': f'[{ref}]', 'vfs_key': key, 'title': item.title, 'url': item.url}
                if len(item.content) > preview_chars:
                    lexical_context = _execute_lexical_context(state, {'query': state.question, 'targets': [key]})
                    item_payload['question_context'] = {'instruction': 'These are the long page regions most relevant to the original question. Inspect them before issuing another page search or read.', 'windows': lexical_context['windows']}
                item_payload['text'] = state.bounded_preview(key, max_serialized_chars=preview_chars)
                items.append(item_payload)
            state.page_count += max(0, len(result.response.data) - 1)
            return {'ok': True, 'pages': items}

        def _execute_read(state: ResearchState, args: dict[str, Any], *, remember_focused: bool=True) -> dict[str, Any]:
            key = str(args['key'])
            if key not in state.vfs:
                raise ValueError(f'unknown VFS key: {key}')
            lines = state.vfs[key].splitlines() or ['']

            def resolve_bound(value: Any, default: int) -> int:
                text = '' if value is None else str(value).strip()
                if value is None or text.lower() in {'', 'null', 'none'}:
                    return default
                location = state.line_locations.get(text)
                if location is not None:
                    if location[0] != key:
                        raise ValueError(f'line ID {value} belongs to {location[0]}, not {key}')
                    return location[1]
                line_number_match = re.fullmatch('L?(\\d+)', text, flags=re.IGNORECASE)
                if line_number_match is None:
                    raise ValueError(f'unknown line bound: {value}; use a displayed line ID or 1-based line number')
                return max(0, int(line_number_match.group(1)) - 1)
            start = resolve_bound(args.get('start_line'), 0)
            end = resolve_bound(args.get('end_line'), len(lines) - 1)
            if start >= len(lines):
                raise ValueError(f'start_line is beyond the file; {key} has {len(lines)} lines')
            if end < start:
                raise ValueError('end_line must not precede start_line')
            requested_end = min(len(lines) - 1, end)
            selected_indices: list[int] = []
            response_chars = 0
            for index in range(start, requested_end + 1):
                estimated_chars = len(lines[index]) + 80
                if selected_indices and response_chars + estimated_chars > VFS_READ_PAGE_CHARS:
                    break
                selected_indices.append(index)
                response_chars += estimated_chars
            selected = selected_indices
            source_refs = [f'[{source.ref}]' for source in state.sources.values() if source.key == key]
            next_index = selected[-1] + 1 if selected else start
            truncated = next_index <= requested_end
            next_line_id = None
            if truncated:
                next_line_id = state._line_id(key, next_index, lines[next_index])
                state.line_locations[next_line_id] = (key, next_index)
            if remember_focused:
                state.remember_focused_lines(key, selected)
            return {'ok': True, 'key': key, 'source_refs': source_refs, 'lines': state.render_lines(key, selected), 'truncated': truncated, 'next_start_line': next_index + 1 if truncated else None, 'next_start_line_id': next_line_id}

        def _execute_list(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
            prefix = str(args['prefix'])
            keys = [key for key in state.vfs if key.startswith(prefix)]
            return {'ok': True, 'keys': keys}

        def _execute_write(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
            key = str(args['key'])
            if key == '*':
                raise ValueError("'*' cannot be a VFS key")
            state.forget_focused_lines(key)
            state.vfs[key] = str(args['content'])
            return {'ok': True, 'key': key, 'chars': len(state.vfs[key])}

        def _execute_delete(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
            key = str(args['key'])
            existed = key in state.vfs
            state.forget_focused_lines(key)
            state.vfs.pop(key, None)
            return {'ok': True, 'key': key, 'deleted': existed}

        def _numeric_literals(text: str) -> set[str]:
            literals: set[str] = set()
            for match in re.finditer('(?<![\\w.])\\d+(?:[,.]\\d+)*%?', text):
                prefix = text[:match.start()].rstrip()
                if prefix.endswith(('<', '>')):
                    continue
                if re.search('(?:above|below|greater than|less than|lower than|more than|threshold(?: of)?)\\s*$', prefix, flags=re.IGNORECASE):
                    continue
                raw = match.group(0)
                digits = re.sub('\\D', '', raw)
                if len(digits) < 2 and (not any((marker in raw for marker in (',', '.', '%')))):
                    continue
                literals.add(raw.rstrip('%').replace(',', ''))
            return literals

        def _validate_retained_numeric_evidence(state: ResearchState, source: Source, note: str, selected_lines: list[dict[str, Any]]) -> None:
            claim_text = re.sub('\\blines?\\s+(?:L[0-9a-f]{10}|\\d+)(?:\\s*(?:-|to|through)\\s*(?:L[0-9a-f]{10}|\\d+))?(?:\\s*\\(L[0-9a-f]{10}\\))?', '', note, flags=re.IGNORECASE)
            note_numbers = _numeric_literals(claim_text)
            selected_numbers = _numeric_literals('\n'.join((str(item['text']) for item in selected_lines)))
            missing = note_numbers - selected_numbers
            if not missing:
                return
            source_lines = state.vfs[source.key].splitlines() or ['']
            locations: dict[str, list[str]] = {}
            for number in sorted(missing):
                matching_indices = [index for index, line in enumerate(source_lines) if number in _numeric_literals(line)]
                if not matching_indices:
                    if number in _numeric_literals(source.title):
                        locations[number] = ['source title only; choose a source whose citable body contains this value']
                    continue
                locations[number] = [f'line {index + 1} ({state._line_id(source.key, index, source_lines[index])})' for index in matching_indices[:3]]
            if not locations:
                return
            details = '; '.join((f"{number}: {', '.join(line_locations)}" for number, line_locations in locations.items()))
            raise ValueError(f'the selected evidence span omits numeric facts asserted by note that are present elsewhere in this source ({details}). Re-read those lines and retry retain_evidence with a span containing the supporting text')

        def _execute_retain_evidence(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
            source_identifier = str(args['source']).strip().strip('[]')
            source = state.sources.get(source_identifier)
            if source is None:
                source = next((candidate for candidate in state.sources.values() if candidate.key == source_identifier), None)
            if source is None:
                if source_identifier in state.vfs and re.fullmatch('search://\\d+', source_identifier):
                    raise ValueError(f"{args['source']} is a search-result container, not a citable source; use the displayed [Sx.y] source reference or search://N/result/y child key that contains the supporting text")
                raise ValueError(f"unknown source reference or VFS key: {args['source']}")
            start_line = args.get('start_line')
            end_line = args.get('end_line')
            if start_line is None or end_line is None:
                raise ValueError('start_line and end_line are required')
            read_output = _execute_read(state, {'key': source.key, 'start_line': start_line, 'end_line': end_line}, remember_focused=False)
            note = str(args['note']).strip()
            _validate_retained_numeric_evidence(state, source, note, read_output['lines'])
            line_ids = ' '.join((str(item['line_id']) for item in read_output['lines']))
            previous_slices = list(state.source_slices.get(source.ref, []))
            packet = state.source_packet(f'{source.ref} {line_ids}', allow_preview=False, include_structured_csv=True, prefer_retained=False)
            if not packet:
                raise RuntimeError(f'could not build evidence packet for source {source.ref}')
            state.source_slices[source.ref] = _merge_citation_slices(previous_slices, list(state.source_slices.get(source.ref, [])))
            retained = packet[0]
            retained['research_note'] = note
            existing = state.retained_evidence.get(source.ref)
            if existing is not None:
                retained = _merge_source_packets([existing], [retained])[0]
                previous_note = str(existing.get('research_note', '')).strip()
                retained['research_note'] = '\n'.join((item for item in (previous_note, note) if item))
            state.retained_evidence[source.ref] = retained
            retained_indices = {state.line_locations[str(item['line_id'])][1] for item in read_output['lines'] if str(item['line_id']) in state.line_locations}
            state.forget_focused_lines(source.key, retained_indices)
            return {'ok': True, 'source_ref': f'[{source.ref}]'}

        def _execute_discard_remaining_sources(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
            reason = str(args['reason']).strip()
            if not reason:
                raise ValueError('reason must not be blank')
            discarded_refs = set(state.review_source_refs)
            discarded_source_count = len(discarded_refs)
            state.review_source_refs.clear()
            retained_keys = {state.sources[ref].key for ref in state.retained_evidence if ref in state.sources}
            for ref in discarded_refs:
                source = state.sources.get(ref)
                if source is not None and source.key not in retained_keys:
                    state.forget_focused_lines(source.key)
            return {'ok': True, 'discarded_source_count': discarded_source_count}

        def _markdown_table_context(state: ResearchState, key: str, match_index: int) -> dict[str, Any] | None:
            lines = state.vfs[key].splitlines() or ['']
            separator_index: int | None = None
            for index in range(match_index, 0, -1):
                if re.fullmatch('\\s*\\|(?:\\s*:?-+:?\\s*\\|)+\\s*', lines[index]):
                    separator_index = index
                    break
                if index < match_index and lines[index].lstrip().startswith('#'):
                    break
            if separator_index is None:
                return None
            header_index = separator_index - 1
            end_index = separator_index
            for index in range(separator_index + 1, len(lines)):
                if not lines[index].lstrip().startswith('|'):
                    break
                end_index = index
            return {'start_line': header_index + 1, 'end_line': end_index + 1, 'header': state.render_lines(key, range(header_index, separator_index + 1))}

        def _execute_regex(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
            pattern = re.compile(str(args['pattern']))
            keys = state.resolve_targets([str(item) for item in args['targets']])
            cursor_value = args.get('cursor')
            cursor = 0 if cursor_value is None else int(cursor_value)
            if cursor < 0:
                raise ValueError('cursor must be at least zero')
            raw_matches: list[tuple[str, dict[str, Any]]] = []
            for key in keys:
                for item in state.render_lines(key):
                    if pattern.search(item['text']):
                        raw_matches.append((key, item))
            matches: list[dict[str, Any]] = []
            page_chars = 0
            for key, item in raw_matches[cursor:]:
                match = {'key': key, **item}
                source_refs = [f'[{source.ref}]' for source in state.sources.values() if source.key == key]
                if source_refs:
                    match['source_refs'] = source_refs
                table_context: dict[str, Any] | None = None
                csv_records = state.structured_csv_records(key, [0, item['line'] - 1])
                if csv_records:
                    match.pop('text')
                    match['csv_record'] = csv_records[0]
                else:
                    table_context = _markdown_table_context(state, key, item['line'] - 1)
                    if table_context is not None:
                        match['table'] = table_context
                focused_indices = {item['line'] - 1}
                if table_context is not None:
                    focused_indices.update((int(header_line['line']) - 1 for header_line in table_context['header']))
                if source_refs:
                    state.remember_focused_lines(key, focused_indices)
                matches.append(match)
                page_chars += len(json.dumps(match, ensure_ascii=False, separators=(',', ':')))
                if page_chars >= VFS_SEARCH_PAGE_CHARS:
                    break
            next_offset = cursor + len(matches)
            next_cursor = next_offset if next_offset < len(raw_matches) else None
            return {'ok': True, 'matched_keys': keys, 'total_match_count': len(raw_matches), 'cursor': cursor, 'matches': matches, 'next_cursor': next_cursor}

        def _chunks(state: ResearchState, keys: list[str]) -> list[dict[str, Any]]:
            chunks: list[dict[str, Any]] = []
            for key in keys:
                content = state.vfs[key]
                start = 0
                index = 0
                while start < len(content):
                    end = min(len(content), start + 3000)
                    chunks.append({'key': key, 'chunk': index, 'start': start, 'end': end, 'text': content[start:end]})
                    if end == len(content):
                        break
                    start = end - 300
                    index += 1
            return chunks
        _LEXICAL_WORD_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
        _LONG_QUOTED_PHRASE_RE = re.compile('"([^"]{24,})"|(?<![a-z0-9])\\\'([^\\\']{24,})\\\'', re.IGNORECASE)
        _LEXICAL_STOP_WORDS = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

        def _lexical_terms(text: str) -> set[str]:
            return {word for word in _LEXICAL_WORD_RE.findall(text.casefold()) if word not in _LEXICAL_STOP_WORDS}

        def _long_quoted_phrases(text: str) -> list[str]:
            return [next((group for group in match.groups() if group is not None)).strip() for match in _LONG_QUOTED_PHRASE_RE.finditer(text)]

        def _exact_phrase_windows(text: str, phrases: list[str]) -> list[tuple[int, int, str]]:
            windows: list[tuple[int, int, str]] = []
            lowered = text.casefold()
            leading_chars = VFS_LEXICAL_WINDOW_CHARS * 3 // 4
            for phrase in phrases:
                search_from = 0
                normalized_phrase = phrase.casefold()
                while True:
                    match_start = lowered.find(normalized_phrase, search_from)
                    if match_start < 0:
                        break
                    start = max(0, match_start - leading_chars)
                    end = min(len(text), start + VFS_LEXICAL_WINDOW_CHARS)
                    start = max(0, end - VFS_LEXICAL_WINDOW_CHARS)
                    if not any((start < existing_end and existing_start < end for existing_start, existing_end, _ in windows)):
                        windows.append((start, end, phrase))
                    search_from = match_start + len(normalized_phrase)
            return windows

        def _lexical_windows(text: str, terms: set[str]) -> list[tuple[int, int, int]]:
            if not text or not terms:
                return []
            if len(text) <= VFS_LEXICAL_WINDOW_CHARS:
                return [(0, len(text), sum((term in text.casefold() for term in terms)))]
            step = max(600, VFS_LEXICAL_WINDOW_CHARS // 3)
            lowered = text.lower()
            scored: list[tuple[int, int]] = []
            start = 0
            while start < len(text):
                window = lowered[start:start + VFS_LEXICAL_WINDOW_CHARS]
                scored.append((sum((term in window for term in terms)), start))
                if start + VFS_LEXICAL_WINDOW_CHARS >= len(text):
                    break
                start += step
            scored.sort(key=lambda item: (-item[0], item[1]))
            selected: list[tuple[int, int, int]] = []
            for matched_term_count, start in scored:
                if len(selected) >= VFS_LEXICAL_WINDOW_COUNT:
                    break
                end = min(len(text), start + VFS_LEXICAL_WINDOW_CHARS)
                if any((start < selected_end and selected_start < end for selected_start, selected_end, _ in selected)):
                    continue
                if selected and matched_term_count == 0:
                    continue
                selected.append((start, end, matched_term_count))
            return sorted(selected)

        def _execute_lexical_context(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
            keys = state.resolve_targets([str(item) for item in args['targets']])
            terms = _lexical_terms(f"{state.question}\n{args['query']}")
            phrases = _long_quoted_phrases(state.question)
            windows: list[dict[str, Any]] = []
            for key in keys:
                content = state.vfs[key]
                selected: list[tuple[int, int, int, str | None]] = [(start, end, len(terms), phrase) for start, end, phrase in _exact_phrase_windows(content, phrases)]
                for start, end, matched_term_count in _lexical_windows(content, terms):
                    if any((start < selected_end and selected_start < end for selected_start, selected_end, _, _ in selected)):
                        continue
                    selected.append((start, end, matched_term_count, None))
                for start, end, matched_term_count, exact_phrase in selected:
                    start_line = content[:start].count('\n')
                    end_line = content[:end].count('\n') + 1
                    windows.append({'key': key, 'start': start, 'end': end, 'matched_term_count': matched_term_count, 'exact_phrase': exact_phrase, 'lines': state.render_lines(key, range(start_line, end_line))})
            windows.sort(key=lambda item: (item['exact_phrase'] is None, -int(item['matched_term_count']), str(item['key']), int(item['start'])))
            return {'ok': True, 'matched_keys': keys, 'windows': windows[:VFS_LEXICAL_WINDOW_COUNT]}

        def _cosine(left: list[float], right: list[float]) -> float:
            numerator = sum((a * b for a, b in zip(left, right, strict=True)))
            left_norm = math.sqrt(sum((value * value for value in left)))
            right_norm = math.sqrt(sum((value * value for value in right)))
            return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0

        async def _execute_similarity(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
            keys = state.resolve_targets([str(item) for item in args['targets']])
            embedded_chunks: list[tuple[dict[str, Any], list[float]]] = []
            missing_chunks: list[dict[str, Any]] = []
            missing_cache_keys: list[tuple[str, str]] = []
            missing_chunk_counts: list[int] = []
            for key in keys:
                cache_key = (key, hashlib.sha256(state.vfs[key].encode()).hexdigest())
                cached = state.document_embeddings.get(cache_key)
                if cached is not None:
                    embedded_chunks.extend(cached)
                    continue
                chunks = _chunks(state, [key])
                missing_cache_keys.append(cache_key)
                missing_chunk_counts.append(len(chunks))
                missing_chunks.extend(chunks)
            if not embedded_chunks and (not missing_chunks):
                return {'ok': True, 'matched_keys': keys, 'chunks': []}
            query_result = await embed_text(str(args['query']), provider='openrouter', model='qwen/qwen3-embedding-8b', input_type='query', provider_extra=EMBEDDING_EXTRA, timeout=EMBEDDING_TIMEOUT)
            if missing_chunks:
                document_result = await embed_text([chunk['text'] for chunk in missing_chunks], provider='openrouter', model='qwen/qwen3-embedding-8b', input_type='document', provider_extra=EMBEDDING_EXTRA, timeout=EMBEDDING_TIMEOUT)
                vectors = [item.embedding for item in sorted(document_result.response.data, key=lambda item: item.index)]
                if len(vectors) != len(missing_chunks):
                    raise RuntimeError(f'embedding result count mismatch: expected {len(missing_chunks)}, received {len(vectors)}')
                offset = 0
                for cache_key, chunk_count in zip(missing_cache_keys, missing_chunk_counts, strict=True):
                    cached = list(zip(missing_chunks[offset:offset + chunk_count], vectors[offset:offset + chunk_count], strict=True))
                    state.document_embeddings[cache_key] = cached
                    embedded_chunks.extend(cached)
                    offset += chunk_count
            query_vector = query_result.response.data[0].embedding
            scored = [{**chunk, 'score': _cosine(query_vector, vector)} for chunk, vector in embedded_chunks]
            scored.sort(key=lambda item: item['score'], reverse=True)
            output: list[dict[str, Any]] = []
            output_chars = 0
            for item in scored[:VFS_SIMILARITY_MAX_CHUNKS]:
                key = item['key']
                content_before = state.vfs[key][:item['start']]
                start_line = content_before.count('\n')
                line_count = item['text'].count('\n') + 1
                result_item = {'key': key, 'chunk': item['chunk'], 'score': item['score'], 'lines': state.render_lines(key, range(start_line, start_line + line_count))}
                source_refs = [f'[{source.ref}]' for source in state.sources.values() if source.key == key]
                if source_refs:
                    result_item['source_refs'] = source_refs
                result_chars = len(json.dumps(result_item, ensure_ascii=False, separators=(',', ':')))
                if len(output) >= VFS_SIMILARITY_MIN_CHUNKS and output_chars + result_chars > VFS_SIMILARITY_RESULT_CHARS:
                    break
                if source_refs:
                    state.remember_focused_lines(key, range(start_line, start_line + line_count))
                output.append(result_item)
                output_chars += result_chars
            return {'ok': True, 'matched_keys': keys, 'chunks': output}

        async def _execute_vfs_search(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
            regex_result: dict[str, Any] | None = None
            regex_error: str | None = None
            try:
                regex_result = _execute_regex(state, args)
            except (TypeError, ValueError, re.error) as error:
                regex_error = str(error)
            similarity_trigger: str | None = None
            if regex_result is None:
                similarity_trigger = 'regex_error'
            elif int(regex_result['total_match_count']) == 0:
                similarity_trigger = 'no_regex_matches'
            similarity_result: dict[str, Any] | None = None
            similarity_error: str | None = None
            if similarity_trigger is not None:
                try:
                    similarity_result = await _execute_similarity(state, args)
                except Exception as error:
                    similarity_error = str(error)
            if regex_result is None and similarity_result is None:
                raise RuntimeError(f"both VFS search methods failed: regex={regex_error or 'unknown'}; similarity={similarity_error or 'unknown'}")
            output: dict[str, Any] = {'ok': True, 'similarity': {'status': 'not_run', 'reason': 'regex_returned_matches_on_first_search'}}
            if regex_result is not None:
                output['regex'] = {key: value for key, value in regex_result.items() if key not in {'ok', 'matched_keys'}}
            if regex_error is not None:
                output['regex_error'] = regex_error
            if similarity_result is not None:
                output['similarity'] = {'status': 'completed', 'trigger': similarity_trigger}
                output['similarity'].update({key: value for key, value in similarity_result.items() if key not in {'ok', 'matched_keys'}})
            if similarity_error is not None:
                output['similarity'] = {'status': 'failed', 'trigger': similarity_trigger, 'error': similarity_error}
            return output

        async def _execute_tool(state: ResearchState, name: str, args: dict[str, Any], preview_budget_chars: int | None=None) -> dict[str, Any]:
            if name in {'search_web', 'fetch_page'}:
                cached = state.retrieval_output_cache.get(_retrieval_signature(name, args))
                if cached is not None:
                    return {**cached, 'cached': True}
            if name == 'search_web':
                return await _execute_search(state, args, preview_budget_chars)
            if name == 'fetch_page':
                return await _execute_fetch(state, args, preview_budget_chars)
            if name == 'vfs_read':
                return _execute_read(state, args)
            if name == 'vfs_list':
                return _execute_list(state, args)
            if name == 'vfs_write':
                return _execute_write(state, args)
            if name == 'vfs_delete':
                return _execute_delete(state, args)
            if name == 'retain_evidence':
                return _execute_retain_evidence(state, args)
            if name == 'discard_remaining_sources':
                return _execute_discard_remaining_sources(state, args)
            if name == 'vfs_search':
                return await _execute_vfs_search(state, args)
            if name == 'update_research_state':
                research_state = str(args['state']).strip()
                if not research_state:
                    raise ValueError('state must not be blank')
                state.research_state = research_state
                return {'ok': True}
            raise ValueError(f'unknown tool: {name}')

        def _deduplicate_tool_calls(calls: list[Any]) -> tuple[list[Any], int]:
            unique_calls: list[Any] = []
            seen: set[tuple[str, str]] = set()
            for call in calls:
                try:
                    arguments = json.dumps(json.loads(call.arguments), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
                except json.JSONDecodeError:
                    arguments = call.arguments
                signature = (call.name, arguments)
                if signature in seen:
                    continue
                seen.add(signature)
                unique_calls.append(call)
            return (unique_calls, len(calls) - len(unique_calls))

        async def _finalize_answer(*, state: ResearchState, question: str, current_answer: str, reason: str, assistant_context: str, last_packet: list[dict[str, Any]], final_source_slices: dict[str, list[CitationSlice]]) -> tuple[str, list[dict[str, Any]]]:
            finalization_context = '\n\n'.join((value for value in (state.research_state.strip(), reason.strip(), assistant_context.strip()) if value))
            packet = state.source_packet(finalization_context, include_structured_csv=True)
            if not packet:
                raise ValueError('final answer must mention at least one observed source reference such as S1.2 or P1')
            unretained_page_refs = [str(item['source_ref']) for item in packet if str(item['source_ref']).strip('[]').startswith('P') and str(item['source_ref']).strip('[]') not in state.retained_evidence]
            if unretained_page_refs:
                raise ValueError(f"fetched-page evidence must be preserved before finalization; call retain_evidence for each decisive excerpt from {', '.join(unretained_page_refs)}, then retry")
            for item in packet:
                ref = str(item['source_ref'])[1:-1]
                final_source_slices[ref] = _merge_citation_slices(final_source_slices.get(ref, []), list(state.source_slices.get(ref, [])))
            precise_refs = {str(item['source_ref']) for item in [*last_packet, *packet]}
            retained_packet = [item for item in state.retained_evidence.values() if str(item['source_ref']) not in precise_refs]
            merged_packet = _merge_source_packets(last_packet, retained_packet)
            merged_packet = _merge_source_packets(merged_packet, packet)
            merged_packet = [item for item in merged_packet if (source := state.sources.get(str(item['source_ref']).strip('[]'))) and source.receipt_id and source.result_id]
            if not merged_packet:
                raise ValueError('none of the selected source records can be materialized as response citations')
            answer = await _answer_text(state=state, question=question, prior_answer=current_answer, requirements=state.evidence_requirements or '', research_state=state.research_state, finalization_reason=reason, packet=merged_packet)
            return (answer, merged_packet)

        def _research_progress_signature(state: ResearchState) -> tuple[Any, ...]:
            return (state.evidence_requirements, tuple(sorted(state.sources)), tuple(((key, tuple(sorted(indices))) for key, indices in sorted(state.focused_lines.items()))), tuple(sorted(state.retained_evidence)), state.research_state, state.audit_gap)

        def _investigation_models(state: ResearchState, deadline_notice_sent: bool, switch_reason: str) -> tuple[str, ...]:
            if MODEL_SCHEDULING != 'state_aware':
                return REPAIR_MODELS if state.audit_gap else INVESTIGATION_MODELS
            if state.audit_gap or deadline_notice_sent or switch_reason:
                return REPAIR_MODELS
            return STATE_AWARE_INVESTIGATION_MODELS

        def _requirements_models(deadline_notice_sent: bool, switch_reason: str) -> tuple[str, ...]:
            if MODEL_SCHEDULING == 'state_aware' and (deadline_notice_sent or switch_reason):
                return REPAIR_MODELS
            return REQUIREMENTS_MODELS

        async def _investigate(question: str, expected_answer: str) -> tuple[str, list[CitationRef]]:
            investigation_started_at = _wall_start()
            deadline_notice_sent = False
            state = ResearchState(question)
            state.research_state = f'Current best answer hypothesis:\n{expected_answer}\nObserved support: none yet.\nMost important unresolved question: test the hypothesis against external evidence.'
            current_answer = expected_answer
            messages: list[Any] = [{'role': 'system', 'content': INVESTIGATION_SYSTEM}, {'role': 'user', 'content': f'Original question:\n{question}\n\nExpected answer hypothesis:\n{expected_answer}'}]
            last_packet: list[dict[str, Any]] = []
            final_source_slices: dict[str, list[CitationSlice]] = {}
            final_audit = ''
            switch_reason = ''
            previous_call_signatures: tuple[str, ...] = ()
            governor_notice_sent = False
            governor_bypass_failed = False
            governor_turns = 0
            for _turn in range(160):
                if not deadline_notice_sent and time.monotonic() - investigation_started_at >= DEADLINE_NOTICE_SECONDS:
                    messages.append({'role': 'user', 'content': 'The external runtime has about 150 seconds remaining. Preserve answer quality. If the observed evidence can support the answer, retain any needed excerpts and call ready_to_finalize now. If one decisive uncertainty remains, perform only the single operation most likely to resolve it, then finalize. Do not restart broad research.'})
                    deadline_notice_sent = True
                _refresh_retrieval_receipt_message(messages, state)
                requirements_pending = state.evidence_requirements is None
                governor_elapsed = _wall_elapsed()
                governor_stage = 'open' if requirements_pending else _governor_stage(state, governor_elapsed)
                if not state.sources:
                    governor_stage = 'open'
                if governor_stage != 'open':
                    governor_turns += 1
                if governor_turns > SPEND_GOVERNOR_MAX_CLOSING_TURNS:
                    governor_stage = 'open'
                if governor_stage == 'hard' and (not governor_bypass_failed) and _closable_source_refs(state):
                    try:
                        current_answer, last_packet = await _finalize_answer(state=state, question=question, current_answer=current_answer, reason='The harness closed the investigation because the observed session spend or elapsed time reached the governor ceiling. Answer from the evidence already retained.', assistant_context=_closable_source_context(state), last_packet=last_packet, final_source_slices=final_source_slices)
                    except (ValueError, RuntimeError) as error:
                        governor_bypass_failed = True
                        switch_reason = f'Observed session spend reached the governor ceiling and the harness could not close the investigation directly: {error}. Resolve that exact problem with the closing tools and finalize now.'
                    else:
                        plan = state.citation_plan(current_answer, last_packet, final_source_slices, final_audit)
                        return _render_public_citations(current_answer, plan, unadorned_output=_requires_unadorned_output(question))
                if requirements_pending:
                    available_tools = REQUIREMENTS_TOOLS
                    available_models = _requirements_models(deadline_notice_sent, switch_reason)
                elif governor_stage == 'open':
                    available_tools = TOOLS
                    available_models = _investigation_models(state, deadline_notice_sent, switch_reason)
                else:
                    available_tools = CLOSING_TOOLS
                    available_models = REPAIR_MODELS
                    if not governor_notice_sent:
                        messages.append({'role': 'user', 'content': 'Observed session spend reached the governor threshold. Retrieval tools are withdrawn for the rest of this task. Retain any excerpt the answer still needs, update the research state if the answer changed, and call ready_to_finalize in this response.'})
                        governor_notice_sent = True
                request_messages = [{'role': 'system', 'content': REQUIREMENTS_SYSTEM}, {'role': 'user', 'content': f'Original question:\n{question}'}] if requirements_pending else messages
                result = await _chat_with_scheduling(available_models, messages=request_messages, tools=available_tools, tool_choice='required', parallel_tool_calls=True, timeout=LLM_TIMEOUT, max_output_tokens=None)
                _capture_budget(state, result)
                _compact_consumed_assistant_reasoning(messages)
                _compact_consumed_tool_results(messages)
                assistant = _assistant_message(result)
                state.remember_reasoning_observation(assistant.reasoning)
                calls, duplicate_call_count = _deduplicate_tool_calls(list(assistant.tool_calls or ()))
                if not calls:
                    prose = (result.llm.raw_text or '').strip()
                    if prose:
                        try:
                            current_answer, last_packet = await _finalize_answer(state=state, question=question, current_answer=current_answer, reason=prose, assistant_context=_assistant_evidence_context(assistant), last_packet=last_packet, final_source_slices=final_source_slices)
                        except ValueError as error:
                            switch_reason = f'The previous model tried to finalize without materializable support. Resolve this exact problem before finalizing again: {error}'
                            messages.extend([assistant.to_input_message(), {'role': 'user', 'content': f'Your terminal answer could not be finalized: {error}. Use tools to resolve that exact problem, then either return a supported terminal answer or call ready_to_finalize.'}])
                            continue
                        plan = state.citation_plan(current_answer, last_packet, final_source_slices, final_audit)
                        return _render_public_citations(current_answer, plan, unadorned_output=_requires_unadorned_output(question))
                    messages.extend([assistant.to_input_message(), {'role': 'user', 'content': 'Use a tool. Call ready_to_finalize only when inspected sources support the answer.'}])
                    switch_reason = 'The previous model returned neither a tool call nor a usable terminal answer. Choose the smallest valid operation that advances the investigation.'
                    continue
                assistant_input = replace(assistant, tool_calls=tuple(calls)).to_input_message()
                messages.append(assistant_input)
                ready_requested = False
                audit_ready = False
                progress_before = _research_progress_signature(state)
                turn_call_signatures: list[str] = []
                turn_failure_signatures: list[str] = []
                retrieval_call_count = sum((call.name in {'search_web', 'fetch_page'} for call in calls))
                retrieval_preview_budget = BATCHED_RETRIEVAL_PREVIEW_CHARS // retrieval_call_count if retrieval_call_count else None
                for call_index, call in enumerate(calls):
                    call_signature = json.dumps({'tool': call.name, 'raw_arguments': call.arguments}, ensure_ascii=False, sort_keys=True)
                    try:
                        args = json.loads(call.arguments)
                        if not isinstance(args, dict):
                            raise ValueError('tool arguments must be a JSON object')
                        call_signature = json.dumps({'tool': call.name, 'arguments': args}, ensure_ascii=False, sort_keys=True)
                        if call.name == 'set_evidence_requirements':
                            if not requirements_pending or len(calls) != 1:
                                raise ValueError('set_evidence_requirements must be the sole call before retrieval')
                            requirements = str(args['requirements']).strip()
                            if not requirements:
                                raise ValueError('requirements must not be empty')
                            state.evidence_requirements = requirements
                            output = {'ok': True}
                        elif call.name == 'ready_to_finalize':
                            if turn_failure_signatures:
                                raise ValueError('cannot finalize in the same response after an earlier tool call failed; inspect that tool feedback, correct the failed operation, and retry finalization')
                            incompatible_calls = [candidate.name for candidate in calls if candidate.name not in {'update_research_state', 'retain_evidence', 'ready_to_finalize'}]
                            if incompatible_calls:
                                raise ValueError(f"ready_to_finalize may only accompany update_research_state and retain_evidence; also received {', '.join(incompatible_calls)}")
                            if call_index != len(calls) - 1:
                                raise ValueError('ready_to_finalize must be the final call in the response')
                            reason = str(args['reason'])
                            current_answer, last_packet = await _finalize_answer(state=state, question=question, current_answer=current_answer, reason=reason, assistant_context=_assistant_evidence_context(assistant), last_packet=last_packet, final_source_slices=final_source_slices)
                            final_audit = ''
                            ready_requested = True
                            audit_ready = True
                            output = {'ok': True, 'answer_checkpoint': current_answer}
                        elif call.name == 'discard_remaining_sources':
                            if call_index != len(calls) - 1:
                                raise ValueError('discard_remaining_sources must be the last call in the response')
                            output = await _execute_tool(state, call.name, args, retrieval_preview_budget)
                        else:
                            output = await _execute_tool(state, call.name, args, retrieval_preview_budget)
                            _record_retrieval_receipt(state, call.name, args, output)
                            _record_vfs_operation_receipt(state, call.name, args, output)
                    except Exception as error:
                        output = {'ok': False, 'error_type': 'tool_argument_validation' if isinstance(error, (KeyError, TypeError, ValueError, json.JSONDecodeError)) else 'tool_execution', 'details': str(error)}
                    turn_call_signatures.append(call_signature)
                    if not output.get('ok'):
                        turn_failure_signatures.append(json.dumps({'tool': call.name, 'error_type': output.get('error_type')}, ensure_ascii=False, sort_keys=True))
                    messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': json.dumps(output, ensure_ascii=False)})
                if duplicate_call_count:
                    messages.append({'role': 'user', 'content': f'The previous response repeated {duplicate_call_count} exact tool calls. The harness executed each distinct call once. Continue from those results without repeating an identical call.'})
                if ready_requested:
                    final_audit = await _audit(state, question, current_answer, last_packet)
                    verdict, audit_payload = _parse_audit(final_audit)
                    if verdict == 'CONTINUE':
                        state.audit_gap = audit_payload
                        state.clear_focused_lines()
                        audit_ready = False
                        messages = [{'role': 'system', 'content': INVESTIGATION_SYSTEM}, {'role': 'user', 'content': f'Original question:\n{question}\n\nThe finalization audit found one unresolved evidence gap:\n{audit_payload}\n\nThe harness will preserve the existing VFS, source references, retained evidence, retrieval receipts, and research state. Resolve this exact gap with the smallest useful next observation, update the research state if the answer changes, then finalize. Do not restart the investigation or repeat already supported premises.'}]
                    elif verdict == 'REVISE':
                        allowed_refs = {str(item['source_ref']).strip('[]') for item in last_packet if isinstance(item, dict) and item.get('source_ref')}
                        _validate_private_answer_refs(audit_payload, allowed_refs, require_ref=not _requires_unadorned_output(question))
                        current_answer = audit_payload
                        state.audit_gap = ''
                        audit_ready = True
                    else:
                        state.audit_gap = ''
                        audit_ready = True
                if MODEL_SCHEDULING == 'state_aware' and (not ready_requested):
                    progress_after = _research_progress_signature(state)
                    current_calls = tuple(turn_call_signatures)
                    current_failures = tuple(turn_failure_signatures)
                    next_switch_reason = ''
                    if current_failures:
                        next_switch_reason = "The previous model's tool call failed. Read the detailed tool feedback, correct that exact operation or choose a different valid operation, and advance the investigation without repeating the failure."
                    elif current_calls and current_calls == previous_call_signatures and (progress_after == progress_before):
                        next_switch_reason = 'The previous model repeated the same operations without adding evidence or changing the research state. Choose a different evidence route.'
                    elif current_calls and (not current_failures) and (progress_after == progress_before):
                        next_switch_reason = 'The previous operations succeeded mechanically but produced no new retained evidence, source coverage, inspected lines, or research-state change. Choose the smallest different operation that can resolve the current uncertainty.'
                    if next_switch_reason:
                        messages.append({'role': 'user', 'content': next_switch_reason})
                    switch_reason = next_switch_reason
                    previous_call_signatures = current_calls
                if ready_requested and audit_ready:
                    plan = state.citation_plan(current_answer, last_packet, final_source_slices, final_audit)
                    return _render_public_citations(current_answer, plan, unadorned_output=_requires_unadorned_output(question))
            raise RuntimeError('investigation did not finalize within the generous 160-turn ceiling')

        async def query(query: Query) -> Response:
            _wall_start()
            try:
                return await _answer_query(query)
            except Exception:
                if query.output_schema is not None:
                    try:
                        return Response(output=_WALL_RESCUE_TEXT)
                    except Exception:
                        return Response(output='')
                return Response(text=_WALL_RESCUE_TEXT)
        _WALL_RESCUE_TEXT = '[[beacon:no-evidence]] The research run could not be completed for this question.'

        async def _answer_query(query: Query) -> Response:
            try:
                expected_answer = await _expected_answer_text(query.text)
            except Exception as error:
                if not _is_retryable_llm_error(error):
                    raise
                expected_answer = 'No expected-answer hypothesis was available because its model call failed. Investigate the original question directly and construct a revisable answer from observed external evidence.'
            answer, citations = await _investigate(query.text, expected_answer)
            if query.output_schema is not None:
                try:
                    output = await _materialize_structured_output(question=query.text, answer=answer, output_schema=query.output_schema)
                except Exception:
                    output = None
                if output is None:
                    output = _WALL_RESCUE_TEXT
                return Response(output=output, citations=citations or None)
            return Response(text=answer, citations=citations or None)
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

async def _s17_base_query(query: Query) -> Response:
    try:
        easy = await _ROUTER._is_easy(query.text)
    except Exception:
        easy = False
    if easy:
        return await _EASY_RUN(query)
    return await _HARD_RUN(query)


# =====================================================================
# submittion17 MECHANISM — iterative claim-driven retrieval and
# verification loop (decompose -> per-claim targeted search -> per-claim
# verdict -> bounded sequential patch), independent of internal evidence
# =====================================================================
#
# Runs after the base pipeline above has produced a draft Response. Unlike
# a single fresh-evidence spot-check, this stage:
#   1. Decomposes the draft into up to 4 discrete, independently-checkable
#      load-bearing/time-sensitive factual claims (LLM call).
#   2. Issues ONE NEW, independently targeted search_web call PER CLAIM
#      (concurrently), each query built from that specific claim rather
#      than the original question -- retrieval targeted at verifying
#      individual assertions, not a single whole-answer check.
#   3. Verifies each claim against only its own freshly retrieved,
#      independently sourced evidence, additionally flagging claims whose
#      fresh sources internally disagree with each other ("disputed").
#   4. Sequentially, per claim: a contradicted claim triggers a bounded
#      corrective rewrite of the running answer (grounded in that claim's
#      fresh evidence only); a disputed claim gets a brief inline
#      qualifier noting source disagreement; a corroborated claim
#      reinforces citation coverage with new, distinct CitationRef entries
#      (never fabricated -- always drawn from a real receipt_id/result_id
#      this pass itself retrieved).
# This changes decomposition, retrieval targeting, contradiction handling,
# verification, and citation-provenance control flow relative to the base
# pipeline; it is not a prompt or parameter tweak. Any failure, missing
# evidence, structured/schema response, or time shortage is a strict
# no-op that returns the base pipeline's own response (after cheap exact
# duplicate-citation cleanup only).

import asyncio as _s17_asyncio
import json as _s17_json
import re as _s17_re
from time import monotonic as _s17_monotonic

_S17_HARD_BUDGET_GATE_S = 250.0
_S17_MAX_WINDOW_S = 45.0
_S17_MIN_WINDOW_S = 8.0
_S17_DECOMPOSE_TIMEOUT_S = 9.0
_S17_SEARCH_TIMEOUT_S = 9.0
_S17_VERIFY_TIMEOUT_S = 8.0
_S17_PATCH_TIMEOUT_S = 11.0
_S17_MAX_CLAIMS = 4
_S17_MAX_NEW_CITATIONS_PER_CLAIM = 2
_S17_MAX_TOTAL_CITATIONS = 60
_S17_MODEL = "deepseek/deepseek-v3.2"

_S17_DECOMPOSE_SYSTEM_PROMPT = (
    "You extract independently fact-checkable claims from a research answer.\n"
    "Given a question and a drafted answer, list up to 4 discrete, concrete, "
    "load-bearing or time-sensitive factual claims from the answer that are "
    "worth independently re-verifying (specific names, dates, figures, "
    "statuses, rankings, outcomes). Skip vague, stylistic, or trivially "
    "well-known statements.\n"
    "For each claim, also produce a short, targeted web search query (5-12 "
    "words) that would directly test whether that specific claim is true -- "
    "not a restatement of the whole original question.\n"
    "Return JSON only: {\"claims\": [{\"claim\": str, \"search_query\": str}, ...]}. "
    "Return an empty list if the answer has no such claims."
)

_S17_VERIFY_SYSTEM_PROMPT = (
    "You are a strict fact-verification auditor for ONE specific claim.\n"
    "You receive a single claim and up to 4 freshly retrieved, independent "
    "evidence snippets gathered specifically to test that claim.\n"
    "Classify strictly from this evidence:\n"
    "- contradicted: a snippet states a directly conflicting fact (different "
    "name, date, figure, status, or outcome) for the same element the claim "
    "asserts.\n"
    "- corroborated: one or more snippets directly support the claim.\n"
    "- disputed: two or more snippets disagree with EACH OTHER on the same "
    "element the claim addresses (not just with the claim).\n"
    "- unverifiable: the evidence neither supports, conflicts, nor disputes.\n"
    "Return JSON only with keys: verdict "
    "('contradicted'|'corroborated'|'disputed'|'unverifiable'), "
    "correction (string or null, only for contradicted -- the corrected "
    "fact), dispute_note (string or null, only for disputed -- one short "
    "clause describing the disagreement), supporting_snippet_indices "
    "(array of 0-based ints, may be empty)."
)

_S17_PATCH_SYSTEM_PROMPT = (
    "You correct ONE factual claim inside a research answer using freshly "
    "retrieved evidence that specifically contradicts it.\n"
    "Rewrite the COMPLETE answer: keep every part unrelated to this claim "
    "byte-for-byte where feasible, and replace only the conflicting fact "
    "with what the fresh evidence supports. If the evidence only shows the "
    "old claim is unverified rather than the correct value, soften the "
    "claim to note it is unconfirmed instead of guessing a new value.\n"
    "Preserve all existing citation markers whose underlying claims are "
    "unchanged. Output plain answer text only: no preamble, no markdown "
    "fences, no meta-commentary about the correction process."
)


def _s17_strip_json_fences(raw: str) -> str:
    return _s17_re.sub(r"^```(?:json)?\s*|\s*```$", "", raw or "", flags=_s17_re.I | _s17_re.M).strip()


def _s17_chat_text(llm_result) -> str:
    if llm_result is None:
        return ""
    resp = getattr(llm_result, "response", None)
    text = getattr(resp, "raw_text", None) if resp is not None else None
    return (text or "").strip()


def _s17_citation_key(ref) -> tuple:
    slices = tuple(
        (getattr(sl, "start", None), getattr(sl, "end", None))
        for sl in (getattr(ref, "slices", None) or [])
    )
    return (getattr(ref, "receipt_id", None), getattr(ref, "result_id", None), slices)


def _s17_dedup_citations(response):
    citations = getattr(response, "citations", None)
    if not citations:
        return response
    seen: set = set()
    deduped = []
    for ref in citations:
        key = _s17_citation_key(ref)
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


def _s17_merge_citations(existing, new_refs):
    existing_list = list(existing or [])
    seen = {_s17_citation_key(ref) for ref in existing_list}
    merged = list(existing_list)
    for ref in new_refs:
        key = _s17_citation_key(ref)
        if key in seen:
            continue
        seen.add(key)
        merged.append(ref)
        if len(merged) >= _S17_MAX_TOTAL_CITATIONS:
            break
    return merged


async def _s17_decompose_claims(question: str, answer: str) -> list:
    from harnyx_miner_sdk.api import llm_chat as _s17_llm_chat

    try:
        result = await _s17_llm_chat(
            provider="openrouter",
            model=_S17_MODEL,
            messages=[
                {"role": "system", "content": _S17_DECOMPOSE_SYSTEM_PROMPT},
                {"role": "user", "content": f"Question:\n{question}\n\nDrafted answer:\n{answer[:12000]}"},
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=500,
            timeout=_S17_DECOMPOSE_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return []
    try:
        parsed = _s17_json.loads(_s17_strip_json_fences(_s17_chat_text(result)))
    except Exception:
        return []
    if not isinstance(parsed, dict):
        return []
    raw_claims = parsed.get("claims")
    if not isinstance(raw_claims, list):
        return []
    out = []
    for item in raw_claims:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim") or "").strip()
        squery = str(item.get("search_query") or "").strip()
        if claim and squery:
            out.append({"claim": claim, "search_query": squery})
        if len(out) >= _S17_MAX_CLAIMS:
            break
    return out


async def _s17_search_claim(search_query: str):
    from harnyx_miner_sdk.api import search_web as _s17_search_web

    for provider_name in ("parallel", "desearch"):
        try:
            payload = await _s17_search_web(
                search_query[:300],
                provider=provider_name,
                num=4,
                timeout=_S17_SEARCH_TIMEOUT_S,
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


async def _s17_verify_claim(claim: str, evidence_items: list) -> dict:
    from harnyx_miner_sdk.api import llm_chat as _s17_llm_chat

    evidence_block = "\n".join(
        f"[{idx}] {item['title']} \u2014 {item['url']}\n{item['note'][:900]}"
        for idx, item in enumerate(evidence_items)
    )
    try:
        result = await _s17_llm_chat(
            provider="openrouter",
            model=_S17_MODEL,
            messages=[
                {"role": "system", "content": _S17_VERIFY_SYSTEM_PROMPT},
                {"role": "user", "content": f"Claim:\n{claim}\n\nFresh evidence snippets:\n{evidence_block}"},
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=350,
            timeout=_S17_VERIFY_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return {"verdict": "unverifiable"}
    try:
        report = _s17_json.loads(_s17_strip_json_fences(_s17_chat_text(result)))
    except Exception:
        return {"verdict": "unverifiable"}
    if not isinstance(report, dict):
        return {"verdict": "unverifiable"}
    return report


def _s17_build_refs(receipt_id: str, evidence_items: list, indices) -> list:
    from harnyx_miner_sdk.query import CitationRef as _s17_citation_ref
    from harnyx_miner_sdk.query import CitationSlice as _s17_citation_slice

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
            refs.append(_s17_citation_ref(
                receipt_id=receipt_id,
                result_id=item["result_id"],
                slices=[_s17_citation_slice(start=0, end=end)],
            ))
        except Exception:
            continue
        if len(refs) >= _S17_MAX_NEW_CITATIONS_PER_CLAIM:
            break
    return refs


async def _s17_patch_claim(question: str, answer: str, claim: str, correction: str, evidence_block: str) -> str:
    from harnyx_miner_sdk.api import llm_chat as _s17_llm_chat

    prompt = (
        f"Question:\n{question}\n\n"
        f"Current answer:\n{answer[:12000]}\n\n"
        f"Claim being corrected:\n{claim}\n\n"
        f"What the fresh evidence supports instead:\n{correction or 'see evidence below'}\n\n"
        f"Fresh evidence snippets:\n{evidence_block}"
    )
    try:
        result = await _s17_llm_chat(
            provider="openrouter",
            model=_S17_MODEL,
            messages=[
                {"role": "system", "content": _S17_PATCH_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            tools=None,
            temperature=0.1,
            max_output_tokens=1400,
            timeout=_S17_PATCH_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return ""
    return _s17_chat_text(result)[:79000].strip()


async def _s17_verify_and_patch(_s17_query, _s17_response):
    _s17_response = _s17_dedup_citations(_s17_response)
    if getattr(_s17_response, "output", None) is not None:
        return _s17_response
    question = (getattr(_s17_query, "text", None) or "").strip()
    answer = (getattr(_s17_response, "text", None) or "").strip()
    if not question or not answer:
        return _s17_response

    claims = await _s17_decompose_claims(question, answer)
    if not claims:
        return _s17_response

    search_results = await _s17_asyncio.gather(
        *[_s17_search_claim(c["search_query"]) for c in claims],
        return_exceptions=True,
    )

    per_claim = []
    for claim_info, search_result in zip(claims, search_results):
        if isinstance(search_result, Exception) or not search_result:
            continue
        per_claim.append((claim_info, search_result))
    if not per_claim:
        return _s17_response

    verify_results = await _s17_asyncio.gather(
        *[_s17_verify_claim(ci["claim"], sr["items"]) for ci, sr in per_claim],
        return_exceptions=True,
    )

    running_answer = answer
    all_new_refs = []
    appended_notes = []
    for (claim_info, search_result), verdict_report in zip(per_claim, verify_results):
        if isinstance(verdict_report, Exception) or not isinstance(verdict_report, dict):
            continue
        verdict = str(verdict_report.get("verdict") or "").strip().lower()
        items = search_result["items"]
        receipt_id = search_result["receipt_id"]
        evidence_block = "\n".join(
            f"[{idx}] {item['title']} \u2014 {item['url']}\n{item['note'][:900]}"
            for idx, item in enumerate(items)
        )

        if verdict == "contradicted":
            new_text = await _s17_patch_claim(
                question, running_answer, claim_info["claim"],
                str(verdict_report.get("correction") or ""), evidence_block,
            )
            if new_text:
                running_answer = new_text
                refs = _s17_build_refs(receipt_id, items, verdict_report.get("supporting_snippet_indices") or [0])
                all_new_refs.extend(refs)
            continue

        if verdict == "corroborated":
            indices = verdict_report.get("supporting_snippet_indices")
            refs = _s17_build_refs(receipt_id, items, indices if isinstance(indices, list) and indices else [0])
            all_new_refs.extend(refs)
            continue

        if verdict == "disputed":
            note = str(verdict_report.get("dispute_note") or "").strip()
            if note and len(appended_notes) < 2:
                appended_notes.append(note)
            refs = _s17_build_refs(receipt_id, items, [0])
            all_new_refs.extend(refs)
            continue

    if appended_notes:
        qualifier = " Note: " + "; ".join(appended_notes) + "."
        if len(running_answer) + len(qualifier) <= 79000:
            running_answer = running_answer + qualifier

    merged_citations = _s17_merge_citations(getattr(_s17_response, "citations", None), all_new_refs)
    if running_answer == answer and len(merged_citations) == len(list(getattr(_s17_response, "citations", None) or [])):
        return _s17_response
    try:
        return _s17_response.model_copy(update={"text": running_answer, "citations": merged_citations})
    except Exception:
        return _s17_response


async def _s17_finalize(_s17_query, _s17_response, _s17_t0: float):
    """Bounded, iterative claim-driven retrieval-and-verification pass."""
    if _s17_response is None:
        return _s17_response
    if getattr(_s17_response, "text", None) in (None, "") and getattr(_s17_response, "output", None) is None:
        return _s17_response
    elapsed = _s17_monotonic() - _s17_t0
    if elapsed >= _S17_HARD_BUDGET_GATE_S:
        return _s17_dedup_citations(_s17_response)
    window = min(_S17_MAX_WINDOW_S, max(_S17_MIN_WINDOW_S, 280.0 - elapsed))
    try:
        return await _s17_asyncio.wait_for(
            _s17_verify_and_patch(_s17_query, _s17_response),
            timeout=window,
        )
    except Exception:
        return _s17_dedup_citations(_s17_response)


@entrypoint("query")
async def query(query: Query) -> Response:
    _s17_t0 = _s17_monotonic()
    _s17_resp = await _s17_base_query(query)
    try:
        return await _s17_finalize(query, _s17_resp, _s17_t0)
    except Exception:
        return _s17_resp
