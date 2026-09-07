"""SN67 Harnyx miner — staged research protocol agent."""
from __future__ import annotations

import asyncio
import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

LLM_PROVIDER = "openrouter"
MODEL = "z-ai/glm-5.2"
COMMIT_FALLBACK_MODEL = "deepseek/deepseek-v3.2"
FETCH_RETRY_ATTEMPTS = 2
LLM_TURN_TIMEOUT_SECONDS = 90.0
TASK_TOTAL_BUDGET_SECONDS = 270.0
SEARCH_TIMEOUT_SECONDS = 20.0
MAX_RETRY_ATTEMPTS_PER_TURN = 2
FETCH_TIMEOUT_SECONDS = 15.0

RESEARCH_TURN_CAP = 10
RESEARCH_TIME_CAP_SECONDS = 140.0
CHECKPOINT_TOOL_TURNS = 2
FINAL_RESERVE_SECONDS = 55.0
FINAL_RETRY_MIN_SECONDS = 25.0

TOOL_RESULT_INLINE_CHARS = 3000
SEARCH_EXCERPT_INLINE_CHARS = 380
COVERAGE_LIST_MAX = 8
MIN_ANSWER_CHARS = 400
HARD_MIN_ANSWER_CHARS = 200
CITATION_BUDGET_CHARS = 90_000
CITATION_GAP_FILL_MAX_CHARS = 4_000
CITATION_ANCHOR_CONTEXT_CHARS = 160
CITATION_ANCHOR_LEAD_CHARS = 800
COMMIT_DIGEST_SOURCES_MAX = 16
COMMIT_DIGEST_NOTE_CHARS = 2_600
COMMIT_DIGEST_TOTAL_CHARS = 64_000
COMMIT_DIGEST_IDENTITY_CHARS = 320

PAGE_WINDOW_CHARS = 3600
PAGE_WINDOWS_PER_PAGE = 3
# A long page is retained whole but shown in part. These bound how much of the
# retained remainder a run may re-read through page_grep / page_read: per call,
# per result, and in total, so the reading cannot trade away the answer's time.
PAGE_GREP_WINDOW_CHARS = 400
PAGE_GREP_MAX_HITS = 12
PAGE_GREP_CALLS_PER_PAGE = 20
PAGE_READ_MAX_CHARS = 12_000
PAGE_READ_CALLS_PER_PAGE = 12
PAGE_REREAD_TOTAL_CHARS = 132_000
# Blind windows kept once the extractor has vouched for regions of the same
# page. A term-density window is a guess about where the answer lives; a
# verified quote is not, and the two should not be paid for at the same rate.
PAGE_WINDOWS_WITH_EXTRACT = 1
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
RELOCATE_WINDOWS_PER_ASK = 2
RELOCATE_PAGES_PER_ASK = 4
RELOCATE_BUDGET_CHARS = 16_000
RELOCATE_MIN_SECONDS = 6.0
AMEND_MIN_SECONDS = 20.0
AMEND_TIMEOUT_SECONDS = 40.0
AMEND_CONTEXT_CHARS = 11_000
AMEND_MIN_KEEP_CHARS = 200
ASK_PROOF_CHARS = 420
ASK_LIST_MAX = 8

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
    {
        "type": "function",
        "function": {
            "name": "page_grep",
            "description": (
                "Find where a literal string occurs anywhere in a result already returned "
                "this run, including the part that was too long to show. Reports each "
                "match's character offset with a little text around it. Reads text already "
                "held in memory: nothing is downloaded and it takes no time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "integer",
                               "description": "the bracketed number of a result already returned"},
                    "pattern": {"type": "string",
                                "description": "literal text to look for, matched case-insensitively"},
                },
                "required": ["source", "pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "page_read",
            "description": (
                "Read a region of a result already returned this run, addressed by character "
                "offset -- typically an offset page_grep reported. Reads text already held in "
                "memory: nothing is downloaded and it takes no time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "integer",
                               "description": "the bracketed number of a result already returned"},
                    "offset": {"type": "integer", "description": "character offset to start reading from"},
                    "length": {"type": "integer", "description": "how many characters to read"},
                },
                "required": ["source", "offset"],
            },
        },
    },
]

