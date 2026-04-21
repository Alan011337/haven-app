#!/usr/bin/env node

/**
 * Guard: reject extensionless relative imports in frontend unit tests.
 *
 * Why: frontend unit tests run under `node --test --experimental-strip-types`
 * (see `npm run test:unit`), which treats test files as native ESM. Node ESM
 * requires explicit file extensions on relative imports (`./foo.ts`, not
 * `./foo`). An extensionless relative import will fail at test runtime with
 * ERR_MODULE_NOT_FOUND. We previously had to normalize a batch of these by
 * hand — this guard makes the drift harder to silently reintroduce.
 *
 * Scope: mirrors `npm run test:unit`, which globs `src/**\/__tests__/*.test.ts`
 * in `frontend/package.json`. This guard covers that same universe plus
 * `*.test.tsx` for future-proofing. Product source, e2e specs, and scripts are
 * deliberately out of scope — they do not run under the strip-types ESM
 * harness and have different resolution semantics.
 */

import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const SRC_ROOT = path.resolve(process.cwd(), 'src');
const TEST_FILE_SUFFIXES = ['.test.ts', '.test.tsx'];
const ALLOWED_RELATIVE_EXT = new Set([
  '.ts',
  '.tsx',
  '.mjs',
  '.cjs',
  '.js',
  '.jsx',
  '.json',
]);

// Captures the string specifier inside `from '...'` / `from "..."`. This
// handles multi-line import clauses because we don't require the full import
// statement to be on one line — we just look for the `from '...'` tail.
const FROM_RE = /\bfrom\s+(['"])([^'"]+)\1/g;

// Captures dynamic `import('...')` / `import("...")` calls.
const DYN_RE = /\bimport\s*\(\s*(['"])([^'"]+)\1/g;

function isRelative(specifier) {
  return (
    specifier === '.' ||
    specifier === '..' ||
    specifier.startsWith('./') ||
    specifier.startsWith('../')
  );
}

async function walk(dirPath) {
  const out = [];
  const entries = await fs.readdir(dirPath, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      out.push(...(await walk(full)));
      continue;
    }
    if (!entry.isFile()) continue;
    if (!TEST_FILE_SUFFIXES.some((suffix) => entry.name.endsWith(suffix))) {
      continue;
    }
    // Only files nested inside a `__tests__` directory count as unit tests
    // for this guard; product files that happen to end in `.test.ts` are
    // not in scope.
    if (!full.includes(`${path.sep}__tests__${path.sep}`)) continue;
    out.push(full);
  }
  return out;
}

function scanFile(filePath, content) {
  // Strip // line comments so regex matches in comments don't cause false
  // positives (block comments are rare in test files and not stripped — if
  // they ever cause a false positive, the right fix is to remove the fake
  // import from the comment rather than widen the guard).
  const stripped = content
    .split('\n')
    .map((line) => {
      const idx = line.indexOf('//');
      return idx === -1 ? line : line.slice(0, idx);
    })
    .join('\n');

  const findings = [];
  const visit = (regex) => {
    regex.lastIndex = 0;
    let match;
    while ((match = regex.exec(stripped)) !== null) {
      const specifier = match[2];
      if (!isRelative(specifier)) continue;
      const ext = path.extname(specifier);
      if (ALLOWED_RELATIVE_EXT.has(ext)) continue;
      const lineNumber = stripped.slice(0, match.index).split('\n').length;
      findings.push({ filePath, lineNumber, specifier });
    }
  };
  visit(FROM_RE);
  visit(DYN_RE);
  return findings;
}

async function main() {
  let srcExists = false;
  try {
    const stat = await fs.stat(SRC_ROOT);
    srcExists = stat.isDirectory();
  } catch {
    srcExists = false;
  }
  if (!srcExists) {
    console.error(
      `[test-imports-guard] src/ not found under ${process.cwd()} — run from frontend/.`,
    );
    process.exit(1);
  }

  const files = await walk(SRC_ROOT);
  const findings = [];
  for (const filePath of files) {
    const content = await fs.readFile(filePath, 'utf8');
    findings.push(...scanFile(filePath, content));
  }

  if (findings.length > 0) {
    console.error(
      '[test-imports-guard] found extensionless relative imports in frontend unit tests:',
    );
    for (const f of findings) {
      const rel = path.relative(process.cwd(), f.filePath);
      console.error(`  - ${rel}:${f.lineNumber}: from '${f.specifier}'`);
    }
    console.error(
      "[test-imports-guard] Node's --experimental-strip-types runner (npm run test:unit) treats these tests as ESM,",
    );
    console.error(
      '[test-imports-guard] so relative imports need an explicit extension (.ts, .tsx, .mjs, .cjs, .js, .jsx, .json).',
    );
    console.error(
      "[test-imports-guard] Fix by adding the suffix — usually .ts — e.g. `from '../foo'` -> `from '../foo.ts'`.",
    );
    process.exit(1);
  }

  console.log(
    `[test-imports-guard] ok: checked ${files.length} unit test files; all relative imports use explicit extensions.`,
  );
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`[test-imports-guard] failed: ${message}`);
  process.exit(1);
});
