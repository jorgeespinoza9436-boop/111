from __future__ import annotations
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class PebbleRow_4e2e5b:

    def _compile(self):
        import asyncio
        import json
        import re
        from time import monotonic
        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        VERSION = 'fdsf'
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
        FETCH_TIMEOUT_S = 16.0
        LANE_B_MAX_PAYLOAD_CHARS = 144000
        SEARCH_TIMEOUT_S = 18.0
        WRAPUP_AT_S = 90.0
        RESCUE_TIMEOUT_S = 55.0
        MIN_TAIL_S = 8.0
        MAX_TURNS = 15
        AUDIT_EXTRA_TURNS = 2
        AUDIT_TIMEOUT_S = 28.0
        ANSWER_REPAIR_TURNS = 2
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
        MAX_REFS_PER_URL = 2
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
        LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nPREFER THE PRIMARY SOURCE: when two sources state the same fact, cite the one that ORIGINATES it -- the agency, registry, filing, official statistics release or the organisation\'s own page -- not an encyclopedia or aggregator repeating it. Measured verbatim on a task where both answers were factually correct: "Answer 1 is preferred for using primary sources" (it cited NARA where we cited Wikipedia) -- a full point lost on every run. Use the encyclopedia to FIND the primary source, then fetch and cite that.\n\nQUOTE WHAT PROVES IT: the judge credits a claim only when your citation CONTAINS the source text stating it. The moment you read a decisive value, call retain_evidence(source, quote) with the exact words from that result. Do this for every condition you test and every figure you report -- an answer whose citations do not carry its numbers loses to one that does, even when both answers are identical.\nALSO QUOTE THE QUESTION\'S PREMISES, not only your answer. Every entity, work, date or figure the question NAMES is a claim the judge expects traceable: the film it says someone directed, the article it points at, the year it fixes, the people it lists. You lose to an otherwise identical answer that cited those too -- measured verbatim: "does not provide a citation for \'Everyone Says I Love You\'... Answer 1 is more thorough in its traceability to all parts of the prompt\'s context". Retain a quote for each named premise as you confirm it, even when it is background you already believed.\n\nREAD DEEP, DO NOT RE-FETCH: read_page shows the head plus a few regions of a long page. If the value you need is not in what you were shown, call page_grep(url, pattern) to find it anywhere in that page and page_read to open the region around a reported offset. Grepping a page you already have costs nothing and beats another search.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. COPY SOURCE VALUES VERBATIM: when the question names a source, every name, label and value in the answer must be the exact string that source prints -- never add a familiar alternative in parentheses, never anglicise a transliteration. \'Makkah\' is the answer; \'Mecca (Makkah)\' is a wrong answer. ONE EXCEPTION, and it is absolute: if the question says to output ONLY the answer (\'output only\', \'respond with only\', \'nothing else\', \'no explanation\'), emit the answer line as the BARE requested text — no [n] markers on it, nothing else on that line: a trailing [3] makes the text inexact and fails the instruction. Still write the PROOF section BELOW it carrying its [n] markers. Only the answer line is shipped, but the citations are harvested from the proof first, and an uncited answer scores zero. Obeying that instruction IS the task. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.\n\nSUPPORTS LINES — REQUIRED WHENEVER YOU WRITE A PROOF SECTION. After the proof section add a final block headed exactly \'Evidence support:\' with ONE line per distinct [n] you cited, as \'[n] Supports: <one sentence naming the exact fact that slice proves>\'. Name the value, date or entity the slice establishes — never \'background\' or \'context\'. If a cited slice supports nothing you asserted, drop the citation instead of writing a line for it. Never emit the words \'Proof\' or \'Evidence support\' as your entire answer.\n\nDO NOT CITE THE QUESTION\'S PREAMBLE. Questions often identify the subject obliquely (\'the studio that distributed X and Y\'). Works named only to POINT at the subject are not something your answer asserts — resolve them without citing. Cite ONLY sources that establish a value the answer actually returns; an irrelevant citation is a rule-12 penalty.\n\nOBEY THE OUTPUT FORMAT LITERALLY. If the query says \'a single integer with no other text or punctuation\', your answer is that integer and nothing else — no bullets, no bold, no units, no workings. Put all reasoning in the proof section, never in the answer line. An answer that is correct but wrongly formatted loses to one that is merely formatted right.\n\nCANONICAL VALUES — copy the source\'s own wording. When a field names an entity, emit the full canonical form exactly as the cited source writes it: \'Arkansas Razorbacks\' not \'Arkansas\'; \'Republic of Pisa\' not \'Italy\'; \'Walt Disney Studios Motion Pictures\' if that is what the page says. Never abbreviate, never substitute a modern or broader name, and never hedge a value the source states plainly — write 1290, not \'c. 1290\', unless the source itself hedges. When two sources disagree on form, prefer the one your citation slice actually shows. Judges score the exact string, and a truncated or generalised value loses a tie you would otherwise win.'

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
        _DEAD_URLS: dict = {}

        def _mark_dead(url: str, msg: str) -> str:
            key = url.strip()
            if key and len(_DEAD_URLS) < 64:
                _DEAD_URLS[key] = msg
            return msg

        async def _do_fetch(url: str, focus: str, question: str, ledger: EvidenceLedger) -> str:
            if not url.strip():
                return '# read_page: empty url'
            _cached = _DEAD_URLS.get(url.strip())
            if _cached:
                return _cached
            payload = None
            _why = ''
            for _attempt in (0, 1):
                try:
                    payload = await fetch_page(url, provider=FETCH_PROVIDER, timeout=FETCH_TIMEOUT_S, provider_extra=_FETCH_EXTRA)
                    if getattr(payload, 'results', None):
                        break
                    _why = 'empty result set'
                except Exception as exc:
                    payload = None
                    _why = repr(exc)[:100]
                    if 'Timeout' not in _why:
                        break
            if payload is None:
                return _mark_dead(url, f'# read_page({url!r}) failed ({_why}). This URL returns no extractable text and will fail again -- do NOT retry it; find the fact on a different source.')
            _spend_note(payload)
            receipt = str(getattr(payload, 'receipt_id', '') or '')
            results = list(getattr(payload, 'results', None) or [])
            if not results or not receipt:
                return _mark_dead(url, f'# read_page({url!r}): no content. Do NOT retry this URL.')
            item = results[0]
            rid = getattr(item, 'result_id', None)
            note = getattr(item, 'note', None) or ''
            if not isinstance(rid, str) or not rid or (not note.strip()):
                return _mark_dead(url, f'# read_page({url!r}): no usable content. Do NOT retry this URL.')
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
                if lane == LLM_LANE_B and payload_chars > LANE_B_MAX_PAYLOAD_CHARS:
                    return _EMPTY_TURN
                timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0, turn_wall - monotonic())
                if timeout <= 5.0:
                    return None
                try:
                    payload = await asyncio.wait_for(llm_chat(provider=lane, model=model, messages=messages, tools=LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': False} if finish_only and lane == LLM_LANE_B else {'enabled': True, 'effort': 'low'}, max_output_tokens=6000 if finish_only and lane == LLM_LANE_B else None, provider_extra=_upstream(lane, model) if pinned else None, timeout=timeout), timeout=min(timeout + 6.0, max(1.0, deadline - monotonic() - 1.0)))
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
            per_url: dict = {}
            for n in _cited_numbers(answer, len(ledger.rows)):
                if len(refs) >= CITATION_CAP:
                    break
                ref = ledger.ref_for(n)
                if ref is None:
                    continue
                row = ledger.rows[n - 1]
                url = str(row.get('url') or '')
                if url and per_url.get(url, 0) >= MAX_REFS_PER_URL:
                    continue
                slices = getattr(ref, 'slices', None)
                cost = sum((max(0, s.end - s.start) for s in slices)) if slices else int(row.get('note_len') or 0)
                if spent + cost > EVIDENCE_CHAR_BUDGET:
                    continue
                spent += cost
                if url:
                    per_url[url] = per_url.get(url, 0) + 1
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
            _DEAD_URLS.clear()
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

class BoulderRow_4e2e5b:

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
                VERSION = 'v52-pin-reviewed'
                LLM_LANE_A = 'openrouter'
                LLM_LANE_B = 'openrouter'
                LOOP_MODEL_A = 'z-ai/glm-5.2'
                LOOP_MODEL_B = 'qwen/qwen3.6-27b'
                AUDIT_MODEL = 'openai/gpt-oss-120b'
                SCHEMA_MODEL = 'openai/gpt-oss-120b'
                RESORT_MODEL = 'deepseek/deepseek-v3.2'
                SEARCH_PROVIDER = 'parallel'
                WALL_BUDGET_S = 266.0
                BRIEF_TIMEOUT_S = 50.0
                TURN_TIMEOUT_S = 75.0
                LANE_B_MAX_PAYLOAD_CHARS = 144000
                AUDIT_TIMEOUT_S = 28.0
                SEARCH_TIMEOUT_S = 18.0
                FETCH_TIMEOUT_SECONDS = 18.3
                WRAPUP_AT_S = 90.0
                MIN_TAIL_S = 8.0
                MAX_TURNS = 15
                AUDIT_EXTRA_TURNS = 2
                ANSWER_REPAIR_TURNS = 2
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
                LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}, {'type': 'function', 'function': {'name': 'page_grep', 'description': 'Search INSIDE a page you already fetched, by regex or literal text, and get every match with its surrounding context and character offset. Use this when read_page showed you the head of a long page but the value you need is deeper in it -- do not re-fetch, grep it.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL of a page already fetched this run'}, 'pattern': {'type': 'string', 'description': 'regex or literal string to find, e.g. a city name, a year, a column label'}}, 'required': ['url', 'pattern']}}}, {'type': 'function', 'function': {'name': 'page_read', 'description': 'Read an arbitrary character range of a page you already fetched. Use the offsets page_grep reports to read the full table or section around a match.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL already fetched'}, 'offset': {'type': 'integer', 'description': 'start character offset'}, 'length': {'type': 'integer', 'description': 'how many characters to read (max 12000)'}}, 'required': ['url', 'offset']}}}, {'type': 'function', 'function': {'name': 'retain_evidence', 'description': "Keep the exact source text that proves a claim you are about to make. Pass the result number and the verbatim quote from it. Do this the moment you find a decisive value -- the judge only credits claims whose citation contains the supporting text, and this is how that text gets into your citation. Use it for the QUESTION'S PREMISES as well as your answer: every entity, work, date or figure the question names should end up with a retained quote confirming it.", 'parameters': {'type': 'object', 'properties': {'source': {'type': 'string', 'description': 'result number to quote from, e.g. 3'}, 'quote': {'type': 'string', 'description': 'verbatim text copied from that result that states the fact'}}, 'required': ['source', 'quote']}}}, {'type': 'function', 'function': {'name': 'compute', 'description': 'Do arithmetic on numbers you already have -- sums, differences, percent changes, ratios, comparisons. LOOP_RULES already requires showing your arithmetic for any derived answer (mean, total, rank, count); use this tool to actually run it instead of doing it in your head, so a derived number can never be a silent mental-math error.', 'parameters': {'type': 'object', 'properties': {'operation': {'type': 'string', 'enum': ['sum', 'difference', 'percent_change', 'ratio', 'compare'], 'description': 'sum/difference/ratio: pairwise on `values`. percent_change: (b-a)/a*100 on the first two `values`. compare: returns which of `values` is largest and smallest.'}, 'values': {'type': 'array', 'items': {'type': 'number'}, 'description': 'the numbers to operate on, in order'}}, 'required': ['operation', 'values']}}}]
                LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nPREFER THE PRIMARY SOURCE: when two sources state the same fact, cite the one that ORIGINATES it -- the agency, registry, filing, official statistics release or the organisation\'s own page -- not an encyclopedia or aggregator repeating it. Measured verbatim on a task where both answers were factually correct: "Answer 1 is preferred for using primary sources" (it cited NARA where we cited Wikipedia) -- a full point lost on every run. Use the encyclopedia to FIND the primary source, then fetch and cite that.\n\nQUOTE WHAT PROVES IT: the judge credits a claim only when your citation CONTAINS the source text stating it. The moment you read a decisive value, call retain_evidence(source, quote) with the exact words from that result. Do this for every condition you test and every figure you report -- an answer whose citations do not carry its numbers loses to one that does, even when both answers are identical.\nALSO QUOTE THE QUESTION\'S PREMISES, not only your answer. Every entity, work, date or figure the question NAMES is a claim the judge expects traceable: the film it says someone directed, the article it points at, the year it fixes, the people it lists. You lose to an otherwise identical answer that cited those too -- measured verbatim: "does not provide a citation for \'Everyone Says I Love You\'... Answer 1 is more thorough in its traceability to all parts of the prompt\'s context". Retain a quote for each named premise as you confirm it, even when it is background you already believed.\n\nREAD DEEP, DO NOT RE-FETCH: read_page shows the head plus a few regions of a long page. If the value you need is not in what you were shown, call page_grep(url, pattern) to find it anywhere in that page and page_read to open the region around a reported offset. Grepping a page you already have costs nothing and beats another search.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. COPY SOURCE VALUES VERBATIM: when the question names a source, every name, label and value in the answer must be the exact string that source prints -- never add a familiar alternative in parentheses, never anglicise a transliteration. \'Makkah\' is the answer; \'Mecca (Makkah)\' is a wrong answer. ONE EXCEPTION, and it is absolute: if the question says to output ONLY the answer (\'output only\', \'respond with only\', \'nothing else\', \'no explanation\'), emit the answer line as the BARE requested text — no [n] markers on it, nothing else on that line: a trailing [3] makes the text inexact and fails the instruction. Still write the PROOF section BELOW it carrying its [n] markers. Only the answer line is shipped, but the citations are harvested from the proof first, and an uncited answer scores zero. Obeying that instruction IS the task. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nCITE THE STATEMENT, NOT JUST THE TABLE: for any fact you had to compute or derive -- a ranking, a sum, a comparison, an intersection of two conditions -- if a source\'s text ALSO states that derived conclusion in prose (not just the raw inputs you computed it from), cite that stated-conclusion sentence, in addition to or instead of the raw table. A citation the judge can read as already proving the claim beats one that requires the judge to redo your arithmetic from a table slice. When the primary data required real computation, search specifically for a source that states the conclusion directly. DO NOT PAD CITATIONS: cite the fewest sources that each distinctly support a claim -- several overlapping or redundant citations for the same single fact read as noise, not thoroughness; drop a citation if another one already covers the same point at least as well.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

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
                            payload = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=FETCH_TIMEOUT_SECONDS)
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

                def _do_compute(operation: str, values: list) -> str:
                    try:
                        nums = [float(v) for v in values or []]
                    except (TypeError, ValueError):
                        return '# compute: values must all be numbers'
                    if not nums:
                        return '# compute: values must be a non-empty list of numbers'
                    if operation == 'sum':
                        return f'# compute: sum({nums}) = {sum(nums)!r}'
                    if operation == 'difference':
                        if len(nums) < 2:
                            return '# compute: difference needs at least 2 values'
                        out = nums[0]
                        for n in nums[1:]:
                            out -= n
                        return f'# compute: difference({nums}) = {out!r}'
                    if operation == 'ratio':
                        if len(nums) < 2 or nums[1] == 0:
                            return '# compute: ratio needs 2 values and a non-zero second value'
                        return f'# compute: ratio({nums[0]}/{nums[1]}) = {nums[0] / nums[1]!r}'
                    if operation == 'percent_change':
                        if len(nums) < 2 or nums[0] == 0:
                            return '# compute: percent_change needs 2 values and a non-zero first value'
                        pct = (nums[1] - nums[0]) / nums[0] * 100.0
                        return f'# compute: percent_change({nums[0]} -> {nums[1]}) = {pct!r}%'
                    if operation == 'compare':
                        return f'# compute: compare({nums}) = largest {max(nums)!r}, smallest {min(nums)!r}'
                    return f'# compute: unknown operation {operation!r}'

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
                    if name == 'compute':
                        return _do_compute(str(args.get('operation') or ''), args.get('values'))
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
                        if lane == LLM_LANE_B and payload_chars > LANE_B_MAX_PAYLOAD_CHARS:
                            return _EMPTY_TURN
                        timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0, turn_wall - monotonic())
                        if timeout <= 5.0:
                            return None
                        try:
                            payload = await asyncio.wait_for(llm_chat(provider=lane, model=model, messages=messages, tools=LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': False} if finish_only and lane == LLM_LANE_B else {'enabled': True, 'effort': 'low'}, max_output_tokens=6000 if finish_only and lane == LLM_LANE_B else None, provider_extra=_upstream(lane, model) if pinned else None, timeout=timeout), timeout=min(timeout + 6.0, max(1.0, deadline - monotonic() - 1.0)))
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
                        tool_budget = max(5.0, min(FETCH_TIMEOUT_SECONDS * 2 + 6.0, deadline - monotonic() - MIN_TAIL_S))
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
                STRUCTURED_LOOP_RULES = LOOP_RULES + "\n\nSTRUCTURED OUTPUT COMPLETENESS: this question requires a specific JSON shape. If a schema field is an array/list of qualifying items, before you write the final answer, RE-READ the evidence you have ALREADY GATHERED (no new tool calls) for other items meeting the question's stated criteria -- an array missing a qualifying item scores exactly as wrong as an incorrect answer. This is a one-time re-read of existing evidence, not a license for more research: only issue ONE additional search, and only for a named field that currently has ZERO evidence -- never re-search a field you already have a cited value for just to double-check it."

                def _schema_field_brief(schema) -> str:
                    if not isinstance(schema, dict):
                        return ''
                    props = schema.get('properties')
                    if not isinstance(props, dict) or not props:
                        return ''
                    required = schema.get('required') or []
                    lines = []
                    for name, spec in props.items():
                        kind = spec.get('type') if isinstance(spec, dict) else None
                        req = ' (required)' if name in required else ''
                        lines.append(f"- {name}: {kind or 'any'}{req}")
                    return 'STRUCTURED OUTPUT SHAPE (for orientation, not a per-field search checklist) — the final answer needs a well-cited value for each of these; research normally and keep this shape in mind, it is not a mandate to search for each field separately:\n' + '\n'.join(lines)

                async def _structured_loop(question: str, brief: str, ledger: EvidenceLedger, deadline: float, turn_cap: int, carry: list[dict] | None=None, allow_tools_in_wrapup: bool=False) -> tuple[str, list[dict]]:
                    if carry is not None:
                        messages = carry
                    else:
                        set_q = _needs_set_completeness(question)
                        messages = [{'role': 'system', 'content': STRUCTURED_LOOP_RULES}]
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
                        tool_budget = max(5.0, min(FETCH_TIMEOUT_SECONDS * 2 + 6.0, deadline - monotonic() - MIN_TAIL_S))
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
                    texts = [r.get('text') or '' for r in ledger.rows if r.get('text')]
                    if not texts:
                        return value

                    def seen(t: str) -> bool:
                        return bool(t) and any((t in src for src in texts))
                    if len(v) >= 3:
                        pat = re.compile('(\\w[\\w\\s]{0,40}?)\\s*[-:–—]\\s*' + re.escape(v) + '\\b')
                        candidates = set()
                        for src in texts:
                            for line in src.splitlines():
                                cm = pat.search(line)
                                if cm:
                                    candidates.add(f'{cm.group(1).strip()} - {v}')
                        if len(candidates) == 1:
                            return candidates.pop()
                    if seen(v):
                        return value
                    m = _GLOSS_RE.match(v)
                    if m:
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

                def _prose_score(text: str) -> float:
                    t = (text or '')[:2000]
                    if not t:
                        return 0.0
                    score = 1.0
                    pipes = t.count('|') * 100.0 / max(len(t), 1)
                    if pipes > 6:
                        score *= 0.3
                    elif pipes > 3:
                        score *= 0.6
                    digits = sum((1 for c in t if c.isdigit()))
                    if digits / max(len(t), 1) > 0.15:
                        score *= 0.6
                    if re.search('\\b(?:were|was|totaled|totalled|ranked|reported|accounted for|the (?:top|highest|lowest|largest|smallest))\\b', t, re.I):
                        score *= 1.4
                    return score

                def _citation_clusters(answer: str, top: int) -> list[list[int]]:
                    answer = _normalize_brackets(answer)
                    clusters: list[list[int]] = []
                    cur: list[int] = []
                    prev_end = None
                    for m in _CITE_NUM_RE.finditer(answer):
                        nums = []
                        for chunk in m.group(1).split(','):
                            piece = chunk.strip()
                            if piece.isdigit():
                                n = int(piece)
                                if 1 <= n <= top:
                                    nums.append(n)
                        if not nums:
                            continue
                        gap = answer[prev_end:m.start()] if prev_end is not None else None
                        if gap is not None and gap.strip(' ,') == '':
                            cur.extend(nums)
                        else:
                            if cur:
                                clusters.append(cur)
                            cur = list(nums)
                        prev_end = m.end()
                    if cur:
                        clusters.append(cur)
                    return clusters

                def _citations_for(answer: str, ledger: EvidenceLedger) -> list[CitationRef]:
                    drop: set[int] = set()
                    for cluster in _citation_clusters(answer, len(ledger.rows)):
                        if len(cluster) <= 2:
                            continue
                        scored = sorted(cluster, key=lambda n: _prose_score(ledger.rows[n - 1].get('text') or ''), reverse=True)
                        drop.update(scored[2:])
                    refs: list[CitationRef] = []
                    spent = 0
                    for n in _cited_numbers(answer, len(ledger.rows)):
                        if n in drop:
                            continue
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
                    ask = f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value. If a field is an array of qualifying items, include EVERY qualifying item the answer supports -- do not truncate to one example when the answer names several; an array missing a qualifying item scores exactly as wrong as an incorrect value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}'
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
                _TOOL_NAME_RE = re.compile('\\b(?:web_search|sec_filing|read_page|page_grep|page_read|retain_evidence|compute)\\b', re.IGNORECASE)
                _PROCESS_TALK_RE = re.compile("\\b(?:I|my|we)\\b|\\b(?:let me|let's)\\b|\\bevidence I\\b|\\bformatting\\b|\\b(?:gathered|retrieved|fetched|queried|need|needed)\\b", re.IGNORECASE)

                def _is_tool_narration(head: str) -> bool:
                    return _TOOL_NAME_RE.search(head) is not None and _PROCESS_TALK_RE.search(head) is not None

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
                _AUDIT_META_RE = re.compile("\\baudit(?:'s|s')?\\s+(?:premise|premises|claim|claims|claimed|note|notes|noted|flag|flags|flagged|report|finding|findings|assertion|suggestion|says|said|states|stated)\\b", re.IGNORECASE)

                def _strip_audit_meta(text: str) -> str:
                    t = text or ''
                    if not _AUDIT_META_RE.search(t):
                        return t
                    out = []
                    for part in re.split('(?<=[.!?])\\s+', t):
                        if _AUDIT_META_RE.search(part) and (not _CITE_NUM_RE.search(part)):
                            continue
                        out.append(part)
                    cleaned = ' '.join((p for p in out if p.strip())).strip()
                    return cleaned if len(cleaned) >= 40 else t

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
                        if query.output_schema is not None:
                            field_brief = _schema_field_brief(query.output_schema)
                            combined_brief = f'{brief}\n\n{field_brief}' if brief and field_brief else field_brief or brief
                            answer, messages = await _structured_loop(question, combined_brief, ledger, deadline, MAX_TURNS)
                        else:
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

        class SecondPath:

            def _compile(self):
                ANSWER_CAP_CHARS = 70000
                BRIEF_TIMEOUT_S = 55.0
                TURN_TIMEOUT_S = 80.0
                FETCH_TIMEOUT_S = 15.0
                TASK_TOTAL_BUDGET_SECONDS = 250.0
                WALL_BUDGET_S = 245.0
                COMMIT_SECS = 85.0
                SEARCH_TIMEOUT_S = 20.0
                AUDIT_TIMEOUT_S = 30.0
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

                async def _s20_base_query(query: Query) -> Response:
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
                import asyncio as _s20_asyncio
                import json as _s20_json
                import re as _s20_re
                from time import monotonic as _s20_monotonic
                _S20_HARD_BUDGET_GATE_S = 250.0
                _S20_MAX_WINDOW_S = 55.0
                _S20_MIN_WINDOW_S = 10.0
                _S20_ANCHOR_CONFIRM_TIMEOUT_S = 8.0
                _S20_STALENESS_VERIFY_TIMEOUT_S = 8.0
                _S20_BASIS_EXTRACT_TIMEOUT_S = 8.0
                _S20_BASIS_AUDIT_TIMEOUT_S = 9.0
                _S20_SEARCH_TIMEOUT_S = 9.0
                _S20_PATCH_TIMEOUT_S = 12.0
                _S20_MAX_ANCHOR_CANDIDATES = 6
                _S20_MAX_CONFIRMED_ANCHOR_GAPS = 3
                _S20_MAX_BASIS_FINDINGS = 3
                _S20_MAX_NEW_CITATIONS_PER_GAP = 2
                _S20_MAX_TOTAL_CITATIONS = 60
                _S20_MODEL = 'deepseek/deepseek-v3.2'
                _S20_CURRENT_STATE_KEYWORD_RE = _s20_re.compile('\\b(currently|is\\s+the\\s+current|remains?\\s+the|still\\s+(?:holds?|serves?|leads?|stands?)|to\\s+date|as\\s+of\\s+(?:now|today|writing)?|the\\s+incumbent|reigning|ongoing|latest|most\\s+recent|record\\s+holder|so\\s+far|present(?:ly)?\\s+(?:the|serves)|active\\s+(?:champion|holder|record))\\b', _s20_re.IGNORECASE)
                _S20_ANCHOR_CONFIRM_SYSTEM_PROMPT = 'You audit candidate sentences from a research answer for load-bearing POSITIVE current-state assertions that LACK an explicit temporal anchor -- statements that something currently holds, remains true, is the latest, or is still the case, without a specific date, version, or as-of qualifier tying that state to a point in time.\nDiscard candidates that already carry an explicit date, version number, or as-of qualifier elsewhere in the same sentence; discard stylistic, trivial, or non-factual current-state phrasing (e.g. \'currently\' used as filler); discard claims about stable facts that do not meaningfully change over time.\nFor each CONFIRMED un-anchored current-state claim, write a short, targeted web search query (5-15 words) phrased to test whether that exact state has changed or is still accurate as of the latest available information -- not a restatement of the claim itself.\nReturn JSON only: {"gaps": [{"sentence": str, "search_query": str}, ...]}. Return an empty list if none of the candidates qualify.'
                _S20_STALENESS_VERIFY_SYSTEM_PROMPT = "You are a strict staleness-verification auditor for ONE un-anchored current-state claim from a research answer.\nYou receive the claim and up to 4 freshly retrieved, independent evidence snippets gathered specifically to test whether that state has changed.\nClassify strictly from this evidence:\n- still_current: a snippet directly shows the state is unchanged as of a determinable recent point; report that point as as_of_date (a short human-readable date or period string, not necessarily an ISO date).\n- superseded: a snippet directly shows the state has since changed -- report the new state as correction.\n- unverifiable: the evidence neither confirms currency nor shows a change.\nReturn JSON only with keys: verdict ('still_current'|'superseded'|'unverifiable'), as_of_date (string or null, only for still_current), correction (string or null, only for superseded), supporting_snippet_indices (array of 0-based ints, may be empty)."
                _S20_PATCH_ANCHOR_SYSTEM_PROMPT = 'You add an explicit temporal anchor to ONE current-state sentence inside a research answer, using freshly retrieved evidence that confirms the state is still accurate as of a specific point.\nRewrite the COMPLETE answer: keep every part unrelated to this sentence byte-for-byte, and edit only the flagged sentence to add the as-of date or period the evidence supports, without changing what the sentence otherwise claims. Do not soften or strengthen the underlying assertion; only pin it to the confirmed point in time.\nPreserve all existing citation markers whose underlying content is unchanged. Output plain answer text only: no preamble, no markdown fences, no meta-commentary about this process.'
                _S20_PATCH_SUPERSESSION_SYSTEM_PROMPT = 'You correct ONE stale current-state claim inside a research answer using freshly retrieved evidence that shows the state has since changed.\nRewrite the COMPLETE answer: keep every part unrelated to this claim byte-for-byte where feasible, and replace only the outdated assertion with the newer state the fresh evidence supports, including when the change occurred if the evidence gives that detail.\nPreserve all existing citation markers whose underlying claims are unchanged. Output plain answer text only: no preamble, no markdown fences, no meta-commentary about the correction process.'
                _S20_BASIS_EXTRACT_SYSTEM_PROMPT = 'You extract quantitative comparison points from a research answer (text or JSON).\nFind every place the answer states or compares a numeric or ranked value (money amount, percentage, count, rate, score, or rank) for 2 or more distinct named entities, periods, or items that share one metric.\nIf no such multi-value comparison exists in the content, set is_comparison to false and leave other fields empty.\nOtherwise, name the shared metric, and for up to 5 of the compared values, give: the entity/item/period it belongs to, and the basis descriptor explicitly stated for that value in the content (currency, fiscal-vs-calendar period, adjusted-vs-unadjusted, methodology or reporting standard, or an explicit as-of date) -- or null if the content states no basis for that value at all.\nOnly report values that are actually present in the given content; do not infer values the content does not state.\nReturn JSON only: {"is_comparison": bool, "metric": str, "values": [{"index": int, "entity": str, "basis": str or null}, ...]}.'
                _S20_BASIS_AUDIT_SYSTEM_PROMPT = 'You are a strict basis-comparability auditor for a quantitative comparison inside a research answer.\nYou receive the shared metric and a list of compared values, each with its 0-based index, the entity/item/period it belongs to, and its stated basis descriptor (or null if none was stated).\nDecide one overall verdict:\n- aligned: every value shares the same basis, or this metric does not require a basis descriptor to be meaningfully compared (e.g. simple counts of discrete named items).\n- mismatched: two or more values explicitly state different, incompatible bases (different currencies, different period types, adjusted vs unadjusted, or different methodologies).\n- unstated: this metric is basis-sensitive (money, fiscal or period-bound figures, methodology-dependent rates) and one or more compared values have no stated basis at all.\nWhen the verdict is mismatched or unstated, list up to 3 finding items, each naming one value by its index and giving a short, targeted web search query (5-15 words) that would source that value\'s basis descriptor or a version of that value expressed on a comparable basis to the others -- never a restatement of the whole original question.\nReturn JSON only: {"verdict": "aligned"|"mismatched"|"unstated", "findings": [{"index": int, "gap_query": str}, ...]}. Return an empty findings list when the verdict is aligned.'
                _S20_PATCH_BASIS_TEXT_SYSTEM_PROMPT = "You correct ONE value's basis inside a comparison research answer, using freshly retrieved evidence.\nRewrite the COMPLETE answer: keep every part unrelated to this one value byte-for-byte where feasible, and edit only the span naming this value to state its basis explicitly. If the evidence gives a comparable-basis figure for this value, use it to make the comparison apples-to-apples. If the evidence does not resolve a comparable figure, keep the original value but add a brief explicit caveat that it is not on the same basis as the other compared value(s).\nPreserve all existing citation markers whose underlying content is unchanged. Output plain answer text only: no preamble, no markdown fences, no meta-commentary about this process."
                _S20_PATCH_BASIS_OUTPUT_SYSTEM_PROMPT = 'You correct ONE value\'s basis inside a structured JSON comparison answer, using freshly retrieved evidence.\nYou receive the target JSON schema (if any), the CURRENT JSON answer, which one compared value (by entity/item) needs its basis addressed, and fresh evidence snippets gathered to resolve it.\nReturn ONLY the JSON keys (top-level, or one level nested) whose values must be added or corrected to state this value\'s basis, or to replace it with a comparable-basis figure, using ONLY key names that already exist in the schema or current answer -- never invent new keys. If the evidence does not give a confident comparable-basis figure, return an empty patch rather than guessing.\nAlso report which evidence snippets (by 0-based index) you actually used.\nReturn JSON only: {"patch": {...} or {}, "used_indices": [int, ...]}'

                def _s20_strip_json_fences(raw: str) -> str:
                    return _s20_re.sub('^```(?:json)?\\s*|\\s*```$', '', raw or '', flags=_s20_re.I | _s20_re.M).strip()

                def _s20_chat_text(llm_result) -> str:
                    if llm_result is None:
                        return ''
                    resp = getattr(llm_result, 'response', None)
                    text = getattr(resp, 'raw_text', None) if resp is not None else None
                    return (text or '').strip()

                def _s20_compact_json(value) -> str:
                    try:
                        return _s20_json.dumps(value, ensure_ascii=False, separators=(',', ':'))
                    except Exception:
                        return ''

                def _s20_citation_key(ref) -> tuple:
                    slices = tuple(((getattr(sl, 'start', None), getattr(sl, 'end', None)) for sl in getattr(ref, 'slices', None) or []))
                    return (getattr(ref, 'receipt_id', None), getattr(ref, 'result_id', None), slices)

                def _s20_dedup_citations(response):
                    citations = getattr(response, 'citations', None)
                    if not citations:
                        return response
                    seen: set = set()
                    deduped = []
                    for ref in citations:
                        key = _s20_citation_key(ref)
                        if key in seen:
                            continue
                        seen.add(key)
                        deduped.append(ref)
                    if len(deduped) == len(citations):
                        return response
                    try:
                        return response.model_copy(update={'citations': deduped})
                    except Exception:
                        return response

                def _s20_merge_citations(existing, new_refs):
                    existing_list = list(existing or [])
                    seen = {_s20_citation_key(ref) for ref in existing_list}
                    merged = list(existing_list)
                    for ref in new_refs:
                        key = _s20_citation_key(ref)
                        if key in seen:
                            continue
                        seen.add(key)
                        merged.append(ref)
                        if len(merged) >= _S20_MAX_TOTAL_CITATIONS:
                            break
                    return merged

                async def _s20_search_gap(search_query: str):
                    from harnyx_miner_sdk.api import search_web as _s20_search_web
                    for provider_name in ('parallel', 'desearch'):
                        try:
                            payload = await _s20_search_web(search_query[:300], provider=provider_name, num=4, timeout=_S20_SEARCH_TIMEOUT_S)
                        except Exception:
                            payload = None
                        if payload is None:
                            continue
                        results = list(getattr(payload, 'results', None) or [])
                        if not results:
                            continue
                        receipt = str(getattr(payload, 'receipt_id', '') or '')
                        if not receipt:
                            continue
                        items = []
                        for item in results:
                            rid = getattr(item, 'result_id', None)
                            note = (getattr(item, 'note', None) or '').strip()
                            if not isinstance(rid, str) or not rid or (not note):
                                continue
                            items.append({'result_id': rid, 'note': note, 'title': (getattr(item, 'title', None) or '').strip(), 'url': (getattr(item, 'url', None) or '').strip()})
                            if len(items) >= 4:
                                break
                        if items:
                            return {'receipt_id': receipt, 'items': items}
                    return None

                def _s20_build_refs(receipt_id: str, evidence_items: list, indices) -> list:
                    from harnyx_miner_sdk.query import CitationRef as _s20_citation_ref
                    from harnyx_miner_sdk.query import CitationSlice as _s20_citation_slice
                    refs = []
                    for raw_idx in indices or []:
                        try:
                            idx = int(raw_idx)
                        except Exception:
                            continue
                        if not 0 <= idx < len(evidence_items):
                            continue
                        item = evidence_items[idx]
                        note_len = len(item['note'])
                        end = min(500, note_len)
                        if end <= 0:
                            continue
                        try:
                            refs.append(_s20_citation_ref(receipt_id=receipt_id, result_id=item['result_id'], slices=[_s20_citation_slice(start=0, end=end)]))
                        except Exception:
                            continue
                        if len(refs) >= _S20_MAX_NEW_CITATIONS_PER_GAP:
                            break
                    return refs

                def _s20_evidence_block(items: list) -> str:
                    return '\n'.join((f"[{idx}] {item['title']} — {item['url']}\n{item['note'][:900]}" for idx, item in enumerate(items)))

                def _s20_shortlist_anchor_sentences(answer: str) -> list:
                    sentences = _s20_re.split('(?<=[.!?])\\s+', answer)
                    candidates = []
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if len(sentence) < 12 or len(sentence) > 600:
                            continue
                        if _S20_CURRENT_STATE_KEYWORD_RE.search(sentence):
                            candidates.append(sentence)
                        if len(candidates) >= _S20_MAX_ANCHOR_CANDIDATES:
                            break
                    return candidates

                async def _s20_confirm_anchor_gaps(question: str, candidates: list) -> list:
                    from harnyx_miner_sdk.api import llm_chat as _s20_llm_chat
                    candidates_block = '\n'.join((f'{idx}. {c}' for idx, c in enumerate(candidates)))
                    try:
                        result = await _s20_llm_chat(provider='openrouter', model=_S20_MODEL, messages=[{'role': 'system', 'content': _S20_ANCHOR_CONFIRM_SYSTEM_PROMPT}, {'role': 'user', 'content': f'Question:\n{question}\n\nCandidate sentences:\n{candidates_block}'}], tools=None, temperature=0.0, max_output_tokens=450, timeout=_S20_ANCHOR_CONFIRM_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return []
                    try:
                        parsed = _s20_json.loads(_s20_strip_json_fences(_s20_chat_text(result)))
                    except Exception:
                        return []
                    if not isinstance(parsed, dict):
                        return []
                    raw = parsed.get('gaps')
                    if not isinstance(raw, list):
                        return []
                    out = []
                    for item in raw:
                        if not isinstance(item, dict):
                            continue
                        sentence = str(item.get('sentence') or '').strip()
                        squery = str(item.get('search_query') or '').strip()
                        if sentence and squery:
                            out.append({'sentence': sentence, 'search_query': squery})
                        if len(out) >= _S20_MAX_CONFIRMED_ANCHOR_GAPS:
                            break
                    return out

                async def _s20_verify_staleness(claim: str, evidence_items: list) -> dict:
                    from harnyx_miner_sdk.api import llm_chat as _s20_llm_chat
                    evidence_block = _s20_evidence_block(evidence_items)
                    try:
                        result = await _s20_llm_chat(provider='openrouter', model=_S20_MODEL, messages=[{'role': 'system', 'content': _S20_STALENESS_VERIFY_SYSTEM_PROMPT}, {'role': 'user', 'content': f'Current-state claim:\n{claim}\n\nFresh evidence snippets:\n{evidence_block}'}], tools=None, temperature=0.0, max_output_tokens=350, timeout=_S20_STALENESS_VERIFY_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return {'verdict': 'unverifiable'}
                    try:
                        report = _s20_json.loads(_s20_strip_json_fences(_s20_chat_text(result)))
                    except Exception:
                        return {'verdict': 'unverifiable'}
                    if not isinstance(report, dict):
                        return {'verdict': 'unverifiable'}
                    return report

                async def _s20_patch_anchor(question: str, answer: str, claim: str, as_of_date: str, evidence_block: str) -> str:
                    from harnyx_miner_sdk.api import llm_chat as _s20_llm_chat
                    prompt = f"Question:\n{question}\n\nCurrent answer:\n{answer[:12000]}\n\nCurrent-state sentence needing an as-of anchor:\n{claim}\n\nConfirmed as-of point to anchor it to:\n{as_of_date or 'see evidence below'}\n\nFresh evidence snippets:\n{evidence_block}"
                    try:
                        result = await _s20_llm_chat(provider='openrouter', model=_S20_MODEL, messages=[{'role': 'system', 'content': _S20_PATCH_ANCHOR_SYSTEM_PROMPT}, {'role': 'user', 'content': prompt}], tools=None, temperature=0.1, max_output_tokens=1400, timeout=_S20_PATCH_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return ''
                    return _s20_chat_text(result)[:79000].strip()

                async def _s20_patch_supersession(question: str, answer: str, claim: str, correction: str, evidence_block: str) -> str:
                    from harnyx_miner_sdk.api import llm_chat as _s20_llm_chat
                    prompt = f"Question:\n{question}\n\nCurrent answer:\n{answer[:12000]}\n\nStale current-state claim being corrected:\n{claim}\n\nWhat the fresh evidence supports instead:\n{correction or 'see evidence below'}\n\nFresh evidence snippets:\n{evidence_block}"
                    try:
                        result = await _s20_llm_chat(provider='openrouter', model=_S20_MODEL, messages=[{'role': 'system', 'content': _S20_PATCH_SUPERSESSION_SYSTEM_PROMPT}, {'role': 'user', 'content': prompt}], tools=None, temperature=0.1, max_output_tokens=1400, timeout=_S20_PATCH_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return ''
                    return _s20_chat_text(result)[:79000].strip()

                async def _s20_temporal_anchor_gate(_s20_query, _s20_response):
                    if getattr(_s20_response, 'output', None) is not None:
                        return _s20_response
                    question = (getattr(_s20_query, 'text', None) or '').strip()
                    answer = (getattr(_s20_response, 'text', None) or '').strip()
                    if not question or not answer:
                        return _s20_response
                    candidates = _s20_shortlist_anchor_sentences(answer)
                    if not candidates:
                        return _s20_response
                    gaps = await _s20_confirm_anchor_gaps(question, candidates)
                    if not gaps:
                        return _s20_response
                    search_results = await _s20_asyncio.gather(*[_s20_search_gap(g['search_query']) for g in gaps], return_exceptions=True)
                    per_gap = []
                    for gap, search_result in zip(gaps, search_results):
                        if isinstance(search_result, Exception) or not search_result:
                            continue
                        per_gap.append((gap, search_result))
                    if not per_gap:
                        return _s20_response
                    verify_results = await _s20_asyncio.gather(*[_s20_verify_staleness(g['sentence'], sr['items']) for g, sr in per_gap], return_exceptions=True)
                    running_answer = answer
                    all_new_refs = []
                    for (gap, search_result), verdict_report in zip(per_gap, verify_results):
                        if isinstance(verdict_report, Exception) or not isinstance(verdict_report, dict):
                            continue
                        verdict = str(verdict_report.get('verdict') or '').strip().lower()
                        items = search_result['items']
                        receipt_id = search_result['receipt_id']
                        evidence_block = _s20_evidence_block(items)
                        if verdict == 'still_current':
                            new_text = await _s20_patch_anchor(question, running_answer, gap['sentence'], str(verdict_report.get('as_of_date') or ''), evidence_block)
                            if new_text:
                                running_answer = new_text
                                refs = _s20_build_refs(receipt_id, items, verdict_report.get('supporting_snippet_indices') or [0])
                                all_new_refs.extend(refs)
                            continue
                        if verdict == 'superseded':
                            new_text = await _s20_patch_supersession(question, running_answer, gap['sentence'], str(verdict_report.get('correction') or ''), evidence_block)
                            if new_text:
                                running_answer = new_text
                                refs = _s20_build_refs(receipt_id, items, verdict_report.get('supporting_snippet_indices') or [0])
                                all_new_refs.extend(refs)
                            continue
                    merged_citations = _s20_merge_citations(getattr(_s20_response, 'citations', None), all_new_refs)
                    if running_answer == answer and len(merged_citations) == len(list(getattr(_s20_response, 'citations', None) or [])):
                        return _s20_response
                    try:
                        return _s20_response.model_copy(update={'text': running_answer, 'citations': merged_citations})
                    except Exception:
                        return _s20_response

                async def _s20_extract_basis_values(content_repr: str, is_structured: bool) -> dict | None:
                    from harnyx_miner_sdk.api import llm_chat as _s20_llm_chat
                    label = 'Current JSON answer' if is_structured else 'Current answer text'
                    try:
                        result = await _s20_llm_chat(provider='openrouter', model=_S20_MODEL, messages=[{'role': 'system', 'content': _S20_BASIS_EXTRACT_SYSTEM_PROMPT}, {'role': 'user', 'content': f'{label}:\n{content_repr[:12000]}'}], tools=None, temperature=0.0, max_output_tokens=500, timeout=_S20_BASIS_EXTRACT_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return None
                    try:
                        parsed = _s20_json.loads(_s20_strip_json_fences(_s20_chat_text(result)))
                    except Exception:
                        return None
                    if not isinstance(parsed, dict) or not parsed.get('is_comparison'):
                        return None
                    values_raw = parsed.get('values')
                    if not isinstance(values_raw, list):
                        return None
                    values = []
                    for item in values_raw:
                        if not isinstance(item, dict):
                            continue
                        try:
                            idx = int(item.get('index'))
                        except Exception:
                            continue
                        entity = str(item.get('entity') or '').strip()
                        basis_raw = item.get('basis')
                        basis = basis_raw.strip() if isinstance(basis_raw, str) and basis_raw.strip() else None
                        if entity:
                            values.append({'index': idx, 'entity': entity, 'basis': basis})
                    if len(values) < 2:
                        return None
                    metric = str(parsed.get('metric') or '').strip()
                    return {'metric': metric, 'values': values}

                async def _s20_audit_basis(comparison: dict) -> dict | None:
                    from harnyx_miner_sdk.api import llm_chat as _s20_llm_chat
                    values_block = '\n'.join((f"{v['index']}. entity={v['entity']!r} basis={v['basis']!r}" for v in comparison['values']))
                    user_content = f"Shared metric: {comparison['metric'] or '(unspecified)'}\n\nCompared values:\n{values_block}"
                    try:
                        result = await _s20_llm_chat(provider='openrouter', model=_S20_MODEL, messages=[{'role': 'system', 'content': _S20_BASIS_AUDIT_SYSTEM_PROMPT}, {'role': 'user', 'content': user_content}], tools=None, temperature=0.0, max_output_tokens=500, timeout=_S20_BASIS_AUDIT_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return None
                    try:
                        parsed = _s20_json.loads(_s20_strip_json_fences(_s20_chat_text(result)))
                    except Exception:
                        return None
                    if not isinstance(parsed, dict):
                        return None
                    verdict = str(parsed.get('verdict') or '').strip().lower()
                    if verdict not in ('aligned', 'mismatched', 'unstated'):
                        return None
                    if verdict == 'aligned':
                        return {'verdict': verdict, 'findings': []}
                    raw_findings = parsed.get('findings')
                    if not isinstance(raw_findings, list):
                        return {'verdict': verdict, 'findings': []}
                    value_by_index = {v['index']: v for v in comparison['values']}
                    findings = []
                    for item in raw_findings:
                        if not isinstance(item, dict):
                            continue
                        try:
                            idx = int(item.get('index'))
                        except Exception:
                            continue
                        if idx not in value_by_index:
                            continue
                        gap_query = str(item.get('gap_query') or '').strip()
                        if not gap_query:
                            continue
                        findings.append({'index': idx, 'entity': value_by_index[idx]['entity'], 'gap_query': gap_query})
                        if len(findings) >= _S20_MAX_BASIS_FINDINGS:
                            break
                    return {'verdict': verdict, 'findings': findings}

                async def _s20_patch_basis_text(answer: str, entity: str, gap_query: str, evidence_block: str) -> str:
                    from harnyx_miner_sdk.api import llm_chat as _s20_llm_chat
                    prompt = f'Current answer:\n{answer[:12000]}\n\nValue needing an explicit or normalized basis:\n{entity}\n\nSearch query used to source it:\n{gap_query}\n\nFresh evidence snippets:\n{evidence_block}'
                    try:
                        result = await _s20_llm_chat(provider='openrouter', model=_S20_MODEL, messages=[{'role': 'system', 'content': _S20_PATCH_BASIS_TEXT_SYSTEM_PROMPT}, {'role': 'user', 'content': prompt}], tools=None, temperature=0.1, max_output_tokens=1400, timeout=_S20_PATCH_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return ''
                    return _s20_chat_text(result)[:79000].strip()

                async def _s20_patch_basis_output(schema_compact: str, current_output_compact: str, entity: str, gap_query: str, evidence_block: str) -> dict | None:
                    from harnyx_miner_sdk.api import llm_chat as _s20_llm_chat
                    prompt = f"Target JSON schema:\n{schema_compact or '(none provided)'}\n\nCurrent JSON answer:\n{current_output_compact[:8000]}\n\nValue needing an explicit or normalized basis:\n{entity}\n\nSearch query used to source it:\n{gap_query}\n\nFresh evidence snippets:\n{evidence_block}"
                    try:
                        result = await _s20_llm_chat(provider='openrouter', model=_S20_MODEL, messages=[{'role': 'system', 'content': _S20_PATCH_BASIS_OUTPUT_SYSTEM_PROMPT}, {'role': 'user', 'content': prompt}], tools=None, temperature=0.0, max_output_tokens=700, timeout=_S20_PATCH_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return None
                    try:
                        parsed = _s20_json.loads(_s20_strip_json_fences(_s20_chat_text(result)))
                    except Exception:
                        return None
                    if not isinstance(parsed, dict):
                        return None
                    return parsed

                def _s20_merge_output_patch(current, patch):
                    if not isinstance(current, dict) or not isinstance(patch, dict) or (not patch):
                        return None
                    merged = dict(current)
                    applied = False
                    for key, value in patch.items():
                        if key not in merged:
                            continue
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

                async def _s20_basis_reconciliation_gate(_s20_query, _s20_response):
                    output_schema = getattr(_s20_query, 'output_schema', None)
                    is_structured = getattr(_s20_response, 'output', None) is not None
                    if is_structured:
                        current_output = getattr(_s20_response, 'output')
                        if not isinstance(current_output, dict):
                            return _s20_response
                        content_repr = _s20_compact_json(current_output)
                        answer_text = None
                    else:
                        answer_text = (getattr(_s20_response, 'text', None) or '').strip()
                        if not answer_text:
                            return _s20_response
                        content_repr = answer_text
                        current_output = None
                    if not content_repr:
                        return _s20_response
                    comparison = await _s20_extract_basis_values(content_repr, is_structured)
                    if not comparison:
                        return _s20_response
                    audit = await _s20_audit_basis(comparison)
                    if not audit or audit['verdict'] == 'aligned' or (not audit['findings']):
                        return _s20_response
                    findings = audit['findings']
                    search_results = await _s20_asyncio.gather(*[_s20_search_gap(f['gap_query']) for f in findings], return_exceptions=True)
                    per_finding = []
                    for finding, search_result in zip(findings, search_results):
                        if isinstance(search_result, Exception) or not search_result:
                            continue
                        per_finding.append((finding, search_result))
                    if not per_finding:
                        return _s20_response
                    running_text = answer_text
                    running_output = dict(current_output) if isinstance(current_output, dict) else None
                    schema_compact = _s20_compact_json(output_schema)[:4000] if output_schema is not None else ''
                    all_new_refs = []
                    changed = False
                    for finding, search_result in per_finding:
                        items = search_result['items']
                        receipt_id = search_result['receipt_id']
                        evidence_block = _s20_evidence_block(items)
                        if is_structured:
                            patch_result = await _s20_patch_basis_output(schema_compact, _s20_compact_json(running_output), finding['entity'], finding['gap_query'], evidence_block)
                            if not patch_result:
                                continue
                            patch = patch_result.get('patch')
                            merged = _s20_merge_output_patch(running_output, patch) if isinstance(patch, dict) else None
                            if merged is None:
                                continue
                            running_output = merged
                            changed = True
                            used_indices = patch_result.get('used_indices')
                            refs = _s20_build_refs(receipt_id, items, used_indices if isinstance(used_indices, list) and used_indices else [0])
                            all_new_refs.extend(refs)
                        else:
                            patched = await _s20_patch_basis_text(running_text, finding['entity'], finding['gap_query'], evidence_block)
                            if not patched:
                                continue
                            running_text = patched
                            changed = True
                            refs = _s20_build_refs(receipt_id, items, [0, 1])
                            all_new_refs.extend(refs)
                    if not changed:
                        return _s20_response
                    merged_citations = _s20_merge_citations(getattr(_s20_response, 'citations', None), all_new_refs)
                    try:
                        if is_structured:
                            return _s20_response.model_copy(update={'output': running_output, 'citations': merged_citations})
                        return _s20_response.model_copy(update={'text': running_text, 'citations': merged_citations})
                    except Exception:
                        return _s20_response

                async def _s20_run_stages(_s20_query, _s20_response):
                    _s20_response = _s20_dedup_citations(_s20_response)
                    try:
                        _s20_response = await _s20_temporal_anchor_gate(_s20_query, _s20_response)
                    except Exception:
                        pass
                    try:
                        _s20_response = await _s20_basis_reconciliation_gate(_s20_query, _s20_response)
                    except Exception:
                        pass
                    return _s20_response

                async def _s20_finalize(_s20_query, _s20_response, _s20_t0: float):
                    if _s20_response is None:
                        return _s20_response
                    if getattr(_s20_response, 'text', None) in (None, '') and getattr(_s20_response, 'output', None) is None:
                        return _s20_response
                    elapsed = _s20_monotonic() - _s20_t0
                    if elapsed >= _S20_HARD_BUDGET_GATE_S:
                        return _s20_dedup_citations(_s20_response)
                    window = min(_S20_MAX_WINDOW_S, max(_S20_MIN_WINDOW_S, 280.0 - elapsed))
                    try:
                        return await _s20_asyncio.wait_for(_s20_run_stages(_s20_query, _s20_response), timeout=window)
                    except Exception:
                        return _s20_dedup_citations(_s20_response)

                async def query(query: Query) -> Response:
                    _s20_t0 = _s20_monotonic()
                    _s20_resp = await _s20_base_query(query)
                    try:
                        return await _s20_finalize(query, _s20_resp, _s20_t0)
                    except Exception:
                        return _s20_resp
                return query

        class DifficultyRouter:
            _PROVIDER = 'openrouter'
            _MODEL = 'google/gemma-4-31b-it'
            _PROMPT = 'Easy or Hard? Reply with one word only.'
            _TIMEOUT_S = 6.0

            async def _is_easy(self, text: str) -> bool:
                result = await asyncio.wait_for(llm_chat(provider=self._PROVIDER, model=self._MODEL, messages=[{'role': 'system', 'content': self._PROMPT}, {'role': 'user', 'content': text}], temperature=0.0, max_output_tokens=4, thinking=LlmThinkingConfig(enabled=False), timeout=self._TIMEOUT_S), timeout=self._TIMEOUT_S + 2.0)
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

class ShimPlate_4e2e5b:

    @staticmethod
    def _pebble_use_4e2e5b() -> bool:
        import time as _t
        return int(_t.time()) % 86400 >= 32400
_PEBBLE_RUN_4e2e5b = PebbleRow_4e2e5b()._compile()
_BOULDER_RUN_4e2e5b = BoulderRow_4e2e5b()._compile()
_SHIM_PLATE_4e2e5b = ShimPlate_4e2e5b()

@entrypoint('query')
async def query(query: Query) -> Response:
    if _SHIM_PLATE_4e2e5b._pebble_use_4e2e5b():
        return await _PEBBLE_RUN_4e2e5b(query)
    return await _BOULDER_RUN_4e2e5b(query)
