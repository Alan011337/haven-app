#!/usr/bin/env bash
# Install backend deps using uv (avoids python -m pip when venv's pip module hangs).
# Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh
# Or: brew install uv
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_DIR}"

# uv install script puts binary in ~/.local/bin — ensure it's on PATH
if [[ -x "${HOME}/.local/bin/uv" ]]; then
  export PATH="${HOME}/.local/bin:${PATH}"
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install it first:" >&2
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  echo "  or: brew install uv" >&2
  echo "Then ensure ~/.local/bin is in PATH, or run: export PATH=\"\$HOME/.local/bin:\$PATH\"" >&2
  exit 1
fi

echo "[install-deps-uv] Using uv to install into venv..."
if [[ ! -d venv ]]; then
  echo "[install-deps-uv] Creating venv..."
  uv venv venv
fi
uv pip install -r requirements.txt --python venv/bin/python
echo "[install-deps-uv] Done."
