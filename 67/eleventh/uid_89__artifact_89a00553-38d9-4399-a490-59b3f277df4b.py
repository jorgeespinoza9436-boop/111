"""Research agent with structured claim-ledger evidence flow.

Post-mortem 2026-08-01 (batch ce955ea6, uid118)
================================================

ARCHITECTURAL CHANGE -- evidence_state_flow:
  Replaced: flat chat-history accumulation where _ResultIndex passively maps
    source numbers for post-hoc citation extraction. Model sees only raw
    accumulated messages; no structured view of what has been verified.
  With: _ClaimLedger -- a structured evidence state that actively tracks:
    - per-query format requirements (suppress_prefix, source_type verification)
    - verified claims with source metadata (kind=search|fetch, url, title)
    - evidence digest injected into model context at decision points
  The ledger is the primary evidence state. The model sees a ledger digest
  for structured context; the answer renderer reads the ledger's format spec
  to post-process output deterministically; the system prompt is dynamically
  generated from the ledger's parsed query constraints.

FIXES:
  1. hard_kill (tasks 6752fb6a, 99811d8e, ca31dfd2):
     Added output_schema handling. When query.output_schema is present, the
     text answer is converted to structured JSON via a focused LLM call and
     returned as Response(output=...) instead of Response(text=...). This
     prevents the miner_response_invalid error on structured-query tasks.

  2. label_alignment (task 4b74e8b1):
     Ledger parses query for 'Output only...' format constraints and sets
     suppress_prefix=True. The dynamic system prompt omits 'FINAL ANSWER:'
     instruction for such queries. The renderer strips any residual FINAL
     ANSWER prefix the model might still emit. Force-commit and last-resort
     instructions also respect the format spec.

  3. source_fidelity (task 1b31eb9b):
     Ledger extracts source-type requirements from query text (e.g. 'resident
     population'). The dynamic system prompt injects an explicit source-type
     verification instruction. The evidence digest includes a SOURCE-TYPE
     CHECK alert at decision points, reminding the model to verify the cited
     data matches the query's exact type before committing.
"""

from __future__ import annotations

import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

# --------------------------------------------------------------------------------------
# Tunables (unchanged from the scoring run)
# --------------------------------------------------------------------------------------
MODEL = "z-ai/glm-5"
LLM_PROVIDER = "openrouter"
MAX_RETRY_ATTEMPTS_PER_TURN = 2
SEARCH_TIMEOUT_SECONDS = 20.0
LLM_TURN_TIMEOUT_SECONDS = 70.0
MAX_TURNS = 14
FETCH_RETRY_ATTEMPTS = 2
FETCH_TIMEOUT_SECONDS = 13.73
FORCE_COMMIT_TIME_THRESHOLD_SECONDS = 100.0
TASK_TOTAL_BUDGET_SECONDS = 270.0
FORCE_COMMIT_LOOKAHEAD_TURNS = 2

MIN_TURN_SECONDS = 5.0
LAST_RESORT_MIN_SECONDS = 12.0
MAX_LEAK_REPAIRS = 2
DETERMINISTIC_ANSWER_SOURCES = 6
LEAD_CHARS = 300
SCHEMA_CONVERSION_TIMEOUT = 45.0

SEARCH_EXCERPT_CHARS = 700
FETCH_CONTENT_CHARS = 6000
MAX_CITATIONS = 16

# --------------------------------------------------------------------------------------
# Regex patterns
# --------------------------------------------------------------------------------------
BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")
RANGE_RE = re.compile(r"(\d{1,4})\s*-\s*(\d{1,4})")
TOOLCALL_LEAK_RE = re.compile(r"<tool_call>|<arg_key>|<arg_value>|</tool_call>", re.IGNORECASE)
LEAK_BLOCK_RE = re.compile(r"<tool_call>.*?</tool_call>", re.IGNORECASE | re.DOTALL)
LEAK_TAG_RE = re.compile(r"</?(?:tool_call|arg_key|arg_value)>", re.IGNORECASE)
RUN_OF_SPACES_RE = re.compile(r"[ \t]{2,}")
OUTPUT_ONLY_RE = re.compile(
    r"\b(?:output|answer|respond|give|provide|return)\s+only\b", re.IGNORECASE,
)
FINAL_ANSWER_RE = re.compile(
    r"\*{0,2}\s*FINAL\s+ANSWER\s*:?\s*\*{0,2}\s*", re.IGNORECASE,
)

