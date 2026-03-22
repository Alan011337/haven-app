import assert from 'node:assert/strict';
import test from 'node:test';

import {
  resolveLoopbackFriendlyApiUrl,
  resolveLoopbackFriendlyUrl,
} from '../loopback-origin.ts';

test('resolveLoopbackFriendlyApiUrl rewrites localhost api host to match 127.0.0.1 frontend origin', () => {
  const resolved = resolveLoopbackFriendlyApiUrl(
    'http://localhost:8000/api',
    'http://127.0.0.1:3000',
  );

  assert.equal(resolved, 'http://127.0.0.1:8000/api');
});

test('resolveLoopbackFriendlyUrl rewrites 127.0.0.1 websocket host to match localhost frontend origin', () => {
  const resolved = resolveLoopbackFriendlyUrl(
    'ws://127.0.0.1:8000/ws',
    'http://localhost:3000',
  );

  assert.equal(resolved, 'ws://localhost:8000/ws');
});

test('resolveLoopbackFriendlyApiUrl leaves non-loopback hosts unchanged', () => {
  const resolved = resolveLoopbackFriendlyApiUrl(
    'https://haven-api-prod.fly.dev/api',
    'http://127.0.0.1:3000',
  );

  assert.equal(resolved, 'https://haven-api-prod.fly.dev/api');
});

