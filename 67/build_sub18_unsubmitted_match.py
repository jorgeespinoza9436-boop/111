#!/usr/bin/env python3
"""Randomly match sub18-unsubmitted agents to registered SN67 hotkeys.

Excludes uid_14, uid_26, uid_43, uid_53.
"""
from __future__ import annotations

import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from enrich_history_providers import enrich_entry

AGENT_DIR = Path("/root/turtle/111/67/sub18-unsubmitted")
WALLET_NAME = "money"
NETUID = 67
NETWORK = "finney"
RANDOM_SEED = 20260807091  # sub18-unsubmitted, exclude uid_14/26/43/53
EXCLUDED_AGENT_UIDS = frozenset({"uid_14", "uid_26", "uid_43", "uid_53"})


def _agent_uid_label(filename: str) -> str:
    m = re.match(r"(uid_\d+)__", filename)
    return m.group(1) if m else filename


def _is_excluded_agent(filename: str) -> bool:
    return _agent_uid_label(filename) in EXCLUDED_AGENT_UIDS


def _fetch_registered_hotkeys() -> list[dict]:
    from bittensor.core.subtensor import Subtensor
    import bittensor as bt

    subtensor = Subtensor(network=NETWORK)
    metagraph = subtensor.metagraph(NETUID)
    wallet_dir = Path.home() / f".bittensor/wallets/{WALLET_NAME}/hotkeys"
    registered: list[dict] = []
    for hk_path in sorted(wallet_dir.iterdir()):
        if hk_path.name.endswith("pub.txt"):
            continue
        hk_name = hk_path.name
        try:
            ss58 = bt.Wallet(name=WALLET_NAME, hotkey=hk_name).hotkey.ss58_address
        except Exception:
            continue
        if ss58 not in metagraph.hotkeys:
            continue
        uid = metagraph.hotkeys.index(ss58)
        registered.append(
            {
                "hotkey_name": hk_name,
                "hotkey_address": ss58,
                "hotkey_ss58": ss58,
                "on_chain_uid": uid,
            }
        )
    registered.sort(key=lambda x: x["hotkey_name"])
    return registered


def _eligible_agents() -> list[Path]:
    agents = []
    for path in sorted(AGENT_DIR.glob("uid_*.py")):
        if _is_excluded_agent(path.name):
            continue
        agents.append(path)
    return agents


