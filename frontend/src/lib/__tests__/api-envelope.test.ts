import test from 'node:test';
import assert from 'node:assert/strict';
import {
  isApiEnvelopePayload,
  normalizeApiEnvelopeError,
  unwrapApiEnvelopeData,
} from '../api-envelope.ts';

test('isApiEnvelopePayload accepts canonical envelope shape', () => {
  const payload = {
    data: { ok: true },
    meta: { request_id: 'req-1' },
    error: null,
  };
  assert.equal(isApiEnvelopePayload(payload), true);
});

test('unwrapApiEnvelopeData returns raw payload for non-envelope input', () => {
  const payload = { foo: 'bar' };
  assert.deepEqual(unwrapApiEnvelopeData(payload), payload);
});

test('normalizeApiEnvelopeError maps code/message/details from envelope', () => {
  const payload = {
    data: null,
    meta: { request_id: 'req-2' },
    error: {
      code: 'forbidden',
      message: 'Forbidden',
      details: { detail: 'Denied' },
    },
  };
  assert.deepEqual(normalizeApiEnvelopeError(payload), {
    code: 'forbidden',
    message: 'Forbidden',
    detail: { detail: 'Denied' },
  });
});
