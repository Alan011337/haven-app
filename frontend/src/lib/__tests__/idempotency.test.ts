import test from 'node:test';
import assert from 'node:assert/strict';
import { buildIdempotencyHeaders, normalizeIdempotencyKey } from '../idempotency.ts';

test('normalizeIdempotencyKey rejects short or empty values', () => {
  assert.equal(normalizeIdempotencyKey(''), null);
  assert.equal(normalizeIdempotencyKey('abc123'), null);
  assert.equal(normalizeIdempotencyKey('   '), null);
});

test('normalizeIdempotencyKey trims and preserves valid values', () => {
  assert.equal(normalizeIdempotencyKey('  idem-12345  '), 'idem-12345');
});

test('buildIdempotencyHeaders returns undefined for invalid keys', () => {
  assert.equal(buildIdempotencyHeaders('short'), undefined);
});

test('buildIdempotencyHeaders returns Idempotency-Key header for valid key', () => {
  assert.deepEqual(buildIdempotencyHeaders('idem-key-1234'), {
    'Idempotency-Key': 'idem-key-1234',
  });
});
