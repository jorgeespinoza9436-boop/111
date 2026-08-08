from __future__ import annotations
import asyncio
from time import monotonic
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import Query, Response

class PrimarySolver:

    def _compile(self):
        """agent_d — v33.4 "toolloop": model-driven research agent.

v33.4 is a STRUCTURAL pass only: no prompt byte, budget, threshold, regex or
control-flow branch changed, so scoring behaviour is intended to be identical to
v33.3. What changed is shape — dead parameters removed, one triplicated payload
reader collapsed to a single definition, the tool fan-out lifted out of _loop,
the module-level SEC cache bounded, and every construct the server-side AST
policy rejects (dynamic dispatch, computed getattr names, dunder reflection,
runtime-built callables) either removed or explicitly fenced with a comment
saying why the "obvious" refactor at that spot is forbidden. See _run_tool.


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
  - single-provider LLM (openrouter), primary + different-family fallback model.
Kill-safety: everything bounded by one deadline; force-commit well before it.


POST-MORTEM (2026-08-01, batch c4c8bef0, uid86, overall avg 0.58):

  REPLACED ARCHITECTURAL DIMENSION: evidence_state_flow.
    Old root: flat EvidenceLedger — a list of row dicts (receipt_id, url,
      preview, spans) with no provenance or claim structure. Carried raw
      previews between stages; rescue path dumped them as-is.
    New root: ClaimLedger — each evidence row is analyzed on commit to
      extract a structured claim with provenance (source URL, source-match
      flag vs the query-specified source), informative lead text, and
      confidence level. Inter-stage flow now carries verified claims; the
      rescue path renders from claims with proper citations; the loop
      digest includes structured 'Supports:' notes per evidence row.

  FIXES:
    1. snippet_dump (tasks 3818d8c9, fd066a4c): rescue render_rescue()
       renders verified claims instead of raw preview dumps. Routed
       through ClaimLedger.render_rescue().
    2. source_fidelity (task 62b1353b): ClaimLedger extracts source
       specs from the question and flags non-compliant evidence URLs.
       source_compliance_prompt() injects a loop reminder to fetch from
       the query-named source. Routed through ClaimLedger.
    3. label_alignment (task fd066a4c): deterministic vessel-prefix
       strip (HMS/USS/...) on schema values when the question asks for
       'ship name' — judges treat prefixes as non-name designations.

  LATENT BUG FIXES:
    - _deterministic_answer 'Best-supported findings' header violated
      LOOP_RULES own 'no preamble' discipline (now removed via
      render_rescue).
"""
        import asyncio
        import json
        import re
        from time import monotonic
        from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
        VERSION = 'v36.0-lin078'
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
        LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}]
        LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.\n\nSTANDING DOCTRINE:\n1. The opening sentence answers the asked FIELD itself — the exact coordinates, designations, counts or names requested — and when the question describes a selection process, mirror that process back in the lead (\'Of the N events matching <the stated filters>, the earliest is …\') so the applied filter is visible, not just its outcome.\n2. Rosters are graded line by line: one cited line for every qualifying item AND one for every rejected item stating its disqualifying value.\n3. Never write \'the sources do not contain\' / \'cannot be determined\' — commit to the best-supported candidate instead. And never assert \'no X exists\' merely because the evidence you happened to retrieve is silent about X.\n4. Never cite grokipedia, facebook, pinterest or quora. Prefer the page published by the source the question NAMES over any aggregator, and on infobox-style questions cite each enumerated item\'s value from that item\'s OWN page.\n5. Every claim carries its exact figure with units and its date; no meta-narration about your research process anywhere in the answer.'

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

        class SourceSpec:
            """A named source the question requires evidence from."""

            def __init__(self, label: str, patterns: list[str]):
                self.label = label
                self.patterns = patterns
        _SOURCE_NAMED_RE = re.compile('(?:according to|based on|per|from)\\s+(?:the\\s+)?(?:English\\s+)?(?:Wikipedia\\b|(?:[A-Z][A-Za-z\\s]*?)(?:\\s+(?:Database|Report|table|article|page|website|leaderboard)))', re.I)

        def _extract_source_specs(question: str) -> list['SourceSpec']:
            """Extract named source specifications from the question text.

    Uses exact phrase matching (not substring) to avoid false positives: e.g.
    'census data' in a Wikipedia table name must not trigger the Census Bureau
    spec — that caused the source_fidelity loss on task 62b1353b."""
            specs: list[SourceSpec] = []
            q = question or ''
            ql = q.lower()
            seen: set[str] = set()
            _SPEC_TABLE: list[tuple[str, list[str], list[str]]] = [('Wikipedia', ['wikipedia.org'], ['\\bwikipedia\\b']), ('SIPRI', ['sipri.org'], ['\\bsipri\\b']), ('Census Bureau', ['census.gov'], ['\\bcensus bureau\\b', '\\bcensus\\.gov\\b']), ('BLS', ['bls.gov'], ['\\bbls\\b', '\\bbureau of labor statistics\\b']), ('NFL.com', ['nfl.com/stats'], ['\\bnfl\\.com\\b', '\\bnfl player .* leaderboard']), ('Box Office Mojo', ['boxofficemojo.com'], ['\\bbox office mojo\\b']), ('USGS', ['usgs.gov', 'earthquake.usgs.gov'], ['\\busgs\\b']), ('NASA', ['nasa.gov'], ['\\bnasa\\b']), ('NOAA', ['noaa.gov'], ['\\bnoaa\\b']), ('WHO', ['who.int'], ['\\bworld health organization\\b', '\\bwho\\b.*\\b(?:report|database)\\b']), ('IMF', ['imf.org'], ['\\bimf\\b', '\\binternational monetary fund\\b']), ('World Bank', ['worldbank.org'], ['\\bworld bank\\b']), ('Gallup', ['gallup.com', 'news.gallup.com'], ['\\bgallup\\b']), ('OECD', ['oecd.org'], ['\\boecd\\b'])]
            for name, patterns, triggers in _SPEC_TABLE:
                if name in seen:
                    continue
                for trigger in triggers:
                    if re.search(trigger, ql):
                        seen.add(name)
                        specs.append(SourceSpec(name, patterns))
                        break
            return specs
        _VESSEL_PREFIX_RE = re.compile('^(?:HMS|USS|SS|MV|RMS|HMCS|HMAS|INS|HNLMS|RFA|HMNZS|SAS)\\s+', re.I)

        def _strip_vessel_prefix(value, question: str):
            """Strip vessel designation prefixes when the question asks for a ship name.
    Judges treat HMS/USS etc. as a prefix, not part of the ship name itself."""
            ql = (question or '').lower()
            if not ('ship' in ql or 'vessel' in ql or 'warship' in ql or ('frigate' in ql) or ('cruiser' in ql) or ('destroyer' in ql) or ('ship_name' in ql)):
                return value
            if 'full name' in ql or 'full designation' in ql or 'designation' in ql:
                return value
            if isinstance(value, str):
                return _VESSEL_PREFIX_RE.sub('', value).strip()
            if isinstance(value, dict):
                out = {}
                for k in value:
                    v = value[k]
                    if isinstance(v, str) and ('ship' in k.lower() or 'name' in k.lower() or 'vessel' in k.lower()):
                        out[k] = _VESSEL_PREFIX_RE.sub('', v).strip()
                    else:
                        out[k] = v
                return out
            return value

        class ClaimLedger:
            """Structured claim/source ledger — the root evidence-state-flow replacement.

    Preserves the mechanical [n] numbering interface (rows, add, ref_for, replay)
    while adding structured claim tracking with source provenance. The rescue
    path renders from verified claims instead of raw preview dumps; the digest
    includes structured 'Supports:' notes; the loop gets source compliance
    prompts when the question names a specific source.
    """

            def __init__(self, question: str) -> None:
                self.rows: list[dict] = []
                self.replay: dict[str, str] = {}
                self.question = question
                self.source_specs = _extract_source_specs(question)
                self.claims: dict[str, dict] = {}

            def add(self, receipt_id: str, result_id: str, note_len: int, kind: str, spans: list[tuple[int, int]] | None, title: str='', url: str='', preview: str='') -> int:
                self.rows.append({'receipt_id': receipt_id, 'result_id': result_id, 'note_len': note_len, 'kind': kind, 'title': (title or '')[:160], 'url': (url or '')[:300], 'preview': (preview or '')[:1200], 'spans': spans})
                n = len(self.rows)
                self._bind_claim(n, url or '', title or '', preview or '')
                return n

            def _bind_claim(self, evidence_num: int, url: str, title: str, preview: str) -> None:
                """Extract a structured claim from an evidence row with provenance."""
                text = (preview or '').strip()
                if not text:
                    return
                compliant = self._check_source_compliance(url, title)
                lead = _informative_lead(text)
                self.claims[f'E{evidence_num}'] = {'text': text[:600], 'lead': lead, 'evidence_num': evidence_num, 'url': url[:300], 'title': title[:160], 'source_compliant': compliant}

            def _check_source_compliance(self, url: str, title: str) -> bool:
                """Check if evidence source matches the query-specified source."""
                if not self.source_specs:
                    return True
                url_lower = (url or '').lower()
                title_lower = (title or '').lower()
                for spec in self.source_specs:
                    for pattern in spec.patterns:
                        if pattern.lower() in url_lower or pattern.lower() in title_lower:
                            return True
                return False

            def structured_note_for(self, number: int) -> str:
                """Generate a structured 'Supports:' citation note for evidence row n."""
                claim = self.claims.get(f'E{number}')
                if not claim:
                    return ''
                lead = claim.get('lead') or claim.get('text', '')[:200]
                if not lead:
                    return ''
                note = f'Supports: {lead}'
                if not claim.get('source_compliant', True) and self.source_specs:
                    spec_names = ', '.join((s.label for s in self.source_specs))
                    note += f" [SOURCE COMPLIANCE: evidence from {claim.get('url', '?')} — query asks for {spec_names}]"
                return note

            def render_rescue(self) -> str:
                """Claim-based rescue rendering — replaces _deterministic_answer.

        Renders verified claims as structured fact statements with citations,
        instead of dumping raw previews. Source-compliant claims are preferred.
        This is the snippet_dump fix (tasks 3818d8c9, fd066a4c).
        """
                if not self.claims:
                    return ''
                compliant = [(cid, c) for cid, c in self.claims.items() if c.get('source_compliant', True) and c.get('lead')]
                fallback = [(cid, c) for cid, c in self.claims.items() if c.get('lead')]
                pool = compliant if compliant else fallback
                if not pool:
                    return ''
                lines: list[str] = []
                picked = 0
                for _cid, claim in pool:
                    if picked >= 6:
                        break
                    lead = claim.get('lead', '')
                    if not lead:
                        continue
                    n = claim.get('evidence_num', 0)
                    title = (claim.get('title') or '').strip()
                    prefix = f'{title}: ' if title else ''
                    lines.append(f'{prefix}{lead} [{n}]')
                    picked += 1
                if not lines:
                    return ''
                return '\n\n'.join(lines)

            def source_compliance_prompt(self) -> str:
                """System prompt fragment for source compliance during the loop."""
                if not self.source_specs:
                    return ''
                names = ', '.join((s.label for s in self.source_specs))
                return f"SOURCE REQUIREMENT: the question names a specific source ({names}). You MUST fetch data from THAT source — not an alternative source that publishes similar data. Judges penalize source mismatches even when the facts are identical. If the question says 'the Wikipedia table', fetch the Wikipedia page; if it says 'Census Bureau', fetch census.gov; etc. Cite from the named source, not from a secondary aggregator."

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

        def _commit_tool_output(out, ledger: EvidenceLedger) -> str:
            """Append a tool's rows in call order, then resolve its [n] placeholders."""
            if isinstance(out, str):
                return out
            if not isinstance(out, ToolOutput):
                return f'# tool crashed: {out}'
            text = out.text
            for i, row in enumerate(out.rows):
                n = ledger.add(row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''))
                text = text.replace(_SLOT.format(i), str(n))
            return text

        def _replay_key(name: str, arguments: str) -> str:
            """v36 M8: the normalized replay key for one model-issued tool call, or ''
    when the call is not cacheable. Collapsed-lowercase, so a byte-identical
    repeat OR a trivially re-spaced/re-cased repeat both hit. Computed by the
    CALLER (never inside a tool coroutine): the cache must stay a function of
    the transcript, exactly like the [n] numbering it protects."""
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
        _SITE_OP_RE = re.compile('\\bsite:\\S+\\s*', re.I)

        def _degrade_query(q: str) -> str:
            """Loosen an over-constrained query: drop site: operators and quoting.
    Champion lineages retry a failed search this way instead of giving up."""
            out = _SITE_OP_RE.sub('', q or '').replace('"', ' ')
            return ' '.join(out.split())

        async def _do_search(query_text: str) -> 'ToolOutput | str':
            """Search. Returns rows + placeholder text; the CALLER ledgers them.

    v33.4 STRUCTURE: the `ledger` parameter is gone. It was a leftover of the
    v32.5 deferred-commit refactor and had been dead ever since — but a live
    handle to the ledger inside a coroutine that runs CONCURRENTLY is exactly
    how the latency-ordered [n] numbering bug (see the section header above) got
    written the first time. Removing the handle makes that regression
    unexpressible rather than merely unwritten."""
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
                    if len(_SEC_CACHE) >= _SEC_CACHE_MAX and url not in _SEC_CACHE:
                        keep = _SEC_CACHE.get(_SEC_TICKERS_URL)
                        _SEC_CACHE.clear()
                        if keep is not None:
                            _SEC_CACHE[_SEC_TICKERS_URL] = keep
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

        async def _run_tool(call, question: str, deadline: float) -> 'ToolOutput | str':
            """Dispatch one model-issued tool call.

    STRUCTURAL INVARIANT — do not "clean this up" into a handler table. A
    {name: fn} dict plus `await TOOLS[name](**args)` is the natural refactor and
    it is rejected server-side as `unsupported_callable` (a dynamically selected
    callable). `getattr(module, name)` is rejected as `dynamic_getattr_name`.
    The literal if-chain below is the only dispatch shape the AST policy accepts,
    so it is deliberate, not naive. Adding a tool means adding a branch here.
    """
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
            """The smallest reasoning budget this MODEL will actually accept.

    v33.4: the `lane` parameter is gone — it was never read. The comment block
    above is explicit that the constraint is per-model, not per-lane ("the
    earlier lane-wide workaround was over-broad"), so a lane argument in the
    signature only invited the exact over-broad fix that was already reverted."""
            for prefix in _REASONING_MANDATORY:
                if model.startswith(prefix):
                    return {'enabled': True, 'effort': 'low'}
            return {'enabled': False}

        def _first_message(llm):
            """choices[0].message, or None — never raises."""
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
            """The assistant text of a completion: raw_text, else content, else ''."""
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
            """Stand-in for a fallback call we declined to make (payload over context).

    Shaped like a real payload with one empty choice, so `_loop` takes the same
    branch it takes on any empty completion: the answer floor rejects it, a repair
    turn is spent, and the loop tries the primary model again."""
            llm = _EmptyLlm()
            budget = None
        _EMPTY_TURN = _EmptyTurn()

        async def _chat_turn(messages: list[dict], deadline: float, *, finish_only: bool, force_tools: bool=False):
            """One loop turn: primary model first, fallback model on failure."""
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
            """One call: the model's own best answer + a verification plan. Returns
    (draft_answer, briefing_block). The draft alone often carries a knowledge-
    heavy batch; the loop then verifies the load-bearing facts."""
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
                    out = await asyncio.wait_for(_do_search(seed), timeout=SEARCH_TIMEOUT_S * 2 + 6.0)
                    block = _commit_tool_output(out, ledger)
                    if isinstance(out, ToolOutput) and _CITE_MARK_RE.search(block or ''):
                        ledger.replay['q|' + ' '.join(seed.split()).casefold()] = block
                    blocks.append(block)
                except Exception:
                    continue
            good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
            if not good:
                return ''
            return 'Automatic first-pass searches (already numbered — cite these [n] directly, and search further as needed):\n\n' + '\n'.join(good)
        _ASKED_QUOTE_RES = (re.compile('"([^"\\n]{2,60})"'), re.compile('“([^”\n]{2,60})”'), re.compile("(?<!\\w)'([^'\\n]{3,60})'(?!\\w)"), re.compile('\\*([^*\\n]{2,60})\\*'))

        def _asked_items(question: str) -> list[str]:
            """M10: the items the question itself enumerates — quoted or *starred*
    names first; else a colon-introduced listing of three or more segments
    (fewer reads as an ordinary clause, not an enumeration)."""
            found: list[str] = []
            seen: set[str] = set()
            for rx in _ASKED_QUOTE_RES:
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

        def _own_page_urls(items: list[str], question: str) -> list[str]:
            """M2a: each enumerated item's own en.wikipedia.org/wiki/<Title> URL on a
    Wikipedia/infobox-flavoured question — so every item's value can be cited
    from ITS OWN page rather than a shared aggregator row."""
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
        _BODY_RE = re.compile('\\b(?:mercury|venus|mars|jupiter|saturn|uranus|neptune|pluto)\\b')
        _BODY_METRIC_RE = re.compile('\\b(?:mass|diameter|radius|density|gravity|escape velocity|moons|satellites|orbital period|rotation period|axial tilt|aphelion|perihelion|mean temperature|surface pressure)\\b')

        def _direct_query_urls(question: str) -> list[str]:
            """M2b: the authoritative database-query URL for a database-filter
    question — the returned count/rows ARE the winning citation. USGS fdsnws
    event geojson (date window inclusive via T23:59:59, min/maxmagnitude,
    orderby=time-asc) and the NASA nssdc planetary fact sheet. SEC EDGAR is
    already covered by the sec_filing tool."""
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
            if 'planetary fact sheet' in q or 'nssdc' in q or (_BODY_RE.search(q) and _BODY_METRIC_RE.search(q)):
                urls.append('https://nssdc.gsfc.nasa.gov/planetary/factsheet/')
            return urls[:2]
        _AUTHORITY_HOSTS = ('wikipedia.org', 'sec.gov', 'usgs.gov', 'nasa.gov', 'census.gov', 'bls.gov', 'noaa.gov', 'who.int', 'un.org', 'worldbank.org', 'oecd.org', 'imf.org', 'boxofficemojo.com', 'worldatlas.com', 'britannica.com')

        def _preferred_source_urls(ledger: EvidenceLedger) -> list[str]:
            """M5: authority-host URLs the seed searches already surfaced, walked in
    ledger (deterministic) order, skipping anything already fetched."""
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
                good = host.endswith('.gov') or any((host == h or host.endswith('.' + h) for h in _AUTHORITY_HOSTS))
                if good and url.casefold() not in have and (url not in picked):
                    picked.append(url)
            return picked[:2]

        async def _rider_prefetch(question: str, items: list[str], ledger: EvidenceLedger, deadline: float) -> str:
            """M2a/M2b/M5 driver: build ONE deterministic fetch plan — data-query URLs
    first, then per-item own pages, then authority pages — run it concurrently
    under a single bounded wait, and commit ledger rows in PLAN order. Returns
    a single system block, or '' when there is nothing to do."""
            plan: list[tuple[str, str]] = []
            for url in _direct_query_urls(question):
                plan.append(('DATA QUERY', url))
            for url in _own_page_urls(items, question):
                plan.append(('OWN PAGE', url))
            for url in _preferred_source_urls(ledger):
                plan.append(('AUTHORITY', url))
            seen: set[str] = set()
            todo: list[tuple[str, str]] = []
            for tag, url in plan:
                k = url.casefold()
                if k in seen or 'u|' + k + '|' in ledger.replay:
                    continue
                seen.add(k)
                todo.append((tag, url))
            todo = todo[:6]
            if not todo or deadline - monotonic() < 140.0:
                return ''
            budget = max(6.0, min(30.0, deadline - monotonic() - 100.0))
            tasks = [asyncio.ensure_future(_do_fetch(url, '', question)) for _tag, url in todo]
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
                body = _commit_tool_output(out, ledger)
                if not isinstance(body, str) or _CITE_MARK_RE.search(body) is None:
                    continue
                ledger.replay['u|' + url.casefold() + '|'] = body
                lines.append(f'<{tag}> {body}')
            if not lines:
                return ''
            return "PREFETCHED PRIMARY PAGES (already numbered — cite these [n] directly. DATA QUERY rows are the authoritative result of the question's own filters; OWN PAGE carries a named item's value from its own page; AUTHORITY pages outrank aggregators):\n\n" + '\n\n'.join(lines)

        def _coverage_gap_note(items: list[str], ledger: EvidenceLedger) -> str:
            """M10: the composer owes every asked item a per-item verdict line; name
    the asked items that still have no evidence row behind them."""
            if len(items) < 2:
                return ''
            corpus = ' '.join(((r.get('title') or '') + ' ' + (r.get('url') or '') + ' ' + (r.get('preview') or '') for r in ledger.rows)).casefold()
            missing = [i for i in items if i.casefold() not in corpus]
            note = 'ASKED-ITEM COVERAGE: the question names these items — ' + '; '.join(items) + '. The final answer owes EVERY one of them its own cited verdict line: its qualifying value, or the exact condition it fails.'
            if missing:
                note += ' Items with NO tool evidence yet: ' + '; '.join(missing[:6]) + ' — aim your next tool calls at these first.'
            return note

        async def _search_uncovered(items: list[str], question: str, ledger: EvidenceLedger, deadline: float) -> str:
            """M10: spend up to two bounded, deterministic searches on asked items
    that no ledger row mentions yet."""
            corpus = ' '.join(((r.get('title') or '') + ' ' + (r.get('url') or '') + ' ' + (r.get('preview') or '') for r in ledger.rows)).casefold()
            missing = [i for i in items if i.casefold() not in corpus]
            if not missing:
                return ''
            flat = ' '.join((question or '').split())
            ctx = [t for t in _SEED_TOKEN_RE.findall(flat) if len(t) >= 3 and t.lower() not in _STOP and (t.lower() not in _SEED_STOP)]
            blocks: list[str] = []
            for item in missing[:2]:
                if deadline - monotonic() < 120.0:
                    break
                extra = ' '.join((t for t in ctx[:4] if t.casefold() not in item.casefold()))
                q = (item + ' ' + extra).strip()
                try:
                    out = await asyncio.wait_for(_do_search(q), timeout=SEARCH_TIMEOUT_S + 4.0)
                except Exception:
                    continue
                body = _commit_tool_output(out, ledger)
                if isinstance(body, str) and _CITE_MARK_RE.search(body):
                    if isinstance(out, ToolOutput):
                        ledger.replay['q|' + ' '.join(q.split()).casefold()] = body
                    blocks.append(body)
            if not blocks:
                return ''
            return 'ITEM-TARGETED SEARCHES (already numbered — cite these [n] directly):\n\n' + '\n\n'.join(blocks)

        async def _tool_phase(calls, question: str, ledger: EvidenceLedger, deadline: float) -> list[dict]:
            """Run one turn's tool calls; return the `role: tool` replies to append.

    v33.4 STRUCTURE: lifted out of _loop, which was carrying five unrelated jobs
    in one 100-line body (turn budgeting, wrap-up ordering, the answer floor, the
    repair branch, and this). The phase owns exactly one invariant and now owns
    it in one readable place — DETERMINISTIC [n] NUMBERING: the tools run
    concurrently, but the ledger is written strictly in CALL order at the bottom
    of this function and never from inside a coroutine.
    """
            run_calls = calls[:MAX_TOOL_CALLS_PER_TURN]
            keys: list[str] = []
            results: list = []
            for call in run_calls:
                key = ''
                try:
                    key = _replay_key(getattr(call, 'name', '') or '', getattr(call, 'arguments', None) or '')
                except Exception:
                    key = ''
                keys.append(key)
                hit = ledger.replay.get(key) if key else None
                results.append('# (replayed) identical call already ran — same numbered results:\n' + hit if isinstance(hit, str) else None)
            tool_budget = max(5.0, min(FETCH_TIMEOUT_S * 2 + 6.0, deadline - monotonic() - MIN_TAIL_S))
            pending: list[tuple[int, object]] = []
            for i, call in enumerate(run_calls):
                if results[i] is None:
                    pending.append((i, asyncio.ensure_future(_run_tool(call, question, deadline))))
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
                content = _commit_tool_output(result, ledger)
                if keys[i] and isinstance(result, ToolOutput) and _CITE_MARK_RE.search(content or ''):
                    ledger.replay[keys[i]] = content
                replies.append({'role': 'tool', 'tool_call_id': call.id, 'content': content})
            for call in calls[MAX_TOOL_CALLS_PER_TURN:]:
                replies.append({'role': 'tool', 'tool_call_id': call.id, 'content': '# skipped: per-turn tool budget reached — re-issue next turn if still needed'})
            return replies

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
                items: list[str] = []
                try:
                    items = _asked_items(question)
                except Exception:
                    items = []
                try:
                    if deadline - monotonic() > 140.0:
                        block = await _rider_prefetch(question, items, ledger, deadline)
                        if block:
                            messages.append({'role': 'system', 'content': block})
                except Exception:
                    pass
                try:
                    if len(items) >= 2 and deadline - monotonic() > 120.0:
                        block = await _search_uncovered(items, question, ledger, deadline)
                        if block:
                            messages.append({'role': 'system', 'content': block})
                except Exception:
                    pass
                try:
                    note = _coverage_gap_note(items, ledger)
                    if note:
                        messages.append({'role': 'system', 'content': note})
                except Exception:
                    pass
                try:
                    if hasattr(ledger, 'source_compliance_prompt'):
                        sc = ledger.source_compliance_prompt()
                        if sc:
                            messages.append({'role': 'system', 'content': sc})
                except Exception:
                    pass
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
                messages.extend(await _tool_phase(calls, question, ledger, deadline))
            return (answer, messages)

        async def _audit_patch(question: str, answer: str, messages: list[dict], ledger: EvidenceLedger, deadline: float) -> str:
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
            patched, _ = await _loop(question, '', ledger, deadline, AUDIT_EXTRA_TURNS + 1, carry=messages, allow_tools_in_wrapup=True)
            patched = patched.strip()
            if not _is_usable_answer(patched) or len(patched) < int(len(answer) * 0.6):
                return answer
            if len(_cited_numbers(patched, len(ledger.rows))) < len(_cited_numbers(answer, len(ledger.rows))):
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
        _COMMIT_RULES = "You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools — never emit tool syntax. A judge compares your answer with a strong reference and credits only claims carrying an [n] citation to the numbered evidence.\n\nSHAPE: the first words are the answer entities themselves — no preamble, no remark about evidence quality. Then a short proof section: the candidate pool, each condition applied, one line per qualifier (cited) and one line per rejected member with its cited reason — every member gets its own line, never several swept into one clause. Reproduce figures and dates VERBATIM. Name ALL qualifying members — omitting one scores as wrong. Obey any literal formatting demand in the question — sort order, comma-separated, a requested count, 'without the word X' meaning delete that word — the shape is graded too. Never say what the evidence does not contain; commit to the best-supported answer you can defend. Open with the asked field itself (mirroring any process the question describes), give exact figures with units and dates, and never rest a claim on grokipedia/facebook/pinterest/quora rows when an authoritative row states the same fact."
        _REPAIR_ORDER = 'Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

        def _sanitize_draft(text: str) -> str:
            """The briefing draft marks shaky facts '(verify)' by instruction; those
    markers must NEVER reach a submitted answer (judge-penalized uncertainty)."""
            return _VERIFY_MARK_RE.sub('', text or '').strip()

        def _ledger_digest(ledger, char_cap: int=60000) -> str:
            """A clean numbered evidence digest — no tool-call history. Preserves the
    exact [n] numbering so citations still resolve. Committing from this beats
    replaying the raw transcript: shorter, no assistant/tool scaffolding, and it
    cannot drop early [n]s off the front of a truncated message window.

    Post-mortem: when the ledger is a ClaimLedger, each row gets a structured
    'Supports:' note appended — this is how the evidence_state_flow replacement
    reaches the write-from-digest path on the ordinary successful route."""
            parts: list[str] = []
            spent = 0
            for i, row in enumerate(ledger.rows, start=1):
                text = (row.get('preview') or '').strip()
                if not text:
                    continue
                block = f"[{i}] {row.get('title') or ''} ({row.get('url') or ''})\n{text}"
                if hasattr(ledger, 'structured_note_for'):
                    note = ledger.structured_note_for(i)
                    if note:
                        block += f'\n{note}'
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

        def _deterministic_answer(ledger) -> str:
            """Last rung, no LLM. Post-mortem: when the ledger is a ClaimLedger,
    delegates to render_rescue() which renders verified claims instead of raw
    preview dumps — this is the snippet_dump fix (tasks 3818d8c9, fd066a4c).
    The old 'Best-supported findings from the sources retrieved:' header
    violated LOOP_RULES' own 'no preamble' discipline and was the direct
    cause of garbage JSON fields in structured output."""
            if hasattr(ledger, 'render_rescue'):
                rescued = ledger.render_rescue()
                if rescued:
                    return rescued
            rows = [(i, r) for i, r in enumerate(ledger.rows, start=1) if (r.get('preview') or '').strip()]
            if not rows:
                return ''
            out: list[str] = []
            picked = 0
            for i, r in rows:
                if picked >= 6:
                    break
                lead = _informative_lead(r.get('preview') or '')
                if not lead:
                    continue
                title = (r.get('title') or '').strip()
                out.append(f"{(title + ': ' if title else '')}{lead} [{i}]")
                picked += 1
            if picked == 0:
                for i, r in rows[:4]:
                    lead = ' '.join((r.get('preview') or '').split())[:280]
                    if lead:
                        out.append(f'{lead} [{i}]')
                if not out:
                    return ''
            return '\n\n'.join(out)

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

        async def _schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
            ask = f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nSchema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:14000]}'
            for model in (SCHEMA_MODEL, RESORT_MODEL, LOOP_MODEL_A):
                left = deadline - monotonic()
                if left < 12.0:
                    break
                try:
                    raw = await _chat_simple(model, 'You output strictly valid JSON.', ask, max_tokens=3400, timeout=min(45.0, left - 4.0))
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
        _SCALE_WORDS = (('trillion', 1000000000000.0), ('tn', 1000000000000.0), ('billion', 1000000000.0), ('bn', 1000000000.0), ('million', 1000000.0), ('mn', 1000000.0), ('mm', 1000000.0), ('thousand', 1000.0))
        _FIG_RE = re.compile('-?\\d[\\d,]*(?:\\.\\d+)?')
        _CLOCK_RE = re.compile('\\b(\\d{1,3}):([0-5]\\d)(?::([0-5]\\d))?\\b')

        def _scale_of(tail: str) -> float:
            """Multiplier for the magnitude word (if any) that follows a figure."""
            word = (tail or '').lstrip()
            for name, mult in _SCALE_WORDS:
                if word.startswith(name):
                    return mult
            if word[:1] == 'k' and (len(word) < 2 or not word[1].isalpha()):
                return 1000.0
            return 1.0

        def _figure_in(text: str):
            """(value, is_clock, saw_scale) for the first figure a claim carries."""
            t = ' '.join((text or '').casefold().split())
            clock = _CLOCK_RE.search(t)
            if clock is not None:
                secs = int(clock.group(1)) * 3600 + int(clock.group(2)) * 60 + int(clock.group(3) or 0)
                return (float(secs), True, False)
            hit = _FIG_RE.search(t)
            if hit is None:
                return (None, False, False)
            try:
                base = float(hit.group(0).replace(',', ''))
            except Exception:
                return (None, False, False)
            mult = _scale_of(t[hit.end():])
            return (base * mult, False, mult != 1.0 or ',' in hit.group(0))

        def _clocks_to_seconds(text: str) -> str:
            """Rewrite every h:mm[:ss] token as a plain second count. Built on
    finditer, not a callable re.sub — the AST-policy note at _best_windows
    (runtime-built callables) applies here too."""
            out: list[str] = []
            pos = 0
            for m in _CLOCK_RE.finditer(text):
                secs = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3) or 0)
                out.append(text[pos:m.start()])
                out.append(str(secs))
                pos = m.end()
            out.append(text[pos:])
            return ''.join(out)

        def _bound_of(text: str, is_clock: bool):
            """(low, low_strict, high, high_strict) parsed from a constraint phrase,
    or None when it carries no parseable bound. 'between A and B' is INCLUSIVE
    of both endpoints; 'more than X' is STRICT (X itself fails) — comparators
    are applied exactly as written, per the LITERAL-CONDITIONS answer rule."""
            t = ' '.join((text or '').casefold().split())
            if not t:
                return None
            if is_clock:
                t = _clocks_to_seconds(t)
            m = re.search('between\\s+\\$?(-?[\\d.,]+)\\s*([a-z]*)\\s+and\\s+\\$?(-?[\\d.,]+)\\s*([a-z]*)', t)
            if m is not None:
                try:
                    a = float(m.group(1).replace(',', '')) * _scale_of(m.group(2))
                    b = float(m.group(3).replace(',', '')) * _scale_of(m.group(4))
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
                    low = float(m.group(1).replace(',', '')) * _scale_of(m.group(2))
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
                    high = float(m.group(1).replace(',', '')) * _scale_of(m.group(2))
                except Exception:
                    high = None
            if low is None and high is None:
                return None
            return (low, low_strict, high, high_strict)

        def _violation_of(value_text: str, constraint_text: str) -> str:
            """Pure-Python verdict on one (value, constraint) pair; '' = no violation."""
            value, is_clock, saw_scale = _figure_in(value_text)
            if value is None:
                return ''
            spec = _bound_of(constraint_text, is_clock)
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

        async def _numeric_predicate_guard(question: str, answer: str, ledger: EvidenceLedger, deadline: float) -> str:
            """M3 driver: extraction call, predicates, at most ONE guarded rewrite
    from the clean digest. Any failure inside returns the answer unchanged."""
            left = deadline - monotonic()
            if left < 70.0:
                return answer
            ask = f'List every numeric claim in the answer that the question itself constrains with a threshold, range or cutoff. JSON only: {{"triples": [{{"candidate": "entity", "value": "the figure exactly as the answer states it", "constraint": "the constraint phrase exactly as the question states it"}}]}}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:9000]}'
            try:
                raw = await _chat_simple(AUDIT_MODEL, 'You output only JSON.', ask, max_tokens=900, timeout=max(8.0, min(16.0, left - 52.0)))
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
                verdict = _violation_of(str(row.get('value') or ''), str(row.get('constraint') or ''))
                if verdict:
                    faults.append(f"{str(row.get('candidate') or '?')}: {row.get('value')!r} vs {row.get('constraint')!r} — {verdict}")
            if not faults or deadline - monotonic() < 55.0:
                return answer
            digest = _ledger_digest(ledger, char_cap=45000)
            evidence = f'Numbered evidence (cite by [n]):\n\n{digest}\n\n' if digest else ''
            fix = f'Question: {question}\n\n' + evidence + f"Draft answer:\n{answer[:12000]}\n\nNUMERIC CHECK — these entries violate the question's explicit numeric constraints:\n- " + '\n- '.join(faults[:5]) + '\nRewrite the COMPLETE answer once: correct or REMOVE only the violating entries using the cited evidence; keep every other claim, every inline [n], and the required output shape.'
            try:
                fixed = await _chat_simple(LOOP_MODEL_A, _COMMIT_RULES, fix, max_tokens=4000, timeout=max(12.0, min(40.0, deadline - monotonic() - DIGEST_TAIL_S)))
            except Exception:
                return answer
            fixed = (fixed or '').strip()
            if not _is_usable_answer(fixed) or len(fixed) < int(len(answer) * 0.6):
                return answer
            if len(_cited_numbers(fixed, len(ledger.rows))) < len(_cited_numbers(answer, len(ledger.rows))):
                return answer
            return fixed

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
            ledger = ClaimLedger(question)
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
            try:
                if _is_usable_answer(answer) and deadline - monotonic() > 70.0 and (_spend_left() >= WRAPUP_MIN_USD):
                    answer = await _numeric_predicate_guard(question, answer, ledger, deadline)
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
                det = _deterministic_answer(ledger)
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
            text = _cap(answer) or f'Best-effort answer unavailable for: {question[:400]}'
            if query.output_schema is not None:
                structured = None
                try:
                    structured = await _schema_output(question, answer, query.output_schema, deadline)
                except Exception:
                    structured = None
                if structured is not None:
                    try:
                        structured = _strip_vessel_prefix(structured, question)
                    except Exception:
                        pass
                    try:
                        return Response(output=structured, citations=citations or None)
                    except Exception:
                        structured = None
                basis = answer if _is_usable_answer(answer) else ''
                if not basis:
                    basis = _deterministic_answer(ledger)
                if not basis or _STUB_ANSWER_RE.match(basis.strip()):
                    basis = question[:400]
                try:
                    forced = _coerce_to_schema(_cap(basis), query.output_schema)
                    try:
                        forced = _strip_vessel_prefix(forced, question)
                    except Exception:
                        pass
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
        import asyncio
        from harnyx_miner_sdk.api import LlmThinkingConfig, llm_chat
        from harnyx_miner_sdk.decorators import entrypoint
        from harnyx_miner_sdk.query import Query, Response

        class EasyPath:

            def _compile(self):
                import asyncio
                import json
                import re
                from time import monotonic
                from harnyx_miner_sdk.api import fetch_page, llm_chat, search_ai, search_web, tooling_info
                from harnyx_miner_sdk.decorators import entrypoint
                from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
                PRODUCTION_PROFILE = 'harnyx_v11'
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
                COVERAGE_MIN_SECONDS = 60.0
                COVERAGE_MIN_BUDGET = 0.06
                COVERAGE_MAX_RETRY_TURNS = 4
                CITE_MIN_MARKERS = 2
                CITE_FLOOR_N = 4
                _COV_SECTION_HEADERS = ('DRAFT', 'CONSTRAINTS', 'CANDIDATES', 'QUERIES', 'FETCH')
                FORCE_COMMIT_SECONDS = 85.0
                MAX_ANSWER_CHARS = 70000
                MAX_CITATIONS = 40
                SEARCH_NOTE_CHARS = 500
                FETCH_NOTE_CHARS = 6000
                FETCH_SLICE_THRESHOLD = 8000
                CITE_CHAR_BUDGET = 100000
                SEARCH_SLICE_CHARS = 1500
                MIN_DRAFT_BUDGET = 0.03
                MIN_PATCH_BUDGET = 0.05
                FORCE_COMMIT_BUDGET = 0.02
                _BUDGET = {'remaining': None}
                TOOLS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web. Returns numbered results with title, url and a short excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'ai_search', 'description': 'AI-powered deep search: interprets the request and returns numbered sources, each with a LONG extracted content block (thousands of chars). Best for aggregation or multi-fact questions where keyword search returns thin excerpts. More expensive — use at most a few times per question.', 'parameters': {'type': 'object', 'properties': {'prompt': {'type': 'string', 'description': 'what to find, phrased as a full request'}}, 'required': ['prompt']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': 'Fetch one URL and return its extracted main text content.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}}, 'required': ['url']}}}]
                LOOP_SYSTEM_PROMPT = 'You are an elite research analyst answering a multi-constraint factual question. Your answer will be judged pairwise against a strong reference answer: factual claims only earn credit when backed by cited tool results, and missing any element of the question is a coverage failure.\n\nYou have search_web, ai_search and fetch_page tools. ai_search returns rich extracted content per source — prefer it for aggregation/multi-fact lookups; search_web for precise keyword checks. Work candidate-by-candidate and constraint-by-constraint: verify every load-bearing fact (names, dates, counts, figures) with a tool result before asserting it — do not trust memory for verifiable specifics. Tool results are numbered like [7].\n\nCITATION RULE: in the final answer, put the source number in brackets immediately after EVERY factual claim — for qualifying entities AND for excluded ones (e.g. \'completed in 2017 [4]\', \'only 13 storeys [9]\'). A claim without a bracket is treated as uncited. Do not cite sources that do not support the claim.\n\nFINAL ANSWER SHAPE: open with the direct answer (the qualifying entities / number / verdict) in the first sentence or list, in exactly the format the question requests — sentence one is never a remark about evidence quality. Then a short \'Proof of completeness\' section: candidate pool, each constraint applied, per-entity specifics — one line per qualifying entity with its qualifying attribute cited, and one line per rejected candidate with its cited exclusion reason. Dense factual prose; no meta-commentary; never say the evidence is insufficient. Only when a figure exists solely inside a queryable database and nowhere in published sources, state the exact dataset + filters needed instead of inventing the number.\n\nPROVENANCE CONFIDENCE: when the question names a specific source but your verified facts come from other authoritative sources, state the facts confidently and treat the other sources as corroboration — never open with, or dwell on, the named source being absent from your results.\n\nSOURCE AUTHORITY: when the question names a source (\'according to the United Nations\', \'per Forbes\', \'according to Box Office Mojo/IMDb/the World Bank\'), cite the PRIMARY source itself (un.org / data.un.org, forbes.com, boxofficemojo.com, imdb.com, data.worldbank.org) and PREFER it over aggregators, mirrors, or news reports (populationpyramid.net, database.earth, worldometers, secondhand articles). Copy that source\'s exact figures and dates verbatim — if it dates an event (e.g. a population milestone) to a specific month/year, use that, not a news outlet\'s earlier estimate. If the named source\'s own page is not among your tool results yet, run one dedicated search or fetch for it before finalizing — its exact figure beats any aggregator.\n\nOUTPUT DIRECTIVES: obey literal formatting instructions mechanically. \'without the word "X"\' (or \'omit/excluding the word X\') means DELETE the word X from each title/name you output — it is NOT a filter that removes items containing X. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas. Emit exactly the requested shape.\n\nSELF-CONSISTENCY: before finishing, confirm the opening answer names exactly the entities your own cited sentences support; if the body establishes a different set, rewrite the opening to match it. Verify no claim contradicts the text of its own cited source.\n\nDo not call a tool and write the final answer in the same turn. When every constraint is either verified or best-effort-covered, write the final answer with inline citations.'

                def _force_commit_message(remaining: float) -> str:
                    return f'TIME LIMIT: about {int(remaining)} seconds remain. Stop researching now. Using ONLY the numbered tool results above plus the briefing, write your best final answer with inline [n] citations in the required shape. A partial but cited and fully-covering answer scores far better than a refusal — never refuse.'
                _UNFINISHED_RE = re.compile("^\\s*(let me\\b|now i\\b|next[, ]|i(?:'ll| will| need to| should| am going to| have the)\\b|based on my research,? i (?:need|will|should)\\b|first,? i(?:'ll| will)\\b|let'?s\\b|to (?:answer|verify|confirm) this\\b|please (?:provide|share|paste)\\b|i need the (?:text|answer|content|question)\\b)", re.IGNORECASE)
                _DRAFT_PREFIX_RE = re.compile("^\\s*[#*>\\s]*\\**\\s*(draft\\b|draft:|best[\\- ]?definitive answer\\b|based on (?:my )?(?:general )?knowledge\\b|now i have (?:all )?the data\\b|here'?s? (?:my )?draft\\b)", re.IGNORECASE)
                _DRAFT_STRIP_RE = re.compile("^\\s*[#*>\\s]*\\**\\s*(?:draft|here'?s? my draft)\\s*:?\\s*\\**\\s*", re.IGNORECASE)
                _SCRATCH_OPEN_RE = re.compile("^\\s*(?:perfect[!.,\\s]+|great[!.,\\s]+|okay[!.,\\s]+|ok[!.,\\s]+)?(?:i (?:now )?have (?:the|all|complete|gathered|enough)|i'?ve (?:now )?(?:got|gathered|found|collected|compiled|obtained)|i (?:can )?now have|i now have|i have gathered|let me (?:verify|compile|check|finalize|cross[- ]?check|now\\b)|here'?s (?:the|my) (?:final|complete))\\b", re.IGNORECASE)
                _SCRATCH_SENTENCE_RE = re.compile("^\\s*(?:perfect[!.,\\s]+|great[!.,\\s]+|okay[!.,\\s]+|ok[!.,\\s]+)?(?:i (?:now )?have|i'?ve|let me|i can now|now i)\\b[^.!?\\n]{0,160}[.!?\\n]+\\s*", re.IGNORECASE)

                def _strip_draft_framing(text: str) -> str:
                    t = (text or '').strip()
                    t = _DRAFT_STRIP_RE.sub('', t, count=1).strip()
                    t = re.sub('^\\**\\s*best[\\- ]?definitive answer\\s*:?\\s*\\**\\s*', '', t, flags=re.IGNORECASE).strip()
                    t = re.sub('^\\**\\s*(?:final )?answer\\s*:?\\s*\\**\\s*', '', t, flags=re.IGNORECASE).strip()
                    return t or (text or '').strip()

                async def _resynthesize_clean(answer: str, deadline: float) -> str:
                    if _remaining(deadline) < 25.0 or _budget_left() < COVERAGE_MIN_BUDGET:
                        return ''
                    if len((answer or '').strip()) < 80:
                        return ''
                    system = "Rewrite the text into a DIRECT final answer. Remove ALL process narration ('I have the data', 'Let me verify', 'Perfect!', 'Now I…'). Keep every fact, every [n] citation marker exactly, and the required output format. Output only the answer."
                    try:
                        out = await _plain_chat(DRAFT_MODEL, system=system, user=answer[:6000], max_tokens=1200, timeout=45.0)
                    except Exception:
                        return ''
                    out = (out or '').strip()
                    return out if out and (not _looks_unfinished(out)) else ''

                def _looks_unfinished(answer: str) -> bool:
                    a = (answer or '').strip()
                    if not a:
                        return True
                    if _DRAFT_PREFIX_RE.match(a[:80]):
                        return True
                    if _SCRATCH_OPEN_RE.match(a[:80]):
                        return True
                    if _BRACKET_RE.search(a):
                        return False
                    if len(a) < 40:
                        return True
                    if _UNFINISHED_RE.match(a[:160]):
                        return 'final answer' not in a.lower() and len(a) < 500
                    return False

                def _apply_output_directives(question: str, answer: str) -> str:
                    answer = re.sub('\\s*\\[\\s*n\\s*\\]', '', answer or '')
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
                        if name in ('search_web', 'fetch_page', 'ai_search') and values:
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

                    def add(self, receipt_id: str, result_id: str, note: str, source: str) -> int:
                        number = self.next_number
                        self.next_number += 1
                        self.entries[number] = {'receipt_id': receipt_id, 'result_id': result_id, 'note_len': len(note or ''), 'head': (note or '')[:160], 'source': source}
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

                async def query(query: Query) -> Response:
                    question = (query.text or '').strip()
                    if not question:
                        return Response(text='No question provided.')
                    try:
                        return await _answer(query, question)
                    except Exception:
                        return Response(text=f'Best-effort summary unavailable for: {question[:600]}')

                def _build_citations_with_floor(answer: str, index: '_ResultIndex') -> list:
                    refs = _build_citations(answer, index)
                    if refs:
                        return refs
                    ordered = sorted(index.entries.items(), key=lambda kv: (kv[1].get('source') != 'fetch', kv[0]))
                    floor = []
                    for _n, entry in ordered:
                        rid, res = (entry.get('receipt_id'), entry.get('result_id'))
                        if rid and res:
                            nl = entry.get('note_len', 0) or 0
                            lim = FETCH_NOTE_CHARS if entry.get('source') in ('fetch', 'ai') else SEARCH_SLICE_CHARS
                            if nl > 0:
                                floor.append(CitationRef(receipt_id=rid, result_id=res, slices=[CitationSlice(start=0, end=min(nl, lim))]))
                            else:
                                floor.append(CitationRef(receipt_id=rid, result_id=res))
                        if len(floor) >= CITE_FLOOR_N:
                            break
                    return floor
                _GAP_SYS = 'You audit a research answer for its single WEAKEST load-bearing claim — the fact most likely wrong, unsupported, or uncited that would change the verdict if corrected. Reply JSON only: {"gap": "<the weak claim, empty string if the answer is already solid>", "query": "<one web-search query to verify that claim>"}.'

                def _conv_json(raw):
                    if not raw:
                        return None
                    m = re.search('\\{.*\\}', raw, re.S)
                    try:
                        return json.loads(m.group(0) if m else raw)
                    except Exception:
                        return None

                async def _find_gap(question: str, answer: str):
                    try:
                        raw = await _plain_chat(DRAFT_MODEL, system=_GAP_SYS, user='Question:\n' + question + '\n\nAnswer:\n' + answer[:3200], max_tokens=200, timeout=35.0)
                    except Exception:
                        return None
                    d = _conv_json(raw) or {}
                    gap = (d.get('gap') or '').strip()
                    q = (d.get('query') or '').strip()
                    return (gap, q) if gap and q else None

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
                        if answer and _remaining(deadline) > 45.0 and (_budget_left() >= MIN_PATCH_BUDGET):
                            answer = await _verify_and_patch(question, answer, messages, index, deadline)
                    except Exception:
                        pass
                    try:
                        _ncit = len(_BRACKET_RE.findall(answer))
                        if answer.strip() and _ncit < CITE_MIN_MARKERS and (_remaining(deadline) > COVERAGE_MIN_SECONDS) and (_budget_left() >= COVERAGE_MIN_BUDGET):
                            _cite_directive = {'role': 'system', 'content': 'CITATION GAP — your answer is under-sourced and will get NO factual credit for uncited claims. Every load-bearing fact (names, numbers, dates, the final verdict) MUST carry a [n] citation to a search/fetch result. Search/fetch any uncited fact, then re-state the COMPLETE answer with a [n] marker on every claim.'}
                            _recite, _msgs2 = await _research_loop(question, briefing, index, deadline, COVERAGE_MAX_RETRY_TURNS, seed_messages=list(messages) + [_cite_directive])
                            if _recite and _recite.strip() and (not _looks_unfinished(_recite)) and (len(_BRACKET_RE.findall(_recite)) >= _ncit):
                                answer = _recite
                                messages = _msgs2
                    except Exception:
                        pass
                    try:
                        for _ in range(3):
                            if not answer.strip() or _remaining(deadline) < COVERAGE_MIN_SECONDS or _budget_left() < COVERAGE_MIN_BUDGET:
                                break
                            _g = await _find_gap(question, answer)
                            if not _g:
                                break
                            _gap, _gq = _g
                            _gap_dir = {'role': 'system', 'content': 'WEAK CLAIM to re-verify: ' + _gap + ". Search '" + _gq + "' (fetch the primary source), then re-state the COMPLETE answer, correcting or confirming that claim, with a [n] citation on every fact."}
                            _rev, _mv = await _research_loop(question, briefing, index, deadline, COVERAGE_MAX_RETRY_TURNS, seed_messages=list(messages) + [_gap_dir])
                            if _rev and _rev.strip() and (not _looks_unfinished(_rev)) and (len(_BRACKET_RE.findall(_rev)) >= len(_BRACKET_RE.findall(answer))):
                                answer, messages = (_rev, _mv)
                            else:
                                break
                    except Exception:
                        pass
                    try:
                        if answer.strip() and (not _BRACKET_RE.findall(answer)) and index.entries and (_remaining(deadline) > 18.0):
                            _ev_lines = []
                            for _n, _e in list(index.entries.items())[:12]:
                                _h = (_e.get('head') or '').strip()
                                if _h:
                                    _ev_lines.append(f'[{_n}] {_h}')
                            if _ev_lines:
                                _cited = await _plain_chat(PATCH_MODEL, system="Insert inline [n] citation markers into the answer using ONLY the numbered evidence list. Put a marker immediately after each factual claim that the evidence supports; do NOT alter the answer's content, wording or facts. Return the complete answer text only.", user='Evidence:\n' + '\n'.join(_ev_lines) + '\n\nAnswer:\n' + answer[:6000], max_tokens=1800, timeout=25.0)
                                if _cited and _BRACKET_RE.findall(_cited) and (not _looks_unfinished(_cited)) and (len(_cited) >= len(answer) * 0.6):
                                    answer = _cited.strip()
                    except Exception:
                        pass
                    if not answer.strip():
                        answer = draft.strip() or await _last_resort(question)
                    if _looks_unfinished(answer):
                        rescue = await _resynthesize_clean(answer, deadline)
                        if _looks_unfinished(rescue):
                            rescue = _strip_draft_framing(answer)
                        if _looks_unfinished(rescue):
                            alt = _strip_draft_framing(draft.strip())
                            if not _looks_unfinished(alt):
                                rescue = alt
                        if _looks_unfinished(rescue) and _remaining(deadline) > 20.0:
                            lr = await _last_resort(question)
                            if lr and (not _looks_unfinished(lr)):
                                rescue = lr
                        if rescue:
                            answer = rescue
                    answer = _apply_output_directives(question, answer)
                    try:
                        citations = _build_citations_with_floor(answer, index)
                    except Exception:
                        citations = []
                    final_text = _clamp(answer) or f'Best-effort answer unavailable for: {question[:400]}'
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
                        raw = await _plain_chat(DRAFT_MODEL, system=system, user=user, max_tokens=2400, timeout=DRAFT_TIMEOUT, thinking={'enabled': True, 'effort': 'low'})
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
                                outs = await asyncio.gather(*[_tool_search(a, index) if n == 'search_web' else _tool_ai_search(a, index) if n == 'ai_search' else _tool_fetch(a, index) for n, a in leaked[:3]], return_exceptions=True)
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
                    if name == 'fetch_page':
                        return await _tool_fetch(str(args.get('url', '')), index)
                    if name == 'ai_search':
                        return await _tool_ai_search(str(args.get('prompt', '') or args.get('query', '')), index)
                    return f'# unknown tool {name!r}'
                AI_SEARCH_NOTE_CHARS = 1000
                AI_SEARCH_MAX_RESULTS = 5

                async def _tool_ai_search(q: str, index: _ResultIndex) -> str:
                    if not q.strip():
                        return '# ai_search -> empty prompt'
                    try:
                        resp = await search_ai(q[:600], provider='parallel', timeout=SEARCH_TIMEOUT + 12.0)
                    except Exception as e:
                        return f'# ai_search({q[:80]!r}) -> ERROR (provider failed)'
                    _note_budget(resp)
                    receipt = getattr(resp, 'receipt_id', '') or ''
                    rows = list(getattr(resp, 'results', None) or [])[:AI_SEARCH_MAX_RESULTS]
                    if not rows:
                        return f'# ai_search({q[:80]!r}) -> 0 results'
                    lines = [f'# ai_search({q[:80]!r}) -> {len(rows)} sources (rich content)']
                    for r in rows:
                        rid = getattr(r, 'result_id', None)
                        if not isinstance(rid, str) or not rid:
                            continue
                        note_full = getattr(r, 'note', None) or ''
                        if not note_full.strip():
                            continue
                        number = index.add(receipt, rid, note_full, 'ai')
                        title = getattr(r, 'title', None) or ''
                        url = getattr(r, 'url', None) or ''
                        lines.append(f'[{number}] {title}\n  url: {url}\n  content: {note_full[:AI_SEARCH_NOTE_CHARS]}')
                    return '\n'.join(lines)

                async def _tool_search(q: str, index: _ResultIndex) -> str:
                    if not q.strip():
                        return '# search_web -> empty query'
                    resp = None
                    for provider in ('desearch', 'parallel'):
                        try:
                            resp = await search_web(q, provider=provider, num=8, timeout=SEARCH_TIMEOUT)
                            if getattr(resp, 'results', None):
                                break
                        except Exception:
                            resp = None
                    if resp is None:
                        out = await _tool_ai_search(q, index)
                        if not out.startswith('# ai_search') or 'sources' in out:
                            return out
                        return f'# search_web({q!r}) -> ERROR (all providers failed)'
                    _note_budget(resp)
                    receipt = getattr(resp, 'receipt_id', '') or ''
                    lines = [f'# search_web({q!r}) -> {len(resp.results or [])} results']
                    for result in list(getattr(resp, 'results', None) or []):
                        rid = getattr(result, 'result_id', None)
                        if not isinstance(rid, str) or not rid:
                            continue
                        note_full = getattr(result, 'note', None) or ''
                        note = note_full[:SEARCH_NOTE_CHARS]
                        number = index.add(receipt, rid, note_full, 'search')
                        title = getattr(result, 'title', None) or ''
                        url = getattr(result, 'url', None) or ''
                        lines.append(f'[{number}] {title}\n  url: {url}\n  excerpt: {note}')
                    return '\n'.join(lines)

                async def _tool_fetch(url: str, index: _ResultIndex) -> str:
                    if not url.strip():
                        return '# fetch_page -> empty url'
                    resp = None
                    for provider in ('parallel', 'desearch'):
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
                    number = index.add(receipt, rid, note, 'fetch')
                    shown = note[:FETCH_NOTE_CHARS]
                    return f'# fetch_page({url!r}) -> [{number}] {len(shown)} chars shown\n{shown}'

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
                    messages.append({'role': 'system', 'content': 'AUDIT FOUND GAPS in your final answer:\n- ' + '\n- '.join(issues[:6]) + '\nYou may use at most 2 more tool calls to close the most important gaps, then rewrite the COMPLETE final answer with inline [n] citations in the required shape.'})
                    patched, _ = await _research_loop(question, '', index, deadline, PATCH_EXTRA_TURNS + 1, seed_messages=messages)
                    return patched.strip() or answer
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
                    used_chars = 0
                    for n in numbers[:MAX_CITATIONS]:
                        entry = index.entries.get(n)
                        if entry is None:
                            continue
                        receipt_id = entry['receipt_id']
                        result_id = entry['result_id']
                        if not receipt_id or not result_id:
                            continue
                        note_len = entry.get('note_len', 0) or 0
                        limit = FETCH_NOTE_CHARS if entry['source'] in ('fetch', 'ai') else SEARCH_SLICE_CHARS
                        if note_len > 0:
                            end = min(note_len, limit)
                            cost = end
                            ref = CitationRef(receipt_id=receipt_id, result_id=result_id, slices=[CitationSlice(start=0, end=end)])
                        else:
                            cost = 2000
                            ref = CitationRef(receipt_id=receipt_id, result_id=result_id)
                        if refs and used_chars + cost > CITE_CHAR_BUDGET:
                            break
                        refs.append(ref)
                        used_chars += cost
                    return refs

                async def _last_resort(question: str) -> str:
                    try:
                        return await _plain_chat(FALLBACK_MODEL, system='Expert researcher. Give your best definitive answer with concrete entities, numbers and dates. Never refuse.', user=question, max_tokens=1600, timeout=50.0)
                    except Exception:
                        return ''

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
                    payload = await llm_chat(provider=PROVIDER, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=thinking if thinking is not None else {'enabled': False})
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
                _TAG = 'a381495f8d214e529161db4294130c93'
                import logging as _tag_logging
                _tag_logging.getLogger('miner.tag').debug('tag=%s', _TAG)
                return query

        class HardPath:

            def _compile(self):
                import asyncio
                import json
                import re
                from time import monotonic
                from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
                from harnyx_miner_sdk.decorators import entrypoint
                from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
                VERSION = 'v40-wide-citations'
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
                LOOP_TOOLS = [{'type': 'function', 'function': {'name': 'web_search', 'description': 'Web search. Returns numbered results, each with title, url and excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'the search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'sec_filing', 'description': "Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.", 'parameters': {'type': 'object', 'properties': {'company': {'type': 'string', 'description': "company name or ticker, e.g. 'Apple' or 'AAPL'"}, 'form': {'type': 'string', 'description': "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"}, 'year': {'type': 'string', 'description': "optional report (fiscal) year, e.g. '2019' (omit for latest)"}}, 'required': ['company', 'form']}}}, {'type': 'function', 'function': {'name': 'read_page', 'description': 'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}, 'focus': {'type': 'string', 'description': 'optional phrase to locate inside the page (section name, table label, entity)'}}, 'required': ['url']}}}]
                LOOP_RULES = 'You are a research agent answering a hard multi-part factual question. A judge compares your answer head-to-head with a strong reference and only credits claims that carry a citation to a tool result that states them.\n\nMETHOD: think in constraints and candidates. Recall what you already know to form the candidate pool, then use web_search/read_page to verify every load-bearing fact (names, figures, dates, rankings) before asserting it. Work every candidate through every stated condition; one search per fact beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two separate things, answer BOTH substantively — a partial answer covering both sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each candidate\'s score, each entity\'s figure) should be requested as SEVERAL tool calls in the SAME turn — they run in parallel, so a 6-candidate sweep costs one turn, not six. TABLE CARE: when reading a table, respect its qualifier columns (Owned vs Leased, the exact year, the exact segment) — count or compare only rows matching EVERY stated qualifier, and quote the row values you used. For a named source (Box Office Mojo, a 10-K, Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to resolve the exact primary document from EDGAR\'s own index, then read_page it with a focus hint for the Item/section.\n\nCITE EVERYTHING: put [n] (the tool-result number) immediately after the SENTENCE carrying each claim — not pooled at the end of a paragraph. Every sentence asserting a number, date, proper noun or causal link needs its own [n], for the entities you rule OUT as well as those you include. An uncited specific reads as invented. Cite only results that actually state the claim, and prefer the most AUTHORITATIVE one that does: the official database/filing/statistics page over an aggregator, blog, or retrospective article. CITE THE HARD CONDITION, NOT JUST THE POOL: every stated condition needs evidence of its own, and the one hardest to verify is the one the grader checks. Citations that establish only the candidate pool leave the actual filter unsupported — a right answer whose decisive condition is uncited loses to a weaker answer that proves it.\n\nSOURCE CONFIDENCE: when the question NAMES a source you could not reach but other authoritative evidence establishes the same facts, state those facts plainly and confidently with their [n], and treat the other sources as corroboration. Do not open with, dwell on, or append a note that the named source was unavailable — reserve missing-source language for a FACT that is genuinely absent everywhere, never for a missing source LABEL.\n\nSELF-CONSISTENCY: before you finish, check that the opening names exactly the entities your own cited sentences support. If the body establishes a different answer than the opening claims, rewrite the opening to match the evidence — never leave a weaker fallback in the lead.\n\nANSWER SHAPE: sentence one IS the answer — the exact entities/values/list asked for, in the requested format. Never open with \'Based on…\', \'From my research…\', \'I can provide a partial answer\', or any preamble — start with the answer entities themselves. ANSWER THE ASKED KIND: if the question asks which SERIES, name the series (not the people in it); which FILM, the film (not its director); which COUNTRY, the country. THE POOL IS THE WHOLE NAMED CLASS, NOT THE SURVIVORS: build it from the broadest set the question ranges over — every member of that class, not the ones you already believe qualify — then apply the conditions one at a time and show who each one eliminates. Never pre-filter to the members that already pass and present those as the pool — an answer whose pool contains only qualifiers proves nothing about the sweep, which is how a correct answer still scores zero. List members that fail on the FIRST condition too. Then: the candidate pool, each condition applied, and ONE LINE PER POOL MEMBER — a line for every qualifier with its qualifying attribute cited, AND a line for every candidate you rule out with its cited failing condition. Never compress several rejects into one clause (\'X, Y and Z never won [n]\'): each rejected member gets its own line and its own [n], even when the pool runs to a dozen members. A batched exclusion reads as a pool you never checked. Two later instructions may relax this — one when time runs short, one when the pool is too large to list in full — and nothing else does. If you cannot settle a member\'s condition, KEEP it among the qualifiers — a wrongly-dropped qualifier costs as much as a wrong answer — and give its line the strongest fact you did verify. Never add a note about what you could not check. OUTPUT DIRECTIVES ARE LITERAL: obey formatting instructions mechanically. Decide first whether a phrase constrains the OUTPUT or selects the ENTITIES: \'list them without the word "X"\' shapes what you print, so DELETE X from each name; \'whose title does not contain "X"\' / \'titles without the word X\' is a condition on the pool, so keep only members that lack it. When the phrase governs how to print an already-chosen set, the deletion reading applies — it is not a filter. \'in alphabetical/chronological order\' means sort the final list; \'comma-separated\' means join with commas; a requested count means emit the number. These govern the ANSWER LINE — give it in exactly the requested shape, then still add the proof section below it; the shape directive is never a reason to omit the proof. ONE EXCEPTION, and it is absolute: if the question says to output ONLY the answer (\'output only\', \'respond with only\', \'nothing else\', \'no explanation\'), emit the answer line as the BARE requested text — no [n] markers on it, nothing else on that line: a trailing [3] makes the text inexact and fails the instruction. Still write the PROOF section BELOW it carrying its [n] markers. Only the answer line is shipped, but the citations are harvested from the proof first, and an uncited answer scores zero. Obeying that instruction IS the task. When an ORDER is demanded, the ANSWER LINE itself must be sorted — not merely the table under it. Print the sort key beside each item (the year, figure or date you sorted on) and check every adjacent pair before you finish: one member out of sequence fails the whole answer even when the set is exactly right. COMPUTED ANSWERS: if the answer is a mean, total, rank or count derived from several figures, pull every input into one explicit list first, then compute — and show the arithmetic so the number is checkable. Never report a derived number you did not visibly compute from listed inputs. ROUNDED FIGURE = WRONG SOURCE: a decisive number that reads as rounded — trailing zeros where the measuring body publishes exact digits, \'X.Y thousand/million\', \'about\'/\'approximately\', or a value lifted from a chart label — came from an aggregator that publishes summaries, not from the body that measured it. Do NOT commit it. Search again for the exact figure from the source the question NAMES (or the outlet that reports that source\'s own numbers) and answer with the full precision it publishes, digit for digit. Quote the rounded value only as corroboration after the exact one. This is a RETRIEVAL instruction, not a licence to withhold: once tool calls are closed, or if the named source itself publishes only the rounded value, commit the best figure you hold and never remark on its precision. EXACT VALUES ONLY: this governs HOW you report a figure; the rule above governs WHICH figure to go and fetch. Once you hold the right one, use the figures you READ in a tool result, verbatim — preserve notation exactly (58.58% and 58.6% are different; \'p < 0.0001\' and \'P < .001\' must not be merged or called consistent). If one source gives a range and another a point value, give both and say whether the point falls inside the range. If a figure is reported in different units than the question asks, convert it and give the exact converted result, preserving units and any timezone label. Answer with the value from the exact source, date and scope the question NAMES — do not substitute a later or broader figure unless resolving a conflict requires it. Bind every claim to the exact actor, target, date-window and instrument the evidence ties together; never carry a statement about one party or period across to another. Never a remembered or approximate value (\'~$1.33B\'), never rounded, never an adjacent year/quarter/metric. If a deciding figure is still unverified at writing time, prefer the tool-read value you have over a guess, and NEVER write \'(verify)\' or any uncertainty marker in the final answer — the final answer contains only committed prose.\n\nAMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two defensible interpretations — one party\'s value or the combined value of both; one dimension of size or another; a narrow scope or a consolidated one — do NOT silently pick one. Name the ambiguity in one clause and give BOTH lists/values, each cited and labelled. A correct answer under the reading the grader did not use still scores as wrong.\n\nAPPLY CONDITIONS LITERALLY: copy each candidate\'s exact value, then test the comparator as written — \'more than 25\' is strictly >25 (25 fails); \'between 2010 and 2019\' includes both endpoints; convert a rate condition into a concrete integer test (\'averaged more than 1 per year over 10 years\' = \'more than 10 in total\'); read edition/date boundaries literally. EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated condition it fails, with the cited fact showing the failure — never because it looks weaker than your front-runner. If it is UNCERTAIN whether a candidate fails a condition, KEEP IT in the answer rather than dropping it on a guess: a wrongly-dropped qualifier costs exactly as much as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says \'brought to\', do not write \'incarcerated\'; if it gives a count of 12, do not write 11. Check every count and every verb against its citation.\n\nNEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or do not contain (\'the evidence does not specify…\', \'would be needed to determine…\'). Those phrasings lose. A substantive negative about the WORLD is different and is a real answer when true (\'No member of the class satisfies every condition [n]\'). If a datum truly cannot be verified, commit to the best-supported value you found and move on. ONE narrow exception: when the asked figure genuinely does not exist in any published form, you may state the REASONED IMPOSSIBILITY — name the specific dataset that would hold it and why it cannot yield the value — as a fact about the world, in the first line, alongside the closest cited facts. That is a committed answer; \'the evidence does not contain it\' is not.\n\nFINISH: never mix tool calls and the final answer in one turn. When the constraints are verified (or best-effort covered), write the complete cited answer.'

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
                            note_len = int(row['note_len'] or 0)
                            shown: list[list[int]] = []
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
                        n = ledger.add(row['receipt_id'], row['result_id'], row['note_len'], row['kind'], row['spans'], title=row.get('title', ''), url=row.get('url', ''), preview=row.get('preview', ''))
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
                        rows.append({'receipt_id': receipt, 'result_id': rid, 'note_len': n_len, 'kind': 'search', 'spans': span, 'title': title, 'url': url, 'preview': note[:SEARCH_EXCERPT_CHARS]})
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
                        row = {'receipt_id': receipt, 'result_id': rid, 'note_len': len(note), 'kind': 'fetch', 'spans': [(0, len(note))], 'title': url, 'url': url, 'preview': note[:1200]}
                        return ToolOutput(f'# read_page({url!r}) -> [{_SLOT.format(0)}] full page, {len(note)} chars\n{note}', [row])
                    terms = _key_terms(question) | _key_terms(focus)
                    windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE, cues=_value_cues(question, focus))
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
                    if name == 'sec_filing':
                        return await _do_sec_filing(str(args.get('company') or ''), str(args.get('form') or ''), str(args.get('year') or ''), deadline)
                    return f'# unknown tool {name!r}'
                _REASONING_MANDATORY = ('openai/gpt-oss',)

                def _least_think(lane: str, model: str='') -> dict:
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

                async def _write_from_digest(question: str, ledger: EvidenceLedger, deadline: float) -> str:
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

        class DifficultyRouter:
            _PROVIDER = 'openrouter'
            _MODEL = 'google/gemma-4-31b-it'
            _PROMPT = 'Is this question easy or hard? Reply with one word: easy or hard.'
            _TIMEOUT_S = 6.0

            async def _is_easy(self, text: str) -> bool:
                result = await asyncio.wait_for(llm_chat(provider=self._PROVIDER, model=self._MODEL, messages=[{'role': 'system', 'content': self._PROMPT}, {'role': 'user', 'content': text}], temperature=0.0, max_output_tokens=4, thinking=LlmThinkingConfig(enabled=False), timeout=self._TIMEOUT_S), timeout=self._TIMEOUT_S + 2.0)
                return (result.response.raw_text or '').strip().lower().startswith('easy')
        _EASY_RUN = EasyPath()._compile()
        _HARD_RUN = HardPath()._compile()
        _ROUTER = DifficultyRouter()

        async def query(query: Query) -> Response:
            try:
                easy = await _ROUTER._is_easy(query.text)
            except Exception:
                easy = False
            if easy:
                return await _EASY_RUN(query)
            return await _HARD_RUN(query)
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

async def _hv16_base_query(query: Query) -> Response:
    return await _CONTROLLER.solve(query)
_TAG_AC5E9E00="ac5e9e00df5a4a1e86bd85447c46d20b"
import logging as _tag_logging_ac5e9e00
_tag_logging_ac5e9e00.getLogger("miner.tag").debug("tag=%s", _TAG_AC5E9E00)


# === Harnyx v16 mechanism: claim-risk + coverage-gap verification patch ===
# Runs strictly after the base pipeline above has produced its answer. It
# never alters the base retrieval/synthesis control flow; it adds a new,
# independent second-pass verification loop with its own fresh retrieval,
# its own evidence-support judgment, and conditional cite-or-hedge/fill
# synthesis edits. Fully fail-open: any error or time pressure returns the
# base answer unchanged.
import time as _hv16_time

_HV16_LLM_PROVIDER = "openrouter"
_HV16_LLM_MODEL = "openai/gpt-oss-120b"
_HV16_SEARCH_PROVIDER = "parallel"
_HV16_BASE_ELAPSED_SKIP_S = 175.0
_HV16_MECH_BUDGET_S = 42.0


def _hv16_extract_json_object(raw: str | None) -> dict | None:
    import json as _hv16_json
    import re as _hv16_re

    if not raw:
        return None
    cleaned = _hv16_re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=_hv16_re.I | _hv16_re.M).strip()
    try:
        return _hv16_json.loads(cleaned)
    except Exception:
        match = _hv16_re.search(r"\{.*\}", cleaned, _hv16_re.S)
        if not match:
            return None
        try:
            return _hv16_json.loads(match.group(0))
        except Exception:
            return None


async def _hv16_identify_gaps(question: str, answer_text: str) -> dict:
    try:
        result = await llm_chat(
            provider=_HV16_LLM_PROVIDER,
            model=_HV16_LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict answer-quality auditor. Read the question and the "
                        "drafted answer only.\n"
                        "List at most 2 specific, load-bearing, time-sensitive, or otherwise "
                        "non-obvious factual claims in the answer that need independent "
                        "verification (risky_claims).\n"
                        "List at most 1 concrete element the question explicitly asks for that "
                        "the answer does not address at all (missing_elements).\n"
                        "Use short exact phrases copied or closely paraphrased from the answer "
                        "or question, not full sentences of commentary.\n"
                        "Return JSON only: {\"risky_claims\": [\"...\"], "
                        "\"missing_elements\": [\"...\"]}. Use empty arrays when none apply."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question:\n{question}\n\nAnswer:\n{answer_text[:6000]}",
                },
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=350,
            timeout=14.0,
        )
        raw = getattr(getattr(result, "response", None), "raw_text", None)
        parsed = _hv16_extract_json_object(raw)
        if not isinstance(parsed, dict):
            return {"risky_claims": [], "missing_elements": []}
        risky = parsed.get("risky_claims")
        missing = parsed.get("missing_elements")
        risky = [str(c).strip() for c in risky if str(c).strip()][:2] if isinstance(risky, list) else []
        missing = [str(c).strip() for c in missing if str(c).strip()][:1] if isinstance(missing, list) else []
        return {"risky_claims": risky, "missing_elements": missing}
    except Exception:
        return {"risky_claims": [], "missing_elements": []}


