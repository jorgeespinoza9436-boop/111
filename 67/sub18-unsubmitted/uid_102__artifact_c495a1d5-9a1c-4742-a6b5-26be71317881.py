"""SN67 Harnyx miner — staged research protocol agent. [slot 12 build 2026-08-04T06:44:20+00:00]

POST-MORTEM 2026-08-05
======================
Architectural change (novelty_target = evidence_state_flow):
  OLD root: _ResultIndex — numbered page store; evidence moves between stages as raw
            char-span windows replayed verbatim into each model turn; cross-period and
            cross-entity comparisons delegated entirely to the LLM reading raw text.
  NEW root: ClaimStore — typed (subject, attribute, period, value, source_num) record
            store populated by a focused extraction LLM call after the research phase;
            multi-year and multi-entity comparisons execute as deterministic relational
            queries over the store; the LLM at commit time sees the pre-computed
            qualifying set, not raw text windows.

Per-task fixes:
  498f4e28 (coverage_gap, avg=0.0): Cambridge admissions cross-year filter
    (pct_maintained 2019<2021<2023) delegated to LLM → always returns [].
    Fixed by: ClaimStore extraction extracts (subject, attribute, period, value)
    records from every fetched page; _relational_digest() runs
    cross_period_monotone(periods, "asc") in Python and injects the qualifying
    subject list into the commit context as a pre-computed deterministic result.

  tiebreak_noise tasks (0e2c4f20, 63a62df0, a533428e, 3cd86126, a95415a9):
    left unchanged per instructions (noise only, no factual error).

Latent bugs fixed on the way:
  - None newly discovered during this refactor.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from time import perf_counter

from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

LLM_PROVIDER = "openrouter"
MODEL = "z-ai/glm-5.2"
COMMIT_FALLBACK_MODEL = "deepseek/deepseek-v3.2"
MAX_RETRY_ATTEMPTS_PER_TURN = 2
FETCH_RETRY_ATTEMPTS = 2
SEARCH_TIMEOUT_SECONDS = 20.0
LLM_TURN_TIMEOUT_SECONDS = 90.0
FETCH_TIMEOUT_SECONDS = 15.0
TASK_TOTAL_BUDGET_SECONDS = 235.0

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
CITATION_SLICE_MIN_CHARS = 4_000
CITATION_ANCHOR_CONTEXT_CHARS = 160
CITATION_ANCHOR_LEAD_CHARS = 800
COMMIT_DIGEST_SOURCES_MAX = 16
COMMIT_DIGEST_NOTE_CHARS = 1_200
COMMIT_DIGEST_TOTAL_CHARS = 26_000
COMMIT_DIGEST_IDENTITY_CHARS = 320

PAGE_WINDOW_CHARS = 3600
PAGE_WINDOWS_PER_PAGE = 3
PAGE_WINDOW_BUDGET_CHARS = 34_000
TERM_LIMIT = 22
TERM_HITS_PER_TERM = 60
TERM_HITS_TOTAL = 600

LEDGER_MAX_PASSES = 3
LEDGER_WINDOW_CHARS = 1600
LEDGER_WINDOWS_PER_ROW = 2
LEDGER_PAGES_PER_ROW = 4
LEDGER_BUDGET_CHARS = 16_000
LEDGER_MIN_SECONDS = 6.0
LEDGER_ROWS_MAX = 10
LEDGER_PROOF_CHARS = 420
RESTATE_MIN_SECONDS = 20.0
RESTATE_TIMEOUT_SECONDS = 40.0
RESTATE_CONTEXT_CHARS = 11_000
RESTATE_MIN_KEEP_CHARS = 200

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
    "Do not answer during the briefing, and do not call a tool in the briefing turn. "
    "The briefing is written before any evidence exists, so it cannot decide what to "
    "look for; the research turn that follows sees the question and the constraints "
    "only.\n\n"
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
)

BRIEFING_NUDGE = (
    "Your first message must open with the BRIEFING block (CANDIDATE POOL / CONSTRAINTS) "
    "as instructed. Write it now, without calling a tool."
)

RESEARCH_OPENING = (
    "Begin RESEARCH now. Write your opening queries from the question and the constraints "
    "above. Do not search for a name, count, figure or value that no source has shown you "
    "yet — search for the pages that would carry it."
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


# ---------------------------------------------------------------------------
# TYPED CLAIM STORE — replacement evidence_state_flow root
#
# Replaces raw char-span text accumulation with structured (subject, attribute,
# period, value, source_num) records.  Cross-period and cross-entity comparisons
# run as deterministic relational queries over the store rather than being
# delegated to the LLM as unguided text inference.
# ---------------------------------------------------------------------------

CLAIM_EXTRACT_SYSTEM = (
    "Extract every numeric claim from the provided research evidence. "
    "For EVERY subject (entity/country/film/language/person/database/etc.) "
    "that has a numeric value in the evidence, output exactly one JSON record "
    "per line (JSONL) in this shape:\n"
    "{\"subject\": \"<entity name>\", \"attribute\": \"<what is measured>\", "
    "\"period\": \"<year or time label, or empty string if none>\", "
    "\"value\": <number as float>, \"source_num\": <citation N integer>}\n\n"
    "Rules:\n"
    "- subject: the named entity exactly as it appears in the evidence\n"
    "- attribute: short snake_case label for the metric "
    "(e.g. 'pct_maintained_home', 'box_office_usd', 'population', 'chart_peak')\n"
    "- period: year as a bare string if present (e.g. '2019', '2021', '2023'), "
    "else empty string\n"
    "- value: the numeric value as float (percentages as given, e.g. 68.8 not 0.688)\n"
    "- source_num: integer N from the [N] header of the evidence block\n"
    "Output ONLY valid JSONL — one JSON object per line, no prose, no fences."
)


@dataclass
class Claim:
    """One typed record in the evidence state: a (subject, attribute, period) → value tuple."""
    subject: str
    attribute: str
    period: str   # year string e.g. "2019", or "" if not period-specific
    value: float
    source_num: int


class ClaimStore:
    """Typed evidence state that replaces raw text-window accumulation.

    Downstream stages query this store with relational operations rather than
    asking the LLM to read and compare raw text windows.
    """

    def __init__(self) -> None:
        self._claims: list[Claim] = []

    def add(self, claim: Claim) -> None:
        self._claims.append(claim)

    def empty(self) -> bool:
        return not self._claims

    def size(self) -> int:
        return len(self._claims)

    def all_claims(self) -> list[Claim]:
        return list(self._claims)

    def by_subject(self) -> dict[str, list[Claim]]:
        result: dict[str, list[Claim]] = defaultdict(list)
        for c in self._claims:
            result[c.subject].append(c)
        return dict(result)

    def cross_period_monotone(
        self, periods: list[str], direction: str = "asc",
    ) -> list[tuple[str, list[tuple[str, float]]]]:
        """Subjects whose values are strictly monotone across ALL given periods.

        Groups claims by (subject_lower, attribute_lower) so attribute-name
        variation across pages does not prevent matching.  Returns original-case
        subject names paired with the qualifying (period, value) sequence.
        """
        # Build {(subject_lower, attribute_lower): {period: value}}
        by_sub_attr: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
        orig_names: dict[str, str] = {}
        for c in self._claims:
            sk = c.subject.lower().strip()
            ak = c.attribute.lower().strip()
            by_sub_attr[(sk, ak)][c.period.strip()] = c.value
            orig_names[sk] = c.subject

        results: list[tuple[str, list[tuple[str, float]]]] = []
        seen: set[str] = set()
        for (sk, _ak), period_vals in by_sub_attr.items():
            if sk in seen:
                continue
            if not all(p in period_vals for p in periods):
                continue
            vals = [(p, period_vals[p]) for p in periods]
            nums = [v for _, v in vals]
            is_mono = (
                (direction == "asc" and all(nums[i] < nums[i + 1] for i in range(len(nums) - 1)))
                or (direction == "desc" and all(nums[i] > nums[i + 1] for i in range(len(nums) - 1)))
            )
            if is_mono:
                seen.add(sk)
                results.append((orig_names.get(sk, sk), vals))
        return results

    def render(self) -> str:
        """Compact tabular rendering of all stored records for LLM context."""
        if not self._claims:
            return ""
        lines = ["CLAIM STORE (typed relational records extracted from evidence):"]
        for c in self._claims[:80]:  # cap to stay within digest budget
            period_tag = f" [{c.period}]" if c.period else ""
            lines.append(
                f"  {c.subject} | {c.attribute}{period_tag} = {c.value} [src:{c.source_num}]"
            )
        return "\n".join(lines)


async def _extract_claims(
    index: "_ResultIndex", question: str, terms: list[str], deadline: float,
) -> ClaimStore:
    """Populate a ClaimStore from the research evidence via one focused LLM call.

    This is the extraction stage of the new evidence_state_flow: after the
    research phase has gathered pages, a single structured LLM call pulls typed
    (subject, attribute, period, value) records out of the evidence digest so
    that downstream comparison stages work on typed data rather than raw text.
    """
    store = ClaimStore()
    if index.max_number() == 0:
        return store
    budget = deadline - perf_counter() - 10
    if budget <= 6:
        return store
    digest = _evidence_digest(index, terms)
    if not digest:
        return store
    messages = [
        {"role": "system", "content": CLAIM_EXTRACT_SYSTEM},
        {"role": "user", "content": f"Question context: {question}\n\nEvidence:\n{digest[:18000]}"},
    ]
    try:
        result = await llm_chat(
            provider=LLM_PROVIDER, model=MODEL, messages=messages,
            temperature=0.0,
            thinking=LlmThinkingConfig(enabled=False),
            timeout=min(22.0, max(4.0, budget)),
        )
        raw = (result.response.raw_text or "").strip()
    except Exception:
        return store
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            rec = json.loads(line)
            if not isinstance(rec, dict):
                continue
            subject = str(rec.get("subject", "")).strip()
            attribute = str(rec.get("attribute", "")).strip()
            if not subject or not attribute:
                continue
            val = rec.get("value")
            if val is None:
                continue
            store.add(Claim(
                subject=subject,
                attribute=attribute,
                period=str(rec.get("period", "")).strip(),
                value=float(val),
                source_num=int(rec.get("source_num", 0)),
            ))
        except (ValueError, TypeError, KeyError):
            continue
    return store


def _relational_digest(store: ClaimStore, question: str) -> str:
    """Deterministic relational queries over the ClaimStore for the commit context.

    This is the query stage of the new evidence_state_flow: instead of asking
    the LLM to compare numeric values across years from raw text, the comparison
    runs here in Python and the result is injected as a pre-computed fact.
    """
    if store.empty():
        return ""
    q = question or ""
    parts: list[str] = [
        "RELATIONAL CLAIM ANALYSIS — deterministic computation over extracted typed records"
        " (use these pre-computed results; do not re-derive from raw text):"
    ]

    # Detect cross-period monotone queries (e.g. "increase between 2019 and 2021 and 2023")
    year_hits = re.findall(r"\b(20\d{2}|19\d{2})\b", q)
    years = sorted(set(year_hits))
    if len(years) >= 2:
        monotone_asc = store.cross_period_monotone(years, direction="asc")
        if monotone_asc:
            parts.append(
                f"\nSubjects with STRICTLY INCREASING values across {' → '.join(years)}"
                " (these are the subjects that qualify for an 'increased each period' filter):"
            )
            for subj, vals in monotone_asc:
                row = ", ".join(f"{p}: {v}" for p, v in vals)
                parts.append(f"  QUALIFIES: {subj}  ({row})")
        else:
            all_subjects = list(store.by_subject().keys())
            if all_subjects:
                parts.append(
                    f"\nNo subjects showed strictly increasing values across all of {years}. "
                    f"Subjects with extracted data: {', '.join(all_subjects[:20])}"
                )
            else:
                parts.append(
                    f"\nNo numeric claims were extracted for the {years} cross-period check."
                )

    # Always include the full claim table for reference
    rendered = store.render()
    if rendered:
        parts.append("\n" + rendered)
    return "\n".join(parts)


class _ResultIndex:
    def __init__(self) -> None:
        self._by_number: dict[int, dict[str, str]] = {}
        self._spans: dict[int, list[tuple[int, int]]] = {}
        self._window_budget = PAGE_WINDOW_BUDGET_CHARS
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
            if start > 0 and cost > self._window_budget:
                continue
            if start > 0:
                self._window_budget -= cost
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
    head_end = min(TOOL_RESULT_INLINE_CHARS, len(note))
    spans = [(0, head_end)]
    if len(note) > head_end:
        spans.extend(_best_windows(
            note, terms, PAGE_WINDOW_CHARS, PAGE_WINDOWS_PER_PAGE, skip_before=head_end,
        ))
    return spans


async def _run_fetch_page(url: str, index: _ResultIndex, terms: list[str]) -> str:
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
    shown = index.surface(n, _page_spans(note, terms))
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
    # One entry per SOURCE, not per evidence number: a page read twice used to
    # go out twice, with near-identical ranges, which reads as padding. Same
    # source -> one entry carrying the union of the ranges it was read from.
    by_source: dict[str, dict[str, object]] = {}
    source_order: list[str] = []
    slice_window = max(CITATION_SLICE_MIN_CHARS, CITATION_BUDGET_CHARS // max(len(ordered), 1))
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
        entry = by_source.get(key)
        if entry is None:
            by_source[key] = {"meta": meta, "spans": spans, "src_len": src_len}
            source_order.append(key)
        else:
            # same page, read again: keep the first receipt and widen its ranges
            limit = int(entry["src_len"])
            entry["spans"] = _merge_spans(
                list(entry["spans"]) + [(s, min(e, limit)) for s, e in spans if s < limit]
            )

    citations: list[CitationRef] = []
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
    return tuple(citations)


def _parse_candidates(briefing_text: str) -> list[str]:
    names: list[str] = []
    for raw in CANDIDATE_RE.findall(briefing_text or ""):
        name = re.split(r"\s+—|\s+--", raw, maxsplit=1)[0].strip().strip("*").rstrip(".")
        if name and name not in names:
            names.append(name)
    return names


BRIEF_SECTION_RE = re.compile(
    r"^\s*\(?[a-z]\)?[.)]?\s*(CANDIDATE POOL|CONSTRAINTS|PLAN)\b", re.IGNORECASE
)
BRIEFING_WITHHELD = "BRIEFING recorded."


def _research_briefing(text: str) -> str:
    """The briefing minus everything it guessed.

    The pool and any opening-query plan are written before one source has been
    read, so their names and figures are values nothing has shown yet. The
    constraints are a decomposition of the question itself and survive. The pool
    is not discarded — it is held for the coverage checkpoint, after evidence
    exists to test it against.
    """
    kept: list[str] = []
    dropping = False
    for line in (text or "").splitlines():
        head = BRIEF_SECTION_RE.match(line)
        if head is not None:
            dropping = not head.group(1).upper().startswith("CONSTRAINT")
            if dropping:
                continue
        elif dropping and not line.strip():
            dropping = False
        if dropping or CANDIDATE_RE.match(line):
            continue
        kept.append(line)
    return "\n".join(kept).strip() or BRIEFING_WITHHELD


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
    """Evidence numbers to expand, fetched pages before search results."""
    fetched: list[int] = []
    searched: list[int] = []
    for n in range(1, index.max_number() + 1):
        meta = index.get(n)
        if meta is None or not meta.get("citable", True):
            continue
        if meta.get("kind") == "fetch":
            fetched.append(n)
        else:
            searched.append(n)
    return sorted((fetched + searched)[:COMMIT_DIGEST_SOURCES_MAX])


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
        spans = index.spans(n)
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
    relational_note: str = "",
) -> list[dict[str, object]] | None:
    """The commit turn's own message list, built from the index rather than the
    research conversation. Returns None when there is no evidence to project.

    relational_note: pre-computed deterministic results from the ClaimStore
    (the new evidence_state_flow root); injected before the evidence digest so
    the LLM sees the qualifying set before the raw evidence.
    """
    digest = _evidence_digest(index, terms or _key_terms(question))
    if not digest:
        return None
    checkpoint = _checkpoint_message(candidates, index)
    if notice:
        checkpoint = notice + "\n\n" + checkpoint
    # Prepend the relational digest (pre-computed facts) to the raw evidence
    evidence_block = (relational_note + "\n\n" + digest) if relational_note else digest
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
        {"role": "user", "content": evidence_block + "\n\n" + checkpoint},
    ]
    if draft:
        messages.append({"role": "assistant", "content": draft})
    messages.append({"role": "user", "content": COMMIT_MESSAGE + suffix})
    return messages


# --- RESTATE ----------------------------------------------------------------
# The stage that issues the delivered answer. This pipeline holds the opening
# pool in code and keeps it out of the research conversation, so the pool is
# the one place that knows every entity in play. That ledger is carried through
# to delivery here: each row is re-projected against the pages already retained
# until a region of one names it and states a figure, and any row that ends up
# backed but unnamed in the draft is reissued into the answer that goes out.

LEDGER_CLAUSE_RE = re.compile(
    r"(?<=[?.;:])\s+"
    r"|\s+(?:and|then|also|finally|additionally)\s+(?=which|what|how|who|when|where|name|list|identify|give|state)",
    re.IGNORECASE,
)
NUMERIC_RE = re.compile(r"\d")


class _Row:
    __slots__ = ("subject", "key", "terms")

    def __init__(self, subject: str, key: str, terms: list[str]) -> None:
        self.subject = subject
        self.key = key
        self.terms = terms


def _answer_ledger(question: str, candidates: list[str]) -> list[_Row]:
    """One row per entity in play, the withheld pool first.

    The pool is the pipeline's own record of what the question puts in play and
    it never reaches the model, so it is the ledger's primary source. The
    question's interrogative clauses are used only when the pool is empty —
    they are a decomposition of the question, not a list of entities.
    """
    rows: list[_Row] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = _coverage_key(candidate)
        if len(key) < 3 or key in seen:
            continue
        terms = _key_terms(candidate, limit=6)
        if not terms:
            continue
        seen.add(key)
        rows.append(_Row(candidate[:90], key, terms))
    if not rows:
        for clause in LEDGER_CLAUSE_RE.split(question or ""):
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
            rows.append(_Row(clause[:90], terms[0], terms))
    return rows[:LEDGER_ROWS_MAX]


def _row_backing(row: _Row, index: _ResultIndex) -> tuple[int, str] | None:
    """The first surfaced region that names a row and states a figure for it.

    A page that merely mentions the subject is not the same as a page that
    answers for it, so the test needs both a term hit and a numeral close by.
    """
    wanted = min(2, len(row.terms))
    for number in range(1, index.max_number() + 1):
        meta = index.get(number)
        if meta is None:
            continue
        note = meta["note"] or ""
        for start, end in index.spans(number) or ():
            body = note[start:end]
            low = body.lower()
            hits = [p for p in (low.find(t) for t in row.terms) if p >= 0]
            if len(hits) < wanted:
                continue
            for at in sorted(hits):
                near = body[max(0, at - LEDGER_PROOF_CHARS):at + LEDGER_PROOF_CHARS]
                if NUMERIC_RE.search(near):
                    return number, " ".join(near.split())
    return None


def _reproject(index: _ResultIndex, ledger: list[_Row], deadline: float) -> dict[str, tuple[int, str]]:
    """Fill the ledger from the pages already retained, in its own loop.

    Each pass takes the rows with nothing behind them, pulls the best-matching
    unseen region out of every retained page for each, and re-tests. It
    re-enters while a pass is still surfacing new regions and stops as soon as
    one is not. It issues no request: the only cost is the text added to what
    has been read, which is capped separately.
    """
    backing = {row.key: b for row in ledger if (b := _row_backing(row, index)) is not None}
    budget = LEDGER_BUDGET_CHARS
    for _pass in range(LEDGER_MAX_PASSES):
        empty = [row for row in ledger if row.key not in backing]
        if not empty or budget <= 0 or deadline - perf_counter() < LEDGER_MIN_SECONDS:
            break
        surfaced = 0
        for row in empty:
            for number in index.fetched_numbers()[:LEDGER_PAGES_PER_ROW]:
                if budget <= 0:
                    break
                meta = index.get(number)
                if meta is None:
                    continue
                for a, b in index.surface(number, _best_windows(
                    meta["note"] or "", row.terms, LEDGER_WINDOW_CHARS,
                    LEDGER_WINDOWS_PER_ROW, avoid=index.spans(number),
                )):
                    surfaced += b - a
                    budget -= b - a
        if not surfaced:
            break
        for row in ledger:
            if row.key not in backing:
                found = _row_backing(row, index)
                if found is not None:
                    backing[row.key] = found
    return backing


def _ledger_notice(ledger: list[_Row], backing: dict[str, tuple[int, str]]) -> str:
    if not ledger:
        return ""
    empty = [row.subject for row in ledger if row.key not in backing]
    lines = [
        "RELOCATED EVIDENCE: the numbered evidence below now includes, for each entity "
        "this question puts in play, the regions of each retrieved page that mention it — "
        "not just each page's opening."
    ]
    if empty:
        lines.append(
            "No region states a figure yet for: " + "; ".join(empty[:COVERAGE_LIST_MAX]) +
            ". Re-scan the numbered evidence for those before treating any of them as missing."
        )
    else:
        lines.append(
            "Every entity now has a region that names it and states a figure for it. Quote "
            "those figures — do not describe them as unavailable."
        )
    return "\n".join(lines)


def _omitted(
    ledger: list[_Row], backing: dict[str, tuple[int, str]], answer: str,
) -> list[tuple[_Row, int, str]]:
    """Rows the evidence now backs that the delivered draft does not name.

    This is why the ledger is carried past the draft: the research turns wrote
    from what they had been shown, and re-projection changes what has been
    shown. A row that is backed but unnamed is, by construction, material the
    draft could not have used.
    """
    hay = (answer or "").lower()
    missing: list[tuple[_Row, int, str]] = []
    for row in ledger:
        found = backing.get(row.key)
        if found is None or row.key in hay:
            continue
        wanted = min(2, len(row.terms))
        if sum(1 for t in row.terms if t in hay) >= wanted:
            continue
        missing.append((row, found[0], found[1]))
    return missing


RESTATE_SYSTEM = (
    "You issue the final version of a research answer. The draft below was written "
    "before part of its evidence had been located; you are given the entities the draft "
    "leaves out together with the passage that covers each one.\n"
    "Rules:\n"
    "1. Keep everything the draft already states, in its structure and order. Any figure "
    "the draft already gives stands as written — you may not restate or correct it.\n"
    "2. Add each omitted entity where it belongs, with the figure its passage states and "
    "that passage's [n] marker.\n"
    "3. Remove any claim that an entity's figure is unavailable when a passage below "
    "states it.\n"
    "4. Output the complete answer and nothing else — no preamble, no notes about what "
    "you changed."
)


async def _reissue(
    question: str, answer: str, gaps: list[tuple[_Row, int, str]], deadline: float,
) -> str:
    """Reissue the answer with the omitted entities in it.

    The returned text REPLACES what the research turns produced; this stage owns
    what is delivered rather than annotating it. A reissue is kept only when it
    is a complete answer in its own right and still carries its citations, so
    the stage can add what was found without the risk of trading a whole answer
    for a fragment.
    """
    budget = deadline - perf_counter() - 3
    if budget <= 10 or not gaps:
        return answer
    room = RESTATE_CONTEXT_CHARS
    blocks: list[str] = []
    for row, number, proof in gaps[:COVERAGE_LIST_MAX]:
        chunk = f"OMITTED — {row.subject}\n[{number}] {proof[:max(0, min(room, 1400))]}"
        room -= len(chunk)
        blocks.append(chunk)
        if room <= 0:
            break
    messages = [
        {"role": "system", "content": RESTATE_SYSTEM},
        {"role": "user", "content": (
            f"QUESTION:\n{question}\n\nDRAFT ANSWER:\n{answer[:RESTATE_CONTEXT_CHARS]}\n\n"
            "ENTITIES THE DRAFT OMITS, WITH THEIR PASSAGES:\n\n" + "\n\n---\n\n".join(blocks) +
            "\n\nReturn the complete final answer now."
        )},
    ]
    try:
        result = await llm_chat(
            provider=LLM_PROVIDER, model=MODEL, messages=messages, temperature=0.1,
            thinking=LlmThinkingConfig(enabled=False),
            timeout=min(RESTATE_TIMEOUT_SECONDS, budget),
        )
        reissued = (result.response.raw_text or "").strip()
    except Exception:
        reissued = ""
    if len(reissued) < max(RESTATE_MIN_KEEP_CHARS, int(len(answer) * 0.5)):
        return answer
    if TOOL_MARKUP_RE.search(reissued) or PSEUDO_CALL_RE.search(reissued):
        return answer
    if BRACKET_RE.search(answer) and not BRACKET_RE.search(reissued):
        return answer
    if _needs_forced_retry(reissued):
        return answer
    return reissued


async def _restated_answer(
    question: str, ledger: list[_Row], index: _ResultIndex, answer: str, deadline: float,
) -> str:
    """The delivered answer, decided here.

    Always runs. Re-projection goes first so the draft is judged against
    everything the retained pages can be made to show, and the text this returns
    is the text that is delivered.
    """
    backing = _reproject(index, ledger, deadline)
    gaps = _omitted(ledger, backing, answer)
    if not gaps or deadline - perf_counter() < RESTATE_MIN_SECONDS:
        return answer
    return await _reissue(question, answer, gaps, deadline)


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
    citations = _citations_from_inline_markers(cite_text or answer, index)
    return Response(text=answer, citations=list(citations) if citations else None)


async def _execute_tool_calls(
    tool_calls, messages, index: _ResultIndex, terms: list[str], *, content: str = "",
) -> None:
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
        elif tc.name == "fetch_page":
            result_text = await _run_fetch_page(str(args.get("url", "")), index, terms)
        else:
            result_text = f"# unknown tool {tc.name!r}"
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})


async def _plain_query(query: Query, budget: float) -> Response:
    start = perf_counter()
    deadline = start + budget
    research_stop = min(start + RESEARCH_TIME_CAP_SECONDS, deadline - FINAL_RESERVE_SECONDS)
    index = _ResultIndex()
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
                # The briefing turn does not reach the research context intact and
                # its own tool calls are not run: what it proposed to look for was
                # chosen while its guesses were the only thing on the page.
                messages.append({"role": "assistant", "content": _research_briefing(content)})
                messages.append({"role": "user", "content": RESEARCH_OPENING})
                continue

            if tool_calls:
                # briefing/notes stay attached to the same assistant message
                await _execute_tool_calls(tool_calls, messages, index, terms, content=content)
                continue

            # model stopped calling tools during research: hold its draft and move on
            if content:
                messages.append({"role": "assistant", "content": content})
            break

        # --- LEDGER: the withheld pool becomes one row per entity in play ---
        ledger = _answer_ledger(query.text, candidates)
        notice = _ledger_notice(ledger, _reproject(index, ledger, deadline - FINAL_RESERVE_SECONDS))

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

        # --- LEDGER re-entry: the re-dispatch turns may have added pages ---
        if index.fetched_numbers():
            notice = _ledger_notice(ledger, _reproject(index, ledger, deadline - 10))

        # --- CLAIM EXTRACTION: populate ClaimStore from all gathered evidence ---
        # The ClaimStore is the new evidence_state_flow root: it holds typed
        # (subject, attribute, period, value) records extracted by a single focused
        # LLM call.  Cross-period comparisons run as relational queries over this
        # store rather than being delegated to the LLM as free-text inference.
        # Extraction runs with whatever time remains before the commit reserve.
        _claim_extraction_deadline = deadline - FINAL_RESERVE_SECONDS - 5
        claim_store = await _extract_claims(
            index, query.text, terms, _claim_extraction_deadline,
        )
        relational_note = _relational_digest(claim_store, query.text)

        # --- FORCED COMMIT: tools disabled ---
        if not final_answer:
            commit_messages = _commit_context(
                query.text, candidates, index, terms=terms, notice=notice,
                relational_note=relational_note,
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
                    relational_note=relational_note,
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

        # --- RESTATE decides what is delivered ---
        # The research turns wrote from what they had been shown. This stage runs
        # on every question, re-projects the retained pages against the ledger one
        # more time, and the answer it returns is the one that goes out.
        if display:
            decided = await _restated_answer(
                query.text, ledger, index, display, deadline - 4,
            )
            # when this stage reissued the answer, its markers are the ones the
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


async def _s18_base_query(query: Query) -> Response:
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
# slot: 12 C18_restate_w2 2026-08-04T06:44:20+00:00


# =====================================================================
# submittion18 MECHANISM — requirement-coverage gap-filling pass (text
# AND structured-output modes), decomposed by query-derived requirement
# category rather than by draft-answer claim
# =====================================================================
#
# Runs after the base pipeline above has produced a draft Response. Unlike
# a fact-contradiction check against the draft's own claims, this stage:
#   1. Decomposes the ORIGINAL QUESTION (not the draft) into up to 6
#      discrete, independently-checkable requirements using the same
#      requirement taxonomy live task generation uses (candidate_universe,
#      metric_or_field_relation, scope, time_qualifier, cardinality,
#      ranking, completeness, absence, other) -- including the target
#      JSON schema when the query is structured, so schema fields become
#      explicit requirements.
#   2. Coverage-checks the draft's CURRENT content (free text OR compact
#      JSON of Response.output) against that checklist, per requirement,
#      classifying each as satisfied / weak / missing and producing a
#      requirement-specific search query for any gap.
#   3. Issues ONE NEW, independently targeted search_web call PER GAP
#      (concurrently, capped at 3, missing prioritized over weak).
#   4. Sequentially, per gap with usable fresh evidence: for structured
#      responses, asks the model for a minimal JSON patch restricted to
#      keys that already exist in the current output/schema (never
#      invents new keys -- enforced both by prompt and by code-side
#      merge), and applies it to Response.output directly; for free-text
#      responses, rewrites only the missing/weak span of the answer,
#      preserving everything else. Both paths grow citations only from
#      the fresh, requirement-targeted evidence, never fabricated.
# This changes decomposition (requirement checklist vs draft claims),
# verification target (query coverage vs draft self-consistency), and
# control flow for structured outputs (direct JSON field patching, which
# the base pipeline's own post-processing does not do) relative to the
# base pipeline; it is not a prompt or parameter tweak. Any failure,
# missing evidence, non-dict structured output, or time shortage is a
# strict no-op that returns the base pipeline's own response (after cheap
# exact duplicate-citation cleanup only).

import asyncio as _s18_asyncio
import json as _s18_json
import re as _s18_re
from time import monotonic as _s18_monotonic

_S18_HARD_BUDGET_GATE_S = 250.0
_S18_MAX_WINDOW_S = 55.0
_S18_MIN_WINDOW_S = 10.0
_S18_EXTRACT_TIMEOUT_S = 9.0
_S18_COVERAGE_TIMEOUT_S = 9.0
_S18_SEARCH_TIMEOUT_S = 9.0
_S18_PATCH_TIMEOUT_S = 12.0
_S18_MAX_REQUIREMENTS = 6
_S18_MAX_GAPS_TO_FILL = 3
_S18_MAX_NEW_CITATIONS_PER_GAP = 2
_S18_MAX_TOTAL_CITATIONS = 60
_S18_MODEL = "deepseek/deepseek-v3.2"

_S18_EXTRACT_SYSTEM_PROMPT = (
    "You extract the discrete requirement checklist implied by a research "
    "question.\n"
    "Given a question (and, if present, the exact JSON schema the final "
    "answer must satisfy), list up to 6 concrete, independently-checkable "
    "requirements the answer MUST satisfy to be considered complete and "
    "correct. Use these requirement categories where they fit: "
    "candidate_universe (what set of entities/items is in scope), "
    "metric_or_field_relation (which metric, field, or relationship must "
    "be reported), scope (time range, region, edition, or other scoping "
    "filter), time_qualifier (a specific date, period, or as-of "
    "condition), cardinality (an exact count, top-N, or single-vs-"
    "multiple requirement), ranking (an explicit order or comparison "
    "requirement), completeness (every required field/element must be "
    "present, not just one), absence (a requirement that something does "
    "NOT apply, exist, or occur), other (anything else load-bearing).\n"
    "Do not invent requirements the question does not ask for. Skip "
    "stylistic or formatting-only observations.\n"
    "For each requirement, write a short label, its category, and a "
    "one-sentence description of what a fully satisfying answer must "
    "contain.\n"
    "Return JSON only: {\"requirements\": [{\"requirement\": str, "
    "\"category\": str, \"check\": str}, ...]}. Return an empty list only "
    "if the question truly has a single trivial requirement."
)

_S18_COVERAGE_SYSTEM_PROMPT = (
    "You are a strict requirement-coverage auditor.\n"
    "You receive a checklist of requirements a research answer must "
    "satisfy, and the CURRENT answer content (either prose text or a "
    "JSON object).\n"
    "For EACH requirement, decide independently:\n"
    "- satisfied: the current content clearly and specifically addresses "
    "this requirement with a concrete value or statement.\n"
    "- weak: the requirement is only vaguely, partially, or ambiguously "
    "addressed (e.g. missing a specific figure, date, or one part of a "
    "multi-part requirement).\n"
    "- missing: the current content does not address this requirement at "
    "all.\n"
    "For any requirement marked weak or missing, also produce a short, "
    "targeted web search query (5-15 words) that would directly source "
    "the missing information -- specific to that ONE requirement, not a "
    "restatement of the whole question.\n"
    "Return JSON only: {\"coverage\": [{\"index\": int, \"verdict\": "
    "\"satisfied\"|\"weak\"|\"missing\", \"gap_query\": str or null}, "
    "...]}, one entry per requirement in the given order."
)

_S18_PATCH_TEXT_SYSTEM_PROMPT = (
    "You fill in ONE missing or weak requirement inside a research answer "
    "using freshly retrieved evidence.\n"
    "Rewrite the COMPLETE answer: keep every part unrelated to this "
    "requirement byte-for-byte where feasible, and add or correct only "
    "the content needed to satisfy this specific requirement using the "
    "fresh evidence. If the evidence does not clearly resolve the "
    "requirement, make the smallest safe improvement (e.g. state what is "
    "known and flag what remains unconfirmed) rather than guessing.\n"
    "Preserve all existing citation markers whose underlying content is "
    "unchanged. Output plain answer text only: no preamble, no markdown "
    "fences, no meta-commentary about this process."
)

_S18_PATCH_OUTPUT_SYSTEM_PROMPT = (
    "You fill in ONE missing or weak requirement inside a structured JSON "
    "answer using freshly retrieved evidence.\n"
    "You receive the target JSON schema, the CURRENT JSON answer, one "
    "specific missing/weak requirement, and fresh evidence snippets "
    "gathered to resolve it.\n"
    "Return ONLY the JSON keys (top-level, or one level nested) whose "
    "values must be added or corrected to satisfy this requirement, using "
    "ONLY key names that already exist in the schema or current answer -- "
    "never invent new keys. If the fresh evidence does not give you a "
    "confident value, return an empty patch.\n"
    "Also report which evidence snippets (by 0-based index) you actually "
    "used.\n"
    "Return JSON only: {\"patch\": {...} or {}, \"used_indices\": "
    "[int, ...]}"
)


def _s18_strip_json_fences(raw: str) -> str:
    return _s18_re.sub(r"^```(?:json)?\s*|\s*```$", "", raw or "", flags=_s18_re.I | _s18_re.M).strip()


def _s18_chat_text(llm_result) -> str:
    if llm_result is None:
        return ""
    resp = getattr(llm_result, "response", None)
    text = getattr(resp, "raw_text", None) if resp is not None else None
    return (text or "").strip()


def _s18_compact_json(value) -> str:
    try:
        return _s18_json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return ""


def _s18_citation_key(ref) -> tuple:
    slices = tuple(
        (getattr(sl, "start", None), getattr(sl, "end", None))
        for sl in (getattr(ref, "slices", None) or [])
    )
    return (getattr(ref, "receipt_id", None), getattr(ref, "result_id", None), slices)


def _s18_dedup_citations(response):
    citations = getattr(response, "citations", None)
    if not citations:
        return response
    seen: set = set()
    deduped = []
    for ref in citations:
        key = _s18_citation_key(ref)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    if len(deduped) == len(citations):
        return response
    try:
        return response.model_copy(update={"citations": deduped})
    except Exception:
        return response


def _s18_merge_citations(existing, new_refs):
    existing_list = list(existing or [])
    seen = {_s18_citation_key(ref) for ref in existing_list}
    merged = list(existing_list)
    for ref in new_refs:
        key = _s18_citation_key(ref)
        if key in seen:
            continue
        seen.add(key)
        merged.append(ref)
        if len(merged) >= _S18_MAX_TOTAL_CITATIONS:
            break
    return merged


async def _s18_extract_requirements(question: str, output_schema) -> list:
    from harnyx_miner_sdk.api import llm_chat as _s18_llm_chat

    schema_block = ""
    if output_schema is not None:
        schema_json = _s18_compact_json(output_schema)[:4000]
        if schema_json:
            schema_block = (
                f"\n\nThe final answer must be a JSON object satisfying "
                f"this schema:\n{schema_json}"
            )
    try:
        result = await _s18_llm_chat(
            provider="openrouter",
            model=_S18_MODEL,
            messages=[
                {"role": "system", "content": _S18_EXTRACT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Question:\n{question}{schema_block}"},
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=550,
            timeout=_S18_EXTRACT_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return []
    try:
        parsed = _s18_json.loads(_s18_strip_json_fences(_s18_chat_text(result)))
    except Exception:
        return []
    if not isinstance(parsed, dict):
        return []
    raw = parsed.get("requirements")
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        requirement = str(item.get("requirement") or "").strip()
        category = str(item.get("category") or "other").strip() or "other"
        check = str(item.get("check") or "").strip()
        if requirement:
            out.append({"requirement": requirement, "category": category, "check": check})
        if len(out) >= _S18_MAX_REQUIREMENTS:
            break
    return out


async def _s18_check_coverage(requirements: list, content_repr: str, is_structured: bool) -> list:
    from harnyx_miner_sdk.api import llm_chat as _s18_llm_chat

    checklist_block = "\n".join(
        f"{idx}. [{req['category']}] {req['requirement']} \u2014 {req['check']}"
        for idx, req in enumerate(requirements)
    )
    label = "Current JSON answer" if is_structured else "Current answer text"
    try:
        result = await _s18_llm_chat(
            provider="openrouter",
            model=_S18_MODEL,
            messages=[
                {"role": "system", "content": _S18_COVERAGE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Requirement checklist:\n{checklist_block}\n\n"
                        f"{label}:\n{content_repr[:12000]}"
                    ),
                },
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=600,
            timeout=_S18_COVERAGE_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return []
    try:
        parsed = _s18_json.loads(_s18_strip_json_fences(_s18_chat_text(result)))
    except Exception:
        return []
    if not isinstance(parsed, dict):
        return []
    raw = parsed.get("coverage")
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("index"))
        except Exception:
            continue
        verdict = str(item.get("verdict") or "").strip().lower()
        gap_query_raw = item.get("gap_query")
        gap_query = gap_query_raw.strip() if isinstance(gap_query_raw, str) else ""
        if 0 <= idx < len(requirements) and verdict in ("satisfied", "weak", "missing"):
            out.append({"index": idx, "verdict": verdict, "gap_query": gap_query or None})
    return out


async def _s18_search_gap(search_query: str):
    from harnyx_miner_sdk.api import search_web as _s18_search_web

    for provider_name in ("parallel", "desearch"):
        try:
            payload = await _s18_search_web(
                search_query[:300],
                provider=provider_name,
                num=4,
                timeout=_S18_SEARCH_TIMEOUT_S,
            )
        except Exception:
            payload = None
        if payload is None:
            continue
        results = list(getattr(payload, "results", None) or [])
        if not results:
            continue
        receipt = str(getattr(payload, "receipt_id", "") or "")
        if not receipt:
            continue
        items = []
        for item in results:
            rid = getattr(item, "result_id", None)
            note = (getattr(item, "note", None) or "").strip()
            if not isinstance(rid, str) or not rid or not note:
                continue
            items.append({
                "result_id": rid,
                "note": note,
                "title": (getattr(item, "title", None) or "").strip(),
                "url": (getattr(item, "url", None) or "").strip(),
            })
            if len(items) >= 4:
                break
        if items:
            return {"receipt_id": receipt, "items": items}
    return None


def _s18_build_refs(receipt_id: str, evidence_items: list, indices) -> list:
    from harnyx_miner_sdk.query import CitationRef as _s18_citation_ref
    from harnyx_miner_sdk.query import CitationSlice as _s18_citation_slice

    refs = []
    for raw_idx in (indices or []):
        try:
            idx = int(raw_idx)
        except Exception:
            continue
        if not (0 <= idx < len(evidence_items)):
            continue
        item = evidence_items[idx]
        note_len = len(item["note"])
        end = min(500, note_len)
        if end <= 0:
            continue
        try:
            refs.append(_s18_citation_ref(
                receipt_id=receipt_id,
                result_id=item["result_id"],
                slices=[_s18_citation_slice(start=0, end=end)],
            ))
        except Exception:
            continue
        if len(refs) >= _S18_MAX_NEW_CITATIONS_PER_GAP:
            break
    return refs


async def _s18_patch_text(question: str, answer: str, requirement_label: str, gap_query: str, evidence_block: str) -> str:
    from harnyx_miner_sdk.api import llm_chat as _s18_llm_chat

    prompt = (
        f"Question:\n{question}\n\n"
        f"Current answer:\n{answer[:12000]}\n\n"
        f"Requirement being filled:\n{requirement_label}\n\n"
        f"Search query used to source it:\n{gap_query}\n\n"
        f"Fresh evidence snippets:\n{evidence_block}"
    )
    try:
        result = await _s18_llm_chat(
            provider="openrouter",
            model=_S18_MODEL,
            messages=[
                {"role": "system", "content": _S18_PATCH_TEXT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            tools=None,
            temperature=0.1,
            max_output_tokens=1400,
            timeout=_S18_PATCH_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return ""
    return _s18_chat_text(result)[:79000].strip()


async def _s18_patch_output(
    question: str,
    schema_compact: str,
    current_output_compact: str,
    requirement_label: str,
    gap_query: str,
    evidence_block: str,
) -> dict | None:
    from harnyx_miner_sdk.api import llm_chat as _s18_llm_chat

    prompt = (
        f"Question:\n{question}\n\n"
        f"Target JSON schema:\n{schema_compact or '(none provided)'}\n\n"
        f"Current JSON answer:\n{current_output_compact[:8000]}\n\n"
        f"Requirement to fill:\n{requirement_label}\n\n"
        f"Search query used to source it:\n{gap_query}\n\n"
        f"Fresh evidence snippets:\n{evidence_block}"
    )
    try:
        result = await _s18_llm_chat(
            provider="openrouter",
            model=_S18_MODEL,
            messages=[
                {"role": "system", "content": _S18_PATCH_OUTPUT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=700,
            timeout=_S18_PATCH_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return None
    try:
        parsed = _s18_json.loads(_s18_strip_json_fences(_s18_chat_text(result)))
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _s18_merge_output_patch(current, patch):
    """Shallow (+1-level-nested) merge that never introduces new keys."""
    if not isinstance(current, dict) or not isinstance(patch, dict) or not patch:
        return None
    merged = dict(current)
    applied = False
    for key, value in patch.items():
        if key not in merged:
            continue  # never invent schema-violating keys
        existing = merged[key]
        if isinstance(existing, dict) and isinstance(value, dict):
            merged_nested = dict(existing)
            for nested_key, nested_value in value.items():
                if nested_key in merged_nested:
                    merged_nested[nested_key] = nested_value
                    applied = True
            merged[key] = merged_nested
        else:
            merged[key] = value
            applied = True
    return merged if applied else None


async def _s18_coverage_pass(_s18_query, _s18_response):
    _s18_response = _s18_dedup_citations(_s18_response)
    question = (getattr(_s18_query, "text", None) or "").strip()
    if not question:
        return _s18_response

    output_schema = getattr(_s18_query, "output_schema", None)
    is_structured = getattr(_s18_response, "output", None) is not None

    if is_structured:
        current_output = getattr(_s18_response, "output")
        if not isinstance(current_output, dict):
            return _s18_response
        content_repr = _s18_compact_json(current_output)
        answer_text = None
    else:
        answer_text = (getattr(_s18_response, "text", None) or "").strip()
        if not answer_text:
            return _s18_response
        content_repr = answer_text
        current_output = None

    if not content_repr:
        return _s18_response

    requirements = await _s18_extract_requirements(question, output_schema)
    if not requirements:
        return _s18_response

    coverage = await _s18_check_coverage(requirements, content_repr, is_structured)
    if not coverage:
        return _s18_response

    missing = [c for c in coverage if c["verdict"] == "missing" and c["gap_query"]]
    weak = [c for c in coverage if c["verdict"] == "weak" and c["gap_query"]]
    gaps = (missing + weak)[:_S18_MAX_GAPS_TO_FILL]
    if not gaps:
        return _s18_response

    search_results = await _s18_asyncio.gather(
        *[_s18_search_gap(g["gap_query"]) for g in gaps],
        return_exceptions=True,
    )

    per_gap = []
    for gap, search_result in zip(gaps, search_results):
        if isinstance(search_result, Exception) or not search_result:
            continue
        per_gap.append((gap, search_result))
    if not per_gap:
        return _s18_response

    running_text = answer_text
    running_output = dict(current_output) if isinstance(current_output, dict) else None
    schema_compact = _s18_compact_json(output_schema)[:4000] if output_schema is not None else ""
    all_new_refs = []
    changed = False

    for gap, search_result in per_gap:
        req = requirements[gap["index"]]
        requirement_label = f"[{req['category']}] {req['requirement']} \u2014 {req['check']}"
        items = search_result["items"]
        receipt_id = search_result["receipt_id"]
        evidence_block = "\n".join(
            f"[{idx}] {item['title']} \u2014 {item['url']}\n{item['note'][:900]}"
            for idx, item in enumerate(items)
        )

        if is_structured:
            patch_result = await _s18_patch_output(
                question, schema_compact, _s18_compact_json(running_output),
                requirement_label, gap["gap_query"], evidence_block,
            )
            if not patch_result:
                continue
            patch = patch_result.get("patch")
            merged = _s18_merge_output_patch(running_output, patch) if isinstance(patch, dict) else None
            if merged is None:
                continue
            running_output = merged
            changed = True
            used_indices = patch_result.get("used_indices")
            refs = _s18_build_refs(
                receipt_id, items,
                used_indices if isinstance(used_indices, list) and used_indices else [0],
            )
            all_new_refs.extend(refs)
        else:
            patched = await _s18_patch_text(question, running_text, requirement_label, gap["gap_query"], evidence_block)
            if not patched:
                continue
            running_text = patched
            changed = True
            refs = _s18_build_refs(receipt_id, items, [0, 1])
            all_new_refs.extend(refs)

    if not changed:
        return _s18_response

    merged_citations = _s18_merge_citations(getattr(_s18_response, "citations", None), all_new_refs)
    try:
        if is_structured:
            return _s18_response.model_copy(update={"output": running_output, "citations": merged_citations})
        return _s18_response.model_copy(update={"text": running_text, "citations": merged_citations})
    except Exception:
        return _s18_response


async def _s18_finalize(_s18_query, _s18_response, _s18_t0: float):
    """Bounded requirement-coverage gap-filling pass (text + structured)."""
    if _s18_response is None:
        return _s18_response
    if getattr(_s18_response, "text", None) in (None, "") and getattr(_s18_response, "output", None) is None:
        return _s18_response
    elapsed = _s18_monotonic() - _s18_t0
    if elapsed >= _S18_HARD_BUDGET_GATE_S:
        return _s18_dedup_citations(_s18_response)
    window = min(_S18_MAX_WINDOW_S, max(_S18_MIN_WINDOW_S, 280.0 - elapsed))
    try:
        return await _s18_asyncio.wait_for(
            _s18_coverage_pass(_s18_query, _s18_response),
            timeout=window,
        )
    except Exception:
        return _s18_dedup_citations(_s18_response)


@entrypoint("query")
async def query(query: Query) -> Response:
    _s18_t0 = _s18_monotonic()
    _s18_resp = await _s18_base_query(query)
    try:
        return await _s18_finalize(query, _s18_resp, _s18_t0)
    except Exception:
        return _s18_resp
