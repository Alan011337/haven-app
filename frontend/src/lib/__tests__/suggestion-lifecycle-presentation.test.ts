import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildCompassEmptyStatePresentation,
  buildCompassInsufficientSignalPresentation,
  buildHandledSuggestionNotice,
  buildMutationCopy,
  buildSharedFutureEmptyStatePresentation,
  buildSharedFutureInsufficientSignalPresentation,
  isSharedFutureDuplicateTitle,
} from '../suggestion-lifecycle-presentation.ts';

test('compass empty state has calm CTA', () => {
  const out = buildCompassEmptyStatePresentation();
  assert.equal(out.eyebrow, 'Compass 建議更新');
  assert.ok(out.title.includes('目前沒有待審核'));
  assert.ok(out.ctaLabel.length > 0);
});

test('compass insufficient signal copy preserves trust', () => {
  const out = buildCompassInsufficientSignalPresentation();
  assert.ok(out.title.includes('足夠清楚'));
  assert.ok(out.description.includes('沒有被改動'));
});

test('shared future empty state mentions pair-visible boundary', () => {
  const out = buildSharedFutureEmptyStatePresentation();
  assert.ok(out.description.includes('共同看見'));
  assert.equal(out.ctaLabel, '讓 Haven 提一版');
});

test('shared future insufficient signal copy mentions boundary', () => {
  const out = buildSharedFutureInsufficientSignalPresentation();
  assert.ok(out.description.includes('共同看見'));
});

test('handled notice is explicit and calm', () => {
  const out = buildHandledSuggestionNotice();
  assert.ok(out.title.includes('已經處理過'));
  assert.ok(out.description.includes('更新到最新狀態'));
});

test('mutation copy differs by surface', () => {
  const compass = buildMutationCopy('compass');
  const future = buildMutationCopy('future');
  assert.notEqual(compass.acceptingLabel, future.acceptingLabel);
});

test('duplicate title detector normalizes casing and whitespace', () => {
  assert.equal(isSharedFutureDuplicateTitle('  一起存旅行基金 ', ['一起存旅行基金']), true);
  assert.equal(isSharedFutureDuplicateTitle('一起存旅行基金', ['一起存旅行基金 ', '別的']), true);
  assert.equal(isSharedFutureDuplicateTitle('不同', ['一起存旅行基金']), false);
});

