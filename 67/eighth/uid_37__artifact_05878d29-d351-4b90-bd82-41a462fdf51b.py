"""SN67 Harnyx miner — lean autonomous deep-research harness (v39-lean-b, line L1).

Design: a single strong reasoning model (GLM-5 over openrouter) drives an autonomous
search/fetch tool loop, then commits one cited FINAL ANSWER. Independently authored;
follows the proven lean-agent pattern but is our own implementation:

  * Ledger-tracked evidence: every tool result gets a stable number [k] whose citation
    is later sliced to exactly the character window the model was shown, so the judge's
    materialized-evidence total stays under its hard cap (invalid-payload = score 0).
  * Bootstrap seeding: two deterministic searches derived from the raw question are fired
    before the model's first turn, so grounded evidence exists even if the model stalls
    on a slow first LLM call (our defence against validator LLM contention).
  * GUARANTEED commit: research stops with a reserved tail (COMMIT_RESERVE_S); we then run
    one tools-off, thinking-off forced commit so a run that gathered evidence NEVER returns
    an empty non-answer. An empty no-tool turn mid-research is treated as a stall (nudge and
    continue), not as a committed answer.
  * Completeness bias for which/list/superlative questions: enumerate every qualifying
    item with its metric, so aggregation/comparison questions are answered in full.

Refactor notes: protocol, prompts, model/provider ladders, budgets and execution order are
unchanged. Six defects are fixed (see REFACTOR_REPORT.md); each behavioural one sits behind
a switch in the "behaviour switches" block below.
"""
from __future__ import annotations

import asyncio
import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmThinkingConfig, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

_AGENT_VARIANT = "acd93685f0c0a4e0"

# ══════════════════════════════════════════════════════════════════════════════
# Providers / model (matched to funded BYOK keys: openrouter + parallel)
# ══════════════════════════════════════════════════════════════════════════════
# v2: add fallbacks so a single-provider outage can no longer 0.0 a whole batch (the SPOF the
# lean-agent teardown flagged). glm-5 is primary; deepseek-v3.2 is the reasoning fallback.
# parallel is primary search/fetch; desearch is the fallback when parallel errors or returns empty.
LLM_PROVIDER = "openrouter"
PRIMARY_MODEL = "z-ai/glm-5"
FALLBACK_MODEL = "deepseek/deepseek-v3.2"
SEARCH_PROVIDER = "parallel"
SEARCH_PROVIDERS = ("parallel", "desearch")   # primary then fallback, tried in order
FETCH_PROVIDERS = ("parallel", "desearch")

# ══════════════════════════════════════════════════════════════════════════════
# Budget / turn governor
# ══════════════════════════════════════════════════════════════════════════════
TOTAL_BUDGET_S = 285.0          # validator kills at 300s; keep a tail for the guaranteed commit
COMMIT_RESERVE_S = 45.0         # tail reserved purely for the forced final commit
LLM_TRY_PER_TURN = 2
SEARCH_TIMEOUT_S = 20.0
FETCH_TIMEOUT_S = 15.0
COMMIT_LOOKAHEAD_TURNS = 2
MAX_TURNS = 16
LLM_TURN_TIMEOUT_S = 68.0
FETCH_TRIES = 2

# Margins that were inline literals in the original. Values unchanged.
RESEARCH_MIN_SLICE_S = 2.0      # below this the research loop stops
TOOL_MIN_SLICE_S = 1.0          # below this no further tool call is started this turn
CHAT_WRAPPER_MARGIN_S = 3.0     # wait_for slack over the chat call's own timeout
TOOL_WRAPPER_MARGIN_S = 1.0     # wait_for slack over a single provider call's timeout
SEARCH_WRAPPER_MARGIN_S = 4.0   # wait_for slack over the whole search provider ladder
FETCH_WRAPPER_MARGIN_S = 4.0    # wait_for slack over the whole fetch provider ladder
PROVIDER_MIN_SLICE_S = 1.0      # below this the provider ladder stops advancing
CHAT_MIN_BUDGET_S = 1.0         # below this a chat attempt is not worth starting
SEED_EXTRA_S = 6.0              # extra budget each bootstrap seed gets for its fallback
SEED_WRAPPER_MARGIN_S = 12.0    # wait_for slack over the whole bootstrap gather
COMMIT_MIN_SLICE_S = 1.5        # below this the forced commit gives up
COMMIT_ATTEMPTS = 2

