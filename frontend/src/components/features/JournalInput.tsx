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
import { GlassCard } from '@/components/haven/GlassCard';

interface JournalInputProps {
  onJournalCreated: () => void;
}

interface SafetyGuidanceState {
  tier: number;
  adviceForUser?: string;
  actionForUser?: string;
}

export default function JournalInput({ onJournalCreated }: JournalInputProps) {
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

  return (
    <>
      <GlassCard className="mb-8 p-6 md:p-8 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" aria-hidden />
        <form onSubmit={handleSubmit} className="flex flex-col">
          <label htmlFor="journal-content" className="sr-only">
            日記內容
          </label>
          <div className="rounded-xl transition-all duration-haven ease-haven focus-within:shadow-focus-glow focus-within:ring-2 focus-within:ring-primary/20">
            <textarea
              id="journal-content"
              aria-label="日記內容"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="今天發生了什麼事？心情如何？（試著寫寫看，AI 會幫你分析喔...）"
              className="w-full p-5 border border-input bg-muted/30 rounded-xl focus-visible:bg-card focus-visible:border-transparent outline-none resize-none min-h-[140px] text-foreground placeholder:text-muted-foreground/50 placeholder:font-light leading-relaxed transition-all duration-haven ease-haven"
              disabled={isSubmitting}
              maxLength={MAX_JOURNAL_CONTENT_LENGTH}
              suppressHydrationWarning={true}
            />
          </div>
          <div className="pt-4 flex items-center justify-between">
            <p className="text-xs text-muted-foreground/60 font-mono tabular-nums">
              {content.length}/{MAX_JOURNAL_CONTENT_LENGTH}
            </p>
            <button
              type="submit"
              disabled={isSubmitting || !content.trim()}
              className={`px-7 py-2.5 rounded-full font-medium border-t border-t-white/30 bg-gradient-to-b from-primary to-primary/90 text-primary-foreground shadow-satin-button active:scale-95 transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${content.trim() ? 'hover:shadow-lift hover:-translate-y-0.5' : ''}`}
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground" aria-hidden />
                  AI 分析中...
                </span>
              ) : (
                '寫下此刻'
              )}
            </button>
          </div>
        </form>
      </GlassCard>

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
