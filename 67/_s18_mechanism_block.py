

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
