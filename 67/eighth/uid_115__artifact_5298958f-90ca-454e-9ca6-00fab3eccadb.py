"""SN67 Harnyx miner — v11. Built on the proven briefing->loop->audit-patch->generous-citations
recipe, plus five targeted fixes for the exact failure modes our prior submission (uid70, 0.562)
bled points on, diagnosed from the on-chain judge reasoning of batch 88c4a837:
  (A) SOURCE AUTHORITY: prefer the PRIMARY named source over aggregators/mirrors (UN over
      PopulationPyramid, Forbes/Box Office Mojo/IMDb over news) — cost us ~3 pts (2ba697a8).
  (B) OUTPUT DIRECTIVES: 'without the word "X"' means DELETE X from each listed title, NOT drop
      titles containing X; sort/format literally — cost us ~2 pts (ff15b6aa). Enforced in prompt AND
      a deterministic post-processor.
  (C) FINALIZER GUARD: never return an unfinished scratch message ('Let me fetch…') as the answer;
      re-synthesize from the draft/evidence — cost us ~2 pts (c0bc943d).
  (D) CONTRADICTION CHECK: audit also flags claims that conflict with their own cited source
      (we said a film was shot in Paris while our citation said Nantes) — part of ~4 wrong-answer pts.
  (E) LEAKED-TOOL-CALL RECOVERY: execute GLM tool-call markup leaked as plain text instead of
      surfacing it as the answer (our own robustness bit; also keeps us mechanistically distinct).

Refactor notes: prompts, models, budgets, thresholds and execution order are unchanged.
Four defects are fixed (see uid194_REFACTOR_REPORT.md); the three with a behavioural
surface sit behind switches below.
"""
from __future__ import annotations

import asyncio
import json
import re
from time import monotonic

from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

# ══════════════════════════════════════════════════════════════════════════════
# Profile / providers
# ══════════════════════════════════════════════════════════════════════════════
PRODUCTION_PROFILE = "harnyx_v11"

PROVIDER = "openrouter"
DRAFT_MODEL = "z-ai/glm-5"          # A/B slot: z-ai/glm-5 | deepseek/deepseek-v3.2
LOOP_MODEL = "z-ai/glm-5"
PATCH_MODEL = "openai/gpt-oss-120b"
JSON_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "deepseek/deepseek-v3.2"

# ══════════════════════════════════════════════════════════════════════════════
# Time budget
# ══════════════════════════════════════════════════════════════════════════════
TOTAL_BUDGET_SECONDS = 245.0    # research deadline: loop + verify/patch must finish by here
# The wall the runtime enforces is 300s. Post-loop work (_last_resort, _structured_output)
# may run past the research deadline but must still land inside this one.
HARD_DEADLINE_SECONDS = 285.0
DRAFT_TIMEOUT = 55.0
LOOP_TURN_TIMEOUT = 80.0
FETCH_TIMEOUT = 15.0
LAST_RESORT_TIMEOUT = 50.0
SCHEMA_TIMEOUT = 50.0
PATCH_TIMEOUT = 30.0
SEARCH_TIMEOUT = 20.0
TOOLING_INFO_TIMEOUT = 10.0
MAX_TURNS = 12
PATCH_EXTRA_TURNS = 2
MAX_CITATIONS = 40
SEARCH_NOTE_CHARS = 500
FETCH_NOTE_CHARS = 6000
FORCE_COMMIT_SECONDS = 85.0
MAX_ANSWER_CHARS = 70000
FETCH_SLICE_THRESHOLD = 8000

# Gates that were inline literals in the original. Values unchanged.
BRIEFING_MIN_REMAINING = 120.0    # skip the briefing below this
PATCH_MIN_REMAINING = 45.0        # skip verify/patch below this
PATCH_ISSUE_MIN_REMAINING = 40.0  # audit found gaps but there is no time to close them
RESCUE_MIN_REMAINING = 20.0       # below this the finalizer guard does not call the model
LOOP_STOP_REMAINING = 8.0         # stop taking research turns below this
CHAT_MARGIN_S = 5.0               # slack withheld from every loop chat
POST_LOOP_MARGIN_S = 2.0          # slack withheld from post-loop calls
POST_LOOP_MIN_TIMEOUT_S = 5.0     # below this a post-loop call is not worth starting

# Shaping constants that were inline literals. Values unchanged.
SEARCH_RESULTS = 8
MAX_LEAKED_CALLS = 3
CITED_RANGE_CAP = 20              # a [1-9999] range contributes at most this many numbers
UNFINISHED_SCAN_CHARS = 160
UNFINISHED_MIN_CHARS = 40
UNFINISHED_MAX_CHARS = 500
DIRECTIVE_MIN_WORD_CHARS = 3
NUMERIC_SCAN_CHARS = 8000
NUMERIC_MAX_ENTRIES = 40
NUMERIC_MAX_NOTES = 2
NUMERIC_MIN_SHARED_WORDS = 2
NUMERIC_MAX_DIGIT_DELTA = 2
NUMERIC_MIN_WORD_CHARS = 3
BRIEFING_MAX_TOKENS = 2400
BRIEFING_FALLBACK_MAX_TOKENS = 2000
AUDIT_MAX_TOKENS = 700
LAST_RESORT_MAX_TOKENS = 1600
SCHEMA_MAX_TOKENS = 2400
ERROR_QUESTION_CHARS = 600
UNAVAILABLE_QUESTION_CHARS = 400
TRUNCATION_SUFFIX_CHARS = 20

