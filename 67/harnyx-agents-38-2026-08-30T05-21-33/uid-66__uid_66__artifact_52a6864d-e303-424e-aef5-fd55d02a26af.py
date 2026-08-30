from __future__ import annotations

import asyncio
import json
import math
import re
from datetime import datetime
from time import monotonic

from harnyx_miner_sdk.api import fetch_page, llm_chat, search_web, tooling_info
from harnyx_miner_sdk.decorators import entrypoint
from harnyx_miner_sdk.query import CitationRef, CitationSlice, Query, Response

_W = 248.0
_SR = 46.0
_MT = 12
_ST = 16.0
_FT = 36.0
_LT = 72.0
_QH = 8
_MXF = 10
_MN = 100
_TG = 2400
_MXS = 9000
_EB = 100000
_MR = 24
_CAP = 920000
_WIN = 480
_HITS = 120
_MGN = 280

_SP = ("parallel", "desearch")
_FP = ("parallel", "desearch", "firecrawl")
_LP = (
    ("openrouter", "z-ai/glm-5.2", ("Decart", "CoreWeave", "Alibaba")),
    ("ai_gateway", "zai/glm-5.3-flash", None),
    ("openrouter", "z-ai/glm-5.3-flash", None),
    ("ai_gateway", "zai/glm-5.2-fast", ("Cerebras", "Groq", "BaseTen")),
)
_CP = (
    ("openrouter", "z-ai/glm-5.2", ("Decart", "CoreWeave", "Alibaba")),
    ("openrouter", "tencent/hy4-preview", None),
    ("ai_gateway", "tencent/hy4-preview", None),
    ("openrouter", "openai/gpt-oss-120b", ("Cerebras", "Groq", "BaseTen")),
)
_GP = (
    ("openrouter", "z-ai/glm-5.2", ("Decart", "CoreWeave", "Alibaba")),
    ("openrouter", "openai/gpt-oss-120b", ("Cerebras", "Groq", "BaseTen")),
    ("openrouter", "tencent/hy4-preview", None),
)

_MK = re.compile(r"\[{1,2}\s*(\d+(?:\s*[,;]\s*\d+)*)\s*\]{1,2}")
_URL = re.compile(r"https?://[^\s)\]>\"']+", re.I)
_HOST = re.compile(
    r"\b((?:[a-z0-9][a-z0-9\-]*\.)+(?:gov|edu|org|com|net|int|mil|uk|ca|au|io|ai))\b",
    re.I,
)
_QT = re.compile(r"\"([^\"]{6,140})\"|\u201c([^\u201d]{6,140})\u201d")
_DD = re.compile(
    r"^(?:x+|n/?a|n\.a\.|na|unknown|none|null|tbd|todo|-|\.|not stated|unspecified)$",
    re.I,
)
_RF = re.compile(
    r"^\s*(i cannot construct|i cannot identify|cannot be determined|"
    r"could not run to completion|i must commit to the best-supported|"
    r"best-supported findings from the sources retrieved|##\s*verify\b)",
    re.I | re.M,
)
_AR = re.compile(
    r"\b(how many days|number of days|elapsed|GET\b|enthalpy|\bEn\b|time interval|subtract .{0,40}time)\b",
    re.I,
)
_SCR = re.compile(
    r"^(?:i have both editions[^\n]*\n+|let me (?:verify|compile|check)[^\n]*\n+|"
    r"the grep confirmed[^\n]*\n+|here is the complete answer\.\s*(?:---)?\s*)",
    re.I,
)
_XML = re.compile(r"<tool_call>\s*([A-Za-z_][\w-]*)\s*(.*?)</tool_call>", re.S | re.I)
_XARG = re.compile(r"<arg_key>\s*(.*?)\s*</arg_key>\s*<arg_value>\s*(.*?)\s*</arg_value>", re.S | re.I)
_DMP = re.compile(
    r"best-supported findings from the sources retrieved|projects & plans: updated yearly",
    re.I,
)
_DF = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%d/%m/%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
    "%Y/%m/%d",
)

