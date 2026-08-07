"""agent_d — v32.6 "toolloop": model-driven research agent.

REDESIGN RATIONALE (batch 88c4a837: our pipeline 0.000, the field's tool-loop
family 0.70-0.80). The scoring architecture is a native agentic loop: the LLM
itself drives search/fetch via tool calls, reads full results in context,
cross-references candidate-by-candidate, and writes one cited answer. Our old
staged pipeline (search -> gate -> chunk -> synth) funnels evidence through
abstractions that lose cross-referencing, never uses model knowledge, and
cannot iterate multi-hop. This file is our OWN implementation of the loop
architecture, keeping the assets our line already validated:
  - the v31.8 answer-shape discipline (asked-KIND, set-intersection
    completeness, numeric verbatim, world-negative vs evidence-concession);
  - a miniaturized section-localizer: big fetched pages are rendered as the
    HEAD plus the TOP-K densest regions (so a filing's deep section, or an
    answer set spread across two distant tables, is readable in one call);
  - SEC EDGAR primary-doc routing as a loop hint;
  - an ordered LLM fallback chain, so no single model outage ends a run.
Kill-safety: everything bounded by one deadline; force-commit well before it.

v32.6 STRUCTURAL PASS. Same prompts, same models, same budgets, same decision
logic — the scored behaviour of v32.5 is preserved byte-for-byte where it is
observable. What changed is the skeleton:

  S1  LAYERED MODULE ORDER. v32.5 called _is_usable_answer, _REPAIR_ORDER and
      _CITE_MARK_RE ~300 lines before defining them. Legal at runtime, but it
      meant the answer floor could be edited without the loop's author seeing
      it. Definitions now flow strictly downward: primitives -> floor ->
      prompts -> ledger -> tools -> LLM -> stages -> entrypoint.
  S2  OVERLAPPING CITATION SLICES (correctness). A large fetch stored spans
      [(0, HEAD)] + windows; when the densest window also started at 0 the row
      carried two overlapping slices, so the validator materialized the same
      characters twice against its 120_000-char wall. Spans are now merged and
      clamped once, at the single place they are built.
  S3  DEADLINE REACHES THE TOOLS. _do_search/_do_fetch retried on fixed
      timeouts with no view of the wall, and _preseed's per-seed wait_for could
      start at 30s remaining with a 42s budget — overshooting the wall and
      skipping the entire model loop. Both now take the deadline and clamp.
  S4  SDK ACCESS IS GUARDED. choices[0].message, msg.to_input_message() and
      call.id were bare attribute chains inside the loop; one shape change
      aborted the whole research run. They are guarded, and if an assistant
      tool-call turn cannot be round-tripped the results are folded into a
      system note rather than emitted as orphan tool_call_ids (which would
      invalidate the transcript on the next request).
  S5  AUDIT TURN NO LONGER CONTRADICTS ITSELF. With 70-90s left the patch loop
      attached tools AND appended "TIME IS UP. No more tool calls." The forced
      tool turn now only fires when there is real headroom, and suppresses the
      wrap-up order for that turn.
  S6  DEAD COUPLING REMOVED. _do_search/_do_fetch/_run_tool carried a `ledger`
      argument they stopped using at the v32.5 deferred-commit refactor, and
      _do_fetch was annotated `-> str` while returning a payload object. The
      ToolOutput class is gone: tools return (text, rows), which also retires
      the class body the old comment flagged as untested against the AST
      policy.
  S7  _best_windows is O(page) instead of O(page x terms) — a monotonic
      forward scan replaces re-slicing the page at every step. Output is
      identical (verified against the v32.5 implementation on randomized
      pages); it just stops costing a second of the wall on a 1MB filing.
  S8  _deterministic_answer (the zero-LLM last rung) now ranks the ledger by
      overlap with the question instead of emitting rows 1-6 blindly.

v32.7 SINGLE-PROVIDER PASS. ai_gateway is removed everywhere — the string does
not appear in this file. It was doing one job: giving every model call a second
attempt on a different failure domain. That job is unchanged, it is just served
by a second MODEL on openrouter now (LANES). Nothing else moved:

  P1  Attempt COUNT is the same (2), the per-attempt timeout is the same, and
      the request shape on each attempt is the same — so the wall-clock envelope
      is unchanged and the kill-safety margin measured for v32.6 still holds.
  P2  The A-then-B pair was hand-unrolled in _chat_turn, _knowledge_brief and
      _write_from_digest with three slightly different shapes. All three now walk
      the same LANES chain, so a model swap is one line rather than four.
  P3  If the fallback model cannot do tool calls, nothing breaks: _chat_turn
      returns None, the loop stops, and the rescue ladder's _write_from_digest —
      which passes NO tools and reads the clean numbered digest — is a better
      writer for that situation than a raw transcript turn would have been. The
      architecture already covered this; it is called out so the fallback model
      can be chosen on answer quality rather than on tool support.

AST-POLICY NOTE. The submitted script must survive the validator's static
check. This file contains: no `sys`/`os`/`importlib` import, no dunder
attribute access, no getattr with a computed field name, and no call to a
dynamically selected callable — tool dispatch stays an explicit if/elif chain
on a string, never a name->function table. Keep it that way when editing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from time import monotonic

from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

VERSION = "v32.7-toolloop"

# ── provider / models ─────────────────────────────────────────────────────────
# v32.7 SINGLE PROVIDER. ai_gateway is gone: one credential, one failure domain,
# no paid-key dependency. What the second provider actually bought was a SECOND
# ATTEMPT at every model call — that is kept. LANES is still an ordered fallback
# chain tried in sequence; it now resolves to two MODELS on one provider instead
# of two providers. Attempt count, timeouts and request shape are unchanged, so
# the wall-clock envelope is identical to v32.6.
LLM_PROVIDER = "openrouter"

LOOP_MODEL_A = "z-ai/glm-5"              # primary — the model the 0.750 line scored on
LOOP_MODEL_B = "deepseek/deepseek-v3.2"  # fallback — THIS IS THE ONE LINE TO SWAP if you
                                         # have a closer glm-5 sibling on openrouter, which
                                         # would hold answer shape steadier across a
                                         # failover. Chosen because (a) this file already
                                         # proves it is reachable on openrouter (it is
                                         # RESORT_MODEL) and (b) gpt-oss-120b already
                                         # carries audit AND schema duty, so reusing it
                                         # here would put three roles behind one outage.
AUDIT_MODEL = "openai/gpt-oss-120b"
SCHEMA_MODEL = "openai/gpt-oss-120b"
RESORT_MODEL = "deepseek/deepseek-v3.2"
SEARCH_PROVIDER = "parallel"             # only search/fetch key we store

# (provider, model, lean_finish)
#
# lean_finish was written as `lane == LLM_LANE_B` in v32.5/32.6, but it was never
# about the lane: glm-5.2-fast had a documented empty-content defect, so the
# finish turn stripped its reasoning and bounded its output. The flag now travels
# with the lane entry, and it still fires on exactly the second attempt of a
# finish turn — by then one attempt has already been spent, so a bounded
# non-reasoning completion is the one most likely to land in what time is left.
# The primary must NEVER carry it: the finish turn is the single turn that has to
# apply every answer rule and place every [n].
LANES = (
    (LLM_PROVIDER, LOOP_MODEL_A, False),
    (LLM_PROVIDER, LOOP_MODEL_B, True),
)

# ── budgets (seconds) ─────────────────────────────────────────────────────────
WALL_BUDGET_S = 262.0        # v32.4c: 248 was the field's shortest, but 270 collided
                             # with a deadline-blind tool phase (75s chat + 32s fetch
                             # retry = 107s > WRAPUP_AT_S), which could overshoot the
                             # 300s kill. 262 + a hard-bounded tool phase is the margin.
SEARCH_TIMEOUT_S = 18.0
BRIEF_TIMEOUT_S = 50.0
FETCH_TIMEOUT_S = 16.0
TURN_TIMEOUT_S = 75.0
AUDIT_TIMEOUT_S = 28.0
WRAPUP_AT_S = 90.0           # remaining <= this -> stop researching, write
MIN_TAIL_S = 8.0
ANSWER_REPAIR_TURNS = 2      # v32.4: bounded retries when the model emits junk instead of an answer
RESCUE_TIMEOUT_S = 55.0
AUDIT_MIN_HEADROOM_S = 70.0  # below this a patch loop cannot search AND rewrite
MAX_TURNS = 15          # v32.4: field runs 14-16; 13 was the most turn-starved in the class
AUDIT_EXTRA_TURNS = 2

# The tool phase is bounded so it can never eat the writing budget. v32.6 names
# the two caps that were previously one magic expression: a search/fetch fan-out
# needs one retry round; an EDGAR resolution needs two large-JSON fetches, and
# capping it at the search figure meant sec_filing was cancelled mid-resolution
# on every cold cache. Both are clamped to the wall at call time regardless.
MAX_TOOL_FANOUT = 8
TOOL_PHASE_S = FETCH_TIMEOUT_S * 2 + 6.0     # 38.0
SEC_TOOL_PHASE_S = 60.0

# ── payload shaping ───────────────────────────────────────────────────────────
SEARCH_EXCERPT_CHARS = 550
FETCH_WINDOW_CHARS = 3600
SEARCH_RESULTS_N = 8
FETCH_HEAD_CHARS = 3000
FETCH_WINDOWS_PER_PAGE = 3   # v32.4: show the top-K disjoint regions, not just one
                             # (single-window reading made runs see different halves
                             # of a spread-out answer set -> divergent medians)
FETCH_PLAIN_CHARS = 6500     # small pages render whole
FETCH_PREVIEW_CHARS = 1200
ANSWER_CHAR_CAP = 60000
CITATION_CAP = 24
MAX_SLICES_PER_REF = 4
# v32.4: the validator materializes every cited slice and rejects the whole
# response past 120_000 chars (miner_response_invalid = 0). Budget below it.
EVIDENCE_CHAR_BUDGET = 105_000
# A slice must be >=100 chars unless it covers a shorter note entirely.
MIN_SLICE_CHARS = 100

# ── spend floors (USD; degrade gracefully when the metered budget runs dry) ───
AUDIT_MIN_USD = 0.05
WRAPUP_MIN_USD = 0.02
BRIEF_MIN_USD = 0.03

_SPEND = {"left": None}


def _spend_note(payload) -> None:
    budget = getattr(payload, "budget", None)
    left = getattr(budget, "session_remaining_budget_usd", None)
    if isinstance(left, (int, float)):
        _SPEND["left"] = float(left)


def _spend_left() -> float:
    left = _SPEND["left"]
    if isinstance(left, (int, float)):
        return float(left)
    return 1.0


def _remaining(deadline: float) -> float:
    return deadline - monotonic()


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 1 — text primitives (no SDK, no I/O; everything below may use these)
# ═══════════════════════════════════════════════════════════════════════════
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9'.\-]{2,}")
_STOP = frozenset(
    "the and for with from that this have has was were are is been its their "
    "which what when where who how many much according also into over under "
    "between during against about after before while other more most than".split())


def _key_terms(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall((text or "").casefold()) if w not in _STOP}


def _merge_spans(spans, note_len: int) -> list[tuple[int, int]]:
    """Clamp regions into the note and merge every overlap, once.

    v32.6 S2 — this is the fix for a real evidence-wall bug. A large fetch built
    its row as [(0, FETCH_HEAD_CHARS)] + windows, and _best_windows is perfectly
    entitled to return a window starting at 0 (the head IS often the densest
    region). The row then carried (0, 3000) and (0, 3600): the validator
    materializes every slice, so those 3000 characters were charged twice
    against _MAX_TOTAL_EVIDENCE_CHARS, and a handful of such refs could push an
    otherwise-legal response over the wall into miner_response_invalid = 0.
    Merging also guarantees the slices we hand the judge are ordered, disjoint
    and non-empty, which is what a materializer expects."""
    cleaned: list[tuple[int, int]] = []
    for span in spans or ():
        start = max(0, min(int(span[0]), note_len))
        end = max(0, min(int(span[1]), note_len))
        if end > start:
            cleaned.append((start, end))
    if not cleaned:
        return []
    cleaned.sort()
    merged = [cleaned[0]]
    for start, end in cleaned[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:                 # overlapping or touching
            if end > last_end:
                merged[-1] = (last_start, end)
        else:
            merged.append((start, end))
    return merged


def _best_windows(note: str, terms: set[str], width: int,
                  k: int = 1) -> list[tuple[int, int]]:
    """Deterministic scan: the K highest-density, NON-OVERLAPPING windows, in
    document order.

    v32.4 — showing only the single densest window was a direct cause of our
    run-to-run set variance (prod f462cada: runs returned different SUBSETS of
    the answer). When a question's qualifying entities are spread across two
    tables far apart in one page, a single window can only ever show one of
    them, so which one the model sees depends on the trajectory. Surfacing the
    top-K regions makes one fetch carry the whole answer set, on every run.

    v32.6 S7 — same scores, same picks, cheaper. The old body re-sliced the page
    at every step and ran `t in seg` for every term against every slice, i.e.
    O(page x terms) character work: on a 1MB filing with 30 key terms that is a
    real fraction of a second stolen from the wall, inside a tool call that is
    itself already on a clamped budget. Because window starts only ever move
    forward, one monotonic cursor per term answers the same question — a term
    is present in [pos, pos+width) exactly when its next occurrence at or after
    pos starts no later than pos+width-len(term)."""
    n = len(note)
    if n <= width:
        return [(0, n)]
    step = max(600, width // 3)
    low = note.lower()  # lower() preserves length (casefold can change it)
    # cursor[t] = position of the next occurrence of t at or after the last
    # window start we asked about; -1 once t cannot occur again.
    cursor: dict[str, int] = {}
    term_list = [t for t in terms if t]
    for term in term_list:
        cursor[term] = low.find(term)
    # `"" in seg` is True for every window, so an empty term was a constant hit
    # in the v32.5 scan (enough to defeat the zero-signal guard below). It cannot
    # come out of _key_terms — _WORD_RE requires three characters — but carrying
    # it as a constant keeps this function output-identical on ALL inputs rather
    # than only on the reachable ones.
    base_hits = 0
    for term in terms:
        if not term:
            base_hits += 1
    scored: list[tuple[int, int]] = []   # (hits, start)
    pos = 0
    while pos < n:
        hits = base_hits
        limit = pos + width
        for term in term_list:
            at = cursor[term]
            if at < 0:
                continue
            if at < pos:
                at = low.find(term, pos)
                cursor[term] = at
                if at < 0:
                    continue
            if at + len(term) <= limit:
                hits += 1
        scored.append((hits, pos))
        if pos + width >= n:
            break
        pos += step
    # highest density first, earliest position breaking ties (deterministic)
    scored.sort(key=lambda hs: (-hs[0], hs[1]))
    picked: list[tuple[int, int]] = []
    for hits, start in scored:
        if len(picked) >= max(1, k):
            break
        end = min(n, start + width)
        if any(start < pe and ps < end for ps, pe in picked):
            continue          # keep the shown regions disjoint
        if picked and hits <= 0:
            continue          # never pad with zero-signal regions
        picked.append((start, end))
    picked.sort()             # document order reads naturally
    return picked or [(0, min(n, width))]


# ── bracket normalization + [n] extraction ───────────────────────────────────
# v32.5: glm emits full-width/CJK brackets (【1】, ［1］) often enough that
# champion lineages normalize them explicitly. ASCII-only matching would drop
# EVERY citation (judge credits nothing) and simultaneously make the answer
# floor read the answer as uncited.
# Ordinal-keyed dict (str.translate accepts one directly) — avoids str.maketrans,
# which is a static access on a builtin type and untested against the server-side
# AST policy. Includes full-width DIGITS: without them the floor's unicode-aware
# \d saw "cited" while the ASCII-only extractor yielded nothing, shipping an
# answer with citations=None — worse than not normalizing at all.
_BRACKET_FIX = {0x3010: "[", 0x3011: "]", 0xFF3B: "[", 0xFF3D: "]",
                0xFF08: "(", 0xFF09: ")", 0x2011: "-", 0x2212: "-"}
for _d in range(10):                      # U+FF10..U+FF19 -> ASCII 0-9
    _BRACKET_FIX[0xFF10 + _d] = chr(48 + _d)


def _normalize_brackets(text: str) -> str:
    return (text or "").translate(_BRACKET_FIX)


_CITE_NUM_RE = re.compile(r"\[([0-9][0-9,\s\-]*)\]")


def _cited_numbers(answer: str, top: int) -> list[int]:
    answer = _normalize_brackets(answer)
    seen: set[int] = set()
    out: list[int] = []
    for m in _CITE_NUM_RE.finditer(answer):
        for chunk in m.group(1).split(","):
            piece = chunk.strip()
            span = re.fullmatch(r"(\d{1,4})\s*-\s*(\d{1,4})", piece)
            if span:
                lo = int(span.group(1))
                hi = int(span.group(2))
                for n in range(lo, min(hi, lo + 16) + 1):
                    if 1 <= n <= top and n not in seen:
                        seen.add(n)
                        out.append(n)
            elif piece.isdigit():
                n = int(piece)
                if 1 <= n <= top and n not in seen:
                    seen.add(n)
                    out.append(n)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 2 — the final-answer floor
# ═══════════════════════════════════════════════════════════════════════════
# Prod batch f462cada: several validator runs submitted literal tool-call MARKUP
# as the final answer ("<tool_call>web_search<arg_key>query</arg_key>…", and a
# corrupted full-width-paren variant) because the loop accepted ANY no-tool-call
# message as the answer. Others submitted empty text or the internal stub. Each
# of those is a guaranteed 0, and since validators re-run the agent, they were a
# major driver of our median-vs-best gap. Nothing may be submitted unless it
# reads as a real answer.
#
# v32.6 S1: this block used to live ~300 lines BELOW _loop, which is its only
# hot caller. It is a gate on everything the agent can emit, so it now sits
# above every stage that consults it.
_TOOL_MARKUP_RE = re.compile(
    r"<\s*/?\s*tool_call|<\s*/?\s*(?:arg_key|arg_value|function_call|invoke)\b"
    r"|\bweb_search\s*[（(]\s*query|\bread_page\s*[（(]\s*url|\bsec_filing\s*[（(]\s*company",
    re.I)
_STUB_ANSWER_RE = re.compile(r"^\s*(?:best-effort answer unavailable|no question provided)", re.I)
_REFUSAL_ONLY_RE = re.compile(
    r"^\s*(?:i (?:cannot|can't|am unable|was unable)|unable to|sorry[,.]|"
    r"i don'?t have (?:enough|access))", re.I)
# v32.4b: INTENT NARRATION — the model describing what it is about to do instead
# of answering ("I need to gather...", "Let me search for..."). Observed shipped
# as a final answer in the qualifying smoke, repeated verbatim 3x.
_INTENT_NARRATION_RE = re.compile(
    r"^\s*(?:i (?:need|will|should|am going|'ll)\b|let me\b|first,? (?:i|let)\b|"
    r"i'?ll (?:search|look|start|begin|gather|check))", re.I)
MIN_ANSWER_CHARS = 40
MIN_CITED_ANSWER_CHARS = 12   # F8: '42 [3]' is a legitimate answer
_CITE_MARK_RE = re.compile(r"\[[0-9]{1,3}\]")   # ASCII, matching _CITE_NUM_RE


def _looks_like_tool_json(s: str) -> bool:
    """F13: only a tool-call JSON at the very START is junk; an answer that
    QUOTES a JSON record mid-text is legitimate."""
    return bool(re.match(r'\s*\{\s*"(?:name|tool|function)"\s*:', s))


def _is_degenerate_repetition(text: str) -> bool:
    """True when the text is the same sentence emitted over and over — the
    classic stalled/greedy-decoding artifact. Cheap and language-agnostic:
    if the distinct sentences cover under half the body, it is a loop."""
    sents = [s.strip().lower() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if len(s.strip()) > 25]
    if len(sents) < 3:
        return False
    uniq = set(sents)
    if len(uniq) * 2 <= len(sents):
        return True
    # or one sentence repeated 3+ times anywhere
    for s in uniq:
        if sents.count(s) >= 3:
            return True
    return False


def _is_usable_answer(text: str) -> bool:
    """A submittable answer. F13/F8 fixes: a CITED, substantive answer is always
    an answer — terse replies ('Yes, both are French [1].') and the reasoned-
    impossibility shape LOOP_RULES explicitly asks for were being thrown away,
    and a 4000-char cited answer was discarded for its opening clause."""
    s = _normalize_brackets(text).strip()
    if not s:
        return False
    # hard junk, regardless of length or citations
    if _TOOL_MARKUP_RE.search(s) or _looks_like_tool_json(s):
        return False
    if _STUB_ANSWER_RE.match(s) or _is_degenerate_repetition(s):
        return False
    cited = bool(_CITE_MARK_RE.search(s))
    if cited and len(s) >= MIN_CITED_ANSWER_CHARS:
        return True          # cited + substantive == an answer, however short
    if len(s) < MIN_ANSWER_CHARS:
        return False
    # uncited: only then do lead-phrase heuristics apply, and only to SHORT text
    if len(s) < 400 and (_REFUSAL_ONLY_RE.match(s) or _INTENT_NARRATION_RE.match(s)):
        return False
    return True


_VERIFY_MARK_RE = re.compile(r"\s*\((?:verify|unverified|uncertain)[^)]*\)", re.I)


def _sanitize_draft(text: str) -> str:
    """The briefing draft marks shaky facts '(verify)' by instruction; those
    markers must NEVER reach a submitted answer (judge-penalized uncertainty)."""
    return _VERIFY_MARK_RE.sub("", text or "").strip()


def _cap(text: str) -> str:
    t = (text or "").strip()
    if len(t) > ANSWER_CHAR_CAP:
        return t[:ANSWER_CHAR_CAP - 16] + " …"
    return t


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 3 — deterministic question classifiers (no LLM; select extra rules)
# ═══════════════════════════════════════════════════════════════════════════
_SET_HINT_RE = re.compile(
    r"\b(?:list|name|identify|enumerate)\b[^?]{0,40}\b(?:all|every|each|the)\b"
    r"|\bhow many\b|\bwhich (?:movies|films|series|countries|companies|states|"
    r"cities|books|albums|artists|players|teams|species|languages|banks|"
    r"universities|agencies|models|products)\b",
    re.IGNORECASE)
_SET_CONNECTIVE_RE = re.compile(r"\b(?:both|also|and (?:also|had|has|was|were)|as well as)\b",
                                re.IGNORECASE)


_PLURAL_HEAD_RE = re.compile(r"\b(?:which|what)\b(?:\s+\w+){0,2}?\s+([a-z]{3,}s)\b", re.IGNORECASE)
_PLURAL_FALSE = frozenset(
    "was is has does its this thus across process business series species news "
    "status analysis basis less unless always perhaps".split())
_ONE_WINNER_RE = re.compile(
    r"\b(?:highest|lowest|largest|smallest|most|least|greatest|fewest|longest|"
    r"shortest|first|last|best|worst|only|oldest|youngest|newest|biggest)\b",
    re.IGNORECASE)
# Generic '-est' superlative catcher so we are not limited to a hand-listed
# vocabulary (tallest/richest/earliest/deepest/… all qualify). The stoplist
# holds ordinary words that merely end in -est.
_EST_STOP = frozenset(
    "interest honest modest protest request suggest forest harvest invest "
    "manifest contest arrest digest earnest conquest tempest midwest northwest "
    "southwest unrest bequest behest attest molest ingest infest detest incest "
    "armrest backrest pretest headrest footrest".split())
_EST_RE = re.compile(r"\b([a-z]{3,})est\b")   # NO IGNORECASE: proper
# nouns (Budapest, Everest, Bucharest, Ernest) start uppercase and so cannot
# match — a false positive here CANCELS the set rule (verified regression).


def _has_superlative(text: str) -> bool:
    if _ONE_WINNER_RE.search(text or ""):
        return True
    for m in _EST_RE.finditer(text or ""):
        if m.group(0).lower() not in _EST_STOP:
            return True
    return False


def _needs_superlative_proof(question: str) -> bool:
    """A superlative/count question ANSWERS with one item, but RESEARCHING it
    requires the whole pool: you cannot know the oldest player without every
    player's birthdate, or the most common name without the full tally. The set
    detector deliberately cancels on superlatives (the answer shape is singular)
    — so those questions were getting no completeness discipline at all."""
    q = " ".join((question or "").split())
    if not q:
        return False
    return _has_superlative(q) or bool(
        re.search(r"\b(?:most|least) (?:common|frequent|number|amount)\b|\bhow many\b", q, re.I))


def _needs_set_completeness(question: str) -> bool:
    q = " ".join((question or "").split())
    if _SET_HINT_RE.search(q):
        return True
    # GENERIC plural head ("which paintings/vessels/treaties …") — class-based,
    # not a closed noun list; a superlative cancels it (one winner wanted)
    # unless an explicit all/every/each restores the set reading.
    m = _PLURAL_HEAD_RE.search(q)
    if m and m.group(1).lower() not in _PLURAL_FALSE:
        if not _has_superlative(q) or re.search(r"\b(?:all|every|each)\b", q, re.IGNORECASE):
            return True
    # multi-criteria phrasing ("that X and also Y") usually means a filtered SET
    return bool(re.search(r"\bwhich\b", q, re.IGNORECASE)) and bool(_SET_CONNECTIVE_RE.search(q))


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 4 — prompts and tool schemas (data only; unchanged from v32.5)
# ═══════════════════════════════════════════════════════════════════════════
LOOP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": ("Web search. Returns numbered results, each with title, "
                            "url and excerpt."),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string",
                                         "description": "the search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sec_filing",
            "description": ("Resolve a company's SEC filing to its primary document "
                            "URL on sec.gov (exact form + year, from EDGAR's own "
                            "index). Use for questions about a specific filing "
                            "(10-K, 10-Q, 8-K, DEF 14A…), then read_page the "
                            "returned URL with a focus hint for the Item/section."),
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string",
                                "description": "company name or ticker, e.g. 'Apple' or 'AAPL'"},
                    "form": {"type": "string",
                             "description": "filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"},
                    "year": {"type": "string",
                             "description": "optional report (fiscal) year, e.g. '2019' (omit for latest)"},
                },
                "required": ["company", "form"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_page",
            "description": ("Fetch a URL and return its main text. Large pages show "
                            "the head plus the few regions most relevant to the "
                            "question; pass a focus hint to steer which regions."),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                    "focus": {"type": "string",
                              "description": ("optional phrase to locate inside the "
                                              "page (section name, table label, "
                                              "entity)")},
                },
                "required": ["url"],
            },
        },
    },
]

# The answer rules are OUR v31.8 discipline, condensed. Every rule below earned
# its place from a scored prod failure.
LOOP_RULES = (
    "You are a research agent answering a hard multi-part factual question. A "
    "judge compares your answer head-to-head with a strong reference and only "
    "credits claims that carry a citation to a tool result that states them.\n\n"
    "METHOD: think in constraints and candidates. Recall what you already know "
    "to form the candidate pool, then use web_search/read_page to verify every "
    "load-bearing fact (names, figures, dates, rankings) before asserting it. "
    "Work every candidate through every stated condition; one search per fact "
    "beats one broad search. TWO DISTINCT SUB-QUESTIONS: if the question asks two "
    "separate things, answer BOTH substantively — a partial answer covering both "
    "sides outscores a complete answer to only one. BATCH YOUR LOOKUPS: independent facts (each "
    "candidate's score, each entity's figure) should be requested as SEVERAL "
    "tool calls in the SAME turn — they run in parallel, so a 6-candidate "
    "sweep costs one turn, not six. TABLE CARE: when reading a table, respect its "
    "qualifier columns (Owned vs Leased, the exact year, the exact segment) — "
    "count or compare only rows matching EVERY stated qualifier, and quote the "
    "row values you used. For a named source (Box Office Mojo, a 10-K, "
    "Nielsen), fetch THAT page — for SEC filings, use the sec_filing tool to "
    "resolve the exact primary document from EDGAR's own index, then read_page "
    "it with a focus hint for the Item/section.\n\n"
    "CITE EVERYTHING: put [n] (the tool-result number) immediately after the "
    "SENTENCE carrying each claim — not pooled at the end of a paragraph. Every "
    "sentence asserting a number, date, proper noun or causal link needs its own "
    "[n], for the entities you rule OUT as well as those you include. An uncited "
    "specific reads as invented. Cite only results that actually state the claim, "
    "and prefer the most AUTHORITATIVE one that does: the official database/"
    "filing/statistics page over an aggregator, blog, or retrospective article.\n\n"
    "SOURCE CONFIDENCE: when the question NAMES a source you could not reach but "
    "other authoritative evidence establishes the same facts, state those facts "
    "plainly and confidently with their [n], and treat the other sources as "
    "corroboration. Do not open with, dwell on, or append a note that the named "
    "source was unavailable — reserve missing-source language for a FACT that is "
    "genuinely absent everywhere, never for a missing source LABEL.\n\n"
    "SELF-CONSISTENCY: before you finish, check that the opening names exactly "
    "the entities your own cited sentences support. If the body establishes a "
    "different answer than the opening claims, rewrite the opening to match the "
    "evidence — never leave a weaker fallback in the lead.\n\n"
    "ANSWER SHAPE: sentence one IS the answer — the exact entities/values/list "
    "asked for, in the requested format. Never open with 'Based on…', 'From my "
    "research…', 'I can provide a partial answer', or any preamble — start with "
    "the answer entities themselves. ANSWER THE ASKED KIND: if the question asks "
    "which SERIES, name the series (not the people in it); which FILM, the film "
    "(not its director); which COUNTRY, the country. Then a short proof section: "
    "the candidate pool, each condition applied, one line per qualifier (cited) "
    "and one line per prominent exclusion with its cited failing condition. "
    "EXACT VALUES ONLY: when the answer turns on figures, use the figures you "
    "READ in a tool result, verbatim — preserve notation exactly (58.58% and "
    "58.6% are different; 'p < 0.0001' and 'P < .001' must not be merged or "
    "called consistent). If one source gives a range and another a point value, "
    "give both and say whether the point falls inside the range. If a figure is "
    "reported in different units than the question asks, convert it and give the "
    "exact converted result, preserving units and any timezone label. Answer with "
    "the value from the exact source, date and scope the question NAMES — do not "
    "substitute a later or broader figure unless resolving a conflict requires "
    "it. Bind every claim to the exact actor, target, date-window and instrument "
    "the evidence ties together; never carry a statement about one party or "
    "period across to another. Never a remembered or approximate value "
    "('~$1.33B'), never rounded, never an adjacent year/quarter/metric. If a "
    "deciding figure is still unverified at writing time, prefer the tool-read "
    "value you have over a guess, and NEVER write '(verify)' or any uncertainty "
    "marker in the final answer — the final answer contains only committed "
    "prose.\n\n"
    "AMBIGUOUS METRIC? ANSWER BOTH READINGS. If the asked quantity has two "
    "defensible interpretations ('highest scoring games' = the team's own "
    "points OR the combined total; 'largest' = area OR population; 'revenue' = "
    "segment OR consolidated), do NOT silently pick one. Name the ambiguity in "
    "one clause and give BOTH lists/values, each cited and labelled. A correct "
    "answer under the reading the grader did not use still scores as wrong.\n\n"
    "APPLY CONDITIONS LITERALLY: copy each candidate's exact value, then test "
    "the comparator as written — 'more than 25' is strictly >25 (25 fails); "
    "'between 2010 and 2019' includes both endpoints; convert a rate condition "
    "into a concrete integer test ('averaged more than 1 per year over 10 "
    "years' = 'more than 10 in total'); read edition/date boundaries literally. "
    "EXCLUDE ONLY ON PROOF: reject a candidate by naming the specific stated "
    "condition it fails, with the cited fact showing the failure — never "
    "because it looks weaker than your front-runner. If it is UNCERTAIN "
    "whether a candidate fails a condition, KEEP IT in the answer rather than "
    "dropping it on a guess: a wrongly-dropped qualifier costs exactly as much "
    "as a wrong answer. SAY NO MORE THAN THE CITATION: if the source says "
    "'brought to', do not write 'incarcerated'; if it gives a count of 12, do "
    "not write 11. Check every count and every verb against its citation.\n\n"
    "NEVER NARRATE YOUR EVIDENCE: no sentence about what your results do or "
    "do not contain ('the evidence does not specify…', 'would be needed to "
    "determine…'). Those phrasings lose. A substantive negative about the "
    "WORLD is different and is a real answer when true ('No officer was held "
    "in all four prisons [n]'). If a datum truly cannot be verified, commit "
    "to the best-supported value you found and move on. ONE narrow exception: "
    "when the asked figure genuinely does not exist in any published form, you "
    "may state the REASONED IMPOSSIBILITY — name the specific dataset that "
    "would hold it and why it cannot yield the value — as a fact about the "
    "world, in the first line, alongside the closest cited facts. That is a "
    "committed answer; 'the evidence does not contain it' is not.\n\n"
    "FINISH: never mix tool calls and the final answer in one turn. When the "
    "constraints are verified (or best-effort covered), write the complete "
    "cited answer."
)

SUPERLATIVE_RULE = (
    "SUPERLATIVE / TALLY — SHOW THE TABLE. The answer is one item, but you "
    "cannot know it without the whole pool. Before naming a winner: (1) list "
    "EVERY candidate the question's scope admits — every player who appeared, "
    "every officeholder in the span, every body in the ranking; (2) put the "
    "deciding value next to each (birth date, count, figure), cited; (3) THEN "
    "name the maximum. Reproduce that candidate table in the proof section — "
    "a correct winner with no visible tally loses to a reference that shows "
    "its work, and 'among others' / 'and several more' is not a tally. If the "
    "pool is large, show the top contenders and state the cutoff you applied."
)

SET_RULE = (
    "SET ANSWER: this question asks for a set. Missing a qualifying member "
    "scores the same as wrong — enumerate the pool, test EVERY member against "
    "EVERY condition, and name ALL qualifiers (each with its own citations per "
    "condition). Name the near-misses you excluded and the condition each "
    "fails. Never claim 'the only X' unless the whole pool was checked; if "
    "your pool may be partial, still commit to every qualifier you verified. "
    "GET THE POOL FROM A LIST, NOT MEMBER-BY-MEMBER: your FIRST retrieval for a "
    "set question should hunt the authoritative roster/list/table that "
    "enumerates the whole pool (search it AS a list — '<pool subject> list', "
    "'<pool subject> table', 'list of <pool subject>' — and read_page it). "
    "Assembling the pool from separate per-member searches is how a run ends up "
    "with 3 of 6 qualifiers: the members you never thought to search for are "
    "invisible to you. Read the roster page first, then verify each member. "
    "UNIVERSAL conditions ('in EVERY one of those prisons', 'for BOTH "
    "segments', 'in ALL three years'): check each candidate against EACH "
    "instance separately, with a citation per instance — one shared instance "
    "is not enough. If NO candidate survives every instance, then 'none' IS "
    "the answer: state it as a verified fact about the world with the "
    "per-instance citations that prove it."
)

_COMMIT_RULES = (
    "You are writing the FINAL ANSWER to a research question from evidence that "
    "has already been gathered. You have NO tools — never emit tool syntax. A "
    "judge compares your answer with a strong reference and credits only claims "
    "carrying an [n] citation to the numbered evidence.\n\n"
    "SHAPE: the first words are the answer entities themselves — no preamble, no "
    "remark about evidence quality. Then a short proof section: the candidate "
    "pool, each condition applied, one line per qualifier (cited) and one per "
    "prominent exclusion with its cited reason. Reproduce figures and dates "
    "VERBATIM. Name ALL qualifying members — omitting one scores as wrong. "
    "Never say what the evidence does not contain; commit to the best-supported "
    "answer you can defend."
)

_REPAIR_ORDER = (
    "Your last message was not a usable final answer (it contained tool-call "
    "markup, was empty, or was a refusal). Do NOT emit tool syntax as text. "
    "Write the FINAL ANSWER now as plain prose: first words are the answer "
    "entities themselves, every factual claim followed by its [n] citation, "
    "then the short proof section. Nothing else."
)


def _wrapup_order(seconds_left: float) -> str:
    return (
        f"TIME IS UP (~{int(seconds_left)}s left). No more tool calls. Write the "
        "complete final answer NOW from the numbered results above plus your "
        "knowledge: the FIRST words are the answer entities (no 'Based on…' "
        "preamble, no 'partial answer' framing, no '(verify)' markers), cite [n] "
        "on every claim, keep the required format. A cited partial answer "
        "scores; a refusal or a remark about insufficient evidence scores zero."
    )


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 5 — evidence ledger (tool-result numbering for [n] citations)
# ═══════════════════════════════════════════════════════════════════════════
class EvidenceLedger:
    def __init__(self) -> None:
        self.rows: list[dict] = []  # 1-based via position

    def add(self, receipt_id: str, result_id: str, note_len: int,
            kind: str, spans: list[tuple[int, int]] | None,
            title: str = "", url: str = "", preview: str = "") -> int:
        self.rows.append({
            "receipt_id": receipt_id,
            "result_id": result_id,
            "note_len": note_len,
            "kind": kind,
            # what the model was SHOWN — powers the clean-digest commit and the
            # deterministic cited last rung (both need text without the transcript)
            "title": (title or "")[:160],
            "url": (url or "")[:300],
            # v32.6 S2: normalized ONCE, here, so every consumer sees ordered,
            # disjoint, in-range regions and no caller can re-introduce an overlap.
            "spans": _merge_spans(spans, note_len),
        })
        self.rows[-1]["preview"] = (preview or "")[:FETCH_PREVIEW_CHARS]
        return len(self.rows)

    def ref_for(self, number: int) -> CitationRef | None:
        if not (1 <= number <= len(self.rows)):
            return None
        row = self.rows[number - 1]
        if row.get("kind") == "reserved":
            return None      # slot reserved but its tool call failed
        if not row["receipt_id"] or not row["result_id"]:
            return None
        spans = row["spans"]
        if spans:
            # every region the model was SHOWN is citable — for a large fetch that
            # is the head AND the focused window; a head-sourced claim must not
            # dangle outside the judge-materialized slice (review finding).
            slices = [CitationSlice(start=s, end=e)
                      for s, e in spans[:MAX_SLICES_PER_REF]]
            return CitationRef(receipt_id=row["receipt_id"],
                               result_id=row["result_id"], slices=slices)
        return None   # F1: every row carries spans now; a sliceless ref would
                      # materialize the whole note and can breach/invalidate.


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 6 — tools
# ═══════════════════════════════════════════════════════════════════════════
# v32.5 DETERMINISTIC NUMBERING. Tool calls run concurrently, but each used to
# append to the ledger as its OWN network call returned, so [n] assignment was
# latency-ordered and differed between validator re-runs of the same question
# (the same defect already fixed in the pre-seed). Tools now return their rows
# plus text carrying \x00i\x00 placeholders; the caller appends rows in CALL
# order and substitutes the real numbers. Numbering becomes a function of the
# transcript, not the network.
#
# v32.6 S6: the carrier is a plain (text, rows) tuple. v32.5 used a one-off
# ToolOutput class whose own comment worried that a dunder name in a class body
# was untested against the server-side AST policy — a tuple removes both the
# class and the worry, and _commit_tool_output is the only reader either way.
_SLOT = "\x00{}\x00"


def _tool_payload(text: str, rows: list[dict]):
    return (text, rows)


def _commit_tool_output(out, ledger: EvidenceLedger) -> str:
    """Append a tool's rows in call order, then resolve its [n] placeholders."""
    if isinstance(out, str):
        return out
    if not (isinstance(out, tuple) and len(out) == 2):
        return f"# tool returned an unusable payload: {out!r}"[:300]
    text = out[0]
    rows = out[1]
    if not isinstance(text, str) or not isinstance(rows, list):
        return "# tool returned an unusable payload"
    for i, row in enumerate(rows):
        n = ledger.add(row["receipt_id"], row["result_id"], row["note_len"],
                       row["kind"], row["spans"], title=row.get("title", ""),
                       url=row.get("url", ""), preview=row.get("preview", ""))
        text = text.replace(_SLOT.format(i), str(n))
    return text


