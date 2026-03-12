import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildUpstreamUrl,
  MAX_INTERNAL_UPSTREAM_REDIRECTS,
  redactProxyPath,
  resolveInternalUpstreamRedirectUrl,
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

test('resolveInternalUpstreamRedirectUrl normalizes same-host redirect back onto target protocol', () => {
  const redirect = resolveInternalUpstreamRedirectUrl({
    currentUpstreamUrl: 'https://haven-api-prod.fly.dev/api/blueprint',
    location: 'http://haven-api-prod.fly.dev/api/blueprint/',
    status: 307,
    targetBase: new URL('https://haven-api-prod.fly.dev/api'),
  });

  assert.equal(redirect, 'https://haven-api-prod.fly.dev/api/blueprint/');
});

test('resolveInternalUpstreamRedirectUrl ignores redirects outside the proxy base path', () => {
  const redirect = resolveInternalUpstreamRedirectUrl({
    currentUpstreamUrl: 'https://haven-api-prod.fly.dev/api/blueprint',
    location: 'https://haven-api-prod.fly.dev/login',
    status: 307,
    targetBase: new URL('https://haven-api-prod.fly.dev/api'),
  });

  assert.equal(redirect, null);
});

test('resolveInternalUpstreamRedirectUrl only follows preserved-method redirects', () => {
  assert.equal(
    resolveInternalUpstreamRedirectUrl({
      currentUpstreamUrl: 'https://haven-api-prod.fly.dev/api/blueprint',
      location: '/api/blueprint/',
      status: 302,
      targetBase: new URL('https://haven-api-prod.fly.dev/api'),
    }),
    null,
  );
  assert.equal(MAX_INTERNAL_UPSTREAM_REDIRECTS, 2);
});
