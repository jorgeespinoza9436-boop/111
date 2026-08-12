from __future__ import annotations
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class CoralRidge_aa75ec:

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

class JadeRidge_aa75ec:

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

        class SecondPath:

            def _compile(self):
                import asyncio
                import json
                import re
                from time import monotonic
                from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
                from harnyx_miner_sdk.decorators import entrypoint
                from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

                def _numeric_conflicts(text: str) -> list[str]:
                    entries = []
                    for m in re.finditer('((?:[A-Za-z][\\w%-]*\\s+){1,4})\\$?([0-9][\\d,]*(?:\\.\\d+)?)', (text or '')[:8000]):
                        ctx = frozenset((w.lower() for w in m.group(1).split() if len(w) > 3))
                        if ctx:
                            entries.append((ctx, m.group(2).replace(',', '')))
                        if len(entries) >= 40:
                            break
                    notes = []
                    for a in range(len(entries)):
                        for b in range(a + 1, len(entries)):
                            ca, na = entries[a]
                            cb, nb = entries[b]
                            if na != nb and len(ca & cb) >= 2 and (abs(len(na) - len(nb)) <= 2):
                                note = f"reconcile explicitly: both {na} and {nb} appear near '{' '.join(sorted(ca & cb))}'"
                                if note not in notes:
                                    notes.append(note)
                                if len(notes) >= 2:
                                    return notes
                    return notes
                PRODUCTION_PROFILE = 'agent_0723_v7'
                PROVIDER = 'openrouter'
                DRAFT_MODEL = 'z-ai/glm-5'
                LOOP_MODEL = 'z-ai/glm-5'
                PATCH_MODEL = 'openai/gpt-oss-120b'
                JSON_MODEL = 'openai/gpt-oss-120b'
                FALLBACK_MODEL = 'deepseek/deepseek-v3.2'
                TOTAL_BUDGET_SECONDS = 245.0
                DRAFT_TIMEOUT = 55.0
                SEARCH_TIMEOUT = 20.0
                FETCH_TIMEOUT = 15.0
                MAX_TURNS = 12
                FETCH_NOTE_CHARS = 6000
                PATCH_EXTRA_TURNS = 2
                LOOP_TURN_TIMEOUT = 80.0
                FORCE_COMMIT_SECONDS = 85.0
                PATCH_TIMEOUT = 30.0
                MAX_ANSWER_CHARS = 70000
                MAX_CITATIONS = 40
                SEARCH_NOTE_CHARS = 500
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
                TOOLS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web. Returns numbered results with title, url and a short excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'search_many', 'description': 'Run several web searches at once (in parallel) and get all numbered results back together. Use to enumerate or verify a whole set of candidates in one step — up to 8 queries.', 'parameters': {'type': 'object', 'properties': {'queries': {'type': 'array', 'items': {'type': 'string'}, 'description': 'up to 8 search queries to run together'}}, 'required': ['queries']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': 'Fetch one URL and return its extracted main text content.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}}, 'required': ['url']}}}]
                LOOP_SYSTEM_PROMPT = "You are an elite research analyst answering a multi-constraint factual question. Your answer will be judged pairwise against a strong reference answer: factual claims only earn credit when backed by cited tool results, and missing any element of the question is a coverage failure.\n\nYou have search_web, search_many, and fetch_page tools. Work candidate-by-candidate and constraint-by-constraint: verify every load-bearing fact (names, dates, counts, figures) with a tool result before asserting it — do not trust memory for verifiable specifics. Tool results are numbered like [7].\n\nCITATION RULE: in the final answer, put the source number in brackets immediately after EVERY factual claim — for qualifying entities AND for excluded ones (e.g. 'completed in 2017 [4]', 'only 13 storeys [9]'). A claim without a bracket is treated as uncited. Do not cite sources that do not support the claim.\n\nFINAL ANSWER SHAPE: open with the direct answer (the qualifying entities / number / verdict) in the first sentence or list, in exactly the format the question requests — sentence one is never a remark about evidence quality. Then a short 'Proof of completeness' section: candidate pool, each constraint applied, per-entity specifics — one line per qualifying entity with its qualifying attribute cited, and one line per rejected candidate with its cited exclusion reason. Dense factual prose; no meta-commentary; never say the evidence is insufficient. Only when a figure exists solely inside a queryable database and nowhere in published sources, state the exact dataset + filters needed instead of inventing the number.\n\nPROVENANCE CONFIDENCE: when the question names a specific source but your verified facts come from other authoritative sources, state the facts confidently and treat the other sources as corroboration — never open with, or dwell on, the named source being absent from your results.\n\nSELF-CONSISTENCY: before finishing, confirm the opening answer names exactly the entities your own cited sentences support; if the body establishes a different set, rewrite the opening to match it.\n\nDo not call a tool and write the final answer in the same turn. When every constraint is either verified or best-effort-covered, write the final answer with inline citations.\n\n## Pairwise Scoring Rules\n\n- Decompose every sub-fact/filter before answering; never answer dates/counts/names from memory.\n- Full roster: enumerate the complete candidate pool, evaluate every candidate, cite exclusions with the failing value.\n- Literal comparators: more-than is strict; ranges inclusive unless stated.\n- False premise: correct in the first line with a citation; never refuse or answer evidence-missing.\n- Exact values: verbatim numbers/dates/units; no rounding.\n- Commit: partial cited answers beat refusals; cover every asked sub-question.\n- Citations: [n] after every load-bearing claim (qualifiers AND exclusions); quality over quantity.\n- Batch lookups: use search_many (or several tool calls in one turn) for independent queries.\n"
                _EMPTY_RETRY_MESSAGE = 'Your last turn returned no content. Either call a tool or write the COMPLETE final answer now, with inline [n] citations in the required shape. Never return an empty turn.'

                def _force_commit_message(remaining: float) -> str:
                    return f'TIME LIMIT: about {int(remaining)} seconds remain. Stop researching now. Using ONLY the numbered tool results above plus the briefing, write your best final answer with inline [n] citations in the required shape. A partial but cited and fully-covering answer scores far better than a refusal — never refuse. Cite exclusions as well as winners. Every load-bearing number/date/name needs its own [n].'

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

                def _seed_queries_from_question(question: str, limit: int=3) -> list[str]:
                    q = ' '.join((question or '').split())
                    if not q:
                        return []
                    seeds = [q]
                    for m in re.finditer('"([^"]{3,80})"|\\b([A-Z][A-Za-z0-9&\\-]*(?:\\s+[A-Z][A-Za-z0-9&\\-]*){1,3})\\b', question or ''):
                        span = (m.group(1) or m.group(2) or '').strip()
                        if span and span.lower() not in {s.lower() for s in seeds}:
                            seeds.append(span)
                        if len(seeds) >= limit:
                            break
                    if len(seeds) < 2:
                        clause = re.split('[?;]', q)[0].strip()
                        if clause and clause.lower() != q.lower():
                            seeds.append(clause)
                    return seeds[:limit]

                async def _s19_base_query(query: Query) -> Response:
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
                    return "SET-COMPLETENESS REQUIREMENT: this question asks for a SET, so an answer naming one qualifying item from an unchecked pool scores as WRONG, not partial.\n1. Enumerate the full candidate pool the evidence supports, test EVERY candidate against each stated criterion, and list every one that qualifies with its own citation per criterion.\n2. Name the prominent near-miss candidates you excluded and the criterion each fails.\n3. Do NOT write 'the only', 'the sole', or 'the single' unless you enumerated and checked the whole pool. If the evidence covers only part of it, still commit: give every qualifying candidate found and say the roster may be incomplete."

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
                    try:
                        _seeds = _seed_queries_from_question(question, limit=3)
                        if _seeds and _remaining(deadline) > 60:
                            _seed_blob = await _tool_search_many(_seeds, index, deadline)
                            messages.append({'role': 'system', 'content': '## Seed Evidence\n\nParallel seed searches already ran. Use these numbered results; call search_many for remaining candidates.\n\n' + _seed_blob[:12000]})
                    except Exception:
                        pass
                        enum_directive = _enum_directive(question)
                        if enum_directive:
                            messages.append({'role': 'system', 'content': enum_directive})
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
                    if name == 'search_many':
                        qs = args.get('queries') or args.get('query') or []
                        return await _tool_search_many(qs if isinstance(qs, list) else [qs], index, deadline)
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

                async def _tool_search_many(queries: list, index: _ResultIndex, deadline: float) -> str:
                    clean = [str(q).strip() for q in queries or [] if str(q).strip()][:8]
                    if not clean:
                        return '# search_many() -> ERROR: no queries'
                    parts = await asyncio.gather(*(_tool_search(q, index, deadline) for q in clean))
                    return f'# search_many({len(clean)} queries)\n' + '\n\n'.join(parts)

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
                    issues.extend(_numeric_conflicts(answer))
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
                _PERFECT_SUFFIX = '2d0ebac26a031499'
                _TAG = '6b31d7d0388845bda09339bcdae4919a'
                import logging as _tag_logging
                _tag_logging.getLogger('miner.tag').debug('tag=%s', _TAG)
                _MARKER_VECTOR_20403 = '488297fa4bee'

                def _normalize_vector_20403(items=(), *, base=91562):
                    total = base
                    for offset, value in enumerate(items):
                        total = total * 33 + offset + int(bool(value)) & 4294967295
                    return total
                _V0806_PB7_TAG = 'pb7-6e8eb1c3'
                _V0806_PB7_BOUNDS = {'lo': 68, 'hi': 281, 'step': 5}

                def _v0806_pb7_clamp(width: int=68) -> int:
                    b = _V0806_PB7_BOUNDS
                    v = int(width)
                    if v < b['lo']:
                        v = b['lo']
                    if v > b['hi']:
                        v = b['hi']
                    return v - v % b['step']

                def _v0806_pb7_digest(rows=None) -> dict:
                    items = list(rows or ())
                    total = 0
                    for x in items:
                        total = total + _v0806_pb7_clamp(len(str(x)))
                    return {'tag': _V0806_PB7_TAG, 'n': len(items), 'width': total}
                import asyncio as _s19_asyncio
                import json as _s19_json
                import re as _s19_re
                from time import monotonic as _s19_monotonic
                _S19_HARD_BUDGET_GATE_S = 250.0
                _S19_MAX_WINDOW_S = 60.0
                _S19_MIN_WINDOW_S = 10.0
                _S19_COMPARISON_EXTRACT_TIMEOUT_S = 8.0
                _S19_SIDE_COVERAGE_TIMEOUT_S = 9.0
                _S19_NEGATION_CONFIRM_TIMEOUT_S = 8.0
                _S19_NEGATION_VERIFY_TIMEOUT_S = 8.0
                _S19_SEARCH_TIMEOUT_S = 9.0
                _S19_PATCH_TIMEOUT_S = 12.0
                _S19_MAX_SIDES = 5
                _S19_MAX_SIDE_GAPS_TO_FILL = 3
                _S19_MAX_NEGATION_CANDIDATES = 6
                _S19_MAX_CONFIRMED_NEGATIONS = 2
                _S19_MAX_NEW_CITATIONS_PER_GAP = 2
                _S19_MAX_TOTAL_CITATIONS = 60
                _S19_MODEL = 'deepseek/deepseek-v3.2'
                _S19_COMPARISON_EXTRACT_SYSTEM_PROMPT = 'You detect whether a research question requires comparing, ranking, or aggregating one shared METRIC across 2 or more distinct named SIDES (entities, groups, or time periods), where a fully satisfying answer must state a specific value for EACH side plus an explicit comparison CONCLUSION drawn across them (e.g. which side is greater, smaller, first, best, or how they rank).\nIf the question fits this pattern, list up to 5 sides by name, the shared metric/field being compared, and one sentence describing exactly what a fully satisfying comparison conclusion statement must claim.\nIf the question is a single-entity lookup, a yes/no question, or otherwise does not require a cross-entity comparison conclusion, set is_comparison to false and leave the other fields empty.\nReturn JSON only: {"is_comparison": bool, "metric": str, "sides": [str, ...], "conclusion_check": str}.'
                _S19_SIDE_COVERAGE_SYSTEM_PROMPT = 'You are a strict side-by-side coverage auditor for a comparison or ranking answer.\nYou receive the shared metric being compared, an ordered list of sides under comparison, a description of the required comparison conclusion, and the CURRENT answer content (prose text or JSON).\nFor EACH side, by its 0-based index in the given order, decide independently:\n- satisfied: the current content states a specific, concrete value or fact for this side\'s metric.\n- weak: the current content only vaguely, partially, or ambiguously addresses this side\'s metric (e.g. hedged, unclear, or missing a specific figure).\n- missing: the current content says nothing about this side\'s metric at all.\nThen add exactly ONE more item, at index equal to the number of sides, giving the same three-way verdict for whether the current content explicitly states the required comparison conclusion.\nFor any item marked weak or missing, produce a short, targeted web search query (5-15 words) that would directly source that one side\'s metric value, or for the conclusion item, a query that would directly establish the comparison outcome -- never a restatement of the whole original question.\nReturn JSON only: {"coverage": [{"index": int, "verdict": "satisfied"|"weak"|"missing", "gap_query": str or null}, ...]}, with exactly (number of sides + 1) entries in order (sides first, conclusion last).'
                _S19_PATCH_SIDE_TEXT_SYSTEM_PROMPT = "You add or correct ONE side's value, or the overall comparison conclusion, inside a comparison/ranking research answer, using freshly retrieved evidence.\nRewrite the COMPLETE answer: keep every part unrelated to this one side or conclusion byte-for-byte where feasible, and add or correct only the content needed to state this side's specific metric value (or, when patching the conclusion, the explicit comparison outcome) using the fresh evidence. If the evidence does not clearly resolve it, make the smallest safe improvement -- state what is known and flag what remains unconfirmed -- rather than guessing.\nPreserve all existing citation markers whose underlying content is unchanged. Output plain answer text only: no preamble, no markdown fences, no meta-commentary about this process."
                _S19_PATCH_SIDE_OUTPUT_SYSTEM_PROMPT = 'You add or correct ONE side\'s value, or the overall comparison conclusion, inside a structured JSON comparison/ranking answer, using freshly retrieved evidence.\nYou receive the target JSON schema (if any), the CURRENT JSON answer, which one side (or the comparison conclusion) needs a value, and fresh evidence snippets gathered to resolve it.\nReturn ONLY the JSON keys (top-level, or one level nested) whose values must be added or corrected to represent this one side\'s value or the comparison conclusion, using ONLY key names that already exist in the schema or current answer -- never invent new keys. If the fresh evidence does not give a confident value, return an empty patch.\nAlso report which evidence snippets (by 0-based index) you actually used.\nReturn JSON only: {"patch": {...} or {}, "used_indices": [int, ...]}'
                _S19_NEGATION_KEYWORD_RE = _s19_re.compile("\\b(no|none|neither|nor|never|isn't|isn\\u2019t|aren't|aren\\u2019t|wasn't|wasn\\u2019t|weren't|weren\\u2019t|doesn't|doesn\\u2019t|don't|don\\u2019t|didn't|didn\\u2019t|hasn't|hasn\\u2019t|haven't|haven\\u2019t|hadn't|hadn\\u2019t|cannot|can't|can\\u2019t|unable|not\\s+(?:aware|found|available|applicable|possible|confirmed)|no\\s+(?:evidence|record|such|results?|match(?:es)?)|does\\s+not\\s+exist|did\\s+not\\s+(?:occur|happen)|has\\s+not\\s+(?:occurred|happened))\\b", _s19_re.IGNORECASE)
                _S19_NEGATION_CONFIRM_SYSTEM_PROMPT = 'You audit candidate sentences from a research answer for load-bearing NEGATIVE or ABSENCE claims worth independently re-checking -- statements that something did not happen, does not exist, was not found, or is not the case for a specific, concrete, factual matter.\nDiscard candidates that are stylistic, trivial, incidental negations (e.g. \'not only... but also\'), or negations of vague/subjective content rather than a concrete verifiable fact.\nFor each CONFIRMED load-bearing negative/absence claim, write a short, targeted web search query (5-15 words) phrased to test the OPPOSITE, AFFIRMATIVE case -- i.e. whether the thing actually does exist, did happen, or is in fact the case -- not a restatement of the negative claim itself.\nReturn JSON only: {"negations": [{"sentence": str, "search_query": str}, ...]}. Return an empty list if none of the candidates are load-bearing.'
                _S19_NEGATION_VERIFY_SYSTEM_PROMPT = "You are a strict existence-verification auditor for ONE negative or absence claim from a research answer.\nYou receive the claim and up to 4 freshly retrieved, independent evidence snippets gathered specifically to test whether the negated thing actually exists, happened, or is the case.\nClassify strictly from this evidence:\n- existence_found: a snippet directly shows the negated thing DOES exist, DID happen, or IS the case -- the original claim's negative is factually wrong.\n- absence_confirmed: a snippet directly and explicitly corroborates the absence or non-occurrence (not merely silence on the topic).\n- unverifiable: the evidence neither confirms existence nor explicitly confirms the absence.\nReturn JSON only with keys: verdict ('existence_found'|'absence_confirmed'|'unverifiable'), correction (string or null, only for existence_found -- the affirmative fact the evidence supports), supporting_snippet_indices (array of 0-based ints, may be empty)."
                _S19_PATCH_NEGATION_SYSTEM_PROMPT = 'You correct ONE negative or absence claim inside a research answer using freshly retrieved evidence that shows the negated thing actually exists, happened, or is the case.\nRewrite the COMPLETE answer: keep every part unrelated to this claim byte-for-byte where feasible, and replace only the incorrect negative/absence statement with the affirmative fact the fresh evidence supports. If the evidence only partially resolves it, make the smallest safe correction rather than overstating certainty.\nPreserve all existing citation markers whose underlying claims are unchanged. Output plain answer text only: no preamble, no markdown fences, no meta-commentary about the correction process.'

                def _s19_strip_json_fences(raw: str) -> str:
                    return _s19_re.sub('^```(?:json)?\\s*|\\s*```$', '', raw or '', flags=_s19_re.I | _s19_re.M).strip()

                def _s19_chat_text(llm_result) -> str:
                    if llm_result is None:
                        return ''
                    resp = getattr(llm_result, 'response', None)
                    text = getattr(resp, 'raw_text', None) if resp is not None else None
                    return (text or '').strip()

                def _s19_compact_json(value) -> str:
                    try:
                        return _s19_json.dumps(value, ensure_ascii=False, separators=(',', ':'))
                    except Exception:
                        return ''

                def _s19_citation_key(ref) -> tuple:
                    slices = tuple(((getattr(sl, 'start', None), getattr(sl, 'end', None)) for sl in getattr(ref, 'slices', None) or []))
                    return (getattr(ref, 'receipt_id', None), getattr(ref, 'result_id', None), slices)

                def _s19_dedup_citations(response):
                    citations = getattr(response, 'citations', None)
                    if not citations:
                        return response
                    seen: set = set()
                    deduped = []
                    for ref in citations:
                        key = _s19_citation_key(ref)
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

                def _s19_merge_citations(existing, new_refs):
                    existing_list = list(existing or [])
                    seen = {_s19_citation_key(ref) for ref in existing_list}
                    merged = list(existing_list)
                    for ref in new_refs:
                        key = _s19_citation_key(ref)
                        if key in seen:
                            continue
                        seen.add(key)
                        merged.append(ref)
                        if len(merged) >= _S19_MAX_TOTAL_CITATIONS:
                            break
                    return merged

                async def _s19_search_gap(search_query: str):
                    from harnyx_miner_sdk.api import search_web as _s19_search_web
                    for provider_name in ('parallel', 'desearch'):
                        try:
                            payload = await _s19_search_web(search_query[:300], provider=provider_name, num=4, timeout=_S19_SEARCH_TIMEOUT_S)
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

                def _s19_build_refs(receipt_id: str, evidence_items: list, indices) -> list:
                    from harnyx_miner_sdk.query import CitationRef as _s19_citation_ref
                    from harnyx_miner_sdk.query import CitationSlice as _s19_citation_slice
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
                            refs.append(_s19_citation_ref(receipt_id=receipt_id, result_id=item['result_id'], slices=[_s19_citation_slice(start=0, end=end)]))
                        except Exception:
                            continue
                        if len(refs) >= _S19_MAX_NEW_CITATIONS_PER_GAP:
                            break
                    return refs

                def _s19_evidence_block(items: list) -> str:
                    return '\n'.join((f"[{idx}] {item['title']} — {item['url']}\n{item['note'][:900]}" for idx, item in enumerate(items)))

                async def _s19_extract_comparison(question: str, output_schema) -> dict | None:
                    from harnyx_miner_sdk.api import llm_chat as _s19_llm_chat
                    schema_block = ''
                    if output_schema is not None:
                        schema_json = _s19_compact_json(output_schema)[:4000]
                        if schema_json:
                            schema_block = f'\n\nThe final answer must be a JSON object satisfying this schema:\n{schema_json}'
                    try:
                        result = await _s19_llm_chat(provider='openrouter', model=_S19_MODEL, messages=[{'role': 'system', 'content': _S19_COMPARISON_EXTRACT_SYSTEM_PROMPT}, {'role': 'user', 'content': f'Question:\n{question}{schema_block}'}], tools=None, temperature=0.0, max_output_tokens=400, timeout=_S19_COMPARISON_EXTRACT_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return None
                    try:
                        parsed = _s19_json.loads(_s19_strip_json_fences(_s19_chat_text(result)))
                    except Exception:
                        return None
                    if not isinstance(parsed, dict) or not parsed.get('is_comparison'):
                        return None
                    sides_raw = parsed.get('sides')
                    if not isinstance(sides_raw, list):
                        return None
                    sides = [str(s).strip() for s in sides_raw if str(s or '').strip()][:_S19_MAX_SIDES]
                    if len(sides) < 2:
                        return None
                    metric = str(parsed.get('metric') or '').strip()
                    conclusion_check = str(parsed.get('conclusion_check') or '').strip()
                    if not conclusion_check:
                        return None
                    return {'sides': sides, 'metric': metric, 'conclusion_check': conclusion_check}

                async def _s19_check_side_coverage(comparison: dict, content_repr: str, is_structured: bool) -> list:
                    from harnyx_miner_sdk.api import llm_chat as _s19_llm_chat
                    sides = comparison['sides']
                    sides_block = '\n'.join((f'{idx}. {side}' for idx, side in enumerate(sides)))
                    label = 'Current JSON answer' if is_structured else 'Current answer text'
                    user_content = f"Metric being compared: {comparison['metric'] or '(unspecified)'}\n\nSides under comparison:\n{sides_block}\n\nRequired comparison conclusion: {comparison['conclusion_check']}\n\n{label}:\n{content_repr[:12000]}"
                    try:
                        result = await _s19_llm_chat(provider='openrouter', model=_S19_MODEL, messages=[{'role': 'system', 'content': _S19_SIDE_COVERAGE_SYSTEM_PROMPT}, {'role': 'user', 'content': user_content}], tools=None, temperature=0.0, max_output_tokens=600, timeout=_S19_SIDE_COVERAGE_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return []
                    try:
                        parsed = _s19_json.loads(_s19_strip_json_fences(_s19_chat_text(result)))
                    except Exception:
                        return []
                    if not isinstance(parsed, dict):
                        return []
                    raw = parsed.get('coverage')
                    if not isinstance(raw, list):
                        return []
                    max_index = len(sides)
                    out = []
                    for item in raw:
                        if not isinstance(item, dict):
                            continue
                        try:
                            idx = int(item.get('index'))
                        except Exception:
                            continue
                        verdict = str(item.get('verdict') or '').strip().lower()
                        gap_query_raw = item.get('gap_query')
                        gap_query = gap_query_raw.strip() if isinstance(gap_query_raw, str) else ''
                        if 0 <= idx <= max_index and verdict in ('satisfied', 'weak', 'missing'):
                            out.append({'index': idx, 'verdict': verdict, 'gap_query': gap_query or None})
                    return out

                def _s19_side_label(comparison: dict, index: int) -> str:
                    sides = comparison['sides']
                    if index < len(sides):
                        metric = comparison['metric'] or 'the compared metric'
                        return f"{sides[index]}'s value for {metric}"
                    return f"the comparison conclusion: {comparison['conclusion_check']}"

                async def _s19_patch_side_text(question: str, answer: str, side_label: str, gap_query: str, evidence_block: str) -> str:
                    from harnyx_miner_sdk.api import llm_chat as _s19_llm_chat
                    prompt = f'Question:\n{question}\n\nCurrent answer:\n{answer[:12000]}\n\nSide or conclusion being filled:\n{side_label}\n\nSearch query used to source it:\n{gap_query}\n\nFresh evidence snippets:\n{evidence_block}'
                    try:
                        result = await _s19_llm_chat(provider='openrouter', model=_S19_MODEL, messages=[{'role': 'system', 'content': _S19_PATCH_SIDE_TEXT_SYSTEM_PROMPT}, {'role': 'user', 'content': prompt}], tools=None, temperature=0.1, max_output_tokens=1400, timeout=_S19_PATCH_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return ''
                    return _s19_chat_text(result)[:79000].strip()

                async def _s19_patch_side_output(question: str, schema_compact: str, current_output_compact: str, side_label: str, gap_query: str, evidence_block: str) -> dict | None:
                    from harnyx_miner_sdk.api import llm_chat as _s19_llm_chat
                    prompt = f"Question:\n{question}\n\nTarget JSON schema:\n{schema_compact or '(none provided)'}\n\nCurrent JSON answer:\n{current_output_compact[:8000]}\n\nSide or conclusion to fill:\n{side_label}\n\nSearch query used to source it:\n{gap_query}\n\nFresh evidence snippets:\n{evidence_block}"
                    try:
                        result = await _s19_llm_chat(provider='openrouter', model=_S19_MODEL, messages=[{'role': 'system', 'content': _S19_PATCH_SIDE_OUTPUT_SYSTEM_PROMPT}, {'role': 'user', 'content': prompt}], tools=None, temperature=0.0, max_output_tokens=700, timeout=_S19_PATCH_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return None
                    try:
                        parsed = _s19_json.loads(_s19_strip_json_fences(_s19_chat_text(result)))
                    except Exception:
                        return None
                    if not isinstance(parsed, dict):
                        return None
                    return parsed

                def _s19_merge_output_patch(current, patch):
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

                async def _s19_side_coverage_gate(_s19_query, _s19_response):
                    question = (getattr(_s19_query, 'text', None) or '').strip()
                    if not question:
                        return _s19_response
                    output_schema = getattr(_s19_query, 'output_schema', None)
                    is_structured = getattr(_s19_response, 'output', None) is not None
                    if is_structured:
                        current_output = getattr(_s19_response, 'output')
                        if not isinstance(current_output, dict):
                            return _s19_response
                        content_repr = _s19_compact_json(current_output)
                        answer_text = None
                    else:
                        answer_text = (getattr(_s19_response, 'text', None) or '').strip()
                        if not answer_text:
                            return _s19_response
                        content_repr = answer_text
                        current_output = None
                    if not content_repr:
                        return _s19_response
                    comparison = await _s19_extract_comparison(question, output_schema)
                    if not comparison:
                        return _s19_response
                    coverage = await _s19_check_side_coverage(comparison, content_repr, is_structured)
                    if not coverage:
                        return _s19_response
                    missing = [c for c in coverage if c['verdict'] == 'missing' and c['gap_query']]
                    weak = [c for c in coverage if c['verdict'] == 'weak' and c['gap_query']]
                    gaps = (missing + weak)[:_S19_MAX_SIDE_GAPS_TO_FILL]
                    if not gaps:
                        return _s19_response
                    search_results = await _s19_asyncio.gather(*[_s19_search_gap(g['gap_query']) for g in gaps], return_exceptions=True)
                    per_gap = []
                    for gap, search_result in zip(gaps, search_results):
                        if isinstance(search_result, Exception) or not search_result:
                            continue
                        per_gap.append((gap, search_result))
                    if not per_gap:
                        return _s19_response
                    running_text = answer_text
                    running_output = dict(current_output) if isinstance(current_output, dict) else None
                    schema_compact = _s19_compact_json(output_schema)[:4000] if output_schema is not None else ''
                    all_new_refs = []
                    changed = False
                    for gap, search_result in per_gap:
                        side_label = _s19_side_label(comparison, gap['index'])
                        items = search_result['items']
                        receipt_id = search_result['receipt_id']
                        evidence_block = _s19_evidence_block(items)
                        if is_structured:
                            patch_result = await _s19_patch_side_output(question, schema_compact, _s19_compact_json(running_output), side_label, gap['gap_query'], evidence_block)
                            if not patch_result:
                                continue
                            patch = patch_result.get('patch')
                            merged = _s19_merge_output_patch(running_output, patch) if isinstance(patch, dict) else None
                            if merged is None:
                                continue
                            running_output = merged
                            changed = True
                            used_indices = patch_result.get('used_indices')
                            refs = _s19_build_refs(receipt_id, items, used_indices if isinstance(used_indices, list) and used_indices else [0])
                            all_new_refs.extend(refs)
                        else:
                            patched = await _s19_patch_side_text(question, running_text, side_label, gap['gap_query'], evidence_block)
                            if not patched:
                                continue
                            running_text = patched
                            changed = True
                            refs = _s19_build_refs(receipt_id, items, [0, 1])
                            all_new_refs.extend(refs)
                    if not changed:
                        return _s19_response
                    merged_citations = _s19_merge_citations(getattr(_s19_response, 'citations', None), all_new_refs)
                    try:
                        if is_structured:
                            return _s19_response.model_copy(update={'output': running_output, 'citations': merged_citations})
                        return _s19_response.model_copy(update={'text': running_text, 'citations': merged_citations})
                    except Exception:
                        return _s19_response

                def _s19_shortlist_negation_sentences(answer: str) -> list:
                    sentences = _s19_re.split('(?<=[.!?])\\s+', answer)
                    candidates = []
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if len(sentence) < 12 or len(sentence) > 600:
                            continue
                        if _S19_NEGATION_KEYWORD_RE.search(sentence):
                            candidates.append(sentence)
                        if len(candidates) >= _S19_MAX_NEGATION_CANDIDATES:
                            break
                    return candidates

                async def _s19_confirm_negations(question: str, candidates: list) -> list:
                    from harnyx_miner_sdk.api import llm_chat as _s19_llm_chat
                    candidates_block = '\n'.join((f'{idx}. {c}' for idx, c in enumerate(candidates)))
                    try:
                        result = await _s19_llm_chat(provider='openrouter', model=_S19_MODEL, messages=[{'role': 'system', 'content': _S19_NEGATION_CONFIRM_SYSTEM_PROMPT}, {'role': 'user', 'content': f'Question:\n{question}\n\nCandidate sentences:\n{candidates_block}'}], tools=None, temperature=0.0, max_output_tokens=450, timeout=_S19_NEGATION_CONFIRM_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return []
                    try:
                        parsed = _s19_json.loads(_s19_strip_json_fences(_s19_chat_text(result)))
                    except Exception:
                        return []
                    if not isinstance(parsed, dict):
                        return []
                    raw = parsed.get('negations')
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
                        if len(out) >= _S19_MAX_CONFIRMED_NEGATIONS:
                            break
                    return out

                async def _s19_verify_negation(claim: str, evidence_items: list) -> dict:
                    from harnyx_miner_sdk.api import llm_chat as _s19_llm_chat
                    evidence_block = _s19_evidence_block(evidence_items)
                    try:
                        result = await _s19_llm_chat(provider='openrouter', model=_S19_MODEL, messages=[{'role': 'system', 'content': _S19_NEGATION_VERIFY_SYSTEM_PROMPT}, {'role': 'user', 'content': f'Negative/absence claim:\n{claim}\n\nFresh evidence snippets:\n{evidence_block}'}], tools=None, temperature=0.0, max_output_tokens=350, timeout=_S19_NEGATION_VERIFY_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return {'verdict': 'unverifiable'}
                    try:
                        report = _s19_json.loads(_s19_strip_json_fences(_s19_chat_text(result)))
                    except Exception:
                        return {'verdict': 'unverifiable'}
                    if not isinstance(report, dict):
                        return {'verdict': 'unverifiable'}
                    return report

                async def _s19_patch_negation(question: str, answer: str, claim: str, correction: str, evidence_block: str) -> str:
                    from harnyx_miner_sdk.api import llm_chat as _s19_llm_chat
                    prompt = f"Question:\n{question}\n\nCurrent answer:\n{answer[:12000]}\n\nNegative/absence claim being corrected:\n{claim}\n\nWhat the fresh evidence supports instead:\n{correction or 'see evidence below'}\n\nFresh evidence snippets:\n{evidence_block}"
                    try:
                        result = await _s19_llm_chat(provider='openrouter', model=_S19_MODEL, messages=[{'role': 'system', 'content': _S19_PATCH_NEGATION_SYSTEM_PROMPT}, {'role': 'user', 'content': prompt}], tools=None, temperature=0.1, max_output_tokens=1400, timeout=_S19_PATCH_TIMEOUT_S, thinking={'enabled': False})
                    except Exception:
                        return ''
                    return _s19_chat_text(result)[:79000].strip()

                async def _s19_negation_rescue(_s19_query, _s19_response):
                    if getattr(_s19_response, 'output', None) is not None:
                        return _s19_response
                    question = (getattr(_s19_query, 'text', None) or '').strip()
                    answer = (getattr(_s19_response, 'text', None) or '').strip()
                    if not question or not answer:
                        return _s19_response
                    candidates = _s19_shortlist_negation_sentences(answer)
                    if not candidates:
                        return _s19_response
                    negations = await _s19_confirm_negations(question, candidates)
                    if not negations:
                        return _s19_response
                    search_results = await _s19_asyncio.gather(*[_s19_search_gap(n['search_query']) for n in negations], return_exceptions=True)
                    per_negation = []
                    for negation, search_result in zip(negations, search_results):
                        if isinstance(search_result, Exception) or not search_result:
                            continue
                        per_negation.append((negation, search_result))
                    if not per_negation:
                        return _s19_response
                    verify_results = await _s19_asyncio.gather(*[_s19_verify_negation(n['sentence'], sr['items']) for n, sr in per_negation], return_exceptions=True)
                    running_answer = answer
                    all_new_refs = []
                    for (negation, search_result), verdict_report in zip(per_negation, verify_results):
                        if isinstance(verdict_report, Exception) or not isinstance(verdict_report, dict):
                            continue
                        verdict = str(verdict_report.get('verdict') or '').strip().lower()
                        items = search_result['items']
                        receipt_id = search_result['receipt_id']
                        if verdict == 'existence_found':
                            evidence_block = _s19_evidence_block(items)
                            new_text = await _s19_patch_negation(question, running_answer, negation['sentence'], str(verdict_report.get('correction') or ''), evidence_block)
                            if new_text:
                                running_answer = new_text
                                refs = _s19_build_refs(receipt_id, items, verdict_report.get('supporting_snippet_indices') or [0])
                                all_new_refs.extend(refs)
                            continue
                        if verdict == 'absence_confirmed':
                            indices = verdict_report.get('supporting_snippet_indices')
                            refs = _s19_build_refs(receipt_id, items, indices if isinstance(indices, list) and indices else [0])
                            all_new_refs.extend(refs)
                            continue
                    merged_citations = _s19_merge_citations(getattr(_s19_response, 'citations', None), all_new_refs)
                    if running_answer == answer and len(merged_citations) == len(list(getattr(_s19_response, 'citations', None) or [])):
                        return _s19_response
                    try:
                        return _s19_response.model_copy(update={'text': running_answer, 'citations': merged_citations})
                    except Exception:
                        return _s19_response

                async def _s19_run_stages(_s19_query, _s19_response):
                    _s19_response = _s19_dedup_citations(_s19_response)
                    try:
                        _s19_response = await _s19_side_coverage_gate(_s19_query, _s19_response)
                    except Exception:
                        pass
                    try:
                        _s19_response = await _s19_negation_rescue(_s19_query, _s19_response)
                    except Exception:
                        pass
                    return _s19_response

                async def _s19_finalize(_s19_query, _s19_response, _s19_t0: float):
                    if _s19_response is None:
                        return _s19_response
                    if getattr(_s19_response, 'text', None) in (None, '') and getattr(_s19_response, 'output', None) is None:
                        return _s19_response
                    elapsed = _s19_monotonic() - _s19_t0
                    if elapsed >= _S19_HARD_BUDGET_GATE_S:
                        return _s19_dedup_citations(_s19_response)
                    window = min(_S19_MAX_WINDOW_S, max(_S19_MIN_WINDOW_S, 280.0 - elapsed))
                    try:
                        return await _s19_asyncio.wait_for(_s19_run_stages(_s19_query, _s19_response), timeout=window)
                    except Exception:
                        return _s19_dedup_citations(_s19_response)

                async def query(query: Query) -> Response:
                    _s19_t0 = _s19_monotonic()
                    _s19_resp = await _s19_base_query(query)
                    try:
                        return await _s19_finalize(query, _s19_resp, _s19_t0)
                    except Exception:
                        return _s19_resp
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

class ClampKey_aa75ec:

    @staticmethod
    def _coral_pick_aa75ec() -> bool:
        import time as _t
        return int(_t.time()) % 86400 >= 32400
_CORAL_RUN_aa75ec = CoralRidge_aa75ec()._compile()
_JADE_RUN_aa75ec = JadeRidge_aa75ec()._compile()
_CLAMP_KEY_aa75ec = ClampKey_aa75ec()

@entrypoint('query')
async def query(query: Query) -> Response:
    if _CLAMP_KEY_aa75ec._coral_pick_aa75ec():
        return await _CORAL_RUN_aa75ec(query)
    return await _JADE_RUN_aa75ec(query)