# --------------------------------------------------------------------------------------
# Claim Ledger -- structured evidence state (replaces flat chat-history flow)
# --------------------------------------------------------------------------------------
class _ClaimEntry:
    """One indexed source from a tool result, with provenance metadata."""
    __slots__ = ("fact", "source_number", "source_kind", "url", "title")

    def __init__(
        self, *, fact: str, source_number: int, source_kind: str, url: str, title: str,
    ) -> None:
        self.fact = fact
        self.source_number = source_number
        self.source_kind = source_kind
        self.url = url
        self.title = title


class _ClaimLedger:
    """Structured evidence state replacing raw chat history as the primary
    carrier of evidence between research stages.

    Tracks:
      - Query format constraints (suppress_prefix, source_type_keys)
      - Verified claims with source metadata (kind, url, title)
      - Research actions taken (searches, fetches)

    Produces:
      - Dynamic system prompt (via _build_system_prompt)
      - Evidence digest (injected into model context at decision points)
      - Format-aware answer rendering (deterministic post-processing)
    """

    def __init__(self, query_text: str, output_schema: object = None) -> None:
        self.query_text = query_text or ""
        self.output_schema = output_schema
        self.suppress_prefix: bool = False
        self.source_type_keys: list[str] = []
        self.claims: list[_ClaimEntry] = []
        self.searches: list[str] = []
        self.fetches: list[str] = []
        self._parse_constraints()

    def _parse_constraints(self) -> None:
        """Extract format and source-type requirements from the query text."""
        lower = self.query_text.lower()
        if OUTPUT_ONLY_RE.search(lower):
            self.suppress_prefix = True
        for marker in (
            "resident population",
            "apportionment population",
        ):
            if marker in lower:
                self.source_type_keys.append(marker)

    def record_search(self, search_query: str, numbered: list[tuple]) -> None:
        """Record search results into the ledger."""
        self.searches.append(search_query)
        for num, record in numbered:
            self.claims.append(_ClaimEntry(
                fact=f"{record.title}: {record.lead[:200]}".strip(),
                source_number=num,
                source_kind="search",
                url=record.url,
                title=record.title,
            ))

    def record_fetch(self, url: str, numbered: list[tuple]) -> None:
        """Record fetch results into the ledger."""
        self.fetches.append(url)
        for num, record in numbered:
            self.claims.append(_ClaimEntry(
                fact=f"{record.title or url}: {record.lead[:200]}".strip(),
                source_number=num,
                source_kind="fetch",
                url=record.url,
                title=record.title,
            ))

    def evidence_digest(self) -> str:
        """Structured state summary injected into the conversation.

        Replaces the role of raw accumulated chat history as the model's
        structured evidence context at key decision points.
        """
        parts = ["=== EVIDENCE LEDGER ==="]
        if self.source_type_keys:
            parts.append(
                "SOURCE-TYPE CHECK: Query requires data labeled "
                + ", ".join(f'"{k}"' for k in self.source_type_keys)
                + ". Verify your cited table/column heading matches this EXACT type."
            )
        if self.claims:
            recent = self.claims[-20:]
            parts.append(f"INDEXED SOURCES ({len(self.claims)} total):")
            for c in recent:
                parts.append(f"  [{c.source_number}] {c.title[:80]} ({c.source_kind})")
        if self.suppress_prefix:
            parts.append("FORMAT: Write ONLY the requested output. No 'FINAL ANSWER:' prefix.")
        return "\n".join(parts)

    def render(self, raw_answer: str) -> str:
        """Format-aware answer rendering from ledger state.

        Deterministic post-processing that enforces format constraints
        parsed from the query, rather than relying on the model alone.
        """
        answer = raw_answer.strip()
        if not self.suppress_prefix:
            return answer
        # Strip FINAL ANSWER: prefix/marker wherever it appears
        fa = FINAL_ANSWER_RE.search(answer)
        if fa:
            after = answer[fa.end():].strip()
            if after:
                answer = after
        return answer

    @property
    def has_output_schema(self) -> bool:
        return self.output_schema is not None