# ══════════════════════════════════════════════════════════════════════════════
# Evidence / citation-safety bounds
# ══════════════════════════════════════════════════════════════════════════════
SEARCH_WINDOW = 700             # chars of a search note surfaced to the model = slice width
FETCH_WINDOW = 6000             # chars of a fetched page surfaced to the model = slice width
CITATION_COUNT_CAP = 20
EVIDENCE_CHAR_CAP = 112_000     # sum of materialized slice widths kept under the ~120k wall
DIGEST_CHAR_CAP = 90_000        # size of the clean evidence digest fed to the forced commit
# v4: the page top (FETCH_WINDOW) is ALWAYS shown+cited exactly as base does (never regresses a
# top-of-page answer). Deep slices are added ONLY from genuine deep clusters, so v3's deep-table
# win is captured without v3's regression.
DEEP_WINDOW = 2600              # width of each targeted deep slice
# v9 structured-extraction: surface MULTIPLE deep regions of a fetched doc (not just one), including
# NUMERIC/TABLE-dense regions the question-terms don't hit — so deep data tables (INSEE PDF, 10-K
# property tables, Box-Office per-studio rows) become visible past the 6000-char top window. Purely
# ADDITIVE to A_v7's top window + synthesis (so A_v7's existing wins cannot regress).
MAX_DEEP_SLICES = 4             # max extra deep regions surfaced per fetched page
NUMERIC_DENSITY_MIN = 55        # digits within a deep_window to treat it as a data/table region
MIN_SLICE_CHARS = 100           # a slice narrower than this is not worth citing
MAX_CITATION_SEGMENTS = 380     # judge-side segment ceiling, held below 400
DEEP_LEAD_DIVISOR = 8           # a deep slice starts deep_window/8 before its anchor
DEEP_STEP_DIVISOR = 3           # numeric scan stride = deep_window/3
DEEP_STEP_MIN = 400
HIT_SCAN_CAP = 4000             # max term hits collected before scanning stops
TITLE_CHARS = 160
SEED_QUESTION_CHARS = 300
SEED_COMPACT_CHARS = 220
MIN_TOKEN_CHARS = 2             # salient tokens must be longer than this

# ══════════════════════════════════════════════════════════════════════════════
# Behaviour switches — each guards one defect fix; flip to restore the old path
# ══════════════════════════════════════════════════════════════════════════════
DEEP_SLICES_FIRST_ROW_ONLY = True   # deep offsets belong to the note they were computed from
GUARD_EMPTY_FETCH_RESULTS = True    # do not index [0] of an empty result list

SYSTEM_PROMPT = (
    "You are a meticulous research analyst. The user asks a factual question that is often "
    "multi-part or requires filtering a set of entities by several conditions. You have two tools, "
    "search_web and fetch_page; every tool result is labelled with a number like [4].\n\n"
    "METHOD:\n"
    "1. Decompose the question into every distinct sub-fact and every filtering condition. Never "
    "recall a date, age, count, rank, population, price, chart position or proper name from memory — "
    "search for it and read the result.\n"
    "2. ENUMERATE, THEN FILTER. When the question asks which members of a set satisfy conditions, "
    "FIRST establish the complete candidate pool from an authoritative list (do not work from the "
    "2-3 famous examples you can recall), THEN evaluate every candidate against every condition. "
    "Silently omitting a qualifying member is the most common way to lose.\n"
    "3. A superlative (highest-grossing, most-certified, largest, oldest, best-selling) is a LOOKUP, "
    "not a guess. Look up the actual ranked value from the authoritative source; an entity's most "
    "famous work is often NOT its top-ranked one.\n"
    "4. NAME-THE-SOURCE. If the question cites a specific source or dataset (e.g. Box Office Mojo, "
    "the 2020 US Census, a Billboard chart, an agency's annual report), get the numbers from THAT "
    "source by fetching its page — not from a secondary article. For a key entity, fetch_page the "
    "single most authoritative source (official site, .gov/.edu, primary filing, canonical article) "
    "and read it. Never cite reddit, x/twitter, quora or forums.\n"
    "5. STRICT THRESHOLD ARITHMETIC. Copy each candidate's exact value, then apply the comparator "
    "literally: 'more than 25' means strictly > 25 (25 fails); 'between 2010 and 2019' is inclusive "
    "of both endpoints. Convert rate/average conditions into a concrete integer test (e.g. 'averaged "
    "more than 1 per year over 10 years' = 'more than 10 in total'). Read date and edition boundaries "
    "literally (the 2010 through 2019 ceremonies are ten awards, one winner each).\n"
    "6. Verify each load-bearing sub-claim against a source before you rely on it; re-check the one "
    "or two near-miss cases that decide the answer.\n\n"
    "ANSWER — only once every sub-fact is verified:\n"
    "- Open with 'FINAL ANSWER: <the fully-resolved answer that already satisfies every condition>'. "
    "For a single-item question name that one item; do not lead with an unfiltered candidate list.\n"
    "- For which/list/superlative questions, then give each qualifying item with its compared value "
    "and citation, and briefly show the closest excluded item(s) with the value that disqualifies "
    "them (e.g. 'Nirvana: 10 charting singles [7] — fails the >12 test').\n"
    "- Quote numbers, dates and names verbatim with units (population 1,362,359 — not 'about 1.4M'); "
    "never round. Do not repeat the same fact, number, or conclusion; state each point once.\n"
    "- If the premise is false, or the specific data genuinely does not exist in any queryable form, "
    "say so plainly in the first line and give the correct fact or the reasoned impossibility (name "
    "the dataset and why it cannot be derived) — do NOT refuse or answer 'evidence missing'; commit "
    "to the best-supported answer.\n\n"
    "CITATIONS: place the source number in brackets immediately after EVERY factual claim — each "
    "number, date, name or yes/no determination gets its own bracket, e.g. 'the 2015 winner was "
    "Eddie Redmayne [6]'. Every load-bearing value must carry a citation or it scores zero. Do not "
    "append a bulk source list at the end and do not pad with tangential citations. Never write a "
    "final answer in the same turn as a tool call.\n\n"
    "BEFORE YOU COMMIT — three checks that decide close calls:\n"
    "1. COMPLETENESS: never conclude 'only X qualifies' until you have listed EVERY candidate from the "
    "question's set/pool BY NAME and checked each against every condition. The most common loss is "
    "omitting a second qualifier you already have evidence for — re-scan your results for it.\n"
    "2. MAXIMAL SPECIFICITY: give the most precise form the evidence supports — the exact room/hall "
    "name (not just the floor), the exact figure (not a rounded one), the exact date. A correct but "
    "vaguer answer loses to a more specific one.\n"
    "3. FILL THE ONE GAP: if a single required value is still missing when you are about to answer — a "
    "runtime, a figure from the pinned named source, one entity's datum — do ONE more targeted "
    "search/fetch for exactly that value before committing. Do not abstain over a single missing number."
)

