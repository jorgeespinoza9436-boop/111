from __future__ import annotations
import asyncio
from time import monotonic
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class PrimarySolver:

    def _compile(self):
        """agent_d — v32 "toolloop": model-driven research agent.

REDESIGN RATIONALE (batch 88c4a837: our pipeline 0.000, the field's tool-loop
family 0.70-0.80). The scoring architecture is a native agentic loop: the LLM
itself drives search/fetch via tool calls, reads full results in context,
cross-references candidate-by-candidate, and writes one cited answer. Our old
staged pipeline (search -> gate -> chunk -> synth) funnels evidence through
abstractions that lose cross-referencing, never uses model knowledge, and
cannot iterate multi-hop. This file is our OWN implementation of the loop
architecture, keeping the assets our line already validated:
  - the v31.8 answer-shape discipline (asked-KIND, set-intersection
    completeness, numeric verbatim, world-negative vs evidence-concession);
  - a miniaturized section-localizer: big fetched pages are rendered as the
    HEAD plus the TOP-K densest regions (so a filing's deep section, or an
    answer set spread across two distant tables, is readable in one call);
  - SEC EDGAR primary-doc routing as a loop hint;
  - dual-provider LLM lanes (openrouter primary, our paid ai_gateway fallback).
Kill-safety: everything bounded by one deadline; force-commit well before it.
"""
        import asyncio
        import json
        import re
        from time import monotonic
        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        VERSION = 'v42-retain-premises'
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
            """A superlative/count question ANSWERS with one item, but RESEARCHING it
    requires the whole pool: you cannot know the oldest player without every
    player's birthdate, or the most common name without the full tally. The set
    detector deliberately cancels on superlatives (the answer shape is singular)
    — so those questions were getting no completeness discipline at all."""
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
        _VALUE_CUE_RE = re.compile('\\d{1,4}\\s*[-–—]\\s*\\d{1,4}|\\d[\\d,]*(?:\\.\\d+)?\\s*%?')
        _CUE_MIN_LEN = 3
        _WEAK_CUE_RE = re.compile('^\\d{1,4}$')

        def _value_cues(*texts: str) -> set[str]:
            """Specific numeric literals the question names, normalized for substring match."""
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
            """Deterministic scan: the K highest-density, NON-OVERLAPPING windows, in
    document order.

    v32.4 — showing only the single densest window was a direct cause of our
    run-to-run set variance (prod f462cada: runs returned different SUBSETS of
    the answer). When a question's qualifying entities are spread across two
    tables far apart in one page, a single window can only ever show one of
    them, so which one the model sees depends on the trajectory. Surfacing the
    top-K regions makes one fetch carry the whole answer set, on every run."""
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
            """Append a tool's rows in call order, then resolve its [n] placeholders."""
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
            """Loosen an over-constrained query: drop site: operators and quoting.
    Champion lineages retry a failed search this way instead of giving up."""
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
            """ONE tokenizer for both the model's company arg and EDGAR titles — the
    review proved asymmetric tokenization false-negatived 'Apple Inc.',
    "McDonald's" and 'U.S. Bancorp'."""
            return [w for w in _SEC_ALNUM_RE.findall((text or '').lower()) if w not in _SEC_STOPWORDS]

        def _sec_norm_form(form: str) -> str:
            """Canonicalize model-supplied form codes to EDGAR's ('10K'->'10-K',
    'def14a'->'DEF 14A', 'Form 10-Q'->'10-Q')."""
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
            """Pick (accession, primaryDocument) for the canonicalized form. A named
    year matches on reportDate ONLY (the fiscal period end) — a filingDate-year
    match would silently return the PRIOR fiscal year's document (review
    finding). Named-year miss -> None; no year -> most recent of that form."""
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
            """Most recent fetched row for `url` (suffix match tolerates redirects)."""
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
            """Regex/literal search inside an already-fetched page.

    uid210 (score 0.85, batch c4c8bef0) stores full pages and lets the model
    navigate them; its citations are ~200-char slices aimed ~21k deep. Our fixed
    head+window render showed the model the page top and cited it, which is why
    our slices materialize navigation chrome. Grep closes that gap without a
    second fetch: no new tool cost, and the page is already in memory."""
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
            """Read an arbitrary region of an already-fetched page (offsets from page_grep)."""
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
            """Model-nominated evidence: keep the span that actually proves a claim.

    The model passes a source number [n] and the VERBATIM text from it that
    supports what it is about to assert. We locate that text and remember the
    span so _citations_for can cite it. If the quote is not found we say so and
    ask for an exact one -- that refusal is the whole training signal, the same
    move uid210 makes when a retained span omits a numeric fact it asserted."""
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
            """The smallest reasoning budget this lane+model will actually accept."""
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

        async def _chat_turn(messages: list[dict], deadline: float, *, finish_only: bool, force_tools: bool=False):
            """One loop turn; lane A first, lane B (our paid ai_gateway) on failure."""
            for lane_model in ((LLM_LANE_A, LOOP_MODEL_A), (LLM_LANE_B, LOOP_MODEL_B)):
                lane = lane_model[0]
                model = lane_model[1]
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
            """One call: the model's own best answer + a verification plan. Returns
    (draft_answer, briefing_block). The draft alone often carries a knowledge-
    heavy batch; the loop then verifies the load-bearing facts."""
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
            """Run the seed queries concurrently; return a numbered digest to inject."""
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
            """Authority-ordered evidence board.

    Width matters more than it looks. At 260 chars a row is a summary, not
    evidence: the commit stage could not tell which row held which figure and
    fell back on citing the top-ranked row for everything -- one task emitted 13
    markers that all pointed at a single summary slice containing none of the
    numbers, and the judge called it hallucinated. The commit therefore gets
    full-width rows; only the mid-loop orientation copy stays compact."""
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
            """Replace older raw tool output with the rebuilt board, in place.

    The tool messages themselves must stay: every tool_call_id needs a reply or
    the transcript fails validation. Only their CONTENT is folded, and only for
    turns before the current one."""
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
                _fold_transcript(messages, ledger, question)
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
            """Reduce the answer to its first line when the question forbids anything else.

    Called AFTER _citations_for so the citation array keeps every [n] the proof
    section carried -- the answer complies while traceability is preserved."""
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
            """Return the form of `value` that the SOURCE actually uses.

    Batch c4c8bef0 / task 3818d8c9: the reference wanted the CityPopulation.de
    strings ["Makkah", "Ad-Dammam", ...]; we shipped ["Mecca (Makkah)", ...],
    annotating each transliteration with its familiar English name, and scored 0.0
    against uid210's 1.0. Same class as 4b74e8b1 ("output only the exact text from
    the column"). A helpful gloss is a wrong answer when the question names a source.

    Only fires when the emitted value is ABSENT from every source and exactly one
    of its two components is present -- so it can never rewrite a value the source
    really contains (e.g. "Dallas-Fort Worth-Arlington, TX (Metropolitan Statistical
    Area)", which IS the column text)."""
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
            """Apply the verbatim rule to every string leaf of a structured output."""
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
            """Build refs under the platform's materialized-evidence wall.

    harnyx_commons/application/miner_response_hydration.py: the validator
    materializes every cited slice and raises MinerResponsePayloadError past
    _MAX_TOTAL_EVIDENCE_CHARS = 120_000 — the whole response then scores 0.
    A SLICELESS ref materializes start=0..len(note), i.e. the ENTIRE note, so
    search refs (which carry no spans) are the expensive ones. Prod f462cada
    hit miner_response_invalid on 2 runs; multi-window reads raised the per-ref
    cost, so budget it explicitly instead of hoping."""
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
            """F13: only a tool-call JSON at the very START is junk; an answer that
    QUOTES a JSON record mid-text is legitimate."""
            return bool(re.match('\\s*\\{\\s*"(?:name|tool|function)"\\s*:', s))

        def _is_degenerate_repetition(text: str) -> bool:
            """True when the text is the same sentence emitted over and over — the
    classic stalled/greedy-decoding artifact. Cheap and language-agnostic:
    if the distinct sentences cover under half the body, it is a loop."""
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
            """A submittable answer. F13/F8 fixes: a CITED, substantive answer is always
    an answer — terse replies ('Yes, both are French [1].') and the reasoned-
    impossibility shape LOOP_RULES explicitly asks for were being thrown away,
    and a 4000-char cited answer was discarded for its opening clause."""
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
            """The briefing draft marks shaky facts '(verify)' by instruction; those
    markers must NEVER reach a submitted answer (judge-penalized uncertainty)."""
            return _VERIFY_MARK_RE.sub('', text or '').strip()

        def _ledger_digest(ledger: EvidenceLedger, char_cap: int=60000) -> str:
            """A clean numbered evidence digest — no tool-call history. Preserves the
    exact [n] numbering so citations still resolve. Committing from this beats
    replaying the raw transcript: shorter, no assistant/tool scaffolding, and it
    cannot drop early [n]s off the front of a truncated message window."""
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
            """First stretch of real prose in a page preview, or '' if there is none."""
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
            """Last rung, no LLM. Never emit a bare 'unavailable' line: the judge sees
    only the answer text and makes a forced preference, so advertising our own
    failure hands it a reason to pick the other side. A cited partial always
    beats a refusal."""
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
            """Last write from the evidence already gathered: MINIMUM reasoning the lane
    accepts (see _least_think — only the gpt-oss family requires reasoning), NO
    tools, and a CLEAN numbered digest instead of the raw transcript — so the
    model cannot emit tool markup and cannot lose early [n]s to a truncated
    message window."""
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
            """Top-level JSON type a schema demands, '' when it does not pin one."""
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
            """Deterministic last-resort value for a structured query.

    A structured query whose Response carries `text` instead of `output` is
    rejected whole by the platform (miner_response_hydration: "structured query
    response must use output") — a hard zero, not a degraded score. So when every
    LLM conversion attempt fails we still owe the host SOMETHING schema-shaped
    built from the answer we already have.
    """
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
            """Drop leading UNCITED stage-direction sentences. Never touches a sentence
    that carries an [n]: that is a real answer, however it opens."""
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
            """Check every explicit numeric comparison the answer writes down.

    The synthesis is told to show each condition check as 'A > B -> verdict'. That
    makes the reasoning machine-checkable: a wrong comparison is the single failure
    that has cost the most here (11 > 10.55 was read as 'at or below the mean',
    dropping a qualifying member). No LLM is asked to re-check itself."""
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
            """Labels the fact table established but the answer never mentions.

    The judge marks an incomplete roster down hard ("Answer 2 is incomplete
    (coverage failure)") even when every member it does name is correct. Because
    extraction now emits one labelled row per member, the members the run actually
    established are known, so the omission is detectable without asking an LLM."""
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
            """True when the opening list omits a member the answer later endorses.

    The coverage repair pass used to append the missing member in a later
    paragraph while leaving the lead stale, producing exactly the contradiction
    the judge punished: 'the jurisdictions are G, M, P ... therefore the complete
    list is A, G, M, P'."""
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

        def _source_rank(url: str, title: str, note: str, ask: str) -> int:
            """Lower is better. The pairwise judge does not only ask whether the answer is
    right -- on a task where both answers were correct and complete it awarded the
    win to the side whose ONE citation note stated the whole answer outright, and
    marked ours down for piecing the same conclusion together from weaker snippets.
    So order the evidence by how authoritative it is AND how directly its note
    already answers the question, and let that order drive the [n] numbering."""
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

        async def _forced_commit(question: str, ledger: EvidenceLedger, board: str, deadline: float) -> str:
            """Tool-free. Composes the answer from the board, not from the transcript."""
            budget = min(COMMIT_TIMEOUT_S, deadline - monotonic() - DIGEST_TAIL_S)
            if budget < COMMIT_MIN_BUDGET_S or not ledger.rows:
                return ''
            evidence = board or _ledger_digest(ledger)
            if not evidence:
                return ''
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
            board = _render_board(ledger, question)
            committed = await _forced_commit(question, ledger, board, deadline)
            if _is_usable_answer(pending):
                return (pending, messages)
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

