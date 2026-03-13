import test from 'node:test';
import assert from 'node:assert/strict';
import {
  HOME_APPRECIATION_HISTORY_QUERY_KEY_PREFIX,
  buildHomeAppreciationHistoryQueryKey,
  getHomeAppreciationWeekRange,
} from '../home-appreciation-history.ts';

test('home appreciation history key keeps stable prefix and week bounds', () => {
  assert.deepEqual(
    buildHomeAppreciationHistoryQueryKey('2026-03-09', '2026-03-15'),
    [...HOME_APPRECIATION_HISTORY_QUERY_KEY_PREFIX, '2026-03-09', '2026-03-15'],
  );
});

test('week range starts on Monday and ends on Sunday', () => {
  assert.deepEqual(
    getHomeAppreciationWeekRange(new Date('2026-03-11T10:00:00+08:00')),
    {
      from: '2026-03-09',
      to: '2026-03-15',
    },
  );
});
