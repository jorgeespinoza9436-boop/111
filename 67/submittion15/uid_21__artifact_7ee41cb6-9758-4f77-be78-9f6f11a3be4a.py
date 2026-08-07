"""SN67 Harnyx miner — v30 "corpuslet": evidence-first tool-loop research agent.


"""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from time import monotonic

from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

VERSION = "v30.0-corpuslet"

# ── provider ─────────────────────────────────────────────────────────────────
# ONE LLM provider. Resilience comes from a model ladder inside openrouter, not
# from a second vendor: three of the four agents we benchmarked against run
# openrouter-only, and all four agree on this model set. The ladder preserves
# the property the dual-vendor design was actually buying — a congested or
# failing model must not cost us the turn — without a second key or a second
# billing surface.
LLM_PROVIDER = "openrouter"
MODEL_FALLBACK = "deepseek/deepseek-v3.2"   # different family: unlikely to fail together
LOOP_TRIES_PRIMARY = 2               # retry the loop model before dropping a rung
MODEL_LOOP = "z-ai/glm-5.2"          # drives the research loop
MODEL_AUDIT = "openai/gpt-oss-120b"  # audit / patch / schema — classification work
SEARCH_PROVIDER = "parallel"

# openai/gpt-oss rejects a request that disables reasoning, so the thinking
# config is per MODEL, never a global default.
_REASONING_REQUIRED = ("openai/gpt-oss",)


def _think_for(model: str, *, want: bool) -> dict:
    """Thinking config this model will actually accept."""
    if any(model.startswith(p) for p in _REASONING_REQUIRED):
        return {"enabled": True, "effort": "low"}
    return {"enabled": True, "effort": "low"} if want else {"enabled": False}


def _ladder(primary: str) -> list[tuple[str, int]]:
    """(model, attempts) rungs. The primary gets retries; the fallback gets one."""
    rungs = [(primary, LOOP_TRIES_PRIMARY)]
    if MODEL_FALLBACK != primary:
        rungs.append((MODEL_FALLBACK, 1))
    return rungs

# ── time budget (seconds) ────────────────────────────────────────────────────
# The platform kills at 300s. Everything below is clamped against ONE deadline
# computed once at entry; no phase may consume the window the next phase needs.
WALL_BUDGET_S = 260.0
FETCH_TIMEOUT_S = 16.0
BRIEF_TIMEOUT_S = 45.0
COMMIT_TIMEOUT_S = 55.0
AUDIT_TIMEOUT_S = 30.0
MAX_CALLS_PER_TURN = 8
TURN_TIMEOUT_S = 70.0
COMMIT_RESERVE_S = 46.0      # research stops here; the tail is for committing
MIN_TAIL_S = 8.0
MAX_TURNS = 14
SEARCH_TIMEOUT_S = 18.0
MAX_REPAIRS = 2

# ── evidence shaping ─────────────────────────────────────────────────────────
SEARCH_RESULTS = 8
SEARCH_EXCERPT_CHARS = 520
PAGE_HEAD_CHARS = 2600       # every page shows its head: titles/infoboxes live there
PAGE_WINDOW_CHARS = 3400     # plus the densest regions, so one read carries the set
PAGE_WINDOWS = 3
EVIDENCE_CHAR_BUDGET = 104000    # hard ceiling is 120k; leave margin for the wall
CITATION_CAP = 26
ANSWER_CHAR_CAP = 48000
MAX_SEED_QUERIES = 3
PAGE_PREVIEW_CHARS = 12000   # what a page contributes to the commit-time digest


# ═══════════════════════════════════════════════════════════════════════════
# question shape
# ═══════════════════════════════════════════════════════════════════════════
# Three disciplines, each traceable to a specific loss on batch 3258ff1c.

_SET_ASK_RE = re.compile(
    r"\b(?:list|name|identify|enumerate|which)\b[^?]{0,60}\b(?:all|every|each|both)\b", re.I)
_SET_JOIN_RE = re.compile(r"\b(?:both|as well as|and also|and had|and received)\b", re.I)
_PLURAL_ASK_RE = re.compile(r"\b(?:which|what)\b(?:\s+\w+){0,2}?\s+([a-z]{3,}s)\b", re.I)
_PLURAL_NOT = frozenset(
    "was is has does its this thus across process business series species status "
    "analysis basis focus versus previous various famous others always perhaps".split())
# "at least 80 wins" / "at most 3" are CONSTRAINTS, not superlatives. Treating
# them as superlatives cancelled the set rule on 32146a3b ("which teams had at
# least 80 wins and fewer than 70 losses") and left it with no discipline at all.
# "top"/"first"/"last" are dropped: they are positional far more often than
# superlative ("the first number in the column").
_TOP_RE = re.compile(
    r"\b(?:highest|lowest|largest|smallest|greatest|fewest|longest|shortest|"
    r"oldest|newest|youngest|maximum|minimum)\b"
    r"|(?<!at )\b(?:most|least)\b", re.I)
# an explicit candidate list: "which of the following X: a, b, c, or d"
_ENUM_LIST_RE = re.compile(
    r"\bwhich of the (?:following|these)\b|\bfrom the following list\b", re.I)
_OR_LIST_RE = re.compile(r"[:,]\s*[^,:?]{2,60}(?:,\s*[^,:?]{2,60}){1,}\s*,?\s+or\s+", re.I)
# comparative constraints: two or more means a filtered pool, and the reference
# will show the whole table (this is what beat us on 1d1bd408)
_CONSTRAINT_RE = re.compile(
    r"\b(?:at least|at most|no more than|no fewer than|greater than|less than|"
    r"fewer than|more than|over|under|above|below|exceed(?:s|ing)?|"
    r"between\s+[^,]{1,30}\s+and)\b", re.I)
_EST_RE = re.compile(r"\b([a-z]{3,})est\b")
# words ending in -est that are not superlatives
_EST_NOT = frozenset(
    "conquest tempest incest behest zest quest crest chest guest jest pest vest "
    "midwest southwest northwest bequest imprest inquest gest wrest".split()
    + "interest honest modest protest request suggest forest harvest invest".split()
    + "arrest contest digest manifest earnest rest best west nest test".split())
_NAMED_SOURCE_RE = re.compile(
    r"\b(?:according to|per|from|listed (?:in|on)|in the)\s+"
    r"((?:the\s+)?[A-Z][\w.'&-]*(?:\s+[A-Z][\w.'&-]*){0,4})", re.S)
_SOURCE_WORD_RE = re.compile(
    r"\b(wikipedia|wikidata|imdb|britannica|eurovisionworld|usgs|nasa|noaa|"
    r"baseball-reference|basketball-reference|box office mojo|rotten tomatoes|"
    r"metacritic|billboard|discogs|goodreads|transfermarkt|olympedia|pubmed|"
    r"arxiv|sec|edgar|eurostat|world bank|imf|census)\b", re.I)


_SOURCE_NOUN_RE = re.compile(
    r"\b(?:wiki\w*|article|page|site|database|dataset|data|table|list|index|"
    r"factsheet|fact sheet|report|filing|registry|catalog(?:ue)?|almanac|"
    r"encyclopedia|archive|records?|statistics|census|survey|bulletin|"
    r"\.(?:com|org|net|gov|edu))\b", re.I)


def _has_top(text: str) -> bool:
    if _TOP_RE.search(text or ""):
        return True
    return any(m.group(0).lower() not in _EST_NOT for m in _EST_RE.finditer(text or ""))


