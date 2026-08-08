#!/usr/bin/env bash
set -euo pipefail
# Submit matched sub16-unsubmitted agents to registered SN67 hotkeys.
# Usage: bash /root/turtle/111/67/sub16-unsubmitted/submit_all.sh [PARALLEL_JOBS]
ROOT_HARNYX="/root/turtle/harnyx"
JOBS_FILE="/root/turtle/111/67/sub16-unsubmitted/submit_jobs.txt"
PARALLEL_JOBS="${1:-29}"
WALLET="money"
cd "$ROOT_HARNYX"
echo "Submitting $(wc -l < "$JOBS_FILE") agents with PARALLEL_JOBS=$PARALLEL_JOBS ..."
running=0
fail=0
ok=0
while IFS=$'\t' read -r HOTKEY AGENT; do
  [[ -z "${HOTKEY:-}" ]] && continue
  (
    echo "[START] $HOTKEY <- $(basename "$AGENT")"
    if uv run --package harnyx-miner harnyx-miner-submit \
        --wallet-name "$WALLET" \
        --hotkey-name "$HOTKEY" \
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
