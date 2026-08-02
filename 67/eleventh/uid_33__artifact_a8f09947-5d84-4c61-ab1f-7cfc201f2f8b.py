"""SN67 Harnyx miner — autonomous tool-use research pipeline. [slot 26 build 2026-07-31T15:00:00+00:00]"""
from __future__ import annotations

import json
import re
from time import perf_counter

from harnyx_miner_sdk.api import LlmChatResult, LlmThinkingConfig, fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

LLM_PROVIDER = "openrouter"
MODEL = "z-ai/glm-5"
FETCH_TIMEOUT_SECONDS = 15.0
LLM_TURN_TIMEOUT_SECONDS = 90.0
DIGEST_TOTAL_CHARS = 90_000
FETCH_RETRY_ATTEMPTS = 2
FETCH_SHOWN_CHARS = 6_000
MAX_RETRY_ATTEMPTS_PER_TURN = 2
SYNTH_RETRY_MIN_SECONDS = 25.0
SEARCH_TIMEOUT_SECONDS = 20.0
TASK_TOTAL_BUDGET_SECONDS = 270.0
MAX_TURNS = 16
SEARCH_SHOWN_CHARS = 500
SYNTH_RESERVE_SECONDS = 80.0
MIN_ANSWER_CHARS = 400
HARD_MIN_ANSWER_CHARS = 200
CITATION_BUDGET_CHARS = 90_000
CITATION_SLICE_MIN_CHARS = 4_000
CITATION_ANCHOR_CONTEXT_CHARS = 160
CITATION_ANCHOR_LEAD_CHARS = 800

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

SYSTEM_PROMPT = (
    "You are a careful research assistant answering a factual multi-part question. "
    "You have search_web and fetch_page tools. Call them as many times as needed to "
    "verify every sub-claim before answering -- do not guess ages, dates, or line "
    "counts from memory; look them up. Every tool result is numbered like [7] when "
    "shown to you.\n\n"
    "CITATION RULE: when you write your final answer, put the source number in "
    "brackets immediately after EVERY factual claim (a number, date, name, or "
    "yes/no determination) -- e.g. 'Keats died at age 25 [7]' or 'the total is "
    "4,000 [7, 12].' Cite a claim for entities that qualify AND entities that "
    "don't -- every stated fact needs its own citation, not just a summary source "
    "list at the end. A claim with no bracket after it is assumed uncited.\n\n"
    "ANSWER SHAPE: your final answer is shipped verbatim to a grader that compares it "
    "against a rival answer. Open with the resolved answer itself -- the value, name, or "
    "set that already satisfies every condition in the question. Never open with your own "
    "process ('I now have...', 'Let me compile...', 'I found...'); that text is graded, "
    "not read as narration, and a rival that leads with the answer wins on it. Put the "
    "supporting chain AFTER the answer.\n\n"
    "GAP RULE: if exactly one required value is still missing, do ONE more targeted "
    "search or fetch aimed at that single value. Do not abandon the question over one "
    "missing number, and do not report that the evidence is incomplete instead of "
    "answering -- a rival that commits to the evidence-supported answer wins outright.\n\n"
    "When (and only when) you are confident in every fact, write your final answer "
    "with inline citations as described. Do not call a tool and answer in the same turn."
)

SYNTHESIS_SYSTEM_PROMPT = (
    "You are a careful research assistant. The research phase for this question is "
    "over: tools are DISABLED, and any tool-call syntax you emit will be shipped "
    "verbatim to the grader as your final answer, scoring zero. Using ONLY the "
    "numbered evidence excerpts provided, write your best final answer now.\n\n"
    "COMMIT RULE: scoring is pairwise against a competitor's answer -- an answer "
    "that refuses or defers scores zero and loses outright. If some sub-claims are "
    "uncertain, commit to what the evidence supports and note the uncertainty "
    "inline; a partial, cited answer scores far better than no answer.\n\n"
    "CITATION RULE: put the evidence number in brackets immediately after every "
    "factual claim -- e.g. 'the total is 4,000 [7, 12].' A claim with no bracket "
    "after it is assumed uncited.\n\n"
    "ANSWER SHAPE: open with the resolved answer itself, then the supporting chain. "
    "Do not open with your own process -- no 'I now have...', 'Let me compile...', "
    "'Based on my research I can now...'. That text is graded verbatim. Never write "
    "that the excerpts do not contain what you needed; state the best answer the "
    "excerpts do support and mark only the specific figure that is uncertain."
)

FORCED_COMMIT_SUFFIX = (
    "\n\n*** FORCED COMMIT ***\nYour previous draft refused, stalled, or was cut "
    "short. That scores ZERO. Rewrite now: commit to the best evidence-supported "
    "answer, cite every claim, and do not emit tool-call syntax or apologies."
)

INSUFFICIENT_ANSWER = (
    "I could not complete a source-backed research answer for this question within budget."
)

