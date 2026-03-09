#!/usr/bin/env node

import { spawn } from "node:child_process";
import process from "node:process";

function parseArgs(argv) {
  const parsed = {};
  const passthrough = [];
  for (let index = 0; index < argv.length; index += 1) {
    const raw = argv[index];
    if (!raw.startsWith("--")) {
      passthrough.push(raw);
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
  return { parsed, passthrough };
}

function parsePositiveInt(raw, fallback) {
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback;
  }
  return Math.floor(parsed);
}

function main() {
  const { parsed: args, passthrough } = parseArgs(process.argv.slice(2));
  const timeoutSeconds = parsePositiveInt(
    args["timeout-seconds"] ?? process.env.E2E_TIMEOUT_SECONDS ?? "420",
    420,
  );
  const graceSeconds = parsePositiveInt(
    args["grace-seconds"] ?? process.env.E2E_TIMEOUT_GRACE_SECONDS ?? "10",
    10,
  );

  const isWindows = process.platform === "win32";
  const npmArgs = ["run", "test:e2e:raw"];
  if (passthrough.length > 0) {
    npmArgs.push("--", ...passthrough);
  }
  const child = spawn("npm", npmArgs, {
    stdio: "inherit",
    shell: isWindows,
    detached: !isWindows,
    env: process.env,
  });

  let timedOut = false;
  let forcedKillTimer = null;

  const timeoutTimer = setTimeout(() => {
    timedOut = true;
    console.error(
      `[e2e-timeout] frontend e2e exceeded ${timeoutSeconds}s; sending SIGTERM (grace ${graceSeconds}s).`,
    );
    if (!isWindows && child.pid) {
      try {
        process.kill(-child.pid, "SIGTERM");
      } catch {
        // ignore; process may have exited already
      }
    } else {
      child.kill("SIGTERM");
    }

    forcedKillTimer = setTimeout(() => {
      if (!child.killed) {
        console.error("[e2e-timeout] frontend e2e still running after grace period; sending SIGKILL.");
      }
      if (!isWindows && child.pid) {
        try {
          process.kill(-child.pid, "SIGKILL");
        } catch {
          // ignore; process may have exited already
        }
      } else {
        child.kill("SIGKILL");
      }
    }, graceSeconds * 1000);
    forcedKillTimer.unref();
  }, timeoutSeconds * 1000);

  timeoutTimer.unref();

  child.on("error", (error) => {
    clearTimeout(timeoutTimer);
    if (forcedKillTimer) clearTimeout(forcedKillTimer);
    console.error(`[e2e-timeout] failed to start frontend e2e command: ${String(error)}`);
    process.exit(1);
  });

  child.on("close", (code, signal) => {
    clearTimeout(timeoutTimer);
    if (forcedKillTimer) clearTimeout(forcedKillTimer);

    if (timedOut) {
      process.exit(124);
      return;
    }
    if (typeof code === "number") {
      process.exit(code);
      return;
    }
    if (signal) {
      console.error(`[e2e-timeout] frontend e2e terminated by signal: ${signal}`);
    }
    process.exit(1);
  });
}

main();
