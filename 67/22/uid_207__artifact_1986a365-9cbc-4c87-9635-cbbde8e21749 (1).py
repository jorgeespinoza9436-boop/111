from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import time
from dataclasses import dataclass, replace
from typing import Any

from harnyx_miner_sdk.api import embed_text, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.llm import LlmMessage
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

SEARCH_PROVIDER = "parallel"
SEARCH_TIMEOUT = 10.0
FETCH_TIMEOUT = 15.0
LLM_TIMEOUT = 90.0
# Slack that lets asyncio cut a call off when llm_chat fails to time out on its own.
# Keep it narrow: a large value would overshoot the ceiling _deadline_timeout computes.
GPT_OSS_MAX_OUTPUT_TOKENS = 65_536
VFS_SEARCH_PAGE_CHARS = 60_000
VFS_SIMILARITY_MIN_CHUNKS = 3
LLM_TIMEOUT_LOCAL_SLACK_SECONDS = 10.0
VFS_READ_PAGE_CHARS = 80_000
VFS_SIMILARITY_MAX_CHUNKS = 5
EMBEDDING_TIMEOUT = 120.0
EMBEDDING_MODEL = "qwen/qwen3-embedding-8b"
# Minimum embedding timeout. vfs_search issues two sequential embed_text calls, so
# an unnarrowed pair could spend 240s on its own and overrun the 300s hard wall
# without a single model turn. Both calls are narrowed to the time actually left
# and given a local asyncio ceiling; the floor keeps a late call from being handed
# a zero or negative budget that would only fail immediately.
EMBEDDING_TIMEOUT_FLOOR_SECONDS = 15.0
DEADLINE_NOTICE_SECONDS = 150.0
BATCHED_RETRIEVAL_PREVIEW_CHARS = 240_000
FOCUSED_OBSERVATION_MEMORY_CHARS = VFS_READ_PAGE_CHARS
GLM5_MAX_OUTPUT_TOKENS = 131_072
CHUTES_GEMMA_MAX_OUTPUT_TOKENS = 32_768
VFS_SIMILARITY_RESULT_CHARS = 45_000
VFS_LEXICAL_WINDOW_CHARS = 3_600
VFS_LEXICAL_WINDOW_COUNT = 3
OPENROUTER_GEMMA_MAX_OUTPUT_TOKENS = 40_960
# Spend governor thresholds, expressed as a fraction of the session hard limit.
# 0.14/0.20 were derived from the measured per-run cost distribution
# ($0.070/$0.100 against a $0.50 hard limit).
SPEND_GOVERNOR_SOFT_FRACTION = 0.14
SPEND_GOVERNOR_HARD_FRACTION = 0.20
SPEND_GOVERNOR_FALLBACK_LIMIT_USD = 0.50
# Closing turns granted to the model once the governor engages. Past this the
# harness finishes the task itself.
SPEND_GOVERNOR_MAX_CLOSING_TURNS = 3
# Time thresholds. The hard wall is 300s and exceeding it scores the task zero.
# Measured over 150 runs at 210: 20 runs passed 200s, with a maximum of 294.9s
# (only 5s of headroom).
#
# Why these values: an A/B run tightened to 130/190 cut total time by only 0.4%
# (610,546 vs 613,134ms) while the score sample dropped. Most runs finish inside
# 130s anyway, and the remaining variance is dominated by validator-to-validator
# noise (1.95x median, 4.9x maximum on the same task). Do not pay score for an
# unevidenced gain. 150/210 still covers the tail 210 actually exhibited (294.9s
# maximum), and leaves 90s after 'hard' for one final-answer LLM call plus
# citation assembly.
TIME_GOVERNOR_SOFT_SECONDS = 150.0
TIME_GOVERNOR_HARD_SECONDS = 210.0
# Absolute wall. soft/hard can be downgraded back to "open" when no evidence has
# been gathered or the closing turns are spent, but this threshold is never
# overridden for any reason. Crossing the 300s hard wall scores the task zero, so
# the harness force-closes while reserving one final-answer LLM call plus
# citation assembly.
TIME_GOVERNOR_ABSOLUTE_SECONDS = 225.0
# Worst-case tail arithmetic (against the 300s hard wall):
#   investigation turn starts at 224s -> 15s timeout, 25s local ceiling -> ends 249s
#   final answer                      -> 25s timeout, 35s local ceiling -> ends 284s
#   citation assembly is pure computation, effectively 0s      -> 16s of margin
# The measured maximum was 294.9s, so that margin is genuinely needed.
TIME_GOVERNOR_RESERVE_SECONDS = 45.0
# Minimum timeout for an investigation-loop turn. Zero or negative would only
# produce an immediate failure on every retry.
LOOP_TIMEOUT_FLOOR_SECONDS = 15.0
# Minimum timeout for the final answer and the audit; both may run past the
# absolute wall.
CLOSING_TIMEOUT_FLOOR_SECONDS = 25.0
# Ceiling on audit CONTINUE round trips. Past it the audit is treated as READY
# and the task closes.
MAX_AUDIT_CONTINUE_ROUNDS = 2
# Ceiling on consecutive whole-ladder failures. Past it, raise rather than retry
# forever.
MAX_CONSECUTIVE_MODEL_FAILURES = 3
CLOSING_TOOL_NAMES = ("update_research_state", "retain_evidence", "ready_to_finalize")

MODEL_SCHEDULING = "state_aware"
# Ladder order is identical to the original; only the final rung
# (openrouter_gemma_open) was appended. Scheduling is sequential, so a later rung
# is never called once an earlier one succeeds. Model selection and performance on
# the normal path are therefore unchanged, and the unpinned openrouter rung only
# rescues the task when every earlier rung is dead.
INVESTIGATION_MODELS = (
    "openrouter_gemma",
    "chutes_gemma",
    "glm5",
    "openrouter_gemma_open",
)
STATE_AWARE_INVESTIGATION_MODELS = (
    "openrouter_gemma",
    "chutes_gemma",
    "glm5",
    "openrouter_gemma_open",
)
REQUIREMENTS_MODELS = (
    "openrouter_gemma",
    "chutes_gemma",
    "glm5",
    "openrouter_gemma_open",
)
REPAIR_MODELS = (
    "openrouter_gemma",
    "chutes_gemma",
    "glm5",
    "openrouter_gemma_open",
)
AUDIT_MODELS = (
    "openrouter_gemma",
    "chutes_gemma",
    "glm5",
    "openrouter_gemma_open",
)
PROSE_MODELS = (
    "openrouter_gemma",
    "chutes_gemma",
    "glm5",
    "openrouter_gemma_open",
)
EVIDENCE_REVIEW_MODELS = INVESTIGATION_MODELS
# Rungs tried after the first expected-answer attempt fails. Previously this was an
# inline ("chutes_gemma", "glm5") pair that omitted the unpinned final rung every
# other ladder carries, so a provider-pin outage could take out hypothesis
# generation while investigation itself would have survived it.
EXPECTED_ANSWER_FALLBACK_MODELS = (
    "chutes_gemma",
    "glm5",
    "openrouter_gemma_open",
)
EMBEDDING_EXTRA = {
    "provider": {
        "only": ["nebius", "deepinfra", "siliconflow"],
        "allow_fallbacks": True,
    }
}
OPENROUTER_GLM_PROVIDER_PREFERENCES = {
    "provider": {
        "only": ["amazon-bedrock"],
        "allow_fallbacks": True,
    }
}
OPENROUTER_GPT_PROVIDER_PREFERENCES = {
    "provider": {
        "only": ["cerebras", "baseten", "deepinfra", "sambanova", "nebius", "coreweave"],
        "allow_fallbacks": True,
    }
}
OPENROUTER_GEMMA_PROVIDER_PREFERENCES = {
    "provider": {
        "only": ["modelrun", "sambanova"],
        "allow_fallbacks": True,
    }
}
OPENROUTER_GEMMA_STABLE_PROVIDER_PREFERENCES = {
    "provider": {
        "only": ["modelrun"],
        "allow_fallbacks": False,
    }
}
EXPECTED_ANSWER_SYSTEM = """\
You are beginning a deep-research task. Before using external sources, write the best expected answer your internal
knowledge suggests. This is a revisable research hypothesis, not evidence.

Write a concise working hypothesis that names the likely answer and the main uncertainty. Also state the smallest
verification route: the finite candidate inventory, if one is needed, and the exact external facts that would prove
or disprove the hypothesis. Name useful sources or pages, but do not produce or guess URLs; retrieval discovers exact
URLs. This route is a heuristic for investigation, not evidence. For an exhaustive question, put the inventory source
before per-candidate metric lookups. Be concrete enough that later investigation can prove, revise, or reject the
answer. Do not invent citations and do not avoid an answer merely because important facts remain uncertain."""

REQUIREMENTS_INSTRUCTION = """\
Before retrieval, call set_evidence_requirements once. Write one evidence question per line, leaving its answer blank.
Each question must ask for an externally verifiable premise that the final answer needs. Do not write a search plan,
source description, table schema, or list of raw data to collect. No external evidence exists yet: never insert a
candidate, number, list member, answer, expected value, or proposition that the original question does not supply.

Do not list arithmetic, set intersection, decade membership, threshold comparison, sorting, or another conclusion
that can be mechanically derived from externally supported operands as a separate evidence question. Ask for the
external operands that the derivation requires. The derivation itself does not require an external source.

Split a person's role, relationship, date, and each required property of an institution into separate questions. Treat
wording and named items supplied by the question as given. A person's role at an institution, the institution's type
or status, and its location are separate evidence questions. For an exhaustive result, ask for the external operands
needed to establish the complete result, but prefer questions that return a complete filtered set over questions that
request every raw value for every candidate. For an intersection of conditions, ask first for the complete result of
the most selective condition, then ask the remaining conditions only about candidates that survive earlier filters.
Those later questions may be conditional and must not guess who the survivors are. Do not create a separate question
asking whether a source or set is complete; the final audit judges whether the observed source scope is sufficient.
When the original question explicitly requires retrieval from a named source, edition, page, report, or dataset, that
source and scope remain a required premise even if another filter could establish the same conclusion.
An identification question does not assert uniqueness: the phrase "the person" is grammatical, not an exhaustive
condition. Unless the question explicitly says only, unique, all, every, asks how many, or otherwise requires an
exhaustive result, never require proof that no other person matches. Do not require every value for every nonqualifying
candidate; a candidate may be eliminated by one supported condition and only surviving candidates need the remaining
checks.

Bad requirement: "North Carolina had fatalities from Hurricane Nicole."
Good requirement: "Which states had direct or indirect fatalities across the named 2022 storms?"
Good requirement: "Which states had direct or indirect fatalities across the named 2023 storms?"
Bad for "Identify the person who has A and B": "Exactly one person satisfies A and B."
Good: "Which identified person has A?" and "Which identified person has B?" """

REQUIREMENTS_SYSTEM = (
    """\
Define the unanswered evidence questions that a complete answer to the original question must resolve. Base them only
on the original question; no expected answer or candidate hypothesis is available.

"""
    + REQUIREMENTS_INSTRUCTION
)

INVESTIGATION_SYSTEM = """\
You are a deep-research agent. Develop a claim that answers the original question and give it enough externally
inspectable support to persuade a skeptical reader.

The expected answer is a useful guess, not evidence. Use it to choose cheap, focused searches. Revise or replace it
when observed sources disagree, reveal a better answer, or expose a missing condition. Internal knowledge may guide
research, but every material external premise in the final claim needs observed support.
When the question attributes facts to a named source, edition, page, report, or dataset, inspect that named source
before accepting a substitute. Otherwise prefer the organization that produced the fact, an official record, or a
primary document over an aggregator or commentary. Begin retrieval with the named or primary source and the exact
subject; use secondary sources for discovery only when the direct source cannot yet be found. If the publisher page
is unavailable, prefer an archived copy of that exact page over a third-party reproduction.
Do not finalize from a secondary source when the observed search results already contain an accessible official or
primary source for the same decisive premise. Inspect the direct source first; retain the secondary source only when
the direct source still lacks the necessary text or scope after inspection.
If a clue-only search does not improve the evidence, do not paraphrase and repeat it. Change the evidence route or
test the expected-answer candidate directly.
If a required source's search surface does not expose a complete inventory, use a suitable secondary source to
discover a finite candidate set, then verify each surviving candidate against the required source. A discovery source
is a research aid, not final support for a premise the question explicitly attributes to the required source.
For an exhaustive question, the expected candidate pool remains unproved. Before finalizing, inspect either a source
that enumerates the pool or direct evidence for every candidate and plausible boundary case; metric pages for guessed
candidates alone do not prove that no candidate is missing.
When a table explicitly ranks rows in descending order by the same numeric metric used by the question's threshold,
you do not need every later row after the first below-threshold row. Retain the header, every row through that boundary,
and explain why the established ordering eliminates the remaining lower-ranked rows. This shortcut is valid only when
the visible header and row order establish that monotonic relationship.

Search snippets are evidence when their visible text directly supports the premise. If later retrieval steps must
combine that snippet with other facts, retain its smallest decisive lines before moving on; otherwise the full snippet
may leave active context while remaining available in VFS. Among observed sources with comparable authority and scope,
preserve the excerpt that states the complete needed premise most directly and compactly. Do not fetch a broader copy
merely to replace a sufficient snippet. A search result from the named official page counts as inspection when its
visible text supplies the needed fact; retain that snippet rather than fetching the same page solely because the
question names it. Use fetch_page only when the snippet lacks necessary context or when inspecting a discovered page
is the most direct remaining evidence route. fetch_page accepts a full URL, including one discovered inside a search
result or another page. Do not construct a URL from a guessed site pattern.
Search and fetch results are saved in VFS. On a long page, locate relevant lines with VFS search before using VFS read
to expand a small window. A large fetch includes question-ranked context windows in addition to its head/middle/tail
preview; inspect those windows before searching the page again. Give each VFS search both an exact regex pattern and
a semantic query. The harness starts with regex and automatically adds embedding results only when regex fails or
finds nothing. For a table, keep the relevant row together with its title, series labels, year labels, and headers.
PDF extraction can place chart values before the heading or labels they belong to. When a title match lacks its data,
inspect both before and after it rather than assuming the table follows the title. You may reconstruct a flattened
chart only when the excerpt exposes a complete rectangle: N ordered category labels, M series labels, and exactly M
groups of N data values after excluding axis ticks. State that mapping explicitly and cross-check it against the page
heading, totals, shares, or nearby prose. If the complete structure is not visible, do not infer a cell from line order.
When the question asks about a specific date, edition, or historical version, inspect a result whose title and scope
match that exact period before broader or current-data pages. Do not revise a period-specific value from a source that
visibly describes a different period. A current rolling statistical table may revise rows labeled with past dates;
when the question concerns what was reported for that period, prefer the contemporaneous archived release.
When inspected sources disagree, resolve the conflict by source scope, authority, date, and fit to the question. If
one source states the question's identifying conditions and requested value together, preserve that internally
consistent account. A differently scoped or measured value is a limitation to disclose, not a reason to repeat
substantially equivalent searches. Once further searches only reproduce the same conflict, finalize the best-supported
answer and state the discrepancy briefly.
The initial evidence questions guide retrieval; they are not a checklist that must remain material. A complete filter
or supported elimination can make a broader question unnecessary. An explicit instruction in the original question
to retrieve or report from a named source, edition, page, report, or dataset remains material and cannot be replaced
by a different proof route. Before finalizing, check every premise that the current answer and its derivation actually
depend on against words or table cells visible in the supplied source records. Your memory of a source is not visible
evidence. If a material row or relationship is absent from the excerpt, locate it with VFS search or fetch the
discovered page; if it remains unavailable, state the limitation instead of silently supplying it.

Use update_research_state whenever evidence changes the current best answer, the decisive support, or the most
important unresolved question. This prose state is your working memory and is returned on every turn. Do not turn it
into a search log. Retain only displayed lines that directly support or contradict a material premise; do not retain a
source merely for possible later extraction. For a flattened table or chart, retain one continuous range containing
the data values, ordered category labels, series labels, and title together, even when axis ticks or spacing lie
between them. Isolated number lines plus a separate title do not preserve the mapping needed to support table claims.
For a descending ranked table filtered by a numeric threshold, retain one continuous range from the header through
the first below-threshold row so the qualifying rows and the exhaustive cutoff remain inspectable together.

Continue while a real uncertainty could change the answer. Before finalizing with evidence from a fetched page,
preserve every decisive excerpt with retain_evidence. When the claim resolves the question and its material premises
are supported, call ready_to_finalize as the final tool in the response. Its reason explains the derivation and cites
source references such as [P1] or [S1.2], without encoding line ranges in prose. The harness writes the answer from
the cited source records. A decisive search snippet may be cited without retention only when finalizing immediately;
retain it before performing later retrieval that must be combined with it.

Tool failures are observations: correct the call or change approach. Tool calls in one response execute sequentially,
so a later call must not depend on a result not yet seen. When exact arguments for several independent fetches, reads,
or evidence retentions over an already known finite candidate set are available, emit them together in one response.
Do not batch alternative searches for the same uncertainty: run one search and inspect its results before trying
another evidence route. Emit each distinct operation at most once per response."""

