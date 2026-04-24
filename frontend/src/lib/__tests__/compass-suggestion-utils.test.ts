import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import {
  buildCompassSuggestionEvidenceArtifactHref,
  compassFieldValuesEqual,
  countCompassFieldDifferences,
  normalizeCompassFieldValue,
} from '../compass-suggestion-utils.ts';

describe('compass-suggestion-utils', () => {
  it('normalizes empty and whitespace', () => {
    assert.equal(normalizeCompassFieldValue('  hi  '), 'hi');
    assert.equal(normalizeCompassFieldValue(null), '');
  });

  it('compares trimmed equality', () => {
    assert.equal(compassFieldValuesEqual(' a ', 'a'), true);
    assert.equal(compassFieldValuesEqual('a', 'b'), false);
  });

  it('counts differing fields', () => {
    const saved = {
      identity_statement: 'a',
      story_anchor: 'b',
      future_direction: 'c',
      updated_by_name: null,
      updated_at: null,
    };
    assert.equal(
      countCompassFieldDifferences(saved, {
        identity_statement: 'a',
        story_anchor: 'x',
        future_direction: 'c',
      }),
      1,
    );
    assert.equal(
      countCompassFieldDifferences(null, {
        identity_statement: 'a',
        story_anchor: null,
        future_direction: null,
      }),
      1,
    );
  });

  it('builds journal href only for UUID source_id', () => {
    const id = 'a0000000-0000-4000-8000-000000000001';
    assert.equal(
      buildCompassSuggestionEvidenceArtifactHref({ source_kind: 'journal', source_id: id }),
      `/journal/${encodeURIComponent(id)}`,
    );
    assert.equal(
      buildCompassSuggestionEvidenceArtifactHref({ source_kind: 'journal', source_id: 'not-a-uuid' }),
      null,
    );
    assert.equal(
      buildCompassSuggestionEvidenceArtifactHref({ source_kind: 'appreciation', source_id: id }),
      null,
    );
  });
});
