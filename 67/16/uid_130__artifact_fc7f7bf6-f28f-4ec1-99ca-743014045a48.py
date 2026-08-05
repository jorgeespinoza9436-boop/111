"""Meridian v37 — dual-donor research agent for harnyx_v3.

BLEND. Roughly 60% of the architecture is the selection-score leader lineage:
the virtual-filing-cabinet research state machine, retained-proof numeric
checking, and the private [S/P] reference compiler. Those parts carry the
structured-task strength and stay algorithmically intact.

The remaining 40% adopts the efficiency discipline of the low-median-cost /
low-median-runtime finalist lineage:

  1. Wall-clock governor — a hard budget with a sealed-answer tail reserve.
     Once a citable answer checkpoint exists and the clock enters the reserve,
     the run publishes that checkpoint instead of gambling the remaining
     seconds on one more model round. The post-seal review pass is likewise
     skipped when the tail cannot afford its model call.
  2. Determination grid — the writer is contracted to emit a machine-readable
     candidate x condition table with a verdict cell per row. A deterministic
     post-pass parses that table, computes the surviving candidate set with
     set logic, and rewrites the locked headline only when the computation
     contradicts it, so the headline and the proof body are two views of one
     table rather than two independent claims.
  3. Lead-narration peel — first-person planning prose ahead of the locked
     headline is removed deterministically before rendering.

All three are deterministic string or clock work: they add no model calls,
which is exactly how the donor lineage kept its median cost and runtime low.

POST-MORTEM (2026-08-03, batch a82ddc4d, uid143/bbf01675):

  Replaced architectural dimension: evidence_state_flow.
    OLD ROOT: retained_evidence (flat dict of unranked text blobs keyed by source
      ref) + research_state (free-text model-authored hypothesis). Evidence between
      stages was an undifferentiated text dump with no provenance authority signals.
    NEW ROOT: ClaimSourceLedger — a structured ledger where each retained source is
      classified by deterministic provenance authority tier (official_pdf >
      institutional > primary_data > aggregator > encyclopedia > other) derived from
      URL and title patterns. The ledger replaces retained_evidence and research_state
      as the primary evidence carrier between stages:
        * Storage: claim_ledger.entries (LedgerEntry with SourceAuthority) replaces
          the flat retained_evidence dict.
        * Serialization: _refresh2_freight_chit_note presents evidence ranked by
          authority tier instead of insertion order, with provenance_authority label
          on each entry.
        * Manifest building: _notarize_ruling sorts the source manifest by authority
          so the answer writer sees official/institutional sources before aggregators.
        * Prompt: PASSAGE_CHARTER PROVENANCE AUTHORITY rule instructs the model to
          prefer higher-authority sources when retaining and citing evidence.

  Fix: source_fidelity (task 500e4a83).
    The agent retrieved grade boundary data from third-party aggregators
    (SaveMyExams, SimpleStudy) rather than official exam board PDFs. Judges
    penalized the weaker provenance. The claim ledger classifies these sources as
    tier-3 aggregator and sorts official exam-board sources (AQA, OCR) to the top
    of the manifest, making the answer writer cite official sources when available.

  Latent-bug note: static profiler flagged bare 'monotonic' as called-but-not-
    imported; all usages are time.monotonic() via 'import time' — false positive.
"""

from __future__ import annotations 

import asyncio 
import hashlib 
import json 
import math 
import re 
import time 
from dataclasses import dataclass ,replace 
from typing import Any 

from harnyx_miner_sdk .api import fetch_page ,llm_chat ,search_web
from harnyx_miner_sdk .decorators import entrypoint
from harnyx_miner_sdk .query import CitationRef ,CitationSlice ,Query ,Response

try :
    from harnyx_miner_sdk .api import embed_text
except ImportError :
    async def embed_text (*_a ,**_kw ):
        raise RuntimeError ("embed_text not available in this environment")

try :
    from harnyx_miner_sdk .llm import LlmMessage
except (ImportError ,ModuleNotFoundError ):
    LlmMessage =dict


def _contract_m (
label_m :str ,
description_m :str ,
properties_m :dict [str ,Any ],
required_m :tuple [str ,...],
)->dict [str ,Any ]:
    return {
    "type":"function",
    "function":{
    "name":label_m ,
    "description":description_m ,
    "parameters":{
    "type":"object",
    "properties":properties_m ,
    "required":list (required_m ),
    "additionalProperties":False ,
    },
    "strict":False ,
    },
    }

VERSION_M ="meridian-v37-dualdonor"
SUBMISSION_HOTKEY_M ="harnyx_v3"

SOUNDING_CARRIER ="parallel"
SOUNDING_GAUGE =10.0 
FERRY_GAUGE =15.0 
PILOT_GAUGE =90.0 
BEARING_GAUGE =120.0 
HORIZON_ALERT_TICKS =150.0 

# Wall-clock governor (donor: the low-median-runtime lineage). The validator kill
# line sits at 300s; the governor works against a slightly earlier private wall.
WARDEN_RAMPART_TICKS =283.0 
# Tail kept for publishing an already-sealed checkpoint: rendering the citation
# plan is local work, so the reserve only needs to absorb clock jitter plus the
# final render, never another model round.
NOTARIZE_STERN_BERTH_TICKS =40.0 
# The post-seal review is one more model call; below this much remaining wall it
# is skipped and the sealed answer ships as-is. A published cited answer beats a
# reviewed answer that the kill line erases.
SURVEY_STERN_FLOOR_TICKS =62.0 
# Per-round ceiling never granted beyond what the wall still holds.
LEG_CANOPY_FLOOR_TICKS =25.0 
MERIDIAN_POOLED_GLIMPSE_GIRTH =240_000 
MERIDIAN_PERUSE_LEAF_GIRTH =80_000 
MERIDIAN_BEAM_MEMORY_GIRTH =MERIDIAN_PERUSE_LEAF_GIRTH 
MERIDIAN_VSEARCH_LEAF_GIRTH =60_000 
MERIDIAN_ECHO2_FLOOR_BRICKS =3 
MERIDIAN_ECHO2_TOP_BRICKS =5 
MERIDIAN_ECHO2_SIGHTING_GIRTH =45_000 
MERIDIAN_GLOSS_SLAT_GIRTH =3_600 
MERIDIAN_GLOSS_SLAT_CENSUS =3 
MERIDIAN_GPTOSS_TOP_FORM_SHARDS =65_536 
MERIDIAN_OR_GEMMA_TOP_FORM_SHARDS =40_960 
MERIDIAN_AG_GEMMA_TOP_FORM_SHARDS =131_072 
MERIDIAN_GLM5_TOP_FORM_SHARDS =131_072 
MERIDIAN_INKLING_TOP_FORM_SHARDS =131_072 

MERIDIAN_PILOT_ROTA ="state_aware"
MERIDIAN_SOUNDING_PILOTS =("glm5","ai_gateway_gemma","inkling")
BOARD_AWARE_MERIDIAN_SOUNDING_PILOTS =(
"openrouter_gemma",
"ai_gateway_gemma",
"openrouter_gemma_stable",
"glm5",
"inkling",
)
MERIDIAN_WANT_PILOTS =("openrouter_gemma","ai_gateway_gemma","openrouter_gemma_stable","glm5")
MERIDIAN_AMEND_PILOTS =(
"openrouter_gemma",
"ai_gateway_gemma",
"openrouter_gemma_stable",
"glm5",
"inkling",
)
MERIDIAN_SURVEY_PILOTS =(
"inkling",
"openrouter_gemma",
"ai_gateway_gemma",
"openrouter_gemma_stable",
"glm5",
)
WARRANT_SCREEN_PILOTS =MERIDIAN_SOUNDING_PILOTS 
BEARING_SLACK ={
"provider":{
"only":["nebius","deepinfra","siliconflow"],
"allow_fallbacks":True ,
}
}
OPENROUTER_GLM_CARRIER_LEANINGS ={
"provider":{
"only":["amazon-bedrock"],
"allow_fallbacks":True ,
}
}
OPENROUTER_GPT_CARRIER_LEANINGS ={
"provider":{
"only":["cerebras","baseten","deepinfra","sambanova","nebius","coreweave"],
"allow_fallbacks":True ,
}
}
MERIDIAN_OR_GEMMA_CARRIER_LEANINGS ={
"provider":{
"only":["sambanova"],
"allow_fallbacks":False ,
}
}
MERIDIAN_OR_GEMMA_STABLE_CARRIER_LEANINGS ={
"provider":{
"only":["modelrun"],
"allow_fallbacks":False ,
}
}
OUTLOOK_RULING_CHARTER ="""\
A deep-research task is starting. Before any external retrieval happens, put down the strongest expected answer your
internal knowledge can offer. Treat it as a revisable hypothesis for the investigation — it is never evidence.

The working hypothesis should be brief: name the probable answer and the single biggest uncertainty hanging over it.
Then sketch the cheapest verification route — if a finite candidate inventory is needed, say which one, and spell out
the exact external facts whose confirmation or refutation would settle the hypothesis. Useful sources or pages may be
named, but never produce or guess a URL; exact URLs come from retrieval. The route is an investigative heuristic, not
support. On an exhaustive question, place the inventory source ahead of any per-candidate metric lookup. Stay concrete
enough that the coming investigation can confirm, amend, or discard the answer. Never fabricate a citation, and never
dodge an answer just because key facts are still unsettled.

Below the hypothesis, add a compact BRIEFING block:
- CANDIDATE POOL: the finite set the question ranges over, or the inventory source enumerating it.
- KEY FACTS: the numeric / geographic / date values on which the answer turns.
- LOOKUPS: 2-5 sharp search queries that would verify those facts, official sources included.
- WATCH OUT: any condition prone to mis-scoping (year, column, boundary, named source)."""

MANDATES_ORDER ="""\
Call set_evidence_requirements exactly once, before any retrieval. Put one evidence question on each line and leave
every answer blank. A valid question requests one externally checkable premise the final answer will rest on. It is
not a search plan, not a source description, not a table schema, and not a shopping list of raw data. Since nothing
external has been observed yet, no candidate, number, list member, answer, expected value, or proposition may appear
unless the original question itself supplies it.

Conclusions that follow mechanically from externally supported operands — arithmetic, set intersection, decade
membership, threshold comparison, sorting — are not separate evidence questions. Request the external operands the
derivation consumes; the derivation itself needs no outside source.

Break compound premises apart: a person's role, their relationship, a date, and each required property of an
institution each get their own line. Wording and named items given by the question count as given. The role someone
holds at an institution, that institution's type or status, and its location are three distinct questions. For an
exhaustive result, request the external operands that establish completeness, preferring questions whose answer is a
complete filtered set over questions demanding every raw value of every candidate. On an intersection of conditions,
lead with the complete result of the most selective condition; later conditions apply only to candidates surviving the
earlier filters, may be phrased conditionally, and must never presume who survives. Never add a question asking
whether a source or set is complete — sufficiency of observed scope is the closing audit's job. If the original
question explicitly demands retrieval from a named source, edition, page, report, or dataset, that source and scope
stay a required premise even when some other filter would reach the same conclusion.
Identification wording does not imply uniqueness: "the person" is grammar, not an exhaustiveness condition. Unless the
question says only, unique, all, every, asks how many, or otherwise forces an exhaustive result, do not demand proof
that nobody else matches. Nor should every value be demanded for every failing candidate; one supported disqualifying
condition eliminates a candidate, and only the survivors need the remaining checks.

Bad requirement: "North Carolina had fatalities from Hurricane Nicole."
Good requirement: "Which states had direct or indirect fatalities across the named 2022 storms?"
Good requirement: "Which states had direct or indirect fatalities across the named 2023 storms?"
Bad for "Identify the person who has A and B": "Exactly one person satisfies A and B."
Good: "Which identified person has A?" and "Which identified person has B?" """

MANDATES_CHARTER =(
"""\
Lay out the open evidence questions that any complete answer to the original question has to resolve. Work from the
original question alone; there is no expected answer and no candidate hypothesis at this stage.

"""
+MANDATES_ORDER 
)

PASSAGE_CHARTER ="""\
Your job is deep research: build a claim that settles the original question, then back it with enough externally
inspectable support that a skeptical reader would accept it.

Treat the expected answer as a helpful guess and nothing more. Let it steer cheap, narrow searches; amend or discard
it the moment observed sources contradict it, surface a stronger answer, or reveal an overlooked condition. Internal
knowledge may point the way, but every material external premise in the finished claim must rest on observed support.
Whenever the question pins a fact to a named source, edition, page, report, or dataset, inspect that exact source
before settling for a stand-in. Failing that, favor the organization that produced the fact, an official record, or a
primary document ahead of any aggregator or commentary. Open retrieval with the named or primary source plus the
precise subject; lean on secondary sources for discovery only while the direct source is still out of reach. When the
publisher's page cannot be reached, an archived copy of that exact page beats a third-party reproduction.
Never finalize off a secondary source while the observed search results already hold a reachable official or primary
source for the same decisive premise: inspect the direct source first, and keep the secondary one only if the direct
source still lacks the needed text or scope afterwards.
A clue-only search that fails to improve the evidence should not be paraphrased and rerun. Switch evidence routes, or
probe the expected-answer candidate head-on.
When a required source's search surface hides the full inventory, discover a finite candidate set through a suitable
secondary source, then check each surviving candidate against the required source itself. Discovery material is an
aid, never final support for a premise the question ties to the required source.
On an exhaustive question the presumed candidate pool stays unproved until either a pool-enumerating source or direct
evidence covering every candidate and plausible boundary case has been inspected; metric pages for guessed candidates
cannot show that nothing was missed.
If a table visibly ranks its rows in descending order by the very metric the question thresholds on, rows past the
first below-threshold entry are unnecessary. Keep the header and every row down through that boundary, and say why the
established ordering rules out everything ranked lower. The shortcut holds only when the visible header and row order
prove that monotone relationship.

RANK / TOP-N / CUTOFF RULE: for a top-N, an N-th place, or a highest/lowest-within-a-set question, produce one Markdown
table ranking the candidate pool by the deciding metric — candidate name, metric value, and a source ref on every row.
Finalization waits until that table is complete and the chosen candidate agrees with it.

SET / FILTER RULE: for all/every/which-N/identify-the-set questions, first enumerate the whole candidate pool in a
table, then show the filtered set plus one excluded near-miss and the condition that knocks it out. Every surviving
candidate carries its own citation; a single citation covering the whole set is insufficient.

SOURCE-DIVERSITY RULE: when the sole cited carrier of a decisive claim is Wikipedia or another aggregator, search or
fetch the originating publisher (gov, org, official statistics, academic) and cite that instead. Wikipedia alone is
tolerable for uncontroversial background — never for the deciding fact.

PROVENANCE AUTHORITY: The evidence ledger ranks each retained source by provenance authority
(official_pdf > institutional > primary_data > aggregator > encyclopedia > other). When retaining
evidence via retain_evidence, prefer official or institutional sources (exam boards, government
agencies, academic publishers, .gov/.edu/.org PDF documents) over third-party aggregators
(SaveMyExams, SimpleStudy, revision sites). When two sources carry the same decisive fact,
retain the higher-authority one and cite it in the final answer. The harness presents retained
evidence sorted by authority tier; cite the topmost source that establishes each claim.

A search snippet counts as evidence when its visible text carries the premise directly. If later retrieval must be
combined with that snippet, retain its smallest decisive lines before moving on; otherwise the snippet can drop out of
active context while staying reachable in VFS. Among observed sources of comparable authority and scope, keep the
excerpt that states the whole needed premise most directly and compactly, and do not fetch a wider copy just to
replace a snippet that already suffices. A search hit from the named official page counts as inspection when its
visible text carries the needed fact — retain the snippet rather than fetching the page merely because the question
names it. Reach for fetch_page only when the snippet is missing necessary context or when inspecting a discovered page
is the straightest remaining route. fetch_page takes a full URL, including one found inside a search result or another
page; never assemble a URL from a guessed site pattern.
Everything searched or fetched lands in VFS. On a long page, pinpoint the relevant lines with VFS search before
widening a small window with VFS read. A large fetch ships question-ranked context windows alongside its
head/middle/tail preview — look through those windows before searching the page again. Give every VFS search both an
exact regex pattern and a semantic query; the harness runs regex first and folds in embedding hits only when regex
fails or comes back empty. For tables, hold the relevant row together with its title, series labels, year labels, and
headers. PDF extraction sometimes drops chart values ahead of the heading or labels they belong to — when a matched
title has no data beside it, look both before and after it instead of assuming the table trails the title. Rebuilding
a flattened chart is allowed only when the excerpt shows a complete rectangle: N ordered category labels, M series
labels, and exactly M groups of N data values once axis ticks are set aside. Spell that mapping out and cross-check it
against the page heading, totals, shares, or neighboring prose; without the full visible structure, no cell may be
inferred from line order.
For a question about a specific date, edition, or historical version, inspect a result whose title and scope match
that exact period before touching broader or current-data pages, and never revise a period-specific value using a
source that visibly covers a different period. Rolling statistical tables can restate rows labeled with past dates;
when the question is about what was reported then, the contemporaneous archived release wins.
When inspected sources clash, settle it on scope, authority, date, and fit to the question. A source stating the
question's identifying conditions and the requested value together is an internally consistent account — keep it. A
differently scoped or differently measured value is a limitation to mention, not a license to rerun near-identical
searches. Once additional searching merely reproduces the clash, finalize the best-supported answer and note the
discrepancy in a sentence.
The opening evidence questions steer retrieval; they are not a checklist that must stay material. A completed filter
or a supported elimination can render a broader question moot. One thing never lapses: an explicit instruction in the
original question to retrieve or report from a named source, edition, page, report, or dataset cannot be satisfied by
a different proof route. Before finalizing, verify every premise the current answer and its derivation actually lean
on against words or table cells visible in the supplied source records — memory of a source is not visible evidence.
When a material row or relationship is missing from the excerpt, chase it with VFS search or fetch the discovered
page; if it stays unavailable, disclose the limitation rather than silently filling it in.

Call update_research_state whenever evidence moves the current best answer, its decisive support, or the most pressing
open question. That prose state is working memory, echoed back every turn — keep it from decaying into a search log.
Retain only displayed lines that directly confirm or contradict a material premise; never retain a source on the off
chance of later extraction. For a flattened table or chart, retain one continuous range holding the data values,
ordered category labels, series labels, and title together, even when axis ticks or blank spacing sit in between —
isolated number lines plus a detached title lose the mapping a table claim depends on. For a descending ranked table
cut by a numeric threshold, retain one continuous range from the header down through the first below-threshold row so
the qualifying rows and the exhaustive cutoff stay inspectable as a unit.

Keep going while any real uncertainty could still flip the answer. Before finalizing on fetched-page evidence, save
every decisive excerpt via retain_evidence. Once the claim resolves the question and its material premises hold, make
ready_to_finalize the last tool of the response. Its reason lays out the derivation and cites source references like
[P1] or [S1.2], with no line ranges encoded in prose; the harness assembles the answer from the cited source records.
A decisive search snippet may be cited unretained only when finalizing on the spot — retain it before any later
retrieval that will have to combine with it.

A failed tool call is an observation: fix the call or change course. Calls within one response run in order, so no
call may depend on output it has not seen. When exact arguments for several independent fetches, reads, or retentions
over an already-known finite candidate set are in hand, send them together in a single response. Never batch rival
searches against the same uncertainty — run one, read its results, then pick the next route. Each distinct operation
appears at most once per response."""

