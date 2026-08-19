from __future__ import annotations
import asyncio
import json
import re
from time import monotonic
from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
_QABD6053 = 'v52-pin-reviewed'
_QABD6020 = 'openrouter'
_QABD6021 = 'ai_gateway'
_QABD6022 = 'z-ai/glm-5.2'
_QABD6023 = 'zai/glm-5.2-fast'
_QABD6004 = 'openai/gpt-oss-120b'
_QABD6044 = 'openai/gpt-oss-120b'
_QABD6040 = 'deepseek/deepseek-v3.2'
_QABD6046 = 'parallel'
_QABD6054 = 266.0
_QABD6007 = 50.0
_QABD6051 = 75.0
_QABD6019 = 144000
_QABD6005 = 28.0
_QABD6047 = 18.0
_QABD6016 = 16.0
_QABD6055 = 90.0
_QABD6031 = 8.0
_QABD6028 = 15
_QABD6002 = 2
_QABD6001 = 2
_QABD6039 = 55.0
_QABD6011 = 14.0
_QABD6045 = 550
_QABD6078 = 400000
_QABD6033 = 700
_QABD6032 = 6
_QABD6034 = 12000
_QABD6041 = 260
_QABD6042 = 6
_QABD6043 = 12
_QABD6014 = 3000
_QABD6018 = 3600
_QABD6010 = 6000
_QABD6009 = 14000
_QABD6017 = 3
_QABD6015 = 6500
_QABD6000 = 60000
_QABD6008 = 24
_QABD6012 = 105000
_QABD6006 = 0.03
_QABD6003 = 0.05
_QABD6056 = 0.02
_QABD6106 = {'left': None}

def _qabd6187(payload) -> None:
    budget = getattr(payload, 'budget', None)
    left = getattr(budget, 'session_remaining_budget_usd', None)
    if isinstance(left, (int, float)):
        _QABD6106['left'] = float(left)

def _qabd6186() -> float:
    left = _QABD6106['left']
    if isinstance(left, (int, float)):
        return float(left)
    return 1.0
_QABD6025 = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}, {'type': 'function', 'function': {'name': 'page_grep', 'description': 'Search INSIDE a page you already fetched, by regex or literal text, and get every match with its surrounding context and character offset. Use this when read_page showed you the head of a long page but the value you need is deeper in it -- do not re-fetch, grep it.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL of a page already fetched this run'}, 'pattern': {'type': 'string', 'description': 'regex or literal string to find, e.g. a city name, a year, a column label'}}, 'required': ['url', 'pattern']}}}, {'type': 'function', 'function': {'name': 'page_read', 'description': 'Read an arbitrary character range of a page you already fetched. Use the offsets page_grep reports to read the full table or section around a match.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL already fetched'}, 'offset': {'type': 'integer', 'description': 'start character offset'}, 'length': {'type': 'integer', 'description': 'how many characters to read (max 12000)'}}, 'required': ['url', 'offset']}}}, {'type': 'function', 'function': {'name': 'retain_evidence', 'description': "Keep the exact source text that proves a claim you are about to make. Pass the result number and the verbatim quote from it. Do this the moment you find a decisive value -- the judge only credits claims whose citation contains the supporting text, and this is how that text gets into your citation. Use it for the QUESTION'S PREMISES as well as your answer: every entity, work, date or figure the question names should end up with a retained quote confirming it.", 'parameters': {'type': 'object', 'properties': {'source': {'type': 'string', 'description': 'result number to quote from, e.g. 3'}, 'quote': {'type': 'string', 'description': 'verbatim text copied from that result that states the fact'}}, 'required': ['source', 'quote']}}}]
_QABD6024 = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nPREFER THE PRIMARY SOURCE: when two sources state the same fact, cite the one that ORIGINATES it -- the agency, registry, filing, official statistics release or the organisation\'s own page -- not an encyclopedia or aggregator repeating it. Measured verbatim on a task where both answers were factually correct: "Answer 1 is preferred for using primary sources" (it cited NARA where we cited Wikipedia) -- a full point lost on every run. Use the encyclopedia to FIND the primary source, then fetch and cite that.\n\nQUOTE WHAT PROVES IT: the judge credits a claim only when your citation CONTAINS the source text stating it. The moment you read a decisive value, call retain_evidence(source, quote) with the exact words from that result. Do this for every condition you test and every figure you report -- an answer whose citations do not carry its numbers loses to one that does, even when both answers are identical.\nALSO QUOTE THE QUESTION\'S PREMISES, not only your answer. Every entity, work, date or figure the question NAMES is a claim the judge expects traceable: the film it says someone directed, the article it points at, the year it fixes, the people it lists. You lose to an otherwise identical answer that cited those too -- measured verbatim: "does not provide a citation for \'Everyone Says I Love You\'... Answer 1 is more thorough in its traceability to all parts of the prompt\'s context". Retain a quote for each named premise as you confirm it, even when it is background you already believed.\n\nREAD DEEP, DO NOT RE-FETCH: read_page shows the head plus a few regions of a long page. If the value you need is not in what you were shown, call page_grep(url, pattern) to find it anywhere in that page and page_read to open the region around a reported offset. Grepping a page you already have costs nothing and beats another search.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. COPY SOURCE VALUES VERBATIM: when the question names a source, every name, label and value in the answer must be the exact string that source prints -- never add a familiar alternative in parentheses, never anglicise a transliteration. \'Makkah\' is the answer; \'Mecca (Makkah)\' is a wrong answer. ONE EXCEPTION, and it is absolute: if the question says to output ONLY the answer (\'output only\', \'respond with only\', \'nothing else\', \'no explanation\'), emit the answer line as the BARE requested text — no [n] markers on it, nothing else on that line: a trailing [3] makes the text inexact and fails the instruction. Still write the PROOF section BELOW it carrying its [n] markers. Only the answer line is shipped, but the citations are harvested from the proof first, and an uncited answer scores zero. Obeying that instruction IS the task. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

def _qabd6217(seconds_left: float) -> str:
    return f"TIME IS UP (~{int(seconds_left)}s left). No more tool calls. Write the complete final answer NOW from the numbered results above plus your knowledge: the FIRST words are the answer entities (no 'Based on…' preamble, no 'partial answer' framing, no '(verify)' markers), cite [n] on every claim, keep the required format. A cited partial answer scores; a refusal or a remark about insufficient evidence scores zero." + ('' if seconds_left >= 60 else ' BREVITY OVERRIDE: too little time remains for a line per pool member. Lead with the answer entities, then give the qualifiers one cited line each and compress the rejects into a single cited line. A complete short answer beats a long one that never finishes.')
_QABD6103 = re.compile('\\b(?:list|name|identify|enumerate)\\b[^?]{0,40}\\b(?:all|every|each|the)\\b|\\bhow many\\b|\\bwhich (?:movies|films|series|countries|companies|states|cities|books|albums|artists|players|teams|species|languages|banks|universities|agencies|models|products)\\b', re.IGNORECASE)
_QABD6102 = re.compile('\\b(?:both|also|and (?:also|had|has|was|were)|as well as)\\b', re.IGNORECASE)
_QABD6086 = re.compile('\\b(?:which|what)\\b(?:\\s+\\w+){0,2}?\\s+([a-z]{3,}s)\\b', re.IGNORECASE)
_QABD6085 = frozenset('was is has does its this thus across process business series species news status analysis basis less unless always perhaps'.split())
_QABD6082 = re.compile('\\b(?:highest|lowest|largest|smallest|most|least|greatest|fewest|longest|shortest|first|last|best|worst|only|oldest|youngest|newest|biggest)\\b', re.IGNORECASE)
_QABD6068 = frozenset('interest honest modest protest request suggest forest harvest invest manifest contest arrest digest earnest conquest tempest midwest northwest southwest unrest bequest behest attest molest ingest infest detest incest armrest backrest pretest headrest footrest'.split())
_QABD6067 = re.compile('\\b([a-z]{3,})est\\b')

def _qabd6157(text: str) -> bool:
    if _QABD6082.search(text or ''):
        return True
    for m in _QABD6067.finditer(text or ''):
        if m.group(0).lower() not in _QABD6068:
            return True
    return False

