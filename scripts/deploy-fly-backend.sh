#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"

FLY_BIN_DEFAULT="/tmp/flybin/flyctl"
if [[ -n "${FLY_BIN:-}" ]]; then
  :
elif [[ -x "${FLY_BIN_DEFAULT}" ]]; then
  FLY_BIN="${FLY_BIN_DEFAULT}"
elif command -v flyctl >/dev/null 2>&1; then
  FLY_BIN="$(command -v flyctl)"
else
  echo "[fly-deploy] fail: flyctl not found. Install first."
  exit 1
fi

if [[ -z "${FLY_APP_NAME:-}" ]]; then
  echo "[fly-deploy] fail: missing FLY_APP_NAME"
  exit 1
fi

FLY_REGION="${FLY_REGION:-nrt}"
FLY_CONFIG_FILE="${FLY_CONFIG_FILE:-${BACKEND_DIR}/fly.toml}"
FLY_DEPLOY_PREFLIGHT_ONLY="${FLY_DEPLOY_PREFLIGHT_ONLY:-0}"
FLYCTL_HOME="${FLYCTL_HOME:-}"

if [[ -z "${FLYCTL_HOME}" && "${FLY_BIN}" == "${FLY_BIN_DEFAULT}" ]]; then
  FLYCTL_HOME="/tmp"
fi

if [[ ! -f "${FLY_CONFIG_FILE}" ]]; then
  echo "[fly-deploy] fail: missing fly config ${FLY_CONFIG_FILE}"
  exit 1
fi

required_env_keys=(
  DATABASE_URL
  OPENAI_API_KEY
  SECRET_KEY
  CORS_ORIGINS
)
for key in "${required_env_keys[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    echo "[fly-deploy] fail: missing required env var ${key}"
    exit 1
  fi
done

if [[ -z "${FLY_API_TOKEN:-}" ]]; then
  echo "[fly-deploy] fail: missing FLY_API_TOKEN"
  echo "[fly-deploy] hint: export FLY_API_TOKEN=<token>"
  exit 1
fi

echo "[fly-deploy] using flyctl: ${FLY_BIN}"
if [[ -n "${FLYCTL_HOME}" ]]; then
  mkdir -p "${FLYCTL_HOME}"
  export HOME="${FLYCTL_HOME}"
  echo "[fly-deploy] flyctl home: ${HOME}"
fi
"${FLY_BIN}" auth whoami >/dev/null

if ! "${FLY_BIN}" apps list | awk '{print $1}' | grep -qx "${FLY_APP_NAME}"; then
  echo "[fly-deploy] creating app ${FLY_APP_NAME} in region ${FLY_REGION}"
  "${FLY_BIN}" apps create "${FLY_APP_NAME}" --org personal || true
fi

fly_secret_exists() {
  local secret_name="$1"
  "${FLY_BIN}" secrets list --app "${FLY_APP_NAME}" | awk 'NR > 1 {print $1}' | grep -qx "${secret_name}"
}

config_pins_redis_backend() {
  local backend_key="$1"
  grep -Eq "^[[:space:]]*${backend_key}[[:space:]]*=[[:space:]]*\"redis\"" "${FLY_CONFIG_FILE}"
}

require_redis_secret() {
  local backend_key="$1"
  local label="$2"
  shift 2
  local secret_keys=("$@")

  if ! config_pins_redis_backend "${backend_key}"; then
    return 0
  fi

  local secret_key
  for secret_key in "${secret_keys[@]}"; do
    if [[ -n "${!secret_key:-}" ]]; then
      echo "[fly-deploy] ${label} secret source: deploy env (${secret_key})"
      return 0
    fi
    if fly_secret_exists "${secret_key}"; then
      echo "[fly-deploy] ${label} secret source: existing fly secret (${secret_key})"
      return 0
    fi
  done

  if [[ "${#secret_keys[@]}" -eq 1 ]]; then
    echo "[fly-deploy] fail: ${FLY_CONFIG_FILE} pins ${backend_key}=redis but ${secret_keys[0]} is missing"
    echo "[fly-deploy] hint: export ${secret_keys[0]}=<redis-url> or set that Fly secret first"
    exit 1
  fi

  echo "[fly-deploy] fail: ${FLY_CONFIG_FILE} pins ${backend_key}=redis but none of ${secret_keys[*]} are available"
  echo "[fly-deploy] hint: export one of ${secret_keys[*]}=<redis-url> or set one of those Fly secrets first"
  exit 1
}

require_redis_secret "AI_ROUTER_SHARED_STATE_BACKEND" "ai router redis" \
  "AI_ROUTER_REDIS_URL" \
  "REDIS_URL" \
  "ABUSE_GUARD_REDIS_URL"
require_redis_secret "ABUSE_GUARD_STORE_BACKEND" "abuse guard redis" "ABUSE_GUARD_REDIS_URL"

secret_pairs=(
  "DATABASE_URL=${DATABASE_URL}"
  "OPENAI_API_KEY=${OPENAI_API_KEY}"
  "SECRET_KEY=${SECRET_KEY}"
  "CORS_ORIGINS=${CORS_ORIGINS}"
)

optional_secret_keys=(
  AI_ROUTER_REDIS_URL
  ABUSE_GUARD_REDIS_URL
  RESEND_API_KEY
  RESEND_FROM_EMAIL
  GEMINI_API_KEY
  BILLING_STRIPE_SECRET_KEY
  BILLING_STRIPE_WEBHOOK_SECRET
  BILLING_STRIPE_PRICE_ID
  BILLING_STRIPE_SUCCESS_URL
  BILLING_STRIPE_CANCEL_URL
  BILLING_STRIPE_PORTAL_RETURN_URL
)
for key in "${optional_secret_keys[@]}"; do
  if [[ -n "${!key:-}" ]]; then
    secret_pairs+=("${key}=${!key}")
  fi
done

if [[ "${FLY_DEPLOY_PREFLIGHT_ONLY}" == "1" ]]; then
  echo "[fly-deploy] preflight-only: pass"
  exit 0
fi

echo "[fly-deploy] setting secrets"
"${FLY_BIN}" secrets set --app "${FLY_APP_NAME}" "${secret_pairs[@]}"

echo "[fly-deploy] deploying app"
(
  cd "${BACKEND_DIR}"
  "${FLY_BIN}" deploy \
    --app "${FLY_APP_NAME}" \
    --config "${FLY_CONFIG_FILE}" \
    --dockerfile "${BACKEND_DIR}/Dockerfile.fly" \
    --remote-only
)

echo "[fly-deploy] ensuring process counts"
"${FLY_BIN}" scale count app=1 worker=1 --app "${FLY_APP_NAME}"

echo "[fly-deploy] verifying health checks"
"${FLY_BIN}" checks list --app "${FLY_APP_NAME}"

echo "[fly-deploy] done"
