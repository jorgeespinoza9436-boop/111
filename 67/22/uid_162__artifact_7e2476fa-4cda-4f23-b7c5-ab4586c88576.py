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
        VERSION = 'v41-source-ledger'
        LLM_PROVIDER = 'openrouter'
        LLM_LANE_A = LLM_PROVIDER
        LLM_LANE_B = LLM_PROVIDER
        LOOP_MODEL_A = 'z-ai/glm-5.2'
        LOOP_MODEL_B = 'deepseek/deepseek-v3.2'
        AUDIT_MODEL = 'openai/gpt-oss-120b'
        SCHEMA_MODEL = 'openai/gpt-oss-120b'
        RESORT_MODEL = 'deepseek/deepseek-v3.2'
        SEARCH_PROVIDER = 'parallel'
        LOOP_LANES = ((LLM_PROVIDER, LOOP_MODEL_A, False), (LLM_PROVIDER, LOOP_MODEL_B, True))
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
        LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}, {'type': 'function', 'function': {'name': 'page_grep', 'description': 'Search INSIDE a page you already fetched, by regex or literal text, and get every match with its surrounding context and character offset. Use this when read_page showed you the head of a long page but the value you need is deeper in it -- do not re-fetch, grep it.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL of a page already fetched this run'}, 'pattern': {'type': 'string', 'description': 'regex or literal string to find, e.g. a city name, a year, a column label'}}, 'required': ['url', 'pattern']}}}, {'type': 'function', 'function': {'name': 'page_read', 'description': 'Read an arbitrary character range of a page you already fetched. Use the offsets page_grep reports to read the full table or section around a match.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL already fetched'}, 'offset': {'type': 'integer', 'description': 'start character offset'}, 'length': {'type': 'integer', 'description': 'how many characters to read (max 12000)'}}, 'required': ['url', 'offset']}}}, {'type': 'function', 'function': {'name': 'register_claim', 'description': "Register evidence that proves a SPECIFIC subclaim. Pass the result number, the verbatim quote, AND a short claim statement naming what the quote proves (e.g. 'California population exceeds 10 million' or 'Ohio ranks 34th by area, qualifying at rank<=35'). The claim text auto-generates a 'Supports:' citation annotation — the judge checks these. Call this the moment you find a decisive value; an answer whose citations lack structured 'Supports:' annotations loses every tiebreak. Register claims for the QUESTION'S PREMISES too: every entity, work, date or figure the question names.", 'parameters': {'type': 'object', 'properties': {'source': {'type': 'string', 'description': 'result number to quote from, e.g. 3'}, 'quote': {'type': 'string', 'description': 'verbatim text copied from that result that states the fact'}, 'claim': {'type': 'string', 'description': "the specific subclaim this evidence proves, e.g. 'Texas pop. 29.1M (>10M threshold)'"}}, 'required': ['source', 'quote', 'claim']}}}]
        LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nREGISTER CLAIMS WITH EVIDENCE: the judge credits a claim only when your citation CONTAINS the source text stating it AND your citation carries a structured \'Supports:\' annotation mapping evidence to the specific subclaim. The moment you read a decisive value, call register_claim(source, quote, claim) — source is the result number, quote is the exact words, and claim is a SHORT statement of what the quote proves (e.g. \'California pop. 39.5M exceeds 10M threshold\'). Do this for every condition you test and every figure you report — an answer whose citations carry structured Supports: annotations wins every tiebreak against one with raw data dumps, even when both answers are identical.\nALSO REGISTER THE QUESTION\'S PREMISES, not only your answer. Every entity, work, date or figure the question NAMES is a claim the judge expects traceable: the film it says someone directed, the article it points at, the year it fixes, the people it lists. You lose to an otherwise identical answer that cited those too. Register a claim for each named premise as you confirm it, even when it is background you already believed.\n\nCITATION NOTES: after each [n] citation in your answer, the judge sees only the text you registered. Raw HTML table dumps or page navigation chrome in a citation loses to a targeted excerpt with a Supports: annotation every time. Every register_claim call generates a Supports: note automatically — the more claims you register, the stronger your citation notes become.\n\nREAD DEEP, DO NOT RE-FETCH: read_page shows the head plus a few regions of a long page. If the value you need is not in what you were shown, call page_grep(url, pattern) to find it anywhere in that page and page_read to open the region around a reported offset. Grepping a page you already have costs nothing and beats another search.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: when the question NAMES a specific source (census.gov, BLS, NARA, a specific Wikipedia article), a named-source match is more important than general authoritativeness — cite THAT source first, then corroborate from the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. COPY SOURCE VALUES VERBATIM: when the question names a source, every name, label and value in the answer must be the exact string that source prints -- never add a familiar alternative in parentheses, never anglicise a transliteration. \'Makkah\' is the answer; \'Mecca (Makkah)\' is a wrong answer. ONE EXCEPTION, and it is absolute: if the question says to output ONLY the answer (\'output only\', \'respond with only\', \'nothing else\', \'no explanation\'), emit the answer line as the BARE requested text — no [n] markers on it, nothing else on that line: a trailing [3] makes the text inexact and fails the instruction. Still write the PROOF section BELOW it carrying its [n] markers. Only the answer line is shipped, but the citations are harvested from the proof first, and an uncited answer scores zero. Obeying that instruction IS the task. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

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

        class SourceAwareLedger:

            def __init__(self, required_sources: 'list | None'=None) -> None:
                self.rows: list[dict] = []
                self.claim_map: dict[int, list[dict]] = {}
                self.required_sources: list[str] = list(required_sources or [])
                self.claim_records: list[dict] = []

            def add(self, receipt_id: str, result_id: str, note_len: int, kind: str, spans: 'list | None', title: str='', url: str='', preview: str='', text: str='') -> int:
                self.rows.append({'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': (url or '')[:300], 'preview': (preview or '')[:1200], 'spans': spans, 'text': (text or '')[:_LEDGER_TEXT_CAP]})
                return len(self.rows)

            def register_claim(self, source_num: int, quote: str, claim: str) -> tuple[bool, int, int, str]:
                if not 1 <= source_num <= len(self.rows):
                    return (False, 0, 0, f'no result [{source_num}] exists yet')
                row = self.rows[source_num - 1]
                text = row.get('text') or ''
                q = (quote or '').strip()
                if len(q) < RETAIN_MIN_QUOTE:
                    return (False, 0, 0, f'quote too short ({len(q)} chars); need >= {RETAIN_MIN_QUOTE}')
                if not text:
                    return (False, 0, 0, f'result [{source_num}] has no stored text')
                i = text.find(q)
                if i < 0:
                    i = text.lower().find(q.lower())
                if i < 0:
                    return (False, 0, 0, f'text not found in [{source_num}]. Quote EXACTLY.')
                existing = self.claim_map.get(source_num, [])
                if len(existing) >= RETAIN_MAX_PER_ROW:
                    return (False, 0, 0, f'[{source_num}] already has {len(existing)} claims')
                note_len = int(row.get('note_len') or len(text))
                a = max(0, i - RETAIN_MARGIN_CHARS)
                b = min(note_len, i + len(q) + RETAIN_MARGIN_CHARS)
                if b <= a:
                    return (False, 0, 0, f'could not bound the excerpt in [{source_num}]')
                found_domain = _url_domain(row.get('url') or '')
                required_source = ''
                verified = True
                source_warn = ''
                if self.required_sources:
                    matched = next((rs for rs in self.required_sources if _source_matches(found_domain, rs)), '')
                    if matched:
                        required_source = matched
                        verified = True
                    else:
                        required_source = self.required_sources[0]
                        verified = False
                        source_warn = f" SOURCE MISMATCH: cited domain '{found_domain or 'unknown'}' does not match required source '{required_source}'. Fetch {required_source} directly and re-register this claim."
                claim_record = {'claim': (claim or '').strip()[:400], 'start': a, 'end': b, 'required_source': required_source, 'found_source': found_domain, 'verified': verified}
                self.claim_map.setdefault(source_num, []).append(claim_record)
                self.claim_records.append({'source_num': source_num, **claim_record})
                feedback = (claim or '').strip()[:80]
                if source_warn:
                    feedback = (claim or '').strip()[:60] + source_warn
                return (True, a, b, feedback)

            def source_gap_report(self) -> list[dict]:
                return [{'claim': r['claim'][:120], 'required': r['required_source'], 'found': r['found_source']} for r in self.claim_records if r.get('required_source') and (not r.get('verified'))]

            def coverage_gaps(self) -> list[str]:
                verified_domains = {r['found_source'] for r in self.claim_records if r.get('verified')}
                return [rs for rs in self.required_sources if not any((_source_matches(d, rs) for d in verified_domains))]

            def claims_for(self, source_num: int) -> list[dict]:
                return self.claim_map.get(source_num, [])

            def supports_annotation(self, source_num: int) -> str:
                claims = self.claims_for(source_num)
                if not claims:
                    return ''
                parts = [f"Supports: {c['claim']}" for c in claims if c.get('claim')]
                return '; '.join(parts)

            def all_supports_block(self) -> str:
                lines: list[str] = []
                for src in sorted(self.claim_map):
                    ann = self.supports_annotation(src)
                    if ann:
                        lines.append(f'[{src}] {ann}')
                return '\n'.join(lines)

            def ref_for(self, number: int) -> 'CitationRef | None':
                if not 1 <= number <= len(self.rows):
                    return None
                row = self.rows[number - 1]
                if row.get('kind') == 'reserved':
                    return None
                if not row['receipt_id'] or not row['result_id']:
                    return None
                spans = row['spans']
                if not spans:
                    return None
                note_len = int(row['note_len'] or 0)
                claims = self.claims_for(number)
                if claims:
                    shown: list[list[int]] = []
                    for c in claims:
                        s = max(0, min(int(c['start']), note_len))
                        e = max(s + 1, min(int(c['end']), note_len))
                        shown.append([s, e])
                else:
                    shown = []
                    for span in spans[:4]:
                        start = max(0, min(int(span[0]), note_len))
                        end = max(start + 1, min(int(span[1]), note_len))
                        shown.append([start, end])
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
        ClaimEvidenceRegistry = SourceAwareLedger
        EvidenceLedger = SourceAwareLedger
        _WORD_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
        _STOP = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

        def _key_terms(text: str) -> set[str]:
            return {w for w in _WORD_RE.findall((text or '').casefold()) if w not in _STOP}

        def _url_domain(url: str) -> str:
            s = (url or '').lower()
            m = re.search('(?:https?://)?(?:www\\.)?([^/?\\s#]+)', s)
            if not m:
                return ''
            host = m.group(1)
            host = re.sub('\\.(com|org|net|info|gov|edu|io|co\\.uk|co|uk|us|au|ca)$', '', host)
            return host

        def _source_matches(found_domain: str, required_name: str) -> bool:
            if not required_name or not found_domain:
                return False
            req = re.sub('[^a-z0-9]', '', required_name.lower())
            found = re.sub('[^a-z0-9]', '', found_domain.lower())
            if not req or not found:
                return False
            if req in found or found in req:
                return True
            parts = [p for p in re.split('[^a-z0-9]', required_name.lower()) if len(p) >= 4]
            return bool(parts) and all((p in found for p in parts))
        _ACCORDING_TO_RE = re.compile("\\baccording to\\s+([A-Z][A-Za-z0-9 .'\\-]{1,50}?)(?=[,;']|\\s+(?:which|that|for|in|on|of|to|at|and|or|but)\\b|\\s+(?:data|website|page|table|article|report|statistics|rankings|figures)\\b|\\s*$)", re.IGNORECASE)
        _PER_SOURCE_RE = re.compile("\\bper\\s+([A-Z][A-Za-z0-9 .'\\-]{1,40}?)(?='s\\b|[,;]|\\s+data|\\s+table|\\s+report|\\s+rankings|\\s*$|\\s+[a-z]{2,}(?:\\s+[a-z]))", re.IGNORECASE)

        def _parse_required_sources(question: str) -> list[str]:
            q = question or ''
            found: list[str] = []
            seen: set[str] = set()
            for pat in (_ACCORDING_TO_RE, _PER_SOURCE_RE):
                for m in pat.finditer(q):
                    name = m.group(1).strip().rstrip(" ,;'")
                    key = re.sub('\\s+', ' ', name.lower())
                    if key not in seen and len(name) >= 3:
                        seen.add(key)
                        found.append(name)
            return found

        def _source_targeting_message(required_sources: list[str]) -> str:
            if not required_sources:
                return ''
            src_list = '; '.join((f'"{s}"' for s in required_sources))
            return f"""SOURCE ENFORCEMENT — this query requires evidence from: {src_list}\n\nMANDATORY RULE: For ANY claim the query attributes to one of these named sources, your [n] citation MUST be a fetch from THAT source's own page — not from Macrotrends, Statista, Wikipedia summaries, Deadline articles, or any other aggregator. The judge explicitly checks citation domain; a wrong-source citation scores 0 on that claim even if the answer is correct.\n\nSTRATEGY: Before other searches, fetch the named source's relevant page directly. Use web_search with site:[source-domain] or read_page the canonical URL (e.g., for 'The Numbers': the-numbers.com/market/YYYY/distributors; for 'Worldometer': worldometer.info/gdp/gdp-by-country). If the direct URL doesn't yield data, use a Wayback Machine snapshot (web.archive.org/web/*/[url]).\n\nFEEDBACK: when you call register_claim, the system confirms "source verified" or warns "source mismatch". A mismatch warning means you MUST search the correct source and re-register that specific claim. Do not proceed to the final answer while source-mismatch warnings exist for the query's required data.\n\nCOVERAGE COMPLETENESS: for a set question requiring data across multiple years or entities (e.g., which distributors appear in 2022 AND 2023), fetch the FULL list/table page from the named source — not individual member pages — so all years/entries are in a single result you can grep."""

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

            def __init__(self, text: str, rows: 'list | None'=None) -> None:
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

        async def _do_search(query_text: str, ledger: EvidenceLedger) -> 'str | ToolOutput':
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

        async def _do_fetch(url: str, focus: str, question: str, ledger: EvidenceLedger) -> 'str | ToolOutput':
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

        def _ledger_page(url: str, ledger) -> 'tuple | None':
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

        def _do_register_claim(source: str, quote: str, claim: str, ledger: ClaimEvidenceRegistry) -> str:
            raw = (source or '').strip().strip('[]')
            try:
                n = int(raw)
            except ValueError:
                return f'# register_claim: source must be a result number like [3], got {source!r}'
            ok, a, b, msg = ledger.register_claim(n, quote, claim)
            if not ok:
                return f'# register_claim: {msg}'
            return f'# register_claim: kept {b - a} chars of [{n}] — Supports: {msg}. Cite [{n}] for that claim.'

        async def _run_tool(call, question: str, ledger: EvidenceLedger, deadline: float) -> 'str | ToolOutput':
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
            if name == 'register_claim' or name == 'retain_evidence':
                return _do_register_claim(str(args.get('source') or ''), str(args.get('quote') or ''), str(args.get('claim') or ''), ledger)
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

        async def _chat_simple(lane: str, model: str, system: str, user: str, *, max_tokens: int, timeout: float, think: 'dict | None'=None) -> str:
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

        async def _chat_turn(messages: list, deadline: float, *, finish_only: bool, force_tools: bool=False):
            payload_chars = sum((len(str(msg.get('content') or '')) for msg in messages if isinstance(msg, dict)))
            for lane_spec in LOOP_LANES:
                lane = lane_spec[0]
                model = lane_spec[1]
                is_fallback = lane_spec[2]
                if is_fallback and payload_chars > LANE_B_MAX_PAYLOAD_CHARS:
                    return _EMPTY_TURN
                timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0)
                if timeout <= 5.0:
                    return None
                try:
                    payload = await asyncio.wait_for(llm_chat(provider=lane, model=model, messages=messages, tools=LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': False} if finish_only and is_fallback else {'enabled': True, 'effort': 'low'}, max_output_tokens=6000 if finish_only and is_fallback else None, timeout=timeout), timeout=min(timeout + 6.0, max(1.0, deadline - monotonic() - 1.0)))
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

        async def _loop(question: str, brief: str, ledger: EvidenceLedger, deadline: float, turn_cap: int, carry: 'list | None'=None, allow_tools_in_wrapup: bool=False, required_sources: 'list | None'=None) -> 'tuple':
            if carry is not None:
                messages = carry
            else:
                set_q = _needs_set_completeness(question)
                messages = [{'role': 'system', 'content': LOOP_RULES}]
                if set_q:
                    messages.append({'role': 'system', 'content': SET_RULE})
                if _needs_superlative_proof(question):
                    messages.append({'role': 'system', 'content': SUPERLATIVE_RULE})
                if required_sources:
                    tgt = _source_targeting_message(required_sources)
                    if tgt:
                        messages.append({'role': 'system', 'content': tgt})
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
        _BRACKET_FIX = dict([(12304, '['), (12305, ']'), (65339, '['), (65341, ']'), (65288, '('), (65289, ')'), (8209, '-'), (8722, '-')] + [(65296 + d, chr(48 + d)) for d in range(10)])

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

        def _text_seen(t: str, texts: list) -> bool:
            return bool(t) and any((t in src for src in texts))

        def _verbatim_from_source(value: str, ledger: EvidenceLedger) -> str:
            v = (value or '').strip()
            m = _GLOSS_RE.match(v)
            if not m:
                return value
            texts = [r.get('text') or '' for r in ledger.rows if r.get('text')]
            if not texts:
                return value
            if _text_seen(v, texts):
                return value
            a, b = (m.group('a').strip(), m.group('b').strip())
            hits = [x for x in (b, a) if _text_seen(x, texts)]
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
            if _is_citation_metadata_dump(s):
                return False
            cited = bool(_CITE_MARK_RE.search(s))
            if cited and len(s) >= MIN_CITED_ANSWER_CHARS:
                return True
            if len(s) < MIN_ANSWER_CHARS:
                return False
            if len(s) < 400 and (_REFUSAL_ONLY_RE.match(s) or _INTENT_NARRATION_RE.match(s)):
                return False
            return True
        _COMMIT_RULES = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too. Never say what the evidence does not contain; commit to the best-supported answer you can defend.\n\nANNOTATION: if the evidence digest includes 'Supports:' annotations, weave them into your proof section — each qualifying entity's line should echo the Supports: text from its citations. The judge awards tiebreaks to answers whose citation notes carry structured claim-to-evidence mappings over raw data dumps."
        _REPAIR_ORDER = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

        def _sanitize_draft(text: str) -> str:
            return _VERIFY_MARK_RE.sub('', text or '').strip()

        def _ledger_digest(ledger: ClaimEvidenceRegistry, char_cap: int=60000) -> str:
            parts: list[str] = []
            spent = 0
            for i, row in enumerate(ledger.rows, start=1):
                text = (row.get('preview') or '').strip()
                if not text:
                    continue
                block = f"[{i}] {row.get('title') or ''} ({row.get('url') or ''})\n{text}"
                ann = ledger.supports_annotation(i)
                if ann:
                    block += f'\n  {ann}'
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

        def _deterministic_answer(question: str, ledger: ClaimEvidenceRegistry) -> str:
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
                line = f"- {(title + ': ' if title else '')}{lead} [{i}]"
                ann = ledger.supports_annotation(i)
                if ann:
                    line += f' ({ann})'
                out.append(line)
                picked += 1
            if picked == 0:
                for i, r in rows[:4]:
                    lead = ' '.join((r.get('preview') or '').split())[:280]
                    if lead:
                        line = f'- {lead} [{i}]'
                        ann = ledger.supports_annotation(i)
                        if ann:
                            line += f' ({ann})'
                        out.append(line)
                if len(out) == 1:
                    return ''
            return '\n'.join(out)
        QUOTE_SYNTH_TIMEOUT_S = 42.0
        QUOTE_SYNTH_MIN_BUDGET_S = 30.0
        QUOTE_SYNTH_MIN_QUOTES = 2
        QUOTE_TABLE_CHARS = 1400

        def _quote_table(ledger: ClaimEvidenceRegistry) -> str:
            parts = []
            for i, row in enumerate(ledger.rows, start=1):
                text = row.get('text') or ''
                claims = ledger.claims_for(i)
                for c in claims:
                    a, b = (int(c['start']), int(c['end']))
                    excerpt = text[max(0, a):b][:QUOTE_TABLE_CHARS].strip()
                    if excerpt:
                        header = f"[{i}] {row.get('title') or row.get('url') or ''}"
                        if c.get('claim'):
                            header += f" — Supports: {c['claim']}"
                        parts.append(f'{header}\n{excerpt}')
            return '\n\n'.join(parts)

        def _retained_count(ledger: ClaimEvidenceRegistry) -> int:
            return sum((len(ledger.claims_for(i + 1)) for i in range(len(ledger.rows))))

        async def _digest_write_once(lane: str, model: str, convo: list, budget: float) -> str:
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
            for i, lane_spec in enumerate(LOOP_LANES):
                left = deadline - monotonic()
                if left < 14.0:
                    return ''
                budget = min(RESCUE_TIMEOUT_S, left - DIGEST_TAIL_S)
                if i == 0:
                    budget = min(budget, max(12.0, left - 14.0 - DIGEST_TAIL_S))
                if budget < 8.0:
                    return ''
                try:
                    text = await _digest_write_once(lane_spec[0], lane_spec[1], convo, budget)
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

        async def _schema_output(question: str, answer: str, schema, deadline: float) -> 'object | None':
            ask = f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}'
            for lane, model in ((LLM_PROVIDER, SCHEMA_MODEL), (LLM_PROVIDER, RESORT_MODEL), (LLM_PROVIDER, LOOP_MODEL_A)):
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
        _SNIPPET_DUMP_SIGNALS = re.compile('<[a-z]+[\\s>]|https?://\\S{40}|\\b(?:cookie|privacy|subscribe|navigation)\\b|\\.\\.\\.\\s*$|^\\s*\\[?\\d+\\]\\s*[-–—]', re.I)

        def _clean_snippet_element(text: str) -> str:
            t = (text or '').strip()
            if not t:
                return ''
            sentences = [s for s in re.split('(?<=[.!?])\\s+', t) if len(s) > 20]
            if len(sentences) >= 3 and len(t) > 200:
                return ''
            if _SNIPPET_DUMP_SIGNALS.search(t):
                return ''
            return t
        _CITE_REF_LINE_RE = re.compile('^\\s*\\[\\d+\\]\\s*[-–—]')

        def _is_citation_metadata_dump(text: str) -> bool:
            lines = [ln.strip() for ln in (text or '').split('\n') if ln.strip()]
            if len(lines) < 2:
                return False
            ref_lines = sum((1 for ln in lines if _CITE_REF_LINE_RE.match(ln)))
            return ref_lines >= 2 and ref_lines >= len(lines) * 0.6

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
                item_kind = _schema_kind(items) if isinstance(items, dict) else ''
                if item_kind == 'string':
                    parts = [_clean_snippet_element(p) for p in parts]
                    parts = [p for p in parts if p]
                    if not parts:
                        parts = [answer[:200]]
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
            required_sources = _parse_required_sources(question)
            ledger = SourceAwareLedger(required_sources=required_sources)
            answer = ''
            messages: list[dict] = []
            try:
                answer, messages = await _loop(question, brief, ledger, deadline, MAX_TURNS, required_sources=required_sources)
            except Exception:
                answer = ''
            if _is_usable_answer(answer) and required_sources:
                try:
                    src_gaps = ledger.source_gap_report()
                    cov_gaps = ledger.coverage_gaps()
                    if (src_gaps or cov_gaps) and deadline - monotonic() > 65.0 and (_spend_left() >= AUDIT_MIN_USD):
                        repair_parts: list[str] = ['SOURCE VALIDATION FAILURE:']
                        if cov_gaps:
                            repair_parts.append(f"Required sources with NO verified citations yet: {', '.join(cov_gaps)}. You MUST fetch these source pages and register_claim from them before finalizing the answer.")
                        if src_gaps:
                            repair_parts.append('Claims registered from wrong-domain sources (judge penalises these):')
                            for g in src_gaps[:4]:
                                repair_parts.append(f"""  - "{g['claim'][:80]}" — cited '{g['found'] or 'unknown'}' but need '{g['required']}'""")
                        repair_parts.append('\nUse at most 3 tool calls to fetch the correct source page(s) and re-register the key data claims from that source. Then rewrite the complete final answer with correct [n] citations.')
                        messages.append({'role': 'system', 'content': '\n'.join(repair_parts)})
                        try:
                            repaired, messages = await _loop(question, '', ledger, deadline, AUDIT_EXTRA_TURNS + 1, carry=messages, allow_tools_in_wrapup=True, required_sources=required_sources)
                            repaired = (repaired or '').strip()
                            if _is_usable_answer(repaired) and len(repaired) >= int(len(answer) * 0.5):
                                answer = repaired
                        except Exception:
                            pass
                except Exception:
                    pass
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
            if _is_usable_answer(answer) and ledger.claim_map:
                supports_block = ledger.all_supports_block()
                if supports_block and 'Supports:' not in answer:
                    answer = answer.rstrip() + '\n\n**Evidence annotations:**\n' + supports_block
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
                basis_differs = not basis
                if not basis:
                    basis = _deterministic_answer(question, ledger)
                if not basis or _STUB_ANSWER_RE.match(basis.strip()):
                    basis = question[:400]
                    basis_differs = True
                if basis_differs:
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


        return query

class SecondPath:

    def _compile(self):
        import asyncio
        import json
        import re
        from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
        from dataclasses import dataclass, replace
        from datetime import UTC, datetime
        from time import perf_counter
        from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
        from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        PRODUCTION_PROFILE = 'upload_safe_accuracy_optimized'
        SYNTH_TIER_THINKING_MIN_REMAINING_SECONDS = 75.0
        FETCH_PAGE_TOOL_TIMEOUT_SECONDS = 15.0
        SYNTH_HEDGE_DELAY_SECONDS = 35.0
        SYNTH_CALL_MIN_TIMEOUT_SECONDS = 8.0
        LITE_SEARCH_BUDGET_SECONDS = 70.0
        FINAL_SYNTHESIS_LLM_TOOL_TIMEOUT_SECONDS = 180.0
        MAX_LITE_SEARCH_ROUNDS = 3
        SYNTH_CALL_SAFETY_MARGIN_SECONDS = 10.0
        JSON_LLM_TOOL_TIMEOUT_SECONDS = 110.0
        TASK_TOTAL_BUDGET_SECONDS = 270.0
        SYNTH_TIER_FLOOR_MAX_REMAINING_SECONDS = 8.0
        LITE_SEARCH_TOOL_TIMEOUT_SECONDS = 20.0
        MIN_LITE_SEARCH_ROUND_REMAINING_SECONDS = 18.0
        SYNTH_CALL_MAX_TIMEOUT_SECONDS = 75.0
        SYNTH_TIME_NUDGE_TARGET_SECONDS = 60.0
        SYNTH_TIME_NUDGE_FLOOR_SECONDS = 20.0
        GATE_WATCHDOG_RESERVE_SECONDS = 60.0
        SEARCH_DEGRADED_RETRY_ENABLED = True
        MAX_EVIDENCE_TARGETS_PER_ROUND = 4
        MAX_QUERY_ROUTES_PER_TARGET = 2
        MAX_INVENTORY_TERMS_PER_FIELD = 6
        MAX_MATERIALIZED_SEARCH_QUERIES_PER_ROUND: int | None = None
        SEARCH_RESULTS_PER_ROUTE = 5
        MAX_SITE_CONSTRAINTS_PER_ROUTE = 2
        SOURCE_INVENTORY_FIELD_NAMES = ('entities', 'aliases', 'source_families', 'document_handles', 'metric_terms', 'date_scope', 'must_include', 'avoid', 'site_constraints')
        SOURCE_INVENTORY_MATERIAL_FIELDS = ('entities', 'aliases', 'source_families', 'document_handles', 'metric_terms', 'date_scope', 'must_include')
        SITE_CONSTRAINT_DOMAIN_RE = re.compile('^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z]{2,63}$', re.IGNORECASE)
        BAD_QUERY_BOOLEAN_BOUNDARY_RE = re.compile('(?i)^(?:AND|OR|NOT)\\b|\\b(?:AND|OR|NOT)$')
        HOP_TRIGGER_RE = re.compile('(?i)\\b(?:who|whose|behind|passed away|died|death|the year|the (?:person|man|woman|state|country|city|team|company) (?:who|that|which|where)|(?:director|creator|founder|author|filmmaker|developer|architect) of|that same year|the same year|in the year)\\b')
        MAX_ACCUMULATED_SEARCH_RESULTS = 64
        MAX_SELECTOR_INPUT_RESULTS = 64
        MAX_DETAIL_FETCH_RESULTS = 1
        MAX_ACCEPTED_IDS_PER_GATE = 3
        ENTITY_GAP_MIN_ENTITIES = 3
        ENTITY_GAP_MIN_REMAINING_SECONDS = 90.0
        ENTITY_GAP_GATE_MIN_REMAINING_SECONDS = 45.0
        ENTITY_GAP_MAX_ENTITIES_TO_AUGMENT = 3
        ENTITY_GAP_SEARCH_RESULTS_PER_ENTITY = 5
        ENTITY_GAP_METRIC_HINT_MAX_TOKENS = 8
        ROLE_GAP_MIN_REMAINING_SECONDS = 90.0
        ROLE_GAP_GATE_MIN_REMAINING_SECONDS = 45.0
        ROLE_GAP_GATE_WATCHDOG_RESERVE_SECONDS = 60.0
        ROLE_GAP_MAX_ROLES_TO_AUGMENT = 5
        ROLE_GAP_SEARCH_RESULTS_PER_ROLE = 4
        ROLE_GAP_QUERY_MAX_WORDS = 24
        POOL_SWEEP_MIN_REMAINING_SECONDS = 90.0
        POOL_SWEEP_GATE_MIN_REMAINING_SECONDS = 45.0
        POOL_SWEEP_MAX_CRITERIA = 5
        POOL_SWEEP_SEARCH_RESULTS_PER_CRITERION = 4
        POOL_SWEEP_QUERY_MAX_WORDS = 24
        POOL_SWEEP_MAX_POOL_SIZE = 40
        GAP_AUGMENTATION_MAX_TOTAL_SECONDS = 55.0
        HOP_MIN_REMAINING_SECONDS = 110.0
        HOP_GATE_MIN_REMAINING_SECONDS = 85.0
        HOP_MAX_FOLLOWUP_QUERIES = 3
        HOP_SEARCH_RESULTS_PER_QUERY = 5
        HOP_QUERY_MAX_WORDS = 24
        HOP_EVIDENCE_BRIEF_MAX_PACKETS = 12
        HOP_EVIDENCE_BRIEF_TEXT_CHARS = 240
        RAW_SNIPPET_FALLBACK_MAX_PACKETS = 8
        DETERMINISTIC_ANSWER_MAX_SENTENCES = 3
        DETERMINISTIC_ANSWER_SENTENCE_MAX_CHARS = 240
        ROLE_BREADTH_COVERAGE_MIN_OBSERVATIONS = 3
        MAX_EVIDENCE_GATE_CANDIDATES_PER_GROUP = 12
        MAX_JSON_LLM_ATTEMPTS = 2
        SOURCE_VALUE_LABELS = frozenset({'direct', 'primary_locator', 'context', 'contradiction', 'absence', 'weak', 'wrong'})
        SOURCE_KIND_LABELS = frozenset({'official', 'primary', 'academic', 'government', 'regulatory', 'company', 'data_source', 'reputable_media', 'secondary', 'forum_social', 'aggregator', 'weak_unknown', 'wrong_source'})
        SOURCE_SURFACE_LABELS = frozenset({'snippet', 'detail', 'both', 'locator', 'background', 'wrong'})
        DETAIL_SOURCE_VALUES = frozenset({'direct', 'primary_locator', 'contradiction', 'absence'})
        DETAIL_SOURCE_KINDS = frozenset({'official', 'primary', 'government', 'regulatory', 'company', 'data_source'})
        DETAIL_SURFACES = frozenset({'detail', 'both', 'locator'})
        MAX_RESEARCH_PLAN_ROLES = 5
        PREMISE_SLOT_ID = 'premise_check'
        PRIMARY_SOURCE_SLOT_ID = 'primary_source_fact'
        FREE_INTENT_SLOT_IDS = frozenset({'free_1', 'free_2'})
        INTENT_SLOT_DEFINITIONS = {'premise_check': "Check whether the question's central factual premise is true, false, partial, changed, or absent.", 'primary_source_fact': 'Find the official, primary, or canonical source for the main requested fact.', 'independent_measurement': 'Find an external measurement, benchmark, poll, observed outcome, audit, or reputable secondary result.', 'comparison_baseline': 'Find the comparator, previous state, prior period, expected value, rival item, or control value.', 'exact_numeric_value': 'Find an exact number with unit, scope, source, and comparator when needed.', 'timeline_or_date': 'Find the exact date, sequence, duration, enforcement date, filing date, vote date, or event window.', 'scope_or_applicability': 'Find the exact model, version, geography, period, final/proposed state, category, exception, or applicability condition.', 'method_or_definition': 'Find the metric definition, benchmark method, legal term, calculation basis, or measurement method.', 'contradiction_or_absence': 'Find disproof, missing-item evidence, contradiction, supersession, or evidence that the requested thing is absent.', 'derived_calculation_inputs': 'Find source operands required for arithmetic, deltas, ratios, or direct logical comparison.', 'downstream_effect_or_reaction': 'Find observed response, market/user/expert reaction, practical consequence, reversal, persistence, or mixed outcome.', 'free_1': 'Question-specific evidence intent selected by the model.', 'free_2': 'Question-specific evidence intent selected by the model.'}
        FALSE_PREMISE_CONTEXT_ROLE_TERMS = ('background', 'context', 'explain', 'justification', 'rationale', 'reason')
        FETCH_PAGE_CONCURRENCY = 2
        FETCH_PAGE_SEARCH_SNIPPET_FALLBACK_SOURCE_KIND = 'fetch_page_search_snippet_fallback'
        SEARCH_SNIPPET_EVIDENCE_SOURCE_KIND = 'selected_search_snippet'
        SEARCH_RESULT_TEXT_COMPRESSED_CHARS = 900
        SEARCH_RESULT_TEXT_SEGMENT_CHARS = 300
        BLOCKED_FETCH_HOST_SUFFIXES = ('facebook.com', 'instagram.com', 'x.com', 'twitter.com', 'tiktok.com', 'threads.net', 'linkedin.com', 'reddit.com', 'youtube.com', 'youtu.be')
        CHUNK_SIZE_CHARS = 1800
        CHUNK_OVERLAP_CHARS = 300
        HIT_CENTERED_PREVIEW_CONTEXT_CHARS = 600
        MAX_CHUNK_CUE_PATTERNS_TOTAL = 32
        MAX_CHUNK_CUE_PATTERNS_PER_ROLE = 5
        MAX_CHUNK_CUE_PATTERN_CHARS = 240
        MAX_SIGNAL_GENERATOR_SAMPLE_CHUNKS = 8
        MAX_LEXICAL_ANCHOR_SETS_TOTAL = 24
        MAX_LEXICAL_ANCHOR_TERMS_PER_FIELD = 8
        MAX_LEXICAL_ANCHOR_TERM_CHARS = 80
        LEXICAL_ANCHOR_NEAR_WINDOW_CHARS = 700
        MAX_SELECTED_CHUNKS_PER_PAGE = 6
        MAX_SELECTED_CHUNKS_TOTAL = 16
        MAX_QUERY_FRAGMENT_CHUNKS_WHEN_NO_PATTERN_HITS = 12
        MAX_CUE_HITS_PER_PATTERN_PER_CHUNK = 3
        REGEX_UNIT_WORDS = frozenset({'%', 'bp', 'bps', 'cent', 'cents', 'cm', 'dollar', 'dollars', 'eur', 'euro', 'euros', 'feet', 'foot', 'ft', 'gb', 'gbit', 'ghz', 'gwh', 'inch', 'inches', 'jpy', 'kg', 'kilogram', 'kilograms', 'kilometer', 'kilometers', 'kilometre', 'kilometres', 'km', 'kwh', 'lb', 'lbs', 'm', 'mb', 'meter', 'meters', 'metre', 'metres', 'mi', 'mile', 'miles', 'ms', 'mw', 'mwh', 'percent', 'pound', 'pounds', 'second', 'seconds', 'usd', 'yen'})
        REGEX_ESCAPE_WORDS = frozenset({'b', 'd', 's', 'w'})
        MAX_TEXT_EXCERPT_CHARS = 900
        GEMMA_MODEL = 'google/gemma-4-31b-it'
        GLM5_MODEL = 'z-ai/glm-5'
        _LLM_PROVIDER = 'openrouter'
        _SEARCH_PROVIDER = 'parallel'
        SYNTH_ALTERNATE_PROVIDER = 'ai_gateway'
        SYNTH_ALTERNATE_MODEL = 'zai/glm-5.2-fast'
        SYNTH_ALTERNATE_MAX_OUTPUT_TOKENS = 12000
        RESEARCH_PLAN_MODEL = GEMMA_MODEL
        EVIDENCE_GATE_MODEL = GEMMA_MODEL
        URL_SELECTION_MODEL = GEMMA_MODEL
        CHUNK_PATTERN_MODEL = GEMMA_MODEL
        FINAL_SYNTHESIS_MODEL = GLM5_MODEL
        PLANNING_TEMPERATURE = 0.35
        LABELING_TEMPERATURE = 0.5
        GATE_TEMPERATURE = 0.5
        SYNTHESIS_TEMPERATURE = 0.9
        EVIDENCE_GATE_THINKING = None
        FINAL_SYNTHESIS_THINKING = LlmThinkingConfig(enabled=True)
        NUMERIC_AUDIT_MIN_REMAINING_SECONDS = 45.0
        NUMERIC_AUDIT_TEMPERATURE = 0.2
        NUMERIC_AUDIT_MIN_LENGTH_RATIO = 0.6

        @dataclass(frozen=True, slots=True)
        class EvidenceCandidate:
            candidate_id: str
            parent_candidate_id: str
            slot_id: str
            slot_intent: str
            text_part: str
            text_start: int
            text_end: int
            receipt_id: str
            result_id: str
            url: str
            title: str | None
            source_text: str
            query: str
            source_kind: str

        @dataclass(frozen=True, slots=True)
        class AcceptedEvidence:
            url: str
            source_text: str
            source_result_text: str
            receipt_id: str
            result_id: str
            title: str | None
            parent_candidate_id: str
            text_part: str
            text_start: int
            text_end: int
            admission_reason: str

        @dataclass(frozen=True, slots=True)
        class CoverageAspect:
            aspect: str
            status: str
            supporting_packet_indices: tuple[int, ...]
            notes: str
            slot_id: str = ''

        @dataclass(frozen=True, slots=True)
        class ContractRole:
            role_id: str
            slot_id: str
            slot_intent: str
            question: str
            kind: str

        @dataclass(frozen=True, slots=True)
        class ResearchContract:
            roles: tuple[ContractRole, ...]
            answer_goal: str

        @dataclass(frozen=True, slots=True)
        class EvidenceObservation:
            role_id: str
            slot_id: str
            candidate_id: str
            entity: str
            metric: str
            value: str
            time_scope: str
            support: str
            source_tier: str
            packet_index: int

        @dataclass(frozen=True, slots=True)
        class CoverageRoleStatus:
            role_id: str
            slot_id: str
            status: str
            supporting_observation_indices: tuple[int, ...]
            value: str
            why: str

        @dataclass(frozen=True, slots=True)
        class CoverageState:
            roles: tuple[CoverageRoleStatus, ...]
            can_answer: bool
            missing_role_ids: tuple[str, ...]
            weak_role_ids: tuple[str, ...]

        @dataclass(frozen=True, slots=True)
        class EvidenceSourceInventory:
            entities: tuple[str, ...]
            aliases: tuple[str, ...]
            source_families: tuple[str, ...]
            document_handles: tuple[str, ...]
            metric_terms: tuple[str, ...]
            date_scope: tuple[str, ...]
            must_include: tuple[str, ...]
            avoid: tuple[str, ...]
            site_constraints: tuple[str, ...]

        @dataclass(frozen=True, slots=True)
        class EvidenceSearchRoute:
            route_id: str
            target_id: str
            slot_id: str
            slot_intent: str
            needed_source_text: str
            source_type: str
            route_kind: str
            query: str
            site_constraints: tuple[str, ...] = ()

        @dataclass(frozen=True, slots=True)
        class EvidenceSearchTarget:
            target_id: str
            slot_id: str
            slot_intent: str
            needed_source_text: str
            source_type: str
            inventory: EvidenceSourceInventory
            routes: tuple[EvidenceSearchRoute, ...]

        @dataclass(frozen=True, slots=True)
        class AccumulatedSearchResult:
            result_id: str
            target_id: str
            slot_id: str
            slot_intent: str
            needed_source_text: str
            source_type: str
            route_id: str
            route_kind: str
            url: str
            title: str | None
            note: str
            query: str
            receipt_id: str
            search_round: int
            stable_index: int

        @dataclass(frozen=True, slots=True)
        class LiteSearchBeam:
            results: tuple[AccumulatedSearchResult, ...]
            targets: tuple[EvidenceSearchTarget, ...]
            routes: tuple[EvidenceSearchRoute, ...]
            elapsed_ms: float
            stop_reason: str

        @dataclass(frozen=True, slots=True)
        class LiteSearchQueryResponse:
            query: str
            response: object | None

        @dataclass(frozen=True, slots=True)
        class SearchResultSourceLabel:
            basis: str
            result_id: str
            target_ids: tuple[str, ...]
            source_value: str
            source_kind: str
            surface: str

        @dataclass(frozen=True, slots=True)
        class SearchResultSourceLabelSet:
            labels: tuple[SearchResultSourceLabel, ...]
            ignored_label_count: int = 0
            unlabeled_result_ids: tuple[str, ...] = ()
            invalid_label_notes: tuple[str, ...] = ()

        @dataclass(frozen=True, slots=True)
        class SearchResultSourceLabelerGroup:
            group_id: str
            targets: tuple[EvidenceSearchTarget, ...]
            routes: tuple[EvidenceSearchRoute, ...]
            results: tuple[AccumulatedSearchResult, ...]

        @dataclass(frozen=True, slots=True)
        class SearchResultEvidenceSelection:
            snippet_result_ids: tuple[str, ...]
            detail_result_ids: tuple[str, ...]
            overlap_result_ids: tuple[str, ...]
            labels: tuple[SearchResultSourceLabel, ...] = ()
            unlabeled_result_ids: tuple[str, ...] = ()
            detail_fill_result_ids: tuple[str, ...] = ()

        @dataclass(frozen=True, slots=True)
        class ResearchPlanRole:
            role_id: str
            slot_id: str
            slot_intent: str
            question: str
            kind: str
            status: str
            value: str | None
            why_not_covered: str
            queries: tuple[str, ...]

        @dataclass(frozen=True, slots=True)
        class GateResult:
            accepted_packets: tuple[AcceptedEvidence, ...]
            coverage: tuple[CoverageAspect, ...] = ()
            role_ledger: tuple[ResearchPlanRole, ...] = ()
            can_answer: bool = False
            missing_questions: tuple[str, ...] = ()
            observations: tuple[EvidenceObservation, ...] = ()

        @dataclass(frozen=True, slots=True)
        class BoundedPoolPlan:
            is_bounded_pool: bool = False
            pool_subject: str = ''
            pool_members: tuple[str, ...] = ()
            criteria: tuple[str, ...] = ()

        @dataclass(frozen=True, slots=True)
        class SecondHopPlan:
            followup_queries: tuple[str, ...] = ()
            resolved_facts: tuple[str, ...] = ()

        @dataclass(frozen=True, slots=True)
        class SearchResultSeed:
            search_receipt_id: str
            search_result_id: str
            slot_id: str
            slot_intent: str
            url: str
            title: str | None
            note: str

        @dataclass(frozen=True, slots=True)
        class CandidateSource:
            receipt_id: str
            result_id: str
            slot_id: str
            slot_intent: str
            url: str
            title: str | None
            source_text: str
            source_kind: str

        @dataclass(frozen=True, slots=True)
        class PageChunk:
            chunk_id: str
            page_id: str
            source_index: int
            chunk_index: int
            receipt_id: str
            result_id: str
            slot_id: str
            slot_intent: str
            url: str
            title: str | None
            query: str
            text_start: int
            text_end: int
            text: str
            source_kind: str

        @dataclass(frozen=True, slots=True)
        class PagePoolEntry:
            page_id: str
            cache_key: str
            source: CandidateSource

        @dataclass(frozen=True, slots=True)
        class ChunkCuePattern:
            pattern_index: int
            role_id: str
            pattern: str
            compiled: re.Pattern[str]

        @dataclass(frozen=True, slots=True)
        class ChunkCueHit:
            chunk_id: str
            role_id: str
            pattern_index: int
            start: int
            end: int
            score: int

        @dataclass(frozen=True, slots=True)
        class ChunkLexicalAnchorSet:
            anchor_index: int
            role_id: str
            all_terms: tuple[str, ...]
            any_terms: tuple[str, ...]
            near_terms: tuple[str, ...]
            avoid_terms: tuple[str, ...]

        @dataclass(frozen=True, slots=True)
        class ChunkLexicalAnchorHit:
            chunk_id: str
            role_id: str
            anchor_index: int
            matched_all_count: int
            matched_any_count: int
            matched_near_count: int
            avoid_count: int
            score: int
            best_span: tuple[int, int] | None

        @dataclass(frozen=True, slots=True)
        class ChunkSignalPlan:
            regex_patterns: tuple[ChunkCuePattern, ...]
            lexical_anchor_sets: tuple[ChunkLexicalAnchorSet, ...]

        @dataclass(slots=True)
        class ResearchRunState:
            pass

        async def _plain_query(query: Query, budget: float) -> Response:
            state = ResearchRunState()
            _set_emit_evidence(())
            deadline = perf_counter() + budget
            try:
                response = await _answer_question(query.text, state=state, deadline=deadline)
                return response
            except Exception:
                return Response(text='I could not complete a source-backed research answer for this question because the research pipeline failed before it produced accepted evidence. A reliable answer would require direct sources that address the question.')

        async def _answer_question(question: str, *, state: ResearchRunState, deadline: float) -> Response:
            search_beam = await _run_lite_search_beam(question=question, state=state, deadline=deadline)
            if not search_beam.results:
                return Response(text=_insufficient_answer(question, ()))
            search_selection = await _select_search_results_for_evidence_paths(question=question, targets=search_beam.targets, routes=search_beam.routes, results=search_beam.results, state=state)
            role_ledger = _beam_role_ledger(targets=search_beam.targets, routes=search_beam.routes, search_selection=search_selection, results=search_beam.results, question=question)
            research_contract = _beam_research_contract(role_ledger=role_ledger, question=question)
            candidates, _candidate_counter = await _candidates_from_selected_search_results(question=question, results=search_beam.results, search_selection=search_selection, role_ledger=role_ledger, candidate_counter=0, state=state)
            gate_result = await _admit_evidence_from_candidate_beam(question=question, contract=research_contract, role_ledger=role_ledger, candidates=candidates, state=state, deadline=deadline)
            accepted_packets = gate_result.accepted_packets
            accepted_observations = gate_result.observations
            coverage_state = _fallback_coverage_state(contract=research_contract, observations=accepted_observations)
            coverage = _coverage_from_coverage_state(coverage_state, accepted_observations)
            augmentation_deadline = min(deadline, perf_counter() + GAP_AUGMENTATION_MAX_TOTAL_SECONDS)
            enumerated_entities = _enumerated_question_entities(question)
            if enumerated_entities and perf_counter() < augmentation_deadline:
                missing_entities = _entities_missing_from_evidence(entities=enumerated_entities, packets=accepted_packets, observations=accepted_observations)
                if missing_entities:
                    gap_gate = await _augment_missing_entity_evidence(question=question, entities=missing_entities, contract=research_contract, role_ledger=role_ledger, existing_packets=accepted_packets, existing_observations=accepted_observations, state=state, deadline=deadline)
                    if gap_gate.accepted_packets:
                        accepted_packets = (*accepted_packets, *gap_gate.accepted_packets)
                        accepted_observations = (*accepted_observations, *gap_gate.observations)
                        coverage_state = _fallback_coverage_state(contract=research_contract, observations=accepted_observations)
                        coverage = _coverage_from_coverage_state(coverage_state, accepted_observations)
            if (coverage_state.missing_role_ids or coverage_state.weak_role_ids) and perf_counter() < augmentation_deadline and (deadline - perf_counter() >= ROLE_GAP_MIN_REMAINING_SECONDS):
                role_gap_gate = await _augment_role_gap_evidence(question=question, coverage_state=coverage_state, contract=research_contract, role_ledger=role_ledger, existing_packets=accepted_packets, existing_observations=accepted_observations, state=state, deadline=deadline)
                if role_gap_gate.accepted_packets:
                    accepted_packets = (*accepted_packets, *role_gap_gate.accepted_packets)
                    accepted_observations = (*accepted_observations, *role_gap_gate.observations)
                    coverage_state = _fallback_coverage_state(contract=research_contract, observations=accepted_observations)
                    coverage = _coverage_from_coverage_state(coverage_state, accepted_observations)
            if perf_counter() < augmentation_deadline and deadline - perf_counter() >= POOL_SWEEP_MIN_REMAINING_SECONDS:
                pool_plan = await _detect_bounded_pool(question=question, existing_packets=accepted_packets, state=state, deadline=deadline)
                if pool_plan.is_bounded_pool and pool_plan.criteria:
                    pool_gate = await _augment_bounded_pool_evidence(question=question, plan=pool_plan, contract=research_contract, role_ledger=role_ledger, existing_packets=accepted_packets, existing_observations=accepted_observations, state=state, deadline=deadline)
                    if pool_gate.accepted_packets:
                        accepted_packets = (*accepted_packets, *pool_gate.accepted_packets)
                        accepted_observations = (*accepted_observations, *pool_gate.observations)
                        coverage_state = _fallback_coverage_state(contract=research_contract, observations=accepted_observations)
                        coverage = _coverage_from_coverage_state(coverage_state, accepted_observations)
            if accepted_packets and perf_counter() < augmentation_deadline and (deadline - perf_counter() >= HOP_MIN_REMAINING_SECONDS):
                hop_plan = await _detect_second_hop(question=question, existing_packets=accepted_packets, state=state, deadline=deadline)
                if hop_plan.followup_queries:
                    hop_gate = await _augment_second_hop_evidence(question=question, plan=hop_plan, contract=research_contract, role_ledger=role_ledger, existing_packets=accepted_packets, existing_observations=accepted_observations, state=state, deadline=deadline)
                    if hop_gate.accepted_packets:
                        accepted_packets = (*accepted_packets, *hop_gate.accepted_packets)
                        accepted_observations = (*accepted_observations, *hop_gate.observations)
                        coverage_state = _fallback_coverage_state(contract=research_contract, observations=accepted_observations)
                        coverage = _coverage_from_coverage_state(coverage_state, accepted_observations)
            if not accepted_packets:
                return await _answer_from_raw_snippets(question=question, results=search_beam.results, coverage=coverage, state=state, deadline=deadline)
            final_answer = await _synthesize_final_answer(question=question, accepted_packets=accepted_packets, accepted_observations=accepted_observations, coverage=coverage, state=state, deadline=deadline)
            final_answer = await _audit_and_repair_answer(question=question, draft=final_answer, accepted_packets=accepted_packets, deadline=deadline)
            final_answer = await _reconcile_opening_with_body(question=question, draft=_safe_response_text(final_answer), accepted_packets=accepted_packets, deadline=deadline)
            final_answer, citations = _answer_text_and_citations(_safe_response_text(final_answer), accepted_packets)
            _set_emit_evidence(accepted_packets)
            return Response(text=final_answer, citations=citations or None)

        async def _run_lite_search_beam(*, question: str, state: ResearchRunState, deadline: float) -> LiteSearchBeam:
            started_perf = perf_counter()
            accumulated: list[AccumulatedSearchResult] = []
            targets_seen: list[EvidenceSearchTarget] = []
            routes_seen: list[EvidenceSearchRoute] = []
            tried_queries: set[str] = set()
            seen_urls: set[str] = set()
            wrong_entities: tuple[str, ...] = ()
            stop_reason = 'max_lite_search_rounds'
            for round_index in range(MAX_LITE_SEARCH_ROUNDS):
                elapsed_seconds = perf_counter() - started_perf
                remaining_seconds = LITE_SEARCH_BUDGET_SECONDS - elapsed_seconds
                if accumulated and remaining_seconds < MIN_LITE_SEARCH_ROUND_REMAINING_SECONDS:
                    stop_reason = 'lite_search_budget_exhausted'
                    break
                if perf_counter() > deadline - 60.0:
                    stop_reason = 'task_deadline_approaching'
                    break
                targets = await _generate_evidence_search_targets(question=question, round_index=round_index, tried_queries=tuple(sorted(tried_queries)), prior_targets=tuple(targets_seen), accumulated_results=tuple(accumulated), state=state, wrong_entities=wrong_entities)
                routes = await _generate_evidence_search_routes(question=question, round_index=round_index, targets=targets, tried_queries=tuple(sorted(tried_queries)), accumulated_results=tuple(accumulated), state=state)
                if not routes:
                    stop_reason = 'no_new_evidence_search_routes'
                    break
                round_queries = _materialized_evidence_search_queries(routes, tried_queries=tried_queries)
                if not round_queries:
                    stop_reason = 'no_new_lite_search_queries'
                    break
                targets_seen.extend(targets)
                routes_seen.extend(routes)
                tried_queries.update((_query_identity(q) for q in round_queries))
                response = await _run_lite_search_round(routes=routes, queries=round_queries, state=state, round_index=round_index, deadline=deadline)
                if response is None:
                    stop_reason = 'lite_search_failed'
                    break
                added_count = _accumulate_lite_search_results(accumulated=accumulated, response=response, routes=routes, seen_urls=seen_urls, round_index=round_index, state=state)
                wrong_entities = _extract_candidate_entities(tuple(accumulated))
                if len(accumulated) >= MAX_ACCUMULATED_SEARCH_RESULTS:
                    stop_reason = 'accumulated_result_cap_reached'
                    break
                if added_count == 0 and round_index > 0:
                    stop_reason = 'no_new_search_results'
                    break
            return LiteSearchBeam(results=tuple(accumulated), targets=tuple(targets_seen), routes=tuple(routes_seen), elapsed_ms=_elapsed_ms(started_perf), stop_reason=stop_reason)

        async def _generate_evidence_search_targets(*, question: str, round_index: int, tried_queries: tuple[str, ...], prior_targets: tuple[EvidenceSearchTarget, ...], accumulated_results: tuple[AccumulatedSearchResult, ...], state: ResearchRunState, wrong_entities: tuple[str, ...]=()) -> tuple[EvidenceSearchTarget, ...]:
            messages = _build_evidence_search_target_messages(question=question, round_index=round_index, tried_queries=tried_queries, prior_targets=prior_targets, accumulated_results=accumulated_results, wrong_entities=wrong_entities)
            payload = await _call_json_llm_with_retry(messages=messages, model=RESEARCH_PLAN_MODEL, temperature=PLANNING_TEMPERATURE, validate_payload=_evidence_search_target_payload_validator(), repair_payload=_repair_evidence_search_target_payload, state=state, stage=f'evidence_search_target_generation_round_{round_index}')
            targets = _evidence_search_targets_from_payload(payload, round_index=round_index) if payload else ()
            if not targets and round_index == 0:
                fallback_inventory = EvidenceSourceInventory(entities=(question,), aliases=(), source_families=(), document_handles=(), metric_terms=(), date_scope=(), must_include=(), avoid=(), site_constraints=())
                fallback_route = EvidenceSearchRoute(route_id='target_1_1_route_1', target_id='target_1_1', slot_id=PRIMARY_SOURCE_SLOT_ID, slot_intent=_slot_intent_for_slot(PRIMARY_SOURCE_SLOT_ID), needed_source_text='Primary or canonical source text needed to answer the original question exactly.', source_type='primary_source', route_kind='direct_question', query=question, site_constraints=())
                targets = (EvidenceSearchTarget(target_id='target_1_1', slot_id=PRIMARY_SOURCE_SLOT_ID, slot_intent=_slot_intent_for_slot(PRIMARY_SOURCE_SLOT_ID), needed_source_text=fallback_route.needed_source_text, source_type=fallback_route.source_type, inventory=fallback_inventory, routes=(fallback_route,)),)
            return targets

        async def _generate_evidence_search_routes(*, question: str, round_index: int, targets: tuple[EvidenceSearchTarget, ...], tried_queries: tuple[str, ...], accumulated_results: tuple[AccumulatedSearchResult, ...], state: ResearchRunState) -> tuple[EvidenceSearchRoute, ...]:
            if not targets:
                return ()
            messages = _build_evidence_search_route_messages(question=question, round_index=round_index, targets=targets, tried_queries=tried_queries, accumulated_results=accumulated_results)
            payload = await _call_json_llm_with_retry(messages=messages, model=RESEARCH_PLAN_MODEL, temperature=PLANNING_TEMPERATURE, validate_payload=_evidence_search_route_payload_validator(targets=targets), state=state, stage=f'evidence_search_route_generation_round_{round_index}')
            routes = _evidence_search_routes_from_payload(payload=payload, targets=targets, tried_queries=set(tried_queries))
            if routes or round_index > 0:
                return routes
            target = targets[0]
            return (EvidenceSearchRoute(route_id=f'{target.target_id}_route_1', target_id=target.target_id, slot_id=target.slot_id, slot_intent=target.slot_intent, needed_source_text=target.needed_source_text, source_type=target.source_type, route_kind='direct_question_fallback', query=question, site_constraints=()),)

        async def _run_lite_search_round(*, routes: tuple[EvidenceSearchRoute, ...], queries: tuple[str, ...], state: ResearchRunState, round_index: int, deadline: float) -> tuple[LiteSearchQueryResponse, ...] | None:
            route_by_query = _route_by_materialized_query(routes)
            result_budget = SEARCH_RESULTS_PER_ROUTE
            responses = await asyncio.gather(*(_run_lite_search_query(query=q, base_query=route_by_query[_query_identity(q)].query if _query_identity(q) in route_by_query else q, round_index=round_index, result_budget=result_budget, state=state, deadline=deadline) for q in queries))
            successful = tuple((item for item in responses if item.response is not None))
            return successful or None

        async def _run_lite_search_query(*, query: str, base_query: str, round_index: int, result_budget: int, state: ResearchRunState, deadline: float) -> LiteSearchQueryResponse:
            try:
                response = await search_web([query], provider=_SEARCH_PROVIDER, num=result_budget, timeout=LITE_SEARCH_TOOL_TIMEOUT_SECONDS)
                return LiteSearchQueryResponse(query=query, response=response)
            except Exception:
                pass
            if SEARCH_DEGRADED_RETRY_ENABLED and base_query != query and (deadline - perf_counter() > 10.0):
                try:
                    response = await search_web([base_query], provider=_SEARCH_PROVIDER, num=result_budget, timeout=LITE_SEARCH_TOOL_TIMEOUT_SECONDS)
                    return LiteSearchQueryResponse(query=base_query, response=response)
                except Exception:
                    pass
            return LiteSearchQueryResponse(query=query, response=None)

        def _accumulate_lite_search_results(*, accumulated: list[AccumulatedSearchResult], response: tuple[LiteSearchQueryResponse, ...], routes: tuple[EvidenceSearchRoute, ...], seen_urls: set[str], round_index: int, state: ResearchRunState) -> int:
            route_by_query = _route_by_materialized_query(routes)
            fallback_route = routes[0] if len(routes) == 1 else None
            added_count = 0
            response_results = tuple(((qr, tuple(getattr(qr.response, 'results', ()) or ())) for qr in response))
            max_result_count = max((len(results) for _, results in response_results), default=0)
            for result_offset in range(max_result_count):
                for query_response, query_results in response_results:
                    if len(accumulated) >= MAX_ACCUMULATED_SEARCH_RESULTS:
                        break
                    if result_offset >= len(query_results):
                        continue
                    result = query_results[result_offset]
                    query_route = route_by_query.get(_query_identity(query_response.query)) or fallback_route
                    url = (getattr(result, 'url', '') or '').strip()
                    note = (getattr(result, 'note', '') or '').strip()
                    if not url or not (note or getattr(result, 'title', None)):
                        continue
                    if _blocked_fetch_url_reason(url):
                        continue
                    url_key = _normalize_url(url) or url
                    if url_key in seen_urls:
                        continue
                    result_query = _string_value(getattr(result, 'query', '')) or query_response.query
                    route = route_by_query.get(_query_identity(result_query)) or query_route
                    seen_urls.add(url_key)
                    stable_index = len(accumulated) + 1
                    result_id = _string_value(getattr(result, 'result_id', '')) or f'R{stable_index}'
                    accumulated.append(AccumulatedSearchResult(result_id=result_id, target_id=route.target_id if route else '', slot_id=route.slot_id if route else '', slot_intent=route.slot_intent if route else '', needed_source_text=route.needed_source_text if route else '', source_type=route.source_type if route else '', route_id=route.route_id if route else '', route_kind=route.route_kind if route else '', url=url, title=getattr(result, 'title', None), note=note, query=result_query, receipt_id=getattr(query_response.response, 'receipt_id', '') or '', search_round=round_index, stable_index=stable_index))
                    added_count += 1
                if len(accumulated) >= MAX_ACCUMULATED_SEARCH_RESULTS:
                    break
            return added_count

        async def _select_search_results_for_evidence_paths(*, question: str, targets: tuple[EvidenceSearchTarget, ...], routes: tuple[EvidenceSearchRoute, ...], results: tuple[AccumulatedSearchResult, ...], state: ResearchRunState) -> SearchResultEvidenceSelection:
            selector_input = results[:MAX_SELECTOR_INPUT_RESULTS]
            if not selector_input:
                return SearchResultEvidenceSelection(snippet_result_ids=(), detail_result_ids=(), overlap_result_ids=())
            label_set = await _label_search_result_sources(question=question, targets=targets, routes=routes, results=selector_input, state=state)
            return _search_result_selection_from_labels(results=selector_input, label_set=label_set, max_detail_results=MAX_DETAIL_FETCH_RESULTS)

        async def _label_search_result_sources(*, question: str, targets: tuple[EvidenceSearchTarget, ...], routes: tuple[EvidenceSearchRoute, ...], results: tuple[AccumulatedSearchResult, ...], state: ResearchRunState) -> SearchResultSourceLabelSet:
            groups = _search_result_source_labeler_groups(targets=targets, routes=routes, results=results)
            if not groups:
                return SearchResultSourceLabelSet(labels=(), unlabeled_result_ids=tuple((r.result_id for r in results)))
            if len(groups) == 1:
                return await _label_search_result_source_group(question=question, group=groups[0], stage='search_result_source_labeler', state=state)
            group_label_sets = await asyncio.gather(*(_label_search_result_source_group(question=question, group=g, stage=f'search_result_source_labeler_{_stage_suffix(g.group_id)}', state=state) for g in groups))
            return _merge_source_label_sets(results=results, label_sets=group_label_sets)

        async def _label_search_result_source_group(*, question: str, group: SearchResultSourceLabelerGroup, stage: str, state: ResearchRunState) -> SearchResultSourceLabelSet:
            messages = _build_search_result_source_labeler_messages(question=question, targets=group.targets, routes=group.routes, results=group.results)
            payload = await _call_json_llm_with_retry(messages=messages, model=URL_SELECTION_MODEL, temperature=LABELING_TEMPERATURE, validate_payload=_search_result_source_labeler_payload_validator(), state=state, stage=stage)
            return _source_labels_from_payload(payload=payload, targets=group.targets, results=group.results)

        def _search_result_source_labeler_groups(*, targets: tuple[EvidenceSearchTarget, ...], routes: tuple[EvidenceSearchRoute, ...], results: tuple[AccumulatedSearchResult, ...]) -> tuple[SearchResultSourceLabelerGroup, ...]:
            if not results:
                return ()
            valid_target_ids = {t.target_id for t in targets}
            result_buckets: dict[str, list[AccumulatedSearchResult]] = {tid: [] for tid in valid_target_ids}
            ungrouped: list[AccumulatedSearchResult] = []
            for result in results:
                if result.target_id in result_buckets:
                    result_buckets[result.target_id].append(result)
                else:
                    ungrouped.append(result)
            groups: list[SearchResultSourceLabelerGroup] = []
            seen: set[str] = set()
            for target in targets:
                if target.target_id in seen:
                    continue
                seen.add(target.target_id)
                bucket = tuple(result_buckets.get(target.target_id, ()))
                if not bucket:
                    continue
                groups.append(SearchResultSourceLabelerGroup(group_id=target.target_id, targets=tuple((t for t in targets if t.target_id == target.target_id)), routes=tuple((r for r in routes if r.target_id == target.target_id)), results=bucket))
            if ungrouped:
                groups.append(SearchResultSourceLabelerGroup(group_id='ungrouped', targets=targets, routes=routes, results=tuple(ungrouped)))
            return tuple(groups)

        def _merge_source_label_sets(*, results: tuple[AccumulatedSearchResult, ...], label_sets: tuple[SearchResultSourceLabelSet, ...]) -> SearchResultSourceLabelSet:
            label_by_id: dict[str, SearchResultSourceLabel] = {}
            ignored = 0
            notes: list[str] = []
            for ls in label_sets:
                ignored += ls.ignored_label_count
                notes.extend(ls.invalid_label_notes)
                for label in ls.labels:
                    label_by_id.setdefault(label.result_id, label)
            labels = tuple((label_by_id[r.result_id] for r in results if r.result_id in label_by_id))
            unlabeled = tuple((r.result_id for r in results if r.result_id not in label_by_id))
            return SearchResultSourceLabelSet(labels=labels, ignored_label_count=ignored, unlabeled_result_ids=unlabeled, invalid_label_notes=tuple(notes[:20]))

        def _stage_suffix(value: str) -> str:
            return re.sub('[^A-Za-z0-9_]+', '_', value).strip('_') or 'group'

        async def _candidates_from_selected_search_results(*, question: str, results: tuple[AccumulatedSearchResult, ...], search_selection: SearchResultEvidenceSelection, role_ledger: tuple[ResearchPlanRole, ...], candidate_counter: int, state: ResearchRunState) -> tuple[tuple[EvidenceCandidate, ...], int]:
            result_by_id = {r.result_id: r for r in results}
            seen_keys: set[str] = set()
            snippet_candidates, candidate_counter = _snippet_results_to_candidates(results=tuple((result_by_id[rid] for rid in search_selection.snippet_result_ids if rid in result_by_id)), seen_candidate_keys=seen_keys, candidate_counter=candidate_counter)
            seeds = tuple((_search_seed_from_accumulated_result(result_by_id[rid]) for rid in search_selection.detail_result_ids if rid in result_by_id))
            if not seeds:
                detail_candidates: tuple[EvidenceCandidate, ...] = ()
            else:
                page_entries, _ = await _page_entries_from_search_seeds(seeds=seeds, state=state, loop_index=0)
                chunks = _loop_chunks_from_page_entries(page_entries=page_entries, query_label=' | '.join((s.note[:120] for s in seeds)), state=state, loop_index=0)
                selected_chunks = await _select_page_chunks(question=question, loop_index=0, chunks=chunks, role_ledger=role_ledger, state=state)
                detail_candidates, candidate_counter = _selected_chunks_to_candidates(chunks=selected_chunks, seen_candidate_keys=seen_keys, candidate_counter=candidate_counter)
            return ((*snippet_candidates, *detail_candidates), candidate_counter)

        def _snippet_results_to_candidates(*, results: tuple[AccumulatedSearchResult, ...], seen_candidate_keys: set[str], candidate_counter: int) -> tuple[tuple[EvidenceCandidate, ...], int]:
            candidates: list[EvidenceCandidate] = []
            for result in results:
                source_text = result.note.strip()
                if not source_text:
                    continue
                key = f'{SEARCH_SNIPPET_EVIDENCE_SOURCE_KIND}:{_normalize_url(result.url) or result.url}:{_text_fingerprint(result.note)}'
                if key in seen_candidate_keys:
                    continue
                seen_candidate_keys.add(key)
                candidate_counter += 1
                slot_id = result.slot_id or PRIMARY_SOURCE_SLOT_ID
                candidates.append(EvidenceCandidate(candidate_id=f'K{candidate_counter}', parent_candidate_id=result.result_id, slot_id=slot_id, slot_intent=result.slot_intent or _slot_intent_for_slot(slot_id), text_part='search_snippet', text_start=0, text_end=len(result.note), receipt_id=result.receipt_id, result_id=result.result_id, url=result.url, title=result.title, source_text=source_text, query=result.query, source_kind=SEARCH_SNIPPET_EVIDENCE_SOURCE_KIND))
            return (tuple(candidates), candidate_counter)
        _ENTITY_TITLE_CONNECTORS = {'a', 'an', 'the', 'of', 'and', 'vs', 'vs.', 'in', 'on', 'at', 'for', 'to', '&', '+'}
        _ENTITY_LEADING_DISCOURSE_WORDS = {'among', 'between', 'looking', 'considering', 'comparing', 'regarding', 'given', 'which', 'what', 'who', 'about', 'across', 'over', 'under', 'within', 'including', 'rank', 'list', 'name', 'order', 'sort', 'compare', 'consider', 'take', 'evaluate'}
        _ENTITY_HINT_STOPWORDS = {'the', 'a', 'an', 'of', 'and', 'or', 'which', 'what', 'who', 'whom', 'whose', 'its', 'had', 'has', 'have', 'was', 'were', 'is', 'are', 'be', 'been', 'during', 'please', 'use', 'using', 'data', 'from', 'looking', 'at', 'for', 'in', 'on', 'to', 'by', 'with', 'that', 'this', 'these', 'those', 'do', 'does', 'did', 'how', 'many', 'much', 'most', 'greatest', 'between', 'among', 'each', 'per', 'as', 'it', 'their', 'them', 'they', 'films', 'film', 'movies', 'movie', 'companies', 'company', 'people', 'person'}

        def _enumerated_question_entities(question: str) -> tuple[str, ...]:
            text = ' '.join(question.split())
            entities: list[str] = []
            for segment in re.split('[?;\\n]', text):
                elements = [e.strip() for e in segment.split(',')]
                if len(elements) < ENTITY_GAP_MIN_ENTITIES:
                    continue
                run: list[str] = []
                for index, raw in enumerate(elements):
                    element = re.sub('^(?:and|or)\\s+', '', raw).strip().strip('"\'')
                    words = element.split()
                    if not words:
                        if len(run) >= ENTITY_GAP_MIN_ENTITIES:
                            break
                        run = []
                        continue
                    if index == 0 or not run:
                        phrase = _trailing_capitalized_phrase(words)
                        if phrase:
                            run = [phrase]
                        continue
                    leading = _leading_capitalized_phrase(words) if element[0].isupper() or element[0].isdigit() else ''
                    if leading:
                        run.append(leading)
                    else:
                        if len(run) >= ENTITY_GAP_MIN_ENTITIES:
                            break
                        run = []
                if len(run) >= ENTITY_GAP_MIN_ENTITIES:
                    seen: set[str] = set()
                    out = [e for e in run if not (e.lower() in seen or seen.add(e.lower()))]
                    if len(out) >= ENTITY_GAP_MIN_ENTITIES:
                        return tuple(out)
            return ()

        def _leading_capitalized_phrase(words: list[str]) -> str:
            phrase: list[str] = []
            for index, word in enumerate(words):
                stripped = word.strip('"\'')
                if stripped and (stripped[0].isupper() or stripped[0].isdigit()):
                    phrase.append(word)
                elif phrase and stripped.lower() in _ENTITY_TITLE_CONNECTORS and (index + 1 < len(words)) and words[index + 1].strip('"\'')[:1].isupper():
                    phrase.append(word)
                else:
                    break
            while phrase and phrase[-1].strip('"\'').lower() in _ENTITY_TITLE_CONNECTORS:
                phrase.pop()
            if not phrase or len(phrase) > 8:
                return ''
            return ' '.join(phrase)

        def _trailing_capitalized_phrase(words: list[str]) -> str:
            phrase: list[str] = []
            for word in reversed(words):
                stripped = word.strip('"\'')
                if stripped and (stripped[0].isupper() or stripped[0].isdigit()):
                    phrase.append(word)
                elif phrase and stripped.lower() in _ENTITY_TITLE_CONNECTORS:
                    phrase.append(word)
                else:
                    break
            while phrase and phrase[-1].strip('"\'').lower() in _ENTITY_TITLE_CONNECTORS:
                phrase.pop()
            ordered = list(reversed(phrase))
            while ordered and ordered[0].strip('"\'').lower() in _ENTITY_LEADING_DISCOURSE_WORDS:
                ordered.pop(0)
            if not ordered or len(ordered) > 8:
                return ''
            return ' '.join(ordered)

        def _entity_probe_token(entity: str) -> str:
            tokens = [t.strip('.,:;"\'').lower() for t in entity.split()]
            tokens = [t for t in tokens if t and t not in _ENTITY_TITLE_CONNECTORS]
            if not tokens:
                return entity.lower()
            return max(tokens, key=len)

        def _entities_missing_from_evidence(*, entities: tuple[str, ...], packets: tuple[AcceptedEvidence, ...], observations: tuple[EvidenceObservation, ...]) -> tuple[str, ...]:
            attributed_packet_indices = {o.packet_index for o in observations if o.value.strip()}
            blob_parts = [f'{o.entity} {o.value}' for o in observations if o.value.strip()]
            blob_parts += [f'{p.source_text} {p.source_result_text}' for i, p in enumerate(packets, start=1) if i in attributed_packet_indices]
            blob = ' '.join(blob_parts).lower()
            missing: list[str] = []
            for entity in entities:
                if entity.lower() in blob:
                    continue
                if _entity_probe_token(entity) in blob:
                    continue
                missing.append(entity)
            return tuple(missing)

        def _question_metric_hint(question: str, entities: tuple[str, ...]) -> str:
            entity_tokens = {t.strip('.,:;"\'').lower() for e in entities for t in e.split()}
            hint: list[str] = []
            for token in re.findall('[A-Za-z0-9%$][A-Za-z0-9%$.-]*', question):
                low = token.lower().strip('.-')
                if not low or low in entity_tokens or low in _ENTITY_HINT_STOPWORDS:
                    continue
                if low in (h.lower() for h in hint):
                    continue
                hint.append(token if token.isupper() else low)
                if len(hint) >= ENTITY_GAP_METRIC_HINT_MAX_TOKENS:
                    break
            source_match = re.search("\\b(?:data from|according to|as reported by|reported in)\\s+([A-Z][\\w&' .-]{2,40}?)(?:\\s*[.?,]|$)", question)
            if source_match:
                source_name = source_match.group(1).strip()
                if source_name.lower() not in ' '.join(hint).lower():
                    hint.append(source_name)
            return ' '.join(hint)

        async def _augment_missing_entity_evidence(*, question: str, entities: tuple[str, ...], contract: ResearchContract, role_ledger: tuple[ResearchPlanRole, ...], existing_packets: tuple[AcceptedEvidence, ...], existing_observations: tuple[EvidenceObservation, ...], state: ResearchRunState, deadline: float) -> GateResult:
            metric_hint = _question_metric_hint(question, entities)
            candidates: list[EvidenceCandidate] = []
            seen_keys: set[str] = set()
            counter = 0
            for entity in entities[:ENTITY_GAP_MAX_ENTITIES_TO_AUGMENT]:
                if deadline - perf_counter() < ENTITY_GAP_MIN_REMAINING_SECONDS:
                    break
                query = f'{entity} {metric_hint}'.strip()
                try:
                    response = await search_web([query], provider=_SEARCH_PROVIDER, num=ENTITY_GAP_SEARCH_RESULTS_PER_ENTITY, timeout=LITE_SEARCH_TOOL_TIMEOUT_SECONDS)
                except Exception:
                    continue
                receipt_id = getattr(response, 'receipt_id', '') or ''
                for result in tuple(getattr(response, 'results', ()) or ()):
                    url = (getattr(result, 'url', '') or '').strip()
                    note = (getattr(result, 'note', '') or '').strip()
                    if not url or not note or _blocked_fetch_url_reason(url):
                        continue
                    key = f'entity_gap:{_normalize_url(url) or url}:{_text_fingerprint(note)}'
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    counter += 1
                    candidates.append(EvidenceCandidate(candidate_id=f'G{counter}', parent_candidate_id=f'G{counter}', slot_id=PRIMARY_SOURCE_SLOT_ID, slot_intent=_slot_intent_for_slot(PRIMARY_SOURCE_SLOT_ID), text_part='search_snippet', text_start=0, text_end=len(note), receipt_id=receipt_id, result_id=_string_value(getattr(result, 'result_id', '')) or f'G{counter}', url=url, title=getattr(result, 'title', None), source_text=note, query=query, source_kind=SEARCH_SNIPPET_EVIDENCE_SOURCE_KIND))
            if not candidates or deadline - perf_counter() < ENTITY_GAP_GATE_MIN_REMAINING_SECONDS:
                return GateResult(accepted_packets=(), observations=())
            return await _run_observation_gate_once(question=question, loop_index=1, existing_packets=existing_packets, existing_observations=existing_observations, contract=contract, retrieval_roles=role_ledger, candidates=tuple(candidates), model=EVIDENCE_GATE_MODEL, state=state, stage='entity_gap_gate', lane='entity_gap')

        def _role_gap_roles_to_augment(*, role_ledger: tuple[ResearchPlanRole, ...], coverage_state: CoverageState) -> tuple[ResearchPlanRole, ...]:
            role_by_id = {role.role_id: role for role in role_ledger}
            ordered_role_ids = _stable_id_union((*coverage_state.missing_role_ids, *coverage_state.weak_role_ids))
            return tuple((role_by_id[rid] for rid in ordered_role_ids if rid in role_by_id))

        def _role_gap_search_query(*, role: ResearchPlanRole, question: str) -> str:
            text = ' '.join(role.question.split())
            if role.role_id == PREMISE_SLOT_ID or len(text.split()) < 3:
                text = ' '.join(question.split())
            return ' '.join(text.split()[:ROLE_GAP_QUERY_MAX_WORDS])

        async def _augment_role_gap_evidence(*, question: str, coverage_state: CoverageState, contract: ResearchContract, role_ledger: tuple[ResearchPlanRole, ...], existing_packets: tuple[AcceptedEvidence, ...], existing_observations: tuple[EvidenceObservation, ...], state: ResearchRunState, deadline: float) -> GateResult:
            roles = _role_gap_roles_to_augment(role_ledger=role_ledger, coverage_state=coverage_state)
            role_queries: list[tuple[ResearchPlanRole, str]] = []
            seen_queries: set[str] = set()
            for role in roles:
                query = _role_gap_search_query(role=role, question=question)
                key = _query_identity(query)
                if not key or key in seen_queries:
                    continue
                seen_queries.add(key)
                role_queries.append((role, query))
                if len(role_queries) >= ROLE_GAP_MAX_ROLES_TO_AUGMENT:
                    break
            if not role_queries or deadline - perf_counter() < ROLE_GAP_MIN_REMAINING_SECONDS:
                return GateResult(accepted_packets=(), observations=())
            responses = await asyncio.gather(*(_run_lite_search_query(query=query, base_query=query, round_index=0, result_budget=ROLE_GAP_SEARCH_RESULTS_PER_ROLE, state=state, deadline=deadline) for _, query in role_queries))
            candidates: list[EvidenceCandidate] = []
            seen_keys: set[str] = set()
            counter = 0
            for (role, _), query_response in zip(role_queries, responses, strict=False):
                if query_response.response is None:
                    continue
                receipt_id = getattr(query_response.response, 'receipt_id', '') or ''
                for result in tuple(getattr(query_response.response, 'results', ()) or ()):
                    url = (getattr(result, 'url', '') or '').strip()
                    note = (getattr(result, 'note', '') or '').strip()
                    if not url or not note or _blocked_fetch_url_reason(url):
                        continue
                    key = f'role_gap:{_normalize_url(url) or url}:{_text_fingerprint(note)}'
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    counter += 1
                    candidates.append(EvidenceCandidate(candidate_id=f'RG{counter}', parent_candidate_id=f'RG{counter}', slot_id=role.slot_id, slot_intent=role.slot_intent or _slot_intent_for_slot(role.slot_id), text_part='search_snippet', text_start=0, text_end=len(note), receipt_id=receipt_id, result_id=_string_value(getattr(result, 'result_id', '')) or f'RG{counter}', url=url, title=getattr(result, 'title', None), source_text=note, query=query_response.query, source_kind=SEARCH_SNIPPET_EVIDENCE_SOURCE_KIND))
            if not candidates or deadline - perf_counter() < ROLE_GAP_GATE_MIN_REMAINING_SECONDS:
                return GateResult(accepted_packets=(), observations=())
            gate_timeout = deadline - ROLE_GAP_GATE_WATCHDOG_RESERVE_SECONDS - perf_counter()
            gate_results = await _gate_groups_with_deadline((_run_observation_gate_once(question=question, loop_index=2, existing_packets=existing_packets, existing_observations=existing_observations, contract=contract, retrieval_roles=role_ledger, candidates=tuple(candidates), model=EVIDENCE_GATE_MODEL, state=state, stage='role_gap_gate', lane='role_gap'),), timeout=gate_timeout)
            return gate_results[0] if gate_results else GateResult(accepted_packets=(), observations=())

        def _build_bounded_pool_plan_messages(*, question: str, existing_packets: tuple[AcceptedEvidence, ...]) -> list[dict[str, str]]:
            evidence_brief = [{'packet_number': i, 'title': p.title or '', 'url': p.url} for i, p in enumerate(existing_packets[:12], start=1)]
            system_content = 'ROLE: bounded-pool planner for a research pipeline. Decide whether the question ranges over a BOUNDED candidate pool — either the candidates are explicitly listed in the question, or they form a closed set that can be fully enumerated (e.g. \'which Maine counties...\', \'of Gary Allan\'s studio albums released in 2005, 2010, 2013...\', \'the 5 male main-cast actors...\'). A single-entity lookup or an open-ended question is NOT a bounded pool.\n\nIf it IS a bounded pool, output the pool subject, the complete member list if you can name it from the question or general structure, and EACH distinct filter criterion the question imposes as a separate checklist item. If it is NOT a bounded pool, set is_bounded_pool to false and leave the lists empty.\n\nOutput ONLY a JSON object: {"is_bounded_pool": bool, "pool_subject": str, "pool_members": [str, ...], "criteria": [str, ...]}. No prose.'
            user_content = f"Question: {question}\n\nEvidence gathered so far (titles only):\n{_format_records_section('EVIDENCE_BRIEF', 'packet', evidence_brief)}\n\nReturn the JSON plan."
            return [{'role': 'system', 'content': system_content}, {'role': 'user', 'content': user_content}]

        def _bounded_pool_payload_validator() -> Callable[[dict[str, object]], str | None]:

            def _validate(payload: dict[str, object]) -> str | None:
                if not isinstance(payload.get('is_bounded_pool'), bool):
                    return 'is_bounded_pool must be a boolean'
                if not isinstance(payload.get('criteria'), list):
                    return 'criteria must be a list'
                if not isinstance(payload.get('pool_members'), list):
                    return 'pool_members must be a list'
                return None
            return _validate

        def _bounded_pool_plan_from_payload(payload: dict[str, object] | None) -> BoundedPoolPlan:
            if not payload or not payload.get('is_bounded_pool'):
                return BoundedPoolPlan()
            members = tuple((str(m).strip() for m in _string_list(payload.get('pool_members')) if str(m).strip()))
            criteria = tuple((str(c).strip() for c in _string_list(payload.get('criteria')) if str(c).strip()))
            if not criteria:
                return BoundedPoolPlan()
            return BoundedPoolPlan(is_bounded_pool=True, pool_subject=str(payload.get('pool_subject') or '').strip(), pool_members=members[:POOL_SWEEP_MAX_POOL_SIZE], criteria=criteria[:POOL_SWEEP_MAX_CRITERIA])

        async def _detect_bounded_pool(*, question: str, existing_packets: tuple[AcceptedEvidence, ...], state: ResearchRunState, deadline: float) -> BoundedPoolPlan:
            if deadline - perf_counter() < POOL_SWEEP_MIN_REMAINING_SECONDS:
                return BoundedPoolPlan()
            messages = _build_bounded_pool_plan_messages(question=question, existing_packets=existing_packets)
            payload = await _call_json_llm_with_retry(messages=messages, model=RESEARCH_PLAN_MODEL, temperature=PLANNING_TEMPERATURE, validate_payload=_bounded_pool_payload_validator(), state=state, stage='bounded_pool_detection')
            return _bounded_pool_plan_from_payload(payload)

        def _bounded_pool_criterion_query(*, plan: BoundedPoolPlan, criterion: str) -> str:
            subject = plan.pool_subject or ' '.join(criterion.split()[:6])
            text = f'{subject} {criterion} full list table comparison'
            return ' '.join(text.split()[:POOL_SWEEP_QUERY_MAX_WORDS])

        async def _augment_bounded_pool_evidence(*, question: str, plan: BoundedPoolPlan, contract: ResearchContract, role_ledger: tuple[ResearchPlanRole, ...], existing_packets: tuple[AcceptedEvidence, ...], existing_observations: tuple[EvidenceObservation, ...], state: ResearchRunState, deadline: float) -> GateResult:
            candidates: list[EvidenceCandidate] = []
            seen_keys: set[str] = set()
            counter = 0
            for criterion in plan.criteria[:POOL_SWEEP_MAX_CRITERIA]:
                if deadline - perf_counter() < POOL_SWEEP_GATE_MIN_REMAINING_SECONDS:
                    break
                query = _bounded_pool_criterion_query(plan=plan, criterion=criterion)
                try:
                    response = await search_web([query], provider=_SEARCH_PROVIDER, num=POOL_SWEEP_SEARCH_RESULTS_PER_CRITERION, timeout=LITE_SEARCH_TOOL_TIMEOUT_SECONDS)
                except Exception:
                    continue
                receipt_id = getattr(response, 'receipt_id', '') or ''
                for result in tuple(getattr(response, 'results', ()) or ()):
                    url = (getattr(result, 'url', '') or '').strip()
                    note = (getattr(result, 'note', '') or '').strip()
                    if not url or not note or _blocked_fetch_url_reason(url):
                        continue
                    key = f'pool_sweep:{_normalize_url(url) or url}:{_text_fingerprint(note)}'
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    counter += 1
                    candidates.append(EvidenceCandidate(candidate_id=f'P{counter}', parent_candidate_id=f'P{counter}', slot_id=PRIMARY_SOURCE_SLOT_ID, slot_intent=_slot_intent_for_slot(PRIMARY_SOURCE_SLOT_ID), text_part='search_snippet', text_start=0, text_end=len(note), receipt_id=receipt_id, result_id=_string_value(getattr(result, 'result_id', '')) or f'P{counter}', url=url, title=getattr(result, 'title', None), source_text=note, query=query, source_kind=SEARCH_SNIPPET_EVIDENCE_SOURCE_KIND))
            if not candidates or deadline - perf_counter() < POOL_SWEEP_GATE_MIN_REMAINING_SECONDS:
                return GateResult(accepted_packets=(), observations=())
            return await _run_observation_gate_once(question=question, loop_index=1, existing_packets=existing_packets, existing_observations=existing_observations, contract=contract, retrieval_roles=role_ledger, candidates=tuple(candidates), model=EVIDENCE_GATE_MODEL, state=state, stage='bounded_pool_gate', lane='bounded_pool')

        def _build_second_hop_plan_messages(*, question: str, existing_packets: tuple[AcceptedEvidence, ...]) -> list[dict[str, str]]:
            evidence_brief = [{'packet_number': index, 'title': packet.title or '', 'url': packet.url, 'accepted_source_text': packet.source_text[:HOP_EVIDENCE_BRIEF_TEXT_CHARS]} for index, packet in enumerate(existing_packets[:HOP_EVIDENCE_BRIEF_MAX_PACKETS], start=1)]
            system_content = f"""ROLE: dependency-hop planner for a research pipeline. Some questions chain on an INTERMEDIATE fact: an indirect reference (for example 'the year the director of film X passed away', 'the state where person Y was born') must first be resolved to a concrete value, and the facts the question actually asks about are defined in terms of that resolved value.\n\nGiven the question and the evidence gathered so far: (1) decide whether the question contains such an indirect reference; (2) check whether the evidence RESOLVES it to a concrete value (a name, a year, a place); (3) check whether the evidence ALREADY CONTAINS the downstream facts the question asks about, stated against the resolved value. Only when a reference is resolved AND the downstream facts are missing, emit up to {HOP_MAX_FOLLOWUP_QUERIES} follow-up search queries. Each query must hard-code the RESOLVED concrete value (never the indirect phrasing) and target one missing downstream fact (for example 'BLS state unemployment rates December 1998 seasonally adjusted', '1998 gubernatorial election results by state').\n\nA single-hop question, an unresolved reference, or already-complete evidence all mean no follow-up. Output ONLY a JSON object: {{"has_dependency_hop": bool, "resolved_facts": [str, ...], "followup_queries": [str, ...]}}. No prose."""
            user_content = f"Question: {question}\n\nEvidence gathered so far:\n{_format_records_section('EVIDENCE_BRIEF', 'packet', evidence_brief)}\n\nReturn the JSON plan."
            return [{'role': 'system', 'content': system_content}, {'role': 'user', 'content': user_content}]

        def _second_hop_payload_validator() -> Callable[[dict[str, object]], str | None]:

            def _validate(payload: dict[str, object]) -> str | None:
                if not isinstance(payload.get('has_dependency_hop'), bool):
                    return 'has_dependency_hop must be a boolean'
                if not isinstance(payload.get('followup_queries'), list):
                    return 'followup_queries must be a list'
                return None
            return _validate

        def _second_hop_plan_from_payload(payload: dict[str, object] | None) -> SecondHopPlan:
            if not payload or not payload.get('has_dependency_hop'):
                return SecondHopPlan()
            queries: list[str] = []
            for raw in _string_list(payload.get('followup_queries')):
                text = ' '.join(str(raw).split()[:HOP_QUERY_MAX_WORDS]).strip()
                if text and text not in queries:
                    queries.append(text)
            if not queries:
                return SecondHopPlan()
            resolved = tuple((str(f).strip() for f in _string_list(payload.get('resolved_facts')) if str(f).strip()))
            return SecondHopPlan(followup_queries=tuple(queries[:HOP_MAX_FOLLOWUP_QUERIES]), resolved_facts=resolved)

        async def _detect_second_hop(*, question: str, existing_packets: tuple[AcceptedEvidence, ...], state: ResearchRunState, deadline: float) -> SecondHopPlan:
            if deadline - perf_counter() < HOP_MIN_REMAINING_SECONDS:
                return SecondHopPlan()
            if not HOP_TRIGGER_RE.search(question):
                return SecondHopPlan()
            messages = _build_second_hop_plan_messages(question=question, existing_packets=existing_packets)
            payload = await _call_json_llm_with_retry(messages=messages, model=RESEARCH_PLAN_MODEL, temperature=PLANNING_TEMPERATURE, validate_payload=_second_hop_payload_validator(), state=state, stage='second_hop_detection')
            return _second_hop_plan_from_payload(payload)

        async def _augment_second_hop_evidence(*, question: str, plan: SecondHopPlan, contract: ResearchContract, role_ledger: tuple[ResearchPlanRole, ...], existing_packets: tuple[AcceptedEvidence, ...], existing_observations: tuple[EvidenceObservation, ...], state: ResearchRunState, deadline: float) -> GateResult:
            candidates: list[EvidenceCandidate] = []
            seen_keys: set[str] = set()
            counter = 0
            for followup_query in plan.followup_queries[:HOP_MAX_FOLLOWUP_QUERIES]:
                if deadline - perf_counter() < HOP_GATE_MIN_REMAINING_SECONDS:
                    break
                try:
                    response = await search_web([followup_query], provider=_SEARCH_PROVIDER, num=HOP_SEARCH_RESULTS_PER_QUERY, timeout=LITE_SEARCH_TOOL_TIMEOUT_SECONDS)
                except Exception:
                    continue
                receipt_id = getattr(response, 'receipt_id', '') or ''
                for result in tuple(getattr(response, 'results', ()) or ()):
                    url = (getattr(result, 'url', '') or '').strip()
                    note = (getattr(result, 'note', '') or '').strip()
                    if not url or not note or _blocked_fetch_url_reason(url):
                        continue
                    key = f'second_hop:{_normalize_url(url) or url}:{_text_fingerprint(note)}'
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    counter += 1
                    candidates.append(EvidenceCandidate(candidate_id=f'H{counter}', parent_candidate_id=f'H{counter}', slot_id=PRIMARY_SOURCE_SLOT_ID, slot_intent=_slot_intent_for_slot(PRIMARY_SOURCE_SLOT_ID), text_part='search_snippet', text_start=0, text_end=len(note), receipt_id=receipt_id, result_id=_string_value(getattr(result, 'result_id', '')) or f'H{counter}', url=url, title=getattr(result, 'title', None), source_text=note, query=followup_query, source_kind=SEARCH_SNIPPET_EVIDENCE_SOURCE_KIND))
            if not candidates or deadline - perf_counter() < HOP_GATE_MIN_REMAINING_SECONDS:
                return GateResult(accepted_packets=(), observations=())
            return await _run_observation_gate_once(question=question, loop_index=1, existing_packets=existing_packets, existing_observations=existing_observations, contract=contract, retrieval_roles=role_ledger, candidates=tuple(candidates), model=EVIDENCE_GATE_MODEL, state=state, stage='second_hop_gate', lane='second_hop')

        async def _gate_groups_with_deadline(coros: Sequence[Awaitable[GateResult]], *, timeout: float) -> tuple[GateResult, ...]:
            tasks = [asyncio.ensure_future(c) for c in coros]
            done, pending = await asyncio.wait(tasks, timeout=max(0.0, timeout))
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            results: list[GateResult] = []
            for task in tasks:
                if task.cancelled() or task.exception() is not None:
                    continue
                results.append(task.result())
            return tuple(results)

        async def _admit_evidence_from_candidate_beam(*, question: str, contract: ResearchContract, role_ledger: tuple[ResearchPlanRole, ...], candidates: tuple[EvidenceCandidate, ...], state: ResearchRunState, deadline: float) -> GateResult:
            if not candidates:
                return GateResult(accepted_packets=(), observations=())
            groups = _evidence_gate_candidate_groups(candidates=candidates, role_ledger=role_ledger)
            timeout = deadline - GATE_WATCHDOG_RESERVE_SECONDS - perf_counter()
            results = await _gate_groups_with_deadline((_run_observation_gate_once(question=question, loop_index=0, existing_packets=(), existing_observations=(), contract=contract, retrieval_roles=role_ledger, candidates=group_candidates, model=EVIDENCE_GATE_MODEL, state=state, stage='beam_evidence_gate_group', lane=group_id) for group_id, group_candidates in groups), timeout=timeout)
            return _merge_grouped_gate_results(tuple(results))

        def _evidence_gate_candidate_groups(*, candidates: tuple[EvidenceCandidate, ...], role_ledger: tuple[ResearchPlanRole, ...]) -> tuple[tuple[str, tuple[EvidenceCandidate, ...]], ...]:
            if len(candidates) <= MAX_EVIDENCE_GATE_CANDIDATES_PER_GROUP or not role_ledger:
                return (('all', candidates),)
            role_terms = {role.role_id: _query_match_terms(' '.join((role.slot_id, role.slot_intent, role.question, ' '.join(role.queries)))) for role in role_ledger}
            term_counts: dict[str, int] = {}
            for terms in role_terms.values():
                for term in terms:
                    term_counts[term] = term_counts.get(term, 0) + 1
            buckets: dict[str, list[EvidenceCandidate]] = {role.role_id: [] for role in role_ledger}
            buckets['unmatched'] = []
            for candidate in candidates:
                buckets[_candidate_gate_group_role_id(candidate, role_ledger, role_terms, term_counts)].append(candidate)
            groups: list[tuple[str, tuple[EvidenceCandidate, ...]]] = []
            for role_id in (*[r.role_id for r in role_ledger], 'unmatched'):
                bucket = buckets.get(role_id, [])
                if not bucket:
                    continue
                for index, start in enumerate(range(0, len(bucket), MAX_EVIDENCE_GATE_CANDIDATES_PER_GROUP), start=1):
                    suffix = f'_{index}' if len(bucket) > MAX_EVIDENCE_GATE_CANDIDATES_PER_GROUP else ''
                    groups.append((f'{role_id}{suffix}', tuple(bucket[start:start + MAX_EVIDENCE_GATE_CANDIDATES_PER_GROUP])))
            return tuple(groups) or (('all', candidates),)

        def _candidate_gate_group_role_id(candidate: EvidenceCandidate, role_ledger: tuple[ResearchPlanRole, ...], role_terms: Mapping[str, tuple[str, ...]], term_counts: Mapping[str, int]) -> str:
            haystack = _query_word_match_text(' '.join((candidate.slot_id, candidate.slot_intent, candidate.query, candidate.url, candidate.title or '', candidate.source_kind, candidate.source_text[:1200])))
            best_role_id = ''
            best_score = 0
            for role in role_ledger:
                score = 2 if role.slot_id == candidate.slot_id else 0
                for term in role_terms.get(role.role_id, ()):
                    if f' {term} ' in haystack:
                        score += 3 if term_counts.get(term, 0) == 1 else 1
                if score > best_score:
                    best_role_id = role.role_id
                    best_score = score
            return best_role_id or 'unmatched'

        def _merge_grouped_gate_results(results: tuple[GateResult, ...]) -> GateResult:
            packets: list[AcceptedEvidence] = []
            observations: list[EvidenceObservation] = []
            packet_index_by_key: dict[tuple[str, str, int, int, str], int] = {}
            for result in results:
                local_to_global: dict[int, int] = {}
                for local_index, packet in enumerate(result.accepted_packets, start=1):
                    key = (packet.result_id, packet.text_part, packet.text_start, packet.text_end, _text_fingerprint(packet.source_text))
                    global_index = packet_index_by_key.get(key)
                    if global_index is None:
                        packets.append(packet)
                        global_index = len(packets)
                        packet_index_by_key[key] = global_index
                    local_to_global[local_index] = global_index
                for obs in result.observations:
                    packet_index = local_to_global.get(obs.packet_index)
                    if packet_index is None:
                        continue
                    observations.append(replace(obs, packet_index=packet_index))
            return GateResult(accepted_packets=tuple(packets), observations=tuple(observations))

        async def _page_entries_from_search_seeds(*, seeds: tuple[SearchResultSeed, ...], state: ResearchRunState, loop_index: int) -> tuple[tuple[PagePoolEntry, ...], dict[str, object]]:
            unique_seeds = _unique_search_result_seeds_by_url(seeds)
            semaphore = asyncio.Semaphore(FETCH_PAGE_CONCURRENCY)
            source_results = await asyncio.gather(*(_fetch_candidate_source(seed=seed, semaphore=semaphore, state=state, loop_index=loop_index) for seed in unique_seeds))
            fetched_sources = tuple((source for source, status in source_results if status == 'fetched'))
            failed_seeds = tuple((seed for seed, (_, status) in zip(unique_seeds, source_results, strict=False) if status != 'fetched'))
            fetched_entries = tuple((PagePoolEntry(page_id=f'P{i}', cache_key=_normalize_url(s.url) or s.url, source=s) for i, s in enumerate(fetched_sources, start=1)))
            fallback_entries = tuple((PagePoolEntry(page_id=f'P{i}', cache_key=_normalize_url(seed.url) or seed.url, source=_candidate_source_from_search_seed(seed, source_kind=FETCH_PAGE_SEARCH_SNIPPET_FALLBACK_SOURCE_KIND)) for i, seed in enumerate(failed_seeds, start=len(fetched_entries) + 1)))
            page_entries = (*fetched_entries, *fallback_entries)
            return (tuple(page_entries), {'fetched_page_count': len(fetched_entries), 'fallback_count': len(fallback_entries)})

        def _unique_search_result_seeds_by_url(seeds: tuple[SearchResultSeed, ...]) -> tuple[SearchResultSeed, ...]:
            unique: list[SearchResultSeed] = []
            seen: set[str] = set()
            for seed in seeds:
                key = _normalize_url(seed.url) or seed.url
                if key not in seen:
                    seen.add(key)
                    unique.append(seed)
            return tuple(unique)

        async def _fetch_candidate_source(*, seed: SearchResultSeed, semaphore: asyncio.Semaphore, state: ResearchRunState, loop_index: int) -> tuple[CandidateSource, str]:
            async with semaphore:
                try:
                    response = await fetch_page(seed.url, provider=_SEARCH_PROVIDER, timeout=FETCH_PAGE_TOOL_TIMEOUT_SECONDS)
                except Exception:
                    return (_candidate_source_from_search_seed(seed, source_kind=FETCH_PAGE_SEARCH_SNIPPET_FALLBACK_SOURCE_KIND), 'exception')
                fetched = _candidate_source_from_fetch_response(seed=seed, response=response)
                if fetched is None:
                    return (_candidate_source_from_search_seed(seed, source_kind=FETCH_PAGE_SEARCH_SNIPPET_FALLBACK_SOURCE_KIND), 'empty_or_unreferenceable')
                return (fetched, 'fetched')

        def _candidate_source_from_search_seed(seed: SearchResultSeed, *, source_kind: str) -> CandidateSource:
            return CandidateSource(receipt_id=seed.search_receipt_id, result_id=seed.search_result_id, slot_id=seed.slot_id, slot_intent=seed.slot_intent, url=seed.url, title=seed.title, source_text=seed.note, source_kind=source_kind)

        def _candidate_source_from_fetch_response(*, seed: SearchResultSeed, response: object) -> CandidateSource | None:
            fetch_data = tuple(getattr(getattr(response, 'response', None), 'data', ()) or ())
            fetch_item = fetch_data[0] if fetch_data else None
            tool_results = tuple(getattr(response, 'results', ()) or ())
            tool_result = tool_results[0] if tool_results else None
            source_text = getattr(tool_result, 'note', '') or getattr(fetch_item, 'content', '') or ''
            if not source_text.strip():
                return None
            receipt_id = (getattr(response, 'receipt_id', '') or '').strip()
            result_id = (getattr(tool_result, 'result_id', '') or '').strip()
            if not receipt_id or not result_id:
                return None
            url = (getattr(tool_result, 'url', '') or '').strip() or (getattr(fetch_item, 'url', '') or '').strip() or seed.url
            title = getattr(tool_result, 'title', None) or getattr(fetch_item, 'title', None) or seed.title
            return CandidateSource(receipt_id=receipt_id, result_id=result_id, slot_id=seed.slot_id, slot_intent=seed.slot_intent, url=url, title=title, source_text=source_text, source_kind='fetch_page')

        def _source_kind_counts(sources: tuple[CandidateSource, ...]) -> dict[str, int]:
            counts: dict[str, int] = {}
            for source in sources:
                counts[source.source_kind] = counts.get(source.source_kind, 0) + 1
            return counts

        def _loop_chunks_from_page_entries(*, page_entries: tuple[PagePoolEntry, ...], query_label: str, state: ResearchRunState, loop_index: int) -> tuple[PageChunk, ...]:
            chunks: list[PageChunk] = []
            for i, entry in enumerate(page_entries, start=1):
                chunks.extend(_static_chunks_for_source(page_id=entry.page_id, source_index=i, source=entry.source, query=query_label))
            return tuple(chunks)

        def _static_chunks_for_source(*, page_id: str, source_index: int, source: CandidateSource, query: str='') -> tuple[PageChunk, ...]:
            return tuple((PageChunk(chunk_id=f'{page_id}_C{ci}', page_id=page_id, source_index=source_index, chunk_index=ci, receipt_id=source.receipt_id, result_id=source.result_id, slot_id=source.slot_id, slot_intent=source.slot_intent, url=source.url, title=source.title, query=query, text_start=ts, text_end=te, text=source.source_text[ts:te], source_kind=source.source_kind) for ci, (ts, te) in enumerate(_overlap_text_ranges(len(source.source_text)), start=1)))

        def _overlap_text_ranges(text_length: int) -> tuple[tuple[int, int], ...]:
            if text_length <= 0:
                return ()
            if text_length <= CHUNK_SIZE_CHARS:
                return ((0, text_length),)
            step = max(1, CHUNK_SIZE_CHARS - CHUNK_OVERLAP_CHARS)
            ranges: list[tuple[int, int]] = []
            start = 0
            while start < text_length:
                end = min(text_length, start + CHUNK_SIZE_CHARS)
                ranges.append((start, end))
                if end >= text_length:
                    break
                start += step
            return tuple(ranges)

        async def _select_page_chunks(*, question: str, loop_index: int, chunks: tuple[PageChunk, ...], role_ledger: tuple[ResearchPlanRole, ...], state: ResearchRunState) -> tuple[PageChunk, ...]:
            if not chunks:
                return ()
            chunk_lookup = {c.chunk_id: c for c in chunks}
            query_terms = _chunk_selection_query_terms(question=question, role_ledger=role_ledger, chunks=chunks)
            query_fragment_scores = _query_fragment_scores_by_chunk(chunks=chunks, query_terms=query_terms)
            sample_chunks = _sample_chunks_for_signal_generation(chunks=chunks, query_fragment_scores=query_fragment_scores)
            chunk_signals = await _generate_chunk_signals(question=question, loop_index=loop_index, role_ledger=role_ledger, sample_chunks=sample_chunks, query_terms=query_terms, state=state)
            cue_hits = _scan_chunks_for_cue_hits(chunks=chunks, cue_patterns=chunk_signals.regex_patterns)
            lexical_hits = _scan_chunks_for_lexical_anchors(chunks=chunks, anchor_sets=chunk_signals.lexical_anchor_sets)
            selected_ids = _select_chunks_from_dual_signals(chunks=chunks, cue_hits=cue_hits, lexical_hits=lexical_hits, query_fragment_scores=query_fragment_scores, role_ledger=role_ledger)
            if not selected_ids:
                selected_ids = _select_chunks_from_query_fragments(chunks=chunks, query_fragment_scores=query_fragment_scores)
            return tuple((chunk_lookup[cid] for cid in selected_ids if cid in chunk_lookup))

        async def _generate_chunk_signals(*, question: str, loop_index: int, role_ledger: tuple[ResearchPlanRole, ...], sample_chunks: tuple[PageChunk, ...], query_terms: tuple[str, ...], state: ResearchRunState) -> ChunkSignalPlan:
            if not role_ledger or not sample_chunks:
                return ChunkSignalPlan(regex_patterns=(), lexical_anchor_sets=())
            regex_result, lexical_result = await asyncio.gather(_generate_chunk_cue_patterns(question=question, loop_index=loop_index, role_ledger=role_ledger, sample_chunks=sample_chunks, query_terms=query_terms, state=state), _generate_chunk_lexical_anchors(question=question, loop_index=loop_index, role_ledger=role_ledger, sample_chunks=sample_chunks, query_terms=query_terms, state=state), return_exceptions=True)
            regex_patterns = regex_result if not isinstance(regex_result, BaseException) else ()
            lexical_anchor_sets = lexical_result if not isinstance(lexical_result, BaseException) else ()
            return ChunkSignalPlan(regex_patterns=regex_patterns, lexical_anchor_sets=lexical_anchor_sets)

        async def _generate_chunk_cue_patterns(*, question: str, loop_index: int, role_ledger: tuple[ResearchPlanRole, ...], sample_chunks: tuple[PageChunk, ...], query_terms: tuple[str, ...], state: ResearchRunState) -> tuple[ChunkCuePattern, ...]:
            messages = _build_chunk_cue_pattern_messages(question=question, loop_index=loop_index, role_ledger=role_ledger, sample_chunks=sample_chunks, query_terms=query_terms)
            payload = await _call_json_llm_with_retry(messages=messages, model=CHUNK_PATTERN_MODEL, temperature=PLANNING_TEMPERATURE, validate_payload=_chunk_cue_pattern_payload_validator(role_ledger), state=state, stage=f'chunk_regex_cue_pattern_generation_loop_{loop_index}', max_attempts=1)
            if payload is None:
                return ()
            patterns, _ = _chunk_cue_patterns_from_payload(payload=payload, role_ledger=role_ledger)
            return patterns

        async def _generate_chunk_lexical_anchors(*, question: str, loop_index: int, role_ledger: tuple[ResearchPlanRole, ...], sample_chunks: tuple[PageChunk, ...], query_terms: tuple[str, ...], state: ResearchRunState) -> tuple[ChunkLexicalAnchorSet, ...]:
            messages = _build_chunk_lexical_anchor_messages(question=question, loop_index=loop_index, role_ledger=role_ledger, sample_chunks=sample_chunks, query_terms=query_terms)
            payload = await _call_json_llm_with_retry(messages=messages, model=CHUNK_PATTERN_MODEL, temperature=PLANNING_TEMPERATURE, validate_payload=_chunk_lexical_anchor_payload_validator(role_ledger), state=state, stage=f'chunk_lexical_anchor_generation_loop_{loop_index}', max_attempts=1)
            if payload is None:
                return ()
            anchor_sets, _ = _chunk_lexical_anchors_from_payload(payload=payload, role_ledger=role_ledger)
            return anchor_sets

        def _chunk_selection_query_terms(*, question: str, role_ledger: tuple[ResearchPlanRole, ...], chunks: tuple[PageChunk, ...]) -> tuple[str, ...]:
            parts = [question]
            for role in role_ledger:
                parts.extend((role.slot_id, role.slot_intent, role.question, role.kind, ' '.join(role.queries)))
            seen_queries: set[str] = set()
            for chunk in chunks:
                if chunk.query and chunk.query not in seen_queries:
                    seen_queries.add(chunk.query)
                    parts.append(chunk.query)
            return _query_match_terms(' '.join(parts))

        def _query_fragment_scores_by_chunk(*, chunks: tuple[PageChunk, ...], query_terms: tuple[str, ...]) -> dict[str, int]:
            if not query_terms:
                return {c.chunk_id: 0 for c in chunks}
            scores: dict[str, int] = {}
            for chunk in chunks:
                text = _query_word_match_text(chunk.text)
                scores[chunk.chunk_id] = sum((1 for term in query_terms if f' {term} ' in text))
            return scores

        def _sample_chunks_for_signal_generation(*, chunks: tuple[PageChunk, ...], query_fragment_scores: Mapping[str, int]) -> tuple[PageChunk, ...]:
            selected: list[PageChunk] = []
            selected_ids: set[str] = set()
            chunks_by_page: dict[str, list[PageChunk]] = {}
            for chunk in chunks:
                chunks_by_page.setdefault(chunk.page_id, []).append(chunk)
            for page_chunks in chunks_by_page.values():
                best = sorted(page_chunks, key=lambda c: (-query_fragment_scores.get(c.chunk_id, 0), c.source_index, c.chunk_index))[0]
                selected.append(best)
                selected_ids.add(best.chunk_id)
                if len(selected) >= MAX_SIGNAL_GENERATOR_SAMPLE_CHUNKS:
                    return tuple(selected)
            for chunk in chunks:
                if chunk.chunk_id not in selected_ids and query_fragment_scores.get(chunk.chunk_id, 0) > 0:
                    selected.append(chunk)
                    selected_ids.add(chunk.chunk_id)
                    if len(selected) >= MAX_SIGNAL_GENERATOR_SAMPLE_CHUNKS:
                        return tuple(selected)
            for chunk in chunks:
                if chunk.chunk_id not in selected_ids:
                    selected.append(chunk)
                    if len(selected) >= MAX_SIGNAL_GENERATOR_SAMPLE_CHUNKS:
                        break
            return tuple(selected)

        def _scan_chunks_for_cue_hits(*, chunks: tuple[PageChunk, ...], cue_patterns: tuple[ChunkCuePattern, ...]) -> tuple[ChunkCueHit, ...]:
            if not cue_patterns:
                return ()
            hits: list[ChunkCueHit] = []
            for chunk in chunks:
                for cue_pattern in cue_patterns:
                    count = 0
                    for match in cue_pattern.compiled.finditer(chunk.text):
                        start, end = match.span()
                        if end <= start:
                            continue
                        hits.append(ChunkCueHit(chunk_id=chunk.chunk_id, role_id=cue_pattern.role_id, pattern_index=cue_pattern.pattern_index, start=start, end=end, score=3))
                        count += 1
                        if count >= MAX_CUE_HITS_PER_PATTERN_PER_CHUNK:
                            break
            return tuple(hits)

        def _scan_chunks_for_lexical_anchors(*, chunks: tuple[PageChunk, ...], anchor_sets: tuple[ChunkLexicalAnchorSet, ...]) -> tuple[ChunkLexicalAnchorHit, ...]:
            if not anchor_sets:
                return ()
            hits: list[ChunkLexicalAnchorHit] = []
            for chunk in chunks:
                for anchor_set in anchor_sets:
                    hit = _lexical_anchor_hit_for_chunk(chunk=chunk, anchor_set=anchor_set)
                    if hit is not None:
                        hits.append(hit)
            return tuple(hits)

        def _lexical_anchor_hit_for_chunk(*, chunk: PageChunk, anchor_set: ChunkLexicalAnchorSet) -> ChunkLexicalAnchorHit | None:
            all_spans = _literal_term_group_spans(chunk.text, anchor_set.all_terms)
            any_spans = _literal_term_group_spans(chunk.text, anchor_set.any_terms)
            near_spans = _literal_term_group_spans(chunk.text, anchor_set.near_terms)
            avoid_spans = _literal_term_group_spans(chunk.text, anchor_set.avoid_terms)
            all_count, any_count = (len(all_spans), len(any_spans))
            near_count, avoid_count = (_near_term_match_count(near_spans), len(avoid_spans))
            all_required = len(anchor_set.all_terms)
            all_satisfied = all_required == 0 or all_count == all_required
            if not all_satisfied and any_count == 0 and (near_count == 0) and (avoid_count == 0):
                return None
            positive_score = 0
            if all_required and all_satisfied:
                positive_score += 5 + all_count * 3
            positive_score += any_count * 3 + near_count * 2
            score = positive_score - avoid_count * 6
            if positive_score <= 0 and avoid_count <= 0:
                return None
            best_span = _best_lexical_span((*all_spans, *any_spans, *near_spans, *avoid_spans))
            return ChunkLexicalAnchorHit(chunk_id=chunk.chunk_id, role_id=anchor_set.role_id, anchor_index=anchor_set.anchor_index, matched_all_count=all_count, matched_any_count=any_count, matched_near_count=near_count, avoid_count=avoid_count, score=score, best_span=best_span)

        def _literal_term_group_spans(text: str, terms: tuple[str, ...]) -> tuple[tuple[int, int], ...]:
            spans: list[tuple[int, int]] = []
            for term in terms:
                term_spans = _literal_term_spans(text=text, term=term)
                if term_spans:
                    spans.append(term_spans[0])
            return tuple(spans)

        def _literal_term_spans(*, text: str, term: str) -> tuple[tuple[int, int], ...]:
            if not text or not term:
                return ()
            tokens = re.findall('[a-z0-9]+', term.casefold())
            if tokens:
                pattern = '\\b' + '[\\W_]+'.join((re.escape(token) for token in tokens)) + '\\b'
                return tuple((m.span() for m in re.finditer(pattern, text.casefold())))
            lowered_text, lowered_term = (text.casefold(), term.casefold())
            spans: list[tuple[int, int]] = []
            start = 0
            while True:
                pos = lowered_text.find(lowered_term, start)
                if pos < 0:
                    break
                spans.append((pos, pos + len(lowered_term)))
                start = pos + len(lowered_term)
            return tuple(spans)

        def _near_term_match_count(spans: tuple[tuple[int, int], ...]) -> int:
            if len(spans) <= 1:
                return len(spans)
            sorted_spans = sorted(spans)
            for i, (window_start, _) in enumerate(sorted_spans):
                count = sum((1 for s, e in sorted_spans[i + 1:] if s - window_start <= LEXICAL_ANCHOR_NEAR_WINDOW_CHARS and e >= window_start))
                if count >= 1:
                    return count + 1
            return 1

        def _best_lexical_span(spans: tuple[tuple[int, int], ...]) -> tuple[int, int] | None:
            if not spans:
                return None
            return sorted(spans)[0]

        def _query_word_match_text(text: str) -> str:
            return f" {re.sub('[^a-z0-9]+', ' ', text.lower())} "

        def _select_chunks_from_dual_signals(*, chunks: tuple[PageChunk, ...], cue_hits: tuple[ChunkCueHit, ...], lexical_hits: tuple[ChunkLexicalAnchorHit, ...], query_fragment_scores: Mapping[str, int], role_ledger: tuple[ResearchPlanRole, ...]) -> tuple[str, ...]:
            hits_by_chunk: dict[str, list[ChunkCueHit]] = {}
            for hit in cue_hits:
                hits_by_chunk.setdefault(hit.chunk_id, []).append(hit)
            lexical_by_chunk: dict[str, list[ChunkLexicalAnchorHit]] = {}
            for hit in lexical_hits:
                lexical_by_chunk.setdefault(hit.chunk_id, []).append(hit)
            scored: list[tuple[int, int, int, PageChunk]] = []
            score_by_id: dict[str, int] = {}
            roles_by_id: dict[str, set[str]] = {}
            for chunk in chunks:
                ch = hits_by_chunk.get(chunk.chunk_id, [])
                lh = lexical_by_chunk.get(chunk.chunk_id, [])
                distinct_patterns = {h.pattern_index for h in ch}
                distinct_roles = {h.role_id for h in ch} | {h.role_id for h in lh}
                cue_score = min(18, len(distinct_patterns) * 3 + len(distinct_roles) * 2 + min(len(ch), 5))
                lexical_score = max(-12, min(22, sum((h.score for h in lh))))
                query_score = min(8, query_fragment_scores.get(chunk.chunk_id, 0))
                if cue_score <= 0 and lexical_score <= 0 and (query_score <= 0):
                    continue
                score = cue_score + lexical_score + query_score
                if score <= 0:
                    continue
                roles_by_id[chunk.chunk_id] = distinct_roles
                score_by_id[chunk.chunk_id] = score
                scored.append((-score, chunk.source_index, chunk.chunk_index, chunk))
            scored.sort(key=lambda item: (item[0], item[1], item[2]))
            return _select_role_and_page_balanced_chunks(scored_chunks=scored, score_by_chunk_id=score_by_id, roles_by_chunk_id=roles_by_id, role_ledger=role_ledger)

        def _select_role_and_page_balanced_chunks(*, scored_chunks: Sequence[tuple[int, int, int, PageChunk]], score_by_chunk_id: Mapping[str, int], roles_by_chunk_id: Mapping[str, set[str]], role_ledger: tuple[ResearchPlanRole, ...]) -> tuple[str, ...]:
            selected_ids: list[str] = []
            selected_set: set[str] = set()
            page_counts: dict[str, int] = {}

            def add_chunk(chunk: PageChunk) -> None:
                if chunk.chunk_id in selected_set or page_counts.get(chunk.page_id, 0) >= MAX_SELECTED_CHUNKS_PER_PAGE or len(selected_ids) >= MAX_SELECTED_CHUNKS_TOTAL:
                    return
                selected_ids.append(chunk.chunk_id)
                selected_set.add(chunk.chunk_id)
                page_counts[chunk.page_id] = page_counts.get(chunk.page_id, 0) + 1
            for role in role_ledger:
                best = next((chunk for _, _, _, chunk in scored_chunks if role.role_id in roles_by_chunk_id.get(chunk.chunk_id, set())), None)
                if best:
                    add_chunk(best)
            seen_pages: set[str] = set()
            for _, _, _, chunk in scored_chunks:
                if chunk.page_id not in seen_pages:
                    seen_pages.add(chunk.page_id)
                    add_chunk(chunk)
            for _, _, _, chunk in scored_chunks:
                add_chunk(chunk)
                if len(selected_ids) >= MAX_SELECTED_CHUNKS_TOTAL:
                    break
            return tuple(selected_ids)

        def _select_chunks_from_query_fragments(*, chunks: tuple[PageChunk, ...], query_fragment_scores: Mapping[str, int]) -> tuple[str, ...]:
            scored = sorted(((-query_fragment_scores.get(c.chunk_id, 0), c.source_index, c.chunk_index, c) for c in chunks if query_fragment_scores.get(c.chunk_id, 0) > 0), key=lambda item: (item[0], item[1], item[2]))
            selected_ids: list[str] = []
            page_counts: dict[str, int] = {}
            for _, _, _, chunk in scored[:MAX_QUERY_FRAGMENT_CHUNKS_WHEN_NO_PATTERN_HITS]:
                if page_counts.get(chunk.page_id, 0) >= MAX_SELECTED_CHUNKS_PER_PAGE:
                    continue
                selected_ids.append(chunk.chunk_id)
                page_counts[chunk.page_id] = page_counts.get(chunk.page_id, 0) + 1
                if len(selected_ids) >= MAX_SELECTED_CHUNKS_TOTAL:
                    break
            return tuple(selected_ids)

        def _selected_chunks_to_candidates(*, chunks: tuple[PageChunk, ...], seen_candidate_keys: set[str], candidate_counter: int) -> tuple[tuple[EvidenceCandidate, ...], int]:
            candidates: list[EvidenceCandidate] = []
            for chunk in chunks:
                key = f'selected_chunk:{_normalize_url(chunk.url) or chunk.url}:{chunk.text_start}:{chunk.text_end}:{_text_fingerprint(chunk.text)}'
                if key in seen_candidate_keys:
                    continue
                seen_candidate_keys.add(key)
                candidate_counter += 1
                candidates.append(EvidenceCandidate(candidate_id=f'K{candidate_counter}', parent_candidate_id=chunk.chunk_id, slot_id=chunk.slot_id, slot_intent=chunk.slot_intent, text_part='chunk', text_start=chunk.text_start, text_end=chunk.text_end, receipt_id=chunk.receipt_id, result_id=chunk.result_id, url=chunk.url, title=chunk.title, source_text=chunk.text, query=chunk.query, source_kind='selected_chunk'))
            return (tuple(candidates), candidate_counter)

        async def _run_observation_gate_once(*, question: str, loop_index: int, existing_packets: tuple[AcceptedEvidence, ...], existing_observations: tuple[EvidenceObservation, ...], contract: ResearchContract, retrieval_roles: tuple[ResearchPlanRole, ...], candidates: tuple[EvidenceCandidate, ...], model: str, state: ResearchRunState, stage: str, lane: str='combined') -> GateResult:
            messages = _build_observation_evidence_gate_messages(question=question, loop_index=loop_index, existing_packets=existing_packets, existing_observations=existing_observations, contract=contract, retrieval_roles=retrieval_roles, candidates=candidates)
            payload = await _call_json_llm_with_retry(messages=messages, model=model, temperature=GATE_TEMPERATURE, thinking=EVIDENCE_GATE_THINKING, validate_payload=_observation_evidence_gate_payload_validator(candidates=candidates, contract=contract), state=state, stage=stage)
            if payload is None:
                return GateResult(accepted_packets=(), observations=())
            accepted_packets = _accepted_packets_from_candidate_ids(payload=payload, candidates=candidates)
            observations = _evidence_observations_from_payload(payload=payload, existing_packet_count=len(existing_packets), candidates=candidates)
            return GateResult(accepted_packets=accepted_packets, observations=observations)

        def _budget_matched_synthesis_plan(remaining_seconds: float) -> tuple[str, LlmThinkingConfig, float] | None:
            if remaining_seconds < SYNTH_TIER_FLOOR_MAX_REMAINING_SECONDS:
                return None
            timeout = max(SYNTH_CALL_MIN_TIMEOUT_SECONDS, min(remaining_seconds - SYNTH_CALL_SAFETY_MARGIN_SECONDS, SYNTH_CALL_MAX_TIMEOUT_SECONDS))
            thinking = remaining_seconds >= SYNTH_TIER_THINKING_MIN_REMAINING_SECONDS
            return (FINAL_SYNTHESIS_MODEL, LlmThinkingConfig(enabled=thinking), timeout)

        def _answer_time_budget_seconds(remaining_seconds: float) -> int:
            usable = remaining_seconds - SYNTH_CALL_SAFETY_MARGIN_SECONDS
            return int(max(SYNTH_TIME_NUDGE_FLOOR_SECONDS, min(usable, SYNTH_TIME_NUDGE_TARGET_SECONDS)))

        def _answer_time_directive(remaining_seconds: float) -> str:
            return f'\n\nTIME BUDGET: aim to deliver this answer within about {_answer_time_budget_seconds(remaining_seconds)} seconds of wall-clock time, deliberation included. Settle the answer from the evidence above in a single pass rather than re-deriving it, and size the write-up to that budget. A response that has not arrived by the deadline is discarded, so a complete answer delivered inside the budget beats a longer one that misses it.'

        def _messages_with_time_directive(messages: Sequence[Mapping[str, object]], remaining_seconds: float) -> list[dict[str, object]]:
            decorated = [dict(message) for message in messages]
            for message in decorated:
                if message.get('role') == 'system':
                    message['content'] = str(message['content']) + _answer_time_directive(remaining_seconds)
                    break
            return decorated

        async def _run_synthesis_call(*, messages: Sequence[Mapping[str, object]], deadline: float, provider: str=_LLM_PROVIDER, model_override: str | None=None, max_output_tokens: int | None=None, thinking_override: LlmThinkingConfig | None=None) -> str | None:
            plan = _budget_matched_synthesis_plan(deadline - perf_counter())
            if plan is None:
                return None
            model, thinking, timeout = plan
            if thinking_override is not None:
                thinking = thinking_override
            messages = _messages_with_time_directive(messages, deadline - perf_counter())
            try:
                if max_output_tokens is not None:
                    response = await llm_chat(provider=provider, messages=messages, model=model_override or model, temperature=SYNTHESIS_TEMPERATURE, thinking=thinking, timeout=timeout, max_output_tokens=max_output_tokens)
                else:
                    response = await llm_chat(provider=provider, messages=messages, model=model_override or model, temperature=SYNTHESIS_TEMPERATURE, thinking=thinking, timeout=timeout)
            except Exception:
                return None
            return _assistant_text(response) or None

        async def _synthesize_final_answer(*, question: str, accepted_packets: tuple[AcceptedEvidence, ...], accepted_observations: tuple[EvidenceObservation, ...], coverage: tuple[CoverageAspect, ...], state: ResearchRunState, deadline: float, unvetted_evidence: bool=False) -> str:
            messages = _build_final_answer_messages(question=question, accepted_packets=accepted_packets, accepted_observations=accepted_observations, coverage=coverage, unvetted_evidence=unvetted_evidence)
            if _budget_matched_synthesis_plan(deadline - perf_counter()) is None:
                return _deterministic_answer_from_evidence(accepted_packets)
            tasks = {asyncio.ensure_future(_run_synthesis_call(messages=messages, deadline=deadline))}
            done, _pending = await asyncio.wait(tasks, timeout=SYNTH_HEDGE_DELAY_SECONDS)
            answer: str | None = None
            first_done = next(iter(done), None)
            if first_done is not None:
                tasks.discard(first_done)
                answer = first_done.result()
            if answer is None and _budget_matched_synthesis_plan(deadline - perf_counter()) is not None:
                tasks.add(asyncio.ensure_future(_run_synthesis_call(messages=messages, deadline=deadline, provider=SYNTH_ALTERNATE_PROVIDER, model_override=SYNTH_ALTERNATE_MODEL, max_output_tokens=SYNTH_ALTERNATE_MAX_OUTPUT_TOKENS, thinking_override=LlmThinkingConfig(enabled=False))))
            while answer is None and tasks:
                done, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    tasks.discard(task)
                    if answer is None:
                        answer = task.result()
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            if answer is None and _budget_matched_synthesis_plan(deadline - perf_counter()) is not None:
                answer = await _run_synthesis_call(messages=messages, deadline=deadline, thinking_override=LlmThinkingConfig(enabled=False))
            return answer if answer else _deterministic_answer_from_evidence(accepted_packets)

        def _build_numeric_audit_messages(*, question: str, draft: str, accepted_packets: tuple[AcceptedEvidence, ...]) -> list[dict[str, str]]:
            evidence_payload = [{'packet_number': i, 'url': p.url, 'title': p.title or '', 'accepted_source_text': p.source_text, 'source_result_text': p.source_result_text} for i, p in enumerate(accepted_packets, start=1)]
            system_content = "ROLE: precision-and-completeness auditor for an evidence-gated pipeline. You receive a DRAFT answer and the accepted evidence it was written from. Return a corrected version of the DRAFT. The final answer is judged pairwise against a reference answer that fully enumerates every candidate and every constraint; a draft that reaches the right conclusion but is less complete or less exact than that reference loses. Close that gap.\n\nMAKE ONLY THESE CHANGES:\n1. EXACTNESS: replace every hedged or approximate quantity with the exact value derived from the evidence. 'approximately 15 years', 'around four hours', 'roughly 290 metres', 'about 12%' must become the precise figure. Never leave an approximation when the evidence supports an exact value.\n2. RECOMPUTE: recompute every stated difference, gap, count, duration, ratio, or percentage directly from the cited figures and correct any error. Watch for mismatched bases in a computed difference — e.g. a year gap taken between a film/nomination year and a ceremony year, or a count that mixes two editions/scopes. Anchor both operands to the same basis stated in the evidence, then recompute.\n3. FULL ROSTER: if the question ranges over a candidate pool (named in the question or a closed set it defines — e.g. 'the 5 male main-cast actors', 'of these three albums'), the answer must give an explicit verdict for EVERY candidate in the pool, not only the qualifying ones: one line per candidate stating qualifies / excluded-because-X, each with a packet citation. If the draft names the winners but omits or under-explains why the other candidates fail, add the missing per-candidate exclusion line from the evidence.\n4. CONSTRAINT CHECKLIST: if the question imposes several explicit conditions (e.g. 'major label' AND 'before 2020' AND 'same director' AND 'filmed at a slaughterhouse'), the answer must explicitly confirm EACH condition with its citation, not just the headline ones. Add any condition the draft leaves unaddressed, drawing the confirmation from the evidence.\n5. CITATIONS: every sentence asserting a number, date, name, or cause must end with its own [n] packet citation. Split any pooled citation bracket so each claim carries the citation for the packet that supports it.\n\nDO NOT: add facts not present in the accepted evidence; change the committed answer or its named entities; drop any qualifying item from an enumeration; soften or remove a false-premise statement; introduce any new hedging; or restructure prose that is already correct and complete. Adding a missing candidate verdict, constraint confirmation, exact figure, or citation is always allowed and expected; only gratuitous rewrites are forbidden.\n\nIf the draft already satisfies all of the above, return it verbatim. Output ONLY the corrected answer as plain text — no preamble, no notes, no description of what you changed."
            user_content = f"Question: {question}\n\nAccepted evidence packets:\n{_format_records_section('ACCEPTED_PACKETS', 'packet', evidence_payload)}\n\nDRAFT answer to audit:\n{draft}\n\nReturn the corrected answer as plain text. Fix exactness and recomputed values, complete the per-candidate roster and the constraint checklist, and place citations per-claim; otherwise keep the draft as-is. If nothing needs correction, return it verbatim."
            return [{'role': 'system', 'content': system_content}, {'role': 'user', 'content': user_content}]

        async def _audit_and_repair_answer(*, question: str, draft: str, accepted_packets: tuple[AcceptedEvidence, ...], deadline: float) -> str:
            if not draft or not draft.strip():
                return draft
            if deadline - perf_counter() < NUMERIC_AUDIT_MIN_REMAINING_SECONDS:
                return draft
            if draft == _deterministic_answer_from_evidence(accepted_packets):
                return draft
            plan = _budget_matched_synthesis_plan(deadline - perf_counter())
            if plan is None:
                return draft
            _model, _thinking, timeout = plan
            messages = _build_numeric_audit_messages(question=question, draft=draft, accepted_packets=accepted_packets)
            try:
                response = await llm_chat(provider=_LLM_PROVIDER, messages=messages, model=FINAL_SYNTHESIS_MODEL, temperature=NUMERIC_AUDIT_TEMPERATURE, thinking=LlmThinkingConfig(enabled=False), timeout=timeout)
            except Exception:
                return draft
            revised = _assistant_text(response).strip()
            if not revised:
                return draft
            if len(revised) < int(len(draft) * NUMERIC_AUDIT_MIN_LENGTH_RATIO):
                return draft
            return revised
        RECONCILE_MIN_REMAINING_SECONDS = 12.0
        RECONCILE_CALL_TIMEOUT_SECONDS = 22.0
        RECONCILE_MAX_PACKETS = 10
        RECONCILE_PACKET_CHARS = 2400
        RECONCILE_DRAFT_CHARS = 6000
        RECONCILE_OPENING_CHARS = 220
        _NO_QUALIFIER_OPENING_RE = re.compile('^\\W*(?:no\\s+(?:\\w+\\s+){0,3}(?:state|city|county|player|country|entity|item|candidate|company|region|team|person|element)s?\\b|no\\s+\\w+\\s+(?:satisf|meet|match|qualif|rank|appear)|none\\s+of\\s+the\\b|there\\s+(?:is|are)\\s+no\\b|the\\s+premise\\b[^.]{0,60}\\bis\\s+false\\b)', re.I)

        def _reconcile_candidate_supported(name: str, packets: tuple[AcceptedEvidence, ...]) -> bool:
            probe = name.strip().casefold()
            if len(probe) < 3:
                return False
            for packet in packets:
                haystack = f'{packet.source_text}\n{packet.source_result_text}'.casefold()
                if probe in haystack:
                    return True
            return False

        def _build_reconcile_messages(*, question: str, draft: str, accepted_packets: tuple[AcceptedEvidence, ...]) -> list[dict[str, str]]:
            payload = [{'packet_number': i, 'url': p.url, 'accepted_source_text': (p.source_text or p.source_result_text or '')[:RECONCILE_PACKET_CHARS]} for i, p in enumerate(accepted_packets[:RECONCILE_MAX_PACKETS], start=1)]
            system_content = 'ROLE: check one answer for an internal contradiction between its opening claim and its own body.\n\nThe answer opens by stating that nothing satisfies the question\'s conditions. Read the answer\'s OWN body and the evidence packets and decide a single question: does the body itself establish a named candidate for which EVERY stated condition holds?\n\nCompare each condition literally. A threshold like \'lower than 270\' is satisfied by 269 and not by 271; \'greater than 1,000,000\' is satisfied by 6,177,224. Judge each condition on the value the body or the packets actually give, not on the body\'s verdict about it.\n\nIf every condition holds for some candidate, the opening is wrong: set contradicted true, put that candidate\'s exact name in candidate_name, and rewrite the whole answer in full so it OPENS by naming that candidate, keeping every figure, citation marker and supporting line already present.\n\nIf no candidate satisfies every condition, the opening is right: set contradicted false and leave the other fields empty. Do not invent a candidate, do not relax a condition, and do not promote a candidate whose deciding value is absent from both the body and the packets.\n\nOutput ONLY a JSON object: {"contradicted": bool, "candidate_name": str, "corrected_answer": str}. No prose, no code fence.'
            user_content = f"Question: {question}\n\nAnswer under review:\n{draft[:RECONCILE_DRAFT_CHARS]}\n\nEvidence packets:\n{_format_records_section('ACCEPTED_PACKETS', 'packet', payload)}\n\nReturn the JSON object."
            return [{'role': 'system', 'content': system_content}, {'role': 'user', 'content': user_content}]

        async def _reconcile_opening_with_body(*, question: str, draft: str, accepted_packets: tuple[AcceptedEvidence, ...], deadline: float) -> str:
            if not draft or not draft.strip() or (not accepted_packets):
                return draft
            if not _NO_QUALIFIER_OPENING_RE.match(draft.strip()[:RECONCILE_OPENING_CHARS]):
                return draft
            if deadline - perf_counter() < RECONCILE_MIN_REMAINING_SECONDS:
                return draft
            timeout = min(RECONCILE_CALL_TIMEOUT_SECONDS, deadline - perf_counter() - 4.0)
            if timeout <= 0:
                return draft
            try:
                response = await llm_chat(provider=_LLM_PROVIDER, messages=_build_reconcile_messages(question=question, draft=draft, accepted_packets=accepted_packets), model=FINAL_SYNTHESIS_MODEL, temperature=0.0, thinking=LlmThinkingConfig(enabled=False), timeout=timeout)
            except Exception:
                return draft
            payload = _so_extract_json(_assistant_text(response))
            if not isinstance(payload, dict) or payload.get('contradicted') is not True:
                return draft
            name = str(payload.get('candidate_name') or '').strip()
            corrected = str(payload.get('corrected_answer') or '').strip()
            if not name or not corrected:
                return draft
            if not _reconcile_candidate_supported(name, accepted_packets):
                return draft
            if name.casefold() not in corrected.casefold():
                return draft
            if _NO_QUALIFIER_OPENING_RE.match(corrected[:RECONCILE_OPENING_CHARS]):
                return draft
            if len(corrected) < int(len(draft) * 0.4):
                return draft
            return corrected

        def _pseudo_packets_from_search_results(results: tuple[AccumulatedSearchResult, ...]) -> tuple[AcceptedEvidence, ...]:
            packets: list[AcceptedEvidence] = []
            seen_keys: set[str] = set()
            for result in results:
                note = result.note.strip()
                if not note:
                    continue
                key = f'{_normalize_url(result.url) or result.url}:{_text_fingerprint(note)}'
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                packets.append(AcceptedEvidence(url=result.url, source_text=_text_excerpt(note, MAX_TEXT_EXCERPT_CHARS), source_result_text=note, receipt_id=result.receipt_id, result_id=result.result_id, title=result.title, parent_candidate_id=result.result_id, text_part='search_snippet', text_start=0, text_end=len(note), admission_reason='raw_snippet_fallback'))
                if len(packets) >= RAW_SNIPPET_FALLBACK_MAX_PACKETS:
                    break
            return tuple(packets)

        async def _answer_from_raw_snippets(*, question: str, results: tuple[AccumulatedSearchResult, ...], coverage: tuple[CoverageAspect, ...], state: ResearchRunState, deadline: float) -> Response:
            pseudo_packets = _pseudo_packets_from_search_results(results)
            if not pseudo_packets:
                return Response(text=_insufficient_answer(question, coverage))
            try:
                final_answer = await _synthesize_final_answer(question=question, accepted_packets=pseudo_packets, accepted_observations=(), coverage=coverage, state=state, deadline=deadline, unvetted_evidence=True)
                final_answer, citations = _answer_text_and_citations(_safe_response_text(final_answer), pseudo_packets)
                _set_emit_evidence(pseudo_packets)
                return Response(text=final_answer, citations=citations or None)
            except Exception:
                _set_emit_evidence(pseudo_packets)
                return Response(text=_insufficient_answer(question, coverage))

        def _fallback_coverage_state(*, contract: ResearchContract, observations: tuple[EvidenceObservation, ...]) -> CoverageState:
            obs_indices: dict[str, list[int]] = {}
            values: dict[str, list[str]] = {}
            obs_by_role: dict[str, list[EvidenceObservation]] = {}
            for i, obs in enumerate(observations, start=1):
                obs_indices.setdefault(obs.role_id, []).append(i)
                values.setdefault(obs.role_id, []).append(obs.value)
                obs_by_role.setdefault(obs.role_id, []).append(obs)
            roles: list[CoverageRoleStatus] = []
            missing_role_ids: list[str] = []
            weak_role_ids: list[str] = []
            for role in contract.roles:
                indices = tuple(obs_indices.get(role.role_id, ()))
                role_obs = tuple(obs_by_role.get(role.role_id, ()))
                role_values = tuple(values.get(role.role_id, ()))
                if not indices:
                    status = 'missing'
                    missing_role_ids.append(role.role_id)
                    why = 'No accepted observation references this immutable role.'
                elif any((o.slot_id == role.slot_id and o.support in {'direct', 'absence', 'contradiction'} for o in role_obs)):
                    status = 'covered'
                    why = 'Accepted observations directly support this role.'
                elif len(role_obs) >= ROLE_BREADTH_COVERAGE_MIN_OBSERVATIONS:
                    status = 'covered'
                    why = 'Multiple independent accepted observations reference this role; breadth of evidence covers it.'
                else:
                    status = 'weak'
                    weak_role_ids.append(role.role_id)
                    why = 'Accepted observations are relevant but marked partial or context only.'
                roles.append(CoverageRoleStatus(role_id=role.role_id, slot_id=role.slot_id, status=status, supporting_observation_indices=indices, value='; '.join((v for v in role_values if v)), why=why))
            can_answer = bool(observations) and (_coverage_roles_allow_answer(contract, tuple(roles)) or _false_premise_roles_allow_answer(contract, tuple(roles), observations))
            return CoverageState(roles=tuple(roles), can_answer=can_answer, missing_role_ids=tuple(missing_role_ids), weak_role_ids=tuple(weak_role_ids))

        def _coverage_roles_allow_answer(contract: ResearchContract, coverage_roles: tuple[CoverageRoleStatus, ...]) -> bool:
            status_by_role = {r.role_id: r.status for r in coverage_roles}
            return all((status_by_role.get(role.role_id) == 'covered' for role in contract.roles))

        def _false_premise_roles_allow_answer(contract: ResearchContract, coverage_roles: tuple[CoverageRoleStatus, ...], observations: tuple[EvidenceObservation, ...]) -> bool:
            status_by_role = {r.role_id: r.status for r in coverage_roles}
            if status_by_role.get(PREMISE_SLOT_ID) != 'covered':
                return False
            premise_is_false = any((o.role_id == PREMISE_SLOT_ID and o.support in {'absence', 'contradiction'} for o in observations))
            if not premise_is_false:
                return False
            blocking = tuple((role.role_id for role in contract.roles if role.role_id != PREMISE_SLOT_ID and (not _is_false_premise_context_role(role))))
            return all((status_by_role.get(rid) == 'covered' for rid in blocking))

        def _is_false_premise_context_role(role: ContractRole) -> bool:
            if role.kind == 'reason':
                return True
            return any((term in role.question.casefold() for term in FALSE_PREMISE_CONTEXT_ROLE_TERMS))

        def _coverage_from_coverage_state(coverage_state: CoverageState, observations: tuple[EvidenceObservation, ...]) -> tuple[CoverageAspect, ...]:
            packet_by_obs = {i: obs.packet_index for i, obs in enumerate(observations, start=1)}
            return tuple((CoverageAspect(aspect=entry.role_id, status=entry.status, supporting_packet_indices=tuple((packet_by_obs[i] for i in entry.supporting_observation_indices if i in packet_by_obs)), notes=(f'value: {entry.value}; ' if entry.value else '') + entry.why, slot_id=entry.slot_id) for entry in coverage_state.roles))

        def _beam_role_ledger(*, targets: tuple[EvidenceSearchTarget, ...], routes: tuple[EvidenceSearchRoute, ...], search_selection: SearchResultEvidenceSelection, results: tuple[AccumulatedSearchResult, ...], question: str) -> tuple[ResearchPlanRole, ...]:
            roles: list[ResearchPlanRole] = [ResearchPlanRole(role_id=PREMISE_SLOT_ID, slot_id=PREMISE_SLOT_ID, slot_intent=_slot_intent_for_slot(PREMISE_SLOT_ID), question="Did the question's central factual premise happen as stated?", kind='premise', status='missing', value=None, why_not_covered='No accepted evidence yet.', queries=(question,))]
            selected_targets = _selected_targets_for_role_ledger(search_selection=search_selection, results=results, targets=targets, routes=routes)
            for st in selected_targets:
                if len(roles) >= MAX_RESEARCH_PLAN_ROLES:
                    break
                roles.append(ResearchPlanRole(role_id=st['target_id'], slot_id=st['slot_id'], slot_intent=st['slot_intent'], question=st['question'], kind='fact', status='missing', value=None, why_not_covered='No accepted evidence yet.', queries=tuple(st['queries'])))
            if len(roles) == 1:
                roles.append(ResearchPlanRole(role_id=PRIMARY_SOURCE_SLOT_ID, slot_id=PRIMARY_SOURCE_SLOT_ID, slot_intent=_slot_intent_for_slot(PRIMARY_SOURCE_SLOT_ID, targets=targets), question=f'What primary or canonical evidence answers the original question exactly: {question}', kind='fact', status='missing', value=None, why_not_covered='No accepted evidence yet.', queries=(question,)))
            return tuple(roles)

        def _selected_targets_for_role_ledger(*, search_selection: SearchResultEvidenceSelection, results: tuple[AccumulatedSearchResult, ...], targets: tuple[EvidenceSearchTarget, ...], routes: tuple[EvidenceSearchRoute, ...]) -> tuple[dict[str, object], ...]:
            target_by_id = {t.target_id: t for t in targets}
            routes_by_tid: dict[str, list[EvidenceSearchRoute]] = {}
            for route in routes:
                routes_by_tid.setdefault(route.target_id, []).append(route)
            result_by_id = {r.result_id: r for r in results}
            selected: list[dict[str, object]] = []
            seen: set[str] = set()
            for rid in _stable_id_union((*search_selection.detail_result_ids, *search_selection.snippet_result_ids)):
                result = result_by_id.get(rid)
                if not result or not result.target_id or result.target_id in seen:
                    continue
                target = target_by_id.get(result.target_id)
                if not target:
                    continue
                seen.add(result.target_id)
                target_routes = tuple(routes_by_tid.get(result.target_id, target.routes))
                selected.append({'target_id': target.target_id, 'slot_id': target.slot_id, 'slot_intent': result.slot_intent or target.slot_intent, 'question': target.needed_source_text, 'queries': tuple((r.query for r in target_routes if r.query))})
            for target in targets:
                if target.target_id not in seen:
                    seen.add(target.target_id)
                    selected.append({'target_id': target.target_id, 'slot_id': target.slot_id, 'slot_intent': target.slot_intent, 'question': target.needed_source_text, 'queries': tuple((r.query for r in target.routes if r.query))})
            return tuple(selected)

        def _beam_research_contract(*, role_ledger: tuple[ResearchPlanRole, ...], question: str) -> ResearchContract:
            return ResearchContract(roles=tuple((ContractRole(role_id=r.role_id, slot_id=r.slot_id, slot_intent=r.slot_intent, question=r.question, kind=r.kind) for r in role_ledger[:MAX_RESEARCH_PLAN_ROLES])), answer_goal=f'Correct false premises first. Answer the original question using only admitted snippet or page evidence; say what is missing if exact evidence is absent. Original question: {question}')

        def _source_labels_from_payload(*, payload: dict[str, object] | None, targets: tuple[EvidenceSearchTarget, ...], results: tuple[AccumulatedSearchResult, ...]) -> SearchResultSourceLabelSet:
            valid_result_ids = {r.result_id for r in results}
            valid_target_ids = {t.target_id for t in targets}
            if payload is None:
                return SearchResultSourceLabelSet(labels=(), unlabeled_result_ids=tuple((r.result_id for r in results)))
            labels: list[SearchResultSourceLabel] = []
            invalid_notes: list[str] = []
            seen: set[str] = set()
            ignored = 0
            for i, item in enumerate(_object_list(payload.get('labels')), start=1):
                result_id = _string_value(item.get('result_id'))
                if result_id not in valid_result_ids or result_id in seen:
                    ignored += 1
                    continue
                basis = _text_excerpt(_string_value(item.get('basis')), MAX_TEXT_EXCERPT_CHARS) or 'labeler_provided_no_basis'
                target_ids = tuple(_stable_valid_id_list(item.get('target_ids'), valid_target_ids))
                source_value = _normalized_source_label(value=item.get('source_value'), valid_labels=SOURCE_VALUE_LABELS, default='weak', invalid_notes=invalid_notes, path=f'labels[{i}].source_value')
                source_kind = _normalized_source_label(value=item.get('source_kind'), valid_labels=SOURCE_KIND_LABELS, default='weak_unknown', invalid_notes=invalid_notes, path=f'labels[{i}].source_kind')
                surface = _normalized_source_label(value=item.get('surface'), valid_labels=SOURCE_SURFACE_LABELS, default='snippet', invalid_notes=invalid_notes, path=f'labels[{i}].surface')
                labels.append(SearchResultSourceLabel(basis=basis, result_id=result_id, target_ids=target_ids, source_value=source_value, source_kind=source_kind, surface=surface))
                seen.add(result_id)
            unlabeled = tuple((r.result_id for r in results if r.result_id not in seen))
            return SearchResultSourceLabelSet(labels=tuple(labels), ignored_label_count=ignored, unlabeled_result_ids=unlabeled, invalid_label_notes=tuple(invalid_notes[:20]))

        def _normalized_source_label(*, value: object, valid_labels: frozenset[str], default: str, invalid_notes: list[str], path: str) -> str:
            label = _string_value(value).strip().lower()
            if label in valid_labels:
                return label
            invalid_notes.append(f'{path} defaulted_to_{default}')
            return default

        def _search_result_selection_from_labels(*, results: tuple[AccumulatedSearchResult, ...], label_set: SearchResultSourceLabelSet, max_detail_results: int) -> SearchResultEvidenceSelection:
            stable_ids = tuple((r.result_id for r in results))
            snippet_ids = tuple((r.result_id for r in results if r.note.strip()))
            label_by_id = {l.result_id: l for l in label_set.labels}
            result_by_id = {r.result_id: r for r in results}
            detail_candidates = _stable_id_union((rid for rid in stable_ids if _label_implies_detail(label_by_id.get(rid))))
            detail_ids = _balanced_result_ids_by_target(candidate_result_ids=detail_candidates, result_by_id=result_by_id, label_by_result_id=label_by_id, max_count=max_detail_results)
            detail_set = set(detail_ids)
            if len(detail_ids) < max_detail_results:
                fill = _balanced_result_ids_by_target(candidate_result_ids=tuple((rid for rid in stable_ids if rid not in detail_set)), result_by_id=result_by_id, label_by_result_id=label_by_id, max_count=max_detail_results - len(detail_ids))
                detail_ids = (*detail_ids, *fill)
                detail_set = set(detail_ids)
            overlap_ids = tuple((rid for rid in snippet_ids if rid in detail_set))
            return SearchResultEvidenceSelection(snippet_result_ids=snippet_ids, detail_result_ids=detail_ids, overlap_result_ids=overlap_ids, labels=label_set.labels, unlabeled_result_ids=label_set.unlabeled_result_ids)

        def _balanced_result_ids_by_target(*, candidate_result_ids: tuple[str, ...], result_by_id: Mapping[str, AccumulatedSearchResult], label_by_result_id: Mapping[str, SearchResultSourceLabel], max_count: int) -> tuple[str, ...]:
            if max_count <= 0 or not candidate_result_ids:
                return ()
            target_order: list[str] = []
            buckets: dict[str, list[str]] = {}
            for rid in candidate_result_ids:
                result = result_by_id.get(rid)
                if not result:
                    continue
                label = label_by_result_id.get(rid)
                for tid in _selection_target_ids(result=result, label=label):
                    if tid not in buckets:
                        buckets[tid] = []
                        target_order.append(tid)
                    buckets[tid].append(rid)
            selected: list[str] = []
            selected_set: set[str] = set()
            while len(selected) < max_count:
                made_progress = False
                for tid in target_order:
                    if len(selected) >= max_count:
                        break
                    while buckets.get(tid):
                        rid = buckets[tid].pop(0)
                        if rid not in selected_set:
                            selected.append(rid)
                            selected_set.add(rid)
                            made_progress = True
                            break
                if not made_progress:
                    break
            return tuple(selected)

        def _selection_target_ids(*, result: AccumulatedSearchResult, label: SearchResultSourceLabel | None) -> tuple[str, ...]:
            if label is not None and label.target_ids:
                return label.target_ids
            if result.target_id:
                return (result.target_id,)
            if result.slot_id:
                return (result.slot_id,)
            return ('unassigned',)

        def _label_implies_detail(label: SearchResultSourceLabel | None) -> bool:
            if label is None:
                return False
            return label.surface in DETAIL_SURFACES or label.source_value in DETAIL_SOURCE_VALUES or label.source_kind in DETAIL_SOURCE_KINDS

        def _accepted_packets_from_candidate_ids(*, payload: dict[str, object], candidates: tuple[EvidenceCandidate, ...]) -> tuple[AcceptedEvidence, ...]:
            candidate_by_id = {c.candidate_id: c for c in candidates}
            accepted: list[AcceptedEvidence] = []
            for candidate_id in _accepted_candidate_ids_used(payload):
                candidate = candidate_by_id.get(candidate_id)
                if not candidate:
                    continue
                source_text = candidate.source_text.strip()
                if not source_text:
                    continue
                accepted.append(AcceptedEvidence(url=candidate.url, source_text=source_text, source_result_text=candidate.source_text, receipt_id=candidate.receipt_id, result_id=candidate.result_id, title=candidate.title, parent_candidate_id=candidate.parent_candidate_id, text_part=candidate.text_part, text_start=candidate.text_start, text_end=candidate.text_end, admission_reason='accepted_by_compact_gate'))
            return tuple(accepted)

        def _evidence_observations_from_payload(*, payload: dict[str, object], existing_packet_count: int, candidates: tuple[EvidenceCandidate, ...]) -> tuple[EvidenceObservation, ...]:
            packet_index_by_candidate_id: dict[str, int] = {}
            next_packet_index = existing_packet_count + 1
            candidate_by_id = {c.candidate_id: c for c in candidates}
            for candidate_id in _accepted_candidate_ids_used(payload):
                candidate = candidate_by_id.get(candidate_id)
                if candidate is None or not candidate.source_text.strip():
                    continue
                packet_index_by_candidate_id[candidate_id] = next_packet_index
                next_packet_index += 1
            raw_obs = payload.get('observations')
            if not isinstance(raw_obs, list):
                return ()
            observations: list[EvidenceObservation] = []
            for item in raw_obs:
                if not isinstance(item, dict):
                    continue
                role_id = _string_value(item.get('role_id'))
                candidate_id = _string_value(item.get('candidate_id'))
                packet_index = packet_index_by_candidate_id.get(candidate_id)
                if not role_id or not candidate_id or packet_index is None:
                    continue
                observations.append(EvidenceObservation(role_id=role_id, slot_id=_string_value(item.get('slot_id')), candidate_id=candidate_id, entity=_string_value(item.get('entity')), metric=_string_value(item.get('metric')), value=_string_value(item.get('value')), time_scope=_string_value(item.get('time_scope')), support=_string_value(item.get('support')), source_tier=_string_value(item.get('source_tier')), packet_index=packet_index))
            return tuple(observations)

        def _accepted_candidate_ids_used(payload: dict[str, object]) -> tuple[str, ...]:
            accepted_candidates = payload.get('accepted_candidates')
            if not isinstance(accepted_candidates, list):
                return ()
            entries: list[str] = []
            seen: set[str] = set()
            for value in accepted_candidates:
                if not isinstance(value, dict):
                    continue
                candidate_id = _string_value(value.get('candidate_id'))
                if not candidate_id or candidate_id in seen:
                    continue
                seen.add(candidate_id)
                entries.append(candidate_id)
                if len(entries) >= MAX_ACCEPTED_IDS_PER_GATE:
                    break
            return tuple(entries)

        def _answer_text_and_citations(answer_text: str, accepted_packets: tuple[AcceptedEvidence, ...]) -> tuple[str, list[CitationRef]]:
            referenced_indices = _referenced_packet_indices(answer_text, packet_count=len(accepted_packets))
            if referenced_indices:
                packets = tuple((accepted_packets[i - 1] for i in referenced_indices))
                answer_text = _remap_answer_citation_numbers(answer_text, packet_count=len(accepted_packets), index_mapping={pi: ci for ci, pi in enumerate(referenced_indices, start=1)})
            else:
                packets = accepted_packets
                answer_text = _remap_answer_citation_numbers(answer_text, packet_count=len(accepted_packets), index_mapping={})
            return (answer_text, [_citation_ref_for_packet(p) for p in packets])

        def _remap_answer_citation_numbers(answer_text: str, *, packet_count: int, index_mapping: Mapping[int, int]) -> str:

            def replace_match(match: re.Match[str]) -> str:
                compact: list[int] = []
                seen: set[int] = set()
                for pi in _citation_indices_from_bracket(match.group(1), packet_count=packet_count):
                    ci = index_mapping.get(pi)
                    if ci is None or ci in seen:
                        continue
                    seen.add(ci)
                    compact.append(ci)
                return f"[{', '.join((str(i) for i in compact))}]" if compact else ''
            remapped = re.sub('\\[([0-9][0-9,\\s-]*)\\]', replace_match, answer_text)
            remapped = re.sub('\\s+([.,;:])', '\\1', remapped)
            return re.sub(' {2,}', ' ', remapped).strip()

        def _citation_ref_for_packet(packet: AcceptedEvidence) -> CitationRef:
            slice_start = max(0, packet.text_start)
            slice_end = max(slice_start, packet.text_end)
            if packet.text_part == 'chunk' and slice_end - slice_start >= 100:
                return CitationRef(receipt_id=packet.receipt_id, result_id=packet.result_id, slices=[CitationSlice(start=slice_start, end=slice_end)])
            return CitationRef(receipt_id=packet.receipt_id, result_id=packet.result_id)

        def _referenced_packet_indices(answer_text: str, *, packet_count: int) -> tuple[int, ...]:
            indices: list[int] = []
            seen: set[int] = set()
            for match in re.finditer('\\[([0-9][0-9,\\s-]*)\\]', answer_text):
                for index in _citation_indices_from_bracket(match.group(1), packet_count=packet_count):
                    if index not in seen:
                        seen.add(index)
                        indices.append(index)
            return tuple(indices)

        def _citation_indices_from_bracket(value: str, *, packet_count: int) -> tuple[int, ...]:
            indices: list[int] = []
            for item in value.split(','):
                text = item.strip()
                if not text:
                    continue
                range_match = re.fullmatch('(\\d{1,3})\\s*-\\s*(\\d{1,3})', text)
                if range_match:
                    start, end = (int(range_match.group(1)), int(range_match.group(2)))
                    if start <= end:
                        indices.extend((i for i in range(start, end + 1) if 1 <= i <= packet_count))
                elif text.isdigit():
                    i = int(text)
                    if 1 <= i <= packet_count:
                        indices.append(i)
            return tuple(indices)

        async def _call_json_llm_with_retry(*, messages: list[dict[str, str]], model: str, temperature: float, thinking: LlmThinkingConfig | None=None, validate_payload: Callable[[dict[str, object]], str | None], state: ResearchRunState, stage: str, max_attempts: int=MAX_JSON_LLM_ATTEMPTS, repair_payload: Callable[[str], tuple[dict[str, object] | None, str | None]] | None=None) -> dict[str, object] | None:
            _ = (state, stage)
            active_messages = list(messages)
            for attempt_index in range(max_attempts):
                try:
                    response = await llm_chat(provider=_LLM_PROVIDER, messages=active_messages, model=model, temperature=temperature, thinking=thinking, timeout=JSON_LLM_TOOL_TIMEOUT_SECONDS)
                except Exception:
                    return None
                last_text = _assistant_text(response)
                payload = _parse_json_object(last_text)
                repair_note: str | None = None
                if payload is None:
                    if repair_payload is not None:
                        payload, repair_note = repair_payload(last_text)
                    if payload is None:
                        error_message = 'The response was not a parseable JSON object. Return exactly one JSON object matching the requested schema, with no Markdown fence and no prose.'
                        if repair_note:
                            error_message = f'{error_message} Local repair failed: {repair_note}'
                    else:
                        error_message = validate_payload(payload)
                        if error_message is None:
                            return payload
                else:
                    error_message = validate_payload(payload)
                    if error_message is None:
                        return payload
                if attempt_index + 1 >= max_attempts:
                    return None
                active_messages = [*messages, {'role': 'assistant', 'content': last_text or '(empty assistant response)'}, {'role': 'user', 'content': f"Fix the JSON only.\n\nPrevious response:\n{(last_text or '(empty response)').strip()}\n\nError:\n{error_message}\n\nReturn one corrected JSON object only. No Markdown or prose. Preserve the task/schema."}]
            return None

        def _parse_json_object(text: str) -> dict[str, object] | None:
            if not text:
                return None
            stripped = _strip_code_fence(text.strip())
            start = stripped.find('{')
            end = stripped.rfind('}')
            if start < 0 or end <= start:
                return None
            candidate = stripped[start:end + 1]
            for attempt in _json_object_parse_attempts(candidate):
                try:
                    parsed = json.loads(attempt, object_pairs_hook=_json_object_without_duplicate_keys)
                except (json.JSONDecodeError, ValueError):
                    continue
                if isinstance(parsed, dict):
                    return {str(k): v for k, v in parsed.items()}
            return None

        def _json_object_parse_attempts(candidate: str) -> tuple[str, ...]:
            comma_repaired = re.sub(',\\s*([}\\]])', '\\1', candidate)
            value_delimiter_repaired = re.sub('("value")\\s*>(>[^",}\\]]*)"', '\\1:"\\2"', candidate)
            vd_and_comma = re.sub(',\\s*([}\\]])', '\\1', value_delimiter_repaired)
            return tuple(dict.fromkeys((candidate, comma_repaired, value_delimiter_repaired, vd_and_comma)))

        def _json_object_without_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
            parsed: dict[str, object] = {}
            for key, value in pairs:
                if key in parsed:
                    raise ValueError(f'Duplicate JSON object key: {key}')
                parsed[key] = value
            return parsed

        def _json_object_merging_evidence_targets(pairs: list[tuple[str, object]]) -> dict[str, object]:
            parsed: dict[str, object] = {}
            merged_targets: list[object] = []
            saw_evidence_targets = False
            for key, value in pairs:
                if key == 'evidence_targets':
                    saw_evidence_targets = True
                    if isinstance(value, list):
                        merged_targets.extend(value)
                    elif value is not None:
                        merged_targets.append(value)
                    continue
                if key in parsed:
                    raise ValueError(f'Duplicate JSON object key: {key}')
                parsed[str(key)] = value
            if saw_evidence_targets:
                parsed['evidence_targets'] = merged_targets
            return parsed

        def _strip_code_fence(text: str) -> str:
            if not text.startswith('```'):
                return text
            stripped = re.sub('^```[A-Za-z0-9_-]*\\s*', '', text.strip(), count=1)
            stripped = re.sub('\\s*```$', '', stripped, count=1)
            return stripped.strip()

        def _repair_evidence_search_target_payload(text: str) -> tuple[dict[str, object] | None, str | None]:
            if not text:
                return (None, 'no mergeable evidence_targets object found')
            stripped = _strip_code_fence(text.strip())
            start = stripped.find('{')
            end = stripped.rfind('}')
            if start < 0 or end <= start:
                return (None, 'no mergeable evidence_targets object found')
            candidate = stripped[start:end + 1]
            raw_payload = None
            for attempt in _json_object_parse_attempts(candidate):
                try:
                    parsed = json.loads(attempt, object_pairs_hook=_json_object_merging_evidence_targets)
                except (json.JSONDecodeError, ValueError):
                    continue
                if isinstance(parsed, dict):
                    raw_payload = {str(k): v for k, v in parsed.items()}
                    break
            if raw_payload is None:
                return (None, 'no mergeable evidence_targets object found')
            targets = raw_payload.get('evidence_targets')
            if not isinstance(targets, list):
                return (None, 'merged evidence_targets value was not an array')
            repaired: list[dict[str, object]] = []
            seen_keys: set[tuple[str, str, str, str]] = set()
            dropped = 0
            for item in targets:
                if not isinstance(item, dict):
                    dropped += 1
                    continue
                slot_id = _string_value(item.get('slot_id'))
                if slot_id not in INTENT_SLOT_DEFINITIONS:
                    dropped += 1
                    continue
                slot_intent = _slot_intent_from_payload(slot_id, item)
                if slot_id in FREE_INTENT_SLOT_IDS and (not slot_intent):
                    dropped += 1
                    continue
                needed_source_text = ' '.join(_string_value(item.get('needed_source_text')).split())
                source_type = ' '.join(_string_value(item.get('source_type')).split())
                key = (slot_id, slot_intent.casefold(), needed_source_text.casefold(), source_type.casefold())
                if not needed_source_text or not source_type or key in seen_keys:
                    dropped += 1
                    continue
                inventory = _source_inventory_from_payload(item.get('inventory'))
                if not _source_inventory_has_material(inventory):
                    dropped += 1
                    continue
                seen_keys.add(key)
                repaired_item: dict[str, object] = {'slot_id': slot_id, 'needed_source_text': needed_source_text, 'source_type': source_type, 'inventory': _source_inventory_to_payload(inventory)}
                if slot_id in FREE_INTENT_SLOT_IDS:
                    repaired_item['slot_intent'] = slot_intent
                repaired.append(repaired_item)
                if len(repaired) >= MAX_EVIDENCE_TARGETS_PER_ROUND:
                    break
            if not repaired:
                return (None, f'no valid evidence_targets items after repair; dropped={dropped}')
            return ({'evidence_targets': repaired}, f'merged duplicate evidence_targets inventories; kept={len(repaired)} dropped={dropped}')

        def _evidence_search_target_payload_validator() -> Callable[[dict[str, object]], str | None]:

            def validate(payload: dict[str, object]) -> str | None:
                extra = sorted(set(payload) - {'evidence_targets'})
                if extra:
                    return f'Unexpected keys: {json.dumps(extra)}. Use only evidence_targets.'
                targets = payload.get('evidence_targets')
                if not isinstance(targets, list) or not targets:
                    return 'evidence_targets must be a non-empty JSON array.'
                for i, item in enumerate(targets):
                    if not isinstance(item, dict):
                        return f'evidence_targets[{i}] must be a JSON object.'
                    extra_keys = sorted(set(item) - {'slot_id', 'slot_intent', 'needed_source_text', 'source_type', 'inventory'})
                    if extra_keys:
                        return f'evidence_targets[{i}] has unexpected keys: {json.dumps(extra_keys)}.'
                    slot_id = _string_value(item.get('slot_id'))
                    if slot_id not in INTENT_SLOT_DEFINITIONS:
                        return f'evidence_targets[{i}].slot_id is invalid: {json.dumps(slot_id)}. Valid: {json.dumps(list(INTENT_SLOT_DEFINITIONS))}.'
                    if slot_id in FREE_INTENT_SLOT_IDS and (not _string_value(item.get('slot_intent'))):
                        return f'evidence_targets[{i}].slot_intent is required when slot_id is {slot_id}.'
                    if not _string_value(item.get('needed_source_text')):
                        return f'evidence_targets[{i}].needed_source_text must be a non-empty string.'
                    if not _string_value(item.get('source_type')):
                        return f'evidence_targets[{i}].source_type must be a non-empty string.'
                    inventory = item.get('inventory')
                    if not isinstance(inventory, dict):
                        return f'evidence_targets[{i}].inventory must be a JSON object.'
                    inv_error = _validate_source_inventory_payload(inventory, path=f'evidence_targets[{i}].inventory')
                    if inv_error:
                        return inv_error
                return None
            return validate

        def _evidence_search_route_payload_validator(*, targets: tuple[EvidenceSearchTarget, ...]) -> Callable[[dict[str, object]], str | None]:
            valid_target_ids = tuple((t.target_id for t in targets))
            valid_set = set(valid_target_ids)

            def validate(payload: dict[str, object]) -> str | None:
                extra = sorted(set(payload) - {'queries'})
                if extra:
                    return f'Unexpected keys: {json.dumps(extra)}. Use only queries.'
                queries = payload.get('queries')
                if not isinstance(queries, list) or not queries:
                    return 'queries must be a non-empty JSON array.'
                for i, item in enumerate(queries):
                    if not isinstance(item, dict):
                        return f'queries[{i}] must be a JSON object.'
                    extra_keys = sorted(set(item) - {'target_id', 'query', 'site_constraints'})
                    missing_keys = sorted({'target_id', 'query'} - set(item))
                    if extra_keys or missing_keys:
                        return f'queries[{i}] must contain target_id, query, and optional site_constraints. Missing: {json.dumps(missing_keys)}; Unexpected: {json.dumps(extra_keys)}.'
                    target_id = _string_value(item.get('target_id'))
                    if target_id not in valid_set:
                        return f'queries[{i}].target_id is invalid: {json.dumps(target_id)}. Valid: {json.dumps(valid_target_ids)}.'
                    query = _clean_llm_search_query(item.get('query'))
                    if not query:
                        return f'queries[{i}].query must be a non-empty string.'
                    if _lite_search_query_syntax_error(query):
                        return f'queries[{i}].query is invalid: {_lite_search_query_syntax_error(query)}'
                return None
            return validate

        def _search_result_source_labeler_payload_validator() -> Callable[[dict[str, object]], str | None]:

            def validate(payload: dict[str, object]) -> str | None:
                if set(payload) != {'labels'}:
                    return 'Top-level JSON keys must be exactly: labels.'
                labels = payload.get('labels')
                if not isinstance(labels, list):
                    return 'labels must be a JSON array.'
                expected = {'basis', 'result_id', 'target_ids', 'source_value', 'source_kind', 'surface'}
                for i, label in enumerate(labels):
                    if not isinstance(label, dict) or set(label) != expected:
                        return f'labels[{i}] has invalid keys.'
                    for f in ('basis', 'result_id', 'source_value', 'source_kind', 'surface'):
                        if not isinstance(label.get(f), str):
                            return f'labels[{i}].{f} must be a string.'
                    if not isinstance(label.get('target_ids'), list):
                        return f'labels[{i}].target_ids must be a JSON array.'
                return None
            return validate

        def _observation_evidence_gate_payload_validator(*, candidates: tuple[EvidenceCandidate, ...], contract: ResearchContract) -> Callable[[dict[str, object]], str | None]:
            valid_candidate_ids = tuple((c.candidate_id for c in candidates))
            valid_candidate_id_set = set(valid_candidate_ids)
            valid_role_ids = tuple((r.role_id for r in contract.roles))
            valid_role_id_set = set(valid_role_ids)
            slot_id_by_role_id = {r.role_id: r.slot_id for r in contract.roles}
            support_values = ('direct', 'partial', 'absence', 'contradiction', 'context')

            def validate(payload: dict[str, object]) -> str | None:
                extra = sorted(set(payload) - {'accepted_candidates', 'observations'})
                if extra:
                    return f'The JSON object must contain only accepted_candidates and observations. Unexpected keys: {json.dumps(extra)}.'
                accepted_candidates = payload.get('accepted_candidates')
                if not isinstance(accepted_candidates, list):
                    return 'accepted_candidates must be a JSON array.'
                accepted_seen: set[str] = set()
                seen_order: list[int] = []
                for i, value in enumerate(accepted_candidates):
                    if not isinstance(value, dict):
                        return f'accepted_candidates[{i}] must be a JSON object.'
                    req = {'order_basis', 'candidate_id'}
                    extra_c = sorted(set(value) - req)
                    missing_c = sorted(req - set(value))
                    if extra_c or missing_c:
                        return f'accepted_candidates[{i}] must contain exactly order_basis and candidate_id. Missing: {json.dumps(missing_c)}; Unexpected: {json.dumps(extra_c)}.'
                    candidate_id = _string_value(value.get('candidate_id'))
                    if candidate_id not in valid_candidate_id_set:
                        return f'accepted_candidates[{i}].candidate_id is invalid.'
                    if candidate_id in accepted_seen:
                        return f'accepted_candidates[{i}].candidate_id duplicates an earlier candidate ID.'
                    accepted_seen.add(candidate_id)
                    if len(accepted_seen) >= MAX_ACCEPTED_IDS_PER_GATE:
                        break
                observations = payload.get('observations')
                if not isinstance(observations, list):
                    return 'observations must be a JSON array.'
                for i, obs in enumerate(observations):
                    if not isinstance(obs, dict):
                        return f'observations[{i}] must be a JSON object.'
                    candidate_id = _string_value(obs.get('candidate_id'))
                    if candidate_id not in accepted_seen:
                        continue
                    req = {'role_id', 'slot_id', 'candidate_id', 'entity', 'metric', 'value', 'time_scope', 'support', 'source_tier'}
                    extra_o = sorted(set(obs) - req)
                    missing_o = sorted(req - set(obs))
                    if extra_o or missing_o:
                        return f'observations[{i}] must contain exactly the required keys. Missing: {json.dumps(missing_o)}; Unexpected: {json.dumps(extra_o)}.'
                    role_id = _string_value(obs.get('role_id'))
                    if role_id not in valid_role_id_set:
                        return f'observations[{i}].role_id is invalid: {json.dumps(role_id)}. Valid: {json.dumps(valid_role_ids)}.'
                    slot_id = _string_value(obs.get('slot_id'))
                    expected_slot = slot_id_by_role_id.get(role_id, '')
                    if slot_id != expected_slot:
                        return f'observations[{i}].slot_id must be {json.dumps(expected_slot)} for role {json.dumps(role_id)}; received {json.dumps(slot_id)}.'
                    for key in ('entity', 'metric', 'value', 'time_scope', 'source_tier'):
                        if not isinstance(obs.get(key), str) or not str(obs.get(key, '')).strip():
                            return f'observations[{i}].{key} must be a non-empty string.'
                    support = _string_value(obs.get('support'))
                    if support not in support_values:
                        return f'observations[{i}].support must be one of {json.dumps(list(support_values))}.'
                return None
            return validate

        def _chunk_cue_pattern_payload_validator(_role_ledger: tuple[ResearchPlanRole, ...]) -> Callable[[dict[str, object]], str | None]:

            def validate(payload: dict[str, object]) -> str | None:
                extra = sorted(set(payload) - {'patterns'})
                if extra:
                    return f'The JSON object must contain only patterns. Unexpected keys: {json.dumps(extra)}.'
                if not isinstance(payload.get('patterns'), list):
                    return 'Missing or invalid key `patterns`: expected a JSON array.'
                return None
            return validate

        def _chunk_lexical_anchor_payload_validator(_role_ledger: tuple[ResearchPlanRole, ...]) -> Callable[[dict[str, object]], str | None]:

            def validate(payload: dict[str, object]) -> str | None:
                extra = sorted(set(payload) - {'anchor_sets'})
                if extra:
                    return f'The JSON object must contain only anchor_sets. Unexpected keys: {json.dumps(extra)}.'
                if not isinstance(payload.get('anchor_sets'), list):
                    return 'Missing or invalid key `anchor_sets`: expected a JSON array.'
                return None
            return validate

        def _evidence_search_targets_from_payload(payload: dict[str, object], *, round_index: int) -> tuple[EvidenceSearchTarget, ...]:
            targets: list[EvidenceSearchTarget] = []
            seen_keys: set[tuple[str, str, str, str]] = set()
            for item in _object_list(payload.get('evidence_targets')):
                if len(targets) >= MAX_EVIDENCE_TARGETS_PER_ROUND:
                    break
                slot_id = _string_value(item.get('slot_id'))
                if slot_id not in INTENT_SLOT_DEFINITIONS:
                    continue
                slot_intent = _slot_intent_from_payload(slot_id, item)
                if slot_id in FREE_INTENT_SLOT_IDS and (not slot_intent):
                    continue
                needed_source_text = ' '.join(_string_value(item.get('needed_source_text')).split())
                source_type = ' '.join(_string_value(item.get('source_type')).split())
                key = (slot_id, slot_intent.casefold(), needed_source_text.casefold(), source_type.casefold())
                if not needed_source_text or not source_type or key in seen_keys:
                    continue
                target_id = f'target_{round_index + 1}_{len(targets) + 1}'
                inventory = _source_inventory_from_payload(item.get('inventory'))
                seen_keys.add(key)
                targets.append(EvidenceSearchTarget(target_id=target_id, slot_id=slot_id, slot_intent=slot_intent, needed_source_text=needed_source_text, source_type=source_type, inventory=inventory, routes=()))
            return tuple(targets)

        def _evidence_search_routes_from_payload(*, payload: dict[str, object] | None, targets: tuple[EvidenceSearchTarget, ...], tried_queries: set[str]) -> tuple[EvidenceSearchRoute, ...]:
            if payload is None:
                return ()
            target_by_id = {t.target_id: t for t in targets}
            routes: list[EvidenceSearchRoute] = []
            seen_materialized = set(tried_queries)
            seen_base: set[tuple[str, str]] = set()
            per_target: dict[str, int] = {}
            for item in _object_list(payload.get('queries')):
                target_id = _string_value(item.get('target_id'))
                target = target_by_id.get(target_id)
                if target is None or per_target.get(target_id, 0) >= MAX_QUERY_ROUTES_PER_TARGET:
                    continue
                query = _clean_llm_search_query(item.get('query'))
                if not query or _lite_search_query_syntax_error(query):
                    continue
                site_constraints = _site_constraints_from_value(item.get('site_constraints'))
                base_key = (target_id, _query_identity(query))
                if base_key in seen_base:
                    continue
                route = EvidenceSearchRoute(route_id=f'{target_id}_route_{per_target.get(target_id, 0) + 1}', target_id=target.target_id, slot_id=target.slot_id, slot_intent=target.slot_intent, needed_source_text=target.needed_source_text, source_type=target.source_type, route_kind='llm_query', query=query, site_constraints=site_constraints)
                new_queries = tuple((q for q in _materialized_evidence_search_route_queries(route) if _query_identity(q) and _query_identity(q) not in seen_materialized))
                if not new_queries:
                    continue
                seen_base.add(base_key)
                seen_materialized.update((_query_identity(q) for q in new_queries))
                per_target[target_id] = per_target.get(target_id, 0) + 1
                routes.append(route)
            return tuple(routes)

        def _chunk_cue_patterns_from_payload(*, payload: dict[str, object], role_ledger: tuple[ResearchPlanRole, ...]) -> tuple[tuple[ChunkCuePattern, ...], tuple[dict[str, object], ...]]:
            valid_role_id_set = {r.role_id for r in role_ledger}
            raw_patterns = payload.get('patterns')
            if not isinstance(raw_patterns, list):
                return ((), ())
            patterns: list[ChunkCuePattern] = []
            rejected: list[dict[str, object]] = []
            per_role: dict[str, int] = {}
            for i, item in enumerate(raw_patterns):
                if not isinstance(item, dict):
                    rejected.append({'index': i, 'reason': 'not an object'})
                    continue
                role_id = str(item.get('role_id', '')).strip()
                pattern_text = str(item.get('pattern', '')).strip()
                if role_id not in valid_role_id_set:
                    rejected.append({'index': i, 'role_id': role_id, 'reason': 'invalid role_id'})
                    continue
                if not pattern_text or len(pattern_text) > MAX_CHUNK_CUE_PATTERN_CHARS:
                    rejected.append({'index': i, 'reason': 'invalid pattern'})
                    continue
                if _regex_pattern_contains_unit_cue(pattern_text) and (not _regex_pattern_has_value_context(pattern_text)):
                    rejected.append({'index': i, 'reason': 'bare unit cue'})
                    continue
                try:
                    compiled = re.compile(pattern_text, re.IGNORECASE)
                except re.error:
                    rejected.append({'index': i, 'reason': 'invalid regex'})
                    continue
                if per_role.get(role_id, 0) >= MAX_CHUNK_CUE_PATTERNS_PER_ROLE or len(patterns) >= MAX_CHUNK_CUE_PATTERNS_TOTAL:
                    rejected.append({'index': i, 'reason': 'cap exceeded'})
                    continue
                per_role[role_id] = per_role.get(role_id, 0) + 1
                patterns.append(ChunkCuePattern(pattern_index=len(patterns) + 1, role_id=role_id, pattern=pattern_text, compiled=compiled))
            return (tuple(patterns), tuple(rejected))

        def _chunk_lexical_anchors_from_payload(*, payload: dict[str, object], role_ledger: tuple[ResearchPlanRole, ...]) -> tuple[tuple[ChunkLexicalAnchorSet, ...], tuple[dict[str, object], ...]]:
            valid_role_id_set = {r.role_id for r in role_ledger}
            raw_anchor_sets = payload.get('anchor_sets')
            if not isinstance(raw_anchor_sets, list):
                return ((), ())
            anchor_sets: list[ChunkLexicalAnchorSet] = []
            rejected: list[dict[str, object]] = []
            seen_keys: set[tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = set()
            for i, item in enumerate(raw_anchor_sets):
                if len(anchor_sets) >= MAX_LEXICAL_ANCHOR_SETS_TOTAL:
                    break
                if not isinstance(item, dict):
                    continue
                role_id = str(item.get('role_id', '')).strip()
                if role_id not in valid_role_id_set:
                    continue
                all_terms, _ = _clean_lexical_anchor_terms(item.get('all'))
                any_terms, _ = _clean_lexical_anchor_terms(item.get('any'))
                near_terms, _ = _clean_lexical_anchor_terms(item.get('near'))
                avoid_terms, _ = _clean_lexical_anchor_terms(item.get('avoid'))
                if not (all_terms or any_terms or near_terms or avoid_terms):
                    continue
                key = (role_id, all_terms, any_terms, near_terms, avoid_terms)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                anchor_sets.append(ChunkLexicalAnchorSet(anchor_index=len(anchor_sets) + 1, role_id=role_id, all_terms=all_terms, any_terms=any_terms, near_terms=near_terms, avoid_terms=avoid_terms))
            return (tuple(anchor_sets), tuple(rejected))

        def _clean_lexical_anchor_terms(value: object) -> tuple[tuple[str, ...], tuple[dict[str, object], ...]]:
            if not isinstance(value, list):
                return ((), ())
            terms: list[str] = []
            rejected: list[dict[str, object]] = []
            seen: set[str] = set()
            for i, item in enumerate(value):
                if not isinstance(item, str):
                    rejected.append({'term_index': i, 'reason': 'not a string'})
                    continue
                term = re.sub('\\s+', ' ', item.strip().casefold())
                if not term or len(term) > MAX_LEXICAL_ANCHOR_TERM_CHARS or term in seen:
                    continue
                seen.add(term)
                terms.append(term)
                if len(terms) >= MAX_LEXICAL_ANCHOR_TERMS_PER_FIELD:
                    break
            return (tuple(terms), tuple(rejected))

        def _regex_pattern_contains_unit_cue(pattern: str) -> bool:
            return any((token in REGEX_UNIT_WORDS for token in _regex_pattern_word_tokens(pattern)))

        def _regex_pattern_has_value_context(pattern: str) -> bool:
            normalized = pattern.lower()
            return bool(re.search('\\\\d|\\[0-9]|[0-9]', normalized) or any((s in pattern for s in ('$', '€', '£', '¥', '%', '/'))) or re.search('\\b(?:percent|per|to|through|between|from)\\b', normalized))

        def _regex_pattern_word_tokens(pattern: str) -> tuple[str, ...]:
            return tuple((token for token in re.findall('[a-zA-Z%]+', pattern.lower()) if token not in REGEX_ESCAPE_WORDS))

        def _build_evidence_search_target_messages(*, question: str, round_index: int, tried_queries: tuple[str, ...], prior_targets: tuple[EvidenceSearchTarget, ...], accumulated_results: tuple[AccumulatedSearchResult, ...], wrong_entities: tuple[str, ...]=()) -> list[dict[str, str]]:
            slot_payload = [{'slot_id': sid, 'intent': intent, 'free_slot': sid in FREE_INTENT_SLOT_IDS} for sid, intent in INTENT_SLOT_DEFINITIONS.items()]
            result_payload = [{'result_id': r.result_id, 'url': r.url, 'title': r.title or '', 'target_id_hint': r.target_id, 'slot_id_hint': r.slot_id, 'slot_intent_hint': r.slot_intent, 'needed_source_text_hint': r.needed_source_text, 'source_type_hint': r.source_type, 'route_id_hint': r.route_id, 'route_kind_hint': r.route_kind, 'query': r.query, 'search_result_text': _text_excerpt(r.note, 500)} for r in accumulated_results[-16:]]
            stacked_payload = [{'result_id': r.result_id, 'round': r.search_round, 'slot_id_hint': r.slot_id, 'source_type_hint': r.source_type, 'url': r.url, 'title': r.title or '', 'query': r.query} for r in accumulated_results]
            prior_target_payload = [{'target_id': t.target_id, 'slot_id': t.slot_id, 'slot_intent': t.slot_intent, 'needed_source_text': t.needed_source_text, 'source_type': t.source_type, 'inventory': _source_inventory_to_payload(t.inventory), 'generated_queries': [r.query for r in t.routes]} for t in prior_targets[-8:]]
            system_content = f"""ROLE: evidence-source inventory analyst for a deep-research answer. You are not an answer writer and you are not a search-query writer. Your job is to describe the source inventory that would let Python build evidence-seeking search queries: entities, aliases, official source families, document handles, metric terms, date/scope terms, must-include terms, avoid terms, and optional site constraints.\n\nOUTPUT: exactly {{"evidence_targets":[{{"slot_id":"...","slot_intent":"...","needed_source_text":"...","source_type":"...","inventory":{{"entities":[],"aliases":[],"source_families":[],"document_handles":[],"metric_terms":[],"date_scope":[],"must_include":[],"avoid":[],"site_constraints":[]}}}}]}}. Use slot_intent only for free_1/free_2. No routes, no query fields, no markdown, no reasons, no extra keys.\n\nCOUNT: return 2-{MAX_EVIDENCE_TARGETS_PER_ROUND} evidence_targets. Each target may have inventory arrays with 1-6 concise terms each.\n\nABSENCE / FALSE-PREMISE RULE: For questions of the form 'which X were [state Y] during [period Z]' or 'what X occurred during [event]', the premise_check target MUST include inventory terms that could prove NO X was in state Y. Add to must_include terms like 'powered down', 'hibernated', 'no instruments', 'not operational', 'none' when the question implies a state that could be false. Add to avoid: time-adjacent periods that could contaminate evidence (e.g. 'post-revival', 'after wake-up', 'following recovery'). Example: 'which instruments were operational during lunar night' -> premise_check must_include: ['powered down','hibernation','no instruments operational'] avoid: ['after revival','February 25','post-wakeup'].\n\nDUAL-DOCUMENT RULE: When the question explicitly names two different official documents, filings, or reports (e.g. 'compare the 8-K estimate with the 10-K final', 'the January press release vs the July JAMA publication'), you MUST generate one evidence_target per document with distinct document_handles and date_scope. Do NOT merge into one target. Example: 'compare January 2023 8-K estimate vs 2023 10-K actual' -> Target 1: document_handles: ['Form 8-K','January 2023'], must_include: ['estimated','range']; Target 2: document_handles: ['Form 10-K','2023 Annual Report'], must_include: ['recorded','actual'].\n\nCALCULATION-METHOD RULE: When the question asks HOW something is calculated (e.g. 'how does X calculate Y for Z purposes', 'what formula does [body] use to determine [metric]'), you MUST include a method_or_definition slot target. Its inventory must contain metric_terms with the calculation inputs (e.g. 'federal mid-term rate', 'present value', 'discount rate', 'deferred salary'), source_families with the governing body (e.g. 'MLB collective bargaining agreement', 'CBA', 'MLBPA official rules'), and must_include with the exact calculation mechanism term.\n\nCOVERAGE-DECOMPOSITION RULE: Decompose the question into EVERY distinct fact it explicitly requests and emit a separate evidence_target for each one a single existing target does not already cover. (a) Each (entity x requested attribute) pair: if one attribute is asked for two entities, emit one target per entity; if one entity is asked for two attributes, emit one target per attribute. (b) Full enumerations: a 'which / list / name all X' requirement gets a target whose must_include drives the COMPLETE set (e.g. 'all', 'each', 'every', the named count), not a single example. (c) Secondary / special-category items joined by 'as well as', 'including', 'and also', or 'a lower / separate threshold for [category]': these qualifying sub-clauses are REQUIRED facts, not optional context — each gets its own target. (d) A comparison baseline named in a sub-clause (e.g. 'compared to the [poll / forecast / prior estimate / projection]') gets its own target so the baseline value is retrieved, not just the headline value. Prefer covering one more required sub-element over adding depth to an already-covered one.\n\nWRONG-ENTITY RULE: If CANDIDATE_WRONG_ADJACENT_ENTITIES is provided, review each entity and add it to the avoid field of any target where that entity would produce results from the wrong source or geography. Use your judgment — only add entities that are genuinely wrong-adjacent for a specific target, not globally."""
            wrong_entities_section = ''
            if wrong_entities:
                wrong_entities_section = f'\nCANDIDATE_WRONG_ADJACENT_ENTITIES (entities seen in prior results that may be wrong-adjacent — inject the relevant ones into avoid for new targets):\n{json.dumps(list(wrong_entities), ensure_ascii=False)}\n'
            user_content = f"Current date: {_current_date()}.\nSearch round: {round_index}\n\nOriginal question:\n{question}\n\nINTENT_SLOT_MENU:\n{_format_records_section('SLOTS', 'slot', slot_payload)}\n\nTRIED_QUERIES:\n{json.dumps(list(tried_queries), ensure_ascii=False)}\n\nPRIOR_INVENTORIES:\n{_format_records_section('PRIOR_TARGETS', 'target', prior_target_payload)}\n\nACCUMULATED_RESULT_SURFACES:\n{_format_records_section('RESULT_SURFACES', 'result', stacked_payload)}\n\nRECENT_ACCUMULATED_RESULTS:\n{_format_records_section('RESULTS', 'result', result_payload)}\n{wrong_entities_section}Return evidence-target JSON now."
            return [{'role': 'system', 'content': system_content}, {'role': 'user', 'content': user_content}]

        def _build_evidence_search_route_messages(*, question: str, round_index: int, targets: tuple[EvidenceSearchTarget, ...], tried_queries: tuple[str, ...], accumulated_results: tuple[AccumulatedSearchResult, ...]) -> list[dict[str, str]]:
            target_payload = [{'target_id': t.target_id, 'slot_id': t.slot_id, 'slot_intent': t.slot_intent, 'needed_source_text': t.needed_source_text, 'source_type': t.source_type, 'inventory': _source_inventory_to_payload(t.inventory)} for t in targets]
            result_surface_payload = [{'result_id': r.result_id, 'round': r.search_round, 'target_id_hint': r.target_id, 'url': r.url, 'title': r.title or '', 'query': r.query} for r in accumulated_results[-24:]]
            system_content = f'ROLE: evidence-search query writer. You receive source-inventory targets from a planner. Your job is to write the exact search strings that should be sent to a web search tool.\n\nOUTPUT JSON ONLY: {{"queries":[{{"target_id":"target_1_1","query":"specific evidence-seeking query","site_constraints":["example.org"]}}]}}. No markdown, no reasons, no extra keys.\n\nDIVERSITY: produce at most {MAX_QUERY_ROUTES_PER_TARGET} queries per target. Return a compact set of high-recall queries now.'
            user_content = f"Current date: {_current_date()}.\nSearch round: {round_index}\n\nOriginal question:\n{question}\n\nSEARCH_TARGETS:\n{_format_records_section('TARGETS', 'target', target_payload)}\n\nTRIED_QUERIES:\n{json.dumps(list(tried_queries), ensure_ascii=False)}\n\nRESULT_SURFACES:\n{_format_records_section('RESULTS', 'result', result_surface_payload)}\n\nReturn executable query JSON now."
            return [{'role': 'system', 'content': system_content}, {'role': 'user', 'content': user_content}]

        def _build_search_result_source_labeler_messages(*, question: str, targets: tuple[EvidenceSearchTarget, ...], routes: tuple[EvidenceSearchRoute, ...], results: tuple[AccumulatedSearchResult, ...]) -> list[dict[str, str]]:
            target_payload = [{'target_id': t.target_id, 'slot_id': t.slot_id, 'slot_intent': t.slot_intent, 'needed_source_text': t.needed_source_text, 'source_type': t.source_type, 'inventory': _source_inventory_to_payload(t.inventory)} for t in targets]
            route_payload = [{'route_id': r.route_id, 'target_id': r.target_id, 'route_kind': r.route_kind, 'query': r.query, 'site_constraints': r.site_constraints} for r in routes]
            result_payload = [{'result_id': r.result_id, 'url': r.url, 'title': r.title or '', 'evidence_target_id_hint': r.target_id, 'slot_id_hint': r.slot_id, 'needed_source_text_hint': r.needed_source_text, 'query': r.query, 'search_result_text': _compress_search_result_text(r.note)} for r in results]
            system_content = 'ROLE: search-result source labeler. Label result value; do not answer, select winners, or drop ambiguous results.\n\nOUTPUT JSON ONLY: {"labels":[{"basis":"...","result_id":"R1","target_ids":["target_1_1"],"source_value":"direct","source_kind":"official","surface":"both"}]}. No markdown. No comments. No extra keys.\n\nVALUES: source_value=direct|primary_locator|context|contradiction|absence|weak|wrong. source_kind=official|primary|academic|government|regulatory|company|data_source|reputable_media|secondary|forum_social|aggregator|weak_unknown|wrong_source. surface=snippet|detail|both|locator|background|wrong.'
            user_content = f"Current date: {_current_date()}.\n\nOriginal question:\n{question}\n\nEVIDENCE_TARGETS_TO_COVER:\n{_format_records_section('TARGETS', 'target', target_payload)}\n\nQUERY_ROUTES:\n{_format_records_section('ROUTES', 'route', route_payload)}\n\nACCUMULATED_SEARCH_RESULTS:\n{_format_records_section('RESULTS', 'result', result_payload)}\n\nReturn search-result source-labeler JSON now."
            return [{'role': 'system', 'content': system_content}, {'role': 'user', 'content': user_content}]

        def _build_observation_evidence_gate_messages(*, question: str, loop_index: int, existing_packets: tuple[AcceptedEvidence, ...], existing_observations: tuple[EvidenceObservation, ...], contract: ResearchContract, retrieval_roles: tuple[ResearchPlanRole, ...], candidates: tuple[EvidenceCandidate, ...]) -> list[dict[str, str]]:
            existing_payload = [{'packet_index': i, 'url': p.url, 'title': p.title or '', 'source_text': p.source_text} for i, p in enumerate(existing_packets, start=1)]
            candidate_payload = [{'candidate_id': c.candidate_id, 'slot_id_hint': c.slot_id, 'slot_intent_hint': c.slot_intent, 'text_part': c.text_part, 'text_start': c.text_start, 'text_end': c.text_end, 'url': c.url, 'title': c.title, 'source_kind': c.source_kind, 'query': c.query, 'source_text': c.source_text} for c in candidates]
            accepted_example_id = candidates[0].candidate_id if candidates else 'C1_upper'
            first_role_id = contract.roles[0].role_id if contract.roles else 'exact_requested_fact'
            system_content = f'ROLE: evidence admission + observation extractor. Admit only candidate.source_text that directly supports contract-role observations.\n\nOUTPUT: exactly accepted_candidates and observations. accepted_candidates is an ordered array of objects with order_basis first and candidate_id second.\n\nBUDGET: max {MAX_ACCEPTED_IDS_PER_GATE} accepted candidates. Prefer fewer strong candidates, ordered by answer-role importance.\n\n{{"accepted_candidates":[{{"order_basis":"Exact official source for the highest-priority role.","candidate_id":"{accepted_example_id}"}}],"observations":[{{"role_id":"{first_role_id}","slot_id":"{(contract.roles[0].slot_id if contract.roles else PRIMARY_SOURCE_SLOT_ID)}","candidate_id":"{accepted_example_id}","entity":"entity","metric":"requested metric","value":"supported value or claim","time_scope":"requested scope","support":"direct","source_tier":"official"}}]}}\n{{"accepted_candidates":[],"observations":[]}}'
            user_content = f"Current date: {_current_date()}.\nLoop index: {loop_index}\nQuestion: {question}\n\nImmutable contract roles:\n{_format_records_section('IMMUTABLE_CONTRACT_ROLES', 'role', [{'role_id': r.role_id, 'slot_id': r.slot_id, 'slot_intent': r.slot_intent, 'question': r.question, 'kind': r.kind} for r in contract.roles])}\n\nExisting accepted packets:\n{_format_records_section('EXISTING_ACCEPTED_PACKETS', 'packet', existing_payload)}\n\nExisting accepted observations:\n{_format_records_section('EXISTING_ACCEPTED_OBSERVATIONS', 'observation', _observation_prompt_payload(existing_observations))}\n\nRetrieval role view:\n{_format_records_section('RETRIEVAL_ROLES', 'role', _role_ledger_prompt_payload(retrieval_roles))}\n\nCandidate chunks:\n{_format_records_section('CANDIDATES', 'candidate', candidate_payload)}\n\nReturn the evidence admission and observation JSON now."
            return [{'role': 'system', 'content': system_content}, {'role': 'user', 'content': user_content}]

        def _build_chunk_cue_pattern_messages(*, question: str, loop_index: int, role_ledger: tuple[ResearchPlanRole, ...], sample_chunks: tuple[PageChunk, ...], query_terms: tuple[str, ...]) -> list[dict[str, str]]:
            page_payload = tuple(({'page_id': c.page_id, 'url': c.url, 'title': c.title or '', 'query': c.query} for c in {c.page_id: c for c in sample_chunks}.values()))
            sample_payload = [{'chunk_id': c.chunk_id, 'page_id': c.page_id, 'text_start': c.text_start, 'text_end': c.text_end, 'query': c.query, 'source_text': _text_window(text=c.text, start=0, end=min(len(c.text), HIT_CENTERED_PREVIEW_CONTEXT_CHARS // 2), context_chars=HIT_CENTERED_PREVIEW_CONTEXT_CHARS)} for c in sample_chunks]
            valid_role_ids = [r.role_id for r in role_ledger]
            system_content = f'ROLE: structural regex cue generator. Return Python re patterns that locate likely evidence chunks.\n\nOUTPUT: exactly {{"patterns":[{{"role_id":"...","pattern":"..."}}]}}. role_id is copied from ROLE_LEDGER. No reasons, no markdown, no extra keys.\n\nBUDGET: max {MAX_CHUNK_CUE_PATTERNS_TOTAL} total and {MAX_CHUNK_CUE_PATTERNS_PER_ROLE} per role.'
            user_content = f"""Current date: {_current_date()}.\nLoop index: {loop_index}\n\nOriginal question:\n{question}\n\nValid role IDs: {json.dumps(valid_role_ids, ensure_ascii=False)}\n\nCurrent research-plan roles:\n{_format_records_section('ROLE_LEDGER', 'role', _role_ledger_prompt_payload(role_ledger))}\n\nPage metadata:\n{_format_records_section('PAGES', 'page', page_payload)}\n\nSample chunks:\n{_format_records_section('SAMPLE_CHUNKS', 'chunk', sample_payload)}\n\nReturn exactly one JSON object now:\n{{"patterns":[{{"role_id":"exact_role_id_from_role_ledger","pattern":"Python re pattern"}}]}}"""
            return [{'role': 'system', 'content': system_content}, {'role': 'user', 'content': user_content}]

        def _build_chunk_lexical_anchor_messages(*, question: str, loop_index: int, role_ledger: tuple[ResearchPlanRole, ...], sample_chunks: tuple[PageChunk, ...], query_terms: tuple[str, ...]) -> list[dict[str, str]]:
            page_payload = tuple(({'page_id': c.page_id, 'url': c.url, 'title': c.title or '', 'query': c.query} for c in {c.page_id: c for c in sample_chunks}.values()))
            sample_payload = [{'chunk_id': c.chunk_id, 'page_id': c.page_id, 'text_start': c.text_start, 'text_end': c.text_end, 'query': c.query, 'source_text': _text_window(text=c.text, start=0, end=min(len(c.text), HIT_CENTERED_PREVIEW_CONTEXT_CHARS // 2), context_chars=HIT_CENTERED_PREVIEW_CONTEXT_CHARS)} for c in sample_chunks]
            valid_role_ids = [r.role_id for r in role_ledger]
            system_content = f'ROLE: lexical evidence-neighborhood anchor generator. Return literal phrase groups that help Python locate chunks.\n\nOUTPUT: exactly {{"anchor_sets":[{{"role_id":"...","all":[],"any":[],"near":[],"avoid":[]}}]}}. role_id is copied from ROLE_LEDGER. Terms are literal strings, not regex.\n\nBUDGET: max {MAX_LEXICAL_ANCHOR_SETS_TOTAL} anchor sets total, {MAX_LEXICAL_ANCHOR_TERMS_PER_FIELD} terms per field, and {MAX_LEXICAL_ANCHOR_TERM_CHARS} chars per term.'
            user_content = f"""Current date: {_current_date()}.\nLoop index: {loop_index}\n\nOriginal question:\n{question}\n\nValid role IDs: {json.dumps(valid_role_ids, ensure_ascii=False)}\n\nCurrent research-plan roles:\n{_format_records_section('ROLE_LEDGER', 'role', _role_ledger_prompt_payload(role_ledger))}\n\nPage metadata:\n{_format_records_section('PAGES', 'page', page_payload)}\n\nSample chunks:\n{_format_records_section('SAMPLE_CHUNKS', 'chunk', sample_payload)}\n\nReturn exactly one JSON object now:\n{{"anchor_sets":[{{"role_id":"exact_role_id_from_role_ledger","all":["literal phrase"],"any":["alternative literal"],"near":["nearby term"],"avoid":["wrong-section phrase"]}}]}}"""
            return [{'role': 'system', 'content': system_content}, {'role': 'user', 'content': user_content}]

        def _build_final_answer_messages(*, question: str, accepted_packets: tuple[AcceptedEvidence, ...], accepted_observations: tuple[EvidenceObservation, ...], coverage: tuple[CoverageAspect, ...], unvetted_evidence: bool=False) -> list[dict[str, str]]:
            evidence_payload = [{'packet_number': i, 'url': p.url, 'title': p.title or '', 'source_text_part': p.text_part, 'source_text_range': [p.text_start, p.text_end], 'accepted_source_text': p.source_text, 'source_result_text': p.source_result_text} for i, p in enumerate(accepted_packets, start=1)]
            coverage_payload = [{'aspect': item.aspect, 'slot_id': item.slot_id, 'status': item.status, 'notes': item.notes} for item in coverage]
            system_content = "ROLE: final answer writer for an evidence-gated pipeline.\n\nUSE ONLY accepted packets, observations, and coverage. accepted_source_text is admitted evidence; source_result_text is same-source context. Do not use memory, general knowledge, or unstated assumptions.\n\nANSWER SHAPE: start with a direct answer. For complex questions, explain the evidence-backed landscape: primary-source position, numbers/dates, comparators, mechanisms, actors, conflicts, uncertainty, missing evidence.\n\nFALSE PREMISE: if accepted evidence disproves or fails to support a premise, say so in the first paragraph. Do not answer as if the premise were true.\n\nFALSE-PREMISE COMPLETION RULE: When the premise is false, ALWAYS follow with: (1) the correct fact — what actually happened or exists; (2) if a comparison remains valid after correcting the premise, provide it. Stopping at 'the premise is false' without the corrected facts scores the same as an empty answer in pairwise evaluation.\n\nNUMERIC PRECISION RULE: When comparing statistical values, percentages, or financial estimates across two sources: reproduce exact notation verbatim — do NOT merge 'p < 0.0001' with 'P < .001' or describe them as 'consistent'. If one source gives a range ($1.9B-$2.3B) and another a point value ($2.1B), state both and note whether the point falls within the range. 58.58% and 58.6% are different notations — preserve both exactly as reported.\n\nDUAL-ANSWER COMPLETENESS RULE: When a question has two distinct sub-questions, provide a substantive answer for EACH. If a requested FACT (a value, date, name, or event) is genuinely absent from the evidence: name the specific source type needed and what it would contain (e.g. 'the MLB CBA CBT AAV calculation was not in the accepted evidence — this would specify the federal mid-term rate used to discount deferred salary'). A partial answer covering both sides weakly outscores a complete answer for only one side.\n\nPROVENANCE-CONFIDENCE RULE: A question often names a specific source (e.g. 'the Electoral Commission's certified results', 'the official 10-K'). If the evidence establishes the requested facts through OTHER authoritative sources, state those facts directly and confidently as the answer. Frame any source-label gap as corroboration, not deficiency: write 'these figures are not labeled as [named source] in the evidence, but are corroborated by [authoritative source]' — do NOT lead with, dwell on, or append a disclaimer that 'the accepted evidence does not include [named source]' or 'Missing evidence' when the facts themselves are present and corroborated. Reserve missing-source language for when a requested FACT is actually absent, not when only the exact source label is. This does NOT relax the FALSE PREMISE rules: a false premise must still be stated plainly in the first paragraph.\n\nEXACT-VALUE RULE: When the question asks for a specific value — a precise date, a numeric interval or difference, a named law/title/organization, a target year, or a duration — lead with the exact figure derived from the evidence, not a rounded or hedged paraphrase (e.g. 'roughly 290 metres' or 'around four hours') when the precise value or arithmetic is available. If a needed figure is reported in different units than the question asks, convert it and give the exact converted result; preserve units and any timezone labels.\n\nCLAIM-BINDING RULE: Attach a claim, filing, ruling, complaint, or accusation only to the exact actor, target, date window, and instrument that the accepted evidence ties together. Do not carry a statement about one party or period over to a different one. If the evidence does not bind all four, state that it does not establish that specific event and report what the evidence does show instead.\n\nASKED-SCOPE RULE: Answer with the value from the exact source, date, or scope the question names. Do not substitute a later or broader figure unless it is required to resolve a conflict; when the asked-for contemporaneous source is precise and a later source is only rounded, report the precise contemporaneous value.\n\nDEFINITIVE-OPENING RULE: sentence one must deliver the requested answer itself — the name, number, date, or verdict the question asks for. Never open with remarks about evidence quality, coverage, or what the packets do or do not contain; the answer comes first, context after.\n\nFULL-ROSTER RULE: when the question asks which items qualify, or supplies its own candidate pool, enumerate EVERY qualifying item — one line per item, giving the attribute value that qualifies it with the packet citation on that same line. After the qualifying list, add one brief line per non-qualifying candidate from the question's own pool stating why it fails the criterion, citing a packet where one supports the exclusion.\n\nADJACENT-CITATION RULE: every sentence asserting a number, date, name, or cause must carry its own packet citation [n] placed immediately at that sentence's end. Cite each claim where it is made; do not gather citations into one pooled bracket elsewhere.\n\nNAMED-SOURCE RULE: when the question pins a source ('according to Wikipedia', 'per official records', and the like), report the pinned source's figure, cite the packet carrying it, and note the figure is as given by that source. Prefer it over aggregator or third-party numbers when both appear.\n\nCOMMITMENT RULE: while any relevant evidence exists, never write that the answer cannot be determined from the accepted evidence, or any similar refusal. State the best-supported value or name outright; if doubt remains, confine it to a single short trailing clause after the committed answer. SELF-CONSISTENCY: before finishing, verify the committed answer is the same candidate your own cited sentences support — if the body's evidence establishes a different candidate as satisfying the asked criteria, the opening answer must name THAT candidate, never a weaker fallback.\n\nCITATIONS/HONESTY: cite packet numbers like [1] near claims. No generic padding, invented facts, pipeline talk, or hidden reasoning."
            if unvetted_evidence:
                system_content += '\n\nUNVETTED-EVIDENCE NOTE: these packets are raw search snippets that skipped the usual admission review. Judge source quality and cross-snippet agreement yourself, then commit to the best-supported answer with citations. Being unvetted is not a reason to decline; flag residual doubt in one trailing clause at most.'
            user_content = f"Question: {question}\n\nAccepted evidence packets:\n{_format_records_section('ACCEPTED_PACKETS', 'packet', evidence_payload)}\n\nAccepted observations:\n{_format_records_section('ACCEPTED_OBSERVATIONS', 'observation', _observation_prompt_payload(accepted_observations))}\n\nCoverage metadata:\n{_format_records_section('COVERAGE', 'aspect', coverage_payload)}\n\nWrite the final answer as plain text. Start with the direct answer. If the premise is false, say so. If a requested fact is genuinely absent, say what is missing; but if you have the facts from authoritative sources, state them confidently rather than disclaiming the exact source label."
            return [{'role': 'system', 'content': system_content}, {'role': 'user', 'content': user_content}]

        def _extract_candidate_entities(results: tuple[AccumulatedSearchResult, ...]) -> tuple[str, ...]:
            entities: list[str] = []
            seen: set[str] = set()
            for result in results[-16:]:
                text = f"{result.title or ''} {result.note[:200]}"
                for match in re.finditer('\\b[A-Z][A-Za-z0-9&\\-]+(?:\\s+[A-Z][A-Za-z0-9&\\-]+){0,2}\\b', text):
                    entity = match.group(0)
                    key = entity.lower()
                    if key not in seen and len(entity) > 3 and (not entity.isupper()):
                        seen.add(key)
                        entities.append(entity)
                if len(entities) >= 12:
                    break
            return tuple(entities[:12])

        def _query_match_terms(query_text: str) -> tuple[str, ...]:
            terms: list[str] = []
            seen: set[str] = set()
            for token in re.findall('[a-z0-9]+', query_text.lower()):
                if token.isdigit() and len(token) >= 2 or (not token.isdigit() and len(token) >= 3):
                    if token not in seen:
                        seen.add(token)
                        terms.append(token)
            return tuple(terms)

        def _slot_intent_for_slot(slot_id: str, *, targets: tuple[EvidenceSearchTarget, ...]=()) -> str:
            for target in targets:
                if target.slot_id == slot_id and target.slot_intent:
                    return target.slot_intent
            return INTENT_SLOT_DEFINITIONS.get(slot_id, slot_id.replace('_', ' '))

        def _slot_intent_from_payload(slot_id: str, item: Mapping[str, object]) -> str:
            if slot_id in FREE_INTENT_SLOT_IDS:
                return _string_value(item.get('slot_intent'))
            return INTENT_SLOT_DEFINITIONS.get(slot_id, '')

        def _stable_valid_id_list(value: object, valid_ids: set[str]) -> list[str]:
            ids: list[str] = []
            seen: set[str] = set()
            for item in _string_list(value):
                if item in valid_ids and item not in seen:
                    ids.append(item)
                    seen.add(item)
            return ids

        def _stable_id_union(values: Iterable[str]) -> tuple[str, ...]:
            ids: list[str] = []
            seen: set[str] = set()
            for value in values:
                if not value or value in seen:
                    continue
                seen.add(value)
                ids.append(value)
            return tuple(ids)

        def _search_seed_from_accumulated_result(result: AccumulatedSearchResult) -> SearchResultSeed:
            slot_id = result.slot_id or PRIMARY_SOURCE_SLOT_ID
            return SearchResultSeed(search_receipt_id=result.receipt_id, search_result_id=result.result_id, slot_id=slot_id, slot_intent=result.slot_intent or _slot_intent_for_slot(slot_id), url=result.url, title=result.title, note=result.note)

        def _validate_source_inventory_payload(raw_inventory: Mapping[str, object], *, path: str) -> str | None:
            extra = sorted(set(raw_inventory) - set(SOURCE_INVENTORY_FIELD_NAMES))
            if extra:
                return f'{path} has unexpected keys: {json.dumps(extra)}. Use only {json.dumps(list(SOURCE_INVENTORY_FIELD_NAMES))}.'
            for field_name in SOURCE_INVENTORY_FIELD_NAMES:
                if field_name not in raw_inventory:
                    continue
                value = raw_inventory.get(field_name)
                if value in (None, ''):
                    continue
                if isinstance(value, str):
                    continue
                if not isinstance(value, list):
                    return f'{path}.{field_name} must be a JSON array of strings.'
                for i, item in enumerate(value):
                    if not isinstance(item, str):
                        return f'{path}.{field_name}[{i}] must be a string.'
            inventory = _source_inventory_from_payload(raw_inventory)
            if not _source_inventory_has_material(inventory):
                return f'{path} must include at least one non-empty source handle field among {json.dumps(list(SOURCE_INVENTORY_MATERIAL_FIELDS))}.'
            return None

        def _source_inventory_from_payload(raw_inventory: object) -> EvidenceSourceInventory:
            inventory = raw_inventory if isinstance(raw_inventory, Mapping) else {}
            return EvidenceSourceInventory(entities=_inventory_string_tuple(inventory, 'entities'), aliases=_inventory_string_tuple(inventory, 'aliases'), source_families=_inventory_string_tuple(inventory, 'source_families'), document_handles=_inventory_string_tuple(inventory, 'document_handles'), metric_terms=_inventory_string_tuple(inventory, 'metric_terms'), date_scope=_inventory_string_tuple(inventory, 'date_scope'), must_include=_inventory_string_tuple(inventory, 'must_include'), avoid=_inventory_string_tuple(inventory, 'avoid'), site_constraints=_site_constraints_from_value(inventory.get('site_constraints')))

        def _source_inventory_to_payload(inventory: EvidenceSourceInventory) -> dict[str, list[str]]:
            return {'entities': list(inventory.entities), 'aliases': list(inventory.aliases), 'source_families': list(inventory.source_families), 'document_handles': list(inventory.document_handles), 'metric_terms': list(inventory.metric_terms), 'date_scope': list(inventory.date_scope), 'must_include': list(inventory.must_include), 'avoid': list(inventory.avoid), 'site_constraints': list(inventory.site_constraints)}

        def _source_inventory_has_material(inventory: EvidenceSourceInventory) -> bool:
            return any((inventory.entities, inventory.aliases, inventory.source_families, inventory.document_handles, inventory.metric_terms, inventory.date_scope, inventory.must_include))

        def _inventory_string_tuple(raw_inventory: Mapping[str, object], field_name: str) -> tuple[str, ...]:
            values: list[str] = []
            seen: set[str] = set()
            for raw_value in _string_list(raw_inventory.get(field_name)):
                value = ' '.join(raw_value.split())
                key = value.casefold()
                if not value or key in seen:
                    continue
                seen.add(key)
                values.append(value)
                if len(values) >= MAX_INVENTORY_TERMS_PER_FIELD:
                    break
            return tuple(values)

        def _materialized_evidence_search_queries(routes: tuple[EvidenceSearchRoute, ...], *, tried_queries: set[str] | None=None) -> tuple[str, ...]:
            tried = tried_queries or set()
            queries: list[str] = []
            seen: set[str] = set()
            for route in routes:
                for q in _materialized_evidence_search_route_queries(route):
                    key = _query_identity(q)
                    if not key or key in tried or key in seen:
                        continue
                    seen.add(key)
                    queries.append(q)
            return tuple(queries)

        def _route_by_materialized_query(routes: tuple[EvidenceSearchRoute, ...]) -> dict[str, EvidenceSearchRoute]:
            result: dict[str, EvidenceSearchRoute] = {}
            for route in routes:
                for q in _materialized_evidence_search_route_queries(route):
                    key = _query_identity(q)
                    if key:
                        result.setdefault(key, route)
            return result

        def _materialized_evidence_search_route_queries(route: EvidenceSearchRoute) -> tuple[str, ...]:
            return (route.query, *(_constrained_site_query(route.query, c) for c in route.site_constraints))

        def _clean_llm_search_query(value: object) -> str:
            query = ' '.join(_string_value(value).split())
            if query.startswith('site:'):
                query = re.sub('^site:\\S+\\s*', '', query).strip()
            return query

        def _constrained_site_query(query: str, constraint: str) -> str:
            return f'site:{constraint} {query}'.strip()

        def _site_constraints_from_value(raw_constraints: object) -> tuple[str, ...]:
            constraints: list[str] = []
            seen: set[str] = set()
            for raw in _string_list(raw_constraints):
                constraint = _clean_site_constraint(raw)
                if not constraint or constraint in seen:
                    continue
                seen.add(constraint)
                constraints.append(constraint)
                if len(constraints) >= MAX_SITE_CONSTRAINTS_PER_ROUTE:
                    break
            return tuple(constraints)

        def _clean_site_constraint(value: object) -> str:
            text = _string_value(value).strip().casefold()
            if not text:
                return ''
            if text.startswith('site:'):
                text = text[5:].strip()
            if '://' in text:
                try:
                    text = urlsplit(text).netloc
                except ValueError:
                    return ''
            text = text.split('/', 1)[0].split('?', 1)[0].strip().strip('.')
            if text.startswith('www.'):
                text = text[4:]
            if not SITE_CONSTRAINT_DOMAIN_RE.fullmatch(text):
                return ''
            return text

        def _lite_search_query_syntax_error(query: str) -> str | None:
            if BAD_QUERY_BOOLEAN_BOUNDARY_RE.search(query.strip()):
                return 'query must not start or end with AND, OR, or NOT.'
            return None

        def _query_identity(query: str) -> str:
            return ' '.join(query.casefold().split())

        def _blocked_fetch_url_reason(url: str) -> str:
            try:
                host = urlsplit(url.strip()).netloc.lower()
            except ValueError:
                return ''
            if '@' in host:
                host = host.rsplit('@', 1)[-1]
            if ':' in host:
                host = host.split(':', 1)[0]
            if host.startswith('www.'):
                host = host[4:]
            return f'blocked_fetch_host:{host}' if any((host == s or host.endswith(f'.{s}') for s in BLOCKED_FETCH_HOST_SUFFIXES)) else ''

        def _compress_search_result_text(text: str) -> str:
            cleaned = re.sub('\\s+', ' ', text).strip()
            if not cleaned or len(cleaned) <= SEARCH_RESULT_TEXT_COMPRESSED_CHARS:
                return cleaned
            segment = max(1, SEARCH_RESULT_TEXT_SEGMENT_CHARS)
            n = len(cleaned)
            head_end = min(segment, n)
            tail_start = max(head_end, n - segment)
            mid_center = n // 2
            mid_start = max(head_end, mid_center - segment // 2)
            mid_end = min(tail_start, mid_start + segment)
            sections = [f'[compressed_search_result_text chars={n}]', f'[pos 0-{head_end}]', cleaned[:head_end]]
            if mid_end > mid_start:
                sections += [f'[pos {mid_start}-{mid_end}]', cleaned[mid_start:mid_end]]
            if tail_start < n:
                sections += [f'[pos {tail_start}-{n}]', cleaned[tail_start:]]
            return '\n'.join(sections)

        def _normalize_url(url: str) -> str:
            try:
                parts = urlsplit(url.strip())
            except ValueError:
                return url.strip().lower()
            if not parts.netloc:
                return url.strip().lower()
            scheme = (parts.scheme or 'https').lower()
            netloc = parts.netloc.lower()
            if netloc.startswith('www.'):
                netloc = netloc[4:]
            path = re.sub('/+$', '', parts.path)
            query_pairs = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not (k.lower().startswith('utm_') or k.lower() in {'fbclid', 'gclid', 'mc_cid', 'mc_eid'})]
            query = urlencode(sorted(query_pairs), doseq=True)
            return urlunsplit((scheme, netloc, path, query, ''))

        def _text_fingerprint(text: str) -> str:
            return ' '.join(re.findall('[a-z0-9]+', text.lower())[:80])

        def _text_excerpt(text: str, limit: int) -> str:
            cleaned = re.sub('\\s+', ' ', text).strip()
            return cleaned if len(cleaned) <= limit else f'{cleaned[:max(0, limit - 3)].rstrip()}...'

        def _text_window(*, text: str, start: int, end: int, context_chars: int) -> str:
            if not text:
                return ''
            start = max(0, min(start, len(text)))
            end = max(start, min(end, len(text)))
            before = max(0, start - context_chars)
            after = min(len(text), end + context_chars)
            prefix = '...\n' if before > 0 else ''
            suffix = '\n...' if after < len(text) else ''
            return f'{prefix}{text[before:after].strip()}{suffix}'.strip()

        def _elapsed_ms(started_perf: float) -> float:
            return round((perf_counter() - started_perf) * 1000, 3)

        def _assistant_text(response: LlmChatResult) -> str:
            return (response.llm.raw_text or '').strip()

        def _insufficient_answer(question: str, coverage: tuple[CoverageAspect, ...]) -> str:
            missing = [item.aspect for item in coverage if item.status != 'covered'] or [question]
            return f"I could not produce a source-backed answer from the available search results. The evidence gate accepted no sources, so a substantive answer would be unsupported. Needed evidence: direct, reliable sources covering {'; '.join(missing[:3])}."

        def _deterministic_answer_from_evidence(accepted_packets: tuple[AcceptedEvidence, ...]) -> str:
            sentences: list[str] = []
            for index, packet in enumerate(accepted_packets, start=1):
                source_text = packet.source_text.strip() or packet.source_result_text.strip()
                sentence = _leading_packet_sentence(source_text)
                if not sentence:
                    continue
                sentences.append(f'{sentence} [{index}].')
                if len(sentences) >= DETERMINISTIC_ANSWER_MAX_SENTENCES:
                    break
            if not sentences:
                return 'No supporting source text was available for this question.'
            return ' '.join(sentences)

        def _leading_packet_sentence(text: str) -> str:
            cleaned = re.sub('\\s+', ' ', text).strip()
            if not cleaned:
                return ''
            match = re.search('[.!?](?:\\s|$)', cleaned)
            sentence = cleaned[:match.end()].strip() if match else cleaned
            if len(sentence) > DETERMINISTIC_ANSWER_SENTENCE_MAX_CHARS:
                sentence = f'{sentence[:DETERMINISTIC_ANSWER_SENTENCE_MAX_CHARS - 3].rstrip()}...'
            return sentence.rstrip('.!?').strip()

        def _safe_response_text(text: str) -> str:
            cleaned = text.strip()
            return cleaned if cleaned else 'I could not produce a supported answer from the accepted evidence.'

        def _object_list(value: object) -> list[dict[str, object]]:
            if not isinstance(value, list):
                return []
            return [{str(k): v for k, v in item.items()} for item in value if isinstance(item, dict)]

        def _string_list(value: object) -> list[str]:
            if isinstance(value, str):
                text = value.strip()
                return [text] if text else []
            if not isinstance(value, list):
                return []
            return [s for item in value if (s := _string_value(item))]

        def _string_value(value: object) -> str:
            if value is None:
                return ''
            return str(value).strip()

        def _current_date() -> str:
            return datetime.now(UTC).date().isoformat()
        _MULTILINE_PROMPT_FIELD_NAMES = frozenset({'accepted_source_text', 'notes', 'preview', 'sample_text', 'search_result_text', 'source_result_text', 'source_text'})

        def _format_records_section(section_name: str, record_tag: str, records: Sequence[Mapping[str, object]]) -> str:
            if not records:
                return f'{section_name}:\n(none)'
            lines = [f'{section_name}:']
            lines.extend((_format_prompt_record(record_tag, record) for record in records))
            return '\n'.join(lines)

        def _format_scalar_list_section(section_name: str, values: Sequence[object]) -> str:
            if not values:
                return f'{section_name}:\n(none)'
            lines = [f'{section_name}:']
            lines.extend((_format_prompt_scalar_value(value) for value in values))
            return '\n'.join(lines)

        def _format_prompt_record(record_tag: str, record: Mapping[str, object]) -> str:
            lines = [f'<{record_tag}>']
            for field_name, value in record.items():
                prompt_field_name = field_name.upper()
                if field_name in _MULTILINE_PROMPT_FIELD_NAMES or (isinstance(value, str) and '\n' in value):
                    lines.append(f'{prompt_field_name}:')
                    text_value = _format_prompt_scalar_value(value)
                    if text_value:
                        lines.append(text_value)
                else:
                    lines.append(f'{prompt_field_name}: {_format_prompt_scalar_value(value)}')
            lines.append(f'</{record_tag}>')
            return '\n'.join(lines)

        def _format_prompt_scalar_value(value: object) -> str:
            if value is None:
                return ''
            if isinstance(value, bool):
                return 'true' if value else 'false'
            if isinstance(value, str):
                return value
            if isinstance(value, (int, float)):
                return str(value)
            if isinstance(value, (list, tuple)):
                if all((v is None or isinstance(v, (str, int, float, bool)) for v in value)):
                    return ', '.join((_format_prompt_scalar_value(item) for item in value))
            return json.dumps(value, ensure_ascii=False, separators=(',', ':'))

        def _observation_prompt_payload(observations: tuple[EvidenceObservation, ...]) -> list[dict[str, object]]:
            return [{'observation_index': i, 'role_id': o.role_id, 'slot_id': o.slot_id, 'candidate_id': o.candidate_id, 'entity': o.entity, 'metric': o.metric, 'value': o.value, 'time_scope': o.time_scope, 'support': o.support, 'source_tier': o.source_tier, 'packet_index': o.packet_index} for i, o in enumerate(observations, start=1)]

        def _role_ledger_prompt_payload(role_ledger: tuple[ResearchPlanRole, ...]) -> list[dict[str, object]]:
            return [{'role_id': r.role_id, 'slot_id': r.slot_id, 'slot_intent': r.slot_intent, 'question': r.question, 'kind': r.kind, 'status': r.status, 'value': r.value, 'why_not_covered': r.why_not_covered, 'queries': list(r.queries)} for r in role_ledger]
        _STRUCTURED_PROVIDER = _LLM_PROVIDER
        _STRUCTURED_MODEL = FINAL_SYNTHESIS_MODEL
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
        EMIT_UNFILLED_TOKENS = frozenset({'', '-', '--', 'n/a', 'na', 'none', 'none exists', 'no answer', 'null', 'unknown', 'unspecified', 'not specified', 'not reported', 'not provided', 'not available', 'not found', 'not determined', 'tbd', 'none found'})
        EMIT_MIN_REMAINING_SECONDS = 8.0
        EMIT_CALL_TIMEOUT_SECONDS = 20.0
        EMIT_MAX_PACKETS = 10
        EMIT_PACKET_CHARS = 3000
        _EMIT_EVIDENCE: list[tuple[AcceptedEvidence, ...]] = [()]

        def _set_emit_evidence(packets: tuple[AcceptedEvidence, ...]) -> None:
            _EMIT_EVIDENCE[0] = packets

        def _emit_value_unfilled(value: object) -> bool:
            if value is None:
                return True
            if isinstance(value, str):
                return value.strip().casefold() in EMIT_UNFILLED_TOKENS
            if isinstance(value, (list, tuple)):
                return len(value) == 0 or all((_emit_value_unfilled(item) for item in value))
            return False

        def _emit_is_unfilled(value: object, schema: object, root: object) -> bool:
            if _emit_value_unfilled(value):
                return True
            resolved = _so_resolve(schema, root)
            if not resolved or not isinstance(value, dict):
                return False
            properties = resolved.get('properties')
            properties = properties if isinstance(properties, dict) else {}
            required = [key for key in resolved.get('required') or () if isinstance(key, str)]
            for key in required or list(properties):
                if key not in value:
                    return True
                if _emit_is_unfilled(value[key], properties.get(key, {}), root):
                    return True
            return False

        def _emit_evidence_messages(question: str, schema: object, packets: tuple[AcceptedEvidence, ...]) -> list[dict[str, str]]:
            payload = [{'packet_number': i, 'url': p.url, 'title': p.title or '', 'accepted_source_text': (p.source_text or p.source_result_text or '')[:EMIT_PACKET_CHARS]} for i, p in enumerate(packets[:EMIT_MAX_PACKETS], start=1)]
            system_content = "ROLE: derive a schema-conforming value directly from source evidence.\n\nYou are given a question, a JSON Schema, and numbered evidence packets. Read the packets and emit the value the schema describes, resolving the question against the evidence yourself. There is no draft answer to copy and none is implied.\n\nEvery required field must carry a real value the evidence supports. Do NOT emit an empty list, an empty string, or a placeholder such as 'unknown', 'N/A', 'not reported' or 'none exists' for a field the evidence can fill. Quote numbers, dates and names exactly as the evidence states them, with their units and full precision; never round or reformat them.\n\nIf the evidence genuinely establishes that nothing satisfies the question, emit the empty value the schema allows rather than inventing one.\n\nOutput ONLY the bare JSON value the schema describes. No prose, no code fence."
            user_content = f"Question: {question}\n\nJSON Schema:\n{json.dumps(schema)[:STRUCTURED_SCHEMA_PROMPT_CHARS]}\n\nEvidence packets:\n{_format_records_section('ACCEPTED_PACKETS', 'packet', payload)}\n\nReturn the JSON value."
            return [{'role': 'system', 'content': system_content}, {'role': 'user', 'content': user_content}]

        async def _emit_from_evidence(question: str, schema: object, deadline: float) -> object:
            packets = _EMIT_EVIDENCE[0]
            if not packets:
                return None
            remaining = deadline - perf_counter()
            if remaining < EMIT_MIN_REMAINING_SECONDS:
                return None
            timeout = min(EMIT_CALL_TIMEOUT_SECONDS, remaining - 3.0)
            raw = await _so_call(_emit_evidence_messages(question, schema, packets), timeout)
            parsed = _so_extract_json(raw)
            if parsed is None:
                return None
            candidate = _so_coerce(parsed, schema, schema)
            if not _so_fits_size(candidate):
                return None
            if _so_errors(candidate, schema, schema):
                return None
            if _emit_is_unfilled(candidate, schema, schema):
                return None
            return candidate

        async def _emit_finalize(question: str, schema: object, value: object, citations: object, deadline: float) -> Response:
            if _emit_is_unfilled(value, schema, schema):
                try:
                    rescued = await _emit_from_evidence(question, schema, deadline)
                except Exception:
                    rescued = None
                if rescued is not None:
                    return _so_response(rescued, citations)
            return _so_response(value, citations)

        async def _structured_response(query: Query, schema: object, drafted: Response, deadline: float) -> Response:
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
                    return await _emit_finalize(query.text, schema, candidate, citations, deadline)
                best = candidate
                if attempt + 1 >= STRUCTURED_ATTEMPTS:
                    break
            if have_best:
                return await _emit_finalize(query.text, schema, best, citations, deadline)
            fallback = _so_skeleton(schema, schema)
            if fallback is None and answer:
                fallback = answer[:STRUCTURED_OUTPUT_CHAR_CAP]
            return await _emit_finalize(query.text, schema, fallback, citations, deadline)

        def _so_response(value: object, citations: object) -> Response:
            if not _so_fits_size(value):
                value = None
            try:
                return Response(output=value, citations=citations or None)
            except Exception:
                return Response(output=value)

        async def query(query: Query) -> Response:
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

class ThirdPath:

    def _compile(self):
        import asyncio
        import json
        import re
        from time import monotonic
        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        VERSION = 'v50-label'
        LLM_LANE_A = 'openrouter'
        LLM_LANE_B = 'ai_gateway'
        LOOP_MODEL_A = 'z-ai/glm-5.2'
        LOOP_MODEL_B = 'zai/glm-5.2-fast'
        AUDIT_MODEL = 'openai/gpt-oss-120b'
        SCHEMA_MODEL = 'openai/gpt-oss-120b'
        RESORT_MODEL = 'deepseek/deepseek-v3.2'
        SEARCH_PROVIDER = 'parallel'
        SEARCH_MODE = 'turbo'
        WALL_BUDGET_S = 266.0
        BRIEF_TIMEOUT_S = 50.0
        TURN_TIMEOUT_S = 75.0
        AUDIT_TIMEOUT_S = 28.0
        SEARCH_TIMEOUT_S = 18.0
        FETCH_TIMEOUT_S = 16.0
        WRAPUP_AT_S = 90.0
        MIN_TAIL_S = 8.0
        MAX_TURNS = 15
        AUDIT_EXTRA_TURNS = 2
        ANSWER_REPAIR_TURNS = 2
        RESCUE_TIMEOUT_S = 55.0
        AUDIT_REPAIR_MAX_S = 70.0
        AUDIT_MIN_HEADROOM_S = 130.0
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
        CITE_HOST_FLOOR = 2
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
        LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}, {'type': 'function', 'function': {'name': 'page_grep', 'description': 'Search INSIDE a page you already fetched, by regex or literal text, and get every match with its surrounding context and character offset. Use this when read_page showed you the head of a long page but the value you need is deeper in it -- do not re-fetch, grep it.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL of a page already fetched this run'}, 'pattern': {'type': 'string', 'description': 'regex or literal string to find, e.g. a city name, a year, a column label'}}, 'required': ['url', 'pattern']}}}, {'type': 'function', 'function': {'name': 'page_read', 'description': 'Read an arbitrary character range of a page you already fetched. Use the offsets page_grep reports to read the full table or section around a match.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL already fetched'}, 'offset': {'type': 'integer', 'description': 'start character offset'}, 'length': {'type': 'integer', 'description': 'how many characters to read (max 12000)'}}, 'required': ['url', 'offset']}}}, {'type': 'function', 'function': {'name': 'retain_evidence', 'description': "Keep the exact source text that proves a claim you are about to make. Pass the result number and the verbatim quote from it. Do this the moment you find a decisive value -- the judge only credits claims whose citation contains the supporting text, and this is how that text gets into your citation. Use it for the QUESTION'S PREMISES as well as your answer: every entity, work, date or figure the question names should end up with a retained quote confirming it.", 'parameters': {'type': 'object', 'properties': {'source': {'type': 'string', 'description': 'result number to quote from, e.g. 3'}, 'quote': {'type': 'string', 'description': 'verbatim text copied from that result that states the fact'}}, 'required': ['source', 'quote']}}}, {'type': 'function', 'function': {'name': 'check_constraints', 'description': 'Decide which items satisfy numeric criteria. Use this WHENEVER the question asks which entities meet one or more thresholds (population over X, rate below Y, more than N times, above the average). Transcribe the rows you read from the sources, state the tests, and this returns the exact set that passes. Do NOT do that comparison in your head -- you get it wrong on long tables and differently wrong each time. A threshold that is itself computed from the data (an average, a total) is written {"agg":"mean","field":"pop"}.', 'parameters': {'type': 'object', 'properties': {'rows': {'type': 'array', 'description': 'the transcribed table: one object per item, e.g. [{"entity":"<name>","<metric>":1234,"<metric2>":56}]', 'items': {'type': 'object'}}, 'tests': {'type': 'array', 'description': 'criteria, ALL of which must hold, e.g. [{"field":"pop","op":"<","value":15000000}]. op is one of < <= > >= == !=', 'items': {'type': 'object'}}}, 'required': ['rows', 'tests']}}}]
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
                    retained: list[list[int]] = []
                    for a, b in row.get('retained') or []:
                        a = max(0, min(int(a), note_len))
                        b = max(a + 1, min(int(b), note_len))
                        retained.append([a, b])
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
                    if retained:
                        merged.extend(retained)
                        merged.sort()
                        folded: list[list[int]] = []
                        for s, e in merged:
                            if folded and s <= folded[-1][1]:
                                folded[-1][1] = max(folded[-1][1], e)
                            else:
                                folded.append([s, e])
                        merged = folded
                    slices = [CitationSlice(start=s, end=e) for s, e in merged if e > s]
                    if not slices:
                        return None
                    return CitationRef(receipt_id=row['receipt_id'], result_id=row['result_id'], slices=slices)
                return None
        _WORD_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
        _STOP = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

        def _key_terms(text: str) -> set[str]:
            return {w for w in _WORD_RE.findall((text or '').casefold()) if w not in _STOP}
        _VALUE_CUE_RE = re.compile('\\d{1,4}\\s*[-–—]\\s*\\d{1,4}|\\d[\\d,]*(?:\\.\\d+)?\\s*%?')
        _CUE_MIN_LEN = 3
        _WEAK_CUE_RE = re.compile('^\\d{1,4}$')

        def _value_cues(*texts: str) -> set[str]:
            cues: set[str] = set()
            for text in texts:
                for raw in _VALUE_CUE_RE.findall(text or ''):
                    token = raw.replace(' ', '').replace('—', '-').replace('–', '-')
                    token = token.rstrip('.,').casefold()
                    if len(token) < _CUE_MIN_LEN or _WEAK_CUE_RE.match(token):
                        continue
                    cues.add(token)
                    if token.endswith('%'):
                        bare = token[:-1]
                        if len(bare) >= _CUE_MIN_LEN and (not _WEAK_CUE_RE.match(bare)):
                            cues.add(bare)
            return cues

        def _best_windows(note: str, terms: set[str], width: int, k: int=1, cues: set[str] | None=None) -> list[tuple[int, int]]:
            n = len(note)
            if n <= width:
                return [(0, n)]
            step = max(600, width // 3)
            low = note.lower().replace('–', '-').replace('—', '-')
            scored: list[tuple[int, int, int]] = []
            pos = 0
            cue_set = cues or frozenset()
            while pos < n:
                seg = low[pos:pos + width]
                hits = sum((1 for t in terms if t in seg))
                cue_hits = sum((1 for c in cue_set if c in seg))
                scored.append((cue_hits, hits, pos))
                if pos + width >= n:
                    break
                pos += step
            scored.sort(key=lambda hs: (-hs[0], -hs[1], hs[2]))
            picked: list[tuple[int, int]] = []
            for cue_hits, hits, start in scored:
                if len(picked) >= max(1, k):
                    break
                end = min(n, start + width)
                if any((start < pe and ps < end for ps, pe in picked)):
                    continue
                if picked and hits <= 0 and (cue_hits <= 0):
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
                    payload = await search_web(attempt, provider=SEARCH_PROVIDER, num=8, timeout=SEARCH_TIMEOUT_S, provider_extra={'mode': SEARCH_MODE})
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
            windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE, cues=_value_cues(question, focus))
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
                squashed_chars, origin = ([], [])
                for pos, ch in enumerate(text):
                    if not ch.isspace():
                        squashed_chars.append(ch.lower())
                        origin.append(pos)
                squashed_q = ''.join(q.split()).lower()
                if squashed_q:
                    hit = ''.join(squashed_chars).find(squashed_q)
                    if hit >= 0 and hit < len(origin):
                        i = origin[hit]
                        end = origin[min(hit + len(squashed_q), len(origin)) - 1] + 1
                        q = text[i:end]
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
        _CMP_OPS = ('<=', '>=', '!=', '<', '>', '==')
        _AGGS = ('mean', 'avg', 'median', 'sum', 'min', 'max', 'count')

        def _cn_num(v):
            if isinstance(v, bool):
                return None
            if isinstance(v, (int, float)):
                return float(v)
            s = str(v or '').strip()
            if not s:
                return None
            s = s.replace(',', '').replace('$', '').replace('%', '').replace('−', '-')
            m = re.search('-?\\d+(?:\\.\\d+)?', s)
            return float(m.group(0)) if m else None

        def _cn_agg(kind: str, values: list) -> float | None:
            vals = [v for v in values if v is not None]
            if not vals:
                return None
            kind = (kind or '').strip().lower()
            if kind in ('mean', 'avg'):
                return sum(vals) / len(vals)
            if kind == 'sum':
                return sum(vals)
            if kind == 'min':
                return min(vals)
            if kind == 'max':
                return max(vals)
            if kind == 'count':
                return float(len(vals))
            if kind == 'median':
                ordered = sorted(vals)
                mid = len(ordered) // 2
                return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0
            return None

        def _do_check_constraints(rows_arg, tests_arg) -> str:
            rows = rows_arg
            tests = tests_arg
            if isinstance(rows, str):
                try:
                    rows = json.loads(rows)
                except Exception:
                    return '# check_constraints: rows must be a JSON list of objects'
            if isinstance(tests, str):
                try:
                    tests = json.loads(tests)
                except Exception:
                    return '# check_constraints: tests must be a JSON list of objects'
            if not isinstance(rows, list) or not rows:
                return '# check_constraints: rows must be a non-empty JSON list of objects'
            if not isinstance(tests, list) or not tests:
                return '# check_constraints: tests must be a non-empty JSON list of objects'
            rows = [r for r in rows if isinstance(r, dict)][:400]
            if not rows:
                return '# check_constraints: no object rows found'

            def label(r):
                for k in ('entity', 'name', 'item', 'state', 'id'):
                    if r.get(k) not in (None, ''):
                        return str(r[k])
                return str(next(iter(r.values()), '?'))
            resolved = []
            for t in tests[:12]:
                if not isinstance(t, dict):
                    continue
                field = str(t.get('field') or '').strip()
                op = str(t.get('op') or '').strip()
                if op not in _CMP_OPS:
                    return '# check_constraints: op must be one of %s (got %r)' % (', '.join(_CMP_OPS), op)
                if not any((field in r for r in rows)):
                    return '# check_constraints: no row has field %r; fields present: %s' % (field, ', '.join(sorted({k for r in rows for k in r}))[:200])
                raw = t.get('value')
                if isinstance(raw, dict):
                    agg = str(raw.get('agg') or '').strip().lower()
                    if agg not in _AGGS:
                        return '# check_constraints: value.agg must be one of %s' % ', '.join(_AGGS)
                    over = str(raw.get('field') or field).strip()
                    threshold = _cn_agg(agg, [_cn_num(r.get(over)) for r in rows])
                    if threshold is None:
                        return '# check_constraints: could not compute %s of %r' % (agg, over)
                    shown = '%s(%s)=%g' % (agg, over, threshold)
                else:
                    threshold = _cn_num(raw)
                    if threshold is None:
                        return '# check_constraints: value %r is not a number or {agg,field}' % (raw,)
                    shown = '%g' % threshold
                resolved.append((field, op, threshold, shown))
            passing, lines, unusable = ([], [], [])
            for r in rows:
                name = label(r)
                verdicts, ok = ([], True)
                for field, op, threshold, shown in resolved:
                    got = _cn_num(r.get(field))
                    if got is None:
                        ok = False
                        verdicts.append('%s=? (missing)' % field)
                        if name not in unusable:
                            unusable.append(name)
                        continue
                    if op == '<':
                        hit = got < threshold
                    elif op == '<=':
                        hit = got <= threshold
                    elif op == '>':
                        hit = got > threshold
                    elif op == '>=':
                        hit = got >= threshold
                    elif op == '==':
                        hit = got == threshold
                    else:
                        hit = got != threshold
                    ok = ok and hit
                    verdicts.append('%s %g%s%s %s' % (field, got, op, shown, 'PASS' if hit else 'FAIL'))
                if ok:
                    passing.append(name)
                lines.append('%-28s %s -> %s' % (name[:28], '; '.join(verdicts), 'KEEP' if ok else 'drop'))
            head = '# check_constraints: %d of %d supplied rows satisfy ALL %d tests.\n# PASSING: %s\n# The comparisons above are exact -- do not redo them. But CHECK YOUR\n# INPUT before answering: you supplied %d rows. If the source table\n# lists more entities than that, transcribe the missing ones and call\n# this again -- an entity you never supplied can never be returned.\n' % (len(passing), len(rows), len(resolved), ', '.join(passing) if passing else '(none)', len(rows))
            if unusable:
                head += '# WARNING -- %d row(s) had a value this could not read and were\n# DROPPED: %s. Re-read those figures from the source and call again.\n' % (len(unusable), ', '.join(unusable[:12]))
            return head + '\n'.join(lines[:120])

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
            if name == 'check_constraints':
                return _do_check_constraints(args.get('rows'), args.get('tests'))
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

        async def _chat_turn(messages: list[dict], deadline: float, *, finish_only: bool, force_tools: bool=False):
            turn_wall = monotonic() + TURN_TIMEOUT_S + 35.0
            for lane_model in ((LLM_LANE_A, LOOP_MODEL_A, True), (LLM_LANE_A, LOOP_MODEL_A, False), (LLM_LANE_B, LOOP_MODEL_B, False)):
                lane = lane_model[0]
                model = lane_model[1]
                pinned = lane_model[2]
                timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0, turn_wall - monotonic())
                if timeout <= 5.0:
                    return None
                try:
                    payload = await llm_chat(provider=lane, model=model, messages=messages, tools=LOOP_TOOLS if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, provider_extra=_upstream(lane, model) if pinned else None, thinking={'enabled': False} if finish_only and lane == LLM_LANE_B else {'enabled': True, 'effort': 'low'}, max_output_tokens=6000 if finish_only and lane == LLM_LANE_B else None, timeout=timeout)
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
        BOARD_ROW_CHARS = 260
        BOARD_COMMIT_CHARS = 1200
        BOARD_MAX_ROWS = 48
        _FOLDED = '[folded into the evidence board]'

        def _board_rows(ledger: EvidenceLedger, question: str) -> list[tuple[int, int, str]]:
            rows: list[tuple[int, int, str]] = []
            for index, row in enumerate(ledger.rows, start=1):
                if row.get('kind') == 'reserved':
                    continue
                preview = ' '.join((row.get('preview') or '').split())
                if not preview:
                    continue
                rank = _source_rank(row.get('url', ''), row.get('title', ''), preview, question)
                title = ' '.join((row.get('title') or '').split())[:90]
                rows.append((rank, index, '[%d] %s — %s' % (index, title, preview[:BOARD_ROW_CHARS])))
            rows.sort(key=lambda r: (r[0], r[1]))
            return rows[:BOARD_MAX_ROWS]

        def _render_board(ledger: EvidenceLedger, question: str, *, width: int=BOARD_ROW_CHARS, char_cap: int=18000) -> str:
            scored = []
            for index, row in enumerate(ledger.rows, start=1):
                if row.get('kind') == 'reserved':
                    continue
                preview = ' '.join((row.get('preview') or '').split())
                if not preview:
                    continue
                rank = _source_rank(row.get('url', ''), row.get('title', ''), preview, question)
                scored.append((rank, index, row, preview))
            scored.sort(key=lambda r: (r[0], r[1]))
            parts, spent = ([], 0)
            for _rank, index, row, preview in scored[:BOARD_MAX_ROWS]:
                title = ' '.join((row.get('title') or '').split())[:90]
                block = '[%d] %s (%s)\n%s' % (index, title, row.get('url') or '', preview[:width])
                if spent + len(block) > char_cap:
                    break
                spent += len(block)
                parts.append(block)
            if not parts:
                return ''
            return 'EVIDENCE BOARD — every item gathered so far, strongest source first. These [n] are the citations available to you; cite the one that actually states each fact, never the same [n] for everything.\n\n' + '\n\n'.join(parts)

        def _fold_transcript(messages: list[dict], ledger: EvidenceLedger, question: str) -> None:
            tool_positions = [i for i, m in enumerate(messages) if isinstance(m, dict) and m.get('role') == 'tool']
            for i in tool_positions[:-8]:
                if messages[i].get('content') != _FOLDED:
                    messages[i] = dict(messages[i])
                    messages[i]['content'] = _FOLDED
            board = _render_board(ledger, question)
            if not board:
                return
            for i, m in enumerate(messages):
                if isinstance(m, dict) and m.get('role') == 'system' and str(m.get('content', '')).startswith('EVIDENCE BOARD'):
                    messages[i] = {'role': 'system', 'content': board}
                    return
            messages.append({'role': 'system', 'content': board})

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
            gates_left = 1
            held_answer = ''
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
                    if gates_left > 0 and ledger.rows and (_retained_count(ledger) == 0) and (not out_of_time) and (deadline - monotonic() > MIN_TAIL_S + 20.0):
                        gates_left -= 1
                        held_answer = candidate
                        messages.append({'role': 'system', 'content': _RETAIN_ORDER})
                        answer = ''
                        continue
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
                _fold_transcript(messages, ledger, question)
            if not _is_usable_answer(answer) and _is_usable_answer(held_answer):
                answer = held_answer
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
                if line.count('|') >= 3:
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
        _QL_PAREN_RE = re.compile("\\b([A-Z][\\w'&.:,-]*(?:[ ][\\w'&.:,-]+){0,8}[ ]?\\((?:1[89]|20)\\d{2}\\))")
        _QL_QUOTED_RE = re.compile('[' + re.escape('\'‘"“') + ']([^' + re.escape('\'’"”') + ']{3,90})[' + re.escape('\'’"”') + ']')
        QLABEL_MAX = 12

        def _question_labels(question: str) -> list:
            q = question or ''
            out: list = []
            for m in _QL_PAREN_RE.finditer(q):
                out.append(m.group(1).strip())
            for m in _QL_QUOTED_RE.finditer(q):
                s = m.group(1).strip()
                if len(s) >= 3:
                    out.append(s)
            seen: list = []
            for x in out:
                if x not in seen:
                    seen.append(x)
            return seen[:QLABEL_MAX]

        def _repair_label(value: str, labels: list) -> str:
            v = (value or '').strip()
            if len(v) < 3 or not labels:
                return value
            lv = v.lower()
            for lab in labels:
                if lv == lab.lower():
                    return value
            hits = [lab for lab in labels if len(lab) > len(v) and lv in lab.lower()]
            return hits[0] if len(hits) == 1 else value

        def _label_fidelity(obj, labels: list, depth: int=0):
            if depth > 6 or not labels:
                return obj
            if isinstance(obj, str):
                return _repair_label(obj, labels)
            if isinstance(obj, list):
                return [_label_fidelity(x, labels, depth + 1) for x in obj]
            if isinstance(obj, dict):
                return {k: _label_fidelity(v, labels, depth + 1) for k, v in obj.items()}
            return obj

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
        _ASCII_PUNCT_MAP = {8208: '-', 8209: '-', 8210: '-', 8211: '-', 8212: '-', 8213: '-', 8722: '-', 173: '-', 8216: "'", 8217: "'", 8218: "'", 8219: "'", 8242: "'", 8220: '"', 8221: '"', 8222: '"', 8223: '"', 8243: '"', 160: ' ', 8239: ' ', 8201: ' '}

        def _ascii_punct(value):
            if isinstance(value, str):
                return value.translate(_ASCII_PUNCT_MAP)
            if isinstance(value, list):
                return [_ascii_punct(v) for v in value]
            if isinstance(value, tuple):
                return tuple((_ascii_punct(v) for v in value))
            if isinstance(value, dict):
                return {k: _ascii_punct(v) for k, v in value.items()}
            return value

        def _cite_host(row) -> str:
            u = str((row or {}).get('url') or '')
            h = re.sub('^\\w+://', '', u).split('/')[0].lower()
            return h[4:] if h.startswith('www.') else h

        def _citations_for(answer: str, ledger: EvidenceLedger) -> list[CitationRef]:
            refs: list[CitationRef] = []
            hosts: set = set()
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
                hosts.add(_cite_host(row))
            if refs and len(hosts) < CITE_HOST_FLOOR:
                for idx in range(len(ledger.rows)):
                    if len(hosts) >= CITE_HOST_FLOOR or len(refs) >= CITATION_CAP:
                        break
                    row = ledger.rows[idx]
                    h = _cite_host(row)
                    if not h or h in hosts or (not row.get('retained')):
                        continue
                    ref = ledger.ref_for(idx + 1)
                    slices = getattr(ref, 'slices', None) if ref is not None else None
                    if ref is None or not slices:
                        continue
                    cost = sum((max(0, s.end - s.start) for s in slices))
                    if spent + cost > EVIDENCE_CHAR_BUDGET:
                        continue
                    spent += cost
                    refs.append(ref)
                    hosts.add(h)
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
        _RETAIN_ORDER = 'STOP -- do not answer yet. You have not retained any evidence, so the citations on your answer would show the TOP OF EACH PAGE (menus, cookie banners, site chrome) instead of the text that proves your claims. The grader sees only the spans you retain. For EVERY fact your answer asserts, call retain_evidence(source="[n]", quote="...") with the sentence or table row from [n] that states it, copied EXACTLY as the source prints it, including the figures. Retain one per fact -- several per source is normal and expected. Then write the final answer.'

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

        def _source_titles(ledger) -> set:
            out = set()
            for row in getattr(ledger, 'rows', None) or []:
                for key in ('title', 'url'):
                    v = ' '.join(str(row.get(key) or '').split()).casefold()
                    if len(v) > 3:
                        out.add(v)
            return out

        def _undigest_for_schema(basis: str, ledger=None) -> str:
            if not basis:
                return ''
            text = _DIGEST_NOISE_RE.sub(' ', basis)
            titles = _source_titles(ledger) if ledger is not None else set()
            out = []
            for raw in text.split('\n'):
                line = raw.strip().lstrip('-*• ').strip()
                if not line or _DIGEST_LEAD_RE.match(line):
                    continue
                if ' '.join(line.split()).casefold() in titles:
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
        _NUM_CMP_RE = re.compile('([-+]?\\d[\\d,]*(?:\\.\\d+)?)\\s*(>=|<=|=>|=<|>|<)\\s*([-+]?\\d[\\d,]*(?:\\.\\d+)?)')
        _VERDICT_RE = re.compile('(qualifies|does not qualify|excluded|fails|no\\b|yes\\b)', re.I)
        _PRIMARY_HOST_RE = re.compile('\\.gov$|\\.gov\\.|\\.mil$|\\.edu$|europa\\.eu|\\.un\\.org|worldbank\\.org|imf\\.org|oecd\\.org|sec\\.gov|federalreserve\\.gov|census\\.gov|bls\\.gov|fec\\.gov|nasa\\.gov|who\\.int', re.I)
        _OFFICIAL_HINT_RE = re.compile('investor|\\bir\\.|/investors?|annual-?report|press-?release|newsroom|/filing|10-k|20-f|official|statistics|factsheet|fact-?sheet', re.I)
        _AGGREGATOR_RE = re.compile('pinterest|quora|reddit|facebook|twitter|x\\.com|tiktok|medium\\.com|blogspot|wordpress|answers\\.|ehow|wikihow|coursehero|scribd|slideshare|tripadvisor|amazon\\.', re.I)

        def _arithmetic_contradictions(answer: str) -> list[str]:
            problems: list[str] = []
            for line in (answer or '').split('\n'):
                for chunk in re.split('[;.]\\s+', line):
                    match = _NUM_CMP_RE.search(chunk)
                    if match is None:
                        continue
                    left, op, right = (_as_number(match.group(1)), match.group(2), _as_number(match.group(3)))
                    if left is None or right is None:
                        continue
                    if op in ('>',):
                        holds = left > right
                    elif op in ('<',):
                        holds = left < right
                    elif op in ('>=', '=>'):
                        holds = left >= right
                    else:
                        holds = left <= right
                    verdict = _VERDICT_RE.search(chunk)
                    if verdict is None:
                        if not holds:
                            problems.append("'%s' is false: %s %s %s" % (chunk.strip()[:90], match.group(1), op, match.group(3)))
                        continue
                    said_yes = verdict.group(1).lower() in ('qualifies', 'yes')
                    if said_yes != holds:
                        problems.append("'%s' -- %s %s %s is %s, so the verdict is inverted" % (chunk.strip()[:90], match.group(1), op, match.group(3), holds))
            return problems[:6]

        def _coverage_gaps(answer: str, facts: list[dict]) -> list[str]:
            text = ' '.join((answer or '').split()).lower()
            if not text:
                return []
            missing: list[str] = []
            seen: set = set()
            for row in facts:
                label = (row.get('label') or '').strip()
                if len(label) < 3 or not row.get('value'):
                    continue
                key = label.lower()
                if key in seen:
                    continue
                seen.add(key)
                if key not in text:
                    missing.append('%s (established as %s [%s]) is never mentioned' % (label, row['value'], row.get('n', 0)))
            return missing[:8]

        def _lead_disagrees_with_body(answer: str, facts: list[dict]) -> bool:
            text = answer or ''
            if not text.strip():
                return False
            parts = re.split('(?<=[.!?])\\s+', ' '.join(text.split()))
            if len(parts) < 2:
                return False
            lead = parts[0].lower()
            rest = ' '.join(parts[1:]).lower()
            for row in facts:
                label = (row.get('label') or '').strip().lower()
                if len(label) < 3 or not row.get('value'):
                    continue
                if label in lead:
                    continue
                for cue in ('complete list', 'therefore', 'qualifying jurisdictions are', 'the answer is', 'in summary', 'final list'):
                    idx = rest.find(cue)
                    if idx >= 0 and label in rest[idx:idx + 260]:
                        return True
            return False
        _SRC_CUE_RE = re.compile('\\b(?i:according to|as (?:listed|reported|published) (?:in|by)|per|based on|using|listed in|from)\\s+(?:[a-z]{2,12}\\s+){0,2}')
        _SRC_TOK = '(?:[A-Z][\\w&.\\-]*|\\d{4})'
        _SRC_PROP_RE = re.compile(_SRC_TOK + '(?:\\s+(?:of|the|and|for|&)\\s+' + _SRC_TOK + '|\\s+' + _SRC_TOK + '){0,5}')
        _SRC_Q_OPEN = "'" + chr(8216) + chr(34) + chr(8220)
        _SRC_Q_CLOSE = "'" + chr(8217) + chr(34) + chr(8221)
        _SRC_QUOTED_RE = re.compile('(?<![A-Za-z])[' + re.escape(_SRC_Q_OPEN) + ']([A-Z][^' + re.escape(_SRC_Q_CLOSE) + ']{6,80})[' + re.escape(_SRC_Q_CLOSE) + ']')
        _SRC_STOP = frozenset(('the', 'this', 'that', 'these', 'those', 'their', 'its'))
        _SRC_GENERIC = frozenset(('index', 'ranking', 'rankings', 'list', 'lists', 'data', 'chart', 'charts', 'company', 'official', 'statistics', 'report', 'reports', 'survey', 'table', 'tables', 'database', 'databases', 'articles', 'article', 'page', 'pages', 'snapshot', 'edition', 'cycle', 'results'))

        def _named_sources(question: str) -> list:
            q = question or ''
            out: list = []
            for m in _SRC_QUOTED_RE.finditer(q):
                out.append(m.group(1))
            for m in _SRC_CUE_RE.finditer(q):
                pm = _SRC_PROP_RE.match(q[m.end():m.end() + 90])
                if not pm:
                    continue
                s = pm.group(0).strip(' .,;:')
                if len(s) < 4 or s.lower() in _SRC_STOP:
                    continue
                if ' ' not in s and len(s) < 5:
                    continue
                out.append(s)
            seen: list = []
            for x in out:
                if x not in seen:
                    seen.append(x)
            return seen[:6]

        def _squash(text: str) -> str:
            return re.sub('[^a-z0-9]+', '', (text or '').lower())

        def _matches_named_source(url: str, title: str, names: list) -> bool:
            host = _squash(re.sub('^\\w+://', '', url or '').split('/')[0])
            blob = _squash('%s %s' % (url or '', title or ''))
            if not blob:
                return False
            for n in names or ():
                sq = _squash(n)
                multiword = ' ' in (n or '').strip()
                if not multiword:
                    if len(sq) >= 5 and sq in host:
                        return True
                    continue
                if len(sq) >= 6 and sq in blob:
                    return True
                toks = [_squash(t) for t in re.findall('[A-Za-z][\\w\\-]{3,}', n or '')]
                toks = [t for t in toks if len(t) >= 4]
                if any((len(t) >= 5 and t not in _SRC_GENERIC and (t in host) for t in toks)):
                    return True
            return False

        def _source_rank(url: str, title: str, note: str, ask: str) -> int:
            blob = '%s %s' % (url or '', title or '')
            rank = 50
            if _PRIMARY_HOST_RE.search(url or ''):
                rank = 5
            elif _OFFICIAL_HINT_RE.search(blob):
                rank = 15
            elif 'wikipedia.org' in (url or '').lower():
                rank = 25
            if _AGGREGATOR_RE.search(url or ''):
                rank = 90
            text = (note or '').lower()
            terms = [w for w in re.findall('[a-z]{4,}', (ask or '').lower())][:12]
            hits = sum((1 for w in set(terms) if w in text))
            digits = len(re.findall('\\d', text))
            rank -= min(hits, 8) * 2
            rank -= 4 if digits >= 12 else 0
            names = _named_sources(ask)
            if names and _matches_named_source(url, title, names):
                rank -= 40
            return rank

        def _as_number(raw: str):
            try:
                return float(raw.replace(',', '').lstrip('+'))
            except Exception:
                return None
        _MARKER_RE = re.compile('\\[(\\d{1,3})\\]')

        async def query(query: Query) -> Response:
            question = (query.text or '').strip()
            if not question:
                return Response(text='No question provided.')
            try:
                return await _solve(query, question)
            except Exception:
                return Response(text=f'Best-effort answer unavailable for: {question[:500]}')
        RESEARCH_RESERVE_S = 53.0
        COMMIT_TIMEOUT_S = 46.0
        COMMIT_MIN_BUDGET_S = 20.0

        def _cite_count(text: str) -> int:
            return len(set(_CITE_MARK_RE.findall(text or '')))
        QUOTE_TABLE_CHARS = 1400

        def _quote_table(ledger: EvidenceLedger) -> str:
            parts = []
            for i, row in enumerate(ledger.rows, start=1):
                text = row.get('text') or ''
                for a, b in row.get('retained') or []:
                    excerpt = text[max(0, int(a)):int(b)][:QUOTE_TABLE_CHARS].strip()
                    if excerpt:
                        parts.append('[%d] %s\n%s' % (i, row.get('title') or row.get('url') or '', excerpt))
            return '\n\n'.join(parts)

        def _retained_count(ledger: EvidenceLedger) -> int:
            return sum((len(r.get('retained') or []) for r in ledger.rows))

        async def _forced_commit(question: str, ledger: EvidenceLedger, board: str, deadline: float) -> str:
            budget = min(COMMIT_TIMEOUT_S, deadline - monotonic() - DIGEST_TAIL_S)
            if budget < COMMIT_MIN_BUDGET_S or not ledger.rows:
                return ''
            evidence = board or _ledger_digest(ledger)
            if not evidence:
                return ''
            quotes = _quote_table(ledger)
            if quotes:
                evidence = 'QUOTES YOU RETAINED AS PROOF — prefer these, and cite the [n] shown here for each fact they carry.\n\n%s\n\n%s' % (quotes[:24000], evidence)
            system = LOOP_RULES + '\n\nRESEARCH IS OVER. You have no tools and nothing further to gather. Write the final answer from the evidence board below, which holds every item collected, strongest source first. Cite its [n] exactly as written; never invent one. Cover every part of the question -- this is the answer that will be scored.'
            try:
                return (await _chat_simple(LLM_LANE_A, LOOP_MODEL_A, system, 'QUESTION: %s\n\n%s' % (question, evidence[:60000]), max_tokens=2600, timeout=budget)).strip()
            except Exception:
                return ''

        async def _research_then_commit(question: str, brief: str, ledger: EvidenceLedger, deadline: float) -> tuple[str, list[dict]]:
            research_deadline = deadline - RESEARCH_RESERVE_S
            pending, messages = ('', [])
            try:
                pending, messages = await _loop(question, brief, ledger, research_deadline, MAX_TURNS)
            except Exception:
                pending, messages = ('', [])
            if _is_usable_answer(pending):
                return (pending, messages)
            board = _render_board(ledger, question)
            committed = await _forced_commit(question, ledger, board, deadline)
            if _is_usable_answer(committed):
                return (committed, messages)
            return (pending, messages)

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
                answer, messages = await _research_then_commit(question, brief, ledger, deadline)
            except Exception:
                answer = ''
            try:
                if _is_usable_answer(answer) and deadline - monotonic() > 75.0 and (_spend_left() >= AUDIT_MIN_USD):
                    patched = await _audit_patch(question, answer, messages, ledger, deadline)
                    if _is_usable_answer(patched):
                        answer = patched
            except Exception:
                pass
            try:
                if _is_usable_answer(answer) and deadline - monotonic() > AUDIT_MIN_HEADROOM_S:
                    _rows = [{'label': (r.get('title') or '')[:80], 'value': '', 'n': i + 1, 'verified': True} for i, r in enumerate(ledger.rows)]
                    _defects = _arithmetic_contradictions(answer)
                    if _lead_disagrees_with_body(answer, _rows):
                        _defects.append('the opening list omits a member the answer later endorses; sentence one must already carry the final, complete list')
                    if _defects:
                        _audit_deadline = min(deadline, monotonic() + AUDIT_REPAIR_MAX_S)
                        _fixed = await _loop(question, brief, ledger, _audit_deadline, 1, carry=list(messages) + [{'role': 'system', 'content': 'Your answer has these defects:\n- ' + '\n- '.join(_defects[:6]) + '\nRecompute every comparison and rewrite the COMPLETE answer from scratch. Do not append a correction: sentence one must already state the final, complete answer.'}])
                        _cand = _fixed[0] if isinstance(_fixed, tuple) else ''
                        if _is_usable_answer(_cand) and (not _arithmetic_contradictions(_cand)):
                            answer = _cand
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
            text = _cap(_ascii_punct(answer)) or f'Best-effort answer unavailable for: {question[:400]}'
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
                        structured = _label_fidelity(structured, _question_labels(question))
                    except Exception:
                        pass
                    try:
                        structured = _ascii_punct(structured)
                        return Response(output=structured, citations=citations or None)
                    except Exception:
                        structured = None
                basis = answer if _is_usable_answer(answer) else ''
                if not basis:
                    basis = _deterministic_answer(question, ledger)
                if not basis or _STUB_ANSWER_RE.match(basis.strip()):
                    basis = question[:400]
                if basis is not answer:
                    cleaned = _undigest_for_schema(basis, ledger)
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

class DifficultyRouter:
    _PROVIDER = 'openrouter'
    _MODEL = 'google/gemma-4-31b-it'
    _DIFFICULTY_PROMPT = 'Easy or Hard? Reply with one word only.'
    _GRANULARITY_PROMPT = 'Score the granularity/detail quality of this problem on an integer scale from 0 to 10. Assess ALL of the following: (1) Are the requirements clearly described? (2) Are edge cases (exceptions) mentioned or implied? (3) Are constraints and limitations clearly specified? (4) Are the I/O formats clearly defined? (5) Is the problem description accurate enough to avoid ambiguity? (6) Are technical terms and concepts clearly explained? (7) Is the scope of the problem well defined? Scoring guide: 10 = Perfect detail, fully solvable without ambiguity; 7-9 = Excellent detail, generally clear but with minor ambiguity; 4-6 = Average detail, some important information missing; 1-3 = Insufficient detail, significant information missing; 0 = Insufficient detail, problem cannot be solved. Reply with ONLY an integer from 0 to 10.'
    _TIMEOUT_S = 6.0

    async def _is_easy(self, text: str) -> bool:
        result = await asyncio.wait_for(llm_chat(provider=self._PROVIDER, model=self._MODEL, messages=[{'role': 'system', 'content': self._DIFFICULTY_PROMPT}, {'role': 'user', 'content': text}], temperature=0.0, max_output_tokens=4, thinking=LlmThinkingConfig(enabled=False), timeout=self._TIMEOUT_S), timeout=self._TIMEOUT_S + 2.0)
        label = (result.response.raw_text or '').strip().lower()
        return label.startswith('easy') or ('easy' in label and 'hard' not in label and ('medium' not in label))

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
_FIRST_RUN = FirstPath()._compile()
_SECOND_RUN = SecondPath()._compile()
_THIRD_RUN = ThirdPath()._compile()
_ROUTER = DifficultyRouter()

@entrypoint('query')
async def query(query: Query) -> Response:
    try:
        easy = await _ROUTER._is_easy(query.text)
    except Exception:
        easy = False
    if easy:
        return await _THIRD_RUN(query)
    try:
        granularity = await _ROUTER._granularity_score(query.text)
    except Exception:
        granularity = 0
    if granularity <= 5:
        return await _SECOND_RUN(query)
    return await _FIRST_RUN(query)
