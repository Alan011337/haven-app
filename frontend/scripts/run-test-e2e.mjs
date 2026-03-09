#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';

const env = { ...process.env };
if (!Object.prototype.hasOwnProperty.call(env, 'PLAYWRIGHT_AUTO_INSTALL')) {
  env.PLAYWRIGHT_AUTO_INSTALL = '1';
}
if (!Object.prototype.hasOwnProperty.call(env, 'PLAYWRIGHT_BROWSERS_PATH')) {
  env.PLAYWRIGHT_BROWSERS_PATH = path.join(process.cwd(), '.playwright-browsers');
}
if (!Object.prototype.hasOwnProperty.call(env, 'E2E_TIMEOUT_SECONDS')) {
  env.E2E_TIMEOUT_SECONDS = '420';
}
if (!Object.prototype.hasOwnProperty.call(env, 'E2E_TIMEOUT_GRACE_SECONDS')) {
  env.E2E_TIMEOUT_GRACE_SECONDS = '10';
}

const passthroughArgs = process.argv.slice(2);
const npmArgs = ['run', 'test:e2e:raw'];
if (passthroughArgs.length > 0) {
  npmArgs.push('--', ...passthroughArgs);
}

const result = spawnSync('npm', npmArgs, {
  stdio: 'inherit',
  shell: process.platform === 'win32',
  env,
  timeout: Number.parseInt(env.E2E_TIMEOUT_SECONDS, 10) * 1000 || 420_000,
});

if (result.error) {
  if (result.error.name === 'Error' && `${result.error.message}`.toLowerCase().includes('timed out')) {
    console.error('[test-e2e-wrapper] e2e timed out.');
  }
  console.error(`[test-e2e-wrapper] failed to start npm: ${String(result.error)}`);
  process.exit(1);
}

if (typeof result.status === 'number') {
  process.exit(result.status);
}

process.exit(1);
