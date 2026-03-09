'use client';

import { useToastStore } from '@/stores/useToastStore';

export function useToast() {
  const showToast = useToastStore((state) => state.showToast);
  return { showToast };
}
