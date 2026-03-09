'use client';

type BadgeVariant = 'default' | 'success' | 'warning' | 'destructive' | 'outline';
type BadgeSize = 'sm' | 'md';

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-primary/10 text-primary border-primary/15 backdrop-blur-sm shadow-glass-inset',
  success: 'bg-accent/10 text-accent border-accent/15 backdrop-blur-sm shadow-glass-inset',
  warning: 'bg-primary/20 text-primary border-primary/20 backdrop-blur-sm shadow-glass-inset',
  destructive: 'bg-destructive/10 text-destructive border-destructive/15 backdrop-blur-sm shadow-glass-inset',
  outline: 'border border-border/80 bg-card/80 text-card-foreground backdrop-blur-sm',
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: 'text-[10px] px-2.5 py-0.5',
  md: 'text-xs px-3 py-1',
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: BadgeSize;
}

export default function Badge({
  variant = 'default',
  size = 'md',
  className = '',
  ...props
}: BadgeProps) {
  return (
    <span
      className={[
        'inline-flex items-center rounded-full border font-semibold tracking-wide cursor-default transition-all duration-haven-fast ease-haven hover:brightness-[1.08]',
        variantClasses[variant],
        sizeClasses[size],
        className,
      ].join(' ')}
      {...props}
    />
  );
}
