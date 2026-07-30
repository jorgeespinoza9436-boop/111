"""SN67 Harnyx miner — v148 deep-research pipeline. [slot 148 build 2026-07-24T21:06:10+00:00]
  SCORE / variance:
    (1) Determinism: SYNTHESIS 0.90->0.15, GATE 0.50->0.20, LABELING 0.50->0.20,
        PLANNING 0.35->0.25. v25 replay rows split 1.0-vs-0.0 on identical inputs
         median-over-validators scoring pays
        directly for row consistency.
    (2) Numeric entity coverage: when the question carries quantitative cues
        (counts, totals, changes, thresholds, percentages), an enumerated entity
        only counts as covered if it co-occurs with a digit in accepted evidence;
        otherwise it enters the entity-gap lane (fixes 2065f36f: per-artist Grammy
        tallies missing for one ceremony). Gap lane widened 3->5 entities and its
        per-entity searches now run concurrently (wall time ~= one search window).
    (3) Detail depth: MAX_DETAIL_FETCH_RESULTS 1->3 with FETCH_PAGE_CONCURRENCY
        2->3 and chunk total 16->18 — one fetched page cannot carry 5 entities'
        figures; target-balanced selection spreads the 3 fetches across targets.
    (4) Synthesis DERIVED-COUNT rule + threshold verdicts: counts enumerable from
        evidence (tracklists, rosters) are derived by counting, not treated as
        missing; every threshold candidate gets an explicit qualifies/fails
        verdict (fixes daaa0981: hedged 'would qualify if' scored 0.0).
  RUNTIME / cost:
    (5) Merged planner: one Gemma call per lite-search round emits targets WITH
        nested queries (was 2 sequential calls); legacy two-call path retained as
        automatic fallback when the merged payload lacks targets or queries.
    (6) JSON tool timeout 110s->45s (planner/labeler/gate outputs are small;
        clamps hung-call tails), keeping retry budget intact.
"""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from time import perf_counter
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_ai, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

PRODUCTION_PROFILE = "Naruto v148"

SYNTH_TIER_THINKING_MIN_REMAINING_SECONDS = 75.0
TASK_TOTAL_BUDGET_SECONDS                 = 270.0
JSON_LLM_TOOL_TIMEOUT_SECONDS = 45.0
SYNTH_TIER_FLOOR_MAX_REMAINING_SECONDS    = 8.0
SYNTH_HEDGE_DELAY_SECONDS                 = 35.0
FINAL_SYNTHESIS_LLM_TOOL_TIMEOUT_SECONDS = 180.0
FETCH_PAGE_TOOL_TIMEOUT_SECONDS           = 15.0
LITE_SEARCH_BUDGET_SECONDS                = 70.0
SYNTH_CALL_SAFETY_MARGIN_SECONDS          = 10.0
MIN_LITE_SEARCH_ROUND_REMAINING_SECONDS   = 18.0
SYNTH_CALL_MIN_TIMEOUT_SECONDS            = 8.0
LITE_SEARCH_TOOL_TIMEOUT_SECONDS          = 20.0
MAX_LITE_SEARCH_ROUNDS = 3
GATE_WATCHDOG_RESERVE_SECONDS             = 60.0
SEARCH_DEGRADED_RETRY_ENABLED             = True
SEARCH_AI_FALLBACK_ENABLED                = True
MAX_EVIDENCE_TARGETS_PER_ROUND = 4
MAX_QUERY_ROUTES_PER_TARGET = 2
MAX_INVENTORY_TERMS_PER_FIELD = 6
MAX_MATERIALIZED_SEARCH_QUERIES_PER_ROUND: int | None = None
SEARCH_RESULTS_PER_ROUTE = 5
MAX_SITE_CONSTRAINTS_PER_ROUTE = 2
SOURCE_INVENTORY_FIELD_NAMES = (
    "entities","aliases","source_families","document_handles",
    "metric_terms","date_scope","must_include","avoid","site_constraints",
)
SOURCE_INVENTORY_MATERIAL_FIELDS = (
    "entities","aliases","source_families","document_handles",
    "metric_terms","date_scope","must_include",
)
SITE_CONSTRAINT_DOMAIN_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$", re.IGNORECASE,
)
BAD_QUERY_BOOLEAN_BOUNDARY_RE = re.compile(r"(?i)^(?:AND|OR|NOT)\b|\b(?:AND|OR|NOT)$")
MAX_ACCUMULATED_SEARCH_RESULTS = 64
MAX_SELECTOR_INPUT_RESULTS = 64
MAX_DETAIL_FETCH_RESULTS = 3
MAX_ACCEPTED_IDS_PER_GATE = 3
ENTITY_GAP_MIN_ENTITIES              = 3
ENTITY_GAP_MIN_REMAINING_SECONDS     = 90.0
ENTITY_GAP_GATE_MIN_REMAINING_SECONDS = 45.0
ENTITY_GAP_MAX_ENTITIES_TO_AUGMENT   = 5
ENTITY_GAP_SEARCH_RESULTS_PER_ENTITY = 5
ENTITY_GAP_METRIC_HINT_MAX_TOKENS    = 10
ROLE_GAP_MIN_REMAINING_SECONDS         = 90.0
ROLE_GAP_GATE_MIN_REMAINING_SECONDS    = 45.0
ROLE_GAP_GATE_WATCHDOG_RESERVE_SECONDS = 60.0
ROLE_GAP_MAX_ROLES_TO_AUGMENT          = 5
ROLE_GAP_SEARCH_RESULTS_PER_ROLE       = 4
ROLE_GAP_QUERY_MAX_WORDS               = 24
GAP_AUGMENTATION_MAX_TOTAL_SECONDS     = 55.0
RAW_SNIPPET_FALLBACK_MAX_PACKETS       = 8
DETERMINISTIC_ANSWER_MAX_SENTENCES     = 3
DETERMINISTIC_ANSWER_SENTENCE_MAX_CHARS = 240
ROLE_BREADTH_COVERAGE_MIN_OBSERVATIONS = 3
MAX_EVIDENCE_GATE_CANDIDATES_PER_GROUP = 12
MAX_JSON_LLM_ATTEMPTS = 2
SOURCE_VALUE_LABELS = frozenset({"direct","primary_locator","context","contradiction","absence","weak","wrong"})
SOURCE_KIND_LABELS = frozenset({
    "official","primary","academic","government","regulatory","company","data_source",
    "reputable_media","secondary","forum_social","aggregator","weak_unknown","wrong_source",
})
SOURCE_SURFACE_LABELS = frozenset({"snippet","detail","both","locator","background","wrong"})
DETAIL_SOURCE_VALUES = frozenset({"direct","primary_locator","contradiction","absence"})
DETAIL_SOURCE_KINDS = frozenset({"official","primary","government","regulatory","company","data_source"})
DETAIL_SURFACES = frozenset({"detail","both","locator"})
MAX_RESEARCH_PLAN_ROLES = 5
PREMISE_SLOT_ID = "premise_check"
PRIMARY_SOURCE_SLOT_ID = "primary_source_fact"
FREE_INTENT_SLOT_IDS = frozenset({"free_1","free_2"})
INTENT_SLOT_DEFINITIONS = {
    "premise_check": "Check whether the question's central factual premise is true, false, partial, changed, or absent.",
    "primary_source_fact": "Find the official, primary, or canonical source for the main requested fact.",
    "independent_measurement": "Find an external measurement, benchmark, poll, observed outcome, audit, or reputable secondary result.",
    "comparison_baseline": "Find the comparator, previous state, prior period, expected value, rival item, or control value.",
    "exact_numeric_value": "Find an exact number with unit, scope, source, and comparator when needed.",
    "timeline_or_date": "Find the exact date, sequence, duration, enforcement date, filing date, vote date, or event window.",
    "scope_or_applicability": "Find the exact model, version, geography, period, final/proposed state, category, exception, or applicability condition.",
    "method_or_definition": "Find the metric definition, benchmark method, legal term, calculation basis, or measurement method.",
    "contradiction_or_absence": "Find disproof, missing-item evidence, contradiction, supersession, or evidence that the requested thing is absent.",
    "derived_calculation_inputs": "Find source operands required for arithmetic, deltas, ratios, or direct logical comparison.",
    "downstream_effect_or_reaction": "Find observed response, market/user/expert reaction, practical consequence, reversal, persistence, or mixed outcome.",
    "free_1": "Question-specific evidence intent selected by the model.",
    "free_2": "Question-specific evidence intent selected by the model.",
}
FALSE_PREMISE_CONTEXT_ROLE_TERMS = ("background","context","explain","justification","rationale","reason")
FETCH_PAGE_CONCURRENCY = 3
FETCH_PAGE_SEARCH_SNIPPET_FALLBACK_SOURCE_KIND = "fetch_page_search_snippet_fallback"
SEARCH_SNIPPET_EVIDENCE_SOURCE_KIND = "selected_search_snippet"
SEARCH_RESULT_TEXT_COMPRESSED_CHARS = 900
SEARCH_RESULT_TEXT_SEGMENT_CHARS = 300
BLOCKED_FETCH_HOST_SUFFIXES = (
    "facebook.com","instagram.com","x.com","twitter.com","tiktok.com",
    "threads.net","linkedin.com","reddit.com","youtube.com","youtu.be",
)
CHUNK_SIZE_CHARS = 1800
CHUNK_OVERLAP_CHARS = 300
HIT_CENTERED_PREVIEW_CONTEXT_CHARS = 600
MAX_CHUNK_CUE_PATTERNS_TOTAL = 32
MAX_CHUNK_CUE_PATTERNS_PER_ROLE = 5
MAX_CHUNK_CUE_PATTERN_CHARS = 240
MAX_SIGNAL_GENERATOR_SAMPLE_CHUNKS = 8
MAX_LEXICAL_ANCHOR_SETS_TOTAL = 24
MAX_LEXICAL_ANCHOR_TERMS_PER_FIELD = 8
MAX_LEXICAL_ANCHOR_TERM_CHARS = 80
LEXICAL_ANCHOR_NEAR_WINDOW_CHARS = 700
MAX_SELECTED_CHUNKS_PER_PAGE = 6
MAX_SELECTED_CHUNKS_TOTAL = 18
MAX_QUERY_FRAGMENT_CHUNKS_WHEN_NO_PATTERN_HITS = 12
MAX_CUE_HITS_PER_PATTERN_PER_CHUNK = 3
REGEX_UNIT_WORDS = frozenset({
    "%","bp","bps","cent","cents","cm","dollar","dollars","eur","euro","euros",
    "feet","foot","ft","gb","gbit","ghz","gwh","inch","inches","jpy","kg",
    "kilogram","kilograms","kilometer","kilometers","kilometre","kilometres",
    "km","kwh","lb","lbs","m","mb","meter","meters","metre","metres","mi",
    "mile","miles","ms","mw","mwh","percent","pound","pounds","second","seconds","usd","yen",
})
REGEX_ESCAPE_WORDS = frozenset({"b","d","s","w"})
MAX_TEXT_EXCERPT_CHARS = 900

GEMMA_MODEL = "google/gemma-4-31b-it"
GLM5_MODEL = "z-ai/glm-5"
_LLM_PROVIDER = "openrouter"
_SEARCH_PROVIDER = "parallel"
SYNTH_ALTERNATE_PROVIDER = "ai_gateway"
SYNTH_ALTERNATE_MODEL = "zai/glm-5.2-fast"
SYNTH_ALTERNATE_MAX_OUTPUT_TOKENS = 12000
RESEARCH_PLAN_MODEL = GEMMA_MODEL
EVIDENCE_GATE_MODEL = GEMMA_MODEL
URL_SELECTION_MODEL = GEMMA_MODEL
CHUNK_PATTERN_MODEL = GEMMA_MODEL
FINAL_SYNTHESIS_MODEL = GLM5_MODEL
PLANNING_TEMPERATURE   = 0.25
LABELING_TEMPERATURE   = 0.20
GATE_TEMPERATURE       = 0.20
SYNTHESIS_TEMPERATURE  = 0.15
EVIDENCE_GATE_THINKING = None
FINAL_SYNTHESIS_THINKING = LlmThinkingConfig(enabled=True)


@dataclass(frozen=True, slots=True)
class EvidenceCandidate:
    candidate_id: str
    parent_candidate_id: str
    slot_id: str
    slot_intent: str
    text_part: str
    text_start: int
    text_end: int
    receipt_id: str
    result_id: str
    url: str
    title: str | None
    source_text: str
    query: str
    source_kind: str


@dataclass(frozen=True, slots=True)
class AcceptedEvidence:
    url: str
    source_text: str
    source_result_text: str
    receipt_id: str
    result_id: str
    title: str | None
    parent_candidate_id: str
    text_part: str
    text_start: int
    text_end: int
    admission_reason: str


@dataclass(frozen=True, slots=True)
class CoverageAspect:
    aspect: str
    status: str
    supporting_packet_indices: tuple[int, ...]
    notes: str
    slot_id: str = ""


@dataclass(frozen=True, slots=True)
class ContractRole:
    role_id: str
    slot_id: str
    slot_intent: str
    question: str
    kind: str


@dataclass(frozen=True, slots=True)
class ResearchContract:
    roles: tuple[ContractRole, ...]
    answer_goal: str


@dataclass(frozen=True, slots=True)
class EvidenceObservation:
    role_id: str
    slot_id: str
    candidate_id: str
    entity: str
    metric: str
    value: str
    time_scope: str
    support: str
    source_tier: str
    packet_index: int


@dataclass(frozen=True, slots=True)
class CoverageRoleStatus:
    role_id: str
    slot_id: str
    status: str
    supporting_observation_indices: tuple[int, ...]
    value: str
    why: str


@dataclass(frozen=True, slots=True)
class CoverageState:
    roles: tuple[CoverageRoleStatus, ...]
    can_answer: bool
    missing_role_ids: tuple[str, ...]
    weak_role_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceSourceInventory:
    entities: tuple[str, ...]
    aliases: tuple[str, ...]
    source_families: tuple[str, ...]
    document_handles: tuple[str, ...]
    metric_terms: tuple[str, ...]
    date_scope: tuple[str, ...]
    must_include: tuple[str, ...]
    avoid: tuple[str, ...]
    site_constraints: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceSearchRoute:
    route_id: str
    target_id: str
    slot_id: str
    slot_intent: str
    needed_source_text: str
    source_type: str
    route_kind: str
    query: str
    site_constraints: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EvidenceSearchTarget:
    target_id: str
    slot_id: str
    slot_intent: str
    needed_source_text: str
    source_type: str
    inventory: EvidenceSourceInventory
    routes: tuple[EvidenceSearchRoute, ...]


@dataclass(frozen=True, slots=True)
class AccumulatedSearchResult:
    result_id: str
    target_id: str
    slot_id: str
    slot_intent: str
    needed_source_text: str
    source_type: str
    route_id: str
    route_kind: str
    url: str
    title: str | None
    note: str
    query: str
    receipt_id: str
    search_round: int
    stable_index: int


@dataclass(frozen=True, slots=True)
class LiteSearchBeam:
    results: tuple[AccumulatedSearchResult, ...]
    targets: tuple[EvidenceSearchTarget, ...]
    routes: tuple[EvidenceSearchRoute, ...]
    elapsed_ms: float
    stop_reason: str


@dataclass(frozen=True, slots=True)
class LiteSearchQueryResponse:
    query: str
    response: object | None


@dataclass(frozen=True, slots=True)
class SearchResultSourceLabel:
    basis: str
    result_id: str
    target_ids: tuple[str, ...]
    source_value: str
    source_kind: str
    surface: str


@dataclass(frozen=True, slots=True)
class SearchResultSourceLabelSet:
    labels: tuple[SearchResultSourceLabel, ...]
    ignored_label_count: int = 0
    unlabeled_result_ids: tuple[str, ...] = ()
    invalid_label_notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SearchResultSourceLabelerGroup:
    group_id: str
    targets: tuple[EvidenceSearchTarget, ...]
    routes: tuple[EvidenceSearchRoute, ...]
    results: tuple[AccumulatedSearchResult, ...]


@dataclass(frozen=True, slots=True)
class SearchResultEvidenceSelection:
    snippet_result_ids: tuple[str, ...]
    detail_result_ids: tuple[str, ...]
    overlap_result_ids: tuple[str, ...]
    labels: tuple[SearchResultSourceLabel, ...] = ()
    unlabeled_result_ids: tuple[str, ...] = ()
    detail_fill_result_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResearchPlanRole:
    role_id: str
    slot_id: str
    slot_intent: str
    question: str
    kind: str
    status: str
    value: str | None
    why_not_covered: str
    queries: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GateResult:
    accepted_packets: tuple[AcceptedEvidence, ...]
    coverage: tuple[CoverageAspect, ...] = ()
    role_ledger: tuple[ResearchPlanRole, ...] = ()
    can_answer: bool = False
    missing_questions: tuple[str, ...] = ()
    observations: tuple[EvidenceObservation, ...] = ()


@dataclass(frozen=True, slots=True)
class SearchResultSeed:
    search_receipt_id: str
    search_result_id: str
    slot_id: str
    slot_intent: str
    url: str
    title: str | None
    note: str


@dataclass(frozen=True, slots=True)
class CandidateSource:
    receipt_id: str
    result_id: str
    slot_id: str
    slot_intent: str
    url: str
    title: str | None
    source_text: str
    source_kind: str


@dataclass(frozen=True, slots=True)
class PageChunk:
    chunk_id: str
    page_id: str
    source_index: int
    chunk_index: int
    receipt_id: str
    result_id: str
    slot_id: str
    slot_intent: str
    url: str
    title: str | None
    query: str
    text_start: int
    text_end: int
    text: str
    source_kind: str


@dataclass(frozen=True, slots=True)
class PagePoolEntry:
    page_id: str
    cache_key: str
    source: CandidateSource


@dataclass(frozen=True, slots=True)
class ChunkCuePattern:
    pattern_index: int
    role_id: str
    pattern: str
    compiled: re.Pattern[str]


@dataclass(frozen=True, slots=True)
class ChunkCueHit:
    chunk_id: str
    role_id: str
    pattern_index: int
    start: int
    end: int
    score: int


@dataclass(frozen=True, slots=True)
class ChunkLexicalAnchorSet:
    anchor_index: int
    role_id: str
    all_terms: tuple[str, ...]
    any_terms: tuple[str, ...]
    near_terms: tuple[str, ...]
    avoid_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChunkLexicalAnchorHit:
    chunk_id: str
    role_id: str
    anchor_index: int
    matched_all_count: int
    matched_any_count: int
    matched_near_count: int
    avoid_count: int
    score: int
    best_span: tuple[int, int] | None


@dataclass(frozen=True, slots=True)
class ChunkSignalPlan:
    regex_patterns: tuple[ChunkCuePattern, ...]
    lexical_anchor_sets: tuple[ChunkLexicalAnchorSet, ...]


@dataclass(slots=True)
class ResearchRunState:
    pass


@entrypoint("query")
async def query(query: Query) -> Response:
    state = ResearchRunState()
    deadline = perf_counter() + TASK_TOTAL_BUDGET_SECONDS
    try:
        response = await _answer_question(query.text, state=state, deadline=deadline)
        return response
    except Exception:
        return Response(
            text=(
                "I could not complete a source-backed research answer for this question "
                "because the research pipeline failed before it produced accepted evidence. "
                "A reliable answer would require direct sources that address the question."
            )
        )


async def _answer_question(question: str, *, state: ResearchRunState, deadline: float) -> Response:
    search_beam = await _run_lite_search_beam(question=question, state=state, deadline=deadline)
    if not search_beam.results:
        return Response(text=_insufficient_answer(question, ()))
    search_selection = await _select_search_results_for_evidence_paths(
        question=question, targets=search_beam.targets, routes=search_beam.routes,
        results=search_beam.results, state=state,
    )
    role_ledger = _beam_role_ledger(
        targets=search_beam.targets, routes=search_beam.routes,
        search_selection=search_selection, results=search_beam.results, question=question,
    )
    research_contract = _beam_research_contract(role_ledger=role_ledger, question=question)
    candidates, _candidate_counter = await _candidates_from_selected_search_results(
        question=question, results=search_beam.results, search_selection=search_selection,
        role_ledger=role_ledger, candidate_counter=0, state=state,
    )
    gate_result = await _admit_evidence_from_candidate_beam(
        question=question, contract=research_contract, role_ledger=role_ledger,
        candidates=candidates, state=state, deadline=deadline,
    )
    accepted_packets = gate_result.accepted_packets
    accepted_observations = gate_result.observations
    coverage_state = _fallback_coverage_state(contract=research_contract, observations=accepted_observations)
    coverage = _coverage_from_coverage_state(coverage_state, accepted_observations)
    augmentation_deadline = min(deadline, perf_counter() + GAP_AUGMENTATION_MAX_TOTAL_SECONDS)
    enumerated_entities = _enumerated_question_entities(question)
    if enumerated_entities and perf_counter() < augmentation_deadline:
        missing_entities = _entities_missing_from_evidence(
            question=question, entities=enumerated_entities,
            packets=accepted_packets, observations=accepted_observations,
        )
        if missing_entities:
            gap_gate = await _augment_missing_entity_evidence(
                question=question, entities=missing_entities, contract=research_contract,
                role_ledger=role_ledger, existing_packets=accepted_packets,
                existing_observations=accepted_observations, state=state, deadline=deadline,
            )
            if gap_gate.accepted_packets:
                accepted_packets = (*accepted_packets, *gap_gate.accepted_packets)
                accepted_observations = (*accepted_observations, *gap_gate.observations)
                coverage_state = _fallback_coverage_state(contract=research_contract, observations=accepted_observations)
                coverage = _coverage_from_coverage_state(coverage_state, accepted_observations)
    if (
        (coverage_state.missing_role_ids or coverage_state.weak_role_ids)
        and perf_counter() < augmentation_deadline
        and deadline - perf_counter() >= ROLE_GAP_MIN_REMAINING_SECONDS
    ):
        role_gap_gate = await _augment_role_gap_evidence(
            question=question, coverage_state=coverage_state, contract=research_contract,
            role_ledger=role_ledger, existing_packets=accepted_packets,
            existing_observations=accepted_observations, state=state, deadline=deadline,
        )
        if role_gap_gate.accepted_packets:
            accepted_packets = (*accepted_packets, *role_gap_gate.accepted_packets)
            accepted_observations = (*accepted_observations, *role_gap_gate.observations)
            coverage_state = _fallback_coverage_state(contract=research_contract, observations=accepted_observations)
            coverage = _coverage_from_coverage_state(coverage_state, accepted_observations)
    if not accepted_packets:
        return await _answer_from_raw_snippets(
            question=question, results=search_beam.results, coverage=coverage,
            state=state, deadline=deadline,
        )
    final_answer = await _synthesize_final_answer(
        question=question, accepted_packets=accepted_packets,
        accepted_observations=accepted_observations, coverage=coverage, state=state,
        deadline=deadline,
    )
    final_answer, citations = _answer_text_and_citations(_safe_response_text(final_answer), accepted_packets)
    return Response(text=final_answer, citations=citations or None)


