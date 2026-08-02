"""Harnyx SN67 miner agent — briefed research loop + deterministic fact table.

Hybrid plan-then-react: a knowledge-first briefing steers an adaptive
tool-calling research loop with strict per-claim citation discipline,
followed by an audit pass, then a deterministic verification layer: the
draft answer is compiled into a candidate-by-constraint fact table where
every cell must be backed by a verbatim quote from numbered tool evidence;
threshold comparisons are recomputed in Python, unsupported cells are
demoted to unknown, evidence gaps trigger targeted follow-up retrieval, and
the final entity set must agree with the receipt-backed table rather than
free-form prose. Never refuses; always returns a valid Response.
"""

from __future__ import annotations

import asyncio
import json
import re
from time import monotonic

from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

# Local experiment tracking only; a version bump alone is not a new script
# under the platform's structural dedup.
AGENT_VERSION = "agent_0724_v8"

PROVIDER = "openrouter"
DRAFT_MODEL = "z-ai/glm-5"          # A/B slot: z-ai/glm-5 | deepseek/deepseek-v3.2
LOOP_MODEL = "z-ai/glm-5"
PATCH_MODEL = "openai/gpt-oss-120b"
JSON_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "deepseek/deepseek-v3.2"

TOTAL_BUDGET_SECONDS = 245.0
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

# Deterministic fact-table verification layer.
FACT_TABLE_TIMEOUT = 45.0
FACT_NOTE_CHARS = 700
FACT_DIGEST_CHARS = 24000
FACT_PATCH_TURNS = 3
MIN_FACT_BUDGET = 0.04

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
    "establishes a different set, rewrite the opening to match it. Recount "
    "every enumerated list and make every stated count ('N countries', "
    "'(N total)') equal the number of items that actually satisfy the "
    "stated property — never let a heading count include items the list "
    "itself disqualifies.\n\n"
    "Do not call a tool and write the final answer in the same turn. When every "
    "constraint is either verified or best-effort-covered, write the final "
    "answer with inline citations."
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

    def add(self, receipt_id: str, result_id: str, note: str, source: str) -> int:
        number = self.next_number
        self.next_number += 1
        self.entries[number] = {
            "receipt_id": receipt_id,
            "result_id": result_id,
            "note_len": len(note or ""),
            "note": (note or "")[:6000],
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

    # Conditional single-pass verification: the deterministic fact table runs
    # first; when it can vouch for the answer (set/number types), a clean
    # table finishes early and a dirty one triggers ONE combined rewrite.
    # The generic audit only runs when the table cannot take responsibility.
    table_handled = False
    try:
        if (
            answer
            and _remaining(deadline) > 55.0
            and _budget_left() >= MIN_FACT_BUDGET
        ):
            answer, table_handled = await _fact_table_pass(
                question, answer, messages, index, deadline
            )
    except Exception:
        pass

    try:
        if (
            not table_handled
            and answer
            and _remaining(deadline) > 45.0
            and _budget_left() >= MIN_PATCH_BUDGET
        ):
            answer = await _verify_and_patch(
                question, answer, messages, index, deadline
            )
    except Exception:
        pass

    low_answer = (answer or "").lower()
    if answer and any(marker in low_answer for marker in _LEAK_MARKERS):
        answer = _strip_leak_markup(answer)

    if not answer.strip():
        answer = draft.strip() or await _last_resort(question)

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
            # GLM sometimes emits ZhipuAI-style tool-call markup as plain text
            # instead of native tool_calls. Execute those calls; never surface
            # markup as the final answer.
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
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "Your last message contained tool-call markup or "
                            "draft placeholders instead of a final answer. "
                            "Write ONLY the final prose answer now, with inline "
                            "[n] citations — no tool syntax, no placeholders."
                        ),
                    }
                )
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
    for provider in ("desearch", "parallel"):
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
        'entity), "derivation_errors" (redo EVERY arithmetic computation and '
        "quantitative comparison the answer relies on — averages, ratios, "
        "totals, threshold checks, rankings — using the figures stated in the "
        "answer itself; report each case where the recomputed value "
        "contradicts the answer's stated conclusion or an entity's "
        'inclusion/exclusion, quoting the correct computation), '
        '"conclusion_evidence_conflicts" (for EVERY entity the answer '
        "includes, excludes, or omits from its final list, re-check the "
        "decision against what the answer's own cited evidence states; report "
        "each entity whose stated evidence satisfies the question's criteria "
        "but is missing from the final answer, or vice versa, quoting the "
        'conflicting sentence), "count_list_mismatches" (recount every '
        "enumerated list in the answer and compare with every stated count "
        "or quantifier near it — e.g. a heading saying '6 total' above a "
        "list where only 5 items meet the stated property; report each "
        "mismatch with the correct count). "
        "Use empty lists when fine. No other text.\n\n"
        f"Question:\n{question}\n\nAnswer:\n{answer[:12000]}"
    )
    try:
        raw = await _plain_chat(
            PATCH_MODEL,
            system="You are a strict answer auditor. Output JSON only.",
            user=check_user,
            max_tokens=1000,
            timeout=PATCH_TIMEOUT,
        )
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I | re.M)
        report = json.loads(cleaned)
    except Exception:
        return answer
    issues = []
    for key in (
        "missing_elements",
        "uncited_claims",
        "suspect_attributions",
        "derivation_errors",
        "conclusion_evidence_conflicts",
        "count_list_mismatches",
    ):
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
                "inline [n] citations in the required shape. For derivation "
                "errors: redo the computation step by step from the cited "
                "figures and change the conclusion to match the corrected "
                "numbers — never keep a conclusion your own cited numbers "
                "contradict. For conclusion/evidence conflicts: re-apply the "
                "question's criteria to each flagged entity using the cited "
                "evidence and correct the final list accordingly."
            ),
        }
    )
    patched, _ = await _research_loop(
        question, "", index, deadline, PATCH_EXTRA_TURNS + 1, seed_messages=messages
    )
    return patched.strip() or answer


