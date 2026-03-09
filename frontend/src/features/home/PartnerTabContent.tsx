'use client';

import { Heart, RefreshCw } from 'lucide-react';
import PartnerJournalCard from '@/components/features/PartnerJournalCard';
import { GlassCard } from '@/components/haven/GlassCard';
import Skeleton from '@/components/ui/Skeleton';
import PartnerSafetyBanner from '@/components/features/PartnerSafetyBanner';
import { Journal } from '@/types';

interface PartnerTabContentProps {
  partnerJournals: Journal[];
  loading: boolean;
  partnerSafetyBanner: { latestSevereId: string; severeCount: number } | null;
  onRefresh: () => void;
  onDismissSafetyBanner: () => void;
}

export default function PartnerTabContent({
  partnerJournals,
  loading,
  partnerSafetyBanner,
  onRefresh,
  onDismissSafetyBanner,
}: PartnerTabContentProps) {
  return (
    <section>
      <div className="flex items-center justify-between mb-6 px-2">
        <h3 className="text-xl font-art font-bold text-card-foreground flex items-center gap-2.5">
          <span className="flex h-3 w-3 relative" aria-hidden>
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-primary" />
          </span>
          伴侶的心聲
        </h3>
        <button
          onClick={onRefresh}
          className="text-muted-foreground hover:text-card-foreground transition-colors duration-haven-fast ease-haven p-2 hover:bg-muted rounded-button"
          aria-label="重新整理"
        >
          <RefreshCw size={18} />
        </button>
      </div>

      {partnerSafetyBanner && !loading && (
        <PartnerSafetyBanner
          severeCount={partnerSafetyBanner.severeCount}
          onDismiss={onDismissSafetyBanner}
        />
      )}

      {loading ? (
        <div className="space-y-6">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-40 w-full rounded-card" />
          ))}
        </div>
      ) : partnerJournals.length === 0 ? (
        <GlassCard className="flex flex-col items-center justify-center py-24 border border-dashed border-border animate-slide-up-fade">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/12 to-primary/4 border border-primary/8 flex items-center justify-center mb-5 shadow-soft">
            <Heart className="w-10 h-10 text-primary fill-primary/20" aria-hidden />
          </div>
          <p className="text-card-foreground font-art font-semibold text-lg">靜悄悄的...</p>
          <p className="text-muted-foreground text-sm mt-2 max-w-xs text-center leading-relaxed">
            當伴侶寫下日記，這裡會出現 AI 溫柔轉譯後的文字。
          </p>
        </GlassCard>
      ) : (
        <div className="grid gap-8">
          {partnerJournals.map((journal, idx) => (
            <div key={journal.id} className={idx < 5 ? `animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}` : ''}>
              <PartnerJournalCard journal={journal} />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
