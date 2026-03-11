import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildUpstreamUrl,
  redactProxyPath,
  shouldLogSlowProxy,
  SLOW_API_PROXY_THRESHOLD_MS,
} from '../upstream-proxy-utils.ts';

test('buildUpstreamUrl appends API segments and query string', () => {
  const upstream = buildUpstreamUrl(
    new URL('https://haven-api-prod.fly.dev/api'),
    ['users', 'partner-status'],
    '?tab=mine',
  );
  assert.equal(upstream, 'https://haven-api-prod.fly.dev/api/users/partner-status?tab=mine');
});

test('redactProxyPath masks UUID-like identifiers', () => {
  assert.equal(
    redactProxyPath('/api/journals/550e8400-e29b-41d4-a716-446655440000'),
    '/api/journals/:id',
  );
});

test('shouldLogSlowProxy only flags slow successful api responses', () => {
  assert.equal(shouldLogSlowProxy('api', 200, SLOW_API_PROXY_THRESHOLD_MS), true);
  assert.equal(shouldLogSlowProxy('api', 401, SLOW_API_PROXY_THRESHOLD_MS + 250), true);
  assert.equal(shouldLogSlowProxy('api', 500, SLOW_API_PROXY_THRESHOLD_MS + 250), false);
  assert.equal(shouldLogSlowProxy('health', 200, SLOW_API_PROXY_THRESHOLD_MS + 250), false);
  assert.equal(shouldLogSlowProxy('api', 200, SLOW_API_PROXY_THRESHOLD_MS - 1), false);
});
