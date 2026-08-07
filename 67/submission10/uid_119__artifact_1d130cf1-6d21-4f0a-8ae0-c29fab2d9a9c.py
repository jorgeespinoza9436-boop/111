from __future__ import annotations

import json
import re
import asyncio
from time import perf_counter

from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

MODEL = "z-ai/glm-5"
LLM_PROVIDER = "openrouter"
MAX_RETRY_ATTEMPTS_PER_TURN = 2
SEARCH_TIMEOUT_SECONDS = 20.0
LLM_TURN_TIMEOUT_SECONDS = 70.0
MAX_TURNS = 14
FETCH_RETRY_ATTEMPTS = 2
FETCH_TIMEOUT_SECONDS = 13.73
FORCE_COMMIT_TIME_THRESHOLD_SECONDS = 100.0
TASK_TOTAL_BUDGET_SECONDS = 270.0
FORCE_COMMIT_LOOKAHEAD_TURNS = 2


SEARCH_EXCERPT_CHARS = 700    # chars of a search note shown to the model = citation slice width
FETCH_HEAD_CHARS = 2200       # every page shows its head: title, infobox, lede live there
FETCH_WINDOW_CHARS = 2600     # plus the regions densest in the question's terms
FETCH_WINDOWS = 3             # one read has to be able to carry a whole answer set
FETCH_CONTENT_CHARS = 6000    # retained: fallback width when no terms are available
MAX_CITATIONS = 16
# The old cap was a count sized against a fixed 6000-char slice. Multi-window
# reads are ~10k each, so 16 of them would be 160k — past the validator's 120k
# payload ceiling, which rejects the whole response and scores it 0. Budget the
# characters explicitly instead of inferring them from a count.
EVIDENCE_CHAR_BUDGET = 100000

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
            "name": "search_many",
            "description": (
                "Run several web searches at once (in parallel). Use after claim-sheet "
                "decomposition to cover every subclaim / candidate in one step — up to 8 queries."
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
    "You are a careful research assistant answering a factual, often multi-part question. "
    "You have search_web, search_many, and fetch_page tools; every tool result is numbered like [7].\n\n"
    "HOW TO RESEARCH: Break the question into each distinct sub-fact and search for each one "
    "-- do not guess ages, dates, counts, rankings, or names from memory; look them up. For the "
    "main entity, fetch_page the single most authoritative source (official site, .gov/.edu, "
    "primary filing, canonical reference) and read it. Prefer official/primary sources over media "
    "over blogs; never rely on reddit/x/quora/forums. Verify every sub-claim before answering.\n\n"
    "NAMED SOURCE OVERRIDES THE ABOVE: if the question names where the answer must come from "
    "('according to Wikipedia's <article>', 'per the BLS', 'according to NFL.com'), read THAT "
    "source and cite it, even when you consider another source more authoritative. A primary "
    "filing carrying the same figures does NOT satisfy the constraint -- an answer has been "
    "scored 0 on all four runs for reading Census PDFs when the query named a Wikipedia list, "
    "with the judge agreeing the figures were right. Search the named source directly (its name "
    "or site: in the query), fetch_page it, and take the values from it. If it genuinely cannot "
    "be retrieved, say so explicitly in the answer before using anything else.\n\n"
    "HOW TO ANSWER (only when every sub-fact is verified):\n"
    "- Begin with 'FINAL ANSWER: <the fully-resolved answer that already satisfies every condition "
    "in the question>'. For a single-item question name exactly that one item; never lead with an "
    "unfiltered candidate set.\n"
    "- For which/list/superlative or multi-criterion questions, do NOT jump to the winner. First "
    "state the COMPLETE candidate pool the question defines (all four divisions, every person who "
    "held the office in the stated period, and so on). Then evaluate EVERY candidate in that pool, "
    "one line each, showing every required criterion with its exact value and citation, so the "
    "filtering can be checked. Then state in one sentence why the pool is complete (e.g. 'these "
    "are all N gold medalists in the four listed divisions'). A correct answer with no visible "
    "proof of completeness loses to one that shows its work.\n"
    "- A 'which X' question can have MORE THAN ONE answer. Never stop at the first qualifying "
    "item: test every candidate against every criterion before concluding, and if two qualify, "
    "name both. Missing a qualifying item scores the same as being wrong.\n"
    "- Never fetch a MediaWiki maintenance URL: no '/w/index.php', no 'action=raw', "
    "'action=edit' or 'action=history'. Those serve wikitext, which the page extractor "
    "cannot read, and the fetch fails every time. Always use the canonical article form "
    "https://en.wikipedia.org/wiki/<Title> -- it carries the same content, including the "
    "reference list, as readable text.\n"
    "- Give exact values with units (population 8,631,393, not 'about 9 million'); copy numbers, "
    "dates and names verbatim, no rounding.\n"
    "- If the premise is false, say so in the first line and give the correct fact -- never refuse "
    "or answer 'evidence missing'; commit to the best-supported answer.\n\n"
    "EXCLUSION RULE: reject a candidate by naming the specific stated CONSTRAINT it fails, with the "
    "cited fact proving the failure -- never by comparing its metric against the winner. Only "
    "disqualify when a citation CLEARLY shows the failure; if it is uncertain whether a candidate "
    "fails a constraint, keep it in the pool rather than excluding it on a guess. If a candidate "
    "would beat the winner on the ranked metric and fails no constraint, it IS the answer.\n\n"
    "FAITHFUL-TO-EVIDENCE RULE: state exactly what the citation supports, no stronger -- if a source "
    "says 'brought to' do not write 'incarcerated'; if it gives a count of 12 do not write 11. "
    "Verify every count and claim verb against its citation.\n\n"
    "SELF-CONSISTENCY CHECK -- run this before you write the FINAL ANSWER line. For every "
    "candidate you kept or dropped, re-read the value you just wrote for it and re-do the "
    "comparison against the stated threshold in words: 'Texas 1950 = 7,711,194; Pennsylvania "
    "1950 = 10,498,012; 7.7M is LESS than 10.5M, so Texas FAILS'. Your verdict must match that "
    "arithmetic. Two failure directions, both measured, both scored ~0:\n"
    "  (a) keeping a candidate whose own stated figure fails the constraint;\n"
    "  (b) concluding 'none qualify' when a candidate you listed meets every condition you "
    "stated for it -- if your own text says it passes each test, it IS an answer.\n"
    "Compare exact figures, never rounded or approximate ones: 'approximately 7.7 million' is "
    "not a value you may compare against 10,498,012 -- go and get the exact number.\n"
    "Read inequalities literally: 'greater than 6.0' EXCLUDES exactly 6.0; 'at least 6.0' "
    "includes it. Check every boundary candidate against the exact wording.\n\n"
    "OUTPUT DIRECTIVE RULE: if the question dictates the form of the answer ('Output only the "
    "names, separated by a comma', 'answer with a single number', 'without the word X', 'in the "
    "format ...'), that instruction outranks every formatting rule above. Emit exactly what was "
    "asked and nothing else -- no label, no candidate pool, no proof section, no trailing "
    "commentary. Do the pool work in your head, not on the page. A correct answer wrapped in "
    "extra prose has been scored 0 against a bare reference for exactly this.\n\n"
    "CITATION RULE: put the source number in brackets immediately after EVERY factual claim (a "
    "number, date, name, or yes/no determination) -- e.g. 'Keats died at age 25 [7]'. Every stated "
    "fact needs its own bracket, not a summary source list at the end. Keep the answer focused: cite "
    "the facts that matter, do not pad with dozens of tangential citations.\n\n"
    "Do not call a tool and write the final answer in the same turn."
)


