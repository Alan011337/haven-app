import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildAnalysisV2WeeklyChangeBrief,
  type AnalysisWeeklyChangeBriefInput,
} from '../analysis-v2-weekly-change.ts';

const NOW_MS = Date.parse('2026-03-15T12:00:00.000Z');

function daysAgo(days: number) {
  return new Date(NOW_MS - days * 24 * 60 * 60 * 1000).toISOString();
}

function baseInput(overrides: Partial<AnalysisWeeklyChangeBriefInput> = {}): AnalysisWeeklyChangeBriefInput {
  return {
    nowMs: NOW_MS,
    hasPartner: true,
    journals: [
      { created_at: daysAgo(1), owner: 'me', isHighTension: true },
      { created_at: daysAgo(2), owner: 'partner', isHighTension: false },
      { created_at: daysAgo(9), owner: 'me', isHighTension: false },
    ],
    appreciations: [
      { created_at: daysAgo(1) },
      { created_at: daysAgo(2) },
      { created_at: daysAgo(9) },
    ],
    relationshipCompassChanges: [],
    repairAgreementChanges: [],
    syncCompletionPct: 43,
    alignmentPct: 29,
    repairAgreementFieldCount: 3,
    hasHeartCare: true,
    topTopics: ['安全感'],
    loveMapAvailable: true,
    ...overrides,
  };
}

test('buildAnalysisV2WeeklyChangeBrief returns four stable movement questions', () => {
  const model = buildAnalysisV2WeeklyChangeBrief(baseInput());

  assert.equal(model.title, '上週以來，哪裡有變化');
  assert.deepEqual(model.cards.map((card) => card.question), [
    '更靠近了什麼',
    '變脆弱了什麼',
    '仍然穩定的是什麼',
    '現在最值得留意的是什麼',
  ]);
  assert.match(model.sourceNote, /近 7 天 \/ 前 7 天/);
});

test('increased appreciations become the closer movement', () => {
  const model = buildAnalysisV2WeeklyChangeBrief(baseInput());
  const closer = model.cards.find((card) => card.key === 'closer');

  assert.equal(closer?.tone, 'strength');
  assert.match(closer?.title ?? '', /感謝比前一週/);
  assert.equal(closer?.action.evidenceId, 'appreciation');
  assert.ok(closer?.sources.includes('Appreciation'));
});

test('increased high tension becomes the fragile movement and keeps repair grounding', () => {
  const model = buildAnalysisV2WeeklyChangeBrief(baseInput());
  const fragile = model.cards.find((card) => card.key === 'fragile');
  const focus = model.cards.find((card) => card.key === 'focus');

  assert.equal(fragile?.tone, 'attention');
  assert.match(fragile?.title ?? '', /高張力片段/);
  assert.ok(fragile?.sources.includes('Repair Agreements'));
  assert.equal(focus?.tone, 'attention');
  assert.equal(focus?.action.evidenceId, 'tension');
});

test('relationship compass revisions can ground weekly movement', () => {
  const model = buildAnalysisV2WeeklyChangeBrief(
    baseInput({
      appreciations: [],
      journals: [{ created_at: daysAgo(1), owner: 'me', isHighTension: false }],
      relationshipCompassChanges: [{ changed_at: daysAgo(2) }],
      repairAgreementChanges: [],
      syncCompletionPct: 72,
    }),
  );
  const closer = model.cards.find((card) => card.key === 'closer');

  assert.match(closer?.title ?? '', /共同方向/);
  assert.ok(closer?.sources.includes('Relationship Compass'));
  assert.equal(closer?.action.href, '/love-map#identity');
});

test('repair agreement revisions can ground weekly movement', () => {
  const model = buildAnalysisV2WeeklyChangeBrief(
    baseInput({
      appreciations: [],
      journals: [{ created_at: daysAgo(1), owner: 'me', isHighTension: false }],
      relationshipCompassChanges: [],
      repairAgreementChanges: [{ changed_at: daysAgo(2) }],
      syncCompletionPct: 72,
    }),
  );
  const closer = model.cards.find((card) => card.key === 'closer');

  assert.match(closer?.title ?? '', /修復約定/);
  assert.ok(closer?.sources.includes('Repair Agreements'));
  assert.equal(closer?.action.href, '/love-map#heart');
});

test('journal thinning is framed as attention without pretending diagnosis', () => {
  const model = buildAnalysisV2WeeklyChangeBrief(
    baseInput({
      journals: [
        { created_at: daysAgo(1), owner: 'me', isHighTension: false },
        { created_at: daysAgo(8), owner: 'me', isHighTension: false },
        { created_at: daysAgo(9), owner: 'partner', isHighTension: false },
        { created_at: daysAgo(10), owner: 'me', isHighTension: false },
      ],
      appreciations: [],
      syncCompletionPct: 70,
    }),
  );
  const fragile = model.cards.find((card) => card.key === 'fragile');

  assert.equal(fragile?.tone, 'attention');
  assert.match(fragile?.title ?? '', /可讀痕跡變少/);
  assert.equal(fragile?.action.evidenceId, 'patterns');
});

test('sparse prior data returns honest fallback instead of fake trend', () => {
  const model = buildAnalysisV2WeeklyChangeBrief(
    baseInput({
      journals: [{ created_at: daysAgo(1), owner: 'me', isHighTension: false }],
      appreciations: [],
      relationshipCompassChanges: [],
      repairAgreementChanges: [],
      syncCompletionPct: 0,
      repairAgreementFieldCount: 0,
      hasHeartCare: false,
      loveMapAvailable: false,
    }),
  );
  const closer = model.cards.find((card) => card.key === 'closer');
  const focus = model.cards.find((card) => card.key === 'focus');

  assert.match(model.sourceNote, /前 7 天樣本較少/);
  assert.match(closer?.title ?? '', /還在累積/);
  assert.match(focus?.title ?? '', /下週真的有東西可以比較/);
});

test('invalid and future dates are ignored safely', () => {
  const model = buildAnalysisV2WeeklyChangeBrief(
    baseInput({
      journals: [
        { created_at: 'not-a-date', owner: 'me', isHighTension: true },
        { created_at: new Date(NOW_MS + 60_000).toISOString(), owner: 'partner', isHighTension: true },
        { created_at: daysAgo(1), owner: 'me', isHighTension: false },
      ],
      appreciations: [{ created_at: 'bad-date' }],
      relationshipCompassChanges: [{ changed_at: new Date(NOW_MS + 60_000).toISOString() }],
      repairAgreementChanges: [{ changed_at: null }],
      syncCompletionPct: 0,
      repairAgreementFieldCount: 0,
      loveMapAvailable: false,
    }),
  );
  const fragile = model.cards.find((card) => card.key === 'fragile');

  assert.notEqual(fragile?.title, '高張力片段比前一週更需要先被照顧');
  assert.equal(model.cards.length, 4);
});
