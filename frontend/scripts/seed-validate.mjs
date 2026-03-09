import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const VALID_CATEGORIES = new Set([
  'DAILY_VIBE',
  'SOUL_DIVE',
  'SAFE_ZONE',
  'MEMORY_LANE',
  'GROWTH_QUEST',
  'AFTER_DARK',
  'CO_PILOT',
  'LOVE_BLUEPRINT',
]);

const args = new Set(process.argv.slice(2));
const isStrict = args.has('--strict');
const minCardsPerCategory = Number(process.env.SEED_MIN_PER_CATEGORY ?? 100);

function fail(message) {
  console.error(`[seed-validate] ${message}`);
  process.exit(1);
}

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : '';
}

const dataPath = path.join(__dirname, 'data', 'cards.json');
if (!fs.existsSync(dataPath)) {
  fail(`cards data not found: ${dataPath}`);
}

let payload;
try {
  payload = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));
} catch (error) {
  fail(`invalid JSON in cards file: ${error instanceof Error ? error.message : String(error)}`);
}

if (!Array.isArray(payload)) {
  fail('cards.json must be an array');
}

const counts = new Map();
const errors = [];

for (let i = 0; i < payload.length; i += 1) {
  const row = payload[i];
  if (!row || typeof row !== 'object') {
    errors.push(`row[${i}] is not an object`);
    continue;
  }

  const category = normalizeText(row.category).toUpperCase();
  const title = normalizeText(row.title);
  const description = normalizeText(row.description);
  const question = normalizeText(row.question);
  const depth = Number(row.depth_level ?? 1);

  if (!VALID_CATEGORIES.has(category)) {
    errors.push(`row[${i}] invalid category: ${String(row.category)}`);
    continue;
  }
  counts.set(category, (counts.get(category) ?? 0) + 1);

  if (!title) errors.push(`row[${i}] missing title`);
  if (!description) errors.push(`row[${i}] missing description`);
  if (!question) errors.push(`row[${i}] missing question`);
  if (!Number.isInteger(depth) || depth < 1 || depth > 3) {
    errors.push(`row[${i}] invalid depth_level: ${String(row.depth_level)}`);
  }
}

console.log('[seed-validate] category counts:');
for (const category of VALID_CATEGORIES) {
  console.log(`  - ${category}: ${counts.get(category) ?? 0}`);
}

if (isStrict) {
  for (const category of VALID_CATEGORIES) {
    const count = counts.get(category) ?? 0;
    if (count < minCardsPerCategory) {
      errors.push(
        `strict mode category ${category} has ${count}, requires >= ${minCardsPerCategory} (SEED_MIN_PER_CATEGORY)`,
      );
    }
  }
}

if (errors.length > 0) {
  console.error('[seed-validate] failed:');
  for (const issue of errors.slice(0, 80)) {
    console.error(`  - ${issue}`);
  }
  if (errors.length > 80) {
    console.error(`  ... and ${errors.length - 80} more issues`);
  }
  process.exit(1);
}

console.log('[seed-validate] ok');
