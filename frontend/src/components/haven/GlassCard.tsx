/**
 * P2-A-4: Glass card primitive. Use instead of ad-hoc blur classes.
 * variant="solid" toggles non-glass (DoD: quick switch).
 */

import type { ReactNode } from 'react';

interface GlassCardProps extends React.ComponentPropsWithoutRef<'div'> {
  children: ReactNode;
  className?: string;
  /** 'glass' (default) | 'solid' for non-glass fallback. */
  variant?: 'glass' | 'solid';
}

export function GlassCard({ children, className = '', variant = 'glass', ...rest }: GlassCardProps) {
  const base = 'relative overflow-hidden rounded-card border border-foreground/10 transition-shadow duration-haven ease-haven card-accent-bar';
  const style = variant === 'solid'
    ? `${base} bg-card shadow-soft hover:shadow-lift`
    : `${base} glass-panel-art shadow-soft hover:shadow-lift`;
  return (
    <div className={`${style} ${className}`} {...rest}>
      {children}
    </div>
  );
}
