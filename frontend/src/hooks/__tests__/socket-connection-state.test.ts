import test from 'node:test';
import assert from 'node:assert/strict';

import {
  INITIAL_SOCKET_STATE,
  transitionSocketConnectionState,
} from '../socket-connection-state';

test('starts in idle', () => {
  assert.equal(INITIAL_SOCKET_STATE, 'idle');
});

test('transitions through connect and reconnect path deterministically', () => {
  const connecting = transitionSocketConnectionState('idle', 'connect_start');
  const connected = transitionSocketConnectionState(connecting, 'connect_open');
  const reconnecting = transitionSocketConnectionState(connected, 'reconnect_scheduled');
  assert.equal(connecting, 'connecting');
  assert.equal(connected, 'connected');
  assert.equal(reconnecting, 'reconnecting');
});

test('fallback state is sticky until disposed', () => {
  const fallback = transitionSocketConnectionState('reconnecting', 'fallback_enabled');
  const stillFallback = transitionSocketConnectionState(fallback, 'reconnect_scheduled');
  const idle = transitionSocketConnectionState(stillFallback, 'disposed');
  assert.equal(fallback, 'fallback');
  assert.equal(stillFallback, 'fallback');
  assert.equal(idle, 'idle');
});
