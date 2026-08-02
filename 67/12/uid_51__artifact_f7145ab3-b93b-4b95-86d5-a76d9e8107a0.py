"""Harnyx SN67 miner agent

Structure-hardened build. Behavioural contract vs the 0.700 baseline:
  * identical prompts, models, tool schema, timeouts and citation mapping
  * openrouter is the only provider
  * no dunder attribute reflection, no dynamic getattr, no dynamic callables,
    no forbidden imports
"""

import asyncio
import json
import re
from time import monotonic

from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

PROVIDER = "openrouter"
DRAFT_MODEL = "z-ai/glm-5"          # A/B slot: z-ai/glm-5 | deepseek/deepseek-v3.2
LOOP_MODEL = "z-ai/glm-5"
PATCH_MODEL = "openai/gpt-oss-20b"
JSON_MODEL = "openai/gpt-oss-20b"
FALLBACK_MODEL = "deepseek/deepseek-v3.2"

FETCH_TIMEOUT = 15.0
TOTAL_BUDGET_SECONDS = 255.0
FETCH_NOTE_CHARS = 6000
DRAFT_TIMEOUT = 55.0
FORCE_COMMIT_SECONDS = 85.0
LOOP_TURN_TIMEOUT = 80.0
SEARCH_NOTE_CHARS = 500
PATCH_TIMEOUT = 30.0
MAX_TURNS = 12
MAX_CITATIONS = 40
FETCH_SLICE_THRESHOLD = 8000
PATCH_EXTRA_TURNS = 2
SEARCH_TIMEOUT = 20.0
MAX_ANSWER_CHARS = 71000

# Budget floors (USD) for graceful degradation.
MIN_PATCH_BUDGET = 0.05
FORCE_COMMIT_BUDGET = 0.02
MIN_DRAFT_BUDGET = 0.03

# Verification fan-out: one parallel probe batch, then one revision pass.
# Gate arithmetic must GUARANTEE the batch can be consumed:
#   worst-case batch = 2 * PROBE_SEARCH_TIMEOUT (both providers tried serially)
#   PROBE_MIN_SECONDS - 2*PROBE_SEARCH_TIMEOUT > REVISE_MIN_SECONDS
#   80 - 24 = 56 > 45  -> a probe that runs is always rewritten.
PROBE_ENABLED = True
PROBE_MIN_SECONDS = 80.0
PROBE_SEARCH_TIMEOUT = 12.0
REVISE_MIN_SECONDS = 45.0
REVISE_TURNS = 2
PROBE_MAX_QUERIES = 8
PROBE_BLOB_CHARS = 12000
SEED_BLOB_CHARS = 12000
PREFETCH_BLOB_CHARS = 14000
SEED_MIN_SECONDS = 60.0
PREFETCH_MIN_SECONDS = 50.0
MIN_TURN_SECONDS = 8.0
PATCH_MIN_SECONDS = 45.0
PATCH_LOOP_SECONDS = 40.0

# Transcript growth guard: long tool-heavy runs must not blow the context window.
MAX_TRANSCRIPT_CHARS = 190000
TOOL_KEEP_CHARS = 3500
TOOL_STUB_CHARS = 400
TRIM_MARKER = "\n…[older tool output trimmed]"

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

    "\n\n## V3 Scoring Binding\n\n"
    "- After claim re-ground / roster fan-out, every load-bearing number/date/name and each comparison operand must carry [n].\n"
    "- Prefer partial cited coverage over inventing roster completeness.\n"
    "- False premise: correct first line with a citation; never empty refusal.\n"
)