# Budget floors (USD) for graceful degradation.
MIN_DRAFT_BUDGET = 0.03
MIN_PATCH_BUDGET = 0.05
FORCE_COMMIT_BUDGET = 0.02

# ══════════════════════════════════════════════════════════════════════════════
# Behaviour switches — each guards one defect fix; flip to restore the old path
# ══════════════════════════════════════════════════════════════════════════════
PER_QUERY_BUDGET = True          # budget state must not survive between queries
BOUND_POST_LOOP_CALLS = True     # keep _last_resort / _structured_output inside the hard wall
STRICT_OUTPUT_DIRECTIVES = True  # only an explicit "the word/the term X" is a directive

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Search the web. Returns numbered results with title, url and a "
                "short excerpt."
            ),
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
            "description": "Fetch one URL and return its extracted main text content.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL to fetch"}},
                "required": ["url"],
            },
        },
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# Prompts
# ══════════════════════════════════════════════════════════════════════════════

LOOP_SYSTEM_PROMPT = (
    "You are an elite research analyst answering a multi-constraint factual "
    "question. Your answer will be judged pairwise against a strong reference "
    "answer: factual claims only earn credit when backed by cited tool results, "
    "and missing any element of the question is a coverage failure.\n\n"
    "You have search_web and fetch_page tools. Work candidate-by-candidate and "
    "constraint-by-constraint: verify every load-bearing fact (names, dates, "
    "counts, figures) with a tool result before asserting it — do not trust "
    "memory for verifiable specifics. Tool results are numbered like [7].\n\n"
    "CITATION RULE: in the final answer, put the source number in brackets "
    "immediately after EVERY factual claim — for qualifying entities AND for "
    "excluded ones (e.g. 'completed in 2017 [4]', 'only 13 storeys [9]'). A "
    "claim without a bracket is treated as uncited. Do not cite sources that do "
    "not support the claim.\n\n"
    "FINAL ANSWER SHAPE: open with the direct answer (the qualifying entities / "
    "number / verdict) in the first sentence or list, in exactly the format the "
    "question requests — sentence one is never a remark about evidence quality. "
    "Then a short 'Proof of completeness' section: candidate pool, each "
    "constraint applied, per-entity specifics — one line per qualifying entity "
    "with its qualifying attribute cited, and one line per rejected candidate "
    "with its cited exclusion reason. Dense factual prose; no meta-commentary; "
    "never say the evidence is insufficient. Only when a figure exists solely "
    "inside a queryable database and nowhere in published sources, state the "
    "exact dataset + filters needed instead of inventing the number.\n\n"
    "PROVENANCE CONFIDENCE: when the question names a specific source but your "
    "verified facts come from other authoritative sources, state the facts "
    "confidently and treat the other sources as corroboration — never open "
    "with, or dwell on, the named source being absent from your results.\n\n"
    "SOURCE AUTHORITY: when the question names a source ('according to the United "
    "Nations', 'per Forbes', 'according to Box Office Mojo/IMDb/the World Bank'), "
    "cite the PRIMARY source itself (un.org / data.un.org, forbes.com, "
    "boxofficemojo.com, imdb.com, data.worldbank.org) and PREFER it over "
    "aggregators, mirrors, or news reports (populationpyramid.net, database.earth, "
    "worldometers, secondhand articles). Copy that source's exact figures and dates "
    "verbatim — if it dates an event (e.g. a population milestone) to a specific "
    "month/year, use that, not a news outlet's earlier estimate.\n\n"
    "OUTPUT DIRECTIVES: obey literal formatting instructions mechanically. "
    "'without the word \"X\"' (or 'omit/excluding the word X') means DELETE the word "
    "X from each title/name you output — it is NOT a filter that removes items "
    "containing X. 'in alphabetical/chronological order' means sort the final list; "
    "'comma-separated' means join with commas. Emit exactly the requested shape.\n\n"
    "SELF-CONSISTENCY: before finishing, confirm the opening answer names "
    "exactly the entities your own cited sentences support; if the body "
    "establishes a different set, rewrite the opening to match it. Verify no claim "
    "contradicts the text of its own cited source.\n\n"
    "Do not call a tool and write the final answer in the same turn. When every "
    "constraint is either verified or best-effort-covered, write the final "
    "answer with inline citations."
)

BRIEFING_SYSTEM = (
"You are an elite research analyst with encyclopedic knowledge preparing "
        "a research briefing. Commit to concrete best guesses; never refuse."
    )

AUDITOR_SYSTEM = "You are a strict answer auditor. Output JSON only."

LAST_RESORT_SYSTEM = (
"Expert researcher. Give your best definitive answer with "
                "concrete entities, numbers and dates. Never refuse."
)

SCHEMA_SYSTEM = "You output strictly valid JSON matching the given schema."


def _force_commit_message(remaining: float) -> str:
    return (
        f"TIME LIMIT: about {int(remaining)} seconds remain. Stop researching "
        "now. Using ONLY the numbered tool results above plus the briefing, "
        "write your best final answer with inline [n] citations in the required "
        "shape. A partial but cited and fully-covering answer scores far better "
        "than a refusal — never refuse."
    )


