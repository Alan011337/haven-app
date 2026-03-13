export const routeLinkCtaClasses = {
  neutral:
    'inline-flex items-center gap-[var(--space-inline)] rounded-button border border-white/60 bg-white/74 px-4 py-2.5 type-label text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium',
  primary:
    'inline-flex items-center gap-[var(--space-inline)] rounded-button border border-primary/16 bg-primary/8 px-5 py-3 type-label text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium',
} as const;

export const selectionChipBaseClass =
  'rounded-full border px-4 py-2 type-label transition-all duration-haven-fast ease-haven focus-ring-premium';

export const selectionChipWithIconClass = `inline-flex items-center gap-[var(--space-inline)] ${selectionChipBaseClass}`;

export function getSelectionChipStateClass(active: boolean) {
  return active
    ? 'border-primary/18 bg-primary/10 text-card-foreground shadow-soft'
    : 'border-white/55 bg-white/70 text-muted-foreground hover:border-primary/16 hover:text-card-foreground';
}
