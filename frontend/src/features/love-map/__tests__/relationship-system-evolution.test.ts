import assert from 'node:assert/strict';
import test from 'node:test';

import type {
  LoveMapRelationshipCompassChangePublic,
  LoveMapRepairAgreementChangePublic,
} from '../../../services/api-client.ts';

import { buildRelationshipEvolutionTimeline } from '../relationship-system-evolution.ts';

const compassField = (
  key: LoveMapRelationshipCompassChangePublic['fields'][number]['key'],
  label: string,
  change_kind: 'added' | 'updated' | 'cleared' = 'updated',
): LoveMapRelationshipCompassChangePublic['fields'][number] => ({
  key,
  label,
  change_kind,
  before_text: null,
  after_text: 'x',
});

const repairField = (): LoveMapRepairAgreementChangePublic['fields'][number] => ({
  key: 'commitment',
  label: '約定',
  change_kind: 'updated',
  before_text: null,
  after_text: 'y',
});

test('buildRelationshipEvolutionTimeline returns empty when both histories are empty', () => {
  assert.deepEqual(
    buildRelationshipEvolutionTimeline({ compassHistory: [], repairHistory: [] }),
    [],
  );
  assert.deepEqual(
    buildRelationshipEvolutionTimeline({ compassHistory: undefined, repairHistory: null }),
    [],
  );
});

test('buildRelationshipEvolutionTimeline maps compass rows with labels and hrefs', () => {
  const compass: LoveMapRelationshipCompassChangePublic[] = [
    {
      id: 'cc-1',
      changed_at: '2026-04-01T12:00:00Z',
      changed_by_name: 'Pat',
      origin_kind: 'accepted_suggestion',
      fields: [compassField('identity_statement', '身份')],
      revision_note: '  trimmed  ',
    },
  ];
  const [row] = buildRelationshipEvolutionTimeline({ compassHistory: compass, repairHistory: [] });
  assert.equal(row?.domain, 'identity');
  assert.equal(row?.sourceLabel, 'Haven 建議 · 已接受');
  assert.equal(row?.summary, '調整了 身份');
  assert.equal(row?.actorLabel, 'Pat');
  assert.equal(row?.sourceHref, '#relationship-compass-history-cc-1');
  assert.equal(row?.sectionHref, '#identity');
  assert.equal(row?.revisionNote, 'trimmed');
  assert.equal(row?.testId, 'relationship-evolution-event-compass-cc-1');
});

test('buildRelationshipEvolutionTimeline maps manual compass origin', () => {
  const [row] = buildRelationshipEvolutionTimeline({
    compassHistory: [
      {
        id: 'm1',
        changed_at: '2026-04-02T12:00:00Z',
        changed_by_name: null,
        origin_kind: 'manual_edit',
        fields: [],
        revision_note: null,
      },
    ],
    repairHistory: [],
  });
  assert.equal(row?.sourceLabel, '手動更新');
  assert.equal(row?.actorLabel, '未具名使用者');
  assert.equal(row?.summary, '保留了原本的內容');
});

test('buildRelationshipEvolutionTimeline maps repair rows and repair origin labels', () => {
  const repair: LoveMapRepairAgreementChangePublic[] = [
    {
      id: 'rr-1',
      changed_at: '2026-04-03T12:00:00Z',
      changed_by_name: 'Sam',
      origin_kind: 'post_mediation_carry_forward',
      source_outcome_capture_id: null,
      source_captured_by_name: null,
      source_captured_at: null,
      fields: [repairField(), repairField()],
      revision_note: null,
    },
    {
      id: 'rr-2',
      changed_at: '2026-04-04T12:00:00Z',
      changed_by_name: 'Bo',
      origin_kind: 'manual_edit',
      source_outcome_capture_id: null,
      source_captured_by_name: null,
      source_captured_at: null,
      fields: [repairField()],
      revision_note: null,
    },
  ];
  const rows = buildRelationshipEvolutionTimeline({ compassHistory: [], repairHistory: repair });
  assert.equal(rows.length, 2);
  assert.equal(rows[0]?.id, 'repair:rr-2');
  assert.equal(rows[0]?.sourceLabel, '手動微調');
  assert.equal(rows[0]?.summary, '在 Heart 裡重新調整了 1 個欄位。');
  assert.equal(rows[1]?.id, 'repair:rr-1');
  assert.equal(rows[1]?.sourceLabel, '修復帶回');
  assert.equal(rows[1]?.summary, '把 2 個欄位 的修復重點正式帶回 Heart。');
  assert.equal(rows[1]?.sourceHref, '#relationship-repair-agreement-history-rr-1');
  assert.equal(rows[1]?.sectionHref, '#heart');
});

test('buildRelationshipEvolutionTimeline sorts by changed_at desc, nulls last, tie-break by id', () => {
  const compass: LoveMapRelationshipCompassChangePublic[] = [
    {
      id: 'z',
      changed_at: '2026-01-02T00:00:00Z',
      changed_by_name: null,
      origin_kind: 'manual_edit',
      fields: [compassField('identity_statement', '身份')],
      revision_note: null,
    },
    {
      id: 'a',
      changed_at: '2026-01-02T00:00:00Z',
      changed_by_name: null,
      origin_kind: 'manual_edit',
      fields: [compassField('identity_statement', '身份')],
      revision_note: null,
    },
    {
      id: 'old',
      changed_at: null,
      changed_by_name: null,
      origin_kind: 'manual_edit',
      fields: [compassField('identity_statement', '身份')],
      revision_note: null,
    },
  ];
  const repair: LoveMapRepairAgreementChangePublic[] = [
    {
      id: 'mid',
      changed_at: '2026-01-01T12:00:00Z',
      changed_by_name: null,
      origin_kind: 'manual_edit',
      source_outcome_capture_id: null,
      source_captured_by_name: null,
      source_captured_at: null,
      fields: [repairField()],
      revision_note: null,
    },
  ];
  const ids = buildRelationshipEvolutionTimeline({
    compassHistory: compass,
    repairHistory: repair,
  }).map((e) => e.id);
  assert.deepEqual(ids, ['compass:a', 'compass:z', 'repair:mid', 'compass:old']);
});

test('buildRelationshipEvolutionTimeline caps at maxEvents (default 6, max 8)', () => {
  const compass = Array.from({ length: 5 }, (_, i) => ({
    id: `c${i}`,
    changed_at: `2026-01-0${i + 1}T00:00:00Z`,
    changed_by_name: null,
    origin_kind: 'manual_edit' as const,
    fields: [compassField('identity_statement', '身份')],
    revision_note: null,
  }));
  const repair = Array.from({ length: 5 }, (_, i) => ({
    id: `r${i}`,
    changed_at: `2026-02-0${i + 1}T00:00:00Z`,
    changed_by_name: null,
    origin_kind: 'manual_edit' as const,
    source_outcome_capture_id: null,
    source_captured_by_name: null,
    source_captured_at: null,
    fields: [repairField()],
    revision_note: null,
  }));
  assert.equal(
    buildRelationshipEvolutionTimeline({ compassHistory: compass, repairHistory: repair }).length,
    6,
  );
  assert.equal(
    buildRelationshipEvolutionTimeline({
      compassHistory: compass,
      repairHistory: repair,
      maxEvents: 2,
    }).length,
    2,
  );
  assert.equal(
    buildRelationshipEvolutionTimeline({
      compassHistory: compass,
      repairHistory: repair,
      maxEvents: 99,
    }).length,
    8,
  );
});
