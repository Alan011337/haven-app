import assert from 'node:assert/strict';
import test from 'node:test';
import {
  isAltWorthRendering,
  resolveJournalFigureCaption,
} from '../journal-figure-caption.ts';
import { JOURNAL_IMAGE_ALT_FALLBACK } from '../editor/journal-attachment-markdown.ts';

// Drift guard: the helper inlines 'journal image' to avoid cross-file .ts
// relative imports. This test imports the source-of-truth constant and
// asserts the helper still rejects it. If someone edits the exported
// constant in isolation, this test fails loudly.
test('isAltWorthRendering: rejects the exported JOURNAL_IMAGE_ALT_FALLBACK (drift guard)', () => {
  assert.equal(isAltWorthRendering(JOURNAL_IMAGE_ALT_FALLBACK), false);
});

// ---- resolveJournalFigureCaption: 8 cases ----

test('caption present → authored, text preserved verbatim', () => {
  assert.deepEqual(
    resolveJournalFigureCaption({
      caption: '窗邊光線停在她的杯沿',
      alt: 'morning with mei',
    }),
    { kind: 'authored', text: '窗邊光線停在她的杯沿' },
  );
});

test('alt present, caption empty string → alt', () => {
  assert.deepEqual(
    resolveJournalFigureCaption({
      caption: '',
      alt: 'morning with mei',
    }),
    { kind: 'alt', text: 'morning with mei' },
  );
});

test('both empty → none', () => {
  assert.deepEqual(
    resolveJournalFigureCaption({ caption: '', alt: '' }),
    { kind: 'none', text: null },
  );
});

test('whitespace-only caption + substantive alt → alt', () => {
  assert.deepEqual(
    resolveJournalFigureCaption({
      caption: '   \n  ',
      alt: 'afternoon at the park',
    }),
    { kind: 'alt', text: 'afternoon at the park' },
  );
});

test('null caption, null alt → none', () => {
  assert.deepEqual(
    resolveJournalFigureCaption({ caption: null, alt: null }),
    { kind: 'none', text: null },
  );
});

test('undefined caption, null alt → none (parity)', () => {
  assert.deepEqual(
    resolveJournalFigureCaption({ caption: undefined, alt: null }),
    { kind: 'none', text: null },
  );
});

test("alt quality gate: caption null, alt === 'journal image' → none", () => {
  assert.deepEqual(
    resolveJournalFigureCaption({ caption: null, alt: 'journal image' }),
    { kind: 'none', text: null },
  );
});

test('alt quality gate: digit/date junk suppressed, substantive alt admitted', () => {
  assert.deepEqual(
    resolveJournalFigureCaption({
      caption: null,
      alt: 'img 20240411 1234',
    }),
    { kind: 'none', text: null },
  );
  assert.deepEqual(
    resolveJournalFigureCaption({
      caption: null,
      alt: 'morning with mei',
    }),
    { kind: 'alt', text: 'morning with mei' },
  );
});

// ---- isAltWorthRendering: 3 dedicated predicate-gate tests ----

test('isAltWorthRendering: rejects the literal fallback', () => {
  assert.equal(isAltWorthRendering('journal image'), false);
  // Surrounding whitespace is normalized away before the literal check.
  assert.equal(isAltWorthRendering('  journal image  '), false);
});

test('isAltWorthRendering: rejects digit/date/punct-only strings', () => {
  assert.equal(isAltWorthRendering('20240411'), false);
  assert.equal(isAltWorthRendering('2024-04-11'), false);
  assert.equal(isAltWorthRendering('___ ...'), false);
  assert.equal(isAltWorthRendering('12:34:56'), false);
});

test('isAltWorthRendering: rejects strings shorter than 2 chars', () => {
  assert.equal(isAltWorthRendering('a'), false);
  assert.equal(isAltWorthRendering(''), false);
  assert.equal(isAltWorthRendering(' '), false);
  assert.equal(isAltWorthRendering(null), false);
  assert.equal(isAltWorthRendering(undefined), false);
  // Two-char substantive strings should pass.
  assert.equal(isAltWorthRendering('ok'), true);
});
