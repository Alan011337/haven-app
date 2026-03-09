'use client';

import { forwardRef } from 'react';

const cardBase =
  'relative bg-card text-card-foreground border border-border/80 rounded-card shadow-soft transition-all duration-haven ease-haven hover:shadow-lift hover:-translate-y-0.5';

export type CardProps = React.HTMLAttributes<HTMLDivElement>;

export const Card = forwardRef<HTMLDivElement, CardProps>(({ className = '', ...props }, ref) => (
  <div ref={ref} className={[cardBase, className].join(' ')} {...props} />
));

Card.displayName = 'Card';

export type CardHeaderProps = React.HTMLAttributes<HTMLDivElement>;

export const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(({ className = '', ...props }, ref) => (
  <div ref={ref} className={['flex flex-col space-y-1.5 p-6', className].join(' ')} {...props} />
));

CardHeader.displayName = 'CardHeader';

export type CardContentProps = React.HTMLAttributes<HTMLDivElement>;

export const CardContent = forwardRef<HTMLDivElement, CardContentProps>(({ className = '', ...props }, ref) => (
  <div ref={ref} className={['p-6 pt-0', className].join(' ')} {...props} />
));

CardContent.displayName = 'CardContent';

export type CardFooterProps = React.HTMLAttributes<HTMLDivElement>;

export const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(({ className = '', ...props }, ref) => (
  <div ref={ref} className={['flex items-center p-6 pt-0', className].join(' ')} {...props} />
));

CardFooter.displayName = 'CardFooter';