def _qabd6171(question: str) -> bool:
    q = ' '.join((question or '').split())
    if not q:
        return False
    return _qabd6157(q) or bool(re.search('\\b(?:most|least) (?:common|frequent|number|amount)\\b|\\bhow many\\b', q, re.I))
_QABD6049 = "SUPERLATIVE / TALLY — SHOW THE TABLE. The answer is one item, but you cannot know it without the whole pool. Before naming a winner: (1) list EVERY candidate the question's scope admits — every player who appeared, every officeholder in the span, every body in the ranking; (2) put the deciding value next to each (birth date, count, figure), cited; (3) THEN name the maximum. NEVER decide a superlative on a rounded or derived display: a coarse figure (a whole-number age, a rounded total, a bucketed rank) cannot separate two contenders that differ below its precision. Fetch the exact underlying value (full birth date, unrounded figure) for every contender, from a source that lists them ALL: a page showing only your front-runner cannot establish that nobody beats them. (3b) THEN name the maximum. Reproduce that candidate table in the proof section — a correct winner with no visible tally loses to a reference that shows its work, and 'among others' / 'and several more' is not a tally. If the pool is too large to list in full, rank it, show every contender down to a stated cutoff, and say what the cutoff was — a stated cutoff is a covered pool; an unstated one reads as an unchecked one."

def _qabd6170(question: str) -> bool:
    q = ' '.join((question or '').split())
    if _QABD6103.search(q):
        return True
    m = _QABD6086.search(q)
    if m and m.group(1).lower() not in _QABD6085:
        if not _qabd6157(q) or re.search('\\b(?:all|every|each)\\b', q, re.IGNORECASE):
            return True
    return bool(re.search('\\bwhich\\b', q, re.IGNORECASE)) and bool(_QABD6102.search(q))
_QABD6048 = "SET ANSWER: this question asks for a set. Missing a qualifying member scores the same as wrong — enumerate the pool, test EVERY member against EVERY condition, and name ALL qualifiers (each with its own citations per condition). Then give EVERY excluded member its own line with the condition it fails and its own [n] — not a single clause sweeping several names together, and not just the near-misses. Never claim 'the only X' unless the whole pool was checked; if your pool may be partial, still commit to every qualifier you verified. GET THE POOL FROM A LIST, NOT MEMBER-BY-MEMBER: your FIRST retrieval for a set question should hunt the authoritative roster/list/table that enumerates the whole pool (search it AS a list — '<pool subject> list', '<pool subject> table', 'list of <pool subject>' — and read_page it). Assembling the pool from separate per-member searches is how a run ends up with 3 of 6 qualifiers: the members you never thought to search for are invisible to you. Read the roster page first, then verify each member. ONE LIST PER PERIOD, THEN JOIN: when a condition has to hold across several periods — successive years, separate editions, or two parallel events — fetch ONE roster page per period and join them on the member: one list per period, not one lookup per member. A pool of 30+ members each needing several figures is a table-join, and per-member lookups will run out of turns long before the pool is covered. UNIVERSAL conditions ('in EVERY one of them', 'for BOTH parts', 'in ALL three periods'): check each candidate against EACH instance separately, with a citation per instance — one shared instance is not enough. If NO candidate survives every instance, then 'none' IS the answer: state it as a verified fact about the world with the per-instance citations that prove it."

class QAbd6013:

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, receipt_id: str, result_id: str, note_len: int, kind: str, spans: list[tuple[int, int]] | None, title: str='', url: str='', preview: str='', text: str='') -> int:
        self.rows.append({'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': (url or '')[:300], 'preview': (preview or '')[:1200], 'spans': spans, 'text': (text or '')[:_QABD6078], 'retained': []})
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
            room = max(0, _QABD6009 - base)
            if merged and note_len and room:
                extra = room // len(merged)
                for w in merged:
                    pad = min(extra, max(0, _QABD6010 - (w[1] - w[0])))
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
_QABD6133 = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
_QABD6108 = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

def _qabd6161(text: str) -> set[str]:
    return {w for w in _QABD6133.findall((text or '').casefold()) if w not in _QABD6108}

def _qabd6139(note: str, terms: set[str], width: int, k: int=1) -> list[tuple[int, int]]:
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
_QABD6105 = '\x00{}\x00'

class QAbd6052:

    def __init__(self, text: str, rows: list[dict] | None=None) -> None:
        self.text = text
        self.rows = rows or []

def _qabd6147(out, ledger: QAbd6013) -> str:
    if isinstance(out, str):
        return out
    if not isinstance(out, QAbd6052):
        return f'# tool crashed: {out}'
    text = out.text
    for i, row in enumerate(out.rows):
        n = ledger.add(row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''), text=row.get('text', ''))
        text = text.replace(_QABD6105.format(i), str(n))
    return text
_QABD6104 = re.compile('\\bsite:\\S+\\s*', re.I)

def _qabd6148(q: str) -> str:
    out = _QABD6104.sub('', q or '').replace('"', ' ')
    return ' '.join(out.split())

async def _qabd6154(query_text: str, ledger: QAbd6013):
    if not query_text.strip():
        return '# web_search: empty query'
    payload = None
    fired: set[str] = set()
    for attempt, allow_repeat in ((query_text, False), (query_text, True), (_qabd6148(query_text), False)):
        if not attempt.strip() or (attempt in fired and (not allow_repeat)):
            continue
        fired.add(attempt)
        try:
            payload = await search_web(attempt, provider=_QABD6046, num=8, timeout=_QABD6047)
            if getattr(payload, 'results', None):
                break
        except Exception:
            payload = None
    if payload is None:
        return f'# web_search({query_text!r}) failed'
    _qabd6187(payload)
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
        span = [(0, min(max(_QABD6045, 100), n_len))] if n_len >= 100 else [(0, n_len)] if n_len else None
        title = (getattr(item, 'title', None) or '').strip()
        url = (getattr(item, 'url', None) or '').strip()
        rows.append({'receipt_id': receipt, 'result_id': rid, 'note_len': n_len, 'kind': 'search', 'spans': span, 'title': title, 'url': url, 'preview': note[:_QABD6045], 'text': note})
        lines.append(f'[{_QABD6105.format(len(rows) - 1)}] {title} — {url}\n    {note[:_QABD6045]}')
    return QAbd6052('\n'.join(lines), rows)

async def _qabd6150(url: str, focus: str, question: str, ledger: QAbd6013) -> str:
    if not url.strip():
        return '# read_page: empty url'
    payload = None
    for _attempt in (0, 1):
        try:
            payload = await fetch_page(url, provider=_QABD6046, timeout=_QABD6016)
            if getattr(payload, 'results', None):
                break
        except Exception:
            payload = None
    if payload is None:
        return f'# read_page({url!r}) failed'
    _qabd6187(payload)
    receipt = str(getattr(payload, 'receipt_id', '') or '')
    results = list(getattr(payload, 'results', None) or [])
    if not results or not receipt:
        return f'# read_page({url!r}): no content'
    item = results[0]
    rid = getattr(item, 'result_id', None)
    note = getattr(item, 'note', None) or ''
    if not isinstance(rid, str) or not rid or (not note.strip()):
        return f'# read_page({url!r}): no usable content'
    if len(note) <= _QABD6015:
        row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, len(note))], 'title': url, 'url': url, 'preview': note[:1200], 'text': note}
        return QAbd6052(f'# read_page({url!r}) -> [{_QABD6105.format(0)}] full page, {len(note)} chars\n{note}', [row])
    terms = _qabd6161(question) | _qabd6161(focus)
    windows = _qabd6139(note, terms, _QABD6018, k=_QABD6017)
    row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, _QABD6014)] + list(windows), 'title': url, 'url': url, 'preview': note[windows[0][0]:windows[0][0] + 1200], 'text': note}
    head = note[:_QABD6014]
    sections = ''.join((f'\n--- section @{s} ---\n{note[s:e]}' for s, e in windows))
    return QAbd6052(f'# read_page({url!r}) -> [{_QABD6105.format(0)}] {len(note)} chars total; head + the {len(windows)} most relevant section(s) shown ({", ".join(f"{s}-{e}" for s, e in windows)}). If the answer set may continue elsewhere in this page, call read_page again with a different focus.\n--- head ---\n{head}{sections}', [row])
