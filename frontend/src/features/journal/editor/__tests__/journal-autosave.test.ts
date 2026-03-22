import assert from 'node:assert/strict';
import test from 'node:test';
import { shouldScheduleJournalAutosave } from '../useJournalAutosave.ts';

test('shouldScheduleJournalAutosave returns true only when autosave is enabled and idle', () => {
  assert.equal(shouldScheduleJournalAutosave({ enabled: true, pending: false }), true);
  assert.equal(shouldScheduleJournalAutosave({ enabled: false, pending: false }), false);
  assert.equal(shouldScheduleJournalAutosave({ enabled: true, pending: true }), false);
});
