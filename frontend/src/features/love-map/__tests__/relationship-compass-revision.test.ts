import assert from 'node:assert/strict';
import test from 'node:test';

import {
  COMPASS_FIELD_KEYS,
  formatCompassChangedAt,
  summarizeCompassChange,
} from '../relationship-compass-revision.ts';

// Minimal row factory so each test states only the fields it cares about.
// Field shape matches LoveMapRelationshipCompassChangePublic on the wire.
type FieldChange = {
  key: string;
  label: string;
  change_kind: 'added' | 'updated' | 'cleared';
  before_text: string | null;
  after_text: string | null;
};

function buildChange(fields: FieldChange[]) {
  return {
    id: 'change-1',
    changed_at: '2026-04-22T04:05:06Z',
    changed_by_name: 'Alice',
    fields,
    revision_note: null,
  };
}

test('summarizeCompassChange: all three added → 第一次寫下 身份、故事、未來', () => {
  const change = buildChange([
    { key: 'identity_statement', label: '身份', change_kind: 'added', before_text: null, after_text: 'A' },
    { key: 'story_anchor', label: '故事', change_kind: 'added', before_text: null, after_text: 'B' },
    { key: 'future_direction', label: '未來', change_kind: 'added', before_text: null, after_text: 'C' },
  ]);
  assert.equal(summarizeCompassChange(change), '第一次寫下 身份、故事、未來');
});

test('summarizeCompassChange: only story updated → 調整了 故事', () => {
  const change = buildChange([
    { key: 'story_anchor', label: '故事', change_kind: 'updated', before_text: 'X', after_text: 'Y' },
  ]);
  assert.equal(summarizeCompassChange(change), '調整了 故事');
});

test('summarizeCompassChange: story + future cleared → 暫時清空 故事、未來', () => {
  const change = buildChange([
    { key: 'story_anchor', label: '故事', change_kind: 'cleared', before_text: 'X', after_text: null },
    { key: 'future_direction', label: '未來', change_kind: 'cleared', before_text: 'Y', after_text: null },
  ]);
  assert.equal(summarizeCompassChange(change), '暫時清空 故事、未來');
});

test('summarizeCompassChange: mixed change kinds collapse to neutral 調整了', () => {
  const change = buildChange([
    { key: 'identity_statement', label: '身份', change_kind: 'added', before_text: null, after_text: 'A' },
    { key: 'story_anchor', label: '故事', change_kind: 'updated', before_text: 'X', after_text: 'Y' },
    { key: 'future_direction', label: '未來', change_kind: 'cleared', before_text: 'Z', after_text: null },
  ]);
  assert.equal(summarizeCompassChange(change), '調整了 身份、故事、未來');
});

test('summarizeCompassChange: empty fields array → 保留了原本的內容', () => {
  const change = buildChange([]);
  assert.equal(summarizeCompassChange(change), '保留了原本的內容');
});

test('summarizeCompassChange: server sends fields out of order → sorted identity→story→future', () => {
  const change = buildChange([
    { key: 'future_direction', label: '未來', change_kind: 'updated', before_text: 'a', after_text: 'b' },
    { key: 'identity_statement', label: '身份', change_kind: 'updated', before_text: 'c', after_text: 'd' },
    { key: 'story_anchor', label: '故事', change_kind: 'updated', before_text: 'e', after_text: 'f' },
  ]);
  assert.equal(summarizeCompassChange(change), '調整了 身份、故事、未來');
});

test('formatCompassChangedAt: valid ISO → YYYY-MM-DD', () => {
  const out = formatCompassChangedAt('2026-04-22T04:05:06Z');
  // Timezone-sensitive but stable in local env; assert shape + year prefix
  // rather than the exact date so the test does not flake across zones.
  assert.match(out, /^\d{4}-\d{2}-\d{2}$/);
  assert.ok(out.startsWith('2026-'));
});

test('formatCompassChangedAt: null → em-dash', () => {
  assert.equal(formatCompassChangedAt(null), '—');
});

test('formatCompassChangedAt: unparseable string → em-dash', () => {
  assert.equal(formatCompassChangedAt('not-a-date'), '—');
});

test('COMPASS_FIELD_KEYS: canonical order stays identity→story→future', () => {
  assert.deepEqual([...COMPASS_FIELD_KEYS], [
    'identity_statement',
    'story_anchor',
    'future_direction',
  ]);
});
