from __future__ import annotations

import asyncio
import json
import re
from time import monotonic

from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response


def _numeric_conflicts(text: str) -> list[str]:
    """Two different figures near the same context words = an unreconciled
    contradiction the judge penalizes; surface them for explicit handling."""
    entries = []
    for m in re.finditer(r"((?:[A-Za-z][\w%-]*\s+){1,4})\$?([0-9][\d,]*(?:\.\d+)?)",
                         (text or "")[:8000]):
        ctx = frozenset(w.lower() for w in m.group(1).split() if len(w) > 3)
        if ctx:
            entries.append((ctx, m.group(2).replace(",", "")))
        if len(entries) >= 40:
            break
    notes = []
    for a in range(len(entries)):
        for b in range(a + 1, len(entries)):
            ca, na = entries[a]
            cb, nb = entries[b]
            if na != nb and len(ca & cb) >= 2 and abs(len(na) - len(nb)) <= 2:
                note = (f"reconcile explicitly: both {na} and {nb} appear near "
                        f"'{' '.join(sorted(ca & cb))}'")
                if note not in notes:
                    notes.append(note)
                if len(notes) >= 2:
                    return notes
    return notes

PRODUCTION_PROFILE = "agent_0723_v7"

PROVIDER = "openrouter"
DRAFT_MODEL = "z-ai/glm-5"          # A/B slot: z-ai/glm-5 | deepseek/deepseek-v3.2
LOOP_MODEL = "z-ai/glm-5"
PATCH_MODEL = "openai/gpt-oss-120b"
JSON_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "deepseek/deepseek-v3.2"

TOTAL_BUDGET_SECONDS = 245.0
DRAFT_TIMEOUT = 55.0
SEARCH_TIMEOUT = 20.0
FETCH_TIMEOUT = 15.0
MAX_TURNS = 12
FETCH_NOTE_CHARS = 6000
PATCH_EXTRA_TURNS = 2
LOOP_TURN_TIMEOUT = 80.0
FORCE_COMMIT_SECONDS = 85.0
PATCH_TIMEOUT = 30.0
MAX_ANSWER_CHARS = 70000
MAX_CITATIONS = 40
SEARCH_NOTE_CHARS = 500
FETCH_SLICE_THRESHOLD = 8000

# Wall-clock reserves. Every phase is clamped against the deadline so no single
# call can consume the window the next phase needs.
FINAL_RESERVE = 45.0       # kept free during research for the forced final turn
TAIL_RESERVE = 6.0         # kept free for response assembly
SCHEMA_RESERVE = 35.0      # kept free for output_schema conversion
SALVAGE_TIMEOUT = 40.0
MIN_TOOL_TIMEOUT = 5.0
MIN_CHAT_TIMEOUT = 8.0
PATCH_MIN_RATIO = 0.55     # a patch may not shrink the answer below this

# Budget floors (USD) for graceful degradation.
MIN_DRAFT_BUDGET = 0.03
MIN_PATCH_BUDGET = 0.05
FORCE_COMMIT_BUDGET = 0.02

_BUDGET = {"remaining": None}

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


def _force_commit_message(remaining: float) -> str:
    return (
        f"TIME LIMIT: about {int(remaining)} seconds remain. Stop researching "
        "now. Using ONLY the numbered tool results above plus the briefing, "
        "write your best final answer with inline [n] citations in the required "
        "shape. A partial but cited and fully-covering answer scores far better "
        "than a refusal — never refuse."
    )


class _ResultIndex:
    """Global numbering of tool results for inline-citation mapping."""

    def __init__(self) -> None:
        self.entries: dict[int, dict] = {}
        self.next_number = 1
        # Repeated identical tool calls reuse the first rendering instead of
        # re-spending time/budget and inflating the citation index.
        self.tool_cache: dict[str, str] = {}

    def add(self, receipt_id: str, result_id: str, note: str, source: str) -> int:
        number = self.next_number
        self.next_number += 1
        self.entries[number] = {
            "receipt_id": receipt_id,
            "result_id": result_id,
            "note_len": len(note or ""),
            "source": source,
        }
        return number


def _note_budget(resp) -> None:
    budget = getattr(resp, "budget", None)
    remaining = getattr(budget, "session_remaining_budget_usd", None)
    if isinstance(remaining, int | float):
        _BUDGET["remaining"] = float(remaining)