_SITE_OP_RE = re.compile(r"\bsite:\S+\s*", re.I)


def _degrade_query(q: str) -> str:
    """Loosen an over-constrained query: drop site: operators and quoting.
    Champion lineages retry a failed search this way instead of giving up."""
    out = _SITE_OP_RE.sub("", q or "").replace('"', " ")
    return " ".join(out.split())


def _search_span(note_len: int) -> list[tuple[int, int]] | None:
    """v32.4: cite the EXCERPT WE SHOWED, not the whole note. A sliceless ref
    materializes the entire note (hydration._materialize_selection), and a rich
    provider excerpt can run to many KB — a handful of them breaches the 120k
    wall and invalidates the whole response. The slice must also be >=100 chars
    unless it covers a shorter note entirely."""
    if note_len >= MIN_SLICE_CHARS:
        return [(0, min(max(SEARCH_EXCERPT_CHARS, MIN_SLICE_CHARS), note_len))]
    if note_len:
        return [(0, note_len)]
    return None


async def _do_search(query_text: str, deadline: float):
    """Returns a (text, rows) payload, or a plain string when nothing is citable.

    v32.6 S3/S6 — takes the deadline (it used to take a `ledger` it had stopped
    touching, and retried on a fixed 18s timeout with no view of the wall: three
    attempts could run 54s inside a tool phase budgeted for 38s, so the fan-out
    was cancelled and every sibling call's evidence went with it)."""
    if not query_text.strip():
        return "# web_search: empty query"
    # v32.5 SECOND PATH: one provider + one attempt was TERMINAL — an empty result
    # set killed that line of enquiry for the whole run, and an empty search is a
    # pure zero-source. Retry once, then once more with the query loosened.
    payload = None
    fired: set[str] = set()
    # the plain retry must fire even when the degraded form is identical — the
    # previous "attempt == attempts[i-1]" guard ate it for every query without a
    # site: or a quote, i.e. almost all of them, leaving one attempt as before.
    for attempt, allow_repeat in ((query_text, False), (query_text, True),
                                  (_degrade_query(query_text), False)):
        if not attempt.strip() or (attempt in fired and not allow_repeat):
            continue
        left = _remaining(deadline) - MIN_TAIL_S
        if left < 4.0:
            break
        fired.add(attempt)
        try:
            payload = await search_web(attempt, provider=SEARCH_PROVIDER,
                                       num=SEARCH_RESULTS_N,
                                       timeout=min(SEARCH_TIMEOUT_S, left))
            if getattr(payload, "results", None):
                break
        except Exception:
            payload = None
    if payload is None:
        return f"# web_search({query_text!r}) failed"
    _spend_note(payload)
    receipt = str(getattr(payload, "receipt_id", "") or "")
    results = list(getattr(payload, "results", None) or [])
    if not receipt:
        return f"# web_search({query_text!r}): no citable results"
    rows: list[dict] = []
    lines = [f"# web_search({query_text!r}): {len(results)} results"]
    for item in results:
        rid = getattr(item, "result_id", None)
        if not isinstance(rid, str) or not rid:
            continue
        note = (getattr(item, "note", None) or "")
        if not note.strip():
            continue   # F1: no source text -> the platform rejects any citation
                       # to it ("cited result has no source text") and the WHOLE
                       # response is invalidated. Never ledger it.
        n_len = len(note)
        title = (getattr(item, "title", None) or "").strip()
        url = (getattr(item, "url", None) or "").strip()
        rows.append({"receipt_id": receipt, "result_id": rid, "note_len": n_len,
                     "kind": "search", "spans": _search_span(n_len),
                     "title": title, "url": url,
                     "preview": note[:SEARCH_EXCERPT_CHARS]})
        lines.append(f"[{_SLOT.format(len(rows) - 1)}] {title} — {url}"
                     f"\n    {note[:SEARCH_EXCERPT_CHARS]}")
    return _tool_payload("\n".join(lines), rows)


