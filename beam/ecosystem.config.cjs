/**
 * PM2 ecosystem for Beam SN105 orchestrator + workers.
 *
 * Usage:
 *   pm2 start ecosystem.config.cjs
 *   pm2 save
 *   pm2 logs beam-orchestrator
 *   pm2 logs beam-worker-1
 */
const path = require("path");

const BEAM_ROOT = __dirname;
const PYTHON = path.join(BEAM_ROOT, ".venv", "bin", "python");
const ORCH_DIR = path.join(BEAM_ROOT, "neurons", "orchestrator");
const WORKER_DIR = path.join(BEAM_ROOT, "neurons", "worker");
const LOG_DIR = "/tmp/beam_logs";
// One worker per hotkey/IP — extra processes share the same BeamCore worker_id and fight for one WS.
const WORKER_COUNT = 1;

// Shared mainnet settings (orchestrator also loads neurons/orchestrator/.env via dotenv in process if set).
const SHARED = {
  CORE_SERVER_URL: "https://beamcore.b1m.ai",
  ORCH_GATEWAY_URL: "https://orch-gateway.b1m.ai",
  SUBTENSOR_NETWORK: "finney",
  NETUID: "105",
  WALLET_NAME: "turtles",
  WALLET_HOTKEY: "hk-15-32",
  WALLET_PATH: "~/.bittensor/wallets",
  ORCHESTRATOR_WORKER_GATEWAY_URL: "http://194.5.152.9:8080",
  WORKER_GATEWAY_URL: "http://194.5.152.9:8080",
  EXTERNAL_IP: "194.5.152.9",
  ORCHESTRATOR_UID: "133",
  READY: "true",
  API_PORT: "8000",
  LOG_LEVEL: "INFO",
  REGION: "EU",
  LOG_DIR,
  // Per-worker limits (10 concurrent handles full ~7–8 chunk batches per transfer)
  WORKER_MAX_CONCURRENT_TASKS: "10",
  WORKER_MAX_QUEUED_WS_TASKS: "10",
  WORKER_MAX_IN_FLIGHT_BYTES: "1073741824",
  WORKER_FETCH_STREAM_CHUNK_SIZE: "1048576",
  WORKER_FETCH_TIMEOUT: "45",
  WORKER_SEND_TIMEOUT: "45",
  WORKER_HTTP_READ_TIMEOUT: "90",
  WORKER_HTTP_WRITE_TIMEOUT: "90",
  PYTHONUNBUFFERED: "1",
};

const HEALTH_SCRIPT = path.join(BEAM_ROOT, "scripts", "beam_health_check.sh");

function workerApp(index, registerPort) {
  const name = `beam-worker-${index}`;
  return {
    name,
    cwd: WORKER_DIR,
    script: PYTHON,
    args: [
      "worker.py",
      "--wallet.name",
      SHARED.WALLET_NAME,
      "--wallet.hotkey",
      SHARED.WALLET_HOTKEY,
      "--subtensor.network",
      SHARED.SUBTENSOR_NETWORK,
    ].join(" "),
    interpreter: "none",
    exec_mode: "fork",
    instances: 1,
    autorestart: true,
    max_restarts: 50,
    min_uptime: "30s",
    restart_delay: 15000 + index * 2000,
    exp_backoff_restart_delay: 2000,
    kill_timeout: 30000,
    env: {
      ...SHARED,
      WORKER_REGISTER_PORT: String(registerPort),
    },
    out_file: path.join(LOG_DIR, `pm2-worker-${index}.out.log`),
    error_file: path.join(LOG_DIR, `pm2-worker-${index}.err.log`),
    merge_logs: true,
    time: true,
  };
}

const workerApps = Array.from({ length: WORKER_COUNT }, (_, i) =>
  workerApp(i + 1, 9001 + i)
);

module.exports = {
  apps: [
    {
      name: "beam-orchestrator",
      cwd: ORCH_DIR,
      script: PYTHON,
      args: "main.py",
      interpreter: "none",
      exec_mode: "fork",
      instances: 1,
      autorestart: true,
      max_restarts: 50,
      min_uptime: "30s",
      restart_delay: 5000,
      exp_backoff_restart_delay: 1000,
      kill_timeout: 15000,
      env: {
        ...SHARED,
      },
      out_file: path.join(LOG_DIR, "pm2-orchestrator.out.log"),
      error_file: path.join(LOG_DIR, "pm2-orchestrator.err.log"),
      merge_logs: true,
      time: true,
    },
    ...workerApps,
    {
      name: "beam-health",
      script: HEALTH_SCRIPT,
      interpreter: "bash",
      exec_mode: "fork",
      instances: 1,
      autorestart: true,
      max_restarts: 100,
      min_uptime: "5s",
      restart_delay: 30000,
      env: {
        GATEWAY_URL: SHARED.ORCHESTRATOR_WORKER_GATEWAY_URL,
        CHECK_INTERVAL_SEC: "120",
        WORKER_STALE_CHECKS: "3",
        WORKER_COUNT: String(WORKER_COUNT),
        LOG_DIR,
      },
      out_file: path.join(LOG_DIR, "pm2-health.out.log"),
      error_file: path.join(LOG_DIR, "pm2-health.err.log"),
      merge_logs: true,
      time: true,
    },
  ],
};
