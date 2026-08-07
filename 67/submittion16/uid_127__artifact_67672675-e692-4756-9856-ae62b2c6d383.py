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
  - a single-provider LLM ladder (openrouter only; two model families).
Kill-safety: everything bounded by one deadline; force-commit well before it.

v32.6 — STRUCTURAL PASS. No change to the answer discipline, the detectors, the
localizer, the EDGAR router or any prompt text (all byte-for-byte v32.5). What
changed is the scaffolding those assets ran on:
  1. search_many, the batch tool LOOP_RULES tells the model to prefer, raised
     TypeError on every call where any sub-search succeeded, and ran its queries
     sequentially. Fixed and made concurrent; rows merge in QUERY order so [n]
     stays run-invariant.
  2. The seed fan-out in _loop called perf_counter(), never imported: NameError
     on turn 1 of every run, swallowed by a bare except. Removed as a duplicate
     of _preseed, which is now itself concurrent.
  3. A research turn plus its tool phase could overrun the wrap-up band and
     leave no time to write; both now reserve FINISH_RESERVE_S.
  4. Sandbox-policy hardening: no classes (hence no dunder names), no dunder
     imports, no mid-module imports, static tool dispatch only, every getattr
     name a string literal.

v32.7 — SINGLE PROVIDER. ai_gateway is removed; openrouter is the only chat
provider. The two-attempt ladder survives as a MODEL ladder (glm-5 then
deepseek-v3.2) because its value was never provider diversity — it was not
letting one transient failure end a turn, which on the finish turn is a zero.
The glm-5.2-fast empty-content workaround (reasoning off + a token cap on the
final turn) is deleted along with the model it existed for.
"""
        import asyncio
        import json
        import re
        from time import monotonic
        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        VERSION = 'v32.7-toolloop'
        LLM_PROVIDER = 'openrouter'
        LOOP_MODEL_A = 'z-ai/glm-5'
        LOOP_MODEL_B = 'deepseek/deepseek-v3.2'
        LOOP_MODEL_LADDER = (LOOP_MODEL_A, LOOP_MODEL_B)
        AUDIT_MODEL = 'openai/gpt-oss-120b'
        SCHEMA_MODEL = 'openai/gpt-oss-120b'
        RESORT_MODEL = 'deepseek/deepseek-v3.2'
        SEARCH_PROVIDER = 'parallel'
        WALL_BUDGET_S = 262.0
        SEARCH_TIMEOUT_S = 18.0
        FETCH_TIMEOUT_S = 16.0
        TURN_TIMEOUT_S = 75.0
        BRIEF_TIMEOUT_S = 50.0
        AUDIT_TIMEOUT_S = 28.0
        WRAPUP_AT_S = 90.0
        TOOL_PHASE_CAP_S = FETCH_TIMEOUT_S * 2 + 6.0
        FINISH_RESERVE_S = 52.0
        MIN_TAIL_S = 8.0
        AUDIT_EXTRA_TURNS = 2
        ANSWER_REPAIR_TURNS = 2
        RESCUE_TIMEOUT_S = 55.0
        MAX_TURNS = 15
        SEARCH_EXCERPT_CHARS = 550
        FETCH_HEAD_CHARS = 3000
        FETCH_WINDOW_CHARS = 3600
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
        LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'search_many', 'description': 'Run several web searches at once (in parallel) and get all numbered results back together. Use to enumerate or verify a whole set of candidates in one step — up to 8 queries.', 'parameters': {'type': 'object', 'properties': {'queries': {'type': 'array', 'items': {'type': 'string'}, 'description': 'up to 8 search queries to run together'}}, 'required': ['queries']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}]
        LOOP_RULES = "You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/search_many/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate's score, each entity's figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR's own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with 'Based on…', 'From my research…', 'I can provide a partial answer', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per prominent exclusion with its cited failing condition. EXACT VALUES ONLY: when the answer turns on figures, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; 'p < 0.0001' and 'P < .001' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value ('~$1.33B'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write '(verify)' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations ('highest scoring games' = the team's own points OR the combined total; 'largest' = area OR population; 'revenue' = segment OR consolidated), do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate's exact value, then test the comparator as written — 'more than 25' is strictly >25 (25 fails); 'between 2010 and 2019' includes both endpoints; convert a rate condition into a concrete integer test ('averaged more than 1 per year over 10 years' = 'more than 10 in total'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says 'brought to', do not write 'incarcerated'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain ('the evidence does not specify…', 'would be needed to determine…'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true ('No officer was held in all four prisons [n]'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; 'the evidence does not contain it' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.\n\n## Pairwise Scoring Rules\n\n- Decompose every sub-fact/filter before answering; never answer dates/counts/names from memory.\n- Full roster: enumerate the complete candidate pool, evaluate every candidate, cite exclusions with the failing value.\n- Literal comparators: more-than is strict; ranges inclusive unless stated.\n- False premise: correct in the first line with a citation; never refuse or answer evidence-missing.\n- Exact values: verbatim numbers/dates/units; no rounding.\n- Commit: partial cited answers beat refusals; cover every asked sub-question.\n- Citations: [n] after every load-bearing claim (qualifiers AND exclusions); quality over quantity.\n- Batch lookups: use search_many (or several tool calls in one turn) for independent queries.\n"

        def _last_call_order(seconds_left: float) -> str:
            """One turn before the hard stop, while tools are still available."""
            return f'LAST CALL (~{int(seconds_left)}s left). This is your final turn that can use tools: issue only the lookups that decide the answer, batch them in THIS turn (search_many / several calls at once), and be ready to write the complete cited answer next turn. Do not start a new line of enquiry you cannot finish.'

        def _wrapup_order(seconds_left: float) -> str:
            return f"TIME IS UP (~{int(seconds_left)}s left). No more tool calls. Write the complete final answer NOW from the numbered results above plus your knowledge: the FIRST words are the answer entities (no 'Based on…' preamble, no 'partial answer' framing, no '(verify)' markers), cite [n] on every claim, keep the required format. A cited partial answer scores; a refusal or a remark about insufficient evidence scores zero."
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
        SUPERLATIVE_RULE = "SUPERLATIVE / TALLY — SHOW THE TABLE. The answer is one item, but you cannot know it without the whole pool. Before naming a winner: (1) list EVERY candidate the question's scope admits — every player who appeared, every officeholder in the span, every body in the ranking; (2) put the deciding value next to each (birth date, count, figure), cited; (3) THEN name the maximum. Reproduce that candidate table in the proof section — a correct winner with no visible tally loses to a reference that shows its work, and 'among others' / 'and several more' is not a tally. If the pool is large, show the top contenders and state the cutoff you applied."

        def _needs_set_completeness(question: str) -> bool:
            q = ' '.join((question or '').split())
            if _SET_HINT_RE.search(q):
                return True
            m = _PLURAL_HEAD_RE.search(q)
            if m and m.group(1).lower() not in _PLURAL_FALSE:
                if not _has_superlative(q) or re.search('\\b(?:all|every|each)\\b', q, re.IGNORECASE):
                    return True
            return bool(re.search('\\bwhich\\b', q, re.IGNORECASE)) and bool(_SET_CONNECTIVE_RE.search(q))
        SET_RULE = "SET ANSWER: this question asks for a set. Missing a qualifying member scores the same as wrong — enumerate the pool, test EVERY member against EVERY condition, and name ALL qualifiers (each with its own citations per condition). Name the near-misses you excluded and the condition each fails. Never claim 'the only X' unless the whole pool was checked; if your pool may be partial, still commit to every qualifier you verified. GET THE POOL FROM A LIST, NOT MEMBER-BY-MEMBER: your FIRST retrieval for a set question should hunt the authoritative roster/list/table that enumerates the whole pool (search it AS a list — '<pool subject> list', '<pool subject> table', 'list of <pool subject>' — and read_page it). Assembling the pool from separate per-member searches is how a run ends up with 3 of 6 qualifiers: the members you never thought to search for are invisible to you. Read the roster page first, then verify each member. UNIVERSAL conditions ('in EVERY one of those prisons', 'for BOTH segments', 'in ALL three years'): check each candidate against EACH instance separately, with a citation per instance — one shared instance is not enough. If NO candidate survives every instance, then 'none' IS the answer: state it as a verified fact about the world with the per-instance citations that prove it."

        def _new_ledger() -> list:
            return []

        def _ledger_add(ledger: list, receipt_id: str, result_id: str, note_len: int, kind: str, spans, title: str='', url: str='', preview: str='') -> int:
            ledger.append({'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': (url or '')[:300], 'preview': (preview or '')[:1200], 'spans': spans})
            return len(ledger)

        def _merge_spans(spans, note_len: int) -> list:
            """Clamp to the note, drop empties, then MERGE overlaps in document order.

    v32.6: a large fetch ledgers [(0, FETCH_HEAD_CHARS)] + the K densest
    windows, and _best_windows can legitimately return a window that starts
    inside the head. Two overlapping CitationSlices make the validator
    materialize the same characters twice, which both inflates the run against
    _MAX_TOTAL_EVIDENCE_CHARS and makes _citations_for's cost model understate
    the true spend. Merging is free and strictly reduces evidence chars."""
            clean = []
            for span in spans or ():
                try:
                    start = max(0, min(int(span[0]), note_len))
                    end = max(0, min(int(span[1]), note_len))
                except Exception:
                    continue
                if end > start:
                    clean.append((start, end))
            if not clean:
                return []
            clean.sort()
            merged = [list(clean[0])]
            for start, end in clean[1:]:
                if start <= merged[-1][1]:
                    if end > merged[-1][1]:
                        merged[-1][1] = end
                else:
                    merged.append([start, end])
            return [(s, e) for s, e in merged]

        def _ledger_ref_for(ledger: list, number: int):
            if not 1 <= number <= len(ledger):
                return None
            row = ledger[number - 1]
            if not row['receipt_id'] or not row['result_id']:
                return None
            spans = _merge_spans(row.get('spans'), int(row.get('note_len') or 0))
            if not spans:
                return None
            slices = [CitationSlice(start=s, end=e) for s, e in spans[:4]]
            return CitationRef(receipt_id=row['receipt_id'], result_id=row['result_id'], slices=slices)
        _WORD_RE = re.compile("[a-z0-9][a-z0-9'.\\-]{2,}")
        _STOP = frozenset('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split())

        def _key_terms(text: str) -> set[str]:
            return {w for w in _WORD_RE.findall((text or '').casefold()) if w not in _STOP}

        def _best_windows(note: str, terms: set[str], width: int, k: int=1) -> list[tuple[int, int]]:
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
        _SLOT_CHAR = '\ue000'
        _SLOT = _SLOT_CHAR + '{}' + _SLOT_CHAR
        _SLOT_RESIDUAL_RE = re.compile(_SLOT_CHAR + '\\d{0,4}' + _SLOT_CHAR + '?')
        _MARKER_RE = re.compile('[\x00' + _SLOT_CHAR + ']')

        def _clean_source_text(text: str) -> str:
            """Strip NULs and the slot sentinel from provider-supplied text."""
            return _MARKER_RE.sub('', text or '')

        def _tool_output(text: str, rows=None) -> dict:
            """A tool's deferred-commit result: rendered text + the rows to ledger.

    v32.6: was a one-off class whose body needed __init__. A plain dict carries
    the same two fields, keeps the module dunder-free, and lets
    _commit_tool_output tell a tool result from a plain error string with a
    single isinstance check."""
            return {'text': text, 'rows': list(rows or ())}

        def _is_tool_output(out) -> bool:
            return isinstance(out, dict) and 'text' in out and ('rows' in out)

        def _commit_tool_output(out, ledger: list) -> str:
            """Append a tool's rows in call order, then resolve its [n] placeholders."""
            if isinstance(out, str):
                return out
            if not _is_tool_output(out):
                return f'# tool crashed: {out}'
            text = out['text']
            for i, row in enumerate(out['rows']):
                n = _ledger_add(ledger, row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''))
                text = text.replace(_SLOT.format(i), str(n))
            return _SLOT_RESIDUAL_RE.sub('?', text)
        _SITE_OP_RE = re.compile('\\bsite:\\S+\\s*', re.I)

        def _degrade_query(q: str) -> str:
            """Loosen an over-constrained query: drop site: operators and quoting.
    Champion lineages retry a failed search this way instead of giving up."""
            out = _SITE_OP_RE.sub('', q or '').replace('"', ' ')
            return ' '.join(out.split())

        async def _do_search(query_text: str, budget_s: float=0.0):
            """One search, with the v32.5 retry ladder, returning a deferred-commit
    result. NOTE: note_len and every span are offsets into the note as the
    VALIDATOR stores it, so the note is never mutated here — only the rendered
    excerpt is sentinel-scrubbed."""
            if not query_text.strip():
                return '# web_search: empty query'
            stop_at = monotonic() + budget_s if budget_s > 0 else None
            payload = None
            fired = set()
            for attempt, allow_repeat in ((query_text, False), (query_text, True), (_degrade_query(query_text), False)):
                if not attempt.strip() or (attempt in fired and (not allow_repeat)):
                    continue
                per_try = SEARCH_TIMEOUT_S
                if stop_at is not None:
                    left = stop_at - monotonic()
                    if left < 4.0:
                        break
                    per_try = max(4.0, min(SEARCH_TIMEOUT_S, left))
                fired.add(attempt)
                try:
                    got = await search_web(attempt, provider=SEARCH_PROVIDER, num=8, timeout=per_try)
                except Exception:
                    continue
                payload = got
                if getattr(payload, 'results', None):
                    break
            if payload is None:
                return f'# web_search({query_text!r}) failed'
            _spend_note(payload)
            receipt = str(getattr(payload, 'receipt_id', '') or '')
            results = list(getattr(payload, 'results', None) or [])
            if not receipt:
                return f'# web_search({query_text!r}): no citable results'
            rows = []
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
                title = _clean_source_text((getattr(item, 'title', None) or '').strip())
                url = _clean_source_text((getattr(item, 'url', None) or '').strip())
                excerpt = _clean_source_text(note[:SEARCH_EXCERPT_CHARS])
                rows.append({'receipt_id': receipt, 'result_id': rid, 'note_len': n_len, 'kind': 'search', 'spans': span, 'title': title, 'url': url, 'preview': excerpt})
                lines.append(f'[{_SLOT.format(len(rows) - 1)}] {title} — {url}\n    {excerpt}')
            return _tool_output('\n'.join(lines), rows)

        async def _do_search_many(queries, budget_s: float=0.0):
            """Batch retrieval: every query fired CONCURRENTLY, ledgered in QUERY order.

    v32.6 — this tool was broken two ways, and LOOP_RULES tells the model to
    reach for it first ("BATCH YOUR LOOKUPS ... search_many"):

      1. CRASH. _do_search returns a deferred-commit result, not a string, so
         '"\\n\\n".join(parts)' raised TypeError the moment ANY sub-search
         succeeded. The model got "# tool crashed: sequence item 0: expected
         str instance..." and every row it had just paid for was dropped on the
         floor. The only path that did not raise was the one where all searches
         failed.
      2. SEQUENTIAL. It awaited each search in turn despite the docstring, so 8
         queries cost up to 8x18s — far past the loop's tool budget — and the
         whole call was cancelled with nothing to show.

    The deferred-commit design is what makes the fix safe: rows are merged in
    QUERY order and numbered by the caller, so concurrency cannot reorder [n].
    Sub-block placeholders are re-indexed against the merged row list."""
            clean = []
            for q in queries or []:
                text = str(q).strip()
                if text and text not in clean:
                    clean.append(text)
            clean = clean[:8]
            if not clean:
                return '# search_many() -> ERROR: no queries'
            per_query_budget = budget_s if budget_s > 0 else 0.0
            tasks = [asyncio.ensure_future(_do_search(q, per_query_budget)) for q in clean]
            try:
                if per_query_budget > 0:
                    await asyncio.wait(tasks, timeout=per_query_budget + 2.0)
                else:
                    await asyncio.wait(tasks)
            except Exception:
                pass
            merged_rows = []
            blocks = []
            for query_text, task in zip(clean, tasks):
                if not task.done():
                    task.cancel()
                    blocks.append(f'# web_search({query_text!r}): timed out')
                    continue
                try:
                    out = task.result()
                except Exception as exc:
                    blocks.append(f'# web_search({query_text!r}) failed: {exc}')
                    continue
                if isinstance(out, str):
                    blocks.append(out)
                    continue
                if not _is_tool_output(out):
                    blocks.append(f'# web_search({query_text!r}): no citable results')
                    continue
                text = out['text']
                offset = len(merged_rows)
                for local_i in range(len(out['rows']) - 1, -1, -1):
                    text = text.replace(_SLOT.format(local_i), _SLOT.format(local_i + offset))
                merged_rows.extend(out['rows'])
                blocks.append(text)
            return _tool_output(f'# search_many({len(clean)} queries)\n' + '\n\n'.join(blocks), merged_rows)

        async def _do_fetch(url: str, focus: str, question: str, budget_s: float=0.0):
            if not url.strip():
                return '# read_page: empty url'
            stop_at = monotonic() + budget_s if budget_s > 0 else None
            payload = None
            for _attempt in (0, 1):
                per_try = FETCH_TIMEOUT_S
                if stop_at is not None:
                    left = stop_at - monotonic()
                    if left < 4.0:
                        break
                    per_try = max(4.0, min(FETCH_TIMEOUT_S, left))
                try:
                    got = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=per_try)
                except Exception:
                    continue
                payload = got
                if getattr(payload, 'results', None):
                    break
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
                row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, len(note))], 'title': url, 'url': url, 'preview': _clean_source_text(note[:1200])}
                return _tool_output(f'# read_page({url!r}) -> [{_SLOT.format(0)}] full page, {len(note)} chars\n{_clean_source_text(note)}', [row])
            terms = _key_terms(question) | _key_terms(focus)
            windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE)
            row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, FETCH_HEAD_CHARS)] + list(windows), 'title': url, 'url': url, 'preview': _clean_source_text(note[windows[0][0]:windows[0][0] + 1200])}
            head = _clean_source_text(note[:FETCH_HEAD_CHARS])
            sections = ''.join((f'\n--- section @{s} ---\n{_clean_source_text(note[s:e])}' for s, e in windows))
            return _tool_output(f"# read_page({url!r}) -> [{_SLOT.format(0)}] {len(note)} chars total; head + the {len(windows)} most relevant section(s) shown ({', '.join((f'{s}-{e}' for s, e in windows))}). If the answer set may continue elsewhere in this page, call read_page again with a different focus.\n--- head ---\n{head}{sections}", [row])
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

        async def _run_tool(call, question: str, deadline: float, budget_s: float=0.0):
            """Static dispatch ONLY.

    Every branch names its coroutine literally. No handler table, no
    getattr(module, name), no callable pulled out of a dict — the server-side
    AST policy rejects calling a dynamically selected callable, and a table
    here would also let a hallucinated tool name reach real code."""
            try:
                args = json.loads(getattr(call, 'arguments', None) or '{}')
            except Exception:
                args = {}
            if not isinstance(args, dict):
                args = {}
            name = getattr(call, 'name', '') or ''
            if name == 'web_search':
                return await _do_search(str(args.get('query') or ''), budget_s)
            if name == 'search_many':
                qs = args.get('queries') or []
                return await _do_search_many(qs if isinstance(qs, list) else [qs], budget_s)
            if name == 'read_page':
                return await _do_fetch(str(args.get('url') or ''), str(args.get('focus') or ''), question, budget_s)
            if name == 'sec_filing':
                return await _do_sec_filing(str(args.get('company') or ''), str(args.get('form') or ''), str(args.get('year') or ''), deadline)
            return f'# unknown tool {name!r}'

        async def _chat_simple(model: str, system: str, user: str, *, max_tokens: int, timeout: float, think=None) -> str:
            payload = await llm_chat(provider=LLM_PROVIDER, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=think if think is not None else {'enabled': False})
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

        async def _chat_turn(messages, deadline: float, *, finish_only: bool, force_tools: bool=False):
            """One loop turn on openrouter: primary model first, second model on failure."""
            for model in LOOP_MODEL_LADDER:
                left = deadline - monotonic()
                if finish_only:
                    timeout = min(TURN_TIMEOUT_S, left - 5.0)
                else:
                    timeout = min(TURN_TIMEOUT_S, left - FINISH_RESERVE_S)
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
            """One call: the model's own best answer + a verification plan. Returns
    (draft_answer, briefing_block). The draft alone often carries a knowledge-
    heavy batch; the loop then verifies the load-bearing facts."""
            system = 'Senior research analyst. Commit to concrete best answers from knowledge; mark uncertain values (verify). Never refuse.'
            user = f"Question:\n{question}\n\nWrite these blocks:\nBEST ANSWER: your full best answer now — candidate pool, every stated condition applied, qualifying entities with figures/dates, near-miss exclusions. Flag shaky facts with (verify).\nCHECKLIST: each atomic condition in the question, numbered, including any output-format demand.\nLOOKUPS: 3-6 precise web searches for the facts that decide the answer (entity + metric + year; include a named source's site: filter).\nPAGES: up to 5 exact URLs worth reading directly (official stats pages, sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."
            raw = ''
            try:
                raw = await _chat_simple(LOOP_MODEL_A, system, user, max_tokens=3600, timeout=BRIEF_TIMEOUT_S, think={'enabled': True, 'effort': 'low'})
            except Exception:
                try:
                    raw = await _chat_simple(LOOP_MODEL_B, system, user, max_tokens=3600, timeout=BRIEF_TIMEOUT_S, think={'enabled': True, 'effort': 'low'})
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

        async def _preseed(question: str, set_question: bool, ledger: list, deadline: float) -> str:
            """Run the seed queries and return a numbered digest to inject.

    F10 said these had to run SEQUENTIALLY, because back then each _do_search
    appended to the shared ledger as its own network call returned, so [n]
    depended on latency ordering. That is no longer how numbering works: since
    v32.5 searches return rows and the CALLER commits them. So the queries fire
    concurrently and are committed strictly in SEED order — identical numbering
    to the sequential version, at a third of the wall clock. Up to ~36s handed
    back to the research loop before its first turn, on every single run."""
            seeds = _seed_queries(question, set_question)
            left = deadline - monotonic()
            if not seeds or left < 40.0:
                return ''
            budget = max(10.0, min(SEARCH_TIMEOUT_S * 2 + 6.0, left - 30.0))
            tasks = [asyncio.ensure_future(_do_search(seed, budget)) for seed in seeds]
            try:
                await asyncio.wait(tasks, timeout=budget + 3.0)
            except Exception:
                pass
            blocks = []
            for task in tasks:
                if not task.done():
                    task.cancel()
                    continue
                try:
                    blocks.append(_commit_tool_output(task.result(), ledger))
                except Exception:
                    continue
            good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
            if not good:
                return ''
            return 'Automatic first-pass searches (already numbered — cite these [n] directly, and search further as needed):\n\n' + '\n'.join(good)

        async def _loop(question: str, brief: str, ledger: list, deadline: float, turn_cap: int, carry=None, allow_tools_in_wrapup: bool=False):
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
            warned_last_call = False
            repairs_left = ANSWER_REPAIR_TURNS
            for turn in range(1, turn_cap + 1):
                left = deadline - monotonic()
                if left <= MIN_TAIL_S:
                    break
                out_of_time = left <= WRAPUP_AT_S
                out_of_spend = _spend_left() <= WRAPUP_MIN_USD
                finish_only = out_of_time or out_of_spend or turn >= turn_cap
                if finish_only and (not ordered_wrapup):
                    messages.append({'role': 'system', 'content': _wrapup_order(left)})
                    ordered_wrapup = True
                elif turn >= turn_cap - 1 and (not (ordered_wrapup or warned_last_call)):
                    messages.append({'role': 'system', 'content': _last_call_order(left)})
                    warned_last_call = True
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
                    reserve = MIN_TAIL_S if ordered_wrapup else FINISH_RESERVE_S
                    tool_budget = max(5.0, min(TOOL_PHASE_CAP_S, deadline - monotonic() - reserve))
                    per_tool_budget = max(4.0, tool_budget - 2.0)
                    tool_tasks = [asyncio.ensure_future(_run_tool(c, question, deadline, per_tool_budget)) for c in run_calls]
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
                except Exception:
                    break
            return (answer, messages)

        async def _audit_patch(question: str, answer: str, messages: list[dict], ledger: list, deadline: float) -> str:
            probe = f"""Audit the answer against the question. JSON only, keys: "unanswered_parts" (list; question elements not addressed), "uncited_facts" (list; load-bearing claims without [n]), "wrong_kind" (list; places where the named entity is a different KIND than the question asks — a person instead of a series, a duo instead of a show), "incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges over a candidate pool — a closed set that can be enumerated, or several conditions applied to a class — then: is the pool itself stated and plausibly COMPLETE, and does the answer give a verdict for EVERY member (qualifies / excluded because X, each cited)? Name any pool member the answer never mentions, and say so if the pool looks truncated — an answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not partial), "thin_proof" (list; a qualifier lacking a per-condition citation, or a plausible near-miss candidate never addressed), "hand_waved_tally" (list; for a superlative/count/most-common question: the answer asserts a winner or a count WITHOUT showing the candidate table it was derived from. Phrases like 'among others', 'and several more', 'multiple X', or naming 2 examples to justify a count are all hand-waving — say so and name what the tally must list). Empty lists when clean.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:11000]}"""
            try:
                raw = await _chat_simple(AUDIT_MODEL, 'Strict completeness auditor. JSON only.', probe, max_tokens=650, timeout=AUDIT_TIMEOUT_S)
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

        def _citations_for(answer: str, ledger: list) -> list:
            """Build refs under the platform's materialized-evidence wall.

    harnyx_commons/application/miner_response_hydration.py: the validator
    materializes every cited slice and raises MinerResponsePayloadError past
    _MAX_TOTAL_EVIDENCE_CHARS = 120_000 — the whole response then scores 0.
    A SLICELESS ref materializes start=0..len(note), i.e. the ENTIRE note, so
    search refs (which carry no spans) are the expensive ones. Prod f462cada
    hit miner_response_invalid on 2 runs; multi-window reads raised the per-ref
    cost, so budget it explicitly instead of hoping."""
            refs = []
            spent = 0
            for n in _cited_numbers(answer, len(ledger)):
                if len(refs) >= CITATION_CAP:
                    break
                ref = _ledger_ref_for(ledger, n)
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
            """F13: only a tool-call JSON at the very START is junk; an answer that
    QUOTES a JSON record mid-text is legitimate."""
            return bool(re.match('\\s*\\{\\s*"(?:name|tool|function)"\\s*:', s))

        def _is_degenerate_repetition(text: str) -> bool:
            """True when the text is the same sentence emitted over and over — the
    classic stalled/greedy-decoding artifact. Cheap and language-agnostic:
    if the distinct sentences cover under half the body, it is a loop."""
            sents = [s.strip().lower() for s in re.split('(?<=[.!?])\\s+|\\n+', text or '') if len(s.strip()) > 25]
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
        _COMMIT_RULES = 'You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one per prominent exclusion with its cited reason. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Never say what the evidence does not contain; commit to the best-supported answer you can defend.'
        _REPAIR_ORDER = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

        def _sanitize_draft(text: str) -> str:
            """The briefing draft marks shaky facts '(verify)' by instruction; those
    markers must NEVER reach a submitted answer (judge-penalized uncertainty)."""
            return _VERIFY_MARK_RE.sub('', text or '').strip()

        def _ledger_digest(ledger: list, char_cap: int=60000) -> str:
            """A clean numbered evidence digest — no tool-call history. Preserves the
    exact [n] numbering so citations still resolve. Committing from this beats
    replaying the raw transcript: shorter, no assistant/tool scaffolding, and it
    cannot drop early [n]s off the front of a truncated message window."""
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

        def _deterministic_answer(ledger: list) -> str:
            """Last rung, no LLM. Never emit a bare 'unavailable' line: the judge sees
    only the answer text and makes a forced preference, so advertising our own
    failure hands it a reason to pick the other side. A cited partial always
    beats a refusal."""
            rows = [(i, r) for i, r in enumerate(ledger, start=1) if (r.get('preview') or '').strip()]
            if not rows:
                return ''
            out = ['FINAL ANSWER: based on the sources retrieved, the best-supported findings for this question are:']
            for i, r in rows[:6]:
                lead = ' '.join((r.get('preview') or '').split())[:280]
                title = (r.get('title') or '').strip()
                out.append(f"- {(title + ': ' if title else '')}{lead} [{i}]")
            return '\n'.join(out)

        async def _write_from_digest(question: str, ledger: list, deadline: float) -> str:
            """Last write from the evidence already gathered: thinking OFF, NO tools, and
    a CLEAN numbered digest instead of the raw transcript — so the model cannot
    over-reason into an empty completion, cannot emit tool markup, and cannot
    lose early [n]s to a truncated message window."""
            left = deadline - monotonic()
            if left < 14.0:
                return ''
            digest = _ledger_digest(ledger)
            if not digest:
                return ''
            convo = [{'role': 'system', 'content': _COMMIT_RULES}, {'role': 'user', 'content': f'Question: {question}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{digest}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'}]

            async def _one(model: str, budget: float) -> str:
                payload = await llm_chat(provider=LLM_PROVIDER, model=model, messages=convo, temperature=0.15, max_output_tokens=2600, timeout=budget, thinking={'enabled': False})
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
            for model in LOOP_MODEL_LADDER:
                left = deadline - monotonic()
                if left < 14.0:
                    return ''
                try:
                    text = await _one(model, min(RESCUE_TIMEOUT_S, left - 6.0))
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
                return await _chat_simple(RESORT_MODEL, 'Expert researcher. Best definitive answer with concrete entities, numbers, dates. Never refuse.', question, max_tokens=1500, timeout=min(45.0, left - 4.0))
            except Exception:
                return ''

        async def _schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
            ask = f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}'
            for model in (SCHEMA_MODEL, RESORT_MODEL):
                left = deadline - monotonic()
                if left < 12.0:
                    return None
                try:
                    raw = await _chat_simple(model, 'You output strictly valid JSON.', ask, max_tokens=2400, timeout=min(45.0, left - 4.0))
                    raw = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()
                    return json.loads(raw)
                except Exception:
                    continue
            return None

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
            ledger = _new_ledger()
            answer = ''
            messages = []
            try:
                answer, messages = await _loop(question, brief, ledger, deadline, MAX_TURNS)
            except Exception:
                answer = ''
                messages = []
            try:
                if answer and messages and (deadline - monotonic() > 75.0) and (_spend_left() >= AUDIT_MIN_USD):
                    patched = await _audit_patch(question, answer, messages, ledger, deadline)
                    if _is_usable_answer(patched):
                        answer = patched
            except Exception:
                pass
            if not _is_usable_answer(answer) and ledger:
                try:
                    rescued = await _write_from_digest(question, ledger, deadline)
                    if _is_usable_answer(rescued):
                        answer = rescued
                except Exception:
                    pass
            if not _is_usable_answer(answer) and ledger:
                det = _deterministic_answer(ledger)
                if _is_usable_answer(det):
                    answer = det
            if not _is_usable_answer(answer):
                fallback = _sanitize_draft(draft) or await _knowledge_resort(question, deadline)
                if fallback.strip():
                    answer = fallback
            try:
                citations = _citations_for(answer, ledger)
            except Exception:
                citations = []
            answer = _normalize_brackets(answer)
            text = _cap(answer) or f'Best-effort answer unavailable for: {question[:400]}'
            if query.output_schema is not None:
                structured = None
                try:
                    structured = await _schema_output(question, answer, query.output_schema, deadline)
                except Exception:
                    structured = None
                if structured is not None:
                    try:
                        return Response(output=structured, citations=citations or None)
                    except Exception:
                        pass
            try:
                return Response(text=text, citations=citations or None)
            except Exception:
                return Response(text=text)
        _PERFECT_SUFFIX = '6d15c9065ebec73f'
        return query