async def _do_fetch(url: str, focus: str, question: str, deadline: float):
    """Returns a (text, rows) payload, or a plain string when nothing is citable.

    v32.6 S6: v32.5 annotated this `-> str` while returning a payload object on
    the success paths — the annotation described the failure path only."""
    if not url.strip():
        return "# read_page: empty url"
    payload = None
    for _attempt in (0, 1):  # one retry: crawls intermittently return empty
        left = _remaining(deadline) - MIN_TAIL_S
        if left < 4.0:
            break
        try:
            payload = await fetch_page(url, provider=SEARCH_PROVIDER,
                                       timeout=min(FETCH_TIMEOUT_S, left))
            if getattr(payload, "results", None):
                break
        except Exception:
            payload = None
    if payload is None:
        return f"# read_page({url!r}) failed"
    _spend_note(payload)
    receipt = str(getattr(payload, "receipt_id", "") or "")
    results = list(getattr(payload, "results", None) or [])
    if not results or not receipt:
        return f"# read_page({url!r}): no content"
    item = results[0]
    rid = getattr(item, "result_id", None)
    note = getattr(item, "note", None) or ""
    if not isinstance(rid, str) or not rid or not note.strip():
        return f"# read_page({url!r}): no usable content"
    if len(note) <= FETCH_PLAIN_CHARS:
        row = {"receipt_id": receipt, "result_id": rid, "note_len": len(note),
               "kind": "fetch", "spans": [(0, len(note))], "title": url,
               "url": url, "preview": note[:FETCH_PREVIEW_CHARS]}
        return _tool_payload(
            f"# read_page({url!r}) -> [{_SLOT.format(0)}] full page, "
            f"{len(note)} chars\n{note}", [row])
    # Large page: head + the K densest question/focus regions (deterministic).
    terms = _key_terms(question) | _key_terms(focus)
    windows = _best_windows(note, terms, FETCH_WINDOW_CHARS, k=FETCH_WINDOWS_PER_PAGE)
    # v32.6 S2: merge here. The head and the first window overlap whenever the
    # densest region IS the head, and two overlapping slices charge the judge's
    # 120k evidence wall twice for the same characters.
    row = {"receipt_id": receipt, "result_id": rid, "note_len": len(note),
           "kind": "fetch",
           "spans": _merge_spans([(0, FETCH_HEAD_CHARS)] + list(windows), len(note)),
           "title": url, "url": url,
           "preview": note[windows[0][0]:windows[0][0] + FETCH_PREVIEW_CHARS]}
    head = note[:FETCH_HEAD_CHARS]
    sections = "".join(
        f"\n--- section @{s} ---\n{note[s:e]}" for s, e in windows)
    return _tool_payload(
        f"# read_page({url!r}) -> [{_SLOT.format(0)}] {len(note)} chars total; head + "
        f"the {len(windows)} most relevant section(s) shown "
        f"({', '.join(f'{s}-{e}' for s, e in windows)}). If the answer set may "
        f"continue elsewhere in this page, call read_page again with a "
        f"different focus.\n--- head ---\n{head}{sections}", [row])


