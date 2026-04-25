/**
 * Pure view-model for the Relationship System evolution timeline on /love-map.
 * Merges saved Compass history + Repair Agreement history only (no pending suggestions).
 */

import { summarizeCompassChange } from '#haven/relationship-compass-revision';
import type {
  LoveMapRelationshipCompassChangePublic,
  LoveMapRepairAgreementChangePublic,
} from '@/services/api-client';

export type RelationshipEvolutionDomain = 'identity' | 'heart';

export type RelationshipEvolutionEvent = {
  /** Stable unique key for React lists (domain-prefixed). */
  id: string;
  domain: RelationshipEvolutionDomain;
  domainLabel: string;
  title: string;
  summary: string;
  actorLabel: string;
  occurredAt: string | null;
  sourceLabel: string;
  revisionNote: string | null;
  /** Deep link to the history row anchor. */
  sourceHref: string;
  /** Section anchor for scroll context (#identity | #heart). */
  sectionHref: string;
  testId: string;
};

function timeValue(iso: string | null): number {
  if (!iso) return Number.NEGATIVE_INFINITY;
  const t = Date.parse(iso);
  return Number.isNaN(t) ? Number.NEGATIVE_INFINITY : t;
}

function compassSourceLabel(origin: LoveMapRelationshipCompassChangePublic['origin_kind']): string {
  return origin === 'accepted_suggestion' ? 'Haven 建議 · 已接受' : '手動更新';
}

function repairSourceLabel(origin: LoveMapRepairAgreementChangePublic['origin_kind']): string {
  return origin === 'post_mediation_carry_forward' ? '修復帶回' : '手動微調';
}

function summarizeRepairChange(change: LoveMapRepairAgreementChangePublic): string {
  const fieldCount = change.fields.length;
  const fieldLabel = `${fieldCount} 個欄位`;
  return change.origin_kind === 'post_mediation_carry_forward'
    ? `把 ${fieldLabel} 的修復重點正式帶回 Heart。`
    : `在 Heart 裡重新調整了 ${fieldLabel}。`;
}

export function buildRelationshipEvolutionTimeline(input: {
  compassHistory: readonly LoveMapRelationshipCompassChangePublic[] | null | undefined;
  repairHistory: readonly LoveMapRepairAgreementChangePublic[] | null | undefined;
  maxEvents?: number;
}): RelationshipEvolutionEvent[] {
  const max = Math.min(Math.max(input.maxEvents ?? 6, 1), 8);
  const compass = [...(input.compassHistory ?? [])].map(
    (change): RelationshipEvolutionEvent => ({
      id: `compass:${change.id}`,
      domain: 'identity',
      domainLabel: 'Identity',
      title: 'Identity｜Relationship Compass 更新',
      summary: summarizeCompassChange(change),
      actorLabel: change.changed_by_name?.trim() || '未具名使用者',
      occurredAt: change.changed_at,
      sourceLabel: compassSourceLabel(change.origin_kind),
      revisionNote: (() => {
        const n = change.revision_note?.trim();
        return n ? n : null;
      })(),
      sourceHref: `#relationship-compass-history-${change.id}`,
      sectionHref: '#identity',
      testId: `relationship-evolution-event-compass-${change.id}`,
    }),
  );

  const repair = [...(input.repairHistory ?? [])].map(
    (change): RelationshipEvolutionEvent => ({
      id: `repair:${change.id}`,
      domain: 'heart',
      domainLabel: 'Heart',
      title: 'Heart｜Repair Agreements 更新',
      summary: summarizeRepairChange(change),
      actorLabel: change.changed_by_name?.trim() || '未具名使用者',
      occurredAt: change.changed_at,
      sourceLabel: repairSourceLabel(change.origin_kind),
      revisionNote: (() => {
        const n = change.revision_note?.trim();
        return n ? n : null;
      })(),
      sourceHref: `#relationship-repair-agreement-history-${change.id}`,
      sectionHref: '#heart',
      testId: `relationship-evolution-event-repair-${change.id}`,
    }),
  );

  const merged = [...compass, ...repair];
  merged.sort((a, b) => {
    const tb = timeValue(b.occurredAt);
    const ta = timeValue(a.occurredAt);
    if (tb !== ta) return tb - ta;
    return a.id.localeCompare(b.id);
  });

  return merged.slice(0, max);
}
