# BEAM Worker Guide

Run a worker on BEAM mainnet.

## Public Endpoints

| Service | Environment variable | URL |
| ------- | -------------------- | --- |
| Core server | `CORE_SERVER_URL` | `https://beamcore.b1m.ai` |
| Worker gateway | `WORKER_GATEWAY_URL` | Operator/orchestrator-owned worker gateway |

## Requirements

- Python 3.10-3.12
- A Bittensor wallet with a registered hotkey on subnet 105
- Stable upload and download bandwidth
- Enough disk space for transfer scratch data

## Install

```bash
git clone https://github.com/Beam-Network/beam.git
cd beam
python3 -m venv .venv
source .venv/bin/activate
pip install -e "."
```

## Register

```bash
btcli subnet register --netuid 105 --subtensor.network finney \
  --wallet.name your_coldkey \
  --wallet.hotkey your_hotkey
```

## Configure

Create or export the worker environment before starting the process:

```bash
CORE_SERVER_URL=https://beamcore.b1m.ai
WORKER_GATEWAY_URL=https://your-orchestrator-worker-gateway.example
SUBTENSOR_NETWORK=finney
NETUID=105
```

The worker uses BeamCore HTTP for registration and signed bootstrap calls. Transfer runtime uses `WORKER_GATEWAY_URL` over WebSocket.

## Run

```bash
cd neurons/worker
python worker.py --wallet.name your_coldkey --wallet.hotkey your_hotkey --subtensor.network finney
```

## Troubleshooting

- Verify the hotkey is registered on subnet 105.
- Verify `WORKER_GATEWAY_URL` points to the orchestrator-owned worker gateway.
- Verify `CORE_SERVER_URL=https://beamcore.b1m.ai`.
- If the worker starts but receives no tasks, keep it connected and confirm the gateway URL is reachable from the host.
