#!/usr/bin/env node
// frontend/scripts/generate-cards.mjs

import fs from 'fs';
import path from 'path';
import process from 'process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const VALID_CATEGORIES = [
  'DAILY_VIBE',
  'SOUL_DIVE',
  'SAFE_ZONE',
  'MEMORY_LANE',
  'GROWTH_QUEST',
  'AFTER_DARK',
  'CO_PILOT',
  'LOVE_BLUEPRINT',
];

const CATEGORY_GUIDE = {
  DAILY_VIBE: 'Light daily bonding questions. Keep tone warm and playful.',
  SOUL_DIVE: 'Introspective value-and-identity questions, emotionally safe but deeper.',
  SAFE_ZONE: 'Repair and de-escalation questions after conflict. Avoid blame.',
  MEMORY_LANE: 'Shared memory and nostalgia prompts to re-anchor connection.',
  GROWTH_QUEST: 'Mutual growth and future planning prompts with specific actions.',
  AFTER_DARK: 'Intimacy-oriented but respectful questions. Never explicit/pornographic.',
  CO_PILOT: 'Practical life coordination prompts (chores, travel, logistics, decisions).',
  LOVE_BLUEPRINT: 'Long-term blueprint prompts about family, finance, future lifestyle.',
};

function parseArgs(argv) {
  const args = new Map();
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const value = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : '1';
    args.set(key, value);
  }
  return args;
}

function usageAndExit(message) {
  if (message) console.error(`\n❌ ${message}\n`);
  console.error('Usage: node scripts/generate-cards.mjs --category CO_PILOT --count 20 [--depth 1] [--out scripts/data/generated]');
  process.exit(1);
}

function ensureCategory(value) {
  const category = String(value || '').trim().toUpperCase();
  if (!VALID_CATEGORIES.includes(category)) {
    usageAndExit(`Invalid category: ${value}.`);
  }
  return category;
}

function toPositiveInt(value, fallback) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) return fallback;
  return parsed;
}

function buildPrompt({ category, count, depth }) {
  return [
    `You are generating relationship card prompts for category ${category}.`,
    `Category guide: ${CATEGORY_GUIDE[category]}`,
    `Generate exactly ${count} cards.`,
    `Target depth_level: ${depth}.`,
    'Output must be a JSON object with key "cards" and array value.',
    'Each card must include: title, description, question, difficulty_level, depth_level, tags.',
    'difficulty_level and depth_level are integers in [1,2,3].',
    'tags must be 1-3 short tags.',
    'Use Traditional Chinese for title/description/question.',
    'Do not include markdown, explanation, or extra keys.',
  ].join('\n');
}

async function callOpenAI({ apiKey, model, prompt }) {
  const response = await fetch('https://api.openai.com/v1/responses', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      input: prompt,
      text: {
        format: {
          type: 'json_schema',
          name: 'generated_cards',
          schema: {
            type: 'object',
            additionalProperties: false,
            properties: {
              cards: {
                type: 'array',
                minItems: 1,
                items: {
                  type: 'object',
                  additionalProperties: false,
                  properties: {
                    title: { type: 'string', minLength: 2 },
                    description: { type: 'string', minLength: 2 },
                    question: { type: 'string', minLength: 6 },
                    difficulty_level: { type: 'integer', minimum: 1, maximum: 3 },
                    depth_level: { type: 'integer', minimum: 1, maximum: 3 },
                    tags: {
                      type: 'array',
                      minItems: 1,
                      maxItems: 3,
                      items: { type: 'string', minLength: 1 },
                    },
                  },
                  required: ['title', 'description', 'question', 'difficulty_level', 'depth_level', 'tags'],
                },
              },
            },
            required: ['cards'],
          },
          strict: true,
        },
      },
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`OpenAI request failed: ${response.status} ${text}`);
  }

  const payload = await response.json();
  const outputText = payload?.output_text;
  if (!outputText) {
    throw new Error('OpenAI response missing output_text.');
  }
  return JSON.parse(outputText);
}

function normalizeCards({ cards, category }) {
  if (!Array.isArray(cards)) throw new Error('Invalid output: cards must be array.');
  const now = new Date().toISOString();
  return cards.map((card, index) => ({
    id: '',
    category,
    title: String(card.title || '').trim(),
    description: String(card.description || '').trim(),
    question: String(card.question || '').trim(),
    difficulty_level: toPositiveInt(card.difficulty_level, 1),
    depth_level: toPositiveInt(card.depth_level, 1),
    tags: Array.isArray(card.tags) ? card.tags.map((item) => String(item).trim()).filter(Boolean).slice(0, 3) : [],
    is_ai_generated: true,
    created_at: now,
    _draft_index: index + 1,
  }));
}

function writeOutput({ outDir, category, cards }) {
  fs.mkdirSync(outDir, { recursive: true });
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filePath = path.join(outDir, `${category.toLowerCase()}-${timestamp}.json`);
  fs.writeFileSync(filePath, `${JSON.stringify(cards, null, 2)}\n`, 'utf-8');
  return filePath;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const category = ensureCategory(args.get('category'));
  const count = toPositiveInt(args.get('count'), 10);
  const depth = Math.min(3, Math.max(1, toPositiveInt(args.get('depth'), 1)));
  const outDir = path.resolve(__dirname, args.get('out') || 'data/generated');
  const model = String(args.get('model') || process.env.OPENAI_MODEL || 'gpt-4o-mini');
  const apiKey = process.env.OPENAI_API_KEY;

  if (!apiKey) {
    usageAndExit('OPENAI_API_KEY is required.');
  }

  const prompt = buildPrompt({ category, count, depth });
  const generated = await callOpenAI({ apiKey, model, prompt });
  const cards = normalizeCards({ cards: generated.cards, category });
  const filePath = writeOutput({ outDir, category, cards });

  console.log(`✅ Generated ${cards.length} drafts for ${category}`);
  console.log(`📄 Output: ${filePath}`);
  console.log('ℹ️ Next: review file manually, then merge into scripts/data/cards.json and run seed:cards:qa');
}

main().catch((error) => {
  console.error('❌ Failed to generate cards:', error.message);
  process.exit(1);
});
