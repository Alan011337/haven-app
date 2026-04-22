// Resolve the visible figcaption treatment for a journal figure.
//
// Unifies the decision across write and read surfaces so the figure's
// authored-caption-vs-alt-whisper switch lives in exactly one place with
// one set of tests.
//
// Shape:
//   - `authored`: the author wrote a caption — render in editorial italic.
//   - `alt`: no author caption, but the filename-derived alt is substantive
//            enough to whisper as context — render in a quieter tone.
//   - `none`: caption is empty AND alt is absent / junk-ish — render no
//             figcaption. SR alt is bound independently on the <img>, so
//             screen-reader a11y is unaffected by this decision.
//
// The `isAltWorthRendering` predicate is intentionally conservative: it
// rejects the literal fallback (`'journal image'`), strings shorter than
// 2 chars, and digit/date/punct-only junk like `IMG_20240411_1234`.

// Mirror of JOURNAL_IMAGE_ALT_FALLBACK from
// `src/features/journal/editor/journal-attachment-markdown.ts`. Inlined so
// this helper stays free of cross-file .ts relative imports (TypeScript
// rejects those without `allowImportingTsExtensions`, and the bare
// specifier / `@/` alias can't be resolved by Node's
// --experimental-strip-types test runner). The drift-guard test in
// `__tests__/journal-figure-caption.test.ts` imports the exported constant
// from the source-of-truth module and asserts this helper rejects it, so
// any edit to either literal surfaces immediately.
const JOURNAL_IMAGE_ALT_FALLBACK = 'journal image';

export type JournalFigureCaption =
  | { kind: 'authored'; text: string }
  | { kind: 'alt'; text: string }
  | { kind: 'none'; text: null };

function normalize(value: string | null | undefined): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function isAltWorthRendering(alt: string | null | undefined): boolean {
  const trimmed = normalize(alt);
  if (trimmed === null) return false;
  if (trimmed === JOURNAL_IMAGE_ALT_FALLBACK) return false;
  if (trimmed.length < 2) return false;
  // Pure digit / whitespace / punct junk (e.g., "2024-04-11", "12:34:56").
  if (/^[\d\s._\-:/]+$/.test(trimmed)) return false;
  // Camera-filename fingerprint: digits plus sparse alpha content (e.g.,
  // "IMG 20240411 1234", "DSC 0091"). If any digit is present, require at
  // least 4 letter chars — ASCII or CJK — so short camera prefixes are
  // rejected while substantive labels like "my 3rd photo" still pass.
  if (/\d/.test(trimmed)) {
    const alphaMatches = trimmed.match(/[a-zA-Z\u4e00-\u9fa5]/g);
    if (!alphaMatches || alphaMatches.length < 4) return false;
  }
  return true;
}

export function resolveJournalFigureCaption(input: {
  caption?: string | null;
  alt?: string | null;
}): JournalFigureCaption {
  const authored = normalize(input.caption);
  if (authored) return { kind: 'authored', text: authored };
  if (isAltWorthRendering(input.alt)) {
    return { kind: 'alt', text: normalize(input.alt) as string };
  }
  return { kind: 'none', text: null };
}
