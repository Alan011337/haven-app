#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8000}"
FRONTEND_BASE_URL="${FRONTEND_BASE_URL:-}"
FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-http://localhost:3000}"
ALPHA_EXPECT_ALLOWLIST="${ALPHA_EXPECT_ALLOWLIST:-1}"

fail() {
  echo "[alpha-gate-curl] FAIL: $*" >&2
  exit 1
}

tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

echo "[alpha-gate-curl] backend=${BACKEND_BASE_URL}"

# 1) health live
curl -fsS --max-time 10 "${BACKEND_BASE_URL}/health/live" >/dev/null || fail "backend /health/live unreachable"
echo "[alpha-gate-curl] health/live ok"

# 2) frontend home (optional)
if [[ -n "${FRONTEND_BASE_URL}" ]]; then
  curl -fsSI --max-time 10 "${FRONTEND_BASE_URL}/" >/dev/null || fail "frontend root unreachable"
  echo "[alpha-gate-curl] frontend root ok"
fi

# 3) CORS preflight
preflight_headers="${tmp_dir}/preflight.headers"
preflight_code="$({
  curl -sS -o /dev/null -D "${preflight_headers}" -w '%{http_code}' \
    -X OPTIONS "${BACKEND_BASE_URL}/api/users/me" \
    -H "Origin: ${FRONTEND_ORIGIN}" \
    -H 'Access-Control-Request-Method: GET'
} || true)"
if [[ "${preflight_code}" != "200" && "${preflight_code}" != "204" ]]; then
  fail "CORS preflight unexpected status=${preflight_code}"
fi
if ! rg -qi '^access-control-allow-origin:' "${preflight_headers}"; then
  fail "missing Access-Control-Allow-Origin"
fi
if ! rg -qi '^access-control-allow-credentials:\s*true' "${preflight_headers}"; then
  fail "missing Access-Control-Allow-Credentials=true"
fi
echo "[alpha-gate-curl] CORS preflight ok"

# 4) allow-list deny path (alpha)
if [[ "${ALPHA_EXPECT_ALLOWLIST}" == "1" ]]; then
  deny_body="${tmp_dir}/deny.json"
  deny_code="$({
    curl -sS -o "${deny_body}" -w '%{http_code}' \
      -X POST "${BACKEND_BASE_URL}/api/auth/token" \
      -H 'Content-Type: application/x-www-form-urlencoded' \
      --data-urlencode "username=outsider+$(date +%s)@example.com" \
      --data-urlencode 'password=invalid-password'
  } || true)"
  if [[ "${deny_code}" != "403" ]]; then
    fail "allow-list deny expected 403, got ${deny_code}"
  fi
  if ! rg -q '邀請制內測' "${deny_body}"; then
    fail "allow-list deny body missing expected generic message"
  fi
  echo "[alpha-gate-curl] allow-list deny path ok"
fi

# 5) auth + partner-status (optional; requires test creds)
if [[ -n "${TEST_ALLOW_EMAIL:-}" && -n "${TEST_ALLOW_PASSWORD:-}" ]]; then
  login_body="${tmp_dir}/login.json"
  login_code="$({
    curl -sS -o "${login_body}" -w '%{http_code}' \
      -X POST "${BACKEND_BASE_URL}/api/auth/token" \
      -H 'Content-Type: application/x-www-form-urlencoded' \
      --data-urlencode "username=${TEST_ALLOW_EMAIL}" \
      --data-urlencode "password=${TEST_ALLOW_PASSWORD}"
  } || true)"
  if [[ "${login_code}" != "200" ]]; then
    fail "allow-list login expected 200, got ${login_code}"
  fi

  token="$(python3 - <<'PY' "${login_body}"
import json, sys
p = sys.argv[1]
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)
print(data.get('access_token') or '')
PY
)"
  if [[ -z "${token}" ]]; then
    fail "access_token missing in login response"
  fi

  partner_code="$({
    curl -sS -o /dev/null -w '%{http_code}' \
      -H "Authorization: Bearer ${token}" \
      "${BACKEND_BASE_URL}/api/users/partner-status"
  } || true)"
  if [[ "${partner_code}" != "200" ]]; then
    fail "partner-status expected 200, got ${partner_code}"
  fi
  echo "[alpha-gate-curl] auth + partner-status ok"
else
  echo "[alpha-gate-curl] skip auth/partner-status (set TEST_ALLOW_EMAIL & TEST_ALLOW_PASSWORD)"
fi

echo "[alpha-gate-curl] pass"