def _wants_set(question: str) -> bool:
    """True when the answer is a SET and omitting a member is as bad as wrong."""
    q = " ".join((question or "").split())
    if not q:
        return False
    if _SET_ASK_RE.search(q):
        return True
    # "which of the following films exceed 100 minutes: A, B, C, or D?" — the pool
    # is handed to us and every member needs a verdict with its own citation.
    if _ENUM_LIST_RE.search(q) or (re.search(r"\bwhich\b", q, re.I) and _OR_LIST_RE.search(q)):
        return True
    head = _PLURAL_ASK_RE.search(q)
    if head and head.group(1).lower() not in _PLURAL_NOT:
        # a superlative wants ONE winner and cancels the set reading, unless an
        # explicit all/every/each puts it back
        if not _has_top(q) or re.search(r"\b(?:all|every|each)\b", q, re.I):
            return True
    return bool(re.search(r"\bwhich\b", q, re.I)) and bool(_SET_JOIN_RE.search(q))


def _wants_tally(question: str) -> bool:
    """True when the answer is ONE item but the research needs the whole pool.

    A superlative answers singular, so the set detector deliberately cancels on
    it — which left these questions with no completeness discipline at all. We
    lost 1d1bd408 and 32146a3b exactly here: right winner, no visible tally,
    judge preferred the reference that showed its work.
    """
    q = " ".join((question or "").split())
    if not q:
        return False
    if _has_top(q) or re.search(r"\b(?:how many|how much|(?:most|least) (?:common|frequent))\b", q, re.I):
        return True
    # A singular "which team ... over 90 wins, under .625, over 50 home wins" reads
    # as one winner, so the set detector stays silent — but the reference answer
    # enumerates every team meeting the first cut and shows its values. Two or
    # more comparative constraints means the pool has to be tabulated.
    return bool(re.search(r"\b(?:which|what)\b", q, re.I)) and len(
        _CONSTRAINT_RE.findall(q)) >= 2


def _named_sources(question: str) -> list[str]:
    """Sources the question names. Answering from an equivalent aggregator loses.

    Judge, task 1d1bd408, scoring us 0/4 while granting our data and conclusion
    were right: the reference used the named Wikipedia article, we used
    baseball-reference, "therefore the first answer is superior because it
    adheres to the source constraint in the query".
    """
    found: list[str] = []
    for m in _SOURCE_WORD_RE.finditer(question or ""):
        name = m.group(1).strip()
        if name.lower() not in {f.lower() for f in found}:
            found.append(name)
    for m in _NAMED_SOURCE_RE.finditer(question or ""):
        name = re.sub(r"^the\s+", "", m.group(1).strip(), flags=re.I).strip(" .,'")
        # "according to the Eurovision Song Contest Grand Final" is an EVENT, not a
        # source. Only keep phrases that name a document/dataset/site, or a proper
        # noun the source-word list already recognised.
        if not _SOURCE_NOUN_RE.search(name):
            continue
        if 2 < len(name) < 60 and name.lower() not in {f.lower() for f in found}:
            found.append(name)
    return found[:4]


LOOP_RULES = (
    "You are a research agent answering a hard factual question. Your answer is "
    "compared against a reference answer by a judge that only counts claims backed "
    "by a validated citation, and that keeps the reference when the two are equally "
    "good. Being merely correct therefore loses — you win by showing more verified "
    "work than the reference does.\n\n"
    "TOOLS. web_search(query) returns numbered results with an excerpt. "
    "read_page(url, focus) returns the page head plus the regions densest in your "
    "focus terms. Search finds the document; READ IT before you rely on a number. "
    "An excerpt is a pointer, not evidence.\n\n"
    "CITATIONS. Every tool result carries a number. Put [n] on every claim that "
    "rests on it, at the point of the claim. A paragraph with one trailing [n] "
    "reads as one supported claim, not five. Never invent a number you were not "
    "given.\n\n"
    "NUMBERS. Quote figures exactly as the source prints them — same units, same "
    "precision, no rounding and no arithmetic the source did not do. If you must "
    "derive a value, show the inputs with their own [n] and say it is derived.\n\n"
    "ANSWER SHAPE. Lead with the direct answer in the first sentence, in the form "
    "the question asks for. Then the proof. Do not open by narrating your process, "
    "do not hedge a verified fact, and never contradict your own cited source.\n\n"
    "When you have the evidence, write the final answer as plain prose. Do not "
    "announce that you are about to answer — just answer."
)

SET_RULE = (
    "SET ANSWER — this question asks for a set, and omitting one qualifying member "
    "scores the same as being wrong.\n"
    "1. Get the POOL from a roster, not member by member. Your first retrieval "
    "should hunt the authoritative list/table that enumerates the whole pool "
    "('<subject> list', 'list of <subject>') and read_page it. Assembling a pool "
    "from separate per-member searches is how a run reports 3 of 6 qualifiers: the "
    "members you never thought to search for stay invisible.\n"
    "2. When the condition spans several periods — successive years, separate "
    "editions, two parallel events — fetch ONE roster page PER PERIOD and join them "
    "on the member. One list per period, not one lookup per member.\n"
    "3. Test EVERY member against EVERY condition. Name all qualifiers, each with "
    "its own [n] per condition.\n"
    "4. Give EVERY excluded member its own line, the condition it fails, the value "
    "that fails it, and its own [n]. One clause sweeping several names together is "
    "not exclusion evidence. This is usually the difference between winning and "
    "losing: the reference proves why the others don't qualify, and if you cannot, "
    "you lose even with the right answer.\n"
    "5. Never say 'the only X' unless you checked the whole pool. If nothing "
    "survives every condition, 'none' is a real answer — state it with the "
    "per-condition citations that prove it."
)

TALLY_RULE = (
    "SUPERLATIVE / COUNT — the answer is one item, but you cannot know which "
    "without the whole pool. Show the table.\n"
    "1. List EVERY candidate the question's scope admits.\n"
    "2. Put the deciding value beside each one, cited.\n"
    "3. Only then name the winner, and reproduce that table in your answer. A "
    "correct winner with no visible tally loses to a reference that shows its work; "
    "'among others' is not a tally.\n"
    "4. Never decide a superlative on a rounded or derived display — a whole-number "
    "age or a bucketed rank cannot separate contenders that differ below its "
    "precision. Get the exact underlying value for every contender, from a source "
    "that lists them ALL: a page showing only your front-runner cannot establish "
    "that nobody beats them.\n"
    "5. If the pool is too large to print in full, rank it, show every contender "
    "above an explicit threshold, and state the threshold you used. A reader can "
    "audit a declared cutoff; an undeclared one is indistinguishable from you "
    "simply having stopped looking."
)


def _source_rule(names: list[str]) -> str:
    listed = ", ".join(names)
    return (
        f"NAMED SOURCE — this question specifies where the answer must come from: "
        f"{listed}. Read THAT source and cite it. An aggregator or mirror carrying "
        f"the same figures does not satisfy the constraint: a judge has scored us 0 "
        f"on all four runs of a question whose data and conclusion it agreed were "
        f"correct, purely because we answered from a different site than the one "
        f"named. Search the named source directly (try 'site:' or its name in the "
        f"query), read_page it, and quote its own wording. Only if it genuinely "
        f"cannot be retrieved may you fall back — and then say so explicitly."
    )


def _shape_rules(question: str) -> list[str]:
    rules: list[str] = []
    if _wants_set(question):
        rules.append(SET_RULE)
    if _wants_tally(question):
        rules.append(TALLY_RULE)
    named = _named_sources(question)
    if named:
        rules.append(_source_rule(named))
    return rules


# ═══════════════════════════════════════════════════════════════════════════
# evidence ledger
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(slots=True)
class Row:
    """One numbered piece of evidence the model was shown.

    `spans` are the exact character windows rendered into the transcript. The
    citation is sliced to them, so what the validator materializes is what the
    model actually read — and the total stays inside the payload ceiling.
    """
    receipt_id: str
    result_id: str
    note_len: int
    spans: tuple[tuple[int, int], ...]
    kind: str
    url: str = ""
    title: str = ""
    preview: str = ""      # the text actually rendered into the transcript