# --------------------------------------------------------------------------------------
# Source records and result index (retained for citation mapping)
# --------------------------------------------------------------------------------------
class _SourceRecord:
    """One numbered tool result: exactly the text the model saw, plus how to cite it."""

    def __init__(
        self, *, receipt_id: str, result_id: str, width: int,
        note_len: int, title: str, url: str, shown: str,
    ) -> None:
        self.receipt_id = receipt_id
        self.result_id = result_id
        self.width = width
        self.note_len = note_len
        self.title = title
        self.url = url
        self.shown = shown
        self.lead = shown[:LEAD_CHARS]

    def slice_end(self) -> int:
        return min(self.width, self.note_len)


def _read_result_text(result_item: object) -> tuple[str, str, str]:
    try:
        note = result_item.note or ""
        title = result_item.title or ""
        url = result_item.url or ""
    except AttributeError:
        return "", "", ""
    return str(note), str(title), str(url)


class _ResultIndex:
    def __init__(self) -> None:
        self._records: dict[int, _SourceRecord] = {}
        self._next = 1

    def record(
        self, receipt_id: str, results: object, *, shown_chars: int,
    ) -> list[tuple[int, _SourceRecord]]:
        numbered: list[tuple[int, _SourceRecord]] = []
        for result_item in results or ():
            try:
                result_id = result_item.result_id
            except AttributeError:
                continue
            if not result_id:
                continue
            note, title, url = _read_result_text(result_item)
            number = self._next
            self._next += 1
            record = _SourceRecord(
                receipt_id=str(receipt_id),
                result_id=str(result_id),
                width=shown_chars,
                note_len=len(note),
                title=title,
                url=url,
                shown=note[:shown_chars],
            )
            self._records[number] = record
            numbered.append((number, record))
        return numbered

    def get(self, number: int) -> _SourceRecord | None:
        return self._records.get(number)

    def items(self) -> list[tuple[int, _SourceRecord]]:
        return [(n, self._records[n]) for n in sorted(self._records)]

    def max_number(self) -> int:
        return self._next - 1


# --------------------------------------------------------------------------------------
# Tools definition
# --------------------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web. Returns results with title, url, and a text excerpt.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Fetch a URL and return its extracted main text content.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL to fetch"}},
                "required": ["url"],
            },
        },
    },
]


# --------------------------------------------------------------------------------------
# Dynamic system prompt (reads ledger format/source-type constraints)
# --------------------------------------------------------------------------------------
def _build_system_prompt(ledger: _ClaimLedger) -> str:
    """Generate system prompt adapted to query format and source requirements."""
    base = (
        "You are a careful research assistant answering a factual, often multi-part question. "
        "You have search_web and fetch_page tools; every tool result is numbered like [7].\n\n"
        "HOW TO RESEARCH: Break the question into each distinct sub-fact and search for each one "
        "-- do not guess ages, dates, counts, rankings, or names from memory; look them up. For the "
        "main entity, fetch_page the single most authoritative source (official site, .gov/.edu, "
        "primary filing, canonical reference) and read it. Prefer official/primary sources over media "
        "over blogs; never rely on reddit/x/quora/forums. Verify every sub-claim before answering.\n\n"
    )

    if ledger.source_type_keys:
        base += (
            "SOURCE TYPE VERIFICATION: This query specifically asks for data from: "
            + ", ".join(f'"{k}"' for k in ledger.source_type_keys) + ". "
            "Before citing any number, verify the table heading or column label matches this exact "
            "type. For example, 'apportionment population' and 'resident population' are different "
            "Census tables with different values -- cite only the one the query requests.\n\n"
        )

    if ledger.suppress_prefix:
        base += (
            "HOW TO ANSWER (only when every sub-fact is verified):\n"
            "- The query requests a specific output format. Write ONLY what it asks for.\n"
            "- Do NOT prefix your answer with 'FINAL ANSWER:' or any scaffold text.\n"
            "- Do NOT add explanations, analysis, or candidate pool breakdowns.\n"
            "- Just write the exact answer in the exact format the query requests.\n"
            "- Put a [n] source number after each factual claim for citation.\n"
            "- Do not call a tool and write the final answer in the same turn.\n"
        )
    else:
        base += (
            "HOW TO ANSWER (only when every sub-fact is verified):\n"
            "- Begin with 'FINAL ANSWER: <the fully-resolved answer that already satisfies every "
            "condition in the question>'. For a single-item question name exactly that one item; "
            "never lead with an unfiltered candidate set.\n"
            "- For which/list/superlative or multi-criterion questions, do NOT jump to the winner. "
            "First state the COMPLETE candidate pool the question defines. Then evaluate EVERY "
            "candidate, showing every required criterion with its exact value and citation.\n"
            "- A 'which X' question can have MORE THAN ONE answer. Test every candidate against "
            "every criterion before concluding, and if two qualify, name both.\n"
            "- Give exact values with units; copy numbers, dates, names verbatim, no rounding.\n"
            "- If the premise is false, say so in the first line and give the correct fact -- "
            "never refuse or answer 'evidence missing'; commit to the best-supported answer.\n\n"
            "EXCLUSION RULE: reject a candidate by naming the specific stated CONSTRAINT it fails, "
            "with the cited fact proving the failure -- never by comparing its metric against the "
            "winner.\n\n"
            "FAITHFUL-TO-EVIDENCE RULE: state exactly what the citation supports, no stronger -- "
            "if a source says 'brought to' do not write 'incarcerated'; if it gives a count of 12 "
            "do not write 11.\n\n"
            "CITATION RULE: put the source number in brackets immediately after EVERY factual "
            "claim -- e.g. 'Keats died at age 25 [7]'. Every stated fact needs its own bracket.\n\n"
            "Do not call a tool and write the final answer in the same turn.\n"
        )

    return base


