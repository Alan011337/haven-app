'use client';

import { forwardRef } from 'react';

const inputBase = [
  'flex w-full rounded-input border border-input bg-card px-4 py-2.5 text-card-foreground text-base',
  'placeholder:text-muted-foreground/60 placeholder:font-light',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:shadow-focus-glow focus-visible:border-transparent',
  'hover:border-primary/30',
  'disabled:cursor-not-allowed disabled:opacity-50',
  'transition-all duration-haven ease-haven',
].join(' ');

const inputError = 'border-destructive focus-visible:ring-destructive';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className = '', id: idProp, ...props }, ref) => {
    const id = idProp ?? label?.toLowerCase().replace(/\s+/g, '-');
    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={id} className="text-sm font-medium text-card-foreground tracking-wide">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={id}
          className={[inputBase, error ? inputError : '', className].join(' ')}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : helperText ? `${id}-helper` : undefined}
          {...props}
        />
        {error && (
          <p id={`${id}-error`} className="text-sm text-destructive animate-slide-up-fade" role="alert">
            {error}
          </p>
        )}
        {helperText && !error && (
          <p id={`${id}-helper`} className="text-sm text-muted-foreground">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, helperText, className = '', id: idProp, ...props }, ref) => {
    const id = idProp ?? label?.toLowerCase().replace(/\s+/g, '-');
    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={id} className="text-sm font-medium text-card-foreground tracking-wide">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={id}
          className={[inputBase, 'min-h-[80px] resize-y', error ? inputError : '', className].join(' ')}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : helperText ? `${id}-helper` : undefined}
          {...props}
        />
        {error && (
          <p id={`${id}-error`} className="text-sm text-destructive animate-slide-up-fade" role="alert">
            {error}
          </p>
        )}
        {helperText && !error && (
          <p id={`${id}-helper`} className="text-sm text-muted-foreground">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

export default Input;