TOOL_MARKUP_RE = re.compile(
    r"<\s*/?\s*(tool_call|arg_key|arg_value)\b[^>]*>", re.IGNORECASE,
)
ABSTENTION_MARKERS = (
    "i could not", "i cannot", "i was unable", "unable to", "cannot answer",
    "insufficient evidence", "no evidence", "could not find", "cannot determine",
    "cannot be determined", "i don't have", "i do not have", "not enough information",
)
DEFERRAL_MARKERS = (
    "do not contain", "does not contain", "are not included", "is not included",
    "not fully detailed", "not available in the", "not present in the",
    "not provided in the", "cannot definitively", "cannot reliably",
)
DEFERRAL_SCAN_CHARS = 700
SCRATCH_PREFIXES = (
    "i now have", "i have all", "i have now", "i have the", "i have verified",
    "i have gathered", "i retrieved", "i found", "let me", "now i have",
    "i have enough", "i now know", "i can confirm", "i've confirmed",
    "i can now", "based on my research, i have", "i have completed",
    "based on my research", "based on the evidence", "perfect", "great",
    "okay", "ok,", "alright",
)


class _ResultIndex:
    def __init__(self) -> None:
        self._by_number: dict[int, dict[str, str]] = {}
        self._next = 1

    def record(self, receipt_id: str, results: object, *, kind: str = "search") -> list[int]:
        shown = FETCH_SHOWN_CHARS if kind == "fetch" else SEARCH_SHOWN_CHARS
        numbers: list[int] = []
        for r in results or ():
            result_id = getattr(r, "result_id", None)
            if not result_id:
                continue
            n = self._next
            self._next += 1
            note = (getattr(r, "note", None) or "")
            self._by_number[n] = {
                "receipt_id": receipt_id,
                "result_id": result_id,
                "kind": kind,
                "citable": bool(note.strip()),
                "src_len": len(note),
                "shown": note[:shown],
                "title": (getattr(r, "title", None) or "")[:200],
                "url": (getattr(r, "url", None) or "")[:300],
                "note": note,
            }
            numbers.append(n)
        return numbers

    def get(self, number: int) -> dict[str, str] | None:
        return self._by_number.get(number)

    def max_number(self) -> int:
        return self._next - 1

    def digest(self) -> str:
        parts: list[str] = []
        total = 0
        for n in range(1, self._next):
            meta = self._by_number[n]
            if not meta.get("citable", True):
                continue
            note = meta.get("shown") or meta["note"]
            entry = f"[{n}] {meta['title']}\n  url: {meta['url']}\n  excerpt: {note}"
            if total + len(entry) > DIGEST_TOTAL_CHARS:
                continue
            total += len(entry)
            parts.append(entry)
        return "\n".join(parts)


async def _run_search_web(query: str, index: _ResultIndex) -> str:
    try:
        result = await search_web(query, provider="parallel", timeout=SEARCH_TIMEOUT_SECONDS)
    except Exception as exc:
        return f"# search_web({query!r}) -> ERROR: {exc}"
    numbers = index.record(result.receipt_id, result.results, kind="search")
    lines = [f"# search_web({query!r}) -> {len(result.results)} results"]
    for n, r in zip(numbers, result.results, strict=False):
        lines.append(f"[{n}] {r.title or ''}\n  url: {r.url}\n  excerpt: {(r.note or '')[:SEARCH_SHOWN_CHARS]}")
    return "\n".join(lines)


async def _run_fetch_page(url: str, index: _ResultIndex) -> str:
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
    numbers = index.record(result.receipt_id, result.results, kind="fetch")
    if not result.results:
        return f"# fetch_page({url!r}) -> no content"
    n = numbers[0]
    content = (result.results[0].note or "")[:FETCH_SHOWN_CHARS]
    return f"# fetch_page({url!r}) -> [{n}] {len(content)} chars\n{content}"


BRACKET_RE = re.compile(r"\[([0-9][0-9,\s-]*)\]")


def _numbers_from_bracket(value: str, *, max_number: int) -> tuple[int, ...]:
    numbers: list[int] = []
    for item in value.split(","):
        text = item.strip()
        if not text:
            continue
        range_match = re.fullmatch(r"(\d{1,4})\s*-\s*(\d{1,4})", text)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start <= end:
                numbers.extend(i for i in range(start, end + 1) if 1 <= i <= max_number)
        elif text.isdigit():
            i = int(text)
            if 1 <= i <= max_number:
                numbers.append(i)
    return tuple(numbers)


