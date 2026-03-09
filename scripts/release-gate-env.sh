#!/usr/bin/env bash

release_gate_resolve_strict_mode() {
  local ci_value="$1"
  local protected_branch="$2"
  if [[ "${ci_value}" == "true" || "${ci_value}" == "1" || "${protected_branch}" == "1" ]]; then
    echo "1"
    return
  fi
  echo "0"
}

release_gate_normalize_env_mode() {
  local raw_value="${1:-dev}"
  local lowered
  lowered="$(echo "${raw_value}" | tr '[:upper:]' '[:lower:]')"
  case "${lowered}" in
    local|dev|development|test)
      echo "dev"
      ;;
    alpha|staging)
      echo "alpha"
      ;;
    prod|production)
      echo "prod"
      ;;
    *)
      echo "dev"
      ;;
  esac
}