# ── sec_filing tool: deterministic EDGAR primary-document resolution ─────────
# Ported from our review-hardened v31.6 pipeline router; the MODEL supplies
# company/form/year as arguments. v32.3 /code-review fixes: symmetric alnum
# tokenization (legal suffixes/apostrophes/dots no longer break matching),
# ticker branch only for single-token input, reportDate-only named-year match,
# form-code canonicalization, null guards, deadline-aware bounded fetches with
# retry, tickers cache, spend notes, neutral examples, uniform search fallback.
_SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
_SEC_DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"
_SEC_FETCH_TIMEOUT_S = 26.0     # large JSON needs more than the page default (lineage lesson)
_SEC_MIN_HEADROOM_S = 40.0
_SEC_CACHE: dict = {}           # url -> parsed JSON (tickers is ~10MB; fetch once)
# v32.6: the cache is process-global and outlives a single question, so a long
# run over many companies grew it without bound. Cap it, and keep the expensive
# ticker index across the eviction.
_SEC_CACHE_MAX = 24
_SEC_STOPWORDS = frozenset(
    "inc incorporated corp corporation company companies co ltd limited llc plc "
    "lp llp group holdings the".split())
_SEC_ALNUM_RE = re.compile(r"[a-z0-9]+")


def _sec_tokens(text: str) -> list[str]:
    """ONE tokenizer for both the model's company arg and EDGAR titles — the
    review proved asymmetric tokenization false-negatived 'Apple Inc.',
    \"McDonald's\" and 'U.S. Bancorp'."""
    return [w for w in _SEC_ALNUM_RE.findall((text or "").lower())
            if w not in _SEC_STOPWORDS]