RULING_RECAST_CHARTER ="""\
Produce the full best current answer to the original question as polished Markdown written for the reader. Any
output-only or formatting constraint stated in the original question is binding; absent one, write substantial prose
whose structure scales with the answer. Neither the expected answer, the prior answer, the investigator's prose, nor
your internal knowledge counts as evidence — only the supplied source records do.

The investigator's present conclusion is the intended answer and its derivation after research. Revise the prior
answer around it while checking each external premise against the supplied source records. Leave out factual claims
the answer does not need; an excluded candidate gets its one decisive failing condition, not background.

Lead with the direct conclusion. Short descriptive headings are for navigation, bullets for parallel findings, and a
Markdown table for candidates sharing the same comparison fields — none of which belongs on a short answer. Keep
paragraphs tight and the decisive comparison scannable. No references section, bibliography, source dump, raw URL, or
appendix of quoted evidence.

Settle the question head-on, say why the conclusion follows, and keep any genuinely relevant uncertainty visible. Drop
the exact internal source reference from the supplied record — [S1.2], [P3], and so on — directly behind the factual
claim it carries. Those references are private placeholders the harness later swaps for public citation numbers, so
never invent one, respell one, or hand-write a numeric citation marker. A derived claim needs no reference of its own
when its external operands are visibly supported close by and the derivation is written out. Mention a source
organization by name only where it naturally explains why the evidence carries weight. A value pulled from a table is
supported only while the supplied text keeps it attached to its row and column labels — never pin a value to a year,
category, or candidate the source record does not visibly attach it to. A csv_records field mechanically projects a
CSV header onto its selected rows; trust its named fields over counting positions inside the raw CSV quote. Back each
premise with the one most direct source that visibly establishes it, adding a second source only when the first cannot
carry the whole premise — weaker duplicates and merely corroborating background add nothing. When measurements
conflict across sources, keep the internally consistent record that states the question's identifying conditions and
requested value together; never splice a conflicting measurement from one source onto an answer supplied by another,
and mention a material discrepancy only in the sentence it takes to flag it. If the question asks what a source
explicitly reports, give that reported value and compare it directly — a recomputation answers a different question.
Wherever a threshold, ranking, ratio, or arithmetic step decides the outcome, show the input values and write the
expression or comparison for every candidate the result depends on (`105 - 81 = 24`, not just two scores and a
margin), and prefer the exact computed value over an indirect inequality whenever the operands allow it. For an
exhaustive conclusion (only, all, closest, a top-k set, an intersection), put enough of the candidate comparison into
the answer that no omitted candidate could change the result. Lead with the direct answer, then walk through the
decisive evidence and derivation in ordinary prose, without exposing process labels like candidate pool, boundary
check, proof of completeness, evidence requirement, audit, or research state. An exhaustive answer names the finite
set naturally, shows each qualifier's decisive values, and touches only the near misses that pin down the boundary; an
inventory source can bound the set, and independently verified candidate pages plus boundary near misses can do the
same when no single inventory page exists. Read strict inequalities literally — the strictly qualifying set comes
first, and an exactly-equal boundary value appears only as an excluded case. On identification or constraint
questions, show explicitly how the answer meets every condition the question states, descriptors and relationships
included. Where the question retrieves a finite set and pushes it through several filters, display the materially
narrowed set after each decisive filter rather than only the last survivor's properties.

Citation placement done right: `Essendon won 105-81 in 1984. [P1]`
Inside a Markdown table, the reference sits on each source-backed row, usually in its last relevant cell; the sole
reference for several rows must never sit on a separate line beneath the table.
Done wrong: a closing `Sources` list, a raw URL, an invented `[1]`, a citation-only line under a table, or a claim
whose only reference turns up paragraphs later.

ANSWER FORMAT: Begin the final answer with a single locked headline: `FINAL ANSWER: <answer in requested format>`.
Then add a `Proof of completeness:` section. When the question screens several candidates through shared conditions,
that section must contain a Markdown table headed by a short caption line reading `Determination grid`, with exactly
one row per candidate-condition pair in the column order `| candidate | condition | decisive value | verdict |`. The
verdict cell must start with the single word PASS or FAIL — never both, never prose. Repeat the candidate name on each
of its rows so every candidate is judged against the identical condition set. Name the first excluded near-miss and
the value that disqualifies it. Remove all hedge words (appears to be, likely, probably), all self-critique phrases
("The current answer mixes...", "This is confusing"), and any "process" narration. Every factual claim in both the
headline and the proof must carry a source ref immediately after it."""

FORMED_FORM_CHARTER ="""\
Cast an already-finished, evidence-backed research answer into the caller's structured output. No further research, no
added facts, no process narration, no prose outside the tool call. Keep the answer's meaning intact and fill every
field the supplied JSON Schema demands. Invoke submit_structured_output exactly once, passing the final output value
as the tool arguments themselves — never as JSON packed inside a string."""

SURVEY_CHARTER ="""\
Check an answer against the supplied external evidence. Watch for the classic failure: values that are individually
correct but pinned to the wrong dates, columns, categories, candidates, or relationships.

Rebuild the source facts first; only then judge the answer's claims. A value owns a year, column, category, or role
only while the visible source text keeps that link intact — never project a table header across omitted lines or lift
it from the answer. A csv_records field mechanically maps a CSV header onto its selected rows; read its named fields
rather than counting positions in the raw CSV quote. For each candidate able to affect the result, classify every
condition of the question as supported true, supported false, or unknown — no evidence means unknown, never false.

On an identification question, every descriptive clause is its own premise. That a person is tied to an institution
says nothing about that institution's location, type, or status; when the supplied records leave such a required
property unestablished, mark it unknown and return CONTINUE. When the question points at an entity indirectly —
through a quotation, a work, an event, a relationship — the mapping from clue to entity is itself a material premise:
demand visible evidence for it however familiar it feels, because support for the resulting name alone never shows why
the name fits the clue.
When the original question insists on retrieval or reporting from a named source, edition, page, report, or dataset,
confirm the supplied records establish exactly that source and scope; a stand-in fails the instruction even while
agreeing with the conclusion. The source inventory is discovery metadata, not evidence — if the answer leans on a
stand-in while the inventory shows a result from the required publisher at matching scope, return CONTINUE naming that
one direct result. Conversely, never demand a stronger duplicate that the question's wording does not require.

Omission from a source proves absence only when that source visibly is a complete inventory at the needed scope.
One supported disqualifying condition finishes a candidate; its other conditions need nothing. For a surviving
candidate with several unknowns, ask for just the single cheapest observation that could eliminate or advance it, and
leave its later conditions unflagged until it survives that check. A CONTINUE audit carries exactly one MISSING line,
matching the one observation its verdict names.
Rows split by a visible `...` are not neighbors: never rebuild ordinal ranks or a ranking cutoff by welding the rows
on either side, and return CONTINUE whenever the omitted rows could move the result.
A finished comparison on one condition may shrink the candidate set, after which only survivors need support on the
rest — a full candidate-by-condition matrix is unnecessary once supported elimination reaches the same conclusion.
Never merge an eligibility condition from one source with a requested value from another whose measurements disagree.
A single supplied record stating all identifying conditions and the requested value together is the internally
consistent account to keep; a record scoped or measured differently is a discrepancy, never an operand for a hybrid.
Never bless or draft a replacement that keeps a candidate while its own chosen evidence account fails that candidate
on a selection condition — either an internally consistent supplied account covers both eligibility and value, or the
verdict is CONTINUE.

Before ruling, list nothing beyond:
- the factual premises the current answer actually asserts; and
- the unresolved facts whose truth could flip the answer to the original question.

Skip auditing the opening research plan and any fact the conclusion no longer rests on. Give each material premise or
result-changing unknown one short line, in exactly one of these forms:
SUPPORTED [source ref]: <the visible source words that establish this premise>
DERIVED [source refs]: <the arithmetic or logical derivation from externally supported operands>
MISSING: <the premise not explicitly established by any supplied source record>
CONTRADICTED [source ref]: <the visible source words that contradict this premise>

A MISSING line is reserved for a genuinely unresolved premise; when nothing is missing, write no MISSING line at all —
never `MISSING: none`, `MISSING: not applicable`, or any other filler. A READY verdict tolerates no MISSING line. One
premise per line. A source ref stripped of its establishing words is not support. Judge from the supplied source
records alone — the answer and internal knowledge are not evidence. A contradiction that explains why a candidate was
excluded supports the exclusion and is no error in the answer. Arithmetic, set operations, decade membership,
threshold comparisons, and ordering qualify as DERIVED without further external citation once every external operand
is SUPPORTED; the DERIVED line must display the calculation or logical step and cite the source refs holding its
operands, and may never smuggle in a missing external operand. A value fully computable from supported operands is not
MISSING for want of a source stating it verbatim — it is DERIVED, and never both. A familiar categorical property may
likewise be DERIVED from explicit defining source facts when the classification is unambiguous; show those facts
instead of demanding the question's exact label from the source.

After the premise lines, exactly one verdict:
VERDICT READY
VERDICT CONTINUE: <the one most important missing observation>
VERDICT REVISE
<a complete replacement answer with exact supplied source refs such as [P1]>

READY demands that every factual statement match the rebuilt source facts, that the conclusion follow, and that no
unknown could shift the result; both READY and REVISE are ruled out while any material premise is MISSING. A source
contradiction against a factual statement the answer asserts forces REVISE; one that merely explains a candidate's
exclusion coexists with READY. REVISE applies only when the supplied evidence settles the question yet the answer is
wrong or unsupported — its replacement cites exact supplied source refs behind each supported claim, opens with the
corrected conclusion, and neither repeats the old answer nor narrates the correction. When the evidence cannot settle
the result, the verdict is CONTINUE."""


SET_WARRANT_MANDATES_MOVE =_contract_m (
"set_evidence_requirements",
"Record only unanswered evidence questions whose externally verifiable premises the final answer needs. "
"Do not record source availability, table structure, or retrieval work.",
{
"requirements":{
"type":"string",
"minLength":1 ,
"description":"One unanswered evidence question per line, with no candidate or expected answer filled in.",
}
},
("requirements",),
)
MANDATES_MOVES =[SET_WARRANT_MANDATES_MOVE ]

MOVE_CATALOG =[
_contract_m (
"search_web",
"Search the web. Full results are retained in VFS and each result receives a source reference.",
{
"query":{"type":"string","minLength":1 },
"num":{"type":"integer","minimum":1 ,"maximum":25 },
},
("query","num"),
),
_contract_m (
"fetch_page",
"Fetch one full URL when a search snippet lacks context or a page exposes a promising direct link. "
"Full content is retained in VFS and receives a source reference.",
{"url":{"type":"string","minLength":1 }},
("url",),
),
_contract_m (
"vfs_read",
"Read an inclusive line range from one VFS key. Large ranges are paginated. Bounds accept 1-based line "
"numbers or stable line IDs.",
{
"key":{"type":"string","minLength":1 },
"start_line":{"type":["string","integer","null"]},
"end_line":{"type":["string","integer","null"]},
},
("key","start_line","end_line"),
),
_contract_m (
"vfs_list",
"List VFS keys, optionally restricted to a literal prefix.",
{"prefix":{"type":"string"}},
("prefix",),
),
_contract_m (
"vfs_write",
"Write or overwrite one VFS file. VFS operations do not create VFS audit entries.",
{
"key":{"type":"string","minLength":1 },
"content":{"type":"string"},
},
("key","content"),
),
_contract_m (
"vfs_delete",
"Delete one VFS key.",
{"key":{"type":"string","minLength":1 }},
("key",),
),
_contract_m (
"vfs_search",
"Search exact keys, wildcard key patterns such as page://*, or * for all VFS files. Supply an exact regex "
"pattern and a semantic query for the same information need. The harness starts with regex and adds embedding "
"results only when regex fails or finds nothing. Continue paginated regex matches with next_cursor.",
{
"pattern":{"type":"string","minLength":1 },
"query":{"type":"string","minLength":1 },
"targets":{
"type":"array",
"items":{"type":"string","minLength":1 },
"minItems":1 ,
},
"cursor":{
"type":"integer",
"minimum":0 ,
"description":"Match offset returned as next_cursor by a previous identical search.",
},
},
("pattern","query","targets"),
),
_contract_m (
"update_research_state",
"Replace the prose working memory used on later turns. Call when the best answer, decisive support, "
"or most important unresolved question changes.",
{
"state":{
"type":"string",
"minLength":1 ,
"description":"Current best answer, decisive observed source refs, and the next unresolved question.",
}
},
("state",),
),
_contract_m (
"ready_to_finalize",
"Propose or confirm finalization after decisive external evidence has been inspected. This is premature when "
"an observed search result exposes an uninspected official or primary source for a premise currently supported "
"only by a secondary source. Every cited fetched-page source must already have a retained evidence excerpt.",
{
"reason":{
"type":"string",
"minLength":1 ,
"description":"Explain readiness and cite decisive source refs such as [S1.2] or [P1].",
}
},
("reason",),
),
]

HOLD2_WARRANT_MOVE =_contract_m (
"retain_evidence",
"Keep one directly useful, already displayed source excerpt in persistent research memory. "
"Do not retain a source merely for possible later extraction. For flattened tables, retain one continuous "
"range that includes the values, category labels, series labels, and title rather than isolated numeric lines. "
"Every date, year, threshold, or other number asserted in the note must also be visible in the selected range.",
{
"source":{
"type":"string",
"minLength":1 ,
"description":"An observed source reference such as S1.2 or P3, or its exact VFS key.",
},
"note":{
"type":"string",
"minLength":1 ,
"description":"What the visible source text establishes and which part of the question it informs.",
},
"start_line":{
"type":["string","integer"],
"description":"First displayed line number or stable line ID containing the evidence.",
},
"end_line":{
"type":["string","integer"],
"description":"Last displayed line number or stable line ID containing the evidence.",
},
},
("source","note","start_line","end_line"),
)
MOULT_RESIDUAL_ORIGINS_MOVE =_contract_m (
"discard_remaining_sources",
"Discard every still-unretained source from the latest retrieval and finish its evidence review.",
{
"reason":{
"type":"string",
"minLength":1 ,
"description":"Why every still-unretained visible source does not materially inform the research.",
}
},
("reason",),
)
WARRANT_SCREEN_MOVES =[HOLD2_WARRANT_MOVE ,MOULT_RESIDUAL_ORIGINS_MOVE ]
MOVE_CATALOG .insert (-1 ,HOLD2_WARRANT_MOVE )


        # ── v37: determination grid (donor: low-median-cost lineage) ──────────────────
        # The writer contract requests a machine-readable candidate x condition table
        # under the proof section. Everything in this module is plain string work: it
        # reads that table, computes the surviving candidate set with set logic, and
        # rewrites the locked headline ONLY when the computation contradicts it and a
        # stack of guards agrees the rewrite cannot turn a right answer into a wrong
        # one. Zero model calls — that is the whole point of adopting it.

_LATTICE_TITLECARD_RE =re .compile (
r"(?:determination|decision)\s+(?:grid|matrix)|proof of completeness",re .I 
)
_LATTICE_CANON2_RUNG_RE =re .compile (r"^\|?[\s:|+-]*\|[\s:|+-]*$")
_CLEARS2_LEAD_RE =re .compile (r"^\W{0,3}(?:pass|yes|true|meets?|satisf|qualif|clears?)",re .I )
_LAPSES_LEAD_RE =re .compile (
r"^\W{0,3}(?:fail|no\b|false|exclude|miss(?:es)?|does\s*not|disqualif)",re .I 
)
_CLEARS2_VOCABLE_RE =re .compile (r"\b(?:pass(?:es|ed)?|qualif\w*|clears?|meets|satisfies)\b",re .I )
_LAPSES_VOCABLE_RE =re .compile (r"\b(?:fail(?:s|ed)?|exclude[ds]?|disqualif\w*|misses)\b",re .I )
_HIDDEN2_BADGE_RE =re .compile (r"\s*\[(?:S\d+(?:\.\d+)?|P\d+)\]")
_LATTICE_BARRED_LABELS =frozenset (
"candidate candidates name names entity entities item items option options subject "
"constraint constraints criterion criteria condition conditions test verdict value "
"no nr num #".split ()
)
_LATTICE_STOPWORDS =frozenset (
"a an and are as at be by for from in is it of on or the to was were with".split ()
)
LATTICE_RULING_CELL_MAX =40 # longer cells are prose commentary, not verdicts
LATTICE_LABEL_MAX =80 # candidate / condition cell width the contract asks for
LATTICE_RUNWAY_RUNGS =2 # header row plus its |---|---| rule ahead of data rows
LATTICE_KEEPER_MAX =12 # a survivor list longer than this is not a determination
LATTICE_MASTHEAD_CHAR_MAX =400 # nor is a computed headline this wide
_MASTHEAD_MARK_RE =re .compile (r"^\s*(?:\*\*|#+\s*)?FINAL ANSWER\s*:\s*",re .I )
_NEG2_MASTHEAD_RE =re .compile (
r"\b(?:none(?:\s+of)?|neither|not\s+any\s+of|there\s+(?:are|were|is)\s+no"
r"|no\s+(?:candidate|entity|item|option|one|company|team|country|city|person))\b",
re .I ,
)
_WAIVER2_MASTHEAD_RE =re .compile (
r"cannot be (?:definitively |conclusively |reliably )?(?:determined|answered|established"
r"|resolved|identified)|insufficient (?:evidence|data|information)"
r"|\bunable to (?:conclude|decide|determine|settle)"
r"|\b(?:remains?|is) (?:unclear|unresolved|inconclusive)"
r"|\b(?:needs?|requires?) (?:more|further|additional) (?:evidence|research|data)",
re .I ,
)
_TOPPICK_COUNT_M =r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
_TOPPICK_GRADE_M =(
r"(?:highest|largest|biggest|greatest|most|top|smallest|lowest|shortest|longest|"
r"oldest|newest|earliest|latest|fastest|slowest|best|worst)"
)
_TOPPICK_RE_M =re .compile (
r"^\s*\(?[a-z]?\)?\s*ranking\b"
rf"|\btop\s+{_TOPPICK_COUNT_M}\b"
rf"|\bthe\s+{_TOPPICK_COUNT_M}\s+{_TOPPICK_GRADE_M}\b"
rf"|\b{_TOPPICK_GRADE_M}[- ]\w+\s+(?:{_TOPPICK_COUNT_M}\s+)?\w*\s*(?:are|is|were|was)\b",
re .I |re .M ,
)
_LEAD_PREAMBLE2_RE =re .compile (
r"^\s*(?:okay|ok|alright)\s*[,.:;!-]"
r"|^\s*(?:first|next|now|then)\s*,"
r"|^\s*(?:let me|let's|to answer this)\b"
r"|^\s*i (?:need|will|should|am going|'ll|'m going)\b"
r"|^\s*we (?:need|should|will|must)\b"
r"|^\s*#*\s*(?:draft|scratch|reasoning|thinking)\s*:",
re .I ,
)


_TERMWISE_TERM_RE =re .compile (r"[a-z0-9][a-z0-9'.\-]{2,}")
_BROAD_MARKED_QUOTATION_RE =re .compile (r'"([^"]{24,})"|(?<![a-z0-9])\'([^\']{24,})\'',re .IGNORECASE )
_TERMWISE_SKIP_TERMS =frozenset (
"the and for with from that this have has was were are is been its their which what when where who how many much "
"according also into over under between during against about after before while other more most than".split ()
)


@dataclass 
class MeridianBeacon :
    ref :str 
    key :str 
    title :str 
    url :str 
    content :str 
    receipt_id :str |None 
    result_id :str |None 
    preview_chars :int =8_000 


@dataclass 
class MeridianChart :
    citations :list [CitationRef ]
    source_indices :dict [str ,int ]


# ── Claim-Source Ledger (replaces retained_evidence + research_state) ─────────
# This is the root replacement for the evidence_state_flow dimension.
# Instead of flat retained_evidence dict + free-text research_state, evidence
# flows through a structured ledger that tags every source with provenance
# authority. Answer production systematically prefers official/institutional
# sources over aggregators, fixing source_fidelity losses.

_AUTHORITY_TIER_NAMES ={
0 :"official_pdf",
1 :"institutional",
2 :"primary_data",
3 :"aggregator",
4 :"encyclopedia",
5 :"other",
}

_AGGREGATOR_PATTERNS =re .compile (
r"(?:savemyexams|simplestudying|simplelearning|studyrocket"
r"|revisionworld|physicsandmathstutor|senecalearning|tutor2u"
r"|thestudentroom|sparknotes|cliffsnotes|shmoop|gradesaver)",
re .I ,
)

_WIKI_PATTERNS =re .compile (r"(?:wikipedia\.org|britannica\.com|encyclopedia\.com)",re .I )

_INSTITUTIONAL_PATTERNS =re .compile (r"\.(?:gov|edu|ac\.uk|int)\b",re .I )

_EXAM_BOARD_PATTERNS =re .compile (
r"\b(?:aqa|ocr|edexcel|wjec|pearson|ofqual|cambridgeassessment"
r"|cambridgeinternational|cie)\b",
re .I ,
)


@dataclass
class SourceAuthority :
    tier :int
    label :str


@dataclass
class LedgerEntry :
    source_ref :str
    authority :SourceAuthority
    evidence :dict [str ,Any ]


def _classify_source_authority (url :str ,title :str )->SourceAuthority :
    """Deterministic provenance authority from URL and title patterns."""
    url_l =(url or "").lower ()
    title_l =(title or "").lower ()
    combined =f"{url_l} {title_l}"

    is_pdf =url_l .endswith (".pdf")or ".pdf?"in url_l
    is_institutional_domain =bool (_INSTITUTIONAL_PATTERNS .search (url_l ))
    is_org =".org/"in url_l or ".org."in url_l or url_l .endswith (".org")

    # Check aggregator domains FIRST — aggregator URLs often contain exam board
    # names in their path (e.g. savemyexams.com/…/aqa/) which would false-positive
    # the exam board pattern below.
    if _AGGREGATOR_PATTERNS .search (url_l ):
        return SourceAuthority (tier =3 ,label ="aggregator")

    if is_pdf and (is_institutional_domain or is_org ):
        return SourceAuthority (tier =0 ,label ="official_pdf")

    if _EXAM_BOARD_PATTERNS .search (combined ):
        if is_pdf :
            return SourceAuthority (tier =0 ,label ="official_pdf")
        return SourceAuthority (tier =1 ,label ="institutional")

    if _WIKI_PATTERNS .search (url_l ):
        return SourceAuthority (tier =4 ,label ="encyclopedia")

    if is_institutional_domain or is_org :
        return SourceAuthority (tier =1 ,label ="institutional")

    if is_pdf :
        return SourceAuthority (tier =2 ,label ="primary_data")

    return SourceAuthority (tier =5 ,label ="other")


