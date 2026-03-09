'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { ArrowLeft, BarChart2 } from 'lucide-react';
import Skeleton from '@/components/ui/Skeleton';

const AnalysisContent = dynamic(
  () => import('./AnalysisContent').then((m) => m.default),
  {
    loading: () => (
      <Skeleton className="h-48 w-full rounded-card" variant="shimmer" aria-label="載入中" />
    ),
  },
);

export default function AnalysisPage() {
  return (
    <div className="min-h-screen bg-muted/40 space-page">
      <div className="mx-auto max-w-3xl">
        <div className="mb-8 animate-page-enter">
          <Link
            href="/"
            className="group inline-flex items-center gap-2 rounded-button px-4 py-2 text-caption text-muted-foreground transition-all duration-haven ease-haven hover:bg-card/80 hover:text-card-foreground hover:shadow-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            aria-label="返回首頁"
          >
            <div className="p-1 rounded-full bg-card shadow-soft border border-border/60 group-hover:border-primary/20 transition-all duration-haven ease-haven" aria-hidden>
              <ArrowLeft className="h-3.5 w-3.5" />
            </div>
            回首頁
          </Link>

          <div className="mt-6 flex items-center gap-3">
            <span className="icon-badge !w-10 !h-10 !rounded-2xl" aria-hidden>
              <BarChart2 className="w-5 h-5" />
            </span>
            <div>
              <h1 className="text-title font-art font-bold text-card-foreground tracking-tight">情緒分析</h1>
              <p className="text-caption text-muted-foreground">洞察你們的情感趨勢</p>
            </div>
          </div>
        </div>

        <div className="animate-page-enter-delay-1">
          <AnalysisContent />
        </div>
      </div>
    </div>
  );
}
