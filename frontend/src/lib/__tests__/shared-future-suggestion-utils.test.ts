import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildSavedSharedFuturePreviewTitles,
  filterSharedFutureEvidence,
  sharedFutureEvidenceKindLabel,
} from '../shared-future-suggestion-utils.ts';

test('shared-future-suggestion-utils: filters evidence to allowed pair-visible kinds', () => {
    const filtered = filterSharedFutureEvidence([
      { source_kind: 'card', label: '共同卡片', excerpt: 'A' },
      { source_kind: 'appreciation', label: '感恩', excerpt: 'B' },
      { source_kind: 'journal', label: '你的日記', excerpt: 'C' },
      { source_kind: '  CARD  ', label: '共同卡片 2', excerpt: 'D' },
    ]);
    assert.deepEqual(
      filtered.map((x) => x.source_kind.trim().toLowerCase()),
      ['card', 'appreciation', 'card'],
    );
});

test('shared-future-suggestion-utils: builds saved titles preview and more count', () => {
    const out = buildSavedSharedFuturePreviewTitles(
      [
        { title: 'A' },
        { title: 'B' },
        { title: 'C' },
        { title: 'D' },
      ],
      3,
    );
    assert.deepEqual(out.titles, ['A', 'B', 'C']);
    assert.equal(out.moreCount, 1);
});

test('shared-future-suggestion-utils: maps evidence kinds to product labels', () => {
  assert.equal(sharedFutureEvidenceKindLabel('card'), '共同卡片');
  assert.equal(sharedFutureEvidenceKindLabel('appreciation'), '感恩');
  assert.equal(sharedFutureEvidenceKindLabel('story_time_capsule'), 'Story');
});

