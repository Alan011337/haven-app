'use client';

import Link from 'next/link';
import { HandHeart } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import Skeleton from '@/components/ui/Skeleton';
import { useMediationStatus } from '@/hooks/queries';
import { cn } from '@/lib/utils';

export default function MediationEntryBanner({ className }: { className?: string }) {
  const { data: status, isLoading: loading } = useMediationStatus();
  const inMediation = status?.in_mediation === true;

  if (loading) {
    return (
      <GlassCard className={cn('p-5 md:p-6 relative overflow-hidden', className)}>
        <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" aria-hidden />
        <div className="flex items-center gap-3">
          <span className="icon-badge !w-9 !h-9" aria-hidden>
            <HandHeart className="w-[18px] h-[18px]" />
          </span>
          <div className="space-y-1.5 flex-1">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-3 w-44" />
          </div>
        </div>
      </GlassCard>
    );
  }

  if (!inMediation) {
    return (
      <GlassCard className={cn('p-5 md:p-6 relative overflow-hidden', className)}>
        <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" aria-hidden />
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="icon-badge !w-9 !h-9 animate-breathe" aria-hidden>
              <HandHeart className="w-[18px] h-[18px]" />
            </span>
            <div>
              <p className="text-body font-art font-medium text-foreground">修復空間</p>
              <p className="text-caption text-muted-foreground/70">目前沒有進行中的調解，一切安好。</p>
            </div>
          </div>
          <Link
            href="/mediation"
            className="shrink-0 rounded-full border border-border bg-white/70 px-4 py-2 text-caption font-medium text-muted-foreground hover:text-card-foreground hover:shadow-soft transition-all duration-haven ease-haven"
            aria-label="前往調解模式"
          >
            前往修復入口
          </Link>
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard className={cn('p-5 md:p-6 relative overflow-hidden border-primary/20', className)}>
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" aria-hidden />
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="icon-badge !w-9 !h-9" aria-hidden>
            <HandHeart className="w-[18px] h-[18px]" />
          </span>
          <div>
            <p className="text-body font-art font-medium text-foreground">你們有進行中的調解</p>
            <p className="text-caption text-muted-foreground">填寫三題換位思考，可查看彼此心聲</p>
          </div>
        </div>
        <Link
          href="/mediation"
          className="shrink-0 rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-t border-t-white/30 px-5 py-2.5 text-body font-semibold shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="前往調解模式"
        >
          前往填寫
        </Link>
      </div>
    </GlassCard>
  );
}
