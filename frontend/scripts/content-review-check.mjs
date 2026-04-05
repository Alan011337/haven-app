#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import process from 'process';
import { fileURLToPath } from 'url';

import { buildDailyVibeQualityReport } from './content-review-daily-vibe.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dataPath = path.resolve(__dirname, 'data/cards.json');
const minCardsPerCategory = Number(process.env.SEED_MIN_PER_CATEGORY ?? 100);
const maxCoPilotWeak = Number(process.env.CONTENT_REVIEW_MAX_COPILOT_WEAK ?? -1);

const categories = [
  'DAILY_VIBE',
  'SOUL_DIVE',
  'SAFE_ZONE',
  'MEMORY_LANE',
  'GROWTH_QUEST',
  'AFTER_DARK',
  'CO_PILOT',
  'LOVE_BLUEPRINT',
];

const blockedAfterDarkPatterns = [
  /強迫/i,
  /偷拍/i,
  /未成年/i,
  /暴力性愛/i,
  /porn|porno|色情片/i,
];

const coPilotPracticalHints = [
  '家務',
  '行程',
  '預算',
  '旅遊',
  '分工',
  '帳單',
  '生活',
  '時間',
  '決策',
];

function readCards() {
  if (!fs.existsSync(dataPath)) {
    throw new Error(`cards.json not found: ${dataPath}`);
  }
  const raw = fs.readFileSync(dataPath, 'utf-8');
  const payload = JSON.parse(raw);
  if (!Array.isArray(payload)) throw new Error('cards.json must be an array.');
  return payload;
}

function countByCategory(cards) {
  const counts = new Map(categories.map((cat) => [cat, 0]));
  for (const card of cards) {
    const category = String(card.category || '').trim().toUpperCase();
    if (!counts.has(category)) continue;
    counts.set(category, (counts.get(category) || 0) + 1);
  }
  return counts;
}

function collectAfterDarkViolations(cards) {
  const violations = [];
  for (const card of cards) {
    const category = String(card.category || '').trim().toUpperCase();
    if (category !== 'AFTER_DARK') continue;
    const text = `${card.title || ''}\n${card.description || ''}\n${card.question || ''}`;
    for (const pattern of blockedAfterDarkPatterns) {
      if (pattern.test(text)) {
        violations.push({
          id: card.id || '',
          title: card.title || '',
          reason: `blocked_pattern:${pattern.toString()}`,
        });
        break;
      }
    }
  }
  return violations;
}

function collectCoPilotWeakPracticality(cards) {
  const weak = [];
  for (const card of cards) {
    const category = String(card.category || '').trim().toUpperCase();
    if (category !== 'CO_PILOT') continue;
    const text = `${card.title || ''} ${card.description || ''} ${card.question || ''}`;
    const hit = coPilotPracticalHints.some((hint) => text.includes(hint));
    if (!hit) {
      weak.push({
        id: card.id || '',
        title: card.title || '',
        reason: 'missing_practical_hint',
      });
    }
  }
  return weak;
}

