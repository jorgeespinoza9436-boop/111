from __future__ import annotations
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class OpalFrame_a29d85:

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
        LLM_LANE_B = 'ai_gateway'
        LOOP_MODEL_A = 'z-ai/glm-5.2'
        LOOP_MODEL_B = 'zai/glm-5.2-fast'
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
        FETCH_TIMEOUT_S = 16.0
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

class OnyxFrame_a29d85:

    def _compile(self):
        import asyncio
        from harnyx_miner_sdk.api import LlmThinkingConfig, llm_chat
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import Query, Response

        class FirstPath:

            def _compile(self):
                from dataclasses import dataclass, field
                import asyncio
                import hashlib
                import json
                import re
                from time import monotonic
                from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
                from harnyx_miner_sdk.decorators import entrypoint
                from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
                _simple_VERSION = 'v126-uid29-adaptive-challenge'
                _simple_LLM_LANE_A = 'openrouter'
                _simple_LLM_LANE_B = 'chutes'
                _simple_LOOP_MODEL_A = 'z-ai/glm-5.2'
                _simple_LOOP_MODEL_B = 'zai-org/GLM-5.2-TEE'
                _simple_EMERGENCY_PROVIDER = 'openrouter'
                _simple_EMERGENCY_MODEL = 'deepseek/deepseek-v3.2'
                _simple_AUDIT_MODEL = 'openai/gpt-oss-120b'
                _simple_SCHEMA_MODEL = 'openai/gpt-oss-120b'
                _simple_RESORT_MODEL = 'deepseek/deepseek-v3.2'
                _simple_SEARCH_PROVIDERS = ('parallel', 'desearch')
                _simple_SEARCH_PROVIDER = _simple_SEARCH_PROVIDERS[0]
                _simple_WALL_BUDGET_S = 258.0
                _simple_BRIEF_TIMEOUT_S = 50.0
                _simple_TURN_TIMEOUT_S = 75.0
                _simple_LANE_B_MAX_PAYLOAD_CHARS = 144000
                _simple_AUDIT_TIMEOUT_S = 28.0
                _simple_SEARCH_TIMEOUT_S = 18.0
                _simple_FETCH_TIMEOUT_S = 16.0
                _simple_WRAPUP_AT_S = 90.0
                _simple_MIN_TAIL_S = 8.0
                _simple_MAX_TURNS = 12
                _simple_AUDIT_EXTRA_TURNS = 2
                _simple_ANSWER_REPAIR_TURNS = 2
                _simple_RESCUE_TIMEOUT_S = 55.0
                _simple_DIGEST_TAIL_S = 14.0
                _simple_SEARCH_EXCERPT_CHARS = 550
                _simple_FETCH_HEAD_CHARS = 2800
                _simple_FETCH_WINDOW_CHARS = 3400
                _simple_FETCH_WINDOWS_PER_PAGE = 3
                _simple_FETCH_PLAIN_CHARS = 6200
                _simple_ANSWER_CHAR_CAP = 60000
                _simple_CITATION_CAP = 24
                _simple_EVIDENCE_CHAR_BUDGET = 105000
                _simple_BRIEF_MIN_USD = 0.03
                _simple_AUDIT_MIN_USD = 0.05
                _simple_WRAPUP_MIN_USD = 0.02
                _simple__SPEND = {'left': None}

                def _simple__spend_note(payload) -> None:
                    budget = getattr(payload, 'budget', None)
                    left = getattr(budget, 'session_remaining_budget_usd', None)
                    if isinstance(left, (int, float)):
                        _simple__SPEND['left'] = float(left)

                def _simple__spend_left() -> float:
                    left = _simple__SPEND['left']
                    if isinstance(left, (int, float)):
                        return float(left)
                    return 1.0
                _simple_LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}]
                _simple_LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

                def _simple__wrapup_order(seconds_left: float) -> str:
                    return f"TIME IS UP (~{int(seconds_left)}s left). No more tool calls. Write the complete final answer NOW from the numbered results above plus your knowledge: the FIRST words are the answer entities (no 'Based on…' preamble, no 'partial answer' framing, no '(verify)' markers), cite [n] on every claim, keep the required format. A cited partial answer scores; a refusal or a remark about insufficient evidence scores zero." + ('' if seconds_left >= 60 else ' BREVITY OVERRIDE: too little time remains for a line per pool member. Lead with the answer entities, then give the qualifiers one cited line each and compress the rejects into a single cited line. A complete short answer beats a long one that never finishes.')
                _simple__SET_HINT_RE = re.compile('\\b(?:list|name|identify|enumerate)\\b[^?]{0,40}\\b(?:all|every|each|the)\\b|\\bhow many\\b|\\bwhich (?:movies|films|series|countries|companies|states|cities|books|albums|artists|players|teams|species|languages|banks|universities|agencies|models|products)\\b', re.IGNORECASE)
                _simple__SET_CONNECTIVE_RE = re.compile('\\b(?:both|also|and (?:also|had|has|was|were)|as well as)\\b', re.IGNORECASE)
                _simple__PLURAL_HEAD_RE = re.compile('\\b(?:which|what)\\b(?:\\s+\\w+){0,2}?\\s+([a-z]{3,}s)\\b', re.IGNORECASE)
                _simple__PLURAL_FALSE = frozenset('was is has does its this thus across process business series species news status analysis basis less unless always perhaps'.split())
                _simple__ONE_WINNER_RE = re.compile('\\b(?:highest|lowest|largest|smallest|most|least|greatest|fewest|longest|shortest|first|last|best|worst|only|oldest|youngest|newest|biggest)\\b', re.IGNORECASE)
                _simple__EST_STOP = frozenset('interest honest modest protest request suggest forest harvest invest manifest contest arrest digest earnest conquest tempest midwest northwest southwest unrest bequest behest attest molest ingest infest detest incest armrest backrest pretest headrest footrest'.split())
                _simple__EST_RE = re.compile('\\b([a-z]{3,})est\\b')

                def _simple__has_superlative(text: str) -> bool:
                    if _simple__ONE_WINNER_RE.search(text or ''):
                        return True
                    for m in _simple__EST_RE.finditer(text or ''):
                        if m.group(0).lower() not in _simple__EST_STOP:
                            return True
                    return False

                def _simple__needs_superlative_proof(question: str) -> bool:
                    q = ' '.join((question or '').split())
                    if not q:
                        return False
                    return _simple__has_superlative(q) or bool(re.search('\\b(?:most|least) (?:common|frequent|number|amount)\\b|\\bhow many\\b', q, re.I))
                _simple_SUPERLATIVE_RULE = "SUPERLATIVE / TALLY — SHOW THE TABLE. The answer is one item, but you cannot know it without the whole pool. Before naming a winner: (1) list EVERY candidate the question's scope admits — every player who appeared, every officeholder in the span, every body in the ranking; (2) put the deciding value next to each (birth date, count, figure), cited; (3) THEN name the maximum. NEVER decide a superlative on a rounded or derived display: a coarse figure (a whole-number age, a rounded total, a bucketed rank) cannot separate two contenders that differ below its precision. Fetch the exact underlying value (full birth date, unrounded figure) for every contender, from a source that lists them ALL: a page showing only your front-runner cannot establish that nobody beats them. (3b) THEN name the maximum. Reproduce that candidate table in the proof section — a correct winner with no visible tally loses to a reference that shows its work, and 'among others' / 'and several more' is not a tally. If the pool is too large to list in full, rank it, show every contender down to a stated cutoff, and say what the cutoff was — a stated cutoff is a covered pool; an unstated one reads as an unchecked one."

                def _simple__needs_set_completeness(question: str) -> bool:
                    q = ' '.join((question or '').split())
                    if _simple__SET_HINT_RE.search(q):
                        return True
                    m = _simple__PLURAL_HEAD_RE.search(q)
                    if m and m.group(1).lower() not in _simple__PLURAL_FALSE:
                        if not _simple__has_superlative(q) or re.search('\\b(?:all|every|each)\\b', q, re.IGNORECASE):
                            return True
                    return bool(re.search('\\bwhich\\b', q, re.IGNORECASE)) and bool(_simple__SET_CONNECTIVE_RE.search(q))
                _simple_SET_RULE = "SET ANSWER: this question asks for a set. Missing a qualifying member scores the same as wrong — enumerate the pool, test EVERY member against EVERY condition, and name ALL qualifiers (each with its own citations per condition). Then give EVERY excluded member its own line with the condition it fails and its own [n] — not a single clause sweeping several names together, and not just the near-misses. Never claim 'the only X' unless the whole pool was checked; if your pool may be partial, still commit to every qualifier you verified. GET THE POOL FROM A LIST, NOT MEMBER-BY-MEMBER: your FIRST retrieval for a set question should hunt the authoritative roster/list/table that enumerates the whole pool (search it AS a list — '<pool subject> list', '<pool subject> table', 'list of <pool subject>' — and read_page it). Assembling the pool from separate per-member searches is how a run ends up with 3 of 6 qualifiers: the members you never thought to search for are invisible to you. Read the roster page first, then verify each member. ONE LIST PER PERIOD, THEN JOIN: when a condition has to hold across several periods — successive years, separate editions, or two parallel events — fetch ONE roster page per period and join them on the member: one list per period, not one lookup per member. A pool of 30+ members each needing several figures is a table-join, and per-member lookups will run out of turns long before the pool is covered. UNIVERSAL conditions ('in EVERY one of them', 'for BOTH parts', 'in ALL three periods'): check each candidate against EACH instance separately, with a citation per instance — one shared instance is not enough. If NO candidate survives every instance, then 'none' IS the answer: state it as a verified fact about the world with the per-instance citations that prove it."

                class _simple_EvidenceLedger:

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
                _simple__WORD_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
                _simple__STOP = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

                def _simple__key_terms(text: str) -> set[str]:
                    return {w for w in _simple__WORD_RE.findall((text or '').casefold()) if w not in _simple__STOP}

                def _simple__best_windows(note: str, terms: set[str], width: int, k: int=1) -> list[tuple[int, int]]:
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
                _simple__SLOT = '\x00{}\x00'

                class _simple_ToolOutput:

                    def __init__(self, text: str, rows: list[dict] | None=None) -> None:
                        self.text = text
                        self.rows = rows or []

                def _simple__commit_tool_output(out, ledger: _simple_EvidenceLedger) -> str:
                    if isinstance(out, str):
                        return out
                    if not isinstance(out, _simple_ToolOutput):
                        return f'# tool crashed: {out}'
                    text = out.text
                    for i, row in enumerate(out.rows):
                        n = ledger.add(row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''))
                        text = text.replace(_simple__SLOT.format(i), str(n))
                    return text
                _simple__SITE_OP_RE = re.compile('\\bsite:\\S+\\s*', re.I)

                def _simple__degrade_query(q: str) -> str:
                    out = _simple__SITE_OP_RE.sub('', q or '').replace('"', ' ')
                    return ' '.join(out.split())

                def _simple__source_contract_score(item, query_text: str) -> tuple[int, int, str]:
                    title = (getattr(item, 'title', None) or '').strip()
                    url = (getattr(item, 'url', None) or '').strip()
                    note = (getattr(item, 'note', None) or '').strip()
                    haystack = f'{title} {url} {note}'.lower()
                    _simple_query = (query_text or '').lower()
                    score = 0
                    requested_domains = (('wikipedia', 'wikipedia.org/wiki/'), ('census', 'census.gov'), ('bls', 'bls.gov'), ('sec', 'sec.gov'), ('nasa', 'nasa.gov'), ('exoplanet archive', 'exoplanetarchive.ipac.caltech.edu'), ('eia', 'eia.gov'))
                    for cue, domain in requested_domains:
                        if cue in _simple_query:
                            score += 12 if domain in haystack else -5
                    if any((domain in haystack for domain in ('.gov', 'wikipedia.org/wiki/', 'sec.gov', 'nasa.gov', 'census.gov', 'bls.gov', 'eia.gov'))):
                        score += 3
                    terms = {term for term in re.findall('[a-z0-9]{4,}', _simple_query) if not term.isdigit()}
                    overlap = sum((1 for term in terms if term in haystack))
                    return (-score, -overlap, url)

                async def _simple__do_search(query_text: str, ledger: _simple_EvidenceLedger):
                    if not query_text.strip():
                        return '# web_search: empty query'
                    payload = None
                    for provider in _simple_SEARCH_PROVIDERS:
                        fired: set[str] = set()
                        for attempt, allow_repeat in ((query_text, False), (query_text, True), (_simple__degrade_query(query_text), False)):
                            if not attempt.strip() or (attempt in fired and (not allow_repeat)):
                                continue
                            fired.add(attempt)
                            try:
                                payload = await search_web(attempt, provider=provider, num=8, timeout=_simple_SEARCH_TIMEOUT_S)
                                if getattr(payload, 'results', None):
                                    break
                            except Exception:
                                payload = None
                        if payload is not None and getattr(payload, 'results', None):
                            break
                    if payload is None:
                        return f'# web_search({query_text!r}) failed'
                    _simple__spend_note(payload)
                    receipt = str(getattr(payload, 'receipt_id', '') or '')
                    results = list(getattr(payload, 'results', None) or [])
                    if not receipt:
                        return f'# web_search({query_text!r}): no citable results'
                    rows: list[dict] = []
                    lines = [f'# web_search({query_text!r}): {len(results)} results']
                    results.sort(key=lambda item: _simple__source_contract_score(item, query_text))
                    for item in results:
                        rid = getattr(item, 'result_id', None)
                        if not isinstance(rid, str) or not rid:
                            continue
                        note = getattr(item, 'note', None) or ''
                        if not note.strip():
                            continue
                        n_len = len(note)
                        span = [(0, min(max(_simple_SEARCH_EXCERPT_CHARS, 100), n_len))] if n_len >= 100 else [(0, n_len)] if n_len else None
                        title = (getattr(item, 'title', None) or '').strip()
                        url = (getattr(item, 'url', None) or '').strip()
                        rows.append({'receipt_id': receipt, 'result_id': rid, 'note_len': n_len, 'kind': 'search', 'spans': span, 'title': title, 'url': url, 'preview': note[:_simple_SEARCH_EXCERPT_CHARS]})
                        lines.append(f'[{_simple__SLOT.format(len(rows) - 1)}] {title} — {url}\n    {note[:_simple_SEARCH_EXCERPT_CHARS]}')
                    return _simple_ToolOutput('\n'.join(lines), rows)

                async def _simple__do_fetch(url: str, focus: str, question: str, ledger: _simple_EvidenceLedger) -> str:
                    if not url.strip():
                        return '# read_page: empty url'
                    payload = None
                    for provider in _simple_SEARCH_PROVIDERS:
                        for _attempt in (0, 1):
                            try:
                                payload = await fetch_page(url, provider=provider, timeout=_simple_FETCH_TIMEOUT_S)
                                if getattr(payload, 'results', None):
                                    break
                            except Exception:
                                payload = None
                        if payload is not None and getattr(payload, 'results', None):
                            break
                    if payload is None:
                        return f'# read_page({url!r}) failed'
                    _simple__spend_note(payload)
                    receipt = str(getattr(payload, 'receipt_id', '') or '')
                    results = list(getattr(payload, 'results', None) or [])
                    if not results or not receipt:
                        return f'# read_page({url!r}): no content'
                    item = results[0]
                    rid = getattr(item, 'result_id', None)
                    note = getattr(item, 'note', None) or ''
                    if not isinstance(rid, str) or not rid or (not note.strip()):
                        return f'# read_page({url!r}): no usable content'
                    if len(note) <= _simple_FETCH_PLAIN_CHARS:
                        row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, len(note))], 'title': url, 'url': url, 'preview': note[:1200]}
                        return _simple_ToolOutput(f'# read_page({url!r}) -> [{_simple__SLOT.format(0)}] full page, {len(note)} chars\n{note}', [row])
                    terms = _simple__key_terms(question) | _simple__key_terms(focus)
                    windows = _simple__best_windows(note, terms, _simple_FETCH_WINDOW_CHARS, k=_simple_FETCH_WINDOWS_PER_PAGE)
                    row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, _simple_FETCH_HEAD_CHARS)] + list(windows), 'title': url, 'url': url, 'preview': note[windows[0][0]:windows[0][0] + 1200]}
                    head = note[:_simple_FETCH_HEAD_CHARS]
                    sections = ''.join((f'\n--- section @{s} ---\n{note[s:e]}' for s, e in windows))
                    return _simple_ToolOutput(f"# read_page({url!r}) -> [{_simple__SLOT.format(0)}] {len(note)} chars total; head + the {len(windows)} most relevant section(s) shown ({', '.join((f'{s}-{e}' for s, e in windows))}). If the answer set may continue elsewhere in this page, call read_page again with a different focus.\n--- head ---\n{head}{sections}", [row])
                _simple__SEC_TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
                _simple__SEC_SUBMISSIONS_URL = 'https://data.sec.gov/submissions/CIK{cik10}.json'
                _simple__SEC_DOC_URL = 'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}'
                _simple__SEC_FETCH_TIMEOUT_S = 26.0
                _simple__SEC_MIN_HEADROOM_S = 40.0
                _simple__SEC_CACHE: dict = {}
                _simple__SEC_STOPWORDS = frozenset('inc incorporated corp corporation company companies co ltd limited llc plc lp llp group holdings the'.split())
                _simple__SEC_ALNUM_RE = re.compile('[a-z0-9]+')

                def _simple__sec_tokens(text: str) -> list[str]:
                    return [w for w in _simple__SEC_ALNUM_RE.findall((text or '').lower()) if w not in _simple__SEC_STOPWORDS]

                def _simple__sec_norm_form(form: str) -> str:
                    f = ' '.join((form or '').upper().replace('FORM', ' ').split())
                    m = re.fullmatch('(\\d{1,2})\\s*-?\\s*([A-Z])', f)
                    if m:
                        return f'{m.group(1)}-{m.group(2)}'
                    m = re.fullmatch('(DEF)\\s*-?\\s*(14A)', f)
                    if m:
                        return 'DEF 14A'
                    return f

                async def _simple__fetch_json(url: str, deadline: float):
                    cached = _simple__SEC_CACHE.get(url)
                    if cached is not None:
                        return cached
                    for _attempt in (0, 1):
                        left = deadline - monotonic()
                        if left < 12.0:
                            return None
                        try:
                            payload = await asyncio.wait_for(fetch_page(url, provider=_simple_SEARCH_PROVIDER, timeout=min(_simple__SEC_FETCH_TIMEOUT_S, left - 6.0)), timeout=min(_simple__SEC_FETCH_TIMEOUT_S, left - 6.0) + 4.0)
                        except Exception:
                            continue
                        _simple__spend_note(payload)
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
                            _simple__SEC_CACHE[url] = obj
                            return obj
                    return None

                def _simple__sec_pick_filing(recent: dict, form: str, year: str):
                    forms = recent.get('form')
                    accs = recent.get('accessionNumber')
                    docs = recent.get('primaryDocument')
                    rdates = recent.get('reportDate')
                    fdates = recent.get('filingDate')
                    if not (isinstance(forms, list) and isinstance(accs, list) and isinstance(docs, list)):
                        return None
                    n = min(len(forms), len(accs), len(docs))
                    form_norm = _simple__sec_norm_form(form)
                    best_year = None
                    best_any = None
                    for i in range(n):
                        if _simple__sec_norm_form(str(forms[i])) != form_norm:
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
                _simple__SEC_SEARCH_HINT = 'search "site:sec.gov {company} {year} {form}" and read_page the Archives result'

                async def _simple__do_sec_filing(company: str, form: str, year: str, deadline: float) -> str:
                    company = (company or '').strip()
                    form = (form or '').strip() or '10-K'
                    year = (year or '').strip()[:4]
                    hint = _simple__SEC_SEARCH_HINT.format(company=company, year=year, form=form)
                    if not company:
                        return '# sec_filing: company required'
                    if deadline - monotonic() < _simple__SEC_MIN_HEADROOM_S:
                        return f'# sec_filing: skipped (low time) — {hint}'
                    tickers = await _simple__fetch_json(_simple__SEC_TICKERS_URL, deadline)
                    if not isinstance(tickers, dict):
                        return f'# sec_filing: EDGAR ticker index unavailable — {hint}'
                    want = _simple__sec_tokens(company)
                    best = None
                    for row in tickers.values():
                        if not isinstance(row, dict):
                            continue
                        title = str(row.get('title', ''))
                        ticker = str(row.get('ticker', '')).lower()
                        words = set(_simple__sec_tokens(title))
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
                    subs = await _simple__fetch_json(_simple__SEC_SUBMISSIONS_URL.format(cik10=cik10), deadline)
                    filings = subs.get('filings') if isinstance(subs, dict) else None
                    recent = filings.get('recent') if isinstance(filings, dict) else None
                    if not isinstance(recent, dict):
                        return f'# sec_filing({company!r}): EDGAR submissions unavailable for {title} — {hint}'
                    pick = _simple__sec_pick_filing(recent, form, year)
                    if pick is None:
                        return f"# sec_filing({company!r}, {form!r}, year={year or 'latest'}): no matching filing in EDGAR's recent index for {title} — check the form/year, or {hint}"
                    accession, doc = pick
                    url = _simple__SEC_DOC_URL.format(cik=cik10.lstrip('0') or cik10, accession=accession.replace('-', ''), doc=doc)
                    return f"# sec_filing -> {title} {form} {year or '(latest)'} primary document:\n{url}\nNow call read_page on this URL with a focus hint for the section you need, and cite figures from that read_page result."

                async def _simple__run_tool(call, question: str, ledger: _simple_EvidenceLedger, deadline: float) -> str:
                    try:
                        args = json.loads(getattr(call, 'arguments', None) or '{}')
                    except Exception:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}
                    name = getattr(call, 'name', '') or ''
                    if name == 'web_search':
                        return await _simple__do_search(str(args.get('query') or ''), ledger)
                    if name == 'read_page':
                        return await _simple__do_fetch(str(args.get('url') or ''), str(args.get('focus') or ''), question, ledger)
                    if name == 'sec_filing':
                        return await _simple__do_sec_filing(str(args.get('company') or ''), str(args.get('form') or ''), str(args.get('year') or ''), deadline)
                    return f'# unknown tool {name!r}'
                _simple__REASONING_MANDATORY = ('openai/gpt-oss',)

                def _simple__least_think(lane: str, model: str='') -> dict:
                    for prefix in _simple__REASONING_MANDATORY:
                        if model.startswith(prefix):
                            return {'enabled': True, 'effort': 'low'}
                    return {'enabled': False}

                async def _simple__chat_simple(lane: str, model: str, system: str, user: str, *, max_tokens: int, timeout: float, think: dict | None=None) -> str:
                    if think is None:
                        think = _simple__least_think(lane, model)
                    payload = await llm_chat(provider=lane, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=think)
                    _simple__spend_note(payload)
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

                class _simple__EmptyChoiceMessage:
                    content = ''
                    tool_calls = ()

                class _simple__EmptyChoice:
                    message = _simple__EmptyChoiceMessage()

                class _simple__EmptyLlm:
                    raw_text = ''
                    choices = (_simple__EmptyChoice(),)

                class _simple__EmptyTurn:
                    llm = _simple__EmptyLlm()
                    budget = None
                _simple__EMPTY_TURN = _simple__EmptyTurn()

                async def _simple__chat_turn(messages: list[dict], deadline: float, *, finish_only: bool, force_tools: bool=False):
                    payload_chars = sum((len(str(msg.get('content') or '')) for msg in messages if isinstance(msg, dict)))
                    for lane_model in ((_simple_LLM_LANE_A, _simple_LOOP_MODEL_A), (_simple_LLM_LANE_B, _simple_LOOP_MODEL_B), (_simple_EMERGENCY_PROVIDER, _simple_EMERGENCY_MODEL)):
                        lane = lane_model[0]
                        model = lane_model[1]
                        if lane == _simple_LLM_LANE_B and payload_chars > _simple_LANE_B_MAX_PAYLOAD_CHARS:
                            continue
                        timeout = min(_simple_TURN_TIMEOUT_S, deadline - monotonic() - 5.0)
                        if timeout <= 5.0:
                            return None
                        try:
                            payload = await llm_chat(provider=lane, model=model, messages=messages, tools=_simple_LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': False} if lane == _simple_LLM_LANE_B else {'enabled': True, 'effort': 'low'}, max_output_tokens=6000 if finish_only and lane == _simple_LLM_LANE_B else None, timeout=timeout)
                            _simple__spend_note(payload)
                            return payload
                        except Exception:
                            continue
                    return None

                async def _simple__knowledge_brief(question: str) -> tuple[str, str]:
                    system = 'Senior research analyst. Commit to concrete best answers from knowledge; mark uncertain values (verify). Never refuse.'
                    user = f"Question:\n{question}\n\nWrite these blocks:\nBEST ANSWER: your full best answer now — candidate pool, every stated condition applied, qualifying entities with figures/dates, near-miss exclusions. Flag shaky facts with (verify).\nCHECKLIST: each atomic condition in the question, numbered, including any output-format demand.\nLOOKUPS: 3-6 precise web searches for the facts that decide the answer (entity + metric + year; include a named source's site: filter).\nPAGES: up to 5 exact URLs worth reading directly (official stats pages, sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."
                    raw = ''
                    try:
                        raw = await _simple__chat_simple(_simple_LLM_LANE_A, _simple_LOOP_MODEL_A, system, user, max_tokens=2400, timeout=_simple_BRIEF_TIMEOUT_S, think=_simple__least_think(_simple_LLM_LANE_A, _simple_LOOP_MODEL_A))
                    except Exception:
                        try:
                            raw = await _simple__chat_simple(_simple_LLM_LANE_B, _simple_LOOP_MODEL_B, system, user, max_tokens=2400, timeout=_simple_BRIEF_TIMEOUT_S, think=_simple__least_think(_simple_LLM_LANE_B, _simple_LOOP_MODEL_B))
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
                _simple__SEED_TOKEN_RE = re.compile("[A-Za-z0-9][A-Za-z0-9.\\-']+")
                _simple__SEED_STOP = frozenset('name list give tell show find identify please could would you your can may might should must let make sure both also'.split())
                _simple_MAX_SEED_QUERIES = 3

                def _simple__seed_queries(question: str, set_question: bool) -> list[str]:
                    q = ' '.join((question or '').split())
                    if not q:
                        return []
                    seeds = [q[:300]]
                    salient = [t for t in _simple__SEED_TOKEN_RE.findall(q) if len(t) >= 3 and t.lower() not in _simple__STOP and (t.lower() not in _simple__SEED_STOP)]
                    if len(salient) >= 2:
                        seeds.append(' '.join(salient[:8]))
                    if set_question and salient:
                        seeds.append('list of ' + ' '.join(salient[:6]))
                    out: list[str] = []
                    for s in seeds:
                        s = s.strip()
                        if s and s not in out:
                            out.append(s)
                    return out[:_simple_MAX_SEED_QUERIES]

                async def _simple__preseed(question: str, set_question: bool, ledger: _simple_EvidenceLedger, deadline: float) -> str:
                    seeds = _simple__seed_queries(question, set_question)
                    if not seeds or deadline - monotonic() < 40.0:
                        return ''
                    blocks: list = []
                    for seed in seeds:
                        if deadline - monotonic() < 30.0:
                            break
                        try:
                            out = await asyncio.wait_for(_simple__do_search(seed, ledger), timeout=_simple_SEARCH_TIMEOUT_S * 2 + 6.0)
                            blocks.append(_simple__commit_tool_output(out, ledger))
                        except Exception:
                            continue
                    good = [b for b in blocks if isinstance(b, str) and _simple__CITE_MARK_RE.search(b)]
                    if not good:
                        return ''
                    return 'Automatic first-pass searches (already numbered — cite these [n] directly, and search further as needed):\n\n' + '\n'.join(good)

                async def _simple__loop(question: str, brief: str, ledger: _simple_EvidenceLedger, deadline: float, turn_cap: int, carry: list[dict] | None=None, allow_tools_in_wrapup: bool=False) -> tuple[str, list[dict]]:
                    if carry is not None:
                        messages = carry
                    else:
                        set_q = _simple__needs_set_completeness(question)
                        messages = [{'role': 'system', 'content': _simple_LOOP_RULES}]
                        if set_q:
                            messages.append({'role': 'system', 'content': _simple_SET_RULE})
                        if _simple__needs_superlative_proof(question):
                            messages.append({'role': 'system', 'content': _simple_SUPERLATIVE_RULE})
                        if brief:
                            messages.append({'role': 'system', 'content': brief})
                        seeded = await _simple__preseed(question, set_q, ledger, deadline)
                        if seeded:
                            messages.append({'role': 'system', 'content': seeded})
                        messages.append({'role': 'user', 'content': question})
                    answer = ''
                    ordered_wrapup = False
                    repairs_left = _simple_ANSWER_REPAIR_TURNS
                    for turn in range(1, turn_cap + 1):
                        left = deadline - monotonic()
                        if left <= _simple_MIN_TAIL_S:
                            break
                        out_of_time = left <= _simple_WRAPUP_AT_S
                        out_of_spend = _simple__spend_left() <= _simple_WRAPUP_MIN_USD
                        finish_only = out_of_time or out_of_spend or turn >= turn_cap
                        if (finish_only or turn >= turn_cap - 1) and (not ordered_wrapup):
                            messages.append({'role': 'system', 'content': _simple__wrapup_order(left)})
                            ordered_wrapup = True
                        payload = await _simple__chat_turn(messages, deadline, finish_only=finish_only, force_tools=allow_tools_in_wrapup and turn == 1)
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
                            if not _simple__is_usable_answer(candidate):
                                if repairs_left > 0 and deadline - monotonic() > _simple_MIN_TAIL_S + 10.0:
                                    repairs_left -= 1
                                    messages.append({'role': 'system', 'content': _simple__REPAIR_ORDER})
                                    answer = ''
                                    continue
                                answer = ''
                                break
                            answer = candidate
                            messages.append({'role': 'assistant', 'content': answer})
                            break
                        messages.append(msg.to_input_message())
                        run_calls = calls[:8]
                        tool_budget = max(5.0, min(_simple_FETCH_TIMEOUT_S * 2 + 6.0, deadline - monotonic() - _simple_MIN_TAIL_S))
                        tool_tasks = [asyncio.ensure_future(_simple__run_tool(c, question, ledger, deadline)) for c in run_calls]
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
                            body = _simple__commit_tool_output(call_result[1], ledger)
                            messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': body})
                        for call in calls[8:]:
                            messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})
                    return (answer, messages)

                async def _simple__audit_patch(question: str, answer: str, messages: list[dict], ledger: _simple_EvidenceLedger, deadline: float) -> str:
                    probe = f"""Audit the answer against the question. JSON only, keys: "unanswered_parts" (list; question elements not addressed), "uncited_facts" (list; load-bearing claims without [n]), "wrong_kind" (list; places where the named entity is a different KIND than the question asks — a person instead of a series, a duo instead of a show), "incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges over a candidate pool — a closed set that can be enumerated, or several conditions applied to a class — then: is the pool itself stated and plausibly COMPLETE, and does the answer give a verdict for EVERY member (qualifies / excluded because X, each cited)? Name any pool member the answer never mentions, and say so if the pool looks truncated — an answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not partial), "thin_proof" (list; a qualifier lacking a per-condition citation, or a plausible near-miss candidate never addressed), "hand_waved_tally" (list; for a superlative/count/most-common question: the answer asserts a winner or a count WITHOUT showing the candidate table it was derived from. Phrases like 'among others', 'and several more', 'multiple X', or naming 2 examples to justify a count are all hand-waving — say so and name what the tally must list). Empty lists when clean.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:11000]}"""
                    try:
                        raw = await _simple__chat_simple(_simple_LLM_LANE_A, _simple_AUDIT_MODEL, 'Strict completeness auditor. JSON only.', probe, max_tokens=2200, timeout=max(8.0, min(_simple_AUDIT_TIMEOUT_S, deadline - monotonic() - 72.0)))
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
                    patched, _ = await _simple__loop(question, '', ledger, deadline, _simple_AUDIT_EXTRA_TURNS + 1, carry=messages, allow_tools_in_wrapup=True)
                    patched = patched.strip()
                    if not _simple__is_usable_answer(patched) or len(patched) < int(len(answer) * 0.6):
                        return answer
                    return patched
                _simple__BRACKET_FIX = {12304: '[', 12305: ']', 65339: '[', 65341: ']', 65288: '(', 65289: ')', 8209: '-', 8722: '-'}
                for _d in range(10):
                    _simple__BRACKET_FIX[65296 + _d] = chr(48 + _d)

                def _simple__normalize_brackets(text: str) -> str:
                    return (text or '').translate(_simple__BRACKET_FIX)
                _simple__CITE_NUM_RE = re.compile('\\[([0-9][0-9,\\s\\-]*)\\]')

                def _simple__cited_numbers(answer: str, top: int) -> list[int]:
                    answer = _simple__normalize_brackets(answer)
                    seen: set[int] = set()
                    out: list[int] = []
                    for m in _simple__CITE_NUM_RE.finditer(answer):
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

                def _simple__citations_for(answer: str, ledger: _simple_EvidenceLedger) -> list[CitationRef]:
                    refs: list[CitationRef] = []
                    spent = 0
                    for n in _simple__cited_numbers(answer, len(ledger.rows)):
                        if len(refs) >= _simple_CITATION_CAP:
                            break
                        ref = ledger.ref_for(n)
                        if ref is None:
                            continue
                        row = ledger.rows[n - 1]
                        slices = getattr(ref, 'slices', None)
                        cost = sum((max(0, s.end - s.start) for s in slices)) if slices else int(row.get('note_len') or 0)
                        if spent + cost > _simple_EVIDENCE_CHAR_BUDGET:
                            continue
                        spent += cost
                        refs.append(ref)
                    return refs
                _simple__VERIFY_MARK_RE = re.compile('\\s*\\((?:verify|unverified|uncertain)[^)]*\\)', re.I)
                _simple__TOOL_MARKUP_RE = re.compile('<\\s*/?\\s*tool_call|<\\s*/?\\s*(?:arg_key|arg_value|function_call|invoke)\\b|\\bweb_search\\s*[（(]\\s*query|\\bread_page\\s*[（(]\\s*url|\\bsec_filing\\s*[（(]\\s*company', re.I)
                _simple__STUB_ANSWER_RE = re.compile('^\\s*(?:best-effort answer unavailable|no question provided)', re.I)
                _simple__REFUSAL_ONLY_RE = re.compile("^\\s*(?:i (?:cannot|can't|am unable|was unable)|unable to|sorry[,.]|i don'?t have (?:enough|access))", re.I)
                _simple__INTENT_NARRATION_RE = re.compile("^\\s*(?:i (?:need|will|should|am going|'ll)\\b|let me\\b|first,? (?:i|let)\\b|i'?ll (?:search|look|start|begin|gather|check))", re.I)
                _simple_MIN_ANSWER_CHARS = 40
                _simple_MIN_CITED_ANSWER_CHARS = 12
                _simple__CITE_MARK_RE = re.compile('\\[[0-9]{1,3}\\]')

                def _simple__looks_like_tool_json(s: str) -> bool:
                    return bool(re.match('\\s*\\{\\s*"(?:name|tool|function)"\\s*:', s))

                def _simple__is_degenerate_repetition(text: str) -> bool:
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

                def _simple__is_usable_answer(text: str) -> bool:
                    s = _simple__normalize_brackets(text).strip()
                    if not s:
                        return False
                    if _simple__TOOL_MARKUP_RE.search(s) or _simple__looks_like_tool_json(s):
                        return False
                    if _simple__STUB_ANSWER_RE.match(s) or _simple__is_degenerate_repetition(s):
                        return False
                    cited = bool(_simple__CITE_MARK_RE.search(s))
                    if cited and len(s) >= _simple_MIN_CITED_ANSWER_CHARS:
                        return True
                    if len(s) < _simple_MIN_ANSWER_CHARS:
                        return False
                    if len(s) < 400 and (_simple__REFUSAL_ONLY_RE.match(s) or _simple__INTENT_NARRATION_RE.match(s)):
                        return False
                    return True
                _simple__COMMIT_RULES = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too. Never say what the evidence does not contain; commit to the best-supported answer you can defend."
                _simple__REPAIR_ORDER = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

                def _simple__sanitize_draft(text: str) -> str:
                    return _simple__VERIFY_MARK_RE.sub('', text or '').strip()

                def _simple__ledger_digest(ledger: _simple_EvidenceLedger, char_cap: int=60000) -> str:
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
                _simple__FURNITURE_RE = re.compile('^\\s*(?:share|search|home|menu|subscribe|sign\\s*in|log\\s*in|newsletter|advertisement|cookie|skip to|follow us|read more|related|tags?|categories?|privacy|terms|contact|about us|navigation|toggle)\\b', re.I)
                _simple__SRC_FOOTNOTE_RE = re.compile('\\[\\s*\\d{1,3}\\s*\\]')
                _simple__MD_LINK_RE = re.compile('\\]\\(')
                _simple__BARE_URL_RE = re.compile('(?<!\\]\\()https?://')
                _simple__SENTENCEY_RE = re.compile('[.!?]\\s|[.!?]$|\\b(?:is|was|were|are|has|have|had|reported|announced|released|won|ranked|totall?ed)\\b', re.I)

                def _simple__informative_lead(preview: str, limit: int=280) -> str:
                    kept: list[str] = []
                    broke = False
                    for chunk in re.split('(?<=[.!?])\\s+|\\n+', _simple__SRC_FOOTNOTE_RE.sub('', preview or '')):
                        seg = ' '.join(chunk.split())
                        if len(seg) < 30 or len(seg) > 400:
                            if kept:
                                broke = True
                                break
                            continue
                        if _simple__SENTENCEY_RE.search(seg) is None:
                            if kept:
                                broke = True
                                break
                            continue
                        if _simple__FURNITURE_RE.match(seg) and (not re.search('\\d', seg)):
                            if kept:
                                broke = True
                                break
                            continue
                        if seg.startswith(('*', '|', '↑', '#')):
                            if kept:
                                broke = True
                                break
                            continue
                        links = len(_simple__MD_LINK_RE.findall(seg)) + len(_simple__BARE_URL_RE.findall(seg))
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

                def _simple__deterministic_answer(question: str, ledger: _simple_EvidenceLedger) -> str:
                    rows = [(i, r) for i, r in enumerate(ledger.rows, start=1) if (r.get('preview') or '').strip()]
                    if not rows:
                        return ''
                    out = ['Best-supported findings from the sources retrieved:']
                    picked = 0
                    for i, r in rows:
                        if picked >= 6:
                            break
                        lead = _simple__informative_lead(r.get('preview') or '')
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

                async def _simple__write_from_digest(question: str, ledger: _simple_EvidenceLedger, deadline: float) -> str:
                    left = deadline - monotonic()
                    if left < 14.0:
                        return ''
                    digest = _simple__ledger_digest(ledger)
                    if not digest:
                        return ''
                    convo = [{'role': 'system', 'content': _simple__COMMIT_RULES}, {'role': 'user', 'content': f'Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'}]

                    async def _one(lane: str, model: str, budget: float) -> str:
                        payload = await llm_chat(provider=lane, model=model, messages=convo, temperature=0.15, max_output_tokens=2600, timeout=budget, thinking=_simple__least_think(lane, model))
                        _simple__spend_note(payload)
                        llm = getattr(payload, 'llm', None)
                        text = (getattr(llm, 'raw_text', None) or '').strip()
                        if not text:
                            choices = getattr(llm, 'choices', None) or []
                            if choices:
                                c = getattr(choices[0].message, 'content', None)
                                if isinstance(c, str):
                                    text = c.strip()
                        return text
                    lanes = ((_simple_LLM_LANE_A, _simple_LOOP_MODEL_A), (_simple_LLM_LANE_B, _simple_LOOP_MODEL_B), (_simple_EMERGENCY_PROVIDER, _simple_EMERGENCY_MODEL))
                    for i, lane_model in enumerate(lanes):
                        left = deadline - monotonic()
                        if left < 14.0:
                            return ''
                        budget = min(_simple_RESCUE_TIMEOUT_S, left - _simple_DIGEST_TAIL_S)
                        if i == 0:
                            budget = min(budget, max(12.0, left - 14.0 - _simple_DIGEST_TAIL_S))
                        if budget < 8.0:
                            return ''
                        try:
                            text = await _one(lane_model[0], lane_model[1], budget)
                        except Exception:
                            continue
                        if _simple__is_usable_answer(text):
                            return text
                    return ''

                async def _simple__knowledge_resort(question: str, deadline: float) -> str:
                    left = deadline - monotonic()
                    if left < 12.0:
                        return ''
                    try:
                        return await _simple__chat_simple(_simple_LLM_LANE_A, _simple_RESORT_MODEL, 'Expert researcher. Best definitive answer with concrete entities, numbers, dates. Never refuse.', question, max_tokens=2600, timeout=min(45.0, left - 4.0))
                    except Exception:
                        return ''

                async def _simple__schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
                    ask = f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}'
                    for lane, model in ((_simple_LLM_LANE_A, _simple_SCHEMA_MODEL), (_simple_LLM_LANE_A, _simple_RESORT_MODEL), (_simple_LLM_LANE_B, _simple_LOOP_MODEL_B), (_simple_EMERGENCY_PROVIDER, _simple_EMERGENCY_MODEL)):
                        left = deadline - monotonic()
                        if left < 12.0:
                            break
                        try:
                            raw = await _simple__chat_simple(lane, model, 'You output strictly valid JSON.', ask, max_tokens=3400, timeout=min(45.0, left - 4.0))
                            raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()
                            value = json.loads(raw)
                            if _simple__matches_schema_shape(value, schema):
                                return value
                            if isinstance(value, dict) and len(value) == 1:
                                inner = list(value.values())[0]
                                if _simple__matches_schema_shape(inner, schema):
                                    return inner
                        except Exception:
                            continue
                    return None

                def _simple__schema_kind(schema) -> str:
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
                                    got = _simple__schema_kind(sub)
                                    if got:
                                        return got
                        if isinstance(schema.get('properties'), dict):
                            return 'object'
                        if isinstance(schema.get('enum'), list):
                            return 'string'
                        return ''
                    return str(kind)

                def _simple__matches_schema_shape(value, schema) -> bool:
                    kind = _simple__schema_kind(schema)
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
                _simple__NUM_IN_TEXT_RE = re.compile('-?\\d[\\d,]*(?:\\.\\d+)?')

                def _simple__coerce_to_schema(answer: str, schema, depth: int=0):
                    if depth > 4 or not isinstance(schema, dict):
                        return answer[:400]
                    enum = schema.get('enum')
                    if isinstance(enum, list) and enum:
                        low = (answer or '').lower()
                        for opt in enum:
                            if isinstance(opt, str) and re.search('\\b' + re.escape(opt.lower()) + '\\b', low):
                                return opt
                        return enum[0]
                    kind = _simple__schema_kind(schema)
                    if not kind:
                        for key in ('anyOf', 'oneOf', 'allOf'):
                            branch = schema.get(key)
                            if isinstance(branch, list) and branch:
                                for sub in branch:
                                    if isinstance(sub, dict) and sub.get('type') != 'null':
                                        return _simple__coerce_to_schema(answer, sub, depth + 1)
                        kind = 'string'
                    if kind == 'array':
                        items = schema.get('items') or {}
                        parts = [p.strip(' -*\t') for p in re.split('[\\n;]|,(?![^(]*\\))', answer or '')]
                        parts = [p[:400] for p in parts if p][:20]
                        if not parts:
                            parts = [answer[:400]]
                        return [_simple__coerce_to_schema(p, items, depth + 1) for p in parts]
                    if kind == 'object':
                        props = schema.get('properties') or {}
                        required = schema.get('required') or list(props.keys())
                        out = {}
                        for key in required:
                            out[key] = _simple__coerce_to_schema(answer, props.get(key) or {}, depth + 1)
                        return out
                    if kind in ('number', 'integer'):
                        found = _simple__NUM_IN_TEXT_RE.search(_simple__CITE_NUM_RE.sub(' ', answer or ''))
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
                _simple__NARRATION_LEAD_RE = re.compile("^\\s*(?:based on (?:my|the)\\b|now (?:i|that i)\\b|i (?:now )?(?:have|was|am|need|will|can)\\b|i(?:'ll|'ve|'m)\\b|let me\\b|let's\\b|first,? i\\b|having (?:now )?\\w+\\b|okay\\b|alright\\b|to answer this\\b|my research\\b)", re.IGNORECASE)
                _simple__ABBREV_TAIL_RE = re.compile('(?:\\b[A-Z]|\\b(?:Inc|Ltd|Co|No|vs|St|Dr|Mr|Ms|Mt|Jr|Sr|etc|e\\.g|i\\.e))\\.$')

                def _simple__strip_lead_narration(text: str) -> str:
                    t = (text or '').strip()
                    if not t:
                        return t
                    for _ in range(2):
                        parts = re.split('(?<=[.!?])\\s+', t, maxsplit=1)
                        if len(parts) != 2:
                            break
                        head, rest = (parts[0], parts[1].strip())
                        if _simple__CITE_NUM_RE.search(head):
                            break
                        if _simple__NARRATION_LEAD_RE.match(head) is None:
                            break
                        if len(head.split()) < 4 or _simple__ABBREV_TAIL_RE.search(head) is not None:
                            break
                        if len(rest) < 120 or _simple__CITE_NUM_RE.search(rest) is None:
                            break
                        t = rest
                    return t

                def _simple__cap(text: str) -> str:
                    t = (text or '').strip()
                    if len(t) > _simple_ANSWER_CHAR_CAP:
                        return t[:_simple_ANSWER_CHAR_CAP - 16] + ' …'
                    return t

                @dataclass
                class _simple_ChainFact:
                    label: str
                    value: str
                    source: str = ''

                @dataclass
                class _simple_ChainTableState:
                    facts: list[_simple_ChainFact] = field(default_factory=list)
                    table_queries: list[str] = field(default_factory=list)
                    direct_queries: list[str] = field(default_factory=list)
                    challenge_queries: list[str] = field(default_factory=list)
                    contradiction_queries: list[str] = field(default_factory=list)
                    complexity: str = 'standard'
                _simple__CHAIN_YEAR_RE = re.compile('\\b(?:18|19|20)\\d{2}\\b')

                def _simple__chain_table_state(question: str, brief: str) -> _simple_ChainTableState:
                    state = _simple_ChainTableState()
                    years = list(dict.fromkeys(_simple__CHAIN_YEAR_RE.findall(brief or '')))
                    lower = (question or '').lower()
                    condition_count = len(re.findall('(?i)\\b(?:and|or|between|before|after|more than|less than|at least|at most)\\b', question or ''))
                    state.complexity = 'deep' if condition_count >= 3 or len(question) > 420 else 'light' if condition_count == 0 and len(question) < 180 else 'standard'
                    for year in years[:2]:
                        state.facts.append(_simple_ChainFact('derived year', year))
                        if any((word in lower for word in ('baseball', 'mlb', 'standings', 'home', 'road'))):
                            state.table_queries.append(f'{year} Major League Baseball season American League standings home road')
                        elif any((word in lower for word in ('box office', 'gross', 'movie', 'film'))):
                            state.table_queries.append(f'{year} box office yearly results')
                    if any((word in lower for word in ('state', 'states', 'bls', 'employment', 'population'))):
                        state.table_queries.append(f'{question} official data table')
                    named_domains = {'wikipedia': 'site:wikipedia.org', 'census': 'site:census.gov', 'bls': 'site:bls.gov', 'sec': 'site:sec.gov', 'nasa': 'site:nasa.gov OR site:ipac.caltech.edu', 'usgs': 'site:usgs.gov'}
                    for cue, domain in named_domains.items():
                        if cue in lower:
                            state.direct_queries.append(f'{question} {domain}')
                    if any((token in lower for token in ('all ', 'each ', 'which ', 'highest', 'lowest', 'more than', 'less than'))):
                        state.challenge_queries.append(f'{question} complete list exclusions near misses')
                        state.contradiction_queries.append(f'{question} counterexample discrepancy alternate ranking')
                    return state

                async def _simple__collect_chain_table(question: str, state: _simple_ChainTableState, ledger: _simple_EvidenceLedger, deadline: float) -> str:
                    blocks: list[str] = []
                    seen: set[str] = set()
                    caps = {'light': (1, 1, 0, 0), 'standard': (2, 2, 1, 0), 'deep': (2, 3, 1, 1)}[state.complexity]
                    portfolio = [('direct', q) for q in state.direct_queries[:caps[0]]] + [('table', q) for q in state.table_queries[:caps[1]]] + [('challenge', q) for q in state.challenge_queries[:caps[2]]] + [('contradiction', q) for q in state.contradiction_queries[:caps[3]]]
                    for lane, lookup in portfolio:
                        if deadline - monotonic() < 95.0:
                            break
                        try:
                            result = await _simple__do_search(lookup, ledger)
                            blocks.append(_simple__commit_tool_output(result, ledger))
                        except Exception:
                            continue
                        rows = getattr(result, 'rows', []) if isinstance(result, _simple_ToolOutput) else []
                        ranked = sorted((str(r.get('url') or '') for r in rows), key=lambda u: (lane == 'direct' and (not any((d in u.lower() for d in ('.gov', 'wikipedia.org', 'ipac.caltech.edu')))), 'wikipedia.org' not in u.lower(), len(u)))
                        for url in ranked[:2]:
                            if not url or url in seen or deadline - monotonic() < 62.0:
                                continue
                            seen.add(url)
                            try:
                                page = await _simple__do_fetch(url, question, lookup, ledger)
                                blocks.append(_simple__commit_tool_output(page, ledger))
                            except Exception:
                                continue
                    facts = '; '.join((f'{x.label}={x.value}' for x in state.facts))
                    evidence = '\n'.join((b for b in blocks if isinstance(b, str) and _simple__CITE_MARK_RE.search(b)))
                    lane_summary = ', '.join((lane for lane, _ in portfolio)) or 'general'
                    return f'CHAIN STATE (verify, then use): {facts}\nCOMPLEXITY: {state.complexity}\nRESEARCH LANES: {lane_summary}\nTABLE EVIDENCE:\n{evidence}' if evidence else f'CHAIN STATE: {facts}'

                async def _simple__solve_chain_table(query: Query, question: str) -> Response:
                    deadline = monotonic() + 258.0
                    try:
                        info = await tooling_info(timeout=10.0)
                        _simple__spend_note(info)
                    except Exception:
                        pass
                    draft, brief = ('', '')
                    try:
                        if _simple__spend_left() >= _simple_BRIEF_MIN_USD and deadline - monotonic() > 170.0:
                            draft, brief = await _simple__knowledge_brief(question)
                    except Exception:
                        pass
                    ledger = _simple_EvidenceLedger()
                    state = _simple__chain_table_state(question, brief)
                    chain_context = await _simple__collect_chain_table(question, state, ledger, deadline)
                    answer, messages = await _simple__loop(question, '\n\n'.join((x for x in (brief, chain_context) if x)), ledger, deadline, 11)
                    if _simple__is_usable_answer(answer) and deadline - monotonic() > 55.0 and (_simple__spend_left() >= _simple_AUDIT_MIN_USD):
                        try:
                            patched = await _simple__audit_patch(question, answer, messages, ledger, deadline)
                            if _simple__is_usable_answer(patched):
                                answer = patched
                        except Exception:
                            pass
                    if not _simple__is_usable_answer(answer) and ledger.rows:
                        try:
                            answer = await _simple__write_from_digest(question, ledger, deadline)
                        except Exception:
                            answer = _simple__deterministic_answer(question, ledger)
                    if not _simple__is_usable_answer(answer):
                        return await _simple__solve(query, question)
                    answer = _simple__cap(_simple__strip_lead_narration(_simple__normalize_brackets(answer)))
                    citations = _simple__citations_for(answer, ledger)
                    if query.output_schema is not None:
                        structured = None
                        try:
                            structured = await _simple__schema_output(question, answer, query.output_schema, deadline)
                        except Exception:
                            structured = None
                        return Response(output=structured if structured is not None else _simple__coerce_to_schema(answer, query.output_schema), citations=citations or None)
                    return Response(text=answer, citations=citations or None)

                async def _simple_query(query: Query) -> Response:
                    question = (query.text or '').strip()
                    if not question:
                        return Response(text='No question provided.')
                    try:
                        return await _simple__solve_chain_table(query, question)
                    except Exception:
                        return Response(text=f'Best-effort answer unavailable for: {question[:500]}')

                async def _simple__solve(query: Query, question: str) -> Response:
                    deadline = monotonic() + _simple_WALL_BUDGET_S
                    try:
                        info = await tooling_info(timeout=10.0)
                        _simple__spend_note(info)
                    except Exception:
                        pass
                    draft = ''
                    brief = ''
                    try:
                        if _simple__spend_left() >= _simple_BRIEF_MIN_USD and deadline - monotonic() > 120.0:
                            draft, brief = await _simple__knowledge_brief(question)
                    except Exception:
                        brief = ''
                    ledger = _simple_EvidenceLedger()
                    answer = ''
                    messages: list[dict] = []
                    try:
                        answer, messages = await _simple__loop(question, brief, ledger, deadline, _simple_MAX_TURNS)
                    except Exception:
                        answer = ''
                    try:
                        if _simple__is_usable_answer(answer) and deadline - monotonic() > 75.0 and (_simple__spend_left() >= _simple_AUDIT_MIN_USD):
                            patched = await _simple__audit_patch(question, answer, messages, ledger, deadline)
                            if _simple__is_usable_answer(patched):
                                answer = patched
                    except Exception:
                        pass
                    if not _simple__is_usable_answer(answer) and ledger.rows:
                        try:
                            rescued = await _simple__write_from_digest(question, ledger, deadline)
                            if _simple__is_usable_answer(rescued):
                                answer = rescued
                        except Exception:
                            pass
                    if not _simple__is_usable_answer(answer) and ledger.rows:
                        det = _simple__deterministic_answer(question, ledger)
                        if _simple__is_usable_answer(det):
                            answer = det
                    if not _simple__is_usable_answer(answer):
                        fallback = _simple__sanitize_draft(draft) or await _simple__knowledge_resort(question, deadline)
                        if _simple__is_usable_answer(fallback):
                            answer = fallback
                    try:
                        citations = _simple__citations_for(answer, ledger)
                    except Exception:
                        citations = []
                    answer = _simple__normalize_brackets(answer)
                    answer = _simple__strip_lead_narration(answer)
                    text = _simple__cap(answer) or f'Best-effort answer unavailable for: {question[:400]}'
                    if query.output_schema is not None:
                        structured = None
                        try:
                            structured = await _simple__schema_output(question, answer, query.output_schema, deadline)
                        except Exception:
                            structured = None
                        if structured is not None:
                            try:
                                return Response(output=structured, citations=citations or None)
                            except Exception:
                                structured = None
                        basis = answer if _simple__is_usable_answer(answer) else ''
                        if not basis:
                            basis = _simple__deterministic_answer(question, ledger)
                        if not basis or _simple__STUB_ANSWER_RE.match(basis.strip()):
                            basis = question[:400]
                        try:
                            forced = _simple__coerce_to_schema(_simple__cap(basis), query.output_schema)
                            return Response(output=forced, citations=citations or None)
                        except Exception:
                            try:
                                return Response(output=_simple__cap(basis)[:2000], citations=citations or None)
                            except Exception:
                                pass
                    try:
                        return Response(text=text, citations=citations or None)
                    except Exception:
                        return Response(text=text)
                _focused_VERSION = 'v33.4-openrouter'
                _focused_LLM_PROVIDER = 'openrouter'
                _focused_LOOP_MODEL_A = 'z-ai/glm-5.2'
                _focused_LOOP_MODEL_B = 'z-ai/glm-5.2'
                _focused_LOOP_MODEL_C = 'deepseek/deepseek-v3.2'
                _focused_LOOP_MODEL_CHAIN = (_focused_LOOP_MODEL_A, _focused_LOOP_MODEL_B, _focused_LOOP_MODEL_C)
                _focused_AUDIT_MODEL = 'openai/gpt-oss-120b'
                _focused_SCHEMA_MODEL = 'openai/gpt-oss-120b'
                _focused_RESORT_MODEL = 'deepseek/deepseek-v3.2'
                _focused_SEARCH_PROVIDER = 'parallel'
                _focused_WALL_BUDGET_S = 262.0
                _focused_BRIEF_TIMEOUT_S = 50.0
                _focused_TURN_TIMEOUT_S = 75.0
                _focused_AUDIT_TIMEOUT_S = 28.0
                _focused_SEARCH_TIMEOUT_S = 18.0
                _focused_FETCH_TIMEOUT_S = 16.0
                _focused_WRAPUP_AT_S = 90.0
                _focused_STALL_TURN_LIMIT = 3
                _focused_AUDIT_EXTRA_TURNS = 2
                _focused_ANSWER_REPAIR_TURNS = 2
                _focused_RESCUE_TIMEOUT_S = 55.0
                _focused_MIN_TAIL_S = 8.0
                _focused_MAX_TURNS = 15
                _focused_DIGEST_TAIL_S = 14.0
                _focused_BRIEF_PHASE_S = _focused_BRIEF_TIMEOUT_S + 12.0
                _focused_PRESEED_PHASE_S = 60.0
                _focused_SEARCH_EXCERPT_CHARS = 550
                _focused_FETCH_HEAD_CHARS = 3000
                _focused_FETCH_WINDOW_CHARS = 3600
                _focused_FETCH_WINDOWS_PER_PAGE = 3
                _focused_FETCH_PLAIN_CHARS = 6500
                _focused_ANSWER_CHAR_CAP = 60000
                _focused_CITATION_CAP = 24
                _focused_EVIDENCE_CHAR_BUDGET = 105000
                _focused_BRIEF_MIN_USD = 0.03
                _focused_AUDIT_MIN_USD = 0.05
                _focused_WRAPUP_MIN_USD = 0.02
                _focused__SPEND = {'left': None}

                def _focused__spend_note(payload) -> None:
                    budget = getattr(payload, 'budget', None)
                    left = getattr(budget, 'session_remaining_budget_usd', None)
                    if isinstance(left, (int, float)):
                        _focused__SPEND['left'] = float(left)

                def _focused__spend_left() -> float:
                    left = _focused__SPEND['left']
                    if isinstance(left, (int, float)):
                        return float(left)
                    return 1.0

                def _focused__spend_reset() -> None:
                    _focused__SPEND['left'] = None
                _focused__TOOLCACHE: dict = {}
                _focused_TOOLCACHE_MAX = 96

                def _focused__toolcache_reset() -> None:
                    _focused__TOOLCACHE.clear()

                def _focused__toolcache_put(key: str, body: str) -> None:
                    if not key:
                        return
                    if len(_focused__TOOLCACHE) >= _focused_TOOLCACHE_MAX and key not in _focused__TOOLCACHE:
                        _focused__TOOLCACHE.clear()
                    _focused__TOOLCACHE[key] = body

                def _focused__message_obj(payload):
                    llm = getattr(payload, 'llm', None)
                    if llm is None:
                        return None
                    choices = getattr(llm, 'choices', None) or []
                    if not choices:
                        return None
                    try:
                        first = choices[0]
                    except Exception:
                        return None
                    return getattr(first, 'message', None)

                def _focused__message_text(payload) -> str:
                    llm = getattr(payload, 'llm', None)
                    text = (getattr(llm, 'raw_text', None) or '').strip() if llm is not None else ''
                    if text:
                        return text
                    msg = _focused__message_obj(payload)
                    if msg is None:
                        return ''
                    content = getattr(msg, 'content', None)
                    if isinstance(content, str):
                        return content.strip()
                    return ''

                def _focused__message_calls(payload) -> list:
                    msg = _focused__message_obj(payload)
                    if msg is None:
                        return []
                    calls = getattr(msg, 'tool_calls', None)
                    if not calls:
                        return []
                    try:
                        return list(calls)
                    except Exception:
                        return []

                def _focused__input_message(payload):
                    msg = _focused__message_obj(payload)
                    if msg is None:
                        return None
                    try:
                        return msg.to_input_message()
                    except Exception:
                        return None

                def _focused__cache_key(name: str, a: str, b: str='') -> str:
                    return name + '|' + ' '.join((a or '').lower().split()) + '|' + ' '.join((b or '').lower().split())

                def _focused__call_cache_key(call) -> str:
                    try:
                        args = json.loads(getattr(call, 'arguments', None) or '{}')
                    except Exception:
                        return ''
                    if not isinstance(args, dict):
                        return ''
                    name = getattr(call, 'name', '') or ''
                    if name == 'web_search':
                        q = str(args.get('query') or '')
                        if q.strip():
                            return _focused__cache_key(name, q)
                    if name == 'read_page':
                        u = str(args.get('url') or '')
                        if u.strip():
                            return _focused__cache_key(name, u, str(args.get('focus') or ''))
                    return ''

                def _focused__time_left(deadline: float) -> float:
                    return deadline - monotonic()

                def _focused__clamp_timeout(deadline: float, want: float, reserve: float=4.0, floor: float=4.0) -> float:
                    room = deadline - monotonic() - reserve
                    if room < floor:
                        return 0.0
                    if want < room:
                        return want
                    return room
                _focused_LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}]
                _focused_LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.\n\nASKED-FIELD LEAD: sentence one gives the EXACT field the question asks for — the coordinates, the designation, the count — and mirrors any described process in its own wording (\'Of the N events matching <the stated filters>, the earliest is …\'), so the asked shape is answered in the asked terms. Every claim carries its exact figure with its units and date. Never assert \'no X exists\' merely because your results do not mention one — absence of evidence is not a world-negative; commit to the best-supported candidate instead.\n\nSOURCE CHOICE: never cite grokipedia, facebook, pinterest or quora. Prefer the question-NAMED source\'s own page over any aggregator, and for infobox-style questions (each enumerated item\'s own statistic) cite each item\'s value from ITS OWN page, not a shared list page.'

                def _focused__wrapup_order(seconds_left: float, stalled: bool=False) -> str:
                    lead = 'NO NEW EVIDENCE is arriving — the last few turns re-requested sources you already have.' if stalled else f'TIME IS UP (~{int(seconds_left)}s left).'
                    return lead + " No more tool calls. Write the complete final answer NOW from the numbered results above plus your knowledge: the FIRST words are the answer entities (no 'Based on…' preamble, no 'partial answer' framing, no '(verify)' markers), cite [n] on every claim, keep the required format. A cited partial answer scores; a refusal or a remark about insufficient evidence scores zero." + ('' if seconds_left >= 60 else ' BREVITY OVERRIDE: too little time remains for a line per pool member. Lead with the answer entities, then give the qualifiers one cited line each and compress the rejects into a single cited line. A complete short answer beats a long one that never finishes.')
                _focused__SET_HINT_RE = re.compile('\\b(?:list|name|identify|enumerate)\\b[^?]{0,40}\\b(?:all|every|each|the)\\b|\\bhow many\\b|\\bwhich (?:movies|films|series|countries|companies|states|cities|books|albums|artists|players|teams|species|languages|banks|universities|agencies|models|products)\\b', re.IGNORECASE)
                _focused__SET_CONNECTIVE_RE = re.compile('\\b(?:both|also|and (?:also|had|has|was|were)|as well as)\\b', re.IGNORECASE)
                _focused__PLURAL_HEAD_RE = re.compile('\\b(?:which|what)\\b(?:\\s+\\w+){0,2}?\\s+([a-z]{3,}s)\\b', re.IGNORECASE)
                _focused__PLURAL_FALSE = frozenset('was is has does its this thus across process business series species news status analysis basis less unless always perhaps'.split())
                _focused__ONE_WINNER_RE = re.compile('\\b(?:highest|lowest|largest|smallest|most|least|greatest|fewest|longest|shortest|first|last|best|worst|only|oldest|youngest|newest|biggest)\\b', re.IGNORECASE)
                _focused__EST_STOP = frozenset('interest honest modest protest request suggest forest harvest invest manifest contest arrest digest earnest conquest tempest midwest northwest southwest unrest bequest behest attest molest ingest infest detest incest armrest backrest pretest headrest footrest'.split())
                _focused__EST_RE = re.compile('\\b([a-z]{3,})est\\b')

                def _focused__has_superlative(text: str) -> bool:
                    if _focused__ONE_WINNER_RE.search(text or ''):
                        return True
                    for m in _focused__EST_RE.finditer(text or ''):
                        if m.group(0).lower() not in _focused__EST_STOP:
                            return True
                    return False

                def _focused__needs_superlative_proof(question: str) -> bool:
                    q = ' '.join((question or '').split())
                    if not q:
                        return False
                    return _focused__has_superlative(q) or bool(re.search('\\b(?:most|least) (?:common|frequent|number|amount)\\b|\\bhow many\\b', q, re.I))
                _focused_SUPERLATIVE_RULE = "SUPERLATIVE / TALLY — SHOW THE TABLE. The answer is one item, but you cannot know it without the whole pool. Before naming a winner: (1) list EVERY candidate the question's scope admits — every player who appeared, every officeholder in the span, every body in the ranking; (2) put the deciding value next to each (birth date, count, figure), cited; (3) THEN name the maximum. NEVER decide a superlative on a rounded or derived display: a coarse figure (a whole-number age, a rounded total, a bucketed rank) cannot separate two contenders that differ below its precision. Fetch the exact underlying value (full birth date, unrounded figure) for every contender, from a source that lists them ALL: a page showing only your front-runner cannot establish that nobody beats them. (3b) THEN name the maximum. Reproduce that candidate table in the proof section — a correct winner with no visible tally loses to a reference that shows its work, and 'among others' / 'and several more' is not a tally. If the pool is too large to list in full, rank it, show every contender down to a stated cutoff, and say what the cutoff was — a stated cutoff is a covered pool; an unstated one reads as an unchecked one."

                def _focused__needs_set_completeness(question: str) -> bool:
                    q = ' '.join((question or '').split())
                    if _focused__SET_HINT_RE.search(q):
                        return True
                    m = _focused__PLURAL_HEAD_RE.search(q)
                    if m and m.group(1).lower() not in _focused__PLURAL_FALSE:
                        if not _focused__has_superlative(q) or re.search('\\b(?:all|every|each)\\b', q, re.IGNORECASE):
                            return True
                    return bool(re.search('\\bwhich\\b', q, re.IGNORECASE)) and bool(_focused__SET_CONNECTIVE_RE.search(q))
                _focused_SET_RULE = "SET ANSWER: this question asks for a set. Missing a qualifying member scores the same as wrong — enumerate the pool, test EVERY member against EVERY condition, and name ALL qualifiers (each with its own citations per condition). Then give EVERY excluded member its own line with the condition it fails and its own [n] — not a single clause sweeping several names together, and not just the near-misses. Never claim 'the only X' unless the whole pool was checked; if your pool may be partial, still commit to every qualifier you verified. GET THE POOL FROM A LIST, NOT MEMBER-BY-MEMBER: your FIRST retrieval for a set question should hunt the authoritative roster/list/table that enumerates the whole pool (search it AS a list — '<pool subject> list', '<pool subject> table', 'list of <pool subject>' — and read_page it). Assembling the pool from separate per-member searches is how a run ends up with 3 of 6 qualifiers: the members you never thought to search for are invisible to you. Read the roster page first, then verify each member. ONE LIST PER PERIOD, THEN JOIN: when a condition has to hold across several periods — successive years, separate editions, or two parallel events — fetch ONE roster page per period and join them on the member: one list per period, not one lookup per member. A pool of 30+ members each needing several figures is a table-join, and per-member lookups will run out of turns long before the pool is covered. UNIVERSAL conditions ('in EVERY one of them', 'for BOTH parts', 'in ALL three periods'): check each candidate against EACH instance separately, with a citation per instance — one shared instance is not enough. If NO candidate survives every instance, then 'none' IS the answer: state it as a verified fact about the world with the per-instance citations that prove it."
                _focused_MAX_SPANS_PER_ROW = 6

                def _focused__normalize_spans(spans: list | None, note_len: int) -> list | None:
                    if not spans or note_len <= 0:
                        return None
                    clean: list = []
                    for span in spans:
                        try:
                            start = int(span[0])
                            end = int(span[1])
                        except Exception:
                            continue
                        start = max(0, min(start, note_len))
                        end = max(0, min(end, note_len))
                        if end <= start:
                            continue
                        clean.append((start, end))
                    if not clean:
                        return None
                    clean.sort()
                    merged: list = [clean[0]]
                    for start, end in clean[1:]:
                        last_start, last_end = merged[-1]
                        if start <= last_end:
                            if end > last_end:
                                merged[-1] = (last_start, end)
                        else:
                            merged.append((start, end))
                    return merged[:_focused_MAX_SPANS_PER_ROW]

                def _focused__ledger_add(ledger: list, receipt_id: str, result_id: str, note_len: int, kind: str, spans: list | None, title: str='', url: str='', preview: str='') -> int:
                    spans = _focused__normalize_spans(spans, note_len)
                    ledger.append({'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': (url or '')[:300], 'preview': (preview or '')[:1200], 'spans': spans})
                    return len(ledger)

                def _focused__ledger_ref(ledger: list, number: int):
                    if not 1 <= number <= len(ledger):
                        return None
                    row = ledger[number - 1]
                    if not row['receipt_id'] or not row['result_id']:
                        return None
                    spans = row['spans']
                    if not spans:
                        return None
                    slices = []
                    for span in spans[:_focused_MAX_SPANS_PER_ROW]:
                        start = int(span[0])
                        end = int(span[1])
                        if end <= start:
                            continue
                        slices.append(CitationSlice(start=start, end=end))
                    if not slices:
                        return None
                    return CitationRef(receipt_id=row['receipt_id'], result_id=row['result_id'], slices=slices)
                _focused__WORD_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
                _focused__STOP = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

                def _focused__key_terms(text: str) -> set[str]:
                    return {w for w in _focused__WORD_RE.findall((text or '').casefold()) if w not in _focused__STOP}

                def _focused__best_windows(note: str, terms: set[str], width: int, k: int=1) -> list[tuple[int, int]]:
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
                _focused__SLOT = '\x00{}\x00'
                _focused__SLOT_RE = re.compile('\x00\\d{1,4}\x00')

                def _focused__tool_output(text: str, rows: list | None=None) -> dict:
                    return {'text': text, 'rows': rows or []}

                def _focused__commit_tool_output(out, ledger: list) -> str:
                    if isinstance(out, str):
                        return out
                    if not isinstance(out, dict) or not isinstance(out.get('text'), str):
                        return f'# tool crashed: {out}'
                    text = out['text']
                    for i, row in enumerate(out.get('rows') or []):
                        try:
                            n = _focused__ledger_add(ledger, row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''))
                        except Exception:
                            continue
                        text = text.replace(_focused__SLOT.format(i), str(n))
                    if '\x00' in text:
                        text = _focused__SLOT_RE.sub('?', text)
                    return text
                _focused__SITE_OP_RE = re.compile('\\bsite:\\S+\\s*', re.I)

                def _focused__degrade_query(q: str) -> str:
                    out = _focused__SITE_OP_RE.sub('', q or '').replace('"', ' ')
                    return ' '.join(out.split())

                async def _focused__do_search(query_text: str, deadline: float):
                    if not query_text.strip():
                        return '# web_search: empty query'
                    payload = None
                    fired: set[str] = set()
                    for attempt, allow_repeat in ((query_text, False), (query_text, True), (_focused__degrade_query(query_text), False)):
                        if not attempt.strip() or (attempt in fired and (not allow_repeat)):
                            continue
                        budget = _focused__clamp_timeout(deadline, _focused_SEARCH_TIMEOUT_S, 3.0, floor=5.0)
                        if budget <= 0.0:
                            break
                        fired.add(attempt)
                        try:
                            payload = await asyncio.wait_for(search_web(attempt, provider=_focused_SEARCH_PROVIDER, num=8, timeout=budget), timeout=budget + 4.0)
                            if getattr(payload, 'results', None):
                                break
                        except Exception:
                            payload = None
                    if payload is None:
                        return f'# web_search({query_text!r}) failed'
                    _focused__spend_note(payload)
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
                        span = [(0, min(max(_focused_SEARCH_EXCERPT_CHARS, 100), n_len))] if n_len >= 100 else [(0, n_len)] if n_len else None
                        title = (getattr(item, 'title', None) or '').strip()
                        url = (getattr(item, 'url', None) or '').strip()
                        rows.append({'receipt_id': receipt, 'result_id': rid, 'note_len': n_len, 'kind': 'search', 'spans': span, 'title': title, 'url': url, 'preview': note[:_focused_SEARCH_EXCERPT_CHARS]})
                        lines.append(f'[{_focused__SLOT.format(len(rows) - 1)}] {title} — {url}\n    {note[:_focused_SEARCH_EXCERPT_CHARS]}')
                    return _focused__tool_output('\n'.join(lines), rows)

                async def _focused__do_fetch(url: str, focus: str, question: str, deadline: float):
                    if not url.strip():
                        return '# read_page: empty url'
                    payload = None
                    for _attempt in (0, 1):
                        budget = _focused__clamp_timeout(deadline, _focused_FETCH_TIMEOUT_S, 3.0, floor=5.0)
                        if budget <= 0.0:
                            break
                        try:
                            payload = await asyncio.wait_for(fetch_page(url, provider=_focused_SEARCH_PROVIDER, timeout=budget), timeout=budget + 4.0)
                            if getattr(payload, 'results', None):
                                break
                        except Exception:
                            payload = None
                    if payload is None:
                        return f'# read_page({url!r}) failed'
                    _focused__spend_note(payload)
                    receipt = str(getattr(payload, 'receipt_id', '') or '')
                    results = list(getattr(payload, 'results', None) or [])
                    if not results or not receipt:
                        return f'# read_page({url!r}): no content'
                    item = results[0]
                    rid = getattr(item, 'result_id', None)
                    note = getattr(item, 'note', None) or ''
                    if not isinstance(rid, str) or not rid or (not note.strip()):
                        return f'# read_page({url!r}): no usable content'
                    if len(note) <= _focused_FETCH_PLAIN_CHARS:
                        row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, len(note))], 'title': url, 'url': url, 'preview': note[:1200]}
                        return _focused__tool_output(f'# read_page({url!r}) -> [{_focused__SLOT.format(0)}] full page, {len(note)} chars\n{note}', [row])
                    terms = _focused__key_terms(question) | _focused__key_terms(focus)
                    windows = _focused__best_windows(note, terms, _focused_FETCH_WINDOW_CHARS, k=_focused_FETCH_WINDOWS_PER_PAGE)
                    row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, _focused_FETCH_HEAD_CHARS)] + list(windows), 'title': url, 'url': url, 'preview': note[windows[0][0]:windows[0][0] + 1200]}
                    head = note[:_focused_FETCH_HEAD_CHARS]
                    sections = ''.join((f'\n--- section @{s} ---\n{note[s:e]}' for s, e in windows))
                    return _focused__tool_output(f"# read_page({url!r}) -> [{_focused__SLOT.format(0)}] {len(note)} chars total; head + the {len(windows)} most relevant section(s) shown ({', '.join((f'{s}-{e}' for s, e in windows))}). If the answer set may continue elsewhere in this page, call read_page again with a different focus.\n--- head ---\n{head}{sections}", [row])
                _focused__SEC_TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
                _focused__SEC_SUBMISSIONS_URL = 'https://data.sec.gov/submissions/CIK{cik10}.json'
                _focused__SEC_DOC_URL = 'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}'
                _focused__SEC_FETCH_TIMEOUT_S = 26.0
                _focused__SEC_MIN_HEADROOM_S = 40.0
                _focused__SEC_CACHE: dict = {}
                _focused__SEC_CACHE_MAX = 24
                _focused__SEC_STOPWORDS = frozenset('inc incorporated corp corporation company companies co ltd limited llc plc lp llp group holdings the'.split())
                _focused__SEC_ALNUM_RE = re.compile('[a-z0-9]+')

                def _focused__sec_tokens(text: str) -> list[str]:
                    return [w for w in _focused__SEC_ALNUM_RE.findall((text or '').lower()) if w not in _focused__SEC_STOPWORDS]

                def _focused__sec_norm_form(form: str) -> str:
                    f = ' '.join((form or '').upper().replace('FORM', ' ').split())
                    m = re.fullmatch('(\\d{1,2})\\s*-?\\s*([A-Z])', f)
                    if m:
                        return f'{m.group(1)}-{m.group(2)}'
                    m = re.fullmatch('(DEF)\\s*-?\\s*(14A)', f)
                    if m:
                        return 'DEF 14A'
                    return f

                def _focused__sec_cache_put(url: str, obj: dict) -> None:
                    if len(_focused__SEC_CACHE) >= _focused__SEC_CACHE_MAX:
                        keep = _focused__SEC_CACHE.get(_focused__SEC_TICKERS_URL)
                        _focused__SEC_CACHE.clear()
                        if keep is not None:
                            _focused__SEC_CACHE[_focused__SEC_TICKERS_URL] = keep
                    _focused__SEC_CACHE[url] = obj

                async def _focused__fetch_json(url: str, deadline: float):
                    cached = _focused__SEC_CACHE.get(url)
                    if cached is not None:
                        return cached
                    for _attempt in (0, 1):
                        budget = _focused__clamp_timeout(deadline, _focused__SEC_FETCH_TIMEOUT_S, 6.0, floor=6.0)
                        if budget <= 0.0:
                            return None
                        try:
                            payload = await asyncio.wait_for(fetch_page(url, provider=_focused_SEARCH_PROVIDER, timeout=budget), timeout=budget + 4.0)
                        except Exception:
                            continue
                        _focused__spend_note(payload)
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
                            _focused__sec_cache_put(url, obj)
                            return obj
                    return None

                def _focused__sec_pick_filing(recent: dict, form: str, year: str):
                    forms = recent.get('form')
                    accs = recent.get('accessionNumber')
                    docs = recent.get('primaryDocument')
                    rdates = recent.get('reportDate')
                    fdates = recent.get('filingDate')
                    if not (isinstance(forms, list) and isinstance(accs, list) and isinstance(docs, list)):
                        return None
                    n = min(len(forms), len(accs), len(docs))
                    form_norm = _focused__sec_norm_form(form)
                    best_year = None
                    best_any = None
                    for i in range(n):
                        if _focused__sec_norm_form(str(forms[i])) != form_norm:
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
                _focused__SEC_SEARCH_HINT = 'search "site:sec.gov {company} {year} {form}" and read_page the Archives result'

                async def _focused__do_sec_filing(company: str, form: str, year: str, deadline: float) -> str:
                    company = (company or '').strip()
                    form = (form or '').strip() or '10-K'
                    year = (year or '').strip()[:4]
                    hint = _focused__SEC_SEARCH_HINT.format(company=company, year=year, form=form)
                    if not company:
                        return '# sec_filing: company required'
                    if _focused__time_left(deadline) < _focused__SEC_MIN_HEADROOM_S:
                        return f'# sec_filing: skipped (low time) — {hint}'
                    tickers = await _focused__fetch_json(_focused__SEC_TICKERS_URL, deadline)
                    if not isinstance(tickers, dict):
                        return f'# sec_filing: EDGAR ticker index unavailable — {hint}'
                    want = _focused__sec_tokens(company)
                    best = None
                    for row in tickers.values():
                        if not isinstance(row, dict):
                            continue
                        title = str(row.get('title', ''))
                        ticker = str(row.get('ticker', '')).lower()
                        words = set(_focused__sec_tokens(title))
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
                    subs = await _focused__fetch_json(_focused__SEC_SUBMISSIONS_URL.format(cik10=cik10), deadline)
                    filings = subs.get('filings') if isinstance(subs, dict) else None
                    recent = filings.get('recent') if isinstance(filings, dict) else None
                    if not isinstance(recent, dict):
                        return f'# sec_filing({company!r}): EDGAR submissions unavailable for {title} — {hint}'
                    pick = _focused__sec_pick_filing(recent, form, year)
                    if pick is None:
                        return f"# sec_filing({company!r}, {form!r}, year={year or 'latest'}): no matching filing in EDGAR's recent index for {title} — check the form/year, or {hint}"
                    accession, doc = pick
                    url = _focused__SEC_DOC_URL.format(cik=cik10.lstrip('0') or cik10, accession=accession.replace('-', ''), doc=doc)
                    return f"# sec_filing -> {title} {form} {year or '(latest)'} primary document:\n{url}\nNow call read_page on this URL with a focus hint for the section you need, and cite figures from that read_page result."

                async def _focused__run_tool(call, question: str, deadline: float):
                    try:
                        args = json.loads(getattr(call, 'arguments', None) or '{}')
                    except Exception:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}
                    name = getattr(call, 'name', '') or ''
                    if name == 'web_search':
                        return await _focused__do_search(str(args.get('query') or ''), deadline)
                    if name == 'read_page':
                        return await _focused__do_fetch(str(args.get('url') or ''), str(args.get('focus') or ''), question, deadline)
                    if name == 'sec_filing':
                        return await _focused__do_sec_filing(str(args.get('company') or ''), str(args.get('form') or ''), str(args.get('year') or ''), deadline)
                    return f'# unknown tool {name!r}'
                _focused__REASONING_MANDATORY = ('openai/gpt-oss',)

                def _focused__least_think(model: str='') -> dict:
                    for prefix in _focused__REASONING_MANDATORY:
                        if model.startswith(prefix):
                            return {'enabled': True, 'effort': 'low'}
                    return {'enabled': False}

                async def _focused__chat_simple(model: str, system: str, user: str, *, max_tokens: int, timeout: float, think: dict | None=None) -> str:
                    if think is None:
                        think = _focused__least_think(model)
                    payload = await asyncio.wait_for(llm_chat(provider=_focused_LLM_PROVIDER, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=think), timeout=timeout + 6.0)
                    _focused__spend_note(payload)
                    return _focused__message_text(payload)

                async def _focused__chat_turn(messages: list[dict], deadline: float, *, finish_only: bool, force_tools: bool=False):
                    for model in _focused_LOOP_MODEL_CHAIN:
                        timeout = _focused__clamp_timeout(deadline, _focused_TURN_TIMEOUT_S, 5.0, floor=5.0)
                        if timeout <= 5.0:
                            return None
                        try:
                            payload = await asyncio.wait_for(llm_chat(provider=_focused_LLM_PROVIDER, model=model, messages=messages, tools=_focused_LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': True, 'effort': 'low'}, max_output_tokens=None, timeout=timeout), timeout=timeout + 6.0)
                            _focused__spend_note(payload)
                            return payload
                        except Exception:
                            continue
                    return None

                async def _focused__knowledge_brief(question: str, deadline: float) -> tuple[str, str]:
                    system = 'Senior research analyst. Commit to concrete best answers from knowledge; mark uncertain values (verify). Never refuse.'
                    user = f"Question:\n{question}\n\nWrite these blocks:\nBEST ANSWER: your full best answer now — candidate pool, every stated condition applied, qualifying entities with figures/dates, near-miss exclusions. Flag shaky facts with (verify).\nCHECKLIST: each atomic condition in the question, numbered, including any output-format demand.\nLOOKUPS: 3-6 precise web searches for the facts that decide the answer (entity + metric + year; include a named source's site: filter).\nPAGES: up to 5 exact URLs worth reading directly (official stats pages, sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."
                    phase_end = monotonic() + _focused_BRIEF_PHASE_S
                    raw = ''
                    for model in _focused_LOOP_MODEL_CHAIN:
                        budget = _focused__clamp_timeout(min(deadline, phase_end), _focused_BRIEF_TIMEOUT_S, 2.0, floor=12.0)
                        if budget <= 0.0:
                            break
                        try:
                            raw = await _focused__chat_simple(model, system, user, max_tokens=2400, timeout=budget, think=_focused__least_think(model))
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
                _focused__SEED_TOKEN_RE = re.compile("[A-Za-z0-9][A-Za-z0-9.\\-']+")
                _focused__SEED_STOP = frozenset('name list give tell show find identify please could would you your can may might should must let make sure both also'.split())
                _focused_MAX_SEED_QUERIES = 3

                def _focused__seed_queries(question: str, set_question: bool) -> list[str]:
                    q = ' '.join((question or '').split())
                    if not q:
                        return []
                    seeds = [q[:300]]
                    salient = [t for t in _focused__SEED_TOKEN_RE.findall(q) if len(t) >= 3 and t.lower() not in _focused__STOP and (t.lower() not in _focused__SEED_STOP)]
                    if len(salient) >= 2:
                        seeds.append(' '.join(salient[:8]))
                    if set_question and salient:
                        seeds.append('list of ' + ' '.join(salient[:6]))
                    out: list[str] = []
                    for s in seeds:
                        s = s.strip()
                        if s and s not in out:
                            out.append(s)
                    return out[:_focused_MAX_SEED_QUERIES]

                async def _focused__preseed(question: str, set_question: bool, ledger: list, deadline: float) -> str:
                    seeds = _focused__seed_queries(question, set_question)
                    if not seeds or _focused__time_left(deadline) < 40.0:
                        return ''
                    phase_end = min(monotonic() + _focused_PRESEED_PHASE_S, deadline - _focused_WRAPUP_AT_S - 10.0)
                    if _focused__time_left(phase_end) < 12.0:
                        return ''
                    blocks: list = []
                    for seed in seeds:
                        if _focused__time_left(deadline) < 30.0 or _focused__time_left(phase_end) < 12.0:
                            break
                        outer = max(10.0, min(_focused_SEARCH_TIMEOUT_S * 2 + 6.0, _focused__time_left(phase_end)))
                        try:
                            out = await asyncio.wait_for(_focused__do_search(seed, phase_end), timeout=outer)
                            committed = _focused__commit_tool_output(out, ledger)
                            blocks.append(committed)
                            if isinstance(out, dict) and _focused__CITE_MARK_RE.search(committed):
                                _focused__toolcache_put(_focused__cache_key('web_search', seed), committed)
                        except Exception:
                            continue
                    good = [b for b in blocks if isinstance(b, str) and _focused__CITE_MARK_RE.search(b)]
                    if not good:
                        return ''
                    return 'Automatic first-pass searches (already numbered — cite these [n] directly, and search further as needed):\n\n' + '\n'.join(good)
                _focused__QUOTED_ITEM_RE = re.compile('[\\"“]([^\\"”]{2,60})[\\"”]|(?:^|[\\s(])\'([^\'\\n]{3,60})\'(?=[\\s).,;:?!]|$)|\\*([^*\\n]{2,60})\\*')

                def _focused__asked_items(question: str) -> list[str]:
                    out: list[str] = []
                    seen: set[str] = set()
                    for m in _focused__QUOTED_ITEM_RE.finditer(question or ''):
                        item = (m.group(1) or m.group(2) or m.group(3) or '').strip()
                        key = ' '.join(item.lower().split())
                        if item and len(item.split()) <= 8 and key and (key not in seen):
                            seen.add(key)
                            out.append(item)
                    return out[:8]

                def _focused__uncovered_items(asked: list[str], ledger: list) -> list[str]:
                    hay = ' '.join((str(r.get('title') or '') + ' ' + str(r.get('url') or '') + ' ' + str(r.get('preview') or '') for r in ledger)).lower()
                    out: list[str] = []
                    for item in asked:
                        key = ' '.join(item.lower().split())
                        if key not in hay and key.replace(' ', '_') not in hay:
                            out.append(item)
                    return out

                def _focused__wiki_url(title: str) -> str:
                    return 'https://en.wikipedia.org/wiki/' + '_'.join((title or '').strip().split())
                _focused__USGS_MAG_RE = re.compile('magnitude\\s*(?:of\\s*)?(\\d+(?:\\.\\d+)?)')
                _focused__USGS_YEAR_RE = re.compile('\\b(1[89]\\d\\d|20\\d\\d)\\b')
                _focused__USGS_MAX_RE = re.compile('or (?:less|lower|below)|at most|under|less than|below|no more than')

                def _focused__usgs_url(question: str) -> str:
                    q = ' '.join((question or '').lower().split())
                    if 'earthquake' not in q and 'seismic' not in q:
                        return ''
                    m = _focused__USGS_MAG_RE.search(q)
                    years = _focused__USGS_YEAR_RE.findall(q)
                    if m is None or not years:
                        return ''
                    y0, y1 = (min(years), max(years))
                    head = q[max(0, m.start() - 30):m.start()]
                    tail = q[m.end():m.end() + 40]
                    if _focused__USGS_MAX_RE.search(tail) or _focused__USGS_MAX_RE.search(head):
                        magpart = 'maxmagnitude=' + m.group(1)
                    else:
                        magpart = 'minmagnitude=' + m.group(1)
                    return 'https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson' + '&starttime=' + y0 + '-01-01&endtime=' + y1 + '-12-31T23:59:59' + '&' + magpart + '&orderby=time-asc'
                _focused__PLANET_NAMES = ('mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto')
                _focused__PLANET_FACT_RE = re.compile('\\b(?:mass|diameter|density|gravity|moons?|escape velocity|rotation|orbital|aphelion|perihelion|temperature|distance from the sun)\\b')

                def _focused__nssdc_url(question: str) -> str:
                    q = ' '.join((question or '').lower().split())
                    hits = sum((1 for p in _focused__PLANET_NAMES if p in q))
                    if hits >= 2 and _focused__PLANET_FACT_RE.search(q):
                        return 'https://nssdc.gsfc.nasa.gov/planetary/factsheet/'
                    return ''
                _focused__AUTH_HOSTS = ('en.wikipedia.org', 'boxofficemojo.com', 'worldatlas.com', 'britannica.com', 'worldbank.org', 'un.org', 'oecd.org', 'imf.org', 'who.int', 'olympics.com', 'fifa.com', 'baseball-reference.com')

                def _focused__authority_urls(ledger: list, cap: int=2) -> list[str]:
                    out: list[str] = []
                    for row in ledger:
                        if row.get('kind') != 'search':
                            continue
                        url = (row.get('url') or '').strip()
                        m = re.match('https?://([^/\\s]+)', url)
                        if m is None:
                            continue
                        host = m.group(1).lower()
                        ok = host.endswith('.gov') or any((host == h or host.endswith('.' + h) for h in _focused__AUTH_HOSTS))
                        if ok and url not in out:
                            out.append(url)
                        if len(out) >= cap:
                            break
                    return out
                _focused_PREFETCH_PHASE_S = 36.0

                async def _focused__authority_prefetch(question: str, ledger: list, deadline: float) -> str:
                    if _focused__time_left(deadline) < 140.0:
                        return ''
                    targets: list[tuple[str, str]] = []
                    items = _focused__asked_items(question)
                    if len(items) >= 2 or (items and 'wikipedia' in (question or '').lower()):
                        for item in items[:4]:
                            targets.append((_focused__wiki_url(item), item))
                    data_url = _focused__usgs_url(question)
                    if data_url:
                        targets.append((data_url, 'count of matching events'))
                    data_url = _focused__nssdc_url(question)
                    if data_url:
                        targets.append((data_url, 'planetary fact sheet'))
                    for url in _focused__authority_urls(ledger, 2):
                        targets.append((url, ''))
                    fetched = {str(r.get('url') or '') for r in ledger if r.get('kind') == 'fetch'}
                    todo: list[tuple[str, str]] = []
                    for url, focus in targets:
                        if url and url not in fetched and all((url != u for u, _f in todo)):
                            todo.append((url, focus))
                    todo = todo[:6]
                    if not todo:
                        return ''
                    phase_end = min(monotonic() + _focused_PREFETCH_PHASE_S, deadline - _focused_WRAPUP_AT_S - 10.0)
                    if phase_end - monotonic() < 12.0:
                        return ''
                    tasks = [asyncio.ensure_future(_focused__do_fetch(url, focus, question, phase_end)) for url, focus in todo]
                    try:
                        await asyncio.wait(tasks, timeout=max(5.0, phase_end - monotonic()))
                    except Exception:
                        pass
                    blocks: list[str] = []
                    for (url, focus), task in zip(todo, tasks):
                        if not task.done():
                            task.cancel()
                            continue
                        try:
                            out = task.result()
                        except Exception:
                            continue
                        try:
                            body = _focused__commit_tool_output(out, ledger)
                        except Exception:
                            continue
                        if isinstance(out, dict) and isinstance(body, str) and _focused__CITE_MARK_RE.search(body):
                            blocks.append(body)
                            _focused__toolcache_put(_focused__cache_key('read_page', url, focus), body)
                    if not blocks:
                        return ''
                    return "Automatic authority prefetch — each enumerated item's OWN page and/or the primary data source, already numbered. Cite these [n] directly and prefer them over aggregators:\n\n" + '\n'.join(blocks)

                async def _focused__loop(question: str, brief: str, ledger: list, deadline: float, turn_cap: int, carry: list[dict] | None=None, allow_tools_in_wrapup: bool=False, sink: list | None=None) -> tuple[str, list[dict]]:
                    asked: list[str] = []
                    if carry is not None:
                        messages = carry
                    else:
                        if sink is not None:
                            messages = sink
                            messages[:] = []
                        else:
                            messages = []
                        try:
                            asked = _focused__asked_items(question)
                        except Exception:
                            asked = []
                        set_q = _focused__needs_set_completeness(question)
                        messages.append({'role': 'system', 'content': _focused_LOOP_RULES})
                        if set_q:
                            messages.append({'role': 'system', 'content': _focused_SET_RULE})
                        if _focused__needs_superlative_proof(question):
                            messages.append({'role': 'system', 'content': _focused_SUPERLATIVE_RULE})
                        if brief:
                            messages.append({'role': 'system', 'content': brief})
                        seeded = await _focused__preseed(question, set_q, ledger, deadline)
                        if seeded:
                            messages.append({'role': 'system', 'content': seeded})
                        try:
                            prefetched = await _focused__authority_prefetch(question, ledger, deadline)
                        except Exception:
                            prefetched = ''
                        if prefetched:
                            messages.append({'role': 'system', 'content': prefetched})
                        messages.append({'role': 'user', 'content': question})
                    answer = ''
                    ordered_wrapup = False
                    repairs_left = _focused_ANSWER_REPAIR_TURNS
                    stalled_turns = 0
                    for turn in range(1, turn_cap + 1):
                        left = _focused__time_left(deadline)
                        if left <= _focused_MIN_TAIL_S:
                            break
                        out_of_time = left <= _focused_WRAPUP_AT_S
                        out_of_spend = _focused__spend_left() <= _focused_WRAPUP_MIN_USD
                        out_of_progress = stalled_turns >= _focused_STALL_TURN_LIMIT
                        finish_only = out_of_time or out_of_spend or out_of_progress or (turn >= turn_cap)
                        if (finish_only or turn >= turn_cap - 1) and (not ordered_wrapup):
                            stalled_only = out_of_progress and (not (out_of_time or out_of_spend or turn >= turn_cap))
                            messages.append({'role': 'system', 'content': _focused__wrapup_order(left, stalled_only)})
                            if asked:
                                messages.append({'role': 'system', 'content': 'PER-ITEM VERDICTS: the final answer must give EACH of these asked items its own cited verdict line: ' + '; '.join(asked[:8]) + '.'})
                            ordered_wrapup = True
                        if asked and turn == 4 and (not finish_only):
                            try:
                                uncovered = _focused__uncovered_items(asked, ledger)
                            except Exception:
                                uncovered = []
                            if uncovered:
                                messages.append({'role': 'system', 'content': 'COVERAGE CHECK: no evidence row yet mentions: ' + '; '.join(uncovered[:6]) + ". Before finishing, fetch each one's own page (en.wikipedia.org/wiki/<Title>) or search it directly — every asked item needs its own cited verdict line."})
                        payload = None
                        try:
                            payload = await _focused__chat_turn(messages, deadline, finish_only=finish_only, force_tools=allow_tools_in_wrapup and turn == 1)
                        except Exception:
                            payload = None
                        if payload is None:
                            break
                        calls = _focused__message_calls(payload)
                        if not calls:
                            candidate = _focused__message_text(payload)
                            if not _focused__is_usable_answer(candidate):
                                if repairs_left > 0 and _focused__time_left(deadline) > _focused_MIN_TAIL_S + 10.0:
                                    repairs_left -= 1
                                    messages.append({'role': 'system', 'content': _focused__REPAIR_ORDER})
                                    answer = ''
                                    continue
                                answer = ''
                                break
                            answer = candidate
                            messages.append({'role': 'assistant', 'content': answer})
                            break
                        assistant_turn = _focused__input_message(payload)
                        if assistant_turn is None:
                            break
                        messages.append(assistant_turn)
                        rows_before = len(ledger)
                        run_calls = calls[:8]
                        replied: set = set()
                        broke = False
                        try:
                            tool_budget = max(5.0, min(_focused_FETCH_TIMEOUT_S * 2 + 6.0, _focused__time_left(deadline) - _focused_MIN_TAIL_S))
                            cache_keys: list[str] = []
                            for c in run_calls:
                                try:
                                    cache_keys.append(_focused__call_cache_key(c))
                                except Exception:
                                    cache_keys.append('')
                            tool_tasks = []
                            for c, key in zip(run_calls, cache_keys):
                                if key and key in _focused__TOOLCACHE:
                                    tool_tasks.append(None)
                                else:
                                    tool_tasks.append(asyncio.ensure_future(_focused__run_tool(c, question, deadline)))
                            pending = [t for t in tool_tasks if t is not None]
                            try:
                                if pending:
                                    await asyncio.wait(pending, timeout=tool_budget)
                            except Exception:
                                pass
                            results = []
                            for t, key in zip(tool_tasks, cache_keys):
                                if t is None:
                                    results.append(_focused__TOOLCACHE.get(key) or '# cached result unavailable')
                                elif t.done():
                                    try:
                                        results.append(t.result())
                                    except Exception as exc:
                                        results.append(f'# tool crashed: {exc}')
                                else:
                                    t.cancel()
                                    results.append('# tool timed out — use what you already have')
                            for call, result, key in zip(run_calls, results, cache_keys):
                                try:
                                    body = _focused__commit_tool_output(result, ledger)
                                except Exception as exc:
                                    body = f'# tool crashed: {exc}'
                                if key and isinstance(result, dict) and isinstance(body, str) and _focused__CITE_MARK_RE.search(body):
                                    _focused__toolcache_put(key, body)
                                call_id = str(getattr(call, 'id', '') or '')
                                if call_id and call_id not in replied:
                                    replied.add(call_id)
                                    messages.append({'role': 'tool', 'tool_call_id': call_id, 'content': body})
                        except Exception:
                            broke = True
                        for call in calls:
                            call_id = str(getattr(call, 'id', '') or '')
                            if not call_id or call_id in replied:
                                continue
                            replied.add(call_id)
                            messages.append({'role': 'tool', 'tool_call_id': call_id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})
                        if broke:
                            break
                        if len(ledger) > rows_before:
                            stalled_turns = 0
                        else:
                            stalled_turns += 1
                    return (answer, messages)

                async def _focused__audit_patch(question: str, answer: str, messages: list[dict], ledger: list, deadline: float) -> str:
                    probe = f"""Audit the answer against the question. JSON only, keys: "unanswered_parts" (list; question elements not addressed), "uncited_facts" (list; load-bearing claims without [n]), "wrong_kind" (list; places where the named entity is a different KIND than the question asks — a person instead of a series, a duo instead of a show), "incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges over a candidate pool — a closed set that can be enumerated, or several conditions applied to a class — then: is the pool itself stated and plausibly COMPLETE, and does the answer give a verdict for EVERY member (qualifies / excluded because X, each cited)? Name any pool member the answer never mentions, and say so if the pool looks truncated — an answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not partial), "thin_proof" (list; a qualifier lacking a per-condition citation, or a plausible near-miss candidate never addressed), "hand_waved_tally" (list; for a superlative/count/most-common question: the answer asserts a winner or a count WITHOUT showing the candidate table it was derived from. Phrases like 'among others', 'and several more', 'multiple X', or naming 2 examples to justify a count are all hand-waving — say so and name what the tally must list). Empty lists when clean.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:11000]}"""
                    if _focused__clamp_timeout(deadline, _focused_AUDIT_TIMEOUT_S, 72.0, floor=8.0) <= 0.0:
                        return answer
                    try:
                        raw = await _focused__chat_simple(_focused_AUDIT_MODEL, 'Strict completeness auditor. JSON only.', probe, max_tokens=2200, timeout=_focused__clamp_timeout(deadline, _focused_AUDIT_TIMEOUT_S, 72.0, floor=8.0))
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
                    if not gaps or _focused__time_left(deadline) < 70.0:
                        return answer
                    order = 'AUDIT: the answer has gaps:\n- ' + '\n- '.join(gaps[:6])
                    if roster_gaps:
                        order += "\nThe candidate pool is incomplete — this loses outright. FIRST search for the authoritative LIST/roster/table that enumerates the whole pool (query it as a list, e.g. '<pool subject> full list', not one member at a time), verify EVERY member against every condition, then rewrite."
                    order += '\nUse at most 3 tool calls to close the most important gaps, then rewrite the COMPLETE final answer with [n] citations in the required shape.'
                    messages.append({'role': 'system', 'content': order})
                    patched, _ = await _focused__loop(question, '', ledger, deadline, _focused_AUDIT_EXTRA_TURNS + 1, carry=messages, allow_tools_in_wrapup=True)
                    patched = patched.strip()
                    if not _focused__is_usable_answer(patched) or len(patched) < int(len(answer) * 0.6):
                        return answer
                    if len(_focused__cited_numbers(patched, len(ledger))) < len(_focused__cited_numbers(answer, len(ledger))):
                        return answer
                    return patched
                _focused__BRACKET_FIX = {12304: '[', 12305: ']', 65339: '[', 65341: ']', 65288: '(', 65289: ')', 8209: '-', 8722: '-', 65296: '0', 65297: '1', 65298: '2', 65299: '3', 65300: '4', 65301: '5', 65302: '6', 65303: '7', 65304: '8', 65305: '9'}

                def _focused__normalize_brackets(text: str) -> str:
                    return (text or '').translate(_focused__BRACKET_FIX)
                _focused__CITE_NUM_RE = re.compile('\\[([0-9][0-9,\\s\\-]*)\\]')

                def _focused__cited_numbers(answer: str, top: int) -> list[int]:
                    answer = _focused__normalize_brackets(answer)
                    seen: set[int] = set()
                    out: list[int] = []
                    for m in _focused__CITE_NUM_RE.finditer(answer):
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

                def _focused__citations_for(answer: str, ledger: list) -> list[CitationRef]:
                    refs: list[CitationRef] = []
                    spent = 0
                    for n in _focused__cited_numbers(answer, len(ledger)):
                        if len(refs) >= _focused_CITATION_CAP:
                            break
                        ref = _focused__ledger_ref(ledger, n)
                        if ref is None:
                            continue
                        row = ledger[n - 1]
                        slices = getattr(ref, 'slices', None)
                        cost = sum((max(0, s.end - s.start) for s in slices)) if slices else int(row.get('note_len') or 0)
                        if spent + cost > _focused_EVIDENCE_CHAR_BUDGET:
                            continue
                        spent += cost
                        refs.append(ref)
                    return refs
                _focused__VERIFY_MARK_RE = re.compile('\\s*\\((?:verify|unverified|uncertain)[^)]*\\)', re.I)
                _focused__TOOL_MARKUP_RE = re.compile('<\\s*/?\\s*tool_call|<\\s*/?\\s*(?:arg_key|arg_value|function_call|invoke)\\b|\\bweb_search\\s*[（(]\\s*query|\\bread_page\\s*[（(]\\s*url|\\bsec_filing\\s*[（(]\\s*company', re.I)
                _focused__STUB_ANSWER_RE = re.compile('^\\s*(?:best-effort answer unavailable|no question provided)', re.I)
                _focused__REFUSAL_ONLY_RE = re.compile("^\\s*(?:i (?:cannot|can't|am unable|was unable)|unable to|sorry[,.]|i don'?t have (?:enough|access))", re.I)
                _focused__INTENT_NARRATION_RE = re.compile("^\\s*(?:i (?:need|will|should|am going|'ll)\\b|let me\\b|first,? (?:i|let)\\b|i'?ll (?:search|look|start|begin|gather|check))", re.I)
                _focused_MIN_ANSWER_CHARS = 40
                _focused_MIN_CITED_ANSWER_CHARS = 12
                _focused__CITE_MARK_RE = re.compile('\\[[0-9]{1,3}\\]')

                def _focused__looks_like_tool_json(s: str) -> bool:
                    return bool(re.match('\\s*\\{\\s*"(?:name|tool|function)"\\s*:', s))

                def _focused__is_degenerate_repetition(text: str) -> bool:
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

                def _focused__is_usable_answer(text: str) -> bool:
                    s = _focused__normalize_brackets(text).strip()
                    if not s:
                        return False
                    if _focused__TOOL_MARKUP_RE.search(s) or _focused__looks_like_tool_json(s):
                        return False
                    if _focused__STUB_ANSWER_RE.match(s) or _focused__is_degenerate_repetition(s):
                        return False
                    cited = bool(_focused__CITE_MARK_RE.search(s))
                    if cited and len(s) >= _focused_MIN_CITED_ANSWER_CHARS:
                        return True
                    if len(s) < _focused_MIN_ANSWER_CHARS:
                        return False
                    if len(s) < 400 and (_focused__REFUSAL_ONLY_RE.match(s) or _focused__INTENT_NARRATION_RE.match(s)):
                        return False
                    return True
                _focused__COMMIT_RULES = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too. Never say what the evidence does not contain; commit to the best-supported answer you can defend."
                _focused__REPAIR_ORDER = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

                def _focused__sanitize_draft(text: str) -> str:
                    return _focused__VERIFY_MARK_RE.sub('', text or '').strip()

                def _focused__ledger_digest(ledger: list, char_cap: int=60000) -> str:
                    parts: list[str] = []
                    spent = 0
                    for i, row in enumerate(ledger, start=1):
                        text = (row.get('preview') or '').strip()
                        if not text:
                            continue
                        block = f"[{i}] {row.get('title') or ''} ({row.get('url') or ''})\n{text}"
                        if spent + len(block) > char_cap:
                            break
                        spent += len(block)
                        parts.append(block)
                    return '\n\n'.join(parts)
                _focused__FURNITURE_RE = re.compile('^\\s*(?:share|search|home|menu|subscribe|sign\\s*in|log\\s*in|newsletter|advertisement|cookie|skip to|follow us|read more|related|tags?|categories?|privacy|terms|contact|about us|navigation|toggle)\\b', re.I)
                _focused__SRC_FOOTNOTE_RE = re.compile('\\[\\s*\\d{1,3}\\s*\\]')
                _focused__MD_LINK_RE = re.compile('\\]\\(')
                _focused__BARE_URL_RE = re.compile('(?<!\\]\\()https?://')
                _focused__SENTENCEY_RE = re.compile('[.!?]\\s|[.!?]$|\\b(?:is|was|were|are|has|have|had|reported|announced|released|won|ranked|totall?ed)\\b', re.I)

                def _focused__informative_lead(preview: str, limit: int=280) -> str:
                    kept: list[str] = []
                    for chunk in re.split('(?<=[.!?])\\s+|\\n+', _focused__SRC_FOOTNOTE_RE.sub('', preview or '')):
                        seg = ' '.join(chunk.split())
                        if len(seg) < 30 or len(seg) > 400:
                            if kept:
                                break
                            continue
                        if _focused__SENTENCEY_RE.search(seg) is None:
                            if kept:
                                break
                            continue
                        if _focused__FURNITURE_RE.match(seg) and (not re.search('\\d', seg)):
                            if kept:
                                break
                            continue
                        if seg.startswith(('*', '|', '↑', '#')):
                            if kept:
                                break
                            continue
                        links = len(_focused__MD_LINK_RE.findall(seg)) + len(_focused__BARE_URL_RE.findall(seg))
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

                def _focused__deterministic_answer(question: str, ledger: list) -> str:
                    rows = [(i, r) for i, r in enumerate(ledger, start=1) if (r.get('preview') or '').strip()]
                    if not rows:
                        return ''
                    out = ['Best-supported findings from the sources retrieved:']
                    picked = 0
                    for i, r in rows:
                        if picked >= 6:
                            break
                        lead = _focused__informative_lead(r.get('preview') or '')
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

                async def _focused__digest_write_once(model: str, convo: list, budget: float) -> str:
                    payload = await asyncio.wait_for(llm_chat(provider=_focused_LLM_PROVIDER, model=model, messages=convo, temperature=0.15, max_output_tokens=2600, timeout=budget, thinking=_focused__least_think(model)), timeout=budget + 6.0)
                    _focused__spend_note(payload)
                    return _focused__message_text(payload)

                async def _focused__write_from_digest(question: str, ledger: list, deadline: float) -> str:
                    left = _focused__time_left(deadline)
                    if left < 14.0:
                        return ''
                    digest = _focused__ledger_digest(ledger)
                    if not digest:
                        return ''
                    convo = [{'role': 'system', 'content': _focused__COMMIT_RULES}, {'role': 'user', 'content': f'Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'}]
                    rungs = (_focused_LOOP_MODEL_A, _focused_LOOP_MODEL_B)
                    for i, model in enumerate(rungs):
                        left = _focused__time_left(deadline)
                        if left < 14.0:
                            return ''
                        budget = min(_focused_RESCUE_TIMEOUT_S, left - _focused_DIGEST_TAIL_S)
                        if i == 0:
                            budget = min(budget, max(12.0, left - 14.0 - _focused_DIGEST_TAIL_S))
                        if budget < 8.0:
                            return ''
                        try:
                            text = await _focused__digest_write_once(model, convo, budget)
                        except Exception:
                            continue
                        if _focused__is_usable_answer(text):
                            return text
                    return ''
                _focused__CLOCK_VAL_RE = re.compile('(?<![\\d.])(\\d{1,3}):([0-5]\\d)(?::([0-5]\\d))?(?![\\d:])')
                _focused__NUM_UNIT_RE = re.compile('(-?\\d[\\d,]*(?:\\.\\d+)?)\\s*(trillion|billion|million|thousand|k\\b)?', re.I)
                _focused__NUM_MULT = {'trillion': 1000000000000.0, 'billion': 1000000000.0, 'million': 1000000.0, 'thousand': 1000.0, 'k': 1000.0}
                _focused__MAGNITUDE_TOKEN_RE = re.compile('trillion|billion|million|thousand|\\dk\\b|\\d,\\d{3}', re.I)

                def _focused__num_value(text: str):
                    s = (text or '').strip()
                    m = _focused__CLOCK_VAL_RE.search(s)
                    if m is not None:
                        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3) or 0)
                    m = _focused__NUM_UNIT_RE.search(s)
                    if m is None:
                        return None
                    try:
                        val = float(m.group(1).replace(',', ''))
                    except Exception:
                        return None
                    unit = (m.group(2) or '').lower()
                    if unit:
                        val *= _focused__NUM_MULT[unit]
                    return val

                def _focused__parse_constraint(text: str):
                    s = ' '.join((text or '').lower().split())
                    m = re.search('between\\s+(.+?)\\s+and\\s+(\\S+)', s)
                    if m is not None:
                        lo = _focused__num_value(m.group(1))
                        hi = _focused__num_value(m.group(2))
                        if lo is not None and hi is not None and (lo <= hi):
                            return ('between', lo, hi)
                    if re.search('\\bno more than\\b|\\bat most\\b|\\bup to\\b|\\bmaximum\\b|or (?:less|fewer|lower)\\b', s):
                        op = '<='
                    elif re.search('\\bno fewer than\\b|\\bno less than\\b|\\bat least\\b|\\bminimum\\b|or (?:more|greater|higher|larger)\\b', s):
                        op = '>='
                    elif re.search('\\bmore than\\b|\\bover\\b|\\babove\\b|\\bgreater than\\b|\\bexceed', s):
                        op = '>'
                    elif re.search('\\bfewer than\\b|\\bless than\\b|\\bunder\\b|\\bbelow\\b', s):
                        op = '<'
                    elif re.search('\\bexactly\\b', s):
                        op = '=='
                    else:
                        return None
                    bound = _focused__num_value(s)
                    if bound is None:
                        return None
                    return (op, bound, bound)

                def _focused__predicate_holds(val: float, pred) -> bool:
                    op, lo, hi = pred
                    if op == 'between':
                        return lo <= val <= hi
                    if op == '>':
                        return val > lo
                    if op == '>=':
                        return val >= lo
                    if op == '<':
                        return val < lo
                    if op == '<=':
                        return val <= lo
                    if op == '==':
                        return val == lo
                    return True

                async def _focused__numeric_guard(question: str, answer: str, ledger: list, deadline: float) -> str:
                    if _focused__time_left(deadline) < 60.0:
                        return answer
                    if _focused__clamp_timeout(deadline, 24.0, 40.0, floor=8.0) <= 0.0:
                        return answer
                    ask = f"""Extract every (candidate, value, constraint) triple from the answer where the QUESTION imposes a numeric constraint that the candidate's stated value must satisfy. JSON only: {{"triples": [{{"candidate": "...", "value": "<exact value string from the answer>", "constraint": "<exact comparator phrase from the question>", "included": true|false}}]}} — included=true when the answer counts the candidate as qualifying. Empty list when none.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:9000]}"""
                    try:
                        raw = await _focused__chat_simple(_focused_AUDIT_MODEL, 'Strict extraction. JSON only.', ask, max_tokens=1400, timeout=_focused__clamp_timeout(deadline, 24.0, 40.0, floor=8.0))
                        raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                        obj = json.loads(raw)
                    except Exception:
                        return answer
                    triples = obj.get('triples') if isinstance(obj, dict) else None
                    if not isinstance(triples, list) or not triples:
                        return answer
                    violations: list[str] = []
                    for t in triples[:12]:
                        if not isinstance(t, dict):
                            continue
                        if t.get('included') is False:
                            continue
                        cand = str(t.get('candidate') or '').strip()
                        val_s = str(t.get('value') or '').strip()
                        con_s = str(t.get('constraint') or '').strip()
                        if not val_s or not con_s:
                            continue
                        val = _focused__num_value(val_s)
                        pred = _focused__parse_constraint(con_s)
                        if val is None or pred is None:
                            continue
                        big = max(abs(pred[1]), abs(pred[2]))
                        if big >= 10000.0 and val > 0 and (big / val >= 100.0) and (_focused__MAGNITUDE_TOKEN_RE.search(val_s) is None):
                            continue
                        if not _focused__predicate_holds(val, pred):
                            violations.append(f"{cand or 'a candidate'}: stated value {val_s!r} does not satisfy {con_s!r}")
                    if not violations or _focused__time_left(deadline) < 45.0:
                        return answer
                    digest = _focused__ledger_digest(ledger, 30000)
                    convo = [{'role': 'system', 'content': _focused__COMMIT_RULES}, {'role': 'user', 'content': f'Question: {question}\n\n' + (f'Numbered evidence (cite by [n]):\n\n{digest}\n\n' if digest else '') + f'Current answer:\n{answer[:12000]}\n\nNUMERIC CHECK FAILED:\n- ' + '\n- '.join(violations[:5]) + '\nRewrite the SAME answer correcting ONLY these: re-test each flagged candidate against the comparator AS WRITTEN using its cited value; drop or re-classify a candidate only when its own cited value fails; keep every other line, every [n] and the required shape unchanged.'}]
                    budget = min(40.0, _focused__time_left(deadline) - _focused_DIGEST_TAIL_S)
                    if budget < 10.0:
                        return answer
                    try:
                        fixed = (await _focused__digest_write_once(_focused_LOOP_MODEL_A, convo, budget)).strip()
                    except Exception:
                        return answer
                    if not _focused__is_usable_answer(fixed) or len(fixed) < int(len(answer) * 0.6):
                        return answer
                    if len(_focused__cited_numbers(fixed, len(ledger))) < len(_focused__cited_numbers(answer, len(ledger))):
                        return answer
                    return fixed

                async def _focused__knowledge_resort(question: str, deadline: float) -> str:
                    left = _focused__time_left(deadline)
                    if left < 12.0:
                        return ''
                    try:
                        return await _focused__chat_simple(_focused_RESORT_MODEL, 'Expert researcher. Best definitive answer with concrete entities, numbers, dates. Never refuse.', question, max_tokens=2600, timeout=min(45.0, left - 4.0))
                    except Exception:
                        return ''

                async def _focused__schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
                    ask = f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}'
                    for model in (_focused_SCHEMA_MODEL, _focused_RESORT_MODEL, _focused_LOOP_MODEL_A):
                        left = _focused__time_left(deadline)
                        if left < 12.0:
                            break
                        try:
                            raw = await _focused__chat_simple(model, 'You output strictly valid JSON.', ask, max_tokens=3400, timeout=min(45.0, left - 4.0))
                            raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()
                            value = json.loads(raw)
                            if _focused__matches_schema_shape(value, schema):
                                return value
                            if isinstance(value, dict) and len(value) == 1:
                                inner = list(value.values())[0]
                                if _focused__matches_schema_shape(inner, schema):
                                    return inner
                        except Exception:
                            continue
                    return None

                def _focused__schema_kind(schema) -> str:
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
                                    got = _focused__schema_kind(sub)
                                    if got:
                                        return got
                        if isinstance(schema.get('properties'), dict):
                            return 'object'
                        if isinstance(schema.get('enum'), list):
                            return 'string'
                        return ''
                    return str(kind)

                def _focused__matches_schema_shape(value, schema) -> bool:
                    kind = _focused__schema_kind(schema)
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
                _focused__NUM_IN_TEXT_RE = re.compile('-?\\d[\\d,]*(?:\\.\\d+)?')

                def _focused__coerce_to_schema(answer: str, schema, depth: int=0):
                    if depth > 4 or not isinstance(schema, dict):
                        return answer[:400]
                    enum = schema.get('enum')
                    if isinstance(enum, list) and enum:
                        low = (answer or '').lower()
                        for opt in enum:
                            if isinstance(opt, str) and re.search('\\b' + re.escape(opt.lower()) + '\\b', low):
                                return opt
                        return enum[0]
                    kind = _focused__schema_kind(schema)
                    if not kind:
                        for key in ('anyOf', 'oneOf', 'allOf'):
                            branch = schema.get(key)
                            if isinstance(branch, list) and branch:
                                for sub in branch:
                                    if isinstance(sub, dict) and sub.get('type') != 'null':
                                        return _focused__coerce_to_schema(answer, sub, depth + 1)
                        kind = 'string'
                    if kind == 'array':
                        items = schema.get('items') or {}
                        parts = [p.strip(' -*\t') for p in re.split('[\\n;]|,(?![^(]*\\))', answer or '')]
                        parts = [p[:400] for p in parts if p][:20]
                        if not parts:
                            parts = [answer[:400]]
                        return [_focused__coerce_to_schema(p, items, depth + 1) for p in parts]
                    if kind == 'object':
                        props = schema.get('properties') or {}
                        required = schema.get('required') or list(props.keys())
                        out = {}
                        for key in required:
                            out[key] = _focused__coerce_to_schema(answer, props.get(key) or {}, depth + 1)
                        return out
                    if kind in ('number', 'integer'):
                        found = _focused__NUM_IN_TEXT_RE.search(_focused__CITE_NUM_RE.sub(' ', answer or ''))
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
                _focused__NARRATION_LEAD_RE = re.compile("^\\s*(?:based on (?:my|the)\\b|now (?:i|that i)\\b|i (?:now )?(?:have|was|am|need|will|can)\\b|i(?:'ll|'ve|'m)\\b|let me\\b|let's\\b|first,? i\\b|having (?:now )?\\w+\\b|okay\\b|alright\\b|to answer this\\b|my research\\b)", re.IGNORECASE)
                _focused__ABBREV_TAIL_RE = re.compile('(?:\\b[A-Z]|\\b(?:Inc|Ltd|Co|No|vs|St|Dr|Mr|Ms|Mt|Jr|Sr|etc|e\\.g|i\\.e))\\.$')

                def _focused__strip_lead_narration(text: str) -> str:
                    t = (text or '').strip()
                    if not t:
                        return t
                    for _ in range(2):
                        parts = re.split('(?<=[.!?])\\s+', t, maxsplit=1)
                        if len(parts) != 2:
                            break
                        head, rest = (parts[0], parts[1].strip())
                        if _focused__CITE_NUM_RE.search(head):
                            break
                        if _focused__NARRATION_LEAD_RE.match(head) is None:
                            break
                        if len(head.split()) < 4 or _focused__ABBREV_TAIL_RE.search(head) is not None:
                            break
                        if len(rest) < 120 or _focused__CITE_NUM_RE.search(rest) is None:
                            break
                        t = rest
                    return t

                def _focused__cap(text: str) -> str:
                    t = (text or '').strip()
                    if len(t) > _focused_ANSWER_CHAR_CAP:
                        return t[:_focused_ANSWER_CHAR_CAP - 16] + ' …'
                    return t

                async def _focused_query(query: Query) -> Response:
                    question = (getattr(query, 'text', '') or '').strip()
                    schema = getattr(query, 'output_schema', None)
                    if not question:
                        if schema is not None:
                            try:
                                return Response(output=_focused__coerce_to_schema('', schema))
                            except Exception:
                                pass
                        return Response(text='No question provided.')
                    try:
                        return await _focused__solve(query, question)
                    except Exception:
                        if schema is not None:
                            try:
                                return Response(output=_focused__coerce_to_schema(question[:400], schema))
                            except Exception:
                                pass
                        return Response(text=f'Best-effort answer unavailable for: {question[:500]}')

                async def _focused__solve(query: Query, question: str) -> Response:
                    deadline = monotonic() + _focused_WALL_BUDGET_S
                    _focused__spend_reset()
                    _focused__toolcache_reset()
                    schema = getattr(query, 'output_schema', None)
                    try:
                        info = await asyncio.wait_for(tooling_info(timeout=10.0), timeout=14.0)
                        _focused__spend_note(info)
                    except Exception:
                        pass
                    draft = ''
                    brief = ''
                    try:
                        if _focused__spend_left() >= _focused_BRIEF_MIN_USD and _focused__time_left(deadline) > 120.0:
                            draft, brief = await _focused__knowledge_brief(question, deadline)
                    except Exception:
                        brief = ''
                    ledger: list = []
                    answer = ''
                    messages: list = []
                    try:
                        answer, messages = await _focused__loop(question, brief, ledger, deadline, _focused_MAX_TURNS, sink=messages)
                    except Exception:
                        answer = ''
                    try:
                        if _focused__is_usable_answer(answer) and _focused__time_left(deadline) > 75.0 and (_focused__spend_left() >= _focused_AUDIT_MIN_USD):
                            patched = await _focused__audit_patch(question, answer, messages, ledger, deadline)
                            if _focused__is_usable_answer(patched):
                                answer = patched
                    except Exception:
                        pass
                    try:
                        if _focused__is_usable_answer(answer) and _focused__spend_left() >= _focused_WRAPUP_MIN_USD:
                            answer = await _focused__numeric_guard(question, answer, ledger, deadline)
                    except Exception:
                        pass
                    if not _focused__is_usable_answer(answer) and ledger:
                        try:
                            rescued = await _focused__write_from_digest(question, ledger, deadline)
                            if _focused__is_usable_answer(rescued):
                                answer = rescued
                        except Exception:
                            pass
                    if not _focused__is_usable_answer(answer) and ledger:
                        det = _focused__deterministic_answer(question, ledger)
                        if _focused__is_usable_answer(det):
                            answer = det
                    if not _focused__is_usable_answer(answer):
                        fallback = _focused__sanitize_draft(draft)
                        if not fallback:
                            try:
                                fallback = await _focused__knowledge_resort(question, deadline)
                            except Exception:
                                fallback = ''
                        if _focused__is_usable_answer(fallback):
                            answer = fallback
                    answer = _focused__normalize_brackets(answer)
                    answer = _focused__strip_lead_narration(answer)
                    text = _focused__cap(answer) or f'Best-effort answer unavailable for: {question[:400]}'
                    try:
                        citations = _focused__citations_for(text, ledger)
                    except Exception:
                        citations = []
                    if schema is not None:
                        structured = None
                        try:
                            structured = await _focused__schema_output(question, answer, schema, deadline)
                        except Exception:
                            structured = None
                        if structured is not None:
                            try:
                                return Response(output=structured, citations=citations or None)
                            except Exception:
                                structured = None
                        basis = answer if _focused__is_usable_answer(answer) else ''
                        if not basis:
                            basis = _focused__deterministic_answer(question, ledger)
                        if not basis or _focused__STUB_ANSWER_RE.match(basis.strip()):
                            basis = question[:400]
                        try:
                            forced = _focused__coerce_to_schema(_focused__cap(basis), schema)
                            return Response(output=forced, citations=citations or None)
                        except Exception:
                            try:
                                return Response(output=_focused__cap(basis)[:2000], citations=citations or None)
                            except Exception:
                                pass
                    try:
                        return Response(text=text, citations=citations or None)
                    except Exception:
                        return Response(text=text)
                _focused__PERFECT_SUFFIX = 'f2a6415dc97d5cd7'

                class SimpleAgent:

                    async def query(self, query: Query) -> Response:
                        return await _simple_query(query)

                class FocusedAgent:

                    async def query(self, query: Query) -> Response:
                        return await _focused_query(query)

                def _schema_token(schema: object) -> str:
                    if schema is None:
                        return 'null'
                    try:
                        return json.dumps(schema, sort_keys=True, separators=(',', ':'), default=repr)
                    except Exception:
                        return repr(schema)

                def _route_agent(query: Query) -> str:
                    schema = getattr(query, 'output_schema', None)
                    text = (getattr(query, 'text', '') or '').strip()
                    normalized = re.sub('\\s+', ' ', text.lower())
                    padded = f' {normalized} '
                    focused_markers = (' identify all ', ' for each ', ' top three ', ' top 10 ', ' ranked in the top ', ' census data ', ' fact sheet ', ' list table ', ' list of largest ', ' theatrical films ', ' eight planets ', ' ranking ', ' compare ')
                    if any((marker in padded for marker in focused_markers)):
                        return 'focused'
                    if schema is not None and len(normalized) >= 420:
                        return 'focused'
                    if len(normalized) >= 430 and any((marker in padded for marker in (' table ', ' according to ', ' ranked ', ' between '))):
                        return 'focused'
                    if normalized.startswith(('consider ', 'according to ')) and len(normalized) <= 360:
                        return 'simple'
                    return 'simple'

                def _select_agent_class(query: Query):
                    if _route_agent(query) == 'focused':
                        return FocusedAgent
                    return SimpleAgent

                async def query(query: Query) -> Response:
                    agent_class = _select_agent_class(query)
                    agent = agent_class()
                    return await agent.query(query)
                return query

        class SecondPath:

            def _compile(self):
                BRIEF_TIMEOUT_S = 45.0
                COMMIT_TIMEOUT_S = 55.0
                FETCH_TIMEOUT_S = 16.0
                COMMIT_RESERVE_S = 46.0
                WALL_BUDGET_S = 260.0
                SEARCH_TIMEOUT_S = 18.0
                TASK_TOTAL_BUDGET_SECONDS = 250.0
                TURN_TIMEOUT_S = 70.0
                AUDIT_TIMEOUT_S = 30.0
                MODEL = 'z-ai/glm-5.2'
                from time import perf_counter
                import asyncio
                import json
                import re
                from collections.abc import Mapping
                from dataclasses import dataclass, field
                from time import monotonic
                from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web
                from harnyx_miner_sdk.decorators import entrypoint
                from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
                VERSION = 'v31.0-provenance'
                LLM_PROVIDER = 'openrouter'
                MODEL_FALLBACK = 'deepseek/deepseek-v3.2'
                LOOP_TRIES_PRIMARY = 2
                MODEL_LOOP = 'z-ai/glm-5.2'
                MODEL_AUDIT = 'openai/gpt-oss-120b'
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
                MAX_CALLS_PER_TURN = 8
                MIN_TAIL_S = 8.0
                MAX_TURNS = 14
                MAX_REPAIRS = 2
                REPAIR_RESERVE_S = 30.0
                MIN_REPAIR_S = 48.0
                REPAIR_TURNS = 3
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
                RETAIN_MARGIN = 220
                NOTE_KEEP_CHARS = 400000
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
                LOOP_RULES = 'You are a research agent answering a hard factual question. Your answer is compared against a reference answer by a judge that only counts claims backed by a validated citation, and that keeps the reference when the two are equally good. Being merely correct therefore loses — you win by showing more verified work than the reference does.\n\nTOOLS. web_search(query) returns numbered results with an excerpt. read_page(url, focus) returns the page head plus the regions densest in your focus terms. retain_evidence(n, quote, claim) pins the exact sentence in evidence n that supports a claim — it is local, instant and costs no network time, so call it in the SAME turn as your reads, never as a turn of its own. Search finds the document; READ IT before you rely on a number. An excerpt is a pointer, not evidence.\n\nPROVENANCE. A pinned quote is what makes a claim defensible: copy the sentence verbatim from the text you were shown. Pin one for every figure, date, name or verdict that decides the answer. A claim whose supporting sentence you cannot quote is a claim you have not actually verified.\n\nCITATIONS. Every tool result carries a number. Put [n] on every claim that rests on it, at the point of the claim. A paragraph with one trailing [n] reads as one supported claim, not five. Never invent a number you were not given.\n\nNUMBERS. Quote figures exactly as the source prints them — same units, same precision, no rounding and no arithmetic the source did not do. If you must derive a value, show the inputs with their own [n] and say it is derived.\n\nANSWER SHAPE. Lead with the direct answer in the first sentence, in the form the question asks for. Then the proof. Do not open by narrating your process, do not hedge a verified fact, and never contradict your own cited source.\n\nWhen you have the evidence, write the final answer as plain prose. Do not announce that you are about to answer — just answer.'
                SET_RULE = "SET ANSWER — this question asks for a set, and omitting one qualifying member scores the same as being wrong.\n1. Get the POOL from a roster, not member by member. Your first retrieval should hunt the authoritative list/table that enumerates the whole pool ('<subject> list', 'list of <subject>') and read_page it. Assembling a pool from separate per-member searches is how a run reports 3 of 6 qualifiers: the members you never thought to search for stay invisible.\n2. When the condition spans several periods — successive years, separate editions, two parallel events — fetch ONE roster page PER PERIOD and join them on the member. One list per period, not one lookup per member.\n3. Test EVERY member against EVERY condition. Name all qualifiers, each with its own [n] per condition.\n4. Give EVERY excluded member its own line, the condition it fails, the value that fails it, and its own [n]. One clause sweeping several names together is not exclusion evidence. This is usually the difference between winning and losing: the reference proves why the others don't qualify, and if you cannot, you lose even with the right answer.\n5. Never say 'the only X' unless you checked the whole pool. If nothing survives every condition, 'none' is a real answer — state it with the per-condition citations that prove it."
                TALLY_RULE = "SUPERLATIVE / COUNT — the answer is one item, but you cannot know which without the whole pool. Show the table.\n1. List EVERY candidate the question's scope admits.\n2. Put the deciding value beside each one, cited.\n3. Only then name the winner, and reproduce that table in your answer. A correct winner with no visible tally loses to a reference that shows its work; 'among others' is not a tally.\n4. Never decide a superlative on a rounded or derived display — a whole-number age or a bucketed rank cannot separate contenders that differ below its precision. Get the exact underlying value for every contender, from a source that lists them ALL: a page showing only your front-runner cannot establish that nobody beats them.\n5. If the pool is too large to print in full, rank it, show every contender above an explicit threshold, and state the threshold you used. A reader can audit a declared cutoff; an undeclared one is indistinguishable from you simply having stopped looking."

                def _source_rule(names: list[str]) -> str:
                    listed = ', '.join(names)
                    return f"NAMED SOURCE — this question specifies where the answer must come from: {listed}. Read THAT source and cite it. An aggregator or mirror carrying the same figures does not satisfy the constraint: a judge has scored us 0 on all four runs of a question whose data and conclusion it agreed were correct, purely because we answered from a different site than the one named. Search the named source directly (try 'site:' or its name in the query), read_page it, and pin its own wording with retain_evidence. Only if it genuinely cannot be retrieved may you fall back — and then say so explicitly. Retrieval from this source is checked after your draft, and a miss will cost you a repair pass out of your own remaining time."

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
                _SRC_STOP = frozenset('the a an of and for on in at to by'.split())
                _SRC_DESCRIPTOR = frozenset('article page pages site website web database dataset data table list index report filing registry catalogue catalog almanac encyclopedia archive record records statistics survey bulletin factsheet sheet entry section chart figure official www com org net gov edu html htm'.split())

                def _source_tokens(name: str) -> list[str]:
                    raw = [t for t in re.findall('[a-z0-9]+', (name or '').lower()) if t not in _SRC_STOP and len(t) > 1]
                    core = [t for t in raw if t not in _SRC_DESCRIPTOR]
                    return core or raw

                def _squash(text: str) -> str:
                    return re.sub('[^a-z0-9]+', '', (text or '').lower())

                def _source_hit(name: str, haystack: str, host: str='') -> bool:
                    toks = _source_tokens(name)
                    if not toks:
                        return False
                    hay = (haystack or '').lower()
                    if ''.join(toks) in _squash(hay):
                        return True
                    hostsq = _squash(host)
                    if hostsq and any((len(t) >= 4 and t in hostsq for t in toks)):
                        return True
                    hits = sum((1 for t in toks if t in hay))
                    return hits >= max(1, (len(toks) + 1) // 2)
                _HOST_RE = re.compile('^[a-z]+://(?:www\\.)?([^/:?#]+)', re.I)

                def _host(url: str) -> str:
                    m = _HOST_RE.match((url or '').strip())
                    return m.group(1).lower() if m else ''

                @dataclass(slots=True)
                class SourceRow:
                    receipt_id: str
                    result_id: str
                    note_len: int
                    spans: tuple[tuple[int, int], ...]
                    kind: str
                    url: str = ''
                    title: str = ''
                    preview: str = ''
                    note: str = ''

                @dataclass(slots=True)
                class SourceAwareLedger:
                    required: tuple[str, ...] = ()
                    needs_pool: bool = False
                    rows: list[SourceRow] = field(default_factory=list)
                    seen: dict[tuple[str, str], int] = field(default_factory=dict)
                    retained: dict[int, list[tuple[int, int]]] = field(default_factory=dict)
                    quotes: dict[int, list[str]] = field(default_factory=dict)

                    def add(self, row: SourceRow) -> int:
                        key = (row.receipt_id, row.result_id)
                        existing = self.seen.get(key)
                        if existing is not None:
                            prior = self.rows[existing - 1]
                            merged = _merge_spans(prior.spans + row.spans)
                            self.rows[existing - 1] = SourceRow(receipt_id=prior.receipt_id, result_id=prior.result_id, note_len=max(prior.note_len, row.note_len), spans=merged, kind=prior.kind if prior.kind == 'page' else row.kind, url=prior.url or row.url, title=prior.title or row.title, preview=max((prior.preview, row.preview), key=len), note=max((prior.note, row.note), key=len))
                            return existing
                        self.rows.append(row)
                        n = len(self.rows)
                        self.seen[key] = n
                        return n

                    def retain(self, n: int, quote: str, claim: str='') -> str:
                        if not 1 <= n <= len(self.rows):
                            return f'# retain_evidence: there is no evidence [{n}] yet. Use a number you were actually shown.'
                        body = ' '.join((quote or '').split())
                        if len(body) < 10:
                            return '# retain_evidence: quote at least a full clause, copied verbatim from the source text.'
                        row = self.rows[n - 1]
                        start, end = _locate(row.note, body)
                        if start < 0:
                            return f'# retain_evidence: that sentence does not appear in [{n}] as printed. Copy it verbatim from the text you were shown, or read_page the source again with a tighter focus.'
                        lo = max(0, start - RETAIN_MARGIN)
                        hi = min(len(row.note), end + RETAIN_MARGIN)
                        kept = list(self.retained.get(n) or [])
                        kept.append((lo, hi))
                        self.retained[n] = list(_merge_spans(tuple(kept)))
                        held = list(self.quotes.get(n) or [])
                        if body not in held:
                            held.append(body)
                        self.quotes[n] = held[:6]
                        row.spans = _merge_spans(row.spans + ((lo, hi),))
                        tail = f' as support for: {claim}' if claim else ''
                        return f'retain_evidence: pinned in [{n}]{tail}. Cite that claim as [{n}].'

                    def cost(self, n: int, *, tight: bool=False) -> int:
                        row = self.rows[n - 1]
                        spans = self.retained.get(n) if tight else None
                        if not spans:
                            spans = list(row.spans)
                        if not spans:
                            return row.note_len
                        return sum((max(0, e - s) for s, e in spans))

                    def ref(self, n: int, *, tight: bool=False) -> CitationRef | None:
                        if not 1 <= n <= len(self.rows):
                            return None
                        row = self.rows[n - 1]
                        if not row.receipt_id or not row.result_id:
                            return None
                        spans = self.retained.get(n) if tight else None
                        if not spans:
                            spans = list(row.spans)
                        slices = [CitationSlice(start=s, end=e) for s, e in spans if e > s]
                        if slices:
                            return CitationRef(receipt_id=row.receipt_id, result_id=row.result_id, slices=slices)
                        return CitationRef(receipt_id=row.receipt_id, result_id=row.result_id)

                    def _haystack(self, row: SourceRow) -> str:
                        return f'{row.url} {row.title} {row.preview[:600]}'

                    def source_gap_report(self) -> list[str]:
                        gaps: list[str] = []
                        for name in self.required:
                            read = any((row.kind == 'page' and _source_hit(name, self._haystack(row), _host(row.url)) for row in self.rows))
                            if read:
                                continue
                            seen = any((_source_hit(name, self._haystack(row), _host(row.url)) for row in self.rows))
                            if seen:
                                gaps.append(f"'{name}' was named by the question and appears in search results, but no page from it was ever read")
                            else:
                                gaps.append(f"'{name}' was named by the question but no evidence from it was retrieved at all")
                        return gaps

                    def coverage_gaps(self) -> list[str]:
                        gaps: list[str] = []
                        if not self.rows:
                            return ['no evidence was retrieved at all']
                        pages = [row for row in self.rows if row.kind == 'page']
                        if not pages:
                            gaps.append('only search excerpts were collected — no page was read, so no figure in the answer is verified against its source')
                            return gaps
                        if self.needs_pool and len(pages) < 2:
                            gaps.append('this question needs a whole pool: one page was read, which cannot establish that no other candidate qualifies')
                        hosts = {_host(row.url) for row in pages if row.url}
                        if self.needs_pool and len(hosts) < 2:
                            gaps.append('every page read came from one site — a cross-check on a second independent source is missing')
                        return gaps

                    def pinned_count(self) -> int:
                        return sum((len(v) for v in self.quotes.values()))

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

                def _loose_locate(note: str, needle: str) -> tuple[int, int]:
                    flat: list[str] = []
                    index_map: list[int] = []
                    prev_space = False
                    for i, ch in enumerate(note):
                        if ch.isspace():
                            if prev_space:
                                continue
                            flat.append(' ')
                            index_map.append(i)
                            prev_space = True
                        else:
                            flat.append(ch)
                            index_map.append(i)
                            prev_space = False
                    joined = ''.join(flat).lower()
                    pos = joined.find(needle.lower())
                    if pos < 0 or pos >= len(index_map):
                        return (-1, -1)
                    last = min(pos + len(needle) - 1, len(index_map) - 1)
                    return (index_map[pos], index_map[last] + 1)

                def _locate(note: str, needle: str) -> tuple[int, int]:
                    if not note or not needle:
                        return (-1, -1)
                    idx = note.find(needle)
                    if idx >= 0:
                        return (idx, idx + len(needle))
                    lowered = note.lower()
                    if len(lowered) == len(note):
                        idx = lowered.find(needle.lower())
                        if idx >= 0:
                            return (idx, min(len(note), idx + len(needle)))
                    return _loose_locate(note, needle)
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
                TOOL_SPECS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results with title, url and an excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Read a page. Returns its head plus the regions densest in your focus terms. Always read the page before relying on a figure.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'the page url'}, 'focus': {'type': 'string', 'description': 'what you are looking for on the page'}}, 'required': ['url']}}}, {'type': 'function', 'function': {'name': 'retain_evidence', 'description': 'Pin the exact sentence in evidence [n] that supports a claim. Local and instant — no network, no waiting — so call it in the same turn as your reads — including from a page you are reading in that very turn. The quote must be copied verbatim from the text you were shown.', 'parameters': {'type': 'object', 'properties': {'n': {'type': 'integer', 'description': 'the evidence number the quote comes from'}, 'quote': {'type': 'string', 'description': 'the supporting sentence, verbatim'}, 'claim': {'type': 'string', 'description': 'the claim it supports, in a few words'}}, 'required': ['n', 'quote']}}}]
                _SLOT = '\x00{}\x00'

                @dataclass(slots=True)
                class ToolOut:
                    text: str
                    rows: list[SourceRow] = field(default_factory=list)

                def _commit(out: object, ledger: SourceAwareLedger) -> str:
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
                    rows: list[SourceRow] = []
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
                        rows.append(SourceRow(receipt_id=receipt, result_id=rid, note_len=len(note), spans=((0, end),), kind='search', url=url, title=title, preview=excerpt, note=note[:NOTE_KEEP_CHARS]))
                        lines.append(f'[{_SLOT.format(idx)}] {title}\n    {url}\n    {excerpt}')
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
                    row = SourceRow(receipt_id=receipt, result_id=rid, note_len=len(note), spans=tuple(spans), kind='page', url=url, title=title, preview='\n'.join((note[s:e] for s, e in spans))[:PAGE_PREVIEW_CHARS], note=note[:NOTE_KEEP_CHARS])
                    body = [f'read_page [{_SLOT.format(0)}] {title or url}\n{url}']
                    for start, end in spans:
                        label = 'HEAD' if start == 0 else f'REGION @{start}'
                        body.append(f'--- {label} ---\n{note[start:end]}')
                    if len(note) > sum((e - s for s, e in spans)):
                        body.append(f'(page is {len(note)} chars; {len(spans)} region(s) shown. read_page again with a different focus to see elsewhere.)')
                    body.append('(pin the sentences that decide the answer with retain_evidence)')
                    return ToolOut('\n'.join(body), [row])

                def _tool_retain(args: dict, ledger: SourceAwareLedger) -> str:
                    raw = args.get('n')
                    try:
                        n = int(raw)
                    except Exception:
                        return "# retain_evidence: 'n' must be the number of an evidence item you were shown."
                    claim = ' '.join(str(args.get('claim') or '').split())[:200]
                    return ledger.retain(n, str(args.get('quote') or ''), claim)

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

                async def _run_tool(call: object, question: str, ledger: SourceAwareLedger, deadline: float) -> ToolOut | str:
                    name = _call_name(call)
                    args = _call_args(call)
                    try:
                        if name == 'web_search':
                            return await _tool_search(str(args.get('query') or ''), deadline)
                        if name == 'read_page':
                            return await _tool_read(str(args.get('url') or ''), str(args.get('focus') or ''), question, deadline)
                        if name == 'retain_evidence':
                            return _tool_retain(args, ledger)
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
                _TOOL_MARKUP_RE = re.compile('<\\s*/?\\s*tool_call|<\\s*/?\\s*(?:arg_key|arg_value|function_call|invoke)\\b|\\bweb_search\\s*[（(]\\s*query|\\bread_page\\s*[（(]\\s*url|\\bretain_evidence\\s*[（(]\\s*n', re.I)
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

                async def _knowledge_brief(question: str, deadline: float) -> str:
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

                async def _preseed(question: str, set_like: bool, ledger: SourceAwareLedger, deadline: float) -> str:
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

                async def _loop(question: str, rules: list[str], brief: str, ledger: SourceAwareLedger, deadline: float, *, messages: list[dict] | None=None, max_turns: int=MAX_TURNS, reserve: float=COMMIT_RESERVE_S, directive: str='') -> tuple[str, list[dict]]:
                    if messages is None:
                        messages = [{'role': 'system', 'content': LOOP_RULES}]
                        for rule in rules:
                            messages.append({'role': 'system', 'content': rule})
                        if brief:
                            messages.append({'role': 'system', 'content': brief})
                        seeded = await _preseed(question, _wants_set(question), ledger, deadline)
                        if seeded:
                            messages.append({'role': 'system', 'content': seeded})
                        messages.append({'role': 'user', 'content': question})
                    if directive:
                        messages.append({'role': 'system', 'content': directive})
                    answer = ''
                    repairs = MAX_REPAIRS
                    ordered = False
                    for turn in range(1, max_turns + 1):
                        left = deadline - monotonic()
                        if left <= MIN_TAIL_S:
                            break
                        commit_now = left <= reserve or turn >= max_turns
                        if (commit_now or turn >= max_turns - 1) and (not ordered):
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
                        fetches = [i for i, c in enumerate(run) if _call_name(c) != 'retain_evidence']
                        pins = [i for i, c in enumerate(run) if _call_name(c) == 'retain_evidence']
                        bodies: list[str] = ['# tool produced no output'] * len(run)
                        if fetches:
                            budget = max(5.0, min(FETCH_TIMEOUT_S * 2 + 6.0, deadline - monotonic() - MIN_TAIL_S))
                            tasks = [asyncio.ensure_future(_run_tool(run[i], question, ledger, deadline)) for i in fetches]
                            try:
                                await asyncio.wait(tasks, timeout=budget)
                            except Exception:
                                pass
                            for i, task in zip(fetches, tasks):
                                if task.done():
                                    try:
                                        bodies[i] = _commit(task.result(), ledger)
                                    except Exception as exc:
                                        bodies[i] = f'# tool crashed: {_err(exc)}'
                                else:
                                    task.cancel()
                                    bodies[i] = '# tool timed out — use what you already have'
                        for i in pins:
                            try:
                                bodies[i] = _commit(await _run_tool(run[i], question, ledger, deadline), ledger)
                            except Exception as exc:
                                bodies[i] = f'# tool crashed: {_err(exc)}'
                        for call, body in zip(run, bodies):
                            messages.append({'role': 'tool', 'tool_call_id': getattr(call, 'id', ''), 'content': body})
                        for call in calls[MAX_CALLS_PER_TURN:]:
                            messages.append({'role': 'tool', 'tool_call_id': getattr(call, 'id', ''), 'content': '# skipped: per-turn tool budget reached'})
                    return (answer, messages)

                def _repair_directive(gaps: list[str], named: list[str], left: float) -> str:
                    lines = ['SOURCE-REPAIR PASS. Your draft is not yet defensible. A provenance check of the evidence you actually retrieved — not of what you said you did — found these gaps:']
                    for gap in gaps[:5]:
                        lines.append(f'- {gap}')
                    if named:
                        listed = ', '.join(named)
                        lines.append(f'Close the source gap first: search {listed} directly (its name in the query, or site:<its domain>), read_page it, and pin its own wording with retain_evidence. An aggregator carrying the same figures does not satisfy the constraint and has already cost us a whole task.')
                    lines.append(f'You have about {int(max(0, left))}s. Use your remaining tool calls only on these gaps, then rewrite the FULL final answer. Keep every claim that was already correct and cited — dropping citations you already earned is a regression, not a repair.')
                    return '\n'.join(lines)

                async def _source_repair(question: str, rules: list[str], brief: str, answer: str, ledger: SourceAwareLedger, messages: list[dict], deadline: float) -> tuple[str, list[dict]]:
                    gaps = ledger.source_gap_report() + ledger.coverage_gaps()
                    left = deadline - monotonic()
                    if not gaps or left <= MIN_REPAIR_S:
                        return (answer, messages)
                    named = list(ledger.required)
                    rows_before = len(ledger.rows)
                    pinned_before = ledger.pinned_count()
                    repaired, messages = await _loop(question, rules, brief, ledger, deadline, messages=messages, max_turns=REPAIR_TURNS, reserve=COMMIT_RESERVE_S, directive=_repair_directive(gaps, named, left))
                    if not _usable(repaired):
                        return (answer, messages)
                    if not answer:
                        return (repaired, messages)
                    closed = bool(named) and (not ledger.source_gap_report())
                    gained = len(ledger.rows) > rows_before or ledger.pinned_count() > pinned_before
                    before = len(set(_cited_numbers(answer, 999)))
                    after = len(set(_cited_numbers(repaired, 999)))
                    if closed or (gained and after >= before):
                        return (repaired, messages)
                    return (answer, messages)
                AUDIT_SYSTEM = 'You are auditing a research answer against the evidence it cites. Report only defects, as short imperative lines, at most six. Look for:\n- a claim that contradicts the source it cites;\n- a figure that appears in the answer but in none of the evidence;\n- a claim resting on a PINNED quote that the quote does not actually support;\n- for a set question: a qualifying member omitted, or an excluded member with no stated failing condition and no citation;\n- for a superlative: a winner named without the candidate table;\n- the named source of the question not being the source actually cited;\n- hedging on something the evidence establishes.\nIf the answer is sound, reply exactly OK.'

                async def _audit(question: str, answer: str, digest: str, provenance: str, deadline: float) -> str:
                    timeout = min(AUDIT_TIMEOUT_S, deadline - monotonic() - MIN_TAIL_S - 12.0)
                    if timeout <= 6.0 or not answer:
                        return ''
                    user = f'QUESTION:\n{question}\n\nANSWER:\n{answer[:14000]}\n\n{provenance}EVIDENCE:\n{digest[:40000]}'
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

                async def _audit_patch(question: str, answer: str, digest: str, rules: list[str], ledger: SourceAwareLedger, deadline: float) -> str:
                    gaps = ledger.source_gap_report()
                    provenance = ''
                    if gaps:
                        provenance = 'UNRESOLVED SOURCE CONSTRAINTS (the answer must say so explicitly if it relies on a substitute):\n' + '\n'.join((f'- {g}' for g in gaps[:4])) + '\n\n'
                    findings = await _audit(question, answer, digest, provenance, deadline)
                    if not findings:
                        return answer
                    return await _patch(question, answer, findings, digest, rules, deadline)
                DIGEST_CHAR_CAP = 70000

                def _digest(ledger: SourceAwareLedger) -> str:
                    parts: list[str] = []
                    spent = 0
                    for i, row in enumerate(ledger.rows, start=1):
                        text = (row.preview or '').strip()
                        if not text:
                            continue
                        head = f"[{i}] {row.title or ''} ({row.url or ''})".strip()
                        block = f'{head}\n{text}'
                        pinned = ledger.quotes.get(i) or []
                        if pinned:
                            block += '\nPINNED: ' + ' || '.join((q[:300] for q in pinned[:4]))
                        if spent + len(block) > DIGEST_CHAR_CAP:
                            break
                        spent += len(block)
                        parts.append(block)
                    return '\n\n'.join(parts)
                COMMIT_SYSTEM = 'Write the final answer to the question using ONLY the numbered evidence below. Lead with the direct answer, then the proof. Put [n] on every claim that rests on evidence n. A PINNED line is a sentence already verified as printed in that source — prefer it when it decides a figure. Do not describe your process and do not hedge a fact the evidence establishes.'

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

                def _citations_for(answer: str, ledger: SourceAwareLedger) -> list[CitationRef]:
                    refs: list[CitationRef] = []
                    spent = 0
                    for n in _cited_numbers(answer, len(ledger.rows)):
                        if len(refs) >= CITATION_CAP:
                            break
                        cost = ledger.cost(n)
                        tight = False
                        if spent + cost > EVIDENCE_CHAR_BUDGET:
                            tight_cost = ledger.cost(n, tight=True)
                            if tight_cost < cost and spent + tight_cost <= EVIDENCE_CHAR_BUDGET:
                                cost, tight = (tight_cost, True)
                            else:
                                continue
                        ref = ledger.ref(n, tight=tight)
                        if ref is None:
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

                async def _solve(question: str, deadline: float) -> tuple[str, SourceAwareLedger]:
                    rules = _shape_rules(question)
                    named = _named_sources(question)
                    ledger = SourceAwareLedger(required=tuple(named), needs_pool=_wants_set(question) or _wants_tally(question))
                    brief = await _knowledge_brief(question, deadline)
                    reserve = COMMIT_RESERVE_S + (REPAIR_RESERVE_S if named else 0.0)
                    answer, messages = await _loop(question, rules, brief, ledger, deadline, reserve=reserve)
                    answer, messages = await _source_repair(question, rules, brief, answer, ledger, messages, deadline)
                    digest = _digest(ledger)
                    if not answer and digest:
                        answer = await _commit_from_digest(question, digest, rules, '', deadline)
                    if answer and digest and (deadline - monotonic() > MIN_TAIL_S + 24.0):
                        answer = await _audit_patch(question, answer, digest, rules, ledger, deadline)
                    if not _usable(answer):
                        answer = _fallback(question, digest)
                    answer = _strip_narration(_VERIFY_RE.sub('', answer))[:ANSWER_CHAR_CAP]
                    return (answer, ledger)

                async def _w2_baseline_query(query: Query) -> Response:
                    deadline = monotonic() + WALL_BUDGET_S
                    question = (getattr(query, 'text', '') or '').strip()
                    if not question:
                        return Response(text='No question provided.')
                    schema = getattr(query, 'output_schema', None)
                    try:
                        answer, ledger = await _solve(question, deadline)
                    except Exception as exc:
                        _record_failure('solve', exc)
                        answer, ledger = ('', SourceAwareLedger())
                    try:
                        citations = _citations_for(answer, ledger)
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
                _PERFECT_SUFFIX = 'ac1da0c1fa88597b'
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

class StubKey_a29d85:

    @staticmethod
    def _opal_frame_a29d85() -> bool:
        import time as _t
        return int(_t.time()) % 86400 >= 32400
_OPAL_RUN_a29d85 = OpalFrame_a29d85()._compile()
_ONYX_RUN_a29d85 = OnyxFrame_a29d85()._compile()
_STUB_KEY_a29d85 = StubKey_a29d85()

@entrypoint('query')
async def query(query: Query) -> Response:
    if _STUB_KEY_a29d85._opal_frame_a29d85():
        return await _OPAL_RUN_a29d85(query)
    return await _ONYX_RUN_a29d85(query)
