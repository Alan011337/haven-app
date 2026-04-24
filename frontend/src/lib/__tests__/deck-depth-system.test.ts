import test from 'node:test';
import assert from 'node:assert/strict';

import {
  filterDecksByDepth,
  getDeckDepthFilterCopy,
  parseDeckDepthParam,
} from '../deck-depth-system.ts';
import type { DeckMeta } from '../deck-meta.ts';
import { DEPTH_OPTIONS, getDepthPresentation } from '../depth-level.ts';

test('maps shared depth labels to human-centered ritual language', () => {
  assert.deepEqual(
    DEPTH_OPTIONS.map((option) => option.label),
    ['輕鬆聊', '靠近一點', '深入內心'],
  );
  assert.equal(getDepthPresentation(1).label, '輕鬆聊');
  assert.equal(getDepthPresentation(2).label, '靠近一點');
  assert.equal(getDepthPresentation(3).label, '深入內心');
});

test('parses valid deck depth query params and ignores unsupported values', () => {
  assert.equal(parseDeckDepthParam('1'), 1);
  assert.equal(parseDeckDepthParam('2'), 2);
  assert.equal(parseDeckDepthParam('3'), 3);
  assert.equal(parseDeckDepthParam('0'), null);
  assert.equal(parseDeckDepthParam('4'), null);
  assert.equal(parseDeckDepthParam('深入內心'), null);
  assert.equal(parseDeckDepthParam(null), null);
  assert.equal(parseDeckDepthParam(undefined), null);
});

test('filters deck cards by deck-level depth identity without mutating input', () => {
  const deckCards = [
    { deck: { depthIdentity: 1 } as DeckMeta, marker: 'light' },
    { deck: { depthIdentity: 2 } as DeckMeta, marker: 'closer' },
    { deck: { depthIdentity: 3 } as DeckMeta, marker: 'deep' },
    { deck: { depthIdentity: 1 } as DeckMeta, marker: 'second-light' },
  ];
  const originalOrder = deckCards.map((item) => item.marker);

  const lightDecks = filterDecksByDepth(deckCards, 1);
  const closerDecks = filterDecksByDepth(deckCards, 2);
  const deepDecks = filterDecksByDepth(deckCards, 3);
  const allDecks = filterDecksByDepth(deckCards, null);

  assert.ok(lightDecks.length > 0);
  assert.ok(closerDecks.length > 0);
  assert.ok(deepDecks.length > 0);
  assert.equal(lightDecks.every((item) => item.deck.depthIdentity === 1), true);
  assert.equal(closerDecks.every((item) => item.deck.depthIdentity === 2), true);
  assert.equal(deepDecks.every((item) => item.deck.depthIdentity === 3), true);
  assert.deepEqual(deckCards.map((item) => item.marker), originalOrder);
  assert.notEqual(allDecks, deckCards);
  assert.deepEqual(
    allDecks.map((item) => item.marker),
    originalOrder,
  );
});

test('returns calm depth-specific copy only when a depth is active', () => {
  assert.equal(getDeckDepthFilterCopy(null), null);
  assert.match(getDeckDepthFilterCopy(1)?.title ?? '', /輕/);
  assert.match(getDeckDepthFilterCopy(2)?.title ?? '', /靠近/);
  assert.match(getDeckDepthFilterCopy(3)?.title ?? '', /深入/);
  assert.match(getDeckDepthFilterCopy(3)?.emptyDescription ?? '', /清除篩選/);
});