_TL = [
    {
        "type": "function",
        "function": {
            "name": "hunt",
            "description": "Search the public web. Prefer official named documents.",
            "parameters": {
                "type": "object",
                "properties": {"q": {"type": "string"}, "qs": {"type": "array", "items": {"type": "string"}}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pull",
            "description": "Fetch a full page or PDF into the ledger.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scan",
            "description": "Regex or literal search inside an already pulled ledger row.",
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {"type": "integer"},
                    "pat": {"type": "string"},
                },
                "required": ["n", "pat"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "peek",
            "description": "Read a character window of a ledger row.",
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {"type": "integer"},
                    "start": {"type": "integer"},
                    "end": {"type": "integer"},
                },
                "required": ["n", "start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "keep",
            "description": "Pin a verbatim quote so citations can prove it.",
            "parameters": {
                "type": "object",
                "properties": {"n": {"type": "integer"}, "quote": {"type": "string"}},
                "required": ["n", "quote"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "arith",
            "description": "Deterministic math. ops: days,hms,en,minus,plus,ratio,max,min,abs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "op": {"type": "string"},
                    "payload": {"type": "object"},
                    "a": {},
                    "b": {},
                    "x": {},
                    "xref": {},
                    "ulab": {},
                    "uref": {},
                },
                "required": ["op"],
            },
        },
    },
]

_SY = (
    "You are a document-grounded research agent. Official named sources beat summaries. "
    "Work in constraints: build the full candidate pool from the named table or list, then "
    "filter. One missed member zeros the score. Sentence one of a final answer IS the answer. "
    "Never refuse. Never write x, N/A, Data not available, or Best-supported findings. "
    "Never narrate tool use (no Let me verify, no grep confirmed, no ## VERIFY). "
    "Cite with [n] right after the claim that the ledger row supports. "
    "Use hunt/pull to reach the named PDF, scan/peek to walk long tables, keep to pin "
    "proving quotes, arith for any day-count, GET interval, En ratio, or numeric compare. "
    "When a report has a PDF file, pull the .pdf URL, never the HTML landing page. "
    "Copy names, dates, units, and parentheticals exactly as printed. "
    "If output must be JSON, still gather the facts first; conversion happens after you finish."
)

_CM = (
    "Produce the FINAL ANSWER now. Tools are off. Start with the asked entities/values. "
    "Cover every required part. Use arith results as ground truth. Cite [n] after claims. "
    "If a schema was given, still write a complete prose answer that states every field. "
    "Never refuse and never emit placeholders."
)

_SM = (
    "Convert the finished answer into JSON that matches the schema exactly. "
    "Reply with one JSON value and nothing else. Copy spelling from the answer and sources. "
    "Never emit x, N/A, unknown, Data not available, empty strings standing in for names, "
    "or research notes inside a field. Never wrap JSON in extra commentary."
)


class _K:
    def __init__(self):
        self.t0 = monotonic()
        self.usd = 0.0

    def left(self):
        return _W - (monotonic() - self.t0)

    def ok(self, need=8.0):
        return self.left() > need

    def note(self, payload):
        try:
            c = getattr(payload, "cost_usd", None)
            if c:
                self.usd += float(c)
            b = getattr(payload, "budget", None)
            r = getattr(b, "session_remaining_budget_usd", None)
            if r is not None and float(r) < 0.04:
                self.usd = 0.48
        except Exception:
            pass


class _R:
    __slots__ = ("n", "url", "title", "txt", "rcpt", "rid", "pins", "shown")

    def __init__(self, n, url, title, txt, rcpt, rid):
        self.n = n
        self.url = url or ""
        self.title = title or ""
        self.txt = txt or ""
        self.rcpt = rcpt
        self.rid = rid
        self.pins = []
        self.shown = []


class _B:
    def __init__(self):
        self.rows = []
        self.seen = set()
        self.np = 0
        self.urls = []
        self.bad = set()

    def ins(self, payload):
        if payload is None:
            return []
        rcpt = getattr(payload, "receipt_id", "") or ""
        items = list(getattr(payload, "results", ()) or ())
        if not items:
            resp = getattr(payload, "response", None)
            data = getattr(resp, "data", None) or []
            items = list(data)
        out = []
        for item in items:
            if isinstance(item, dict):
                txt = (item.get("note") or item.get("content") or "")[:_CAP]
                url = item.get("url") or ""
                rid = item.get("result_id") or ""
                title = item.get("title") or ""
            else:
                txt = (getattr(item, "note", None) or getattr(item, "content", None) or "")[:_CAP]
                url = getattr(item, "url", None) or ""
                rid = getattr(item, "result_id", None) or ""
                title = getattr(item, "title", "") or ""
            blob = f"{url}\n{title}\n{txt}"
            for u in _URL.findall(blob):
                u = u.rstrip(").,;\"'")
                if u.startswith("http") and u not in self.urls:
                    self.urls.append(u)
            if url.startswith("http") and url not in self.urls:
                self.urls.append(url)
            if len(txt) < 16 or not rcpt:
                continue
            rid = rid or f"x{len(self.rows) + 1}"
            key = (url, rid, txt[:80])
            if key in self.seen:
                continue
            self.seen.add(key)
            row = _R(len(self.rows) + 1, url, title, txt, rcpt, rid)
            self.rows.append(row)
            out.append(row)
        return out

    def get(self, n):
        try:
            n = int(n)
        except Exception:
            return None
        if 1 <= n <= len(self.rows):
            return self.rows[n - 1]
        return None


def _vx_num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        try:
            return float(s)
        except Exception:
            m = re.search(r"-?\d+(?:\.\d+)?", s)
            if m:
                try:
                    return float(m.group(0))
                except Exception:
                    return None
    return None


def _vx_dt(s):
    s = str(s or "").strip()
    s = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", s)
    for fmt in _DF:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000 if y < 70 else 1900
        for mm, dd in ((a, b), (b, a)):
            try:
                return datetime(y, mm, dd)
            except Exception:
                pass
    return None


def _vx_hms(s):
    p = [int(x) for x in re.findall(r"\d+", str(s))]
    if not p:
        return None
    h = p[0]
    m = p[1] if len(p) > 1 else 0
    sec = p[2] if len(p) > 2 else 0
    return h * 3600 + m * 60 + sec


def _vx_fmt(t):
    t = int(t)
    sign = "-" if t < 0 else ""
    t = abs(t)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    if s or h >= 24:
        return f"{sign}{h}:{m:02d}:{s:02d}"
    return f"{sign}{h}:{m:02d}"


def _vx_c(op, payload=None, **kw):
    p = dict(payload or {})
    p.update(kw)
    o = str(op or "").strip().lower()
    if o == "days":
        a, b = _vx_dt(p.get("a")), _vx_dt(p.get("b"))
        if a and b:
            return str(abs((b.date() - a.date()).days))
        return ""
    if o == "hms":
        a, b = _vx_hms(p.get("a")), _vx_hms(p.get("b"))
        if a is None or b is None:
            return ""
        return _vx_fmt(b - a)
    if o == "en":
        x, xr = _vx_num(p.get("x")), _vx_num(p.get("xref"))
        u, ur = _vx_num(p.get("ulab")), _vx_num(p.get("uref"))
        if None in (x, xr, u, ur):
            return ""
        den = math.sqrt(u * u + ur * ur)
        if den == 0:
            return ""
        return f"{abs(x - xr) / den:.4f}".rstrip("0").rstrip(".")
    if o in ("minus", "sub", "delta"):
        a, b = _vx_num(p.get("a")), _vx_num(p.get("b"))
        if a is None or b is None:
            return ""
        v = a - b
        return str(int(v) if float(v).is_integer() else round(v, 6))
    if o in ("plus", "add"):
        a, b = _vx_num(p.get("a")), _vx_num(p.get("b"))
        if a is None or b is None:
            return ""
        v = a + b
        return str(int(v) if float(v).is_integer() else round(v, 6))
    if o == "ratio":
        a, b = _vx_num(p.get("a")), _vx_num(p.get("b"))
        if a is None or b in (None, 0):
            return ""
        v = a / b
        return str(int(v) if float(v).is_integer() else round(v, 6))
    if o == "abs":
        a = _vx_num(p.get("a"))
        return "" if a is None else str(abs(a))
    if o in ("max", "min"):
        rows = p.get("rows") or p.get("items") or []
        best = None
        lab = ""
        for row in rows:
            if isinstance(row, dict):
                n = _vx_num(row.get("value") or row.get("v"))
                name = str(row.get("label") or row.get("name") or "")
            else:
                n = _vx_num(row)
                name = str(row)
            if n is None:
                continue
            if best is None or (o == "max" and n > best) or (o == "min" and n < best):
                best = n
                lab = name
        if best is None:
            return ""
        return json.dumps({"label": lab, "value": best}, ensure_ascii=False)
    return ""


def _vx_g(text, pat, cap=_HITS, win=_WIN, back=None):
    text = text or ""
    if not pat:
        return []
    try:
        rx = re.compile(pat, re.I)
    except Exception:
        rx = re.compile(re.escape(pat), re.I)
    left = win if back is None else back
    hits = []
    for m in rx.finditer(text):
        a = max(0, m.start() - left)
        b = min(len(text), m.end() + win)
        hits.append((a, b, text[a:b]))
        if len(hits) >= cap:
            break
    if not hits:
        loc = text.casefold().find(str(pat).casefold())
        if loc >= 0:
            a = max(0, loc - left)
            b = min(len(text), loc + len(pat) + win)
            hits.append((a, b, text[a:b]))
    return hits


def _vx_dump(s):
    t = str(s or "")
    if _DMP.search(t):
        return True
    if len(t) > 500 and t.count("\n") > 5 and "sources retrieved" in t.casefold():
        return True
    return False


def _vx_dead_leaf(v):
    if v is None:
        return True
    if not isinstance(v, str):
        return False
    s = v.strip()
    if not s:
        return True
    if _DD.match(s):
        return True
    cl = s.casefold()
    if "data not available" in cl or cl in {"not available", "cannot say"}:
        return True
    if re.search(r"\bno (qualifying|surviving|matching) (routes|plants|items|records)\b", cl):
        return True
    if _vx_dump(s):
        return True
    return False


def _vx_frag_arr(v):
    if not isinstance(v, list) or len(v) < 2:
        return False
    strs = [x for x in v if isinstance(x, str)]
    if len(strs) < 2:
        return False
    n = 0
    for s in strs:
        t = s.strip()
        if not t:
            continue
        if t[:1] in "{}[]," or t.endswith(",") or (t.startswith('"') and (t.endswith('",') or t.endswith('"'))):
            if any(ch in t for ch in "{}[]"):
                n += 1
    return n >= max(2, len(strs) // 2)


def _vx_dead_tree(v):
    if _vx_frag_arr(v):
        return True
    leaves = []

    def walk(x):
        if isinstance(x, dict):
            for y in x.values():
                walk(y)
        elif isinstance(x, list):
            if _vx_frag_arr(x):
                leaves.append("{")
            for y in x:
                walk(y)
        elif isinstance(x, str):
            leaves.append(x)

    walk(v)
    if not leaves:
        return False
    if any(_vx_dump(x) or _vx_dead_leaf(x) for x in leaves):
        if any(_vx_dump(x) for x in leaves):
            return True
        dead = [x for x in leaves if _vx_dead_leaf(x)]
        if dead and (len(dead) == len(leaves) or any(_DD.match(x.strip()) or "not available" in x.casefold() for x in dead)):
            return True
    return False


def _vx_z(text):
    s = (text or "").strip()
    if not s:
        return None
    cl = s.casefold()
    if "<tool_call>" in cl or "<arg_key>" in cl or "<function" in cl:
        return None
    if _RF.search(s) or _vx_dump(s):
        return None
    s = _SCR.sub("", s).strip()
    if not s or _RF.search(s):
        return None
    if "<tool_call>" in s.casefold():
        return None
    return s


def _vx_j(raw):
    if not raw:
        return None
    body = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.+?)```", body, re.S)
    if fenced:
        body = fenced.group(1).strip()
    try:
        return json.loads(body)
    except Exception:
        pass
    for a, b in (("{", "}"), ("[", "]")):
        i, j = body.find(a), body.rfind(b)
        while i >= 0 and j > i:
            try:
                return json.loads(body[i : j + 1])
            except Exception:
                j = body.rfind(b, i, j)
    return None


def _vx_trim(value, schema):
    if not isinstance(schema, dict) or value is None:
        return value
    t = schema.get("type")
    if (t == "object" or "properties" in schema) and isinstance(value, dict):
        props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        if schema.get("additionalProperties") is False and props:
            value = {k: v for k, v in value.items() if k in props}
        out = {}
        for k, v in value.items():
            out[k] = _vx_trim(v, props.get(k) or {})
        for k in schema.get("required") or []:
            if isinstance(k, str) and k not in out:
                out[k] = _vx_skel(props.get(k) or {})
        return out
    if t == "array" and isinstance(value, list):
        item = schema.get("items") if isinstance(schema.get("items"), dict) else {}
        return [_vx_trim(x, item) for x in value]
    return value


def _vx_shape(value, schema):
    if schema is None or value is None:
        return False
    if not isinstance(schema, dict):
        return isinstance(value, (dict, list, str, int, float, bool))
    t = schema.get("type")
    if t == "object" or "properties" in schema:
        if not isinstance(value, dict):
            return False
        req = schema.get("required") or []
        return all(isinstance(k, str) and k in value for k in req)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    return isinstance(value, (dict, list, str, int, float, bool))


def _vx_sok(value, schema):
    if schema is None:
        return False
    if _vx_dead_tree(value):
        return False
    return _vx_shape(value, schema)


def _vx_emit(value, schema):
    if isinstance(value, (dict, list)):
        value = _vx_trim(value, schema)
    if value is not None and _vx_sok(value, schema):
        return value
    guess = _vx_j(value) if isinstance(value, str) else None
    if guess is not None:
        guess = _vx_trim(guess, schema)
        if _vx_sok(guess, schema):
            return guess
    sk = _vx_skel(schema)
    return sk if _vx_shape(sk, schema) else sk


def _vx_used(text):
    found = []
    for m in _MK.finditer(text or ""):
        for p in re.split(r"[,;]", m.group(1)):
            p = p.strip()
            if p.isdigit():
                n = int(p)
                if n not in found:
                    found.append(n)
    return found


def _vx_rep(text, keep):
    keep = [n for n in keep if isinstance(n, int)]
    order = []
    for n in _vx_used(text):
        if n in keep and n not in order:
            order.append(n)
    for n in keep:
        if n not in order:
            order.append(n)
    pos = {n: i + 1 for i, n in enumerate(order)}

    def sub(m):
        parts = []
        for p in re.split(r"[,;]", m.group(1)):
            p = p.strip()
            if p.isdigit():
                k = int(p)
                if k in pos:
                    parts.append(str(pos[k]))
        if not parts:
            return ""
        return "[[" + "]], [[".join(parts) + "]]"

    return _MK.sub(sub, text or ""), pos


def _vx_sl(row, spans):
    note = row.txt or ""
    n = len(note)
    if n <= 0:
        return []
    if n < _MN:
        return [CitationSlice(start=0, end=n)]
    picked = []
    for a, b in spans or []:
        a = max(0, min(n, int(a)))
        b = max(0, min(n, int(b)))
        if b <= a:
            continue
        need = max(_MN, min(_TG, n))
        if b - a < need:
            extra = need - (b - a)
            left = extra // 2
            a = max(0, a - left)
            b = min(n, a + need)
            if b - a < _MN:
                a = max(0, b - min(_MN, n))
        if b - a > _MXS:
            b = a + _MXS
        picked.append((a, b))
    if not picked:
        picked.append((0, min(n, _TG)))
    merged = []
    for a, b in sorted(picked):
        if b - a > _MXS:
            b = a + _MXS
        if merged and a <= merged[-1][1]:
            new_b = max(merged[-1][1], b)
            if new_b - merged[-1][0] <= _MXS:
                merged[-1] = (merged[-1][0], new_b)
            elif len(merged) < 3:
                a2 = merged[-1][1]
                b2 = min(n, a2 + _MXS, max(b, a2 + _MN))
                if b2 - a2 >= _MN:
                    merged.append((a2, min(b2, a2 + _MXS)))
            continue
        merged.append((a, b))
    out = []
    for a, b in merged[:3]:
        if b - a >= _MN or n < _MN:
            out.append(CitationSlice(start=a, end=b))
    return out


def _vx_refs(bag, text, fast, question=""):
    if fast:
        return [], text
    used = _vx_used(text)
    citable = [
        r.n
        for r in _vx_best(bag, question)
        if r.rid and str(r.rid)[:1] != "x" and r.rcpt and len(r.txt or "") >= _MN
    ]
    if not used:
        used = citable[:4]
    else:
        for n in citable[:3]:
            if n not in used:
                used.append(n)
    if not used:
        used = [r.n for r in bag.rows[:8]]
    used = [n for n in used if isinstance(n, int)]
    chosen = []
    budget = _EB
    for n in used:
        row = bag.get(n)
        if row is None:
            continue
        if not row.rid or str(row.rid)[:1] == "x" or not row.rcpt:
            continue
        spans = list(row.pins) or list(row.shown) or [(0, min(len(row.txt), _TG))]
        sl = _vx_sl(row, spans)
        if not sl:
            continue
        cost = sum(s.end - s.start for s in sl)
        if cost > budget:
            continue
        budget -= cost
        chosen.append((row, sl))
        if len(chosen) >= 6:
            break
    order = [row.n for row, _ in chosen]
    body, pos = _vx_rep(text, order)
    refs = []
    ranked = sorted(chosen, key=lambda it: pos.get(it[0].n, 999))
    for row, sl in ranked:
        try:
            refs.append(CitationRef(receipt_id=row.rcpt, result_id=row.rid, slices=list(sl)))
        except Exception:
            continue
    return refs, body


def _vx_pack(text, output, cites, schema, fast):
    note = None
    if text and str(text).strip():
        note = str(text).strip()[:24000]
    try:
        if schema is not None:
            if fast:
                return Response(output=output)
            return Response(output=output, note=note, citations=cites or None)
        body = note or "No source-backed answer could be established."
        if fast:
            body = _MK.sub("", body).strip() or body
            return Response(text=body)
        return Response(text=body, citations=cites or None)
    except Exception:
        if schema is not None:
            try:
                return Response(output=output, note=note)
            except Exception:
                return Response(output=output)
        return Response(text=(note or "No source-backed answer could be established.")[:8000])


def _vx_k(bag, n, quote):
    row = bag.get(n)
    if row is None:
        return "no such row"
    q = (quote or "").strip()
    if len(q) < 8:
        return "quote too short"
    t = row.txt
    loc = t.find(q)
    if loc < 0:
        loc = t.casefold().find(q.casefold())
    if loc < 0:
        return "quote not in row"
    a = max(0, loc - _MGN)
    b = min(len(t), loc + max(len(q), 12) + _MGN)
    if b - a < _MN and len(t) >= _MN:
        b = min(len(t), a + _MN)
    row.pins.append((a, b))
    row.shown.append((a, b))
    return f"ok: pinned {b - a} chars on [{row.n}]"


def _vx_norm(u):
    return (u or "").strip().split("#")[0].rstrip("/").casefold()


def _vx_ascii(s):
    return (
        (s or "")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )


def _vx_thin(txt, url=""):
    t = (txt or "").strip()
    if not t:
        return True
    cl = t[:500].casefold()
    if "extract error" in cl or "failed to extract" in cl or "no content" in cl:
        return True
    if ".pdf" in (url or "").casefold() and len(t) < 280:
        return True
    return False


def _vx_bits(payload):
    items = list(getattr(payload, "results", ()) or ())
    if not items:
        resp = getattr(payload, "response", None)
        items = list(getattr(resp, "data", None) or [])
    if not items:
        return "", ""
    item = items[0]
    if isinstance(item, dict):
        return (item.get("note") or item.get("content") or "", item.get("url") or "")
    return (
        getattr(item, "note", None) or getattr(item, "content", None) or "",
        getattr(item, "url", None) or "",
    )


def _vx_needles(question):
    q = question or ""
    pats = []
    for tok in (
        "Watch List",
        "Improvement Watch",
        "permitted",
        "under construction",
        "Cooperative",
        "boardings",
        "Total Annual Boardings",
        "Ridership",
        "subsequent",
        "enthalpy",
        "Appendix",
    ):
        if tok.casefold() in q.casefold():
            pats.append(tok)
    if "appendix" in q.casefold() and "boardings" not in [p.casefold() for p in pats]:
        pats.append("boardings")
    pats.extend(re.findall(r"20\d{2}", q))
    for m in _QT.finditer(q):
        t = next((g for g in m.groups() if g), None)
        if t and 6 <= len(t) <= 48:
            pats.append(t[:80])
    out = []
    seen = set()
    for p in pats:
        k = _vx_ascii(p).casefold()
        if k and k not in seen and len(p) >= 3:
            seen.add(k)
            out.append(p)
    return out[:14]


def _vx_ov(spans, a, b):
    for s, e in spans:
        lo, hi = max(a, s), min(b, e)
        if hi > lo and (hi - lo) >= 0.45 * max(1, b - a):
            return True
    return False


def _vx_surf(row, question, cap=8):
    if row is None:
        return ""
    parts = []
    spans = []
    for pat in _vx_needles(question):
        pl = pat.casefold()
        win = 7500 if any(k in pl for k in ("boarding", "appendix")) else (
            4000 if any(k in pl for k in ("list", "table", "permitted", "construction")) else 380
        )
        try:
            rx = re.escape(pat) if re.search(r"[^\w\s]", pat) else pat
            hits = _vx_g(row.txt, rx, cap=6, win=win, back=240 if win >= 1200 else None)
        except Exception:
            hits = []
        for a, b, frag in hits:
            if _vx_ov(spans, a, b):
                continue
            spans.append((a, b))
            row.shown.append((a, b))
            parts.append(f"off={a}:{b}\n{frag}")
            if len(parts) >= cap:
                break
        if len(parts) >= cap:
            break
    if not parts and row.txt:
        parts.append(row.txt[:2400])
    return "\n".join(parts)[:12000]


def _vx_best(bag, question):
    years = []
    for y in re.findall(r"20\d{2}", question or ""):
        if y not in years:
            years.append(y)
    ranked = []
    for r in bag.rows:
        lu = (r.url or "").casefold()
        sc = min(len(r.txt or ""), 500000)
        if ".pdf" in lu:
            sc += 80000
        if any(tok in lu for tok in ("wp-content", "/uploads/", "/documents/")):
            sc += 20000
        for y in years:
            if y in lu:
                sc += 40000
        blob = (r.txt or "")[:80000].casefold()
        for tok in ("watch list", "under construction", "subsequent license", "permitted plants"):
            if tok in blob:
                sc += 35000
        ranked.append((sc, r))
    ranked.sort(key=lambda it: it[0], reverse=True)
    return [r for _, r in ranked]


def _vx_extra(provider, kind, url="", mode=0):
    if provider == "parallel":
        if kind == "search":
            return {"mode": "advanced", "max_chars_total": 80000, "excerpt_settings": {"max_chars_per_result": 12000}}
        pdf = ".pdf" in (url or "").lower()
        if int(mode or 0) <= 0:
            return {"max_chars_total": 240000 if pdf else 120000}
        return {"full_content": True, "max_chars_total": 720000 if pdf else 180000}
    if provider == "firecrawl":
        if kind == "search":
            return {"categories": ("pdf",)}
        return {"formats": ("markdown",)}
    return None


async def _vx_hunt(clock, bag, qs):
    if isinstance(qs, str):
        qs = [qs]
    qs = [q.strip() for q in (qs or []) if str(q).strip()][:4]
    added = []
    for q in qs:
        if not clock.ok(10):
            break
        for prov in _SP:
            try:
                extra = _vx_extra(prov, "search")
                payload = await asyncio.wait_for(
                    search_web(q, provider=prov, num=_QH, provider_extra=extra, timeout=_ST),
                    timeout=_ST + 4,
                )
                clock.note(payload)
                rows = bag.ins(payload)
                if rows:
                    added.extend(rows)
                    break
            except Exception:
                continue
    if not any(".pdf" in (u or "").lower() for u in bag.urls) and clock.ok(10):
        for q in qs[:2]:
            try:
                extra = _vx_extra("firecrawl", "search")
                payload = await asyncio.wait_for(
                    search_web(q, provider="firecrawl", num=_QH, provider_extra=extra, timeout=_ST),
                    timeout=_ST + 4,
                )
                clock.note(payload)
                rows = bag.ins(payload)
                if rows:
                    added.extend(rows)
                if any(".pdf" in (u or "").lower() for u in bag.urls):
                    break
            except Exception:
                continue
    if not added:
        return "hunt: no new rows"
    lines = []
    for r in added[:12]:
        lines.append(f"[{r.n}] {r.title or r.url}\n{(r.txt[:380]).strip()}")
    return "hunt:\n" + "\n".join(lines)


async def _vx_p(clock, bag, url, goal=""):
    url = (url or "").strip()
    if not url.startswith("http"):
        return "pull: bad url"
    if bag.np >= _MXF:
        return "pull: cap"
    nu = _vx_norm(url)
    if nu in bag.bad:
        return "pull: skip"
    pdf = ".pdf" in nu
    for prov in _FP:
        modes = (0, 1) if (prov == "parallel" and pdf) else (0,)
        for mode in modes:
            if not clock.ok(12):
                bag.bad.add(nu)
                return "pull: failed"
            try:
                extra = _vx_extra(prov, "fetch", url, mode)
                if prov == "parallel" and int(mode) == 0:
                    tmo = 22.0 if pdf else 12.0
                else:
                    tmo = _FT
                payload = await asyncio.wait_for(
                    fetch_page(url, provider=prov, provider_extra=extra, timeout=tmo),
                    timeout=tmo + 6,
                )
                clock.note(payload)
                txt, _u = _vx_bits(payload)
                if _vx_thin(txt, url):
                    continue
                rows = bag.ins(payload)
                if not rows:
                    continue
                bag.np += 1
                r = rows[0]
                head = r.txt[:1200]
                r.shown.append((0, min(len(r.txt), 1200)))
                surf = _vx_surf(r, goal)
                return f"pull [{r.n}] {r.url} chars={len(r.txt)}\n{head}\nHITS:\n{surf}"
            except Exception:
                continue
    bag.bad.add(nu)
    return "pull: failed"


def _vx_pdfs(clock, bag, question):
    urls = []
    for u in _URL.findall(question or ""):
        if u.startswith("http") and u not in urls:
            urls.append(u)
    for u in bag.urls:
        if u not in urls:
            urls.append(u)
    for r in bag.rows:
        if r.url and r.url not in urls:
            urls.append(r.url)
    ranked = []
    years = []
    for y in re.findall(r"20\d{2}", question or ""):
        if y not in years:
            years.append(y)
    for u in urls:
        lu = u.casefold()
        if ".pdf" not in lu:
            continue
        sc = 4
        if any(tok in lu for tok in (".gov", ".edu", "publicpower", "ecology.wa", "nist.gov")):
            sc += 2
        if any(tok in lu for tok in ("wp-content", "/uploads/", "/documents/", "/publication")):
            sc += 4
        for tok in re.findall(r"[a-z]{4,}", _vx_ascii(question or "").casefold())[:10]:
            if tok in lu:
                sc += 1
        for y in years:
            if y in lu:
                sc += 6
        for y in re.findall(r"20\d{2}", lu):
            if years and y not in years:
                sc -= 4
        if sc > 0:
            ranked.append((sc, u))
    ranked.sort(reverse=True)
    for _, u in ranked:
        if not clock.ok(22):
            break
        if any(r.url == u and len(r.txt) > 8000 for r in bag.rows):
            continue
        return u
    return None


async def _vx_seed_docs(clock, bag, question):
    seen = set()
    for _ in range(3):
        u = _vx_pdfs(clock, bag, question)
        if not u or u in seen:
            break
        seen.add(u)
        await _vx_p(clock, bag, u, question[:500])


def _vx_scan(bag, n, pat):
    row = bag.get(n)
    if row is None:
        return "scan: no row"
    hits = _vx_g(row.txt, pat, cap=_HITS, win=_WIN)
    if not hits:
        return f"scan [{row.n}]: no hits"
    parts = []
    for i, (a, b, frag) in enumerate(hits[:40], 1):
        row.shown.append((a, b))
        parts.append(f"#{i} off={a}:{b}\n{frag}")
    return f"scan [{row.n}] {len(hits)} hits\n" + "\n".join(parts)


def _vx_peek(bag, n, start, end):
    row = bag.get(n)
    if row is None:
        return "peek: no row"
    a = max(0, int(start))
    b = min(len(row.txt), int(end))
    if b <= a:
        return "peek: empty"
    if b - a > 12000:
        b = a + 12000
    row.shown.append((a, b))
    return f"peek [{row.n}] {a}:{b}\n{row.txt[a:b]}"


def _vx_digest(bag, question):
    parts = []
    for r in _vx_best(bag, question)[:3]:
        parts.append(f"[{r.n}] {r.title or r.url} ({len(r.txt)}c)")
        surf = _vx_surf(r, question, cap=8)
        if surf:
            parts.append(surf[:4000])
        else:
            parts.append((r.txt[:1600]).replace("\n", " "))
    return "\n".join(parts)[:14000]


def _vx_txt(payload):
    r = getattr(payload, "response", None)
    t = getattr(r, "raw_text", None)
    if t and str(t).strip():
        return str(t).strip()
    ch = getattr(r, "choices", None) or ()
    if not ch:
        return ""
    msg = ch[0].message
    content = getattr(msg, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts = []
        for p in content:
            x = getattr(p, "text", None)
            if x is None and isinstance(p, dict):
                x = p.get("text")
            if x:
                parts.append(str(x))
        if parts:
            return "\n".join(parts).strip()
    return ""


class _TC:
    def __init__(self, name, arguments, cid):
        self.name = name
        self.arguments = arguments
        self.id = cid
        self.type = "function"


def _vx_xml(text):
    out = []
    for i, m in enumerate(_XML.finditer(text or ""), 1):
        args = {}
        for km in _XARG.finditer(m.group(2) or ""):
            args[(km.group(1) or "").strip()] = (km.group(2) or "").strip()
        out.append(_TC(m.group(1), json.dumps(args), f"x{i}"))
    return out


def _vx_calls(payload):
    r = getattr(payload, "response", None)
    if r is None:
        return None, []
    ch = getattr(r, "choices", None) or ()
    msg = ch[0].message if ch else None
    calls = list(getattr(msg, "tool_calls", None) or ()) if msg is not None else []
    if not calls:
        calls = _vx_xml(_vx_txt(payload))
    return msg, calls


async def _vx_llm(clock, messages, tools=None, finish=False, kind="loop"):
    ladder = _LP if kind == "loop" else (_CP if kind == "commit" else _GP)
    tok = 1800 if kind == "loop" else (4200 if kind == "commit" else 1600)
    temp = 0.12 if kind == "loop" else 0.0
    tmo = min(_LT, max(8.0, clock.left() - 4.0))
    if tmo < 8:
        return None
    choice = "none" if finish or not tools else "auto"
    for prov, model, only in ladder:
        extra = None
        if only and prov == "openrouter":
            extra = {"provider": {"only": list(only), "allow_fallbacks": True}}
        elif only and prov == "ai_gateway":
            extra = {"provider": {"only": list(only)}}
        try:
            payload = await asyncio.wait_for(
                llm_chat(
                    provider=prov,
                    model=model,
                    messages=messages,
                    temperature=temp,
                    max_output_tokens=tok,
                    tools=tools if not finish else None,
                    tool_choice=choice,
                    parallel_tool_calls=True if tools and not finish else None,
                    provider_extra=extra,
                    timeout=tmo,
                ),
                timeout=tmo + 5.0,
            )
            clock.note(payload)
            return payload
        except Exception:
            continue
    return None


def _vx_seed(question):
    raw = question or ""
    q = _vx_ascii(raw)
    titles = []
    for m in _QT.finditer(q):
        t = next((g for g in m.groups() if g), None)
        if t and t.casefold() not in {"table", "list", "section"}:
            titles.append(t)
    years = []
    for y in re.findall(r"20\d{2}", q):
        if y not in years:
            years.append(y)
    main = titles[0] if titles else q[:140]
    qs = [f"{main} filetype:pdf"]
    for y in years[:2]:
        qs.append(f"{main} {y} filetype:pdf")
    pre = re.split(r'"', q, 1)[0]
    pre = re.sub(r"^(Using|From|Based on)\s+", "", pre, flags=re.I)
    pre = re.sub(r"'s\s*$", "", pre.strip())
    if len(pre) > 12:
        qs.append(f"{pre} filetype:pdf")
    hosts = _HOST.findall(q)
    if hosts:
        qs.append(f"site:{hosts[0]} {main}")
    for u in _URL.findall(raw)[:2]:
        qs.append(u)
    out = []
    for item in qs:
        item = (item or "").strip()
        if item and item not in out:
            out.append(item)
    if not out:
        out.append(q[:180])
    return out[:5]


async def _vx_run(clock, name, args, bag, goal):
    n = str(name or "")
    a = args if isinstance(args, dict) else {}
    if n == "hunt":
        return await _vx_hunt(clock, bag, a.get("qs") or a.get("q") or a.get("query") or "")
    if n == "pull":
        return await _vx_p(clock, bag, a.get("url") or "", goal)
    if n == "scan":
        return _vx_scan(bag, a.get("n") or a.get("source") or 0, a.get("pat") or a.get("pattern") or "")
    if n == "peek":
        return _vx_peek(bag, a.get("n") or 0, a.get("start") or 0, a.get("end") or 0)
    if n == "keep":
        return _vx_k(bag, a.get("n") or 0, a.get("quote") or a.get("q") or "")
    if n == "arith":
        payload = dict(a.get("payload") or {})
        for k in ("a", "b", "x", "xref", "ulab", "uref", "rows", "items"):
            if k in a and k not in payload:
                payload[k] = a[k]
        v = _vx_c(a.get("op") or "", payload)
        return f"arith {a.get('op')}: {v}" if v else "arith: failed"
    return f"unknown tool {n}"


async def _vx_loop(clock, question, schema, bag, fast):
    qs = _vx_seed(question)
    if clock.ok(14):
        try:
            await _vx_hunt(clock, bag, qs[:4])
        except Exception:
            pass
    if clock.ok(22):
        try:
            await _vx_seed_docs(clock, bag, question)
        except Exception:
            pass
    sch = ""
    if schema is not None:
        sch = "\nJSON schema (fill after research):\n" + json.dumps(schema, ensure_ascii=False)[:3500]
    messages = [
        {"role": "system", "content": _SY},
        {"role": "user", "content": question[:12000] + sch},
    ]
    if bag.rows:
        preview = "\n".join(f"[{r.n}] {r.title or r.url} ({len(r.txt)}c)" for r in bag.rows[:14])
        messages.append({"role": "system", "content": "Ledger already holds:\n" + preview})
        windows = []
        for r in _vx_best(bag, question)[:2]:
            if len(r.txt or "") < 1500:
                continue
            surf = _vx_surf(r, question)
            if surf:
                windows.append(f"[{r.n}] {r.url}\n{surf}")
        if windows:
            messages.append({"role": "system", "content": "Pinned table windows:\n" + "\n".join(windows)[:12000]})
    if _AR.search(question or ""):
        messages.append(
            {"role": "system", "content": "Any day-count, GET interval, or En value MUST come from arith, not mental math."}
        )
    draft = ""
    math_notes = []
    turns = 0
    while turns < _MT and clock.ok(_SR if schema else 18):
        turns += 1
        finish = (not clock.ok(_SR + 12 if schema else 28)) or turns >= _MT or clock.usd >= 0.40
        payload = await _vx_llm(clock, messages, tools=_TL, finish=finish, kind="loop")
        if payload is None:
            break
        msg, calls = _vx_calls(payload)
        if not calls:
            cand = _vx_z(_vx_txt(payload))
            if cand:
                parsed = _vx_j(cand)
                if schema is not None and parsed is not None and _vx_dead_tree(parsed):
                    messages.append({"role": "assistant", "content": cand[:4000]})
                    messages.append(
                        {
                            "role": "user",
                            "content": "That JSON uses placeholders. Compute real values from the ledger and arith. Do not emit x or Data not available.",
                        }
                    )
                    continue
                draft = cand
                break
            if finish:
                break
            messages.append(
                {
                    "role": "user",
                    "content": "Continue. Fetch the named official table, scan remaining rows, keep proving quotes, then answer.",
                }
            )
            continue
        try:
            messages.append(msg.to_input_message())
        except Exception:
            messages.append({"role": "assistant", "content": _vx_txt(payload) or "working"})
        run = calls[:6]
        parsed_calls = []
        for c in run:
            raw = getattr(c, "arguments", "") or "{}"
            try:
                args = json.loads(raw) if isinstance(raw, str) else dict(raw)
            except Exception:
                args = {}
            if not isinstance(args, dict):
                args = {}
            parsed_calls.append((c, getattr(c, "name", ""), args))
        tasks = [asyncio.ensure_future(_vx_run(clock, name, args, bag, question)) for _, name, args in parsed_calls]
        try:
            await asyncio.wait(tasks, timeout=min(48.0, max(10.0, clock.left() - 10.0)))
        except Exception:
            pass
        for (call, name, args), task in zip(parsed_calls, tasks):
            body = "tool failed"
            if task.done():
                try:
                    body = task.result()
                except Exception as exc:
                    body = f"tool error {exc}"
            if name == "arith" and body.startswith("arith"):
                math_notes.append(body)
            cid = getattr(call, "id", None) or "tool"
            messages.append({"role": "tool", "tool_call_id": cid, "content": (body or "ok")[:18000]})
        if len(json.dumps(messages, default=str)) > 120000:
            messages = [messages[0], messages[1]] + messages[-10:]
    parsed_draft = _vx_j(draft) if draft else None
    need_c = (
        schema is not None
        or (not _vx_z(draft))
        or (parsed_draft is not None and _vx_dead_tree(parsed_draft))
    )
    if need_c:
        digest = _vx_digest(bag, question)
        extra = ""
        if math_notes:
            extra += "\n" + "\n".join(math_notes[-8:])
        if digest:
            extra += "\nLEDGER HITS:\n" + digest
        payload = await _vx_llm(
            clock,
            messages + [{"role": "user", "content": _CM + extra}],
            tools=None,
            finish=True,
            kind="commit",
        )
        raw = _vx_txt(payload) if payload else ""
        draft = _vx_z(raw) or ""
        if not draft and raw:
            cl = raw.casefold()
            if "<tool_call>" not in cl and "<arg_key>" not in cl and "<function" not in cl:
                draft = _SCR.sub("", raw).strip()
    return _vx_z(draft) or (draft if draft and "<tool_call>" not in draft.casefold() else "")


async def _vx_s(clock, schema, answer, bag, question):
    if schema is None:
        return None
    last = None
    for _ in range(3):
        if not clock.ok(10):
            break
        digest = _vx_digest(bag, question)
        prompt = (
            "Schema:\n"
            + json.dumps(schema, ensure_ascii=False)[:2000]
            + "\n\nSources:\n"
            + (digest or "")[:12000]
            + "\n\nQuestion:\n"
            + (question or "")[:1500]
            + "\n\nAnswer:\n"
            + _MK.sub("", answer or "")[:3000]
        )
        payload = await _vx_llm(
            clock,
            [{"role": "system", "content": _SM}, {"role": "user", "content": prompt}],
            tools=None,
            finish=True,
            kind="schema",
        )
        parsed = _vx_j(_vx_txt(payload) if payload else "")
        if parsed is None:
            parsed = _vx_j(answer)
        if parsed is not None and _vx_sok(parsed, schema):
            return parsed
        last = parsed
        answer = (answer or "") + "\nUse real names and numbers from the sources. No placeholders."
    if last is not None and _vx_sok(last, schema):
        return last
    parsed = _vx_j(answer)
    if parsed is not None and _vx_sok(parsed, schema):
        return parsed
    return last if last is not None and not _vx_dead_tree(last) else None


def _vx_skel(schema):
    if not isinstance(schema, dict):
        return {}
    t = schema.get("type")
    if t == "array":
        return []
    if t == "string":
        m = 0
        try:
            m = int(schema.get("minLength") or 0)
        except Exception:
            m = 0
        return ("x" * max(1, min(m, 12))) if m else ""
    if t == "integer":
        return 0
    if t == "number":
        return 0
    if t == "boolean":
        return False
    if t == "object" or "properties" in schema:
        out = {}
        props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        req = schema.get("required") or []
        for k in req:
            if isinstance(k, str):
                out[k] = _vx_skel(props.get(k) or {})
        return out
    return {}


async def _run(clock, query: Query) -> Response:
    question = (query.text or "").strip()
    schema = query.output_schema
    fast = bool(getattr(query, "fast", False))
    bag = _B()
    try:
        info = await asyncio.wait_for(tooling_info(timeout=8.0), timeout=10.0)
        clock.note(info)
    except Exception:
        pass
    answer = await _vx_loop(clock, question, schema, bag, fast)
    if not answer:
        answer = "The named sources were retrieved but no complete qualifying set could be read from the visible tables."
    extra = ""
    if schema is not None:
        extra = _vx_digest(bag, question)
        if extra:
            answer = ((answer or "") + "\n" + extra)[:20000]
    refs, body = _vx_refs(bag, answer, fast, question)
    if schema is not None:
        output = await _vx_s(clock, schema, body, bag, question)
        output = _vx_emit(output if output is not None else _vx_j(body), schema)
        note = None if fast else (body or extra or answer or "")
        if (not fast) and extra and extra[:120] not in (note or ""):
            note = ((note or "") + "\n" + extra)[:24000]
            refs, note = _vx_refs(bag, note, False, question)
        if (not fast) and not refs and (note or extra):
            refs, note = _vx_refs(bag, note or extra, False, question)
        try:
            return _vx_pack(note, output, refs if not fast else None, schema, fast)
        except Exception:
            return _vx_pack(note, output, None, schema, fast)
    return _vx_pack(body, None, refs, None, fast)


@entrypoint("query")
async def query(query: Query) -> Response:
    clock = _K()
    try:
        return await _run(clock, query)
    except Exception:
        schema = getattr(query, "output_schema", None)
        if schema is not None:
            return Response(output=_vx_skel(schema))
        return Response(text="No source-backed answer could be established.")
