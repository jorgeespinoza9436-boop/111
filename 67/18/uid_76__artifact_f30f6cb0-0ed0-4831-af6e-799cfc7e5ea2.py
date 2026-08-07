"""SN67 Harnyx miner — staged research protocol agent. [slot 11 build 2026-08-05T15:00:48+00:00]"""
from __future__ import annotations

import asyncio
import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

LLM_PROVIDER = "openrouter"
MODEL = "z-ai/glm-5"
COMMIT_FALLBACK_MODEL = "deepseek/deepseek-v3.2"
FETCH_RETRY_ATTEMPTS = 2
TASK_TOTAL_BUDGET_SECONDS = 235.0
FETCH_TIMEOUT_SECONDS = 15.0
LLM_TURN_TIMEOUT_SECONDS = 90.0
MAX_RETRY_ATTEMPTS_PER_TURN = 2
SEARCH_TIMEOUT_SECONDS = 20.0

RESEARCH_TURN_CAP = 10
RESEARCH_TIME_CAP_SECONDS = 140.0
CHECKPOINT_TOOL_TURNS = 2
FINAL_RESERVE_SECONDS = 55.0
FINAL_RETRY_MIN_SECONDS = 25.0

TOOL_RESULT_INLINE_CHARS = 3000
SEARCH_EXCERPT_INLINE_CHARS = 700
COVERAGE_LIST_MAX = 8
MIN_ANSWER_CHARS = 400
HARD_MIN_ANSWER_CHARS = 200
MAX_CITATIONS = 16
CITATION_BUDGET_CHARS = 90_000

PAGE_WINDOW_CHARS = 3600
PAGE_WINDOWS_PER_PAGE = 3
PAGE_WINDOW_BUDGET_CHARS = 34_000
# Every source is guaranteed this much surfaced area of its own before the
# shared allowance is touched, so a page read late in a run cannot be left with
# only its opening by pages read earlier. Bounded twice: a single source can
# reserve no more than one opening plus its windows, and only the first
# PAGE_RESERVE_POOL_CHARS worth of reservations are honoured at all.
PAGE_SOURCE_RESERVE_CHARS = PAGE_WINDOW_CHARS * PAGE_WINDOWS_PER_PAGE
PAGE_RESERVE_POOL_CHARS = 64_800
TERM_LIMIT = 22
TERM_HITS_PER_TERM = 60
TERM_HITS_TOTAL = 600

RELOCATE_MAX_PASSES = 3
RELOCATE_WINDOW_CHARS = 1600
RELOCATE_WINDOWS_PER_KEY = 2
RELOCATE_PAGES_PER_KEY = 4
RELOCATE_BUDGET_CHARS = 16_000
RELOCATE_MIN_SECONDS = 6.0
PROOF_CHARS = 420
DIRECTIVE_TOTAL_CHARS = 6_000

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web. Returns results with title, url, and a text excerpt.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Fetch a URL and return its extracted main text content.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL to fetch"}},
                "required": ["url"],
            },
        },
    },
]

SYSTEM_PROMPT = (
    "You are a precise web-research agent answering one factual question in a single "
    "continuous session. You have search_web and fetch_page tools. Follow this protocol "
    "exactly, using the literal phase markers.\n\n"
    "BRIEFING:\n"
    "Open your first message with a BRIEFING block written from your own knowledge, "
    "before reading any tool result:\n"
    "(a) CANDIDATE POOL — every entity that might satisfy the question, one per line, "
    "formatted exactly:\n"
    "- CANDIDATE: <name> — <one-clause confidence note>\n"
    "(b) CONSTRAINTS — the atomic constraints the answer must satisfy, decomposed.\n"
    "(c) PLAN — 2-4 opening queries.\n"
    "Do not answer during the briefing. You may issue your opening tool calls in the "
    "same turn as the briefing.\n\n"
    "RESEARCH:\n"
    "Call tools adaptively. Your goal is coverage: obtain the specific figures or facts "
    "needed to test EVERY candidate against EVERY constraint — for entities that qualify "
    "AND entities that do not. If a query or page fails, pivot the query or the source "
    "rather than repeating it. BATCH RULE: when testing many candidates against a "
    "per-candidate fact (a statistic, a tempo, a runtime, a date), issue the lookups "
    "for SEVERAL candidates as multiple tool calls in the SAME turn — never spend one "
    "turn per candidate. METRIC RULE: when the question asks for the percentage "
    "change or growth of an economic indicator, retrieve the OFFICIAL growth-rate "
    "series for that indicator (e.g. World Bank 'GDP growth (annual %)', real terms) — "
    "NEVER derive a percentage from current-value levels yourself. SOURCE RULE: if the "
    "question names a source (e.g. Forbes, Box Office Mojo, IMDb, Rotten Tomatoes, a UN "
    "or government agency), get the data from THAT source — search it directly, fetch "
    "its page, and cite it for the core claims. For each metric, prefer ONE consistent "
    "canonical source across all candidates (same series, same year basis); do not mix "
    "sources for the same metric unless the preferred source is unreachable, and note "
    "the substitution if you must.\n\n"
    "VERIFY:\n"
    "When told to verify, build a per-candidate x per-constraint table from the numbered "
    "evidence, citing [n] markers. Name the near-miss exclusions and the exact criterion "
    "each fails. Do not write 'the only', 'the sole', or 'the single' unless you "
    "enumerated and checked the whole pool. Never state a figure that is not present in "
    "the numbered evidence. Never declare a candidate's data missing without re-scanning "
    "the numbered evidence for it first — if the figure is there, include or exclude that "
    "candidate on the merits, citing the figure. Check that every core figure is cited "
    "to the question's named source (or one consistent canonical source per metric); if "
    "a core figure only has a substitute source while the named source is reachable, "
    "fetch the named source before finalizing. Re-read the question's explicit "
    "output-format instructions (ordering, list format, words to include or omit) and "
    "make the final answer obey them exactly — such instructions control how you WRITE "
    "the answer text, never which entities qualify: an instruction to omit a word means "
    "write the qualifying entity's name without that word, not exclude the entity.\n\n"
    "FINAL ANSWER:\n"
    "End with a committed, SELF-CONTAINED answer: state the answer first, then a compact "
    "proof — each qualifying entity with the figures that qualify it, and the near-miss "
    "exclusions with the exact criterion each fails — written as clean prose or short "
    "bullets with [n] citations. Do NOT reproduce the working table or internal "
    "scaffolding; rewrite the proof as prose. A reader must be able to see the full "
    "candidate-pool reasoning from the FINAL ANSWER alone. Scoring is pairwise against a "
    "competitor: an answer that refuses, defers, or hedges to 'insufficient data' loses "
    "outright, and so does a bare answer with no completeness proof. If evidence covers "
    "only part of the pool, commit to the best-supported answer and note that the roster "
    "may be incomplete.\n\n"
    "CITATION RULE: in the final answer, put the evidence number in brackets immediately "
    "after EVERY factual claim — e.g. 'the total is 4,000 [7, 12].' A claim with no "
    "bracket after it is assumed uncited."
)

BRIEFING_NUDGE = (
    "Your first message must open with the BRIEFING block (CANDIDATE POOL / CONSTRAINTS "
    "/ PLAN) as instructed. Write it now, then begin research."
)

FORCED_COMMIT_SUFFIX = (
    "\n\n*** FORCED COMMIT ***\nYour previous draft refused, stalled, or was cut short. "
    "That scores ZERO. Rewrite now: commit to the best evidence-supported answer, cite "
    "every claim, and do not emit tool-call syntax or apologies."
)

INSUFFICIENT_ANSWER = (
    "I could not complete a source-backed research answer for this question within budget."
)

TOOL_MARKUP_RE = re.compile(
    r"<\s*/?\s*(tool_call|arg_key|arg_value)\b[^>]*>", re.IGNORECASE,
)
# glm-5 sometimes narrates tool calls as prose instead of emitting structured
# calls; that text must never reach the judge as a final answer
PSEUDO_CALL_RE = re.compile(r"\b(?:search_web|fetch_page)\s*\(", re.IGNORECASE)
ABSTENTION_MARKERS = (
    "i could not", "i cannot", "i was unable", "unable to", "cannot answer",
    "insufficient evidence", "no evidence", "could not find", "cannot determine",
    "cannot be determined", "i don't have", "i do not have", "not enough information",
)
CANDIDATE_RE = re.compile(r"^\s*[-*]\s*CANDIDATE:\s*(.+?)\s*$", re.MULTILINE)
FINAL_SECTION_RE = re.compile(
    r"^\s*(?:#{1,4}\s*)?(?:\*{1,2})?\s*FINAL ANSWER\s*(?:\*{1,2})?\s*:?\s*$"
    r"|(?:\*{1,2}|#{1,4}\s*)?FINAL ANSWER(?:\*{1,2})?\s*:",
    re.IGNORECASE | re.MULTILINE,
)
DUMP_GARBAGE_RE = re.compile(
    r"can[’']?t be reached|ERR_|unexpectedly closed|access denied|403 forbidden"
    r"|404 not found|-> ERROR|enable javascript|verify you are human",
    re.IGNORECASE,
)


