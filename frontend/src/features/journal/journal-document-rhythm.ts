// Shared document rhythm tokens for Journal write/read continuity.
//
// Consumed by:
//   - Lexical `editorTheme` + `ContentEditable` wrapper in
//     `src/features/journal/editor/JournalLexicalComposer.tsx` (write mode).
//   - Markdown renderer `'read'` variant branches in
//     `src/lib/journal-markdown.tsx` (read mode, including compare mode).
//   - Write-side figure in `src/features/journal/editor/JournalImageNode.tsx`.
//
// Intentionally NOT consumed by:
//   - The `'partner'` variant (smaller-scale partner card context) and the
//     `'studio'` variant (non-standard preview context) in journal-markdown.tsx.
//     Those keep their own tokens so this module stays scoped to the
//     write↔read rail.
//   - Tailwind token config; these stay as utility-class strings to avoid
//     system-wide churn.
//
// Landing values sit deliberately between the previous write and read values,
// biased slightly toward read's generosity since read is the finished artifact.

export const JOURNAL_RHYTHM = {
  h1: 'font-art tracking-[-0.022em] text-card-foreground text-[2.6rem] leading-[1.02] md:text-[3.1rem]',
  h2: 'font-art tracking-[-0.022em] text-card-foreground mt-11 text-[1.95rem] leading-[1.1] md:text-[2.2rem]',
  h3: 'font-art tracking-[-0.02em] text-card-foreground mt-9 text-[1.42rem] leading-[1.18] md:text-[1.58rem]',
  paragraph:
    'text-[1.07rem] leading-[2.02] text-card-foreground md:text-[1.08rem]',
  paragraphMargin: 'my-6',
  listItem:
    'pl-1 text-[1.07rem] leading-[2.02] text-card-foreground marker:text-primary/55 md:text-[1.08rem]',
  ul: 'my-6 ml-6 list-disc space-y-2.5',
  ol: 'my-6 ml-6 list-decimal space-y-2.5',
  quote:
    'my-9 rounded-[1.7rem] border border-primary/13 bg-primary/[0.05] px-6 py-5 font-art text-[1.17rem] leading-[1.84] text-card-foreground md:px-8 md:py-6',
  hr: 'my-11 border-none h-px bg-primary/[0.13]',
  figure:
    'my-10 overflow-hidden rounded-[2.05rem] border border-[rgba(219,204,187,0.34)] bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(249,244,237,0.9))] shadow-soft md:mx-[-1.25rem]',
  figureImage:
    'max-h-[36rem] w-full bg-[rgba(246,239,231,0.72)] object-contain',
  figcaption:
    'border-t border-white/58 px-5 py-3.5 text-sm leading-7 text-muted-foreground md:px-6',
  scrollMarginClass: 'scroll-mt-40',
  scrollMarginPx: 160,
  containerMaxW: 'max-w-[44rem]',
} as const;

export type JournalRhythmTokens = typeof JOURNAL_RHYTHM;