COMMIT_NUDGE = (
    "About {secs}s of research budget remain — stop searching now. Using ONLY the numbered tool "
    "results gathered above, write the best FINAL ANSWER you can in the required format, with exact "
    "cited values. If a sub-claim is still uncertain, give the most-likely value and mark just that "
    "piece as a best estimate — a partial, cited answer scores far higher than a refusal."
)

HARD_COMMIT = (
    "STOP researching. Do not call any tool. Right now, using ONLY the numbered tool results already "
    "gathered above, write your single best FINAL ANSWER in the required format. "
    "Put a bracket citation [n] IMMEDIATELY after EVERY factual claim — each number, date, name, "
    "or yes/no gets its own [n] right next to it, not grouped at the end. "
    "For any piece still unresolved give the most-likely value and mark it as a best estimate. "
    "If the specific data provably does not exist, state that as your reasoned conclusion with citations. "
    "Do NOT give a bare refusal or 'evidence missing' non-answer — a partial, cited answer always scores higher."
)

FALLBACK_TEXT = "FINAL ANSWER: a fully source-backed answer could not be assembled within the time budget."

_TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web; returns numbered results, each with a title, url and text excerpt.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "the search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Fetch one URL and return the extracted main text of that page.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "the URL to fetch"}},
                "required": ["url"],
            },
        },
    },
]

_BRACKET_RE = re.compile(r"\[(\d[\d,\s-]*)\]")
_STOPWORDS = frozenset(
    "the a an of to in on for and or by with from at as is are was were be been being that this "
    "which who whom whose what when where how many much more most between during according only "
    "into over under than then their there these those has have had".split()
)

# Validation patterns for final answers — reject scratch text and hedged non-answers
_SCRATCH_PREFIXES = (
    "let me", "i need to", "i should", "first i", "first, i",
    "to answer this", "searching for", "looking up", "i'll search",
    "i will search", "wait,", "hold on", "one moment",
)
_HEDGE_PREFIXES = (
    "i cannot", "i can't", "i am unable", "i'm unable",
    "i do not have", "i don't have", "unfortunately",
    "sorry,", "i apologize", "i'm not able", "i am not able",
    "without more information", "the answer is unclear",
)


def _is_valid_final_answer(text: str) -> bool:
    """Reject scratch text and hedged non-answers that would score zero."""
    if not text or len(text) < 20:
        return False
    low = text.strip().lower()
    # Committed answers are always valid
    if "final answer:" in low[:100]:
        return True
    # Reject scratch text (model still planning)
    for p in _SCRATCH_PREFIXES:
        if low.startswith(p):
            return False
    # Reject hedged refusals
    for p in _HEDGE_PREFIXES:
        if low.startswith(p):
            return False
    return True


class _LedgerRow:
    """One numbered piece of evidence.

    Every field is assigned in __init__ — the point of replacing the old dict is
    that a field cannot exist without being declared here, and `note_len` /
    `top_end` stay ints instead of needing int() coercion at every read.
    """

    def __init__(self, receipt_id, result_id, window, note_len, top_end,
                 deeps, text, title, url):
        self.receipt_id = receipt_id
        self.result_id = result_id
        self.window = window
        self.note_len = note_len
        self.top_end = top_end
        self.deeps = deeps
        self.text = text
        self.title = title
        self.url = url