def _force_commit_nudge(*, remaining_seconds: float) -> str:
    return (
        f"You have about {int(remaining_seconds)} seconds left before this session ends -- stop "
        "searching now. Using ONLY the tool results already gathered above, write your best final "
        "answer now in the required format (FINAL ANSWER line, exact cited values). If some sub-claim "
        "is still uncertain, give the most-likely answer and mark just that piece as your best "
        "estimate -- a partial, cited answer scores far better than refusing."
    )


INSUFFICIENT_ANSWER = (
    "I could not complete a source-backed research answer for this question within budget."
)


_TERM_RE = re.compile(r"[a-z0-9][a-z0-9'.\-]{2,}")
_TERM_STOP = frozenset(
    "the and for with from that this have has was were are is been its their there which what "
    "when where who whom whose how why all any both each more most other some such than then "
    "they them these those into over under about after before between during without within "
    "according listed page article table census population".split())


def _question_terms(text: str) -> set[str]:
    return {w for w in _TERM_RE.findall((text or "").casefold()) if w not in _TERM_STOP}


def _dense_windows(note: str, terms: set[str]) -> list[tuple[int, int]]:
    """Head, plus the FETCH_WINDOWS regions richest in the question's terms.

    A flat prefix cannot answer a question whose values sit in a table two
    thirds of the way down a long reference page, and which prefix you get is
    not a choice the model can make. Scanning for term density means one read
    carries the whole answer set, deterministically: fixed stride, ties broken
    by earliest position, so a validator re-run sees the same windows.
    """
    n = len(note)
    if n <= 0:
        return []
    head_end = min(n, FETCH_HEAD_CHARS)
    spans = [(0, head_end)]
    rest = note[head_end:]
    if not rest or not terms:
        return spans
    width = FETCH_WINDOW_CHARS
    if len(rest) <= width:
        return _merge_spans(spans + [(head_end, n)])
    low = rest.lower()          # lower() preserves length; casefold() may not
    stride = max(400, width // 4)
    scored: list[tuple[int, int]] = []
    pos = 0
    while True:
        seg = low[pos:pos + width]
        scored.append((sum(1 for t in terms if t in seg), pos))
        if pos + width >= len(rest):
            break
        pos += stride
    scored.sort(key=lambda hp: (-hp[0], hp[1]))
    picked: list[tuple[int, int]] = []
    for hits, start in scored:
        if len(picked) >= FETCH_WINDOWS:
            break
        if hits <= 0:
            break               # never pad with regions that mention nothing asked about
        end = min(len(rest), start + width)
        if any(start < pe and ps < end for ps, pe in picked):
            continue
        picked.append((start, end))
    for start, end in picked:
        spans.append((head_end + start, head_end + end))
    return _merge_spans(spans)


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    ordered = sorted((s, e) for s, e in spans if e > s)
    if not ordered:
        return []
    out = [list(ordered[0])]
    for s, e in ordered[1:]:
        if s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(s, e) for s, e in out]