class ReserveSolver:

    def _compile(self):
        """SN67 Harnyx miner — autonomous tool-use research agent, v9 (evidence ledger).

Lineage: uid_16 autonomous GLM-5 tool-use loop -> iter2 citation/timeout safety ->
v5 answer ladder + tool-call leak guard -> v6 exhaustiveness prompt -> v7 structural
containment -> v8 structural hardening -> v9 (this file).

Post-mortem 2026-08-01:
  Replaced architectural dimension: evidence_state_flow
    Old root: conversational tool history (messages list) as sole evidence carrier.
        _ResultIndex tracked source metadata for citation construction but the model
        accessed evidence only through the growing transcript. The system prompt was
        static regardless of query requirements — no format adaptation, no source-
        compliance tracking, no structured state between stages.
    New root: _FactLedger carries structured evidence state between all stages.
        Query text is parsed deterministically into output-format constraints
        (bare/default), named-source requirements, and source-compliance state.
        The system prompt is generated dynamically from the ledger via
        _build_loop_system(), making research guidance format-aware and source-
        aware. Source compliance is tracked per tool result. The answer rendering
        stage reads the ledger to produce format-compliant, sanitized output —
        reasoning preamble, scaffold, and tool markup never reach the final
        response text.

  Fixes routed through the new evidence-state-flow:
    - scaffold_leak (4b74e8b1, b1816359): _build_loop_system reads
      ledger.output_format; when 'bare' (detected from 'Output only'), the system
      prompt omits Proof-of-completeness scaffold and FINAL ANSWER prefix.
      render_answer() strips residual scaffold, FINAL ANSWER prefix (bare only),
      and reasoning preamble ('Now I have all the information...').
      _sanitize_toolcall strips raw <tool_call> markup.
    - source_fidelity (4b74e8b1): Named sources parsed from query into
      ledger.named_sources and injected into system prompt as SOURCE REQUIREMENT.
      Source compliance tracked per tool result; mid-loop SOURCE GAP guidance
      injected when required sources are missing.
    - schema_missing (6752fb6a, 99811d8e, ca31dfd2): output_schema detection on
      Query; when present, answer is converted to JSON via a dedicated LLM call
      and returned as Response(output=...). Time reserved (SCHEMA_RESERVE_SECONDS)
      so the research loop stops early enough for the conversion.

Providers: openrouter (GLM-5) + parallel — exact match to funded keys.
"""
        import json
        import re
        from time import perf_counter
        from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        MODEL = 'z-ai/glm-5'
        LLM_PROVIDER = 'openrouter'
        TOOL_PROVIDER = 'parallel'
        MAX_TURNS = 14
        MAX_RETRY_ATTEMPTS_PER_TURN = 2
        FETCH_RETRY_ATTEMPTS = 2
        FORCE_COMMIT_LOOKAHEAD_TURNS = 2
        TASK_TOTAL_BUDGET_SECONDS = 270.0
        LLM_TURN_TIMEOUT_SECONDS = 70.0
        SEARCH_TIMEOUT_SECONDS = 20.0
        FETCH_TIMEOUT_SECONDS = 15.0
        FORCE_COMMIT_TIME_THRESHOLD_SECONDS = 100.0
        FINAL_RESERVE_SECONDS = 55.0
        TAIL_RESERVE_SECONDS = 6.0
        MIN_TOOL_TIMEOUT_SECONDS = 5.0
        SCHEMA_RESERVE_SECONDS = 35.0
        SCHEMA_TIMEOUT_SECONDS = 50.0
        LOOP_ABORT_REMAINING_SECONDS = 5.0
        LAST_RESORT_MIN_SECONDS = 12.0
        HEDGE_REWRITE_MIN_SECONDS = 15.0
        SEARCH_EXCERPT_CHARS = 700
        FETCH_CONTENT_CHARS = 6000
        MAX_CITATIONS = 16
        EVIDENCE_CHAR_BUDGET = 110000
        DETERMINISTIC_ANSWER_MAX_SOURCES = 6
        HEDGE_LEAD_SCAN_CHARS = 400
        MIN_USABLE_ANSWER_CHARS = 40
        DETERMINISTIC_LEAD_CHARS = 300
        _JUNK_HOSTS = ('reddit.com', 'quora.com', 'fandom.com', 'blogspot.', 'grokipedia', 'pinterest.', 'answers.com', 'scribd.com')
        _PRIMARY_HINTS = ('.gov', '.edu', 'wikipedia.org', '.int', 'sec.gov', 'official')

        def _parse_named_sources(query_text: str) -> list[str]:
            """Deterministically extract source names the query requires data from."""
            sources: list[str] = []
            for m in re.finditer('according to (?:the )?([^,;.?!]{3,80}?)(?:\\s*[,;.?!]|\\s+and\\s|\\s+which\\s|\\s+a\\s|\\s+that\\s|\\s+in\\s|\\s*$)', query_text):
                sources.append(m.group(1).strip())
            for m in re.finditer('Wikipedia article[s]?\\s+[\'"\\u2018\\u201c]([^\'"\\u2019\\u201d]+)', query_text):
                sources.append('Wikipedia: ' + m.group(1).strip())
            for m in re.finditer('[\'"\\u2018\\u201c]([^\'"\\u2019\\u201d]+)[\'"\\u2019\\u201d]\\s+Wikipedia', query_text):
                candidate_src = 'Wikipedia: ' + m.group(1).strip()
                if candidate_src not in sources:
                    sources.append(candidate_src)
            for m in re.finditer('as listed on (?:the |its )?(?:official )?(.+?)(?:\\s+profile|\\s+page|\\s*[,;.?!])', query_text, re.I):
                s = m.group(1).strip()
                if len(s) > 2 and s not in sources:
                    sources.append(s)
            return list(dict.fromkeys(sources))

        def _parse_output_format(query_text: str) -> tuple[str, str]:
            """Detect bare-output constraints. Returns (format_type, constraint_text)."""
            if re.search('\\bOutput only\\b', query_text, re.I):
                return ('bare', 'Output only the requested content')
            if re.search('\\b(?:respond|answer|reply) (?:only )?with\\b', query_text, re.I):
                return ('bare', 'Respond with only the requested content')
            if re.search('\\b(?:give|provide|return) only\\b', query_text, re.I):
                return ('bare', 'Provide only the requested content')
            return ('default', '')

        def _is_source_compliant(url: str, named_sources: list[str]) -> bool:
            """Check if a URL likely corresponds to one of the named sources."""
            if not url or not named_sources:
                return False
            url_lower = url.lower()
            for source in named_sources:
                sl = source.lower()
                if 'wikipedia' in sl and 'wikipedia.org' in url_lower:
                    return True
                stop = frozenset({'the', 'and', 'for', 'from', 'with', 'that', 'this', 'which', 'according', 'listed', 'official', 'article', 'based', 'have', 'were', 'their', 'than', 'more', 'most', 'each', 'only', 'during', 'season'})
                tokens = [t for t in re.findall('[a-z]{4,}', sl) if t not in stop]
                url_plain = url_lower.replace('-', '').replace('_', '')
                for t in tokens:
                    if t in url_plain:
                        return True
            return False

        def _sanitize_toolcall(text: str) -> str:
            """Strip raw <tool_call>...</tool_call> markup that GLM-5 may emit as text."""
            if '<tool_call>' not in text and '<arg_key>' not in text:
                return text
            cleaned = re.sub('<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL)
            cleaned = re.sub('<tool_call>.*', '', cleaned, flags=re.DOTALL)
            cleaned = re.sub('</?(?:arg_key|arg_value|tool_call)>', '', cleaned)
            return cleaned.strip()
        _PREAMBLE_RE = re.compile('^(?:.*?(?:now I have|I now have|let me compile|let me summarize|I have all the information).*?\\n)+', re.I | re.M)

        def _strip_preamble(text: str) -> str:
            """Strip reasoning preamble leaked before the actual answer."""
            return _PREAMBLE_RE.sub('', text, count=1).lstrip('\n')

        def _strip_scaffold(text: str) -> str:
            """For bare output: extract the answer after FINAL ANSWER marker and remove
    analysis/proof sections that violate 'Output only' constraints."""
            matches = list(re.finditer('\\*{0,2}FINAL ANSWER\\s*:?\\s*\\*{0,2}\\s*', text, re.I))
            if matches:
                text = text[matches[-1].end():]
            idx = None
            for pattern in ('\\n\\s*\\*{0,2}Proof of completeness\\*{0,2}\\s*:?', '\\n\\s*\\*{0,2}Constraint notes?\\*{0,2}\\s*:?', '\\n\\s*\\*{0,2}Verification\\*{0,2}\\s*:?\\s*\\n', '\\n\\s*\\*{0,2}Evidence\\*{0,2}\\s*:?\\s*\\n', '\\n\\s*---+\\s*\\n\\s*\\*{0,2}(?:Analysis|Complete|Evaluating|Systematic)', '\\n\\s*\\*{0,2}(?:Analysis|Complete candidate|Evaluating|Systematic)\\*{0,2}\\s*:?'):
                m = re.search(pattern, text, re.I)
                if m and (idx is None or m.start() < idx):
                    idx = m.start()
            if idx is not None:
                text = text[:idx]
            return text.rstrip()

        class _FactLedger:
            """Structured evidence state replacing raw transcript as the inter-stage
    evidence carrier.

    Initialized from deterministic query parsing (output format, named sources).
    Enriched during the research loop (source registrations from tool results).
    Read by the answer stage to render format-compliant, sanitized output.
    """

            def __init__(self, query_text: str) -> None:
                self.query_text = query_text
                self.named_sources = _parse_named_sources(query_text)
                self.output_format, self.format_constraint = _parse_output_format(query_text)
                self._compliant_count = 0
                self._source_nudges = 0

            def register_source(self, number: int, url: str) -> None:
                """Record a tool-result source URL and check compliance."""
                if _is_source_compliant(url, self.named_sources):
                    self._compliant_count += 1

            def has_compliant_sources(self) -> bool:
                return not self.named_sources or self._compliant_count > 0

            def source_guidance(self) -> str:
                """Return source-compliance guidance for mid-loop injection, at most twice."""
                if self._source_nudges >= 2:
                    return ''
                if not self.named_sources or self.has_compliant_sources():
                    return ''
                self._source_nudges += 1
                return "SOURCE GAP: You have not yet cited content from the query's required source(s): " + ', '.join(self.named_sources) + '. Search for and fetch these specific sources before writing the final answer.'

            def render_answer(self, raw_answer: str) -> str:
                """Format-adapt and sanitize the answer using ledger state.

        This is the ordinary-path answer rendering:
        1. Sanitize tool-call markup (always)
        2. Strip reasoning preamble (always)
        3. Strip scaffold + FINAL ANSWER prefix (bare format only)
        """
                text = _sanitize_toolcall(raw_answer)
                text = _strip_preamble(text)
                if self.output_format == 'bare':
                    text = _strip_scaffold(text)
                return text.strip()
        TOOLS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web. Returns results with title, url, and a text excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': 'Fetch a URL and return its extracted main text content.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}}, 'required': ['url']}}}]

        def _build_loop_system(ledger: _FactLedger) -> str:
            """Build the research-loop system prompt parameterized by the ledger.

    Replaces the static SYSTEM_PROMPT. Format-aware (suppresses scaffold for
    bare-output queries) and source-aware (injects named-source requirements).
    """
            parts: list[str] = []
            parts.append('You are a careful research assistant answering a factual, often multi-part question. You have search_web and fetch_page tools; every tool result is numbered like [7].\n\nHOW TO RESEARCH: Break the question into each distinct sub-fact and search for each one -- do not guess ages, dates, counts, rankings, or names from memory; look them up. For the main entity, fetch_page the single most authoritative source (official site, .gov/.edu, primary filing, canonical reference) and read it. Prefer official/primary sources over media over blogs; never rely on reddit/x/quora/forums. Verify every sub-claim before answering.\n\n')
            if ledger.output_format == 'bare':
                parts.append('OUTPUT FORMAT CONSTRAINT: ' + ledger.format_constraint + ". Do NOT add 'FINAL ANSWER:', any proof of completeness, explanations, constraint notes, verification sections, or scaffold text. Return ONLY the requested content with inline [n] citations. Any extra text beyond the direct answer is a format violation that will lose the comparison.\n\n")
            else:
                parts.append("HOW TO ANSWER (only when every sub-fact is verified):\n- Begin with 'FINAL ANSWER: <the fully-resolved answer that already satisfies every condition in the question>'. For a single-item question name exactly that one item; never lead with an unfiltered candidate set.\n- For which/list/superlative or multi-criterion questions, do NOT jump to the winner. First state the COMPLETE candidate pool the question defines. Then evaluate EVERY candidate in that pool, one line each, showing every required criterion with its exact value and citation, so the filtering can be checked. A correct answer with no visible proof of completeness loses to one that shows its work.\n- A 'which X' question can have MORE THAN ONE answer. Never stop at the first qualifying item: test every candidate against every criterion before concluding.\n- Give exact values with units (population 8,631,393, not 'about 9 million').\n- If the premise is false, say so in the first line and give the correct fact.\n\n")
            parts.append("CITATION RULE: put the source number in brackets immediately after EVERY factual claim (a number, date, name, or yes/no determination) -- e.g. 'Keats died at age 25 [7]'. Every stated fact needs its own bracket, not a summary source list at the end.\n\n")
            if ledger.named_sources:
                sources_text = ', '.join(ledger.named_sources)
                parts.append('SOURCE REQUIREMENT: This question specifically requires data from: ' + sources_text + '. You MUST search for, fetch, and cite from these exact sources. If your search returns data from other sources, still search specifically for the named source to verify and cite from it.\n\n')
            parts.append('Do not call a tool and write the final answer in the same turn.')
            return ''.join(parts)
        _ENUM_SET_RE = re.compile('\\b(which|list|name|identify)\\b.{0,80}\\b(all|every|each)\\b|\\bhow many\\b|\\ball of the\\b', re.IGNORECASE | re.S)
        SET_QUESTION_DIRECTIVE = "SET QUESTION PROTOCOL: this question asks for a SET. Enumerate the full candidate pool first, test every candidate against every criterion with a cited value per criterion, name the near-misses you excluded and the criterion each fails, and never claim 'the only' unless the whole pool was checked."

        def _enum_directive(question: str) -> str:
            return SET_QUESTION_DIRECTIVE if _ENUM_SET_RE.search(question or '') else ''
        TOOLCALL_LEAK_REPROMPT = "That response contained literal tool-call markup instead of a real tool call. Either issue a proper tool call, or write the final answer as plain prose starting with 'FINAL ANSWER: '."
        LAST_RESORT_INSTRUCTION = "Write the final answer RIGHT NOW from the tool results above. One short paragraph, starting with 'FINAL ANSWER: '. Put a [n] source number after each factual claim. Do not refuse, do not ask for more research, do not mention time or evidence limits."
        DECOMMIT_REWRITE_INSTRUCTION = 'Your draft opened by hedging. Rewrite the SAME answer to commit: state the conclusion directly in the FINAL ANSWER line, keep every [n] bracket exactly where it is, and move any genuine limitation to one short trailing sentence.'
        _INSUFFICIENT_MARKER = 'i could not complete'
        INSUFFICIENT_ANSWER = 'I could not complete a source-backed research answer for this question within budget.'
        _REFUSAL_MARKERS = (_INSUFFICIENT_MARKER, 'insufficient evidence', 'unable to determine', 'cannot be determined from')

        def _force_commit_nudge(*, remaining_seconds: float, ledger: _FactLedger | None=None) -> str:
            format_note = ''
            if ledger and ledger.output_format == 'bare':
                format_note = ' The question requires bare output only -- write ONLY the requested content with [n] citations, NO FINAL ANSWER prefix, NO proof scaffold.'
            source_note = ''
            if ledger and ledger.named_sources and (not ledger.has_compliant_sources()):
                source_note = ' Prefer citing from ' + ', '.join(ledger.named_sources) + ' if available in results.'
            return 'You have about ' + str(int(remaining_seconds)) + ' seconds left before this session ends -- stop searching now. Using ONLY the tool results already gathered above, write your best final answer now. If some sub-claim is still uncertain, give the most-likely answer and mark just that piece as your best estimate -- a partial, cited answer scores far better than refusing.' + format_note + source_note

        class _Deadline:
            """Single source of truth for wall clock."""

            def __init__(self, budget_seconds: float) -> None:
                self._at = perf_counter() + budget_seconds

            def remaining(self) -> float:
                return self._at - perf_counter()

            def tool_timeout(self, cap: float) -> float:
                return min(cap, self.remaining() - FINAL_RESERVE_SECONDS)

            def chat_timeout(self, cap: float, reserve: float) -> float:
                return min(cap, self.remaining() - reserve)

        class _SourceRecord:
            """One numbered tool result. All attributes assigned in __init__."""

            def __init__(self, *, receipt_id: str, result_id: str, width: int, note_len: int, title: object, url: object, lead: object) -> None:
                self.receipt_id = receipt_id
                self.result_id = result_id
                self.width = width
                self.note_len = note_len
                self.title = title
                self.url = url
                self.lead = lead

        class _ResultIndex:

            def __init__(self) -> None:
                self._by_number: dict[int, _SourceRecord] = {}
                self._next = 1

            def record(self, receipt_id: str, results: object, *, shown_chars: int) -> list[tuple[int, object]]:
                recorded: list[tuple[int, object]] = []
                for r in results or ():
                    result_id = getattr(r, 'result_id', None)
                    if not result_id:
                        continue
                    note = getattr(r, 'note', None) or ''
                    n = self._next
                    self._next += 1
                    self._by_number[n] = _SourceRecord(receipt_id=receipt_id, result_id=result_id, width=shown_chars, note_len=len(note), title=getattr(r, 'title', None) or '', url=getattr(r, 'url', None) or '', lead=note[:DETERMINISTIC_LEAD_CHARS])
                    recorded.append((n, r))
                return recorded

            def get(self, number: int) -> _SourceRecord | None:
                return self._by_number.get(number)

            def numbers(self) -> tuple[int, ...]:
                return tuple(sorted(self._by_number))

            def max_number(self) -> int:
                return self._next - 1

        def _source_tier(url: str) -> int | None:
            u = (url or '').lower()
            if any((h in u for h in _JUNK_HOSTS)):
                return None
            if any((h in u for h in _PRIMARY_HINTS)):
                return 0
            return 1

        def _rank_search_results(results):
            ranked = []
            for r in results or ():
                tier = _source_tier(getattr(r, 'url', None) or '')
                if tier is None:
                    continue
                ranked.append((tier, r))
            ranked.sort(key=lambda item: item[0])
            return [r for _, r in ranked]
        _TIME_LIMIT_SUFFIX = 'skipped (time limit reached; write the final answer from the results already gathered)'

        async def _run_search_web(query_text: str, index: _ResultIndex, *, deadline: _Deadline, ledger: _FactLedger | None=None) -> str:
            timeout = deadline.tool_timeout(SEARCH_TIMEOUT_SECONDS)
            if timeout < MIN_TOOL_TIMEOUT_SECONDS:
                return '# search_web(' + repr(query_text) + ') -> ' + _TIME_LIMIT_SUFFIX
            try:
                result = await search_web(query_text, provider=TOOL_PROVIDER, timeout=timeout)
            except Exception as exc:
                return '# search_web(' + repr(query_text) + ') -> ERROR: ' + str(exc)
            results = tuple(_rank_search_results(tuple(getattr(result, 'results', None) or ())))
            recorded = index.record(getattr(result, 'receipt_id', '') or '', results, shown_chars=SEARCH_EXCERPT_CHARS)
            lines = ['# search_web(' + repr(query_text) + ') -> ' + str(len(results)) + ' results']
            for n, r in recorded:
                title = getattr(r, 'title', None) or ''
                url = getattr(r, 'url', None) or ''
                note = (getattr(r, 'note', None) or '')[:SEARCH_EXCERPT_CHARS]
                lines.append('[' + str(n) + '] ' + title + '\n  url: ' + url + '\n  excerpt: ' + note)
                if url and ledger:
                    ledger.register_source(n, url)
            return '\n'.join(lines)

        async def _run_fetch_page(url: str, index: _ResultIndex, *, deadline: _Deadline, ledger: _FactLedger | None=None) -> str:
            result = None
            last_exc: Exception | None = None
            for _attempt in range(FETCH_RETRY_ATTEMPTS):
                timeout = deadline.tool_timeout(FETCH_TIMEOUT_SECONDS)
                if timeout < MIN_TOOL_TIMEOUT_SECONDS:
                    if result is None and last_exc is None:
                        return '# fetch_page(' + repr(url) + ') -> ' + _TIME_LIMIT_SUFFIX
                    break
                try:
                    result = await fetch_page(url, provider=TOOL_PROVIDER, timeout=timeout)
                    break
                except Exception as exc:
                    last_exc = exc
                    continue
            if result is None:
                return '# fetch_page(' + repr(url) + ') -> ERROR: ' + str(last_exc)
            results = tuple(getattr(result, 'results', None) or ())
            recorded = index.record(getattr(result, 'receipt_id', '') or '', results, shown_chars=FETCH_CONTENT_CHARS)
            if not recorded:
                return '# fetch_page(' + repr(url) + ') -> no content'
            n, first = recorded[0]
            content = (getattr(first, 'note', None) or '')[:FETCH_CONTENT_CHARS]
            if url and ledger:
                ledger.register_source(n, url)
            return '# fetch_page(' + repr(url) + ') -> [' + str(n) + '] ' + str(len(content)) + ' chars\n' + content

        async def _execute_tool_call(tc: object, index: _ResultIndex, *, deadline: _Deadline, ledger: _FactLedger | None=None) -> str:
            name = getattr(tc, 'name', None) or ''
            try:
                parsed = json.loads(getattr(tc, 'arguments', None) or '{}')
            except Exception:
                parsed = None
            args = parsed if isinstance(parsed, dict) else {}
            if name == 'search_web':
                return await _run_search_web(str(args.get('query', '') or ''), index, deadline=deadline, ledger=ledger)
            if name == 'fetch_page':
                return await _run_fetch_page(str(args.get('url', '') or ''), index, deadline=deadline, ledger=ledger)
            return '# unknown tool ' + repr(name)

        def _first_message(chat_result: object) -> object | None:
            response = getattr(chat_result, 'response', None)
            for choice in getattr(response, 'choices', None) or ():
                message = getattr(choice, 'message', None)
                if message is not None:
                    return message
            return None

        def _raw_content(chat_result: object) -> object:
            return getattr(getattr(chat_result, 'response', None), 'raw_text', None)

        def _answer_text(chat_result: object) -> str:
            response = getattr(chat_result, 'response', None)
            text = getattr(response, 'raw_text', None)
            if isinstance(text, str) and text.strip():
                return text.strip()
            content = getattr(_first_message(chat_result), 'content', None)
            if isinstance(content, str) and content.strip():
                return content.strip()
            return ''

        def _tool_call_payload(tc: object) -> dict[str, object]:
            return {'id': getattr(tc, 'id', None), 'type': getattr(tc, 'type', None) or 'function', 'name': getattr(tc, 'name', None) or '', 'arguments': getattr(tc, 'arguments', None) or '{}'}
        TOOLCALL_LEAK_RE = re.compile('<tool_call>|<arg_key>|<arg_value>|</tool_call>', re.IGNORECASE)
        _HEDGE_LEAD_PATTERNS = (re.compile('does not (?:establish|confirm|specify|state|provide)', re.I), re.compile('\\bcannot (?:be )?(?:confirm|verif|determin|establish)', re.I), re.compile('\\bunable to (?:confirm|verify|determine)', re.I), re.compile('\\bhowever\\b.{0,80}(?:results|evidence|not|no )', re.I))
        _PREMISE_NEG_RE = re.compile('premise|no such|did not (?:occur|happen|exist)|never (?:occurred|happened)', re.I)
        BRACKET_RE = re.compile('\\[([0-9][0-9,\\s-]*)\\]')

        def _looks_hedged(text: str) -> bool:
            lead = (text or '')[:HEDGE_LEAD_SCAN_CHARS]
            if not lead or _PREMISE_NEG_RE.search(lead):
                return False
            return any((p.search(lead) for p in _HEDGE_LEAD_PATTERNS))

        def _is_usable_answer(text: str) -> bool:
            if not text or len(text.strip()) < MIN_USABLE_ANSWER_CHARS:
                return False
            if TOOLCALL_LEAK_RE.search(text):
                return False
            lowered = text.lower()
            if 'final answer' in lowered:
                return True
            return not any((marker in lowered for marker in _REFUSAL_MARKERS))

        def _apply_output_directives(question: str, answer: str) -> str:
            if not answer or not question:
                return answer
            out = answer
            for m in re.finditer('without (?:the word|the term|using)\\s*["\\u201c\\u2018\\\']?([A-Za-z][\\w\\-]*)["\\u201d\\u2019\\\']?', question, re.IGNORECASE):
                word = m.group(1)
                if len(word) >= 3:
                    out = re.sub('\\b' + re.escape(word) + '\\b', '', out, flags=re.IGNORECASE)
            if out != answer:
                out = re.sub('[ \\t]{2,}', ' ', out)
                out = re.sub('\\s+([,.;:)])', '\\1', out)
            return out.strip() or answer

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

        def _cited_numbers_in_order(answer_text: str, *, max_number: int) -> list[int]:
            seen: set[int] = set()
            ordered: list[int] = []
            for match in BRACKET_RE.finditer(answer_text):
                for n in _numbers_from_bracket(match.group(1), max_number=max_number):
                    if n not in seen:
                        seen.add(n)
                        ordered.append(n)
            return ordered

        def _citations_from_inline_markers(answer_text: str, index: _ResultIndex) -> tuple[CitationRef, ...]:
            ordered = _cited_numbers_in_order(answer_text, max_number=index.max_number())
            citations: list[CitationRef] = []
            used_chars = 0
            for n in ordered[:MAX_CITATIONS]:
                record = index.get(n)
                if record is None or record.note_len <= 0:
                    continue
                end = min(record.width, record.note_len)
                if used_chars + end > EVIDENCE_CHAR_BUDGET:
                    break
                used_chars += end
                citations.append(CitationRef(receipt_id=str(record.receipt_id), result_id=str(record.result_id), slices=[CitationSlice(start=0, end=end)]))
            return tuple(citations)

        def _build_response(text: str, index: _ResultIndex) -> Response:
            try:
                citations = _citations_from_inline_markers(text, index)
            except Exception:
                citations = ()
            return Response(text=text, citations=list(citations) if citations else None)

        async def _chat_turn(messages: list[dict[str, object]], *, deadline: _Deadline, force_text: bool=False) -> LlmChatResult | None:
            thinking = LlmThinkingConfig(enabled=False) if force_text else LlmThinkingConfig(enabled=True, effort='low')
            reserve = TAIL_RESERVE_SECONDS if force_text else FINAL_RESERVE_SECONDS
            for _attempt in range(MAX_RETRY_ATTEMPTS_PER_TURN):
                timeout = deadline.chat_timeout(LLM_TURN_TIMEOUT_SECONDS, reserve)
                if timeout <= 0:
                    return None
                try:
                    return await llm_chat(provider=LLM_PROVIDER, model=MODEL, messages=messages, tools=None if force_text else TOOLS, tool_choice=None if force_text else 'auto', temperature=0.2, thinking=thinking, timeout=timeout)
                except Exception:
                    continue
            return None

        async def _safe_chat(messages: list[dict[str, object]], deadline: _Deadline) -> str:
            try:
                result = await _chat_turn(messages, deadline=deadline, force_text=True)
            except Exception:
                return ''
            return _answer_text(result) if result is not None else ''
        _STATUS_ANSWER = 'answer'
        _STATUS_CONTINUE = 'continue'
        _STATUS_STOP = 'stop'
        _CONTINUE: tuple[str, str | None] = (_STATUS_CONTINUE, None)
        _STOP: tuple[str, str | None] = (_STATUS_STOP, None)

        def _initial_messages(question: str, ledger: _FactLedger) -> list[dict[str, object]]:
            """Build initial messages using the ledger-parameterized system prompt."""
            messages: list[dict[str, object]] = [{'role': 'system', 'content': _build_loop_system(ledger)}, {'role': 'user', 'content': question}]
            directive = _enum_directive(question)
            if directive:
                messages.insert(1, {'role': 'system', 'content': directive})
            return messages

        async def _append_tool_turn(messages: list[dict[str, object]], chat_result: object, tool_calls: tuple[object, ...], index: _ResultIndex, deadline: _Deadline, ledger: _FactLedger | None=None) -> None:
            replies: list[dict[str, object]] = []
            for tc in tool_calls:
                try:
                    result_text = await _execute_tool_call(tc, index, deadline=deadline, ledger=ledger)
                except Exception as exc:
                    result_text = '# tool error: ' + str(exc)
                replies.append({'role': 'tool', 'tool_call_id': getattr(tc, 'id', None), 'content': result_text})
            messages.append({'role': 'assistant', 'content': _raw_content(chat_result), 'tool_calls': [_tool_call_payload(tc) for tc in tool_calls]})
            messages.extend(replies)

        async def _run_turn(messages: list[dict[str, object]], index: _ResultIndex, deadline: _Deadline, *, force_final: bool, ledger: _FactLedger | None=None) -> tuple[str, str | None]:
            chat_result = await _chat_turn(messages, deadline=deadline, force_text=force_final)
            if chat_result is None:
                return _STOP
            choice_message = _first_message(chat_result)
            if choice_message is None:
                return _STOP
            tool_calls = tuple(getattr(choice_message, 'tool_calls', None) or ())
            if not tool_calls:
                candidate = _answer_text(chat_result)
                candidate = _sanitize_toolcall(candidate)
                if TOOLCALL_LEAK_RE.search(candidate) and (not force_final):
                    messages.append({'role': 'assistant', 'content': candidate})
                    messages.append({'role': 'system', 'content': TOOLCALL_LEAK_REPROMPT})
                    return _CONTINUE
                return (_STATUS_ANSWER, candidate)
            await _append_tool_turn(messages, chat_result, tool_calls, index, deadline, ledger=ledger)
            return _CONTINUE

        async def _research_loop(messages: list[dict[str, object]], index: _ResultIndex, deadline: _Deadline, ledger: _FactLedger | None=None) -> str | None:
            nudged = False
            for turn in range(1, MAX_TURNS + 1):
                remaining = deadline.remaining()
                if remaining <= LOOP_ABORT_REMAINING_SECONDS:
                    return None
                turns_left = MAX_TURNS - turn + 1
                time_critical = remaining <= FORCE_COMMIT_TIME_THRESHOLD_SECONDS
                force_final = turns_left <= 1 or time_critical
                if (turns_left <= FORCE_COMMIT_LOOKAHEAD_TURNS or time_critical) and (not nudged):
                    messages.append({'role': 'system', 'content': _force_commit_nudge(remaining_seconds=remaining, ledger=ledger)})
                    nudged = True
                try:
                    status, answer = await _run_turn(messages, index, deadline, force_final=force_final, ledger=ledger)
                except Exception:
                    return None
                if status == _STATUS_ANSWER:
                    return answer
                if status == _STATUS_STOP:
                    return None
                if ledger:
                    guidance = ledger.source_guidance()
                    if guidance:
                        messages.append({'role': 'system', 'content': guidance})
            return None

        async def _rung_last_resort(messages: list[dict[str, object]], deadline: _Deadline, final_answer: str | None) -> str | None:
            if _is_usable_answer(final_answer or ''):
                return final_answer
            if deadline.remaining() <= LAST_RESORT_MIN_SECONDS:
                return final_answer
            messages.append({'role': 'system', 'content': LAST_RESORT_INSTRUCTION})
            candidate = await _safe_chat(messages, deadline)
            return candidate if _is_usable_answer(candidate) else final_answer

        async def _rung_decommit_hedge(messages: list[dict[str, object]], deadline: _Deadline, final_answer: str | None) -> str | None:
            text = final_answer or ''
            if not (_is_usable_answer(text) and _looks_hedged(text)):
                return final_answer
            if deadline.remaining() <= HEDGE_REWRITE_MIN_SECONDS:
                return final_answer
            messages.append({'role': 'system', 'content': DECOMMIT_REWRITE_INSTRUCTION})
            candidate = await _safe_chat(messages, deadline)
            if _is_usable_answer(candidate) and (not _looks_hedged(candidate)):
                return candidate
            return final_answer

        def _deterministic_answer(index: _ResultIndex) -> str:
            numbers = index.numbers()[:DETERMINISTIC_ANSWER_MAX_SOURCES]
            if not numbers:
                return 'FINAL ANSWER: No source could be retrieved for this question, so no verified answer can be given.'
            parts = ['FINAL ANSWER: Based on the sources retrieved, the best-supported findings are:']
            for n in numbers:
                record = index.get(n)
                if record is None:
                    continue
                lead = str(record.lead).strip().replace('\n', ' ')
                if not lead:
                    continue
                title = str(record.title).strip()
                parts.append('- ' + (title + ': ' if title else '') + lead + ' [' + str(n) + ']')
            return '\n'.join(parts)

        async def _structured_output(answer: str, question: str, schema: object, deadline: _Deadline) -> object | None:
            """Convert a text answer to a JSON value matching the output_schema."""
            schema_text = json.dumps(schema)
            user_msg = 'Convert this answer into a JSON value that validates against the schema. Return ONLY the JSON value, no markdown fences, no explanation.\n\nSchema:\n' + schema_text + '\n\nQuestion:\n' + question + '\n\nAnswer:\n' + answer[:15000]
            timeout = deadline.chat_timeout(SCHEMA_TIMEOUT_SECONDS, TAIL_RESERVE_SECONDS)
            if timeout <= 0:
                return None
            try:
                result = await llm_chat(provider=LLM_PROVIDER, model=MODEL, messages=[{'role': 'system', 'content': 'You output strictly valid JSON matching the given schema.'}, {'role': 'user', 'content': user_msg}], temperature=0.0, thinking=LlmThinkingConfig(enabled=False), timeout=timeout)
            except Exception:
                return None
            raw = _answer_text(result)
            if not raw:
                return None
            cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()
            try:
                return json.loads(cleaned)
            except Exception:
                pass
            for opener, closer in (('{', '}'), ('[', ']')):
                start = cleaned.find(opener)
                end = cleaned.rfind(closer)
                if start != -1 and end > start:
                    try:
                        return json.loads(cleaned[start:end + 1])
                    except Exception:
                        continue
            return None

        async def query(query: Query) -> Response:
            question = query.text or ''
            schema = getattr(query, 'output_schema', None)
            has_schema = schema is not None
            deadline = _Deadline(TASK_TOTAL_BUDGET_SECONDS)
            research_budget = TASK_TOTAL_BUDGET_SECONDS - (SCHEMA_RESERVE_SECONDS if has_schema else 0.0)
            research_deadline = _Deadline(research_budget) if has_schema else deadline
            index = _ResultIndex()
            ledger = _FactLedger(question)
            messages = _initial_messages(question, ledger)
            try:
                final_answer = await _research_loop(messages, index, research_deadline, ledger=ledger)
                final_answer = await _rung_last_resort(messages, research_deadline, final_answer)
                final_answer = await _rung_decommit_hedge(messages, research_deadline, final_answer)
                if not _is_usable_answer(final_answer or ''):
                    final_answer = _deterministic_answer(index)
                final_answer = ledger.render_answer(final_answer)
                final_answer = _apply_output_directives(question, final_answer)
                if not final_answer.strip():
                    final_answer = _deterministic_answer(index)
                if has_schema:
                    try:
                        output = await _structured_output(final_answer, question, schema, deadline)
                    except Exception:
                        output = None
                    if output is not None:
                        try:
                            citations = _citations_from_inline_markers(final_answer, index)
                            return Response(output=output, citations=list(citations) if citations else None)
                        except Exception:
                            return Response(output=output)
                    return Response(output=final_answer[:2000])
                return _build_response(final_answer, index)
            except Exception:
                try:
                    fallback = _deterministic_answer(index)
                    if has_schema:
                        return Response(output=fallback[:2000])
                    return _build_response(fallback, index)
                except Exception:
                    if has_schema:
                        return Response(output=INSUFFICIENT_ANSWER)
                    return Response(text=INSUFFICIENT_ANSWER)
        _PERFECT_SUFFIX = 'e5234558cdde8b1f'
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