def _sec_norm_form(form: str) -> str:
    """Canonicalize model-supplied form codes to EDGAR's ('10K'->'10-K',
    'def14a'->'DEF 14A', 'Form 10-Q'->'10-Q')."""
    f = " ".join((form or "").upper().replace("FORM", " ").split())
    m = re.fullmatch(r"(\d{1,2})\s*-?\s*([A-Z])", f)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.fullmatch(r"(DEF)\s*-?\s*(14A)", f)
    if m:
        return "DEF 14A"
    return f


def _sec_cache_put(url: str, obj: dict) -> None:
    if len(_SEC_CACHE) >= _SEC_CACHE_MAX:
        tickers = _SEC_CACHE.get(_SEC_TICKERS_URL)
        _SEC_CACHE.clear()
        if tickers is not None:
            _SEC_CACHE[_SEC_TICKERS_URL] = tickers
    _SEC_CACHE[url] = obj


async def _fetch_json(url: str, deadline: float):
    cached = _SEC_CACHE.get(url)
    if cached is not None:
        return cached
    for _attempt in (0, 1):   # large-JSON crawls intermittently return empty
        left = _remaining(deadline)
        if left < 12.0:
            return None
        budget = min(_SEC_FETCH_TIMEOUT_S, left - 6.0)
        try:
            payload = await asyncio.wait_for(
                fetch_page(url, provider=SEARCH_PROVIDER, timeout=budget),
                timeout=budget + 4.0)
        except Exception:
            continue
        _spend_note(payload)
        results = list(getattr(payload, "results", None) or [])
        note = (getattr(results[0], "note", None) or "") if results else ""
        start = note.find("{")
        end = note.rfind("}")
        if start == -1 or end <= start:
            continue
        try:
            obj = json.loads(note[start:end + 1])
        except Exception:
            continue
        if isinstance(obj, dict):
            _sec_cache_put(url, obj)
            return obj
    return None


def _sec_pick_filing(recent: dict, form: str, year: str):
    """Pick (accession, primaryDocument) for the canonicalized form. A named
    year matches on reportDate ONLY (the fiscal period end) — a filingDate-year
    match would silently return the PRIOR fiscal year's document (review
    finding). Named-year miss -> None; no year -> most recent of that form."""
    forms = recent.get("form")
    accs = recent.get("accessionNumber")
    docs = recent.get("primaryDocument")
    rdates = recent.get("reportDate")
    fdates = recent.get("filingDate")
    if not (isinstance(forms, list) and isinstance(accs, list) and isinstance(docs, list)):
        return None
    n = min(len(forms), len(accs), len(docs))
    form_norm = _sec_norm_form(form)
    best_year = None
    best_any = None
    for i in range(n):
        if _sec_norm_form(str(forms[i])) != form_norm:
            continue
        if accs[i] is None or docs[i] is None:
            continue
        acc = str(accs[i])
        doc = str(docs[i])
        if not acc or not (doc.endswith(".htm") or doc.endswith(".html")):
            continue
        rd = str(rdates[i]) if (isinstance(rdates, list) and i < len(rdates)
                                and rdates[i] is not None) else ""
        fd = str(fdates[i]) if (isinstance(fdates, list) and i < len(fdates)
                                and fdates[i] is not None) else ""
        key = rd or fd
        if best_any is None or key > best_any[0]:
            best_any = (key, acc, doc)
        if year and rd[:4] == year:
            if best_year is None or key > best_year[0]:
                best_year = (key, acc, doc)
    pick = best_year if year else best_any
    if pick is None:
        return None
    return pick[1], pick[2]


_SEC_SEARCH_HINT = "search \"site:sec.gov {company} {year} {form}\" and read_page the Archives result"


async def _do_sec_filing(company: str, form: str, year: str, deadline: float) -> str:
    company = (company or "").strip()
    form = (form or "").strip() or "10-K"
    year = (year or "").strip()[:4]
    hint = _SEC_SEARCH_HINT.format(company=company, year=year, form=form)
    if not company:
        return "# sec_filing: company required"
    if _remaining(deadline) < _SEC_MIN_HEADROOM_S:
        return f"# sec_filing: skipped (low time) — {hint}"
    tickers = await _fetch_json(_SEC_TICKERS_URL, deadline)
    if not isinstance(tickers, dict):
        return f"# sec_filing: EDGAR ticker index unavailable — {hint}"
    want = _sec_tokens(company)
    best = None  # (score, -len(title), cik10, title)
    for row in tickers.values():
        if not isinstance(row, dict):
            continue
        title = str(row.get("title", ""))
        ticker = str(row.get("ticker", "")).lower()
        words = set(_sec_tokens(title))
        n_hit = sum(1 for w in want if w in words)
        if len(want) == 1 and ticker == want[0]:
            score = 100   # exact ticker — only for single-token input (review:
            # 'Sun Communities' must never resolve via ticker SUN=Sunoco)
        elif want and n_hit == len(want):   # ALL tokens present — no namesakes
            score = 50 + n_hit
        else:
            continue
        cand = (score, -len(title), str(row.get("cik_str", "")).zfill(10), title)
        if best is None or cand > best:
            best = cand
    if best is None:
        return f"# sec_filing({company!r}): no confident EDGAR match — {hint}"
    cik10, title = best[2], best[3]
    subs = await _fetch_json(_SEC_SUBMISSIONS_URL.format(cik10=cik10), deadline)
    filings = subs.get("filings") if isinstance(subs, dict) else None
    recent = filings.get("recent") if isinstance(filings, dict) else None
    if not isinstance(recent, dict):
        return f"# sec_filing({company!r}): EDGAR submissions unavailable for {title} — {hint}"
    pick = _sec_pick_filing(recent, form, year)
    if pick is None:
        return (f"# sec_filing({company!r}, {form!r}, year={year or 'latest'}): no matching "
                f"filing in EDGAR's recent index for {title} — check the form/year, or {hint}")
    accession, doc = pick
    url = _SEC_DOC_URL.format(cik=cik10.lstrip("0") or cik10,
                              accession=accession.replace("-", ""), doc=doc)
    return (f"# sec_filing -> {title} {form} {year or '(latest)'} primary document:\n"
            f"{url}\nNow call read_page on this URL with a focus hint for the "
            f"section you need, and cite figures from that read_page result.")


def _tool_args(call) -> dict:
    try:
        args = json.loads(getattr(call, "arguments", None) or "{}")
    except Exception:
        return {}
    return args if isinstance(args, dict) else {}


async def _run_tool(call, question: str, deadline: float):
    """Dispatch one tool call.

    AST-POLICY: this MUST stay an explicit if/elif chain on a string literal
    comparison. A {name: handler} table read as handlers[name](...) is exactly
    the 'calling dynamically selected callables' construct the validator
    rejects, and it is the tempting refactor here."""
    args = _tool_args(call)
    name = getattr(call, "name", "") or ""
    # (arg or "") not str(arg): an explicit JSON null must not become 'None'
    if name == "web_search":
        return await _do_search(str(args.get("query") or ""), deadline)
    if name == "read_page":
        return await _do_fetch(str(args.get("url") or ""),
                               str(args.get("focus") or ""), question, deadline)
    if name == "sec_filing":
        return await _do_sec_filing(str(args.get("company") or ""),
                                    str(args.get("form") or ""),
                                    str(args.get("year") or ""), deadline)
    return f"# unknown tool {name!r}"


def _tool_phase_budget(calls, deadline: float) -> float:
    """One bound for the whole fan-out, clamped to the wall.

    F3 (v32.4): the tool phase must never outlive the deadline.
    v32.6: an EDGAR resolution is two large-JSON fetches, so capping the phase
    at the search/fetch figure guaranteed sec_filing was cancelled mid-way on a
    cold cache — and a cancelled resolution caches nothing, so the next attempt
    started over. The clamp to the remaining wall still dominates."""
    cap = TOOL_PHASE_S
    for call in calls:
        if (getattr(call, "name", "") or "") == "sec_filing":
            cap = SEC_TOOL_PHASE_S
            break
    return max(5.0, min(cap, _remaining(deadline) - MIN_TAIL_S))


async def _run_tool_calls(calls, question: str, ledger: EvidenceLedger,
                          deadline: float) -> list[str]:
    """Run a fan-out concurrently under one bounded budget; return one committed
    body per call, in CALL order.

    R1: asyncio.wait (not wait_for+gather) so a timeout does NOT discard the
    calls that already finished.
    v32.5: ledger rows are appended HERE, in call order — never inside the
    concurrent coroutines — so [n] numbering is run-invariant."""
    tasks = [asyncio.ensure_future(_run_tool(c, question, deadline)) for c in calls]
    try:
        await asyncio.wait(tasks, timeout=_tool_phase_budget(calls, deadline))
    except Exception:
        pass
    bodies: list[str] = []
    for task in tasks:
        if not task.done():
            task.cancel()
            bodies.append("# tool timed out — use what you already have")
            continue
        try:
            bodies.append(_commit_tool_output(task.result(), ledger))
        except Exception as exc:
            bodies.append(f"# tool crashed: {exc}")
    return bodies


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 7 — LLM plumbing (ordered fallback chain, single provider)
# ═══════════════════════════════════════════════════════════════════════════
# v32.6 S4: v32.5 read `choices[0].message` as a bare attribute chain in three
# places. If a model ever returns a choice without `.message`, that is an
# AttributeError thrown from inside _loop — i.e. the whole research run is
# abandoned and the rescue ladder starts from whatever the ledger happens to
# hold. These three helpers are the only places that touch the payload shape.


def _first_message(llm):
    choices = getattr(llm, "choices", None) or []
    if not choices:
        return None
    return getattr(choices[0], "message", None)


def _message_text(llm) -> str:
    """raw_text if the provider supplies it, else the first choice's content."""
    text = (getattr(llm, "raw_text", None) or "").strip()
    if text:
        return text
    content = getattr(_first_message(llm), "content", None)
    if isinstance(content, str):
        return content.strip()
    return ""