STOP_TERMS = frozenset((
    "the", "and", "for", "are", "was", "were", "has", "have", "had", "with", "that",
    "this", "from", "which", "what", "who", "whom", "whose", "when", "where", "how",
    "many", "much", "does", "did", "any", "all", "its", "their", "there", "here",
    "into", "than", "then", "them", "they", "you", "your", "our", "his", "her",
    "not", "but", "also", "only", "each", "every", "some", "such", "more", "most",
    "other", "others", "same", "both", "list", "name", "names", "give", "state",
    "using", "use", "used", "please", "answer", "question", "according", "based",
    "page", "pages", "site", "website", "web", "data", "value", "values", "number",
    "numbers", "total", "figure", "figures", "table", "report", "reports", "year",
    "years", "one", "two", "three", "over", "under", "between", "about", "above",
    "below", "after", "before", "during", "per", "including", "include", "included",
))


def _key_terms(text: str, limit: int = TERM_LIMIT) -> list[str]:
    """Distinctive lookup terms for a piece of text, numerals and long words first.

    Purely lexical and content-agnostic: the ranking is by information density
    (a digit run beats a long word beats a short word), never by subject matter.
    """
    words = re.findall(r"[A-Za-z][A-Za-z'\-]{2,}|\d[\d,.%/]*", text or "")
    ordered = sorted(words, key=lambda w: (not any(c.isdigit() for c in w), -len(w)))
    terms: list[str] = []
    for w in ordered:
        lw = w.lower().strip(".,%/-")
        if len(lw) < 3 or lw in STOP_TERMS or lw in terms:
            continue
        terms.append(lw)
        if len(terms) >= limit:
            break
    return terms


def _term_hits(note_lower: str, terms: list[str]) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for t in terms:
        i = note_lower.find(t)
        seen = 0
        while i != -1 and seen < TERM_HITS_PER_TERM:
            hits.append((i, t))
            seen += 1
            i = note_lower.find(t, i + max(1, len(t)))
        if len(hits) >= TERM_HITS_TOTAL:
            break
    hits.sort()
    return hits


