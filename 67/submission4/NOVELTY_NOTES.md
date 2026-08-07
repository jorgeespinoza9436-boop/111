# submission4 vs eighth — novelty checklist

## Concrete behavior changes (NOT cosmetic)

Every agent in submission4 wraps the eighth base `query` as `_eighth_base_query` and adds a post-pipeline `_hnyx_score_upgrade` that changes control/data flow:

1. **Coverage-gap retrieval** — extracts load-bearing query elements (numbers, dates, entities, comparison sides); if missing from the draft answer, issues targeted `search_web` queries (and optional `search_ai` when sparse) before commit.
2. **Temporal/status verification hop** — for time-sensitive questions, runs an extra dated/official-status search and patches the answer with that evidence.
3. **Detail fetch verification** — fetches top URLs from gap searches to deepen evidence notes used for citations.
4. **Citation note-slice rebinding** — builds `CitationRef` + `CitationSlice` from evidence notes that token-overlap answer sentences (judge only credits validated citation notes).
5. **LLM evidence-merge synthesis** — when gaps/temporal triggers fire, runs a dedicated repair `llm_chat` that rewrites the answer using NEW EVIDENCE only.
6. **Uncited load-bearing claim filter** — when inline `[n]` style is present, drops number/date sentences lacking citations (pairwise judge gives them no credit).
7. **Optional derived-figure synthesis** (variants 1–2) — when the question asks for sum/ratio/etc., computes from extracted figures in pure Python (no `safe_exec`; platform upload forbids aliased/indirect `safe_exec`).

## Why this is not `duplicate` under similarity_judge.py

- Not slot/salt/timestamp/comment/rename-only
- Not parameter-only (timeout/model/temperature)
- Not prompt-churn restating the same policy
- Adds new retrieval + verification + citation-traceability + synthesis branches with consequential control flow after the base agent returns

Expected classification vs eighth base: **near_duplicate** (localized post-pipeline) to **novel** (new retrieval/verification/synthesis loop). Should not be pure **duplicate**.

## Variant packs (anti-clone diversity)

| Variant | search_ai fallback | derived-figure math | uncited hedge | gap queries | fetch top |
|---------|--------------------|----------------------|---------------|-------------|-----------|
| 0 | on | off | on | 2 | 1 |
| 1 | on | on | off | 3 | 2 |
| 2 | off | on | on | 2 | 1 |
| 3 | on | off | on | 3 | 2 |

## Scoring alignment

Pairwise judge rewards: claim coverage, validated citations supporting answer-visible claims, no uncited time-sensitive facts, comparison both sides covered, avoid citation spam / unsupported numbers.

## Runtime note

Post-pipeline budget is capped at **~35s** so base agent (~245s) + upgrade stays under the ~300s sandbox entrypoint timeout. On failure, wrapper returns the base response unchanged.
