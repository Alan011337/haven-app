#!/usr/bin/env node

import path from 'path';
import process from 'process';
import { spawnSync } from 'child_process';
import { fileURLToPath } from 'url';

const scriptFile = fileURLToPath(import.meta.url);
const frontendRoot = path.resolve(path.dirname(scriptFile), '..');
const timeoutMs = Number(process.env.LINT_TIMEOUT_MS ?? 420_000);
const lintScope = (process.env.LINT_SCOPE ?? 'all').trim().toLowerCase();

function runOrExit(command, args) {
  const startedAt = Date.now();
  console.log(`[lint] running: ${command} ${args.join(' ')}`);
  const result = spawnSync(command, args, {
    cwd: frontendRoot,
    stdio: 'inherit',
    env: process.env,
    timeout: timeoutMs,
    killSignal: 'SIGTERM',
  });

  const elapsedMs = Date.now() - startedAt;
  if (result.error) {
    if (result.error.name === 'TimeoutError' || result.error.code === 'ETIMEDOUT') {
      console.error(
        `[lint] timeout after ${Math.round(elapsedMs / 1000)}s: ${command} ${args.join(' ')}`,
      );
      process.exit(124);
    }
    console.error(`[lint] failed to run command: ${command} ${args.join(' ')}`);
    console.error(result.error.message);
    process.exit(1);
  }
  if (result.signal) {
    console.error(`[lint] terminated by signal ${result.signal}: ${command} ${args.join(' ')}`);
    process.exit(1);
  }
  if (result.status !== 0) {
    console.error(`[lint] command failed (${result.status}): ${command} ${args.join(' ')}`);
    process.exit(result.status ?? 1);
  }

  console.log(`[lint] ok (${Math.round(elapsedMs / 1000)}s): ${command} ${args.join(' ')}`);
}

function resolveChangedTargets() {
  const allowedPrefixes = ['src/', 'e2e/', 'scripts/'];
  const files = new Set();
  const collect = (args) => {
    const result = spawnSync('git', args, {
      cwd: frontendRoot,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: process.env,
      timeout: 20_000,
      encoding: 'utf8',
    });
    if (result.status !== 0 || result.error) {
      return;
    }
    for (const line of result.stdout.split('\n')) {
      const rawCandidate = line.trim();
      if (!rawCandidate) continue;
      const candidate = rawCandidate.startsWith('frontend/')
        ? rawCandidate.slice('frontend/'.length)
        : rawCandidate;
      if (!allowedPrefixes.some((prefix) => candidate.startsWith(prefix))) continue;
      if (candidate === 'scripts/lint.mjs') continue;
      files.add(candidate);
    }
  };
  collect(['diff', '--name-only', '--diff-filter=ACMRTUXB', 'HEAD', '--', 'src', 'e2e', 'scripts']);
  collect(['diff', '--cached', '--name-only', '--diff-filter=ACMRTUXB', '--', 'src', 'e2e', 'scripts']);
  return Array.from(files);
}

const eslintBin = path.join(frontendRoot, 'node_modules', '.bin', 'eslint');
const eslintBaseArgs = [
  '--cache',
  '--cache-location',
  '.next/cache/eslint',
  '--max-warnings',
  '0',
  '--no-error-on-unmatched-pattern',
];

if (lintScope === 'changed') {
  const changedTargets = resolveChangedTargets();
  if (changedTargets.length === 0) {
    console.log('[lint] no changed frontend files under src/e2e/scripts; skip eslint');
    process.exit(0);
  }
  runOrExit(eslintBin, [...changedTargets, ...eslintBaseArgs]);
} else {
  runOrExit(eslintBin, [
    'src',
    'e2e',
    'scripts',
    ...eslintBaseArgs,
  ]);
}
