#!/usr/bin/env python3
"""Extract LLM/search/fetch providers from agent scripts and enrich history files."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

KNOWN_LLM = frozenset({"openrouter", "chutes", "ai_gateway"})
KNOWN_SEARCH = frozenset({"parallel", "desearch"})


def extract_providers(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    llm: set[str] = set()
    search: set[str] = set()
    fetch: set[str] = set()
    models: set[str] = set()

    for m in re.finditer(
        r"(?:LLM_LANE(?:_[AB])?|PROVIDER|_PROVIDER)\s*=\s*['\"]([^'\"]+)['\"]",
        text,
    ):
        v = m.group(1).strip()
        if v in KNOWN_LLM:
            llm.add(v)

    for m in re.finditer(r"SEARCH_PROVIDER\s*=\s*['\"]([^'\"]+)['\"]", text):
        search.add(m.group(1).strip())

    for m in re.finditer(r"FETCH_PROVIDER\s*=\s*['\"]([^'\"]+)['\"]", text):
        fetch.add(m.group(1).strip())

    for m in re.finditer(
        r"provider\s*=\s*['\"](openrouter|chutes|ai_gateway|parallel|desearch)['\"]",
        text,
    ):
        v = m.group(1)
        if v in KNOWN_LLM:
            llm.add(v)
        else:
            search.add(v)

    for m in re.finditer(r"for\s+provider(?:_name)?\s+in\s+\(([^)]+)\)", text):
        for q in re.findall(r"['\"]([^'\"]+)['\"]", m.group(1)):
            if q in KNOWN_LLM:
                llm.add(q)
            elif q in KNOWN_SEARCH:
                search.add(q)

    if "_S17_CLAIM_SEARCH_ATTEMPTS" in text:
        for m in re.finditer(r'\("(exa|tavily|parallel|desearch|firecrawl)"', text):
            search.add(m.group(1))

    for m in re.finditer(r"fetch_page\([^)]*provider\s*=\s*['\"]([^'\"]+)['\"]", text):
        fetch.add(m.group(1))

    for m in re.finditer(r"_S\d+_MODEL\s*=\s*['\"]([^'\"]+)['\"]", text):
        models.add(m.group(1))

    for m in re.finditer(r"model\s*=\s*['\"]([^'\"/@]+/[^'\"]+)['\"]", text):
        models.add(m.group(1))

    for m in re.finditer(r"MODEL(?:_LADDER)?\s*=\s*\(([^)]+)\)", text):
        first = re.search(r"['\"]([^'\"]+)['\"]", m.group(1))
        if first:
            models.add(first.group(1))

    llm_sorted = sorted(llm)
    search_sorted = sorted(search)
    fetch_sorted = sorted(fetch)
    models_sorted = sorted(models)

    return {
        "llm_providers": llm_sorted,
        "search_providers": search_sorted,
        "fetch_providers": fetch_sorted,
        "models": models_sorted[:12],
        "primary_llm_provider": llm_sorted[0] if llm_sorted else None,
        "primary_search_provider": search_sorted[0] if search_sorted else None,
        "providers_summary": _summary(llm_sorted, search_sorted, fetch_sorted),
    }


def _summary(llm: list[str], search: list[str], fetch: list[str]) -> str:
    parts = []
    if llm:
        parts.append("llm:" + "+".join(llm))
    if search:
        parts.append("search:" + "+".join(search))
    if fetch:
        parts.append("fetch:" + "+".join(fetch))
    return " | ".join(parts)


def enrich_entry(entry: dict, agent_path: Path) -> dict:
    out = dict(entry)
    prov = extract_providers(agent_path)
    out["providers"] = prov
    out["llm_providers"] = prov["llm_providers"]
    out["search_providers"] = prov["search_providers"]
    out["fetch_providers"] = prov["fetch_providers"]
    out["primary_llm_provider"] = prov["primary_llm_provider"]
    out["primary_search_provider"] = prov["primary_search_provider"]
    out["providers_summary"] = prov["providers_summary"]
    if prov["models"]:
        out["models"] = prov["models"]
    return out


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def update_submitted(dir_path: Path) -> None:
    hist_path = dir_path / "submission_history.json"
    if not hist_path.exists():
        return
    hist = json.loads(hist_path.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    entries = []
    for e in hist.get("entries", []):
        agent_path = Path(e.get("agent_path", dir_path / e["filename"]))
        if not agent_path.is_file():
            agent_path = dir_path / e["filename"]
        entries.append(enrich_entry(e, agent_path))

    hist["entries"] = entries
    hist["providers_enriched_at"] = now

    write_json(hist_path, hist)
    stamped = sorted(dir_path.glob("submission_history_*.json"))
    if stamped:
        write_json(stamped[-1], hist)

    map_path = dir_path / "hotkey_map.json"
    if map_path.exists():
        mp = json.loads(map_path.read_text(encoding="utf-8"))
        mp["providers_enriched_at"] = now
        mp_entries = []
        for e in mp.get("entries", []):
            agent_path = Path(e.get("agent_path", dir_path / e["filename"]))
            if not agent_path.is_file():
                agent_path = dir_path / e["filename"]
            pe = dict(e)
            prov = extract_providers(agent_path)
            pe["llm_providers"] = prov["llm_providers"]
            pe["search_providers"] = prov["search_providers"]
            pe["fetch_providers"] = prov["fetch_providers"]
            pe["primary_llm_provider"] = prov["primary_llm_provider"]
            pe["primary_search_provider"] = prov["primary_search_provider"]
            pe["providers_summary"] = prov["providers_summary"]
            if prov["models"]:
                pe["models"] = prov["models"]
            mp_entries.append(pe)
        mp["entries"] = mp_entries
        write_json(map_path, mp)

        tsv_lines = [
            "hotkey_name\thotkey_address\ton_chain_uid\tagent_name\tfilename\t"
            "primary_llm_provider\tprimary_search_provider\tproviders_summary\t"
            "artifact_id\tsubmitted_at\tdate"
        ]
        for e in mp_entries:
            tsv_lines.append(
                f"{e['hotkey_name']}\t{e['hotkey_address']}\t{e['on_chain_uid']}\t"
                f"{e['agent_name']}\t{e['filename']}\t"
                f"{e.get('primary_llm_provider','')}\t{e.get('primary_search_provider','')}\t"
                f"{e.get('providers_summary','')}\t"
                f"{e.get('artifact_id','')}\t{e.get('submitted_at','')}\t{e['date']}"
            )
        (dir_path / "hotkey_map.tsv").write_text("\n".join(tsv_lines) + "\n", encoding="utf-8")


def update_unsubmitted(dir_path: Path) -> None:
    for name in ("unsubmitted_agents.json", "submission_history.json"):
        hist_path = dir_path / name
        if not hist_path.exists():
            continue
        hist = json.loads(hist_path.read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entries = []
        for e in hist.get("entries", []):
            agent_path = Path(e.get("agent_path", dir_path / e["filename"]))
            if not agent_path.is_file():
                agent_path = dir_path / e["filename"]
            entries.append(enrich_entry(e, agent_path))
        hist["entries"] = entries
        hist["providers_enriched_at"] = now
        write_json(hist_path, hist)

    stamped = sorted(dir_path.glob("submission_history_*.json"))
    if stamped and (dir_path / "submission_history.json").exists():
        write_json(stamped[-1], json.loads((dir_path / "submission_history.json").read_text()))

    tsv_lines = [
        "filename\tagent_uid_label\tprimary_llm_provider\tprimary_search_provider\t"
        "providers_summary\tstatus\tsource_dir"
    ]
    ua_path = dir_path / "unsubmitted_agents.json"
    if ua_path.exists():
        hist = json.loads(ua_path.read_text())
        for e in hist.get("entries", []):
            tsv_lines.append(
                f"{e['filename']}\t{e['agent_uid_label']}\t"
                f"{e.get('primary_llm_provider','')}\t{e.get('primary_search_provider','')}\t"
                f"{e.get('providers_summary','')}\t{e['status']}\t{e.get('source_dir','')}"
            )
        (dir_path / "unsubmitted_agents.tsv").write_text("\n".join(tsv_lines) + "\n", encoding="utf-8")

    map_path = dir_path / "hotkey_map.json"
    if map_path.exists():
        mp = json.loads(map_path.read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        mp["providers_enriched_at"] = now
        mp_entries = []
        for e in mp.get("entries", []):
            agent_path = Path(e.get("agent_path", dir_path / e["filename"]))
            if not agent_path.is_file():
                agent_path = dir_path / e["filename"]
            pe = dict(e)
            if agent_path.is_file():
                prov = extract_providers(agent_path)
                pe["llm_providers"] = prov["llm_providers"]
                pe["search_providers"] = prov["search_providers"]
                pe["fetch_providers"] = prov["fetch_providers"]
                pe["primary_llm_provider"] = prov["primary_llm_provider"]
                pe["primary_search_provider"] = prov["primary_search_provider"]
                pe["providers_summary"] = prov["providers_summary"]
                if prov["models"]:
                    pe["models"] = prov["models"]
            mp_entries.append(pe)
        mp["entries"] = mp_entries
        write_json(map_path, mp)

        tsv_lines = [
            "hotkey_name\thotkey_address\ton_chain_uid\tagent_name\tfilename\t"
            "primary_llm_provider\tprimary_search_provider\tproviders_summary\tdate"
        ]
        for e in mp_entries:
            tsv_lines.append(
                f"{e['hotkey_name']}\t{e['hotkey_address']}\t{e['on_chain_uid']}\t"
                f"{e['agent_name']}\t{e['filename']}\t"
                f"{e.get('primary_llm_provider','')}\t{e.get('primary_search_provider','')}\t"
                f"{e.get('providers_summary','')}\t{e.get('date','')}"
            )
        (dir_path / "hotkey_map.tsv").write_text("\n".join(tsv_lines) + "\n", encoding="utf-8")


def update_submittion17(dir_path: Path) -> None:
    hist_path = dir_path / "submission_history.json"
    if not hist_path.exists():
        return
    hist = json.loads(hist_path.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if hist.get("entries"):
        entries = []
        for e in hist["entries"]:
            agent_path = Path(e.get("agent_path", dir_path / e["filename"]))
            entries.append(enrich_entry(e, agent_path))
        hist["entries"] = entries

    unmatched = []
    for item in hist.get("unmatched_agents", []) or hist.get("leftover_unmatched_agents", []):
        if isinstance(item, str):
            fn = item
            agent_path = dir_path / fn
            unmatched.append(enrich_entry({
                "filename": fn,
                "agent_path": str(agent_path),
                "agent_name": fn.split("__")[0],
            }, agent_path))
        elif isinstance(item, dict):
            agent_path = Path(item.get("agent_path", dir_path / item["filename"]))
            unmatched.append(enrich_entry(item, agent_path))

    if unmatched:
        hist["unmatched_agents_with_providers"] = unmatched

    hist["providers_enriched_at"] = now
    write_json(hist_path, hist)

    map_path = dir_path / "hotkey_map.json"
    if map_path.exists():
        mp = json.loads(map_path.read_text(encoding="utf-8"))
        mp["providers_enriched_at"] = now
        mp_entries = []
        for e in mp.get("entries", []):
            agent_path = Path(e.get("agent_path", dir_path / e["filename"]))
            pe = dict(e)
            prov = extract_providers(agent_path)
            pe.update({
                "llm_providers": prov["llm_providers"],
                "search_providers": prov["search_providers"],
                "fetch_providers": prov["fetch_providers"],
                "primary_llm_provider": prov["primary_llm_provider"],
                "primary_search_provider": prov["primary_search_provider"],
                "providers_summary": prov["providers_summary"],
            })
            if prov["models"]:
                pe["models"] = prov["models"]
            mp_entries.append(pe)
        mp["entries"] = mp_entries
        write_json(map_path, mp)

        tsv_lines = [
            "hotkey_name\thotkey_address\ton_chain_uid\tagent_name\tfilename\t"
            "primary_llm_provider\tprimary_search_provider\tproviders_summary\tdate"
        ]
        for e in mp_entries:
            tsv_lines.append(
                f"{e['hotkey_name']}\t{e['hotkey_address']}\t{e['on_chain_uid']}\t"
                f"{e['agent_name']}\t{e['filename']}\t"
                f"{e.get('primary_llm_provider','')}\t{e.get('primary_search_provider','')}\t"
                f"{e.get('providers_summary','')}\t{e['date']}"
            )
        (dir_path / "hotkey_map.tsv").write_text("\n".join(tsv_lines) + "\n", encoding="utf-8")


def main() -> None:
    root = Path("/root/turtle/111/67")
    update_submitted(root / "sub17-submitted")
    update_unsubmitted(root / "sub17-unsubmitted")
    update_submittion17(root / "submittion17")

    # also enrich sub16 folders if present
    sub16_unsub = root / "sub16-unsubmitted"
    if (sub16_unsub / "unsubmitted_agents.json").exists() or (sub16_unsub / "hotkey_map.json").exists():
        update_unsubmitted(sub16_unsub)
    sub16_sub = root / "sub16-submitted"
    if (sub16_sub / "submission_history.json").exists():
        update_submitted(sub16_sub)

    print("Provider enrichment complete.")
    sample = extract_providers(root / "submittion17" / "uid_87__artifact_62e9371e-f665-4e02-97d3-8c4f438ec0c1.py")
    print("sample uid_87:", sample)


if __name__ == "__main__":
    main()