def main() -> None:
    now = datetime.now(timezone.utc)
    created_at = now.isoformat().replace("+00:00", "Z")
    date_str = now.strftime("%Y-%m-%d")
    timestamp_slug = now.strftime("%Y%m%dT%H%M%SZ")

    registered = _fetch_registered_hotkeys()
    agents = _eligible_agents()
    if not agents:
        raise SystemExit(f"No eligible agents in {AGENT_DIR}")
    if not registered:
        raise SystemExit(f"No registered hotkeys found on SN{NETUID}")

    match_count = min(len(agents), len(registered))
    available = list(registered)

    rng = random.Random(RANDOM_SEED)
    picked_hotkeys = available.copy()
    rng.shuffle(picked_hotkeys)
    picked_hotkeys = picked_hotkeys[:match_count]

    picked_agents = agents.copy()
    rng.shuffle(picked_agents)
    picked_agents = picked_agents[:match_count]

    pairs = list(zip(picked_hotkeys, picked_agents))
    pairs.sort(key=lambda p: p[0]["hotkey_name"])

    coldkey = None
    try:
        import bittensor as bt

        coldkey = bt.Wallet(name=WALLET_NAME).coldkeypub.ss58_address
    except Exception:
        pass

    entries = []
    jobs_lines = []
    map_entries = []

    for hk, agent_path in pairs:
        filename = agent_path.name
        agent_uid = _agent_uid_label(filename)
        base = {
            "hotkey_name": hk["hotkey_name"],
            "hotkey_address": hk["hotkey_address"],
            "hotkey_ss58": hk["hotkey_ss58"],
            "on_chain_uid": hk["on_chain_uid"],
            "uid": hk["on_chain_uid"],
            "agent_name": agent_uid,
            "agent_uid_label": agent_uid,
            "filename": filename,
            "agent_path": str(agent_path),
            "date": date_str,
            "matched_at": created_at,
            "match": "random",
            "random_seed": RANDOM_SEED,
            "wallet_name": WALLET_NAME,
            "netuid": NETUID,
            "network": NETWORK,
            "status": "matched_pending_submit",
            "submit_status": "pending",
        }
        entry = enrich_entry(base, agent_path)
        entries.append(entry)
        jobs_lines.append(f"{hk['hotkey_name']}\t{agent_path}")

        map_entries.append(
            {
                "hotkey_name": hk["hotkey_name"],
                "hotkey_address": hk["hotkey_address"],
                "on_chain_uid": hk["on_chain_uid"],
                "agent_name": agent_uid,
                "filename": filename,
                "agent_path": str(agent_path),
                "date": date_str,
                "primary_llm_provider": entry.get("primary_llm_provider"),
                "primary_search_provider": entry.get("primary_search_provider"),
                "llm_providers": entry.get("llm_providers"),
                "search_providers": entry.get("search_providers"),
                "fetch_providers": entry.get("fetch_providers"),
                "providers_summary": entry.get("providers_summary"),
                "models": entry.get("models"),
            }
        )

    leftover_agents = sorted(set(a.name for a in agents) - {e["filename"] for e in entries})
    leftover_hotkeys = sorted(
        set(h["hotkey_name"] for h in available) - {e["hotkey_name"] for e in entries}
    )

    hotkey_map = {
        "created_at": created_at,
        "wallet_name": WALLET_NAME,
        "coldkey_ss58": coldkey,
        "netuid": NETUID,
        "network": NETWORK,
        "match": "random",
        "random_seed": RANDOM_SEED,
        "match_count": match_count,
        "registered_hotkey_count": len(registered),
        "excluded_agent_uids": sorted(EXCLUDED_AGENT_UIDS),
        "source": "sub18-unsubmitted",
        "available_hotkey_count": len(available),
        "entries": map_entries,
    }

    history = {
        "created_at": created_at,
        "wallet_name": WALLET_NAME,
        "coldkey_ss58": coldkey,
        "netuid": NETUID,
        "network": NETWORK,
        "agent_dir": str(AGENT_DIR),
        "match": "random",
        "random_seed": RANDOM_SEED,
        "match_count": match_count,
        "registered_hotkey_count": len(registered),
        "excluded_agent_uids": sorted(EXCLUDED_AGENT_UIDS),
        "source": "sub18-unsubmitted",
        "available_hotkey_count": len(available),
        "matched_count": len(entries),
        "agent_count_total_in_dir": len(list(AGENT_DIR.glob("uid_*.py"))),
        "agent_count_eligible": len(agents),
        "leftover_available_hotkeys": leftover_hotkeys,
        "leftover_unmatched_agents": leftover_agents,
        "excluded_agents_present": sorted(
            p.name for p in AGENT_DIR.glob("uid_*.py") if _is_excluded_agent(p.name)
        ),
        "entries": entries,
    }

    AGENT_DIR.mkdir(parents=True, exist_ok=True)
    (AGENT_DIR / "hotkey_map.json").write_text(
        json.dumps(hotkey_map, indent=2) + "\n", encoding="utf-8"
    )
    tsv_lines = [
        "hotkey_name\thotkey_address\ton_chain_uid\tagent_name\tfilename\t"
        "primary_llm_provider\tprimary_search_provider\tproviders_summary\tdate"
    ]
    for e in map_entries:
        tsv_lines.append(
            f"{e['hotkey_name']}\t{e['hotkey_address']}\t{e['on_chain_uid']}\t"
            f"{e['agent_name']}\t{e['filename']}\t"
            f"{e.get('primary_llm_provider') or ''}\t{e.get('primary_search_provider') or ''}\t"
            f"{e.get('providers_summary') or ''}\t{e['date']}"
        )
    (AGENT_DIR / "hotkey_map.tsv").write_text("\n".join(tsv_lines) + "\n", encoding="utf-8")
    (AGENT_DIR / "submit_jobs.txt").write_text("\n".join(jobs_lines) + "\n", encoding="utf-8")
    (AGENT_DIR / "submission_history.json").write_text(
        json.dumps(history, indent=2) + "\n", encoding="utf-8"
    )
    stamped = AGENT_DIR / f"submission_history_{timestamp_slug}.json"
    stamped.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")

    submit_all = AGENT_DIR / "submit_all.sh"
    submit_all.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
