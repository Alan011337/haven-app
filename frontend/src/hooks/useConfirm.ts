'use client';

import { useConfirmStore } from '@/stores/useConfirmStore';

export function useConfirm() {
  const confirm = useConfirmStore((state) => state.confirm);
  return { confirm };
}
