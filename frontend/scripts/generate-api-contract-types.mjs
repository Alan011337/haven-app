#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..');
const inventoryPath = path.join(repoRoot, 'docs', 'security', 'api-inventory.json');
const outputPath = path.join(repoRoot, 'frontend', 'src', 'types', 'api-contract.ts');
const modeCheck = process.argv.includes('--check');

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function quote(value) {
  return `'${String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`;
}

function uniqueSorted(values) {
  return [...new Set(values)].sort((a, b) => a.localeCompare(b));
}

function renderUnionType(name, values) {
  const members = uniqueSorted(values).map((value) => quote(value)).join(' | ');
  return `export type ${name} = ${members || 'never'};`;
}

function renderEntries(entries) {
  const lines = entries.map(
    (entry) =>
      `  { method: ${quote(entry.method)}, path: ${quote(entry.path)}, authPolicy: ${quote(
        entry.auth_policy,
      )}, dataSensitivity: ${quote(entry.data_sensitivity)} },`,
  );
  return ['export const API_CONTRACT_ENTRIES = [', ...lines, '] as const;'].join('\n');
}

function renderPathsArray(name, entriesFilter) {
  const values = uniqueSorted(entriesFilter.map((entry) => entry.path)).map((value) => `  ${quote(value)},`);
  return [`export const ${name} = [`, ...values, '] as const;'].join('\n');
}

function buildOutput(payload) {
  const entries = Array.isArray(payload.entries) ? payload.entries : [];
  const methods = entries.map((entry) => entry.method);
  const authPolicies = entries.map((entry) => entry.auth_policy);
  const dataSensitivities = entries.map((entry) => entry.data_sensitivity);
  const mutatingEntries = entries.filter((entry) => ['POST', 'PUT', 'PATCH', 'DELETE'].includes(entry.method));
  const apiEntries = entries.filter((entry) => typeof entry.path === 'string' && entry.path.startsWith('/api/'));

  return `// AUTO-GENERATED FILE. DO NOT EDIT.
// Source: docs/security/api-inventory.json
// Generator: frontend/scripts/generate-api-contract-types.mjs

${renderUnionType('ApiContractMethod', methods)}
${renderUnionType('ApiContractAuthPolicy', authPolicies)}
${renderUnionType('ApiContractDataSensitivity', dataSensitivities)}

export type ApiContractEntry = {
  method: ApiContractMethod;
  path: string;
  authPolicy: ApiContractAuthPolicy;
  dataSensitivity: ApiContractDataSensitivity;
};

${renderEntries(entries)}

${renderPathsArray('MUTATING_API_PATHS', mutatingEntries)}
${renderPathsArray('API_PATHS', apiEntries)}
`;
}

function main() {
  if (!fs.existsSync(inventoryPath)) {
    console.error(`[api-contract-types] fail: missing inventory file: ${inventoryPath}`);
    process.exit(1);
  }
  const payload = readJson(inventoryPath);
  const output = buildOutput(payload);

  if (modeCheck) {
    if (!fs.existsSync(outputPath)) {
      console.error('[api-contract-types] fail: generated file missing, run contract:types:generate');
      process.exit(1);
    }
    const current = fs.readFileSync(outputPath, 'utf8');
    if (current !== output) {
      console.error('[api-contract-types] fail: generated file is stale, run contract:types:generate');
      process.exit(1);
    }
    console.log('[api-contract-types] ok: generated file is up to date');
    return;
  }

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, output, 'utf8');
  console.log(`[api-contract-types] generated: ${outputPath}`);
}

main();
