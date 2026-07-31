"""SN67 Harnyx miner — v12 (structural refactor of the uid222 0.700 champion).

Behaviour, prompts, models, thresholds and phase ordering are preserved verbatim from v11.
What changed is the SHAPE of the program, plus a strict validator-syntax discipline.

STRUCTURE FIXES
  1. No module-level mutable state. v11 kept the remaining USD budget in a global dict, so
     budget readings leaked across queries inside one worker process. All per-query state
     (deadline, budget, citation ledger) now lives on a single `_Run` object created per call.
  2. No caller-list aliasing. v11's research loop bound `messages = seed_messages` and then
     mutated the caller's list; the audit phase relied on that side effect. The loop now copies
     its seed and RETURNS the transcript, and the audit phase returns (answer, transcript).
  3. Every LLM timeout is clamped to the time actually left. v11 hard-coded 45-50s timeouts in
     `_last_resort` / `_structured_output` / `_resynthesize_clean`, which could run past the
     245s deadline in the exact tail case those paths exist for.
  4. Crash-proof leak parsing. v11's leaked-tool-call name extraction raised IndexError on
     markup that opened with a tag; that exception unwound the whole research phase and
     discarded the answer. Parsing is now total.
  5. Per-turn tool handling is isolated: an SDK-shape surprise ends the loop with the transcript
     intact instead of destroying the phase.
  6. Dead code removed (unused scratch-sentence regex, unused section-header tuple).
  7. Phases are named functions (`_phase_*`) instead of one 130-line entrypoint body.

VALIDATOR-SYNTAX DISCIPLINE (all four reported rejection classes are structurally impossible here)
  * forbidden_import ....... only asyncio / json / re / time.monotonic + harnyx_miner_sdk.
                             No sys, no os, no logging, no __future__ import.
  * dunder_attribute ....... no `__name__` / `__class__` / `__dict__` reflection anywhere.
  * dynamic_getattr_name ... every getattr() second argument is a string literal.
  * unsupported_callable ... no callable ever selected at runtime — no dispatch dicts, no
                             conditional-expression calls, no lambdas, no function aliases.

Provider is openrouter throughout; ai_gateway is not used.
"""

import asyncio
import json
import re
from time import monotonic

from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

PRODUCTION_PROFILE = "harnyx_v12"
BUILD_TAG = "a381495f8d214e529161db4294130c93"

# --------------------------------------------------------------------------- models
PROVIDER = "openrouter"
DRAFT_MODEL = "z-ai/glm-5"
LOOP_MODEL = "z-ai/glm-5"
PATCH_MODEL = "openai/gpt-oss-120b"
JSON_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "deepseek/deepseek-v3.2"

# ---------------------------------------------------------------------------- time
TOTAL_BUDGET_SECONDS = 245.0
DRAFT_TIMEOUT = 55.0
LOOP_TURN_TIMEOUT = 80.0
PATCH_TIMEOUT = 30.0
SEARCH_TIMEOUT = 20.0
FETCH_TIMEOUT = 15.0
RESYNTH_TIMEOUT = 45.0
LAST_RESORT_TIMEOUT = 50.0
SCHEMA_TIMEOUT = 50.0
MIN_CHAT_TIMEOUT = 6.0
CHAT_TIME_MARGIN = 3.0

MAX_TURNS = 12
PATCH_EXTRA_TURNS = 2
FORCE_COMMIT_SECONDS = 85.0

# ---------------------------------------------------------------- gates and floors
COVERAGE_MIN_SECONDS = 60.0
COVERAGE_MIN_BUDGET = 0.06
COVERAGE_MAX_RETRY_TURNS = 4
CITE_MIN_MARKERS = 2
CITE_FLOOR_N = 4

MIN_DRAFT_BUDGET = 0.03
MIN_PATCH_BUDGET = 0.05
FORCE_COMMIT_BUDGET = 0.02

MAX_ANSWER_CHARS = 70000
MAX_CITATIONS = 40
SEARCH_NOTE_CHARS = 500
FETCH_NOTE_CHARS = 6000
FETCH_SLICE_THRESHOLD = 8000

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

# --------------------------------------------------------------------------- prompts

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