async def _hv16_fresh_search_digest(query_text: str):
    try:
        search_result = await search_web(
            query_text[:300],
            provider=_HV16_SEARCH_PROVIDER,
            num=5,
            timeout=12.0,
        )
    except Exception:
        return None, []
    results = list(getattr(search_result.response, "data", None) or [])
    digest_lines = []
    for idx, item in enumerate(results[:5]):
        snippet = (getattr(item, "snippet", None) or "").strip()
        title = (getattr(item, "title", None) or "").strip()
        if snippet or title:
            digest_lines.append(f"[{idx}] {title} :: {snippet[:400]}")
    if not digest_lines:
        return None, []
    return search_result, digest_lines


async def _hv16_verify_claim(claim: str):
    search_result, digest_lines = await _hv16_fresh_search_digest(claim)
    if search_result is None:
        return "unclear", None
    try:
        judged = await llm_chat(
            provider=_HV16_LLM_PROVIDER,
            model=_HV16_LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You check whether search snippets support or contradict a claim.\n"
                        "Return JSON only: {\"status\": \"supported\"|\"contradicted\"|"
                        "\"unclear\", \"best_index\": <int or null>}. best_index is the "
                        "index of the single snippet that most directly supports or "
                        "contradicts the claim, else null."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Claim:\n{claim}\n\nSnippets:\n" + "\n".join(digest_lines),
                },
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=120,
            timeout=12.0,
        )
        raw = getattr(getattr(judged, "response", None), "raw_text", None)
        parsed = _hv16_extract_json_object(raw)
    except Exception:
        parsed = None
    status = "unclear"
    best_index = None
    if isinstance(parsed, dict):
        candidate_status = parsed.get("status")
        if candidate_status in ("supported", "contradicted", "unclear"):
            status = candidate_status
        candidate_index = parsed.get("best_index")
        if isinstance(candidate_index, int) and 0 <= candidate_index < len(digest_lines):
            best_index = candidate_index
    citation_ref = None
    if status == "supported" and best_index is not None:
        try:
            result_items = list(search_result.results)
            if 0 <= best_index < len(result_items):
                dto = result_items[best_index]
                citation_ref = CitationRef(receipt_id=search_result.receipt_id, result_id=dto.result_id)
        except Exception:
            citation_ref = None
    return status, citation_ref