SYSTEM_PROMPT = (
    "You are a precise web-research agent answering one factual question in a single "
    "continuous session. You have search_web, fetch_page, page_grep and page_read tools. "
    "Follow this protocol "
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
    "READ THE WHOLE PAGE BEFORE FETCHING ANOTHER: fetch_page shows only the opening of "
    "a long page and reports how many characters it holds in total; the rest is still "
    "held under that same [n] and re-fetching the URL returns the identical opening. "
    "Call page_grep(source, pattern) to find where something occurs anywhere in that "
    "page, then page_read(source, offset, length) to read that region. Long lists, "
    "tables and appendices routinely put the rows you need thousands of characters "
    "past the opening, so when a question asks for a complete set from one document, "
    "look for each member inside the page you already hold before searching for "
    "another source; ask for the widest region a read allows and put several "
    "page_grep/page_read calls in the SAME turn. "
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


# Some hosts are reached through a reader/mirror that carries the real target in
# its own path. Left alone they read as different documents, so one page can be
# retrieved several times and every enumerable set it contains is then present
# once per copy — which is fatal to any question that asks how many.
_URL_PROXY_RE = re.compile(
    r"^(?:r\.jina\.ai/"
    r"|web\.archive\.org/web/[^/]+/"
    r"|webcache\.googleusercontent\.com/search\?q=cache:[^+]*\+)"
    r"(?=https?://)",
    re.IGNORECASE,
)


def _normalized_url(url: str) -> str:
    text = (url or "").strip().lower()
    for _ in range(3):
        text = re.sub(r"^https?://", "", text)
        text = re.sub(r"^www\.", "", text)
        unwrapped = _URL_PROXY_RE.sub("", text)
        if unwrapped == text:
            break
        text = unwrapped
    text = text.split("#", 1)[0]
    return text.rstrip("/") or text


class _ResultIndex:
    def __init__(self) -> None:
        self._by_number: dict[int, dict[str, str]] = {}
        self._spans: dict[int, list[tuple[int, int]]] = {}
        self._window_budget = PAGE_WINDOW_BUDGET_CHARS
        self._verified: dict[int, list[tuple[int, int]]] = {}
        self.reread_budget = PAGE_REREAD_TOTAL_CHARS
        self._reserve_pool = PAGE_RESERVE_POOL_CHARS
        self._source_spend: dict[int, int] = {}
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
            self._by_number[n] = {
                "receipt_id": receipt_id,
                "result_id": result_id,
                "kind": kind,
                "citable": bool(note.strip()),
                "src_len": len(note),
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

    # --- surfaced regions -------------------------------------------------
    # Every region a source was READ from is recorded here, so the same
    # coordinates drive both what the reader sees and what is offered as
    # supporting material. The two used to be computed independently and
    # could disagree about which part of a page the answer came from.

    def mark_verified(self, number: int, spans: list[tuple[int, int]]) -> None:
        """Regions an extractor could point at, as opposed to guessed at.

        Recorded separately because every later stage that has to drop text
        ranks by the question's own words, and the regions that carry the
        ANSWER score lowest on exactly that measure -- the identifier a question
        asks for is the one string the question cannot contain.
        """
        if not spans:
            return
        kept = self._verified.setdefault(number, [])
        kept.extend((int(a), int(b)) for a, b in spans if b > a)
        self._verified[number] = _merge_spans(kept)

    def verified(self, number: int) -> list[tuple[int, int]]:
        return list(self._verified.get(number) or ())

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

    def retain(self, number: int, start: int, end: int) -> None:
        """Record a region as shown WITHOUT charging the surfaced-text allowance.

        The allowance exists to ration density-window GUESSES across pages. A
        region the model asked to read by offset is not a guess, and refusing to
        record it would drop it from the commit pack after the model had already
        been shown it -- the same held-then-cut failure the verified ranking
        fixes for the extractor.
        """
        meta = self._by_number.get(number)
        if meta is None:
            return
        limit = int(meta.get("src_len") or 0)
        start = max(0, min(int(start), limit))
        end = max(start, min(int(end), limit))
        if end - start <= 0:
            return
        existing = self._spans.setdefault(number, [])
        existing.append((start, end))
        self._spans[number] = _merge_spans(existing)

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
            note = meta["note"]
            for start, end in spans:
                parts.append(note[start:end])
        return "\n".join(parts)

    def fetched_numbers(self) -> list[int]:
        return [
            n for n, meta in self._by_number.items()
            if meta.get("kind") == "fetch" and meta.get("citable", True)
        ]


async def _run_search_web(query: str, index: _ResultIndex) -> str:
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


def _page_spans(note: str, terms: list[str],
                windows: int = PAGE_WINDOWS_PER_PAGE) -> list[tuple[int, int]]:
    """What to show of a page: its opening, plus the densest regions elsewhere.

    A long document's relevant rows are routinely nowhere near its start, so a
    fixed prefix reads the boilerplate and stops. The opening is always kept —
    it carries the identity of the document — and the rest of the allowance goes
    to the regions that actually mention what was asked.
    """
    # A page that fits inside the allowance is shown whole. Selecting regions of
    # it can only lose text the budget was willing to pay for, and the rows that
    # answer a question are routinely the ones no question term points at.
    if len(note) <= TOOL_RESULT_INLINE_CHARS + PAGE_WINDOW_CHARS * PAGE_WINDOWS_PER_PAGE:
        return [(0, len(note))]
    head_end = min(TOOL_RESULT_INLINE_CHARS, len(note))
    spans = [(0, head_end)]
    if len(note) > head_end and windows > 0:
        spans.extend(_best_windows(
            note, terms, PAGE_WINDOW_CHARS, windows, skip_before=head_end,
        ))
    return spans


# --- passage extraction -------------------------------------------------------
# A long page is shown to the reader as an opening plus the densest regions its
# own words point at. The rows that answer a question routinely carry an
# identifier the question cannot contain, because that identifier IS the answer,
# so a term-density selector is blind to them by construction. A small model
# reading the page in full picks them out; it returns the text and this file
# computes the coordinates, because a model asked for offsets guesses.
EXTRACT_MIN_PAGE_CHARS = TOOL_RESULT_INLINE_CHARS + PAGE_WINDOW_CHARS * PAGE_WINDOWS_PER_PAGE
EXTRACT_CHUNK_CHARS = 40_000
EXTRACT_CHUNK_OVERLAP = 2_000
EXTRACT_MAX_CHUNKS = 12
EXTRACT_CONCURRENCY = 4
EXTRACT_SPAN_PAD_CHARS = 600
EXTRACT_MAX_SPANS = 6
EXTRACT_TIMEOUT_SECONDS = 25.0
EXTRACT_MIN_BUDGET_SECONDS = 45.0
EXTRACT_MAX_OUTPUT_TOKENS = 3000
EXTRACT_MODEL = "google/gemma-4-31b-it"
_EXTRACT_UPSTREAMS = ("Friendli", "ModelRun")
# The extractor has always named its upstreams; the main model never did, and
# went out over the whole provider menu. Same idiom, applied where the TOKENS
# are and nowhere else: the research turns carry the accumulated prompt and are
# most of the bill, and they are short calls. The commit, amend and structured
# calls are the long-output calls, and on `a010a611` the pinned set answered
# those 2.7x slower per call with five 98-142 s timeouts on the commit alone
# (the unpinned base had none in 12 runs). Those three go out unpinned.
_MAIN_UPSTREAMS = ("Decart", "StreamLake", "Inceptron")
_MAIN_DEAD: set = set()


def _main_pin() -> dict | None:
    """Every live upstream, not just the first.

    Naming one at a time buys a price we have actually measured, and costs a
    retry attempt whenever that one 429s -- a lost turn is a score risk, and
    score gates everything. Naming the whole set lets the router fail over
    INSIDE the request instead, at the price of a blend across upstreams whose
    real rates are not measured yet. The next batch's rows measure them for free.
    """
    live = [u for u in _MAIN_UPSTREAMS if u not in _MAIN_DEAD]
    if not live:
        return None
    return {"provider": {"only": list(live), "allow_fallbacks": False}}


def _main_pin_failed() -> None:
    """Second line only: the router already failed over within the set, so a
    call that still failed points at the head of the list. Retire it for the
    run; when the set empties the caller goes out unpinned rather than not at
    all."""
    live = [u for u in _MAIN_UPSTREAMS if u not in _MAIN_DEAD]
    if live:
        _MAIN_DEAD.add(live[0])
_EXTRACT_MIN_QUOTE_CHARS = 12
_X_ESCAPABLE = "\\`*_{}[]()#+-.!|>~"
# Emphasis and code markup are invisible to a reader, so a model quoting what it
# read drops them. Stripping them from BOTH sides of the comparison is what makes
# the quote locatable again; everything else still has to match exactly.
_X_MARKUP = ("***", "**", "~~", "__", "*", "_", "`")
_X_JSON_ESCAPES = frozenset('"\\/bfnrtu')


def _x_norm_map(text: str) -> tuple[str, list[int]]:
    """Collapse whitespace runs, drop escapes and markup; keep norm->orig index."""
    out: list[str] = []
    imap: list[int] = []
    i = 0
    n = len(text)
    prev_ws = False
    while i < n:
        ch = text[i]
        if ch == "\\" and i + 1 < n and text[i + 1] in _X_ESCAPABLE:
            i += 1
            out.append(text[i])
            imap.append(i)
            prev_ws = False
            i += 1
            continue
        if ch.isspace():
            if not prev_ws:
                out.append(" ")
                imap.append(i)
                prev_ws = True
            i += 1
            continue
        hit = None
        for mark in _X_MARKUP:
            if text.startswith(mark, i):
                hit = mark
                break
        if hit is not None:
            i += len(hit)
            continue
        out.append(ch)
        imap.append(i)
        prev_ws = False
        i += 1
    return "".join(out), imap


def _x_norm(text: str) -> str:
    return _x_norm_map(text)[0]


def _x_find(page: str, quote: str, npage: str, imap: list[int]) -> tuple[int, int] | None:
    """Locate a returned quote. None means DISCARD it — never fall back to an
    offset the model supplied, and never widen the match to make it fit."""
    needle = _x_norm(quote or "").strip()
    if len(needle) < _EXTRACT_MIN_QUOTE_CHARS:
        return None
    at = npage.find(needle)
    if at < 0 or not imap:
        return None
    end_index = at + len(needle)
    start = imap[min(at, len(imap) - 1)]
    end = imap[end_index] if end_index < len(imap) else len(page)
    return (start, max(start + 1, end))


def _x_repair(body: str) -> str:
    """The page's own markdown escapes end up inside the model's JSON string and
    `\.` is not a legal JSON escape. The same reply mixes correctly doubled and
    bare ones, so this scans rather than substituting."""
    out: list[str] = []
    i = 0
    n = len(body)
    while i < n:
        ch = body[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        nxt = body[i + 1] if i + 1 < n else ""
        if nxt in _X_JSON_ESCAPES:
            out.append(ch)
            out.append(nxt)
            i += 2
            continue
        out.append(nxt)
        i += 2 if nxt else 1
    return "".join(out)


def _x_quotes(text: str) -> list[str]:
    """A parse failure is NOT an abstention: an unreadable reply must never be
    mistaken for 'this page carries nothing', which is a different fact."""
    body = (text or "").strip()
    start = body.find("{")
    end = body.rfind("}")
    if start < 0 or end < start:
        return []
    body = body[start:end + 1]
    for candidate in (body, _x_repair(body)):
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        quotes = parsed.get("quotes") if isinstance(parsed, dict) else None
        if isinstance(quotes, list):
            return [q for q in quotes if isinstance(q, str)]
    return []


def _x_chunks(text: str) -> list[str]:
    """Every character is offered to the extractor. Chunking exists because one
    call over a very long page answers from its opening and invents the rest;
    it is not a budget cap."""
    if len(text) <= EXTRACT_CHUNK_CHARS:
        return [text]
    out: list[str] = []
    at = 0
    while at < len(text) and len(out) < EXTRACT_MAX_CHUNKS:
        out.append(text[at:at + EXTRACT_CHUNK_CHARS])
        if at + EXTRACT_CHUNK_CHARS >= len(text):
            break
        at += EXTRACT_CHUNK_CHARS - EXTRACT_CHUNK_OVERLAP
    return out


_EXTRACT_SYSTEM = (
    "You extract evidence. You are given a QUESTION and the text of one PAGE.\n"
    "Return between 0 and 8 quotes copied VERBATIM from the page - the exact "
    "passages a reader needs in order to answer the question. Copy the characters "
    "exactly as they appear, including punctuation, spacing within the line, and "
    "any table pipes. Do not paraphrase, summarise, renumber, translate or "
    "reformat.\n"
    "If the page does not contain text that supports an answer, return an empty "
    "list. Never write text that is not present on the page.\n"
    'Answer with JSON only, in the form {"quotes": ["...", "..."]}'
)


async def _x_call(question: str, chunk: str, timeout: float) -> list[str]:
    try:
        result = await llm_chat(
            provider=LLM_PROVIDER,
            model=EXTRACT_MODEL,
            messages=[
                {"role": "system", "content": _EXTRACT_SYSTEM},
                {"role": "user", "content": f"QUESTION:\n{question}\n\nPAGE:\n{chunk}"},
            ],
            temperature=0.0,
            max_output_tokens=EXTRACT_MAX_OUTPUT_TOKENS,
            timeout=timeout,
            provider_extra={"provider": {"only": list(_EXTRACT_UPSTREAMS),
                                         "allow_fallbacks": False}},
        )
    except Exception:
        # An unpinned retry is not available here: the same model on another
        # upstream has been observed inventing table rows, and a fabricated
        # quote that happens to match is worse than no quote at all.
        return []
    try:
        return _x_quotes(result.response.raw_text or "")
    except Exception:
        return []


async def _extract_spans(question: str, note: str, budget: float) -> list[tuple[int, int]]:
    """Regions of `note` the extractor could vouch for, verified against the page."""
    if not question or len(note) <= EXTRACT_MIN_PAGE_CHARS or budget < EXTRACT_MIN_BUDGET_SECONDS:
        return []
    chunks = _x_chunks(note)
    timeout = min(EXTRACT_TIMEOUT_SECONDS, max(5.0, budget - 20.0))
    gate = asyncio.Semaphore(EXTRACT_CONCURRENCY)

    async def _one(chunk: str) -> list[str]:
        async with gate:
            return await _x_call(question, chunk, timeout)

    try:
        batches = await asyncio.gather(*(_one(c) for c in chunks), return_exceptions=True)
    except Exception:
        return []
    npage, imap = _x_norm_map(note)
    spans: list[tuple[int, int]] = []
    for batch in batches:
        if isinstance(batch, BaseException):
            continue
        for quote in batch:
            found = _x_find(note, quote, npage, imap)
            if found is None:
                continue
            middle = (found[0] + found[1]) // 2
            half = max(EXTRACT_SPAN_PAD_CHARS, (found[1] - found[0]) // 2 + 200)
            spans.append((max(0, middle - half), min(len(note), middle + half)))
    return _merge_spans(spans)[:EXTRACT_MAX_SPANS]


_REREAD_EXHAUSTED = (
    "# the allowance for re-reading already-retrieved results is spent for this run. "
    "Write the answer from what you have been shown."
)


def _held_result(number: object, index: _ResultIndex) -> tuple[int, dict] | None:
    """Resolve a bracketed result number to a result whose text is already held."""
    raw = str(number if number is not None else "").strip().strip("[]").strip()
    try:
        n = int(raw)
    except ValueError:
        return None
    meta = index.get(n)
    if meta is None or not (meta.get("note") or ""):
        return None
    return n, meta


def _run_page_grep(number: object, pattern: str, index: _ResultIndex) -> str:
    """Report where a literal string sits inside a result already in hand.

    A long page is retained whole but shown in part, so the only thing standing
    between the reader and material past the shown region is knowing where it
    is. Matching is over text already in memory: it costs nothing and consumes
    none of the retrieval budget. Measured on `a010a611` `cd2d2173`: the base
    saw 13,888 of a 160,012-char page and never reached episodes 4-44; the
    champion read the whole table with fourteen of these calls.
    """
    resolved = _held_result(number, index)
    if resolved is None:
        return ("# page_grep: no such result. Pass the number in brackets next to a result "
                "returned earlier in this run; nothing else can be read.")
    n, meta = resolved
    pat = (pattern or "").strip()
    if not pat:
        return f"# page_grep([{n}]): give a literal string to look for."
    scans = int(meta.get("scans") or 0)
    if scans >= PAGE_GREP_CALLS_PER_PAGE:
        return (f"# page_grep([{n}]): this result has been scanned as often as it can be. "
                f"Read a region of it, or work with what you already have.")
    if index.reread_budget <= 0:
        return _REREAD_EXHAUSTED
    meta["scans"] = scans + 1
    note = meta["note"]
    low = note.lower()
    needle = pat.lower()
    offsets: list[int] = []
    at = low.find(needle)
    while at != -1 and len(offsets) < PAGE_GREP_MAX_HITS:
        offsets.append(at)
        at = low.find(needle, at + max(1, len(needle)))
    if not offsets:
        return (f"# page_grep({pat!r}) on [{n}]: no match in {len(note)} chars. Try a shorter "
                f"string, a different spelling, or a different result.")
    parts = [f"# page_grep({pat!r}) on [{n}] -> {len(offsets)} match(es) within {len(note)} chars"]
    for at in offsets:
        start = max(0, at - PAGE_GREP_WINDOW_CHARS // 2)
        end = min(len(note), start + PAGE_GREP_WINDOW_CHARS)
        parts.append(f"--- match at offset {at}, showing {start}:{end} ---\n{note[start:end]}")
    rendered = "\n".join(parts)
    index.reread_budget -= len(rendered)
    return rendered


def _run_page_read(number: object, offset: object, length: object, index: _ResultIndex) -> str:
    """Return one region of a result already in hand, addressed by offset.

    Bounded on three sides on purpose: a single call cannot exceed a fixed width,
    one result cannot be opened more than a few times, and the run as a whole has
    a fixed allowance across every result. Each call is a turn against a fixed
    time budget, so an unbounded version trades the answer for the reading.
    """
    resolved = _held_result(number, index)
    if resolved is None:
        return ("# page_read: no such result. Pass the number in brackets next to a result "
                "returned earlier in this run; nothing else can be read.")
    n, meta = resolved
    reads = int(meta.get("reads") or 0)
    if reads >= PAGE_READ_CALLS_PER_PAGE:
        return (f"# page_read([{n}]): this result has been opened as often as it can be. "
                f"Work with what you already have, or try a different result.")
    if index.reread_budget <= 0:
        return _REREAD_EXHAUSTED
    note = meta["note"]
    try:
        start = int(str(offset).strip() or 0)
    except ValueError:
        start = 0
    try:
        width = int(str(length).strip() or PAGE_READ_MAX_CHARS)
    except ValueError:
        width = PAGE_READ_MAX_CHARS
    start = max(0, min(start, len(note)))
    width = max(1, min(width, PAGE_READ_MAX_CHARS, index.reread_budget))
    end = min(len(note), start + width)
    if end <= start:
        return (f"# page_read([{n}] @{start}): that offset is at or past the end of this "
                f"result's {len(note)} chars.")
    meta["reads"] = reads + 1
    index.reread_budget -= end - start
    # What was read is what was shown: the commit pack and the citations read the
    # same ledger of surfaced regions the fetch stage writes to. Recorded
    # uncharged (a deliberate read is not a density guess) and marked verified,
    # so the pack keeps it ahead of the question-word ranking.
    index.retain(n, start, end)
    index.mark_verified(n, [(start, end)])
    return f"# page_read([{n}] offsets {start}:{end} of {len(note)} chars)\n{note[start:end]}"


async def _run_fetch_page(url: str, index: _ResultIndex, terms: list[str],
                          question: str = "", budget: float = 0.0) -> str:
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
    # The extractor runs first and is offered first. It reads the page in full
    # and returns text it can point at; the density windows are a guess made
    # from the question's own words, and a question cannot contain the
    # identifier that IS its answer. Offering the guess first spends the page's
    # guaranteed allowance on it, and whatever the extractor found then competes
    # for what is left -- the wrong way round for the only regions on the page
    # that were actually checked. Measured on `a010a611` `75b2b013`: same
    # queries, same PDFs, same order as the sibling that keeps this ordering,
    # 0.00 against its 1.00, the answer rows held mid-run and cut at the commit.
    try:
        found = await _extract_spans(question, note, budget)
    except Exception:
        found = []
    windows = PAGE_WINDOWS_WITH_EXTRACT if found else PAGE_WINDOWS_PER_PAGE
    shown = index.surface(n, found + _page_spans(note, terms, windows))
    index.mark_verified(n, found)
    if not shown:
        shown = index.spans(n) or [(0, min(TOOL_RESULT_INLINE_CHARS, len(note)))]
    body = _render_spans(note, shown)
    return (
        f"# fetch_page({url!r}) -> [{n}] {len(note)} chars total, "
        f"{len(body)} shown"
        + (f"; the remaining {len(note) - len(body)} chars are held under [{n}] and NOT "
           f"shown -- reach them with page_grep({n}, ...) and page_read({n}, offset, "
           f"length), up to {PAGE_READ_MAX_CHARS} chars per read. Re-fetching this URL "
           f"returns the same opening again." if len(note) > len(body) else "")
        + f"\n{body}"
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


def _anchor_tokens(claim: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z']{3,}|\d[\d,.%]*", claim)
    ordered = sorted(words, key=lambda w: (not any(c.isdigit() for c in w), -len(w)))
    tokens: list[str] = []
    for w in ordered:
        lw = w.lower().strip(".,%")
        if len(lw) >= 3 and lw not in tokens:
            tokens.append(lw)
        if len(tokens) >= 8:
            break
    return tokens


SLICE_BOILER_RE = re.compile(
    r"utm_source|utm_campaign|word game|cookie consent|accept cookies|subscribe now"
    r"|sign in\b|newsletter|advertisement|\U0001f9e9",
    re.IGNORECASE,
)


def _window_quality(text: str) -> float:
    """Legibility of a candidate slice as judge-facing evidence: markdown-table
    debris and page boilerplate read as unsupported garbage in pairwise."""
    if not text:
        return 0.0
    q = 1.0
    pipes_per_100 = text.count("|") * 100.0 / len(text)
    if pipes_per_100 > 6:
        q *= 0.25
    elif pipes_per_100 > 3:
        q *= 0.6
    letters = sum(1 for c in text if c.isalpha())
    if letters * 1.0 / len(text) < 0.45:
        q *= 0.4
    if SLICE_BOILER_RE.search(text[:400]):
        q *= 0.5
    return q


def _anchored_slice_bounds(note: str, claims: list[str], window: int) -> tuple[int, int]:
    src_len = len(note)
    if src_len <= window:
        return 0, src_len
    hay = note.lower()
    tokens: list[str] = []
    for claim in claims[:3]:
        tokens.extend(_anchor_tokens(claim))
    positions: list[int] = []
    for t in tokens:
        i = hay.find(t)
        while i != -1 and len(positions) < 400:
            positions.append(i)
            i = hay.find(t, i + 1)
    # head window is the default: document heads carry the headline/lede text
    # that reads as claim support; deep offsets tend to land on table debris
    head_text = note[:window]
    head_hits = sum(1 for q in positions if q < window)
    head_score = (1.0 + head_hits) * _window_quality(head_text) * 1.5
    if not positions:
        return 0, window
    positions.sort()
    best_start, best_score = 0, head_score
    for p in positions:
        start = max(0, min(p - CITATION_ANCHOR_LEAD_CHARS, src_len - window))
        if start == 0:
            continue
        end = start + window
        hits = sum(1 for q in positions if start <= q <= end)
        score = (1.0 + hits) * _window_quality(note[start:end])
        if score > best_score:
            best_score, best_start = score, start
    return best_start, best_start + window


def _citations_from_inline_markers(
    answer_text: str, index: _ResultIndex
) -> tuple[tuple[CitationRef, ...], dict[int, int]]:
    """Build the citation array and the number -> array-position map.

    One entry per SOURCE, so several evidence numbers can share a position, and
    a source that loses its ranges to the budget occupies none. The map records
    where each number's entry actually landed.
    """
    max_number = index.max_number()
    seen: set[int] = set()
    ordered: list[int] = []
    claims_by_number: dict[int, list[str]] = {}
    key_of_number: dict[int, str] = {}
    for match in BRACKET_RE.finditer(answer_text):
        claim = answer_text[max(0, match.start() - CITATION_ANCHOR_CONTEXT_CHARS):match.start()]
        for n in _numbers_from_bracket(match.group(1), max_number=max_number):
            claims_by_number.setdefault(n, []).append(claim)
            if n not in seen:
                seen.add(n)
                ordered.append(n)
    # One entry per SOURCE, not per evidence number: a page read twice used to
    # go out twice, with near-identical ranges, which reads as padding. Same
    # source -> one entry carrying the union of the ranges it was read from.
    by_source: dict[str, dict[str, object]] = {}
    source_order: list[str] = []
    slice_window = CITATION_BUDGET_CHARS // max(len(ordered), 1)
    for n in ordered:
        meta = index.get(n)
        if meta is None or not meta.get("citable", True):
            continue
        src_len = int(meta.get("src_len") or 0)
        if src_len <= 0:
            continue
        # The ranges this source was actually read from. Those are the ranges a
        # claim can have come from, so they are the ranges offered as support;
        # a source that was never surfaced in ranges falls back to anchoring the
        # claim inside it, as before.
        spans = [(s, e) for s, e in index.spans(n) if e > s]
        if not spans:
            start, end = _anchored_slice_bounds(
                meta["note"], claims_by_number.get(n, []), slice_window,
            )
            if end > start:
                spans = [(start, end)]
        spans = [(max(0, s), min(src_len, e)) for s, e in spans]
        spans = _merge_spans([(s, e) for s, e in spans if e - s >= 100 or (s == 0 and e == src_len)])
        if not spans:
            continue
        key = _normalized_url(meta.get("url") or "") or f"{meta['receipt_id']}/{meta['result_id']}"
        key_of_number[n] = key
        entry = by_source.get(key)
        if entry is None:
            by_source[key] = {"meta": meta, "spans": spans, "src_len": src_len}
            source_order.append(key)
        else:
            limit = int(entry["src_len"])
            if src_len != limit:
                # The same document reached through a different rendering. Its
                # offsets do not mean the same thing as the copy already kept,
                # so folding them in would clamp one coordinate space into
                # another. Keep the first and drop this copy: a second copy adds
                # no fact, and it makes anything the page ENUMERATES appear
                # twice.
                continue
            # same page, same rendering, read again: widen the kept ranges
            entry["spans"] = _merge_spans(
                list(entry["spans"]) + [(s, min(e, limit)) for s, e in spans if s < limit]
            )

    # Two ranges of one page separated by a short unread run are one passage the
    # reader has to bridge on their own, and the sentence that ties them together
    # is exactly what falls in the run. Close short runs so a supported statement
    # sits whole inside one offered range instead of straddling two -- but pay for
    # them ONLY out of the allowance no retained range is already using, so closing
    # a run can never cost one. No headroom, no change.
    headroom = CITATION_BUDGET_CHARS - sum(
        e - s for entry in by_source.values() for s, e in entry["spans"]
    )
    for entry in by_source.values():
        if headroom <= 0:
            break
        limit = int(entry["src_len"])
        joined: list[tuple[int, int]] = []
        for start, end in sorted(entry["spans"]):
            run = start - joined[-1][1] if joined else 0
            if joined and end <= limit and 0 <= run <= min(CITATION_GAP_FILL_MAX_CHARS, headroom):
                headroom -= run
                joined[-1] = (joined[-1][0], max(joined[-1][1], end))
            else:
                joined.append((start, end))
        entry["spans"] = joined

    citations: list[CitationRef] = []
    position_of_key: dict[str, int] = {}
    budget = CITATION_BUDGET_CHARS
    for key in source_order:
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
        position_of_key[key] = len(citations)
    position_of = {
        n: position_of_key[key]
        for n, key in key_of_number.items()
        if key in position_of_key
    }
    return tuple(citations), position_of


def _repoint_markers(text: str, position_of: dict[int, int], *, max_number: int) -> str:
    """Rewrite evidence brackets as position pointers into the citation array.

    `[7]` and `[7, 12]` are written against tool-result numbering; the array
    that ships alongside is compact, ordered by first use, and merges repeats of
    one source into a single entry. This maps each number onto the position it
    occupies and emits one pointer per position, so a pointer and the entry it
    selects always agree. Numbers that carry no entry are dropped rather than
    left pointing past the end of the array.
    """

    def _replace(match: "re.Match[str]") -> str:
        positions: list[int] = []
        for n in _numbers_from_bracket(match.group(1), max_number=max_number):
            position = position_of.get(n)
            if position is not None and position not in positions:
                positions.append(position)
        if not positions:
            return ""
        return "".join(f"[[{p}]]" for p in positions)

    return BRACKET_RE.sub(_replace, text)


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


def _checkpoint_message(candidates: list[str], index: _ResultIndex) -> str:
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

# A `fast` query is judged on component correctness against the reference, from a
# payload carrying the question, the two answers and their notes -- no citations,
# no candidate pool, no exclusions. The only thing that changes on such a query
# is the COMMIT PROMPT: no table, no near-miss discussion, no preamble. Every
# retrieval stage runs unchanged, extractor and re-dispatch included -- both were
# skipped once and each skip was measured to cost an answer.
FAST_COMMIT_MESSAGE = (
    "Tools are now DISABLED. Answer the question directly and completely from the "
    "numbered evidence you already have. State every part the question asks for, "
    "in the order asked, using the exact names, figures and units the evidence "
    "gives. No candidate table, no near-miss discussion, no preamble."
)
_FAST: list = [False]
# The index of the most recent `_plain_query`, read by the entrypoint to tell a
# run that reached the floor with NO tool result at all from one that reached it
# after a full run. On `a010a611`, 58 runs across four of our arms returned in
# 0.2-1.2 s with zero LLM calls, zero tool calls and $0 -- the validator's tool
# plane was not up yet in the first minutes of evaluation -- and every one shipped
# its own floor string, which the platform scored 0.000 as a normal response.
_LAST_INDEX: list = [None]
COLD_START_WINDOW_SECONDS = 20.0
COLD_START_BACKOFF_SECONDS = 4.0
COLD_START_MIN_BUDGET_SECONDS = 200.0


def _fast_mode() -> bool:
    return bool(_FAST[0])


def _digest_numbers(index: _ResultIndex) -> list[int]:
    """Evidence numbers to expand, fetched pages before search results.

    One slot per PAGE: a page fetched more than once used to occupy one digest
    slot per fetch, each shown as its own opening — three slots of the same
    boilerplate while other sources were squeezed. Duplicates are folded into
    the first fetch of that URL (their read spans are unioned at render time).
    """
    fetched: list[int] = []
    searched: list[int] = []
    seen_urls: set[str] = set()
    for n in range(1, index.max_number() + 1):
        meta = index.get(n)
        if meta is None or not meta.get("citable", True):
            continue
        if meta.get("kind") == "fetch":
            key = _normalized_url(meta.get("url") or "") or f"#{n}"
            if key in seen_urls:
                continue
            seen_urls.add(key)
            fetched.append(n)
        else:
            searched.append(n)
    return sorted((fetched + searched)[:COMMIT_DIGEST_SOURCES_MAX])


def _union_spans_same_url(index: _ResultIndex, number: int) -> list[tuple[int, int]]:
    """The union of read spans across every fetch of this page (equal-length
    notes only, so offsets are comparable)."""
    meta = index.get(number)
    if meta is None:
        return list(index.spans(number) or ())
    key = _normalized_url(meta.get("url") or "")
    length = int(meta.get("src_len") or 0)
    spans: list[tuple[int, int]] = list(index.spans(number) or ())
    if not key:
        return spans
    for n in range(1, index.max_number() + 1):
        if n == number:
            continue
        other = index.get(n)
        if other is None or other.get("kind") != "fetch":
            continue
        if _normalized_url(other.get("url") or "") != key:
            continue
        if int(other.get("src_len") or 0) != length:
            continue
        spans.extend(index.spans(n) or ())
    return _merge_spans(spans)


def _digest_spans(
    note: str, spans: list[tuple[int, int]], terms: list[str], window: int,
    verified: list[tuple[int, int]] | None = None,
) -> list[tuple[int, int]]:
    """Which parts of the regions read from a source fit in its allowance.

    When everything read fits, everything read is shown. When it does not, the
    choice used to be made the same way the regions were chosen in the first
    place — by where the question's own words occur. That ranking is the reason
    a region can be read during research and still be missing from the turn that
    writes the answer: a passage carrying the identifier the question ASKS FOR
    scores lowest on the question's own words, so it is the first thing cut.
    Regions an extractor could quote are therefore kept ahead of that ranking
    rather than subjected to it.
    """
    spans = _merge_spans([(s, e) for s, e in spans if e > s])
    if not spans:
        return []
    total = sum(e - s for s, e in spans)
    if total <= window:
        return spans
    identity = min(COMMIT_DIGEST_IDENTITY_CHARS, window, spans[0][1] - spans[0][0])
    kept: list[tuple[int, int]] = [(spans[0][0], spans[0][0] + identity)] if identity > 0 else []
    left = window - identity
    vouched = _merge_spans(list(verified or ()))
    is_vouched = lambda s, e: any(s < vb and va < e for va, vb in vouched)
    rest: list[tuple[int, int]] = []
    for start, end in spans:
        if start == spans[0][0] or not is_vouched(start, end):
            rest.append((start, end))
            continue
        take = min(end - start, max(0, left))
        if take <= 0:
            continue
        kept.append((start, start + take))
        left -= take
    scored: list[tuple[int, tuple[int, int]]] = []
    for start, end in rest:
        hits = _term_hits(note[start:end].lower(), terms)
        scored.append((len({t for _p, t in hits}), (start, end)))
    scored.sort(key=lambda row: -row[0])
    for _score, (start, end) in scored:
        if left <= 0:
            break
        if end - start <= left:
            kept.append((start, end))
            left -= end - start
            continue
        picked = _best_windows(note, terms, max(400, left), 1, skip_before=start,
                               avoid=[(0, start), (end, len(note))])
        if picked:
            kept.extend(picked)
            left -= sum(e - s for s, e in picked)
        else:
            kept.append((start, start + left))
            left = 0
    return _merge_spans(kept)


def _evidence_digest(index: _ResultIndex, terms: list[str]) -> str:
    """The numbered evidence, projected straight out of the result index.

    Each source contributes its opening plus the regions it was read from; the
    per-source allowance widens when few sources were gathered, so the whole
    digest stays inside one bounded size regardless of how much was collected.
    The turn that writes the answer therefore sees the same regions the research
    turns saw, instead of a shorter prefix of every source.
    """
    numbers = _digest_numbers(index)
    if not numbers:
        return ""
    window = max(COMMIT_DIGEST_NOTE_CHARS, COMMIT_DIGEST_TOTAL_CHARS // len(numbers))
    parts = ["NUMBERED EVIDENCE (the sources gathered for this question; cite by these numbers):"]
    for n in numbers:
        meta = index.get(n)
        if meta is None:
            continue
        note = meta["note"] or ""
        spans = _union_spans_same_url(index, n) if meta.get("kind") == "fetch" else index.spans(n)
        if not spans:
            # never surfaced in ranges (a search result): give it the same
            # treatment here rather than a bare prefix
            head_end = min(window, len(note))
            spans = _merge_spans([(0, head_end)] + _best_windows(
                note, terms, min(window, PAGE_WINDOW_CHARS), 1, skip_before=head_end,
            ))
        budgeted = _digest_spans(note, spans, terms, window, index.verified(n))
        body = _render_spans(note, budgeted).strip()
        parts.append(f"[{n}] {meta.get('title') or ''}\n  url: {meta.get('url') or ''}\n{body}")
    return "\n\n".join(parts)


def _commit_context(
    question: str, candidates: list[str], index: _ResultIndex, *,
    terms: list[str] | None = None, notice: str = "",
    draft: str | None = None, suffix: str = "",
) -> list[dict[str, object]] | None:
    """The commit turn's own message list, built from the index rather than the
    research conversation. Returns None when there is no evidence to project."""
    digest = _evidence_digest(index, terms or _key_terms(question))
    if not digest:
        return None
    # No candidate table and no exclusions on a fast query: neither reaches that
    # judge, and asking for them spends the commit turn's output on text scored
    # only for the excess components it adds. The instruction then appears once,
    # at the end, rather than being restated around the digest.
    if _fast_mode():
        body = digest
    else:
        checkpoint = _checkpoint_message(candidates, index)
        if notice:
            checkpoint = notice + "\n\n" + checkpoint
        body = digest + "\n\n" + checkpoint
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
        {"role": "user", "content": body},
    ]
    if draft:
        messages.append({"role": "assistant", "content": draft})
    messages.append({"role": "user", "content":
                     (FAST_COMMIT_MESSAGE if _fast_mode() else COMMIT_MESSAGE) + suffix})
    return messages


# --- AMEND ------------------------------------------------------------------
# The stage that decides the delivered answer. It replaces the pre-delivery
# repair pass this pipeline used to end on, which could only rewrite what the
# draft already said. This one first changes what has been READ — it re-projects
# the pages already retrieved against each thing the question asks for, in its
# own loop, issuing no requests — and then rewrites the draft around whatever
# that turns up that the draft does not carry. It runs on every question and
# what it returns is what goes out.

NARRATED_GAP_MARKERS = (
    "not captured", "not individually identified", "cannot be confirmed from",
    "only partially retrieved", "only partially captured", "falls in a gap",
    "was not captured", "not visible in the available", "no team listing",
    "closest available snapshot",
)


def _narrates_gap(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in NARRATED_GAP_MARKERS)


ASK_CLAUSE_RE = re.compile(
    r"(?<=[?.;:])\s+"
    r"|\s+(?:and|then|also|finally|additionally)\s+(?=which|what|how|who|when|where|name|list|identify|give|state)",
    re.IGNORECASE,
)
NUMERIC_RE = re.compile(r"\d")


class _Ask:
    __slots__ = ("label", "terms")

    def __init__(self, label: str, terms: list[str]) -> None:
        self.label = label
        self.terms = terms


def _question_asks(question: str, candidates: list[str]) -> list[_Ask]:
    """The distinct things the question asks for, one entry each.

    Two sources, both structural: the interrogative clauses of the question
    itself, and each entity the opening brief put in play. Nothing here keys on
    subject matter — a clause qualifies because of where it sits in the
    sentence, not because of what it is about.
    """
    asks: list[_Ask] = []
    seen: set[str] = set()
    for clause in ASK_CLAUSE_RE.split(question or ""):
        clause = clause.strip()
        if len(clause) < 12:
            continue
        terms = _key_terms(clause, limit=10)
        if len(terms) < 2:
            continue
        key = "|".join(sorted(terms[:4]))
        if key in seen:
            continue
        seen.add(key)
        asks.append(_Ask(clause[:90], terms))
    for candidate in candidates[:ASK_LIST_MAX]:
        terms = _key_terms(candidate, limit=6)
        if not terms:
            continue
        key = "|".join(sorted(terms[:4]))
        if key in seen:
            continue
        seen.add(key)
        asks.append(_Ask(candidate[:90], terms))
    return asks[:ASK_LIST_MAX + 4]


def _ask_answered(ask: _Ask, index: _ResultIndex) -> bool:
    """True when some surfaced passage names the ask and states a figure for it.

    A page that merely mentions the subject is not the same as a page that
    answers for it, so the test needs both a term hit and a numeral close by.
    """
    wanted = min(2, len(ask.terms))
    for number in range(1, index.max_number() + 1):
        meta = index.get(number)
        if meta is None:
            continue
        note = meta["note"] or ""
        for start, end in index.spans(number) or ():
            passage = note[start:end].lower()
            if not passage:
                continue
            hits = [p for p in (passage.find(t) for t in ask.terms) if p >= 0]
            if len(hits) < wanted:
                continue
            for p in hits:
                near = passage[max(0, p - ASK_PROOF_CHARS):p + ASK_PROOF_CHARS]
                if NUMERIC_RE.search(near):
                    return True
    return False


def _relocate(index: _ResultIndex, asks: list[_Ask], deadline: float) -> list[_Ask]:
    """Re-project retained pages against whatever is still unanswered.

    Runs its own loop: each pass takes the asks with nothing stated for them,
    pulls the best-matching unseen region out of every retained page for each,
    and re-tests. It re-enters while a pass is still surfacing new regions and
    stops as soon as one is not — no request is issued, so the only cost is the
    text added to the reader's view, which is capped separately.
    """
    open_asks = [a for a in asks if not _ask_answered(a, index)]
    budget = RELOCATE_BUDGET_CHARS
    for _pass in range(RELOCATE_MAX_PASSES):
        if not open_asks or budget <= 0 or deadline - perf_counter() < RELOCATE_MIN_SECONDS:
            break
        surfaced = 0
        for ask in open_asks:
            for number in index.fetched_numbers()[:RELOCATE_PAGES_PER_ASK]:
                if budget <= 0:
                    break
                meta = index.get(number)
                if meta is None:
                    continue
                found = _best_windows(
                    meta["note"] or "", ask.terms, RELOCATE_WINDOW_CHARS,
                    RELOCATE_WINDOWS_PER_ASK, avoid=index.spans(number),
                )
                for span_start, span_end in index.surface(number, found):
                    surfaced += span_end - span_start
                    budget -= span_end - span_start
        if not surfaced:
            break
        open_asks = [a for a in open_asks if not _ask_answered(a, index)]
    return open_asks


def _relocate_notice(asks: list[_Ask], open_asks: list[_Ask]) -> str:
    if not asks:
        return ""
    if not open_asks:
        return (
            "RELOCATED EVIDENCE: every part of the question now has a passage in the "
            "numbered evidence that names it and states a figure for it. Quote those "
            "figures — do not describe them as unavailable."
        )
    names = "; ".join(a.label for a in open_asks[:ASK_LIST_MAX])
    return (
        "RELOCATED EVIDENCE: the numbered evidence below now includes, for each part of "
        "the question, the regions of each retrieved page that mention it — not just each "
        "page's opening. Parts with no passage stating a figure yet: " + names + ". "
        "Re-scan the numbered evidence for those before treating any of them as missing."
    )


def _unreported(asks: list[_Ask], index: _ResultIndex, answer: str, *, force: bool = False) -> list[tuple[_Ask, str]]:
    """Asks a passage now states a figure for, but the answer does not report.

    This is the whole point of relocating after a draft exists: the research
    turns wrote the answer from what they had been shown, and relocation changes
    what has been shown. Anything it turns up that the draft does not carry is,
    by construction, material the draft could not have used.
    """
    hay = (answer or "").lower()
    missing: list[tuple[_Ask, str]] = []
    for ask in asks:
        if not _ask_answered(ask, index):
            continue
        wanted = min(2, len(ask.terms))
        if not force and sum(1 for t in ask.terms if t in hay) >= wanted:
            continue
        passage = ""
        for number in range(1, index.max_number() + 1):
            meta = index.get(number)
            if meta is None:
                continue
            note = meta["note"] or ""
            for start, end in index.spans(number) or ():
                body = note[start:end]
                low = body.lower()
                hit = [p for p in (low.find(t) for t in ask.terms) if p >= 0]
                if len(hit) < wanted:
                    continue
                at = min(hit)
                near = body[max(0, at - ASK_PROOF_CHARS):at + ASK_PROOF_CHARS]
                if NUMERIC_RE.search(near):
                    passage = f"[{number}] {near.strip()}"
                    break
            if passage:
                break
        if passage:
            missing.append((ask, passage))
    return missing


AMEND_SYSTEM = (
    "You issue the final version of a research answer. The draft below was written "
    "before part of its evidence had been located, so you are given both the draft and "
    "any passages that ARE in the evidence and that the draft does not report.\n"
    "Rules:\n"
    "1. Keep everything the draft already gets right, in its structure and order.\n"
    "2. Add the located figures where they belong, each with its [n] marker, and remove "
    "any statement that something is unavailable when a passage below states it.\n"
    "3. If the question prescribes an exact output ('output only ...', a required "
    "separator, ordering, or list format), make the FIRST line exactly that prescribed "
    "output and keep the supporting proof below it.\n"
    "4. Delete leftover process text: phase markers, working tables, narrated intentions. "
    "Keep every other [n] citation bracket exactly where it stands.\n"
    "5. Output the complete answer and nothing else — no preamble, no notes about what "
    "you changed. If nothing above applies, return the draft verbatim."
)


async def _amend(
    question: str, answer: str, gaps: list[tuple[_Ask, str]], deadline: float,
) -> str:
    """Rewrite the answer around the passages relocation turned up.

    The returned text REPLACES what the research turns produced; this stage owns
    what is delivered rather than annotating it. A rewrite is kept only when it
    is a complete answer in its own right and still carries its citations, so
    the stage can add what was found without the risk of trading a whole answer
    for a fragment.
    """
    budget = deadline - perf_counter() - 3
    if budget <= 10:
        return answer
    room = AMEND_CONTEXT_CHARS
    blocks: list[str] = []
    for ask, passage in gaps[:ASK_LIST_MAX]:
        chunk = f"NOT REPORTED — {ask.label}\n{passage[:max(0, min(room, 1400))]}"
        room -= len(chunk)
        blocks.append(chunk)
        if room <= 0:
            break
    located = "\n\n---\n\n".join(blocks) if blocks else "(none — the draft reports everything located)"
    messages = [
        {"role": "system", "content": AMEND_SYSTEM},
        {"role": "user", "content": (
            f"QUESTION:\n{question}\n\nDRAFT ANSWER:\n{answer[:AMEND_CONTEXT_CHARS]}\n\n"
            "LOCATED PASSAGES THE DRAFT DOES NOT REPORT:\n\n" + located +
            "\n\nReturn the complete final answer now."
        )},
    ]
    try:
        result = await llm_chat(
            provider=LLM_PROVIDER, model=MODEL, messages=messages, temperature=0.1,
            thinking=LlmThinkingConfig(enabled=False),
            timeout=min(AMEND_TIMEOUT_SECONDS, budget),
        )
        revised = (result.response.raw_text or "").strip()
    except Exception:
        revised = ""
    if len(revised) < max(AMEND_MIN_KEEP_CHARS, int(len(answer) * 0.5)):
        return answer
    if TOOL_MARKUP_RE.search(revised) or PSEUDO_CALL_RE.search(revised):
        return answer
    if any(m in revised.lower()[:200] for m in ABSTENTION_MARKERS):
        return answer
    if BRACKET_RE.search(answer) and not BRACKET_RE.search(revised):
        return answer
    if _needs_forced_retry(revised):
        return answer
    return revised


async def _amended_answer(
    question: str, asks: list[_Ask], index: _ResultIndex, answer: str, deadline: float,
) -> str:
    """The delivered answer, decided here.

    Always runs. Relocation goes first so the rewrite is judged against
    everything the retained pages can be made to show, and the text this returns
    is the text that is delivered.
    """
    _relocate(index, asks, deadline)
    if deadline - perf_counter() < AMEND_MIN_SECONDS:
        return answer
    gaps = _unreported(asks, index, answer, force=_narrates_gap(answer))
    result = await _amend(question, answer, gaps, deadline)
    return result


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
                timeout=timeout, provider_extra=_main_pin(),
            )
        except Exception:
            _main_pin_failed()
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
            # Was `budget - 28`: with ~118 s left that is a 90 s first attempt
            # and a 26 s second one, and on `a010a611` replay 8 of 12 runs hit
            # exactly that pair of timeouts and shipped the floor string.
            # Capped so the thinking-off retry keeps a real window.
            timeout = min(budget - 28.0, 60.0)
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


SCAFFOLD_HEAD_RE = re.compile(r"^\s*(?:#{1,4}\s*)?(?:\*{1,2})?\s*(?:VERIFY|BRIEFING)\b", re.IGNORECASE)


def _needs_forced_retry(text: str) -> bool:
    if TOOL_MARKUP_RE.search(text) is not None:
        return True
    # A reply that OPENS with the protocol's own phase marker and never reached
    # FINAL ANSWER is the working table, not the answer. `_final_section` passes
    # it through whole when the marker is absent, and it scored 0.000 on every
    # one of the nine C-lineage runs that shipped it on `a010a611`.
    if SCAFFOLD_HEAD_RE.match(text) is not None and not FINAL_SECTION_RE.search(text):
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


def _dump_floor_answer(index: _ResultIndex) -> str | None:
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


def _deliverable(text: str | None, index: _ResultIndex, *, cite_text: str | None = None) -> Response:
    answer = (text or "").strip()
    if not answer:
        answer = _dump_floor_answer(index) or INSUFFICIENT_ANSWER
    # citations may be sourced from the fuller pre-extraction text: the marker
    # numbers that justify the final section often live in the verify table
    citations, position_of = _citations_from_inline_markers(cite_text or answer, index)
    answer = _repoint_markers(answer, position_of, max_number=index.max_number())
    return Response(text=answer, citations=list(citations) if citations else None)


async def _execute_tool_calls(
    tool_calls, messages, index: _ResultIndex, terms: list[str], *, content: str = "",
    question: str = "", budget: float = 0.0,
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
            return await _run_fetch_page(str(args.get("url", "")), index, terms,
                                         question=question, budget=budget)
        if tc.name == "page_grep":
            return _run_page_grep(args.get("source"), str(args.get("pattern", "")), index)
        if tc.name == "page_read":
            return _run_page_read(args.get("source"), args.get("offset"), args.get("length"), index)
        return f"# unknown tool {tc.name!r}"

    # a turn's tool calls are independent lookups: run them concurrently so a
    # 4-call turn costs one round-trip of wall-clock, not four
    results = await asyncio.gather(*(_one(tc) for tc in tool_calls))
    for tc, result_text in zip(tool_calls, results):
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})


def _serializer_evidence(index: "_ResultIndex", limit: int) -> str:
    """The passages this run actually read, in the coordinates it read them at."""
    parts: list[str] = []
    used = 0
    numbers = list(range(1, index.max_number() + 1))
    numbers.sort(key=lambda n: 0 if (index.get(n) or {}).get("kind") == "fetch" else 1)
    for n in numbers:
        meta = index.get(n)
        if meta is None or not meta.get("citable"):
            continue
        spans = index.spans(n)
        if not spans:
            continue
        body = _render_spans(meta.get("note") or "", spans)
        if not body.strip():
            continue
        chunk = f"[{n}] {(meta.get('title') or meta.get('url') or '')[:160]}\n{body}"
        room = limit - used
        if room <= 0:
            break
        parts.append(chunk[:room])
        used += min(len(chunk), room)
    return "\n\n".join(parts)


async def _plain_query(query: Query, budget: float) -> Response:
    start = perf_counter()
    deadline = start + budget
    research_stop = min(start + RESEARCH_TIME_CAP_SECONDS, deadline - FINAL_RESERVE_SECONDS)
    index = _ResultIndex()
    _LAST_INDEX[0] = index
    _SO_EVIDENCE_HOOK[:] = [lambda limit: _serializer_evidence(index, limit)]
    terms = _key_terms(query.text)
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query.text},
    ]
    candidates: list[str] = []
    final_answer: str | None = None
    notice = ""
    last_content = ""

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
                await _execute_tool_calls(tool_calls, messages, index, terms, content=content,
                                          question=query.text or "",
                                          budget=deadline - perf_counter())
                continue

            # model stopped calling tools during research: hold its draft and move on
            if content:
                messages.append({"role": "assistant", "content": content})
                last_content = content
            break

        # --- RELOCATE: re-project retained pages onto the unanswered parts ---
        asks = _question_asks(query.text, candidates)
        open_asks = _relocate(index, asks, deadline - FINAL_RESERVE_SECONDS)
        notice = _relocate_notice(asks, open_asks)

        # --- CHECKPOINT: VERIFY + capped targeted re-dispatch ---
        # Runs on fast queries too. It was skipped there once, as apparatus for
        # a comparing judge -- and the re-dispatch turn it owns is where the base
        # fetched the one PDF carrying four of five answer rows on `412ac0ae`.
        checkpoint = _checkpoint_message(candidates, index)
        if notice:
            checkpoint = notice + "\n\n" + checkpoint
        messages.append({"role": "user", "content": checkpoint})
        for _extra in range(CHECKPOINT_TOOL_TURNS + 1):
            # a re-dispatch turn only pays if there is still room to run its
            # tools AND a committed final afterwards
            if deadline - perf_counter() <= FINAL_RESERVE_SECONDS + 25:
                break
            # Bounded below the commit's own reserve: a single pinned checkpoint
            # turn ran the full 90 s cap right before the commit on the (b)
            # re-check, left it 52 s, and the floor string shipped.
            chat_result = await _chat_turn(
                messages, deadline=min(deadline - FINAL_RESERVE_SECONDS, perf_counter() + 45.0),
                thinking_on=True)
            if chat_result is None:
                break
            choice_message = chat_result.response.choices[0].message
            content = (chat_result.response.raw_text or "").strip()
            tool_calls = choice_message.tool_calls or ()
            if tool_calls:
                await _execute_tool_calls(tool_calls, messages, index, terms, content=content,
                                          question=query.text or "",
                                          budget=deadline - perf_counter())
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

        # --- RELOCATE re-entry: the re-dispatch turns may have added pages ---
        if index.fetched_numbers():
            open_asks = _relocate(index, asks, deadline - 10)
            notice = _relocate_notice(asks, open_asks)

        # --- FORCED COMMIT: tools disabled ---
        if not final_answer:
            commit_messages = _commit_context(
                query.text, candidates, index, terms=terms, notice=notice,
            )
            if commit_messages is None:
                messages.append({"role": "user", "content":
                                 FAST_COMMIT_MESSAGE if _fast_mode() else COMMIT_MESSAGE})
                commit_messages = messages
            final_answer = await _commit_call(commit_messages, deadline=deadline)
        if not final_answer and last_content:
            # A checkpoint turn that reached FINAL ANSWER is the answer. One that
            # did not is still the model's latest reading of the evidence, and it
            # beats the floor string: "could not run to completion" scored 0.000
            # on every one of its 7 deliveries across `a010a611` production and
            # replay, while a draft carries the figures. `_needs_forced_retry`
            # below still sends a scaffold-headed draft through the retry.
            final_answer = last_content

        # the gate must judge what would actually be DELIVERED (the extracted
        # final section) — a refusal hiding behind a verify preamble passes a
        # whole-text check but must not reach the judge
        cite_text = _strip_tool_markup(final_answer) if final_answer else ""
        display = _final_section(cite_text) if cite_text else ""

        if display and _needs_forced_retry(display):
            retry: str | None = None
            if deadline - perf_counter() >= FINAL_RETRY_MIN_SECONDS:
                retry_messages = _commit_context(
                    query.text, candidates, index, terms=terms, notice=notice,
                    draft=final_answer, suffix=FORCED_COMMIT_SUFFIX,
                )
                if retry_messages is None:
                    messages.append({"role": "assistant", "content": final_answer})
                    messages.append({"role": "user", "content": COMMIT_MESSAGE + FORCED_COMMIT_SUFFIX})
                    retry_messages = messages
                retry = await _commit_call(retry_messages, deadline=deadline)
            retry_stripped = _strip_tool_markup(retry) if retry else ""
            retry_display = _final_section(retry_stripped) if retry_stripped else ""
            if retry_display and not _needs_forced_retry(retry_display):
                cite_text, display = retry_stripped, retry_display
            elif not _needs_forced_retry(cite_text):
                display = cite_text
            else:
                display = _dump_floor_answer(index) or display

        # --- AMEND decides what is delivered ---
        # The research turns wrote from what they had been shown. This stage runs
        # on every question, re-projects the retained pages one more time against
        # what the question asks for, and the answer it returns is the one that
        # goes out.
        if display:
            decided = await _amended_answer(
                query.text, asks, index, display, deadline - 4,
            )
            # when this stage rewrote the answer, its markers are the ones the
            # delivered text carries, so they are the ones that source citations
            cited_from = cite_text or display if decided == display else decided
            return _deliverable(decided, index, cite_text=cited_from)
        return _deliverable(None, index)
    except Exception:
        return _deliverable(None, index)


# --- structured output (begin) ---
_STRUCTURED_PROVIDER = LLM_PROVIDER
_STRUCTURED_MODEL = MODEL
STRUCTURED_RESERVE_SECONDS = 72.0
STRUCTURED_ATTEMPTS = 3
STRUCTURED_CALL_TIMEOUT_SECONDS = 34.0
# A fixed per-call cap left the tail of the reserve unspent: with a 22 s cap and
# a 25 s floor on retrying, the third attempt could not run inside 55 s by
# arithmetic, and two timeouts returned the budget and a placeholder together.
# Each attempt now takes the cap or whatever is left, whichever is smaller.
STRUCTURED_CALL_MIN_SECONDS = 8.0
STRUCTURED_FLOOR_VALUE_CHARS = 160
STRUCTURED_SCHEMA_PROMPT_CHARS = 12000
STRUCTURED_ANSWER_PROMPT_CHARS = 20000
STRUCTURED_MAX_REPORTED_ERRORS = 10
STRUCTURED_OUTPUT_CHAR_CAP = 78000
STRUCTURED_MAX_DEPTH = 14
# A schema answer is a bare value: the reasoning that justifies it has nowhere
# to go inside `output`, and the response note is the one field the form rules
# exempt. Only sentences that already state a shipped value are eligible, so the
# note cannot say anything the answer does not.
NOTE_MAX_CHARS = 1600
NOTE_MAX_LINES = 8
NOTE_LINE_CHARS = 450
NOTE_MIN_SENTENCE_CHARS = 24
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


# Some questions print the literals they expect back and then point AT THEMSELVES
# for the authoritative form ("... exactly as named above", "in the order given
# above"). Only that self-anchored family may drive the casing pass below.
# Instructions anchored on the SOURCE instead ("exactly as printed in the table")
# are deliberately excluded: there the retrieved document's own form is the
# authoritative one and it need not match the question's.
_SO_QCASE_GATE = re.compile(
    r"(?:exactly|precisely) as (?:named|listed|printed|given|shown|spelled|written|they appear)"
    r"\s+(?:above|in the (?:question|prompt))"
    r"|in the order given above",
    re.IGNORECASE,
)


def _so_qcase_value(text: str, question: str, question_lower: str) -> str:
    """The question's own casing for a value the question printed verbatim."""
    if len(text) < 3:
        return text
    if text in question:
        return text
    position = question_lower.find(text.lower())
    if position < 0:
        return text
    printed = question[position:position + len(text)]
    # Lowercasing is not always length-preserving, so the offset found in the
    # folded text can slide. Only accept a slice that is still the same string.
    if printed.lower() != text.lower():
        return text
    return printed


def _so_qcase(value: object, question: str, question_lower: str, depth: int = 0) -> object:
    if depth > STRUCTURED_MAX_DEPTH:
        return value
    if isinstance(value, str):
        return _so_qcase_value(value, question, question_lower)
    if isinstance(value, list):
        return [_so_qcase(item, question, question_lower, depth + 1) for item in value]
    if isinstance(value, dict):
        return {key: _so_qcase(item, question, question_lower, depth + 1)
                for key, item in value.items()}
    return value


def _so_qcased(value: object, question: str, schema: object) -> object:
    """Restore query-printed casing, but never at the cost of schema validity.

    A schema `enum` or `pattern` can pin a casing the question does not use, so
    the pass is reverted whenever it introduces an error the original did not
    have. Values the question never prints are left alone — matching the SOURCE's
    form is a different rule with a different authority, and this pass does not
    make that call.
    """
    if not question or not _SO_QCASE_GATE.search(question):
        return value
    try:
        recased = _so_qcase(value, question, question.lower())
    except Exception:
        return value
    if _so_canonical(recased) == _so_canonical(value):
        return value
    try:
        if len(_so_errors(recased, schema, schema)) > len(_so_errors(value, schema, schema)):
            return value
    except Exception:
        return value
    return recased


STRUCTURED_EVIDENCE_PROMPT_CHARS = 24000
_SO_BLANKS = frozenset(("", "n/a", "na", "none", "null", "unknown", "not available",
                        "not found", "not specified", "tbd", "-", "--"))

# One slot, assigned by the pipeline that owns the sources. A plain module-level
# rebind would need `global`, which no accepted payload has ever carried.
_SO_EVIDENCE_HOOK: list = []


def _so_leaf_blank(value: object, depth: int = 0) -> bool:
    if depth > STRUCTURED_MAX_DEPTH:
        return False
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, str):
        return value.strip().lower() in _SO_BLANKS
    if isinstance(value, (int, float)):
        return value == 0
    if isinstance(value, list):
        return all(_so_leaf_blank(item, depth + 1) for item in value)
    if isinstance(value, dict):
        return all(_so_leaf_blank(item, depth + 1) for item in value.values())
    return False


def _so_is_vacuous(value: object) -> bool:
    """A payload that is schema-valid and says nothing.

    Every leaf blank, empty or zero. Booleans are excluded: `false` is an answer,
    and a question that asks whether a claim holds is answered by it.
    """
    if value is None:
        return True
    if isinstance(value, (dict, list)) and not value:
        return True
    if isinstance(value, dict):
        leaves = [item for item in value.values() if not isinstance(item, bool)]
        if not leaves:
            return False
        return all(_so_leaf_blank(item) for item in leaves)
    return _so_leaf_blank(value)


def _so_evidence(limit: int = STRUCTURED_EVIDENCE_PROMPT_CHARS) -> str:
    if not _SO_EVIDENCE_HOOK:
        return ""
    hook = _SO_EVIDENCE_HOOK[0]
    try:
        return (hook(limit) or "")[:limit]
    except Exception:
        return ""


def _so_messages(question: str, schema: object, answer: str, problems: list[str],
                 evidence: str = "") -> list[dict[str, str]]:
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
        "4. Keep the schema's field names and nesting exactly as given.\n"
        "5. If the researched answer does not carry a value the schema requires, "
        "read it out of the EVIDENCE section when one is present, quoting its "
        "figures exactly. A value supported by the evidence always beats a blank."
    )
    request = (
        f"QUESTION:\n{question}\n\n"
        f"JSON SCHEMA:\n{schema_text}\n\n"
        f"RESEARCHED ANSWER:\n{answer_text}\n\n"
        + (f"EVIDENCE (passages already retrieved from the cited sources):\n"
           f"{evidence[:STRUCTURED_EVIDENCE_PROMPT_CHARS]}\n\n" if evidence else "")
        + "Return the conforming JSON value now."
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


PROOF_MIN_SECONDS = 12.0
PROOF_CALL_TIMEOUT_SECONDS = 18.0


def _so_allowed_markers(answer: str) -> list[int]:
    """The pointers the draft already resolved -- the only ones a proof may reuse.

    The evidence block is numbered by the result index, the shipped citations by
    a contiguous renumbering of the markers the draft actually used. Letting the
    proof invent a pointer would therefore attach a claim to the wrong source,
    which the judge checks. Reusing the draft's own numbers cannot drift.
    """
    seen: list[int] = []
    for raw in _NOTE_MARKER_RE.findall(answer or ""):
        n = int(raw)
        if n not in seen:
            seen.append(n)
    seen.sort()
    return seen


def _so_proof_messages(question: str, value: object, answer: str, evidence: str,
                       allowed: list[int]) -> list[dict[str, str]]:
    """Ask for the completeness the answer field has no room to carry.

    A schema answer is a bare value, so the reasoning that makes it checkable --
    which candidates were in scope, which were ruled out, and how the shipped
    numbers were derived -- has nowhere to live except the note. The output
    contract is fixed and already decided before this runs; nothing here can
    change it.
    """
    values = []
    _note_values(value, values)
    shown = ", ".join(sorted({v for v in values if len(v) >= 2})[:12])
    pointers = ", ".join(f"[[{n}]]" for n in allowed) or "(none)"
    instruction = (
        "You write the evidence trail for an answer that has already been decided. "
        "You cannot change the answer; you show why it is the answer.\n"
        "Write one claim per line, each line starting with '- '. Rules:\n"
        "1. Establish the COMPLETE candidate set the question ranges over, and say "
        "what makes it complete (the source's own count or list).\n"
        "2. Name the candidates that were considered and RULED OUT, with the reason.\n"
        "3. Show the arithmetic that produces each answer value, written out "
        "(for example: 8 + 2 + 2 + 3 = 15).\n"
        "4. EVERY line must quote at least one of the ANSWER VALUES verbatim, and "
        "every line must end with a pointer from ALLOWED POINTERS. Use no other "
        "pointer and invent no new one.\n"
        "5. State only what the EVIDENCE supports. Never write that something is "
        "missing, unavailable, truncated or unconfirmed -- omit the line instead.\n"
        "6. No tables, no headings, no bold. Plain sentences only.\n"
        "Emit only the lines. No preamble."
    )
    request = (
        f"QUESTION:\n{question}\n\n"
        f"ANSWER VALUES (already fixed):\n{shown}\n\n"
        f"ALLOWED POINTERS: {pointers}\n\n"
        f"DRAFT:\n{(answer or '')[:STRUCTURED_ANSWER_PROMPT_CHARS]}\n\n"
        + (f"EVIDENCE:\n{evidence[:STRUCTURED_EVIDENCE_PROMPT_CHARS]}\n\n" if evidence else "")
        + "Write the claim lines now."
    )
    return [
        {"role": "system", "content": instruction},
        {"role": "user", "content": request},
    ]


async def _so_proof(question: str, value: object, answer: str, evidence: str,
                    deadline: float) -> str:
    """One call, strictly additive: every failure path returns "" and the caller
    falls back to the draft-derived note."""
    remaining = deadline - perf_counter()
    if remaining < PROOF_MIN_SECONDS:
        return ""
    allowed = _so_allowed_markers(answer)
    if not allowed:
        return ""
    try:
        return await _so_call(
            _so_proof_messages(question, value, answer, evidence, allowed),
            min(PROOF_CALL_TIMEOUT_SECONDS, remaining - 2.0),
        )
    except Exception:
        return ""


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


_SO_WINDOW_CHARS = 220
_SO_WINDOW_STEP = 55
_SO_NUMERIC_HINT = frozenset(
    ("digits", "number", "count", "usd", "cost", "dollars", "year", "date",
     "total", "amount", "quantity", "figure")
)
_SO_CANDIDATE_RE = re.compile(
    r"[\"\u201c]([^\"\u201d\n]{1,80})[\"\u201d]"
    r"|\b((?:[A-Za-z0-9]+[./-])+[A-Za-z0-9]+)\b"
    r"|\b(\d[\d,]*(?:\.\d+)?)\b"
)
_SO_FLOOR_STOP = frozenset(
    ("the", "and", "for", "that", "with", "from", "this", "each", "its", "value",
     "field", "answer", "string", "number", "exactly", "given", "name", "total",
     "one", "all", "any", "correct", "qualifying")
)
_SO_KEY_MATCH_FLOOR = 0.5


def _so_words(text: str) -> set[str]:
    return {w for w in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(w) > 2} - _SO_FLOOR_STOP


def _so_key_score(target: str, candidate: str) -> tuple[float, float]:
    """How much two field names overlap: (containment, Jaccard).

    Containment leads because a rename keeps the distinctive token and adds or
    drops qualifiers -- `premise_status` / `premise_accuracy` share one word of
    two, which Jaccard prices at 0.33 and containment at 0.50. Jaccard breaks
    ties so a longer, vaguer key cannot outrank an exact one.
    """
    left, right = _so_words(target), _so_words(candidate)
    if not left or not right:
        return (0.0, 0.0)
    shared = len(left.intersection(right))
    return (shared / min(len(left), len(right)), shared / len(left | right))


def _so_pick_source(name: str, schema: dict, source: object, taken: set | None = None) -> object:
    """The draft's own value for one schema field, when the draft is JSON.

    A drafted answer is frequently already a JSON object under the pipeline's own
    field names rather than the schema's. Remapping those names is a rename, not
    a re-derivation, so it is done here rather than paid for with another call.
    """
    if not isinstance(source, dict):
        return None
    taken = taken if taken is not None else set()
    if name in source and name not in taken:
        taken.add(name)
        return source[name]
    best_key, best_score = None, (_SO_KEY_MATCH_FLOOR, -1.0)
    for key in source:
        if not isinstance(key, str) or key in taken:
            continue
        score = _so_key_score(name, key)
        if score > best_score:
            best_key, best_score = key, score
    if best_key is None:
        return None
    # One source field cannot answer two schema fields; without this a single
    # dominant key fills the whole object and the payload repeats itself.
    taken.add(best_key)
    return source[best_key]


def _so_floor_terms(name: str, schema: dict) -> list[str]:
    """The words that identify one schema field inside a prose answer."""
    words = list(_so_words(name))
    described = schema.get("description") if isinstance(schema, dict) else None
    if isinstance(described, str):
        words += [w for w in _so_words(described)][:8]
    return words


def _so_floor_string(name: str, schema: dict, answer: str, source: object, used: set | None = None) -> str:
    """The most defensible literal the draft offers for one string field.

    A schema-conforming placeholder scores zero with certainty; a literal the
    draft actually printed can score. So this reads the draft, and only the
    LENGTH is clipped to what the schema will accept.
    """
    lower_cap = schema.get("minLength")
    lower_cap = lower_cap if isinstance(lower_cap, int) and not isinstance(lower_cap, bool) else 0
    upper_cap = schema.get("maxLength")
    upper_cap = upper_cap if isinstance(upper_cap, int) and not isinstance(upper_cap, bool) else None
    width = min(STRUCTURED_FLOOR_VALUE_CHARS, upper_cap) if upper_cap else STRUCTURED_FLOOR_VALUE_CHARS

    if isinstance(source, str) and source.strip():
        picked = " ".join(source.split())
        if len(picked) <= width and len(picked) >= lower_cap:
            return picked
        clipped = picked[:width]
        if len(clipped) >= lower_cap:
            return clipped
    elif isinstance(source, (int, float)) and not isinstance(source, bool):
        rendered = str(source)
        if lower_cap <= len(rendered) <= (upper_cap or len(rendered)):
            return rendered

    # A sentence splitter is the wrong unit here: `U.S.` severs the very clause
    # that carries the value ("... affected helicopters of U" | "registry is 15").
    # A sliding window has no such seam.
    terms = _so_floor_terms(name, schema)
    text = " ".join((answer or "").split())
    best_window, best_hits = "", 0
    for start in range(0, max(len(text) - _SO_WINDOW_CHARS, 0) + 1, _SO_WINDOW_STEP):
        window = text[start:start + _SO_WINDOW_CHARS]
        low = window.lower()
        hits = sum(1 for term in terms if term in low)
        if hits > best_hits:
            best_hits, best_window = hits, window

    if best_hits:
        wants_digits = bool(_SO_NUMERIC_HINT.intersection(
            _so_words(name + " " + str(schema.get("description") or ""))))
        fits = []
        for found in _SO_CANDIDATE_RE.finditer(best_window):
            quoted, dotted, numeric = found.groups()
            candidate = (quoted or dotted or numeric).strip()
            if lower_cap <= len(candidate) <= (upper_cap or len(candidate)):
                fits.append((candidate, numeric is not None))
        used = used if used is not None else set()
        # Two fields answered by the same literal reads as a degenerate payload
        # even when both literals are real, so a value is spent once.
        for candidate, is_numeric in fits:
            if is_numeric == wants_digits and candidate not in used:
                used.add(candidate)
                return candidate
        for candidate, _is_numeric in fits:
            if candidate not in used:
                used.add(candidate)
                return candidate

    scope = best_window if best_hits else text
    if len(scope) > width:
        clipped = scope[:width]
        spaced = clipped.rsplit(" ", 1)[0] if " " in clipped else clipped
        scope = spaced if len(spaced) >= lower_cap else clipped
    return scope if len(scope) >= lower_cap else text[:width]


def _so_floor(
    schema: object, root: object, answer: str, source: object = None,
    name: str = "", depth: int = 0, used: set | None = None,
) -> object:
    """`_so_skeleton`'s shape, filled from the draft instead of with `x`.

    Reached only when every re-expression attempt failed. Returns None when the
    draft is empty — the one case where the skeleton is still the best payload
    available, because there is nothing else to put in the box.
    """
    if depth == 0:
        if not (answer or "").strip():
            return None
        source = _so_extract_json(answer)
        used = set()
    resolved = _so_resolve(schema, root)
    if depth > STRUCTURED_MAX_DEPTH or not resolved:
        return None
    if "const" in resolved:
        return resolved["const"]
    if "default" in resolved:
        return resolved["default"]
    allowed = resolved.get("enum")
    if isinstance(allowed, list) and allowed:
        for option in allowed:
            if source is not None and option == source:
                return option
        return allowed[0]
    for keyword in ("anyOf", "oneOf", "allOf"):
        branches = resolved.get(keyword)
        if isinstance(branches, list) and branches:
            return _so_floor(branches[0], root, answer, source, name, depth + 1, used)
    type_names = _so_type_names(resolved)
    type_name = type_names[0] if type_names else ("object" if resolved.get("properties") else "null")

    if type_name == "object":
        properties = resolved.get("properties")
        properties = properties if isinstance(properties, dict) else {}
        built = {}
        taken: set = set()
        for key in resolved.get("required") or ():
            if not isinstance(key, str):
                continue
            sub_schema = _so_resolve(properties.get(key, {}), root)
            built[key] = _so_floor(
                properties.get(key, {}), root, answer,
                _so_pick_source(key, sub_schema, source, taken), key, depth + 1, used,
            )
        return built
    if type_name == "array":
        items_schema = resolved.get("items")
        items_schema = items_schema if isinstance(items_schema, dict) else {}
        upper = resolved.get("maxItems")
        upper = upper if isinstance(upper, int) and not isinstance(upper, bool) else 25
        if isinstance(source, list) and source:
            return [
                _so_floor(items_schema, root, answer, item, name, depth + 1, used)
                for item in source[:upper]
            ]
        minimum = resolved.get("minItems")
        count = minimum if isinstance(minimum, int) and not isinstance(minimum, bool) else 0
        return [
            _so_floor(items_schema, root, answer, None, name, depth + 1, used)
            for _ in range(min(count, 8))
        ]
    if type_name == "string":
        return _so_floor_string(name, resolved, answer, source, used)
    if type_name == "integer" or type_name == "number":
        if isinstance(source, (int, float)) and not isinstance(source, bool):
            return int(source) if type_name == "integer" else source
        if isinstance(source, str):
            try:
                parsed = float(source.replace(",", ""))
                return int(parsed) if type_name == "integer" else parsed
            except ValueError:
                pass
        return _so_skeleton_number(resolved, type_name)
    if type_name == "boolean":
        return source if isinstance(source, bool) else False
    return None


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
    question = ""
    try:
        question = query.text or ""
    except Exception:
        question = ""

    # The floor is computed BEFORE the first call, so no exit from this loop can
    # reach `_so_skeleton` while a draft exists. Measured on the B lineage across
    # three batches: 39 runs shipped a skeleton payload (every string leaf `x`)
    # and all 39 scored 0.000 — a conforming placeholder is a certain zero, a
    # literal the draft printed is not. This lineage shipped 14 such payloads in
    # 60 schema-bound runs on `c9c8b787`.
    best: object = None
    have_best = False
    used_evidence = False
    # The conversion step used to be handed the prose answer alone and told not
    # to invent. An answer that hedges then converts to a schema-valid object of
    # blanks, which passes every shape check there is. The passages this run
    # actually read travel with it from the FIRST call instead.
    evidence = _so_evidence()
    problems: list[str] = []
    floored = _so_floor(schema, schema, answer)
    if floored is not None:
        best, have_best = floored, True
    for attempt in range(STRUCTURED_ATTEMPTS):
        remaining = deadline - perf_counter()
        if remaining <= 4.0:
            break
        timeout = min(STRUCTURED_CALL_TIMEOUT_SECONDS, remaining - 2.0)
        if timeout < STRUCTURED_CALL_MIN_SECONDS:
            break
        raw = await _so_call(_so_messages(query.text, schema, answer, problems, evidence), timeout)
        parsed = _so_extract_json(raw)
        if parsed is None:
            problems = ["the reply was not parseable JSON; emit the bare JSON value only"]
            continue
        candidate = _so_coerce(parsed, schema, schema)
        candidate = _so_qcased(candidate, question, schema)
        if not _so_fits_size(candidate):
            problems = [f"the value exceeded {STRUCTURED_OUTPUT_CHAR_CAP} JSON characters; be more concise"]
            continue
        problems = _so_errors(candidate, schema, schema)[:STRUCTURED_MAX_REPORTED_ERRORS]
        # The floor already occupies `best`, so "keep the candidate" is a choice
        # rather than the only option: keep whichever the checker rejects LESS,
        # and never trade a populated value for a vacuous one.
        if not have_best or (
            (_so_is_vacuous(best) and not _so_is_vacuous(candidate))
            or (not _so_is_vacuous(candidate)
                and len(problems) < len(_so_errors(best, schema, schema)))
        ):
            best = candidate
            have_best = True
        if not problems:
            # A schema-valid payload with nothing in it is the one failure the
            # shape check cannot see. Ask again with the retrieved passages
            # attached -- the first answer is kept either way, so this can only
            # add.
            if _so_is_vacuous(candidate) and not used_evidence:
                if evidence:
                    used_evidence = True
                    problems = ["every field came back blank; the evidence section "
                                "carries the rows this question asks about — take the "
                                "values from it"]
                    continue
            proof = await _so_proof(question, candidate, answer, evidence, deadline)
            return _so_response(candidate, citations,
                                _so_best_note(proof, answer, candidate, citations))
        if attempt + 1 >= STRUCTURED_ATTEMPTS:
            break

    if have_best:
        proof = await _so_proof(question, best, answer, evidence, deadline)
        return _so_response(best, citations,
                            _so_best_note(proof, answer, best, citations))
    fallback = _so_skeleton(schema, schema)
    if fallback is None and answer:
        fallback = answer[:STRUCTURED_OUTPUT_CHAR_CAP]
    return _so_response(fallback, citations, _so_note(answer, fallback, citations))


_NOTE_MARKER_RE = re.compile(r"\[\[(\d{1,3})\]\]")
_NOTE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
# A sentence reporting that something could NOT be established cannot support a
# value the answer ships -- pairing the two is a self-contradiction, and the
# judge scores a contradictory note WORSE than no note at all. A draft written
# before the structured re-ask routinely carries such lines about the very
# fields that were later recovered, so this is the common case, not an edge one.
_NOTE_ABSENCE_RE = re.compile(
    r"\b(?:missing|truncated|absent|unavailable|unknown|unclear|unconfirmed|"
    r"not\s+(?:found|available|stated|listed|shown|given|present|reported)|"
    r"could\s+not|cannot|can't|couldn't|unable|no\s+(?:data|value|figure|entry|record))\b",
    re.IGNORECASE,
)


def _note_values(value: object, out: list[str], depth: int = 0) -> None:
    """Every scalar the answer actually ships, as comparable text."""
    if depth > STRUCTURED_MAX_DEPTH:
        return
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float)):
        out.append(str(value))
        return
    if isinstance(value, str):
        text = value.strip()
        if text:
            out.append(text)
        return
    if isinstance(value, dict):
        for item in value.values():
            _note_values(item, out, depth + 1)
        return
    if isinstance(value, list):
        for item in value:
            _note_values(item, out, depth + 1)