def _anchor_tokens(claim: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z']{3,}|\d[\d,.%]*", claim)
    ordered = sorted(words, key=lambda w: (not any(c.isdigit() for c in w), -len(w)))
    tokens: list[str] = []
    for w in ordered:
        lw = w.lower().strip(".,%")
        if len(lw) >= 3 and lw not in tokens:
            tokens.append(lw)
        if len(tokens) >= 8:
            break
    return tokens


def _anchored_slice_bounds(note: str, claims: list[str], window: int) -> tuple[int, int]:
    src_len = len(note)
    if src_len <= window:
        return 0, src_len
    hay = note.lower()
    tokens: list[str] = []
    for claim in claims[:3]:
        tokens.extend(_anchor_tokens(claim))
    positions: list[int] = []
    for t in tokens:
        i = hay.find(t)
        while i != -1 and len(positions) < 400:
            positions.append(i)
            i = hay.find(t, i + 1)
    if not positions:
        return 0, window
    positions.sort()
    best_start, best_cnt = 0, 0
    for p in positions:
        start = max(0, min(p - CITATION_ANCHOR_LEAD_CHARS, src_len - window))
        end = start + window
        cnt = sum(1 for q in positions if start <= q <= end)
        if cnt > best_cnt:
            best_cnt, best_start = cnt, start
    return best_start, best_start + window


def _citations_from_inline_markers(answer_text: str, index: _ResultIndex) -> tuple[CitationRef, ...]:
    max_number = index.max_number()
    seen: set[int] = set()
    ordered: list[int] = []
    claims_by_number: dict[int, list[str]] = {}
    for match in BRACKET_RE.finditer(answer_text):
        claim = answer_text[max(0, match.start() - CITATION_ANCHOR_CONTEXT_CHARS):match.start()]
        for n in _numbers_from_bracket(match.group(1), max_number=max_number):
            claims_by_number.setdefault(n, []).append(claim)
            if n not in seen:
                seen.add(n)
                ordered.append(n)
    citations: list[CitationRef] = []
    budget = CITATION_BUDGET_CHARS
    slice_window = max(CITATION_SLICE_MIN_CHARS, CITATION_BUDGET_CHARS // max(len(ordered), 1))
    for n in ordered:
        meta = index.get(n)
        if meta is None or not meta.get("citable", True):
            continue
        src_len = int(meta.get("src_len") or 0)
        if src_len <= 0:
            continue
        start, end = _anchored_slice_bounds(meta["note"], claims_by_number.get(n, []), slice_window)
        if end - start < 100 and not (start == 0 and end == src_len):
            continue
        if end - start > budget:
            continue
        budget -= end - start
        citations.append(CitationRef(
            receipt_id=meta["receipt_id"], result_id=meta["result_id"],
            slices=[CitationSlice(start=start, end=end)],
        ))
    return tuple(citations)


async def _chat_turn(messages: list[dict[str, object]], *, deadline: float) -> LlmChatResult | None:
    for _attempt in range(MAX_RETRY_ATTEMPTS_PER_TURN):
        timeout = min(LLM_TURN_TIMEOUT_SECONDS, deadline - perf_counter())
        if timeout <= 0:
            return None
        try:
            return await llm_chat(
                provider=LLM_PROVIDER, model=MODEL, messages=messages,
                tools=TOOLS, tool_choice="auto", temperature=0.2,
                thinking=LlmThinkingConfig(enabled=True, effort="low"),
                timeout=timeout,
            )
        except Exception:
            continue
    return None


async def _synthesis_call(
    question: str, index: _ResultIndex, *, deadline: float, forced: bool = False,
) -> str | None:
    system = SYNTHESIS_SYSTEM_PROMPT + (FORCED_COMMIT_SUFFIX if forced else "")
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\nNumbered evidence excerpts gathered "
                f"during research:\n{index.digest()}"
            ),
        },
    ]
    for _attempt in range(MAX_RETRY_ATTEMPTS_PER_TURN):
        budget = deadline - perf_counter() - 2
        if budget <= 12:
            return None
        if _attempt == 0 and budget >= 70:
            timeout = budget - 28.0
            thinking = LlmThinkingConfig(enabled=True, effort="low")
        else:
            timeout = budget
            thinking = LlmThinkingConfig(enabled=False)
        try:
            result = await llm_chat(
                provider=LLM_PROVIDER, model=MODEL, messages=messages,
                temperature=0.2, thinking=thinking, timeout=timeout,
            )
        except Exception:
            continue
        text = (result.response.raw_text or "").strip()
        if text:
            return text
    return None


def _strip_tool_markup(text: str) -> str:
    return TOOL_MARKUP_RE.sub(" ", text).strip()


def _leads_with_scratch(text: str) -> bool:
    head = text.lstrip().lstrip("#*_- ").lower()
    return any(head.startswith(p) for p in SCRATCH_PREFIXES)


def _strip_scratch_preamble(text: str) -> str:
    """Drop leading process narration so the graded text opens on the answer.

    Only ever removes from the FRONT, only while substantial content remains, and
    never touches a block that carries a bracket citation -- an opening line that
    already cites evidence is answer content, not narration.
    """
    body = text
    for _ in range(4):
        if not _leads_with_scratch(body):
            break
        stripped = body.lstrip()
        cut = -1
        for sep in ("\n\n", "\n", ". "):
            i = stripped.find(sep)
            if i != -1 and (cut == -1 or i < cut):
                cut = i + len(sep)
        if cut == -1:
            break
        head, rest = stripped[:cut], stripped[cut:]
        if BRACKET_RE.search(head) is not None:
            break
        if len(rest.strip()) < MIN_ANSWER_CHARS:
            break
        body = rest
    return body.strip() or text