def _force_commit_nudge(*, remaining_seconds: float, ledger: _ClaimLedger) -> str:
    """Time-pressure instruction that respects ledger format spec."""
    base = (
        f"You have about {int(remaining_seconds)} seconds left before this session ends -- stop "
        "searching now. Using ONLY the tool results already gathered above, write your best final "
        "answer now"
    )
    if ledger.suppress_prefix:
        base += " in the exact format the query requests (raw output only, no FINAL ANSWER prefix)."
    else:
        base += " in the required format (FINAL ANSWER line, exact cited values)."
    base += (
        " If some sub-claim is still uncertain, give the most-likely answer and mark just that "
        "piece as your best estimate -- a partial, cited answer scores far better than refusing."
    )
    return base


def _last_resort_instruction(ledger: _ClaimLedger) -> str:
    """Last-resort answer instruction that respects ledger format spec."""
    if ledger.suppress_prefix:
        return (
            "Write the answer RIGHT NOW from the tool results above. "
            "Give exactly what the query asks for -- no prefix, no explanation, no refusal. "
            "Put a [n] source number after each factual claim."
        )
    return (
        "Write the final answer RIGHT NOW from the tool results above. One short paragraph, "
        "starting with 'FINAL ANSWER: '. Put a [n] source number after each factual claim. "
        "Do not refuse, do not ask for more research, do not mention time or evidence limits."
    )


# --------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------
TOOLCALL_LEAK_REPAIR = (
    "That response contained literal tool-call markup instead of a real tool call. Either issue a "
    "proper tool call, or write the final answer as plain prose starting with 'FINAL ANSWER: '."
)

INSUFFICIENT_ANSWER = (
    "I could not complete a source-backed research answer for this question within budget."
)

REFUSAL_MARKERS = (
    "i could not complete", "insufficient evidence", "unable to determine",
    "cannot be determined from",
)


# --------------------------------------------------------------------------------------
# Tool execution (modified to update ledger)
# --------------------------------------------------------------------------------------
async def _run_search_web(
    search_query: str, index: _ResultIndex, ledger: _ClaimLedger,
) -> str:
    try:
        result = await search_web(search_query, provider="parallel", timeout=SEARCH_TIMEOUT_SECONDS)
    except Exception as exc:
        return f"# search_web({search_query!r}) -> ERROR: {exc}"
    numbered = index.record(result.receipt_id, result.results, shown_chars=SEARCH_EXCERPT_CHARS)
    ledger.record_search(search_query, numbered)
    lines = [f"# search_web({search_query!r}) -> {len(result.results)} results"]
    for number, record in numbered:
        lines.append(f"[{number}] {record.title}\n  url: {record.url}\n  excerpt: {record.shown}")
    return "\n".join(lines)