# Submit matched sub18-unsubmitted agents in parallel.
# Usage: bash /root/turtle/111/67/sub18-unsubmitted/submit_all.sh [PARALLEL_JOBS]
ROOT="/root/turtle/harnyx"
JOBS_FILE="/root/turtle/111/67/sub18-unsubmitted/submit_jobs.txt"
PARALLEL_JOBS="${{1:-{match_count}}}"
WALLET="money"
cd "$ROOT"
echo "Submitting $(wc -l < "$JOBS_FILE") agents with PARALLEL_JOBS=$PARALLEL_JOBS ..."
running=0
fail=0
ok=0
while IFS=$'\\t' read -r HOTKEY AGENT; do
  [[ -z "${{HOTKEY:-}}" ]] && continue
  (
    echo "[START] $HOTKEY <- $(basename "$AGENT")"
    if uv run --package harnyx-miner harnyx-miner-submit \\
        --wallet-name "$WALLET" \\
        --hotkey-name "$HOTKEY" \\
        --agent-path "$AGENT"; then
      echo "[OK] $HOTKEY"
    else
      echo "[FAIL] $HOTKEY" >&2
      exit 1
    fi
  ) &
  running=$((running + 1))
  if (( running >= PARALLEL_JOBS )); then
    if wait -n; then
      ok=$((ok + 1))
    else
      fail=$((fail + 1))
    fi
    running=$((running - 1))
  fi
done < "$JOBS_FILE"
while (( running > 0 )); do
  if wait -n; then
    ok=$((ok + 1))
  else
    fail=$((fail + 1))
  fi
  running=$((running - 1))
done
echo "Done. ok≈$ok fail≈$fail (counts approximate with wait -n)"
""",
        encoding="utf-8",
    )
    submit_all.chmod(0o755)

    (AGENT_DIR / "SUBMIT_COMMAND.txt").write_text(
        f"""# Submit sub18-unsubmitted agents ({match_count} of {len(registered)} registered hotkeys)
# Excluded agents: {", ".join(sorted(EXCLUDED_AGENT_UIDS))}
# History: {stamped}
# Map:     {AGENT_DIR / "hotkey_map.json"}
# Seed:    {RANDOM_SEED}

cd /root/turtle/harnyx
bash /root/turtle/111/67/sub18-unsubmitted/submit_all.sh {match_count}
""",
        encoding="utf-8",
    )

    print(f"Matched {len(entries)} pairs (seed={RANDOM_SEED})")
    print(f"Source: sub18-unsubmitted; excluded={sorted(EXCLUDED_AGENT_UIDS)}")
    print(f"Registered={len(registered)} matched_hotkeys={len(entries)} leftover_hotkeys={len(leftover_hotkeys)}")
    print(f"Eligible agents={len(agents)} leftover_agents={len(leftover_agents)}")
    for e in entries:
        print(
            f"  {e['hotkey_name']} (uid={e['on_chain_uid']}) <- {e['filename']} "
            f"[{e.get('providers_summary')}]"
        )
    if leftover_hotkeys:
        print("Leftover unmatched hotkeys:")
        for name in leftover_hotkeys:
            print(f"  {name}")
    if leftover_agents:
        print("Leftover unmatched agents:")
        for name in leftover_agents:
            print(f"  {name}")
    print(f"\nSubmit all:\n  bash /root/turtle/111/67/sub18-unsubmitted/submit_all.sh {match_count}")


if __name__ == "__main__":
    main()