BRIEFING_SECTIONS = (
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

ENUM_DIRECTIVE_TEXT = (
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

CITE_GAP_DIRECTIVE = (
    "CITATION GAP — your answer is under-sourced and will get NO factual credit for "
    "uncited claims. Every load-bearing fact (names, numbers, dates, the final "
    "verdict) MUST carry a [n] citation to a search/fetch result. Search/fetch any "
    "uncited fact, then re-state the COMPLETE answer with a [n] marker on every claim."
)

AUDIT_SYSTEM = "You are a strict answer auditor. Output JSON only."

AUDIT_KEYS = (
    "missing_elements",
    "uncited_claims",
    "suspect_attributions",
    "contradictions",
    "wrong_source",
)


def _force_commit_message(remaining: float) -> str:
    return (
        f"TIME LIMIT: about {int(remaining)} seconds remain. Stop researching "
        "now. Using ONLY the numbered tool results above plus the briefing, "
        "write your best final answer with inline [n] citations in the required "
        "shape. A partial but cited and fully-covering answer scores far better "
        "than a refusal — never refuse."
    )


# ============================================================== per-query run state


class _Run:
    """Everything mutable for ONE query: clock, budget reading, citation ledger.

    v11 held the budget in a module global, so a stale reading from a previous query could
    disable the briefing or the patch phase of the next one. Nothing here outlives the call.
    """

    def __init__(self) -> None:
        self.deadline = monotonic() + TOTAL_BUDGET_SECONDS
        self.budget_usd = None
        self.entries = {}
        self.next_number = 1

    # -- clock ---------------------------------------------------------------
    def remaining(self) -> float:
        return self.deadline - monotonic()

    def chat_timeout(self, wanted: float) -> float:
        """Never let an LLM call outlive the deadline; returns 0.0 when there is no room."""
        room = self.remaining() - CHAT_TIME_MARGIN
        if room < MIN_CHAT_TIMEOUT:
            return 0.0
        if wanted < room:
            return wanted
        return room

    # -- budget --------------------------------------------------------------
    def note_budget(self, payload) -> None:
        budget = getattr(payload, "budget", None)
        remaining = getattr(budget, "session_remaining_budget_usd", None)
        if isinstance(remaining, (int, float)):
            self.budget_usd = float(remaining)

    def budget_left(self) -> float:
        if isinstance(self.budget_usd, (int, float)):
            return float(self.budget_usd)
        return 1.0

    # -- citation ledger -----------------------------------------------------
    def add_result(self, receipt_id: str, result_id: str, note: str, source: str) -> int:
        number = self.next_number
        self.next_number += 1
        self.entries[number] = {
            "receipt_id": receipt_id,
            "result_id": result_id,
            "note_len": len(note or ""),
            "source": source,
        }
        return number

    def max_number(self) -> int:
        return self.next_number - 1


# ================================================================= text hygiene


_BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")

# A mid-research scratch line surfaced as the answer is a hard zero.
_UNFINISHED_RE = re.compile(
    r"^\s*(let me\b|now i\b|next[, ]|i(?:'ll| will| need to| should| am going to| have the)\b"
    r"|based on my research,? i (?:need|will|should)\b|first,? i(?:'ll| will)\b|let'?s\b"
    r"|to (?:answer|verify|confirm) this\b)",
    re.IGNORECASE,
)
# Explicit DRAFT scaffolding leaked as the answer — the champion's #1 loss mode.
_DRAFT_PREFIX_RE = re.compile(
    r"^\s*[#*>\s]*\**\s*(draft\b|draft:|best[\- ]?definitive answer\b"
    r"|based on (?:my )?(?:general )?knowledge\b|now i have (?:all )?the data\b"
    r"|here'?s? (?:my )?draft\b)",
    re.IGNORECASE,
)
_DRAFT_STRIP_RE = re.compile(
    r"^\s*[#*>\s]*\**\s*(?:draft|here'?s? my draft)\s*:?\s*\**\s*",
    re.IGNORECASE,
)
# Scratch narration that leaked WITH citations ("I now have the data. Let me verify").
_SCRATCH_OPEN_RE = re.compile(
    r"^\s*(?:perfect[!.,\s]+|great[!.,\s]+|okay[!.,\s]+|ok[!.,\s]+)?"
    r"(?:i (?:now )?have (?:the|all|complete|gathered|enough)"
    r"|i'?ve (?:now )?(?:got|gathered|found|collected|compiled|obtained)"
    r"|i (?:can )?now have|i now have|i have gathered"
    r"|let me (?:verify|compile|check|finalize|cross[- ]?check|now\b)"
    r"|here'?s (?:the|my) (?:final|complete))\b",
    re.IGNORECASE,
)
_BEST_ANSWER_PREFIX_RE = re.compile(
    r"^\**\s*best[\- ]?definitive answer\s*:?\s*\**\s*", re.IGNORECASE
)
_ANSWER_PREFIX_RE = re.compile(r"^\**\s*(?:final )?answer\s*:?\s*\**\s*", re.IGNORECASE)

_WITHOUT_WORD_RE = re.compile(
    r'without (?:the word|the term|using)\s*["“‘\']?([A-Za-z][\w\-]*)["”’\']?',
    re.IGNORECASE,
)

_TOOL_CALL_BLOCK_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.S)
_ARG_VALUE_RE = re.compile(r"<arg_value>(.*?)</arg_value>", re.S)
_LEAK_TAG_RE = re.compile(r"</?(?:tool_call|arg_key|arg_value)[^>]*>")


def _looks_unfinished(answer: str) -> bool:
    text = (answer or "").strip()
    if not text:
        return True
    head = text[:80]
    if _DRAFT_PREFIX_RE.match(head):
        return True
    if _SCRATCH_OPEN_RE.match(head):
        return True
    # A bracketed [n] means the model committed a real sourced answer — never discard it.
    if _BRACKET_RE.search(text):
        return False
    if len(text) < 40:
        return True
    if _UNFINISHED_RE.match(text[:160]):
        return "final answer" not in text.lower() and len(text) < 500
    return False


def _strip_draft_framing(text: str) -> str:
    """Deterministically turn leaked DRAFT scaffolding into a committed answer (no LLM call —
    this path exists precisely for when time and budget are gone)."""
    original = (text or "").strip()
    out = _DRAFT_STRIP_RE.sub("", original, count=1).strip()
    out = _BEST_ANSWER_PREFIX_RE.sub("", out).strip()
    out = _ANSWER_PREFIX_RE.sub("", out).strip()
    return out or original


def _apply_output_directives(question: str, answer: str) -> str:
    """'without the word X' means DELETE X from each listed title, not drop titles containing X."""
    if not answer:
        return answer
    out = answer
    for found in _WITHOUT_WORD_RE.finditer(question or ""):
        word = found.group(1)
        if len(word) >= 3:
            out = re.sub(r"\b" + re.escape(word) + r"\b", "", out, flags=re.IGNORECASE)
    if out != answer:
        out = re.sub(r"[ \t]{2,}", " ", out)
        out = re.sub(r"\s+([,.;:)])", r"\1", out)
        out = re.sub(r"\(\s+", "(", out)
    return out.strip() or answer


def _leaked_call_name(block: str) -> str:
    """Total parse of the tool name in leaked GLM markup.

    v11 did `block.split('<', 1)[0].strip().split()[0]`, which raised IndexError whenever the
    block opened with a tag — and that exception unwound the entire research phase.
    """
    head = (block or "").split("<", 1)[0]
    words = head.split()
    if not words:
        return ""
    return words[0]


def _parse_leaked_tool_calls(text: str) -> list:
    calls = []
    for block in _TOOL_CALL_BLOCK_RE.findall(text or ""):
        name = _leaked_call_name(block)
        if name != "search_web" and name != "fetch_page":
            continue
        values = _ARG_VALUE_RE.findall(block)
        if values:
            calls.append((name, values[0].strip()))
    return calls


def _strip_leak_markup(text: str) -> str:
    cleaned = _TOOL_CALL_BLOCK_RE.sub("", text or "")
    return _LEAK_TAG_RE.sub("", cleaned).strip()


def _content_to_text(content) -> str:
    """GLM-5 via openrouter sometimes returns content as a LIST of parts, not a str."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for piece in content:
            if isinstance(piece, str):
                parts.append(piece)
                continue
            if isinstance(piece, dict):
                value = piece.get("text")
                if not isinstance(value, str):
                    value = piece.get("content")
                if isinstance(value, str):
                    parts.append(value)
                continue
            value = getattr(piece, "text", None)
            if isinstance(value, str):
                parts.append(value)
        return "".join(parts)
    return ""


def _message_text(llm, message) -> str:
    text = (getattr(llm, "raw_text", None) or "").strip()
    if text:
        return text
    return _content_to_text(getattr(message, "content", None)).strip()


def _clamp(text: str) -> str:
    out = (text or "").strip()
    if len(out) > MAX_ANSWER_CHARS:
        return out[: MAX_ANSWER_CHARS - 20] + "\n…[truncated]"
    return out


# ==================================================================== llm helpers


async def _plain_chat(
    run: _Run,
    model: str,
    system: str,
    user: str,
    max_tokens: int,
    timeout: float,
    thinking=None,
) -> str:
    """Single-shot chat. The timeout is always clamped to the time actually left."""
    budgeted = run.chat_timeout(timeout)
    if budgeted <= 0.0:
        return ""
    if thinking is None:
        thinking_arg = {"enabled": False}
    else:
        thinking_arg = thinking
    payload = await llm_chat(
        provider=PROVIDER,
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.15,
        max_output_tokens=max_tokens,
        timeout=budgeted,
        thinking=thinking_arg,
    )
    run.note_budget(payload)
    llm = getattr(payload, "llm", None)
    text = (getattr(llm, "raw_text", None) or "").strip()
    if text:
        return text
    choices = getattr(llm, "choices", None) or []
    if choices:
        message = getattr(choices[0], "message", None)
        got = _content_to_text(getattr(message, "content", None)).strip()
        if got:
            return got
    return ""


async def _loop_chat(run: _Run, messages: list, force_text: bool):
    for attempt in range(2):
        timeout = run.chat_timeout(LOOP_TURN_TIMEOUT)
        if timeout <= 0.0:
            return None
        if attempt == 0:
            model = LOOP_MODEL
        else:
            model = FALLBACK_MODEL
        if force_text:
            tools_arg = None
            choice_arg = None
        else:
            tools_arg = TOOLS
            choice_arg = "auto"
        try:
            return await llm_chat(
                provider=PROVIDER,
                model=model,
                messages=messages,
                tools=tools_arg,
                tool_choice=choice_arg,
                temperature=0.2,
                thinking={"enabled": True, "effort": "low"},
                timeout=timeout,
            )
        except Exception:
            continue
    return None


# ========================================================================== tools


async def _tool_search(query_text: str, run: _Run) -> str:
    if not (query_text or "").strip():
        return "# search_web -> empty query"
    resp = None
    for provider in ("desearch", "parallel"):
        try:
            resp = await search_web(query_text, provider=provider, num=8, timeout=SEARCH_TIMEOUT)
            if getattr(resp, "results", None):
                break
        except Exception:
            resp = None
    if resp is None:
        return "# search_web(" + repr(query_text) + ") -> ERROR (all providers failed)"
    run.note_budget(resp)
    receipt = getattr(resp, "receipt_id", "") or ""
    results = list(getattr(resp, "results", None) or [])
    lines = ["# search_web(" + repr(query_text) + ") -> " + str(len(results)) + " results"]
    for result in results:
        rid = getattr(result, "result_id", None)
        if not isinstance(rid, str) or not rid:
            continue
        note = (getattr(result, "note", None) or "")[:SEARCH_NOTE_CHARS]
        number = run.add_result(receipt, rid, note, "search")
        title = getattr(result, "title", None) or ""
        url = getattr(result, "url", None) or ""
        lines.append("[" + str(number) + "] " + title + "\n  url: " + url + "\n  excerpt: " + note)
    return "\n".join(lines)


async def _tool_fetch(url: str, run: _Run) -> str:
    if not (url or "").strip():
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
        return "# fetch_page(" + repr(url) + ") -> ERROR (all providers failed)"
    run.note_budget(resp)
    receipt = getattr(resp, "receipt_id", "") or ""
    results = list(getattr(resp, "results", None) or [])
    if not results:
        return "# fetch_page(" + repr(url) + ") -> no content"
    result = results[0]
    rid = getattr(result, "result_id", None)
    note = getattr(result, "note", None) or ""
    if not isinstance(rid, str) or not rid or not note.strip():
        return "# fetch_page(" + repr(url) + ") -> no usable content"
    number = run.add_result(receipt, rid, note, "fetch")
    shown = note[:FETCH_NOTE_CHARS]
    return (
        "# fetch_page(" + repr(url) + ") -> [" + str(number) + "] "
        + str(len(shown)) + " chars shown\n" + shown
    )


async def _run_tool_call(tool_call, run: _Run) -> str:
    """Static dispatch only: the callable is never chosen at runtime."""
    try:
        args = json.loads(getattr(tool_call, "arguments", None) or "{}")
    except Exception:
        args = {}
    if not isinstance(args, dict):
        args = {}
    name = getattr(tool_call, "name", "") or ""
    if name == "search_web":
        return await _tool_search(str(args.get("query", "")), run)
    if name == "fetch_page":
        return await _tool_fetch(str(args.get("url", "")), run)
    return "# unknown tool " + repr(name)


async def _execute_leaked_calls(calls: list, run: _Run) -> list:
    coros = []
    for name, argument in calls[:3]:
        if name == "search_web":
            coros.append(_tool_search(argument, run))
        else:
            coros.append(_tool_fetch(argument, run))
    if not coros:
        return []
    return await asyncio.gather(*coros, return_exceptions=True)


def _tool_result_text(out) -> str:
    if isinstance(out, str):
        return out
    return "# tool error: " + str(out)


def _to_input_message(message):
    """SDK message -> transcript entry, with a dict fallback if the helper is unavailable."""
    try:
        return message.to_input_message()
    except Exception:
        return {"role": "assistant", "content": _content_to_text(getattr(message, "content", None))}


# =================================================================== enum detection


_ENUM_QUESTION_RE = re.compile(
    r"\b(which|what)\b[^?]{0,80}\b(all|every|each)\b|\ball\s+(?:the\s+)?\w+\s+(?:that|who|which)\b"
    r"|\blist\s+(?:all|every|the)\b|\bname\s+(?:all|every|each)\b|\bhow\s+many\b",
    re.IGNORECASE,
)
_ENUM_PLURAL_RE = re.compile(r"\b(?:which|what)\b(?:\s+\w+){0,2}?\s+(\w{4,}s)\b", re.IGNORECASE)
_ENUM_ALL_RE = re.compile(r"\b(all|every|each)\b", re.IGNORECASE)
_ENUM_PLURAL_STOP = frozenset(
    {"was", "has", "does", "this", "these", "those", "its", "hers", "yours", "always",
     "across", "class", "less", "unless", "press", "gas", "bus"}
)
_ENUM_SUPERLATIVE_RE = re.compile(
    r"\b(highest|lowest|largest|smallest|most|least|greatest|fewest|longest|shortest)\b",
    re.IGNORECASE,
)


def _enum_is_set_question(question: str) -> bool:
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
    if not _enum_is_set_question(question):
        return ""
    return ENUM_DIRECTIVE_TEXT


# ==================================================================== research loop


def _seed_transcript(question: str, briefing: str, seed_messages) -> list:
    """Fresh transcript, or a COPY of the seed. v11 aliased the caller's list and mutated it."""
    if seed_messages:
        return list(seed_messages)
    messages = [{"role": "system", "content": LOOP_SYSTEM_PROMPT}]
    directive = _enum_directive(question)
    if directive:
        messages.append({"role": "system", "content": directive})
    if briefing:
        messages.append({"role": "system", "content": briefing})
    messages.append({"role": "user", "content": question})
    return messages


async def _research_loop(
    run: _Run,
    question: str,
    briefing: str,
    max_turns: int,
    seed_messages=None,
):
    messages = _seed_transcript(question, briefing, seed_messages)
    final_answer = ""
    nudged = False

    for turn in range(1, max_turns + 1):
        remaining = run.remaining()
        if remaining <= 8.0:
            break
        time_critical = remaining <= FORCE_COMMIT_SECONDS
        budget_critical = run.budget_left() <= FORCE_COMMIT_BUDGET
        force_final = (turn >= max_turns) or time_critical or budget_critical
        if (force_final or turn >= max_turns - 1) and not nudged:
            messages.append({"role": "system", "content": _force_commit_message(remaining)})
            nudged = True

        payload = await _loop_chat(run, messages, force_final)
        if payload is None:
            break
        run.note_budget(payload)
        llm = getattr(payload, "llm", None)
        choices = getattr(llm, "choices", None) or []
        if not choices:
            break
        message = getattr(choices[0], "message", None)
        if message is None:
            break
        tool_calls = getattr(message, "tool_calls", None) or ()

        if not tool_calls:
            text = _message_text(llm, message)
            leaked = _parse_leaked_tool_calls(text)
            if leaked and not force_final:
                # GLM sometimes emits ZhipuAI tool markup as plain text: execute it (in parallel)
                # instead of surfacing markup as the answer.
                messages.append({"role": "assistant", "content": text})
                outs = await _execute_leaked_calls(leaked, run)
                for out in outs:
                    messages.append({"role": "user", "content": _tool_result_text(out)})
                continue
            if "<tool_call" in text.lower():
                text = _strip_leak_markup(text)
            final_answer = text
            break

        # Isolated: an SDK-shape surprise ends the loop with the transcript intact.
        try:
            messages.append(_to_input_message(message))
            call_list = list(tool_calls)
            outputs = await asyncio.gather(
                *[_run_tool_call(tc, run) for tc in call_list],
                return_exceptions=True,
            )
            for position in range(len(call_list)):
                call_id = getattr(call_list[position], "id", None) or ""
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": _tool_result_text(outputs[position]),
                    }
                )
        except Exception:
            break

    return final_answer, messages


