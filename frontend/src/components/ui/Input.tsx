'use client';

import { forwardRef } from 'react';

const inputBase = [
  'flex w-full surface-field focus-ring-premium px-4 py-3 text-card-foreground type-body',
  'placeholder:text-muted-foreground/74 placeholder:font-light',
  'disabled:cursor-not-allowed disabled:bg-muted/55 disabled:text-muted-foreground/82',
  'read-only:bg-muted/35 read-only:text-card-foreground/82',
  'transition-[border-color,box-shadow,background-color,color] duration-haven ease-haven',
].join(' ');

const inputError = 'surface-field-error';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className = '', id: idProp, ...props }, ref) => {
    const id = idProp ?? label?.toLowerCase().replace(/\s+/g, '-');
    return (
      <div className="stack-block w-full">
        {label && (
          <label htmlFor={id} className="type-label text-card-foreground/84">
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
          <p id={`${id}-error`} className="type-caption text-destructive animate-slide-up-fade" role="alert">
            {error}
          </p>
        )}
        {helperText && !error && (
          <p id={`${id}-helper`} className="type-caption text-muted-foreground">
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
      <div className="stack-block w-full">
        {label && (
          <label htmlFor={id} className="type-label text-card-foreground/84">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={id}
          className={[inputBase, 'min-h-[8.5rem] resize-y py-3.5', error ? inputError : '', className].join(' ')}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : helperText ? `${id}-helper` : undefined}
          {...props}
        />
        {error && (
          <p id={`${id}-error`} className="type-caption text-destructive animate-slide-up-fade" role="alert">
            {error}
          </p>
        )}
        {helperText && !error && (
          <p id={`${id}-helper`} className="type-caption text-muted-foreground">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

export default Input;
