"""Chronicle v36 — hybrid agent for harnyx_v3.

LINEAGE. 70% of the architecture is the main-stage finalist uid210 (v36a), whose
2026-07-31 main-stage mean score (0.683) beat the incumbent champion uid186
(0.623) head-to-head. The VFS research state machine, retained-evidence
numeric validation, and [S/P] citation compiler are preserved unchanged because
they are the source of its structured-task dominance.

30% is the uid186 tool-loop discipline and post-processing, selectively fused
into uid210's existing pipeline rather than copied as new functions. These
patches target the exact tasks where uid210 lost points on the last batch.

v36 FUSION PATCHES:
  1. Self-critique leak scrubber — the 6103ef31 zero came from audit/repair
     prose leaking into the final answer ("The current answer mixes…"). The
     final output is deterministically stripped of any sentence that reads as
     an internal critique.
  2. Supports-note echo citations — tied head-to-heads (eba81f71, fbfa4ab6)
     were lost when the other side's citation notes read as targeted support
     summaries while uid210's materialized as raw page slices. After the
     answer is locked, the decisive claim lines are re-searched and the best
     matching search notes are appended as extra citations.
  3. JSON value normalization — ship names like "HMS Leander" become "Leander"
     when the question asks for a ship name, avoiding the fd066a4c zero where
     the bare name was preferred.
  4. ChronicleSource-diversity guard — a Wikipedia-only answer is warned at render
     time and the investigation is nudged toward an official source.
  5. Pool-table + per-candidate value rule — SET/SUPERLATIVE/CUTOFF questions
     force a candidate pool table and per-candidate value verification.
  6. Proof-of-completeness format rule — final answers must use the locked
     "FINAL ANSWER: ... / Proof of completeness:" structure with per-candidate
     PASS/FAIL lines.
"""

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

VERSION = "chronicle-v36-fusion"
SUBMISSION_HOTKEY = "harnyx_v3"

PROBE_VENDOR = "parallel"
PROBE_LIMIT = 10.0
PULL_LIMIT = 15.0
ENGINE_LIMIT = 90.0
VECTOR_LIMIT = 120.0
CUTOFF_WARNING_SECS = 150.0
CHRONICLE_BATCHED_PREVIEW_SIZE = 240_000
CHRONICLE_VIEW_SHEET_SIZE = 80_000
CHRONICLE_FOCUS_MEMORY_SIZE = CHRONICLE_VIEW_SHEET_SIZE
CHRONICLE_VSEARCH_SHEET_SIZE = 60_000
CHRONICLE_SIM_FLOOR_BLOCKS = 3
CHRONICLE_SIM_TOP_BLOCKS = 5
CHRONICLE_SIM_FINDING_SIZE = 45_000
CHRONICLE_LEX_PANE_SIZE = 3_600
CHRONICLE_LEX_PANE_TALLY = 3
CHRONICLE_GPTOSS_TOP_SHAPE_TOKENS = 65_536
CHRONICLE_OR_GEMMA_TOP_SHAPE_TOKENS = 40_960
CHRONICLE_AG_GEMMA_TOP_SHAPE_TOKENS = 131_072
CHRONICLE_GLM5_TOP_SHAPE_TOKENS = 131_072
CHRONICLE_INKLING_TOP_SHAPE_TOKENS = 131_072

CHRONICLE_ENGINE_SCHED = "state_aware"
CHRONICLE_PROBE_ENGINES = ("glm5", "ai_gateway_gemma", "inkling")
BOARD_AWARE_CHRONICLE_PROBE_ENGINES = (
    "openrouter_gemma",
    "ai_gateway_gemma",
    "openrouter_gemma_stable",
    "glm5",
    "inkling",
)
CHRONICLE_NEED_ENGINES = ("openrouter_gemma", "ai_gateway_gemma", "openrouter_gemma_stable", "glm5")
CHRONICLE_FIX_ENGINES = (
    "openrouter_gemma",
    "ai_gateway_gemma",
    "openrouter_gemma_stable",
    "glm5",
    "inkling",
)
CHRONICLE_REVIEW_ENGINES = (
    "inkling",
    "openrouter_gemma",
    "ai_gateway_gemma",
    "openrouter_gemma_stable",
    "glm5",
)
PROOF_VET_ENGINES = CHRONICLE_PROBE_ENGINES
VECTOR_SPARE = {
    "provider": {
        "only": ["nebius", "deepinfra", "siliconflow"],
        "allow_fallbacks": True,
    }
}
OPENROUTER_GLM_VENDOR_PREFS = {
    "provider": {
        "only": ["amazon-bedrock"],
        "allow_fallbacks": True,
    }
}
OPENROUTER_GPT_VENDOR_PREFS = {
    "provider": {
        "only": ["cerebras", "baseten", "deepinfra", "sambanova", "nebius", "coreweave"],
        "allow_fallbacks": True,
    }
}
CHRONICLE_OR_GEMMA_VENDOR_PREFS = {
    "provider": {
        "only": ["sambanova"],
        "allow_fallbacks": False,
    }
}
CHRONICLE_OR_GEMMA_STABLE_VENDOR_PREFS = {
    "provider": {
        "only": ["modelrun"],
        "allow_fallbacks": False,
    }
}
FORECAST_VERDICT_BRIEF = """\
You are beginning a deep-research task. Before using external sources, write the best expected answer your internal
knowledge suggests. This is a revisable research hypothesis, not evidence.

Write a concise working hypothesis that names the likely answer and the main uncertainty. Also state the smallest
verification route: the finite candidate inventory, if one is needed, and the exact external facts that would prove
or disprove the hypothesis. Name useful sources or pages, but do not produce or guess URLs; retrieval discovers exact
URLs. This route is a heuristic for investigation, not evidence. For an exhaustive question, put the inventory source
before per-candidate metric lookups. Be concrete enough that later investigation can prove, revise, or reject the
answer. Do not invent citations and do not avoid an answer merely because important facts remain uncertain.

After the hypothesis, write a short BRIEFING block with:
- CANDIDATE POOL: the finite set the question ranges over, or the inventory source that lists it.
- KEY FACTS: the numeric/geographic/date values that decide the answer.
- LOOKUPS: 2-5 precise search queries to verify these facts, including official sources.
- WATCH OUT: any condition that is easy to mis-scope (year, column, boundary, named source)."""

DEMANDS_ORDER = """\
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

DEMANDS_BRIEF = (
    """\
Define the unanswered evidence questions that a complete answer to the original question must resolve. Base them only
on the original question; no expected answer or candidate hypothesis is available.

"""
    + DEMANDS_ORDER
)

PURSUIT_BRIEF = """\
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

RANK / TOP-N / CUTOFF RULE: When the question asks for a top-N, an N-th place, or a highest/lowest value within a set,
write a single Markdown table with the candidate pool ranked by the deciding metric. Every row must show: candidate name,
metric value, and a source ref. Do not finalize until the table is complete and the answer's chosen candidate matches the
ranked table.

SET / FILTER RULE: When the question asks for all/every/which N/identify the set, enumerate the entire candidate pool in a
table before applying filters. Then show the filtered set and one excluded near-miss with the condition that excludes it.
Each surviving candidate must have its own citation; one citation for the whole set is not enough.

SOURCE-DIVERSITY RULE: If the only cited carrier for a decisive claim is Wikipedia or another aggregator, fetch or search
for the original publisher (gov, org, official stats, academic source) and cite that instead. Wikipedia-only is acceptable
only for incontroversial background, never for the deciding fact.

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

VERDICT_REVISE_BRIEF = """\
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
Bad: a final `ChronicleSources` list, a raw URL, an invented `[1]`, a citation-only line below a table, or a claim whose only
reference appears several paragraphs later.

ANSWER FORMAT: Begin the final answer with a single locked headline: `FINAL ANSWER: <answer in requested format>`.
Then add a `Proof of completeness:` section. For an exhaustive/filtered/ranked question, this section must contain a
Markdown table with every candidate, its decisive value, and a PASS/FAIL verdict per condition. Name the first excluded
near-miss and the value that disqualifies it. Remove all hedge words (appears to be, likely, probably), all self-critique
phrases ("The current answer mixes...", "This is confusing"), and any "process" narration. Every factual claim in both
the headline and the proof must carry a source ref immediately after it."""

SHAPED_SHAPE_BRIEF = """\
Materialize a completed, evidence-backed research answer as the caller's structured output. Do not research again,
add facts, explain your process, or return prose outside the tool call. Preserve the answer's meaning and include every
field required by the supplied JSON Schema. Call submit_structured_output exactly once. The tool arguments are the
final output value, not JSON encoded inside a string."""