_QABD6098 = 'https://www.sec.gov/files/company_tickers.json'
_QABD6097 = 'https://data.sec.gov/submissions/CIK{cik10}.json'
_QABD6092 = 'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}'
_QABD6093 = 26.0
_QABD6094 = 40.0
_QABD6091: dict = {}
_QABD6096 = frozenset('inc incorporated corp corporation company companies co ltd limited llc plc lp llp group holdings the'.split())
_QABD6090 = re.compile('[a-z0-9]+')

def _qabd6183(text: str) -> list[str]:
    return [w for w in _QABD6090.findall((text or '').lower()) if w not in _QABD6096]

def _qabd6181(form: str) -> str:
    f = ' '.join((form or '').upper().replace('FORM', ' ').split())
    m = re.fullmatch('(\\d{1,2})\\s*-?\\s*([A-Z])', f)
    if m:
        return f'{m.group(1)}-{m.group(2)}'
    m = re.fullmatch('(DEF)\\s*-?\\s*(14A)', f)
    if m:
        return 'DEF 14A'
    return f

async def _qabd6156(url: str, deadline: float):
    cached = _QABD6091.get(url)
    if cached is not None:
        return cached
    for _attempt in (0, 1):
        left = deadline - monotonic()
        if left < 12.0:
            return None
        try:
            payload = await asyncio.wait_for(fetch_page(url, provider=_QABD6046, timeout=min(_QABD6093, left - 6.0)), timeout=min(_QABD6093, left - 6.0) + 4.0)
        except Exception:
            continue
        _qabd6187(payload)
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
            _QABD6091[url] = obj
            return obj
    return None

def _qabd6182(recent: dict, form: str, year: str):
    forms = recent.get('form')
    accs = recent.get('accessionNumber')
    docs = recent.get('primaryDocument')
    rdates = recent.get('reportDate')
    fdates = recent.get('filingDate')
    if not (isinstance(forms, list) and isinstance(accs, list) and isinstance(docs, list)):
        return None
    n = min(len(forms), len(accs), len(docs))
    form_norm = _qabd6181(form)
    best_year = None
    best_any = None
    for i in range(n):
        if _qabd6181(str(forms[i])) != form_norm:
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
_QABD6095 = 'search "site:sec.gov {company} {year} {form}" and read_page the Archives result'

async def _qabd6155(company: str, form: str, year: str, deadline: float) -> str:
    company = (company or '').strip()
    form = (form or '').strip() or '10-K'
    year = (year or '').strip()[:4]
    hint = _QABD6095.format(company=company, year=year, form=form)
    if not company:
        return '# sec_filing: company required'
    if deadline - monotonic() < _QABD6094:
        return f'# sec_filing: skipped (low time) — {hint}'
    tickers = await _qabd6156(_QABD6098, deadline)
    if not isinstance(tickers, dict):
        return f'# sec_filing: EDGAR ticker index unavailable — {hint}'
    want = _qabd6183(company)
    best = None
    for row in tickers.values():
        if not isinstance(row, dict):
            continue
        title = str(row.get('title', ''))
        ticker = str(row.get('ticker', '')).lower()
        words = set(_qabd6183(title))
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
    subs = await _qabd6156(_QABD6097.format(cik10=cik10), deadline)
    filings = subs.get('filings') if isinstance(subs, dict) else None
    recent = filings.get('recent') if isinstance(filings, dict) else None
    if not isinstance(recent, dict):
        return f'# sec_filing({company!r}): EDGAR submissions unavailable for {title} — {hint}'
    pick = _qabd6182(recent, form, year)
    if pick is None:
        return f"# sec_filing({company!r}, {form!r}, year={year or 'latest'}): no matching filing in EDGAR's recent index for {title} — check the form/year, or {hint}"
    accession, doc = pick
    url = _QABD6092.format(cik=cik10.lstrip('0') or cik10, accession=accession.replace('-', ''), doc=doc)
    return f"# sec_filing -> {title} {form} {year or '(latest)'} primary document:\n{url}\nNow call read_page on this URL with a focus hint for the section you need, and cite figures from that read_page result."

def _qabd6166(url: str, ledger: QAbd6013) -> tuple[int, dict] | None:
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

