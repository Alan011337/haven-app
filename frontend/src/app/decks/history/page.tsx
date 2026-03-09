'use client';

import { Suspense } from 'react';
import dynamic from 'next/dynamic';
import Skeleton from '@/components/ui/Skeleton';

const DeckHistoryPageContent = dynamic(
  () => import('./DeckHistoryPageContent').then((m) => m.default),
  {
    loading: () => (
      <div className="min-h-screen bg-muted/40 pb-20">
        <Skeleton className="h-14 w-full rounded-none" aria-hidden />
        <div className="p-4 max-w-2xl mx-auto space-y-6">
          <Skeleton className="h-32 w-full rounded-card" aria-hidden />
          <Skeleton className="h-24 w-full rounded-card" aria-hidden />
        </div>
      </div>
    ),
  },
);

export default function HistoryPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-muted/40 pb-20" />}>
      <DeckHistoryPageContent />
    </Suspense>
  );
}