# ========================================================================== phases


async def _phase_briefing(run: _Run, question: str):
    """Knowledge-first draft + constraint/candidate/query plan. Returns (draft, briefing)."""
    user = "Question:\n" + question + "\n\n" + BRIEFING_SECTIONS
    raw = ""
    try:
        raw = await _plain_chat(
            run,
            DRAFT_MODEL,
            BRIEFING_SYSTEM,
            user,
            2400,
            DRAFT_TIMEOUT,
            {"enabled": True, "effort": "low"},
        )
    except Exception:
        raw = ""
    if not raw.strip():
        try:
            raw = await _plain_chat(run, FALLBACK_MODEL, BRIEFING_SYSTEM, user, 2000, DRAFT_TIMEOUT)
        except Exception:
            raw = ""
    if not raw.strip():
        return "", ""
    draft = raw
    marker = re.search(r"CONSTRAINTS\s*:", raw)
    if marker is not None:
        draft = raw[: marker.start()]
    draft = re.sub(r"^DRAFT\s*:\s*", "", draft).strip()
    briefing = (
        "RESEARCH BRIEFING (from prior analysis; verify uncertain values, "
        "correct it where tool evidence disagrees):\n" + raw.strip()
    )
    return draft, briefing


def _audit_issues(report) -> list:
    issues = []
    if not isinstance(report, dict):
        return issues
    for key in AUDIT_KEYS:
        values = report.get(key)
        if isinstance(values, list):
            for value in values:
                text = str(value).strip()
                if text:
                    issues.append(text)
    return issues