class _Ledger:
    """Assigns each surfaced tool result a stable number and remembers how to cite it safely,
    plus the shown text so a clean evidence digest can be rebuilt for the forced commit."""

    def __init__(self) -> None:
        self._rows: dict[int, _LedgerRow] = {}
        self._n = 0

    def add(self, receipt_id: str, results: object, *, window: int,
            deeps: list[tuple[int, int]] | None = None) -> list[tuple[int, object]]:
        # v9: `deeps` is a LIST of (start,end) windows into the SAME note, each disjoint from and after
        # the top window (search calls pass deeps=None -> byte-identical to base; only fetch adds them).
        # The top window [0:top_end] is ALWAYS stored/shown/cited unchanged, so A_v7's answers can't
        # regress; the deep slices only ADD relevant deep-table evidence.
        #
        # Returns (number, result) PAIRS rather than bare numbers: results without a result_id are
        # skipped, so a caller that re-pairs positionally against the unfiltered list mislabels
        # everything after the first gap.
        assigned: list[tuple[int, object]] = []
        for r in results or ():
            rid = getattr(r, "result_id", None)
            if not rid:
                continue
            self._n += 1
            note = getattr(r, "note", None) or ""
            top_end = min(window, len(note))
            text = note[:top_end]
            kept: list[tuple[int, int]] = []
            # The offsets in `deeps` were measured against ONE note. Applying them to a second
            # result would slice an unrelated document at those coordinates.
            own_deeps = deeps or []
            if DEEP_SLICES_FIRST_ROW_ONLY and assigned:
                own_deeps = []
            for d in own_deeps:
                ds, de = int(d[0]), min(int(d[1]), len(note))
                if de - ds < MIN_SLICE_CHARS or ds < top_end:           # >=100 chars & after the top window
                    continue
                if any(not (de <= es or ds >= ee) for es, ee in kept):  # disjoint from already-kept slices
                    continue
                kept.append((ds, de))
                text = f"{text}\n…\n{note[ds:de]}"                     # digest/forced-commit see deep regions too
            self._rows[self._n] = _LedgerRow(
                receipt_id=receipt_id,
                result_id=rid,
                window=window,
                note_len=len(note),
                top_end=top_end,
                deeps=kept,
                text=text,
                title=(getattr(r, "title", None) or "")[:TITLE_CHARS],
                url=getattr(r, "url", None) or "",
            )
            assigned.append((self._n, r))
        return assigned

    def row(self, n: int) -> _LedgerRow | None:
        return self._rows.get(n)

    def high(self) -> int:
        return self._n

    def digest(self, *, char_cap: int) -> str:
        """Compact numbered evidence block ([n] title/url + shown text) for a clean forced commit,
        capped so the commit context stays small and fast. Numbers match the citation ledger."""
        parts: list[str] = []
        spent = 0
        for n in range(1, self._n + 1):
            row = self._rows.get(n)
            if not row:
                continue
            text = row.text or ""
            if not text:
                continue
            block = f"[{n}] {row.title or ''} ({row.url or ''})\n{text}"
            if spent + len(block) > char_cap:
                continue
            spent += len(block)
            parts.append(block)
        return "\n\n".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# Question analysis
# ══════════════════════════════════════════════════════════════════════════════

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-']+")


def _seed_queries(question: str) -> list[str]:
    """Two deterministic bootstrap queries: the raw question, plus its salient content tokens."""
    q = " ".join(question.split())
    seeds = [q[:SEED_QUESTION_CHARS]]
    tokens = _TOKEN_RE.findall(question)
    salient = [t for t in tokens if t.lower() not in _STOPWORDS and (t[0].isupper() or any(c.isdigit() for c in t))]
    if salient:
        compact = " ".join(dict.fromkeys(salient))[:SEED_COMPACT_CHARS]
        if compact and compact.lower() != q[:SEED_COMPACT_CHARS].lower():
            seeds.append(compact)
    return seeds[:2]


def _salient_terms(text: str) -> list[str]:
    """Lower-cased content tokens of the question, stopwords dropped — used to detect a deep cluster."""
    tokens = _TOKEN_RE.findall(text or "")
    return list(dict.fromkeys(
        t.lower() for t in tokens if len(t) > MIN_TOKEN_CHARS and t.lower() not in _STOPWORDS
    ))


# ══════════════════════════════════════════════════════════════════════════════
# Deep-region selection
# ══════════════════════════════════════════════════════════════════════════════


def _term_hits(low: str, terms: list[str], start_at: int) -> list[int]:
    """Offsets at or after `start_at` where any salient term occurs, capped."""
    hits: list[int] = []
    for t in terms:
        st = start_at
        while len(hits) < HIT_SCAN_CAP:
            i = low.find(t, st)
            if i < 0:
                break
            hits.append(i)
            st = i + len(t)
    return hits


