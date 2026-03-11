import test from 'node:test';
import assert from 'node:assert/strict';
import { buildHomeBootstrapPlan } from '../home-bootstrap-plan.ts';

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
