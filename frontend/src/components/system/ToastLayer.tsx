'use client';

import { useToastStore, type ToastType } from '@/stores/useToastStore';

const TOAST_STYLES: Record<ToastType, string> = {
  success: 'border-accent/30 bg-gradient-to-r from-accent/10 to-accent/5 text-accent',
  error: 'border-destructive/30 bg-gradient-to-r from-destructive/10 to-destructive/5 text-destructive',
  info: 'border-primary/30 bg-gradient-to-r from-primary/10 to-primary/5 text-primary',
};

export default function ToastLayer() {
  const toasts = useToastStore((state) => state.toasts);

  return (
    <div className="pointer-events-none fixed right-4 top-4 z-[100] flex w-[min(90vw,22rem)] flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`rounded-xl border px-4 py-3 text-sm font-medium shadow-soft backdrop-blur-sm animate-slide-up-fade ${TOAST_STYLES[toast.type]}`}
        >
          {toast.message}
        </div>
      ))}
    </div>
  );
}