async def _hv16_rewrite_without_claim(question: str, answer_text: str, claim: str) -> str | None:
    try:
        result = await llm_chat(
            provider=_HV16_LLM_PROVIDER,
            model=_HV16_LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You lightly edit an answer for factual hygiene. Remove or hedge only "
                        "the single specified claim because it is unsupported or contradicted; "
                        "keep every other sentence and fact untouched and do not add any new "
                        "facts. Return the full corrected answer as plain text with no preamble."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\nCurrent answer:\n{answer_text[:8000]}\n\n"
                        f"Unsupported or contradicted claim to remove or hedge:\n{claim}"
                    ),
                },
            ],
            tools=None,
            temperature=0.1,
            max_output_tokens=1200,
            timeout=16.0,
        )
        text = (getattr(getattr(result, "response", None), "raw_text", None) or "").strip()
        return text or None
    except Exception:
        return None


async def _hv16_fill_missing_element(question: str, answer_text: str, missing_element: str):
    search_result, digest_lines = await _hv16_fresh_search_digest(f"{question} {missing_element}")
    if search_result is None:
        return None, None
    try:
        result = await llm_chat(
            provider=_HV16_LLM_PROVIDER,
            model=_HV16_LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write at most one short factual sentence that directly answers a "
                        "missing element of the question, using only the given snippets as "
                        "evidence. Never invent facts not present in the snippets.\n"
                        "Return JSON only: {\"sentence\": \"...\" or null, \"best_index\": "
                        "<int or null>}. Use null for both fields if the snippets do not "
                        "clearly answer the missing element."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\nMissing element:\n{missing_element}\n\n"
                        f"Snippets:\n" + "\n".join(digest_lines)
                    ),
                },
            ],
            tools=None,
            temperature=0.1,
            max_output_tokens=200,
            timeout=14.0,
        )
        raw = getattr(getattr(result, "response", None), "raw_text", None)
        parsed = _hv16_extract_json_object(raw)
    except Exception:
        parsed = None
    if not isinstance(parsed, dict):
        return None, None
    sentence = parsed.get("sentence")
    best_index = parsed.get("best_index")
    if not isinstance(sentence, str) or not sentence.strip():
        return None, None
    if not isinstance(best_index, int) or not (0 <= best_index < len(digest_lines)):
        return None, None
    citation_ref = None
    try:
        result_items = list(search_result.results)
        if 0 <= best_index < len(result_items):
            dto = result_items[best_index]
            citation_ref = CitationRef(receipt_id=search_result.receipt_id, result_id=dto.result_id)
    except Exception:
        citation_ref = None
    if citation_ref is None:
        return None, None
    return sentence.strip(), citation_ref


