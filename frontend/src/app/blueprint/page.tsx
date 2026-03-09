'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import Skeleton from '@/components/ui/Skeleton';

const BlueprintPageContent = dynamic(
  () => import('./BlueprintPageContent').then((m) => m.default),
  {
    loading: () => (
      <Skeleton className="h-[50vh] w-full rounded-card" aria-label="載入中" />
    ),
  },
);

export default function BlueprintPage() {
  return (
    <div className="min-h-screen bg-muted/40 space-page pb-24">
      <div className="max-w-4xl mx-auto w-full">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground font-medium mb-6 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-button px-2 py-1"
          aria-label="返回首頁"
        >
          <ArrowLeft className="w-5 h-5" aria-hidden />
          回首頁
        </Link>

        <BlueprintPageContent />
      </div>
    </div>
  );
}
