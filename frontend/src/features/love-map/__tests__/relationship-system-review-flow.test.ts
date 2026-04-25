import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildRelationshipSystemReviewFlow,
  buildReviewFlowAllDoneCopy,
  buildReviewFlowAnchorId,
  buildReviewFlowCompleteCopy,
  buildReviewFlowContinueCopy,
  buildReviewFlowPendingCopy,
  type ReviewFlowInput,
} from '../relationship-system-review-flow.ts';

const baseInput: ReviewFlowInput = {
  hasPartner: true,
  compassPendingCount: 0,
  sharedFuturePendingCount: 0,
  sharedFutureRefinementPendingCount: 0,
};

test('buildRelationshipSystemReviewFlow returns zeroed/blank model when no partner', () => {
  const model = buildRelationshipSystemReviewFlow({
    ...baseInput,
    hasPartner: false,
    compassPendingCount: 3,
    sharedFuturePendingCount: 1,
    sharedFutureRefinementPendingCount: 2,
  });
  assert.equal(model.totalPending, 0);
  // Un-paired visitor never sees a "completed" celebration — they haven't
  // reached the review surface in the first place.
  assert.equal(model.isComplete, false);
  assert.equal(model.firstTarget, null);
  assert.deepEqual(model.targets, []);
});

test('buildRelationshipSystemReviewFlow returns complete state when partnered and nothing pending', () => {
  const model = buildRelationshipSystemReviewFlow(baseInput);
  assert.equal(model.totalPending, 0);
  assert.equal(model.isComplete, true);
  assert.equal(model.firstTarget, null);
  assert.deepEqual(model.targets, []);
});

test('buildRelationshipSystemReviewFlow targets Compass when only Compass is pending', () => {
  const model = buildRelationshipSystemReviewFlow({
    ...baseInput,
    compassPendingCount: 1,
  });
  assert.equal(model.totalPending, 1);
  assert.equal(model.isComplete, false);
  assert.equal(model.firstTarget?.kind, 'relationship_compass');
  assert.equal(model.firstTarget?.section, 'identity');
  assert.equal(model.firstTarget?.anchorId, 'pending-review-compass');
  assert.equal(model.firstTarget?.href, '#pending-review-compass');
  assert.equal(model.firstTarget?.count, 1);
  assert.equal(model.targets.length, 1);
});

test('buildRelationshipSystemReviewFlow targets Shared Future when only Shared Future is pending', () => {
  const model = buildRelationshipSystemReviewFlow({
    ...baseInput,
    sharedFuturePendingCount: 2,
  });
  assert.equal(model.totalPending, 2);
  assert.equal(model.firstTarget?.kind, 'shared_future');
  assert.equal(model.firstTarget?.section, 'future');
  assert.equal(model.firstTarget?.href, '#pending-review-future');
  assert.equal(model.firstTarget?.count, 2);
});

test('buildRelationshipSystemReviewFlow prioritises Compass over Shared Future when both are pending', () => {
  const model = buildRelationshipSystemReviewFlow({
    ...baseInput,
    compassPendingCount: 1,
    sharedFuturePendingCount: 3,
    sharedFutureRefinementPendingCount: 1,
  });
  assert.equal(model.totalPending, 5);
  assert.equal(model.firstTarget?.kind, 'relationship_compass');
  // targets carry the full ordered breakdown for surfaces that want
  // per-kind detail.
  assert.deepEqual(
    model.targets.map((t) => [t.kind, t.count]),
    [
      ['relationship_compass', 1],
      ['shared_future', 3],
      ['shared_future_refinement', 1],
    ],
  );
});

test('buildRelationshipSystemReviewFlow falls back to Future section anchor for refinement-only pending', () => {
  const model = buildRelationshipSystemReviewFlow({
    ...baseInput,
    sharedFutureRefinementPendingCount: 2,
  });
  // Refinements are rendered inline next to their target wishlist item;
  // they share the Future section anchor instead of getting a third
  // distinct landing spot.
  assert.equal(model.firstTarget?.kind, 'shared_future_refinement');
  assert.equal(model.firstTarget?.anchorId, 'future');
  assert.equal(model.firstTarget?.href, '#future');
});

test('buildRelationshipSystemReviewFlow floors invalid numeric counts to zero', () => {
  const model = buildRelationshipSystemReviewFlow({
    ...baseInput,
    compassPendingCount: Number.NaN,
    sharedFuturePendingCount: -2,
    sharedFutureRefinementPendingCount: 1.8,
  });
  assert.equal(model.totalPending, 1);
  assert.equal(model.firstTarget?.kind, 'shared_future_refinement');
  assert.equal(model.firstTarget?.count, 1);
});

test('buildRelationshipSystemReviewFlow advances firstTarget after Compass clears', () => {
  // Simulate post-accept refetch: Compass count drops to 0, Shared Future
  // remains pending. The next firstTarget should automatically point at
  // Shared Future without any per-suggestion tracking.
  const before = buildRelationshipSystemReviewFlow({
    ...baseInput,
    compassPendingCount: 1,
    sharedFuturePendingCount: 1,
  });
  assert.equal(before.firstTarget?.kind, 'relationship_compass');

  const after = buildRelationshipSystemReviewFlow({
    ...baseInput,
    compassPendingCount: 0,
    sharedFuturePendingCount: 1,
  });
  assert.equal(after.firstTarget?.kind, 'shared_future');
  assert.equal(after.totalPending, 1);
});

test('buildReviewFlowAnchorId returns stable ids per kind', () => {
  assert.equal(buildReviewFlowAnchorId('relationship_compass'), 'pending-review-compass');
  assert.equal(buildReviewFlowAnchorId('shared_future'), 'pending-review-future');
  assert.equal(buildReviewFlowAnchorId('shared_future_refinement'), 'future');
});

test('review-flow copy helpers produce the expected CTA labels and hrefs', () => {
  const pendingModel = buildRelationshipSystemReviewFlow({
    ...baseInput,
    compassPendingCount: 1,
    sharedFuturePendingCount: 1,
  });
  const pending = buildReviewFlowPendingCopy(pendingModel);
  assert.equal(pending.title, '待審核的 Haven 建議');
  assert.equal(pending.ctaLabel, '從第一則開始審核');
  assert.equal(pending.ctaHref, '#pending-review-compass');
  assert.ok(pending.description.includes('2 則'));

  const continueCopy = buildReviewFlowContinueCopy(pendingModel);
  assert.equal(continueCopy.title, '繼續審核下一則');
  assert.equal(continueCopy.ctaLabel, '繼續審核下一則');
  assert.equal(continueCopy.ctaHref, '#pending-review-compass');

  const completeCopy = buildReviewFlowCompleteCopy();
  assert.equal(completeCopy.title, '目前沒有待審核的更新');
  assert.equal(completeCopy.ctaHref, undefined);

  const allDone = buildReviewFlowAllDoneCopy();
  assert.equal(allDone.title, '所有待審核建議都已處理完');
  assert.equal(allDone.ctaHref, undefined);
});

test('review-flow pending copy hides CTA when there is no target to point at', () => {
  const emptyModel = buildRelationshipSystemReviewFlow(baseInput);
  const pending = buildReviewFlowPendingCopy(emptyModel);
  assert.equal(pending.ctaLabel, undefined);
  assert.equal(pending.ctaHref, undefined);
});
