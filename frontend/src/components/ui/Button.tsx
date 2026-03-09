'use client';

import { forwardRef } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'outline' | 'destructive';
type ButtonSize = 'sm' | 'md' | 'lg';

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-gradient-to-b from-primary to-primary/90 text-primary-foreground rounded-full border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 transition-all duration-haven ease-haven',
  secondary:
    'bg-muted text-card-foreground hover:bg-muted/80 hover:shadow-soft active:scale-[0.97] focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 transition-all duration-haven ease-haven',
  ghost:
    'text-card-foreground hover:bg-muted hover:text-card-foreground active:scale-[0.97] focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 transition-all duration-haven ease-haven',
  outline:
    'border border-input bg-card text-card-foreground hover:bg-muted hover:text-card-foreground hover:shadow-soft active:scale-[0.97] focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 transition-all duration-haven ease-haven',
  destructive:
    'bg-gradient-to-b from-destructive to-destructive/90 text-destructive-foreground border-t border-t-white/20 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 transition-all duration-haven ease-haven',
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-8 px-3.5 text-xs rounded-button',
  md: 'h-10 px-5 text-sm rounded-button',
  lg: 'h-12 px-7 text-base rounded-button',
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
        className={[
          'inline-flex items-center justify-center gap-2 font-medium transition-colors duration-haven-fast ease-haven',
          'disabled:pointer-events-none disabled:opacity-50',
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
