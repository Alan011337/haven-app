// frontend/src/components/features/JournalCard.tsx
"use client";

import Link from 'next/link';
import { Journal } from '@/types';
import TarotCard from '@/components/ui/TarotCard';
import { GlassCard } from '@/components/haven/GlassCard';
import { logClientError } from '@/lib/safe-error-log';
import { useDeleteJournal } from '@/hooks/queries';
import { useToast } from '@/hooks/useToast';
import { useConfirm } from '@/hooks/useConfirm';
import { getJournalSafetyBand } from '@/lib/safety';
import { buildJournalExcerpt, deriveJournalTitle, extractFirstJournalImage } from '@/lib/journal-format';

interface JournalCardProps {
  journal: Journal;
  onDelete?: () => void;
  variant?: 'default' | 'timeline';
}

export default function JournalCard({
  journal,
  onDelete,
  variant = 'default',
}: JournalCardProps) {
  const { showToast } = useToast();
  const { confirm } = useConfirm();
  const deleteJournalMutation = useDeleteJournal();
  const isDeleting = deleteJournalMutation.isPending;

  // --- 1. 日期時間格式化 ---
  const dateObj = new Date(journal.created_at);
  const dateStr = dateObj.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
  const timeStr = dateObj.toLocaleTimeString('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
  });

  // --- 2. 安全層級判斷 ---
  const safetyBand = getJournalSafetyBand(journal);
  const isElevated = safetyBand === 'elevated';
  const isCrisis = safetyBand === 'severe';
  const isSevere = isCrisis;
  const visibilityLabel =
    journal.visibility === 'PRIVATE'
      ? '私密保存'
      : journal.visibility === 'PRIVATE_LOCAL'
        ? '完全私密（舊版）'
        : journal.visibility === 'PARTNER_ORIGINAL'
          ? '伴侶看原文'
          : journal.visibility === 'PARTNER_ANALYSIS_ONLY'
            ? '伴侶只看分析（舊版）'
            : '伴侶看整理後的版本';
  const title = deriveJournalTitle(journal);
  const excerpt = buildJournalExcerpt(journal.content);
  const firstImageRaw = extractFirstJournalImage(journal.content);
  const firstImageUrl = (() => {
    if (!firstImageRaw) return null;
    if (firstImageRaw.startsWith('attachment:')) {
      const attachmentId = firstImageRaw.replace('attachment:', '').trim();
      return journal.attachments?.find((a) => a.id === attachmentId)?.url ?? null;
    }
    if (firstImageRaw.startsWith('http://') || firstImageRaw.startsWith('https://')) {
      return firstImageRaw;
    }
    return null;
  })();

  // --- 3. 刪除邏輯 ---
  const handleDelete = async () => {
    const shouldDelete = await confirm({
      title: '刪除日記',
      message: '確定要刪除這篇日記嗎？刪除後無法復原。',
      confirmText: '刪除',
      cancelText: '取消',
    });
    if (!shouldDelete) return;

    try {
      await deleteJournalMutation.mutateAsync(journal.id);
      onDelete?.();
    } catch (error) {
      logClientError('journal-card-delete-failed', error);
      showToast('刪除失敗，請稍後再試', 'error');
    }
  };

  // 刪除中的 Loading 狀態
  if (isDeleting) {
    return (
      <GlassCard className="p-8 text-center animate-pulse flex flex-col items-center justify-center min-h-[200px]">
        <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin mb-2" />
        <p className="text-muted-foreground text-sm">正在抹去這段記憶...</p>
      </GlassCard>
    );
  }

  return (
    <article
      className={`relative group overflow-hidden rounded-[2rem] border shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift
      ${isCrisis
        ? 'bg-[linear-gradient(180deg,rgba(255,246,246,0.96),rgba(255,250,249,0.92))] border-destructive/18'
        : isElevated
          ? 'bg-[linear-gradient(180deg,rgba(255,250,245,0.96),rgba(255,252,248,0.92))] border-primary/15'
          : variant === 'timeline'
            ? 'home-surface-paper'
            : 'glass-card border-border'
      }`}
    >
      {/* Top accent line */}
      <div className={`absolute left-0 right-0 top-0 h-px ${isCrisis ? 'bg-gradient-to-r from-transparent via-destructive/32 to-transparent' : 'bg-gradient-to-r from-transparent via-primary/24 to-transparent'}`} aria-hidden />

      {/* Delete button */}
      <button
        onClick={handleDelete}
        className="absolute right-5 top-5 z-20 rounded-full border border-transparent bg-card/80 p-2 text-muted-foreground/60 backdrop-blur-md
                   hover:border-destructive/20 hover:bg-destructive/10 hover:text-destructive
                   transition-all duration-haven-fast ease-haven opacity-100 md:opacity-0 md:group-hover:opacity-100"
        title="刪除日記"
        aria-label="刪除日記"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
          <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
        </svg>
      </button>

      <div className="p-7 md:p-9">
         {/* Header: date + mood badge */}
         <div className="mb-6 flex flex-col justify-between gap-3 pr-8 sm:flex-row sm:items-center">
             <div className="flex items-center gap-3">
               <div className={`h-10 w-0.5 shrink-0 rounded-full ${variant === 'timeline' ? 'bg-gradient-to-b from-primary/32 to-primary/6' : 'bg-gradient-to-b from-primary/42 to-primary/8'}`} aria-hidden />
               <div className="flex flex-col">
                 <span className={`text-[11px] font-semibold uppercase tracking-[0.24em] tabular-nums ${isCrisis ? 'text-destructive' : 'text-muted-foreground/60'}`}>
                    {dateStr}
                 </span>
                 <span className="mt-0.5 text-[11px] font-medium tracking-wide tabular-nums text-muted-foreground/50">
                    {timeStr}
                 </span>
               </div>
             </div>

             <div className="flex flex-wrap items-center gap-2">
               <span className={`inline-flex items-center self-start rounded-full px-3.5 py-1.5 text-[11px] font-bold shadow-soft sm:self-auto
                  ${isCrisis
                    ? 'bg-destructive/10 text-destructive border border-destructive/20'
                    : isElevated
                      ? 'bg-primary/10 text-primary border border-primary/20'
                      : 'bg-primary/8 text-primary/90 border border-primary/15'
                  }`}>
                  {isCrisis ? '🚨 高風險警示' : isElevated ? '⚠️ 情緒高張' : (journal.mood_label || '隨手記')}
               </span>
               <span className="inline-flex items-center rounded-full border border-border/75 bg-white/78 px-3 py-1 text-[11px] font-semibold text-muted-foreground shadow-soft">
                 {visibilityLabel}
               </span>
             </div>
         </div>

         <div className="mb-5 space-y-2">
           <h3 className="font-art text-[1.55rem] leading-tight text-card-foreground">{title}</h3>
           <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
             {(journal.attachments?.length ?? 0) > 0 && <span>{journal.attachments!.length} 張圖片</span>}
             {journal.visibility === 'PARTNER_TRANSLATED_ONLY' && journal.partner_translation_status === 'PENDING' ? <span>整理中</span> : null}
             {journal.visibility === 'PARTNER_TRANSLATED_ONLY' && journal.partner_translation_status === 'FAILED' ? <span>整理暫未完成</span> : null}
           </div>
         </div>

         {/* Journal content */}
         <div className={`mb-8 rounded-[1.7rem] border px-5 py-6 ${variant === 'timeline' ? 'home-surface-ink home-paper-lines border-[rgba(219,204,187,0.4)]' : 'border-white/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.68),rgba(252,248,243,0.7))]'} shadow-glass-inset`}>
            {firstImageUrl ? (
              <div className="mb-4 flex gap-4">
                <div className="shrink-0 overflow-hidden rounded-[1rem]">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={firstImageUrl}
                    alt=""
                    className="max-h-24 max-w-24 object-contain"
                    loading="lazy"
                  />
                </div>
                <p className="line-clamp-4 whitespace-pre-wrap font-sans text-[15px] leading-[2] text-card-foreground">
                  {excerpt}
                </p>
              </div>
            ) : (
              <p className="line-clamp-6 whitespace-pre-wrap font-sans text-[15px] leading-[2] text-card-foreground">
                {excerpt}
              </p>
            )}
         </div>

         <div className="mb-6 flex justify-end">
           <Link
             href={`/journal/${journal.id}`}
             className="inline-flex items-center gap-2 rounded-full border border-white/56 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
           >
             打開 Journal 書房
           </Link>
         </div>

         {/* --- AI Analysis --- */}
         <div className="space-y-4">
          
          {/* 1. 嚴重警示區 (Crisis Mode) */}
          {isSevere && (
            <div className="rounded-[1.4rem] border border-destructive/24 bg-destructive/8 p-5 animate-slide-up-fade">
              <div className="flex items-center text-destructive mb-2 font-bold text-sm">
                <span className="icon-badge !bg-gradient-to-br !from-destructive/12 !to-destructive/4 !border-destructive/8 mr-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </span>
                請優先照顧自己
              </div>
              <p className="text-sm text-foreground mb-3 leading-relaxed">
                系統偵測到目前的情緒能量較高。建議先暫停與伴侶的同步，給自己一些空間喘息。
              </p>
              <div className="flex gap-2 mt-3">
                <span className="stat-box !py-1 !px-2.5 text-xs font-bold text-destructive">
                  安心專線 1925
                </span>
                <span className="stat-box !py-1 !px-2.5 text-xs font-bold text-destructive">
                  保護專線 113
                </span>
              </div>
            </div>
          )}

          {/* 1.5 高壓提醒區 (Tier 1) */}
          {isElevated && !isSevere && (
            <div className="rounded-[1.35rem] border border-primary/14 bg-primary/8 p-4 shadow-soft animate-slide-up-fade">
              <div className="flex items-center text-primary mb-1 font-bold text-sm gap-2.5">
                <span className="icon-badge !w-7 !h-7" aria-hidden>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M4.93 19h14.14c1.54 0 2.5-1.67 1.73-3L13.73 4c-.77-1.33-2.7-1.33-3.47 0L3.2 16c-.77 1.33.19 3 1.73 3z" />
                  </svg>
                </span>
                先放慢一下
              </div>
              <p className="text-sm text-foreground leading-relaxed">
                系統判定目前情緒壓力偏高，建議先做短暫安撫，再進行同步溝通。
              </p>
            </div>
          )}

          {/* 2. 深層需求 (EFT) */}
          {journal.emotional_needs && (
            <div className={`rounded-[1.35rem] border p-4 animate-slide-up-fade-1 ${isCrisis ? 'bg-destructive/8 border-destructive/20' : variant === 'timeline' ? 'bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(251,247,242,0.94))] border-[rgba(219,204,187,0.38)]' : 'bg-white/68 border-white/55'}`}>
              <h4 className={`text-xs font-bold font-art uppercase tracking-wider mb-2 flex items-center gap-2 ${isCrisis ? 'text-destructive' : 'text-muted-foreground'}`}>
                 <span className="icon-badge">{isCrisis ? '🛡️' : '🦁'}</span>
                 <span>{isCrisis ? '安全導航' : '內心深處的渴望'}</span>
              </h4>
              <div className="list-item-premium">
                <p className="text-foreground text-sm font-medium leading-relaxed">
                  {journal.emotional_needs}
                </p>
              </div>
            </div>
          )}

          {/* 3. 建議與行動 (Grid 排版) */}
          {!isSevere && (journal.advice_for_user || journal.action_for_user) && (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {journal.advice_for_user && (
                <div className={`rounded-[1.35rem] border p-4 shadow-soft transition-all duration-haven ease-haven hover:shadow-lift animate-slide-up-fade-2 ${variant === 'timeline' ? 'border-primary/10 bg-primary/[0.065] hover:bg-primary/[0.09]' : 'border-primary/14 bg-primary/8 hover:bg-primary/12'}`}>
                  <h4 className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-primary">
                    <span className="icon-badge !w-6 !h-6">✦</span>
                    <span>給自己的理解</span>
                  </h4>
                  <div className="list-item-premium mt-1">
                    <p className="text-sm text-foreground leading-relaxed">
                      {journal.advice_for_user}
                    </p>
                  </div>
                </div>
              )}
              
              {journal.action_for_user && (
                <div className={`rounded-[1.35rem] border p-4 shadow-soft transition-all duration-haven ease-haven hover:shadow-lift animate-slide-up-fade-3 ${variant === 'timeline' ? 'border-accent/12 bg-accent/[0.065] hover:bg-accent/[0.09]' : 'border-accent/16 bg-accent/8 hover:bg-accent/12'}`}>
                  <h4 className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-accent">
                    <span className="icon-badge !w-6 !h-6">↗</span>
                    <span>接下來的一步</span>
                  </h4>
                  <div className="list-item-premium mt-1">
                    <p className="text-sm text-foreground leading-relaxed">
                      {journal.action_for_user}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 5. Card Recommendation */}
          {!isSevere && journal.card_recommendation && (
            <div className="mt-8 pt-5">
              <div className="section-divider mb-5" />
                <div className="relative overflow-hidden rounded-[1.8rem] bg-gradient-to-br from-primary to-primary/85 p-6 text-primary-foreground shadow-lift md:p-8">
                <div className="absolute top-0 right-0 w-72 h-72 bg-white opacity-[0.04] rounded-full blur-hero-orb -translate-y-1/2 translate-x-1/3" aria-hidden />
                <div className="absolute bottom-0 left-0 w-48 h-48 bg-white opacity-[0.03] rounded-full blur-hero-orb-sm translate-y-1/3 -translate-x-1/4" aria-hidden />
                <div className="flex flex-col-reverse md:flex-row items-center gap-6 relative z-10">
                  <div className="flex-1 text-center md:text-left">
                    <div className="inline-block px-2.5 py-0.5 rounded-full border border-white/20 bg-white/10 text-[10px] font-bold tracking-widest uppercase mb-3">
                      Daily Wisdom
                    </div>
                    <h3 className="text-2xl font-art font-bold text-primary-foreground mb-2">
                      {journal.card_recommendation}
                    </h3>
                    <p className="text-sm text-primary-foreground/85 leading-relaxed font-light">
                      這張牌象徵著你此刻的內在能量。試著點擊這張牌，翻開它所帶來的深層指引與祝福。
                    </p>
                  </div>

                  <div className="perspective-1000">
                    <div className="w-28 h-44 sm:w-32 sm:h-48 relative transition-transform duration-haven ease-haven hover:scale-105 hover:rotate-1">
                       <TarotCard cardName={journal.card_recommendation} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </article>
  );
}
