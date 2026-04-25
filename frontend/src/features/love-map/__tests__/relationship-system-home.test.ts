import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildRelationshipSystemHomeModel,
  formatRelationshipSystemCount,
  type RelationshipSystemHomeInput,
} from '../relationship-system-home.ts';

const baseInput: RelationshipSystemHomeInput = {
  hasPartner: true,
  compassCueCount: 3,
  careCueCount: 5,
  repairAgreementCount: 3,
  storyAnchorCount: 2,
  wishlistCount: 3,
  filledLayerCount: 2,
  compassPendingCount: 0,
  futurePendingCount: 0,
  refinementPendingCount: 0,
  repairPendingCount: 0,
  compassHistoryCount: 1,
  repairHistoryCount: 2,
  lastActivityLabel: '4/24 20:15',
};

test('buildRelationshipSystemHomeModel derives saved, pending, evolution counts', () => {
  const model = buildRelationshipSystemHomeModel({
    ...baseInput,
    compassPendingCount: 1,
    futurePendingCount: 2,
    refinementPendingCount: 1,
    repairPendingCount: 1,
  });

  assert.equal(model.savedDomainCount, 4);
  assert.equal(model.pendingReviewCount, 5);
  assert.equal(model.evolutionCount, 3);
  assert.equal(model.statusCards[0]?.eyebrow, '已保存的共同真相');
  assert.equal(model.statusCards[1]?.value, '5 則');
  assert.equal(model.statusCards[2]?.value, '3 次');
});

test('buildRelationshipSystemHomeModel keeps the four base anchors stable', () => {
  const model = buildRelationshipSystemHomeModel(baseInput);

  assert.deepEqual(
    model.navItems.slice(0, 4).map((item) => [item.key, item.href]),
    [
      ['identity', '#identity'],
      ['heart', '#heart'],
      ['story', '#story'],
      ['future', '#future'],
    ],
  );
  assert.equal(model.navItems.at(-1)?.key, 'recent-evolution');
  assert.equal(model.navItems.at(-1)?.href, '#evolution');
});

test('buildRelationshipSystemHomeModel links evolving status card and nextAction to #evolution when history exists', () => {
  const model = buildRelationshipSystemHomeModel(baseInput);
  assert.equal(model.statusCards[2]?.key, 'evolving');
  assert.equal(model.statusCards[2]?.href, '#evolution');
  assert.equal(model.nextAction.href, '#evolution');
  assert.equal(model.nextAction.label, '回看最近演進');
});

test('buildRelationshipSystemHomeModel omits evolution deep links when there is no saved history', () => {
  const model = buildRelationshipSystemHomeModel({
    ...baseInput,
    compassHistoryCount: 0,
    repairHistoryCount: 0,
  });
  assert.equal(model.evolutionCount, 0);
  assert.equal(model.statusCards[2]?.href, undefined);
  assert.equal(model.navItems.find((i) => i.key === 'recent-evolution'), undefined);
  assert.equal(model.nextAction.label, '回看關係地圖');
  assert.equal(model.nextAction.href, '#identity');
});

test('buildRelationshipSystemHomeModel points pending review to the highest-priority pending area', () => {
  const compassPending = buildRelationshipSystemHomeModel({
    ...baseInput,
    compassPendingCount: 1,
    futurePendingCount: 1,
  });
  const heartPending = buildRelationshipSystemHomeModel({
    ...baseInput,
    compassPendingCount: 0,
    repairPendingCount: 1,
    futurePendingCount: 1,
  });
  const futurePending = buildRelationshipSystemHomeModel({
    ...baseInput,
    compassPendingCount: 0,
    repairPendingCount: 0,
    futurePendingCount: 1,
  });

  assert.equal(compassPending.nextAction.href, '#identity');
  assert.equal(heartPending.nextAction.href, '#heart');
  assert.equal(futurePending.nextAction.href, '#future');
});

test('buildRelationshipSystemHomeModel returns calm unpaired fallback', () => {
  const model = buildRelationshipSystemHomeModel({
    ...baseInput,
    hasPartner: false,
    compassCueCount: 0,
    careCueCount: 0,
    repairAgreementCount: 0,
    storyAnchorCount: 0,
    wishlistCount: 0,
    compassPendingCount: 2,
    compassHistoryCount: 3,
    repairHistoryCount: 3,
    lastActivityLabel: null,
  });

  assert.equal(model.savedDomainCount, 0);
  assert.equal(model.pendingReviewCount, 0);
  assert.equal(model.evolutionCount, 0);
  assert.equal(model.statusCards[0]?.value, '待完成');
  assert.equal(model.nextAction.href, '/settings#settings-relationship');
  assert.equal(model.navItems.find((item) => item.key === 'pending-review'), undefined);
});

test('buildRelationshipSystemHomeModel chooses useful next action after pending work is clear', () => {
  assert.equal(
    buildRelationshipSystemHomeModel({ ...baseInput, compassCueCount: 2 }).nextAction.label,
    '補完整 Relationship Compass',
  );
  assert.equal(
    buildRelationshipSystemHomeModel({ ...baseInput, repairAgreementCount: 2 }).nextAction.label,
    '補完整 Repair Agreements',
  );
  assert.equal(
    buildRelationshipSystemHomeModel({ ...baseInput, wishlistCount: 0 }).nextAction.label,
    '留下第一個 Future 片段',
  );
});

test('formatRelationshipSystemCount never exposes invalid numeric text', () => {
  assert.equal(formatRelationshipSystemCount(Number.NaN, '則'), '還在累積');
  assert.equal(formatRelationshipSystemCount(-1, '則'), '還在累積');
  assert.equal(formatRelationshipSystemCount(2.8, '則'), '2 則');
});