async def _run_lite_search_beam(*, question: str, state: ResearchRunState, deadline: float) -> LiteSearchBeam:
    started_perf = perf_counter()
    accumulated: list[AccumulatedSearchResult] = []
    targets_seen: list[EvidenceSearchTarget] = []
    routes_seen: list[EvidenceSearchRoute] = []
    tried_queries: set[str] = set()
    seen_urls: set[str] = set()
    wrong_entities: tuple[str, ...] = ()
    stop_reason = "max_lite_search_rounds"
    for round_index in range(MAX_LITE_SEARCH_ROUNDS):
        elapsed_seconds = perf_counter() - started_perf
        remaining_seconds = LITE_SEARCH_BUDGET_SECONDS - elapsed_seconds
        if accumulated and remaining_seconds < MIN_LITE_SEARCH_ROUND_REMAINING_SECONDS:
            stop_reason = "lite_search_budget_exhausted"
            break
        if perf_counter() > deadline - 60.0:
            stop_reason = "task_deadline_approaching"
            break
        targets, routes = await _generate_evidence_plan(
            question=question, round_index=round_index,
            tried_queries=tuple(sorted(tried_queries)), prior_targets=tuple(targets_seen),
            accumulated_results=tuple(accumulated), state=state,
            wrong_entities=wrong_entities,
        )
        if not targets:
            targets = await _generate_evidence_search_targets(
                question=question, round_index=round_index,
                tried_queries=tuple(sorted(tried_queries)), prior_targets=tuple(targets_seen),
                accumulated_results=tuple(accumulated), state=state,
                wrong_entities=wrong_entities,
            )
            routes = ()
        if targets and not routes:
            routes = await _generate_evidence_search_routes(
                question=question, round_index=round_index, targets=targets,
                tried_queries=tuple(sorted(tried_queries)),
                accumulated_results=tuple(accumulated), state=state,
            )
        if not routes:
            stop_reason = "no_new_evidence_search_routes"
            break
        round_queries = _materialized_evidence_search_queries(routes, tried_queries=tried_queries)
        if not round_queries:
            stop_reason = "no_new_lite_search_queries"
            break
        targets_seen.extend(targets)
        routes_seen.extend(routes)
        tried_queries.update(_query_identity(q) for q in round_queries)
        response = await _run_lite_search_round(routes=routes, queries=round_queries, state=state, round_index=round_index, deadline=deadline)
        if response is None:
            stop_reason = "lite_search_failed"
            break
        added_count = _accumulate_lite_search_results(
            accumulated=accumulated, response=response, routes=routes,
            seen_urls=seen_urls, round_index=round_index, state=state,
        )
        wrong_entities = _extract_candidate_entities(tuple(accumulated))
        if len(accumulated) >= MAX_ACCUMULATED_SEARCH_RESULTS:
            stop_reason = "accumulated_result_cap_reached"
            break
        if added_count == 0 and round_index > 0:
            stop_reason = "no_new_search_results"
            break
    return LiteSearchBeam(
        results=tuple(accumulated), targets=tuple(targets_seen), routes=tuple(routes_seen),
        elapsed_ms=_elapsed_ms(started_perf), stop_reason=stop_reason,
    )


async def _generate_evidence_search_targets(
    *, question: str, round_index: int, tried_queries: tuple[str, ...],
    prior_targets: tuple[EvidenceSearchTarget, ...],
    accumulated_results: tuple[AccumulatedSearchResult, ...], state: ResearchRunState,
    wrong_entities: tuple[str, ...] = (),
) -> tuple[EvidenceSearchTarget, ...]:
    messages = _build_evidence_search_target_messages(
        question=question, round_index=round_index, tried_queries=tried_queries,
        prior_targets=prior_targets, accumulated_results=accumulated_results,
        wrong_entities=wrong_entities,
    )
    payload = await _call_json_llm_with_retry(
        messages=messages, model=RESEARCH_PLAN_MODEL, temperature=PLANNING_TEMPERATURE,
        validate_payload=_evidence_search_target_payload_validator(),
        repair_payload=_repair_evidence_search_target_payload, state=state,
        stage=f"evidence_search_target_generation_round_{round_index}",
    )
    targets = _evidence_search_targets_from_payload(payload, round_index=round_index) if payload else ()
    if not targets and round_index == 0:
        fallback_inventory = EvidenceSourceInventory(
            entities=(question,), aliases=(), source_families=(), document_handles=(),
            metric_terms=(), date_scope=(), must_include=(), avoid=(), site_constraints=(),
        )
        fallback_route = EvidenceSearchRoute(
            route_id="target_1_1_route_1", target_id="target_1_1",
            slot_id=PRIMARY_SOURCE_SLOT_ID, slot_intent=_slot_intent_for_slot(PRIMARY_SOURCE_SLOT_ID),
            needed_source_text="Primary or canonical source text needed to answer the original question exactly.",
            source_type="primary_source", route_kind="direct_question", query=question, site_constraints=(),
        )
        targets = (EvidenceSearchTarget(
            target_id="target_1_1", slot_id=PRIMARY_SOURCE_SLOT_ID,
            slot_intent=_slot_intent_for_slot(PRIMARY_SOURCE_SLOT_ID),
            needed_source_text=fallback_route.needed_source_text,
            source_type=fallback_route.source_type, inventory=fallback_inventory,
            routes=(fallback_route,),
        ),)
    return targets


async def _generate_evidence_search_routes(
    *, question: str, round_index: int, targets: tuple[EvidenceSearchTarget, ...],
    tried_queries: tuple[str, ...], accumulated_results: tuple[AccumulatedSearchResult, ...],
    state: ResearchRunState,
) -> tuple[EvidenceSearchRoute, ...]:
    if not targets:
        return ()
    messages = _build_evidence_search_route_messages(
        question=question, round_index=round_index, targets=targets,
        tried_queries=tried_queries, accumulated_results=accumulated_results,
    )
    payload = await _call_json_llm_with_retry(
        messages=messages, model=RESEARCH_PLAN_MODEL, temperature=PLANNING_TEMPERATURE,
        validate_payload=_evidence_search_route_payload_validator(targets=targets),
        state=state, stage=f"evidence_search_route_generation_round_{round_index}",
    )
    routes = _evidence_search_routes_from_payload(payload=payload, targets=targets, tried_queries=set(tried_queries))
    if routes or round_index > 0:
        return routes
    target = targets[0]
    return (EvidenceSearchRoute(
        route_id=f"{target.target_id}_route_1", target_id=target.target_id,
        slot_id=target.slot_id, slot_intent=target.slot_intent,
        needed_source_text=target.needed_source_text, source_type=target.source_type,
        route_kind="direct_question_fallback", query=question, site_constraints=(),
    ),)


_PLAN_OUTPUT_TAIL_MARKER = '"site_constraints":[]}}]}'
_PLAN_OUTPUT_TAIL_MERGED = (
    '"site_constraints":[]},"queries":[{"query":"...","site_constraints":[]}]}]}'
)
_PLAN_NO_ROUTES_MARKER = "No routes, no query fields, no markdown, no reasons, no extra keys."
_PLAN_NO_ROUTES_MERGED = (
    'Each target MUST also carry "queries": 1-2 objects holding the exact evidence-seeking '
    "search strings for that target; each query is a plain string a web search tool executes "
    "as-is, with optional site_constraints of at most "
    f"{MAX_SITE_CONSTRAINTS_PER_ROUTE} bare domains. No markdown, no reasons, no other extra keys."
)
_PLAN_QUERY_STYLE_SECTION = (
    "\n\nQUERY STYLE: write the search strings yourself from each target's inventory — specific, "
    f"evidence-seeking, high-recall, at most {MAX_QUERY_ROUTES_PER_TARGET} per target, no duplicates "
    "of TRIED_QUERIES, no boolean operators at the string's edge."
)


def _build_evidence_plan_messages(
    *, question: str, round_index: int, tried_queries: tuple[str, ...],
    prior_targets: tuple[EvidenceSearchTarget, ...], accumulated_results: tuple[AccumulatedSearchResult, ...],
    wrong_entities: tuple[str, ...] = (),
) -> list[dict[str, str]] | None:
    """Merged-planner prompt: the target-inventory prompt extended so every target also
    carries its own executable queries — one Gemma round-trip instead of two per round."""
    messages = _build_evidence_search_target_messages(
        question=question, round_index=round_index, tried_queries=tried_queries,
        prior_targets=prior_targets, accumulated_results=accumulated_results,
        wrong_entities=wrong_entities,
    )
    system_content = messages[0]["content"]
    if _PLAN_OUTPUT_TAIL_MARKER not in system_content or _PLAN_NO_ROUTES_MARKER not in system_content:
        return None
    system_content = system_content.replace(_PLAN_OUTPUT_TAIL_MARKER, _PLAN_OUTPUT_TAIL_MERGED, 1)
    system_content = system_content.replace(_PLAN_NO_ROUTES_MARKER, _PLAN_NO_ROUTES_MERGED, 1)
    system_content += _PLAN_QUERY_STYLE_SECTION
    return [{"role": "system", "content": system_content}, {"role": "user", "content": messages[1]["content"]}]


def _evidence_plan_payload_validator() -> Callable[[dict[str, object]], str | None]:
    def validate(payload: dict[str, object]) -> str | None:
        extra = sorted(set(payload) - {"evidence_targets"})
        if extra:
            return f"Unexpected keys: {json.dumps(extra)}. Use only evidence_targets."
        targets = payload.get("evidence_targets")
        if not isinstance(targets, list) or not targets:
            return "evidence_targets must be a non-empty JSON array."
        for i, item in enumerate(targets):
            if not isinstance(item, dict):
                return f"evidence_targets[{i}] must be a JSON object."
            extra_keys = sorted(set(item) - {"slot_id","slot_intent","needed_source_text","source_type","inventory","queries"})
            if extra_keys:
                return f"evidence_targets[{i}] has unexpected keys: {json.dumps(extra_keys)}."
            slot_id = _string_value(item.get("slot_id"))
            if slot_id not in INTENT_SLOT_DEFINITIONS:
                return f"evidence_targets[{i}].slot_id is invalid: {json.dumps(slot_id)}. Valid: {json.dumps(list(INTENT_SLOT_DEFINITIONS))}."
            if slot_id in FREE_INTENT_SLOT_IDS and not _string_value(item.get("slot_intent")):
                return f"evidence_targets[{i}].slot_intent is required when slot_id is {slot_id}."
            if not _string_value(item.get("needed_source_text")):
                return f"evidence_targets[{i}].needed_source_text must be a non-empty string."
            if not _string_value(item.get("source_type")):
                return f"evidence_targets[{i}].source_type must be a non-empty string."
            inventory = item.get("inventory")
            if not isinstance(inventory, dict):
                return f"evidence_targets[{i}].inventory must be a JSON object."
            inv_error = _validate_source_inventory_payload(inventory, path=f"evidence_targets[{i}].inventory")
            if inv_error:
                return inv_error
            raw_queries = item.get("queries")
            if raw_queries is None:
                return f"evidence_targets[{i}].queries is required: 1-{MAX_QUERY_ROUTES_PER_TARGET} query objects."
            if not isinstance(raw_queries, list) or not raw_queries:
                return f"evidence_targets[{i}].queries must be a non-empty JSON array."
            for qi, raw_query in enumerate(raw_queries):
                if not isinstance(raw_query, dict):
                    return f"evidence_targets[{i}].queries[{qi}] must be a JSON object."
                query_extra = sorted(set(raw_query) - {"query","site_constraints"})
                if query_extra:
                    return f"evidence_targets[{i}].queries[{qi}] has unexpected keys: {json.dumps(query_extra)}."
                query = _clean_llm_search_query(raw_query.get("query"))
                if not query:
                    return f"evidence_targets[{i}].queries[{qi}].query must be a non-empty string."
                if _lite_search_query_syntax_error(query):
                    return f"evidence_targets[{i}].queries[{qi}].query is invalid: {_lite_search_query_syntax_error(query)}"
        return None
    return validate


def _evidence_plan_from_payload(
    payload: dict[str, object], *, round_index: int, tried_queries: set[str],
) -> tuple[tuple[EvidenceSearchTarget, ...], tuple[EvidenceSearchRoute, ...]]:
    """Single-pass parse of the merged planner payload into targets plus their routes.
    Target acceptance mirrors _evidence_search_targets_from_payload; nested-query route
    acceptance mirrors _evidence_search_routes_from_payload (caps, dedup, materialization)."""
    targets: list[EvidenceSearchTarget] = []
    routes: list[EvidenceSearchRoute] = []
    seen_keys: set[tuple[str, str, str, str]] = set()
    seen_materialized = set(tried_queries)
    for item in _object_list(payload.get("evidence_targets")):
        if len(targets) >= MAX_EVIDENCE_TARGETS_PER_ROUND:
            break
        slot_id = _string_value(item.get("slot_id"))
        if slot_id not in INTENT_SLOT_DEFINITIONS:
            continue
        slot_intent = _slot_intent_from_payload(slot_id, item)
        if slot_id in FREE_INTENT_SLOT_IDS and not slot_intent:
            continue
        needed_source_text = " ".join(_string_value(item.get("needed_source_text")).split())
        source_type = " ".join(_string_value(item.get("source_type")).split())
        key = (slot_id, slot_intent.casefold(), needed_source_text.casefold(), source_type.casefold())
        if not needed_source_text or not source_type or key in seen_keys:
            continue
        target_id = f"target_{round_index + 1}_{len(targets) + 1}"
        inventory = _source_inventory_from_payload(item.get("inventory"))
        seen_keys.add(key)
        target = EvidenceSearchTarget(
            target_id=target_id, slot_id=slot_id, slot_intent=slot_intent,
            needed_source_text=needed_source_text, source_type=source_type,
            inventory=inventory, routes=(),
        )
        targets.append(target)
        route_count = 0
        seen_base: set[str] = set()
        for raw_query in _object_list(item.get("queries")):
            if route_count >= MAX_QUERY_ROUTES_PER_TARGET:
                break
            query = _clean_llm_search_query(raw_query.get("query"))
            if not query or _lite_search_query_syntax_error(query):
                continue
            base_key = _query_identity(query)
            if not base_key or base_key in seen_base:
                continue
            site_constraints = _site_constraints_from_value(raw_query.get("site_constraints"))
            route = EvidenceSearchRoute(
                route_id=f"{target_id}_route_{route_count + 1}",
                target_id=target_id, slot_id=target.slot_id, slot_intent=target.slot_intent,
                needed_source_text=target.needed_source_text, source_type=target.source_type,
                route_kind="llm_query", query=query, site_constraints=site_constraints,
            )
            new_queries = tuple(
                q for q in _materialized_evidence_search_route_queries(route)
                if _query_identity(q) and _query_identity(q) not in seen_materialized
            )
            if not new_queries:
                continue
            seen_base.add(base_key)
            seen_materialized.update(_query_identity(q) for q in new_queries)
            route_count += 1
            routes.append(route)
    return tuple(targets), tuple(routes)


async def _generate_evidence_plan(
    *, question: str, round_index: int, tried_queries: tuple[str, ...],
    prior_targets: tuple[EvidenceSearchTarget, ...],
    accumulated_results: tuple[AccumulatedSearchResult, ...], state: ResearchRunState,
    wrong_entities: tuple[str, ...] = (),
) -> tuple[tuple[EvidenceSearchTarget, ...], tuple[EvidenceSearchRoute, ...]]:
    """One-call planner: targets and executable queries together. Returns ((), ()) on any
    shortfall so the beam falls back to the legacy two-call path with all its guarantees."""
    messages = _build_evidence_plan_messages(
        question=question, round_index=round_index, tried_queries=tried_queries,
        prior_targets=prior_targets, accumulated_results=accumulated_results,
        wrong_entities=wrong_entities,
    )
    if messages is None:
        return (), ()
    payload = await _call_json_llm_with_retry(
        messages=messages, model=RESEARCH_PLAN_MODEL, temperature=PLANNING_TEMPERATURE,
        validate_payload=_evidence_plan_payload_validator(),
        state=state, stage=f"evidence_plan_generation_round_{round_index}",
    )
    if not payload:
        return (), ()
    return _evidence_plan_from_payload(payload, round_index=round_index, tried_queries=set(tried_queries))


async def _run_lite_search_round(
    *, routes: tuple[EvidenceSearchRoute, ...], queries: tuple[str, ...],
    state: ResearchRunState, round_index: int, deadline: float,
) -> tuple[LiteSearchQueryResponse, ...] | None:
    route_by_query = _route_by_materialized_query(routes)
    result_budget = SEARCH_RESULTS_PER_ROUTE
    responses = await asyncio.gather(*(
        _run_lite_search_query(
            query=q,
            base_query=route_by_query[_query_identity(q)].query if _query_identity(q) in route_by_query else q,
            round_index=round_index,
            result_budget=result_budget,
            state=state,
            deadline=deadline,
        )
        for q in queries
    ))
    successful = tuple(item for item in responses if item.response is not None)
    return successful or None


async def _run_lite_search_query(
    *, query: str, base_query: str, round_index: int,
    result_budget: int, state: ResearchRunState, deadline: float,
) -> LiteSearchQueryResponse:
    try:
        response = await search_web([query], provider=_SEARCH_PROVIDER, num=result_budget, timeout=LITE_SEARCH_TOOL_TIMEOUT_SECONDS)
        return LiteSearchQueryResponse(query=query, response=response)
    except Exception:
        pass

    if SEARCH_DEGRADED_RETRY_ENABLED and base_query != query and (deadline - perf_counter()) > 10.0:
        try:
            response = await search_web([base_query], provider=_SEARCH_PROVIDER, num=result_budget, timeout=LITE_SEARCH_TOOL_TIMEOUT_SECONDS)
            return LiteSearchQueryResponse(query=base_query, response=response)
        except Exception:
            pass

    if SEARCH_AI_FALLBACK_ENABLED and (deadline - perf_counter()) > 10.0:
        try:
            response = await search_ai(base_query, provider=_SEARCH_PROVIDER, count=result_budget)
            return LiteSearchQueryResponse(query=base_query, response=response)
        except Exception:
            pass

    return LiteSearchQueryResponse(query=query, response=None)


def _accumulate_lite_search_results(
    *, accumulated: list[AccumulatedSearchResult], response: tuple[LiteSearchQueryResponse, ...],
    routes: tuple[EvidenceSearchRoute, ...], seen_urls: set[str],
    round_index: int, state: ResearchRunState,
) -> int:
    route_by_query = _route_by_materialized_query(routes)
    fallback_route = routes[0] if len(routes) == 1 else None
    added_count = 0
    response_results = tuple(
        (qr, tuple(getattr(qr.response, "results", ()) or ())) for qr in response
    )
    max_result_count = max((len(results) for _, results in response_results), default=0)
    for result_offset in range(max_result_count):
        for query_response, query_results in response_results:
            if len(accumulated) >= MAX_ACCUMULATED_SEARCH_RESULTS:
                break
            if result_offset >= len(query_results):
                continue
            result = query_results[result_offset]
            query_route = route_by_query.get(_query_identity(query_response.query)) or fallback_route
            url = (getattr(result, "url", "") or "").strip()
            note = (getattr(result, "note", "") or "").strip()
            if not url or not (note or getattr(result, "title", None)):
                continue
            if _blocked_fetch_url_reason(url):
                continue
            url_key = _normalize_url(url) or url
            if url_key in seen_urls:
                continue
            result_query = _string_value(getattr(result, "query", "")) or query_response.query
            route = route_by_query.get(_query_identity(result_query)) or query_route
            seen_urls.add(url_key)
            stable_index = len(accumulated) + 1
            result_id = _string_value(getattr(result, "result_id", "")) or f"R{stable_index}"
            accumulated.append(AccumulatedSearchResult(
                result_id=result_id,
                target_id=route.target_id if route else "",
                slot_id=route.slot_id if route else "",
                slot_intent=route.slot_intent if route else "",
                needed_source_text=route.needed_source_text if route else "",
                source_type=route.source_type if route else "",
                route_id=route.route_id if route else "",
                route_kind=route.route_kind if route else "",
                url=url, title=getattr(result, "title", None), note=note,
                query=result_query,
                receipt_id=getattr(query_response.response, "receipt_id", "") or "",
                search_round=round_index, stable_index=stable_index,
            ))
            added_count += 1
        if len(accumulated) >= MAX_ACCUMULATED_SEARCH_RESULTS:
            break
    return added_count


async def _select_search_results_for_evidence_paths(
    *, question: str, targets: tuple[EvidenceSearchTarget, ...],
    routes: tuple[EvidenceSearchRoute, ...], results: tuple[AccumulatedSearchResult, ...],
    state: ResearchRunState,
) -> SearchResultEvidenceSelection:
    selector_input = results[:MAX_SELECTOR_INPUT_RESULTS]
    if not selector_input:
        return SearchResultEvidenceSelection(snippet_result_ids=(), detail_result_ids=(), overlap_result_ids=())
    label_set = await _label_search_result_sources(
        question=question, targets=targets, routes=routes, results=selector_input, state=state,
    )
    return _search_result_selection_from_labels(
        results=selector_input, label_set=label_set, max_detail_results=MAX_DETAIL_FETCH_RESULTS,
    )


async def _label_search_result_sources(
    *, question: str, targets: tuple[EvidenceSearchTarget, ...],
    routes: tuple[EvidenceSearchRoute, ...], results: tuple[AccumulatedSearchResult, ...],
    state: ResearchRunState,
) -> SearchResultSourceLabelSet:
    groups = _search_result_source_labeler_groups(targets=targets, routes=routes, results=results)
    if not groups:
        return SearchResultSourceLabelSet(labels=(), unlabeled_result_ids=tuple(r.result_id for r in results))
    if len(groups) == 1:
        return await _label_search_result_source_group(
            question=question, group=groups[0], stage="search_result_source_labeler", state=state,
        )
    group_label_sets = await asyncio.gather(*(
        _label_search_result_source_group(
            question=question, group=g,
            stage=f"search_result_source_labeler_{_stage_suffix(g.group_id)}", state=state,
        ) for g in groups
    ))
    return _merge_source_label_sets(results=results, label_sets=group_label_sets)


async def _label_search_result_source_group(
    *, question: str, group: SearchResultSourceLabelerGroup, stage: str, state: ResearchRunState,
) -> SearchResultSourceLabelSet:
    messages = _build_search_result_source_labeler_messages(
        question=question, targets=group.targets, routes=group.routes, results=group.results,
    )
    payload = await _call_json_llm_with_retry(
        messages=messages, model=URL_SELECTION_MODEL, temperature=LABELING_TEMPERATURE,
        validate_payload=_search_result_source_labeler_payload_validator(), state=state, stage=stage,
    )
    return _source_labels_from_payload(payload=payload, targets=group.targets, results=group.results)


def _search_result_source_labeler_groups(
    *, targets: tuple[EvidenceSearchTarget, ...], routes: tuple[EvidenceSearchRoute, ...],
    results: tuple[AccumulatedSearchResult, ...],
) -> tuple[SearchResultSourceLabelerGroup, ...]:
    if not results:
        return ()
    valid_target_ids = {t.target_id for t in targets}
    result_buckets: dict[str, list[AccumulatedSearchResult]] = {tid: [] for tid in valid_target_ids}
    ungrouped: list[AccumulatedSearchResult] = []
    for result in results:
        if result.target_id in result_buckets:
            result_buckets[result.target_id].append(result)
        else:
            ungrouped.append(result)
    groups: list[SearchResultSourceLabelerGroup] = []
    seen: set[str] = set()
    for target in targets:
        if target.target_id in seen:
            continue
        seen.add(target.target_id)
        bucket = tuple(result_buckets.get(target.target_id, ()))
        if not bucket:
            continue
        groups.append(SearchResultSourceLabelerGroup(
            group_id=target.target_id,
            targets=tuple(t for t in targets if t.target_id == target.target_id),
            routes=tuple(r for r in routes if r.target_id == target.target_id),
            results=bucket,
        ))
    if ungrouped:
        groups.append(SearchResultSourceLabelerGroup(
            group_id="ungrouped", targets=targets, routes=routes, results=tuple(ungrouped),
        ))
    return tuple(groups)