def _numeric_anchors(note: str, top_window: int, deep_window: int) -> list[int]:
    """Stride offsets whose following deep_window is digit-dense enough to look like a table."""
    anchors: list[int] = []
    step = max(DEEP_STEP_MIN, deep_window // DEEP_STEP_DIVISOR)
    n = len(note)
    i = top_window
    while i < n:
        if sum(c.isdigit() for c in note[i:i + deep_window]) >= NUMERIC_DENSITY_MIN:
            anchors.append(i)
        i += step
    return anchors


def _value_regions(note: str, terms: list[str], top_window: int, *,
                   deep_window: int = DEEP_WINDOW, max_slices: int = MAX_DEEP_SLICES) -> list[tuple[int, int]]:
    """v9: up to `max_slices` disjoint (start,end) windows AFTER top_window that are densest in
    question terms OR in digits (data/table rows). ADDITIVE to the top window — surfaces deep tables
    the single term-cluster deep-slice misses. Never touches the top window, so A_v7 answers are
    unchanged; this can only ADD relevant evidence."""
    n = len(note)
    if n <= top_window + 120:
        return []
    hits = _term_hits(note.lower(), terms, top_window)
    hits.extend(_numeric_anchors(note, top_window, deep_window))
    if not hits:
        return []
    hits.sort()
    # `s` and `e` are both non-decreasing in a sorted `h`, so two monotonic cursors give the
    # same [s, e) density count as rescanning every hit for every candidate — in one pass over
    # `hits` instead of one pass per hit.
    total = len(hits)
    lo = hi = 0
    cands: list[tuple[int, int, int]] = []
    for h in hits:
        s = max(top_window, h - deep_window // DEEP_LEAD_DIVISOR)
        e = min(s + deep_window, n)
        while lo < total and hits[lo] < s:
            lo += 1
        while hi < total and hits[hi] < e:
            hi += 1
        cands.append((hi - lo, s, e))          # local density
    cands.sort(reverse=True)                   # densest first
    slices: list[tuple[int, int]] = []
    for _cnt, s, e in cands:
        if len(slices) >= max_slices:
            break
        if e - s < MIN_SLICE_CHARS:
            continue
        if any(not (e <= us or s >= ue) for us, ue in slices):   # overlaps an already-picked slice
            continue
        slices.append((s, e))
    return sorted(slices)


# ══════════════════════════════════════════════════════════════════════════════
# Tool execution
# ══════════════════════════════════════════════════════════════════════════════


def _first_citable(results: object) -> object:
    """The result that will receive the lowest ledger number, i.e. the one whose note the
    caller must read and whose offsets the deep slices describe."""
    for r in results or ():
        if getattr(r, "result_id", None):
            return r
    return None


async def _do_search(query: str, ledger: _Ledger, *, time_left: float = SEARCH_TIMEOUT_S) -> str:
    if not query:
        return "# search_web() -> ERROR: empty query"
    # v2: try providers in order; advance on error OR empty results. Total internal time is
    # bounded to <= 2*SEARCH_TIMEOUT_S (and never more than time_left), so a hung primary can
    # never eat the research budget past the outer wait_for.
    t0 = perf_counter()
    total_budget = min(2.0 * SEARCH_TIMEOUT_S, max(1.0, time_left))
    res = None
    last_exc: Exception | None = None
    for provider in SEARCH_PROVIDERS:
        remaining = total_budget - (perf_counter() - t0)
        if remaining <= PROVIDER_MIN_SLICE_S:
            break
        to = min(SEARCH_TIMEOUT_S, remaining)
        try:
            # v4: hard per-call wait_for so the internal total-time bound holds even if the host
            # ignores the `timeout` arg — lets the outer turn-loop wrapper stay tight (24s).
            res = await asyncio.wait_for(search_web(query, provider=provider, timeout=to),
                                         timeout=to + TOOL_WRAPPER_MARGIN_S)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            res = None
        if res is not None and getattr(res, "results", None):
            break
    if res is None or not getattr(res, "results", None):
        if last_exc is not None:
            return f"# search_web({query!r}) -> ERROR: {last_exc}"
        return f"# search_web({query!r}) -> 0 results"
    pairs = ledger.add(res.receipt_id, res.results, window=SEARCH_WINDOW)
    out = [f"# search_web({query!r}) -> {len(pairs)} results"]
    for n, r in pairs:
        excerpt = (getattr(r, "note", None) or "")[:SEARCH_WINDOW]
        out.append(f"[{n}] {getattr(r, 'title', '') or ''}\n  url: {getattr(r, 'url', '') or ''}\n  {excerpt}")
    return "\n".join(out)


async def _do_fetch(url: str, ledger: _Ledger, *, time_left: float = FETCH_TIMEOUT_S,
                    terms: list[str] | None = None) -> str:
    if not url:
        return "# fetch_page() -> ERROR: empty url"
    # v2: one attempt per provider (parallel then desearch), total time bounded to
    # <= 2*FETCH_TIMEOUT_S and never more than time_left. Provider fallback replaces the old
    # same-provider double-retry: it insures against a provider-wide outage, not a flaky URL.
    t0 = perf_counter()
    total_budget = min(2.0 * FETCH_TIMEOUT_S, max(1.0, time_left))
    res = None
    err: Exception | None = None
    for provider in FETCH_PROVIDERS:
        remaining = total_budget - (perf_counter() - t0)
        if remaining <= PROVIDER_MIN_SLICE_S:
            break
        to = min(FETCH_TIMEOUT_S, remaining)
        try:
            # v4: hard per-call wait_for (see _do_search) so the internal bound holds host-agnostically.
            res = await asyncio.wait_for(fetch_page(url, provider=provider, timeout=to),
                                         timeout=to + TOOL_WRAPPER_MARGIN_S)
        except Exception as exc:  # noqa: BLE001
            err = exc
            res = None
        if res is not None and getattr(res, "results", None):
            break
    if res is None:
        return f"# fetch_page({url!r}) -> ERROR: {err}"
    # A provider can return a non-None response carrying an EMPTY result list. The original
    # then read results[0] unconditionally.
    if GUARD_EMPTY_FETCH_RESULTS and not getattr(res, "results", None):
        if err is not None:
            return f"# fetch_page({url!r}) -> ERROR: {err}"
        return f"# fetch_page({url!r}) -> no content"
    # v4: page top is always shown+cited exactly as base; deep slices are added only where a dense
    # deep cluster exists (see _value_regions). This captures deep-table answers without ever
    # dropping a top-of-page answer. The note read here is the one that becomes the [n] below, so
    # the printed body, the ledger row and the deep offsets all describe the same document.
    primary = _first_citable(res.results) if GUARD_EMPTY_FETCH_RESULTS else res.results[0]
    if primary is None:
        return f"# fetch_page({url!r}) -> no content"
    note = getattr(primary, "note", None) or ""
    # v9: surface MULTIPLE deep regions (term-clusters + numeric/table-dense), additive to the top window.
    deeps = _value_regions(note, terms or [], FETCH_WINDOW)
    pairs = ledger.add(res.receipt_id, res.results, window=FETCH_WINDOW, deeps=deeps)
    if not pairs:
        return f"# fetch_page({url!r}) -> no content"
    top_body = note[:FETCH_WINDOW]
    parts = [top_body]
    for ds, de in deeps:
        parts.append(f"… [continued from char {ds}] …\n{note[ds:de]}")
    body = "\n\n".join(parts)
    tag = f" (+{len(deeps)} deep {sum(de - ds for ds, de in deeps)}c)" if deeps else ""
    return f"# fetch_page({url!r}) -> [{pairs[0][0]}] {len(top_body)}c{tag}\n{body}"


# ══════════════════════════════════════════════════════════════════════════════
# Citation construction
# ══════════════════════════════════════════════════════════════════════════════

_RANGE_RE = re.compile(r"(\d{1,4})\s*-\s*(\d{1,4})")


def _cited_numbers(text: str, *, high: int) -> list[int]:
    ordered: list[int] = []
    seen: set[int] = set()
    for m in _BRACKET_RE.finditer(text):
        for part in m.group(1).split(","):
            part = part.strip()
            if not part:
                continue
            rng = _RANGE_RE.fullmatch(part)
            if rng:
                lo, hi = int(rng.group(1)), int(rng.group(2))
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


def _select_top_slices(cited: list[int], ledger: _Ledger) -> tuple[list[tuple[_LedgerRow, int]], int]:
    """Phase 1 — one top slice [0, top_end] per cited [n], in citation order, under the char cap."""
    selected: list[tuple[_LedgerRow, int]] = []
    spent = 0
    for n in cited:
        if len(selected) >= CITATION_COUNT_CAP:
            break
        row = ledger.row(n)
        if row is None:
            continue
        if row.note_len <= 0:
            continue
        top_end = min(row.top_end or row.window, row.note_len)
        if top_end <= 0:
            continue
        if spent + top_end > EVIDENCE_CHAR_CAP:
            continue
        spent += top_end
        selected.append((row, top_end))
    return selected, spent


def _select_deep_slices(selected: list[tuple[_LedgerRow, int]], spent: int) -> dict[int, list[tuple[int, int]]]:
    """Phase 2 — append deep slices from LEFTOVER budget only, so a deep slice can never
    displace or shrink a top slice that phase 1 already accepted."""
    deep_for: dict[int, list[tuple[int, int]]] = {}
    segments = len(selected)                                  # each top slice counts as one segment
    for idx, (row, top_end) in enumerate(selected):
        for d in (row.deeps or []):
            if segments >= MAX_CITATION_SEGMENTS:
                break
            ds, de = int(d[0]), int(d[1])
            if not (0 <= ds < de <= row.note_len) or (de - ds) < MIN_SLICE_CHARS or ds < top_end:
                continue
            if spent + (de - ds) > EVIDENCE_CHAR_CAP:
                break
            spent += (de - ds)
            segments += 1
            deep_for.setdefault(idx, []).append((ds, de))
    return deep_for


def _build_citations(answer: str, ledger: _Ledger) -> list[CitationRef]:
    """v4: TWO-PHASE. Phase 1 selects one top slice [0, top_end] per cited [n] — byte-identical to
    base's selection and char accounting. Phase 2 appends an optional deep slice ONLY from leftover
    budget, so a deep slice can never displace or shrink a citation base would have included.
    Every slice is >=100 chars and end<=note_len (== source_text length; no server truncation)."""
    cited = _cited_numbers(answer, high=ledger.high())
    selected, spent = _select_top_slices(cited, ledger)
    deep_for = _select_deep_slices(selected, spent)
    refs: list[CitationRef] = []
    for idx, (row, top_end) in enumerate(selected):
        slices = [CitationSlice(start=0, end=top_end)]
        for ds, de in deep_for.get(idx, []):
            slices.append(CitationSlice(start=ds, end=de))
        refs.append(
            CitationRef(
                receipt_id=str(row.receipt_id),
                result_id=str(row.result_id),
                slices=slices,
            )
        )
    return refs


# ══════════════════════════════════════════════════════════════════════════════
# LLM transport
# ══════════════════════════════════════════════════════════════════════════════


async def _chat(messages: list[dict[str, object]], *, deadline: float, final: bool):
    thinking = (
        LlmThinkingConfig(enabled=False)
        if final
        else LlmThinkingConfig(enabled=True, effort="low")
    )
    # v2: primary model gets LLM_TRY_PER_TURN attempts; if all fail (provider throttled/erroring
    # glm-5 for the whole batch — the SPOF), fall through to one attempt on the fallback model
    # before giving up. When glm-5 is healthy the fallback is never reached.
    attempts: list[tuple[str, int]] = [(PRIMARY_MODEL, LLM_TRY_PER_TURN), (FALLBACK_MODEL, 1)]
    for model, tries in attempts:
        for _ in range(tries):
            budget = deadline - perf_counter()
            if budget <= CHAT_MIN_BUDGET_S:
                return None
            to = min(LLM_TURN_TIMEOUT_S, budget)
            try:
                # asyncio.wait_for is a hard client-side cap in case the host ignores `timeout`,
                # so our internal deadline is always enforced and we never hit the 300s kill.
                return await asyncio.wait_for(
                    llm_chat(
                        provider=LLM_PROVIDER,
                        model=model,
                        messages=messages,
                        tools=None if final else _TOOL_SPECS,
                        tool_choice=None if final else "auto",
                        temperature=0.2,
                        thinking=thinking,
                        timeout=to,
                    ),
                    timeout=to + CHAT_WRAPPER_MARGIN_S,
                )
            except Exception:  # noqa: BLE001
                continue
    return None


async def _forced_commit(question: str, ledger: _Ledger, *, deadline: float) -> str | None:
    """Commit from a CLEAN numbered evidence digest (no tool-call history): a small, fast,
    reliable context that avoids the provider fragility of forcing tools-off over a long
    tool-call transcript. This is what makes a run that gathered evidence never surrender
    an empty non-answer."""
    digest = ledger.digest(char_cap=DIGEST_CHAR_CAP)
    if not digest:
        return None
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + HARD_COMMIT},
        {"role": "user", "content": (
            question
            + "\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n"
            + digest
        )},
    ]
    for attempt in range(COMMIT_ATTEMPTS):
        if deadline - perf_counter() <= COMMIT_MIN_SLICE_S:
            break
        result = await _chat(msgs, deadline=deadline, final=True)
        if result is None:
            break
        text = (result.response.raw_text or "").strip()
        if text and _is_valid_final_answer(text):
            return text
        # Invalid answer — add stronger nudge and retry
        if attempt < COMMIT_ATTEMPTS - 1:
            msgs.append({"role": "assistant", "content": text or "(empty response)"})
            msgs.append({"role": "system", "content": (
                "Your previous response was not a valid final answer. "
                "You MUST start with 'FINAL ANSWER:' followed by your best cited answer. "
                "Do NOT refuse or hedge — give the best answer you can from the evidence above."
            )})
    return None


