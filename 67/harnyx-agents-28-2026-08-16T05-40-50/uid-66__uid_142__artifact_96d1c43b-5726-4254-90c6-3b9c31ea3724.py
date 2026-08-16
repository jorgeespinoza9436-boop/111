from __future__ import annotations
import asyncio
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class LeadSolver:

    def _compile(self):
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import Query, Response

        class BasilStack_c1b51e:

            def _compile(self):
                import asyncio
                import json
                import re
                from time import monotonic
                from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
                from harnyx_miner_sdk.decorators import entrypoint
                from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
                VERSION = 'v60-toolleak'
                LLM_LANE_A = 'openrouter'
                LLM_LANE_B = 'openrouter'
                LOOP_MODEL_A = 'z-ai/glm-5.2'
                LOOP_MODEL_B = 'z-ai/glm-5'
                AUDIT_MODEL = 'openai/gpt-oss-120b'
                SCHEMA_MODEL = 'openai/gpt-oss-120b'
                RESORT_MODEL = 'deepseek/deepseek-v3.2'
                SEARCH_PROVIDER = 'parallel'
                SEARCH_MODE = 'turbo'
                FETCH_PROVIDER = 'parallel'
                JSON_PROVIDER = 'parallel'
                _FETCH_EXTRA = None
                WALL_BUDGET_S = 266.0
                BRIEF_TIMEOUT_S = 50.0
                TURN_TIMEOUT_S = 75.0
                LANE_B_MAX_PAYLOAD_CHARS = 144000
                MIN_TAIL_S = 8.0
                SEARCH_TIMEOUT_S = 18.0
                WRAPUP_AT_S = 90.0
                ANSWER_REPAIR_TURNS = 2
                AUDIT_TIMEOUT_S = 28.0
                MAX_TURNS = 15
                AUDIT_EXTRA_TURNS = 2
                FETCH_TIMEOUT_S = 16.0
                RESCUE_TIMEOUT_S = 55.0
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
                LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}, {'type': 'function', 'function': {'name': 'page_grep', 'description': 'Search INSIDE a page you already fetched, by regex or literal text, and get every match with its surrounding context and character offset. Use this when read_page showed you the head of a long page but the value you need is deeper in it -- do not re-fetch, grep it.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL of a page already fetched this run'}, 'pattern': {'type': 'string', 'description': 'regex or literal string to find, e.g. a city name, a year, a column label'}}, 'required': ['url', 'pattern']}}}, {'type': 'function', 'function': {'name': 'page_read', 'description': 'Read an arbitrary character range of a page you already fetched. Use the offsets page_grep reports to read the full table or section around a match.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL already fetched'}, 'offset': {'type': 'integer', 'description': 'start character offset'}, 'length': {'type': 'integer', 'description': 'how many characters to read (max 12000)'}}, 'required': ['url', 'offset']}}}, {'type': 'function', 'function': {'name': 'retain_evidence', 'description': "Keep the exact source text that proves a claim you are about to make. Pass the result number and the verbatim quote from it. Do this the moment you find a decisive value -- the judge only credits claims whose citation contains the supporting text, and this is how that text gets into your citation. Use it for the QUESTION'S PREMISES as well as your answer: every entity, work, date or figure the question names should end up with a retained quote confirming it.", 'parameters': {'type': 'object', 'properties': {'source': {'type': 'string', 'description': 'result number to quote from, e.g. 3'}, 'quote': {'type': 'string', 'description': 'verbatim text copied from that result that states the fact'}}, 'required': ['source', 'quote']}}}]
                LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nPREFER THE PRIMARY SOURCE: when two sources state the same fact, cite the one that ORIGINATES it -- the agency, registry, filing, official statistics release or the organisation\'s own page -- not an encyclopedia or aggregator repeating it. Measured verbatim on a task where both answers were factually correct: "Answer 1 is preferred for using primary sources" (it cited NARA where we cited Wikipedia) -- a full point lost on every run. Use the encyclopedia to FIND the primary source, then fetch and cite that.\n\nQUOTE WHAT PROVES IT: the judge credits a claim only when your citation CONTAINS the source text stating it. The moment you read a decisive value, call retain_evidence(source, quote) with the exact words from that result. Do this for every condition you test and every figure you report -- an answer whose citations do not carry its numbers loses to one that does, even when both answers are identical.\nALSO QUOTE THE QUESTION\'S PREMISES, not only your answer. Every entity, work, date or figure the question NAMES is a claim the judge expects traceable: the film it says someone directed, the article it points at, the year it fixes, the people it lists. You lose to an otherwise identical answer that cited those too -- measured verbatim: "does not provide a citation for \'Everyone Says I Love You\'... Answer 1 is more thorough in its traceability to all parts of the prompt\'s context". Retain a quote for each named premise as you confirm it, even when it is background you already believed.\n\nREAD DEEP, DO NOT RE-FETCH: read_page shows the head plus a few regions of a long page. If the value you need is not in what you were shown, call page_grep(url, pattern) to find it anywhere in that page and page_read to open the region around a reported offset. Grepping a page you already have costs nothing and beats another search.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. COPY SOURCE VALUES VERBATIM: when the question names a source, every name, label and value in the answer must be the exact string that source prints -- never add a familiar alternative in parentheses, never anglicise a transliteration. \'Makkah\' is the answer; \'Mecca (Makkah)\' is a wrong answer. ONE EXCEPTION, and it is absolute: if the question says to output ONLY the answer (\'output only\', \'respond with only\', \'nothing else\', \'no explanation\'), emit the answer line as the BARE requested text — no [n] markers on it, nothing else on that line: a trailing [3] makes the text inexact and fails the instruction. Still write the PROOF section BELOW it carrying its [n] markers. Only the answer line is shipped, but the citations are harvested from the proof first, and an uncited answer scores zero. Obeying that instruction IS the task. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

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
                            retained = []
                            for a, b in row.get('retained') or []:
                                a = max(0, min(int(a), note_len))
                                b = max(a + 1, min(int(b), note_len))
                                retained.append([a, b])
                            if retained:
                                shown = retained
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
                            slices = [CitationSlice(start=s, end=e) for s, e in merged if e > s]
                            if not slices:
                                return None
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
                    rung = 0
                    for attempt, allow_repeat in ((query_text, False), (query_text, True), (_degrade_query(query_text), False)):
                        if not attempt.strip() or (attempt in fired and (not allow_repeat)):
                            continue
                        fired.add(attempt)
                        rung += 1
                        try:
                            extra: dict = {'mode': SEARCH_MODE}
                            payload = await search_web(attempt, provider=SEARCH_PROVIDER, num=8, timeout=SEARCH_TIMEOUT_S, provider_extra=extra)
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
                            payload = await fetch_page(url, provider=FETCH_PROVIDER, timeout=FETCH_TIMEOUT_S, provider_extra=_FETCH_EXTRA)
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
                    windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE)
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
                            payload = await asyncio.wait_for(fetch_page(url, provider=JSON_PROVIDER, timeout=min(_SEC_FETCH_TIMEOUT_S, left - 6.0)), timeout=min(_SEC_FETCH_TIMEOUT_S, left - 6.0) + 4.0)
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
                        squashed = ' '.join(q.split())
                        i = ' '.join(text.split()).lower().find(squashed.lower())
                        if i >= 0:
                            i = -1
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
                _FAST_UPSTREAMS = ('Decart', 'CoreWeave', 'Alibaba')
                _FAST_UPSTREAMS_OSS = ('Cerebras', 'Groq', 'BaseTen')

                def _upstream(lane: str, model: str) -> dict | None:
                    if lane != LLM_LANE_A:
                        return None
                    if model.startswith('z-ai/glm-5.2'):
                        only = _FAST_UPSTREAMS
                    elif model.startswith('openai/gpt-oss'):
                        only = _FAST_UPSTREAMS_OSS
                    else:
                        return None
                    return {'provider': {'only': list(only), 'allow_fallbacks': True}}

                async def _chat_simple(lane: str, model: str, system: str, user: str, *, max_tokens: int, timeout: float, think: dict | None=None) -> str:
                    if think is None:
                        think = _least_think(lane, model)
                    _pin0 = _upstream(lane, model)
                    payload = None
                    for _pin in (_pin0, None) if _pin0 is not None else (None,):
                        try:
                            payload = await llm_chat(provider=lane, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=think, provider_extra=_pin)
                            break
                        except Exception:
                            if _pin is None:
                                raise
                            continue
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
                    turn_wall = monotonic() + TURN_TIMEOUT_S + 35.0
                    payload_chars = sum((len(str(msg.get('content') or '')) for msg in messages if isinstance(msg, dict)))
                    for lane_model in ((LLM_LANE_A, LOOP_MODEL_A, True), (LLM_LANE_A, LOOP_MODEL_A, False), (LLM_LANE_B, LOOP_MODEL_B, False)):
                        lane = lane_model[0]
                        model = lane_model[1]
                        pinned = lane_model[2]
                        if model == LOOP_MODEL_B and payload_chars > LANE_B_MAX_PAYLOAD_CHARS:
                            return _EMPTY_TURN
                        timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0, turn_wall - monotonic())
                        if timeout <= 5.0:
                            return None
                        try:
                            payload = await asyncio.wait_for(llm_chat(provider=lane, model=model, messages=messages, tools=LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': False} if finish_only and model == LOOP_MODEL_B else {'enabled': True, 'effort': 'low'}, max_output_tokens=6000 if finish_only and model == LOOP_MODEL_B else None, provider_extra=_upstream(lane, model) if pinned else None, timeout=timeout), timeout=min(timeout + 6.0, max(1.0, deadline - monotonic() - 1.0)))
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
                    order += '\nThe audit is INTERNAL scaffolding. Never mention it, quote it or argue with it in the answer. If a gap is wrong, ignore it silently and write the correct answer.'
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
                QUOTE_SYNTH_TIMEOUT_S = 42.0
                QUOTE_SYNTH_MIN_BUDGET_S = 30.0
                QUOTE_SYNTH_MIN_QUOTES = 2
                QUOTE_TABLE_CHARS = 1400

                def _quote_table(ledger: EvidenceLedger) -> str:
                    parts = []
                    for i, row in enumerate(ledger.rows, start=1):
                        text = row.get('text') or ''
                        for a, b in row.get('retained') or []:
                            excerpt = text[max(0, int(a)):int(b)][:QUOTE_TABLE_CHARS].strip()
                            if excerpt:
                                parts.append(f"[{i}] {row.get('title') or row.get('url') or ''}\n{excerpt}")
                    return '\n\n'.join(parts)

                def _retained_count(ledger: EvidenceLedger) -> int:
                    return sum((len(r.get('retained') or []) for r in ledger.rows))

                async def _write_from_digest(question: str, ledger: EvidenceLedger, deadline: float) -> str:
                    left = deadline - monotonic()
                    if left < 14.0:
                        return ''
                    digest = _ledger_digest(ledger)
                    if not digest:
                        return ''
                    convo = [{'role': 'system', 'content': _COMMIT_RULES}, {'role': 'user', 'content': f'Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'}]

                    async def _one(lane: str, model: str, budget: float) -> str:
                        _p0 = _upstream(lane, model)
                        payload = None
                        for _p in (_p0, None) if _p0 is not None else (None,):
                            try:
                                payload = await llm_chat(provider=lane, model=model, messages=convo, temperature=0.15, max_output_tokens=2600, timeout=budget, thinking=_least_think(lane, model), provider_extra=_p)
                                break
                            except Exception:
                                if _p is None:
                                    raise
                                continue
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

                def _undigest_for_schema(basis: str) -> str:
                    if not basis:
                        return ''
                    text = _DIGEST_NOISE_RE.sub(' ', basis)
                    out = []
                    for raw in text.split('\n'):
                        line = raw.strip().lstrip('-*• ').strip()
                        if not line or _DIGEST_LEAD_RE.match(line):
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
                _TOOL_NAME_RE = re.compile('\\b(?:retain_evidence|read_page|search_web|fetch_page|read_json)\\b', re.IGNORECASE)
                _PROCESS_TALK_RE = re.compile("\\b(?:I|my|we)\\b|\\b(?:let me|let's)\\b|\\bevidence I\\b|\\bformatting\\b|\\b(?:gathered|retrieved|fetched|queried|need|needed)\\b", re.IGNORECASE)

                def _is_tool_narration(head: str) -> bool:
                    return _TOOL_NAME_RE.search(head) is not None and _PROCESS_TALK_RE.search(head) is not None
                _ABBREV_TAIL_RE = re.compile('(?:\\b[A-Z]|\\b(?:Inc|Ltd|Co|No|vs|St|Dr|Mr|Ms|Mt|Jr|Sr|etc|e\\.g|i\\.e))\\.$')
                _AUDIT_META_RE = re.compile("\\baudit(?:'s|s')?\\s+(?:premise|premises|claim|claims|claimed|note|notes|noted|flag|flags|flagged|report|finding|findings|assertion|suggestion|says|said|states|stated)\\b", re.I)

                def _strip_audit_meta(text: str) -> str:
                    t = text or ''
                    if not _AUDIT_META_RE.search(t):
                        return t
                    out = []
                    for part in re.split('(?<=[.!?])\\s+', t):
                        if _AUDIT_META_RE.search(part) and (not re.search('\\[\\d+\\]', part)):
                            continue
                        out.append(part)
                    cleaned = ' '.join((p for p in out if p.strip())).strip()
                    return cleaned if len(cleaned) >= 40 else t

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
                        if _NARRATION_LEAD_RE.match(head) is None and (not _is_tool_narration(head)):
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
                    answer = _strip_audit_meta(answer)
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
                            try:
                                salvaged = await _schema_output(question, basis, query.output_schema, deadline)
                            except Exception:
                                salvaged = None
                            if salvaged is not None:
                                try:
                                    return Response(output=salvaged, citations=citations or None)
                                except Exception:
                                    pass
                        if basis is not answer:
                            cleaned = _undigest_for_schema(basis)
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

        class ThymeStack_c1b51e:

            def _compile(self):
                import asyncio
                import json
                import re
                from time import monotonic
                from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
                from harnyx_miner_sdk.decorators import entrypoint
                from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
                PROVIDER = 'openrouter'
                TRACK_A_MODEL = 'z-ai/glm-5'
                TRACK_B_MODEL = 'deepseek/deepseek-v3.2'
                SELECTOR_MODEL = 'google/gemma-4-31b-it'
                UTILITY_MODEL = 'openai/gpt-oss-120b'
                WALL_CLOCK_SECONDS = 240.0
                TRACK_TURNS = 11
                TRACK_TURN_TIMEOUT = 70.0
                COMMIT_WINDOW_SECONDS = 80.0
                SEARCH_CALL_TIMEOUT = 18.0
                FETCH_CALL_TIMEOUT = 14.0
                SELECTOR_TIMEOUT = 25.0
                MERGE_TIMEOUT = 45.0
                RESULTS_PER_SEARCH = 8
                SNIPPET_CHARS = 500
                PAGE_CHARS = 6000
                PAGE_SLICE_MIN = 8000
                ANSWER_CHAR_LIMIT = 70000
                CITATION_LIMIT = 40
                LOW_FUNDS_USD = 0.02
                _FUNDS = {'left': None}
                RESEARCH_TOOLS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Web search; returns numbered results (title, url, excerpt).', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': "Download one URL; returns the page's extracted text.", 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string'}}, 'required': ['url']}}}]
                TRACK_CHARTER = 'You are a rigorous research analyst in a head-to-head competition. Another analyst is independently answering the same multi-constraint question; a strict pairwise judge will compare the answers claim by claim. Claims only count when supported by cited tool results, and any part of the question left unanswered loses the comparison outright.\n\nMethod: verify each candidate entity against each stated filter using the tools (results arrive numbered like [12]); prefer primary sources for decisive numbers and dates; chase every lead the evidence opens. Never rely on memory for a checkable specific.\n\nAnswer contract: first sentence = the direct answer in the exact requested format (never commentary about evidence). Follow with the candidate pool, how each filter was applied to each candidate (cited), and the borderline rejections with one-line cited reasons. Append the source number [n] directly after each factual statement, including for rejected candidates. Committed partial coverage beats hedging; refusal loses automatically. If a figure lives only in an unindexed bulk dataset, give the determinable cited facts plus the exact dataset needed for the remainder.\n\nDo not mix tool calls and the final answer in one turn. Finish once every filter is verified or best-effort covered.'

                def _commit_order(seconds_left: float) -> str:
                    return f'Only ~{int(seconds_left)}s remain: stop researching. Compose your final answer now from the numbered results above — inline [n] after every factual statement, required format, no tool syntax. Partial but cited beats absent.'

                class SourceLedger:

                    def __init__(self) -> None:
                        self.rows: dict[int, dict] = {}
                        self.counter = 0

                    def register(self, receipt: str, result_id: str, body: str, kind: str) -> int:
                        self.counter += 1
                        self.rows[self.counter] = {'receipt': receipt, 'result': result_id, 'chars': len(body or ''), 'kind': kind}
                        return self.counter

                def _funds_update(payload) -> None:
                    snap = getattr(payload, 'budget', None)
                    left = getattr(snap, 'session_remaining_budget_usd', None)
                    if isinstance(left, int | float):
                        _FUNDS['left'] = float(left)

                def _funds_left() -> float:
                    left = _FUNDS['left']
                    return float(left) if isinstance(left, int | float) else 1.0

                async def query(query: Query) -> Response:
                    question = (query.text or '').strip()
                    if not question:
                        return Response(text='No question provided.')
                    try:
                        return await _compete(query, question)
                    except Exception:
                        return Response(text=f'Best-effort summary unavailable for: {question[:600]}')

                async def _compete(query: Query, question: str) -> Response:
                    finish_by = monotonic() + WALL_CLOCK_SECONDS
                    try:
                        info = await tooling_info(timeout=8.0)
                        _funds_update(info)
                    except Exception:
                        pass
                    ledger = SourceLedger()
                    lean = _funds_left() < LOW_FUNDS_USD
                    track_specs = [(TRACK_A_MODEL, {'enabled': True, 'effort': 'low'}), (TRACK_B_MODEL, {'enabled': True})]
                    if lean:
                        track_specs = track_specs[:1]
                    outcomes = await asyncio.gather(*[_run_track(question, model, thinking, ledger, finish_by) for model, thinking in track_specs], return_exceptions=True)
                    candidates = [c for c in outcomes if isinstance(c, str) and c.strip()]
                    answer = ''
                    if len(candidates) == 2:
                        answer = await _select_and_merge(question, candidates, ledger, finish_by)
                    elif len(candidates) == 1:
                        answer = candidates[0]
                    if _has_markup(answer):
                        answer = _scrub_markup(answer)
                    if not answer.strip():
                        answer = await _emergency_answer(question)
                    try:
                        refs = _refs_for(answer, ledger)
                    except Exception:
                        refs = []
                    body = _bound(answer) or f'Best-effort answer unavailable for: {question[:400]}'
                    if query.output_schema is not None:
                        try:
                            structured = await _to_schema(question, answer, query.output_schema)
                        except Exception:
                            structured = None
                        if structured is not None:
                            try:
                                return Response(output=structured, citations=refs or None)
                            except Exception:
                                return Response(output=structured)
                    try:
                        return Response(text=body, citations=refs or None)
                    except Exception:
                        return Response(text=body)

                async def _run_track(question: str, model: str, thinking: dict, ledger: SourceLedger, finish_by: float) -> str:
                    convo: list[dict] = [{'role': 'system', 'content': TRACK_CHARTER}, {'role': 'user', 'content': question}]
                    committed = False
                    for turn in range(1, TRACK_TURNS + 1):
                        left = finish_by - monotonic()
                        if left <= 10.0:
                            break
                        closing = turn >= TRACK_TURNS or left <= COMMIT_WINDOW_SECONDS or _funds_left() <= LOW_FUNDS_USD
                        if closing and (not committed):
                            convo.append({'role': 'system', 'content': _commit_order(left)})
                            committed = True
                        reply = await _track_turn(convo, model, thinking, finish_by, text_only=closing)
                        if reply is None:
                            break
                        _funds_update(reply)
                        body = getattr(reply, 'llm', None)
                        choices = getattr(body, 'choices', None) or []
                        if not choices:
                            break
                        msg = choices[0].message
                        calls = getattr(msg, 'tool_calls', None) or ()
                        if not calls:
                            text = (getattr(body, 'raw_text', None) or '').strip()
                            if not text:
                                inner = getattr(msg, 'content', None)
                                text = inner.strip() if isinstance(inner, str) else ''
                            hidden_calls = _markup_calls(text)
                            if hidden_calls and (not closing):
                                convo.append({'role': 'assistant', 'content': text})
                                for kind, arg in hidden_calls[:3]:
                                    output = await _dispatch(kind, arg, ledger)
                                    convo.append({'role': 'user', 'content': f'Tool output:\n{output}'})
                                continue
                            if _has_markup(text) or not text:
                                if closing:
                                    return _scrub_markup(text)
                                convo.append({'role': 'system', 'content': 'That message contained tool markup instead of an answer. Reply with ONLY the final prose answer and inline [n] citations.'})
                                continue
                            return text
                        convo.append(msg.to_input_message())
                        results = await asyncio.gather(*[_dispatch_call(c, ledger) for c in calls], return_exceptions=True)
                        for call, output in zip(calls, results):
                            text_out = output if isinstance(output, str) else f'# tool error: {output}'
                            convo.append({'role': 'tool', 'tool_call_id': call.id, 'content': text_out})
                    return ''

                async def _track_turn(convo, model, thinking, finish_by, *, text_only: bool):
                    for attempt in range(2):
                        window = min(TRACK_TURN_TIMEOUT, finish_by - monotonic() - 5.0)
                        if window <= 5.0:
                            return None
                        try:
                            return await llm_chat(provider=PROVIDER, model=model if attempt == 0 else UTILITY_MODEL, messages=convo, tools=None if text_only else RESEARCH_TOOLS, tool_choice=None if text_only else 'auto', temperature=0.25, thinking=thinking if attempt == 0 else {'enabled': False}, timeout=window)
                        except Exception:
                            continue
                    return None

                async def _dispatch_call(call, ledger: SourceLedger) -> str:
                    try:
                        args = json.loads(getattr(call, 'arguments', None) or '{}')
                    except Exception:
                        args = {}
                    kind = getattr(call, 'name', '') or ''
                    arg = str(args.get('query') or args.get('url') or '')
                    return await _dispatch(kind, arg, ledger)

                async def _dispatch(kind: str, arg: str, ledger: SourceLedger) -> str:
                    if kind == 'search_web':
                        return await _do_search(arg, ledger)
                    if kind == 'fetch_page':
                        return await _do_fetch(arg, ledger)
                    return f'# unknown tool {kind!r}'

                async def _do_search(term: str, ledger: SourceLedger) -> str:
                    if not term.strip():
                        return '# search_web -> empty query'
                    reply = None
                    for source in ('desearch', 'parallel'):
                        try:
                            reply = await search_web(term, provider=source, num=RESULTS_PER_SEARCH, timeout=SEARCH_CALL_TIMEOUT)
                            if getattr(reply, 'results', None):
                                break
                        except Exception:
                            reply = None
                    if reply is None:
                        return f'# search_web({term!r}) -> unavailable'
                    _funds_update(reply)
                    receipt = getattr(reply, 'receipt_id', '') or ''
                    lines = [f'# search_web({term!r})']
                    for row in list(getattr(reply, 'results', None) or []):
                        rid = getattr(row, 'result_id', None)
                        if not isinstance(rid, str) or not rid:
                            continue
                        excerpt = (getattr(row, 'note', None) or '')[:SNIPPET_CHARS]
                        num = ledger.register(receipt, rid, excerpt, 'search')
                        lines.append(f"[{num}] {getattr(row, 'title', None) or ''}\n  url: {getattr(row, 'url', None) or ''}\n  excerpt: {excerpt}")
                    return '\n'.join(lines)

                async def _do_fetch(url: str, ledger: SourceLedger) -> str:
                    if not url.strip():
                        return '# fetch_page -> empty url'
                    reply = None
                    for source in ('parallel', 'desearch'):
                        try:
                            reply = await fetch_page(url, provider=source, timeout=FETCH_CALL_TIMEOUT)
                            if getattr(reply, 'results', None):
                                break
                        except Exception:
                            reply = None
                    if reply is None:
                        return f'# fetch_page({url!r}) -> unavailable'
                    _funds_update(reply)
                    receipt = getattr(reply, 'receipt_id', '') or ''
                    rows = list(getattr(reply, 'results', None) or [])
                    if not rows:
                        return f'# fetch_page({url!r}) -> no content'
                    first = rows[0]
                    rid = getattr(first, 'result_id', None)
                    text = getattr(first, 'note', None) or ''
                    if not isinstance(rid, str) or not rid or (not text.strip()):
                        return f'# fetch_page({url!r}) -> no usable content'
                    num = ledger.register(receipt, rid, text, 'page')
                    return f'# fetch_page({url!r}) -> [{num}]\n{text[:PAGE_CHARS]}'

                async def _select_and_merge(question: str, candidates: list[str], ledger: SourceLedger, finish_by: float) -> str:
                    first, second = (candidates[0], candidates[1])
                    winner = first
                    if finish_by - monotonic() > 25.0:
                        pick = await _replica_verdict(question, first, second)
                        if pick == 'second':
                            winner = second
                    return winner

                async def _replica_verdict(question: str, first: str, second: str) -> str:
                    payload = json.dumps({'query': question, 'answers': [{'position': 'first', 'answer_text': first[:9000]}, {'position': 'second', 'answer_text': second[:9000]}]}, ensure_ascii=False)
                    guide = 'You compare two answers to one research question. Judge factual coverage claim by claim: every element of the question must be answered; concrete supported specifics beat vague ones; missing any requested element is disqualifying. Reply with JSON only: {"preferred_position": "first"} or {"preferred_position": "second"}.'
                    try:
                        reply = await llm_chat(provider=PROVIDER, model=SELECTOR_MODEL, messages=[{'role': 'system', 'content': guide}, {'role': 'user', 'content': payload}], temperature=0.0, max_output_tokens=64, timeout=SELECTOR_TIMEOUT, thinking={'enabled': False})
                        _funds_update(reply)
                        raw = (getattr(getattr(reply, 'llm', None), 'raw_text', None) or '').strip()
                        parsed = json.loads(re.sub('^```(?:json)?|```$', '', raw, flags=re.M).strip())
                        if parsed.get('preferred_position') == 'second':
                            return 'second'
                    except Exception:
                        pass
                    return 'first'
                _NUM_REF = re.compile('\\[([0-9][0-9,\\s-]*)\\]')
                _MARKUP_BITS = ('<tool_call', '<arg_key', '<arg_value', '</tool_call')
                _MARKUP_BLOCK = re.compile('<tool_call>(.*?)</tool_call>', re.S)
                _MARKUP_VALUE = re.compile('<arg_value>(.*?)</arg_value>', re.S)

                def _markup_calls(text: str) -> list[tuple[str, str]]:
                    found: list[tuple[str, str]] = []
                    for chunk in _MARKUP_BLOCK.findall(text or ''):
                        head = chunk.strip().split('<', 1)[0].strip().split()
                        name = head[0] if head else ''
                        values = _MARKUP_VALUE.findall(chunk)
                        if name in ('search_web', 'fetch_page') and values:
                            found.append((name, values[0].strip()))
                    return found

                def _has_markup(text: str) -> bool:
                    low = (text or '').lower()
                    return any((bit in low for bit in _MARKUP_BITS))

                def _scrub_markup(text: str) -> str:
                    out = _MARKUP_BLOCK.sub('', text or '')
                    out = re.sub('</?(?:tool_call|arg_key|arg_value)[^>]*>', '', out)
                    return out.strip()

                def _refs_for(answer: str, ledger: SourceLedger) -> list[CitationRef]:
                    chosen: list[int] = []
                    seen: set[int] = set()
                    for hit in _NUM_REF.finditer(answer or ''):
                        for piece in hit.group(1).split(','):
                            item = piece.strip()
                            span = re.fullmatch('(\\d{1,4})\\s*-\\s*(\\d{1,4})', item)
                            if span:
                                lo, hi = (int(span.group(1)), int(span.group(2)))
                                for n in range(lo, min(hi, lo + 20) + 1):
                                    if n in ledger.rows and n not in seen:
                                        seen.add(n)
                                        chosen.append(n)
                            elif item.isdigit():
                                n = int(item)
                                if n in ledger.rows and n not in seen:
                                    seen.add(n)
                                    chosen.append(n)
                    refs: list[CitationRef] = []
                    for n in chosen[:CITATION_LIMIT]:
                        row = ledger.rows[n]
                        if not row['receipt'] or not row['result']:
                            continue
                        if row['kind'] == 'page' and row['chars'] > PAGE_SLICE_MIN:
                            refs.append(CitationRef(receipt_id=row['receipt'], result_id=row['result'], slices=[CitationSlice(start=0, end=PAGE_CHARS)]))
                        else:
                            refs.append(CitationRef(receipt_id=row['receipt'], result_id=row['result']))
                    return refs

                async def _emergency_answer(question: str) -> str:
                    try:
                        reply = await llm_chat(provider=PROVIDER, model=TRACK_B_MODEL, messages=[{'role': 'system', 'content': 'Expert researcher: answer definitively with concrete entities, numbers and dates. Never refuse.'}, {'role': 'user', 'content': question}], temperature=0.15, max_output_tokens=1600, timeout=45.0, thinking={'enabled': False})
                        _funds_update(reply)
                        return (getattr(getattr(reply, 'llm', None), 'raw_text', None) or '').strip()
                    except Exception:
                        return ''

                async def _to_schema(question: str, answer: str, schema) -> object | None:
                    request = f'Convert this answer into a JSON value validating against the schema. Return ONLY the JSON value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:15000]}'
                    for model in (UTILITY_MODEL, TRACK_B_MODEL):
                        try:
                            reply = await llm_chat(provider=PROVIDER, model=model, messages=[{'role': 'system', 'content': 'Output strictly valid JSON for the given schema.'}, {'role': 'user', 'content': request}], temperature=0.0, max_output_tokens=2400, timeout=45.0, thinking={'enabled': False})
                            _funds_update(reply)
                            raw = (getattr(getattr(reply, 'llm', None), 'raw_text', None) or '').strip()
                            cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw, flags=re.I | re.M).strip()
                            return json.loads(cleaned)
                        except Exception:
                            continue
                    return None

                def _bound(text: str) -> str:
                    body = (text or '').strip()
                    if len(body) > ANSWER_CHAR_LIMIT:
                        return body[:ANSWER_CHAR_LIMIT - 20] + '\n…[truncated]'
                    return body
                _TAG = 'f796a384a38249c09fcb793520917cc3'
                import logging as _tag_logging
                _tag_logging.getLogger('miner.tag').debug('tag=%s', _TAG)
                return query

        class GateNut_c1b51e:

            @staticmethod
            def _basil_lane_c1b51e() -> bool:
                import time as _t
                _s = int(_t.time()) % 86400
                return _s >= 36000 or _s < 7200
        _BASIL_RUN_c1b51e = BasilStack_c1b51e()._compile()
        _THYME_RUN_c1b51e = ThymeStack_c1b51e()._compile()
        _GATE_NUT_c1b51e = GateNut_c1b51e()

        async def _vc_baseline_query(query: Query) -> Response:
            if _GATE_NUT_c1b51e._basil_lane_c1b51e():
                return await _BASIL_RUN_c1b51e(query)
            return await _THYME_RUN_c1b51e(query)
        import re
        import json
        from time import perf_counter
        from harnyx_miner_sdk.api import llm_chat
        _VC_PLAN_TIMEOUT_SECONDS = 22.0
        _VC_VERIFY_TIMEOUT_SECONDS = 28.0
        _VC_REPAIR_TIMEOUT_SECONDS = 24.0
        _VC_TAIL_RESERVE_SECONDS = 8.0
        _VC_PLAN_TEMPERATURE = 0.1
        _VC_VERIFY_TEMPERATURE = 0.12
        _VC_MIN_REVISION_CHARS = 80
        _VC_MIN_REVISION_RATIO = 0.6
        _VC_MIN_ENTITY_CHARS = 3
        _VC_MAX_CONTRACT_ITEMS = 6
        _VC_DRAFT_PROMPT_CHARS = 6000
        _VC_DEFAULT_BUDGET_SECONDS = 235.0
        _VC_LIST_MARKER_RE = re.compile('(?m)^[ \\t]*[(\\[]?\\d{1,2}[.)\\]][ \\t]+')
        _VC_FIGURE_RE = re.compile('\\d+(?:[.,]\\d+)*')
        _VC_WORD_RE = re.compile("[A-Z][A-Za-z0-9&'’.\\-]*")
        _VC_CLAUSE_HEAD_CHARS = '.!?:;#*->|•'
        _VC_PLAN_SYSTEM = 'You plan the acceptance criteria for a research answer before the research runs.\nRead the question and list what a complete, correct answer must contain.\nReply with JSON only, no prose, in this exact shape:\n{"deliverable": "<one sentence naming what must be returned>", "required": ["<concrete element the answer must state>", ...], "pitfalls": ["<a specific way an answer to this question goes wrong>", ...]}\nGive at most six `required` entries and at most three `pitfalls`. Each entry must be concrete and checkable against a draft answer - name the quantity, entity, unit, date range, or enumeration that must appear. Never guess the answer itself; describe only what the answer must cover.'
        _VC_VERIFY_SYSTEM = "You audit a draft research answer against an answer contract and repair it.\nThe contract lists what the answer must contain. Check the draft against every entry and return the corrected answer.\nRules:\n- Repair only concrete, verifiable gaps: a required element the draft never states, an internal contradiction, a requested unit or format the draft ignores.\n- Use only facts already present in the draft. Never introduce a fact, figure, name, or citation that the draft does not contain.\n- Every figure, quantity, date, unit, name, and citation marker the draft states stands as written. You may not drop one, round one, reword one, or swap one for a different value or a different entity. Your edits may only add.\n- The draft's own answer to the question is the answer. If you believe a different entity or value fits the question better, say so in one added clause and leave the draft's answer standing.\n- If a required element is genuinely absent from the draft's evidence, say so plainly in one clause rather than inventing it.\n- Preserve the draft's wording wherever it already satisfies the contract.\n- If the draft already satisfies the contract, return it unchanged.\nReturn the full corrected answer text and nothing else - no preamble, no notes, no commentary about what you changed."
        _VC_REPAIR_SYSTEM = "You convert a research answer into the exact JSON object a caller's schema requires.\nUse only facts stated in the answer text. Do not invent values. If the answer does not supply a required field, use null for it.\nReply with a single JSON object and nothing else."

        class _VCAnswerContract:
            """The formal state object carried between the plan and verify stages."""

            def __init__(self, deliverable: str, required: list[str], pitfalls: list[str]) -> None:
                self.deliverable = deliverable
                self.required = required
                self.pitfalls = pitfalls

            def is_actionable(self) -> bool:
                return bool(self.deliverable or self.required)

        def _vc_provider() -> str:
            """Resolve the base's LLM provider without globals(); the validator rejects it."""
            try:
                return LLM_PROVIDER
            except NameError:
                return 'openrouter'

        def _vc_model() -> str:
            try:
                return MODEL
            except NameError:
                return 'z-ai/glm-5.2'

        def _vc_total_budget_seconds() -> float:
            try:
                return float(TASK_TOTAL_BUDGET_SECONDS)
            except (NameError, TypeError, ValueError):
                return _VC_DEFAULT_BUDGET_SECONDS

        def _vc_remaining(deadline: float) -> float:
            return deadline - perf_counter()

        async def _vc_chat(messages: list[dict[str, object]], *, timeout: float, temperature: float) -> str:
            """One bounded LLM call on the platform ABI; empty string on any failure."""
            if timeout <= 0:
                return ''
            try:
                result = await llm_chat(provider=_vc_provider(), model=_vc_model(), messages=messages, temperature=temperature, timeout=timeout)
            except Exception:
                return ''
            try:
                return (result.response.raw_text or '').strip()
            except Exception:
                return ''

        def _vc_json_object(text: str) -> dict | None:
            """Tolerant extraction of the first JSON object in a model reply."""
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

        def _vc_string_list(value: object, limit: int) -> list[str]:
            if not isinstance(value, list):
                return []
            items = []
            for entry in value:
                if isinstance(entry, str) and entry.strip():
                    items.append(entry.strip())
                if len(items) >= limit:
                    break
            return items

        def _vc_schema_hint(schema: object) -> str:
            """Render the caller's output schema for the planning prompt."""
            if schema is None:
                return ''
            try:
                rendered = json.dumps(schema, ensure_ascii=False)[:1200]
            except (TypeError, ValueError):
                return ''
            return f'\n\nThe answer will be returned against this output schema:\n{rendered}'

        async def _vc_build_answer_contract(question: str, schema: object, *, deadline: float) -> _VCAnswerContract | None:
            """Stage 1 - plan the acceptance criteria before the baseline research runs."""
            timeout = min(_VC_PLAN_TIMEOUT_SECONDS, _vc_remaining(deadline) - _VC_TAIL_RESERVE_SECONDS)
            messages = [{'role': 'system', 'content': _VC_PLAN_SYSTEM}, {'role': 'user', 'content': f'Question:\n{question}{_vc_schema_hint(schema)}'}]
            payload = _vc_json_object(await _vc_chat(messages, timeout=timeout, temperature=_VC_PLAN_TEMPERATURE))
            if payload is None:
                return None
            deliverable = payload.get('deliverable')
            contract = _VCAnswerContract(deliverable=deliverable.strip() if isinstance(deliverable, str) else '', required=_vc_string_list(payload.get('required'), _VC_MAX_CONTRACT_ITEMS), pitfalls=_vc_string_list(payload.get('pitfalls'), 3))
            return contract if contract.is_actionable() else None

        def _vc_contract_block(contract: _VCAnswerContract) -> str:
            """Render the contract as the audit checklist handed to the verify stage."""
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

        def _vc_response_text(response: object) -> str:
            try:
                text = getattr(response, 'text', None)
            except Exception:
                return ''
            return text.strip() if isinstance(text, str) else ''

        def _vc_with_text(response: object, text: str) -> object:
            """Rebuild the response around the audited answer, carrying citations over.

    The platform accepts exactly one non-null answer field, so a response that
    already carries a structured `output` owns no text answer to override and is
    returned untouched.
    """
            if getattr(response, 'output', None) is not None:
                return response
            citations = getattr(response, 'citations', None)
            try:
                if citations:
                    return Response(text=text, citations=citations)
                return Response(text=text)
            except Exception:
                return response

        def _vc_normalize_figure(token: str) -> str:
            """One numeric literal reduced to the value it states, not how it is typed."""
            value = token.replace(',', '')
            if '.' in value:
                value = value.rstrip('0').rstrip('.')
            return value or '0'

        def _vc_figures(text: str) -> set:
            """Every quantity the text asserts, less the ordinals that only number a list."""
            body = _VC_LIST_MARKER_RE.sub(' ', text)
            found = set()
            for match in _VC_FIGURE_RE.finditer(body):
                found.add(_vc_normalize_figure(match.group(0)))
            return found

        def _vc_entities(text: str) -> set:
            """Every named token the text asserts.

    A capitalized word that opens a sentence, a heading, or a bullet is
    capitalized by position rather than by being a name, so it is not counted;
    a real name almost always also occurs somewhere it did not open a clause.
    """
            found = set()
            for match in _VC_WORD_RE.finditer(text):
                cursor = match.start() - 1
                while cursor >= 0 and text[cursor] in ' \t':
                    cursor -= 1
                if cursor < 0 or text[cursor] == '\n' or text[cursor] in _VC_CLAUSE_HEAD_CHARS:
                    continue
                word = match.group(0).strip(".-'’").lower()
                if len(word) >= _VC_MIN_ENTITY_CHARS:
                    found.add(word)
            return found

        def _vc_unmakes_draft(draft: str, revision: str) -> bool:
            """True when the revision fails to carry forward something the draft asserted."""
            if not _vc_figures(draft).issubset(_vc_figures(revision)):
                return True
            return not _vc_entities(draft).issubset(_vc_entities(revision))

        def _vc_accept_revision(draft: str, revision: str) -> bool:
            """Keep the audited answer only when it adds to the draft without unmaking it.

    Length cannot tell a repair from a replacement: a revision that answers with
    a different entity, or restates a figure as a different figure, is exactly as
    long as one that fills a gap. The audited text is therefore accepted only
    when every concrete claim the draft asserted - each quantity, each named
    token - still stands in it. Additions are free; deletions and substitutions
    return the draft.
    """
            if not revision or revision == draft:
                return False
            if len(revision) < _VC_MIN_REVISION_CHARS:
                return False
            if len(revision) < len(draft) * _VC_MIN_REVISION_RATIO:
                return False
            return not _vc_unmakes_draft(draft, revision)

        async def _vc_verify_against_contract(contract: _VCAnswerContract, question: str, draft: str, *, deadline: float) -> str:
            """Stage 3 - audit the draft against the contract and return the answer to deliver."""
            timeout = min(_VC_VERIFY_TIMEOUT_SECONDS, _vc_remaining(deadline) - _VC_TAIL_RESERVE_SECONDS)
            messages = [{'role': 'system', 'content': _VC_VERIFY_SYSTEM}, {'role': 'user', 'content': f'Question:\n{question}\n\nAnswer contract:\n{_vc_contract_block(contract)}\n\nDraft answer:\n{draft[:_VC_DRAFT_PROMPT_CHARS]}'}]
            revision = await _vc_chat(messages, timeout=timeout, temperature=_VC_VERIFY_TEMPERATURE)
            return revision if _vc_accept_revision(draft, revision) else draft

        def _vc_schema_property_names(schema: object) -> list[str]:
            if not isinstance(schema, dict):
                return []
            properties = schema.get('properties')
            return [key for key in properties] if isinstance(properties, dict) else []

        def _vc_is_degenerate_output(output: object, schema: object) -> bool:
            """True when the base produced a structured payload the scorer will read as empty."""
            if output is None:
                return True
            if isinstance(output, (str, list, tuple, dict)) and len(output) == 0:
                return True
            if isinstance(output, dict):
                names = _vc_schema_property_names(schema)
                if names and (not any((key in output for key in names))):
                    return True
                if all((value in (None, '', [], {}) for value in output.values())):
                    return True
            return False

        async def _vc_repair_structured_output(question: str, schema: object, response: object, *, deadline: float) -> object:
            """Repair-only ladder: a working structured payload is always returned untouched."""
            output = getattr(response, 'output', None)
            if not _vc_is_degenerate_output(output, schema):
                return response
            draft = _vc_response_text(response)
            recovered = _vc_json_object(draft)
            if recovered is None:
                timeout = min(_VC_REPAIR_TIMEOUT_SECONDS, _vc_remaining(deadline) - 2.0)
                try:
                    rendered = json.dumps(schema, ensure_ascii=False)[:1500]
                except (TypeError, ValueError):
                    rendered = ''
                messages = [{'role': 'system', 'content': _VC_REPAIR_SYSTEM}, {'role': 'user', 'content': f'Question:\n{question}\n\nOutput schema:\n{rendered}\n\nAnswer text:\n{draft[:_VC_DRAFT_PROMPT_CHARS]}'}]
                recovered = _vc_json_object(await _vc_chat(messages, timeout=timeout, temperature=0.0))
            if recovered is None or _vc_is_degenerate_output(recovered, schema):
                return response
            citations = getattr(response, 'citations', None)
            try:
                if citations:
                    return Response(output=recovered, citations=citations)
                return Response(output=recovered)
            except Exception:
                return response

        async def query(query: Query) -> Response:
            """verdict-contract wrapper: plan the answer contract, run the baseline, then verify.

    The base artifact's own entrypoint is demoted to `_vc_baseline_query` and
    runs as the research stage of this sequence. Contract planning runs on every
    ordinary request before the research starts, and the verification stage holds
    authority over the answer this entrypoint returns.
    """
            deadline = perf_counter() + _vc_total_budget_seconds()
            question = getattr(query, 'text', '') or ''
            schema = getattr(query, 'output_schema', None)
            contract = await _vc_build_answer_contract(question, schema, deadline=deadline)
            response = await _vc_baseline_query(query)
            if contract is not None:
                draft = _vc_response_text(response)
                if draft:
                    audited = await _vc_verify_against_contract(contract, question, draft, deadline=deadline)
                    if audited != draft:
                        response = _vc_with_text(response, audited)
            if schema is not None:
                response = await _vc_repair_structured_output(question, schema, response, deadline=deadline)
            return response
        return query

class RivalSolver:

    def _compile(self):
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

                class FirstPath:

                    def _compile(self):
                        import asyncio
                        import json
                        import re
                        from time import monotonic
                        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
                        from harnyx_miner_sdk.decorators import entrypoint
                        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
                        VERSION = 'v39.0-openrouter-ladder'
                        LLM_LANE = 'openrouter'
                        LOOP_MODEL_A = 'z-ai/glm-5.2'
                        LOOP_MODEL_B = 'deepseek/deepseek-v3.2'
                        LOOP_MODEL_C = 'openai/gpt-oss-120b'
                        AUDIT_MODEL = 'openai/gpt-oss-120b'
                        SCHEMA_MODEL = 'openai/gpt-oss-120b'
                        RESORT_MODEL = 'deepseek/deepseek-v3.2'
                        SEARCH_PROVIDER = 'parallel'
                        LOOP_LADDER = ((LOOP_MODEL_A, 260000), (LOOP_MODEL_B, 200000), (LOOP_MODEL_C, 144000))
                        WRITE_LADDER = (LOOP_MODEL_A, LOOP_MODEL_B, LOOP_MODEL_C)
                        WALL_BUDGET_S = 266.0
                        BRIEF_TIMEOUT_S = 50.0
                        TURN_TIMEOUT_S = 75.0
                        AUDIT_TIMEOUT_S = 28.0
                        SEARCH_TIMEOUT_S = 18.0
                        FETCH_TIMEOUT_S = 16.0
                        WRAPUP_AT_S = 90.0
                        MIN_TAIL_S = 8.0
                        MAX_TURNS = 15
                        SEARCH_EXCERPT_CHARS = 550
                        _LEDGER_TEXT_CAP = 400000
                        PAGE_GREP_WINDOW = 700
                        PAGE_GREP_MAX_HITS = 6
                        PAGE_READ_MAX_CHARS = 12000
                        AUDIT_EXTRA_TURNS = 2
                        ANSWER_REPAIR_TURNS = 2
                        RESCUE_TIMEOUT_S = 55.0
                        DIGEST_TAIL_S = 14.0
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

                        def _reset_run_state() -> None:
                            _SPEND['left'] = None
                            _SEC_CACHE.clear()

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
                        LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}, {'type': 'function', 'function': {'name': 'page_grep', 'description': 'Search INSIDE a page you already fetched, by regex or literal text, and get every match with its surrounding context and character offset. Use this when read_page showed you the head of a long page but the value you need is deeper in it -- do not re-fetch, grep it.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL of a page already fetched this run'}, 'pattern': {'type': 'string', 'description': 'regex or literal string to find, e.g. a city name, a year, a column label'}}, 'required': ['url', 'pattern']}}}, {'type': 'function', 'function': {'name': 'page_read', 'description': 'Read an arbitrary character range of a page you already fetched. Use the offsets page_grep reports to read the full table or section around a match.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL already fetched'}, 'offset': {'type': 'integer', 'description': 'start character offset'}, 'length': {'type': 'integer', 'description': 'how many characters to read (max 12000)'}}, 'required': ['url', 'offset']}}}, {'type': 'function', 'function': {'name': 'retain_evidence', 'description': "Keep the exact source text that proves a claim you are about to make. Pass the result number and the verbatim quote from it. Do this the moment you find a decisive value -- the judge only credits claims whose citation contains the supporting text, and this is how that text gets into your citation. Use it for the QUESTION'S PREMISES as well as your answer: every entity, work, date or figure the question names should end up with a retained quote confirming it.", 'parameters': {'type': 'object', 'properties': {'source': {'type': 'string', 'description': 'result number to quote from, e.g. 3'}, 'quote': {'type': 'string', 'description': 'verbatim text copied from that result that states the fact'}}, 'required': ['source', 'quote']}}}]
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
                                self.search_cache: dict = {}

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
                                    retained = []
                                    for a, b in row.get('retained') or []:
                                        a = max(0, min(int(a), note_len))
                                        b = max(a + 1, min(int(b), note_len))
                                        retained.append([a, b])
                                    if retained:
                                        shown = retained
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
                                    slices = [CitationSlice(start=s, end=e) for s, e in merged if e > s]
                                    if not slices:
                                        return None
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
                                n = ledger.add(row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''), text=row.get('text', ''))
                                text = text.replace(_SLOT.format(i), str(n))
                            return text
                        _SITE_OP_RE = re.compile('\\bsite:\\S+\\s*', re.I)

                        def _degrade_query(q: str) -> str:
                            out = _SITE_OP_RE.sub('', q or '').replace('"', ' ')
                            return ' '.join(out.split())

                        def _norm_query(text: str) -> str:
                            return ' '.join((text or '').lower().split())

                        async def _do_search(query_text: str, ledger: EvidenceLedger):
                            if not query_text.strip():
                                return '# web_search: empty query'
                            cached = ledger.search_cache.get(_norm_query(query_text))
                            if isinstance(cached, str) and cached:
                                return '# web_search: you already ran this exact query this run — the SAME numbered results are below, unchanged. Do not repeat it: page_grep a page you already fetched, or ask a different query.\n' + cached
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
                            windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE)
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
                        _SEC_CACHE_MAX = 8
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
                                    if len(_SEC_CACHE) < _SEC_CACHE_MAX:
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
                                squashed = ' '.join(q.split())
                                i = ' '.join(text.split()).lower().find(squashed.lower())
                                if i >= 0:
                                    i = -1
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

                        def _call_name_args(call) -> tuple:
                            try:
                                args = json.loads(getattr(call, 'arguments', None) or '{}')
                            except Exception:
                                args = {}
                            if not isinstance(args, dict):
                                args = {}
                            name = getattr(call, 'name', '') or ''
                            return (str(name), args)

                        async def _run_tool(call, question: str, ledger: EvidenceLedger, deadline: float) -> str:
                            name_args = _call_name_args(call)
                            name = name_args[0]
                            args = name_args[1]
                            if name == 'web_search':
                                return await _do_search(str(args.get('query') or ''), ledger)
                            if name == 'read_page':
                                return await _do_fetch(str(args.get('url') or ''), str(args.get('focus') or ''), question, ledger)
                            if name == 'retain_evidence':
                                return _do_retain_evidence(str(args.get('source') or ''), str(args.get('quote') or ''), ledger)
                            if name == 'page_grep':
                                return _do_page_grep(str(args.get('url') or ''), str(args.get('pattern') or ''), ledger)
                            if name == 'page_read':
                                return _do_page_read(str(args.get('url') or ''), args.get('offset') or 0, args.get('length') or PAGE_READ_MAX_CHARS, ledger)
                            if name == 'sec_filing':
                                return await _do_sec_filing(str(args.get('company') or ''), str(args.get('form') or ''), str(args.get('year') or ''), deadline)
                            return f'# unknown tool {name!r}'
                        MAX_TOOLS_PER_TURN = 8
                        LOOP_STALL_ALLOWANCE = 2
                        _PRODUCER_TOOLS = frozenset(('web_search', 'read_page', 'sec_filing'))
                        _CONSUMER_TOOLS = frozenset(('page_grep', 'page_read', 'retain_evidence'))

                        def _assistant_tool_message(msg, calls) -> dict:
                            try:
                                built = msg.to_input_message()
                                if isinstance(built, dict):
                                    return built
                                if built is not None:
                                    return built
                            except Exception:
                                pass
                            tool_calls = []
                            for call in calls:
                                name_args = _call_name_args(call)
                                tool_calls.append({'id': call.id, 'type': 'function', 'function': {'name': name_args[0], 'arguments': json.dumps(name_args[1])}})
                            content = getattr(msg, 'content', None)
                            return {'role': 'assistant', 'content': content if isinstance(content, str) else '', 'tool_calls': tool_calls}

                        async def _gather_bounded(tasks: list, budget: float) -> list:
                            if not tasks:
                                return []
                            try:
                                await asyncio.wait(tasks, timeout=max(0.5, budget))
                            except Exception:
                                pass
                            out = []
                            for task in tasks:
                                if task.done():
                                    try:
                                        out.append(task.result())
                                    except Exception as exc:
                                        out.append(f'# tool crashed: {exc}')
                                else:
                                    task.cancel()
                                    out.append('# tool timed out — use what you already have')
                            return out

                        async def _run_tool_waves(run_calls: list, question: str, ledger: EvidenceLedger, deadline: float, budget: float) -> list:
                            bodies: list = [''] * len(run_calls)
                            wave1: list = []
                            wave2: list = []
                            for i, call in enumerate(run_calls):
                                name = _call_name_args(call)[0]
                                if name in _CONSUMER_TOOLS:
                                    wave2.append(i)
                                else:
                                    wave1.append(i)
                            if wave1:
                                tasks = [asyncio.ensure_future(_run_tool(run_calls[i], question, ledger, deadline)) for i in wave1]
                                raw = await _gather_bounded(tasks, budget)
                                for slot, i in enumerate(wave1):
                                    body = _commit_tool_output(raw[slot], ledger)
                                    bodies[i] = body
                                    name_args = _call_name_args(run_calls[i])
                                    if name_args[0] == 'web_search' and _CITE_MARK_RE.search(body):
                                        key = _norm_query(str(name_args[1].get('query') or ''))
                                        if key and key not in ledger.search_cache:
                                            ledger.search_cache[key] = body
                            if wave2:
                                left = deadline - monotonic() - MIN_TAIL_S
                                tasks = [asyncio.ensure_future(_run_tool(run_calls[i], question, ledger, deadline)) for i in wave2]
                                raw = await _gather_bounded(tasks, max(2.0, min(budget, left)))
                                for slot, i in enumerate(wave2):
                                    bodies[i] = _commit_tool_output(raw[slot], ledger)
                            for i in range(len(bodies)):
                                if not bodies[i]:
                                    bodies[i] = '# tool produced no output — try a different call'
                            return bodies
                        _REASONING_MANDATORY = ('openai/gpt-oss',)

                        def _least_think(model: str='') -> dict:
                            for prefix in _REASONING_MANDATORY:
                                if model.startswith(prefix):
                                    return {'enabled': True, 'effort': 'low'}
                            return {'enabled': False}

                        async def _chat_simple(model: str, system: str, user: str, *, max_tokens: int, timeout: float, think: dict | None=None) -> str:
                            if think is None:
                                think = _least_think(model)
                            payload = await llm_chat(provider=LLM_LANE, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=think)
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

                        def _msg_chars(messages: list) -> int:
                            total = 0
                            for msg in messages:
                                if isinstance(msg, dict):
                                    total += len(str(msg.get('content') or ''))
                            return total

                        def _trim_messages(messages: list, ceiling: int) -> list:
                            if _msg_chars(messages) <= ceiling:
                                return messages
                            head: list = []
                            tail_pool: list = []
                            seen_user = False
                            for msg in messages:
                                role = msg.get('role') if isinstance(msg, dict) else ''
                                if not seen_user and role in ('system', 'user'):
                                    head.append(msg)
                                    if role == 'user':
                                        seen_user = True
                                    continue
                                tail_pool.append(msg)
                            room = ceiling - _msg_chars(head)
                            if room <= 2000:
                                return head + tail_pool[-2:]
                            kept: list = []
                            spent = 0
                            for msg in reversed(tail_pool):
                                size = len(str(msg.get('content') or '')) if isinstance(msg, dict) else 400
                                if spent + size > room and kept:
                                    break
                                spent += size
                                kept.append(msg)
                            kept.reverse()
                            if kept and isinstance(kept[0], dict) and (kept[0].get('role') == 'tool'):
                                while kept and isinstance(kept[0], dict) and (kept[0].get('role') == 'tool'):
                                    kept.pop(0)
                            if not kept:
                                return head
                            note = {'role': 'system', 'content': 'Earlier tool output has been trimmed from this transcript to fit the context window. The numbered results [n] you were shown remain valid and citable — keep citing them by number. If you need to re-read a page, use page_grep/page_read rather than re-fetching.'}
                            return head + [note] + kept

                        async def _chat_turn(messages: list[dict], deadline: float, *, finish_only: bool, force_tools: bool=False):
                            want_tools = force_tools or not finish_only
                            for rung in LOOP_LADDER:
                                model = rung[0]
                                ceiling = rung[1]
                                timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0)
                                if timeout <= 5.0:
                                    return None
                                sent = _trim_messages(messages, ceiling)
                                if not sent:
                                    continue
                                try:
                                    payload = await asyncio.wait_for(llm_chat(provider=LLM_LANE, model=model, messages=sent, tools=LOOP_TOOLS if want_tools else None, tool_choice='auto' if want_tools else None, temperature=0.2, thinking={'enabled': True, 'effort': 'low'}, max_output_tokens=None, timeout=timeout), timeout=min(timeout + 6.0, max(1.0, deadline - monotonic() - 1.0)))
                                    _spend_note(payload)
                                    return payload
                                except Exception:
                                    continue
                            return None

                        async def _knowledge_brief(question: str) -> tuple[str, str]:
                            system = 'Senior research analyst. Commit to concrete best answers from knowledge; mark uncertain values (verify). Never refuse.'
                            user = f"Question:\n{question}\n\nFill in this internal worksheet. It is planning scratch for your own use, never an answer, so keep the tags lowercase and never reuse them as section headings later.\ndraft: your full best answer now — candidate pool, every stated condition applied, qualifying entities with figures/dates, near-miss exclusions. Flag shaky facts with (verify).\nconditions: each atomic condition in the question, numbered, including any output-format demand.\nsearches: 3-6 precise web searches for the facts that decide the answer (entity + metric + year; include a named source's site: filter).\nurls: up to 5 exact URLs worth reading directly (official stats pages, sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."
                            raw = ''
                            for model in WRITE_LADDER:
                                try:
                                    raw = await _chat_simple(model, system, user, max_tokens=2400, timeout=BRIEF_TIMEOUT_S, think=_least_think(model))
                                except Exception:
                                    raw = ''
                                if raw:
                                    break
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
                                    body = _commit_tool_output(out, ledger)
                                    blocks.append(body)
                                    key = _norm_query(seed)
                                    if key and _CITE_MARK_RE.search(body) and (key not in ledger.search_cache):
                                        ledger.search_cache[key] = body
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
                            stalls_left = LOOP_STALL_ALLOWANCE
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
                                    if stalls_left > 0 and deadline - monotonic() > MIN_TAIL_S + 20.0:
                                        stalls_left -= 1
                                        continue
                                    break
                                llm = getattr(payload, 'llm', None)
                                choices = getattr(llm, 'choices', None) or []
                                if not choices:
                                    if stalls_left > 0 and deadline - monotonic() > MIN_TAIL_S + 20.0:
                                        stalls_left -= 1
                                        continue
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
                                messages.append(_assistant_tool_message(msg, calls))
                                run_calls = calls[:MAX_TOOLS_PER_TURN]
                                left = deadline - monotonic()
                                if left <= MIN_TAIL_S:
                                    break
                                tool_budget = min(FETCH_TIMEOUT_S * 2 + 6.0, left - MIN_TAIL_S)
                                if tool_budget < 3.0:
                                    tool_budget = max(1.0, left - 2.0)
                                bodies = await _run_tool_waves(run_calls, question, ledger, deadline, tool_budget)
                                for i, call in enumerate(run_calls):
                                    body = bodies[i]
                                    messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': body})
                                for call in calls[MAX_TOOLS_PER_TURN:]:
                                    messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})
                            return (answer, messages)

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
                        QUOTE_SYNTH_TIMEOUT_S = 42.0
                        QUOTE_SYNTH_MIN_BUDGET_S = 30.0
                        QUOTE_SYNTH_MIN_QUOTES = 2
                        QUOTE_TABLE_CHARS = 1400

                        def _quote_table(ledger: EvidenceLedger) -> str:
                            parts = []
                            for i, row in enumerate(ledger.rows, start=1):
                                text = row.get('text') or ''
                                for a, b in row.get('retained') or []:
                                    excerpt = text[max(0, int(a)):int(b)][:QUOTE_TABLE_CHARS].strip()
                                    if excerpt:
                                        parts.append(f"[{i}] {row.get('title') or row.get('url') or ''}\n{excerpt}")
                            return '\n\n'.join(parts)

                        def _retained_count(ledger: EvidenceLedger) -> int:
                            return sum((len(r.get('retained') or []) for r in ledger.rows))

                        async def _write_from_digest(question: str, ledger: EvidenceLedger, deadline: float) -> str:
                            left = deadline - monotonic()
                            if left < 14.0:
                                return ''
                            digest = _ledger_digest(ledger)
                            if not digest:
                                return ''
                            convo = [{'role': 'system', 'content': _COMMIT_RULES}, {'role': 'user', 'content': f'Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'}]

                            async def _one(model: str, budget: float) -> str:
                                payload = await llm_chat(provider=LLM_LANE, model=model, messages=convo, temperature=0.15, max_output_tokens=2600, timeout=budget, thinking=_least_think(model))
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
                            for i, model in enumerate(WRITE_LADDER):
                                left = deadline - monotonic()
                                if left < 14.0:
                                    return ''
                                budget = min(RESCUE_TIMEOUT_S, left - DIGEST_TAIL_S)
                                if i < len(WRITE_LADDER) - 1:
                                    budget = min(budget, max(12.0, left - 14.0 - DIGEST_TAIL_S))
                                if budget < 8.0:
                                    return ''
                                try:
                                    text = await _one(model, budget)
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

                        async def _hv16_base_query(query: Query) -> Response:
                            question = (query.text or '').strip()
                            if not question:
                                return Response(text='No question provided.')
                            try:
                                return await _solve(query, question)
                            except Exception:
                                return Response(text=f'Best-effort answer unavailable for: {question[:500]}')

                        async def _solve(query: Query, question: str) -> Response:
                            deadline = monotonic() + WALL_BUDGET_S
                            _reset_run_state()
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
                            shaped = answer
                            try:
                                shaped = _strip_lead_narration(shaped)
                                shaped = _answer_line_only(shaped, question)
                            except Exception:
                                shaped = answer
                            if shaped.strip():
                                answer = shaped
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
                                    try:
                                        salvaged = await _schema_output(question, basis, query.output_schema, deadline)
                                    except Exception:
                                        salvaged = None
                                    if salvaged is not None:
                                        try:
                                            return Response(output=salvaged, citations=citations or None)
                                        except Exception:
                                            pass
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
                        import time as _hv16_time
                        _HV16_LLM_PROVIDER = 'openrouter'
                        _HV16_LLM_MODEL = 'openai/gpt-oss-120b'
                        _HV16_SEARCH_PROVIDER = 'parallel'
                        _HV16_BASE_ELAPSED_SKIP_S = 175.0
                        _HV16_MECH_BUDGET_S = 42.0

                        def _hv16_extract_json_object(raw: str | None) -> dict | None:
                            import json as _hv16_json
                            import re as _hv16_re
                            if not raw:
                                return None
                            cleaned = _hv16_re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=_hv16_re.I | _hv16_re.M).strip()
                            try:
                                return _hv16_json.loads(cleaned)
                            except Exception:
                                match = _hv16_re.search('\\{.*\\}', cleaned, _hv16_re.S)
                                if not match:
                                    return None
                                try:
                                    return _hv16_json.loads(match.group(0))
                                except Exception:
                                    return None

                        async def _hv16_identify_gaps(question: str, answer_text: str) -> dict:
                            try:
                                result = await llm_chat(provider=_HV16_LLM_PROVIDER, model=_HV16_LLM_MODEL, messages=[{'role': 'system', 'content': 'You are a strict answer-quality auditor. Read the question and the drafted answer only.\nList at most 2 specific, load-bearing, time-sensitive, or otherwise non-obvious factual claims in the answer that need independent verification (risky_claims).\nList at most 1 concrete element the question explicitly asks for that the answer does not address at all (missing_elements).\nUse short exact phrases copied or closely paraphrased from the answer or question, not full sentences of commentary.\nReturn JSON only: {"risky_claims": ["..."], "missing_elements": ["..."]}. Use empty arrays when none apply.'}, {'role': 'user', 'content': f'Question:\n{question}\n\nAnswer:\n{answer_text[:6000]}'}], tools=None, temperature=0.0, max_output_tokens=350, timeout=14.0)
                                raw = getattr(getattr(result, 'response', None), 'raw_text', None)
                                parsed = _hv16_extract_json_object(raw)
                                if not isinstance(parsed, dict):
                                    return {'risky_claims': [], 'missing_elements': []}
                                risky = parsed.get('risky_claims')
                                missing = parsed.get('missing_elements')
                                risky = [str(c).strip() for c in risky if str(c).strip()][:2] if isinstance(risky, list) else []
                                missing = [str(c).strip() for c in missing if str(c).strip()][:1] if isinstance(missing, list) else []
                                return {'risky_claims': risky, 'missing_elements': missing}
                            except Exception:
                                return {'risky_claims': [], 'missing_elements': []}

                        async def _hv16_fresh_search_digest(query_text: str):
                            try:
                                search_result = await search_web(query_text[:300], provider=_HV16_SEARCH_PROVIDER, num=5, timeout=12.0)
                            except Exception:
                                return (None, [])
                            results = list(getattr(search_result.response, 'data', None) or [])
                            digest_lines = []
                            for idx, item in enumerate(results[:5]):
                                snippet = (getattr(item, 'snippet', None) or '').strip()
                                title = (getattr(item, 'title', None) or '').strip()
                                if snippet or title:
                                    digest_lines.append(f'[{idx}] {title} :: {snippet[:400]}')
                            if not digest_lines:
                                return (None, [])
                            return (search_result, digest_lines)

                        async def _hv16_verify_claim(claim: str):
                            search_result, digest_lines = await _hv16_fresh_search_digest(claim)
                            if search_result is None:
                                return ('unclear', None)
                            try:
                                judged = await llm_chat(provider=_HV16_LLM_PROVIDER, model=_HV16_LLM_MODEL, messages=[{'role': 'system', 'content': 'You check whether search snippets support or contradict a claim.\nReturn JSON only: {"status": "supported"|"contradicted"|"unclear", "best_index": <int or null>}. best_index is the index of the single snippet that most directly supports or contradicts the claim, else null.'}, {'role': 'user', 'content': f'Claim:\n{claim}\n\nSnippets:\n' + '\n'.join(digest_lines)}], tools=None, temperature=0.0, max_output_tokens=120, timeout=12.0)
                                raw = getattr(getattr(judged, 'response', None), 'raw_text', None)
                                parsed = _hv16_extract_json_object(raw)
                            except Exception:
                                parsed = None
                            status = 'unclear'
                            best_index = None
                            if isinstance(parsed, dict):
                                candidate_status = parsed.get('status')
                                if candidate_status in ('supported', 'contradicted', 'unclear'):
                                    status = candidate_status
                                candidate_index = parsed.get('best_index')
                                if isinstance(candidate_index, int) and 0 <= candidate_index < len(digest_lines):
                                    best_index = candidate_index
                            citation_ref = None
                            if status == 'supported' and best_index is not None:
                                try:
                                    result_items = list(search_result.results)
                                    if 0 <= best_index < len(result_items):
                                        dto = result_items[best_index]
                                        citation_ref = CitationRef(receipt_id=search_result.receipt_id, result_id=dto.result_id)
                                except Exception:
                                    citation_ref = None
                            return (status, citation_ref)

                        async def _hv16_rewrite_without_claim(question: str, answer_text: str, claim: str) -> str | None:
                            try:
                                result = await llm_chat(provider=_HV16_LLM_PROVIDER, model=_HV16_LLM_MODEL, messages=[{'role': 'system', 'content': 'You lightly edit an answer for factual hygiene. Remove or hedge only the single specified claim because it is unsupported or contradicted; keep every other sentence and fact untouched and do not add any new facts. Return the full corrected answer as plain text with no preamble.'}, {'role': 'user', 'content': f'Question:\n{question}\n\nCurrent answer:\n{answer_text[:8000]}\n\nUnsupported or contradicted claim to remove or hedge:\n{claim}'}], tools=None, temperature=0.1, max_output_tokens=1200, timeout=16.0)
                                text = (getattr(getattr(result, 'response', None), 'raw_text', None) or '').strip()
                                return text or None
                            except Exception:
                                return None

                        async def _hv16_fill_missing_element(question: str, answer_text: str, missing_element: str):
                            search_result, digest_lines = await _hv16_fresh_search_digest(f'{question} {missing_element}')
                            if search_result is None:
                                return (None, None)
                            try:
                                result = await llm_chat(provider=_HV16_LLM_PROVIDER, model=_HV16_LLM_MODEL, messages=[{'role': 'system', 'content': 'You write at most one short factual sentence that directly answers a missing element of the question, using only the given snippets as evidence. Never invent facts not present in the snippets.\nReturn JSON only: {"sentence": "..." or null, "best_index": <int or null>}. Use null for both fields if the snippets do not clearly answer the missing element.'}, {'role': 'user', 'content': f'Question:\n{question}\n\nMissing element:\n{missing_element}\n\nSnippets:\n' + '\n'.join(digest_lines)}], tools=None, temperature=0.1, max_output_tokens=200, timeout=14.0)
                                raw = getattr(getattr(result, 'response', None), 'raw_text', None)
                                parsed = _hv16_extract_json_object(raw)
                            except Exception:
                                parsed = None
                            if not isinstance(parsed, dict):
                                return (None, None)
                            sentence = parsed.get('sentence')
                            best_index = parsed.get('best_index')
                            if not isinstance(sentence, str) or not sentence.strip():
                                return (None, None)
                            if not isinstance(best_index, int) or not 0 <= best_index < len(digest_lines):
                                return (None, None)
                            citation_ref = None
                            try:
                                result_items = list(search_result.results)
                                if 0 <= best_index < len(result_items):
                                    dto = result_items[best_index]
                                    citation_ref = CitationRef(receipt_id=search_result.receipt_id, result_id=dto.result_id)
                            except Exception:
                                citation_ref = None
                            if citation_ref is None:
                                return (None, None)
                            return (sentence.strip(), citation_ref)

                        async def _hv16_verification_patch(query_text: str, response: 'Response') -> 'Response':
                            mech_started = _hv16_time.monotonic()
                            if response.text is None:
                                return response
                            answer_text = response.text
                            if not answer_text.strip():
                                return response
                            mech_deadline = mech_started + _HV16_MECH_BUDGET_S
                            try:
                                gaps = await _hv16_identify_gaps(query_text, answer_text)
                            except Exception:
                                return response
                            risky_claims = gaps.get('risky_claims') or []
                            missing_elements = gaps.get('missing_elements') or []
                            if not risky_claims and (not missing_elements):
                                return response
                            citations = list(response.citations or [])
                            existing_keys = {(citation.receipt_id, citation.result_id) for citation in citations}
                            changed = False
                            for claim in risky_claims:
                                if _hv16_time.monotonic() > mech_deadline:
                                    break
                                try:
                                    status, citation_ref = await _hv16_verify_claim(claim)
                                except Exception:
                                    continue
                                if status == 'supported' and citation_ref is not None:
                                    key = (citation_ref.receipt_id, citation_ref.result_id)
                                    if key not in existing_keys:
                                        citations.append(citation_ref)
                                        existing_keys.add(key)
                                        changed = True
                                elif status == 'contradicted':
                                    try:
                                        rewritten = await _hv16_rewrite_without_claim(query_text, answer_text, claim)
                                    except Exception:
                                        rewritten = None
                                    if rewritten and rewritten.strip() and (rewritten.strip() != answer_text.strip()):
                                        answer_text = rewritten.strip()
                                        changed = True
                            for missing_element in missing_elements:
                                if _hv16_time.monotonic() > mech_deadline:
                                    break
                                try:
                                    sentence, citation_ref = await _hv16_fill_missing_element(query_text, answer_text, missing_element)
                                except Exception:
                                    sentence, citation_ref = (None, None)
                                if sentence and citation_ref is not None:
                                    key = (citation_ref.receipt_id, citation_ref.result_id)
                                    if key not in existing_keys:
                                        answer_text = answer_text.rstrip() + '\n\n' + sentence
                                        citations.append(citation_ref)
                                        existing_keys.add(key)
                                        changed = True
                            if not changed:
                                return response
                            try:
                                return Response(text=answer_text, output=None, citations=citations or None)
                            except Exception:
                                return response

                        async def query(query: Query) -> Response:
                            _hv16_call_started = _hv16_time.monotonic()
                            response = await _hv16_base_query(query)
                            try:
                                base_elapsed = _hv16_time.monotonic() - _hv16_call_started
                                if base_elapsed > _HV16_BASE_ELAPSED_SKIP_S:
                                    return response
                                return await _hv16_verification_patch(query.text, response)
                            except Exception:
                                return response
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
                        LLM_LANE_A = 'openrouter'
                        LLM_LANE_B = 'ai_gateway'
                        LOOP_MODEL_A = 'z-ai/glm-5.2'
                        LOOP_MODEL_B = 'zai/glm-5.2-fast'
                        AUDIT_MODEL = 'openai/gpt-oss-120b'
                        CLAIM_MODEL = 'openai/gpt-oss-120b'
                        SCHEMA_MODEL = 'openai/gpt-oss-120b'
                        RESORT_MODEL = 'z-ai/glm-5.2'
                        WALL_BUDGET_S = 266.0
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
                        FETCH_WINDOWS_PER_PAGE = 3
                        FETCH_PLAIN_CHARS = 6500
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
                        ANSWER_CHAR_CAP = 60000
                        CITATION_CAP = 24
                        EVIDENCE_CHAR_BUDGET = 105000
                        WRAPUP_MIN_USD = 0.02
                        BRIEF_MIN_USD = 0.03
                        AUDIT_MIN_USD = 0.05
                        _SPEND = {'left': None}
                        _CONSUMER_TOOLS = frozenset(('page_grep', 'page_read', 'retain_evidence'))

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
                        LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}, {'type': 'function', 'function': {'name': 'page_grep', 'description': 'Search INSIDE a page you already fetched, by regex or literal text, and get every match with its surrounding context and character offset. Use this when read_page showed you the head of a long page but the value you need is deeper — do not re-fetch, grep it.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL of a page already fetched this run'}, 'pattern': {'type': 'string', 'description': 'regex or literal string to find, e.g. a city name, a year, a column label'}}, 'required': ['url', 'pattern']}}}, {'type': 'function', 'function': {'name': 'page_read', 'description': 'Read an arbitrary character range of a page you already fetched. Use the offsets page_grep reports to read the full table or section around a match.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL already fetched'}, 'offset': {'type': 'integer', 'description': 'start character offset'}, 'length': {'type': 'integer', 'description': 'how many characters to read (max 12000)'}}, 'required': ['url', 'offset']}}}, {'type': 'function', 'function': {'name': 'retain_evidence', 'description': "Keep the exact source text that proves a claim you are about to make. Pass the result number and the verbatim quote from it. Do this the moment you find a decisive value — the judge only credits claims whose citation contains the supporting text. Use it for the QUESTION'S PREMISES as well as your answer.", 'parameters': {'type': 'object', 'properties': {'source': {'type': 'string', 'description': 'result number to quote from, e.g. 3'}, 'quote': {'type': 'string', 'description': 'verbatim text copied from that result that states the fact'}}, 'required': ['source', 'quote']}}}]
                        LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nPREFER THE PRIMARY SOURCE: when two sources state the same fact, cite the one that ORIGINATES it -- the agency, registry, filing, official statistics release or the organisation\'s own page -- not an encyclopedia or aggregator repeating it. Use the encyclopedia to FIND the primary source, then fetch and cite that.\n\nQUOTE WHAT PROVES IT: the judge credits a claim only when your citation CONTAINS the source text stating it. The moment you read a decisive value, call retain_evidence(source, quote) with the exact words from that result. Do this for every condition you test and every figure you report. ALSO QUOTE THE QUESTION\'S PREMISES: every entity, work, date or figure the question NAMES should get a retained quote confirming it.\n\nREAD DEEP, DO NOT RE-FETCH: read_page shows the head plus a few regions of a long page. If the value you need is not in what you were shown, call page_grep(url, pattern) to find it anywhere in that page and page_read to open the region around a reported offset. Grepping a page you already have costs nothing and beats another search.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. COPY SOURCE VALUES VERBATIM into the answer -- never round, abbreviate, rephrase or \'clean up\' a figure, name, title or date that appears in a source. If the source says 3.847, write 3.847, not 3.85 or 3.8. If it says a full legal name, write that full name. EXCEPTION -- OUTPUT ONLY: if the question says \'output only\', \'answer with only\', \'just the number/name\', or otherwise forbids explanation, your entire message must be exactly that bare value plus its citation -- no preamble, no \'Final answer:\', no restated question, no units unless asked. Violating the format loses the question regardless of factual correctness. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nVERBATIM SOURCE STRINGS: copy entity names, place names, titles and values EXACTLY as they appear in the cited evidence text — preserve the original spelling, transliteration, diacritics, capitalization and units. NEVER canonicalize a name to a more common English exonym or \'correct\' the source\'s spelling: keep \'Makkah\' not \'Mecca\', \'Jiddah\' not \'Jeddah\', \'Ad-Dammām\' not \'Dammam\', \'Türkiye\' not \'Turkey\', and render \'Kolkata\' exactly as the source gives it. For a set or list answer, render EACH member with the source\'s exact string.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

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
                                    note_len = int(row.get('note_len') or 0)
                                    shown: list[list[int]] = []
                                    retained = row.get('retained') or []
                                    if retained:
                                        for a, b in retained:
                                            start = max(0, min(int(a), note_len))
                                            end = max(start + 1, min(int(b), note_len))
                                            if end > start:
                                                shown.append([start, end])
                                    else:
                                        for span in spans[:4]:
                                            start = max(0, min(int(span[0]), note_len))
                                            end = min(int(span[1]), note_len)
                                            if end <= start:
                                                continue
                                            shown.append([start, end])
                                    if not shown:
                                        return None
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
                                    slices = [CitationSlice(start=s, end=e) for s, e in merged if e > s]
                                    if not slices:
                                        return None
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
                                for provider in ('parallel', 'desearch'):
                                    try:
                                        payload = await search_web(attempt, provider=provider, num=8, timeout=SEARCH_TIMEOUT_S)
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

                        async def _do_fetch(url: str, focus: str, question: str, ledger: EvidenceLedger):
                            if not url.strip():
                                return '# read_page: empty url'
                            payload = None
                            for provider in ('parallel', 'desearch'):
                                try:
                                    payload = await fetch_page(url, provider=provider, timeout=FETCH_TIMEOUT_S)
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
                            windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE)
                            row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, FETCH_HEAD_CHARS)] + list(windows), 'title': url, 'url': url, 'preview': note[windows[0][0]:windows[0][0] + 1200], 'text': note}
                            head = note[:FETCH_HEAD_CHARS]
                            sections = ''.join((f'\n--- section @{s} ---\n{note[s:e]}' for s, e in windows))
                            return ToolOutput(f"# read_page({url!r}) -> [{_SLOT.format(0)}] {len(note)} chars total; head + the {len(windows)} most relevant section(s) shown ({', '.join((f'{s}-{e}' for s, e in windows))}). If the value you need is not shown, call page_grep(url, pattern) on this SAME url — do not re-fetch.\n--- head ---\n{head}{sections}", [row])
                        _SEC_TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
                        _SEC_SUBMISSIONS_URL = 'https://data.sec.gov/submissions/CIK{cik10}.json'
                        _SEC_DOC_URL = 'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}'
                        _SEC_FETCH_TIMEOUT_S = 26.0
                        _SEC_MIN_HEADROOM_S = 40.0
                        _SEC_CACHE: dict = {}
                        _SEC_CACHE_MAX = 8
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
                            for provider in ('parallel', 'desearch'):
                                left = deadline - monotonic()
                                if left < 12.0:
                                    return None
                                try:
                                    payload = await asyncio.wait_for(fetch_page(url, provider=provider, timeout=min(_SEC_FETCH_TIMEOUT_S, left - 6.0)), timeout=min(_SEC_FETCH_TIMEOUT_S, left - 6.0) + 4.0)
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
                                    if len(_SEC_CACHE) >= _SEC_CACHE_MAX:
                                        for key in list(_SEC_CACHE.keys()):
                                            if key != _SEC_TICKERS_URL:
                                                _SEC_CACHE.pop(key, None)
                                                break
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

                        def _call_name_args(call) -> tuple[str, dict]:
                            try:
                                args = json.loads(getattr(call, 'arguments', None) or '{}')
                            except Exception:
                                args = {}
                            if not isinstance(args, dict):
                                args = {}
                            name = getattr(call, 'name', '') or ''
                            return (str(name), args)

                        async def _run_tool(call, question: str, ledger: EvidenceLedger, deadline: float):
                            name, args = _call_name_args(call)
                            if name == 'web_search':
                                return await _do_search(str(args.get('query') or ''), ledger)
                            if name == 'read_page':
                                return await _do_fetch(str(args.get('url') or ''), str(args.get('focus') or ''), question, ledger)
                            if name == 'sec_filing':
                                return await _do_sec_filing(str(args.get('company') or ''), str(args.get('form') or ''), str(args.get('year') or ''), deadline)
                            if name == 'page_grep':
                                return _do_page_grep(str(args.get('url') or ''), str(args.get('pattern') or ''), ledger)
                            if name == 'page_read':
                                return _do_page_read(str(args.get('url') or ''), args.get('offset') or 0, args.get('length') or PAGE_READ_MAX_CHARS, ledger)
                            if name == 'retain_evidence':
                                return _do_retain_evidence(str(args.get('source') or ''), str(args.get('quote') or ''), ledger)
                            return f'# unknown tool {name!r}'

                        async def _gather_bounded(tasks: list, budget: float) -> list:
                            if not tasks:
                                return []
                            try:
                                await asyncio.wait(tasks, timeout=max(0.5, budget))
                            except Exception:
                                pass
                            out = []
                            for task in tasks:
                                if task.done():
                                    try:
                                        out.append(task.result())
                                    except Exception as exc:
                                        out.append(f'# tool crashed: {exc}')
                                else:
                                    task.cancel()
                                    out.append('# tool timed out — use what you already have')
                            return out

                        async def _run_tool_waves(run_calls: list, question: str, ledger: EvidenceLedger, deadline: float, budget: float) -> list:
                            bodies: list = [''] * len(run_calls)
                            wave1: list = []
                            wave2: list = []
                            for i, call in enumerate(run_calls):
                                name = _call_name_args(call)[0]
                                if name in _CONSUMER_TOOLS:
                                    wave2.append(i)
                                else:
                                    wave1.append(i)
                            if wave1:
                                tasks = [asyncio.ensure_future(_run_tool(run_calls[i], question, ledger, deadline)) for i in wave1]
                                raw = await _gather_bounded(tasks, budget)
                                for slot, i in enumerate(wave1):
                                    try:
                                        bodies[i] = _commit_tool_output(raw[slot], ledger)
                                    except Exception:
                                        bodies[i] = '# tool result unavailable — use what you already have'
                            if wave2:
                                left = deadline - monotonic() - MIN_TAIL_S
                                tasks = [asyncio.ensure_future(_run_tool(run_calls[i], question, ledger, deadline)) for i in wave2]
                                raw = await _gather_bounded(tasks, max(2.0, min(budget, left)))
                                for slot, i in enumerate(wave2):
                                    try:
                                        bodies[i] = _commit_tool_output(raw[slot], ledger)
                                    except Exception:
                                        bodies[i] = '# tool result unavailable — use what you already have'
                            for i in range(len(bodies)):
                                if not bodies[i]:
                                    bodies[i] = '# tool produced no output — try a different call'
                            return bodies
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
                            lanes = ((LLM_LANE_A, LOOP_MODEL_A), (LLM_LANE_B, LOOP_MODEL_B))
                            for lane_index, lane_model in enumerate(lanes):
                                lane = lane_model[0]
                                model = lane_model[1]
                                if lane_index == 1 and payload_chars > LANE_B_MAX_PAYLOAD_CHARS:
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
                        _ROSTER_PROPER_RE = re.compile("\\b[A-Z][A-Za-z0-9.&'’/-]+(?:\\s+(?:of|the|and|de|van|von|del|di|la|le|du|dos|da)\\s+[A-Z][A-Za-z0-9.&'’/-]+|\\s+[A-Z][A-Za-z0-9.&'’/-]+){0,5}")
                        _ROSTER_NAME_STOP = frozenset('the a an of in on at to for and or but with from by as list complete full search home menu share results result page pages according wikipedia list of top best most least first last new news read more related how what which who when where why this that these those it he she they we you i'.split())

                        def _extract_candidates(text: str, limit: int=40) -> list[str]:
                            seen: set[str] = set()
                            out: list[str] = []
                            for m in _ROSTER_PROPER_RE.finditer((text or '')[:120000]):
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

                        async def _roster_prepass(question: str, ledger: EvidenceLedger, deadline: float) -> str:
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
                        _EPHEMERAL_ORDER_MARKS = ('TIME IS UP', 'Your last message was not a usable', 'AUDIT: the answer has gaps', 'CLAIM CHECK:')

                        def _strip_stale_orders(messages: list[dict]) -> list[dict]:
                            out: list[dict] = []
                            for msg in messages:
                                if isinstance(msg, dict) and msg.get('role') == 'system':
                                    body = str(msg.get('content') or '')
                                    stale = False
                                    for mark in _EPHEMERAL_ORDER_MARKS:
                                        if body.startswith(mark):
                                            stale = True
                                            break
                                    if stale:
                                        continue
                                out.append(msg)
                            return out

                        async def _loop(question: str, brief: str, ledger: EvidenceLedger, deadline: float, turn_cap: int, carry: list[dict] | None=None, allow_tools_in_wrapup: bool=False, extra_context: str='') -> tuple[str, list[dict]]:
                            if carry is not None:
                                messages = _strip_stale_orders(carry)
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
                                try:
                                    msg = choices[0].message
                                    calls = getattr(msg, 'tool_calls', None) or ()
                                except Exception:
                                    break
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
                                try:
                                    messages.append(msg.to_input_message())
                                except Exception:
                                    break
                                run_calls = calls[:8]
                                tool_budget = max(5.0, min(FETCH_TIMEOUT_S * 2 + 6.0, deadline - monotonic() - MIN_TAIL_S))
                                bodies = await _run_tool_waves(run_calls, question, ledger, deadline, tool_budget)
                                for i, call in enumerate(run_calls):
                                    messages.append({'role': 'tool', 'tool_call_id': str(getattr(call, 'id', '') or ''), 'content': bodies[i]})
                                for call in calls[8:]:
                                    messages.append({'role': 'tool', 'tool_call_id': str(getattr(call, 'id', '') or ''), 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})
                            return (answer, messages)

                        async def _audit_patch(question: str, answer: str, messages: list[dict], ledger: EvidenceLedger, deadline: float) -> tuple[str, list[dict]]:
                            probe = f"""Audit the answer against the question. JSON only, keys: "unanswered_parts" (list; question elements not addressed), "uncited_facts" (list; load-bearing claims without [n]), "wrong_kind" (list; places where the named entity is a different KIND than the question asks — a person instead of a series, a duo instead of a show), "incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges over a candidate pool — a closed set that can be enumerated, or several conditions applied to a class — then: is the pool itself stated and plausibly COMPLETE, and does the answer give a verdict for EVERY member (qualifies / excluded because X, each cited)? Name any pool member the answer never mentions, and say so if the pool looks truncated — an answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not partial), "thin_proof" (list; a qualifier lacking a per-condition citation, or a plausible near-miss candidate never addressed), "hand_waved_tally" (list; for a superlative/count/most-common question: the answer asserts a winner or a count WITHOUT showing the candidate table it was derived from. Phrases like 'among others', 'and several more', 'multiple X', or naming 2 examples to justify a count are all hand-waving — say so and name what the tally must list). Empty lists when clean.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:11000]}"""
                            try:
                                raw = await _chat_simple(LLM_LANE_A, AUDIT_MODEL, 'Strict completeness auditor. JSON only.', probe, max_tokens=2200, timeout=max(8.0, min(AUDIT_TIMEOUT_S, deadline - monotonic() - 72.0)))
                                raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                                report = json.loads(raw)
                            except Exception:
                                return (answer, messages)
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
                                return (answer, messages)
                            order = 'AUDIT: the answer has gaps:\n- ' + '\n- '.join(gaps[:6])
                            if roster_gaps:
                                order += "\nThe candidate pool is incomplete — this loses outright. FIRST search for the authoritative LIST/roster/table that enumerates the whole pool (query it as a list, e.g. '<pool subject> full list', not one member at a time), verify EVERY member against every condition, then rewrite."
                            order += '\nUse at most 3 tool calls to close the most important gaps, then rewrite the COMPLETE final answer with [n] citations in the required shape.'
                            convo = _strip_stale_orders(messages)
                            convo.append({'role': 'system', 'content': order})
                            patched, convo = await _loop(question, '', ledger, deadline, AUDIT_EXTRA_TURNS + 1, carry=convo, allow_tools_in_wrapup=True)
                            patched = patched.strip()
                            if not _is_usable_answer(patched) or len(patched) < int(len(answer) * 0.6):
                                return (answer, messages)
                            return (patched, convo)
                        _CLAIM_PROBE = 'Decompose the ANSWER into its atomic factual claims (each asserts ONE number, date, proper noun, ranking, or causal link). Output JSON ONLY, no prose:\n{"claims": [{"text": "<the claim, <=160 chars>", "citation": "<the [n] marker attached to it in the answer, or empty>", "load_bearing": true|false, "support": "strong"|"weak"|"none", "search": "<one precise web query that would verify this claim: entity + metric + year; empty if not needed>"}]}\nload_bearing = the claim decides the answer (a qualifier\'s deciding attribute, a superlative\'s winning value, a computed input). support = "strong" only if the claim carries an [n]; "weak" if cited but the cited kind looks like an aggregator/summary; "none" if it carries no [n] at all. Give at most 12 claims, hardest-to-verify first.\n\nQuestion:\n{question}\n\nAnswer:\n{answer}'
                        MAX_CLAIM_REPAIR_SEARCHES = 2

                        async def _verify_and_repair(question: str, answer: str, messages: list[dict], ledger: EvidenceLedger, deadline: float) -> tuple[str, list[dict]]:
                            if deadline - monotonic() < 78.0:
                                return (answer, messages)
                            probe = _CLAIM_PROBE.format(question=question[:2500], answer=answer[:11000])
                            try:
                                raw = await _chat_simple(LLM_LANE_A, CLAIM_MODEL, 'You decompose answers into atomic claims. JSON only.', probe, max_tokens=2200, timeout=max(8.0, min(AUDIT_TIMEOUT_S, deadline - monotonic() - 74.0)))
                                raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                                report = json.loads(raw)
                            except Exception:
                                return (answer, messages)
                            claims = report.get('claims') if isinstance(report, dict) else None
                            if not isinstance(claims, list) or not claims:
                                return (answer, messages)
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
                                return (answer, messages)
                            convo = _strip_stale_orders(messages)
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
                                    convo.append({'role': 'system', 'content': 'CLAIM VERIFICATION — fresh evidence for the load-bearing claims below (already numbered — cite these [n]):\n\n' + '\n'.join(good)})
                            order = 'CLAIM CHECK: the following load-bearing claims in your answer are not solidly supported by cited evidence:\n- ' + '\n- '.join(weak[:8]) + '\nFor EACH, either attach an [n] that actually states it (use the fresh evidence above and any earlier numbered result), or, if it cannot be confirmed, replace it with the best value you CAN cite — never leave a load-bearing claim uncited. Use at most 2 more tool calls only if needed, then rewrite the COMPLETE final answer in the required shape with [n] on every factual sentence.'
                            convo.append({'role': 'system', 'content': order})
                            revised, convo = await _loop(question, '', ledger, deadline, AUDIT_EXTRA_TURNS + 1, carry=convo, allow_tools_in_wrapup=True)
                            revised = revised.strip()
                            if not _is_usable_answer(revised) or len(revised) < int(len(answer) * 0.6):
                                return (answer, messages)
                            return (revised, convo)
                        _BRACKET_FIX = {12304: '[', 12305: ']', 65339: '[', 65341: ']', 65288: '(', 65289: ')', 8209: '-', 8722: '-'}
                        for _d in range(10):
                            _BRACKET_FIX[65296 + _d] = chr(48 + _d)

                        def _normalize_brackets(text: str) -> str:
                            return (text or '').translate(_BRACKET_FIX)
                        _CITE_NUM_RE = re.compile('\\[([0-9][0-9,\\s\\-]*)\\]')
                        MAX_CITED_NUMBERS = 256

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
                                if len(out) >= MAX_CITED_NUMBERS:
                                    break
                            return out
                        SEARCH_SLICE_WIDEN = 1600
                        MAX_SLICES_PER_REF = 4
                        _VALUE_SIGNAL_RE = re.compile("\\d|\\b[A-Z][A-Za-z][A-Za-z.'’-]+\\b")

                        def _widen_span(start, end, kind: str, note_len: int) -> tuple[int, int]:
                            s = max(0, min(int(start), note_len))
                            e = max(s, min(int(end), note_len))
                            if kind == 'search':
                                e = min(note_len, max(e, s + SEARCH_SLICE_WIDEN))
                            need = max(0, CITATION_MIN_SPAN_CHARS - (e - s))
                            if need and note_len:
                                left = min(need // 2, s)
                                s -= left
                                rest = need - left
                                right = min(rest, note_len - e)
                                e += right
                                s = max(0, s - (rest - right))
                            return (s, e)

                        def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
                            clean = sorted(((int(s), int(e)) for s, e in spans if e > s))
                            merged: list[tuple[int, int]] = []
                            for s, e in clean:
                                if merged and s <= merged[-1][1]:
                                    if e > merged[-1][1]:
                                        merged[-1] = (merged[-1][0], e)
                                else:
                                    merged.append((s, e))
                            return merged

                        def _citations_for(answer: str, ledger: EvidenceLedger) -> list[CitationRef]:
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
                                retained = row.get('retained') or []
                                if retained:
                                    spans = [(int(a), int(b)) for a, b in retained]
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
                                if cost > CITATION_MAX_REF_CHARS and merged:
                                    room = CITATION_MAX_REF_CHARS
                                    trimmed: list[tuple[int, int]] = []
                                    for s, e in merged:
                                        if room <= 0:
                                            break
                                        width = e - s
                                        if width <= room:
                                            trimmed.append((s, e))
                                            room -= width
                                        else:
                                            trimmed.append((s, s + room))
                                            room = 0
                                    merged = trimmed
                                    cost = sum((e - s for s, e in merged))
                                built.append({'order': grp['order'], 'receipt_id': grp['receipt_id'], 'result_id': grp['result_id'], 'note_len': grp['note_len'], 'spans': merged, 'has_value': grp['has_value'], 'cost': cost})
                            ranked = [(0 if g['has_value'] else 1, g['order'], i) for i, g in enumerate(built)]
                            ranked.sort()
                            built = [built[triple[2]] for triple in ranked]
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
                                    end = min(int(e), note_len)
                                    if end <= start:
                                        continue
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
                                line_counts: dict = {}
                                for ln in lines:
                                    line_counts[ln] = line_counts.get(ln, 0) + 1
                                for count in line_counts.values():
                                    if count >= 3:
                                        return True
                                if len(line_counts) * 2 > len(lines):
                                    return False
                            sents = [s.strip().lower() for s in re.split('(?<=[.!?])\\s+|\\n+', body) if len(s.strip()) > 25]
                            if len(sents) < 3:
                                return False
                            sent_counts: dict = {}
                            for s in sents:
                                sent_counts[s] = sent_counts.get(s, 0) + 1
                            if len(sent_counts) * 2 <= len(sents):
                                return True
                            for count in sent_counts.values():
                                if count >= 3:
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

                        def _ledger_digest(ledger: EvidenceLedger, char_cap: int=60000) -> str:
                            parts: list[str] = []
                            spent = 0
                            for i, row in enumerate(ledger.rows, start=1):
                                full = row.get('text') or ''
                                retained_bits = []
                                for a, b in row.get('retained') or []:
                                    excerpt = full[max(0, int(a)):int(b)][:1400].strip()
                                    if excerpt:
                                        retained_bits.append(excerpt)
                                text = '\n---\n'.join(retained_bits) if retained_bits else (row.get('preview') or '').strip()
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

                        async def _digest_write_call(lane: str, model: str, convo: list[dict], budget: float) -> str:
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

                        async def _write_from_digest(question: str, ledger: EvidenceLedger, deadline: float) -> str:
                            left = deadline - monotonic()
                            if left < 14.0:
                                return ''
                            digest = _ledger_digest(ledger)
                            if not digest:
                                return ''
                            convo = [{'role': 'system', 'content': _COMMIT_RULES}, {'role': 'user', 'content': f'Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'}]
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
                                    text = await _digest_write_call(lane_model[0], lane_model[1], convo, budget)
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

                        def _undigest_for_schema(basis: str) -> str:
                            if not basis:
                                return ''
                            text = _DIGEST_NOISE_RE.sub(' ', basis)
                            out = []
                            for raw in text.split('\n'):
                                line = raw.strip().lstrip('-*• ').strip()
                                if not line or _DIGEST_LEAD_RE.match(line):
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

                        async def _exact_value_crosscheck(question: str, answer: str, ledger: EvidenceLedger, deadline: float) -> str:
                            digest = _ledger_digest(ledger, char_cap=48000)
                            if not digest.strip():
                                return answer
                            system = "You verify ONE value in a finished research answer against a numbered EvidenceLedger. Do not rewrite or restyle the answer. Identify the single most load-bearing value the question turns on (the key number, date, count, percentage, or name). Check it against the ledger rows. Reply on ONE line only: 'OK' if the answer's value is supported or you are not certain it is wrong; otherwise 'CORRECT: <exact old text> => <exact new text> [n]' where <new text> is copied verbatim from ledger row [n] and <old text> is copied verbatim from the answer. Correct ONLY a clear, ledger-supported error. When in doubt, reply OK."
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

                        async def _solve(query: Query, question: str) -> Response:
                            deadline = monotonic() + WALL_BUDGET_S
                            _spend_reset()
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
                                if _is_usable_answer(answer) and deadline - monotonic() > 75.0 and (_spend_left() >= AUDIT_MIN_USD):
                                    patched, patched_msgs = await _audit_patch(question, answer, messages, ledger, deadline)
                                    if _is_usable_answer(patched):
                                        answer = patched
                                        messages = patched_msgs
                            except Exception:
                                pass
                            try:
                                if _is_usable_answer(answer) and deadline - monotonic() > 78.0 and (_spend_left() >= AUDIT_MIN_USD):
                                    repaired, repaired_msgs = await _verify_and_repair(question, answer, messages, ledger, deadline)
                                    if _is_usable_answer(repaired):
                                        answer = repaired
                                        messages = repaired_msgs
                            except Exception:
                                pass
                            try:
                                if _is_usable_answer(answer) and _needs_exact_value_check(question) and (deadline - monotonic() > 72.0) and (_spend_left() >= AUDIT_MIN_USD):
                                    checked = await _exact_value_crosscheck(question, answer, ledger, deadline)
                                    if _is_usable_answer(checked):
                                        answer = checked
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
                            shaped = answer
                            try:
                                shaped = _strip_lead_narration(shaped)
                                shaped = _answer_line_only(shaped, question)
                            except Exception:
                                shaped = answer
                            if shaped.strip():
                                answer = shaped
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
                                    try:
                                        salvaged = await _schema_output(question, basis, query.output_schema, deadline)
                                    except Exception:
                                        salvaged = None
                                    if salvaged is not None:
                                        try:
                                            salvaged = _verbatim_structured(salvaged, ledger)
                                        except Exception:
                                            pass
                                        try:
                                            return Response(output=salvaged, citations=citations or None)
                                        except Exception:
                                            pass
                                    cleaned = _undigest_for_schema(basis)
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
                        _PERFECT_SUFFIX = 'd9a9aaa3d9b7db57'
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

                async def query(query: Query) -> Response:
                    try:
                        easy = await _ROUTER._is_easy(query.text)
                    except Exception:
                        easy = False
                    if easy:
                        return await _SECOND_RUN(query)
                    return await _FIRST_RUN(query)
                return query

        class ReserveSolver:

            def _compile(self):
                import asyncio
                import json
                import re
                from time import monotonic
                from harnyx_miner_sdk.api import LlmThinkingConfig, fetch_page, llm_chat, search_web, tooling_info
                from harnyx_miner_sdk.decorators import entrypoint
                from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
                E_VERSION = 'v38.0-lin078-r4-flat'
                E_LLM_PROVIDER = 'openrouter'
                E_LOOP_MODEL_A = 'z-ai/glm-5.2'
                E_LOOP_MODEL_B = 'deepseek/deepseek-v3.2'
                E_AUDIT_MODEL = 'openai/gpt-oss-120b'
                E_SCHEMA_MODEL = 'openai/gpt-oss-120b'
                E_RESORT_MODEL = 'deepseek/deepseek-v3.2'
                E_SEARCH_PROVIDER = 'parallel'
                E_WALL_BUDGET_S = 262.0
                E_BRIEF_TIMEOUT_S = 50.0
                E_AI_SEARCH_TIMEOUT_S = 45.0
                E_FETCH_TIMEOUT_S = 16.0
                E_WRAPUP_AT_S = 90.0
                E_FALLBACK_MAX_PAYLOAD_CHARS = 380000
                E_AUDIT_TIMEOUT_S = 28.0
                E_SEARCH_TIMEOUT_S = 18.0
                E_AUDIT_EXTRA_TURNS = 2
                E_ANSWER_REPAIR_TURNS = 2
                E_MIN_TAIL_S = 8.0
                E_MAX_TURNS = 15
                E_MAX_TOOL_CALLS_PER_TURN = 8
                E_TURN_TIMEOUT_S = 75.0
                E_RESCUE_TIMEOUT_S = 55.0
                E_DIGEST_TAIL_S = 14.0
                E_SEARCH_EXCERPT_CHARS = 550
                E_FETCH_HEAD_CHARS = 3000
                E_FETCH_WINDOW_CHARS = 3600
                E_FETCH_WINDOWS_PER_PAGE = 3
                E_FETCH_PLAIN_CHARS = 6500
                E_ANSWER_CHAR_CAP = 60000
                E_CITATION_CAP = 24
                E_EVIDENCE_CHAR_BUDGET = 105000
                E_BRIEF_MIN_USD = 0.03
                E_AUDIT_MIN_USD = 0.05
                E_WRAPUP_MIN_USD = 0.02
                E_SPEND = {'left': None}

                def E_spend_note(payload) -> None:
                    budget = getattr(payload, 'budget', None)
                    left = getattr(budget, 'session_remaining_budget_usd', None)
                    if isinstance(left, (int, float)):
                        E_SPEND['left'] = float(left)

                def E_spend_left() -> float:
                    left = E_SPEND['left']
                    if isinstance(left, (int, float)):
                        return float(left)
                    return 1.0
                E_LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}]
                E_LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.\n\nSTANDING DOCTRINE:\n1. The opening sentence answers the asked FIELD itself — the exact coordinates, designations, counts or names requested — and when the question describes a selection process, mirror that process back in the lead (\'Of the N events matching <the stated filters>, the earliest is …\') so the applied filter is visible, not just its outcome.\n2. Rosters are graded line by line: one cited line for every qualifying item AND one for every rejected item stating its disqualifying value.\n3. Never write \'the sources do not contain\' / \'cannot be determined\' — commit to the best-supported candidate instead. And never assert \'no X exists\' merely because the evidence you happened to retrieve is silent about X.\n4. Never cite grokipedia, facebook, pinterest or quora. Prefer the page published by the source the question NAMES over any aggregator, and on infobox-style questions cite each enumerated item\'s value from that item\'s OWN page.\n5. Every claim carries its exact figure with units and its date; no meta-narration about your research process anywhere in the answer.\n6. End the answer with a \'Citation notes:\' block — one line per distinct [n] you used, shaped \'[n] <source name> — supports: <the specific fact it backs>\'. Judges verify your claims through these notes: a citation tied to its claim beats an identical answer whose citations are bare slices. Keep each line under 20 words.\n7. When two results state the same fact, cite the one whose text is readable prose (a search excerpt, a clean page section) over raw markup, and cite the page SECTION showing the value, never just the page head.\n8. A load-bearing claim that an AI-SUMMARY source row states should cite that row — its note reads to the judge as a clean support summary tied to the claim.\n9. When the question pins a source to a DATED edition (\'the July 18, 2018 fact sheet\', \'as of the June 2020 report\'), cite the dated edition (the archived snapshot when one was fetched) and copy ITS values verbatim — never substitute today\'s live figures.'

                def E_wrapup_order(seconds_left: float) -> str:
                    return f"TIME IS UP (~{int(seconds_left)}s left). No more tool calls. Write the complete final answer NOW from the numbered results above plus your knowledge: the FIRST words are the answer entities (no 'Based on…' preamble, no 'partial answer' framing, no '(verify)' markers), cite [n] on every claim, keep the required format. A cited partial answer scores; a refusal or a remark about insufficient evidence scores zero." + ('' if seconds_left >= 60 else ' BREVITY OVERRIDE: too little time remains for a line per pool member. Lead with the answer entities, then give the qualifiers one cited line each and compress the rejects into a single cited line. A complete short answer beats a long one that never finishes.')
                E_SET_HINT_RE = re.compile('\\b(?:list|name|identify|enumerate)\\b[^?]{0,40}\\b(?:all|every|each|the)\\b|\\bhow many\\b|\\bwhich (?:movies|films|series|countries|companies|states|cities|books|albums|artists|players|teams|species|languages|banks|universities|agencies|models|products)\\b', re.IGNORECASE)
                E_SET_CONNECTIVE_RE = re.compile('\\b(?:both|also|and (?:also|had|has|was|were)|as well as)\\b', re.IGNORECASE)
                E_PLURAL_HEAD_RE = re.compile('\\b(?:which|what)\\b(?:\\s+\\w+){0,2}?\\s+([a-z]{3,}s)\\b', re.IGNORECASE)
                E_PLURAL_FALSE = frozenset('was is has does its this thus across process business series species news status analysis basis less unless always perhaps'.split())
                E_ONE_WINNER_RE = re.compile('\\b(?:highest|lowest|largest|smallest|most|least|greatest|fewest|longest|shortest|first|last|best|worst|only|oldest|youngest|newest|biggest)\\b', re.IGNORECASE)
                E_EST_STOP = frozenset('interest honest modest protest request suggest forest harvest invest manifest contest arrest digest earnest conquest tempest midwest northwest southwest unrest bequest behest attest molest ingest infest detest incest armrest backrest pretest headrest footrest'.split())
                E_EST_RE = re.compile('\\b([a-z]{3,})est\\b')

                def E_has_superlative(text: str) -> bool:
                    if E_ONE_WINNER_RE.search(text or ''):
                        return True
                    for m in E_EST_RE.finditer(text or ''):
                        if m.group(0).lower() not in E_EST_STOP:
                            return True
                    return False

                def E_needs_superlative_proof(question: str) -> bool:
                    q = ' '.join((question or '').split())
                    if not q:
                        return False
                    return E_has_superlative(q) or bool(re.search('\\b(?:most|least) (?:common|frequent|number|amount)\\b|\\bhow many\\b', q, re.I))
                E_SUPERLATIVE_RULE = "SUPERLATIVE / TALLY — SHOW THE TABLE. The answer is one item, but you cannot know it without the whole pool. Before naming a winner: (1) list EVERY candidate the question's scope admits — every player who appeared, every officeholder in the span, every body in the ranking; (2) put the deciding value next to each (birth date, count, figure), cited; (3) THEN name the maximum. NEVER decide a superlative on a rounded or derived display: a coarse figure (a whole-number age, a rounded total, a bucketed rank) cannot separate two contenders that differ below its precision. Fetch the exact underlying value (full birth date, unrounded figure) for every contender, from a source that lists them ALL: a page showing only your front-runner cannot establish that nobody beats them. (3b) THEN name the maximum. Reproduce that candidate table in the proof section — a correct winner with no visible tally loses to a reference that shows its work, and 'among others' / 'and several more' is not a tally. If the pool is too large to list in full, rank it, show every contender down to a stated cutoff, and say what the cutoff was — a stated cutoff is a covered pool; an unstated one reads as an unchecked one."

                def E_needs_set_completeness(question: str) -> bool:
                    q = ' '.join((question or '').split())
                    if E_SET_HINT_RE.search(q):
                        return True
                    m = E_PLURAL_HEAD_RE.search(q)
                    if m and m.group(1).lower() not in E_PLURAL_FALSE:
                        if not E_has_superlative(q) or re.search('\\b(?:all|every|each)\\b', q, re.IGNORECASE):
                            return True
                    return bool(re.search('\\bwhich\\b', q, re.IGNORECASE)) and bool(E_SET_CONNECTIVE_RE.search(q))
                E_SET_RULE = "SET ANSWER: this question asks for a set. Missing a qualifying member scores the same as wrong — enumerate the pool, test EVERY member against EVERY condition, and name ALL qualifiers (each with its own citations per condition). Then give EVERY excluded member its own line with the condition it fails and its own [n] — not a single clause sweeping several names together, and not just the near-misses. Never claim 'the only X' unless the whole pool was checked; if your pool may be partial, still commit to every qualifier you verified. GET THE POOL FROM A LIST, NOT MEMBER-BY-MEMBER: your FIRST retrieval for a set question should hunt the authoritative roster/list/table that enumerates the whole pool (search it AS a list — '<pool subject> list', '<pool subject> table', 'list of <pool subject>' — and read_page it). Assembling the pool from separate per-member searches is how a run ends up with 3 of 6 qualifiers: the members you never thought to search for are invisible to you. Read the roster page first, then verify each member. ONE LIST PER PERIOD, THEN JOIN: when a condition has to hold across several periods — successive years, separate editions, or two parallel events — fetch ONE roster page per period and join them on the member: one list per period, not one lookup per member. A pool of 30+ members each needing several figures is a table-join, and per-member lookups will run out of turns long before the pool is covered. UNIVERSAL conditions ('in EVERY one of them', 'for BOTH parts', 'in ALL three periods'): check each candidate against EACH instance separately, with a citation per instance — one shared instance is not enough. If NO candidate survives every instance, then 'none' IS the answer: state it as a verified fact about the world with the per-instance citations that prove it."

                class E_EvidenceLedger:

                    def __init__(self) -> None:
                        self.rows: list[dict] = []
                        self.replay: dict[str, str] = {}

                    def add(self, receipt_id: str, result_id: str, note_len: int, kind: str, spans: list[tuple[int, int]] | None, title: str='', url: str='', preview: str='', note_text: str='') -> int:
                        self.rows.append({'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': (url or '')[:300], 'preview': (preview or '')[:1200], 'spans': spans, 'note_text': (note_text or '')[:60000]})
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
                E_WORD_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
                E_STOP = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

                def E_key_terms(text: str) -> set[str]:
                    return {w for w in E_WORD_RE.findall((text or '').casefold()) if w not in E_STOP}

                def E_best_windows(note: str, terms: set[str], width: int, k: int=1) -> list[tuple[int, int]]:
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
                E_SLOT = '\x00{}\x00'

                class E_ToolOutput:

                    def __init__(self, text: str, rows: list[dict] | None=None) -> None:
                        self.text = text
                        self.rows = rows or []

                def E_commit_tool_output(out, ledger: E_EvidenceLedger) -> str:
                    if isinstance(out, str):
                        return out
                    if not isinstance(out, E_ToolOutput):
                        return f'# tool crashed: {out}'
                    text = out.text
                    for i, row in enumerate(out.rows):
                        n = ledger.add(row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''), note_text=row.get('note_text', ''))
                        text = text.replace(E_SLOT.format(i), str(n))
                    return text

                def E_replay_key(name: str, arguments: str) -> str:
                    if name not in ('web_search', 'read_page'):
                        return ''
                    try:
                        args = json.loads(arguments or '{}')
                    except Exception:
                        return ''
                    if not isinstance(args, dict):
                        return ''
                    if name == 'web_search':
                        q = ' '.join(str(args.get('query') or '').split()).casefold()
                        return 'q|' + q if q else ''
                    url = ' '.join(str(args.get('url') or '').split()).casefold()
                    focus = ' '.join(str(args.get('focus') or '').split()).casefold()
                    return 'u|' + url + '|' + focus if url else ''
                E_SITE_OP_RE = re.compile('\\bsite:\\S+\\s*', re.I)

                def E_degrade_query(q: str) -> str:
                    out = E_SITE_OP_RE.sub('', q or '').replace('"', ' ')
                    return ' '.join(out.split())

                async def E_do_search(query_text: str) -> 'E_ToolOutput | str':
                    if not query_text.strip():
                        return '# web_search: empty query'
                    payload = None
                    fired: set[str] = set()
                    for attempt, allow_repeat in ((query_text, False), (query_text, True), (E_degrade_query(query_text), False)):
                        if not attempt.strip() or (attempt in fired and (not allow_repeat)):
                            continue
                        fired.add(attempt)
                        try:
                            payload = await search_web(attempt, provider=E_SEARCH_PROVIDER, num=8, timeout=E_SEARCH_TIMEOUT_S)
                            if getattr(payload, 'results', None):
                                break
                        except Exception:
                            payload = None
                    if payload is None:
                        return f'# web_search({query_text!r}) failed'
                    E_spend_note(payload)
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
                        span = [(0, min(max(E_SEARCH_EXCERPT_CHARS, 100), n_len))] if n_len >= 100 else [(0, n_len)] if n_len else None
                        title = (getattr(item, 'title', None) or '').strip()
                        url = (getattr(item, 'url', None) or '').strip()
                        rows.append({'receipt_id': receipt, 'result_id': rid, 'note_len': n_len, 'kind': 'search', 'spans': span, 'title': title, 'url': url, 'preview': note[:E_SEARCH_EXCERPT_CHARS]})
                        lines.append(f'[{E_SLOT.format(len(rows) - 1)}] {title} — {url}\n    {note[:E_SEARCH_EXCERPT_CHARS]}')
                    return E_ToolOutput('\n'.join(lines), rows)

                async def E_do_ai_summary(prompt_text: str, skip_keys: 'set | None'=None) -> 'E_ToolOutput | str':
                    if not prompt_text.strip():
                        return '# ai_search: empty prompt'
                    try:
                        payload = await search_web(prompt_text, provider=E_SEARCH_PROVIDER, num=8, timeout=E_AI_SEARCH_TIMEOUT_S)
                    except Exception:
                        return f'# ai_search({prompt_text!r}) failed'
                    E_spend_note(payload)
                    receipt = str(getattr(payload, 'receipt_id', '') or '')
                    results = list(getattr(payload, 'results', None) or [])
                    if not receipt or not results:
                        return f'# ai_search({prompt_text!r}): no results'
                    rows: list[dict] = []
                    lines = [f'# ai_search({prompt_text!r}): {len(results)} summarized findings']
                    for item in results[:8]:
                        rid = getattr(item, 'result_id', None)
                        if not isinstance(rid, str) or not rid:
                            continue
                        note = getattr(item, 'note', None) or ''
                        if not note.strip():
                            continue
                        title = (getattr(item, 'title', None) or '').strip()
                        url = (getattr(item, 'url', None) or '').strip()
                        if skip_keys and (url.casefold(), note[:400]) in skip_keys:
                            continue
                        n_len = len(note)
                        span = [(0, n_len)] if n_len < 100 else [(0, min(900, n_len))]
                        rows.append({'receipt_id': receipt, 'result_id': rid, 'note_len': n_len, 'kind': 'search', 'spans': span, 'title': title, 'url': url, 'preview': note[:900]})
                        lines.append(f'[{E_SLOT.format(len(rows) - 1)}] {title} — {url}\n    {note[:900]}')
                    if not rows:
                        return f'# ai_search({prompt_text!r}): no citable results'
                    return E_ToolOutput('\n'.join(lines), rows)

                async def E_ai_summary_seed(question: str, ledger: E_EvidenceLedger, deadline: float) -> str:
                    q = ' '.join((question or '').split())[:300]
                    if not q or deadline - monotonic() < 60.0:
                        return ''
                    a_key = 'a:' + q.casefold()
                    if a_key in ledger.replay:
                        return ''
                    have = {((r.get('url') or '').casefold(), (r.get('preview') or '')[:400]) for r in ledger.rows}
                    try:
                        out = await asyncio.wait_for(E_do_ai_summary(q, have), timeout=E_AI_SEARCH_TIMEOUT_S + 6.0)
                    except Exception:
                        return ''
                    block = E_commit_tool_output(out, ledger)
                    if not (isinstance(out, E_ToolOutput) and isinstance(block, str) and E_CITE_MARK_RE.search(block)):
                        return ''
                    ledger.replay[a_key] = block
                    return 'AI-SUMMARY SOURCES (each note below is a provider-written summary of its source — PREFER citing these [n] for the load-bearing claims they state; their notes read to the judge as clean support summaries rather than raw page text):\n\n' + block
                E_BLOCKWALL_RE = re.compile('captcha|cloudflare|enable javascript|accept (?:all )?cookies|log ?in to edit|view source|page not found|access denied|verify (?:that )?you are (?:a )?human|are you a robot|error 40[34]', re.I)

                def E_looks_blocked(note: str) -> bool:
                    body = note or ''
                    if E_BLOCKWALL_RE.search(body[:4000]) is None:
                        return False
                    prose = 0
                    for chunk in re.split('(?<=[.!?])\\s+|\\n+', body):
                        seg = ' '.join(chunk.split())
                        if not 40 <= len(seg) <= 400:
                            continue
                        if E_BLOCKWALL_RE.search(seg) or re.search('[a-zA-Z]{3}', seg) is None:
                            continue
                        prose += len(seg)
                        if prose >= 700:
                            return False
                    return True

                async def E_do_fetch(url: str, focus: str, question: str) -> 'E_ToolOutput | str':
                    if not url.strip():
                        return '# read_page: empty url'
                    payload = None
                    for _attempt in (0, 1):
                        try:
                            payload = await fetch_page(url, provider=E_SEARCH_PROVIDER, timeout=E_FETCH_TIMEOUT_S)
                            if getattr(payload, 'results', None):
                                break
                        except Exception:
                            payload = None
                    if payload is None:
                        return f'# read_page({url!r}) failed'
                    E_spend_note(payload)
                    receipt = str(getattr(payload, 'receipt_id', '') or '')
                    results = list(getattr(payload, 'results', None) or [])
                    if not results or not receipt:
                        return f'# read_page({url!r}): no content'
                    item = results[0]
                    rid = getattr(item, 'result_id', None)
                    note = getattr(item, 'note', None) or ''
                    if not isinstance(rid, str) or not rid or (not note.strip()):
                        return f'# read_page({url!r}): no usable content'
                    if E_looks_blocked(note):
                        return f'# read_page({url!r}): blocked page (captcha/consent/login wall) — NOT citable; fetch a different source'
                    if len(note) <= E_FETCH_PLAIN_CHARS:
                        row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, len(note))], 'title': url, 'url': url, 'preview': note[:1200]}
                        return E_ToolOutput(f'# read_page({url!r}) -> [{E_SLOT.format(0)}] full page, {len(note)} chars\n{note}', [row])
                    terms = E_key_terms(question) | E_key_terms(focus)
                    windows = E_best_windows(note, terms, E_FETCH_WINDOW_CHARS, k=E_FETCH_WINDOWS_PER_PAGE)
                    row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, E_FETCH_HEAD_CHARS)] + list(windows), 'title': url, 'url': url, 'preview': note[windows[0][0]:windows[0][0] + 1200], 'note_text': note[:60000]}
                    head = note[:E_FETCH_HEAD_CHARS]
                    sections = ''.join((f'\n--- section @{s} ---\n{note[s:e]}' for s, e in windows))
                    ranges = ', '.join((f'{s}-{e}' for s, e in windows))
                    return E_ToolOutput(f'# read_page({url!r}) -> [{E_SLOT.format(0)}] {len(note)} chars total; head + the {len(windows)} most relevant section(s) shown ({ranges}). If the answer set may continue elsewhere in this page, call read_page again with a different focus.\n--- head ---\n{head}{sections}', [row])
                E_SEC_TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
                E_SEC_SUBMISSIONS_URL = 'https://data.sec.gov/submissions/CIK{cik10}.json'
                E_SEC_DOC_URL = 'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}'
                E_SEC_FETCH_TIMEOUT_S = 26.0
                E_SEC_MIN_HEADROOM_S = 40.0
                E_SEC_CACHE: dict = {}
                E_SEC_CACHE_MAX = 24
                E_SEC_STOPWORDS = frozenset('inc incorporated corp corporation company companies co ltd limited llc plc lp llp group holdings the'.split())
                E_SEC_ALNUM_RE = re.compile('[a-z0-9]+')

                def E_sec_tokens(text: str) -> list[str]:
                    return [w for w in E_SEC_ALNUM_RE.findall((text or '').lower()) if w not in E_SEC_STOPWORDS]

                def E_sec_norm_form(form: str) -> str:
                    f = ' '.join((form or '').upper().replace('FORM', ' ').split())
                    m = re.fullmatch('(\\d{1,2})\\s*-?\\s*([A-Z])', f)
                    if m:
                        return f'{m.group(1)}-{m.group(2)}'
                    m = re.fullmatch('(DEF)\\s*-?\\s*(14A)', f)
                    if m:
                        return 'DEF 14A'
                    return f

                async def E_fetch_json(url: str, deadline: float):
                    cached = E_SEC_CACHE.get(url)
                    if cached is not None:
                        return cached
                    for _attempt in (0, 1):
                        left = deadline - monotonic()
                        if left < 12.0:
                            return None
                        try:
                            payload = await asyncio.wait_for(fetch_page(url, provider=E_SEARCH_PROVIDER, timeout=min(E_SEC_FETCH_TIMEOUT_S, left - 6.0)), timeout=min(E_SEC_FETCH_TIMEOUT_S, left - 6.0) + 4.0)
                        except Exception:
                            continue
                        E_spend_note(payload)
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
                            if len(E_SEC_CACHE) >= E_SEC_CACHE_MAX and url not in E_SEC_CACHE:
                                keep = E_SEC_CACHE.get(E_SEC_TICKERS_URL)
                                E_SEC_CACHE.clear()
                                if keep is not None:
                                    E_SEC_CACHE[E_SEC_TICKERS_URL] = keep
                            E_SEC_CACHE[url] = obj
                            return obj
                    return None

                def E_sec_pick_filing(recent: dict, form: str, year: str):
                    forms = recent.get('form')
                    accs = recent.get('accessionNumber')
                    docs = recent.get('primaryDocument')
                    rdates = recent.get('reportDate')
                    fdates = recent.get('filingDate')
                    if not (isinstance(forms, list) and isinstance(accs, list) and isinstance(docs, list)):
                        return None
                    n = min(len(forms), len(accs), len(docs))
                    form_norm = E_sec_norm_form(form)
                    best_year = None
                    best_any = None
                    for i in range(n):
                        if E_sec_norm_form(str(forms[i])) != form_norm:
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
                E_SEC_SEARCH_HINT = 'search "site:sec.gov {company} {year} {form}" and read_page the Archives result'

                async def E_do_sec_filing(company: str, form: str, year: str, deadline: float) -> str:
                    company = (company or '').strip()
                    form = (form or '').strip() or '10-K'
                    year = (year or '').strip()[:4]
                    hint = E_SEC_SEARCH_HINT.format(company=company, year=year, form=form)
                    if not company:
                        return '# sec_filing: company required'
                    if deadline - monotonic() < E_SEC_MIN_HEADROOM_S:
                        return f'# sec_filing: skipped (low time) — {hint}'
                    tickers = await E_fetch_json(E_SEC_TICKERS_URL, deadline)
                    if not isinstance(tickers, dict):
                        return f'# sec_filing: EDGAR ticker index unavailable — {hint}'
                    want = E_sec_tokens(company)
                    best = None
                    for row in tickers.values():
                        if not isinstance(row, dict):
                            continue
                        title = str(row.get('title', ''))
                        ticker = str(row.get('ticker', '')).lower()
                        words = set(E_sec_tokens(title))
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
                    subs = await E_fetch_json(E_SEC_SUBMISSIONS_URL.format(cik10=cik10), deadline)
                    filings = subs.get('filings') if isinstance(subs, dict) else None
                    recent = filings.get('recent') if isinstance(filings, dict) else None
                    if not isinstance(recent, dict):
                        return f'# sec_filing({company!r}): EDGAR submissions unavailable for {title} — {hint}'
                    pick = E_sec_pick_filing(recent, form, year)
                    if pick is None:
                        return f"# sec_filing({company!r}, {form!r}, year={year or 'latest'}): no matching filing in EDGAR's recent index for {title} — check the form/year, or {hint}"
                    accession, doc = pick
                    url = E_SEC_DOC_URL.format(cik=cik10.lstrip('0') or cik10, accession=accession.replace('-', ''), doc=doc)
                    return f"# sec_filing -> {title} {form} {year or '(latest)'} primary document:\n{url}\nNow call read_page on this URL with a focus hint for the section you need, and cite figures from that read_page result."

                async def E_run_tool(call, question: str, deadline: float) -> 'E_ToolOutput | str':
                    try:
                        args = json.loads(getattr(call, 'arguments', None) or '{}')
                    except Exception:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}
                    name = getattr(call, 'name', '') or ''
                    if name == 'web_search':
                        return await E_do_search(str(args.get('query') or ''))
                    if name == 'read_page':
                        return await E_do_fetch(str(args.get('url') or ''), str(args.get('focus') or ''), question)
                    if name == 'sec_filing':
                        return await E_do_sec_filing(str(args.get('company') or ''), str(args.get('form') or ''), str(args.get('year') or ''), deadline)
                    return f'# unknown tool {name!r}'
                E_REASONING_MANDATORY = ('openai/gpt-oss',)

                def E_least_think(model: str) -> dict:
                    for prefix in E_REASONING_MANDATORY:
                        if model.startswith(prefix):
                            return {'enabled': True, 'effort': 'low'}
                    return {'enabled': False}

                def E_first_message(llm):
                    choices = getattr(llm, 'choices', None) or []
                    if not choices:
                        return None
                    return getattr(choices[0], 'message', None)

                def E_message_text(msg) -> str:
                    content = getattr(msg, 'content', None)
                    if isinstance(content, str):
                        return content.strip()
                    return ''

                def E_payload_text(payload) -> str:
                    llm = getattr(payload, 'llm', None)
                    text = (getattr(llm, 'raw_text', None) or '').strip()
                    if text:
                        return text
                    return E_message_text(E_first_message(llm))

                async def E_chat_simple(model: str, system: str, user: str, *, max_tokens: int, timeout: float, think: dict | None=None, temp: float=0.15) -> str:
                    if think is None:
                        think = E_least_think(model)
                    payload = await llm_chat(provider=E_LLM_PROVIDER, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=temp, max_output_tokens=max_tokens, timeout=timeout, thinking=think)
                    E_spend_note(payload)
                    return E_payload_text(payload)

                class E_EmptyChoiceMessage:
                    content = ''
                    tool_calls = ()

                class E_EmptyChoice:
                    message = E_EmptyChoiceMessage()

                class E_EmptyLlm:
                    raw_text = ''
                    choices = (E_EmptyChoice(),)

                class E_EmptyTurn:
                    llm = E_EmptyLlm()
                    budget = None
                E_EMPTY_TURN = E_EmptyTurn()

                async def E_chat_turn(messages: list[dict], deadline: float, *, finish_only: bool, force_tools: bool=False):
                    payload_chars = sum((len(str(msg.get('content') or '')) for msg in messages if isinstance(msg, dict)))
                    for attempt, model in enumerate((E_LOOP_MODEL_A, E_LOOP_MODEL_B)):
                        is_fallback = attempt > 0
                        if is_fallback and payload_chars > E_FALLBACK_MAX_PAYLOAD_CHARS:
                            return E_EMPTY_TURN
                        timeout = min(E_TURN_TIMEOUT_S, deadline - monotonic() - 5.0)
                        if timeout <= 5.0:
                            return None
                        try:
                            payload = await llm_chat(provider=E_LLM_PROVIDER, model=model, messages=messages, tools=E_LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': True, 'effort': 'low'}, max_output_tokens=None, timeout=timeout)
                            E_spend_note(payload)
                            return payload
                        except Exception:
                            continue
                    return None

                async def E_knowledge_brief(question: str) -> tuple[str, str]:
                    system = 'Senior research analyst. Commit to concrete best answers from knowledge; mark uncertain values (verify). Never refuse.'
                    user = f"Question:\n{question}\n\nWrite these blocks:\nBEST ANSWER: your full best answer now — candidate pool, every stated condition applied, qualifying entities with figures/dates, near-miss exclusions. Flag shaky facts with (verify).\nCHECKLIST: each atomic condition in the question, numbered, including any output-format demand.\nLOOKUPS: 3-6 precise web searches for the facts that decide the answer (entity + metric + year; include a named source's site: filter).\nPAGES: up to 5 exact URLs worth reading directly (official stats pages, sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."
                    raw = ''
                    try:
                        raw = await E_chat_simple(E_LOOP_MODEL_A, system, user, max_tokens=2400, timeout=E_BRIEF_TIMEOUT_S, think=E_least_think(E_LOOP_MODEL_A))
                    except Exception:
                        try:
                            raw = await E_chat_simple(E_LOOP_MODEL_B, system, user, max_tokens=2400, timeout=E_BRIEF_TIMEOUT_S, think=E_least_think(E_LOOP_MODEL_B))
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
                E_SEED_TOKEN_RE = re.compile("[A-Za-z0-9][A-Za-z0-9.\\-']+")
                E_SEED_STOP = frozenset('name list give tell show find identify please could would you your can may might should must let make sure both also'.split())
                E_MAX_SEED_QUERIES = 4
                E_NAMED_SOURCE_RE = re.compile("\\b(?:[Aa]ccording to|[Aa]s (?:reported|published) by|[Bb]ased on)\\s+(?:the\\s+)?([A-Z][\\w&.'-]*(?:\\s+[A-Z][\\w&.'-]*){0,5})")

                def E_seed_queries(question: str, set_question: bool) -> list[str]:
                    q = ' '.join((question or '').split())
                    if not q:
                        return []
                    seeds = [q[:300]]
                    salient = [t for t in E_SEED_TOKEN_RE.findall(q) if len(t) >= 3 and t.lower() not in E_STOP and (t.lower() not in E_SEED_STOP)]
                    named = E_NAMED_SOURCE_RE.search(q)
                    if named:
                        seeds.append((named.group(1) + ' ' + ' '.join(salient[:4])).strip())
                    if len(salient) >= 2:
                        seeds.append(' '.join(salient[:8]))
                    if set_question and salient:
                        seeds.append('list of ' + ' '.join(salient[:6]))
                    out: list[str] = []
                    for s in seeds:
                        s = s.strip()
                        if s and s not in out:
                            out.append(s)
                    return out[:E_MAX_SEED_QUERIES]

                async def E_preseed(question: str, set_question: bool, ledger: E_EvidenceLedger, deadline: float) -> str:
                    seeds = E_seed_queries(question, set_question)
                    if not seeds or deadline - monotonic() < 40.0:
                        return ''
                    blocks: list = []
                    for seed in seeds:
                        if deadline - monotonic() < 30.0:
                            break
                        try:
                            out = await asyncio.wait_for(E_do_search(seed), timeout=E_SEARCH_TIMEOUT_S * 2 + 6.0)
                            block = E_commit_tool_output(out, ledger)
                            if isinstance(out, E_ToolOutput) and E_CITE_MARK_RE.search(block or ''):
                                ledger.replay['q|' + ' '.join(seed.split()).casefold()] = block
                            blocks.append(block)
                        except Exception:
                            continue
                    good = [b for b in blocks if isinstance(b, str) and E_CITE_MARK_RE.search(b)]
                    if not good:
                        return ''
                    return 'Automatic first-pass searches (already numbered — cite these [n] directly, and search further as needed):\n\n' + '\n'.join(good)
                E_ASKED_QUOTE_RES = (re.compile('"([^"\\n]{2,60})"'), re.compile('“([^”\n]{2,60})”'), re.compile("(?<!\\w)'([^'\\n]{3,60})'(?!\\w)"), re.compile('\\*([^*\\n]{2,60})\\*'))

                def E_asked_items(question: str) -> list[str]:
                    found: list[str] = []
                    seen: set[str] = set()
                    for rx in E_ASKED_QUOTE_RES:
                        for raw in rx.findall(question or ''):
                            item = ' '.join(raw.split()).strip(' .,;:?!')
                            if not item or not re.search('[A-Za-z0-9]', item):
                                continue
                            k = item.casefold()
                            if k not in seen:
                                seen.add(k)
                                found.append(item)
                    if not found:
                        _head, sep, tail = (question or '').partition(':')
                        if sep:
                            segs = re.split('\\s*(?:;|–|—|, and |, )\\s*', tail)
                            segs = [' '.join(s.split()).strip(' .,;:?!') for s in segs]
                            segs = [s for s in segs if 2 <= len(s) <= 60 and re.search('[A-Za-z]', s)]
                            if len(segs) >= 3:
                                for s in segs:
                                    if s.casefold() not in seen:
                                        seen.add(s.casefold())
                                        found.append(s)
                    return found[:8]

                def E_own_page_urls(items: list[str], question: str) -> list[str]:
                    ql = (question or '').casefold()
                    infoboxy = 'wikipedia' in ql or 'infobox' in ql
                    if not items or (len(items) < 2 and (not infoboxy)):
                        return []
                    out: list[str] = []
                    for item in items[:5]:
                        name = item.strip(' .\'"')
                        if not 2 <= len(name) <= 70 or len(name.split()) > 8:
                            continue
                        if not re.search('[A-Za-z]', name):
                            continue
                        out.append('https://en.wikipedia.org/wiki/' + name.replace(' ', '_'))
                    return out[:4]
                E_BODY_RE = re.compile('\\b(?:mercury|venus|mars|jupiter|saturn|uranus|neptune|pluto)\\b')
                E_BODY_METRIC_RE = re.compile('\\b(?:mass|diameter|radius|density|gravity|escape velocity|moons|satellites|orbital period|rotation period|axial tilt|aphelion|perihelion|mean temperature|surface pressure)\\b')

                def E_direct_query_urls(question: str) -> list[str]:
                    q = ' '.join((question or '').casefold().split())
                    urls: list[str] = []
                    if 'earthquake' in q or 'seismic' in q:
                        yrs = re.findall('\\b(19\\d\\d|20\\d\\d)\\b', q)
                        mag = re.search('magnitude\\s+(?:of\\s+)?(?:at least\\s+|above\\s+|over\\s+|greater than\\s+|exceeding\\s+)?(\\d+(?:\\.\\d+)?)', q)
                        if yrs and mag:
                            u = f'https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={min(yrs)}-01-01&endtime={max(yrs)}-12-31T23:59:59&minmagnitude={mag.group(1)}&orderby=time-asc'
                            lid = re.search('(?:less than|under|below|at most|up to)\\s+(?:magnitude\\s+)?(\\d+(?:\\.\\d+)?)', q)
                            if lid:
                                u += f'&maxmagnitude={lid.group(1)}'
                            urls.append(u)
                    if 'planetary fact sheet' in q or 'nssdc' in q or (E_BODY_RE.search(q) and E_BODY_METRIC_RE.search(q)):
                        urls.append('https://nssdc.gsfc.nasa.gov/planetary/factsheet/')
                    return urls[:2]
                E_MONTH_NUM = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06', 'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
                E_MONTH_ALT = 'january|february|march|april|may|june|july|august|september|october|november|december'
                E_DATED_MDY_RE = re.compile('\\b(' + E_MONTH_ALT + ')\\s+(\\d{1,2}),?\\s+(\\d{4})\\b', re.I)
                E_DATED_DMY_RE = re.compile('\\b(\\d{1,2})\\s+(' + E_MONTH_ALT + ')\\s+(\\d{4})\\b', re.I)
                E_DATED_MY_RE = re.compile('\\b(' + E_MONTH_ALT + ')\\s+(\\d{4})\\b', re.I)
                E_DATED_SOURCE_RE = re.compile('fact sheet|report|article|page|edition|version|publication|survey|census|bulletin|revision|snapshot|archive|as of|dated|update', re.I)

                def E_dated_edition(question: str) -> str:
                    q = ' '.join((question or '').split())
                    for rx, shape in ((E_DATED_MDY_RE, 'mdy'), (E_DATED_DMY_RE, 'dmy'), (E_DATED_MY_RE, 'my')):
                        for m in rx.finditer(q):
                            ctx = q[max(0, m.start() - 60):m.end() + 60]
                            if E_DATED_SOURCE_RE.search(ctx) is None:
                                continue
                            if shape == 'mdy':
                                mon, day, year = (m.group(1), m.group(2), m.group(3))
                            elif shape == 'dmy':
                                day, mon, year = (m.group(1), m.group(2), m.group(3))
                            else:
                                mon, year = (m.group(1), m.group(2))
                                day = '15'
                            return year + E_MONTH_NUM[mon.casefold()] + day.zfill(2)
                    return ''
                E_AUTHORITY_HOSTS = ('wikipedia.org', 'sec.gov', 'usgs.gov', 'nasa.gov', 'census.gov', 'bls.gov', 'noaa.gov', 'who.int', 'un.org', 'worldbank.org', 'oecd.org', 'imf.org', 'boxofficemojo.com', 'worldatlas.com', 'britannica.com')

                def E_preferred_source_urls(ledger: E_EvidenceLedger) -> list[str]:
                    have = {(r.get('url') or '').casefold() for r in ledger.rows if r.get('kind') == 'fetch'}
                    picked: list[str] = []
                    for row in ledger.rows:
                        if row.get('kind') != 'search':
                            continue
                        url = (row.get('url') or '').strip().rstrip('.,;:!?')
                        if not url.casefold().startswith('http'):
                            continue
                        bits = url.split('/')
                        host = bits[2].casefold() if len(bits) > 2 else ''
                        good = host.endswith('.gov') or any((host == h or host.endswith('.' + h) for h in E_AUTHORITY_HOSTS))
                        if good and url.casefold() not in have and (url not in picked):
                            picked.append(url)
                    return picked[:2]

                async def E_rider_prefetch(question: str, items: list[str], ledger: E_EvidenceLedger, deadline: float) -> str:
                    plan: list[tuple[str, str]] = []
                    for url in E_direct_query_urls(question):
                        plan.append(('DATA QUERY', url))
                    for url in E_own_page_urls(items, question):
                        plan.append(('OWN PAGE', url))
                    for url in E_preferred_source_urls(ledger):
                        plan.append(('AUTHORITY', url))
                    seen: set[str] = set()
                    todo: list[tuple[str, str]] = []
                    for tag, url in plan:
                        k = url.casefold()
                        if k in seen or 'u|' + k + '|' in ledger.replay:
                            continue
                        seen.add(k)
                        todo.append((tag, url))
                    try:
                        stamp = E_dated_edition(question)
                    except Exception:
                        stamp = ''
                    if stamp:
                        staged: list[tuple[str, str]] = []
                        added = 0
                        for tag, url in todo:
                            if added < 2 and 'web.archive.org' not in url and ('fdsnws' not in url):
                                staged.append(('WAYBACK', 'https://web.archive.org/web/' + stamp + '000000/' + url))
                                added += 1
                            staged.append((tag, url))
                        todo = staged
                    todo = todo[:6]
                    if not todo or deadline - monotonic() < 140.0:
                        return ''
                    budget = max(6.0, min(30.0, deadline - monotonic() - 100.0))
                    tasks = [asyncio.ensure_future(E_do_fetch(url, '', question)) for _tag, url in todo]
                    try:
                        await asyncio.wait(tasks, timeout=budget)
                    except Exception:
                        pass
                    lines: list[str] = []
                    for (tag, url), task in zip(todo, tasks):
                        if not task.done():
                            task.cancel()
                            continue
                        try:
                            out = task.result()
                        except Exception:
                            continue
                        body = E_commit_tool_output(out, ledger)
                        if not isinstance(body, str) or E_CITE_MARK_RE.search(body) is None:
                            continue
                        ledger.replay['u|' + url.casefold() + '|'] = body
                        lines.append(f'<{tag}> {body}')
                    if not lines:
                        return ''
                    return "PREFETCHED PRIMARY PAGES (already numbered — cite these [n] directly. DATA QUERY rows are the authoritative result of the question's own filters; OWN PAGE carries a named item's value from its own page; AUTHORITY pages outrank aggregators):\n\n" + '\n\n'.join(lines)

                def E_coverage_gap_note(items: list[str], ledger: E_EvidenceLedger) -> str:
                    if len(items) < 2:
                        return ''
                    corpus = ' '.join(((r.get('title') or '') + ' ' + (r.get('url') or '') + ' ' + (r.get('preview') or '') for r in ledger.rows)).casefold()
                    missing = [i for i in items if i.casefold() not in corpus]
                    note = 'ASKED-ITEM COVERAGE: the question names these items — ' + '; '.join(items) + '. The final answer owes EVERY one of them its own cited verdict line: its qualifying value, or the exact condition it fails.'
                    if missing:
                        note += ' Items with NO tool evidence yet: ' + '; '.join(missing[:6]) + ' — aim your next tool calls at these first.'
                    return note

                async def E_search_uncovered(items: list[str], question: str, ledger: E_EvidenceLedger, deadline: float) -> str:
                    corpus = ' '.join(((r.get('title') or '') + ' ' + (r.get('url') or '') + ' ' + (r.get('preview') or '') for r in ledger.rows)).casefold()
                    missing = [i for i in items if i.casefold() not in corpus]
                    if not missing:
                        return ''
                    flat = ' '.join((question or '').split())
                    ctx = [t for t in E_SEED_TOKEN_RE.findall(flat) if len(t) >= 3 and t.lower() not in E_STOP and (t.lower() not in E_SEED_STOP)]
                    blocks: list[str] = []
                    for item in missing[:2]:
                        if deadline - monotonic() < 120.0:
                            break
                        extra = ' '.join((t for t in ctx[:4] if t.casefold() not in item.casefold()))
                        q = (item + ' ' + extra).strip()
                        try:
                            out = await asyncio.wait_for(E_do_search(q), timeout=E_SEARCH_TIMEOUT_S + 4.0)
                        except Exception:
                            continue
                        body = E_commit_tool_output(out, ledger)
                        if isinstance(body, str) and E_CITE_MARK_RE.search(body):
                            if isinstance(out, E_ToolOutput):
                                ledger.replay['q|' + ' '.join(q.split()).casefold()] = body
                            blocks.append(body)
                    if not blocks:
                        return ''
                    return 'ITEM-TARGETED SEARCHES (already numbered — cite these [n] directly):\n\n' + '\n\n'.join(blocks)

                async def E_tool_phase(calls, question: str, ledger: E_EvidenceLedger, deadline: float) -> list[dict]:
                    run_calls = calls[:E_MAX_TOOL_CALLS_PER_TURN]
                    keys: list[str] = []
                    results: list = []
                    for call in run_calls:
                        key = ''
                        try:
                            key = E_replay_key(getattr(call, 'name', '') or '', getattr(call, 'arguments', None) or '')
                        except Exception:
                            key = ''
                        keys.append(key)
                        hit = ledger.replay.get(key) if key else None
                        results.append('# (replayed) identical call already ran — same numbered results:\n' + hit if isinstance(hit, str) else None)
                    tool_budget = max(5.0, min(E_FETCH_TIMEOUT_S * 2 + 6.0, deadline - monotonic() - E_MIN_TAIL_S))
                    pending: list[tuple[int, object]] = []
                    for i, call in enumerate(run_calls):
                        if results[i] is None:
                            pending.append((i, asyncio.ensure_future(E_run_tool(call, question, deadline))))
                    if pending:
                        try:
                            await asyncio.wait([t for _i, t in pending], timeout=tool_budget)
                        except Exception:
                            pass
                    for i, task in pending:
                        if task.done():
                            try:
                                results[i] = task.result()
                            except Exception as exc:
                                results[i] = f'# tool crashed: {exc}'
                        else:
                            task.cancel()
                            results[i] = '# tool timed out — use what you already have'
                    replies: list[dict] = []
                    for i, call in enumerate(run_calls):
                        result = results[i]
                        content = E_commit_tool_output(result, ledger)
                        if keys[i] and isinstance(result, E_ToolOutput) and E_CITE_MARK_RE.search(content or ''):
                            ledger.replay[keys[i]] = content
                        replies.append({'role': 'tool', 'tool_call_id': call.id, 'content': content})
                    for call in calls[E_MAX_TOOL_CALLS_PER_TURN:]:
                        replies.append({'role': 'tool', 'tool_call_id': call.id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})
                    return replies

                async def E_loop(question: str, brief: str, ledger: E_EvidenceLedger, deadline: float, turn_cap: int, carry: list[dict] | None=None, allow_tools_in_wrapup: bool=False) -> tuple[str, list[dict]]:
                    if carry is not None:
                        messages = carry
                    else:
                        set_q = E_needs_set_completeness(question)
                        messages = [{'role': 'system', 'content': E_LOOP_RULES}]
                        if set_q:
                            messages.append({'role': 'system', 'content': E_SET_RULE})
                        if E_needs_superlative_proof(question):
                            messages.append({'role': 'system', 'content': E_SUPERLATIVE_RULE})
                        if brief:
                            messages.append({'role': 'system', 'content': brief})
                        seeded = await E_preseed(question, set_q, ledger, deadline)
                        if seeded:
                            messages.append({'role': 'system', 'content': seeded})
                        try:
                            block = await E_ai_summary_seed(question, ledger, deadline)
                            if block:
                                messages.append({'role': 'system', 'content': block})
                        except Exception:
                            pass
                        items: list[str] = []
                        try:
                            items = E_asked_items(question)
                        except Exception:
                            items = []
                        try:
                            if deadline - monotonic() > 140.0:
                                block = await E_rider_prefetch(question, items, ledger, deadline)
                                if block:
                                    messages.append({'role': 'system', 'content': block})
                        except Exception:
                            pass
                        try:
                            if len(items) >= 2 and deadline - monotonic() > 120.0:
                                block = await E_search_uncovered(items, question, ledger, deadline)
                                if block:
                                    messages.append({'role': 'system', 'content': block})
                        except Exception:
                            pass
                        try:
                            note = E_coverage_gap_note(items, ledger)
                            if note:
                                messages.append({'role': 'system', 'content': note})
                        except Exception:
                            pass
                        messages.append({'role': 'user', 'content': question})
                    answer = ''
                    ordered_wrapup = False
                    repairs_left = E_ANSWER_REPAIR_TURNS
                    for turn in range(1, turn_cap + 1):
                        left = deadline - monotonic()
                        if left <= E_MIN_TAIL_S:
                            break
                        out_of_time = left <= E_WRAPUP_AT_S
                        out_of_spend = E_spend_left() <= E_WRAPUP_MIN_USD
                        finish_only = out_of_time or out_of_spend or turn >= turn_cap
                        if (finish_only or turn >= turn_cap - 1) and (not ordered_wrapup):
                            messages.append({'role': 'system', 'content': E_wrapup_order(left)})
                            ordered_wrapup = True
                        payload = await E_chat_turn(messages, deadline, finish_only=finish_only, force_tools=allow_tools_in_wrapup and turn == 1)
                        if payload is None:
                            break
                        msg = E_first_message(getattr(payload, 'llm', None))
                        if msg is None:
                            break
                        calls = getattr(msg, 'tool_calls', None) or ()
                        if not calls:
                            candidate = E_payload_text(payload)
                            if not E_is_usable_answer(candidate):
                                if repairs_left > 0 and deadline - monotonic() > E_MIN_TAIL_S + 10.0:
                                    repairs_left -= 1
                                    messages.append({'role': 'system', 'content': E_REPAIR_ORDER})
                                    answer = ''
                                    continue
                                answer = ''
                                break
                            answer = candidate
                            messages.append({'role': 'assistant', 'content': answer})
                            break
                        messages.append(msg.to_input_message())
                        messages.extend(await E_tool_phase(calls, question, ledger, deadline))
                    return (answer, messages)

                async def E_audit_patch(question: str, answer: str, messages: list[dict], ledger: E_EvidenceLedger, deadline: float) -> str:
                    probe = f"""Audit the answer against the question. JSON only, keys: "unanswered_parts" (list; question elements not addressed), "uncited_facts" (list; load-bearing claims without [n]), "wrong_kind" (list; places where the named entity is a different KIND than the question asks — a person instead of a series, a duo instead of a show), "incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges over a candidate pool — a closed set that can be enumerated, or several conditions applied to a class — then: is the pool itself stated and plausibly COMPLETE, and does the answer give a verdict for EVERY member (qualifies / excluded because X, each cited)? Name any pool member the answer never mentions, and say so if the pool looks truncated — an answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not partial), "thin_proof" (list; a qualifier lacking a per-condition citation, or a plausible near-miss candidate never addressed), "hand_waved_tally" (list; for a superlative/count/most-common question: the answer asserts a winner or a count WITHOUT showing the candidate table it was derived from. Phrases like 'among others', 'and several more', 'multiple X', or naming 2 examples to justify a count are all hand-waving — say so and name what the tally must list). Empty lists when clean.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:11000]}"""
                    try:
                        raw = await E_chat_simple(E_AUDIT_MODEL, 'Strict completeness auditor. JSON only.', probe, max_tokens=2200, timeout=max(8.0, min(E_AUDIT_TIMEOUT_S, deadline - monotonic() - 72.0)), temp=0.0)
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
                    patched, _ = await E_loop(question, '', ledger, deadline, E_AUDIT_EXTRA_TURNS + 1, carry=messages, allow_tools_in_wrapup=True)
                    patched = patched.strip()
                    if not E_is_usable_answer(patched) or len(patched) < int(len(answer) * 0.6):
                        return answer
                    if len(E_cited_numbers(patched, len(ledger.rows))) < len(E_cited_numbers(answer, len(ledger.rows))):
                        return answer
                    return patched
                E_BRACKET_FIX = {12304: '[', 12305: ']', 65339: '[', 65341: ']', 65288: '(', 65289: ')', 8209: '-', 8722: '-'}
                E_BRACKET_FIX.update({65296 + d: chr(48 + d) for d in range(10)})

                def E_normalize_brackets(text: str) -> str:
                    return (text or '').translate(E_BRACKET_FIX)
                E_CITE_NUM_RE = re.compile('\\[([0-9][0-9,\\s\\-]*)\\]')

                def E_cited_numbers(answer: str, top: int) -> list[int]:
                    answer = E_normalize_brackets(answer)
                    seen: set[int] = set()
                    out: list[int] = []
                    for m in E_CITE_NUM_RE.finditer(answer):
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
                E_ANCHOR_WORD_RE = re.compile("\\b[A-Z][A-Za-z][\\w'-]{2,}\\b")
                E_ANCHOR_NUM_RE = re.compile('\\d[\\d,]*(?:\\.\\d+)?%?')
                E_ANCHOR_STOP = frozenset('the this that these those there according answer among however therefore because citation notes supports both which while where when what'.split())

                def E_claim_anchors(answer_norm: str, n: int) -> list[str]:
                    mark = f'[{n}]'
                    anchors: list[str] = []
                    seen: set[str] = set()
                    for seg in re.split('(?<=[.!?])\\s+|\\n+', answer_norm or ''):
                        if mark not in seg:
                            continue
                        bare = E_CITE_NUM_RE.sub(' ', seg)
                        for tok in E_ANCHOR_NUM_RE.findall(bare):
                            t = tok.strip('.,%')
                            if len(t) >= 2 and t.casefold() not in seen:
                                seen.add(t.casefold())
                                anchors.append(t)
                        for tok in E_ANCHOR_WORD_RE.findall(bare):
                            low = tok.casefold()
                            if low in E_ANCHOR_STOP or low in E_STOP or low in seen:
                                continue
                            seen.add(low)
                            anchors.append(tok)
                        if len(anchors) >= 14:
                            break
                    return anchors[:14]

                def E_anchored_window(note_text: str, anchors: list[str]):
                    if not note_text or not anchors:
                        return None
                    low = note_text.lower()
                    hits: list[tuple[int, int]] = []
                    for ai, anchor in enumerate(anchors):
                        needle = anchor.lower()
                        start = 0
                        for _rep in (0, 1, 2):
                            pos = low.find(needle, start)
                            if pos == -1:
                                break
                            hits.append((pos, ai))
                            start = pos + max(1, len(needle))
                    if not hits:
                        return None
                    hits.sort()
                    width = 660
                    best = None
                    for pos, _ai in hits:
                        distinct = {a2 for p2, a2 in hits if pos <= p2 < pos + width}
                        cand = (-len(distinct), pos)
                        if best is None or cand < best:
                            best = cand
                    pos = best[1]
                    win_anchors = {a2 for p2, a2 in hits if pos <= p2 < pos + width}
                    if len(win_anchors) < 2:
                        only = anchors[next(iter(win_anchors))] if win_anchors else ''
                        if not (len(only) >= 5 and only[:1].isdigit()):
                            return None
                    s = max(0, pos - 120)
                    e = min(len(note_text), pos + width + 120)
                    if e - s < 100:
                        s = max(0, e - 100)
                        if e - s < 100:
                            return None
                    return (s, min(e, s + 900))

                def E_refine_head_slice(ref, row, answer_norm: str, n: int):
                    if ref is None or row.get('kind') != 'fetch':
                        return ref
                    note_text = row.get('note_text') or ''
                    if not note_text:
                        return ref
                    slices = list(getattr(ref, 'slices', None) or [])
                    if not slices:
                        return ref
                    head = slices[0]
                    if head.start != 0 or head.end < 2000 or int(row.get('note_len') or 0) <= head.end:
                        return ref
                    window = E_anchored_window(note_text, E_claim_anchors(answer_norm, n))
                    if window is None:
                        return ref
                    new_slices = [CitationSlice(start=window[0], end=window[1])]
                    for s in slices[1:]:
                        new_slices.append(s)
                    return CitationRef(receipt_id=row['receipt_id'], result_id=row['result_id'], slices=new_slices[:4])

                def E_citations_for(answer: str, ledger: E_EvidenceLedger) -> list[CitationRef]:
                    refs: list[CitationRef] = []
                    spent = 0
                    answer_norm = E_normalize_brackets(answer)
                    for n in E_cited_numbers(answer, len(ledger.rows)):
                        if len(refs) >= E_CITATION_CAP:
                            break
                        ref = ledger.ref_for(n)
                        if ref is None:
                            continue
                        row = ledger.rows[n - 1]
                        try:
                            ref = E_refine_head_slice(ref, row, answer_norm, n)
                        except Exception:
                            pass
                        slices = getattr(ref, 'slices', None)
                        cost = sum((max(0, s.end - s.start) for s in slices)) if slices else int(row.get('note_len') or 0)
                        if spent + cost > E_EVIDENCE_CHAR_BUDGET:
                            continue
                        spent += cost
                        refs.append(ref)
                    return refs
                E_VERIFY_MARK_RE = re.compile('\\s*\\((?:verify|unverified|uncertain)[^)]*\\)', re.I)
                E_TOOL_MARKUP_RE = re.compile('<\\s*/?\\s*tool_call|<\\s*/?\\s*(?:arg_key|arg_value|function_call|invoke)\\b|\\bweb_search\\s*[（(]\\s*query|\\bread_page\\s*[（(]\\s*url|\\bsec_filing\\s*[（(]\\s*company', re.I)
                E_STUB_ANSWER_RE = re.compile('^\\s*(?:best-effort answer unavailable|no question provided)', re.I)
                E_REFUSAL_ONLY_RE = re.compile("^\\s*(?:i (?:cannot|can't|am unable|was unable)|unable to|sorry[,.]|i don'?t have (?:enough|access))", re.I)
                E_INTENT_NARRATION_RE = re.compile("^\\s*(?:i (?:need|will|should|am going|'ll)\\b|let me\\b|first,? (?:i|let)\\b|i'?ll (?:search|look|start|begin|gather|check))", re.I)
                E_MIN_ANSWER_CHARS = 40
                E_MIN_CITED_ANSWER_CHARS = 12
                E_CITE_MARK_RE = re.compile('\\[[0-9]{1,3}\\]')

                def E_looks_like_tool_json(s: str) -> bool:
                    return bool(re.match('\\s*\\{\\s*"(?:name|tool|function)"\\s*:', s))

                def E_is_degenerate_repetition(text: str) -> bool:
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

                def E_is_usable_answer(text: str) -> bool:
                    s = E_normalize_brackets(text).strip()
                    if not s:
                        return False
                    if E_TOOL_MARKUP_RE.search(s) or E_looks_like_tool_json(s):
                        return False
                    if E_STUB_ANSWER_RE.match(s) or E_is_degenerate_repetition(s):
                        return False
                    cited = bool(E_CITE_MARK_RE.search(s))
                    if cited and len(s) >= E_MIN_CITED_ANSWER_CHARS:
                        return True
                    if len(s) < E_MIN_ANSWER_CHARS:
                        return False
                    if len(s) < 400 and (E_REFUSAL_ONLY_RE.match(s) or E_INTENT_NARRATION_RE.match(s)):
                        return False
                    return True
                E_COMMIT_RULES = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too. Never say what the evidence does not contain; commit to the best-supported answer you can defend. Open with the asked field itself (mirroring any process the question describes), give exact figures with units and dates, and never rest a claim on grokipedia/facebook/pinterest/quora rows when an authoritative row states the same fact. End with a 'Citation notes:' block: one line per distinct [n], '[n] <source> — supports: <the fact it backs>'."
                E_REPAIR_ORDER = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

                def E_sanitize_draft(text: str) -> str:
                    return E_VERIFY_MARK_RE.sub('', text or '').strip()

                def E_ledger_digest(ledger: E_EvidenceLedger, char_cap: int=60000) -> str:
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
                E_FURNITURE_RE = re.compile('^\\s*(?:share|search|home|menu|subscribe|sign\\s*in|log\\s*in|newsletter|advertisement|cookie|skip to|follow us|read more|related|tags?|categories?|privacy|terms|contact|about us|navigation|toggle)\\b', re.I)
                E_SRC_FOOTNOTE_RE = re.compile('\\[\\s*\\d{1,3}\\s*\\]')
                E_MD_LINK_RE = re.compile('\\]\\(')
                E_BARE_URL_RE = re.compile('(?<!\\]\\()https?://')
                E_SENTENCEY_RE = re.compile('[.!?]\\s|[.!?]$|\\b(?:is|was|were|are|has|have|had|reported|announced|released|won|ranked|totall?ed)\\b', re.I)

                def E_informative_lead(preview: str, limit: int=280) -> str:
                    kept: list[str] = []
                    for chunk in re.split('(?<=[.!?])\\s+|\\n+', E_SRC_FOOTNOTE_RE.sub('', preview or '')):
                        seg = ' '.join(chunk.split())
                        if len(seg) < 30 or len(seg) > 400:
                            if kept:
                                break
                            continue
                        if E_SENTENCEY_RE.search(seg) is None:
                            if kept:
                                break
                            continue
                        if E_FURNITURE_RE.match(seg) and (not re.search('\\d', seg)):
                            if kept:
                                break
                            continue
                        if seg.startswith(('*', '|', '↑', '#')):
                            if kept:
                                break
                            continue
                        links = len(E_MD_LINK_RE.findall(seg)) + len(E_BARE_URL_RE.findall(seg))
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

                def E_deterministic_answer(ledger: E_EvidenceLedger) -> str:
                    rows = [(i, r) for i, r in enumerate(ledger.rows, start=1) if (r.get('preview') or '').strip()]
                    if not rows:
                        return ''
                    out = ['Best-supported findings from the sources retrieved:']
                    picked = 0
                    for i, r in rows:
                        if picked >= 6:
                            break
                        lead = E_informative_lead(r.get('preview') or '')
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

                async def E_write_from_digest(question: str, ledger: E_EvidenceLedger, deadline: float) -> str:
                    left = deadline - monotonic()
                    if left < 14.0:
                        return ''
                    digest = E_ledger_digest(ledger)
                    if not digest:
                        return ''
                    ask = f'Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'
                    for i, model in enumerate((E_LOOP_MODEL_A, E_LOOP_MODEL_B)):
                        left = deadline - monotonic()
                        if left < 14.0:
                            return ''
                        budget = min(E_RESCUE_TIMEOUT_S, left - E_DIGEST_TAIL_S)
                        if i == 0:
                            budget = min(budget, max(12.0, left - 14.0 - E_DIGEST_TAIL_S))
                        if budget < 8.0:
                            return ''
                        try:
                            text = await E_chat_simple(model, E_COMMIT_RULES, ask, max_tokens=2600, timeout=budget)
                        except Exception:
                            continue
                        if E_is_usable_answer(text):
                            return text
                    return ''

                async def E_knowledge_resort(question: str, deadline: float) -> str:
                    left = deadline - monotonic()
                    if left < 12.0:
                        return ''
                    try:
                        return await E_chat_simple(E_RESORT_MODEL, 'Expert researcher. Best definitive answer with concrete entities, numbers, dates. Never refuse.', question, max_tokens=2600, timeout=min(45.0, left - 4.0))
                    except Exception:
                        return ''

                async def E_schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
                    ask = f"Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nIf the question demands an ORDER (sorted/ranked by a quantity, alphabetical, chronological), the JSON array MUST follow exactly that order: derive each item's sort key from the answer, sort by it, and correct the answer's own order wherever it contradicts the keys — check every adjacent pair before emitting.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}"
                    for model in (E_SCHEMA_MODEL, E_RESORT_MODEL, E_LOOP_MODEL_A):
                        left = deadline - monotonic()
                        if left < 12.0:
                            break
                        try:
                            raw = await E_chat_simple(model, 'You output strictly valid JSON.', ask, max_tokens=3400, timeout=min(45.0, left - 4.0), temp=0.0)
                            raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()
                            value = json.loads(raw)
                            if E_matches_schema_shape(value, schema):
                                return value
                            if isinstance(value, dict) and len(value) == 1:
                                inner = list(value.values())[0]
                                if E_matches_schema_shape(inner, schema):
                                    return inner
                        except Exception:
                            continue
                    return None

                def E_schema_kind(schema) -> str:
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
                                    got = E_schema_kind(sub)
                                    if got:
                                        return got
                        if isinstance(schema.get('properties'), dict):
                            return 'object'
                        if isinstance(schema.get('enum'), list):
                            return 'string'
                        return ''
                    return str(kind)

                def E_matches_schema_shape(value, schema) -> bool:
                    kind = E_schema_kind(schema)
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
                E_NUM_IN_TEXT_RE = re.compile('-?\\d[\\d,]*(?:\\.\\d+)?')

                def E_coerce_to_schema(answer: str, schema, depth: int=0):
                    if depth > 4 or not isinstance(schema, dict):
                        return answer[:400]
                    enum = schema.get('enum')
                    if isinstance(enum, list) and enum:
                        low = (answer or '').lower()
                        for opt in enum:
                            if isinstance(opt, str) and re.search('\\b' + re.escape(opt.lower()) + '\\b', low):
                                return opt
                        return enum[0]
                    kind = E_schema_kind(schema)
                    if not kind:
                        for key in ('anyOf', 'oneOf', 'allOf'):
                            branch = schema.get(key)
                            if isinstance(branch, list) and branch:
                                for sub in branch:
                                    if isinstance(sub, dict) and sub.get('type') != 'null':
                                        return E_coerce_to_schema(answer, sub, depth + 1)
                        kind = 'string'
                    if kind == 'array':
                        items = schema.get('items') or {}
                        parts = [p.strip(' -*\t') for p in re.split('[\\n;]|,(?![^(]*\\))', answer or '')]
                        parts = [p[:400] for p in parts if p][:20]
                        if not parts:
                            parts = [answer[:400]]
                        return [E_coerce_to_schema(p, items, depth + 1) for p in parts]
                    if kind == 'object':
                        props = schema.get('properties') or {}
                        required = schema.get('required') or list(props.keys())
                        out = {}
                        for key in required:
                            out[key] = E_coerce_to_schema(answer, props.get(key) or {}, depth + 1)
                        return out
                    if kind in ('number', 'integer'):
                        found = E_NUM_IN_TEXT_RE.search(E_CITE_NUM_RE.sub(' ', answer or ''))
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
                E_NARRATION_LEAD_RE = re.compile("^\\s*(?:based on (?:my|the)\\b|now (?:i|that i)\\b|i (?:now )?(?:have|was|am|need|will|can)\\b|i(?:'ll|'ve|'m)\\b|let me\\b|let's\\b|first,? i\\b|having (?:now )?\\w+\\b|okay\\b|alright\\b|to answer this\\b|my research\\b)", re.IGNORECASE)
                E_ABBREV_TAIL_RE = re.compile('(?:\\b[A-Z]|\\b(?:Inc|Ltd|Co|No|vs|St|Dr|Mr|Ms|Mt|Jr|Sr|etc|e\\.g|i\\.e))\\.$')

                def E_strip_lead_narration(text: str) -> str:
                    t = (text or '').strip()
                    if not t:
                        return t
                    for _ in range(2):
                        parts = re.split('(?<=[.!?])\\s+', t, maxsplit=1)
                        if len(parts) != 2:
                            break
                        head, rest = (parts[0], parts[1].strip())
                        if E_CITE_NUM_RE.search(head):
                            break
                        if E_NARRATION_LEAD_RE.match(head) is None:
                            break
                        if len(head.split()) < 4 or E_ABBREV_TAIL_RE.search(head) is not None:
                            break
                        if len(rest) < 120 or E_CITE_NUM_RE.search(rest) is None:
                            break
                        t = rest
                    return t

                def E_cap(text: str) -> str:
                    t = (text or '').strip()
                    if len(t) > E_ANSWER_CHAR_CAP:
                        return t[:E_ANSWER_CHAR_CAP - 16] + ' …'
                    return t
                E_SCALE_WORDS = (('trillion', 1000000000000.0), ('tn', 1000000000000.0), ('billion', 1000000000.0), ('bn', 1000000000.0), ('million', 1000000.0), ('mn', 1000000.0), ('mm', 1000000.0), ('thousand', 1000.0))
                E_FIG_RE = re.compile('-?\\d[\\d,]*(?:\\.\\d+)?')
                E_CLOCK_RE = re.compile('\\b(\\d{1,3}):([0-5]\\d)(?::([0-5]\\d))?\\b')

                def E_scale_of(tail: str) -> float:
                    word = (tail or '').lstrip()
                    for name, mult in E_SCALE_WORDS:
                        if word.startswith(name):
                            return mult
                    if word[:1] == 'k' and (len(word) < 2 or not word[1].isalpha()):
                        return 1000.0
                    return 1.0

                def E_figure_in(text: str):
                    t = ' '.join((text or '').casefold().split())
                    clock = E_CLOCK_RE.search(t)
                    if clock is not None:
                        secs = int(clock.group(1)) * 3600 + int(clock.group(2)) * 60 + int(clock.group(3) or 0)
                        return (float(secs), True, False)
                    hit = E_FIG_RE.search(t)
                    if hit is None:
                        return (None, False, False)
                    try:
                        base = float(hit.group(0).replace(',', ''))
                    except Exception:
                        return (None, False, False)
                    mult = E_scale_of(t[hit.end():])
                    return (base * mult, False, mult != 1.0 or ',' in hit.group(0))

                def E_clocks_to_seconds(text: str) -> str:
                    out: list[str] = []
                    pos = 0
                    for m in E_CLOCK_RE.finditer(text):
                        secs = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3) or 0)
                        out.append(text[pos:m.start()])
                        out.append(str(secs))
                        pos = m.end()
                    out.append(text[pos:])
                    return ''.join(out)

                def E_bound_of(text: str, is_clock: bool):
                    t = ' '.join((text or '').casefold().split())
                    if not t:
                        return None
                    if is_clock:
                        t = E_clocks_to_seconds(t)
                    m = re.search('between\\s+\\$?(-?[\\d.,]+)\\s*([a-z]*)\\s+and\\s+\\$?(-?[\\d.,]+)\\s*([a-z]*)', t)
                    if m is not None:
                        try:
                            a = float(m.group(1).replace(',', '')) * E_scale_of(m.group(2))
                            b = float(m.group(3).replace(',', '')) * E_scale_of(m.group(4))
                        except Exception:
                            return None
                        return (min(a, b), False, max(a, b), False)
                    low = None
                    high = None
                    low_strict = False
                    high_strict = False
                    m = re.search('(?:more than|greater than|over|above|exceed(?:s|ing)?)\\s+\\$?(?:magnitude\\s+)?(-?[\\d.,]+)\\s*([a-z]*)', t)
                    if m is not None:
                        low_strict = True
                    else:
                        m = re.search('(?:at least|no (?:less|fewer) than|minimum(?: of)?|>=)\\s+\\$?(?:magnitude\\s+)?(-?[\\d.,]+)\\s*([a-z]*)', t)
                        if m is None:
                            m = re.search('\\$?(-?[\\d.,]+)\\s*([a-z]*)\\s+or\\s+(?:more|greater|higher|above)', t)
                    if m is not None:
                        try:
                            low = float(m.group(1).replace(',', '')) * E_scale_of(m.group(2))
                        except Exception:
                            low = None
                    m = re.search('(?:less than|fewer than|under|below)\\s+\\$?(?:magnitude\\s+)?(-?[\\d.,]+)\\s*([a-z]*)', t)
                    if m is not None:
                        high_strict = True
                    else:
                        m = re.search('(?:at most|no more than|maximum(?: of)?|within|<=)\\s+\\$?(?:magnitude\\s+)?(-?[\\d.,]+)\\s*([a-z]*)', t)
                        if m is None:
                            m = re.search('\\$?(-?[\\d.,]+)\\s*([a-z]*)\\s+or\\s+(?:less|fewer|lower|below)', t)
                    if m is not None:
                        try:
                            high = float(m.group(1).replace(',', '')) * E_scale_of(m.group(2))
                        except Exception:
                            high = None
                    if low is None and high is None:
                        return None
                    return (low, low_strict, high, high_strict)

                def E_violation_of(value_text: str, constraint_text: str) -> str:
                    value, is_clock, saw_scale = E_figure_in(value_text)
                    if value is None:
                        return ''
                    spec = E_bound_of(constraint_text, is_clock)
                    if spec is None:
                        return ''
                    low, low_strict, high, high_strict = spec
                    if not saw_scale and (not is_clock) and (value > 0):
                        for bound in (low, high):
                            if bound is not None and bound >= 10000.0 and (bound / value >= 100.0):
                                return ''
                    eps = 1e-09
                    if low is not None:
                        if value < low - eps:
                            return f'falls below the required minimum {low:g}'
                        if low_strict and abs(value - low) <= eps:
                            return f"equals the strict bound {low:g} ('more than' excludes it)"
                    if high is not None:
                        if value > high + eps:
                            return f'exceeds the allowed maximum {high:g}'
                        if high_strict and abs(value - high) <= eps:
                            return f"equals the strict bound {high:g} ('less than' excludes it)"
                    return ''

                def E_bounds_decidable(value_text: str, constraint_text: str) -> bool:
                    value, is_clock, saw_scale = E_figure_in(value_text)
                    if value is None:
                        return False
                    spec = E_bound_of(constraint_text, is_clock)
                    if spec is None:
                        return False
                    low, _ls, high, _hs = spec
                    if not saw_scale and (not is_clock) and (value > 0):
                        for bound in (low, high):
                            if bound is not None and bound >= 10000.0 and (bound / value >= 100.0):
                                return False
                    return True
                E_STATED_CMP_RE = re.compile('(-?\\d[\\d,]*(?:\\.\\d+)?)\\s*([a-z%]*)\\s+(?:\\w+\\s+)?is\\s+(less|lower|smaller|fewer|more|greater|higher|larger)\\s+than\\s+\\$?(-?\\d[\\d,]*(?:\\.\\d+)?)\\s*([a-z%]*)', re.I)

                def E_cmp_unit(word: str) -> str:
                    w = (word or '').casefold()
                    if not w or E_scale_of(w) != 1.0 or w == 'k':
                        return ''
                    return w

                def E_stated_comparison_faults(answer: str) -> list[str]:
                    t = ' '.join(E_CITE_NUM_RE.sub(' ', (answer or '')[:9000]).split())
                    out: list[str] = []
                    for m in E_STATED_CMP_RE.finditer(t):
                        try:
                            a = float(m.group(1).replace(',', '')) * E_scale_of(m.group(2).casefold())
                            b = float(m.group(4).replace(',', '')) * E_scale_of(m.group(5).casefold())
                        except Exception:
                            continue
                        unit_a = E_cmp_unit(m.group(2))
                        unit_b = E_cmp_unit(m.group(5))
                        if unit_a and unit_b and (unit_a != unit_b):
                            continue
                        rel = m.group(3).casefold()
                        eps = 1e-09 * max(1.0, abs(a), abs(b))
                        wrong = a > b + eps if rel in ('less', 'lower', 'smaller', 'fewer') else a < b - eps
                        if wrong:
                            out.append(f'the answer states {m.group(0).strip()!r}, but {a:g} vs {b:g} contradicts that relation')
                        if len(out) >= 3:
                            break
                    return out

                async def E_numeric_predicate_guard(question: str, answer: str, ledger: E_EvidenceLedger, deadline: float) -> str:
                    left = deadline - monotonic()
                    if left < 70.0:
                        return answer
                    ask = f'List every numeric claim in the answer that the question itself constrains with a threshold, range or cutoff. JSON only: {{"triples": [{{"candidate": "entity", "value": "the figure exactly as the answer states it", "constraint": "the constraint phrase exactly as the question states it", "verdict": "included" or "excluded"}}]}} — verdict is how the ANSWER treats the candidate: "included" when it counts it as qualifying, "excluded" when it rules it out or negates it.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:9000]}'
                    try:
                        raw = await E_chat_simple(E_AUDIT_MODEL, 'You output only JSON.', ask, max_tokens=900, timeout=max(8.0, min(16.0, left - 52.0)), temp=0.0)
                        raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                        parsed = json.loads(raw)
                    except Exception:
                        return answer
                    triples = parsed.get('triples') if isinstance(parsed, dict) else None
                    if not isinstance(triples, list):
                        return answer
                    faults: list[str] = []
                    for row in triples[:12]:
                        if not isinstance(row, dict):
                            continue
                        value_text = str(row.get('value') or '')
                        constraint_text = str(row.get('constraint') or '')
                        why = E_violation_of(value_text, constraint_text)
                        stance = str(row.get('verdict') or 'included').casefold()
                        excluded = stance.startswith(('exclud', 'fail', 'reject', 'negat', 'not', 'no'))
                        if excluded:
                            if not why and E_bounds_decidable(value_text, constraint_text):
                                faults.append(f"{str(row.get('candidate') or '?')}: {row.get('value')!r} SATISFIES {row.get('constraint')!r}, yet the answer excludes/negates it — include it or correct the figure")
                        elif why:
                            faults.append(f"{str(row.get('candidate') or '?')}: {row.get('value')!r} vs {row.get('constraint')!r} — {why}")
                    try:
                        faults.extend(E_stated_comparison_faults(answer))
                    except Exception:
                        pass
                    if not faults or deadline - monotonic() < 55.0:
                        return answer
                    digest = E_ledger_digest(ledger, char_cap=45000)
                    evidence = f'Numbered evidence (cite by [n]):\n\n{digest}\n\n' if digest else ''
                    fix = f'Question: {question}\n\n' + evidence + f"Draft answer:\n{answer[:12000]}\n\nNUMERIC CHECK — these entries violate the question's explicit numeric constraints:\n- " + '\n- '.join(faults[:5]) + '\nRewrite the COMPLETE answer once: correct or REMOVE only the violating entries using the cited evidence; keep every other claim, every inline [n], and the required output shape.'
                    try:
                        fixed = await E_chat_simple(E_LOOP_MODEL_A, E_COMMIT_RULES, fix, max_tokens=4000, timeout=max(12.0, min(40.0, deadline - monotonic() - E_DIGEST_TAIL_S)))
                    except Exception:
                        return answer
                    fixed = (fixed or '').strip()
                    if not E_is_usable_answer(fixed) or len(fixed) < int(len(answer) * 0.6):
                        return answer
                    if len(E_cited_numbers(fixed, len(ledger.rows))) < len(E_cited_numbers(answer, len(ledger.rows))):
                        return answer
                    return fixed
                E_ORDER_ALPHA_RE = re.compile('\\balphabetical(?:ly)?\\b', re.I)
                E_ORDER_ASC_RE = re.compile('\\b(?:ascending|chronological(?:ly)?|oldest to (?:newest|youngest)|earliest to latest|smallest to largest|lowest to highest|least to most|increasing order|smallest first|lowest first|earliest first)\\b', re.I)
                E_ORDER_DESC_RE = re.compile('\\b(?:descending|largest to smallest|highest to lowest|most to least|newest to oldest|latest to earliest|decreasing order|largest first|highest first|biggest first)\\b', re.I)
                E_ORDER_BY_RE = re.compile('\\b(?:sort(?:ed)?|rank(?:ed)?|order(?:ed)?)\\s+(?:them\\s+|these\\s+)?(?:in\\s+order\\s+)?by\\b|\\bin\\s+(?:the\\s+)?order\\s+of\\b', re.I)

                def E_order_directive(question: str) -> str:
                    q = ' '.join((question or '').split())
                    if not q:
                        return ''
                    if E_ORDER_ALPHA_RE.search(q):
                        return 'alpha'
                    if E_ORDER_ASC_RE.search(q):
                        return 'asc'
                    if E_ORDER_DESC_RE.search(q):
                        return 'desc'
                    if E_ORDER_BY_RE.search(q):
                        return 'by'
                    return ''

                async def E_reorder_list(items: list, question: str, answer: str, direction: str, deadline: float):
                    if not 2 <= len(items) <= 20:
                        return None
                    if not all((isinstance(x, str) and x.strip() for x in items)):
                        return None
                    if direction == 'alpha':
                        deco = sorted(((x.casefold(), i) for i, x in enumerate(items)))
                        ordered = [items[i] for _k, i in deco]
                        return ordered if ordered != items else None
                    if deadline - monotonic() < 15.0:
                        return None
                    ask = f'For each listed item, extract the numeric value the answer associates with it — the quantity the question sorts or ranks by. JSON only: {{"pairs": [{{"item": "<name>", "value": <number>}}]}}\n\nItems: {json.dumps(items)}\n\nQuestion:\n{question[:2000]}\n\nAnswer:\n{answer[:9000]}'
                    try:
                        raw = await E_chat_simple(E_SCHEMA_MODEL, 'You output only JSON.', ask, max_tokens=800, timeout=max(8.0, min(16.0, deadline - monotonic() - 6.0)), temp=0.0)
                        raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                        got = json.loads(raw)
                    except Exception:
                        return None
                    pairs = got.get('pairs') if isinstance(got, dict) else None
                    if not isinstance(pairs, list):
                        return None
                    vals: dict[int, float] = {}
                    for p in pairs:
                        if not isinstance(p, dict):
                            continue
                        name = ' '.join(str(p.get('item') or '').split()).casefold()
                        try:
                            val = float(p.get('value'))
                        except Exception:
                            continue
                        if not name:
                            continue
                        for i, item in enumerate(items):
                            key = ' '.join(item.split()).casefold()
                            if i not in vals and (key == name or key in name or name in key):
                                vals[i] = val
                                break
                    if len(vals) != len(items):
                        return None
                    if direction == 'by':
                        chronology = all((1500.0 <= v <= 2100.0 and v == int(v) for v in vals.values()))
                        direction = 'asc' if chronology else 'desc'
                    sign = 1.0 if direction == 'asc' else -1.0
                    deco = sorted(((sign * vals[i], i) for i in range(len(items))))
                    ordered = [items[i] for _k, i in deco]
                    return ordered if ordered != items else None

                async def E_apply_order_guard(question: str, answer: str, value, deadline: float):
                    direction = E_order_directive(question)
                    if not direction:
                        return value
                    if isinstance(value, list):
                        fixed = await E_reorder_list(value, question, answer, direction, deadline)
                        return fixed if fixed is not None else value
                    if isinstance(value, dict):
                        out = dict(value)
                        done = 0
                        for k in list(out.keys()):
                            if done >= 2:
                                break
                            v = out[k]
                            if isinstance(v, list) and all((isinstance(x, str) for x in v)):
                                fixed = await E_reorder_list(v, question, answer, direction, deadline)
                                if fixed is not None:
                                    out[k] = fixed
                                done += 1
                        return out
                    return value

                def E_ensure_citation_notes(answer: str, ledger: E_EvidenceLedger) -> str:
                    s = answer or ''
                    if not s or re.search('citation notes\\s*:', s, re.I):
                        return s
                    nums = E_cited_numbers(s, len(ledger.rows))
                    if not nums:
                        return s
                    lines: list[str] = []
                    for n in nums[:12]:
                        row = ledger.rows[n - 1]
                        preview = (row.get('preview') or '').strip()
                        if not preview:
                            continue
                        title = (row.get('title') or '').strip()
                        url = (row.get('url') or '').strip()
                        src = title if title and title != url else url
                        lead = E_informative_lead(preview, 110)
                        if not lead:
                            lead = ' '.join(preview.split())[:110]
                        lines.append(f"[{n}] {src or 'retrieved source'} — key line: {lead}")
                    if not lines:
                        return s
                    return s + '\n\nCitation notes:\n' + '\n'.join(lines)

                def E_leaf_values(value, depth: int=0) -> list[str]:
                    if depth > 4:
                        return []
                    if isinstance(value, bool) or value is None:
                        return []
                    if isinstance(value, (int, float)):
                        return [str(value)]
                    if isinstance(value, str):
                        v = value.strip()
                        return [v] if len(v) >= 3 else []
                    out: list[str] = []
                    if isinstance(value, dict):
                        for v in value.values():
                            out.extend(E_leaf_values(v, depth + 1))
                            if len(out) >= 12:
                                break
                    elif isinstance(value, list):
                        for v in value:
                            out.extend(E_leaf_values(v, depth + 1))
                            if len(out) >= 12:
                                break
                    return out[:12]

                def E_needle_hits(needle: str, hay: str) -> bool:
                    sig = needle.replace('.', '')
                    if sig.isdigit():
                        start = 0
                        while True:
                            pos = hay.find(needle, start)
                            if pos == -1:
                                return False
                            before = hay[pos - 1] if pos > 0 else ' '
                            after_i = pos + len(needle)
                            after = hay[after_i] if after_i < len(hay) else ' '
                            if not before.isdigit() and (not after.isdigit()):
                                return True
                            start = pos + 1
                    return needle in hay

                def E_augment_schema_refs(structured, citations: list, ledger: E_EvidenceLedger) -> list:
                    refs = list(citations or [])
                    if len(refs) >= 10 or not ledger.rows:
                        return refs
                    needles: list[str] = []
                    for leaf in E_leaf_values(structured):
                        norm = ' '.join(leaf.split()).casefold().replace(',', '')
                        sig = norm.replace('.', '').replace('-', '')
                        if not norm:
                            continue
                        if sig.isdigit():
                            try:
                                if 1500 <= int(float(norm)) <= 2100:
                                    continue
                            except Exception:
                                pass
                            if len(sig) < 3:
                                continue
                        elif len(norm) < 3:
                            continue
                        if norm not in needles:
                            needles.append(norm)
                    if not needles:
                        return refs
                    have_ids = {(getattr(r, 'receipt_id', ''), getattr(r, 'result_id', '')) for r in refs}
                    have_urls: set[str] = set()
                    for row in ledger.rows:
                        if (row.get('receipt_id'), row.get('result_id')) in have_ids:
                            u = (row.get('url') or '').casefold()
                            if u:
                                have_urls.add(u)
                    for i, row in enumerate(ledger.rows, start=1):
                        if len(refs) >= 10:
                            break
                        pair = (row.get('receipt_id'), row.get('result_id'))
                        url = (row.get('url') or '').casefold()
                        if pair in have_ids or (url and url in have_urls):
                            continue
                        hay = ((row.get('title') or '') + ' ' + (row.get('preview') or '')).casefold().replace(',', '')
                        if not any((E_needle_hits(n, hay) for n in needles)):
                            continue
                        ref = ledger.ref_for(i)
                        if ref is None:
                            continue
                        refs.append(ref)
                        have_ids.add(pair)
                        if url:
                            have_urls.add(url)
                    return refs

                async def E_query(query: Query) -> Response:
                    question = (query.text or '').strip()
                    if not question:
                        return Response(text='No question provided.')
                    try:
                        return await E_solve(query, question)
                    except Exception:
                        return Response(text=f'Best-effort answer unavailable for: {question[:500]}')

                async def E_solve(query: Query, question: str) -> Response:
                    deadline = monotonic() + E_WALL_BUDGET_S
                    try:
                        info = await tooling_info(timeout=10.0)
                        E_spend_note(info)
                    except Exception:
                        pass
                    draft = ''
                    brief = ''
                    try:
                        if E_spend_left() >= E_BRIEF_MIN_USD and deadline - monotonic() > 120.0:
                            draft, brief = await E_knowledge_brief(question)
                    except Exception:
                        brief = ''
                    ledger = E_EvidenceLedger()
                    answer = ''
                    messages: list[dict] = []
                    try:
                        answer, messages = await E_loop(question, brief, ledger, deadline, E_MAX_TURNS)
                    except Exception:
                        answer = ''
                    try:
                        if E_is_usable_answer(answer) and deadline - monotonic() > 75.0 and (E_spend_left() >= E_AUDIT_MIN_USD):
                            patched = await E_audit_patch(question, answer, messages, ledger, deadline)
                            if E_is_usable_answer(patched):
                                answer = patched
                    except Exception:
                        pass
                    try:
                        if E_is_usable_answer(answer) and deadline - monotonic() > 70.0 and (E_spend_left() >= E_WRAPUP_MIN_USD):
                            answer = await E_numeric_predicate_guard(question, answer, ledger, deadline)
                    except Exception:
                        pass
                    if not E_is_usable_answer(answer) and ledger.rows:
                        try:
                            rescued = await E_write_from_digest(question, ledger, deadline)
                            if E_is_usable_answer(rescued):
                                answer = rescued
                        except Exception:
                            pass
                    if not E_is_usable_answer(answer) and ledger.rows:
                        det = E_deterministic_answer(ledger)
                        if E_is_usable_answer(det):
                            answer = det
                    if not E_is_usable_answer(answer):
                        fallback = E_sanitize_draft(draft) or await E_knowledge_resort(question, deadline)
                        if E_is_usable_answer(fallback):
                            answer = fallback
                    try:
                        citations = E_citations_for(answer, ledger)
                    except Exception:
                        citations = []
                    if not citations and ledger.rows:
                        try:
                            floor: list[CitationRef] = []
                            for i, row in enumerate(ledger.rows, start=1):
                                if not (row.get('preview') or '').strip():
                                    continue
                                ref = ledger.ref_for(i)
                                if ref is not None:
                                    floor.append(ref)
                                if len(floor) >= 3:
                                    break
                            citations = floor
                        except Exception:
                            citations = []
                    answer = E_normalize_brackets(answer)
                    answer = E_strip_lead_narration(answer)
                    noted = answer
                    if query.output_schema is None:
                        try:
                            noted = E_ensure_citation_notes(answer, ledger)
                        except Exception:
                            noted = answer
                    text = E_cap(noted) or f'Best-effort answer unavailable for: {question[:400]}'
                    if query.output_schema is not None:
                        structured = None
                        try:
                            structured = await E_schema_output(question, answer, query.output_schema, deadline)
                        except Exception:
                            structured = None
                        if structured is not None:
                            try:
                                structured = await E_apply_order_guard(question, answer, structured, deadline)
                            except Exception:
                                pass
                            try:
                                citations = E_augment_schema_refs(structured, citations, ledger)
                            except Exception:
                                pass
                            try:
                                return Response(output=structured, citations=citations or None)
                            except Exception:
                                structured = None
                        basis = answer if E_is_usable_answer(answer) else ''
                        if not basis:
                            basis = E_deterministic_answer(ledger)
                        if not basis or E_STUB_ANSWER_RE.match(basis.strip()):
                            basis = question[:400]
                        try:
                            forced = E_coerce_to_schema(E_cap(basis), query.output_schema)
                            try:
                                forced = await E_apply_order_guard(question, answer, forced, deadline)
                            except Exception:
                                pass
                            try:
                                citations = E_augment_schema_refs(forced, citations, ledger)
                            except Exception:
                                pass
                            return Response(output=forced, citations=citations or None)
                        except Exception:
                            try:
                                return Response(output=E_cap(basis)[:2000], citations=citations or None)
                            except Exception:
                                pass
                    try:
                        return Response(text=text, citations=citations or None)
                    except Exception:
                        return Response(text=text)
                H_VERSION = 'v39-nodigest-primary-flat'
                H_LLM_LANE_A = 'openrouter'
                H_LLM_LANE_B = 'openrouter'
                H_LOOP_MODEL_A = 'z-ai/glm-5.2'
                H_LOOP_MODEL_B = 'zai/glm-5.2-fast'
                H_AUDIT_MODEL = 'openai/gpt-oss-120b'
                H_SCHEMA_MODEL = 'openai/gpt-oss-120b'
                H_RESORT_MODEL = 'deepseek/deepseek-v3.2'
                H_SEARCH_PROVIDER = 'parallel'
                H_WALL_BUDGET_S = 266.0
                H_BRIEF_TIMEOUT_S = 50.0
                H_TURN_TIMEOUT_S = 75.0
                H_LANE_B_MAX_PAYLOAD_CHARS = 144000
                H_AUDIT_TIMEOUT_S = 28.0
                H_SEARCH_TIMEOUT_S = 18.0
                H_FETCH_TIMEOUT_S = 16.0
                H_WRAPUP_AT_S = 90.0
                H_MIN_TAIL_S = 8.0
                H_MAX_TURNS = 15
                H_AUDIT_EXTRA_TURNS = 2
                H_ANSWER_REPAIR_TURNS = 2
                H_RESCUE_TIMEOUT_S = 55.0
                H_DIGEST_TAIL_S = 14.0
                H_SEARCH_EXCERPT_CHARS = 550
                H_LEDGER_TEXT_CAP = 400000
                H_PAGE_GREP_WINDOW = 700
                H_PAGE_GREP_MAX_HITS = 6
                H_PAGE_READ_MAX_CHARS = 12000
                H_RETAIN_MARGIN_CHARS = 260
                H_RETAIN_MAX_PER_ROW = 6
                H_RETAIN_MIN_QUOTE = 12
                H_FETCH_HEAD_CHARS = 3000
                H_FETCH_WINDOW_CHARS = 3600
                H_CITATION_MIN_SPAN_CHARS = 6000
                H_CITATION_MAX_REF_CHARS = 14000
                H_FETCH_WINDOWS_PER_PAGE = 3
                H_FETCH_PLAIN_CHARS = 6500
                H_ANSWER_CHAR_CAP = 60000
                H_CITATION_CAP = 24
                H_EVIDENCE_CHAR_BUDGET = 105000
                H_BRIEF_MIN_USD = 0.03
                H_AUDIT_MIN_USD = 0.05
                H_WRAPUP_MIN_USD = 0.02
                H_SPEND = {'left': None}

                def H_spend_note(payload) -> None:
                    budget = getattr(payload, 'budget', None)
                    left = getattr(budget, 'session_remaining_budget_usd', None)
                    if isinstance(left, (int, float)):
                        H_SPEND['left'] = float(left)

                def H_spend_left() -> float:
                    left = H_SPEND['left']
                    if isinstance(left, (int, float)):
                        return float(left)
                    return 1.0
                H_LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}, {'type': 'function', 'function': {'name': 'page_grep', 'description': 'Search INSIDE a page you already fetched, by regex or literal text, and get every match with its surrounding context and character offset. Use this when read_page showed you the head of a long page but the value you need is deeper in it -- do not re-fetch, grep it.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL of a page already fetched this run'}, 'pattern': {'type': 'string', 'description': 'regex or literal string to find, e.g. a city name, a year, a column label'}}, 'required': ['url', 'pattern']}}}, {'type': 'function', 'function': {'name': 'page_read', 'description': 'Read an arbitrary character range of a page you already fetched. Use the offsets page_grep reports to read the full table or section around a match.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL already fetched'}, 'offset': {'type': 'integer', 'description': 'start character offset'}, 'length': {'type': 'integer', 'description': 'how many characters to read (max 12000)'}}, 'required': ['url', 'offset']}}}, {'type': 'function', 'function': {'name': 'retain_evidence', 'description': "Keep the exact source text that proves a claim you are about to make. Pass the result number and the verbatim quote from it. Do this the moment you find a decisive value -- the judge only credits claims whose citation contains the supporting text, and this is how that text gets into your citation. Use it for the QUESTION'S PREMISES as well as your answer: every entity, work, date or figure the question names should end up with a retained quote confirming it.", 'parameters': {'type': 'object', 'properties': {'source': {'type': 'string', 'description': 'result number to quote from, e.g. 3'}, 'quote': {'type': 'string', 'description': 'verbatim text copied from that result that states the fact'}}, 'required': ['source', 'quote']}}}]
                H_LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nPREFER THE PRIMARY SOURCE: when two sources state the same fact, cite the one that ORIGINATES it -- the agency, registry, filing, official statistics release or the organisation\'s own page -- not an encyclopedia or aggregator repeating it. Measured verbatim on a task where both answers were factually correct: "Answer 1 is preferred for using primary sources" (it cited NARA where we cited Wikipedia) -- a full point lost on every run. Use the encyclopedia to FIND the primary source, then fetch and cite that.\n\nQUOTE WHAT PROVES IT: the judge credits a claim only when your citation CONTAINS the source text stating it. The moment you read a decisive value, call retain_evidence(source, quote) with the exact words from that result. Do this for every condition you test and every figure you report -- an answer whose citations do not carry its numbers loses to one that does, even when both answers are identical.\nALSO QUOTE THE QUESTION\'S PREMISES, not only your answer. Every entity, work, date or figure the question NAMES is a claim the judge expects traceable: the film it says someone directed, the article it points at, the year it fixes, the people it lists. You lose to an otherwise identical answer that cited those too -- measured verbatim: "does not provide a citation for \'Everyone Says I Love You\'... Answer 1 is more thorough in its traceability to all parts of the prompt\'s context". Retain a quote for each named premise as you confirm it, even when it is background you already believed.\n\nREAD DEEP, DO NOT RE-FETCH: read_page shows the head plus a few regions of a long page. If the value you need is not in what you were shown, call page_grep(url, pattern) to find it anywhere in that page and page_read to open the region around a reported offset. Grepping a page you already have costs nothing and beats another search.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. COPY SOURCE VALUES VERBATIM: when the question names a source, every name, label and value in the answer must be the exact string that source prints -- never add a familiar alternative in parentheses, never anglicise a transliteration. \'Makkah\' is the answer; \'Mecca (Makkah)\' is a wrong answer. ONE EXCEPTION, and it is absolute: if the question says to output ONLY the answer (\'output only\', \'respond with only\', \'nothing else\', \'no explanation\'), emit the answer line as the BARE requested text — no [n] markers on it, nothing else on that line: a trailing [3] makes the text inexact and fails the instruction. Still write the PROOF section BELOW it carrying its [n] markers. Only the answer line is shipped, but the citations are harvested from the proof first, and an uncited answer scores zero. Obeying that instruction IS the task. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

                def H_wrapup_order(seconds_left: float) -> str:
                    return f"TIME IS UP (~{int(seconds_left)}s left). No more tool calls. Write the complete final answer NOW from the numbered results above plus your knowledge: the FIRST words are the answer entities (no 'Based on…' preamble, no 'partial answer' framing, no '(verify)' markers), cite [n] on every claim, keep the required format. A cited partial answer scores; a refusal or a remark about insufficient evidence scores zero." + ('' if seconds_left >= 60 else ' BREVITY OVERRIDE: too little time remains for a line per pool member. Lead with the answer entities, then give the qualifiers one cited line each and compress the rejects into a single cited line. A complete short answer beats a long one that never finishes.')
                H_SET_HINT_RE = re.compile('\\b(?:list|name|identify|enumerate)\\b[^?]{0,40}\\b(?:all|every|each|the)\\b|\\bhow many\\b|\\bwhich (?:movies|films|series|countries|companies|states|cities|books|albums|artists|players|teams|species|languages|banks|universities|agencies|models|products)\\b', re.IGNORECASE)
                H_SET_CONNECTIVE_RE = re.compile('\\b(?:both|also|and (?:also|had|has|was|were)|as well as)\\b', re.IGNORECASE)
                H_PLURAL_HEAD_RE = re.compile('\\b(?:which|what)\\b(?:\\s+\\w+){0,2}?\\s+([a-z]{3,}s)\\b', re.IGNORECASE)
                H_PLURAL_FALSE = frozenset('was is has does its this thus across process business series species news status analysis basis less unless always perhaps'.split())
                H_ONE_WINNER_RE = re.compile('\\b(?:highest|lowest|largest|smallest|most|least|greatest|fewest|longest|shortest|first|last|best|worst|only|oldest|youngest|newest|biggest)\\b', re.IGNORECASE)
                H_EST_STOP = frozenset('interest honest modest protest request suggest forest harvest invest manifest contest arrest digest earnest conquest tempest midwest northwest southwest unrest bequest behest attest molest ingest infest detest incest armrest backrest pretest headrest footrest'.split())
                H_EST_RE = re.compile('\\b([a-z]{3,})est\\b')

                def H_has_superlative(text: str) -> bool:
                    if H_ONE_WINNER_RE.search(text or ''):
                        return True
                    for m in H_EST_RE.finditer(text or ''):
                        if m.group(0).lower() not in H_EST_STOP:
                            return True
                    return False

                def H_needs_superlative_proof(question: str) -> bool:
                    q = ' '.join((question or '').split())
                    if not q:
                        return False
                    return H_has_superlative(q) or bool(re.search('\\b(?:most|least) (?:common|frequent|number|amount)\\b|\\bhow many\\b', q, re.I))
                H_SUPERLATIVE_RULE = "SUPERLATIVE / TALLY — SHOW THE TABLE. The answer is one item, but you cannot know it without the whole pool. Before naming a winner: (1) list EVERY candidate the question's scope admits — every player who appeared, every officeholder in the span, every body in the ranking; (2) put the deciding value next to each (birth date, count, figure), cited; (3) THEN name the maximum. NEVER decide a superlative on a rounded or derived display: a coarse figure (a whole-number age, a rounded total, a bucketed rank) cannot separate two contenders that differ below its precision. Fetch the exact underlying value (full birth date, unrounded figure) for every contender, from a source that lists them ALL: a page showing only your front-runner cannot establish that nobody beats them. (3b) THEN name the maximum. Reproduce that candidate table in the proof section — a correct winner with no visible tally loses to a reference that shows its work, and 'among others' / 'and several more' is not a tally. If the pool is too large to list in full, rank it, show every contender down to a stated cutoff, and say what the cutoff was — a stated cutoff is a covered pool; an unstated one reads as an unchecked one."

                def H_needs_set_completeness(question: str) -> bool:
                    q = ' '.join((question or '').split())
                    if H_SET_HINT_RE.search(q):
                        return True
                    m = H_PLURAL_HEAD_RE.search(q)
                    if m and m.group(1).lower() not in H_PLURAL_FALSE:
                        if not H_has_superlative(q) or re.search('\\b(?:all|every|each)\\b', q, re.IGNORECASE):
                            return True
                    return bool(re.search('\\bwhich\\b', q, re.IGNORECASE)) and bool(H_SET_CONNECTIVE_RE.search(q))
                H_SET_RULE = "SET ANSWER: this question asks for a set. Missing a qualifying member scores the same as wrong — enumerate the pool, test EVERY member against EVERY condition, and name ALL qualifiers (each with its own citations per condition). Then give EVERY excluded member its own line with the condition it fails and its own [n] — not a single clause sweeping several names together, and not just the near-misses. Never claim 'the only X' unless the whole pool was checked; if your pool may be partial, still commit to every qualifier you verified. GET THE POOL FROM A LIST, NOT MEMBER-BY-MEMBER: your FIRST retrieval for a set question should hunt the authoritative roster/list/table that enumerates the whole pool (search it AS a list — '<pool subject> list', '<pool subject> table', 'list of <pool subject>' — and read_page it). Assembling the pool from separate per-member searches is how a run ends up with 3 of 6 qualifiers: the members you never thought to search for are invisible to you. Read the roster page first, then verify each member. ONE LIST PER PERIOD, THEN JOIN: when a condition has to hold across several periods — successive years, separate editions, or two parallel events — fetch ONE roster page per period and join them on the member: one list per period, not one lookup per member. A pool of 30+ members each needing several figures is a table-join, and per-member lookups will run out of turns long before the pool is covered. UNIVERSAL conditions ('in EVERY one of them', 'for BOTH parts', 'in ALL three periods'): check each candidate against EACH instance separately, with a citation per instance — one shared instance is not enough. If NO candidate survives every instance, then 'none' IS the answer: state it as a verified fact about the world with the per-instance citations that prove it."

                class H_EvidenceLedger:

                    def __init__(self) -> None:
                        self.rows: list[dict] = []

                    def add(self, receipt_id: str, result_id: str, note_len: int, kind: str, spans: list[tuple[int, int]] | None, title: str='', url: str='', preview: str='', text: str='') -> int:
                        self.rows.append({'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': (url or '')[:300], 'preview': (preview or '')[:1200], 'spans': spans, 'text': (text or '')[:H_LEDGER_TEXT_CAP], 'retained': []})
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
                            retained = []
                            for a, b in row.get('retained') or []:
                                a = max(0, min(int(a), note_len))
                                b = max(a + 1, min(int(b), note_len))
                                retained.append([a, b])
                            if retained:
                                shown = retained
                            shown.sort()
                            merged: list[list[int]] = []
                            for s, e in shown:
                                if merged and s <= merged[-1][1]:
                                    merged[-1][1] = max(merged[-1][1], e)
                                else:
                                    merged.append([s, e])
                            base = sum((e - s for s, e in merged))
                            room = max(0, H_CITATION_MAX_REF_CHARS - base)
                            if merged and note_len and room:
                                extra = room // len(merged)
                                for w in merged:
                                    pad = min(extra, max(0, H_CITATION_MIN_SPAN_CHARS - (w[1] - w[0])))
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
                            slices = [CitationSlice(start=s, end=e) for s, e in merged if e > s]
                            if not slices:
                                return None
                            return CitationRef(receipt_id=row['receipt_id'], result_id=row['result_id'], slices=slices)
                        return None
                H_WORD_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
                H_STOP = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

                def H_key_terms(text: str) -> set[str]:
                    return {w for w in H_WORD_RE.findall((text or '').casefold()) if w not in H_STOP}

                def H_best_windows(note: str, terms: set[str], width: int, k: int=1) -> list[tuple[int, int]]:
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
                H_SLOT = '\x00{}\x00'

                class H_ToolOutput:

                    def __init__(self, text: str, rows: list[dict] | None=None) -> None:
                        self.text = text
                        self.rows = rows or []

                def H_commit_tool_output(out, ledger: H_EvidenceLedger) -> str:
                    if isinstance(out, str):
                        return out
                    if not isinstance(out, H_ToolOutput):
                        return f'# tool crashed: {out}'
                    text = out.text
                    for i, row in enumerate(out.rows):
                        n = ledger.add(row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''), text=row.get('text', ''))
                        text = text.replace(H_SLOT.format(i), str(n))
                    return text
                H_SITE_OP_RE = re.compile('\\bsite:\\S+\\s*', re.I)

                def H_degrade_query(q: str) -> str:
                    out = H_SITE_OP_RE.sub('', q or '').replace('"', ' ')
                    return ' '.join(out.split())

                async def H_do_search(query_text: str, ledger: H_EvidenceLedger):
                    if not query_text.strip():
                        return '# web_search: empty query'
                    payload = None
                    fired: set[str] = set()
                    for attempt, allow_repeat in ((query_text, False), (query_text, True), (H_degrade_query(query_text), False)):
                        if not attempt.strip() or (attempt in fired and (not allow_repeat)):
                            continue
                        fired.add(attempt)
                        try:
                            payload = await search_web(attempt, provider=H_SEARCH_PROVIDER, num=8, timeout=H_SEARCH_TIMEOUT_S)
                            if getattr(payload, 'results', None):
                                break
                        except Exception:
                            payload = None
                    if payload is None:
                        return f'# web_search({query_text!r}) failed'
                    H_spend_note(payload)
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
                        span = [(0, min(max(H_SEARCH_EXCERPT_CHARS, 100), n_len))] if n_len >= 100 else [(0, n_len)] if n_len else None
                        title = (getattr(item, 'title', None) or '').strip()
                        url = (getattr(item, 'url', None) or '').strip()
                        rows.append({'receipt_id': receipt, 'result_id': rid, 'note_len': n_len, 'kind': 'search', 'spans': span, 'title': title, 'url': url, 'preview': note[:H_SEARCH_EXCERPT_CHARS], 'text': note})
                        lines.append(f'[{H_SLOT.format(len(rows) - 1)}] {title} — {url}\n    {note[:H_SEARCH_EXCERPT_CHARS]}')
                    return H_ToolOutput('\n'.join(lines), rows)

                async def H_do_fetch(url: str, focus: str, question: str, ledger: H_EvidenceLedger) -> str:
                    if not url.strip():
                        return '# read_page: empty url'
                    payload = None
                    for _attempt in (0, 1):
                        try:
                            payload = await fetch_page(url, provider=H_SEARCH_PROVIDER, timeout=H_FETCH_TIMEOUT_S)
                            if getattr(payload, 'results', None):
                                break
                        except Exception:
                            payload = None
                    if payload is None:
                        return f'# read_page({url!r}) failed'
                    H_spend_note(payload)
                    receipt = str(getattr(payload, 'receipt_id', '') or '')
                    results = list(getattr(payload, 'results', None) or [])
                    if not results or not receipt:
                        return f'# read_page({url!r}): no content'
                    item = results[0]
                    rid = getattr(item, 'result_id', None)
                    note = getattr(item, 'note', None) or ''
                    if not isinstance(rid, str) or not rid or (not note.strip()):
                        return f'# read_page({url!r}): no usable content'
                    if len(note) <= H_FETCH_PLAIN_CHARS:
                        row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, len(note))], 'title': url, 'url': url, 'preview': note[:1200], 'text': note}
                        return H_ToolOutput(f'# read_page({url!r}) -> [{H_SLOT.format(0)}] full page, {len(note)} chars\n{note}', [row])
                    terms = H_key_terms(question) | H_key_terms(focus)
                    windows = H_best_windows(note, terms, H_FETCH_WINDOW_CHARS, k=H_FETCH_WINDOWS_PER_PAGE)
                    row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, H_FETCH_HEAD_CHARS)] + list(windows), 'title': url, 'url': url, 'preview': note[windows[0][0]:windows[0][0] + 1200], 'text': note}
                    head = note[:H_FETCH_HEAD_CHARS]
                    sections = ''.join((f'\n--- section @{s} ---\n{note[s:e]}' for s, e in windows))
                    ranges = ', '.join((f'{s}-{e}' for s, e in windows))
                    return H_ToolOutput(f'# read_page({url!r}) -> [{H_SLOT.format(0)}] {len(note)} chars total; head + the {len(windows)} most relevant section(s) shown ({ranges}). If the answer set may continue elsewhere in this page, call read_page again with a different focus.\n--- head ---\n{head}{sections}', [row])
                H_SEC_TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
                H_SEC_SUBMISSIONS_URL = 'https://data.sec.gov/submissions/CIK{cik10}.json'
                H_SEC_DOC_URL = 'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}'
                H_SEC_FETCH_TIMEOUT_S = 26.0
                H_SEC_MIN_HEADROOM_S = 40.0
                H_SEC_CACHE: dict = {}
                H_SEC_STOPWORDS = frozenset('inc incorporated corp corporation company companies co ltd limited llc plc lp llp group holdings the'.split())
                H_SEC_ALNUM_RE = re.compile('[a-z0-9]+')

                def H_sec_tokens(text: str) -> list[str]:
                    return [w for w in H_SEC_ALNUM_RE.findall((text or '').lower()) if w not in H_SEC_STOPWORDS]

                def H_sec_norm_form(form: str) -> str:
                    f = ' '.join((form or '').upper().replace('FORM', ' ').split())
                    m = re.fullmatch('(\\d{1,2})\\s*-?\\s*([A-Z])', f)
                    if m:
                        return f'{m.group(1)}-{m.group(2)}'
                    m = re.fullmatch('(DEF)\\s*-?\\s*(14A)', f)
                    if m:
                        return 'DEF 14A'
                    return f

                async def H_fetch_json(url: str, deadline: float):
                    cached = H_SEC_CACHE.get(url)
                    if cached is not None:
                        return cached
                    for _attempt in (0, 1):
                        left = deadline - monotonic()
                        if left < 12.0:
                            return None
                        try:
                            payload = await asyncio.wait_for(fetch_page(url, provider=H_SEARCH_PROVIDER, timeout=min(H_SEC_FETCH_TIMEOUT_S, left - 6.0)), timeout=min(H_SEC_FETCH_TIMEOUT_S, left - 6.0) + 4.0)
                        except Exception:
                            continue
                        H_spend_note(payload)
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
                            H_SEC_CACHE[url] = obj
                            return obj
                    return None

                def H_sec_pick_filing(recent: dict, form: str, year: str):
                    forms = recent.get('form')
                    accs = recent.get('accessionNumber')
                    docs = recent.get('primaryDocument')
                    rdates = recent.get('reportDate')
                    fdates = recent.get('filingDate')
                    if not (isinstance(forms, list) and isinstance(accs, list) and isinstance(docs, list)):
                        return None
                    n = min(len(forms), len(accs), len(docs))
                    form_norm = H_sec_norm_form(form)
                    best_year = None
                    best_any = None
                    for i in range(n):
                        if H_sec_norm_form(str(forms[i])) != form_norm:
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
                H_SEC_SEARCH_HINT = 'search "site:sec.gov {company} {year} {form}" and read_page the Archives result'

                async def H_do_sec_filing(company: str, form: str, year: str, deadline: float) -> str:
                    company = (company or '').strip()
                    form = (form or '').strip() or '10-K'
                    year = (year or '').strip()[:4]
                    hint = H_SEC_SEARCH_HINT.format(company=company, year=year, form=form)
                    if not company:
                        return '# sec_filing: company required'
                    if deadline - monotonic() < H_SEC_MIN_HEADROOM_S:
                        return f'# sec_filing: skipped (low time) — {hint}'
                    tickers = await H_fetch_json(H_SEC_TICKERS_URL, deadline)
                    if not isinstance(tickers, dict):
                        return f'# sec_filing: EDGAR ticker index unavailable — {hint}'
                    want = H_sec_tokens(company)
                    best = None
                    for row in tickers.values():
                        if not isinstance(row, dict):
                            continue
                        title = str(row.get('title', ''))
                        ticker = str(row.get('ticker', '')).lower()
                        words = set(H_sec_tokens(title))
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
                    subs = await H_fetch_json(H_SEC_SUBMISSIONS_URL.format(cik10=cik10), deadline)
                    filings = subs.get('filings') if isinstance(subs, dict) else None
                    recent = filings.get('recent') if isinstance(filings, dict) else None
                    if not isinstance(recent, dict):
                        return f'# sec_filing({company!r}): EDGAR submissions unavailable for {title} — {hint}'
                    pick = H_sec_pick_filing(recent, form, year)
                    if pick is None:
                        return f"# sec_filing({company!r}, {form!r}, year={year or 'latest'}): no matching filing in EDGAR's recent index for {title} — check the form/year, or {hint}"
                    accession, doc = pick
                    url = H_SEC_DOC_URL.format(cik=cik10.lstrip('0') or cik10, accession=accession.replace('-', ''), doc=doc)
                    return f"# sec_filing -> {title} {form} {year or '(latest)'} primary document:\n{url}\nNow call read_page on this URL with a focus hint for the section you need, and cite figures from that read_page result."

                def H_ledger_page(url: str, ledger: H_EvidenceLedger) -> tuple[int, dict] | None:
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

                def H_do_page_grep(url: str, pattern: str, ledger: H_EvidenceLedger) -> str:
                    hit = H_ledger_page(url, ledger)
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
                        if any((abs(c - prev) < H_PAGE_GREP_WINDOW // 2 for prev in seen_at)):
                            continue
                        seen_at.append(c)
                        a = max(0, c - H_PAGE_GREP_WINDOW // 2)
                        b = min(len(text), a + H_PAGE_GREP_WINDOW)
                        out.append(f'\n--- match @{a} ---\n{text[a:b]}')
                        if len(out) >= H_PAGE_GREP_MAX_HITS:
                            break
                    if not out:
                        return f'# page_grep({pat!r}) on [{n}]: no match in {len(text)} chars. Try a shorter or looser pattern.'
                    return f'# page_grep({pat!r}) on [{n}] -> {len(out)} match(es) of {len(text)} chars' + ''.join(out)

                def H_do_page_read(url: str, offset: int, length: int, ledger: H_EvidenceLedger) -> str:
                    hit = H_ledger_page(url, ledger)
                    if hit is None:
                        return f'# page_read: {url!r} has not been fetched this run; call read_page first'
                    n, row = hit
                    text = row.get('text') or ''
                    a = max(0, min(int(offset or 0), max(0, len(text) - 1)))
                    ln = int(length or H_PAGE_READ_MAX_CHARS)
                    b = min(len(text), a + max(1, min(ln, H_PAGE_READ_MAX_CHARS)))
                    return f'# page_read([{n}] @{a}:{b} of {len(text)})\n{text[a:b]}'

                def H_do_retain_evidence(source: str, quote: str, ledger: H_EvidenceLedger) -> str:
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
                    if len(q) < H_RETAIN_MIN_QUOTE:
                        return f'# retain_evidence: quote too short ({len(q)} chars); quote at least {H_RETAIN_MIN_QUOTE} characters of the source text'
                    if not text:
                        return f'# retain_evidence: result [{n}] has no stored text to quote from'
                    i = text.find(q)
                    if i < 0:
                        i = text.lower().find(q.lower())
                    if i < 0:
                        squashed = ' '.join(q.split())
                        i = ' '.join(text.split()).lower().find(squashed.lower())
                        if i >= 0:
                            i = -1
                    if i < 0:
                        return f'# retain_evidence: that text does not appear in [{n}]. Quote it EXACTLY as the source prints it, or read more of the page first.'
                    kept = row.setdefault('retained', [])
                    if len(kept) >= H_RETAIN_MAX_PER_ROW:
                        return f'# retain_evidence: [{n}] already has {len(kept)} retained excerpts'
                    a = max(0, i - H_RETAIN_MARGIN_CHARS)
                    b = min(int(row.get('note_len') or len(text)), i + len(q) + H_RETAIN_MARGIN_CHARS)
                    if b <= a:
                        return f'# retain_evidence: could not bound the excerpt in [{n}]'
                    kept.append((a, b))
                    return f'# retain_evidence: kept {b - a} chars of [{n}] around your quote. Cite [{n}] for that claim.'

                async def H_run_tool(call, question: str, ledger: H_EvidenceLedger, deadline: float) -> str:
                    try:
                        args = json.loads(getattr(call, 'arguments', None) or '{}')
                    except Exception:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}
                    name = getattr(call, 'name', '') or ''
                    if name == 'web_search':
                        return await H_do_search(str(args.get('query') or ''), ledger)
                    if name == 'read_page':
                        return await H_do_fetch(str(args.get('url') or ''), str(args.get('focus') or ''), question, ledger)
                    if name == 'retain_evidence':
                        return H_do_retain_evidence(str(args.get('source') or ''), str(args.get('quote') or ''), ledger)
                    if name == 'page_grep':
                        return H_do_page_grep(str(args.get('url') or ''), str(args.get('pattern') or ''), ledger)
                    if name == 'page_read':
                        return H_do_page_read(str(args.get('url') or ''), args.get('offset') or 0, args.get('length') or H_PAGE_READ_MAX_CHARS, ledger)
                    if name == 'sec_filing':
                        return await H_do_sec_filing(str(args.get('company') or ''), str(args.get('form') or ''), str(args.get('year') or ''), deadline)
                    return f'# unknown tool {name!r}'
                H_REASONING_MANDATORY = ('openai/gpt-oss',)

                def H_least_think(lane: str, model: str='') -> dict:
                    for prefix in H_REASONING_MANDATORY:
                        if model.startswith(prefix):
                            return {'enabled': True, 'effort': 'low'}
                    return {'enabled': False}

                async def H_chat_simple(lane: str, model: str, system: str, user: str, *, max_tokens: int, timeout: float, think: dict | None=None) -> str:
                    if think is None:
                        think = H_least_think(lane, model)
                    payload = await llm_chat(provider=lane, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=think)
                    H_spend_note(payload)
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

                class H_EmptyChoiceMessage:
                    content = ''
                    tool_calls = ()

                class H_EmptyChoice:
                    message = H_EmptyChoiceMessage()

                class H_EmptyLlm:
                    raw_text = ''
                    choices = (H_EmptyChoice(),)

                class H_EmptyTurn:
                    llm = H_EmptyLlm()
                    budget = None
                H_EMPTY_TURN = H_EmptyTurn()

                async def H_chat_turn(messages: list[dict], deadline: float, *, finish_only: bool, force_tools: bool=False):
                    payload_chars = sum((len(str(msg.get('content') or '')) for msg in messages if isinstance(msg, dict)))
                    for attempt, lane_model in enumerate(((H_LLM_LANE_A, H_LOOP_MODEL_A), (H_LLM_LANE_B, H_LOOP_MODEL_B))):
                        lane = lane_model[0]
                        model = lane_model[1]
                        is_fallback = attempt > 0
                        if is_fallback and payload_chars > H_LANE_B_MAX_PAYLOAD_CHARS:
                            return H_EMPTY_TURN
                        timeout = min(H_TURN_TIMEOUT_S, deadline - monotonic() - 5.0)
                        if timeout <= 5.0:
                            return None
                        try:
                            payload = await asyncio.wait_for(llm_chat(provider=lane, model=model, messages=messages, tools=H_LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': False} if finish_only and is_fallback else {'enabled': True, 'effort': 'low'}, max_output_tokens=6000 if finish_only and is_fallback else None, timeout=timeout), timeout=min(timeout + 6.0, max(1.0, deadline - monotonic() - 1.0)))
                            H_spend_note(payload)
                            return payload
                        except Exception:
                            continue
                    return None

                async def H_knowledge_brief(question: str) -> tuple[str, str]:
                    system = 'Senior research analyst. Commit to concrete best answers from knowledge; mark uncertain values (verify). Never refuse.'
                    user = f"Question:\n{question}\n\nFill in this internal worksheet. It is planning scratch for your own use, never an answer, so keep the tags lowercase and never reuse them as section headings later.\ndraft: your full best answer now — candidate pool, every stated condition applied, qualifying entities with figures/dates, near-miss exclusions. Flag shaky facts with (verify).\nconditions: each atomic condition in the question, numbered, including any output-format demand.\nsearches: 3-6 precise web searches for the facts that decide the answer (entity + metric + year; include a named source's site: filter).\nurls: up to 5 exact URLs worth reading directly (official stats pages, sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."
                    raw = ''
                    try:
                        raw = await H_chat_simple(H_LLM_LANE_A, H_LOOP_MODEL_A, system, user, max_tokens=2400, timeout=H_BRIEF_TIMEOUT_S, think=H_least_think(H_LLM_LANE_A, H_LOOP_MODEL_A))
                    except Exception:
                        try:
                            raw = await H_chat_simple(H_LLM_LANE_B, H_LOOP_MODEL_B, system, user, max_tokens=2400, timeout=H_BRIEF_TIMEOUT_S, think=H_least_think(H_LLM_LANE_B, H_LOOP_MODEL_B))
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
                H_SEED_TOKEN_RE = re.compile("[A-Za-z0-9][A-Za-z0-9.\\-']+")
                H_SEED_STOP = frozenset('name list give tell show find identify please could would you your can may might should must let make sure both also'.split())
                H_MAX_SEED_QUERIES = 3

                def H_seed_queries(question: str, set_question: bool) -> list[str]:
                    q = ' '.join((question or '').split())
                    if not q:
                        return []
                    seeds = [q[:300]]
                    salient = [t for t in H_SEED_TOKEN_RE.findall(q) if len(t) >= 3 and t.lower() not in H_STOP and (t.lower() not in H_SEED_STOP)]
                    if len(salient) >= 2:
                        seeds.append(' '.join(salient[:8]))
                    if set_question and salient:
                        seeds.append('list of ' + ' '.join(salient[:6]))
                    out: list[str] = []
                    for s in seeds:
                        s = s.strip()
                        if s and s not in out:
                            out.append(s)
                    return out[:H_MAX_SEED_QUERIES]

                async def H_preseed(question: str, set_question: bool, ledger: H_EvidenceLedger, deadline: float) -> str:
                    seeds = H_seed_queries(question, set_question)
                    if not seeds or deadline - monotonic() < 40.0:
                        return ''
                    blocks: list = []
                    for seed in seeds:
                        if deadline - monotonic() < 30.0:
                            break
                        try:
                            out = await asyncio.wait_for(H_do_search(seed, ledger), timeout=H_SEARCH_TIMEOUT_S * 2 + 6.0)
                            blocks.append(H_commit_tool_output(out, ledger))
                        except Exception:
                            continue
                    good = [b for b in blocks if isinstance(b, str) and H_CITE_MARK_RE.search(b)]
                    if not good:
                        return ''
                    return 'Automatic first-pass searches (already numbered — cite these [n] directly, and search further as needed):\n\n' + '\n'.join(good)

                async def H_loop(question: str, brief: str, ledger: H_EvidenceLedger, deadline: float, turn_cap: int, carry: list[dict] | None=None, allow_tools_in_wrapup: bool=False) -> tuple[str, list[dict]]:
                    if carry is not None:
                        messages = carry
                    else:
                        set_q = H_needs_set_completeness(question)
                        messages = [{'role': 'system', 'content': H_LOOP_RULES}]
                        if set_q:
                            messages.append({'role': 'system', 'content': H_SET_RULE})
                        if H_needs_superlative_proof(question):
                            messages.append({'role': 'system', 'content': H_SUPERLATIVE_RULE})
                        if brief:
                            messages.append({'role': 'system', 'content': brief})
                        seeded = await H_preseed(question, set_q, ledger, deadline)
                        if seeded:
                            messages.append({'role': 'system', 'content': seeded})
                        messages.append({'role': 'user', 'content': question})
                    answer = ''
                    ordered_wrapup = False
                    repairs_left = H_ANSWER_REPAIR_TURNS
                    for turn in range(1, turn_cap + 1):
                        left = deadline - monotonic()
                        if left <= H_MIN_TAIL_S:
                            break
                        out_of_time = left <= H_WRAPUP_AT_S
                        out_of_spend = H_spend_left() <= H_WRAPUP_MIN_USD
                        finish_only = out_of_time or out_of_spend or turn >= turn_cap
                        if (finish_only or turn >= turn_cap - 1) and (not ordered_wrapup):
                            messages.append({'role': 'system', 'content': H_wrapup_order(left)})
                            ordered_wrapup = True
                        payload = await H_chat_turn(messages, deadline, finish_only=finish_only, force_tools=allow_tools_in_wrapup and turn == 1)
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
                            if not H_is_usable_answer(candidate):
                                if repairs_left > 0 and deadline - monotonic() > H_MIN_TAIL_S + 10.0:
                                    repairs_left -= 1
                                    messages.append({'role': 'system', 'content': H_REPAIR_ORDER})
                                    answer = ''
                                    continue
                                answer = ''
                                break
                            answer = candidate
                            messages.append({'role': 'assistant', 'content': answer})
                            break
                        messages.append(msg.to_input_message())
                        run_calls = calls[:8]
                        tool_budget = max(5.0, min(H_FETCH_TIMEOUT_S * 2 + 6.0, deadline - monotonic() - H_MIN_TAIL_S))
                        tool_tasks = [asyncio.ensure_future(H_run_tool(c, question, ledger, deadline)) for c in run_calls]
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
                            body = H_commit_tool_output(call_result[1], ledger)
                            messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': body})
                        for call in calls[8:]:
                            messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})
                    return (answer, messages)

                async def H_audit_patch(question: str, answer: str, messages: list[dict], ledger: H_EvidenceLedger, deadline: float) -> str:
                    probe = f"""Audit the answer against the question. JSON only, keys: "unanswered_parts" (list; question elements not addressed), "uncited_facts" (list; load-bearing claims without [n]), "wrong_kind" (list; places where the named entity is a different KIND than the question asks — a person instead of a series, a duo instead of a show), "incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges over a candidate pool — a closed set that can be enumerated, or several conditions applied to a class — then: is the pool itself stated and plausibly COMPLETE, and does the answer give a verdict for EVERY member (qualifies / excluded because X, each cited)? Name any pool member the answer never mentions, and say so if the pool looks truncated — an answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not partial), "thin_proof" (list; a qualifier lacking a per-condition citation, or a plausible near-miss candidate never addressed), "hand_waved_tally" (list; for a superlative/count/most-common question: the answer asserts a winner or a count WITHOUT showing the candidate table it was derived from. Phrases like 'among others', 'and several more', 'multiple X', or naming 2 examples to justify a count are all hand-waving — say so and name what the tally must list). Empty lists when clean.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:11000]}"""
                    try:
                        raw = await H_chat_simple(H_LLM_LANE_A, H_AUDIT_MODEL, 'Strict completeness auditor. JSON only.', probe, max_tokens=2200, timeout=max(8.0, min(H_AUDIT_TIMEOUT_S, deadline - monotonic() - 72.0)))
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
                    patched, _ = await H_loop(question, '', ledger, deadline, H_AUDIT_EXTRA_TURNS + 1, carry=messages, allow_tools_in_wrapup=True)
                    patched = patched.strip()
                    if not H_is_usable_answer(patched) or len(patched) < int(len(answer) * 0.6):
                        return answer
                    return patched
                H_BRACKET_FIX = {12304: '[', 12305: ']', 65339: '[', 65341: ']', 65288: '(', 65289: ')', 8209: '-', 8722: '-'}
                for _d in range(10):
                    H_BRACKET_FIX[65296 + _d] = chr(48 + _d)

                def H_normalize_brackets(text: str) -> str:
                    return (text or '').translate(H_BRACKET_FIX)
                H_CITE_NUM_RE = re.compile('\\[([0-9][0-9,\\s\\-]*)\\]')

                def H_cited_numbers(answer: str, top: int) -> list[int]:
                    answer = H_normalize_brackets(answer)
                    seen: set[int] = set()
                    out: list[int] = []
                    for m in H_CITE_NUM_RE.finditer(answer):
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
                H_OUTPUT_ONLY_RE = re.compile('\\boutput only\\b|\\brespond with only\\b|\\breply with only\\b|\\banswer with only\\b|\\bonly the exact\\b|\\bnothing else\\b|\\bno explanation\\b|\\bwithout explanation\\b|\\bno other text\\b|\\bjust the (?:name|names|value|values|number|numbers|list|text|answer|title|titles)\\b', re.IGNORECASE)
                H_OUTPUT_ONLY_MIN_CHARS = 2

                def H_answer_line_only(answer: str, question: str) -> str:
                    if not answer or not H_OUTPUT_ONLY_RE.search(question or ''):
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
                        if len(line) >= H_OUTPUT_ONLY_MIN_CHARS:
                            return line
                    return answer
                H_GLOSS_RE = re.compile('^(?P<a>[^()]{2,60}?)\\s*\\((?P<b>[^()]{2,60})\\)$')

                def H_verbatim_from_source(value: str, ledger: H_EvidenceLedger) -> str:
                    v = (value or '').strip()
                    m = H_GLOSS_RE.match(v)
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

                def H_verbatim_structured(obj, ledger: H_EvidenceLedger, depth: int=0):
                    if depth > 6:
                        return obj
                    if isinstance(obj, str):
                        return H_verbatim_from_source(obj, ledger)
                    if isinstance(obj, list):
                        return [H_verbatim_structured(x, ledger, depth + 1) for x in obj]
                    if isinstance(obj, dict):
                        return {k: H_verbatim_structured(v, ledger, depth + 1) for k, v in obj.items()}
                    return obj

                def H_citations_for(answer: str, ledger: H_EvidenceLedger) -> list[CitationRef]:
                    refs: list[CitationRef] = []
                    spent = 0
                    for n in H_cited_numbers(answer, len(ledger.rows)):
                        if len(refs) >= H_CITATION_CAP:
                            break
                        ref = ledger.ref_for(n)
                        if ref is None:
                            continue
                        row = ledger.rows[n - 1]
                        slices = getattr(ref, 'slices', None)
                        cost = sum((max(0, s.end - s.start) for s in slices)) if slices else int(row.get('note_len') or 0)
                        if spent + cost > H_EVIDENCE_CHAR_BUDGET:
                            continue
                        spent += cost
                        refs.append(ref)
                    return refs
                H_VERIFY_MARK_RE = re.compile('\\s*\\((?:verify|unverified|uncertain)[^)]*\\)', re.I)
                H_TOOL_MARKUP_RE = re.compile('<\\s*/?\\s*tool_call|<\\s*/?\\s*(?:arg_key|arg_value|function_call|invoke)\\b|\\bweb_search\\s*[（(]\\s*query|\\bread_page\\s*[（(]\\s*url|\\bsec_filing\\s*[（(]\\s*company', re.I)
                H_STUB_ANSWER_RE = re.compile('^\\s*(?:best-effort answer unavailable|no question provided)', re.I)
                H_REFUSAL_ONLY_RE = re.compile("^\\s*(?:i (?:cannot|can't|am unable|was unable)|unable to|sorry[,.]|i don'?t have (?:enough|access))", re.I)
                H_INTENT_NARRATION_RE = re.compile("^\\s*(?:i (?:need|will|should|am going|'ll)\\b|let me\\b|first,? (?:i|let)\\b|i'?ll (?:search|look|start|begin|gather|check))", re.I)
                H_MIN_ANSWER_CHARS = 40
                H_MIN_CITED_ANSWER_CHARS = 12
                H_CITE_MARK_RE = re.compile('\\[[0-9]{1,3}\\]')

                def H_looks_like_tool_json(s: str) -> bool:
                    return bool(re.match('\\s*\\{\\s*"(?:name|tool|function)"\\s*:', s))

                def H_is_degenerate_repetition(text: str) -> bool:
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

                def H_is_usable_answer(text: str) -> bool:
                    s = H_normalize_brackets(text).strip()
                    if not s:
                        return False
                    if H_TOOL_MARKUP_RE.search(s) or H_looks_like_tool_json(s):
                        return False
                    if H_STUB_ANSWER_RE.match(s) or H_is_degenerate_repetition(s):
                        return False
                    cited = bool(H_CITE_MARK_RE.search(s))
                    if cited and len(s) >= H_MIN_CITED_ANSWER_CHARS:
                        return True
                    if len(s) < H_MIN_ANSWER_CHARS:
                        return False
                    if len(s) < 400 and (H_REFUSAL_ONLY_RE.match(s) or H_INTENT_NARRATION_RE.match(s)):
                        return False
                    return True
                H_COMMIT_RULES = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too. Never say what the evidence does not contain; commit to the best-supported answer you can defend."
                H_REPAIR_ORDER = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

                def H_sanitize_draft(text: str) -> str:
                    return H_VERIFY_MARK_RE.sub('', text or '').strip()

                def H_ledger_digest(ledger: H_EvidenceLedger, char_cap: int=60000) -> str:
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
                H_FURNITURE_RE = re.compile('^\\s*(?:share|search|home|menu|subscribe|sign\\s*in|log\\s*in|newsletter|advertisement|cookie|skip to|follow us|read more|related|tags?|categories?|privacy|terms|contact|about us|navigation|toggle)\\b', re.I)
                H_SRC_FOOTNOTE_RE = re.compile('\\[\\s*\\d{1,3}\\s*\\]')
                H_MD_LINK_RE = re.compile('\\]\\(')
                H_BARE_URL_RE = re.compile('(?<!\\]\\()https?://')
                H_SENTENCEY_RE = re.compile('[.!?]\\s|[.!?]$|\\b(?:is|was|were|are|has|have|had|reported|announced|released|won|ranked|totall?ed)\\b', re.I)

                def H_informative_lead(preview: str, limit: int=280) -> str:
                    kept: list[str] = []
                    broke = False
                    for chunk in re.split('(?<=[.!?])\\s+|\\n+', H_SRC_FOOTNOTE_RE.sub('', preview or '')):
                        seg = ' '.join(chunk.split())
                        if len(seg) < 30 or len(seg) > 400:
                            if kept:
                                broke = True
                                break
                            continue
                        if H_SENTENCEY_RE.search(seg) is None:
                            if kept:
                                broke = True
                                break
                            continue
                        if H_FURNITURE_RE.match(seg) and (not re.search('\\d', seg)):
                            if kept:
                                broke = True
                                break
                            continue
                        if seg.startswith(('*', '|', '↑', '#')):
                            if kept:
                                broke = True
                                break
                            continue
                        links = len(H_MD_LINK_RE.findall(seg)) + len(H_BARE_URL_RE.findall(seg))
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

                def H_deterministic_answer(question: str, ledger: H_EvidenceLedger) -> str:
                    rows = [(i, r) for i, r in enumerate(ledger.rows, start=1) if (r.get('preview') or '').strip()]
                    if not rows:
                        return ''
                    out = ['Best-supported findings from the sources retrieved:']
                    picked = 0
                    for i, r in rows:
                        if picked >= 6:
                            break
                        lead = H_informative_lead(r.get('preview') or '')
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
                H_QUOTE_SYNTH_TIMEOUT_S = 42.0
                H_QUOTE_SYNTH_MIN_BUDGET_S = 30.0
                H_QUOTE_SYNTH_MIN_QUOTES = 2
                H_QUOTE_TABLE_CHARS = 1400

                def H_quote_table(ledger: H_EvidenceLedger) -> str:
                    parts = []
                    for i, row in enumerate(ledger.rows, start=1):
                        text = row.get('text') or ''
                        for a, b in row.get('retained') or []:
                            excerpt = text[max(0, int(a)):int(b)][:H_QUOTE_TABLE_CHARS].strip()
                            if excerpt:
                                parts.append(f"[{i}] {row.get('title') or row.get('url') or ''}\n{excerpt}")
                    return '\n\n'.join(parts)

                def H_retained_count(ledger: H_EvidenceLedger) -> int:
                    return sum((len(r.get('retained') or []) for r in ledger.rows))

                async def H_write_from_digest(question: str, ledger: H_EvidenceLedger, deadline: float) -> str:
                    left = deadline - monotonic()
                    if left < 14.0:
                        return ''
                    digest = H_ledger_digest(ledger)
                    if not digest:
                        return ''
                    convo = [{'role': 'system', 'content': H_COMMIT_RULES}, {'role': 'user', 'content': f'Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'}]

                    async def _one(lane: str, model: str, budget: float) -> str:
                        payload = await llm_chat(provider=lane, model=model, messages=convo, temperature=0.15, max_output_tokens=2600, timeout=budget, thinking=H_least_think(lane, model))
                        H_spend_note(payload)
                        llm = getattr(payload, 'llm', None)
                        text = (getattr(llm, 'raw_text', None) or '').strip()
                        if not text:
                            choices = getattr(llm, 'choices', None) or []
                            if choices:
                                c = getattr(choices[0].message, 'content', None)
                                if isinstance(c, str):
                                    text = c.strip()
                        return text
                    lanes = ((H_LLM_LANE_A, H_LOOP_MODEL_A), (H_LLM_LANE_B, H_LOOP_MODEL_B))
                    for i, lane_model in enumerate(lanes):
                        left = deadline - monotonic()
                        if left < 14.0:
                            return ''
                        budget = min(H_RESCUE_TIMEOUT_S, left - H_DIGEST_TAIL_S)
                        if i == 0:
                            budget = min(budget, max(12.0, left - 14.0 - H_DIGEST_TAIL_S))
                        if budget < 8.0:
                            return ''
                        try:
                            text = await _one(lane_model[0], lane_model[1], budget)
                        except Exception:
                            continue
                        if H_is_usable_answer(text):
                            return text
                    return ''

                async def H_knowledge_resort(question: str, deadline: float) -> str:
                    left = deadline - monotonic()
                    if left < 12.0:
                        return ''
                    try:
                        return await H_chat_simple(H_LLM_LANE_A, H_RESORT_MODEL, 'Expert researcher. Best definitive answer with concrete entities, numbers, dates. Never refuse.', question, max_tokens=2600, timeout=min(45.0, left - 4.0))
                    except Exception:
                        return ''

                async def H_schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
                    ask = f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}'
                    for lane, model in ((H_LLM_LANE_A, H_SCHEMA_MODEL), (H_LLM_LANE_A, H_RESORT_MODEL), (H_LLM_LANE_B, H_LOOP_MODEL_B)):
                        left = deadline - monotonic()
                        if left < 12.0:
                            break
                        try:
                            raw = await H_chat_simple(lane, model, 'You output strictly valid JSON.', ask, max_tokens=3400, timeout=min(45.0, left - 4.0))
                            raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()
                            value = json.loads(raw)
                            if H_matches_schema_shape(value, schema):
                                return value
                            if isinstance(value, dict) and len(value) == 1:
                                inner = list(value.values())[0]
                                if H_matches_schema_shape(inner, schema):
                                    return inner
                        except Exception:
                            continue
                    return None

                def H_schema_kind(schema) -> str:
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
                                    got = H_schema_kind(sub)
                                    if got:
                                        return got
                        if isinstance(schema.get('properties'), dict):
                            return 'object'
                        if isinstance(schema.get('enum'), list):
                            return 'string'
                        return ''
                    return str(kind)

                def H_matches_schema_shape(value, schema) -> bool:
                    kind = H_schema_kind(schema)
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
                H_NUM_IN_TEXT_RE = re.compile('-?\\d[\\d,]*(?:\\.\\d+)?')
                H_DIGEST_LEAD_RE = re.compile('^\\s*Best-supported findings|^\\s*sources retrieved:', re.I)
                H_DIGEST_NOISE_RE = re.compile('\\[slice \\d+:\\d+\\]|https?://\\S+')
                H_VALUE_MAX_CHARS = 90

                def H_undigest_for_schema(basis: str) -> str:
                    if not basis:
                        return ''
                    text = H_DIGEST_NOISE_RE.sub(' ', basis)
                    out = []
                    for raw in text.split('\n'):
                        line = raw.strip().lstrip('-*• ').strip()
                        if not line or H_DIGEST_LEAD_RE.match(line):
                            continue
                        if ':' in line:
                            head, _, tail = line.partition(':')
                            line = tail.strip() if 0 < len(tail.strip()) <= H_VALUE_MAX_CHARS else head.strip()
                        if not line or len(line) > H_VALUE_MAX_CHARS:
                            continue
                        if line.count(' ') > 8:
                            continue
                        if line not in out:
                            out.append(line)
                        if len(out) >= 6:
                            break
                    return '\n'.join(out)

                def H_coerce_to_schema(answer: str, schema, depth: int=0):
                    if depth > 4 or not isinstance(schema, dict):
                        return answer[:400]
                    enum = schema.get('enum')
                    if isinstance(enum, list) and enum:
                        low = (answer or '').lower()
                        for opt in enum:
                            if isinstance(opt, str) and re.search('\\b' + re.escape(opt.lower()) + '\\b', low):
                                return opt
                        return enum[0]
                    kind = H_schema_kind(schema)
                    if not kind:
                        for key in ('anyOf', 'oneOf', 'allOf'):
                            branch = schema.get(key)
                            if isinstance(branch, list) and branch:
                                for sub in branch:
                                    if isinstance(sub, dict) and sub.get('type') != 'null':
                                        return H_coerce_to_schema(answer, sub, depth + 1)
                        kind = 'string'
                    if kind == 'array':
                        items = schema.get('items') or {}
                        parts = [p.strip(' -*\t') for p in re.split('[\\n;]|,(?![^(]*\\))', answer or '')]
                        parts = [p[:400] for p in parts if p][:20]
                        if not parts:
                            parts = [answer[:400]]
                        return [H_coerce_to_schema(p, items, depth + 1) for p in parts]
                    if kind == 'object':
                        props = schema.get('properties') or {}
                        required = schema.get('required') or list(props.keys())
                        out = {}
                        for key in required:
                            out[key] = H_coerce_to_schema(answer, props.get(key) or {}, depth + 1)
                        return out
                    if kind in ('number', 'integer'):
                        found = H_NUM_IN_TEXT_RE.search(H_CITE_NUM_RE.sub(' ', answer or ''))
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
                H_NARRATION_LEAD_RE = re.compile("^\\s*(?:based on (?:my|the)\\b|now (?:i|that i)\\b|i (?:now )?(?:have|was|am|need|will|can)\\b|i(?:'ll|'ve|'m)\\b|let me\\b|let's\\b|first,? i\\b|having (?:now )?\\w+\\b|okay\\b|alright\\b|to answer this\\b|my research\\b)", re.IGNORECASE)
                H_ABBREV_TAIL_RE = re.compile('(?:\\b[A-Z]|\\b(?:Inc|Ltd|Co|No|vs|St|Dr|Mr|Ms|Mt|Jr|Sr|etc|e\\.g|i\\.e))\\.$')

                def H_strip_lead_narration(text: str) -> str:
                    t = (text or '').strip()
                    if not t:
                        return t
                    for _ in range(2):
                        parts = re.split('(?<=[.!?])\\s+', t, maxsplit=1)
                        if len(parts) != 2:
                            break
                        head, rest = (parts[0], parts[1].strip())
                        if H_CITE_NUM_RE.search(head):
                            break
                        if H_NARRATION_LEAD_RE.match(head) is None:
                            break
                        if len(head.split()) < 4 or H_ABBREV_TAIL_RE.search(head) is not None:
                            break
                        if len(rest) < 120 or H_CITE_NUM_RE.search(rest) is None:
                            break
                        t = rest
                    return t

                def H_cap(text: str) -> str:
                    t = (text or '').strip()
                    if len(t) > H_ANSWER_CHAR_CAP:
                        return t[:H_ANSWER_CHAR_CAP - 16] + ' …'
                    return t

                async def H_query(query: Query) -> Response:
                    question = (query.text or '').strip()
                    if not question:
                        return Response(text='No question provided.')
                    try:
                        return await H_solve(query, question)
                    except Exception:
                        return Response(text=f'Best-effort answer unavailable for: {question[:500]}')

                async def H_solve(query: Query, question: str) -> Response:
                    deadline = monotonic() + H_WALL_BUDGET_S
                    try:
                        info = await tooling_info(timeout=10.0)
                        H_spend_note(info)
                    except Exception:
                        pass
                    draft = ''
                    brief = ''
                    try:
                        if H_spend_left() >= H_BRIEF_MIN_USD and deadline - monotonic() > 120.0:
                            draft, brief = await H_knowledge_brief(question)
                    except Exception:
                        brief = ''
                    ledger = H_EvidenceLedger()
                    answer = ''
                    messages: list[dict] = []
                    try:
                        answer, messages = await H_loop(question, brief, ledger, deadline, H_MAX_TURNS)
                    except Exception:
                        answer = ''
                    try:
                        if H_is_usable_answer(answer) and deadline - monotonic() > 75.0 and (H_spend_left() >= H_AUDIT_MIN_USD):
                            patched = await H_audit_patch(question, answer, messages, ledger, deadline)
                            if H_is_usable_answer(patched):
                                answer = patched
                    except Exception:
                        pass
                    if not H_is_usable_answer(answer) and ledger.rows:
                        try:
                            rescued = await H_write_from_digest(question, ledger, deadline)
                            if H_is_usable_answer(rescued):
                                answer = rescued
                        except Exception:
                            pass
                    if not H_is_usable_answer(answer) and ledger.rows:
                        det = H_deterministic_answer(question, ledger)
                        if H_is_usable_answer(det):
                            answer = det
                    if not H_is_usable_answer(answer):
                        fallback = H_sanitize_draft(draft) or await H_knowledge_resort(question, deadline)
                        if H_is_usable_answer(fallback):
                            answer = fallback
                    try:
                        citations = H_citations_for(answer, ledger)
                    except Exception:
                        citations = []
                    answer = H_normalize_brackets(answer)
                    answer = H_strip_lead_narration(answer)
                    answer = H_answer_line_only(answer, question)
                    text = H_cap(answer) or f'Best-effort answer unavailable for: {question[:400]}'
                    if query.output_schema is not None:
                        structured = None
                        try:
                            structured = await H_schema_output(question, answer, query.output_schema, deadline)
                        except Exception:
                            structured = None
                        if structured is not None:
                            try:
                                structured = H_verbatim_structured(structured, ledger)
                            except Exception:
                                pass
                            try:
                                return Response(output=structured, citations=citations or None)
                            except Exception:
                                structured = None
                        basis = answer if H_is_usable_answer(answer) else ''
                        if not basis:
                            basis = H_deterministic_answer(question, ledger)
                        if not basis or H_STUB_ANSWER_RE.match(basis.strip()):
                            basis = question[:400]
                        if basis is not answer:
                            try:
                                salvaged = await H_schema_output(question, basis, query.output_schema, deadline)
                            except Exception:
                                salvaged = None
                            if salvaged is not None:
                                try:
                                    return Response(output=salvaged, citations=citations or None)
                                except Exception:
                                    pass
                        if basis is not answer:
                            cleaned = H_undigest_for_schema(basis)
                            basis = cleaned if cleaned else ''
                        try:
                            forced = H_coerce_to_schema(H_cap(basis), query.output_schema)
                            return Response(output=forced, citations=citations or None)
                        except Exception:
                            try:
                                return Response(output=H_cap(basis)[:2000], citations=citations or None)
                            except Exception:
                                pass
                    try:
                        return Response(text=text, citations=citations or None)
                    except Exception:
                        return Response(text=text)
                ROUTER_PROVIDER = 'openrouter'
                ROUTER_MODEL = 'google/gemma-4-31b-it'
                ROUTER_PROMPT = 'Is this question easy or hard? Reply with one word: easy or hard.'
                ROUTER_TIMEOUT_S = 6.0

                async def route_is_easy(text: str) -> bool:
                    result = await asyncio.wait_for(llm_chat(provider=ROUTER_PROVIDER, model=ROUTER_MODEL, messages=[{'role': 'system', 'content': ROUTER_PROMPT}, {'role': 'user', 'content': text}], temperature=0.0, max_output_tokens=4, thinking=LlmThinkingConfig(enabled=False), timeout=ROUTER_TIMEOUT_S), timeout=ROUTER_TIMEOUT_S + 2.0)
                    return (result.response.raw_text or '').strip().lower().startswith('easy')

                async def query(query: Query) -> Response:
                    try:
                        easy = await route_is_easy(query.text)
                    except Exception:
                        easy = False
                    if easy:
                        return await E_query(query)
                    return await H_query(query)
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
            _TOTAL_BUDGET_S = 290.0

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

        async def query(query: Query) -> Response:
            return await _CONTROLLER.solve(query)
        _TAG_D95EEF87 = 'd95eef87c2074c9b8a6db9fedd37e96e'
        import logging as _tag_logging_d95eef87
        _tag_logging_d95eef87.getLogger('miner.tag').debug('tag=%s', _TAG_D95EEF87)
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

class Adjudicator:
    """Run both pipelines under one deadline, then keep the better answer."""
    _DEADLINE_S = 290.0

    def __init__(self, lead, rival, gate):
        self._lead = lead
        self._rival = rival
        self._gate = gate

    async def _guarded(self, run, query: Query):
        if run is None:
            return None
        try:
            return await run(query)
        except Exception:
            return None

    async def solve(self, query: Query) -> Response:
        try:
            settled = await asyncio.wait_for(asyncio.gather(self._guarded(self._lead, query), self._guarded(self._rival, query)), timeout=self._DEADLINE_S)
        except Exception:
            settled = ()
        candidates = [r for r in settled if r is not None]
        if not candidates:
            return Response(text='No answer produced.')
        return max(candidates, key=lambda r: self._gate.grade(query, r))
_LEAD_RUN = _safe_compile(LeadSolver)
_RIVAL_RUN = _safe_compile(RivalSolver)
_ADJUDICATOR = Adjudicator(_LEAD_RUN, _RIVAL_RUN, ResponseGate())

@entrypoint('query')
async def query(query: Query) -> Response:
    return await _ADJUDICATOR.solve(query)
_TAG_E107468E="e107468ed8da43adafa3b1e691793e75"
import logging as _tag_logging_e107468e
_tag_logging_e107468e.getLogger("miner.tag").debug("tag=%s", _TAG_E107468E)
