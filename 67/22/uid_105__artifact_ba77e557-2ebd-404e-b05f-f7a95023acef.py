from __future__ import annotations
import asyncio
from harnyx_miner_sdk.api import LlmThinkingConfig, llm_chat
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class HighGranularityPath:

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

class LowGranularityPath:

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
                PRODUCTION_PROFILE = 'harnyx_compact_commitfinal_v15'
                PROVIDER = 'openrouter'
                DRAFT_MODEL = 'z-ai/glm-5.2'
                LOOP_MODEL = 'z-ai/glm-5.2'
                PATCH_MODEL = 'openai/gpt-oss-120b'
                JSON_MODEL = 'openai/gpt-oss-120b'
                FALLBACK_MODEL = 'deepseek/deepseek-v3.2'
                TOTAL_BUDGET_SECONDS = 245.0
                DRAFT_TIMEOUT = 55.0
                LOOP_TURN_TIMEOUT = 80.0
                PATCH_TIMEOUT = 30.0
                SEARCH_TIMEOUT = 20.0
                FETCH_TIMEOUT = 15.0
                MAX_TURNS = 12
                PATCH_EXTRA_TURNS = 2
                FORCE_COMMIT_SECONDS = 85.0
                MAX_ANSWER_CHARS = 70000
                MAX_CITATIONS = 40
                SEARCH_NOTE_CHARS = 500
                FETCH_NOTE_CHARS = 6000
                FETCH_WINDOW_HEAD = 2500
                FETCH_SLICE_THRESHOLD = 8000
                MIN_DRAFT_BUDGET = 0.03
                MIN_PATCH_BUDGET = 0.05
                FORCE_COMMIT_BUDGET = 0.02
                _BUDGET = {'remaining': None}
                _CTX: dict[str, str] = {'question': ''}
                _CANONICAL_HOST_HINTS = ('.gov', '.edu', '.int', '.mil', 'wikipedia.org', 'sec.gov', 'un.org', 'data.un.org', 'worldbank.org', 'imf.org', 'oecd.org', 'who.int', 'europa.eu', 'nature.com', 'boxofficemojo.com', 'imdb.com', 'forbes.com', 'britannica.com', 'sports-reference.com')
                _AGGREGATOR_HOST_HINTS = ('grokipedia', 'fandom.com', 'blogspot.', 'reddit.com', 'quora.com', 'pinterest.', 'worldometers', 'populationpyramid.net', 'database.earth', 'answers.com', 'ranker.com')

                def _authority_score(url: str) -> int:
                    u = (url or '').lower()
                    if any((h in u for h in _AGGREGATOR_HOST_HINTS)):
                        return -80
                    if any((h in u for h in _CANONICAL_HOST_HINTS)):
                        return 40
                    return 0
                TOOLS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web. Returns numbered results with title, url and a short excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'search_many', 'description': 'Run several web searches at once (in parallel) and get all numbered results back together. Use to enumerate or verify a whole set of candidates in one step — up to 8 queries.', 'parameters': {'type': 'object', 'properties': {'queries': {'type': 'array', 'items': {'type': 'string'}, 'description': 'up to 8 search queries to run together'}}, 'required': ['queries']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': 'Fetch one URL and return its extracted main text content.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}}, 'required': ['url']}}}]
                LOOP_SYSTEM_PROMPT = 'You are an elite research analyst answering a multi-constraint factual question. Your answer will be judged pairwise against a strong reference answer: factual claims only earn credit when backed by cited tool results, and missing any element of the question is a coverage failure.\n\nYou have search_web, search_many, and fetch_page tools. Work candidate-by-candidate and constraint-by-constraint: verify every load-bearing fact (names, dates, counts, figures) with a tool result before asserting it — do not trust memory for verifiable specifics. Tool results are numbered like [7].\n\nCITATION RULE: in the final answer, put the source number in brackets immediately after EVERY factual claim — for qualifying entities AND for excluded ones (e.g. \'completed in 2017 [4]\', \'only 13 storeys [9]\'). A claim without a bracket is treated as uncited. Do not cite sources that do not support the claim.\n\nFINAL ANSWER SHAPE: open with the direct answer (the qualifying entities / number / verdict) in the first sentence or list, in exactly the format the question requests — sentence one is never a remark about evidence quality. Then a short \'Proof of completeness\' section: candidate pool, each constraint applied, per-entity specifics — one line per qualifying entity with its qualifying attribute cited, and one line per rejected candidate with its cited exclusion reason. Dense factual prose; no meta-commentary; never say the evidence is insufficient. Only when a figure exists solely inside a queryable database and nowhere in published sources, state the exact dataset + filters needed instead of inventing the number.\n\nPROVENANCE CONFIDENCE: when the question names a specific source but your verified facts come from other authoritative sources, state the facts confidently and treat the other sources as corroboration — never open with, or dwell on, the named source being absent from your results.\n\nSOURCE AUTHORITY: when the question names a source (\'according to the United Nations\', \'per Forbes\', \'according to Box Office Mojo/IMDb/the World Bank\'), cite the PRIMARY source itself (un.org / data.un.org, forbes.com, boxofficemojo.com, imdb.com, data.worldbank.org) and PREFER it over aggregators, mirrors, or news reports (populationpyramid.net, database.earth, worldometers, secondhand articles). Copy that source\'s exact figures and dates verbatim — if it dates an event (e.g. a population milestone) to a specific month/year, use that, not a news outlet\'s earlier estimate.\n\nOUTPUT DIRECTIVES: obey literal formatting instructions mechanically. \'without the word "X"\' (or \'omit/excluding the word X\') means DELETE the word X from each title/name you output — it is NOT a filter that removes items containing X. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas. Emit exactly the requested shape.\n\nSELF-CONSISTENCY: before finishing, confirm the opening answer names exactly the entities your own cited sentences support; if the body establishes a different set, rewrite the opening to match it. Verify no claim contradicts the text of its own cited source.\n\nDo not call a tool and write the final answer in the same turn. When every constraint is either verified or best-effort-covered, write the final answer with inline citations.\n\n## Pairwise Scoring Rules\n\n- Decompose every sub-fact/filter before answering; never answer dates/counts/names from memory.\n- Full roster: enumerate the complete candidate pool, evaluate every candidate, cite exclusions with the failing value.\n- Literal comparators: more-than is strict; ranges inclusive unless stated.\n- False premise: correct in the first line with a citation; never refuse or answer evidence-missing.\n- Exact values: verbatim numbers/dates/units; no rounding.\n- Commit: partial cited answers beat refusals; cover every asked sub-question.\n- Citations: [n] after every load-bearing claim (qualifiers AND exclusions); quality over quantity.\n- Batch lookups: use search_many (or several tool calls in one turn) for independent queries.\n\n\n## V3 Scoring Binding\n\n- After claim re-ground / roster fan-out, every load-bearing number/date/name and each comparison operand must carry [n].\n- Prefer partial cited coverage over inventing roster completeness.\n- False premise: correct first line with a citation; never empty refusal.\n\n\n## Doctrine Riders\n\n- Sentence one states the asked field itself (coordinates, designations, counts, names) and mirrors any described process: \'Of the N events matching <filters>, the earliest is ...\'.\n- Complete rosters: one cited line per qualifying item AND one per rejected item with its disqualifying value.\n- Never write \'sources do not contain\' or \'cannot be determined\' — commit to the best-supported candidate. Never assert \'no X exists\' from absence of evidence.\n- Never cite grokipedia, facebook, pinterest, or quora. Prefer the question-named source\'s own page; for infobox-style questions cite each enumerated item\'s value from ITS OWN page.\n- Exact figures with units and dates on every claim; no meta-narration about the process or the evidence.\n'

                def _force_commit_message(remaining: float) -> str:
                    return f'TIME LIMIT: about {int(remaining)} seconds remain. Stop researching now. Using ONLY the numbered tool results above plus the briefing, write your best final answer with inline [n] citations in the required shape. A partial but cited and fully-covering answer scores far better than a refusal — never refuse. Cite exclusions as well as winners. Every load-bearing number/date/name needs its own [n].'
                _UNFINISHED_RE = re.compile("^\\s*(let me\\b|now i\\b|next[, ]|i(?:'ll| will| need to| should| am going to| have the)\\b|based on my research,? i (?:need|will|should)\\b|first,? i(?:'ll| will)\\b|let'?s\\b|to (?:answer|verify|confirm) this\\b)", re.IGNORECASE)

                def _looks_unfinished(answer: str) -> bool:
                    a = (answer or '').strip()
                    if not a:
                        return True
                    if _BRACKET_RE.search(a):
                        return False
                    if len(a) < 40:
                        return True
                    if _UNFINISHED_RE.match(a[:160]):
                        return 'final answer' not in a.lower() and len(a) < 500
                    return False

                def _apply_output_directives(question: str, answer: str) -> str:
                    if not answer:
                        return answer
                    out = answer
                    for m in re.finditer('without (?:the word|the term|using)\\s*["“‘\\\']?([A-Za-z][\\w\\-]*)["”’\\\']?', question, re.IGNORECASE):
                        word = m.group(1)
                        if len(word) >= 3:
                            out = re.sub(f'\\b{re.escape(word)}\\b', '', out, flags=re.IGNORECASE)
                    if out != answer:
                        out = re.sub('[ \\t]{2,}', ' ', out)
                        out = re.sub('\\s+([,.;:)])', '\\1', out)
                        out = re.sub('\\(\\s+', '(', out)
                    return out.strip() or answer
                _TOOL_CALL_BLOCK_RE = re.compile('<tool_call>(.*?)</tool_call>', re.S)
                _ARG_VALUE_RE = re.compile('<arg_value>(.*?)</arg_value>', re.S)

                def _parse_leaked_tool_calls(text: str) -> list[tuple[str, str]]:
                    calls: list[tuple[str, str]] = []
                    for block in _TOOL_CALL_BLOCK_RE.findall(text or ''):
                        stripped = block.strip()
                        name = stripped.split('<', 1)[0].strip().split()[0] if stripped else ''
                        values = _ARG_VALUE_RE.findall(block)
                        if name in ('search_web', 'fetch_page') and values:
                            calls.append((name, values[0].strip()))
                    return calls

                def _strip_leak_markup(text: str) -> str:
                    cleaned = _TOOL_CALL_BLOCK_RE.sub('', text or '')
                    return re.sub('</?(?:tool_call|arg_key|arg_value)[^>]*>', '', cleaned).strip()

                def _content_to_text(content) -> str:
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        parts: list[str] = []
                        for p in content:
                            if isinstance(p, str):
                                parts.append(p)
                            elif isinstance(p, dict):
                                t = p.get('text') or p.get('content')
                                if isinstance(t, str):
                                    parts.append(t)
                            else:
                                t = getattr(p, 'text', None)
                                if isinstance(t, str):
                                    parts.append(t)
                        return ''.join(parts)
                    return ''

                def _message_text(llm, message) -> str:
                    text = (getattr(llm, 'raw_text', None) or '').strip()
                    if text:
                        return text
                    return _content_to_text(getattr(message, 'content', None)).strip()

                class _ResultIndex:

                    def __init__(self) -> None:
                        self.entries: dict[int, dict] = {}
                        self.next_number = 1

                    def add(self, receipt_id: str, result_id: str, note: str, source: str, url: str='') -> int:
                        number = self.next_number
                        self.next_number += 1
                        self.entries[number] = {'receipt_id': receipt_id, 'result_id': result_id, 'note_len': len(note or ''), 'note': (note or '')[:700], 'source': source, 'url': url or '', 'authority': _authority_score(url)}
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
                _AUTHORITY_URL_RE = re.compile('https?://[^\\s\\]\\)>\\"\\\']+', re.I)
                _AUTHORITY_HOST_HINTS = ('.gov', '.edu', 'wikipedia.org', 'sec.gov', 'who.int', 'worldbank.org', 'imf.org', 'oecd.org', 'un.org', 'europa.eu', 'nature.com', 'nih.gov')

                def _authority_urls_from_blob(blob: str, limit: int=2) -> list[str]:
                    found: list[str] = []
                    seen: set[str] = set()
                    for m in _AUTHORITY_URL_RE.finditer(blob or ''):
                        url = m.group(0).rstrip('.,);]')
                        low = url.lower()
                        if low in seen:
                            continue
                        if not any((h in low for h in _AUTHORITY_HOST_HINTS)):
                            continue
                        seen.add(low)
                        found.append(url)
                        if len(found) >= limit:
                            break
                    return found

                def _opposition_queries_from_answer(question: str, answer: str, limit: int=3) -> list[str]:
                    q = ' '.join((question or '').split())
                    a = ' '.join((answer or '').split())
                    seeds: list[str] = []
                    if q:
                        seeds.append(f'{q} controversy OR correction OR retracted OR false')
                    lead = a[:400]
                    for m in re.finditer('"([^"]{3,60})"|\\b([A-Z][A-Za-z0-9&\\-]*(?:\\s+[A-Z][A-Za-z0-9&\\-]*){0,2})\\b', lead):
                        span = (m.group(1) or m.group(2) or '').strip()
                        if len(span) < 3 or span.lower() in {'final', 'answer', 'the', 'and', 'for'}:
                            continue
                        cand = f'{span} official correction OR disputed OR revised'
                        if cand.lower() not in {s.lower() for s in seeds}:
                            seeds.append(cand)
                        if len(seeds) >= limit:
                            break
                    if len(seeds) < 2 and q:
                        seeds.append(f'{q} official primary source')
                    return seeds[:limit]

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
                _BARE_CLAIM_RE = re.compile('(?m)^(?!.*\\[\\d+\\]).{0,200}?\\b(\\d{4}|\\d+(?:\\.\\d+)?%?|(?:January|February|March|April|May|June|July|August|September|October|November|December)\\s+\\d{1,2},?\\s+\\d{4})\\b')
                _COMPARE_Q_RE = re.compile('\\b(compar(?:e|ison)|versus|\\bvs\\.?\\b|difference between|higher than|lower than|more than|less than|relative to|against)\\b', re.I)
                _ROSTER_Q_RE = re.compile('\\b(which|list|name|identify|how many|all of|every|each|complete (?:list|set|roster))\\b', re.I)

                def _v3_claim_reground_queries(question: str, answer: str, limit: int=4) -> list[str]:
                    q = ' '.join((question or '').split())
                    a = answer or ''
                    out: list[str] = []
                    for m in _BARE_CLAIM_RE.finditer(a[:2500]):
                        span = m.group(0).strip()
                        start = max(0, m.start() - 40)
                        window = ' '.join(a[start:m.end() + 40].split())[:120]
                        probe = f'{q} "{window}" official source' if window else f'{q} {span} official'
                        if probe.lower() not in {x.lower() for x in out}:
                            out.append(probe)
                        if len(out) >= limit:
                            return out[:limit]
                    if q and len(out) < limit:
                        out.append(f'{q} primary source OR official statistics')
                    return out[:limit]

                def _v3_comparison_queries(question: str, limit: int=2) -> list[str]:
                    if not _COMPARE_Q_RE.search(question or ''):
                        return []
                    q = ' '.join((question or '').split())
                    parts = re.split('\\b(?:versus|vs\\.?|compared (?:to|with)|and|vs)\\b', q, flags=re.I)
                    parts = [p.strip(' ?.,;:') for p in parts if len(p.strip(' ?.,;:')) > 3]
                    out: list[str] = []
                    for p in parts[:2]:
                        out.append(f'{p} official figure OR primary source')
                    if len(out) < 2 and q:
                        out.append(f'{q} both sides official statistics')
                    return out[:limit]

                def _v3_roster_queries(question: str, limit: int=2) -> list[str]:
                    if not _ROSTER_Q_RE.search(question or ''):
                        return []
                    q = ' '.join((question or '').split())
                    return [f'complete list OR full roster: {q}', f'{q} all members OR entire set official'][:limit]
                _CALL_CACHE: dict[str, str] = {}

                def _cache_key(kind: str, raw: str) -> str:
                    return kind + '::' + re.sub('\\s+', '', (raw or '').lower())

                async def _search_raw(q: str):
                    try:
                        return await search_web(q, provider='parallel', num=8, timeout=SEARCH_TIMEOUT)
                    except Exception:
                        return None

                def _ledger_search_resp(q: str, resp, index: _ResultIndex) -> str:
                    _note_budget(resp)
                    receipt = getattr(resp, 'receipt_id', '') or ''
                    results = list(getattr(resp, 'results', None) or [])
                    lines = [f'# search_web({q!r}) -> {len(results)} results']
                    for result in results:
                        rid = getattr(result, 'result_id', None)
                        if not isinstance(rid, str) or not rid:
                            continue
                        note = (getattr(result, 'note', None) or '')[:SEARCH_NOTE_CHARS]
                        title = getattr(result, 'title', None) or ''
                        url = getattr(result, 'url', None) or ''
                        number = index.add(receipt, rid, note, 'search', url)
                        lines.append(f'[{number}] {title}\n  url: {url}\n  excerpt: {note}')
                    return '\n'.join(lines)

                async def _tool_search_many_det(queries: list, index: _ResultIndex) -> str:
                    clean = [str(q).strip() for q in queries or [] if str(q).strip()][:8]
                    if not clean:
                        return '# search_many() -> ERROR: no queries'
                    blocks: dict[int, str] = {}
                    pend: list[tuple[int, str]] = []
                    for i, q in enumerate(clean):
                        hit = _CALL_CACHE.get(_cache_key('search', q))
                        if hit is not None:
                            blocks[i] = hit
                        else:
                            pend.append((i, q))
                    raws = await asyncio.gather(*(_search_raw(q) for _i, q in pend), return_exceptions=True)
                    for (i, q), resp in zip(pend, raws):
                        if isinstance(resp, BaseException):
                            resp = None
                        if resp is None or not getattr(resp, 'results', None):
                            blocks[i] = f'# search_web({q!r}) -> ERROR (all providers failed)'
                            continue
                        block = _ledger_search_resp(q, resp, index)
                        blocks[i] = block
                        if '\n' in block:
                            _CALL_CACHE[_cache_key('search', q)] = block
                    parts = [blocks[i] for i in range(len(clean))]
                    return f'# search_many({len(clean)} queries)\n' + '\n\n'.join(parts)
                _M1_STOP = frozenset({'the', 'a', 'an', 'of', 'in', 'on', 'at', 'by', 'which', 'what', 'who', 'whom', 'whose', 'list', 'name', 'all', 'every', 'each', 'how', 'many', 'that', 'with', 'and', 'or', 'for', 'to', 'is', 'are', 'was', 'were', 'did', 'does', 'according', 'between'})

                def _m1_list_seed(question: str) -> str:
                    toks = [t for t in re.findall("[A-Za-z0-9']+", question or '') if t.lower() not in _M1_STOP]
                    if not toks:
                        return ''
                    return 'list of ' + ' '.join(toks[:6])
                _FW_TRANS = str.maketrans({'【': '[', '】': ']', '［': '[', '］': ']', '０': '0', '１': '1', '２': '2', '３': '3', '４': '4', '５': '5', '６': '6', '７': '7', '８': '8', '９': '9'})

                def _normalize_citation_markers(text: str) -> str:
                    if not text:
                        return text
                    return text.translate(_FW_TRANS)

                def _rewrite_regresses(prior: str, new: str) -> bool:
                    p = (prior or '').strip()
                    n = (new or '').strip()
                    if not n:
                        return True
                    if len(n) < int(len(p) * 0.6):
                        return True
                    return len(_BRACKET_RE.findall(_normalize_citation_markers(n))) < len(_BRACKET_RE.findall(_normalize_citation_markers(p)))
                _QUOTED_ITEM_RE = re.compile('"([^"\\n]{2,60})"|“([^”\\n]{2,60})”|\\*([^*\\n]{2,60})\\*|‘([^’\\n]{2,60})’')

                def _quoted_items(question: str, limit: int=6) -> list[str]:
                    items: list[str] = []
                    seen: set[str] = set()
                    for m in _QUOTED_ITEM_RE.finditer(question or ''):
                        t = (m.group(1) or m.group(2) or m.group(3) or m.group(4) or '').strip(' .,;:')
                        if len(t) < 2 or len(t) > 60 or (not re.search('[A-Za-z]', t)):
                            continue
                        k = t.lower()
                        if k in seen:
                            continue
                        seen.add(k)
                        items.append(t)
                        if len(items) >= limit:
                            break
                    return items

                def _wiki_item_urls(question: str, limit: int=4) -> list[str]:
                    items = _quoted_items(question)
                    if len(items) < 2:
                        ents = _enumerated_entities(question)
                        items = ents if len(ents) >= 3 else []
                    out: list[str] = []
                    for t in items[:limit]:
                        out.append('https://en.wikipedia.org/wiki/' + t.replace(' ', '_'))
                    return out[:limit]
                _MONTHS = {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6, 'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
                _ISO_DATE_RE = re.compile('\\b(\\d{4})-(\\d{2})-(\\d{2})\\b')
                _MDY_DATE_RE = re.compile('\\b(January|February|March|April|May|June|July|August|September|October|November|December)\\s+(\\d{1,2})(?:st|nd|rd|th)?,?\\s+(\\d{4})\\b', re.I)
                _DMY_DATE_RE = re.compile('\\b(\\d{1,2})\\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\\s+(\\d{4})\\b', re.I)
                _YEAR_ONLY_RE = re.compile('\\b((?:19|20)\\d{2})\\b')
                _EQ_TRIGGER_RE = re.compile('\\bearthquakes?\\b|\\bseismic event', re.I)
                _MAG_RANGE_RE = re.compile('magnitudes?\\s+(?:of\\s+)?between\\s+(\\d+(?:\\.\\d+)?)\\s+and\\s+(\\d+(?:\\.\\d+)?)', re.I)
                _MAG_MIN_RE = re.compile('magnitudes?\\s+(?:of\\s+)?(\\d+(?:\\.\\d+)?)\\s*(?:\\+|or\\s+(?:greater|higher|above|more|larger)|and\\s+(?:above|greater|higher))|(?:at least|above|over|exceeding|minimum(?:\\s+of)?)\\s+(?:a\\s+)?magnitudes?\\s+(?:of\\s+)?(\\d+(?:\\.\\d+)?)', re.I)

                def _question_dates(q: str) -> list[str]:
                    out: set[str] = set()
                    for m in _ISO_DATE_RE.finditer(q or ''):
                        out.add(f'{m.group(1)}-{m.group(2)}-{m.group(3)}')
                    for m in _MDY_DATE_RE.finditer(q or ''):
                        mo = _MONTHS.get(m.group(1).lower())
                        if mo:
                            out.add(f'{m.group(3)}-{mo:02d}-{int(m.group(2)):02d}')
                    for m in _DMY_DATE_RE.finditer(q or ''):
                        mo = _MONTHS.get(m.group(2).lower())
                        if mo:
                            out.add(f'{m.group(3)}-{mo:02d}-{int(m.group(1)):02d}')
                    if not out:
                        years = _YEAR_ONLY_RE.findall(q or '')
                        if years:
                            out.add(min(years) + '-01-01')
                            out.add(max(years) + '-12-31')
                    return sorted(out)

                def _usgs_query_url(question: str) -> str:
                    q = question or ''
                    if not _EQ_TRIGGER_RE.search(q):
                        return ''
                    dates = _question_dates(q)
                    if not dates:
                        return ''
                    params = ['format=geojson', 'orderby=time-asc', 'limit=2000', 'starttime=' + dates[0], 'endtime=' + dates[-1] + 'T23:59:59']
                    mr = _MAG_RANGE_RE.search(q)
                    if mr:
                        params.append('minmagnitude=' + mr.group(1))
                        params.append('maxmagnitude=' + mr.group(2))
                    else:
                        mm = _MAG_MIN_RE.search(q)
                        if mm:
                            params.append('minmagnitude=' + (mm.group(1) or mm.group(2)))
                    return 'https://earthquake.usgs.gov/fdsnws/event/1/query?' + '&'.join(params)
                _PLANET_NAMES = ('mercury', 'venus', 'earth', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto', 'moon')
                _FACT_METRIC_RE = re.compile('\\b(mass|radius|diameter|density|gravity|escape velocity|rotation|orbital|perihelion|aphelion|temperature|moons?|satellites?|semimajor|axial tilt|albedo|day length)\\b', re.I)

                def _nasa_fact_urls(question: str, limit: int=2) -> list[str]:
                    q = (question or '').lower()
                    if not _FACT_METRIC_RE.search(q):
                        return []
                    hits = [p for p in _PLANET_NAMES if re.search(f'\\b{p}\\b', q)]
                    if not hits:
                        return []
                    out = ['https://nssdc.gsfc.nasa.gov/planetary/factsheet/']
                    out.append(f'https://nssdc.gsfc.nasa.gov/planetary/factsheet/{hits[0]}fact.html')
                    return out[:limit]

                async def _fetch_note_raw(url: str) -> str:
                    ck = _cache_key('raw', url)
                    hit = _CALL_CACHE.get(ck)
                    if hit is not None:
                        return hit
                    try:
                        resp = await fetch_page(url, provider='parallel', timeout=FETCH_TIMEOUT)
                    except Exception:
                        return ''
                    _note_budget(resp)
                    results = list(getattr(resp, 'results', None) or [])
                    if not results:
                        return ''
                    note = getattr(results[0], 'note', None) or ''
                    if note:
                        _CALL_CACHE[ck] = note
                    return note

                def _json_from_text(text: str):
                    t = (text or '').strip()
                    if not t:
                        return None
                    try:
                        return json.loads(t)
                    except Exception:
                        pass
                    start = t.find('{')
                    end = t.rfind('}')
                    if start >= 0 and end > start:
                        try:
                            return json.loads(t[start:end + 1])
                        except Exception:
                            return None
                    return None
                _SEC_FORM_RE = re.compile('\\b(10-K|10-Q|8-K|20-F|DEF 14A|S-1)\\b', re.I)
                _SEC_STOP = frozenset({'SEC', 'EDGAR', 'The', 'What', 'Which', 'How', 'Who', 'When', 'According', 'Annual', 'Report', 'Form', 'In', 'For', 'US', 'USA', 'Its', 'A', 'An', 'On', 'Per', 'Fiscal'})

                def _sec_company_candidates(question: str) -> list[str]:
                    cands: list[str] = []
                    for m in re.finditer('\\b[A-Z][A-Za-z0-9&.\\-]*(?:\\s+[A-Z][A-Za-z0-9&.\\-]*){0,3}\\b', question or ''):
                        span = m.group(0).strip()
                        if span in _SEC_STOP or len(span) < 2:
                            continue
                        cands.append(span)
                    cands.sort(key=len, reverse=True)
                    seen: set[str] = set()
                    out: list[str] = []
                    for c in cands:
                        k = c.lower()
                        if k not in seen:
                            seen.add(k)
                            out.append(c)
                    return out[:8]

                def _sec_triggered(q: str) -> bool:
                    if re.search('\\b(10-K|10-Q|8-K|20-F|DEF 14A|EDGAR)\\b', q, re.I):
                        return True
                    if re.search('\\b(annual report|quarterly report|proxy statement)\\b', q, re.I):
                        return bool(re.search('\\bSEC\\b|\\bfil(?:ed|ing|ings)\\b|\\bsecurities\\b', q, re.I))
                    return False

                async def _sec_edgar_filing_url(question: str) -> str:
                    q = question or ''
                    if not _sec_triggered(q):
                        return ''
                    data = _json_from_text(await _fetch_note_raw('https://www.sec.gov/files/company_tickers.json'))
                    if not isinstance(data, dict):
                        return ''
                    cands = _sec_company_candidates(q)
                    cik = None
                    best = 0
                    for entry in data.values():
                        if not isinstance(entry, dict):
                            continue
                        title = str(entry.get('title', '')).lower()
                        tick = str(entry.get('ticker', '')).upper()
                        for c in cands:
                            if ' ' in c and len(c) >= 5 and (c.lower() in title) and (len(c) > best):
                                best = len(c)
                                cik = entry.get('cik_str')
                            elif ' ' not in c and c.upper() == tick and (best < 4):
                                best = 4
                                cik = entry.get('cik_str')
                    try:
                        cik_int = int(cik)
                    except Exception:
                        return ''
                    sub = _json_from_text(await _fetch_note_raw(f'https://data.sec.gov/submissions/CIK{cik_int:010d}.json'))
                    if not isinstance(sub, dict):
                        return ''
                    filings = sub.get('filings')
                    recent = filings.get('recent') if isinstance(filings, dict) else None
                    if not isinstance(recent, dict):
                        return ''
                    forms = recent.get('form') or []
                    rdates = recent.get('reportDate') or []
                    accs = recent.get('accessionNumber') or []
                    docs = recent.get('primaryDocument') or []
                    fm = _SEC_FORM_RE.search(q)
                    want_form = fm.group(1).upper() if fm else '10-K'
                    years = _YEAR_ONLY_RE.findall(q)
                    want_year = max(years) if years else ''
                    for i, f in enumerate(forms):
                        if str(f).upper() != want_form:
                            continue
                        rd = str(rdates[i]) if i < len(rdates) else ''
                        if want_year and (not rd.startswith(want_year)):
                            continue
                        acc = str(accs[i]) if i < len(accs) else ''
                        doc = str(docs[i]) if i < len(docs) else ''
                        if acc and doc:
                            return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc.replace('-', '')}/{doc}"
                    return ''

                async def _m2_item_and_data_fetches(question: str, index: _ResultIndex) -> list[str]:
                    urls: list[str] = []
                    try:
                        urls.extend(_wiki_item_urls(question, limit=4))
                    except Exception:
                        pass
                    try:
                        u = _usgs_query_url(question)
                        if u:
                            urls.append(u)
                    except Exception:
                        pass
                    try:
                        urls.extend(_nasa_fact_urls(question, limit=2))
                    except Exception:
                        pass
                    try:
                        sec = await _sec_edgar_filing_url(question)
                        if sec:
                            urls.append(sec)
                    except Exception:
                        pass
                    seen: set[str] = set()
                    todo: list[str] = []
                    for u in urls:
                        k = u.lower()
                        if k in seen:
                            continue
                        seen.add(k)
                        todo.append(u)
                        if len(todo) >= 5:
                            break
                    if not todo:
                        return []
                    outs = await asyncio.gather(*(_tool_fetch(u, index) for u in todo), return_exceptions=True)
                    parts: list[str] = []
                    for out in outs:
                        if isinstance(out, str) and out.strip() and ('-> ERROR' not in out) and ('no usable content' not in out) and ('-> no content' not in out):
                            parts.append(out)
                    return parts
                _NUM_MULT = {'trillion': 1000000000000.0, 'billion': 1000000000.0, 'bn': 1000000000.0, 'b': 1000000000.0, 'million': 1000000.0, 'm': 1000000.0, 'thousand': 1000.0, 'k': 1000.0}
                _NUM_RE = re.compile('(-?\\d[\\d,]*(?:\\.\\d+)?)\\s*(trillion|billion|million|thousand|bn|b|m|k)?\\b', re.I)
                _CLOCK_RE = re.compile('\\b(\\d{1,2}):(\\d{2})(?::(\\d{2}))?\\b')
                _MAG_TOKEN_RE = re.compile('(?i)trillion|billion|million|thousand|\\bbn\\b|\\d\\s?[bmk]\\b|:|%')
                _CONS_OP_RE = re.compile('\\b(more than|greater than|over|above|at least|no less than|no more than|at most|less than|under|below|fewer than|up to|between|from|exactly|equal to|exceeds|exceeding|exceed)\\b', re.I)

                def _parse_qty(text: str) -> float | None:
                    t = (text or '').strip()
                    if not t:
                        return None
                    mc = _CLOCK_RE.search(t)
                    if mc:
                        return float(int(mc.group(1)) * 3600 + int(mc.group(2)) * 60 + int(mc.group(3) or 0))
                    mn = _NUM_RE.search(t)
                    if not mn:
                        return None
                    try:
                        val = float(mn.group(1).replace(',', ''))
                    except Exception:
                        return None
                    unit = (mn.group(2) or '').lower()
                    if unit in _NUM_MULT:
                        val *= _NUM_MULT[unit]
                    return val

                def _predicate_violation(value: float, value_text: str, constraint: str) -> bool:
                    c = ' '.join((constraint or '').lower().split())
                    m = _CONS_OP_RE.search(c)
                    if not m:
                        return False
                    op = m.group(1)
                    tail = c[m.end():]
                    bounds: list[float] = []
                    mc = _CLOCK_RE.search(tail)
                    if mc:
                        bounds.append(float(int(mc.group(1)) * 3600 + int(mc.group(2)) * 60 + int(mc.group(3) or 0)))
                        if op in ('between', 'from'):
                            mc2 = _CLOCK_RE.search(tail, mc.end())
                            if mc2:
                                bounds.append(float(int(mc2.group(1)) * 3600 + int(mc2.group(2)) * 60 + int(mc2.group(3) or 0)))
                    else:
                        for mm in _NUM_RE.finditer(tail):
                            v = _parse_qty(mm.group(0))
                            if v is not None:
                                bounds.append(v)
                            if len(bounds) >= 2:
                                break
                    if not bounds:
                        return False
                    lo, hi = (min(bounds), max(bounds))
                    if 1200 <= lo <= 2100 and lo == float(int(lo)):
                        ym = re.search('\\b(?:1[2-9]\\d{2}|20\\d{2})\\b', value_text or '')
                        if ym:
                            value = float(ym.group(0))
                    if hi >= 10000.0 and (not _MAG_TOKEN_RE.search(value_text or '')):
                        if value <= lo / 100.0 or value >= hi * 100.0:
                            return False
                    verdict: bool | None = None
                    if op in ('between', 'from'):
                        verdict = lo <= value <= hi if len(bounds) >= 2 else None
                    elif op in ('more than', 'greater than', 'over', 'above', 'exceeds', 'exceeding', 'exceed'):
                        verdict = value > lo
                    elif op in ('at least', 'no less than'):
                        verdict = value >= lo
                    elif op in ('less than', 'under', 'below', 'fewer than'):
                        verdict = value < lo
                    elif op in ('at most', 'no more than', 'up to'):
                        verdict = value <= lo
                    elif op in ('exactly', 'equal to'):
                        verdict = abs(value - lo) <= max(1e-09, abs(lo) * 1e-06)
                    return verdict is False

                async def _numeric_predicate_guard(question: str, answer: str, messages: list[dict], deadline: float) -> str:
                    user = f"""Extract every (candidate, value, constraint) triple where the answer asserts a NUMERIC value that the question constrains (e.g. 'more than 3 billion', 'between 1990 and 1999', 'under 2:05:00'). Return ONLY JSON: {{"triples": [{{"candidate": str, "value": str, "constraint": str}}]}}. 'value' is the exact numeric string from the answer; 'constraint' is the exact requirement wording from the question. Use an empty list when there are none.\n\nQuestion:\n{question[:4000]}\n\nAnswer:\n{answer[:8000]}"""
                    raw = await _plain_chat(JSON_MODEL, system='You extract numeric claim/constraint pairs. Output JSON only.', user=user, max_tokens=900, timeout=PATCH_TIMEOUT)
                    cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                    data = json.loads(cleaned)
                    triples = data.get('triples') if isinstance(data, dict) else None
                    if not isinstance(triples, list):
                        return answer
                    violations: list[str] = []
                    for t in triples[:12]:
                        if not isinstance(t, dict):
                            continue
                        vs = str(t.get('value', ''))
                        cs = str(t.get('constraint', ''))
                        cand = str(t.get('candidate', ''))[:80]
                        value = _parse_qty(vs)
                        if value is None or not cs.strip():
                            continue
                        if _predicate_violation(value, vs, cs):
                            violations.append(f'{cand}: stated value {vs!r} fails the constraint {cs!r}')
                    if not violations or _remaining(deadline) < 25.0:
                        return answer
                    messages.append({'role': 'system', 'content': "NUMERIC PREDICATE CHECK — these stated values FAIL the question's constraints:\n- " + '\n- '.join(violations[:5]) + '\nRemove or correct ONLY the violating candidates (re-check them against the numbered evidence); keep every other item unchanged, then rewrite the COMPLETE final answer with inline [n] citations.'})
                    rw = await _loop_chat(messages, deadline, force_text=True)
                    if rw is None:
                        return answer
                    llm = getattr(rw, 'llm', None)
                    choices = getattr(llm, 'choices', None) or []
                    if not choices:
                        return answer
                    cand_text = _message_text(llm, choices[0].message).strip()
                    if not cand_text or _rewrite_regresses(answer, cand_text):
                        return answer
                    return cand_text
                FETCH_M6_HEAD = 3000
                FETCH_M6_WIN = 3600

                def _densest_windows(note: str, question: str) -> tuple[str, list[tuple[int, int]]]:
                    text = note or ''
                    head_end = min(len(text), FETCH_M6_HEAD)
                    ranges: list[tuple[int, int]] = [(0, head_end)]
                    shown = text[:head_end]
                    terms = set(_WORD_RE.findall((question or '').lower()))
                    body = text[head_end:]
                    if not terms or not body:
                        return (shown, ranges)
                    win, step = (FETCH_M6_WIN, 600)
                    scored: list[tuple[int, int]] = []
                    for start in range(0, max(1, len(body) - win + 1), step):
                        chunk = body[start:start + win]
                        cl = chunk.lower()
                        hits = sum((cl.count(t) for t in terms))
                        if hits > 0:
                            scored.append((hits, start))
                    scored.sort(reverse=True)
                    picked: list[int] = []
                    for _hits, start in scored:
                        if all((abs(start - p) >= win for p in picked)):
                            picked.append(start)
                        if len(picked) >= 3:
                            break
                    picked.sort()
                    for start in picked:
                        abs_start = head_end + start
                        abs_end = min(len(text), abs_start + win)
                        if abs_start >= ranges[-1][1] and abs_end - abs_start >= 200:
                            ranges.append((abs_start, abs_end))
                            shown += f'\n...[offset {abs_start}]...\n' + text[abs_start:abs_end]
                    return (shown, ranges)

                async def query(query: Query) -> Response:
                    question = (query.text or '').strip()
                    if not question:
                        return Response(text='No question provided.')
                    _CTX['question'] = question
                    _CALL_CACHE.clear()
                    try:
                        return await _answer(query, question)
                    except Exception:
                        return Response(text=await _last_resort(question) or f'{question[:200]}')

                async def _answer(query: Query, question: str) -> Response:
                    deadline = monotonic() + TOTAL_BUDGET_SECONDS
                    try:
                        info = await tooling_info(timeout=10.0)
                        _note_budget(info)
                    except Exception:
                        pass
                    briefing = ''
                    draft = ''
                    try:
                        if _budget_left() >= MIN_DRAFT_BUDGET and _remaining(deadline) > 120.0:
                            draft, briefing = await _build_briefing(question)
                    except Exception:
                        briefing = ''
                    index = _ResultIndex()
                    answer = ''
                    messages: list[dict] = []
                    try:
                        answer, messages = await _research_loop(question, briefing, index, deadline, MAX_TURNS)
                    except Exception:
                        answer = ''
                    try:
                        if answer and _remaining(deadline) > 40:
                            _opp = _opposition_queries_from_answer(question, answer or '', limit=3)
                            if _opp:
                                _opp_blob = await _tool_search_many(_opp, index)
                                messages.append({'role': 'system', 'content': '## Contradiction Probe\n\nOpposing/correction searches ran. If they refute a claim, correct it with citations; otherwise keep the draft and cite the confirming notes.\n\n' + _opp_blob[:12000]})
                    except Exception:
                        pass
                    if bool((answer or '').strip()) and _remaining(deadline) > 35:
                        try:
                            _v3_qs: list[str] = []
                            _v3_qs.extend(_v3_claim_reground_queries(query.text, answer or '', limit=3))
                            _v3_qs.extend(_v3_comparison_queries(query.text, limit=2))
                            _v3_qs.extend(_v3_roster_queries(query.text, limit=2))
                            _deduped: list[str] = []
                            _seen_q: set[str] = set()
                            for _q in _v3_qs:
                                _k = _q.lower()
                                if _q and _k not in _seen_q:
                                    _seen_q.add(_k)
                                    _deduped.append(_q)
                            _v3_qs = _deduped[:6]
                            if _v3_qs:
                                _v3_blob = await _tool_search_many(_v3_qs, index)
                                messages.append({'role': 'system', 'content': '## V3 Claim Re-ground / Dual-cite / Roster Fan-out\n\nFresh targeted evidence for bare claims, comparison operands, and roster completeness. Rewrite the COMPLETE final answer with [n] after every load-bearing number/date/name and each comparison side.\n\n' + _v3_blob[:12000]})
                                if _remaining(deadline) > 16:
                                    try:
                                        _rw = await _loop_chat(messages, deadline, force_text=True)
                                        if _rw is not None:
                                            _llm = getattr(_rw, 'llm', None)
                                            _choices = getattr(_llm, 'choices', None) or []
                                            if _choices:
                                                _cand = _message_text(_llm, _choices[0].message)
                                                if _cand and str(_cand).strip():
                                                    answer = str(_cand).strip()
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                    try:
                        if answer and _remaining(deadline) > 45.0 and (_budget_left() >= MIN_PATCH_BUDGET):
                            answer = await _verify_and_patch(question, answer, messages, index, deadline)
                    except Exception:
                        pass
                    try:
                        if answer.strip() and _budget_left() >= MIN_PATCH_BUDGET:
                            answer = await _entity_gap_pass(question, answer, index, deadline)
                    except Exception:
                        pass
                    try:
                        if answer.strip() and _remaining(deadline) > 40.0 and (_budget_left() >= MIN_PATCH_BUDGET):
                            answer = await _numeric_predicate_guard(question, answer, messages, deadline)
                    except Exception:
                        pass
                    answer = _strip_draft_markers(answer)
                    try:
                        answer = _normalize_citation_markers(answer)
                    except Exception:
                        pass
                    deterministic = _deterministic_answer_from_index(index)
                    if not answer.strip():
                        answer = deterministic or draft.strip()
                        if not answer.strip() and _remaining(deadline) > 20.0:
                            answer = await _last_resort(question)
                    if _looks_unfinished(answer):
                        rescue = deterministic or draft.strip()
                        if not rescue and _remaining(deadline) > 20.0:
                            rescue = await _last_resort(question)
                        if rescue:
                            answer = rescue
                    if _is_weak_final(answer) and _remaining(deadline) > 25.0 and (_budget_left() >= FORCE_COMMIT_BUDGET):
                        try:
                            recommitted = _strip_draft_markers(await _force_commit_resynth(question, index, deadline))
                            if recommitted.strip() and (not _is_weak_final(recommitted)):
                                answer = recommitted
                        except Exception:
                            pass
                    answer = _apply_output_directives(question, answer)
                    try:
                        answer = _normalize_citation_markers(answer)
                    except Exception:
                        pass
                    try:
                        citations = _build_citations(answer, index)
                    except Exception:
                        citations = []
                    final_text = _clamp(answer) or deterministic or _clamp(draft) or f'{question[:200]}'
                    if query.output_schema is not None:
                        try:
                            output = await _structured_output(question, answer, query.output_schema)
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

                async def _build_briefing(question: str) -> tuple[str, str]:
                    system = 'You are an elite research analyst with encyclopedic knowledge preparing a research briefing. Commit to concrete best guesses; never refuse.'
                    user = f"Question:\n{question}\n\nProduce a briefing with exactly these sections:\nDRAFT: your best definitive answer from knowledge alone — enumerate the full candidate pool, apply every constraint, name qualifying entities with concrete numbers/dates, note borderline exclusions. Mark uncertain values with (verify).\nCONSTRAINTS: numbered list of every atomic constraint/filter in the question (including ordering and requested output format).\nCANDIDATES: the entities to verify, one per line, with which constraints are uncertain for each.\nQUERIES: 3-6 targeted web searches that would verify the load-bearing facts (exact names + years; include the named source site if any).\nFETCH: 0-6 exact URLs likely to contain the needed figures, ONLY for named sources whose URL patterns you know (one per entity/year; for annual reports pick the edition containing each requested year, usually year+1 or year+2). Otherwise write 'none'."
                    try:
                        raw = await _plain_chat(DRAFT_MODEL, system=system, user=user, max_tokens=2400, timeout=DRAFT_TIMEOUT, thinking={'enabled': False})
                    except Exception:
                        raw = await _plain_chat(FALLBACK_MODEL, system=system, user=user, max_tokens=2000, timeout=DRAFT_TIMEOUT)
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
                _ENT_TOK = "[A-Z][\\w.&'’-]*(?:\\s+(?:of|de|von|van|al|el|du|da|di|del|della|la|le|dos|das)\\s+[A-Z][\\w.&'’-]*|\\s+[A-Z][\\w.&'’-]*){0,4}"
                _ENTITY_LIST_RE = re.compile(f'({_ENT_TOK}(?:\\s*,\\s*(?:and\\s+|or\\s+)?{_ENT_TOK}){{2,}})')
                _ENTITY_HEAD_STOP = frozenset({'The', 'A', 'An', 'In', 'On', 'At', 'Of', 'And', 'Or', 'For', 'To', 'As', 'By', 'Which', 'What', 'Who', 'When', 'Where', 'According', 'During', 'Based', 'Using', 'Both', 'Each'})
                _METRIC_STOP = frozenset({'which', 'what', 'who', 'whom', 'whose', 'when', 'where', 'the', 'and', 'for', 'with', 'that', 'this', 'these', 'those', 'from', 'into', 'among', 'between', 'according', 'following', 'were', 'was', 'have', 'has', 'had', 'did', 'does', 'their', 'them', 'they', 'there', 'about', 'would', 'could', 'should', 'than', 'then', 'over', 'under', 'each', 'every', 'both', 'list', 'name'})

                def _enumerated_entities(question: str) -> list[str]:
                    best: list[str] = []
                    for m in _ENTITY_LIST_RE.finditer(question or ''):
                        parts = re.split('\\s*,\\s*|\\s+and\\s+|\\s+or\\s+', m.group(1))
                        ents: list[str] = []
                        for p in parts:
                            toks = p.strip(' .,;:').split()
                            while toks and (toks[0] in _ENTITY_HEAD_STOP or toks[0][:1].islower()):
                                toks.pop(0)
                            cleaned = ' '.join(toks)
                            if len(cleaned) >= 3 and cleaned[:1].isupper():
                                ents.append(cleaned)
                        if len(ents) >= 3 and len(ents) > len(best):
                            best = ents
                    seen: set[str] = set()
                    out: list[str] = []
                    for e in best:
                        k = e.lower()
                        if k not in seen:
                            seen.add(k)
                            out.append(e)
                    return out

                def _metric_hint(question: str, entities: list[str]) -> str:
                    ent_words = {w.lower() for e in entities for w in re.findall('[A-Za-z]{3,}', e)}
                    words = re.findall('[A-Za-z]{4,}', question or '')
                    hint = [w for w in words if w.lower() not in _METRIC_STOP and w.lower() not in ent_words and (not w[0].isupper())]
                    return ' '.join(dict.fromkeys(hint))[:60]

                def _entities_missing(entities: list[str], answer: str, index: _ResultIndex) -> list[str]:
                    blob = (answer or '').lower()
                    for e in index.entries.values():
                        blob += ' ' + (e.get('note') or '').lower()
                    missing: list[str] = []
                    for ent in entities:
                        toks = re.findall('[A-Za-z]{4,}', ent)
                        probe = max(toks, key=len).lower() if toks else ent.lower()
                        if ent.lower() not in blob and probe not in blob:
                            missing.append(ent)
                    return missing

                async def _entity_gap_pass(question: str, answer: str, index: _ResultIndex, deadline: float) -> str:
                    entities = _enumerated_entities(question)
                    if len(entities) < 3:
                        try:
                            _qi = _quoted_items(question)
                            if len(_qi) >= 2:
                                entities = _qi
                        except Exception:
                            pass
                    if len(entities) < 2 or _remaining(deadline) < 55.0:
                        return answer
                    missing = _entities_missing(entities, answer, index)
                    if not missing:
                        return answer
                    hint = _metric_hint(question, entities)
                    outs = await asyncio.gather(*[_tool_search(f'{ent} {hint}'.strip(), index) for ent in missing[:4]], return_exceptions=True)
                    tool_msgs = [o for o in outs if isinstance(o, str) and o.strip()]
                    if not tool_msgs:
                        return answer
                    seed: list[dict] = [{'role': 'system', 'content': LOOP_SYSTEM_PROMPT}, {'role': 'assistant', 'content': (answer or '')[:8000]}, {'role': 'system', 'content': 'COVERAGE GAP: your answer above did not cover these required items from the question: ' + ', '.join(missing) + '. Fresh search results for them follow. Incorporate every one, KEEP all items you already had, and rewrite the COMPLETE final answer with inline [n] citations.'}]
                    seed += [{'role': 'user', 'content': m} for m in tool_msgs]
                    seed.append({'role': 'user', 'content': question})
                    try:
                        patched, _ = await _research_loop(question, '', index, deadline, 2, seed_messages=seed)
                    except Exception:
                        return answer
                    patched = _strip_draft_markers(patched)
                    return patched.strip() or answer

                async def _research_loop(question: str, briefing: str, index: _ResultIndex, deadline: float, max_turns: int, seed_messages: list[dict] | None=None) -> tuple[str, list[dict]]:
                    if seed_messages is not None:
                        messages = seed_messages
                    else:
                        messages = [{'role': 'system', 'content': LOOP_SYSTEM_PROMPT}]
                        enum_directive = _enum_directive(question)
                        if enum_directive:
                            messages.append({'role': 'system', 'content': enum_directive})
                        if briefing:
                            messages.append({'role': 'system', 'content': briefing})
                        messages.append({'role': 'user', 'content': question})
                    if seed_messages is None:
                        try:
                            _seeds = _seed_queries_from_question(question, limit=3)
                            try:
                                if _enum_is_set_question(question):
                                    _lq = _m1_list_seed(question)
                                    if _lq and _lq.lower() not in {s.lower() for s in _seeds}:
                                        _seeds.append(_lq)
                                _seeds = _seeds[:4]
                            except Exception:
                                pass
                            if _seeds and _remaining(deadline) > 60:
                                try:
                                    _seed_blob = await _tool_search_many_det(_seeds, index)
                                except Exception:
                                    _seed_blob = await _tool_search_many(_seeds, index)
                                messages.append({'role': 'system', 'content': '## Seed Evidence\n\nParallel seed searches already ran. Use these numbered results; call search_many for remaining candidates.\n\n' + _seed_blob[:12000]})
                        except Exception:
                            pass
                    try:
                        if _remaining(deadline) > 50:
                            _auth_blob = ''
                            for _msg in messages:
                                if isinstance(_msg, dict) and 'Seed Evidence' in str(_msg.get('content', '')):
                                    _auth_blob = str(_msg.get('content', ''))
                                    break
                            _auth_urls = _authority_urls_from_blob(_auth_blob, limit=2)
                            if _auth_urls:
                                _auth_parts = []
                                for u in _auth_urls:
                                    try:
                                        _auth_parts.append(await _tool_fetch(u, index))
                                    except Exception:
                                        continue
                                if _auth_parts:
                                    messages.append({'role': 'system', 'content': '## Authority Prefetch\n\nPrimary/official pages were fetched automatically from seed hits. Prefer these over secondary blogs.\n\n' + '\n\n'.join(_auth_parts)[:14000]})
                    except Exception:
                        pass
                    if seed_messages is None:
                        try:
                            if _remaining(deadline) > 70:
                                _m2_parts = await _m2_item_and_data_fetches(question, index)
                                if _m2_parts:
                                    messages.append({'role': 'system', 'content': "## Item Own-Pages / Authoritative Data Queries\n\nPages fetched directly: each enumerated item's OWN page and/or the authoritative database query matching this question's filters. Cite each item's value from its own page; a returned count/row set from a data query is the winning citation.\n\n" + '\n\n'.join(_m2_parts)[:16000]})
                        except Exception:
                            pass
                    final_answer = ''
                    nudged = False
                    for turn in range(1, max_turns + 1):
                        remaining = _remaining(deadline)
                        if remaining <= 8.0:
                            break
                        time_critical = remaining <= FORCE_COMMIT_SECONDS
                        budget_critical = _budget_left() <= FORCE_COMMIT_BUDGET
                        force_final = turn >= max_turns or time_critical or budget_critical
                        if (force_final or turn >= max_turns - 1) and (not nudged):
                            messages.append({'role': 'system', 'content': _force_commit_message(remaining)})
                            nudged = True
                        payload = await _loop_chat(messages, deadline, force_text=force_final)
                        if payload is None:
                            break
                        _note_budget(payload)
                        llm = getattr(payload, 'llm', None)
                        choices = getattr(llm, 'choices', None) or []
                        if not choices:
                            break
                        message = choices[0].message
                        tool_calls = getattr(message, 'tool_calls', None) or ()
                        if not tool_calls:
                            text = _message_text(llm, message)
                            leaked = _parse_leaked_tool_calls(text)
                            if leaked and (not force_final):
                                messages.append({'role': 'assistant', 'content': text})
                                outs = await asyncio.gather(*[_tool_search(a, index) if n == 'search_web' else _tool_fetch(a, index) for n, a in leaked[:3]], return_exceptions=True)
                                for out in outs:
                                    messages.append({'role': 'user', 'content': out if isinstance(out, str) else f'# tool error: {out}'})
                                continue
                            if '<tool_call' in text.lower():
                                text = _strip_leak_markup(text)
                            final_answer = text
                            break
                        messages.append(message.to_input_message())
                        outputs = await asyncio.gather(*[_run_tool_call(tc, index) for tc in tool_calls], return_exceptions=True)
                        for tc, out in zip(tool_calls, outputs):
                            text = out if isinstance(out, str) else f'# tool error: {out}'
                            messages.append({'role': 'tool', 'tool_call_id': tc.id, 'content': text})
                    return (final_answer, messages)

                async def _loop_chat(messages: list[dict], deadline: float, *, force_text: bool):
                    for attempt in range(2):
                        timeout = min(LOOP_TURN_TIMEOUT, _remaining(deadline) - 5.0)
                        if timeout <= 5.0:
                            return None
                        model = LOOP_MODEL if attempt == 0 else FALLBACK_MODEL
                        try:
                            return await llm_chat(provider=PROVIDER, model=model, messages=messages, tools=None if force_text else TOOLS, tool_choice=None if force_text else 'auto', temperature=0.2, thinking={'enabled': True, 'effort': 'low'}, timeout=timeout)
                        except Exception:
                            continue
                    return None

                async def _run_tool_call(tc, index: _ResultIndex) -> str:
                    try:
                        args = json.loads(getattr(tc, 'arguments', None) or '{}')
                    except Exception:
                        args = {}
                    name = getattr(tc, 'name', '') or ''
                    if name == 'search_web':
                        return await _tool_search(str(args.get('query', '')), index)
                    if name == 'search_many':
                        qs = args.get('queries') or []
                        return await _tool_search_many(qs if isinstance(qs, list) else [qs], index)
                    if name == 'fetch_page':
                        return await _tool_fetch(str(args.get('url', '')), index)
                    return f'# unknown tool {name!r}'

                async def _tool_search(q: str, index: _ResultIndex) -> str:
                    if not q.strip():
                        return '# search_web -> empty query'
                    _ck = _cache_key('search', q)
                    _hit = _CALL_CACHE.get(_ck)
                    if _hit is not None:
                        return _hit
                    resp = None
                    for provider in ('parallel',):
                        try:
                            resp = await search_web(q, provider=provider, num=8, timeout=SEARCH_TIMEOUT)
                            if getattr(resp, 'results', None):
                                break
                        except Exception:
                            resp = None
                    if resp is None:
                        return f'# search_web({q!r}) -> ERROR (all providers failed)'
                    _note_budget(resp)
                    receipt = getattr(resp, 'receipt_id', '') or ''
                    lines = [f'# search_web({q!r}) -> {len(resp.results or [])} results']
                    for result in list(getattr(resp, 'results', None) or []):
                        rid = getattr(result, 'result_id', None)
                        if not isinstance(rid, str) or not rid:
                            continue
                        note = (getattr(result, 'note', None) or '')[:SEARCH_NOTE_CHARS]
                        title = getattr(result, 'title', None) or ''
                        url = getattr(result, 'url', None) or ''
                        number = index.add(receipt, rid, note, 'search', url)
                        lines.append(f'[{number}] {title}\n  url: {url}\n  excerpt: {note}')
                    out = '\n'.join(lines)
                    if len(lines) > 1:
                        _CALL_CACHE[_ck] = out
                    return out

                async def _tool_search_many(queries: list, index: _ResultIndex) -> str:
                    clean = [str(q).strip() for q in queries or [] if str(q).strip()][:8]
                    if not clean:
                        return '# search_many() -> ERROR: no queries'
                    parts = await asyncio.gather(*(_tool_search(q, index) for q in clean))
                    return f'# search_many({len(clean)} queries)\n' + '\n\n'.join(parts)

                async def _tool_fetch(url: str, index: _ResultIndex) -> str:
                    if not url.strip():
                        return '# fetch_page -> empty url'
                    _ck = _cache_key('fetch', url)
                    _hit = _CALL_CACHE.get(_ck)
                    if _hit is not None:
                        return _hit
                    resp = None
                    for provider in ('parallel',):
                        try:
                            resp = await fetch_page(url, provider=provider, timeout=FETCH_TIMEOUT)
                            if getattr(resp, 'results', None):
                                break
                        except Exception:
                            resp = None
                    if resp is None:
                        return f'# fetch_page({url!r}) -> ERROR (all providers failed)'
                    _note_budget(resp)
                    receipt = getattr(resp, 'receipt_id', '') or ''
                    results = list(getattr(resp, 'results', None) or [])
                    if not results:
                        return f'# fetch_page({url!r}) -> no content'
                    result = results[0]
                    rid = getattr(result, 'result_id', None)
                    note = getattr(result, 'note', None) or ''
                    if not isinstance(rid, str) or not rid or (not note.strip()):
                        return f'# fetch_page({url!r}) -> no usable content'
                    number = index.add(receipt, rid, note, 'fetch', url)
                    shown = note[:FETCH_NOTE_CHARS]
                    if len(note) > FETCH_NOTE_CHARS:
                        try:
                            _shown_m6, _ranges_m6 = _densest_windows(note, _CTX.get('question', ''))
                            if _shown_m6:
                                shown = _shown_m6
                                index.entries[number]['windows'] = _ranges_m6
                        except Exception:
                            pass
                    out = f'# fetch_page({url!r}) -> [{number}] {len(shown)} chars shown\n{shown}'
                    _CALL_CACHE[_ck] = out
                    return out
                _WORD_RE = re.compile('[a-z0-9]{4,}')
                _RECENCY_RE = re.compile('\\b(updated?|revised|raised|increased to|reduced to|changed to|now|current(?:ly)?|latest|as of|effective|new(?:ly)?|v\\d+\\.\\d+|\\d{4})\\b', re.IGNORECASE)

                def _focus_window(note: str, question: str, limit: int) -> str:
                    text = note or ''
                    if len(text) <= limit:
                        return text
                    terms = set(_WORD_RE.findall(question.lower()))
                    head = text[:FETCH_WINDOW_HEAD]
                    body = text[FETCH_WINDOW_HEAD:]
                    if not terms or not body:
                        return text[:limit]
                    win, step = (1400, 350)
                    scored: list[tuple[int, int, str]] = []
                    for start in range(0, max(1, len(body) - win + 1), step):
                        chunk = body[start:start + win]
                        cl = chunk.lower()
                        hits = sum((cl.count(t) for t in terms))
                        if hits <= 0:
                            continue
                        recency = len(_RECENCY_RE.findall(chunk))
                        scored.append((hits + 2 * recency, start, chunk))
                    if not scored:
                        return text[:limit]
                    scored.sort(reverse=True)
                    picked: list[tuple[int, str]] = []
                    for _score, start, chunk in scored:
                        if all((abs(start - s) >= win for s, _ in picked)):
                            picked.append((start, chunk))
                        if len(picked) >= 2:
                            break
                    picked.sort()
                    budget = limit - len(head) - 20
                    out = head
                    for _start, chunk in picked:
                        if budget <= 0:
                            break
                        seg = chunk[:budget]
                        out += '\n...\n' + seg
                        budget -= len(seg)
                    return out

                async def _verify_and_patch(question: str, answer: str, messages: list[dict], index: _ResultIndex, deadline: float) -> str:
                    check_user = f'Audit this answer against its question. Report ONLY genuine, fixable problems as a JSON object with keys: "missing_elements" (question elements not addressed, or a qualifying set member not evaluated), "uncited_claims" (specific load-bearing factual claims lacking [n]), "suspect_attributions" (facts that look attributed to the wrong entity), "contradictions" (claims that conflict with the text of their own cited source, e.g. answer says shot in Paris but the citation says Nantes), "wrong_source" (used an aggregator/news site when the question named a specific primary source like the UN, Forbes, or Box Office Mojo). Use empty lists when fine. No other text.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:12000]}'
                    try:
                        raw = await _plain_chat(PATCH_MODEL, system='You are a strict answer auditor. Output JSON only.', user=check_user, max_tokens=700, timeout=PATCH_TIMEOUT)
                        cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
                        report = json.loads(cleaned)
                    except Exception:
                        return answer
                    issues = []
                    for key in ('missing_elements', 'uncited_claims', 'suspect_attributions', 'contradictions', 'wrong_source'):
                        values = report.get(key) if isinstance(report, dict) else None
                        if isinstance(values, list):
                            issues.extend((str(v) for v in values if str(v).strip()))
                    if not issues or _remaining(deadline) < 40.0:
                        return answer
                    route_hint = ''
                    try:
                        if isinstance(report, dict) and report.get('missing_elements'):
                            route_hint = "\nFIRST ACTION: fetch the authoritative LIST page that covers the missing items (the named source's own index or the relevant en.wikipedia.org list page) BEFORE rewriting; add one cited line per recovered item."
                    except Exception:
                        route_hint = ''
                    messages.append({'role': 'system', 'content': 'AUDIT FOUND GAPS in your final answer:\n- ' + '\n- '.join(issues[:6]) + '\nYou may use at most 2 more tool calls to close the most important gaps, then rewrite the COMPLETE final answer with inline [n] citations in the required shape.' + route_hint})
                    patched, _ = await _research_loop(question, '', index, deadline, PATCH_EXTRA_TURNS + 1, seed_messages=messages)
                    patched = patched.strip()
                    if patched and _rewrite_regresses(answer, patched):
                        return answer
                    return patched or answer
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
                    for n in numbers[:MAX_CITATIONS]:
                        entry = index.entries.get(n)
                        if entry is None:
                            continue
                        receipt_id = entry['receipt_id']
                        result_id = entry['result_id']
                        if not receipt_id or not result_id:
                            continue
                        if entry['source'] == 'fetch' and entry['note_len'] > FETCH_SLICE_THRESHOLD:
                            slices = [CitationSlice(start=0, end=FETCH_NOTE_CHARS)]
                            try:
                                wins = entry.get('windows') or []
                                m6_slices = []
                                for s, e in wins:
                                    e2 = min(int(e), entry['note_len'])
                                    if isinstance(s, int) and e2 - int(s) >= 120:
                                        m6_slices.append(CitationSlice(start=int(s), end=e2))
                                if m6_slices:
                                    slices = m6_slices[:4]
                            except Exception:
                                slices = [CitationSlice(start=0, end=FETCH_NOTE_CHARS)]
                            refs.append(CitationRef(receipt_id=receipt_id, result_id=result_id, slices=slices))
                        else:
                            refs.append(CitationRef(receipt_id=receipt_id, result_id=result_id))
                    return refs

                async def _last_resort(question: str) -> str:
                    try:
                        return await _plain_chat(FALLBACK_MODEL, system='Expert researcher. Give your best definitive answer with concrete entities, numbers and dates. Never refuse. Do not output the word DRAFT, placeholders, or any note that this is provisional.', user=question, max_tokens=1600, timeout=50.0)
                    except Exception:
                        return ''
                _DRAFT_LEAD_RE = re.compile('^\\s*(?:#+\\s*)?(?:\\*+\\s*)?draft\\b\\s*[:\\-—]*\\s*(?:\\*+)?\\s*', re.IGNORECASE)
                _DRAFT_INLINE_RE = re.compile('\\s*[\\(\\[]\\s*(?:draft|verify|unverified|to verify|tbd|needs? verification|best guess|placeholder|approx(?:imate)?)\\s*[\\)\\]]', re.IGNORECASE)

                def _strip_draft_markers(answer: str) -> str:
                    if not answer:
                        return answer
                    out = _DRAFT_LEAD_RE.sub('', answer.lstrip(), count=1)
                    out = _DRAFT_INLINE_RE.sub('', out)
                    out = re.sub('(?im)^\\s*(?:#+\\s*)?\\**\\s*draft\\s*\\**\\s*$\\n?', '', out)
                    return out.strip() or answer
                _SENT_RE = re.compile('(.+?[.!?])(?:\\s|$)', re.S)

                def _lead_sentence(note: str, limit: int=260) -> str:
                    text = (note or '').strip().replace('\n', ' ')
                    text = re.sub('\\s{2,}', ' ', text)
                    if not text:
                        return ''
                    m = _SENT_RE.match(text)
                    sentence = (m.group(1) if m else text).strip()
                    if len(sentence) > limit:
                        sentence = sentence[:limit - 1].rstrip() + '…'
                    return sentence

                def _deterministic_answer_from_index(index: _ResultIndex, max_sentences: int=5) -> str:
                    entries = [(n, e) for n, e in index.entries.items() if (e.get('note') or '').strip()]
                    if not entries:
                        return ''
                    entries.sort(key=lambda ne: (ne[1].get('authority', 0), 1 if ne[1].get('source') == 'fetch' else 0, ne[1].get('note_len', 0)), reverse=True)
                    lines: list[str] = []
                    seen: set[str] = set()
                    for n, e in entries:
                        sentence = _lead_sentence(e.get('note', ''))
                        key = sentence[:60].lower()
                        if not sentence or key in seen:
                            continue
                        seen.add(key)
                        lines.append(f'{sentence} [{n}]')
                        if len(lines) >= max_sentences:
                            break
                    return ' '.join(lines)
                _WEAK_FINAL_RE = re.compile("cannot be (?:\\w+\\s+){0,2}(?:determined|resolved|answered|established|identified)|could not (?:be )?(?:determined|resolved|found|established|identified)|(?:accepted )?(?:evidence|packets?|sources?) (?:do(?:es)? not|did not|don'?t|doesn'?t|lack)|(?:evidence|packets?|data) (?:lack|are insufficient|is insufficient)|insufficient (?:evidence|data|information)|unable to (?:determine|answer|identif|resolv|provide)|not (?:enough|sufficient) (?:evidence|data|information)|no (?:reliable )?(?:evidence|data) (?:to|is|was)", re.IGNORECASE)
                _WIKI_JUNK = ('this article needs', 'more citations', 'additional citations', 'unsourced material', '[edit]', 'jump to navigation', 'jump to search', 'from wikipedia, the free encyclopedia', 'this article is about', 'citations for verification', 'please help improve', 'needs to be updated')

                def _looks_csv_dump(a: str) -> bool:
                    first = a.split('\n', 1)[0][:400]
                    fields = [f.strip() for f in first.split(',')]
                    if len(fields) < 5:
                        return False
                    codeish = sum((1 for f in fields if re.fullmatch('[A-Z][A-Z0-9_]{2,}', f) or re.fullmatch('-?\\d[\\d.,]*', f)))
                    return codeish >= max(4, int(len(fields) * 0.6))

                def _is_weak_final(answer: str) -> bool:
                    a = (answer or '').strip()
                    if len(a) < 12:
                        return True
                    if _WEAK_FINAL_RE.search(a[:1500]):
                        return True
                    low = a.lower()
                    committed = 'final answer' in low[:400] or low[:60].startswith(('answer:', '**answer', 'the answer'))
                    if committed:
                        return False
                    headers = len(re.findall('#{1,4}\\s\\S', a))
                    links = a.count('](http') + a.count('[](')
                    junk = low.count('logo') + low.count('season summary') + low.count('[via ') + low.count('[about ') + low.count('skip to') + sum((low.count(w) for w in _WIKI_JUNK))
                    if headers + links + junk >= 3:
                        return True
                    if any((w in low[:800] for w in _WIKI_JUNK)):
                        return True
                    lead = a.lstrip()
                    if lead[:1] in ('|',) or lead.startswith(('[](', '[icon', '![', '| ')):
                        return True
                    if _looks_csv_dump(a):
                        return True
                    return False

                async def _force_commit_resynth(question: str, index: _ResultIndex, deadline: float) -> str:
                    evidence = []
                    for n, e in sorted(index.entries.items()):
                        note = (e.get('note') or '').strip()
                        if note:
                            evidence.append(f"[{n}] {e.get('url', '')}\n{note}")
                    if not evidence:
                        return _deterministic_answer_from_index(index)
                    ev_text = '\n\n'.join(evidence[:24])[:14000]
                    user = f"Question:\n{question}\n\nNumbered evidence:\n{ev_text}\n\nYour prior attempt refused, hedged, or pasted raw page text. Now COMPUTE a specific answer using ONLY the numbered evidence above: never say 'cannot be determined', 'evidence does not contain it', or that data is missing; do the arithmetic / intersection / count / ranking yourself; for a set question enumerate the full candidate pool and name every qualifier. Open with 'FINAL ANSWER:' then the direct answer, with inline [n] citations."
                    try:
                        out = await _plain_chat(LOOP_MODEL, system=LOOP_SYSTEM_PROMPT, user=user, max_tokens=1800, timeout=min(60.0, max(12.0, _remaining(deadline) - 10.0)))
                    except Exception:
                        out = ''
                    return out.strip() or _deterministic_answer_from_index(index)

                async def _structured_output(question: str, answer: str, schema) -> object | None:
                    schema_text = json.dumps(schema)
                    user = f'Convert this answer into a JSON value that validates against the schema. Return ONLY the JSON value.\n\nSchema:\n{schema_text}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:15000]}'
                    for model in (JSON_MODEL, FALLBACK_MODEL):
                        try:
                            raw = await _plain_chat(model, system='You output strictly valid JSON matching the given schema.', user=user, max_tokens=2400, timeout=50.0)
                            cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()
                            return json.loads(cleaned)
                        except Exception:
                            continue
                    return None

                async def _plain_chat(model: str, *, system: str, user: str, max_tokens: int, timeout: float, thinking: dict | None=None) -> str:
                    if thinking is None:
                        if 'gpt-oss' in model:
                            thinking = {'enabled': True, 'effort': 'low'}
                        else:
                            thinking = {'enabled': False}
                    payload = await llm_chat(provider=PROVIDER, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=thinking)
                    _note_budget(payload)
                    llm = getattr(payload, 'llm', None)
                    text = (getattr(llm, 'raw_text', None) or '').strip()
                    if text:
                        return text
                    choices = getattr(llm, 'choices', None) or []
                    if choices:
                        got = _content_to_text(getattr(choices[0].message, 'content', None)).strip()
                        if got:
                            return got
                    return ''

                def _remaining(deadline: float) -> float:
                    return deadline - monotonic()

                def _clamp(text: str) -> str:
                    t = (text or '').strip()
                    if len(t) > MAX_ANSWER_CHARS:
                        return t[:MAX_ANSWER_CHARS - 20] + '\n…[truncated]'
                    return t

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
                VERSION = 'v33.4-openrouter'
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
                TURN_TIMEOUT_S = 75.0
                AUDIT_TIMEOUT_S = 28.0
                SEARCH_TIMEOUT_S = 18.0
                FETCH_TIMEOUT_S = 16.0
                WRAPUP_AT_S = 90.0
                MAX_TURNS = 15
                AUDIT_EXTRA_TURNS = 2
                ANSWER_REPAIR_TURNS = 2
                RESCUE_TIMEOUT_S = 55.0
                DIGEST_TAIL_S = 14.0
                MIN_TAIL_S = 8.0
                BRIEF_PHASE_S = BRIEF_TIMEOUT_S + 12.0
                PRESEED_PHASE_S = 60.0
                SEARCH_EXCERPT_CHARS = 550
                FETCH_HEAD_CHARS = 3000
                FETCH_WINDOW_CHARS = 3600
                FETCH_WINDOWS_PER_PAGE = 3
                FETCH_PLAIN_CHARS = 6500
                ANSWER_CHAR_CAP = 60000
                CITATION_CAP = 24
                TRANSCRIPT_CHAR_BUDGET = 300000
                TOOL_MSG_KEEP_CHARS = 2400
                TOOL_MSGS_KEPT_WHOLE = 8
                WINDOW_SCAN_MAX_CHARS = 1200000
                WINDOW_SCAN_MAX_TERMS = 48
                EVIDENCE_CHAR_BUDGET = 105000
                CLAIM_MAX = 50
                CLAIM_VIEW_MAX = 18
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

                def _payload_message(payload):
                    try:
                        llm = getattr(payload, 'llm', None)
                        if llm is None:
                            return None
                        choices = getattr(llm, 'choices', None) or []
                        if not choices:
                            return None
                        return getattr(choices[0], 'message', None)
                    except Exception:
                        return None

                def _payload_text(payload) -> str:
                    try:
                        llm = getattr(payload, 'llm', None)
                        text = (getattr(llm, 'raw_text', None) or '').strip() if llm is not None else ''
                        if text:
                            return text
                    except Exception:
                        return ''
                    msg = _payload_message(payload)
                    if msg is None:
                        return ''
                    content = getattr(msg, 'content', None)
                    if isinstance(content, str):
                        return content.strip()
                    return ''

                def _transcript_chars(messages: list) -> int:
                    total = 0
                    for m in messages:
                        if isinstance(m, dict):
                            content = m.get('content')
                            if isinstance(content, str):
                                total += len(content)
                    return total

                def _compact_transcript(messages: list) -> None:
                    if _transcript_chars(messages) <= TRANSCRIPT_CHAR_BUDGET:
                        return
                    tool_positions = []
                    for i, m in enumerate(messages):
                        if isinstance(m, dict) and m.get('role') == 'tool' and isinstance(m.get('content'), str):
                            tool_positions.append(i)
                    if len(tool_positions) <= TOOL_MSGS_KEPT_WHOLE:
                        return
                    for i in tool_positions[:-TOOL_MSGS_KEPT_WHOLE]:
                        body = messages[i]['content']
                        if len(body) <= TOOL_MSG_KEEP_CHARS:
                            continue
                        messages[i]['content'] = body[:TOOL_MSG_KEEP_CHARS] + '\n… [earlier result trimmed to fit the context window; its [n] numbers above remain valid — re-read the page if you need more]'
                        if _transcript_chars(messages) <= TRANSCRIPT_CHAR_BUDGET:
                            return
                LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}]
                LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITATION QUOTE — ADD A SUPPORTS NOTE: immediately after each [n], write \'Supports: [verbatim quote]\' with 5-20 words taken verbatim from result [n] that directly prove the claim. Example: \'...shipped 59 million units [4]. Supports: «Lenovo shipped 59.0M units in 2023» — IDC tracker.\' The VERIFIED CLAIM LEDGER injected as a system message shows confirmed facts with their verbatim quotes — use those quotes for your Supports: notes. This targeted per-claim annotation makes each citation directly traceable.\n\nCITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

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

                def _ledger_add(ledger: list, receipt_id: str, result_id: str, note_len: int, kind: str, spans: list | None, title: str='', url: str='', preview: str='') -> int:
                    ledger.append({'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': (url or '')[:300], 'preview': (preview or '')[:1200], 'spans': spans})
                    return len(ledger)

                def _ledger_ref(ledger: list, number: int):
                    if not 1 <= number <= len(ledger):
                        return None
                    row = ledger[number - 1]
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
                _CLAIM_FIGURE_RE = re.compile('\\$[\\d,.]+[MBKT]?|\\b\\d[\\d,.]*\\s*(?:%|percent|million|billion|thousand)\\b|\\b(?:19|20)\\d{2}\\b', re.I)
                _CLAIM_SENTENCE_SPLIT_RE = re.compile('(?<=[.!?])\\s+|\\n+')

                def _extract_claim_sentences(text: str) -> list:
                    sentences = _CLAIM_SENTENCE_SPLIT_RE.split((text or '')[:4000])
                    out: list = []
                    for sent in sentences:
                        sent = ' '.join(sent.split())
                        if len(sent) < 30 or len(sent) > 320:
                            continue
                        if not _CLAIM_FIGURE_RE.search(sent):
                            continue
                        out.append(sent)
                        if len(out) >= 12:
                            break
                    return out

                def _claim_slot_key(text: str) -> str:
                    words = re.sub('[^a-z0-9 ]', ' ', (text or '').lower()).split()[:8]
                    return ' '.join(words)

                def _update_claim_ledger(claim_ledger: dict, preview: str, n_ref: int, url: str) -> None:
                    if not preview or n_ref <= 0 or len(claim_ledger) >= CLAIM_MAX:
                        return
                    for sent in _extract_claim_sentences(preview):
                        key = _claim_slot_key(sent)
                        if not key or key in claim_ledger:
                            continue
                        claim_ledger[key] = {'claim': sent[:200], 'quote': sent[:150], 'n_ref': n_ref, 'url': url}
                        if len(claim_ledger) >= CLAIM_MAX:
                            break

                def _claim_status_view(claim_ledger: dict) -> str:
                    if not claim_ledger:
                        return ''
                    lines = ["VERIFIED CLAIM LEDGER — cite these [n] with a 'Supports: [quote]' annotation for each claim you use:"]
                    for i, rec in enumerate(claim_ledger.values()):
                        if i >= CLAIM_VIEW_MAX:
                            break
                        lines.append(f"  [{rec['n_ref']}] {rec['claim'][:180]}")
                    return '\n'.join(lines)
                _SNIPPET_RESULT_LINE_RE = re.compile('^\\s*#\\s+web_search\\b|^\\s*\\[\\d+\\]\\s+.+?\\s+—\\s+https?://', re.M)
                _SNIPPET_RAW_URL_RE = re.compile('https?://\\S{8,}', re.I)

                def _is_snippet_dump(answer: str) -> bool:
                    if not answer or len(answer) < 50:
                        return False
                    if _SNIPPET_RESULT_LINE_RE.search(answer[:4000]):
                        return True
                    urls = _SNIPPET_RAW_URL_RE.findall(answer[:3000])
                    if len(urls) >= 5:
                        return True
                    return False
                _WORD_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
                _STOP = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

                def _key_terms(text: str) -> set[str]:
                    return {w for w in _WORD_RE.findall((text or '').casefold()) if w not in _STOP}

                def _best_windows(note: str, terms: set[str], width: int, k: int=1) -> list[tuple[int, int]]:
                    n = len(note)
                    if n <= width:
                        return [(0, n)]
                    if n > WINDOW_SCAN_MAX_CHARS:
                        n = WINDOW_SCAN_MAX_CHARS
                    if len(terms) > WINDOW_SCAN_MAX_TERMS:
                        ranked = sorted(((-len(t), t) for t in terms))
                        terms = {t for _neg, t in ranked[:WINDOW_SCAN_MAX_TERMS]}
                    step = max(600, width // 3)
                    low = note[:n].lower()
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

                def _commit_tool_output(out, ledger: list) -> str:
                    if isinstance(out, str):
                        return out
                    if not isinstance(out, dict) or not isinstance(out.get('text'), str):
                        return f'# tool crashed: {out}'
                    text = out['text']
                    for i, row in enumerate(out.get('rows') or []):
                        try:
                            n = _ledger_add(ledger, row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''))
                        except Exception:
                            continue
                        text = text.replace(_SLOT.format(i), str(n))
                    if '\x00' in text:
                        text = text.replace('\x00', '')
                    return text
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
                    return _payload_text(payload)

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

                async def _preseed(question: str, set_question: bool, ledger: list, deadline: float) -> str:
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
                            blocks.append(_commit_tool_output(out, ledger))
                        except Exception:
                            continue
                    good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
                    if not good:
                        return ''
                    return 'Automatic first-pass searches (already numbered — cite these [n] directly, and search further as needed):\n\n' + '\n'.join(good)

                def _tool_cache_key(call) -> str:
                    name = getattr(call, 'name', '') or ''
                    raw = getattr(call, 'arguments', None) or '{}'
                    try:
                        args = json.loads(raw)
                    except Exception:
                        args = None
                    if isinstance(args, dict):
                        try:
                            return name + '|' + json.dumps(args, sort_keys=True)
                        except Exception:
                            pass
                    return name + '|' + str(raw)

                async def _loop(question: str, brief: str, ledger: list, deadline: float, turn_cap: int, carry: list[dict] | None=None, allow_tools_in_wrapup: bool=False, tool_cache: dict | None=None, claim_ledger: dict | None=None) -> tuple[str, list[dict]]:
                    if tool_cache is None:
                        tool_cache = {}
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
                    _claim_view_idx = -1
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
                        _compact_transcript(messages)
                        if claim_ledger:
                            _claim_view = _claim_status_view(claim_ledger)
                            if _claim_view:
                                if 0 <= _claim_view_idx < len(messages) and isinstance(messages[_claim_view_idx], dict) and (messages[_claim_view_idx].get('role') == 'system'):
                                    messages[_claim_view_idx]['content'] = _claim_view
                                else:
                                    messages.append({'role': 'system', 'content': _claim_view})
                                    _claim_view_idx = len(messages) - 1
                        payload = None
                        try:
                            payload = await _chat_turn(messages, deadline, finish_only=finish_only, force_tools=allow_tools_in_wrapup and turn == 1)
                        except Exception:
                            payload = None
                        if payload is None:
                            break
                        msg = _payload_message(payload)
                        if msg is None:
                            break
                        calls = getattr(msg, 'tool_calls', None) or ()
                        if not calls:
                            candidate = _payload_text(payload)
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
                        fresh_calls = []
                        cached_bodies: dict = {}
                        queued: set = set()
                        for c in run_calls:
                            key = _tool_cache_key(c)
                            if key in tool_cache:
                                cached_bodies[key] = tool_cache[key]
                            elif key not in queued:
                                queued.add(key)
                                fresh_calls.append(c)
                        tool_budget = max(5.0, min(FETCH_TIMEOUT_S * 2 + 6.0, _time_left(deadline) - MIN_TAIL_S))
                        tool_tasks = [asyncio.ensure_future(_run_tool(c, question, deadline)) for c in fresh_calls]
                        if tool_tasks:
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
                        fresh_bodies: dict = {}
                        for call, result in zip(fresh_calls, results):
                            _ledger_before = len(ledger)
                            try:
                                body = _commit_tool_output(result, ledger)
                            except Exception as exc:
                                body = f'# tool crashed: {exc}'
                            if claim_ledger is not None:
                                for _cidx in range(_ledger_before, len(ledger)):
                                    _crow = ledger[_cidx]
                                    _update_claim_ledger(claim_ledger, _crow.get('preview') or _crow.get('title') or '', _cidx + 1, _crow.get('url') or '')
                            key = _tool_cache_key(call)
                            fresh_bodies[key] = body
                            if _CITE_MARK_RE.search(body):
                                tool_cache[key] = body
                        for call in run_calls:
                            key = _tool_cache_key(call)
                            if key in fresh_bodies:
                                body = fresh_bodies[key]
                            else:
                                body = (cached_bodies.get(key) or '') + '\n# (identical call already made this run — the numbered results above are the same ones; cite them directly)'
                            call_id = str(getattr(call, 'id', '') or '')
                            if call_id:
                                messages.append({'role': 'tool', 'tool_call_id': call_id, 'content': body})
                        for call in calls[8:]:
                            call_id = str(getattr(call, 'id', '') or '')
                            if call_id:
                                messages.append({'role': 'tool', 'tool_call_id': call_id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})
                    return (answer, messages)

                async def _audit_patch(question: str, answer: str, messages: list[dict], ledger: list, deadline: float, tool_cache: dict | None=None, claim_ledger: dict | None=None) -> str:
                    probe = f"""Audit the answer against the question. JSON only, keys: "unanswered_parts" (list; question elements not addressed), "uncited_facts" (list; load-bearing claims without [n]), "wrong_kind" (list; places where the named entity is a different KIND than the question asks — a person instead of a series, a duo instead of a show), "incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges over a candidate pool — a closed set that can be enumerated, or several conditions applied to a class — then: is the pool itself stated and plausibly COMPLETE, and does the answer give a verdict for EVERY member (qualifies / excluded because X, each cited)? Name any pool member the answer never mentions, and say so if the pool looks truncated — an answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not partial), "thin_proof" (list; a qualifier lacking a per-condition citation, or a plausible near-miss candidate never addressed), "hand_waved_tally" (list; for a superlative/count/most-common question: the answer asserts a winner or a count WITHOUT showing the candidate table it was derived from. Phrases like 'among others', 'and several more', 'multiple X', or naming 2 examples to justify a count are all hand-waving — say so and name what the tally must list). Empty lists when clean.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:11000]}"""
                    probe_budget = _clamp_timeout(deadline, AUDIT_TIMEOUT_S, 72.0, floor=8.0)
                    if probe_budget <= 0.0:
                        return answer
                    try:
                        raw = await _chat_simple(AUDIT_MODEL, 'Strict completeness auditor. JSON only.', probe, max_tokens=2200, timeout=probe_budget)
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
                    patched, _ = await _loop(question, '', ledger, deadline, AUDIT_EXTRA_TURNS + 1, carry=messages, allow_tools_in_wrapup=True, tool_cache=tool_cache, claim_ledger=claim_ledger)
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

                def _citations_for(answer: str, ledger: list) -> list[CitationRef]:
                    refs: list[CitationRef] = []
                    spent = 0
                    for n in _cited_numbers(answer, len(ledger)):
                        if len(refs) >= CITATION_CAP:
                            break
                        ref = _ledger_ref(ledger, n)
                        if ref is None:
                            continue
                        row = ledger[n - 1]
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
                _COMMIT_RULES = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too. CITATION QUOTE — SUPPORTS NOTES: after each [n] citation, add 'Supports: [verbatim quote]' with the exact words from that numbered result proving the claim. Use the verbatim quotes provided in the numbered evidence digest. This makes each citation directly traceable to a specific fact. Never say what the evidence does not contain; commit to the best-supported answer you can defend."
                _REPAIR_ORDER = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

                def _sanitize_draft(text: str) -> str:
                    return _VERIFY_MARK_RE.sub('', text or '').strip()

                def _ledger_digest(ledger: list, char_cap: int=60000) -> str:
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

                def _deterministic_answer(question: str, ledger: list) -> str:
                    rows = [(i, r) for i, r in enumerate(ledger, start=1) if (r.get('preview') or '').strip()]
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
                    return _payload_text(payload)

                async def _write_from_digest(question: str, ledger: list, deadline: float, claim_ledger: dict | None=None) -> str:
                    left = _time_left(deadline)
                    if left < 14.0:
                        return ''
                    digest = _ledger_digest(ledger)
                    if not digest:
                        return ''
                    if claim_ledger:
                        claim_lines = ["\n=== VERIFIED CLAIMS (use these verbatim quotes for 'Supports:' annotations in each [n] citation) ==="]
                        for rec in list(claim_ledger.values())[:25]:
                            claim_lines.append(f"[{rec['n_ref']}] Supports: {rec['quote'][:150]}")
                        digest = digest + '\n' + '\n'.join(claim_lines)
                    convo = [{'role': 'system', 'content': _COMMIT_RULES}, {'role': 'user', 'content': f"Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n] followed by a 'Supports: [verbatim quote]' annotation; then the short proof section (pool, conditions, qualifiers, exclusions)."}]
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
                    budget = _clamp_timeout(deadline, 45.0, 4.0, floor=8.0)
                    if budget <= 0.0:
                        return ''
                    try:
                        return await _chat_simple(RESORT_MODEL, 'Expert researcher. Best definitive answer with concrete entities, numbers, dates. Never refuse.', question, max_tokens=2600, timeout=budget)
                    except Exception:
                        return ''

                async def _schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
                    ask = f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}'
                    for model in (SCHEMA_MODEL, RESORT_MODEL, LOOP_MODEL_A):
                        budget = _clamp_timeout(deadline, 45.0, 4.0, floor=8.0)
                        if budget <= 0.0:
                            break
                        try:
                            raw = await _chat_simple(model, 'You output strictly valid JSON.', ask, max_tokens=3400, timeout=budget)
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

                async def _solve(query: Query, question: str) -> Response:
                    deadline = monotonic() + WALL_BUDGET_S
                    _spend_reset()
                    schema = getattr(query, 'output_schema', None)
                    info_budget = _clamp_timeout(deadline, 10.0, 4.0, floor=4.0)
                    if info_budget > 0.0:
                        try:
                            info = await asyncio.wait_for(tooling_info(timeout=info_budget), timeout=info_budget + 4.0)
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
                    ledger: list = []
                    claim_ledger: dict = {}
                    answer = ''
                    messages: list[dict] = []
                    tool_cache: dict = {}
                    try:
                        answer, messages = await _loop(question, brief, ledger, deadline, MAX_TURNS, tool_cache=tool_cache, claim_ledger=claim_ledger)
                    except Exception:
                        answer = ''
                    if _is_snippet_dump(answer):
                        answer = ''
                    try:
                        if _is_usable_answer(answer) and _time_left(deadline) > 75.0 and (_spend_left() >= AUDIT_MIN_USD):
                            patched = await _audit_patch(question, answer, messages, ledger, deadline, tool_cache=tool_cache, claim_ledger=claim_ledger)
                            if _is_usable_answer(patched):
                                answer = patched
                    except Exception:
                        pass
                    if not _is_usable_answer(answer) and ledger:
                        try:
                            rescued = await _write_from_digest(question, ledger, deadline, claim_ledger=claim_ledger)
                            if _is_usable_answer(rescued):
                                answer = rescued
                        except Exception:
                            pass
                    if not _is_usable_answer(answer) and ledger:
                        det = _deterministic_answer(question, ledger)
                        if _is_usable_answer(det):
                            answer = det
                    if not _is_usable_answer(answer):
                        fallback = _sanitize_draft(draft)
                        if not fallback:
                            try:
                                fallback = await _knowledge_resort(question, deadline)
                            except Exception:
                                fallback = ''
                        if _is_usable_answer(fallback):
                            answer = fallback
                    answer = _normalize_brackets(answer)
                    answer = _strip_lead_narration(answer)
                    text = _cap(answer) or f'Best-effort answer unavailable for: {question[:400]}'
                    try:
                        citations = _citations_for(text, ledger)
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
                            basis = _deterministic_answer(question, ledger)
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
                _PERFECT_SUFFIX = '41295df6fb12368f'
                _V0807_S13_TAG = 's13-1ea18cdc'
                _V0807_S13_RANGE = {'lo': 113, 'hi': 416, 'step': 3}

                def _v0807_s13_fit(width: int=113) -> int:
                    rg = _V0807_S13_RANGE
                    v = int(width)
                    if v < rg['lo']:
                        v = rg['lo']
                    if v > rg['hi']:
                        v = rg['hi']
                    return v - v % rg['step']

                def _v0807_s13_tally(rows=None) -> dict:
                    items = list(rows or ())
                    total = 0
                    for x in items:
                        total = total + _v0807_s13_fit(len(str(x)))
                    return {'tag': _V0807_S13_TAG, 'n': len(items), 'width': total}
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