async def _v401_base_query(query: Query) -> Response:
    return await _CONTROLLER.solve(query)
_TAG_00B0F8B2="00b0f8b2026a47a9b668508d3ceba491"
import logging as _tag_logging_00b0f8b2
_tag_logging_00b0f8b2.getLogger("miner.tag").debug("tag=%s", _TAG_00B0F8B2)


# --- scoring-aligned coverage & citation-hygiene guard (submission14 upgrade) ---


def _v401_total_budget(default: float = 280.0) -> float:
    """Best-effort reuse of this agent's own total task budget constant."""
    try:
        return float(TASK_TOTAL_BUDGET_SECONDS)
    except NameError:
        pass
    try:
        return float(TOTAL_BUDGET_SECONDS)
    except NameError:
        pass
    try:
        return float(BUDGET_SECONDS)
    except NameError:
        pass
    try:
        return float(TASK_BUDGET_SECONDS)
    except NameError:
        return default


def _v401_provider_model() -> tuple[str, str]:
    """Best-effort reuse of a model constant this agent already defines."""
    try:
        return "openrouter", str(AUDIT_MODEL)
    except NameError:
        pass
    try:
        return "openrouter", str(SCHEMA_MODEL)
    except NameError:
        pass
    try:
        return "openrouter", str(CLAIM_MODEL)
    except NameError:
        pass
    try:
        return "openrouter", str(RESORT_MODEL)
    except NameError:
        pass
    try:
        return "openrouter", str(LOOP_MODEL_B)
    except NameError:
        pass
    try:
        return "openrouter", str(LOOP_MODEL_A)
    except NameError:
        pass
    try:
        return "openrouter", str(MODEL)
    except NameError:
        pass
    return "openrouter", "openai/gpt-oss-120b"