ANSWER_UPDATE_SYSTEM = """\
Write the complete best current answer to the original question as polished, reader-facing Markdown. Obey any
explicit output-only or formatting constraint in the original question; otherwise use substantial prose with
structure proportional to the answer. The expected answer, prior answer, investigator prose, and your internal
knowledge are not evidence. Use only the supplied source records.

The investigator's current conclusion is the intended answer and derivation after research. Use it to revise the
prior answer, while checking every external premise against the supplied source records. Do not add factual claims
that are unnecessary to establish the answer; for an excluded candidate, state its decisive failing condition rather
than unrelated background.

Open with the direct conclusion. Use short descriptive headings when they help navigation, bullets for parallel
findings, and a Markdown table when several candidates share the same comparison fields. Do not force a heading or
table onto a short answer. Keep paragraphs focused and make the decisive comparison easy to scan. Do not add a
references section, bibliography, source dump, raw URL, or quoted evidence appendix.

Resolve the question directly, explain why the conclusion follows, and preserve relevant uncertainty. Place the
exact internal source reference from the supplied record, such as [S1.2] or [P3], immediately after the factual claim
it supports. These references are private placeholders that the harness converts to public citation numbers. Never
invent a reference, alter its spelling, or write a numeric citation marker yourself. A derived claim needs no separate
reference when all external operands are visibly supported nearby and the derivation is explicit. Name a source
organization naturally only when it helps explain why the evidence is authoritative. A table-derived value is
supported only when the supplied text preserves its association with the relevant row and column labels. Never assign
a value to a year, category, or candidate that the source record does not visibly associate with that value. A
csv_records field is a mechanical projection of a CSV header onto its selected rows; prefer its named fields over
counting positions in the raw CSV quote. For each premise, rely on the single most direct source that visibly
establishes it. Add another source only when the first source cannot establish the whole premise; do not rely on weaker
duplicates or merely corroborating background. When sources report conflicting measurements, prefer an internally
consistent source record that establishes the question's identifying conditions and requested value together. Do not
combine a conflicting measurement from one source with the answer supplied by another; mention a material discrepancy
briefly only when it affects interpretation. If the question asks what a source explicitly reports, state that
reported value and compare it directly; do not add a recomputation that answers a different question. When a
threshold, ranking, ratio, or arithmetic operation decides the answer, show the relevant input
values and write the arithmetic expression or comparison for every candidate needed to establish the result (for
example, `105 - 81 = 24`, not only the two scores and the resulting margin). Prefer an exact calculated value over an
indirect inequality when the supplied operands allow the calculation. When the conclusion is
exhaustive (for example, only, all, closest, a top-k set, or an intersection), show enough of the candidate comparison
in the answer to establish that no omitted candidate changes the result. Open with the direct answer, then explain the
decisive evidence and derivation in natural prose. Do not expose research-process labels such as candidate pool,
boundary check, proof of completeness, evidence requirement, audit, or research state. For an exhaustive answer,
identify the finite set naturally, show each qualifying entity's decisive values, and mention only the near misses
needed to establish the boundary. An inventory source can bound the set, but independently verified candidate pages
and boundary near misses can do so when no single inventory page is available. Apply strict inequalities literally:
state the strictly qualifying set first, and describe an equal boundary value only as an excluded case. For an
identification or constraint question, explicitly show how the answer satisfies every condition in the original
question, including descriptors and relationships. When the question asks to retrieve a finite set and then filter
it through multiple conditions, show the materially narrowed set after each decisive filter, not only the final
candidate's properties.

Good citation placement: `Essendon won 105-81 in 1984. [P1]`
For a Markdown table, place the source reference in each source-backed row, normally in its final relevant cell. Never
put the only reference for several table rows on a separate line below the table.
Bad: a final `Sources` list, a raw URL, an invented `[1]`, a citation-only line below a table, or a claim whose only
reference appears several paragraphs later."""

STRUCTURED_OUTPUT_SYSTEM = """\
Materialize a completed, evidence-backed research answer as the caller's structured output. Do not research again,
add facts, explain your process, or return prose outside the tool call. Preserve the answer's meaning and include every
field required by the supplied JSON Schema. Call submit_structured_output exactly once. The tool arguments are the
final output value, not JSON encoded inside a string."""

AUDIT_SYSTEM = """\
Audit an answer against supplied external evidence. The answer may contain the correct values attached to the wrong
dates, columns, categories, candidates, or relationships.

Reconstruct the source facts before accepting any claim from the answer. A value has a year, column, category, or role
only when the visible source text preserves that association. Do not infer a table header across omitted lines or from
the answer itself. A csv_records field is a mechanical projection of a CSV header onto its selected rows; use its named
fields instead of counting positions in the raw CSV quote. For every candidate that could affect the result, treat each
condition in the question as supported true, supported false, or unknown. Absence of evidence is unknown, not false.

For an identification question, audit every descriptive clause as a separate premise. Evidence that a person is
affiliated with an institution does not establish the institution's location, type, or status. If the supplied source
records do not explicitly establish such a property required by the question, mark it unknown and return CONTINUE.
When the question identifies an entity indirectly through a quotation, work, event, or relationship, the mapping
from that clue to the identified person or entity is itself a material premise. Require visible evidence for that
mapping even when it is familiar or stated as part of the question; evidence for the resulting name alone does not
establish why it matches the clue.
When the original question explicitly requires retrieval or reporting from a named source, edition, page, report, or
dataset, verify that the supplied records establish that source and scope. A substitute source does not satisfy that
instruction even when it supports the same conclusion. The source inventory is discovery metadata, not evidence. If
the answer relies on a substitute while the inventory exposes a result from the required publisher with matching
scope, return CONTINUE and name that one direct result for inspection. Do not request a stronger duplicate merely
because one may exist when the question does not require a named source or scope.

Source omission proves absence only when the source visibly represents a complete inventory at the required scope.
A candidate excluded by one supported condition does not need evidence for the other conditions. When a surviving
candidate has multiple unknown conditions, request only the single cheapest observation that could exclude it or move
it forward; do not mark later conditions missing until the candidate survives that check. A CONTINUE audit must
contain exactly one MISSING line, and it must match the one observation named in the verdict.
Rows separated by a visible `...` are not adjacent. Do not reconstruct ordinal ranks or a ranking cutoff by joining
the rows on either side; return CONTINUE if omitted rows could change the result.
A complete comparison on one condition may reduce the candidate set, after which only the survivors need support for
the remaining conditions. Do not require a full candidate-by-condition matrix when supported elimination establishes
the same conclusion.
Do not combine an eligibility condition from one source with a requested value from another source when their
measurements conflict. If one supplied source record states all identifying conditions and the requested value
together, preserve that internally consistent account. Treat a differently scoped or measured record as a
discrepancy, not as an operand for a hybrid answer.
Never approve or write a replacement that keeps a candidate as the answer while its chosen evidence account makes
that candidate fail a selection condition. Use a supplied internally consistent account that establishes both
eligibility and the requested value, or return CONTINUE when no such account is available.

Before deciding, identify only:
- factual premises asserted by the current answer; and
- unresolved facts whose truth could change the answer to the original question.

Do not audit an initial research plan or require facts that are no longer material to the conclusion. Write one short
line for each material premise or result-changing unknown. Use exactly one of:
SUPPORTED [source ref]: <the visible source words that establish this premise>
DERIVED [source refs]: <the arithmetic or logical derivation from externally supported operands>
MISSING: <the premise not explicitly established by any supplied source record>
CONTRADICTED [source ref]: <the visible source words that contradict this premise>

Emit a MISSING line only for a real unresolved premise. If nothing is missing, omit MISSING entirely; never write
`MISSING: none`, `MISSING: not applicable`, or another empty placeholder. A READY verdict must contain no MISSING line.
Do not combine premises on one line. A source ref without the establishing words is not support. Use only the
supplied source records; the answer and internal knowledge are not evidence. A contradicted condition for an excluded
candidate can support the answer's exclusion; it is not itself an answer error. Arithmetic, set operations, decade
membership, threshold comparisons, and ordering may be DERIVED without another external citation when every external
operand is SUPPORTED. A DERIVED line must show the calculation or logical step and cite the source refs containing its
external operands; never use DERIVED to supply a missing external operand. A value that is completely calculable from
supported external operands is not missing merely because no source states the calculated value verbatim. Mark that
premise DERIVED, not MISSING, and do not emit both statuses for the same premise.
A familiar categorical property may also be DERIVED from explicit defining source facts when the classification is
unambiguous; show those facts instead of requiring the source to use the question's exact label.

After all premise lines, emit exactly one verdict:
VERDICT READY
VERDICT CONTINUE: <the one most important missing observation>
VERDICT REVISE
<a complete replacement answer with exact supplied source refs such as [P1]>

Use READY only if every factual statement agrees with the reconstructed source facts, the conclusion follows, and no
unknown could change the result. READY and REVISE are invalid if a material premise is MISSING. A source
contradiction to a factual statement asserted by the current answer requires REVISE, while a contradiction that
establishes why a candidate is excluded is compatible with READY. Use REVISE only when the supplied evidence settles
the question but the answer is wrong or unsupported. The replacement must cite exact supplied source refs after its
supported factual claims. Begin it with the corrected conclusion and do not repeat the old answer or discuss the
correction process. Use CONTINUE when the evidence cannot settle the result."""


def _schema(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(required),
                "additionalProperties": False,
            },
            "strict": False,
        },
    }


def _parse_csv_row(line: str) -> list[str] | None:
    fields: list[str] = []
    field: list[str] = []
    in_quotes = False
    after_quote = False
    index = 0
    while index < len(line):
        character = line[index]
        if in_quotes:
            if character != '"':
                field.append(character)
            elif index + 1 < len(line) and line[index + 1] == '"':
                field.append('"')
                index += 1
            else:
                in_quotes = False
                after_quote = True
        elif after_quote:
            if character == ",":
                fields.append("".join(field))
                field = []
                after_quote = False
            elif character not in " \t":
                return None
        elif character == ",":
            fields.append("".join(field))
            field = []
        elif character == '"' and not field:
            in_quotes = True
        else:
            field.append(character)
        index += 1
    if in_quotes:
        return None
    fields.append("".join(field))
    return fields


SET_EVIDENCE_REQUIREMENTS_TOOL = _schema(
    "set_evidence_requirements",
    "Record only unanswered evidence questions whose externally verifiable premises the final answer needs. "
    "Do not record source availability, table structure, or retrieval work.",
    {
        "requirements": {
            "type": "string",
            "minLength": 1,
            "description": "One unanswered evidence question per line, with no candidate or expected answer filled in.",
        }
    },
    ("requirements",),
)
REQUIREMENTS_TOOLS = [SET_EVIDENCE_REQUIREMENTS_TOOL]

SEARCH_WEB_TOOL = _schema(
    "search_web",
    "Search the web. Full results are retained in VFS and each result receives a source reference.",
    {
        "query": {"type": "string", "minLength": 1},
        "num": {"type": "integer", "minimum": 1, "maximum": 25},
    },
    ("query", "num"),
)
FETCH_PAGE_TOOL = _schema(
    "fetch_page",
    "Fetch one full URL when a search snippet lacks context or a page exposes a promising direct link. "
    "Full content is retained in VFS and receives a source reference.",
    {"url": {"type": "string", "minLength": 1}},
    ("url",),
)
VFS_READ_TOOL = _schema(
    "vfs_read",
    "Read an inclusive line range from one VFS key. Large ranges are paginated. Bounds accept 1-based line "
    "numbers or stable line IDs.",
    {
        "key": {"type": "string", "minLength": 1},
        "start_line": {"type": ["string", "integer", "null"]},
        "end_line": {"type": ["string", "integer", "null"]},
    },
    ("key", "start_line", "end_line"),
)
VFS_LIST_TOOL = _schema(
    "vfs_list",
    "List VFS keys, optionally restricted to a literal prefix.",
    {"prefix": {"type": "string"}},
    ("prefix",),
)
VFS_WRITE_TOOL = _schema(
    "vfs_write",
    "Write or overwrite one VFS file. VFS operations do not create VFS audit entries.",
    {
        "key": {"type": "string", "minLength": 1},
        "content": {"type": "string"},
    },
    ("key", "content"),
)
VFS_DELETE_TOOL = _schema(
    "vfs_delete",
    "Delete one VFS key.",
    {"key": {"type": "string", "minLength": 1}},
    ("key",),
)
VFS_SEARCH_TOOL = _schema(
    "vfs_search",
    "Search exact keys, wildcard key patterns such as page://*, or * for all VFS files. Supply an exact regex "
    "pattern and a semantic query for the same information need. The harness starts with regex and adds embedding "
    "results only when regex fails or finds nothing. Continue paginated regex matches with next_cursor.",
    {
        "pattern": {"type": "string", "minLength": 1},
        "query": {"type": "string", "minLength": 1},
        "targets": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "minItems": 1,
        },
        "cursor": {
            "type": "integer",
            "minimum": 0,
            "description": "Match offset returned as next_cursor by a previous identical search.",
        },
    },
    ("pattern", "query", "targets"),
)
UPDATE_RESEARCH_STATE_TOOL = _schema(
    "update_research_state",
    "Replace the prose working memory used on later turns. Call when the best answer, decisive support, "
    "or most important unresolved question changes.",
    {
        "state": {
            "type": "string",
            "minLength": 1,
            "description": "Current best answer, decisive observed source refs, and the next unresolved question.",
        }
    },
    ("state",),
)
READY_TO_FINALIZE_TOOL = _schema(
    "ready_to_finalize",
    "Propose or confirm finalization after decisive external evidence has been inspected. This is premature when "
    "an observed search result exposes an uninspected official or primary source for a premise currently supported "
    "only by a secondary source. Every cited fetched-page source must already have a retained evidence excerpt.",
    {
        "reason": {
            "type": "string",
            "minLength": 1,
            "description": "Explain readiness and cite decisive source refs such as [S1.2] or [P1].",
        }
    },
    ("reason",),
)

RETAIN_EVIDENCE_TOOL = _schema(
    "retain_evidence",
    "Keep one directly useful, already displayed source excerpt in persistent research memory. "
    "Do not retain a source merely for possible later extraction. For flattened tables, retain one continuous "
    "range that includes the values, category labels, series labels, and title rather than isolated numeric lines. "
    "Every date, year, threshold, or other number asserted in the note must also be visible in the selected range.",
    {
        "source": {
            "type": "string",
            "minLength": 1,
            "description": "An observed source reference such as S1.2 or P3, or its exact VFS key.",
        },
        "note": {
            "type": "string",
            "minLength": 1,
            "description": "What the visible source text establishes and which part of the question it informs.",
        },
        "start_line": {
            "type": ["string", "integer"],
            "description": "First displayed line number or stable line ID containing the evidence.",
        },
        "end_line": {
            "type": ["string", "integer"],
            "description": "Last displayed line number or stable line ID containing the evidence.",
        },
    },
    ("source", "note", "start_line", "end_line"),
)
DISCARD_REMAINING_SOURCES_TOOL = _schema(
    "discard_remaining_sources",
    "Discard every still-unretained source from the latest retrieval and finish its evidence review.",
    {
        "reason": {
            "type": "string",
            "minLength": 1,
            "description": "Why every still-unretained visible source does not materially inform the research.",
        }
    },
    ("reason",),
)
EVIDENCE_REVIEW_TOOLS = [RETAIN_EVIDENCE_TOOL, DISCARD_REMAINING_SOURCES_TOOL]
# Declared in final order rather than assembled by mutating a partially built list.
# The previous form appended retain_evidence with TOOLS.insert(-1, ...) after the
# fact, which made the tool order depend on statement order and would silently
# duplicate the entry if the module were ever imported twice.
TOOLS = [
    SEARCH_WEB_TOOL,
    FETCH_PAGE_TOOL,
    VFS_READ_TOOL,
    VFS_LIST_TOOL,
    VFS_WRITE_TOOL,
    VFS_DELETE_TOOL,
    VFS_SEARCH_TOOL,
    UPDATE_RESEARCH_STATE_TOOL,
    RETAIN_EVIDENCE_TOOL,
    READY_TO_FINALIZE_TOOL,
]
# The closing-only tool set left available once the governor engages.
CLOSING_TOOLS = [tool for tool in TOOLS if tool["function"]["name"] in CLOSING_TOOL_NAMES]


@dataclass
class Source:
    ref: str
    key: str
    title: str
    url: str
    content: str
    receipt_id: str | None
    result_id: str | None
    preview_chars: int = 8_000


@dataclass
class CitationPlan:
    citations: list[CitationRef]
    source_indices: dict[str, int]


