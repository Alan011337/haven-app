// frontend/src/app/decks/page.tsx

'use client';

import { Suspense } from 'react';
import dynamic from 'next/dynamic';
import { ArrowLeft } from 'lucide-react';
import Skeleton from '@/components/ui/Skeleton';

function DecksLoadingSkeleton() {
  return (
    <div className="min-h-screen bg-muted/40 pb-20">
      <header className="sticky top-0 z-10 bg-card/80 backdrop-blur-2xl border-b border-border/60 space-page flex items-center shadow-soft py-4">
        <div className="p-2 -ml-2">
          <ArrowLeft className="w-5 h-5 text-muted-foreground" aria-hidden />
        </div>
        <h1 className="ml-2 text-title font-art font-bold text-card-foreground tracking-tight">牌組圖書館</h1>
      </header>
      <main className="space-page space-y-6 max-w-6xl mx-auto">
        <div className="text-center space-y-2 mb-6 mt-4 animate-page-enter">
          <h2 className="text-title font-art font-bold text-card-foreground tracking-tight">今天想聊點什麼？</h2>
          <p className="text-caption text-muted-foreground">選擇一套牌組，開啟無限話題。</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 animate-page-enter-delay-1">
          <Skeleton className="h-48 rounded-card" variant="shimmer" />
          <Skeleton className="h-48 rounded-card" variant="shimmer" />
          <Skeleton className="h-48 rounded-card" variant="shimmer" />
        </div>
      </main>
    </div>
  );
}

const DecksPageContent = dynamic(
  () => import('./DecksPageContent').then((m) => m.default),
  {
    loading: () => <DecksLoadingSkeleton />,
  },
);

export default function DecksPage() {
  return (
    <Suspense fallback={<DecksLoadingSkeleton />}>
      <DecksPageContent />
    </Suspense>
  );
}