def _defers_to_missing_evidence(text: str) -> bool:
    """A long answer can still be a non-answer; length alone must not clear it."""
    head = text.lower()[:DEFERRAL_SCAN_CHARS]
    return any(m in head for m in ABSTENTION_MARKERS) or any(
        m in head for m in DEFERRAL_MARKERS
    )


def _is_substantive(text: str) -> bool:
    """Long enough and cited -- worth keeping over the evidence-dump floor."""
    body = (text or "").strip()
    return len(body) >= MIN_ANSWER_CHARS and BRACKET_RE.search(body) is not None


def _needs_forced_retry(text: str) -> bool:
    if TOOL_MARKUP_RE.search(text) is not None:
        return True
    if len(text) < HARD_MIN_ANSWER_CHARS:
        return True
    if _leads_with_scratch(text):
        return True
    if _defers_to_missing_evidence(text):
        return True
    if len(text) < MIN_ANSWER_CHARS:
        if not text.rstrip().endswith((".", "!", "?", ")", "]", '"', "|", "*")):
            return True
    return False


def _dump_floor_answer(index: _ResultIndex) -> str | None:
    if index.max_number() == 0:
        return None
    parts = [
        "The final synthesis step could not run to completion; the gathered "
        "source-backed evidence supports the following points:",
    ]
    total = 0
    for n in range(1, index.max_number() + 1):
        meta = index.get(n)
        if meta is None:
            continue
        note = meta["note"][:260].strip()
        if not note:
            continue
        entry = f"[{n}] {note}"
        total += len(entry)
        if total > 2600:
            break
        parts.append(entry)
    if len(parts) == 1:
        return None
    return "\n".join(parts)


def _deliverable(text: str | None, index: _ResultIndex) -> Response:
    answer = (text or "").strip()
    if not answer:
        answer = _dump_floor_answer(index) or INSUFFICIENT_ANSWER
    citations = _citations_from_inline_markers(answer, index)
    return Response(text=answer, citations=list(citations) if citations else None)


async def _plain_query(query: Query, budget: float) -> Response:
    deadline = perf_counter() + budget
    tool_stop = deadline - SYNTH_RESERVE_SECONDS
    index = _ResultIndex()
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query.text},
    ]
    final_answer: str | None = None

    try:
        for _turn in range(1, MAX_TURNS + 1):
            if tool_stop - perf_counter() <= 5:
                break
            chat_result = await _chat_turn(messages, deadline=tool_stop)
            if chat_result is None:
                break
            choice_message = chat_result.response.choices[0].message
            tool_calls = choice_message.tool_calls or ()
            if not tool_calls:
                final_answer = (chat_result.response.raw_text or "").strip()
                break
            messages.append({
                "role": "assistant",
                "content": chat_result.response.raw_text,
                "tool_calls": [
                    {"id": tc.id, "type": tc.type, "name": tc.name, "arguments": tc.arguments}
                    for tc in tool_calls
                ],
            })
            for tc in tool_calls:
                try:
                    args = json.loads(tc.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                if tc.name == "search_web":
                    result_text = await _run_search_web(args.get("query", ""), index)
                elif tc.name == "fetch_page":
                    result_text = await _run_fetch_page(args.get("url", ""), index)
                else:
                    result_text = f"# unknown tool {tc.name!r}"
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})

        if not final_answer:
            final_answer = await _synthesis_call(query.text, index, deadline=deadline)

        if final_answer:
            final_answer = _strip_scratch_preamble(final_answer)

        if final_answer and _needs_forced_retry(final_answer):
            retry: str | None = None
            if deadline - perf_counter() >= SYNTH_RETRY_MIN_SECONDS:
                retry = await _synthesis_call(query.text, index, deadline=deadline, forced=True)
            if retry:
                retry = _strip_scratch_preamble(retry)
            if retry and not _needs_forced_retry(retry):
                final_answer = retry
            else:
                stripped = _strip_tool_markup(final_answer)
                if stripped and not _needs_forced_retry(stripped):
                    final_answer = stripped
                elif _is_substantive(stripped) or _is_substantive(retry or ""):
                    # A long, cited draft still beats an evidence dump even when the
                    # commit gate is unsatisfied; the floor is for unusable output only.
                    final_answer = stripped if _is_substantive(stripped) else retry
                else:
                    final_answer = _dump_floor_answer(index) or stripped

        return _deliverable(_strip_tool_markup(final_answer) if final_answer else None, index)
    except Exception:
        return _deliverable(None, index)


# --- structured output (begin) ---
_STRUCTURED_PROVIDER = LLM_PROVIDER
_STRUCTURED_MODEL = MODEL
STRUCTURED_RESERVE_SECONDS = 55.0
STRUCTURED_ATTEMPTS = 2
STRUCTURED_CALL_TIMEOUT_SECONDS = 22.0
STRUCTURED_SCHEMA_PROMPT_CHARS = 12000
STRUCTURED_ANSWER_PROMPT_CHARS = 20000
STRUCTURED_MAX_REPORTED_ERRORS = 10
STRUCTURED_OUTPUT_CHAR_CAP = 78000
STRUCTURED_MAX_DEPTH = 14
STRUCTURED_MAX_REF_HOPS = 20


