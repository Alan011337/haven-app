#!/usr/bin/env bash
# Shared helpers for release/security gate scripts.

gate_detect_current_branch() {
  local root_dir="$1"
  git -C "${root_dir}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown"
}

gate_is_protected_release_branch() {
  local branch="$1"
  [[ "${branch}" == "main" || "${branch}" == release/* ]]
}

gate_default_by_strict_mode() {
  local strict_mode="$1"
  local strict_default="$2"
  local relaxed_default="$3"
  if [[ "${strict_mode}" == "1" ]]; then
    echo "${strict_default}"
  else
    echo "${relaxed_default}"
  fi
}

gate_python_can_bootstrap() {
  local candidate="$1"
  local pythonpath="$2"
  local bootstrap_cmd="$3"
  PYTHONUTF8=1 PYTHONPATH="${pythonpath}" "${candidate}" -c "${bootstrap_cmd}" >/dev/null 2>&1
}
