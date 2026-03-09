/**
 * P2-A-4: Glass panel primitive for sidebars/sections.
 * variant="solid" toggles non-glass (DoD: quick switch).
 */

import type { ReactNode } from 'react';

interface GlassPanelProps {
  children: ReactNode;
  className?: string;
  /** 'glass' (default) | 'solid' | 'sidebar' (Phase 5: translucent + thin edge). */
  variant?: 'glass' | 'solid' | 'sidebar';
  /** Semantic element. */
  as?: 'div' | 'aside';
}

export function GlassPanel({ children, className = '', variant = 'glass', as: Tag = 'div' }: GlassPanelProps) {
  const base = 'rounded-card';
  const style = variant === 'solid'
    ? `${base} border border-foreground/10 bg-card shadow-soft`
    : variant === 'sidebar'
      ? `${base} bg-card/80 backdrop-blur-2xl border-r border-foreground/5 shadow-glass-inset`
      : `${base} border border-foreground/10 glass-panel-art`;
  return <Tag className={`${style} ${className}`}>{children}</Tag>;
}