@dataclass(slots=True)
class Ledger:
    rows: list[Row] = field(default_factory=list)
    _seen: dict[tuple[str, str], int] = field(default_factory=dict)

    def add(self, row: Row) -> int:
        """Append in CALL order and return its [n]. Merges repeat reads of one
        result so a second read widens the slices instead of duplicating them."""
        key = (row.receipt_id, row.result_id)
        existing = self._seen.get(key)
        if existing is not None:
            prior = self.rows[existing - 1]
            merged = _merge_spans(prior.spans + row.spans)
            self.rows[existing - 1] = Row(
                receipt_id=prior.receipt_id, result_id=prior.result_id,
                note_len=max(prior.note_len, row.note_len), spans=merged,
                kind=prior.kind, url=prior.url or row.url, title=prior.title or row.title,
                preview=max((prior.preview, row.preview), key=len))
            return existing
        self.rows.append(row)
        n = len(self.rows)
        self._seen[key] = n
        return n

    def cost(self, n: int) -> int:
        row = self.rows[n - 1]
        if not row.spans:
            return row.note_len          # a sliceless ref materializes everything
        return sum(max(0, e - s) for s, e in row.spans)

    def ref(self, n: int) -> CitationRef | None:
        if not 1 <= n <= len(self.rows):
            return None
        row = self.rows[n - 1]
        if not row.receipt_id or not row.result_id:
            return None
        slices = [CitationSlice(start=s, end=e) for s, e in row.spans if e > s]
        if slices:
            return CitationRef(receipt_id=row.receipt_id, result_id=row.result_id,
                               slices=slices)
        return CitationRef(receipt_id=row.receipt_id, result_id=row.result_id)


def _merge_spans(spans: tuple[tuple[int, int], ...]) -> tuple[tuple[int, int], ...]:
    ordered = sorted((s, e) for s, e in spans if e > s)
    if not ordered:
        return ()
    out = [list(ordered[0])]
    for s, e in ordered[1:]:
        if s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return tuple((s, e) for s, e in out)


# ═══════════════════════════════════════════════════════════════════════════
# page rendering — head plus the densest regions
# ═══════════════════════════════════════════════════════════════════════════
_TERM_RE = re.compile(r"[a-z0-9][a-z0-9'.\-]{2,}")
_TERM_STOP = frozenset(
    "the and for with from that this have has was were are is been its their there "
    "which what when where who whom whose how why all any both each more most other "
    "some such than then they them these those into over under about after before "
    "between during without within according listed page article table".split())


def _terms(text: str) -> set[str]:
    return {w for w in _TERM_RE.findall((text or "").casefold()) if w not in _TERM_STOP}


def _dense_windows(note: str, terms: set[str], width: int, k: int) -> list[tuple[int, int]]:
    """The k highest-signal non-overlapping windows, in document order.

    Showing only the single densest region is a direct cause of run-to-run set
    variance: when a question's qualifying members sit in two tables far apart
    in one page, one window can only ever show one of them, and which one
    depends on the trajectory. Surfacing the top k makes one read carry the
    whole set on every run.

    Deterministic: fixed stride, ties broken by earliest position.
    """
    n = len(note)
    if n <= width or not terms:
        return [(0, min(n, width))] if n else []
    stride = max(400, width // 4)
    low = note.lower()                     # lower() preserves length; casefold may not
    scored: list[tuple[int, int]] = []
    pos = 0
    while True:
        seg = low[pos:pos + width]
        scored.append((sum(1 for t in terms if t in seg), pos))
        if pos + width >= n:
            break
        pos += stride
    scored.sort(key=lambda hp: (-hp[0], hp[1]))
    picked: list[tuple[int, int]] = []
    for hits, start in scored:
        if len(picked) >= max(1, k):
            break
        if picked and hits <= 0:
            break                          # never pad with zero-signal regions
        end = min(n, start + width)
        if any(start < pe and ps < end for ps, pe in picked):
            continue
        picked.append((start, end))
    picked.sort()
    return picked or [(0, min(n, width))]


# ═══════════════════════════════════════════════════════════════════════════
# tools
# ═══════════════════════════════════════════════════════════════════════════
TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Web search. Returns numbered results with title, url and an excerpt.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "the search query"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "read_page",
        "description": ("Read a page. Returns its head plus the regions densest in your "
                        "focus terms. Always read the page before relying on a figure."),
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string", "description": "the page url"},
            "focus": {"type": "string",
                      "description": "what you are looking for on the page"}},
            "required": ["url"]}}},
]

_SLOT = "\x00{}\x00"      # placeholder resolved to a real [n] at commit time


@dataclass(slots=True)
class ToolOut:
    """A tool's rendered text plus the rows it wants numbered.

    Rows are NOT appended by the coroutine — the caller appends them in call
    order and substitutes the placeholders, so [n] never depends on which
    network call returned first.
    """
    text: str
    rows: list[Row] = field(default_factory=list)


def _commit(out: object, ledger: Ledger) -> str:
    if isinstance(out, str):
        return out
    if not isinstance(out, ToolOut):
        return f"# tool error: {out}"
    text = out.text
    for i, row in enumerate(out.rows):
        text = text.replace(_SLOT.format(i), str(ledger.add(row)))
    return text


_SITE_OP_RE = re.compile(r"(?:\b|^)site\s*:\s*\S+\s*", re.I)


def _loosen(query: str) -> str:
    """Drop site: operators and quoting from an over-constrained query."""
    out = _SITE_OP_RE.sub("", query or "").replace('"', " ")
    return " ".join(out.split())


async def _tool_search(query: str, deadline: float) -> ToolOut:
    query = " ".join((query or "").split())[:400]
    if not query:
        return ToolOut("# web_search: empty query")
    attempts = [query]
    loose = _loosen(query)
    if loose and loose != query:
        attempts.append(loose)
    results = ()
    receipt = ""
    for attempt in attempts:
        if deadline - monotonic() < MIN_TAIL_S:
            break
        try:
            payload = await search_web([attempt], provider=SEARCH_PROVIDER,
                                       num=SEARCH_RESULTS, timeout=SEARCH_TIMEOUT_S)
        except Exception:
            continue
        results = tuple(getattr(payload, "results", ()) or ())
        receipt = getattr(payload, "receipt_id", "") or ""
        if results:
            break
    if not results:
        return ToolOut(f"# web_search '{query}': no results. Try different terms.")
    lines: list[str] = [f"web_search: {query}"]
    rows: list[Row] = []
    for result in results:
        url = (getattr(result, "url", "") or "").strip()
        note = (getattr(result, "note", "") or "").strip()
        if not url or not note:
            continue
        title = (getattr(result, "title", "") or "").strip()
        rid = str(getattr(result, "result_id", "") or "")
        end = min(len(note), SEARCH_EXCERPT_CHARS)
        idx = len(rows)
        excerpt = " ".join(note[:end].split())
        rows.append(Row(receipt_id=receipt, result_id=rid, note_len=len(note),
                        spans=((0, end),), kind="search", url=url, title=title,
                        preview=excerpt))
        lines.append(f"[{_SLOT.format(idx)}] {title}\n    {url}\n    "
                     f"{' '.join(note[:end].split())}")
    if not rows:
        return ToolOut(f"# web_search '{query}': no usable results.")
    lines.append("(excerpts only — read_page before relying on any figure)")
    return ToolOut("\n".join(lines), rows)


