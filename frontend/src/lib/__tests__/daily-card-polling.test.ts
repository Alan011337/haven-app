import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DAILY_CARD_IDLE_POLL_MS,
  DAILY_CARD_WAITING_PARTNER_POLL_MS,
  resolveDailyCardPollingIntervalMs,
} from '../daily-card-polling.ts';

test('resolveDailyCardPollingIntervalMs polls less aggressively when there is no active card yet', () => {
  assert.equal(resolveDailyCardPollingIntervalMs(null), DAILY_CARD_IDLE_POLL_MS);
  assert.equal(resolveDailyCardPollingIntervalMs({ state: 'IDLE', card: null }), DAILY_CARD_IDLE_POLL_MS);
});

test('resolveDailyCardPollingIntervalMs keeps waiting-partner sync active with a separate interval', () => {
  assert.equal(
    resolveDailyCardPollingIntervalMs({ state: 'WAITING_PARTNER', card: { id: 'card-1' } }),
    DAILY_CARD_WAITING_PARTNER_POLL_MS,
  );
});

test('resolveDailyCardPollingIntervalMs disables polling while the user is actively answering or after completion', () => {
  assert.equal(
    resolveDailyCardPollingIntervalMs({ state: 'IDLE', card: { id: 'card-1' } }),
    null,
  );
  assert.equal(
    resolveDailyCardPollingIntervalMs({ state: 'PARTNER_STARTED', card: { id: 'card-1' } }),
    null,
  );
  assert.equal(
    resolveDailyCardPollingIntervalMs({ state: 'COMPLETED', card: { id: 'card-1' } }),
    null,
  );
});
