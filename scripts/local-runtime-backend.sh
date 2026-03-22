#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./local-dev-lib.sh
source "${SCRIPT_DIR}/local-dev-lib.sh"

prepare_local_runtime_env
bash "${SCRIPT_DIR}/local-dev-db.sh" start

cd "${BACKEND_DIR}"
print_local_runtime_summary
exec ./scripts/run-dev.sh