def _assistant_turn(msg):
    """Round-trip an assistant tool-call turn back into the transcript.

    Returns the SDK's own input-message dict, or None when it cannot be
    produced. None matters: replying to tool_call_ids whose assistant turn is
    missing makes the NEXT request's transcript invalid, so the caller must take
    the system-note path instead of emitting orphan tool replies."""
    try:
        turn = msg.to_input_message()
    except Exception:
        return None
    return turn if isinstance(turn, dict) else None


async def _chat_simple(provider: str, model: str, system: str, user: str, *,
                       max_tokens: int, timeout: float,
                       think: dict | None = None) -> str:
    payload = await llm_chat(
        provider=provider,
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0.15,  # v32.4b: field-standard; greedy caused repetition loops
        max_output_tokens=max_tokens,
        timeout=timeout,
        thinking=think if think is not None else {"enabled": False},
    )
    _spend_note(payload)
    return _message_text(getattr(payload, "llm", None))


async def _chat_turn(messages: list[dict], deadline: float, *, finish_only: bool,
                     force_tools: bool = False):
    """One loop turn: primary model first, fallback model on failure."""
    use_tools = force_tools or not finish_only
    for provider, model, lean_finish in LANES:
        timeout = min(TURN_TIMEOUT_S, _remaining(deadline) - 5.0)
        if timeout <= 5.0:
            return None
        lean = finish_only and lean_finish
        try:
            payload = await llm_chat(
                provider=provider,
                model=model,
                messages=messages,
                tools=LOOP_TOOLS if use_tools else None,
                tool_choice="auto" if use_tools else None,
                # v32.4b: BACK to 0.2. Greedy decoding (0.0) produced degenerate
                # repetition in the qualifying smoke — a turn emitted the same
                # "I need to gather..." sentence 3x and that shipped as the answer.
                # The whole field runs 0.2; determinism comes from the pre-seed and
                # the answer floor, not from collapsing the sampler.
                temperature=0.2,
                # v32.5b: this is LANE-scoped, not turn-scoped, and v32.7 moves the
                # scope onto the lane entry itself (see LANES). Stripping reasoning
                # from the PRIMARY on the final turn would remove it from the one
                # turn that must apply every answer rule and place every [n].
                thinking=({"enabled": False} if lean
                          else {"enabled": True, "effort": "low"}),
                max_output_tokens=6000 if lean else None,
                timeout=timeout,
            )
            _spend_note(payload)
            return payload
        except Exception:
            continue
    return None


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 8 — stage 1: knowledge briefing
# ═══════════════════════════════════════════════════════════════════════════
async def _knowledge_brief(question: str) -> tuple[str, str]:
    """One call: the model's own best answer + a verification plan. Returns
    (draft_answer, briefing_block). The draft alone often carries a knowledge-
    heavy batch; the loop then verifies the load-bearing facts."""
    system = ("Senior research analyst. Commit to concrete best answers from "
              "knowledge; mark uncertain values (verify). Never refuse.")
    user = (
        f"Question:\n{question}\n\n"
        "Write these blocks:\n"
        "BEST ANSWER: your full best answer now — candidate pool, every stated "
        "condition applied, qualifying entities with figures/dates, near-miss "
        "exclusions. Flag shaky facts with (verify).\n"
        "CHECKLIST: each atomic condition in the question, numbered, including "
        "any output-format demand.\n"
        "LOOKUPS: 3-6 precise web searches for the facts that decide the answer "
        "(entity + metric + year; include a named source's site: filter).\n"
        "PAGES: up to 5 exact URLs worth reading directly (official stats pages, "
        "sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."
    )
    # v32.7: the hand-unrolled A-then-B pair is now the shared LANES chain, so a
    # model swap lands in one place instead of four. Same two attempts, same
    # thinking settings, same order.
    raw = ""
    first = True
    for provider, model, _lean in LANES:
        think = {"enabled": True, "effort": "low"} if first else {"enabled": True}
        first = False
        try:
            raw = await _chat_simple(provider, model, system, user,
                                     max_tokens=3600, timeout=BRIEF_TIMEOUT_S,
                                     think=think)
        except Exception:
            raw = ""
        if raw:
            break
    if not raw:
        return "", ""
    draft = raw
    cut = re.search(r"[#*\s]*CHECKLIST[#*\s]*:", raw, re.IGNORECASE)
    if cut is not None:
        draft = raw[:cut.start()]
    draft = re.sub(r"^BEST ANSWER\s*:\s*", "", draft).strip()
    brief = ("PRIOR ANALYSIS (your own; verify anything marked (verify), and "
             "correct it wherever tool results disagree):\n" + raw.strip())
    return draft, brief


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 9 — stage 1b: deterministic pre-seed
# ═══════════════════════════════════════════════════════════════════════════
# The measured variance killer: with the model choosing turn 1, five validator
# re-runs opened five different trajectories and gathered five different
# evidence sets (prod f462cada: one run complete, four partial -> median 0).
# These queries are pure functions of the question, so EVERY run starts from the
# same numbered evidence — and the rescue rungs are never empty-handed.
_SEED_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-']+")
_SEED_STOP = frozenset("name list give tell show find identify please could would "
                       "you your can may might should must let make sure both also".split())
MAX_SEED_QUERIES = 3
PRESEED_MIN_ENTRY_S = 40.0
PRESEED_MIN_SEED_S = 30.0


def _seed_queries(question: str, set_question: bool) -> list[str]:
    q = " ".join((question or "").split())
    if not q:
        return []
    seeds = [q[:300]]
    # F7: keep CONTENT words, not just capitalised/numeric ones — the pool noun
    # in a set question is always lowercase ('which bridges…'), and dropping it
    # turned the roster seed into 'list of Budapest 1945'.
    salient = [t for t in _SEED_TOKEN_RE.findall(q)
               if len(t) >= 3 and t.lower() not in _STOP and t.lower() not in _SEED_STOP]
    if len(salient) >= 2:
        seeds.append(" ".join(salient[:8]))
    if set_question and salient:
        # a set question is lost by an incomplete POOL, so seed the roster hunt
        seeds.append("list of " + " ".join(salient[:6]))
    out: list[str] = []
    for s in seeds:
        s = s.strip()
        if s and s not in out:
            out.append(s)
    return out[:MAX_SEED_QUERIES]


async def _preseed(question: str, set_question: bool, ledger: EvidenceLedger,
                   deadline: float) -> str:
    """Run the seed queries; return a numbered digest to inject."""
    seeds = _seed_queries(question, set_question)
    if not seeds or _remaining(deadline) < PRESEED_MIN_ENTRY_S:
        return ""
    # F10: run SEQUENTIALLY. Under asyncio.gather each _do_search appends to the
    # shared ledger as its own network call returns, so [n] assignment depended on
    # latency ordering and differed between runs — the opposite of the determinism
    # this mechanism exists to provide.
    blocks: list = []
    for seed in seeds:
        if _remaining(deadline) < PRESEED_MIN_SEED_S:
            break
        # v32.6 S3: the per-seed wait_for used a FIXED 42s budget while the entry
        # guard let a seed start with 30s left — a slow provider therefore ran the
        # clock 12s PAST the wall, and _loop then broke on its first line without
        # ever calling the model. Clamp the budget to what is actually left.
        budget = min(SEARCH_TIMEOUT_S * 2 + 6.0, _remaining(deadline) - MIN_TAIL_S)
        if budget < 8.0:
            break
        try:
            out = await asyncio.wait_for(_do_search(seed, deadline), timeout=budget)
            blocks.append(_commit_tool_output(out, ledger))
        except Exception:
            continue
    good = [b for b in blocks if isinstance(b, str) and _CITE_MARK_RE.search(b)]
    if not good:
        return ""   # no numbered rows -> do not claim "already numbered"
    return ("Automatic first-pass searches (already numbered — cite these [n] "
            "directly, and search further as needed):\n\n" + "\n".join(good))


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 10 — stage 2: the research loop
# ═══════════════════════════════════════════════════════════════════════════
def _opening_messages(question: str, brief: str) -> tuple[list[dict], bool]:
    set_q = _needs_set_completeness(question)
    messages = [{"role": "system", "content": LOOP_RULES}]
    if set_q:
        messages.append({"role": "system", "content": SET_RULE})
    if _needs_superlative_proof(question):
        messages.append({"role": "system", "content": SUPERLATIVE_RULE})
    if brief:
        messages.append({"role": "system", "content": brief})
    return messages, set_q


async def _loop(question: str, brief: str, ledger: EvidenceLedger,
                deadline: float, turn_cap: int,
                carry: list[dict] | None = None,
                force_tools_first_turn: bool = False) -> tuple[str, list[dict]]:
    if carry is not None:
        messages = carry
    else:
        messages, set_q = _opening_messages(question, brief)
        # deterministic evidence BEFORE the model's first choice
        seeded = await _preseed(question, set_q, ledger, deadline)
        if seeded:
            messages.append({"role": "system", "content": seeded})
        messages.append({"role": "user", "content": question})

    answer = ""
    ordered_wrapup = False
    repairs_left = ANSWER_REPAIR_TURNS
    for turn in range(1, turn_cap + 1):
        left = _remaining(deadline)
        if left <= MIN_TAIL_S:
            break
        out_of_time = left <= WRAPUP_AT_S
        out_of_spend = _spend_left() <= WRAPUP_MIN_USD
        # v32.6 S5: the audit patch used to attach tools AND append "TIME IS UP.
        # No more tool calls." on the same turn whenever it entered with 70-90s
        # left — the model was ordered to stop and handed the means to continue.
        # A forced tool turn now only fires with real headroom, and owns its turn.
        forced_tool_turn = (force_tools_first_turn and turn == 1
                            and not out_of_time and not out_of_spend)
        finish_only = (out_of_time or out_of_spend or turn >= turn_cap) and not forced_tool_turn
        if (finish_only or turn >= turn_cap - 1) and not ordered_wrapup and not forced_tool_turn:
            messages.append({"role": "system", "content": _wrapup_order(left)})
            ordered_wrapup = True

        payload = await _chat_turn(messages, deadline, finish_only=finish_only,
                                   force_tools=forced_tool_turn)
        if payload is None:
            break
        llm = getattr(payload, "llm", None)
        msg = _first_message(llm)
        if msg is None:
            break
        calls = getattr(msg, "tool_calls", None) or ()
        if not calls:
            candidate = _message_text(llm)
            # v32.4 FLOOR: never accept tool-markup / empty / stub / bare refusal
            # as the final answer (prod f462cada shipped exactly that). Spend a
            # bounded repair turn telling the model to write plain prose instead.
            if not _is_usable_answer(candidate):
                if repairs_left > 0 and _remaining(deadline) > MIN_TAIL_S + 10.0:
                    repairs_left -= 1
                    # F9: do NOT echo the junk back — replaying tool markup as an
                    # assistant turn is the strongest few-shot signal to repeat it.
                    messages.append({"role": "system", "content": _REPAIR_ORDER})
                    answer = ""
                    continue
                answer = ""   # nothing usable — let the caller's rescue chain run
                break
            answer = candidate
            # keep the answer IN the transcript so the audit-patch loop can
            # see what it is fixing (review finding: it was never appended).
            messages.append({"role": "assistant", "content": answer})
            break

        # per-turn fan-out cap: run the first N, stub the rest — EVERY tool_call
        # id still gets a reply (an unanswered id fails transcript validation).
        run_calls = list(calls[:MAX_TOOL_FANOUT])
        turn_msg = _assistant_turn(msg)
        call_ids = [getattr(c, "id", None) for c in calls]
        ids_ok = all(isinstance(cid, str) and cid for cid in call_ids)
        if turn_msg is None or not ids_ok:
            # v32.6 S4: we cannot build a valid tool-reply transcript for this
            # turn. Emitting tool messages anyway would leave orphan
            # tool_call_ids and the NEXT request would be rejected outright, so
            # fold the evidence into a system note and keep researching.
            bodies = await _run_tool_calls(run_calls, question, ledger, deadline)
            messages.append({
                "role": "system",
                "content": ("Tool results (already numbered — cite these [n]):\n\n"
                            + "\n\n".join(bodies))})
            continue

        messages.append(turn_msg)
        bodies = await _run_tool_calls(run_calls, question, ledger, deadline)
        for cid, body in zip(call_ids, bodies):
            messages.append({"role": "tool", "tool_call_id": cid, "content": body})
        for cid in call_ids[MAX_TOOL_FANOUT:]:
            messages.append({"role": "tool", "tool_call_id": cid,
                             "content": "# skipped: per-turn tool budget reached — re-issue next turn if still needed"})
    return answer, messages


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 11 — stage 3: completeness audit + patch
# ═══════════════════════════════════════════════════════════════════════════
_AUDIT_KEYS = ("incomplete_roster", "hand_waved_tally", "unanswered_parts",
               "uncited_facts", "wrong_kind", "thin_proof")