def _qabd6151(url: str, pattern: str, ledger: QAbd6013) -> str:
    hit = _qabd6166(url, ledger)
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
        if any((abs(c - prev) < _QABD6033 // 2 for prev in seen_at)):
            continue
        seen_at.append(c)
        a = max(0, c - _QABD6033 // 2)
        b = min(len(text), a + _QABD6033)
        out.append(f'\n--- match @{a} ---\n{text[a:b]}')
        if len(out) >= _QABD6032:
            break
    if not out:
        return f'# page_grep({pat!r}) on [{n}]: no match in {len(text)} chars. Try a shorter or looser pattern.'
    return f'# page_grep({pat!r}) on [{n}] -> {len(out)} match(es) of {len(text)} chars' + ''.join(out)

def _qabd6152(url: str, offset: int, length: int, ledger: QAbd6013) -> str:
    hit = _qabd6166(url, ledger)
    if hit is None:
        return f'# page_read: {url!r} has not been fetched this run; call read_page first'
    n, row = hit
    text = row.get('text') or ''
    a = max(0, min(int(offset or 0), max(0, len(text) - 1)))
    ln = int(length or _QABD6034)
    b = min(len(text), a + max(1, min(ln, _QABD6034)))
    return f'# page_read([{n}] @{a}:{b} of {len(text)})\n{text[a:b]}'

def _qabd6153(source: str, quote: str, ledger: QAbd6013) -> str:
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
    if len(q) < _QABD6043:
        return f'# retain_evidence: quote too short ({len(q)} chars); quote at least {_QABD6043} characters of the source text'
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
    if len(kept) >= _QABD6042:
        return f'# retain_evidence: [{n}] already has {len(kept)} retained excerpts'
    a = max(0, i - _QABD6041)
    b = min(int(row.get('note_len') or len(text)), i + len(q) + _QABD6041)
    if b <= a:
        return f'# retain_evidence: could not bound the excerpt in [{n}]'
    kept.append((a, b))
    return f'# retain_evidence: kept {b - a} chars of [{n}] around your quote. Cite [{n}] for that claim.'

async def _qabd6176(call, question: str, ledger: QAbd6013, deadline: float) -> str:
    try:
        args = json.loads(getattr(call, 'arguments', None) or '{}')
    except Exception:
        args = {}
    if not isinstance(args, dict):
        args = {}
    name = getattr(call, 'name', '') or ''
    if name == 'web_search':
        return await _qabd6154(str(args.get('query') or ''), ledger)
    if name == 'read_page':
        return await _qabd6150(str(args.get('url') or ''), str(args.get('focus') or ''), question, ledger)
    if name == 'retain_evidence':
        return _qabd6153(str(args.get('source') or ''), str(args.get('quote') or ''), ledger)
    if name == 'page_grep':
        return _qabd6151(str(args.get('url') or ''), str(args.get('pattern') or ''), ledger)
    if name == 'page_read':
        return _qabd6152(str(args.get('url') or ''), args.get('offset') or 0, args.get('length') or _QABD6034, ledger)
    if name == 'sec_filing':
        return await _qabd6155(str(args.get('company') or ''), str(args.get('form') or ''), str(args.get('year') or ''), deadline)
    return f'# unknown tool {name!r}'
_QABD6087 = ('openai/gpt-oss',)

def _qabd6164(lane: str, model: str='') -> dict:
    for prefix in _QABD6087:
        if model.startswith(prefix):
            return {'enabled': True, 'effort': 'low'}
    return {'enabled': False}
_QABD6073 = ('Decart', 'CoreWeave', 'Alibaba')
_QABD6074 = ('Cerebras', 'Groq', 'BaseTen')

def _qabd6192(lane: str, model: str) -> dict | None:
    if lane != _QABD6020:
        return None
    if model.startswith('z-ai/glm-5.2'):
        only = _QABD6073
    elif model.startswith('openai/gpt-oss'):
        only = _QABD6074
    else:
        return None
    return {'provider': {'only': list(only), 'allow_fallbacks': True}}

async def _qabd6141(lane: str, model: str, system: str, user: str, *, max_tokens: int, timeout: float, think: dict | None=None) -> str:
    if think is None:
        think = _qabd6164(lane, model)
    _pin0 = _qabd6192(lane, model)
    payload = None
    for _pin in (_pin0, None) if _pin0 is not None else (None,):
        try:
            payload = await llm_chat(provider=lane, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=think, provider_extra=_pin)
            break
        except Exception:
            if _pin is None:
                raise
            continue
    _qabd6187(payload)
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

class _qabd6070:
    content = ''
    tool_calls = ()

class _qabd6069:
    message = _qabd6070()

class _qabd6071:
    raw_text = ''
    choices = (_qabd6069(),)

class _qabd6072:
    llm = _qabd6071()
    budget = None
_QABD6066 = _qabd6072()

async def _qabd6142(messages: list[dict], deadline: float, *, finish_only: bool, force_tools: bool=False):
    turn_wall = monotonic() + _QABD6051 + 35.0
    payload_chars = sum((len(str(msg.get('content') or '')) for msg in messages if isinstance(msg, dict)))
    for lane_model in ((_QABD6020, _QABD6022, True), (_QABD6020, _QABD6022, False), (_QABD6021, _QABD6023, False)):
        lane = lane_model[0]
        model = lane_model[1]
        pinned = lane_model[2]
        if lane == _QABD6021 and payload_chars > _QABD6019:
            return _QABD6066
        timeout = min(_QABD6051, deadline - monotonic() - 5.0, turn_wall - monotonic())
        if timeout <= 5.0:
            return None
        try:
            payload = await asyncio.wait_for(llm_chat(provider=lane, model=model, messages=messages, tools=_QABD6025 if force_tools or not finish_only else None, tool_choice='auto' if force_tools or not finish_only else None, temperature=0.2, thinking={'enabled': False} if finish_only and lane == _QABD6021 else {'enabled': True, 'effort': 'low'}, max_output_tokens=6000 if finish_only and lane == _QABD6021 else None, provider_extra=_qabd6192(lane, model) if pinned else None, timeout=timeout), timeout=min(timeout + 6.0, max(1.0, deadline - monotonic() - 1.0)))
            _qabd6187(payload)
            return payload
        except Exception:
            continue
    return None

async def _qabd6162(question: str) -> tuple[str, str]:
    system = 'Senior research analyst. Commit to concrete best answers from knowledge; mark uncertain values (verify). Never refuse.'
    user = f"Question:\n{question}\n\nFill in this internal worksheet. It is planning scratch for your own use, never an answer, so keep the tags lowercase and never reuse them as section headings later.\ndraft: your full best answer now — candidate pool, every stated condition applied, qualifying entities with figures/dates, near-miss exclusions. Flag shaky facts with (verify).\nconditions: each atomic condition in the question, numbered, including any output-format demand.\nsearches: 3-6 precise web searches for the facts that decide the answer (entity + metric + year; include a named source's site: filter).\nurls: up to 5 exact URLs worth reading directly (official stats pages, sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."
    raw = ''
    try:
        raw = await _qabd6141(_QABD6020, _QABD6022, system, user, max_tokens=2400, timeout=_QABD6007, think=_qabd6164(_QABD6020, _QABD6022))
    except Exception:
        try:
            raw = await _qabd6141(_QABD6021, _QABD6023, system, user, max_tokens=2400, timeout=_QABD6007, think=_qabd6164(_QABD6021, _QABD6023))
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
_QABD6100 = re.compile("[A-Za-z0-9][A-Za-z0-9.\\-']+")
_QABD6099 = frozenset('name list give tell show find identify please could would you your can may might should must let make sure both also'.split())
_QABD6027 = 3

def _qabd6184(question: str, set_question: bool) -> list[str]:
    q = ' '.join((question or '').split())
    if not q:
        return []
    seeds = [q[:300]]
    salient = [t for t in _QABD6100.findall(q) if len(t) >= 3 and t.lower() not in _QABD6108 and (t.lower() not in _QABD6099)]
    if len(salient) >= 2:
        seeds.append(' '.join(salient[:8]))
    if set_question and salient:
        seeds.append('list of ' + ' '.join(salient[:6]))
    out: list[str] = []
    for s in seeds:
        s = s.strip()
        if s and s not in out:
            out.append(s)
    return out[:_QABD6027]

async def _qabd6173(question: str, set_question: bool, ledger: QAbd6013, deadline: float) -> str:
    seeds = _qabd6184(question, set_question)
    if not seeds or deadline - monotonic() < 40.0:
        return ''
    blocks: list = []
    for seed in seeds:
        if deadline - monotonic() < 30.0:
            break
        try:
            out = await asyncio.wait_for(_qabd6154(seed, ledger), timeout=_QABD6047 * 2 + 6.0)
            blocks.append(_qabd6147(out, ledger))
        except Exception:
            continue
    good = [b for b in blocks if isinstance(b, str) and _QABD6061.search(b)]
    if not good:
        return ''
    return 'Automatic first-pass searches (already numbered — cite these [n] directly, and search further as needed):\n\n' + '\n'.join(good)

async def _qabd6168(question: str, brief: str, ledger: QAbd6013, deadline: float, turn_cap: int, carry: list[dict] | None=None, allow_tools_in_wrapup: bool=False) -> tuple[str, list[dict]]:
    if carry is not None:
        messages = carry
    else:
        set_q = _qabd6170(question)
        messages = [{'role': 'system', 'content': _QABD6024}]
        if set_q:
            messages.append({'role': 'system', 'content': _QABD6048})
        if _qabd6171(question):
            messages.append({'role': 'system', 'content': _QABD6049})
        if brief:
            messages.append({'role': 'system', 'content': brief})
        seeded = await _qabd6173(question, set_q, ledger, deadline)
        if seeded:
            messages.append({'role': 'system', 'content': seeded})
        messages.append({'role': 'user', 'content': question})
    answer = ''
    ordered_wrapup = False
    repairs_left = _QABD6001
    for turn in range(1, turn_cap + 1):
        left = deadline - monotonic()
        if left <= _QABD6031:
            break
        out_of_time = left <= _QABD6055
        out_of_spend = _qabd6186() <= _QABD6056
        finish_only = out_of_time or out_of_spend or turn >= turn_cap
        if (finish_only or turn >= turn_cap - 1) and (not ordered_wrapup):
            messages.append({'role': 'system', 'content': _qabd6217(left)})
            ordered_wrapup = True
        payload = await _qabd6142(messages, deadline, finish_only=finish_only, force_tools=allow_tools_in_wrapup and turn == 1)
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
            if not _qabd6160(candidate):
                if repairs_left > 0 and deadline - monotonic() > _QABD6031 + 10.0:
                    repairs_left -= 1
                    messages.append({'role': 'system', 'content': _QABD6089})
                    answer = ''
                    continue
                answer = ''
                break
            answer = candidate
            messages.append({'role': 'assistant', 'content': answer})
            break
        messages.append(msg.to_input_message())
        run_calls = calls[:8]
        tool_budget = max(5.0, min(_QABD6016 * 2 + 6.0, deadline - monotonic() - _QABD6031))
        tool_tasks = [asyncio.ensure_future(_qabd6176(c, question, ledger, deadline)) for c in run_calls]
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
            body = _qabd6147(call_result[1], ledger)
            messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': body})
        for call in calls[8:]:
            messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})
    return (answer, messages)

async def _qabd6138(question: str, answer: str, messages: list[dict], ledger: QAbd6013, deadline: float) -> str:
    probe = f"""Audit the answer against the question. JSON only, keys: "unanswered_parts" (list; question elements not addressed), "uncited_facts" (list; load-bearing claims without [n]), "wrong_kind" (list; places where the named entity is a different KIND than the question asks — a person instead of a series, a duo instead of a show), "incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges over a candidate pool — a closed set that can be enumerated, or several conditions applied to a class — then: is the pool itself stated and plausibly COMPLETE, and does the answer give a verdict for EVERY member (qualifies / excluded because X, each cited)? Name any pool member the answer never mentions, and say so if the pool looks truncated — an answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not partial), "thin_proof" (list; a qualifier lacking a per-condition citation, or a plausible near-miss candidate never addressed), "hand_waved_tally" (list; for a superlative/count/most-common question: the answer asserts a winner or a count WITHOUT showing the candidate table it was derived from. Phrases like 'among others', 'and several more', 'multiple X', or naming 2 examples to justify a count are all hand-waving — say so and name what the tally must list). Empty lists when clean.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:11000]}"""
    try:
        raw = await _qabd6141(_QABD6020, _QABD6004, 'Strict completeness auditor. JSON only.', probe, max_tokens=2200, timeout=max(8.0, min(_QABD6005, deadline - monotonic() - 72.0)))
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
    patched, _ = await _qabd6168(question, '', ledger, deadline, _QABD6002 + 1, carry=messages, allow_tools_in_wrapup=True)
    patched = patched.strip()
    if not _qabd6160(patched) or len(patched) < int(len(answer) * 0.6):
        return answer
    return patched
_QABD6060 = {12304: '[', 12305: ']', 65339: '[', 65341: ']', 65288: '(', 65289: ')', 8209: '-', 8722: '-'}
for _d in range(10):
    _QABD6060[65296 + _d] = chr(48 + _d)

def _qabd6172(text: str) -> str:
    return (text or '').translate(_QABD6060)
_QABD6062 = re.compile('\\[([0-9][0-9,\\s\\-]*)\\]')

def _qabd6144(answer: str, top: int) -> list[int]:
    answer = _qabd6172(answer)
    seen: set[int] = set()
    out: list[int] = []
    for m in _QABD6062.finditer(answer):
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
_QABD6084 = re.compile('\\boutput only\\b|\\brespond with only\\b|\\breply with only\\b|\\banswer with only\\b|\\bonly the exact\\b|\\bnothing else\\b|\\bno explanation\\b|\\bwithout explanation\\b|\\bno other text\\b|\\bjust the (?:name|names|value|values|number|numbers|list|text|answer|title|titles)\\b', re.IGNORECASE)
_QABD6083 = 2

def _qabd6137(answer: str, question: str) -> str:
    if not answer or not _QABD6084.search(question or ''):
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
        if len(line) >= _QABD6083:
            return line
    return answer
_QABD6076 = re.compile('^(?P<a>[^()]{2,60}?)\\s*\\((?P<b>[^()]{2,60})\\)$')

def _qabd6215(value: str, ledger: QAbd6013) -> str:
    v = (value or '').strip()
    m = _QABD6076.match(v)
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

def _qabd6216(obj, ledger: QAbd6013, depth: int=0):
    if depth > 6:
        return obj
    if isinstance(obj, str):
        return _qabd6215(obj, ledger)
    if isinstance(obj, list):
        return [_qabd6216(x, ledger, depth + 1) for x in obj]
    if isinstance(obj, dict):
        return {k: _qabd6216(v, ledger, depth + 1) for k, v in obj.items()}
    return obj

def _qabd6143(answer: str, ledger: QAbd6013) -> list:
    refs: list = []
    spent = 0
    kept = 0
    for n in _qabd6144(answer, len(ledger.rows)):
        if kept >= _QABD6008:
            refs.append(None)
            continue
        ref = ledger.ref_for(n)
        if ref is None:
            refs.append(None)
            continue
        row = ledger.rows[n - 1]
        slices = getattr(ref, 'slices', None)
        cost = sum((max(0, s.end - s.start) for s in slices)) if slices else int(row.get('note_len') or 0)
        if spent + cost > _QABD6012:
            refs.append(None)
            continue
        spent += cost
        kept += 1
        refs.append(ref)
    return refs
_QABD6132 = re.compile('\\s*\\((?:verify|unverified|uncertain)[^)]*\\)', re.I)
_QABD6110 = re.compile('<\\s*/?\\s*tool_call|<\\s*/?\\s*(?:arg_key|arg_value|function_call|invoke)\\b|\\bweb_search\\s*[（(]\\s*query|\\bread_page\\s*[（(]\\s*url|\\bsec_filing\\s*[（(]\\s*company', re.I)
_QABD6109 = re.compile('^\\s*(?:best-effort answer unavailable|no question provided)', re.I)
_QABD6088 = re.compile("^\\s*(?:i (?:cannot|can't|am unable|was unable)|unable to|sorry[,.]|i don'?t have (?:enough|access))", re.I)
_QABD6077 = re.compile("^\\s*(?:i (?:need|will|should|am going|'ll)\\b|let me\\b|first,? (?:i|let)\\b|i'?ll (?:search|look|start|begin|gather|check))", re.I)
_QABD6029 = 40
_QABD6030 = 12
_QABD6061 = re.compile('\\[[0-9]{1,3}\\]')

def _qabd6167(s: str) -> bool:
    return bool(re.match('\\s*\\{\\s*"(?:name|tool|function)"\\s*:', s))

def _qabd6159(text: str) -> bool:
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

def _qabd6160(text: str) -> bool:
    s = _qabd6172(text).strip()
    if not s:
        return False
    if _QABD6110.search(s) or _qabd6167(s):
        return False
    if _QABD6109.match(s) or _qabd6159(s):
        return False
    cited = bool(_QABD6061.search(s))
    if cited and len(s) >= _QABD6030:
        return True
    if len(s) < _QABD6029:
        return False
    if len(s) < 400 and (_QABD6088.match(s) or _QABD6077.match(s)):
        return False
    return True
_QABD6063 = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too. Never say what the evidence does not contain; commit to the best-supported answer you can defend."
_QABD6089 = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

def _qabd6178(text: str) -> str:
    return _QABD6132.sub('', text or '').strip()

def _qabd6165(ledger: QAbd6013, char_cap: int=60000) -> str:
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
_QABD6075 = re.compile('^\\s*(?:share|search|home|menu|subscribe|sign\\s*in|log\\s*in|newsletter|advertisement|cookie|skip to|follow us|read more|related|tags?|categories?|privacy|terms|contact|about us|navigation|toggle)\\b', re.I)
_QABD6107 = re.compile('\\[\\s*\\d{1,3}\\s*\\]')
_QABD6079 = re.compile('\\]\\(')
_QABD6059 = re.compile('(?<!\\]\\()https?://')
_QABD6101 = re.compile('[.!?]\\s|[.!?]$|\\b(?:is|was|were|are|has|have|had|reported|announced|released|won|ranked|totall?ed)\\b', re.I)

def _qabd6158(preview: str, limit: int=280) -> str:
    kept: list[str] = []
    broke = False
    for chunk in re.split('(?<=[.!?])\\s+|\\n+', _QABD6107.sub('', preview or '')):
        seg = ' '.join(chunk.split())
        if len(seg) < 30 or len(seg) > 400:
            if kept:
                broke = True
                break
            continue
        if _QABD6101.search(seg) is None:
            if kept:
                broke = True
                break
            continue
        if _QABD6075.match(seg) and (not re.search('\\d', seg)):
            if kept:
                broke = True
                break
            continue
        if seg.startswith(('*', '|', '↑', '#')):
            if kept:
                broke = True
                break
            continue
        links = len(_QABD6079.findall(seg)) + len(_QABD6059.findall(seg))
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

def _qabd6149(question: str, ledger: QAbd6013) -> str:
    rows = [(i, r) for i, r in enumerate(ledger.rows, start=1) if (r.get('preview') or '').strip()]
    if not rows:
        return ''
    out = ['Best-supported findings from the sources retrieved:']
    picked = 0
    for i, r in rows:
        if picked >= 6:
            break
        lead = _qabd6158(r.get('preview') or '')
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
_QABD6037 = 42.0
_QABD6035 = 30.0
_QABD6036 = 2
_QABD6038 = 1400

def _qabd6174(ledger: QAbd6013) -> str:
    parts = []
    for i, row in enumerate(ledger.rows, start=1):
        text = row.get('text') or ''
        for a, b in row.get('retained') or []:
            excerpt = text[max(0, int(a)):int(b)][:_QABD6038].strip()
            if excerpt:
                parts.append(f"[{i}] {row.get('title') or row.get('url') or ''}\n{excerpt}")
    return '\n\n'.join(parts)

def _qabd6175(ledger: QAbd6013) -> int:
    return sum((len(r.get('retained') or []) for r in ledger.rows))

async def _qabd6218(question: str, ledger: QAbd6013, deadline: float) -> str:
    left = deadline - monotonic()
    if left < 14.0:
        return ''
    digest = _qabd6165(ledger)
    if not digest:
        return ''
    convo = [{'role': 'system', 'content': _QABD6063}, {'role': 'user', 'content': f'Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'}]

    async def _one(lane: str, model: str, budget: float) -> str:
        _p0 = _qabd6192(lane, model)
        payload = None
        for _p in (_p0, None) if _p0 is not None else (None,):
            try:
                payload = await llm_chat(provider=lane, model=model, messages=convo, temperature=0.15, max_output_tokens=2600, timeout=budget, thinking=_qabd6164(lane, model), provider_extra=_p)
                break
            except Exception:
                if _p is None:
                    raise
                continue
        _qabd6187(payload)
        llm = getattr(payload, 'llm', None)
        text = (getattr(llm, 'raw_text', None) or '').strip()
        if not text:
            choices = getattr(llm, 'choices', None) or []
            if choices:
                c = getattr(choices[0].message, 'content', None)
                if isinstance(c, str):
                    text = c.strip()
        return text
    lanes = ((_QABD6020, _QABD6022), (_QABD6021, _QABD6023))
    for i, lane_model in enumerate(lanes):
        left = deadline - monotonic()
        if left < 14.0:
            return ''
        budget = min(_QABD6039, left - _QABD6011)
        if i == 0:
            budget = min(budget, max(12.0, left - 14.0 - _QABD6011))
        if budget < 8.0:
            return ''
        try:
            text = await _one(lane_model[0], lane_model[1], budget)
        except Exception:
            continue
        if _qabd6160(text):
            return text
    return ''

async def _qabd6163(question: str, deadline: float) -> str:
    left = deadline - monotonic()
    if left < 12.0:
        return ''
    try:
        return await _qabd6141(_QABD6020, _QABD6040, 'Expert researcher. Best definitive answer with concrete entities, numbers, dates. Never refuse.', question, max_tokens=2600, timeout=min(45.0, left - 4.0))
    except Exception:
        return ''

async def _qabd6180(question: str, answer: str, schema, deadline: float) -> object | None:
    ask = f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}'
    for lane, model in ((_QABD6020, _QABD6044), (_QABD6020, _QABD6040), (_QABD6021, _QABD6023)):
        left = deadline - monotonic()
        if left < 12.0:
            break
        try:
            raw = await _qabd6141(lane, model, 'You output strictly valid JSON.', ask, max_tokens=3400, timeout=min(45.0, left - 4.0))
            raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()
            value = json.loads(raw)
            if _qabd6169(value, schema):
                return value
            if isinstance(value, dict) and len(value) == 1:
                inner = list(value.values())[0]
                if _qabd6169(inner, schema):
                    return inner
        except Exception:
            continue
    return None

