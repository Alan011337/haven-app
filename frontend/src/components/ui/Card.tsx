'use client';

import { forwardRef } from 'react';

const cardBase =
  'relative surface-card text-card-foreground transition-[border-color,box-shadow,transform,background-color] duration-haven ease-haven';

const explicitInteractiveCardClasses = 'surface-card-interactive focus-ring-premium cursor-pointer';
const inferredInteractiveCardClasses =
  'focus-ring-premium cursor-pointer hover:border-primary/10 hover:shadow-soft';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  interactive?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', interactive, onClick, role, tabIndex, ...props }, ref) => {
    const isExplicitInteractive = interactive === true;
    const isInferredInteractive =
      interactive === undefined && Boolean(onClick || role === 'button' || role === 'link' || tabIndex !== undefined);
    const interactionClasses = isExplicitInteractive
      ? explicitInteractiveCardClasses
      : isInferredInteractive
        ? inferredInteractiveCardClasses
        : '';
    return (
      <div
        ref={ref}
        data-interactive={isExplicitInteractive ? 'explicit' : isInferredInteractive ? 'inferred' : undefined}
        className={[cardBase, interactionClasses, className].join(' ')}
        onClick={onClick}
        role={role}
        tabIndex={tabIndex}
        {...props}
      />
    );
  }
);

Card.displayName = 'Card';

export type CardHeaderProps = React.HTMLAttributes<HTMLDivElement>;

export const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(({ className = '', ...props }, ref) => (
  <div ref={ref} className={['stack-block p-6 md:p-7', className].join(' ')} {...props} />
));

CardHeader.displayName = 'CardHeader';

export type CardContentProps = React.HTMLAttributes<HTMLDivElement>;

export const CardContent = forwardRef<HTMLDivElement, CardContentProps>(({ className = '', ...props }, ref) => (
  <div ref={ref} className={['px-6 pb-6 pt-0 md:px-7 md:pb-7', className].join(' ')} {...props} />
));

CardContent.displayName = 'CardContent';

export type CardFooterProps = React.HTMLAttributes<HTMLDivElement>;

export const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(({ className = '', ...props }, ref) => (
  <div ref={ref} className={['stack-inline px-6 pb-6 pt-0 md:px-7 md:pb-7', className].join(' ')} {...props} />
));

CardFooter.displayName = 'CardFooter';
