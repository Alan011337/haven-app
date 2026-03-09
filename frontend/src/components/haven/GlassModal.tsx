/**
 * P2-A-4: Glass modal/dialog content wrapper. Wrap dialog content for glass effect.
 * variant="solid" toggles non-glass (DoD: quick switch).
 */

import type { ReactNode } from 'react';

interface GlassModalProps {
  children: ReactNode;
  className?: string;
  /** 'glass' (default) | 'solid'. */
  variant?: 'glass' | 'solid';
}

export function GlassModal({ children, className = '', variant = 'glass' }: GlassModalProps) {
  const base = 'rounded-card border border-foreground/10 shadow-modal overflow-hidden relative';
  const style = variant === 'solid'
    ? `${base} bg-card`
    : `${base} glass-panel-art backdrop-blur-[var(--glass-blur-3)] bg-background/60`;
  return (
    <div className={`${style} ${className}`}>
      <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/20 to-transparent" aria-hidden />
      {children}
    </div>
  );
}