_PROBE_INSTRUCTION = (
    "## Verification Fan-out — contradiction probe, claim re-ground, dual-cite, roster\n\n"
    "Opposing/correction searches, targeted re-grounding probes for bare claims, "
    "comparison-operand lookups and roster-completeness searches all ran in "
    "parallel. If a result refutes a claim, correct it with citations; otherwise "
    "keep the draft and cite the confirming notes. Then rewrite the COMPLETE "
    "final answer in the required shape with [n] after every load-bearing "
    "number/date/name and after each comparison operand, for qualifying AND "
    "excluded entities.\n\n"
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


# ---------------------------------------------------------------- result index
# Plain-dict result index (no class, no dunder methods). Global numbering of
# tool results for inline-citation mapping.


def _new_index() -> dict:
    return {"entries": {}, "next": 1}


def _index_add(index: dict, receipt_id: str, result_id: str, note: str, source: str) -> int:
    number = index["next"]
    index["next"] = number + 1
    index["entries"][number] = {
        "receipt_id": receipt_id,
        "result_id": result_id,
        "note_len": len(note or ""),
        "source": source,
    }
    return number


def _index_max(index: dict) -> int:
    return index["next"] - 1


# --------------------------------------------------------------------- budget


def _note_budget(resp) -> None:
    budget = getattr(resp, "budget", None)
    remaining = getattr(budget, "session_remaining_budget_usd", None)
    if isinstance(remaining, (int, float)):
        _BUDGET["remaining"] = float(remaining)


def _budget_left() -> float:
    remaining = _BUDGET["remaining"]
    if isinstance(remaining, (int, float)):
        return float(remaining)
    return 1.0


# ------------------------------------------------------------ query synthesis


_AUTHORITY_URL_RE = re.compile(
    r"https?://[^\s\]\)>\"\']+",
    re.I,
)
_AUTHORITY_HOST_HINTS = (
    ".gov", ".edu", "wikipedia.org", "sec.gov", "who.int", "worldbank.org",
    "imf.org", "oecd.org", "un.org", "europa.eu", "nature.com", "nih.gov",
)


def _authority_urls_from_blob(blob: str, limit: int = 2) -> list:
    """Pick primary/official URLs from retrieval text for auto-fetch."""
    found = []
    seen = set()
    for m in _AUTHORITY_URL_RE.finditer(blob or ""):
        url = m.group(0).rstrip(".,);]")
        low = url.lower()
        if low in seen:
            continue
        if not any(h in low for h in _AUTHORITY_HOST_HINTS):
            continue
        seen.add(low)
        found.append(url)
        if len(found) >= limit:
            break
    return found


def _opposition_queries_from_answer(question: str, answer: str, limit: int = 3) -> list:
    """Build opposing-evidence queries from the draft (concrete verification branch)."""
    q = " ".join((question or "").split())
    a = " ".join((answer or "").split())
    seeds = []
    if q:
        seeds.append(f"{q} controversy OR correction OR retracted OR false")
    # Pull a few capitalized entities / quoted spans from the answer lead.
    lead = a[:400]
    for m in re.finditer(r'"([^"]{3,60})"|\b([A-Z][A-Za-z0-9&\-]*(?:\s+[A-Z][A-Za-z0-9&\-]*){0,2})\b', lead):
        span = (m.group(1) or m.group(2) or "").strip()
        if len(span) < 3 or span.lower() in {"final", "answer", "the", "and", "for"}:
            continue
        cand = f"{span} official correction OR disputed OR revised"
        if cand.lower() not in {s.lower() for s in seeds}:
            seeds.append(cand)
        if len(seeds) >= limit:
            break
    if len(seeds) < 2 and q:
        seeds.append(f"{q} official primary source")
    return seeds[:limit]


def _seed_queries_from_question(question: str, limit: int = 3) -> list:
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


_BARE_CLAIM_RE = re.compile(
    r"(?m)^(?!.*\[\d+\]).{0,200}?\b("
    r"\d{4}|\d+(?:\.\d+)?%?|"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4}"
    r")\b"
)
_COMPARE_Q_RE = re.compile(
    r"\b(compar(?:e|ison)|versus|\bvs\.?\b|difference between|higher than|lower than|"
    r"more than|less than|relative to|against)\b",
    re.I,
)
_ROSTER_Q_RE = re.compile(
    r"\b(which|list|name|identify|how many|all of|every|each|complete (?:list|set|roster))\b",
    re.I,
)