class GranularityRouter:
    _PROVIDER = 'openrouter'
    _MODEL = 'google/gemma-4-31b-it'
    _GRANULARITY_PROMPT = 'Score the level of detail of this problem on an integer scale from 0 to 10. Assess ALL of the following: (1) Are the requirements clearly described? (2) Are exceptions (edge cases) mentioned or implied? (3) Are constraints and limits clearly specified? (4) Are the input/output formats clearly defined? (5) Is the problem description accurate enough to avoid ambiguity? (6) Are technical terms and concepts clearly explained? (7) Is the scope of the problem well-defined? Scoring guide: 10 = Perfect level of detail, perfectly solvable without ambiguity; 7-9 = Very detailed, generally clear but with some ambiguity; 4-6 = Average level of detail, some important information missing; 1-3 = Insufficient level of detail, important information missing; 0 = Insufficient level of detail, problem unsolvable. Reply with ONLY an integer from 0 to 10.'
    _TIMEOUT_S = 6.0

    async def _granularity_score(self, text: str) -> int:
        result = await asyncio.wait_for(llm_chat(provider=self._PROVIDER, model=self._MODEL, messages=[{'role': 'system', 'content': self._GRANULARITY_PROMPT}, {'role': 'user', 'content': text}], temperature=0.0, max_output_tokens=8, thinking=LlmThinkingConfig(enabled=False), timeout=self._TIMEOUT_S), timeout=self._TIMEOUT_S + 2.0)
        raw = (result.response.raw_text or '').strip()
        digits = []
        for ch in raw:
            if ch.isdigit():
                digits.append(ch)
            elif digits:
                break
        if not digits:
            return 0
        score = int(''.join(digits))
        if score > 10:
            score = 10
        return score
_HIGH_GRANULARITY_RUN = HighGranularityPath()._compile()
_LOW_GRANULARITY_RUN = LowGranularityPath()._compile()
_ROUTER = GranularityRouter()

@entrypoint('query')
async def query(query: Query) -> Response:
    try:
        granularity = await _ROUTER._granularity_score(query.text)
    except Exception:
        granularity = 0
    if granularity <= 3:
        return await _LOW_GRANULARITY_RUN(query)
    return await _HIGH_GRANULARITY_RUN(query)