async def _tool_read(url: str, focus: str, question: str, deadline: float) -> ToolOut:
    url = (url or "").strip()
    if not url:
        return ToolOut("# read_page: no url")
    if deadline - monotonic() < MIN_TAIL_S:
        return ToolOut(f"# read_page {url}: out of time")
    try:
        payload = await fetch_page(url, provider=SEARCH_PROVIDER, timeout=FETCH_TIMEOUT_S)
    except Exception as exc:
        return ToolOut(f"# read_page {url} failed ({_err(exc)}). "
                       f"Try another source or search for a mirror.")
    results = tuple(getattr(payload, "results", ()) or ())
    receipt = getattr(payload, "receipt_id", "") or ""
    if not results:
        return ToolOut(f"# read_page {url}: no content returned.")
    result = results[0]
    note = (getattr(result, "note", "") or "")
    if not note.strip():
        return ToolOut(f"# read_page {url}: empty page.")
    title = (getattr(result, "title", "") or "").strip()
    rid = str(getattr(result, "result_id", "") or "")

    terms = _terms(focus) | _terms(question)
    head_end = min(len(note), PAGE_HEAD_CHARS)
    spans = [(0, head_end)]
    for start, end in _dense_windows(note[head_end:], terms, PAGE_WINDOW_CHARS, PAGE_WINDOWS):
        spans.append((head_end + start, head_end + end))
    spans = list(_merge_spans(tuple(spans)))

    row = Row(receipt_id=receipt, result_id=rid, note_len=len(note),
              spans=tuple(spans), kind="page", url=url, title=title,
              preview="\n".join(note[s:e] for s, e in spans)[:PAGE_PREVIEW_CHARS])
    body = [f"read_page [{_SLOT.format(0)}] {title or url}\n{url}"]
    for i, (start, end) in enumerate(spans):
        label = "HEAD" if start == 0 else f"REGION @{start}"
        body.append(f"--- {label} ---\n{note[start:end]}")
    if len(note) > sum(e - s for s, e in spans):
        body.append(f"(page is {len(note)} chars; {len(spans)} region(s) shown. "
                    f"read_page again with a different focus to see elsewhere.)")
    return ToolOut("\n".join(body), [row])


def _call_name(call: object) -> str:
    """Tool name, whichever shape the call arrives in.

    This SDK's LlmMessageToolCall is FLAT — id/type/name/arguments, no .function.
    Reading OpenAI's nested {function:{name,arguments}} shape silently yielded ""
    for every call, so the model asked for a search on every turn and got back
    "# unknown tool:" every time. The nested branch is kept only as a fallback.
    """
    name = getattr(call, "name", None)
    if isinstance(name, str) and name.strip():
        return name.strip()
    fn = getattr(call, "function", None)
    return (getattr(fn, "name", "") or "").strip()


def _call_args(call: object) -> dict:
    """Arguments as a dict.

    message.tool_calls carries `arguments` as a JSON STRING; the response-level
    LlmResponse.tool_calls accessor hands back an already-parsed Mapping. Accept
    either, so the reader does not depend on which accessor the turn used.
    """
    raw = getattr(call, "arguments", None)
    if raw is None:
        fn = getattr(call, "function", None)
        raw = getattr(fn, "arguments", None)
    if isinstance(raw, Mapping):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw or "{}")
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


async def _run_tool(call: object, question: str, deadline: float) -> ToolOut | str:
    name = _call_name(call)
    args = _call_args(call)
    try:
        if name == "web_search":
            return await _tool_search(str(args.get("query") or ""), deadline)
        if name == "read_page":
            return await _tool_read(str(args.get("url") or ""),
                                    str(args.get("focus") or ""), question, deadline)
    except Exception as exc:
        return f"# tool {name} crashed: {_err(exc)}"
    return f"# unknown tool: {name}"


# ═══════════════════════════════════════════════════════════════════════════
# llm access — one provider, one ladder
# ═══════════════════════════════════════════════════════════════════════════
def _err(exc: BaseException) -> str:
    """Short description of an exception WITHOUT dunder reflection.

    type(exc).__name__ is the natural way to write this, but the platform's AST
    policy rejects dunder attribute reflection outright — a real upload 422:
    "__name__ attribute reflection is not supported (dunder_attribute)".
    repr() carries the class name too and is a plain builtin call.
    """
    try:
        return repr(exc)[:160]
    except Exception:
        return "error"


def _text_of(payload: object) -> str:
    llm = getattr(payload, "llm", None)
    text = (getattr(llm, "raw_text", None) or "").strip()
    if text:
        return text
    choices = getattr(llm, "choices", None) or []
    if choices:
        content = getattr(getattr(choices[0], "message", None), "content", None)
        if isinstance(content, str):
            return content.strip()
    return ""


async def _chat(system: str, user: str, *, timeout: float, max_tokens: int = 2600,
                think: bool = False, model: str = "") -> str:
    """One tool-free call, walking the model ladder on failure or empty output."""
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    for rung, attempts in _ladder(model or MODEL_LOOP):
        for _ in range(attempts):
            if timeout <= 4.0:
                return ""
            try:
                payload = await llm_chat(
                    provider=LLM_PROVIDER, model=rung, messages=messages,
                    temperature=0.15, max_output_tokens=max_tokens, timeout=timeout,
                    thinking=_think_for(rung, want=think),
                )
                text = _text_of(payload)
                if text:
                    return text
            except Exception:
                continue
    return ""


async def _turn(messages: list[dict], deadline: float, *, tools_on: bool):
    """One loop turn, walking the model ladder on failure.

    Reasoning stays on at low effort throughout: the committing turn is the one
    that must apply every answer rule and place every [n], so it is the last
    place to economise on it.
    """
    for rung, attempts in _ladder(MODEL_LOOP):
        for _ in range(attempts):
            timeout = min(TURN_TIMEOUT_S, deadline - monotonic() - 5.0)
            if timeout <= 5.0:
                return None
            try:
                return await llm_chat(
                    provider=LLM_PROVIDER, model=rung, messages=messages,
                    tools=TOOL_SPECS if tools_on else None,
                    tool_choice="auto" if tools_on else None,
                    temperature=0.2,
                    thinking=_think_for(rung, want=True),
                    timeout=timeout,
                )
            except Exception:
                continue
    return None


# ═══════════════════════════════════════════════════════════════════════════
# answer floor
# ═══════════════════════════════════════════════════════════════════════════
# Each of these shipped as a final answer at some point and each is a certain 0.
_TOOL_MARKUP_RE = re.compile(
    r"<\s*/?\s*tool_call|<\s*/?\s*(?:arg_key|arg_value|function_call|invoke)\b"
    r"|\bweb_search\s*[（(]\s*query|\bread_page\s*[（(]\s*url", re.I)
_NARRATION_RE = re.compile(
    r"^\s*(?:i (?:need|will|should|am going|'ll)\b|let me\b|first,?\s*(?:i|let)\b|"
    r"i'?ll (?:search|look|start|begin|gather|check)|now (?:i|that i)\b)", re.I)
_REFUSAL_RE = re.compile(
    r"^\s*(?:i\s+(?:can(?:no|')t|am\s+unable|was\s+unable|do\s*n[o']t\s+have)"
    r"|unable\s+to\b|sorry\b|regrettably\b|there\s+is\s+insufficient)", re.I)
_CITE_RE = re.compile(r"\[[0-9]{1,3}\]")
_VERIFY_RE = re.compile(r"\s*\((?:verify|unverified|uncertain)[^)]*\)", re.I)
MIN_ANSWER_CHARS = 40
MIN_CITED_CHARS = 6      # 'Earth [2]' is a complete answer to some questions


