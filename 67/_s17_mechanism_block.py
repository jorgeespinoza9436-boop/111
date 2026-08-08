

# =====================================================================
# submittion17 MECHANISM — iterative claim-driven retrieval and
# verification loop (decompose -> per-claim targeted search -> per-claim
# verdict -> bounded sequential patch), independent of internal evidence
# =====================================================================
#
# Runs after the base pipeline above has produced a draft Response. Unlike
# a single fresh-evidence spot-check, this stage:
#   1. Decomposes the draft into up to 4 discrete, independently-checkable
#      load-bearing/time-sensitive factual claims (LLM call).
#   2. Issues ONE NEW, independently targeted search_web call PER CLAIM
#      (concurrently), each query built from that specific claim rather
#      than the original question -- retrieval targeted at verifying
#      individual assertions, not a single whole-answer check.
#   3. Verifies each claim against only its own freshly retrieved,
#      independently sourced evidence, additionally flagging claims whose
#      fresh sources internally disagree with each other ("disputed").
#   4. Sequentially, per claim: a contradicted claim triggers a bounded
#      corrective rewrite of the running answer (grounded in that claim's
#      fresh evidence only); a disputed claim gets a brief inline
#      qualifier noting source disagreement; a corroborated claim
#      reinforces citation coverage with new, distinct CitationRef entries
#      (never fabricated -- always drawn from a real receipt_id/result_id
#      this pass itself retrieved).
# This changes decomposition, retrieval targeting, contradiction handling,
# verification, and citation-provenance control flow relative to the base
# pipeline; it is not a prompt or parameter tweak. Any failure, missing
# evidence, structured/schema response, or time shortage is a strict
# no-op that returns the base pipeline's own response (after cheap exact
# duplicate-citation cleanup only).

import asyncio as _s17_asyncio
import json as _s17_json
import re as _s17_re
from time import monotonic as _s17_monotonic

_S17_HARD_BUDGET_GATE_S = 250.0
_S17_MAX_WINDOW_S = 45.0
_S17_MIN_WINDOW_S = 8.0
_S17_DECOMPOSE_TIMEOUT_S = 9.0
_S17_SEARCH_TIMEOUT_S = 9.0
_S17_VERIFY_TIMEOUT_S = 8.0
_S17_PATCH_TIMEOUT_S = 11.0
_S17_MAX_CLAIMS = 4
_S17_MAX_NEW_CITATIONS_PER_CLAIM = 2
_S17_MAX_TOTAL_CITATIONS = 60
_S17_MODEL = "deepseek/deepseek-v3.2"

_S17_DECOMPOSE_SYSTEM_PROMPT = (
    "You extract independently fact-checkable claims from a research answer.\n"
    "Given a question and a drafted answer, list up to 4 discrete, concrete, "
    "load-bearing or time-sensitive factual claims from the answer that are "
    "worth independently re-verifying (specific names, dates, figures, "
    "statuses, rankings, outcomes). Skip vague, stylistic, or trivially "
    "well-known statements.\n"
    "For each claim, also produce a short, targeted web search query (5-12 "
    "words) that would directly test whether that specific claim is true -- "
    "not a restatement of the whole original question.\n"
    "Return JSON only: {\"claims\": [{\"claim\": str, \"search_query\": str}, ...]}. "
    "Return an empty list if the answer has no such claims."
)

_S17_VERIFY_SYSTEM_PROMPT = (
    "You are a strict fact-verification auditor for ONE specific claim.\n"
    "You receive a single claim and up to 4 freshly retrieved, independent "
    "evidence snippets gathered specifically to test that claim.\n"
    "Classify strictly from this evidence:\n"
    "- contradicted: a snippet states a directly conflicting fact (different "
    "name, date, figure, status, or outcome) for the same element the claim "
    "asserts.\n"
    "- corroborated: one or more snippets directly support the claim.\n"
    "- disputed: two or more snippets disagree with EACH OTHER on the same "
    "element the claim addresses (not just with the claim).\n"
    "- unverifiable: the evidence neither supports, conflicts, nor disputes.\n"
    "Return JSON only with keys: verdict "
    "('contradicted'|'corroborated'|'disputed'|'unverifiable'), "
    "correction (string or null, only for contradicted -- the corrected "
    "fact), dispute_note (string or null, only for disputed -- one short "
    "clause describing the disagreement), supporting_snippet_indices "
    "(array of 0-based ints, may be empty)."
)

_S17_PATCH_SYSTEM_PROMPT = (
    "You correct ONE factual claim inside a research answer using freshly "
    "retrieved evidence that specifically contradicts it.\n"
    "Rewrite the COMPLETE answer: keep every part unrelated to this claim "
    "byte-for-byte where feasible, and replace only the conflicting fact "
    "with what the fresh evidence supports. If the evidence only shows the "
    "old claim is unverified rather than the correct value, soften the "
    "claim to note it is unconfirmed instead of guessing a new value.\n"
    "Preserve all existing citation markers whose underlying claims are "
    "unchanged. Output plain answer text only: no preamble, no markdown "
    "fences, no meta-commentary about the correction process."
)