def _v3_claim_reground_queries(question: str, answer: str, limit: int = 4) -> list:
    """Build targeted re-grounding queries for load-bearing claims lacking nearby [n]."""
    q = " ".join((question or "").split())
    a = answer or ""
    out = []
    # Bare numeric/date lines without citations
    for m in _BARE_CLAIM_RE.finditer(a[:2500]):
        span = m.group(0).strip()
        # Prefer a short window around the match
        start = max(0, m.start() - 40)
        window = " ".join(a[start : m.end() + 40].split())[:120]
        probe = f'{q} "{window}" official source' if window else f"{q} {span} official"
        if probe.lower() not in {x.lower() for x in out}:
            out.append(probe)
        if len(out) >= limit:
            return out[:limit]
    # Always include one grounding probe from the question lead
    if q and len(out) < limit:
        out.append(f"{q} primary source OR official statistics")
    return out[:limit]


def _v3_comparison_queries(question: str, limit: int = 2) -> list:
    """Concrete source-selection change: dual-operand evidence for comparison questions."""
    if not _COMPARE_Q_RE.search(question or ""):
        return []
    q = " ".join((question or "").split())
    # Split on common comparison markers
    parts = re.split(r"\b(?:versus|vs\.?|compared (?:to|with)|and|vs)\b", q, flags=re.I)
    parts = [p.strip(" ?.,;:") for p in parts if len(p.strip(" ?.,;:")) > 3]
    out = []
    for p in parts[:2]:
        out.append(f"{p} official figure OR primary source")
    if len(out) < 2 and q:
        out.append(f"{q} both sides official statistics")
    return out[:limit]


def _v3_roster_queries(question: str, limit: int = 2) -> list:
    """Concrete retrieval change: completeness fan-out for set/list/roster questions."""
    if not _ROSTER_Q_RE.search(question or ""):
        return []
    q = " ".join((question or "").split())
    return [
        f"complete list OR full roster: {q}",
        f"{q} all members OR entire set official",
    ][:limit]


def _probe_queries(question: str, answer: str) -> list:
    """Merge every verification branch into ONE deduped parallel batch."""
    candidates = []
    candidates.extend(_opposition_queries_from_answer(question, answer, limit=3))
    candidates.extend(_v3_claim_reground_queries(question, answer, limit=3))
    candidates.extend(_v3_comparison_queries(question, limit=2))
    candidates.extend(_v3_roster_queries(question, limit=2))
    deduped = []
    seen = set()
    for item in candidates:
        text = (item or "").strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            deduped.append(text)
    return deduped[:PROBE_MAX_QUERIES]


