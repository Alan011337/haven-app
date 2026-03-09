#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import process from 'process';
import { spawnSync } from 'child_process';
import { fileURLToPath } from 'url';

const scriptFile = fileURLToPath(import.meta.url);
const frontendRoot = path.resolve(path.dirname(scriptFile), '..');
const DEFAULT_TIMEOUT_MS = Number(process.env.TYPECHECK_TIMEOUT_MS ?? 300_000);
const TYPEGEN_TIMEOUT_MS = Number(process.env.TYPECHECK_TYPEGEN_TIMEOUT_MS ?? DEFAULT_TIMEOUT_MS);
const TSC_TIMEOUT_MS = Number(process.env.TYPECHECK_TSC_TIMEOUT_MS ?? DEFAULT_TIMEOUT_MS);
const SKIP_TYPEGEN = ['1', 'true', 'yes'].includes(
  String(process.env.TYPECHECK_SKIP_TYPEGEN ?? '').toLowerCase(),
);
const localBin = (binName) => path.join(frontendRoot, 'node_modules', '.bin', binName);

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

function runOrExit(command, args, timeoutMs) {
  const startedAt = Date.now();
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

if (SKIP_TYPEGEN) {
  console.log('[typecheck] skipping next typegen (TYPECHECK_SKIP_TYPEGEN enabled)');
} else {
  runOrExit(localBin('next'), ['typegen'], TYPEGEN_TIMEOUT_MS);
}
runOrExit(
  localBin('tsc'),
  ['--project', 'tsconfig.typecheck.json', '--noEmit', '--incremental'],
  TSC_TIMEOUT_MS,
);
