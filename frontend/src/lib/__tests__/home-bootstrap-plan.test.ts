import test from 'node:test';
import assert from 'node:assert/strict';
import { buildHomeBootstrapPlan } from '../home-bootstrap-plan.ts';
import {
  HOME_OPTIONAL_DATA_TIMEOUT_MS,
  HOME_STATUS_TIMEOUT_MS,
  HOME_TIMELINE_TIMEOUT_MS,
} from '../home-performance.ts';
import { resolveHomeTimelineStage } from '../home-timeline-state.ts';

test('mine tab keeps partner data and secondary cards off until non-critical stage', () => {
  assert.deepEqual(buildHomeBootstrapPlan('mine', false), {
    loadMineJournals: true,
    loadPartnerJournals: false,
    loadHeaderEnhancements: false,
    loadMineSecondaryCards: false,
  });
});

test('partner tab only loads partner journals on first paint', () => {
  assert.deepEqual(buildHomeBootstrapPlan('partner', false), {
    loadMineJournals: false,
    loadPartnerJournals: true,
    loadHeaderEnhancements: false,
    loadMineSecondaryCards: false,
  });
});

test('non-critical stage unlocks header data and mine secondary cards', () => {
  assert.deepEqual(buildHomeBootstrapPlan('mine', true), {
    loadMineJournals: true,
    loadPartnerJournals: false,
    loadHeaderEnhancements: true,
    loadMineSecondaryCards: true,
  });
});

test('home optional data timeout stays short enough for fail-open cards', () => {
  assert.equal(HOME_OPTIONAL_DATA_TIMEOUT_MS, 3500);
});

test('home status timeout stays shorter than timeline timeout', () => {
  assert.equal(HOME_STATUS_TIMEOUT_MS, 4000);
});

test('home timeline timeout stays below default global request timeout', () => {
  assert.equal(HOME_TIMELINE_TIMEOUT_MS, 6000);
});

test('timeline state prefers ready data over deferred error state', () => {
  assert.equal(
    resolveHomeTimelineStage({
      mounted: true,
      loading: false,
      unavailable: true,
      itemCount: 2,
    }),
    'ready',
  );
});

test('timeline state falls back to deferred when first load times out', () => {
  assert.equal(
    resolveHomeTimelineStage({
      mounted: true,
      loading: false,
      unavailable: true,
      itemCount: 0,
    }),
    'deferred',
  );
});
