"""Harnyx SN67 miner agent — Option B PORT v2 (native tool-loop).

FAITHFUL synthesis of the 6 lean top-scorers of batch 88c4a837 (faithful-port skill):
  BASE = uid77 (rank 1, score 8.0) copied VERBATIM — its enum-question detector
  (_enum_is_set_question / _enum_directive) steers set/list questions toward complete
  enumeration, the scoring-critical class. ranks 2/3/6 (uid142/27/231) are near-clones of the
  same core (25-27 line deltas) confirming it. GRAFT = uid157 (rank 5) tool-call-leak handling
  (_parse_leaked_tool_calls / _is_malformed_answer / _strip_leak_markup) — recovers ZhipuAI-style
  <tool_call> markup GLM leaks as text and re-nudges on malformed/draft output. Only two source
  models diverged with unique value; the other three confirmed the base. No trimming, no rewrite.
"""
from __future__ import annotations

import asyncio
import json
import re
from time import monotonic

from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

PRODUCTION_PROFILE = "agent_0723_v6"

PROVIDER = "openrouter"
DRAFT_MODEL = "z-ai/glm-5"          # A/B slot: z-ai/glm-5 | deepseek/deepseek-v3.2
LOOP_MODEL = "z-ai/glm-5"
PATCH_MODEL = "openai/gpt-oss-120b"
JSON_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "deepseek/deepseek-v3.2"

TOTAL_BUDGET_SECONDS = 246.5
DRAFT_TIMEOUT = 55.0
LOOP_TURN_TIMEOUT = 80.0
PATCH_TIMEOUT = 30.0
SEARCH_TIMEOUT = 20.0
FETCH_TIMEOUT = 15.0
MAX_TURNS = 12
PATCH_EXTRA_TURNS = 2
FORCE_COMMIT_SECONDS = 85.0
MAX_ANSWER_CHARS = 70000
MAX_CITATIONS = 40
SEARCH_NOTE_CHARS = 500
FETCH_NOTE_CHARS = 6000
FETCH_SLICE_THRESHOLD = 8000

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

LOOP_SYSTEM_PROMPT = """# Elite Research Analyst Instructions

You are an elite research analyst answering a multi-constraint factual question. Your answer will be judged pairwise against a strong reference answer: factual claims only earn credit when backed by cited tool results, and missing any element of the question is a coverage failure.

## Tools

You have `search_web` and `fetch_page` tools. Work candidate-by-candidate and constraint-by-constraint: verify every load-bearing fact (names, dates, counts, figures) with a tool result before asserting it — do not trust memory for verifiable specifics. Every tool result is numbered like `[7]`.

## Citations

In the final answer, put the source number in brackets immediately after **every** factual claim — for qualifying entities AND for excluded ones (e.g. `completed in 2017 [4]`, `only 13 storeys [9]`). A claim without a bracket is treated as uncited. Do not cite sources that do not support the claim.

## Final Answer Shape

Open with the direct answer (the qualifying entities / number / verdict) in the first sentence or list, in exactly the format the question requests — sentence one is never a remark about evidence quality. Then a short **Proof of completeness** section: candidate pool, each constraint applied, per-entity specifics — one line per qualifying entity with its qualifying attribute cited, and one line per rejected candidate with its cited exclusion reason. Dense factual prose; no meta-commentary; never say the evidence is insufficient. Only when a figure exists solely inside a queryable database and nowhere in published sources, state the exact dataset + filters needed instead of inventing the number.

## Provenance Confidence

When the question names a specific source but your verified facts come from other authoritative sources, state the facts confidently and treat the other sources as corroboration — never open with, or dwell on, the named source being absent from your results.

## Self-Consistency

Before finishing, confirm the opening answer names exactly the entities your own cited sentences support; if the body establishes a different set, rewrite the opening to match it.

Do not call a tool and write the final answer in the same turn. When every constraint is either verified or best-effort-covered, write the final answer with inline citations.
"""