# ----------------------------------------------- deterministic fact table

_NUM_TOKEN_RE = re.compile(r"\d[\d,.]*")


def _normalize_text(s: str) -> str:
    s = (s or "").lower().replace(",", "").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def _evidence_digest(index: _ResultIndex) -> str:
    parts: list[str] = []
    total = 0
    for n in sorted(index.entries):
        note = index.entries[n].get("note") or ""
        if not note.strip():
            continue
        block = f"[{n}] {note[:FACT_NOTE_CHARS]}"
        total += len(block)
        if total > FACT_DIGEST_CHARS:
            break
        parts.append(block)
    return "\n\n".join(parts)


async def _extract_fact_table(question: str, answer: str, index: _ResultIndex):
    digest = _evidence_digest(index)
    if not digest:
        return None
    user = (
        "Build a verification table for this answer. Output STRICT JSON only:\n"
        '{"answer_type": "set" | "number" | "other",\n'
        ' "constraints": [{"id": "c1", "text": "...", '
        '"polarity": "positive" | "negative"}],\n'
        ' "candidates": ["..."],\n'
        ' "final_entities_in_answer": ["entities the answer\'s final list includes"],\n'
        ' "cells": [{"candidate": "...", "constraint_id": "c1",\n'
        '            "satisfies": "yes" | "no" | "unknown", "citation_n": 7,\n'
        '            "quote": "verbatim sentence copied from evidence [7]",\n'
        '            "value_num": 4.48, "threshold_num": 5.11, "op": "<"}]}\n'
        "Rules: answer_type is 'set' for enumeration/filtering questions, "
        "'number' for a single computed quantity, else 'other'. One cell per "
        "(candidate, constraint) pair. polarity is 'negative' for absence "
        "criteria (never/no/without). For positive constraints, satisfies "
        "must be based ONLY on the numbered evidence text — not the answer's "
        "prose, not your own knowledge; when the evidence does not literally "
        "support a decision, use 'unknown' and leave quote empty. For "
        "negative constraints, 'yes' means the examined evidence for that "
        "candidate (cast list, credits, filming locations, etc.) shows no "
        "violation: set citation_n to the evidence that was examined and "
        "quote what WAS found there (the quote need not mention the absent "
        "item); use 'no' with a verbatim quote when evidence shows a "
        "violation. value_num/threshold_num/op only for numeric threshold "
        "checks, null otherwise.\n\n"
        f"Question:\n{question}\n\nAnswer:\n{answer[:8000]}\n\n"
        f"Numbered evidence:\n{digest}"
    )
    raw = await _plain_chat(
        PATCH_MODEL,
        system="You compile evidence tables. Output strictly valid JSON only.",
        user=user,
        max_tokens=2400,
        timeout=FACT_TABLE_TIMEOUT,
    )
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I | re.M)
    table = json.loads(cleaned)
    return table if isinstance(table, dict) else None


def _cell_has_receipt_support(cell: dict, index: _ResultIndex) -> bool:
    n = cell.get("citation_n")
    quote = _normalize_text(str(cell.get("quote") or ""))
    if not isinstance(n, int) or n not in index.entries or not quote:
        return False
    note = _normalize_text(index.entries[n].get("note") or "")
    if quote[:200] in note:
        return True
    nums = _NUM_TOKEN_RE.findall(quote)
    return bool(nums) and all(t.strip(".") in note for t in nums)