class ClaimSourceLedger :
    """Structured evidence state tracking provenance authority per source.

    Replaces the flat retained_evidence dict + free-text research_state with
    an authority-ranked evidence ledger. Each retained source is classified by
    provenance tier (official_pdf > institutional > primary_data > aggregator >
    encyclopedia > other). Serialization presents evidence ranked by authority
    so answer production systematically prefers official/institutional sources."""

    def __init__ (self )->None :
        self .entries :dict [str ,LedgerEntry ]={}
        self .hypothesis :str =""
        self .audit_directive :str =""

    def register (
    self ,
    source_ref :str ,
    evidence :dict [str ,Any ],
    url :str ="",
    title :str ="",
    )->None :
        url =url or str (evidence .get ("url",""))
        title =title or str (evidence .get ("title",""))
        authority =_classify_source_authority (url ,title )
        existing =self .entries .get (source_ref )
        if existing is not None :
            merged ={**existing .evidence ,**evidence }
            old_q =str (existing .evidence .get ("quote","")).strip ()
            new_q =str (evidence .get ("quote","")).strip ()
            if old_q and new_q :
                if old_q in new_q :
                    merged ["quote"]=new_q
                elif new_q in old_q :
                    merged ["quote"]=old_q
                else :
                    merged ["quote"]=f"{old_q}\n\n{new_q}"
            old_n =str (existing .evidence .get ("research_note","")).strip ()
            new_n =str (evidence .get ("research_note","")).strip ()
            if old_n and new_n :
                merged ["research_note"]=f"{old_n}\n{new_n}"
            self .entries [source_ref ]=LedgerEntry (
            source_ref =source_ref ,
            authority =authority ,
            evidence =merged ,
            )
        else :
            self .entries [source_ref ]=LedgerEntry (
            source_ref =source_ref ,
            authority =authority ,
            evidence =evidence ,
            )

    def ranked_entries (self )->list [LedgerEntry ]:
        """Entries sorted by authority tier (best first), then source ref."""
        return sorted (
        self .entries .values (),
        key =lambda e :(e .authority .tier ,e .source_ref ),
        )

    def authority_for (self ,ref :str )->SourceAuthority :
        entry =self .entries .get (ref )
        if entry is not None :
            return entry .authority
        return SourceAuthority (tier =5 ,label ="other")

    def serialize_evidence (self )->str :
        """Serialize retained evidence ranked by provenance authority."""
        if not self .entries :
            return ""
        ranked =self .ranked_entries ()
        items :list [dict [str ,Any ]]=[]
        for entry in ranked :
            item ={
            k :v
            for k ,v in entry .evidence .items ()
            if k in {"source_ref","title","url","quote","csv_records"}
            }
            item ["provenance_authority"]=entry .authority .label
            note =entry .evidence .get ("research_note","")
            if note :
                item ["research_note"]=note
            items .append (item )
        return json .dumps (items ,ensure_ascii =False ,indent =2 )