def _finalize(answer: str, ledger: _Ledger) -> Response:
    citations = _build_citations(answer, ledger)
    return Response(text=answer, citations=citations or None)


# ══════════════════════════════════════════════════════════════════════════════
# Orchestration
# ══════════════════════════════════════════════════════════════════════════════


async def _bootstrap(question: str, ledger: _Ledger, messages: list[dict[str, object]]) -> None:
    """Seed grounded evidence in parallel so the store is never empty on turn 1."""
    try:
        seeds = _seed_queries(question)
        # v2: give each seed enough budget that a fast-failing primary can still fall back to
        # desearch (fast connection error + one fallback attempt fits well inside the wrapper).
        seeded = await asyncio.wait_for(
            asyncio.gather(*(_do_search(s, ledger, time_left=SEARCH_TIMEOUT_S + SEED_EXTRA_S)
                             for s in seeds)),
            timeout=SEARCH_TIMEOUT_S + SEED_WRAPPER_MARGIN_S,
        )
        if ledger.high() > 0:
            messages.append({
                "role": "system",
                "content": "Preliminary automatic searches (already numbered; search more as needed):\n\n"
                + "\n\n".join(seeded),
            })
    except Exception:  # noqa: BLE001
        pass


async def _run_tool_call(tc, ledger: _Ledger, *, time_left: float, terms: list[str],
                         seen_searches: dict[str, str]) -> str:
    """Dispatch one tool call and return the text that becomes its tool message."""
    try:
        args = json.loads(tc.arguments or "{}")
    except json.JSONDecodeError:
        args = {}
    if tc.name == "search_web":
        q = str(args.get("query", ""))
        norm = " ".join(q.lower().split())
        # v4 (b1): skip a genuinely redundant identical search that already returned
        # results — hand back the prior [n]s instead of burning another round-trip.
        if norm and norm in seen_searches:
            return f"# search_web({q!r}) -> already searched; see {seen_searches[norm]}"
        # v4 (b2): internal per-call wait_for enforces the total bound, so the
        # outer wrapper can stay tight at 24s (base-like margin, no 44s overshoot).
        content = await asyncio.wait_for(
            _do_search(q, ledger, time_left=time_left),
            timeout=2.0 * SEARCH_TIMEOUT_S + SEARCH_WRAPPER_MARGIN_S,
        )
        if norm and " results" in content and "-> 0 results" not in content:
            seen_searches[norm] = f"prior results up to [{ledger.high()}]"
        return content
    if tc.name == "fetch_page":
        return await asyncio.wait_for(
            _do_fetch(str(args.get("url", "")), ledger, time_left=time_left, terms=terms),
            timeout=FETCH_TIMEOUT_S * FETCH_TRIES + FETCH_WRAPPER_MARGIN_S,
        )
    return f"# unsupported tool {tc.name!r}"


