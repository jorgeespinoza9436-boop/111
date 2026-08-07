from __future__ import annotations
import asyncio
from time import monotonic
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class PrimarySolver:

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
                VERSION = 'v33.4-structure'
                LLM_PROVIDER = 'openrouter'
                LOOP_MODEL_A = 'z-ai/glm-5.2'
                LOOP_MODEL_B = 'deepseek/deepseek-v3.2'
                AUDIT_MODEL = 'openai/gpt-oss-120b'
                SCHEMA_MODEL = 'openai/gpt-oss-120b'
                RESORT_MODEL = 'deepseek/deepseek-v3.2'
                SEARCH_PROVIDER = 'parallel'
                WALL_BUDGET_S = 262.0
                BRIEF_TIMEOUT_S = 50.0
                TURN_TIMEOUT_S = 75.0
                FALLBACK_MAX_PAYLOAD_CHARS = 380000
                AUDIT_TIMEOUT_S = 28.0
                SEARCH_TIMEOUT_S = 18.0
                FETCH_TIMEOUT_S = 16.0
                WRAPUP_AT_S = 90.0
                MIN_TAIL_S = 8.0
                MAX_TURNS = 15
                MAX_TOOL_CALLS_PER_TURN = 8
                AUDIT_EXTRA_TURNS = 2
                ANSWER_REPAIR_TURNS = 2
                RESCUE_TIMEOUT_S = 55.0
                DIGEST_TAIL_S = 14.0
                FETCH_HEAD_CHARS = 3000
                FETCH_WINDOW_CHARS = 3600
                SEARCH_EXCERPT_CHARS = 550
                FETCH_WINDOWS_PER_PAGE = 3
                FETCH_PLAIN_CHARS = 6500
                ANSWER_CHAR_CAP = 60000
                CITATION_CAP = 24
                EVIDENCE_CHAR_BUDGET = 105000
                AUDIT_MIN_USD = 0.05
                WRAPUP_MIN_USD = 0.02
                BRIEF_MIN_USD = 0.03
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
                LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'search_many', 'description': 'Run up to 8 web searches in parallel. Use to enumerate or verify a whole candidate set / metric panel in one step.', 'parameters': {'type': 'object', 'properties': {'queries': {'type': 'array', 'items': {'type': 'string'}, 'description': 'up to 8 search queries'}}, 'required': ['queries']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}]
                LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.\n\n## Pairwise Scoring Rules\n- Decompose every sub-fact/filter; never answer dates/counts/rankings/names from memory.\n- Full roster: enumerate the COMPLETE candidate pool, evaluate EVERY candidate, cite qualifiers AND closest exclusions with the failing value.\n- Literal comparators (`more than 25` is strict >); inclusive ranges; convert rates to integer tests.\n- False premise: first line corrects with a citation — never refuse or answer `evidence missing`.\n- Exact values verbatim with units; no rounding.\n- Commit: partial cited answer beats refusal; cover every asked sub-question.\n- Citations: `[n]` after every load-bearing claim (winners AND exclusions); quality over spam.\n- Batch lookups: prefer `search_many` (or multiple tool calls in one turn) for independent queries.\n'

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

                async def _do_search(query_text: str) -> 'ToolOutput | str':
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

                async def _do_search_many(queries, ledger=None, budget_s: float=0.0, *args, **kwargs):
                    clean = []
                    for q in queries or []:
                        text = str(q).strip()
                        if text and text not in clean:
                            clean.append(text)
                    clean = clean[:8]
                    if not clean:
                        return '# search_many() -> ERROR: no queries'

                    async def _one(q: str):
                        try:
                            return await _do_search(q, budget_s=budget_s or 0.0)
                        except TypeError:
                            pass
                        if ledger is not None:
                            try:
                                return await _do_search(q, ledger)
                            except TypeError:
                                pass
                        return await _do_search(q)
                    parts = await asyncio.gather(*(_one(q) for q in clean), return_exceptions=True)
                    merged_rows = []
                    blocks = []
                    for q, p in zip(clean, parts):
                        if isinstance(p, Exception):
                            blocks.append(f'# web_search({q!r}) failed: {p}')
                            continue
                        if isinstance(p, str):
                            blocks.append(p)
                            continue
                        text = getattr(p, 'text', None)
                        rows = getattr(p, 'rows', None)
                        if text is None and isinstance(p, dict):
                            text = p.get('text', '')
                            rows = p.get('rows', [])
                        if text is None:
                            blocks.append(f'# web_search({q!r}): no citable results')
                            continue
                        rows = rows or []
                        offset = len(merged_rows)
                        for local_i in range(len(rows) - 1, -1, -1):
                            text = text.replace(_SLOT.format(local_i), _SLOT.format(local_i + offset))
                        merged_rows.extend(rows)
                        blocks.append(text)
                    joined = '# search_many(%d queries)' % len(clean) + chr(10) + (chr(10) * 2).join(blocks)
                    try:
                        return ToolOutput(joined, merged_rows)
                    except NameError:
                        pass
                    try:
                        return _tool_output(joined, merged_rows)
                    except NameError:
                        pass
                    return joined

                async def _do_fetch(url: str, focus: str, question: str) -> 'ToolOutput | str':
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
                            if len(_SEC_CACHE) >= _SEC_CACHE_MAX and url not in _SEC_CACHE:
                                keep = _SEC_CACHE.get(_SEC_TICKERS_URL)
                                _SEC_CACHE.clear()
                                if keep is not None:
                                    _SEC_CACHE[_SEC_TICKERS_URL] = keep
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

                async def _run_tool(call, question: str, deadline: float) -> 'ToolOutput | str':
                    try:
                        args = json.loads(getattr(call, 'arguments', None) or '{}')
                    except Exception:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}
                    name = getattr(call, 'name', '') or ''
                    if name == 'web_search':
                        return await _do_search(str(args.get('query') or ''))
                    if name == 'search_many':
                        qs = args.get('queries') or []
                        return await _do_search_many(qs if isinstance(qs, list) else [qs], ledger)
                    if name == 'read_page':
                        return await _do_fetch(str(args.get('url') or ''), str(args.get('focus') or ''), question)
                    if name == 'sec_filing':
                        return await _do_sec_filing(str(args.get('company') or ''), str(args.get('form') or ''), str(args.get('year') or ''), deadline)
                    return f'# unknown tool {name!r}'
                _REASONING_MANDATORY = ('openai/gpt-oss',)

                def _least_think(model: str) -> dict:
                    for prefix in _REASONING_MANDATORY:
                        if model.startswith(prefix):
                            return {'enabled': True, 'effort': 'low'}
                    return {'enabled': False}

                def _first_message(llm):
                    choices = getattr(llm, 'choices', None) or []
                    if not choices:
                        return None
                    return getattr(choices[0], 'message', None)

                def _message_text(msg) -> str:
                    content = getattr(msg, 'content', None)
                    if isinstance(content, str):
                        return content.strip()
                    return ''

                def _payload_text(payload) -> str:
                    llm = getattr(payload, 'llm', None)
                    text = (getattr(llm, 'raw_text', None) or '').strip()
                    if text:
                        return text
                    return _message_text(_first_message(llm))

                async def _chat_simple(model: str, system: str, user: str, *, max_tokens: int, timeout: float, think: dict | None=None) -> str:
                    if think is None:
                        think = _least_think(model)
                    payload = await llm_chat(provider=LLM_PROVIDER, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=think)
                    _spend_note(payload)
                    return _payload_text(payload)

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
                    for attempt, model in enumerate((LOOP_MODEL_A, LOOP_MODEL_B)):
                        is_fallback = attempt > 0
                        if is_fallback and payload_chars > FALLBACK_MAX_PAYLOAD_CHARS:
                            return _EMPTY_TURN
                        timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0)
                        if timeout <= 5.0:
                            return None
                        try:
                            payload = await llm_chat(provider=LLM_PROVIDER, model=model, messages=messages, tools=LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': True, 'effort': 'low'}, max_output_tokens=None, timeout=timeout)
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
                        raw = await _chat_simple(LOOP_MODEL_A, system, user, max_tokens=2400, timeout=BRIEF_TIMEOUT_S, think=_least_think(LOOP_MODEL_A))
                    except Exception:
                        try:
                            raw = await _chat_simple(LOOP_MODEL_B, system, user, max_tokens=2400, timeout=BRIEF_TIMEOUT_S, think=_least_think(LOOP_MODEL_B))
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
                            out = await asyncio.wait_for(_do_search(seed), timeout=SEARCH_TIMEOUT_S * 2 + 6.0)
                            blocks.append(_commit_tool_output(out, ledger))
                        except Exception:
                            continue
                    good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
                    if not good:
                        return ''
                    return 'Automatic first-pass searches (already numbered — cite these [n] directly, and search further as needed):\n\n' + '\n'.join(good)

                async def _tool_phase(calls, question: str, ledger: EvidenceLedger, deadline: float) -> list[dict]:
                    run_calls = calls[:MAX_TOOL_CALLS_PER_TURN]
                    tool_budget = max(5.0, min(FETCH_TIMEOUT_S * 2 + 6.0, deadline - monotonic() - MIN_TAIL_S))
                    tool_tasks = [asyncio.ensure_future(_run_tool(c, question, deadline)) for c in run_calls]
                    try:
                        await asyncio.wait(tool_tasks, timeout=tool_budget)
                    except Exception:
                        pass
                    results = []
                    for task in tool_tasks:
                        if task.done():
                            try:
                                results.append(task.result())
                            except Exception as exc:
                                results.append(f'# tool crashed: {exc}')
                        else:
                            task.cancel()
                            results.append('# tool timed out — use what you already have')
                    replies: list[dict] = []
                    for call, result in zip(run_calls, results):
                        replies.append({'role': 'tool', 'tool_call_id': call.id, 'content': _commit_tool_output(result, ledger)})
                    for call in calls[MAX_TOOL_CALLS_PER_TURN:]:
                        replies.append({'role': 'tool', 'tool_call_id': call.id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})
                    return replies

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
                        msg = _first_message(getattr(payload, 'llm', None))
                        if msg is None:
                            break
                        calls = getattr(msg, 'tool_calls', None) or ()
                        if not calls:
                            candidate = _payload_text(payload)
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
                        messages.extend(await _tool_phase(calls, question, ledger, deadline))
                    return (answer, messages)

                async def _claim_gap_reresearch(question: str, answer: str, messages: list[dict], ledger, deadline: float) -> str:
                    from time import perf_counter as _pc
                    rem = deadline - _pc()
                    if not (answer or '').strip() or rem < 50.0:
                        return answer
                    user = f'Output JSON ONLY: {{"gap_queries":[...up to 4 search queries to close missing elements, uncited facts, comparison sides, or exclusions...]}}. Use [] if complete.\n\nQuestion:\n{question}\n\nDraft:\n{answer[:10000]}'
                    provider = 'openrouter'
                    model = 'openai/gpt-oss-120b'
                    try:
                        chat = await llm_chat(provider=provider, model=model, messages=[{'role': 'system', 'content': 'Claim-gap planner. JSON only.'}, {'role': 'user', 'content': user}], tools=None, temperature=0.1, max_output_tokens=500, timeout=min(25.0, rem - 20))
                        raw = (chat.response.raw_text or '').strip()
                        cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw, flags=re.I | re.M)
                        report = json.loads(cleaned)
                        queries = report.get('gap_queries') if isinstance(report, dict) else None
                    except Exception:
                        return answer
                    clean = [str(q).strip() for q in queries or [] if str(q).strip()][:4]
                    if not clean or deadline - _pc() < 35.0:
                        return answer
                    try:
                        evidence = await _do_search_many(clean, ledger)
                    except TypeError:
                        try:
                            evidence = await _do_search_many(clean)
                        except Exception:
                            try:
                                parts = []
                                for q in clean:
                                    try:
                                        parts.append(await _do_search(q, ledger))
                                    except TypeError:
                                        try:
                                            parts.append(await _do_search(q, budget_s=0.0))
                                        except TypeError:
                                            parts.append(await _do_search(q))
                                evidence = '\n\n'.join((str(p) for p in parts))
                            except Exception:
                                return answer
                    except Exception:
                        return answer
                    messages.append({'role': 'system', 'content': '## Claim-gap forced evidence\n' + str(evidence) + '\n\nRewrite COMPLETE final answer with [n] citations including exclusions.'})
                    try:
                        rewrite = await llm_chat(provider=provider, model=model, messages=messages + [{'role': 'user', 'content': 'Write the complete final answer now. No tools.'}], tools=None, temperature=0.2, timeout=min(40.0, max(10.0, deadline - _pc() - 5)))
                        cand = (rewrite.response.raw_text or '').strip()
                        if cand:
                            return cand
                    except Exception:
                        pass
                    return answer

                async def _audit_patch(question: str, answer: str, messages: list[dict], ledger: EvidenceLedger, deadline: float) -> str:
                    probe = f"""Audit the answer against the question. JSON only, keys: "unanswered_parts" (list; question elements not addressed), "uncited_facts" (list; load-bearing claims without [n]), "wrong_kind" (list; places where the named entity is a different KIND than the question asks — a person instead of a series, a duo instead of a show), "incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges over a candidate pool — a closed set that can be enumerated, or several conditions applied to a class — then: is the pool itself stated and plausibly COMPLETE, and does the answer give a verdict for EVERY member (qualifies / excluded because X, each cited)? Name any pool member the answer never mentions, and say so if the pool looks truncated — an answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not partial), "thin_proof" (list; a qualifier lacking a per-condition citation, or a plausible near-miss candidate never addressed), "hand_waved_tally" (list; for a superlative/count/most-common question: the answer asserts a winner or a count WITHOUT showing the candidate table it was derived from. Phrases like 'among others', 'and several more', 'multiple X', or naming 2 examples to justify a count are all hand-waving — say so and name what the tally must list). Empty lists when clean.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:11000]}"""
                    try:
                        raw = await _chat_simple(AUDIT_MODEL, 'Strict completeness auditor. JSON only.', probe, max_tokens=2200, timeout=max(8.0, min(AUDIT_TIMEOUT_S, deadline - monotonic() - 72.0)))
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
                _BRACKET_FIX.update({65296 + d: chr(48 + d) for d in range(10)})

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

                def _deterministic_answer(ledger: EvidenceLedger) -> str:
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
                    ask = f'Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'
                    for i, model in enumerate((LOOP_MODEL_A, LOOP_MODEL_B)):
                        left = deadline - monotonic()
                        if left < 14.0:
                            return ''
                        budget = min(RESCUE_TIMEOUT_S, left - DIGEST_TAIL_S)
                        if i == 0:
                            budget = min(budget, max(12.0, left - 14.0 - DIGEST_TAIL_S))
                        if budget < 8.0:
                            return ''
                        try:
                            text = await _chat_simple(model, _COMMIT_RULES, ask, max_tokens=2600, timeout=budget)
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
                        return await _chat_simple(RESORT_MODEL, 'Expert researcher. Best definitive answer with concrete entities, numbers, dates. Never refuse.', question, max_tokens=2600, timeout=min(45.0, left - 4.0))
                    except Exception:
                        return ''

                async def _schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
                    ask = f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}'
                    for model in (SCHEMA_MODEL, RESORT_MODEL, LOOP_MODEL_A):
                        left = deadline - monotonic()
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
                            try:
                                patched = await _claim_gap_reresearch(question, patched, messages, ledger, deadline)
                            except Exception:
                                pass
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
                        det = _deterministic_answer(ledger)
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
                            basis = _deterministic_answer(ledger)
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
                _PERFECT_SUFFIX = '5db92afc57ac10c3'
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
                VERSION = 'chronicle-v36-fusion'
                SUBMISSION_HOTKEY = 'harnyx_v3'
                PROBE_VENDOR = 'parallel'
                PROBE_LIMIT = 10.0
                PULL_LIMIT = 15.0
                ENGINE_LIMIT = 90.0
                VECTOR_LIMIT = 120.0
                CUTOFF_WARNING_SECS = 150.0
                CHRONICLE_BATCHED_PREVIEW_SIZE = 240000
                CHRONICLE_VIEW_SHEET_SIZE = 80000
                CHRONICLE_FOCUS_MEMORY_SIZE = CHRONICLE_VIEW_SHEET_SIZE
                CHRONICLE_VSEARCH_SHEET_SIZE = 60000
                CHRONICLE_SIM_FLOOR_BLOCKS = 3
                CHRONICLE_SIM_TOP_BLOCKS = 5
                CHRONICLE_SIM_FINDING_SIZE = 45000
                CHRONICLE_LEX_PANE_SIZE = 3600
                CHRONICLE_LEX_PANE_TALLY = 3
                CHRONICLE_GPTOSS_TOP_SHAPE_TOKENS = 65536
                CHRONICLE_OR_GEMMA_TOP_SHAPE_TOKENS = 40960
                CHRONICLE_AG_GEMMA_TOP_SHAPE_TOKENS = 131072
                CHRONICLE_GLM5_TOP_SHAPE_TOKENS = 131072
                CHRONICLE_INKLING_TOP_SHAPE_TOKENS = 131072
                CHRONICLE_ENGINE_SCHED = 'state_aware'
                CHRONICLE_PROBE_ENGINES = ('glm5', 'ai_gateway_gemma', 'inkling')
                BOARD_AWARE_CHRONICLE_PROBE_ENGINES = ('openrouter_gemma', 'ai_gateway_gemma', 'openrouter_gemma_stable', 'glm5', 'inkling')
                CHRONICLE_NEED_ENGINES = ('openrouter_gemma', 'ai_gateway_gemma', 'openrouter_gemma_stable', 'glm5')
                CHRONICLE_FIX_ENGINES = ('openrouter_gemma', 'ai_gateway_gemma', 'openrouter_gemma_stable', 'glm5', 'inkling')
                CHRONICLE_REVIEW_ENGINES = ('inkling', 'openrouter_gemma', 'ai_gateway_gemma', 'openrouter_gemma_stable', 'glm5')
                PROOF_VET_ENGINES = CHRONICLE_PROBE_ENGINES
                VECTOR_SPARE = {'provider': {'only': ['nebius', 'deepinfra', 'siliconflow'], 'allow_fallbacks': True}}
                OPENROUTER_GLM_VENDOR_PREFS = {'provider': {'only': ['amazon-bedrock'], 'allow_fallbacks': True}}
                OPENROUTER_GPT_VENDOR_PREFS = {'provider': {'only': ['cerebras', 'baseten', 'deepinfra', 'sambanova', 'nebius', 'coreweave'], 'allow_fallbacks': True}}
                CHRONICLE_OR_GEMMA_VENDOR_PREFS = {'provider': {'only': ['sambanova'], 'allow_fallbacks': False}}
                CHRONICLE_OR_GEMMA_STABLE_VENDOR_PREFS = {'provider': {'only': ['modelrun'], 'allow_fallbacks': False}}
                FORECAST_VERDICT_BRIEF = 'You are beginning a deep-research task. Before using external sources, write the best expected answer your internal\nknowledge suggests. This is a revisable research hypothesis, not evidence.\n\nWrite a concise working hypothesis that names the likely answer and the main uncertainty. Also state the smallest\nverification route: the finite candidate inventory, if one is needed, and the exact external facts that would prove\nor disprove the hypothesis. Name useful sources or pages, but do not produce or guess URLs; retrieval discovers exact\nURLs. This route is a heuristic for investigation, not evidence. For an exhaustive question, put the inventory source\nbefore per-candidate metric lookups. Be concrete enough that later investigation can prove, revise, or reject the\nanswer. Do not invent citations and do not avoid an answer merely because important facts remain uncertain.\n\nAfter the hypothesis, write a short BRIEFING block with:\n- CANDIDATE POOL: the finite set the question ranges over, or the inventory source that lists it.\n- KEY FACTS: the numeric/geographic/date values that decide the answer.\n- LOOKUPS: 2-5 precise search queries to verify these facts, including official sources.\n- WATCH OUT: any condition that is easy to mis-scope (year, column, boundary, named source).'
                DEMANDS_ORDER = 'Before retrieval, call set_evidence_requirements once. Write one evidence question per line, leaving its answer blank.\nEach question must ask for an externally verifiable premise that the final answer needs. Do not write a search plan,\nsource description, table schema, or list of raw data to collect. No external evidence exists yet: never insert a\ncandidate, number, list member, answer, expected value, or proposition that the original question does not supply.\n\nDo not list arithmetic, set intersection, decade membership, threshold comparison, sorting, or another conclusion\nthat can be mechanically derived from externally supported operands as a separate evidence question. Ask for the\nexternal operands that the derivation requires. The derivation itself does not require an external source.\n\nSplit a person\'s role, relationship, date, and each required property of an institution into separate questions. Treat\nwording and named items supplied by the question as given. A person\'s role at an institution, the institution\'s type\nor status, and its location are separate evidence questions. For an exhaustive result, ask for the external operands\nneeded to establish the complete result, but prefer questions that return a complete filtered set over questions that\nrequest every raw value for every candidate. For an intersection of conditions, ask first for the complete result of\nthe most selective condition, then ask the remaining conditions only about candidates that survive earlier filters.\nThose later questions may be conditional and must not guess who the survivors are. Do not create a separate question\nasking whether a source or set is complete; the final audit judges whether the observed source scope is sufficient.\nWhen the original question explicitly requires retrieval from a named source, edition, page, report, or dataset, that\nsource and scope remain a required premise even if another filter could establish the same conclusion.\nAn identification question does not assert uniqueness: the phrase "the person" is grammatical, not an exhaustive\ncondition. Unless the question explicitly says only, unique, all, every, asks how many, or otherwise requires an\nexhaustive result, never require proof that no other person matches. Do not require every value for every nonqualifying\ncandidate; a candidate may be eliminated by one supported condition and only surviving candidates need the remaining\nchecks.\n\nBad requirement: "North Carolina had fatalities from Hurricane Nicole."\nGood requirement: "Which states had direct or indirect fatalities across the named 2022 storms?"\nGood requirement: "Which states had direct or indirect fatalities across the named 2023 storms?"\nBad for "Identify the person who has A and B": "Exactly one person satisfies A and B."\nGood: "Which identified person has A?" and "Which identified person has B?" '
                DEMANDS_BRIEF = 'Define the unanswered evidence questions that a complete answer to the original question must resolve. Base them only\non the original question; no expected answer or candidate hypothesis is available.\n\n' + DEMANDS_ORDER
                PURSUIT_BRIEF = "You are a deep-research agent. Develop a claim that answers the original question and give it enough externally\ninspectable support to persuade a skeptical reader.\n\nThe expected answer is a useful guess, not evidence. Use it to choose cheap, focused searches. Revise or replace it\nwhen observed sources disagree, reveal a better answer, or expose a missing condition. Internal knowledge may guide\nresearch, but every material external premise in the final claim needs observed support.\nWhen the question attributes facts to a named source, edition, page, report, or dataset, inspect that named source\nbefore accepting a substitute. Otherwise prefer the organization that produced the fact, an official record, or a\nprimary document over an aggregator or commentary. Begin retrieval with the named or primary source and the exact\nsubject; use secondary sources for discovery only when the direct source cannot yet be found. If the publisher page\nis unavailable, prefer an archived copy of that exact page over a third-party reproduction.\nDo not finalize from a secondary source when the observed search results already contain an accessible official or\nprimary source for the same decisive premise. Inspect the direct source first; retain the secondary source only when\nthe direct source still lacks the necessary text or scope after inspection.\nIf a clue-only search does not improve the evidence, do not paraphrase and repeat it. Change the evidence route or\ntest the expected-answer candidate directly.\nIf a required source's search surface does not expose a complete inventory, use a suitable secondary source to\ndiscover a finite candidate set, then verify each surviving candidate against the required source. A discovery source\nis a research aid, not final support for a premise the question explicitly attributes to the required source.\nFor an exhaustive question, the expected candidate pool remains unproved. Before finalizing, inspect either a source\nthat enumerates the pool or direct evidence for every candidate and plausible boundary case; metric pages for guessed\ncandidates alone do not prove that no candidate is missing.\nWhen a table explicitly ranks rows in descending order by the same numeric metric used by the question's threshold,\nyou do not need every later row after the first below-threshold row. Retain the header, every row through that boundary,\nand explain why the established ordering eliminates the remaining lower-ranked rows. This shortcut is valid only when\nthe visible header and row order establish that monotonic relationship.\n\nRANK / TOP-N / CUTOFF RULE: When the question asks for a top-N, an N-th place, or a highest/lowest value within a set,\nwrite a single Markdown table with the candidate pool ranked by the deciding metric. Every row must show: candidate name,\nmetric value, and a source ref. Do not finalize until the table is complete and the answer's chosen candidate matches the\nranked table.\n\nSET / FILTER RULE: When the question asks for all/every/which N/identify the set, enumerate the entire candidate pool in a\ntable before applying filters. Then show the filtered set and one excluded near-miss with the condition that excludes it.\nEach surviving candidate must have its own citation; one citation for the whole set is not enough.\n\nSOURCE-DIVERSITY RULE: If the only cited carrier for a decisive claim is Wikipedia or another aggregator, fetch or search\nfor the original publisher (gov, org, official stats, academic source) and cite that instead. Wikipedia-only is acceptable\nonly for incontroversial background, never for the deciding fact.\n\nSearch snippets are evidence when their visible text directly supports the premise. If later retrieval steps must\ncombine that snippet with other facts, retain its smallest decisive lines before moving on; otherwise the full snippet\nmay leave active context while remaining available in VFS. Among observed sources with comparable authority and scope,\npreserve the excerpt that states the complete needed premise most directly and compactly. Do not fetch a broader copy\nmerely to replace a sufficient snippet. A search result from the named official page counts as inspection when its\nvisible text supplies the needed fact; retain that snippet rather than fetching the same page solely because the\nquestion names it. Use fetch_page only when the snippet lacks necessary context or when inspecting a discovered page\nis the most direct remaining evidence route. fetch_page accepts a full URL, including one discovered inside a search\nresult or another page. Do not construct a URL from a guessed site pattern.\nSearch and fetch results are saved in VFS. On a long page, locate relevant lines with VFS search before using VFS read\nto expand a small window. A large fetch includes question-ranked context windows in addition to its head/middle/tail\npreview; inspect those windows before searching the page again. Give each VFS search both an exact regex pattern and\na semantic query. The harness starts with regex and automatically adds embedding results only when regex fails or\nfinds nothing. For a table, keep the relevant row together with its title, series labels, year labels, and headers.\nPDF extraction can place chart values before the heading or labels they belong to. When a title match lacks its data,\ninspect both before and after it rather than assuming the table follows the title. You may reconstruct a flattened\nchart only when the excerpt exposes a complete rectangle: N ordered category labels, M series labels, and exactly M\ngroups of N data values after excluding axis ticks. State that mapping explicitly and cross-check it against the page\nheading, totals, shares, or nearby prose. If the complete structure is not visible, do not infer a cell from line order.\nWhen the question asks about a specific date, edition, or historical version, inspect a result whose title and scope\nmatch that exact period before broader or current-data pages. Do not revise a period-specific value from a source that\nvisibly describes a different period. A current rolling statistical table may revise rows labeled with past dates;\nwhen the question concerns what was reported for that period, prefer the contemporaneous archived release.\nWhen inspected sources disagree, resolve the conflict by source scope, authority, date, and fit to the question. If\none source states the question's identifying conditions and requested value together, preserve that internally\nconsistent account. A differently scoped or measured value is a limitation to disclose, not a reason to repeat\nsubstantially equivalent searches. Once further searches only reproduce the same conflict, finalize the best-supported\nanswer and state the discrepancy briefly.\nThe initial evidence questions guide retrieval; they are not a checklist that must remain material. A complete filter\nor supported elimination can make a broader question unnecessary. An explicit instruction in the original question\nto retrieve or report from a named source, edition, page, report, or dataset remains material and cannot be replaced\nby a different proof route. Before finalizing, check every premise that the current answer and its derivation actually\ndepend on against words or table cells visible in the supplied source records. Your memory of a source is not visible\nevidence. If a material row or relationship is absent from the excerpt, locate it with VFS search or fetch the\ndiscovered page; if it remains unavailable, state the limitation instead of silently supplying it.\n\nUse update_research_state whenever evidence changes the current best answer, the decisive support, or the most\nimportant unresolved question. This prose state is your working memory and is returned on every turn. Do not turn it\ninto a search log. Retain only displayed lines that directly support or contradict a material premise; do not retain a\nsource merely for possible later extraction. For a flattened table or chart, retain one continuous range containing\nthe data values, ordered category labels, series labels, and title together, even when axis ticks or spacing lie\nbetween them. Isolated number lines plus a separate title do not preserve the mapping needed to support table claims.\nFor a descending ranked table filtered by a numeric threshold, retain one continuous range from the header through\nthe first below-threshold row so the qualifying rows and the exhaustive cutoff remain inspectable together.\n\nContinue while a real uncertainty could change the answer. Before finalizing with evidence from a fetched page,\npreserve every decisive excerpt with retain_evidence. When the claim resolves the question and its material premises\nare supported, call ready_to_finalize as the final tool in the response. Its reason explains the derivation and cites\nsource references such as [P1] or [S1.2], without encoding line ranges in prose. The harness writes the answer from\nthe cited source records. A decisive search snippet may be cited without retention only when finalizing immediately;\nretain it before performing later retrieval that must be combined with it.\n\nTool failures are observations: correct the call or change approach. Tool calls in one response execute sequentially,\nso a later call must not depend on a result not yet seen. When exact arguments for several independent fetches, reads,\nor evidence retentions over an already known finite candidate set are available, emit them together in one response.\nDo not batch alternative searches for the same uncertainty: run one search and inspect its results before trying\nanother evidence route. Emit each distinct operation at most once per response."
                VERDICT_REVISE_BRIEF = 'Write the complete best current answer to the original question as polished, reader-facing Markdown. Obey any\nexplicit output-only or formatting constraint in the original question; otherwise use substantial prose with\nstructure proportional to the answer. The expected answer, prior answer, investigator prose, and your internal\nknowledge are not evidence. Use only the supplied source records.\n\nThe investigator\'s current conclusion is the intended answer and derivation after research. Use it to revise the\nprior answer, while checking every external premise against the supplied source records. Do not add factual claims\nthat are unnecessary to establish the answer; for an excluded candidate, state its decisive failing condition rather\nthan unrelated background.\n\nOpen with the direct conclusion. Use short descriptive headings when they help navigation, bullets for parallel\nfindings, and a Markdown table when several candidates share the same comparison fields. Do not force a heading or\ntable onto a short answer. Keep paragraphs focused and make the decisive comparison easy to scan. Do not add a\nreferences section, bibliography, source dump, raw URL, or quoted evidence appendix.\n\nResolve the question directly, explain why the conclusion follows, and preserve relevant uncertainty. Place the\nexact internal source reference from the supplied record, such as [S1.2] or [P3], immediately after the factual claim\nit supports. These references are private placeholders that the harness converts to public citation numbers. Never\ninvent a reference, alter its spelling, or write a numeric citation marker yourself. A derived claim needs no separate\nreference when all external operands are visibly supported nearby and the derivation is explicit. Name a source\norganization naturally only when it helps explain why the evidence is authoritative. A table-derived value is\nsupported only when the supplied text preserves its association with the relevant row and column labels. Never assign\na value to a year, category, or candidate that the source record does not visibly associate with that value. A\ncsv_records field is a mechanical projection of a CSV header onto its selected rows; prefer its named fields over\ncounting positions in the raw CSV quote. For each premise, rely on the single most direct source that visibly\nestablishes it. Add another source only when the first source cannot establish the whole premise; do not rely on weaker\nduplicates or merely corroborating background. When sources report conflicting measurements, prefer an internally\nconsistent source record that establishes the question\'s identifying conditions and requested value together. Do not\ncombine a conflicting measurement from one source with the answer supplied by another; mention a material discrepancy\nbriefly only when it affects interpretation. If the question asks what a source explicitly reports, state that\nreported value and compare it directly; do not add a recomputation that answers a different question. When a\nthreshold, ranking, ratio, or arithmetic operation decides the answer, show the relevant input\nvalues and write the arithmetic expression or comparison for every candidate needed to establish the result (for\nexample, `105 - 81 = 24`, not only the two scores and the resulting margin). Prefer an exact calculated value over an\nindirect inequality when the supplied operands allow the calculation. When the conclusion is\nexhaustive (for example, only, all, closest, a top-k set, or an intersection), show enough of the candidate comparison\nin the answer to establish that no omitted candidate changes the result. Open with the direct answer, then explain the\ndecisive evidence and derivation in natural prose. Do not expose research-process labels such as candidate pool,\nboundary check, proof of completeness, evidence requirement, audit, or research state. For an exhaustive answer,\nidentify the finite set naturally, show each qualifying entity\'s decisive values, and mention only the near misses\nneeded to establish the boundary. An inventory source can bound the set, but independently verified candidate pages\nand boundary near misses can do so when no single inventory page is available. Apply strict inequalities literally:\nstate the strictly qualifying set first, and describe an equal boundary value only as an excluded case. For an\nidentification or constraint question, explicitly show how the answer satisfies every condition in the original\nquestion, including descriptors and relationships. When the question asks to retrieve a finite set and then filter\nit through multiple conditions, show the materially narrowed set after each decisive filter, not only the final\ncandidate\'s properties.\n\nGood citation placement: `Essendon won 105-81 in 1984. [P1]`\nFor a Markdown table, place the source reference in each source-backed row, normally in its final relevant cell. Never\nput the only reference for several table rows on a separate line below the table.\nBad: a final `ChronicleSources` list, a raw URL, an invented `[1]`, a citation-only line below a table, or a claim whose only\nreference appears several paragraphs later.\n\nANSWER FORMAT: Begin the final answer with a single locked headline: `FINAL ANSWER: <answer in requested format>`.\nThen add a `Proof of completeness:` section. For an exhaustive/filtered/ranked question, this section must contain a\nMarkdown table with every candidate, its decisive value, and a PASS/FAIL verdict per condition. Name the first excluded\nnear-miss and the value that disqualifies it. Remove all hedge words (appears to be, likely, probably), all self-critique\nphrases ("The current answer mixes...", "This is confusing"), and any "process" narration. Every factual claim in both\nthe headline and the proof must carry a source ref immediately after it.'
                SHAPED_SHAPE_BRIEF = "Materialize a completed, evidence-backed research answer as the caller's structured output. Do not research again,\nadd facts, explain your process, or return prose outside the tool call. Preserve the answer's meaning and include every\nfield required by the supplied JSON Schema. Call submit_structured_output exactly once. The tool arguments are the\nfinal output value, not JSON encoded inside a string."
                REVIEW_BRIEF = "Audit an answer against supplied external evidence. The answer may contain the correct values attached to the wrong\ndates, columns, categories, candidates, or relationships.\n\nReconstruct the source facts before accepting any claim from the answer. A value has a year, column, category, or role\nonly when the visible source text preserves that association. Do not infer a table header across omitted lines or from\nthe answer itself. A csv_records field is a mechanical projection of a CSV header onto its selected rows; use its named\nfields instead of counting positions in the raw CSV quote. For every candidate that could affect the result, treat each\ncondition in the question as supported true, supported false, or unknown. Absence of evidence is unknown, not false.\n\nFor an identification question, audit every descriptive clause as a separate premise. Evidence that a person is\naffiliated with an institution does not establish the institution's location, type, or status. If the supplied source\nrecords do not explicitly establish such a property required by the question, mark it unknown and return CONTINUE.\nWhen the question identifies an entity indirectly through a quotation, work, event, or relationship, the mapping\nfrom that clue to the identified person or entity is itself a material premise. Require visible evidence for that\nmapping even when it is familiar or stated as part of the question; evidence for the resulting name alone does not\nestablish why it matches the clue.\nWhen the original question explicitly requires retrieval or reporting from a named source, edition, page, report, or\ndataset, verify that the supplied records establish that source and scope. A substitute source does not satisfy that\ninstruction even when it supports the same conclusion. The source inventory is discovery metadata, not evidence. If\nthe answer relies on a substitute while the inventory exposes a result from the required publisher with matching\nscope, return CONTINUE and name that one direct result for inspection. Do not request a stronger duplicate merely\nbecause one may exist when the question does not require a named source or scope.\n\nChronicleSource omission proves absence only when the source visibly represents a complete inventory at the required scope.\nA candidate excluded by one supported condition does not need evidence for the other conditions. When a surviving\ncandidate has multiple unknown conditions, request only the single cheapest observation that could exclude it or move\nit forward; do not mark later conditions missing until the candidate survives that check. A CONTINUE audit must\ncontain exactly one MISSING line, and it must match the one observation named in the verdict.\nRows separated by a visible `...` are not adjacent. Do not reconstruct ordinal ranks or a ranking cutoff by joining\nthe rows on either side; return CONTINUE if omitted rows could change the result.\nA complete comparison on one condition may reduce the candidate set, after which only the survivors need support for\nthe remaining conditions. Do not require a full candidate-by-condition matrix when supported elimination establishes\nthe same conclusion.\nDo not combine an eligibility condition from one source with a requested value from another source when their\nmeasurements conflict. If one supplied source record states all identifying conditions and the requested value\ntogether, preserve that internally consistent account. Treat a differently scoped or measured record as a\ndiscrepancy, not as an operand for a hybrid answer.\nNever approve or write a replacement that keeps a candidate as the answer while its chosen evidence account makes\nthat candidate fail a selection condition. Use a supplied internally consistent account that establishes both\neligibility and the requested value, or return CONTINUE when no such account is available.\n\nBefore deciding, identify only:\n- factual premises asserted by the current answer; and\n- unresolved facts whose truth could change the answer to the original question.\n\nDo not audit an initial research plan or require facts that are no longer material to the conclusion. Write one short\nline for each material premise or result-changing unknown. Use exactly one of:\nSUPPORTED [source ref]: <the visible source words that establish this premise>\nDERIVED [source refs]: <the arithmetic or logical derivation from externally supported operands>\nMISSING: <the premise not explicitly established by any supplied source record>\nCONTRADICTED [source ref]: <the visible source words that contradict this premise>\n\nEmit a MISSING line only for a real unresolved premise. If nothing is missing, omit MISSING entirely; never write\n`MISSING: none`, `MISSING: not applicable`, or another empty placeholder. A READY verdict must contain no MISSING line.\nDo not combine premises on one line. A source ref without the establishing words is not support. Use only the\nsupplied source records; the answer and internal knowledge are not evidence. A contradicted condition for an excluded\ncandidate can support the answer's exclusion; it is not itself an answer error. Arithmetic, set operations, decade\nmembership, threshold comparisons, and ordering may be DERIVED without another external citation when every external\noperand is SUPPORTED. A DERIVED line must show the calculation or logical step and cite the source refs containing its\nexternal operands; never use DERIVED to supply a missing external operand. A value that is completely calculable from\nsupported external operands is not missing merely because no source states the calculated value verbatim. Mark that\npremise DERIVED, not MISSING, and do not emit both statuses for the same premise.\nA familiar categorical property may also be DERIVED from explicit defining source facts when the classification is\nunambiguous; show those facts instead of requiring the source to use the question's exact label.\n\nAfter all premise lines, emit exactly one verdict:\nVERDICT READY\nVERDICT CONTINUE: <the one most important missing observation>\nVERDICT REVISE\n<a complete replacement answer with exact supplied source refs such as [P1]>\n\nUse READY only if every factual statement agrees with the reconstructed source facts, the conclusion follows, and no\nunknown could change the result. READY and REVISE are invalid if a material premise is MISSING. A source\ncontradiction to a factual statement asserted by the current answer requires REVISE, while a contradiction that\nestablishes why a candidate is excluded is compatible with READY. Use REVISE only when the supplied evidence settles\nthe question but the answer is wrong or unsupported. The replacement must cite exact supplied source refs after its\nsupported factual claims. Begin it with the corrected conclusion and do not repeat the old answer or discuss the\ncorrection process. Use CONTINUE when the evidence cannot settle the result."

                def _contract(label: str, description: str, properties: dict[str, Any], required: tuple[str, ...]) -> dict[str, Any]:
                    return {'type': 'function', 'function': {'name': label, 'description': description, 'parameters': {'type': 'object', 'properties': properties, 'required': list(required), 'additionalProperties': False}, 'strict': False}}

                def _decode_csv_row(row_x: str) -> list[str] | None:
                    fields: list[str] = []
                    field: list[str] = []
                    in_quotes = False
                    after_quote = False
                    index = 0
                    while index < len(row_x):
                        character = row_x[index]
                        if in_quotes:
                            if character != '"':
                                field.append(character)
                            elif index + 1 < len(row_x) and row_x[index + 1] == '"':
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
                SET_PROOF_DEMANDS_OP = _contract('set_evidence_requirements', 'Record only unanswered evidence questions whose externally verifiable premises the final answer needs. Do not record source availability, table structure, or retrieval work.', {'requirements': {'type': 'string', 'minLength': 1, 'description': 'One unanswered evidence question per line, with no candidate or expected answer filled in.'}}, ('requirements',))
                DEMANDS_OPS = [SET_PROOF_DEMANDS_OP]
                OP_CATALOG = [_contract('search_web', 'Search the web. Full results are retained in VFS and each result receives a source reference.', {'query': {'type': 'string', 'minLength': 1}, 'num': {'type': 'integer', 'minimum': 1, 'maximum': 25}}, ('query', 'num')), _contract('fetch_page', 'Fetch one full URL when a search snippet lacks context or a page exposes a promising direct link. Full content is retained in VFS and receives a source reference.', {'url': {'type': 'string', 'minLength': 1}}, ('url',)), _contract('vfs_read', 'Read an inclusive line range from one VFS key. Large ranges are paginated. Bounds accept 1-based line numbers or stable line IDs.', {'key': {'type': 'string', 'minLength': 1}, 'start_line': {'type': ['string', 'integer', 'null']}, 'end_line': {'type': ['string', 'integer', 'null']}}, ('key', 'start_line', 'end_line')), _contract('vfs_list', 'List VFS keys, optionally restricted to a literal prefix.', {'prefix': {'type': 'string'}}, ('prefix',)), _contract('vfs_write', 'Write or overwrite one VFS file. VFS operations do not create VFS audit entries.', {'key': {'type': 'string', 'minLength': 1}, 'content': {'type': 'string'}}, ('key', 'content')), _contract('vfs_delete', 'Delete one VFS key.', {'key': {'type': 'string', 'minLength': 1}}, ('key',)), _contract('vfs_search', 'Search exact keys, wildcard key patterns such as page://*, or * for all VFS files. Supply an exact regex pattern and a semantic query for the same information need. The harness starts with regex and adds embedding results only when regex fails or finds nothing. Continue paginated regex matches with next_cursor.', {'pattern': {'type': 'string', 'minLength': 1}, 'query': {'type': 'string', 'minLength': 1}, 'targets': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'minItems': 1}, 'cursor': {'type': 'integer', 'minimum': 0, 'description': 'Match offset returned as next_cursor by a previous identical search.'}}, ('pattern', 'query', 'targets')), _contract('update_research_state', 'Replace the prose working memory used on later turns. Call when the best answer, decisive support, or most important unresolved question changes.', {'state': {'type': 'string', 'minLength': 1, 'description': 'Current best answer, decisive observed source refs, and the next unresolved question.'}}, ('state',)), _contract('ready_to_finalize', 'Propose or confirm finalization after decisive external evidence has been inspected. This is premature when an observed search result exposes an uninspected official or primary source for a premise currently supported only by a secondary source. Every cited fetched-page source must already have a retained evidence excerpt.', {'reason': {'type': 'string', 'minLength': 1, 'description': 'Explain readiness and cite decisive source refs such as [S1.2] or [P1].'}}, ('reason',))]
                KEEP_PROOF_OP = _contract('retain_evidence', 'Keep one directly useful, already displayed source excerpt in persistent research memory. Do not retain a source merely for possible later extraction. For flattened tables, retain one continuous range that includes the values, category labels, series labels, and title rather than isolated numeric lines. Every date, year, threshold, or other number asserted in the note must also be visible in the selected range.', {'source': {'type': 'string', 'minLength': 1, 'description': 'An observed source reference such as S1.2 or P3, or its exact VFS key.'}, 'note': {'type': 'string', 'minLength': 1, 'description': 'What the visible source text establishes and which part of the question it informs.'}, 'start_line': {'type': ['string', 'integer'], 'description': 'First displayed line number or stable line ID containing the evidence.'}, 'end_line': {'type': ['string', 'integer'], 'description': 'Last displayed line number or stable line ID containing the evidence.'}}, ('source', 'note', 'start_line', 'end_line'))
                SHED_REMAINING_ORIGINS_OP = _contract('discard_remaining_sources', 'Discard every still-unretained source from the latest retrieval and finish its evidence review.', {'reason': {'type': 'string', 'minLength': 1, 'description': 'Why every still-unretained visible source does not materially inform the research.'}}, ('reason',))
                PROOF_VET_OPS = [KEEP_PROOF_OP, SHED_REMAINING_ORIGINS_OP]
                OP_CATALOG.insert(-1, KEEP_PROOF_OP)

                @dataclass
                class ChronicleSource:
                    ref: str
                    key: str
                    title: str
                    url: str
                    content: str
                    receipt_id: str | None
                    result_id: str | None
                    preview_chars: int = 8000

                @dataclass
                class ChroniclePlan:
                    citations: list[CitationRef]
                    source_indices: dict[str, int]

                class ChronicleState:

                    def __init__(self, question: str='') -> None:
                        self.question = question
                        self.vfs: dict[str, str] = {}
                        self.sources: dict[str, ChronicleSource] = {}
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
                        rows = self.vfs[key].splitlines() or ['']
                        selected = range(len(rows)) if indices is None else indices
                        output: list[dict[str, Any]] = []
                        for index in selected:
                            if index < 0 or index >= len(rows):
                                continue
                            row_id = self._line_id(key, index, rows[index])
                            self.line_locations[row_id] = (key, index)
                            output.append({'line_id': row_id, 'line': index + 1, 'text': rows[index]})
                        return output

                    def focused_excerpts(self) -> list[dict[str, Any]]:
                        excerpts: list[dict[str, Any]] = []
                        for key, indices in self.focused_lines.items():
                            origin_tags = [f'[{origin.ref}]' for origin in self.sources.values() if origin.key == key]
                            excerpts.append({'vfs_key': key, 'source_refs': origin_tags, 'lines': self.render_lines(key, sorted(indices))})
                        return excerpts

                    def remember_focused_lines(self, key: str, indices: set[int] | range) -> None:
                        rows = self.vfs[key].splitlines() or ['']
                        valid_indices = sorted({index for index in indices if 0 <= index < len(rows)})
                        focused = self.focused_lines.setdefault(key, set())
                        for index in valid_indices:
                            if index in focused:
                                continue
                            focused.add(index)
                            location = (key, index)
                            self.focused_line_order[location] = None
                            self.focused_line_chars += len(rows[index]) + 80
                        if not focused:
                            self.focused_lines.pop(key, None)
                        while self.focused_line_chars > CHRONICLE_FOCUS_MEMORY_SIZE and len(self.focused_line_order) > 1:
                            old_slot, old_index = next(iter(self.focused_line_order))
                            self.forget_focused_lines(old_slot, {old_index})

                    def forget_focused_lines(self, key: str, indices: set[int] | None=None) -> None:
                        focused = self.focused_lines.get(key)
                        if focused is None:
                            return
                        removed = set(focused if indices is None else focused & indices)
                        rows = self.vfs.get(key, '').splitlines() or ['']
                        for index in removed:
                            self.focused_line_order.pop((key, index), None)
                            if 0 <= index < len(rows):
                                self.focused_line_chars -= len(rows[index]) + 80
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
                        while self.reasoning_observation_chars > CHRONICLE_FOCUS_MEMORY_SIZE and len(self.reasoning_observations) > 1:
                            removed = self.reasoning_observations.pop(0)
                            self.reasoning_observation_chars -= len(removed)

                    def pending_review_excerpts(self) -> list[dict[str, Any]]:
                        excerpts: list[dict[str, Any]] = []
                        for ref, origin in self.sources.items():
                            if ref not in self.review_source_refs:
                                continue
                            excerpts.append({'source_ref': f'[{ref}]', 'vfs_key': origin.key, 'title': origin.title, 'url': origin.url, 'text': self.bounded_preview(origin.key, max_serialized_chars=origin.preview_chars)})
                        return excerpts

                    def preview(self, key: str, max_chars: int=8000) -> list[dict[str, Any]]:
                        rows = self.vfs[key].splitlines() or ['']
                        if len(self.vfs[key]) <= max_chars:
                            return self.render_lines(key)
                        spend = max_chars // 3
                        groups: list[list[int]] = [[], [], []]
                        positions = [range(len(rows)), range(len(rows) // 3, len(rows)), range(len(rows) - 1, -1, -1)]
                        for group, position in zip(groups, positions, strict=True):
                            used = 0
                            for index in position:
                                if used and used + len(rows[index]) + 1 > spend:
                                    break
                                group.append(index)
                                used += len(rows[index]) + 1
                            group.sort()
                        selected = sorted(set(groups[0] + groups[1] + groups[2]))
                        return self.render_lines(key, selected)

                    def bounded_preview(self, key: str, max_serialized_chars: int) -> list[dict[str, Any]]:
                        prose_spend = max_serialized_chars
                        preview: list[dict[str, Any]] = []
                        for _attempt in range(4):
                            preview = self.preview(key, max_chars=prose_spend)
                            serialized_size = len(json.dumps(preview, ensure_ascii=False, separators=(',', ':')))
                            if serialized_size <= max_serialized_chars:
                                return preview
                            prose_spend = max(100, int(prose_spend * max_serialized_chars / serialized_size * 0.9))
                        return preview

                    def resolve_targets(self, targets: list[str]) -> list[str]:
                        slots: list[str] = []
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
                            slots.extend(matches)
                        return list(dict.fromkeys(slots))

                    def citation_slices(self, key: str, indices: list[int] | range) -> list[CitationSlice]:
                        content = self.vfs[key]
                        rows = content.splitlines(keepends=True) or [content]
                        selected = sorted({index for index in indices if 0 <= index < len(rows)})
                        if not selected:
                            return []
                        offsets = [0]
                        for row_x in rows:
                            offsets.append(offsets[-1] + len(row_x))
                        groups: list[tuple[int, int]] = []
                        start = prior = selected[0]
                        for index in selected[1:]:
                            if index != prior + 1:
                                groups.append((start, prior + 1))
                                start = index
                            prior = index
                        groups.append((start, prior + 1))
                        spans: list[tuple[int, int]] = []
                        for start_row, end_row in groups:
                            start_offset = offsets[start_row]
                            end_offset = offsets[end_row]
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
                        segment_size = max_chars // 3
                        middle_start = max(0, (len(content) - segment_size) // 2)
                        spans = [(0, segment_size), (middle_start, middle_start + segment_size), (len(content) - segment_size, len(content))]
                        quote = '\n\n...\n\n'.join((content[start:end] for start, end in spans))
                        slices = [CitationSlice(start=start, end=end) for start, end in spans]
                        return (quote, slices)

                    @staticmethod
                    def cited_line_indices(reason: str, ref: str) -> list[int]:
                        escaped_tag = re.escape(ref)
                        patterns = (f'\\[{escaped_tag}\\s*,\\s*lines?\\s+(\\d+)(?:\\s*(?:-|to)\\s*(\\d+))?\\]', f'\\[{escaped_tag}\\s*,\\s*L(\\d+)(?:\\s*-\\s*L?(\\d+))?\\]', f'\\[{escaped_tag}\\]\\s*[:,]?\\s*lines?\\s+(\\d+)(?:\\s*(?:-|to)\\s*(\\d+))?', f'\\[{escaped_tag}\\]\\s*[:,]?\\s*L(\\d+)(?:\\s*-\\s*L?(\\d+))?', f'\\b{escaped_tag}\\b\\s*[:,]?\\s*lines?\\s+(\\d+)(?:\\s*(?:-|to)\\s*(\\d+))?', f'\\b{escaped_tag}\\b\\s*[:,]?\\s*L(\\d+)(?:\\s*-\\s*L?(\\d+))?')
                        indices: set[int] = set()
                        for pattern in patterns:
                            for match in re.finditer(pattern, reason, flags=re.IGNORECASE):
                                start = int(match.group(1))
                                end = int(match.group(2) or start)
                                if end < start:
                                    start, end = (end, start)
                                indices.update(range(max(1, start) - 1, end))
                        for bracket in re.findall('\\[([^\\]]+)\\]', reason):
                            if re.search(f'(?:^|[\\s,;]){escaped_tag}(?:$|[\\s,;:])', bracket) is None:
                                continue
                            for match in re.finditer('\\bL(\\d+)(?:\\s*-\\s*L?(\\d+))?', bracket, flags=re.IGNORECASE):
                                start = int(match.group(1))
                                end = int(match.group(2) or start)
                                if end < start:
                                    start, end = (end, start)
                                indices.update(range(max(1, start) - 1, end))
                        return sorted(indices)

                    def source_evidence_indices(self, key: str, indices: list[int] | range | set[int], *, include_focused: bool=True) -> list[int]:
                        rows = self.vfs[key].splitlines() or ['']
                        row_tally = len(rows)
                        candidates = set(indices)
                        if include_focused:
                            candidates.update(self.focused_lines.get(key, set()))
                        selected = {index for index in candidates if 0 <= index < row_tally}
                        for index in tuple(selected):
                            span = _md_grid_span(self, key, index)
                            if span is None:
                                continue
                            selected.update((item['line'] - 1 for item in span['header']))
                        if selected:
                            header = _decode_csv_row(rows[0])
                            selected_rows = [_decode_csv_row(rows[index]) for index in selected]
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
                        rows = self.vfs[key].splitlines()
                        if not rows or 0 not in indices:
                            return []
                        header = _decode_csv_row(rows[0])
                        if header is None:
                            return []
                        if len(header) < 3 or len(set(header)) != len(header):
                            return []
                        records: list[dict[str, str]] = []
                        for index in indices:
                            if index == 0 or not 0 <= index < len(rows):
                                continue
                            row = _decode_csv_row(rows[index])
                            if row is None:
                                return []
                            if len(row) != len(header):
                                return []
                            records.append(dict(zip(header, row, strict=True)))
                        return records

                    def source_packet(self, reason: str, *, allow_preview: bool=True, include_structured_csv: bool=False, prefer_retained: bool=True) -> list[dict[str, Any]]:
                        mentioned_tags = list(dict.fromkeys(re.findall('\\b(S\\d+(?:\\.\\d+)?|P\\d+)\\b', reason)))
                        tags: list[str] = []
                        for ref in mentioned_tags:
                            if re.fullmatch('S\\d+', ref):
                                tags.extend((candidate for candidate in self.sources if candidate.startswith(f'{ref}.')))
                            else:
                                tags.append(ref)
                        tags.extend((origin.ref for origin in self.sources.values() if origin.key in reason))
                        tags = list(dict.fromkeys(tags))
                        single_origin_row_indices: list[int] = []
                        if len(tags) == 1:
                            indices: set[int] = set()
                            for match in re.finditer('\\b(?:lines?\\s+)?L(\\d+)(?:\\s*-\\s*L?(\\d+))?', reason, flags=re.IGNORECASE):
                                start = int(match.group(1))
                                end = int(match.group(2) or start)
                                if end < start:
                                    start, end = (end, start)
                                indices.update(range(max(1, start) - 1, end))
                            single_origin_row_indices = sorted(indices)
                        row_ids = list(dict.fromkeys(re.findall('\\bL[0-9a-f]{10}\\b', reason)))
                        packet: list[dict[str, Any]] = []
                        for ref in tags:
                            origin = self.sources.get(ref)
                            if origin is None:
                                continue
                            if prefer_retained and ref in self.retained_evidence:
                                retained = self.retained_evidence[ref]
                                retained_item = {key: value for key, value in retained.items() if key in {'source_ref', 'title', 'url', 'quote', 'csv_records'}}
                                remaining_focused = self.focused_lines.get(origin.key)
                                if remaining_focused:
                                    selected_indices = self.source_evidence_indices(origin.key, remaining_focused)
                                    focused_item: dict[str, Any] = {'source_ref': f'[{ref}]', 'title': origin.title, 'url': origin.url, 'quote': '\n'.join((item['text'] for item in self.render_lines(origin.key, selected_indices)))}
                                    if include_structured_csv:
                                        csv_records = self.structured_csv_records(origin.key, selected_indices)
                                        if csv_records:
                                            retained_records = list(retained_item.get('csv_records', []))
                                            focused_item['csv_records'] = [*retained_records, *(log for log in csv_records if log not in retained_records)]
                                        self.source_slices[ref] = _fuse_cite_spans(self.source_slices.get(ref, []), self.citation_slices(origin.key, selected_indices))
                                    retained_item = _fuse_origin_bundles([retained_item], [focused_item])[0]
                                packet.append(retained_item)
                                continue
                            origin_row_ids = [row_id for row_id in row_ids if self.line_locations.get(row_id, (None,))[0] == origin.key]
                            cited_line_indices = sorted(set(self.cited_line_indices(reason, ref)) | set(single_origin_row_indices))
                            selected_indices: list[int] | range | None
                            cite_indices: list[int] | range | None
                            if origin_row_ids:
                                row_indices = [self.line_locations[row_id][1] for row_id in origin_row_ids]
                                proof_pane = set(row_indices)
                                selected_indices = self.source_evidence_indices(origin.key, proof_pane, include_focused=False)
                                cite_indices = selected_indices
                                quote = '\n'.join((item['text'] for item in self.render_lines(origin.key, selected_indices)))
                            elif cited_line_indices:
                                selected = set(cited_line_indices)
                                cite_indices = self.source_evidence_indices(origin.key, selected, include_focused=False)
                                selected_indices = cite_indices
                                quote = '\n'.join((f"{item['line']}: {item['text']}" for item in self.render_lines(origin.key, selected_indices)))
                            elif origin.key in self.focused_lines:
                                selected_indices = self.source_evidence_indices(origin.key, self.focused_lines[origin.key])
                                cite_indices = selected_indices
                                quote = '\n'.join((item['text'] for item in self.render_lines(origin.key, selected_indices)))
                            elif not allow_preview:
                                continue
                            else:
                                quote, slices = self.packet_preview(origin.key)
                                self.source_slices[ref] = slices
                                selected_indices = None
                                cite_indices = None
                            if include_structured_csv and selected_indices is not None:
                                self.source_slices[ref] = self.citation_slices(origin.key, cite_indices or selected_indices)
                            item: dict[str, Any] = {'source_ref': f'[{ref}]', 'title': origin.title, 'url': origin.url, 'quote': quote}
                            if selected_indices is not None:
                                csv_records = self.structured_csv_records(origin.key, selected_indices)
                                if csv_records:
                                    item['csv_records'] = csv_records
                            packet.append(item)
                        return packet

                    def citation_plan(self, answer: str, fallback_packet: list[dict[str, Any]], final_source_slices: dict[str, list[CitationSlice]], audit: str) -> ChroniclePlan:
                        review_tags = list(dict.fromkeys(re.findall('\\b(S\\d+(?:\\.\\d+)?|P\\d+)\\b', audit)))
                        verdict_tags = list(dict.fromkeys(re.findall('\\b(S\\d+(?:\\.\\d+)?|P\\d+)\\b', answer)))
                        mentioned_tags = list(dict.fromkeys([*verdict_tags, *review_tags]))
                        tags: list[str] = []
                        for ref in mentioned_tags:
                            if re.fullmatch('S\\d+', ref):
                                tags.extend((candidate for candidate in self.sources if candidate.startswith(f'{ref}.')))
                            else:
                                tags.append(ref)
                        if not tags:
                            tags = [item['source_ref'][1:-1] for item in fallback_packet]
                        cite_origins: dict[tuple[str, str], ChronicleSource] = {}
                        citation_slices: dict[tuple[str, str], list[CitationSlice]] = {}
                        origin_identities: dict[str, tuple[str, str]] = {}
                        for ref in tags:
                            origin = self.sources.get(ref)
                            if origin and origin.receipt_id and origin.result_id:
                                ident = (origin.receipt_id, origin.result_id)
                                origin_identities[ref] = ident
                                slices = _fuse_cite_spans([], final_source_slices.get(ref, self.source_slices.get(ref, [])))
                                cite_origins[ident] = origin
                                citation_slices[ident] = _fuse_cite_spans(citation_slices.get(ident, []), slices)
                        ident_indices = {ident: index for index, ident in enumerate(cite_origins, start=1)}
                        citations = [CitationRef(receipt_id=origin.receipt_id, result_id=origin.result_id, slices=citation_slices[ident]) for ident, origin in cite_origins.items()]
                        return ChroniclePlan(citations=citations, source_indices={ref: ident_indices[ident] for ref, ident in origin_identities.items() if ident in ident_indices})
                _CRITIQUESCRUB_RE = re.compile('(?:^|[.!?]\\s+)\\s*(?:The current answer|The (?:draft|proposed|above) answer|This answer|This (?:is|looks?|seems|appears|may be|might be)|It seems|It appears|There (?:is|are)|However,? the|But the|The (?:reasoning|analysis|derivation|conclusion)|[^.!?]*(?:confus|inconsisten|incomplete|wrong|mixes|misstates|contradicts|has issues|is inaccurate|is incorrect|contains|is problematic)[^.!?]*)[.!?](?=\\s|$)', re.IGNORECASE | re.DOTALL)

                def _cut_critiquescrub(text: str) -> str:
                    out_rows: list[str] = []
                    for row_x in text.splitlines():
                        cleaned = _CRITIQUESCRUB_RE.sub('', row_x).strip()
                        if not cleaned or len(cleaned) < 4:
                            continue
                        out_rows.append(cleaned)
                    return '\n'.join(out_rows).strip()
                _SEEPY_QUOTES = re.compile('\\b(?:the current answer|the draft answer|the proposed answer|this answer (?:is|looks|seems|mixes|misstates|has)|there is an issue|this is confusing|this is likely|this is probably|this may be wrong)\\b', re.IGNORECASE)

                def _has_critiquescrub(text: str) -> bool:
                    return bool(_SEEPY_QUOTES.search(text or ''))

                def _has_viable_verdict(text: str) -> bool:
                    body = (text or '').strip()
                    if len(body) < 24:
                        return False
                    words = re.findall('[A-Za-z0-9]+', body)
                    if len(words) < 6:
                        return False
                    stripped = re.sub('\\[(?:S\\d+(?:\\.\\d+)?|P\\d+)\\]', '', body)
                    return len(re.findall('[A-Za-z]{3,}', stripped)) >= 5
                _STATE_DOMAIN_RE = re.compile('\\.(?:gov|mil|int)(?:[./]|$)|(?:^|\\.)(?:un|oecd|imf|worldbank|who|ecb|europa|census|bls|sec|noaa|nasa|nih|cdc|fbi|irs|treasury|federalreserve|parliament|bundesbank)\\.', re.IGNORECASE)
                _CANONICAL_DOMAIN_RE = re.compile('(?:^|\\.)(?:wikipedia|britannica|citypopulation|worldometers|macrotrends|statista|ourworldindata|baseball-reference|basketball-reference|pro-football-reference|hockey-reference|boxofficemojo|the-numbers|imdb|olympics|fifa|uefa|premierleague|nfl|nba|mlb|nhl|billboard|discogs|allmusic|rottentomatoes|metacritic|sipri|pewresearch|gallup|nature|science|reuters|apnews|bbc|parliament\\.uk)\\.', re.IGNORECASE)
                _FRAIL_DOMAIN_RE = re.compile('(?:^|\\.)(?:reddit|quora|answers|stackexchange|stackoverflow|fandom|wikia|tumblr|pinterest|medium|substack|blogspot|wordpress|tiktok|facebook|x|twitter|instagram|youtube|ranker|screenrant|buzzfeed|cheatsheet|sportskeeda|thesportster|listverse|wattpad)\\.', re.IGNORECASE)
                _LINK_DOMAIN_RE = re.compile('^[a-z]+://([^/]+)', re.IGNORECASE)

                def _origin_tier(url: str) -> int:
                    m = _LINK_DOMAIN_RE.match((url or '').strip())
                    domain = (m.group(1) if m else '').lower()
                    if not domain:
                        return 1
                    if _FRAIL_DOMAIN_RE.search(domain):
                        return 0
                    if _STATE_DOMAIN_RE.search(domain):
                        return 3
                    if _CANONICAL_DOMAIN_RE.search(domain):
                        return 2
                    return 1

                def _canon_subject_labels(value: object, question: str) -> object:

                    def _strip_prefix(text: str) -> str:
                        text = text.strip()
                        prefix_re = re.compile('^(?:HMS|USS|SS|SMV|USNS|HMAS|HMCS|RFA|HMS|SMS|KMS)\\s+', re.IGNORECASE)
                        return prefix_re.sub('', text)

                    def _walk(v: object) -> object:
                        if isinstance(v, str):
                            out = _strip_prefix(v)
                            if out and len(out) > 1:
                                return out
                            return v
                        if isinstance(v, dict):
                            return {k: _walk(v) for k, v in v.items()}
                        if isinstance(v, list):
                            return [_walk(item) for item in v]
                        return v
                    return _walk(value)

                def _internal_origin_tags(answer: str) -> list[str]:
                    return list(dict.fromkeys(re.findall('\\[(S\\d+(?:\\.\\d+)?|P\\d+)\\]', answer)))

                def _canon_bundled_internal_tags(answer: str) -> str:
                    ref = '(?:S\\d+(?:\\.\\d+)?|P\\d+)'
                    bundled = re.compile(f'\\[({ref}(?:\\s*,\\s*{ref})+)\\]')
                    return bundled.sub(lambda match: ''.join((f'[{item}]' for item in re.findall(ref, match.group(1)))), answer)

                def _needs_bare_shape(question: str) -> bool:
                    return bool(re.search('(?i)\\b(?:output|return|respond)\\s+only\\b', question))

                def _check_internal_verdict_tags(answer: str, allowed_tags: set[str], *, require_ref: bool=True) -> None:
                    if '[[' in answer or ']]' in answer:
                        raise ValueError('write private source refs such as [P1], not public numeric markers')
                    if re.search('(?i)(?:https?://|\\bwww\\.|(?<!:)//(?=[a-z0-9])|(?<![\\w@])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+[a-z]{2,63}/[^\\s)]*)', answer):
                        raise ValueError('do not render raw URLs in the reader-facing answer')
                    if re.search('(?im)^\\s{0,3}(?:#{1,6}\\s*)?(?:sources?|citations?|references?|bibliography|works\\s+cited)\\s*:?\\s*$', answer):
                        raise ValueError('do not render a citation or source-list section')
                    literal_tag_pattern = re.compile('\\[(?:S\\d+(?:\\.\\d+)?|P\\d+)\\]')
                    without_literal_tags = literal_tag_pattern.sub('', answer)
                    if '[' in without_literal_tags or ']' in without_literal_tags:
                        raise ValueError('square brackets are reserved for one exact private source ref such as [P1]')
                    if re.search('\\b(?:S\\d+(?:\\.\\d+)?|P\\d+)\\b', without_literal_tags):
                        raise ValueError('each private source ref must appear alone in brackets, for example [P1]')
                    tags = _internal_origin_tags(answer)
                    unclear_tags = [ref for ref in tags if ref not in allowed_tags]
                    if unclear_tags:
                        raise ValueError(f"answer cites unavailable source refs: {', '.join(unclear_tags)}")
                    if require_ref and allowed_tags and (not tags):
                        raise ValueError('answer must place at least one supplied source ref after a supported factual claim')

                def _emit_outward_cites(answer: str, plan: ChroniclePlan, *, unadorned_output: bool=False, state: ChronicleState | None=None) -> tuple[str, list[CitationRef]]:
                    answer = _cut_critiquescrub(answer)
                    if _has_critiquescrub(answer) or not _has_viable_verdict(answer):
                        raise ValueError('final answer contains self-critique or is unusable after scrubbing')
                    tags = _internal_origin_tags(answer)
                    missing_tags = [ref for ref in tags if ref not in plan.source_indices]
                    if missing_tags:
                        raise ValueError('answer source refs do not have materializable citations: ' + ', '.join(missing_tags))
                    rendered = re.sub('\\[(S\\d+(?:\\.\\d+)?|P\\d+)\\]', lambda match: f'[[{plan.source_indices[match.group(1)]}]]', answer)
                    marker_indices = [int(value) for value in re.findall('\\[\\[(\\d+)]]', rendered)]
                    invalid_indices = sorted({index for index in marker_indices if index < 1 or index > len(plan.citations)})
                    if invalid_indices:
                        raise ValueError('answer contains citation indices without response citations: ' + ', '.join((str(index) for index in invalid_indices)))
                    if plan.citations and (not marker_indices) and (not unadorned_output):
                        raise ValueError('answer has response citations but no inline citation markers')
                    used_indices = sorted(set(marker_indices)) if marker_indices else list(range(1, len(plan.citations) + 1))
                    trim_indices = {old_index: new_index for new_index, old_index in enumerate(used_indices, start=1)}
                    rendered = re.sub('\\[\\[(\\d+)]]', lambda match: f'[[{trim_indices[int(match.group(1))]}]]', rendered)
                    if unadorned_output:
                        rendered = re.sub('[ \\t]*\\[\\[\\d+]]', '', rendered)
                    citations = [plan.citations[index - 1] for index in used_indices]
                    return (rendered.strip(), citations)

                def _fuse_cite_spans(existing: list[CitationSlice], additional: list[CitationSlice]) -> list[CitationSlice]:
                    spans = sorted(((int(item.start), int(item.end)) for item in [*existing, *additional] if int(item.end) > int(item.start)))
                    merged: list[tuple[int, int]] = []
                    for start, end in spans:
                        if merged and start <= merged[-1][1]:
                            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                        else:
                            merged.append((start, end))
                    return [CitationSlice(start=start, end=end) for start, end in merged]

                def _agent_memo(finding: Any) -> Any:
                    choices = finding.llm.choices
                    if len(choices) != 1:
                        raise RuntimeError(f'expected one LLM choice, received {len(choices)}')
                    return choices[0].message

                def _agent_proof_span(memo: Any) -> str:
                    prose_parts = [str(part.text) for part in memo.content if getattr(part, 'text', None)]
                    return '\n'.join((item for item in (str(memo.reasoning or '').strip(), *prose_parts) if item))

                def _gather_shelf_slots(value: Any) -> list[str]:
                    slots: list[str] = []
                    if isinstance(value, dict):
                        for field, item in value.items():
                            if field in {'key', 'vfs_key'} and isinstance(item, str):
                                slots.append(item)
                            elif field in {'keys', 'matched_keys'} and isinstance(item, list):
                                slots.extend((candidate for candidate in item if isinstance(candidate, str)))
                            else:
                                slots.extend(_gather_shelf_slots(item))
                    elif isinstance(value, list):
                        for item in value:
                            slots.extend(_gather_shelf_slots(item))
                    return list(dict.fromkeys(slots))

                def _trim_spent_op_findings(messages: list[Any]) -> None:
                    for memo in messages:
                        if not isinstance(memo, dict) or memo.get('role') != 'tool':
                            continue
                        content = memo.get('content')
                        if not isinstance(content, str) or len(content) < 1000:
                            continue
                        try:
                            output = json.loads(content)
                        except json.JSONDecodeError:
                            continue
                        if not isinstance(output, dict):
                            continue
                        ticket: dict[str, Any] = {'ok': output.get('ok', False)}
                        slots = _gather_shelf_slots(output)
                        if slots:
                            ticket['vfs_keys'] = slots
                        if output.get('error_type'):
                            ticket['error_type'] = output['error_type']
                            ticket['details'] = str(output.get('details', ''))[:1000]
                        if output.get('audit'):
                            ticket['audit'] = output['audit']
                        affinity = output.get('similarity')
                        if isinstance(affinity, dict):
                            ticket['similarity'] = {field: affinity[field] for field in ('status', 'trigger', 'reason') if field in affinity}
                        memo['content'] = json.dumps(ticket, ensure_ascii=False)

                def _trim_spent_agent_thought(messages: list[Any]) -> None:
                    for index, memo in enumerate(messages):
                        if isinstance(memo, LlmMessage):
                            if memo.role == 'assistant' and memo.reasoning_details is not None:
                                messages[index] = replace(memo, reasoning_details=None)
                            continue
                        if not isinstance(memo, dict) or memo.get('role') != 'assistant':
                            continue
                        memo.pop('reasoning', None)
                        memo.pop('reasoning_details', None)

                def _log_haul_ticket(state: ChronicleState, label: str, args: dict[str, Any], output: dict[str, Any]) -> None:
                    if not output.get('ok') or label not in {'search_web', 'fetch_page'}:
                        return
                    if label == 'search_web':
                        destinations = [str(output['vfs_key'])]
                        origin_index = [{'source_ref': item['source_ref'], 'vfs_key': item['vfs_key'], 'title': item['title'], 'url': item['url']} for item in output.get('results', []) if isinstance(item, dict)]
                    else:
                        destinations = [str(sheet['vfs_key']) for sheet in output.get('pages', []) if isinstance(sheet, dict) and sheet.get('vfs_key')]
                        origin_index = [{'source_ref': item['source_ref'], 'vfs_key': item['vfs_key'], 'title': item['title'], 'url': item['url']} for item in output.get('pages', []) if isinstance(item, dict)]
                    fingerprint = _haul_fingerprint(label, args)
                    state.retrieval_output_cache[fingerprint] = output
                    ticket = state.retrieval_receipts.setdefault(fingerprint, {'tool': label, 'arguments': args, 'destinations': [], 'sources': [], 'calls': 0})
                    ticket['calls'] += 1
                    ticket['destinations'] = list(dict.fromkeys([*ticket['destinations'], *destinations]))
                    known_origins = {str(item['source_ref']): item for item in [*ticket['sources'], *origin_index]}
                    ticket['sources'] = list(known_origins.values())

                def _haul_fingerprint(label: str, args: dict[str, Any]) -> str:
                    return json.dumps({'tool': label, 'arguments': args}, ensure_ascii=False, sort_keys=True)

                def _log_shelf_step_ticket(state: ChronicleState, label: str, args: dict[str, Any], output: dict[str, Any]) -> None:
                    if not output.get('ok') or label not in {'vfs_read', 'vfs_search', 'vfs_list'}:
                        return
                    if label == 'vfs_read':
                        rows = output.get('lines', [])
                        outcome = {'returned_line_count': len(rows), 'first_line': rows[0].get('line') if rows else None, 'last_line': rows[-1].get('line') if rows else None, 'truncated': bool(output.get('truncated'))}
                    elif label == 'vfs_search':
                        pattern_x = output.get('regex', {})
                        affinity = output.get('similarity', {})
                        outcome = {'regex_total_match_count': pattern_x.get('total_match_count'), 'regex_returned_match_count': len(pattern_x.get('matches', [])), 'regex_next_cursor': pattern_x.get('next_cursor'), 'similarity_status': affinity.get('status'), 'similarity_returned_chunk_count': len(affinity.get('chunks', []))}
                    else:
                        outcome = {'returned_key_count': len(output.get('keys', []))}
                    fingerprint = json.dumps({'tool': label, 'arguments': args}, ensure_ascii=False, sort_keys=True)
                    ticket = state.vfs_operation_receipts.setdefault(fingerprint, {'tool': label, 'arguments': args, 'calls': 0, 'outcome': outcome})
                    ticket['calls'] += 1
                    ticket['outcome'] = outcome

                def _gather_origin_tags(value: Any) -> list[str]:
                    tags: list[str] = []
                    if isinstance(value, dict):
                        for field, item in value.items():
                            if field == 'source_ref' and isinstance(item, str):
                                tags.append(item.strip().strip('[]'))
                            else:
                                tags.extend(_gather_origin_tags(item))
                    elif isinstance(value, list):
                        for item in value:
                            tags.extend(_gather_origin_tags(item))
                    return list(dict.fromkeys(tags))

                def _note_spend(state: ChronicleState, finding: Any) -> None:
                    spend = getattr(finding, 'budget', None)
                    if spend is None:
                        return
                    state.budget_snapshot = {'session_hard_limit_usd': round(float(spend.session_hard_limit_usd), 6), 'session_used_budget_usd': round(float(spend.session_used_budget_usd), 6), 'session_hard_remaining_usd': round(max(0.0, float(spend.session_hard_limit_usd) - float(spend.session_used_budget_usd)), 6)}

                def _renew_haul_ticket_memo(messages: list[Any], state: ChronicleState) -> None:
                    marker = 'Harness research memory'
                    messages[:] = [memo for memo in messages if not (isinstance(memo, dict) and memo.get('role') == 'user' and isinstance(memo.get('content'), str) and memo['content'].startswith(marker))]
                    if not state.research_state and (not state.audit_gap) and (not state.budget_snapshot) and (not state.retrieval_receipts) and (not state.vfs_operation_receipts) and (not state.retained_evidence) and (not state.focused_lines) and (not state.reasoning_observations):
                        return
                    sections: list[str] = []
                    if state.evidence_requirements:
                        sections.append('Evidence questions established before retrieval. They guide the investigation but may become immaterial after supported filtering:\n' + state.evidence_requirements)
                    if state.audit_gap:
                        sections.append('Latest finalization audit. This gap overrides any stale claim in the model-authored state that no uncertainty remains. Do not call ready_to_finalize again until new evidence resolves it:\n' + state.audit_gap)
                    if state.budget_snapshot:
                        sections.append('Latest hosted-tool budget snapshot. This is runtime state, not evidence:\n' + json.dumps(state.budget_snapshot, ensure_ascii=False, indent=2) + '\nFinish before the hard remaining amount reaches zero. After observing the single result that resolves an audit gap, combine any now-independent retain_evidence, update_research_state, and ready_to_finalize calls in the same response instead of spending separate turns on each.')
                    if state.research_state:
                        sections.append('Current model-authored research state. Revise it with update_research_state when the answer, support, or next unresolved question changes:\n' + state.research_state)
                    if state.reasoning_observations:
                        sections.append('Prior source-linked reasoning preserved by the harness. This is working memory, not external evidence. Use its source refs to avoid rediscovering observations, but inspect or retain the referenced source text before relying on a material premise in the final answer:\n' + '\n\n---\n\n'.join(state.reasoning_observations))
                    if state.retrieval_receipts:
                        trim_haul_tickets = [{key: ticket[key] for key in ('tool', 'arguments', 'destinations', 'sources', 'calls') if key in ticket} for ticket in state.retrieval_receipts.values()]
                        sections.append('Completed external retrieval receipts. These record actions and a compact source inventory, not evidence. Each source entry maps a stable source ref to the exact VFS key whose text can be re-read instead of repeating a web search:\n' + json.dumps(trim_haul_tickets, ensure_ascii=False, indent=2))
                    if state.vfs_operation_receipts:
                        sections.append('Completed local VFS inspection operations. These are action history, not evidence. Do not repeat the same read or search merely by changing wording. When prior local inspections did not expose the missing relationship, change the evidence route:\n' + json.dumps(list(state.vfs_operation_receipts.values()), ensure_ascii=False, indent=2))
                    if state.retained_evidence:
                        sections.append('Retained source excerpts selected by your prior reasoning. These are external evidence and do not need to be retrieved again. Only each quote is source evidence; research_note is your prior interpretation and may be wrong:\n' + json.dumps(list(state.retained_evidence.values()), ensure_ascii=False, indent=2))
                    if state.focused_lines:
                        sections.append('Recent unretained VFS observations. VFS remains the full source of truth; only one generous read-page of recent raw observations is replayed here. Retain lines that support or contradict a material premise. Re-read a VFS location when an older unretained observation becomes necessary:\n' + json.dumps(state.focused_excerpts(), ensure_ascii=False, indent=2))
                    messages.insert(2, {'role': 'user', 'content': f'{marker}:\n\n' + '\n\n'.join(sections)})

                def _fuse_origin_bundles(retained: list[dict[str, Any]], live: list[dict[str, Any]]) -> list[dict[str, Any]]:
                    merged: dict[str, dict[str, Any]] = {str(item['source_ref']): item for item in retained}
                    for item in live:
                        origin_tag = str(item['source_ref'])
                        prior = merged.get(origin_tag)
                        if prior is None:
                            merged[origin_tag] = item
                            continue
                        prior_quote = str(prior.get('quote', '')).strip()
                        live_quote = str(item.get('quote', '')).strip()
                        if not prior_quote or prior_quote in live_quote:
                            quote = live_quote
                        elif not live_quote or live_quote in prior_quote:
                            quote = prior_quote
                        else:
                            quote = f'{prior_quote}\n\n{live_quote}'
                        merged[origin_tag] = {**prior, **item, 'quote': quote}
                    return list(merged.values())

                def _is_transient_llm_fault(fault: Exception) -> bool:
                    memo = str(fault).lower()
                    return any((marker in memo for marker in ('429', '500', '502', '503', '504', 'service unavailable', 'timed out', 'timeout', 'empty_output', 'empty output', 'tool execution failed', 'tool invocation failed')))

                async def _op_engine(engine_label: str, messages: list[Any], tools: list[dict[str, Any]] | None, tool_choice: str, parallel_tool_calls: bool, timeout: float, max_output_tokens: int | None=None) -> Any:
                    if engine_label == 'glm5':
                        return await llm_chat(provider='openrouter', model='z-ai/glm-5', messages=messages, temperature=0.2, max_output_tokens=max_output_tokens or CHRONICLE_GLM5_TOP_SHAPE_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'low'}, provider_extra=OPENROUTER_GLM_VENDOR_PREFS, timeout=timeout)
                    if engine_label == 'gpt_oss':
                        return await llm_chat(provider='openrouter', model='openai/gpt-oss-120b', messages=messages, temperature=0.0, max_output_tokens=max_output_tokens or CHRONICLE_GPTOSS_TOP_SHAPE_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'high'}, provider_extra=OPENROUTER_GPT_VENDOR_PREFS, timeout=timeout)
                    if engine_label == 'openrouter_gemma':
                        return await llm_chat(provider='openrouter', model='google/gemma-4-31b-it', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or CHRONICLE_OR_GEMMA_TOP_SHAPE_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, provider_extra=CHRONICLE_OR_GEMMA_VENDOR_PREFS, timeout=timeout)
                    if engine_label == 'openrouter_gemma_prose':
                        return await llm_chat(provider='openrouter', model='google/gemma-4-31b-it', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or CHRONICLE_OR_GEMMA_TOP_SHAPE_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, provider_extra=CHRONICLE_OR_GEMMA_VENDOR_PREFS, timeout=timeout)
                    if engine_label == 'openrouter_gemma_stable':
                        return await llm_chat(provider='openrouter', model='google/gemma-4-31b-it', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or CHRONICLE_OR_GEMMA_TOP_SHAPE_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, provider_extra=CHRONICLE_OR_GEMMA_STABLE_VENDOR_PREFS, timeout=timeout)
                    if engine_label == 'inkling':
                        return await llm_chat(provider='ai_gateway', model='thinkingmachines/inkling', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or CHRONICLE_INKLING_TOP_SHAPE_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, timeout=timeout)
                    if engine_label == 'ai_gateway_gemma':
                        return await llm_chat(provider='ai_gateway', model='google/gemma-4-31b-it', messages=messages, temperature=1.0, max_output_tokens=max_output_tokens or CHRONICLE_AG_GEMMA_TOP_SHAPE_TOKENS, tools=tools, tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, thinking={'enabled': True, 'effort': 'medium'}, provider_extra={'providerOptions': {'gateway': {'only': ['cerebras']}}}, timeout=timeout)
                    raise ValueError(f'unknown model: {engine_label}')

                async def _converse_with_engine_relay(engines: tuple[str, ...], messages: list[Any], tools: list[dict[str, Any]] | None, tool_choice: str, parallel_tool_calls: bool, timeout: float, max_output_tokens: int | None=None) -> Any:
                    if not engines:
                        raise RuntimeError('no research model was configured')
                    raced_engines = engines[:2]
                    remaining_engines = engines[2:]
                    tasks = [asyncio.create_task(_op_engine(model, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)) for model in raced_engines]
                    errors: list[Exception] = []
                    queued = set(tasks)
                    try:
                        while queued:
                            done, queued = await asyncio.wait(queued, return_when=asyncio.FIRST_COMPLETED)
                            for task in done:
                                try:
                                    finding = task.result()
                                except Exception as fault:
                                    errors.append(fault)
                                    continue
                                for unfinished in queued:
                                    unfinished.cancel()
                                await asyncio.gather(*queued, return_exceptions=True)
                                return finding
                    finally:
                        for unfinished in queued:
                            unfinished.cancel()
                        if queued:
                            await asyncio.gather(*queued, return_exceptions=True)
                    non_transient = next((fault for fault in errors if not _is_transient_llm_fault(fault)), None)
                    if non_transient is not None:
                        raise non_transient
                    for model in remaining_engines:
                        try:
                            return await _op_engine(model, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)
                        except Exception as fault:
                            if not _is_transient_llm_fault(fault):
                                raise
                            errors.append(fault)
                    if not errors:
                        raise RuntimeError('no research model was configured')
                    raise errors[-1]

                async def _converse_with_serial_engine_relay(engines: tuple[str, ...], messages: list[Any], tools: list[dict[str, Any]] | None, tool_choice: str, parallel_tool_calls: bool, timeout: float, max_output_tokens: int | None=None) -> Any:
                    if not engines:
                        raise RuntimeError('no research model was configured')
                    errors: list[Exception] = []
                    for model in engines:
                        try:
                            return await _op_engine(model, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)
                        except Exception as fault:
                            if not _is_transient_llm_fault(fault):
                                raise
                            errors.append(fault)
                    raise errors[-1]

                async def _converse_with_dispatch(engines: tuple[str, ...], messages: list[Any], tools: list[dict[str, Any]] | None, tool_choice: str, parallel_tool_calls: bool, timeout: float, max_output_tokens: int | None=None) -> Any:
                    if CHRONICLE_ENGINE_SCHED == 'race':
                        return await _converse_with_engine_relay(engines, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)
                    if CHRONICLE_ENGINE_SCHED in {'sequential', 'state_aware'}:
                        return await _converse_with_serial_engine_relay(engines, messages, tools, tool_choice, parallel_tool_calls, timeout, max_output_tokens)
                    raise ValueError(f'unknown model scheduling policy: {CHRONICLE_ENGINE_SCHED}')

                async def _copy_converse_with_retry(messages: list[Any], tool_choice: str, timeout: float) -> Any:
                    return await _converse_with_dispatch(('glm5', 'openrouter_gemma', 'gpt_oss'), messages, None, tool_choice, False, timeout)

                async def _closing_verdict_converse_with_retry(messages: list[Any], timeout: float) -> Any:
                    return await _converse_with_dispatch(('ai_gateway_gemma', 'openrouter_gemma_prose', 'openrouter_gemma_stable', 'glm5'), messages, None, 'none', False, timeout)

                async def _research_prose(brief: str, user: str) -> str:
                    messages = [{'role': 'system', 'content': brief}, {'role': 'user', 'content': user}]
                    finding = await _copy_converse_with_retry(messages, 'none', ENGINE_LIMIT)
                    text = finding.llm.raw_text
                    if not text or not text.strip():
                        raise RuntimeError('research model returned empty prose')
                    return text.strip()

                async def _verdict_prose(*, state: ChronicleState, question: str, prior_answer: str, requirements: str, research_state: str, finalization_reason: str, packet: list[dict[str, Any]]) -> str:
                    allowed_tags = {str(item['source_ref']).strip('[]') for item in packet if isinstance(item, dict) and item.get('source_ref')}
                    messages: list[Any] = [{'role': 'system', 'content': VERDICT_REVISE_BRIEF}, {'role': 'user', 'content': f"Original question:\n{question}\n\nPrior answer hypothesis:\n{prior_answer}\n\nEvidence requirements:\n{requirements}\n\nInvestigator's current research state:\n{research_state or '(not updated)'}\n\nFinalization reason:\n{finalization_reason}\n\nSupplied source records:\n{json.dumps(packet, ensure_ascii=False, indent=2)}"}]
                    for attempt in range(3):
                        finding = await _closing_verdict_converse_with_retry(messages, ENGINE_LIMIT)
                        _note_spend(state, finding)
                        text = finding.llm.raw_text
                        if not text or not text.strip():
                            raise RuntimeError('answer writer returned empty prose')
                        text = _canon_bundled_internal_tags(text.strip())
                        try:
                            _check_internal_verdict_tags(text, allowed_tags, require_ref=not _needs_bare_shape(question))
                        except ValueError as fault:
                            if attempt == 2:
                                raise
                            messages.extend([{'role': 'assistant', 'content': text}, {'role': 'user', 'content': f'Output contract error: {fault}. Rewrite the complete answer. Use only the exact private source refs present in the supplied records; the harness renders public citation numbers.'}])
                            continue
                        return text
                    raise AssertionError('unreachable')

                def _shaped_shape_op(output_schema: dict[str, Any]) -> tuple[dict[str, Any], bool]:
                    direct_object = output_schema.get('type') == 'object'
                    parameters = output_schema if direct_object else {'type': 'object', 'properties': {'output': {'description': "The non-null JSON value that matches the caller's supplied output schema."}}, 'required': ['output'], 'additionalProperties': False}
                    return ({'type': 'function', 'function': {'name': 'submit_structured_output', 'description': "Submit the complete final value required by the caller's JSON Schema.", 'parameters': parameters, 'strict': False}}, direct_object)

                async def _cast_shaped_shape(*, question: str, answer: str, output_schema: dict[str, Any]) -> Any:
                    op_x, direct_object = _shaped_shape_op(output_schema)
                    proof_backed_verdict = re.sub('\\[\\[\\d+]]', '', answer).strip()
                    messages: list[Any] = [{'role': 'system', 'content': SHAPED_SHAPE_BRIEF}, {'role': 'user', 'content': f'Original question:\n{question}\n\nCompleted evidence-backed answer:\n{proof_backed_verdict}\n\nRequired JSON Schema:\n{json.dumps(output_schema, ensure_ascii=False, indent=2)}'}]
                    for attempt in range(3):
                        finding = await _converse_with_dispatch(CHRONICLE_PROBE_ENGINES, messages, [op_x], 'required', False, ENGINE_LIMIT)
                        agent = _agent_memo(finding)
                        ops = list(agent.tool_calls or ())
                        fault: ValueError | None = None
                        output: Any = None
                        if len(ops) != 1:
                            fault = ValueError(f'call submit_structured_output exactly once; received {len(ops)} tool calls')
                        else:
                            op = ops[0]
                            try:
                                if op.name != 'submit_structured_output':
                                    raise ValueError(f'unexpected tool {op.name}; call submit_structured_output')
                                arguments = json.loads(op.arguments)
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
                                output = _canon_subject_labels(output, question)
                            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as caught:
                                fault = ValueError(str(caught))
                        if fault is None:
                            return output
                        if attempt == 2:
                            raise fault
                        messages.append(agent.to_input_message())
                        if ops:
                            for op in ops:
                                messages.append({'role': 'tool', 'tool_call_id': op.id, 'content': json.dumps({'ok': False, 'error_type': 'tool_argument_validation', 'details': str(fault)})})
                        else:
                            messages.append({'role': 'user', 'content': f'Output contract error: {fault}. Call the required tool with the complete schema-conforming value.'})
                    raise AssertionError('unreachable')

                async def _forecast_verdict_prose(question: str) -> str:
                    messages = [{'role': 'system', 'content': FORECAST_VERDICT_BRIEF}, {'role': 'user', 'content': question}]
                    try:
                        finding = await _op_engine('inkling', messages, None, 'none', False, ENGINE_LIMIT)
                    except Exception as fault:
                        if not _is_transient_llm_fault(fault):
                            raise
                        finding = await _converse_with_dispatch(('gpt_oss', 'openrouter_gemma'), messages, None, 'none', False, ENGINE_LIMIT)
                    text = finding.llm.raw_text
                    if not text or not text.strip():
                        raise RuntimeError('research model returned empty prose')
                    return text.strip()

                def _decode_review(text: str) -> tuple[str, str]:
                    matches = list(re.finditer('(?m)^VERDICT (READY|CONTINUE|REVISE)(?::[ \\t]*(.*))?[ \\t]*$', text))
                    if len(matches) != 1:
                        raise ValueError('audit must contain exactly one VERDICT line')
                    match = matches[0]
                    ruling = match.group(1)
                    inline = (match.group(2) or '').strip()
                    following = text[match.end():].strip()
                    payload = '\n'.join((part for part in (inline, following) if part))
                    if ruling == 'REVISE' and (not payload):
                        raise ValueError('VERDICT REVISE must include a complete replacement answer')
                    if ruling == 'CONTINUE' and (not payload):
                        raise ValueError('VERDICT CONTINUE must name the missing observation')
                    return (ruling, payload)

                async def _review(state: ChronicleState, question: str, answer: str, packet: list[dict[str, Any]]) -> str:
                    allowed_tags = {str(item['source_ref']).strip('[]') for item in packet if isinstance(item, dict) and item.get('source_ref')}
                    origin_inventory = [{'source_ref': f'[{origin.ref}]', 'title': origin.title, 'url': origin.url} for origin in state.sources.values()]
                    messages = [{'role': 'system', 'content': REVIEW_BRIEF}, {'role': 'user', 'content': f'Original question:\n{question}\n\nObserved source inventory (discovery metadata only; titles and URLs are not evidence):\n{json.dumps(origin_inventory, ensure_ascii=False, indent=2)}\n\nSupplied source records:\n{json.dumps(packet, ensure_ascii=False, indent=2)}\n\nCurrent answer:\n{answer}'}]
                    for attempt in range(3):
                        finding = await _converse_with_serial_engine_relay(CHRONICLE_REVIEW_ENGINES, messages, None, 'none', False, ENGINE_LIMIT)
                        _note_spend(state, finding)
                        text = finding.llm.raw_text
                        if not text or not text.strip():
                            raise RuntimeError('auditor returned empty output')
                        text = text.strip()
                        try:
                            ruling, payload = _decode_review(text)
                            if ruling in {'READY', 'REVISE'} and re.search('(?m)^MISSING:', text):
                                raise ValueError(f'VERDICT {ruling} is invalid while a material premise is MISSING; a MISSING line must name a real unresolved premise and cannot say none or not applicable. If no premise is missing, preserve the verdict and omit all MISSING lines. Correct only this output-format error; do not introduce a new evidence requirement')
                            if ruling == 'REVISE':
                                _check_internal_verdict_tags(payload, allowed_tags, require_ref=not _needs_bare_shape(question))
                        except ValueError as fault:
                            if attempt == 2:
                                raise
                            messages.extend([{'role': 'assistant', 'content': text}, {'role': 'user', 'content': f'Output contract error: {fault}. Re-audit from the supplied records. Follow the required premise-line and final VERDICT format exactly; a replacement answer must use only exact supplied private source refs.'}])
                            continue
                        return text
                    raise AssertionError('unreachable')

                def _finding_ident(finding: Any, index: int) -> tuple[str | None, str | None]:
                    if index >= len(finding.results):
                        return (finding.receipt_id, None)
                    return (finding.receipt_id, finding.results[index].result_id)

                async def _run_probe(state: ChronicleState, args: dict[str, Any], preview_spend_size: int | None=None) -> dict[str, Any]:
                    query = str(args['query']).strip()
                    num = int(args.get('num', 10))
                    finding = await search_web(query, provider=PROBE_VENDOR, num=num, timeout=PROBE_LIMIT)
                    _note_spend(state, finding)
                    state.search_count += 1
                    parent_slot = f'search://{state.search_count}'
                    state.vfs[parent_slot] = finding.response.model_dump_json(indent=2)
                    items: list[dict[str, Any]] = []
                    preview_chars = 8000
                    if preview_spend_size is not None:
                        preview_chars = min(preview_chars, max(300, preview_spend_size // max(1, len(finding.response.data))))
                    for index, item in enumerate(finding.response.data):
                        ref = f'S{state.search_count}.{index + 1}'
                        key = f'{parent_slot}/result/{index + 1}'
                        content = item.snippet or item.title or ''
                        state.vfs[key] = content
                        receipt_id, result_id = _finding_ident(finding, index)
                        state.sources[ref] = ChronicleSource(ref=ref, key=key, title=item.title or item.link, url=item.link, content=content, receipt_id=receipt_id, result_id=result_id, preview_chars=preview_chars)
                        items.append({'source_ref': f'[{ref}]', 'vfs_key': key, 'title': item.title, 'url': item.link, 'text': state.bounded_preview(key, max_serialized_chars=preview_chars)})
                    return {'ok': True, 'vfs_key': parent_slot, 'results': items}
                _MIRROR_RESERVE_SECS = 18.0
                _MIRROR_EXTRA_TAGS = 3
                _MIRROR_SPAN_SIZE = 900
                _MIRROR_SKIP_ROW_RE = re.compile('^\\s*(?:proof of completeness|sources?|references?|notes?|citations?)\\b[:\\s]*$', re.IGNORECASE)

                def _assertion_rows(answer: str, limit: int=2) -> list[str]:
                    scored: list[tuple[float, str]] = []
                    for raw in (answer or '').splitlines():
                        row = re.sub('\\[\\[?\\d+\\]?\\]', ' ', raw).strip(' -*\t')
                        if len(row) < 25 or _MIRROR_SKIP_ROW_RE.match(row):
                            continue
                        weight = 0.0
                        if re.match('(?i)^\\s*final answer\\s*:', raw):
                            weight += 4.0
                        if re.search('\\d', row):
                            weight += 1.5
                        if re.search('(?i)\\b(?:pass|fail|highest|largest|greatest|most|first|only)\\b', row):
                            weight += 1.0
                        weight += min(1.0, len(row) / 220.0)
                        scored.append((weight, re.sub('(?i)^\\s*final answer\\s*:\\s*', '', row)[:180]))
                    scored.sort(key=lambda pair: pair[0], reverse=True)
                    seen: set[str] = set()
                    picked: list[str] = []
                    for _weight, row in scored:
                        fingerprint = row.lower()[:60]
                        if fingerprint in seen:
                            continue
                        seen.add(fingerprint)
                        picked.append(row)
                        if len(picked) >= limit:
                            break
                    return picked

                async def _mirror_probe_after_seal(rendered: str, citations: list[CitationRef], state: ChronicleState, began_at: float) -> list[CitationRef]:
                    spent = time.monotonic() - began_at
                    if spent > CUTOFF_WARNING_SECS - _MIRROR_RESERVE_SECS:
                        return citations
                    rows = _assertion_rows(rendered)
                    if not rows:
                        return citations
                    already = {(ref.receipt_id, ref.result_id) for ref in citations}
                    known_refs = set(state.sources)
                    added: list[tuple[float, CitationRef]] = []
                    for row in rows:
                        try:
                            await _run_probe(state, {'query': row, 'num': 6})
                        except Exception:
                            continue
                        row_terms = {term for term in re.findall('[A-Za-z0-9]{3,}', row.lower()) if term not in _WORDWISE_SKIP_TERMS}
                        for ref, origin in state.sources.items():
                            if ref in known_refs:
                                continue
                            known_refs.add(ref)
                            ident = (origin.receipt_id, origin.result_id)
                            if not origin.receipt_id or not origin.result_id or ident in already:
                                continue
                            body = origin.content or ''
                            hits = sum((1 for term in row_terms if term in body.lower()))
                            if not row_terms or hits / len(row_terms) < 0.45:
                                continue
                            already.add(ident)
                            end = min(len(body), _MIRROR_SPAN_SIZE)
                            slices = [CitationSlice(start=0, end=end)] if end > 0 else []
                            score = hits / len(row_terms) + 0.3 * _origin_tier(origin.url or '')
                            added.append((score, CitationRef(receipt_id=origin.receipt_id, result_id=origin.result_id, slices=slices)))
                    added.sort(key=lambda pair: pair[0], reverse=True)
                    return citations + [ref for _score, ref in added[:_MIRROR_EXTRA_TAGS]]

                async def _run_pull(state: ChronicleState, args: dict[str, Any], preview_spend_size: int | None=None) -> dict[str, Any]:
                    url = str(args['url']).strip()
                    if re.search('\\.(?:xls|xlsx|xlsb)(?:[?#]|$)', url, flags=re.IGNORECASE):
                        raise ValueError('fetch_page cannot expose spreadsheet binary rows to VFS tools; search the same publisher for a CSV, HTML, or plain-text companion')
                    finding = await fetch_page(url, provider=PROBE_VENDOR, timeout=PULL_LIMIT)
                    _note_spend(state, finding)
                    state.page_count += 1
                    items: list[dict[str, Any]] = []
                    preview_chars = 8000
                    if preview_spend_size is not None:
                        preview_chars = min(preview_chars, max(300, preview_spend_size // max(1, len(finding.response.data))))
                    for index, item in enumerate(finding.response.data):
                        ref = f'P{state.page_count + index}'
                        key = f'page://{item.url}'
                        state.vfs[key] = item.content
                        receipt_id, result_id = _finding_ident(finding, index)
                        state.sources[ref] = ChronicleSource(ref=ref, key=key, title=item.title or item.url, url=item.url, content=item.content, receipt_id=receipt_id, result_id=result_id, preview_chars=preview_chars)
                        item_payload = {'source_ref': f'[{ref}]', 'vfs_key': key, 'title': item.title, 'url': item.url}
                        if len(item.content) > preview_chars:
                            wordwise_span = _run_wordwise_span(state, {'query': state.question, 'targets': [key]})
                            item_payload['question_context'] = {'instruction': 'These are the long page regions most relevant to the original question. Inspect them before issuing another page search or read.', 'windows': wordwise_span['windows']}
                        item_payload['text'] = state.bounded_preview(key, max_serialized_chars=preview_chars)
                        items.append(item_payload)
                    state.page_count += max(0, len(finding.response.data) - 1)
                    return {'ok': True, 'pages': items}

                def _run_view(state: ChronicleState, args: dict[str, Any], *, remember_focused: bool=True) -> dict[str, Any]:
                    key = str(args['key'])
                    if key not in state.vfs:
                        raise ValueError(f'unknown VFS key: {key}')
                    rows = state.vfs[key].splitlines() or ['']

                    def resolve_bound(value: Any, default: int) -> int:
                        text = '' if value is None else str(value).strip()
                        if value is None or text.lower() in {'', 'null', 'none'}:
                            return default
                        location = state.line_locations.get(text)
                        if location is not None:
                            if location[0] != key:
                                raise ValueError(f'line ID {value} belongs to {location[0]}, not {key}')
                            return location[1]
                        row_number_match = re.fullmatch('L?(\\d+)', text, flags=re.IGNORECASE)
                        if row_number_match is None:
                            raise ValueError(f'unknown line bound: {value}; use a displayed line ID or 1-based line number')
                        return max(0, int(row_number_match.group(1)) - 1)
                    start = resolve_bound(args.get('start_line'), 0)
                    end = resolve_bound(args.get('end_line'), len(rows) - 1)
                    if start >= len(rows):
                        raise ValueError(f'start_line is beyond the file; {key} has {len(rows)} lines')
                    if end < start:
                        raise ValueError('end_line must not precede start_line')
                    requested_end = min(len(rows) - 1, end)
                    selected_indices: list[int] = []
                    reply_size = 0
                    for index in range(start, requested_end + 1):
                        estimated_size = len(rows[index]) + 80
                        if selected_indices and reply_size + estimated_size > CHRONICLE_VIEW_SHEET_SIZE:
                            break
                        selected_indices.append(index)
                        reply_size += estimated_size
                    selected = selected_indices
                    origin_tags = [f'[{origin.ref}]' for origin in state.sources.values() if origin.key == key]
                    next_index = selected[-1] + 1 if selected else start
                    truncated = next_index <= requested_end
                    next_row_id = None
                    if truncated:
                        next_row_id = state._line_id(key, next_index, rows[next_index])
                        state.line_locations[next_row_id] = (key, next_index)
                    if remember_focused:
                        state.remember_focused_lines(key, selected)
                    return {'ok': True, 'key': key, 'source_refs': origin_tags, 'lines': state.render_lines(key, selected), 'truncated': truncated, 'next_start_line': next_index + 1 if truncated else None, 'next_start_line_id': next_row_id}

                def _run_roster(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
                    prefix = str(args['prefix'])
                    slots = [key for key in state.vfs if key.startswith(prefix)]
                    return {'ok': True, 'keys': slots}

                def _run_store(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
                    key = str(args['key'])
                    if key == '*':
                        raise ValueError("'*' cannot be a VFS key")
                    state.forget_focused_lines(key)
                    state.vfs[key] = str(args['content'])
                    return {'ok': True, 'key': key, 'chars': len(state.vfs[key])}

                def _run_drop(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
                    key = str(args['key'])
                    existed = key in state.vfs
                    state.forget_focused_lines(key)
                    state.vfs.pop(key, None)
                    return {'ok': True, 'key': key, 'deleted': existed}

                def _number_values(text: str) -> set[str]:
                    values: set[str] = set()
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
                        values.add(raw.rstrip('%').replace(',', ''))
                    return values

                def _check_retained_number_proof(state: ChronicleState, origin: ChronicleSource, note: str, selected_rows_x: list[dict[str, Any]]) -> None:
                    assertion_prose = re.sub('\\blines?\\s+(?:L[0-9a-f]{10}|\\d+)(?:\\s*(?:-|to|through)\\s*(?:L[0-9a-f]{10}|\\d+))?(?:\\s*\\(L[0-9a-f]{10}\\))?', '', note, flags=re.IGNORECASE)
                    note_numbers = _number_values(assertion_prose)
                    selected_numbers = _number_values('\n'.join((str(item['text']) for item in selected_rows_x)))
                    missing = note_numbers - selected_numbers
                    if not missing:
                        return
                    origin_rows = state.vfs[origin.key].splitlines() or ['']
                    locations: dict[str, list[str]] = {}
                    for number in sorted(missing):
                        matching_indices = [index for index, row_x in enumerate(origin_rows) if number in _number_values(row_x)]
                        if not matching_indices:
                            if number in _number_values(origin.title):
                                locations[number] = ['source title only; choose a source whose citable body contains this value']
                            continue
                        locations[number] = [f'line {index + 1} ({state._line_id(origin.key, index, origin_rows[index])})' for index in matching_indices[:3]]
                    if not locations:
                        return
                    details = '; '.join((f"{number}: {', '.join(row_locations)}" for number, row_locations in locations.items()))
                    raise ValueError(f'the selected evidence span omits numeric facts asserted by note that are present elsewhere in this source ({details}). Re-read those lines and retry retain_evidence with a span containing the supporting text')

                def _run_keep_proof(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
                    origin_identifier = str(args['source']).strip().strip('[]')
                    origin = state.sources.get(origin_identifier)
                    if origin is None:
                        origin = next((candidate for candidate in state.sources.values() if candidate.key == origin_identifier), None)
                    if origin is None:
                        if origin_identifier in state.vfs and re.fullmatch('search://\\d+', origin_identifier):
                            raise ValueError(f"{args['source']} is a search-result container, not a citable source; use the displayed [Sx.y] source reference or search://N/result/y child key that contains the supporting text")
                        raise ValueError(f"unknown source reference or VFS key: {args['source']}")
                    start_row = args.get('start_line')
                    end_row = args.get('end_line')
                    if start_row is None or end_row is None:
                        raise ValueError('start_line and end_line are required')
                    view_shape = _run_view(state, {'key': origin.key, 'start_line': start_row, 'end_line': end_row}, remember_focused=False)
                    note = str(args['note']).strip()
                    _check_retained_number_proof(state, origin, note, view_shape['lines'])
                    row_ids = ' '.join((str(item['line_id']) for item in view_shape['lines']))
                    prior_spans = list(state.source_slices.get(origin.ref, []))
                    packet = state.source_packet(f'{origin.ref} {row_ids}', allow_preview=False, include_structured_csv=True, prefer_retained=False)
                    if not packet:
                        raise RuntimeError(f'could not build evidence packet for source {origin.ref}')
                    state.source_slices[origin.ref] = _fuse_cite_spans(prior_spans, list(state.source_slices.get(origin.ref, [])))
                    retained = packet[0]
                    retained['research_note'] = note
                    existing = state.retained_evidence.get(origin.ref)
                    if existing is not None:
                        retained = _fuse_origin_bundles([existing], [retained])[0]
                        prior_note = str(existing.get('research_note', '')).strip()
                        retained['research_note'] = '\n'.join((item for item in (prior_note, note) if item))
                    state.retained_evidence[origin.ref] = retained
                    retained_indices = {state.line_locations[str(item['line_id'])][1] for item in view_shape['lines'] if str(item['line_id']) in state.line_locations}
                    state.forget_focused_lines(origin.key, retained_indices)
                    return {'ok': True, 'source_ref': f'[{origin.ref}]'}

                def _run_shed_remaining_origins(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
                    reason = str(args['reason']).strip()
                    if not reason:
                        raise ValueError('reason must not be blank')
                    discarded_tags = set(state.review_source_refs)
                    discarded_origin_tally = len(discarded_tags)
                    state.review_source_refs.clear()
                    retained_slots = {state.sources[ref].key for ref in state.retained_evidence if ref in state.sources}
                    for ref in discarded_tags:
                        origin = state.sources.get(ref)
                        if origin is not None and origin.key not in retained_slots:
                            state.forget_focused_lines(origin.key)
                    return {'ok': True, 'discarded_source_count': discarded_origin_tally}

                def _md_grid_span(state: ChronicleState, key: str, match_index: int) -> dict[str, Any] | None:
                    rows = state.vfs[key].splitlines() or ['']
                    separator_index: int | None = None
                    for index in range(match_index, 0, -1):
                        if re.fullmatch('\\s*\\|(?:\\s*:?-+:?\\s*\\|)+\\s*', rows[index]):
                            separator_index = index
                            break
                        if index < match_index and rows[index].lstrip().startswith('#'):
                            break
                    if separator_index is None:
                        return None
                    header_index = separator_index - 1
                    end_index = separator_index
                    for index in range(separator_index + 1, len(rows)):
                        if not rows[index].lstrip().startswith('|'):
                            break
                        end_index = index
                    return {'start_line': header_index + 1, 'end_line': end_index + 1, 'header': state.render_lines(key, range(header_index, separator_index + 1))}

                def _run_pattern(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
                    pattern = re.compile(str(args['pattern']))
                    slots = state.resolve_targets([str(item) for item in args['targets']])
                    cursor_value = args.get('cursor')
                    cursor = 0 if cursor_value is None else int(cursor_value)
                    if cursor < 0:
                        raise ValueError('cursor must be at least zero')
                    raw_matches: list[tuple[str, dict[str, Any]]] = []
                    for key in slots:
                        for item in state.render_lines(key):
                            if pattern.search(item['text']):
                                raw_matches.append((key, item))
                    matches: list[dict[str, Any]] = []
                    sheet_size = 0
                    for key, item in raw_matches[cursor:]:
                        match = {'key': key, **item}
                        origin_tags = [f'[{origin.ref}]' for origin in state.sources.values() if origin.key == key]
                        if origin_tags:
                            match['source_refs'] = origin_tags
                        grid_span: dict[str, Any] | None = None
                        csv_records = state.structured_csv_records(key, [0, item['line'] - 1])
                        if csv_records:
                            match.pop('text')
                            match['csv_record'] = csv_records[0]
                        else:
                            grid_span = _md_grid_span(state, key, item['line'] - 1)
                            if grid_span is not None:
                                match['table'] = grid_span
                        focused_indices = {item['line'] - 1}
                        if grid_span is not None:
                            focused_indices.update((int(header_row['line']) - 1 for header_row in grid_span['header']))
                        if origin_tags:
                            state.remember_focused_lines(key, focused_indices)
                        matches.append(match)
                        sheet_size += len(json.dumps(match, ensure_ascii=False, separators=(',', ':')))
                        if sheet_size >= CHRONICLE_VSEARCH_SHEET_SIZE:
                            break
                    next_offset = cursor + len(matches)
                    next_cursor = next_offset if next_offset < len(raw_matches) else None
                    return {'ok': True, 'matched_keys': slots, 'total_match_count': len(raw_matches), 'cursor': cursor, 'matches': matches, 'next_cursor': next_cursor}

                def _blocks(state: ChronicleState, slots: list[str]) -> list[dict[str, Any]]:
                    blocks: list[dict[str, Any]] = []
                    for key in slots:
                        content = state.vfs[key]
                        start = 0
                        index = 0
                        while start < len(content):
                            end = min(len(content), start + 3000)
                            blocks.append({'key': key, 'chunk': index, 'start': start, 'end': end, 'text': content[start:end]})
                            if end == len(content):
                                break
                            start = end - 300
                            index += 1
                    return blocks
                _WORDWISE_TERM_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
                _WIDE_CITED_QUOTE_RE = re.compile('"([^"]{24,})"|(?<![a-z0-9])\\\'([^\\\']{24,})\\\'', re.IGNORECASE)
                _WORDWISE_SKIP_TERMS = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

                def _wordwise_terms(text: str) -> set[str]:
                    return {term_x for term_x in _WORDWISE_TERM_RE.findall(text.casefold()) if term_x not in _WORDWISE_SKIP_TERMS}

                def _wide_cited_quotes(text: str) -> list[str]:
                    return [next((group for group in match.groups() if group is not None)).strip() for match in _WIDE_CITED_QUOTE_RE.finditer(text)]

                def _literal_quote_panes(text: str, quotes: list[str]) -> list[tuple[int, int, str]]:
                    panes: list[tuple[int, int, str]] = []
                    lowered = text.casefold()
                    leading_size = CHRONICLE_LEX_PANE_SIZE * 3 // 4
                    for quote_x in quotes:
                        probe_from = 0
                        normalized_quote = quote_x.casefold()
                        while True:
                            match_start = lowered.find(normalized_quote, probe_from)
                            if match_start < 0:
                                break
                            start = max(0, match_start - leading_size)
                            end = min(len(text), start + CHRONICLE_LEX_PANE_SIZE)
                            start = max(0, end - CHRONICLE_LEX_PANE_SIZE)
                            if not any((start < existing_end and existing_start < end for existing_start, existing_end, _ignored in panes)):
                                panes.append((start, end, quote_x))
                            probe_from = match_start + len(normalized_quote)
                    return panes

                def _wordwise_panes(text: str, terms: set[str]) -> list[tuple[int, int, int]]:
                    if not text or not terms:
                        return []
                    if len(text) <= CHRONICLE_LEX_PANE_SIZE:
                        return [(0, len(text), sum((term in text.casefold() for term in terms)))]
                    stage = max(600, CHRONICLE_LEX_PANE_SIZE // 3)
                    lowered = text.lower()
                    scored: list[tuple[int, int]] = []
                    start = 0
                    while start < len(text):
                        pane = lowered[start:start + CHRONICLE_LEX_PANE_SIZE]
                        scored.append((sum((term in pane for term in terms)), start))
                        if start + CHRONICLE_LEX_PANE_SIZE >= len(text):
                            break
                        start += stage
                    scored.sort(key=lambda item: (-item[0], item[1]))
                    selected: list[tuple[int, int, int]] = []
                    for matched_term_tally, start in scored:
                        if len(selected) >= CHRONICLE_LEX_PANE_TALLY:
                            break
                        end = min(len(text), start + CHRONICLE_LEX_PANE_SIZE)
                        if any((start < selected_end and selected_start < end for selected_start, selected_end, _ignored in selected)):
                            continue
                        if selected and matched_term_tally == 0:
                            continue
                        selected.append((start, end, matched_term_tally))
                    return sorted(selected)

                def _run_wordwise_span(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
                    slots = state.resolve_targets([str(item) for item in args['targets']])
                    terms = _wordwise_terms(f"{state.question}\n{args['query']}")
                    quotes = _wide_cited_quotes(state.question)
                    panes: list[dict[str, Any]] = []
                    for key in slots:
                        content = state.vfs[key]
                        selected: list[tuple[int, int, int, str | None]] = [(start, end, len(terms), quote_x) for start, end, quote_x in _literal_quote_panes(content, quotes)]
                        for start, end, matched_term_tally in _wordwise_panes(content, terms):
                            if any((start < selected_end and selected_start < end for selected_start, selected_end, _ignored, _ignored in selected)):
                                continue
                            selected.append((start, end, matched_term_tally, None))
                        for start, end, matched_term_tally, literal_quote in selected:
                            start_row = content[:start].count('\n')
                            end_row = content[:end].count('\n') + 1
                            panes.append({'key': key, 'start': start, 'end': end, 'matched_term_count': matched_term_tally, 'exact_phrase': literal_quote, 'lines': state.render_lines(key, range(start_row, end_row))})
                    panes.sort(key=lambda item: (item['exact_phrase'] is None, -int(item['matched_term_count']), str(item['key']), int(item['start'])))
                    return {'ok': True, 'matched_keys': slots, 'windows': panes[:CHRONICLE_LEX_PANE_TALLY]}

                def _dotnorm(left: list[float], right: list[float]) -> float:
                    numerator = sum((a * b for a, b in zip(left, right, strict=True)))
                    left_norm = math.sqrt(sum((value * value for value in left)))
                    right_norm = math.sqrt(sum((value * value for value in right)))
                    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0

                async def _run_affinity(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
                    slots = state.resolve_targets([str(item) for item in args['targets']])
                    embedded_blocks: list[tuple[dict[str, Any], list[float]]] = []
                    missing_blocks: list[dict[str, Any]] = []
                    missing_cache_slots: list[tuple[str, str]] = []
                    missing_block_counts: list[int] = []
                    for key in slots:
                        cache_slot = (key, hashlib.sha256(state.vfs[key].encode()).hexdigest())
                        cached = state.document_embeddings.get(cache_slot)
                        if cached is not None:
                            embedded_blocks.extend(cached)
                            continue
                        blocks = _blocks(state, [key])
                        missing_cache_slots.append(cache_slot)
                        missing_block_counts.append(len(blocks))
                        missing_blocks.extend(blocks)
                    if not embedded_blocks and (not missing_blocks):
                        return {'ok': True, 'matched_keys': slots, 'chunks': []}
                    query_finding = await embed_text(str(args['query']), provider='openrouter', model='qwen/qwen3-embedding-8b', input_type='query', provider_extra=VECTOR_SPARE, timeout=VECTOR_LIMIT)
                    if missing_blocks:
                        document_finding = await embed_text([block['text'] for block in missing_blocks], provider='openrouter', model='qwen/qwen3-embedding-8b', input_type='document', provider_extra=VECTOR_SPARE, timeout=VECTOR_LIMIT)
                        vectors = [item.embedding for item in sorted(document_finding.response.data, key=lambda item: item.index)]
                        if len(vectors) != len(missing_blocks):
                            raise RuntimeError(f'embedding result count mismatch: expected {len(missing_blocks)}, received {len(vectors)}')
                        offset = 0
                        for cache_slot, block_tally in zip(missing_cache_slots, missing_block_counts, strict=True):
                            cached = list(zip(missing_blocks[offset:offset + block_tally], vectors[offset:offset + block_tally], strict=True))
                            state.document_embeddings[cache_slot] = cached
                            embedded_blocks.extend(cached)
                            offset += block_tally
                    query_vector = query_finding.response.data[0].embedding
                    scored = [{**block, 'score': _dotnorm(query_vector, vector)} for block, vector in embedded_blocks]
                    scored.sort(key=lambda item: item['score'], reverse=True)
                    output: list[dict[str, Any]] = []
                    shape_size = 0
                    for item in scored[:CHRONICLE_SIM_TOP_BLOCKS]:
                        key = item['key']
                        content_before = state.vfs[key][:item['start']]
                        start_row = content_before.count('\n')
                        row_tally = item['text'].count('\n') + 1
                        finding_item = {'key': key, 'chunk': item['chunk'], 'score': item['score'], 'lines': state.render_lines(key, range(start_row, start_row + row_tally))}
                        origin_tags = [f'[{origin.ref}]' for origin in state.sources.values() if origin.key == key]
                        if origin_tags:
                            finding_item['source_refs'] = origin_tags
                        finding_size = len(json.dumps(finding_item, ensure_ascii=False, separators=(',', ':')))
                        if len(output) >= CHRONICLE_SIM_FLOOR_BLOCKS and shape_size + finding_size > CHRONICLE_SIM_FINDING_SIZE:
                            break
                        if origin_tags:
                            state.remember_focused_lines(key, range(start_row, start_row + row_tally))
                        output.append(finding_item)
                        shape_size += finding_size
                    return {'ok': True, 'matched_keys': slots, 'chunks': output}

                async def _run_shelf_probe(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
                    pattern_finding: dict[str, Any] | None = None
                    pattern_fault: str | None = None
                    try:
                        pattern_finding = _run_pattern(state, args)
                    except (TypeError, ValueError, re.error) as fault:
                        pattern_fault = str(fault)
                    affinity_trigger: str | None = None
                    if pattern_finding is None:
                        affinity_trigger = 'regex_error'
                    elif int(pattern_finding['total_match_count']) == 0:
                        affinity_trigger = 'no_regex_matches'
                    affinity_finding: dict[str, Any] | None = None
                    affinity_fault: str | None = None
                    if affinity_trigger is not None:
                        try:
                            affinity_finding = await _run_affinity(state, args)
                        except Exception as fault:
                            affinity_fault = str(fault)
                    if pattern_finding is None and affinity_finding is None:
                        raise RuntimeError(f"both VFS search methods failed: regex={pattern_fault or 'unknown'}; similarity={affinity_fault or 'unknown'}")
                    output: dict[str, Any] = {'ok': True, 'similarity': {'status': 'not_run', 'reason': 'regex_returned_matches_on_first_search'}}
                    if pattern_finding is not None:
                        output['regex'] = {key: value for key, value in pattern_finding.items() if key not in {'ok', 'matched_keys'}}
                    if pattern_fault is not None:
                        output['regex_error'] = pattern_fault
                    if affinity_finding is not None:
                        output['similarity'] = {'status': 'completed', 'trigger': affinity_trigger}
                        output['similarity'].update({key: value for key, value in affinity_finding.items() if key not in {'ok', 'matched_keys'}})
                    if affinity_fault is not None:
                        output['similarity'] = {'status': 'failed', 'trigger': affinity_trigger, 'error': affinity_fault}
                    return output

                async def _run_op(state: ChronicleState, label: str, args: dict[str, Any], preview_spend_size: int | None=None) -> dict[str, Any]:
                    if label in {'search_web', 'fetch_page'}:
                        cached = state.retrieval_output_cache.get(_haul_fingerprint(label, args))
                        if cached is not None:
                            return {**cached, 'cached': True}
                    if label == 'search_web':
                        return await _run_probe(state, args, preview_spend_size)
                    if label == 'fetch_page':
                        return await _run_pull(state, args, preview_spend_size)
                    if label == 'vfs_read':
                        return _run_view(state, args)
                    if label == 'vfs_list':
                        return _run_roster(state, args)
                    if label == 'vfs_write':
                        return _run_store(state, args)
                    if label == 'vfs_delete':
                        return _run_drop(state, args)
                    if label == 'retain_evidence':
                        return _run_keep_proof(state, args)
                    if label == 'discard_remaining_sources':
                        return _run_shed_remaining_origins(state, args)
                    if label == 'vfs_search':
                        return await _run_shelf_probe(state, args)
                    if label == 'update_research_state':
                        research_state = str(args['state']).strip()
                        if not research_state:
                            raise ValueError('state must not be blank')
                        state.research_state = research_state
                        return {'ok': True}
                    raise ValueError(f'unknown tool: {label}')

                def _unique_op_ops(ops: list[Any]) -> tuple[list[Any], int]:
                    distinct_ops: list[Any] = []
                    seen: set[tuple[str, str]] = set()
                    for op in ops:
                        try:
                            arguments = json.dumps(json.loads(op.arguments), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
                        except json.JSONDecodeError:
                            arguments = op.arguments
                        fingerprint = (op.name, arguments)
                        if fingerprint in seen:
                            continue
                        seen.add(fingerprint)
                        distinct_ops.append(op)
                    return (distinct_ops, len(ops) - len(distinct_ops))

                async def _seal_verdict(*, state: ChronicleState, question: str, current_answer: str, reason: str, assistant_context: str, last_packet: list[dict[str, Any]], final_source_slices: dict[str, list[CitationSlice]]) -> tuple[str, list[dict[str, Any]]]:
                    finalization_span = '\n\n'.join((value for value in (state.research_state.strip(), reason.strip(), assistant_context.strip()) if value))
                    packet = state.source_packet(finalization_span, include_structured_csv=True)
                    if not packet:
                        raise ValueError('final answer must mention at least one observed source reference such as S1.2 or P1')
                    unretained_sheet_tags = [str(item['source_ref']) for item in packet if str(item['source_ref']).strip('[]').startswith('P') and str(item['source_ref']).strip('[]') not in state.retained_evidence]
                    if unretained_sheet_tags:
                        raise ValueError(f"fetched-page evidence must be preserved before finalization; call retain_evidence for each decisive excerpt from {', '.join(unretained_sheet_tags)}, then retry")
                    for item in packet:
                        ref = str(item['source_ref'])[1:-1]
                        final_source_slices[ref] = _fuse_cite_spans(final_source_slices.get(ref, []), list(state.source_slices.get(ref, [])))
                    precise_tags = {str(item['source_ref']) for item in [*last_packet, *packet]}
                    retained_bundle = [item for item in state.retained_evidence.values() if str(item['source_ref']) not in precise_tags]
                    merged_bundle = _fuse_origin_bundles(last_packet, retained_bundle)
                    merged_bundle = _fuse_origin_bundles(merged_bundle, packet)
                    merged_bundle = [item for item in merged_bundle if (origin := state.sources.get(str(item['source_ref']).strip('[]'))) and origin.receipt_id and origin.result_id]
                    if not merged_bundle:
                        raise ValueError('none of the selected source records can be materialized as response citations')
                    answer = await _verdict_prose(state=state, question=question, prior_answer=current_answer, requirements=state.evidence_requirements or '', research_state=state.research_state, finalization_reason=reason, packet=merged_bundle)
                    return (answer, merged_bundle)

                def _research_advance_fingerprint(state: ChronicleState) -> tuple[Any, ...]:
                    return (state.evidence_requirements, tuple(sorted(state.sources)), tuple(((key, tuple(sorted(indices))) for key, indices in sorted(state.focused_lines.items()))), tuple(sorted(state.retained_evidence)), state.research_state, state.audit_gap)

                def _pursuit_engines(state: ChronicleState, cutoff_warning_fired: bool, pivot_cause: str) -> tuple[str, ...]:
                    if CHRONICLE_ENGINE_SCHED != 'state_aware':
                        return CHRONICLE_FIX_ENGINES if state.audit_gap else CHRONICLE_PROBE_ENGINES
                    if state.audit_gap or cutoff_warning_fired or pivot_cause:
                        return CHRONICLE_FIX_ENGINES
                    return BOARD_AWARE_CHRONICLE_PROBE_ENGINES

                def _demands_engines(cutoff_warning_fired: bool, pivot_cause: str) -> tuple[str, ...]:
                    if CHRONICLE_ENGINE_SCHED == 'state_aware' and (cutoff_warning_fired or pivot_cause):
                        return CHRONICLE_FIX_ENGINES
                    return CHRONICLE_NEED_ENGINES

                async def _pursue(question: str, forecast_verdict: str) -> tuple[str, list[CitationRef]]:
                    pursuit_begun_at = time.monotonic()
                    cutoff_warning_fired = False
                    state = ChronicleState(question)
                    state.research_state = f'Current best answer hypothesis:\n{forecast_verdict}\nObserved support: none yet.\nMost important unresolved question: test the hypothesis against external evidence.'
                    current_answer = forecast_verdict
                    messages: list[Any] = [{'role': 'system', 'content': PURSUIT_BRIEF}, {'role': 'user', 'content': f'Original question:\n{question}\n\nExpected answer hypothesis:\n{forecast_verdict}'}]
                    last_packet: list[dict[str, Any]] = []
                    final_source_slices: dict[str, list[CitationSlice]] = {}
                    closing_review = ''
                    pivot_cause = ''
                    prior_op_signatures: tuple[str, ...] = ()
                    for _round in range(160):
                        if not cutoff_warning_fired and time.monotonic() - pursuit_begun_at >= CUTOFF_WARNING_SECS:
                            messages.append({'role': 'user', 'content': 'The external runtime has about 150 seconds remaining. Preserve answer quality. If the observed evidence can support the answer, retain any needed excerpts and call ready_to_finalize now. If one decisive uncertainty remains, perform only the single operation most likely to resolve it, then finalize. Do not restart broad research.'})
                            cutoff_warning_fired = True
                        _renew_haul_ticket_memo(messages, state)
                        demands_queued = state.evidence_requirements is None
                        if demands_queued:
                            onhand_ops = DEMANDS_OPS
                            onhand_engines = _demands_engines(cutoff_warning_fired, pivot_cause)
                        else:
                            onhand_ops = OP_CATALOG
                            onhand_engines = _pursuit_engines(state, cutoff_warning_fired, pivot_cause)
                        ask_memos = [{'role': 'system', 'content': DEMANDS_BRIEF}, {'role': 'user', 'content': f'Original question:\n{question}'}] if demands_queued else messages
                        finding = await _converse_with_dispatch(onhand_engines, messages=ask_memos, tools=onhand_ops, tool_choice='required', parallel_tool_calls=True, timeout=ENGINE_LIMIT, max_output_tokens=None)
                        _note_spend(state, finding)
                        _trim_spent_agent_thought(messages)
                        _trim_spent_op_findings(messages)
                        agent = _agent_memo(finding)
                        state.remember_reasoning_observation(agent.reasoning)
                        ops, twin_op_tally = _unique_op_ops(list(agent.tool_calls or ()))
                        if not ops:
                            copy = (finding.llm.raw_text or '').strip()
                            if copy:
                                try:
                                    current_answer, last_packet = await _seal_verdict(state=state, question=question, current_answer=current_answer, reason=copy, assistant_context=_agent_proof_span(agent), last_packet=last_packet, final_source_slices=final_source_slices)
                                except ValueError as fault:
                                    pivot_cause = f'The previous model tried to finalize without materializable support. Resolve this exact problem before finalizing again: {fault}'
                                    messages.extend([agent.to_input_message(), {'role': 'user', 'content': f'Your terminal answer could not be finalized: {fault}. Use tools to resolve that exact problem, then either return a supported terminal answer or call ready_to_finalize.'}])
                                    continue
                                plan = state.citation_plan(current_answer, last_packet, final_source_slices, closing_review)
                                return _emit_outward_cites(current_answer, plan, unadorned_output=_needs_bare_shape(question))
                            messages.extend([agent.to_input_message(), {'role': 'user', 'content': 'Use a tool. Call ready_to_finalize only when inspected sources support the answer.'}])
                            pivot_cause = 'The previous model returned neither a tool call nor a usable terminal answer. Choose the smallest valid operation that advances the investigation.'
                            continue
                        agent_input = replace(agent, tool_calls=tuple(ops)).to_input_message()
                        messages.append(agent_input)
                        ready_requested = False
                        review_ready = False
                        advance_before = _research_advance_fingerprint(state)
                        round_op_signatures: list[str] = []
                        round_fail_signatures: list[str] = []
                        haul_op_tally = sum((op.name in {'search_web', 'fetch_page'} for op in ops))
                        haul_preview_spend = CHRONICLE_BATCHED_PREVIEW_SIZE // haul_op_tally if haul_op_tally else None
                        for op_index, op in enumerate(ops):
                            op_fingerprint = json.dumps({'tool': op.name, 'raw_arguments': op.arguments}, ensure_ascii=False, sort_keys=True)
                            try:
                                args = json.loads(op.arguments)
                                if not isinstance(args, dict):
                                    raise ValueError('tool arguments must be a JSON object')
                                op_fingerprint = json.dumps({'tool': op.name, 'arguments': args}, ensure_ascii=False, sort_keys=True)
                                if op.name == 'set_evidence_requirements':
                                    if not demands_queued or len(ops) != 1:
                                        raise ValueError('set_evidence_requirements must be the sole call before retrieval')
                                    requirements = str(args['requirements']).strip()
                                    if not requirements:
                                        raise ValueError('requirements must not be empty')
                                    state.evidence_requirements = requirements
                                    output = {'ok': True}
                                elif op.name == 'ready_to_finalize':
                                    if round_fail_signatures:
                                        raise ValueError('cannot finalize in the same response after an earlier tool call failed; inspect that tool feedback, correct the failed operation, and retry finalization')
                                    incompatible_ops = [candidate.name for candidate in ops if candidate.name not in {'update_research_state', 'retain_evidence', 'ready_to_finalize'}]
                                    if incompatible_ops:
                                        raise ValueError(f"ready_to_finalize may only accompany update_research_state and retain_evidence; also received {', '.join(incompatible_ops)}")
                                    if op_index != len(ops) - 1:
                                        raise ValueError('ready_to_finalize must be the final call in the response')
                                    reason = str(args['reason'])
                                    current_answer, last_packet = await _seal_verdict(state=state, question=question, current_answer=current_answer, reason=reason, assistant_context=_agent_proof_span(agent), last_packet=last_packet, final_source_slices=final_source_slices)
                                    closing_review = ''
                                    ready_requested = True
                                    review_ready = True
                                    output = {'ok': True, 'answer_checkpoint': current_answer}
                                elif op.name == 'discard_remaining_sources':
                                    if op_index != len(ops) - 1:
                                        raise ValueError('discard_remaining_sources must be the last call in the response')
                                    output = await _run_op(state, op.name, args, haul_preview_spend)
                                else:
                                    output = await _run_op(state, op.name, args, haul_preview_spend)
                                    _log_haul_ticket(state, op.name, args, output)
                                    _log_shelf_step_ticket(state, op.name, args, output)
                            except Exception as fault:
                                output = {'ok': False, 'error_type': 'tool_argument_validation' if isinstance(fault, (KeyError, TypeError, ValueError, json.JSONDecodeError)) else 'tool_execution', 'details': str(fault)}
                            round_op_signatures.append(op_fingerprint)
                            if not output.get('ok'):
                                round_fail_signatures.append(json.dumps({'tool': op.name, 'error_type': output.get('error_type')}, ensure_ascii=False, sort_keys=True))
                            messages.append({'role': 'tool', 'tool_call_id': op.id, 'content': json.dumps(output, ensure_ascii=False)})
                        if twin_op_tally:
                            messages.append({'role': 'user', 'content': f'The previous response repeated {twin_op_tally} exact tool calls. The harness executed each distinct call once. Continue from those results without repeating an identical call.'})
                        if ready_requested:
                            closing_review = await _review(state, question, current_answer, last_packet)
                            ruling, review_payload = _decode_review(closing_review)
                            if ruling == 'CONTINUE':
                                state.audit_gap = review_payload
                                state.clear_focused_lines()
                                review_ready = False
                                messages = [{'role': 'system', 'content': PURSUIT_BRIEF}, {'role': 'user', 'content': f'Original question:\n{question}\n\nThe finalization audit found one unresolved evidence gap:\n{review_payload}\n\nThe harness will preserve the existing VFS, source references, retained evidence, retrieval receipts, and research state. Resolve this exact gap with the smallest useful next observation, update the research state if the answer changes, then finalize. Do not restart the investigation or repeat already supported premises.'}]
                            elif ruling == 'REVISE':
                                allowed_tags = {str(item['source_ref']).strip('[]') for item in last_packet if isinstance(item, dict) and item.get('source_ref')}
                                _check_internal_verdict_tags(review_payload, allowed_tags, require_ref=not _needs_bare_shape(question))
                                current_answer = review_payload
                                state.audit_gap = ''
                                review_ready = True
                            else:
                                state.audit_gap = ''
                                review_ready = True
                        if CHRONICLE_ENGINE_SCHED == 'state_aware' and (not ready_requested):
                            advance_after = _research_advance_fingerprint(state)
                            live_ops = tuple(round_op_signatures)
                            live_failures = tuple(round_fail_signatures)
                            next_pivot_cause = ''
                            if live_failures:
                                next_pivot_cause = "The previous model's tool call failed. Read the detailed tool feedback, correct that exact operation or choose a different valid operation, and advance the investigation without repeating the failure."
                            elif live_ops and live_ops == prior_op_signatures and (advance_after == advance_before):
                                next_pivot_cause = 'The previous model repeated the same operations without adding evidence or changing the research state. Choose a different evidence route.'
                            elif live_ops and (not live_failures) and (advance_after == advance_before):
                                next_pivot_cause = 'The previous operations succeeded mechanically but produced no new retained evidence, source coverage, inspected lines, or research-state change. Choose the smallest different operation that can resolve the current uncertainty.'
                            if next_pivot_cause:
                                messages.append({'role': 'user', 'content': next_pivot_cause})
                            pivot_cause = next_pivot_cause
                            prior_op_signatures = live_ops
                        if ready_requested and review_ready:
                            plan = state.citation_plan(current_answer, last_packet, final_source_slices, closing_review)
                            rendered, citations = _emit_outward_cites(current_answer, plan, unadorned_output=_needs_bare_shape(question))
                            if not _needs_bare_shape(question):
                                try:
                                    citations = await _mirror_probe_after_seal(rendered, citations, state, pursuit_begun_at)
                                except Exception:
                                    pass
                            return (rendered, citations)
                    raise RuntimeError('investigation did not finalize within the generous 160-turn ceiling')

                async def query(query: Query) -> Response:
                    try:
                        forecast_verdict = await _forecast_verdict_prose(query.text)
                    except Exception as fault:
                        if not _is_transient_llm_fault(fault):
                            raise
                        forecast_verdict = 'No expected-answer hypothesis was available because its model call failed. Investigate the original question directly and construct a revisable answer from observed external evidence.'
                    answer, citations = await _pursue(query.text, forecast_verdict)
                    if query.output_schema is not None:
                        output = await _cast_shaped_shape(question=query.text, answer=answer, output_schema=query.output_schema)
                        return Response(output=output, citations=citations)
                    return Response(text=answer, citations=citations)
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
        _R4991913_LADDER = (2, 4, 3, 14)

        def _r4991913_span_budget(step: int=2) -> int:
            """Offline pacing helper (unused)."""
            if step <= 0:
                return _R4991913_LADDER[0]
            return _R4991913_LADDER[min(step, len(_R4991913_LADDER) - 1)]

        def _r4991913_rank_notes(items: list | None=None) -> list:
            """Offline ordering helper (unused)."""
            pool = list(items or ())
            if not pool:
                return []
            scored = [(len(str(v)) * 3, str(v)) for v in pool]
            scored.sort(reverse=True)
            return [v for _, v in scored[:4]]
        return query

class ReserveSolver:

    def _compile(self):
        """SN67 Harnyx miner — staged research protocol agent. [slot 04 build 2026-08-04T00:41:07+00:00]"""
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
        TASK_TOTAL_BUDGET_SECONDS = 270.0
        FETCH_RETRY_ATTEMPTS = 2
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

        class _ResultIndex:

            def __init__(self) -> None:
                self._by_number: dict[int, dict[str, str]] = {}
                self._spans: dict[int, list[tuple[int, int]]] = {}
                self._window_budget = PAGE_WINDOW_BUDGET_CHARS
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
            """What to show of a page: its opening, plus the densest regions elsewhere.

    A long document's relevant rows are routinely nowhere near its start, so a
    fixed prefix reads the boilerplate and stops. The opening is always kept —
    it carries the identity of the document — and the rest of the allowance goes
    to the regions that actually mention what was asked.
    """
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
            """Evidence numbers to expand, fetched pages before search results."""
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
            """Which parts of the regions read from a source fit in its allowance.

    When everything read fits, everything read is shown. When it does not, the
    choice is made the same way the regions were chosen in the first place — by
    where the question's own words actually occur — rather than by keeping the
    first N characters, which is how a figure a few hundred characters into a
    long region gets dropped on the way to the answer.
    """
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
            """The numbered evidence, projected straight out of the result index.

    Each source contributes its opening plus the regions it was read from; the
    per-source allowance widens when few sources were gathered, so the whole
    digest stays inside one bounded size regardless of how much was collected.
    The turn that writes the answer therefore sees the same regions the research
    turns saw, instead of a shorter prefix of every source.
    """
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
            """The commit turn's own message list, built from the index rather than the
    research conversation. Returns None when there is no evidence to project."""
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
            """The distinct things the question asks for, one role each.

    Two sources, both structural: the interrogative clauses of the question
    itself, and each entity the opening brief put in play. Nothing here keys on
    subject matter — a clause is a role because of where it sits in the
    sentence, not because of what it is about.
    """
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
            """True when some surfaced passage names the role and states a figure for it.

    A page that merely mentions the subject is not the same as a page that
    answers for it, so the test needs both a term hit and a numeral close by.
    """
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
            """Re-project retained pages against whatever the answer still lacks.

    Runs its own loop: each pass takes the roles with nothing stated for them,
    pulls the best-matching unseen region out of every retained page for each,
    and re-tests. It re-enters while a pass is still surfacing new regions, and
    stops as soon as one isn't — no request is issued, so the only cost is the
    text added to the reader's view, which is capped separately.
    """
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
            """Roles a passage now states a figure for, but the answer does not report.

    This is the whole point of localising after a draft exists: the research
    turns wrote the answer from what they had been shown, and localisation
    changes what has been shown. Anything it turns up that the draft does not
    carry is, by construction, material the draft could not have used.
    """
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
            """Rewrite the answer around the passages localisation turned up.

    The returned text REPLACES what the research turns produced; this stage owns
    what is delivered rather than annotating it. A revision is kept only when it
    is a complete answer in its own right, so the rewrite can add what was found
    without the risk of trading a whole answer for a fragment.
    """
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
            """The delivered answer, decided here.

    Always runs. When localisation surfaced nothing the draft is missing it
    returns the draft unchanged, which is the ordinary case; when it did, the
    revision it produces is what goes out.
    """
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

class EscalationController:
    """Answer with the primary pipeline; escalate only when the answer misses."""
    _ESCALATE_BEFORE_S = 150.0
    _TOTAL_BUDGET_S = 230.0

    def __init__(self, primary, reserve, gate):
        self._primary = primary
        self._reserve = reserve
        self._gate = gate

    async def _attempt(self, run, query: Query, budget: float):
        if run is None or budget <= 0:
            return None
        try:
            return await asyncio.wait_for(run(query), timeout=budget)
        except Exception:
            return None

    async def solve(self, query: Query) -> Response:
        started = monotonic()
        first = await self._attempt(self._primary, query, self._TOTAL_BUDGET_S)
        if first is not None and self._gate.satisfies(query, first):
            return first
        elapsed = monotonic() - started
        if elapsed >= self._ESCALATE_BEFORE_S:
            return first if first is not None else Response(text='No answer produced.')
        second = await self._attempt(self._reserve, query, self._TOTAL_BUDGET_S - elapsed)
        candidates = [r for r in (first, second) if r is not None]
        if not candidates:
            return Response(text='No answer produced.')
        return max(candidates, key=lambda r: self._gate.grade(query, r))
_PRIMARY_RUN = _safe_compile(PrimarySolver)
_RESERVE_RUN = _safe_compile(ReserveSolver)
_CONTROLLER = EscalationController(_PRIMARY_RUN, _RESERVE_RUN, ResponseGate())

async def _s17_base_query(query: Query) -> Response:
    return await _CONTROLLER.solve(query)
_TAG_37F6E951="37f6e9514a0b47da805d01563f290245"
import logging as _tag_logging_37f6e951
_tag_logging_37f6e951.getLogger("miner.tag").debug("tag=%s", _TAG_37F6E951)


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
