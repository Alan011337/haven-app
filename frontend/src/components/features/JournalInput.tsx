// frontend/src/components/features/JournalInput.tsx
"use client";

import { isAxiosError } from 'axios';
import { useEffect, useState } from 'react';
import { AlertTriangle, PhoneCall, Shield } from 'lucide-react';

import { trackJournalSubmit } from '@/lib/cuj-events';
import { applyOptimisticPatch, rollbackOptimisticPatch } from '@/lib/optimistic-ui';
import { useCreateJournal } from '@/hooks/queries';
import { logClientError } from '@/lib/safe-error-log';
import { MAX_JOURNAL_CONTENT_LENGTH } from '@/services/api-client';
import { useToast } from '@/hooks/useToast';
import { resolveSafetyBand } from '@/lib/safety';
import { isNetworkError } from '@/lib/offline-queue/network';
import { enqueue } from '@/lib/offline-queue/queue';
import { HomeComposerStage } from '@/features/home/HomePrimitives';
import { cn } from '@/lib/utils';

interface JournalInputProps {
  onJournalCreated: () => void;
  className?: string;
  variant?: 'default' | 'cover';
}

interface SafetyGuidanceState {
  tier: number;
  adviceForUser?: string;
  actionForUser?: string;
}

export default function JournalInput({
  onJournalCreated,
  className,
  variant = 'default',
}: JournalInputProps) {
  const [content, setContent] = useState('');
  const [safetyGuidance, setSafetyGuidance] = useState<SafetyGuidanceState | null>(null);
  const { showToast } = useToast();
  const createJournalMutation = useCreateJournal();
  const isSubmitting = createJournalMutation.isPending;

  useEffect(() => {
    if (!safetyGuidance) {
      return;
    }

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSafetyGuidance(null);
      }
    };
    window.addEventListener('keydown', onKeyDown);

    return () => {
      window.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [safetyGuidance]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    // UX-SPEED-01: optimistic clear of input; rollback on failure
    const snapshot = applyOptimisticPatch(
      { content, isSubmitting: false },
      (s) => ({ ...s, content: '', isSubmitting: true }),
    );
    setContent(snapshot.nextState.content);

    const operationId =
      typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
        ? crypto.randomUUID()
        : `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    trackJournalSubmit({ content_length: content.trim().length }, operationId);

    try {
      const result = await createJournalMutation.mutateAsync({
        content,
        options: { requestId: operationId, idempotencyKey: operationId },
      });

      if (result) {
        const safetyTier = Number(result.safety_tier ?? 0);
        const safetyBand = resolveSafetyBand(result.safety_tier);
        setContent('');
        onJournalCreated();

        if (safetyBand === 'severe') {
          setSafetyGuidance({
            tier: safetyTier,
            adviceForUser: result.advice_for_user,
            actionForUser: result.action_for_user,
          });
          showToast('已啟動安全引導模式，先照顧好自己。', 'info');
        } else if (safetyBand === 'elevated') {
          showToast('系統偵測你現在有些緊繃，先慢一點也沒關係。', 'info');
        }
      }
    } catch (error) {
      logClientError('journal-input-submit-failed', error);
      if (isNetworkError(error)) {
        try {
          await enqueue(operationId, 'journal_create', { content: content.trim() });
          setContent('');
          onJournalCreated();
          showToast('已存到離線，連線後會自動同步', 'info');
        } catch {
          const rolled = rollbackOptimisticPatch(snapshot.rollbackState);
          setContent(rolled.content);
          showToast('離線佇列已滿，請連線後再試', 'error');
        }
        return;
      }
      const rolled = rollbackOptimisticPatch(snapshot.rollbackState);
      setContent(rolled.content);
      if (isAxiosError(error)) {
        showToast(error.response?.data?.detail || '發布失敗，請稍後再試', 'error');
        return;
      }
      if (error instanceof Error) {
        showToast(error.message, 'error');
      } else {
        showToast('AI 分析服務連線失敗，請確認後端是否啟動', 'error');
      }
    }
  };

  const form = (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          <span className="inline-flex items-center rounded-full border border-primary/15 bg-primary/8 px-3 py-1 text-[11px] font-semibold tracking-[0.2em] text-primary uppercase">
            Private Page
          </span>
          <span className="inline-flex items-center rounded-full border border-border/80 bg-white/70 px-3 py-1 text-[11px] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
            AI 會在背景安靜整理
          </span>
        </div>
        <p className="font-mono text-xs tabular-nums text-muted-foreground/70">
          {content.length}/{MAX_JOURNAL_CONTENT_LENGTH}
        </p>
      </div>

      <label htmlFor="journal-content" className="sr-only">
        日記內容
      </label>
      <div
        className={cn(
          'relative overflow-hidden rounded-[1.85rem] border shadow-soft',
          variant === 'cover'
            ? 'home-surface-paper home-paper-lines border-[rgba(219,204,187,0.5)]'
            : 'border-white/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.82),rgba(250,246,241,0.78))]',
        )}
      >
        {variant !== 'cover' ? (
          <div className="absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-primary/22 to-transparent" aria-hidden />
        ) : null}
        <textarea
          id="journal-content"
          aria-label="日記內容"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="今天發生了什麼事？你最希望被怎麼理解？不用寫得完整，只要先留下一句最真的感受。"
          className={cn(
            'relative z-10 w-full resize-none bg-transparent text-[15px] leading-[2] text-foreground outline-none transition-all duration-haven ease-haven placeholder:font-light placeholder:text-muted-foreground/50 md:px-6',
            variant === 'cover' ? 'min-h-[320px] px-6 py-8 md:min-h-[360px] md:px-7' : 'min-h-[220px] px-5 py-6',
            'focus-visible:bg-white/35',
          )}
          disabled={isSubmitting}
          maxLength={MAX_JOURNAL_CONTENT_LENGTH}
          suppressHydrationWarning={true}
        />
      </div>

      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="max-w-xl space-y-1.5">
          <p className="text-[0.68rem] uppercase tracking-[0.28em] text-primary/80">Editorial Note</p>
          <p className="text-sm leading-7 text-muted-foreground">
            {variant === 'cover'
              ? '先把今天寫成一頁，再讓 AI 在背景安靜協助整理。首頁這一層不追求完整，只追求真實。'
              : '先寫下去就好。提交後，AI 會在背景協助整理情緒層次與後續建議，不需要你一次把所有話都說完。'}
          </p>
        </div>

        <button
          type="submit"
          disabled={isSubmitting || !content.trim()}
          className={`inline-flex items-center justify-center gap-2 rounded-full border-t border-t-white/30 bg-gradient-to-b from-primary to-primary/90 px-8 py-3 font-medium text-primary-foreground shadow-satin-button transition-all duration-haven ease-haven active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${content.trim() ? 'hover:-translate-y-0.5 hover:shadow-lift' : ''}`}
        >
          {isSubmitting ? (
            <>
              <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground" aria-hidden />
              AI 分析中…
            </>
          ) : (
            '收藏這篇日記'
          )}
        </button>
      </div>
    </form>
  );

  return (
    <>
      {variant === 'cover' ? (
        <div className={cn('space-y-4', className)}>
          <div className="flex flex-wrap items-center justify-between gap-3 px-1">
            <div className="space-y-1">
              <p className="text-[0.72rem] uppercase tracking-[0.34em] text-primary/80">Cover Story</p>
              <h3 className="font-art text-[1.9rem] leading-tight text-card-foreground md:text-[2.25rem]">
                首頁現在留給你一整頁，慢慢把今天寫下來。
              </h3>
            </div>
            <div className="rounded-full border border-white/50 bg-white/66 px-3 py-2 text-[0.68rem] uppercase tracking-[0.28em] text-primary/75 shadow-soft">
              稿紙模式
            </div>
          </div>
          {form}
        </div>
      ) : (
        <HomeComposerStage
          eyebrow="Composer Stage"
          title="寫下今天真正想被理解的那一段。"
          description="這裡不是社群貼文，也不是任務欄位。它更像一頁正準備被排版的私人稿件。"
          className={className}
        >
          {form}
        </HomeComposerStage>
      )}

      {safetyGuidance && (
        <div className="fixed inset-0 z-[130] bg-black/45 backdrop-blur-sm p-4 flex items-center justify-center">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="safety-guidance-title"
            className="w-full max-w-xl bg-card rounded-card shadow-modal border border-border overflow-hidden"
          >
            <div className="px-6 py-5 bg-gradient-to-b from-primary to-primary/90 text-primary-foreground">
              <div className="flex items-center gap-2.5">
                <span className="icon-badge !w-8 !h-8 !bg-white/15 !border-white/20" aria-hidden><AlertTriangle className="w-4 h-4" /></span>
                <h3 id="safety-guidance-title" className="text-lg font-art font-bold">
                  先把安全放在第一位
                </h3>
              </div>
              <p className="text-sm text-primary-foreground/90 mt-2 leading-relaxed">
                系統偵測到你現在承受的情緒張力偏高。先安頓自己，再慢慢處理後續對話。
              </p>
            </div>

            <div className="p-6 space-y-4">
              <div className="rounded-2xl border border-border bg-destructive/10 p-4 animate-slide-up-fade">
                <p className="text-sm font-semibold text-destructive mb-2 flex items-center gap-2.5">
                  <span className="icon-badge !w-6 !h-6 !bg-gradient-to-br !from-destructive/12 !to-destructive/4 !border-destructive/8" aria-hidden><Shield className="w-3 h-3" /></span>
                  安全優先建議（Tier {safetyGuidance.tier}）
                </p>
                <p className="text-sm text-foreground leading-relaxed">
                  {safetyGuidance.actionForUser || '請先離開高壓情境、深呼吸，優先確認自身安全。'}
                </p>
              </div>

              {safetyGuidance.adviceForUser && (
                <div className="rounded-2xl border border-border bg-muted p-4 animate-slide-up-fade-1">
                  <p className="text-xs font-art font-bold text-muted-foreground uppercase tracking-wider mb-1.5">AI 引導</p>
                  <p className="text-sm text-foreground leading-relaxed">{safetyGuidance.adviceForUser}</p>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 animate-slide-up-fade-2">
                <a
                  href="tel:1925"
                  className="inline-flex items-center justify-center gap-2.5 rounded-xl border border-border bg-destructive/10 px-4 py-3 text-sm font-bold text-destructive hover:bg-destructive/20 hover:shadow-soft transition-all duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="icon-badge !w-6 !h-6 !bg-gradient-to-br !from-destructive/12 !to-destructive/4 !border-destructive/8" aria-hidden><PhoneCall className="w-3 h-3" /></span>
                  安心專線 1925
                </a>
                <a
                  href="tel:113"
                  className="inline-flex items-center justify-center gap-2.5 rounded-xl border border-border bg-primary/10 px-4 py-3 text-sm font-bold text-primary hover:bg-primary/20 hover:shadow-soft transition-all duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="icon-badge !w-6 !h-6" aria-hidden><PhoneCall className="w-3 h-3" /></span>
                  保護專線 113
                </a>
              </div>

              <div className="pt-1 flex justify-end">
                <button
                  type="button"
                  onClick={() => setSafetyGuidance(null)}
                  className="rounded-xl bg-gradient-to-b from-primary to-primary/90 text-primary-foreground px-5 py-2.5 text-sm font-medium border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-95 transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  我知道了
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