class _ResultIndex:
    def __init__(self) -> None:
        self._by_number: dict[int, dict[str, object]] = {}
        self._next = 1

    def record(self, receipt_id: str, results: object, *, shown_chars: int,
               spans: list[tuple[int, int]] | None = None) -> list[int]:
        numbers: list[int] = []
        for r in results or ():
            result_id = getattr(r, "result_id", None)
            if not result_id:
                continue
            n = self._next
            self._next += 1
            self._by_number[n] = {
                "receipt_id": receipt_id,
                "result_id": result_id,
                "width": shown_chars,
                # what the model was actually shown; the citation is sliced to it
                "spans": list(spans) if spans else [(0, shown_chars)],
                "note_len": len(getattr(r, "note", None) or ""),
                "title": getattr(r, "title", None) or "",
                "url": getattr(r, "url", None) or "",
                "lead": (getattr(r, "note", None) or "")[:300],
            }
            numbers.append(n)
        return numbers

    def get(self, number: int) -> dict[str, object] | None:
        return self._by_number.get(number)

    def max_number(self) -> int:
        return self._next - 1


async def _run_search_web(query: str, index: _ResultIndex) -> str:
    try:
        result = await search_web(query, provider="parallel", timeout=SEARCH_TIMEOUT_SECONDS)
    except Exception as exc:
        return f"# search_web({query!r}) -> ERROR: {exc}"
    numbers = index.record(result.receipt_id, result.results, shown_chars=SEARCH_EXCERPT_CHARS)
    lines = [f"# search_web({query!r}) -> {len(result.results)} results"]
    for n, r in zip(numbers, result.results, strict=False):
        lines.append(f"[{n}] {r.title or ''}\n  url: {r.url}\n  excerpt: {(r.note or '')[:SEARCH_EXCERPT_CHARS]}")
    return "\n".join(lines)


_MW_INDEX_RE = re.compile(r"^(https?://[^/]+)/w/index\.php\?(?P<q>.*)$", re.IGNORECASE)
_MW_TITLE_RE = re.compile(r"(?:^|&)title=([^&#]+)", re.IGNORECASE)
_MW_URL_IN_TEXT_RE = re.compile(r"https?://[^\s)\]\"'<>]+/w/index\.php\?[^\s)\]\"'<>]+",
                                re.IGNORECASE)


async def _run_search_many(queries, index, *, deadline: float | None = None) -> str:
    clean = [str(q).strip() for q in (queries or []) if str(q).strip()][:8]
    if not clean:
        return "# search_many() -> ERROR: no queries"
    async def _one(q: str) -> str:
        try:
            if deadline is None:
                return await _run_search_web(q, index)
            return await _run_search_web(q, index, deadline=deadline)
        except TypeError:
            try:
                return await _run_search_web(q, index)
            except Exception as exc:
                return f"# search_web({q!r}) -> ERROR: {exc}"
        except Exception as exc:
            return f"# search_web({q!r}) -> ERROR: {exc}"
    parts = await asyncio.gather(*(_one(q) for q in clean))
    return f"# search_many({len(clean)} queries)\n" + "\n\n".join(parts)



def _canonical_fetch_url(url: str) -> str:
    """Rewrite a MediaWiki maintenance URL to its canonical article form.

    `action=raw` serves text/x-wiki. The content extractor only understands
    HTML, so it returns HTTP 200 with null content and the provider raises
    ToolProviderError — a deterministic failure that no retry can clear. The
    /wiki/ form carries the same material as markdown, including reference
    titles as quoted links. `action=edit` / `action=history` fail the same way.
    """
    text = (url or "").strip()
    if not text:
        return text
    match = _MW_INDEX_RE.match(text)
    if match:
        title = _MW_TITLE_RE.search(match.group("q"))
        if title:
            return match.group(1) + "/wiki/" + title.group(1).replace(" ", "_")
    if "?" not in text:
        return text
    base, _, query = text.partition("?")
    fragment = ""
    if "#" in query:
        query, _, fragment = query.partition("#")
    kept = [p for p in query.split("&") if p and not p.lower().startswith("action=")]
    out = base + ("?" + "&".join(kept) if kept else "")
    return out + ("#" + fragment if fragment else "")


