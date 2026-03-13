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
  const base =
    'relative overflow-hidden rounded-card transition-[box-shadow,border-color,transform,background-color] duration-haven ease-haven card-accent-bar';
  const style = variant === 'solid'
    ? `${base} surface-card surface-card-interactive`
    : `${base} surface-glass-card surface-card-interactive`;
  return (
    <div className={`${style} ${className}`} {...rest}>
      {children}
    </div>
  );
}