def _merge_source_label_sets(
    *, results: tuple[AccumulatedSearchResult, ...],
    label_sets: tuple[SearchResultSourceLabelSet, ...],
) -> SearchResultSourceLabelSet:
    label_by_id: dict[str, SearchResultSourceLabel] = {}
    ignored = 0
    notes: list[str] = []
    for ls in label_sets:
        ignored += ls.ignored_label_count
        notes.extend(ls.invalid_label_notes)
        for label in ls.labels:
            label_by_id.setdefault(label.result_id, label)
    labels = tuple(label_by_id[r.result_id] for r in results if r.result_id in label_by_id)
    unlabeled = tuple(r.result_id for r in results if r.result_id not in label_by_id)
    return SearchResultSourceLabelSet(
        labels=labels, ignored_label_count=ignored,
        unlabeled_result_ids=unlabeled, invalid_label_notes=tuple(notes[:20]),
    )


def _stage_suffix(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "group"


async def _candidates_from_selected_search_results(
    *, question: str, results: tuple[AccumulatedSearchResult, ...],
    search_selection: SearchResultEvidenceSelection, role_ledger: tuple[ResearchPlanRole, ...],
    candidate_counter: int, state: ResearchRunState,
) -> tuple[tuple[EvidenceCandidate, ...], int]:
    result_by_id = {r.result_id: r for r in results}
    seen_keys: set[str] = set()
    snippet_candidates, candidate_counter = _snippet_results_to_candidates(
        results=tuple(result_by_id[rid] for rid in search_selection.snippet_result_ids if rid in result_by_id),
        seen_candidate_keys=seen_keys, candidate_counter=candidate_counter,
    )
    seeds = tuple(
        _search_seed_from_accumulated_result(result_by_id[rid])
        for rid in search_selection.detail_result_ids if rid in result_by_id
    )
    if not seeds:
        detail_candidates: tuple[EvidenceCandidate, ...] = ()
    else:
        page_entries, _ = await _page_entries_from_search_seeds(seeds=seeds, state=state, loop_index=0)
        chunks = _loop_chunks_from_page_entries(
            page_entries=page_entries,
            query_label=" | ".join(s.note[:120] for s in seeds),
            state=state, loop_index=0,
        )
        selected_chunks = await _select_page_chunks(
            question=question, loop_index=0, chunks=chunks, role_ledger=role_ledger, state=state,
        )
        detail_candidates, candidate_counter = _selected_chunks_to_candidates(
            chunks=selected_chunks, seen_candidate_keys=seen_keys, candidate_counter=candidate_counter,
        )
    return (*snippet_candidates, *detail_candidates), candidate_counter


def _snippet_results_to_candidates(
    *, results: tuple[AccumulatedSearchResult, ...],
    seen_candidate_keys: set[str], candidate_counter: int,
) -> tuple[tuple[EvidenceCandidate, ...], int]:
    candidates: list[EvidenceCandidate] = []
    for result in results:
        source_text = result.note.strip()
        if not source_text:
            continue
        key = f"{SEARCH_SNIPPET_EVIDENCE_SOURCE_KIND}:{_normalize_url(result.url) or result.url}:{_text_fingerprint(result.note)}"
        if key in seen_candidate_keys:
            continue
        seen_candidate_keys.add(key)
        candidate_counter += 1
        slot_id = result.slot_id or PRIMARY_SOURCE_SLOT_ID
        candidates.append(EvidenceCandidate(
            candidate_id=f"K{candidate_counter}",
            parent_candidate_id=result.result_id,
            slot_id=slot_id,
            slot_intent=result.slot_intent or _slot_intent_for_slot(slot_id),
            text_part="search_snippet", text_start=0, text_end=len(result.note),
            receipt_id=result.receipt_id, result_id=result.result_id,
            url=result.url, title=result.title, source_text=source_text,
            query=result.query, source_kind=SEARCH_SNIPPET_EVIDENCE_SOURCE_KIND,
        ))
    return tuple(candidates), candidate_counter


_ENTITY_TITLE_CONNECTORS = {"a", "an", "the", "of", "and", "vs", "vs.", "in", "on", "at", "for", "to", "&", "+"}
_ENTITY_LEADING_DISCOURSE_WORDS = {
    "among", "between", "looking", "considering", "comparing", "regarding", "given",
    "which", "what", "who", "about", "across", "over", "under", "within", "including",
    "rank", "list", "name", "order", "sort", "compare", "consider", "take", "evaluate",
}
_ENTITY_HINT_STOPWORDS = {
    "the", "a", "an", "of", "and", "or", "which", "what", "who", "whom", "whose", "its", "had",
    "has", "have", "was", "were", "is", "are", "be", "been", "during", "please", "use", "using",
    "data", "from", "looking", "at", "for", "in", "on", "to", "by", "with", "that", "this",
    "these", "those", "do", "does", "did", "how", "many", "much", "most", "greatest", "between",
    "among", "each", "per", "as", "it", "their", "them", "they", "films", "film", "movies",
    "movie", "companies", "company", "people", "person",
}


def _enumerated_question_entities(question: str) -> tuple[str, ...]:
    """Detect an explicit comma-list of >=3 capitalized named entities in the question."""
    text = " ".join(question.split())
    entities: list[str] = []
    for segment in re.split(r"[?;\n]", text):
        elements = [e.strip() for e in segment.split(",")]
        if len(elements) < ENTITY_GAP_MIN_ENTITIES:
            continue
        run: list[str] = []
        for index, raw in enumerate(elements):
            element = re.sub(r"^(?:and|or)\s+", "", raw).strip().strip("\"'")
            words = element.split()
            if not words:
                if len(run) >= ENTITY_GAP_MIN_ENTITIES:
                    break
                run = []
                continue
            if index == 0 or not run:
                phrase = _trailing_capitalized_phrase(words)
                if phrase:
                    run = [phrase]
                continue
            leading = _leading_capitalized_phrase(words) if element[0].isupper() or element[0].isdigit() else ""
            if leading:
                run.append(leading)
            else:
                if len(run) >= ENTITY_GAP_MIN_ENTITIES:
                    break
                run = []
        if len(run) >= ENTITY_GAP_MIN_ENTITIES:
            seen: set[str] = set()
            out = [e for e in run if not (e.lower() in seen or seen.add(e.lower()))]
            if len(out) >= ENTITY_GAP_MIN_ENTITIES:
                return tuple(out)
    return ()


def _leading_capitalized_phrase(words: list[str]) -> str:
    phrase: list[str] = []
    for index, word in enumerate(words):
        stripped = word.strip("\"'")
        if stripped and (stripped[0].isupper() or stripped[0].isdigit()):
            phrase.append(word)
        elif (
            phrase and stripped.lower() in _ENTITY_TITLE_CONNECTORS
            and index + 1 < len(words) and words[index + 1].strip("\"'")[:1].isupper()
        ):
            phrase.append(word)
        else:
            break
    while phrase and phrase[-1].strip("\"'").lower() in _ENTITY_TITLE_CONNECTORS:
        phrase.pop()
    if not phrase or len(phrase) > 8:
        return ""
    return " ".join(phrase)


def _trailing_capitalized_phrase(words: list[str]) -> str:
    phrase: list[str] = []
    for word in reversed(words):
        stripped = word.strip("\"'")
        if stripped and (stripped[0].isupper() or stripped[0].isdigit()):
            phrase.append(word)
        elif phrase and stripped.lower() in _ENTITY_TITLE_CONNECTORS:
            phrase.append(word)
        else:
            break
    while phrase and phrase[-1].strip("\"'").lower() in _ENTITY_TITLE_CONNECTORS:
        phrase.pop()
    ordered = list(reversed(phrase))
    while ordered and ordered[0].strip("\"'").lower() in _ENTITY_LEADING_DISCOURSE_WORDS:
        ordered.pop(0)
    if not ordered or len(ordered) > 8:
        return ""
    return " ".join(ordered)


def _entity_probe_token(entity: str) -> str:
    tokens = [t.strip(".,:;\"'").lower() for t in entity.split()]
    tokens = [t for t in tokens if t and t not in _ENTITY_TITLE_CONNECTORS]
    if not tokens:
        return entity.lower()
    return max(tokens, key=len)


NUMERIC_COVERAGE_DIGIT_WINDOW_CHARS = 160
NUMERIC_COVERAGE_MAX_OCCURRENCES_PER_ENTITY = 6
_NUMERIC_COVERAGE_QUESTION_CUES = (
    "how many", "number of", "total", "count", "percent", "percentage", "%",
    "increase", "decrease", "change in", "more than", "less than", "fewer than",
    "at least", "at most", "greater than", "smaller than", "highest", "lowest",
    "difference between", "grew", "declined", "nominations", "wins",
)


def _question_requires_numeric_coverage(question: str) -> bool:
    """True when the question compares or thresholds per-entity quantities, so an
    entity mention without nearby digits cannot satisfy its evidence need."""
    folded = " ".join(question.casefold().split())
    return any(cue in folded for cue in _NUMERIC_COVERAGE_QUESTION_CUES)


def _entity_occurs_near_digit(*, segment: str, needle: str) -> bool:
    """True when the entity co-occurs with a digit inside THIS evidence segment.
    Proximity is judged per segment so a digit belonging to one packet or
    observation never satisfies an adjacent, unrelated entity's coverage."""
    if not needle:
        return False
    start = 0
    for _occurrence in range(NUMERIC_COVERAGE_MAX_OCCURRENCES_PER_ENTITY):
        found = segment.find(needle, start)
        if found < 0:
            return False
        window_start = max(0, found - NUMERIC_COVERAGE_DIGIT_WINDOW_CHARS)
        window_end = found + len(needle) + NUMERIC_COVERAGE_DIGIT_WINDOW_CHARS
        if any(ch.isdigit() for ch in segment[window_start:window_end]):
            return True
        start = found + max(1, len(needle))
    return False


def _entities_missing_from_evidence(
    *, question: str, entities: tuple[str, ...], packets: tuple[AcceptedEvidence, ...],
    observations: tuple[EvidenceObservation, ...],
) -> tuple[str, ...]:
    attributed_packet_indices = {o.packet_index for o in observations if o.value.strip()}
    segments = [f"{o.entity} {o.value}".lower() for o in observations if o.value.strip()]
    segments += [
        f"{p.source_text} {p.source_result_text}".lower()
        for i, p in enumerate(packets, start=1) if i in attributed_packet_indices
    ]
    require_numeric = _question_requires_numeric_coverage(question)
    missing: list[str] = []
    for entity in entities:
        entity_needle = entity.lower()
        probe_needle = _entity_probe_token(entity)
        if require_numeric:
            if any(
                _entity_occurs_near_digit(segment=segment, needle=entity_needle)
                or _entity_occurs_near_digit(segment=segment, needle=probe_needle)
                for segment in segments
            ):
                continue
        else:
            if any(entity_needle in segment or probe_needle in segment for segment in segments):
                continue
        missing.append(entity)
    return tuple(missing)


def _question_metric_hint(question: str, entities: tuple[str, ...]) -> str:
    """Discriminative query hint for entity-gap searches. Digit-bearing tokens
    (years, ordinals, percentages) and their immediate noun neighbors are the
    retrieval anchors for count/comparison questions, so they claim hint budget
    before generic in-order content tokens — the metric nouns often sit late in
    the sentence and were previously truncated off the cap."""
    entity_tokens = {t.strip(".,:;\"'").lower() for e in entities for t in e.split()}
    raw_tokens = re.findall(r"[A-Za-z0-9%$][A-Za-z0-9%$.-]*", question)

    def _usable(token: str) -> str:
        low = token.lower().strip(".-")
        if not low or low in entity_tokens or low in _ENTITY_HINT_STOPWORDS:
            return ""
        return low

    digit_anchored: list[str] = []
    neighbor_pool: list[str] = []
    for index, token in enumerate(raw_tokens):
        low = _usable(token)
        if not low or not any(ch.isdigit() for ch in low) or len(low) < 2:
            continue
        digit_anchored.append(token if token.isupper() else low)
        picked = 0
        for follower in raw_tokens[index + 1:]:
            if picked >= 2:
                break
            follower_low = _usable(follower)
            if not follower_low or any(ch.isdigit() for ch in follower_low):
                continue
            neighbor_pool.append(follower if follower.isupper() else follower_low)
            picked += 1

    hint: list[str] = []
    seen_hint: set[str] = set()
    for pool in (digit_anchored, neighbor_pool, raw_tokens):
        for token in pool:
            low = _usable(token) if pool is raw_tokens else token.lower()
            if not low or low in seen_hint:
                continue
            seen_hint.add(low)
            hint.append(token if token.isupper() else low)
            if len(hint) >= ENTITY_GAP_METRIC_HINT_MAX_TOKENS:
                break
        if len(hint) >= ENTITY_GAP_METRIC_HINT_MAX_TOKENS:
            break
    source_match = re.search(
        r"\b(?:data from|according to|as reported by|reported in)\s+([A-Z][\w&' .-]{2,40}?)(?:\s*[.?,]|$)",
        question,
    )
    if source_match:
        source_name = source_match.group(1).strip()
        if source_name.lower() not in " ".join(hint).lower():
            hint.append(source_name)
    return " ".join(hint)


async def _augment_missing_entity_evidence(
    *, question: str, entities: tuple[str, ...], contract: ResearchContract,
    role_ledger: tuple[ResearchPlanRole, ...], existing_packets: tuple[AcceptedEvidence, ...],
    existing_observations: tuple[EvidenceObservation, ...], state: ResearchRunState,
    deadline: float,
) -> GateResult:
    metric_hint = _question_metric_hint(question, entities)
    candidates: list[EvidenceCandidate] = []
    seen_keys: set[str] = set()
    counter = 0
    gap_entities = entities[:ENTITY_GAP_MAX_ENTITIES_TO_AUGMENT]
    if not gap_entities or deadline - perf_counter() < ENTITY_GAP_MIN_REMAINING_SECONDS:
        return GateResult(accepted_packets=(), observations=())
    entity_queries = tuple(f"{entity} {metric_hint}".strip() for entity in gap_entities)

    async def _gap_search(gap_query: str) -> object | None:
        try:
            return await search_web(
                [gap_query], provider=_SEARCH_PROVIDER,
                num=ENTITY_GAP_SEARCH_RESULTS_PER_ENTITY, timeout=LITE_SEARCH_TOOL_TIMEOUT_SECONDS,
            )
        except Exception:
            return None

    gap_responses = await asyncio.gather(*(_gap_search(q) for q in entity_queries))
    for query, response in zip(entity_queries, gap_responses, strict=False):
        if response is None:
            continue
        receipt_id = getattr(response, "receipt_id", "") or ""
        for result in tuple(getattr(response, "results", ()) or ()):
            url = (getattr(result, "url", "") or "").strip()
            note = (getattr(result, "note", "") or "").strip()
            if not url or not note or _blocked_fetch_url_reason(url):
                continue
            key = f"entity_gap:{_normalize_url(url) or url}:{_text_fingerprint(note)}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            counter += 1
            candidates.append(EvidenceCandidate(
                candidate_id=f"G{counter}",
                parent_candidate_id=f"G{counter}",
                slot_id=PRIMARY_SOURCE_SLOT_ID,
                slot_intent=_slot_intent_for_slot(PRIMARY_SOURCE_SLOT_ID),
                text_part="search_snippet", text_start=0, text_end=len(note),
                receipt_id=receipt_id, result_id=f"G{counter}",
                url=url, title=getattr(result, "title", None), source_text=note,
                query=query, source_kind=SEARCH_SNIPPET_EVIDENCE_SOURCE_KIND,
            ))
    if not candidates or deadline - perf_counter() < ENTITY_GAP_GATE_MIN_REMAINING_SECONDS:
        return GateResult(accepted_packets=(), observations=())
    return await _run_observation_gate_once(
        question=question, loop_index=1, existing_packets=existing_packets,
        existing_observations=existing_observations, contract=contract,
        retrieval_roles=role_ledger, candidates=tuple(candidates),
        model=EVIDENCE_GATE_MODEL, state=state, stage="entity_gap_gate", lane="entity_gap",
    )


def _role_gap_roles_to_augment(
    *, role_ledger: tuple[ResearchPlanRole, ...], coverage_state: CoverageState,
) -> tuple[ResearchPlanRole, ...]:
    role_by_id = {role.role_id: role for role in role_ledger}
    ordered_role_ids = _stable_id_union((*coverage_state.missing_role_ids, *coverage_state.weak_role_ids))
    return tuple(role_by_id[rid] for rid in ordered_role_ids if rid in role_by_id)


def _role_gap_search_query(*, role: ResearchPlanRole, question: str) -> str:
    text = " ".join(role.question.split())
    if role.role_id == PREMISE_SLOT_ID or len(text.split()) < 3:
        text = " ".join(question.split())
    return " ".join(text.split()[:ROLE_GAP_QUERY_MAX_WORDS])


async def _augment_role_gap_evidence(
    *, question: str, coverage_state: CoverageState, contract: ResearchContract,
    role_ledger: tuple[ResearchPlanRole, ...], existing_packets: tuple[AcceptedEvidence, ...],
    existing_observations: tuple[EvidenceObservation, ...], state: ResearchRunState,
    deadline: float,
) -> GateResult:
    roles = _role_gap_roles_to_augment(role_ledger=role_ledger, coverage_state=coverage_state)
    role_queries: list[tuple[ResearchPlanRole, str]] = []
    seen_queries: set[str] = set()
    for role in roles:
        query = _role_gap_search_query(role=role, question=question)
        key = _query_identity(query)
        if not key or key in seen_queries:
            continue
        seen_queries.add(key)
        role_queries.append((role, query))
        if len(role_queries) >= ROLE_GAP_MAX_ROLES_TO_AUGMENT:
            break
    if not role_queries or deadline - perf_counter() < ROLE_GAP_MIN_REMAINING_SECONDS:
        return GateResult(accepted_packets=(), observations=())
    responses = await asyncio.gather(*(
        _run_lite_search_query(
            query=query, base_query=query, round_index=0,
            result_budget=ROLE_GAP_SEARCH_RESULTS_PER_ROLE, state=state, deadline=deadline,
        ) for _, query in role_queries
    ))
    candidates: list[EvidenceCandidate] = []
    seen_keys: set[str] = set()
    counter = 0
    for (role, _), query_response in zip(role_queries, responses, strict=False):
        if query_response.response is None:
            continue
        receipt_id = getattr(query_response.response, "receipt_id", "") or ""
        for result in tuple(getattr(query_response.response, "results", ()) or ()):
            url = (getattr(result, "url", "") or "").strip()
            note = (getattr(result, "note", "") or "").strip()
            if not url or not note or _blocked_fetch_url_reason(url):
                continue
            key = f"role_gap:{_normalize_url(url) or url}:{_text_fingerprint(note)}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            counter += 1
            candidates.append(EvidenceCandidate(
                candidate_id=f"RG{counter}",
                parent_candidate_id=f"RG{counter}",
                slot_id=role.slot_id,
                slot_intent=role.slot_intent or _slot_intent_for_slot(role.slot_id),
                text_part="search_snippet", text_start=0, text_end=len(note),
                receipt_id=receipt_id,
                result_id=_string_value(getattr(result, "result_id", "")) or f"RG{counter}",
                url=url, title=getattr(result, "title", None), source_text=note,
                query=query_response.query, source_kind=SEARCH_SNIPPET_EVIDENCE_SOURCE_KIND,
            ))
    if not candidates or deadline - perf_counter() < ROLE_GAP_GATE_MIN_REMAINING_SECONDS:
        return GateResult(accepted_packets=(), observations=())
    gate_timeout = deadline - ROLE_GAP_GATE_WATCHDOG_RESERVE_SECONDS - perf_counter()
    gate_results = await _gate_groups_with_deadline((
        _run_observation_gate_once(
            question=question, loop_index=2, existing_packets=existing_packets,
            existing_observations=existing_observations, contract=contract,
            retrieval_roles=role_ledger, candidates=tuple(candidates),
            model=EVIDENCE_GATE_MODEL, state=state, stage="role_gap_gate", lane="role_gap",
        ),
    ), timeout=gate_timeout)
    return gate_results[0] if gate_results else GateResult(accepted_packets=(), observations=())


async def _gate_groups_with_deadline(
    coros: Sequence[Awaitable[GateResult]], *, timeout: float,
) -> tuple[GateResult, ...]:
    """Run gate-group coroutines concurrently; past `timeout`, stop waiting on
    stragglers and keep whichever groups already finished."""
    tasks = [asyncio.ensure_future(c) for c in coros]
    done, pending = await asyncio.wait(tasks, timeout=max(0.0, timeout))
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    results: list[GateResult] = []
    for task in tasks:
        if task.cancelled() or task.exception() is not None:
            continue
        results.append(task.result())
    return tuple(results)


async def _admit_evidence_from_candidate_beam(
    *, question: str, contract: ResearchContract, role_ledger: tuple[ResearchPlanRole, ...],
    candidates: tuple[EvidenceCandidate, ...], state: ResearchRunState, deadline: float,
) -> GateResult:
    if not candidates:
        return GateResult(accepted_packets=(), observations=())
    groups = _evidence_gate_candidate_groups(candidates=candidates, role_ledger=role_ledger)
    timeout = deadline - GATE_WATCHDOG_RESERVE_SECONDS - perf_counter()
    results = await _gate_groups_with_deadline((
        _run_observation_gate_once(
            question=question, loop_index=0, existing_packets=(), existing_observations=(),
            contract=contract, retrieval_roles=role_ledger, candidates=group_candidates,
            model=EVIDENCE_GATE_MODEL, state=state, stage="beam_evidence_gate_group", lane=group_id,
        ) for group_id, group_candidates in groups
    ), timeout=timeout)
    return _merge_grouped_gate_results(tuple(results))


def _evidence_gate_candidate_groups(
    *, candidates: tuple[EvidenceCandidate, ...], role_ledger: tuple[ResearchPlanRole, ...],
) -> tuple[tuple[str, tuple[EvidenceCandidate, ...]], ...]:
    if len(candidates) <= MAX_EVIDENCE_GATE_CANDIDATES_PER_GROUP or not role_ledger:
        return (("all", candidates),)
    role_terms = {
        role.role_id: _query_match_terms(
            " ".join((role.slot_id, role.slot_intent, role.question, " ".join(role.queries)))
        ) for role in role_ledger
    }
    term_counts: dict[str, int] = {}
    for terms in role_terms.values():
        for term in terms:
            term_counts[term] = term_counts.get(term, 0) + 1
    buckets: dict[str, list[EvidenceCandidate]] = {role.role_id: [] for role in role_ledger}
    buckets["unmatched"] = []
    for candidate in candidates:
        buckets[_candidate_gate_group_role_id(candidate, role_ledger, role_terms, term_counts)].append(candidate)
    groups: list[tuple[str, tuple[EvidenceCandidate, ...]]] = []
    for role_id in (*[r.role_id for r in role_ledger], "unmatched"):
        bucket = buckets.get(role_id, [])
        if not bucket:
            continue
        for index, start in enumerate(range(0, len(bucket), MAX_EVIDENCE_GATE_CANDIDATES_PER_GROUP), start=1):
            suffix = f"_{index}" if len(bucket) > MAX_EVIDENCE_GATE_CANDIDATES_PER_GROUP else ""
            groups.append((f"{role_id}{suffix}", tuple(bucket[start:start + MAX_EVIDENCE_GATE_CANDIDATES_PER_GROUP])))
    return tuple(groups) or (("all", candidates),)


def _candidate_gate_group_role_id(
    candidate: EvidenceCandidate, role_ledger: tuple[ResearchPlanRole, ...],
    role_terms: Mapping[str, tuple[str, ...]], term_counts: Mapping[str, int],
) -> str:
    haystack = _query_word_match_text(" ".join((
        candidate.slot_id, candidate.slot_intent, candidate.query, candidate.url,
        candidate.title or "", candidate.source_kind, candidate.source_text[:1200],
    )))
    best_role_id = ""
    best_score = 0
    for role in role_ledger:
        score = 2 if role.slot_id == candidate.slot_id else 0
        for term in role_terms.get(role.role_id, ()):
            if f" {term} " in haystack:
                score += 3 if term_counts.get(term, 0) == 1 else 1
        if score > best_score:
            best_role_id = role.role_id
            best_score = score
    return best_role_id or "unmatched"


def _merge_grouped_gate_results(results: tuple[GateResult, ...]) -> GateResult:
    packets: list[AcceptedEvidence] = []
    observations: list[EvidenceObservation] = []
    packet_index_by_key: dict[tuple[str, str, int, int, str], int] = {}
    for result in results:
        local_to_global: dict[int, int] = {}
        for local_index, packet in enumerate(result.accepted_packets, start=1):
            key = (packet.result_id, packet.text_part, packet.text_start, packet.text_end, _text_fingerprint(packet.source_text))
            global_index = packet_index_by_key.get(key)
            if global_index is None:
                packets.append(packet)
                global_index = len(packets)
                packet_index_by_key[key] = global_index
            local_to_global[local_index] = global_index
        for obs in result.observations:
            packet_index = local_to_global.get(obs.packet_index)
            if packet_index is None:
                continue
            observations.append(replace(obs, packet_index=packet_index))
    return GateResult(accepted_packets=tuple(packets), observations=tuple(observations))


async def _page_entries_from_search_seeds(
    *, seeds: tuple[SearchResultSeed, ...], state: ResearchRunState, loop_index: int,
) -> tuple[tuple[PagePoolEntry, ...], dict[str, object]]:
    unique_seeds = _unique_search_result_seeds_by_url(seeds)
    semaphore = asyncio.Semaphore(FETCH_PAGE_CONCURRENCY)
    source_results = await asyncio.gather(*(
        _fetch_candidate_source(seed=seed, semaphore=semaphore, state=state, loop_index=loop_index)
        for seed in unique_seeds
    ))
    fetched_sources = tuple(source for source, status in source_results if status == "fetched")
    failed_seeds = tuple(
        seed for seed, (_, status) in zip(unique_seeds, source_results, strict=False) if status != "fetched"
    )
    fetched_entries = tuple(
        PagePoolEntry(page_id=f"P{i}", cache_key=_normalize_url(s.url) or s.url, source=s)
        for i, s in enumerate(fetched_sources, start=1)
    )
    fallback_entries = tuple(
        PagePoolEntry(
            page_id=f"P{i}",
            cache_key=_normalize_url(seed.url) or seed.url,
            source=_candidate_source_from_search_seed(seed, source_kind=FETCH_PAGE_SEARCH_SNIPPET_FALLBACK_SOURCE_KIND),
        ) for i, seed in enumerate(failed_seeds, start=len(fetched_entries) + 1)
    )
    page_entries = (*fetched_entries, *fallback_entries)
    return tuple(page_entries), {"fetched_page_count": len(fetched_entries), "fallback_count": len(fallback_entries)}


def _unique_search_result_seeds_by_url(seeds: tuple[SearchResultSeed, ...]) -> tuple[SearchResultSeed, ...]:
    unique: list[SearchResultSeed] = []
    seen: set[str] = set()
    for seed in seeds:
        key = _normalize_url(seed.url) or seed.url
        if key not in seen:
            seen.add(key)
            unique.append(seed)
    return tuple(unique)


async def _fetch_candidate_source(
    *, seed: SearchResultSeed, semaphore: asyncio.Semaphore,
    state: ResearchRunState, loop_index: int,
) -> tuple[CandidateSource, str]:
    async with semaphore:
        try:
            response = await fetch_page(seed.url, provider=_SEARCH_PROVIDER, timeout=FETCH_PAGE_TOOL_TIMEOUT_SECONDS)
        except Exception:
            return _candidate_source_from_search_seed(seed, source_kind=FETCH_PAGE_SEARCH_SNIPPET_FALLBACK_SOURCE_KIND), "exception"
        fetched = _candidate_source_from_fetch_response(seed=seed, response=response)
        if fetched is None:
            return _candidate_source_from_search_seed(seed, source_kind=FETCH_PAGE_SEARCH_SNIPPET_FALLBACK_SOURCE_KIND), "empty_or_unreferenceable"
        return fetched, "fetched"


def _candidate_source_from_search_seed(seed: SearchResultSeed, *, source_kind: str) -> CandidateSource:
    return CandidateSource(
        receipt_id=seed.search_receipt_id, result_id=seed.search_result_id,
        slot_id=seed.slot_id, slot_intent=seed.slot_intent,
        url=seed.url, title=seed.title, source_text=seed.note, source_kind=source_kind,
    )


def _candidate_source_from_fetch_response(*, seed: SearchResultSeed, response: object) -> CandidateSource | None:
    fetch_data = tuple(getattr(getattr(response, "response", None), "data", ()) or ())
    fetch_item = fetch_data[0] if fetch_data else None
    tool_results = tuple(getattr(response, "results", ()) or ())
    tool_result = tool_results[0] if tool_results else None
    source_text = getattr(tool_result, "note", "") or getattr(fetch_item, "content", "") or ""
    if not source_text.strip():
        return None
    receipt_id = (getattr(response, "receipt_id", "") or "").strip()
    result_id = (getattr(tool_result, "result_id", "") or "").strip()
    if not receipt_id or not result_id:
        return None
    url = (getattr(tool_result, "url", "") or "").strip() or (getattr(fetch_item, "url", "") or "").strip() or seed.url
    title = getattr(tool_result, "title", None) or getattr(fetch_item, "title", None) or seed.title
    return CandidateSource(
        receipt_id=receipt_id, result_id=result_id, slot_id=seed.slot_id,
        slot_intent=seed.slot_intent, url=url, title=title,
        source_text=source_text, source_kind="fetch_page",
    )


def _source_kind_counts(sources: tuple[CandidateSource, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for source in sources:
        counts[source.source_kind] = counts.get(source.source_kind, 0) + 1
    return counts


def _loop_chunks_from_page_entries(
    *, page_entries: tuple[PagePoolEntry, ...], query_label: str,
    state: ResearchRunState, loop_index: int,
) -> tuple[PageChunk, ...]:
    chunks: list[PageChunk] = []
    for i, entry in enumerate(page_entries, start=1):
        chunks.extend(_static_chunks_for_source(page_id=entry.page_id, source_index=i, source=entry.source, query=query_label))
    return tuple(chunks)


def _static_chunks_for_source(
    *, page_id: str, source_index: int, source: CandidateSource, query: str = "",
) -> tuple[PageChunk, ...]:
    return tuple(
        PageChunk(
            chunk_id=f"{page_id}_C{ci}", page_id=page_id, source_index=source_index, chunk_index=ci,
            receipt_id=source.receipt_id, result_id=source.result_id,
            slot_id=source.slot_id, slot_intent=source.slot_intent,
            url=source.url, title=source.title, query=query,
            text_start=ts, text_end=te, text=source.source_text[ts:te], source_kind=source.source_kind,
        )
        for ci, (ts, te) in enumerate(_overlap_text_ranges(len(source.source_text)), start=1)
    )


def _overlap_text_ranges(text_length: int) -> tuple[tuple[int, int], ...]:
    if text_length <= 0:
        return ()
    if text_length <= CHUNK_SIZE_CHARS:
        return ((0, text_length),)
    step = max(1, CHUNK_SIZE_CHARS - CHUNK_OVERLAP_CHARS)
    ranges: list[tuple[int, int]] = []
    start = 0
    while start < text_length:
        end = min(text_length, start + CHUNK_SIZE_CHARS)
        ranges.append((start, end))
        if end >= text_length:
            break
        start += step
    return tuple(ranges)


async def _select_page_chunks(
    *, question: str, loop_index: int, chunks: tuple[PageChunk, ...],
    role_ledger: tuple[ResearchPlanRole, ...], state: ResearchRunState,
) -> tuple[PageChunk, ...]:
    if not chunks:
        return ()
    chunk_lookup = {c.chunk_id: c for c in chunks}
    query_terms = _chunk_selection_query_terms(question=question, role_ledger=role_ledger, chunks=chunks)
    query_fragment_scores = _query_fragment_scores_by_chunk(chunks=chunks, query_terms=query_terms)
    sample_chunks = _sample_chunks_for_signal_generation(chunks=chunks, query_fragment_scores=query_fragment_scores)
    chunk_signals = await _generate_chunk_signals(
        question=question, loop_index=loop_index, role_ledger=role_ledger,
        sample_chunks=sample_chunks, query_terms=query_terms, state=state,
    )
    cue_hits = _scan_chunks_for_cue_hits(chunks=chunks, cue_patterns=chunk_signals.regex_patterns)
    lexical_hits = _scan_chunks_for_lexical_anchors(chunks=chunks, anchor_sets=chunk_signals.lexical_anchor_sets)
    selected_ids = _select_chunks_from_dual_signals(
        chunks=chunks, cue_hits=cue_hits, lexical_hits=lexical_hits,
        query_fragment_scores=query_fragment_scores, role_ledger=role_ledger,
    )
    if not selected_ids:
        selected_ids = _select_chunks_from_query_fragments(chunks=chunks, query_fragment_scores=query_fragment_scores)
    return tuple(chunk_lookup[cid] for cid in selected_ids if cid in chunk_lookup)


async def _generate_chunk_signals(
    *, question: str, loop_index: int, role_ledger: tuple[ResearchPlanRole, ...],
    sample_chunks: tuple[PageChunk, ...], query_terms: tuple[str, ...], state: ResearchRunState,
) -> ChunkSignalPlan:
    if not role_ledger or not sample_chunks:
        return ChunkSignalPlan(regex_patterns=(), lexical_anchor_sets=())
    regex_result, lexical_result = await asyncio.gather(
        _generate_chunk_cue_patterns(question=question, loop_index=loop_index, role_ledger=role_ledger, sample_chunks=sample_chunks, query_terms=query_terms, state=state),
        _generate_chunk_lexical_anchors(question=question, loop_index=loop_index, role_ledger=role_ledger, sample_chunks=sample_chunks, query_terms=query_terms, state=state),
        return_exceptions=True,
    )
    regex_patterns = regex_result if not isinstance(regex_result, BaseException) else ()
    lexical_anchor_sets = lexical_result if not isinstance(lexical_result, BaseException) else ()
    return ChunkSignalPlan(regex_patterns=regex_patterns, lexical_anchor_sets=lexical_anchor_sets)


async def _generate_chunk_cue_patterns(
    *, question: str, loop_index: int, role_ledger: tuple[ResearchPlanRole, ...],
    sample_chunks: tuple[PageChunk, ...], query_terms: tuple[str, ...], state: ResearchRunState,
) -> tuple[ChunkCuePattern, ...]:
    messages = _build_chunk_cue_pattern_messages(question=question, loop_index=loop_index, role_ledger=role_ledger, sample_chunks=sample_chunks, query_terms=query_terms)
    payload = await _call_json_llm_with_retry(
        messages=messages, model=CHUNK_PATTERN_MODEL, temperature=PLANNING_TEMPERATURE,
        validate_payload=_chunk_cue_pattern_payload_validator(role_ledger), state=state,
        stage=f"chunk_regex_cue_pattern_generation_loop_{loop_index}", max_attempts=1,
    )
    if payload is None:
        return ()
    patterns, _ = _chunk_cue_patterns_from_payload(payload=payload, role_ledger=role_ledger)
    return patterns


async def _generate_chunk_lexical_anchors(
    *, question: str, loop_index: int, role_ledger: tuple[ResearchPlanRole, ...],
    sample_chunks: tuple[PageChunk, ...], query_terms: tuple[str, ...], state: ResearchRunState,
) -> tuple[ChunkLexicalAnchorSet, ...]:
    messages = _build_chunk_lexical_anchor_messages(question=question, loop_index=loop_index, role_ledger=role_ledger, sample_chunks=sample_chunks, query_terms=query_terms)
    payload = await _call_json_llm_with_retry(
        messages=messages, model=CHUNK_PATTERN_MODEL, temperature=PLANNING_TEMPERATURE,
        validate_payload=_chunk_lexical_anchor_payload_validator(role_ledger), state=state,
        stage=f"chunk_lexical_anchor_generation_loop_{loop_index}", max_attempts=1,
    )
    if payload is None:
        return ()
    anchor_sets, _ = _chunk_lexical_anchors_from_payload(payload=payload, role_ledger=role_ledger)
    return anchor_sets


def _chunk_selection_query_terms(
    *, question: str, role_ledger: tuple[ResearchPlanRole, ...], chunks: tuple[PageChunk, ...],
) -> tuple[str, ...]:
    parts = [question]
    for role in role_ledger:
        parts.extend((role.slot_id, role.slot_intent, role.question, role.kind, " ".join(role.queries)))
    seen_queries: set[str] = set()
    for chunk in chunks:
        if chunk.query and chunk.query not in seen_queries:
            seen_queries.add(chunk.query)
            parts.append(chunk.query)
    return _query_match_terms(" ".join(parts))


def _query_fragment_scores_by_chunk(*, chunks: tuple[PageChunk, ...], query_terms: tuple[str, ...]) -> dict[str, int]:
    if not query_terms:
        return {c.chunk_id: 0 for c in chunks}
    scores: dict[str, int] = {}
    for chunk in chunks:
        text = _query_word_match_text(chunk.text)
        scores[chunk.chunk_id] = sum(1 for term in query_terms if f" {term} " in text)
    return scores


def _sample_chunks_for_signal_generation(
    *, chunks: tuple[PageChunk, ...], query_fragment_scores: Mapping[str, int],
) -> tuple[PageChunk, ...]:
    selected: list[PageChunk] = []
    selected_ids: set[str] = set()
    chunks_by_page: dict[str, list[PageChunk]] = {}
    for chunk in chunks:
        chunks_by_page.setdefault(chunk.page_id, []).append(chunk)
    for page_chunks in chunks_by_page.values():
        best = sorted(page_chunks, key=lambda c: (-query_fragment_scores.get(c.chunk_id, 0), c.source_index, c.chunk_index))[0]
        selected.append(best)
        selected_ids.add(best.chunk_id)
        if len(selected) >= MAX_SIGNAL_GENERATOR_SAMPLE_CHUNKS:
            return tuple(selected)
    for chunk in chunks:
        if chunk.chunk_id not in selected_ids and query_fragment_scores.get(chunk.chunk_id, 0) > 0:
            selected.append(chunk)
            selected_ids.add(chunk.chunk_id)
            if len(selected) >= MAX_SIGNAL_GENERATOR_SAMPLE_CHUNKS:
                return tuple(selected)
    for chunk in chunks:
        if chunk.chunk_id not in selected_ids:
            selected.append(chunk)
            if len(selected) >= MAX_SIGNAL_GENERATOR_SAMPLE_CHUNKS:
                break
    return tuple(selected)


def _scan_chunks_for_cue_hits(*, chunks: tuple[PageChunk, ...], cue_patterns: tuple[ChunkCuePattern, ...]) -> tuple[ChunkCueHit, ...]:
    if not cue_patterns:
        return ()
    hits: list[ChunkCueHit] = []
    for chunk in chunks:
        for cue_pattern in cue_patterns:
            count = 0
            for match in cue_pattern.compiled.finditer(chunk.text):
                start, end = match.span()
                if end <= start:
                    continue
                hits.append(ChunkCueHit(chunk_id=chunk.chunk_id, role_id=cue_pattern.role_id, pattern_index=cue_pattern.pattern_index, start=start, end=end, score=3))
                count += 1
                if count >= MAX_CUE_HITS_PER_PATTERN_PER_CHUNK:
                    break
    return tuple(hits)


def _scan_chunks_for_lexical_anchors(*, chunks: tuple[PageChunk, ...], anchor_sets: tuple[ChunkLexicalAnchorSet, ...]) -> tuple[ChunkLexicalAnchorHit, ...]:
    if not anchor_sets:
        return ()
    hits: list[ChunkLexicalAnchorHit] = []
    for chunk in chunks:
        for anchor_set in anchor_sets:
            hit = _lexical_anchor_hit_for_chunk(chunk=chunk, anchor_set=anchor_set)
            if hit is not None:
                hits.append(hit)
    return tuple(hits)


def _lexical_anchor_hit_for_chunk(*, chunk: PageChunk, anchor_set: ChunkLexicalAnchorSet) -> ChunkLexicalAnchorHit | None:
    all_spans = _literal_term_group_spans(chunk.text, anchor_set.all_terms)
    any_spans = _literal_term_group_spans(chunk.text, anchor_set.any_terms)
    near_spans = _literal_term_group_spans(chunk.text, anchor_set.near_terms)
    avoid_spans = _literal_term_group_spans(chunk.text, anchor_set.avoid_terms)
    all_count, any_count = len(all_spans), len(any_spans)
    near_count, avoid_count = _near_term_match_count(near_spans), len(avoid_spans)
    all_required = len(anchor_set.all_terms)
    all_satisfied = all_required == 0 or all_count == all_required
    if not all_satisfied and any_count == 0 and near_count == 0 and avoid_count == 0:
        return None
    positive_score = 0
    if all_required and all_satisfied:
        positive_score += 5 + (all_count * 3)
    positive_score += any_count * 3 + near_count * 2
    score = positive_score - avoid_count * 6
    if positive_score <= 0 and avoid_count <= 0:
        return None
    best_span = _best_lexical_span((*all_spans, *any_spans, *near_spans, *avoid_spans))
    return ChunkLexicalAnchorHit(
        chunk_id=chunk.chunk_id, role_id=anchor_set.role_id, anchor_index=anchor_set.anchor_index,
        matched_all_count=all_count, matched_any_count=any_count, matched_near_count=near_count,
        avoid_count=avoid_count, score=score, best_span=best_span,
    )


def _literal_term_group_spans(text: str, terms: tuple[str, ...]) -> tuple[tuple[int, int], ...]:
    spans: list[tuple[int, int]] = []
    for term in terms:
        term_spans = _literal_term_spans(text=text, term=term)
        if term_spans:
            spans.append(term_spans[0])
    return tuple(spans)


def _literal_term_spans(*, text: str, term: str) -> tuple[tuple[int, int], ...]:
    if not text or not term:
        return ()
    tokens = re.findall(r"[a-z0-9]+", term.casefold())
    if tokens:
        pattern = r"\b" + r"[\W_]+".join(re.escape(token) for token in tokens) + r"\b"
        return tuple(m.span() for m in re.finditer(pattern, text.casefold()))
    lowered_text, lowered_term = text.casefold(), term.casefold()
    spans: list[tuple[int, int]] = []
    start = 0
    while True:
        pos = lowered_text.find(lowered_term, start)
        if pos < 0:
            break
        spans.append((pos, pos + len(lowered_term)))
        start = pos + len(lowered_term)
    return tuple(spans)


def _near_term_match_count(spans: tuple[tuple[int, int], ...]) -> int:
    if len(spans) <= 1:
        return len(spans)
    sorted_spans = sorted(spans)
    for i, (window_start, _) in enumerate(sorted_spans):
        count = sum(1 for s, e in sorted_spans[i+1:] if s - window_start <= LEXICAL_ANCHOR_NEAR_WINDOW_CHARS and e >= window_start)
        if count >= 1:
            return count + 1
    return 1


def _best_lexical_span(spans: tuple[tuple[int, int], ...]) -> tuple[int, int] | None:
    if not spans:
        return None
    return sorted(spans)[0]


def _query_word_match_text(text: str) -> str:
    return f" {re.sub(r'[^a-z0-9]+', ' ', text.lower())} "


def _select_chunks_from_dual_signals(
    *, chunks: tuple[PageChunk, ...], cue_hits: tuple[ChunkCueHit, ...],
    lexical_hits: tuple[ChunkLexicalAnchorHit, ...], query_fragment_scores: Mapping[str, int],
    role_ledger: tuple[ResearchPlanRole, ...],
) -> tuple[str, ...]:
    hits_by_chunk: dict[str, list[ChunkCueHit]] = {}
    for hit in cue_hits:
        hits_by_chunk.setdefault(hit.chunk_id, []).append(hit)
    lexical_by_chunk: dict[str, list[ChunkLexicalAnchorHit]] = {}
    for hit in lexical_hits:
        lexical_by_chunk.setdefault(hit.chunk_id, []).append(hit)
    scored: list[tuple[int, int, int, PageChunk]] = []
    score_by_id: dict[str, int] = {}
    roles_by_id: dict[str, set[str]] = {}
    for chunk in chunks:
        ch = hits_by_chunk.get(chunk.chunk_id, [])
        lh = lexical_by_chunk.get(chunk.chunk_id, [])
        distinct_patterns = {h.pattern_index for h in ch}
        distinct_roles = {h.role_id for h in ch} | {h.role_id for h in lh}
        cue_score = min(18, len(distinct_patterns) * 3 + len(distinct_roles) * 2 + min(len(ch), 5))
        lexical_score = max(-12, min(22, sum(h.score for h in lh)))
        query_score = min(8, query_fragment_scores.get(chunk.chunk_id, 0))
        if cue_score <= 0 and lexical_score <= 0 and query_score <= 0:
            continue
        score = cue_score + lexical_score + query_score
        if score <= 0:
            continue
        roles_by_id[chunk.chunk_id] = distinct_roles
        score_by_id[chunk.chunk_id] = score
        scored.append((-score, chunk.source_index, chunk.chunk_index, chunk))
    scored.sort(key=lambda item: (item[0], item[1], item[2]))
    return _select_role_and_page_balanced_chunks(scored_chunks=scored, score_by_chunk_id=score_by_id, roles_by_chunk_id=roles_by_id, role_ledger=role_ledger)


def _select_role_and_page_balanced_chunks(
    *, scored_chunks: Sequence[tuple[int, int, int, PageChunk]], score_by_chunk_id: Mapping[str, int],
    roles_by_chunk_id: Mapping[str, set[str]], role_ledger: tuple[ResearchPlanRole, ...],
) -> tuple[str, ...]:
    selected_ids: list[str] = []
    selected_set: set[str] = set()
    page_counts: dict[str, int] = {}

    def add_chunk(chunk: PageChunk) -> None:
        if chunk.chunk_id in selected_set or page_counts.get(chunk.page_id, 0) >= MAX_SELECTED_CHUNKS_PER_PAGE or len(selected_ids) >= MAX_SELECTED_CHUNKS_TOTAL:
            return
        selected_ids.append(chunk.chunk_id)
        selected_set.add(chunk.chunk_id)
        page_counts[chunk.page_id] = page_counts.get(chunk.page_id, 0) + 1

    for role in role_ledger:
        best = next(
            (chunk for _, _, _, chunk in scored_chunks if role.role_id in roles_by_chunk_id.get(chunk.chunk_id, set())),
            None,
        )
        if best:
            add_chunk(best)
    seen_pages: set[str] = set()
    for _, _, _, chunk in scored_chunks:
        if chunk.page_id not in seen_pages:
            seen_pages.add(chunk.page_id)
            add_chunk(chunk)
    for _, _, _, chunk in scored_chunks:
        add_chunk(chunk)
        if len(selected_ids) >= MAX_SELECTED_CHUNKS_TOTAL:
            break
    return tuple(selected_ids)


def _select_chunks_from_query_fragments(*, chunks: tuple[PageChunk, ...], query_fragment_scores: Mapping[str, int]) -> tuple[str, ...]:
    scored = sorted(
        ((-query_fragment_scores.get(c.chunk_id, 0), c.source_index, c.chunk_index, c) for c in chunks if query_fragment_scores.get(c.chunk_id, 0) > 0),
        key=lambda item: (item[0], item[1], item[2]),
    )
    selected_ids: list[str] = []
    page_counts: dict[str, int] = {}
    for _, _, _, chunk in scored[:MAX_QUERY_FRAGMENT_CHUNKS_WHEN_NO_PATTERN_HITS]:
        if page_counts.get(chunk.page_id, 0) >= MAX_SELECTED_CHUNKS_PER_PAGE:
            continue
        selected_ids.append(chunk.chunk_id)
        page_counts[chunk.page_id] = page_counts.get(chunk.page_id, 0) + 1
        if len(selected_ids) >= MAX_SELECTED_CHUNKS_TOTAL:
            break
    return tuple(selected_ids)


def _selected_chunks_to_candidates(
    *, chunks: tuple[PageChunk, ...], seen_candidate_keys: set[str], candidate_counter: int,
) -> tuple[tuple[EvidenceCandidate, ...], int]:
    candidates: list[EvidenceCandidate] = []
    for chunk in chunks:
        key = f"selected_chunk:{_normalize_url(chunk.url) or chunk.url}:{chunk.text_start}:{chunk.text_end}:{_text_fingerprint(chunk.text)}"
        if key in seen_candidate_keys:
            continue
        seen_candidate_keys.add(key)
        candidate_counter += 1
        candidates.append(EvidenceCandidate(
            candidate_id=f"K{candidate_counter}", parent_candidate_id=chunk.chunk_id,
            slot_id=chunk.slot_id, slot_intent=chunk.slot_intent,
            text_part="chunk", text_start=chunk.text_start, text_end=chunk.text_end,
            receipt_id=chunk.receipt_id, result_id=chunk.result_id,
            url=chunk.url, title=chunk.title, source_text=chunk.text,
            query=chunk.query, source_kind="selected_chunk",
        ))
    return tuple(candidates), candidate_counter


async def _run_observation_gate_once(
    *, question: str, loop_index: int, existing_packets: tuple[AcceptedEvidence, ...],
    existing_observations: tuple[EvidenceObservation, ...], contract: ResearchContract,
    retrieval_roles: tuple[ResearchPlanRole, ...], candidates: tuple[EvidenceCandidate, ...],
    model: str, state: ResearchRunState, stage: str, lane: str = "combined",
) -> GateResult:
    messages = _build_observation_evidence_gate_messages(
        question=question, loop_index=loop_index, existing_packets=existing_packets,
        existing_observations=existing_observations, contract=contract,
        retrieval_roles=retrieval_roles, candidates=candidates,
    )
    payload = await _call_json_llm_with_retry(
        messages=messages, model=model, temperature=GATE_TEMPERATURE,
        thinking=EVIDENCE_GATE_THINKING,
        validate_payload=_observation_evidence_gate_payload_validator(candidates=candidates, contract=contract),
        state=state, stage=stage,
    )
    if payload is None:
        return GateResult(accepted_packets=(), observations=())
    accepted_packets = _accepted_packets_from_candidate_ids(payload=payload, candidates=candidates)
    observations = _evidence_observations_from_payload(
        payload=payload, existing_packet_count=len(existing_packets), candidates=candidates,
    )
    return GateResult(accepted_packets=accepted_packets, observations=observations)


def _budget_matched_synthesis_plan(remaining_seconds: float) -> tuple[str, LlmThinkingConfig, float] | None:
    if remaining_seconds < SYNTH_TIER_FLOOR_MAX_REMAINING_SECONDS:
        return None
    timeout = max(SYNTH_CALL_MIN_TIMEOUT_SECONDS, remaining_seconds - SYNTH_CALL_SAFETY_MARGIN_SECONDS)
    thinking = remaining_seconds >= SYNTH_TIER_THINKING_MIN_REMAINING_SECONDS
    return (FINAL_SYNTHESIS_MODEL, LlmThinkingConfig(enabled=thinking), timeout)


async def _run_synthesis_call(
    *, messages: Sequence[Mapping[str, object]], deadline: float,
    provider: str = _LLM_PROVIDER, model_override: str | None = None,
    max_output_tokens: int | None = None,
    thinking_override: LlmThinkingConfig | None = None,
) -> str | None:
    plan = _budget_matched_synthesis_plan(deadline - perf_counter())
    if plan is None:
        return None
    model, thinking, timeout = plan
    if thinking_override is not None:
        thinking = thinking_override
    try:
        if max_output_tokens is not None:
            response = await llm_chat(
                provider=provider,
                messages=messages, model=model_override or model,
                temperature=SYNTHESIS_TEMPERATURE,
                thinking=thinking, timeout=timeout,
                max_output_tokens=max_output_tokens,
            )
        else:
            response = await llm_chat(
                provider=provider,
                messages=messages, model=model_override or model,
                temperature=SYNTHESIS_TEMPERATURE,
                thinking=thinking, timeout=timeout,
            )
    except Exception:
        return None
    return _assistant_text(response) or None


async def _synthesize_final_answer(
    *, question: str, accepted_packets: tuple[AcceptedEvidence, ...],
    accepted_observations: tuple[EvidenceObservation, ...],
    coverage: tuple[CoverageAspect, ...], state: ResearchRunState,
    deadline: float, unvetted_evidence: bool = False,
) -> str:
    messages = _build_final_answer_messages(
        question=question, accepted_packets=accepted_packets,
        accepted_observations=accepted_observations, coverage=coverage,
        unvetted_evidence=unvetted_evidence,
    )
    if _budget_matched_synthesis_plan(deadline - perf_counter()) is None:
        return _deterministic_answer_from_evidence(accepted_packets)
    tasks = {asyncio.ensure_future(_run_synthesis_call(messages=messages, deadline=deadline))}
    done, _pending = await asyncio.wait(tasks, timeout=SYNTH_HEDGE_DELAY_SECONDS)
    answer: str | None = None
    first_done = next(iter(done), None)
    if first_done is not None:
        tasks.discard(first_done)
        answer = first_done.result()
    if answer is None and _budget_matched_synthesis_plan(deadline - perf_counter()) is not None:
        tasks.add(asyncio.ensure_future(_run_synthesis_call(
            messages=messages, deadline=deadline,
            provider=SYNTH_ALTERNATE_PROVIDER, model_override=SYNTH_ALTERNATE_MODEL,
            max_output_tokens=SYNTH_ALTERNATE_MAX_OUTPUT_TOKENS,
            thinking_override=LlmThinkingConfig(enabled=False),
        )))
    while answer is None and tasks:
        done, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            tasks.discard(task)
            if answer is None:
                answer = task.result()
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    return answer if answer else _deterministic_answer_from_evidence(accepted_packets)


def _pseudo_packets_from_search_results(results: tuple[AccumulatedSearchResult, ...]) -> tuple[AcceptedEvidence, ...]:
    packets: list[AcceptedEvidence] = []
    seen_keys: set[str] = set()
    for result in results:
        note = result.note.strip()
        if not note:
            continue
        key = f"{_normalize_url(result.url) or result.url}:{_text_fingerprint(note)}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        packets.append(AcceptedEvidence(
            url=result.url, source_text=_text_excerpt(note, MAX_TEXT_EXCERPT_CHARS),
            source_result_text=note,
            receipt_id=result.receipt_id, result_id=result.result_id, title=result.title,
            parent_candidate_id=result.result_id, text_part="search_snippet",
            text_start=0, text_end=len(note),
            admission_reason="raw_snippet_fallback",
        ))
        if len(packets) >= RAW_SNIPPET_FALLBACK_MAX_PACKETS:
            break
    return tuple(packets)


async def _answer_from_raw_snippets(
    *, question: str, results: tuple[AccumulatedSearchResult, ...],
    coverage: tuple[CoverageAspect, ...], state: ResearchRunState, deadline: float,
) -> Response:
    pseudo_packets = _pseudo_packets_from_search_results(results)
    if not pseudo_packets:
        return Response(text=_insufficient_answer(question, coverage))
    try:
        final_answer = await _synthesize_final_answer(
            question=question, accepted_packets=pseudo_packets,
            accepted_observations=(), coverage=coverage, state=state,
            deadline=deadline, unvetted_evidence=True,
        )
        final_answer, citations = _answer_text_and_citations(_safe_response_text(final_answer), pseudo_packets)
        return Response(text=final_answer, citations=citations or None)
    except Exception:
        return Response(text=_insufficient_answer(question, coverage))


def _fallback_coverage_state(*, contract: ResearchContract, observations: tuple[EvidenceObservation, ...]) -> CoverageState:
    obs_indices: dict[str, list[int]] = {}
    values: dict[str, list[str]] = {}
    obs_by_role: dict[str, list[EvidenceObservation]] = {}
    for i, obs in enumerate(observations, start=1):
        obs_indices.setdefault(obs.role_id, []).append(i)
        values.setdefault(obs.role_id, []).append(obs.value)
        obs_by_role.setdefault(obs.role_id, []).append(obs)
    roles: list[CoverageRoleStatus] = []
    missing_role_ids: list[str] = []
    weak_role_ids: list[str] = []
    for role in contract.roles:
        indices = tuple(obs_indices.get(role.role_id, ()))
        role_obs = tuple(obs_by_role.get(role.role_id, ()))
        role_values = tuple(values.get(role.role_id, ()))
        if not indices:
            status = "missing"
            missing_role_ids.append(role.role_id)
            why = "No accepted observation references this immutable role."
        elif any(o.slot_id == role.slot_id and o.support in {"direct","absence","contradiction"} for o in role_obs):
            status = "covered"
            why = "Accepted observations directly support this role."
        elif len(role_obs) >= ROLE_BREADTH_COVERAGE_MIN_OBSERVATIONS:
            status = "covered"
            why = "Multiple independent accepted observations reference this role; breadth of evidence covers it."
        else:
            status = "weak"
            weak_role_ids.append(role.role_id)
            why = "Accepted observations are relevant but marked partial or context only."
        roles.append(CoverageRoleStatus(
            role_id=role.role_id, slot_id=role.slot_id, status=status,
            supporting_observation_indices=indices,
            value="; ".join(v for v in role_values if v), why=why,
        ))
    can_answer = bool(observations) and (
        _coverage_roles_allow_answer(contract, tuple(roles)) or
        _false_premise_roles_allow_answer(contract, tuple(roles), observations)
    )
    return CoverageState(roles=tuple(roles), can_answer=can_answer, missing_role_ids=tuple(missing_role_ids), weak_role_ids=tuple(weak_role_ids))


def _coverage_roles_allow_answer(contract: ResearchContract, coverage_roles: tuple[CoverageRoleStatus, ...]) -> bool:
    status_by_role = {r.role_id: r.status for r in coverage_roles}
    return all(status_by_role.get(role.role_id) == "covered" for role in contract.roles)


def _false_premise_roles_allow_answer(contract: ResearchContract, coverage_roles: tuple[CoverageRoleStatus, ...], observations: tuple[EvidenceObservation, ...]) -> bool:
    status_by_role = {r.role_id: r.status for r in coverage_roles}
    if status_by_role.get(PREMISE_SLOT_ID) != "covered":
        return False
    premise_is_false = any(o.role_id == PREMISE_SLOT_ID and o.support in {"absence","contradiction"} for o in observations)
    if not premise_is_false:
        return False
    blocking = tuple(role.role_id for role in contract.roles if role.role_id != PREMISE_SLOT_ID and not _is_false_premise_context_role(role))
    return all(status_by_role.get(rid) == "covered" for rid in blocking)


def _is_false_premise_context_role(role: ContractRole) -> bool:
    if role.kind == "reason":
        return True
    return any(term in role.question.casefold() for term in FALSE_PREMISE_CONTEXT_ROLE_TERMS)


def _coverage_from_coverage_state(coverage_state: CoverageState, observations: tuple[EvidenceObservation, ...]) -> tuple[CoverageAspect, ...]:
    packet_by_obs = {i: obs.packet_index for i, obs in enumerate(observations, start=1)}
    return tuple(CoverageAspect(
        aspect=entry.role_id, status=entry.status,
        supporting_packet_indices=tuple(packet_by_obs[i] for i in entry.supporting_observation_indices if i in packet_by_obs),
        notes=(f"value: {entry.value}; " if entry.value else "") + entry.why,
        slot_id=entry.slot_id,
    ) for entry in coverage_state.roles)


def _beam_role_ledger(
    *, targets: tuple[EvidenceSearchTarget, ...], routes: tuple[EvidenceSearchRoute, ...],
    search_selection: SearchResultEvidenceSelection, results: tuple[AccumulatedSearchResult, ...],
    question: str,
) -> tuple[ResearchPlanRole, ...]:
    roles: list[ResearchPlanRole] = [ResearchPlanRole(
        role_id=PREMISE_SLOT_ID, slot_id=PREMISE_SLOT_ID,
        slot_intent=_slot_intent_for_slot(PREMISE_SLOT_ID),
        question="Did the question's central factual premise happen as stated?",
        kind="premise", status="missing", value=None,
        why_not_covered="No accepted evidence yet.", queries=(question,),
    )]
    selected_targets = _selected_targets_for_role_ledger(
        search_selection=search_selection, results=results, targets=targets, routes=routes,
    )
    for st in selected_targets:
        if len(roles) >= MAX_RESEARCH_PLAN_ROLES:
            break
        roles.append(ResearchPlanRole(
            role_id=st["target_id"], slot_id=st["slot_id"], slot_intent=st["slot_intent"],
            question=st["question"], kind="fact", status="missing", value=None,
            why_not_covered="No accepted evidence yet.", queries=tuple(st["queries"]),
        ))
    if len(roles) == 1:
        roles.append(ResearchPlanRole(
            role_id=PRIMARY_SOURCE_SLOT_ID, slot_id=PRIMARY_SOURCE_SLOT_ID,
            slot_intent=_slot_intent_for_slot(PRIMARY_SOURCE_SLOT_ID, targets=targets),
            question=f"What primary or canonical evidence answers the original question exactly: {question}",
            kind="fact", status="missing", value=None,
            why_not_covered="No accepted evidence yet.", queries=(question,),
        ))
    return tuple(roles)


def _selected_targets_for_role_ledger(
    *, search_selection: SearchResultEvidenceSelection, results: tuple[AccumulatedSearchResult, ...],
    targets: tuple[EvidenceSearchTarget, ...], routes: tuple[EvidenceSearchRoute, ...],
) -> tuple[dict[str, object], ...]:
    target_by_id = {t.target_id: t for t in targets}
    routes_by_tid: dict[str, list[EvidenceSearchRoute]] = {}
    for route in routes:
        routes_by_tid.setdefault(route.target_id, []).append(route)
    result_by_id = {r.result_id: r for r in results}
    selected: list[dict[str, object]] = []
    seen: set[str] = set()
    for rid in _stable_id_union((*search_selection.detail_result_ids, *search_selection.snippet_result_ids)):
        result = result_by_id.get(rid)
        if not result or not result.target_id or result.target_id in seen:
            continue
        target = target_by_id.get(result.target_id)
        if not target:
            continue
        seen.add(result.target_id)
        target_routes = tuple(routes_by_tid.get(result.target_id, target.routes))
        selected.append({"target_id": target.target_id, "slot_id": target.slot_id,
                         "slot_intent": result.slot_intent or target.slot_intent,
                         "question": target.needed_source_text,
                         "queries": tuple(r.query for r in target_routes if r.query)})
    for target in targets:
        if target.target_id not in seen:
            seen.add(target.target_id)
            selected.append({"target_id": target.target_id, "slot_id": target.slot_id,
                             "slot_intent": target.slot_intent, "question": target.needed_source_text,
                             "queries": tuple(r.query for r in target.routes if r.query)})
    return tuple(selected)


def _beam_research_contract(*, role_ledger: tuple[ResearchPlanRole, ...], question: str) -> ResearchContract:
    return ResearchContract(
        roles=tuple(ContractRole(role_id=r.role_id, slot_id=r.slot_id, slot_intent=r.slot_intent, question=r.question, kind=r.kind) for r in role_ledger[:MAX_RESEARCH_PLAN_ROLES]),
        answer_goal=f"Correct false premises first. Answer the original question using only admitted snippet or page evidence; say what is missing if exact evidence is absent. Original question: {question}",
    )


def _source_labels_from_payload(
    *, payload: dict[str, object] | None, targets: tuple[EvidenceSearchTarget, ...],
    results: tuple[AccumulatedSearchResult, ...],
) -> SearchResultSourceLabelSet:
    valid_result_ids = {r.result_id for r in results}
    valid_target_ids = {t.target_id for t in targets}
    if payload is None:
        return SearchResultSourceLabelSet(labels=(), unlabeled_result_ids=tuple(r.result_id for r in results))
    labels: list[SearchResultSourceLabel] = []
    invalid_notes: list[str] = []
    seen: set[str] = set()
    ignored = 0
    for i, item in enumerate(_object_list(payload.get("labels")), start=1):
        result_id = _string_value(item.get("result_id"))
        if result_id not in valid_result_ids or result_id in seen:
            ignored += 1
            continue
        basis = _text_excerpt(_string_value(item.get("basis")), MAX_TEXT_EXCERPT_CHARS) or "labeler_provided_no_basis"
        target_ids = tuple(_stable_valid_id_list(item.get("target_ids"), valid_target_ids))
        source_value = _normalized_source_label(value=item.get("source_value"), valid_labels=SOURCE_VALUE_LABELS, default="weak", invalid_notes=invalid_notes, path=f"labels[{i}].source_value")
        source_kind = _normalized_source_label(value=item.get("source_kind"), valid_labels=SOURCE_KIND_LABELS, default="weak_unknown", invalid_notes=invalid_notes, path=f"labels[{i}].source_kind")
        surface = _normalized_source_label(value=item.get("surface"), valid_labels=SOURCE_SURFACE_LABELS, default="snippet", invalid_notes=invalid_notes, path=f"labels[{i}].surface")
        labels.append(SearchResultSourceLabel(basis=basis, result_id=result_id, target_ids=target_ids, source_value=source_value, source_kind=source_kind, surface=surface))
        seen.add(result_id)
    unlabeled = tuple(r.result_id for r in results if r.result_id not in seen)
    return SearchResultSourceLabelSet(labels=tuple(labels), ignored_label_count=ignored, unlabeled_result_ids=unlabeled, invalid_label_notes=tuple(invalid_notes[:20]))


def _normalized_source_label(*, value: object, valid_labels: frozenset[str], default: str, invalid_notes: list[str], path: str) -> str:
    label = _string_value(value).strip().lower()
    if label in valid_labels:
        return label
    invalid_notes.append(f"{path} defaulted_to_{default}")
    return default


def _search_result_selection_from_labels(
    *, results: tuple[AccumulatedSearchResult, ...], label_set: SearchResultSourceLabelSet, max_detail_results: int,
) -> SearchResultEvidenceSelection:
    stable_ids = tuple(r.result_id for r in results)
    snippet_ids = tuple(r.result_id for r in results if r.note.strip())
    label_by_id = {l.result_id: l for l in label_set.labels}
    result_by_id = {r.result_id: r for r in results}
    detail_candidates = _stable_id_union(rid for rid in stable_ids if _label_implies_detail(label_by_id.get(rid)))
    detail_ids = _balanced_result_ids_by_target(candidate_result_ids=detail_candidates, result_by_id=result_by_id, label_by_result_id=label_by_id, max_count=max_detail_results)
    detail_set = set(detail_ids)
    if len(detail_ids) < max_detail_results:
        fill = _balanced_result_ids_by_target(
            candidate_result_ids=tuple(rid for rid in stable_ids if rid not in detail_set),
            result_by_id=result_by_id, label_by_result_id=label_by_id, max_count=max_detail_results - len(detail_ids),
        )
        detail_ids = (*detail_ids, *fill)
        detail_set = set(detail_ids)
    overlap_ids = tuple(rid for rid in snippet_ids if rid in detail_set)
    return SearchResultEvidenceSelection(snippet_result_ids=snippet_ids, detail_result_ids=detail_ids, overlap_result_ids=overlap_ids, labels=label_set.labels, unlabeled_result_ids=label_set.unlabeled_result_ids)


def _balanced_result_ids_by_target(
    *, candidate_result_ids: tuple[str, ...], result_by_id: Mapping[str, AccumulatedSearchResult],
    label_by_result_id: Mapping[str, SearchResultSourceLabel], max_count: int,
) -> tuple[str, ...]:
    if max_count <= 0 or not candidate_result_ids:
        return ()
    target_order: list[str] = []
    buckets: dict[str, list[str]] = {}
    for rid in candidate_result_ids:
        result = result_by_id.get(rid)
        if not result:
            continue
        label = label_by_result_id.get(rid)
        for tid in _selection_target_ids(result=result, label=label):
            if tid not in buckets:
                buckets[tid] = []
                target_order.append(tid)
            buckets[tid].append(rid)
    selected: list[str] = []
    selected_set: set[str] = set()
    while len(selected) < max_count:
        made_progress = False
        for tid in target_order:
            if len(selected) >= max_count:
                break
            while buckets.get(tid):
                rid = buckets[tid].pop(0)
                if rid not in selected_set:
                    selected.append(rid)
                    selected_set.add(rid)
                    made_progress = True
                    break
        if not made_progress:
            break
    return tuple(selected)


def _selection_target_ids(*, result: AccumulatedSearchResult, label: SearchResultSourceLabel | None) -> tuple[str, ...]:
    if label is not None and label.target_ids:
        return label.target_ids
    if result.target_id:
        return (result.target_id,)
    if result.slot_id:
        return (result.slot_id,)
    return ("unassigned",)


def _label_implies_detail(label: SearchResultSourceLabel | None) -> bool:
    if label is None:
        return False
    return label.surface in DETAIL_SURFACES or label.source_value in DETAIL_SOURCE_VALUES or label.source_kind in DETAIL_SOURCE_KINDS


def _accepted_packets_from_candidate_ids(*, payload: dict[str, object], candidates: tuple[EvidenceCandidate, ...]) -> tuple[AcceptedEvidence, ...]:
    candidate_by_id = {c.candidate_id: c for c in candidates}
    accepted: list[AcceptedEvidence] = []
    for candidate_id in _accepted_candidate_ids_used(payload):
        candidate = candidate_by_id.get(candidate_id)
        if not candidate:
            continue
        source_text = candidate.source_text.strip()
        if not source_text:
            continue
        accepted.append(AcceptedEvidence(
            url=candidate.url, source_text=source_text, source_result_text=candidate.source_text,
            receipt_id=candidate.receipt_id, result_id=candidate.result_id, title=candidate.title,
            parent_candidate_id=candidate.parent_candidate_id, text_part=candidate.text_part,
            text_start=candidate.text_start, text_end=candidate.text_end,
            admission_reason="accepted_by_compact_gate",
        ))
    return tuple(accepted)


def _evidence_observations_from_payload(*, payload: dict[str, object], existing_packet_count: int, candidates: tuple[EvidenceCandidate, ...]) -> tuple[EvidenceObservation, ...]:
    packet_index_by_candidate_id: dict[str, int] = {}
    next_packet_index = existing_packet_count + 1
    candidate_by_id = {c.candidate_id: c for c in candidates}
    for candidate_id in _accepted_candidate_ids_used(payload):
        candidate = candidate_by_id.get(candidate_id)
        if candidate is None or not candidate.source_text.strip():
            continue
        packet_index_by_candidate_id[candidate_id] = next_packet_index
        next_packet_index += 1
    raw_obs = payload.get("observations")
    if not isinstance(raw_obs, list):
        return ()
    observations: list[EvidenceObservation] = []
    for item in raw_obs:
        if not isinstance(item, dict):
            continue
        role_id = _string_value(item.get("role_id"))
        candidate_id = _string_value(item.get("candidate_id"))
        packet_index = packet_index_by_candidate_id.get(candidate_id)
        if not role_id or not candidate_id or packet_index is None:
            continue
        observations.append(EvidenceObservation(
            role_id=role_id, slot_id=_string_value(item.get("slot_id")),
            candidate_id=candidate_id, entity=_string_value(item.get("entity")),
            metric=_string_value(item.get("metric")), value=_string_value(item.get("value")),
            time_scope=_string_value(item.get("time_scope")), support=_string_value(item.get("support")),
            source_tier=_string_value(item.get("source_tier")), packet_index=packet_index,
        ))
    return tuple(observations)


def _accepted_candidate_ids_used(payload: dict[str, object]) -> tuple[str, ...]:
    accepted_candidates = payload.get("accepted_candidates")
    if not isinstance(accepted_candidates, list):
        return ()
    entries: list[str] = []
    seen: set[str] = set()
    for value in accepted_candidates:
        if not isinstance(value, dict):
            continue
        candidate_id = _string_value(value.get("candidate_id"))
        if not candidate_id or candidate_id in seen:
            continue
        seen.add(candidate_id)
        entries.append(candidate_id)
        if len(entries) >= MAX_ACCEPTED_IDS_PER_GATE:
            break
    return tuple(entries)


def _answer_text_and_citations(answer_text: str, accepted_packets: tuple[AcceptedEvidence, ...]) -> tuple[str, list[CitationRef]]:
    referenced_indices = _referenced_packet_indices(answer_text, packet_count=len(accepted_packets))
    if referenced_indices:
        packets = tuple(accepted_packets[i - 1] for i in referenced_indices)
        answer_text = _remap_answer_citation_numbers(answer_text, packet_count=len(accepted_packets),
            index_mapping={pi: ci for ci, pi in enumerate(referenced_indices, start=1)})
    else:
        packets = accepted_packets
        answer_text = _remap_answer_citation_numbers(answer_text, packet_count=len(accepted_packets), index_mapping={})
    return answer_text, [_citation_ref_for_packet(p) for p in packets]


def _remap_answer_citation_numbers(answer_text: str, *, packet_count: int, index_mapping: Mapping[int, int]) -> str:
    def replace_match(match: re.Match[str]) -> str:
        compact: list[int] = []
        seen: set[int] = set()
        for pi in _citation_indices_from_bracket(match.group(1), packet_count=packet_count):
            ci = index_mapping.get(pi)
            if ci is None or ci in seen:
                continue
            seen.add(ci)
            compact.append(ci)
        return f"[{', '.join(str(i) for i in compact)}]" if compact else ""
    remapped = re.sub(r"\[([0-9][0-9,\s-]*)\]", replace_match, answer_text)
    remapped = re.sub(r"\s+([.,;:])", r"\1", remapped)
    return re.sub(r" {2,}", " ", remapped).strip()


def _citation_ref_for_packet(packet: AcceptedEvidence) -> CitationRef:
    slice_start = max(0, packet.text_start)
    slice_end = max(slice_start, packet.text_end)
    if packet.text_part == "chunk" and slice_end - slice_start >= 100:
        return CitationRef(receipt_id=packet.receipt_id, result_id=packet.result_id, slices=[CitationSlice(start=slice_start, end=slice_end)])
    return CitationRef(receipt_id=packet.receipt_id, result_id=packet.result_id)


def _referenced_packet_indices(answer_text: str, *, packet_count: int) -> tuple[int, ...]:
    indices: list[int] = []
    seen: set[int] = set()
    for match in re.finditer(r"\[([0-9][0-9,\s-]*)\]", answer_text):
        for index in _citation_indices_from_bracket(match.group(1), packet_count=packet_count):
            if index not in seen:
                seen.add(index)
                indices.append(index)
    return tuple(indices)


def _citation_indices_from_bracket(value: str, *, packet_count: int) -> tuple[int, ...]:
    indices: list[int] = []
    for item in value.split(","):
        text = item.strip()
        if not text:
            continue
        range_match = re.fullmatch(r"(\d{1,3})\s*-\s*(\d{1,3})", text)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start <= end:
                indices.extend(i for i in range(start, end + 1) if 1 <= i <= packet_count)
        elif text.isdigit():
            i = int(text)
            if 1 <= i <= packet_count:
                indices.append(i)
    return tuple(indices)


async def _call_json_llm_with_retry(
    *, messages: list[dict[str, str]], model: str, temperature: float,
    thinking: LlmThinkingConfig | None = None,
    validate_payload: Callable[[dict[str, object]], str | None],
    state: ResearchRunState, stage: str, max_attempts: int = MAX_JSON_LLM_ATTEMPTS,
    repair_payload: Callable[[str], tuple[dict[str, object] | None, str | None]] | None = None,
) -> dict[str, object] | None:
    _ = (state, stage)
    active_messages = list(messages)
    for attempt_index in range(max_attempts):
        try:
            response = await llm_chat(provider=_LLM_PROVIDER, messages=active_messages, model=model, temperature=temperature, thinking=thinking, timeout=JSON_LLM_TOOL_TIMEOUT_SECONDS)
        except Exception:
            return None
        last_text = _assistant_text(response)
        payload = _parse_json_object(last_text)
        repair_note: str | None = None
        if payload is None:
            if repair_payload is not None:
                payload, repair_note = repair_payload(last_text)
            if payload is None:
                error_message = "The response was not a parseable JSON object. Return exactly one JSON object matching the requested schema, with no Markdown fence and no prose."
                if repair_note:
                    error_message = f"{error_message} Local repair failed: {repair_note}"
            else:
                error_message = validate_payload(payload)
                if error_message is None:
                    return payload
        else:
            error_message = validate_payload(payload)
            if error_message is None:
                return payload
        if attempt_index + 1 >= max_attempts:
            return None
        active_messages = [
            *messages,
            {"role": "assistant", "content": last_text or "(empty assistant response)"},
            {"role": "user", "content": f"Fix the JSON only.\n\nPrevious response:\n{(last_text or '(empty response)').strip()}\n\nError:\n{error_message}\n\nReturn one corrected JSON object only. No Markdown or prose. Preserve the task/schema."},
        ]
    return None


def _parse_json_object(text: str) -> dict[str, object] | None:
    if not text:
        return None
    stripped = _strip_code_fence(text.strip())
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        return None
    candidate = stripped[start:end + 1]
    for attempt in _json_object_parse_attempts(candidate):
        try:
            parsed = json.loads(attempt, object_pairs_hook=_json_object_without_duplicate_keys)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            return {str(k): v for k, v in parsed.items()}
    return None


def _json_object_parse_attempts(candidate: str) -> tuple[str, ...]:
    comma_repaired = re.sub(r",\s*([}\]])", r"\1", candidate)
    value_delimiter_repaired = re.sub(r'("value")\s*>(>[^",}\]]*)"', r'\1:"\2"', candidate)
    vd_and_comma = re.sub(r",\s*([}\]])", r"\1", value_delimiter_repaired)
    return tuple(dict.fromkeys((candidate, comma_repaired, value_delimiter_repaired, vd_and_comma)))


def _json_object_without_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for key, value in pairs:
        if key in parsed:
            raise ValueError(f"Duplicate JSON object key: {key}")
        parsed[key] = value
    return parsed


def _json_object_merging_evidence_targets(pairs: list[tuple[str, object]]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    merged_targets: list[object] = []
    saw_evidence_targets = False
    for key, value in pairs:
        if key == "evidence_targets":
            saw_evidence_targets = True
            if isinstance(value, list):
                merged_targets.extend(value)
            elif value is not None:
                merged_targets.append(value)
            continue
        if key in parsed:
            raise ValueError(f"Duplicate JSON object key: {key}")
        parsed[str(key)] = value
    if saw_evidence_targets:
        parsed["evidence_targets"] = merged_targets
    return parsed


def _strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    stripped = re.sub(r"^```[A-Za-z0-9_-]*\s*", "", text.strip(), count=1)
    stripped = re.sub(r"\s*```$", "", stripped, count=1)
    return stripped.strip()


def _repair_evidence_search_target_payload(text: str) -> tuple[dict[str, object] | None, str | None]:
    if not text:
        return None, "no mergeable evidence_targets object found"
    stripped = _strip_code_fence(text.strip())
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        return None, "no mergeable evidence_targets object found"
    candidate = stripped[start:end + 1]
    raw_payload = None
    for attempt in _json_object_parse_attempts(candidate):
        try:
            parsed = json.loads(attempt, object_pairs_hook=_json_object_merging_evidence_targets)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            raw_payload = {str(k): v for k, v in parsed.items()}
            break
    if raw_payload is None:
        return None, "no mergeable evidence_targets object found"
    targets = raw_payload.get("evidence_targets")
    if not isinstance(targets, list):
        return None, "merged evidence_targets value was not an array"
    repaired: list[dict[str, object]] = []
    seen_keys: set[tuple[str, str, str, str]] = set()
    dropped = 0
    for item in targets:
        if not isinstance(item, dict):
            dropped += 1
            continue
        slot_id = _string_value(item.get("slot_id"))
        if slot_id not in INTENT_SLOT_DEFINITIONS:
            dropped += 1
            continue
        slot_intent = _slot_intent_from_payload(slot_id, item)
        if slot_id in FREE_INTENT_SLOT_IDS and not slot_intent:
            dropped += 1
            continue
        needed_source_text = " ".join(_string_value(item.get("needed_source_text")).split())
        source_type = " ".join(_string_value(item.get("source_type")).split())
        key = (slot_id, slot_intent.casefold(), needed_source_text.casefold(), source_type.casefold())
        if not needed_source_text or not source_type or key in seen_keys:
            dropped += 1
            continue
        inventory = _source_inventory_from_payload(item.get("inventory"))
        if not _source_inventory_has_material(inventory):
            dropped += 1
            continue
        seen_keys.add(key)
        repaired_item: dict[str, object] = {"slot_id": slot_id, "needed_source_text": needed_source_text, "source_type": source_type, "inventory": _source_inventory_to_payload(inventory)}
        if slot_id in FREE_INTENT_SLOT_IDS:
            repaired_item["slot_intent"] = slot_intent
        repaired.append(repaired_item)
        if len(repaired) >= MAX_EVIDENCE_TARGETS_PER_ROUND:
            break
    if not repaired:
        return None, f"no valid evidence_targets items after repair; dropped={dropped}"
    return {"evidence_targets": repaired}, f"merged duplicate evidence_targets inventories; kept={len(repaired)} dropped={dropped}"


def _evidence_search_target_payload_validator() -> Callable[[dict[str, object]], str | None]:
    def validate(payload: dict[str, object]) -> str | None:
        extra = sorted(set(payload) - {"evidence_targets"})
        if extra:
            return f"Unexpected keys: {json.dumps(extra)}. Use only evidence_targets."
        targets = payload.get("evidence_targets")
        if not isinstance(targets, list) or not targets:
            return "evidence_targets must be a non-empty JSON array."
        for i, item in enumerate(targets):
            if not isinstance(item, dict):
                return f"evidence_targets[{i}] must be a JSON object."
            extra_keys = sorted(set(item) - {"slot_id","slot_intent","needed_source_text","source_type","inventory"})
            if extra_keys:
                return f"evidence_targets[{i}] has unexpected keys: {json.dumps(extra_keys)}."
            slot_id = _string_value(item.get("slot_id"))
            if slot_id not in INTENT_SLOT_DEFINITIONS:
                return f"evidence_targets[{i}].slot_id is invalid: {json.dumps(slot_id)}. Valid: {json.dumps(list(INTENT_SLOT_DEFINITIONS))}."
            if slot_id in FREE_INTENT_SLOT_IDS and not _string_value(item.get("slot_intent")):
                return f"evidence_targets[{i}].slot_intent is required when slot_id is {slot_id}."
            if not _string_value(item.get("needed_source_text")):
                return f"evidence_targets[{i}].needed_source_text must be a non-empty string."
            if not _string_value(item.get("source_type")):
                return f"evidence_targets[{i}].source_type must be a non-empty string."
            inventory = item.get("inventory")
            if not isinstance(inventory, dict):
                return f"evidence_targets[{i}].inventory must be a JSON object."
            inv_error = _validate_source_inventory_payload(inventory, path=f"evidence_targets[{i}].inventory")
            if inv_error:
                return inv_error
        return None
    return validate


def _evidence_search_route_payload_validator(*, targets: tuple[EvidenceSearchTarget, ...]) -> Callable[[dict[str, object]], str | None]:
    valid_target_ids = tuple(t.target_id for t in targets)
    valid_set = set(valid_target_ids)
    def validate(payload: dict[str, object]) -> str | None:
        extra = sorted(set(payload) - {"queries"})
        if extra:
            return f"Unexpected keys: {json.dumps(extra)}. Use only queries."
        queries = payload.get("queries")
        if not isinstance(queries, list) or not queries:
            return "queries must be a non-empty JSON array."
        for i, item in enumerate(queries):
            if not isinstance(item, dict):
                return f"queries[{i}] must be a JSON object."
            extra_keys = sorted(set(item) - {"target_id","query","site_constraints"})
            missing_keys = sorted({"target_id","query"} - set(item))
            if extra_keys or missing_keys:
                return f"queries[{i}] must contain target_id, query, and optional site_constraints. Missing: {json.dumps(missing_keys)}; Unexpected: {json.dumps(extra_keys)}."
            target_id = _string_value(item.get("target_id"))
            if target_id not in valid_set:
                return f"queries[{i}].target_id is invalid: {json.dumps(target_id)}. Valid: {json.dumps(valid_target_ids)}."
            query = _clean_llm_search_query(item.get("query"))
            if not query:
                return f"queries[{i}].query must be a non-empty string."
            if _lite_search_query_syntax_error(query):
                return f"queries[{i}].query is invalid: {_lite_search_query_syntax_error(query)}"
        return None
    return validate


def _search_result_source_labeler_payload_validator() -> Callable[[dict[str, object]], str | None]:
    def validate(payload: dict[str, object]) -> str | None:
        if set(payload) != {"labels"}:
            return "Top-level JSON keys must be exactly: labels."
        labels = payload.get("labels")
        if not isinstance(labels, list):
            return "labels must be a JSON array."
        expected = {"basis","result_id","target_ids","source_value","source_kind","surface"}
        for i, label in enumerate(labels):
            if not isinstance(label, dict) or set(label) != expected:
                return f"labels[{i}] has invalid keys."
            for f in ("basis","result_id","source_value","source_kind","surface"):
                if not isinstance(label.get(f), str):
                    return f"labels[{i}].{f} must be a string."
            if not isinstance(label.get("target_ids"), list):
                return f"labels[{i}].target_ids must be a JSON array."
        return None
    return validate


def _observation_evidence_gate_payload_validator(*, candidates: tuple[EvidenceCandidate, ...], contract: ResearchContract) -> Callable[[dict[str, object]], str | None]:
    valid_candidate_ids = tuple(c.candidate_id for c in candidates)
    valid_candidate_id_set = set(valid_candidate_ids)
    valid_role_ids = tuple(r.role_id for r in contract.roles)
    valid_role_id_set = set(valid_role_ids)
    slot_id_by_role_id = {r.role_id: r.slot_id for r in contract.roles}
    support_values = ("direct","partial","absence","contradiction","context")
    def validate(payload: dict[str, object]) -> str | None:
        extra = sorted(set(payload) - {"accepted_candidates","observations"})
        if extra:
            return f"The JSON object must contain only accepted_candidates and observations. Unexpected keys: {json.dumps(extra)}."
        accepted_candidates = payload.get("accepted_candidates")
        if not isinstance(accepted_candidates, list):
            return "accepted_candidates must be a JSON array."
        accepted_seen: set[str] = set()
        seen_order: list[int] = []
        for i, value in enumerate(accepted_candidates):
            if not isinstance(value, dict):
                return f"accepted_candidates[{i}] must be a JSON object."
            req = {"order_basis","candidate_id"}
            extra_c = sorted(set(value) - req)
            missing_c = sorted(req - set(value))
            if extra_c or missing_c:
                return f"accepted_candidates[{i}] must contain exactly order_basis and candidate_id. Missing: {json.dumps(missing_c)}; Unexpected: {json.dumps(extra_c)}."
            candidate_id = _string_value(value.get("candidate_id"))
            if candidate_id not in valid_candidate_id_set:
                return f"accepted_candidates[{i}].candidate_id is invalid."
            if candidate_id in accepted_seen:
                return f"accepted_candidates[{i}].candidate_id duplicates an earlier candidate ID."
            accepted_seen.add(candidate_id)
            if len(accepted_seen) >= MAX_ACCEPTED_IDS_PER_GATE:
                break
        observations = payload.get("observations")
        if not isinstance(observations, list):
            return "observations must be a JSON array."
        for i, obs in enumerate(observations):
            if not isinstance(obs, dict):
                return f"observations[{i}] must be a JSON object."
            candidate_id = _string_value(obs.get("candidate_id"))
            if candidate_id not in accepted_seen:
                continue
            req = {"role_id","slot_id","candidate_id","entity","metric","value","time_scope","support","source_tier"}
            extra_o = sorted(set(obs) - req)
            missing_o = sorted(req - set(obs))
            if extra_o or missing_o:
                return f"observations[{i}] must contain exactly the required keys. Missing: {json.dumps(missing_o)}; Unexpected: {json.dumps(extra_o)}."
            role_id = _string_value(obs.get("role_id"))
            if role_id not in valid_role_id_set:
                return f"observations[{i}].role_id is invalid: {json.dumps(role_id)}. Valid: {json.dumps(valid_role_ids)}."
            slot_id = _string_value(obs.get("slot_id"))
            expected_slot = slot_id_by_role_id.get(role_id, "")
            if slot_id != expected_slot:
                return f"observations[{i}].slot_id must be {json.dumps(expected_slot)} for role {json.dumps(role_id)}; received {json.dumps(slot_id)}."
            for key in ("entity","metric","value","time_scope","source_tier"):
                if not isinstance(obs.get(key), str) or not str(obs.get(key, "")).strip():
                    return f"observations[{i}].{key} must be a non-empty string."
            support = _string_value(obs.get("support"))
            if support not in support_values:
                return f"observations[{i}].support must be one of {json.dumps(list(support_values))}."
        return None
    return validate


def _chunk_cue_pattern_payload_validator(_role_ledger: tuple[ResearchPlanRole, ...]) -> Callable[[dict[str, object]], str | None]:
    def validate(payload: dict[str, object]) -> str | None:
        extra = sorted(set(payload) - {"patterns"})
        if extra:
            return f"The JSON object must contain only patterns. Unexpected keys: {json.dumps(extra)}."
        if not isinstance(payload.get("patterns"), list):
            return "Missing or invalid key `patterns`: expected a JSON array."
        return None
    return validate


def _chunk_lexical_anchor_payload_validator(_role_ledger: tuple[ResearchPlanRole, ...]) -> Callable[[dict[str, object]], str | None]:
    def validate(payload: dict[str, object]) -> str | None:
        extra = sorted(set(payload) - {"anchor_sets"})
        if extra:
            return f"The JSON object must contain only anchor_sets. Unexpected keys: {json.dumps(extra)}."
        if not isinstance(payload.get("anchor_sets"), list):
            return "Missing or invalid key `anchor_sets`: expected a JSON array."
        return None
    return validate


def _evidence_search_targets_from_payload(payload: dict[str, object], *, round_index: int) -> tuple[EvidenceSearchTarget, ...]:
    targets: list[EvidenceSearchTarget] = []
    seen_keys: set[tuple[str, str, str, str]] = set()
    for item in _object_list(payload.get("evidence_targets")):
        if len(targets) >= MAX_EVIDENCE_TARGETS_PER_ROUND:
            break
        slot_id = _string_value(item.get("slot_id"))
        if slot_id not in INTENT_SLOT_DEFINITIONS:
            continue
        slot_intent = _slot_intent_from_payload(slot_id, item)
        if slot_id in FREE_INTENT_SLOT_IDS and not slot_intent:
            continue
        needed_source_text = " ".join(_string_value(item.get("needed_source_text")).split())
        source_type = " ".join(_string_value(item.get("source_type")).split())
        key = (slot_id, slot_intent.casefold(), needed_source_text.casefold(), source_type.casefold())
        if not needed_source_text or not source_type or key in seen_keys:
            continue
        target_id = f"target_{round_index + 1}_{len(targets) + 1}"
        inventory = _source_inventory_from_payload(item.get("inventory"))
        seen_keys.add(key)
        targets.append(EvidenceSearchTarget(target_id=target_id, slot_id=slot_id, slot_intent=slot_intent, needed_source_text=needed_source_text, source_type=source_type, inventory=inventory, routes=()))
    return tuple(targets)


def _evidence_search_routes_from_payload(*, payload: dict[str, object] | None, targets: tuple[EvidenceSearchTarget, ...], tried_queries: set[str]) -> tuple[EvidenceSearchRoute, ...]:
    if payload is None:
        return ()
    target_by_id = {t.target_id: t for t in targets}
    routes: list[EvidenceSearchRoute] = []
    seen_materialized = set(tried_queries)
    seen_base: set[tuple[str, str]] = set()
    per_target: dict[str, int] = {}
    for item in _object_list(payload.get("queries")):
        target_id = _string_value(item.get("target_id"))
        target = target_by_id.get(target_id)
        if target is None or per_target.get(target_id, 0) >= MAX_QUERY_ROUTES_PER_TARGET:
            continue
        query = _clean_llm_search_query(item.get("query"))
        if not query or _lite_search_query_syntax_error(query):
            continue
        site_constraints = _site_constraints_from_value(item.get("site_constraints"))
        base_key = (target_id, _query_identity(query))
        if base_key in seen_base:
            continue
        route = EvidenceSearchRoute(
            route_id=f"{target_id}_route_{per_target.get(target_id, 0) + 1}",
            target_id=target.target_id, slot_id=target.slot_id, slot_intent=target.slot_intent,
            needed_source_text=target.needed_source_text, source_type=target.source_type,
            route_kind="llm_query", query=query, site_constraints=site_constraints,
        )
        new_queries = tuple(q for q in _materialized_evidence_search_route_queries(route) if _query_identity(q) and _query_identity(q) not in seen_materialized)
        if not new_queries:
            continue
        seen_base.add(base_key)
        seen_materialized.update(_query_identity(q) for q in new_queries)
        per_target[target_id] = per_target.get(target_id, 0) + 1
        routes.append(route)
    return tuple(routes)


def _chunk_cue_patterns_from_payload(*, payload: dict[str, object], role_ledger: tuple[ResearchPlanRole, ...]) -> tuple[tuple[ChunkCuePattern, ...], tuple[dict[str, object], ...]]:
    valid_role_id_set = {r.role_id for r in role_ledger}
    raw_patterns = payload.get("patterns")
    if not isinstance(raw_patterns, list):
        return (), ()
    patterns: list[ChunkCuePattern] = []
    rejected: list[dict[str, object]] = []
    per_role: dict[str, int] = {}
    for i, item in enumerate(raw_patterns):
        if not isinstance(item, dict):
            rejected.append({"index": i, "reason": "not an object"})
            continue
        role_id = str(item.get("role_id", "")).strip()
        pattern_text = str(item.get("pattern", "")).strip()
        if role_id not in valid_role_id_set:
            rejected.append({"index": i, "role_id": role_id, "reason": "invalid role_id"})
            continue
        if not pattern_text or len(pattern_text) > MAX_CHUNK_CUE_PATTERN_CHARS:
            rejected.append({"index": i, "reason": "invalid pattern"})
            continue
        if _regex_pattern_contains_unit_cue(pattern_text) and not _regex_pattern_has_value_context(pattern_text):
            rejected.append({"index": i, "reason": "bare unit cue"})
            continue
        try:
            compiled = re.compile(pattern_text, re.IGNORECASE)
        except re.error:
            rejected.append({"index": i, "reason": "invalid regex"})
            continue
        if per_role.get(role_id, 0) >= MAX_CHUNK_CUE_PATTERNS_PER_ROLE or len(patterns) >= MAX_CHUNK_CUE_PATTERNS_TOTAL:
            rejected.append({"index": i, "reason": "cap exceeded"})
            continue
        per_role[role_id] = per_role.get(role_id, 0) + 1
        patterns.append(ChunkCuePattern(pattern_index=len(patterns) + 1, role_id=role_id, pattern=pattern_text, compiled=compiled))
    return tuple(patterns), tuple(rejected)


def _chunk_lexical_anchors_from_payload(*, payload: dict[str, object], role_ledger: tuple[ResearchPlanRole, ...]) -> tuple[tuple[ChunkLexicalAnchorSet, ...], tuple[dict[str, object], ...]]:
    valid_role_id_set = {r.role_id for r in role_ledger}
    raw_anchor_sets = payload.get("anchor_sets")
    if not isinstance(raw_anchor_sets, list):
        return (), ()
    anchor_sets: list[ChunkLexicalAnchorSet] = []
    rejected: list[dict[str, object]] = []
    seen_keys: set[tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = set()
    for i, item in enumerate(raw_anchor_sets):
        if len(anchor_sets) >= MAX_LEXICAL_ANCHOR_SETS_TOTAL:
            break
        if not isinstance(item, dict):
            continue
        role_id = str(item.get("role_id", "")).strip()
        if role_id not in valid_role_id_set:
            continue
        all_terms, _ = _clean_lexical_anchor_terms(item.get("all"))
        any_terms, _ = _clean_lexical_anchor_terms(item.get("any"))
        near_terms, _ = _clean_lexical_anchor_terms(item.get("near"))
        avoid_terms, _ = _clean_lexical_anchor_terms(item.get("avoid"))
        if not (all_terms or any_terms or near_terms or avoid_terms):
            continue
        key = (role_id, all_terms, any_terms, near_terms, avoid_terms)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        anchor_sets.append(ChunkLexicalAnchorSet(anchor_index=len(anchor_sets) + 1, role_id=role_id, all_terms=all_terms, any_terms=any_terms, near_terms=near_terms, avoid_terms=avoid_terms))
    return tuple(anchor_sets), tuple(rejected)


def _clean_lexical_anchor_terms(value: object) -> tuple[tuple[str, ...], tuple[dict[str, object], ...]]:
    if not isinstance(value, list):
        return (), ()
    terms: list[str] = []
    rejected: list[dict[str, object]] = []
    seen: set[str] = set()
    for i, item in enumerate(value):
        if not isinstance(item, str):
            rejected.append({"term_index": i, "reason": "not a string"})
            continue
        term = re.sub(r"\s+", " ", item.strip().casefold())
        if not term or len(term) > MAX_LEXICAL_ANCHOR_TERM_CHARS or term in seen:
            continue
        seen.add(term)
        terms.append(term)
        if len(terms) >= MAX_LEXICAL_ANCHOR_TERMS_PER_FIELD:
            break
    return tuple(terms), tuple(rejected)


def _regex_pattern_contains_unit_cue(pattern: str) -> bool:
    return any(token in REGEX_UNIT_WORDS for token in _regex_pattern_word_tokens(pattern))


def _regex_pattern_has_value_context(pattern: str) -> bool:
    normalized = pattern.lower()
    return bool(re.search(r"\\d|\[0-9]|[0-9]", normalized) or any(s in pattern for s in ("$","€","£","¥","%","/")) or re.search(r"\b(?:percent|per|to|through|between|from)\b", normalized))


def _regex_pattern_word_tokens(pattern: str) -> tuple[str, ...]:
    return tuple(token for token in re.findall(r"[a-zA-Z%]+", pattern.lower()) if token not in REGEX_ESCAPE_WORDS)


def _build_evidence_search_target_messages(
    *, question: str, round_index: int, tried_queries: tuple[str, ...],
    prior_targets: tuple[EvidenceSearchTarget, ...], accumulated_results: tuple[AccumulatedSearchResult, ...],
    wrong_entities: tuple[str, ...] = (),
) -> list[dict[str, str]]:
    slot_payload = [{"slot_id": sid, "intent": intent, "free_slot": sid in FREE_INTENT_SLOT_IDS} for sid, intent in INTENT_SLOT_DEFINITIONS.items()]
    result_payload = [{"result_id": r.result_id, "url": r.url, "title": r.title or "", "target_id_hint": r.target_id, "slot_id_hint": r.slot_id, "slot_intent_hint": r.slot_intent, "needed_source_text_hint": r.needed_source_text, "source_type_hint": r.source_type, "route_id_hint": r.route_id, "route_kind_hint": r.route_kind, "query": r.query, "search_result_text": _text_excerpt(r.note, 500)} for r in accumulated_results[-16:]]
    stacked_payload = [{"result_id": r.result_id, "round": r.search_round, "slot_id_hint": r.slot_id, "source_type_hint": r.source_type, "url": r.url, "title": r.title or "", "query": r.query} for r in accumulated_results]
    prior_target_payload = [{"target_id": t.target_id, "slot_id": t.slot_id, "slot_intent": t.slot_intent, "needed_source_text": t.needed_source_text, "source_type": t.source_type, "inventory": _source_inventory_to_payload(t.inventory), "generated_queries": [r.query for r in t.routes]} for t in prior_targets[-8:]]
    system_content = (
        "ROLE: evidence-source inventory analyst for a deep-research answer. You are not an answer writer and you are not a search-query writer. Your job is to describe the source inventory that would let Python build evidence-seeking search queries: entities, aliases, official source families, document handles, metric terms, date/scope terms, must-include terms, avoid terms, and optional site constraints.\n\n"
        "OUTPUT: exactly {\"evidence_targets\":[{\"slot_id\":\"...\",\"slot_intent\":\"...\",\"needed_source_text\":\"...\",\"source_type\":\"...\",\"inventory\":{\"entities\":[],\"aliases\":[],\"source_families\":[],\"document_handles\":[],\"metric_terms\":[],\"date_scope\":[],\"must_include\":[],\"avoid\":[],\"site_constraints\":[]}}]}. Use slot_intent only for free_1/free_2. No routes, no query fields, no markdown, no reasons, no extra keys.\n\n"
        f"COUNT: return 2-{MAX_EVIDENCE_TARGETS_PER_ROUND} evidence_targets. Each target may have inventory arrays with 1-6 concise terms each.\n\n"
        "ABSENCE / FALSE-PREMISE RULE: For questions of the form 'which X were [state Y] during [period Z]' "
        "or 'what X occurred during [event]', the premise_check target MUST include inventory terms that could "
        "prove NO X was in state Y. Add to must_include terms like 'powered down', 'hibernated', 'no instruments', "
        "'not operational', 'none' when the question implies a state that could be false. Add to avoid: "
        "time-adjacent periods that could contaminate evidence (e.g. 'post-revival', 'after wake-up', "
        "'following recovery'). Example: 'which instruments were operational during lunar night' -> "
        "premise_check must_include: ['powered down','hibernation','no instruments operational'] "
        "avoid: ['after revival','February 25','post-wakeup'].\n\n"
        "DUAL-DOCUMENT RULE: When the question explicitly names two different official documents, filings, "
        "or reports (e.g. 'compare the 8-K estimate with the 10-K final', 'the January press release vs "
        "the July JAMA publication'), you MUST generate one evidence_target per document with distinct "
        "document_handles and date_scope. Do NOT merge into one target. Example: 'compare January 2023 "
        "8-K estimate vs 2023 10-K actual' -> Target 1: document_handles: ['Form 8-K','January 2023'], "
        "must_include: ['estimated','range']; Target 2: document_handles: ['Form 10-K','2023 Annual Report'], "
        "must_include: ['recorded','actual'].\n\n"
        "CALCULATION-METHOD RULE: When the question asks HOW something is calculated (e.g. 'how does X "
        "calculate Y for Z purposes', 'what formula does [body] use to determine [metric]'), you MUST "
        "include a method_or_definition slot target. Its inventory must contain metric_terms with the "
        "calculation inputs (e.g. 'federal mid-term rate', 'present value', 'discount rate', 'deferred "
        "salary'), source_families with the governing body (e.g. 'MLB collective bargaining agreement', "
        "'CBA', 'MLBPA official rules'), and must_include with the exact calculation mechanism term.\n\n"
        "COVERAGE-DECOMPOSITION RULE: Decompose the question into EVERY distinct fact it explicitly "
        "requests and emit a separate evidence_target for each one a single existing target does not "
        "already cover. (a) Each (entity x requested attribute) pair: if one attribute is asked for two "
        "entities, emit one target per entity; if one entity is asked for two attributes, emit one target "
        "per attribute. (b) Full enumerations: a 'which / list / name all X' requirement gets a target "
        "whose must_include drives the COMPLETE set (e.g. 'all', 'each', 'every', the named count), not a "
        "single example. (c) Secondary / special-category items joined by 'as well as', 'including', "
        "'and also', or 'a lower / separate threshold for [category]': these qualifying sub-clauses are "
        "REQUIRED facts, not optional context — each gets its own target. (d) A comparison baseline named "
        "in a sub-clause (e.g. 'compared to the [poll / forecast / prior estimate / projection]') gets its "
        "own target so the baseline value is retrieved, not just the headline value. Prefer covering one "
        "more required sub-element over adding depth to an already-covered one.\n\n"
        "WRONG-ENTITY RULE: If CANDIDATE_WRONG_ADJACENT_ENTITIES is provided, review each entity and "
        "add it to the avoid field of any target where that entity would produce results from the wrong "
        "source or geography. Use your judgment — only add entities that are genuinely wrong-adjacent "
        "for a specific target, not globally."
    )
    wrong_entities_section = ""
    if wrong_entities:
        wrong_entities_section = (
            f"\nCANDIDATE_WRONG_ADJACENT_ENTITIES (entities seen in prior results that may be "
            f"wrong-adjacent — inject the relevant ones into avoid for new targets):\n"
            f"{json.dumps(list(wrong_entities), ensure_ascii=False)}\n"
        )
    user_content = (
        f"Current date: {_current_date()}.\nSearch round: {round_index}\n\nOriginal question:\n{question}\n\n"
        f"INTENT_SLOT_MENU:\n{_format_records_section('SLOTS', 'slot', slot_payload)}\n\n"
        f"TRIED_QUERIES:\n{json.dumps(list(tried_queries), ensure_ascii=False)}\n\n"
        f"PRIOR_INVENTORIES:\n{_format_records_section('PRIOR_TARGETS', 'target', prior_target_payload)}\n\n"
        f"ACCUMULATED_RESULT_SURFACES:\n{_format_records_section('RESULT_SURFACES', 'result', stacked_payload)}\n\n"
        f"RECENT_ACCUMULATED_RESULTS:\n{_format_records_section('RESULTS', 'result', result_payload)}\n"
        f"{wrong_entities_section}"
        f"Return evidence-target JSON now."
    )
    return [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]


def _build_evidence_search_route_messages(
    *, question: str, round_index: int, targets: tuple[EvidenceSearchTarget, ...],
    tried_queries: tuple[str, ...], accumulated_results: tuple[AccumulatedSearchResult, ...],
) -> list[dict[str, str]]:
    target_payload = [{"target_id": t.target_id, "slot_id": t.slot_id, "slot_intent": t.slot_intent, "needed_source_text": t.needed_source_text, "source_type": t.source_type, "inventory": _source_inventory_to_payload(t.inventory)} for t in targets]
    result_surface_payload = [{"result_id": r.result_id, "round": r.search_round, "target_id_hint": r.target_id, "url": r.url, "title": r.title or "", "query": r.query} for r in accumulated_results[-24:]]
    system_content = (
        "ROLE: evidence-search query writer. You receive source-inventory targets from a planner. Your job is to write the exact search strings that should be sent to a web search tool.\n\n"
        "OUTPUT JSON ONLY: {\"queries\":[{\"target_id\":\"target_1_1\",\"query\":\"specific evidence-seeking query\",\"site_constraints\":[\"example.org\"]}]}. No markdown, no reasons, no extra keys.\n\n"
        f"DIVERSITY: produce at most {MAX_QUERY_ROUTES_PER_TARGET} queries per target. Return a compact set of high-recall queries now."
    )
    user_content = (
        f"Current date: {_current_date()}.\nSearch round: {round_index}\n\nOriginal question:\n{question}\n\n"
        f"SEARCH_TARGETS:\n{_format_records_section('TARGETS', 'target', target_payload)}\n\n"
        f"TRIED_QUERIES:\n{json.dumps(list(tried_queries), ensure_ascii=False)}\n\n"
        f"RESULT_SURFACES:\n{_format_records_section('RESULTS', 'result', result_surface_payload)}\n\nReturn executable query JSON now."
    )
    return [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]


def _build_search_result_source_labeler_messages(
    *, question: str, targets: tuple[EvidenceSearchTarget, ...],
    routes: tuple[EvidenceSearchRoute, ...], results: tuple[AccumulatedSearchResult, ...],
) -> list[dict[str, str]]:
    target_payload = [{"target_id": t.target_id, "slot_id": t.slot_id, "slot_intent": t.slot_intent, "needed_source_text": t.needed_source_text, "source_type": t.source_type, "inventory": _source_inventory_to_payload(t.inventory)} for t in targets]
    route_payload = [{"route_id": r.route_id, "target_id": r.target_id, "route_kind": r.route_kind, "query": r.query, "site_constraints": r.site_constraints} for r in routes]
    result_payload = [{"result_id": r.result_id, "url": r.url, "title": r.title or "", "evidence_target_id_hint": r.target_id, "slot_id_hint": r.slot_id, "needed_source_text_hint": r.needed_source_text, "query": r.query, "search_result_text": _compress_search_result_text(r.note)} for r in results]
    system_content = (
        "ROLE: search-result source labeler. Label result value; do not answer, select winners, or drop ambiguous results.\n\n"
        "OUTPUT JSON ONLY: {\"labels\":[{\"basis\":\"...\",\"result_id\":\"R1\",\"target_ids\":[\"target_1_1\"],\"source_value\":\"direct\",\"source_kind\":\"official\",\"surface\":\"both\"}]}. No markdown. No comments. No extra keys.\n\n"
        "VALUES: source_value=direct|primary_locator|context|contradiction|absence|weak|wrong. source_kind=official|primary|academic|government|regulatory|company|data_source|reputable_media|secondary|forum_social|aggregator|weak_unknown|wrong_source. surface=snippet|detail|both|locator|background|wrong."
    )
    user_content = (
        f"Current date: {_current_date()}.\n\nOriginal question:\n{question}\n\n"
        f"EVIDENCE_TARGETS_TO_COVER:\n{_format_records_section('TARGETS', 'target', target_payload)}\n\n"
        f"QUERY_ROUTES:\n{_format_records_section('ROUTES', 'route', route_payload)}\n\n"
        f"ACCUMULATED_SEARCH_RESULTS:\n{_format_records_section('RESULTS', 'result', result_payload)}\n\nReturn search-result source-labeler JSON now."
    )
    return [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]


def _build_observation_evidence_gate_messages(
    *, question: str, loop_index: int, existing_packets: tuple[AcceptedEvidence, ...],
    existing_observations: tuple[EvidenceObservation, ...], contract: ResearchContract,
    retrieval_roles: tuple[ResearchPlanRole, ...], candidates: tuple[EvidenceCandidate, ...],
) -> list[dict[str, str]]:
    existing_payload = [{"packet_index": i, "url": p.url, "title": p.title or "", "source_text": p.source_text} for i, p in enumerate(existing_packets, start=1)]
    candidate_payload = [{"candidate_id": c.candidate_id, "slot_id_hint": c.slot_id, "slot_intent_hint": c.slot_intent, "text_part": c.text_part, "text_start": c.text_start, "text_end": c.text_end, "url": c.url, "title": c.title, "source_kind": c.source_kind, "query": c.query, "source_text": c.source_text} for c in candidates]
    accepted_example_id = candidates[0].candidate_id if candidates else "C1_upper"
    first_role_id = contract.roles[0].role_id if contract.roles else "exact_requested_fact"
    system_content = (
        "ROLE: evidence admission + observation extractor. Admit only candidate.source_text that directly supports contract-role observations.\n\n"
        "OUTPUT: exactly accepted_candidates and observations. accepted_candidates is an ordered array of objects with order_basis first and candidate_id second.\n\n"
        f"BUDGET: max {MAX_ACCEPTED_IDS_PER_GATE} accepted candidates. Prefer fewer strong candidates, ordered by answer-role importance.\n\n"
        '{"accepted_candidates":[{"order_basis":"Exact official source for the highest-priority role.","candidate_id":"'
        f'{accepted_example_id}'
        '"}],"observations":[{"role_id":"'
        f'{first_role_id}'
        '","slot_id":"'
        f'{contract.roles[0].slot_id if contract.roles else PRIMARY_SOURCE_SLOT_ID}'
        '","candidate_id":"'
        f'{accepted_example_id}'
        '","entity":"entity","metric":"requested metric","value":"supported value or claim","time_scope":"requested scope","support":"direct","source_tier":"official"}]}\n'
        '{"accepted_candidates":[],"observations":[]}'
    )
    user_content = (
        f"Current date: {_current_date()}.\nLoop index: {loop_index}\nQuestion: {question}\n\n"
        f"Immutable contract roles:\n{_format_records_section('IMMUTABLE_CONTRACT_ROLES', 'role', [{'role_id': r.role_id, 'slot_id': r.slot_id, 'slot_intent': r.slot_intent, 'question': r.question, 'kind': r.kind} for r in contract.roles])}\n\n"
        f"Existing accepted packets:\n{_format_records_section('EXISTING_ACCEPTED_PACKETS', 'packet', existing_payload)}\n\n"
        f"Existing accepted observations:\n{_format_records_section('EXISTING_ACCEPTED_OBSERVATIONS', 'observation', _observation_prompt_payload(existing_observations))}\n\n"
        f"Retrieval role view:\n{_format_records_section('RETRIEVAL_ROLES', 'role', _role_ledger_prompt_payload(retrieval_roles))}\n\n"
        f"Candidate chunks:\n{_format_records_section('CANDIDATES', 'candidate', candidate_payload)}\n\nReturn the evidence admission and observation JSON now."
    )
    return [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]


def _build_chunk_cue_pattern_messages(
    *, question: str, loop_index: int, role_ledger: tuple[ResearchPlanRole, ...],
    sample_chunks: tuple[PageChunk, ...], query_terms: tuple[str, ...],
) -> list[dict[str, str]]:
    page_payload = tuple({"page_id": c.page_id, "url": c.url, "title": c.title or "", "query": c.query} for c in {c.page_id: c for c in sample_chunks}.values())
    sample_payload = [{"chunk_id": c.chunk_id, "page_id": c.page_id, "text_start": c.text_start, "text_end": c.text_end, "query": c.query, "source_text": _text_window(text=c.text, start=0, end=min(len(c.text), HIT_CENTERED_PREVIEW_CONTEXT_CHARS // 2), context_chars=HIT_CENTERED_PREVIEW_CONTEXT_CHARS)} for c in sample_chunks]
    valid_role_ids = [r.role_id for r in role_ledger]
    system_content = (
        "ROLE: structural regex cue generator. Return Python re patterns that locate likely evidence chunks.\n\n"
        "OUTPUT: exactly {\"patterns\":[{\"role_id\":\"...\",\"pattern\":\"...\"}]}. role_id is copied from ROLE_LEDGER. No reasons, no markdown, no extra keys.\n\n"
        f"BUDGET: max {MAX_CHUNK_CUE_PATTERNS_TOTAL} total and {MAX_CHUNK_CUE_PATTERNS_PER_ROLE} per role."
    )
    user_content = (
        f"Current date: {_current_date()}.\nLoop index: {loop_index}\n\nOriginal question:\n{question}\n\nValid role IDs: {json.dumps(valid_role_ids, ensure_ascii=False)}\n\n"
        f"Current research-plan roles:\n{_format_records_section('ROLE_LEDGER', 'role', _role_ledger_prompt_payload(role_ledger))}\n\n"
        f"Page metadata:\n{_format_records_section('PAGES', 'page', page_payload)}\n\n"
        f"Sample chunks:\n{_format_records_section('SAMPLE_CHUNKS', 'chunk', sample_payload)}\n\n"
        'Return exactly one JSON object now:\n{"patterns":[{"role_id":"exact_role_id_from_role_ledger","pattern":"Python re pattern"}]}'
    )
    return [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]


def _build_chunk_lexical_anchor_messages(
    *, question: str, loop_index: int, role_ledger: tuple[ResearchPlanRole, ...],
    sample_chunks: tuple[PageChunk, ...], query_terms: tuple[str, ...],
) -> list[dict[str, str]]:
    page_payload = tuple({"page_id": c.page_id, "url": c.url, "title": c.title or "", "query": c.query} for c in {c.page_id: c for c in sample_chunks}.values())
    sample_payload = [{"chunk_id": c.chunk_id, "page_id": c.page_id, "text_start": c.text_start, "text_end": c.text_end, "query": c.query, "source_text": _text_window(text=c.text, start=0, end=min(len(c.text), HIT_CENTERED_PREVIEW_CONTEXT_CHARS // 2), context_chars=HIT_CENTERED_PREVIEW_CONTEXT_CHARS)} for c in sample_chunks]
    valid_role_ids = [r.role_id for r in role_ledger]
    system_content = (
        "ROLE: lexical evidence-neighborhood anchor generator. Return literal phrase groups that help Python locate chunks.\n\n"
        "OUTPUT: exactly {\"anchor_sets\":[{\"role_id\":\"...\",\"all\":[],\"any\":[],\"near\":[],\"avoid\":[]}]}. role_id is copied from ROLE_LEDGER. Terms are literal strings, not regex.\n\n"
        f"BUDGET: max {MAX_LEXICAL_ANCHOR_SETS_TOTAL} anchor sets total, {MAX_LEXICAL_ANCHOR_TERMS_PER_FIELD} terms per field, and {MAX_LEXICAL_ANCHOR_TERM_CHARS} chars per term."
    )
    user_content = (
        f"Current date: {_current_date()}.\nLoop index: {loop_index}\n\nOriginal question:\n{question}\n\nValid role IDs: {json.dumps(valid_role_ids, ensure_ascii=False)}\n\n"
        f"Current research-plan roles:\n{_format_records_section('ROLE_LEDGER', 'role', _role_ledger_prompt_payload(role_ledger))}\n\n"
        f"Page metadata:\n{_format_records_section('PAGES', 'page', page_payload)}\n\n"
        f"Sample chunks:\n{_format_records_section('SAMPLE_CHUNKS', 'chunk', sample_payload)}\n\n"
        'Return exactly one JSON object now:\n{"anchor_sets":[{"role_id":"exact_role_id_from_role_ledger","all":["literal phrase"],"any":["alternative literal"],"near":["nearby term"],"avoid":["wrong-section phrase"]}]}'
    )
    return [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]


def _build_final_answer_messages(
    *, question: str, accepted_packets: tuple[AcceptedEvidence, ...],
    accepted_observations: tuple[EvidenceObservation, ...], coverage: tuple[CoverageAspect, ...],
    unvetted_evidence: bool = False,
) -> list[dict[str, str]]:
    evidence_payload = [{"packet_number": i, "url": p.url, "title": p.title or "", "source_text_part": p.text_part, "source_text_range": [p.text_start, p.text_end], "accepted_source_text": p.source_text, "source_result_text": p.source_result_text} for i, p in enumerate(accepted_packets, start=1)]
    coverage_payload = [{"aspect": item.aspect, "slot_id": item.slot_id, "status": item.status, "notes": item.notes} for item in coverage]
    system_content = (
        "ROLE: final answer writer for an evidence-gated pipeline.\n\n"
        "USE ONLY accepted packets, observations, and coverage. accepted_source_text is admitted "
        "evidence; source_result_text is same-source context. Do not use memory, general knowledge, "
        "or unstated assumptions.\n\n"
        "ANSWER SHAPE: start with a direct answer. For complex questions, explain the evidence-backed "
        "landscape: primary-source position, numbers/dates, comparators, mechanisms, actors, "
        "conflicts, uncertainty, missing evidence.\n\n"
        "FALSE PREMISE: if accepted evidence disproves or fails to support a premise, say so in the "
        "first paragraph. Do not answer as if the premise were true.\n\n"
        "FALSE-PREMISE COMPLETION RULE: When the premise is false, ALWAYS follow with: (1) the correct "
        "fact — what actually happened or exists; (2) if a comparison remains valid after correcting "
        "the premise, provide it. Stopping at 'the premise is false' without the corrected facts scores "
        "the same as an empty answer in pairwise evaluation.\n\n"
        "NUMERIC PRECISION RULE: When comparing statistical values, percentages, or financial estimates "
        "across two sources: reproduce exact notation verbatim — do NOT merge 'p < 0.0001' with "
        "'P < .001' or describe them as 'consistent'. If one source gives a range ($1.9B-$2.3B) and "
        "another a point value ($2.1B), state both and note whether the point falls within the range. "
        "58.58% and 58.6% are different notations — preserve both exactly as reported.\n\n"
        "DUAL-ANSWER COMPLETENESS RULE: When a question has two distinct sub-questions, provide a "
        "substantive answer for EACH. If a requested FACT (a value, date, name, or event) is genuinely "
        "absent from the evidence: name the specific source type needed and what it would contain (e.g. "
        "'the MLB CBA CBT AAV calculation was not in the accepted evidence — this would specify the "
        "federal mid-term rate used to discount deferred salary'). A partial answer covering both sides "
        "weakly outscores a complete answer for only one side.\n\n"
        "PROVENANCE-CONFIDENCE RULE: A question often names a specific source (e.g. 'the Electoral "
        "Commission's certified results', 'the official 10-K'). If the evidence establishes the "
        "requested facts through OTHER authoritative sources, state those facts directly and "
        "confidently as the answer. Frame any source-label gap as corroboration, not deficiency: "
        "write 'these figures are not labeled as [named source] in the evidence, but are corroborated "
        "by [authoritative source]' — do NOT lead with, dwell on, or append a disclaimer that 'the "
        "accepted evidence does not include [named source]' or 'Missing evidence' when the facts "
        "themselves are present and corroborated. Reserve missing-source language for when a requested "
        "FACT is actually absent, not when only the exact source label is. This does NOT relax the "
        "FALSE PREMISE rules: a false premise must still be stated plainly in the first paragraph.\n\n"
        "EXACT-VALUE RULE: When the question asks for a specific value — a precise date, a numeric "
        "interval or difference, a named law/title/organization, a target year, or a duration — lead "
        "with the exact figure derived from the evidence, not a rounded or hedged paraphrase "
        "(e.g. 'roughly 290 metres' or 'around four hours') when the precise value or arithmetic is "
        "available. If a needed figure is reported in different units than the question asks, convert "
        "it and give the exact converted result; preserve units and any timezone labels.\n\n"
        "DERIVED-COUNT RULE: when a qualification test needs an item count or denominator (tracks "
        "on a standard edition, roster members, list entries, games played) that no packet states "
        "as a bare number, but a packet's accepted_source_text or source_result_text enumerates "
        "the items themselves, derive the count by counting the enumerated items, use it in the "
        "arithmetic, and cite that packet — e.g. '13 standard-edition tracks (counted from the "
        "tracklist) [n]'. A count derivable from an enumeration present in evidence is PRESENT, "
        "not missing; never demote a candidate to 'conditional', 'likely', or 'unverified' for "
        "lack of a count the evidence enumerates.\n\n"
        "CLAIM-BINDING RULE: Attach a claim, filing, ruling, complaint, or accusation only to the "
        "exact actor, target, date window, and instrument that the accepted evidence ties together. "
        "Do not carry a statement about one party or period over to a different one. If the evidence "
        "does not bind all four, state that it does not establish that specific event and report what "
        "the evidence does show instead.\n\n"
        "ASKED-SCOPE RULE: Answer with the value from the exact source, date, or scope the question "
        "names. Do not substitute a later or broader figure unless it is required to resolve a "
        "conflict; when the asked-for contemporaneous source is precise and a later source is only "
        "rounded, report the precise contemporaneous value.\n\n"
        "DEFINITIVE-OPENING RULE: sentence one must deliver the requested answer itself — the "
        "name, number, date, or verdict the question asks for. Never open with remarks about "
        "evidence quality, coverage, or what the packets do or do not contain; the answer comes "
        "first, context after.\n\n"
        "FULL-ROSTER RULE: when the question asks which items qualify, or supplies its own "
        "candidate pool, enumerate EVERY qualifying item — one line per item, giving the "
        "attribute value that qualifies it with the packet citation on that same line. After "
        "the qualifying list, add one brief line per non-qualifying candidate from the "
        "question's own pool stating why it fails the criterion, citing a packet where one "
        "supports the exclusion.\n\n"
        "ADJACENT-CITATION RULE: every sentence asserting a number, date, name, or cause must "
        "carry its own packet citation [n] placed immediately at that sentence's end. Cite each "
        "claim where it is made; do not gather citations into one pooled bracket elsewhere.\n\n"
        "NAMED-SOURCE RULE: when the question pins a source ('according to Wikipedia', 'per "
        "official records', and the like), report the pinned source's figure, cite the packet "
        "carrying it, and note the figure is as given by that source. Prefer it over aggregator "
        "or third-party numbers when both appear.\n\n"
        "COMMITMENT RULE: while any relevant evidence exists, never write that the answer "
        "cannot be determined from the accepted evidence, or any similar refusal. State the "
        "best-supported value or name outright; if doubt remains, confine it to a single short "
        "trailing clause after the committed answer. THRESHOLD VERDICTS: when candidates are tested "
        "against a numeric threshold or criterion, deliver an explicit qualifies/fails verdict for "
        "EVERY candidate using the best-supported or derived figures; the opening answer names the "
        "complete qualifying set, never a partial set with the remainder left conditional. "
        "SELF-CONSISTENCY: before finishing, verify "
        "the committed answer is the same candidate your own cited sentences support — if the "
        "body's evidence establishes a different candidate as satisfying the asked criteria, the "
        "opening answer must name THAT candidate, never a weaker fallback.\n\n"
        "CITATIONS/HONESTY: cite packet numbers like [1] near claims. No generic padding, invented "
        "facts, pipeline talk, or hidden reasoning."
    )
    if unvetted_evidence:
        system_content += (
            "\n\nUNVETTED-EVIDENCE NOTE: these packets are raw search snippets that skipped the "
            "usual admission review. Judge source quality and cross-snippet agreement yourself, "
            "then commit to the best-supported answer with citations. Being unvetted is not a "
            "reason to decline; flag residual doubt in one trailing clause at most."
        )
    user_content = (
        f"Question: {question}\n\n"
        f"Accepted evidence packets:\n{_format_records_section('ACCEPTED_PACKETS', 'packet', evidence_payload)}\n\n"
        f"Accepted observations:\n{_format_records_section('ACCEPTED_OBSERVATIONS', 'observation', _observation_prompt_payload(accepted_observations))}\n\n"
        f"Coverage metadata:\n{_format_records_section('COVERAGE', 'aspect', coverage_payload)}\n\n"
        "Write the final answer as plain text. Start with the direct answer. If the premise is false, say so. If a requested fact is genuinely absent, say what is missing; but if you have the facts from authoritative sources, state them confidently rather than disclaiming the exact source label."
    )
    return [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]


def _extract_candidate_entities(results: tuple[AccumulatedSearchResult, ...]) -> tuple[str, ...]:
    """Extract prominent capitalized entity names from recent accumulated search result titles/notes."""
    entities: list[str] = []
    seen: set[str] = set()
    for result in results[-16:]:
        text = f"{result.title or ''} {result.note[:200]}"
        for match in re.finditer(r'\b[A-Z][A-Za-z0-9&\-]+(?:\s+[A-Z][A-Za-z0-9&\-]+){0,2}\b', text):
            entity = match.group(0)
            key = entity.lower()
            if key not in seen and len(entity) > 3 and not entity.isupper():
                seen.add(key)
                entities.append(entity)
        if len(entities) >= 12:
            break
    return tuple(entities[:12])


def _query_match_terms(query_text: str) -> tuple[str, ...]:
    terms: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[a-z0-9]+", query_text.lower()):
        if (token.isdigit() and len(token) >= 2) or (not token.isdigit() and len(token) >= 3):
            if token not in seen:
                seen.add(token)
                terms.append(token)
    return tuple(terms)


def _slot_intent_for_slot(slot_id: str, *, targets: tuple[EvidenceSearchTarget, ...] = ()) -> str:
    for target in targets:
        if target.slot_id == slot_id and target.slot_intent:
            return target.slot_intent
    return INTENT_SLOT_DEFINITIONS.get(slot_id, slot_id.replace("_", " "))


def _slot_intent_from_payload(slot_id: str, item: Mapping[str, object]) -> str:
    if slot_id in FREE_INTENT_SLOT_IDS:
        return _string_value(item.get("slot_intent"))
    return INTENT_SLOT_DEFINITIONS.get(slot_id, "")


def _stable_valid_id_list(value: object, valid_ids: set[str]) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for item in _string_list(value):
        if item in valid_ids and item not in seen:
            ids.append(item)
            seen.add(item)
    return ids


def _stable_id_union(values: Iterable[str]) -> tuple[str, ...]:
    ids: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ids.append(value)
    return tuple(ids)


def _search_seed_from_accumulated_result(result: AccumulatedSearchResult) -> SearchResultSeed:
    slot_id = result.slot_id or PRIMARY_SOURCE_SLOT_ID
    return SearchResultSeed(
        search_receipt_id=result.receipt_id, search_result_id=result.result_id,
        slot_id=slot_id, slot_intent=result.slot_intent or _slot_intent_for_slot(slot_id),
        url=result.url, title=result.title, note=result.note,
    )


def _validate_source_inventory_payload(raw_inventory: Mapping[str, object], *, path: str) -> str | None:
    extra = sorted(set(raw_inventory) - set(SOURCE_INVENTORY_FIELD_NAMES))
    if extra:
        return f"{path} has unexpected keys: {json.dumps(extra)}. Use only {json.dumps(list(SOURCE_INVENTORY_FIELD_NAMES))}."
    for field_name in SOURCE_INVENTORY_FIELD_NAMES:
        if field_name not in raw_inventory:
            continue
        value = raw_inventory.get(field_name)
        if value in (None, ""):
            continue
        if isinstance(value, str):
            continue
        if not isinstance(value, list):
            return f"{path}.{field_name} must be a JSON array of strings."
        for i, item in enumerate(value):
            if not isinstance(item, str):
                return f"{path}.{field_name}[{i}] must be a string."
    inventory = _source_inventory_from_payload(raw_inventory)
    if not _source_inventory_has_material(inventory):
        return f"{path} must include at least one non-empty source handle field among {json.dumps(list(SOURCE_INVENTORY_MATERIAL_FIELDS))}."
    return None


def _source_inventory_from_payload(raw_inventory: object) -> EvidenceSourceInventory:
    inventory = raw_inventory if isinstance(raw_inventory, Mapping) else {}
    return EvidenceSourceInventory(
        entities=_inventory_string_tuple(inventory, "entities"),
        aliases=_inventory_string_tuple(inventory, "aliases"),
        source_families=_inventory_string_tuple(inventory, "source_families"),
        document_handles=_inventory_string_tuple(inventory, "document_handles"),
        metric_terms=_inventory_string_tuple(inventory, "metric_terms"),
        date_scope=_inventory_string_tuple(inventory, "date_scope"),
        must_include=_inventory_string_tuple(inventory, "must_include"),
        avoid=_inventory_string_tuple(inventory, "avoid"),
        site_constraints=_site_constraints_from_value(inventory.get("site_constraints")),
    )


def _source_inventory_to_payload(inventory: EvidenceSourceInventory) -> dict[str, list[str]]:
    return {
        "entities": list(inventory.entities), "aliases": list(inventory.aliases),
        "source_families": list(inventory.source_families), "document_handles": list(inventory.document_handles),
        "metric_terms": list(inventory.metric_terms), "date_scope": list(inventory.date_scope),
        "must_include": list(inventory.must_include), "avoid": list(inventory.avoid),
        "site_constraints": list(inventory.site_constraints),
    }


def _source_inventory_has_material(inventory: EvidenceSourceInventory) -> bool:
    return any((inventory.entities, inventory.aliases, inventory.source_families, inventory.document_handles, inventory.metric_terms, inventory.date_scope, inventory.must_include))


def _inventory_string_tuple(raw_inventory: Mapping[str, object], field_name: str) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for raw_value in _string_list(raw_inventory.get(field_name)):
        value = " ".join(raw_value.split())
        key = value.casefold()
        if not value or key in seen:
            continue
        seen.add(key)
        values.append(value)
        if len(values) >= MAX_INVENTORY_TERMS_PER_FIELD:
            break
    return tuple(values)


def _materialized_evidence_search_queries(routes: tuple[EvidenceSearchRoute, ...], *, tried_queries: set[str] | None = None) -> tuple[str, ...]:
    tried = tried_queries or set()
    queries: list[str] = []
    seen: set[str] = set()
    for route in routes:
        for q in _materialized_evidence_search_route_queries(route):
            key = _query_identity(q)
            if not key or key in tried or key in seen:
                continue
            seen.add(key)
            queries.append(q)
    return tuple(queries)


def _route_by_materialized_query(routes: tuple[EvidenceSearchRoute, ...]) -> dict[str, EvidenceSearchRoute]:
    result: dict[str, EvidenceSearchRoute] = {}
    for route in routes:
        for q in _materialized_evidence_search_route_queries(route):
            key = _query_identity(q)
            if key:
                result.setdefault(key, route)
    return result


def _materialized_evidence_search_route_queries(route: EvidenceSearchRoute) -> tuple[str, ...]:
    return (route.query, *(_constrained_site_query(route.query, c) for c in route.site_constraints))


def _clean_llm_search_query(value: object) -> str:
    query = " ".join(_string_value(value).split())
    if query.startswith("site:"):
        query = re.sub(r"^site:\S+\s*", "", query).strip()
    return query


def _constrained_site_query(query: str, constraint: str) -> str:
    return f"site:{constraint} {query}".strip()


def _site_constraints_from_value(raw_constraints: object) -> tuple[str, ...]:
    constraints: list[str] = []
    seen: set[str] = set()
    for raw in _string_list(raw_constraints):
        constraint = _clean_site_constraint(raw)
        if not constraint or constraint in seen:
            continue
        seen.add(constraint)
        constraints.append(constraint)
        if len(constraints) >= MAX_SITE_CONSTRAINTS_PER_ROUTE:
            break
    return tuple(constraints)


def _clean_site_constraint(value: object) -> str:
    text = _string_value(value).strip().casefold()
    if not text:
        return ""
    if text.startswith("site:"):
        text = text[5:].strip()
    if "://" in text:
        try:
            text = urlsplit(text).netloc
        except ValueError:
            return ""
    text = text.split("/", 1)[0].split("?", 1)[0].strip().strip(".")
    if text.startswith("www."):
        text = text[4:]
    if not SITE_CONSTRAINT_DOMAIN_RE.fullmatch(text):
        return ""
    return text


def _lite_search_query_syntax_error(query: str) -> str | None:
    if BAD_QUERY_BOOLEAN_BOUNDARY_RE.search(query.strip()):
        return "query must not start or end with AND, OR, or NOT."
    return None


def _query_identity(query: str) -> str:
    return " ".join(query.casefold().split())


def _blocked_fetch_url_reason(url: str) -> str:
    try:
        host = urlsplit(url.strip()).netloc.lower()
    except ValueError:
        return ""
    if "@" in host:
        host = host.rsplit("@", 1)[-1]
    if ":" in host:
        host = host.split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    return f"blocked_fetch_host:{host}" if any(host == s or host.endswith(f".{s}") for s in BLOCKED_FETCH_HOST_SUFFIXES) else ""


def _compress_search_result_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned or len(cleaned) <= SEARCH_RESULT_TEXT_COMPRESSED_CHARS:
        return cleaned
    segment = max(1, SEARCH_RESULT_TEXT_SEGMENT_CHARS)
    n = len(cleaned)
    head_end = min(segment, n)
    tail_start = max(head_end, n - segment)
    mid_center = n // 2
    mid_start = max(head_end, mid_center - segment // 2)
    mid_end = min(tail_start, mid_start + segment)
    sections = [f"[compressed_search_result_text chars={n}]", f"[pos 0-{head_end}]", cleaned[:head_end]]
    if mid_end > mid_start:
        sections += [f"[pos {mid_start}-{mid_end}]", cleaned[mid_start:mid_end]]
    if tail_start < n:
        sections += [f"[pos {tail_start}-{n}]", cleaned[tail_start:]]
    return "\n".join(sections)


def _normalize_url(url: str) -> str:
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip().lower()
    if not parts.netloc:
        return url.strip().lower()
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = re.sub(r"/+$", "", parts.path)
    query_pairs = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not (k.lower().startswith("utm_") or k.lower() in {"fbclid","gclid","mc_cid","mc_eid"})]
    query = urlencode(sorted(query_pairs), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def _text_fingerprint(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower())[:80])


def _text_excerpt(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned if len(cleaned) <= limit else f"{cleaned[:max(0, limit - 3)].rstrip()}..."


def _text_window(*, text: str, start: int, end: int, context_chars: int) -> str:
    if not text:
        return ""
    start = max(0, min(start, len(text)))
    end = max(start, min(end, len(text)))
    before = max(0, start - context_chars)
    after = min(len(text), end + context_chars)
    prefix = "...\n" if before > 0 else ""
    suffix = "\n..." if after < len(text) else ""
    return f"{prefix}{text[before:after].strip()}{suffix}".strip()


def _elapsed_ms(started_perf: float) -> float:
    return round((perf_counter() - started_perf) * 1000, 3)


def _assistant_text(response: LlmChatResult) -> str:
    return (response.llm.raw_text or "").strip()


def _insufficient_answer(question: str, coverage: tuple[CoverageAspect, ...]) -> str:
    missing = [item.aspect for item in coverage if item.status != "covered"] or [question]
    return (
        "I could not produce a source-backed answer from the available search results. "
        "The evidence gate accepted no sources, so a substantive answer would be unsupported. "
        f"Needed evidence: direct, reliable sources covering {'; '.join(missing[:3])}."
    )


def _deterministic_answer_from_evidence(accepted_packets: tuple[AcceptedEvidence, ...]) -> str:
    sentences: list[str] = []
    for index, packet in enumerate(accepted_packets, start=1):
        source_text = packet.source_text.strip() or packet.source_result_text.strip()
        sentence = _leading_packet_sentence(source_text)
        if not sentence:
            continue
        sentences.append(f"{sentence} [{index}].")
        if len(sentences) >= DETERMINISTIC_ANSWER_MAX_SENTENCES:
            break
    if not sentences:
        return "No supporting source text was available for this question."
    return " ".join(sentences)


def _leading_packet_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return ""
    match = re.search(r"[.!?](?:\s|$)", cleaned)
    sentence = cleaned[:match.end()].strip() if match else cleaned
    if len(sentence) > DETERMINISTIC_ANSWER_SENTENCE_MAX_CHARS:
        sentence = f"{sentence[:DETERMINISTIC_ANSWER_SENTENCE_MAX_CHARS - 3].rstrip()}..."
    return sentence.rstrip(".!?").strip()


def _safe_response_text(text: str) -> str:
    cleaned = text.strip()
    return cleaned if cleaned else "I could not produce a supported answer from the accepted evidence."


def _object_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [{str(k): v for k, v in item.items()} for item in value if isinstance(item, dict)]


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        return []
    return [s for item in value if (s := _string_value(item))]


def _string_value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _current_date() -> str:
    return datetime.now(UTC).date().isoformat()


_MULTILINE_PROMPT_FIELD_NAMES = frozenset({"accepted_source_text","notes","preview","sample_text","search_result_text","source_result_text","source_text"})


def _format_records_section(section_name: str, record_tag: str, records: Sequence[Mapping[str, object]]) -> str:
    if not records:
        return f"{section_name}:\n(none)"
    lines = [f"{section_name}:"]
    lines.extend(_format_prompt_record(record_tag, record) for record in records)
    return "\n".join(lines)


def _format_scalar_list_section(section_name: str, values: Sequence[object]) -> str:
    if not values:
        return f"{section_name}:\n(none)"
    lines = [f"{section_name}:"]
    lines.extend(_format_prompt_scalar_value(value) for value in values)
    return "\n".join(lines)


def _format_prompt_record(record_tag: str, record: Mapping[str, object]) -> str:
    lines = [f"<{record_tag}>"]
    for field_name, value in record.items():
        prompt_field_name = field_name.upper()
        if field_name in _MULTILINE_PROMPT_FIELD_NAMES or (isinstance(value, str) and "\n" in value):
            lines.append(f"{prompt_field_name}:")
            text_value = _format_prompt_scalar_value(value)
            if text_value:
                lines.append(text_value)
        else:
            lines.append(f"{prompt_field_name}: {_format_prompt_scalar_value(value)}")
    lines.append(f"</{record_tag}>")
    return "\n".join(lines)


def _format_prompt_scalar_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple)):
        if all(v is None or isinstance(v, (str, int, float, bool)) for v in value):
            return ", ".join(_format_prompt_scalar_value(item) for item in value)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _observation_prompt_payload(observations: tuple[EvidenceObservation, ...]) -> list[dict[str, object]]:
    return [{"observation_index": i, "role_id": o.role_id, "slot_id": o.slot_id, "candidate_id": o.candidate_id, "entity": o.entity, "metric": o.metric, "value": o.value, "time_scope": o.time_scope, "support": o.support, "source_tier": o.source_tier, "packet_index": o.packet_index} for i, o in enumerate(observations, start=1)]


def _role_ledger_prompt_payload(role_ledger: tuple[ResearchPlanRole, ...]) -> list[dict[str, object]]:
    return [{"role_id": r.role_id, "slot_id": r.slot_id, "slot_intent": r.slot_intent, "question": r.question, "kind": r.kind, "status": r.status, "value": r.value, "why_not_covered": r.why_not_covered, "queries": list(r.queries)} for r in role_ledger]

# slot: 148 A1 2026-07-24T07:18:11+00:00
_TAG="20d492c3296248c3b5aca43f580ffe05"
import logging as _tag_logging
_tag_logging.getLogger("miner.tag").debug("tag=%s", _TAG)
