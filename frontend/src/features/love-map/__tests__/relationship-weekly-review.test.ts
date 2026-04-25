import assert from 'node:assert/strict';
import test from 'node:test';

import { buildRelationshipWeeklyReviewRitualModel } from '../relationship-weekly-review.ts';

test('returns null when unpaired', () => {
  assert.equal(
    buildRelationshipWeeklyReviewRitualModel({
      hasPartner: false,
      pendingReviewCount: 2,
      evolutionCount: 3,
      compassHistoryCount: 1,
      repairHistoryCount: 1,
    }),
    null,
  );
});

test('stable prompt order and keys', () => {
  const model = buildRelationshipWeeklyReviewRitualModel({
    hasPartner: true,
    now: new Date('2026-04-25T12:00:00Z'),
    pendingReviewCount: 0,
    evolutionCount: 0,
    compassHistoryCount: 0,
    repairHistoryCount: 0,
  });
  assert.ok(model);
  assert.deepEqual(
    model.prompts.map((p) => p.key),
    ['understood_this_week', 'worth_carrying_forward', 'needs_care', 'next_week_intention'],
  );
});

test('derives ISO week label (Mon–Sun) in UTC', () => {
  // 2026-04-25 is Saturday; ISO week start Monday 2026-04-20.
  const model = buildRelationshipWeeklyReviewRitualModel({
    hasPartner: true,
    now: new Date('2026-04-25T04:05:06Z'),
    pendingReviewCount: 0,
    evolutionCount: 0,
    compassHistoryCount: 0,
    repairHistoryCount: 0,
  });
  assert.ok(model);
  assert.equal(model.weekLabel, '2026-04-20–2026-04-26');
});

test('includes pending/evolution/heart/identity cues when counts present', () => {
  const model = buildRelationshipWeeklyReviewRitualModel({
    hasPartner: true,
    now: new Date('2026-04-25T04:05:06Z'),
    pendingReviewCount: 2,
    evolutionCount: 3,
    compassHistoryCount: 1,
    repairHistoryCount: 1,
  });
  assert.ok(model);
  const cueKeys = model.cues.map((c) => c.key);
  assert.ok(cueKeys.includes('pending-review'));
  assert.ok(cueKeys.includes('evolution'));
  assert.ok(cueKeys.includes('heart'));
  assert.ok(cueKeys.includes('identity'));
  assert.ok(cueKeys.includes('future'));
  assert.equal(model.emptyNudge, null);
});

test('sparse data returns calm empty nudge and still offers Future as a gentle next step', () => {
  const model = buildRelationshipWeeklyReviewRitualModel({
    hasPartner: true,
    now: new Date('2026-04-25T04:05:06Z'),
    pendingReviewCount: 0,
    evolutionCount: 0,
    compassHistoryCount: 0,
    repairHistoryCount: 0,
  });
  assert.ok(model);
  assert.ok(model.cues.some((c) => c.key === 'future'));
  assert.ok(model.emptyNudge);
});

