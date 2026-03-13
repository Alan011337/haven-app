'use client';

import { forwardRef } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'outline' | 'destructive';
type ButtonSize = 'sm' | 'md' | 'lg';

const buttonBase = [
  'relative inline-flex shrink-0 items-center justify-center overflow-hidden whitespace-nowrap select-none',
  'gap-[var(--space-inline)] rounded-button border text-center',
  'type-label focus-ring-premium transition-[transform,box-shadow,background-color,border-color,color,opacity] duration-haven ease-haven',
  'disabled:pointer-events-none disabled:opacity-55 disabled:shadow-none',
].join(' ');

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'border-transparent bg-gradient-to-b from-primary to-primary/92 text-primary-foreground shadow-satin-button hover:-translate-y-px hover:shadow-lift active:translate-y-0 active:scale-[0.985]',
  secondary:
    'border-border/70 bg-card/86 text-card-foreground shadow-soft hover:border-primary/16 hover:bg-card hover:shadow-soft active:scale-[0.99]',
  ghost:
    'border-transparent bg-transparent text-card-foreground shadow-none hover:bg-muted/78 hover:text-foreground active:scale-[0.99]',
  outline:
    'border-border/85 bg-background/74 text-card-foreground shadow-glass-inset hover:border-primary/18 hover:bg-muted/48 hover:shadow-soft active:scale-[0.99]',
  destructive:
    'border-transparent bg-gradient-to-b from-destructive to-destructive/92 text-destructive-foreground shadow-satin-button hover:-translate-y-px hover:shadow-soft active:translate-y-0 active:scale-[0.985]',
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-9 px-4',
  md: 'h-11 px-5',
  lg: 'h-12 px-6 text-sm',
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      leftIcon,
      rightIcon,
      className = '',
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled ?? loading;
    return (
      <button
        ref={ref}
        type={props.type ?? 'button'}
        disabled={isDisabled}
        aria-busy={loading || undefined}
        className={[
          buttonBase,
          variantClasses[variant],
          sizeClasses[size],
          className,
        ].join(' ')}
        {...props}
      >
        {loading ? (
          <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />
        ) : (
          leftIcon
        )}
        {children}
        {!loading && rightIcon}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
