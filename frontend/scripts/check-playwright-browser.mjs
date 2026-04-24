#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

const INSTALL_HINT = 'npx playwright install chromium';
const AUTO_INSTALL_ENV_KEY = 'PLAYWRIGHT_AUTO_INSTALL';
const BROWSERS_PATH_ENV_KEY = 'PLAYWRIGHT_BROWSERS_PATH';
const DEFAULT_BROWSERS_PATH = path.join(process.cwd(), '.playwright-browsers');
const INSTALL_LOCK_NAME = '__dirlock';
const require = createRequire(import.meta.url);

if (!Object.prototype.hasOwnProperty.call(process.env, BROWSERS_PATH_ENV_KEY)) {
  process.env[BROWSERS_PATH_ENV_KEY] = DEFAULT_BROWSERS_PATH;
}

fs.mkdirSync(process.env[BROWSERS_PATH_ENV_KEY], { recursive: true });

// Playwright derives macOS "slots" from the Darwin kernel major, then decides arm64 vs x64
// based on CPU model strings containing "Apple". Some sandboxes/hypervisors omit that signal,
// which makes Playwright think it's mac-x64 even on Apple Silicon Node builds — causing huge
// redundant Chromium downloads and "missing executable" false negatives.
if (
  process.platform === 'darwin' &&
  process.arch === 'arm64' &&
  !Object.prototype.hasOwnProperty.call(process.env, 'PLAYWRIGHT_HOST_PLATFORM_OVERRIDE')
) {
  const ver = os.release().split('.').map((a) => parseInt(a, 10));
  const darwinMajor = Number.isFinite(ver[0]) ? ver[0] : 0;
  const LAST_STABLE_MACOS_MAJOR_VERSION = 15;
  const macSlot = Math.min(darwinMajor - 9, LAST_STABLE_MACOS_MAJOR_VERSION);
  const hasAppleCpu = os.cpus().some((cpu) => String(cpu.model).includes('Apple'));
  // If CPU model strings are sanitized (common in sandboxes), Playwright can't infer Apple Silicon.
  // On a real arm64 Node build, defaulting to mac*-arm64 matches Chrome-for-testing arm64 bundles.
  if (hasAppleCpu || process.arch === 'arm64') {
    process.env.PLAYWRIGHT_HOST_PLATFORM_OVERRIDE = `mac${macSlot}-arm64`;
  }
}

function parseBool(rawValue) {
  if (!rawValue) return false;
  const normalized = String(rawValue).trim().toLowerCase();
  return normalized === '1' || normalized === 'true' || normalized === 'yes' || normalized === 'on';
}

function resolveChromiumExecutablePath() {
  try {
    const { chromium } = requirePlaywright();
    return {
      executablePath: chromium.executablePath(),
      error: null,
    };
  } catch (error) {
    return {
      executablePath: '',
      error,
    };
  }
}

function requirePlaywright() {
  // Lazy require so PLAYWRIGHT_BROWSERS_PATH is applied before Playwright resolves cache path.
  return require('@playwright/test');
}

function isExecutableReady(executablePath) {
  return Boolean(executablePath) && fs.existsSync(executablePath);
}

function printMissingExecutable(message) {
  console.error('[playwright-preflight] chromium executable not found.');
  console.error(
    `[playwright-preflight] ${BROWSERS_PATH_ENV_KEY}=${process.env[BROWSERS_PATH_ENV_KEY]}`,
  );
  if (message) {
    console.error(`[playwright-preflight] ${message}`);
  }
  console.error(`[playwright-preflight] run: ${INSTALL_HINT}`);
  console.error(
    `[playwright-preflight] tip: set ${AUTO_INSTALL_ENV_KEY}=1 to auto-install before e2e.`,
  );
}

function runChromiumInstall() {
  const installResult = spawnSync('npx', ['playwright', 'install', 'chromium'], {
    stdio: 'inherit',
    shell: process.platform === 'win32',
    env: process.env,
  });
  if (installResult.error) {
    throw installResult.error;
  }
  if (installResult.status !== 0) {
    throw new Error(`install command exited with code ${installResult.status ?? 'unknown'}`);
  }
}

