#!/usr/bin/env bash
# Start a Beam worker against this host's orchestrator gateway.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# Prefer beam venv; fall back to turtle venv if needed
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
elif [[ -x /root/turtle/.venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source /root/turtle/.venv/bin/activate
fi

export CORE_SERVER_URL="${CORE_SERVER_URL:-https://beamcore.b1m.ai}"
# Must match orchestrator ORCHESTRATOR_WORKER_GATEWAY_URL
export WORKER_GATEWAY_URL="${WORKER_GATEWAY_URL:-http://194.5.152.9:8080}"
export WORKER_MAX_CONCURRENT_TASKS="${WORKER_MAX_CONCURRENT_TASKS:-10}"
export SUBTENSOR_NETWORK="${SUBTENSOR_NETWORK:-finney}"
export NETUID="${NETUID:-105}"

WALLET_NAME="${WALLET_NAME:-turtles}"
WALLET_HOTKEY="${WALLET_HOTKEY:-hk-15-32}"

cd "$(dirname "$0")"
exec python worker.py \
  --wallet.name "$WALLET_NAME" \
  --wallet.hotkey "$WALLET_HOTKEY" \
  --subtensor.network "$SUBTENSOR_NETWORK"