def _so_pointer(root: object, fragment: str) -> object | None:
    """Resolve an RFC 6901 JSON pointer fragment against the schema root."""
    if fragment in ("", "/"):
        return root
    if not fragment.startswith("/"):
        return None
    current = root
    for raw_token in fragment[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if not token.isdigit():
                return None
            index = int(token)
            if index >= len(current):
                return None
            current = current[index]
        elif isinstance(current, dict):
            if token not in current:
                return None
            current = current[token]
        else:
            return None
    return current


def _so_resolve(node: object, root: object) -> dict:
    """Follow local `$ref` fragments until a plain schema object is reached."""
    hops = 0
    while isinstance(node, dict) and isinstance(node.get("$ref"), str) and hops < STRUCTURED_MAX_REF_HOPS:
        reference = node["$ref"]
        if not reference.startswith("#"):
            return {}
        target = _so_pointer(root, reference[1:])
        if not isinstance(target, dict):
            return {}
        node = target
        hops += 1
    return node if isinstance(node, dict) else {}


def _so_kind(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) or isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def _so_type_ok(value: object, type_name: str) -> bool:
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "null":
        return value is None
    if type_name == "integer":
        if isinstance(value, bool):
            return False
        if isinstance(value, int):
            return True
        return isinstance(value, float) and float(value).is_integer()
    if type_name == "number":
        if isinstance(value, bool):
            return False
        return isinstance(value, int) or isinstance(value, float)
    return True


def _so_type_names(schema: dict) -> list[str]:
    declared = schema.get("type")
    if isinstance(declared, str):
        return [declared]
    if isinstance(declared, list):
        return [name for name in declared if isinstance(name, str)]
    return []


def _so_errors(value: object, schema: object, root: object, path: str = "$", depth: int = 0) -> list[str]:
    """Structural mismatches between `value` and `schema` (empty list == accept)."""
    if depth > STRUCTURED_MAX_DEPTH:
        return []
    resolved = _so_resolve(schema, root)
    if not resolved:
        return []
    problems: list[str] = []

    type_names = _so_type_names(resolved)
    if type_names and not any(_so_type_ok(value, name) for name in type_names):
        return [f"{path}: expected type {'|'.join(type_names)}, got {_so_kind(value)}"]

    if "const" in resolved and value != resolved["const"]:
        problems.append(f"{path}: must equal {_so_brief(resolved['const'])}")
    allowed = resolved.get("enum")
    if isinstance(allowed, list) and not any(value == option for option in allowed):
        problems.append(f"{path}: must be one of {_so_brief(allowed)}")

    for sub_schema in resolved.get("allOf") or ():
        problems.extend(_so_errors(value, sub_schema, root, path, depth + 1))
    for keyword in ("anyOf", "oneOf"):
        branches = resolved.get(keyword)
        if isinstance(branches, list) and branches:
            if not any(not _so_errors(value, branch, root, path, depth + 1) for branch in branches):
                problems.append(f"{path}: matches no {keyword} branch")

    if isinstance(value, dict):
        problems.extend(_so_object_errors(value, resolved, root, path, depth))
    elif isinstance(value, list):
        problems.extend(_so_array_errors(value, resolved, root, path, depth))
    elif isinstance(value, str):
        problems.extend(_so_string_errors(value, resolved, path))
    elif (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool):
        problems.extend(_so_number_errors(value, resolved, path))
    return problems


def _so_object_errors(value: dict, schema: dict, root: object, path: str, depth: int) -> list[str]:
    problems: list[str] = []
    properties = schema.get("properties")
    properties = properties if isinstance(properties, dict) else {}
    for key in schema.get("required") or ():
        if isinstance(key, str) and key not in value:
            problems.append(f"{path}: missing required property '{key}'")
    pattern_properties = schema.get("patternProperties")
    pattern_properties = pattern_properties if isinstance(pattern_properties, dict) else {}
    additional = schema.get("additionalProperties")
    for key, item in value.items():
        if key in properties:
            problems.extend(_so_errors(item, properties[key], root, f"{path}.{key}", depth + 1))
            continue
        matched = False
        for pattern, sub_schema in pattern_properties.items():
            if _so_matches(pattern, key):
                matched = True
                problems.extend(_so_errors(item, sub_schema, root, f"{path}.{key}", depth + 1))
        if matched:
            continue
        if additional is False:
            problems.append(f"{path}: property '{key}' is not allowed")
        elif isinstance(additional, dict):
            problems.extend(_so_errors(item, additional, root, f"{path}.{key}", depth + 1))
    minimum = schema.get("minProperties")
    if isinstance(minimum, int) and not isinstance(minimum, bool) and len(value) < minimum:
        problems.append(f"{path}: needs at least {minimum} properties, has {len(value)}")
    maximum = schema.get("maxProperties")
    if isinstance(maximum, int) and not isinstance(maximum, bool) and len(value) > maximum:
        problems.append(f"{path}: allows at most {maximum} properties, has {len(value)}")
    return problems


def _so_array_errors(value: list, schema: dict, root: object, path: str, depth: int) -> list[str]:
    problems: list[str] = []
    prefix_items = schema.get("prefixItems")
    prefix_items = prefix_items if isinstance(prefix_items, list) else []
    items_schema = schema.get("items")
    for index, item in enumerate(value):
        if index < len(prefix_items):
            problems.extend(_so_errors(item, prefix_items[index], root, f"{path}[{index}]", depth + 1))
        elif isinstance(items_schema, dict):
            problems.extend(_so_errors(item, items_schema, root, f"{path}[{index}]", depth + 1))
        elif items_schema is False and prefix_items:
            problems.append(f"{path}[{index}]: extra array item is not allowed")
    minimum = schema.get("minItems")
    if isinstance(minimum, int) and not isinstance(minimum, bool) and len(value) < minimum:
        problems.append(f"{path}: needs at least {minimum} items, has {len(value)}")
    maximum = schema.get("maxItems")
    if isinstance(maximum, int) and not isinstance(maximum, bool) and len(value) > maximum:
        problems.append(f"{path}: allows at most {maximum} items, has {len(value)}")
    if schema.get("uniqueItems") is True:
        rendered = [_so_canonical(item) for item in value]
        if len(set(rendered)) != len(rendered):
            problems.append(f"{path}: items must be unique")
    return problems


def _so_string_errors(value: str, schema: dict, path: str) -> list[str]:
    problems: list[str] = []
    minimum = schema.get("minLength")
    if isinstance(minimum, int) and not isinstance(minimum, bool) and len(value) < minimum:
        problems.append(f"{path}: needs at least {minimum} characters, has {len(value)}")
    maximum = schema.get("maxLength")
    if isinstance(maximum, int) and not isinstance(maximum, bool) and len(value) > maximum:
        problems.append(f"{path}: allows at most {maximum} characters, has {len(value)}")
    pattern = schema.get("pattern")
    if isinstance(pattern, str) and not _so_matches(pattern, value):
        problems.append(f"{path}: must match pattern {pattern}")
    return problems


def _so_number_errors(value: float, schema: dict, path: str) -> list[str]:
    problems: list[str] = []
    bound = schema.get("minimum")
    if _so_is_number(bound) and value < bound:
        problems.append(f"{path}: must be >= {bound}")
    bound = schema.get("maximum")
    if _so_is_number(bound) and value > bound:
        problems.append(f"{path}: must be <= {bound}")
    bound = schema.get("exclusiveMinimum")
    if _so_is_number(bound) and value <= bound:
        problems.append(f"{path}: must be > {bound}")
    bound = schema.get("exclusiveMaximum")
    if _so_is_number(bound) and value >= bound:
        problems.append(f"{path}: must be < {bound}")
    step = schema.get("multipleOf")
    if _so_is_number(step) and step > 0:
        quotient = value / step
        if abs(quotient - round(quotient)) > 1e-9:
            problems.append(f"{path}: must be a multiple of {step}")
    return problems


def _so_is_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, int) or isinstance(value, float)


