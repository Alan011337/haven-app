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
    ? `${base} surface-card`
    : variant === 'sidebar'
      ? `${base} surface-glass-panel`
      : `${base} surface-glass-card`;
  return <Tag className={`${style} ${className}`}>{children}</Tag>;
}
