import test from 'node:test';
import assert from 'node:assert/strict';
import {
  classifyDisconnectReason,
  computeReconnectDelayMs,
  resolveReconnectCap,
} from '../socket-reconnect-policy.ts';

test('classifyDisconnectReason buckets auth close code 1008', () => {
  assert.equal(classifyDisconnectReason(1008), 'auth_or_policy');
  assert.equal(classifyDisconnectReason(1011), 'transport_or_server');
});

test('resolveReconnectCap halves cap for server pressure close codes', () => {
  assert.equal(resolveReconnectCap(8, 1011), 4);
  assert.equal(resolveReconnectCap(5, 1012), 3);
  assert.equal(resolveReconnectCap(8, 1000), 8);
});

test('computeReconnectDelayMs applies bounded jitter', () => {
  const delay = computeReconnectDelayMs({
    retryCount: 2,
    closeCode: 1000,
    randomFn: () => 1,
    jitterRatio: 0.2,
    baseDelayMs: 1000,
    maxDelayMs: 15000,
  });
  // base exponential delay=4000, with max jitter 20%=800
  assert.equal(delay, 4800);
});

test('computeReconnectDelayMs clamps to server pressure floor and ceiling', () => {
  const lowRetry = computeReconnectDelayMs({
    retryCount: 0,
    closeCode: 1011,
    randomFn: () => 0,
    baseDelayMs: 300,
    maxDelayMs: 1000,
  });
  assert.equal(lowRetry, 2000);

  const highRetry = computeReconnectDelayMs({
    retryCount: 10,
    closeCode: 1013,
    randomFn: () => 0,
    baseDelayMs: 5000,
    maxDelayMs: 60000,
  });
  assert.equal(highRetry, 30000);
});