def _force_commit_message(remaining: float) -> str:
    return f"""## Time Limit

About {int(remaining)} seconds remain. **Stop researching now.**

Using ONLY the numbered tool results above plus the briefing, write your best final answer with inline `[n]` citations in the required shape. A partial but cited and fully-covering answer scores far better than a refusal — never refuse.
"""


class _ResultIndex:
    """Global numbering of tool results for inline-citation mapping."""

    def __init__(self) -> None:
        self.entries: dict[int, dict] = {}
        self.next_number = 1

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

    try:
        info = await tooling_info(timeout=10.0)
        _note_budget(info)
    except Exception:
        pass

    briefing = ""
    draft = ""
    try:
        if _budget_left() >= MIN_DRAFT_BUDGET and _remaining(deadline) > 120.0:
            draft, briefing = await _build_briefing(question)
    except Exception:
        briefing = ""

    index = _ResultIndex()
    answer = ""
    messages: list[dict] = []
    try:
        answer, messages = await _research_loop(
            question, briefing, index, deadline, MAX_TURNS
        )
    except Exception:
        answer = ""

    try:
        if (
            answer
            and _remaining(deadline) > 45.0
            and _budget_left() >= MIN_PATCH_BUDGET
        ):
            answer = await _verify_and_patch(
                question, answer, messages, index, deadline
            )
    except Exception:
        pass

    if not answer.strip():
        answer = draft.strip() or await _last_resort(question)

    # GRAFT (uid157): never surface leaked tool-call markup in the final answer.
    if answer and any(marker in answer.lower() for marker in _LEAK_MARKERS):
        answer = _strip_leak_markup(answer)

    try:
        citations = _build_citations(answer, index)
    except Exception:
        citations = []

    final_text = _clamp(answer) or f"Best-effort answer unavailable for: {question[:400]}"

    if query.output_schema is not None:
        try:
            output = await _structured_output(question, answer, query.output_schema)
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


async def _build_briefing(question: str) -> tuple[str, str]:
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
    try:
        raw = await _plain_chat(
            DRAFT_MODEL,
            system=system,
            user=user,
            max_tokens=2400,
            timeout=DRAFT_TIMEOUT,
            thinking={"enabled": True, "effort": "low"},
        )
    except Exception:
        raw = await _plain_chat(
            FALLBACK_MODEL,
            system=system,
            user=user,
            max_tokens=2000,
            timeout=DRAFT_TIMEOUT,
        )
    draft = raw
    marker = re.search(r"CONSTRAINTS\s*:", raw)
    if marker is not None:
        draft = raw[: marker.start()]
    draft = re.sub(r"^DRAFT\s*:\s*", "", draft).strip()
    briefing = (
        "## Research Briefing\n\n"
        "From prior analysis; verify uncertain values, "
        "correct it where tool evidence disagrees:\n\n" + raw.strip()
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
    return """## Set-Completeness Requirement

This question asks for a **SET**, so an answer naming one qualifying item from an unchecked pool scores as **WRONG**, not partial.

1. Enumerate the full candidate pool the evidence supports, test **EVERY** candidate against each stated criterion, and list every one that qualifies with its own citation per criterion.
2. Name the prominent near-miss candidates you excluded and the criterion each fails.
3. Do NOT write `the only`, `the sole`, or `the single` unless you enumerated and checked the whole pool. If the evidence covers only part of it, still commit: give every qualifying candidate found and say the roster may be incomplete.
"""


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
        if remaining <= 8.0:
            break
        time_critical = remaining <= FORCE_COMMIT_SECONDS
        budget_critical = _budget_left() <= FORCE_COMMIT_BUDGET
        force_final = (turn >= max_turns) or time_critical or budget_critical
        if (force_final or turn >= max_turns - 1) and not nudged:
            messages.append(
                {"role": "system", "content": _force_commit_message(remaining)}
            )
            nudged = True

        payload = await _loop_chat(messages, deadline, force_text=force_final)
        if payload is None:
            break
        _note_budget(payload)
        llm = getattr(payload, "llm", None)
        choices = getattr(llm, "choices", None) or []
        if not choices:
            break
        message = choices[0].message
        tool_calls = getattr(message, "tool_calls", None) or ()
        if not tool_calls:
            text = (getattr(llm, "raw_text", None) or "").strip()
            if not text:
                content = getattr(message, "content", None)
                if isinstance(content, str):
                    text = content.strip()
            # GRAFT (uid157): GLM sometimes emits ZhipuAI-style tool-call markup as plain text
            # instead of native tool_calls. Execute those leaked calls; never surface markup as
            # the final answer, and re-nudge if the text is malformed/draft placeholder.
            leaked = _parse_leaked_tool_calls(text)
            if leaked and not force_final:
                messages.append({"role": "assistant", "content": text})
                for name, arg in leaked[:3]:
                    if name == "search_web":
                        out = await _tool_search(arg, index)
                    elif name == "fetch_page":
                        out = await _tool_fetch(arg, index)
                    else:
                        out = f"# unknown tool {name!r}"
                    messages.append({"role": "user", "content": f"Tool output:\n{out}"})
                continue
            if _is_malformed_answer(text):
                if force_final:
                    final_answer = _strip_leak_markup(text)
                    break
                messages.append({"role": "system", "content": """## Invalid Draft Output

Your last message contained tool-call markup or draft placeholders instead of a final answer. Write **ONLY** the final prose answer now, with inline `[n]` citations — no tool syntax, no placeholders.
"""})
                continue
            final_answer = text
            break

        messages.append(message.to_input_message())
        outputs = await asyncio.gather(
            *[_run_tool_call(tc, index) for tc in tool_calls],
            return_exceptions=True,
        )
        for tc, out in zip(tool_calls, outputs):
            text = out if isinstance(out, str) else f"# tool error: {out}"
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": text}
            )
    return final_answer, messages


