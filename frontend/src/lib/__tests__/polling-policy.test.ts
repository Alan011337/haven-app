import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildAdaptiveRefetchInterval,
  getAdaptiveIntervalMs,
} from '../polling-policy';

function withWindowEnv(
  options: {
    hidden: boolean;
    online: boolean;
  },
  run: () => void,
): void {
  const originalWindowDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'window');
  const originalDocumentDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'document');
  const originalNavigatorDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'navigator');

  Object.defineProperty(globalThis, 'window', {
    configurable: true,
    value: {},
  });
  Object.defineProperty(globalThis, 'document', {
    configurable: true,
    value: { hidden: options.hidden },
  });
  Object.defineProperty(globalThis, 'navigator', {
    configurable: true,
    value: { onLine: options.online },
  });

  try {
    run();
  } finally {
    if (originalWindowDescriptor) {
      Object.defineProperty(globalThis, 'window', originalWindowDescriptor);
    } else {
      delete (globalThis as { window?: unknown }).window;
    }
    if (originalDocumentDescriptor) {
      Object.defineProperty(globalThis, 'document', originalDocumentDescriptor);
    } else {
      delete (globalThis as { document?: unknown }).document;
    }
    if (originalNavigatorDescriptor) {
      Object.defineProperty(globalThis, 'navigator', originalNavigatorDescriptor);
    } else {
      delete (globalThis as { navigator?: unknown }).navigator;
    }
  }
}

test('getAdaptiveIntervalMs returns false when offline and disableWhenOffline=true', () => {
  withWindowEnv({ hidden: false, online: false }, () => {
    assert.equal(getAdaptiveIntervalMs(5000), false);
  });
});

test('getAdaptiveIntervalMs applies hidden multiplier when tab hidden', () => {
  withWindowEnv({ hidden: true, online: true }, () => {
    assert.equal(getAdaptiveIntervalMs(2000, { hiddenMultiplier: 4 }), 8000);
  });
});

test('buildAdaptiveRefetchInterval returns callable interval provider', () => {
  withWindowEnv({ hidden: false, online: true }, () => {
    const refetchInterval = buildAdaptiveRefetchInterval(3000);
    assert.equal(typeof refetchInterval, 'function');
    assert.equal(refetchInterval(), 3000);
  });
});
