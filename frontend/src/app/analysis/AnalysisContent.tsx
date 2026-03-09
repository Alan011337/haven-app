'use client';

import { BarChart2, Sparkles } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';

export default function AnalysisContent() {
  return (
    <GlassCard className="p-12 text-center relative overflow-hidden">
      {/* Top accent line */}
      <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />

      <span
        className="icon-badge !w-16 !h-16 !rounded-2xl mx-auto mb-5 animate-breathe"
        aria-hidden
      >
        <BarChart2 className="h-7 w-7" aria-hidden />
      </span>
      <h1 className="text-title font-art font-bold text-card-foreground tracking-tight">
        情緒分析
      </h1>
      <p className="mt-3 text-body text-muted-foreground leading-relaxed max-w-sm mx-auto">
        這個功能正在優化中，下一版會提供更完整的趨勢與洞察。
      </p>
      <div className="mt-6 inline-flex items-center gap-1.5 text-caption text-primary/60 font-medium">
        <Sparkles className="w-3.5 h-3.5" aria-hidden />
        即將推出
      </div>
    </GlassCard>
  );
}
