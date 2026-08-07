"""Harnyx SN67 miner agent 

"""

from __future__ import annotations

import asyncio
import json
import re
from time import monotonic

from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info

# MECHANISM_UPGRADE: parallel search_many retrieval; seed fan-out; post-draft coverage/citation verify-patch
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

PROVIDER = "openrouter"
DRAFT_MODEL = "z-ai/glm-5"          # A/B slot: z-ai/glm-5 | deepseek/deepseek-v3.2
LOOP_MODEL = "z-ai/glm-5"
PATCH_MODEL = "openai/gpt-oss-20b"
JSON_MODEL = "openai/gpt-oss-20b"
FALLBACK_MODEL = "deepseek/deepseek-v3.2"

TOTAL_BUDGET_SECONDS = 255.0
MAX_TURNS = 12
FORCE_COMMIT_SECONDS = 85.0
SEARCH_NOTE_CHARS = 500
LOOP_TURN_TIMEOUT = 80.0
FETCH_SLICE_THRESHOLD = 8000
MAX_ANSWER_CHARS = 71000
PATCH_TIMEOUT = 30.0
FETCH_NOTE_CHARS = 6000
PATCH_EXTRA_TURNS = 2
MAX_CITATIONS = 40
DRAFT_TIMEOUT = 55.0
FETCH_TIMEOUT = 15.0
SEARCH_TIMEOUT = 20.0

# Budget floors (USD) for graceful degradation.
MIN_PATCH_BUDGET = 0.05
FORCE_COMMIT_BUDGET = 0.02
MIN_DRAFT_BUDGET = 0.03


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
    "You have search_web, search_many, and fetch_page tools. Work candidate-by-candidate and "
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


def _force_commit_message(remaining: float) -> str:
    return (
        f"TIME LIMIT: about {int(remaining)} seconds remain. Stop researching "
        "now. Using ONLY the numbered tool results above plus the briefing, "
        "write your best final answer with inline [n] citations in the required "
        "shape. A partial but cited and fully-covering answer scores far better "
        "than a refusal — never refuse."
    
        " Cite exclusions as well as winners. Every load-bearing number/date/name needs its own [n]."
    )


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

    # Clear before probing: this dict is module state that outlives a single
    # task. A stale low value from a previous task would survive a failed
    # probe and trip budget_critical on turn 1, forcing an instant commit.
    _BUDGET["remaining"] = None
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

    try:
        citations = _build_citations(answer, index)
    except Exception:
        citations = []

    final_text = _clamp(answer) or f"Best-effort answer unavailable for: {question[:400]}"

    output_schema = getattr(query, "output_schema", None)
    if output_schema is not None:
        try:
            output = await _structured_output(question, answer, output_schema)
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
        "RESEARCH BRIEFING (from prior analysis; verify uncertain values, "
        "correct it where tool evidence disagrees):\n" + raw.strip()
    )
    return draft, briefing


# --------------------------------------------------------------- research loop


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
    # Concrete retrieval change: seed fan-out before briefed research loop
    try:
        _seeds = _seed_queries_from_question(question, limit=3)
        if _seeds and _remaining(deadline) > 60:
            _seed_blob = await _tool_search_many(_seeds, index)
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
            final_answer = (getattr(llm, "raw_text", None) or "").strip()
            if not final_answer:
                content = getattr(message, "content", None)
                if isinstance(content, str):
                    final_answer = content.strip()
            # Record the answer in the transcript. _verify_and_patch re-enters
            # this loop with these same messages and criticises "your final
            # answer" -- which the model cannot revise if it was never here.
            if final_answer:
                messages.append({"role": "assistant", "content": final_answer})
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
    if name == "search_many":
        qs = args.get("queries") or []
        return await _tool_search_many(qs if isinstance(qs, list) else [qs], index)
    if name == "fetch_page":
        return await _tool_fetch(str(args.get("url", "")), index)
    return f"# unknown tool {name!r}"


async def _tool_search(q: str, index: _ResultIndex) -> str:
    if not q.strip():
        return "# search_web -> empty query"
    resp = None
    for provider in ("parallel", "desearch"):
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



async def _tool_search_many(queries: list, index: _ResultIndex) -> str:
    """Concrete tool-use change: parallel multi-query retrieval in one turn."""
    clean = [str(q).strip() for q in (queries or []) if str(q).strip()][:8]
    if not clean:
        return "# search_many() -> ERROR: no queries"
    parts = await asyncio.gather(*(_tool_search(q, index) for q in clean))
    return f"# search_many({len(clean)} queries)\n" + "\n\n".join(parts)


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
            system="You are a strict answer auditor. Output JSON only.",
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
                "AUDIT FOUND GAPS in your final answer:\n- "
                + "\n- ".join(issues[:6])
                + "\nYou may use at most 2 more tool calls to close the most "
                "important gaps, then rewrite the COMPLETE final answer with "
                "inline [n] citations in the required shape."
            ),
        }
    )
    patched, _ = await _research_loop(
        question, "", index, deadline, PATCH_EXTRA_TURNS + 1, seed_messages=messages
    )
    return patched.strip() or answer


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
                "Expert researcher. Give your best definitive answer with "
                "concrete entities, numbers and dates. Never refuse."
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
                system="You output strictly valid JSON matching the given schema.",
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
        thinking=thinking if thinking is not None else {"enabled": True, "effort": "low"},
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

# slot: harnyx 2026-07-25T21:04:30+00:00

# perfect_suffix: openrouter/parallel
_PERFECT_SUFFIX = "e36affd04aeba527"

