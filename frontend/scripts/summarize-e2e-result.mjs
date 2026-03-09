#!/usr/bin/env node

import fs from "node:fs";
import process from "node:process";

const E2E_SUMMARY_SCHEMA_VERSION = "v1";

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

function classifyFailure({ result, log }) {
  if (result === "unavailable") {
    return {
      classification: "pre_e2e_step_failure",
      nextAction: "Check preflight/install/build/server startup steps.",
    };
  }
  if (result !== "fail") {
    return {
      classification: "none",
      nextAction: "none",
    };
  }
  if (log.includes("[playwright-preflight] chromium executable not found")) {
    return {
      classification: "missing_browser",
      nextAction: "Validate playwright install path and browser cache.",
    };
  }
  if (log.includes("getaddrinfo ENOTFOUND cdn.playwright.dev")) {
    return {
      classification: "browser_download_network",
      nextAction: "Check DNS/network egress to cdn.playwright.dev or pre-seed browser cache.",
    };
  }
  if (log.includes("ERR_CONNECTION_REFUSED") || log.includes("ECONNREFUSED")) {
    return {
      classification: "app_unreachable",
      nextAction: "Inspect app server startup logs and E2E base URL.",
    };
  }
  if (log.includes("[e2e-timeout]")) {
    return {
      classification: "e2e_process_timeout",
      nextAction: "Reduce e2e scope or increase E2E_TIMEOUT_SECONDS after reviewing stuck process logs.",
    };
  }
  if (log.includes("Timed out") && log.includes("toHaveURL")) {
    return {
      classification: "cuj_assertion_timeout",
      nextAction: "Inspect smoke assertions and mocked API routes.",
    };
  }
  return {
    classification: "test_or_runtime_failure",
    nextAction: "Inspect e2e log for the first failing assertion.",
  };
}

function renderMarkdownSummary({ payload, title }) {
  const lines = [
    `### ${title}`,
    `- result: \`${payload.result}\``,
    `- exit_code: \`${payload.exit_code ?? "n/a"}\``,
    `- classification: \`${payload.classification}\``,
    `- log_available: \`${payload.log_available ? "yes" : "no"}\``,
    `- next_action: ${payload.next_action}`,
  ];
  return `${lines.join("\n")}\n`;
}

function writeMarkdownSummary({ markdownSummaryPath, markdownSummary }) {
  if (
    !markdownSummaryPath ||
    markdownSummaryPath === "undefined" ||
    markdownSummaryPath === "null"
  ) {
    return;
  }
  fs.appendFileSync(markdownSummaryPath, markdownSummary, "utf8");
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const logPath = args["log-path"];
  const summaryPath = args["summary-path"];
  const rawExitCode = args["exit-code"];
  const markdownSummaryPath = args["markdown-summary-path"];
  const summaryTitle = args["summary-title"] || "Frontend e2e smoke";

  if (!logPath) {
    console.error("[e2e-summary] fail: --log-path is required.");
    process.exit(1);
  }
  if (!summaryPath) {
    console.error("[e2e-summary] fail: --summary-path is required.");
    process.exit(1);
  }

  const parsedExitCode = Number(rawExitCode);
  const hasExitCode = Number.isFinite(parsedExitCode);
  const logAvailable = fs.existsSync(logPath);
  const log = logAvailable ? fs.readFileSync(logPath, "utf8") : "";
  const result = hasExitCode ? (parsedExitCode === 0 ? "pass" : "fail") : "unavailable";
  const { classification, nextAction } = classifyFailure({ result, log });

  const payload = {
    schema_version: E2E_SUMMARY_SCHEMA_VERSION,
    result,
    exit_code: hasExitCode ? parsedExitCode : null,
    classification,
    log_available: logAvailable,
    next_action: nextAction,
  };

  fs.writeFileSync(summaryPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  const markdownSummary = renderMarkdownSummary({
    payload,
    title: summaryTitle,
  });
  writeMarkdownSummary({
    markdownSummaryPath,
    markdownSummary,
  });

  console.log("[e2e-summary] e2e result");
  console.log(`  result: ${payload.result}`);
  console.log(`  exit_code: ${payload.exit_code ?? "n/a"}`);
  console.log(`  classification: ${payload.classification}`);
  console.log(`  log_available: ${payload.log_available ? "yes" : "no"}`);
  console.log(`  next_action: ${payload.next_action}`);
  process.stdout.write(markdownSummary);
}

main();
