#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GIT_DIR="${ROOT_DIR}/.git"
HOOKS_DIR="${GIT_DIR}/hooks"
PRE_COMMIT_PATH="${HOOKS_DIR}/pre-commit"

if [[ ! -d "${GIT_DIR}" ]]; then
  echo "[install-git-hooks] fail: .git directory not found at ${GIT_DIR}"
  exit 1
fi

mkdir -p "${HOOKS_DIR}"

cat > "${PRE_COMMIT_PATH}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "${ROOT_DIR}/backend"
PYTHONUTF8=1 PYTHONPATH=. "${ROOT_DIR}/backend/.venv-gate/bin/python" scripts/check_duplicate_suffix_files.py
EOF

chmod +x "${PRE_COMMIT_PATH}"
echo "[install-git-hooks] installed pre-commit hook at ${PRE_COMMIT_PATH}"
