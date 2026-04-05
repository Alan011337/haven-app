import test from 'node:test';
import assert from 'node:assert/strict';

import {
  DAILY_VIBE_DEPTH_2_WARN_MIN,
  DAILY_VIBE_DEPTH_3_WARN_MIN,
  buildDailyVibeQualityReport,
  collectDailyVibeDepthHealth,
  collectDailyVibeDuplicateTitleSignals,
  collectDailyVibePlaceholderSignals,
} from '../content-review-daily-vibe.mjs';

function createCard({
  category = 'DAILY_VIBE',
  title,
  depth = 1,
  question = `${title} question`,
}) {
  return {
    category,
    title,
    question,
    depth_level: depth,
  };
}

test('collectDailyVibeDepthHealth warns when medium/deep support drops below floors', () => {
  const cards = [
    ...Array.from({ length: DAILY_VIBE_DEPTH_2_WARN_MIN - 1 }, (_, index) =>
      createCard({ title: `depth2-${index}`, depth: 2 }),
    ),
    ...Array.from({ length: DAILY_VIBE_DEPTH_3_WARN_MIN - 1 }, (_, index) =>
      createCard({ title: `depth3-${index}`, depth: 3 }),
    ),
    createCard({ title: 'depth1-0', depth: 1 }),
  ];

  const report = collectDailyVibeDepthHealth(cards);

  assert.deepEqual(report.depth_counts, {
    1: 1,
    2: DAILY_VIBE_DEPTH_2_WARN_MIN - 1,
    3: DAILY_VIBE_DEPTH_3_WARN_MIN - 1,
  });
  assert.equal(report.floor_warnings.length, 2);
  assert.match(report.floor_warnings[0], /depth 2 support below guard floor/);
  assert.match(report.floor_warnings[1], /depth 3 support below guard floor/);
});

test('collectDailyVibeDuplicateTitleSignals detects cross-depth and medium/deep duplicate titles', () => {
  const cards = [
    createCard({ title: '如果今天可以重來', depth: 1, question: 'light' }),
    createCard({ title: '如果今天可以重來', depth: 3, question: 'deep' }),
    createCard({ title: '訊息解讀', depth: 2, question: 'medium a' }),
    createCard({ title: '訊息解讀', depth: 2, question: 'medium b' }),
    createCard({ title: '只出現一次', depth: 3, question: 'solo' }),
  ];

  const signals = collectDailyVibeDuplicateTitleSignals(cards);

  assert.deepEqual(
    signals.cross_depth_duplicate_titles.map((item) => item.title),
    ['如果今天可以重來'],
  );
  assert.deepEqual(
    signals.medium_deep_duplicate_titles.map((item) => item.title),
    ['如果今天可以重來', '訊息解讀'],
  );
  assert.deepEqual(signals.cross_depth_duplicate_titles[0].depths, [1, 3]);
  assert.deepEqual(signals.medium_deep_duplicate_titles[1].depths, [2]);
});

test('collectDailyVibePlaceholderSignals only flags medium/deep numbered placeholders', () => {
  const cards = [
    createCard({ title: '日常共感 #01', depth: 1, question: 'light placeholder' }),
    createCard({ title: '日常共感 #14', depth: 2, question: 'medium placeholder' }),
    createCard({ title: '日常共感 #25', depth: 3, question: 'deep placeholder' }),
    createCard({ title: '收心儀式', depth: 3, question: 'named deep card' }),
  ];

  const signals = collectDailyVibePlaceholderSignals(cards);

  assert.deepEqual(signals.medium_deep_placeholder_titles, [
    {
      title: '日常共感 #14',
      depth: 2,
      question: 'medium placeholder',
    },
    {
      title: '日常共感 #25',
      depth: 3,
      question: 'deep placeholder',
    },
  ]);
});

test('buildDailyVibeQualityReport aggregates summary counts and warning signals', () => {
  const cards = [
    ...Array.from({ length: DAILY_VIBE_DEPTH_2_WARN_MIN }, (_, index) =>
      createCard({ title: `depth2-${index}`, depth: 2 }),
    ),
    ...Array.from({ length: DAILY_VIBE_DEPTH_3_WARN_MIN }, (_, index) =>
      createCard({ title: `depth3-${index}`, depth: 3 }),
    ),
    createCard({ title: '如果今天可以重來', depth: 1, question: 'light variant' }),
    createCard({ title: '如果今天可以重來', depth: 3, question: 'deep variant' }),
    createCard({ title: '日常共感 #23', depth: 2, question: 'placeholder' }),
  ];

  const report = buildDailyVibeQualityReport(cards);

  assert.equal(report.summary.total_cards, cards.length);
  assert.equal(report.summary.cross_depth_duplicate_titles_count, 1);
  assert.equal(report.summary.medium_deep_duplicate_titles_count, 1);
  assert.equal(report.summary.medium_deep_placeholder_titles_count, 1);
  assert.equal(report.depth_counts[2], DAILY_VIBE_DEPTH_2_WARN_MIN + 1);
  assert.equal(report.depth_counts[3], DAILY_VIBE_DEPTH_3_WARN_MIN + 1);
  assert.equal(report.floor_warnings.length, 0);
  assert.ok(report.warnings.includes('1 cross-depth duplicate titles detected'));
  assert.ok(report.warnings.includes('1 medium/deep duplicate titles detected'));
  assert.ok(report.warnings.includes('1 medium/deep placeholder titles detected'));
});