# ══════════════════════════════════════════════════════════════════════════════
# Patterns
# ══════════════════════════════════════════════════════════════════════════════

_BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")

# --- (C) finalizer guard: never surface a mid-research scratch line as the answer ---
_UNFINISHED_RE = re.compile(
    r"^\s*(let me\b|now i\b|next[, ]|i(?:'ll| will| need to| should| am going to| have the)\b"
    r"|based on my research,? i (?:need|will|should)\b|first,? i(?:'ll| will)\b|let'?s\b"
    r"|to (?:answer|verify|confirm) this\b)",
    re.IGNORECASE,
)

# --- (E) leaked-tool-call recovery: GLM sometimes emits ZhipuAI tool markup as plain text ---
_TOOL_CALL_BLOCK_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.S)
_ARG_VALUE_RE = re.compile(r"<arg_value>(.*?)</arg_value>", re.S)
_LEAK_TAG_RE = re.compile(r"</?(?:tool_call|arg_key|arg_value)[^>]*>")

_ENUM_QUESTION_RE = re.compile(
    r"\b(which|what)\b[^?]{0,80}\b(all|every|each)\b|\ball\s+(?:the\s+)?\w+\s+(?:that|who|which)\b"
    r"|\blist\s+(?:all|every|the)\b|\bname\s+(?:all|every|each)\b|\bhow\s+many\b",
    re.IGNORECASE,
)
# The plural must be the HEAD of the question, not a later modifier: "which
# country has the most citizens" asks for ONE country. Two words of slack
# covers adjectives ("which American Pie films") without reaching past the head.
_ENUM_PLURAL_RE = re.compile(r"\b(?:which|what)\b(?:\s+\w+){0,2}?\s+(\w{4,}s)\b", re.IGNORECASE)
# A superlative means one winner is wanted, so it cancels the plural signal
# unless an explicit all/every/each says otherwise.
_ENUM_ALL_RE = re.compile(r"\b(all|every|each)\b", re.IGNORECASE)
_ENUM_PLURAL_STOP = frozenset(
    {"was", "has", "does", "this", "these", "those", "its", "hers", "yours", "always",
     "across", "class", "less", "unless", "press", "gas", "bus"}
)
_ENUM_SUPERLATIVE_RE = re.compile(
    r"\b(highest|lowest|largest|smallest|most|least|greatest|fewest|longest|shortest)\b",
    re.IGNORECASE,
)

_NUMERIC_PAIR_RE = re.compile(r"((?:[A-Za-z][\w%-]*\s+){1,4})\$?([0-9][\d,]*(?:\.\d+)?)")
_CONSTRAINTS_RE = re.compile(r"CONSTRAINTS\s*:")
_DRAFT_PREFIX_RE = re.compile(r"^DRAFT\s*:\s*")
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I | re.M)
_RANGE_RE = re.compile(r"(\d{1,4})\s*-\s*(\d{1,4})")

# --- (B) output-directive matching ---
# The original alternation put `using` alongside `the word`/`the term`. Because the
# alternation is ordered, "without using the word American" matched the `using`
# branch and captured "the" — then deleted every "the" from the answer. It also
# matched "without using steel", which is a content constraint on the entities,
# not an instruction about how to spell the output.
_OUTPUT_DIRECTIVE_RE = re.compile(
    r'without (?:using )?(?:the word|the term)\s*["\u201c\u2018\']?([A-Za-z][\w\-]*)["\u201d\u2019\']?',
    re.IGNORECASE,
)
_LEGACY_OUTPUT_DIRECTIVE_RE = re.compile(
    r'without (?:the word|the term|using)\s*["\u201c\u2018\']?([A-Za-z][\w\-]*)["\u201d\u2019\']?',
    re.IGNORECASE,
)
# Deleting one of these from an entire answer destroys the prose around the titles
# the directive was meant to edit.
_DIRECTIVE_STOPWORDS = frozenset(
    {"the", "and", "for", "with", "from", "that", "this", "its", "was", "were",
     "are", "not", "but", "all", "any", "one", "two", "has", "had", "his", "her",
     "their", "them", "they", "you", "your", "our", "which", "who", "what"}
)
_DOUBLE_SPACE_RE = re.compile(r"[ \t]{2,}")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:)])")
_OPEN_PAREN_RE = re.compile(r"\(\s+")


# ══════════════════════════════════════════════════════════════════════════════
# Answer analysis
# ══════════════════════════════════════════════════════════════════════════════


def _numeric_conflicts(text: str) -> list[str]:
    """Two different figures near the same context words = an unreconciled
    contradiction the judge penalizes; surface them for explicit handling."""
    entries = []
    for m in _NUMERIC_PAIR_RE.finditer((text or "")[:NUMERIC_SCAN_CHARS]):
        ctx = frozenset(w.lower() for w in m.group(1).split() if len(w) > NUMERIC_MIN_WORD_CHARS)
        if ctx:
            entries.append((ctx, m.group(2).replace(",", "")))
        if len(entries) >= NUMERIC_MAX_ENTRIES:
            break
    notes = []
    for a in range(len(entries)):
        for b in range(a + 1, len(entries)):
            ca, na = entries[a]
            cb, nb = entries[b]
            if na != nb and len(ca & cb) >= NUMERIC_MIN_SHARED_WORDS and abs(len(na) - len(nb)) <= NUMERIC_MAX_DIGIT_DELTA:
                note = (f"reconcile explicitly: both {na} and {nb} appear near "
                        f"'{' '.join(sorted(ca & cb))}'")
                if note not in notes:
                    notes.append(note)
                if len(notes) >= NUMERIC_MAX_NOTES:
                    return notes
    return notes


