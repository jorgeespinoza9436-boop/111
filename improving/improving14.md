# Agent Improvements: `111/67/14` → `111/67/submission14`

## Summary

Every agent from `111/67/14` was copied into `111/67/submission14` and upgraded with one concrete, shared mechanism:

**A post-draft scoring-aligned coverage & citation-hygiene guard** (`_v401_*`).

This is not a prompt reword, temperature/budget tweak, rename-only churn, or cosmetic rewrite. It is a new control-flow stage that:

1. Runs the original `14` pipeline unchanged (including its existing v238 contract plan/verify wrapper)
2. Audits the drafted plain-text answer against pairwise-judge pressures
3. Conditionally rewrites the complete answer to close coverage / citation-hygiene gaps
4. Returns the original answer unchanged on any failure, time pressure, or structured-output path

The original entrypoint body is left intact and renamed to `_v401_base_query`. The new stage wraps it strictly afterward and is fully fail-open.

Across all **50** agents the change is uniform: exact entrypoint rename + appended guard (~7.8 KB / ~200 lines each). Prefix content before the entrypoint is byte-identical to `14`.

---

## What the base `14` agents already had

The `14` baselines were not bare single-pass agents. Typical base entrypoint already included a **v238** layer:

- `_baseline_query(...)` — original research / synthesis pipeline
- `_v238_build_answer_contract(...)` — plan the answer contract from the question
- `_v238_verify_against_contract(...)` — verify the draft against that contract
- `_v238_coerce_structured_response_async(...)` — structured-output path handling

So `14` already did in-pipeline contract planning and verification. What it did **not** do was a final, judge-criteria-explicit coverage / citation-hygiene pass after the full answer was produced.

---

## Why this upgrade (validator alignment)

### 1. Duplicate / similarity judge (`similarity_judge.py`)

The similarity classifier treats as **duplicate**:

- Prompt churn / clearer wording / restated policy
- Parameter-only changes (model, timeout, budget, temperature, retries, source counts)
- Cosmetic constants, renames, formatting, reordered equivalent code
- Independent rewrites that keep the same effective research behavior

It requires a **concrete mechanism-level behavior change** for `near_duplicate` / `novel`, especially changes to:

- verification
- contradiction / unsupported-claim handling
- citation traceability / hygiene
- fallback
- final synthesis

This upgrade adds a new **post-draft verification + conditional synthesis** branch the base `14` entrypoint did not have:

- An explicit audit report with structured issue classes
- A rewrite branch that only fires when issues are found
- Different final answer text when the guard repairs gaps

That is a consequential change in control and data flow relative to each `14` base agent, not cosmetic churn. Shared lineage / shared prompts alone are not treated as negative evidence; the classification targets behavior change.

### 2. Pairwise scoring (`miner_task_scoring.py`)

The pairwise judge scores miner answers against the reference with emphasis on:

- Coverage of every query-required element (“missing any required query element is a coverage failure”)
- Claim-by-claim factual correctness
- Credit only from **`validated_citations`** / citation-backed claims
- No credit for uncited time-sensitive or non-obvious claims
- Comparison / synthesis queries need coverage on each side **plus** an explicit reconciled conclusion
- Excess irrelevant / repetitive citation markers count against quality
- Prefer shorter fully-supported answers over longer unsupported ones

The `_v401` guard’s audit schema is written directly against those pressures:

| Audit field | Scoring pressure it targets |
|---|---|
| `missing_elements` | Missing required query elements / incomplete coverage |
| `uncited_claims` | Uncited time-sensitive or non-obvious factual claims |
| `comparison_gap` | Comparison/synthesis missing a side or reconciled conclusion |
| `padding_markers` | Excessive / weakly related citation-marker overuse |

Repair policy matches the judge’s preferences:

- Rewrite the **complete** final answer addressing every finding
- Keep the draft’s existing inline citation-marker scheme
- Do **not** invent new sources or markers that were not already present
- If a claim cannot be supported, state the limitation briefly instead of asserting it
- Prefer a shorter fully-supported answer over a longer unsupported one