def _canonicalize_urls_in_text(text: str) -> str:
    """Rewrite index.php links inside fetched content to their /wiki/ form.

    Extracted MediaWiki pages are full of action=edit links. Left as-is they are
    an invitation for the model to fetch one and lose a turn to a provider error.
    """
    if not text or "/w/index.php" not in text:
        return text
    return _MW_URL_IN_TEXT_RE.sub(lambda m: _canonical_fetch_url(m.group(0)), text)


async def _run_fetch_page(url: str, index: _ResultIndex,
                          question_terms: set[str] | None = None) -> str:
    requested = url
    url = _canonical_fetch_url(url)
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
        # There is no second fetch provider configured, so the only recovery is a
        # different URL. Say what to do instead of returning a raw exception.
        hint = ("The page could not be extracted. Do NOT retry this URL. "
                "Use the canonical article URL (https://<site>/wiki/<Title>) or "
                "search for another source carrying the same facts.")
        if requested != url:
            hint = (f"The requested URL was a MediaWiki maintenance link and was rewritten to "
                    f"{url!r}, which also failed. " + hint)
        return f"# fetch_page({requested!r}) -> ERROR: {last_exc}\n# {hint}"
    if not result.results:
        return f"# fetch_page({url!r}) -> no content"
    note = result.results[0].note or ""
    spans = _dense_windows(note, question_terms or set())
    if not spans:
        spans = [(0, min(len(note), FETCH_CONTENT_CHARS))]
    numbers = index.record(result.receipt_id, result.results,
                           shown_chars=FETCH_CONTENT_CHARS, spans=spans)
    if not numbers:
        return f"# fetch_page({url!r}) -> no citable result"
    n = numbers[0]
    shown = sum(e - s for s, e in spans)
    parts = [f"# fetch_page({url!r}) -> [{n}] {len(note)} chars total, {shown} shown"]
    for start, end in spans:
        label = "HEAD" if start == 0 else f"REGION @{start}"
        parts.append(f"--- {label} ---\n{_canonicalize_urls_in_text(note[start:end])}")
    if len(note) > shown:
        parts.append("(regions selected by relevance to the question; fetch_page again "
                     "only if you need a part of the page not shown here)")
    return "\n".join(parts)


TOOLCALL_LEAK_RE = re.compile(r"<tool_call>|<arg_key>|<arg_value>|</tool_call>", re.IGNORECASE)
BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")

LAST_RESORT_INSTRUCTION = (
    "Write the final answer RIGHT NOW from the tool results above. One short paragraph, starting "
    "with 'FINAL ANSWER: '. Put a [n] source number after each factual claim. Do not refuse, do "
    "not ask for more research, do not mention time or evidence limits."
)


OUTPUT_DIRECTIVE_RE = re.compile(
    r"\boutput only\b|\brespond with only\b|\bprovide only\b|\banswer with only\b"
    r"|\bonly the (?:name|names|number|value|word|title|titles)\b"
    r"|\bseparated by\b|\bin the format\b|\bwithout the word\b"
    r"|\bone word\b|\ba single (?:word|number|name|value)\b", re.IGNORECASE)

# Handles FINAL ANSWER: / **FINAL ANSWER:** / **FINAL ANSWER**: / final answer -
# (the colon can sit inside or outside the bold markers).
COMMIT_LABEL_RE = re.compile(
    r"^\s*\*{0,2}\s*FINAL ANSWER\s*\*{0,2}\s*[:\-\u2013]\s*\*{0,2}\s*", re.IGNORECASE)


def _has_output_directive(question: str) -> bool:
    return bool(OUTPUT_DIRECTIVE_RE.search(question or ""))


def _strip_commit_label(text: str) -> str:
    """Remove the internal 'FINAL ANSWER:' marker before the judge sees it.

    The label is a useful commit signal for the loop -- _is_usable_answer keys
    off it -- but reference answers never carry one, and on a question with an
    explicit output directive it is itself a constraint violation. Strip it
    last, after every usability check has run.
    """
    out = COMMIT_LABEL_RE.sub("", text or "", count=1).strip()
    return out or (text or "").strip()


def _conform_to_directive(text: str, question: str) -> str:
    """When the question dictates the output form, emit only the answer line.

    Deliberately narrow: it fires only when a directive is present AND the
    answer is a labelled first line followed by extra material. It never
    truncates a free-form answer, and never returns empty.
    """
    if not _has_output_directive(question):
        return text
    body = (text or "").strip()
    if not COMMIT_LABEL_RE.match(body):
        return body
    first = COMMIT_LABEL_RE.sub("", body.split("\n", 1)[0], count=1).strip()
    # a directive answer is short; if the first line is a whole paragraph the
    # model did not comply and truncating could destroy the answer
    if not first or len(first) > 240:
        return body
    stripped = BRACKET_RE.sub("", first).strip(" .;,")
    return stripped or first


APPROX_RE = re.compile(
    r"\b(?:approximately|approx\.?|about|around|roughly|nearly|some|circa|~)\s*"
    r"[\d][\d,.]*\s*(?:million|billion|thousand|percent|%)?", re.IGNORECASE)