class MeridianHelm :
    def __init__ (self ,inquiry :str ="")->None :
        self .question =inquiry
        self .vfs :dict [str ,str ]={}
        self .sources :dict [str ,MeridianBeacon ]={}
        self .line_locations :dict [str ,tuple [str ,int ]]={}
        self .focused_lines :dict [str ,set [int ]]={}
        self .focused_line_order :dict [tuple [str ,int ],None ]={}
        self .focused_line_chars =0
        self .reasoning_observations :list [str ]=[]
        self .reasoning_observation_chars =0
        self .source_slices :dict [str ,list [CitationSlice ]]={}
        self .retrieval_receipts :dict [str ,dict [str ,Any ]]={}
        self .retrieval_output_cache :dict [str ,dict [str ,Any ]]={}
        self .vfs_operation_receipts :dict [str ,dict [str ,Any ]]={}
        self .claim_ledger =ClaimSourceLedger ()
        self .document_embeddings :dict [
        tuple [str ,str ],
        list [tuple [dict [str ,Any ],list [float ]]],
        ]={}
        self .review_source_refs :set [str ]=set ()
        self .evidence_requirements :str |None =None
        self .budget_snapshot :dict [str ,float ]|None =None
        self .search_count =0
        self .page_count =0

    @property
    def retained_evidence (self )->dict [str ,dict [str ,Any ]]:
        return {ref :entry .evidence for ref ,entry in self .claim_ledger .entries .items ()}

    @property
    def research_state (self )->str :
        return self .claim_ledger .hypothesis

    @research_state .setter
    def research_state (self ,value :str )->None :
        self .claim_ledger .hypothesis =value

    @property
    def audit_gap (self )->str :
        return self .claim_ledger .audit_directive

    @audit_gap .setter
    def audit_gap (self ,value :str )->None :
        self .claim_ledger .audit_directive =value

    @staticmethod 
    def _line_id_m (key :str ,index_m :int ,text :str )->str :
        digest_m =hashlib .sha256 (f"{key}\0{index_m}\0{text}".encode ()).hexdigest ()[:10 ]
        return f"L{digest_m}"

    def render_lines (
    self ,
    key :str ,
    indices_m :list [int ]|range |None =None ,
    )->list [dict [str ,Any ]]:
        rungs =self .vfs [key ].splitlines ()or [""]
        selected_m =range (len (rungs ))if indices_m is None else indices_m 
        output :list [dict [str ,Any ]]=[]
        for index_m in selected_m :
            if index_m <0 or index_m >=len (rungs ):
                continue 
            rung_id =self ._line_id_m (key ,index_m ,rungs [index_m ])
            self .line_locations [rung_id ]=(key ,index_m )
            output .append ({"line_id":rung_id ,"line":index_m +1 ,"text":rungs [index_m ]})
        return output 

    def focused_excerpts (self )->list [dict [str ,Any ]]:
        extracts :list [dict [str ,Any ]]=[]
        for key ,indices_m in self .focused_lines .items ():
            origin_badges =[f"[{origin_m.ref}]"for origin_m in self .sources .values ()if origin_m .key ==key ]
            extracts .append (
            {
            "vfs_key":key ,
            "source_refs":origin_badges ,
            "lines":self .render_lines (key ,sorted (indices_m )),
            }
            )
        return extracts 

    def remember_focused_lines (self ,key :str ,indices_m :set [int ]|range )->None :
        rungs =self .vfs [key ].splitlines ()or [""]
        valid_indices_m =sorted ({index_m for index_m in indices_m if 0 <=index_m <len (rungs )})
        beamed =self .focused_lines .setdefault (key ,set ())
        for index_m in valid_indices_m :
            if index_m in beamed :
                continue 
            beamed .add (index_m )
            location_m =(key ,index_m )
            self .focused_line_order [location_m ]=None 
            self .focused_line_chars +=len (rungs [index_m ])+80 
        if not beamed :
            self .focused_lines .pop (key ,None )
        while (
        self .focused_line_chars >MERIDIAN_BEAM_MEMORY_GIRTH 
        and len (self .focused_line_order )>1 
        ):
            old_slot_m ,old_index_m =next (iter (self .focused_line_order ))
            self .forget_focused_lines (old_slot_m ,{old_index_m })

    def forget_focused_lines (
    self ,
    key :str ,
    indices_m :set [int ]|None =None ,
    )->None :
        beamed =self .focused_lines .get (key )
        if beamed is None :
            return 
        removed_m =set (beamed if indices_m is None else beamed &indices_m )
        rungs =self .vfs .get (key ,"").splitlines ()or [""]
        for index_m in removed_m :
            self .focused_line_order .pop ((key ,index_m ),None )
            if 0 <=index_m <len (rungs ):
                self .focused_line_chars -=len (rungs [index_m ])+80 
        beamed .difference_update (removed_m )
        if not beamed :
            self .focused_lines .pop (key ,None )
        self .focused_line_chars =max (0 ,self .focused_line_chars )

    def clear_focused_lines (self )->None :
        for key in tuple (self .focused_lines ):
            self .forget_focused_lines (key )

    def remember_reasoning_observation (self ,musing :str |None )->None :
        sighting2 =str (musing or "").strip ()
        if not sighting2 or not re .search (r"\b(?:S\d+(?:\.\d+)?|P\d+)\b",sighting2 ):
            return 
        if sighting2 in self .reasoning_observations :
            return 
        self .reasoning_observations .append (sighting2 )
        self .reasoning_observation_chars +=len (sighting2 )
        while (
        self .reasoning_observation_chars >MERIDIAN_BEAM_MEMORY_GIRTH 
        and len (self .reasoning_observations )>1 
        ):
            removed_m =self .reasoning_observations .pop (0 )
            self .reasoning_observation_chars -=len (removed_m )

    def pending_review_excerpts (self )->list [dict [str ,Any ]]:
        extracts :list [dict [str ,Any ]]=[]
        for ref ,origin_m in self .sources .items ():
            if ref not in self .review_source_refs :
                continue 
            extracts .append (
            {
            "source_ref":f"[{ref}]",
            "vfs_key":origin_m .key ,
            "title":origin_m .title ,
            "url":origin_m .url ,
            "text":self .bounded_preview (
            origin_m .key ,
            max_serialized_chars =origin_m .preview_chars ,
            ),
            }
            )
        return extracts 

    def glimpse (self ,key :str ,max_chars :int =8_000 )->list [dict [str ,Any ]]:
        rungs =self .vfs [key ].splitlines ()or [""]
        if len (self .vfs [key ])<=max_chars :
            return self .render_lines (key )
        outlay =max_chars //3 
        groups_m :list [list [int ]]=[[],[],[]]
        positions_m =[range (len (rungs )),range (len (rungs )//3 ,len (rungs )),range (len (rungs )-1 ,-1 ,-1 )]
        for group_m ,position_m in zip (groups_m ,positions_m ,strict =True ):
            used_m =0 
            for index_m in position_m :
                if used_m and used_m +len (rungs [index_m ])+1 >outlay :
                    break 
                group_m .append (index_m )
                used_m +=len (rungs [index_m ])+1 
            group_m .sort ()
        selected_m =sorted (set (groups_m [0 ]+groups_m [1 ]+groups_m [2 ]))
        return self .render_lines (key ,selected_m )

    def bounded_preview (
    self ,
    key :str ,
    max_serialized_chars :int ,
    )->list [dict [str ,Any ]]:
        wording_outlay =max_serialized_chars 
        glimpse :list [dict [str ,Any ]]=[]
        for _attempt_m in range (4 ):
            glimpse =self .glimpse (key ,max_chars =wording_outlay )
            serialized_girth =len (
            json .dumps (
            glimpse ,
            ensure_ascii =False ,
            separators =(",",":"),
            )
            )
            if serialized_girth <=max_serialized_chars :
                return glimpse 
            wording_outlay =max (
            100 ,
            int (wording_outlay *max_serialized_chars /serialized_girth *0.9 ),
            )
        return glimpse 

    def resolve_targets (self ,targets_m :list [str ])->list [str ]:
        slots_m :list [str ]=[]
        for target_m in targets_m :
            if target_m =="*":
                matches_m =list (self .vfs )
            elif any (char_m in target_m for char_m in "*?["):
                sieve =re .compile ("^"+re .escape (target_m ).replace (r"\*",".*").replace (r"\?",".")+"$")
                matches_m =[key for key in self .vfs if sieve .fullmatch (key )]
            elif target_m in self .vfs :
                matches_m =[target_m ]
            else :
                matches_m =[]
            slots_m .extend (matches_m )
        return list (dict .fromkeys (slots_m ))

    def citation_cuts (self ,key :str ,indices_m :list [int ]|range )->list [CitationSlice ]:
        content =self .vfs [key ]
        rungs =content .splitlines (keepends =True )or [content ]
        selected_m =sorted ({index_m for index_m in indices_m if 0 <=index_m <len (rungs )})
        if not selected_m :
            return []

        offsets_m =[0 ]
        for rung_x in rungs :
            offsets_m .append (offsets_m [-1 ]+len (rung_x ))

        groups_m :list [tuple [int ,int ]]=[]
        start =prior_m =selected_m [0 ]
        for index_m in selected_m [1 :]:
            if index_m !=prior_m +1 :
                groups_m .append ((start ,prior_m +1 ))
                start =index_m 
            prior_m =index_m 
        groups_m .append ((start ,prior_m +1 ))

        reaches :list [tuple [int ,int ]]=[]
        for start_rung ,end_rung in groups_m :
            start_offset_m =offsets_m [start_rung ]
            end_offset_m =offsets_m [end_rung ]
            if end_offset_m -start_offset_m <100 and len (content )>=100 :
                missing_m =100 -(end_offset_m -start_offset_m )
                start_offset_m =max (0 ,start_offset_m -(missing_m //2 ))
                end_offset_m =min (len (content ),end_offset_m +missing_m )
                start_offset_m =max (0 ,end_offset_m -100 )
            if reaches and start_offset_m <=reaches [-1 ][1 ]:
                reaches [-1 ]=(reaches [-1 ][0 ],max (reaches [-1 ][1 ],end_offset_m ))
            else :
                reaches .append ((start_offset_m ,end_offset_m ))
        return [CitationSlice (start =start ,end =end )for start ,end in reaches if end >start ]

    def packet_preview (
    self ,
    key :str ,
    max_chars :int =8_000 ,
    )->tuple [str ,list [CitationSlice ]]:
        content =self .vfs [key ]
        if len (content )<=max_chars :
            return content ,[CitationSlice (start =0 ,end =len (content ))]

        segment_girth =max_chars //3 
        middle_start_m =max (0 ,(len (content )-segment_girth )//2 )
        reaches =[
        (0 ,segment_girth ),
        (middle_start_m ,middle_start_m +segment_girth ),
        (len (content )-segment_girth ,len (content )),
        ]
        quotation ="\n\n...\n\n".join (content [start :end ]for start ,end in reaches )
        slices =[CitationSlice (start =start ,end =end )for start ,end in reaches ]
        return quotation ,slices 

    @staticmethod 
    def marked_line_indices (ground :str ,ref :str )->list [int ]:
        escaped_badge =re .escape (ref )
        patterns_m =(
        rf"\[{escaped_badge}\s*,\s*lines?\s+(\d+)(?:\s*(?:-|to)\s*(\d+))?\]",
        rf"\[{escaped_badge}\s*,\s*L(\d+)(?:\s*-\s*L?(\d+))?\]",
        rf"\[{escaped_badge}\]\s*[:,]?\s*lines?\s+(\d+)(?:\s*(?:-|to)\s*(\d+))?",
        rf"\[{escaped_badge}\]\s*[:,]?\s*L(\d+)(?:\s*-\s*L?(\d+))?",
        rf"\b{escaped_badge}\b\s*[:,]?\s*lines?\s+(\d+)(?:\s*(?:-|to)\s*(\d+))?",
        rf"\b{escaped_badge}\b\s*[:,]?\s*L(\d+)(?:\s*-\s*L?(\d+))?",
        )
        indices_m :set [int ]=set ()
        for sieve in patterns_m :
            for match_m in re .finditer (sieve ,ground ,flags =re .IGNORECASE ):
                start =int (match_m .group (1 ))
                end =int (match_m .group (2 )or start )
                if end <start :
                    start ,end =end ,start 
                indices_m .update (range (max (1 ,start )-1 ,end ))
        for bracket_m in re .findall (r"\[([^\]]+)\]",ground ):
            if re .search (rf"(?:^|[\s,;]){escaped_badge}(?:$|[\s,;:])",bracket_m )is None :
                continue 
            for match_m in re .finditer (
            r"\bL(\d+)(?:\s*-\s*L?(\d+))?",
            bracket_m ,
            flags =re .IGNORECASE ,
            ):
                start =int (match_m .group (1 ))
                end =int (match_m .group (2 )or start )
                if end <start :
                    start ,end =end ,start 
                indices_m .update (range (max (1 ,start )-1 ,end ))
        return sorted (indices_m )

    def source_evidence_indices (
    self ,
    key :str ,
    indices_m :list [int ]|range |set [int ],
    *,
    include_focused :bool =True ,
    )->list [int ]:
        rungs =self .vfs [key ].splitlines ()or [""]
        rung_census =len (rungs )
        candidates_m =set (indices_m )
        if include_focused :
            candidates_m .update (self .focused_lines .get (key ,set ()))
        selected_m ={index_m for index_m in candidates_m if 0 <=index_m <rung_census }
        for index_m in tuple (selected_m ):
            reach =_markdown2_lattice_reach (self ,key ,index_m )
            if reach is None :
                continue 
            selected_m .update (item_m ["line"]-1 for item_m in reach ["header"])
        if selected_m :
            header_m =_unravel_csv_rung (rungs [0 ])
            selected_rungs =[_unravel_csv_rung (rungs [index_m ])for index_m in selected_m ]
            if header_m is None or any (rung is None for rung in selected_rungs ):
                header_m =[]
                selected_widths_m =set ()
            else :
                selected_widths_m ={len (rung )for rung in selected_rungs if rung is not None }
            textual_fields_m =sum (bool (re .search (r"[A-Za-z]",field_m ))for field_m in header_m )
            if len (header_m )>=3 and len (header_m )in selected_widths_m and textual_fields_m >=len (header_m )//2 :
                selected_m .add (0 )
        return sorted (selected_m )

    def structured_csv_records (
    self ,
    key :str ,
    indices_m :list [int ]|range ,
    )->list [dict [str ,str ]]:
        rungs =self .vfs [key ].splitlines ()
        if not rungs or 0 not in indices_m :
            return []
        header_m =_unravel_csv_rung (rungs [0 ])
        if header_m is None :
            return []
        if len (header_m )<3 or len (set (header_m ))!=len (header_m ):
            return []
        records_m :list [dict [str ,str ]]=[]
        for index_m in indices_m :
            if index_m ==0 or not 0 <=index_m <len (rungs ):
                continue 
            rung =_unravel_csv_rung (rungs [index_m ])
            if rung is None :
                return []
            if len (rung )!=len (header_m ):
                return []
            records_m .append (dict (zip (header_m ,rung ,strict =True )))
        return records_m 

    def source_packet (
    self ,
    ground :str ,
    *,
    allow_preview :bool =True ,
    include_structured_csv :bool =False ,
    prefer_retained :bool =True ,
    )->list [dict [str ,Any ]]:
        mentioned_badges =list (dict .fromkeys (re .findall (r"\b(S\d+(?:\.\d+)?|P\d+)\b",ground )))
        badges :list [str ]=[]
        for ref in mentioned_badges :
            if re .fullmatch (r"S\d+",ref ):
                badges .extend (candidate_m for candidate_m in self .sources if candidate_m .startswith (f"{ref}."))
            else :
                badges .append (ref )
        badges .extend (origin_m .ref for origin_m in self .sources .values ()if origin_m .key in ground )
        badges =list (dict .fromkeys (badges ))
        single_origin_rung_indices :list [int ]=[]
        if len (badges )==1 :
            indices_m :set [int ]=set ()
            for match_m in re .finditer (
            r"\b(?:lines?\s+)?L(\d+)(?:\s*-\s*L?(\d+))?",
            ground ,
            flags =re .IGNORECASE ,
            ):
                start =int (match_m .group (1 ))
                end =int (match_m .group (2 )or start )
                if end <start :
                    start ,end =end ,start 
                indices_m .update (range (max (1 ,start )-1 ,end ))
            single_origin_rung_indices =sorted (indices_m )
        rung_ids =list (dict .fromkeys (re .findall (r"\bL[0-9a-f]{10}\b",ground )))
        manifest :list [dict [str ,Any ]]=[]
        for ref in badges :
            origin_m =self .sources .get (ref )
            if origin_m is None :
                continue 
            if prefer_retained and ref in self .claim_ledger .entries :
                held =self .claim_ledger .entries [ref ].evidence
                held_item ={
                key :value_m 
                for key ,value_m in held .items ()
                if key in {"source_ref","title","url","quote","csv_records"}
                }
                residual_beamed =self .focused_lines .get (origin_m .key )
                if residual_beamed :
                    selected_indices_m =self .source_evidence_indices (
                    origin_m .key ,
                    residual_beamed ,
                    )
                    beamed_item :dict [str ,Any ]={
                    "source_ref":f"[{ref}]",
                    "title":origin_m .title ,
                    "url":origin_m .url ,
                    "quote":"\n".join (
                    item_m ["text"]
                    for item_m in self .render_lines (origin_m .key ,selected_indices_m )
                    ),
                    }
                    if include_structured_csv :
                        csv_records_m =self .structured_csv_records (
                        origin_m .key ,
                        selected_indices_m ,
                        )
                        if csv_records_m :
                            held_records =list (held_item .get ("csv_records",[]))
                            beamed_item ["csv_records"]=[
                            *held_records ,
                            *(
                            chalk 
                            for chalk in csv_records_m 
                            if chalk not in held_records 
                            ),
                            ]
                        self .source_slices [ref ]=_weld_mark_reaches (
                        self .source_slices .get (ref ,[]),
                        self .citation_cuts (origin_m .key ,selected_indices_m ),
                        )
                    held_item =_weld_origin_sheaves (
                    [held_item ],
                    [beamed_item ],
                    )[0 ]
                manifest .append (held_item )
                continue 
            origin_rung_ids =[
            rung_id for rung_id in rung_ids if self .line_locations .get (rung_id ,(None ,))[0 ]==origin_m .key 
            ]
            marked_line_indices =sorted (set (self .marked_line_indices (ground ,ref ))|set (single_origin_rung_indices ))
            selected_indices_m :list [int ]|range |None 
            mark_indices :list [int ]|range |None 
            if origin_rung_ids :
                rung_indices =[self .line_locations [rung_id ][1 ]for rung_id in origin_rung_ids ]
                warrant_slat =set (rung_indices )
                selected_indices_m =self .source_evidence_indices (
                origin_m .key ,
                warrant_slat ,
                include_focused =False ,
                )
                mark_indices =selected_indices_m 
                quotation ="\n".join (item_m ["text"]for item_m in self .render_lines (origin_m .key ,selected_indices_m ))
            elif marked_line_indices :
                selected_m =set (marked_line_indices )
                mark_indices =self .source_evidence_indices (
                origin_m .key ,
                selected_m ,
                include_focused =False ,
                )
                selected_indices_m =mark_indices 
                quotation ="\n".join (
                f"{item_m['line']}: {item_m['text']}"for item_m in self .render_lines (origin_m .key ,selected_indices_m )
                )
            elif origin_m .key in self .focused_lines :
                selected_indices_m =self .source_evidence_indices (
                origin_m .key ,
                self .focused_lines [origin_m .key ],
                )
                mark_indices =selected_indices_m 
                quotation ="\n".join (item_m ["text"]for item_m in self .render_lines (origin_m .key ,selected_indices_m ))
            elif not allow_preview :
                continue 
            else :
                quotation ,slices =self .packet_preview (origin_m .key )
                self .source_slices [ref ]=slices 
                selected_indices_m =None 
                mark_indices =None 
            if include_structured_csv and selected_indices_m is not None :
                self .source_slices [ref ]=self .citation_cuts (
                origin_m .key ,
                mark_indices or selected_indices_m ,
                )
            item_m :dict [str ,Any ]={
            "source_ref":f"[{ref}]",
            "title":origin_m .title ,
            "url":origin_m .url ,
            "quote":quotation ,
            }
            if selected_indices_m is not None :
                csv_records_m =self .structured_csv_records (origin_m .key ,selected_indices_m )
                if csv_records_m :
                    item_m ["csv_records"]=csv_records_m 
            manifest .append (item_m )
        return manifest 

    def citation_plan (
    self ,
    reply :str ,
    fallback_manifest :list [dict [str ,Any ]],
    final_origin_cuts :dict [str ,list [CitationSlice ]],
    audit_m :str ,
    )->MeridianChart :
        survey_badges =list (dict .fromkeys (re .findall (r"\b(S\d+(?:\.\d+)?|P\d+)\b",audit_m )))
        ruling_badges =list (dict .fromkeys (re .findall (r"\b(S\d+(?:\.\d+)?|P\d+)\b",reply )))
        mentioned_badges =list (dict .fromkeys ([*ruling_badges ,*survey_badges ]))
        badges :list [str ]=[]
        for ref in mentioned_badges :
            if re .fullmatch (r"S\d+",ref ):
                badges .extend (candidate_m for candidate_m in self .sources if candidate_m .startswith (f"{ref}."))
            else :
                badges .append (ref )
        if not badges :
            badges =[item_m ["source_ref"][1 :-1 ]for item_m in fallback_manifest ]
        mark_origins :dict [tuple [str ,str ],MeridianBeacon ]={}
        citation_cuts :dict [tuple [str ,str ],list [CitationSlice ]]={}
        origin_identities_m :dict [str ,tuple [str ,str ]]={}
        for ref in badges :
            origin_m =self .sources .get (ref )
            if origin_m and origin_m .receipt_id and origin_m .result_id :
                handle =(origin_m .receipt_id ,origin_m .result_id )
                origin_identities_m [ref ]=handle 
                slices =_weld_mark_reaches (
                [],
                final_origin_cuts .get (ref ,self .source_slices .get (ref ,[])),
                )
                mark_origins [handle ]=origin_m 
                citation_cuts [handle ]=_weld_mark_reaches (
                citation_cuts .get (handle ,[]),
                slices ,
                )
        handle_indices ={
        handle :index_m 
        for index_m ,handle in enumerate (mark_origins ,start =1 )
        }
        citations =[
        CitationRef (
        receipt_id =origin_m .receipt_id ,
        result_id =origin_m .result_id ,
        slices =citation_cuts [handle ],
        )
        for handle ,origin_m in mark_origins .items ()
        ]
        return MeridianChart (
        citations =citations ,
        source_indices ={
        ref :handle_indices [handle ]
        for ref ,handle in origin_identities_m .items ()
        if handle in handle_indices 
        },
        )


# ============ RENDERING & DETERMINATION LATTICE ============


def _unravel_csv_rung (rung_x :str )->list [str ]|None :
    fields_m :list [str ]=[]
    field_m :list [str ]=[]
    in_quotations =False 
    after_quotation =False 
    index_m =0 
    while index_m <len (rung_x ):
        character_m =rung_x [index_m ]
        if in_quotations :
            if character_m !='"':
                field_m .append (character_m )
            elif index_m +1 <len (rung_x )and rung_x [index_m +1 ]=='"':
                field_m .append ('"')
                index_m +=1 
            else :
                in_quotations =False 
                after_quotation =True 
        elif after_quotation :
            if character_m ==",":
                fields_m .append ("".join (field_m ))
                field_m =[]
                after_quotation =False 
            elif character_m not in " \t":
                return None 
        elif character_m ==",":
            fields_m .append ("".join (field_m ))
            field_m =[]
        elif character_m =='"'and not field_m :
            in_quotations =True 
        else :
            field_m .append (character_m )
        index_m +=1 
    if in_quotations :
        return None 
    fields_m .append ("".join (field_m ))
    return fields_m 


def _vocable_pouch (text :str )->set [str ]:
    return {
    piece_m 
    for piece_m in re .findall (r"[a-z0-9]+",(text or "").lower ())
    if piece_m not in _LATTICE_STOPWORDS and len (piece_m )>1 
    }


def _lattice_rung_glean2 (line_m :str )->tuple [str ,str ,bool ]|None :
    """One (candidate, condition, met) triple from a grid row, or None.

    None means the row cannot be read with certainty. Unreadable rows make the
    table ragged, and `_grid_trustworthy` refuses a ragged table outright — so
    a table the parser cannot read behaves exactly like no table at all."""
    raw_m =(line_m or "").strip ()
    if raw_m .count ("|")<2 or _LATTICE_CANON2_RUNG_RE .match (raw_m ):
        return None 
    cells_m =[cell_m .strip ().strip ("*_`").strip ()for cell_m in raw_m .strip ("|").split ("|")]
    if len (cells_m )<3 :
        return None 
    who_m =cells_m [0 ].strip (" \t.:-*•").strip ()
    cond_m =cells_m [1 ].strip (" \t.:-").strip ()
    decree =_HIDDEN2_BADGE_RE .sub ("",cells_m [-1 ]).strip ()
    if not who_m or not cond_m or len (who_m )>LATTICE_LABEL_MAX or len (cond_m )>LATTICE_LABEL_MAX :
        return None 
    if who_m .lower ()in _LATTICE_BARRED_LABELS or cond_m .lower ()in _LATTICE_BARRED_LABELS :
        return None 
    if len (decree )>LATTICE_RULING_CELL_MAX :
        return None 
    if _CLEARS2_VOCABLE_RE .search (decree )and _LAPSES_VOCABLE_RE .search (decree ):
        return None # a cell naming both outcomes decides nothing
    if _CLEARS2_LEAD_RE .match (decree ):
        return who_m ,cond_m ,True 
    if _LAPSES_LEAD_RE .match (decree ):
        return who_m ,cond_m ,False 
    return None 


def _lattice_trawl (reply :str )->tuple [set [int ],list [tuple [str ,str ,bool ]]]:
    """(line indices the grid occupies, its readable rows).

    The index set exists so no other body parser ever counts a grid line twice."""
    lines_m =(reply or "").splitlines ()
    claimed_m :set [int ]=set ()
    rungs :list [tuple [str ,str ,bool ]]=[]
    i_m =0 
    while i_m <len (lines_m ):
        titlecard =lines_m [i_m ].strip ()
        if not titlecard or "|"in titlecard or len (titlecard )>80 or not _LATTICE_TITLECARD_RE .search (titlecard ):
            i_m +=1 
            continue 
        local_m :set [int ]=set ()
        found_m :list [tuple [str ,str ,bool ]]=[]
        runway =0 
        j_m =i_m +1 
        while j_m <len (lines_m ):
            rung_line =lines_m [j_m ]
            if not rung_line .strip ():
                if found_m :
                    break # blank line closes the table
                runway +=1 
                if runway >LATTICE_RUNWAY_RUNGS :
                    break 
                j_m +=1 
                continue 
            triple_m =_lattice_rung_glean2 (rung_line )
            if triple_m is not None :
                found_m .append (triple_m )
                local_m .add (j_m )
                j_m +=1 
                continue 
            if _LATTICE_CANON2_RUNG_RE .match (rung_line .strip ())or (
            not found_m and runway <LATTICE_RUNWAY_RUNGS and rung_line .count ("|")>=2 
            ):
                local_m .add (j_m )# header row / rule line ahead of the data rows
                runway +=1 
                j_m +=1 
                continue 
            break 
        if found_m :
            rungs .extend (found_m )
            claimed_m .update (local_m )
            claimed_m .add (i_m )
        i_m =max (j_m ,i_m +1 )
    return claimed_m ,rungs 


def _lattice_collate (reply :str )->dict [str ,dict [str ,bool ]]:
    """{candidate: {condition: met}} folded from the readable grid rows.

    Candidates merge case-insensitively but keep their first spelling; a
    candidate marked MISS anywhere on a condition misses it — the strictest
    reading is the only safe one."""
    _claimed_m ,rungs =_lattice_trawl (reply )
    table_m :dict [str ,dict [str ,bool ]]={}
    spellings_m :dict [str ,str ]={}
    for who_m ,cond_m ,met_m in rungs :
        name_m =spellings_m .setdefault (who_m .lower (),who_m )
        folded_m =table_m .setdefault (name_m ,{})
        cond_key_m =cond_m .lower ()
        folded_m [cond_key_m ]=folded_m .get (cond_key_m ,True )and met_m 
    return table_m 


def _lattice_creditable (table_m :dict [str ,dict [str ,bool ]])->bool :
    """A grid is computable only when it describes a real screen: at least two
    candidates, each judged against the identical condition set. A ragged grid
    means rows were dropped or never written; computing from it would invent a
    result nothing supports."""
    if len (table_m )<2 :
        return False 
    cond_sets_m =[frozenset (folded_m )for folded_m in table_m .values ()]
    if not cond_sets_m or not cond_sets_m [0 ]:
        return False 
    return len (set (cond_sets_m ))==1 


def _lattice_keepers (table_m :dict [str ,dict [str ,bool ]])->list [str ]:
    """Set logic, not generation: the candidates meeting every condition."""
    return sorted (who_m for who_m ,folded_m in table_m .items ()if folded_m and all (folded_m .values ()))


def _pen_masthead (keepers :list [str ])->str :
    if not keepers :
        return ""
    if len (keepers )==1 :
        return f"FINAL ANSWER: {keepers[0]}"
    return "FINAL ANSWER: "+", ".join (keepers [:-1 ])+" and "+keepers [-1 ]


def _masthead_index (reply :str )->int :
    for i_m ,rung in enumerate ((reply or "").splitlines ()):
        if _MASTHEAD_MARK_RE .match (rung .strip ()):
            return i_m 
    return -1 


def _enact_lattice_decree (reply :str )->str :
    """Overwrite the locked headline with the determination computed from the
    grid — but only past every guard below. Each early return exists because
    the rewrite could otherwise damage a correct answer; when any guard holds,
    the answer comes back byte for byte unchanged."""
    at_m =_masthead_index (reply )
    if at_m <0 :
        return reply # nothing locked to rewrite
    table_m =_lattice_collate (reply )
    if not _lattice_creditable (table_m ):
        return reply # absent, single-candidate, or ragged grid
    keepers =_lattice_keepers (table_m )
    if not keepers or len (keepers )>LATTICE_KEEPER_MAX :
        return reply # an empty or unbounded set is not a determination
    lines_m =(reply or "").splitlines ()
    old_masthead =_MASTHEAD_MARK_RE .sub ("",lines_m [at_m ].strip ()).strip ()
    masthead_pouch =_vocable_pouch (_HIDDEN2_BADGE_RE .sub ("",old_masthead ))
    keeper_bags =[_vocable_pouch (who_m )for who_m in keepers ]
    keeper_union :set [str ]=set ()
    for pouch in keeper_bags :
        keeper_union |=pouch 
        # Agreement test: the headline must name every survivor AND no distinct
        # loser. Sibling names share words, so a loser counts as named only via a
        # token that separates it from every survivor.
    covers_m =all (pouch and pouch .issubset (masthead_pouch )for pouch in keeper_bags )
    loser_named_m =False 
    for who_m in table_m :
        if who_m in keepers :
            continue 
        pouch =_vocable_pouch (who_m )
        if pouch and pouch .issubset (masthead_pouch )and (pouch -keeper_union ):
            loser_named_m =True 
            break 
    if covers_m and not loser_named_m :
        return reply # the writer already agreed; leave it alone
    demurring =bool (_NEG2_MASTHEAD_RE .search (old_masthead )or _WAIVER2_MASTHEAD_RE .search (old_masthead ))
    if _TOPPICK_RE_M .search (reply or "")and not demurring :
    # A ranked top-N answer legitimately names fewer candidates than the
    # grid marks as meeting the screen; the all-meets set is NOT the answer.
        return reply 
    if len (keepers )>=len (table_m )and not demurring :
        return reply # a grid excluding nothing has no discriminating power
    if not demurring and not any (_vocable_pouch (who_m )&masthead_pouch for who_m in table_m ):
    # The headline answers with a value or date; the grid is supporting
    # work, not the asked-for output. It stays advisory.
        return reply 
    fresh_m =_pen_masthead (keepers )
    if not fresh_m or len (fresh_m )>LATTICE_MASTHEAD_CHAR_MAX :
        return reply 
    kept_badges ="".join (m_m .group (0 )for m_m in _HIDDEN2_BADGE_RE .finditer (lines_m [at_m ]))
    lines_m [at_m ]=fresh_m +kept_badges 
    return "\n".join (lines_m )


def _shuck_lead_preamble2 (reply :str )->str :
    """Drop first-person planning prose ahead of the locked headline. Only rows
    that read as narration and carry no source tag are removed, and only when a
    locked headline actually follows within the opening rows."""
    lines_m =(reply or "").splitlines ()
    at_m =_masthead_index (reply )
    if at_m <=0 or at_m >8 :
        return reply 
    head_m =lines_m [:at_m ]
    if all (
    not rung .strip ()or (_LEAD_PREAMBLE2_RE .match (rung )and not _HIDDEN2_BADGE_RE .search (rung ))
    for rung in head_m 
    ):
        return "\n".join (lines_m [at_m :])
    return reply 


def _burnish_notarized_prose2 (reply :str )->str :
    """Deterministic post-seal passes. A post-commit pass must never be able to
    lose an answer already held, so every step is exception-safe."""
    text =reply 
    try :
        text =_shuck_lead_preamble2 (text )
        text =_enact_lattice_decree (text )
    except Exception :
        return reply 
    return text or reply 


def _inward_origin_badges (reply :str )->list [str ]:
    return list (dict .fromkeys (re .findall (r"\[(S\d+(?:\.\d+)?|P\d+)\]",reply )))


def _canon_sheafed_inward_badges (reply :str )->str :
    ref =r"(?:S\d+(?:\.\d+)?|P\d+)"
    sheafed =re .compile (rf"\[({ref}(?:\s*,\s*{ref})+)\]")
    return sheafed .sub (
    lambda match_m :"".join (
    f"[{item_m}]"
    for item_m in re .findall (ref ,match_m .group (1 ))
    ),
    reply ,
    )


def _wants2_naked_form (inquiry :str )->bool :
    return bool (
    re .search (
    r"(?i)\b(?:output|return|respond)\s+only\b",
    inquiry ,
    )
    )


def _verify2_inward_ruling_badges (
reply :str ,
allowed_badges :set [str ],
*,
require_ref_m :bool =True ,
)->None :
    if "[["in reply or "]]"in reply :
        raise ValueError ("write private source refs such as [P1], not public numeric markers")
    if re .search (
    r"(?i)(?:https?://|\bwww\.|(?<!:)//(?=[a-z0-9])|"
    r"(?<![\w@])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,63}/[^\s)]*)",
    reply ,
    ):
        raise ValueError ("do not render raw URLs in the reader-facing answer")
    if re .search (
    r"(?im)^\s{0,3}(?:#{1,6}\s*)?(?:sources?|citations?|references?|bibliography|works\s+cited)\s*:?\s*$",
    reply ,
    ):
        raise ValueError ("do not render a citation or source-list section")

    verbatim_badge_sieve =re .compile (r"\[(?:S\d+(?:\.\d+)?|P\d+)\]")
    without_verbatim_badges =verbatim_badge_sieve .sub ("",reply )
    if "["in without_verbatim_badges or "]"in without_verbatim_badges :
        raise ValueError (
        "square brackets are reserved for one exact private source ref such as [P1]"
        )
    if re .search (r"\b(?:S\d+(?:\.\d+)?|P\d+)\b",without_verbatim_badges ):
        raise ValueError (
        "each private source ref must appear alone in brackets, for example [P1]"
        )
    badges =_inward_origin_badges (reply )
    unclear_badges =[ref for ref in badges if ref not in allowed_badges ]
    if unclear_badges :
        raise ValueError (f"answer cites unavailable source refs: {', '.join(unclear_badges)}")
    if require_ref_m and allowed_badges and not badges :
        raise ValueError ("answer must place at least one supplied source ref after a supported factual claim")


def _issue_public_marks (
reply :str ,
chart :MeridianChart ,
*,
unadorned_output_m :bool =False ,
helm :MeridianHelm |None =None ,
)->tuple [str ,list [CitationRef ]]:
    badges =_inward_origin_badges (reply )
    missing_badges =[ref for ref in badges if ref not in chart .source_indices ]
    if missing_badges :
        raise ValueError (
        "answer source refs do not have materializable citations: "
        +", ".join (missing_badges )
        )
    rendered_m =re .sub (
    r"\[(S\d+(?:\.\d+)?|P\d+)\]",
    lambda match_m :f"[[{chart.source_indices[match_m.group(1)]}]]",
    reply ,
    )
    marker_indices_m =[
    int (value_m )
    for value_m in re .findall (r"\[\[(\d+)]]",rendered_m )
    ]
    invalid_indices_m =sorted (
    {
    index_m 
    for index_m in marker_indices_m 
    if index_m <1 or index_m >len (chart .citations )
    }
    )
    if invalid_indices_m :
        raise ValueError (
        "answer contains citation indices without response citations: "
        +", ".join (str (index_m )for index_m in invalid_indices_m )
        )
    if chart .citations and not marker_indices_m and not unadorned_output_m :
        raise ValueError ("answer has response citations but no inline citation markers")

    used_indices_m =(
    sorted (set (marker_indices_m ))
    if marker_indices_m 
    else list (range (1 ,len (chart .citations )+1 ))
    )
    prune_indices ={
    old_index_m :new_index_m 
    for new_index_m ,old_index_m in enumerate (used_indices_m ,start =1 )
    }
    rendered_m =re .sub (
    r"\[\[(\d+)]]",
    lambda match_m :f"[[{prune_indices[int(match_m.group(1))]}]]",
    rendered_m ,
    )
    if unadorned_output_m :
        rendered_m =re .sub (r"[ \t]*\[\[\d+]]","",rendered_m )
    citations =[chart .citations [index_m -1 ]for index_m in used_indices_m ]
    return (rendered_m .strip (),citations )


def _weld_mark_reaches (
existing_m :list [CitationSlice ],
additional_m :list [CitationSlice ],
)->list [CitationSlice ]:
    reaches =sorted (
    (int (item_m .start ),int (item_m .end ))for item_m in [*existing_m ,*additional_m ]if int (item_m .end )>int (item_m .start )
    )
    merged_m :list [tuple [int ,int ]]=[]
    for start ,end in reaches :
        if merged_m and start <=merged_m [-1 ][1 ]:
            merged_m [-1 ]=(merged_m [-1 ][0 ],max (merged_m [-1 ][1 ],end ))
        else :
            merged_m .append ((start ,end ))
    return [CitationSlice (start =start ,end =end )for start ,end in merged_m ]


def _glean_origin_badges (value_m :Any )->list [str ]:
    badges :list [str ]=[]
    if isinstance (value_m ,dict ):
        for field_m ,item_m in value_m .items ():
            if field_m =="source_ref"and isinstance (item_m ,str ):
                badges .append (item_m .strip ().strip ("[]"))
            else :
                badges .extend (_glean_origin_badges (item_m ))
    elif isinstance (value_m ,list ):
        for item_m in value_m :
            badges .extend (_glean_origin_badges (item_m ))
    return list (dict .fromkeys (badges ))


def _markdown2_lattice_reach (
helm :MeridianHelm ,
key :str ,
match_index_m :int ,
)->dict [str ,Any ]|None :
    rungs =helm .vfs [key ].splitlines ()or [""]
    separator_index_m :int |None =None 
    for index_m in range (match_index_m ,0 ,-1 ):
        if re .fullmatch (r"\s*\|(?:\s*:?-+:?\s*\|)+\s*",rungs [index_m ]):
            separator_index_m =index_m 
            break 
        if index_m <match_index_m and rungs [index_m ].lstrip ().startswith ("#"):
            break 
    if separator_index_m is None :
        return None 

    header_index_m =separator_index_m -1 
    end_index_m =separator_index_m 
    for index_m in range (separator_index_m +1 ,len (rungs )):
        if not rungs [index_m ].lstrip ().startswith ("|"):
            break 
        end_index_m =index_m 
    return {
    "start_line":header_index_m +1 ,
    "end_line":end_index_m +1 ,
    "header":helm .render_lines (key ,range (header_index_m ,separator_index_m +1 )),
    }


# ============ PILOT PLUMBING ============


def _jot_outlay (helm :MeridianHelm ,sighting :Any )->None :
    outlay =getattr (sighting ,"budget",None )
    if outlay is None :
        return 
    helm .budget_snapshot ={
    "session_hard_limit_usd":round (float (outlay .session_hard_limit_usd ),6 ),
    "session_used_budget_usd":round (float (outlay .session_used_budget_usd ),6 ),
    "session_hard_remaining_usd":round (
    max (
    0.0 ,
    float (outlay .session_hard_limit_usd )-float (outlay .session_used_budget_usd ),
    ),
    6 ,
    ),
    }


def _is_fleeting_llm_mishap (mishap :Exception )->bool :
    notem =str (mishap ).lower ()
    return any (
    marker_m in notem 
    for marker_m in (
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


async def _move_pilot (
pilot_label :str ,
messages :list [Any ],
tools :list [dict [str ,Any ]]|None ,
tool_choice :str ,
parallel_tool_calls :bool ,
timeout :float ,
max_output_tokens :int |None =None ,
)->Any :
    if pilot_label =="glm5":
        return await llm_chat (
        provider ="openrouter",
        model ="z-ai/glm-5",
        messages =messages ,
        temperature =0.2 ,
        max_output_tokens =max_output_tokens or MERIDIAN_GLM5_TOP_FORM_SHARDS ,
        tools =tools ,
        tool_choice =tool_choice ,
        parallel_tool_calls =parallel_tool_calls ,
        thinking ={"enabled":True ,"effort":"low"},
        provider_extra =OPENROUTER_GLM_CARRIER_LEANINGS ,
        timeout =timeout ,
        )
    if pilot_label =="gpt_oss":
        return await llm_chat (
        provider ="openrouter",
        model ="openai/gpt-oss-120b",
        messages =messages ,
        temperature =0.0 ,
        max_output_tokens =max_output_tokens or MERIDIAN_GPTOSS_TOP_FORM_SHARDS ,
        tools =tools ,
        tool_choice =tool_choice ,
        parallel_tool_calls =parallel_tool_calls ,
        thinking ={"enabled":True ,"effort":"high"},
        provider_extra =OPENROUTER_GPT_CARRIER_LEANINGS ,
        timeout =timeout ,
        )
    if pilot_label =="openrouter_gemma":
        return await llm_chat (
        provider ="openrouter",
        model ="google/gemma-4-31b-it",
        messages =messages ,
        temperature =1.0 ,
        max_output_tokens =max_output_tokens or MERIDIAN_OR_GEMMA_TOP_FORM_SHARDS ,
        tools =tools ,
        tool_choice =tool_choice ,
        parallel_tool_calls =parallel_tool_calls ,
        thinking ={"enabled":True ,"effort":"medium"},
        provider_extra =MERIDIAN_OR_GEMMA_CARRIER_LEANINGS ,
        timeout =timeout ,
        )
    if pilot_label =="openrouter_gemma_prose":
        return await llm_chat (
        provider ="openrouter",
        model ="google/gemma-4-31b-it",
        messages =messages ,
        temperature =1.0 ,
        max_output_tokens =max_output_tokens or MERIDIAN_OR_GEMMA_TOP_FORM_SHARDS ,
        tools =tools ,
        tool_choice =tool_choice ,
        parallel_tool_calls =parallel_tool_calls ,
        thinking ={"enabled":True ,"effort":"medium"},
        provider_extra =MERIDIAN_OR_GEMMA_CARRIER_LEANINGS ,
        timeout =timeout ,
        )
    if pilot_label =="openrouter_gemma_stable":
        return await llm_chat (
        provider ="openrouter",
        model ="google/gemma-4-31b-it",
        messages =messages ,
        temperature =1.0 ,
        max_output_tokens =max_output_tokens or MERIDIAN_OR_GEMMA_TOP_FORM_SHARDS ,
        tools =tools ,
        tool_choice =tool_choice ,
        parallel_tool_calls =parallel_tool_calls ,
        thinking ={"enabled":True ,"effort":"medium"},
        provider_extra =MERIDIAN_OR_GEMMA_STABLE_CARRIER_LEANINGS ,
        timeout =timeout ,
        )
    if pilot_label =="inkling":
        return await llm_chat (
        provider ="ai_gateway",
        model ="thinkingmachines/inkling",
        messages =messages ,
        temperature =1.0 ,
        max_output_tokens =max_output_tokens or MERIDIAN_INKLING_TOP_FORM_SHARDS ,
        tools =tools ,
        tool_choice =tool_choice ,
        parallel_tool_calls =parallel_tool_calls ,
        thinking ={"enabled":True ,"effort":"medium"},
        timeout =timeout ,
        )
    if pilot_label =="ai_gateway_gemma":
        return await llm_chat (
        provider ="ai_gateway",
        model ="google/gemma-4-31b-it",
        messages =messages ,
        temperature =1.0 ,
        max_output_tokens =max_output_tokens or MERIDIAN_AG_GEMMA_TOP_FORM_SHARDS ,
        tools =tools ,
        tool_choice =tool_choice ,
        parallel_tool_calls =parallel_tool_calls ,
        thinking ={"enabled":True ,"effort":"medium"},
        provider_extra ={
        "providerOptions":{
        "gateway":{
        "only":["cerebras"],
        }
        }
        },
        timeout =timeout ,
        )
    raise ValueError (f"unknown model: {pilot_label}")


async def _parley_with_pilot_chain (
pilots :tuple [str ,...],
messages :list [Any ],
tools :list [dict [str ,Any ]]|None ,
tool_choice :str ,
parallel_tool_calls :bool ,
timeout :float ,
max_output_tokens :int |None =None ,
)->Any :
    if not pilots :
        raise RuntimeError ("no research model was configured")

    raced_pilots =pilots [:2 ]
    residual_pilots =pilots [2 :]
    tasks_m =[
    asyncio .create_task (
    _move_pilot (
    model ,
    messages ,
    tools ,
    tool_choice ,
    parallel_tool_calls ,
    timeout ,
    max_output_tokens ,
    )
    )
    for model in raced_pilots 
    ]
    errors_m :list [Exception ]=[]
    queued_m =set (tasks_m )
    try :
        while queued_m :
            done_m ,queued_m =await asyncio .wait (
            queued_m ,
            return_when =asyncio .FIRST_COMPLETED ,
            )
            for task_m in done_m :
                try :
                    sighting =task_m .result ()
                except Exception as mishap :
                    errors_m .append (mishap )
                    continue 
                for unfinished_m in queued_m :
                    unfinished_m .cancel ()
                await asyncio .gather (*queued_m ,return_exceptions =True )
                return sighting 
    finally :
        for unfinished_m in queued_m :
            unfinished_m .cancel ()
        if queued_m :
            await asyncio .gather (*queued_m ,return_exceptions =True )

    non_fleeting =next (
    (mishap for mishap in errors_m if not _is_fleeting_llm_mishap (mishap )),
    None ,
    )
    if non_fleeting is not None :
        raise non_fleeting 

    for model in residual_pilots :
        try :
            return await _move_pilot (
            model ,
            messages ,
            tools ,
            tool_choice ,
            parallel_tool_calls ,
            timeout ,
            max_output_tokens ,
            )
        except Exception as mishap :
            if not _is_fleeting_llm_mishap (mishap ):
                raise 
            errors_m .append (mishap )

    if not errors_m :
        raise RuntimeError ("no research model was configured")
    raise errors_m [-1 ]


async def _parley_with_single2_pilot_chain (
pilots :tuple [str ,...],
messages :list [Any ],
tools :list [dict [str ,Any ]]|None ,
tool_choice :str ,
parallel_tool_calls :bool ,
timeout :float ,
max_output_tokens :int |None =None ,
)->Any :
    if not pilots :
        raise RuntimeError ("no research model was configured")

    errors_m :list [Exception ]=[]
    for model in pilots :
        try :
            return await _move_pilot (
            model ,
            messages ,
            tools ,
            tool_choice ,
            parallel_tool_calls ,
            timeout ,
            max_output_tokens ,
            )
        except Exception as mishap :
            if not _is_fleeting_llm_mishap (mishap ):
                raise 
            errors_m .append (mishap )

    raise errors_m [-1 ]


async def _parley_with_routing (
pilots :tuple [str ,...],
messages :list [Any ],
tools :list [dict [str ,Any ]]|None ,
tool_choice :str ,
parallel_tool_calls :bool ,
timeout :float ,
max_output_tokens :int |None =None ,
)->Any :
    if MERIDIAN_PILOT_ROTA =="race":
        return await _parley_with_pilot_chain (
        pilots ,
        messages ,
        tools ,
        tool_choice ,
        parallel_tool_calls ,
        timeout ,
        max_output_tokens ,
        )
    if MERIDIAN_PILOT_ROTA in {"sequential","state_aware"}:
        return await _parley_with_single2_pilot_chain (
        pilots ,
        messages ,
        tools ,
        tool_choice ,
        parallel_tool_calls ,
        timeout ,
        max_output_tokens ,
        )
    raise ValueError (f"unknown model scheduling policy: {MERIDIAN_PILOT_ROTA}")


async def _prose2_parley_with_retry (
messages :list [Any ],
tool_choice :str ,
timeout :float ,
)->Any :
    return await _parley_with_routing (
    ("glm5","openrouter_gemma","gpt_oss"),
    messages ,
    None ,
    tool_choice ,
    False ,
    timeout ,
    )


async def _final2_ruling_parley_with_retry (
messages :list [Any ],
timeout :float ,
)->Any :
    return await _parley_with_routing (
    ("ai_gateway_gemma","openrouter_gemma_prose","openrouter_gemma_stable","glm5"),
    messages ,
    None ,
    "none",
    False ,
    timeout ,
    )


def _passage_pilots (
helm :MeridianHelm ,
horizon_alert_raised :bool ,
swerve_spur :str ,
)->tuple [str ,...]:
    if MERIDIAN_PILOT_ROTA !="state_aware":
        return MERIDIAN_AMEND_PILOTS if helm .audit_gap else MERIDIAN_SOUNDING_PILOTS 
    if helm .audit_gap or horizon_alert_raised or swerve_spur :
        return MERIDIAN_AMEND_PILOTS 
    return BOARD_AWARE_MERIDIAN_SOUNDING_PILOTS 


def _mandates_pilots (
horizon_alert_raised :bool ,
swerve_spur :str ,
)->tuple [str ,...]:
    if MERIDIAN_PILOT_ROTA =="state_aware"and (horizon_alert_raised or swerve_spur ):
        return MERIDIAN_AMEND_PILOTS 
    return MERIDIAN_WANT_PILOTS 


# ============ RULING & SURVEY PROSE ============


async def _inquiry2_wording (charter :str ,user_m :str )->str :
    messages =[
    {"role":"system","content":charter },
    {"role":"user","content":user_m },
    ]
    sighting =await _prose2_parley_with_retry (messages ,"none",PILOT_GAUGE )
    text =sighting .llm .raw_text 
    if not text or not text .strip ():
        raise RuntimeError ("research model returned empty prose")
    return text .strip ()


async def _ruling_wording (
*,
helm :MeridianHelm ,
inquiry :str ,
prior_reply :str ,
stipulations :str ,
inquiry2_helm :str ,
finalization_ground :str ,
manifest :list [dict [str ,Any ]],
)->str :
    allowed_badges ={
    str (item_m ["source_ref"]).strip ("[]")
    for item_m in manifest 
    if isinstance (item_m ,dict )and item_m .get ("source_ref")
    }
    messages :list [Any ]=[
    {"role":"system","content":RULING_RECAST_CHARTER },
    {
    "role":"user",
    "content":(
    f"Original question:\n{inquiry}\n\n"
    f"Prior answer hypothesis:\n{prior_reply}\n\n"
    f"Evidence requirements:\n{stipulations}\n\n"
    f"Investigator's current research state:\n"
    f"{inquiry2_helm or '(not updated)'}\n\n"
    f"Finalization reason:\n{finalization_ground}\n\n"
    f"Supplied source records:\n"
    f"{json.dumps(manifest, ensure_ascii=False, indent=2)}"
    ),
    },
    ]
    for attempt_m in range (3 ):
        sighting =await _final2_ruling_parley_with_retry (messages ,PILOT_GAUGE )
        _jot_outlay (helm ,sighting )
        text =sighting .llm .raw_text 
        if not text or not text .strip ():
            raise RuntimeError ("answer writer returned empty prose")
        text =_canon_sheafed_inward_badges (text .strip ())
        try :
            _verify2_inward_ruling_badges (
            text ,
            allowed_badges ,
            require_ref_m =not _wants2_naked_form (inquiry ),
            )
        except ValueError as mishap :
            if attempt_m ==2 :
                raise 
            messages .extend (
            [
            {"role":"assistant","content":text },
            {
            "role":"user",
            "content":(
            f"Output contract error: {mishap}. Rewrite the complete answer. "
            "Use only the exact private source refs present in the supplied "
            "records; the harness renders public citation numbers."
            ),
            },
            ]
            )
            continue 
        return text 
    raise AssertionError ("unreachable")


def _formed_form_move (
output_schema_m :dict [str ,Any ],
)->tuple [dict [str ,Any ],bool ]:
    direct_object_m =output_schema_m .get ("type")=="object"
    parameters_m =(
    output_schema_m 
    if direct_object_m 
    else {
    "type":"object",
    "properties":{
    "output":{
    "description":(
    "The non-null JSON value that matches the caller's supplied output schema."
    )
    }
    },
    "required":["output"],
    "additionalProperties":False ,
    }
    )
    return (
    {
    "type":"function",
    "function":{
    "name":"submit_structured_output",
    "description":(
    "Submit the complete final value required by the caller's JSON Schema."
    ),
    "parameters":parameters_m ,
    "strict":False ,
    },
    },
    direct_object_m ,
    )


async def _mint_formed_form (
*,
inquiry :str ,
reply :str ,
output_schema_m :dict [str ,Any ],
)->Any :
    move_x ,direct_object_m =_formed_form_move (output_schema_m )
    warrant_backed_ruling =re .sub (r"\[\[\d+]]","",reply ).strip ()
    messages :list [Any ]=[
    {"role":"system","content":FORMED_FORM_CHARTER },
    {
    "role":"user",
    "content":(
    f"Original question:\n{inquiry}\n\n"
    f"Completed evidence-backed answer:\n{warrant_backed_ruling}\n\n"
    "Required JSON Schema:\n"
    f"{json.dumps(output_schema_m, ensure_ascii=False, indent=2)}"
    ),
    },
    ]
    for attempt_m in range (3 ):
        sighting =await _parley_with_routing (
        MERIDIAN_SOUNDING_PILOTS ,
        messages ,
        [move_x ],
        "required",
        False ,
        PILOT_GAUGE ,
        )
        envoy =_envoy_note (sighting )
        moves =list (envoy .tool_calls or ())
        mishap :ValueError |None =None 
        output :Any =None 
        if len (moves )!=1 :
            mishap =ValueError (
            "call submit_structured_output exactly once; "
            f"received {len(moves)} tool calls"
            )
        else :
            move =moves [0 ]
            try :
                if move .name !="submit_structured_output":
                    raise ValueError (
                    f"unexpected tool {move.name}; call submit_structured_output"
                    )
                arguments_m =json .loads (move .arguments )
                if not isinstance (arguments_m ,dict ):
                    raise ValueError ("tool arguments must be a JSON object")
                if direct_object_m :
                    output =arguments_m 
                else :
                    if set (arguments_m )!={"output"}:
                        raise ValueError (
                        "non-object output must be submitted in the sole `output` argument"
                        )
                    output =arguments_m ["output"]
                if output is None :
                    raise ValueError ("top-level null is not a valid miner answer")
            except (KeyError ,TypeError ,ValueError ,json .JSONDecodeError )as caught :
                mishap =ValueError (str (caught ))
        if mishap is None :
            return output 
        if attempt_m ==2 :
            raise mishap 

        messages .append (envoy .to_input_message ())
        if moves :
            for move in moves :
                messages .append (
                {
                "role":"tool",
                "tool_call_id":move .id ,
                "content":json .dumps (
                {
                "ok":False ,
                "error_type":"tool_argument_validation",
                "details":str (mishap ),
                }
                ),
                }
                )
        else :
            messages .append (
            {
            "role":"user",
            "content":(
            f"Output contract error: {mishap}. Call the required tool with "
            "the complete schema-conforming value."
            ),
            }
            )
    raise AssertionError ("unreachable")


async def _outlook_ruling_wording (inquiry :str )->str :
    messages =[
    {"role":"system","content":OUTLOOK_RULING_CHARTER },
    {"role":"user","content":inquiry },
    ]
    try :
        sighting =await _move_pilot (
        "inkling",
        messages ,
        None ,
        "none",
        False ,
        PILOT_GAUGE ,
        )
    except Exception as mishap :
        if not _is_fleeting_llm_mishap (mishap ):
            raise 
        sighting =await _parley_with_routing (
        ("gpt_oss","openrouter_gemma"),
        messages ,
        None ,
        "none",
        False ,
        PILOT_GAUGE ,
        )
    text =sighting .llm .raw_text 
    if not text or not text .strip ():
        raise RuntimeError ("research model returned empty prose")
    return text .strip ()


def _unravel_survey (text :str )->tuple [str ,str ]:
    matches_m =list (
    re .finditer (
    r"(?m)^VERDICT (READY|CONTINUE|REVISE)(?::[ \t]*(.*))?[ \t]*$",
    text ,
    )
    )
    if len (matches_m )!=1 :
        raise ValueError ("audit must contain exactly one VERDICT line")
    match_m =matches_m [0 ]
    decree =match_m .group (1 )
    inline_m =(match_m .group (2 )or "").strip ()
    following_m =text [match_m .end ():].strip ()
    payload_m ="\n".join (part_m for part_m in (inline_m ,following_m )if part_m )
    if decree =="REVISE"and not payload_m :
        raise ValueError ("VERDICT REVISE must include a complete replacement answer")
    if decree =="CONTINUE"and not payload_m :
        raise ValueError ("VERDICT CONTINUE must name the missing observation")
    return decree ,payload_m 


async def _survey (
helm :MeridianHelm ,
inquiry :str ,
reply :str ,
manifest :list [dict [str ,Any ]],
)->str :
    allowed_badges ={
    str (item_m ["source_ref"]).strip ("[]")
    for item_m in manifest 
    if isinstance (item_m ,dict )and item_m .get ("source_ref")
    }
    origin_inventory_m =[
    {
    "source_ref":f"[{origin_m.ref}]",
    "title":origin_m .title ,
    "url":origin_m .url ,
    }
    for origin_m in helm .sources .values ()
    ]
    messages =[
    {"role":"system","content":SURVEY_CHARTER },
    {
    "role":"user",
    "content":(
    f"Original question:\n{inquiry}\n\n"
    "Observed source inventory (discovery metadata only; titles and URLs are "
    "not evidence):\n"
    f"{json.dumps(origin_inventory_m, ensure_ascii=False, indent=2)}\n\n"
    f"Supplied source records:\n"
    f"{json.dumps(manifest, ensure_ascii=False, indent=2)}\n\n"
    f"Current answer:\n{reply}"
    ),
    },
    ]
    for attempt_m in range (3 ):
        sighting =await _parley_with_single2_pilot_chain (
        MERIDIAN_SURVEY_PILOTS ,
        messages ,
        None ,
        "none",
        False ,
        PILOT_GAUGE ,
        )
        _jot_outlay (helm ,sighting )
        text =sighting .llm .raw_text 
        if not text or not text .strip ():
            raise RuntimeError ("auditor returned empty output")
        text =text .strip ()
        try :
            decree ,payload_m =_unravel_survey (text )
            if decree in {"READY","REVISE"}and re .search (r"(?m)^MISSING:",text ):
                raise ValueError (
                f"VERDICT {decree} is invalid while a material premise is MISSING; "
                "a MISSING line must name a real unresolved premise and cannot say none or "
                "not applicable. If no premise is missing, preserve the verdict and omit all "
                "MISSING lines. Correct only this output-format error; do not introduce a new "
                "evidence requirement"
                )
            if decree =="REVISE":
                _verify2_inward_ruling_badges (
                payload_m ,
                allowed_badges ,
                require_ref_m =not _wants2_naked_form (inquiry ),
                )
        except ValueError as mishap :
            if attempt_m ==2 :
                raise 
            messages .extend (
            [
            {"role":"assistant","content":text },
            {
            "role":"user",
            "content":(
            f"Output contract error: {mishap}. Re-audit from the supplied records. "
            "Follow the required premise-line and final VERDICT format exactly; "
            "a replacement answer must use only exact supplied private source refs."
            ),
            },
            ]
            )
            continue 
        return text 
    raise AssertionError ("unreachable")


# ============ CABINET & FREIGHT BOOKKEEPING ============


def _envoy_note (sighting :Any )->Any :
    choices_m =sighting .llm .choices 
    if len (choices_m )!=1 :
        raise RuntimeError (f"expected one LLM choice, received {len(choices_m)}")
    return choices_m [0 ].message 


def _envoy_warrant_reach (notem :Any )->str :
    wording_parts =[
    str (part_m .text )
    for part_m in notem .content 
    if getattr (part_m ,"text",None )
    ]
    return "\n".join (
    item_m 
    for item_m in (str (notem .reasoning or "").strip (),*wording_parts )
    if item_m 
    )


def _glean_cabinet_slots (value_m :Any )->list [str ]:
    slots_m :list [str ]=[]
    if isinstance (value_m ,dict ):
        for field_m ,item_m in value_m .items ():
            if field_m in {"key","vfs_key"}and isinstance (item_m ,str ):
                slots_m .append (item_m )
            elif field_m in {"keys","matched_keys"}and isinstance (item_m ,list ):
                slots_m .extend (candidate_m for candidate_m in item_m if isinstance (candidate_m ,str ))
            else :
                slots_m .extend (_glean_cabinet_slots (item_m ))
    elif isinstance (value_m ,list ):
        for item_m in value_m :
            slots_m .extend (_glean_cabinet_slots (item_m ))
    return list (dict .fromkeys (slots_m ))


def _prune_drained_move_findings (messages :list [Any ])->None :
    for notem in messages :
        if not isinstance (notem ,dict )or notem .get ("role")!="tool":
            continue 
        content =notem .get ("content")
        if not isinstance (content ,str )or len (content )<1_000 :
            continue 
        try :
            output =json .loads (content )
        except json .JSONDecodeError :
            continue 
        if not isinstance (output ,dict ):
            continue 
        chit :dict [str ,Any ]={"ok":output .get ("ok",False )}
        slots_m =_glean_cabinet_slots (output )
        if slots_m :
            chit ["vfs_keys"]=slots_m 
        if output .get ("error_type"):
            chit ["error_type"]=output ["error_type"]
            chit ["details"]=str (output .get ("details",""))[:1_000 ]
        if output .get ("audit"):
            chit ["audit"]=output ["audit"]
        resonance =output .get ("similarity")
        if isinstance (resonance ,dict ):
            chit ["similarity"]={
            field_m :resonance [field_m ]
            for field_m in ("status","trigger","reason")
            if field_m in resonance 
            }
        notem ["content"]=json .dumps (chit ,ensure_ascii =False )


def _prune_drained_envoy_musing2 (messages :list [Any ])->None :
    for index_m ,notem in enumerate (messages ):
        if isinstance (notem ,LlmMessage ):
            if notem .role =="assistant"and notem .reasoning_details is not None :
                messages [index_m ]=replace (notem ,reasoning_details =None )
            continue 
        if not isinstance (notem ,dict )or notem .get ("role")!="assistant":
            continue 
        notem .pop ("reasoning",None )
        notem .pop ("reasoning_details",None )


def _chalk_freight_chit (
helm :MeridianHelm ,
label_m :str ,
args_m :dict [str ,Any ],
output :dict [str ,Any ],
)->None :
    if not output .get ("ok")or label_m not in {"search_web","fetch_page"}:
        return 
    if label_m =="search_web":
        destinations_m =[str (output ["vfs_key"])]
        origin_index_m =[
        {
        "source_ref":item_m ["source_ref"],
        "vfs_key":item_m ["vfs_key"],
        "title":item_m ["title"],
        "url":item_m ["url"],
        }
        for item_m in output .get ("results",[])
        if isinstance (item_m ,dict )
        ]
    else :
        destinations_m =[
        str (leaf ["vfs_key"])for leaf in output .get ("pages",[])if isinstance (leaf ,dict )and leaf .get ("vfs_key")
        ]
        origin_index_m =[
        {
        "source_ref":item_m ["source_ref"],
        "vfs_key":item_m ["vfs_key"],
        "title":item_m ["title"],
        "url":item_m ["url"],
        }
        for item_m in output .get ("pages",[])
        if isinstance (item_m ,dict )
        ]
    thumbmark =_freight_thumbmark (label_m ,args_m )
    helm .retrieval_output_cache [thumbmark ]=output 
    chit =helm .retrieval_receipts .setdefault (
    thumbmark ,
    {
    "tool":label_m ,
    "arguments":args_m ,
    "destinations":[],
    "sources":[],
    "calls":0 ,
    },
    )
    chit ["calls"]+=1 
    chit ["destinations"]=list (dict .fromkeys ([*chit ["destinations"],*destinations_m ]))
    known_origins_m ={str (item_m ["source_ref"]):item_m for item_m in [*chit ["sources"],*origin_index_m ]}
    chit ["sources"]=list (known_origins_m .values ())


def _freight_thumbmark (label_m :str ,args_m :dict [str ,Any ])->str :
    return json .dumps (
    {"tool":label_m ,"arguments":args_m },
    ensure_ascii =False ,
    sort_keys =True ,
    )


def _chalk_cabinet_step_chit (
helm :MeridianHelm ,
label_m :str ,
args_m :dict [str ,Any ],
output :dict [str ,Any ],
)->None :
    if not output .get ("ok")or label_m not in {"vfs_read","vfs_search","vfs_list"}:
        return 

    if label_m =="vfs_read":
        rungs =output .get ("lines",[])
        outcome_m ={
        "returned_line_count":len (rungs ),
        "first_line":rungs [0 ].get ("line")if rungs else None ,
        "last_line":rungs [-1 ].get ("line")if rungs else None ,
        "truncated":bool (output .get ("truncated")),
        }
    elif label_m =="vfs_search":
        sieve_x =output .get ("regex",{})
        resonance =output .get ("similarity",{})
        outcome_m ={
        "regex_total_match_count":sieve_x .get ("total_match_count"),
        "regex_returned_match_count":len (sieve_x .get ("matches",[])),
        "regex_next_cursor":sieve_x .get ("next_cursor"),
        "similarity_status":resonance .get ("status"),
        "similarity_returned_chunk_count":len (resonance .get ("chunks",[])),
        }
    else :
        outcome_m ={"returned_key_count":len (output .get ("keys",[]))}

    thumbmark =json .dumps (
    {"tool":label_m ,"arguments":args_m },
    ensure_ascii =False ,
    sort_keys =True ,
    )
    chit =helm .vfs_operation_receipts .setdefault (
    thumbmark ,
    {
    "tool":label_m ,
    "arguments":args_m ,
    "calls":0 ,
    "outcome":outcome_m ,
    },
    )
    chit ["calls"]+=1 
    chit ["outcome"]=outcome_m 


def _refresh2_freight_chit_note (
messages :list [Any ],
helm :MeridianHelm ,
)->None :
    marker_m ="Harness research memory"
    messages [:]=[
    notem 
    for notem in messages 
    if not (
    isinstance (notem ,dict )
    and notem .get ("role")=="user"
    and isinstance (notem .get ("content"),str )
    and notem ["content"].startswith (marker_m )
    )
    ]
    if (
    not helm .research_state 
    and not helm .audit_gap 
    and not helm .budget_snapshot 
    and not helm .retrieval_receipts 
    and not helm .vfs_operation_receipts 
    and not helm .claim_ledger .entries
    and not helm .focused_lines
    and not helm .reasoning_observations 
    ):
        return 
    sections_m :list [str ]=[]
    if helm .evidence_requirements :
        sections_m .append (
        "Evidence questions established before retrieval. They guide the investigation "
        "but may become immaterial after supported filtering:\n"+helm .evidence_requirements 
        )
    if helm .audit_gap :
        sections_m .append (
        "Latest finalization audit. This gap overrides any stale claim in the "
        "model-authored state that no uncertainty remains. Do not call "
        "ready_to_finalize again until new evidence resolves it:\n"+helm .audit_gap 
        )
    if helm .budget_snapshot :
        sections_m .append (
        "Latest hosted-tool budget snapshot. This is runtime state, not evidence:\n"
        +json .dumps (helm .budget_snapshot ,ensure_ascii =False ,indent =2 )
        +"\nFinish before the hard remaining amount reaches zero. After observing the "
        "single result that resolves an audit gap, combine any now-independent "
        "retain_evidence, update_research_state, and ready_to_finalize calls in the "
        "same response instead of spending separate turns on each."
        )
    if helm .research_state :
        sections_m .append (
        "Current model-authored research state. Revise it with update_research_state "
        "when the answer, support, or next unresolved question changes:\n"+helm .research_state 
        )
    if helm .reasoning_observations :
        sections_m .append (
        "Prior source-linked reasoning preserved by the harness. This is working memory, "
        "not external evidence. Use its source refs to avoid rediscovering observations, "
        "but inspect or retain the referenced source text before relying on a material "
        "premise in the final answer:\n"
        +"\n\n---\n\n".join (helm .reasoning_observations )
        )
    if helm .retrieval_receipts :
        prune_freight_tickets =[
        {
        key :chit [key ]
        for key in ("tool","arguments","destinations","sources","calls")
        if key in chit 
        }
        for chit in helm .retrieval_receipts .values ()
        ]
        sections_m .append (
        "Completed external retrieval receipts. These record actions and a compact "
        "source inventory, not evidence. Each source entry maps a stable source ref "
        "to the exact VFS key whose text can be re-read instead of repeating a web "
        "search:\n"
        +json .dumps (
        prune_freight_tickets ,
        ensure_ascii =False ,
        indent =2 ,
        )
        )
    if helm .vfs_operation_receipts :
        sections_m .append (
        "Completed local VFS inspection operations. These are action history, not "
        "evidence. Do not repeat the same read or search merely by changing wording. "
        "When prior local inspections did not expose the missing relationship, change "
        "the evidence route:\n"
        +json .dumps (
        list (helm .vfs_operation_receipts .values ()),
        ensure_ascii =False ,
        indent =2 ,
        )
        )
    if helm .claim_ledger .entries :
        sections_m .append (
        "Retained source evidence ranked by provenance authority (official_pdf > "
        "institutional > primary_data > aggregator > encyclopedia > other). When "
        "multiple sources support the same claim, prefer the highest-authority source "
        "for citation in the final answer. Only each quote is source evidence; "
        "research_note is your prior interpretation and may be wrong:\n"
        +helm .claim_ledger .serialize_evidence ()
        )
    if helm .focused_lines :
        sections_m .append (
        "Recent unretained VFS observations. VFS remains the full source of truth; "
        "only one generous read-page of recent raw observations is replayed here. "
        "Retain lines that support or contradict a material premise. Re-read a VFS "
        "location when an older unretained observation becomes necessary:\n"
        +json .dumps (
        helm .focused_excerpts (),
        ensure_ascii =False ,
        indent =2 ,
        )
        )
    messages .insert (
    2 ,
    {
    "role":"user",
    "content":f"{marker_m}:\n\n"+"\n\n".join (sections_m ),
    },
    )


def _weld_origin_sheaves (
held :list [dict [str ,Any ]],
live_m :list [dict [str ,Any ]],
)->list [dict [str ,Any ]]:
    merged_m :dict [str ,dict [str ,Any ]]={str (item_m ["source_ref"]):item_m for item_m in held }
    for item_m in live_m :
        origin_badge =str (item_m ["source_ref"])
        prior_m =merged_m .get (origin_badge )
        if prior_m is None :
            merged_m [origin_badge ]=item_m 
            continue 
        prior_quotation =str (prior_m .get ("quote","")).strip ()
        live_quotation =str (item_m .get ("quote","")).strip ()
        if not prior_quotation or prior_quotation in live_quotation :
            quotation =live_quotation 
        elif not live_quotation or live_quotation in prior_quotation :
            quotation =prior_quotation 
        else :
            quotation =f"{prior_quotation}\n\n{live_quotation}"
        merged_m [origin_badge ]={**prior_m ,**item_m ,"quote":quotation }
    return list (merged_m .values ())


def _sighting_handle (sighting :Any ,index_m :int )->tuple [str |None ,str |None ]:
    if index_m >=len (sighting .results ):
        return sighting .receipt_id ,None 
    return sighting .receipt_id ,sighting .results [index_m ].result_id 


def _inquiry2_headway_thumbmark (helm :MeridianHelm )->tuple [Any ,...]:
    return (
    helm .evidence_requirements ,
    tuple (sorted (helm .sources )),
    tuple (
    (key ,tuple (sorted (indices_m )))
    for key ,indices_m in sorted (helm .focused_lines .items ())
    ),
    tuple (sorted (helm .claim_ledger .entries )),
    helm .research_state ,
    helm .audit_gap ,
    )


# ============ MOVE EXECUTORS ============


async def _run_sounding (
helm :MeridianHelm ,
args_m :dict [str ,Any ],
glimpse_outlay_girth :int |None =None ,
)->dict [str ,Any ]:
    query =str (args_m ["query"]).strip ()
    num =int (args_m .get ("num",10 ))
    sighting =await search_web (
    query ,
    provider =SOUNDING_CARRIER ,
    num =num ,
    timeout =SOUNDING_GAUGE ,
    )
    _jot_outlay (helm ,sighting )
    helm .search_count +=1 
    parent_slot_m =f"search://{helm.search_count}"
    helm .vfs [parent_slot_m ]=sighting .response .model_dump_json (indent =2 )
    items_m :list [dict [str ,Any ]]=[]
    preview_chars =8_000 
    if glimpse_outlay_girth is not None :
        preview_chars =min (
        preview_chars ,
        max (300 ,glimpse_outlay_girth //max (1 ,len (sighting .response .data ))),
        )
    for index_m ,item_m in enumerate (sighting .response .data ):
        ref =f"S{helm.search_count}.{index_m + 1}"
        key =f"{parent_slot_m}/result/{index_m + 1}"
        content =item_m .snippet or item_m .title or ""
        helm .vfs [key ]=content 
        receipt_id ,result_id =_sighting_handle (sighting ,index_m )
        helm .sources [ref ]=MeridianBeacon (
        ref =ref ,
        key =key ,
        title =item_m .title or item_m .link ,
        url =item_m .link ,
        content =content ,
        receipt_id =receipt_id ,
        result_id =result_id ,
        preview_chars =preview_chars ,
        )
        items_m .append (
        {
        "source_ref":f"[{ref}]",
        "vfs_key":key ,
        "title":item_m .title ,
        "url":item_m .link ,
        "text":helm .bounded_preview (
        key ,
        max_serialized_chars =preview_chars ,
        ),
        }
        )
    return {"ok":True ,"vfs_key":parent_slot_m ,"results":items_m }


async def _run_ferry (
helm :MeridianHelm ,
args_m :dict [str ,Any ],
glimpse_outlay_girth :int |None =None ,
)->dict [str ,Any ]:
    url =str (args_m ["url"]).strip ()
    if re .search (r"\.(?:xls|xlsx|xlsb)(?:[?#]|$)",url ,flags =re .IGNORECASE ):
        raise ValueError (
        "fetch_page cannot expose spreadsheet binary rows to VFS tools; search the "
        "same publisher for a CSV, HTML, or plain-text companion"
        )
    sighting =await fetch_page (url ,provider =SOUNDING_CARRIER ,timeout =FERRY_GAUGE )
    _jot_outlay (helm ,sighting )
    helm .page_count +=1 
    items_m :list [dict [str ,Any ]]=[]
    preview_chars =8_000 
    if glimpse_outlay_girth is not None :
        preview_chars =min (
        preview_chars ,
        max (300 ,glimpse_outlay_girth //max (1 ,len (sighting .response .data ))),
        )
    for index_m ,item_m in enumerate (sighting .response .data ):
        ref =f"P{helm.page_count + index_m}"
        key =f"page://{item_m.url}"
        helm .vfs [key ]=item_m .content 
        receipt_id ,result_id =_sighting_handle (sighting ,index_m )
        helm .sources [ref ]=MeridianBeacon (
        ref =ref ,
        key =key ,
        title =item_m .title or item_m .url ,
        url =item_m .url ,
        content =item_m .content ,
        receipt_id =receipt_id ,
        result_id =result_id ,
        preview_chars =preview_chars ,
        )
        item_payload_m ={
        "source_ref":f"[{ref}]",
        "vfs_key":key ,
        "title":item_m .title ,
        "url":item_m .url ,
        }
        if len (item_m .content )>preview_chars :
            termwise_reach =_run_termwise_reach (
            helm ,
            {"query":helm .question ,"targets":[key ]},
            )
            item_payload_m ["question_context"]={
            "instruction":(
            "These are the long page regions most relevant to the original question. Inspect them before "
            "issuing another page search or read."
            ),
            "windows":termwise_reach ["windows"],
            }
        item_payload_m ["text"]=helm .bounded_preview (
        key ,
        max_serialized_chars =preview_chars ,
        )
        items_m .append (item_payload_m )
    helm .page_count +=max (0 ,len (sighting .response .data )-1 )
    return {"ok":True ,"pages":items_m }


def _run_peruse (
helm :MeridianHelm ,
args_m :dict [str ,Any ],
*,
remember_beamed :bool =True ,
)->dict [str ,Any ]:
    key =str (args_m ["key"])
    if key not in helm .vfs :
        raise ValueError (f"unknown VFS key: {key}")

    rungs =helm .vfs [key ].splitlines ()or [""]

    def resolve_bound (value_m :Any ,default_m :int )->int :
        text =""if value_m is None else str (value_m ).strip ()
        if value_m is None or text .lower ()in {"","null","none"}:
            return default_m 
        location_m =helm .line_locations .get (text )
        if location_m is not None :
            if location_m [0 ]!=key :
                raise ValueError (f"line ID {value_m} belongs to {location_m[0]}, not {key}")
            return location_m [1 ]
        rung_figure_match =re .fullmatch (r"L?(\d+)",text ,flags =re .IGNORECASE )
        if rung_figure_match is None :
            raise ValueError (f"unknown line bound: {value_m}; use a displayed line ID or 1-based line number")
        return max (0 ,int (rung_figure_match .group (1 ))-1 )

    start =resolve_bound (args_m .get ("start_line"),0 )
    end =resolve_bound (args_m .get ("end_line"),len (rungs )-1 )
    if start >=len (rungs ):
        raise ValueError (f"start_line is beyond the file; {key} has {len(rungs)} lines")
    if end <start :
        raise ValueError ("end_line must not precede start_line")
    requested_end_m =min (len (rungs )-1 ,end )
    selected_indices_m :list [int ]=[]
    reply_girth =0 
    for index_m in range (start ,requested_end_m +1 ):
        estimated_girth =len (rungs [index_m ])+80 
        if selected_indices_m and reply_girth +estimated_girth >MERIDIAN_PERUSE_LEAF_GIRTH :
            break 
        selected_indices_m .append (index_m )
        reply_girth +=estimated_girth 
    selected_m =selected_indices_m 
    origin_badges =[f"[{origin_m.ref}]"for origin_m in helm .sources .values ()if origin_m .key ==key ]
    next_index_m =selected_m [-1 ]+1 if selected_m else start 
    truncated_m =next_index_m <=requested_end_m 
    next_rung_id =None 
    if truncated_m :
        next_rung_id =helm ._line_id_m (key ,next_index_m ,rungs [next_index_m ])
        helm .line_locations [next_rung_id ]=(key ,next_index_m )
    if remember_beamed :
        helm .remember_focused_lines (key ,selected_m )
    return {
    "ok":True ,
    "key":key ,
    "source_refs":origin_badges ,
    "lines":helm .render_lines (key ,selected_m ),
    "truncated":truncated_m ,
    "next_start_line":next_index_m +1 if truncated_m else None ,
    "next_start_line_id":next_rung_id ,
    }


def _run_muster (helm :MeridianHelm ,args_m :dict [str ,Any ])->dict [str ,Any ]:
    prefix_m =str (args_m ["prefix"])
    slots_m =[key for key in helm .vfs if key .startswith (prefix_m )]
    return {"ok":True ,"keys":slots_m }


def _run_stow (helm :MeridianHelm ,args_m :dict [str ,Any ])->dict [str ,Any ]:
    key =str (args_m ["key"])
    if key =="*":
        raise ValueError ("'*' cannot be a VFS key")
    helm .forget_focused_lines (key )
    helm .vfs [key ]=str (args_m ["content"])
    return {"ok":True ,"key":key ,"chars":len (helm .vfs [key ])}


def _run_jettison (helm :MeridianHelm ,args_m :dict [str ,Any ])->dict [str ,Any ]:
    key =str (args_m ["key"])
    existed_m =key in helm .vfs 
    helm .forget_focused_lines (key )
    helm .vfs .pop (key ,None )
    return {"ok":True ,"key":key ,"deleted":existed_m }


def _figure_values (text :str )->set [str ]:
    values_m :set [str ]=set ()
    for match_m in re .finditer (r"(?<![\w.])\d+(?:[,.]\d+)*%?",text ):
        prefix_m =text [:match_m .start ()].rstrip ()
        if prefix_m .endswith (("<",">")):
            continue 
        if re .search (
        r"(?:above|below|greater than|less than|lower than|more than|threshold(?: of)?)\s*$",
        prefix_m ,
        flags =re .IGNORECASE ,
        ):
            continue 
        raw_m =match_m .group (0 )
        digits_m =re .sub (r"\D","",raw_m )
        if len (digits_m )<2 and not any (marker_m in raw_m for marker_m in (",",".","%")):
            continue 
        values_m .add (raw_m .rstrip ("%").replace (",",""))
    return values_m 


def _verify2_held_figure_warrant (
helm :MeridianHelm ,
origin_m :MeridianBeacon ,
jot :str ,
selected_rungs_x :list [dict [str ,Any ]],
)->None :
    assertion_wording =re .sub (
    (
    r"\blines?\s+(?:L[0-9a-f]{10}|\d+)"
    r"(?:\s*(?:-|to|through)\s*(?:L[0-9a-f]{10}|\d+))?"
    r"(?:\s*\(L[0-9a-f]{10}\))?"
    ),
    "",
    jot ,
    flags =re .IGNORECASE ,
    )
    jot_figures2 =_figure_values (assertion_wording )
    selected_figures2 =_figure_values (
    "\n".join (str (item_m ["text"])for item_m in selected_rungs_x )
    )
    missing_m =jot_figures2 -selected_figures2 
    if not missing_m :
        return 

    origin_rungs =helm .vfs [origin_m .key ].splitlines ()or [""]
    locations_m :dict [str ,list [str ]]={}
    for figure in sorted (missing_m ):
        matching_indices_m =[
        index_m 
        for index_m ,rung_x in enumerate (origin_rungs )
        if figure in _figure_values (rung_x )
        ]
        if not matching_indices_m :
            if figure in _figure_values (origin_m .title ):
                locations_m [figure ]=[
                "source title only; choose a source whose citable body contains this value"
                ]
            continue 
        locations_m [figure ]=[
        f"line {index_m + 1} ({helm._line_id_m(origin_m.key, index_m, origin_rungs[index_m])})"
        for index_m in matching_indices_m [:3 ]
        ]
    if not locations_m :
        return 
    details_m ="; ".join (
    f"{figure}: {', '.join(rung_locations)}"
    for figure ,rung_locations in locations_m .items ()
    )
    raise ValueError (
    "the selected evidence span omits numeric facts asserted by note that are present "
    f"elsewhere in this source ({details_m}). Re-read those lines and retry "
    "retain_evidence with a span containing the supporting text"
    )


def _run_hold2_warrant (
helm :MeridianHelm ,
args_m :dict [str ,Any ],
)->dict [str ,Any ]:
    origin_identifier_m =str (args_m ["source"]).strip ().strip ("[]")
    origin_m =helm .sources .get (origin_identifier_m )
    if origin_m is None :
        origin_m =next (
        (candidate_m for candidate_m in helm .sources .values ()if candidate_m .key ==origin_identifier_m ),
        None ,
        )
    if origin_m is None :
        if origin_identifier_m in helm .vfs and re .fullmatch (r"search://\d+",origin_identifier_m ):
            raise ValueError (
            f"{args_m['source']} is a search-result container, not a citable source; "
            "use the displayed [Sx.y] source reference or search://N/result/y child key "
            "that contains the supporting text"
            )
        raise ValueError (f"unknown source reference or VFS key: {args_m['source']}")
    start_rung =args_m .get ("start_line")
    end_rung =args_m .get ("end_line")
    if start_rung is None or end_rung is None :
        raise ValueError ("start_line and end_line are required")
    peruse_form =_run_peruse (
    helm ,
    {
    "key":origin_m .key ,
    "start_line":start_rung ,
    "end_line":end_rung ,
    },
    remember_beamed =False ,
    )
    jot =str (args_m ["note"]).strip ()
    _verify2_held_figure_warrant (helm ,origin_m ,jot ,peruse_form ["lines"])
    rung_ids =" ".join (str (item_m ["line_id"])for item_m in peruse_form ["lines"])
    prior_reaches =list (helm .source_slices .get (origin_m .ref ,[]))

    manifest =helm .source_packet (
    f"{origin_m.ref} {rung_ids}",
    allow_preview =False ,
    include_structured_csv =True ,
    prefer_retained =False ,
    )
    if not manifest :
        raise RuntimeError (f"could not build evidence packet for source {origin_m.ref}")
    helm .source_slices [origin_m .ref ]=_weld_mark_reaches (
    prior_reaches ,
    list (helm .source_slices .get (origin_m .ref ,[])),
    )
    held =manifest [0 ]
    held ["research_note"]=jot
    existing_entry =helm .claim_ledger .entries .get (origin_m .ref )
    if existing_entry is not None :
        held =_weld_origin_sheaves ([existing_entry .evidence ],[held ])[0 ]
        prior_jot =str (existing_entry .evidence .get ("research_note","")).strip ()
        held ["research_note"]="\n".join (
        item_m for item_m in (prior_jot ,jot )if item_m
        )
    helm .claim_ledger .register (
    origin_m .ref ,
    held ,
    url =origin_m .url ,
    title =origin_m .title ,
    )
    held_indices ={
    helm .line_locations [str (item_m ["line_id"])][1 ]
    for item_m in peruse_form ["lines"]
    if str (item_m ["line_id"])in helm .line_locations 
    }
    helm .forget_focused_lines (origin_m .key ,held_indices )
    return {"ok":True ,"source_ref":f"[{origin_m.ref}]"}


def _run_moult_residual_origins (
helm :MeridianHelm ,
args_m :dict [str ,Any ],
)->dict [str ,Any ]:
    ground =str (args_m ["reason"]).strip ()
    if not ground :
        raise ValueError ("reason must not be blank")
    discarded_badges =set (helm .review_source_refs )
    discarded_origin_census =len (discarded_badges )
    helm .review_source_refs .clear ()
    held_slots ={helm .sources [ref ].key for ref in helm .claim_ledger .entries if ref in helm .sources }
    for ref in discarded_badges :
        origin_m =helm .sources .get (ref )
        if origin_m is not None and origin_m .key not in held_slots :
            helm .forget_focused_lines (origin_m .key )
    return {"ok":True ,"discarded_source_count":discarded_origin_census }


def _run_sieve (helm :MeridianHelm ,args_m :dict [str ,Any ])->dict [str ,Any ]:
    sieve =re .compile (str (args_m ["pattern"]))
    slots_m =helm .resolve_targets ([str (item_m )for item_m in args_m ["targets"]])
    cursor_value_m =args_m .get ("cursor")
    cursor_m =0 if cursor_value_m is None else int (cursor_value_m )
    if cursor_m <0 :
        raise ValueError ("cursor must be at least zero")
    raw_matches_m :list [tuple [str ,dict [str ,Any ]]]=[]
    for key in slots_m :
        for item_m in helm .render_lines (key ):
            if sieve .search (item_m ["text"]):
                raw_matches_m .append ((key ,item_m ))

    matches_m :list [dict [str ,Any ]]=[]
    leaf_girth =0 
    for key ,item_m in raw_matches_m [cursor_m :]:
        match_m ={"key":key ,**item_m }
        origin_badges =[f"[{origin_m.ref}]"for origin_m in helm .sources .values ()if origin_m .key ==key ]
        if origin_badges :
            match_m ["source_refs"]=origin_badges 
        lattice_reach :dict [str ,Any ]|None =None 
        csv_records_m =helm .structured_csv_records (
        key ,
        [0 ,item_m ["line"]-1 ],
        )
        if csv_records_m :
            match_m .pop ("text")
            match_m ["csv_record"]=csv_records_m [0 ]
        else :
            lattice_reach =_markdown2_lattice_reach (
            helm ,
            key ,
            item_m ["line"]-1 ,
            )
            if lattice_reach is not None :
                match_m ["table"]=lattice_reach 
        beamed_indices ={item_m ["line"]-1 }
        if lattice_reach is not None :
            beamed_indices .update (
            int (header_rung ["line"])-1 
            for header_rung in lattice_reach ["header"]
            )
        if origin_badges :
            helm .remember_focused_lines (key ,beamed_indices )
        matches_m .append (match_m )
        leaf_girth +=len (json .dumps (match_m ,ensure_ascii =False ,separators =(",",":")))
        if leaf_girth >=MERIDIAN_VSEARCH_LEAF_GIRTH :
            break 

    next_offset_m =cursor_m +len (matches_m )
    next_cursor_m =next_offset_m if next_offset_m <len (raw_matches_m )else None 
    return {
    "ok":True ,
    "matched_keys":slots_m ,
    "total_match_count":len (raw_matches_m ),
    "cursor":cursor_m ,
    "matches":matches_m ,
    "next_cursor":next_cursor_m ,
    }


def _bricks (helm :MeridianHelm ,slots_m :list [str ])->list [dict [str ,Any ]]:
    bricks :list [dict [str ,Any ]]=[]
    for key in slots_m :
        content =helm .vfs [key ]
        start =0 
        index_m =0 
        while start <len (content ):
            end =min (len (content ),start +3_000 )
            bricks .append (
            {
            "key":key ,
            "chunk":index_m ,
            "start":start ,
            "end":end ,
            "text":content [start :end ],
            }
            )
            if end ==len (content ):
                break 
            start =end -300 
            index_m +=1 
    return bricks 


def _termwise_terms (text :str )->set [str ]:
    return {
    term_x_m 
    for term_x_m in _TERMWISE_TERM_RE .findall (text .casefold ())
    if term_x_m not in _TERMWISE_SKIP_TERMS 
    }


def _broad_marked_quotations (text :str )->list [str ]:
    return [
    next (group_m for group_m in match_m .groups ()if group_m is not None ).strip ()
    for match_m in _BROAD_MARKED_QUOTATION_RE .finditer (text )
    ]


def _verbatim_quotation_slats (text :str ,quotations :list [str ])->list [tuple [int ,int ,str ]]:
    slats :list [tuple [int ,int ,str ]]=[]
    lowered_m =text .casefold ()
    leading_girth =(MERIDIAN_GLOSS_SLAT_GIRTH *3 )//4 
    for quotation_x in quotations :
        sounding_from =0 
        normalized_quotation =quotation_x .casefold ()
        while True :
            match_start_m =lowered_m .find (normalized_quotation ,sounding_from )
            if match_start_m <0 :
                break 
            start =max (0 ,match_start_m -leading_girth )
            end =min (len (text ),start +MERIDIAN_GLOSS_SLAT_GIRTH )
            start =max (0 ,end -MERIDIAN_GLOSS_SLAT_GIRTH )
            if not any (start <existing_end_m and existing_start_m <end for existing_start_m ,existing_end_m ,_ignored_m in slats ):
                slats .append ((start ,end ,quotation_x ))
            sounding_from =match_start_m +len (normalized_quotation )
    return slats 


def _termwise_slats (text :str ,terms_m :set [str ])->list [tuple [int ,int ,int ]]:
    if not text or not terms_m :
        return []
    if len (text )<=MERIDIAN_GLOSS_SLAT_GIRTH :
        return [(0 ,len (text ),sum (term_m in text .casefold ()for term_m in terms_m ))]

    stage_m =max (600 ,MERIDIAN_GLOSS_SLAT_GIRTH //3 )
    lowered_m =text .lower ()
    scored_m :list [tuple [int ,int ]]=[]
    start =0 
    while start <len (text ):
        slat =lowered_m [start :start +MERIDIAN_GLOSS_SLAT_GIRTH ]
        scored_m .append ((sum (term_m in slat for term_m in terms_m ),start ))
        if start +MERIDIAN_GLOSS_SLAT_GIRTH >=len (text ):
            break 
        start +=stage_m 
    scored_m .sort (key =lambda item_m :(-item_m [0 ],item_m [1 ]))

    selected_m :list [tuple [int ,int ,int ]]=[]
    for matched_term_census ,start in scored_m :
        if len (selected_m )>=MERIDIAN_GLOSS_SLAT_CENSUS :
            break 
        end =min (len (text ),start +MERIDIAN_GLOSS_SLAT_GIRTH )
        if any (start <selected_end_m and selected_start_m <end for selected_start_m ,selected_end_m ,_ignored_m in selected_m ):
            continue 
        if selected_m and matched_term_census ==0 :
            continue 
        selected_m .append ((start ,end ,matched_term_census ))
    return sorted (selected_m )


def _run_termwise_reach (helm :MeridianHelm ,args_m :dict [str ,Any ])->dict [str ,Any ]:
    slots_m =helm .resolve_targets ([str (item_m )for item_m in args_m ["targets"]])
    terms_m =_termwise_terms (f"{helm.question}\n{args_m['query']}")
    quotations =_broad_marked_quotations (helm .question )
    slats :list [dict [str ,Any ]]=[]
    for key in slots_m :
        content =helm .vfs [key ]
        selected_m :list [tuple [int ,int ,int ,str |None ]]=[
        (start ,end ,len (terms_m ),quotation_x )
        for start ,end ,quotation_x in _verbatim_quotation_slats (content ,quotations )
        ]
        for start ,end ,matched_term_census in _termwise_slats (content ,terms_m ):
            if any (
            start <selected_end_m and selected_start_m <end 
            for selected_start_m ,selected_end_m ,_ignored_m ,_ignored_m in selected_m 
            ):
                continue 
            selected_m .append ((start ,end ,matched_term_census ,None ))
        for start ,end ,matched_term_census ,verbatim_quotation in selected_m :
            start_rung =content [:start ].count ("\n")
            end_rung =content [:end ].count ("\n")+1 
            slats .append (
            {
            "key":key ,
            "start":start ,
            "end":end ,
            "matched_term_count":matched_term_census ,
            "exact_phrase":verbatim_quotation ,
            "lines":helm .render_lines (key ,range (start_rung ,end_rung )),
            }
            )
    slats .sort (
    key =lambda item_m :(
    item_m ["exact_phrase"]is None ,
    -int (item_m ["matched_term_count"]),
    str (item_m ["key"]),
    int (item_m ["start"]),
    )
    )
    return {"ok":True ,"matched_keys":slots_m ,"windows":slats [:MERIDIAN_GLOSS_SLAT_CENSUS ]}


def _raynorm (left_m :list [float ],right_m :list [float ])->float :
    numerator_m =sum (a_m *b_m for a_m ,b_m in zip (left_m ,right_m ,strict =True ))
    left_norm_m =math .sqrt (sum (value_m *value_m for value_m in left_m ))
    right_norm_m =math .sqrt (sum (value_m *value_m for value_m in right_m ))
    return numerator_m /(left_norm_m *right_norm_m )if left_norm_m and right_norm_m else 0.0 


async def _run_resonance (helm :MeridianHelm ,args_m :dict [str ,Any ])->dict [str ,Any ]:
    slots_m =helm .resolve_targets ([str (item_m )for item_m in args_m ["targets"]])
    embedded_bricks :list [tuple [dict [str ,Any ],list [float ]]]=[]
    missing_bricks :list [dict [str ,Any ]]=[]
    missing_cache_slots_m :list [tuple [str ,str ]]=[]
    missing_brick_counts :list [int ]=[]
    for key in slots_m :
        cache_slot_m =(key ,hashlib .sha256 (helm .vfs [key ].encode ()).hexdigest ())
        cached_m =helm .document_embeddings .get (cache_slot_m )
        if cached_m is not None :
            embedded_bricks .extend (cached_m )
            continue 
        bricks =_bricks (helm ,[key ])
        missing_cache_slots_m .append (cache_slot_m )
        missing_brick_counts .append (len (bricks ))
        missing_bricks .extend (bricks )

    if not embedded_bricks and not missing_bricks :
        return {"ok":True ,"matched_keys":slots_m ,"chunks":[]}
    query_sighting =await embed_text (
    str (args_m ["query"]),
    provider ="openrouter",
    model ="qwen/qwen3-embedding-8b",
    input_type ="query",
    provider_extra =BEARING_SLACK ,
    timeout =BEARING_GAUGE ,
    )
    if missing_bricks :
        document_sighting =await embed_text (
        [brick ["text"]for brick in missing_bricks ],
        provider ="openrouter",
        model ="qwen/qwen3-embedding-8b",
        input_type ="document",
        provider_extra =BEARING_SLACK ,
        timeout =BEARING_GAUGE ,
        )
        vectors_m =[item_m .embedding for item_m in sorted (document_sighting .response .data ,key =lambda item_m :item_m .index )]
        if len (vectors_m )!=len (missing_bricks ):
            raise RuntimeError (
            f"embedding result count mismatch: expected {len(missing_bricks)}, received {len(vectors_m)}"
            )
        offset_m =0 
        for cache_slot_m ,brick_census in zip (missing_cache_slots_m ,missing_brick_counts ,strict =True ):
            cached_m =list (
            zip (
            missing_bricks [offset_m :offset_m +brick_census ],
            vectors_m [offset_m :offset_m +brick_census ],
            strict =True ,
            )
            )
            helm .document_embeddings [cache_slot_m ]=cached_m 
            embedded_bricks .extend (cached_m )
            offset_m +=brick_census 

    query_bearing =query_sighting .response .data [0 ].embedding 
    scored_m =[
    {**brick ,"score":_raynorm (query_bearing ,bearing )}
    for brick ,bearing in embedded_bricks 
    ]
    scored_m .sort (key =lambda item_m :item_m ["score"],reverse =True )
    output :list [dict [str ,Any ]]=[]
    form_girth =0 
    for item_m in scored_m [:MERIDIAN_ECHO2_TOP_BRICKS ]:
        key =item_m ["key"]
        content_before_m =helm .vfs [key ][:item_m ["start"]]
        start_rung =content_before_m .count ("\n")
        rung_census =item_m ["text"].count ("\n")+1 
        sighting_item ={
        "key":key ,
        "chunk":item_m ["chunk"],
        "score":item_m ["score"],
        "lines":helm .render_lines (key ,range (start_rung ,start_rung +rung_census )),
        }
        origin_badges =[f"[{origin_m.ref}]"for origin_m in helm .sources .values ()if origin_m .key ==key ]
        if origin_badges :
            sighting_item ["source_refs"]=origin_badges 
        sighting_girth =len (
        json .dumps (
        sighting_item ,
        ensure_ascii =False ,
        separators =(",",":"),
        )
        )
        if (
        len (output )>=MERIDIAN_ECHO2_FLOOR_BRICKS 
        and form_girth +sighting_girth >MERIDIAN_ECHO2_SIGHTING_GIRTH 
        ):
            break 
        if origin_badges :
            helm .remember_focused_lines (
            key ,
            range (start_rung ,start_rung +rung_census ),
            )
        output .append (sighting_item )
        form_girth +=sighting_girth 
    return {"ok":True ,"matched_keys":slots_m ,"chunks":output }


async def _run_cabinet_sounding (
helm :MeridianHelm ,
args_m :dict [str ,Any ],
)->dict [str ,Any ]:
    sieve_sighting :dict [str ,Any ]|None =None 
    sieve_mishap :str |None =None 
    try :
        sieve_sighting =_run_sieve (helm ,args_m )
    except (TypeError ,ValueError ,re .error )as mishap :
        sieve_mishap =str (mishap )

    resonance_trigger :str |None =None 
    if sieve_sighting is None :
        resonance_trigger ="regex_error"
    elif int (sieve_sighting ["total_match_count"])==0 :
        resonance_trigger ="no_regex_matches"

    resonance_sighting :dict [str ,Any ]|None =None 
    resonance_mishap :str |None =None 
    if resonance_trigger is not None :
        try :
            resonance_sighting =await _run_resonance (helm ,args_m )
        except Exception as mishap :
            resonance_mishap =str (mishap )

    if sieve_sighting is None and resonance_sighting is None :
        raise RuntimeError (
        "both VFS search methods failed: "
        f"regex={sieve_mishap or 'unknown'}; similarity={resonance_mishap or 'unknown'}"
        )

    output :dict [str ,Any ]={
    "ok":True ,
    "similarity":{
    "status":"not_run",
    "reason":"regex_returned_matches_on_first_search",
    },
    }
    if sieve_sighting is not None :
        output ["regex"]={
        key :value_m 
        for key ,value_m in sieve_sighting .items ()
        if key not in {"ok","matched_keys"}
        }
    if sieve_mishap is not None :
        output ["regex_error"]=sieve_mishap 
    if resonance_sighting is not None :
        output ["similarity"]={"status":"completed","trigger":resonance_trigger }
        output ["similarity"].update (
        {
        key :value_m 
        for key ,value_m in resonance_sighting .items ()
        if key not in {"ok","matched_keys"}
        }
        )
    if resonance_mishap is not None :
        output ["similarity"]={
        "status":"failed",
        "trigger":resonance_trigger ,
        "error":resonance_mishap ,
        }
    return output 


async def _run_move (
helm :MeridianHelm ,
label_m :str ,
args_m :dict [str ,Any ],
glimpse_outlay_girth :int |None =None ,
)->dict [str ,Any ]:
    if label_m in {"search_web","fetch_page"}:
        cached_m =helm .retrieval_output_cache .get (_freight_thumbmark (label_m ,args_m ))
        if cached_m is not None :
            return {**cached_m ,"cached":True }
    if label_m =="search_web":
        return await _run_sounding (helm ,args_m ,glimpse_outlay_girth )
    if label_m =="fetch_page":
        return await _run_ferry (helm ,args_m ,glimpse_outlay_girth )
    if label_m =="vfs_read":
        return _run_peruse (helm ,args_m )
    if label_m =="vfs_list":
        return _run_muster (helm ,args_m )
    if label_m =="vfs_write":
        return _run_stow (helm ,args_m )
    if label_m =="vfs_delete":
        return _run_jettison (helm ,args_m )
    if label_m =="retain_evidence":
        return _run_hold2_warrant (helm ,args_m )
    if label_m =="discard_remaining_sources":
        return _run_moult_residual_origins (helm ,args_m )
    if label_m =="vfs_search":
        return await _run_cabinet_sounding (helm ,args_m )
    if label_m =="update_research_state":
        inquiry2_helm =str (args_m ["state"]).strip ()
        if not inquiry2_helm :
            raise ValueError ("state must not be blank")
        helm .research_state =inquiry2_helm 
        return {"ok":True }
    raise ValueError (f"unknown tool: {label_m}")


def _distinct2_move_moves (moves :list [Any ])->tuple [list [Any ],int ]:
    distinct_moves :list [Any ]=[]
    seen_m :set [tuple [str ,str ]]=set ()
    for move in moves :
        try :
            arguments_m =json .dumps (
            json .loads (move .arguments ),
            ensure_ascii =False ,
            sort_keys =True ,
            separators =(",",":"),
            )
        except json .JSONDecodeError :
            arguments_m =move .arguments 
        thumbmark =(move .name ,arguments_m )
        if thumbmark in seen_m :
            continue 
        seen_m .add (thumbmark )
        distinct_moves .append (move )
    return distinct_moves ,len (moves )-len (distinct_moves )


# ============ PASSAGE LOOP & ENTRYPOINT ============


async def _notarize_ruling (
*,
helm :MeridianHelm ,
inquiry :str ,
current_reply :str ,
ground :str ,
assistant_context_m :str ,
last_manifest :list [dict [str ,Any ]],
final_origin_cuts :dict [str ,list [CitationSlice ]],
)->tuple [str ,list [dict [str ,Any ]]]:
    finalization_reach ="\n\n".join (
    value_m 
    for value_m in (
    helm .research_state .strip (),
    ground .strip (),
    assistant_context_m .strip (),
    )
    if value_m 
    )
    manifest =helm .source_packet (
    finalization_reach ,
    include_structured_csv =True ,
    )
    if not manifest :
        raise ValueError (
        "final answer must mention at least one observed source reference such as S1.2 or P1"
        )
    unretained_leaf_badges =[
    str (item_m ["source_ref"])
    for item_m in manifest 
    if str (item_m ["source_ref"]).strip ("[]").startswith ("P")
    and str (item_m ["source_ref"]).strip ("[]")not in helm .claim_ledger .entries
    ]
    if unretained_leaf_badges :
        raise ValueError (
        "fetched-page evidence must be preserved before finalization; call retain_evidence "
        f"for each decisive excerpt from {', '.join(unretained_leaf_badges)}, then retry"
        )
    for item_m in manifest :
        ref =str (item_m ["source_ref"])[1 :-1 ]
        final_origin_cuts [ref ]=_weld_mark_reaches (
        final_origin_cuts .get (ref ,[]),
        list (helm .source_slices .get (ref ,[])),
        )
    precise_badges ={str (item_m ["source_ref"])for item_m in [*last_manifest ,*manifest ]}
    held_sheaf =[
    entry .evidence
    for entry in helm .claim_ledger .entries .values ()
    if str (entry .evidence .get ("source_ref",""))not in precise_badges
    ]
    merged_sheaf =_weld_origin_sheaves (last_manifest ,held_sheaf )
    merged_sheaf =_weld_origin_sheaves (merged_sheaf ,manifest )
    # Sort manifest by provenance authority so the answer writer sees
    # official/institutional sources before aggregators.
    merged_sheaf .sort (
    key =lambda item_m :helm .claim_ledger .authority_for (
    str (item_m .get ("source_ref","")).strip ("[]")
    ).tier
    )
    merged_sheaf =[
    item_m 
    for item_m in merged_sheaf 
    if (
    (origin_m :=helm .sources .get (str (item_m ["source_ref"]).strip ("[]")))
    and origin_m .receipt_id 
    and origin_m .result_id 
    )
    ]
    if not merged_sheaf :
        raise ValueError (
        "none of the selected source records can be materialized as response citations"
        )
    reply =await _ruling_wording (
    helm =helm ,
    inquiry =inquiry ,
    prior_reply =current_reply ,
    stipulations =helm .evidence_requirements or "",
    inquiry2_helm =helm .research_state ,
    finalization_ground =ground ,
    manifest =merged_sheaf ,
    )
    return reply ,merged_sheaf 


async def _navigate (inquiry :str ,outlook_ruling :str )->tuple [str ,list [CitationRef ]]:
    passage_begun_at =time .monotonic ()
    horizon_alert_raised =False 
    helm =MeridianHelm (inquiry )
    helm .research_state =(
    f"Current best answer hypothesis:\n{outlook_ruling}\n"
    "Observed support: none yet.\n"
    "Most important unresolved question: test the hypothesis against external evidence."
    )
    current_reply =outlook_ruling 
    messages :list [Any ]=[
    {"role":"system","content":PASSAGE_CHARTER },
    {
    "role":"user",
    "content":(f"Original question:\n{inquiry}\n\nExpected answer hypothesis:\n{outlook_ruling}"),
    },
    ]
    last_manifest :list [dict [str ,Any ]]=[]
    final_origin_cuts :dict [str ,list [CitationSlice ]]={}
    final2_survey =""
    swerve_spur =""
    prior_move_signatures :tuple [str ,...]=()

    for _leg in range (160 ):
        rampart_drained =time .monotonic ()-passage_begun_at 
        if rampart_drained >=WARDEN_RAMPART_TICKS -NOTARIZE_STERN_BERTH_TICKS and last_manifest :
        # Wall governor: a citable checkpoint already exists and the clock
        # has entered the reserve. Publishing it now is local work; one
        # more model round could cross the kill line and lose everything.
            current_reply =_burnish_notarized_prose2 (current_reply )
            chart =helm .citation_plan (
            current_reply ,
            last_manifest ,
            final_origin_cuts ,
            final2_survey ,
            )
            return _issue_public_marks (
            current_reply ,
            chart ,
            unadorned_output_m =_wants2_naked_form (inquiry ),
            )
        if (
        not horizon_alert_raised 
        and rampart_drained >=HORIZON_ALERT_TICKS 
        ):
            messages .append (
            {
            "role":"user",
            "content":(
            "The external runtime has about 150 seconds remaining. Preserve answer quality. "
            "If the observed evidence can support the answer, retain any needed excerpts and call "
            "ready_to_finalize now. If one decisive uncertainty remains, perform only the single "
            "operation most likely to resolve it, then finalize. Do not restart broad research."
            ),
            }
            )
            horizon_alert_raised =True 
        _refresh2_freight_chit_note (messages ,helm )
        mandates_queued =helm .evidence_requirements is None 
        if mandates_queued :
            onhand_moves =MANDATES_MOVES 
            onhand_pilots =_mandates_pilots (
            horizon_alert_raised ,
            swerve_spur ,
            )
        else :
            onhand_moves =MOVE_CATALOG 
            onhand_pilots =_passage_pilots (
            helm ,
            horizon_alert_raised ,
            swerve_spur ,
            )
        ask_notes =(
        [
        {"role":"system","content":MANDATES_CHARTER },
        {"role":"user","content":f"Original question:\n{inquiry}"},
        ]
        if mandates_queued 
        else messages 
        )
        # Per-round ceiling: never grant a model round more wall time than the
        # governor still holds outside its reserve (donor lineage arithmetic).
        leg_canopy =min (
        PILOT_GAUGE ,
        max (
        LEG_CANOPY_FLOOR_TICKS ,
        WARDEN_RAMPART_TICKS -NOTARIZE_STERN_BERTH_TICKS -rampart_drained ,
        ),
        )
        sighting =await _parley_with_routing (
        onhand_pilots ,
        messages =ask_notes ,
        tools =onhand_moves ,
        tool_choice ="required",
        parallel_tool_calls =True ,
        timeout =leg_canopy ,
        max_output_tokens =None ,
        )
        _jot_outlay (helm ,sighting )
        _prune_drained_envoy_musing2 (messages )
        _prune_drained_move_findings (messages )
        envoy =_envoy_note (sighting )
        helm .remember_reasoning_observation (envoy .reasoning )
        moves ,twin_move_census =_distinct2_move_moves (list (envoy .tool_calls or ()))
        if not moves :
            prose2 =(sighting .llm .raw_text or "").strip ()
            if prose2 :
                try :
                    current_reply ,last_manifest =await _notarize_ruling (
                    helm =helm ,
                    inquiry =inquiry ,
                    current_reply =current_reply ,
                    ground =prose2 ,
                    assistant_context_m =_envoy_warrant_reach (envoy ),
                    last_manifest =last_manifest ,
                    final_origin_cuts =final_origin_cuts ,
                    )
                except ValueError as mishap :
                    swerve_spur =(
                    "The previous model tried to finalize without materializable support. "
                    f"Resolve this exact problem before finalizing again: {mishap}"
                    )
                    messages .extend (
                    [
                    envoy .to_input_message (),
                    {
                    "role":"user",
                    "content":(
                    f"Your terminal answer could not be finalized: {mishap}. "
                    "Use tools to resolve that exact problem, then either return a "
                    "supported terminal answer or call ready_to_finalize."
                    ),
                    },
                    ]
                    )
                    continue 
                current_reply =_burnish_notarized_prose2 (current_reply )
                chart =helm .citation_plan (
                current_reply ,
                last_manifest ,
                final_origin_cuts ,
                final2_survey ,
                )
                return _issue_public_marks (
                current_reply ,
                chart ,
                unadorned_output_m =_wants2_naked_form (inquiry ),
                )
            messages .extend (
            [
            envoy .to_input_message (),
            {
            "role":"user",
            "content":"Use a tool. Call ready_to_finalize only when inspected sources support the answer.",
            },
            ]
            )
            swerve_spur =(
            "The previous model returned neither a tool call nor a usable terminal answer. "
            "Choose the smallest valid operation that advances the investigation."
            )
            continue 
        envoy_input =replace (
        envoy ,
        tool_calls =tuple (moves ),
        ).to_input_message ()
        messages .append (envoy_input )
        ready_requested_m =False 
        survey_ready =False 
        headway_before =_inquiry2_headway_thumbmark (helm )
        leg_move_signatures :list [str ]=[]
        leg_fail_signatures :list [str ]=[]
        freight_move_census =sum (move .name in {"search_web","fetch_page"}for move in moves )
        freight_glimpse_outlay =(
        MERIDIAN_POOLED_GLIMPSE_GIRTH //freight_move_census if freight_move_census else None 
        )
        for move_index ,move in enumerate (moves ):
            move_thumbmark =json .dumps (
            {"tool":move .name ,"raw_arguments":move .arguments },
            ensure_ascii =False ,
            sort_keys =True ,
            )
            try :
                args_m =json .loads (move .arguments )
                if not isinstance (args_m ,dict ):
                    raise ValueError ("tool arguments must be a JSON object")
                move_thumbmark =json .dumps (
                {"tool":move .name ,"arguments":args_m },
                ensure_ascii =False ,
                sort_keys =True ,
                )
                if move .name =="set_evidence_requirements":
                    if not mandates_queued or len (moves )!=1 :
                        raise ValueError ("set_evidence_requirements must be the sole call before retrieval")
                    stipulations =str (args_m ["requirements"]).strip ()
                    if not stipulations :
                        raise ValueError ("requirements must not be empty")
                    helm .evidence_requirements =stipulations 
                    output ={"ok":True }
                elif move .name =="ready_to_finalize":
                    if leg_fail_signatures :
                        raise ValueError (
                        "cannot finalize in the same response after an earlier tool call "
                        "failed; inspect that tool feedback, correct the failed operation, "
                        "and retry finalization"
                        )
                    incompatible_moves =[
                    candidate_m .name 
                    for candidate_m in moves 
                    if candidate_m .name not in {"update_research_state","retain_evidence","ready_to_finalize"}
                    ]
                    if incompatible_moves :
                        raise ValueError (
                        "ready_to_finalize may only accompany update_research_state and retain_evidence; "
                        f"also received {', '.join(incompatible_moves)}"
                        )
                    if move_index !=len (moves )-1 :
                        raise ValueError ("ready_to_finalize must be the final call in the response")
                    ground =str (args_m ["reason"])
                    current_reply ,last_manifest =await _notarize_ruling (
                    helm =helm ,
                    inquiry =inquiry ,
                    current_reply =current_reply ,
                    ground =ground ,
                    assistant_context_m =_envoy_warrant_reach (envoy ),
                    last_manifest =last_manifest ,
                    final_origin_cuts =final_origin_cuts ,
                    )
                    final2_survey =""
                    ready_requested_m =True 
                    survey_ready =True 
                    output ={
                    "ok":True ,
                    "answer_checkpoint":current_reply ,
                    }
                elif move .name =="discard_remaining_sources":
                    if move_index !=len (moves )-1 :
                        raise ValueError ("discard_remaining_sources must be the last call in the response")
                    output =await _run_move (
                    helm ,
                    move .name ,
                    args_m ,
                    freight_glimpse_outlay ,
                    )
                else :
                    output =await _run_move (
                    helm ,
                    move .name ,
                    args_m ,
                    freight_glimpse_outlay ,
                    )
                    _chalk_freight_chit (helm ,move .name ,args_m ,output )
                    _chalk_cabinet_step_chit (helm ,move .name ,args_m ,output )
            except Exception as mishap :
                output ={
                "ok":False ,
                "error_type":(
                "tool_argument_validation"
                if isinstance (mishap ,(KeyError ,TypeError ,ValueError ,json .JSONDecodeError ))
                else "tool_execution"
                ),
                "details":str (mishap ),
                }
            leg_move_signatures .append (move_thumbmark )
            if not output .get ("ok"):
                leg_fail_signatures .append (
                json .dumps (
                {
                "tool":move .name ,
                "error_type":output .get ("error_type"),
                },
                ensure_ascii =False ,
                sort_keys =True ,
                )
                )
            messages .append (
            {
            "role":"tool",
            "tool_call_id":move .id ,
            "content":json .dumps (output ,ensure_ascii =False ),
            }
            )
        if twin_move_census :
            messages .append (
            {
            "role":"user",
            "content":(
            f"The previous response repeated {twin_move_census} exact tool "
            "calls. The harness executed each distinct call once. Continue from "
            "those results without repeating an identical call."
            ),
            }
            )
        if ready_requested_m :
            survey_stern =WARDEN_RAMPART_TICKS -(time .monotonic ()-passage_begun_at )
            if survey_stern <SURVEY_STERN_FLOOR_TICKS :
            # The review is one more model call the tail cannot afford; a
            # published cited answer beats a reviewed answer the kill line
            # erases. Ship the sealed checkpoint as-is.
                final2_survey =""
                helm .audit_gap =""
                survey_ready =True 
                current_reply =_burnish_notarized_prose2 (current_reply )
                chart =helm .citation_plan (
                current_reply ,
                last_manifest ,
                final_origin_cuts ,
                final2_survey ,
                )
                return _issue_public_marks (
                current_reply ,
                chart ,
                unadorned_output_m =_wants2_naked_form (inquiry ),
                )
            final2_survey =await _survey (
            helm ,
            inquiry ,
            current_reply ,
            last_manifest ,
            )
            decree ,survey_payload =_unravel_survey (final2_survey )
            if decree =="CONTINUE":
                helm .audit_gap =survey_payload 
                helm .clear_focused_lines ()
                survey_ready =False 
                messages =[
                {"role":"system","content":PASSAGE_CHARTER },
                {
                "role":"user",
                "content":(
                f"Original question:\n{inquiry}\n\n"
                "The finalization audit found one unresolved evidence gap:\n"
                f"{survey_payload}\n\n"
                "The harness will preserve the existing VFS, source references, "
                "retained evidence, retrieval receipts, and research state. Resolve "
                "this exact gap with the smallest useful next observation, update the "
                "research state if the answer changes, then finalize. Do not restart "
                "the investigation or repeat already supported premises."
                ),
                }
                ]
            elif decree =="REVISE":
                allowed_badges ={
                str (item_m ["source_ref"]).strip ("[]")
                for item_m in last_manifest 
                if isinstance (item_m ,dict )and item_m .get ("source_ref")
                }
                _verify2_inward_ruling_badges (
                survey_payload ,
                allowed_badges ,
                require_ref_m =not _wants2_naked_form (inquiry ),
                )
                current_reply =survey_payload 
                helm .audit_gap =""
                survey_ready =True 
            else :
                helm .audit_gap =""
                survey_ready =True 
        if MERIDIAN_PILOT_ROTA =="state_aware"and not ready_requested_m :
            headway_after =_inquiry2_headway_thumbmark (helm )
            live_moves =tuple (leg_move_signatures )
            live_failures_m =tuple (leg_fail_signatures )
            next_swerve_spur =""
            if live_failures_m :
                next_swerve_spur =(
                "The previous model's tool call failed. Read the detailed tool feedback, correct "
                "that exact operation or choose a different valid operation, and advance the "
                "investigation without repeating the failure."
                )
            elif (
            live_moves 
            and live_moves ==prior_move_signatures 
            and headway_after ==headway_before 
            ):
                next_swerve_spur =(
                "The previous model repeated the same operations without adding evidence or changing "
                "the research state. Choose a different evidence route."
                )
            elif live_moves and not live_failures_m and headway_after ==headway_before :
                next_swerve_spur =(
                "The previous operations succeeded mechanically but produced no new retained evidence, "
                "source coverage, inspected lines, or research-state change. Choose the smallest different "
                "operation that can resolve the current uncertainty."
                )
            if next_swerve_spur :
                messages .append ({"role":"user","content":next_swerve_spur })
            swerve_spur =next_swerve_spur 
            prior_move_signatures =live_moves 
        if ready_requested_m and survey_ready :
            current_reply =_burnish_notarized_prose2 (current_reply )
            chart =helm .citation_plan (
            current_reply ,
            last_manifest ,
            final_origin_cuts ,
            final2_survey ,
            )
            return _issue_public_marks (
            current_reply ,
            chart ,
            unadorned_output_m =_wants2_naked_form (inquiry ),
            )

    raise RuntimeError ("investigation did not finalize within the generous 160-turn ceiling")


@entrypoint ("query")
async def query (query :Query )->Response :
    try :
        outlook_ruling =await _outlook_ruling_wording (query .text )
    except Exception as mishap :
        if not _is_fleeting_llm_mishap (mishap ):
            raise 
        outlook_ruling =(
        "No expected-answer hypothesis was available because its model call "
        "failed. Investigate the original question directly and construct a "
        "revisable answer from observed external evidence."
        )
    reply ,citations =await _navigate (query .text ,outlook_ruling )
    if query .output_schema is not None :
        output =await _mint_formed_form (
        inquiry =query .text ,
        reply =reply ,
        output_schema_m =query .output_schema ,
        )
        return Response (output =output ,citations =citations )
    return Response (text =reply ,citations =citations )