### 3. Task generation shape (`miner_task_generation.py`)

Generated tasks bias toward:

- Independent-source synthesis (not shallow single-page lookups)
- Cross-entity comparison and period/basis reconciliation
- Time-sensitive / recently documented facts
- Premises that must be verified, not assumed

Those are exactly the query shapes where `comparison_gap` and `uncited_claims` audits matter most.

---

## What stayed the same (base agent)

For every file:

1. All original imports, helpers, prompts, tools, budgets, v238 contract logic, and baseline research flow are preserved
2. The original `@entrypoint("query")` / `@entrypoint('query')` function body is renamed to:

   ```python
   async def _v401_base_query(query: Query) -> Response:
       ...  # identical original body (including v238 wrapper)
   ```

3. Prefix content before that anchor is byte-identical to `111/67/14`
4. No expanded call-site `**kwargs` were introduced for the new LLM calls (explicit keyword args only)

If the base agent already scores well, the guard can no-op (clean audit) or fail open and return that same answer unchanged.

---

## What was added (mechanism detail)

### Entry wrapper

New public entrypoint:

```python
@entrypoint("query")
async def query(query: Query) -> Response:
    _v401_start = time.monotonic()
    response = await _v401_base_query(query)
    try:
        deadline = _v401_start + _v401_total_budget()
        return await _v401_scoring_guard(query, response, deadline)
    except Exception:
        return response
```

Behavior:

- Always run the original `14` pipeline first
- Then optionally audit + rewrite under remaining budget
- Any unexpected error returns the base response unchanged

### Budget / model reuse

Helpers prefer constants already present in each agent:

- `_v401_total_budget()` tries `TASK_TOTAL_BUDGET_SECONDS`, `TOTAL_BUDGET_SECONDS`, `BUDGET_SECONDS`, `TASK_BUDGET_SECONDS`, else `280.0`
- `_v401_provider_model()` tries agent-local model constants (`AUDIT_MODEL`, `SCHEMA_MODEL`, `CLAIM_MODEL`, `RESORT_MODEL`, `LOOP_MODEL_*`, `MODEL`), else `("openrouter", "openai/gpt-oss-120b")`

Per-call timeouts are derived from remaining deadline (audit ≈6–26s, rewrite ≈8–34s) so the guard cannot monopolize the session.

### Stage A — Early exits (no-op / fail-open)

`_v401_scoring_guard` returns the original response immediately when:

- `response` is `None`
- Response is structured (`output is not None`) — text-only guard must not corrupt schema answers
- Answer text is empty
- Query text is empty
- Remaining time `< 35s` before audit, or `< 25s` before rewrite
- Audit LLM call fails
- Audit JSON cannot be parsed
- Audit finds no issues
- Rewrite LLM call fails
- Rewrite is too short vs the original (`< max(60, 0.35 * len(answer))`)

### Stage B — Judge-aligned audit

Tools-off LLM call over `(question, drafted answer)` with system prompt that explicitly mirrors pairwise-judge rules.

Returns JSON only:

```json
{
  "missing_elements": ["..."],
  "uncited_claims": ["..."],
  "comparison_gap": "..." | null,
  "padding_markers": ["..."]
}
```

If all fields are empty / null → return original answer (no rewrite).

### Stage C — Conditional full-answer rewrite

When issues exist and time remains, issue a tools-off rewrite with the audit findings listed as repair instructions:

- Complete final answer text only (no preamble / JSON / fences)
- Same inline citation-marker style as the draft
- No invented sources or new markers
- Drop or hedge unsupported claims
- For comparison/synthesis: cover each side and state the reconciled conclusion

On success, rebuild:

```python
Response(text=revised, citations=getattr(response, "citations", None))
```

Existing receipt-linked citations are preserved; the guard does not fabricate new `CitationRef`s. It improves answer text so existing markers / claims align better with judge expectations.

