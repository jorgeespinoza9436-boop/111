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
"""
from __future__ import annotations

import asyncio
import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmThinkingConfig, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

# ---- Providers / model (matched to funded BYOK keys: openrouter + parallel) -------------
# v2: add fallbacks so a single-provider outage can no longer 0.0 a whole batch (the SPOF the
# lean-agent teardown flagged). glm-5 is primary; deepseek-v3.2 is the reasoning fallback.
# parallel is primary search/fetch; desearch is the fallback when parallel errors or returns empty.
LLM_PROVIDER = "openrouter"
PRIMARY_MODEL = "z-ai/glm-5"
FALLBACK_MODEL = "deepseek/deepseek-v3.2"
SEARCH_PROVIDER = "parallel"
SEARCH_PROVIDERS = ("parallel", "desearch")   # primary then fallback, tried in order
FETCH_PROVIDERS = ("parallel", "desearch")

# ---- Budget / turn governor -------------------------------------------------------------
TOTAL_BUDGET_S = 285.0          # validator kills at 300s; keep a tail for the guaranteed commit
COMMIT_RESERVE_S = 45.0         # tail reserved purely for the forced final commit
COMMIT_LOOKAHEAD_TURNS = 2
MAX_TURNS = 16
LLM_TURN_TIMEOUT_S = 68.0
LLM_TRY_PER_TURN = 2
SEARCH_TIMEOUT_S = 20.0
FETCH_TIMEOUT_S = 15.0
FETCH_TRIES = 2

# ---- Evidence / citation-safety bounds --------------------------------------------------
SEARCH_WINDOW = 700             # chars of a search note surfaced to the model = slice width
FETCH_WINDOW = 6000             # chars of a fetched page surfaced to the model = slice width
CITATION_COUNT_CAP = 20
EVIDENCE_CHAR_CAP = 112_000     # sum of materialized slice widths kept under the ~120k wall
DIGEST_CHAR_CAP = 90_000        # size of the clean evidence digest fed to the forced commit
# v4: the page top (FETCH_WINDOW) is ALWAYS shown+cited exactly as base does (never regresses a
# top-of-page answer). A second "deep" slice is added ONLY when a genuine deep term-cluster exists
# that is denser than the whole top window — capturing v3's deep-table win without v3's regression.
DEEP_WINDOW = 2600              # width of each targeted deep slice
DEEP_MIN_HITS = 2              # min salient-term hits inside the deep window to bother adding it
# v9 structured-extraction: surface MULTIPLE deep regions of a fetched doc (not just one), including
# NUMERIC/TABLE-dense regions the question-terms don't hit — so deep data tables (INSEE PDF, 10-K
# property tables, Box-Office per-studio rows) become visible past the 6000-char top window. Purely
# ADDITIVE to A_v7's top window + synthesis (so A_v7's existing wins cannot regress).
MAX_DEEP_SLICES = 4             # max extra deep regions surfaced per fetched page
NUMERIC_DENSITY_MIN = 55        # digits within a deep_window to treat it as a data/table region

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


class _Ledger:
    """Assigns each surfaced tool result a stable number and remembers how to cite it safely,
    plus the shown text so a clean evidence digest can be rebuilt for the forced commit."""

    def __init__(self) -> None:
        self._rows: dict[int, dict[str, object]] = {}
        self._n = 0

    def add(self, receipt_id: str, results: object, *, window: int,
            deeps: list[tuple[int, int]] | None = None) -> list[int]:
        # v9: `deeps` is a LIST of (start,end) windows into the SAME note, each disjoint from and after
        # the top window (search calls pass deeps=None → byte-identical to base; only fetch adds them).
        # The top window [0:top_end] is ALWAYS stored/shown/cited unchanged, so A_v7's answers can't
        # regress; the deep slices only ADD relevant deep-table evidence.
        assigned: list[int] = []
        for r in results or ():
            rid = getattr(r, "result_id", None)
            if not rid:
                continue
            self._n += 1
            note = getattr(r, "note", None) or ""
            top_end = min(window, len(note))
            text = note[:top_end]
            kept: list[tuple[int, int]] = []
            for d in (deeps or []):
                ds, de = int(d[0]), min(int(d[1]), len(note))
                if de - ds < 100 or ds < top_end:                       # >=100 chars & after the top window
                    continue
                if any(not (de <= es or ds >= ee) for es, ee in kept):  # disjoint from already-kept slices
                    continue
                kept.append((ds, de))
                text = f"{text}\n…\n{note[ds:de]}"                       # digest/forced-commit see deep regions too
            self._rows[self._n] = {
                "receipt_id": receipt_id,
                "result_id": rid,
                "window": window,
                "note_len": len(note),
                "top_end": top_end,
                "deeps": kept,
                "text": text,
                "title": (getattr(r, "title", None) or "")[:160],
                "url": getattr(r, "url", None) or "",
            }
            assigned.append(self._n)
        return assigned

    def row(self, n: int) -> dict[str, object] | None:
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
            text = str(row.get("text") or "")
            if not text:
                continue
            block = f"[{n}] {row.get('title') or ''} ({row.get('url') or ''})\n{text}"
            if spent + len(block) > char_cap:
                continue
            spent += len(block)
            parts.append(block)
        return "\n\n".join(parts)


def _seed_queries(question: str) -> list[str]:
    """Two deterministic bootstrap queries: the raw question, plus its salient content tokens."""
    q = " ".join(question.split())
    seeds = [q[:300]]
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-']+", question)
    salient = [t for t in tokens if t.lower() not in _STOPWORDS and (t[0].isupper() or any(c.isdigit() for c in t))]
    if salient:
        compact = " ".join(dict.fromkeys(salient))[:220]
        if compact and compact.lower() != q[:220].lower():
            seeds.append(compact)
    return seeds[:2]


def _salient_terms(text: str) -> list[str]:
    """Lower-cased content tokens of the question, stopwords dropped — used to detect a deep cluster."""
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-']+", text or "")
    return list(dict.fromkeys(t.lower() for t in tokens if len(t) > 2 and t.lower() not in _STOPWORDS))


def _deep_cluster_offset(note: str, terms: list[str], top_window: int, deep_window: int) -> int | None:
    """Offset (>= top_window) of the deep_window span densest in question terms, or None.

    Returns None unless a genuine deep cluster exists that is AT LEAST as term-dense as the entire
    top window — so a top-of-page answer never triggers a deep slice (the property v3 lacked)."""
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
    top_hits = sum(1 for h in hits if h < top_window)
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
    # Only add a deep slice if the deep cluster is meaningful AND at least as dense as the top region.
    if best_off is None or best_count < DEEP_MIN_HITS or best_count < top_hits:
        return None
    return max(top_window, min(best_off - deep_window // 8, n - deep_window))


def _value_regions(note: str, terms: list[str], top_window: int, *,
                   deep_window: int = DEEP_WINDOW, max_slices: int = MAX_DEEP_SLICES) -> list[tuple[int, int]]:
    """v9: up to `max_slices` disjoint (start,end) windows AFTER top_window that are densest in
    question terms OR in digits (data/table rows). ADDITIVE to the top window — surfaces deep tables
    the single term-cluster deep-slice misses. Never touches the top window, so A_v7 answers are
    unchanged; this can only ADD relevant evidence."""
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
        if sum(c.isdigit() for c in note[i:i + deep_window]) >= NUMERIC_DENSITY_MIN:
            hits.append(i)
        i += step
    if not hits:
        return []
    hits.sort()
    cands: list[tuple[int, int, int]] = []
    for h in hits:
        s = max(top_window, h - deep_window // 8)
        e = min(s + deep_window, n)
        cnt = sum(1 for x in hits if s <= x < e)          # local density
        cands.append((cnt, s, e))
    cands.sort(reverse=True)                               # densest first
    slices: list[tuple[int, int]] = []
    for _cnt, s, e in cands:
        if len(slices) >= max_slices:
            break
        if e - s < 100:
            continue
        if any(not (e <= us or s >= ue) for us, ue in slices):   # overlaps an already-picked slice
            continue
        slices.append((s, e))
    return sorted(slices)


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
        if remaining <= 1.0:
            break
        to = min(SEARCH_TIMEOUT_S, remaining)
        try:
            # v4: hard per-call wait_for so the internal total-time bound holds even if the host
            # ignores the `timeout` arg — lets the outer turn-loop wrapper stay tight (24s).
            res = await asyncio.wait_for(search_web(query, provider=provider, timeout=to), timeout=to + 1.0)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            res = None
        if res is not None and getattr(res, "results", None):
            break
    if res is None or not getattr(res, "results", None):
        if last_exc is not None:
            return f"# search_web({query!r}) -> ERROR: {last_exc}"
        return f"# search_web({query!r}) -> 0 results"
    nums = ledger.add(res.receipt_id, res.results, window=SEARCH_WINDOW)
    out = [f"# search_web({query!r}) -> {len(nums)} results"]
    for n, r in zip(nums, res.results, strict=False):
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
        if remaining <= 1.0:
            break
        to = min(FETCH_TIMEOUT_S, remaining)
        try:
            # v4: hard per-call wait_for (see _do_search) so the internal bound holds host-agnostically.
            res = await asyncio.wait_for(fetch_page(url, provider=provider, timeout=to), timeout=to + 1.0)
        except Exception as exc:  # noqa: BLE001
            err = exc
            res = None
        if res is not None and getattr(res, "results", None):
            break
    if res is None:
        return f"# fetch_page({url!r}) -> ERROR: {err}"
    # v4: page top is always shown+cited exactly as base; add a deep slice only if a dense deep
    # cluster exists (see _deep_cluster_offset). This captures deep-table answers without ever
    # dropping a top-of-page answer.
    note = getattr(res.results[0], "note", None) or ""
    # v9: surface MULTIPLE deep regions (term-clusters + numeric/table-dense), additive to the top window.
    deeps = _value_regions(note, terms or [], FETCH_WINDOW)
    nums = ledger.add(res.receipt_id, res.results, window=FETCH_WINDOW, deeps=deeps)
    if not nums:
        return f"# fetch_page({url!r}) -> no content"
    top_body = note[:FETCH_WINDOW]
    parts = [top_body]
    for ds, de in deeps:
        parts.append(f"… [continued from char {ds}] …\n{note[ds:de]}")
    body = "\n\n".join(parts)
    tag = f" (+{len(deeps)} deep {sum(de - ds for ds, de in deeps)}c)" if deeps else ""
    return f"# fetch_page({url!r}) -> [{nums[0]}] {len(top_body)}c{tag}\n{body}"


def _cited_numbers(text: str, *, high: int) -> list[int]:
    ordered: list[int] = []
    seen: set[int] = set()
    for m in _BRACKET_RE.finditer(text):
        for part in m.group(1).split(","):
            part = part.strip()
            if not part:
                continue
            rng = re.fullmatch(r"(\d{1,4})\s*-\s*(\d{1,4})", part)
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


def _build_citations(answer: str, ledger: _Ledger) -> list[CitationRef]:
    """v4: TWO-PHASE. Phase 1 selects one top slice [0, top_end] per cited [n] — byte-identical to
    base's selection and char accounting. Phase 2 appends an optional deep slice ONLY from leftover
    budget, so a deep slice can never displace or shrink a citation base would have included.
    Every slice is >=100 chars and end<=note_len (== source_text length; no server truncation)."""
    cited = _cited_numbers(answer, high=ledger.high())
    selected: list[tuple[dict[str, object], int]] = []   # (row, top_end)
    spent = 0
    # Phase 1 — top slices (== base)
    for n in cited:
        if len(selected) >= CITATION_COUNT_CAP:
            break
        row = ledger.row(n)
        if row is None:
            continue
        note_len = int(row.get("note_len", 0))
        if note_len <= 0:
            continue
        top_end = min(int(row.get("top_end") or int(row.get("window", FETCH_WINDOW))), note_len)
        if top_end <= 0:
            continue
        if spent + top_end > EVIDENCE_CHAR_CAP:
            continue
        spent += top_end
        selected.append((row, top_end))
    # Phase 2 — v9: append MULTIPLE deep slices per citation from leftover budget only (pure upside;
    # never displaces a top slice). Respects the <=400-segment and total-char caps.
    deep_for: dict[int, list[tuple[int, int]]] = {}
    segments = len(selected)                                  # each top slice counts as one segment
    for idx, (row, top_end) in enumerate(selected):
        note_len = int(row.get("note_len", 0))
        for d in (row.get("deeps") or []):
            if segments >= 380:
                break
            ds, de = int(d[0]), int(d[1])
            if not (0 <= ds < de <= note_len) or (de - ds) < 100 or ds < top_end:
                continue
            if spent + (de - ds) > EVIDENCE_CHAR_CAP:
                break
            spent += (de - ds)
            segments += 1
            deep_for.setdefault(idx, []).append((ds, de))
    refs: list[CitationRef] = []
    for idx, (row, top_end) in enumerate(selected):
        slices = [CitationSlice(start=0, end=top_end)]
        for ds, de in deep_for.get(idx, []):
            slices.append(CitationSlice(start=ds, end=de))
        refs.append(
            CitationRef(
                receipt_id=str(row["receipt_id"]),
                result_id=str(row["result_id"]),
                slices=slices,
            )
        )
    return refs


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
            if budget <= 1.0:
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
                    timeout=to + 3.0,
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
    for _ in range(2):
        if deadline - perf_counter() <= 1.5:
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

    # Bootstrap: seed grounded evidence in parallel so the store is never empty on turn 1.
    try:
        seeds = _seed_queries(query.text)
        # v2: give each seed enough budget that a fast-failing primary can still fall back to
        # desearch (fast connection error + one fallback attempt fits well inside the wrapper).
        seeded = await asyncio.wait_for(
            asyncio.gather(*(_do_search(s, ledger, time_left=SEARCH_TIMEOUT_S + 6.0) for s in seeds)),
            timeout=SEARCH_TIMEOUT_S + 12.0,
        )
        if ledger.high() > 0:
            messages.append({
                "role": "system",
                "content": "Preliminary automatic searches (already numbered; search more as needed):\n\n"
                + "\n\n".join(seeded),
            })
    except Exception:  # noqa: BLE001
        pass

    final_answer: str | None = None
    nudged = False
    try:
        for turn in range(1, MAX_TURNS + 1):
            remaining = research_deadline - perf_counter()
            if remaining <= 2.0:
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
                if time_left <= 1.0:
                    over_budget = True  # stop tools here so the commit reserve is never eaten
                    break
                try:
                    args = json.loads(tc.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                try:
                    if tc.name == "search_web":
                        q = str(args.get("query", ""))
                        norm = " ".join(q.lower().split())
                        # v4 (b1): skip a genuinely redundant identical search that already returned
                        # results — hand back the prior [n]s instead of burning another round-trip.
                        if norm and norm in seen_searches:
                            content = f"# search_web({q!r}) -> already searched; see {seen_searches[norm]}"
                        else:
                            # v4 (b2): internal per-call wait_for enforces the total bound, so the
                            # outer wrapper can stay tight at 24s (base-like margin, no 44s overshoot).
                            content = await asyncio.wait_for(
                                _do_search(q, ledger, time_left=time_left),
                                timeout=2.0 * SEARCH_TIMEOUT_S + 4.0,
                            )
                            if norm and " results" in content and "-> 0 results" not in content:
                                seen_searches[norm] = f"prior results up to [{ledger.high()}]"
                    elif tc.name == "fetch_page":
                        content = await asyncio.wait_for(
                            _do_fetch(str(args.get("url", "")), ledger, time_left=time_left, terms=query_terms),
                            timeout=FETCH_TIMEOUT_S * FETCH_TRIES + 4.0,
                        )
                    else:
                        content = f"# unsupported tool {tc.name!r}"
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
_TAG="cd7b1eb0163f4e48b84e8e77fbb4cbb9"
import logging as _tag_logging
_tag_logging.getLogger("miner.tag").debug("tag=%s", _TAG)