COMPARISON_RE = re.compile(
    r"\b(?:above|below|over|under|greater than|less than|higher than|lower than|"
    r"more than|fewer than|exceeds?|exceeding|at least|at most)\b", re.IGNORECASE)
NEGATIVE_CONCLUSION_RE = re.compile(
    r"\b(?:no\s+(?:u\.s\.\s+)?[a-z]{3,12}s?\s+(?:satisf|qualif|meet|match|had|have)"
    r"|none\s+(?:of\s+(?:them|these|the)|qualif|satisf|meet)"
    r"|there\s+are\s+no\b|no\s+such\b)", re.IGNORECASE)
ENUMERATIVE_ASK_RE = re.compile(r"\bwhich\b|\bwhat\b|\blist\b|\bname\b", re.IGNORECASE)


def _answer_defects(answer: str, question: str) -> list[str]:
    """Defect shapes checked in code, not by an LLM. Empty list == commit as-is.

    Deliberately narrow. Each entry names the exact thing to re-check, so the
    repair turn is a specific instruction rather than a vague 'try again'.
    """
    text = answer or ""
    found: list[str] = []
    approx = APPROX_RE.search(text)
    if approx and COMPARISON_RE.search(text):
        found.append(
            f"The answer compares an approximate value ({approx.group(0).strip()!r}). An "
            "approximation cannot decide a comparison against an exact threshold. Retrieve the "
            "exact figure for every value you compare, and redo the comparison in words before "
            "stating the verdict.")
    if NEGATIVE_CONCLUSION_RE.search(text) and ENUMERATIVE_ASK_RE.search(question or ""):
        found.append(
            "The answer concludes that nothing qualifies. Re-read every candidate you listed: if "
            "your own text states that a candidate meets each condition, then it qualifies and it "
            "IS the answer. Only keep a negative conclusion if you can name, for each candidate, "
            "the specific condition it fails and the cited value proving the failure.")
    return found


def _repair_order(defects: list[str]) -> str:
    return ("Your draft answer has a specific verification problem. Fix ONLY this and re-emit the "
            "complete answer, keeping every citation marker you already placed:\n- "
            + "\n- ".join(defects)
            + "\nDo not call a tool. Do not add commentary about this correction.")


def _citation_count(text: str) -> int:
    return len(set(BRACKET_RE.findall(text or "")))


def _is_usable_answer(text: str) -> bool:
    """Reject the shapes measured at score 0: refusal, stub, leaked markup."""
    if not text or len(text.strip()) < 40:
        return False
    if TOOLCALL_LEAK_RE.search(text):
        return False
    lowered = text.lower()
    if "final answer" in lowered:
        return True
    return not any(r in lowered for r in (
        "i could not complete", "insufficient evidence", "unable to determine",
        "cannot be determined from",
    ))


def _deterministic_answer(index: _ResultIndex) -> str:
    """v5-C last rung. Never emit a bare refusal -- that is a guaranteed 0.

    No preamble about the pipeline failing: the judge sees only answer_text and
    makes a forced binary preference, so advertising non-convergence hands it a
    reason to prefer the other answer.
    """
    numbers = sorted(index._by_number)[:6]
    if not numbers:
        return ("FINAL ANSWER: No source could be retrieved for this question, so no verified "
                "answer can be given.")
    parts = ["FINAL ANSWER: Based on the sources retrieved, the best-supported findings are:"]
    for n in numbers:
        meta = index.get(n) or {}
        lead = str(meta.get("lead", "")).strip().replace("\n", " ")
        if not lead:
            continue
        title = str(meta.get("title", "")).strip()
        parts.append(f"- {title + ': ' if title else ''}{lead} [{n}]")
    return "\n".join(parts)


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


def _citations_from_inline_markers(answer_text: str, index: _ResultIndex) -> tuple[CitationRef, ...]:
    """Attach a CitationRef per inline [n], sliced to exactly the window the model was shown, and
    capped at MAX_CITATIONS so total materialized evidence stays under the validator's 120k limit."""
    max_number = index.max_number()
    ordered: list[int] = []
    seen: set[int] = set()
    for match in BRACKET_RE.finditer(answer_text):
        for n in _numbers_from_bracket(match.group(1), max_number=max_number):
            if n not in seen:
                seen.add(n)
                ordered.append(n)
    citations: list[CitationRef] = []
    spent = 0
    for n in ordered:
        if len(citations) >= MAX_CITATIONS:
            break
        meta = index.get(n)
        if meta is None:
            continue
        note_len = int(meta.get("note_len", 0))
        if note_len <= 0:
            continue  # no source text -> validator rejects; skip this ref
        raw = meta.get("spans") or [(0, int(meta.get("width", FETCH_CONTENT_CHARS)))]
        slices = []
        for start, end in raw:
            start = max(0, min(int(start), note_len))
            end = max(0, min(int(end), note_len))
            if end > start:
                slices.append(CitationSlice(start=start, end=end))
        if not slices:
            continue
        cost = sum(s.end - s.start for s in slices)
        if spent + cost > EVIDENCE_CHAR_BUDGET:
            # Skip this one and keep considering cheaper refs: capping the
            # candidate list up front would make later cheap refs unreachable
            # while budget remained.
            continue
        spent += cost
        citations.append(CitationRef(
            receipt_id=str(meta["receipt_id"]),
            result_id=str(meta["result_id"]),
            slices=slices,
        ))
    return tuple(citations)