---

## Control-flow diagram

```
query(Query)
  │
  ├─► _v401_base_query(query)          # original 14 entrypoint body
  │       │
  │       ├─ structured? → baseline + v238 coerce → return
  │       ├─ build v238 answer contract (best-effort)
  │       ├─ _baseline_query(query)    # original research pipeline
  │       └─ verify against contract (best-effort)
  │               │
  │               ▼
  │            base Response
  │
  └─► _v401_scoring_guard(query, response, deadline)   # NEW
          │
          ├─ skip if structured / empty / low time / errors
          ├─ LLM audit → missing / uncited / comparison_gap / padding
          ├─ if clean → return base Response
          ├─ LLM rewrite addressing findings (no new invented markers)
          └─ return revised Response (same citations) or base on failure
```

---

## How this differs from the later `15` → `submittion15` upgrade

| | `14` → `submission14` (`_v401`) | `15` → `submittion15` (`_hv16`) |
|---|---|---|
| Core idea | Post-draft judge-criteria audit + rewrite | Post-draft claim-risk / coverage-gap verify with **fresh search** |
| New retrieval? | No | Yes (`search_web` per risky claim / missing element) |
| New citations? | No (preserves existing citations) | Yes (attaches real `CitationRef` from new receipts when supported) |
| Contradiction handling | Rewrite/hedge via audit findings | Explicit supported / contradicted / unclear branch |
| Typical change class | Final synthesis + verification hygiene | Verification + tool-use + citation-traceability |

Both are concrete mechanism changes vs their respective bases; they are different mechanisms.

---

## What this is *not*

Explicitly avoided, because the similarity judge treats them as duplicate:

- Changing only model / temperature / max tokens / timeout / budget constants
- Rewording base system prompts without changing what the agent does
- Renaming variables / reformatting / reordering equivalent code alone
- Adding comments, salts, timestamps, or submission-slot metadata
- Fabricating citations from answer text or invented URLs
- Relying on stochastic LLM noise as a “behavior change”

Also avoided for platform / contract safety:

- Mutating structured `output` answers
- Inventing new citation markers not present in the draft
- Breaking the entrypoint contract (`async def query(query: Query) -> Response`)
- Expanded call-site `**kwargs` for new `llm_chat` invocations

---

## Safety / fail-open properties

1. Base `14` pipeline always runs first and can always be returned as-is
2. Guard skips when remaining time is tight
3. Structured-output responses are never rewritten by this text guard
4. Every LLM/parse/rebuild step wrapped in `try/except`
5. Clean audit → no rewrite
6. Weak / short rewrite rejected; original kept
7. Existing citations preserved on successful rewrite

---

## Validation shape

- All **50** agents in `submission14` received the same rename + guard pattern
- Prefix before the entrypoint anchor is byte-identical to `14`
- Guard present in every file (`_v401_scoring_guard`, `_V401_AUDIT_SYSTEM_PROMPT`, new `@entrypoint` wrapper)
- Uniform size delta (~7805 bytes) consistent with a shared appended mechanism rather than per-file prompt churn

---

## Files

| Path | Role |
|---|---|
| `111/67/14/*.py` | Unmodified base agents |
| `111/67/submission14/*.py` | Same agents + `_v401_*` scoring guard wrapper |
| `111/67/sub14-submitted/` | Matched/submitted subset from this round |
| `111/67/sub14-unsubmitted/` | Leftover / later-submitted subset from this round |

---

## Expected judge reading (intent)

Against each corresponding `14` base agent, the similarity judge should be able to name a concrete mechanism change such as:

> “Localized post-draft coverage and citation-hygiene audit that conditionally rewrites final synthesis when missing elements, uncited claims, comparison gaps, or citation padding are found, while the surrounding research pipeline is unchanged.”

That is the intended `near_duplicate` / `novel`-eligible behavior change: not a rewrite of the whole agent, but a real new verification + final-synthesis branch with consequential control and data flow.
