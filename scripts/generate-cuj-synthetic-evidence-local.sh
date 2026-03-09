#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
TMP_DIR="${CUJ_SYNTHETIC_TMP_DIR:-/tmp}"

BACKEND_PYTHON="${BACKEND_PYTHON:-${BACKEND_DIR}/.venv-gate/bin/python}"
if [[ ! -x "${BACKEND_PYTHON}" ]]; then
  BACKEND_PYTHON="python3"
fi

SUMMARY_PATH="${CUJ_SYNTHETIC_SUMMARY_PATH:-${TMP_DIR}/cuj-synthetics-summary-local.json}"
HEALTH_PAYLOAD_PATH="${CUJ_SYNTHETIC_HEALTH_PAYLOAD_PATH:-${TMP_DIR}/cuj-health-payload-local.json}"
SLO_PAYLOAD_PATH="${CUJ_SYNTHETIC_SLO_PAYLOAD_PATH:-${TMP_DIR}/cuj-slo-payload-local.json}"
MAX_AGE_HOURS="${CUJ_SYNTHETIC_EVIDENCE_MAX_AGE_HOURS:-36}"

cat > "${HEALTH_PAYLOAD_PATH}" <<'JSON'
{
  "status": "ok",
  "sli": {
    "http_runtime": {
      "sample_count": 12,
      "latency_ms": {
        "p95": 900
      }
    }
  }
}
JSON

cat > "${SLO_PAYLOAD_PATH}" <<'JSON'
{
  "checks": {
    "notification_outbox_depth": {
      "status": "ok",
      "depth": 0
    }
  },
  "sli": {
    "abuse_economics": {
      "evaluation": {"status": "ok"}
    },
    "notification_runtime": {
      "counters": {
        "attempt_total": 4,
        "success_total": 4,
        "failure_total": 0
      }
    },
    "dynamic_content_runtime": {
      "counters": {
        "attempt_total": 2,
        "success_total": 2,
        "fallback_total": 0
      }
    },
    "evaluation": {
      "ws": {"status": "ok"},
      "ws_burn_rate": {"status": "ok"},
      "ai_router_burn_rate": {"status": "ok"},
      "push": {"status": "ok"},
      "cuj": {"status": "ok"}
    }
  }
}
JSON

cd "${ROOT_DIR}"
python3 scripts/synthetics/run_cuj_synthetics.py \
  --health-payload-file "${HEALTH_PAYLOAD_PATH}" \
  --slo-payload-file "${SLO_PAYLOAD_PATH}" \
  --output-dir docs/sre/evidence \
  --summary-path "${SUMMARY_PATH}"

cd "${BACKEND_DIR}"
PYTHONUTF8=1 PYTHONPATH=. "${BACKEND_PYTHON}" scripts/check_cuj_synthetic_evidence_gate.py \
  --require-pass \
  --max-age-hours "${MAX_AGE_HOURS}"

echo "[cuj-evidence-local] health payload: ${HEALTH_PAYLOAD_PATH}"
echo "[cuj-evidence-local] slo payload: ${SLO_PAYLOAD_PATH}"
echo "[cuj-evidence-local] summary: ${SUMMARY_PATH}"
echo "[cuj-evidence-local] result: pass"
