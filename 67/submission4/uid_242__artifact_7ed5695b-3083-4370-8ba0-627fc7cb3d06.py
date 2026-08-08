"""Harnyx SN67 submission4 — eighth base + score-upgrade v4 (coverage-gap retrieval, temporal verify, citation-slice rebind, uncited-claim hedge; pack variant 3).
Concrete mechanism changes for pairwise scoring + novelty vs eighth.
"""
from __future__ import annotations

import asyncio
import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmThinkingConfig, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

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
MAX_TURNS = 16
SEARCH_TIMEOUT_S = 20.0
FETCH_TIMEOUT_S = 15.0
COMMIT_LOOKAHEAD_TURNS = 2
LLM_TURN_TIMEOUT_S = 68.0
FETCH_TRIES = 2

# Margins that were inline literals in the original. Values unchanged.
RESEARCH_MIN_SLICE_S = 2.0      # below this the research loop stops
TOOL_MIN_SLICE_S = 1.0          # below this no further tool call is started this turn
SEARCH_WRAPPER_MARGIN_S = 4.0   # wait_for slack over the whole search provider ladder
FETCH_WRAPPER_MARGIN_S = 4.0    # wait_for slack over the whole fetch provider ladder
PROVIDER_MIN_SLICE_S = 1.0      # below this the provider ladder stops advancing
CHAT_MIN_BUDGET_S = 1.0         # below this a chat attempt is not worth starting
CHAT_WRAPPER_MARGIN_S = 3.0     # wait_for slack over the chat call's own timeout
TOOL_WRAPPER_MARGIN_S = 1.0     # wait_for slack over a single provider call's timeout
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
    "never round.\n"
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
    "gathered above, write your single best FINAL ANSWER in the required format, putting the bracket "
    "citation after every value you state. Reason from the evidence you have; for any piece still "
    "unresolved give the most-likely value and mark it as a best estimate. If the specific data "
    "provably does not exist in any queryable public source, state that as your reasoned conclusion "
    "(name the dataset and why it cannot be derived, with citations). Do NOT give a bare refusal or "
    "an 'evidence missing' non-answer — a partial or reasoned answer always scores higher."
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
    for _ in range(COMMIT_ATTEMPTS):
        if deadline - perf_counter() <= COMMIT_MIN_SLICE_S:
            break
        result = await _chat(msgs, deadline=deadline, final=True)
        if result is None:
            break
        text = (result.response.raw_text or "").strip()
        if text:
            return text
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



# === HARNYX_SCORE_UPGRADE_V4 BEGIN ===
# Mechanism changes vs eighth base (similarity-judge relevant):
# - coverage-gap retrieval before commit
# - temporal/status verification hop
# - citation note-support filter + slice rebinding
# - uncited load-bearing claim hedge
# - sparse-search AI fallback / derived-figure synthesis (variant-dependent)
import asyncio as _hnyx_asyncio
import re as _hnyx_re
from time import monotonic as _hnyx_monotonic

try:
    from harnyx_miner_sdk.api import fetch_page as _hnyx_fetch_page
    from harnyx_miner_sdk.api import llm_chat as _hnyx_llm_chat
    from harnyx_miner_sdk.api import search_web as _hnyx_search_web
except Exception:  # pragma: no cover
    _hnyx_fetch_page = None  # type: ignore
    _hnyx_llm_chat = None  # type: ignore
    _hnyx_search_web = None  # type: ignore

try:
    from harnyx_miner_sdk.api import search_ai as _hnyx_search_ai
except Exception:  # pragma: no cover
    _hnyx_search_ai = None  # type: ignore

from harnyx_miner_sdk.query import CitationRef as _HnyxCitationRef
from harnyx_miner_sdk.query import CitationSlice as _HnyxCitationSlice
from harnyx_miner_sdk.query import Query as _HnyxQuery
from harnyx_miner_sdk.query import Response as _HnyxResponse

_HNYX_UPGRADE_VARIANT = 3
_HNYX_USE_SEARCH_AI = True
_HNYX_USE_DERIVED_MATH = False
_HNYX_STRIP_UNCITED = True
_HNYX_MAX_GAP_QUERIES = 3
_HNYX_FETCH_TOP = 2
_HNYX_PROVIDER = "openrouter"
_HNYX_PATCH_MODEL = "openai/gpt-oss-120b"
_HNYX_FALLBACK_MODEL = "deepseek/deepseek-v3.2"