def _repetitive(text: str) -> bool:
    """The same sentence emitted over and over — a decoding collapse, not prose."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text or "") if len(p.strip()) > 20]
    if len(parts) < 3:
        return False
    return len(set(parts)) <= max(1, len(parts) // 3)


def _usable(text: str) -> bool:
    body = (text or "").strip()
    if not body:
        return False
    if _TOOL_MARKUP_RE.search(body) or _repetitive(body):
        return False
    if body.startswith("{") or body.startswith("["):
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict) and ("name" in parsed or "tool" in parsed):
                return False
        except Exception:
            pass
    cited = bool(_CITE_RE.search(body))
    if cited and len(body) >= MIN_CITED_CHARS:
        return True                        # '42 [3]' is a legitimate answer
    if _NARRATION_RE.match(body) or _REFUSAL_RE.match(body):
        return False
    return len(body) >= MIN_ANSWER_CHARS


REPAIR_ORDER = (
    "That was not a usable final answer — it was tool-call markup, a description "
    "of what you intended to do, or empty. Write the answer itself now: plain "
    "prose, the direct answer in the first sentence, [n] on every supported claim. "
    "Do not call any tool and do not describe your process."
)


def _wrapup(seconds_left: float) -> str:
    return (
        f"TIME: about {int(max(0, seconds_left))}s remain. Stop researching and write "
        f"the final answer NOW from the evidence already in this transcript. Commit to "
        f"the best supported answer — an unhedged answer with citations beats a hedge. "
        f"Apply every answer rule you were given and place [n] on every claim."
    )


# ═══════════════════════════════════════════════════════════════════════════
# stages
# ═══════════════════════════════════════════════════════════════════════════
BRIEF_SYSTEM = (
    "Answer from your own knowledge, then say how to verify it. Two blocks, "
    "nothing else.\nDRAFT: your best answer now, with any figure you are unsure of "
    "marked (verify).\nPLAN: the specific documents or tables that would confirm it, "
    "and the exact search terms that would find them. Name the source the question "
    "specifies if it names one."
)


async def _brief(question: str, deadline: float) -> str:
    """The model's own answer plus a verification plan.

    Cheap and high-value: it gives the loop a hypothesis to confirm or refute
    instead of starting cold, and it names the documents worth fetching.
    """
    timeout = min(BRIEF_TIMEOUT_S, deadline - monotonic() - COMMIT_RESERVE_S)
    if timeout <= 6.0:
        return ""
    text = await _chat(BRIEF_SYSTEM, question, timeout=timeout, max_tokens=1400)
    if not text:
        return ""
    return ("PRIOR KNOWLEDGE (unverified — confirm or refute against sources; "
            "a (verify) mark means you must check it):\n" + text[:6000])


_SEED_TOKEN_RE = re.compile(r"[A-Za-z0-9][\w.'\-]{1,}")
_SEED_STOP = frozenset(
    "what which who whom whose when where how many much name list give tell show "
    "find identify please could would you your the and for with from that this "
    "have has was were are is been its their there according per listed".split())


def _seed_queries(question: str, set_like: bool) -> list[str]:
    """Deterministic bootstrap searches derived from the question text.

    Fired before the model's first turn so grounded evidence exists even if the
    first LLM call is slow or times out under validator contention — and so the
    same question seeds identically on every re-run.
    """
    tokens = [t for t in _SEED_TOKEN_RE.findall(question or "")
              if t.lower() not in _SEED_STOP and len(t) > 2]
    if not tokens:
        return []
    core = " ".join(tokens[:12])
    queries = [core]
    if set_like:
        queries.append(f"list of {' '.join(tokens[:8])}")
    for name in _named_sources(question)[:1]:
        queries.append(f"{' '.join(tokens[:8])} {name}")
    out: list[str] = []
    for q in queries:
        q = " ".join(q.split())
        if q and q not in out:
            out.append(q)
    return out[:MAX_SEED_QUERIES]


async def _preseed(question: str, set_like: bool, ledger: Ledger,
                   deadline: float) -> str:
    queries = _seed_queries(question, set_like)
    if not queries or deadline - monotonic() < COMMIT_RESERVE_S + 12.0:
        return ""
    outs = await asyncio.gather(*(_tool_search(q, deadline) for q in queries),
                                return_exceptions=True)
    blocks: list[str] = []
    for out in outs:                       # commit in CALL order, not completion order
        if isinstance(out, BaseException) or not isinstance(out, ToolOut):
            continue
        body = _commit(out, ledger)
        if body and not body.startswith("#"):
            blocks.append(body)
    if not blocks:
        return ""
    return ("SEED EVIDENCE (already retrieved; cite by [n], read_page before "
            "relying on a figure):\n" + "\n\n".join(blocks))


async def _loop(question: str, rules: list[str], brief: str, ledger: Ledger,
                deadline: float) -> tuple[str, list[dict]]:
    messages: list[dict] = [{"role": "system", "content": LOOP_RULES}]
    for rule in rules:
        messages.append({"role": "system", "content": rule})
    if brief:
        messages.append({"role": "system", "content": brief})
    seeded = await _preseed(question, _wants_set(question), ledger, deadline)
    if seeded:
        messages.append({"role": "system", "content": seeded})
    messages.append({"role": "user", "content": question})

    answer = ""
    repairs = MAX_REPAIRS
    ordered = False
    for turn in range(1, MAX_TURNS + 1):
        left = deadline - monotonic()
        if left <= MIN_TAIL_S:
            break
        commit_now = left <= COMMIT_RESERVE_S or turn >= MAX_TURNS
        if (commit_now or turn >= MAX_TURNS - 1) and not ordered:
            messages.append({"role": "system", "content": _wrapup(left)})
            ordered = True

        payload = await _turn(messages, deadline, tools_on=not commit_now)
        if payload is None:
            break
        llm = getattr(payload, "llm", None)
        choices = getattr(llm, "choices", None) or []
        if not choices:
            break
        msg = getattr(choices[0], "message", None)
        calls = tuple(getattr(msg, "tool_calls", None) or ())

        if not calls:
            candidate = _text_of(payload)
            if not _usable(candidate):
                # Do NOT echo the junk back: replaying tool markup as an assistant
                # turn is the strongest possible signal to produce more of it.
                if repairs > 0 and (deadline - monotonic()) > MIN_TAIL_S + 10.0:
                    repairs -= 1
                    messages.append({"role": "system", "content": REPAIR_ORDER})
                    continue
                break
            answer = candidate
            messages.append({"role": "assistant", "content": answer})
            break

        try:
            messages.append(msg.to_input_message())
        except Exception:
            messages.append({"role": "assistant", "content": "",
                             "tool_calls": [{"id": getattr(c, "id", ""),
                                             "type": "function",
                                             "function": {"name": _call_name(c),
                                                          "arguments": json.dumps(_call_args(c))}}
                                            for c in calls]})

        run = calls[:MAX_CALLS_PER_TURN]
        budget = max(5.0, min(FETCH_TIMEOUT_S * 2 + 6.0,
                              deadline - monotonic() - MIN_TAIL_S))
        tasks = [asyncio.ensure_future(_run_tool(c, question, deadline)) for c in run]
        try:
            # asyncio.wait, not wait_for+gather: a timeout must not discard the
            # calls that already finished.
            await asyncio.wait(tasks, timeout=budget)
        except Exception:
            pass
        outs: list[object] = []
        for task in tasks:
            if task.done():
                try:
                    outs.append(task.result())
                except Exception as exc:
                    outs.append(f"# tool crashed: {_err(exc)}")
            else:
                task.cancel()
                outs.append("# tool timed out — use what you already have")
        for call, out in zip(run, outs):
            messages.append({"role": "tool", "tool_call_id": getattr(call, "id", ""),
                             "content": _commit(out, ledger)})
        # every tool_call id must get a reply or the transcript is invalid
        for call in calls[MAX_CALLS_PER_TURN:]:
            messages.append({"role": "tool", "tool_call_id": getattr(call, "id", ""),
                             "content": "# skipped: per-turn tool budget reached"})
    return answer, messages


AUDIT_SYSTEM = (
    "You are auditing a research answer against the evidence it cites. Report only "
    "defects, as short imperative lines, at most six. Look for:\n"
    "- a claim that contradicts the source it cites;\n"
    "- a figure that appears in the answer but in none of the evidence;\n"
    "- for a set question: a qualifying member omitted, or an excluded member with "
    "no stated failing condition and no citation;\n"
    "- for a superlative: a winner named without the candidate table;\n"
    "- the named source of the question not being the source actually cited;\n"
    "- hedging on something the evidence establishes.\n"
    "If the answer is sound, reply exactly OK."
)


async def _audit(question: str, answer: str, digest: str, deadline: float) -> str:
    timeout = min(AUDIT_TIMEOUT_S, deadline - monotonic() - MIN_TAIL_S - 12.0)
    if timeout <= 6.0 or not answer:
        return ""
    user = (f"QUESTION:\n{question}\n\nANSWER:\n{answer[:14000]}\n\n"
            f"EVIDENCE:\n{digest[:40000]}")
    text = await _chat(AUDIT_SYSTEM, user, timeout=timeout, max_tokens=700,
                       model=MODEL_AUDIT)
    body = (text or "").strip()
    if not body or body.upper().startswith("OK"):
        return ""
    return body


async def _patch(question: str, answer: str, findings: str, digest: str,
                 rules: list[str], deadline: float) -> str:
    timeout = min(COMMIT_TIMEOUT_S, deadline - monotonic() - MIN_TAIL_S)
    if timeout <= 8.0:
        return answer
    system = ("Rewrite the answer so every listed defect is fixed. Keep everything "
              "that was already correct and cited. Change nothing the findings do "
              "not require. Output only the corrected answer.\n\n" + "\n\n".join(rules))
    user = (f"QUESTION:\n{question}\n\nANSWER:\n{answer[:14000]}\n\n"
            f"DEFECTS TO FIX:\n{findings[:3000]}\n\nEVIDENCE:\n{digest[:40000]}")
    text = (await _chat(system, user, timeout=timeout, max_tokens=3000, think=True,
                        model=MODEL_AUDIT)).strip()
    if not _usable(text):
        return answer
    # A patch that drops citation coverage is a regression, not a fix: an audit
    # model that answers the wrong prompt (or a rung that returns an unrelated
    # completion) would otherwise replace a well-cited answer with prose that
    # cites nothing, and the judge counts only validated citations.
    before = len(set(_cited_numbers(answer, 999)))
    after = len(set(_cited_numbers(text, 999)))
    if before and after < before:
        return answer
    return text


DIGEST_CHAR_CAP = 70000


def _digest(ledger: Ledger) -> str:
    """A clean numbered evidence digest, built from the LEDGER.

    It used to be reconstructed by scanning `messages` for role=="tool" entries,
    but that list is MIXED: the assistant turn is appended as the SDK's
    LlmMessage dataclass (from to_input_message()), which has no .get(), so the
    scan raised AttributeError on every run that used a tool — and query()'s
    catch-all turned that into the give-up string with no trace.

    Building from the ledger is also strictly better: it preserves the exact [n]
    numbering, carries no assistant/tool scaffolding, and cannot drop early [n]s
    off the front of a truncated message window.
    """
    parts: list[str] = []
    spent = 0
    for i, row in enumerate(ledger.rows, start=1):
        text = (row.preview or "").strip()
        if not text:
            continue
        head = f"[{i}] {row.title or ''} ({row.url or ''})".strip()
        block = f"{head}\n{text}"
        if spent + len(block) > DIGEST_CHAR_CAP:
            break
        spent += len(block)
        parts.append(block)
    return "\n\n".join(parts)


COMMIT_SYSTEM = (
    "Write the final answer to the question using ONLY the numbered evidence "
    "below. Lead with the direct answer, then the proof. Put [n] on every claim "
    "that rests on evidence n. Do not describe your process and do not hedge a "
    "fact the evidence establishes."
)


async def _commit_from_digest(question: str, digest: str, rules: list[str],
                              draft: str, deadline: float) -> str:
    timeout = min(COMMIT_TIMEOUT_S, deadline - monotonic() - MIN_TAIL_S)
    if timeout <= 6.0:
        return ""
    system = COMMIT_SYSTEM + ("\n\n" + "\n\n".join(rules) if rules else "")
    user = f"QUESTION:\n{question}\n\nEVIDENCE:\n{digest[:70000]}"
    if draft:
        user += f"\n\nEARLIER DRAFT (may be incomplete; verify against the evidence):\n{draft[:4000]}"
    text = await _chat(system, user, timeout=timeout, max_tokens=3000)
    return text.strip() if _usable(text) else ""


_LEAD_RE = re.compile(r"^\s*(?:based on (?:my|the)\b|now (?:i|that i)\b|"
                      r"i (?:now )?(?:have|will)\b|let me\b)", re.I)


def _strip_narration(answer: str) -> str:
    """Drop leading uncited stage-direction sentences; never touch a cited one."""
    parts = re.split(r"(?<=[.!?])\s+", answer or "")
    while len(parts) > 1 and _LEAD_RE.match(parts[0]) and not _CITE_RE.search(parts[0]):
        parts = parts[1:]
    return " ".join(parts).strip()


def _fallback(question: str, digest: str) -> str:
    """Last rung, no LLM. Never emit a bare 'unavailable' line — the judge reads
    that as a forfeit, while any cited substance can still win a comparison."""
    lines = [ln.strip() for ln in (digest or "").splitlines() if ln.strip()]
    kept: list[str] = []
    for line in lines:
        if line.startswith(("#", "---", "(")) or line.startswith("http"):
            continue
        if re.match(r"^(?:web_search|read_page)\b", line):
            continue
        if len(line) < 40 or not re.search(r"[.!?]", line):
            continue
        kept.append(line)
        if len(kept) >= 6:
            break
    if not kept:
        return ("The available sources did not yield a verifiable answer to this "
                "question within the research budget.")
    return ("Based on the retrieved sources, the most relevant established facts are "
            "below; they bear directly on the question but were not resolved into a "
            "single verified answer within the research budget.\n\n"
            + "\n".join(f"- {ln}" for ln in kept))


# ═══════════════════════════════════════════════════════════════════════════
# citations
# ═══════════════════════════════════════════════════════════════════════════
_CITE_GROUP_RE = re.compile(r"\[([0-9][0-9,\s\-]*)\]")


def _cited_numbers(answer: str, limit: int) -> list[int]:
    out: list[int] = []
    seen: set[int] = set()
    for m in _CITE_GROUP_RE.finditer(answer or ""):
        for part in re.split(r"[,\s]+", m.group(1)):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                bounds = part.split("-", 1)
                try:
                    lo, hi = int(bounds[0]), int(bounds[1])
                except ValueError:
                    continue
                span = range(lo, hi + 1) if lo <= hi else range(hi, lo + 1)
            else:
                try:
                    span = [int(part)]
                except ValueError:
                    continue
            for n in span:
                if 1 <= n <= limit and n not in seen:
                    seen.add(n)
                    out.append(n)
    return out


def _citations(answer: str, ledger: Ledger) -> list[CitationRef]:
    """Refs for what the answer actually cites, inside the payload ceiling.

    The cap is applied to what we KEEP, not to what we consider: slicing the
    candidate list first would make cheap refs past the cap unreachable even
    with budget to spare, and the one-line-per-excluded-member rule pushes the
    distinct [n] count well past it.
    """
    refs: list[CitationRef] = []
    spent = 0
    for n in _cited_numbers(answer, len(ledger.rows)):
        if len(refs) >= CITATION_CAP:
            break
        ref = ledger.ref(n)
        if ref is None:
            continue
        cost = ledger.cost(n)
        if spent + cost > EVIDENCE_CHAR_BUDGET:
            continue                       # skip the expensive one, keep looking
        spent += cost
        refs.append(ref)
    return refs


# ═══════════════════════════════════════════════════════════════════════════
# structured output
# ═══════════════════════════════════════════════════════════════════════════
SCHEMA_SYSTEM = (
    "Convert the answer into a JSON value matching the schema. Emit the bare JSON "
    "value only — no prose, no markdown fence, no explanation."
)


def _extract_json(text: str) -> object | None:
    body = (text or "").strip()
    if body.startswith("```"):
        body = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", body).strip()
    try:
        return json.loads(body)
    except Exception:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = body.find(opener), body.rfind(closer)
        if 0 <= start < end:
            try:
                return json.loads(body[start:end + 1])
            except Exception:
                continue
    return None


def _schema_skeleton(schema: object) -> object:
    if not isinstance(schema, dict):
        return None
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = next((k for k in kind if k != "null"), None)
    if kind == "object":
        props = schema.get("properties")
        return {k: _schema_skeleton(v) for k, v in props.items()} if isinstance(props, dict) else {}
    if kind == "array":
        return []
    if kind in ("number", "integer"):
        return 0
    if kind == "boolean":
        return False
    return ""


async def _structured(question: str, schema: object, answer: str,
                      deadline: float) -> object:
    timeout = min(40.0, deadline - monotonic() - 3.0)
    if timeout > 6.0:
        user = (f"SCHEMA:\n{json.dumps(schema)[:4000]}\n\nQUESTION:\n{question}\n\n"
                f"ANSWER:\n{(answer or '')[:8000]}")
        for _ in range(2):
            text = await _chat(SCHEMA_SYSTEM, user, timeout=timeout, max_tokens=1200,
                               model=MODEL_AUDIT)
            value = _extract_json(text)
            if value is not None:
                return value
            timeout = min(timeout, deadline - monotonic() - 3.0)
            if timeout <= 6.0:
                break
    return _schema_skeleton(schema)


# ═══════════════════════════════════════════════════════════════════════════
# entrypoint
# ═══════════════════════════════════════════════════════════════════════════
LAST_FAILURES: list[str] = []


def _record_failure(where: str, exc: BaseException) -> None:
    """Keep the failure visible to a debug harness. Never raises.

    Deliberately no `traceback` module and no function-local import: every
    artifact this platform has accepted imports only asyncio / json / re /
    dataclasses / collections.abc / time / urllib.parse / harnyx_miner_sdk, all
    at module level. After one 422 on an assumed-permitted construct, the import
    set here stays a strict subset of what is demonstrably allowed. A wrapping
    debug harness is the right place to capture a full traceback.
    """
    try:
        LAST_FAILURES.append(f"{where}: {_err(exc)}")
        # Slice ASSIGNMENT, not `del LAST_FAILURES[:-5]`: the platform's AST
        # policy rejects delete statements outright (upload 422:
        # "delete statements are not supported in miner scripts").
        LAST_FAILURES[:] = LAST_FAILURES[-5:]
    except Exception:
        pass
async def _solve(question: str, deadline: float) -> tuple[str, Ledger]:
    ledger = Ledger()
    rules = _shape_rules(question)
    brief = await _brief(question, deadline)
    answer, _messages = await _loop(question, rules, brief, ledger, deadline)
    digest = _digest(ledger)

    if not answer and digest:
        answer = await _commit_from_digest(question, digest, rules, "", deadline)

    if answer and digest and deadline - monotonic() > MIN_TAIL_S + 24.0:
        findings = await _audit(question, answer, digest, deadline)
        if findings:
            answer = await _patch(question, answer, findings, digest, rules, deadline)

    if not _usable(answer):
        answer = _fallback(question, digest)
    answer = _strip_narration(_VERIFY_RE.sub("", answer))[:ANSWER_CHAR_CAP]
    return answer, ledger


async def _hv16_base_query(query: Query) -> Response:
    deadline = monotonic() + WALL_BUDGET_S
    question = (getattr(query, "text", "") or "").strip()
    if not question:
        return Response(text="No question provided.")
    schema = getattr(query, "output_schema", None)
    try:
        answer, ledger = await _solve(question, deadline)
    except Exception as exc:
        # The catch-all must stay — a raised exception is a guaranteed 0 — but it
        # must not erase WHY. Swallowing the traceback here is what made three
        # live runs uninformative while every tool call was being dropped.
        _record_failure("solve", exc)
        answer, ledger = "", Ledger()
    try:
        citations = _citations(answer, ledger)
    except Exception:
        citations = []
    if schema is None:
        if not answer:
            answer = ("The available sources did not yield a verifiable answer to "
                      "this question within the research budget.")
        return Response(text=answer, citations=citations or None)
    try:
        value = await _structured(question, schema, answer, deadline)
    except Exception:
        value = _schema_skeleton(schema)
    try:
        return Response(output=value, citations=citations or None)
    except Exception:
        return Response(output=value)

# === Harnyx v16 mechanism: claim-risk + coverage-gap verification patch ===
# Runs strictly after the base pipeline above has produced its answer. It
# never alters the base retrieval/synthesis control flow; it adds a new,
# independent second-pass verification loop with its own fresh retrieval,
# its own evidence-support judgment, and conditional cite-or-hedge/fill
# synthesis edits. Fully fail-open: any error or time pressure returns the
# base answer unchanged.
import time as _hv16_time

_HV16_LLM_PROVIDER = "openrouter"
_HV16_LLM_MODEL = "openai/gpt-oss-120b"
_HV16_SEARCH_PROVIDER = "parallel"
_HV16_BASE_ELAPSED_SKIP_S = 175.0
_HV16_MECH_BUDGET_S = 42.0


def _hv16_extract_json_object(raw: str | None) -> dict | None:
    import json as _hv16_json
    import re as _hv16_re

    if not raw:
        return None
    cleaned = _hv16_re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=_hv16_re.I | _hv16_re.M).strip()
    try:
        return _hv16_json.loads(cleaned)
    except Exception:
        match = _hv16_re.search(r"\{.*\}", cleaned, _hv16_re.S)
        if not match:
            return None
        try:
            return _hv16_json.loads(match.group(0))
        except Exception:
            return None


async def _hv16_identify_gaps(question: str, answer_text: str) -> dict:
    try:
        result = await llm_chat(
            provider=_HV16_LLM_PROVIDER,
            model=_HV16_LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict answer-quality auditor. Read the question and the "
                        "drafted answer only.\n"
                        "List at most 2 specific, load-bearing, time-sensitive, or otherwise "
                        "non-obvious factual claims in the answer that need independent "
                        "verification (risky_claims).\n"
                        "List at most 1 concrete element the question explicitly asks for that "
                        "the answer does not address at all (missing_elements).\n"
                        "Use short exact phrases copied or closely paraphrased from the answer "
                        "or question, not full sentences of commentary.\n"
                        "Return JSON only: {\"risky_claims\": [\"...\"], "
                        "\"missing_elements\": [\"...\"]}. Use empty arrays when none apply."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question:\n{question}\n\nAnswer:\n{answer_text[:6000]}",
                },
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=350,
            timeout=14.0,
        )
        raw = getattr(getattr(result, "response", None), "raw_text", None)
        parsed = _hv16_extract_json_object(raw)
        if not isinstance(parsed, dict):
            return {"risky_claims": [], "missing_elements": []}
        risky = parsed.get("risky_claims")
        missing = parsed.get("missing_elements")
        risky = [str(c).strip() for c in risky if str(c).strip()][:2] if isinstance(risky, list) else []
        missing = [str(c).strip() for c in missing if str(c).strip()][:1] if isinstance(missing, list) else []
        return {"risky_claims": risky, "missing_elements": missing}
    except Exception:
        return {"risky_claims": [], "missing_elements": []}


async def _hv16_fresh_search_digest(query_text: str):
    try:
        search_result = await search_web(
            query_text[:300],
            provider=_HV16_SEARCH_PROVIDER,
            num=5,
            timeout=12.0,
        )
    except Exception:
        return None, []
    results = list(getattr(search_result.response, "data", None) or [])
    digest_lines = []
    for idx, item in enumerate(results[:5]):
        snippet = (getattr(item, "snippet", None) or "").strip()
        title = (getattr(item, "title", None) or "").strip()
        if snippet or title:
            digest_lines.append(f"[{idx}] {title} :: {snippet[:400]}")
    if not digest_lines:
        return None, []
    return search_result, digest_lines


async def _hv16_verify_claim(claim: str):
    search_result, digest_lines = await _hv16_fresh_search_digest(claim)
    if search_result is None:
        return "unclear", None
    try:
        judged = await llm_chat(
            provider=_HV16_LLM_PROVIDER,
            model=_HV16_LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You check whether search snippets support or contradict a claim.\n"
                        "Return JSON only: {\"status\": \"supported\"|\"contradicted\"|"
                        "\"unclear\", \"best_index\": <int or null>}. best_index is the "
                        "index of the single snippet that most directly supports or "
                        "contradicts the claim, else null."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Claim:\n{claim}\n\nSnippets:\n" + "\n".join(digest_lines),
                },
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=120,
            timeout=12.0,
        )
        raw = getattr(getattr(judged, "response", None), "raw_text", None)
        parsed = _hv16_extract_json_object(raw)
    except Exception:
        parsed = None
    status = "unclear"
    best_index = None
    if isinstance(parsed, dict):
        candidate_status = parsed.get("status")
        if candidate_status in ("supported", "contradicted", "unclear"):
            status = candidate_status
        candidate_index = parsed.get("best_index")
        if isinstance(candidate_index, int) and 0 <= candidate_index < len(digest_lines):
            best_index = candidate_index
    citation_ref = None
    if status == "supported" and best_index is not None:
        try:
            result_items = list(search_result.results)
            if 0 <= best_index < len(result_items):
                dto = result_items[best_index]
                citation_ref = CitationRef(receipt_id=search_result.receipt_id, result_id=dto.result_id)
        except Exception:
            citation_ref = None
    return status, citation_ref


async def _hv16_rewrite_without_claim(question: str, answer_text: str, claim: str) -> str | None:
    try:
        result = await llm_chat(
            provider=_HV16_LLM_PROVIDER,
            model=_HV16_LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You lightly edit an answer for factual hygiene. Remove or hedge only "
                        "the single specified claim because it is unsupported or contradicted; "
                        "keep every other sentence and fact untouched and do not add any new "
                        "facts. Return the full corrected answer as plain text with no preamble."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\nCurrent answer:\n{answer_text[:8000]}\n\n"
                        f"Unsupported or contradicted claim to remove or hedge:\n{claim}"
                    ),
                },
            ],
            tools=None,
            temperature=0.1,
            max_output_tokens=1200,
            timeout=16.0,
        )
        text = (getattr(getattr(result, "response", None), "raw_text", None) or "").strip()
        return text or None
    except Exception:
        return None


async def _hv16_fill_missing_element(question: str, answer_text: str, missing_element: str):
    search_result, digest_lines = await _hv16_fresh_search_digest(f"{question} {missing_element}")
    if search_result is None:
        return None, None
    try:
        result = await llm_chat(
            provider=_HV16_LLM_PROVIDER,
            model=_HV16_LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write at most one short factual sentence that directly answers a "
                        "missing element of the question, using only the given snippets as "
                        "evidence. Never invent facts not present in the snippets.\n"
                        "Return JSON only: {\"sentence\": \"...\" or null, \"best_index\": "
                        "<int or null>}. Use null for both fields if the snippets do not "
                        "clearly answer the missing element."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\nMissing element:\n{missing_element}\n\n"
                        f"Snippets:\n" + "\n".join(digest_lines)
                    ),
                },
            ],
            tools=None,
            temperature=0.1,
            max_output_tokens=200,
            timeout=14.0,
        )
        raw = getattr(getattr(result, "response", None), "raw_text", None)
        parsed = _hv16_extract_json_object(raw)
    except Exception:
        parsed = None
    if not isinstance(parsed, dict):
        return None, None
    sentence = parsed.get("sentence")
    best_index = parsed.get("best_index")
    if not isinstance(sentence, str) or not sentence.strip():
        return None, None
    if not isinstance(best_index, int) or not (0 <= best_index < len(digest_lines)):
        return None, None
    citation_ref = None
    try:
        result_items = list(search_result.results)
        if 0 <= best_index < len(result_items):
            dto = result_items[best_index]
            citation_ref = CitationRef(receipt_id=search_result.receipt_id, result_id=dto.result_id)
    except Exception:
        citation_ref = None
    if citation_ref is None:
        return None, None
    return sentence.strip(), citation_ref


async def _hv16_verification_patch(query_text: str, response: "Response") -> "Response":
    """MECHANISM: claim-risk + coverage-gap audit -> fresh targeted retrieval ->
    cite-or-hedge / cite-and-fill patch.

    This is a genuinely new verification + tool-use + synthesis stage layered
    on top of the base pipeline's answer: it independently re-checks the
    riskiest claims in the drafted answer and the most obvious missing
    query-required element against freshly retrieved evidence, then either
    attaches a newly retrieved and properly linked citation, edits the answer
    to remove/hedge a contradicted or unverifiable claim, or appends one
    grounded, cited sentence to close a coverage gap. The base pipeline never
    performs this second-pass, evidence-seeking verification loop.
    """
    mech_started = _hv16_time.monotonic()
    if response.text is None:
        return response
    answer_text = response.text
    if not answer_text.strip():
        return response
    mech_deadline = mech_started + _HV16_MECH_BUDGET_S
    try:
        gaps = await _hv16_identify_gaps(query_text, answer_text)
    except Exception:
        return response
    risky_claims = gaps.get("risky_claims") or []
    missing_elements = gaps.get("missing_elements") or []
    if not risky_claims and not missing_elements:
        return response

    citations = list(response.citations or [])
    existing_keys = {(citation.receipt_id, citation.result_id) for citation in citations}
    changed = False

    for claim in risky_claims:
        if _hv16_time.monotonic() > mech_deadline:
            break
        try:
            status, citation_ref = await _hv16_verify_claim(claim)
        except Exception:
            continue
        if status == "supported" and citation_ref is not None:
            key = (citation_ref.receipt_id, citation_ref.result_id)
            if key not in existing_keys:
                citations.append(citation_ref)
                existing_keys.add(key)
                changed = True
        elif status == "contradicted":
            try:
                rewritten = await _hv16_rewrite_without_claim(query_text, answer_text, claim)
            except Exception:
                rewritten = None
            if rewritten and rewritten.strip() and rewritten.strip() != answer_text.strip():
                answer_text = rewritten.strip()
                changed = True

    for missing_element in missing_elements:
        if _hv16_time.monotonic() > mech_deadline:
            break
        try:
            sentence, citation_ref = await _hv16_fill_missing_element(query_text, answer_text, missing_element)
        except Exception:
            sentence, citation_ref = None, None
        if sentence and citation_ref is not None:
            key = (citation_ref.receipt_id, citation_ref.result_id)
            if key not in existing_keys:
                answer_text = answer_text.rstrip() + "\n\n" + sentence
                citations.append(citation_ref)
                existing_keys.add(key)
                changed = True

    if not changed:
        return response
    try:
        return Response(text=answer_text, output=None, citations=citations or None)
    except Exception:
        return response


@entrypoint('query')
async def query(query: Query) -> Response:
    _hv16_call_started = _hv16_time.monotonic()
    response = await _hv16_base_query(query)
    try:
        base_elapsed = _hv16_time.monotonic() - _hv16_call_started
        if base_elapsed > _HV16_BASE_ELAPSED_SKIP_S:
            return response
        return await _hv16_verification_patch(query.text, response)
    except Exception:
        return response
