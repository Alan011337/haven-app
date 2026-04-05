import test from 'node:test';
import assert from 'node:assert/strict';

import {
  getHomeDailyDepthPresentation,
  HOME_DAILY_DEPTH_OPTIONS,
} from '../home-daily-depth.ts';

test('exposes the calm Home-only depth labels in level order', () => {
  assert.deepEqual(
    HOME_DAILY_DEPTH_OPTIONS.map((option) => option.label),
    ['輕鬆聊', '靠近一點', '深入內心'],
  );
});

test('returns the correct Home presentation for each depth level', () => {
  assert.deepEqual(getHomeDailyDepthPresentation(1), {
    level: 1,
    label: '輕鬆聊',
    description: '先用比較不費力的問題，慢慢進到今晚。',
    ctaLabel: '抽一張適合「輕鬆聊」的題目',
  });
  assert.deepEqual(getHomeDailyDepthPresentation(2), {
    level: 2,
    label: '靠近一點',
    description: '聊近況，也聊到彼此真正想被理解的地方。',
    ctaLabel: '抽一張適合「靠近一點」的題目',
  });
  assert.deepEqual(getHomeDailyDepthPresentation(3), {
    level: 3,
    label: '深入內心',
    description: '留給今晚願意更坦白、更靠近內在的時刻。',
    ctaLabel: '抽一張適合「深入內心」的題目',
  });
});

test('returns null for unsupported or absent Home depth levels', () => {
  assert.equal(getHomeDailyDepthPresentation(null), null);
  assert.equal(getHomeDailyDepthPresentation(undefined), null);
});
