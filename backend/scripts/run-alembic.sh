#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_PYTHONPATH="${BACKEND_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

cd "${BACKEND_DIR}"

ALEMBIC_MODE="${ALEMBIC_MODE:-legacy-upgrade}"
if [[ "${1:-}" == "--mode" ]]; then
  if [[ -z "${2:-}" ]]; then
    echo "[run-alembic] fail: --mode requires a value."
    echo "[run-alembic] supported modes: legacy-upgrade, fresh-bootstrap, verify-only"
    exit 1
  fi
  ALEMBIC_MODE="${2}"
  shift 2
elif [[ "${1:-}" == --mode=* ]]; then
  ALEMBIC_MODE="${1#--mode=}"
  shift
fi

case "${ALEMBIC_MODE}" in
  legacy-upgrade|fresh-bootstrap|verify-only)
    ;;
  *)
    echo "[run-alembic] fail: unsupported mode '${ALEMBIC_MODE}'."
    echo "[run-alembic] supported modes: legacy-upgrade, fresh-bootstrap, verify-only"
    exit 1
    ;;
esac

# Load .env if present (so DATABASE_URL etc. are set for alembic)
if [[ -f .env ]]; then
  _ORIG_DATABASE_URL="${DATABASE_URL-}"
  _ORIG_BACKEND_PYTHON_BIN="${BACKEND_PYTHON_BIN-}"
  _HAS_DATABASE_URL="${DATABASE_URL+1}"
  _HAS_BACKEND_PYTHON_BIN="${BACKEND_PYTHON_BIN+1}"
  set -a
  # shellcheck source=/dev/null
  source .env 2>/dev/null || true
  set +a
  if [[ -n "${_HAS_DATABASE_URL:-}" ]]; then
    export DATABASE_URL="${_ORIG_DATABASE_URL}"
  fi
  if [[ -n "${_HAS_BACKEND_PYTHON_BIN:-}" ]]; then
    export BACKEND_PYTHON_BIN="${_ORIG_BACKEND_PYTHON_BIN}"
  fi
fi

can_import_alembic() {
  local candidate="$1"
  PYTHONUTF8=1 PYTHONPATH="${BACKEND_PYTHONPATH}" "${candidate}" -c "import alembic" >/dev/null 2>&1
}

resolve_target_database_url() {
  if [[ -n "${DATABASE_URL:-}" ]]; then
    printf '%s\n' "${DATABASE_URL}"
    return 0
  fi

  awk -F '=' '
    /^sqlalchemy\.url[[:space:]]*=/ {
      value=$0
      sub(/^[^=]*=/, "", value)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      print value
      exit
    }
  ' alembic.ini
}

classify_sqlite_database_state() {
  local target_url
  target_url="$(resolve_target_database_url)"

  if ! RUN_ALEMBIC_TARGET_URL="${target_url}" RUN_ALEMBIC_BACKEND_DIR="${BACKEND_DIR}" "${PYTHON_BIN}" - <<'PY'
import os
import sqlite3
import sys
from pathlib import Path

url = os.environ.get("RUN_ALEMBIC_TARGET_URL", "").strip()
backend_dir = Path(os.environ.get("RUN_ALEMBIC_BACKEND_DIR", ".")).resolve()

if not url.startswith("sqlite:///"):
    print("non_sqlite")
    raise SystemExit(0)

raw_path = url[len("sqlite:///") :]
if raw_path in {"", ":memory:"}:
    print("missing_or_empty")
    raise SystemExit(0)

db_path = Path(raw_path)
if not db_path.is_absolute():
    db_path = (backend_dir / db_path).resolve()

if not db_path.exists():
    print("missing_or_empty")
    raise SystemExit(0)

conn = sqlite3.connect(str(db_path))
try:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
finally:
    conn.close()

if not rows:
    print("missing_or_empty")
else:
    print("non_empty")
PY
  then
    return 1
  fi
}