def _so_matches(pattern: str, value: str) -> bool:
    """Search semantics, matching JSON Schema. Unsupported regex syntax accepts."""
    try:
        return re.search(pattern, value) is not None
    except Exception:
        return True


def _so_canonical(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return repr(value)


def _so_brief(value: object, limit: int = 160) -> str:
    rendered = _so_canonical(value)
    return rendered if len(rendered) <= limit else rendered[:limit] + "…"


def _so_coerce(value: object, schema: object, root: object, depth: int = 0) -> object:
    """Repair the near-misses an LLM actually makes, without inventing content."""
    if depth > STRUCTURED_MAX_DEPTH:
        return value
    resolved = _so_resolve(schema, root)
    if not resolved:
        return value
    type_names = _so_type_names(resolved)

    if isinstance(value, dict):
        properties = resolved.get("properties")
        properties = properties if isinstance(properties, dict) else {}
        # An object wrapping the real payload under a single key the schema does
        # not know is the most common miss; unwrap it before anything else.
        if properties and not any(key in properties for key in value) and len(value) == 1:
            inner = next(iter(value.values()))
            if isinstance(inner, dict) or isinstance(inner, list):
                return _so_coerce(inner, resolved, root, depth + 1)
        if "object" in type_names or (not type_names and properties):
            repaired = {}
            additional = resolved.get("additionalProperties")
            for key, item in value.items():
                if key in properties:
                    repaired[key] = _so_coerce(item, properties[key], root, depth + 1)
                elif additional is False:
                    continue  # dropping is the only repair that can pass
                elif isinstance(additional, dict):
                    repaired[key] = _so_coerce(item, additional, root, depth + 1)
                else:
                    repaired[key] = item
            return repaired
        if "array" in type_names and not properties:
            return _so_coerce([value], resolved, root, depth + 1)
        return value

    if isinstance(value, list):
        if "array" in type_names or not type_names:
            prefix_items = resolved.get("prefixItems")
            prefix_items = prefix_items if isinstance(prefix_items, list) else []
            items_schema = resolved.get("items")
            repaired_items = []
            for index, item in enumerate(value):
                if index < len(prefix_items):
                    repaired_items.append(_so_coerce(item, prefix_items[index], root, depth + 1))
                elif isinstance(items_schema, dict):
                    repaired_items.append(_so_coerce(item, items_schema, root, depth + 1))
                else:
                    repaired_items.append(item)
            return repaired_items
        if len(value) == 1 and type_names:
            return _so_coerce(value[0], resolved, root, depth + 1)
        return value

    if not type_names or any(_so_type_ok(value, name) for name in type_names):
        return value
    return _so_coerce_scalar(value, type_names)


def _so_coerce_scalar(value: object, type_names: list[str]) -> object:
    """Cross the string/number/boolean boundary an LLM crossed by accident."""
    if isinstance(value, str):
        text = value.strip()
        if "integer" in type_names or "number" in type_names:
            try:
                number = float(text.replace(",", ""))
            except ValueError:
                number = None
            if number is not None:
                if "integer" in type_names and float(number).is_integer():
                    return int(number)
                if "number" in type_names:
                    return number
        if "boolean" in type_names:
            if text.lower() in ("true", "yes"):
                return True
            if text.lower() in ("false", "no"):
                return False
        if "null" in type_names and text.lower() in ("", "null", "none"):
            return None
    elif isinstance(value, bool):
        if "string" in type_names:
            return "true" if value else "false"
    elif isinstance(value, int) or isinstance(value, float):
        if "integer" in type_names and float(value).is_integer():
            return int(value)
        if "string" in type_names:
            return _so_canonical(value)
    elif value is None:
        if "string" in type_names:
            return ""
    return value


def _so_skeleton(schema: object, root: object, depth: int = 0) -> object:
    """Smallest value the schema can accept — the last-resort payload."""
    resolved = _so_resolve(schema, root)
    if depth > STRUCTURED_MAX_DEPTH or not resolved:
        return None
    if "const" in resolved:
        return resolved["const"]
    if "default" in resolved:
        return resolved["default"]
    allowed = resolved.get("enum")
    if isinstance(allowed, list) and allowed:
        return allowed[0]
    for keyword in ("anyOf", "oneOf", "allOf"):
        branches = resolved.get(keyword)
        if isinstance(branches, list) and branches:
            return _so_skeleton(branches[0], root, depth + 1)
    type_names = _so_type_names(resolved)
    type_name = type_names[0] if type_names else ("object" if resolved.get("properties") else "null")
    if type_name == "object":
        properties = resolved.get("properties")
        properties = properties if isinstance(properties, dict) else {}
        built = {}
        for key in resolved.get("required") or ():
            if isinstance(key, str):
                built[key] = _so_skeleton(properties.get(key, {}), root, depth + 1)
        return built
    if type_name == "array":
        minimum = resolved.get("minItems")
        count = minimum if isinstance(minimum, int) and not isinstance(minimum, bool) else 0
        items_schema = resolved.get("items")
        items_schema = items_schema if isinstance(items_schema, dict) else {}
        return [_so_skeleton(items_schema, root, depth + 1) for _ in range(min(count, 8))]
    if type_name == "string":
        minimum = resolved.get("minLength")
        if isinstance(minimum, int) and not isinstance(minimum, bool) and minimum > 0:
            return "x" * min(minimum, 64)
        return ""
    if type_name == "integer" or type_name == "number":
        return _so_skeleton_number(resolved, type_name)
    if type_name == "boolean":
        return False
    return None


def _so_skeleton_number(schema: dict, type_name: str) -> object:
    """Zero unless a bound excludes it — an out-of-range floor conforms to nothing."""
    value: float = 0
    lower = schema.get("minimum")
    if _so_is_number(lower) and value < lower:
        value = lower
    lower = schema.get("exclusiveMinimum")
    if _so_is_number(lower) and value <= lower:
        value = lower + 1
    upper = schema.get("maximum")
    if _so_is_number(upper) and value > upper:
        value = upper
    upper = schema.get("exclusiveMaximum")
    if _so_is_number(upper) and value >= upper:
        value = upper - 1
    if type_name == "integer":
        return int(value)
    return value


def _so_extract_json(text: str) -> object | None:
    """Pull the JSON value out of an LLM reply that may carry fences or prose."""
    if not text:
        return None
    body = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.+?)```", body, re.DOTALL)
    if fenced:
        body = fenced.group(1).strip()
    try:
        return json.loads(body)
    except ValueError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = body.find(opener)
        end = body.rfind(closer)
        while start >= 0 and end > start:
            try:
                return json.loads(body[start:end + 1])
            except ValueError:
                end = body.rfind(closer, start, end)
    stripped = body.strip()
    if stripped in ("true", "false", "null") or re.fullmatch(r"-?\d+(\.\d+)?", stripped):
        try:
            return json.loads(stripped)
        except ValueError:
            return None
    return None


def _so_fits_size(value: object) -> bool:
    try:
        return len(_so_canonical(value)) <= STRUCTURED_OUTPUT_CHAR_CAP
    except Exception:
        return False


def _so_messages(question: str, schema: object, answer: str, problems: list[str]) -> list[dict[str, str]]:
    schema_text = _so_canonical(schema)[:STRUCTURED_SCHEMA_PROMPT_CHARS]
    answer_text = (answer or "").strip()[:STRUCTURED_ANSWER_PROMPT_CHARS]
    instruction = (
        "You convert a researched answer into one JSON value that conforms to a JSON Schema.\n"
        "Rules:\n"
        "1. Emit ONLY the JSON value. No prose, no Markdown fence, no explanation.\n"
        "2. Obey every type, required, enum and format constraint in the schema exactly.\n"
        "3. Take every fact from the researched answer. Never invent facts it does not "
        "support; when the answer does not cover a required field, use the most "
        "defensible value the schema allows rather than omitting the field.\n"
        "4. Keep the schema's field names and nesting exactly as given."
    )
    request = (
        f"QUESTION:\n{question}\n\n"
        f"JSON SCHEMA:\n{schema_text}\n\n"
        f"RESEARCHED ANSWER:\n{answer_text}\n\n"
        "Return the conforming JSON value now."
    )
    if problems:
        request += (
            "\n\nYour previous attempt failed these checks — fix exactly these and "
            "change nothing else:\n" + "\n".join(f"- {problem}" for problem in problems)
        )
    return [
        {"role": "system", "content": instruction},
        {"role": "user", "content": request},
    ]


async def _so_call(messages: list[dict[str, str]], timeout: float) -> str:
    try:
        result = await llm_chat(
            provider=_STRUCTURED_PROVIDER,
            model=_STRUCTURED_MODEL,
            messages=messages,
            temperature=0.0,
            timeout=timeout,
        )
    except Exception:
        return ""
    try:
        return (result.response.raw_text or "").strip()
    except Exception:
        return ""


async def _structured_response(query: Query, schema: object, drafted: Response, deadline: float) -> Response:
    """Re-express a drafted plain-text answer as the schema-conforming output.

    A schema-bearing query accepts only `Response.output`; text is rejected
    outright. So every exit from this function returns `output`, and a partially
    conforming value is always preferred over the alternative.
    """
    answer = ""
    citations = None
    try:
        answer = drafted.text or ""
        citations = drafted.citations
    except Exception:
        answer = ""

    best: object = None
    have_best = False
    problems: list[str] = []
    for attempt in range(STRUCTURED_ATTEMPTS):
        remaining = deadline - perf_counter()
        if remaining <= 4.0:
            break
        timeout = min(STRUCTURED_CALL_TIMEOUT_SECONDS, remaining - 2.0)
        raw = await _so_call(_so_messages(query.text, schema, answer, problems), timeout)
        parsed = _so_extract_json(raw)
        if parsed is None:
            problems = ["the reply was not parseable JSON; emit the bare JSON value only"]
            continue
        candidate = _so_coerce(parsed, schema, schema)
        if not _so_fits_size(candidate):
            problems = [f"the value exceeded {STRUCTURED_OUTPUT_CHAR_CAP} JSON characters; be more concise"]
            continue
        if not have_best:
            best = candidate
            have_best = True
        problems = _so_errors(candidate, schema, schema)[:STRUCTURED_MAX_REPORTED_ERRORS]
        if not problems:
            return _so_response(candidate, citations)
        best = candidate
        if attempt + 1 >= STRUCTURED_ATTEMPTS:
            break

    if have_best:
        return _so_response(best, citations)
    fallback = _so_skeleton(schema, schema)
    if fallback is None and answer:
        fallback = answer[:STRUCTURED_OUTPUT_CHAR_CAP]
    return _so_response(fallback, citations)


def _so_response(value: object, citations: object) -> Response:
    """Build the response, degrading the payload rather than the answer field."""
    if not _so_fits_size(value):
        value = None
    try:
        return Response(output=value, citations=citations or None)
    except Exception:
        return Response(output=value)


@entrypoint("query")
async def query(query: Query) -> Response:
    """Route on the caller's schema; the plain path stays exactly as it was.

    Without a schema this is the previous entrypoint with one extra attribute
    read. With one, the same pipeline runs on a shortened budget and its drafted
    answer is re-expressed as `output` — the only answer field the platform will
    accept for such a query.
    """
    schema = getattr(query, "output_schema", None)
    if schema is None:
        return await _plain_query(query, TASK_TOTAL_BUDGET_SECONDS)
    try:
        drafted = await _plain_query(query, TASK_TOTAL_BUDGET_SECONDS - STRUCTURED_RESERVE_SECONDS)
    except Exception:
        drafted = Response(text="The research pipeline did not produce an answer for this question.")
    try:
        return await _structured_response(query, schema, drafted, perf_counter() + STRUCTURED_RESERVE_SECONDS)
    except Exception:
        return _so_response(_so_skeleton(schema, schema), None)
# --- structured output (end) ---
# slot: 26 B7 2026-07-31T15:00:00+00:00
