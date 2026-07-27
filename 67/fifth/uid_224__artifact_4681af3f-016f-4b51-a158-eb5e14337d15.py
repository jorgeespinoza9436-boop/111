"""SN67 Harnyx miner — lean autonomous deep-research harness (v40-lean-c, line L1).

Design: a single strong reasoning model (GLM-5 over openrouter) drives an autonomous
search/fetch tool loop, then commits one cited FINAL ANSWER. Independently authored;
follows the proven lean-agent pattern but is our own implementation:

  * Ledger-tracked evidence: every tool result gets a stable number [k] whose citation
    is later sliced to exactly the character window the model was shown, so the judge's
    materialized-evidence total stays under its hard cap (invalid-payload = score 0).
  * Parallel enumeration: a search_many tool runs several queries at once, so which/list/
    how-many questions can gather every candidate in one turn and be filtered completely
    within budget (the multi-constraint aggregation weakness of a one-search-at-a-time loop).
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
LLM_PROVIDER = "openrouter"
SEARCH_PROVIDER = "parallel"
PRIMARY_MODEL = "z-ai/glm-5"

# ---- Budget / turn governor -------------------------------------------------------------
COMMIT_RESERVE_S = 45.0         # tail reserved purely for the forced final commit
TOTAL_BUDGET_S = 285.0          # validator kills at 300s; keep a tail for the guaranteed commit
COMMIT_LOOKAHEAD_TURNS = 2
LLM_TRY_PER_TURN = 2
LLM_TURN_TIMEOUT_S = 68.0
MAX_TURNS = 16
SEARCH_TIMEOUT_S = 20.0
FETCH_TRIES = 2
FETCH_TIMEOUT_S = 15.0
MAX_BATCH_QUERIES = 8    # parallel searches per search_many call (enumerate/filter coverage)

# ---- Evidence / citation-safety bounds --------------------------------------------------
SEARCH_WINDOW = 700             # chars of a search note surfaced to the model = slice width
FETCH_WINDOW = 6000             # chars of a fetched page surfaced to the model = slice width
CITATION_COUNT_CAP = 20
DIGEST_CHAR_CAP = 90_000        # size of the clean evidence digest fed to the forced commit
EVIDENCE_CHAR_CAP = 112_000     # sum of materialized slice widths kept under the ~120k wall

SYSTEM_PROMPT = (
    "You are a meticulous research analyst. The user asks a factual question that is often "
    "multi-part or requires filtering a set of entities by several conditions. You have three tools: "
    "search_web (one query), search_many (several queries at once, in parallel), and fetch_page; "
    "every tool result is labelled with a number like [4].\n\n"
    "METHOD:\n"
    "1. Decompose the question into every distinct sub-fact and every filtering condition. Never "
    "recall a date, age, count, rank, population, price, chart position or proper name from memory — "
    "search for it and read the result.\n"
    "2. ENUMERATE, THEN FILTER. When the question asks which members of a set satisfy conditions, "
    "FIRST establish the complete candidate pool from an authoritative list (do not work from the "
    "2-3 famous examples you can recall), THEN evaluate every candidate against every condition. "
    "Once you have the pool, use search_many with one query per candidate (e.g. '<candidate> <metric>') "
    "to gather the deciding value for all of them in a single step. Silently omitting a qualifying "
    "member is the most common way to lose.\n"
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
    "final answer in the same turn as a tool call."
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
            "name": "search_many",
            "description": (
                "Run several web searches at once (in parallel) and get all numbered results back "
                "together. Use this to enumerate or verify a whole set of candidates in one step — "
                "e.g. one query per candidate — so a which/list/how-many question is covered fully "
                "within the time budget instead of one slow search at a time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "up to 8 search queries to run together",
                    }
                },
                "required": ["queries"],
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

    def add(self, receipt_id: str, results: object, *, window: int) -> list[int]:
        assigned: list[int] = []
        for r in results or ():
            rid = getattr(r, "result_id", None)
            if not rid:
                continue
            self._n += 1
            note = getattr(r, "note", None) or ""
            self._rows[self._n] = {
                "receipt_id": receipt_id,
                "result_id": rid,
                "window": window,
                "note_len": len(note),
                "text": note[:window],
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


async def _do_search(query: str, ledger: _Ledger, *, time_left: float = SEARCH_TIMEOUT_S) -> str:
    if not query:
        return "# search_web() -> ERROR: empty query"
    timeout = min(SEARCH_TIMEOUT_S, max(1.0, time_left))
    try:
        res = await search_web(query, provider=SEARCH_PROVIDER, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return f"# search_web({query!r}) -> ERROR: {exc}"
    nums = ledger.add(res.receipt_id, res.results, window=SEARCH_WINDOW)
    out = [f"# search_web({query!r}) -> {len(nums)} results"]
    for n, r in zip(nums, res.results, strict=False):
        excerpt = (getattr(r, "note", None) or "")[:SEARCH_WINDOW]
        out.append(f"[{n}] {getattr(r, 'title', '') or ''}\n  url: {getattr(r, 'url', '') or ''}\n  {excerpt}")
    return "\n".join(out)


async def _do_search_many(queries: list[str], ledger: _Ledger, *, time_left: float = SEARCH_TIMEOUT_S) -> str:
    """Run several searches in parallel so an enumerate/filter question can gather every candidate
    in a single turn instead of one slow search at a time. Each sub-result keeps its own [n]."""
    clean = [str(q).strip() for q in (queries or []) if str(q).strip()][:MAX_BATCH_QUERIES]
    if not clean:
        return "# search_many() -> ERROR: no queries"
    parts = await asyncio.gather(*(_do_search(q, ledger, time_left=time_left) for q in clean))
    return f"# search_many({len(clean)} queries)\n" + "\n\n".join(parts)


async def _do_fetch(url: str, ledger: _Ledger, *, time_left: float = FETCH_TIMEOUT_S) -> str:
    if not url:
        return "# fetch_page() -> ERROR: empty url"
    timeout = min(FETCH_TIMEOUT_S, max(1.0, time_left))
    res = None
    err: Exception | None = None
    for _ in range(FETCH_TRIES):
        try:
            res = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=timeout)
            break
        except Exception as exc:  # noqa: BLE001
            err = exc
    if res is None:
        return f"# fetch_page({url!r}) -> ERROR: {err}"
    nums = ledger.add(res.receipt_id, res.results, window=FETCH_WINDOW)
    if not nums:
        return f"# fetch_page({url!r}) -> no content"
    body = (getattr(res.results[0], "note", None) or "")[:FETCH_WINDOW]
    return f"# fetch_page({url!r}) -> [{nums[0]}] {len(body)} chars\n{body}"


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
                    ordered.append(n)
                    seen.add(n)
    return ordered


def _build_citations(answer: str, ledger: _Ledger) -> list[CitationRef]:
    """One CitationRef per inline [n], sliced to the exact shown window, count- and char-capped
    so the judge's materialized-evidence total stays under EVIDENCE_CHAR_CAP."""
    refs: list[CitationRef] = []
    spent = 0
    for n in _cited_numbers(answer, high=ledger.high()):
        if len(refs) >= CITATION_COUNT_CAP:
            break
        row = ledger.row(n)
        if row is None:
            continue
        note_len = int(row.get("note_len", 0))
        if note_len <= 0:
            continue
        end = min(int(row.get("window", FETCH_WINDOW)), note_len)
        if end <= 0:
            continue
        if spent + end > EVIDENCE_CHAR_CAP:
            continue
        spent += end
        refs.append(
            CitationRef(
                receipt_id=str(row["receipt_id"]),
                result_id=str(row["result_id"]),
                slices=[CitationSlice(start=0, end=end)],
            )
        )
    return refs


