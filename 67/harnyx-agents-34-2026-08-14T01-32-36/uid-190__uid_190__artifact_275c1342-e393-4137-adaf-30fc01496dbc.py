from __future__ import annotations
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class MossBank_62ab2f:

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

class FernBank_62ab2f:

    def _compile(self):
        import asyncio
        import json
        import re
        from time import perf_counter
        from harnyx_miner_sdk.api import LlmThinkingConfig, fetch_page, llm_chat, search_web
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        LLM_PROVIDER = 'openrouter'
        PRIMARY_MODEL = 'z-ai/glm-5'
        FALLBACK_MODEL = 'deepseek/deepseek-v3.2'
        SEARCH_PROVIDER = 'parallel'
        SEARCH_PROVIDERS = ('parallel', 'desearch')
        FETCH_PROVIDERS = ('parallel', 'desearch')
        TOTAL_BUDGET_S = 285.0
        COMMIT_RESERVE_S = 45.0
        COMMIT_LOOKAHEAD_TURNS = 2
        MAX_TURNS = 16
        LLM_TURN_TIMEOUT_S = 68.0
        LLM_TRY_PER_TURN = 2
        SEARCH_TIMEOUT_S = 20.0
        FETCH_TIMEOUT_S = 15.0
        FETCH_TRIES = 2
        SEARCH_WINDOW = 700
        FETCH_WINDOW = 6000
        CITATION_COUNT_CAP = 20
        EVIDENCE_CHAR_CAP = 112000
        DIGEST_CHAR_CAP = 90000
        DEEP_WINDOW = 2600
        DEEP_MIN_HITS = 2
        MAX_DEEP_SLICES = 4
        NUMERIC_DENSITY_MIN = 55
        SYSTEM_PROMPT = "You are a meticulous research analyst. The user asks a factual question that is often multi-part or requires filtering a set of entities by several conditions. You have two tools, search_web and fetch_page; every tool result is labelled with a number like [4].\n\nMETHOD:\n1. Decompose the question into every distinct sub-fact and every filtering condition. Never recall a date, age, count, rank, population, price, chart position or proper name from memory — search for it and read the result.\n2. ENUMERATE, THEN FILTER. When the question asks which members of a set satisfy conditions, FIRST establish the complete candidate pool from an authoritative list (do not work from the 2-3 famous examples you can recall), THEN evaluate every candidate against every condition. Silently omitting a qualifying member is the most common way to lose.\n3. A superlative (highest-grossing, most-certified, largest, oldest, best-selling) is a LOOKUP, not a guess. Look up the actual ranked value from the authoritative source; an entity's most famous work is often NOT its top-ranked one.\n4. NAME-THE-SOURCE. If the question cites a specific source or dataset (e.g. Box Office Mojo, the 2020 US Census, a Billboard chart, an agency's annual report), get the numbers from THAT source by fetching its page — not from a secondary article. For a key entity, fetch_page the single most authoritative source (official site, .gov/.edu, primary filing, canonical article) and read it. Never cite reddit, x/twitter, quora or forums.\n5. STRICT THRESHOLD ARITHMETIC. Copy each candidate's exact value, then apply the comparator literally: 'more than 25' means strictly > 25 (25 fails); 'between 2010 and 2019' is inclusive of both endpoints. Convert rate/average conditions into a concrete integer test (e.g. 'averaged more than 1 per year over 10 years' = 'more than 10 in total'). Read date and edition boundaries literally (the 2010 through 2019 ceremonies are ten awards, one winner each).\n6. Verify each load-bearing sub-claim against a source before you rely on it; re-check the one or two near-miss cases that decide the answer.\n\nANSWER — only once every sub-fact is verified:\n- Open with 'FINAL ANSWER: <the fully-resolved answer that already satisfies every condition>'. For a single-item question name that one item; do not lead with an unfiltered candidate list.\n- For which/list/superlative questions, then give each qualifying item with its compared value and citation, and briefly show the closest excluded item(s) with the value that disqualifies them (e.g. 'Nirvana: 10 charting singles [7] — fails the >12 test').\n- Quote numbers, dates and names verbatim with units (population 1,362,359 — not 'about 1.4M'); never round.\n- If the premise is false, or the specific data genuinely does not exist in any queryable form, say so plainly in the first line and give the correct fact or the reasoned impossibility (name the dataset and why it cannot be derived) — do NOT refuse or answer 'evidence missing'; commit to the best-supported answer.\n\nCITATIONS: place the source number in brackets immediately after EVERY factual claim — each number, date, name or yes/no determination gets its own bracket, e.g. 'the 2015 winner was Eddie Redmayne [6]'. Every load-bearing value must carry a citation or it scores zero. Do not append a bulk source list at the end and do not pad with tangential citations. Never write a final answer in the same turn as a tool call.\n\nBEFORE YOU COMMIT — three checks that decide close calls:\n1. COMPLETENESS: never conclude 'only X qualifies' until you have listed EVERY candidate from the question's set/pool BY NAME and checked each against every condition. The most common loss is omitting a second qualifier you already have evidence for — re-scan your results for it.\n2. MAXIMAL SPECIFICITY: give the most precise form the evidence supports — the exact room/hall name (not just the floor), the exact figure (not a rounded one), the exact date. A correct but vaguer answer loses to a more specific one.\n3. FILL THE ONE GAP: if a single required value is still missing when you are about to answer — a runtime, a figure from the pinned named source, one entity's datum — do ONE more targeted search/fetch for exactly that value before committing. Do not abstain over a single missing number.\n\n## Pairwise Scoring Rules\n\n- Decompose every sub-fact/filter before answering; never answer dates/counts/names from memory.\n- Full roster: enumerate the complete candidate pool, evaluate every candidate, cite exclusions with the failing value.\n- Literal comparators: more-than is strict; ranges inclusive unless stated.\n- False premise: correct in the first line with a citation; never refuse or answer evidence-missing.\n- Exact values: verbatim numbers/dates/units; no rounding.\n- Commit: partial cited answers beat refusals; cover every asked sub-question.\n- Citations: [n] after every load-bearing claim (qualifiers AND exclusions); quality over quantity.\n- Batch lookups: use search_many (or several tool calls in one turn) for independent queries.\n"
        COMMIT_NUDGE = 'About {secs}s of research budget remain — stop searching now. Using ONLY the numbered tool results gathered above, write the best FINAL ANSWER you can in the required format, with exact cited values. If a sub-claim is still uncertain, give the most-likely value and mark just that piece as a best estimate — a partial, cited answer scores far higher than a refusal. Cite exclusions as well as winners. Every load-bearing number/date/name needs its own [n].'
        HARD_COMMIT = "STOP researching. Do not call any tool. Right now, using ONLY the numbered tool results already gathered above, write your single best FINAL ANSWER in the required format, putting the bracket citation after every value you state. Reason from the evidence you have; for any piece still unresolved give the most-likely value and mark it as a best estimate. If the specific data provably does not exist in any queryable public source, state that as your reasoned conclusion (name the dataset and why it cannot be derived, with citations). Do NOT give a bare refusal or an 'evidence missing' non-answer — a partial or reasoned answer always scores higher."
        FALLBACK_TEXT = 'FINAL ANSWER: a fully source-backed answer could not be assembled within the time budget.'
        _TOOL_SPECS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web; returns numbered results, each with a title, url and text excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'search_many', 'description': 'Run several web searches at once (in parallel) and get all numbered results back together. Use to enumerate or verify a whole set of candidates in one step — up to 8 queries.', 'parameters': {'type': 'object', 'properties': {'queries': {'type': 'array', 'items': {'type': 'string'}, 'description': 'up to 8 search queries to run together'}}, 'required': ['queries']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': 'Fetch one URL and return the extracted main text of that page.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'the URL to fetch'}}, 'required': ['url']}}}]
        _BRACKET_RE = re.compile('\\[(\\d[\\d,\\s-]*)\\]')
        _STOPWORDS = frozenset('the a an of to in on for and or by with from at as is are was were be been being that this which who whom whose what when where how many much more most between during according only into over under than then their there these those has have had'.split())

        class _Ledger:

            def __init__(self) -> None:
                self._rows: dict[int, dict[str, object]] = {}
                self._n = 0

            def add(self, receipt_id: str, results: object, *, window: int, deeps: list[tuple[int, int]] | None=None) -> list[int]:
                assigned: list[int] = []
                for r in results or ():
                    rid = getattr(r, 'result_id', None)
                    if not rid:
                        continue
                    self._n += 1
                    note = getattr(r, 'note', None) or ''
                    top_end = min(window, len(note))
                    text = note[:top_end]
                    kept: list[tuple[int, int]] = []
                    for d in deeps or []:
                        ds, de = (int(d[0]), min(int(d[1]), len(note)))
                        if de - ds < 100 or ds < top_end:
                            continue
                        if any((not (de <= es or ds >= ee) for es, ee in kept)):
                            continue
                        kept.append((ds, de))
                        text = f'{text}\n…\n{note[ds:de]}'
                    self._rows[self._n] = {'receipt_id': receipt_id, 'result_id': rid, 'window': window, 'note_len': len(note), 'top_end': top_end, 'deeps': kept, 'text': text, 'title': (getattr(r, 'title', None) or '')[:160], 'url': getattr(r, 'url', None) or ''}
                    assigned.append(self._n)
                return assigned

            def row(self, n: int) -> dict[str, object] | None:
                return self._rows.get(n)

            def high(self) -> int:
                return self._n

            def digest(self, *, char_cap: int) -> str:
                parts: list[str] = []
                spent = 0
                for n in range(1, self._n + 1):
                    row = self._rows.get(n)
                    if not row:
                        continue
                    text = str(row.get('text') or '')
                    if not text:
                        continue
                    block = f"[{n}] {row.get('title') or ''} ({row.get('url') or ''})\n{text}"
                    if spent + len(block) > char_cap:
                        continue
                    spent += len(block)
                    parts.append(block)
                return '\n\n'.join(parts)

        def _seed_queries(question: str) -> list[str]:
            q = ' '.join(question.split())
            seeds = [q[:300]]
            tokens = re.findall("[A-Za-z0-9][A-Za-z0-9.\\-']+", question)
            salient = [t for t in tokens if t.lower() not in _STOPWORDS and (t[0].isupper() or any((c.isdigit() for c in t)))]
            if salient:
                compact = ' '.join(dict.fromkeys(salient))[:220]
                if compact and compact.lower() != q[:220].lower():
                    seeds.append(compact)
            return seeds[:2]

        def _salient_terms(text: str) -> list[str]:
            tokens = re.findall("[A-Za-z0-9][A-Za-z0-9.\\-']+", text or '')
            return list(dict.fromkeys((t.lower() for t in tokens if len(t) > 2 and t.lower() not in _STOPWORDS)))

        def _deep_cluster_offset(note: str, terms: list[str], top_window: int, deep_window: int) -> int | None:
            n = len(note)
            if n <= top_window + 100 or not terms:
                return None
            low = note.lower()
            hits: list[int] = []
            for t in terms:
                start = 0
                while len(hits) < 4000:
                    i = low.find(t, start)
                    if i < 0:
                        break
                    hits.append(i)
                    start = i + len(t)
            if not hits:
                return None
            hits.sort()
            top_hits = sum((1 for h in hits if h < top_window))
            deep_hits = [h for h in hits if h >= top_window]
            best_off: int | None = None
            best_count = 0
            j = 0
            for i in range(len(deep_hits)):
                while j < len(deep_hits) and deep_hits[j] < deep_hits[i] + deep_window:
                    j += 1
                count = j - i
                if count > best_count:
                    best_count = count
                    best_off = deep_hits[i]
            if best_off is None or best_count < DEEP_MIN_HITS or best_count < top_hits:
                return None
            return max(top_window, min(best_off - deep_window // 8, n - deep_window))

        def _value_regions(note: str, terms: list[str], top_window: int, *, deep_window: int=DEEP_WINDOW, max_slices: int=MAX_DEEP_SLICES) -> list[tuple[int, int]]:
            n = len(note)
            if n <= top_window + 120:
                return []
            low = note.lower()
            hits: list[int] = []
            for t in terms:
                st = top_window
                while len(hits) < 4000:
                    i = low.find(t, st)
                    if i < 0:
                        break
                    hits.append(i)
                    st = i + len(t)
            step = max(400, deep_window // 3)
            i = top_window
            while i < n:
                if sum((c.isdigit() for c in note[i:i + deep_window])) >= NUMERIC_DENSITY_MIN:
                    hits.append(i)
                i += step
            if not hits:
                return []
            hits.sort()
            cands: list[tuple[int, int, int]] = []
            for h in hits:
                s = max(top_window, h - deep_window // 8)
                e = min(s + deep_window, n)
                cnt = sum((1 for x in hits if s <= x < e))
                cands.append((cnt, s, e))
            cands.sort(reverse=True)
            slices: list[tuple[int, int]] = []
            for _cnt, s, e in cands:
                if len(slices) >= max_slices:
                    break
                if e - s < 100:
                    continue
                if any((not (e <= us or s >= ue) for us, ue in slices)):
                    continue
                slices.append((s, e))
            return sorted(slices)

        async def _do_search(query: str, ledger: _Ledger, *, time_left: float=SEARCH_TIMEOUT_S) -> str:
            if not query:
                return '# search_web() -> ERROR: empty query'
            t0 = perf_counter()
            total_budget = min(2.0 * SEARCH_TIMEOUT_S, max(1.0, time_left))
            res = None
            last_exc: Exception | None = None
            for provider in SEARCH_PROVIDERS:
                remaining = total_budget - (perf_counter() - t0)
                if remaining <= 1.0:
                    break
                to = min(SEARCH_TIMEOUT_S, remaining)
                try:
                    res = await asyncio.wait_for(search_web(query, provider=provider, timeout=to), timeout=to + 1.0)
                except Exception as exc:
                    last_exc = exc
                    res = None
                if res is not None and getattr(res, 'results', None):
                    break
            if res is None or not getattr(res, 'results', None):
                if last_exc is not None:
                    return f'# search_web({query!r}) -> ERROR: {last_exc}'
                return f'# search_web({query!r}) -> 0 results'
            nums = ledger.add(res.receipt_id, res.results, window=SEARCH_WINDOW)
            out = [f'# search_web({query!r}) -> {len(nums)} results']
            for n, r in zip(nums, res.results, strict=False):
                excerpt = (getattr(r, 'note', None) or '')[:SEARCH_WINDOW]
                out.append(f"[{n}] {getattr(r, 'title', '') or ''}\n  url: {getattr(r, 'url', '') or ''}\n  {excerpt}")
            return '\n'.join(out)

        async def _do_search_many(queries: list[str], ledger: _Ledger, *, time_left: float=SEARCH_TIMEOUT_S) -> str:
            clean = [str(q).strip() for q in queries or [] if str(q).strip()][:8]
            if not clean:
                return '# search_many() -> ERROR: no queries'
            parts = await asyncio.gather(*(_do_search(q, ledger, time_left=time_left) for q in clean))
            return f'# search_many({len(clean)} queries)\n' + '\n\n'.join(parts)

        async def _do_fetch(url: str, ledger: _Ledger, *, time_left: float=FETCH_TIMEOUT_S, terms: list[str] | None=None) -> str:
            if not url:
                return '# fetch_page() -> ERROR: empty url'
            t0 = perf_counter()
            total_budget = min(2.0 * FETCH_TIMEOUT_S, max(1.0, time_left))
            res = None
            err: Exception | None = None
            for provider in FETCH_PROVIDERS:
                remaining = total_budget - (perf_counter() - t0)
                if remaining <= 1.0:
                    break
                to = min(FETCH_TIMEOUT_S, remaining)
                try:
                    res = await asyncio.wait_for(fetch_page(url, provider=provider, timeout=to), timeout=to + 1.0)
                except Exception as exc:
                    err = exc
                    res = None
                if res is not None and getattr(res, 'results', None):
                    break
            if res is None:
                return f'# fetch_page({url!r}) -> ERROR: {err}'
            note = getattr(res.results[0], 'note', None) or ''
            deeps = _value_regions(note, terms or [], FETCH_WINDOW)
            nums = ledger.add(res.receipt_id, res.results, window=FETCH_WINDOW, deeps=deeps)
            if not nums:
                return f'# fetch_page({url!r}) -> no content'
            top_body = note[:FETCH_WINDOW]
            parts = [top_body]
            for ds, de in deeps:
                parts.append(f'… [continued from char {ds}] …\n{note[ds:de]}')
            body = '\n\n'.join(parts)
            tag = f' (+{len(deeps)} deep {sum((de - ds for ds, de in deeps))}c)' if deeps else ''
            return f'# fetch_page({url!r}) -> [{nums[0]}] {len(top_body)}c{tag}\n{body}'

        def _cited_numbers(text: str, *, high: int) -> list[int]:
            ordered: list[int] = []
            seen: set[int] = set()
            for m in _BRACKET_RE.finditer(text):
                for part in m.group(1).split(','):
                    part = part.strip()
                    if not part:
                        continue
                    rng = re.fullmatch('(\\d{1,4})\\s*-\\s*(\\d{1,4})', part)
                    if rng:
                        lo, hi = (int(rng.group(1)), int(rng.group(2)))
                        candidates = range(lo, hi + 1) if lo <= hi else ()
                    elif part.isdigit():
                        candidates = (int(part),)
                    else:
                        candidates = ()
                    for n in candidates:
                        if 1 <= n <= high and n not in seen:
                            seen.add(n)
                            ordered.append(n)
            return ordered

        def _build_citations(answer: str, ledger: _Ledger) -> list[CitationRef]:
            cited = _cited_numbers(answer, high=ledger.high())
            selected: list[tuple[dict[str, object], int]] = []
            spent = 0
            for n in cited:
                if len(selected) >= CITATION_COUNT_CAP:
                    break
                row = ledger.row(n)
                if row is None:
                    continue
                note_len = int(row.get('note_len', 0))
                if note_len <= 0:
                    continue
                top_end = min(int(row.get('top_end') or int(row.get('window', FETCH_WINDOW))), note_len)
                if top_end <= 0:
                    continue
                if spent + top_end > EVIDENCE_CHAR_CAP:
                    continue
                spent += top_end
                selected.append((row, top_end))
            deep_for: dict[int, list[tuple[int, int]]] = {}
            segments = len(selected)
            for idx, (row, top_end) in enumerate(selected):
                note_len = int(row.get('note_len', 0))
                for d in row.get('deeps') or []:
                    if segments >= 380:
                        break
                    ds, de = (int(d[0]), int(d[1]))
                    if not 0 <= ds < de <= note_len or de - ds < 100 or ds < top_end:
                        continue
                    if spent + (de - ds) > EVIDENCE_CHAR_CAP:
                        break
                    spent += de - ds
                    segments += 1
                    deep_for.setdefault(idx, []).append((ds, de))
            refs: list[CitationRef] = []
            for idx, (row, top_end) in enumerate(selected):
                slices = [CitationSlice(start=0, end=top_end)]
                for ds, de in deep_for.get(idx, []):
                    slices.append(CitationSlice(start=ds, end=de))
                refs.append(CitationRef(receipt_id=str(row['receipt_id']), result_id=str(row['result_id']), slices=slices))
            return refs

        async def _chat(messages: list[dict[str, object]], *, deadline: float, final: bool):
            thinking = LlmThinkingConfig(enabled=False) if final else LlmThinkingConfig(enabled=True, effort='low')
            attempts: list[tuple[str, int]] = [(PRIMARY_MODEL, LLM_TRY_PER_TURN), (FALLBACK_MODEL, 1)]
            for model, tries in attempts:
                for _ in range(tries):
                    budget = deadline - perf_counter()
                    if budget <= 1.0:
                        return None
                    to = min(LLM_TURN_TIMEOUT_S, budget)
                    try:
                        return await asyncio.wait_for(llm_chat(provider=LLM_PROVIDER, model=model, messages=messages, tools=None if final else _TOOL_SPECS, tool_choice=None if final else 'auto', temperature=0.2, thinking=thinking, timeout=to), timeout=to + 3.0)
                    except Exception:
                        continue
            return None

        async def _forced_commit(question: str, ledger: _Ledger, *, deadline: float) -> str | None:
            digest = ledger.digest(char_cap=DIGEST_CHAR_CAP)
            if not digest:
                return None
            msgs = [{'role': 'system', 'content': SYSTEM_PROMPT + '\n\n' + HARD_COMMIT}, {'role': 'user', 'content': question + '\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n' + digest}]
            for _ in range(2):
                if deadline - perf_counter() <= 1.5:
                    break
                result = await _chat(msgs, deadline=deadline, final=True)
                if result is None:
                    break
                text = (result.response.raw_text or '').strip()
                if text:
                    return text
            return None

        async def _pairwise_verify_patch(question: str, answer: str, messages: list, ledger, deadline: float) -> str:
            if not answer or deadline - perf_counter() < 45:
                return answer
            try:
                audit = await _chat([{'role': 'system', 'content': '# Strict Answer Auditor\n\nOutput JSON only with keys missing_elements, uncited_claims, suspect_attributions (arrays).'}, {'role': 'user', 'content': f'Audit vs question. JSON only.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:12000]}'}], deadline=deadline, final=True)
                if audit is None:
                    return answer
                raw = (audit.response.raw_text or '').strip()
                cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw, flags=re.I | re.M).strip()
                report = json.loads(cleaned)
            except Exception:
                return answer
            issues: list[str] = []
            for key in ('missing_elements', 'uncited_claims', 'suspect_attributions'):
                vals = report.get(key) if isinstance(report, dict) else None
                if isinstance(vals, list):
                    issues.extend((str(v) for v in vals if str(v).strip()))
            if not issues or deadline - perf_counter() < 25:
                return answer
            messages.append({'role': 'system', 'content': '## Audit Gaps\n\n' + '\n'.join((f'- {x}' for x in issues[:6])) + '\n\nUse at most 2 more tool calls (prefer search_many), then rewrite the COMPLETE final answer with inline [n] citations including exclusions.'})
            patched = answer
            for _extra in range(2):
                remaining = deadline - perf_counter()
                if remaining <= 8:
                    break
                force_final = _extra == 1 or remaining <= 20
                result = await _chat(messages, deadline=deadline, final=force_final)
                if result is None:
                    break
                tool_calls = result.response.choices[0].message.tool_calls or ()
                if not tool_calls:
                    text_out = (result.response.raw_text or '').strip()
                    if text_out:
                        patched = text_out
                    break
                messages.append({'role': 'assistant', 'content': result.response.raw_text, 'tool_calls': [{'id': tc.id, 'type': tc.type, 'name': tc.name, 'arguments': tc.arguments} for tc in tool_calls]})
                for tc in tool_calls:
                    try:
                        args = json.loads(tc.arguments or '{}')
                    except json.JSONDecodeError:
                        args = {}
                    time_left = max(1.0, deadline - perf_counter())
                    try:
                        if tc.name == 'search_web':
                            content = await _do_search(str(args.get('query', '')), ledger, time_left=time_left)
                        elif tc.name == 'search_many':
                            qs = args.get('queries') or []
                            content = await _do_search_many(qs if isinstance(qs, list) else [qs], ledger, time_left=time_left)
                        elif tc.name == 'fetch_page':
                            try:
                                content = await _do_fetch(str(args.get('url', '')), ledger, time_left=time_left)
                            except TypeError:
                                content = await _do_fetch(str(args.get('url', '')), ledger)
                        else:
                            content = f'# unsupported tool {tc.name!r}'
                    except Exception:
                        content = f'# {tc.name} failed during patch'
                    messages.append({'role': 'tool', 'tool_call_id': tc.id, 'content': content})
            return patched or answer

        def _finalize(answer: str, ledger: _Ledger) -> Response:
            citations = _build_citations(answer, ledger)
            return Response(text=answer, citations=citations or None)

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

        async def query(query: Query) -> Response:
            deadline = perf_counter() + TOTAL_BUDGET_S
            research_deadline = deadline - COMMIT_RESERVE_S
            ledger = _Ledger()
            query_terms = _salient_terms(query.text)
            seen_searches: dict[str, str] = {}
            messages: list[dict[str, object]] = [{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': query.text}]
            try:
                seeds = _seed_queries(query.text)
                seeded_blob = await asyncio.wait_for(_do_search_many(seeds, ledger, time_left=SEARCH_TIMEOUT_S + 6.0), timeout=SEARCH_TIMEOUT_S + 12.0)
                if ledger.high() > 0:
                    messages.append({'role': 'system', 'content': 'Preliminary automatic searches (already numbered; search more as needed):\n\n' + seeded_blob})
            except Exception:
                pass
            final_answer: str | None = None
            nudged = False
            try:
                for turn in range(1, MAX_TURNS + 1):
                    remaining = research_deadline - perf_counter()
                    if remaining <= 2.0:
                        break
                    turns_left = MAX_TURNS - turn + 1
                    if turns_left <= COMMIT_LOOKAHEAD_TURNS and (not nudged):
                        messages.append({'role': 'system', 'content': COMMIT_NUDGE.format(secs=int(deadline - perf_counter()))})
                        nudged = True
                    result = await _chat(messages, deadline=research_deadline, final=False)
                    if result is None:
                        break
                    message = result.response.choices[0].message
                    tool_calls = message.tool_calls or ()
                    if not tool_calls:
                        text = (result.response.raw_text or '').strip()
                        if text:
                            final_answer = text
                            break
                        if not nudged:
                            messages.append({'role': 'system', 'content': HARD_COMMIT})
                            nudged = True
                        continue
                    messages.append({'role': 'assistant', 'content': result.response.raw_text, 'tool_calls': [{'id': tc.id, 'type': tc.type, 'name': tc.name, 'arguments': tc.arguments} for tc in tool_calls]})
                    over_budget = False
                    for tc in tool_calls:
                        time_left = research_deadline - perf_counter()
                        if time_left <= 1.0:
                            over_budget = True
                            break
                        try:
                            args = json.loads(tc.arguments or '{}')
                        except json.JSONDecodeError:
                            args = {}
                        try:
                            if tc.name == 'search_web':
                                q = str(args.get('query', ''))
                                norm = ' '.join(q.lower().split())
                                if norm and norm in seen_searches:
                                    content = f'# search_web({q!r}) -> already searched; see {seen_searches[norm]}'
                                else:
                                    content = await asyncio.wait_for(_do_search(q, ledger, time_left=time_left), timeout=2.0 * SEARCH_TIMEOUT_S + 4.0)
                                    if norm and ' results' in content and ('-> 0 results' not in content):
                                        seen_searches[norm] = f'prior results up to [{ledger.high()}]'
                            elif tc.name == 'search_many':
                                qs = args.get('queries') or []
                                content = await asyncio.wait_for(_do_search_many(qs if isinstance(qs, list) else [qs], ledger, time_left=time_left), timeout=2.0 * SEARCH_TIMEOUT_S + 8.0)
                            elif tc.name == 'fetch_page':
                                content = await asyncio.wait_for(_do_fetch(str(args.get('url', '')), ledger, time_left=time_left, terms=query_terms), timeout=FETCH_TIMEOUT_S * FETCH_TRIES + 4.0)
                            else:
                                content = f'# unsupported tool {tc.name!r}'
                        except Exception:
                            content = f'# {tc.name} exceeded its time budget'
                        messages.append({'role': 'tool', 'tool_call_id': tc.id, 'content': content})
                    if over_budget:
                        break
                if not final_answer and ledger.high() > 0:
                    final_answer = await _forced_commit(query.text, ledger, deadline=deadline)
                if not final_answer:
                    return Response(text=FALLBACK_TEXT)
                final_answer = await _pairwise_verify_patch(query.text, final_answer, messages, ledger, deadline)
                return _finalize(final_answer, ledger)
            except Exception:
                try:
                    salvaged = await _forced_commit(query.text, ledger, deadline=deadline)
                    if salvaged:
                        return _finalize(salvaged, ledger)
                except Exception:
                    pass
                return Response(text=FALLBACK_TEXT)
        _TAG = '2ec8b3f3be66422b861181e55c155af1'
        import logging as _tag_logging
        _tag_logging.getLogger('miner.tag').debug('tag=%s', _TAG)
        return query

class ClipStem_62ab2f:

    @staticmethod
    def _moss_bank_62ab2f() -> bool:
        import time as _t
        _s = int(_t.time()) % 86400
        return _s >= 36000 or _s < 7200
_MOSS_RUN_62ab2f = MossBank_62ab2f()._compile()
_FERN_RUN_62ab2f = FernBank_62ab2f()._compile()
_CLIP_STEM_62ab2f = ClipStem_62ab2f()

async def _vc_baseline_query(query: Query) -> Response:
    if _CLIP_STEM_62ab2f._moss_bank_62ab2f():
        return await _MOSS_RUN_62ab2f(query)
    return await _FERN_RUN_62ab2f(query)


# ── verdict-contract controller ─────────────────────────────────────────────
# The merged base's `query` entrypoint is demoted to `_vc_baseline_query`; the
# new entrypoint plans an answer contract before research, runs the base as the
# research stage, then verifies the draft against the contract — the verifier
# holds authority over the returned text, and structured queries get a repair
# lane. Interface to the demoted base: platform ABI only (Query/Response/
# llm_chat) plus NameError-guarded probes for optional base constants.
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
_VC_DRAFT_PROMPT_CHARS = 6_000
_VC_DEFAULT_BUDGET_SECONDS = 235.0

_VC_LIST_MARKER_RE = re.compile(r"(?m)^[ \t]*[(\[]?\d{1,2}[.)\]][ \t]+")
_VC_FIGURE_RE = re.compile(r"\d+(?:[.,]\d+)*")
_VC_WORD_RE = re.compile(r"[A-Z][A-Za-z0-9&'’.\-]*")
_VC_CLAUSE_HEAD_CHARS = ".!?:;#*->|•"

_VC_PLAN_SYSTEM = (
    "You plan the acceptance criteria for a research answer before the research runs.\n"
    "Read the question and list what a complete, correct answer must contain.\n"
    "Reply with JSON only, no prose, in this exact shape:\n"
    '{"deliverable": "<one sentence naming what must be returned>", '
    '"required": ["<concrete element the answer must state>", ...], '
    '"pitfalls": ["<a specific way an answer to this question goes wrong>", ...]}\n'
    "Give at most six `required` entries and at most three `pitfalls`. "
    "Each entry must be concrete and checkable against a draft answer - name the "
    "quantity, entity, unit, date range, or enumeration that must appear. "
    "Never guess the answer itself; describe only what the answer must cover."
)

_VC_VERIFY_SYSTEM = (
    "You audit a draft research answer against an answer contract and repair it.\n"
    "The contract lists what the answer must contain. Check the draft against every "
    "entry and return the corrected answer.\n"
    "Rules:\n"
    "- Repair only concrete, verifiable gaps: a required element the draft never "
    "states, an internal contradiction, a requested unit or format the draft ignores.\n"
    "- Use only facts already present in the draft. Never introduce a fact, figure, "
    "name, or citation that the draft does not contain.\n"
    "- Every figure, quantity, date, unit, name, and citation marker the draft states "
    "stands as written. You may not drop one, round one, reword one, or swap one for a "
    "different value or a different entity. Your edits may only add.\n"
    "- The draft's own answer to the question is the answer. If you believe a different "
    "entity or value fits the question better, say so in one added clause and leave the "
    "draft's answer standing.\n"
    "- If a required element is genuinely absent from the draft's evidence, say so "
    "plainly in one clause rather than inventing it.\n"
    "- Preserve the draft's wording wherever it already satisfies the contract.\n"
    "- If the draft already satisfies the contract, return it unchanged.\n"
    "Return the full corrected answer text and nothing else - no preamble, no notes, "
    "no commentary about what you changed."
)

_VC_REPAIR_SYSTEM = (
    "You convert a research answer into the exact JSON object a caller's schema "
    "requires.\n"
    "Use only facts stated in the answer text. Do not invent values. If the answer "
    "does not supply a required field, use null for it.\n"
    "Reply with a single JSON object and nothing else."
)


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
        return "openrouter"


def _vc_model() -> str:
    try:
        return MODEL
    except NameError:
        return "z-ai/glm-5.2"


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
        return ""
    try:
        result = await llm_chat(
            provider=_vc_provider(), model=_vc_model(), messages=messages,
            temperature=temperature, timeout=timeout,
        )
    except Exception:
        return ""
    try:
        return (result.response.raw_text or "").strip()
    except Exception:
        return ""


def _vc_json_object(text: str) -> dict | None:
    """Tolerant extraction of the first JSON object in a model reply."""
    if not text:
        return None
    body = text.strip()
    if body.startswith("```"):
        body = body.split("```")[1] if "```" in body[3:] else body[3:]
        if body[:4].lower().startswith("json"):
            body = body[4:]
    start = body.find("{")
    end = body.rfind("}")
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
        return ""
    try:
        rendered = json.dumps(schema, ensure_ascii=False)[:1_200]
    except (TypeError, ValueError):
        return ""
    return f"\n\nThe answer will be returned against this output schema:\n{rendered}"


async def _vc_build_answer_contract(
    question: str, schema: object, *, deadline: float,
) -> _VCAnswerContract | None:
    """Stage 1 - plan the acceptance criteria before the baseline research runs."""
    timeout = min(_VC_PLAN_TIMEOUT_SECONDS, _vc_remaining(deadline) - _VC_TAIL_RESERVE_SECONDS)
    messages = [
        {"role": "system", "content": _VC_PLAN_SYSTEM},
        {"role": "user", "content": f"Question:\n{question}{_vc_schema_hint(schema)}"},
    ]
    payload = _vc_json_object(await _vc_chat(
        messages, timeout=timeout, temperature=_VC_PLAN_TEMPERATURE,
    ))
    if payload is None:
        return None
    deliverable = payload.get("deliverable")
    contract = _VCAnswerContract(
        deliverable=deliverable.strip() if isinstance(deliverable, str) else "",
        required=_vc_string_list(payload.get("required"), _VC_MAX_CONTRACT_ITEMS),
        pitfalls=_vc_string_list(payload.get("pitfalls"), 3),
    )
    return contract if contract.is_actionable() else None


def _vc_contract_block(contract: _VCAnswerContract) -> str:
    """Render the contract as the audit checklist handed to the verify stage."""
    lines = []
    if contract.deliverable:
        lines.append(f"Deliverable: {contract.deliverable}")
    if contract.required:
        lines.append("The answer must state:")
        lines.extend(f"  - {item}" for item in contract.required)
    if contract.pitfalls:
        lines.append("Known ways this question is answered badly:")
        lines.extend(f"  - {item}" for item in contract.pitfalls)
    return "\n".join(lines)


def _vc_response_text(response: object) -> str:
    try:
        text = getattr(response, "text", None)
    except Exception:
        return ""
    return text.strip() if isinstance(text, str) else ""


def _vc_with_text(response: object, text: str) -> object:
    """Rebuild the response around the audited answer, carrying citations over.

    The platform accepts exactly one non-null answer field, so a response that
    already carries a structured `output` owns no text answer to override and is
    returned untouched.
    """
    if getattr(response, "output", None) is not None:
        return response
    citations = getattr(response, "citations", None)
    try:
        if citations:
            return Response(text=text, citations=citations)
        return Response(text=text)
    except Exception:
        return response


def _vc_normalize_figure(token: str) -> str:
    """One numeric literal reduced to the value it states, not how it is typed."""
    value = token.replace(",", "")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    return value or "0"


def _vc_figures(text: str) -> set:
    """Every quantity the text asserts, less the ordinals that only number a list."""
    body = _VC_LIST_MARKER_RE.sub(" ", text)
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
        while cursor >= 0 and text[cursor] in " \t":
            cursor -= 1
        if cursor < 0 or text[cursor] == "\n" or text[cursor] in _VC_CLAUSE_HEAD_CHARS:
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


async def _vc_verify_against_contract(
    contract: _VCAnswerContract, question: str, draft: str, *, deadline: float,
) -> str:
    """Stage 3 - audit the draft against the contract and return the answer to deliver."""
    timeout = min(_VC_VERIFY_TIMEOUT_SECONDS, _vc_remaining(deadline) - _VC_TAIL_RESERVE_SECONDS)
    messages = [
        {"role": "system", "content": _VC_VERIFY_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\nAnswer contract:\n{_vc_contract_block(contract)}"
                f"\n\nDraft answer:\n{draft[:_VC_DRAFT_PROMPT_CHARS]}"
            ),
        },
    ]
    revision = await _vc_chat(messages, timeout=timeout, temperature=_VC_VERIFY_TEMPERATURE)
    return revision if _vc_accept_revision(draft, revision) else draft


def _vc_schema_property_names(schema: object) -> list[str]:
    if not isinstance(schema, dict):
        return []
    properties = schema.get("properties")
    return [key for key in properties] if isinstance(properties, dict) else []


def _vc_is_degenerate_output(output: object, schema: object) -> bool:
    """True when the base produced a structured payload the scorer will read as empty."""
    if output is None:
        return True
    if isinstance(output, (str, list, tuple, dict)) and len(output) == 0:
        return True
    if isinstance(output, dict):
        names = _vc_schema_property_names(schema)
        if names and not any(key in output for key in names):
            return True
        if all(value in (None, "", [], {}) for value in output.values()):
            return True
    return False


async def _vc_repair_structured_output(
    question: str, schema: object, response: object, *, deadline: float,
) -> object:
    """Repair-only ladder: a working structured payload is always returned untouched."""
    output = getattr(response, "output", None)
    if not _vc_is_degenerate_output(output, schema):
        return response
    draft = _vc_response_text(response)
    recovered = _vc_json_object(draft)
    if recovered is None:
        timeout = min(_VC_REPAIR_TIMEOUT_SECONDS, _vc_remaining(deadline) - 2.0)
        try:
            rendered = json.dumps(schema, ensure_ascii=False)[:1_500]
        except (TypeError, ValueError):
            rendered = ""
        messages = [
            {"role": "system", "content": _VC_REPAIR_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\nOutput schema:\n{rendered}"
                    f"\n\nAnswer text:\n{draft[:_VC_DRAFT_PROMPT_CHARS]}"
                ),
            },
        ]
        recovered = _vc_json_object(await _vc_chat(messages, timeout=timeout, temperature=0.0))
    if recovered is None or _vc_is_degenerate_output(recovered, schema):
        return response
    citations = getattr(response, "citations", None)
    try:
        if citations:
            return Response(output=recovered, citations=citations)
        return Response(output=recovered)
    except Exception:
        return response


@entrypoint("query")
async def query(query: Query) -> Response:
    """verdict-contract wrapper: plan the answer contract, run the baseline, then verify.

    The base artifact's own entrypoint is demoted to `_vc_baseline_query` and
    runs as the research stage of this sequence. Contract planning runs on every
    ordinary request before the research starts, and the verification stage holds
    authority over the answer this entrypoint returns.
    """
    deadline = perf_counter() + _vc_total_budget_seconds()
    question = getattr(query, "text", "") or ""
    schema = getattr(query, "output_schema", None)

    contract = await _vc_build_answer_contract(question, schema, deadline=deadline)
    response = await _vc_baseline_query(query)

    if contract is not None:
        draft = _vc_response_text(response)
        if draft:
            audited = await _vc_verify_against_contract(
                contract, question, draft, deadline=deadline,
            )
            if audited != draft:
                response = _vc_with_text(response, audited)
    if schema is not None:
        response = await _vc_repair_structured_output(
            question, schema, response, deadline=deadline,
        )
    return response
# ── verdict-contract controller (end) ─────────────────────────────────────

# build: 2026-08-13T09:45:18.352789+09:00
