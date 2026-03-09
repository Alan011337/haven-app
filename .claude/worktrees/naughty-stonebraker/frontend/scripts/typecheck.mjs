#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import process from 'process';
import { spawnSync } from 'child_process';
import { fileURLToPath } from 'url';

const scriptFile = fileURLToPath(import.meta.url);
const frontendRoot = path.resolve(path.dirname(scriptFile), '..');
const DEFAULT_TIMEOUT_MS = Number(process.env.TYPECHECK_TIMEOUT_MS ?? 180_000);

const cleanTargets = [
  path.join(frontendRoot, '.next', 'types'),
  path.join(frontendRoot, '.next', 'dev', 'types'),
  path.join(frontendRoot, 'tsconfig.tsbuildinfo'),
];

for (const target of cleanTargets) {
  try {
    fs.rmSync(target, { recursive: true, force: true });
  } catch {
    // Ignore cleanup errors for non-existing or locked generated files.
  }
}

function runOrExit(command, args) {
  const startedAt = Date.now();
  const result = spawnSync(command, args, {
    cwd: frontendRoot,
    stdio: 'inherit',
    env: process.env,
    timeout: DEFAULT_TIMEOUT_MS,
    killSignal: 'SIGTERM',
  });

  const elapsedMs = Date.now() - startedAt;

  if (result.error) {
    if (result.error.name === 'TimeoutError' || result.error.code === 'ETIMEDOUT') {
      console.error(
        `[typecheck] timeout after ${Math.round(elapsedMs / 1000)}s: ${command} ${args.join(' ')}`,
      );
      process.exit(124);
    }
    console.error(`[typecheck] failed to run command: ${command} ${args.join(' ')}`);
    console.error(result.error.message);
    process.exit(1);
  }

  if (result.signal) {
    console.error(
      `[typecheck] terminated by signal ${result.signal}: ${command} ${args.join(' ')}`,
    );
    process.exit(1);
  }

  if (result.status !== 0) {
    console.error(
      `[typecheck] command failed (${result.status}): ${command} ${args.join(' ')}`,
    );
    process.exit(result.status ?? 1);
  }

  console.log(`[typecheck] ok (${Math.round(elapsedMs / 1000)}s): ${command} ${args.join(' ')}`);
}

runOrExit('npx', ['next', 'typegen']);
runOrExit('npx', ['tsc', '--noEmit', '--incremental', 'false']);
