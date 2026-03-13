'use client';

type BadgeVariant =
  | 'default'
  | 'metadata'
  | 'status'
  | 'success'
  | 'warning'
  | 'destructive'
  | 'filter'
  | 'count'
  | 'outline';
type BadgeSize = 'sm' | 'md';

const variantClasses: Record<BadgeVariant, string> = {
  default: 'border-primary/15 bg-primary/10 text-primary',
  metadata: 'border-border/70 bg-card/72 text-muted-foreground',
  status: 'border-accent/18 bg-accent/10 text-card-foreground',
  success: 'border-accent/22 bg-accent/14 text-card-foreground',
  warning: 'border-primary/22 bg-primary/14 text-card-foreground',
  destructive: 'border-destructive/20 bg-destructive/12 text-destructive',
  filter: 'border-border/78 bg-background/78 text-card-foreground',
  count: 'border-transparent bg-primary text-primary-foreground shadow-soft',
  outline: 'border-border/82 bg-transparent text-card-foreground',
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: 'type-micro px-2.5 py-1',
  md: 'type-caption px-3 py-1.5',
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
        'inline-flex items-center rounded-full border cursor-default whitespace-nowrap transition-[background-color,border-color,color,box-shadow] duration-haven-fast ease-haven',
        variantClasses[variant],
        sizeClasses[size],
        className,
      ].join(' ')}
      {...props}
    />
  );
}