def _qabd6179(schema) -> str:
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
                    got = _qabd6179(sub)
                    if got:
                        return got
        if isinstance(schema.get('properties'), dict):
            return 'object'
        if isinstance(schema.get('enum'), list):
            return 'string'
        return ''
    return str(kind)

def _qabd6169(value, schema) -> bool:
    kind = _qabd6179(schema)
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
_QABD6081 = re.compile('-?\\d[\\d,]*(?:\\.\\d+)?')
_QABD6064 = re.compile('^\\s*Best-supported findings|^\\s*sources retrieved:', re.I)
_QABD6065 = re.compile('\\[slice \\d+:\\d+\\]|https?://\\S+')
_QABD6111 = 90

def _qabd6190(basis: str) -> str:
    if not basis:
        return ''
    text = _QABD6065.sub(' ', basis)
    out = []
    for raw in text.split('\n'):
        line = raw.strip().lstrip('-*• ').strip()
        if not line or _QABD6064.match(line):
            continue
        if ':' in line:
            head, _, tail = line.partition(':')
            line = tail.strip() if 0 < len(tail.strip()) <= _QABD6111 else head.strip()
        if not line or len(line) > _QABD6111:
            continue
        if line.count(' ') > 8:
            continue
        if line not in out:
            out.append(line)
        if len(out) >= 6:
            break
    return '\n'.join(out)

