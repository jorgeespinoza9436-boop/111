"""SN67 Harnyx miner — briefing -> tool loop -> audit-and-patch (profile agent_0723_v7).

A knowledge briefing seeds a native tool loop; the loop's answer is audited for gaps and
then optionally patched by re-entering the loop over the same transcript, with a guard that
refuses a revision thinner than the original. Every phase is clamped against the deadline so
no call can consume the window the next phase needs.

Refactor notes: prompts, models, budgets, thresholds, timeout arithmetic and execution order
are unchanged. Two defects are fixed (see uid120_REFACTOR_REPORT.md); both sit behind
switches below.
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
PRODUCTION_PROFILE = "agent_0723_v7"

PROVIDER = "openrouter"
DRAFT_MODEL = "z-ai/glm-5"          # A/B slot: z-ai/glm-5 | deepseek/deepseek-v3.2
LOOP_MODEL = "z-ai/glm-5"
PATCH_MODEL = "openai/gpt-oss-120b"
JSON_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "deepseek/deepseek-v3.2"

# ══════════════════════════════════════════════════════════════════════════════
# Time budget
# ══════════════════════════════════════════════════════════════════════════════
TOTAL_BUDGET_SECONDS = 245.0
SEARCH_TIMEOUT = 20.0
MAX_TURNS = 12
SEARCH_NOTE_CHARS = 500
PATCH_TIMEOUT = 30.0
FETCH_TIMEOUT = 15.0
PATCH_EXTRA_TURNS = 2
LOOP_TURN_TIMEOUT = 80.0
MAX_ANSWER_CHARS = 70000
MAX_CITATIONS = 40
FETCH_SLICE_THRESHOLD = 8000
DRAFT_TIMEOUT = 55.0
FORCE_COMMIT_SECONDS = 85.0
FETCH_NOTE_CHARS = 6000

# Wall-clock reserves. Every phase is clamped against the deadline so no single
# call can consume the window the next phase needs.
FINAL_RESERVE = 45.0       # kept free during research for the forced final turn
TAIL_RESERVE = 6.0         # kept free for response assembly
SCHEMA_RESERVE = 35.0      # kept free for output_schema conversion
SALVAGE_TIMEOUT = 40.0
MIN_TOOL_TIMEOUT = 5.0
MIN_CHAT_TIMEOUT = 8.0
PATCH_MIN_RATIO = 0.55     # a patch may not shrink the answer below this

# Gates and shaping constants that were inline literals. Values unchanged.
TOOLING_INFO_TIMEOUT = 10.0
BRIEFING_MIN_REMAINING = 120.0    # skip the briefing below this
PATCH_MIN_REMAINING = 45.0        # skip verify/patch below this
PATCH_ISSUE_MIN_REMAINING = 40.0  # audit found gaps but there is no time to close them
LOOP_TAIL_MARGIN = 2.0            # stop taking turns below TAIL_RESERVE + this
LAST_RESORT_TIMEOUT = 50.0
SCHEMA_TIMEOUT = 50.0
SEARCH_RESULTS = 8
BRIEFING_MAX_TOKENS = 2400
BRIEFING_FALLBACK_MAX_TOKENS = 2000
AUDIT_MAX_TOKENS = 700
LAST_RESORT_MAX_TOKENS = 1600
SCHEMA_MAX_TOKENS = 2400
CITED_RANGE_CAP = 20              # a [1-9999] range contributes at most this many numbers
PATCH_MIN_CHARS = 80              # a revision shorter than this is never accepted
PATCH_CITE_RATIO = 0.6            # a revision must keep this share of the original citations
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
PER_QUERY_BUDGET = True      # budget state must not survive between queries
CACHE_EMPTY_SEARCHES = False # caching a 0-result rendering blocks every retry of that query

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
    "SELF-CONSISTENCY: before finishing, confirm the opening answer names "
    "exactly the entities your own cited sentences support; if the body "
    "establishes a different set, rewrite the opening to match it.\n\n"
    "Do not call a tool and write the final answer in the same turn. When every "
    "constraint is either verified or best-effort-covered, write the final "
    "answer with inline citations."
)

_EMPTY_RETRY_MESSAGE = (
    "Your last turn returned no content. Either call a tool or write the "
    "COMPLETE final answer now, with inline [n] citations in the required "
    "shape. Never return an empty turn."
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

# Defined before its first use: the original declared it below _accept_patch,
# which reads it.
_BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")

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

_CONSTRAINTS_RE = re.compile(r"CONSTRAINTS\s*:")
_DRAFT_PREFIX_RE = re.compile(r"^DRAFT\s*:\s*")
_RANGE_RE = re.compile(r"(\d{1,4})\s*-\s*(\d{1,4})")


# ══════════════════════════════════════════════════════════════════════════════
# Payload helpers
# ══════════════════════════════════════════════════════════════════════════════


def _payload_text(payload) -> str:
    llm = getattr(payload, "llm", None)
    text = (getattr(llm, "raw_text", None) or "").strip()
    if text:
        return text
    choices = getattr(llm, "choices", None) or []
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


def _extract_json(raw: str) -> object:
    """Tolerant JSON extraction: fenced blocks, prose wrappers, bare values."""
    text = (raw or "").strip()
    if text.startswith("```"):
        newline = text.find("\n")
        if newline != -1:
            text = text[newline + 1 :]
        stripped = text.rstrip()
        if stripped.endswith("```"):
            text = stripped[:-3]
    text = text.strip()
    if not text:
        raise ValueError("empty payload")
    try:
        return json.loads(text)
    except Exception:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                continue
    raise ValueError("no json value found")


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
        # Repeated identical tool calls reuse the first rendering instead of
        # re-spending time/budget and inflating the citation index.
        self.tool_cache: dict[str, str] = {}

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


def _chat_timeout(deadline: float, cap: float, reserve: float) -> float:
    """Largest timeout that still leaves `reserve` seconds for later phases."""
    return min(cap, _remaining(deadline) - reserve)


def _tool_timeout(deadline: float, cap: float) -> float:
    return min(cap, _remaining(deadline) - FINAL_RESERVE)


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


async def _research_answer(question: str, briefing: str, index: _ResultIndex,
                           research_deadline: float, budget: _BudgetTracker) -> tuple[str, list]:
    """Research loop, then salvage from gathered evidence if it produced no text."""
    answer = ""
    messages: list[dict] = []
    try:
        answer, messages = await _research_loop(
            question, briefing, index, research_deadline, MAX_TURNS, budget
        )
    except Exception:
        answer = ""

    # The loop can end holding cited evidence but no written answer (turn cap,
    # provider failure, empty completion). Synthesise from that evidence rather
    # than discarding it for the uncited knowledge draft.
    if not answer.strip() and _has_tool_evidence(messages):
        try:
            answer = await _salvage_answer(messages, research_deadline, budget)
        except Exception:
            answer = ""
    return answer, messages


async def _answer(query: Query, question: str) -> Response:
    deadline = monotonic() + TOTAL_BUDGET_SECONDS
    schema = getattr(query, "output_schema", None)
    # Schema conversion is a hard requirement when requested, so research gives
    # back the time it needs instead of racing it at the end.
    research_deadline = deadline - (SCHEMA_RESERVE if schema is not None else 0.0)
    budget = _new_budget()

    try:
        info = await tooling_info(timeout=TOOLING_INFO_TIMEOUT)
        budget.note(info)
    except Exception:
        pass

    briefing = ""
    draft = ""
    try:
        if budget.left() >= MIN_DRAFT_BUDGET and _remaining(research_deadline) > BRIEFING_MIN_REMAINING:
            draft, briefing = await _build_briefing(question, research_deadline, budget)
    except Exception:
        briefing = ""

    index = _ResultIndex()
    answer, messages = await _research_answer(question, briefing, index, research_deadline, budget)

    try:
        if (
            answer
            and _remaining(research_deadline) > PATCH_MIN_REMAINING
            and budget.left() >= MIN_PATCH_BUDGET
        ):
            answer = await _verify_and_patch(
                question, answer, messages, index, research_deadline, budget
            )
    except Exception:
        pass

    if not answer.strip():
        answer = draft.strip() or await _last_resort(question, deadline, budget)

    final_text = _clamp(answer) or f"Best-effort answer unavailable for: {question[:UNAVAILABLE_QUESTION_CHARS]}"

    # Citations are derived from the text actually delivered, so a clamped tail
    # can never leave refs pointing at claims the grader cannot see.
    try:
        citations = _build_citations(final_text, index)
    except Exception:
        citations = []

    if schema is not None:
        try:
            output = await _structured_output(question, final_text, schema, deadline, budget)
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


async def _build_briefing(question: str, deadline: float,
                          budget: _BudgetTracker) -> tuple[str, str]:
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
    raw = ""
    timeout = _chat_timeout(deadline, DRAFT_TIMEOUT, FINAL_RESERVE)
    if timeout < MIN_CHAT_TIMEOUT:
        return "", ""
    try:
        raw = await _plain_chat(
            DRAFT_MODEL,
            budget,
            system=system,
            user=user,
            max_tokens=BRIEFING_MAX_TOKENS,
            timeout=timeout,
            thinking={"enabled": True, "effort": "low"},
        )
    except Exception:
        raw = ""
    if not raw.strip():
        timeout = _chat_timeout(deadline, DRAFT_TIMEOUT, FINAL_RESERVE)
        if timeout < MIN_CHAT_TIMEOUT:
            return "", ""
        try:
            raw = await _plain_chat(
                FALLBACK_MODEL,
                budget,
                system=system,
                user=user,
                max_tokens=BRIEFING_FALLBACK_MAX_TOKENS,
                timeout=timeout,
            )
        except Exception:
            return "", ""
    if not raw.strip():
        return "", ""
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


def _has_tool_evidence(messages: list) -> bool:
    for entry in messages or []:
        if isinstance(entry, dict) and entry.get("role") == "tool":
            return True
    return False


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


async def _execute_tool_calls(tool_calls, messages: list[dict], index: _ResultIndex,
                              deadline: float, budget: _BudgetTracker) -> None:
    try:
        outputs = await asyncio.gather(
            *[_run_tool_call(tc, index, deadline, budget) for tc in tool_calls],
            return_exceptions=True,
        )
    except Exception:
        outputs = ["# tool error: execution failed"] * len(tool_calls)
    # Every tool_call must get a reply or the transcript is invalid on reuse.
    for tc, out in zip(tool_calls, outputs):
        text_out = out if isinstance(out, str) else f"# tool error: {out}"
        messages.append(
            {
                "role": "tool",
                "tool_call_id": getattr(tc, "id", None) or "",
                "content": text_out,
            }
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
        if remaining <= TAIL_RESERVE + LOOP_TAIL_MARGIN:
            break
        time_critical = remaining <= FORCE_COMMIT_SECONDS
        budget_critical = budget.left() <= FORCE_COMMIT_BUDGET
        force_final = (turn >= max_turns) or time_critical or budget_critical
        if (force_final or turn >= max_turns - 1) and not nudged:
            messages.append(
                {"role": "system", "content": _force_commit_message(remaining)}
            )
            nudged = True

        try:
            payload = await _loop_chat(messages, deadline, force_text=force_final)
        except Exception:
            payload = None
        if payload is None:
            break
        budget.note(payload)
        llm = getattr(payload, "llm", None)
        choices = getattr(llm, "choices", None) or []
        if not choices:
            break
        message = getattr(choices[0], "message", None)
        if message is None:
            break
        tool_calls = getattr(message, "tool_calls", None) or ()
        if not tool_calls:
            text = _payload_text(payload)
            if text:
                final_answer = text
                # Keeping the committed answer in the transcript is what lets the
                # audit pass revise it instead of rewriting blind.
                messages.append({"role": "assistant", "content": final_answer})
                break
            if force_final or turn >= max_turns:
                break
            messages.append({"role": "system", "content": _EMPTY_RETRY_MESSAGE})
            continue

        try:
            messages.append(message.to_input_message())
        except Exception:
            # Transcript cannot be extended safely; stop with evidence intact.
            break
        await _execute_tool_calls(tool_calls, messages, index, deadline, budget)
    return final_answer, messages


async def _loop_chat(messages: list[dict], deadline: float, *, force_text: bool):
    # A research turn may never eat the window reserved for the final answer.
    reserve = TAIL_RESERVE if force_text else FINAL_RESERVE
    for attempt in range(2):
        timeout = _chat_timeout(deadline, LOOP_TURN_TIMEOUT, reserve)
        if timeout < MIN_CHAT_TIMEOUT:
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


async def _salvage_answer(messages: list[dict], deadline: float,
                          budget: _BudgetTracker) -> str:
    """One text-only synthesis over evidence already gathered."""
    convo = list(messages)
    room = _remaining(deadline) - TAIL_RESERVE
    if room < MIN_CHAT_TIMEOUT:
        return ""
    convo.append({"role": "system", "content": _force_commit_message(room)})
    for attempt in range(2):
        timeout = _chat_timeout(deadline, SALVAGE_TIMEOUT, TAIL_RESERVE)
        if timeout < MIN_CHAT_TIMEOUT:
            return ""
        model = LOOP_MODEL if attempt == 0 else FALLBACK_MODEL
        try:
            payload = await llm_chat(
                provider=PROVIDER,
                model=model,
                messages=convo,
                temperature=0.2,
                thinking={"enabled": False},
                timeout=timeout,
            )
        except Exception:
            continue
        budget.note(payload)
        text = _payload_text(payload)
        if text:
            return text
    return ""


# ------------------------------------------------------------------ tool calls


def _tool_call_arguments(tc) -> dict:
    raw_args = getattr(tc, "arguments", None)
    if raw_args is None:
        function = getattr(tc, "function", None)
        raw_args = getattr(function, "arguments", None)
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str) and raw_args.strip():
        try:
            parsed = json.loads(raw_args)
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
    return {}


def _tool_call_name(tc) -> str:
    name = getattr(tc, "name", None) or ""
    if not name:
        function = getattr(tc, "function", None)
        name = getattr(function, "name", None) or ""
    return name


async def _run_tool_call(tc, index: _ResultIndex, deadline: float,
                         budget: _BudgetTracker) -> str:
    args = _tool_call_arguments(tc)
    name = _tool_call_name(tc)
    if name == "search_web":
        value = args.get("query") or args.get("q") or args.get("search_query") or ""
        return await _tool_search(str(value), index, deadline, budget)
    if name == "fetch_page":
        value = args.get("url") or args.get("link") or ""
        return await _tool_fetch(str(value), index, deadline, budget)
    return f"# unknown tool {name!r}"


async def _best_provider_response(call, providers, cap: float, deadline: float):
    """Walk the provider ladder, keeping the first non-None response and stopping
    at the first one that actually carries results."""
    best = None
    for provider in providers:
        timeout = _tool_timeout(deadline, cap)
        if timeout < MIN_TOOL_TIMEOUT:
            break
        try:
            resp = await call(provider, timeout)
        except Exception:
            continue
        if resp is None:
            continue
        # A later provider failing must not discard an earlier valid response.
        if best is None:
            best = resp
        if getattr(resp, "results", None):
            best = resp
            break
    return best


async def _tool_search(q: str, index: _ResultIndex, deadline: float,
                       budget: _BudgetTracker) -> str:
    if not q.strip():
        return "# search_web -> empty query"
    key = "s:" + " ".join(q.split()).lower()
    cached = index.tool_cache.get(key)
    if cached is not None:
        return "# (already retrieved earlier — reusing the same numbered results)\n" + cached

    async def call(provider, timeout):
        return await search_web(q, provider=provider, num=SEARCH_RESULTS, timeout=timeout)

    best = await _best_provider_response(call, ("desearch", "parallel"), SEARCH_TIMEOUT, deadline)
    if best is None:
        if _tool_timeout(deadline, SEARCH_TIMEOUT) < MIN_TOOL_TIMEOUT:
            return (
                f"# search_web({q!r}) -> skipped (time limit reached; write the "
                "final answer from the results already gathered)"
            )
        return f"# search_web({q!r}) -> ERROR (all providers failed)"
    budget.note(best)
    receipt = getattr(best, "receipt_id", "") or ""
    results = list(getattr(best, "results", None) or [])
    lines = [f"# search_web({q!r}) -> {len(results)} results"]
    for result in results:
        rid = getattr(result, "result_id", None)
        if not isinstance(rid, str) or not rid:
            continue
        note = (getattr(result, "note", None) or "")[:SEARCH_NOTE_CHARS]
        number = index.add(receipt, rid, note, "search")
        title = getattr(result, "title", None) or ""
        url = getattr(result, "url", None) or ""
        lines.append(f"[{number}] {title}\n  url: {url}\n  excerpt: {note}")
    rendered = "\n".join(lines)
    # Caching a zero-result rendering would answer every later retry of this query
    # from the cache, so a transient empty response could never be retried.
    # _tool_fetch already caches only usable content; this matches it.
    if CACHE_EMPTY_SEARCHES or len(lines) > 1:
        index.tool_cache[key] = rendered
    return rendered


async def _tool_fetch(url: str, index: _ResultIndex, deadline: float,
                      budget: _BudgetTracker) -> str:
    if not url.strip():
        return "# fetch_page -> empty url"
    key = "f:" + url.strip()
    cached = index.tool_cache.get(key)
    if cached is not None:
        return "# (already fetched earlier — reusing the same numbered result)\n" + cached

    async def call(provider, timeout):
        return await fetch_page(url, provider=provider, timeout=timeout)

    best = await _best_provider_response(call, ("parallel", "desearch"), FETCH_TIMEOUT, deadline)
    if best is None:
        if _tool_timeout(deadline, FETCH_TIMEOUT) < MIN_TOOL_TIMEOUT:
            return (
                f"# fetch_page({url!r}) -> skipped (time limit reached; write the "
                "final answer from the results already gathered)"
            )
        return f"# fetch_page({url!r}) -> ERROR (all providers failed)"
    budget.note(best)
    receipt = getattr(best, "receipt_id", "") or ""
    results = list(getattr(best, "results", None) or [])
    if not results:
        return f"# fetch_page({url!r}) -> no content"
    result = results[0]
    rid = getattr(result, "result_id", None)
    note = getattr(result, "note", None) or ""
    if not isinstance(rid, str) or not rid or not note.strip():
        return f"# fetch_page({url!r}) -> no usable content"
    number = index.add(receipt, rid, note, "fetch")
    shown = note[:FETCH_NOTE_CHARS]
    rendered = f"# fetch_page({url!r}) -> [{number}] {len(shown)} chars shown\n{shown}"
    index.tool_cache[key] = rendered
    return rendered


# -------------------------------------------------------------- verify & patch


def _accept_patch(original: str, patched: str) -> bool:
    """A revision may not silently trade a complete answer for a thinner one."""
    new = (patched or "").strip()
    if len(new) < PATCH_MIN_CHARS:
        return False
    old = (original or "").strip()
    if len(new) < len(old) * PATCH_MIN_RATIO:
        return False
    old_cites = len(_BRACKET_RE.findall(old))
    if old_cites == 0:
        return True
    return len(_BRACKET_RE.findall(new)) >= max(1, int(old_cites * PATCH_CITE_RATIO))


async def _audit_report(check_user: str, budget: _BudgetTracker, deadline: float):
    timeout = _chat_timeout(deadline, PATCH_TIMEOUT, FINAL_RESERVE)
    if timeout < MIN_CHAT_TIMEOUT:
        raise ValueError("no time for audit")
    raw = await _plain_chat(
        PATCH_MODEL,
        budget,
        system=AUDITOR_SYSTEM,
        user=check_user,
        max_tokens=AUDIT_MAX_TOKENS,
        timeout=timeout,
    )
    return _extract_json(raw)


def _audit_issues(report) -> list[str]:
    issues = []
    for key in ("missing_elements", "uncited_claims", "suspect_attributions"):
        values = report.get(key) if isinstance(report, dict) else None
        if isinstance(values, list):
            issues.extend(str(v) for v in values if str(v).strip())
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
        '"missing_elements" (question elements not addressed), '
        '"uncited_claims" (specific load-bearing factual claims lacking [n]), '
        '"suspect_attributions" (facts that look attributed to the wrong '
        "entity). Use empty lists when fine. No other text.\n\n"
        f"Question:\n{question}\n\nAnswer:\n{answer[:12000]}"
    )
    try:
        report = await _audit_report(check_user, budget, deadline)
    except Exception:
        return answer
    issues = _audit_issues(report)
    if not issues or _remaining(deadline) < PATCH_ISSUE_MIN_REMAINING:
        return answer

    # Work on a copy: a failed revision must leave the original transcript,
    # and therefore the original answer, fully intact.
    convo = list(messages)
    last = convo[-1] if convo else None
    if not (
        isinstance(last, dict)
        and last.get("role") == "assistant"
        and last.get("content") == answer
    ):
        convo.append({"role": "assistant", "content": answer})
    convo.append(
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
        question, "", index, deadline, PATCH_EXTRA_TURNS + 1, budget, seed_messages=convo
    )
    if _accept_patch(answer, patched):
        return patched.strip()
    return answer


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
    emitted: set[tuple] = set()
    for n in numbers:
        if len(refs) >= MAX_CITATIONS:
            break
        entry = index.entries.get(n)
        if entry is None:
            continue
        receipt_id = entry.receipt_id
        result_id = entry.result_id
        if not receipt_id or not result_id:
            continue
        # The same source can be numbered twice across calls; emit it once so
        # duplicates do not consume the citation cap.
        pair = (receipt_id, result_id)
        if pair in emitted:
            continue
        emitted.add(pair)
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


async def _last_resort(question: str, deadline: float, budget: _BudgetTracker) -> str:
    timeout = _chat_timeout(deadline, LAST_RESORT_TIMEOUT, TAIL_RESERVE)
    if timeout < MIN_CHAT_TIMEOUT:
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


async def _structured_output(
    question: str, answer: str, schema, deadline: float, budget: _BudgetTracker
) -> object | None:
    schema_text = json.dumps(schema)
    user = (
"Convert this answer into a JSON value that validates against the "
        "schema. Return ONLY the JSON value.\n\n"
        f"Schema:\n{schema_text}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:15000]}"
    )
    for model in (JSON_MODEL, FALLBACK_MODEL):
        timeout = _chat_timeout(deadline, SCHEMA_TIMEOUT, TAIL_RESERVE)
        if timeout < MIN_CHAT_TIMEOUT:
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
            return _extract_json(raw)
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
    return _payload_text(payload)

# slot: harnyx 2026-07-28T13:14:58+00:00

# perfect_suffix: openrouter/parallel
_PERFECT_SUFFIX = "17200268ee3f2513"

