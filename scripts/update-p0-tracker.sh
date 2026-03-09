#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

TRACKER_PATH="${ROOT_DIR}/docs/p0-machine-tracker.yaml"
ROADMAP_TRACKER_PATH="${ROOT_DIR}/docs/roadmap-machine-tracker.yaml"

RUN_GATES=1
SECURITY_COUNT=""
FULL_COUNT=""
FRONTEND_ENV="ok"
FRONTEND_TYPECHECK="ok"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/update-p0-tracker.sh
  ./scripts/update-p0-tracker.sh --no-run --security-count 133 --full-count 224

Options:
  --no-run                 Skip running release gate. Requires count inputs.
  --security-count <int>   Backend security gate passed count.
  --full-count <int>       Backend full test passed count.
  --frontend-env <value>   Frontend env check status (default: ok).
  --frontend-typecheck <value>
                           Frontend typecheck status (default: ok).
  --tracker <path>         Override P0 tracker file path.
  --roadmap <path>         Override roadmap tracker file path.
  -h, --help               Show help.
EOF
}

is_integer() {
  [[ "${1:-}" =~ ^[0-9]+$ ]]
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-run)
      RUN_GATES=0
      shift
      ;;
    --security-count)
      SECURITY_COUNT="${2:-}"
      shift 2
      ;;
    --full-count)
      FULL_COUNT="${2:-}"
      shift 2
      ;;
    --frontend-env)
      FRONTEND_ENV="${2:-ok}"
      shift 2
      ;;
    --frontend-typecheck)
      FRONTEND_TYPECHECK="${2:-ok}"
      shift 2
      ;;
    --tracker)
      TRACKER_PATH="${2:-}"
      shift 2
      ;;
    --roadmap)
      ROADMAP_TRACKER_PATH="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "${TRACKER_PATH}" ]]; then
  echo "P0 tracker not found: ${TRACKER_PATH}" >&2
  exit 1
fi

if [[ "${RUN_GATES}" -eq 1 ]]; then
  tmp_log="$(mktemp)"
  trap 'rm -f "${tmp_log}"' EXIT

  if ! "${ROOT_DIR}/scripts/release-gate.sh" | tee "${tmp_log}"; then
    echo "release gate failed; tracker not updated" >&2
    exit 1
  fi

  mapfile -t pass_counts < <(awk '/ passed in / {print $1}' "${tmp_log}")
  SECURITY_COUNT="${pass_counts[0]:-}"
  FULL_COUNT="${pass_counts[1]:-}"

  if grep -q "\[frontend env check\]" "${tmp_log}" && grep -q "result: ok" "${tmp_log}"; then
    FRONTEND_ENV="ok"
  else
    FRONTEND_ENV="unknown"
  fi

  if grep -q "\[typecheck\] ok" "${tmp_log}"; then
    FRONTEND_TYPECHECK="ok"
  else
    FRONTEND_TYPECHECK="unknown"
  fi
fi

if ! is_integer "${SECURITY_COUNT}" || ! is_integer "${FULL_COUNT}"; then
  echo "Invalid counts. Provide integer values for --security-count and --full-count." >&2
  exit 1
fi

timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

ruby - "${TRACKER_PATH}" "${ROADMAP_TRACKER_PATH}" "${timestamp}" "${SECURITY_COUNT}" "${FULL_COUNT}" "${FRONTEND_ENV}" "${FRONTEND_TYPECHECK}" <<'RUBY'
require "yaml"

p0_path, roadmap_path, timestamp, security_count, full_count, frontend_env, frontend_typecheck = ARGV

def dump_yaml(path, payload)
  serialized = YAML.dump(payload).sub(/\A---\s*\n/, "")
  File.write(path, serialized)
end

p0_data = YAML.load_file(p0_path)
p0_data["tracker"] ||= {}
p0_data["tracker"]["generated_at"] = timestamp

p0_items = p0_data["items"] || []
p0_items.each do |item|
  next unless item.is_a?(Hash)
  id = item["id"].to_s
  if id.start_with?("P0-") || id.start_with?("META-") || id == "LAUNCH-01"
    item["last_verified_at"] = timestamp unless item["status"] == "todo"
  end

  next unless id == "P0-A"
  item["gate_snapshot"] = {
    "backend_security_passed" => security_count.to_i,
    "backend_full_passed" => full_count.to_i,
    "frontend_env" => frontend_env,
    "frontend_typecheck" => frontend_typecheck,
  }
end

dump_yaml(p0_path, p0_data)

if File.exist?(roadmap_path)
  roadmap_data = YAML.load_file(roadmap_path)
  roadmap_data["tracker"] ||= {}
  roadmap_data["tracker"]["generated_at"] = timestamp

  p0_by_id = {}
  p0_items.each do |item|
    next unless item.is_a?(Hash) && item["id"]
    p0_by_id[item["id"]] = item
  end

  roadmap_items = roadmap_data["items"] || []
  roadmap_items.each do |item|
    next unless item.is_a?(Hash) && item["id"]
    p0_item = p0_by_id[item["id"]]
    next unless p0_item

    item["status"] = p0_item["status"] if p0_item.key?("status")
    item["last_verified_at"] = p0_item["last_verified_at"] if p0_item.key?("last_verified_at")
    item["evidence_paths"] = p0_item["evidence_paths"] if p0_item.key?("evidence_paths")
    item["gate_snapshot"] = p0_item["gate_snapshot"] if p0_item.key?("gate_snapshot")
    item["next_action"] = p0_item["next_action"] if p0_item.key?("next_action")
  end

  dump_yaml(roadmap_path, roadmap_data)
end
RUBY

echo "tracker updated:"
echo "  timestamp: ${timestamp}"
echo "  backend_security_passed: ${SECURITY_COUNT}"
echo "  backend_full_passed: ${FULL_COUNT}"
echo "  frontend_env: ${FRONTEND_ENV}"
echo "  frontend_typecheck: ${FRONTEND_TYPECHECK}"