# ------------------------------------------------------------------ entrypoint


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

    # _research_loop never raises: it always returns (answer, well-formed
    # transcript) so the downstream probe/patch stages can re-enter it safely.
    index = _new_index()
    answer, messages = await _research_loop(
        question, briefing, index, deadline, MAX_TURNS
    )

    # Verification fan-out + revision. The probe evidence is CONSUMED here --
    # searching without a rewrite pass burns budget for zero score.
    try:
        answer = await _probe_and_revise(question, answer, messages, index, deadline)
    except Exception:
        pass

    try:
        if (
            answer
            and _remaining(deadline) > PATCH_MIN_SECONDS
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


async def _build_briefing(question: str) -> tuple:
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


def _init_messages(question: str, briefing: str, seed_messages) -> list:
    if seed_messages is not None:
        return seed_messages
    messages = [{"role": "system", "content": LOOP_SYSTEM_PROMPT}]
    if briefing:
        messages.append({"role": "system", "content": briefing})
    messages.append({"role": "user", "content": question})
    return messages


def _has_user_turn(messages: list) -> bool:
    """A transcript with no user turn cannot be resumed; guards re-entry."""
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") == "user":
            return True
    return False


async def _seed_and_prefetch(
    question: str, messages: list, index: dict, deadline: float
) -> None:
    """Seed fan-out, then auto-prefetch authority URLs found in the seed hits.

    Runs on fresh transcripts only -- re-entrant calls (probe / patch) must not
    repeat these searches and fetches.
    """
    seed_blob = ""
    try:
        seeds = _seed_queries_from_question(question, limit=3)
        if seeds and _remaining(deadline) > SEED_MIN_SECONDS:
            seed_blob = await _tool_search_many(seeds, index)
            messages.append({
                "role": "system",
                "content": (
                    "## Seed Evidence\n\nParallel seed searches already ran. "
                    "Use these numbered results; call search_many for remaining candidates.\n\n"
                    + seed_blob[:SEED_BLOB_CHARS]
                ),
            })
    except Exception:
        seed_blob = ""

    try:
        if not seed_blob or _remaining(deadline) <= PREFETCH_MIN_SECONDS:
            return
        auth_urls = _authority_urls_from_blob(seed_blob, limit=2)
        if not auth_urls:
            return
        coros = []
        for url in auth_urls:
            coros.append(_tool_fetch(url, index))
        results = await _run_parallel(coros)
        auth_parts = []
        for item in results:
            if isinstance(item, str) and item.strip():
                auth_parts.append(item)
        if auth_parts:
            messages.append({
                "role": "system",
                "content": (
                    "## Authority Prefetch\n\nPrimary/official pages were fetched "
                    "automatically from seed hits. Prefer these over secondary blogs.\n\n"
                    + "\n\n".join(auth_parts)[:PREFETCH_BLOB_CHARS]
                ),
            })
    except Exception:
        pass


async def _research_loop(
    question: str,
    briefing: str,
    index: dict,
    deadline: float,
    max_turns: int,
    seed_messages: list = None,
) -> tuple:
    """Returns (answer, transcript). Never raises: the transcript is the input
    for the probe and patch stages, so losing it costs the whole run."""
    messages = _init_messages(question, briefing, seed_messages)
    final_answer = ""
    try:
        if seed_messages is None:
            await _seed_and_prefetch(question, messages, index, deadline)
        final_answer = await _turn_loop(messages, index, deadline, max_turns)
    except Exception:
        pass
    return final_answer, messages


async def _turn_loop(
    messages: list, index: dict, deadline: float, max_turns: int
) -> str:
    final_answer = ""
    nudged = False
    for turn in range(1, max_turns + 1):
        remaining = _remaining(deadline)
        if remaining <= MIN_TURN_SECONDS:
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
        tool_calls = list(getattr(message, "tool_calls", None) or ())
        if not tool_calls:
            final_answer = (getattr(llm, "raw_text", None) or "").strip()
            if not final_answer:
                content = getattr(message, "content", None)
                if isinstance(content, str):
                    final_answer = content.strip()
            # Record the answer in the transcript. The probe and patch stages
            # re-enter this loop with these same messages and criticise "your
            # final answer" -- which the model cannot revise if it was never here.
            if final_answer:
                messages.append({"role": "assistant", "content": final_answer})
            break

        if not _append_assistant_turn(messages, message):
            break
        await _run_tool_calls(tool_calls, index, messages)
    return final_answer


def _append_assistant_turn(messages: list, message) -> bool:
    """A serialisation failure ends the loop cleanly instead of discarding the
    answer and the whole transcript."""
    try:
        messages.append(message.to_input_message())
        return True
    except Exception:
        return False


async def _run_tool_calls(tool_calls: list, index: dict, messages: list) -> None:
    coros = []
    for tc in tool_calls:
        coros.append(_run_tool_call(tc, index))
    outputs = await _run_parallel(coros)
    for position in range(len(tool_calls)):
        out = outputs[position] if position < len(outputs) else ""
        text = out if isinstance(out, str) else f"# tool error: {out}"
        call_id = getattr(tool_calls[position], "id", "") or ""
        messages.append(
            {"role": "tool", "tool_call_id": call_id, "content": text}
        )


async def _run_parallel(coros: list) -> list:
    """Concurrent execution with results in submission order.

    Statically-named calls only -- no argument unpacking into gather, and each
    failure is isolated to its own slot.
    """
    tasks = []
    for coro in coros:
        tasks.append(asyncio.ensure_future(coro))
    results = []
    for task in tasks:
        try:
            results.append(await task)
        except Exception as exc:
            results.append(exc)
    return results


def _message_chars(msg) -> int:
    if isinstance(msg, dict):
        content = msg.get("content")
        if isinstance(content, str):
            return len(content)
        return len(str(content))
    return len(str(msg))


def _trim_pass(messages: list, total: int, keep_chars: int) -> int:
    """Shorten OLDEST tool payloads to keep_chars until the cap is met."""
    for position in range(len(messages)):
        if total <= MAX_TRANSCRIPT_CHARS:
            return total
        msg = messages[position]
        if not isinstance(msg, dict) or msg.get("role") != "tool":
            continue
        content = msg.get("content")
        if not isinstance(content, str) or len(content) <= keep_chars:
            continue
        trimmed = content[:keep_chars] + TRIM_MARKER
        total -= len(content) - len(trimmed)
        msg["content"] = trimmed
    return total


def _trim_messages(messages: list) -> None:
    """Cap transcript size, oldest tool payloads sacrificed first.

    Tool messages are truncated, never dropped: removing one orphans its
    tool_call_id and the provider rejects the whole request. Two passes so a
    long tool-heavy run still converges -- one pass cannot reach the cap once
    every payload is already at TOOL_KEEP_CHARS.
    """
    total = 0
    for msg in messages:
        total += _message_chars(msg)
    if total <= MAX_TRANSCRIPT_CHARS:
        return
    total = _trim_pass(messages, total, TOOL_KEEP_CHARS)
    if total > MAX_TRANSCRIPT_CHARS:
        _trim_pass(messages, total, TOOL_STUB_CHARS)


async def _loop_chat(messages: list, deadline: float, *, force_text: bool):
    _trim_messages(messages)
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


async def _run_tool_call(tc, index: dict) -> str:
    try:
        args = json.loads(getattr(tc, "arguments", None) or "{}")
    except Exception:
        args = {}
    if not isinstance(args, dict):
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


# ----------------------------------------------------------------------- tools


async def _tool_search(q: str, index: dict, timeout: float = SEARCH_TIMEOUT) -> str:
    if not q.strip():
        return "# search_web -> empty query"
    resp = None
    for provider in ("parallel", "desearch"):
        try:
            attempt = await search_web(q, provider=provider, num=8, timeout=timeout)
        except Exception:
            continue
        if attempt is None:
            continue
        resp = attempt
        if getattr(attempt, "results", None):
            break
    if resp is None:
        return f"# search_web({q!r}) -> ERROR (all providers failed)"
    _note_budget(resp)
    receipt = getattr(resp, "receipt_id", "") or ""
    results = list(getattr(resp, "results", None) or [])
    lines = [f"# search_web({q!r}) -> {len(results)} results"]
    for result in results:
        rid = getattr(result, "result_id", None)
        if not isinstance(rid, str) or not rid:
            continue
        note = (getattr(result, "note", None) or "")[:SEARCH_NOTE_CHARS]
        number = _index_add(index, receipt, rid, note, "search")
        title = getattr(result, "title", None) or ""
        url = getattr(result, "url", None) or ""
        lines.append(f"[{number}] {title}\n  url: {url}\n  excerpt: {note}")
    return "\n".join(lines)


async def _tool_search_many(queries: list, index: dict,
                            timeout: float = SEARCH_TIMEOUT) -> str:
    """Concrete tool-use change: parallel multi-query retrieval in one turn."""
    clean = [str(q).strip() for q in (queries or []) if str(q).strip()][:8]
    if not clean:
        return "# search_many() -> ERROR: no queries"
    coros = []
    for q in clean:
        coros.append(_tool_search(q, index, timeout))
    results = await _run_parallel(coros)
    parts = []
    for item in results:
        if isinstance(item, str):
            parts.append(item)
        else:
            parts.append(f"# search error: {item}")
    return f"# search_many({len(clean)} queries)\n" + "\n\n".join(parts)


async def _tool_fetch(url: str, index: dict) -> str:
    if not url.strip():
        return "# fetch_page -> empty url"
    resp = None
    for provider in ("parallel", "desearch"):
        try:
            attempt = await fetch_page(url, provider=provider, timeout=FETCH_TIMEOUT)
        except Exception:
            continue
        if attempt is None:
            continue
        resp = attempt
        if getattr(attempt, "results", None):
            break
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
    number = _index_add(index, receipt, rid, note, "fetch")
    shown = note[:FETCH_NOTE_CHARS]
    return f"# fetch_page({url!r}) -> [{number}] {len(shown)} chars shown\n{shown}"


# --------------------------------------------------------- probe & revise


async def _probe_and_revise(
    question: str,
    answer: str,
    messages: list,
    index: dict,
    deadline: float,
) -> str:
    """One parallel verification batch, then one rewrite that consumes it."""
    base = (answer or "").strip()
    if not PROBE_ENABLED or not base:
        return answer
    if _remaining(deadline) < PROBE_MIN_SECONDS or _budget_left() < MIN_PATCH_BUDGET:
        return answer
    if not _has_user_turn(messages):
        return answer
    queries = _probe_queries(question, base)
    if not queries:
        return answer
    try:
        blob = await _tool_search_many(queries, index, PROBE_SEARCH_TIMEOUT)
    except Exception:
        return answer
    if not blob.strip():
        return answer
    messages.append(
        {"role": "system", "content": _PROBE_INSTRUCTION + blob[:PROBE_BLOB_CHARS]}
    )
    if _remaining(deadline) < REVISE_MIN_SECONDS:
        return answer
    revised, _ = await _research_loop(
        question, "", index, deadline, REVISE_TURNS, seed_messages=messages
    )
    if _prefer_revision(base, revised):
        return revised.strip()
    return answer


def _prefer_revision(original: str, revised: str) -> bool:
    """Non-regression guard: only take a rewrite that is not clearly degraded."""
    new_text = (revised or "").strip()
    if not new_text:
        return False
    old_text = (original or "").strip()
    if not old_text:
        return True
    new_cites = len(_BRACKET_RE.findall(new_text))
    old_cites = len(_BRACKET_RE.findall(old_text))
    if new_cites < old_cites and len(new_text) < len(old_text) * 0.7:
        return False
    if new_cites <= old_cites and len(new_text) < len(old_text) * 0.5:
        return False
    return True


# -------------------------------------------------------------- verify & patch


async def _verify_and_patch(
    question: str,
    answer: str,
    messages: list,
    index: dict,
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
    if not issues or _remaining(deadline) < PATCH_LOOP_SECONDS:
        return answer
    if not _has_user_turn(messages):
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
    if _prefer_revision(answer, patched):
        return patched.strip()
    return answer


# ------------------------------------------------------------------- citations


_BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")


def _cited_numbers(answer: str, max_number: int) -> list:
    seen = set()
    ordered = []
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


def _build_citations(answer: str, index: dict) -> list:
    numbers = _cited_numbers(answer, _index_max(index))
    refs = []
    for n in numbers[:MAX_CITATIONS]:
        entry = index["entries"].get(n)
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


async def _structured_output(question: str, answer: str, schema):
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
    thinking: dict = None,
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

# slot: harnyx 2026-07-31T14:16:03+00:00

# perfect_suffix: openrouter/parallel
_PERFECT_SUFFIX = "9e27adc9146d1e46"

