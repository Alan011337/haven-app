'use client';

import dynamic from 'next/dynamic';
import MemorySkeleton from './MemorySkeleton';
import { MemoryShell } from './MemoryPrimitives';

const MemoryPageContent = dynamic(
  () => import('./MemoryPageContent').then((m) => m.default),
  {
    loading: () => <MemorySkeleton />,
  },
);

export default function MemoryPage() {
  return (
    <MemoryShell>
      <MemoryPageContent />
    </MemoryShell>
  );
}
