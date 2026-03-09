'use client';

import { createContext, useCallback, useContext, useMemo, useState } from 'react';

interface ConfirmOptions {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
}

interface ConfirmState {
  options: ConfirmOptions;
  resolve: (confirmed: boolean) => void;
}

interface ConfirmContextValue {
  confirm: (options: ConfirmOptions) => Promise<boolean>;
}

const ConfirmContext = createContext<ConfirmContextValue | undefined>(undefined);

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [dialog, setDialog] = useState<ConfirmState | null>(null);

  const confirm = useCallback((options: ConfirmOptions) => {
    return new Promise<boolean>((resolve) => {
      setDialog({ options, resolve });
    });
  }, []);

  const closeDialog = useCallback((confirmed: boolean) => {
    setDialog((prev) => {
      if (prev) {
        prev.resolve(confirmed);
      }
      return null;
    });
  }, []);

  const value = useMemo(() => ({ confirm }), [confirm]);

  return (
    <ConfirmContext.Provider value={value}>
      {children}
      {dialog && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-sm rounded-card border border-border bg-card p-6 shadow-modal">
            <h3 className="text-lg font-bold text-foreground">
              {dialog.options.title || '請確認'}
            </h3>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              {dialog.options.message}
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => closeDialog(false)}
                className="rounded-lg border border-border px-4 py-2 text-sm text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {dialog.options.cancelText || '取消'}
              </button>
              <button
                type="button"
                onClick={() => closeDialog(true)}
                className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground shadow-soft hover:shadow-lift active:scale-95 transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {dialog.options.confirmText || '確認'}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  const context = useContext(ConfirmContext);
  if (!context) {
    throw new Error('useConfirm must be used within ConfirmProvider');
  }
  return context;
}