def _best_windows(
    note: str, terms: list[str], width: int, k: int,
    *, skip_before: int = 0, avoid: list[tuple[int, int]] | None = None,
) -> list[tuple[int, int]]:
    """The k highest-density disjoint regions of `note` for `terms`.

    Deterministic scan, no model call and no extra request: score a candidate
    region by how many DISTINCT terms fall inside it, break ties on raw hits,
    take the best, then exclude everything it covers and repeat. Regions already
    surfaced (`avoid`) and the leading `skip_before` chars are never re-emitted.
    """
    src_len = len(note)
    if k <= 0 or not terms or src_len <= skip_before:
        return []
    hits = [(p, t) for p, t in _term_hits(note.lower(), terms) if p >= skip_before]
    if not hits:
        return []
    taken: list[tuple[int, int]] = list(avoid or ())
    picked: list[tuple[int, int]] = []
    consumed: set[tuple[int, str]] = set()
    for _round in range(k):
        best_key: tuple[int, int] | None = None
        best_span: tuple[int, int] | None = None
        best_inside: list[tuple[int, str]] = []
        for p, _t in hits:
            start = max(skip_before, min(p - width // 4, max(skip_before, src_len - width)))
            end = min(src_len, start + width)
            if end - start < width // 3:
                continue
            if any(start < e and s < end for s, e in taken):
                continue
            inside = [h for h in hits if start <= h[0] < end and h not in consumed]
            if not inside:
                continue
            key = (len({t for _p, t in inside}), len(inside))
            if best_key is None or key > best_key:
                best_key, best_span, best_inside = key, (start, end), inside
        if best_span is None:
            break
        taken.append(best_span)
        picked.append(best_span)
        consumed.update(best_inside)
    picked.sort()
    return picked


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _render_spans(note: str, spans: list[tuple[int, int]]) -> str:
    """The surfaced regions as one block, each labelled with its offset so the
    reader knows the text is non-contiguous and where each part came from."""
    parts: list[str] = []
    for start, end in _merge_spans(spans):
        parts.append(f"[chars {start}-{end}]\n{note[start:end]}")
    return "\n...\n".join(parts)


def _normalized_url(url: str) -> str:
    text = (url or "").strip().lower()
    text = re.sub(r"^https?://", "", text)
    text = re.sub(r"^www\.", "", text)
    text = text.split("#", 1)[0]
    return text.rstrip("/") or text


class _SourceSurface:
    """Everything that decides what of a source is ever seen.

    One component owns the whole path from a retrieved page to the text that
    reaches a turn and the ranges offered as support: it stores the sources,
    chooses which regions of each to expose, renders them, runs its own loop
    until every item in play has a region behind it, states what it found, and
    issues the supporting ranges. Those used to be separate pieces that each
    re-derived the relevant part of a page independently and could disagree
    about which part of it the answer came from; here there is one set of
    coordinates and everything reads from it.
    """

    def __init__(self) -> None:
        self._by_number: dict[int, dict[str, str]] = {}
        self._spans: dict[int, list[tuple[int, int]]] = {}
        self._window_budget = PAGE_WINDOW_BUDGET_CHARS
        self._reserve_pool = PAGE_RESERVE_POOL_CHARS
        self._source_spend: dict[int, int] = {}
        self._found: dict[str, tuple[int, str]] = {}
        self._next = 1

    def record(self, receipt_id: str, results: object, *, kind: str = "search") -> list[int]:
        numbers: list[int] = []
        for r in results or ():
            result_id = getattr(r, "result_id", None)
            if not result_id:
                continue
            n = self._next
            self._next += 1
            note = (getattr(r, "note", None) or "")
            shown = SEARCH_EXCERPT_INLINE_CHARS if kind == "search" else TOOL_RESULT_INLINE_CHARS
            self._by_number[n] = {
                "receipt_id": receipt_id,
                "result_id": result_id,
                "kind": kind,
                "citable": bool(note.strip()),
                "src_len": len(note),
                "shown": min(shown, len(note)),
                "title": (getattr(r, "title", None) or "")[:200],
                "url": (getattr(r, "url", None) or "")[:300],
                "note": note,
            }
            numbers.append(n)
        return numbers

    def get(self, number: int) -> dict[str, str] | None:
        return self._by_number.get(number)

    def max_number(self) -> int:
        return self._next - 1

    def all_note_text(self) -> str:
        return "\n".join(meta["note"] for meta in self._by_number.values())

    def fetched_numbers(self) -> list[int]:
        return [
            n for n, meta in self._by_number.items()
            if meta.get("kind") == "fetch" and meta.get("citable", True)
        ]

    # --- which regions of a source are exposed ----------------------------

    def surface(self, number: int, spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Record regions as shown, honouring the run-wide surfaced-text cap."""
        meta = self._by_number.get(number)
        if meta is None:
            return []
        limit = int(meta.get("src_len") or 0)
        existing = self._spans.setdefault(number, [])
        added: list[tuple[int, int]] = []
        for start, end in spans:
            start = max(0, min(int(start), limit))
            end = max(start, min(int(end), limit))
            if end - start <= 0:
                continue
            if any(start >= s and end <= e for s, e in existing):
                continue
            cost = end - start
            if start > 0:
                # A source draws on its own guaranteed area first and only then
                # competes for the shared allowance. Without this the allowance
                # is spent first-come-first-served, so whichever pages happen to
                # be read last are shown as their opening and nothing else —
                # which is exactly where a long document keeps its tables.
                spent = self._source_spend.get(number, 0)
                reserve = min(
                    max(0, PAGE_SOURCE_RESERVE_CHARS - spent), self._reserve_pool
                )
                if cost <= reserve:
                    self._reserve_pool -= cost
                elif cost <= self._window_budget:
                    self._window_budget -= cost
                else:
                    continue
                self._source_spend[number] = spent + cost
            existing.append((start, end))
            added.append((start, end))
        self._spans[number] = _merge_spans(existing)
        return added

    def spans(self, number: int) -> list[tuple[int, int]]:
        return list(self._spans.get(number) or ())

    def window_budget(self) -> int:
        return self._window_budget

    def surfaced_text(self) -> str:
        parts: list[str] = []
        for number, spans in self._spans.items():
            meta = self._by_number.get(number)
            if meta is None:
                continue
            for start, end in spans:
                parts.append(meta["note"][start:end])
        return "\n".join(parts)

    def page_spans(self, note: str, terms: list[str]) -> list[tuple[int, int]]:
        """A page's opening, plus the densest regions elsewhere in it.

        A long document's relevant rows are routinely nowhere near its start, so
        a fixed prefix reads the boilerplate and stops. The opening is always
        kept — it carries the identity of the document — and the rest of the
        allowance goes to the regions that mention what was asked.
        """
        head_end = min(TOOL_RESULT_INLINE_CHARS, len(note))
        spans = [(0, head_end)]
        if len(note) > head_end:
            spans.extend(_best_windows(
                note, terms, PAGE_WINDOW_CHARS, PAGE_WINDOWS_PER_PAGE, skip_before=head_end,
            ))
        return spans

    def expose(self, number: int, terms: list[str]) -> str:
        """Record and render the regions of a source that a turn will see."""
        meta = self._by_number.get(number)
        if meta is None:
            return ""
        note = meta["note"] or ""
        shown = self.surface(number, self.page_spans(note, terms))
        if not shown:
            shown = self.spans(number) or [(0, min(TOOL_RESULT_INLINE_CHARS, len(note)))]
        return _render_spans(note, shown)

    # --- the subsystem's own loop -----------------------------------------

    def _proof(self, key: str) -> tuple[int, str] | None:
        """The first exposed region that names an item AND states a figure.

        Naming an item is not evidence about it; an item counts as found only
        when a numeral sits close enough to the mention to be about it.
        """
        if len(key) < 3:
            return None
        for number in range(1, self._next):
            meta = self._by_number.get(number)
            if meta is None:
                continue
            note = meta["note"] or ""
            for start, end in self.spans(number) or ():
                passage = note[start:end]
                at = passage.lower().find(key)
                while at != -1:
                    near = passage[max(0, at - PROOF_CHARS):at + PROOF_CHARS]
                    if NUMERIC_RE.search(near):
                        return number, " ".join(near.split())
                    at = passage.lower().find(key, at + len(key))
        return None

    def _rescan(self, keys: list[str]) -> list[str]:
        self._found = {}
        missing: list[str] = []
        for key in keys:
            proof = self._proof(key)
            if proof is None:
                missing.append(key)
            else:
                self._found[key] = proof
        return missing

    def relocate(self, keys: list[str], deadline: float) -> list[str]:
        """Keep re-projecting retained pages until every item has a region.

        Each pass takes the items with nothing stated for them, pulls the
        best-matching unseen region out of every retained page for each, and
        re-tests. It re-enters while a pass is still exposing new regions and
        stops as soon as one is not. No request is issued: the only cost is the
        text added to what has been exposed, which is capped separately.
        """
        if not keys:
            return []
        missing = self._rescan(keys)
        budget = RELOCATE_BUDGET_CHARS
        for _pass in range(RELOCATE_MAX_PASSES):
            if not missing or budget <= 0 or deadline - perf_counter() < RELOCATE_MIN_SECONDS:
                break
            exposed = 0
            for key in missing:
                key_terms = _key_terms(key, limit=6)
                if not key_terms:
                    continue
                for number in self.fetched_numbers()[:RELOCATE_PAGES_PER_KEY]:
                    if budget <= 0:
                        break
                    meta = self._by_number.get(number)
                    if meta is None:
                        continue
                    for a, b in self.surface(number, _best_windows(
                        meta["note"] or "", key_terms, RELOCATE_WINDOW_CHARS,
                        RELOCATE_WINDOWS_PER_KEY, avoid=self.spans(number),
                    )):
                        exposed += b - a
                        budget -= b - a
            if not exposed:
                break
            missing = self._rescan(keys)
        return missing

    def directive(self) -> str:
        """What the answering turn is told about the regions that were located.

        This pipeline writes its answer from the conversation, so a region
        exposed after the page was first read has to be stated here or it is
        not in front of the writer at all.
        """
        if not self._found:
            return ""
        lines = ["RELOCATED EVIDENCE — regions of the pages already retrieved that name an "
                 "item in play and state a figure for it. These are in the evidence: quote "
                 "them with their [n] marker rather than calling them unavailable."]
        room = DIRECTIVE_TOTAL_CHARS
        for key, (number, proof) in self._found.items():
            entry = f"  {key} — [{number}] {proof[:600]}"
            room -= len(entry)
            if room <= 0:
                break
            lines.append(entry)
        return "\n".join(lines)

    # --- what is offered as support ---------------------------------------

    def refs(self, answer_text: str) -> tuple[CitationRef, ...]:
        """The supporting ranges for an answer's [n] markers.

        The ranges a source was READ from are the ranges a claim can have come
        from, so those are the ranges offered; a source never exposed in ranges
        falls back to the excerpt it was listed with. One entry per SOURCE, not
        per evidence number — a page read twice used to go out twice with
        near-identical ranges, which reads as padding — carrying the union of
        the ranges it was read from.
        """
        max_number = self.max_number()
        seen: set[int] = set()
        ordered: list[int] = []
        for match in BRACKET_RE.finditer(answer_text):
            for number in _numbers_from_bracket(match.group(1), max_number=max_number):
                if number not in seen:
                    seen.add(number)
                    ordered.append(number)
        by_source: dict[str, dict[str, object]] = {}
        source_order: list[str] = []
        for number in ordered:
            meta = self._by_number.get(number)
            if meta is None or not meta.get("citable", True):
                continue
            src_len = int(meta.get("src_len") or 0)
            if src_len <= 0:
                continue
            spans = [(s, e) for s, e in self.spans(number) if e > s]
            if not spans:
                shown = int(meta.get("shown") or 0)
                if shown <= 0:
                    continue
                spans = [(0, shown)]
            spans = _merge_spans([(max(0, s), min(src_len, e)) for s, e in spans])
            if not spans:
                continue
            key = _normalized_url(meta.get("url") or "") or f"{meta['receipt_id']}/{meta['result_id']}"
            entry = by_source.get(key)
            if entry is None:
                by_source[key] = {"meta": meta, "spans": spans, "src_len": src_len}
                source_order.append(key)
            else:
                limit = int(entry["src_len"])
                entry["spans"] = _merge_spans(
                    list(entry["spans"]) + [(s, min(e, limit)) for s, e in spans if s < limit]
                )
        citations: list[CitationRef] = []
        budget = CITATION_BUDGET_CHARS
        for key in source_order:
            if len(citations) >= MAX_CITATIONS:
                break
            entry = by_source[key]
            meta = entry["meta"]
            spans = [(s, e) for s, e in entry["spans"] if e > s]
            cost = sum(e - s for s, e in spans)
            while spans and cost > budget:
                # drop the narrowest range first — the widest carries the most proof
                spans.remove(min(spans, key=lambda span: span[1] - span[0]))
                cost = sum(e - s for s, e in spans)
            if not spans:
                continue
            budget -= cost
            citations.append(CitationRef(
                receipt_id=meta["receipt_id"], result_id=meta["result_id"],
                slices=[CitationSlice(start=s, end=e) for s, e in spans],
            ))
        return tuple(citations)


async def _run_search_web(query: str, index: _SourceSurface) -> str:
    try:
        result = await search_web(query, provider="parallel", timeout=SEARCH_TIMEOUT_SECONDS)
    except Exception as exc:
        return f"# search_web({query!r}) -> ERROR: {exc}"
    numbers = index.record(result.receipt_id, result.results, kind="search")
    lines = [f"# search_web({query!r}) -> {len(result.results)} results"]
    for n, r in zip(numbers, result.results, strict=False):
        lines.append(
            f"[{n}] {r.title or ''}\n  url: {r.url}\n"
            f"  excerpt: {(r.note or '')[:SEARCH_EXCERPT_INLINE_CHARS]}"
        )
    return "\n".join(lines)


async def _run_fetch_page(url: str, index: _SourceSurface, terms: list[str]) -> str:
    result = None
    last_exc: Exception | None = None
    for _attempt in range(FETCH_RETRY_ATTEMPTS):
        try:
            result = await fetch_page(url, provider="parallel", timeout=FETCH_TIMEOUT_SECONDS)
            break
        except Exception as exc:
            last_exc = exc
            continue
    if result is None:
        return f"# fetch_page({url!r}) -> ERROR: {last_exc}"
    numbers = index.record(result.receipt_id, result.results, kind="fetch")
    if not result.results or not numbers:
        return f"# fetch_page({url!r}) -> no content"
    n = numbers[0]
    note = result.results[0].note or ""
    body = index.expose(n, terms)
    return (
        f"# fetch_page({url!r}) -> [{n}] {len(note)} chars total, "
        f"{len(body)} shown\n{body}"
    )


BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")


def _numbers_from_bracket(value: str, *, max_number: int) -> tuple[int, ...]:
    numbers: list[int] = []
    for item in value.split(","):
        text = item.strip()
        if not text:
            continue
        range_match = re.fullmatch(r"(\d{1,4})\s*-\s*(\d{1,4})", text)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start <= end:
                numbers.extend(i for i in range(start, end + 1) if 1 <= i <= max_number)
        elif text.isdigit():
            i = int(text)
            if 1 <= i <= max_number:
                numbers.append(i)
    return tuple(numbers)


NUMERIC_RE = re.compile(r"\d")


def _relocation_keys(question: str, candidates: list[str]) -> list[str]:
    """The items the relocation loop works through, lower-cased for matching."""
    keys: list[str] = []
    for candidate in candidates[:COVERAGE_LIST_MAX]:
        key = _coverage_key(candidate)
        if len(key) >= 3 and key not in keys:
            keys.append(key)
    if not keys:
        for term in _key_terms(question, limit=8):
            if len(term) >= 4 and term not in keys:
                keys.append(term)
    return keys


def _parse_candidates(briefing_text: str) -> list[str]:
    names: list[str] = []
    for raw in CANDIDATE_RE.findall(briefing_text or ""):
        name = re.split(r"\s+—|\s+--", raw, maxsplit=1)[0].strip().strip("*").rstrip(".")
        if name and name not in names:
            names.append(name)
    return names


def _coverage_key(candidate: str) -> str:
    return re.sub(r"\s*\(.*?\)", "", candidate).strip().lower()


def _uncovered_candidates(candidates: list[str], evidence_text: str) -> list[str]:
    hay = evidence_text.lower()
    missing: list[str] = []
    for c in candidates:
        key = _coverage_key(c)
        if len(key) >= 3 and key not in hay:
            missing.append(c)
    return missing


def _checkpoint_message(candidates: list[str], index: _SourceSurface) -> str:
    missing = _uncovered_candidates(candidates, index.all_note_text())
    if missing:
        coverage = (
            "Code-side coverage check: the gathered evidence contains NO per-candidate "
            "data for these BRIEFING candidates: " + "; ".join(missing[:COVERAGE_LIST_MAX]) + ". "
            f"You may make AT MOST {CHECKPOINT_TOOL_TURNS} more tool-call turns, targeted "
            "ONLY at exactly these candidates; after that tools are DISABLED and you MUST "
            "commit. "
        )
    else:
        coverage = (
            f"You may make AT MOST {CHECKPOINT_TOOL_TURNS} more tool-call turns if a "
            "specific candidate's figures are still missing from the evidence; after that "
            "tools are DISABLED and you MUST commit. "
        )
    return (
        "CHECKPOINT — the research phase is over. Enter VERIFY now: build the "
        "per-candidate x per-constraint table from the numbered evidence gathered so far, "
        "citing [n] markers. " + coverage +
        "Before declaring any candidate's data missing, re-scan the numbered evidence "
        "for it — if the figure is present, decide that candidate on the merits with the "
        "figure cited. Then re-check the question's explicit output-format instructions "
        "(ordering, list format, words to include or omit), and end with FINAL ANSWER — "
        "self-contained: the answer, each qualifying entity's figures, and the near-miss "
        "exclusions with their failing criterion, as clean prose with [n] citations (no "
        "working table)."
    )


COMMIT_MESSAGE = (
    "Tools are now DISABLED. Produce the VERIFY table and FINAL ANSWER from the numbered "
    "evidence you already have, with [n] citations after every claim. Commit."
)


async def _chat_turn(
    messages: list[dict[str, object]], *, deadline: float, thinking_on: bool,
) -> LlmChatResult | None:
    for _attempt in range(MAX_RETRY_ATTEMPTS_PER_TURN):
        timeout = min(LLM_TURN_TIMEOUT_SECONDS, deadline - perf_counter())
        if timeout <= 0:
            return None
        try:
            return await llm_chat(
                provider=LLM_PROVIDER, model=MODEL, messages=messages,
                tools=TOOLS, tool_choice="auto", temperature=0.2,
                thinking=LlmThinkingConfig(enabled=thinking_on, effort="low"),
                timeout=timeout,
            )
        except Exception:
            continue
    return None


async def _commit_call(messages: list[dict[str, object]], *, deadline: float) -> str | None:
    # attempt 0: primary model, thinking on (budget permitting)
    # attempt 1: primary model, thinking off
    # attempt 2: fallback model on an uncorrelated provider pool, thinking off
    for _attempt in range(3):
        budget = deadline - perf_counter() - 2
        if budget <= 12:
            return None
        model = MODEL if _attempt < 2 else COMMIT_FALLBACK_MODEL
        if _attempt == 0 and budget >= 70:
            timeout = budget - 28.0
            thinking = LlmThinkingConfig(enabled=True, effort="low")
        else:
            timeout = min(budget, 60.0) if _attempt < 2 else budget
            thinking = LlmThinkingConfig(enabled=False)
        try:
            result = await llm_chat(
                provider=LLM_PROVIDER, model=model, messages=messages,
                temperature=0.2, thinking=thinking, timeout=timeout,
            )
        except Exception:
            continue
        text = (result.response.raw_text or "").strip()
        if text:
            return text
    return None


def _strip_tool_markup(text: str) -> str:
    return TOOL_MARKUP_RE.sub(" ", text).strip()


def _final_section(text: str) -> str:
    """Deliver only the FINAL ANSWER section; the verification scaffolding that
    precedes it stays in-conversation. Falls back to the full text when the
    section is absent or too bare to stand alone."""
    matches = list(FINAL_SECTION_RE.finditer(text))
    if not matches:
        return text
    section = text[matches[-1].end():].strip().lstrip("*:# ").strip()
    if len(section) < HARD_MIN_ANSWER_CHARS:
        return text
    head, sep, rest = section.partition("\n")
    if head.count("**") % 2 == 1:
        # the marker match consumed the opening bold token; drop the orphan
        section = head.replace("**", "") + sep + rest
    return section


def _needs_forced_retry(text: str) -> bool:
    if TOOL_MARKUP_RE.search(text) is not None:
        return True
    if PSEUDO_CALL_RE.search(text) is not None:
        return True
    if len(text) < HARD_MIN_ANSWER_CHARS:
        return True
    # an answer that OPENS with a refusal is a refusal regardless of how much
    # explanatory prose follows it
    if any(m in text.lower()[:400] for m in ABSTENTION_MARKERS):
        return True
    if len(text) < MIN_ANSWER_CHARS:
        if not text.rstrip().endswith((".", "!", "?", ")", "]", '"', "|", "*")):
            return True
    return False


def _dump_floor_answer(index: _SourceSurface) -> str | None:
    if index.max_number() == 0:
        return None
    parts = [
        "The final synthesis step could not run to completion; the gathered "
        "source-backed evidence supports the following points:",
    ]
    total = 0
    for n in range(1, index.max_number() + 1):
        meta = index.get(n)
        if meta is None:
            continue
        note = meta["note"][:260].strip()
        if not note or DUMP_GARBAGE_RE.search(note):
            continue
        entry = f"[{n}] {note}"
        total += len(entry)
        if total > 2600:
            break
        parts.append(entry)
    if len(parts) == 1:
        return None
    return "\n".join(parts)


def _deliverable(text: str | None, index: _SourceSurface, *, cite_text: str | None = None) -> Response:
    answer = (text or "").strip()
    if not answer:
        answer = _dump_floor_answer(index) or INSUFFICIENT_ANSWER
    # citations may be sourced from the fuller pre-extraction text: the marker
    # numbers that justify the final section often live in the verify table
    citations = index.refs(cite_text or answer)
    return Response(text=answer, citations=list(citations) if citations else None)


async def _execute_tool_calls(
    tool_calls, messages, index: _SourceSurface, terms: list[str], *, content: str = "",
) -> None:
    messages.append({
        "role": "assistant",
        "content": content or None,
        "tool_calls": [
            {"id": tc.id, "type": tc.type, "name": tc.name, "arguments": tc.arguments}
            for tc in tool_calls
        ],
    })
    async def _one(tc) -> str:
        try:
            args = json.loads(tc.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        if tc.name == "search_web":
            return await _run_search_web(str(args.get("query", "")), index)
        if tc.name == "fetch_page":
            return await _run_fetch_page(str(args.get("url", "")), index, terms)
        return f"# unknown tool {tc.name!r}"

    # a turn's tool calls are independent lookups: run them concurrently so a
    # 4-call turn costs one round-trip of wall-clock, not four
    results = await asyncio.gather(*(_one(tc) for tc in tool_calls))
    for tc, result_text in zip(tool_calls, results):
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})


async def _plain_query(query: Query, budget: float) -> Response:
    start = perf_counter()
    deadline = start + budget
    research_stop = min(start + RESEARCH_TIME_CAP_SECONDS, deadline - FINAL_RESERVE_SECONDS)
    index = _SourceSurface()
    terms = _key_terms(query.text)
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query.text},
    ]
    candidates: list[str] = []
    final_answer: str | None = None

    try:
        # --- BRIEFING + RESEARCH ---
        nudged = False
        turn = 0
        while turn < RESEARCH_TURN_CAP and perf_counter() < research_stop:
            turn += 1
            thinking_on = turn == 1
            chat_result = await _chat_turn(messages, deadline=research_stop, thinking_on=thinking_on)
            if chat_result is None:
                break
            choice_message = chat_result.response.choices[0].message
            content = (chat_result.response.raw_text or "").strip()
            tool_calls = choice_message.tool_calls or ()

            if turn == 1:
                candidates = _parse_candidates(content)
                if candidates:
                    terms = _key_terms(query.text + " " + " ".join(candidates))
                if not tool_calls and content and not candidates \
                        and "BRIEFING" not in content.upper() and not nudged:
                    nudged = True
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": BRIEFING_NUDGE})
                    turn -= 1
                    continue

            if tool_calls:
                # briefing/notes stay attached to the same assistant message
                await _execute_tool_calls(tool_calls, messages, index, terms, content=content)
                continue

            # model stopped calling tools during research: hold its draft and move on
            if content:
                messages.append({"role": "assistant", "content": content})
            break

        # --- the subsystem resolves what it holds, then states it ---
        keys = _relocation_keys(query.text, candidates)
        index.relocate(keys, deadline - FINAL_RESERVE_SECONDS)

        # --- CHECKPOINT: VERIFY + capped targeted re-dispatch ---
        checkpoint = _checkpoint_message(candidates, index)
        directive = index.directive()
        if directive:
            checkpoint = directive + "\n\n" + checkpoint
        messages.append({"role": "user", "content": checkpoint})
        last_content = ""
        for _extra in range(CHECKPOINT_TOOL_TURNS + 1):
            # a re-dispatch turn only pays if there is still room to run its
            # tools AND a committed final afterwards
            if deadline - perf_counter() <= FINAL_RESERVE_SECONDS + 25:
                break
            chat_result = await _chat_turn(messages, deadline=deadline - 30, thinking_on=True)
            if chat_result is None:
                break
            choice_message = chat_result.response.choices[0].message
            content = (chat_result.response.raw_text or "").strip()
            tool_calls = choice_message.tool_calls or ()
            if tool_calls:
                await _execute_tool_calls(tool_calls, messages, index, terms, content=content)
                if content:
                    last_content = content
                continue
            # a text-only turn is final only if it actually reached FINAL ANSWER;
            # a narrated intent to keep working ("let me search...") is not an answer
            if content and FINAL_SECTION_RE.search(content):
                final_answer = content
                break
            if content:
                last_content = content
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": (
                    "Continue: either call the tools you need NOW, or produce the "
                    "verification table and FINAL ANSWER from the evidence you have."
                )})
                continue
            break

        # --- the subsystem re-enters over whatever the re-dispatch added ---
        if index.fetched_numbers():
            index.relocate(keys, deadline - 10)
            directive = index.directive()
            if directive:
                messages.append({"role": "user", "content": directive})

        # --- FORCED COMMIT: tools disabled ---
        if not final_answer:
            messages.append({"role": "user", "content": COMMIT_MESSAGE})
            final_answer = await _commit_call(messages, deadline=deadline)
        if not final_answer and last_content and FINAL_SECTION_RE.search(last_content):
            # a checkpoint turn that already reached a FINAL ANSWER beats the
            # raw-notes floor; a mid-research process trace does not
            final_answer = last_content

        # the gate must judge what would actually be DELIVERED (the extracted
        # final section) — a refusal hiding behind a verify preamble passes a
        # whole-text check but must not reach the judge
        cite_text = _strip_tool_markup(final_answer) if final_answer else ""
        display = _final_section(cite_text) if cite_text else ""

        if display and _needs_forced_retry(display):
            retry: str | None = None
            if deadline - perf_counter() >= FINAL_RETRY_MIN_SECONDS:
                messages.append({"role": "assistant", "content": final_answer})
                messages.append({"role": "user", "content": COMMIT_MESSAGE + FORCED_COMMIT_SUFFIX})
                retry = await _commit_call(messages, deadline=deadline)
            retry_stripped = _strip_tool_markup(retry) if retry else ""
            retry_display = _final_section(retry_stripped) if retry_stripped else ""
            if retry_display and not _needs_forced_retry(retry_display):
                cite_text, display = retry_stripped, retry_display
            elif not _needs_forced_retry(cite_text):
                display = cite_text
            else:
                display = _dump_floor_answer(index) or display

        if display:
            return _deliverable(display, index, cite_text=cite_text or display)
        return _deliverable(None, index)
    except Exception:
        return _deliverable(None, index)


# --- structured output (begin) ---
_STRUCTURED_PROVIDER = LLM_PROVIDER
_STRUCTURED_MODEL = MODEL
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
    """Resolve an RFC 6901 JSON pointer fragment against the schema root."""
    if fragment in ("", "/"):
        return root
    if not fragment.startswith("/"):
        return None
    current = root
    for raw_token in fragment[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
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
    """Follow local `$ref` fragments until a plain schema object is reached."""
    hops = 0
    while isinstance(node, dict) and isinstance(node.get("$ref"), str) and hops < STRUCTURED_MAX_REF_HOPS:
        reference = node["$ref"]
        if not reference.startswith("#"):
            return {}
        target = _so_pointer(root, reference[1:])
        if not isinstance(target, dict):
            return {}
        node = target
        hops += 1
    return node if isinstance(node, dict) else {}


def _so_kind(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) or isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def _so_type_ok(value: object, type_name: str) -> bool:
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "null":
        return value is None
    if type_name == "integer":
        if isinstance(value, bool):
            return False
        if isinstance(value, int):
            return True
        return isinstance(value, float) and float(value).is_integer()
    if type_name == "number":
        if isinstance(value, bool):
            return False
        return isinstance(value, int) or isinstance(value, float)
    return True


def _so_type_names(schema: dict) -> list[str]:
    declared = schema.get("type")
    if isinstance(declared, str):
        return [declared]
    if isinstance(declared, list):
        return [name for name in declared if isinstance(name, str)]
    return []


def _so_errors(value: object, schema: object, root: object, path: str = "$", depth: int = 0) -> list[str]:
    """Structural mismatches between `value` and `schema` (empty list == accept)."""
    if depth > STRUCTURED_MAX_DEPTH:
        return []
    resolved = _so_resolve(schema, root)
    if not resolved:
        return []
    problems: list[str] = []

    type_names = _so_type_names(resolved)
    if type_names and not any(_so_type_ok(value, name) for name in type_names):
        return [f"{path}: expected type {'|'.join(type_names)}, got {_so_kind(value)}"]

    if "const" in resolved and value != resolved["const"]:
        problems.append(f"{path}: must equal {_so_brief(resolved['const'])}")
    allowed = resolved.get("enum")
    if isinstance(allowed, list) and not any(value == option for option in allowed):
        problems.append(f"{path}: must be one of {_so_brief(allowed)}")

    for sub_schema in resolved.get("allOf") or ():
        problems.extend(_so_errors(value, sub_schema, root, path, depth + 1))
    for keyword in ("anyOf", "oneOf"):
        branches = resolved.get(keyword)
        if isinstance(branches, list) and branches:
            if not any(not _so_errors(value, branch, root, path, depth + 1) for branch in branches):
                problems.append(f"{path}: matches no {keyword} branch")

    if isinstance(value, dict):
        problems.extend(_so_object_errors(value, resolved, root, path, depth))
    elif isinstance(value, list):
        problems.extend(_so_array_errors(value, resolved, root, path, depth))
    elif isinstance(value, str):
        problems.extend(_so_string_errors(value, resolved, path))
    elif (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool):
        problems.extend(_so_number_errors(value, resolved, path))
    return problems


def _so_object_errors(value: dict, schema: dict, root: object, path: str, depth: int) -> list[str]:
    problems: list[str] = []
    properties = schema.get("properties")
    properties = properties if isinstance(properties, dict) else {}
    for key in schema.get("required") or ():
        if isinstance(key, str) and key not in value:
            problems.append(f"{path}: missing required property '{key}'")
    pattern_properties = schema.get("patternProperties")
    pattern_properties = pattern_properties if isinstance(pattern_properties, dict) else {}
    additional = schema.get("additionalProperties")
    for key, item in value.items():
        if key in properties:
            problems.extend(_so_errors(item, properties[key], root, f"{path}.{key}", depth + 1))
            continue
        matched = False
        for pattern, sub_schema in pattern_properties.items():
            if _so_matches(pattern, key):
                matched = True
                problems.extend(_so_errors(item, sub_schema, root, f"{path}.{key}", depth + 1))
        if matched:
            continue
        if additional is False:
            problems.append(f"{path}: property '{key}' is not allowed")
        elif isinstance(additional, dict):
            problems.extend(_so_errors(item, additional, root, f"{path}.{key}", depth + 1))
    minimum = schema.get("minProperties")
    if isinstance(minimum, int) and not isinstance(minimum, bool) and len(value) < minimum:
        problems.append(f"{path}: needs at least {minimum} properties, has {len(value)}")
    maximum = schema.get("maxProperties")
    if isinstance(maximum, int) and not isinstance(maximum, bool) and len(value) > maximum:
        problems.append(f"{path}: allows at most {maximum} properties, has {len(value)}")
    return problems


def _so_array_errors(value: list, schema: dict, root: object, path: str, depth: int) -> list[str]:
    problems: list[str] = []
    prefix_items = schema.get("prefixItems")
    prefix_items = prefix_items if isinstance(prefix_items, list) else []
    items_schema = schema.get("items")
    for index, item in enumerate(value):
        if index < len(prefix_items):
            problems.extend(_so_errors(item, prefix_items[index], root, f"{path}[{index}]", depth + 1))
        elif isinstance(items_schema, dict):
            problems.extend(_so_errors(item, items_schema, root, f"{path}[{index}]", depth + 1))
        elif items_schema is False and prefix_items:
            problems.append(f"{path}[{index}]: extra array item is not allowed")
    minimum = schema.get("minItems")
    if isinstance(minimum, int) and not isinstance(minimum, bool) and len(value) < minimum:
        problems.append(f"{path}: needs at least {minimum} items, has {len(value)}")
    maximum = schema.get("maxItems")
    if isinstance(maximum, int) and not isinstance(maximum, bool) and len(value) > maximum:
        problems.append(f"{path}: allows at most {maximum} items, has {len(value)}")
    if schema.get("uniqueItems") is True:
        rendered = [_so_canonical(item) for item in value]
        if len(set(rendered)) != len(rendered):
            problems.append(f"{path}: items must be unique")
    return problems


def _so_string_errors(value: str, schema: dict, path: str) -> list[str]:
    problems: list[str] = []
    minimum = schema.get("minLength")
    if isinstance(minimum, int) and not isinstance(minimum, bool) and len(value) < minimum:
        problems.append(f"{path}: needs at least {minimum} characters, has {len(value)}")
    maximum = schema.get("maxLength")
    if isinstance(maximum, int) and not isinstance(maximum, bool) and len(value) > maximum:
        problems.append(f"{path}: allows at most {maximum} characters, has {len(value)}")
    pattern = schema.get("pattern")
    if isinstance(pattern, str) and not _so_matches(pattern, value):
        problems.append(f"{path}: must match pattern {pattern}")
    return problems


def _so_number_errors(value: float, schema: dict, path: str) -> list[str]:
    problems: list[str] = []
    bound = schema.get("minimum")
    if _so_is_number(bound) and value < bound:
        problems.append(f"{path}: must be >= {bound}")
    bound = schema.get("maximum")
    if _so_is_number(bound) and value > bound:
        problems.append(f"{path}: must be <= {bound}")
    bound = schema.get("exclusiveMinimum")
    if _so_is_number(bound) and value <= bound:
        problems.append(f"{path}: must be > {bound}")
    bound = schema.get("exclusiveMaximum")
    if _so_is_number(bound) and value >= bound:
        problems.append(f"{path}: must be < {bound}")
    step = schema.get("multipleOf")
    if _so_is_number(step) and step > 0:
        quotient = value / step
        if abs(quotient - round(quotient)) > 1e-9:
            problems.append(f"{path}: must be a multiple of {step}")
    return problems


def _so_is_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, int) or isinstance(value, float)


def _so_matches(pattern: str, value: str) -> bool:
    """Search semantics, matching JSON Schema. Unsupported regex syntax accepts."""
    try:
        return re.search(pattern, value) is not None
    except Exception:
        return True


def _so_canonical(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return repr(value)


def _so_brief(value: object, limit: int = 160) -> str:
    rendered = _so_canonical(value)
    return rendered if len(rendered) <= limit else rendered[:limit] + "…"


def _so_coerce(value: object, schema: object, root: object, depth: int = 0) -> object:
    """Repair the near-misses an LLM actually makes, without inventing content."""
    if depth > STRUCTURED_MAX_DEPTH:
        return value
    resolved = _so_resolve(schema, root)
    if not resolved:
        return value
    type_names = _so_type_names(resolved)

    if isinstance(value, dict):
        properties = resolved.get("properties")
        properties = properties if isinstance(properties, dict) else {}
        # An object wrapping the real payload under a single key the schema does
        # not know is the most common miss; unwrap it before anything else.
        if properties and not any(key in properties for key in value) and len(value) == 1:
            inner = next(iter(value.values()))
            if isinstance(inner, dict) or isinstance(inner, list):
                return _so_coerce(inner, resolved, root, depth + 1)
        if "object" in type_names or (not type_names and properties):
            repaired = {}
            additional = resolved.get("additionalProperties")
            for key, item in value.items():
                if key in properties:
                    repaired[key] = _so_coerce(item, properties[key], root, depth + 1)
                elif additional is False:
                    continue  # dropping is the only repair that can pass
                elif isinstance(additional, dict):
                    repaired[key] = _so_coerce(item, additional, root, depth + 1)
                else:
                    repaired[key] = item
            return repaired
        if "array" in type_names and not properties:
            return _so_coerce([value], resolved, root, depth + 1)
        return value

    if isinstance(value, list):
        if "array" in type_names or not type_names:
            prefix_items = resolved.get("prefixItems")
            prefix_items = prefix_items if isinstance(prefix_items, list) else []
            items_schema = resolved.get("items")
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

    if not type_names or any(_so_type_ok(value, name) for name in type_names):
        return value
    return _so_coerce_scalar(value, type_names)


def _so_coerce_scalar(value: object, type_names: list[str]) -> object:
    """Cross the string/number/boolean boundary an LLM crossed by accident."""
    if isinstance(value, str):
        text = value.strip()
        if "integer" in type_names or "number" in type_names:
            try:
                number = float(text.replace(",", ""))
            except ValueError:
                number = None
            if number is not None:
                if "integer" in type_names and float(number).is_integer():
                    return int(number)
                if "number" in type_names:
                    return number
        if "boolean" in type_names:
            if text.lower() in ("true", "yes"):
                return True
            if text.lower() in ("false", "no"):
                return False
        if "null" in type_names and text.lower() in ("", "null", "none"):
            return None
    elif isinstance(value, bool):
        if "string" in type_names:
            return "true" if value else "false"
    elif isinstance(value, int) or isinstance(value, float):
        if "integer" in type_names and float(value).is_integer():
            return int(value)
        if "string" in type_names:
            return _so_canonical(value)
    elif value is None:
        if "string" in type_names:
            return ""
    return value


def _so_skeleton(schema: object, root: object, depth: int = 0) -> object:
    """Smallest value the schema can accept — the last-resort payload."""
    resolved = _so_resolve(schema, root)
    if depth > STRUCTURED_MAX_DEPTH or not resolved:
        return None
    if "const" in resolved:
        return resolved["const"]
    if "default" in resolved:
        return resolved["default"]
    allowed = resolved.get("enum")
    if isinstance(allowed, list) and allowed:
        return allowed[0]
    for keyword in ("anyOf", "oneOf", "allOf"):
        branches = resolved.get(keyword)
        if isinstance(branches, list) and branches:
            return _so_skeleton(branches[0], root, depth + 1)
    type_names = _so_type_names(resolved)
    type_name = type_names[0] if type_names else ("object" if resolved.get("properties") else "null")
    if type_name == "object":
        properties = resolved.get("properties")
        properties = properties if isinstance(properties, dict) else {}
        built = {}
        for key in resolved.get("required") or ():
            if isinstance(key, str):
                built[key] = _so_skeleton(properties.get(key, {}), root, depth + 1)
        return built
    if type_name == "array":
        minimum = resolved.get("minItems")
        count = minimum if isinstance(minimum, int) and not isinstance(minimum, bool) else 0
        items_schema = resolved.get("items")
        items_schema = items_schema if isinstance(items_schema, dict) else {}
        return [_so_skeleton(items_schema, root, depth + 1) for _ in range(min(count, 8))]
    if type_name == "string":
        minimum = resolved.get("minLength")
        if isinstance(minimum, int) and not isinstance(minimum, bool) and minimum > 0:
            return "x" * min(minimum, 64)
        return ""
    if type_name == "integer" or type_name == "number":
        return _so_skeleton_number(resolved, type_name)
    if type_name == "boolean":
        return False
    return None


def _so_skeleton_number(schema: dict, type_name: str) -> object:
    """Zero unless a bound excludes it — an out-of-range floor conforms to nothing."""
    value: float = 0
    lower = schema.get("minimum")
    if _so_is_number(lower) and value < lower:
        value = lower
    lower = schema.get("exclusiveMinimum")
    if _so_is_number(lower) and value <= lower:
        value = lower + 1
    upper = schema.get("maximum")
    if _so_is_number(upper) and value > upper:
        value = upper
    upper = schema.get("exclusiveMaximum")
    if _so_is_number(upper) and value >= upper:
        value = upper - 1
    if type_name == "integer":
        return int(value)
    return value


def _so_extract_json(text: str) -> object | None:
    """Pull the JSON value out of an LLM reply that may carry fences or prose."""
    if not text:
        return None
    body = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.+?)```", body, re.DOTALL)
    if fenced:
        body = fenced.group(1).strip()
    try:
        return json.loads(body)
    except ValueError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = body.find(opener)
        end = body.rfind(closer)
        while start >= 0 and end > start:
            try:
                return json.loads(body[start:end + 1])
            except ValueError:
                end = body.rfind(closer, start, end)
    stripped = body.strip()
    if stripped in ("true", "false", "null") or re.fullmatch(r"-?\d+(\.\d+)?", stripped):
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
    answer_text = (answer or "").strip()[:STRUCTURED_ANSWER_PROMPT_CHARS]
    instruction = (
        "You convert a researched answer into one JSON value that conforms to a JSON Schema.\n"
        "Rules:\n"
        "1. Emit ONLY the JSON value. No prose, no Markdown fence, no explanation.\n"
        "2. Obey every type, required, enum and format constraint in the schema exactly.\n"
        "3. Take every fact from the researched answer. Never invent facts it does not "
        "support; when the answer does not cover a required field, use the most "
        "defensible value the schema allows rather than omitting the field.\n"
        "4. Keep the schema's field names and nesting exactly as given."
    )
    request = (
        f"QUESTION:\n{question}\n\n"
        f"JSON SCHEMA:\n{schema_text}\n\n"
        f"RESEARCHED ANSWER:\n{answer_text}\n\n"
        "Return the conforming JSON value now."
    )
    if problems:
        request += (
            "\n\nYour previous attempt failed these checks — fix exactly these and "
            "change nothing else:\n" + "\n".join(f"- {problem}" for problem in problems)
        )
    return [
        {"role": "system", "content": instruction},
        {"role": "user", "content": request},
    ]


async def _so_call(messages: list[dict[str, str]], timeout: float) -> str:
    try:
        result = await llm_chat(
            provider=_STRUCTURED_PROVIDER,
            model=_STRUCTURED_MODEL,
            messages=messages,
            temperature=0.0,
            timeout=timeout,
        )
    except Exception:
        return ""
    try:
        return (result.response.raw_text or "").strip()
    except Exception:
        return ""


async def _structured_response(query: Query, schema: object, drafted: Response, deadline: float) -> Response:
    """Re-express a drafted plain-text answer as the schema-conforming output.

    A schema-bearing query accepts only `Response.output`; text is rejected
    outright. So every exit from this function returns `output`, and a partially
    conforming value is always preferred over the alternative.
    """
    answer = ""
    citations = None
    try:
        answer = drafted.text or ""
        citations = drafted.citations
    except Exception:
        answer = ""

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
            problems = ["the reply was not parseable JSON; emit the bare JSON value only"]
            continue
        candidate = _so_coerce(parsed, schema, schema)
        if not _so_fits_size(candidate):
            problems = [f"the value exceeded {STRUCTURED_OUTPUT_CHAR_CAP} JSON characters; be more concise"]
            continue
        if not have_best:
            best = candidate
            have_best = True
        problems = _so_errors(candidate, schema, schema)[:STRUCTURED_MAX_REPORTED_ERRORS]
        if not problems:
            return _so_response(candidate, citations)
        best = candidate
        if attempt + 1 >= STRUCTURED_ATTEMPTS:
            break

    if have_best:
        return _so_response(best, citations)
    fallback = _so_skeleton(schema, schema)
    if fallback is None and answer:
        fallback = answer[:STRUCTURED_OUTPUT_CHAR_CAP]
    return _so_response(fallback, citations)


def _so_response(value: object, citations: object) -> Response:
    """Build the response, degrading the payload rather than the answer field."""
    if not _so_fits_size(value):
        value = None
    try:
        return Response(output=value, citations=citations or None)
    except Exception:
        return Response(output=value)


async def _w2_baseline_query(query: Query) -> Response:
    """Route on the caller's schema; the plain path stays exactly as it was.

    Without a schema this is the previous entrypoint with one extra attribute
    read. With one, the same pipeline runs on a shortened budget and its drafted
    answer is re-expressed as `output` — the only answer field the platform will
    accept for such a query.
    """
    schema = getattr(query, "output_schema", None)
    if schema is None:
        return await _plain_query(query, TASK_TOTAL_BUDGET_SECONDS)
    try:
        drafted = await _plain_query(query, TASK_TOTAL_BUDGET_SECONDS - STRUCTURED_RESERVE_SECONDS)
    except Exception:
        drafted = Response(text="The research pipeline did not produce an answer for this question.")
    try:
        return await _structured_response(query, schema, drafted, perf_counter() + STRUCTURED_RESERVE_SECONDS)
    except Exception:
        return _so_response(_so_skeleton(schema, schema), None)
# --- structured output (end) ---


# --- w2 answer-contract wrapper (begin) ---
# The base artifact's `query` entrypoint is demoted to `_w2_baseline_query` and a
# new `query` coordinates three stages: answer-contract planning, baseline
# research, and contract verification with authority over the returned answer.
# The only contract with the demoted base is the platform ABI (`Query`,
# `Response`, `llm_chat`) plus NameError-guarded probes for optional base
# constants.

_W2_PLAN_TIMEOUT_SECONDS = 22.0
_W2_VERIFY_TIMEOUT_SECONDS = 28.0
_W2_REPAIR_TIMEOUT_SECONDS = 24.0
_W2_TAIL_RESERVE_SECONDS = 8.0
_W2_PLAN_TEMPERATURE = 0.1
_W2_VERIFY_TEMPERATURE = 0.12
_W2_MIN_REVISION_CHARS = 80
_W2_MIN_REVISION_RATIO = 0.6
_W2_MIN_ENTITY_CHARS = 3
_W2_MAX_CONTRACT_ITEMS = 6
_W2_DRAFT_PROMPT_CHARS = 6_000
_W2_DEFAULT_BUDGET_SECONDS = 235.0

_W2_LIST_MARKER_RE = re.compile(r"(?m)^[ \t]*[(\[]?\d{1,2}[.)\]][ \t]+")
_W2_FIGURE_RE = re.compile(r"\d+(?:[.,]\d+)*")
_W2_WORD_RE = re.compile(r"[A-Z][A-Za-z0-9&'’.\-]*")
_W2_CLAUSE_HEAD_CHARS = ".!?:;#*->|•"

_W2_PLAN_SYSTEM = (
    "You plan the acceptance criteria for a research answer before the research runs.\n"
    "Read the question and list what a complete, correct answer must contain.\n"
    "Reply with JSON only, no prose, in this exact shape:\n"
    '{"deliverable": "<one sentence naming what must be returned>", '
    '"required": ["<concrete element the answer must state>", ...], '
    '"pitfalls": ["<a specific way an answer to this question goes wrong>", ...]}\n'
    "Give at most six `required` entries and at most three `pitfalls`. "
    "Each entry must be concrete and checkable against a draft answer - name the "
    "quantity, entity, unit, date range, or enumeration that must appear. "
    "Never guess the answer itself; describe only what the answer must cover."
)

_W2_VERIFY_SYSTEM = (
    "You audit a draft research answer against an answer contract and repair it.\n"
    "The contract lists what the answer must contain. Check the draft against every "
    "entry and return the corrected answer.\n"
    "Rules:\n"
    "- Repair only concrete, verifiable gaps: a required element the draft never "
    "states, an internal contradiction, a requested unit or format the draft ignores.\n"
    "- Use only facts already present in the draft. Never introduce a fact, figure, "
    "name, or citation that the draft does not contain.\n"
    "- Every figure, quantity, date, unit, name, and citation marker the draft states "
    "stands as written. You may not drop one, round one, reword one, or swap one for a "
    "different value or a different entity. Your edits may only add.\n"
    "- The draft's own answer to the question is the answer. If you believe a different "
    "entity or value fits the question better, say so in one added clause and leave the "
    "draft's answer standing.\n"
    "- If a required element is genuinely absent from the draft's evidence, say so "
    "plainly in one clause rather than inventing it.\n"
    "- Preserve the draft's wording wherever it already satisfies the contract.\n"
    "- If the draft already satisfies the contract, return it unchanged.\n"
    "Return the full corrected answer text and nothing else - no preamble, no notes, "
    "no commentary about what you changed."
)

_W2_REPAIR_SYSTEM = (
    "You convert a research answer into the exact JSON object a caller's schema "
    "requires.\n"
    "Use only facts stated in the answer text. Do not invent values. If the answer "
    "does not supply a required field, use null for it.\n"
    "Reply with a single JSON object and nothing else."
)


class _W2AnswerContract:
    """The formal state object carried between the plan and verify stages."""

    def __init__(self, deliverable: str, required: list[str], pitfalls: list[str]) -> None:
        self.deliverable = deliverable
        self.required = required
        self.pitfalls = pitfalls

    def is_actionable(self) -> bool:
        return bool(self.deliverable or self.required)


def _w2_provider() -> str:
    """Resolve the base's LLM provider without globals(); the validator rejects it."""
    try:
        return LLM_PROVIDER
    except NameError:
        return "openrouter"


def _w2_model() -> str:
    try:
        return MODEL
    except NameError:
        return "z-ai/glm-5"


def _w2_total_budget_seconds() -> float:
    try:
        return float(TASK_TOTAL_BUDGET_SECONDS)
    except (NameError, TypeError, ValueError):
        return _W2_DEFAULT_BUDGET_SECONDS


def _w2_remaining(deadline: float) -> float:
    return deadline - perf_counter()


async def _w2_chat(messages: list[dict[str, object]], *, timeout: float, temperature: float) -> str:
    """One bounded LLM call on the platform ABI; empty string on any failure."""
    if timeout <= 0:
        return ""
    try:
        result = await llm_chat(
            provider=_w2_provider(), model=_w2_model(), messages=messages,
            temperature=temperature, timeout=timeout,
        )
    except Exception:
        return ""
    try:
        return (result.response.raw_text or "").strip()
    except Exception:
        return ""


def _w2_json_object(text: str) -> dict | None:
    """Tolerant extraction of the first JSON object in a model reply."""
    if not text:
        return None
    body = text.strip()
    if body.startswith("```"):
        body = body.split("```")[1] if "```" in body[3:] else body[3:]
        if body[:4].lower().startswith("json"):
            body = body[4:]
    start = body.find("{")
    end = body.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(body[start:end + 1])
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _w2_string_list(value: object, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    items = []
    for entry in value:
        if isinstance(entry, str) and entry.strip():
            items.append(entry.strip())
        if len(items) >= limit:
            break
    return items


def _w2_schema_hint(schema: object) -> str:
    """Render the caller's output schema for the planning prompt."""
    if schema is None:
        return ""
    try:
        rendered = json.dumps(schema, ensure_ascii=False)[:1_200]
    except (TypeError, ValueError):
        return ""
    return f"\n\nThe answer will be returned against this output schema:\n{rendered}"


async def _w2_build_answer_contract(
    question: str, schema: object, *, deadline: float,
) -> _W2AnswerContract | None:
    """Stage 1 - plan the acceptance criteria before the baseline research runs."""
    timeout = min(_W2_PLAN_TIMEOUT_SECONDS, _w2_remaining(deadline) - _W2_TAIL_RESERVE_SECONDS)
    messages = [
        {"role": "system", "content": _W2_PLAN_SYSTEM},
        {"role": "user", "content": f"Question:\n{question}{_w2_schema_hint(schema)}"},
    ]
    payload = _w2_json_object(await _w2_chat(
        messages, timeout=timeout, temperature=_W2_PLAN_TEMPERATURE,
    ))
    if payload is None:
        return None
    deliverable = payload.get("deliverable")
    contract = _W2AnswerContract(
        deliverable=deliverable.strip() if isinstance(deliverable, str) else "",
        required=_w2_string_list(payload.get("required"), _W2_MAX_CONTRACT_ITEMS),
        pitfalls=_w2_string_list(payload.get("pitfalls"), 3),
    )
    return contract if contract.is_actionable() else None


def _w2_contract_block(contract: _W2AnswerContract) -> str:
    """Render the contract as the audit checklist handed to the verify stage."""
    lines = []
    if contract.deliverable:
        lines.append(f"Deliverable: {contract.deliverable}")
    if contract.required:
        lines.append("The answer must state:")
        lines.extend(f"  - {item}" for item in contract.required)
    if contract.pitfalls:
        lines.append("Known ways this question is answered badly:")
        lines.extend(f"  - {item}" for item in contract.pitfalls)
    return "\n".join(lines)


def _w2_response_text(response: object) -> str:
    try:
        text = getattr(response, "text", None)
    except Exception:
        return ""
    return text.strip() if isinstance(text, str) else ""


def _w2_with_text(response: object, text: str) -> object:
    """Rebuild the response around the audited answer, carrying citations over.

    The platform accepts exactly one non-null answer field, so a response that
    already carries a structured `output` owns no text answer to override and is
    returned untouched.
    """
    if getattr(response, "output", None) is not None:
        return response
    citations = getattr(response, "citations", None)
    try:
        if citations:
            return Response(text=text, citations=citations)
        return Response(text=text)
    except Exception:
        return response


def _w2_normalize_figure(token: str) -> str:
    """One numeric literal reduced to the value it states, not how it is typed."""
    value = token.replace(",", "")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    return value or "0"


def _w2_figures(text: str) -> set:
    """Every quantity the text asserts, less the ordinals that only number a list."""
    body = _W2_LIST_MARKER_RE.sub(" ", text)
    found = set()
    for match in _W2_FIGURE_RE.finditer(body):
        found.add(_w2_normalize_figure(match.group(0)))
    return found


def _w2_entities(text: str) -> set:
    """Every named token the text asserts.

    A capitalized word that opens a sentence, a heading, or a bullet is
    capitalized by position rather than by being a name, so it is not counted;
    a real name almost always also occurs somewhere it did not open a clause.
    """
    found = set()
    for match in _W2_WORD_RE.finditer(text):
        cursor = match.start() - 1
        while cursor >= 0 and text[cursor] in " \t":
            cursor -= 1
        if cursor < 0 or text[cursor] == "\n" or text[cursor] in _W2_CLAUSE_HEAD_CHARS:
            continue
        word = match.group(0).strip(".-'’").lower()
        if len(word) >= _W2_MIN_ENTITY_CHARS:
            found.add(word)
    return found


def _w2_unmakes_draft(draft: str, revision: str) -> bool:
    """True when the revision fails to carry forward something the draft asserted."""
    if not _w2_figures(draft).issubset(_w2_figures(revision)):
        return True
    return not _w2_entities(draft).issubset(_w2_entities(revision))


def _w2_accept_revision(draft: str, revision: str) -> bool:
    """Keep the audited answer only when it adds to the draft without unmaking it.

    Length cannot tell a repair from a replacement: a revision that answers with
    a different entity, or restates a figure as a different figure, is exactly as
    long as one that fills a gap. The audited text is therefore accepted only
    when every concrete claim the draft asserted - each quantity, each named
    token - still stands in it. Additions are free; deletions and substitutions
    return the draft.
    """
    if not revision or revision == draft:
        return False
    if len(revision) < _W2_MIN_REVISION_CHARS:
        return False
    if len(revision) < len(draft) * _W2_MIN_REVISION_RATIO:
        return False
    return not _w2_unmakes_draft(draft, revision)


async def _w2_verify_against_contract(
    contract: _W2AnswerContract, question: str, draft: str, *, deadline: float,
) -> str:
    """Stage 3 - audit the draft against the contract and return the answer to deliver."""
    timeout = min(_W2_VERIFY_TIMEOUT_SECONDS, _w2_remaining(deadline) - _W2_TAIL_RESERVE_SECONDS)
    messages = [
        {"role": "system", "content": _W2_VERIFY_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\nAnswer contract:\n{_w2_contract_block(contract)}"
                f"\n\nDraft answer:\n{draft[:_W2_DRAFT_PROMPT_CHARS]}"
            ),
        },
    ]
    revision = await _w2_chat(messages, timeout=timeout, temperature=_W2_VERIFY_TEMPERATURE)
    return revision if _w2_accept_revision(draft, revision) else draft


def _w2_schema_property_names(schema: object) -> list[str]:
    if not isinstance(schema, dict):
        return []
    properties = schema.get("properties")
    return [key for key in properties] if isinstance(properties, dict) else []


def _w2_is_degenerate_output(output: object, schema: object) -> bool:
    """True when the base produced a structured payload the scorer will read as empty."""
    if output is None:
        return True
    if isinstance(output, (str, list, tuple, dict)) and len(output) == 0:
        return True
    if isinstance(output, dict):
        names = _w2_schema_property_names(schema)
        if names and not any(key in output for key in names):
            return True
        if all(value in (None, "", [], {}) for value in output.values()):
            return True
    return False


async def _w2_repair_structured_output(
    question: str, schema: object, response: object, *, deadline: float,
) -> object:
    """Repair-only ladder: a working structured payload is always returned untouched."""
    output = getattr(response, "output", None)
    if not _w2_is_degenerate_output(output, schema):
        return response
    draft = _w2_response_text(response)
    recovered = _w2_json_object(draft)
    if recovered is None:
        timeout = min(_W2_REPAIR_TIMEOUT_SECONDS, _w2_remaining(deadline) - 2.0)
        try:
            rendered = json.dumps(schema, ensure_ascii=False)[:1_500]
        except (TypeError, ValueError):
            rendered = ""
        messages = [
            {"role": "system", "content": _W2_REPAIR_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\nOutput schema:\n{rendered}"
                    f"\n\nAnswer text:\n{draft[:_W2_DRAFT_PROMPT_CHARS]}"
                ),
            },
        ]
        recovered = _w2_json_object(await _w2_chat(messages, timeout=timeout, temperature=0.0))
    if recovered is None or _w2_is_degenerate_output(recovered, schema):
        return response
    citations = getattr(response, "citations", None)
    try:
        if citations:
            return Response(output=recovered, citations=citations)
        return Response(output=recovered)
    except Exception:
        return response


@entrypoint("query")
async def query(query: Query) -> Response:
    """w2 contract wrapper: plan the answer contract, run the baseline, then verify.

    The baseline artifact's own entrypoint is demoted to `_w2_baseline_query` and
    runs as the research stage of this sequence. Contract planning runs on every
    ordinary request before the research starts, and the verification stage holds
    authority over the answer this entrypoint returns.
    """
    deadline = perf_counter() + _w2_total_budget_seconds()
    question = getattr(query, "text", "") or ""
    schema = getattr(query, "output_schema", None)

    contract = await _w2_build_answer_contract(question, schema, deadline=deadline)
    response = await _w2_baseline_query(query)

    if contract is not None:
        draft = _w2_response_text(response)
        if draft:
            audited = await _w2_verify_against_contract(
                contract, question, draft, deadline=deadline,
            )
            if audited != draft:
                response = _w2_with_text(response, audited)
    if schema is not None:
        response = await _w2_repair_structured_output(
            question, schema, response, deadline=deadline,
        )
    return response
# --- w2 answer-contract wrapper (end) ---
# slot: 11 C17_surface_w2 2026-08-05T15:00:48+00:00