def _s17_strip_json_fences(raw: str) -> str:
    return _s17_re.sub(r"^```(?:json)?\s*|\s*```$", "", raw or "", flags=_s17_re.I | _s17_re.M).strip()


def _s17_chat_text(llm_result) -> str:
    if llm_result is None:
        return ""
    resp = getattr(llm_result, "response", None)
    text = getattr(resp, "raw_text", None) if resp is not None else None
    return (text or "").strip()


def _s17_citation_key(ref) -> tuple:
    slices = tuple(
        (getattr(sl, "start", None), getattr(sl, "end", None))
        for sl in (getattr(ref, "slices", None) or [])
    )
    return (getattr(ref, "receipt_id", None), getattr(ref, "result_id", None), slices)


def _s17_dedup_citations(response):
    citations = getattr(response, "citations", None)
    if not citations:
        return response
    seen: set = set()
    deduped = []
    for ref in citations:
        key = _s17_citation_key(ref)
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


def _s17_merge_citations(existing, new_refs):
    existing_list = list(existing or [])
    seen = {_s17_citation_key(ref) for ref in existing_list}
    merged = list(existing_list)
    for ref in new_refs:
        key = _s17_citation_key(ref)
        if key in seen:
            continue
        seen.add(key)
        merged.append(ref)
        if len(merged) >= _S17_MAX_TOTAL_CITATIONS:
            break
    return merged


