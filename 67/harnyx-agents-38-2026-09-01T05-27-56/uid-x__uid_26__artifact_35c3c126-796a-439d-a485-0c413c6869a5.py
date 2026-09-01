"""uid_195 research agent - variant 09.

Two stages added to the uid_195 pipeline, one taken from each of two
validator_reference candidates:
  uid   2 - claim-level verify-and-repair (verify)
  uid  89 - citation slice backfill (backfill)

The primary controller, the evidence state (_ResultIndex) and the amend
stage that decides the delivered answer are unchanged. All model calls go
through LLM_PROVIDER = "openrouter".
"""
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
TASK_TOTAL_BUDGET_SECONDS = 270.0
FETCH_TIMEOUT_SECONDS = 15.0
FETCH_RETRY_ATTEMPTS = 2
MAX_RETRY_ATTEMPTS_PER_TURN = 2
SEARCH_TIMEOUT_SECONDS = 20.0
LLM_TURN_TIMEOUT_SECONDS = 90.0

RESEARCH_TURN_CAP = 10
RESEARCH_TIME_CAP_SECONDS = 140.0
CHECKPOINT_TOOL_TURNS = 2
FINAL_RESERVE_SECONDS = 55.0
FINAL_RETRY_MIN_SECONDS = 25.0

COVERAGE_LIST_MAX = 8
MIN_ANSWER_CHARS = 400
CITATION_ANCHOR_CONTEXT_CHARS = 160
TOOL_RESULT_INLINE_CHARS = 3000
SEARCH_EXCERPT_INLINE_CHARS = 380
HARD_MIN_ANSWER_CHARS = 200
CITATION_BUDGET_CHARS = 90_000
CITATION_GAP_FILL_MAX_CHARS = 4_000
COMMIT_DIGEST_NOTE_CHARS = 2_600
CITATION_ANCHOR_LEAD_CHARS = 800
COMMIT_DIGEST_SOURCES_MAX = 16
COMMIT_DIGEST_TOTAL_CHARS = 64_000
COMMIT_DIGEST_IDENTITY_CHARS = 320

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