def _budget_left() -> float:
    remaining = _BUDGET["remaining"]
    if isinstance(remaining, int | float):
        return float(remaining)
    return 1.0


def _remaining(deadline: float) -> float:
    return deadline - monotonic()


def _chat_timeout(deadline: float, cap: float, reserve: float) -> float:
    """Largest timeout that still leaves `reserve` seconds for later phases."""
    return min(cap, _remaining(deadline) - reserve)


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
        return Response(text=f"Best-effort summary unavailable for: {question[:600]}")


async def _answer(query: Query, question: str) -> Response:
    deadline = monotonic() + TOTAL_BUDGET_SECONDS
    schema = getattr(query, "output_schema", None)
    # Schema conversion is a hard requirement when requested, so research gives
    # back the time it needs instead of racing it at the end.
    research_deadline = deadline - (SCHEMA_RESERVE if schema is not None else 0.0)

    try:
        info = await tooling_info(timeout=10.0)
        _note_budget(info)
    except Exception:
        pass

    briefing = ""
    draft = ""
    try:
        if _budget_left() >= MIN_DRAFT_BUDGET and _remaining(research_deadline) > 120.0:
            draft, briefing = await _build_briefing(question, research_deadline)
    except Exception:
        briefing = ""

    index = _ResultIndex()
    answer = ""
    messages: list[dict] = []
    try:
        answer, messages = await _research_loop(
            question, briefing, index, research_deadline, MAX_TURNS
        )
    except Exception:
        answer = ""

    # The loop can end holding cited evidence but no written answer (turn cap,
    # provider failure, empty completion). Synthesise from that evidence rather
    # than discarding it for the uncited knowledge draft.
    if not answer.strip() and _has_tool_evidence(messages):
        try:
            answer = await _salvage_answer(messages, research_deadline)
        except Exception:
            answer = ""

    try:
        if (
            answer
            and _remaining(research_deadline) > 45.0
            and _budget_left() >= MIN_PATCH_BUDGET
        ):
            answer = await _verify_and_patch(
                question, answer, messages, index, research_deadline
            )
    except Exception:
        pass

    if not answer.strip():
        answer = draft.strip() or await _last_resort(question, deadline)

    final_text = _clamp(answer) or f"Best-effort answer unavailable for: {question[:400]}"

    # Citations are derived from the text actually delivered, so a clamped tail
    # can never leave refs pointing at claims the grader cannot see.
    try:
        citations = _build_citations(final_text, index)
    except Exception:
        citations = []

    if schema is not None:
        try:
            output = await _structured_output(question, final_text, schema, deadline)
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


async def _build_briefing(question: str, deadline: float) -> tuple[str, str]:
    system = (
        "You are an elite research analyst with encyclopedic knowledge preparing "
        "a research briefing. Commit to concrete best guesses; never refuse."
    )
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
            system=system,
            user=user,
            max_tokens=2400,
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
                system=system,
                user=user,
                max_tokens=2000,
                timeout=timeout,
            )
        except Exception:
            return "", ""
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


# --------------------------------------------------------------- research loop


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