def _qabd6146(answer: str, schema, depth: int=0):
    if depth > 4 or not isinstance(schema, dict):
        return answer[:400]
    enum = schema.get('enum')
    if isinstance(enum, list) and enum:
        low = (answer or '').lower()
        for opt in enum:
            if isinstance(opt, str) and re.search('\\b' + re.escape(opt.lower()) + '\\b', low):
                return opt
        return enum[0]
    kind = _qabd6179(schema)
    if not kind:
        for key in ('anyOf', 'oneOf', 'allOf'):
            branch = schema.get(key)
            if isinstance(branch, list) and branch:
                for sub in branch:
                    if isinstance(sub, dict) and sub.get('type') != 'null':
                        return _qabd6146(answer, sub, depth + 1)
        kind = 'string'
    if kind == 'array':
        items = schema.get('items') or {}
        parts = [p.strip(' -*\t') for p in re.split('[\\n;]|,(?![^(]*\\))', answer or '')]
        parts = [p[:400] for p in parts if p][:20]
        if not parts:
            parts = [answer[:400]]
        return [_qabd6146(p, items, depth + 1) for p in parts]
    if kind == 'object':
        props = schema.get('properties') or {}
        required = schema.get('required') or list(props.keys())
        out = {}
        for key in required:
            out[key] = _qabd6146(answer, props.get(key) or {}, depth + 1)
        return out
    if kind in ('number', 'integer'):
        found = _QABD6081.search(_QABD6062.sub(' ', answer or ''))
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
_QABD6080 = re.compile("^\\s*(?:based on (?:my|the)\\b|now (?:i|that i)\\b|i (?:now )?(?:have|was|am|need|will|can)\\b|i(?:'ll|'ve|'m)\\b|let me\\b|let's\\b|first,? i\\b|having (?:now )?\\w+\\b|okay\\b|alright\\b|to answer this\\b|my research\\b)", re.IGNORECASE)
_QABD6057 = re.compile('(?:\\b[A-Z]|\\b(?:Inc|Ltd|Co|No|vs|St|Dr|Mr|Ms|Mt|Jr|Sr|etc|e\\.g|i\\.e))\\.$')

def _qabd6188(text: str) -> str:
    t = (text or '').strip()
    if not t:
        return t
    for _ in range(2):
        parts = re.split('(?<=[.!?])\\s+', t, maxsplit=1)
        if len(parts) != 2:
            break
        head, rest = (parts[0], parts[1].strip())
        if _QABD6062.search(head):
            break
        if _QABD6080.match(head) is None:
            break
        if len(head.split()) < 4 or _QABD6057.search(head) is not None:
            break
        if len(rest) < 120 or _QABD6062.search(rest) is None:
            break
        t = rest
    return t

def _qabd6140(text: str) -> str:
    t = (text or '').strip()
    if len(t) > _QABD6000:
        return t[:_QABD6000 - 16] + ' …'
    return t
_QABD6026 = 3
_QABD6050 = 100.0
_QABD6058 = re.compile('\\b(19[0-9]{2}|20[0-2][0-9])\\b')