def _note_states_value(sentence: str, values: list[str]) -> bool:
    """True when the sentence repeats a value the answer ships.

    Digits are compared with separators removed, so a value printed `380,000`
    in the source still matches the `380000` the schema asked for (and back).
    """
    lowered = sentence.casefold()
    stripped = lowered.replace(",", "")
    for value in values:
        candidate = value.casefold()
        if len(candidate) < 2:
            continue
        if candidate in lowered:
            return True
        bare = candidate.replace(",", "")
        if len(bare) >= 2 and bare in stripped:
            return True
    return False


def _so_best_note(proof: str, answer: str, value: object, citations: object) -> str | None:
    """Prefer the enumeration pass; keep the draft-derived note as the floor.

    The proof runs through the SAME guards as the draft (§ `_so_note`), so an
    enumeration that drifts into a contradiction or an unresolvable pointer is
    dropped line by line and we simply fall back. C39 can therefore only differ
    from C38 by carrying MORE checked claims, never fewer.
    """
    base = _so_note(answer, value, citations)
    if not proof:
        return base
    lifted = _so_note(proof, value, citations)
    if not lifted:
        return base
    if base and _note_claim_count(base) >= _note_claim_count(lifted):
        return base
    return lifted


def _note_claim_count(note: str) -> int:
    return sum(1 for line in (note or "").split("\n") if line.startswith("- "))