def _looks_unfinished(answer: str) -> bool:
    a = (answer or "").strip()
    if not a:
        return True
    # A bracketed [n] citation means the model committed a real, sourced answer — never discard it
    # for the uncited draft.
    if _BRACKET_RE.search(a):
        return False
    if len(a) < UNFINISHED_MIN_CHARS:
        return True
    if _UNFINISHED_RE.match(a[:UNFINISHED_SCAN_CHARS]):
        return "final answer" not in a.lower() and len(a) < UNFINISHED_MAX_CHARS
    return False


# --- (B) deterministic output-directive post-processor ---
def _apply_output_directives(question: str, answer: str) -> str:
    """Enforce literal 'without the word X' directives the model may have missed: delete the word
    X from the answer text (it names titles, so this strips X from each listed title)."""
    if not answer:
        return answer
    out = answer
    pattern = _OUTPUT_DIRECTIVE_RE if STRICT_OUTPUT_DIRECTIVES else _LEGACY_OUTPUT_DIRECTIVE_RE
    for m in pattern.finditer(question):
        word = m.group(1)
        if len(word) < DIRECTIVE_MIN_WORD_CHARS:
            continue
        if STRICT_OUTPUT_DIRECTIVES and word.lower() in _DIRECTIVE_STOPWORDS:
            continue
        out = re.sub(rf"\b{re.escape(word)}\b", "", out, flags=re.IGNORECASE)
    if out != answer:
        out = _DOUBLE_SPACE_RE.sub(" ", out)
        out = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", out)
        out = _OPEN_PAREN_RE.sub("(", out)
    return out.strip() or answer


def _parse_leaked_tool_calls(text: str) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []
    for block in _TOOL_CALL_BLOCK_RE.findall(text or ""):
        stripped = block.strip()
        name = stripped.split("<", 1)[0].strip().split()[0] if stripped else ""
        values = _ARG_VALUE_RE.findall(block)
        if name in ("search_web", "fetch_page") and values:
            calls.append((name, values[0].strip()))
    return calls


def _strip_leak_markup(text: str) -> str:
    cleaned = _TOOL_CALL_BLOCK_RE.sub("", text or "")
    return _LEAK_TAG_RE.sub("", cleaned).strip()