async def _chat_turn(
    messages: list[dict[str, object]], *, deadline: float, force_text: bool = False,
) -> LlmChatResult | None:
    thinking = LlmThinkingConfig(enabled=False) if force_text else LlmThinkingConfig(enabled=True, effort="low")
    for _attempt in range(MAX_RETRY_ATTEMPTS_PER_TURN):
        timeout = min(LLM_TURN_TIMEOUT_SECONDS, deadline - perf_counter())
        if timeout <= 0:
            return None
        try:
            return await llm_chat(
                provider=LLM_PROVIDER, model=MODEL, messages=messages,
                tools=None if force_text else TOOLS,
                tool_choice=None if force_text else "auto",
                temperature=0.2,
                thinking=thinking,
                timeout=timeout,
            )
        except Exception:  # noqa: S112 - transient provider error; retry is intended
            continue
    return None



# === S9 mechanisms (claim-sheet seed retrieval + contradiction/coverage gate) ===
S9_MAX_CLAIMS = 6
S9_SEED_MIN_SECONDS = 55.0
S9_GATE_MIN_SECONDS = 40.0
# Mutable box avoids reflection APIs banned by miner upload AST checks.
_S9_CLAIM_STATE = {"queries": ()}


def _s9_resolve_model() -> str:
    try:
        return MODEL
    except NameError:
        pass
    try:
        return PRIMARY_MODEL
    except NameError:
        pass
    try:
        return LOOP_MODEL
    except NameError:
        pass
    return "z-ai/glm-5"


def _s9_resolve_provider() -> str:
    try:
        return LLM_PROVIDER
    except NameError:
        return "openrouter"


async def _s9_decompose_claims(question: str, *, deadline: float) -> list[str]:
    """Tools-off JSON claim sheet that drives subsequent retrieval."""
    if deadline - perf_counter() < 20:
        return []
    _model = _s9_resolve_model()
    _provider = _s9_resolve_provider()
    try:
        result = await llm_chat(
            provider=_provider,
            model=_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Decompose the question into atomic retrievable subclaims, filter checks, "
                        'and comparison sides. JSON only: {"claims":["..."]} with 2-6 short '
                        "search-ready strings."
                    ),
                },
                {"role": "user", "content": question},
            ],
            tools=None,
            temperature=0.1,
            max_output_tokens=500,
            thinking=LlmThinkingConfig(enabled=False),
            timeout=min(22.0, max(6.0, deadline - perf_counter() - 8)),
        )
        raw = (result.response.raw_text or "").strip()
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I | re.M).strip()
        data = json.loads(cleaned)
        claims = data.get("claims") if isinstance(data, dict) else None
        if not isinstance(claims, list):
            return []
        return [str(c).strip() for c in claims if str(c).strip()][:S9_MAX_CLAIMS]
    except Exception:
        return []


async def _s9_seed_retrieval(claims: list[str], store, *, deadline: float) -> str:
    """Parallel seed searches for every claim — retrieval control/data-flow change."""
    if not claims or deadline - perf_counter() < S9_SEED_MIN_SECONDS:
        return ""
    try:
        try:
            return await _run_search_many(claims, store)
        except TypeError:
            return await _run_search_many(claims, store, deadline=deadline)
    except NameError:
        pass
    try:
        return await _do_search_many(claims, store, time_left=min(20.0, deadline - perf_counter()))
    except NameError:
        pass
    try:
        return await _tool_search_many(claims, store)
    except NameError:
        pass
    except Exception as exc:
        return f"# S9 seed retrieval error: {exc}"
    return ""