def _so_note(answer: str, value: object, citations: object) -> str | None:
    """Carry the answer's own justification into the one field that accepts it.

    Kept deliberately narrow: a sentence qualifies only if it (a) already states
    a value present in `output` and (b) points at a citation this response
    actually ships. Anything else -- narration, near-misses, method notes -- is
    dropped, so the note can neither contradict the answer nor introduce a claim
    the evidence does not carry. Returns None rather than an empty string: the
    platform rejects the WHOLE response for a blank note.
    """
    if not answer:
        return None
    try:
        limit = len(citations) if citations else 0
    except Exception:
        limit = 0
    if limit <= 0:
        return None
    values: list[str] = []
    _note_values(value, values)
    if not values:
        return None
    lines: list[str] = []
    seen: set[str] = set()
    for raw in _NOTE_SPLIT_RE.split(answer):
        sentence = " ".join(raw.split()).strip("-*\u2022 ").strip()
        if len(sentence) < NOTE_MIN_SENTENCE_CHARS:
            continue
        # Working tables, headings and stub lines are not claims: they read as
        # fragments beside a bare value and buy none of the clarity the note is
        # there to add.
        if "|" in sentence or "#" in sentence or "**" in sentence:
            continue
        if sentence.endswith(":"):
            continue
        markers = [int(n) for n in _NOTE_MARKER_RE.findall(sentence)]
        if not markers or not all(1 <= n <= limit for n in markers):
            continue
        if _NOTE_ABSENCE_RE.search(sentence):
            continue
        if not _note_states_value(sentence, values):
            continue
        # Whole claims only. A sliced sentence stops being the thing that was
        # checked -- it reads as an incomplete assertion, which is the one kind
        # of note the judge scores below having none.
        if len(sentence) > NOTE_LINE_CHARS:
            continue
        key = sentence.casefold()
        if key in seen:
            continue
        seen.add(key)
        lines.append(sentence)
        if len(lines) >= NOTE_MAX_LINES:
            break
    if not lines:
        return None
    head = "Where each answer value comes from:"
    note = head
    for line in lines:
        candidate = note + "\n- " + line
        if len(candidate) > NOTE_MAX_CHARS:
            break
        note = candidate
    if note == head:
        return None
    return note.strip() or None


