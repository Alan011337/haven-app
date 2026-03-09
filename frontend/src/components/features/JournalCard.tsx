// frontend/src/components/features/JournalCard.tsx
"use client";

import { Journal } from '@/types';
import TarotCard from '@/components/ui/TarotCard';
import { GlassCard } from '@/components/haven/GlassCard';
import { logClientError } from '@/lib/safe-error-log';
import { useDeleteJournal } from '@/hooks/queries';
import { useToast } from '@/hooks/useToast';
import { useConfirm } from '@/hooks/useConfirm';
import { getJournalSafetyBand } from '@/lib/safety';

interface JournalCardProps {
  journal: Journal;
  onDelete?: () => void;
}

export default function JournalCard({ journal, onDelete }: JournalCardProps) {
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
      className={`relative group rounded-card shadow-soft border overflow-hidden transition-all duration-haven ease-haven hover:shadow-lift hover:-translate-y-0.5
      ${isCrisis
        ? 'bg-destructive/5 border-destructive/20'
        : isElevated
          ? 'bg-primary/5 border-primary/15'
          : 'glass-card border-border'
      }`}
    >
      {/* Top accent line */}
      <div className={`absolute top-0 left-0 right-0 h-0.5 ${isCrisis ? 'bg-gradient-to-r from-transparent via-destructive/40 to-transparent' : 'bg-gradient-to-r from-transparent via-primary/30 to-transparent'}`} aria-hidden />

      {/* Delete button */}
      <button
        onClick={handleDelete}
        className="absolute top-5 right-5 z-20 p-2 text-muted-foreground/60 bg-card/80 backdrop-blur-md rounded-full
                   hover:text-destructive hover:bg-destructive/10 border border-transparent hover:border-destructive/20
                   transition-all duration-haven-fast ease-haven opacity-100 md:opacity-0 md:group-hover:opacity-100"
        title="刪除日記"
        aria-label="刪除日記"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
          <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
        </svg>
      </button>

      <div className="p-8 md:p-10">
         {/* Header: date + mood badge */}
         <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 pr-8">
             <div className="flex items-center gap-3">
               <div className="h-8 w-0.5 shrink-0 rounded-full bg-gradient-to-b from-primary/50 to-primary/10" aria-hidden />
               <div className="flex flex-col">
                 <span className={`text-[11px] font-semibold tracking-widest uppercase tabular-nums ${isCrisis ? 'text-destructive' : 'text-muted-foreground/60'}`}>
                    {dateStr}
                 </span>
                 <span className="text-[11px] text-muted-foreground/50 font-medium mt-0.5 tracking-wide tabular-nums">
                    {timeStr}
                 </span>
               </div>
             </div>

             <span className={`inline-flex items-center px-3.5 py-1 rounded-full text-[11px] font-bold self-start sm:self-auto
                ${isCrisis
                  ? 'bg-destructive/10 text-destructive border border-destructive/20'
                  : isElevated
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'bg-primary/8 text-primary/90 border border-primary/15'
                }`}>
                {isCrisis ? '🚨 高風險警示' : isElevated ? '⚠️ 情緒高張' : (journal.mood_label || '隨手記')}
             </span>
         </div>

         {/* Journal content */}
         <div className="mb-8">
           <p className="text-card-foreground leading-[1.85] text-[15px] whitespace-pre-wrap font-sans">
            {journal.content}
           </p>
         </div>

         {/* --- AI Analysis --- */}
         <div className="space-y-4">
          
          {/* 1. 嚴重警示區 (Crisis Mode) */}
          {isSevere && (
            <div className="bg-destructive/10 border border-destructive/30 rounded-xl p-5 animate-slide-up-fade">
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
            <div className="bg-primary/10 border border-border rounded-xl p-4 animate-slide-up-fade shadow-soft">
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
            <div className={`rounded-xl p-4 border animate-slide-up-fade-1 ${isCrisis ? 'bg-destructive/10 border-destructive/20' : 'bg-muted border-border'}`}>
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
             <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {journal.advice_for_user && (
                <div className="bg-primary/10 p-4 rounded-xl border border-border shadow-soft hover:bg-primary/15 hover:shadow-lift transition-all duration-haven ease-haven animate-slide-up-fade-2">
                  <h4 className="text-xs font-bold font-art text-primary mb-2 uppercase tracking-wide flex items-center gap-2">
                    <span className="icon-badge">💡</span>
                    <span>溫馨建議</span>
                  </h4>
                  <div className="list-item-premium mt-1">
                    <p className="text-sm text-foreground leading-relaxed">
                      {journal.advice_for_user}
                    </p>
                  </div>
                </div>
              )}
              
              {journal.action_for_user && (
                <div className="bg-accent/10 p-4 rounded-xl border border-border shadow-soft hover:bg-accent/15 hover:shadow-lift transition-all duration-haven ease-haven animate-slide-up-fade-3">
                  <h4 className="text-xs font-bold font-art text-accent mb-2 uppercase tracking-wide flex items-center gap-2">
                    <span className="icon-badge">🚀</span>
                    <span>小小行動</span>
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

          {/* 4. 伴侶同步指南 */}
          {(journal.advice_for_partner || journal.action_for_partner) && !isSevere && (
            <div className="mt-4 pt-4 animate-slide-up-fade-3">
               <div className="section-divider mb-4" />
               <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs font-bold font-art text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                    <span className="icon-badge">🤝</span>
                    <span>伴侶同步指南</span>
                  </h4>
                  <span className="text-[10px] bg-muted text-muted-foreground px-2 py-0.5 rounded-full border border-border">
                    僅顯示給對方
                  </span>
               </div>
               
              <div className="bg-primary/10 p-4 rounded-xl border border-border space-y-3 shadow-glass-inset">
                 {journal.advice_for_partner && (
                   <div className="list-item-premium flex gap-3 items-start animate-slide-up-fade-4">
                     <span className="shrink-0 text-[10px] font-bold bg-card text-primary px-2 py-0.5 rounded border border-border shadow-soft mt-0.5">
                       建議
                     </span>
                     <p className="text-sm text-foreground leading-relaxed">{journal.advice_for_partner}</p>
                   </div>
                 )}
                 {journal.action_for_partner && (
                   <div className="list-item-premium flex gap-3 items-start animate-slide-up-fade-5">
                     <span className="shrink-0 text-[10px] font-bold bg-card text-primary px-2 py-0.5 rounded border border-border shadow-soft mt-0.5">
                       行動
                     </span>
                     <p className="text-sm text-foreground leading-relaxed">{journal.action_for_partner}</p>
                   </div>
                 )}
              </div>
            </div>
          )}

          {/* 5. Card Recommendation */}
          {!isSevere && journal.card_recommendation && (
            <div className="mt-8 pt-5">
              <div className="section-divider mb-5" />
              <div className="bg-gradient-to-br from-primary to-primary/85 rounded-2xl p-6 md:p-8 text-primary-foreground relative overflow-hidden shadow-lift">
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
