'use client';

import Link from 'next/link';
import { HandHeart } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import { useMediationStatus } from '@/hooks/queries';
import { cn } from '@/lib/utils';

export default function MediationEntryBanner({ className }: { className?: string }) {
  const { data: status, isLoading: loading } = useMediationStatus();
  const inMediation = status?.in_mediation === true;

  if (loading || !inMediation) return null;

  return (
    <GlassCard className={cn('p-4 flex items-center justify-between gap-4 border-primary/20', className)}>
      <div className="flex items-center gap-3">
        <span className="icon-badge !w-10 !h-10" aria-hidden>
          <HandHeart className="w-5 h-5" />
        </span>
        <div>
          <p className="text-body font-art font-medium text-foreground">你們有進行中的調解</p>
          <p className="text-caption text-muted-foreground">填寫三題換位思考，可查看彼此心聲與下次 SOP</p>
        </div>
      </div>
      <Link
        href="/mediation"
        className="shrink-0 rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-t border-t-white/30 px-5 py-2 text-body font-medium shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label="前往調解模式"
      >
        前往填寫
      </Link>
    </GlassCard>
  );
}