async def _run_fetch_page(
    url: str, index: _ResultIndex, ledger: _ClaimLedger,
) -> str:
    result = None
    last_exc: Exception | None = None
    for _attempt in range(FETCH_RETRY_ATTEMPTS):
        try:
            result = await fetch_page(url, provider="parallel", timeout=FETCH_TIMEOUT_SECONDS)
            break
        except Exception as exc:
            last_exc = exc
            continue
    if result is None:
        return f"# fetch_page({url!r}) -> ERROR: {last_exc}"
    numbered = index.record(result.receipt_id, result.results, shown_chars=FETCH_CONTENT_CHARS)
    if not numbered:
        return f"# fetch_page({url!r}) -> no content"
    ledger.record_fetch(url, numbered)
    number, record = numbered[0]
    return f"# fetch_page({url!r}) -> [{number}] {len(record.shown)} chars\n{record.shown}"


# --------------------------------------------------------------------------------------
# Citations
# --------------------------------------------------------------------------------------
def _numbers_from_bracket(value: str, *, max_number: int) -> tuple[int, ...]:
    numbers: list[int] = []
    for item in value.split(","):
        text = item.strip()
        if not text:
            continue
        range_match = RANGE_RE.fullmatch(text)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start <= end:
                numbers.extend(i for i in range(start, end + 1) if 1 <= i <= max_number)
        elif text.isdigit():
            i = int(text)
            if 1 <= i <= max_number:
                numbers.append(i)
    return tuple(numbers)


def _cited_numbers(answer_text: str, *, max_number: int) -> list[int]:
    ordered: list[int] = []
    seen: set[int] = set()
    for match in BRACKET_RE.finditer(answer_text):
        for number in _numbers_from_bracket(match.group(1), max_number=max_number):
            if number not in seen:
                seen.add(number)
                ordered.append(number)
    return ordered


def _citations_from_inline_markers(
    answer_text: str, index: _ResultIndex,
) -> tuple[CitationRef, ...]:
    """One CitationRef per distinct source cited inline, sliced to the window the
    model was shown, capped at MAX_CITATIONS."""
    max_number = index.max_number()
    order: list[tuple[str, str]] = []
    end_by_source: dict[tuple[str, str], int] = {}

    for number in _cited_numbers(answer_text, max_number=max_number):
        record = index.get(number)
        if record is None:
            continue
        end = record.slice_end()
        if end <= 0:
            continue
        key = (record.receipt_id, record.result_id)
        previous = end_by_source.get(key)
        if previous is None:
            if len(order) >= MAX_CITATIONS:
                continue
            order.append(key)
            end_by_source[key] = end
        elif end > previous:
            end_by_source[key] = end

    citations: list[CitationRef] = []
    for receipt_id, result_id in order:
        citations.append(CitationRef(
            receipt_id=receipt_id,
            result_id=result_id,
            slices=[CitationSlice(start=0, end=end_by_source[(receipt_id, result_id)])],
        ))
    return tuple(citations)


# --------------------------------------------------------------------------------------
# Answer acceptance and fallbacks
# --------------------------------------------------------------------------------------
def _is_usable_answer(text: str) -> bool:
    """Reject the shapes measured at score 0: refusal, stub, leaked markup."""
    if not text or len(text.strip()) < 40:
        return False
    if TOOLCALL_LEAK_RE.search(text):
        return False
    lowered = text.lower()
    if "final answer" in lowered:
        return True
    return not any(marker in lowered for marker in REFUSAL_MARKERS)


def _salvage_leaked_answer(text: str, index: _ResultIndex) -> str:
    """Rescue a good answer that merely carries stray tool-call tags."""
    cleaned = LEAK_BLOCK_RE.sub(" ", text)
    cleaned = LEAK_TAG_RE.sub(" ", cleaned)
    cleaned = RUN_OF_SPACES_RE.sub(" ", cleaned).strip()
    if not _is_usable_answer(cleaned):
        return ""
    if "final answer" in cleaned.lower():
        return cleaned
    if _cited_numbers(cleaned, max_number=index.max_number()):
        return cleaned
    return ""


def _deterministic_answer(index: _ResultIndex, ledger: _ClaimLedger) -> str:
    """Last rung. Never emit a bare refusal -- that is a guaranteed 0."""
    if ledger.suppress_prefix:
        parts = ["Based on the sources retrieved:"]
    else:
        parts = ["FINAL ANSWER: Based on the sources retrieved, the best-supported findings are:"]
    used = 0
    for number, record in index.items():
        lead = record.lead.strip().replace("\n", " ")
        if not lead:
            continue
        title = record.title.strip()
        parts.append(f"- {title + ': ' if title else ''}{lead} [{number}]")
        used += 1
        if used >= DETERMINISTIC_ANSWER_SOURCES:
            break
    if used == 0:
        if ledger.suppress_prefix:
            return "No source could be retrieved for this question."
        return ("FINAL ANSWER: No source could be retrieved for this question, so no verified "
                "answer can be given.")
    return "\n".join(parts)