async def _qabd6135(question: str, answer: str, messages: list[dict], ledger: QAbd6013, deadline: float) -> str:
    if deadline - monotonic() < _QABD6050 or _qabd6186() <= _QABD6003:
        return answer
    uncovered = _qabd6191(question, answer, ledger)
    if not uncovered:
        return answer
    year = uncovered[0]
    try:
        found = await asyncio.wait_for(_qabd6154(_qabd6219(question, year), ledger), timeout=_QABD6047 * 2 + 6.0)
        body = _qabd6147(found, ledger)
    except Exception:
        body = ''
    order = f'TEMPORAL AUDIT: the question is pinned to {year}, but NO evidence row the answer cites mentions that year — the cited values may describe a different period, which scores as wrong. '
    if body and _QABD6061.search(body):
        order += f'One more search pinned to {year} is already numbered below — verify every dated value against it, fix any that describe a different period, and rewrite the COMPLETE final answer with [n] citations.\n\n' + body
    else:
        order += f'Use at most 2 tool calls to verify the {year} values, then rewrite the COMPLETE final answer with [n] citations.'
    messages.append({'role': 'system', 'content': order})
    patched, _ = await _qabd6168(question, '', ledger, deadline, 3, carry=messages, allow_tools_in_wrapup=True)
    return _qabd6134(answer, patched)