function main() {
  const cards = readCards();
  const counts = countByCategory(cards);
  const insufficient = categories.filter((cat) => (counts.get(cat) || 0) < minCardsPerCategory);
  const afterDarkViolations = collectAfterDarkViolations(cards);
  const coPilotWeak = collectCoPilotWeakPracticality(cards);
  const dailyVibeQuality = buildDailyVibeQualityReport(cards);

  console.log('[content-review-check] category counts:');
  for (const cat of categories) {
    console.log(`  - ${cat}: ${counts.get(cat) || 0}`);
  }

  if (insufficient.length > 0) {
    console.error(`[content-review-check] insufficient card count (<${minCardsPerCategory}): ${insufficient.join(', ')}`);
  }

  if (afterDarkViolations.length > 0) {
    console.error(`[content-review-check] AFTER_DARK blocked pattern violations: ${afterDarkViolations.length}`);
  }

  // CO_PILOT practicality issue defaults to warning-level, but can be gated by threshold.
  if (coPilotWeak.length > 0) {
    console.warn(`[content-review-check] CO_PILOT weak practicality candidates: ${coPilotWeak.length}`);
  }
  if (maxCoPilotWeak >= 0 && coPilotWeak.length > maxCoPilotWeak) {
    console.error(
      `[content-review-check] CO_PILOT weak practicality exceeds threshold: ${coPilotWeak.length} > ${maxCoPilotWeak}`,
    );
  }

  const depthCounts = dailyVibeQuality.depth_counts;
  const depthRatios = dailyVibeQuality.depth_ratios;
  console.log('[content-review-check] DAILY_VIBE quality:');
  console.log(
    `  - depth counts: L1=${depthCounts[1]} L2=${depthCounts[2]} L3=${depthCounts[3]}`,
  );
  console.log(
    `  - depth ratios: L1=${(depthRatios[1] * 100).toFixed(1)}% L2=${(depthRatios[2] * 100).toFixed(1)}% L3=${(depthRatios[3] * 100).toFixed(1)}%`,
  );

  if (dailyVibeQuality.floor_warnings.length > 0) {
    console.warn(
      `[content-review-check] DAILY_VIBE floor warnings: ${dailyVibeQuality.floor_warnings.join(' | ')}`,
    );
  } else {
    console.log('  - floor warnings: none');
  }

  const crossDepthTitles = dailyVibeQuality.cross_depth_duplicate_titles.map((item) => item.title);
  const mediumDeepDuplicateTitles = dailyVibeQuality.medium_deep_duplicate_titles.map((item) => item.title);
  const placeholderTitles = dailyVibeQuality.medium_deep_placeholder_titles.map((item) => item.title);

  if (crossDepthTitles.length > 0) {
    console.warn(
      `[content-review-check] DAILY_VIBE cross-depth duplicate titles: ${crossDepthTitles.length} (${crossDepthTitles.slice(0, 5).join(', ')})`,
    );
  } else {
    console.log('  - cross-depth duplicate titles: none');
  }

  if (mediumDeepDuplicateTitles.length > 0) {
    console.warn(
      `[content-review-check] DAILY_VIBE medium/deep duplicate titles: ${mediumDeepDuplicateTitles.length} (${mediumDeepDuplicateTitles.slice(0, 5).join(', ')})`,
    );
  } else {
    console.log('  - medium/deep duplicate titles: none');
  }

  if (placeholderTitles.length > 0) {
    console.warn(
      `[content-review-check] DAILY_VIBE medium/deep placeholder titles: ${placeholderTitles.length} (${placeholderTitles.slice(0, 5).join(', ')})`,
    );
  } else {
    console.log('  - medium/deep placeholder titles: none');
  }

  const report = {
    generated_at: new Date().toISOString(),
    min_cards_per_category: minCardsPerCategory,
    counts: Object.fromEntries(categories.map((cat) => [cat, counts.get(cat) || 0])),
    insufficient_categories: insufficient,
    after_dark_blocked_violations: afterDarkViolations.slice(0, 200),
    co_pilot_weak_practicality: coPilotWeak.slice(0, 200),
    max_co_pilot_weak: maxCoPilotWeak,
    daily_vibe_quality: dailyVibeQuality,
  };

  const reportPath = path.resolve(__dirname, 'data/reports/content-review-report.json');
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf-8');
  console.log(`[content-review-check] report: ${reportPath}`);

  if (
    insufficient.length > 0
    || afterDarkViolations.length > 0
    || (maxCoPilotWeak >= 0 && coPilotWeak.length > maxCoPilotWeak)
  ) {
    process.exit(1);
  }
  console.log('[content-review-check] ok');
}

try {
  main();
} catch (error) {
  console.error('[content-review-check] failed:', error.message);
  process.exit(1);
}