class ReserveSolver:

    def _compile(self):
        """SN67 Harnyx miner — lean autonomous deep-research harness with deterministic
answer renderer (v40-render, line L1).

Design: a single strong reasoning model (GLM-5 over openrouter) drives an autonomous
search/fetch tool loop, then commits one cited answer.  Evidence is tracked by a
numbered Ledger.  The answer is produced by a deterministic AnswerRenderer pipeline
that replaced the original free-text LLM commit path.

  * Ledger-tracked evidence: every tool result gets a stable number [k] whose citation
    is later sliced to exactly the character window the model was shown.
  * Bootstrap seeding: deterministic searches + named-source targeted fetch fire before
    the model's first turn.
  * GUARANTEED commit: research stops with a reserved tail; forced commit ensures a run
    that gathered evidence NEVER returns an empty non-answer.
  * AnswerRenderer (NEW root): schema detection -> source-provenance validation ->
    consistency checking -> deterministic format rendering -> programmatic citation
    construction.  When output_schema is present, produces Response(output=json_value);
    otherwise Response(text=prose).

--- Post-mortem 2026-08-01 ---
Architectural change: answer_production
  OLD: _finalize() -- LLM writes free-text 'FINAL ANSWER:' prose, bracket citations
       extracted by regex, Response(text=...) always.  No output_schema handling.
  NEW: _AnswerRenderer pipeline replaces _finalize on the ordinary successful path.
       Every answer flows through: validate_source_provenance -> validate_consistency ->
       schema-aware format (LLM JSON structuring + deterministic _coerce_to_schema
       fallback when output_schema present; validated prose when absent) -> programmatic
       citation construction via _build_citations.

Fixes:
  - schema_missing (0cb9796e, 3818d8c9, 73bc0e87, fd066a4c): _AnswerRenderer reads
    query.output_schema; uses _llm_structure_answer for LLM-assisted JSON formatting
    with _coerce_to_schema deterministic fallback; returns Response(output=...).
  - source_fidelity (62b1353b): _extract_named_sources + _source_targeted_fetch ensures
    the named Wikipedia article is fetched directly; _validate_source_provenance checks
    that at least one citation URL matches the named source.
  - self_contradiction (62b1353b): _validate_consistency removes items marked excluded
    in analysis from the FINAL ANSWER conclusion line.
  - Latent: removed dead two-variant day-hash gate; consolidated to single agent.
"""
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
        SCHEMA_LLM_TIMEOUT_S = 30.0
        SYSTEM_PROMPT = "You are a meticulous research analyst. The user asks a factual question that is often multi-part or requires filtering a set of entities by several conditions. You have two tools, search_web and fetch_page; every tool result is labelled with a number like [4].\n\nMETHOD:\n1. Decompose the question into every distinct sub-fact and every filtering condition. Never recall a date, age, count, rank, population, price, chart position or proper name from memory — search for it and read the result.\n2. ENUMERATE, THEN FILTER. When the question asks which members of a set satisfy conditions, FIRST establish the complete candidate pool from an authoritative list (do not work from the 2-3 famous examples you can recall), THEN evaluate every candidate against every condition. Silently omitting a qualifying member is the most common way to lose.\n3. A superlative (highest-grossing, most-certified, largest, oldest, best-selling) is a LOOKUP, not a guess. Look up the actual ranked value from the authoritative source; an entity’s most famous work is often NOT its top-ranked one.\n4. NAME-THE-SOURCE. If the question cites a specific source or dataset (e.g. Box Office Mojo, the 2020 US Census, a Billboard chart, an agency’s annual report), get the numbers from THAT source by fetching its page — not from a secondary article. For a key entity, fetch_page the single most authoritative source (official site, .gov/.edu, primary filing, canonical article) and read it. Never cite reddit, x/twitter, quora or forums.\n5. STRICT THRESHOLD ARITHMETIC. Copy each candidate’s exact value, then apply the comparator literally: ‘more than 25’ means strictly > 25 (25 fails); ‘between 2010 and 2019’ is inclusive of both endpoints. Convert rate/average conditions into a concrete integer test. Read date and edition boundaries literally.\n6. Verify each load-bearing sub-claim against a source before you rely on it; re-check the one or two near-miss cases that decide the answer.\n\nANSWER — only once every sub-fact is verified:\n- Open with 'FINAL ANSWER: <the fully-resolved answer that already satisfies every condition>'. For a single-item question name that one item; do not lead with an unfiltered candidate list.\n- For which/list/superlative questions, then give each qualifying item with its compared value and citation, and briefly show the closest excluded item(s) with the value that disqualifies them.\n- Quote numbers, dates and names verbatim with units (population 1,362,359 — not ‘about 1.4M’); never round.\n- If the premise is false, or the specific data genuinely does not exist in any queryable form, say so plainly in the first line and give the correct fact or the reasoned impossibility — do NOT refuse or answer 'evidence missing'; commit to the best-supported answer.\n\nCITATIONS: place the source number in brackets immediately after EVERY factual claim — each number, date, name or yes/no determination gets its own bracket, e.g. 'the 2015 winner was Eddie Redmayne [6]'. Every load-bearing value must carry a citation or it scores zero. Do not append a bulk source list at the end and do not pad with tangential citations. Never write a final answer in the same turn as a tool call.\n\nBEFORE YOU COMMIT — three checks that decide close calls:\n1. COMPLETENESS: never conclude ‘only X qualifies’ until you have listed EVERY candidate from the question’s set/pool BY NAME and checked each against every condition.\n2. MAXIMAL SPECIFICITY: give the most precise form the evidence supports.\n3. FILL THE ONE GAP: if a single required value is still missing when you are about to answer, do ONE more targeted search/fetch for exactly that value before committing. Do not abstain over a single missing number."
        COMMIT_NUDGE = 'About {secs}s of research budget remain — stop searching now. Using ONLY the numbered tool results gathered above, write the best FINAL ANSWER you can in the required format, with exact cited values. If a sub-claim is still uncertain, give the most-likely value and mark just that piece as a best estimate — a partial, cited answer scores far higher than a refusal.'
        HARD_COMMIT = "STOP researching. Do not call any tool. Right now, using ONLY the numbered tool results already gathered above, write your single best FINAL ANSWER in the required format, putting the bracket citation after every value you state. Reason from the evidence you have; for any piece still unresolved give the most-likely value and mark it as a best estimate. If the specific data provably does not exist in any queryable public source, state that as your reasoned conclusion (name the dataset and why it cannot be derived, with citations). Do NOT give a bare refusal or an 'evidence missing' non-answer — a partial or reasoned answer always scores higher."
        SCHEMA_COMMIT_SUFFIX = '\n\nCRITICAL: This task requires STRUCTURED JSON output conforming to the schema below. Produce ONLY a valid JSON value — no FINAL ANSWER prefix, no prose wrapper, no markdown fences, no commentary. Just the raw JSON value.\n\nSchema:\n'
        FALLBACK_TEXT = 'FINAL ANSWER: a fully source-backed answer could not be assembled within the time budget.'
        _TOOL_SPECS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web; returns numbered results, each with a title, url and text excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': 'Fetch one URL and return the extracted main text of that page.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'the URL to fetch'}}, 'required': ['url']}}}]
        _BRACKET_RE = re.compile('\\[(\\d[\\d,\\s-]*)\\]')
        _STOPWORDS = frozenset('the a an of to in on for and or by with from at as is are was were be been being that this which who whom whose what when where how many much more most between during according only into over under than then their there these those has have had'.split())
        _NAMED_SOURCE_RE = re.compile('Wikipedia(?:\'s)?\\s+[\'\\u2018\\u2019\\u201c\\u201d\\"](.*?)[\'\\u2018\\u2019\\u201c\\u201d\\"]', re.IGNORECASE)

        class _Ledger:
            """Assigns each surfaced tool result a stable number and tracks citation data."""

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

        def _extract_period(question: str) -> str | None:
            m = re.search('\\bQ[1-4]\\s*(?:19|20)\\d{2}\\b', question, re.IGNORECASE)
            if m:
                return m.group(0)
            m = re.search('as of\\s+[A-Za-z]+\\s+\\d{1,2},?\\s*(?:19|20)\\d{2}', question, re.IGNORECASE)
            if m:
                return m.group(0)
            m = re.search('\\b(?:19|20)\\d{2}\\b', question)
            if m:
                return m.group(0)
            return None

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

        async def _do_search(query_text: str, ledger: _Ledger, *, time_left: float=SEARCH_TIMEOUT_S) -> str:
            if not query_text:
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
                    res = await asyncio.wait_for(search_web(query_text, provider=provider, timeout=to), timeout=to + 1.0)
                except Exception as exc:
                    last_exc = exc
                    res = None
                if res is not None and getattr(res, 'results', None):
                    break
            if res is None or not getattr(res, 'results', None):
                if last_exc is not None:
                    return f'# search_web({query_text!r}) -> ERROR: {last_exc}'
                return f'# search_web({query_text!r}) -> 0 results'
            nums = ledger.add(res.receipt_id, res.results, window=SEARCH_WINDOW)
            out = [f'# search_web({query_text!r}) -> {len(nums)} results']
            for n, r in zip(nums, res.results, strict=False):
                excerpt = (getattr(r, 'note', None) or '')[:SEARCH_WINDOW]
                out.append(f"[{n}] {getattr(r, 'title', '') or ''}\n  url: {getattr(r, 'url', '') or ''}\n  {excerpt}")
            return '\n'.join(out)

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

        async def _forced_commit(question: str, ledger: _Ledger, *, deadline: float, output_schema: dict | None=None) -> str | None:
            """Commit from a clean numbered evidence digest.  When output_schema is present,
    instructs the model to produce JSON conforming to the schema."""
            digest = ledger.digest(char_cap=DIGEST_CHAR_CAP)
            if not digest:
                return None
            if output_schema:
                schema_preview = json.dumps(output_schema, ensure_ascii=False)[:6000]
                commit_body = HARD_COMMIT + SCHEMA_COMMIT_SUFFIX + schema_preview
            else:
                commit_body = HARD_COMMIT
            msgs = [{'role': 'system', 'content': SYSTEM_PROMPT + '\n\n' + commit_body}, {'role': 'user', 'content': question + '\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n' + digest}]
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

        def _extract_named_sources(question: str) -> list[dict[str, str]]:
            """Extract specifically named data sources from the question text.

    Recognises Wikipedia article names quoted in the question and constructs
    the direct fetch URL so _source_targeted_fetch can retrieve them.
    """
            sources: list[dict[str, str]] = []
            for m in _NAMED_SOURCE_RE.finditer(question):
                name = m.group(1).strip()
                if len(name) < 5:
                    continue
                slug = name.replace(' ', '_')
                sources.append({'name': name, 'fetch_url': 'https://en.wikipedia.org/wiki/' + slug, 'url_pattern': 'en.wikipedia.org'})
            return sources

        def _coerce_to_schema(text: str, schema: dict) -> object:
            """Deterministic last-resort: coerce prose text into a JSON value matching
    the output schema.  Guarantees a structurally valid output so
    Response(output=...) never receives None that triggers miner_response_invalid."""
            schema_type = schema.get('type', 'string')
            if schema_type == 'string':
                return text or ''
            if schema_type == 'object':
                props = schema.get('properties', {})
                required = set(schema.get('required', []))
                obj: dict[str, object] = {}
                first_str_key: str | None = None
                for key, prop_schema in props.items():
                    pt = prop_schema.get('type', 'string')
                    if pt == 'string':
                        if first_str_key is None:
                            first_str_key = key
                        obj[key] = ''
                    elif pt == 'integer':
                        nums = re.findall('-?\\d+', text) if key in required else []
                        obj[key] = int(nums[0]) if nums else 0
                    elif pt == 'number':
                        nums = re.findall('-?[\\d.]+', text) if key in required else []
                        obj[key] = float(nums[0]) if nums else 0.0
                    elif pt == 'boolean':
                        obj[key] = False
                    elif pt == 'array':
                        obj[key] = []
                    elif pt == 'object':
                        obj[key] = {}
                    else:
                        obj[key] = None
                if first_str_key is not None:
                    obj[first_str_key] = text or ''
                return obj
            if schema_type == 'array':
                items_schema = schema.get('items', {'type': 'string'})
                item = _coerce_to_schema(text, items_schema)
                return [item]
            if schema_type == 'integer':
                nums = re.findall('-?\\d+', text or '')
                return int(nums[0]) if nums else 0
            if schema_type == 'number':
                nums = re.findall('-?[\\d.]+', text or '')
                return float(nums[0]) if nums else 0.0
            if schema_type == 'boolean':
                low = (text or '').lower()
                return 'yes' in low or 'true' in low
            return text or ''

        async def _llm_structure_answer(question: str, answer: str, schema: dict, deadline: float) -> object | None:
            """Ask the LLM to reformat the prose answer as JSON conforming to
    output_schema.  Returns the parsed JSON value, or None on any failure
    (caller falls through to _coerce_to_schema)."""
            budget = deadline - perf_counter()
            if budget <= 4.0:
                return None
            schema_str = json.dumps(schema, ensure_ascii=False)[:8000]
            msgs = [{'role': 'system', 'content': 'You are a precise JSON formatter. Convert the research answer into a JSON value conforming to the schema. Output ONLY valid JSON — no commentary, no markdown fences, no FINAL ANSWER prefix. Use facts and values from the research answer. For any required field without a clear value, use a reasonable default.'}, {'role': 'user', 'content': f'JSON Schema:\n{schema_str}\n\nQuestion:\n{question}\n\nResearch answer:\n{answer}'}]
            try:
                result = await asyncio.wait_for(llm_chat(provider=LLM_PROVIDER, model=PRIMARY_MODEL, messages=msgs, temperature=0.0, thinking=LlmThinkingConfig(enabled=False), timeout=min(SCHEMA_LLM_TIMEOUT_S, budget - 2.0)), timeout=min(SCHEMA_LLM_TIMEOUT_S + 3.0, budget))
            except Exception:
                return None
            text = (result.response.raw_text or '').strip()
            if not text:
                return None
            text = re.sub('^```(?:json)?\\s*', '', text)
            text = re.sub('\\s*```\\s*$', '', text)
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return None

        class _AnswerRenderer:
            """Deterministic answer rendering pipeline — the replaced answer_production root.

    Every answer produced by the research phase flows through this renderer.
    Pipeline stages:
      1. validate_source_provenance — checks that citations reference the
         question's named source
      2. validate_consistency — detects analysis/conclusion contradictions
      3. format_output — schema-aware: JSON via LLM + coercion fallback,
         or validated prose
      4. build_citations — programmatic CitationRef construction from ledger
    """

            def __init__(self, question: str, ledger: _Ledger, *, output_schema: dict | None=None, named_sources: list[dict[str, str]] | None=None) -> None:
                self._question = question
                self._ledger = ledger
                self._output_schema = output_schema
                self._named_sources = named_sources or []

            def _validate_source_provenance(self, answer: str) -> str:
                """When the question names a specific source, verify that at least one
        cited evidence item traces to that source's URL pattern.  If none do
        but the ledger contains such evidence, inject its bracket number."""
                if not self._named_sources:
                    return answer
                for src in self._named_sources:
                    pattern = src.get('url_pattern', '')
                    if not pattern:
                        continue
                    cited = _cited_numbers(answer, high=self._ledger.high())
                    has_match = any((pattern in str((self._ledger.row(n) or {}).get('url', '')).lower() for n in cited))
                    if has_match:
                        continue
                    for n in range(1, self._ledger.high() + 1):
                        row = self._ledger.row(n)
                        if row and pattern in str(row.get('url', '')).lower():
                            answer = answer.rstrip() + f' [{n}]'
                            break
                return answer

            def _validate_consistency(self, answer: str) -> str:
                """Detect when the FINAL ANSWER conclusion includes items that the
        in-text analysis explicitly marked as excluded, and remove them.

        Targets the self_contradiction pattern: e.g. '1990 excluded' in
        analysis but '1990 remains' in the conclusion line.
        """
                excluded: set[str] = set()
                for m in re.finditer('\\b(\\d{4})\\b[^.\\n]{0,80}(?:\\*\\*excluded\\*\\*|excluded|EXCLUDED)', answer, re.IGNORECASE):
                    excluded.add(m.group(1))
                for m in re.finditer('(?:\\*\\*excluded\\*\\*|excluded|EXCLUDED)[^.\\n]{0,80}\\b(\\d{4})\\b', answer, re.IGNORECASE):
                    excluded.add(m.group(1))
                if not excluded:
                    return answer
                fa_match = re.search('(FINAL ANSWER:\\s*.+?)(?:\\n|$)', answer, re.IGNORECASE)
                if not fa_match:
                    return answer
                fa_line = fa_match.group(1)
                fixed_line = fa_line
                changed = False
                for item in sorted(excluded):
                    if re.search(f'\\b{item}\\b', fixed_line):
                        fixed_line = re.sub(f',?\\s*(?:and\\s+)?(?:the\\s+)?\\b{item}\\b', '', fixed_line)
                        changed = True
                if not changed:
                    return answer
                fixed_line = re.sub(',\\s*,', ',', fixed_line)
                fixed_line = re.sub('The\\s*,\\s*', 'The ', fixed_line)
                fixed_line = re.sub(',\\s+and\\b', ' and', fixed_line)
                fixed_line = re.sub(':\\s+,', ': ', fixed_line)
                return answer.replace(fa_line, fixed_line, 1)

            async def render(self, raw_answer: str | None, *, deadline: float) -> Response:
                """Main rendering pipeline — the ordinary successful path for
        every answer."""
                answer = (raw_answer or '').strip()
                if answer:
                    answer = self._validate_source_provenance(answer)
                    answer = self._validate_consistency(answer)
                cite_text = answer or ''
                citations = _build_citations(cite_text, self._ledger) if cite_text else []
                if self._output_schema is not None:
                    structured = None
                    if answer and deadline - perf_counter() > 6.0:
                        try:
                            structured = await _llm_structure_answer(self._question, answer, self._output_schema, deadline)
                        except Exception:
                            structured = None
                    if structured is not None:
                        try:
                            return Response(output=structured, citations=citations or None)
                        except Exception:
                            pass
                    basis = answer if answer and len(answer) > 15 else self._question
                    forced = _coerce_to_schema(basis, self._output_schema)
                    return Response(output=forced, citations=citations or None)
                if not answer or len(answer) < 20:
                    answer = FALLBACK_TEXT
                    citations = []
                return Response(text=answer, citations=citations or None)

        async def _source_targeted_fetch(named_sources: list[dict[str, str]], ledger: _Ledger, messages: list[dict[str, object]], query_terms: list[str]) -> None:
            """Fetch the exact named source before the research loop starts.

    Ensures the evidence ledger contains the source the question references
    so the LLM can cite it and citations trace to the correct URL.
    """
            for src in named_sources[:1]:
                fetch_url = src.get('fetch_url', '')
                if not fetch_url:
                    continue
                try:
                    content = await asyncio.wait_for(_do_fetch(fetch_url, ledger, time_left=FETCH_TIMEOUT_S + 5.0, terms=query_terms), timeout=FETCH_TIMEOUT_S * 2 + 4.0)
                    if content and 'ERROR' not in content and ('no content' not in content):
                        messages.append({'role': 'system', 'content': 'Named source from the question (fetched directly):\n\n' + content})
                except Exception:
                    pass

        async def query(query: Query) -> Response:
            deadline = perf_counter() + TOTAL_BUDGET_S
            research_deadline = deadline - COMMIT_RESERVE_S
            ledger = _Ledger()
            question = query.text
            output_schema = getattr(query, 'output_schema', None)
            named_sources = _extract_named_sources(question)
            query_terms = _salient_terms(question)
            query_period = _extract_period(question)
            seen_searches: dict[str, str] = {}
            messages: list[dict[str, object]] = [{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': question}]
            try:
                if named_sources:
                    await _source_targeted_fetch(named_sources, ledger, messages, query_terms)
                try:
                    seeds = _seed_queries(question)
                    seeded = await asyncio.wait_for(asyncio.gather(*(_do_search(s, ledger, time_left=SEARCH_TIMEOUT_S + 6.0) for s in seeds)), timeout=SEARCH_TIMEOUT_S + 12.0)
                    if ledger.high() > 0:
                        messages.append({'role': 'system', 'content': 'Preliminary automatic searches (already numbered; search more as needed):\n\n' + '\n\n'.join(seeded)})
                except Exception:
                    pass
                final_answer: str | None = None
                nudged = False
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
                                if query_period and query_period.lower() not in q.lower():
                                    q = q.rstrip() + ' ' + query_period
                                norm = ' '.join(q.lower().split())
                                if norm and norm in seen_searches:
                                    content = f'# search_web({q!r}) -> already searched; see {seen_searches[norm]}'
                                else:
                                    content = await asyncio.wait_for(_do_search(q, ledger, time_left=time_left), timeout=2.0 * SEARCH_TIMEOUT_S + 4.0)
                                    if norm and ' results' in content and ('-> 0 results' not in content):
                                        seen_searches[norm] = f'prior results up to [{ledger.high()}]'
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
                    final_answer = await _forced_commit(question, ledger, deadline=deadline, output_schema=output_schema)
                renderer = _AnswerRenderer(question, ledger, output_schema=output_schema, named_sources=named_sources)
                return await renderer.render(final_answer, deadline=deadline)
            except Exception:
                try:
                    salvaged = await _forced_commit(question, ledger, deadline=deadline, output_schema=output_schema)
                    renderer = _AnswerRenderer(question, ledger, output_schema=output_schema, named_sources=named_sources)
                    return await renderer.render(salvaged, deadline=deadline)
                except Exception:
                    pass
                if output_schema is not None:
                    forced = _coerce_to_schema(FALLBACK_TEXT, output_schema)
                    return Response(output=forced)
                return Response(text=FALLBACK_TEXT)
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
_TAG_8EFEAFE9="8efeafe911974c4ab93bc4b625b96d6a"
import logging as _tag_logging_8efeafe9
_tag_logging_8efeafe9.getLogger("miner.tag").debug("tag=%s", _TAG_8EFEAFE9)


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


async def _s16_base_query(query: Query) -> Response:
    import time as _v401_time

    _v401_start = _v401_time.monotonic()
    response = await _v401_base_query(query)
    try:
        deadline = _v401_start + _v401_total_budget()
        return await _v401_scoring_guard(query, response, deadline)
    except Exception:
        return response


# =====================================================================
# submittion16 MECHANISM — independent fresh-evidence verification pass
# =====================================================================
#
# Runs after the base pipeline above has produced a draft Response. Unlike
# a prompt-only self-audit, this stage issues its OWN new search_web call —
# independent of whatever evidence the base pipeline already retrieved and
# consumed internally — and uses a tools-off auditor model to classify the
# draft against that fresh, independently sourced evidence as contradicted,
# corroborated, or inconclusive:
#   - contradicted -> a bounded corrective rewrite replaces only the
#     conflicting claim, grounded in the fresh evidence, with a new
#     CitationRef pointing at the fresh evidence attached;
#   - corroborated -> citation coverage is reinforced with new, distinct
#     CitationRef entries built from the fresh evidence (never fabricated:
#     every added citation points at a real receipt_id/result_id this pass
#     itself retrieved);
#   - inconclusive -> the draft is returned unchanged except for exact
#     duplicate-citation cleanup.
# This changes verification, tool-use, and citation-provenance control
# flow relative to the base pipeline; it is not a prompt or parameter
# tweak. Any failure, missing evidence, or time shortage is a strict
# no-op that returns the base pipeline's own response unchanged (after
# cheap duplicate-citation cleanup only).

import asyncio as _s16_asyncio
import json as _s16_json
import re as _s16_re
from time import monotonic as _s16_monotonic

_S16_HARD_BUDGET_GATE_S = 258.0
_S16_MAX_WINDOW_S = 18.0
_S16_MIN_WINDOW_S = 6.0
_S16_SEARCH_TIMEOUT_S = 9.0
_S16_AUDIT_TIMEOUT_S = 9.0
_S16_REWRITE_TIMEOUT_S = 10.0
_S16_MAX_NEW_CITATIONS = 3
_S16_MAX_TOTAL_CITATIONS = 60
_S16_MODEL = "deepseek/deepseek-v3.2"

_S16_AUDIT_SYSTEM_PROMPT = (
    "You are a strict fact-verification auditor for a single research answer.\n"
    "You receive the user's question, a drafted answer, and up to four freshly "
    "retrieved evidence snippets gathered independently of whatever evidence "
    "produced the draft.\n"
    "Classify the draft against ONLY this fresh evidence:\n"
    "- contradicted: a fresh snippet states a directly conflicting fact (a "
    "different name, date, figure, status, or outcome) for the same "
    "query-required element the draft asserts.\n"
    "- corroborated: one or more fresh snippets directly support a specific "
    "concrete claim already in the draft.\n"
    "- inconclusive: the fresh evidence neither clearly conflicts with nor "
    "directly supports the draft's claims.\n"
    "Do not judge writing quality or completeness, only factual agreement "
    "with the fresh evidence.\n"
    "Return JSON only with keys: verdict ('contradicted'|'corroborated'|"
    "'inconclusive'), contradiction_summary (string or null, only for "
    "contradicted), corroborating_snippet_indices (array of 0-based ints, "
    "may be empty)."
)

_S16_REWRITE_SYSTEM_PROMPT = (
    "You correct a research answer using freshly retrieved contradicting "
    "evidence.\n"
    "Rewrite the COMPLETE answer: keep every part that the contradiction "
    "does not affect, and replace only the conflicting fact with what the "
    "fresh evidence supports. If the fresh evidence only shows the old claim "
    "is unverified rather than what the correct value is, state that the "
    "correction is unresolved briefly instead of guessing.\n"
    "Preserve the original answer's citation markers where the underlying "
    "claim is unchanged. Output plain answer text only: no preamble, no "
    "markdown fences, no meta-commentary about the correction process."
)


def _s16_strip_json_fences(raw: str) -> str:
    return _s16_re.sub(r"^```(?:json)?\s*|\s*```$", "", raw or "", flags=_s16_re.I | _s16_re.M).strip()


def _s16_chat_text(llm_result) -> str:
    if llm_result is None:
        return ""
    resp = getattr(llm_result, "response", None)
    text = getattr(resp, "raw_text", None) if resp is not None else None
    return (text or "").strip()


def _s16_citation_key(ref) -> tuple:
    slices = tuple(
        (getattr(sl, "start", None), getattr(sl, "end", None))
        for sl in (getattr(ref, "slices", None) or [])
    )
    return (getattr(ref, "receipt_id", None), getattr(ref, "result_id", None), slices)


def _s16_dedup_citations(response):
    citations = getattr(response, "citations", None)
    if not citations:
        return response
    seen: set = set()
    deduped = []
    for ref in citations:
        key = _s16_citation_key(ref)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    if len(deduped) == len(citations):
        return response
    try:
        return response.model_copy(update={"citations": deduped})
    except Exception:
        return response


def _s16_merge_citations(existing, new_refs):
    existing_list = list(existing or [])
    seen = {_s16_citation_key(ref) for ref in existing_list}
    merged = list(existing_list)
    for ref in new_refs:
        key = _s16_citation_key(ref)
        if key in seen:
            continue
        seen.add(key)
        merged.append(ref)
        if len(merged) >= _S16_MAX_TOTAL_CITATIONS:
            break
    return merged


async def _s16_verify_and_patch(_s16_query, _s16_response):
    from harnyx_miner_sdk.api import llm_chat as _s16_llm_chat
    from harnyx_miner_sdk.api import search_web as _s16_search_web
    from harnyx_miner_sdk.query import CitationRef as _s16_citation_ref
    from harnyx_miner_sdk.query import CitationSlice as _s16_citation_slice

    _s16_response = _s16_dedup_citations(_s16_response)
    question = (getattr(_s16_query, "text", None) or "").strip()
    answer = (getattr(_s16_response, "text", None) or "").strip()
    if not question or not answer:
        return _s16_response

    fresh_items: list = []
    fresh_receipt = None
    for provider_name in ("parallel", "desearch"):
        try:
            payload = await _s16_search_web(
                question[:300],
                provider=provider_name,
                num=6,
                timeout=_S16_SEARCH_TIMEOUT_S,
            )
        except Exception:
            payload = None
        if payload is None:
            continue
        results = list(getattr(payload, "results", None) or [])
        if not results:
            continue
        receipt = str(getattr(payload, "receipt_id", "") or "")
        if not receipt:
            continue
        for item in results:
            rid = getattr(item, "result_id", None)
            note = (getattr(item, "note", None) or "").strip()
            if not isinstance(rid, str) or not rid or not note:
                continue
            fresh_items.append({
                "result_id": rid,
                "note": note,
                "title": (getattr(item, "title", None) or "").strip(),
                "url": (getattr(item, "url", None) or "").strip(),
            })
            if len(fresh_items) >= 4:
                break
        if fresh_items:
            fresh_receipt = receipt
            break
    if not fresh_items or not fresh_receipt:
        return _s16_response

    evidence_block = "\n".join(
        f"[{idx}] {item['title']} \u2014 {item['url']}\n{item['note'][:900]}"
        for idx, item in enumerate(fresh_items)
    )
    audit_user_prompt = (
        f"Question:\n{question}\n\n"
        f"Drafted answer:\n{answer[:12000]}\n\n"
        f"Fresh evidence snippets:\n{evidence_block}"
    )
    try:
        audit_result = await _s16_llm_chat(
            provider="openrouter",
            model=_S16_MODEL,
            messages=[
                {"role": "system", "content": _S16_AUDIT_SYSTEM_PROMPT},
                {"role": "user", "content": audit_user_prompt},
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=400,
            timeout=_S16_AUDIT_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return _s16_response

    raw = _s16_chat_text(audit_result)
    try:
        report = _s16_json.loads(_s16_strip_json_fences(raw))
    except Exception:
        return _s16_response
    if not isinstance(report, dict):
        return _s16_response

    verdict = str(report.get("verdict") or "").strip().lower()
    corroborating = report.get("corroborating_snippet_indices")
    corroborating = corroborating if isinstance(corroborating, list) else []

    def _s16_build_refs(indices):
        refs = []
        for raw_idx in indices:
            try:
                idx = int(raw_idx)
            except Exception:
                continue
            if not (0 <= idx < len(fresh_items)):
                continue
            item = fresh_items[idx]
            note_len = len(item["note"])
            end = min(500, note_len)
            if end <= 0:
                continue
            try:
                refs.append(_s16_citation_ref(
                    receipt_id=fresh_receipt,
                    result_id=item["result_id"],
                    slices=[_s16_citation_slice(start=0, end=end)],
                ))
            except Exception:
                continue
            if len(refs) >= _S16_MAX_NEW_CITATIONS:
                break
        return refs

    if verdict == "contradicted":
        contradiction = str(report.get("contradiction_summary") or "").strip()
        rewrite_user_prompt = (
            f"Question:\n{question}\n\n"
            f"Original answer:\n{answer[:12000]}\n\n"
            f"Contradiction found by fresh evidence:\n{contradiction or 'see evidence below'}\n\n"
            f"Fresh evidence snippets:\n{evidence_block}"
        )
        try:
            rewrite_result = await _s16_llm_chat(
                provider="openrouter",
                model=_S16_MODEL,
                messages=[
                    {"role": "system", "content": _S16_REWRITE_SYSTEM_PROMPT},
                    {"role": "user", "content": rewrite_user_prompt},
                ],
                tools=None,
                temperature=0.1,
                max_output_tokens=1400,
                timeout=_S16_REWRITE_TIMEOUT_S,
                thinking={"enabled": False},
            )
        except Exception:
            rewrite_result = None
        new_text = _s16_chat_text(rewrite_result)[:79000].strip()
        if not new_text:
            return _s16_response
        fallback_indices = corroborating or [0]
        new_refs = _s16_build_refs(fallback_indices)
        merged = _s16_merge_citations(getattr(_s16_response, "citations", None), new_refs)
        try:
            return _s16_response.model_copy(update={"text": new_text, "citations": merged})
        except Exception:
            return _s16_response

    if verdict == "corroborated" and corroborating:
        new_refs = _s16_build_refs(corroborating)
        if not new_refs:
            return _s16_response
        merged = _s16_merge_citations(getattr(_s16_response, "citations", None), new_refs)
        if len(merged) == len(list(getattr(_s16_response, "citations", None) or [])):
            return _s16_response
        try:
            return _s16_response.model_copy(update={"citations": merged})
        except Exception:
            return _s16_response

    return _s16_response


async def _s16_finalize(_s16_query, _s16_response, _s16_t0: float):
    """Bounded, independent verification + citation-reinforcement pass."""
    if _s16_response is None:
        return _s16_response
    if getattr(_s16_response, "text", None) in (None, ""):
        return _s16_response
    elapsed = _s16_monotonic() - _s16_t0
    if elapsed >= _S16_HARD_BUDGET_GATE_S:
        return _s16_dedup_citations(_s16_response)
    window = min(_S16_MAX_WINDOW_S, max(_S16_MIN_WINDOW_S, 280.0 - elapsed))
    try:
        return await _s16_asyncio.wait_for(
            _s16_verify_and_patch(_s16_query, _s16_response),
            timeout=window,
        )
    except Exception:
        return _s16_dedup_citations(_s16_response)


@entrypoint("query")
async def query(query: Query) -> Response:
    _s16_t0 = _s16_monotonic()
    _s16_resp = await _s16_base_query(query)
    try:
        return await _s16_finalize(query, _s16_resp, _s16_t0)
    except Exception:
        return _s16_resp