@entrypoint("query")
async def query(query: Query) -> Response:
    deadline = perf_counter() + TOTAL_BUDGET_S
    research_deadline = deadline - COMMIT_RESERVE_S
    ledger = _Ledger()
    query_terms = _salient_terms(query.text)             # v4: used to detect a deep fetch cluster
    seen_searches: dict[str, str] = {}                   # v4: normalized query -> prior result summary (dedup)
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query.text},
    ]

    await _bootstrap(query.text, ledger, messages)

    final_answer: str | None = None
    nudged = False
    try:
        for turn in range(1, MAX_TURNS + 1):
            remaining = research_deadline - perf_counter()
            if remaining <= RESEARCH_MIN_SLICE_S:
                break  # stop researching; the reserved tail is for the guaranteed commit
            turns_left = MAX_TURNS - turn + 1
            if turns_left <= COMMIT_LOOKAHEAD_TURNS and not nudged:
                messages.append({"role": "system", "content": COMMIT_NUDGE.format(secs=int(deadline - perf_counter()))})
                nudged = True

            result = await _chat(messages, deadline=research_deadline, final=False)
            if result is None:
                break
            message = result.response.choices[0].message
            tool_calls = message.tool_calls or ()
            if not tool_calls:
                text = (result.response.raw_text or "").strip()
                if text:
                    if _is_valid_final_answer(text):
                        final_answer = text
                        break
                    # Invalid answer — nudge and continue
                    if not nudged:
                        messages.append({"role": "system", "content": HARD_COMMIT})
                        nudged = True
                    continue
                # An empty no-tool turn is a stall, not an answer: push to commit and keep going.
                if not nudged:
                    messages.append({"role": "system", "content": HARD_COMMIT})
                    nudged = True
                continue

            messages.append({
                "role": "assistant",
                "content": result.response.raw_text,
                "tool_calls": [
                    {"id": tc.id, "type": tc.type, "name": tc.name, "arguments": tc.arguments}
                    for tc in tool_calls
                ],
            })
            over_budget = False
            for tc in tool_calls:
                time_left = research_deadline - perf_counter()
                if time_left <= TOOL_MIN_SLICE_S:
                    over_budget = True  # stop tools here so the commit reserve is never eaten
                    break
                try:
                    content = await _run_tool_call(
                        tc, ledger, time_left=time_left, terms=query_terms,
                        seen_searches=seen_searches,
                    )
                except Exception:  # noqa: BLE001
                    content = f"# {tc.name} exceeded its time budget"
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": content})
            if over_budget:
                break

        # Guaranteed commit: if the loop never produced a non-empty answer, force one now
        # from the clean evidence digest (reliable even when the transcript is long).
        if not final_answer and ledger.high() > 0:
            final_answer = await _forced_commit(query.text, ledger, deadline=deadline)
        if not final_answer:
            return Response(text=FALLBACK_TEXT)
        return _finalize(final_answer, ledger)
    except Exception:  # noqa: BLE001
        try:
            salvaged = await _forced_commit(query.text, ledger, deadline=deadline)
            if salvaged:
                return _finalize(salvaged, ledger)
        except Exception:  # noqa: BLE001
            pass
        return Response(text=FALLBACK_TEXT)

# slot: harnyx 2026-07-28T13:14:58+00:00

# perfect_suffix: openrouter/parallel
_PERFECT_SUFFIX = "ef6209e366bf3a37"
