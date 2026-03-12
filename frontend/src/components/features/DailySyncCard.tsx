"use client";

import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Sun, Loader2, Lock, Unlock } from "lucide-react";
import { GlassCard } from "@/components/haven/GlassCard";
import { useDailySyncStatus } from "@/hooks/queries";
import { queryKeys } from "@/lib/query-keys";
import { submitDailySync } from "@/services/api-client";
import { logClientError } from "@/lib/safe-error-log";
import { trackDailySyncSubmitted } from "@/lib/relationship-events";
import { capturePosthogEvent } from "@/lib/posthog";
import { useToast } from "@/hooks/useToast";
import { cn } from "@/lib/utils";

const MOOD_OPTIONS = [
  { value: 1, emoji: '😔', label: '很低落' },
  { value: 2, emoji: '😕', label: '有點悶' },
  { value: 3, emoji: '😐', label: '普通' },
  { value: 4, emoji: '🙂', label: '不錯' },
  { value: 5, emoji: '😊', label: '很開心' },
] as const;

function getMoodEmoji(score: number | null | undefined): string {
  return MOOD_OPTIONS.find((o) => o.value === score)?.emoji ?? '😐';
}

export default function DailySyncCard({ className }: { className?: string }) {
  const queryClient = useQueryClient();
  const { data: status, isLoading: loading } = useDailySyncStatus();
  const [submitting, setSubmitting] = useState(false);
  const [mood, setMood] = useState(3);
  const [answer, setAnswer] = useState("");
  const { showToast } = useToast();

  useEffect(() => {
    if (!status) return;
    capturePosthogEvent("daily_sync_viewed", {
      my_filled: status.my_filled,
      unlocked: status.unlocked,
    });
    if (status.my_filled && status.my_mood_score != null) setMood(status.my_mood_score);
    if (status.my_filled && status.my_answer_text) setAnswer(status.my_answer_text);
  }, [status]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const qId = status?.today_question_id;
    if (!qId) return;
    setSubmitting(true);
    try {
      await submitDailySync({ mood_score: mood, question_id: qId, answer_text: answer.trim() });
      trackDailySyncSubmitted({ mood_score: mood, question_id: qId });
      await queryClient.invalidateQueries({ queryKey: queryKeys.dailySyncStatus() });
      showToast("已儲存今日同步", "success");
    } catch (err) {
      logClientError("daily-sync-submit-failed", err);
      showToast("儲存失敗，請稍後再試", "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <GlassCard className={cn("p-6 flex items-center justify-center min-h-[140px]", className)}>
        <Loader2 className="w-6 h-6 animate-spin text-primary" aria-hidden />
      </GlassCard>
    );
  }

  if (!status) {
    return (
      <GlassCard className={cn("p-6 md:p-8", className)}>
        <h3 className="font-art text-lg font-semibold text-card-foreground mb-2 flex items-center gap-2">
          <span className="icon-badge animate-breathe">
            <Sun className="w-5 h-5 text-primary" aria-hidden />
          </span>
          每日 3 分鐘同步
        </h3>
        <p className="text-sm text-muted-foreground/70 leading-relaxed">
          今日的同步問題正在準備中，稍後即可填寫。
        </p>
      </GlassCard>
    );
  }

  return (
    <GlassCard className={cn("p-6 md:p-8", className)}>
      <h3 className="font-art text-lg font-semibold text-card-foreground mb-2 flex items-center gap-2">
        <span className="icon-badge">
          <Sun className="w-5 h-5 text-primary" aria-hidden />
        </span>
        每日 3 分鐘同步
      </h3>
      {!status.my_filled ? (
        <form onSubmit={handleSubmit} className="space-y-4 animate-slide-up-fade">
          <p className="text-caption text-muted-foreground">{status.today_question_label ?? "今日一問"}</p>
          <div className="animate-slide-up-fade-1">
            <p className="text-body text-foreground font-medium mb-2.5">
              今天的情緒
            </p>
            <div className="flex items-center gap-1.5 sm:gap-2" role="radiogroup" aria-label="情緒評分">
              {MOOD_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  role="radio"
                  aria-checked={mood === opt.value}
                  aria-label={`${opt.label} — ${opt.value} 分`}
                  onClick={() => setMood(opt.value)}
                  className={cn(
                    'group relative flex flex-col items-center gap-1 rounded-2xl px-2.5 py-2 sm:px-3 sm:py-2.5 transition-all duration-haven ease-haven',
                    mood === opt.value
                      ? 'bg-primary/12 ring-2 ring-primary/30 shadow-focus-glow scale-[1.08]'
                      : 'hover:bg-muted/50 hover:scale-105'
                  )}
                >
                  <span className={cn(
                    'text-[1.65rem] sm:text-[1.85rem] transition-all duration-haven ease-haven select-none',
                    mood === opt.value ? '' : 'grayscale-[0.35] opacity-60 group-hover:grayscale-0 group-hover:opacity-100'
                  )}>
                    {opt.emoji}
                  </span>
                  <span className={cn(
                    'text-[10px] font-medium tracking-wide transition-colors duration-haven',
                    mood === opt.value ? 'text-primary' : 'text-muted-foreground/50 group-hover:text-muted-foreground'
                  )}>
                    {opt.label}
                  </span>
                </button>
              ))}
            </div>
          </div>
          <div className="animate-slide-up-fade-2">
            <label htmlFor="daily-answer" className="block text-body text-foreground font-medium mb-1">
              你的回答
            </label>
            <div className="rounded-xl transition-all duration-haven ease-haven focus-within:shadow-focus-glow focus-within:ring-2 focus-within:ring-primary/20">
              <textarea
                id="daily-answer"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="寫一句話..."
                className="w-full rounded-xl border border-input bg-muted/30 px-4 py-3 text-foreground placeholder:text-muted-foreground/50 placeholder:font-light focus-visible:bg-card focus-visible:border-transparent outline-none resize-none min-h-[80px] transition-all duration-haven ease-haven"
                maxLength={1000}
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground px-5 py-2.5 font-medium border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:pointer-events-none"
          >
            {submitting ? "儲存中..." : "送出"}
          </button>
        </form>
      ) : (
        <div className="space-y-3 animate-slide-up-fade">
          <p className="text-body text-foreground flex items-center gap-1.5 flex-wrap">
            <span className="text-xl">{getMoodEmoji(status.my_mood_score)}</span>
            你今日已填寫：情緒 <span className="tabular-nums font-medium">{status.my_mood_score}</span> 分，{status.today_question_label}
          </p>
          <div className="list-item-premium">
            <p className="text-caption text-muted-foreground italic">「{status.my_answer_text}」</p>
          </div>
          {!status.unlocked ? (
            <p className="text-caption text-muted-foreground flex items-center gap-2.5">
              <span className="icon-badge !w-6 !h-6" aria-hidden><Lock className="w-3 h-3" /></span>
              等待伴侶也填寫後即可解鎖對方的回答
            </p>
          ) : (
            <>
              <div className="section-divider" aria-hidden />
              <div className="animate-scale-in rounded-2xl bg-primary/5 border border-primary/10 p-4">
                <p className="text-caption font-medium text-foreground flex items-center gap-2 mb-1">
                  <span className="icon-badge">
                    <Unlock className="w-4 h-4 text-primary" aria-hidden />
                  </span>
                  伴侶今日同步
                </p>
                <p className="text-body text-foreground flex items-center gap-1.5">
                  <span className="text-xl">{getMoodEmoji(status.partner_mood_score)}</span>
                  情緒 <span className="tabular-nums font-medium">{status.partner_mood_score}</span> 分
                </p>
                <div className="list-item-premium mt-2">
                  <p className="text-caption text-muted-foreground italic">「{status.partner_answer_text}」</p>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </GlassCard>
  );
}
