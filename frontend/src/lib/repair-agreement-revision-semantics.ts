export const REPAIR_AGREEMENT_FIELD_KEYS = [
  'protect_what_matters',
  'avoid_in_conflict',
  'repair_reentry',
] as const;

export type RepairAgreementFieldKey = (typeof REPAIR_AGREEMENT_FIELD_KEYS)[number];

export type RepairAgreementsForRevisionSemantics = Partial<
  Record<RepairAgreementFieldKey, string | null | undefined>
> | null | undefined;

export type RepairAgreementFieldChangeLike = {
  key: string;
  before_text?: string | null;
  after_text?: string | null;
};

export type RepairAgreementChangeLike<TField extends RepairAgreementFieldChangeLike = RepairAgreementFieldChangeLike> = {
  id: string;
  revision_note?: string | null;
  fields: TField[];
};

export type RepairAgreementFieldRevisionContext<
  TChange extends RepairAgreementChangeLike = RepairAgreementChangeLike,
> = {
  change: TChange;
  fieldChange: TChange['fields'][number] & {
    key: RepairAgreementFieldKey;
  };
};

export type RepairAgreementFieldReviewSemantics<
  TChange extends RepairAgreementChangeLike = RepairAgreementChangeLike,
> = {
  currentRevision: RepairAgreementFieldRevisionContext<TChange> | null;
  primaryNote: string | null;
  earlierNoteContext: RepairAgreementFieldRevisionContext<TChange> | null;
  shouldRenderEarlierNote: boolean;
};

export function normalizeRepairAgreementText(value?: string | null) {
  const trimmed = (value ?? '').trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function isRepairAgreementFieldKey(value: string): value is RepairAgreementFieldKey {
  return REPAIR_AGREEMENT_FIELD_KEYS.includes(value as RepairAgreementFieldKey);
}

export function getRepairAgreementSavedValue(
  agreements: RepairAgreementsForRevisionSemantics,
  fieldKey: RepairAgreementFieldKey,
) {
  return normalizeRepairAgreementText(agreements?.[fieldKey]);
}

export function buildLatestCurrentRevisionByField<TChange extends RepairAgreementChangeLike>(
  repairAgreementHistory: TChange[] | null | undefined,
  repairAgreements: RepairAgreementsForRevisionSemantics,
): Record<RepairAgreementFieldKey, RepairAgreementFieldRevisionContext<TChange> | null> {
  const next: Record<RepairAgreementFieldKey, RepairAgreementFieldRevisionContext<TChange> | null> = {
    protect_what_matters: null,
    avoid_in_conflict: null,
    repair_reentry: null,
  };

  for (const change of repairAgreementHistory ?? []) {
    for (const fieldChange of change.fields) {
      if (!isRepairAgreementFieldKey(fieldChange.key)) {
        continue;
      }
      if (next[fieldChange.key]) {
        continue;
      }
      const currentSavedValue = getRepairAgreementSavedValue(repairAgreements, fieldChange.key);
      if (currentSavedValue !== normalizeRepairAgreementText(fieldChange.after_text)) {
        continue;
      }
      next[fieldChange.key] = {
        change,
        fieldChange: {
          ...fieldChange,
          key: fieldChange.key,
        },
      };
    }
  }

  return next;
}

export function buildLatestNoteCarryingRevisionByField<TChange extends RepairAgreementChangeLike>(
  repairAgreementHistory: TChange[] | null | undefined,
): Record<RepairAgreementFieldKey, RepairAgreementFieldRevisionContext<TChange> | null> {
  const next: Record<RepairAgreementFieldKey, RepairAgreementFieldRevisionContext<TChange> | null> = {
    protect_what_matters: null,
    avoid_in_conflict: null,
    repair_reentry: null,
  };

  for (const change of repairAgreementHistory ?? []) {
    if (!change.revision_note) {
      continue;
    }
    for (const fieldChange of change.fields) {
      if (!isRepairAgreementFieldKey(fieldChange.key)) {
        continue;
      }
      if (next[fieldChange.key]) {
        continue;
      }
      next[fieldChange.key] = {
        change,
        fieldChange: {
          ...fieldChange,
          key: fieldChange.key,
        },
      };
    }
  }

  return next;
}

export function resolveRepairAgreementFieldReviewSemantics<
  TChange extends RepairAgreementChangeLike,
>({
  currentRevision,
  latestNoteCarryingRevision,
}: {
  currentRevision: RepairAgreementFieldRevisionContext<TChange> | null;
  latestNoteCarryingRevision: RepairAgreementFieldRevisionContext<TChange> | null;
}): RepairAgreementFieldReviewSemantics<TChange> {
  if (!currentRevision) {
    return {
      currentRevision: null,
      primaryNote: null,
      earlierNoteContext: null,
      shouldRenderEarlierNote: false,
    };
  }

  const primaryNote = currentRevision.change.revision_note || null;
  const earlierNoteContext = primaryNote ? null : latestNoteCarryingRevision;
  const shouldRenderEarlierNote = Boolean(
    earlierNoteContext && earlierNoteContext.change.id !== currentRevision.change.id,
  );

  return {
    currentRevision,
    primaryNote,
    earlierNoteContext: shouldRenderEarlierNote ? earlierNoteContext : null,
    shouldRenderEarlierNote,
  };
}