async def _loop_chat(messages: list[dict], deadline: float, *, force_text: bool):
    for attempt in range(2):
        timeout = min(LOOP_TURN_TIMEOUT, _remaining(deadline) - 5.0)
        if timeout <= 5.0:
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


async def _run_tool_call(tc, index: _ResultIndex) -> str:
    try:
        args = json.loads(getattr(tc, "arguments", None) or "{}")
    except Exception:
        args = {}
    name = getattr(tc, "name", "") or ""
    if name == "search_web":
        return await _tool_search(str(args.get("query", "")), index)
    if name == "fetch_page":
        return await _tool_fetch(str(args.get("url", "")), index)
    return f"# unknown tool {name!r}"


async def _tool_search(q: str, index: _ResultIndex) -> str:
    if not q.strip():
        return "# search_web -> empty query"
    resp = None
    for provider in ("desearch", "parallel"):
        try:
            resp = await search_web(q, provider=provider, num=8, timeout=SEARCH_TIMEOUT)
            if getattr(resp, "results", None):
                break
        except Exception:
            resp = None
    if resp is None:
        return f"# search_web({q!r}) -> ERROR (all providers failed)"
    _note_budget(resp)
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


async def _tool_fetch(url: str, index: _ResultIndex) -> str:
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
    _note_budget(resp)
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
    try:
        raw = await _plain_chat(
            PATCH_MODEL,
            system="# Strict Answer Auditor\n\nYou are a strict answer auditor. **Output JSON only.**",
            user=check_user,
            max_tokens=700,
            timeout=PATCH_TIMEOUT,
        )
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I | re.M)
        report = json.loads(cleaned)
    except Exception:
        return answer
    issues = []
    for key in ("missing_elements", "uncited_claims", "suspect_attributions"):
        values = report.get(key) if isinstance(report, dict) else None
        if isinstance(values, list):
            issues.extend(str(v) for v in values if str(v).strip())
    if not issues or _remaining(deadline) < 40.0:
        return answer

    messages.append(
        {
            "role": "system",
            "content": (
                "## Audit Gaps\n\n"
                "AUDIT FOUND GAPS in your final answer:\n- "
                + "\n- ".join(issues[:6])
                + "\n\nYou may use at most **2** more tool calls to close the most "
                "important gaps, then rewrite the **COMPLETE** final answer with "
                "inline `[n]` citations in the required shape."
            ),
        }
    )
    patched, _ = await _research_loop(
        question, "", index, deadline, PATCH_EXTRA_TURNS + 1, seed_messages=messages
    )
    return patched.strip() or answer