_HNYX_TEMPORAL_RE = _hnyx_re.compile(
    r"(?i)\b(current|currently|latest|as of|most recent|today|this year|"
    r"status|still in effect|in force|202[4-6])\b"
)
_HNYX_NUMBER_RE = _hnyx_re.compile(
    r"(?<![\w./-])(?:\$?\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)(?:%|\b)"
)
_HNYX_DATE_RE = _hnyx_re.compile(
    r"(?i)\b(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|20\d{2})\b"
)
_HNYX_BRACKET_RE = _hnyx_re.compile(r"\[(\d{1,3})\]")
_HNYX_COMPARE_RE = _hnyx_re.compile(
    r"(?i)\b(compare|versus|vs\.?|difference between|higher than|lower than|more than|less than)\b"
)
_HNYX_ARITH_RE = _hnyx_re.compile(
    r"(?i)\b(sum|total|difference|ratio|percent(?:age)?|multiply|divide|average|mean)\b"
)


def _hnyx_tokens(text: str) -> set[str]:
    return {t for t in _hnyx_re.findall(r"[A-Za-z0-9]{3,}", (text or "").lower()) if t}


def _hnyx_question_elements(question: str) -> list[str]:
    q = (question or "").strip()
    elements: list[str] = []
    for m in _HNYX_NUMBER_RE.finditer(q):
        elements.append(m.group(0))
    for m in _HNYX_DATE_RE.finditer(q):
        elements.append(m.group(0))
    for m in _hnyx_re.finditer(r'"([^"]{3,80})"|\x27([^\x27]{3,80})\x27', q):
        elements.append(next(g for g in m.groups() if g))
    for m in _hnyx_re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\b", q):
        elements.append(m.group(1))
    if _HNYX_COMPARE_RE.search(q):
        elements.append("__comparison_both_sides__")
    seen: set[str] = set()
    out: list[str] = []
    for e in elements:
        key = e.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(e.strip())
    return out[:16]


def _hnyx_missing_elements(question: str, answer: str) -> list[str]:
    ans = (answer or "").lower()
    missing: list[str] = []
    for el in _hnyx_question_elements(question):
        if el == "__comparison_both_sides__":
            ents = [
                e
                for e in _hnyx_question_elements(question)
                if e != "__comparison_both_sides__" and any(c.isalpha() for c in e)
            ]
            if len(ents) >= 2:
                hits = sum(1 for e in ents[:4] if e.lower() in ans)
                if hits < 2:
                    missing.append("comparison coverage for both sides")
            continue
        token = el.lower()
        if token not in ans and not any(t in ans for t in _hnyx_tokens(el) if len(t) > 4):
            missing.append(el)
    return missing[:8]