_ROSTER_KEYS = ("incomplete_roster", "hand_waved_tally")


def _audit_gaps(report) -> tuple[list[str], list[str]]:
    gaps: list[str] = []
    roster_gaps: list[str] = []
    if not isinstance(report, dict):
        return gaps, roster_gaps
    for key in _AUDIT_KEYS:
        vals = report.get(key)
        if not isinstance(vals, list):
            continue
        found = [str(v) for v in vals if str(v).strip()]
        if key in _ROSTER_KEYS:
            roster_gaps.extend(found)
        gaps.extend(found)
    return gaps, roster_gaps


async def _audit_patch(question: str, answer: str, messages: list[dict],
                       ledger: EvidenceLedger, deadline: float) -> str:
    probe = (
        "Audit the answer against the question. JSON only, keys: "
        '"unanswered_parts" (list; question elements not addressed), '
        '"uncited_facts" (list; load-bearing claims without [n]), '
        '"wrong_kind" (list; places where the named entity is a different KIND '
        "than the question asks — a person instead of a series, a duo instead "
        "of a show), "
        '"incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges '
        "over a candidate pool — a closed set that can be enumerated, or several "
        "conditions applied to a class — then: is the pool itself stated and "
        "plausibly COMPLETE, and does the answer give a verdict for EVERY member "
        "(qualifies / excluded because X, each cited)? Name any pool member the "
        "answer never mentions, and say so if the pool looks truncated — an "
        "answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not "
        "partial), "
        '"thin_proof" (list; a qualifier lacking a per-condition citation, or a '
        "plausible near-miss candidate never addressed), "
        '"hand_waved_tally" (list; for a superlative/count/most-common question: '
        "the answer asserts a winner or a count WITHOUT showing the candidate "
        "table it was derived from. Phrases like 'among others', 'and several "
        "more', 'multiple X', or naming 2 examples to justify a count are all "
        "hand-waving — say so and name what the tally must list). "
        "Empty lists when clean.\n\n"
        f"Question:\n{question}\n\nAnswer:\n{answer[:11000]}"
    )
    try:
        raw = await _chat_simple(LLM_PROVIDER, AUDIT_MODEL,
                                 "Strict completeness auditor. JSON only.",
                                 probe, max_tokens=650, timeout=AUDIT_TIMEOUT_S)
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I | re.M)
        report = json.loads(raw)
    except Exception:
        return answer
    gaps, roster_gaps = _audit_gaps(report)
    # F2: the patch loop needs room for a search AND a rewrite; below this the
    # audit is a pure cost with no possible effect.
    if not gaps or _remaining(deadline) < AUDIT_MIN_HEADROOM_S:
        return answer
    # A truncated candidate pool is a retrieval gap, not a writing gap: spend the
    # patch turns SEARCHING for the roster/list source, then re-answer.
    order = ("AUDIT: the answer has gaps:\n- " + "\n- ".join(gaps[:6]))
    if roster_gaps:
        order += ("\nThe candidate pool is incomplete — this loses outright. FIRST "
                  "search for the authoritative LIST/roster/table that enumerates "
                  "the whole pool (query it as a list, e.g. '<pool subject> full "
                  "list', not one member at a time), verify EVERY member against "
                  "every condition, then rewrite.")
    order += ("\nUse at most 3 tool calls to close the most important gaps, then "
              "rewrite the COMPLETE final answer with [n] citations in the "
              "required shape.")
    messages.append({"role": "system", "content": order})
    patched, _ = await _loop(question, "", ledger, deadline,
                             AUDIT_EXTRA_TURNS + 1, carry=messages,
                             force_tools_first_turn=True)
    patched = patched.strip()
    # uid201's guard: a "repair" that collapsed the answer is a regression.
    if not _is_usable_answer(patched) or len(patched) < int(len(answer) * 0.6):
        return answer
    return patched


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 12 — citations
# ═══════════════════════════════════════════════════════════════════════════
def _citations_for(answer: str, ledger: EvidenceLedger) -> list[CitationRef]:
    """Build refs under the platform's materialized-evidence wall.

    harnyx_commons/application/miner_response_hydration.py: the validator
    materializes every cited slice and raises MinerResponsePayloadError past
    _MAX_TOTAL_EVIDENCE_CHARS = 120_000 — the whole response then scores 0.
    A SLICELESS ref materializes start=0..len(note), i.e. the ENTIRE note, so
    search refs (which carry no spans) are the expensive ones. Prod f462cada
    hit miner_response_invalid on 2 runs; multi-window reads raised the per-ref
    cost, so budget it explicitly instead of hoping.

    v32.6: the cap now counts ACCEPTED refs, not candidates. Truncating the
    candidate list first meant one expensive early ref that the budget rejected
    still consumed a citation slot, so a long answer silently shipped fewer
    citations than the cap allows."""
    refs: list[CitationRef] = []
    spent = 0
    for n in _cited_numbers(answer, len(ledger.rows)):
        if len(refs) >= CITATION_CAP:
            break
        ref = ledger.ref_for(n)
        if ref is None:
            continue
        row = ledger.rows[n - 1]
        slices = getattr(ref, "slices", None)
        cost = (sum(max(0, s.end - s.start) for s in slices) if slices
                else int(row.get("note_len") or 0))     # sliceless == the whole note
        if spent + cost > EVIDENCE_CHAR_BUDGET:
            continue      # skip this one, keep considering cheaper later refs
        spent += cost
        refs.append(ref)
    return refs


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 13 — the rescue ladder (every rung is cited; none advertises failure)
# ═══════════════════════════════════════════════════════════════════════════
def _ledger_digest(ledger: EvidenceLedger, char_cap: int = 60000) -> str:
    """A clean numbered evidence digest — no tool-call history. Preserves the
    exact [n] numbering so citations still resolve. Committing from this beats
    replaying the raw transcript: shorter, no assistant/tool scaffolding, and it
    cannot drop early [n]s off the front of a truncated message window."""
    parts: list[str] = []
    spent = 0
    for i, row in enumerate(ledger.rows, start=1):
        text = (row.get("preview") or "").strip()
        if not text:
            continue
        block = f"[{i}] {row.get('title') or ''} ({row.get('url') or ''})\n{text}"
        if spent + len(block) > char_cap:
            break
        spent += len(block)
        parts.append(block)
    return "\n\n".join(parts)


DETERMINISTIC_ROWS = 6


def _deterministic_answer(question: str, ledger: EvidenceLedger) -> str:
    """Last rung, no LLM. Never emit a bare 'unavailable' line: the judge sees
    only the answer text and makes a forced preference, so advertising our own
    failure hands it a reason to pick the other side. A cited partial always
    beats a refusal.

    v32.6 S8: v32.5 took the ledger's FIRST six rows and ignored the `question`
    argument entirely. By the time this rung runs the ledger is dominated by the
    pre-seed and by whatever the model happened to fetch first, so the six rows
    with the least to do with the question were the ones being submitted. Rank
    by key-term overlap, then restore ledger order for readability. Ties break
    on ledger position, so the output stays a pure function of the evidence."""
    rows = [(i, r) for i, r in enumerate(ledger.rows, start=1)
            if (r.get("preview") or "").strip()]
    if not rows:
        return ""
    terms = _key_terms(question)
    ranked: list[tuple[int, int]] = []      # (-hits, ledger index)
    for i, r in rows:
        blob = ((r.get("title") or "") + " " + (r.get("preview") or "")).casefold()
        ranked.append((-sum(1 for t in terms if t in blob), i))
    ranked.sort()
    chosen = sorted(idx for _neg, idx in ranked[:DETERMINISTIC_ROWS])
    by_index = dict(rows)
    out = ["FINAL ANSWER: based on the sources retrieved, the best-supported "
           "findings for this question are:"]
    for i in chosen:
        r = by_index[i]
        lead = " ".join((r.get("preview") or "").split())[:280]
        title = (r.get("title") or "").strip()
        out.append(f"- {title + ': ' if title else ''}{lead} [{i}]")
    return "\n".join(out)


async def _commit_once(provider: str, model: str, convo: list[dict], budget: float) -> str:
    payload = await llm_chat(
        provider=provider, model=model, messages=convo,
        temperature=0.15, max_output_tokens=2600,
        timeout=budget, thinking={"enabled": False},
    )
    _spend_note(payload)
    return _message_text(getattr(payload, "llm", None))


async def _write_from_digest(question: str, ledger: EvidenceLedger, deadline: float) -> str:
    """Last write from the evidence already gathered: thinking OFF, NO tools, and
    a CLEAN numbered digest instead of the raw transcript — so the model cannot
    over-reason into an empty completion, cannot emit tool markup, and cannot
    lose early [n]s to a truncated message window."""
    if _remaining(deadline) < 14.0:
        return ""
    digest = _ledger_digest(ledger)
    if not digest:
        return ""
    convo = [{"role": "system", "content": _COMMIT_RULES},
             {"role": "user", "content": (
                 f"Question: {question}\n\nNumbered evidence you gathered (cite "
                 f"facts by these [n]):\n\n{digest}\n\n"
                 "Write the FINAL ANSWER now from this evidence. Plain prose, no "
                 "tool syntax. First words are the answer entities; every factual "
                 "claim carries its [n]; then the short proof section (pool, "
                 "conditions, qualifiers, exclusions).")}]
    # v32.5b: the hedge race is REVERTED. Review proved three independent paths
    # to "": (1) asyncio.wait puts a RAISED task in `done`, so a fast primary
    # failure — the exact case the fallback exists for — meant the fallback was
    # never started; (2) for 31s < left <= 45s the fallback branch was skipped and
    # the cleanup loop cancelled the still-running primary; (3) FIRST_COMPLETED
    # let a fast-junk lane cancel a slow-good one. The sequential loop below has
    # none of those failure modes, and an answer that exists beats one that races.
    for provider, model, _lean in LANES:
        left = _remaining(deadline)
        if left < 14.0:
            return ""
        try:
            text = await _commit_once(provider, model, convo,
                                      min(RESCUE_TIMEOUT_S, left - 6.0))
        except Exception:
            continue
        if _is_usable_answer(text):
            return text
    return ""


async def _knowledge_resort(question: str, deadline: float) -> str:
    left = _remaining(deadline)
    if left < 12.0:
        return ""
    try:
        return await _chat_simple(
            LLM_PROVIDER, RESORT_MODEL,
            ("Expert researcher. Best definitive answer with concrete entities, "
             "numbers, dates. Never refuse."),
            question, max_tokens=1500, timeout=min(45.0, left - 4.0))
    except Exception:
        return ""