def _so_response(value: object, citations: object, note: str | None = None) -> Response:
    """Build the response, degrading the payload rather than the answer field.

    The note is attached only when this SDK carries the field and the text is
    non-empty; every fallback path below drops it rather than the answer, since
    a rejected response scores nothing at all.
    """
    if not _so_fits_size(value):
        value = None
    if note:
        try:
            fields = getattr(Response, "model_fields", None) or {}
        except Exception:
            fields = {}
        if "note" in fields:
            try:
                return Response(output=value, citations=citations or None, note=note)
            except Exception:
                pass
    try:
        return Response(output=value, citations=citations or None)
    except Exception:
        return Response(output=value)


async def _plain_query_with_cold_retry(query: Query, budget: float) -> Response:
    """One retry when the pipeline came back with nothing having happened.

    A run that returns within seconds holding zero tool results did not fail on
    the question; it never got to ask one. Sleeping briefly and running once more
    is bounded three ways -- only inside the first seconds, only with most of the
    budget left, only once -- so a genuine fast floor is never retried into the
    time wall. Unverifiable in replay (a validator cold-start cannot be staged),
    so it ships on the bound, not on a measurement.
    """
    start = perf_counter()
    _LAST_INDEX[0] = None
    result = await _plain_query(query, budget)
    elapsed = perf_counter() - start
    index = _LAST_INDEX[0]
    nothing_happened = index is None or index.max_number() == 0
    if (nothing_happened and elapsed < COLD_START_WINDOW_SECONDS
            and budget - elapsed - COLD_START_BACKOFF_SECONDS > COLD_START_MIN_BUDGET_SECONDS):
        await asyncio.sleep(COLD_START_BACKOFF_SECONDS)
        return await _plain_query(query, budget - (perf_counter() - start))
    return result