async def _chat(messages: list[dict[str, object]], *, deadline: float, final: bool):
    thinking = (
        LlmThinkingConfig(enabled=False)
        if final
        else LlmThinkingConfig(enabled=True, effort="low")
    )
    for _ in range(LLM_TRY_PER_TURN):
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
                    model=PRIMARY_MODEL,
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
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query.text},
    ]

    # Bootstrap: seed grounded evidence in parallel so the store is never empty on turn 1.
    try:
        seeds = _seed_queries(query.text)
        seeded = await asyncio.wait_for(
            asyncio.gather(*(_do_search(s, ledger) for s in seeds)),
            timeout=SEARCH_TIMEOUT_S + 6.0,
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
                        content = await asyncio.wait_for(
                            _do_search(str(args.get("query", "")), ledger, time_left=time_left),
                            timeout=SEARCH_TIMEOUT_S + 4.0,
                        )
                    elif tc.name == "search_many":
                        qs = args.get("queries") or []
                        content = await asyncio.wait_for(
                            _do_search_many(qs if isinstance(qs, list) else [qs], ledger, time_left=time_left),
                            timeout=SEARCH_TIMEOUT_S + 8.0,
                        )
                    elif tc.name == "fetch_page":
                        content = await asyncio.wait_for(
                            _do_fetch(str(args.get("url", "")), ledger, time_left=time_left),
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
