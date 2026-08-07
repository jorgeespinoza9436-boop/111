# improving16 — `111/67/16` → `111/67/submittion16`

## Scope

- **Source:** 46 miner agents in `111/67/16`
- **Output:** 46 improved agents in `111/67/submittion16`
- **Method:** Same per-file architecture preserved; one new post-pipeline mechanism appended to every agent.

Each baseline agent’s original `query()` logic was renamed to `_s16_base_query()` and left unchanged. A new `query()` entrypoint runs the baseline, then runs a bounded verification pass on the result.

## Goal

1. **Higher pairwise score** on SN67 miner tasks (claim-level factual correctness + citation traceability).
2. **Pass similarity / duplicate checks** relative to the corresponding `111/67/16` baseline — not via cosmetic churn, but via a concrete new control-flow branch (independent retrieval → audit → conditional rewrite / citation reinforcement).

## Mechanism: independent fresh-evidence verification pass

After `_s16_base_query()` returns a text `Response`, `_s16_finalize()` may run:

### 1. Fresh retrieval (new tool use)

- Issues its **own** `search_web` call on the user question (up to 4 snippets).
- Tries `parallel`, then `desearch` if needed.
- This evidence is **independent** of whatever the base pipeline already searched, fetched, and consumed internally.

### 2. Tools-off audit (new verification branch)

- Auditor model (`deepseek/deepseek-v3.2` via `openrouter`) classifies the draft against **only** the fresh snippets:
  - `contradicted` — fresh evidence directly conflicts on a query-required fact (name, date, figure, status, outcome).
  - `corroborated` — fresh evidence directly supports a concrete claim already in the draft.
  - `inconclusive` — neither clear conflict nor direct support.

### 3. Conditional outcomes (new synthesis / citation behavior)

| Verdict | Behavior |
|--------|----------|
| **contradicted** | Tools-off rewrite grounded in fresh evidence; answer text updated; new `CitationRef` from the fresh search attached (real `receipt_id` / `result_id`, never fabricated). |
| **corroborated** | Answer text unchanged; up to 3 new distinct `CitationRef` entries added from corroborating snippet indices. |
| **inconclusive** | No text change; only exact duplicate-citation cleanup. |

### 4. Safety / fallback (strict no-op)

- Skipped if response has no `text` (structured `output` only).
- Skipped if elapsed wall time ≥ **258s** (hard budget gate).
- Otherwise bounded to **6–18s** via `asyncio.wait_for`.
- Any search failure, LLM failure, JSON parse failure, or timeout → return baseline response (after cheap dedup only).
- Citation caps: max **3** new refs per pass, **60** total citations on the response.

## Why this targets scoring

Aligned with `miner_task_scoring.py` pairwise judge behavior:

- Only **hydrated `validated_citations`** count as evidence; inline bracket labels in answer text are untrusted.
- Judges reward **claim-by-claim** support and penalize unsupported time-sensitive facts.
- Added citations are real tool receipts from this pass (with slice windows on snippet text), not decorative URL lists in prose.

Aligned with `miner_task_generation.py` task shapes:

- Tasks favor **multi-source synthesis**, reconciliation, and current facts that need retrieval.
- A second independent evidence check reduces stale/wrong facts and strengthens traceability on comparison and status queries.

## Why this should not be flagged duplicate vs `111/67/16`

Per `similarity_judge.py` rubric:

- **Not duplicate:** no baseline agent had this post-draft independent-search + verdict-gated rewrite/citation branch.
- **Novel mechanism:** changes tool use, verification control flow, fallback policy, and citation provenance after the main pipeline.
- **Not prompt churn:** baseline prompts, models, timeouts, and core loop logic were not edited.
- **Not parameter-only:** the diff adds a new retrieval step and conditional rewrite path, not just temperature/token tweaks.

## Implementation notes

- All new symbols are prefixed `_s16_` / `_S16_` to avoid colliding with baseline code.
- `llm_chat(...)` calls use **explicit keyword arguments** (no `**kwargs` expansion) for platform AST / submit compatibility.
- Duplicate citations are removed by `(receipt_id, result_id, slices)` key before merge.

## Validation

- `py_compile` passed on all 46 `submittion16` files.
- Import/load test passed on all 46 (with entrypoint registry cleared between files).
- Mocked end-to-end checks: corroborated citation add, contradiction rewrite, inconclusive no-op, tool failure fallback, over-budget skip, structured-output no-op.

## Per-agent structure (every file)

```text
... original agent code unchanged ...

async def _s16_base_query(query: Query) -> Response:
    ... was @entrypoint("query") ...

# submittion16 MECHANISM block (~320 lines)
async def _s16_finalize(...)
@entrypoint("query")
async def query(query: Query) -> Response:
    _s16_resp = await _s16_base_query(query)
    return await _s16_finalize(query, _s16_resp, t0)
```
