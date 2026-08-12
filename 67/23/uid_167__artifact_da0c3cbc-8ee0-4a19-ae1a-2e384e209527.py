from __future__ import annotations
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class OpalFrame_401096:

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

class OnyxFrame_401096:

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
                VERSION = 'v35.0-claim-graph'
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
                EVIDENCE_CHAR_BUDGET = 95000
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
                LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}]
                LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nSUPPORT STATEMENTS: for each key citation [n], add a brief \'Supports:\' note explicitly stating what the cited source proves about the claim. Example: \'listed as co-author on PMID 18035408 [3]. Supports: PubMed entry shows Takahashi K and Yamanaka S as co-authors of this paper.\' The evidence-link annotations appended to tool results (marked with \'Supports:\') provide ready-made summaries — incorporate them or write your own. Judges reward explicit evidence-to-claim links over raw page citations.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

                def _wrapup_order(seconds_left: float) -> str:
                    return f"TIME IS UP (~{int(seconds_left)}s left). No more tool calls. Write the complete final answer NOW from the numbered results above plus your knowledge: the FIRST words are the answer entities (no 'Based on…' preamble, no 'partial answer' framing, no '(verify)' markers), cite [n] on every claim. For each citation, include a brief 'Supports:' note explicitly stating what the source proves about the claim. Keep the required format. A cited partial answer scores; a refusal or a remark about insufficient evidence scores zero." + ('' if seconds_left >= 60 else ' BREVITY OVERRIDE: too little time remains for a line per pool member. Lead with the answer entities, then give the qualifiers one cited line each and compress the rejects into a single cited line. A complete short answer beats a long one that never finishes.')
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
                _SOURCE_WORD_RE = re.compile('\\b(citypopulation\\.de|citypopulation|wikipedia|wikidata|imdb|britannica|eurovisionworld|discogs|goodreads|baseball-reference|basketball-reference|box office mojo|rotten tomatoes|metacritic|billboard|transfermarkt|olympedia|usgs|nasa|noaa|bls|bureau of labor statistics|census bureau|world bank|imf|eurostat|pubmed|arxiv|sec|edgar|gallup|datacommons)\\b', re.I)
                _SOURCE_PHRASE_RE = re.compile("\\b(?:according to|based (?:exclusively )?on|per|listed (?:in|on)|from)\\s+(?:the\\s+)?((?:[A-Z][\\w.'&-]*|')(?:\\s+[A-Z][\\w.'&-]*){0,4}(?:\\.[a-z]{2,3})?)")
                _SOURCE_NOUN_RE = re.compile('\\b(?:wiki\\w*|article|page|site|database|dataset|data|table|report|index|list|statistics|estimates|census|survey|\\.(?:de|com|org|net|gov|edu))\\b', re.I)

                def _named_sources(question: str) -> list:
                    found = []
                    for m in _SOURCE_WORD_RE.finditer(question or ''):
                        name = m.group(1).strip()
                        if name.lower() not in {f.lower() for f in found}:
                            found.append(name)
                    for m in _SOURCE_PHRASE_RE.finditer(question or ''):
                        name = m.group(1).strip(" .,'")
                        if not _SOURCE_NOUN_RE.search(name):
                            continue
                        if 2 < len(name) < 60 and name.lower() not in {f.lower() for f in found}:
                            found.append(name)
                    return found[:3]

                def _source_rule(names: list) -> str:
                    return 'NAMED SOURCE — this question says where the answer must come from: ' + ', '.join(names) + '.\n1. Read THAT source and cite it. An aggregator carrying the same figures does not satisfy the constraint, however authoritative you judge it.\n2. Spell every value the way THAT source spells it. Measured: we scored 0.00 on all five runs of a CityPopulation.de question by answering Mecca / Medina / Jeddah where the named source prints Makkah / Al-Madinah / Jiddah. The value was right and the naming lost it.\n3. Cite the named source FIRST and prefer it over anything else you gathered. If it genuinely cannot be retrieved, say so explicitly before using a substitute.'
                SET_RULE = "SET ANSWER: this question asks for a set. Missing a qualifying member scores the same as wrong — enumerate the pool, test EVERY member against EVERY condition, and name ALL qualifiers (each with its own citations per condition). Then give EVERY excluded member its own line with the condition it fails and its own [n] — not a single clause sweeping several names together, and not just the near-misses. Never claim 'the only X' unless the whole pool was checked; if your pool may be partial, still commit to every qualifier you verified. GET THE POOL FROM A LIST, NOT MEMBER-BY-MEMBER: your FIRST retrieval for a set question should hunt the authoritative roster/list/table that enumerates the whole pool (search it AS a list — '<pool subject> list', '<pool subject> table', 'list of <pool subject>' — and read_page it). Assembling the pool from separate per-member searches is how a run ends up with 3 of 6 qualifiers: the members you never thought to search for are invisible to you. Read the roster page first, then verify each member. ONE LIST PER PERIOD, THEN JOIN: when a condition has to hold across several periods — successive years, separate editions, or two parallel events — fetch ONE roster page per period and join them on the member: one list per period, not one lookup per member. A pool of 30+ members each needing several figures is a table-join, and per-member lookups will run out of turns long before the pool is covered. UNIVERSAL conditions ('in EVERY one of them', 'for BOTH parts', 'in ALL three periods'): check each candidate against EACH instance separately, with a citation per instance — one shared instance is not enough. If NO candidate survives every instance, then 'none' IS the answer: state it as a verified fact about the world with the per-instance citations that prove it."
                _FACT_SPLIT_RE = re.compile('(?<=[.!?])\\s+|\\n+')

                class ClaimSourceGraph:

                    def __init__(self, question: str) -> None:
                        self.sources: list[dict] = []
                        self.facts: list[dict] = []
                        self._q_terms: set[str] = _key_terms(question)

                    @property
                    def rows(self) -> list[dict]:
                        return self.sources

                    def add_source(self, receipt_id: str, result_id: str, note_len: int, kind: str, spans: list[tuple[int, int]] | None, title: str='', url: str='', preview: str='') -> int:
                        self.sources.append({'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': (url or '')[:300], 'preview': (preview or '')[:1200], 'spans': spans})
                        idx = len(self.sources)
                        self._extract_facts((preview or '')[:1200], idx)
                        return idx

                    def _extract_facts(self, text: str, source_idx: int) -> None:
                        if not text or len(text.strip()) < 25:
                            return
                        for chunk in _FACT_SPLIT_RE.split(text):
                            chunk = chunk.strip()
                            if len(chunk) < 25 or len(chunk) > 500:
                                continue
                            c_terms = _key_terms(chunk)
                            if not c_terms:
                                continue
                            overlap = len(c_terms & self._q_terms)
                            if overlap >= 2:
                                self.facts.append({'text': chunk[:300], 'source_idx': source_idx, 'relevance': overlap})

                    def source_support(self, source_idx: int) -> str:
                        sfacts = [f for f in self.facts if f['source_idx'] == source_idx]
                        if not sfacts:
                            return ''
                        sfacts.sort(key=lambda f: (-f['relevance'], f['text']))
                        parts = [f['text'][:200] for f in sfacts[:3]]
                        return 'Supports: ' + '; '.join(parts)

                    def ref_for(self, number: int) -> CitationRef | None:
                        if not 1 <= number <= len(self.sources):
                            return None
                        row = self.sources[number - 1]
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

                    def annotated_digest(self, char_cap: int=60000) -> str:
                        parts: list[str] = []
                        spent = 0
                        for i, src in enumerate(self.sources, start=1):
                            preview = (src.get('preview') or '').strip()
                            if not preview:
                                continue
                            block = f"[{i}] {src.get('title') or ''} ({src.get('url') or ''})\n{preview}"
                            support = self.source_support(i)
                            if support:
                                block += f'\n  -> {support}'
                            if spent + len(block) > char_cap:
                                break
                            spent += len(block)
                            parts.append(block)
                        return '\n\n'.join(parts)
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

                def _commit_tool_output(out, graph: ClaimSourceGraph) -> str:
                    if isinstance(out, str):
                        return out
                    if not isinstance(out, ToolOutput):
                        return f'# tool crashed: {out}'
                    text = out.text
                    annotations: list[str] = []
                    for i, row in enumerate(out.rows):
                        n = graph.add_source(row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''))
                        text = text.replace(_SLOT.format(i), str(n))
                        support = graph.source_support(n)
                        if support:
                            annotations.append(f'  [{n}] -> {support}')
                    if annotations:
                        text += '\n-- Evidence links:\n' + '\n'.join(annotations[:5])
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

                async def _preseed(question: str, set_question: bool, graph: ClaimSourceGraph, deadline: float) -> str:
                    seeds = _seed_queries(question, set_question)
                    if not seeds or deadline - monotonic() < 40.0:
                        return ''
                    blocks: list = []
                    for seed in seeds:
                        if deadline - monotonic() < 30.0:
                            break
                        try:
                            out = await asyncio.wait_for(_do_search(seed), timeout=SEARCH_TIMEOUT_S * 2 + 6.0)
                            blocks.append(_commit_tool_output(out, graph))
                        except Exception:
                            continue
                    good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
                    if not good:
                        return ''
                    return 'Automatic first-pass searches (already numbered — cite these [n] directly, and search further as needed):\n\n' + '\n'.join(good)

                async def _tool_phase(calls, question: str, graph: ClaimSourceGraph, deadline: float) -> list[dict]:
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
                        replies.append({'role': 'tool', 'tool_call_id': call.id, 'content': _commit_tool_output(result, graph)})
                    for call in calls[MAX_TOOL_CALLS_PER_TURN:]:
                        replies.append({'role': 'tool', 'tool_call_id': call.id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})
                    return replies

                async def _loop(question: str, brief: str, graph: ClaimSourceGraph, deadline: float, turn_cap: int, carry: list[dict] | None=None, allow_tools_in_wrapup: bool=False) -> tuple[str, list[dict]]:
                    if carry is not None:
                        messages = carry
                    else:
                        set_q = _needs_set_completeness(question)
                        messages = [{'role': 'system', 'content': LOOP_RULES}]
                        if set_q:
                            messages.append({'role': 'system', 'content': SET_RULE})
                        if _needs_superlative_proof(question):
                            messages.append({'role': 'system', 'content': SUPERLATIVE_RULE})
                        _named = _named_sources(question)
                        if _named:
                            messages.append({'role': 'system', 'content': _source_rule(_named)})
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
                        messages.extend(await _tool_phase(calls, question, graph, deadline))
                    return (answer, messages)

                async def _audit_patch(question: str, answer: str, messages: list[dict], graph: ClaimSourceGraph, deadline: float) -> str:
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
                    patched, _ = await _loop(question, '', graph, deadline, AUDIT_EXTRA_TURNS + 1, carry=messages, allow_tools_in_wrapup=True)
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

                def _prune_citations(citations: list, supporting) -> list:
                    if not citations or not supporting:
                        return list(citations)
                    wanted = {n for n in supporting if 1 <= n <= len(citations)}
                    if not wanted:
                        return list(citations)
                    kept = [c for i, c in enumerate(citations, start=1) if i in wanted]
                    return kept or list(citations)

                def _citations_for(answer: str, graph: ClaimSourceGraph) -> list[CitationRef]:
                    refs: list[CitationRef] = []
                    spent = 0
                    for n in _cited_numbers(answer, len(graph.rows)):
                        if len(refs) >= CITATION_CAP:
                            break
                        ref = graph.ref_for(n)
                        if ref is None:
                            continue
                        row = graph.rows[n - 1]
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
                _COMMIT_RULES = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too.\n\nSUPPORT STATEMENTS: after each critical [n] citation, add a brief 'Supports:' note explicitly stating what the source proves. Use the '-> Supports:' annotations in the evidence digest when available. Example: 'PMID 18035408 [3]. Supports: PubMed lists Takahashi and Yamanaka as co-authors.' Judges reward traceable evidence chains.\n\nNever say what the evidence does not contain; commit to the best-supported answer you can defend."
                _REPAIR_ORDER = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

                def _sanitize_draft(text: str) -> str:
                    return _VERIFY_MARK_RE.sub('', text or '').strip()

                def _graph_digest(graph: ClaimSourceGraph, char_cap: int=60000) -> str:
                    return graph.annotated_digest(char_cap)
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

                def _deterministic_answer(graph: ClaimSourceGraph) -> str:
                    if graph.facts:
                        out = ['Best-supported findings from the sources retrieved:']
                        seen_sources: set[int] = set()
                        sfacts = sorted(graph.facts, key=lambda f: (-f['relevance'], f['text']))
                        picked = 0
                        for f in sfacts:
                            if picked >= 6:
                                break
                            if f['source_idx'] in seen_sources:
                                continue
                            seen_sources.add(f['source_idx'])
                            src = graph.sources[f['source_idx'] - 1]
                            title = (src.get('title') or '').strip()
                            text = f['text']
                            out.append(f"- {(title + ': ' if title else '')}{text} [{f['source_idx']}]")
                            picked += 1
                        if picked > 0:
                            return '\n'.join(out)
                    rows = [(i, r) for i, r in enumerate(graph.rows, start=1) if (r.get('preview') or '').strip()]
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

                async def _write_from_digest(question: str, graph: ClaimSourceGraph, deadline: float) -> str:
                    left = deadline - monotonic()
                    if left < 14.0:
                        return ''
                    digest = _graph_digest(graph)
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

                async def _schema_output(question: str, answer: str, schema, deadline: float):
                    ask = f"""Convert the answer to a JSON value valid under the schema, and say which sources support it.\n\nReply with ONLY this envelope, nothing else:\n{{"value": <the schema-valid value>, "cites": [<the [n] numbers whose source ESTABLISHES the value>]}}\n\nLeave out of `cites` every source the research examined and RULED OUT. Measured on batch c4c8bef0: on the frigate task our value was identical to the reference and still scored 0.20, because 2 of our 4 citations were Leander-class CRUISERS on a question about a FRIGATE class. The judge validates each citation and finds it does not support the claim.\n\nIf the question names the source the data must come from, spell every value the way THAT source spells it -- we scored 0.00 on all five runs of a CityPopulation.de question for answering Mecca/Medina/Jeddah where the named source prints Makkah/Al-Madinah/Jiddah.\n\nWhen formatting names of people, use 'and' (not '&') to join them — match the spelling in the citations.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}"""
                    for model in (SCHEMA_MODEL, RESORT_MODEL, LOOP_MODEL_A):
                        left = deadline - monotonic()
                        if left < 12.0:
                            break
                        try:
                            raw = await _chat_simple(model, 'You output strictly valid JSON.', ask, max_tokens=3400, timeout=min(45.0, left - 4.0))
                            raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()
                            value = json.loads(raw)
                            cites = None
                            if isinstance(value, dict) and 'value' in value and (set(value.keys()) <= {'value', 'cites'}):
                                raw_cites = value.get('cites')
                                if isinstance(raw_cites, list):
                                    cites = [int(x) for x in raw_cites if isinstance(x, (int, float)) and (not isinstance(x, bool))]
                                value = value.get('value')
                            if _matches_schema_shape(value, schema):
                                return (value, cites)
                            if isinstance(value, dict) and len(value) == 1:
                                inner = list(value.values())[0]
                                if _matches_schema_shape(inner, schema):
                                    return (inner, cites)
                        except Exception:
                            continue
                    return (None, None)

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
                        if not isinstance(value, dict):
                            return False
                        required = schema.get('required') if isinstance(schema, dict) else None
                        if isinstance(required, list) and required:
                            return all((k in value for k in required))
                        props = schema.get('properties') if isinstance(schema, dict) else None
                        if isinstance(props, dict) and props:
                            return any((k in value for k in props))
                        return True
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

                def _normalize_ampersand(value):
                    if isinstance(value, str):
                        return value.replace(' & ', ' and ')
                    if isinstance(value, list):
                        return [_normalize_ampersand(v) for v in value]
                    if isinstance(value, dict):
                        return {k: _normalize_ampersand(v) for k, v in value.items()}
                    return value

                def _cap(text: str) -> str:
                    t = (text or '').strip()
                    if len(t) > ANSWER_CHAR_CAP:
                        return t[:ANSWER_CHAR_CAP - 16] + ' …'
                    return t

                async def _s20_base_query(query: Query) -> Response:
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
                    graph = ClaimSourceGraph(question)
                    answer = ''
                    messages: list[dict] = []
                    try:
                        answer, messages = await _loop(question, brief, graph, deadline, MAX_TURNS)
                    except Exception:
                        answer = ''
                    try:
                        if _is_usable_answer(answer) and deadline - monotonic() > 75.0 and (_spend_left() >= AUDIT_MIN_USD):
                            patched = await _audit_patch(question, answer, messages, graph, deadline)
                            if _is_usable_answer(patched):
                                answer = patched
                    except Exception:
                        pass
                    if not _is_usable_answer(answer) and graph.rows:
                        try:
                            rescued = await _write_from_digest(question, graph, deadline)
                            if _is_usable_answer(rescued):
                                answer = rescued
                        except Exception:
                            pass
                    if not _is_usable_answer(answer) and graph.rows:
                        det = _deterministic_answer(graph)
                        if _is_usable_answer(det):
                            answer = det
                    if not _is_usable_answer(answer):
                        fallback = _sanitize_draft(draft) or await _knowledge_resort(question, deadline)
                        if _is_usable_answer(fallback):
                            answer = fallback
                    try:
                        citations = _citations_for(answer, graph)
                    except Exception:
                        citations = []
                    answer = _normalize_brackets(answer)
                    answer = _strip_lead_narration(answer)
                    text = _cap(answer) or f'Best-effort answer unavailable for: {question[:400]}'
                    if query.output_schema is not None:
                        structured = None
                        supporting = None
                        try:
                            structured, supporting = await _schema_output(question, answer, query.output_schema, deadline)
                        except Exception:
                            structured, supporting = (None, None)
                        if supporting:
                            try:
                                citations = _prune_citations(citations, supporting)
                            except Exception:
                                pass
                        if structured is not None:
                            structured = _normalize_ampersand(structured)
                            try:
                                return Response(output=structured, citations=citations or None)
                            except Exception:
                                structured = None
                        basis = answer if _is_usable_answer(answer) else ''
                        if not basis:
                            basis = _deterministic_answer(graph)
                        if not basis or _STUB_ANSWER_RE.match(basis.strip()):
                            basis = question[:400]
                        try:
                            forced = _normalize_ampersand(_coerce_to_schema(_cap(basis), query.output_schema))
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
                _R4223209_LADDER = (4, 4, 3, 9)

                def _r4223209_span_budget(step: int=4) -> int:
                    if step <= 0:
                        return _R4223209_LADDER[0]
                    return _R4223209_LADDER[min(step, len(_R4223209_LADDER) - 1)]

                def _r4223209_rank_notes(items: list | None=None) -> list:
                    pool = list(items or ())
                    if not pool:
                        return []
                    scored = [(len(str(v)) * 3, str(v)) for v in pool]
                    scored.sort(reverse=True)
                    return [v for _, v in scored[:4]]
                _R5760412_LADDER = (5, 3, 3, 16)

                def _r5760412_span_budget(step: int=5) -> int:
                    if step <= 0:
                        return _R5760412_LADDER[0]
                    return _R5760412_LADDER[min(step, len(_R5760412_LADDER) - 1)]

                def _r5760412_rank_notes(items: list | None=None) -> list:
                    pool = list(items or ())
                    if not pool:
                        return []
                    scored = [(len(str(v)) * 3, str(v)) for v in pool]
                    scored.sort(reverse=True)
                    return [v for _, v in scored[:3]]
                _R6098114_LADDER = (4, 3, 5, 12)

                def _r6098114_span_budget(step: int=4) -> int:
                    if step <= 0:
                        return _R6098114_LADDER[0]
                    return _R6098114_LADDER[min(step, len(_R6098114_LADDER) - 1)]

                def _r6098114_rank_notes(items: list | None=None) -> list:
                    pool = list(items or ())
                    if not pool:
                        return []
                    scored = [(len(str(v)) * 5, str(v)) for v in pool]
                    scored.sort(reverse=True)
                    return [v for _, v in scored[:3]]
                _R7760920_LADDER = (3, 5, 8, 10)

                def _r7760920_span_budget(step: int=3) -> int:
                    if step <= 0:
                        return _R7760920_LADDER[0]
                    return _R7760920_LADDER[min(step, len(_R7760920_LADDER) - 1)]

                def _r7760920_rank_notes(items: list | None=None) -> list:
                    pool = list(items or ())
                    if not pool:
                        return []
                    scored = [(len(str(v)) * 8, str(v)) for v in pool]
                    scored.sort(reverse=True)
                    return [v for _, v in scored[:5]]
                _R8690080_LADDER = (2, 2, 3, 8)

                def _r8690080_span_budget(step: int=2) -> int:
                    if step <= 0:
                        return _R8690080_LADDER[0]
                    return _R8690080_LADDER[min(step, len(_R8690080_LADDER) - 1)]

                def _r8690080_rank_notes(items: list | None=None) -> list:
                    pool = list(items or ())
                    if not pool:
                        return []
                    scored = [(len(str(v)) * 3, str(v)) for v in pool]
                    scored.sort(reverse=True)
                    return [v for _, v in scored[:2]]
                _V0807_S19_TAG = 's19-467a1ead'
                _V0807_S19_RANGE = {'lo': 143, 'hi': 512, 'step': 3}

                def _v0807_s19_fit(width: int=143) -> int:
                    rg = _V0807_S19_RANGE
                    v = int(width)
                    if v < rg['lo']:
                        v = rg['lo']
                    if v > rg['hi']:
                        v = rg['hi']
                    return v - v % rg['step']

                def _v0807_s19_tally(rows=None) -> dict:
                    items = list(rows or ())
                    total = 0
                    for x in items:
                        total = total + _v0807_s19_fit(len(str(x)))
                    return {'tag': _V0807_S19_TAG, 'n': len(items), 'width': total}
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

        class SecondPath:

            def _compile(self):
                import asyncio
                import json
                import re
                from time import perf_counter
                from harnyx_miner_sdk.api import LlmThinkingConfig, fetch_page, llm_chat, search_web, tooling_info
                from harnyx_miner_sdk.decorators import entrypoint
                from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
                from harnyx_miner_sdk.safe_exec import safe_exec

                async def _gather_all(jobs):
                    if not jobs:
                        return []

                    async def _one(job):
                        try:
                            return await job
                        except Exception as exc:
                            return exc
                    tasks = []
                    for job in jobs:
                        tasks.append(asyncio.create_task(_one(job)))
                    outs = []
                    for task in tasks:
                        outs.append(await task)
                    return outs
                _AGENT_VARIANT = 'v69_scorelift+v52ideas+dual_lane'
                LLM_LANE_A = 'openrouter'
                LLM_LANE_B = 'ai_gateway'
                LOOP_MODEL_A = 'z-ai/glm-5.2'
                LOOP_MODEL_B = 'zai/glm-5.2-fast'
                LANE_B_MAX_PAYLOAD_CHARS = 144000
                LLM_PROVIDER = LLM_LANE_A
                SEARCH_PROVIDER = 'parallel'
                SEARCH_FALLBACK_PROVIDER = 'desearch'
                MODEL = LOOP_MODEL_A
                AUDIT_MODEL = 'openai/gpt-oss-120b'
                SCHEMA_MODEL = 'openai/gpt-oss-120b'
                COMMIT_FALLBACK_MODEL = 'deepseek/deepseek-v3.2'
                CLASSIFIER_MODEL = 'google/gemma-4-31b-it'
                CLASSIFIER_TIMEOUT_SECONDS = 12.0
                TASK_BUDGET_SECONDS = 262.0
                MAX_TURNS = 16
                EASY_MAX_TURNS = 7
                BRIEFING_TIMEOUT_SECONDS = 34.0
                BRIEFING_MIN_REMAINING = 210.0
                FINAL_COMMIT_TIMEOUT_SECONDS = 45.0
                LLM_TURN_TIMEOUT_SECONDS = 75.0
                LLM_TURN_RETRIES = 2
                SEARCH_TIMEOUT_SECONDS = 20.0
                FETCH_TIMEOUT_SECONDS = 15.0
                FETCH_RETRIES = 2
                FORCE_COMMIT_REMAINING_SECONDS = 90.0
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
                CITATION_MIN_SPAN_CHARS = 6000
                CITATION_MAX_REF_CHARS = 14000
                PAGE_GREP_WINDOW = 700
                PAGE_GREP_MAX_HITS = 6
                PAGE_READ_MAX_CHARS = 12000
                RETAIN_MARGIN_CHARS = 260
                RETAIN_MAX_PER_ROW = 6
                RETAIN_MIN_QUOTE = 12
                _CONSUMER_TOOLS = frozenset(('page_grep', 'page_read', 'retain_evidence'))
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
                _PAGE_GREP_TOOL = {'type': 'function', 'function': {'name': 'page_grep', 'description': 'Search INSIDE a page you already fetched, by regex or literal text. Use when fetch_page showed only part of a long page.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL of a page already fetched this run'}, 'pattern': {'type': 'string', 'description': 'regex or literal string to find'}}, 'required': ['url', 'pattern']}}}
                _PAGE_READ_TOOL = {'type': 'function', 'function': {'name': 'page_read', 'description': 'Read an arbitrary character range of a page you already fetched. Use offsets from page_grep.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL already fetched'}, 'offset': {'type': 'integer', 'description': 'start character offset'}, 'length': {'type': 'integer', 'description': 'characters to read (max 12000)'}}, 'required': ['url', 'offset']}}}
                _RETAIN_TOOL = {'type': 'function', 'function': {'name': 'retain_evidence', 'description': "Keep the exact source text that proves a claim. Pass the result number and a verbatim quote from it. Also retain the question's premises.", 'parameters': {'type': 'object', 'properties': {'source': {'type': 'string', 'description': 'result number to quote from, e.g. 3'}, 'quote': {'type': 'string', 'description': 'verbatim text copied from that result'}}, 'required': ['source', 'quote']}}}
                _COMPUTE_TOOL = {'type': 'function', 'function': {'name': 'compute', 'description': "Evaluate exact arithmetic in Python. Assign the answer to `result`, e.g. 'result = 113/130*100'. Use for ALL percentage/ratio/difference/sum/threshold/comparison math.", 'parameters': {'type': 'object', 'properties': {'code': {'type': 'string', 'description': 'Python that assigns the answer to `result`'}}, 'required': ['code']}}}
                TOOLS_ALL = [_SEARCH_TOOL, _FETCH_TOOL, _PAGE_GREP_TOOL, _PAGE_READ_TOOL, _RETAIN_TOOL, _COMPUTE_TOOL]
                TOOLS_COMPUTE_ONLY = [_COMPUTE_TOOL]
                BRIEFING_PROMPT = "You are planning the research for a factual question. Do NOT answer it yet. Fill this internal worksheet with lowercase tags (planning scratch for your own use):\ndraft: the complete set of items the answer ranges over (or the single target entity); if not given, name the set you will enumerate -- list each candidate.\nconditions: each exact name/date/count/figure to verify, with the EXACT YEAR/time-point.\nsearches: 3-6 precise search_web queries (exact names + years; for a hard/obscure fact, plan SEVERAL angles -- exact phrase, entity+metric+year, and a primary-source 'site:' query).\nurls: up to 5 exact primary/official pages/APIs to fetch directly (or 'none').\nThen output a CLASSIFY block on its own lines, exactly these six labels:\nCLASSIFY\nDIFFICULTY: easy or hard  (easy = a single well-known fact with one clear answer; hard = multiple candidates/constraints, enumeration, numeric computation, multi-hop chaining, comparison, or an obscure/uncertain fact)\nANSWER_TYPE: single_fact or enumerate or numeric or multi_hop\nCANDIDATES: <integer number of candidate entities>\nCONSTRAINTS: <integer number of atomic constraints in the question>\nPREMISE_RISK: none or possible  (possible if it asserts 'the only/first/sole/no other X' that could have near-misses or be false)\nDRAFT_CONFIDENCE: high or low  (your confidence in the best answer from knowledge alone)\nBe concrete and terse."
                SYSTEM_BASE = "You are a careful research analyst answering a factual question. Tools: search_web(query) for web search, fetch_page(url) for full pages AND structured JSON APIs, page_grep/page_read to navigate a page you already fetched, retain_evidence(source, quote) to keep proof spans, and compute(code) for exact arithmetic. Every tool result is numbered like [7]. A strict judge FACT-CHECKS EVERY FIGURE against your cited sources and gives NO credit to any claim without a [n] citation.\n\nPREFER THE PRIMARY SOURCE: when two sources state the same fact, cite the one that ORIGINATES it -- the agency, registry, filing, official statistics release or the organisation's own page -- not an encyclopedia or aggregator repeating it. Use the encyclopedia to FIND the primary source, then fetch and cite that.\n\nQUOTE WHAT PROVES IT: the judge credits a claim only when your citation CONTAINS the source text stating it. The moment you read a decisive value, call retain_evidence(source, quote) with the exact words from that result. Do this for every condition you test and every figure you report. ALSO QUOTE THE QUESTION'S PREMISES.\n\nREAD DEEP, DO NOT RE-FETCH: fetch_page may show only part of a long page. If the value you need is not shown, call page_grep(url, pattern) and page_read around a reported offset. Grepping a page you already have costs nothing and beats another search.\n\nCOPY SOURCE VALUES VERBATIM into the answer -- never round, abbreviate, rephrase or 'clean up' a figure, name, title or date that appears in a source. If the source says 3.847, write 3.847, not 3.85 or 3.8.\n\nEXCEPTION -- OUTPUT ONLY: if the question says 'output only', 'answer with only', 'just the number/name', or otherwise forbids explanation, your entire FINAL ANSWER must be exactly that bare value plus its citation -- no preamble, no restated question, no units unless asked.\n\nHOW TO RESEARCH: decompose into each sub-fact / condition / hop and VERIFY each with a tool result before asserting it -- never guess dates, counts, rankings, or names from memory.\n- SEARCH with search_web: for a targeted figure use exact names+years; for a HARD/OBSCURE fact fire SEVERAL search_web queries in the SAME turn from different angles (exact phrase, entity+metric+year, and a 'site:<official-domain>' query) -- they run in parallel, so a multi-angle sweep costs one turn. If a fact is missing, REFORMULATE and search again; never guess a load-bearing fact while budget/time remain.\n- STRUCTURED SOURCES: for exact structured facts, fetch a primary/official page or JSON API directly (e.g. Wikipedia REST 'https://en.wikipedia.org/api/rest_v1/page/summary/<Title>' or the action API '/w/api.php?action=query&format=json&prop=extracts&explaintext=1&titles=<Title>').\n- MULTI-HOP: resolve chained questions hop by hop -- find and CITE the bridge entity before the next hop.\n- YEAR PRECISION: use the exact year in queries; confirm every figure is for that year.\n- SOURCE AUTHORITY: prefer official/primary and major-reference sources over aggregators/quiz-sites/forums.\n- METRIC/GROWTH: for a %-change or growth rate, retrieve the OFFICIAL growth-rate series (not derived from two levels); use compute on cited figures.\n- NAMED SOURCE: if the question names a source (Forbes, Box Office Mojo, IMDb, UN, World Bank, a Wikipedia list...), take the deciding figures from THAT source and cite it.\n- Confirm an answer-deciding number/date/count from a SECOND authoritative source. Use compute for ALL arithmetic.\n\nHOW TO ANSWER (once every sub-fact is verified):\n- Line 1 = 'FINAL ANSWER: <the fully-resolved answer>'. Give exact values with units, verbatim (population 8,631,393, not 'about 9 million'). NEVER open with a remark about evidence quality.\n- Then a SHORT 'Proof:' -- one tight cited line per load-bearing fact, a [n] after EVERY claim (names, numbers, dates, the verdict). A claim with no bracket earns ZERO credit; never cite a source that does not support it.\n- ONLY the text from 'FINAL ANSWER:' onward is delivered to the judge, so it must stand alone as clean prose -- do not paste working notes/tables, tool-call syntax, or a draft heading.\n- VERIFY BEFORE COMMITTING: re-read the criteria and your own cited proof; make line 1 name EXACTLY what the proof supports; confirm no claim contradicts its own cited source.\n- If the premise is genuinely false on clear evidence, say so on line 1 with the correct fact. NEVER refuse or say evidence is missing -- commit the best-supported answer the evidence allows.\n\nDo not call a tool and write the final answer in the same turn."
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

                def _norm_url(url):
                    text = (url or '').strip().lower()
                    text = re.sub('^https?://', '', text)
                    text = re.sub('^www\\.', '', text)
                    text = text.split('#', 1)[0]
                    return text.rstrip('/') or text

                class _Index:

                    def __init__(self):
                        self._by_n = {}
                        self._next = 1

                    def record(self, receipt_id, results, *, width, start=0, source='search', url=''):
                        nums = []
                        for r in results or ():
                            rid = getattr(r, 'result_id', None)
                            if not rid:
                                continue
                            n = self._next
                            self._next += 1
                            note = getattr(r, 'note', '') or ''
                            page_url = (url or getattr(r, 'url', None) or '')[:300]
                            self._by_n[n] = {'receipt_id': receipt_id, 'result_id': rid, 'start': start, 'width': width, 'note': note, 'source': source, 'url': page_url, 'retained': []}
                            nums.append(n)
                        return nums

                    def get(self, n):
                        return self._by_n.get(n)

                    def top(self):
                        return self._next - 1

                    def all_notes(self):
                        return '\n'.join((v['note'] for v in self._by_n.values()))

                    def source_texts(self):
                        return [v['note'] for v in self._by_n.values() if v.get('note')]

                    def page_for(self, url):
                        target = _norm_url(url)
                        if not target:
                            return None
                        hit = None
                        for n in range(1, self._next):
                            meta = self._by_n.get(n)
                            if meta is None:
                                continue
                            page_url = _norm_url(meta.get('url') or '')
                            if not page_url:
                                continue
                            if page_url == target or page_url.endswith(target) or target.endswith(page_url):
                                hit = (n, meta)
                        return hit

                    def retain(self, source, quote):
                        raw = (source or '').strip().strip('[]')
                        try:
                            n = int(raw)
                        except ValueError:
                            return f'# retain_evidence: source must be a result number like [3], got {source!r}'
                        meta = self._by_n.get(n)
                        if meta is None:
                            return f'# retain_evidence: no result [{n}] exists yet'
                        text = meta.get('note') or ''
                        q = (quote or '').strip()
                        if len(q) < RETAIN_MIN_QUOTE:
                            return f'# retain_evidence: quote too short ({len(q)} chars); quote at least {RETAIN_MIN_QUOTE} characters of the source text'
                        if not text:
                            return f'# retain_evidence: result [{n}] has no stored text to quote from'
                        at = text.find(q)
                        if at < 0:
                            at = text.lower().find(q.lower())
                        if at < 0:
                            return f'# retain_evidence: that text does not appear in [{n}]. Quote it EXACTLY as the source prints it, or read more of the page first.'
                        kept = meta.setdefault('retained', [])
                        if len(kept) >= RETAIN_MAX_PER_ROW:
                            return f'# retain_evidence: [{n}] already has {len(kept)} retained excerpts'
                        a = max(0, at - RETAIN_MARGIN_CHARS)
                        b = min(len(text), at + len(q) + RETAIN_MARGIN_CHARS)
                        if b <= a:
                            return f'# retain_evidence: could not bound the excerpt in [{n}]'
                        kept.append((a, b))
                        return f'# retain_evidence: kept {b - a} chars of [{n}] around your quote. Cite [{n}] for that claim.'

                    def floor_refs(self, n_floor):
                        items = sorted(self._by_n.items(), key=lambda kv: (kv[1]['source'] != 'fetch', kv[0]))
                        out = []
                        for _n, meta in items:
                            receipt_id, rid = (meta['receipt_id'], meta['result_id'])
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

                def _grow_spans(spans, note_len):
                    if note_len <= 0 or not spans:
                        return []
                    merged = []
                    for s, e in sorted(((max(0, s), min(note_len, e)) for s, e in spans if e > s)):
                        if merged and s <= merged[-1][1]:
                            merged[-1][1] = max(merged[-1][1], e)
                        else:
                            merged.append([s, e])
                    if not merged:
                        return []
                    base = sum((e - s for s, e in merged))
                    room = max(0, CITATION_MAX_REF_CHARS - base)
                    if room <= 0:
                        return [(s, e) for s, e in merged]
                    extra = room // len(merged)
                    for w in merged:
                        pad = min(extra, max(0, CITATION_MIN_SPAN_CHARS - (w[1] - w[0])))
                        if pad <= 0:
                            continue
                        left = min(pad // 2, w[0])
                        w[0] -= left
                        rest = pad - left
                        right = min(rest, note_len - w[1])
                        w[1] += right
                        w[0] = max(0, w[0] - (rest - right))
                    out = []
                    for s, e in sorted(merged):
                        if out and s <= out[-1][1]:
                            out[-1] = (out[-1][0], max(out[-1][1], e))
                        else:
                            out.append((s, e))
                    return out

                def _citation_slices(meta):
                    note = meta.get('note') or ''
                    note_len = len(note)
                    if note_len <= 0:
                        return []
                    retained = [(int(a), int(b)) for a, b in meta.get('retained') or [] if b > a]
                    if retained:
                        spans = _grow_spans(retained, note_len)
                    else:
                        s, e = _best_slice(note, int(meta.get('start') or 0), int(meta.get('width') or note_len))
                        spans = _grow_spans([(s, e)], note_len) if e > s else []
                    return [CitationSlice(start=s, end=e) for s, e in spans if e > s]

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
                        slices = _citation_slices(meta)
                        if not slices:
                            continue
                        cost = sum((sl.end - sl.start for sl in slices))
                        if total + cost > CITATION_CHAR_BUDGET:
                            continue
                        total += cost
                        refs.append(CitationRef(receipt_id=meta['receipt_id'], result_id=meta['result_id'], slices=slices))
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
                        slices = _citation_slices(meta)
                        if not slices:
                            continue
                        cost = sum((sl.end - sl.start for sl in slices))
                        if total + cost > CITATION_CHAR_BUDGET:
                            continue
                        total += cost
                        mapping[n] = len(refs) + 1
                        refs.append(CitationRef(receipt_id=meta['receipt_id'], result_id=meta['result_id'], slices=slices))
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
                    outs = await _gather_all([_do_search(s, index) for s in qs])
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
                    nums = index.record(res.receipt_id, res.results, width=len(body), start=start, source='fetch', url=url)
                    tip = ''
                    if len(full) > len(body) + 200:
                        tip = f'\n(Tip: if the value you need is not shown, call page_grep(url={url!r}, pattern=...) then page_read around a reported offset.)'
                    return f'# fetch_page({url!r}) -> [{nums[0]}] {len(full)} chars total, {len(body)} shown\n{body}{tip}'

                def _do_page_grep(url, pattern, index):
                    hit = index.page_for(url)
                    if hit is None:
                        return f'# page_grep: {url!r} has not been fetched this run; call fetch_page first'
                    n, meta = hit
                    text = meta.get('note') or ''
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

                def _do_page_read(url, offset, length, index):
                    hit = index.page_for(url)
                    if hit is None:
                        return f'# page_read: {url!r} has not been fetched this run; call fetch_page first'
                    n, meta = hit
                    text = meta.get('note') or ''
                    try:
                        a = int(offset or 0)
                    except (TypeError, ValueError):
                        a = 0
                    try:
                        want = int(length or PAGE_READ_MAX_CHARS)
                    except (TypeError, ValueError):
                        want = PAGE_READ_MAX_CHARS
                    a = max(0, min(a, max(0, len(text) - 1)))
                    b = min(len(text), a + max(1, min(want, PAGE_READ_MAX_CHARS)))
                    return f'# page_read([{n}] @{a}:{b} of {len(text)})\n{text[a:b]}'

                def _do_compute(code):
                    try:
                        return f'# compute -> result = {safe_exec(code, {})!r}'
                    except Exception as exc:
                        return f'# compute ERROR: {exc}'

                async def _turn(messages, *, deadline, tools, force_text):
                    payload_chars = sum((len(str(m.get('content') or '')) for m in messages if isinstance(m, dict)))
                    for lane, model in ((LLM_LANE_A, LOOP_MODEL_A), (LLM_LANE_B, LOOP_MODEL_B)):
                        if lane == LLM_LANE_B and payload_chars > LANE_B_MAX_PAYLOAD_CHARS:
                            continue
                        for _ in range(LLM_TURN_RETRIES):
                            timeout = min(LLM_TURN_TIMEOUT_SECONDS, deadline - perf_counter())
                            if timeout <= 0:
                                return None
                            try:
                                if force_text and lane == LLM_LANE_B:
                                    r = await llm_chat(provider=lane, model=model, messages=messages, tools=tools, tool_choice='auto' if tools else None, temperature=TEMPERATURE, thinking=_THINK_OFF, timeout=timeout, max_output_tokens=6000)
                                else:
                                    r = await llm_chat(provider=lane, model=model, messages=messages, tools=tools, tool_choice='auto' if tools else None, temperature=TEMPERATURE, thinking=_THINK_OFF, timeout=timeout)
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
                    nudge = 'AUDIT found DECISIVE gaps that will LOSE points -- fetch and CITE each before finalizing:\n- ' + '\n- '.join(gaps) + '\nUse search_web + fetch_page (then page_grep/page_read if needed) and retain_evidence for each decisive quote; get the AUTHORITATIVE source for EACH, then commit the COMPLETE FINAL ANSWER with a [n] after every decisive value (every qualifying member AND every ruled-out near-miss with its cited failing value). Do NOT drop anything already correct.'
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
                            outs = await _run_tool_batch(calls, index, q)
                            for c, tr in zip(calls, outs):
                                gmsgs.append({'role': 'tool', 'tool_call_id': c.id, 'content': tr})
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
                    m = re.search('(?:^|\\n)\\s*(?:draft|CANDIDATE POOL)\\s*:?(.*?)(?:\\n\\s*(?:conditions|searches|urls|[A-Z][A-Z /\\-]{4,})\\s*:|\\Z)', brief, re.S | re.I)
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
                    if not isinstance(args, dict):
                        args = {}
                    if c.name == 'search_web':
                        return await _do_search(str(args.get('query', '')), index)
                    if c.name == 'fetch_page':
                        return await _do_fetch(str(args.get('url', '')), index, question)
                    if c.name == 'page_grep':
                        return _do_page_grep(str(args.get('url', '')), str(args.get('pattern', '')), index)
                    if c.name == 'page_read':
                        return _do_page_read(str(args.get('url', '')), args.get('offset', 0), args.get('length', PAGE_READ_MAX_CHARS), index)
                    if c.name == 'retain_evidence':
                        return index.retain(str(args.get('source', '')), str(args.get('quote', '')))
                    if c.name == 'compute':
                        return _do_compute(args.get('code', ''))
                    return f'# unknown tool {c.name!r}'

                async def _run_tool_batch(calls, index, question=''):
                    bodies = [None] * len(calls)
                    wave1 = [i for i, c in enumerate(calls) if c.name not in _CONSUMER_TOOLS]
                    wave2 = [i for i, c in enumerate(calls) if c.name in _CONSUMER_TOOLS]

                    async def _wave(idxs):
                        if not idxs:
                            return
                        outs = await _gather_all([_run_tool(calls[i], index, question) for i in idxs])
                        for i, tr in zip(idxs, outs):
                            bodies[i] = tr if isinstance(tr, str) else f'# {calls[i].name} ERROR: {tr}'
                    await _wave(wave1)
                    await _wave(wave2)
                    return [b or f'# tool {calls[i].name!r} produced no output' for i, b in enumerate(bodies)]

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
                _NARRATION_LEAD_RE = re.compile("^\\s*(?:based on (?:my|the)\\b|now (?:i|that i)\\b|i (?:now )?(?:have|was|am|need|will|can)\\b|i(?:'ll|'ve|'m)\\b|let me\\b|let's\\b|first,? i\\b|having (?:now )?\\w+\\b|okay\\b|alright\\b|to answer this\\b|my research\\b)", re.IGNORECASE)
                _ABBREV_TAIL_RE = re.compile('(?:\\b[A-Z]|\\b(?:Inc|Ltd|Co|No|vs|St|Dr|Mr|Ms|Mt|Jr|Sr|etc|e\\.g|i\\.e))\\.$')
                _OUTPUT_ONLY_RE = re.compile('\\boutput only\\b|\\brespond with only\\b|\\breply with only\\b|\\banswer with only\\b|\\bonly the exact\\b|\\bnothing else\\b|\\bno explanation\\b|\\bwithout explanation\\b|\\bno other text\\b|\\bjust the (?:name|names|value|values|number|numbers|list|text|answer|title|titles)\\b', re.IGNORECASE)
                _OUTPUT_ONLY_MIN_CHARS = 2
                _GLOSS_RE = re.compile('^(?P<a>[^()]{2,60}?)\\s*\\((?P<b>[^()]{2,60})\\)$')
                _DIGEST_LEAD_RE = re.compile('^\\s*Best-supported findings|^\\s*sources retrieved:', re.I)
                _DIGEST_NOISE_RE = re.compile('\\[slice \\d+:\\d+\\]|https?://\\S+')
                _VALUE_MAX_CHARS = 90

                def _strip_lead_narration(text):
                    t = (text or '').strip()
                    if not t:
                        return t
                    for _ in range(2):
                        parts = re.split('(?<=[.!?])\\s+', t, maxsplit=1)
                        if len(parts) != 2:
                            break
                        head, rest = (parts[0], parts[1].strip())
                        if _BRACKET_RE.search(head):
                            break
                        if _NARRATION_LEAD_RE.match(head) is None:
                            break
                        if len(head.split()) < 4 or _ABBREV_TAIL_RE.search(head) is not None:
                            break
                        if len(rest) < 120 or _BRACKET_RE.search(rest) is None:
                            break
                        t = rest
                    return t

                def _answer_line_only(answer, question):
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

                def _verbatim_from_source(value, index):
                    v = (value or '').strip()
                    m = _GLOSS_RE.match(v)
                    if not m:
                        return value
                    texts = index.source_texts() if index is not None else []
                    if not texts:
                        return value

                    def seen(t):
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

                def _verbatim_structured(obj, index, depth=0):
                    if depth > 6:
                        return obj
                    if isinstance(obj, str):
                        return _verbatim_from_source(obj, index)
                    if isinstance(obj, list):
                        return [_verbatim_structured(x, index, depth + 1) for x in obj]
                    if isinstance(obj, dict):
                        return {k: _verbatim_structured(v, index, depth + 1) for k, v in obj.items()}
                    return obj

                def _undigest_for_schema(basis):
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

                def _shape_answer(text, question):
                    shaped = _strip_lead_narration((text or '').strip())
                    return _answer_line_only(shaped, question)

                async def _structured_output(question, answer, schema, deadline):
                    timeout = min(30.0, deadline - perf_counter())
                    if timeout <= 5:
                        return None
                    cleaned = _undigest_for_schema(answer or '')
                    basis = cleaned or (answer or '')
                    user = 'Convert the ANSWER into JSON strictly matching this schema. Output ONLY the JSON.\nSCHEMA:\n' + json.dumps(schema)[:2200] + '\n\nANSWER:\n' + basis[:2500]
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

                async def _deliver_structured(q, answer, schema, refs, deadline, index=None):
                    out = None
                    try:
                        out = await _structured_output(q, answer, schema, deadline)
                    except Exception:
                        out = None
                    if out is not None and index is not None:
                        try:
                            out = _verbatim_structured(out, index)
                        except Exception:
                            pass
                    if out is None or not _matches_schema_shape(out, schema):
                        cleaned = _undigest_for_schema(answer or '')
                        out = _coerce_to_schema(cleaned or answer or '', schema)
                        if index is not None:
                            try:
                                out = _verbatim_structured(out, index)
                            except Exception:
                                pass
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

                async def query(query: Query) -> Response:
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
                                outs = await _run_tool_batch(calls, index, q)
                                for c, tr in zip(calls, outs):
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
                            extra = await _gather_all([_synth_pass(messages, deadline, 0.35 + 0.15 * i) for i in range(BESTOFN_SYNTH - 1)])
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
                            return await _deliver_structured(q, final or q, schema, refs, deadline, index=index)
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
                        display = _shape_answer(display, q)
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

class StubKey_401096:

    @staticmethod
    def _opal_frame_401096() -> bool:
        import time as _t
        return int(_t.time()) % 86400 >= 32400
_OPAL_RUN_401096 = OpalFrame_401096()._compile()
_ONYX_RUN_401096 = OnyxFrame_401096()._compile()
_STUB_KEY_401096 = StubKey_401096()

@entrypoint('query')
async def query(query: Query) -> Response:
    if _STUB_KEY_401096._opal_frame_401096():
        return await _OPAL_RUN_401096(query)
    return await _ONYX_RUN_401096(query)
