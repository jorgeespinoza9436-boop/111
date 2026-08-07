#!/usr/bin/env python3
"""Randomly match N agents from submittion17 to N registered SN67 hotkeys."""
from __future__ import annotations

import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

AGENT_DIR = Path("/root/turtle/111/67/submittion17")
WALLET_NAME = "money"
NETUID = 67
NETWORK = "finney"
MATCH_COUNT = 9
RANDOM_SEED = 202608069  # submittion17 batch of 9


def _agent_uid_label(filename: str) -> str:
    m = re.match(r"(uid_\d+)__", filename)
    return m.group(1) if m else filename


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
        registered.append({
            "hotkey_name": hk_name,
            "hotkey_address": ss58,
            "hotkey_ss58": ss58,
            "on_chain_uid": uid,
        })
    registered.sort(key=lambda x: x["hotkey_name"])
    return registered


def main() -> None:
    now = datetime.now(timezone.utc)
    created_at = now.isoformat().replace("+00:00", "Z")
    date_str = now.strftime("%Y-%m-%d")
    timestamp_slug = now.strftime("%Y%m%dT%H%M%SZ")

    agents = sorted(AGENT_DIR.glob("uid_*.py"))
    if not agents:
        raise SystemExit(f"No agents found in {AGENT_DIR}")

    registered = _fetch_registered_hotkeys()
    if len(registered) < MATCH_COUNT:
        raise SystemExit(
            f"Need {MATCH_COUNT} registered hotkeys, found {len(registered)} on SN{NETUID}"
        )

    rng = random.Random(RANDOM_SEED)
    picked_hotkeys = registered.copy()
    rng.shuffle(picked_hotkeys)
    picked_hotkeys = picked_hotkeys[:MATCH_COUNT]

    picked_agents = agents.copy()
    rng.shuffle(picked_agents)
    picked_agents = picked_agents[:MATCH_COUNT]

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
    tsv_lines = ["hotkey_name\thotkey_address\ton_chain_uid\tagent_name\tfilename\tdate"]

    for hk, agent_path in pairs:
        filename = agent_path.name
        agent_uid = _agent_uid_label(filename)
        entry = {
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
        entries.append(entry)
        jobs_lines.append(f"{hk['hotkey_name']}\t{agent_path}")
        tsv_lines.append(
            f"{hk['hotkey_name']}\t{hk['hotkey_address']}\t{hk['on_chain_uid']}\t{agent_uid}\t{filename}\t{date_str}"
        )

    leftover_agents = sorted(
        set(a.name for a in agents) - {e["filename"] for e in entries}
    )
    leftover_hotkeys = sorted(
        set(h["hotkey_name"] for h in registered) - {e["hotkey_name"] for e in entries}
    )

    hotkey_map = {
        "created_at": created_at,
        "wallet_name": WALLET_NAME,
        "coldkey_ss58": coldkey,
        "netuid": NETUID,
        "network": NETWORK,
        "match": "random",
        "random_seed": RANDOM_SEED,
        "match_count": MATCH_COUNT,
        "registered_hotkey_count": len(registered),
        "entries": [
            {
                "hotkey_name": e["hotkey_name"],
                "hotkey_address": e["hotkey_address"],
                "on_chain_uid": e["on_chain_uid"],
                "agent_name": e["agent_name"],
                "filename": e["filename"],
                "agent_path": e["agent_path"],
                "date": e["date"],
            }
            for e in entries
        ],
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
        "match_count": MATCH_COUNT,
        "registered_hotkey_count": len(registered),
        "matched_count": len(entries),
        "agent_count_total_in_dir": len(agents),
        "leftover_available_hotkeys": leftover_hotkeys,
        "leftover_unmatched_agents": leftover_agents,
        "entries": entries,
    }

    AGENT_DIR.mkdir(parents=True, exist_ok=True)
    (AGENT_DIR / "hotkey_map.json").write_text(
        json.dumps(hotkey_map, indent=2) + "\n", encoding="utf-8"
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
        """#!/usr/bin/env bash
set -euo pipefail
# Submit matched submittion17 agents in parallel.
# Usage: bash /root/turtle/111/67/submittion17/submit_all.sh [PARALLEL_JOBS]
ROOT="/root/turtle/harnyx"
JOBS_FILE="/root/turtle/111/67/submittion17/submit_jobs.txt"
PARALLEL_JOBS="${1:-9}"
WALLET="money"
cd "$ROOT"
echo "Submitting $(wc -l < "$JOBS_FILE") agents with PARALLEL_JOBS=$PARALLEL_JOBS ..."
running=0
fail=0
ok=0
while IFS=$'\\t' read -r HOTKEY AGENT; do
  [[ -z "${HOTKEY:-}" ]] && continue
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
        f"""# Submit submittion17 agents ({MATCH_COUNT}) to registered SN67 hotkeys
# History: {stamped}
# Map:     {AGENT_DIR / "hotkey_map.json"}
# Seed:    {RANDOM_SEED}

cd /root/turtle/harnyx
bash /root/turtle/111/67/submittion17/submit_all.sh {MATCH_COUNT}
""",
        encoding="utf-8",
    )

    print(f"Matched {len(entries)} pairs (seed={RANDOM_SEED})")
    print(f"Registered hotkeys on chain: {len(registered)}")
    print(f"Leftover hotkeys: {len(leftover_hotkeys)}, leftover agents: {len(leftover_agents)}")
    for e in entries:
        print(f"  {e['hotkey_name']} (uid={e['on_chain_uid']}) <- {e['filename']}")


if __name__ == "__main__":
    main()
