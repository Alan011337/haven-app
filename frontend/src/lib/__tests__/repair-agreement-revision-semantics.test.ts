import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildLatestCurrentRevisionByField,
  buildLatestNoteCarryingRevisionByField,
  resolveRepairAgreementFieldReviewSemantics,
  type RepairAgreementChangeLike,
} from '../repair-agreement-revision-semantics.ts';

type TestRepairAgreementChange = RepairAgreementChangeLike<{
  key: string;
  label: string;
  before_text: string | null;
  after_text: string | null;
}>;

function change(
  id: string,
  key: string,
  afterText: string | null,
  revisionNote: string | null,
): TestRepairAgreementChange {
  return {
    id,
    revision_note: revisionNote,
    fields: [
      {
        key,
        label: key,
        before_text: null,
        after_text: afterText,
      },
    ],
  };
}

test('exact-current revision is selected by matching the saved current field value', () => {
  const history = [
    change('newer-stale-value', 'repair_reentry', 'older wording', 'stale why'),
    change('current-value', 'repair_reentry', 'current wording', 'current why'),
  ];

  const currentByField = buildLatestCurrentRevisionByField(history, {
    repair_reentry: ' current wording ',
  });

  assert.equal(currentByField.repair_reentry?.change.id, 'current-value');
  assert.equal(currentByField.repair_reentry?.change.revision_note, 'current why');
});

test('exact-current note wins and suppresses earlier-note fallback', () => {
  const history = [
    change('current-with-note', 'repair_reentry', 'current wording', 'current why'),
    change('earlier-with-note', 'repair_reentry', 'earlier wording', 'earlier why'),
  ];
  const currentByField = buildLatestCurrentRevisionByField(history, {
    repair_reentry: 'current wording',
  });
  const noteByField = buildLatestNoteCarryingRevisionByField(history);

  const semantics = resolveRepairAgreementFieldReviewSemantics({
    currentRevision: currentByField.repair_reentry,
    latestNoteCarryingRevision: noteByField.repair_reentry,
  });

  assert.equal(semantics.primaryNote, 'current why');
  assert.equal(semantics.earlierNoteContext, null);
  assert.equal(semantics.shouldRenderEarlierNote, false);
});

test('earlier-note fallback only appears for superseded no-note current wording', () => {
  const history = [
    change('current-without-note', 'repair_reentry', 'current wording', null),
    change('earlier-with-note', 'repair_reentry', 'earlier wording', 'earlier why'),
  ];
  const currentByField = buildLatestCurrentRevisionByField(history, {
    repair_reentry: 'current wording',
  });
  const noteByField = buildLatestNoteCarryingRevisionByField(history);

  const semantics = resolveRepairAgreementFieldReviewSemantics({
    currentRevision: currentByField.repair_reentry,
    latestNoteCarryingRevision: noteByField.repair_reentry,
  });

  assert.equal(semantics.primaryNote, null);
  assert.equal(semantics.earlierNoteContext?.change.id, 'earlier-with-note');
  assert.equal(semantics.earlierNoteContext?.change.revision_note, 'earlier why');
  assert.equal(semantics.earlierNoteContext?.fieldChange.after_text, 'earlier wording');
  assert.equal(semantics.shouldRenderEarlierNote, true);
});

test('no note means no primary echo and no fallback pixels', () => {
  const history = [
    change('current-without-note', 'protect_what_matters', 'current wording', null),
    change('other-field-with-note', 'repair_reentry', 'other wording', 'other why'),
  ];
  const currentByField = buildLatestCurrentRevisionByField(history, {
    protect_what_matters: 'current wording',
  });
  const noteByField = buildLatestNoteCarryingRevisionByField(history);

  const semantics = resolveRepairAgreementFieldReviewSemantics({
    currentRevision: currentByField.protect_what_matters,
    latestNoteCarryingRevision: noteByField.protect_what_matters,
  });

  assert.equal(semantics.primaryNote, null);
  assert.equal(semantics.earlierNoteContext, null);
  assert.equal(semantics.shouldRenderEarlierNote, false);
});

test('unknown fields cannot create current revisions or note fallbacks', () => {
  const history = [
    change('unknown-current', 'legacy_conflict_field', 'current wording', 'legacy why'),
  ];
  const currentByField = buildLatestCurrentRevisionByField(history, {
    repair_reentry: 'current wording',
  });
  const noteByField = buildLatestNoteCarryingRevisionByField(history);

  assert.equal(currentByField.repair_reentry, null);
  assert.equal(noteByField.repair_reentry, null);
});