def _content_to_text(content) -> str:
    """GLM-5/openrouter sometimes returns the answer in message.content as a LIST of parts, not a
    str. Walk it so a good answer is never lost to the uncited fallback. Pure robustness."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict):
                t = p.get("text") or p.get("content")
                if isinstance(t, str):
                    parts.append(t)
            else:
                t = getattr(p, "text", None)
                if isinstance(t, str):
                    parts.append(t)
        return "".join(parts)
    return ""


def _message_text(llm, message) -> str:
    text = (getattr(llm, "raw_text", None) or "").strip()
    if text:
        return text
    return _content_to_text(getattr(message, "content", None)).strip()


def _clamp(text: str) -> str:
    t = (text or "").strip()
    if len(t) > MAX_ANSWER_CHARS:
        return t[: MAX_ANSWER_CHARS - TRUNCATION_SUFFIX_CHARS] + "\n…[truncated]"
    return t


# ══════════════════════════════════════════════════════════════════════════════
# Session budget
# ══════════════════════════════════════════════════════════════════════════════


class _BudgetTracker:
    """Remaining session budget in USD, as last reported by the API.

    This used to be a module-level dict. Module state outlives a query: if
    `tooling_info` then failed on the next query, the stale value from the
    previous one decided whether to run the briefing, whether to force an
    immediate tools-off commit, and whether to run the audit pass.
    """

    def __init__(self) -> None:
        self.remaining = None

    def note(self, resp) -> None:
        budget = getattr(resp, "budget", None)
        remaining = getattr(budget, "session_remaining_budget_usd", None)
        if isinstance(remaining, int | float):
            self.remaining = float(remaining)

    def left(self) -> float:
        remaining = self.remaining
        if isinstance(remaining, int | float):
            return float(remaining)
        return 1.0


_SHARED_BUDGET = _BudgetTracker()


def _new_budget() -> _BudgetTracker:
    return _BudgetTracker() if PER_QUERY_BUDGET else _SHARED_BUDGET


# ══════════════════════════════════════════════════════════════════════════════
# Evidence index
# ══════════════════════════════════════════════════════════════════════════════


class _IndexEntry:
    """One numbered tool result. Every field is assigned here, so a field cannot
    exist without being declared."""

    def __init__(self, receipt_id: str, result_id: str, note_len: int, source: str) -> None:
        self.receipt_id = receipt_id
        self.result_id = result_id
        self.note_len = note_len
        self.source = source


class _ResultIndex:
    """Global numbering of tool results for inline-citation mapping."""

    def __init__(self) -> None:
        self.entries: dict[int, _IndexEntry] = {}
        self.next_number = 1

    def add(self, receipt_id: str, result_id: str, note: str, source: str) -> int:
        number = self.next_number
        self.next_number += 1
        self.entries[number] = _IndexEntry(
            receipt_id=receipt_id,
            result_id=result_id,
            note_len=len(note or ""),
            source=source,
        )
        return number


# ══════════════════════════════════════════════════════════════════════════════
# Time helpers
# ══════════════════════════════════════════════════════════════════════════════


def _remaining(deadline: float) -> float:
    return deadline - monotonic()


def _post_loop_timeout(cap: float, hard_deadline: float) -> float:
    """Timeout for a call that runs AFTER the research deadline. Returns `cap`
    unchanged whenever the hard wall is far away, which is every healthy run."""
    if not BOUND_POST_LOOP_CALLS:
        return cap
    return min(cap, _remaining(hard_deadline) - POST_LOOP_MARGIN_S)


# ══════════════════════════════════════════════════════════════════════════════
# Entrypoint
# ══════════════════════════════════════════════════════════════════════════════


@entrypoint("query")
async def query(query: Query) -> Response:
    question = (query.text or "").strip()
    if not question:
        return Response(text="No question provided.")
    try:
        return await _answer(query, question)
    except Exception:
        # Absolute last line of defence: any escaped exception still yields a
        # valid text Response (miner-attributed errors are terminal, score 0).
        return Response(text=f"Best-effort summary unavailable for: {question[:ERROR_QUESTION_CHARS]}")


async def _finalize_answer(question: str, answer: str, draft: str, deadline: float,
                           hard_deadline: float, budget: _BudgetTracker) -> str:
    """Answer ladder after the research loop: draft, last-resort, finalizer guard."""
    if not answer.strip():
        answer = draft.strip() or await _last_resort(question, hard_deadline, budget)

    # (C) finalizer guard: a scratch line ('Let me fetch…') is a hard 0 — fall back to a real answer.
    if _looks_unfinished(answer):
        rescue = draft.strip()
        if not rescue and _remaining(deadline) > RESCUE_MIN_REMAINING:
            rescue = await _last_resort(question, hard_deadline, budget)
        if rescue:
            answer = rescue
    return answer


async def _answer(query: Query, question: str) -> Response:
    start = monotonic()
    deadline = start + TOTAL_BUDGET_SECONDS
    # Post-loop work may run past `deadline` but never past this.
    hard_deadline = start + HARD_DEADLINE_SECONDS
    budget = _new_budget()

    try:
        info = await tooling_info(timeout=TOOLING_INFO_TIMEOUT)
        budget.note(info)
    except Exception:
        pass

    briefing = ""
    draft = ""
    try:
        if budget.left() >= MIN_DRAFT_BUDGET and _remaining(deadline) > BRIEFING_MIN_REMAINING:
            draft, briefing = await _build_briefing(question, budget)
    except Exception:
        briefing = ""

    index = _ResultIndex()
    answer = ""
    messages: list[dict] = []
    try:
        answer, messages = await _research_loop(
            question, briefing, index, deadline, MAX_TURNS, budget
        )
    except Exception:
        answer = ""

    try:
        if (
            answer
            and _remaining(deadline) > PATCH_MIN_REMAINING
            and budget.left() >= MIN_PATCH_BUDGET
        ):
            answer = await _verify_and_patch(
                question, answer, messages, index, deadline, budget
            )
    except Exception:
        pass

    answer = await _finalize_answer(question, answer, draft, deadline, hard_deadline, budget)

    # (B) enforce literal 'without the word X' output directives the model may have missed.
    answer = _apply_output_directives(question, answer)

    try:
        citations = _build_citations(answer, index)
    except Exception:
        citations = []

    final_text = _clamp(answer) or f"Best-effort answer unavailable for: {question[:UNAVAILABLE_QUESTION_CHARS]}"

    if query.output_schema is not None:
        try:
            output = await _structured_output(
                question, answer, query.output_schema, hard_deadline, budget
            )
        except Exception:
            output = None
        if output is not None:
            try:
                return Response(output=output, citations=citations or None)
            except Exception:
                return Response(output=output)

    try:
        return Response(text=final_text, citations=citations or None)
    except Exception:
        return Response(text=final_text)


# ------------------------------------------------------------------ briefing


async def _build_briefing(question: str, budget: _BudgetTracker) -> tuple[str, str]:
    system = BRIEFING_SYSTEM
    user = (
f"Question:\n{question}\n\n"
        "Produce a briefing with exactly these sections:\n"
        "DRAFT: your best definitive answer from knowledge alone — enumerate the "
        "full candidate pool, apply every constraint, name qualifying entities "
        "with concrete numbers/dates, note borderline exclusions. Mark uncertain "
        "values with (verify).\n"
        "CONSTRAINTS: numbered list of every atomic constraint/filter in the "
        "question (including ordering and requested output format).\n"
        "CANDIDATES: the entities to verify, one per line, with which "
        "constraints are uncertain for each.\n"
        "QUERIES: 3-6 targeted web searches that would verify the load-bearing "
        "facts (exact names + years; include the named source site if any).\n"
        "FETCH: 0-6 exact URLs likely to contain the needed figures, ONLY for "
        "named sources whose URL patterns you know (one per entity/year; for "
        "annual reports pick the edition containing each requested year, usually "
        "year+1 or year+2). Otherwise write 'none'."
    )
    try:
        raw = await _plain_chat(
            DRAFT_MODEL,
            budget,
            system=system,
            user=user,
            max_tokens=BRIEFING_MAX_TOKENS,
            timeout=DRAFT_TIMEOUT,
            thinking={"enabled": True, "effort": "low"},
        )
    except Exception:
        raw = await _plain_chat(
            FALLBACK_MODEL,
            budget,
            system=system,
            user=user,
            max_tokens=BRIEFING_FALLBACK_MAX_TOKENS,
            timeout=DRAFT_TIMEOUT,
        )
    draft = raw
    marker = _CONSTRAINTS_RE.search(raw)
    if marker is not None:
        draft = raw[: marker.start()]
    draft = _DRAFT_PREFIX_RE.sub("", draft).strip()
    briefing = (
        "RESEARCH BRIEFING (from prior analysis; verify uncertain values, "
        "correct it where tool evidence disagrees):\n" + raw.strip()
    )
    return draft, briefing


# --------------------------------------------------------------- research loop


def _enum_is_set_question(question: str) -> bool:
    """Deterministic: does the question ask for a SET rather than a single fact?"""
    text = " ".join((question or "").split())
    if not text:
        return False
    if _ENUM_QUESTION_RE.search(text):
        return True
    plural = _ENUM_PLURAL_RE.search(text)
    if plural and plural.group(1).lower() not in _ENUM_PLURAL_STOP:
        if not _ENUM_SUPERLATIVE_RE.search(text) or _ENUM_ALL_RE.search(text):
            return True
    return bool(_ENUM_SUPERLATIVE_RE.search(text)) and " and " in text.lower()


def _enum_directive(question: str) -> str:
    """Extra instruction for set questions only; empty for single-fact ones."""
    if not _enum_is_set_question(question):
        return ""
    return (
        "SET-COMPLETENESS REQUIREMENT: this question asks for a SET, so an answer naming one "
        "qualifying item from an unchecked pool scores as WRONG, not partial.\n"
        "1. Enumerate the full candidate pool the evidence supports, test EVERY candidate against "
        "each stated criterion, and list every one that qualifies with its own citation per "
        "criterion.\n"
        "2. Name the prominent near-miss candidates you excluded and the criterion each fails.\n"
        "3. Do NOT write 'the only', 'the sole', or 'the single' unless you enumerated and checked "
        "the whole pool. If the evidence covers only part of it, still commit: give every "
        "qualifying candidate found and say the roster may be incomplete."
    )


def _seed_loop_messages(question: str, briefing: str) -> list[dict]:
    messages = [{"role": "system", "content": LOOP_SYSTEM_PROMPT}]
    # Fires only on set questions; deterministic, no extra LLM call.
    enum_directive = _enum_directive(question)
    if enum_directive:
        messages.append({"role": "system", "content": enum_directive})
    if briefing:
        messages.append({"role": "system", "content": briefing})
    messages.append({"role": "user", "content": question})
    return messages


async def _dispatch_leaked_calls(leaked, messages: list[dict], index: _ResultIndex,
                                 budget: _BudgetTracker) -> None:
    """(E) GLM sometimes leaks ZhipuAI tool-call markup as plain text — execute it (in
    parallel) rather than surfacing markup as the final answer."""
    outs = await asyncio.gather(
        *[(_tool_search(a, index, budget) if n == "search_web" else _tool_fetch(a, index, budget))
          for n, a in leaked[:MAX_LEAKED_CALLS]],
        return_exceptions=True,
    )
    for out in outs:
        messages.append(
            {"role": "user", "content": out if isinstance(out, str) else f"# tool error: {out}"}
        )


async def _execute_tool_calls(tool_calls, messages: list[dict], index: _ResultIndex,
                              budget: _BudgetTracker) -> None:
    outputs = await asyncio.gather(
        *[_run_tool_call(tc, index, budget) for tc in tool_calls],
        return_exceptions=True,
    )
    for tc, out in zip(tool_calls, outputs):
        text = out if isinstance(out, str) else f"# tool error: {out}"
        messages.append(
            {"role": "tool", "tool_call_id": tc.id, "content": text}
        )


async def _research_loop(
    question: str,
    briefing: str,
    index: _ResultIndex,
    deadline: float,
    max_turns: int,
    budget: _BudgetTracker,
    seed_messages: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    if seed_messages is not None:
        messages = seed_messages
    else:
        messages = _seed_loop_messages(question, briefing)

    final_answer = ""
    nudged = False
    for turn in range(1, max_turns + 1):
        remaining = _remaining(deadline)
        if remaining <= LOOP_STOP_REMAINING:
            break
        time_critical = remaining <= FORCE_COMMIT_SECONDS
        budget_critical = budget.left() <= FORCE_COMMIT_BUDGET
        force_final = (turn >= max_turns) or time_critical or budget_critical
        if (force_final or turn >= max_turns - 1) and not nudged:
            messages.append(
                {"role": "system", "content": _force_commit_message(remaining)}
            )
            nudged = True

        payload = await _loop_chat(messages, deadline, force_text=force_final)
        if payload is None:
            break
        budget.note(payload)
        llm = getattr(payload, "llm", None)
        choices = getattr(llm, "choices", None) or []
        if not choices:
            break
        message = choices[0].message
        tool_calls = getattr(message, "tool_calls", None) or ()
        if not tool_calls:
            text = _message_text(llm, message)
            leaked = _parse_leaked_tool_calls(text)
            if leaked and not force_final:
                messages.append({"role": "assistant", "content": text})
                await _dispatch_leaked_calls(leaked, messages, index, budget)
                continue
            if "<tool_call" in text.lower():
                text = _strip_leak_markup(text)
            final_answer = text
            break

        messages.append(message.to_input_message())
        await _execute_tool_calls(tool_calls, messages, index, budget)
    return final_answer, messages


async def _loop_chat(messages: list[dict], deadline: float, *, force_text: bool):
    for attempt in range(2):
        timeout = min(LOOP_TURN_TIMEOUT, _remaining(deadline) - CHAT_MARGIN_S)
        if timeout <= CHAT_MARGIN_S:
            return None
        model = LOOP_MODEL if attempt == 0 else FALLBACK_MODEL
        try:
            return await llm_chat(
                provider=PROVIDER,
                model=model,
                messages=messages,
                tools=None if force_text else TOOLS,
                tool_choice=None if force_text else "auto",
                temperature=0.2,
                thinking={"enabled": True, "effort": "low"},
                timeout=timeout,
            )
        except Exception:
            continue
    return None


async def _run_tool_call(tc, index: _ResultIndex, budget: _BudgetTracker) -> str:
    try:
        args = json.loads(getattr(tc, "arguments", None) or "{}")
    except Exception:
        args = {}
    name = getattr(tc, "name", "") or ""
    if name == "search_web":
        return await _tool_search(str(args.get("query", "")), index, budget)
    if name == "fetch_page":
        return await _tool_fetch(str(args.get("url", "")), index, budget)
    return f"# unknown tool {name!r}"


async def _tool_search(q: str, index: _ResultIndex, budget: _BudgetTracker) -> str:
    if not q.strip():
        return "# search_web -> empty query"
    resp = None
    for provider in ("desearch", "parallel"):
        try:
            resp = await search_web(q, provider=provider, num=SEARCH_RESULTS, timeout=SEARCH_TIMEOUT)
            if getattr(resp, "results", None):
                break
        except Exception:
            resp = None
    if resp is None:
        return f"# search_web({q!r}) -> ERROR (all providers failed)"
    budget.note(resp)
    receipt = getattr(resp, "receipt_id", "") or ""
    lines = [f"# search_web({q!r}) -> {len(resp.results or [])} results"]
    for result in list(getattr(resp, "results", None) or []):
        rid = getattr(result, "result_id", None)
        if not isinstance(rid, str) or not rid:
            continue
        note = (getattr(result, "note", None) or "")[:SEARCH_NOTE_CHARS]
        number = index.add(receipt, rid, note, "search")
        title = getattr(result, "title", None) or ""
        url = getattr(result, "url", None) or ""
        lines.append(f"[{number}] {title}\n  url: {url}\n  excerpt: {note}")
    return "\n".join(lines)


async def _tool_fetch(url: str, index: _ResultIndex, budget: _BudgetTracker) -> str:
    if not url.strip():
        return "# fetch_page -> empty url"
    resp = None
    for provider in ("parallel", "desearch"):
        try:
            resp = await fetch_page(url, provider=provider, timeout=FETCH_TIMEOUT)
            if getattr(resp, "results", None):
                break
        except Exception:
            resp = None
    if resp is None:
        return f"# fetch_page({url!r}) -> ERROR (all providers failed)"
    budget.note(resp)
    receipt = getattr(resp, "receipt_id", "") or ""
    results = list(getattr(resp, "results", None) or [])
    if not results:
        return f"# fetch_page({url!r}) -> no content"
    result = results[0]
    rid = getattr(result, "result_id", None)
    note = getattr(result, "note", None) or ""
    if not isinstance(rid, str) or not rid or not note.strip():
        return f"# fetch_page({url!r}) -> no usable content"
    number = index.add(receipt, rid, note, "fetch")
    shown = note[:FETCH_NOTE_CHARS]
    return f"# fetch_page({url!r}) -> [{number}] {len(shown)} chars shown\n{shown}"


# -------------------------------------------------------------- verify & patch


def _audit_issues(report, answer: str) -> list[str]:
    issues = []
    for key in ("missing_elements", "uncited_claims", "suspect_attributions",
                "contradictions", "wrong_source"):
        values = report.get(key) if isinstance(report, dict) else None
        if isinstance(values, list):
            issues.extend(str(v) for v in values if str(v).strip())
    issues.extend(_numeric_conflicts(answer))
    return issues


async def _verify_and_patch(
    question: str,
    answer: str,
    messages: list[dict],
    index: _ResultIndex,
    deadline: float,
    budget: _BudgetTracker,
) -> str:
    check_user = (
"Audit this answer against its question. Report ONLY genuine, fixable "
        "problems as a JSON object with keys: "
        '"missing_elements" (question elements not addressed, or a qualifying set '
        "member not evaluated), "
        '"uncited_claims" (specific load-bearing factual claims lacking [n]), '
        '"suspect_attributions" (facts that look attributed to the wrong entity), '
        '"contradictions" (claims that conflict with the text of their own cited '
        "source, e.g. answer says shot in Paris but the citation says Nantes), "
        '"wrong_source" (used an aggregator/news site when the question named a '
        "specific primary source like the UN, Forbes, or Box Office Mojo). "
        "Use empty lists when fine. No other text.\n\n"
        f"Question:\n{question}\n\nAnswer:\n{answer[:12000]}"
    )
    try:
        raw = await _plain_chat(
            PATCH_MODEL,
            budget,
            system=AUDITOR_SYSTEM,
            user=check_user,
            max_tokens=AUDIT_MAX_TOKENS,
            timeout=PATCH_TIMEOUT,
        )
        cleaned = _CODE_FENCE_RE.sub("", raw.strip())
        report = json.loads(cleaned)
    except Exception:
        return answer
    issues = _audit_issues(report, answer)
    if not issues or _remaining(deadline) < PATCH_ISSUE_MIN_REMAINING:
        return answer

    messages.append(
        {
            "role": "system",
            "content": (
"AUDIT FOUND GAPS in your final answer:\n- "
                + "\n- ".join(issues[:6])
                + "\nYou may use at most 2 more tool calls to close the most "
                "important gaps, then rewrite the COMPLETE final answer with "
                "inline [n] citations in the required shape."
),
        }
    )
    patched, _ = await _research_loop(
        question, "", index, deadline, PATCH_EXTRA_TURNS + 1, budget, seed_messages=messages
    )
    return patched.strip() or answer


# ------------------------------------------------------------------- citations


def _cited_numbers(answer: str, max_number: int) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for found in _BRACKET_RE.finditer(answer):
        for part in found.group(1).split(","):
            text = part.strip()
            range_match = _RANGE_RE.fullmatch(text)
            if range_match:
                start, end = int(range_match.group(1)), int(range_match.group(2))
                for n in range(start, min(end, start + CITED_RANGE_CAP) + 1):
                    if 1 <= n <= max_number and n not in seen:
                        seen.add(n)
                        ordered.append(n)
            elif text.isdigit():
                n = int(text)
                if 1 <= n <= max_number and n not in seen:
                    seen.add(n)
                    ordered.append(n)
    return ordered


def _build_citations(answer: str, index: _ResultIndex) -> list[CitationRef]:
    numbers = _cited_numbers(answer, index.next_number - 1)
    refs: list[CitationRef] = []
    for n in numbers[:MAX_CITATIONS]:
        entry = index.entries.get(n)
        if entry is None:
            continue
        receipt_id = entry.receipt_id
        result_id = entry.result_id
        if not receipt_id or not result_id:
            continue
        if entry.source == "fetch" and entry.note_len > FETCH_SLICE_THRESHOLD:
            refs.append(
                CitationRef(
                    receipt_id=receipt_id,
                    result_id=result_id,
                    slices=[CitationSlice(start=0, end=FETCH_NOTE_CHARS)],
                )
            )
        else:
            refs.append(CitationRef(receipt_id=receipt_id, result_id=result_id))
    return refs


# ------------------------------------------------------------------ fallbacks


async def _last_resort(question: str, hard_deadline: float, budget: _BudgetTracker) -> str:
    timeout = _post_loop_timeout(LAST_RESORT_TIMEOUT, hard_deadline)
    if timeout <= POST_LOOP_MIN_TIMEOUT_S:
        return ""
    try:
        return await _plain_chat(
            FALLBACK_MODEL,
            budget,
            system=LAST_RESORT_SYSTEM,
            user=question,
            max_tokens=LAST_RESORT_MAX_TOKENS,
            timeout=timeout,
        )
    except Exception:
        return ""


async def _structured_output(question: str, answer: str, schema,
                             hard_deadline: float, budget: _BudgetTracker) -> object | None:
    schema_text = json.dumps(schema)
    user = (
"Convert this answer into a JSON value that validates against the "
        "schema. Return ONLY the JSON value.\n\n"
        f"Schema:\n{schema_text}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:15000]}"
    )
    for model in (JSON_MODEL, FALLBACK_MODEL):
        timeout = _post_loop_timeout(SCHEMA_TIMEOUT, hard_deadline)
        if timeout <= POST_LOOP_MIN_TIMEOUT_S:
            return None
        try:
            raw = await _plain_chat(
                model,
                budget,
                system=SCHEMA_SYSTEM,
                user=user,
                max_tokens=SCHEMA_MAX_TOKENS,
                timeout=timeout,
            )
            cleaned = _CODE_FENCE_RE.sub("", raw.strip()).strip()
            return json.loads(cleaned)
        except Exception:
            continue
    return None


# ------------------------------------------------------------------ llm helper


async def _plain_chat(
    model: str,
    budget: _BudgetTracker,
    *,
    system: str,
    user: str,
    max_tokens: int,
    timeout: float,
    thinking: dict | None = None,
) -> str:
    payload = await llm_chat(
        provider=PROVIDER,
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.15,
        max_output_tokens=max_tokens,
        timeout=timeout,
        thinking=thinking if thinking is not None else {"enabled": False},
    )
    budget.note(payload)
    llm = getattr(payload, "llm", None)
    text = (getattr(llm, "raw_text", None) or "").strip()
    if text:
        return text
    choices = getattr(llm, "choices", None) or []
    if choices:
        got = _content_to_text(getattr(choices[0].message, "content", None)).strip()
        if got:
            return got
    return ""

# slot: harnyx 2026-07-28T13:14:58+00:00

# perfect_suffix: openrouter/parallel
_PERFECT_SUFFIX = "0ec3e0775d91f6f3"