function parseLockPathFromMessage(message) {
  if (!message) {
    return '';
  }
  const match = String(message).match(/Path:\s+(\S*__dirlock)\b/);
  return match ? match[1] : '';
}

function removeInstallLock(lockPath, reason) {
  if (!lockPath || !fs.existsSync(lockPath)) {
    return false;
  }
  try {
    fs.rmSync(lockPath, { force: true, recursive: true });
    console.error(`[playwright-preflight] removed install lock (${reason}): ${lockPath}`);
    return true;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(
      `[playwright-preflight] failed to remove install lock (${reason}): ${errorMessage}`,
    );
    return false;
  }
}

function clearKnownInstallLock(reason) {
  const lockPath = path.join(process.env[BROWSERS_PATH_ENV_KEY], INSTALL_LOCK_NAME);
  return removeInstallLock(lockPath, reason);
}

function maybeRemoveStaleInstallLock(errorMessage) {
  if (!String(errorMessage).includes('Unable to update lock within the stale threshold')) {
    return false;
  }
  const lockPath = parseLockPathFromMessage(errorMessage);
  if (!lockPath) {
    return clearKnownInstallLock('stale-lock-retry-fallback');
  }

  try {
    const stats = fs.statSync(lockPath);
    const ageMs = Date.now() - stats.mtimeMs;
    const staleThresholdMs = 10 * 60 * 1000;
    if (ageMs < staleThresholdMs) {
      console.error(
        `[playwright-preflight] install lock exists but is recent (${Math.round(ageMs / 1000)}s); skipping lock cleanup.`,
      );
      return false;
    }
    return removeInstallLock(lockPath, 'stale-lock-retry');
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    console.error(`[playwright-preflight] failed to remove stale install lock: ${reason}`);
    return false;
  }
}

function runChromiumInstallWithRetry() {
  try {
    runChromiumInstall();
    return;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (!maybeRemoveStaleInstallLock(message)) {
      throw error;
    }
    console.log('[playwright-preflight] retrying chromium install after stale lock cleanup.');
    runChromiumInstall();
  }
}

const autoInstallEnabled = parseBool(process.env[AUTO_INSTALL_ENV_KEY]);
const initialCheck = resolveChromiumExecutablePath();

if (isExecutableReady(initialCheck.executablePath)) {
  console.log(`[playwright-preflight] chromium executable ready: ${initialCheck.executablePath}`);
  console.log(`[playwright-preflight] ${BROWSERS_PATH_ENV_KEY}=${process.env[BROWSERS_PATH_ENV_KEY]}`);
  process.exit(0);
}

if (!autoInstallEnabled) {
  const message =
    initialCheck.error instanceof Error ? initialCheck.error.message : String(initialCheck.error ?? '');
  printMissingExecutable(message || undefined);
  process.exit(1);
}

console.log('[playwright-preflight] chromium executable missing; auto-install enabled.');
console.log(`[playwright-preflight] ${BROWSERS_PATH_ENV_KEY}=${process.env[BROWSERS_PATH_ENV_KEY]}`);
clearKnownInstallLock('preinstall-cleanup');
try {
  runChromiumInstallWithRetry();
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error('[playwright-preflight] auto-install failed.');
  console.error(
    `[playwright-preflight] ${BROWSERS_PATH_ENV_KEY}=${process.env[BROWSERS_PATH_ENV_KEY]}`,
  );
  console.error(`[playwright-preflight] ${message}`);
  console.error(`[playwright-preflight] run manually: ${INSTALL_HINT}`);
  process.exit(1);
}

const postInstallCheck = resolveChromiumExecutablePath();
if (isExecutableReady(postInstallCheck.executablePath)) {
  console.log(`[playwright-preflight] chromium executable ready: ${postInstallCheck.executablePath}`);
  console.log(`[playwright-preflight] ${BROWSERS_PATH_ENV_KEY}=${process.env[BROWSERS_PATH_ENV_KEY]}`);
  process.exit(0);
}

const postInstallMessage =
  postInstallCheck.error instanceof Error
    ? postInstallCheck.error.message
    : String(postInstallCheck.error ?? '');
printMissingExecutable(postInstallMessage || 'auto-install completed but executable still missing');
process.exit(1);