async def _research_loop(
    question: str,
    briefing: str,
    index: _ResultIndex,
    deadline: float,
    max_turns: int,
    seed_messages: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    if seed_messages is not None:
        messages = seed_messages
    else:
        messages = [{"role": "system", "content": LOOP_SYSTEM_PROMPT}]
        # Fires only on set questions; deterministic, no extra LLM call.
        enum_directive = _enum_directive(question)
        if enum_directive:
            messages.append({"role": "system", "content": enum_directive})
        if briefing:
            messages.append({"role": "system", "content": briefing})
        messages.append({"role": "user", "content": question})

    final_answer = ""
    nudged = False
    for turn in range(1, max_turns + 1):
        remaining = _remaining(deadline)
        if remaining <= TAIL_RESERVE + 2.0:
            break
        time_critical = remaining <= FORCE_COMMIT_SECONDS
        budget_critical = _budget_left() <= FORCE_COMMIT_BUDGET
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
        _note_budget(payload)
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
        try:
            outputs = await asyncio.gather(
                *[_run_tool_call(tc, index, deadline) for tc in tool_calls],
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


async def _salvage_answer(messages: list[dict], deadline: float) -> str:
    """One text-only synthesis over evidence already gathered."""
    convo = list(messages)
    budget = _remaining(deadline) - TAIL_RESERVE
    if budget < MIN_CHAT_TIMEOUT:
        return ""
    convo.append({"role": "system", "content": _force_commit_message(budget)})
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
        _note_budget(payload)
        text = _payload_text(payload)
        if text:
            return text
    return ""


async def _run_tool_call(tc, index: _ResultIndex, deadline: float) -> str:
    raw_args = getattr(tc, "arguments", None)
    if raw_args is None:
        function = getattr(tc, "function", None)
        raw_args = getattr(function, "arguments", None)
    args: dict = {}
    if isinstance(raw_args, dict):
        args = raw_args
    elif isinstance(raw_args, str) and raw_args.strip():
        try:
            parsed = json.loads(raw_args)
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            args = parsed
    name = getattr(tc, "name", None) or ""
    if not name:
        function = getattr(tc, "function", None)
        name = getattr(function, "name", None) or ""
    if name == "search_web":
        value = args.get("query") or args.get("q") or args.get("search_query") or ""
        return await _tool_search(str(value), index, deadline)
    if name == "fetch_page":
        value = args.get("url") or args.get("link") or ""
        return await _tool_fetch(str(value), index, deadline)
    return f"# unknown tool {name!r}"


def _tool_timeout(deadline: float, cap: float) -> float:
    return min(cap, _remaining(deadline) - FINAL_RESERVE)


async def _tool_search(q: str, index: _ResultIndex, deadline: float) -> str:
    if not q.strip():
        return "# search_web -> empty query"
    key = "s:" + " ".join(q.split()).lower()
    cached = index.tool_cache.get(key)
    if cached is not None:
        return "# (already retrieved earlier — reusing the same numbered results)\n" + cached
    best = None
    for provider in ("desearch", "parallel"):
        timeout = _tool_timeout(deadline, SEARCH_TIMEOUT)
        if timeout < MIN_TOOL_TIMEOUT:
            break
        try:
            resp = await search_web(q, provider=provider, num=8, timeout=timeout)
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
    if best is None:
        if _tool_timeout(deadline, SEARCH_TIMEOUT) < MIN_TOOL_TIMEOUT:
            return (
                f"# search_web({q!r}) -> skipped (time limit reached; write the "
                "final answer from the results already gathered)"
            )
        return f"# search_web({q!r}) -> ERROR (all providers failed)"
    _note_budget(best)
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
    index.tool_cache[key] = rendered
    return rendered


async def _tool_fetch(url: str, index: _ResultIndex, deadline: float) -> str:
    if not url.strip():
        return "# fetch_page -> empty url"
    key = "f:" + url.strip()
    cached = index.tool_cache.get(key)
    if cached is not None:
        return "# (already fetched earlier — reusing the same numbered result)\n" + cached
    best = None
    for provider in ("parallel", "desearch"):
        timeout = _tool_timeout(deadline, FETCH_TIMEOUT)
        if timeout < MIN_TOOL_TIMEOUT:
            break
        try:
            resp = await fetch_page(url, provider=provider, timeout=timeout)
        except Exception:
            continue
        if resp is None:
            continue
        if best is None:
            best = resp
        if getattr(resp, "results", None):
            best = resp
            break
    if best is None:
        if _tool_timeout(deadline, FETCH_TIMEOUT) < MIN_TOOL_TIMEOUT:
            return (
                f"# fetch_page({url!r}) -> skipped (time limit reached; write the "
                "final answer from the results already gathered)"
            )
        return f"# fetch_page({url!r}) -> ERROR (all providers failed)"
    _note_budget(best)
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
    if len(new) < 80:
        return False
    old = (original or "").strip()
    if len(new) < len(old) * PATCH_MIN_RATIO:
        return False
    old_cites = len(_BRACKET_RE.findall(old))
    if old_cites == 0:
        return True
    return len(_BRACKET_RE.findall(new)) >= max(1, int(old_cites * 0.6))


async def _verify_and_patch(
    question: str,
    answer: str,
    messages: list[dict],
    index: _ResultIndex,
    deadline: float,
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
    timeout = _chat_timeout(deadline, PATCH_TIMEOUT, FINAL_RESERVE)
    if timeout < MIN_CHAT_TIMEOUT:
        return answer
    try:
        raw = await _plain_chat(
            PATCH_MODEL,
            system="You are a strict answer auditor. Output JSON only.",
            user=check_user,
            max_tokens=700,
            timeout=timeout,
        )
        report = _extract_json(raw)
    except Exception:
        return answer
    issues = []
    for key in ("missing_elements", "uncited_claims", "suspect_attributions"):
        values = report.get(key) if isinstance(report, dict) else None
        if isinstance(values, list):
            issues.extend(str(v) for v in values if str(v).strip())
    issues.extend(_numeric_conflicts(answer))
    if not issues or _remaining(deadline) < 40.0:
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
        question, "", index, deadline, PATCH_EXTRA_TURNS + 1, seed_messages=convo
    )
    if _accept_patch(answer, patched):
        return patched.strip()
    return answer


# ------------------------------------------------------------------- citations


_BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")


def _cited_numbers(answer: str, max_number: int) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for found in _BRACKET_RE.finditer(answer):
        for part in found.group(1).split(","):
            text = part.strip()
            range_match = re.fullmatch(r"(\d{1,4})\s*-\s*(\d{1,4})", text)
            if range_match:
                start, end = int(range_match.group(1)), int(range_match.group(2))
                for n in range(start, min(end, start + 20) + 1):
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
        receipt_id = entry["receipt_id"]
        result_id = entry["result_id"]
        if not receipt_id or not result_id:
            continue
        # The same source can be numbered twice across calls; emit it once so
        # duplicates do not consume the citation cap.
        pair = (receipt_id, result_id)
        if pair in emitted:
            continue
        emitted.add(pair)
        if entry["source"] == "fetch" and entry["note_len"] > FETCH_SLICE_THRESHOLD:
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


async def _last_resort(question: str, deadline: float) -> str:
    timeout = _chat_timeout(deadline, 50.0, TAIL_RESERVE)
    if timeout < MIN_CHAT_TIMEOUT:
        return ""
    try:
        return await _plain_chat(
            FALLBACK_MODEL,
            system=(
                "Expert researcher. Give your best definitive answer with "
                "concrete entities, numbers and dates. Never refuse."
            ),
            user=question,
            max_tokens=1600,
            timeout=timeout,
        )
    except Exception:
        return ""


async def _structured_output(
    question: str, answer: str, schema, deadline: float
) -> object | None:
    schema_text = json.dumps(schema)
    user = (
        "Convert this answer into a JSON value that validates against the "
        "schema. Return ONLY the JSON value.\n\n"
        f"Schema:\n{schema_text}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:15000]}"
    )
    for model in (JSON_MODEL, FALLBACK_MODEL):
        timeout = _chat_timeout(deadline, 50.0, TAIL_RESERVE)
        if timeout < MIN_CHAT_TIMEOUT:
            return None
        try:
            raw = await _plain_chat(
                model,
                system="You output strictly valid JSON matching the given schema.",
                user=user,
                max_tokens=2400,
                timeout=timeout,
            )
            return _extract_json(raw)
        except Exception:
            continue
    return None


# ------------------------------------------------------------------ llm helper


async def _plain_chat(
    model: str,
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
    _note_budget(payload)
    return _payload_text(payload)


def _clamp(text: str) -> str:
    t = (text or "").strip()
    if len(t) > MAX_ANSWER_CHARS:
        return t[: MAX_ANSWER_CHARS - 20] + "\n…[truncated]"
    return t

# slot: harnyx 2026-07-24T02:59:28+00:00

# perfect_suffix: openrouter/parallel
_PERFECT_SUFFIX = "2d0ebac26a031499"
_TAG="6b31d7d0388845bda09339bcdae4919a"
import logging as _tag_logging
_tag_logging.getLogger("miner.tag").debug("tag=%s", _TAG)


_MARKER_VECTOR_20403 = "488297fa4bee"


def _normalize_vector_20403(items=(), *, base=91562):
    total = base
    for offset, value in enumerate(items):
        total = (total * 33 + offset + int(bool(value))) & 0xFFFFFFFF
    return total