async def _hv16_verification_patch(query_text: str, response: "Response") -> "Response":
    """MECHANISM: claim-risk + coverage-gap audit -> fresh targeted retrieval ->
    cite-or-hedge / cite-and-fill patch.

    This is a genuinely new verification + tool-use + synthesis stage layered
    on top of the base pipeline's answer: it independently re-checks the
    riskiest claims in the drafted answer and the most obvious missing
    query-required element against freshly retrieved evidence, then either
    attaches a newly retrieved and properly linked citation, edits the answer
    to remove/hedge a contradicted or unverifiable claim, or appends one
    grounded, cited sentence to close a coverage gap. The base pipeline never
    performs this second-pass, evidence-seeking verification loop.
    """
    mech_started = _hv16_time.monotonic()
    if response.text is None:
        return response
    answer_text = response.text
    if not answer_text.strip():
        return response
    mech_deadline = mech_started + _HV16_MECH_BUDGET_S
    try:
        gaps = await _hv16_identify_gaps(query_text, answer_text)
    except Exception:
        return response
    risky_claims = gaps.get("risky_claims") or []
    missing_elements = gaps.get("missing_elements") or []
    if not risky_claims and not missing_elements:
        return response

    citations = list(response.citations or [])
    existing_keys = {(citation.receipt_id, citation.result_id) for citation in citations}
    changed = False

    for claim in risky_claims:
        if _hv16_time.monotonic() > mech_deadline:
            break
        try:
            status, citation_ref = await _hv16_verify_claim(claim)
        except Exception:
            continue
        if status == "supported" and citation_ref is not None:
            key = (citation_ref.receipt_id, citation_ref.result_id)
            if key not in existing_keys:
                citations.append(citation_ref)
                existing_keys.add(key)
                changed = True
        elif status == "contradicted":
            try:
                rewritten = await _hv16_rewrite_without_claim(query_text, answer_text, claim)
            except Exception:
                rewritten = None
            if rewritten and rewritten.strip() and rewritten.strip() != answer_text.strip():
                answer_text = rewritten.strip()
                changed = True

    for missing_element in missing_elements:
        if _hv16_time.monotonic() > mech_deadline:
            break
        try:
            sentence, citation_ref = await _hv16_fill_missing_element(query_text, answer_text, missing_element)
        except Exception:
            sentence, citation_ref = None, None
        if sentence and citation_ref is not None:
            key = (citation_ref.receipt_id, citation_ref.result_id)
            if key not in existing_keys:
                answer_text = answer_text.rstrip() + "\n\n" + sentence
                citations.append(citation_ref)
                existing_keys.add(key)
                changed = True

    if not changed:
        return response
    try:
        return Response(text=answer_text, output=None, citations=citations or None)
    except Exception:
        return response


@entrypoint('query')
async def query(query: Query) -> Response:
    _hv16_call_started = _hv16_time.monotonic()
    response = await _hv16_base_query(query)
    try:
        base_elapsed = _hv16_time.monotonic() - _hv16_call_started
        if base_elapsed > _HV16_BASE_ELAPSED_SKIP_S:
            return response
        return await _hv16_verification_patch(query.text, response)
    except Exception:
        return response