class ResearchState:
    def __init__(self, question: str = "") -> None:
        self.question = question
        # Task start time. Held on per-query state rather than in a global so it can
        # never be mixed up with a concurrently running query. Nested calls
        # (_answer_text, _audit) use it to narrow their own timeouts to the time left.
        self.started_at = time.monotonic()
        self.vfs: dict[str, str] = {}
        self.sources: dict[str, Source] = {}
        self.line_locations: dict[str, tuple[str, int]] = {}
        self.focused_lines: dict[str, set[int]] = {}
        self.focused_line_order: dict[tuple[str, int], None] = {}
        self.focused_line_chars = 0
        self.reasoning_observations: list[str] = []
        self.reasoning_observation_chars = 0
        self.source_slices: dict[str, list[CitationSlice]] = {}
        self.retrieval_receipts: dict[str, dict[str, Any]] = {}
        self.retrieval_output_cache: dict[str, dict[str, Any]] = {}
        self.vfs_operation_receipts: dict[str, dict[str, Any]] = {}
        self.retained_evidence: dict[str, dict[str, Any]] = {}
        self.document_embeddings: dict[
            tuple[str, str],
            list[tuple[dict[str, Any], list[float]]],
        ] = {}
        self.review_source_refs: set[str] = set()
        self.evidence_requirements: str | None = None
        self.research_state = ""
        self.audit_gap = ""
        self.budget_snapshot: dict[str, float] | None = None
        self.search_count = 0
        self.page_count = 0

    @staticmethod
    def _line_id(key: str, index: int, text: str) -> str:
        digest = hashlib.sha256(f"{key}\0{index}\0{text}".encode()).hexdigest()[:10]
        return f"L{digest}"

    def render_lines(
        self,
        key: str,
        indices: list[int] | range | None = None,
    ) -> list[dict[str, Any]]:
        lines = self.vfs[key].splitlines() or [""]
        selected = range(len(lines)) if indices is None else indices
        output: list[dict[str, Any]] = []
        for index in selected:
            if index < 0 or index >= len(lines):
                continue
            line_id = self._line_id(key, index, lines[index])
            self.line_locations[line_id] = (key, index)
            output.append({"line_id": line_id, "line": index + 1, "text": lines[index]})
        return output

    def focused_excerpts(self) -> list[dict[str, Any]]:
        excerpts: list[dict[str, Any]] = []
        for key, indices in self.focused_lines.items():
            source_refs = [f"[{source.ref}]" for source in self.sources.values() if source.key == key]
            excerpts.append(
                {
                    "vfs_key": key,
                    "source_refs": source_refs,
                    "lines": self.render_lines(key, sorted(indices)),
                }
            )
        return excerpts

    def remember_focused_lines(self, key: str, indices: set[int] | range) -> None:
        lines = self.vfs[key].splitlines() or [""]
        valid_indices = sorted({index for index in indices if 0 <= index < len(lines)})
        focused = self.focused_lines.setdefault(key, set())
        for index in valid_indices:
            if index in focused:
                continue
            focused.add(index)
            location = (key, index)
            self.focused_line_order[location] = None
            self.focused_line_chars += len(lines[index]) + 80
        if not focused:
            self.focused_lines.pop(key, None)
        while (
            self.focused_line_chars > FOCUSED_OBSERVATION_MEMORY_CHARS
            and len(self.focused_line_order) > 1
        ):
            old_key, old_index = next(iter(self.focused_line_order))
            self.forget_focused_lines(old_key, {old_index})

    def forget_focused_lines(
        self,
        key: str,
        indices: set[int] | None = None,
    ) -> None:
        focused = self.focused_lines.get(key)
        if focused is None:
            return
        removed = set(focused if indices is None else focused & indices)
        lines = self.vfs.get(key, "").splitlines() or [""]
        for index in removed:
            self.focused_line_order.pop((key, index), None)
            if 0 <= index < len(lines):
                self.focused_line_chars -= len(lines[index]) + 80
        focused.difference_update(removed)
        if not focused:
            self.focused_lines.pop(key, None)
        self.focused_line_chars = max(0, self.focused_line_chars)

    def clear_focused_lines(self) -> None:
        for key in tuple(self.focused_lines):
            self.forget_focused_lines(key)

    def remember_reasoning_observation(self, reasoning: str | None) -> None:
        observation = str(reasoning or "").strip()
        if not observation or not re.search(r"\b(?:S\d+(?:\.\d+)?|P\d+)\b", observation):
            return
        if observation in self.reasoning_observations:
            return
        self.reasoning_observations.append(observation)
        self.reasoning_observation_chars += len(observation)
        while (
            self.reasoning_observation_chars > FOCUSED_OBSERVATION_MEMORY_CHARS
            and len(self.reasoning_observations) > 1
        ):
            removed = self.reasoning_observations.pop(0)
            self.reasoning_observation_chars -= len(removed)

    def pending_review_excerpts(self) -> list[dict[str, Any]]:
        excerpts: list[dict[str, Any]] = []
        for ref, source in self.sources.items():
            if ref not in self.review_source_refs:
                continue
            excerpts.append(
                {
                    "source_ref": f"[{ref}]",
                    "vfs_key": source.key,
                    "title": source.title,
                    "url": source.url,
                    "text": self.bounded_preview(
                        source.key,
                        max_serialized_chars=source.preview_chars,
                    ),
                }
            )
        return excerpts

    def preview(self, key: str, max_chars: int = 8_000) -> list[dict[str, Any]]:
        lines = self.vfs[key].splitlines() or [""]
        if len(self.vfs[key]) <= max_chars:
            return self.render_lines(key)
        budget = max_chars // 3
        groups: list[list[int]] = [[], [], []]
        positions = [range(len(lines)), range(len(lines) // 3, len(lines)), range(len(lines) - 1, -1, -1)]
        for group, position in zip(groups, positions, strict=True):
            used = 0
            for index in position:
                if used and used + len(lines[index]) + 1 > budget:
                    break
                group.append(index)
                used += len(lines[index]) + 1
            group.sort()
        selected = sorted(set(groups[0] + groups[1] + groups[2]))
        return self.render_lines(key, selected)

    def bounded_preview(
        self,
        key: str,
        max_serialized_chars: int,
    ) -> list[dict[str, Any]]:
        text_budget = max_serialized_chars
        preview: list[dict[str, Any]] = []
        for _attempt in range(4):
            preview = self.preview(key, max_chars=text_budget)
            serialized_chars = len(
                json.dumps(
                    preview,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
            if serialized_chars <= max_serialized_chars:
                return preview
            text_budget = max(
                100,
                int(text_budget * max_serialized_chars / serialized_chars * 0.9),
            )
        return preview

    def resolve_targets(self, targets: list[str]) -> list[str]:
        keys: list[str] = []
        for target in targets:
            if target == "*":
                matches = list(self.vfs)
            elif any(char in target for char in "*?["):
                pattern = re.compile("^" + re.escape(target).replace(r"\*", ".*").replace(r"\?", ".") + "$")
                matches = [key for key in self.vfs if pattern.fullmatch(key)]
            elif target in self.vfs:
                matches = [target]
            else:
                matches = []
            keys.extend(matches)
        return list(dict.fromkeys(keys))

    def citation_slices(self, key: str, indices: list[int] | range) -> list[CitationSlice]:
        content = self.vfs[key]
        lines = content.splitlines(keepends=True) or [content]
        selected = sorted({index for index in indices if 0 <= index < len(lines)})
        if not selected:
            return []

        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line))

        groups: list[tuple[int, int]] = []
        start = previous = selected[0]
        for index in selected[1:]:
            if index != previous + 1:
                groups.append((start, previous + 1))
                start = index
            previous = index
        groups.append((start, previous + 1))

        spans: list[tuple[int, int]] = []
        for start_line, end_line in groups:
            start_offset = offsets[start_line]
            end_offset = offsets[end_line]
            if end_offset - start_offset < 100 and len(content) >= 100:
                missing = 100 - (end_offset - start_offset)
                start_offset = max(0, start_offset - (missing // 2))
                end_offset = min(len(content), end_offset + missing)
                start_offset = max(0, end_offset - 100)
            if spans and start_offset <= spans[-1][1]:
                spans[-1] = (spans[-1][0], max(spans[-1][1], end_offset))
            else:
                spans.append((start_offset, end_offset))
        return [CitationSlice(start=start, end=end) for start, end in spans if end > start]

    def packet_preview(
        self,
        key: str,
        max_chars: int = 8_000,
    ) -> tuple[str, list[CitationSlice]]:
        content = self.vfs[key]
        if len(content) <= max_chars:
            return content, [CitationSlice(start=0, end=len(content))]

        segment_chars = max_chars // 3
        middle_start = max(0, (len(content) - segment_chars) // 2)
        spans = [
            (0, segment_chars),
            (middle_start, middle_start + segment_chars),
            (len(content) - segment_chars, len(content)),
        ]
        quote = "\n\n...\n\n".join(content[start:end] for start, end in spans)
        slices = [CitationSlice(start=start, end=end) for start, end in spans]
        return quote, slices

    @staticmethod
    def cited_line_indices(reason: str, ref: str) -> list[int]:
        escaped_ref = re.escape(ref)
        patterns = (
            rf"\[{escaped_ref}\s*,\s*lines?\s+(\d+)(?:\s*(?:-|to)\s*(\d+))?\]",
            rf"\[{escaped_ref}\s*,\s*L(\d+)(?:\s*-\s*L?(\d+))?\]",
            rf"\[{escaped_ref}\]\s*[:,]?\s*lines?\s+(\d+)(?:\s*(?:-|to)\s*(\d+))?",
            rf"\[{escaped_ref}\]\s*[:,]?\s*L(\d+)(?:\s*-\s*L?(\d+))?",
            rf"\b{escaped_ref}\b\s*[:,]?\s*lines?\s+(\d+)(?:\s*(?:-|to)\s*(\d+))?",
            rf"\b{escaped_ref}\b\s*[:,]?\s*L(\d+)(?:\s*-\s*L?(\d+))?",
        )
        indices: set[int] = set()
        for pattern in patterns:
            for match in re.finditer(pattern, reason, flags=re.IGNORECASE):
                start = int(match.group(1))
                end = int(match.group(2) or start)
                if end < start:
                    start, end = end, start
                indices.update(range(max(1, start) - 1, end))
        for bracket in re.findall(r"\[([^\]]+)\]", reason):
            if re.search(rf"(?:^|[\s,;]){escaped_ref}(?:$|[\s,;:])", bracket) is None:
                continue
            for match in re.finditer(
                r"\bL(\d+)(?:\s*-\s*L?(\d+))?",
                bracket,
                flags=re.IGNORECASE,
            ):
                start = int(match.group(1))
                end = int(match.group(2) or start)
                if end < start:
                    start, end = end, start
                indices.update(range(max(1, start) - 1, end))
        return sorted(indices)

    def source_evidence_indices(
        self,
        key: str,
        indices: list[int] | range | set[int],
        *,
        include_focused: bool = True,
    ) -> list[int]:
        lines = self.vfs[key].splitlines() or [""]
        line_count = len(lines)
        candidates = set(indices)
        if include_focused:
            candidates.update(self.focused_lines.get(key, set()))
        selected = {index for index in candidates if 0 <= index < line_count}
        for index in tuple(selected):
            context = _markdown_table_context(self, key, index)
            if context is None:
                continue
            selected.update(item["line"] - 1 for item in context["header"])
        if selected:
            header = _parse_csv_row(lines[0])
            selected_rows = [_parse_csv_row(lines[index]) for index in selected]
            if header is None or any(row is None for row in selected_rows):
                header = []
                selected_widths = set()
            else:
                selected_widths = {len(row) for row in selected_rows if row is not None}
            textual_fields = sum(bool(re.search(r"[A-Za-z]", field)) for field in header)
            if len(header) >= 3 and len(header) in selected_widths and textual_fields >= len(header) // 2:
                selected.add(0)
        return sorted(selected)

    def structured_csv_records(
        self,
        key: str,
        indices: list[int] | range,
    ) -> list[dict[str, str]]:
        lines = self.vfs[key].splitlines()
        if not lines or 0 not in indices:
            return []
        header = _parse_csv_row(lines[0])
        if header is None:
            return []
        if len(header) < 3 or len(set(header)) != len(header):
            return []
        records: list[dict[str, str]] = []
        for index in indices:
            if index == 0 or not 0 <= index < len(lines):
                continue
            row = _parse_csv_row(lines[index])
            if row is None:
                return []
            if len(row) != len(header):
                return []
            records.append(dict(zip(header, row, strict=True)))
        return records

    def source_packet(
        self,
        reason: str,
        *,
        allow_preview: bool = True,
        include_structured_csv: bool = False,
        prefer_retained: bool = True,
    ) -> list[dict[str, Any]]:
        mentioned_refs = list(dict.fromkeys(re.findall(r"\b(S\d+(?:\.\d+)?|P\d+)\b", reason)))
        refs: list[str] = []
        for ref in mentioned_refs:
            if re.fullmatch(r"S\d+", ref):
                refs.extend(candidate for candidate in self.sources if candidate.startswith(f"{ref}."))
            else:
                refs.append(ref)
        refs.extend(source.ref for source in self.sources.values() if source.key in reason)
        refs = list(dict.fromkeys(refs))
        single_source_line_indices: list[int] = []
        if len(refs) == 1:
            indices: set[int] = set()
            for match in re.finditer(
                r"\b(?:lines?\s+)?L(\d+)(?:\s*-\s*L?(\d+))?",
                reason,
                flags=re.IGNORECASE,
            ):
                start = int(match.group(1))
                end = int(match.group(2) or start)
                if end < start:
                    start, end = end, start
                indices.update(range(max(1, start) - 1, end))
            single_source_line_indices = sorted(indices)
        line_ids = list(dict.fromkeys(re.findall(r"\bL[0-9a-f]{10}\b", reason)))
        packet: list[dict[str, Any]] = []
        for ref in refs:
            source = self.sources.get(ref)
            if source is None:
                continue
            if prefer_retained and ref in self.retained_evidence:
                retained = self.retained_evidence[ref]
                retained_item = {
                    key: value
                    for key, value in retained.items()
                    if key in {"source_ref", "title", "url", "quote", "csv_records"}
                }
                remaining_focused = self.focused_lines.get(source.key)
                if remaining_focused:
                    selected_indices = self.source_evidence_indices(
                        source.key,
                        remaining_focused,
                    )
                    focused_item: dict[str, Any] = {
                        "source_ref": f"[{ref}]",
                        "title": source.title,
                        "url": source.url,
                        "quote": "\n".join(
                            item["text"]
                            for item in self.render_lines(source.key, selected_indices)
                        ),
                    }
                    if include_structured_csv:
                        csv_records = self.structured_csv_records(
                            source.key,
                            selected_indices,
                        )
                        if csv_records:
                            retained_records = list(retained_item.get("csv_records", []))
                            focused_item["csv_records"] = [
                                *retained_records,
                                *(
                                    record
                                    for record in csv_records
                                    if record not in retained_records
                                ),
                            ]
                        self.source_slices[ref] = _merge_citation_slices(
                            self.source_slices.get(ref, []),
                            self.citation_slices(source.key, selected_indices),
                        )
                    retained_item = _merge_source_packets(
                        [retained_item],
                        [focused_item],
                    )[0]
                packet.append(retained_item)
                continue
            source_line_ids = [
                line_id for line_id in line_ids if self.line_locations.get(line_id, (None,))[0] == source.key
            ]
            cited_line_indices = sorted(set(self.cited_line_indices(reason, ref)) | set(single_source_line_indices))
            selected_indices: list[int] | range | None
            citation_indices: list[int] | range | None
            if source_line_ids:
                line_indices = [self.line_locations[line_id][1] for line_id in source_line_ids]
                evidence_window = set(line_indices)
                selected_indices = self.source_evidence_indices(
                    source.key,
                    evidence_window,
                    include_focused=False,
                )
                citation_indices = selected_indices
                quote = "\n".join(item["text"] for item in self.render_lines(source.key, selected_indices))
            elif cited_line_indices:
                selected = set(cited_line_indices)
                citation_indices = self.source_evidence_indices(
                    source.key,
                    selected,
                    include_focused=False,
                )
                selected_indices = citation_indices
                quote = "\n".join(
                    f"{item['line']}: {item['text']}" for item in self.render_lines(source.key, selected_indices)
                )
            elif source.key in self.focused_lines:
                selected_indices = self.source_evidence_indices(
                    source.key,
                    self.focused_lines[source.key],
                )
                citation_indices = selected_indices
                quote = "\n".join(item["text"] for item in self.render_lines(source.key, selected_indices))
            elif not allow_preview:
                continue
            else:
                quote, slices = self.packet_preview(source.key)
                self.source_slices[ref] = slices
                selected_indices = None
                citation_indices = None
            if include_structured_csv and selected_indices is not None:
                self.source_slices[ref] = self.citation_slices(
                    source.key,
                    citation_indices or selected_indices,
                )
            item: dict[str, Any] = {
                "source_ref": f"[{ref}]",
                "title": source.title,
                "url": source.url,
                "quote": quote,
            }
            if selected_indices is not None:
                csv_records = self.structured_csv_records(source.key, selected_indices)
                if csv_records:
                    item["csv_records"] = csv_records
            packet.append(item)
        return packet

    def citation_plan(
        self,
        answer: str,
        fallback_packet: list[dict[str, Any]],
        final_source_slices: dict[str, list[CitationSlice]],
        audit: str,
    ) -> CitationPlan:
        audit_refs = list(dict.fromkeys(re.findall(r"\b(S\d+(?:\.\d+)?|P\d+)\b", audit)))
        answer_refs = list(dict.fromkeys(re.findall(r"\b(S\d+(?:\.\d+)?|P\d+)\b", answer)))
        mentioned_refs = list(dict.fromkeys([*answer_refs, *audit_refs]))
        refs: list[str] = []
        for ref in mentioned_refs:
            if re.fullmatch(r"S\d+", ref):
                refs.extend(candidate for candidate in self.sources if candidate.startswith(f"{ref}."))
            else:
                refs.append(ref)
        if not refs:
            refs = [item["source_ref"][1:-1] for item in fallback_packet]
        citation_sources: dict[tuple[str, str], Source] = {}
        citation_slices: dict[tuple[str, str], list[CitationSlice]] = {}
        source_identities: dict[str, tuple[str, str]] = {}
        for ref in refs:
            source = self.sources.get(ref)
            if source and source.receipt_id and source.result_id:
                identity = (source.receipt_id, source.result_id)
                source_identities[ref] = identity
                slices = _merge_citation_slices(
                    [],
                    final_source_slices.get(ref, self.source_slices.get(ref, [])),
                )
                citation_sources[identity] = source
                citation_slices[identity] = _merge_citation_slices(
                    citation_slices.get(identity, []),
                    slices,
                )
        identity_indices = {
            identity: index
            for index, identity in enumerate(citation_sources, start=1)
        }
        citations = [
            CitationRef(
                receipt_id=source.receipt_id,
                result_id=source.result_id,
                slices=citation_slices[identity],
            )
            for identity, source in citation_sources.items()
        ]
        return CitationPlan(
            citations=citations,
            source_indices={
                ref: identity_indices[identity]
                for ref, identity in source_identities.items()
                if identity in identity_indices
            },
        )


def _private_source_refs(answer: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\[(S\d+(?:\.\d+)?|P\d+)\]", answer)))


def _normalize_grouped_private_refs(answer: str) -> str:
    ref = r"(?:S\d+(?:\.\d+)?|P\d+)"
    grouped = re.compile(rf"\[({ref}(?:\s*,\s*{ref})+)\]")

    def _split_group(match: "re.Match[str]") -> str:
        return "".join(
            f"[{item}]"
            for item in re.findall(ref, match.group(1))
        )

    return grouped.sub(_split_group, answer)


def _requires_unadorned_output(question: str) -> bool:
    return bool(
        re.search(
            r"(?i)\b(?:output|return|respond)\s+only\b",
            question,
        )
    )


def _validate_private_answer_refs(
    answer: str,
    allowed_refs: set[str],
    *,
    require_ref: bool = True,
) -> None:
    if "[[" in answer or "]]" in answer:
        raise ValueError("write private source refs such as [P1], not public numeric markers")
    if re.search(
        r"(?i)(?:https?://|\bwww\.|(?<!:)//(?=[a-z0-9])|"
        r"(?<![\w@])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,63}/[^\s)]*)",
        answer,
    ):
        raise ValueError("do not render raw URLs in the reader-facing answer")
    if re.search(
        r"(?im)^\s{0,3}(?:#{1,6}\s*)?(?:sources?|citations?|references?|bibliography|works\s+cited)\s*:?\s*$",
        answer,
    ):
        raise ValueError("do not render a citation or source-list section")

    exact_ref_pattern = re.compile(r"\[(?:S\d+(?:\.\d+)?|P\d+)\]")
    without_exact_refs = exact_ref_pattern.sub("", answer)
    if "[" in without_exact_refs or "]" in without_exact_refs:
        raise ValueError(
            "square brackets are reserved for one exact private source ref such as [P1]"
        )
    if re.search(r"\b(?:S\d+(?:\.\d+)?|P\d+)\b", without_exact_refs):
        raise ValueError(
            "each private source ref must appear alone in brackets, for example [P1]"
        )
    refs = _private_source_refs(answer)
    unknown_refs = [ref for ref in refs if ref not in allowed_refs]
    if unknown_refs:
        raise ValueError(f"answer cites unavailable source refs: {', '.join(unknown_refs)}")
    if require_ref and allowed_refs and not refs:
        raise ValueError("answer must place at least one supplied source ref after a supported factual claim")


def _render_public_citations(
    answer: str,
    plan: CitationPlan,
    *,
    unadorned_output: bool = False,
) -> tuple[str, list[CitationRef]]:
    refs = _private_source_refs(answer)
    missing_refs = [ref for ref in refs if ref not in plan.source_indices]
    if missing_refs:
        raise ValueError(
            "answer source refs do not have materializable citations: "
            + ", ".join(missing_refs)
        )
    def _to_public_marker(match: "re.Match[str]") -> str:
        return f"[[{plan.source_indices[match.group(1)]}]]"

    rendered = re.sub(
        r"\[(S\d+(?:\.\d+)?|P\d+)\]",
        _to_public_marker,
        answer,
    )
    marker_indices = [
        int(value)
        for value in re.findall(r"\[\[(\d+)]]", rendered)
    ]
    invalid_indices = sorted(
        {
            index
            for index in marker_indices
            if index < 1 or index > len(plan.citations)
        }
    )
    if invalid_indices:
        raise ValueError(
            "answer contains citation indices without response citations: "
            + ", ".join(str(index) for index in invalid_indices)
        )
    if plan.citations and not marker_indices and not unadorned_output:
        raise ValueError("answer has response citations but no inline citation markers")

    used_indices = (
        sorted(set(marker_indices))
        if marker_indices
        else list(range(1, len(plan.citations) + 1))
    )
    compact_indices = {
        old_index: new_index
        for new_index, old_index in enumerate(used_indices, start=1)
    }
    def _to_compact_marker(match: "re.Match[str]") -> str:
        return f"[[{compact_indices[int(match.group(1))]}]]"

    rendered = re.sub(
        r"\[\[(\d+)]]",
        _to_compact_marker,
        rendered,
    )
    if unadorned_output:
        rendered = re.sub(r"[ \t]*\[\[\d+]]", "", rendered)
    return (
        rendered.strip(),
        [plan.citations[index - 1] for index in used_indices],
    )


def _strip_unmaterializable_refs(answer: str, plan: CitationPlan) -> str:
    """Remove only the private refs that cannot be materialized as citations.

    Materializable refs are left alone so citation density is preserved as far as
    possible.
    """

    def _replace(match: "re.Match[str]") -> str:
        return match.group(0) if match.group(1) in plan.source_indices else ""

    cleaned = re.sub(r"\s*\[(S\d+(?:\.\d+)?|P\d+)\]", _replace, answer)
    return re.sub(r"[ \t]+([.,;:!?])", r"\1", cleaned).strip()


def _strip_all_private_refs(answer: str) -> str:
    cleaned = re.sub(r"\s*\[(?:S\d+(?:\.\d+)?|P\d+)\]", "", answer)
    return re.sub(r"[ \t]+([.,;:!?])", r"\1", cleaned).strip()


def _safe_render_public_citations(
    answer: str,
    plan: CitationPlan,
    *,
    unadorned_output: bool = False,
) -> tuple[str, list[CitationRef]]:
    """Wrap _render_public_citations so it can never raise.

    The original called this renderer bare at three return sites. The renderer has
    five distinct ValueError paths, so a finished answer that had already passed
    investigation and audit could blow up at the final assembly step and score the
    whole task zero. Here each failure drops citation density by one step and the
    answer itself is always returned. Slightly lower quality always beats a zero.
    """
    try:
        return _render_public_citations(answer, plan, unadorned_output=unadorned_output)
    except (ValueError, KeyError, IndexError):
        pass

    # Step 1: strip only the refs that cannot be materialized.
    cleaned = _strip_unmaterializable_refs(answer, plan)
    if cleaned:
        try:
            return _render_public_citations(
                cleaned,
                plan,
                unadorned_output=unadorned_output,
            )
        except (ValueError, KeyError, IndexError):
            pass

    # Step 2: strip every ref and attach the citation list alone.
    bare = _strip_all_private_refs(answer)
    if bare:
        try:
            return _render_public_citations(bare, plan, unadorned_output=True)
        except (ValueError, KeyError, IndexError):
            pass

    # Step 3: return the prose alone, with no citations.
    return (bare or answer.strip() or "No answer could be assembled."), []


def _merge_citation_slices(
    existing: list[CitationSlice],
    additional: list[CitationSlice],
) -> list[CitationSlice]:
    spans = sorted(
        (int(item.start), int(item.end)) for item in [*existing, *additional] if int(item.end) > int(item.start)
    )
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return [CitationSlice(start=start, end=end) for start, end in merged]


def _assistant_message(result: Any) -> Any:
    choices = result.llm.choices
    if len(choices) != 1:
        raise RuntimeError(f"expected one LLM choice, received {len(choices)}")
    return choices[0].message


def _assistant_evidence_context(message: Any) -> str:
    text_parts = [
        str(part.text)
        for part in message.content
        if getattr(part, "text", None)
    ]
    return "\n".join(
        item
        for item in (str(message.reasoning or "").strip(), *text_parts)
        if item
    )


def _collect_vfs_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for field, item in value.items():
            if field in {"key", "vfs_key"} and isinstance(item, str):
                keys.append(item)
            elif field in {"keys", "matched_keys"} and isinstance(item, list):
                keys.extend(candidate for candidate in item if isinstance(candidate, str))
            else:
                keys.extend(_collect_vfs_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.extend(_collect_vfs_keys(item))
    return list(dict.fromkeys(keys))


def _compact_consumed_tool_results(messages: list[Any]) -> None:
    for message in messages:
        if not isinstance(message, dict) or message.get("role") != "tool":
            continue
        content = message.get("content")
        if not isinstance(content, str) or len(content) < 1_000:
            continue
        try:
            output = json.loads(content)
        except json.JSONDecodeError:
            continue
        if not isinstance(output, dict):
            continue
        receipt: dict[str, Any] = {"ok": output.get("ok", False)}
        keys = _collect_vfs_keys(output)
        if keys:
            receipt["vfs_keys"] = keys
        if output.get("error_type"):
            receipt["error_type"] = output["error_type"]
            receipt["details"] = str(output.get("details", ""))[:1_000]
        if output.get("audit"):
            receipt["audit"] = output["audit"]
        similarity = output.get("similarity")
        if isinstance(similarity, dict):
            receipt["similarity"] = {
                field: similarity[field]
                for field in ("status", "trigger", "reason")
                if field in similarity
            }
        message["content"] = json.dumps(receipt, ensure_ascii=False)


def _compact_consumed_assistant_reasoning(messages: list[Any]) -> None:
    for index, message in enumerate(messages):
        if isinstance(message, LlmMessage):
            if message.role == "assistant" and message.reasoning_details is not None:
                messages[index] = replace(message, reasoning_details=None)
            continue
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        message.pop("reasoning", None)
        message.pop("reasoning_details", None)


def _record_retrieval_receipt(
    state: ResearchState,
    name: str,
    args: dict[str, Any],
    output: dict[str, Any],
) -> None:
    if not output.get("ok") or name not in {"search_web", "fetch_page"}:
        return
    if name == "search_web":
        destinations = [str(output["vfs_key"])]
        source_index = [
            {
                "source_ref": item["source_ref"],
                "vfs_key": item["vfs_key"],
                "title": item["title"],
                "url": item["url"],
            }
            for item in output.get("results", [])
            if isinstance(item, dict)
        ]
    else:
        destinations = [
            str(page["vfs_key"]) for page in output.get("pages", []) if isinstance(page, dict) and page.get("vfs_key")
        ]
        source_index = [
            {
                "source_ref": item["source_ref"],
                "vfs_key": item["vfs_key"],
                "title": item["title"],
                "url": item["url"],
            }
            for item in output.get("pages", [])
            if isinstance(item, dict)
        ]
    signature = _retrieval_signature(name, args)
    state.retrieval_output_cache[signature] = output
    receipt = state.retrieval_receipts.setdefault(
        signature,
        {
            "tool": name,
            "arguments": args,
            "destinations": [],
            "sources": [],
            "calls": 0,
        },
    )
    receipt["calls"] += 1
    receipt["destinations"] = list(dict.fromkeys([*receipt["destinations"], *destinations]))
    known_sources = {str(item["source_ref"]): item for item in [*receipt["sources"], *source_index]}
    receipt["sources"] = list(known_sources.values())


def _retrieval_signature(name: str, args: dict[str, Any]) -> str:
    return json.dumps(
        {"tool": name, "arguments": args},
        ensure_ascii=False,
        sort_keys=True,
    )


def _record_vfs_operation_receipt(
    state: ResearchState,
    name: str,
    args: dict[str, Any],
    output: dict[str, Any],
) -> None:
    if not output.get("ok") or name not in {"vfs_read", "vfs_search", "vfs_list"}:
        return

    if name == "vfs_read":
        lines = output.get("lines", [])
        outcome = {
            "returned_line_count": len(lines),
            "first_line": lines[0].get("line") if lines else None,
            "last_line": lines[-1].get("line") if lines else None,
            "truncated": bool(output.get("truncated")),
        }
    elif name == "vfs_search":
        regex = output.get("regex", {})
        similarity = output.get("similarity", {})
        outcome = {
            "regex_total_match_count": regex.get("total_match_count"),
            "regex_returned_match_count": len(regex.get("matches", [])),
            "regex_next_cursor": regex.get("next_cursor"),
            "similarity_status": similarity.get("status"),
            "similarity_returned_chunk_count": len(similarity.get("chunks", [])),
        }
    else:
        outcome = {"returned_key_count": len(output.get("keys", []))}

    signature = json.dumps(
        {"tool": name, "arguments": args},
        ensure_ascii=False,
        sort_keys=True,
    )
    receipt = state.vfs_operation_receipts.setdefault(
        signature,
        {
            "tool": name,
            "arguments": args,
            "calls": 0,
            "outcome": outcome,
        },
    )
    receipt["calls"] += 1
    receipt["outcome"] = outcome


def _collect_source_refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        for field, item in value.items():
            if field == "source_ref" and isinstance(item, str):
                refs.append(item.strip().strip("[]"))
            else:
                refs.extend(_collect_source_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.extend(_collect_source_refs(item))
    return list(dict.fromkeys(refs))


def _capture_budget(state: ResearchState, result: Any) -> None:
    budget = getattr(result, "budget", None)
    if budget is None:
        return
    state.budget_snapshot = {
        "session_hard_limit_usd": round(float(budget.session_hard_limit_usd), 6),
        "session_used_budget_usd": round(float(budget.session_used_budget_usd), 6),
        "session_hard_remaining_usd": round(
            max(
                0.0,
                float(budget.session_hard_limit_usd) - float(budget.session_used_budget_usd),
            ),
            6,
        ),
    }


def _closable_source_refs(state: ResearchState) -> list[str]:
    """Source refs that are safe to cite when the harness closes the task itself.

    _finalize_answer raises ValueError when (a) the context mentions no source ref
    at all, or (b) a page ref (P*) is absent from retained_evidence. Filtering both
    conditions up front avoids making a call that is bound to fail.
    """
    return [
        ref
        for ref in state.sources
        if not str(ref).startswith("P") or str(ref) in state.retained_evidence
    ]


def _closable_source_context(state: ResearchState) -> str:
    """Context for a forced close, naming every citable ref explicitly."""
    refs = " ".join(f"[{ref}]" for ref in _closable_source_refs(state))
    return f"{state.research_state}\n\nObserved source references: {refs}"


def _governor_stage(state: ResearchState, elapsed_seconds: float) -> str:
    """Pick the investigation stage from observed spend and elapsed time.

    Stages run open -> soft -> hard.

    Whichever threshold is crossed first wins. The original only asked for both in
    the prompt without enforcing either, and budget exhaustion (zero) and 300s
    overruns (zero) both actually occurred.
    """
    if elapsed_seconds >= TIME_GOVERNOR_HARD_SECONDS:
        return "hard"
    snapshot = state.budget_snapshot or {}
    limit = float(snapshot.get("session_hard_limit_usd") or 0.0)
    if limit <= 0.0:
        limit = SPEND_GOVERNOR_FALLBACK_LIMIT_USD
    used = float(snapshot.get("session_used_budget_usd") or 0.0)
    if used >= limit * SPEND_GOVERNOR_HARD_FRACTION:
        return "hard"
    if elapsed_seconds >= TIME_GOVERNOR_SOFT_SECONDS:
        return "soft"
    if used >= limit * SPEND_GOVERNOR_SOFT_FRACTION:
        return "soft"
    return "open"


def _refresh_retrieval_receipt_message(
    messages: list[Any],
    state: ResearchState,
) -> None:
    marker = "Harness research memory"
    messages[:] = [
        message
        for message in messages
        if not (
            isinstance(message, dict)
            and message.get("role") == "user"
            and isinstance(message.get("content"), str)
            and message["content"].startswith(marker)
        )
    ]
    if (
        not state.research_state
        and not state.audit_gap
        and not state.budget_snapshot
        and not state.retrieval_receipts
        and not state.vfs_operation_receipts
        and not state.retained_evidence
        and not state.focused_lines
        and not state.reasoning_observations
    ):
        return
    sections: list[str] = []
    if state.evidence_requirements:
        sections.append(
            "Evidence questions established before retrieval. They guide the investigation "
            "but may become immaterial after supported filtering:\n" + state.evidence_requirements
        )
    if state.audit_gap:
        sections.append(
            "Latest finalization audit. This gap overrides any stale claim in the "
            "model-authored state that no uncertainty remains. Do not call "
            "ready_to_finalize again until new evidence resolves it:\n" + state.audit_gap
        )
    if state.budget_snapshot:
        sections.append(
            "Latest hosted-tool budget snapshot. This is runtime state, not evidence:\n"
            + json.dumps(state.budget_snapshot, ensure_ascii=False, separators=(",", ":"))
            + "\nFinish before the hard remaining amount reaches zero. After observing the "
            "single result that resolves an audit gap, combine any now-independent "
            "retain_evidence, update_research_state, and ready_to_finalize calls in the "
            "same response instead of spending separate turns on each."
        )
    if state.research_state:
        sections.append(
            "Current model-authored research state. Revise it with update_research_state "
            "when the answer, support, or next unresolved question changes:\n" + state.research_state
        )
    if state.reasoning_observations:
        sections.append(
            "Prior source-linked reasoning preserved by the harness. This is working memory, "
            "not external evidence. Use its source refs to avoid rediscovering observations, "
            "but inspect or retain the referenced source text before relying on a material "
            "premise in the final answer:\n"
            + "\n\n---\n\n".join(state.reasoning_observations)
        )
    if state.retrieval_receipts:
        compact_retrieval_receipts = [
            {
                key: receipt[key]
                for key in ("tool", "arguments", "destinations", "sources", "calls")
                if key in receipt
            }
            for receipt in state.retrieval_receipts.values()
        ]
        sections.append(
            "Completed external retrieval receipts. These record actions and a compact "
            "source inventory, not evidence. Each source entry maps a stable source ref "
            "to the exact VFS key whose text can be re-read instead of repeating a web "
            "search:\n"
            + json.dumps(
                compact_retrieval_receipts,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    if state.vfs_operation_receipts:
        sections.append(
            "Completed local VFS inspection operations. These are action history, not "
            "evidence. Do not repeat the same read or search merely by changing wording. "
            "When prior local inspections did not expose the missing relationship, change "
            "the evidence route:\n"
            + json.dumps(
                list(state.vfs_operation_receipts.values()),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    if state.retained_evidence:
        sections.append(
            "Retained source excerpts selected by your prior reasoning. These are "
            "external evidence and do not need to be retrieved again. Only each quote "
            "is source evidence; research_note is your prior interpretation and may be wrong:\n"
            + json.dumps(
                list(state.retained_evidence.values()),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    if state.focused_lines:
        sections.append(
            "Recent unretained VFS observations. VFS remains the full source of truth; "
            "only one generous read-page of recent raw observations is replayed here. "
            "Retain lines that support or contradict a material premise. Re-read a VFS "
            "location when an older unretained observation becomes necessary:\n"
            + json.dumps(
                state.focused_excerpts(),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    messages.insert(
        2,
        {
            "role": "user",
            "content": f"{marker}:\n\n" + "\n\n".join(sections),
        },
    )


def _merge_source_packets(
    retained: list[dict[str, Any]],
    current: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {str(item["source_ref"]): item for item in retained}
    for item in current:
        source_ref = str(item["source_ref"])
        previous = merged.get(source_ref)
        if previous is None:
            merged[source_ref] = item
            continue
        previous_quote = str(previous.get("quote", "")).strip()
        current_quote = str(item.get("quote", "")).strip()
        if not previous_quote or previous_quote in current_quote:
            quote = current_quote
        elif not current_quote or current_quote in previous_quote:
            quote = previous_quote
        else:
            quote = f"{previous_quote}\n\n{current_quote}"
        merged[source_ref] = {**previous, **item, "quote": quote}
    return list(merged.values())


def _deadline_timeout(
    started_at: float,
    base: float,
    *,
    floor: float = LOOP_TIMEOUT_FLOOR_SECONDS,
) -> float:
    """Narrow a model timeout to the time left before the absolute wall.

    The original gave every investigation-loop turn a fixed 90s. A turn beginning
    at 240s elapsed could blow the 300s hard wall on its own. When less than floor
    remains, floor is still granted: zero or negative would only produce an
    immediate failure on every retry.
    """
    remaining = TIME_GOVERNOR_ABSOLUTE_SECONDS - (time.monotonic() - started_at)
    if remaining <= floor:
        return floor
    return max(floor, min(base, remaining))


def _is_retryable_llm_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "429",
            "500",
            "502",
            "503",
            "504",
            "service unavailable",
            "timed out",
            "timeout",
            "empty_output",
            "empty output",
            "tool execution failed",
            "tool invocation failed",
        )
    )


async def _call_model(
    model_name: str,
    messages: list[Any],
    tools: list[dict[str, Any]] | None,
    tool_choice: str,
    parallel_tool_calls: bool,
    timeout: float,
    max_output_tokens: int | None = None,
) -> Any:
    if model_name == "glm5":
        return await llm_chat(
            provider="openrouter",
            model="z-ai/glm-5",
            messages=messages,
            temperature=0.2,
            max_output_tokens=max_output_tokens or GLM5_MAX_OUTPUT_TOKENS,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking={"enabled": True, "effort": "low"},
            provider_extra=OPENROUTER_GLM_PROVIDER_PREFERENCES,
            timeout=timeout,
        )
    if model_name == "gpt_oss":
        return await llm_chat(
            provider="openrouter",
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=0.0,
            max_output_tokens=max_output_tokens or GPT_OSS_MAX_OUTPUT_TOKENS,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking={"enabled": True, "effort": "high"},
            provider_extra=OPENROUTER_GPT_PROVIDER_PREFERENCES,
            timeout=timeout,
        )
    if model_name == "openrouter_gemma":
        return await llm_chat(
            provider="openrouter",
            model="google/gemma-4-31b-it",
            messages=messages,
            temperature=1.0,
            max_output_tokens=max_output_tokens or OPENROUTER_GEMMA_MAX_OUTPUT_TOKENS,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking={"enabled": True, "effort": "medium"},
            provider_extra=OPENROUTER_GEMMA_PROVIDER_PREFERENCES,
            timeout=timeout,
        )
    if model_name == "openrouter_gemma_prose":
        return await llm_chat(
            provider="openrouter",
            model="google/gemma-4-31b-it",
            messages=messages,
            temperature=1.0,
            max_output_tokens=max_output_tokens or OPENROUTER_GEMMA_MAX_OUTPUT_TOKENS,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking={"enabled": True, "effort": "medium"},
            provider_extra=OPENROUTER_GEMMA_PROVIDER_PREFERENCES,
            timeout=timeout,
        )
    if model_name == "openrouter_gemma_stable":
        return await llm_chat(
            provider="openrouter",
            model="google/gemma-4-31b-it",
            messages=messages,
            temperature=1.0,
            max_output_tokens=max_output_tokens or OPENROUTER_GEMMA_MAX_OUTPUT_TOKENS,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking={"enabled": True, "effort": "medium"},
            provider_extra=OPENROUTER_GEMMA_STABLE_PROVIDER_PREFERENCES,
            timeout=timeout,
        )
    if model_name == "chutes_gemma":
        return await llm_chat(
            provider="chutes",
            model="google/gemma-4-31B-turbo-TEE",
            messages=messages,
            temperature=1.0,
            max_output_tokens=max_output_tokens or CHUTES_GEMMA_MAX_OUTPUT_TOKENS,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            timeout=timeout,
        )
    if model_name == "openrouter_gemma_open":
        # Final ladder rung. No provider pinning, so openrouter routes to whatever
        # backend is alive at that moment. This rung survives even when every
        # earlier rung fails because of its provider pin.
        return await llm_chat(
            provider="openrouter",
            model="google/gemma-4-31b-it",
            messages=messages,
            temperature=1.0,
            max_output_tokens=max_output_tokens or OPENROUTER_GEMMA_MAX_OUTPUT_TOKENS,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking={"enabled": True, "effort": "medium"},
            timeout=timeout,
        )
    raise ValueError(f"unknown model: {model_name}")


async def _call_model_guarded(
    model_name: str,
    messages: list[Any],
    tools: list[dict[str, Any]] | None,
    tool_choice: str,
    parallel_tool_calls: bool,
    timeout: float,
    max_output_tokens: int | None = None,
) -> Any:
    """Impose a local hard ceiling on _call_model.

    The timeout argument to llm_chat may never fire while a provider is still
    trickling out a response. A single model turn that eats the entire 300s hard
    wall scores the task zero, so the call is cut off at the asyncio level here. A
    cut-off call surfaces as a retryable error and the next ladder rung takes over.
    """
    try:
        return await asyncio.wait_for(
            _call_model(
                model_name,
                messages,
                tools,
                tool_choice,
                parallel_tool_calls,
                timeout,
                max_output_tokens,
            ),
            timeout=max(5.0, timeout + LLM_TIMEOUT_LOCAL_SLACK_SECONDS),
        )
    except asyncio.TimeoutError as error:
        # str() on asyncio.TimeoutError is usually empty, so _is_retryable_llm_error
        # would not recognise it as retryable. Re-raise with an explicit message.
        raise TimeoutError(
            f"model {model_name} timed out after {timeout:.1f}s local ceiling"
        ) from error


async def _chat_with_model_fallback(
    models: tuple[str, ...],
    messages: list[Any],
    tools: list[dict[str, Any]] | None,
    tool_choice: str,
    parallel_tool_calls: bool,
    timeout: float,
    max_output_tokens: int | None = None,
) -> Any:
    if not models:
        raise RuntimeError("no research model was configured")

    raced_models = models[:2]
    remaining_models = models[2:]
    tasks = [
        asyncio.create_task(
            _call_model_guarded(
                model,
                messages,
                tools,
                tool_choice,
                parallel_tool_calls,
                timeout,
                max_output_tokens,
            )
        )
        for model in raced_models
    ]
    errors: list[Exception] = []
    pending = set(tasks)
    try:
        while pending:
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done:
                try:
                    result = task.result()
                except Exception as error:
                    errors.append(error)
                    continue
                for unfinished in pending:
                    unfinished.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                return result
    finally:
        for unfinished in pending:
            unfinished.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    non_retryable = next(
        (error for error in errors if not _is_retryable_llm_error(error)),
        None,
    )
    if non_retryable is not None:
        raise non_retryable

    for model in remaining_models:
        try:
            return await _call_model_guarded(
                model,
                messages,
                tools,
                tool_choice,
                parallel_tool_calls,
                timeout,
                max_output_tokens,
            )
        except Exception as error:
            if not _is_retryable_llm_error(error):
                raise
            errors.append(error)

    if not errors:
        raise RuntimeError("no research model was configured")
    raise errors[-1]


async def _chat_with_sequential_model_fallback(
    models: tuple[str, ...],
    messages: list[Any],
    tools: list[dict[str, Any]] | None,
    tool_choice: str,
    parallel_tool_calls: bool,
    timeout: float,
    max_output_tokens: int | None = None,
) -> Any:
    if not models:
        raise RuntimeError("no research model was configured")

    errors: list[Exception] = []
    for model in models:
        try:
            return await _call_model_guarded(
                model,
                messages,
                tools,
                tool_choice,
                parallel_tool_calls,
                timeout,
                max_output_tokens,
            )
        except Exception as error:
            if not _is_retryable_llm_error(error):
                raise
            errors.append(error)

    # models is guaranteed non-empty above, so errors is non-empty too, but never
    # allow an IndexError from indexing an empty list.
    if not errors:
        raise RuntimeError("no research model produced a result")
    raise errors[-1]


async def _chat_with_scheduling(
    models: tuple[str, ...],
    messages: list[Any],
    tools: list[dict[str, Any]] | None,
    tool_choice: str,
    parallel_tool_calls: bool,
    timeout: float,
    max_output_tokens: int | None = None,
) -> Any:
    if MODEL_SCHEDULING == "race":
        return await _chat_with_model_fallback(
            models,
            messages,
            tools,
            tool_choice,
            parallel_tool_calls,
            timeout,
            max_output_tokens,
        )
    if MODEL_SCHEDULING in {"sequential", "state_aware"}:
        return await _chat_with_sequential_model_fallback(
            models,
            messages,
            tools,
            tool_choice,
            parallel_tool_calls,
            timeout,
            max_output_tokens,
        )
    raise ValueError(f"unknown model scheduling policy: {MODEL_SCHEDULING}")


async def _prose_chat_with_retry(
    messages: list[Any],
    tool_choice: str,
    timeout: float,
) -> Any:
    return await _chat_with_scheduling(
        PROSE_MODELS,
        messages,
        None,
        tool_choice,
        False,
        timeout,
    )


async def _final_answer_chat_with_retry(
    messages: list[Any],
    timeout: float,
) -> Any:
    return await _chat_with_scheduling(
        PROSE_MODELS,
        messages,
        None,
        "none",
        False,
        timeout,
    )


async def _research_text(system: str, user: str) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    result = await _prose_chat_with_retry(messages, "none", LLM_TIMEOUT)
    text = result.llm.raw_text
    if not text or not text.strip():
        raise RuntimeError("research model returned empty prose")
    return text.strip()


async def _answer_text(
    *,
    state: ResearchState,
    question: str,
    prior_answer: str,
    requirements: str,
    research_state: str,
    finalization_reason: str,
    packet: list[dict[str, Any]],
) -> str:
    allowed_refs = {
        str(item["source_ref"]).strip("[]")
        for item in packet
        if isinstance(item, dict) and item.get("source_ref")
    }
    messages: list[Any] = [
        {"role": "system", "content": ANSWER_UPDATE_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Original question:\n{question}\n\n"
                f"Prior answer hypothesis:\n{prior_answer}\n\n"
                f"Evidence requirements:\n{requirements}\n\n"
                f"Investigator's current research state:\n"
                f"{research_state or '(not updated)'}\n\n"
                f"Finalization reason:\n{finalization_reason}\n\n"
                f"Supplied source records:\n"
                f'{json.dumps(packet, ensure_ascii=False, separators=(",", ":"))}'
            ),
        },
    ]
    last_text = ""
    for attempt in range(3):
        # Fit the retry budget to the time left. The original allowed 3 attempts at a
        # fixed 90s, so the final-answer step alone could cross the hard wall.
        if attempt and time.monotonic() - state.started_at >= TIME_GOVERNOR_ABSOLUTE_SECONDS:
            break
        result = await _final_answer_chat_with_retry(
            messages,
            _deadline_timeout(state.started_at, LLM_TIMEOUT, floor=CLOSING_TIMEOUT_FLOOR_SECONDS),
        )
        _capture_budget(state, result)
        text = result.llm.raw_text
        if not text or not text.strip():
            raise RuntimeError("answer writer returned empty prose")
        text = _normalize_grouped_private_refs(text.strip())
        last_text = text
        try:
            _validate_private_answer_refs(
                text,
                allowed_refs,
                require_ref=not _requires_unadorned_output(question),
            )
        except ValueError as error:
            if attempt == 2:
                raise
            messages.extend(
                [
                    {"role": "assistant", "content": text},
                    {
                        "role": "user",
                        "content": (
                            f"Output contract error: {error}. Rewrite the complete answer. "
                            "Use only the exact private source refs present in the supplied "
                            "records; the harness renders public citation numbers."
                        ),
                    },
                ]
            )
            continue
        return text
    # Retries stopped for lack of time. Keep the last draft even if it failed
    # contract validation; the renderer strips unmaterializable refs safely.
    if last_text:
        return last_text
    raise RuntimeError("answer writer produced no usable draft")


def _structured_output_tool(
    output_schema: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    direct_object = output_schema.get("type") == "object"
    parameters = (
        output_schema
        if direct_object
        else {
            "type": "object",
            "properties": {
                "output": {
                    "description": (
                        "The non-null JSON value that matches the caller's supplied output schema."
                    )
                }
            },
            "required": ["output"],
            "additionalProperties": False,
        }
    )
    return (
        {
            "type": "function",
            "function": {
                "name": "submit_structured_output",
                "description": (
                    "Submit the complete final value required by the caller's JSON Schema."
                ),
                "parameters": parameters,
                "strict": False,
            },
        },
        direct_object,
    )


async def _materialize_structured_output(
    *,
    question: str,
    answer: str,
    output_schema: dict[str, Any],
    started_at: float,
) -> Any:
    tool, direct_object = _structured_output_tool(output_schema)
    evidence_backed_answer = re.sub(r"\[\[\d+]]", "", answer).strip()
    messages: list[Any] = [
        {"role": "system", "content": STRUCTURED_OUTPUT_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Original question:\n{question}\n\n"
                f"Completed evidence-backed answer:\n{evidence_backed_answer}\n\n"
                "Required JSON Schema:\n"
                f"{json.dumps(output_schema, ensure_ascii=False, indent=2)}"
            ),
        },
    ]
    last_error: ValueError | None = None
    for attempt in range(3):
        # This step runs after the investigation has already spent most of the wall,
        # so a fixed 3 x 90s here could overrun on its own and score the task zero
        # with a finished answer in hand. Narrow each attempt to the time actually
        # left and stop retrying once the absolute wall is crossed, exactly as
        # _answer_text and _audit already do.
        if attempt and time.monotonic() - started_at >= TIME_GOVERNOR_ABSOLUTE_SECONDS:
            break
        result = await _chat_with_scheduling(
            INVESTIGATION_MODELS,
            messages,
            [tool],
            "required",
            False,
            _deadline_timeout(
                started_at,
                LLM_TIMEOUT,
                floor=CLOSING_TIMEOUT_FLOOR_SECONDS,
            ),
        )
        assistant = _assistant_message(result)
        calls = list(assistant.tool_calls or ())
        error: ValueError | None = None
        output: Any = None
        if len(calls) != 1:
            error = ValueError(
                "call submit_structured_output exactly once; "
                f"received {len(calls)} tool calls"
            )
        else:
            call = calls[0]
            try:
                if call.name != "submit_structured_output":
                    raise ValueError(
                        f"unexpected tool {call.name}; call submit_structured_output"
                    )
                arguments = json.loads(call.arguments)
                if not isinstance(arguments, dict):
                    raise ValueError("tool arguments must be a JSON object")
                if direct_object:
                    output = arguments
                else:
                    if set(arguments) != {"output"}:
                        raise ValueError(
                            "non-object output must be submitted in the sole `output` argument"
                        )
                    output = arguments["output"]
                if output is None:
                    raise ValueError("top-level null is not a valid miner answer")
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as caught:
                error = ValueError(str(caught))
        if error is None:
            return output
        last_error = error
        if attempt == 2:
            raise error

        messages.append(assistant.to_input_message())
        if calls:
            for call in calls:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            {
                                "ok": False,
                                "error_type": "tool_argument_validation",
                                "details": str(error),
                            }
                        ),
                    }
                )
        else:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Output contract error: {error}. Call the required tool with "
                        "the complete schema-conforming value."
                    ),
                }
            )
    # Retries stopped for lack of time. The caller catches this and returns the
    # prose answer rather than discarding the completed research.
    if last_error is not None:
        raise last_error
    raise RuntimeError("structured output was not produced within the time budget")


async def _expected_answer_text(question: str) -> str:
    messages = [
        {"role": "system", "content": EXPECTED_ANSWER_SYSTEM},
        {"role": "user", "content": question},
    ]
    try:
        # _call_model_guarded, not _call_model. This was the one model call site in
        # the module without a local asyncio ceiling, so a provider that accepted
        # the request and then stalled could burn the wall before the investigation
        # had started. The ceiling turns that into a retryable error instead.
        result = await _call_model_guarded(
            "openrouter_gemma",
            messages,
            None,
            "none",
            False,
            LLM_TIMEOUT,
        )
    except Exception as error:
        if not _is_retryable_llm_error(error):
            raise
        result = await _chat_with_scheduling(
            EXPECTED_ANSWER_FALLBACK_MODELS,
            messages,
            None,
            "none",
            False,
            LLM_TIMEOUT,
        )
    text = result.llm.raw_text
    if not text or not text.strip():
        raise RuntimeError("research model returned empty prose")
    return text.strip()


def _parse_audit(text: str) -> tuple[str, str]:
    matches = list(
        re.finditer(
            r"(?m)^VERDICT (READY|CONTINUE|REVISE)(?::[ \t]*(.*))?[ \t]*$",
            text,
        )
    )
    if len(matches) != 1:
        raise ValueError("audit must contain exactly one VERDICT line")
    match = matches[0]
    verdict = match.group(1)
    inline = (match.group(2) or "").strip()
    following = text[match.end() :].strip()
    payload = "\n".join(part for part in (inline, following) if part)
    if verdict == "REVISE" and not payload:
        raise ValueError("VERDICT REVISE must include a complete replacement answer")
    if verdict == "CONTINUE" and not payload:
        raise ValueError("VERDICT CONTINUE must name the missing observation")
    return verdict, payload


async def _audit(
    state: ResearchState,
    question: str,
    answer: str,
    packet: list[dict[str, Any]],
) -> str:
    allowed_refs = {
        str(item["source_ref"]).strip("[]")
        for item in packet
        if isinstance(item, dict) and item.get("source_ref")
    }
    source_inventory = [
        {
            "source_ref": f"[{source.ref}]",
            "title": source.title,
            "url": source.url,
        }
        for source in state.sources.values()
    ]
    messages = [
        {"role": "system", "content": AUDIT_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Original question:\n{question}\n\n"
                "Observed source inventory (discovery metadata only; titles and URLs are "
                "not evidence):\n"
                f'{json.dumps(source_inventory, ensure_ascii=False, separators=(",", ":"))}\n\n'
                f"Supplied source records:\n"
                f'{json.dumps(packet, ensure_ascii=False, separators=(",", ":"))}\n\n'
                f"Current answer:\n{answer}"
            ),
        },
    ]
    for attempt in range(3):
        if attempt and time.monotonic() - state.started_at >= TIME_GOVERNOR_ABSOLUTE_SECONDS:
            break
        result = await _chat_with_sequential_model_fallback(
            AUDIT_MODELS,
            messages,
            None,
            "none",
            False,
            _deadline_timeout(state.started_at, LLM_TIMEOUT, floor=CLOSING_TIMEOUT_FLOOR_SECONDS),
        )
        _capture_budget(state, result)
        text = result.llm.raw_text
        if not text or not text.strip():
            raise RuntimeError("auditor returned empty output")
        text = text.strip()
        try:
            verdict, payload = _parse_audit(text)
            if verdict in {"READY", "REVISE"} and re.search(r"(?m)^MISSING:", text):
                raise ValueError(
                    f"VERDICT {verdict} is invalid while a material premise is MISSING; "
                    "a MISSING line must name a real unresolved premise and cannot say none or "
                    "not applicable. If no premise is missing, preserve the verdict and omit all "
                    "MISSING lines. Correct only this output-format error; do not introduce a new "
                    "evidence requirement"
                )
            if verdict == "REVISE":
                _validate_private_answer_refs(
                    payload,
                    allowed_refs,
                    require_ref=not _requires_unadorned_output(question),
                )
        except ValueError as error:
            if attempt == 2:
                raise
            messages.extend(
                [
                    {"role": "assistant", "content": text},
                    {
                        "role": "user",
                        "content": (
                            f"Output contract error: {error}. Re-audit from the supplied records. "
                            "Follow the required premise-line and final VERDICT format exactly; "
                            "a replacement answer must use only exact supplied private source refs."
                        ),
                    },
                ]
            )
            continue
        return text
    # Re-audit stopped for lack of time. The caller catches this exception, treats
    # the verdict as READY, and closes with the current answer.
    raise RuntimeError("auditor produced no usable verdict within the time budget")


def _result_identity(result: Any, index: int) -> tuple[str | None, str | None]:
    if index >= len(result.results):
        return result.receipt_id, None
    return result.receipt_id, result.results[index].result_id


async def _execute_search(
    state: ResearchState,
    args: dict[str, Any],
    preview_budget_chars: int | None = None,
) -> dict[str, Any]:
    query = str(args["query"]).strip()
    num = int(args.get("num", 10))
    result = await search_web(
        query,
        provider=SEARCH_PROVIDER,
        num=num,
        timeout=SEARCH_TIMEOUT,
    )
    _capture_budget(state, result)
    state.search_count += 1
    parent_key = f"search://{state.search_count}"
    state.vfs[parent_key] = result.response.model_dump_json(indent=2)
    items: list[dict[str, Any]] = []
    preview_chars = 8_000
    if preview_budget_chars is not None:
        preview_chars = min(
            preview_chars,
            max(300, preview_budget_chars // max(1, len(result.response.data))),
        )
    for index, item in enumerate(result.response.data):
        ref = f"S{state.search_count}.{index + 1}"
        key = f"{parent_key}/result/{index + 1}"
        content = item.snippet or item.title or ""
        state.vfs[key] = content
        receipt_id, result_id = _result_identity(result, index)
        state.sources[ref] = Source(
            ref=ref,
            key=key,
            title=item.title or item.link,
            url=item.link,
            content=content,
            receipt_id=receipt_id,
            result_id=result_id,
            preview_chars=preview_chars,
        )
        items.append(
            {
                "source_ref": f"[{ref}]",
                "vfs_key": key,
                "title": item.title,
                "url": item.link,
                "text": state.bounded_preview(
                    key,
                    max_serialized_chars=preview_chars,
                ),
            }
        )
    return {"ok": True, "vfs_key": parent_key, "results": items}


async def _execute_fetch(
    state: ResearchState,
    args: dict[str, Any],
    preview_budget_chars: int | None = None,
) -> dict[str, Any]:
    url = str(args["url"]).strip()
    if re.search(r"\.(?:xls|xlsx|xlsb)(?:[?#]|$)", url, flags=re.IGNORECASE):
        raise ValueError(
            "fetch_page cannot expose spreadsheet binary rows to VFS tools; search the "
            "same publisher for a CSV, HTML, or plain-text companion"
        )
    result = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=FETCH_TIMEOUT)
    _capture_budget(state, result)
    state.page_count += 1
    items: list[dict[str, Any]] = []
    preview_chars = 8_000
    if preview_budget_chars is not None:
        preview_chars = min(
            preview_chars,
            max(300, preview_budget_chars // max(1, len(result.response.data))),
        )
    for index, item in enumerate(result.response.data):
        ref = f"P{state.page_count + index}"
        key = f"page://{item.url}"
        state.vfs[key] = item.content
        receipt_id, result_id = _result_identity(result, index)
        state.sources[ref] = Source(
            ref=ref,
            key=key,
            title=item.title or item.url,
            url=item.url,
            content=item.content,
            receipt_id=receipt_id,
            result_id=result_id,
            preview_chars=preview_chars,
        )
        item_payload = {
            "source_ref": f"[{ref}]",
            "vfs_key": key,
            "title": item.title,
            "url": item.url,
        }
        if len(item.content) > preview_chars:
            lexical_context = _execute_lexical_context(
                state,
                {"query": state.question, "targets": [key]},
            )
            item_payload["question_context"] = {
                "instruction": (
                    "These are the long page regions most relevant to the original question. Inspect them before "
                    "issuing another page search or read."
                ),
                "windows": lexical_context["windows"],
            }
        item_payload["text"] = state.bounded_preview(
            key,
            max_serialized_chars=preview_chars,
        )
        items.append(item_payload)
    state.page_count += max(0, len(result.response.data) - 1)
    return {"ok": True, "pages": items}


def _resolve_line_bound(
    state: ResearchState,
    key: str,
    value: Any,
    default: int,
) -> int:
    """Turn a vfs_read bound into a 0-based line index.

    Accepts None, a blank/null placeholder, a stable line ID, or a 1-based line
    number. Lifted out of _execute_read so the resolver is an ordinary top-level
    function rather than a closure rebuilt on every read.
    """
    text = "" if value is None else str(value).strip()
    if value is None or text.lower() in {"", "null", "none"}:
        return default
    location = state.line_locations.get(text)
    if location is not None:
        if location[0] != key:
            raise ValueError(f"line ID {value} belongs to {location[0]}, not {key}")
        return location[1]
    line_number_match = re.fullmatch(r"L?(\d+)", text, flags=re.IGNORECASE)
    if line_number_match is None:
        raise ValueError(f"unknown line bound: {value}; use a displayed line ID or 1-based line number")
    return max(0, int(line_number_match.group(1)) - 1)


def _execute_read(
    state: ResearchState,
    args: dict[str, Any],
    *,
    remember_focused: bool = True,
) -> dict[str, Any]:
    key = str(args["key"])
    if key not in state.vfs:
        raise ValueError(f"unknown VFS key: {key}")

    lines = state.vfs[key].splitlines() or [""]
    start = _resolve_line_bound(state, key, args.get("start_line"), 0)
    end = _resolve_line_bound(state, key, args.get("end_line"), len(lines) - 1)
    if start >= len(lines):
        raise ValueError(f"start_line is beyond the file; {key} has {len(lines)} lines")
    if end < start:
        raise ValueError("end_line must not precede start_line")
    requested_end = min(len(lines) - 1, end)
    selected_indices: list[int] = []
    response_chars = 0
    for index in range(start, requested_end + 1):
        estimated_chars = len(lines[index]) + 80
        if selected_indices and response_chars + estimated_chars > VFS_READ_PAGE_CHARS:
            break
        selected_indices.append(index)
        response_chars += estimated_chars
    selected = selected_indices
    source_refs = [f"[{source.ref}]" for source in state.sources.values() if source.key == key]
    next_index = selected[-1] + 1 if selected else start
    truncated = next_index <= requested_end
    next_line_id = None
    if truncated:
        next_line_id = state._line_id(key, next_index, lines[next_index])
        state.line_locations[next_line_id] = (key, next_index)
    if remember_focused:
        state.remember_focused_lines(key, selected)
    return {
        "ok": True,
        "key": key,
        "source_refs": source_refs,
        "lines": state.render_lines(key, selected),
        "truncated": truncated,
        "next_start_line": next_index + 1 if truncated else None,
        "next_start_line_id": next_line_id,
    }


def _execute_list(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
    prefix = str(args["prefix"])
    keys = [key for key in state.vfs if key.startswith(prefix)]
    return {"ok": True, "keys": keys}


def _execute_write(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
    key = str(args["key"])
    if key == "*":
        raise ValueError("'*' cannot be a VFS key")
    state.forget_focused_lines(key)
    state.vfs[key] = str(args["content"])
    return {"ok": True, "key": key, "chars": len(state.vfs[key])}


def _execute_delete(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
    key = str(args["key"])
    existed = key in state.vfs
    state.forget_focused_lines(key)
    state.vfs.pop(key, None)
    return {"ok": True, "key": key, "deleted": existed}


def _numeric_literals(text: str) -> set[str]:
    literals: set[str] = set()
    for match in re.finditer(r"(?<![\w.])\d+(?:[,.]\d+)*%?", text):
        prefix = text[: match.start()].rstrip()
        if prefix.endswith(("<", ">")):
            continue
        if re.search(
            r"(?:above|below|greater than|less than|lower than|more than|threshold(?: of)?)\s*$",
            prefix,
            flags=re.IGNORECASE,
        ):
            continue
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if len(digits) < 2 and not any(marker in raw for marker in (",", ".", "%")):
            continue
        literals.add(raw.rstrip("%").replace(",", ""))
    return literals


def _validate_retained_numeric_evidence(
    state: ResearchState,
    source: Source,
    note: str,
    selected_lines: list[dict[str, Any]],
) -> None:
    claim_text = re.sub(
        (
            r"\blines?\s+(?:L[0-9a-f]{10}|\d+)"
            r"(?:\s*(?:-|to|through)\s*(?:L[0-9a-f]{10}|\d+))?"
            r"(?:\s*\(L[0-9a-f]{10}\))?"
        ),
        "",
        note,
        flags=re.IGNORECASE,
    )
    note_numbers = _numeric_literals(claim_text)
    selected_numbers = _numeric_literals(
        "\n".join(str(item["text"]) for item in selected_lines)
    )
    missing = note_numbers - selected_numbers
    if not missing:
        return

    source_lines = state.vfs[source.key].splitlines() or [""]
    locations: dict[str, list[str]] = {}
    for number in sorted(missing):
        matching_indices = [
            index
            for index, line in enumerate(source_lines)
            if number in _numeric_literals(line)
        ]
        if not matching_indices:
            if number in _numeric_literals(source.title):
                locations[number] = [
                    "source title only; choose a source whose citable body contains this value"
                ]
            continue
        locations[number] = [
            f"line {index + 1} ({state._line_id(source.key, index, source_lines[index])})"
            for index in matching_indices[:3]
        ]
    if not locations:
        return
    details = "; ".join(
        f"{number}: {', '.join(line_locations)}"
        for number, line_locations in locations.items()
    )
    raise ValueError(
        "the selected evidence span omits numeric facts asserted by note that are present "
        f"elsewhere in this source ({details}). Re-read those lines and retry "
        "retain_evidence with a span containing the supporting text"
    )


def _execute_retain_evidence(
    state: ResearchState,
    args: dict[str, Any],
) -> dict[str, Any]:
    source_identifier = str(args["source"]).strip().strip("[]")
    source = state.sources.get(source_identifier)
    if source is None:
        source = next(
            (candidate for candidate in state.sources.values() if candidate.key == source_identifier),
            None,
        )
    if source is None:
        if source_identifier in state.vfs and re.fullmatch(r"search://\d+", source_identifier):
            raise ValueError(
                f"{args['source']} is a search-result container, not a citable source; "
                "use the displayed [Sx.y] source reference or search://N/result/y child key "
                "that contains the supporting text"
            )
        raise ValueError(f"unknown source reference or VFS key: {args['source']}")
    start_line = args.get("start_line")
    end_line = args.get("end_line")
    if start_line is None or end_line is None:
        raise ValueError("start_line and end_line are required")
    read_output = _execute_read(
        state,
        {
            "key": source.key,
            "start_line": start_line,
            "end_line": end_line,
        },
        remember_focused=False,
    )
    note = str(args["note"]).strip()
    _validate_retained_numeric_evidence(state, source, note, read_output["lines"])
    line_ids = " ".join(str(item["line_id"]) for item in read_output["lines"])
    previous_slices = list(state.source_slices.get(source.ref, []))

    packet = state.source_packet(
        f"{source.ref} {line_ids}",
        allow_preview=False,
        include_structured_csv=True,
        prefer_retained=False,
    )
    if not packet:
        raise RuntimeError(f"could not build evidence packet for source {source.ref}")
    state.source_slices[source.ref] = _merge_citation_slices(
        previous_slices,
        list(state.source_slices.get(source.ref, [])),
    )
    retained = packet[0]
    retained["research_note"] = note
    existing = state.retained_evidence.get(source.ref)
    if existing is not None:
        retained = _merge_source_packets([existing], [retained])[0]
        previous_note = str(existing.get("research_note", "")).strip()
        retained["research_note"] = "\n".join(
            item for item in (previous_note, note) if item
        )
    state.retained_evidence[source.ref] = retained
    retained_indices = {
        state.line_locations[str(item["line_id"])][1]
        for item in read_output["lines"]
        if str(item["line_id"]) in state.line_locations
    }
    state.forget_focused_lines(source.key, retained_indices)
    return {"ok": True, "source_ref": f"[{source.ref}]"}


def _execute_discard_remaining_sources(
    state: ResearchState,
    args: dict[str, Any],
) -> dict[str, Any]:
    reason = str(args["reason"]).strip()
    if not reason:
        raise ValueError("reason must not be blank")
    discarded_refs = set(state.review_source_refs)
    discarded_source_count = len(discarded_refs)
    state.review_source_refs.clear()
    retained_keys = {state.sources[ref].key for ref in state.retained_evidence if ref in state.sources}
    for ref in discarded_refs:
        source = state.sources.get(ref)
        if source is not None and source.key not in retained_keys:
            state.forget_focused_lines(source.key)
    return {"ok": True, "discarded_source_count": discarded_source_count}


def _markdown_table_context(
    state: ResearchState,
    key: str,
    match_index: int,
) -> dict[str, Any] | None:
    lines = state.vfs[key].splitlines() or [""]
    separator_index: int | None = None
    for index in range(match_index, 0, -1):
        if re.fullmatch(r"\s*\|(?:\s*:?-+:?\s*\|)+\s*", lines[index]):
            separator_index = index
            break
        if index < match_index and lines[index].lstrip().startswith("#"):
            break
    if separator_index is None:
        return None

    header_index = separator_index - 1
    end_index = separator_index
    for index in range(separator_index + 1, len(lines)):
        if not lines[index].lstrip().startswith("|"):
            break
        end_index = index
    return {
        "start_line": header_index + 1,
        "end_line": end_index + 1,
        "header": state.render_lines(key, range(header_index, separator_index + 1)),
    }


def _execute_regex(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
    pattern = re.compile(str(args["pattern"]))
    keys = state.resolve_targets([str(item) for item in args["targets"]])
    cursor_value = args.get("cursor")
    cursor = 0 if cursor_value is None else int(cursor_value)
    if cursor < 0:
        raise ValueError("cursor must be at least zero")
    raw_matches: list[tuple[str, dict[str, Any]]] = []
    for key in keys:
        for item in state.render_lines(key):
            if pattern.search(item["text"]):
                raw_matches.append((key, item))

    matches: list[dict[str, Any]] = []
    page_chars = 0
    for key, item in raw_matches[cursor:]:
        match = {"key": key, **item}
        source_refs = [f"[{source.ref}]" for source in state.sources.values() if source.key == key]
        if source_refs:
            match["source_refs"] = source_refs
        table_context: dict[str, Any] | None = None
        csv_records = state.structured_csv_records(
            key,
            [0, item["line"] - 1],
        )
        if csv_records:
            match.pop("text")
            match["csv_record"] = csv_records[0]
        else:
            table_context = _markdown_table_context(
                state,
                key,
                item["line"] - 1,
            )
            if table_context is not None:
                match["table"] = table_context
        focused_indices = {item["line"] - 1}
        if table_context is not None:
            focused_indices.update(
                int(header_line["line"]) - 1
                for header_line in table_context["header"]
            )
        if source_refs:
            state.remember_focused_lines(key, focused_indices)
        matches.append(match)
        page_chars += len(json.dumps(match, ensure_ascii=False, separators=(",", ":")))
        if page_chars >= VFS_SEARCH_PAGE_CHARS:
            break

    next_offset = cursor + len(matches)
    next_cursor = next_offset if next_offset < len(raw_matches) else None
    return {
        "ok": True,
        "matched_keys": keys,
        "total_match_count": len(raw_matches),
        "cursor": cursor,
        "matches": matches,
        "next_cursor": next_cursor,
    }


def _chunks(state: ResearchState, keys: list[str]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for key in keys:
        content = state.vfs[key]
        start = 0
        index = 0
        while start < len(content):
            end = min(len(content), start + 3_000)
            chunks.append(
                {
                    "key": key,
                    "chunk": index,
                    "start": start,
                    "end": end,
                    "text": content[start:end],
                }
            )
            if end == len(content):
                break
            start = end - 300
            index += 1
    return chunks


_LEXICAL_WORD_RE = re.compile(r"[a-z0-9][a-z0-9'.\-]{2,}")
_LONG_QUOTED_PHRASE_RE = re.compile(r'"([^"]{24,})"|(?<![a-z0-9])\'([^\']{24,})\'', re.IGNORECASE)
_LEXICAL_STOP_WORDS = frozenset(
    "the and for with from that this have has was were are is been its their which what when where who how many much "
    "according also into over under between during against about after before while other more most than".split()
)


def _lexical_terms(text: str) -> set[str]:
    return {
        word
        for word in _LEXICAL_WORD_RE.findall(text.casefold())
        if word not in _LEXICAL_STOP_WORDS
    }


def _long_quoted_phrases(text: str) -> list[str]:
    return [
        next(group for group in match.groups() if group is not None).strip()
        for match in _LONG_QUOTED_PHRASE_RE.finditer(text)
    ]


def _exact_phrase_windows(text: str, phrases: list[str]) -> list[tuple[int, int, str]]:
    windows: list[tuple[int, int, str]] = []
    lowered = text.casefold()
    leading_chars = (VFS_LEXICAL_WINDOW_CHARS * 3) // 4
    for phrase in phrases:
        search_from = 0
        normalized_phrase = phrase.casefold()
        while True:
            match_start = lowered.find(normalized_phrase, search_from)
            if match_start < 0:
                break
            start = max(0, match_start - leading_chars)
            end = min(len(text), start + VFS_LEXICAL_WINDOW_CHARS)
            start = max(0, end - VFS_LEXICAL_WINDOW_CHARS)
            if not any(start < existing_end and existing_start < end for existing_start, existing_end, _ in windows):
                windows.append((start, end, phrase))
            search_from = match_start + len(normalized_phrase)
    return windows


def _lexical_window_scan_rank(item: tuple[int, int]) -> tuple[int, int]:
    """Most matched terms first, then earliest offset."""
    return (-item[0], item[1])


def _lexical_windows(text: str, terms: set[str]) -> list[tuple[int, int, int]]:
    if not text or not terms:
        return []
    if len(text) <= VFS_LEXICAL_WINDOW_CHARS:
        return [(0, len(text), sum(term in text.casefold() for term in terms))]

    step = max(600, VFS_LEXICAL_WINDOW_CHARS // 3)
    lowered = text.lower()
    scored: list[tuple[int, int]] = []
    start = 0
    while start < len(text):
        window = lowered[start : start + VFS_LEXICAL_WINDOW_CHARS]
        scored.append((sum(term in window for term in terms), start))
        if start + VFS_LEXICAL_WINDOW_CHARS >= len(text):
            break
        start += step
    scored.sort(key=_lexical_window_scan_rank)

    selected: list[tuple[int, int, int]] = []
    for matched_term_count, start in scored:
        if len(selected) >= VFS_LEXICAL_WINDOW_COUNT:
            break
        end = min(len(text), start + VFS_LEXICAL_WINDOW_CHARS)
        if any(start < selected_end and selected_start < end for selected_start, selected_end, _ in selected):
            continue
        if selected and matched_term_count == 0:
            continue
        selected.append((start, end, matched_term_count))
    return sorted(selected)


def _lexical_context_rank(item: dict[str, Any]) -> tuple[bool, int, str, int]:
    """Exact-phrase windows first, then most matched terms, then key and offset."""
    return (
        item["exact_phrase"] is None,
        -int(item["matched_term_count"]),
        str(item["key"]),
        int(item["start"]),
    )


def _execute_lexical_context(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
    keys = state.resolve_targets([str(item) for item in args["targets"]])
    terms = _lexical_terms(f"{state.question}\n{args['query']}")
    phrases = _long_quoted_phrases(state.question)
    windows: list[dict[str, Any]] = []
    for key in keys:
        content = state.vfs[key]
        selected: list[tuple[int, int, int, str | None]] = [
            (start, end, len(terms), phrase)
            for start, end, phrase in _exact_phrase_windows(content, phrases)
        ]
        for start, end, matched_term_count in _lexical_windows(content, terms):
            if any(
                start < selected_end and selected_start < end
                for selected_start, selected_end, _, _ in selected
            ):
                continue
            selected.append((start, end, matched_term_count, None))
        for start, end, matched_term_count, exact_phrase in selected:
            start_line = content[:start].count("\n")
            end_line = content[:end].count("\n") + 1
            windows.append(
                {
                    "key": key,
                    "start": start,
                    "end": end,
                    "matched_term_count": matched_term_count,
                    "exact_phrase": exact_phrase,
                    "lines": state.render_lines(key, range(start_line, end_line)),
                }
            )
    windows.sort(key=_lexical_context_rank)
    return {"ok": True, "matched_keys": keys, "windows": windows[:VFS_LEXICAL_WINDOW_COUNT]}


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


async def _embed_guarded(
    state: ResearchState,
    text: Any,
    *,
    input_type: str,
) -> Any:
    """Call embed_text with a deadline-narrowed timeout and a local hard ceiling.

    Mirrors _call_model_guarded. The timeout argument may never fire while a
    provider is still trickling out a response, and vfs_search makes two of these
    calls back to back, so an unguarded pair could spend the whole remaining wall
    on retrieval alone. Below the absolute wall this narrows nothing: the budget is
    min(EMBEDDING_TIMEOUT, time left), which equals EMBEDDING_TIMEOUT for any call
    starting with more than 120s in hand.
    """
    timeout = _deadline_timeout(
        state.started_at,
        EMBEDDING_TIMEOUT,
        floor=EMBEDDING_TIMEOUT_FLOOR_SECONDS,
    )
    try:
        return await asyncio.wait_for(
            embed_text(
                text,
                provider="openrouter",
                model=EMBEDDING_MODEL,
                input_type=input_type,
                provider_extra=EMBEDDING_EXTRA,
                timeout=timeout,
            ),
            timeout=max(5.0, timeout + LLM_TIMEOUT_LOCAL_SLACK_SECONDS),
        )
    except asyncio.TimeoutError as error:
        # _execute_vfs_search catches this and degrades to the regex result, so a
        # slow embedding provider costs recall rather than the whole task.
        raise TimeoutError(
            f"{input_type} embedding timed out after {timeout:.1f}s local ceiling"
        ) from error


def _embedding_index(item: Any) -> Any:
    """Restore provider-independent ordering of a batched embedding response."""
    return item.index


def _similarity_score(item: dict[str, Any]) -> Any:
    return item["score"]


async def _execute_similarity(state: ResearchState, args: dict[str, Any]) -> dict[str, Any]:
    keys = state.resolve_targets([str(item) for item in args["targets"]])
    embedded_chunks: list[tuple[dict[str, Any], list[float]]] = []
    missing_chunks: list[dict[str, Any]] = []
    missing_cache_keys: list[tuple[str, str]] = []
    missing_chunk_counts: list[int] = []
    for key in keys:
        cache_key = (key, hashlib.sha256(state.vfs[key].encode()).hexdigest())
        cached = state.document_embeddings.get(cache_key)
        if cached is not None:
            embedded_chunks.extend(cached)
            continue
        chunks = _chunks(state, [key])
        missing_cache_keys.append(cache_key)
        missing_chunk_counts.append(len(chunks))
        missing_chunks.extend(chunks)

    if not embedded_chunks and not missing_chunks:
        return {"ok": True, "matched_keys": keys, "chunks": []}
    query_result = await _embed_guarded(
        state,
        str(args["query"]),
        input_type="query",
    )
    if missing_chunks:
        document_result = await _embed_guarded(
            state,
            [chunk["text"] for chunk in missing_chunks],
            input_type="document",
        )
        vectors = [
            item.embedding
            for item in sorted(document_result.response.data, key=_embedding_index)
        ]
        if len(vectors) != len(missing_chunks):
            raise RuntimeError(
                f"embedding result count mismatch: expected {len(missing_chunks)}, received {len(vectors)}"
            )
        offset = 0
        for cache_key, chunk_count in zip(missing_cache_keys, missing_chunk_counts, strict=True):
            cached = list(
                zip(
                    missing_chunks[offset : offset + chunk_count],
                    vectors[offset : offset + chunk_count],
                    strict=True,
                )
            )
            state.document_embeddings[cache_key] = cached
            embedded_chunks.extend(cached)
            offset += chunk_count

    query_vector = query_result.response.data[0].embedding
    scored = [
        {**chunk, "score": _cosine(query_vector, vector)}
        for chunk, vector in embedded_chunks
    ]
    scored.sort(key=_similarity_score, reverse=True)
    output: list[dict[str, Any]] = []
    output_chars = 0
    for item in scored[:VFS_SIMILARITY_MAX_CHUNKS]:
        key = item["key"]
        content_before = state.vfs[key][: item["start"]]
        start_line = content_before.count("\n")
        line_count = item["text"].count("\n") + 1
        result_item = {
            "key": key,
            "chunk": item["chunk"],
            "score": item["score"],
            "lines": state.render_lines(key, range(start_line, start_line + line_count)),
        }
        source_refs = [f"[{source.ref}]" for source in state.sources.values() if source.key == key]
        if source_refs:
            result_item["source_refs"] = source_refs
        result_chars = len(
            json.dumps(
                result_item,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        if (
            len(output) >= VFS_SIMILARITY_MIN_CHUNKS
            and output_chars + result_chars > VFS_SIMILARITY_RESULT_CHARS
        ):
            break
        if source_refs:
            state.remember_focused_lines(
                key,
                range(start_line, start_line + line_count),
            )
        output.append(result_item)
        output_chars += result_chars
    return {"ok": True, "matched_keys": keys, "chunks": output}


async def _execute_vfs_search(
    state: ResearchState,
    args: dict[str, Any],
) -> dict[str, Any]:
    regex_result: dict[str, Any] | None = None
    regex_error: str | None = None
    try:
        regex_result = _execute_regex(state, args)
    except (TypeError, ValueError, re.error) as error:
        regex_error = str(error)

    similarity_trigger: str | None = None
    if regex_result is None:
        similarity_trigger = "regex_error"
    elif int(regex_result["total_match_count"]) == 0:
        similarity_trigger = "no_regex_matches"

    similarity_result: dict[str, Any] | None = None
    similarity_error: str | None = None
    if similarity_trigger is not None:
        try:
            similarity_result = await _execute_similarity(state, args)
        except Exception as error:
            similarity_error = str(error)

    if regex_result is None and similarity_result is None:
        raise RuntimeError(
            "both VFS search methods failed: "
            f"regex={regex_error or 'unknown'}; similarity={similarity_error or 'unknown'}"
        )

    output: dict[str, Any] = {
        "ok": True,
        "similarity": {
            "status": "not_run",
            "reason": "regex_returned_matches_on_first_search",
        },
    }
    if regex_result is not None:
        output["regex"] = {
            key: value
            for key, value in regex_result.items()
            if key not in {"ok", "matched_keys"}
        }
    if regex_error is not None:
        output["regex_error"] = regex_error
    if similarity_result is not None:
        output["similarity"] = {"status": "completed", "trigger": similarity_trigger}
        output["similarity"].update(
            {
                key: value
                for key, value in similarity_result.items()
                if key not in {"ok", "matched_keys"}
            }
        )
    if similarity_error is not None:
        output["similarity"] = {
            "status": "failed",
            "trigger": similarity_trigger,
            "error": similarity_error,
        }
    return output


async def _execute_tool(
    state: ResearchState,
    name: str,
    args: dict[str, Any],
    preview_budget_chars: int | None = None,
) -> dict[str, Any]:
    if name in {"search_web", "fetch_page"}:
        cached = state.retrieval_output_cache.get(_retrieval_signature(name, args))
        if cached is not None:
            return {**cached, "cached": True}
    if name == "search_web":
        return await _execute_search(state, args, preview_budget_chars)
    if name == "fetch_page":
        return await _execute_fetch(state, args, preview_budget_chars)
    if name == "vfs_read":
        return _execute_read(state, args)
    if name == "vfs_list":
        return _execute_list(state, args)
    if name == "vfs_write":
        return _execute_write(state, args)
    if name == "vfs_delete":
        return _execute_delete(state, args)
    if name == "retain_evidence":
        return _execute_retain_evidence(state, args)
    if name == "discard_remaining_sources":
        return _execute_discard_remaining_sources(state, args)
    if name == "vfs_search":
        return await _execute_vfs_search(state, args)
    if name == "update_research_state":
        research_state = str(args["state"]).strip()
        if not research_state:
            raise ValueError("state must not be blank")
        state.research_state = research_state
        return {"ok": True}
    raise ValueError(f"unknown tool: {name}")


def _deduplicate_tool_calls(calls: list[Any]) -> tuple[list[Any], int]:
    unique_calls: list[Any] = []
    seen: set[tuple[str, str]] = set()
    for call in calls:
        try:
            arguments = json.dumps(
                json.loads(call.arguments),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except json.JSONDecodeError:
            arguments = call.arguments
        signature = (call.name, arguments)
        if signature in seen:
            continue
        seen.add(signature)
        unique_calls.append(call)
    return unique_calls, len(calls) - len(unique_calls)


async def _finalize_answer(
    *,
    state: ResearchState,
    question: str,
    current_answer: str,
    reason: str,
    assistant_context: str,
    last_packet: list[dict[str, Any]],
    final_source_slices: dict[str, list[CitationSlice]],
) -> tuple[str, list[dict[str, Any]]]:
    finalization_context = "\n\n".join(
        value
        for value in (
            state.research_state.strip(),
            reason.strip(),
            assistant_context.strip(),
        )
        if value
    )
    packet = state.source_packet(
        finalization_context,
        include_structured_csv=True,
    )
    if not packet:
        raise ValueError(
            "final answer must mention at least one observed source reference such as S1.2 or P1"
        )
    unretained_page_refs = [
        str(item["source_ref"])
        for item in packet
        if str(item["source_ref"]).strip("[]").startswith("P")
        and str(item["source_ref"]).strip("[]") not in state.retained_evidence
    ]
    if unretained_page_refs:
        raise ValueError(
            "fetched-page evidence must be preserved before finalization; call retain_evidence "
            f"for each decisive excerpt from {', '.join(unretained_page_refs)}, then retry"
        )
    for item in packet:
        ref = str(item["source_ref"])[1:-1]
        final_source_slices[ref] = _merge_citation_slices(
            final_source_slices.get(ref, []),
            list(state.source_slices.get(ref, [])),
        )
    precise_refs = {str(item["source_ref"]) for item in [*last_packet, *packet]}
    retained_packet = [
        item
        for item in state.retained_evidence.values()
        if str(item["source_ref"]) not in precise_refs
    ]
    merged_packet = _merge_source_packets(last_packet, retained_packet)
    merged_packet = _merge_source_packets(merged_packet, packet)
    merged_packet = [
        item
        for item in merged_packet
        if (
            (source := state.sources.get(str(item["source_ref"]).strip("[]")))
            and source.receipt_id
            and source.result_id
        )
    ]
    if not merged_packet:
        raise ValueError(
            "none of the selected source records can be materialized as response citations"
        )
    answer = await _answer_text(
        state=state,
        question=question,
        prior_answer=current_answer,
        requirements=state.evidence_requirements or "",
        research_state=state.research_state,
        finalization_reason=reason,
        packet=merged_packet,
    )
    return answer, merged_packet


def _emergency_close(
    *,
    state: ResearchState,
    question: str,
    current_answer: str,
    last_packet: list[dict[str, Any]],
    final_source_slices: dict[str, list[CitationSlice]],
    final_audit: str,
) -> tuple[str, list[CitationRef]]:
    """Always return something from what is on hand once time runs out.

    No exception escapes. Raising during investigation locks in a zero, whereas
    returning even a thinly supported answer can still earn partial credit.
    """
    try:
        plan = state.citation_plan(
            current_answer,
            last_packet,
            final_source_slices,
            final_audit,
        )
    except Exception:
        plan = CitationPlan(citations=[], source_indices={})
    try:
        return _safe_render_public_citations(
            current_answer,
            plan,
            unadorned_output=_requires_unadorned_output(question),
        )
    except Exception:
        return _strip_all_private_refs(current_answer), []


def _research_progress_signature(state: ResearchState) -> tuple[Any, ...]:
    return (
        state.evidence_requirements,
        tuple(sorted(state.sources)),
        tuple(
            (key, tuple(sorted(indices)))
            for key, indices in sorted(state.focused_lines.items())
        ),
        tuple(sorted(state.retained_evidence)),
        state.research_state,
        state.audit_gap,
    )


def _investigation_models(
    state: ResearchState,
    deadline_notice_sent: bool,
    switch_reason: str,
) -> tuple[str, ...]:
    if MODEL_SCHEDULING != "state_aware":
        return REPAIR_MODELS if state.audit_gap else INVESTIGATION_MODELS
    if state.audit_gap or deadline_notice_sent or switch_reason:
        return REPAIR_MODELS
    return STATE_AWARE_INVESTIGATION_MODELS


def _requirements_models(
    deadline_notice_sent: bool,
    switch_reason: str,
) -> tuple[str, ...]:
    if MODEL_SCHEDULING == "state_aware" and (deadline_notice_sent or switch_reason):
        return REPAIR_MODELS
    return REQUIREMENTS_MODELS


@dataclass
class AuditOutcome:
    """Result of the post-finalization audit round."""

    current_answer: str
    final_audit: str
    audit_ready: bool
    audit_continue_rounds: int
    messages: list[Any]


async def _run_finalization_audit(
    *,
    state: ResearchState,
    question: str,
    current_answer: str,
    last_packet: list[dict[str, Any]],
    messages: list[Any],
    investigation_started_at: float,
    audit_continue_rounds: int,
) -> AuditOutcome:
    """Audit the finalized answer and decide whether the task can close.

    The audit is a quality step, not the step that produces the answer. The audit
    call, the VERDICT parse, and the REVISE validation are each guarded, so a format
    violation by the audit model discards only the audit rather than scoring a
    finished answer zero. On CONTINUE the returned messages are a fresh transcript
    naming the single gap; every other verdict leaves the transcript untouched.
    """
    final_audit = ""
    audit_ready = True
    audit_elapsed = time.monotonic() - investigation_started_at
    if audit_elapsed >= TIME_GOVERNOR_ABSOLUTE_SECONDS:
        # No time left for an audit. Confirm the current answer as it stands.
        final_audit = ""
        state.audit_gap = ""
        audit_ready = True
        verdict, audit_payload = "READY", ""
    else:
        try:
            final_audit = await _audit(
                state,
                question,
                current_answer,
                last_packet,
            )
            verdict, audit_payload = _parse_audit(final_audit)
        except Exception:
            final_audit = ""
            verdict, audit_payload = "READY", ""
    if verdict == "CONTINUE" and audit_continue_rounds >= MAX_AUDIT_CONTINUE_ROUNDS:
        # Audit round-trip ceiling. The original allowed CONTINUE without limit,
        # letting the audit and re-investigation feed each other and burn the
        # entire time budget.
        verdict, audit_payload = "READY", ""
        final_audit = ""
    if verdict == "CONTINUE":
        audit_continue_rounds += 1
        state.audit_gap = audit_payload
        state.clear_focused_lines()
        audit_ready = False
        messages = [
            {"role": "system", "content": INVESTIGATION_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Original question:\n{question}\n\n"
                    "The finalization audit found one unresolved evidence gap:\n"
                    f"{audit_payload}\n\n"
                    "The harness will preserve the existing VFS, source references, "
                    "retained evidence, retrieval receipts, and research state. Resolve "
                    "this exact gap with the smallest useful next observation, update the "
                    "research state if the answer changes, then finalize. Do not restart "
                    "the investigation or repeat already supported premises."
                ),
            }
        ]
    elif verdict == "REVISE":
        allowed_refs = {
            str(item["source_ref"]).strip("[]")
            for item in last_packet
            if isinstance(item, dict) and item.get("source_ref")
        }
        try:
            _validate_private_answer_refs(
                audit_payload,
                allowed_refs,
                require_ref=not _requires_unadorned_output(question),
            )
        except ValueError:
            # The replacement answer from the audit violated the format. Abandon
            # the replacement and keep the existing answer, which already passed
            # validation. The original raised here and lost the sound answer too.
            final_audit = ""
        else:
            current_answer = audit_payload
        state.audit_gap = ""
        audit_ready = True
    else:
        state.audit_gap = ""
        audit_ready = True
    return AuditOutcome(
        current_answer=current_answer,
        final_audit=final_audit,
        audit_ready=audit_ready,
        audit_continue_rounds=audit_continue_rounds,
        messages=messages,
    )


@dataclass
class TurnOutcome:
    """Everything one assistant turn's tool calls changed in the investigation."""

    current_answer: str
    last_packet: list[dict[str, Any]]
    ready_requested: bool
    call_signatures: list[str]
    failure_signatures: list[str]


async def _execute_turn_calls(
    *,
    state: ResearchState,
    question: str,
    calls: list[Any],
    assistant: Any,
    messages: list[Any],
    requirements_pending: bool,
    current_answer: str,
    last_packet: list[dict[str, Any]],
    final_source_slices: dict[str, list[CitationSlice]],
) -> TurnOutcome:
    """Run one turn's deduplicated tool calls and append their results to messages.

    Lifted verbatim out of the investigation loop, which had grown past 550 lines.
    Every failure is converted into an ok=False tool result rather than propagating,
    so this never alters the loop's control flow; the caller decides what to do with
    ready_requested and the two signature lists.
    """
    ready_requested = False
    turn_call_signatures: list[str] = []
    turn_failure_signatures: list[str] = []
    retrieval_call_count = sum(call.name in {"search_web", "fetch_page"} for call in calls)
    retrieval_preview_budget = (
        BATCHED_RETRIEVAL_PREVIEW_CHARS // retrieval_call_count if retrieval_call_count else None
    )
    for call_index, call in enumerate(calls):
        call_signature = json.dumps(
            {"tool": call.name, "raw_arguments": call.arguments},
            ensure_ascii=False,
            sort_keys=True,
        )
        try:
            args = json.loads(call.arguments)
            if not isinstance(args, dict):
                raise ValueError("tool arguments must be a JSON object")
            call_signature = json.dumps(
                {"tool": call.name, "arguments": args},
                ensure_ascii=False,
                sort_keys=True,
            )
            if call.name == "set_evidence_requirements":
                if not requirements_pending or len(calls) != 1:
                    raise ValueError("set_evidence_requirements must be the sole call before retrieval")
                requirements = str(args["requirements"]).strip()
                if not requirements:
                    raise ValueError("requirements must not be empty")
                state.evidence_requirements = requirements
                output = {"ok": True}
            elif call.name == "ready_to_finalize":
                if turn_failure_signatures:
                    raise ValueError(
                        "cannot finalize in the same response after an earlier tool call "
                        "failed; inspect that tool feedback, correct the failed operation, "
                        "and retry finalization"
                    )
                incompatible_calls = [
                    candidate.name
                    for candidate in calls
                    if candidate.name not in {"update_research_state", "retain_evidence", "ready_to_finalize"}
                ]
                if incompatible_calls:
                    raise ValueError(
                        "ready_to_finalize may only accompany update_research_state and retain_evidence; "
                        f"also received {', '.join(incompatible_calls)}"
                    )
                if call_index != len(calls) - 1:
                    raise ValueError("ready_to_finalize must be the final call in the response")
                reason = str(args["reason"])
                current_answer, last_packet = await _finalize_answer(
                    state=state,
                    question=question,
                    current_answer=current_answer,
                    reason=reason,
                    assistant_context=_assistant_evidence_context(assistant),
                    last_packet=last_packet,
                    final_source_slices=final_source_slices,
                )
                # final_audit and audit_ready are reset by the caller from
                # ready_requested; the finalization audit reassigns both anyway.
                ready_requested = True
                output = {
                    "ok": True,
                    "answer_checkpoint": current_answer,
                }
            elif call.name == "discard_remaining_sources":
                if call_index != len(calls) - 1:
                    raise ValueError("discard_remaining_sources must be the last call in the response")
                output = await _execute_tool(
                    state,
                    call.name,
                    args,
                    retrieval_preview_budget,
                )
            else:
                output = await _execute_tool(
                    state,
                    call.name,
                    args,
                    retrieval_preview_budget,
                )
                _record_retrieval_receipt(state, call.name, args, output)
                _record_vfs_operation_receipt(state, call.name, args, output)
        except Exception as error:
            output = {
                "ok": False,
                "error_type": (
                    "tool_argument_validation"
                    if isinstance(error, (KeyError, TypeError, ValueError, json.JSONDecodeError))
                    else "tool_execution"
                ),
                "details": str(error),
            }
        turn_call_signatures.append(call_signature)
        if not output.get("ok"):
            turn_failure_signatures.append(
                json.dumps(
                    {
                        "tool": call.name,
                        "error_type": output.get("error_type"),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(output, ensure_ascii=False),
            }
        )
    return TurnOutcome(
        current_answer=current_answer,
        last_packet=last_packet,
        ready_requested=ready_requested,
        call_signatures=turn_call_signatures,
        failure_signatures=turn_failure_signatures,
    )


def _next_switch_reason(
    *,
    current_calls: tuple[str, ...],
    current_failures: tuple[str, ...],
    previous_call_signatures: tuple[str, ...],
    progress_before: tuple[Any, ...],
    progress_after: tuple[Any, ...],
) -> str:
    """Name the reason to redirect the next turn, or "" when the turn made progress.

    Pure function of the turn's call signatures and the research-progress signature
    taken either side of the turn.
    """
    if current_failures:
        return (
            "The previous model's tool call failed. Read the detailed tool feedback, correct "
            "that exact operation or choose a different valid operation, and advance the "
            "investigation without repeating the failure."
        )
    if (
        current_calls
        and current_calls == previous_call_signatures
        and progress_after == progress_before
    ):
        return (
            "The previous model repeated the same operations without adding evidence or changing "
            "the research state. Choose a different evidence route."
        )
    if current_calls and not current_failures and progress_after == progress_before:
        return (
            "The previous operations succeeded mechanically but produced no new retained evidence, "
            "source coverage, inspected lines, or research-state change. Choose the smallest different "
            "operation that can resolve the current uncertainty."
        )
    return ""


def _governor_decision(
    state: ResearchState,
    elapsed_seconds: float,
    *,
    requirements_pending: bool,
    governor_turns: int,
) -> tuple[str, bool, int]:
    """Resolve the stage for one investigation turn.

    Returns (stage, past_absolute_wall, governor_turns). The absolute wall is
    decided first: the two downgrade rules below are right for spend protection but
    must not apply to time protection. Forcing the stage back to "open" whenever
    (a) no sources had been gathered or (b) the closing turns were spent would leave
    the 210s hard threshold inert, and those are exactly the situations most likely
    to cross the 300s hard wall and score zero.
    """
    past_absolute_wall = elapsed_seconds >= TIME_GOVERNOR_ABSOLUTE_SECONDS
    stage = "open" if requirements_pending else _governor_stage(state, elapsed_seconds)
    # With no evidence at all, the retrieval tools must not be withdrawn: withdrawing
    # them cannot produce an answer and locks in a zero. Keep searching even at the
    # cost of more budget.
    if not state.sources and not past_absolute_wall:
        stage = "open"
    if stage != "open":
        governor_turns += 1
    # The closing turns are spent and the task still has not closed. Keeping the tools
    # withheld would end worse than carrying on with the full tool set. Spend
    # protection is best-effort and accuracy comes first.
    if governor_turns > SPEND_GOVERNOR_MAX_CLOSING_TURNS and not past_absolute_wall:
        stage = "open"
    # Past the absolute wall, ignore every downgrade and pin the stage to hard.
    if past_absolute_wall:
        stage = "hard"
    return stage, past_absolute_wall, governor_turns


async def _investigate(question: str, expected_answer: str) -> tuple[str, list[CitationRef]]:
    investigation_started_at = time.monotonic()
    deadline_notice_sent = False
    state = ResearchState(question)
    state.research_state = (
        f"Current best answer hypothesis:\n{expected_answer}\n"
        "Observed support: none yet.\n"
        "Most important unresolved question: test the hypothesis against external evidence."
    )
    current_answer = expected_answer
    messages: list[Any] = [
        {"role": "system", "content": INVESTIGATION_SYSTEM},
        {
            "role": "user",
            "content": (f"Original question:\n{question}\n\nExpected answer hypothesis:\n{expected_answer}"),
        },
    ]
    last_packet: list[dict[str, Any]] = []
    final_source_slices: dict[str, list[CitationSlice]] = {}
    final_audit = ""
    switch_reason = ""
    previous_call_signatures: tuple[str, ...] = ()
    governor_notice_sent = False
    governor_bypass_failed = False
    governor_turns = 0
    audit_continue_rounds = 0
    model_failure_streak = 0

    for _turn in range(160):
        if (
            not deadline_notice_sent
            and time.monotonic() - investigation_started_at >= DEADLINE_NOTICE_SECONDS
        ):
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "The external runtime has about 150 seconds remaining. Preserve answer quality. "
                        "If the observed evidence can support the answer, retain any needed excerpts and call "
                        "ready_to_finalize now. If one decisive uncertainty remains, perform only the single "
                        "operation most likely to resolve it, then finalize. Do not restart broad research."
                    ),
                }
            )
            deadline_notice_sent = True
        _refresh_retrieval_receipt_message(messages, state)
        requirements_pending = state.evidence_requirements is None
        governor_elapsed = time.monotonic() - investigation_started_at
        governor_stage, past_absolute_wall, governor_turns = _governor_decision(
            state,
            governor_elapsed,
            requirements_pending=requirements_pending,
            governor_turns=governor_turns,
        )
        if past_absolute_wall:
            # Retry the direct close even if an earlier hard close failed. The only
            # remaining options are closing now or overrunning the hard wall for a
            # zero.
            governor_bypass_failed = False
        if (
            governor_stage == "hard"
            and not governor_bypass_failed
            and _closable_source_refs(state)
        ):
            # Spend or elapsed time crossed the hard threshold. Spend no further model
            # turns; the harness closes directly on the evidence gathered so far.
            try:
                current_answer, last_packet = await _finalize_answer(
                    state=state,
                    question=question,
                    current_answer=current_answer,
                    reason=(
                        "The harness closed the investigation because the observed session "
                        "spend or elapsed time reached the governor ceiling. Answer from the "
                        "evidence already retained."
                    ),
                    assistant_context=_closable_source_context(state),
                    last_packet=last_packet,
                    final_source_slices=final_source_slices,
                )
            except (ValueError, RuntimeError) as error:
                # Direct closure is not possible in this state (for example evidence was
                # never retained). Raising here would kill the whole task and lock in a
                # zero, so downgrade to soft and let the model fix it with the closing
                # tools.
                governor_bypass_failed = True
                switch_reason = (
                    "Observed session spend reached the governor ceiling and the harness "
                    f"could not close the investigation directly: {error}. Resolve that exact "
                    "problem with the closing tools and finalize now."
                )
            else:
                plan = state.citation_plan(
                    current_answer,
                    last_packet,
                    final_source_slices,
                    final_audit,
                )
                return _safe_render_public_citations(
                    current_answer,
                    plan,
                    unadorned_output=_requires_unadorned_output(question),
                )
        if past_absolute_wall:
            # Past the absolute wall and the direct close above did not succeed (no
            # citable source, or _finalize_answer failed). One more model turn would
            # cross the 300s hard wall for a certain zero. Go out with what is on hand.
            return _emergency_close(
                state=state,
                question=question,
                current_answer=current_answer,
                last_packet=last_packet,
                final_source_slices=final_source_slices,
                final_audit=final_audit,
            )
        if requirements_pending:
            available_tools = REQUIREMENTS_TOOLS
            available_models = _requirements_models(
                deadline_notice_sent,
                switch_reason,
            )
        elif governor_stage == "open":
            available_tools = TOOLS
            available_models = _investigation_models(
                state,
                deadline_notice_sent,
                switch_reason,
            )
        else:
            # soft/hard: withdraw the retrieval tools. tool_choice is required, so the
            # model has no option but to pick one of the closing tools.
            available_tools = CLOSING_TOOLS
            available_models = REPAIR_MODELS
            if not governor_notice_sent:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Observed session spend reached the governor threshold. Retrieval "
                            "tools are withdrawn for the rest of this task. Retain any excerpt "
                            "the answer still needs, update the research state if the answer "
                            "changed, and call ready_to_finalize in this response."
                        ),
                    }
                )
                governor_notice_sent = True
        request_messages = (
            [
                {"role": "system", "content": REQUIREMENTS_SYSTEM},
                {"role": "user", "content": f"Original question:\n{question}"},
            ]
            if requirements_pending
            else messages
        )
        try:
            result = await _chat_with_scheduling(
                available_models,
                messages=request_messages,
                tools=available_tools,
                tool_choice="required",
                parallel_tool_calls=True,
                timeout=_deadline_timeout(investigation_started_at, LLM_TIMEOUT),
                max_output_tokens=None,
            )
        except Exception as error:
            # Every ladder rung failed. In the original the exception escaped here and
            # scored the task zero. Close on the sources already gathered if there are
            # any; otherwise retry on the next turn while it is still early.
            if _closable_source_refs(state) or past_absolute_wall:
                if _closable_source_refs(state):
                    try:
                        current_answer, last_packet = await _finalize_answer(
                            state=state,
                            question=question,
                            current_answer=current_answer,
                            reason=(
                                "The harness closed the investigation because every "
                                "configured model failed. Answer from the evidence "
                                "already retained."
                            ),
                            assistant_context=_closable_source_context(state),
                            last_packet=last_packet,
                            final_source_slices=final_source_slices,
                        )
                    except Exception:
                        pass
                return _emergency_close(
                    state=state,
                    question=question,
                    current_answer=current_answer,
                    last_packet=last_packet,
                    final_source_slices=final_source_slices,
                    final_audit=final_audit,
                )
            model_failure_streak += 1
            if model_failure_streak >= MAX_CONSECUTIVE_MODEL_FAILURES:
                raise
            switch_reason = (
                "The previous model call failed entirely: "
                f"{error}. Choose the smallest valid operation that advances the "
                "investigation."
            )
            continue
        model_failure_streak = 0
        _capture_budget(state, result)
        _compact_consumed_assistant_reasoning(messages)
        _compact_consumed_tool_results(messages)
        assistant = _assistant_message(result)
        state.remember_reasoning_observation(assistant.reasoning)
        calls, duplicate_call_count = _deduplicate_tool_calls(list(assistant.tool_calls or ()))
        if not calls:
            prose = (result.llm.raw_text or "").strip()
            if prose:
                try:
                    current_answer, last_packet = await _finalize_answer(
                        state=state,
                        question=question,
                        current_answer=current_answer,
                        reason=prose,
                        assistant_context=_assistant_evidence_context(assistant),
                        last_packet=last_packet,
                        final_source_slices=final_source_slices,
                    )
                except ValueError as error:
                    switch_reason = (
                        "The previous model tried to finalize without materializable support. "
                        f"Resolve this exact problem before finalizing again: {error}"
                    )
                    messages.extend(
                        [
                            assistant.to_input_message(),
                            {
                                "role": "user",
                                "content": (
                                    f"Your terminal answer could not be finalized: {error}. "
                                    "Use tools to resolve that exact problem, then either return a "
                                    "supported terminal answer or call ready_to_finalize."
                                ),
                            },
                        ]
                    )
                    continue
                plan = state.citation_plan(
                    current_answer,
                    last_packet,
                    final_source_slices,
                    final_audit,
                )
                return _safe_render_public_citations(
                    current_answer,
                    plan,
                    unadorned_output=_requires_unadorned_output(question),
                )
            messages.extend(
                [
                    assistant.to_input_message(),
                    {
                        "role": "user",
                        "content": "Use a tool. Call ready_to_finalize only when inspected sources support the answer.",
                    },
                ]
            )
            switch_reason = (
                "The previous model returned neither a tool call nor a usable terminal answer. "
                "Choose the smallest valid operation that advances the investigation."
            )
            continue
        assistant_input = replace(
            assistant,
            tool_calls=tuple(calls),
        ).to_input_message()
        messages.append(assistant_input)
        progress_before = _research_progress_signature(state)
        outcome = await _execute_turn_calls(
            state=state,
            question=question,
            calls=calls,
            assistant=assistant,
            messages=messages,
            requirements_pending=requirements_pending,
            current_answer=current_answer,
            last_packet=last_packet,
            final_source_slices=final_source_slices,
        )
        current_answer = outcome.current_answer
        last_packet = outcome.last_packet
        ready_requested = outcome.ready_requested
        turn_call_signatures = outcome.call_signatures
        turn_failure_signatures = outcome.failure_signatures
        audit_ready = ready_requested
        if ready_requested:
            final_audit = ""
        if duplicate_call_count:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"The previous response repeated {duplicate_call_count} exact tool "
                        "calls. The harness executed each distinct call once. Continue from "
                        "those results without repeating an identical call."
                    ),
                }
            )
        if ready_requested:
            audit_outcome = await _run_finalization_audit(
                state=state,
                question=question,
                current_answer=current_answer,
                last_packet=last_packet,
                messages=messages,
                investigation_started_at=investigation_started_at,
                audit_continue_rounds=audit_continue_rounds,
            )
            current_answer = audit_outcome.current_answer
            final_audit = audit_outcome.final_audit
            audit_ready = audit_outcome.audit_ready
            audit_continue_rounds = audit_outcome.audit_continue_rounds
            messages = audit_outcome.messages
        if MODEL_SCHEDULING == "state_aware" and not ready_requested:
            current_calls = tuple(turn_call_signatures)
            next_switch_reason = _next_switch_reason(
                current_calls=current_calls,
                current_failures=tuple(turn_failure_signatures),
                previous_call_signatures=previous_call_signatures,
                progress_before=progress_before,
                progress_after=_research_progress_signature(state),
            )
            if next_switch_reason:
                messages.append({"role": "user", "content": next_switch_reason})
            switch_reason = next_switch_reason
            previous_call_signatures = current_calls
        if ready_requested and audit_ready:
            plan = state.citation_plan(
                current_answer,
                last_packet,
                final_source_slices,
                final_audit,
            )
            return _safe_render_public_citations(
                current_answer,
                plan,
                unadorned_output=_requires_unadorned_output(question),
            )

    # The turn ceiling is spent. The original raised RuntimeError here, discarding
    # every piece of evidence and every answer candidate gathered so far for a
    # certain zero. Instead, attempt one proper close and, failing that, go out with
    # what is on hand.
    if _closable_source_refs(state):
        try:
            current_answer, last_packet = await _finalize_answer(
                state=state,
                question=question,
                current_answer=current_answer,
                reason=(
                    "The harness closed the investigation because the turn ceiling was "
                    "reached. Answer from the evidence already retained."
                ),
                assistant_context=_closable_source_context(state),
                last_packet=last_packet,
                final_source_slices=final_source_slices,
            )
        except Exception:
            pass
    return _emergency_close(
        state=state,
        question=question,
        current_answer=current_answer,
        last_packet=last_packet,
        final_source_slices=final_source_slices,
        final_audit=final_audit,
    )


@entrypoint("query")
async def query(query: Query) -> Response:
    task_started_at = time.monotonic()
    # Hypothesis generation is a convenience step. Investigation can proceed without
    # it, so a non-retryable error must not kill the task. The original re-raised
    # non-retryable errors, leaving a path that scored zero without ever starting the
    # investigation.
    try:
        expected_answer = await _expected_answer_text(query.text)
    except Exception:
        expected_answer = (
            "No expected-answer hypothesis was available because its model call "
            "failed. Investigate the original question directly and construct a "
            "revisable answer from observed external evidence."
        )
    answer, citations = await _investigate(query.text, expected_answer)
    if query.output_schema is not None:
        # When structured-output materialization failed, the original raised and threw
        # away the entire research result. Return the prose answer even when the schema
        # cannot be enforced.
        try:
            output = await _materialize_structured_output(
                question=query.text,
                answer=answer,
                output_schema=query.output_schema,
                started_at=task_started_at,
            )
        except Exception:
            return Response(text=answer, citations=citations)
        return Response(output=output, citations=citations)
    return Response(text=answer, citations=citations)

# slot: harnyx 2026-08-09T14:08:00+00:00

# perfect_suffix: openrouter/parallel
_PERFECT_SUFFIX = "f1b4736718b385dc"

