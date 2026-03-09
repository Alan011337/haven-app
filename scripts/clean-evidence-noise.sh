#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

DRY_RUN="${EVIDENCE_NOISE_CLEAN_DRY_RUN:-0}"
PRUNE_TIMESTAMPED="${EVIDENCE_NOISE_PRUNE_TIMESTAMPED:-1}"
KEEP_UNTRACKED_TIMESTAMPED_COUNT="${EVIDENCE_NOISE_KEEP_UNTRACKED_TIMESTAMPED_COUNT:-2}"

if ! command -v git >/dev/null 2>&1; then
  echo "[clean-evidence-noise] fail: git command not found"
  exit 1
fi

declare -a SEARCH_ROOTS=(
  "${ROOT_DIR}/docs/security/evidence"
  "${ROOT_DIR}/docs/sre/evidence"
)

removed=0
skipped_tracked=0
checked=0
timestamp_removed=0

for root in "${SEARCH_ROOTS[@]}"; do
  if [[ ! -d "${root}" ]]; then
    continue
  fi
  while IFS= read -r -d '' file; do
    checked=$((checked + 1))
    rel_path="${file#${ROOT_DIR}/}"
    if git -C "${ROOT_DIR}" ls-files --error-unmatch "${rel_path}" >/dev/null 2>&1; then
      skipped_tracked=$((skipped_tracked + 1))
      continue
    fi
    if [[ "${DRY_RUN}" == "1" ]]; then
      echo "[clean-evidence-noise] dry-run remove: ${rel_path}"
      removed=$((removed + 1))
      continue
    fi
    rm -f "${file}"
    removed=$((removed + 1))
    echo "[clean-evidence-noise] removed: ${rel_path}"
  done < <(find "${root}" -type f -name "*-latest.json" -print0)
done

if [[ "${PRUNE_TIMESTAMPED}" == "1" ]]; then
  keep_count="${KEEP_UNTRACKED_TIMESTAMPED_COUNT}"
  if ! [[ "${keep_count}" =~ ^[0-9]+$ ]]; then
    keep_count=2
  fi
  for root in "${SEARCH_ROOTS[@]}"; do
    if [[ ! -d "${root}" ]]; then
      continue
    fi
    for ext in json md; do
      temp_list="$(mktemp)"
      find "${root}" -type f -name "*-20??????T??????Z.${ext}" | sort > "${temp_list}"
      file_total="$(wc -l < "${temp_list}" | tr -d ' ')"
      if [[ "${file_total}" -le "${keep_count}" ]]; then
        rm -f "${temp_list}"
        continue
      fi
      remove_total="$((file_total - keep_count))"
      idx=0
      while IFS= read -r file; do
        if [[ "${idx}" -ge "${remove_total}" ]]; then
          break
        fi
        rel_path="${file#${ROOT_DIR}/}"
        if git -C "${ROOT_DIR}" ls-files --error-unmatch "${rel_path}" >/dev/null 2>&1; then
          skipped_tracked=$((skipped_tracked + 1))
          idx=$((idx + 1))
          continue
        fi
        if [[ "${DRY_RUN}" == "1" ]]; then
          echo "[clean-evidence-noise] dry-run prune timestamped: ${rel_path}"
          timestamp_removed=$((timestamp_removed + 1))
          idx=$((idx + 1))
          continue
        fi
        rm -f "${file}"
        timestamp_removed=$((timestamp_removed + 1))
        echo "[clean-evidence-noise] pruned timestamped: ${rel_path}"
        idx=$((idx + 1))
      done < "${temp_list}"
      rm -f "${temp_list}"
    done
  done
fi

echo "[clean-evidence-noise] result"
echo "  checked: ${checked}"
echo "  removed_untracked_latest: ${removed}"
echo "  removed_untracked_timestamped: ${timestamp_removed}"
echo "  skipped_tracked_latest: ${skipped_tracked}"