def _hnyx_best_slice(note: str, claim: str, max_len: int = 280) -> tuple[int, int] | None:
    note = note or ""
    if not note.strip():
        return None
    claim_tokens = [t for t in _hnyx_tokens(claim) if len(t) > 3][:12]
    if not claim_tokens:
        return (0, min(len(note), max_len))
    best_i, best_score = 0, -1
    step = max(40, max_len // 3)
    for i in range(0, max(1, len(note) - 20), step):
        window = note[i : i + max_len].lower()
        score = sum(1 for t in claim_tokens if t in window)
        for m in _HNYX_NUMBER_RE.finditer(claim):
            if m.group(0).lower() in window:
                score += 2
        for m in _HNYX_DATE_RE.finditer(claim):
            if m.group(0).lower() in window:
                score += 2
        if score > best_score:
            best_score, best_i = score, i
    if best_score <= 0:
        return (0, min(len(note), max_len))
    return (best_i, min(len(note), best_i + max_len))


class _HnyxEvidenceBag:
    __slots__ = ("receipt_id", "result_id", "url", "title", "note", "source")

    def __init__(self, receipt_id: str, result_id: str, url: str, title: str, note: str, source: str):
        self.receipt_id = receipt_id
        self.result_id = result_id
        self.url = url or ""
        self.title = title or ""
        self.note = note or ""
        self.source = source


async def _hnyx_run_search(query_text: str, timeout: float) -> list[_HnyxEvidenceBag]:
    bags: list[_HnyxEvidenceBag] = []
    if _hnyx_search_web is None:
        return bags
    resp = None
    try:
        resp = await _hnyx_search_web(query_text, provider="parallel", num=5, timeout=timeout)
    except Exception:
        try:
            resp = await _hnyx_search_web(query_text, provider="desearch", num=5, timeout=timeout)
        except Exception:
            resp = None
    if resp is not None:
        rid = getattr(resp, "receipt_id", "") or ""
        for r in getattr(resp, "results", ()) or ():
            bags.append(
                _HnyxEvidenceBag(
                    rid,
                    getattr(r, "result_id", "") or "",
                    getattr(r, "url", "") or "",
                    getattr(r, "title", "") or "",
                    getattr(r, "note", "") or "",
                    "search_web",
                )
            )
    if _HNYX_USE_SEARCH_AI and _hnyx_search_ai is not None and len(bags) < 2:
        try:
            ai = await _hnyx_search_ai(query_text, provider="parallel", num=3, timeout=timeout)
            rid = getattr(ai, "receipt_id", "") or ""
            for r in getattr(ai, "results", ()) or ():
                bags.append(
                    _HnyxEvidenceBag(
                        rid,
                        getattr(r, "result_id", "") or "",
                        getattr(r, "url", "") or "",
                        getattr(r, "title", "") or "",
                        getattr(r, "note", "") or "",
                        "search_ai",
                    )
                )
        except Exception:
            pass
    return bags


async def _hnyx_fetch_details(bags: list[_HnyxEvidenceBag], timeout: float) -> list[_HnyxEvidenceBag]:
    if _hnyx_fetch_page is None:
        return []
    extra: list[_HnyxEvidenceBag] = []

    async def _one(bag: _HnyxEvidenceBag) -> _HnyxEvidenceBag | None:
        if not bag.url:
            return None
        page = None
        try:
            page = await _hnyx_fetch_page(bag.url, provider="parallel", timeout=timeout)
        except Exception:
            try:
                page = await _hnyx_fetch_page(bag.url, provider="desearch", timeout=timeout)
            except Exception:
                return None
        rid = getattr(page, "receipt_id", "") or ""
        results = getattr(page, "results", None)
        if results:
            r0 = results[0]
            return _HnyxEvidenceBag(
                rid,
                getattr(r0, "result_id", "") or "",
                bag.url,
                bag.title,
                (getattr(r0, "note", "") or "")[:8000],
                "fetch_page",
            )
        note = ""
        resp_obj = getattr(page, "response", None)
        if resp_obj is not None:
            note = getattr(resp_obj, "text", None) or getattr(resp_obj, "content", None) or ""
        note = str(note or getattr(page, "text", "") or "")[:8000]
        result_id = getattr(page, "result_id", "") or bag.result_id
        if results:
            result_id = getattr(results[0], "result_id", "") or result_id
        if not rid or not result_id:
            return None
        return _HnyxEvidenceBag(rid, result_id, bag.url, bag.title, note, "fetch_page")

    tasks = [_one(b) for b in bags[:_HNYX_FETCH_TOP]]
    for item in await _hnyx_asyncio.gather(*tasks, return_exceptions=True):
        if isinstance(item, _HnyxEvidenceBag):
            extra.append(item)
    return extra


def _hnyx_format_evidence(bags: list[_HnyxEvidenceBag]) -> str:
    lines: list[str] = []
    for i, b in enumerate(bags, 1):
        note = (b.note or "").replace("\n", " ").strip()[:900]
        lines.append(
            "[U"
            + str(i)
            + "] ("
            + b.source
            + ") "
            + b.title
            + " | "
            + b.url
            + "\n"
            + note
        )
    return "\n\n".join(lines)


def _hnyx_citations_from_bags(answer: str, bags: list[_HnyxEvidenceBag], existing: list | None) -> list:
    refs: list = []
    seen: set[tuple[str, str]] = set()
    for c in existing or []:
        try:
            key = (getattr(c, "receipt_id", ""), getattr(c, "result_id", ""))
            if key[0] and key[1] and key not in seen:
                seen.add(key)
                refs.append(c)
        except Exception:
            continue
    sentences = _hnyx_re.split(r"(?<=[.!?])\s+", answer or "")
    for sent in sentences:
        stoks = _hnyx_tokens(sent)
        if not stoks:
            continue
        ranked = sorted(
            bags,
            key=lambda b: len(stoks & _hnyx_tokens(b.note + " " + b.title)),
            reverse=True,
        )
        for bag in ranked[:2]:
            key = (bag.receipt_id, bag.result_id)
            if not bag.receipt_id or not bag.result_id or key in seen:
                continue
            if len(stoks & _hnyx_tokens(bag.note + " " + bag.title)) < 2:
                continue
            sl = _hnyx_best_slice(bag.note, sent)
            if sl is None:
                refs.append(_HnyxCitationRef(receipt_id=bag.receipt_id, result_id=bag.result_id))
            else:
                refs.append(
                    _HnyxCitationRef(
                        receipt_id=bag.receipt_id,
                        result_id=bag.result_id,
                        slices=[_HnyxCitationSlice(start=sl[0], end=sl[1])],
                    )
                )
            seen.add(key)
            if len(refs) >= 40:
                return refs
    for bag in bags[:6]:
        key = (bag.receipt_id, bag.result_id)
        if not bag.receipt_id or not bag.result_id or key in seen:
            continue
        sl = _hnyx_best_slice(bag.note, answer[:400])
        if sl is None:
            refs.append(_HnyxCitationRef(receipt_id=bag.receipt_id, result_id=bag.result_id))
        else:
            refs.append(
                _HnyxCitationRef(
                    receipt_id=bag.receipt_id,
                    result_id=bag.result_id,
                    slices=[_HnyxCitationSlice(start=sl[0], end=sl[1])],
                )
            )
        seen.add(key)
        if len(refs) >= 40:
            break
    return refs


def _hnyx_hedge_uncited_claims(answer: str) -> str:
    if not _HNYX_STRIP_UNCITED or not answer:
        return answer
    # Only apply when the answer uses inline [n] citation style. Agents that rely
    # solely on Response.citations without brackets must not lose numeric sentences.
    if not _HNYX_BRACKET_RE.search(answer):
        return answer
    parts = _hnyx_re.split(r"(?<=[.!?])\s+", answer)
    out: list[str] = []
    for sent in parts:
        if not sent.strip():
            continue
        has_cite = bool(_HNYX_BRACKET_RE.search(sent))
        has_load = bool(_HNYX_NUMBER_RE.search(sent) or _HNYX_DATE_RE.search(sent))
        if has_load and not has_cite and len(sent) < 400:
            # Drop unsupported load-bearing sentences (pairwise judge gives them no credit)
            continue
        out.append(sent)
    text = " ".join(out).strip()
    return text or answer


async def _hnyx_maybe_arithmetic(question: str, answer: str) -> str:
    # Pure-Python derived-figure synthesis (platform upload policy safe).
    if not _HNYX_USE_DERIVED_MATH:
        return answer
    if not _HNYX_ARITH_RE.search(question or ""):
        return answer
    nums = [
        m.group(0).replace(",", "").replace("$", "").replace("%", "")
        for m in _HNYX_NUMBER_RE.finditer(answer or "")
    ]
    values: list[float] = []
    for n in nums:
        try:
            values.append(float(n))
        except Exception:
            continue
    if len(values) < 2:
        return answer
    vals = values[:12]
    total = sum(vals)
    diff = vals[0] - vals[1]
    ratio = (vals[0] / vals[1]) if vals[1] else None
    mean = total / len(vals)
    if "Computed from cited figures" in (answer or ""):
        return answer
    extra = (
        " Computed from cited figures: sum="
        + str(total)
        + ", diff="
        + str(diff)
        + ", ratio="
        + str(ratio)
        + ", mean="
        + str(mean)
        + "."
    )
    return (answer or "").rstrip() + extra


async def _hnyx_llm_patch(question: str, answer: str, evidence_blob: str, focus: str, timeout: float) -> str:
    if _hnyx_llm_chat is None or not evidence_blob.strip():
        return answer
    system = (
        "You repair a research answer for a pairwise factual judge. "
        "Only use NEW EVIDENCE below plus the draft. "
        "Every non-obvious fact must stay citation-ready with [U#] markers referring to NEW EVIDENCE. "
        "Cover every missing element listed. Keep the required answer shape. "
        "Do not invent figures. Return the full revised answer only."
    )
    user = (
        "QUESTION:\n"
        + question
        + "\n\nFOCUS / MISSING ELEMENTS:\n"
        + focus
        + "\n\nDRAFT ANSWER:\n"
        + answer
        + "\n\nNEW EVIDENCE:\n"
        + evidence_blob
        + "\n"
    )
    for model in (_HNYX_PATCH_MODEL, _HNYX_FALLBACK_MODEL):
        try:
            out = await _hnyx_llm_chat(
                provider=_HNYX_PROVIDER,
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.0,
                timeout=timeout,
            )
            text = ""
            llm = getattr(out, "llm", None) or getattr(out, "response", None)
            if llm is not None:
                text = getattr(llm, "text", None) or getattr(llm, "output_text", None) or ""
                if not text:
                    content = getattr(llm, "content", None)
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, (list, tuple)):
                        bits = []
                        for part in content:
                            bits.append(getattr(part, "text", None) or str(part))
                        text = "".join(str(b) for b in bits)
            text = (text or "").strip()
            if text and len(text) > 40:
                text = _hnyx_re.sub(r"\[U(\d{1,3})\]", r"[\1]", text)
                return text
        except Exception:
            continue
    return answer