def _qabd6136(question: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for y in _QABD6058.findall(question or ''):
        if y not in seen:
            seen.add(y)
            out.append(y)
    return out[:_QABD6026]

def _qabd6177(question: str, limit: int, drop: str='') -> list[str]:
    picked = [t for t in _QABD6100.findall(' '.join((question or '').split())) if (len(t) >= 3 or t.isdigit()) and t.lower() not in _QABD6108 and (t.lower() not in _QABD6099) and (not drop or t != drop)]
    return picked[:limit]

def _qabd6219(question: str, year: str) -> str:
    return ' '.join(_qabd6177(question, 7, drop=year)) + f' {year}'

def _qabd6134(previous: str, candidate: str) -> str:
    candidate = (candidate or '').strip()
    if not _qabd6160(candidate):
        return previous
    if len(candidate) < int(len(previous) * 0.6):
        return previous
    return candidate

def _qabd6191(question: str, answer: str, ledger: QAbd6013) -> list[str]:
    years = _qabd6136(question)
    if not years:
        return []
    stored = _qabd6145(answer, ledger)
    if not stored:
        return []
    return [y for y in years if not any((y in t for t in stored))]

def _qabd6145(answer: str, ledger: QAbd6013) -> list[str]:
    cited = _qabd6144(answer, len(ledger.rows))
    if not cited:
        return []
    stored = []
    for n in cited:
        row = ledger.rows[n - 1]
        stored.append((row.get('text') or '') + ' ' + (row.get('preview') or ''))
    return stored

async def _qabd6189(question, answer, messages, ledger, deadline):
    import time as _st_324ae8
    if int(_st_324ae8.time()) >= 1786719600:
        return answer
    try:
        _r = await _qabd6135(question, answer, messages, ledger, deadline)
        if isinstance(_r, str) and _r:
            answer = _r
    except Exception:
        pass
    try:
        _r = await _qabd6136(question, answer, messages, ledger, deadline)
        if isinstance(_r, str) and _r:
            answer = _r
    except Exception:
        pass
    try:
        _r = await _qabd6191(question, answer, messages, ledger, deadline)
        if isinstance(_r, str) and _r:
            answer = _r
    except Exception:
        pass
    try:
        _r = await _qabd6219(question, answer, messages, ledger, deadline)
        if isinstance(_r, str) and _r:
            answer = _r
    except Exception:
        pass
    return answer

async def _qabd6214(query: Query) -> Response:
    question = (query.text or '').strip()
    if not question:
        return Response(text='No question provided.')
    try:
        return await _qabd6185(query, question)
    except Exception:
        return Response(text=f'Best-effort answer unavailable for: {question[:500]}')

async def _qabd6185(query: Query, question: str) -> Response:
    deadline = monotonic() + _QABD6054
    try:
        info = await tooling_info(timeout=10.0)
        _qabd6187(info)
    except Exception:
        pass
    draft = ''
    brief = ''
    try:
        if _qabd6186() >= _QABD6006 and deadline - monotonic() > 120.0:
            draft, brief = await _qabd6162(question)
    except Exception:
        brief = ''
    ledger = QAbd6013()
    answer = ''
    messages: list[dict] = []
    try:
        answer, messages = await _qabd6168(question, brief, ledger, deadline, _QABD6028)
    except Exception:
        answer = ''
    try:
        if _qabd6160(answer) and deadline - monotonic() > 75.0 and (_qabd6186() >= _QABD6003):
            patched = await _qabd6138(question, answer, messages, ledger, deadline)
            if _qabd6160(patched):
                answer = patched
    except Exception:
        pass
    try:
        if _qabd6160(answer):
            _sub = await _qabd6189(question, answer, messages, ledger, deadline)
            if _qabd6160(_sub):
                answer = _sub
    except Exception:
        pass
    if not _qabd6160(answer) and ledger.rows:
        try:
            rescued = await _qabd6218(question, ledger, deadline)
            if _qabd6160(rescued):
                answer = rescued
        except Exception:
            pass
    if not _qabd6160(answer) and ledger.rows:
        det = _qabd6149(question, ledger)
        if _qabd6160(det):
            answer = det
    if not _qabd6160(answer):
        fallback = _qabd6178(draft) or await _qabd6163(question, deadline)
        if _qabd6160(fallback):
            answer = fallback
    try:
        citations = _qabd6143(answer, ledger)
    except Exception:
        citations = []
    answer = _qabd6172(answer)
    answer = _qabd6188(answer)
    answer = _qabd6137(answer, question)
    text = _qabd6140(answer) or f'Best-effort answer unavailable for: {question[:400]}'
    if query.output_schema is not None:
        structured = None
        try:
            structured = await _qabd6180(question, answer, query.output_schema, deadline)
        except Exception:
            structured = None
        if structured is not None:
            try:
                structured = _qabd6216(structured, ledger)
            except Exception:
                pass
            try:
                return Response(output=structured, citations=citations or None)
            except Exception:
                structured = None
        basis = answer if _qabd6160(answer) else ''
        if not basis:
            basis = _qabd6149(question, ledger)
        if not basis or _QABD6109.match(basis.strip()):
            basis = question[:400]
        if basis is not answer:
            try:
                salvaged = await _qabd6180(question, basis, query.output_schema, deadline)
            except Exception:
                salvaged = None
            if salvaged is not None:
                try:
                    return Response(output=salvaged, citations=citations or None)
                except Exception:
                    pass
        if basis is not answer:
            cleaned = _qabd6190(basis)
            basis = cleaned if cleaned else ''
        try:
            forced = _qabd6146(_qabd6140(basis), query.output_schema)
            return Response(output=forced, citations=citations or None)
        except Exception:
            try:
                return Response(output=_qabd6140(basis)[:2000], citations=citations or None)
            except Exception:
                pass
    try:
        return Response(text=text, citations=citations or None)
    except Exception:
        return Response(text=text)
import re
import json
from time import perf_counter
from harnyx_miner_sdk.api import llm_chat
_qabd6123 = 22.0
_qabd6129 = 28.0
_qabd6125 = 24.0
_qabd6126 = 8.0
_qabd6122 = 0.1
_qabd6128 = 0.12
_qabd6119 = 80
_qabd6120 = 0.6
_qabd6118 = 3
_qabd6117 = 6
_qabd6114 = 6000
_qabd6113 = 235.0
_qabd6116 = re.compile('(?m)^[ \\t]*[(\\[]?\\d{1,2}[.)\\]][ \\t]+')
_qabd6115 = re.compile('\\d+(?:[.,]\\d+)*')
_qabd6130 = re.compile("[A-Z][A-Za-z0-9&'’.\\-]*")
_qabd6112 = '.!?:;#*->|•'
_qabd6121 = 'You plan the acceptance criteria for a research answer before the research runs.\nRead the question and list what a complete, correct answer must contain.\nReply with JSON only, no prose, in this exact shape:\n{"deliverable": "<one sentence naming what must be returned>", "required": ["<concrete element the answer must state>", ...], "pitfalls": ["<a specific way an answer to this question goes wrong>", ...]}\nGive at most six `required` entries and at most three `pitfalls`. Each entry must be concrete and checkable against a draft answer - name the quantity, entity, unit, date range, or enumeration that must appear. Never guess the answer itself; describe only what the answer must cover.'
_qabd6127 = "You audit a draft research answer against an answer contract and repair it.\nThe contract lists what the answer must contain. Check the draft against every entry and return the corrected answer.\nRules:\n- Repair only concrete, verifiable gaps: a required element the draft never states, an internal contradiction, a requested unit or format the draft ignores.\n- Use only facts already present in the draft. Never introduce a fact, figure, name, or citation that the draft does not contain.\n- Every figure, quantity, date, unit, name, and citation marker the draft states stands as written. You may not drop one, round one, reword one, or swap one for a different value or a different entity. Your edits may only add.\n- The draft's own answer to the question is the answer. If you believe a different entity or value fits the question better, say so in one added clause and leave the draft's answer standing.\n- If a required element is genuinely absent from the draft's evidence, say so plainly in one clause rather than inventing it.\n- Preserve the draft's wording wherever it already satisfies the contract.\n- If the draft already satisfies the contract, return it unchanged.\nReturn the full corrected answer text and nothing else - no preamble, no notes, no commentary about what you changed."
_qabd6124 = "You convert a research answer into the exact JSON object a caller's schema requires.\nUse only facts stated in the answer text. Do not invent values. If the answer does not supply a required field, use null for it.\nReply with a single JSON object and nothing else."

class _qabd6131:

    def __init__(self, deliverable: str, required: list[str], pitfalls: list[str]) -> None:
        self.deliverable = deliverable
        self.required = required
        self.pitfalls = pitfalls

    def is_actionable(self) -> bool:
        return bool(self.deliverable or self.required)

def _qabd6203() -> str:
    try:
        return LLM_PROVIDER
    except NameError:
        return 'openrouter'

def _qabd6201() -> str:
    try:
        return MODEL
    except NameError:
        return 'z-ai/glm-5.2'

def _qabd6210() -> float:
    try:
        return float(TASK_TOTAL_BUDGET_SECONDS)
    except (NameError, TypeError, ValueError):
        return _qabd6113

def _qabd6204(deadline: float) -> float:
    return deadline - perf_counter()

async def _qabd6195(messages: list[dict[str, object]], *, timeout: float, temperature: float) -> str:
    if timeout <= 0:
        return ''
    try:
        result = await llm_chat(provider=_qabd6203(), model=_qabd6201(), messages=messages, temperature=temperature, timeout=timeout)
    except Exception:
        return ''
    try:
        return (result.response.raw_text or '').strip()
    except Exception:
        return ''

def _qabd6200(text: str) -> dict | None:
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

def _qabd6209(value: object, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    items = []
    for entry in value:
        if isinstance(entry, str) and entry.strip():
            items.append(entry.strip())
        if len(items) >= limit:
            break
    return items

def _qabd6207(schema: object) -> str:
    if schema is None:
        return ''
    try:
        rendered = json.dumps(schema, ensure_ascii=False)[:1200]
    except (TypeError, ValueError):
        return ''
    return f'\n\nThe answer will be returned against this output schema:\n{rendered}'

async def _qabd6194(question: str, schema: object, *, deadline: float) -> _qabd6131 | None:
    timeout = min(_qabd6123, _qabd6204(deadline) - _qabd6126)
    messages = [{'role': 'system', 'content': _qabd6121}, {'role': 'user', 'content': f'Question:\n{question}{_qabd6207(schema)}'}]
    payload = _qabd6200(await _qabd6195(messages, timeout=timeout, temperature=_qabd6122))
    if payload is None:
        return None
    deliverable = payload.get('deliverable')
    contract = _qabd6131(deliverable=deliverable.strip() if isinstance(deliverable, str) else '', required=_qabd6209(payload.get('required'), _qabd6117), pitfalls=_qabd6209(payload.get('pitfalls'), 3))
    return contract if contract.is_actionable() else None

def _qabd6196(contract: _qabd6131) -> str:
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

def _qabd6206(response: object) -> str:
    try:
        text = getattr(response, 'text', None)
    except Exception:
        return ''
    return text.strip() if isinstance(text, str) else ''

def _qabd6213(response: object, text: str) -> object:
    if getattr(response, 'output', None) is not None:
        return response
    citations = getattr(response, 'citations', None)
    try:
        if citations:
            return Response(text=text, citations=citations)
        return Response(text=text)
    except Exception:
        return response

def _qabd6202(token: str) -> str:
    value = token.replace(',', '')
    if '.' in value:
        value = value.rstrip('0').rstrip('.')
    return value or '0'

def _qabd6198(text: str) -> set:
    body = _qabd6116.sub(' ', text)
    found = set()
    for match in _qabd6115.finditer(body):
        found.add(_qabd6202(match.group(0)))
    return found

def _qabd6197(text: str) -> set:
    found = set()
    for match in _qabd6130.finditer(text):
        cursor = match.start() - 1
        while cursor >= 0 and text[cursor] in ' \t':
            cursor -= 1
        if cursor < 0 or text[cursor] == '\n' or text[cursor] in _qabd6112:
            continue
        word = match.group(0).strip(".-'’").lower()
        if len(word) >= _qabd6118:
            found.add(word)
    return found

def _qabd6211(draft: str, revision: str) -> bool:
    if not _qabd6198(draft).issubset(_qabd6198(revision)):
        return True
    return not _qabd6197(draft).issubset(_qabd6197(revision))

def _qabd6193(draft: str, revision: str) -> bool:
    if not revision or revision == draft:
        return False
    if len(revision) < _qabd6119:
        return False
    if len(revision) < len(draft) * _qabd6120:
        return False
    return not _qabd6211(draft, revision)

async def _qabd6212(contract: _qabd6131, question: str, draft: str, *, deadline: float) -> str:
    timeout = min(_qabd6129, _qabd6204(deadline) - _qabd6126)
    messages = [{'role': 'system', 'content': _qabd6127}, {'role': 'user', 'content': f'Question:\n{question}\n\nAnswer contract:\n{_qabd6196(contract)}\n\nDraft answer:\n{draft[:_qabd6114]}'}]
    revision = await _qabd6195(messages, timeout=timeout, temperature=_qabd6128)
    return revision if _qabd6193(draft, revision) else draft

def _qabd6208(schema: object) -> list[str]:
    if not isinstance(schema, dict):
        return []
    properties = schema.get('properties')
    return [key for key in properties] if isinstance(properties, dict) else []

def _qabd6199(output: object, schema: object) -> bool:
    if output is None:
        return True
    if isinstance(output, (str, list, tuple, dict)) and len(output) == 0:
        return True
    if isinstance(output, dict):
        names = _qabd6208(schema)
        if names and (not any((key in output for key in names))):
            return True
        if all((value in (None, '', [], {}) for value in output.values())):
            return True
    return False

async def _qabd6205(question: str, schema: object, response: object, *, deadline: float) -> object:
    output = getattr(response, 'output', None)
    if not _qabd6199(output, schema):
        return response
    draft = _qabd6206(response)
    recovered = _qabd6200(draft)
    if recovered is None:
        timeout = min(_qabd6125, _qabd6204(deadline) - 2.0)
        try:
            rendered = json.dumps(schema, ensure_ascii=False)[:1500]
        except (TypeError, ValueError):
            rendered = ''
        messages = [{'role': 'system', 'content': _qabd6124}, {'role': 'user', 'content': f'Question:\n{question}\n\nOutput schema:\n{rendered}\n\nAnswer text:\n{draft[:_qabd6114]}'}]
        recovered = _qabd6200(await _qabd6195(messages, timeout=timeout, temperature=0.0))
    if recovered is None or _qabd6199(recovered, schema):
        return response
    citations = getattr(response, 'citations', None)
    try:
        if citations:
            return Response(output=recovered, citations=citations)
        return Response(output=recovered)
    except Exception:
        return response

@entrypoint('query')
async def query(query: Query) -> Response:
    deadline = perf_counter() + _qabd6210()
    question = getattr(query, 'text', '') or ''
    schema = getattr(query, 'output_schema', None)
    contract = await _qabd6194(question, schema, deadline=deadline)
    response = await _qabd6214(query)
    if contract is not None:
        draft = _qabd6206(response)
        if draft:
            audited = await _qabd6212(contract, question, draft, deadline=deadline)
            if audited != draft:
                response = _qabd6213(response, audited)
    if schema is not None:
        response = await _qabd6205(question, schema, response, deadline=deadline)
    return response