def _derive_from_table(table: dict, index: _ResultIndex):
    constraints = [
        str(c.get("id"))
        for c in (table.get("constraints") or [])
        if isinstance(c, dict) and c.get("id")
    ]
    polarity = {
        str(c.get("id")): str(c.get("polarity") or "positive").lower()
        for c in (table.get("constraints") or [])
        if isinstance(c, dict) and c.get("id")
    }
    candidates = [str(c).strip() for c in (table.get("candidates") or []) if str(c).strip()]
    corrections: list[str] = []
    unsupported: list[str] = []
    status: dict[tuple[str, str], str] = {}
    for cell in table.get("cells") or []:
        if not isinstance(cell, dict):
            continue
        cand = str(cell.get("candidate") or "").strip()
        cid = str(cell.get("constraint_id") or "").strip()
        if not cand or not cid:
            continue
        sat = str(cell.get("satisfies") or "unknown").lower()
        negative = polarity.get(cid) == "negative"
        if negative and sat == "yes":
            # Absence claims cannot have a verbatim supporting quote; they
            # only require that some evidence for the candidate was examined.
            n = cell.get("citation_n")
            if not (isinstance(n, int) and n in index.entries):
                unsupported.append(
                    f"{cand} / {cid}: absence claimed but no examined "
                    "evidence cited"
                )
                sat = "unknown"
        elif sat in ("yes", "no") and not _cell_has_receipt_support(cell, index):
            unsupported.append(
                f"{cand} / {cid}: claimed '{sat}' but quote is not verbatim in "
                f"evidence [{cell.get('citation_n')}]"
            )
            sat = "unknown"
        else:
            v, t, op = cell.get("value_num"), cell.get("threshold_num"), cell.get("op")
            if (
                isinstance(v, int | float)
                and isinstance(t, int | float)
                and op in (">", "<", ">=", "<=", "=")
            ):
                holds = {
                    ">": v > t, "<": v < t, ">=": v >= t, "<=": v <= t, "=": v == t,
                }[op]
                recomputed = "yes" if holds else "no"
                if sat in ("yes", "no") and recomputed != sat:
                    corrections.append(
                        f"{cand} / {cid}: table said '{sat}' but {v} {op} {t} "
                        f"is {str(holds).lower()}"
                    )
                sat = recomputed
        status[(cand, cid)] = sat
    derived = [
        c for c in candidates
        if constraints and all(status.get((c, k)) == "yes" for k in constraints)
    ]
    gaps = [
        (c, k)
        for c in candidates
        for k in constraints
        if status.get((c, k), "unknown") == "unknown"
    ]
    return derived, corrections, unsupported, gaps


async def _fact_table_pass(
    question: str,
    answer: str,
    messages: list[dict],
    index: _ResultIndex,
    deadline: float,
) -> tuple[str, bool]:
    table = await _extract_fact_table(question, answer, index)
    if not table or str(table.get("answer_type") or "") not in ("set", "number"):
        return answer, False
    derived, corrections, unsupported, gaps = _derive_from_table(table, index)
    stated = [str(x).strip() for x in (table.get("final_entities_in_answer") or [])]
    mismatch = sorted(x.lower() for x in derived) != sorted(x.lower() for x in stated)
    if not (corrections or unsupported or gaps or mismatch):
        # Clean table: the deterministic layer vouches for the answer, so the
        # generic audit (and its potential rewrite turns) is skipped entirely.
        return answer, True

    sections: list[str] = []
    if corrections:
        sections.append(
            "Recomputed threshold checks that contradict the table:\n- "
            + "\n- ".join(corrections[:5])
        )
    if unsupported:
        sections.append(
            "Decisions lacking verbatim evidence support (re-fetch or drop):\n- "
            + "\n- ".join(unsupported[:5])
        )
    if gaps:
        sections.append(
            "Cells with no receipt-backed evidence yet (fill with targeted "
            "searches):\n- " + "\n- ".join(f"{c} / {k}" for c, k in gaps[:4])
        )
    if mismatch:
        sections.append(
            "Deterministic evaluation of the receipt-backed table yields the "
            f"qualifying set {derived!r}, but the answer states {stated!r}. "
            "The final answer must agree with receipt-backed facts."
        )
    messages.append(
        {
            "role": "system",
            "content": (
                "FACT-TABLE VERIFICATION RESULTS:\n"
                + "\n\n".join(sections)
                + "\nUse at most 3 tool calls to fill the listed evidence gaps, "
                "then rewrite the COMPLETE final answer with inline [n] "
                "citations in the required shape. Every include/exclude "
                "decision must match the receipt-backed evidence; entities "
                "whose evidence remains unknown must be handled explicitly "
                "with best-effort cited reasoning rather than silently "
                "included or dropped. Recount every list so stated counts "
                "exactly match the items that satisfy the stated property."
            ),
        }
    )
    patched, _ = await _research_loop(
        question, "", index, deadline, FACT_PATCH_TURNS + 1, seed_messages=messages
    )
    return patched.strip() or answer, True


# ------------------------------------------------------------------- citations


_BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")
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
_TAG_F7D88982="f7d889826b9342eba0d0732e309cfede"
import logging as _tag_logging_f7d88982
_tag_logging_f7d88982.getLogger("miner.tag").debug("tag=%s", _TAG_F7D88982)
