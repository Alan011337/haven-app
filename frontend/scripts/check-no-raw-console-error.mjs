#!/usr/bin/env node

import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const SRC_ROOT = path.resolve(process.cwd(), 'src');
const ALLOWLIST = new Set([
  path.resolve(SRC_ROOT, 'lib/safe-error-log.ts'),
]);
const CODE_EXTENSIONS = new Set(['.ts', '.tsx', '.js', '.jsx']);

async function walk(dirPath) {
  const entries = await fs.readdir(dirPath, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const fullPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await walk(fullPath)));
      continue;
    }
    if (entry.isFile() && CODE_EXTENSIONS.has(path.extname(entry.name))) {
      files.push(fullPath);
    }
  }

  return files;
}

async function main() {
  const findings = [];
  const files = await walk(SRC_ROOT);

  for (const filePath of files) {
    if (ALLOWLIST.has(filePath)) {
      continue;
    }

    const content = await fs.readFile(filePath, 'utf8');
    const lines = content.split('\n');
    lines.forEach((line, index) => {
      if (!line.includes('console.error(')) {
        return;
      }
      if (line.includes('allow-raw-console-error')) {
        return;
      }
      const relativePath = path.relative(process.cwd(), filePath);
      findings.push(`${relativePath}:${index + 1}: ${line.trim()}`);
    });
  }

  if (findings.length > 0) {
    console.error('[console-error-guard] found raw console.error usage:');
    findings.forEach((item) => console.error(`  - ${item}`));
    console.error(
      '[console-error-guard] use logClientError from src/lib/safe-error-log.ts or add allow-raw-console-error with justification.',
    );
    process.exit(1);
  }

  console.log('[console-error-guard] ok: no raw console.error found in src/');
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`[console-error-guard] failed: ${message}`);
  process.exit(1);
});