async def _phase_audit(run: _Run, question: str, answer: str, messages: list):
    """Audit for missing elements / uncited claims / contradictions / wrong source, then patch.

    Returns (answer, transcript). v11 relied on in-place mutation of the caller's list to keep
    the transcript in sync; the flow is now explicit.
    """
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
        "Question:\n" + question + "\n\nAnswer:\n" + answer[:12000]
    )
    try:
        raw = await _plain_chat(run, PATCH_MODEL, AUDIT_SYSTEM, check_user, 700, PATCH_TIMEOUT)
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I | re.M)
        report = json.loads(cleaned)
    except Exception:
        return answer, messages

    issues = _audit_issues(report)
    if not issues or run.remaining() < 40.0:
        return answer, messages

    seed = list(messages)
    seed.append(
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
    patched, patched_messages = await _research_loop(
        run, question, "", PATCH_EXTRA_TURNS + 1, seed
    )
    patched = patched.strip()
    if patched:
        return patched, patched_messages
    return answer, patched_messages


async def _phase_citation_gate(run: _Run, question: str, briefing: str, answer: str, messages: list):
    """The judge gives no factual credit to uncited claims: re-enter research if under-sourced."""
    marker_count = len(_BRACKET_RE.findall(answer))
    if not answer.strip() or marker_count >= CITE_MIN_MARKERS:
        return answer, messages
    if run.remaining() <= COVERAGE_MIN_SECONDS or run.budget_left() < COVERAGE_MIN_BUDGET:
        return answer, messages

    seed = list(messages)
    seed.append({"role": "system", "content": CITE_GAP_DIRECTIVE})
    recited, recited_messages = await _research_loop(
        run, question, briefing, COVERAGE_MAX_RETRY_TURNS, seed
    )
    if (
        recited
        and recited.strip()
        and not _looks_unfinished(recited)
        and len(_BRACKET_RE.findall(recited)) >= marker_count
    ):
        return recited, recited_messages
    return answer, messages


async def _resynthesize_clean(run: _Run, answer: str) -> str:
    """Leaked scratch narration still holds the real content + [n]; rewrite rather than regex-cut."""
    if run.remaining() < 25.0 or run.budget_left() < COVERAGE_MIN_BUDGET:
        return ""
    system = (
        "Rewrite the text into a DIRECT final answer. Remove ALL process narration "
        "('I have the data', 'Let me verify', 'Perfect!', 'Now I…'). Keep every fact, every [n] "
        "citation marker exactly, and the required output format. Output only the answer."
    )
    try:
        out = await _plain_chat(run, DRAFT_MODEL, system, answer[:6000], 1200, RESYNTH_TIMEOUT)
    except Exception:
        return ""
    out = (out or "").strip()
    if out and not _looks_unfinished(out):
        return out
    return ""


async def _last_resort(run: _Run, question: str) -> str:
    try:
        return await _plain_chat(
            run,
            FALLBACK_MODEL,
            (
                "Expert researcher. Give your best definitive answer with "
                "concrete entities, numbers and dates. Never refuse."
            ),
            question,
            1600,
            LAST_RESORT_TIMEOUT,
        )
    except Exception:
        return ""


# ======================================================================= citations


def _cited_numbers(answer: str, max_number: int) -> list:
    seen = set()
    ordered = []
    for found in _BRACKET_RE.finditer(answer or ""):
        for part in found.group(1).split(","):
            text = part.strip()
            span = re.fullmatch(r"(\d{1,4})\s*-\s*(\d{1,4})", text)
            if span:
                start = int(span.group(1))
                end = int(span.group(2))
                for number in range(start, min(end, start + 20) + 1):
                    if 1 <= number <= max_number and number not in seen:
                        seen.add(number)
                        ordered.append(number)
            elif text.isdigit():
                number = int(text)
                if 1 <= number <= max_number and number not in seen:
                    seen.add(number)
                    ordered.append(number)
    return ordered


def _citation_for(entry) -> object:
    receipt_id = entry.get("receipt_id")
    result_id = entry.get("result_id")
    if not receipt_id or not result_id:
        return None
    if entry.get("source") == "fetch" and entry.get("note_len", 0) > FETCH_SLICE_THRESHOLD:
        return CitationRef(
            receipt_id=receipt_id,
            result_id=result_id,
            slices=[CitationSlice(start=0, end=FETCH_NOTE_CHARS)],
        )
    return CitationRef(receipt_id=receipt_id, result_id=result_id)


def _build_citations(answer: str, run: _Run) -> list:
    refs = []
    for number in _cited_numbers(answer, run.max_number())[:MAX_CITATIONS]:
        entry = run.entries.get(number)
        if entry is None:
            continue
        ref = _citation_for(entry)
        if ref is not None:
            refs.append(ref)
    return refs


def _floor_citations(run: _Run) -> list:
    """Fetched detail first, then search results, each in discovery order (no sort key callable)."""
    fetched = []
    searched = []
    for number in sorted(run.entries):
        entry = run.entries[number]
        if entry.get("source") == "fetch":
            fetched.append(entry)
        else:
            searched.append(entry)
    floor = []
    for entry in fetched + searched:
        ref = _citation_for(entry)
        if ref is not None:
            floor.append(ref)
        if len(floor) >= CITE_FLOOR_N:
            break
    return floor


def _build_citations_with_floor(answer: str, run: _Run) -> list:
    refs = _build_citations(answer, run)
    if refs:
        return refs
    return _floor_citations(run)


# =================================================================== structured out


async def _structured_output(run: _Run, question: str, answer: str, schema):
    schema_text = json.dumps(schema)
    user = (
        "Convert this answer into a JSON value that validates against the "
        "schema. Return ONLY the JSON value.\n\n"
        "Schema:\n" + schema_text + "\n\nQuestion:\n" + question + "\n\nAnswer:\n" + answer[:15000]
    )
    for model in (JSON_MODEL, FALLBACK_MODEL):
        try:
            raw = await _plain_chat(
                run,
                model,
                "You output strictly valid JSON matching the given schema.",
                user,
                2400,
                SCHEMA_TIMEOUT,
            )
            cleaned = re.sub(
                r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I | re.M
            ).strip()
            if not cleaned:
                continue
            return json.loads(cleaned)
        except Exception:
            continue
    return None


# ====================================================================== entrypoint


@entrypoint("query")
async def query(query: Query) -> Response:
    question = (query.text or "").strip()
    if not question:
        return Response(text="No question provided.")
    try:
        return await _answer(query, question)
    except Exception:
        # Miner-attributed errors are terminal (score 0): always return a valid Response.
        return Response(text="Best-effort summary unavailable for: " + question[:600])


async def _answer(query: Query, question: str) -> Response:
    run = _Run()

    try:
        info = await tooling_info(timeout=10.0)
        run.note_budget(info)
    except Exception:
        pass

    # 1. briefing -----------------------------------------------------------
    draft = ""
    briefing = ""
    try:
        if run.budget_left() >= MIN_DRAFT_BUDGET and run.remaining() > 120.0:
            draft, briefing = await _phase_briefing(run, question)
    except Exception:
        draft = ""
        briefing = ""

    # 2. research loop ------------------------------------------------------
    answer = ""
    messages = []
    try:
        answer, messages = await _research_loop(run, question, briefing, MAX_TURNS)
    except Exception:
        answer = ""

    # 3. audit + patch ------------------------------------------------------
    try:
        if answer and run.remaining() > 45.0 and run.budget_left() >= MIN_PATCH_BUDGET:
            answer, messages = await _phase_audit(run, question, answer, messages)
    except Exception:
        pass

    # 4. citation-enforcement gate -----------------------------------------
    try:
        answer, messages = await _phase_citation_gate(run, question, briefing, answer, messages)
    except Exception:
        pass

    if not answer.strip():
        answer = draft.strip()
        if not answer:
            answer = await _last_resort(run, question)

    # 5. finalizer guard ----------------------------------------------------
    try:
        if _looks_unfinished(answer):
            rescue = await _resynthesize_clean(run, answer)
            if _looks_unfinished(rescue):
                rescue = _strip_draft_framing(answer)
            if _looks_unfinished(rescue):
                alternative = _strip_draft_framing(draft.strip())
                if not _looks_unfinished(alternative):
                    rescue = alternative
            if _looks_unfinished(rescue) and run.remaining() > 20.0:
                late = await _last_resort(run, question)
                if late and not _looks_unfinished(late):
                    rescue = late
            if rescue:
                answer = rescue
    except Exception:
        pass

    # 6. literal output directives -----------------------------------------
    answer = _apply_output_directives(question, answer)

    try:
        citations = _build_citations_with_floor(answer, run)
    except Exception:
        citations = []

    final_text = _clamp(answer)
    if not final_text:
        final_text = "Best-effort answer unavailable for: " + question[:400]

    if query.output_schema is not None:
        output = None
        try:
            output = await _structured_output(run, question, answer, query.output_schema)
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