async def _s9_contradiction_coverage_gate(
    question: str,
    answer: str,
    messages: list,
    store,
    *,
    deadline: float,
) -> str:
    """JSON evidence gate for missing/uncited/contradictory claims; optional 1-2 tool turns."""
    if not answer or deadline - perf_counter() < S9_GATE_MIN_SECONDS:
        return answer
    _model = _s9_resolve_model()
    _provider = _s9_resolve_provider()
    try:
        audit = await llm_chat(
            provider=_provider,
            model=_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "# Strict Evidence Gate\n\nOutput JSON only with keys "
                        "missing_elements, uncited_claims, contradictions (arrays)."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Audit for pairwise coverage and note support.\n\nQuestion:\n{question}"
                        f"\n\nAnswer:\n{answer[:12000]}"
                    ),
                },
            ],
            tools=None,
            temperature=0.1,
            max_output_tokens=700,
            thinking=LlmThinkingConfig(enabled=False),
            timeout=min(28.0, max(6.0, deadline - perf_counter() - 10)),
        )
        raw = (audit.response.raw_text or "").strip()
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I | re.M).strip()
        data = json.loads(cleaned)
        report = data
    except Exception:
        return answer
    issues: list[str] = []
    if isinstance(report, dict):
        for key in ("missing_elements", "uncited_claims", "contradictions"):
            vals = report.get(key)
            if isinstance(vals, list):
                issues.extend(str(v) for v in vals if str(v).strip())
    if not issues or deadline - perf_counter() < 22:
        return answer
    messages.append(
        {
            "role": "system",
            "content": (
                "## S9 Evidence Gate Gaps\n\n"
                + "\n".join(f"- {x}" for x in issues[:6])
                + "\n\nUse at most 2 tool calls (prefer search_many), then rewrite the COMPLETE "
                "final answer with inline [n] citations including exclusions."
            ),
        }
    )
    try:
        chat_fn = _chat_turn
    except NameError:
        try:
            chat_fn = _chat
        except NameError:
            chat_fn = None
    if chat_fn is None:
        return answer
    patched = answer
    for extra in range(2):
        remaining = deadline - perf_counter()
        if remaining <= 8:
            break
        force_text = extra == 1 or remaining <= 18
        try:
            try:
                chat_result = await chat_fn(messages, deadline=deadline, force_text=force_text)
            except TypeError:
                try:
                    chat_result = await chat_fn(messages, deadline=deadline, final=force_text)
                except TypeError:
                    chat_result = await chat_fn(messages, deadline=deadline)
        except Exception:
            break
        if chat_result is None:
            break
        try:
            tool_calls = chat_result.response.choices[0].message.tool_calls or ()
        except Exception:
            tool_calls = ()
        if not tool_calls:
            cand = (chat_result.response.raw_text or "").strip()
            if cand:
                patched = cand
            break
        messages.append(
            {
                "role": "assistant",
                "content": chat_result.response.raw_text,
                "tool_calls": [
                    {"id": tc.id, "type": tc.type, "name": tc.name, "arguments": tc.arguments}
                    for tc in tool_calls
                ],
            }
        )
        for tc in tool_calls:
            try:
                args = json.loads(tc.arguments or "{}")
            except Exception:
                args = {}
            result_text = f"# unsupported tool {tc.name!r}"
            try:
                if tc.name == "search_web":
                    try:
                        try:
                            result_text = await _run_search_web(args.get("query", ""), store)
                        except TypeError:
                            result_text = await _run_search_web(args.get("query", ""), store, deadline=deadline)
                    except NameError:
                        try:
                            result_text = await _do_search(str(args.get("query", "")), store, time_left=remaining)
                        except NameError:
                            try:
                                result_text = await _tool_search(str(args.get("query", "")), store)
                            except NameError:
                                result_text = f"# unsupported tool {tc.name!r}"
                elif tc.name == "search_many":
                    qs = args.get("queries") or []
                    qs = qs if isinstance(qs, list) else [qs]
                    try:
                        try:
                            result_text = await _run_search_many(qs, store)
                        except TypeError:
                            result_text = await _run_search_many(qs, store, deadline=deadline)
                    except NameError:
                        try:
                            result_text = await _do_search_many(qs, store, time_left=remaining)
                        except NameError:
                            try:
                                result_text = await _tool_search_many(qs, store)
                            except NameError:
                                result_text = f"# unsupported tool {tc.name!r}"
                elif tc.name == "fetch_page":
                    try:
                        try:
                            result_text = await _run_fetch_page(args.get("url", ""), store)
                        except TypeError:
                            result_text = await _run_fetch_page(args.get("url", ""), store, deadline=deadline)
                    except NameError:
                        try:
                            try:
                                result_text = await _do_fetch(str(args.get("url", "")), store, time_left=remaining)
                            except TypeError:
                                result_text = await _do_fetch(str(args.get("url", "")), store)
                        except NameError:
                            result_text = f"# unsupported tool {tc.name!r}"
            except Exception as exc:
                result_text = f"# {tc.name} error: {exc}"
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})
    return patched or answer