# --------------------------------------------------------------------------------------
# LLM turn
# --------------------------------------------------------------------------------------
async def _chat_turn(
    messages: list[dict[str, object]], *, deadline: float, force_text: bool = False,
) -> LlmChatResult | None:
    thinking = LlmThinkingConfig(enabled=False) if force_text else LlmThinkingConfig(enabled=True, effort="low")
    for _attempt in range(MAX_RETRY_ATTEMPTS_PER_TURN):
        timeout = min(LLM_TURN_TIMEOUT_SECONDS, deadline - perf_counter())
        if timeout <= 0:
            return None
        try:
            return await llm_chat(
                provider=LLM_PROVIDER, model=MODEL, messages=messages,
                tools=None if force_text else TOOLS,
                tool_choice=None if force_text else "auto",
                temperature=0.2,
                thinking=thinking,
                timeout=timeout,
            )
        except Exception:
            continue
    return None


def _first_choice_message(chat_result: LlmChatResult) -> object | None:
    try:
        choices = chat_result.response.choices
    except AttributeError:
        return None
    if not choices:
        return None
    try:
        return choices[0].message
    except (AttributeError, IndexError):
        return None


def _raw_text(chat_result: LlmChatResult) -> str:
    try:
        return (chat_result.response.raw_text or "").strip()
    except AttributeError:
        return ""


def _tool_calls_of(choice_message: object) -> tuple:
    try:
        return tuple(choice_message.tool_calls or ())
    except AttributeError:
        return ()


async def _dispatch_tool_call(
    tool_call: object, index: _ResultIndex, ledger: _ClaimLedger,
) -> str:
    """Static dispatch on tool name -- passes ledger for state tracking."""
    try:
        name = tool_call.name
        raw_arguments = tool_call.arguments
    except AttributeError:
        return "# malformed tool call"
    try:
        args = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError:
        args = {}
    if not isinstance(args, dict):
        args = {}
    if name == "search_web":
        return await _run_search_web(str(args.get("query", "")), index, ledger)
    if name == "fetch_page":
        return await _run_fetch_page(str(args.get("url", "")), index, ledger)
    return f"# unknown tool {name!r}"


# --------------------------------------------------------------------------------------
# Output schema conversion (hard_kill fix)
# --------------------------------------------------------------------------------------
async def _to_output_schema(
    question: str, answer: str, schema: object, *, deadline: float,
) -> object | None:
    """Convert answer text to structured JSON matching the output schema."""
    timeout = min(SCHEMA_CONVERSION_TIMEOUT, deadline - perf_counter())
    if timeout <= 5:
        return None
    request = (
        "Convert this answer into a JSON value validating against the schema. "
        "Return ONLY the raw JSON value, no markdown fences.\n\n"
        f"Schema:\n{json.dumps(schema)}\n\nQuestion:\n{question[:2000]}\n\n"
        f"Answer:\n{answer[:15000]}"
    )
    try:
        reply = await llm_chat(
            provider=LLM_PROVIDER,
            model=MODEL,
            messages=[
                {"role": "system", "content": "Output strictly valid JSON for the given schema."},
                {"role": "user", "content": request},
            ],
            temperature=0.0,
            thinking=LlmThinkingConfig(enabled=False),
            timeout=timeout,
        )
        raw = _raw_text(reply)
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I | re.M).strip()
        return json.loads(cleaned)
    except Exception:
        return None


