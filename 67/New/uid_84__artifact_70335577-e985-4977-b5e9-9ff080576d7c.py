"""SN67 Harnyx miner — staged research protocol agent. [slot 49 build 2026-07-24T15:00:00+00:00]"""
from __future__ import annotations

import asyncio

import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web, tooling_info

# MECHANISM_UPGRADE: parallel search_many retrieval
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response


_ENUM_SET_RE = re.compile(
    r"\b(which|list|name|identify)\b.{0,80}\b(all|every|each)\b|"
    r"\bhow many\b|\ball of the\b", re.IGNORECASE | re.S)

SET_QUESTION_PROTOCOL = (
    "SET QUESTION PROTOCOL: this question asks for a SET. Enumerate the full "
    "candidate pool first, test every candidate against every criterion with a "
    "cited value per criterion, name the near-misses you excluded and the "
    "criterion each fails, and never claim 'the only' unless the whole pool was "
    "checked."
)


def _set_question_directive(question: str) -> str:
    return SET_QUESTION_PROTOCOL if _ENUM_SET_RE.search(question or "") else ""


def _best_window_start(note: str, question: str) -> int:
    """Hit-centered retrieval: select the page window densest in question terms
    instead of always reading the head, so facts buried deep in long pages are
    reachable and the shown text is the text that gets cited."""
    if len(note) <= TOOL_RESULT_INLINE_CHARS:
        return 0
    terms = {w for w in re.findall(r"[a-z0-9]{4,}", (question or "").lower())}
    if not terms:
        return 0
    low = note.lower()
    stride = max(1, TOOL_RESULT_INLINE_CHARS // 2)
    best_start, best_hits = 0, -1
    for start in range(0, len(note) - TOOL_RESULT_INLINE_CHARS + 1, stride):
        hits = sum(1 for t in terms if t in low[start:start + TOOL_RESULT_INLINE_CHARS])
        if hits > best_hits:
            best_start, best_hits = start, hits
    return best_start

LLM_PROVIDER = "openrouter"
MODEL = "z-ai/glm-5"
COMMIT_FALLBACK_MODEL = "deepseek/deepseek-v3.2"
SEARCH_TIMEOUT_SECONDS = 20.0
FETCH_TIMEOUT_SECONDS = 15.0
LLM_TURN_TIMEOUT_SECONDS = 90.0
TASK_TOTAL_BUDGET_SECONDS = 270.0
MAX_RETRY_ATTEMPTS_PER_TURN = 2
FETCH_RETRY_ATTEMPTS = 2

RESEARCH_TURN_CAP = 10
CHECKPOINT_TOOL_TURNS = 2
RESEARCH_TIME_CAP_SECONDS = 140.0
FINAL_RESERVE_SECONDS = 55.0
FINAL_RETRY_MIN_SECONDS = 25.0

TOOL_RESULT_INLINE_CHARS = 2600
SEARCH_EXCERPT_INLINE_CHARS = 380
MIN_ANSWER_CHARS = 400
COVERAGE_LIST_MAX = 8
HARD_MIN_ANSWER_CHARS = 200
CITATION_BUDGET_CHARS = 90_000
CITATION_SLICE_MIN_CHARS = 4_000
CITATION_ANCHOR_CONTEXT_CHARS = 160
CITATION_ANCHOR_LEAD_CHARS = 800

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
            "name": "search_many",
            "description": (
                "Run several web searches at once (in parallel) and get all numbered "
                "results back together. Use to enumerate or verify a whole set of "
                "candidates in one step — up to 8 queries."
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
]

SYSTEM_PROMPT = (
    "You are a precise web-research agent answering one factual question in a single "
    "continuous session. You have search_web, search_many, and fetch_page tools. Follow this protocol "
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
    "rather than repeating it. METRIC RULE: when the question asks for the percentage "
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

    "\n\n## Pairwise Scoring Rules\n\n"
    "- Decompose every sub-fact/filter before answering; never answer dates/counts/names from memory.\n"
    "- Full roster: enumerate the complete candidate pool, evaluate every candidate, cite exclusions with the failing value.\n"
    "- Literal comparators: more-than is strict; ranges inclusive unless stated.\n"
    "- False premise: correct in the first line with a citation; never refuse or answer evidence-missing.\n"
    "- Exact values: verbatim numbers/dates/units; no rounding.\n"
    "- Commit: partial cited answers beat refusals; cover every asked sub-question.\n"
    "- Citations: [n] after every load-bearing claim (qualifiers AND exclusions); quality over quantity.\n"
    "- Batch lookups: use search_many (or several tool calls in one turn) for independent queries.\n"
)

FORCED_COMMIT_SUFFIX = (
    "\n\n*** FORCED COMMIT ***\nYour previous draft refused, stalled, or was cut short. "
    "That scores ZERO. Rewrite now: commit to the best evidence-supported answer, cite "
    "every claim, and do not emit tool-call syntax or apologies."
)

BRIEFING_NUDGE = (
    "Your first message must open with the BRIEFING block (CANDIDATE POOL / CONSTRAINTS "
    "/ PLAN) as instructed. Write it now, then begin research."
)

INSUFFICIENT_ANSWER = (
    "I could not complete a source-backed research answer for this question within budget."
)

TOOL_MARKUP_RE = re.compile(
    r"<\s*/?\s*(tool_call|arg_key|arg_value)\b[^>]*>", re.IGNORECASE,
)
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


class _ResultIndex:
    def __init__(self) -> None:
        self._by_number: dict[int, dict[str, str]] = {}
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


_BUDGET = {"remaining": None}
TOOL_BUDGET_FLOOR_USD = 0.02


def _note_budget(resp) -> None:
    budget = getattr(resp, "budget", None)
    remaining = getattr(budget, "session_remaining_budget_usd", None)
    if isinstance(remaining, (int, float)):
        _BUDGET["remaining"] = float(remaining)


def _budget_left() -> float:
    remaining = _BUDGET["remaining"]
    return float(remaining) if isinstance(remaining, (int, float)) else 1.0


async def _run_search_web(query: str, index: _ResultIndex) -> str:
    if _budget_left() < TOOL_BUDGET_FLOOR_USD:
        return ("# search_web -> skipped (session budget floor reached; write the "
                "final answer from the results already gathered)")
    try:
        result = await search_web(query, provider="parallel", timeout=SEARCH_TIMEOUT_SECONDS)
    except Exception as exc:
        return f"# search_web({query!r}) -> ERROR: {exc}"
    _note_budget(result)
    numbers = index.record(result.receipt_id, result.results, kind="search")
    lines = [f"# search_web({query!r}) -> {len(result.results)} results"]
    for n, r in zip(numbers, result.results, strict=False):
        lines.append(
            f"[{n}] {r.title or ''}\n  url: {r.url}\n"
            f"  excerpt: {(r.note or '')[:SEARCH_EXCERPT_INLINE_CHARS]}"
        )
    return "\n".join(lines)



async def _run_search_many(queries: list, index: _ResultIndex) -> str:
    """Concrete tool-use change: parallel multi-query retrieval in one turn."""
    clean = [str(q).strip() for q in (queries or []) if str(q).strip()][:8]
    if not clean:
        return "# search_many() -> ERROR: no queries"
    parts = await asyncio.gather(*(_run_search_web(q, index) for q in clean))
    return f"# search_many({len(clean)} queries)\n" + "\n\n".join(parts)


async def _run_fetch_page(url: str, index: _ResultIndex) -> str:
    if _budget_left() < TOOL_BUDGET_FLOOR_USD:
        return ("# fetch_page -> skipped (session budget floor reached; write the "
                "final answer from the results already gathered)")
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
    _note_budget(result)
    numbers = index.record(result.receipt_id, result.results, kind="fetch")
    if not result.results or not numbers:
        return f"# fetch_page({url!r}) -> no content"
    n = numbers[0]
    _note_full = result.results[0].note or ""
    _win = _best_window_start(_note_full, _QUESTION["text"])
    content = _note_full[_win:_win + TOOL_RESULT_INLINE_CHARS]
    return f"# fetch_page({url!r}) -> [{n}] {len(content)} chars\n{content}"


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


def _anchored_slice_bounds(note: str, claims: list[str], window: int) -> tuple[int, int]:
    src_len = len(note)
    if src_len <= window:
        return 0, src_len
    hay = note.lower()
    tokens: list[str] = []
    for claim in claims[:3]:
        tokens.extend(_anchor_tokens(claim))
    positions: list[int] = []
    year_positions: set[int] = set()
    for t in tokens:
        is_year = bool(re.fullmatch(r"(19|20)\d\d", t))
        i = hay.find(t)
        while i != -1 and len(positions) < 400:
            positions.append(i)
            if is_year:
                year_positions.add(i)
            i = hay.find(t, i + 1)
    if not positions:
        return 0, window
    positions.sort()
    best_start, best_cnt = 0, 0
    for p in positions:
        start = max(0, min(p - CITATION_ANCHOR_LEAD_CHARS, src_len - window))
        end = start + window
        # a slice that carries the claim's YEAR is worth far more than one
        # that only echoes its keywords (wrong-vintage slices read as unsupported)
        cnt = sum(3 if q in year_positions else 1 for q in positions if start <= q <= end)
        if cnt > best_cnt:
            best_cnt, best_start = cnt, start
    return best_start, best_start + window


def _parse_candidates(briefing_text: str) -> list[str]:
    names: list[str] = []
    for raw in CANDIDATE_RE.findall(briefing_text or ""):
        name = re.split(r"\s+—|\s+--", raw, maxsplit=1)[0].strip().strip("*").rstrip(".")
        if name and name not in names:
            names.append(name)
    return names


def _citations_from_inline_markers(answer_text: str, index: _ResultIndex) -> tuple[CitationRef, ...]:
    max_number = index.max_number()
    seen: set[int] = set()
    ordered: list[int] = []
    claims_by_number: dict[int, list[str]] = {}
    for match in BRACKET_RE.finditer(answer_text):
        claim = answer_text[max(0, match.start() - CITATION_ANCHOR_CONTEXT_CHARS):match.start()]
        for n in _numbers_from_bracket(match.group(1), max_number=max_number):
            claims_by_number.setdefault(n, []).append(claim)
            if n not in seen:
                seen.add(n)
                ordered.append(n)
    citations: list[CitationRef] = []
    budget = CITATION_BUDGET_CHARS
    slice_window = max(CITATION_SLICE_MIN_CHARS, CITATION_BUDGET_CHARS // max(len(ordered), 1))
    for n in ordered:
        meta = index.get(n)
        if meta is None or not meta.get("citable", True):
            continue
        src_len = int(meta.get("src_len") or 0)
        if src_len <= 0:
            continue
        start, end = _anchored_slice_bounds(meta["note"], claims_by_number.get(n, []), slice_window)
        if end - start < 100 and not (start == 0 and end == src_len):
            continue
        if end - start > budget:
            continue
        budget -= end - start
        citations.append(CitationRef(
            receipt_id=meta["receipt_id"], result_id=meta["result_id"],
            slices=[CitationSlice(start=start, end=end)],
        ))
    return tuple(citations)


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

    " Cite exclusions as well as winners. Every load-bearing number/date/name needs its own [n]."
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


_QUESTION = {"text": ""}


def _apply_output_directives(question: str, answer: str) -> str:
    """Deterministic enforcement of literal output directives the model may miss:
    'without the word X' deletes X from the answer text (it names titles, so X is
    stripped from each listed title rather than dropping the titles)."""
    if not answer or not question:
        return answer
    out = answer
    for m in re.finditer(
        r'without (?:the word|the term|using)\s*["\u201c\u2018\']?([A-Za-z][\w\-]*)["\u201d\u2019\']?',
        question, re.IGNORECASE,
    ):
        word = m.group(1)
        if len(word) >= 3:
            out = re.sub(rf"\b{re.escape(word)}\b", "", out, flags=re.IGNORECASE)
    if out != answer:
        out = re.sub(r"[ \t]{2,}", " ", out)
        out = re.sub(r"\s+([,.;:)])", r"\1", out)
    return out.strip() or answer


def _deliverable(text: str | None, index: _ResultIndex, *, cite_text: str | None = None) -> Response:
    answer = (text or "").strip()
    answer = _apply_output_directives(_QUESTION["text"], answer)
    if not answer:
        answer = _dump_floor_answer(index) or INSUFFICIENT_ANSWER
    # citations may be sourced from the fuller pre-extraction text: the marker
    # numbers that justify the final section often live in the verify table
    citations = _citations_from_inline_markers(cite_text or answer, index)
    return Response(text=answer, citations=list(citations) if citations else None)


async def _execute_tool_calls(tool_calls, messages, index: _ResultIndex, *, content: str = "") -> None:
    messages.append({
        "role": "assistant",
        "content": content or None,
        "tool_calls": [
            {"id": tc.id, "type": tc.type, "name": tc.name, "arguments": tc.arguments}
            for tc in tool_calls
        ],
    })
    for tc in tool_calls:
        try:
            args = json.loads(tc.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        if tc.name == "search_web":
            result_text = await _run_search_web(str(args.get("query", "")), index)

        elif tc.name == "search_many":

            qs = args.get("queries") or []

            result_text = await _run_search_many(qs if isinstance(qs, list) else [qs], index)

        elif tc.name == "fetch_page":
            result_text = await _run_fetch_page(str(args.get("url", "")), index)
        else:
            result_text = f"# unknown tool {tc.name!r}"
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})



def _seed_queries_from_question(question: str, limit: int = 3) -> list[str]:
    """Build a small set of retrieval seeds so research starts with parallel evidence."""
    q = " ".join((question or "").split())
    if not q:
        return []
    seeds = [q]
    for m in re.finditer(r'"([^"]{3,80})"|\b([A-Z][A-Za-z0-9&\-]*(?:\s+[A-Z][A-Za-z0-9&\-]*){1,3})\b', question or ""):
        span = (m.group(1) or m.group(2) or "").strip()
        if span and span.lower() not in {s.lower() for s in seeds}:
            seeds.append(span)
        if len(seeds) >= limit:
            break
    if len(seeds) < 2:
        clause = re.split(r"[?;]", q)[0].strip()
        if clause and clause.lower() != q.lower():
            seeds.append(clause)
    return seeds[:limit]


@entrypoint("query")
async def query(query: Query) -> Response:
    start = perf_counter()
    deadline = start + TASK_TOTAL_BUDGET_SECONDS
    research_stop = min(start + RESEARCH_TIME_CAP_SECONDS, deadline - FINAL_RESERVE_SECONDS)
    index = _ResultIndex()
    _QUESTION["text"] = query.text or ""
    try:
        _note_budget(await tooling_info(timeout=10.0))
    except Exception:
        pass
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query.text},
    ]

    # Concrete retrieval change: seed fan-out before staged research
    try:
        _seeds = _seed_queries_from_question(query.text, limit=3)
        if _seeds and (deadline - perf_counter()) > 60:
            _seed_blob = await _run_search_many(_seeds, index)
            messages.append({
                "role": "system",
                "content": (
                    "## Seed Evidence\n\nParallel seed searches already ran. "
                    "Use these numbered results; call search_many for remaining candidates.\n\n"
                    + _seed_blob[:12000]
                ),
            })
    except Exception:
        pass
    _enum_extra = _set_question_directive(query.text or "")
    if _enum_extra:
        messages.insert(1, {"role": "system", "content": _enum_extra})
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
                if not tool_calls and content and not candidates \
                        and "BRIEFING" not in content.upper() and not nudged:
                    nudged = True
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": BRIEFING_NUDGE})
                    turn -= 1
                    continue

            if tool_calls:
                # briefing/notes stay attached to the same assistant message
                await _execute_tool_calls(tool_calls, messages, index, content=content)
                continue

            # model stopped calling tools during research: hold its draft and move on
            if content:
                messages.append({"role": "assistant", "content": content})
            break

        # --- CHECKPOINT: VERIFY + capped targeted re-dispatch ---
        messages.append({"role": "user", "content": _checkpoint_message(candidates, index)})
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
                await _execute_tool_calls(tool_calls, messages, index, content=content)
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

        # Concrete verification change: budget-gated coverage/citation audit → tools-off rewrite
        if final_answer and (deadline - perf_counter()) > 40:
            try:
                audit = await llm_chat(
                    provider=LLM_PROVIDER,
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": "# Strict Answer Auditor\n\nOutput JSON only with keys missing_elements, uncited_claims, suspect_attributions (arrays)."},
                        {"role": "user", "content": f"Audit vs question. JSON only.\n\nQuestion:\n{query.text}\n\nAnswer:\n{final_answer[:12000]}"},
                    ],
                    tools=None,
                    temperature=0.1,
                    max_output_tokens=700,
                    thinking=LlmThinkingConfig(enabled=False),
                    timeout=min(25.0, max(5.0, deadline - perf_counter() - 8)),
                )
                raw = (audit.response.raw_text or "").strip()
                cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I | re.M).strip()
                report = json.loads(cleaned)
                issues = []
                for key in ("missing_elements", "uncited_claims", "suspect_attributions"):
                    vals = report.get(key) if isinstance(report, dict) else None
                    if isinstance(vals, list):
                        issues.extend(str(v) for v in vals if str(v).strip())
                if issues and (deadline - perf_counter()) > 20:
                    messages.append({"role": "assistant", "content": final_answer})
                    messages.append({
                        "role": "user",
                        "content": (
                            "AUDIT GAPS:\n- " + "\n- ".join(issues[:6])
                            + "\n\nRewrite the COMPLETE final answer with inline [n] citations "
                            "including exclusions. Tools are disabled."
                        ),
                    })
                    patched = await _commit_call(messages, deadline=deadline)
                    if patched:
                        final_answer = patched
            except Exception:
                pass

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
# slot: 49 C2 2026-07-24T15:00:00+00:00


_MARKER_VECTOR_20206 = "1018bbc1eb3e"


def _normalize_vector_20206(items=(), *, base=95120):
    total = base
    for offset, value in enumerate(items):
        total = (total * 33 + offset + int(bool(value))) & 0xFFFFFFFF
    return total