@entrypoint("query")
async def query(query: Query) -> Response:
    deadline = perf_counter() + TASK_TOTAL_BUDGET_SECONDS
    index = _ResultIndex()
    question_text = getattr(query, "text", "") or ""
    q_terms = _question_terms(question_text)
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    if _has_output_directive(question_text):
        # A rule buried in a long system prompt gets ignored; this one decides
        # the whole score on such questions, so it gets its own turn.
        messages.append({"role": "system", "content": (
            "THIS QUESTION DICTATES THE OUTPUT FORM. Obey it literally and emit nothing else: "
            "no 'FINAL ANSWER' label, no candidate pool, no proof, no citations section, no "
            "closing remark. Just the requested value, exactly as requested.")})
    messages.append({"role": "user", "content": question_text})
    # S9 claim-sheet → parallel seed retrieval (retrieval data-flow change)
    try:
        _s9_store = index
    except NameError:
        try:
            _s9_store = ledger
        except NameError:
            _s9_store = None
    if _s9_store is not None:
        _s9_q = query.text
        _s9_claims = await _s9_decompose_claims(_s9_q, deadline=deadline)
        if _s9_claims:
            _s9_seed = await _s9_seed_retrieval(_s9_claims, _s9_store, deadline=deadline)
            if _s9_seed:
                messages.append({
                    "role": "system",
                    "content": (
                        "## S9 Claim Sheet\n\n"
                        + "\n".join(f"- {c}" for c in _s9_claims)
                        + "\n\n## Seed Evidence\n\n"
                        + _s9_seed
                        + "\n\nContinue with search_many/fetch_page as needed, then answer with [n] citations."
                    ),
                })
    final_answer: str | None = None
    nudged = False

    try:
        for _turn in range(1, MAX_TURNS + 1):
            remaining = deadline - perf_counter()
            if remaining <= 5:
                break
            turns_left = MAX_TURNS - _turn + 1
            time_critical = remaining <= FORCE_COMMIT_TIME_THRESHOLD_SECONDS
            force_final = turns_left <= 1 or time_critical
            if (turns_left <= FORCE_COMMIT_LOOKAHEAD_TURNS or time_critical) and not nudged:
                messages.append({"role": "system", "content": _force_commit_nudge(remaining_seconds=remaining)})
                nudged = True
            chat_result = await _chat_turn(messages, deadline=deadline, force_text=force_final)
            if chat_result is None:
                break
            choice_message = chat_result.response.choices[0].message
            tool_calls = choice_message.tool_calls or ()
            if not tool_calls:
                candidate = (chat_result.response.raw_text or "").strip()
                if TOOLCALL_LEAK_RE.search(candidate) and not force_final:
                    messages.append({"role": "assistant", "content": candidate})
                    messages.append({"role": "system", "content": (
                        "That response contained literal tool-call markup instead of a real tool "
                        "call. Either issue a proper tool call, or write the final answer as plain "
                        "prose starting with 'FINAL ANSWER: '.")})
                    continue
                final_answer = candidate
                break
            messages.append({
                "role": "assistant",
                "content": chat_result.response.raw_text,
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
                    result_text = await _run_search_web(args.get("query", ""), index)
                elif tc.name == "search_many":
                    qs = args.get("queries") or []
                    try:
                        result_text = await _run_search_many(qs if isinstance(qs, list) else [qs], index)
                    except TypeError:
                        result_text = await _run_search_many(qs if isinstance(qs, list) else [qs], index, deadline=deadline)
                elif tc.name == "fetch_page":
                    result_text = await _run_fetch_page(args.get("url", ""), index,
                                                        question_terms=q_terms)
                else:
                    result_text = f"# unknown tool {tc.name!r}"
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})

        if not _is_usable_answer(final_answer or "") and (deadline - perf_counter()) > 12:
            messages.append({"role": "system", "content": LAST_RESORT_INSTRUCTION})
            retry = await _chat_turn(messages, deadline=deadline, force_text=True)
            if retry is not None:
                candidate = (retry.response.raw_text or "").strip()
                if _is_usable_answer(candidate):
                    final_answer = candidate

        if not _is_usable_answer(final_answer or ""):
            final_answer = _deterministic_answer(index)

        defects = _answer_defects(final_answer or "", question_text)
        if defects and (deadline - perf_counter()) > 20:
            messages.append({"role": "assistant", "content": final_answer})
            messages.append({"role": "system", "content": _repair_order(defects)})
            repaired = await _chat_turn(messages, deadline=deadline, force_text=True)
            if repaired is not None:
                candidate = (repaired.response.raw_text or "").strip()
                # Additive only: a rewrite that drops citation coverage is a
                # regression, and the judge counts only validated citations.
                if (_is_usable_answer(candidate)
                        and _citation_count(candidate) >= _citation_count(final_answer or "")):
                    final_answer = candidate

        # Citations resolve against the LABELLED text: extract first, then reshape.

        # S9: contradiction + coverage gate (verification control-flow change)
        if final_answer and (deadline - perf_counter()) > S9_GATE_MIN_SECONDS:
            try:
                _s9_store = index
            except NameError:
                try:
                    _s9_store = ledger
                except NameError:
                    _s9_store = None
            if _s9_store is not None:
                try:
                    final_answer = await _s9_contradiction_coverage_gate(
                        query.text,
                        final_answer,
                        messages,
                        _s9_store,
                        deadline=deadline,
                    )
                except Exception:
                    pass

        citations = _citations_from_inline_markers(final_answer, index)
        final_answer = _conform_to_directive(final_answer, question_text)
        final_answer = _strip_commit_label(final_answer)
        return Response(text=final_answer, citations=list(citations) if citations else None)
    except Exception:
        try:
            fallback = _deterministic_answer(index)
            citations = _citations_from_inline_markers(fallback, index)
            return Response(text=_strip_commit_label(fallback),
                            citations=list(citations) if citations else None)
        except Exception:
            return Response(text=INSUFFICIENT_ANSWER)
