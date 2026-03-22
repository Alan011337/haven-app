#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./local-dev-lib.sh
source "${SCRIPT_DIR}/local-dev-lib.sh"

prepare_local_runtime_env
NODE22_DIR="$(node22_path_maybe || true)"
if [[ -n "${NODE22_DIR}" ]]; then
  export PATH="${NODE22_DIR}:${PATH}"
fi

cd "${FRONTEND_DIR}"
print_local_runtime_summary
exec npm run dev -- --hostname "${HAVEN_LOCAL_DEV_FRONTEND_HOST}" --port "${HAVEN_LOCAL_DEV_FRONTEND_PORT}"
