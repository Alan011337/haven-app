#!/usr/bin/env node

import fs from "node:fs";
import process from "node:process";

const REQUIRED_KEYS = [
  "schema_version",
  "result",
  "exit_code",
  "classification",
  "log_available",
  "next_action",
];
const ALLOWED_RESULTS = new Set(["pass", "fail", "unavailable"]);
const ALLOWED_CLASSIFICATIONS = new Set([
  "none",
  "pre_e2e_step_failure",
  "missing_browser",
  "browser_download_network",
  "app_unreachable",
  "e2e_process_timeout",
  "cuj_assertion_timeout",
  "test_or_runtime_failure",
]);

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const raw = argv[index];
    if (!raw.startsWith("--")) {
      continue;
    }
    const key = raw.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      parsed[key] = "true";
      continue;
    }
    parsed[key] = next;
    index += 1;
  }
  return parsed;
}

function fail(message) {
  console.error(`[frontend-e2e-summary-schema-gate] fail: ${message}`);
  process.exit(1);
}

function validatePayload(payload, requiredSchemaVersion) {
  for (const key of REQUIRED_KEYS) {
    if (!Object.prototype.hasOwnProperty.call(payload, key)) {
      fail(`missing required key: ${key}`);
    }
  }

  if (payload.schema_version !== requiredSchemaVersion) {
    fail(
      `schema_version mismatch: expected=${requiredSchemaVersion} actual=${String(payload.schema_version)}`,
    );
  }
  if (!ALLOWED_RESULTS.has(payload.result)) {
    fail(`invalid result value: ${String(payload.result)}`);
  }
  if (!ALLOWED_CLASSIFICATIONS.has(payload.classification)) {
    fail(`invalid classification value: ${String(payload.classification)}`);
  }
  if (typeof payload.log_available !== "boolean") {
    fail(`log_available must be boolean, got ${typeof payload.log_available}`);
  }
  if (typeof payload.next_action !== "string" || payload.next_action.length === 0) {
    fail("next_action must be a non-empty string");
  }
  if (!(payload.exit_code === null || Number.isInteger(payload.exit_code))) {
    fail("exit_code must be integer or null");
  }

  if (payload.result === "pass" && payload.classification !== "none") {
    fail("classification must be `none` when result is `pass`");
  }
  if (payload.result === "unavailable" && payload.exit_code !== null) {
    fail("exit_code must be null when result is `unavailable`");
  }
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const summaryPath = args["summary-path"];
  const requiredSchemaVersion = args["required-schema-version"] || "v1";

  if (!summaryPath) {
    fail("--summary-path is required");
  }
  if (!fs.existsSync(summaryPath)) {
    fail(`summary file missing: ${summaryPath}`);
  }

  let payload;
  try {
    payload = JSON.parse(fs.readFileSync(summaryPath, "utf8"));
  } catch (error) {
    fail(`invalid JSON summary: ${String(error)}`);
  }

  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    fail("summary payload must be a JSON object");
  }

  validatePayload(payload, requiredSchemaVersion);
  console.log(
    `[frontend-e2e-summary-schema-gate] pass (schema_version=${requiredSchemaVersion})`,
  );
}

main();
