import test from 'node:test';
import assert from 'node:assert/strict';
import { parseSharedFutureNotes } from '../shared-future-read-model.ts';

test('returns empty read model when notes are blank', () => {
  assert.deepEqual(parseSharedFutureNotes(' \n '), {
    baseNote: null,
    nextSteps: [],
    cadences: [],
    hasStructuredRefinements: false,
  });
});

test('keeps plain notes untouched when no structured refinement lines exist', () => {
  assert.deepEqual(parseSharedFutureNotes('先把那一晚留給散步和晚餐。'), {
    baseNote: '先把那一晚留給散步和晚餐。',
    nextSteps: [],
    cadences: [],
    hasStructuredRefinements: false,
  });
});

test('splits base note, next steps, and cadence lines while preserving order', () => {
  assert.deepEqual(
    parseSharedFutureNotes(
      [
        '不安排社交，只留給我們兩個人。',
        '',
        '下一步：先把每月第二個週五晚上固定留給彼此。',
        '節奏：每月第二個週五晚上留給彼此。',
        '下一步：提前一週決定這晚想怎麼過。',
      ].join('\n'),
    ),
    {
      baseNote: '不安排社交，只留給我們兩個人。',
      nextSteps: ['先把每月第二個週五晚上固定留給彼此。', '提前一週決定這晚想怎麼過。'],
      cadences: ['每月第二個週五晚上留給彼此。'],
      hasStructuredRefinements: true,
    },
  );
});

test('keeps malformed prefixed lines in the base note so content is not dropped', () => {
  assert.deepEqual(
    parseSharedFutureNotes(['先保留一些描述。', '下一步：', '節奏：   '].join('\n')),
    {
      baseNote: ['先保留一些描述。', '下一步：', '節奏：'].join('\n'),
      nextSteps: [],
      cadences: [],
      hasStructuredRefinements: false,
    },
  );
});
