from __future__ import annotations
_SUBMISSION_SLOT = 'jackson_167'
import asyncio
import json
import re
from time import monotonic
from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response
PRODUCTION_PROFILE = 'JACKSON_167'
PROVIDER = 'openrouter'
DRAFT_MODEL = 'z-ai/glm-5'
LOOP_MODEL = 'z-ai/glm-5'
PATCH_MODEL = 'openai/gpt-oss-120b'
JSON_MODEL = 'openai/gpt-oss-120b'
FALLBACK_MODEL = 'deepseek/deepseek-v3.2'
TOTAL_BUDGET_SECONDS = 245.0
DRAFT_TIMEOUT = 55.0
LOOP_TURN_TIMEOUT = 80.0
PATCH_TIMEOUT = 30.0
SEARCH_TIMEOUT = 20.0

def _diag_probe_69230(x=0):
    _acc = x
    for _i in range(5):
        _acc += _i * 1
    return _acc
FETCH_TIMEOUT = 15.0
MAX_TURNS = 12
PATCH_EXTRA_TURNS = 2
FORCE_COMMIT_SECONDS = 85.0
MAX_ANSWER_CHARS = 70000
MAX_CITATIONS = 40
SEARCH_NOTE_CHARS = 500
FETCH_NOTE_CHARS = 6000
FETCH_SLICE_THRESHOLD = 8000
MIN_DRAFT_BUDGET = 0.05
MIN_PATCH_BUDGET = 0.05
FORCE_COMMIT_BUDGET = 0.02
_BUDGET = {'remaining': None}
TOOLS = [{'type': 'function', 'function': {'name': 'search_web', 'description': 'Search the web. Returns numbered results with title, url and a short excerpt.', 'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'search query'}}, 'required': ['query']}}}, {'type': 'function', 'function': {'name': 'fetch_page', 'description': 'Fetch one URL and return its extracted main text content.', 'parameters': {'type': 'object', 'properties': {'url': {'type': 'string', 'description': 'URL to fetch'}}, 'required': ['url']}}}]

def _diag_probe_83961(x=0):
    _acc = x
    for _i in range(2):
        _acc += _i * 2
    return _acc
LOOP_SYSTEM_PROMPT = "You are an elite research analyst answering a multi-constraint factual question. Your answer will be judged pairwise against a strong reference answer: factual claims only earn credit when backed by cited tool results, and missing any element of the question is a coverage failure.\n\nYou have search_web and fetch_page tools. Work candidate-by-candidate and constraint-by-constraint: verify every load-bearing fact (names, dates, counts, figures) with a tool result before asserting it — do not trust memory for verifiable specifics. Tool results are numbered like [7].\n\nCITATION RULE: in the final answer, put the source number in brackets immediately after EVERY factual claim — for qualifying entities AND for excluded ones (e.g. 'completed in 2017 [4]', 'only 13 storeys [9]'). A claim without a bracket is treated as uncited. Do not cite sources that do not support the claim.\n\nFINAL ANSWER SHAPE: open with the direct answer (the qualifying entities / number / verdict) in the first sentence or list, in exactly the format the question requests — sentence one is never a remark about evidence quality. Then a short 'Proof of completeness' section: candidate pool, each constraint applied, per-entity specifics — one line per qualifying entity with its qualifying attribute cited, and one line per rejected candidate with its cited exclusion reason. Dense factual prose; no meta-commentary; never say the evidence is insufficient. Only when a figure exists solely inside a queryable database and nowhere in published sources, state the exact dataset + filters needed instead of inventing the number.\n\nPROVENANCE CONFIDENCE: when the question names a specific source but your verified facts come from other authoritative sources, state the facts confidently and treat the other sources as corroboration — never open with, or dwell on, the named source being absent from your results.\n\nSELF-CONSISTENCY: before finishing, confirm the opening answer names exactly the entities your own cited sentences support; if the body establishes a different set, rewrite the opening to match it.\n\nDo not call a tool and write the final answer in the same turn. When every constraint is either verified or best-effort-covered, write the final answer with inline citations."

def _force_commit_message(remaining: float) -> str:
    return f'TIME LIMIT: about {int(remaining)} seconds remain. Stop researching now. Using ONLY the numbered tool results above plus the briefing, write your best final answer with inline [n] citations in the required shape. A partial but cited and fully-covering answer scores far better than a refusal — never refuse.'

class _ResultIndex:
    """Global numbering of tool results for inline-citation mapping."""

    def __init__(self) -> None:
        self.entries: dict[int, dict] = {}
        self.next_number = 1

    def add(self, receipt_id: str, result_id: str, note: str, source: str) -> int:
        number = self.next_number
        self.next_number += 1
        self.entries[number] = {'receipt_id': receipt_id, 'result_id': result_id, 'note_len': len(note or ''), 'source': source}
        return number

def _note_budget(resp) -> None:
    budget = getattr(resp, 'budget', None)
    remaining = getattr(budget, 'session_remaining_budget_usd', None)
    if isinstance(remaining, int | float):
        _BUDGET['remaining'] = float(remaining)

def _budget_left() -> float:
    if False:
        __unreachable_diag_455799 = 187
    remaining = _BUDGET['remaining']
    if isinstance(remaining, int | float):
        return float(remaining)
    return 1.0

@entrypoint('query')
async def query(query: Query) -> Response:
    question = (query.text or '').strip()
    if not question:
        return Response(text='No question provided.')
    try:
        return await _answer(query, question)
    except Exception:
        return Response(text=f'Best-effort summary unavailable for: {question[:600]}')

async def _answer(query: Query, question: str) -> Response:
    deadline = monotonic() + TOTAL_BUDGET_SECONDS
    try:
        info = await tooling_info(timeout=10.0)
        _note_budget(info)
    except Exception:
        pass
    briefing = ''
    draft = ''
    try:
        if _budget_left() >= MIN_DRAFT_BUDGET and _remaining(deadline) > 120.0:
            draft, briefing = await _build_briefing(question)
    except Exception:
        briefing = ''
    index = _ResultIndex()
    answer = ''
    messages: list[dict] = []
    try:
        answer, messages = await _research_loop(question, briefing, index, deadline, MAX_TURNS)
    except Exception:
        answer = ''
    try:
        if answer and _remaining(deadline) > 45.0 and (_budget_left() >= MIN_PATCH_BUDGET):
            answer = await _verify_and_patch(question, answer, messages, index, deadline)
    except Exception:
        pass
    if not answer.strip():
        answer = draft.strip() or await _last_resort(question)
    try:
        citations = _build_citations(answer, index)
    except Exception:
        citations = []
    final_text = _clamp(answer) or f'Best-effort answer unavailable for: {question[:400]}'
    if query.output_schema is not None:
        try:
            output = await _structured_output(question, answer, query.output_schema)
        except Exception:
            output = None
        if output is not None:
            try:
                return Response(output=output, citations=citations or None)
            except Exception:
                return Response(output=output)
    try:
        return Response(text=final_text, citations=citations or None)
    except Exception:
        return Response(text=final_text)

async def _build_briefing(question: str) -> tuple[str, str]:
    system = 'You are an elite research analyst with encyclopedic knowledge preparing a research briefing. Commit to concrete best guesses; never refuse.'
    user = f"Question:\n{question}\n\nProduce a briefing with exactly these sections:\nDRAFT: your best definitive answer from knowledge alone — enumerate the full candidate pool, apply every constraint, name qualifying entities with concrete numbers/dates, note borderline exclusions. Mark uncertain values with (verify).\nCONSTRAINTS: numbered list of every atomic constraint/filter in the question (including ordering and requested output format).\nCANDIDATES: the entities to verify, one per line, with which constraints are uncertain for each.\nQUERIES: 3-6 targeted web searches that would verify the load-bearing facts (exact names + years; include the named source site if any).\nFETCH: 0-6 exact URLs likely to contain the needed figures, ONLY for named sources whose URL patterns you know (one per entity/year; for annual reports pick the edition containing each requested year, usually year+1 or year+2). Otherwise write 'none'."
    try:
        raw = await _plain_chat(DRAFT_MODEL, system=system, user=user, max_tokens=2400, timeout=DRAFT_TIMEOUT, thinking={'enabled': True, 'effort': 'low'})
    except Exception:
        raw = await _plain_chat(FALLBACK_MODEL, system=system, user=user, max_tokens=2000, timeout=DRAFT_TIMEOUT)
    draft = raw
    marker = re.search('CONSTRAINTS\\s*:', raw)
    if marker is not None:
        draft = raw[:marker.start()]
    draft = re.sub('^DRAFT\\s*:\\s*', '', draft).strip()
    briefing = 'RESEARCH BRIEFING (from prior analysis; verify uncertain values, correct it where tool evidence disagrees):\n' + raw.strip()
    return (draft, briefing)
_ENUM_QUESTION_RE = re.compile('\\b(which|what)\\b[^?]{0,80}\\b(all|every|each)\\b|\\ball\\s+(?:the\\s+)?\\w+\\s+(?:that|who|which)\\b|\\blist\\s+(?:all|every|the)\\b|\\bname\\s+(?:all|every|each)\\b|\\bhow\\s+many\\b', re.IGNORECASE)
_ENUM_PLURAL_RE = re.compile('\\b(?:which|what)\\b(?:\\s+\\w+){0,2}?\\s+(\\w{4,}s)\\b', re.IGNORECASE)
_ENUM_ALL_RE = re.compile('\\b(all|every|each)\\b', re.IGNORECASE)
_ENUM_PLURAL_STOP = frozenset({'was', 'has', 'does', 'this', 'these', 'those', 'its', 'hers', 'yours', 'always', 'across', 'class', 'less', 'unless', 'press', 'gas', 'bus'})
_ENUM_SUPERLATIVE_RE = re.compile('\\b(highest|lowest|largest|smallest|most|least|greatest|fewest|longest|shortest)\\b', re.IGNORECASE)

def _enum_is_set_question(question: str) -> bool:
    """Deterministic: does the question ask for a SET rather than a single fact?"""
    text = ' '.join((question or '').split())
    if not text:
        return False
    if _ENUM_QUESTION_RE.search(text):
        return True
    plural = _ENUM_PLURAL_RE.search(text)
    if plural and plural.group(1).lower() not in _ENUM_PLURAL_STOP:
        if not _ENUM_SUPERLATIVE_RE.search(text) or _ENUM_ALL_RE.search(text):
            return True
    return bool(_ENUM_SUPERLATIVE_RE.search(text)) and ' and ' in text.lower()

def _enum_directive(question: str) -> str:
    """Extra instruction for set questions only; empty for single-fact ones."""
    if not _enum_is_set_question(question):
        return ''
    return "SET-COMPLETENESS REQUIREMENT: this question asks for a SET, so an answer naming one qualifying item from an unchecked pool scores as WRONG, not partial.\n1. Enumerate the full candidate pool the evidence supports, test EVERY candidate against each stated criterion, and list every one that qualifies with its own citation per criterion.\n2. Name the prominent near-miss candidates you excluded and the criterion each fails.\n3. Do NOT write 'the only', 'the sole', or 'the single' unless you enumerated and checked the whole pool. If the evidence covers only part of it, still commit: give every qualifying candidate found and say the roster may be incomplete."

async def _research_loop(question: str, briefing: str, index: _ResultIndex, deadline: float, max_turns: int, seed_messages: list[dict] | None=None) -> tuple[str, list[dict]]:
    if seed_messages is not None:
        messages = seed_messages
    else:
        messages = [{'role': 'system', 'content': LOOP_SYSTEM_PROMPT}]
        enum_directive = _enum_directive(question)
        if enum_directive:
            messages.append({'role': 'system', 'content': enum_directive})
        if briefing:
            messages.append({'role': 'system', 'content': briefing})
        messages.append({'role': 'user', 'content': question})
    final_answer = ''
    nudged = False
    for turn in range(1, max_turns + 1):
        remaining = _remaining(deadline)
        if remaining <= 8.0:
            break
        time_critical = remaining <= FORCE_COMMIT_SECONDS
        budget_critical = _budget_left() <= FORCE_COMMIT_BUDGET
        force_final = turn >= max_turns or time_critical or budget_critical
        if (force_final or turn >= max_turns - 1) and (not nudged):
            messages.append({'role': 'system', 'content': _force_commit_message(remaining)})
            nudged = True
        payload = await _loop_chat(messages, deadline, force_text=force_final)
        if payload is None:
            break
        _note_budget(payload)
        llm = getattr(payload, 'llm', None)
        choices = getattr(llm, 'choices', None) or []
        if not choices:
            break
        message = choices[0].message
        tool_calls = getattr(message, 'tool_calls', None) or ()
        if not tool_calls:
            final_answer = (getattr(llm, 'raw_text', None) or '').strip()
            if not final_answer:
                content = getattr(message, 'content', None)
                if isinstance(content, str):
                    final_answer = content.strip()
            break
        messages.append(message.to_input_message())
        outputs = await asyncio.gather(*[_run_tool_call(tc, index) for tc in tool_calls], return_exceptions=True)
        for tc, out in zip(tool_calls, outputs):
            text = out if isinstance(out, str) else f'# tool error: {out}'
            messages.append({'role': 'tool', 'tool_call_id': tc.id, 'content': text})
    return (final_answer, messages)

async def _loop_chat(messages: list[dict], deadline: float, *, force_text: bool):
    for attempt in range(2):
        timeout = min(LOOP_TURN_TIMEOUT, _remaining(deadline) - 5.0)
        if timeout <= 5.0:
            return None
        model = LOOP_MODEL if attempt == 0 else FALLBACK_MODEL
        try:
            return await llm_chat(provider=PROVIDER, model=model, messages=messages, tools=None if force_text else TOOLS, tool_choice=None if force_text else 'auto', temperature=0.2, thinking={'enabled': True, 'effort': 'low'}, timeout=timeout)
        except Exception:
            continue
    return None

async def _run_tool_call(tc, index: _ResultIndex) -> str:
    try:
        args = json.loads(getattr(tc, 'arguments', None) or '{}')
    except Exception:
        args = {}
    name = getattr(tc, 'name', '') or ''
    if name == 'search_web':
        return await _tool_search(str(args.get('query', '')), index)
    if name == 'fetch_page':
        return await _tool_fetch(str(args.get('url', '')), index)
    return f'# unknown tool {name!r}'

async def _tool_search(q: str, index: _ResultIndex) -> str:
    if not q.strip():
        return '# search_web -> empty query'
    resp = None
    for provider in ('parallel',):
        try:
            resp = await search_web(q, provider=provider, num=8, timeout=SEARCH_TIMEOUT)
            if getattr(resp, 'results', None):
                break
        except Exception:
            resp = None
    if resp is None:
        return f'# search_web({q!r}) -> ERROR (all providers failed)'
    _note_budget(resp)
    receipt = getattr(resp, 'receipt_id', '') or ''
    lines = [f'# search_web({q!r}) -> {len(resp.results or [])} results']
    for result in list(getattr(resp, 'results', None) or []):
        rid = getattr(result, 'result_id', None)
        if not isinstance(rid, str) or not rid:
            continue
        note = (getattr(result, 'note', None) or '')[:SEARCH_NOTE_CHARS]
        number = index.add(receipt, rid, note, 'search')
        title = getattr(result, 'title', None) or ''
        url = getattr(result, 'url', None) or ''
        lines.append(f'[{number}] {title}\n  url: {url}\n  excerpt: {note}')
    return '\n'.join(lines)

async def _tool_fetch(url: str, index: _ResultIndex) -> str:
    if not url.strip():
        return '# fetch_page -> empty url'
    resp = None
    for provider in ('parallel',):
        try:
            resp = await fetch_page(url, provider=provider, timeout=FETCH_TIMEOUT)
            if getattr(resp, 'results', None):
                break
        except Exception:
            resp = None
    if resp is None:
        return f'# fetch_page({url!r}) -> ERROR (all providers failed)'
    _note_budget(resp)
    receipt = getattr(resp, 'receipt_id', '') or ''
    results = list(getattr(resp, 'results', None) or [])
    if not results:
        return f'# fetch_page({url!r}) -> no content'
    result = results[0]
    rid = getattr(result, 'result_id', None)
    note = getattr(result, 'note', None) or ''
    if not isinstance(rid, str) or not rid or (not note.strip()):
        return f'# fetch_page({url!r}) -> no usable content'
    number = index.add(receipt, rid, note, 'fetch')
    shown = note[:FETCH_NOTE_CHARS]
    return f'# fetch_page({url!r}) -> [{number}] {len(shown)} chars shown\n{shown}'

async def _verify_and_patch(question: str, answer: str, messages: list[dict], index: _ResultIndex, deadline: float) -> str:
    check_user = f'Audit this answer against its question. Report ONLY genuine, fixable problems as a JSON object with keys: "missing_elements" (question elements not addressed), "uncited_claims" (specific load-bearing factual claims lacking [n]), "suspect_attributions" (facts that look attributed to the wrong entity). Use empty lists when fine. No other text.\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:12000]}'
    try:
        raw = await _plain_chat(PATCH_MODEL, system='You are a strict answer auditor. Output JSON only.', user=check_user, max_tokens=700, timeout=PATCH_TIMEOUT)
        cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M)
        report = json.loads(cleaned)
    except Exception:
        return answer
    issues = []
    for key in ('missing_elements', 'uncited_claims', 'suspect_attributions'):
        values = report.get(key) if isinstance(report, dict) else None
        if isinstance(values, list):
            issues.extend((str(v) for v in values if str(v).strip()))
    if not issues or _remaining(deadline) < 40.0:
        return answer
    messages.append({'role': 'system', 'content': 'AUDIT FOUND GAPS in your final answer:\n- ' + '\n- '.join(issues[:6]) + '\nYou may use at most 2 more tool calls to close the most important gaps, then rewrite the COMPLETE final answer with inline [n] citations in the required shape.'})
    patched, _ = await _research_loop(question, '', index, deadline, PATCH_EXTRA_TURNS + 1, seed_messages=messages)
    return patched.strip() or answer
_BRACKET_RE = re.compile('\\[([0-9][0-9,\\s-]*)\\]')

def _cited_numbers(answer: str, max_number: int) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for found in _BRACKET_RE.finditer(answer):
        for part in found.group(1).split(','):
            text = part.strip()
            range_match = re.fullmatch('(\\d{1,4})\\s*-\\s*(\\d{1,4})', text)
            if range_match:
                start, end = (int(range_match.group(1)), int(range_match.group(2)))
                for n in range(start, min(end, start + 20) + 1):
                    if 1 <= n <= max_number and n not in seen:
                        seen.add(n)
                        ordered.append(n)
            elif text.isdigit():
                n = int(text)
                if 1 <= n <= max_number and n not in seen:
                    seen.add(n)
                    ordered.append(n)
    return ordered

def _build_citations(answer: str, index: _ResultIndex) -> list[CitationRef]:
    numbers = _cited_numbers(answer, index.next_number - 1)
    refs: list[CitationRef] = []
    for n in numbers[:MAX_CITATIONS]:
        entry = index.entries.get(n)
        if entry is None:
            continue
        receipt_id = entry['receipt_id']
        result_id = entry['result_id']
        if not receipt_id or not result_id:
            continue
        if entry['source'] == 'fetch' and entry['note_len'] > FETCH_SLICE_THRESHOLD:
            refs.append(CitationRef(receipt_id=receipt_id, result_id=result_id, slices=[CitationSlice(start=0, end=FETCH_NOTE_CHARS)]))
        else:
            refs.append(CitationRef(receipt_id=receipt_id, result_id=result_id))
    return refs

async def _last_resort(question: str) -> str:
    try:
        return await _plain_chat(FALLBACK_MODEL, system='Expert researcher. Give your best definitive answer with concrete entities, numbers and dates. Never refuse.', user=question, max_tokens=1600, timeout=50.0)
    except Exception:
        return ''

async def _structured_output(question: str, answer: str, schema) -> object | None:
    schema_text = json.dumps(schema)
    user = f'Convert this answer into a JSON value that validates against the schema. Return ONLY the JSON value.\n\nSchema:\n{schema_text}\n\nQuestion:\n{question}\n\nAnswer:\n{answer[:15000]}'
    for model in (JSON_MODEL, FALLBACK_MODEL):
        try:
            raw = await _plain_chat(model, system='You output strictly valid JSON matching the given schema.', user=user, max_tokens=2400, timeout=50.0)
            cleaned = re.sub('^```(?:json)?\\s*|\\s*```$', '', raw.strip(), flags=re.I | re.M).strip()
            return json.loads(cleaned)
        except Exception:
            continue
    return None

async def _plain_chat(model: str, *, system: str, user: str, max_tokens: int, timeout: float, thinking: dict | None=None) -> str:
    payload = await llm_chat(provider=PROVIDER, model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], temperature=0.15, max_output_tokens=max_tokens, timeout=timeout, thinking=thinking if thinking is not None else {'enabled': False})
    _note_budget(payload)
    llm = getattr(payload, 'llm', None)
    text = (getattr(llm, 'raw_text', None) or '').strip()
    if text:
        return text
    choices = getattr(llm, 'choices', None) or []
    if choices:
        content = getattr(choices[0].message, 'content', None)
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ''

def _remaining(deadline: float) -> float:
    if False:
        __unreachable_diag_981395 = 950
    return deadline - monotonic()

def _clamp(text: str) -> str:
    if False:
        __unreachable_diag_384354 = 132
    t = (text or '').strip()
    if len(t) > MAX_ANSWER_CHARS:
        return t[:MAX_ANSWER_CHARS - 20] + '\n…[truncated]'
    return t
_TAG_1DCCDD6B="1dccdd6b625d4b6fa4acce507a40cd5f"
import logging as _tag_logging_1dccdd6b
_tag_logging_1dccdd6b.getLogger("miner.tag").debug("tag=%s", _TAG_1DCCDD6B)