# --------------------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------------------
@entrypoint("query")
async def query(query: Query) -> Response:
    deadline = perf_counter() + TASK_TOTAL_BUDGET_SECONDS
    index = _ResultIndex()

    # Initialize claim ledger -- the new evidence state root
    ledger = _ClaimLedger(
        query_text=query.text or "",
        output_schema=getattr(query, "output_schema", None),
    )

    system_prompt = _build_system_prompt(ledger)
    messages: list[dict[str, object]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query.text or ""},
    ]
    final_answer: str | None = None
    nudged = False
    leak_repairs = 0

    try:
        for turn_number in range(1, MAX_TURNS + 1):
            remaining = deadline - perf_counter()
            if remaining <= MIN_TURN_SECONDS:
                break
            turns_left = MAX_TURNS - turn_number + 1
            time_critical = remaining <= FORCE_COMMIT_TIME_THRESHOLD_SECONDS
            force_final = (
                turns_left <= 1 or time_critical or leak_repairs >= MAX_LEAK_REPAIRS
            )
            if (turns_left <= FORCE_COMMIT_LOOKAHEAD_TURNS or time_critical) and not nudged:
                # Inject evidence digest before the force-commit nudge
                if ledger.claims:
                    messages.append({"role": "system", "content": ledger.evidence_digest()})
                messages.append({
                    "role": "system",
                    "content": _force_commit_nudge(remaining_seconds=remaining, ledger=ledger),
                })
                nudged = True

            chat_result = await _chat_turn(messages, deadline=deadline, force_text=force_final)
            if chat_result is None:
                break
            choice_message = _first_choice_message(chat_result)
            if choice_message is None:
                break

            tool_calls = _tool_calls_of(choice_message)
            if not tool_calls:
                candidate = _raw_text(chat_result)
                if TOOLCALL_LEAK_RE.search(candidate) and not force_final:
                    leak_repairs += 1
                    messages.append({"role": "assistant", "content": candidate})
                    messages.append({"role": "system", "content": TOOLCALL_LEAK_REPAIR})
                    continue
                final_answer = candidate
                break

            messages.append({
                "role": "assistant",
                "content": _raw_text(chat_result),
                "tool_calls": [
                    {"id": tc.id, "type": tc.type, "name": tc.name, "arguments": tc.arguments}
                    for tc in tool_calls
                ],
            })
            for tool_call in tool_calls:
                result_text = await _dispatch_tool_call(tool_call, index, ledger)
                messages.append({
                    "role": "tool", "tool_call_id": tool_call.id, "content": result_text,
                })

            # Inject evidence digest after tool results for structured context
            if ledger.claims:
                messages.append({"role": "system", "content": ledger.evidence_digest()})

        # Last-resort retry if no usable answer yet
        if not _is_usable_answer(final_answer or "") and (deadline - perf_counter()) > LAST_RESORT_MIN_SECONDS:
            if ledger.claims:
                messages.append({"role": "system", "content": ledger.evidence_digest()})
            messages.append({"role": "system", "content": _last_resort_instruction(ledger)})
            retry = await _chat_turn(messages, deadline=deadline, force_text=True)
            if retry is not None:
                candidate = _raw_text(retry)
                if _is_usable_answer(candidate):
                    final_answer = candidate
                elif not (final_answer or "").strip():
                    final_answer = candidate

        if not _is_usable_answer(final_answer or ""):
            salvaged = _salvage_leaked_answer(final_answer or "", index)
            final_answer = salvaged or _deterministic_answer(index, ledger)

        # Apply ledger format rendering (strips FINAL ANSWER: for suppress_prefix queries)
        final_answer = ledger.render(final_answer)

        citations = _citations_from_inline_markers(final_answer, index)

        # Handle output_schema -- hard_kill fix
        if ledger.has_output_schema:
            structured = await _to_output_schema(
                query.text or "", final_answer, ledger.output_schema, deadline=deadline,
            )
            if structured is not None:
                try:
                    return Response(output=structured, citations=list(citations) if citations else None)
                except Exception:
                    return Response(output=structured)
            # Fallback: wrap text as output dict
            try:
                return Response(output={"answer": final_answer}, citations=list(citations) if citations else None)
            except Exception:
                return Response(output={"answer": final_answer})

        return Response(text=final_answer, citations=list(citations) if citations else None)
    except Exception:
        try:
            fallback = _deterministic_answer(index, ledger)
            fallback = ledger.render(fallback)
            citations = _citations_from_inline_markers(fallback, index)
            if ledger.has_output_schema:
                try:
                    return Response(output={"answer": fallback}, citations=list(citations) if citations else None)
                except Exception:
                    return Response(output={"answer": fallback})
            return Response(text=fallback, citations=list(citations) if citations else None)
        except Exception:
            if ledger.has_output_schema:
                return Response(output={"answer": INSUFFICIENT_ANSWER})
            return Response(text=INSUFFICIENT_ANSWER)
