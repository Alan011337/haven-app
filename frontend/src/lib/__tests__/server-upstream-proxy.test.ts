import test from 'node:test';
import assert from 'node:assert/strict';
import { buildUpstreamUrl, redactProxyPath } from '../upstream-proxy-utils.ts';

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