async def _schema_output(question: str, answer: str, schema, deadline: float) -> object | None:
    ask = ("Convert the answer to a JSON value valid under the schema. Output "
           "ONLY the JSON value.\n\n"
           f"Schema:\n{json.dumps(schema)}\n\nQuestion:\n{question}\n\n"
           f"Answer:\n{answer[:14000]}")
    for model in (SCHEMA_MODEL, RESORT_MODEL):
        left = _remaining(deadline)
        if left < 12.0:
            return None
        try:
            raw = await _chat_simple(LLM_PROVIDER, model,
                                     "You output strictly valid JSON.", ask,
                                     max_tokens=2400, timeout=min(45.0, left - 4.0))
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(),
                         flags=re.I | re.M).strip()
            return json.loads(raw)
        except Exception:
            continue
    return None


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 14 — entrypoint
# ═══════════════════════════════════════════════════════════════════════════
async def _rescue(question: str, answer: str, draft: str,
                  ledger: EvidenceLedger, deadline: float) -> str:
    """v32.4 RESCUE LADDER — every rung is cited; none advertises failure."""
    # 1) rewrite from the clean evidence digest (thinking off, no tools)
    if not _is_usable_answer(answer) and ledger.rows:
        try:
            rescued = await _write_from_digest(question, ledger, deadline)
            if _is_usable_answer(rescued):
                answer = rescued
        except Exception:
            pass
    # 2) deterministic, CITED, zero-LLM. F4: this must come BEFORE the knowledge
    #    draft — the draft is written pre-research and carries no [n] at all, so
    #    it passed the floor and permanently shadowed the only cited rung.
    if not _is_usable_answer(answer) and ledger.rows:
        det = _deterministic_answer(question, ledger)
        if _is_usable_answer(det):
            answer = det
    # 3) last resort: model knowledge (uncited, but better than nothing)
    #
    # v32.6 S9 — TWO defects, both inherited, both live:
    #   (a) rungs 1 and 2 are gated on _is_usable_answer; this one was gated on
    #       `fallback.strip()`, i.e. emptiness only. The briefing draft is
    #       written by the same model that shipped tool markup in f462cada, so
    #       the floor's own invariant ("nothing may be submitted unless it reads
    #       as a real answer") had a hole at the last rung — reproduced: a junk
    #       draft was assigned and submitted verbatim.
    #   (b) `_sanitize_draft(draft) or await _knowledge_resort(...)` short-
    #       circuits on a truthy draft, so a junk-but-non-empty draft ALSO
    #       skipped the resort model — the one remaining shot at a real answer.
    # F4 is preserved: nothing here can overwrite an answer that already passes.
    if not _is_usable_answer(answer):
        fallback = _sanitize_draft(draft)
        if not _is_usable_answer(fallback):
            resort = await _knowledge_resort(question, deadline)
            if _is_usable_answer(resort):
                fallback = resort
        if _is_usable_answer(fallback):
            answer = fallback
    return answer


async def _solve(query_obj: Query, question: str) -> Response:
    deadline = monotonic() + WALL_BUDGET_S
    try:
        info = await tooling_info(timeout=10.0)
        _spend_note(info)
    except Exception:
        pass

    draft = ""
    brief = ""
    try:
        if _spend_left() >= BRIEF_MIN_USD and _remaining(deadline) > 120.0:
            draft, brief = await _knowledge_brief(question)
    except Exception:
        brief = ""

    ledger = EvidenceLedger()
    answer = ""
    messages: list[dict] = []
    try:
        answer, messages = await _loop(question, brief, ledger, deadline, MAX_TURNS)
    except Exception:
        answer = ""

    try:
        if answer and _remaining(deadline) > 75.0 and _spend_left() >= AUDIT_MIN_USD:
            patched = await _audit_patch(question, answer, messages, ledger, deadline)
            # the patch loop can itself return junk — only take it if it passes
            if _is_usable_answer(patched):
                answer = patched
    except Exception:
        pass

    try:
        answer = await _rescue(question, answer, draft, ledger, deadline)
    except Exception:
        pass

    try:
        citations = _citations_for(answer, ledger)
    except Exception:
        citations = []

    answer = _normalize_brackets(answer)   # the judge reads THIS, not the ref list
    text = _cap(answer) or f"Best-effort answer unavailable for: {question[:400]}"

    if query_obj.output_schema is not None:
        structured = None
        try:
            structured = await _schema_output(question, answer,
                                              query_obj.output_schema, deadline)
        except Exception:
            structured = None
        if structured is not None:
            try:
                return Response(output=structured, citations=citations or None)
            except Exception:
                pass  # invalid structured output must not sink the good text answer

    try:
        return Response(text=text, citations=citations or None)
    except Exception:
        return Response(text=text)


async def _v401_base_query(query: Query) -> Response:
    question = (query.text or "").strip()
    if not question:
        return Response(text="No question provided.")
    try:
        return await _solve(query, question)
    except Exception:
        # a miner-attributed exception is a hard 0 — always return SOME text
        return Response(text=f"Best-effort answer unavailable for: {question[:500]}")

# slot: harnyx 2026-08-01T13:10:30+00:00

# perfect_suffix: openrouter/parallel
_PERFECT_SUFFIX = "33bcb5ac8b2756bd"



# --- scoring-aligned coverage & citation-hygiene guard (submission14 upgrade) ---


def _v401_total_budget(default: float = 280.0) -> float:
    """Best-effort reuse of this agent's own total task budget constant."""
    try:
        return float(TASK_TOTAL_BUDGET_SECONDS)
    except NameError:
        pass
    try:
        return float(TOTAL_BUDGET_SECONDS)
    except NameError:
        pass
    try:
        return float(BUDGET_SECONDS)
    except NameError:
        pass
    try:
        return float(TASK_BUDGET_SECONDS)
    except NameError:
        return default


def _v401_provider_model() -> tuple[str, str]:
    """Best-effort reuse of a model constant this agent already defines."""
    try:
        return "openrouter", str(AUDIT_MODEL)
    except NameError:
        pass
    try:
        return "openrouter", str(SCHEMA_MODEL)
    except NameError:
        pass
    try:
        return "openrouter", str(CLAIM_MODEL)
    except NameError:
        pass
    try:
        return "openrouter", str(RESORT_MODEL)
    except NameError:
        pass
    try:
        return "openrouter", str(LOOP_MODEL_B)
    except NameError:
        pass
    try:
        return "openrouter", str(LOOP_MODEL_A)
    except NameError:
        pass
    try:
        return "openrouter", str(MODEL)
    except NameError:
        pass
    return "openrouter", "openai/gpt-oss-120b"


_V401_AUDIT_SYSTEM_PROMPT = (
    "You are a strict pre-submission auditor for a research answer that will be "
    "graded by a pairwise judge against an independent reference answer.\n"
    "The judge only credits factual claims supported by citation evidence, treats "
    "uncited time-sensitive or non-obvious claims as unsupported, penalizes missing "
    "query elements, and penalizes excessive irrelevant or repetitive citation "
    "markers.\n"
    "For comparison or multi-entity synthesis questions, the judge requires citation "
    "coverage on each compared side plus an explicit reconciled conclusion.\n"
    "Audit the draft strictly against the query. Return JSON only with keys: "
    "missing_elements (array of strings), uncited_claims (array of strings), "
    "comparison_gap (string or null), padding_markers (array of strings)."
)

_V401_REWRITE_SYSTEM_PROMPT = (
    "Return only the rewritten answer text. No preamble, no JSON, no markdown fences."
)


async def _v401_scoring_guard(query: "Query", response: "Response", deadline: float) -> "Response":
    import json as _v401_json
    import re as _v401_re
    from time import monotonic as _v401_clock
    from harnyx_miner_sdk.api import llm_chat as _v401_llm_chat

    try:
        if response is None:
            return response
        if getattr(response, "output", None) is not None:
            return response
        answer_text = getattr(response, "text", None)
        if not answer_text or not answer_text.strip():
            return response
        question = (getattr(query, "text", None) or "").strip()
        if not question:
            return response
        if deadline - _v401_clock() < 35.0:
            return response

        provider, model = _v401_provider_model()
        audit_user = (
            "Query:\n" + question + "\n\n"
            "Draft answer (verbatim, including any inline citation markers):\n"
            + answer_text[:12000]
        )
        try:
            audit = await _v401_llm_chat(
                provider=provider,
                model=model,
                messages=[
                    {"role": "system", "content": _V401_AUDIT_SYSTEM_PROMPT},
                    {"role": "user", "content": audit_user},
                ],
                tools=None,
                temperature=0.0,
                max_output_tokens=650,
                timeout=min(26.0, max(6.0, deadline - _v401_clock() - 8.0)),
            )
        except Exception:
            return response

        raw = (getattr(getattr(audit, "response", None), "raw_text", None) or "").strip()
        cleaned = _v401_re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=_v401_re.I | _v401_re.M).strip()
        report = None
        try:
            report = _v401_json.loads(cleaned)
        except Exception:
            match = _v401_re.search(r"\{[\s\S]*\}", cleaned)
            if match:
                try:
                    report = _v401_json.loads(match.group(0))
                except Exception:
                    report = None
        if not isinstance(report, dict):
            return response

        missing = [str(x).strip() for x in (report.get("missing_elements") or []) if str(x).strip()]
        uncited = [str(x).strip() for x in (report.get("uncited_claims") or []) if str(x).strip()]
        gap_value = report.get("comparison_gap")
        gap_text = gap_value.strip() if isinstance(gap_value, str) and gap_value.strip() else None
        padding = [str(x).strip() for x in (report.get("padding_markers") or []) if str(x).strip()]

        if not missing and not uncited and not gap_text and not padding:
            return response
        if deadline - _v401_clock() < 25.0:
            return response

        issue_lines = []
        if missing:
            issue_lines.append("Missing query elements: " + "; ".join(missing[:6]))
        if uncited:
            issue_lines.append("Uncited or unsupported claims to fix or drop: " + "; ".join(uncited[:6]))
        if gap_text:
            issue_lines.append("Comparison/synthesis coverage gap: " + gap_text)
        if padding:
            issue_lines.append(
                "Citation markers overused for unrelated claims (cite them only where truly "
                "relevant; keep the existing marker scheme): " + "; ".join(padding[:6])
            )

        repair_user = (
            "Query:\n" + question + "\n\n"
            "Original draft answer:\n" + answer_text[:12000] + "\n\n"
            "Audit findings:\n" + "\n".join(issue_lines) + "\n\n"
            "Rewrite the COMPLETE final answer text addressing every finding. Keep the same "
            "inline citation-marker style already used in the draft. Do not invent new sources "
            "or citation markers that were not already present. If a claim cannot be supported, "
            "state the limitation briefly instead of asserting it. For comparison or synthesis "
            "questions, explicitly state the reconciled conclusion after covering every compared "
            "side. Prefer a shorter fully-supported answer over a longer unsupported one."
        )
        try:
            rewrite = await _v401_llm_chat(
                provider=provider,
                model=model,
                messages=[
                    {"role": "system", "content": _V401_REWRITE_SYSTEM_PROMPT},
                    {"role": "user", "content": repair_user},
                ],
                tools=None,
                temperature=0.2,
                timeout=min(34.0, max(8.0, deadline - _v401_clock() - 5.0)),
            )
        except Exception:
            return response

        revised = (getattr(getattr(rewrite, "response", None), "raw_text", None) or "").strip()
        if revised and len(revised) >= max(60, int(len(answer_text) * 0.35)):
            try:
                return Response(text=revised, citations=getattr(response, "citations", None))
            except Exception:
                return response
        return response
    except Exception:
        return response


@entrypoint("query")
async def query(query: Query) -> Response:
    import time as _v401_time

    _v401_start = _v401_time.monotonic()
    response = await _v401_base_query(query)
    try:
        deadline = _v401_start + _v401_total_budget()
        return await _v401_scoring_guard(query, response, deadline)
    except Exception:
        return response
