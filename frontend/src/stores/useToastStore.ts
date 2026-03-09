'use client';

import { create } from 'zustand';
import { toast as sonnerToast } from 'sonner';

export type ToastType = 'success' | 'error' | 'info';

export interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastStore {
  toasts: ToastItem[];
  showToast: (message: string, type?: ToastType) => void;
  dismiss: (id: number) => void;
}

export const useToastStore = create<ToastStore>(() => ({
  toasts: [],

  showToast: (message: string, type: ToastType = 'info') => {
    if (type === 'success') {
      sonnerToast.success(message);
    } else if (type === 'error') {
      sonnerToast.error(message);
    } else {
      sonnerToast.info(message);
    }
  },

  dismiss: () => {},
}));
