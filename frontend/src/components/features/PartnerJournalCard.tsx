// frontend/src/components/features/PartnerJournalCard.tsx

import React from 'react';
import { Journal } from '@/types';
import ActionCard from "./ActionCard";
import { Sparkles, HeartHandshake, Lightbulb, Lock, ShieldAlert } from 'lucide-react';
import { getJournalSafetyBand } from '@/lib/safety';
import SafetyTierGate from './SafetyTierGate';

interface Props {
  journal: Journal;
}

export default function PartnerJournalCard({ journal }: Props) {
  const date = new Date(journal.created_at).toLocaleDateString('zh-TW', {
    month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  const safetyBand = getJournalSafetyBand(journal);
  const isElevated = safetyBand === 'elevated';
  const isSevere = safetyBand === 'severe';
  const isSafetyConcern = isElevated || isSevere;

  return (
    <SafetyTierGate tier={journal.safety_tier ?? 0}>
    <div className={`
      relative group overflow-hidden
      bg-card rounded-card p-8
      shadow-soft border border-border
      transition-all duration-haven ease-haven hover:shadow-lift hover:-translate-y-1
      ${isSevere ? 'ring-2 ring-destructive/20' : isElevated ? 'ring-2 ring-primary/20' : ''}
    `}>
      <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-b from-primary/5 to-transparent rounded-bl-[100px] opacity-60 pointer-events-none" aria-hidden />

      <div className="relative flex justify-between items-start mb-6">
        <div className="flex items-center gap-4">
          <span className="icon-badge !w-12 !h-12 !rounded-2xl text-xl" aria-hidden>
             😊
          </span>
          <div>
            <div className="text-sm font-medium text-muted-foreground mb-0.5 tabular-nums">{date}</div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold text-foreground font-art">
                心情：{journal.mood_label || '平靜'}
              </span>
              {isSafetyConcern && (
                <span
                  className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-bold ${
                    isSevere ? 'bg-destructive/15 text-destructive' : 'bg-primary/15 text-primary'
                  }`}
                >
                  <ShieldAlert size={12} aria-hidden /> {isSevere ? '安全優先模式' : '需多加關懷'}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground bg-muted px-3 py-1.5 rounded-full border border-border">
          <span>🔒</span>
          <span>原文已隱私保護</span>
        </div>
      </div>

      <div className="relative mb-8 p-6 bg-primary/5 rounded-2xl border border-border shadow-soft shadow-glass-inset">
        <Sparkles className="absolute -top-3 -left-2 text-primary/50 w-8 h-8" aria-hidden />
        <h4 className="text-xs font-bold text-primary uppercase tracking-widest mb-3 ml-1 font-art">
          {isSevere ? '安全導航' : '內在需求'}
        </h4>
        <p className="text-xl text-foreground font-medium leading-relaxed font-art italic">
          &quot;{journal.emotional_needs || '希望能被理解與支持'}&quot;
        </p>
      </div>

      {isSevere && (
        <div className="mb-8 bg-destructive/5 border border-destructive/20 p-5 rounded-2xl animate-slide-up-fade">
          <h4 className="text-sm font-bold text-destructive mb-2 flex items-center gap-2.5">
            <span className="icon-badge !w-7 !h-7 !bg-gradient-to-br !from-destructive/12 !to-destructive/4 !border-destructive/8" aria-hidden><ShieldAlert size={14} /></span>
            高風險提醒：先確認安全，再談溝通
          </h4>
          <p className="text-sm text-destructive/90 leading-relaxed mb-3">
            系統偵測到目前情緒張力偏高。建議先降低刺激、確認彼此安全，暫停深度討論。
          </p>
          <div className="flex flex-wrap gap-2 mb-3">
            <a
              href="tel:1925"
              className="text-xs font-bold text-destructive bg-card px-2 py-1 rounded border border-border hover:bg-destructive/10 transition-colors duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              安心專線 1925
            </a>
            <a
              href="tel:113"
              className="text-xs font-bold text-destructive bg-card px-2 py-1 rounded border border-border hover:bg-destructive/10 transition-colors duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              保護專線 113
            </a>
          </div>

          {(journal.action_for_partner || journal.advice_for_partner) && (
            <div className="bg-card/80 border border-border rounded-xl p-4 space-y-2 shadow-glass-inset">
              {journal.action_for_partner && (
                <p className="text-sm text-destructive">
                  <span className="font-bold mr-1">行動：</span>
                  {journal.action_for_partner}
                </p>
              )}
              {journal.advice_for_partner && (
                <p className="text-sm text-destructive">
                  <span className="font-bold mr-1">建議：</span>
                  {journal.advice_for_partner}
                </p>
              )}
            </div>
          )}

          <div className="mt-3 rounded-xl border border-border bg-card/80 px-3 py-2 text-xs text-destructive flex items-center gap-2 font-semibold shadow-glass-inset">
            <span className="icon-badge !w-5 !h-5 !bg-gradient-to-br !from-destructive/12 !to-destructive/4 !border-destructive/8" aria-hidden><Lock size={10} /></span>
            高風險模式已啟用：暫停暖心小行動推薦，優先安全與降壓。
          </div>
        </div>
      )}

      {/* --- Grid Layout for Recommendations --- */}
      {!isSevere && <div className="grid md:grid-cols-2 gap-6">

        {/* 左側：AI 推薦行動卡片 */}
        {journal.card_recommendation && (
            <div className="flex flex-col h-full animate-slide-up-fade-1">
              <h4 className="flex items-center gap-2.5 text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3 font-art">
                <span className="icon-badge !w-6 !h-6" aria-hidden><HeartHandshake size={12} /></span> 暖心小行動
              </h4>
              <div className="flex-1">
                 <ActionCard cardKey={journal.card_recommendation} />
              </div>
            </div>
        )}

        {/* 右側：具體建議文字 */}
        <div className="space-y-4 animate-slide-up-fade-2">
            {journal.action_for_partner && (
              <div className="bg-accent/10 p-4 rounded-2xl border border-border shadow-soft">
                <h4 className="flex items-center gap-2.5 text-sm font-bold text-accent mb-2">
                  <span className="icon-badge !w-6 !h-6 !bg-gradient-to-br !from-accent/12 !to-accent/4 !border-accent/8" aria-hidden><div className="w-1.5 h-1.5 rounded-full bg-accent" /></span>
                  具體做法
                </h4>
                <p className="text-foreground/90 text-sm leading-relaxed text-justify">
                  {journal.action_for_partner}
                </p>
              </div>
            )}

            {journal.advice_for_partner && (
              <div className="bg-primary/10 p-4 rounded-2xl border border-border shadow-soft">
                <h4 className="flex items-center gap-2.5 text-sm font-bold text-primary mb-2">
                  <span className="icon-badge !w-6 !h-6" aria-hidden><Lightbulb size={12} /></span>
                  理解視角
                </h4>
                <p className="text-foreground/90 text-sm leading-relaxed text-justify">
                  {journal.advice_for_partner}
                </p>
              </div>
            )}
        </div>
      </div>}
    </div>
    </SafetyTierGate>
  );
}