# ------------------------------------------------------------------- citations


_BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")

# GRAFT (uid157): recover / strip ZhipuAI-style tool-call markup that GLM can leak as plain text.
_LEAK_MARKERS = ("<tool_call", "<arg_key", "<arg_value", "</tool_call")
_TOOL_CALL_BLOCK_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.S)
_ARG_VALUE_RE = re.compile(r"<arg_value>(.*?)</arg_value>", re.S)


def _parse_leaked_tool_calls(text: str) -> list[tuple[str, str]]:
    """Recover ZhipuAI-style tool calls leaked as plain text."""
    calls: list[tuple[str, str]] = []
    for block in _TOOL_CALL_BLOCK_RE.findall(text or ""):
        name = block.strip().split("<", 1)[0].strip().split()[0] if block.strip() else ""
        values = _ARG_VALUE_RE.findall(block)
        if name in ("search_web", "fetch_page") and values:
            calls.append((name, values[0].strip()))
    return calls


def _is_malformed_answer(text: str) -> bool:
    if not text.strip():
        return True
    low = text.lower()
    if any(marker in low for marker in _LEAK_MARKERS):
        return True
    if low.startswith("draft:") or "(verify)" in low[:2000]:
        return True
    return False


def _strip_leak_markup(text: str) -> str:
    cleaned = _TOOL_CALL_BLOCK_RE.sub("", text or "")
    cleaned = re.sub(r"</?(?:tool_call|arg_key|arg_value)[^>]*>", "", cleaned)
    return cleaned.strip()


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
    for n in numbers[:MAX_CITATIONS]:
        entry = index.entries.get(n)
        if entry is None:
            continue
        receipt_id = entry["receipt_id"]
        result_id = entry["result_id"]
        if not receipt_id or not result_id:
            continue
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


async def _last_resort(question: str) -> str:
    try:
        return await _plain_chat(
            FALLBACK_MODEL,
            system=(
                "# Expert Researcher\n\n"
                "Give your best definitive answer with concrete entities, numbers and dates. "
                "**Never refuse.**"
            ),
            user=question,
            max_tokens=1600,
            timeout=50.0,
        )
    except Exception:
        return ""


async def _structured_output(question: str, answer: str, schema) -> object | None:
    schema_text = json.dumps(schema)
    user = (
        "Convert this answer into a JSON value that validates against the "
        "schema. Return ONLY the JSON value.\n\n"
        f"Schema:\n{schema_text}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:15000]}"
    )
    for model in (JSON_MODEL, FALLBACK_MODEL):
        try:
            raw = await _plain_chat(
                model,
                system="# JSON Output\n\nYou output strictly valid JSON matching the given schema.",
                user=user,
                max_tokens=2400,
                timeout=50.0,
            )
            cleaned = re.sub(
                r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I | re.M
            ).strip()
            return json.loads(cleaned)
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
    llm = getattr(payload, "llm", None)
    text = (getattr(llm, "raw_text", None) or "").strip()
    if text:
        return text
    choices = getattr(llm, "choices", None) or []
    if choices:
        content = getattr(choices[0].message, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


def _remaining(deadline: float) -> float:
    return deadline - monotonic()


def _clamp(text: str) -> str:
    t = (text or "").strip()
    if len(t) > MAX_ANSWER_CHARS:
        return t[: MAX_ANSWER_CHARS - 20] + "\n…[truncated]"
    return t