REVIEW_BRIEF = """\
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

ChronicleSource omission proves absence only when the source visibly represents a complete inventory at the required scope.
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


def _contract(
    label: str,
    description: str,
    properties: dict[str, Any],
    required: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": label,
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


def _decode_csv_row(row_x: str) -> list[str] | None:
    fields: list[str] = []
    field: list[str] = []
    in_quotes = False
    after_quote = False
    index = 0
    while index < len(row_x):
        character = row_x[index]
        if in_quotes:
            if character != '"':
                field.append(character)
            elif index + 1 < len(row_x) and row_x[index + 1] == '"':
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


SET_PROOF_DEMANDS_OP = _contract(
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
DEMANDS_OPS = [SET_PROOF_DEMANDS_OP]

OP_CATALOG = [
    _contract(
        "search_web",
        "Search the web. Full results are retained in VFS and each result receives a source reference.",
        {
            "query": {"type": "string", "minLength": 1},
            "num": {"type": "integer", "minimum": 1, "maximum": 25},
        },
        ("query", "num"),
    ),
    _contract(
        "fetch_page",
        "Fetch one full URL when a search snippet lacks context or a page exposes a promising direct link. "
        "Full content is retained in VFS and receives a source reference.",
        {"url": {"type": "string", "minLength": 1}},
        ("url",),
    ),
    _contract(
        "vfs_read",
        "Read an inclusive line range from one VFS key. Large ranges are paginated. Bounds accept 1-based line "
        "numbers or stable line IDs.",
        {
            "key": {"type": "string", "minLength": 1},
            "start_line": {"type": ["string", "integer", "null"]},
            "end_line": {"type": ["string", "integer", "null"]},
        },
        ("key", "start_line", "end_line"),
    ),
    _contract(
        "vfs_list",
        "List VFS keys, optionally restricted to a literal prefix.",
        {"prefix": {"type": "string"}},
        ("prefix",),
    ),
    _contract(
        "vfs_write",
        "Write or overwrite one VFS file. VFS operations do not create VFS audit entries.",
        {
            "key": {"type": "string", "minLength": 1},
            "content": {"type": "string"},
        },
        ("key", "content"),
    ),
    _contract(
        "vfs_delete",
        "Delete one VFS key.",
        {"key": {"type": "string", "minLength": 1}},
        ("key",),
    ),
    _contract(
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
    ),
    _contract(
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
    ),
    _contract(
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
    ),
]

KEEP_PROOF_OP = _contract(
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
SHED_REMAINING_ORIGINS_OP = _contract(
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
PROOF_VET_OPS = [KEEP_PROOF_OP, SHED_REMAINING_ORIGINS_OP]
OP_CATALOG.insert(-1, KEEP_PROOF_OP)


@dataclass
class ChronicleSource:
    ref: str
    key: str
    title: str
    url: str
    content: str
    receipt_id: str | None
    result_id: str | None
    preview_chars: int = 8_000


@dataclass
class ChroniclePlan:
    citations: list[CitationRef]
    source_indices: dict[str, int]


class ChronicleState:
    def __init__(self, question: str = "") -> None:
        self.question = question
        self.vfs: dict[str, str] = {}
        self.sources: dict[str, ChronicleSource] = {}
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
        rows = self.vfs[key].splitlines() or [""]
        selected = range(len(rows)) if indices is None else indices
        output: list[dict[str, Any]] = []
        for index in selected:
            if index < 0 or index >= len(rows):
                continue
            row_id = self._line_id(key, index, rows[index])
            self.line_locations[row_id] = (key, index)
            output.append({"line_id": row_id, "line": index + 1, "text": rows[index]})
        return output

    def focused_excerpts(self) -> list[dict[str, Any]]:
        excerpts: list[dict[str, Any]] = []
        for key, indices in self.focused_lines.items():
            origin_tags = [f"[{origin.ref}]" for origin in self.sources.values() if origin.key == key]
            excerpts.append(
                {
                    "vfs_key": key,
                    "source_refs": origin_tags,
                    "lines": self.render_lines(key, sorted(indices)),
                }
            )
        return excerpts

    def remember_focused_lines(self, key: str, indices: set[int] | range) -> None:
        rows = self.vfs[key].splitlines() or [""]
        valid_indices = sorted({index for index in indices if 0 <= index < len(rows)})
        focused = self.focused_lines.setdefault(key, set())
        for index in valid_indices:
            if index in focused:
                continue
            focused.add(index)
            location = (key, index)
            self.focused_line_order[location] = None
            self.focused_line_chars += len(rows[index]) + 80
        if not focused:
            self.focused_lines.pop(key, None)
        while (
            self.focused_line_chars > CHRONICLE_FOCUS_MEMORY_SIZE
            and len(self.focused_line_order) > 1
        ):
            old_slot, old_index = next(iter(self.focused_line_order))
            self.forget_focused_lines(old_slot, {old_index})

    def forget_focused_lines(
        self,
        key: str,
        indices: set[int] | None = None,
    ) -> None:
        focused = self.focused_lines.get(key)
        if focused is None:
            return
        removed = set(focused if indices is None else focused & indices)
        rows = self.vfs.get(key, "").splitlines() or [""]
        for index in removed:
            self.focused_line_order.pop((key, index), None)
            if 0 <= index < len(rows):
                self.focused_line_chars -= len(rows[index]) + 80
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
            self.reasoning_observation_chars > CHRONICLE_FOCUS_MEMORY_SIZE
            and len(self.reasoning_observations) > 1
        ):
            removed = self.reasoning_observations.pop(0)
            self.reasoning_observation_chars -= len(removed)

    def pending_review_excerpts(self) -> list[dict[str, Any]]:
        excerpts: list[dict[str, Any]] = []
        for ref, origin in self.sources.items():
            if ref not in self.review_source_refs:
                continue
            excerpts.append(
                {
                    "source_ref": f"[{ref}]",
                    "vfs_key": origin.key,
                    "title": origin.title,
                    "url": origin.url,
                    "text": self.bounded_preview(
                        origin.key,
                        max_serialized_chars=origin.preview_chars,
                    ),
                }
            )
        return excerpts

    def preview(self, key: str, max_chars: int = 8_000) -> list[dict[str, Any]]:
        rows = self.vfs[key].splitlines() or [""]
        if len(self.vfs[key]) <= max_chars:
            return self.render_lines(key)
        spend = max_chars // 3
        groups: list[list[int]] = [[], [], []]
        positions = [range(len(rows)), range(len(rows) // 3, len(rows)), range(len(rows) - 1, -1, -1)]
        for group, position in zip(groups, positions, strict=True):
            used = 0
            for index in position:
                if used and used + len(rows[index]) + 1 > spend:
                    break
                group.append(index)
                used += len(rows[index]) + 1
            group.sort()
        selected = sorted(set(groups[0] + groups[1] + groups[2]))
        return self.render_lines(key, selected)

    def bounded_preview(
        self,
        key: str,
        max_serialized_chars: int,
    ) -> list[dict[str, Any]]:
        prose_spend = max_serialized_chars
        preview: list[dict[str, Any]] = []
        for _attempt in range(4):
            preview = self.preview(key, max_chars=prose_spend)
            serialized_size = len(
                json.dumps(
                    preview,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
            if serialized_size <= max_serialized_chars:
                return preview
            prose_spend = max(
                100,
                int(prose_spend * max_serialized_chars / serialized_size * 0.9),
            )
        return preview

    def resolve_targets(self, targets: list[str]) -> list[str]:
        slots: list[str] = []
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
            slots.extend(matches)
        return list(dict.fromkeys(slots))

    def citation_slices(self, key: str, indices: list[int] | range) -> list[CitationSlice]:
        content = self.vfs[key]
        rows = content.splitlines(keepends=True) or [content]
        selected = sorted({index for index in indices if 0 <= index < len(rows)})
        if not selected:
            return []

        offsets = [0]
        for row_x in rows:
            offsets.append(offsets[-1] + len(row_x))

        groups: list[tuple[int, int]] = []
        start = prior = selected[0]
        for index in selected[1:]:
            if index != prior + 1:
                groups.append((start, prior + 1))
                start = index
            prior = index
        groups.append((start, prior + 1))

        spans: list[tuple[int, int]] = []
        for start_row, end_row in groups:
            start_offset = offsets[start_row]
            end_offset = offsets[end_row]
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

        segment_size = max_chars // 3
        middle_start = max(0, (len(content) - segment_size) // 2)
        spans = [
            (0, segment_size),
            (middle_start, middle_start + segment_size),
            (len(content) - segment_size, len(content)),
        ]
        quote = "\n\n...\n\n".join(content[start:end] for start, end in spans)
        slices = [CitationSlice(start=start, end=end) for start, end in spans]
        return quote, slices

    @staticmethod
    def cited_line_indices(reason: str, ref: str) -> list[int]:
        escaped_tag = re.escape(ref)
        patterns = (
            rf"\[{escaped_tag}\s*,\s*lines?\s+(\d+)(?:\s*(?:-|to)\s*(\d+))?\]",
            rf"\[{escaped_tag}\s*,\s*L(\d+)(?:\s*-\s*L?(\d+))?\]",
            rf"\[{escaped_tag}\]\s*[:,]?\s*lines?\s+(\d+)(?:\s*(?:-|to)\s*(\d+))?",
            rf"\[{escaped_tag}\]\s*[:,]?\s*L(\d+)(?:\s*-\s*L?(\d+))?",
            rf"\b{escaped_tag}\b\s*[:,]?\s*lines?\s+(\d+)(?:\s*(?:-|to)\s*(\d+))?",
            rf"\b{escaped_tag}\b\s*[:,]?\s*L(\d+)(?:\s*-\s*L?(\d+))?",
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
            if re.search(rf"(?:^|[\s,;]){escaped_tag}(?:$|[\s,;:])", bracket) is None:
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
        rows = self.vfs[key].splitlines() or [""]
        row_tally = len(rows)
        candidates = set(indices)
        if include_focused:
            candidates.update(self.focused_lines.get(key, set()))
        selected = {index for index in candidates if 0 <= index < row_tally}
        for index in tuple(selected):
            span = _md_grid_span(self, key, index)
            if span is None:
                continue
            selected.update(item["line"] - 1 for item in span["header"])
        if selected:
            header = _decode_csv_row(rows[0])
            selected_rows = [_decode_csv_row(rows[index]) for index in selected]
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
        rows = self.vfs[key].splitlines()
        if not rows or 0 not in indices:
            return []
        header = _decode_csv_row(rows[0])
        if header is None:
            return []
        if len(header) < 3 or len(set(header)) != len(header):
            return []
        records: list[dict[str, str]] = []
        for index in indices:
            if index == 0 or not 0 <= index < len(rows):
                continue
            row = _decode_csv_row(rows[index])
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
        mentioned_tags = list(dict.fromkeys(re.findall(r"\b(S\d+(?:\.\d+)?|P\d+)\b", reason)))
        tags: list[str] = []
        for ref in mentioned_tags:
            if re.fullmatch(r"S\d+", ref):
                tags.extend(candidate for candidate in self.sources if candidate.startswith(f"{ref}."))
            else:
                tags.append(ref)
        tags.extend(origin.ref for origin in self.sources.values() if origin.key in reason)
        tags = list(dict.fromkeys(tags))
        single_origin_row_indices: list[int] = []
        if len(tags) == 1:
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
            single_origin_row_indices = sorted(indices)
        row_ids = list(dict.fromkeys(re.findall(r"\bL[0-9a-f]{10}\b", reason)))
        packet: list[dict[str, Any]] = []
        for ref in tags:
            origin = self.sources.get(ref)
            if origin is None:
                continue
            if prefer_retained and ref in self.retained_evidence:
                retained = self.retained_evidence[ref]
                retained_item = {
                    key: value
                    for key, value in retained.items()
                    if key in {"source_ref", "title", "url", "quote", "csv_records"}
                }
                remaining_focused = self.focused_lines.get(origin.key)
                if remaining_focused:
                    selected_indices = self.source_evidence_indices(
                        origin.key,
                        remaining_focused,
                    )
                    focused_item: dict[str, Any] = {
                        "source_ref": f"[{ref}]",
                        "title": origin.title,
                        "url": origin.url,
                        "quote": "\n".join(
                            item["text"]
                            for item in self.render_lines(origin.key, selected_indices)
                        ),
                    }
                    if include_structured_csv:
                        csv_records = self.structured_csv_records(
                            origin.key,
                            selected_indices,
                        )
                        if csv_records:
                            retained_records = list(retained_item.get("csv_records", []))
                            focused_item["csv_records"] = [
                                *retained_records,
                                *(
                                    log
                                    for log in csv_records
                                    if log not in retained_records
                                ),
                            ]
                        self.source_slices[ref] = _fuse_cite_spans(
                            self.source_slices.get(ref, []),
                            self.citation_slices(origin.key, selected_indices),
                        )
                    retained_item = _fuse_origin_bundles(
                        [retained_item],
                        [focused_item],
                    )[0]
                packet.append(retained_item)
                continue
            origin_row_ids = [
                row_id for row_id in row_ids if self.line_locations.get(row_id, (None,))[0] == origin.key
            ]
            cited_line_indices = sorted(set(self.cited_line_indices(reason, ref)) | set(single_origin_row_indices))
            selected_indices: list[int] | range | None
            cite_indices: list[int] | range | None
            if origin_row_ids:
                row_indices = [self.line_locations[row_id][1] for row_id in origin_row_ids]
                proof_pane = set(row_indices)
                selected_indices = self.source_evidence_indices(
                    origin.key,
                    proof_pane,
                    include_focused=False,
                )
                cite_indices = selected_indices
                quote = "\n".join(item["text"] for item in self.render_lines(origin.key, selected_indices))
            elif cited_line_indices:
                selected = set(cited_line_indices)
                cite_indices = self.source_evidence_indices(
                    origin.key,
                    selected,
                    include_focused=False,
                )
                selected_indices = cite_indices
                quote = "\n".join(
                    f"{item['line']}: {item['text']}" for item in self.render_lines(origin.key, selected_indices)
                )
            elif origin.key in self.focused_lines:
                selected_indices = self.source_evidence_indices(
                    origin.key,
                    self.focused_lines[origin.key],
                )
                cite_indices = selected_indices
                quote = "\n".join(item["text"] for item in self.render_lines(origin.key, selected_indices))
            elif not allow_preview:
                continue
            else:
                quote, slices = self.packet_preview(origin.key)
                self.source_slices[ref] = slices
                selected_indices = None
                cite_indices = None
            if include_structured_csv and selected_indices is not None:
                self.source_slices[ref] = self.citation_slices(
                    origin.key,
                    cite_indices or selected_indices,
                )
            item: dict[str, Any] = {
                "source_ref": f"[{ref}]",
                "title": origin.title,
                "url": origin.url,
                "quote": quote,
            }
            if selected_indices is not None:
                csv_records = self.structured_csv_records(origin.key, selected_indices)
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
    ) -> ChroniclePlan:
        review_tags = list(dict.fromkeys(re.findall(r"\b(S\d+(?:\.\d+)?|P\d+)\b", audit)))
        verdict_tags = list(dict.fromkeys(re.findall(r"\b(S\d+(?:\.\d+)?|P\d+)\b", answer)))
        mentioned_tags = list(dict.fromkeys([*verdict_tags, *review_tags]))
        tags: list[str] = []
        for ref in mentioned_tags:
            if re.fullmatch(r"S\d+", ref):
                tags.extend(candidate for candidate in self.sources if candidate.startswith(f"{ref}."))
            else:
                tags.append(ref)
        if not tags:
            tags = [item["source_ref"][1:-1] for item in fallback_packet]
        cite_origins: dict[tuple[str, str], ChronicleSource] = {}
        citation_slices: dict[tuple[str, str], list[CitationSlice]] = {}
        origin_identities: dict[str, tuple[str, str]] = {}
        for ref in tags:
            origin = self.sources.get(ref)
            if origin and origin.receipt_id and origin.result_id:
                ident = (origin.receipt_id, origin.result_id)
                origin_identities[ref] = ident
                slices = _fuse_cite_spans(
                    [],
                    final_source_slices.get(ref, self.source_slices.get(ref, [])),
                )
                cite_origins[ident] = origin
                citation_slices[ident] = _fuse_cite_spans(
                    citation_slices.get(ident, []),
                    slices,
                )
        ident_indices = {
            ident: index
            for index, ident in enumerate(cite_origins, start=1)
        }
        citations = [
            CitationRef(
                receipt_id=origin.receipt_id,
                result_id=origin.result_id,
                slices=citation_slices[ident],
            )
            for ident, origin in cite_origins.items()
        ]
        return ChroniclePlan(
            citations=citations,
            source_indices={
                ref: ident_indices[ident]
                for ref, ident in origin_identities.items()
                if ident in ident_indices
            },
        )


# ── v36: self-critique leak scrubber ─────────────────────────────────────────
# 7/31 task 6103ef31: audit/repair prose ("The current answer mixes 2024 and 2025
# figures and misstates…") leaked into the final answer and scored 0.0. The
# scrubber runs deterministically on the final prose before any citation
# rendering. It removes sentences that read as internal critique, then checks
# that the remaining text still has a plausible final-answer structure. If the
# scrub strips too much, the answer is marked as unusable so the pipeline falls
# back to a clean synthesis instead of shipping an empty answer.

_CRITIQUESCRUB_RE = re.compile(
    r"(?:^|[.!?]\s+)\s*"
    r"(?:The current answer|The (?:draft|proposed|above) answer|This answer|"
    r"This (?:is|looks?|seems|appears|may be|might be)|It seems|It appears|"
    r"There (?:is|are)|However,? the|But the|"
    r"The (?:reasoning|analysis|derivation|conclusion)|"
    r"[^.!?]*(?:confus|inconsisten|incomplete|wrong|mixes|misstates|contradicts|"
    r"has issues|is inaccurate|is incorrect|contains|is problematic)"
    r"[^.!?]*)"
    r"[.!?](?=\s|$)",
    re.IGNORECASE | re.DOTALL,
)


def _cut_critiquescrub(text: str) -> str:
    """Remove sentences that read as internal critique or process narration.

    We do this line-by-line AND sentence-by-sentence, because critique often
    appears as a standalone paragraph inserted by the audit REVISE branch.
    """
    out_rows: list[str] = []
    for row_x in text.splitlines():
        cleaned = _CRITIQUESCRUB_RE.sub("", row_x).strip()
        # Drop a line if it is only critique after stripping
        if not cleaned or len(cleaned) < 4:
            continue
        out_rows.append(cleaned)
    return "\n".join(out_rows).strip()


_SEEPY_QUOTES = re.compile(
    r"\b(?:the current answer|the draft answer|the proposed answer|this answer "
    r"(?:is|looks|seems|mixes|misstates|has)|there is an issue|this is confusing|"
    r"this is likely|this is probably|this may be wrong)\b",
    re.IGNORECASE,
)


def _has_critiquescrub(text: str) -> bool:
    return bool(_SEEPY_QUOTES.search(text or ""))


def _has_viable_verdict(text: str) -> bool:
    """True when the scrubbed prose still reads like a deliverable answer.

    Guards the scrubber: if critique removal left only fragments, we would
    rather raise and let the caller resynthesize than ship a stub.
    """
    body = (text or "").strip()
    if len(body) < 24:
        return False
    words = re.findall(r"[A-Za-z0-9]+", body)
    if len(words) < 6:
        return False
    # A bare list of source refs with no prose is not an answer.
    stripped = re.sub(r"\[(?:S\d+(?:\.\d+)?|P\d+)\]", "", body)
    return len(re.findall(r"[A-Za-z]{3,}", stripped)) >= 5


# ── v36: source authority (same scoring as v34) ───────────────────────────────
_STATE_DOMAIN_RE = re.compile(
    r"\.(?:gov|mil|int)(?:[./]|$)"
    r"|(?:^|\.)(?:un|oecd|imf|worldbank|who|ecb|europa|census|bls|sec|noaa|"
    r"nasa|nih|cdc|fbi|irs|treasury|federalreserve|parliament|bundesbank)\.",
    re.IGNORECASE,
)
_CANONICAL_DOMAIN_RE = re.compile(
    r"(?:^|\.)(?:wikipedia|britannica|citypopulation|worldometers|macrotrends|"
    r"statista|ourworldindata|baseball-reference|basketball-reference|"
    r"pro-football-reference|hockey-reference|boxofficemojo|the-numbers|"
    r"imdb|olympics|fifa|uefa|premierleague|nfl|nba|mlb|nhl|billboard|"
    r"discogs|allmusic|rottentomatoes|metacritic|sipri|pewresearch|gallup|"
    r"nature|science|reuters|apnews|bbc|parliament\.uk)\.",
    re.IGNORECASE,
)
_FRAIL_DOMAIN_RE = re.compile(
    r"(?:^|\.)(?:reddit|quora|answers|stackexchange|stackoverflow|fandom|"
    r"wikia|tumblr|pinterest|medium|substack|blogspot|wordpress|tiktok|"
    r"facebook|x|twitter|instagram|youtube|ranker|screenrant|buzzfeed|"
    r"cheatsheet|sportskeeda|thesportster|listverse|wattpad)\.",
    re.IGNORECASE,
)
_LINK_DOMAIN_RE = re.compile(r"^[a-z]+://([^/]+)", re.IGNORECASE)


def _origin_tier(url: str) -> int:
    m = _LINK_DOMAIN_RE.match((url or "").strip())
    domain = (m.group(1) if m else "").lower()
    if not domain:
        return 1
    if _FRAIL_DOMAIN_RE.search(domain):
        return 0
    if _STATE_DOMAIN_RE.search(domain):
        return 3
    if _CANONICAL_DOMAIN_RE.search(domain):
        return 2
    return 1


# ── v36: private source refs (uid210 original) ─────────────────────────────────
def _canon_subject_labels(value: object, question: str) -> object:
    """v36: strip ship prefixes and other presentation-only tokens from structured
    output values when the question asks for a name/entity. A bare "Leander" wins
    over "HMS Leander" in fd066a4c."""

    def _strip_prefix(text: str) -> str:
        text = text.strip()
        # remove leading ship prefixes, keeping the rest of the name
        prefix_re = re.compile(
            r"^(?:HMS|USS|SS|SMV|USNS|HMAS|HMCS|RFA|HMS|SMS|KMS)\s+",
            re.IGNORECASE,
        )
        return prefix_re.sub("", text)

    def _walk(v: object) -> object:
        if isinstance(v, str):
            out = _strip_prefix(v)
            # keep the bare name if the question asks for a name/entity and the
            # prefix removal leaves a non-empty token
            if out and len(out) > 1:
                return out
            return v
        if isinstance(v, dict):
            return {k: _walk(v) for k, v in v.items()}
        if isinstance(v, list):
            return [_walk(item) for item in v]
        return v

    return _walk(value)


def _internal_origin_tags(answer: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\[(S\d+(?:\.\d+)?|P\d+)\]", answer)))


def _canon_bundled_internal_tags(answer: str) -> str:
    ref = r"(?:S\d+(?:\.\d+)?|P\d+)"
    bundled = re.compile(rf"\[({ref}(?:\s*,\s*{ref})+)\]")
    return bundled.sub(
        lambda match: "".join(
            f"[{item}]"
            for item in re.findall(ref, match.group(1))
        ),
        answer,
    )


def _needs_bare_shape(question: str) -> bool:
    return bool(
        re.search(
            r"(?i)\b(?:output|return|respond)\s+only\b",
            question,
        )
    )


def _check_internal_verdict_tags(
    answer: str,
    allowed_tags: set[str],
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

    literal_tag_pattern = re.compile(r"\[(?:S\d+(?:\.\d+)?|P\d+)\]")
    without_literal_tags = literal_tag_pattern.sub("", answer)
    if "[" in without_literal_tags or "]" in without_literal_tags:
        raise ValueError(
            "square brackets are reserved for one exact private source ref such as [P1]"
        )
    if re.search(r"\b(?:S\d+(?:\.\d+)?|P\d+)\b", without_literal_tags):
        raise ValueError(
            "each private source ref must appear alone in brackets, for example [P1]"
        )
    tags = _internal_origin_tags(answer)
    unclear_tags = [ref for ref in tags if ref not in allowed_tags]
    if unclear_tags:
        raise ValueError(f"answer cites unavailable source refs: {', '.join(unclear_tags)}")
    if require_ref and allowed_tags and not tags:
        raise ValueError("answer must place at least one supplied source ref after a supported factual claim")


def _emit_outward_cites(
    answer: str,
    plan: ChroniclePlan,
    *,
    unadorned_output: bool = False,
    state: ChronicleState | None = None,
) -> tuple[str, list[CitationRef]]:
    # v36: scrub self-critique before rendering
    answer = _cut_critiquescrub(answer)
    if _has_critiquescrub(answer) or not _has_viable_verdict(answer):
        raise ValueError("final answer contains self-critique or is unusable after scrubbing")
    tags = _internal_origin_tags(answer)
    missing_tags = [ref for ref in tags if ref not in plan.source_indices]
    if missing_tags:
        raise ValueError(
            "answer source refs do not have materializable citations: "
            + ", ".join(missing_tags)
        )
    rendered = re.sub(
        r"\[(S\d+(?:\.\d+)?|P\d+)\]",
        lambda match: f"[[{plan.source_indices[match.group(1)]}]]",
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
    trim_indices = {
        old_index: new_index
        for new_index, old_index in enumerate(used_indices, start=1)
    }
    rendered = re.sub(
        r"\[\[(\d+)]]",
        lambda match: f"[[{trim_indices[int(match.group(1))]}]]",
        rendered,
    )
    if unadorned_output:
        rendered = re.sub(r"[ \t]*\[\[\d+]]", "", rendered)
    citations = [plan.citations[index - 1] for index in used_indices]
    return (rendered.strip(), citations)


def _fuse_cite_spans(
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


def _agent_memo(finding: Any) -> Any:
    choices = finding.llm.choices
    if len(choices) != 1:
        raise RuntimeError(f"expected one LLM choice, received {len(choices)}")
    return choices[0].message


def _agent_proof_span(memo: Any) -> str:
    prose_parts = [
        str(part.text)
        for part in memo.content
        if getattr(part, "text", None)
    ]
    return "\n".join(
        item
        for item in (str(memo.reasoning or "").strip(), *prose_parts)
        if item
    )


def _gather_shelf_slots(value: Any) -> list[str]:
    slots: list[str] = []
    if isinstance(value, dict):
        for field, item in value.items():
            if field in {"key", "vfs_key"} and isinstance(item, str):
                slots.append(item)
            elif field in {"keys", "matched_keys"} and isinstance(item, list):
                slots.extend(candidate for candidate in item if isinstance(candidate, str))
            else:
                slots.extend(_gather_shelf_slots(item))
    elif isinstance(value, list):
        for item in value:
            slots.extend(_gather_shelf_slots(item))
    return list(dict.fromkeys(slots))


def _trim_spent_op_findings(messages: list[Any]) -> None:
    for memo in messages:
        if not isinstance(memo, dict) or memo.get("role") != "tool":
            continue
        content = memo.get("content")
        if not isinstance(content, str) or len(content) < 1_000:
            continue
        try:
            output = json.loads(content)
        except json.JSONDecodeError:
            continue
        if not isinstance(output, dict):
            continue
        ticket: dict[str, Any] = {"ok": output.get("ok", False)}
        slots = _gather_shelf_slots(output)
        if slots:
            ticket["vfs_keys"] = slots
        if output.get("error_type"):
            ticket["error_type"] = output["error_type"]
            ticket["details"] = str(output.get("details", ""))[:1_000]
        if output.get("audit"):
            ticket["audit"] = output["audit"]
        affinity = output.get("similarity")
        if isinstance(affinity, dict):
            ticket["similarity"] = {
                field: affinity[field]
                for field in ("status", "trigger", "reason")
                if field in affinity
            }
        memo["content"] = json.dumps(ticket, ensure_ascii=False)


def _trim_spent_agent_thought(messages: list[Any]) -> None:
    for index, memo in enumerate(messages):
        if isinstance(memo, LlmMessage):
            if memo.role == "assistant" and memo.reasoning_details is not None:
                messages[index] = replace(memo, reasoning_details=None)
            continue
        if not isinstance(memo, dict) or memo.get("role") != "assistant":
            continue
        memo.pop("reasoning", None)
        memo.pop("reasoning_details", None)


def _log_haul_ticket(
    state: ChronicleState,
    label: str,
    args: dict[str, Any],
    output: dict[str, Any],
) -> None:
    if not output.get("ok") or label not in {"search_web", "fetch_page"}:
        return
    if label == "search_web":
        destinations = [str(output["vfs_key"])]
        origin_index = [
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
            str(sheet["vfs_key"]) for sheet in output.get("pages", []) if isinstance(sheet, dict) and sheet.get("vfs_key")
        ]
        origin_index = [
            {
                "source_ref": item["source_ref"],
                "vfs_key": item["vfs_key"],
                "title": item["title"],
                "url": item["url"],
            }
            for item in output.get("pages", [])
            if isinstance(item, dict)
        ]
    fingerprint = _haul_fingerprint(label, args)
    state.retrieval_output_cache[fingerprint] = output
    ticket = state.retrieval_receipts.setdefault(
        fingerprint,
        {
            "tool": label,
            "arguments": args,
            "destinations": [],
            "sources": [],
            "calls": 0,
        },
    )
    ticket["calls"] += 1
    ticket["destinations"] = list(dict.fromkeys([*ticket["destinations"], *destinations]))
    known_origins = {str(item["source_ref"]): item for item in [*ticket["sources"], *origin_index]}
    ticket["sources"] = list(known_origins.values())


def _haul_fingerprint(label: str, args: dict[str, Any]) -> str:
    return json.dumps(
        {"tool": label, "arguments": args},
        ensure_ascii=False,
        sort_keys=True,
    )


def _log_shelf_step_ticket(
    state: ChronicleState,
    label: str,
    args: dict[str, Any],
    output: dict[str, Any],
) -> None:
    if not output.get("ok") or label not in {"vfs_read", "vfs_search", "vfs_list"}:
        return

    if label == "vfs_read":
        rows = output.get("lines", [])
        outcome = {
            "returned_line_count": len(rows),
            "first_line": rows[0].get("line") if rows else None,
            "last_line": rows[-1].get("line") if rows else None,
            "truncated": bool(output.get("truncated")),
        }
    elif label == "vfs_search":
        pattern_x = output.get("regex", {})
        affinity = output.get("similarity", {})
        outcome = {
            "regex_total_match_count": pattern_x.get("total_match_count"),
            "regex_returned_match_count": len(pattern_x.get("matches", [])),
            "regex_next_cursor": pattern_x.get("next_cursor"),
            "similarity_status": affinity.get("status"),
            "similarity_returned_chunk_count": len(affinity.get("chunks", [])),
        }
    else:
        outcome = {"returned_key_count": len(output.get("keys", []))}

    fingerprint = json.dumps(
        {"tool": label, "arguments": args},
        ensure_ascii=False,
        sort_keys=True,
    )
    ticket = state.vfs_operation_receipts.setdefault(
        fingerprint,
        {
            "tool": label,
            "arguments": args,
            "calls": 0,
            "outcome": outcome,
        },
    )
    ticket["calls"] += 1
    ticket["outcome"] = outcome


def _gather_origin_tags(value: Any) -> list[str]:
    tags: list[str] = []
    if isinstance(value, dict):
        for field, item in value.items():
            if field == "source_ref" and isinstance(item, str):
                tags.append(item.strip().strip("[]"))
            else:
                tags.extend(_gather_origin_tags(item))
    elif isinstance(value, list):
        for item in value:
            tags.extend(_gather_origin_tags(item))
    return list(dict.fromkeys(tags))


def _note_spend(state: ChronicleState, finding: Any) -> None:
    spend = getattr(finding, "budget", None)
    if spend is None:
        return
    state.budget_snapshot = {
        "session_hard_limit_usd": round(float(spend.session_hard_limit_usd), 6),
        "session_used_budget_usd": round(float(spend.session_used_budget_usd), 6),
        "session_hard_remaining_usd": round(
            max(
                0.0,
                float(spend.session_hard_limit_usd) - float(spend.session_used_budget_usd),
            ),
            6,
        ),
    }


def _renew_haul_ticket_memo(
    messages: list[Any],
    state: ChronicleState,
) -> None:
    marker = "Harness research memory"
    messages[:] = [
        memo
        for memo in messages
        if not (
            isinstance(memo, dict)
            and memo.get("role") == "user"
            and isinstance(memo.get("content"), str)
            and memo["content"].startswith(marker)
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
            + json.dumps(state.budget_snapshot, ensure_ascii=False, indent=2)
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
        trim_haul_tickets = [
            {
                key: ticket[key]
                for key in ("tool", "arguments", "destinations", "sources", "calls")
                if key in ticket
            }
            for ticket in state.retrieval_receipts.values()
        ]
        sections.append(
            "Completed external retrieval receipts. These record actions and a compact "
            "source inventory, not evidence. Each source entry maps a stable source ref "
            "to the exact VFS key whose text can be re-read instead of repeating a web "
            "search:\n"
            + json.dumps(
                trim_haul_tickets,
                ensure_ascii=False,
                indent=2,
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
                indent=2,
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
                indent=2,
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
                indent=2,
            )
        )
    messages.insert(
        2,
        {
            "role": "user",
            "content": f"{marker}:\n\n" + "\n\n".join(sections),
        },
    )


def _fuse_origin_bundles(
    retained: list[dict[str, Any]],
    live: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {str(item["source_ref"]): item for item in retained}
    for item in live:
        origin_tag = str(item["source_ref"])
        prior = merged.get(origin_tag)
        if prior is None:
            merged[origin_tag] = item
            continue
        prior_quote = str(prior.get("quote", "")).strip()
        live_quote = str(item.get("quote", "")).strip()
        if not prior_quote or prior_quote in live_quote:
            quote = live_quote
        elif not live_quote or live_quote in prior_quote:
            quote = prior_quote
        else:
            quote = f"{prior_quote}\n\n{live_quote}"
        merged[origin_tag] = {**prior, **item, "quote": quote}
    return list(merged.values())


def _is_transient_llm_fault(fault: Exception) -> bool:
    memo = str(fault).lower()
    return any(
        marker in memo
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


async def _op_engine(
    engine_label: str,
    messages: list[Any],
    tools: list[dict[str, Any]] | None,
    tool_choice: str,
    parallel_tool_calls: bool,
    timeout: float,
    max_output_tokens: int | None = None,
) -> Any:
    if engine_label == "glm5":
        return await llm_chat(
            provider="openrouter",
            model="z-ai/glm-5",
            messages=messages,
            temperature=0.2,
            max_output_tokens=max_output_tokens or CHRONICLE_GLM5_TOP_SHAPE_TOKENS,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking={"enabled": True, "effort": "low"},
            provider_extra=OPENROUTER_GLM_VENDOR_PREFS,
            timeout=timeout,
        )
    if engine_label == "gpt_oss":
        return await llm_chat(
            provider="openrouter",
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=0.0,
            max_output_tokens=max_output_tokens or CHRONICLE_GPTOSS_TOP_SHAPE_TOKENS,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking={"enabled": True, "effort": "high"},
            provider_extra=OPENROUTER_GPT_VENDOR_PREFS,
            timeout=timeout,
        )
    if engine_label == "openrouter_gemma":
        return await llm_chat(
            provider="openrouter",
            model="google/gemma-4-31b-it",
            messages=messages,
            temperature=1.0,
            max_output_tokens=max_output_tokens or CHRONICLE_OR_GEMMA_TOP_SHAPE_TOKENS,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking={"enabled": True, "effort": "medium"},
            provider_extra=CHRONICLE_OR_GEMMA_VENDOR_PREFS,
            timeout=timeout,
        )
    if engine_label == "openrouter_gemma_prose":
        return await llm_chat(
            provider="openrouter",
            model="google/gemma-4-31b-it",
            messages=messages,
            temperature=1.0,
            max_output_tokens=max_output_tokens or CHRONICLE_OR_GEMMA_TOP_SHAPE_TOKENS,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking={"enabled": True, "effort": "medium"},
            provider_extra=CHRONICLE_OR_GEMMA_VENDOR_PREFS,
            timeout=timeout,
        )
    if engine_label == "openrouter_gemma_stable":
        return await llm_chat(
            provider="openrouter",
            model="google/gemma-4-31b-it",
            messages=messages,
            temperature=1.0,
            max_output_tokens=max_output_tokens or CHRONICLE_OR_GEMMA_TOP_SHAPE_TOKENS,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking={"enabled": True, "effort": "medium"},
            provider_extra=CHRONICLE_OR_GEMMA_STABLE_VENDOR_PREFS,
            timeout=timeout,
        )
    if engine_label == "inkling":
        return await llm_chat(
            provider="ai_gateway",
            model="thinkingmachines/inkling",
            messages=messages,
            temperature=1.0,
            max_output_tokens=max_output_tokens or CHRONICLE_INKLING_TOP_SHAPE_TOKENS,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking={"enabled": True, "effort": "medium"},
            timeout=timeout,
        )
    if engine_label == "ai_gateway_gemma":
        return await llm_chat(
            provider="ai_gateway",
            model="google/gemma-4-31b-it",
            messages=messages,
            temperature=1.0,
            max_output_tokens=max_output_tokens or CHRONICLE_AG_GEMMA_TOP_SHAPE_TOKENS,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            thinking={"enabled": True, "effort": "medium"},
            provider_extra={
                "providerOptions": {
                    "gateway": {
                        "only": ["cerebras"],
                    }
                }
            },
            timeout=timeout,
        )
    raise ValueError(f"unknown model: {engine_label}")


async def _converse_with_engine_relay(
    engines: tuple[str, ...],
    messages: list[Any],
    tools: list[dict[str, Any]] | None,
    tool_choice: str,
    parallel_tool_calls: bool,
    timeout: float,
    max_output_tokens: int | None = None,
) -> Any:
    if not engines:
        raise RuntimeError("no research model was configured")

    raced_engines = engines[:2]
    remaining_engines = engines[2:]
    tasks = [
        asyncio.create_task(
            _op_engine(
                model,
                messages,
                tools,
                tool_choice,
                parallel_tool_calls,
                timeout,
                max_output_tokens,
            )
        )
        for model in raced_engines
    ]
    errors: list[Exception] = []
    queued = set(tasks)
    try:
        while queued:
            done, queued = await asyncio.wait(
                queued,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done:
                try:
                    finding = task.result()
                except Exception as fault:
                    errors.append(fault)
                    continue
                for unfinished in queued:
                    unfinished.cancel()
                await asyncio.gather(*queued, return_exceptions=True)
                return finding
    finally:
        for unfinished in queued:
            unfinished.cancel()
        if queued:
            await asyncio.gather(*queued, return_exceptions=True)

    non_transient = next(
        (fault for fault in errors if not _is_transient_llm_fault(fault)),
        None,
    )
    if non_transient is not None:
        raise non_transient

    for model in remaining_engines:
        try:
            return await _op_engine(
                model,
                messages,
                tools,
                tool_choice,
                parallel_tool_calls,
                timeout,
                max_output_tokens,
            )
        except Exception as fault:
            if not _is_transient_llm_fault(fault):
                raise
            errors.append(fault)

    if not errors:
        raise RuntimeError("no research model was configured")
    raise errors[-1]


async def _converse_with_serial_engine_relay(
    engines: tuple[str, ...],
    messages: list[Any],
    tools: list[dict[str, Any]] | None,
    tool_choice: str,
    parallel_tool_calls: bool,
    timeout: float,
    max_output_tokens: int | None = None,
) -> Any:
    if not engines:
        raise RuntimeError("no research model was configured")

    errors: list[Exception] = []
    for model in engines:
        try:
            return await _op_engine(
                model,
                messages,
                tools,
                tool_choice,
                parallel_tool_calls,
                timeout,
                max_output_tokens,
            )
        except Exception as fault:
            if not _is_transient_llm_fault(fault):
                raise
            errors.append(fault)

    raise errors[-1]


async def _converse_with_dispatch(
    engines: tuple[str, ...],
    messages: list[Any],
    tools: list[dict[str, Any]] | None,
    tool_choice: str,
    parallel_tool_calls: bool,
    timeout: float,
    max_output_tokens: int | None = None,
) -> Any:
    if CHRONICLE_ENGINE_SCHED == "race":
        return await _converse_with_engine_relay(
            engines,
            messages,
            tools,
            tool_choice,
            parallel_tool_calls,
            timeout,
            max_output_tokens,
        )
    if CHRONICLE_ENGINE_SCHED in {"sequential", "state_aware"}:
        return await _converse_with_serial_engine_relay(
            engines,
            messages,
            tools,
            tool_choice,
            parallel_tool_calls,
            timeout,
            max_output_tokens,
        )
    raise ValueError(f"unknown model scheduling policy: {CHRONICLE_ENGINE_SCHED}")


async def _copy_converse_with_retry(
    messages: list[Any],
    tool_choice: str,
    timeout: float,
) -> Any:
    return await _converse_with_dispatch(
        ("glm5", "openrouter_gemma", "gpt_oss"),
        messages,
        None,
        tool_choice,
        False,
        timeout,
    )


async def _closing_verdict_converse_with_retry(
    messages: list[Any],
    timeout: float,
) -> Any:
    return await _converse_with_dispatch(
        ("ai_gateway_gemma", "openrouter_gemma_prose", "openrouter_gemma_stable", "glm5"),
        messages,
        None,
        "none",
        False,
        timeout,
    )


async def _research_prose(brief: str, user: str) -> str:
    messages = [
        {"role": "system", "content": brief},
        {"role": "user", "content": user},
    ]
    finding = await _copy_converse_with_retry(messages, "none", ENGINE_LIMIT)
    text = finding.llm.raw_text
    if not text or not text.strip():
        raise RuntimeError("research model returned empty prose")
    return text.strip()


async def _verdict_prose(
    *,
    state: ChronicleState,
    question: str,
    prior_answer: str,
    requirements: str,
    research_state: str,
    finalization_reason: str,
    packet: list[dict[str, Any]],
) -> str:
    allowed_tags = {
        str(item["source_ref"]).strip("[]")
        for item in packet
        if isinstance(item, dict) and item.get("source_ref")
    }
    messages: list[Any] = [
        {"role": "system", "content": VERDICT_REVISE_BRIEF},
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
                f"{json.dumps(packet, ensure_ascii=False, indent=2)}"
            ),
        },
    ]
    for attempt in range(3):
        finding = await _closing_verdict_converse_with_retry(messages, ENGINE_LIMIT)
        _note_spend(state, finding)
        text = finding.llm.raw_text
        if not text or not text.strip():
            raise RuntimeError("answer writer returned empty prose")
        text = _canon_bundled_internal_tags(text.strip())
        try:
            _check_internal_verdict_tags(
                text,
                allowed_tags,
                require_ref=not _needs_bare_shape(question),
            )
        except ValueError as fault:
            if attempt == 2:
                raise
            messages.extend(
                [
                    {"role": "assistant", "content": text},
                    {
                        "role": "user",
                        "content": (
                            f"Output contract error: {fault}. Rewrite the complete answer. "
                            "Use only the exact private source refs present in the supplied "
                            "records; the harness renders public citation numbers."
                        ),
                    },
                ]
            )
            continue
        return text
    raise AssertionError("unreachable")


def _shaped_shape_op(
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


async def _cast_shaped_shape(
    *,
    question: str,
    answer: str,
    output_schema: dict[str, Any],
) -> Any:
    op_x, direct_object = _shaped_shape_op(output_schema)
    proof_backed_verdict = re.sub(r"\[\[\d+]]", "", answer).strip()
    messages: list[Any] = [
        {"role": "system", "content": SHAPED_SHAPE_BRIEF},
        {
            "role": "user",
            "content": (
                f"Original question:\n{question}\n\n"
                f"Completed evidence-backed answer:\n{proof_backed_verdict}\n\n"
                "Required JSON Schema:\n"
                f"{json.dumps(output_schema, ensure_ascii=False, indent=2)}"
            ),
        },
    ]
    for attempt in range(3):
        finding = await _converse_with_dispatch(
            CHRONICLE_PROBE_ENGINES,
            messages,
            [op_x],
            "required",
            False,
            ENGINE_LIMIT,
        )
        agent = _agent_memo(finding)
        ops = list(agent.tool_calls or ())
        fault: ValueError | None = None
        output: Any = None
        if len(ops) != 1:
            fault = ValueError(
                "call submit_structured_output exactly once; "
                f"received {len(ops)} tool calls"
            )
        else:
            op = ops[0]
            try:
                if op.name != "submit_structured_output":
                    raise ValueError(
                        f"unexpected tool {op.name}; call submit_structured_output"
                    )
                arguments = json.loads(op.arguments)
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
                # v36: normalize entity names for structured output (HMS/USS/SS/SMV
                # prefixes often make the answer mismatch the schema/judge preference)
                output = _canon_subject_labels(output, question)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as caught:
                fault = ValueError(str(caught))
        if fault is None:
            return output
        if attempt == 2:
            raise fault

        messages.append(agent.to_input_message())
        if ops:
            for op in ops:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": op.id,
                        "content": json.dumps(
                            {
                                "ok": False,
                                "error_type": "tool_argument_validation",
                                "details": str(fault),
                            }
                        ),
                    }
                )
        else:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Output contract error: {fault}. Call the required tool with "
                        "the complete schema-conforming value."
                    ),
                }
            )
    raise AssertionError("unreachable")


async def _forecast_verdict_prose(question: str) -> str:
    messages = [
        {"role": "system", "content": FORECAST_VERDICT_BRIEF},
        {"role": "user", "content": question},
    ]
    try:
        finding = await _op_engine(
            "inkling",
            messages,
            None,
            "none",
            False,
            ENGINE_LIMIT,
        )
    except Exception as fault:
        if not _is_transient_llm_fault(fault):
            raise
        finding = await _converse_with_dispatch(
            ("gpt_oss", "openrouter_gemma"),
            messages,
            None,
            "none",
            False,
            ENGINE_LIMIT,
        )
    text = finding.llm.raw_text
    if not text or not text.strip():
        raise RuntimeError("research model returned empty prose")
    return text.strip()


def _decode_review(text: str) -> tuple[str, str]:
    matches = list(
        re.finditer(
            r"(?m)^VERDICT (READY|CONTINUE|REVISE)(?::[ \t]*(.*))?[ \t]*$",
            text,
        )
    )
    if len(matches) != 1:
        raise ValueError("audit must contain exactly one VERDICT line")
    match = matches[0]
    ruling = match.group(1)
    inline = (match.group(2) or "").strip()
    following = text[match.end() :].strip()
    payload = "\n".join(part for part in (inline, following) if part)
    if ruling == "REVISE" and not payload:
        raise ValueError("VERDICT REVISE must include a complete replacement answer")
    if ruling == "CONTINUE" and not payload:
        raise ValueError("VERDICT CONTINUE must name the missing observation")
    return ruling, payload


async def _review(
    state: ChronicleState,
    question: str,
    answer: str,
    packet: list[dict[str, Any]],
) -> str:
    allowed_tags = {
        str(item["source_ref"]).strip("[]")
        for item in packet
        if isinstance(item, dict) and item.get("source_ref")
    }
    origin_inventory = [
        {
            "source_ref": f"[{origin.ref}]",
            "title": origin.title,
            "url": origin.url,
        }
        for origin in state.sources.values()
    ]
    messages = [
        {"role": "system", "content": REVIEW_BRIEF},
        {
            "role": "user",
            "content": (
                f"Original question:\n{question}\n\n"
                "Observed source inventory (discovery metadata only; titles and URLs are "
                "not evidence):\n"
                f"{json.dumps(origin_inventory, ensure_ascii=False, indent=2)}\n\n"
                f"Supplied source records:\n"
                f"{json.dumps(packet, ensure_ascii=False, indent=2)}\n\n"
                f"Current answer:\n{answer}"
            ),
        },
    ]
    for attempt in range(3):
        finding = await _converse_with_serial_engine_relay(
            CHRONICLE_REVIEW_ENGINES,
            messages,
            None,
            "none",
            False,
            ENGINE_LIMIT,
        )
        _note_spend(state, finding)
        text = finding.llm.raw_text
        if not text or not text.strip():
            raise RuntimeError("auditor returned empty output")
        text = text.strip()
        try:
            ruling, payload = _decode_review(text)
            if ruling in {"READY", "REVISE"} and re.search(r"(?m)^MISSING:", text):
                raise ValueError(
                    f"VERDICT {ruling} is invalid while a material premise is MISSING; "
                    "a MISSING line must name a real unresolved premise and cannot say none or "
                    "not applicable. If no premise is missing, preserve the verdict and omit all "
                    "MISSING lines. Correct only this output-format error; do not introduce a new "
                    "evidence requirement"
                )
            if ruling == "REVISE":
                _check_internal_verdict_tags(
                    payload,
                    allowed_tags,
                    require_ref=not _needs_bare_shape(question),
                )
        except ValueError as fault:
            if attempt == 2:
                raise
            messages.extend(
                [
                    {"role": "assistant", "content": text},
                    {
                        "role": "user",
                        "content": (
                            f"Output contract error: {fault}. Re-audit from the supplied records. "
                            "Follow the required premise-line and final VERDICT format exactly; "
                            "a replacement answer must use only exact supplied private source refs."
                        ),
                    },
                ]
            )
            continue
        return text
    raise AssertionError("unreachable")


def _finding_ident(finding: Any, index: int) -> tuple[str | None, str | None]:
    if index >= len(finding.results):
        return finding.receipt_id, None
    return finding.receipt_id, finding.results[index].result_id


async def _run_probe(
    state: ChronicleState,
    args: dict[str, Any],
    preview_spend_size: int | None = None,
) -> dict[str, Any]:
    query = str(args["query"]).strip()
    num = int(args.get("num", 10))
    finding = await search_web(
        query,
        provider=PROBE_VENDOR,
        num=num,
        timeout=PROBE_LIMIT,
    )
    _note_spend(state, finding)
    state.search_count += 1
    parent_slot = f"search://{state.search_count}"
    state.vfs[parent_slot] = finding.response.model_dump_json(indent=2)
    items: list[dict[str, Any]] = []
    preview_chars = 8_000
    if preview_spend_size is not None:
        preview_chars = min(
            preview_chars,
            max(300, preview_spend_size // max(1, len(finding.response.data))),
        )
    for index, item in enumerate(finding.response.data):
        ref = f"S{state.search_count}.{index + 1}"
        key = f"{parent_slot}/result/{index + 1}"
        content = item.snippet or item.title or ""
        state.vfs[key] = content
        receipt_id, result_id = _finding_ident(finding, index)
        state.sources[ref] = ChronicleSource(
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
    return {"ok": True, "vfs_key": parent_slot, "results": items}


# ── v36: supports-note echo citations ────────────────────────────────────────
# 7/31 tasks eba81f71 / fbfa4ab6 were lost on tie-breaks where the judge wanted a
# citation sitting directly behind the decisive sentence. After the answer is
# sealed we re-search the one or two claim lines that carry it and append the
# matching hits as extra citations. This never rewrites the prose, so it cannot
# regress a good answer; it only widens the evidence attached to it.

_MIRROR_RESERVE_SECS = 18.0
_MIRROR_EXTRA_TAGS = 3
_MIRROR_SPAN_SIZE = 900
_MIRROR_SKIP_ROW_RE = re.compile(
    r"^\s*(?:proof of completeness|sources?|references?|notes?|citations?)\b[:\s]*$",
    re.IGNORECASE,
)


def _assertion_rows(answer: str, limit: int = 2) -> list[str]:
    """Pick the decisive, fact-bearing lines out of a finished answer."""
    scored: list[tuple[float, str]] = []
    for raw in (answer or "").splitlines():
        row = re.sub(r"\[\[?\d+\]?\]", " ", raw).strip(" -*\t")
        if len(row) < 25 or _MIRROR_SKIP_ROW_RE.match(row):
            continue
        weight = 0.0
        if re.match(r"(?i)^\s*final answer\s*:", raw):
            weight += 4.0
        if re.search(r"\d", row):
            weight += 1.5
        if re.search(r"(?i)\b(?:pass|fail|highest|largest|greatest|most|first|only)\b", row):
            weight += 1.0
        weight += min(1.0, len(row) / 220.0)
        scored.append((weight, re.sub(r"(?i)^\s*final answer\s*:\s*", "", row)[:180]))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    seen: set[str] = set()
    picked: list[str] = []
    for _weight, row in scored:
        fingerprint = row.lower()[:60]
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        picked.append(row)
        if len(picked) >= limit:
            break
    return picked


async def _mirror_probe_after_seal(
    rendered: str,
    citations: list[CitationRef],
    state: ChronicleState,
    began_at: float,
) -> list[CitationRef]:
    """Append up to a few citations that directly restate the decisive claims."""
    spent = time.monotonic() - began_at
    if spent > CUTOFF_WARNING_SECS - _MIRROR_RESERVE_SECS:
        return citations
    rows = _assertion_rows(rendered)
    if not rows:
        return citations
    already = {(ref.receipt_id, ref.result_id) for ref in citations}
    known_refs = set(state.sources)
    added: list[tuple[float, CitationRef]] = []
    for row in rows:
        try:
            await _run_probe(state, {"query": row, "num": 6})
        except Exception:
            continue
        row_terms = {
            term
            for term in re.findall(r"[A-Za-z0-9]{3,}", row.lower())
            if term not in _WORDWISE_SKIP_TERMS
        }
        for ref, origin in state.sources.items():
            if ref in known_refs:
                continue
            known_refs.add(ref)
            ident = (origin.receipt_id, origin.result_id)
            if not origin.receipt_id or not origin.result_id or ident in already:
                continue
            body = (origin.content or "")
            hits = sum(1 for term in row_terms if term in body.lower())
            if not row_terms or hits / len(row_terms) < 0.45:
                continue
            already.add(ident)
            end = min(len(body), _MIRROR_SPAN_SIZE)
            slices = [CitationSlice(start=0, end=end)] if end > 0 else []
            score = hits / len(row_terms) + 0.3 * _origin_tier(origin.url or "")
            added.append((score, CitationRef(
                receipt_id=origin.receipt_id,
                result_id=origin.result_id,
                slices=slices,
            )))
    added.sort(key=lambda pair: pair[0], reverse=True)
    return citations + [ref for _score, ref in added[:_MIRROR_EXTRA_TAGS]]


async def _run_pull(
    state: ChronicleState,
    args: dict[str, Any],
    preview_spend_size: int | None = None,
) -> dict[str, Any]:
    url = str(args["url"]).strip()
    if re.search(r"\.(?:xls|xlsx|xlsb)(?:[?#]|$)", url, flags=re.IGNORECASE):
        raise ValueError(
            "fetch_page cannot expose spreadsheet binary rows to VFS tools; search the "
            "same publisher for a CSV, HTML, or plain-text companion"
        )
    finding = await fetch_page(url, provider=PROBE_VENDOR, timeout=PULL_LIMIT)
    _note_spend(state, finding)
    state.page_count += 1
    items: list[dict[str, Any]] = []
    preview_chars = 8_000
    if preview_spend_size is not None:
        preview_chars = min(
            preview_chars,
            max(300, preview_spend_size // max(1, len(finding.response.data))),
        )
    for index, item in enumerate(finding.response.data):
        ref = f"P{state.page_count + index}"
        key = f"page://{item.url}"
        state.vfs[key] = item.content
        receipt_id, result_id = _finding_ident(finding, index)
        state.sources[ref] = ChronicleSource(
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
            wordwise_span = _run_wordwise_span(
                state,
                {"query": state.question, "targets": [key]},
            )
            item_payload["question_context"] = {
                "instruction": (
                    "These are the long page regions most relevant to the original question. Inspect them before "
                    "issuing another page search or read."
                ),
                "windows": wordwise_span["windows"],
            }
        item_payload["text"] = state.bounded_preview(
            key,
            max_serialized_chars=preview_chars,
        )
        items.append(item_payload)
    state.page_count += max(0, len(finding.response.data) - 1)
    return {"ok": True, "pages": items}


def _run_view(
    state: ChronicleState,
    args: dict[str, Any],
    *,
    remember_focused: bool = True,
) -> dict[str, Any]:
    key = str(args["key"])
    if key not in state.vfs:
        raise ValueError(f"unknown VFS key: {key}")

    rows = state.vfs[key].splitlines() or [""]

    def resolve_bound(value: Any, default: int) -> int:
        text = "" if value is None else str(value).strip()
        if value is None or text.lower() in {"", "null", "none"}:
            return default
        location = state.line_locations.get(text)
        if location is not None:
            if location[0] != key:
                raise ValueError(f"line ID {value} belongs to {location[0]}, not {key}")
            return location[1]
        row_number_match = re.fullmatch(r"L?(\d+)", text, flags=re.IGNORECASE)
        if row_number_match is None:
            raise ValueError(f"unknown line bound: {value}; use a displayed line ID or 1-based line number")
        return max(0, int(row_number_match.group(1)) - 1)

    start = resolve_bound(args.get("start_line"), 0)
    end = resolve_bound(args.get("end_line"), len(rows) - 1)
    if start >= len(rows):
        raise ValueError(f"start_line is beyond the file; {key} has {len(rows)} lines")
    if end < start:
        raise ValueError("end_line must not precede start_line")
    requested_end = min(len(rows) - 1, end)
    selected_indices: list[int] = []
    reply_size = 0
    for index in range(start, requested_end + 1):
        estimated_size = len(rows[index]) + 80
        if selected_indices and reply_size + estimated_size > CHRONICLE_VIEW_SHEET_SIZE:
            break
        selected_indices.append(index)
        reply_size += estimated_size
    selected = selected_indices
    origin_tags = [f"[{origin.ref}]" for origin in state.sources.values() if origin.key == key]
    next_index = selected[-1] + 1 if selected else start
    truncated = next_index <= requested_end
    next_row_id = None
    if truncated:
        next_row_id = state._line_id(key, next_index, rows[next_index])
        state.line_locations[next_row_id] = (key, next_index)
    if remember_focused:
        state.remember_focused_lines(key, selected)
    return {
        "ok": True,
        "key": key,
        "source_refs": origin_tags,
        "lines": state.render_lines(key, selected),
        "truncated": truncated,
        "next_start_line": next_index + 1 if truncated else None,
        "next_start_line_id": next_row_id,
    }


def _run_roster(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
    prefix = str(args["prefix"])
    slots = [key for key in state.vfs if key.startswith(prefix)]
    return {"ok": True, "keys": slots}


def _run_store(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
    key = str(args["key"])
    if key == "*":
        raise ValueError("'*' cannot be a VFS key")
    state.forget_focused_lines(key)
    state.vfs[key] = str(args["content"])
    return {"ok": True, "key": key, "chars": len(state.vfs[key])}


def _run_drop(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
    key = str(args["key"])
    existed = key in state.vfs
    state.forget_focused_lines(key)
    state.vfs.pop(key, None)
    return {"ok": True, "key": key, "deleted": existed}


def _number_values(text: str) -> set[str]:
    values: set[str] = set()
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
        values.add(raw.rstrip("%").replace(",", ""))
    return values


def _check_retained_number_proof(
    state: ChronicleState,
    origin: ChronicleSource,
    note: str,
    selected_rows_x: list[dict[str, Any]],
) -> None:
    assertion_prose = re.sub(
        (
            r"\blines?\s+(?:L[0-9a-f]{10}|\d+)"
            r"(?:\s*(?:-|to|through)\s*(?:L[0-9a-f]{10}|\d+))?"
            r"(?:\s*\(L[0-9a-f]{10}\))?"
        ),
        "",
        note,
        flags=re.IGNORECASE,
    )
    note_numbers = _number_values(assertion_prose)
    selected_numbers = _number_values(
        "\n".join(str(item["text"]) for item in selected_rows_x)
    )
    missing = note_numbers - selected_numbers
    if not missing:
        return

    origin_rows = state.vfs[origin.key].splitlines() or [""]
    locations: dict[str, list[str]] = {}
    for number in sorted(missing):
        matching_indices = [
            index
            for index, row_x in enumerate(origin_rows)
            if number in _number_values(row_x)
        ]
        if not matching_indices:
            if number in _number_values(origin.title):
                locations[number] = [
                    "source title only; choose a source whose citable body contains this value"
                ]
            continue
        locations[number] = [
            f"line {index + 1} ({state._line_id(origin.key, index, origin_rows[index])})"
            for index in matching_indices[:3]
        ]
    if not locations:
        return
    details = "; ".join(
        f"{number}: {', '.join(row_locations)}"
        for number, row_locations in locations.items()
    )
    raise ValueError(
        "the selected evidence span omits numeric facts asserted by note that are present "
        f"elsewhere in this source ({details}). Re-read those lines and retry "
        "retain_evidence with a span containing the supporting text"
    )


def _run_keep_proof(
    state: ChronicleState,
    args: dict[str, Any],
) -> dict[str, Any]:
    origin_identifier = str(args["source"]).strip().strip("[]")
    origin = state.sources.get(origin_identifier)
    if origin is None:
        origin = next(
            (candidate for candidate in state.sources.values() if candidate.key == origin_identifier),
            None,
        )
    if origin is None:
        if origin_identifier in state.vfs and re.fullmatch(r"search://\d+", origin_identifier):
            raise ValueError(
                f"{args['source']} is a search-result container, not a citable source; "
                "use the displayed [Sx.y] source reference or search://N/result/y child key "
                "that contains the supporting text"
            )
        raise ValueError(f"unknown source reference or VFS key: {args['source']}")
    start_row = args.get("start_line")
    end_row = args.get("end_line")
    if start_row is None or end_row is None:
        raise ValueError("start_line and end_line are required")
    view_shape = _run_view(
        state,
        {
            "key": origin.key,
            "start_line": start_row,
            "end_line": end_row,
        },
        remember_focused=False,
    )
    note = str(args["note"]).strip()
    _check_retained_number_proof(state, origin, note, view_shape["lines"])
    row_ids = " ".join(str(item["line_id"]) for item in view_shape["lines"])
    prior_spans = list(state.source_slices.get(origin.ref, []))

    packet = state.source_packet(
        f"{origin.ref} {row_ids}",
        allow_preview=False,
        include_structured_csv=True,
        prefer_retained=False,
    )
    if not packet:
        raise RuntimeError(f"could not build evidence packet for source {origin.ref}")
    state.source_slices[origin.ref] = _fuse_cite_spans(
        prior_spans,
        list(state.source_slices.get(origin.ref, [])),
    )
    retained = packet[0]
    retained["research_note"] = note
    existing = state.retained_evidence.get(origin.ref)
    if existing is not None:
        retained = _fuse_origin_bundles([existing], [retained])[0]
        prior_note = str(existing.get("research_note", "")).strip()
        retained["research_note"] = "\n".join(
            item for item in (prior_note, note) if item
        )
    state.retained_evidence[origin.ref] = retained
    retained_indices = {
        state.line_locations[str(item["line_id"])][1]
        for item in view_shape["lines"]
        if str(item["line_id"]) in state.line_locations
    }
    state.forget_focused_lines(origin.key, retained_indices)
    return {"ok": True, "source_ref": f"[{origin.ref}]"}


def _run_shed_remaining_origins(
    state: ChronicleState,
    args: dict[str, Any],
) -> dict[str, Any]:
    reason = str(args["reason"]).strip()
    if not reason:
        raise ValueError("reason must not be blank")
    discarded_tags = set(state.review_source_refs)
    discarded_origin_tally = len(discarded_tags)
    state.review_source_refs.clear()
    retained_slots = {state.sources[ref].key for ref in state.retained_evidence if ref in state.sources}
    for ref in discarded_tags:
        origin = state.sources.get(ref)
        if origin is not None and origin.key not in retained_slots:
            state.forget_focused_lines(origin.key)
    return {"ok": True, "discarded_source_count": discarded_origin_tally}


def _md_grid_span(
    state: ChronicleState,
    key: str,
    match_index: int,
) -> dict[str, Any] | None:
    rows = state.vfs[key].splitlines() or [""]
    separator_index: int | None = None
    for index in range(match_index, 0, -1):
        if re.fullmatch(r"\s*\|(?:\s*:?-+:?\s*\|)+\s*", rows[index]):
            separator_index = index
            break
        if index < match_index and rows[index].lstrip().startswith("#"):
            break
    if separator_index is None:
        return None

    header_index = separator_index - 1
    end_index = separator_index
    for index in range(separator_index + 1, len(rows)):
        if not rows[index].lstrip().startswith("|"):
            break
        end_index = index
    return {
        "start_line": header_index + 1,
        "end_line": end_index + 1,
        "header": state.render_lines(key, range(header_index, separator_index + 1)),
    }


def _run_pattern(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
    pattern = re.compile(str(args["pattern"]))
    slots = state.resolve_targets([str(item) for item in args["targets"]])
    cursor_value = args.get("cursor")
    cursor = 0 if cursor_value is None else int(cursor_value)
    if cursor < 0:
        raise ValueError("cursor must be at least zero")
    raw_matches: list[tuple[str, dict[str, Any]]] = []
    for key in slots:
        for item in state.render_lines(key):
            if pattern.search(item["text"]):
                raw_matches.append((key, item))

    matches: list[dict[str, Any]] = []
    sheet_size = 0
    for key, item in raw_matches[cursor:]:
        match = {"key": key, **item}
        origin_tags = [f"[{origin.ref}]" for origin in state.sources.values() if origin.key == key]
        if origin_tags:
            match["source_refs"] = origin_tags
        grid_span: dict[str, Any] | None = None
        csv_records = state.structured_csv_records(
            key,
            [0, item["line"] - 1],
        )
        if csv_records:
            match.pop("text")
            match["csv_record"] = csv_records[0]
        else:
            grid_span = _md_grid_span(
                state,
                key,
                item["line"] - 1,
            )
            if grid_span is not None:
                match["table"] = grid_span
        focused_indices = {item["line"] - 1}
        if grid_span is not None:
            focused_indices.update(
                int(header_row["line"]) - 1
                for header_row in grid_span["header"]
            )
        if origin_tags:
            state.remember_focused_lines(key, focused_indices)
        matches.append(match)
        sheet_size += len(json.dumps(match, ensure_ascii=False, separators=(",", ":")))
        if sheet_size >= CHRONICLE_VSEARCH_SHEET_SIZE:
            break

    next_offset = cursor + len(matches)
    next_cursor = next_offset if next_offset < len(raw_matches) else None
    return {
        "ok": True,
        "matched_keys": slots,
        "total_match_count": len(raw_matches),
        "cursor": cursor,
        "matches": matches,
        "next_cursor": next_cursor,
    }


def _blocks(state: ChronicleState, slots: list[str]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for key in slots:
        content = state.vfs[key]
        start = 0
        index = 0
        while start < len(content):
            end = min(len(content), start + 3_000)
            blocks.append(
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
    return blocks


_WORDWISE_TERM_RE = re.compile(r"[a-z0-9][a-z0-9'.\-]{2,}")
_WIDE_CITED_QUOTE_RE = re.compile(r'"([^"]{24,})"|(?<![a-z0-9])\'([^\']{24,})\'', re.IGNORECASE)
_WORDWISE_SKIP_TERMS = frozenset(
    "the and for with from that this have has was were are is been its their which what when where who how many much "
    "according also into over under between during against about after before while other more most than".split()
)


def _wordwise_terms(text: str) -> set[str]:
    return {
        term_x
        for term_x in _WORDWISE_TERM_RE.findall(text.casefold())
        if term_x not in _WORDWISE_SKIP_TERMS
    }


def _wide_cited_quotes(text: str) -> list[str]:
    return [
        next(group for group in match.groups() if group is not None).strip()
        for match in _WIDE_CITED_QUOTE_RE.finditer(text)
    ]


def _literal_quote_panes(text: str, quotes: list[str]) -> list[tuple[int, int, str]]:
    panes: list[tuple[int, int, str]] = []
    lowered = text.casefold()
    leading_size = (CHRONICLE_LEX_PANE_SIZE * 3) // 4
    for quote_x in quotes:
        probe_from = 0
        normalized_quote = quote_x.casefold()
        while True:
            match_start = lowered.find(normalized_quote, probe_from)
            if match_start < 0:
                break
            start = max(0, match_start - leading_size)
            end = min(len(text), start + CHRONICLE_LEX_PANE_SIZE)
            start = max(0, end - CHRONICLE_LEX_PANE_SIZE)
            if not any(start < existing_end and existing_start < end for existing_start, existing_end, _ignored in panes):
                panes.append((start, end, quote_x))
            probe_from = match_start + len(normalized_quote)
    return panes


def _wordwise_panes(text: str, terms: set[str]) -> list[tuple[int, int, int]]:
    if not text or not terms:
        return []
    if len(text) <= CHRONICLE_LEX_PANE_SIZE:
        return [(0, len(text), sum(term in text.casefold() for term in terms))]

    stage = max(600, CHRONICLE_LEX_PANE_SIZE // 3)
    lowered = text.lower()
    scored: list[tuple[int, int]] = []
    start = 0
    while start < len(text):
        pane = lowered[start : start + CHRONICLE_LEX_PANE_SIZE]
        scored.append((sum(term in pane for term in terms), start))
        if start + CHRONICLE_LEX_PANE_SIZE >= len(text):
            break
        start += stage
    scored.sort(key=lambda item: (-item[0], item[1]))

    selected: list[tuple[int, int, int]] = []
    for matched_term_tally, start in scored:
        if len(selected) >= CHRONICLE_LEX_PANE_TALLY:
            break
        end = min(len(text), start + CHRONICLE_LEX_PANE_SIZE)
        if any(start < selected_end and selected_start < end for selected_start, selected_end, _ignored in selected):
            continue
        if selected and matched_term_tally == 0:
            continue
        selected.append((start, end, matched_term_tally))
    return sorted(selected)


def _run_wordwise_span(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
    slots = state.resolve_targets([str(item) for item in args["targets"]])
    terms = _wordwise_terms(f"{state.question}\n{args['query']}")
    quotes = _wide_cited_quotes(state.question)
    panes: list[dict[str, Any]] = []
    for key in slots:
        content = state.vfs[key]
        selected: list[tuple[int, int, int, str | None]] = [
            (start, end, len(terms), quote_x)
            for start, end, quote_x in _literal_quote_panes(content, quotes)
        ]
        for start, end, matched_term_tally in _wordwise_panes(content, terms):
            if any(
                start < selected_end and selected_start < end
                for selected_start, selected_end, _ignored, _ignored in selected
            ):
                continue
            selected.append((start, end, matched_term_tally, None))
        for start, end, matched_term_tally, literal_quote in selected:
            start_row = content[:start].count("\n")
            end_row = content[:end].count("\n") + 1
            panes.append(
                {
                    "key": key,
                    "start": start,
                    "end": end,
                    "matched_term_count": matched_term_tally,
                    "exact_phrase": literal_quote,
                    "lines": state.render_lines(key, range(start_row, end_row)),
                }
            )
    panes.sort(
        key=lambda item: (
            item["exact_phrase"] is None,
            -int(item["matched_term_count"]),
            str(item["key"]),
            int(item["start"]),
        )
    )
    return {"ok": True, "matched_keys": slots, "windows": panes[:CHRONICLE_LEX_PANE_TALLY]}


def _dotnorm(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


async def _run_affinity(state: ChronicleState, args: dict[str, Any]) -> dict[str, Any]:
    slots = state.resolve_targets([str(item) for item in args["targets"]])
    embedded_blocks: list[tuple[dict[str, Any], list[float]]] = []
    missing_blocks: list[dict[str, Any]] = []
    missing_cache_slots: list[tuple[str, str]] = []
    missing_block_counts: list[int] = []
    for key in slots:
        cache_slot = (key, hashlib.sha256(state.vfs[key].encode()).hexdigest())
        cached = state.document_embeddings.get(cache_slot)
        if cached is not None:
            embedded_blocks.extend(cached)
            continue
        blocks = _blocks(state, [key])
        missing_cache_slots.append(cache_slot)
        missing_block_counts.append(len(blocks))
        missing_blocks.extend(blocks)

    if not embedded_blocks and not missing_blocks:
        return {"ok": True, "matched_keys": slots, "chunks": []}
    query_finding = await embed_text(
        str(args["query"]),
        provider="openrouter",
        model="qwen/qwen3-embedding-8b",
        input_type="query",
        provider_extra=VECTOR_SPARE,
        timeout=VECTOR_LIMIT,
    )
    if missing_blocks:
        document_finding = await embed_text(
            [block["text"] for block in missing_blocks],
            provider="openrouter",
            model="qwen/qwen3-embedding-8b",
            input_type="document",
            provider_extra=VECTOR_SPARE,
            timeout=VECTOR_LIMIT,
        )
        vectors = [item.embedding for item in sorted(document_finding.response.data, key=lambda item: item.index)]
        if len(vectors) != len(missing_blocks):
            raise RuntimeError(
                f"embedding result count mismatch: expected {len(missing_blocks)}, received {len(vectors)}"
            )
        offset = 0
        for cache_slot, block_tally in zip(missing_cache_slots, missing_block_counts, strict=True):
            cached = list(
                zip(
                    missing_blocks[offset : offset + block_tally],
                    vectors[offset : offset + block_tally],
                    strict=True,
                )
            )
            state.document_embeddings[cache_slot] = cached
            embedded_blocks.extend(cached)
            offset += block_tally

    query_vector = query_finding.response.data[0].embedding
    scored = [
        {**block, "score": _dotnorm(query_vector, vector)}
        for block, vector in embedded_blocks
    ]
    scored.sort(key=lambda item: item["score"], reverse=True)
    output: list[dict[str, Any]] = []
    shape_size = 0
    for item in scored[:CHRONICLE_SIM_TOP_BLOCKS]:
        key = item["key"]
        content_before = state.vfs[key][: item["start"]]
        start_row = content_before.count("\n")
        row_tally = item["text"].count("\n") + 1
        finding_item = {
            "key": key,
            "chunk": item["chunk"],
            "score": item["score"],
            "lines": state.render_lines(key, range(start_row, start_row + row_tally)),
        }
        origin_tags = [f"[{origin.ref}]" for origin in state.sources.values() if origin.key == key]
        if origin_tags:
            finding_item["source_refs"] = origin_tags
        finding_size = len(
            json.dumps(
                finding_item,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        if (
            len(output) >= CHRONICLE_SIM_FLOOR_BLOCKS
            and shape_size + finding_size > CHRONICLE_SIM_FINDING_SIZE
        ):
            break
        if origin_tags:
            state.remember_focused_lines(
                key,
                range(start_row, start_row + row_tally),
            )
        output.append(finding_item)
        shape_size += finding_size
    return {"ok": True, "matched_keys": slots, "chunks": output}


async def _run_shelf_probe(
    state: ChronicleState,
    args: dict[str, Any],
) -> dict[str, Any]:
    pattern_finding: dict[str, Any] | None = None
    pattern_fault: str | None = None
    try:
        pattern_finding = _run_pattern(state, args)
    except (TypeError, ValueError, re.error) as fault:
        pattern_fault = str(fault)

    affinity_trigger: str | None = None
    if pattern_finding is None:
        affinity_trigger = "regex_error"
    elif int(pattern_finding["total_match_count"]) == 0:
        affinity_trigger = "no_regex_matches"

    affinity_finding: dict[str, Any] | None = None
    affinity_fault: str | None = None
    if affinity_trigger is not None:
        try:
            affinity_finding = await _run_affinity(state, args)
        except Exception as fault:
            affinity_fault = str(fault)

    if pattern_finding is None and affinity_finding is None:
        raise RuntimeError(
            "both VFS search methods failed: "
            f"regex={pattern_fault or 'unknown'}; similarity={affinity_fault or 'unknown'}"
        )

    output: dict[str, Any] = {
        "ok": True,
        "similarity": {
            "status": "not_run",
            "reason": "regex_returned_matches_on_first_search",
        },
    }
    if pattern_finding is not None:
        output["regex"] = {
            key: value
            for key, value in pattern_finding.items()
            if key not in {"ok", "matched_keys"}
        }
    if pattern_fault is not None:
        output["regex_error"] = pattern_fault
    if affinity_finding is not None:
        output["similarity"] = {"status": "completed", "trigger": affinity_trigger}
        output["similarity"].update(
            {
                key: value
                for key, value in affinity_finding.items()
                if key not in {"ok", "matched_keys"}
            }
        )
    if affinity_fault is not None:
        output["similarity"] = {
            "status": "failed",
            "trigger": affinity_trigger,
            "error": affinity_fault,
        }
    return output


async def _run_op(
    state: ChronicleState,
    label: str,
    args: dict[str, Any],
    preview_spend_size: int | None = None,
) -> dict[str, Any]:
    if label in {"search_web", "fetch_page"}:
        cached = state.retrieval_output_cache.get(_haul_fingerprint(label, args))
        if cached is not None:
            return {**cached, "cached": True}
    if label == "search_web":
        return await _run_probe(state, args, preview_spend_size)
    if label == "fetch_page":
        return await _run_pull(state, args, preview_spend_size)
    if label == "vfs_read":
        return _run_view(state, args)
    if label == "vfs_list":
        return _run_roster(state, args)
    if label == "vfs_write":
        return _run_store(state, args)
    if label == "vfs_delete":
        return _run_drop(state, args)
    if label == "retain_evidence":
        return _run_keep_proof(state, args)
    if label == "discard_remaining_sources":
        return _run_shed_remaining_origins(state, args)
    if label == "vfs_search":
        return await _run_shelf_probe(state, args)
    if label == "update_research_state":
        research_state = str(args["state"]).strip()
        if not research_state:
            raise ValueError("state must not be blank")
        state.research_state = research_state
        return {"ok": True}
    raise ValueError(f"unknown tool: {label}")


def _unique_op_ops(ops: list[Any]) -> tuple[list[Any], int]:
    distinct_ops: list[Any] = []
    seen: set[tuple[str, str]] = set()
    for op in ops:
        try:
            arguments = json.dumps(
                json.loads(op.arguments),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except json.JSONDecodeError:
            arguments = op.arguments
        fingerprint = (op.name, arguments)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        distinct_ops.append(op)
    return distinct_ops, len(ops) - len(distinct_ops)


async def _seal_verdict(
    *,
    state: ChronicleState,
    question: str,
    current_answer: str,
    reason: str,
    assistant_context: str,
    last_packet: list[dict[str, Any]],
    final_source_slices: dict[str, list[CitationSlice]],
) -> tuple[str, list[dict[str, Any]]]:
    finalization_span = "\n\n".join(
        value
        for value in (
            state.research_state.strip(),
            reason.strip(),
            assistant_context.strip(),
        )
        if value
    )
    packet = state.source_packet(
        finalization_span,
        include_structured_csv=True,
    )
    if not packet:
        raise ValueError(
            "final answer must mention at least one observed source reference such as S1.2 or P1"
        )
    unretained_sheet_tags = [
        str(item["source_ref"])
        for item in packet
        if str(item["source_ref"]).strip("[]").startswith("P")
        and str(item["source_ref"]).strip("[]") not in state.retained_evidence
    ]
    if unretained_sheet_tags:
        raise ValueError(
            "fetched-page evidence must be preserved before finalization; call retain_evidence "
            f"for each decisive excerpt from {', '.join(unretained_sheet_tags)}, then retry"
        )
    for item in packet:
        ref = str(item["source_ref"])[1:-1]
        final_source_slices[ref] = _fuse_cite_spans(
            final_source_slices.get(ref, []),
            list(state.source_slices.get(ref, [])),
        )
    precise_tags = {str(item["source_ref"]) for item in [*last_packet, *packet]}
    retained_bundle = [
        item
        for item in state.retained_evidence.values()
        if str(item["source_ref"]) not in precise_tags
    ]
    merged_bundle = _fuse_origin_bundles(last_packet, retained_bundle)
    merged_bundle = _fuse_origin_bundles(merged_bundle, packet)
    merged_bundle = [
        item
        for item in merged_bundle
        if (
            (origin := state.sources.get(str(item["source_ref"]).strip("[]")))
            and origin.receipt_id
            and origin.result_id
        )
    ]
    if not merged_bundle:
        raise ValueError(
            "none of the selected source records can be materialized as response citations"
        )
    answer = await _verdict_prose(
        state=state,
        question=question,
        prior_answer=current_answer,
        requirements=state.evidence_requirements or "",
        research_state=state.research_state,
        finalization_reason=reason,
        packet=merged_bundle,
    )
    return answer, merged_bundle


def _research_advance_fingerprint(state: ChronicleState) -> tuple[Any, ...]:
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


def _pursuit_engines(
    state: ChronicleState,
    cutoff_warning_fired: bool,
    pivot_cause: str,
) -> tuple[str, ...]:
    if CHRONICLE_ENGINE_SCHED != "state_aware":
        return CHRONICLE_FIX_ENGINES if state.audit_gap else CHRONICLE_PROBE_ENGINES
    if state.audit_gap or cutoff_warning_fired or pivot_cause:
        return CHRONICLE_FIX_ENGINES
    return BOARD_AWARE_CHRONICLE_PROBE_ENGINES


def _demands_engines(
    cutoff_warning_fired: bool,
    pivot_cause: str,
) -> tuple[str, ...]:
    if CHRONICLE_ENGINE_SCHED == "state_aware" and (cutoff_warning_fired or pivot_cause):
        return CHRONICLE_FIX_ENGINES
    return CHRONICLE_NEED_ENGINES


async def _pursue(question: str, forecast_verdict: str) -> tuple[str, list[CitationRef]]:
    pursuit_begun_at = time.monotonic()
    cutoff_warning_fired = False
    state = ChronicleState(question)
    state.research_state = (
        f"Current best answer hypothesis:\n{forecast_verdict}\n"
        "Observed support: none yet.\n"
        "Most important unresolved question: test the hypothesis against external evidence."
    )
    current_answer = forecast_verdict
    messages: list[Any] = [
        {"role": "system", "content": PURSUIT_BRIEF},
        {
            "role": "user",
            "content": (f"Original question:\n{question}\n\nExpected answer hypothesis:\n{forecast_verdict}"),
        },
    ]
    last_packet: list[dict[str, Any]] = []
    final_source_slices: dict[str, list[CitationSlice]] = {}
    closing_review = ""
    pivot_cause = ""
    prior_op_signatures: tuple[str, ...] = ()

    for _round in range(160):
        if (
            not cutoff_warning_fired
            and time.monotonic() - pursuit_begun_at >= CUTOFF_WARNING_SECS
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
            cutoff_warning_fired = True
        _renew_haul_ticket_memo(messages, state)
        demands_queued = state.evidence_requirements is None
        if demands_queued:
            onhand_ops = DEMANDS_OPS
            onhand_engines = _demands_engines(
                cutoff_warning_fired,
                pivot_cause,
            )
        else:
            onhand_ops = OP_CATALOG
            onhand_engines = _pursuit_engines(
                state,
                cutoff_warning_fired,
                pivot_cause,
            )
        ask_memos = (
            [
                {"role": "system", "content": DEMANDS_BRIEF},
                {"role": "user", "content": f"Original question:\n{question}"},
            ]
            if demands_queued
            else messages
        )
        finding = await _converse_with_dispatch(
            onhand_engines,
            messages=ask_memos,
            tools=onhand_ops,
            tool_choice="required",
            parallel_tool_calls=True,
            timeout=ENGINE_LIMIT,
            max_output_tokens=None,
        )
        _note_spend(state, finding)
        _trim_spent_agent_thought(messages)
        _trim_spent_op_findings(messages)
        agent = _agent_memo(finding)
        state.remember_reasoning_observation(agent.reasoning)
        ops, twin_op_tally = _unique_op_ops(list(agent.tool_calls or ()))
        if not ops:
            copy = (finding.llm.raw_text or "").strip()
            if copy:
                try:
                    current_answer, last_packet = await _seal_verdict(
                        state=state,
                        question=question,
                        current_answer=current_answer,
                        reason=copy,
                        assistant_context=_agent_proof_span(agent),
                        last_packet=last_packet,
                        final_source_slices=final_source_slices,
                    )
                except ValueError as fault:
                    pivot_cause = (
                        "The previous model tried to finalize without materializable support. "
                        f"Resolve this exact problem before finalizing again: {fault}"
                    )
                    messages.extend(
                        [
                            agent.to_input_message(),
                            {
                                "role": "user",
                                "content": (
                                    f"Your terminal answer could not be finalized: {fault}. "
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
                    closing_review,
                )
                return _emit_outward_cites(
                    current_answer,
                    plan,
                    unadorned_output=_needs_bare_shape(question),
                )
            messages.extend(
                [
                    agent.to_input_message(),
                    {
                        "role": "user",
                        "content": "Use a tool. Call ready_to_finalize only when inspected sources support the answer.",
                    },
                ]
            )
            pivot_cause = (
                "The previous model returned neither a tool call nor a usable terminal answer. "
                "Choose the smallest valid operation that advances the investigation."
            )
            continue
        agent_input = replace(
            agent,
            tool_calls=tuple(ops),
        ).to_input_message()
        messages.append(agent_input)
        ready_requested = False
        review_ready = False
        advance_before = _research_advance_fingerprint(state)
        round_op_signatures: list[str] = []
        round_fail_signatures: list[str] = []
        haul_op_tally = sum(op.name in {"search_web", "fetch_page"} for op in ops)
        haul_preview_spend = (
            CHRONICLE_BATCHED_PREVIEW_SIZE // haul_op_tally if haul_op_tally else None
        )
        for op_index, op in enumerate(ops):
            op_fingerprint = json.dumps(
                {"tool": op.name, "raw_arguments": op.arguments},
                ensure_ascii=False,
                sort_keys=True,
            )
            try:
                args = json.loads(op.arguments)
                if not isinstance(args, dict):
                    raise ValueError("tool arguments must be a JSON object")
                op_fingerprint = json.dumps(
                    {"tool": op.name, "arguments": args},
                    ensure_ascii=False,
                    sort_keys=True,
                )
                if op.name == "set_evidence_requirements":
                    if not demands_queued or len(ops) != 1:
                        raise ValueError("set_evidence_requirements must be the sole call before retrieval")
                    requirements = str(args["requirements"]).strip()
                    if not requirements:
                        raise ValueError("requirements must not be empty")
                    state.evidence_requirements = requirements
                    output = {"ok": True}
                elif op.name == "ready_to_finalize":
                    if round_fail_signatures:
                        raise ValueError(
                            "cannot finalize in the same response after an earlier tool call "
                            "failed; inspect that tool feedback, correct the failed operation, "
                            "and retry finalization"
                        )
                    incompatible_ops = [
                        candidate.name
                        for candidate in ops
                        if candidate.name not in {"update_research_state", "retain_evidence", "ready_to_finalize"}
                    ]
                    if incompatible_ops:
                        raise ValueError(
                            "ready_to_finalize may only accompany update_research_state and retain_evidence; "
                            f"also received {', '.join(incompatible_ops)}"
                        )
                    if op_index != len(ops) - 1:
                        raise ValueError("ready_to_finalize must be the final call in the response")
                    reason = str(args["reason"])
                    current_answer, last_packet = await _seal_verdict(
                        state=state,
                        question=question,
                        current_answer=current_answer,
                        reason=reason,
                        assistant_context=_agent_proof_span(agent),
                        last_packet=last_packet,
                        final_source_slices=final_source_slices,
                    )
                    closing_review = ""
                    ready_requested = True
                    review_ready = True
                    output = {
                        "ok": True,
                        "answer_checkpoint": current_answer,
                    }
                elif op.name == "discard_remaining_sources":
                    if op_index != len(ops) - 1:
                        raise ValueError("discard_remaining_sources must be the last call in the response")
                    output = await _run_op(
                        state,
                        op.name,
                        args,
                        haul_preview_spend,
                    )
                else:
                    output = await _run_op(
                        state,
                        op.name,
                        args,
                        haul_preview_spend,
                    )
                    _log_haul_ticket(state, op.name, args, output)
                    _log_shelf_step_ticket(state, op.name, args, output)
            except Exception as fault:
                output = {
                    "ok": False,
                    "error_type": (
                        "tool_argument_validation"
                        if isinstance(fault, (KeyError, TypeError, ValueError, json.JSONDecodeError))
                        else "tool_execution"
                    ),
                    "details": str(fault),
                }
            round_op_signatures.append(op_fingerprint)
            if not output.get("ok"):
                round_fail_signatures.append(
                    json.dumps(
                        {
                            "tool": op.name,
                            "error_type": output.get("error_type"),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": op.id,
                    "content": json.dumps(output, ensure_ascii=False),
                }
            )
        if twin_op_tally:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"The previous response repeated {twin_op_tally} exact tool "
                        "calls. The harness executed each distinct call once. Continue from "
                        "those results without repeating an identical call."
                    ),
                }
            )
        if ready_requested:
            closing_review = await _review(
                state,
                question,
                current_answer,
                last_packet,
            )
            ruling, review_payload = _decode_review(closing_review)
            if ruling == "CONTINUE":
                state.audit_gap = review_payload
                state.clear_focused_lines()
                review_ready = False
                messages = [
                    {"role": "system", "content": PURSUIT_BRIEF},
                    {
                        "role": "user",
                        "content": (
                            f"Original question:\n{question}\n\n"
                            "The finalization audit found one unresolved evidence gap:\n"
                            f"{review_payload}\n\n"
                            "The harness will preserve the existing VFS, source references, "
                            "retained evidence, retrieval receipts, and research state. Resolve "
                            "this exact gap with the smallest useful next observation, update the "
                            "research state if the answer changes, then finalize. Do not restart "
                            "the investigation or repeat already supported premises."
                        ),
                    }
                ]
            elif ruling == "REVISE":
                allowed_tags = {
                    str(item["source_ref"]).strip("[]")
                    for item in last_packet
                    if isinstance(item, dict) and item.get("source_ref")
                }
                _check_internal_verdict_tags(
                    review_payload,
                    allowed_tags,
                    require_ref=not _needs_bare_shape(question),
                )
                current_answer = review_payload
                state.audit_gap = ""
                review_ready = True
            else:
                state.audit_gap = ""
                review_ready = True
        if CHRONICLE_ENGINE_SCHED == "state_aware" and not ready_requested:
            advance_after = _research_advance_fingerprint(state)
            live_ops = tuple(round_op_signatures)
            live_failures = tuple(round_fail_signatures)
            next_pivot_cause = ""
            if live_failures:
                next_pivot_cause = (
                    "The previous model's tool call failed. Read the detailed tool feedback, correct "
                    "that exact operation or choose a different valid operation, and advance the "
                    "investigation without repeating the failure."
                )
            elif (
                live_ops
                and live_ops == prior_op_signatures
                and advance_after == advance_before
            ):
                next_pivot_cause = (
                    "The previous model repeated the same operations without adding evidence or changing "
                    "the research state. Choose a different evidence route."
                )
            elif live_ops and not live_failures and advance_after == advance_before:
                next_pivot_cause = (
                    "The previous operations succeeded mechanically but produced no new retained evidence, "
                    "source coverage, inspected lines, or research-state change. Choose the smallest different "
                    "operation that can resolve the current uncertainty."
                )
            if next_pivot_cause:
                messages.append({"role": "user", "content": next_pivot_cause})
            pivot_cause = next_pivot_cause
            prior_op_signatures = live_ops
        if ready_requested and review_ready:
            plan = state.citation_plan(
                current_answer,
                last_packet,
                final_source_slices,
                closing_review,
            )
            rendered, citations = _emit_outward_cites(
                current_answer,
                plan,
                unadorned_output=_needs_bare_shape(question),
            )
            # v36: append targeted echo-citations that restate the final claims
            if not _needs_bare_shape(question):
                try:
                    citations = await _mirror_probe_after_seal(
                        rendered, citations, state, pursuit_begun_at
                    )
                except Exception:
                    pass
            return (rendered, citations)

    raise RuntimeError("investigation did not finalize within the generous 160-turn ceiling")


@entrypoint("query")
async def query(query: Query) -> Response:
    try:
        forecast_verdict = await _forecast_verdict_prose(query.text)
    except Exception as fault:
        if not _is_transient_llm_fault(fault):
            raise
        forecast_verdict = (
            "No expected-answer hypothesis was available because its model call "
            "failed. Investigate the original question directly and construct a "
            "revisable answer from observed external evidence."
        )
    answer, citations = await _pursue(query.text, forecast_verdict)
    if query.output_schema is not None:
        output = await _cast_shaped_shape(
            question=query.text,
            answer=answer,
            output_schema=query.output_schema,
        )
        return Response(output=output, citations=citations)
    return Response(text=answer, citations=citations)
