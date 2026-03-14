'use client';

import { Suspense } from 'react';
import dynamic from 'next/dynamic';
import DeckLibrarySkeleton from './DeckLibrarySkeleton';

const DecksPageContent = dynamic(
  () => import('./DecksPageContent').then((m) => m.default),
  {
    loading: () => <DeckLibrarySkeleton />,
  },
);

export default function DecksPage() {
  return (
    <Suspense fallback={<DeckLibrarySkeleton />}>
      <DecksPageContent />
    </Suspense>
  );
}