def _page_spans(note: str, terms: list[str]) -> list[tuple[int, int]]:
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
    if len(note) > head_end:
        spans.extend(_best_windows(
            note, terms, PAGE_WINDOW_CHARS, PAGE_WINDOWS_PER_PAGE, skip_before=head_end,
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
    r"""The page's own markdown escapes end up inside the model's JSON string and
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
    spans = _page_spans(note, terms)
    try:
        spans = spans + await _extract_spans(question, note, budget)
    except Exception:
        pass
    shown = index.surface(n, spans)
    if not shown:
        shown = index.spans(n) or [(0, min(TOOL_RESULT_INLINE_CHARS, len(note)))]
    body = _render_spans(note, shown)
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
) -> list[tuple[int, int]]:
    """Which parts of the regions read from a source fit in its allowance.

    When everything read fits, everything read is shown. When it does not, the
    choice is made the same way the regions were chosen in the first place — by
    where the question's own words actually occur — rather than by keeping the
    first N characters, which is how a figure a few hundred characters into a
    long region gets dropped on the way to the answer.
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
    scored: list[tuple[int, tuple[int, int]]] = []
    for start, end in spans:
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
        budgeted = _digest_spans(note, spans, terms, window)
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
    checkpoint = _checkpoint_message(candidates, index)
    if notice:
        checkpoint = notice + "\n\n" + checkpoint
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
        {"role": "user", "content": digest + "\n\n" + checkpoint},
    ]
    if draft:
        messages.append({"role": "assistant", "content": draft})
    messages.append({"role": "user", "content": COMMIT_MESSAGE + suffix})
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



# --- added stage kit ------------------------------------------------------
# Shared plumbing for the added stages: an evidence view that also shows
# search-only results, the adoption guard the amend stage uses, one bounded
# rewrite call, and one bounded targeted search. Every stage below is invoked
# by name from _plain_query; nothing here selects a callable at run time.

STAGE_SYSTEM = (
    "You issue the corrected final version of a research answer. You are given "
    "the question, the current draft, the evidence that was actually read, and "
    "one specific defect to repair.\n"
    "Rules:\n"
    "1. Repair only the named defect. Keep everything else the draft gets right, "
    "in its structure and order.\n"
    "2. Every figure you state must come from the evidence below and must carry "
    "its [n] marker. Never invent a marker number that is not in the evidence.\n"
    "3. If the question prescribes an exact output format, keep the FIRST line "
    "exactly that prescribed output.\n"
    "4. Never answer that something is unavailable when a passage below states it.\n"
    "5. Output the complete answer and nothing else - no preamble, no notes about "
    "what you changed. If the defect does not actually apply, return the draft "
    "verbatim."
)

STAGE_FIGURE_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
STAGE_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
STAGE_ITEM_RE = re.compile(r"^\s*(?:[-*\u2022]|\d{1,2}[.)])\s+\S", re.MULTILINE)
STAGE_ENTITY_RE = re.compile(r"\b[A-Z][\w&.-]*(?:\s+[A-Z][\w&.-]*)*")
STAGE_URL_RE = re.compile(r"^\s*url:\s*(\S+)", re.MULTILINE)
STAGE_WORD_NUMBERS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
STAGE_AUTHORITY_SUFFIXES = (".gov", ".mil", ".int", ".edu", ".gov.uk", ".go.jp", ".gc.ca")
STAGE_AUTHORITY_HOSTS = (
    "europa.eu", "who.int", "worldbank.org", "imf.org", "oecd.org", "un.org",
    "eurostat", "census.gov", "sec.gov", "bls.gov", "ecb.europa.eu", "iea.org",
)


def _stage_evidence(index: _ResultIndex, limit: int) -> str:
    """The passages this run read, plus the excerpts of search-only results.

    _serializer_evidence shows surfaced spans only, so a source a stage brought
    in through one targeted search would be invisible to the rewrite that stage
    exists to drive. This view falls back to the head of the note for a source
    that has no spans yet.
    """
    parts: list[str] = []
    used = 0
    for n in range(1, index.max_number() + 1):
        meta = index.get(n)
        if meta is None or not meta.get("citable"):
            continue
        spans = index.spans(n)
        if spans:
            body = _render_spans(meta.get("note") or "", spans)
        else:
            body = (meta.get("note") or "")[:STAGE_UNSPANNED_CHARS]
        if not body.strip():
            continue
        chunk = f"[{n}] {(meta.get('title') or meta.get('url') or '')[:160]}\n{body}"
        room = limit - used
        if room <= 0:
            break
        parts.append(chunk[:room])
        used += min(len(chunk), room)
    return "\n\n".join(parts)


def _stage_keep(answer: str, revised: str) -> bool:
    """The amend stage's adoption guard, applied to every added stage.

    A repair is worth taking only when it is still a complete answer that keeps
    its citations; otherwise a whole answer gets traded for a fragment.
    """
    if not revised:
        return False
    if len(revised) < max(AMEND_MIN_KEEP_CHARS, int(len(answer) * 0.5)):
        return False
    if TOOL_MARKUP_RE.search(revised) or PSEUDO_CALL_RE.search(revised):
        return False
    if any(m in revised.lower()[:200] for m in ABSTENTION_MARKERS):
        return False
    if BRACKET_RE.search(answer) and not BRACKET_RE.search(revised):
        return False
    if _needs_forced_retry(revised):
        return False
    return True


async def _stage_rewrite(
    question: str, answer: str, index: _ResultIndex, directive: str, deadline: float,
) -> str:
    budget = deadline - perf_counter() - 2
    if budget <= STAGE_REWRITE_MIN_SECONDS:
        return answer
    evidence = _stage_evidence(index, STAGE_EVIDENCE_CHARS)
    messages = [
        {"role": "system", "content": STAGE_SYSTEM},
        {"role": "user", "content": (
            f"QUESTION:\n{question}\n\n"
            f"DRAFT ANSWER:\n{answer[:AMEND_CONTEXT_CHARS]}\n\n"
            f"EVIDENCE READ:\n{evidence}\n\n"
            f"DEFECT TO REPAIR:\n{directive}\n\n"
            "Return the complete final answer now."
        )},
    ]
    try:
        result = await llm_chat(
            provider=LLM_PROVIDER, model=MODEL, messages=messages, temperature=0.1,
            thinking=LlmThinkingConfig(enabled=False),
            timeout=min(STAGE_REWRITE_TIMEOUT, budget),
        )
        revised = (result.response.raw_text or "").strip()
    except Exception:
        revised = ""
    if _stage_keep(answer, revised):
        return revised
    return answer


async def _stage_search(text: str, index: _ResultIndex, deadline: float) -> bool:
    """One targeted search, folded into the same evidence index."""
    if not text.strip():
        return False
    if deadline - perf_counter() < STAGE_SEARCH_MIN_SECONDS:
        return False
    try:
        await _run_search_web(text[:220], index)
        return True
    except Exception:
        return False


def _stage_terms_query(terms: list[str], extra: str) -> str:
    return (" ".join(terms[:6]) + " " + extra).strip()


def _stage_note_text(index: _ResultIndex) -> str:
    return index.all_note_text().lower()


def _stage_digits(value: str) -> str:
    return value.replace(",", "").replace(" ", "")
# --- added stage kit (end) ------------------------------------------------

# --- added stage budgets --------------------------------------------------
# Every added stage is opportunistic: it runs only when the tail of the
# task budget can pay for it, and never at the expense of the amend stage
# that decides what is delivered.
STAGE_EVIDENCE_CHARS = 9000
STAGE_UNSPANNED_CHARS = 520
STAGE_REWRITE_TIMEOUT = 36.0
STAGE_REWRITE_MIN_SECONDS = 13.0
STAGE_SEARCH_MIN_SECONDS = 50.0
STAGE_TAIL_RESERVE_SECONDS = 28.0
ROSTER_BUDGET_SECONDS = 22.0


# --- stage: claim-level verify-and-repair ---------------------------------
# The audit turn judges the answer as one object, so a single unsupported
# sentence inside an otherwise sound answer survives it. This decomposes the
# draft into atomic claims, keeps the ones carrying a figure, and hands the
# rewrite the specific sentences that assert a number with nothing behind them.

VERIFY_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
VERIFY_MIN_CLAIM_CHARS = 24
VERIFY_MAX_CLAIMS = 6


def _atomic_claims(answer: str) -> list[str]:
    claims: list[str] = []
    for sentence in VERIFY_SENTENCE_RE.split(answer or ""):
        text = sentence.strip()
        if len(text) < VERIFY_MIN_CLAIM_CHARS:
            continue
        if not NUMERIC_RE.search(text):
            continue
        claims.append(text)
    return claims


def _uncited_claims(answer: str) -> list[str]:
    out: list[str] = []
    for claim in _atomic_claims(answer):
        if BRACKET_RE.search(claim):
            continue
        out.append(claim[:180])
        if len(out) >= VERIFY_MAX_CLAIMS:
            break
    return out


async def _verify_and_repair(
    question: str, answer: str, index: _ResultIndex, terms: list[str], deadline: float,
) -> str:
    if not BRACKET_RE.search(answer or ""):
        return answer
    loose = _uncited_claims(answer)
    if not loose:
        return answer
    listed = "\n".join(f"- {claim}" for claim in loose)
    directive = (
        "These claims state a figure but carry no marker:\n" + listed + "\n"
        "For each, attach the marker of the passage that supports it, correct the "
        "figure to what that passage states, or remove the claim. Leave every "
        "already-cited claim exactly as it stands."
    )
    return await _stage_rewrite(question, answer, index, directive, deadline)


# --- stage: citation slice backfill ---------------------------------------
# A source cited from its search excerpt goes out with a slice anchored by the
# generic claim text around the marker, which is how a citation ends up
# pointing at a page's navigation. This runs before the citation array is built
# and materialises a value-anchored region for every cited source that has no
# surfaced span yet. No model call and no search: it re-projects what was
# already read.

BACKFILL_WINDOW_CHARS = 900
BACKFILL_MAX_SOURCES = 10


def _backfill_claims(answer: str, index: _ResultIndex) -> dict[int, list[str]]:
    claims: dict[int, list[str]] = {}
    for match in BRACKET_RE.finditer(answer or ""):
        lead = answer[max(0, match.start() - CITATION_ANCHOR_CONTEXT_CHARS):match.start()]
        for n in _numbers_from_bracket(match.group(1), max_number=index.max_number()):
            claims.setdefault(n, []).append(lead)
    return claims


async def _citation_backfill(
    question: str, answer: str, index: _ResultIndex, terms: list[str], deadline: float,
) -> str:
    claims = _backfill_claims(answer, index)
    if not claims:
        return answer
    done = 0
    for n in sorted(claims):
        if done >= BACKFILL_MAX_SOURCES:
            break
        meta = index.get(n)
        if meta is None or not meta.get("citable"):
            continue
        if index.spans(n):
            continue
        note = meta.get("note") or ""
        if len(note) < 120:
            continue
        start, end = _anchored_slice_bounds(note, claims.get(n) or [], BACKFILL_WINDOW_CHARS)
        if end <= start:
            continue
        index.surface(n, [(start, end)])
        done += 1
    return answer


async def _plain_query(query: Query, budget: float) -> Response:
    start = perf_counter()
    deadline = start + budget
    research_stop = min(start + RESEARCH_TIME_CAP_SECONDS, deadline - FINAL_RESERVE_SECONDS)
    index = _ResultIndex()
    _SO_INDEX_HOLDER[:] = [index]
    terms = _key_terms(query.text)
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query.text},
    ]
    candidates: list[str] = []
    final_answer: str | None = None
    notice = ""

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
            break

        # --- RELOCATE: re-project retained pages onto the unanswered parts ---
        asks = _question_asks(query.text, candidates)
        open_asks = _relocate(index, asks, deadline - FINAL_RESERVE_SECONDS)
        notice = _relocate_notice(asks, open_asks)

        # --- CHECKPOINT: VERIFY + capped targeted re-dispatch ---
        checkpoint = _checkpoint_message(candidates, index)
        if notice:
            checkpoint = notice + "\n\n" + checkpoint
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
                messages.append({"role": "user", "content": COMMIT_MESSAGE})
                commit_messages = messages
            final_answer = await _commit_call(commit_messages, deadline=deadline)
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

        # --- ADDED STAGES: claim-level verify-and-repair then citation slice backfill ---
        # These run on the answer the commit stage produced and before the
        # amend stage, so what amend re-projects is already repaired.
        stage_input = display
        stage_deadline = deadline - STAGE_TAIL_RESERVE_SECONDS
        if display:
            display = await _verify_and_repair(query.text, display, index, terms, stage_deadline)
        if display:
            display = await _citation_backfill(query.text, display, index, terms, stage_deadline)
        if display != stage_input:
            # citations are sourced from what is actually delivered
            cite_text = display
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
STRUCTURED_RESERVE_SECONDS = 55.0
STRUCTURED_ATTEMPTS = 3
STRUCTURED_MIN_RETRY_SECONDS = 25.0
STRUCTURED_CALL_TIMEOUT_SECONDS = 22.0
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
_SO_INDEX_HOLDER: list = []


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
    # The index is held directly rather than behind a closure: binding a
    # callable out of a container and calling it is an unsupported_callable in
    # the miner-script subset, and this reads the same evidence either way.
    if not _SO_INDEX_HOLDER:
        return ""
    try:
        return (_serializer_evidence(_SO_INDEX_HOLDER[0], limit) or "")[:limit]
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

    best: object = None
    have_best = False
    used_evidence = False
    # The conversion step used to be handed the prose answer alone and told not
    # to invent. An answer that hedges then converts to a schema-valid object of
    # blanks, which passes every shape check there is. The passages this run
    # actually read travel with it from the FIRST call instead.
    evidence = _so_evidence()
    problems: list[str] = []
    for attempt in range(STRUCTURED_ATTEMPTS):
        remaining = deadline - perf_counter()
        if remaining <= (STRUCTURED_MIN_RETRY_SECONDS if attempt else 4.0):
            break
        timeout = min(STRUCTURED_CALL_TIMEOUT_SECONDS, remaining - 2.0)
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
        if not have_best or (_so_is_vacuous(best) and not _so_is_vacuous(candidate)):
            best = candidate
            have_best = True
        problems = _so_errors(candidate, schema, schema)[:STRUCTURED_MAX_REPORTED_ERRORS]
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
        best = candidate
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


@entrypoint("query")
async def query(query: Query) -> Response:
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