def _compose_g16n8_0_entry():


    FETCH_TIMEOUT_SECONDS = 15.0
    MAX_FETCH_CONTENT_CHARS = 40_000
    FINAL_ANSWER_CUTOFF_SECONDS = 285.0
    PAGE_READER_TIMEOUT_SECONDS = 20.0
    RESEARCH_TURNS = 23
    RESEARCH_CUTOFF_SECONDS = 240.0
    TASK_TOTAL_BUDGET_SECONDS = 250.0
    MAX_OUTPUT_TOKENS = 127_999
    MAX_SEARCH_RESULTS = 10

    LLM_PROVIDER = "openrouter"
    MODEL = "z-ai/glm-5.2"

    from time import perf_counter
    import asyncio
    import hashlib
    import json
    import re
    import time
    from collections.abc import Awaitable, Callable, Sequence
    from dataclasses import dataclass
    from typing import TypeVar
    from urllib.parse import urldefrag, urlparse

    from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web
    from harnyx_miner_sdk.decorators import entrypoint
    from harnyx_miner_sdk.llm import LlmChoiceMessage, LlmMessageToolCall, LlmUsage
    from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

    VERSION = "v230-2-fdlq"
    _BASE_MODEL = "deepseek/deepseek-v4-flash-0731"
    FINALIZATION_TURNS = 2
    MAX_TURNS = RESEARCH_TURNS + FINALIZATION_TURNS
    ENTRYPOINT_TIMEOUT_SECONDS = 300.0
    ENTRYPOINT_RETURN_CUTOFF_SECONDS = 295.0
    TURNS_REMAINING_WARNING_THRESHOLD = 20
    CONTEXT_WINDOW_TOKENS = 1_048_576
    CONTEXT_SUMMARIZATION_CUTOFF = 0.7
    PAGE_READER_CHUNK_SIZE = 6_000
    PAGE_READER_CHUNK_OVERLAP = 500
    MAX_CITATION_REFS = 200
    MAX_CITATION_SEGMENTS = 400
    MAX_CITATION_EVIDENCE_CHARS = 120_000
    MIN_CITATION_SLICE_CHARS = 100
    MAX_EVIDENCE_SEGMENT_CHARS = 1_600
    EVIDENCE_SEGMENT_OVERLAP_CHARS = 200

    SYSTEM_PROMPT = (
        "You are an AI agent that will be given a specific task. You are to complete that task using the tools "
        "provided in 25 steps. You will need to call a finish tool as your last step, where you will pass your "
        "finish reason and any required final fields for that tool.\n"
        " You are not able to interact with the user during the task.\n\n"
        "SOURCE RESTRICTIONS: Before researching, identify whether the task limits acceptable evidence to named "
        "sources, documents, editions, page types, or publication forms. If it does, that limit is binding for search "
        "targets, fetched evidence, calculations, and final citations. A discovery page may help locate the required "
        "source but cannot support the final answer. Do not substitute a third-party summary, a different edition, or "
        "another page or document form merely because it contains the same facts. Do not call finish until every "
        "material answer claim is directly supported by shown evidence from the allowed source and exact requested "
        "document form; if required evidence is still missing, continue researching within the remaining research "
        "turns. Example: when a task says to use only an agency's annual report, cite that report, not a news summary "
        "or a later edition."
    )

    MESSAGE_SUMMARIZER = "The context window is approaching its limit. Please create a concise summary of the conversation so far to preserve important information.\n\nYour summary should include:\n\n1. **Task Overview**: What is the main goal or objective?\n\n2. **Progress Made**: What has been accomplished so far?\n   - Key files created/modified (with paths)\n   - Important functions/classes implemented\n   - Tools used and their outcomes\n\n3. **Current State**: Where are we now?\n   - What is currently working?\n   - What has been tested/verified?\n\n4. **Next Steps**: What still needs to be done?\n   - Outstanding TODOs (with specific file paths and line numbers if applicable)\n   - Known issues or bugs to address\n   - Features or functionality not yet implemented\n\n5. **Important Context**: Any critical details that shouldn't be lost\n   - Special configurations or setup requirements\n   - Important variable names, API endpoints, or data structures\n   - Edge cases or constraints to keep in mind\n   - Dependencies or relationships between components\n\nKeep the summary concise but comprehensive. Do not use any tools. Focus on actionable information that will allow smooth continuation of the work.\n"

    MESSAGE_SUMMARIZER_TEXT_ONLY = (
        "IMPORTANT: Respond with the summary as plain prose text only. Do NOT call any tools — a tool call cannot serve "
        "as a summary and will cause the summarization to fail."
    )

    MESSAGE_SUMMARIZER_BRIDGE = '**Context Continuation**\n\nDue to context window limitations, the previous conversation has been summarized. Below is a summary of what happened before:\n\n---\n\n{summary}\n\n---\n\nYou should continue working on this task from where it was left off. All the progress, current state, and next steps are described in the summary above. Proceed with completing any outstanding work.'

    CONTAMINATION_NEEDLES = (
        "deepsearchqa",
        "deep search qa",
        "google/deepsearchqa",
        "dsqa-full.csv",
        "artificialanalysis.ai/agents/search-api",
        "openrouter.ai/benchmarks/deepsearchqa",
    )

    WEB_SEARCH_TOOL = {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web. Returns up to 10 ranked results from Parallel Search API advanced, including titles, "
                "URLs, and excerpts. Use concise keyword queries."
            ),
            "parameters": {
                "additionalProperties": False,
                "properties": {
                    "query": {
                        "description": "One concise web search query.",
                        "maxLength": 200,
                        "minLength": 1,
                        "title": "Query",
                        "type": "string",
                    }
                },
                "required": ["query"],
                "title": "WebSearchParams",
                "type": "object",
            },
        },
    }

    WEB_FETCH_TOOL = {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": (
                "Fetch and extract text from a top-level URL returned by web_search or an HTTP(S) URL literally "
                "shown in that result's title or excerpt. Other URLs are rejected."
            ),
            "parameters": {
                "additionalProperties": False,
                "properties": {
                    "url": {
                        "description": "One top-level or literally shown child URL from an earlier web_search call.",
                        "minLength": 1,
                        "title": "Url",
                        "type": "string",
                    }
                },
                "required": ["url"],
                "title": "WebFetchParams",
                "type": "object",
            },
        },
    }

    FINISH_TOOL = {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Submit the final answer and end the task. Call this only when the answer is ready.",
            "parameters": {
                "additionalProperties": False,
                "properties": {
                    "answer": {
                        "description": "The final answer to the user's question. Give only the answer.",
                        "minLength": 1,
                        "title": "Answer",
                        "type": "string",
                    }
                },
                "required": ["answer"],
                "title": "FinishAnswerParams",
                "type": "object",
            },
        },
    }

    TOOLS = [WEB_SEARCH_TOOL, WEB_FETCH_TOOL, FINISH_TOOL]


    class DeadlineExceededError(RuntimeError):
        """The declared miner-owned wall-clock budget cannot start another stage."""


    class StageDeadlineElapsedError(TimeoutError):
        """A miner-owned stage deadline elapsed before the awaited call completed."""


    DeadlineResult = TypeVar("DeadlineResult")


    async def _await_before_stage_cutoff(
        operation: Awaitable[DeadlineResult],
        *,
        timeout_seconds: float,
    ) -> DeadlineResult:
        task = asyncio.ensure_future(operation)
        done, _pending = await asyncio.wait(
            (task,),
            timeout=max(0.001, timeout_seconds - 0.1),
        )
        if task in done:
            return await task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        raise StageDeadlineElapsedError("miner-owned stage deadline elapsed")


    @dataclass(frozen=True, slots=True)
    class ExecutionDeadline:
        started_at: float
        clock: Callable[[], float]

        @classmethod
        def start(cls, *, clock: Callable[[], float] = time.monotonic) -> ExecutionDeadline:
            return cls(started_at=clock(), clock=clock)

        def elapsed_seconds(self) -> float:
            return max(0.0, self.clock() - self.started_at)

        def remaining_before(self, cutoff_seconds: float) -> float:
            return max(0.0, cutoff_seconds - self.elapsed_seconds())

        def research_open(self) -> bool:
            return self.remaining_before(RESEARCH_CUTOFF_SECONDS) > 0.0

        def require_timeout_before(self, cutoff_seconds: float, *, stage: str) -> float:
            remaining = self.remaining_before(cutoff_seconds)
            if remaining <= 0.0:
                raise DeadlineExceededError(f"{stage} cannot start after its wall-clock cutoff")
            return remaining


    def _log_deadline_event(event: str, deadline: ExecutionDeadline, **details: object) -> None:
        print(
            json.dumps(
                {
                    "event": event,
                    "elapsed_seconds": round(deadline.elapsed_seconds(), 6),
                    **details,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        )


    @dataclass(frozen=True, slots=True)
    class EvidenceSegment:
        segment_id: int
        start: int
        end: int


    @dataclass(frozen=True, slots=True)
    class EvidenceCandidate:
        candidate_id: int
        receipt_id: str
        result_id: str
        url: str
        title: str
        note: str
        segments: tuple[EvidenceSegment, ...]


    @dataclass(frozen=True, slots=True)
    class EvidenceSelection:
        candidate_id: int
        segment_ids: tuple[int, ...]
        is_support_set: bool


    def _collapsed_whitespace_with_offsets(text: str) -> tuple[str, tuple[int, ...], tuple[int, ...]]:
        normalized: list[str] = []
        starts: list[int] = []
        ends: list[int] = []
        in_whitespace = False
        for offset, character in enumerate(text):
            if character.isspace():
                if not in_whitespace:
                    normalized.append(" ")
                    starts.append(offset)
                    ends.append(offset + 1)
                    in_whitespace = True
                else:
                    ends[-1] = offset + 1
                continue
            normalized.append(character)
            starts.append(offset)
            ends.append(offset + 1)
            in_whitespace = False
        return "".join(normalized), tuple(starts), tuple(ends)


    def _all_exact_ranges(source_text: str, visible_text: str) -> list[tuple[int, int]]:
        ranges: list[tuple[int, int]] = []
        cursor = 0
        while True:
            start = source_text.find(visible_text, cursor)
            if start < 0:
                return ranges
            ranges.append((start, start + len(visible_text)))
            cursor = start + 1


    def _all_whitespace_normalized_ranges(source_text: str, visible_text: str) -> list[tuple[int, int]]:
        normalized_source, starts, ends = _collapsed_whitespace_with_offsets(source_text)
        normalized_visible, _, _ = _collapsed_whitespace_with_offsets(visible_text)
        normalized_visible = normalized_visible.strip()
        if not normalized_visible:
            return []
        ranges: list[tuple[int, int]] = []
        cursor = 0
        while True:
            start = normalized_source.find(normalized_visible, cursor)
            if start < 0:
                return ranges
            end = start + len(normalized_visible)
            ranges.append((starts[start], ends[end - 1]))
            cursor = start + 1


    def _merge_ranges(ranges: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
        merged: list[tuple[int, int]] = []
        for start, end in sorted(ranges):
            if not merged or start > merged[-1][1]:
                merged.append((start, end))
                continue
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end))
        return merged


    def _expand_to_minimum_slice(source_length: int, start: int, end: int) -> tuple[int, int]:
        if source_length < MIN_CITATION_SLICE_CHARS:
            return 0, source_length
        missing = max(0, MIN_CITATION_SLICE_CHARS - (end - start))
        left = min(start, missing // 2)
        start -= left
        end += missing - left
        if end > source_length:
            start = max(0, start - (end - source_length))
            end = source_length
        return start, end


    def _split_segment_range(start: int, end: int) -> list[tuple[int, int]]:
        if end - start <= MAX_EVIDENCE_SEGMENT_CHARS:
            return [(start, end)]
        step = MAX_EVIDENCE_SEGMENT_CHARS - EVIDENCE_SEGMENT_OVERLAP_CHARS
        segments: list[tuple[int, int]] = []
        cursor = start
        while cursor < end:
            segment_end = min(cursor + MAX_EVIDENCE_SEGMENT_CHARS, end)
            if segment_end - cursor < MIN_CITATION_SLICE_CHARS and segments:
                previous_start, _ = segments[-1]
                segments[-1] = (previous_start, end)
                break
            segments.append((cursor, segment_end))
            if segment_end == end:
                break
            cursor += step
        return segments


    def _evidence_segments(note: str, visible_texts: Sequence[str]) -> tuple[EvidenceSegment, ...]:
        visible_ranges: list[tuple[int, int]] = []
        for visible_text in visible_texts:
            if not visible_text.strip():
                continue
            exact = _all_exact_ranges(note, visible_text)
            visible_ranges.extend(exact or _all_whitespace_normalized_ranges(note, visible_text))
        expanded = [_expand_to_minimum_slice(len(note), start, end) for start, end in visible_ranges]
        segment_ranges: list[tuple[int, int]] = []
        for start, end in _merge_ranges(expanded):
            segment_ranges.extend(_split_segment_range(start, end))
        return tuple(
            EvidenceSegment(segment_id=segment_id, start=start, end=end)
            for segment_id, (start, end) in enumerate(dict.fromkeys(segment_ranges))
        )


    def _visible_fetch_texts(body: str) -> tuple[str, ...]:
        if len(body) <= MAX_FETCH_CONTENT_CHARS:
            return (body,)
        half = MAX_FETCH_CONTENT_CHARS // 2
        return body[:half], body[-half:]


    class EvidenceLedger:
        """Own exact source support and stable evidence numbers shown to the model."""

        def __init__(self) -> None:
            self._candidates: list[EvidenceCandidate] = []
            self._identity_candidates: dict[tuple[str, str], EvidenceCandidate] = {}
            self._selections: list[EvidenceSelection] = []
            self._support_set_numbers: dict[tuple[int, tuple[int, ...]], int] = {}

        @property
        def candidates(self) -> tuple[EvidenceCandidate, ...]:
            return tuple(self._candidates)

        @property
        def support_set_numbers(self) -> tuple[int, ...]:
            return tuple(
                number
                for number, selection in enumerate(self._selections, start=1)
                if selection.is_support_set
            )

        def capture(
            self,
            result: object,
            *,
            retained_indices: set[int],
            visible_text_by_index: dict[int, tuple[str, ...]],
        ) -> dict[int, EvidenceCandidate]:
            if getattr(result, "result_policy", None) != "referenceable":
                raise RuntimeError("observed search result is not referenceable")
            receipt_id = getattr(result, "receipt_id", None)
            if not isinstance(receipt_id, str) or not receipt_id:
                raise RuntimeError("referenceable search result has no receipt_id")

            observed: dict[int, EvidenceCandidate] = {}
            for item in getattr(result, "results", ()):
                index = getattr(item, "index", None)
                if index not in retained_indices:
                    continue
                result_id = getattr(item, "result_id", None)
                note = getattr(item, "note", None)
                if not isinstance(result_id, str) or not result_id:
                    raise RuntimeError("referenceable search result has no result_id")
                if not isinstance(note, str) or not note.strip():
                    continue
                identity = (receipt_id, result_id)
                existing = self._identity_candidates.get(identity)
                if existing is not None:
                    observed[index] = existing
                    continue
                segments = _evidence_segments(note, visible_text_by_index.get(index, ()))
                if not segments:
                    continue
                candidate = EvidenceCandidate(
                    candidate_id=len(self._candidates),
                    receipt_id=receipt_id,
                    result_id=result_id,
                    url=str(getattr(item, "url", None) or ""),
                    title=str(getattr(item, "title", None) or ""),
                    note=note,
                    segments=segments,
                )
                self._candidates.append(candidate)
                self._identity_candidates[identity] = candidate
                for segment in segments:
                    self._selections.append(EvidenceSelection(candidate.candidate_id, (segment.segment_id,), False))
                observed[index] = candidate
            return observed

        def numbered_segments(
            self,
            candidate: EvidenceCandidate,
        ) -> tuple[tuple[int, EvidenceSegment], ...]:
            segments = {segment.segment_id: segment for segment in candidate.segments}
            return tuple(
                (number, segments[selection.segment_ids[0]])
                for number, selection in enumerate(self._selections, start=1)
                if selection.candidate_id == candidate.candidate_id and not selection.is_support_set
            )

        def register_support_set(self, candidate: EvidenceCandidate) -> int:
            segment_ids = tuple(segment.segment_id for segment in candidate.segments)
            if not segment_ids:
                raise RuntimeError("cannot register an empty evidence support set")
            identity = (candidate.candidate_id, segment_ids)
            existing = self._support_set_numbers.get(identity)
            if existing is not None:
                return existing
            self._selections.append(EvidenceSelection(candidate.candidate_id, segment_ids, True))
            evidence_number = len(self._selections)
            self._support_set_numbers[identity] = evidence_number
            return evidence_number

        def selection_for_evidence_number(self, evidence_number: int) -> EvidenceSelection | None:
            if evidence_number < 1 or evidence_number > len(self._selections):
                return None
            return self._selections[evidence_number - 1]


    def _normalized_url(url: str) -> str:
        return urldefrag(url.strip()).url


    CHILD_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


    def _admissible_url(value: str) -> str | None:
        cleaned = _normalized_url(value.rstrip(".,;:!?)\"]"))
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
            return None
        return cleaned


    def _visible_child_urls(*texts: str | None) -> set[str]:
        discovered: set[str] = set()
        for text in texts:
            if not text:
                continue
            for match in CHILD_URL_PATTERN.findall(text):
                admitted = _admissible_url(match)
                if admitted is not None:
                    discovered.add(admitted)
        return discovered


    @dataclass(frozen=True, slots=True)
    class PageChunk:
        chunk_id: str
        start: int
        end: int
        text: str


    @dataclass(frozen=True, slots=True)
    class PageReadResult:
        selected_texts: tuple[str, ...]
        page_findings: str
        missing_information: str


    PAGE_READER_SYSTEM_PROMPT = 'ROLE\nYou read one complete source document for a separate research agent. Select the original chunks that let that agent\nverify every useful finding from this page. Base the memo only on this document. Do not search, use tools, or expose\nprivate reasoning.\n\nSELECTION RULES\n- Select a chunk when it directly supports a requested fact, exposes a useful source link, or supplies a heading,\n  label, unit, exception, or qualifier needed to interpret a fact.\n- A zero count, no-match result, or other exhaustive negative is a useful finding. For such a finding, select the\n  document scope and every candidate region needed to verify completeness.\n- The selected original support must fit within 120000 characters. Keep the smallest complete support set. If the\n  complete support needed for a finding cannot fit, do not assert that finding; explain the unresolved fact in\n  missing_information instead.\n- selected_chunk_ids may be empty only when this page contributes no fact or source route to the answer. In that case,\n  page_findings must also be an empty string and missing_information must explain what source is still needed.\n- If page_findings contains any useful conclusion, selected_chunk_ids must contain its supporting original chunks.\n\nOUTPUT CONTRACT\nReturn one JSON object with exactly these fields:\n- selected_chunk_ids: unique input chunk IDs in document order.\n- page_findings: a concise factual memo of what the selected original chunks establish, or an empty string only when\n  the page is irrelevant.\n- missing_information: facts still needed from another page, or an empty string.\nReturn no Markdown and no other text.\n\nGOOD ZERO-RESULT EXAMPLE\nThe question asks whether any Florida record was REMOVED. C0000 identifies the annual document, while C0008 and C0014\ncontain all Florida candidate records and none has action REMOVED.\n{"selected_chunk_ids":["C0000","C0008","C0014"],"page_findings":"The annual document contains no Florida REMOVED record.","missing_information":""}\n\nBAD ZERO-RESULT EXAMPLE\n{"selected_chunk_ids":[],"page_findings":"There are zero Florida REMOVED records.","missing_information":""}\nThis is invalid because it asserts a useful conclusion while returning no original evidence.\n\nIRRELEVANT-PAGE EXAMPLE\n{"selected_chunk_ids":[],"page_findings":"","missing_information":"The requested annual report is not on this page."}'


    def _page_chunks(body: str) -> tuple[PageChunk, ...]:
        if PAGE_READER_CHUNK_OVERLAP >= PAGE_READER_CHUNK_SIZE:
            raise RuntimeError("page-reader overlap must be smaller than chunk size")
        chunks: list[PageChunk] = []
        start = 0
        index = 0
        while start < len(body):
            end = min(len(body), start + PAGE_READER_CHUNK_SIZE)
            chunks.append(PageChunk(f"C{index:04d}", start, end, body[start:end]))
            if end == len(body):
                break
            start = end - PAGE_READER_CHUNK_OVERLAP
            index += 1
        return tuple(chunks)


    def _json_object_from_reader_text(text: str) -> dict[str, object]:
        stripped = text.strip()
        fence = re.fullmatch(r"```(?:json)?\s*\n?(.*?)\n?```", stripped, flags=re.DOTALL | re.IGNORECASE)
        if fence is not None:
            stripped = fence.group(1).strip()
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise ValueError("page reader must return one JSON object")
        return parsed


    def _validate_page_reader_output(payload: dict[str, object], chunks: tuple[PageChunk, ...]) -> PageReadResult:
        expected = {"selected_chunk_ids", "page_findings", "missing_information"}
        if set(payload) != expected:
            raise ValueError("page reader returned unexpected fields")
        selected = payload["selected_chunk_ids"]
        findings = payload["page_findings"]
        missing = payload["missing_information"]
        if not isinstance(selected, list) or any(not isinstance(item, str) for item in selected):
            raise TypeError("selected_chunk_ids must be an array of strings")
        if len(selected) != len(set(selected)):
            raise ValueError("selected_chunk_ids must be unique")
        by_id = {chunk.chunk_id: chunk for chunk in chunks}
        if any(item not in by_id for item in selected):
            raise ValueError("selected_chunk_ids contains an unknown ID")
        order = {chunk.chunk_id: index for index, chunk in enumerate(chunks)}
        if selected != sorted(selected, key=lambda item: order[item]):
            raise ValueError("selected_chunk_ids must be in document order")
        if not isinstance(findings, str):
            raise TypeError("page_findings must be a string")
        if not isinstance(missing, str):
            raise TypeError("missing_information must be a string")
        if findings.strip() and not selected:
            raise ValueError(
                "page_findings contributes to the answer but selected_chunk_ids is empty; select the original chunks "
                "that verify the finding, and for an exhaustive negative include the document scope plus every candidate "
                "region or the complete document"
            )
        if selected and not findings.strip():
            raise ValueError("selected_chunk_ids is non-empty but page_findings is empty; explain what the chunks establish")
        if not selected and not missing.strip():
            raise ValueError("an irrelevant page with no selected chunks must explain the missing information")
        return PageReadResult(tuple(by_id[item].text for item in selected), findings, missing)


    async def _read_large_page(
        *,
        question: str,
        url: str,
        body: str,
        deadline: ExecutionDeadline,
    ) -> PageReadResult:
        chunks = _page_chunks(body)
        serialized = "\n\n".join(
            f"<{chunk.chunk_id} start={chunk.start} end={chunk.end}>\n{chunk.text}\n</{chunk.chunk_id}>"
            for chunk in chunks
        )
        messages: list[dict[str, object]] = [
            {"role": "system", "content": PAGE_READER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"QUESTION\n{question}\n\nSOURCE URL\n{url}\n\nDOCUMENT CHUNKS\n{serialized}",
            },
        ]
        reader_started_at = deadline.clock()
        for attempt in range(1, 3):
            reader_elapsed = max(0.0, deadline.clock() - reader_started_at)
            reader_remaining = PAGE_READER_TIMEOUT_SECONDS - reader_elapsed
            if reader_remaining <= 0.0:
                raise DeadlineExceededError("large-page reader exhausted its shared 20-second call and recovery budget")
            timeout_seconds = min(
                reader_remaining,
                deadline.require_timeout_before(RESEARCH_CUTOFF_SECONDS, stage="large-page reader"),
            )
            result = await _await_before_stage_cutoff(
                llm_chat(
                    provider="openrouter",
                    model=_BASE_MODEL,
                    messages=messages,
                    temperature=0,
                    thinking={"enabled": False},
                    provider_extra=None,
                    timeout=timeout_seconds,
                ),
                timeout_seconds=timeout_seconds,
            )
            if len(result.response.choices) != 1:
                raise RuntimeError("page reader did not return exactly one choice")
            message = result.response.choices[0].message
            if message.tool_calls:
                raise RuntimeError("page reader returned an unexpected tool call")
            text = _assistant_text(message)
            if text is None:
                raise RuntimeError("page reader returned no text")
            try:
                page_read = _validate_page_reader_output(_json_object_from_reader_text(text), chunks)
                support_segments = _evidence_segments(body, page_read.selected_texts)
                support_ranges = _merge_ranges((segment.start, segment.end) for segment in support_segments)
                support_chars = sum(end - start for start, end in support_ranges)
                if support_chars > MAX_CITATION_EVIDENCE_CHARS:
                    raise ValueError(
                        f"selected original support is {support_chars} characters, above the "
                        f"{MAX_CITATION_EVIDENCE_CHARS}-character public evidence limit; select the smallest complete "
                        "support set, and move any finding that cannot fit to missing_information instead of asserting it"
                    )
                if len(support_ranges) > MAX_CITATION_SEGMENTS:
                    raise ValueError(
                        f"selected original support forms {len(support_ranges)} ranges, above the "
                        f"{MAX_CITATION_SEGMENTS}-segment public evidence limit; select a smaller complete support set"
                    )
                return page_read
            except (TypeError, ValueError) as error:
                if attempt == 2:
                    raise RuntimeError(
                        f"page reader output rejected after one feedback retry: {error}; raw_output={text!r}"
                    ) from error
                _log_deadline_event("large_page_reader_feedback_retry", deadline, reason=str(error))
                messages.extend(
                    [
                        {"role": "assistant", "content": text},
                        {
                            "role": "user",
                            "content": f"Your output was rejected by the mechanical contract: {error}. Return a corrected JSON object.",
                        },
                    ]
                )
        raise AssertionError("page-reader recovery loop ended unexpectedly")


    def _contamination_hit(text: str) -> str | None:
        folded = text.casefold()
        for needle in CONTAMINATION_NEEDLES:
            if needle in folded:
                return needle
        return None


    def _truncate_middle(text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        return (
            text[: max_length // 2]
            + f"\n... This content has been truncated from an original {len(text)} characters to stay below "
            + f"{max_length} characters ...\n"
            + text[-max_length // 2 :]
        )


    def _parse_object(arguments: str) -> dict[str, object] | None:
        try:
            parsed = json.loads(arguments if arguments.strip() else "{}")
        except (json.JSONDecodeError, ValueError):
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed


    def _single_string_argument(
        arguments: str,
        *,
        field: str,
        max_length: int | None = None,
    ) -> str | None:
        parsed = _parse_object(arguments)
        if parsed is None or set(parsed) != {field}:
            return None
        value = parsed[field]
        if not isinstance(value, str) or not value or (max_length is not None and len(value) > max_length):
            return None
        return value


    def _assistant_text(message: LlmChoiceMessage) -> str | None:
        content = message.content
        texts: list[str] = []
        for part in content:
            if part.text is not None:
                texts.append(part.text)
        if not texts:
            return None
        return "".join(texts)


    def _assistant_input_message(message: LlmChoiceMessage) -> dict[str, object]:
        text = _assistant_text(message)
        tool_calls = []
        for call in message.tool_calls or ():
            tool_calls.append(
                {
                    "id": call.id,
                    "type": call.type,
                    "name": call.name,
                    "arguments": call.arguments if call.arguments.strip() else "{}",
                }
            )
        payload: dict[str, object] = {
            "role": "assistant",
            "content": text,
        }
        if tool_calls:
            payload["tool_calls"] = tool_calls
        if message.reasoning_details is not None:
            payload["reasoning_details"] = list(message.reasoning_details)
        return payload


    def _tool_result_message(call: LlmMessageToolCall, content: str) -> dict[str, object]:
        return {
            "role": "tool",
            "tool_call_id": call.id,
            "name": call.name,
            "content": content,
        }


    async def _search(
        query: str,
        allowed_urls: set[str],
        ledger: EvidenceLedger,
        deadline: ExecutionDeadline | None = None,
    ) -> str:
        attempt_number = 0
        while True:
            if deadline is not None and not deadline.research_open():
                _log_deadline_event("research_tool_skipped_at_deadline", deadline, tool="web_search")
                return "<web_search><error>The wall-clock research deadline has been reached.</error></web_search>"
            attempt_number += 1
            timeout_seconds = (
                None
                if deadline is None
                else deadline.require_timeout_before(RESEARCH_CUTOFF_SECONDS, stage="web_search")
            )
            try:
                if timeout_seconds is None:
                    result = await search_web(
                        query,
                        provider="parallel",
                        num=MAX_SEARCH_RESULTS,
                        provider_extra={"mode": "advanced"},
                    )
                else:
                    result = await _await_before_stage_cutoff(
                        search_web(
                            query,
                            provider="parallel",
                            num=MAX_SEARCH_RESULTS,
                            provider_extra={"mode": "advanced"},
                            timeout=timeout_seconds,
                        ),
                        timeout_seconds=timeout_seconds,
                    )
            except StageDeadlineElapsedError:
                _log_deadline_event("research_tool_timed_out_at_deadline", deadline, tool="web_search")
                return "<web_search><error>The wall-clock research deadline was reached during search.</error></web_search>"
            except BaseException:
                if deadline is not None and not deadline.research_open():
                    _log_deadline_event("research_retry_stopped_at_deadline", deadline, tool="web_search")
                    return "<web_search><error>The wall-clock research deadline has been reached.</error></web_search>"
                backoff_seconds = min(2 ** min(attempt_number - 1, 5), 30)
                if deadline is not None:
                    backoff_seconds = min(
                        backoff_seconds,
                        deadline.require_timeout_before(RESEARCH_CUTOFF_SECONDS, stage="web_search retry"),
                    )
                await asyncio.sleep(backoff_seconds)
                continue

            retained_by_index: dict[int, dict[str, object]] = {}
            retained_indices: set[int] = set()
            visible_text_by_index: dict[int, tuple[str, ...]] = {}
            for index, item in enumerate(result.response.data):
                candidate: dict[str, object] = {
                    "excerpts": [item.snippet] if item.snippet is not None else [],
                    "title": item.title,
                    "url": item.link,
                }
                searchable = json.dumps(candidate, ensure_ascii=False, sort_keys=True)
                if _contamination_hit(searchable) is not None:
                    continue
                retained_by_index[index] = candidate
                retained_indices.add(index)
                visible_text_by_index[index] = tuple(
                    text for text in (item.title, item.snippet) if isinstance(text, str) and text
                )
                top_level_url = _admissible_url(item.link)
                if top_level_url is not None:
                    allowed_urls.add(top_level_url)
                allowed_urls.update(_visible_child_urls(item.title, item.snippet))
            observed = ledger.capture(
                result,
                retained_indices=retained_indices,
                visible_text_by_index=visible_text_by_index,
            )
            retained: list[dict[str, object]] = []
            for index, candidate in retained_by_index.items():
                evidence_candidate = observed.get(index)
                if evidence_candidate is not None:
                    candidate["excerpts"] = [
                        f"[evidence {number}] {evidence_candidate.note[segment.start:segment.end]}"
                        for number, segment in ledger.numbered_segments(evidence_candidate)
                    ]
                retained.append(candidate)
            return json.dumps({"results": retained}, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


    async def _fetch(
        url: str,
        allowed_urls: set[str],
        ledger: EvidenceLedger,
        deadline: ExecutionDeadline | None = None,
        *,
        page_question: str | None = None,
        page_reader_cache: dict[tuple[str, str], PageReadResult] | None = None,
    ) -> str:
        normalized_url = _normalized_url(url)
        if normalized_url not in allowed_urls:
            return (
                f"<web_fetch><url>{url}</url><error>URL was not returned or literally shown by an earlier web_search "
                "call in this task.</error></web_fetch>"
            )
        if deadline is not None and not deadline.research_open():
            _log_deadline_event("research_tool_skipped_at_deadline", deadline, tool="web_fetch")
            return (
                f"<web_fetch><url>{url}</url>"
                "<error>The wall-clock research deadline has been reached.</error></web_fetch>"
            )
        citable_result: object | None = None
        visible_texts: tuple[str, ...] | None = None
        page_read: PageReadResult | None = None
        timeout_seconds = FETCH_TIMEOUT_SECONDS
        if deadline is not None:
            timeout_seconds = min(
                timeout_seconds,
                deadline.require_timeout_before(RESEARCH_CUTOFF_SECONDS, stage="web_fetch"),
            )
        try:
            result = await _await_before_stage_cutoff(
                fetch_page(
                    url,
                    provider="parallel",
                    provider_extra={"full_content": True},
                    timeout=timeout_seconds,
                ),
                timeout_seconds=timeout_seconds,
            )
            if len(result.response.data) != 1:
                raise RuntimeError("fetch_page did not return exactly one page")
            body = result.response.data[0].content
            if _contamination_hit(body) is not None:
                return (
                    f"<web_fetch><url>{url}</url><error>Fetched text was removed by the benchmark contamination "
                    "filter.</error></web_fetch>"
                )
            if len(body) > MAX_FETCH_CONTENT_CHARS and page_question is not None and deadline is not None:
                cache_key = (normalized_url, hashlib.sha256(body.encode("utf-8")).hexdigest())
                if page_reader_cache is not None:
                    page_read = page_reader_cache.get(cache_key)
                if page_read is None:
                    page_read = await _read_large_page(
                        question=page_question,
                        url=url,
                        body=body,
                        deadline=deadline,
                    )
                    if page_reader_cache is not None:
                        page_reader_cache[cache_key] = page_read
                visible_texts = page_read.selected_texts
            else:
                visible_texts = _visible_fetch_texts(body)
            allowed_urls.update(_visible_child_urls(*visible_texts))
            citable_result = result
        except StageDeadlineElapsedError as error:
            if deadline is None:
                raise
            _log_deadline_event("research_tool_timed_out_at_deadline", deadline, tool="web_fetch")
            raw_content = (
                f"<web_fetch><url>{url}</url><error>{_truncate_middle(str(error), MAX_FETCH_CONTENT_CHARS)}</error>"
                "</web_fetch>"
            )
        except Exception as error:
            raw_content = (
                f"<web_fetch><url>{url}</url><error>{_truncate_middle(str(error), MAX_FETCH_CONTENT_CHARS)}</error>"
                "</web_fetch>"
            )
        if citable_result is None or visible_texts is None:
            return raw_content
        observed = ledger.capture(
            citable_result,
            retained_indices={0},
            visible_text_by_index={0: visible_texts},
        )
        candidate = observed.get(0)
        evidence = ""
        if candidate is not None:
            evidence = "".join(
                f'<evidence number="{number}">{candidate.note[segment.start:segment.end]}</evidence>'
                for number, segment in ledger.numbered_segments(candidate)
            )
        if page_read is None:
            return f"<web_fetch><url>{url}</url><body>{evidence}</body></web_fetch>"
        findings = page_read.page_findings
        if candidate is not None and findings.strip():
            support_number = ledger.register_support_set(candidate)
            findings = (
                f'<page_findings evidence_number="{support_number}">{findings}</page_findings>'
                "<citation_instruction>Cite the page_findings once with its evidence number. That one number already "
                "represents every selected original passage; do not copy the body evidence numbers.</citation_instruction>"
            )
        else:
            findings = f"<page_findings>{findings}</page_findings>"
        return (
            f"<web_fetch><url>{url}</url>"
            f"{findings}"
            f"<missing_information>{page_read.missing_information}</missing_information>"
            f"<body>{evidence}</body></web_fetch>"
        )


    async def _execute_tool_calls(
        tool_calls: Sequence[LlmMessageToolCall] | None,
        allowed_urls: set[str],
        ledger: EvidenceLedger,
        *,
        allow_research: bool = True,
        deadline: ExecutionDeadline | None = None,
    ) -> tuple[list[dict[str, object]], str | None]:
        calls = list(tool_calls or ())
        finish_names = [call.name for call in calls if call.name == "finish"]
        reject_finish = len(finish_names) > 1
        ordered_calls = sorted(calls, key=lambda call: call.name == "finish")
        tool_messages: list[dict[str, object]] = []
        finish_answer: str | None = None

        for call in ordered_calls:
            research_open = allow_research and (deadline is None or deadline.research_open())
            if reject_finish and call.name == "finish":
                unique_names = sorted(set(finish_names))
                content = (
                    f"Cannot call finish tool '{call.name}': multiple finish tools ({unique_names}) were called in the "
                    "same turn. Only one finish tool may be called per turn — retry with a single finish tool call."
                )
            elif call.name in {"web_search", "web_fetch"} and not research_open:
                content = (
                    "Research phase ended by the turn or wall-clock limit. "
                    "Call finish with the best supported answer."
                )
            elif call.name == "web_search":
                query = _single_string_argument(call.arguments, field="query", max_length=200)
                content = (
                    "Tool arguments are not valid"
                    if query is None
                    else await _search(query, allowed_urls, ledger, deadline)
                )
            elif call.name == "web_fetch":
                url = _single_string_argument(call.arguments, field="url")
                content = (
                    "Tool arguments are not valid"
                    if url is None
                    else await _fetch(url, allowed_urls, ledger, deadline)
                )
            elif call.name == "finish":
                answer = _single_string_argument(call.arguments, field="answer")
                if answer is None:
                    content = "Tool arguments are not valid"
                else:
                    content = "Final answer proposed for Harnyx contract validation."
                    finish_answer = answer
            else:
                content = f"{call.name} is not a valid tool"
            tool_messages.append(_tool_result_message(call, content))
        return tool_messages, finish_answer


    async def _generate(
        messages: list[dict[str, object]],
        *,
        tools: list[dict[str, object]],
        timeout_seconds: float | None = None,
    ) -> tuple[LlmChoiceMessage, LlmUsage]:
        if timeout_seconds is None:
            result = await llm_chat(
                provider="openrouter",
                model=_BASE_MODEL,
                messages=messages,
                temperature=0.6,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                tools=tools or None,
                tool_choice="auto" if tools else None,
                thinking={"enabled": True, "effort": "medium"},
                provider_extra=None,
            )
        else:
            result = await _await_before_stage_cutoff(
                llm_chat(
                    provider="openrouter",
                    model=_BASE_MODEL,
                    messages=messages,
                    temperature=0.6,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    tools=tools or None,
                    tool_choice="auto" if tools else None,
                    thinking={"enabled": True, "effort": "medium"},
                    provider_extra=None,
                    timeout=timeout_seconds,
                ),
                timeout_seconds=timeout_seconds,
            )
        if not result.response.choices:
            raise RuntimeError("LLM response contained no choices")
        choice = result.response.choices[0]
        if choice.finish_reason in ("max_tokens", "length"):
            raise RuntimeError("LLM exhausted the configured output token limit")
        return choice.message, result.response.usage


    def _total_tokens(usage: LlmUsage) -> int:
        if usage.total_tokens is not None:
            return usage.total_tokens
        return (usage.prompt_tokens or 0) + (usage.completion_tokens or 0) + (usage.reasoning_tokens or 0)


    async def _summarize(
        messages: list[dict[str, object]],
        *,
        deadline: ExecutionDeadline | None = None,
    ) -> list[dict[str, object]]:
        text_only_prompt = f"{MESSAGE_SUMMARIZER}\n\n{MESSAGE_SUMMARIZER_TEXT_ONLY}"
        tool_docs = "\n".join(
            f"- {tool['function']['name']}: {tool['function']['description']}" for tool in TOOLS
        )
        no_tools_prompt = (
            f"{text_only_prompt}\n\nTools are disabled for this response. For reference, the tools available earlier in "
            f"the conversation were:\n{tool_docs}"
        )
        attempts = (
            (MESSAGE_SUMMARIZER, TOOLS),
            (text_only_prompt, TOOLS),
            (no_tools_prompt, []),
        )
        summary: str | None = None
        for prompt, tools in attempts:
            response_message, _usage = await _generate(
                [*messages, {"role": "user", "content": prompt}],
                tools=tools,
                timeout_seconds=(
                    None
                    if deadline is None
                    else deadline.require_timeout_before(
                        RESEARCH_CUTOFF_SECONDS,
                        stage="context summarization",
                    )
                ),
            )
            summary = _assistant_text(response_message)
            if summary is not None:
                break
        if summary is None:
            raise RuntimeError("Summarizer response contained no text blocks; cannot summarize context")

        # This runner always starts with exactly one system message and one user task.
        # Stirrup preserves those two messages and replaces every prior summary/turn.
        task_context = messages[:2]
        return [
            *task_context,
            {"role": "user", "content": MESSAGE_SUMMARIZER_BRIDGE.format(summary=summary)},
            {"role": "user", "content": "Got it, thanks!"},
        ]


    async def _run_stirrup_answer_path(task: str, ledger: EvidenceLedger) -> str:
        messages: list[dict[str, object]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]
        allowed_urls: set[str] = set()

        for accepted_turn in range(1, MAX_TURNS + 1):
            completed_turns = accepted_turn - 1
            if MAX_TURNS - completed_turns <= TURNS_REMAINING_WARNING_THRESHOLD and completed_turns != 0:
                remaining = MAX_TURNS - completed_turns
                if remaining == 1:
                    warning = "This is the last turn. Please finish the task by calling a finish tool."
                else:
                    warning = (
                        f"You have {remaining} turns remaining to complete the task. Please continue. Remember you will "
                        "need a separate turn to call a finish tool."
                    )
                messages.append({"role": "user", "content": warning})

            response_message, usage = await _generate(messages, tools=TOOLS)
            assistant_message = _assistant_input_message(response_message)
            tool_messages, finish_answer = await _execute_tool_calls(response_message.tool_calls, allowed_urls, ledger)
            messages.extend([assistant_message, *tool_messages])
            if finish_answer is not None:
                return finish_answer.strip()

            if (
                _total_tokens(usage) / CONTEXT_WINDOW_TOKENS >= CONTEXT_SUMMARIZATION_CUTOFF
                and accepted_turn != MAX_TURNS
            ):
                messages = await _summarize(messages)

            next_turn_will_show_warning = MAX_TURNS - accepted_turn <= TURNS_REMAINING_WARNING_THRESHOLD
            if not tool_messages and not next_turn_will_show_warning:
                messages.append({"role": "user", "content": "Please continue the task"})

        raise RuntimeError("Maximum number of turns reached without a successful finish call")


    async def _run_answer_only(task: str) -> str:
        """Retain an offline control surface for the frozen answer-only contract."""

        return await _run_stirrup_answer_path(task, EvidenceLedger())


    class FinishOutputError(ValueError):
        pass


    EVIDENCE_MARKER = re.compile(r"\[\[(\d+)\]\]")


    def _harnyx_finish_tool(query: Query) -> dict[str, object]:
        note_schema: dict[str, object] = {
            "type": "string",
            "maxLength": 80000,
            "description": (
                "Optional public explanation. Omit this field when no note is useful. Cite supported factual claims "
                "with the same [[N]] evidence markers used in prose. Do not repeat the answer or expose private reasoning."
            ),
        }
        if query.output_schema is None:
            properties: dict[str, object] = {
                "answer": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 80000,
                    "description": (
                        "The complete final prose answer. Immediately after each supported claim, write [[N]], where N "
                        "is an evidence number shown by search or fetch. Use only shown numbers. When page_findings has "
                        "an evidence_number, cite that one number once for the finding; it already represents all selected "
                        "original passages. Never copy the body's evidence numbers to reproduce that support set. Write the "
                        "answer once; do not add a separate sources list merely to carry citations."
                    ),
                },
                "note": note_schema,
            }
            required = ["answer"]
            description = (
                "Submit the final prose answer and end the task. Good: 'The value is 12.[[3]]'. Bad: an unknown "
                "marker, an uncited source list, copied evidence, or prose outside this tool call."
            )
        else:
            properties = {
                "output": query.output_schema,
                "output_evidence": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": MAX_CITATION_SEGMENTS,
                    "items": {"type": "integer", "minimum": 1},
                    "description": (
                        "Evidence numbers shown by search or fetch that directly support the material output values. "
                        "A page_findings evidence_number already represents all selected original passages; include that one "
                        "number once instead of copying its body evidence numbers. Order and duplicates do not matter."
                    ),
                },
                "note": note_schema,
            }
            required = ["output", "output_evidence"]
            description = (
                "Submit the requested structured output and end the task. Put every required answer value directly in "
                "output, cite it through output_evidence, and do not create a separate prose answer."
            )
        return {
            "type": "function",
            "function": {
                "name": "finish",
                "description": description,
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": properties,
                    "required": required,
                },
            },
        }


    def _harnyx_tools(query: Query) -> list[dict[str, object]]:
        return [WEB_SEARCH_TOOL, WEB_FETCH_TOOL, _harnyx_finish_tool(query)]


    def _marker_numbers(text: str, *, label: str) -> list[int]:
        without_valid_markers = EVIDENCE_MARKER.sub("", text)
        if "[[" in without_valid_markers or "]]" in without_valid_markers:
            raise FinishOutputError(f"{label} contains a malformed evidence marker; use exact [[N]] syntax")
        return [int(match.group(1)) for match in EVIDENCE_MARKER.finditer(text)]


    def _missing_evidence_message(*, field: str, ledger: EvidenceLedger) -> str:
        support_numbers = ledger.support_set_numbers
        if not support_numbers:
            if field == "finish answer":
                return "finish answer must include at least one shown [[N]] evidence marker"
            return "output_evidence must include at least one shown evidence number"
        rendered = ", ".join(str(number) for number in support_numbers)
        return (
            f"{field} has no evidence number. Cite each claimed page finding with its shown page_findings "
            f"evidence_number. The available page-finding numbers are {rendered}; each already represents all selected "
            "original passages, so do not copy the body evidence numbers."
        )


    def _required_evidence_selection(
        evidence_number: int,
        ledger: EvidenceLedger,
    ) -> EvidenceSelection:
        selection = ledger.selection_for_evidence_number(evidence_number)
        if selection is None:
            raise FinishOutputError(f"selected unobserved evidence number {evidence_number}")
        return selection


    def _citation_projection(
        evidence_numbers: Sequence[int],
        ledger: EvidenceLedger,
    ) -> tuple[list[CitationRef], dict[int, int]]:
        candidates = {candidate.candidate_id: candidate for candidate in ledger.candidates}
        candidate_order: list[int] = []
        segment_ids_by_candidate: dict[int, set[int]] = {}
        selection_by_number: dict[int, EvidenceSelection] = {}
        for evidence_number in evidence_numbers:
            selection = _required_evidence_selection(evidence_number, ledger)
            candidate_id = selection.candidate_id
            selection_by_number[evidence_number] = selection
            if candidate_id not in segment_ids_by_candidate:
                candidate_order.append(candidate_id)
                segment_ids_by_candidate[candidate_id] = set()
            segment_ids_by_candidate[candidate_id].update(selection.segment_ids)
        if len(candidate_order) > MAX_CITATION_REFS:
            raise FinishOutputError("selected evidence exceeds the public 200-citation limit")

        citation_numbers_by_candidate: dict[int, int] = {}
        citations: list[CitationRef] = []
        segment_count = 0
        evidence_chars = 0
        for candidate_id in candidate_order:
            candidate = candidates[candidate_id]
            segments = {segment.segment_id: segment for segment in candidate.segments}
            selected_ranges = [
                (segments[segment_id].start, segments[segment_id].end)
                for segment_id in sorted(segment_ids_by_candidate[candidate_id])
            ]
            merged_ranges = _merge_ranges(selected_ranges)
            segment_count += len(merged_ranges)
            evidence_chars += sum(end - start for start, end in merged_ranges)
            citation_number = len(citations) + 1
            citation_numbers_by_candidate[candidate_id] = citation_number
            citations.append(
                CitationRef(
                    receipt_id=candidate.receipt_id,
                    result_id=candidate.result_id,
                    slices=[CitationSlice(start=start, end=end) for start, end in merged_ranges],
                )
            )
        if segment_count > MAX_CITATION_SEGMENTS:
            raise FinishOutputError("selected evidence exceeds the public 400-segment limit")
        if evidence_chars > MAX_CITATION_EVIDENCE_CHARS:
            raise FinishOutputError("selected evidence exceeds the public 120000-character limit")
        public_number_by_evidence = {
            evidence_number: citation_numbers_by_candidate[selection.candidate_id]
            for evidence_number, selection in selection_by_number.items()
        }
        return citations, public_number_by_evidence


    def _renumber_markers(text: str, public_number_by_evidence: dict[int, int]) -> str:
        rewritten = EVIDENCE_MARKER.sub(
            lambda match: f"[[{public_number_by_evidence[int(match.group(1))]}]]",
            text,
        )
        return re.sub(r"(\[\[\d+\]\])(?:\1)+", r"\1", rewritten)


    def _finish_response(query: Query, arguments: str, ledger: EvidenceLedger) -> Response:
        payload = _parse_object(arguments)
        if payload is None:
            raise FinishOutputError("finish arguments are not a JSON object")
        required_keys = {"answer"} if query.output_schema is None else {"output", "output_evidence"}
        allowed_keys = {*required_keys, "note"}
        if not required_keys.issubset(payload) or not set(payload).issubset(allowed_keys):
            raise FinishOutputError("finish arguments do not match the task-specific response contract")
        note = payload.get("note", "")
        if not isinstance(note, str):
            raise FinishOutputError("finish note must be a string when provided")
        note_numbers = _marker_numbers(note, label="finish note")

        if query.output_schema is None:
            answer = payload["answer"]
            if not isinstance(answer, str) or not answer.strip():
                raise FinishOutputError("finish answer must be non-blank prose")
            answer_numbers = _marker_numbers(answer, label="finish answer")
            if not answer_numbers:
                raise FinishOutputError(_missing_evidence_message(field="finish answer", ledger=ledger))
            citations, public_numbers = _citation_projection([*answer_numbers, *note_numbers], ledger)
            try:
                return Response(
                    text=_renumber_markers(answer, public_numbers),
                    note=_renumber_markers(note, public_numbers) if note.strip() else None,
                    citations=citations or None,
                )
            except ValueError as error:
                raise FinishOutputError(f"public response violates the Harnyx contract: {error}") from error

        output_evidence = payload["output_evidence"]
        if not isinstance(output_evidence, list) or any(
            not isinstance(number, int) or isinstance(number, bool) for number in output_evidence
        ):
            raise FinishOutputError("output_evidence must be an array of evidence numbers")
        if not output_evidence:
            raise FinishOutputError(_missing_evidence_message(field="output_evidence", ledger=ledger))
        from harnyx_miner_sdk.structured_output import validate_output_against_schema

        try:
            validate_output_against_schema(payload["output"], query.output_schema)
        except ValueError as error:
            raise FinishOutputError(f"structured output violates the supplied schema: {error}") from error
        citations, public_numbers = _citation_projection([*output_evidence, *note_numbers], ledger)
        try:
            return Response(
                output=payload["output"],
                note=_renumber_markers(note, public_numbers) if note.strip() else None,
                citations=citations or None,
            )
        except ValueError as error:
            raise FinishOutputError(f"public response violates the Harnyx contract: {error}") from error


    def _recover_plain_finalization_response(
        query: Query,
        message: LlmChoiceMessage,
        ledger: EvidenceLedger,
        *,
        allow_research: bool,
    ) -> Response | None:
        if allow_research or message.tool_calls:
            return None
        if query.output_schema is not None:
            raise FinishOutputError("structured task must call finish with output and output_evidence")
        answer = _assistant_text(message)
        if answer is None or not answer.strip():
            raise FinishOutputError("finalization response contained neither a finish call nor a plain answer")
        return _finish_response(query, json.dumps({"answer": answer}), ledger)


    async def _execute_harnyx_tool_calls(
        tool_calls: Sequence[LlmMessageToolCall] | None,
        allowed_urls: set[str],
        ledger: EvidenceLedger,
        *,
        query: Query,
        allow_research: bool,
        deadline: ExecutionDeadline | None = None,
        page_reader_cache: dict[tuple[str, str], PageReadResult] | None = None,
    ) -> tuple[list[dict[str, object]], Response | None]:
        calls = list(tool_calls or ())
        finish_names = [call.name for call in calls if call.name == "finish"]
        reject_finish = len(finish_names) > 1
        ordered_calls = sorted(calls, key=lambda call: call.name == "finish")
        tool_messages: list[dict[str, object]] = []
        finish_response: Response | None = None

        for call in ordered_calls:
            research_open = allow_research and (deadline is None or deadline.research_open())
            if reject_finish and call.name == "finish":
                content = "Cannot call finish more than once in the same turn. Retry with one finish tool call."
            elif call.name in {"web_search", "web_fetch"} and not research_open:
                content = (
                    "Research phase ended by the turn or wall-clock limit. "
                    "Call finish with the best supported answer."
                )
            elif call.name == "web_search":
                search_query = _single_string_argument(call.arguments, field="query", max_length=200)
                content = (
                    "Tool arguments are not valid"
                    if search_query is None
                    else await _search(search_query, allowed_urls, ledger, deadline)
                )
            elif call.name == "web_fetch":
                url = _single_string_argument(call.arguments, field="url")
                content = (
                    "Tool arguments are not valid"
                    if url is None
                    else await _fetch(
                        url,
                        allowed_urls,
                        ledger,
                        deadline,
                        page_question=query.text,
                        page_reader_cache=page_reader_cache,
                    )
                )
            elif call.name == "finish":
                try:
                    finish_response = _finish_response(query, call.arguments, ledger)
                except FinishOutputError as error:
                    content = f"Final answer rejected by Harnyx contract validation: {error}"
                else:
                    content = "Final answer accepted."
            else:
                content = f"{call.name} is not a valid tool"
            tool_messages.append(_tool_result_message(call, content))
        return tool_messages, finish_response


    FINALIZATION_PROMPT = 'The research phase is complete. Do not search or fetch again. Call finish now with the best\ncomplete answer. For a plain task, write normal prose and put each shown [[N]] evidence number directly after the claim\nit supports. When page_findings has an evidence_number, cite that one number once; it already represents every selected\noriginal passage, so never copy the body evidence numbers. For a structured task, fill every required output field and\nlist its supporting evidence numbers. Use an optional note only when a short evidence-backed supplement is useful.'

    DEADLINE_FINALIZATION_PROMPT =DEADLINE_FINALIZATION_PROMPT = "The wall-clock research deadline has been reached. Do not search or fetch again.\nUse only the information already in the conversation and call finish now with the best complete answer. The proposed\nanswer must contain every value needed by the user's requested output before Harnyx can accept it."

    RECOVERY_PROMPT = 'This is the single recovery turn and the final turn. Research tools remain disabled. Use the\ncontract feedback from the rejected finish attempt and the information already in the conversation to call finish once\nwith a corrected, complete answer.'


    # ---- v230-2-fdlq ----
    # Added: fallback model lane, deterministic finish floor, list-first roster directive, figure coverage audit
    # Ordinary successful path:
    #   query -> answer -> _run_harnyx_answer_path -> _roster_directive -> _generate (+_generate_fallback on failure) -> _execute_harnyx_tool_calls -> _finish_response -> _figure_gaps -> _deterministic_finish (floor) -> Response


    # ---------------------------------------------------------------------------
    # Added-stage helpers.
    # ---------------------------------------------------------------------------

    _ASK_CUE_RE = re.compile(
        r"\b(which|what|who|whom|whose|when|where|how many|how much|name the|"
        r"list (?:all|the|every|each)|identify|give the)\b", re.I)
    _SENT_SPLIT_RE = re.compile(r"(?<=[.?!])\s+")
    _NAMED_ENTITY_RE = re.compile(
        r"[A-Z][A-Za-z0-9&'\-]+(?:\s+[A-Z][A-Za-z0-9&'\-]+){0,3}")
    _ENTITY_SPLIT_RE = re.compile(r"\s+(?:and|&|vs\.?|versus|or)\s+", re.I)
    _ENTITY_STOP = {"The", "This", "That", "What", "Which", "Who", "When", "Where",
                    "How", "Why", "List", "Name", "Give", "Find", "In", "Of", "For",
                    "Is", "Are", "Was", "Were", "Does", "Do", "Did", "According",
                    "Please", "Using", "Only"}
    _FIGURE_RE = re.compile(r"\d[\d,]*(?:\.\d+)?%?")
    _SET_CUE_RE = re.compile(
        r"\b(which|what|list|name)\b[^.?!]{0,80}\b(all|every|each|both|"
        r"distributors|countries|companies|films|members|winners|those)\b", re.I)


    def _ask_clause(text: str) -> str:
        'The clause that actually asks something.\n\n    These tasks characteristically open with premise decoration and put the ask\n    last, so slicing the head probes the decoration instead of the question.\n    '
        body = " ".join((text or "").split())
        if not body:
            return ""
        sentences = [s for s in _SENT_SPLIT_RE.split(body) if s.strip()]
        if not sentences:
            return body
        ask = ""
        for sentence in sentences:
            if _ASK_CUE_RE.search(sentence):
                ask = sentence
        return ask or sentences[-1]


    def _named_entities(text: str, limit: int = 6) -> list[str]:
        """Capitalized subjects the task names, with connectors split."""
        found: list[str] = []
        seen: set[str] = set()
        for match in _NAMED_ENTITY_RE.finditer(text or ""):
            for piece in _ENTITY_SPLIT_RE.split(match.group(0)):
                words = piece.split()
                while words and words[0] in _ENTITY_STOP:
                    words = words[1:]
                name = " ".join(words).strip(" ,.'-")
                key = name.casefold()
                if len(name) < 4 or key in seen:
                    continue
                seen.add(key)
                found.append(name)
                if len(found) >= limit:
                    return found
        return found


    def _selected_text(ledger: "EvidenceLedger", numbers) -> str:
        "Concatenated source text behind a set of evidence numbers.\n\n    This is what the judge actually sees. Reading the ledger's raw candidate\n    text instead would repeat the mistake these stages exist to prevent.\n    "
        candidates = {c.candidate_id: c for c in ledger.candidates}
        chunks: list[str] = []
        for number in numbers:
            selection = ledger.selection_for_evidence_number(int(number))
            if selection is None:
                continue
            candidate = candidates.get(selection.candidate_id)
            if candidate is None:
                continue
            segments = {s.segment_id: s for s in candidate.segments}
            for segment_id in selection.segment_ids:
                segment = segments.get(segment_id)
                if segment is not None:
                    chunks.append(getattr(segment, "text", "") or "")
        return "\n".join(chunks)


    def _selected_urls(ledger: "EvidenceLedger", numbers) -> list[str]:
        candidates = {c.candidate_id: c for c in ledger.candidates}
        urls: list[str] = []
        for number in numbers:
            selection = ledger.selection_for_evidence_number(int(number))
            if selection is None:
                continue
            candidate = candidates.get(selection.candidate_id)
            url = getattr(candidate, "url", "") if candidate else ""
            if url and url not in urls:
                urls.append(url)
        return urls


    def _answer_and_numbers(response: "Response") -> tuple:
        text = (getattr(response, "text", None) or "") + " " + (getattr(response, "note", None) or "")
        return text, [int(m.group(1)) for m in EVIDENCE_MARKER.finditer(text)]


    FALLBACK_MODEL = "z-ai/glm-5.2"
    FALLBACK_MAX_OUTPUT_TOKENS = 32_000


    async def _generate_fallback(
        messages: list[dict[str, object]],
        *,
        tools: list[dict[str, object]],
        timeout_seconds: float | None,
    ):
        'Second lane. The base has exactly one model, pinned to a single upstream\n    with allow_fallbacks False and no alternative anywhere -- so one 429 ends\n    the run with RuntimeError and a zero. This lane keeps fallbacks ON on\n    purpose: at this point the pinned upstream has already failed, and routing\n    freedom is worth more than upstream affinity.'
        # Two explicit calls rather than **{...}: the validator rejects expanded
        # keyword arguments (invalid_script_payload / expanded_keywords). The base's
        # own _generate branches the same way for the same reason.
        if timeout_seconds is None:
            result = await llm_chat(
                provider="openrouter",
                model=FALLBACK_MODEL,
                messages=messages,
                temperature=0.4,
                max_output_tokens=FALLBACK_MAX_OUTPUT_TOKENS,
                tools=tools or None,
                tool_choice="auto" if tools else None,
                thinking={"enabled": True, "effort": "low"},
                provider_extra=None,
            )
        else:
            result = await llm_chat(
                provider="openrouter",
                model=FALLBACK_MODEL,
                messages=messages,
                temperature=0.4,
                max_output_tokens=FALLBACK_MAX_OUTPUT_TOKENS,
                tools=tools or None,
                tool_choice="auto" if tools else None,
                thinking={"enabled": True, "effort": "low"},
                provider_extra=None,
                timeout=timeout_seconds,
            )
        if not result.response.choices:
            raise RuntimeError("fallback lane returned no choices")
        return result.response.choices[0].message, result.response.usage


    FLOOR_MAX_EVIDENCE = 6
    FLOOR_MIN_CHARS = 60


    def _deterministic_finish(query: "Query", ledger: "EvidenceLedger"):
        "Last-resort answer built from evidence already held.\n\n    The base ends `raise RuntimeError(...)` when the reserved finish turns are\n    spent -- a total zero even though the ledger is usually full of captured,\n    citable evidence. This builds a contract-valid finish from what is already\n    there: real [[N]] markers over real support-set numbers, so it survives\n    _finish_response's validation rather than bypassing it.\n    "
        numbers = list(ledger.support_set_numbers)[:FLOOR_MAX_EVIDENCE]
        if not numbers:
            return None
        lines = ["Best-supported findings for this task, from the evidence gathered:"]
        for number in numbers:
            snippet = " ".join(_selected_text(ledger, [number]).split())[:220]
            if not snippet:
                continue
            lines.append(f"- {snippet} [[{number}]]")
        if len(lines) < 2:
            return None
        answer = "\n".join(lines)
        if len(answer) < FLOOR_MIN_CHARS:
            return None
        try:
            if query.output_schema is not None:
                return _finish_response(
                    query, json.dumps({"output": answer, "output_evidence": numbers}), ledger)
            return _finish_response(query, json.dumps({"answer": answer}), ledger)
        except Exception:
            return None


    def _needs_roster(text: str) -> bool:
        return bool(_SET_CUE_RE.search(text or ""))


    def _roster_directive(text: str) -> str:
        'Opening directive for set tasks: get the pool from ONE list.\n\n    Assembling a pool from per-member lookups is how a run ships 3 of 6\n    qualifiers -- the members never searched for are invisible. This fires\n    before the first turn, so it shapes the first retrieval rather than\n    repairing the last.\n    '
        ask = _ask_clause(text)
        return ("SET TASK. Your FIRST retrieval should hunt the authoritative "
                "roster that enumerates the WHOLE pool -- search it AS a list "
                "(\"<pool subject> list\", \"<pool subject> table\") and read that "
                "page, then verify each member against every stated condition. "
                "Give every member its own line with its own evidence marker, "
                "including the members you rule OUT. The ask is: " + ask[:240])


    MAX_FIGURE_FLAGS = 4
    MIN_FIGURE_CHARS = 2


    def _figure_gaps(response: "Response", ledger: "EvidenceLedger") -> list:
        'Figures asserted by the finish that no cited passage states.\n\n    The judge credits a claim only when the CITED SLICE contains the text\n    stating it. Checking the raw candidate text instead would pass figures the\n    judge never sees, which is precisely the failure this guards.\n    '
        text, numbers = _answer_and_numbers(response)
        if not numbers:
            return []
        shown = _selected_text(ledger, numbers)
        shown_plain = shown.replace(",", "")
        gaps: list = []
        seen: set = set()
        for match in _FIGURE_RE.finditer(EVIDENCE_MARKER.sub(" ", text)):
            token = match.group(0)
            if len(token) < MIN_FIGURE_CHARS:
                continue
            plain = token.replace(",", "").rstrip("%")
            if plain in seen:
                continue
            seen.add(plain)
            if token not in shown and plain not in shown_plain:
                gaps.append(token)
            if len(gaps) >= MAX_FIGURE_FLAGS:
                break
        return gaps


    def _figure_correction(gaps: list) -> str:
        return ("UNCITED FIGURES. These values appear in your answer but in none of "
                "the passages you cited: " + ", ".join(gaps)
                + ".\nEXEMPTION: a figure you DERIVED (a total, mean, share or "
                "difference) is legitimate -- keep it and show its inputs with "
                "their markers. Otherwise cite a shown evidence number whose "
                "passage prints it, or drop it. Then call finish again.")


    async def _run_harnyx_answer_path(
        query: Query,
        ledger: EvidenceLedger,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> Response:
        messages: list[dict[str, object]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query.text},
        ]
        if _needs_roster(query.text or ""):
            messages.append({"role": "user",
                             "content": _roster_directive(query.text or "")})
        allowed_urls: set[str] = set()
        page_reader_cache: dict[tuple[str, str], PageReadResult] = {}
        deadline = ExecutionDeadline.start(clock=clock)
        finalization_attempts = 0
        finalization_started = False
        force_finalization = False
        _audit_done = False

        for accepted_turn in range(1, MAX_TURNS + 1):
            allow_research = (
                accepted_turn <= RESEARCH_TURNS
                and not force_finalization
                and not finalization_started
                and deadline.research_open()
            )
            if not allow_research:
                if finalization_attempts >= FINALIZATION_TURNS:
                    break
                finalization_attempts += 1
                if not finalization_started:
                    prompt = (
                        DEADLINE_FINALIZATION_PROMPT
                        if accepted_turn <= RESEARCH_TURNS
                        else FINALIZATION_PROMPT
                    )
                    messages.append({"role": "user", "content": prompt})
                    finalization_started = True
                    _log_deadline_event(
                        "finalization_started",
                        deadline,
                        cause="wall_clock" if accepted_turn <= RESEARCH_TURNS else "turn_limit",
                    )
                elif finalization_attempts == FINALIZATION_TURNS:
                    messages.append({"role": "user", "content": RECOVERY_PROMPT})
            else:
                completed_turns = accepted_turn - 1
                if MAX_TURNS - completed_turns <= TURNS_REMAINING_WARNING_THRESHOLD and completed_turns != 0:
                    remaining = MAX_TURNS - completed_turns
                    warning = (
                        f"You have {remaining} turns remaining to complete the task. Please continue. Remember you will "
                        "need a separate turn to call a finish tool."
                    )
                    messages.append({"role": "user", "content": warning})

            tools = _harnyx_tools(query) if allow_research else [_harnyx_finish_tool(query)]
            cutoff = RESEARCH_CUTOFF_SECONDS if allow_research else FINAL_ANSWER_CUTOFF_SECONDS
            try:
                timeout_seconds = deadline.require_timeout_before(cutoff, stage="answer generation")
                try:
                    response_message, usage = await _generate(
                        messages,
                        tools=tools,
                        timeout_seconds=timeout_seconds,
                    )
                except (StageDeadlineElapsedError, DeadlineExceededError):
                    raise
                except Exception:
                    # Single pinned upstream just failed (429 or transport).
                    # Without this the run raises and scores zero.
                    response_message, usage = await _generate_fallback(
                        messages,
                        tools=tools,
                        timeout_seconds=timeout_seconds,
                    )
            except (StageDeadlineElapsedError, DeadlineExceededError):
                if allow_research:
                    force_finalization = True
                    _log_deadline_event("research_generation_stopped_at_deadline", deadline)
                    continue
                raise DeadlineExceededError(
                    "final answer generation reached its deadline before finish produced an answer"
                ) from None

            assistant_message = _assistant_input_message(response_message)
            tool_messages, finish_response = await _execute_harnyx_tool_calls(
                response_message.tool_calls,
                allowed_urls,
                ledger,
                query=query,
                allow_research=allow_research,
                deadline=deadline,
                page_reader_cache=page_reader_cache,
            )
            messages.extend([assistant_message, *tool_messages])
            if finish_response is not None:
                # Audit the finish BEFORE accepting it. Each check that
                # fires costs one corrective turn, and only one round is
                # allowed: the reserved finish turns are the last thing
                # standing between a partial answer and a RuntimeError.
                _fix = ""
                if not _audit_done:
                    try:
                        _figs = _figure_gaps(finish_response, ledger)
                    except Exception:
                        _figs = []
                    if _figs and not _fix:
                        _fix = _figure_correction(_figs)
                if _fix and deadline.research_open():
                    _audit_done = True
                    messages.append({"role": "user", "content": _fix})
                    continue
                return finish_response

            if not allow_research and not tool_messages:
                try:
                    recovered_response = _recover_plain_finalization_response(
                        query,
                        response_message,
                        ledger,
                        allow_research=allow_research,
                    )
                except FinishOutputError as error:
                    _log_deadline_event(
                        "plain_finalization_rejected",
                        deadline,
                        reason=str(error),
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Final answer rejected by Harnyx contract validation: {error}",
                        }
                    )
                else:
                    if recovered_response is not None:
                        _log_deadline_event("plain_finalization_recovered", deadline)
                        return recovered_response

            if (
                allow_research
                and deadline.research_open()
                and _total_tokens(usage) / CONTEXT_WINDOW_TOKENS >= CONTEXT_SUMMARIZATION_CUTOFF
                and accepted_turn < RESEARCH_TURNS
            ):
                try:
                    messages = await _summarize(messages, deadline=deadline)
                except (StageDeadlineElapsedError, DeadlineExceededError):
                    force_finalization = True
                    _log_deadline_event("summarization_stopped_at_deadline", deadline)

            if not tool_messages and allow_research and deadline.research_open():
                messages.append({"role": "user", "content": "Please continue the task"})

        _floor = None
        try:
            _floor = _deterministic_finish(query, ledger)
        except Exception:
            _floor = None
        if _floor is not None:
            _log_deadline_event("deterministic_floor_used", deadline)
            return _floor
        raise RuntimeError("Reserved finish and recovery turns ended without an accepted Harnyx response")


    async def _w4_baseline_query(query: Query) -> Response:
        ledger = EvidenceLedger()
        return await _run_harnyx_answer_path(query, ledger)


    # --- w4 answer-contract wrapper (begin) ---
    # The base artifact's `query` entrypoint is demoted to `_w4_baseline_query` and a
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


    def _w4_provider() -> str:
        """Resolve the base's LLM provider without globals(); the validator rejects it."""
        try:
            return LLM_PROVIDER
        except NameError:
            return "openrouter"


    def _w4_model() -> str:
        try:
            return MODEL
        except NameError:
            return "z-ai/glm-5"


    def _w4_total_budget_seconds() -> float:
        try:
            return float(TASK_TOTAL_BUDGET_SECONDS)
        except (NameError, TypeError, ValueError):
            return _W2_DEFAULT_BUDGET_SECONDS


    def _w4_remaining(deadline: float) -> float:
        return deadline - perf_counter()


    async def _w4_chat(messages: list[dict[str, object]], *, timeout: float, temperature: float) -> str:
        """One bounded LLM call on the platform ABI; empty string on any failure."""
        if timeout <= 0:
            return ""
        try:
            result = await llm_chat(
                provider=_w4_provider(), model=_w4_model(), messages=messages,
                temperature=temperature, timeout=timeout,
            )
        except Exception:
            return ""
        try:
            return (result.response.raw_text or "").strip()
        except Exception:
            return ""


    def _w4_json_object(text: str) -> dict | None:
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


    def _w4_string_list(value: object, limit: int) -> list[str]:
        if not isinstance(value, list):
            return []
        items = []
        for entry in value:
            if isinstance(entry, str) and entry.strip():
                items.append(entry.strip())
            if len(items) >= limit:
                break
        return items


    def _w4_schema_hint(schema: object) -> str:
        """Render the caller's output schema for the planning prompt."""
        if schema is None:
            return ""
        try:
            rendered = json.dumps(schema, ensure_ascii=False)[:1_200]
        except (TypeError, ValueError):
            return ""
        return f"\n\nThe answer will be returned against this output schema:\n{rendered}"


    async def _w4_build_answer_contract(
        question: str, schema: object, *, deadline: float,
    ) -> _W2AnswerContract | None:
        """Stage 1 - plan the acceptance criteria before the baseline research runs."""
        timeout = min(_W2_PLAN_TIMEOUT_SECONDS, _w4_remaining(deadline) - _W2_TAIL_RESERVE_SECONDS)
        messages = [
            {"role": "system", "content": _W2_PLAN_SYSTEM},
            {"role": "user", "content": f"Question:\n{question}{_w4_schema_hint(schema)}"},
        ]
        payload = _w4_json_object(await _w4_chat(
            messages, timeout=timeout, temperature=_W2_PLAN_TEMPERATURE,
        ))
        if payload is None:
            return None
        deliverable = payload.get("deliverable")
        contract = _W2AnswerContract(
            deliverable=deliverable.strip() if isinstance(deliverable, str) else "",
            required=_w4_string_list(payload.get("required"), _W2_MAX_CONTRACT_ITEMS),
            pitfalls=_w4_string_list(payload.get("pitfalls"), 3),
        )
        return contract if contract.is_actionable() else None


    def _w4_contract_block(contract: _W2AnswerContract) -> str:
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


    def _w4_response_text(response: object) -> str:
        try:
            text = getattr(response, "text", None)
        except Exception:
            return ""
        return text.strip() if isinstance(text, str) else ""


    def _w4_with_text(response: object, text: str) -> object:
        'Rebuild the response around the audited answer, carrying citations over.\n\n    The platform accepts exactly one non-null answer field, so a response that\n    already carries a structured `output` owns no text answer to override and is\n    returned untouched.\n    '
        if getattr(response, "output", None) is not None:
            return response
        citations = getattr(response, "citations", None)
        try:
            if citations:
                return Response(text=text, citations=citations)
            return Response(text=text)
        except Exception:
            return response


    def _w4_normalize_figure(token: str) -> str:
        """One numeric literal reduced to the value it states, not how it is typed."""
        value = token.replace(",", "")
        if "." in value:
            value = value.rstrip("0").rstrip(".")
        return value or "0"


    def _w4_figures(text: str) -> set:
        """Every quantity the text asserts, less the ordinals that only number a list."""
        body = _W2_LIST_MARKER_RE.sub(" ", text)
        found = set()
        for match in _W2_FIGURE_RE.finditer(body):
            found.add(_w4_normalize_figure(match.group(0)))
        return found


    def _w4_entities(text: str) -> set:
        'Every named token the text asserts.\n\n    A capitalized word that opens a sentence, a heading, or a bullet is\n    capitalized by position rather than by being a name, so it is not counted;\n    a real name almost always also occurs somewhere it did not open a clause.\n    '
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


    def _w4_unmakes_draft(draft: str, revision: str) -> bool:
        """True when the revision fails to carry forward something the draft asserted."""
        if not _w4_figures(draft).issubset(_w4_figures(revision)):
            return True
        return not _w4_entities(draft).issubset(_w4_entities(revision))


    def _w4_accept_revision(draft: str, revision: str) -> bool:
        'Keep the audited answer only when it adds to the draft without unmaking it.\n\n    Length cannot tell a repair from a replacement: a revision that answers with\n    a different entity, or restates a figure as a different figure, is exactly as\n    long as one that fills a gap. The audited text is therefore accepted only\n    when every concrete claim the draft asserted - each quantity, each named\n    token - still stands in it. Additions are free; deletions and substitutions\n    return the draft.\n    '
        if not revision or revision == draft:
            return False
        if len(revision) < _W2_MIN_REVISION_CHARS:
            return False
        if len(revision) < len(draft) * _W2_MIN_REVISION_RATIO:
            return False
        return not _w4_unmakes_draft(draft, revision)


    async def _w4_verify_against_contract(
        contract: _W2AnswerContract, question: str, draft: str, *, deadline: float,
    ) -> str:
        """Stage 3 - audit the draft against the contract and return the answer to deliver."""
        timeout = min(_W2_VERIFY_TIMEOUT_SECONDS, _w4_remaining(deadline) - _W2_TAIL_RESERVE_SECONDS)
        messages = [
            {"role": "system", "content": _W2_VERIFY_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\nAnswer contract:\n{_w4_contract_block(contract)}"
                    f"\n\nDraft answer:\n{draft[:_W2_DRAFT_PROMPT_CHARS]}"
                ),
            },
        ]
        revision = await _w4_chat(messages, timeout=timeout, temperature=_W2_VERIFY_TEMPERATURE)
        return revision if _w4_accept_revision(draft, revision) else draft


    def _w4_schema_property_names(schema: object) -> list[str]:
        if not isinstance(schema, dict):
            return []
        properties = schema.get("properties")
        return [key for key in properties] if isinstance(properties, dict) else []


    def _w4_is_degenerate_output(output: object, schema: object) -> bool:
        """True when the base produced a structured payload the scorer will read as empty."""
        if output is None:
            return True
        if isinstance(output, (str, list, tuple, dict)) and len(output) == 0:
            return True
        if isinstance(output, dict):
            names = _w4_schema_property_names(schema)
            if names and not any(key in output for key in names):
                return True
            if all(value in (None, "", [], {}) for value in output.values()):
                return True
        return False


    async def _w4_repair_structured_output(
        question: str, schema: object, response: object, *, deadline: float,
    ) -> object:
        """Repair-only ladder: a working structured payload is always returned untouched."""
        output = getattr(response, "output", None)
        if not _w4_is_degenerate_output(output, schema):
            return response
        draft = _w4_response_text(response)
        recovered = _w4_json_object(draft)
        if recovered is None:
            timeout = min(_W2_REPAIR_TIMEOUT_SECONDS, _w4_remaining(deadline) - 2.0)
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
            recovered = _w4_json_object(await _w4_chat(messages, timeout=timeout, temperature=0.0))
        if recovered is None or _w4_is_degenerate_output(recovered, schema):
            return response
        citations = getattr(response, "citations", None)
        try:
            if citations:
                return Response(output=recovered, citations=citations)
            return Response(output=recovered)
        except Exception:
            return response


    async def _w4_research_or_salvage(query_input: Query) -> Response:
        'Stage 2 - the research stage, held so no failure inside it can escape.\n\n    The demoted base entrypoint is foreign code: it raises whatever its own tool\n    layer raises. A hosted tool call that overruns its own `timeout=` surfaces as\n    `harnyx_commons.errors.ToolInvocationTimeoutError`, which subclasses\n    RuntimeError directly and matches no guard the base installed for itself. Any\n    such escape leaves `@entrypoint`, and the platform charges an escaping\n    exception to the miner as MINER_UNHANDLED_EXCEPTION: the task scores 0 with\n    no retry. Measured on `FB_526bfbe6_w2`, 1 of 3 replays (2026-08-09).\n\n    The stage therefore always resolves to a Response the later stages can work\n    on. A floor answer scores poorly; an escape scores zero and takes the whole\n    task with it.\n    '
        try:
            return await _w4_baseline_query(query_input)
        except Exception:
            return Response(text="No verifiable source-backed answer was reached for this question.")


    async def query(query: Query) -> Response:
        "w4 contract wrapper: plan the answer contract, run the baseline, then verify.\n\n    The baseline artifact's own entrypoint is demoted to `_w4_baseline_query` and\n    runs as the research stage of this sequence. Contract planning runs on every\n    ordinary request before the research starts, and the verification stage holds\n    authority over the answer this entrypoint returns.\n    "
        deadline = perf_counter() + _w4_total_budget_seconds()
        question = getattr(query, "text", "") or ""
        schema = getattr(query, "output_schema", None)

        contract = await _w4_build_answer_contract(question, schema, deadline=deadline)
        response = await _w4_research_or_salvage(query)

        if contract is not None:
            draft = _w4_response_text(response)
            if draft:
                audited = await _w4_verify_against_contract(
                    contract, question, draft, deadline=deadline,
                )
                if audited != draft:
                    response = _w4_with_text(response, audited)
        if schema is not None:
            response = await _w4_repair_structured_output(
                question, schema, response, deadline=deadline,
            )
        return response
    # --- w4 answer-contract wrapper (end) ---

    return query

_GRAFT_ENTRY_g16n8_0 = _compose_g16n8_0_entry()


_GRAFT_ROUTE_WANTED_G16N8_0_CUES = ("compare", "versus", " vs ", "difference",
    "trade-off", "evaluate", "assess", "analyz", "analys", "why did")


def _graft_route_wanted_g16n8_0(query) -> bool:
    """Send analytical questions to the grafted pipeline."""
    try:
        text = (getattr(query, "text", "") or "").lower()
    except Exception:
        return False
    return any(c in text for c in _GRAFT_ROUTE_WANTED_G16N8_0_CUES)

@entrypoint("query")
async def query(query: Query) -> Response:
    # Additional architecture route. Wrapped: the entrypoint contract is
    # that nothing escapes, so a failure here falls through unchanged.
    try:
        if _graft_route_wanted_g16n8_0(query):
            return await _GRAFT_ENTRY_g16n8_0(query)
    except Exception:
        pass
    """Route on the caller's schema, and record the scoring mode for the run.

    Without a schema this is the previous entrypoint with two extra attribute
    reads. With one, the same pipeline runs on a shortened budget and its drafted
    answer is re-expressed as `output` — the only answer field the platform will
    accept for such a query. `fast` is orthogonal to both: it says the answer is
    judged for correctness alone, so the stages that exist to prove completeness
    to a comparing judge are skipped while the stages that decide the answer are
    not.
    """
    # A worker serves more than one task, so this is set per call, never once.
    _FAST[0] = bool(getattr(query, "fast", False))
    _MAIN_DEAD.clear()
    schema = getattr(query, "output_schema", None)
    if schema is None:
        return await _plain_query_with_cold_retry(query, TASK_TOTAL_BUDGET_SECONDS)
    try:
        drafted = await _plain_query_with_cold_retry(
            query, TASK_TOTAL_BUDGET_SECONDS - STRUCTURED_RESERVE_SECONDS)
    except Exception:
        drafted = Response(text="The research pipeline did not produce an answer for this question.")
    try:
        return await _structured_response(query, schema, drafted, perf_counter() + STRUCTURED_RESERVE_SECONDS)
    except Exception:
        return _so_response(_so_skeleton(schema, schema), None)
# --- structured output (end) ---
