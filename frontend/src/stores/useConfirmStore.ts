'use client';

import { create } from 'zustand';

export interface ConfirmOptions {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
}

interface PendingConfirm {
  options: ConfirmOptions;
  resolve: (confirmed: boolean) => void;
}

interface ConfirmStore {
  pending: PendingConfirm | null;
  confirm: (options: ConfirmOptions) => Promise<boolean>;
  resolve: (confirmed: boolean) => void;
}

export const useConfirmStore = create<ConfirmStore>((set, get) => ({
  pending: null,

  confirm: (options: ConfirmOptions) => {
    return new Promise<boolean>((resolve) => {
      set({ pending: { options, resolve } });
    });
  },

  resolve: (confirmed: boolean) => {
    const { pending } = get();
    if (pending) {
      pending.resolve(confirmed);
    }
    set({ pending: null });
  },
}));
