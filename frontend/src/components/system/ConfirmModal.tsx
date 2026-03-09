'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/shadcn/dialog';
import { useConfirmStore } from '@/stores/useConfirmStore';
import Button from '@/components/ui/Button';

export default function ConfirmModal() {
  const pending = useConfirmStore((state) => state.pending);
  const resolve = useConfirmStore((state) => state.resolve);

  const open = Boolean(pending);
  const onOpenChange = (next: boolean) => {
    if (!next) resolve(false);
  };

  if (!pending) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm animate-scale-in">
        <DialogHeader>
          <DialogTitle className="font-art">{pending.options.title || '請確認'}</DialogTitle>
          <DialogDescription>{pending.options.message}</DialogDescription>
        </DialogHeader>
        <DialogFooter className="mt-6 flex-row justify-end gap-3 sm:flex-row">
          <Button
            type="button"
            variant="outline"
            size="md"
            onClick={() => resolve(false)}
          >
            {pending.options.cancelText || '取消'}
          </Button>
          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={() => resolve(true)}
          >
            {pending.options.confirmText || '確認'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