guard_sqlite_bootstrap_for_upgrade_head() {
  local command="${1:-}"
  local target="${2:-}"

  if [[ "${command}" != "upgrade" || "${target}" != "head" ]]; then
    return 0
  fi

  if [[ "${ALLOW_EMPTY_DB_MIGRATION:-0}" == "1" ]]; then
    return 0
  fi

  local target_url
  target_url="$(resolve_target_database_url)"

  if [[ "${target_url}" != sqlite:///* ]]; then
    return 0
  fi

  if ! RUN_ALEMBIC_TARGET_URL="${target_url}" RUN_ALEMBIC_BACKEND_DIR="${BACKEND_DIR}" "${PYTHON_BIN}" - <<'PY'
import os
import sqlite3
import sys
from pathlib import Path

url = os.environ.get("RUN_ALEMBIC_TARGET_URL", "").strip()
backend_dir = Path(os.environ.get("RUN_ALEMBIC_BACKEND_DIR", ".")).resolve()

if not url.startswith("sqlite:///"):
    sys.exit(0)

raw_path = url[len("sqlite:///") :]
if raw_path in {"", ":memory:"}:
    sys.exit(0)

db_path = Path(raw_path)
if not db_path.is_absolute():
    db_path = (backend_dir / db_path).resolve()

if not db_path.exists():
    print(f"[run-alembic] bootstrap check failed: sqlite db file not found: {db_path}")
    sys.exit(2)

conn = sqlite3.connect(str(db_path))
try:
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
finally:
    conn.close()

if "alembic_version" in tables:
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT version_num FROM alembic_version "
            "WHERE version_num IS NOT NULL AND TRIM(version_num) != ''"
        ).fetchall()
    finally:
        conn.close()

    if len(rows) != 1:
        print(
            "[run-alembic] bootstrap check failed: sqlite db has invalid alembic_version rows; "
            "expected exactly 1 non-empty version_num"
        )
        sys.exit(4)

    sys.exit(0)

required_legacy_tables = {"users", "journal"}
missing = sorted(required_legacy_tables - tables)
if missing:
    print(
        "[run-alembic] bootstrap check failed: sqlite db has no alembic_version and missing legacy tables: "
        + ", ".join(missing)
    )
    sys.exit(3)
PY
  then
    echo "[run-alembic] hint: this migration chain assumes a legacy pre-alembic schema baseline."
    echo "[run-alembic] hint: set DATABASE_URL to a provisioned DB, or bootstrap a brand-new local sqlite DB first."
    echo "[run-alembic] hint: run 'DATABASE_URL=sqlite:///./test.db ${PYTHON_BIN} scripts/bootstrap-sqlite-schema.py'"
    echo "[run-alembic] hint: ALLOW_EMPTY_DB_MIGRATION=1 only bypasses this guard; it does not fix incompatible legacy migration assumptions."
    return 1
  fi

  return 0
}

bootstrap_fresh_sqlite_for_upgrade_head() {
  local command="${1:-}"
  local target="${2:-}"

  if [[ "${command}" != "upgrade" || "${target}" != "head" ]]; then
    echo "[run-alembic] fail: fresh-bootstrap mode currently supports only 'upgrade head'."
    echo "[run-alembic] hint: use --mode legacy-upgrade for other alembic commands."
    return 1
  fi

  local db_state
  db_state="$(classify_sqlite_database_state)"
  case "${db_state}" in
    non_sqlite)
      echo "[run-alembic] fail: fresh-bootstrap mode only supports sqlite DATABASE_URL."
      echo "[run-alembic] hint: use --mode legacy-upgrade for postgres/managed DB upgrades."
      return 1
      ;;
    missing_or_empty)
      echo "[run-alembic] fresh-bootstrap: initializing sqlite schema baseline."
      "${PYTHON_BIN}" scripts/bootstrap-sqlite-schema.py
      ;;
    non_empty)
      echo "[run-alembic] fail: target sqlite database is not empty."
      echo "[run-alembic] hint: use --mode legacy-upgrade for existing databases."
      return 1
      ;;
    *)
      echo "[run-alembic] fail: unable to classify sqlite database state."
      return 1
      ;;
  esac
}

# Prefer venv312 if present (same as run-dev-python312.sh)
if [[ -z "${BACKEND_PYTHON_BIN:-}" && -x "${BACKEND_DIR}/venv312/bin/python" ]]; then
  BACKEND_PYTHON_BIN="${BACKEND_DIR}/venv312/bin/python"
fi
if [[ -n "${BACKEND_PYTHON_BIN:-}" ]]; then
  if [[ "${BACKEND_PYTHON_BIN}" == */* ]]; then
    if [[ ! -x "${BACKEND_PYTHON_BIN}" ]]; then
      echo "[run-alembic] fail: BACKEND_PYTHON_BIN is not executable: ${BACKEND_PYTHON_BIN}"
      exit 1
    fi
  elif ! command -v "${BACKEND_PYTHON_BIN}" >/dev/null 2>&1; then
    echo "[run-alembic] fail: BACKEND_PYTHON_BIN command not found: ${BACKEND_PYTHON_BIN}"
    exit 1
  fi

  if ! can_import_alembic "${BACKEND_PYTHON_BIN}"; then
    echo "[run-alembic] fail: BACKEND_PYTHON_BIN cannot import alembic: ${BACKEND_PYTHON_BIN}"
    exit 1
  fi
  PYTHON_BIN="${BACKEND_PYTHON_BIN}"
else
  for candidate in ".venv-gate/bin/python" "venv/bin/python" "python3" "python"; do
    if [[ "${candidate}" == */* ]] && [[ ! -x "${candidate}" ]]; then
      continue
    fi
    if [[ "${candidate}" != */* ]] && ! command -v "${candidate}" >/dev/null 2>&1; then
      continue
    fi
    if can_import_alembic "${candidate}"; then
      PYTHON_BIN="${candidate}"
      break
    fi
  done
fi

if [[ -z "${PYTHON_BIN:-}" ]]; then
  echo "[run-alembic] fail: no usable python interpreter found for alembic."
  echo "[run-alembic] hint: set BACKEND_PYTHON_BIN to an interpreter with alembic installed."
  exit 1
fi

echo "[run-alembic] backend python: ${PYTHON_BIN}"
echo "[run-alembic] bootstrap: PYTHONUTF8=1, PYTHONPATH includes ${BACKEND_DIR}"
echo "[run-alembic] mode: ${ALEMBIC_MODE}"

export PYTHONUTF8=1
export PYTHONPATH="${BACKEND_PYTHONPATH}"

if [[ "${ALEMBIC_MODE}" == "verify-only" ]]; then
  guard_sqlite_bootstrap_for_upgrade_head "upgrade" "head"
  echo "[run-alembic] verify-only: preflight checks passed."
  exit 0
fi

if [[ "${ALEMBIC_MODE}" == "fresh-bootstrap" ]] && [[ $# -eq 0 ]]; then
  set -- upgrade head
fi

if [[ "${ALEMBIC_MODE}" == "fresh-bootstrap" ]]; then
  bootstrap_fresh_sqlite_for_upgrade_head "${1:-}" "${2:-}"
fi

if [[ "${ALEMBIC_MODE}" == "legacy-upgrade" ]]; then
  guard_sqlite_bootstrap_for_upgrade_head "${1:-}" "${2:-}"
fi

exec "${PYTHON_BIN}" -m alembic "$@"