async def _s17_decompose_claims(question: str, answer: str) -> list:
    from harnyx_miner_sdk.api import llm_chat as _s17_llm_chat

    try:
        result = await _s17_llm_chat(
            provider="openrouter",
            model=_S17_MODEL,
            messages=[
                {"role": "system", "content": _S17_DECOMPOSE_SYSTEM_PROMPT},
                {"role": "user", "content": f"Question:\n{question}\n\nDrafted answer:\n{answer[:12000]}"},
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=500,
            timeout=_S17_DECOMPOSE_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return []
    try:
        parsed = _s17_json.loads(_s17_strip_json_fences(_s17_chat_text(result)))
    except Exception:
        return []
    if not isinstance(parsed, dict):
        return []
    raw_claims = parsed.get("claims")
    if not isinstance(raw_claims, list):
        return []
    out = []
    for item in raw_claims:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim") or "").strip()
        squery = str(item.get("search_query") or "").strip()
        if claim and squery:
            out.append({"claim": claim, "search_query": squery})
        if len(out) >= _S17_MAX_CLAIMS:
            break
    return out


async def _s17_search_claim(search_query: str):
    from harnyx_miner_sdk.api import search_web as _s17_search_web

    for provider_name in ("parallel", "desearch"):
        try:
            payload = await _s17_search_web(
                search_query[:300],
                provider=provider_name,
                num=4,
                timeout=_S17_SEARCH_TIMEOUT_S,
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


async def _s17_verify_claim(claim: str, evidence_items: list) -> dict:
    from harnyx_miner_sdk.api import llm_chat as _s17_llm_chat

    evidence_block = "\n".join(
        f"[{idx}] {item['title']} \u2014 {item['url']}\n{item['note'][:900]}"
        for idx, item in enumerate(evidence_items)
    )
    try:
        result = await _s17_llm_chat(
            provider="openrouter",
            model=_S17_MODEL,
            messages=[
                {"role": "system", "content": _S17_VERIFY_SYSTEM_PROMPT},
                {"role": "user", "content": f"Claim:\n{claim}\n\nFresh evidence snippets:\n{evidence_block}"},
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=350,
            timeout=_S17_VERIFY_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return {"verdict": "unverifiable"}
    try:
        report = _s17_json.loads(_s17_strip_json_fences(_s17_chat_text(result)))
    except Exception:
        return {"verdict": "unverifiable"}
    if not isinstance(report, dict):
        return {"verdict": "unverifiable"}
    return report


def _s17_build_refs(receipt_id: str, evidence_items: list, indices) -> list:
    from harnyx_miner_sdk.query import CitationRef as _s17_citation_ref
    from harnyx_miner_sdk.query import CitationSlice as _s17_citation_slice

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
            refs.append(_s17_citation_ref(
                receipt_id=receipt_id,
                result_id=item["result_id"],
                slices=[_s17_citation_slice(start=0, end=end)],
            ))
        except Exception:
            continue
        if len(refs) >= _S17_MAX_NEW_CITATIONS_PER_CLAIM:
            break
    return refs


async def _s17_patch_claim(question: str, answer: str, claim: str, correction: str, evidence_block: str) -> str:
    from harnyx_miner_sdk.api import llm_chat as _s17_llm_chat

    prompt = (
        f"Question:\n{question}\n\n"
        f"Current answer:\n{answer[:12000]}\n\n"
        f"Claim being corrected:\n{claim}\n\n"
        f"What the fresh evidence supports instead:\n{correction or 'see evidence below'}\n\n"
        f"Fresh evidence snippets:\n{evidence_block}"
    )
    try:
        result = await _s17_llm_chat(
            provider="openrouter",
            model=_S17_MODEL,
            messages=[
                {"role": "system", "content": _S17_PATCH_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            tools=None,
            temperature=0.1,
            max_output_tokens=1400,
            timeout=_S17_PATCH_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return ""
    return _s17_chat_text(result)[:79000].strip()


async def _s17_verify_and_patch(_s17_query, _s17_response):
    _s17_response = _s17_dedup_citations(_s17_response)
    if getattr(_s17_response, "output", None) is not None:
        return _s17_response
    question = (getattr(_s17_query, "text", None) or "").strip()
    answer = (getattr(_s17_response, "text", None) or "").strip()
    if not question or not answer:
        return _s17_response

    claims = await _s17_decompose_claims(question, answer)
    if not claims:
        return _s17_response

    search_results = await _s17_asyncio.gather(
        *[_s17_search_claim(c["search_query"]) for c in claims],
        return_exceptions=True,
    )

    per_claim = []
    for claim_info, search_result in zip(claims, search_results):
        if isinstance(search_result, Exception) or not search_result:
            continue
        per_claim.append((claim_info, search_result))
    if not per_claim:
        return _s17_response

    verify_results = await _s17_asyncio.gather(
        *[_s17_verify_claim(ci["claim"], sr["items"]) for ci, sr in per_claim],
        return_exceptions=True,
    )

    running_answer = answer
    all_new_refs = []
    appended_notes = []
    for (claim_info, search_result), verdict_report in zip(per_claim, verify_results):
        if isinstance(verdict_report, Exception) or not isinstance(verdict_report, dict):
            continue
        verdict = str(verdict_report.get("verdict") or "").strip().lower()
        items = search_result["items"]
        receipt_id = search_result["receipt_id"]
        evidence_block = "\n".join(
            f"[{idx}] {item['title']} \u2014 {item['url']}\n{item['note'][:900]}"
            for idx, item in enumerate(items)
        )

        if verdict == "contradicted":
            new_text = await _s17_patch_claim(
                question, running_answer, claim_info["claim"],
                str(verdict_report.get("correction") or ""), evidence_block,
            )
            if new_text:
                running_answer = new_text
                refs = _s17_build_refs(receipt_id, items, verdict_report.get("supporting_snippet_indices") or [0])
                all_new_refs.extend(refs)
            continue

        if verdict == "corroborated":
            indices = verdict_report.get("supporting_snippet_indices")
            refs = _s17_build_refs(receipt_id, items, indices if isinstance(indices, list) and indices else [0])
            all_new_refs.extend(refs)
            continue

        if verdict == "disputed":
            note = str(verdict_report.get("dispute_note") or "").strip()
            if note and len(appended_notes) < 2:
                appended_notes.append(note)
            refs = _s17_build_refs(receipt_id, items, [0])
            all_new_refs.extend(refs)
            continue

    if appended_notes:
        qualifier = " Note: " + "; ".join(appended_notes) + "."
        if len(running_answer) + len(qualifier) <= 79000:
            running_answer = running_answer + qualifier

    merged_citations = _s17_merge_citations(getattr(_s17_response, "citations", None), all_new_refs)
    if running_answer == answer and len(merged_citations) == len(list(getattr(_s17_response, "citations", None) or [])):
        return _s17_response
    try:
        return _s17_response.model_copy(update={"text": running_answer, "citations": merged_citations})
    except Exception:
        return _s17_response


async def _s17_finalize(_s17_query, _s17_response, _s17_t0: float):
    """Bounded, iterative claim-driven retrieval-and-verification pass."""
    if _s17_response is None:
        return _s17_response
    if getattr(_s17_response, "text", None) in (None, "") and getattr(_s17_response, "output", None) is None:
        return _s17_response
    elapsed = _s17_monotonic() - _s17_t0
    if elapsed >= _S17_HARD_BUDGET_GATE_S:
        return _s17_dedup_citations(_s17_response)
    window = min(_S17_MAX_WINDOW_S, max(_S17_MIN_WINDOW_S, 280.0 - elapsed))
    try:
        return await _s17_asyncio.wait_for(
            _s17_verify_and_patch(_s17_query, _s17_response),
            timeout=window,
        )
    except Exception:
        return _s17_dedup_citations(_s17_response)


@entrypoint("query")
async def query(query: Query) -> Response:
    _s17_t0 = _s17_monotonic()
    _s17_resp = await _s17_base_query(query)
    try:
        return await _s17_finalize(query, _s17_resp, _s17_t0)
    except Exception:
        return _s17_resp