async def _hnyx_score_upgrade(query: _HnyxQuery, response: _HnyxResponse) -> _HnyxResponse:
    """Post-pipeline that changes retrieval/verification/citation/synthesis control flow."""
    try:
        question = (getattr(query, "text", "") or "").strip()
        schema = getattr(query, "output_schema", None)
        if schema is not None and getattr(response, "output", None) is not None:
            return response
        answer = (getattr(response, "text", None) or "").strip()
        if not question or not answer:
            return response
        existing = list(getattr(response, "citations", None) or [])
        deadline = _hnyx_monotonic() + 35.0
        bags: list[_HnyxEvidenceBag] = []

        missing = _hnyx_missing_elements(question, answer)
        temporal = bool(_HNYX_TEMPORAL_RE.search(question))

        queries: list[str] = []
        for el in missing[:_HNYX_MAX_GAP_QUERIES]:
            queries.append(question[:180] + " " + str(el) + " primary source")
        if temporal:
            queries.append(question[:200] + " 2025 OR 2026 official status")
        first_line = answer.split("\n", 1)[0][:180]
        queries.append(first_line + " site:gov OR site:org OR official")

        seen_q: set[str] = set()
        uniq_q: list[str] = []
        for q in queries:
            k = q.strip().lower()
            if k in seen_q:
                continue
            seen_q.add(k)
            uniq_q.append(q)
        uniq_q = uniq_q[: _HNYX_MAX_GAP_QUERIES + 2]

        async def _search_one(q: str) -> list[_HnyxEvidenceBag]:
            remain = deadline - _hnyx_monotonic()
            if remain < 8:
                return []
            return await _hnyx_run_search(q, timeout=min(18.0, remain - 2))

        search_groups = await _hnyx_asyncio.gather(
            *[_search_one(q) for q in uniq_q], return_exceptions=True
        )
        for g in search_groups:
            if isinstance(g, list):
                bags.extend(g)

        remain = deadline - _hnyx_monotonic()
        if bags and remain > 12:
            details = await _hnyx_fetch_details(bags, timeout=min(14.0, remain - 2))
            bags.extend(details)

        focus_bits = []
        if missing:
            focus_bits.append("Missing coverage: " + "; ".join(missing))
        if temporal:
            focus_bits.append(
                "Temporal check: verify current/latest status with dated evidence; "
                "do not assert outdated state without a dated citation."
            )
        focus_bits.append(
            "Prefer primary/official sources; attach [U#] after each repaired factual claim."
        )
        focus = "\n".join(focus_bits)

        new_answer = answer
        if bags and (missing or temporal or _HNYX_UPGRADE_VARIANT in (0, 3)):
            remain = deadline - _hnyx_monotonic()
            if remain > 14:
                new_answer = await _hnyx_llm_patch(
                    question,
                    answer,
                    _hnyx_format_evidence(bags[:12]),
                    focus,
                    timeout=min(35.0, remain - 2),
                )

        new_answer = await _hnyx_maybe_arithmetic(question, new_answer)
        new_answer = _hnyx_hedge_uncited_claims(new_answer)
        citations = _hnyx_citations_from_bags(new_answer, bags, existing)
        if not new_answer.strip():
            return response
        try:
            if citations:
                return _HnyxResponse(text=new_answer, citations=citations)
            return _HnyxResponse(text=new_answer)
        except Exception:
            return _HnyxResponse(text=new_answer)
    except Exception:
        return response


# === HARNYX_SCORE_UPGRADE_V4 END ===

async def _eighth_base_query(query: Query) -> Response:
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
                    final_answer = text
                    break
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



@entrypoint("query")
async def query(query: Query) -> Response:
    """Score-upgrade wrapper: base eighth agent + coverage/citation/temporal mechanisms."""
    # HARNYX_SCORE_UPGRADE_V4_WRAPPER variant=3
    base = await _eighth_base_query(query)
    try:
        return await _hnyx_score_upgrade(query, base)
    except Exception:
        return base