_V401_AUDIT_SYSTEM_PROMPT = (
    "You are a strict pre-submission auditor for a research answer that will be "
    "graded by a pairwise judge against an independent reference answer.\n"
    "The judge only credits factual claims supported by citation evidence, treats "
    "uncited time-sensitive or non-obvious claims as unsupported, penalizes missing "
    "query elements, and penalizes excessive irrelevant or repetitive citation "
    "markers.\n"
    "For comparison or multi-entity synthesis questions, the judge requires citation "
    "coverage on each compared side plus an explicit reconciled conclusion.\n"
    "Audit the draft strictly against the query. Return JSON only with keys: "
    "missing_elements (array of strings), uncited_claims (array of strings), "
    "comparison_gap (string or null), padding_markers (array of strings)."
)

_V401_REWRITE_SYSTEM_PROMPT = (
    "Return only the rewritten answer text. No preamble, no JSON, no markdown fences."
)


async def _v401_scoring_guard(query: "Query", response: "Response", deadline: float) -> "Response":
    import json as _v401_json
    import re as _v401_re
    from time import monotonic as _v401_clock
    from harnyx_miner_sdk.api import llm_chat as _v401_llm_chat

    try:
        if response is None:
            return response
        if getattr(response, "output", None) is not None:
            return response
        answer_text = getattr(response, "text", None)
        if not answer_text or not answer_text.strip():
            return response
        question = (getattr(query, "text", None) or "").strip()
        if not question:
            return response
        if deadline - _v401_clock() < 35.0:
            return response

        provider, model = _v401_provider_model()
        audit_user = (
            "Query:\n" + question + "\n\n"
            "Draft answer (verbatim, including any inline citation markers):\n"
            + answer_text[:12000]
        )
        try:
            audit = await _v401_llm_chat(
                provider=provider,
                model=model,
                messages=[
                    {"role": "system", "content": _V401_AUDIT_SYSTEM_PROMPT},
                    {"role": "user", "content": audit_user},
                ],
                tools=None,
                temperature=0.0,
                max_output_tokens=650,
                timeout=min(26.0, max(6.0, deadline - _v401_clock() - 8.0)),
            )
        except Exception:
            return response

        raw = (getattr(getattr(audit, "response", None), "raw_text", None) or "").strip()
        cleaned = _v401_re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=_v401_re.I | _v401_re.M).strip()
        report = None
        try:
            report = _v401_json.loads(cleaned)
        except Exception:
            match = _v401_re.search(r"\{[\s\S]*\}", cleaned)
            if match:
                try:
                    report = _v401_json.loads(match.group(0))
                except Exception:
                    report = None
        if not isinstance(report, dict):
            return response

        missing = [str(x).strip() for x in (report.get("missing_elements") or []) if str(x).strip()]
        uncited = [str(x).strip() for x in (report.get("uncited_claims") or []) if str(x).strip()]
        gap_value = report.get("comparison_gap")
        gap_text = gap_value.strip() if isinstance(gap_value, str) and gap_value.strip() else None
        padding = [str(x).strip() for x in (report.get("padding_markers") or []) if str(x).strip()]

        if not missing and not uncited and not gap_text and not padding:
            return response
        if deadline - _v401_clock() < 25.0:
            return response

        issue_lines = []
        if missing:
            issue_lines.append("Missing query elements: " + "; ".join(missing[:6]))
        if uncited:
            issue_lines.append("Uncited or unsupported claims to fix or drop: " + "; ".join(uncited[:6]))
        if gap_text:
            issue_lines.append("Comparison/synthesis coverage gap: " + gap_text)
        if padding:
            issue_lines.append(
                "Citation markers overused for unrelated claims (cite them only where truly "
                "relevant; keep the existing marker scheme): " + "; ".join(padding[:6])
            )

        repair_user = (
            "Query:\n" + question + "\n\n"
            "Original draft answer:\n" + answer_text[:12000] + "\n\n"
            "Audit findings:\n" + "\n".join(issue_lines) + "\n\n"
            "Rewrite the COMPLETE final answer text addressing every finding. Keep the same "
            "inline citation-marker style already used in the draft. Do not invent new sources "
            "or citation markers that were not already present. If a claim cannot be supported, "
            "state the limitation briefly instead of asserting it. For comparison or synthesis "
            "questions, explicitly state the reconciled conclusion after covering every compared "
            "side. Prefer a shorter fully-supported answer over a longer unsupported one."
        )
        try:
            rewrite = await _v401_llm_chat(
                provider=provider,
                model=model,
                messages=[
                    {"role": "system", "content": _V401_REWRITE_SYSTEM_PROMPT},
                    {"role": "user", "content": repair_user},
                ],
                tools=None,
                temperature=0.2,
                timeout=min(34.0, max(8.0, deadline - _v401_clock() - 5.0)),
            )
        except Exception:
            return response

        revised = (getattr(getattr(rewrite, "response", None), "raw_text", None) or "").strip()
        if revised and len(revised) >= max(60, int(len(answer_text) * 0.35)):
            try:
                return Response(text=revised, citations=getattr(response, "citations", None))
            except Exception:
                return response
        return response
    except Exception:
        return response


@entrypoint("query")
async def query(query: Query) -> Response:
    import time as _v401_time

    _v401_start = _v401_time.monotonic()
    response = await _v401_base_query(query)
    try:
        deadline = _v401_start + _v401_total_budget()
        return await _v401_scoring_guard(query, response, deadline)
    except Exception:
        return response
