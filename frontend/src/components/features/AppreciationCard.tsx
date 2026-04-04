"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Heart, Loader2, RefreshCw } from "lucide-react";
import { GlassCard } from "@/components/haven/GlassCard";
import { useHomeAppreciationHistory } from "@/hooks/queries";
import { HOME_APPRECIATION_HISTORY_QUERY_KEY_PREFIX } from "@/lib/home-appreciation-history";
import { createAppreciation } from "@/services/api-client";
import { logClientError } from "@/lib/safe-error-log";
import { trackAppreciationSent } from "@/lib/relationship-events";
import { capturePosthogEvent } from "@/lib/posthog";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/useToast";
import { cn } from "@/lib/utils";

const APPRECIATION_EMOJIS = ['💛', '🌸', '✨', '🤝', '☕', '🌿', '💕', '🫶'];

export default function AppreciationCard({ className }: { className?: string }) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { data, isLoading, isError, refetch } = useHomeAppreciationHistory();
  const partnerLabel = user?.partner_nickname || user?.partner_name || "對方";
  const [submitting, setSubmitting] = useState(false);
  const [loopCompletedToday, setLoopCompletedToday] = useState(false);
  const [text, setText] = useState("");
  const { showToast } = useToast();

  const recentList = data?.recent ?? [];
  const weekList = data?.thisWeek ?? [];
  const historyList = weekList.length > 0 ? weekList : recentList.slice(0, 5);

  useEffect(() => {
    if (!data) return;
    capturePosthogEvent("appreciation_viewed", {
      list_count: data.recent.length,
      week_list_count: data.thisWeek.length,
    });
  }, [data]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;
    setSubmitting(true);
    try {
      await createAppreciation(trimmed);
      const completed = await trackAppreciationSent({ content_length: trimmed.length });
      setLoopCompletedToday(completed);
      setText("");
      await queryClient.invalidateQueries({ queryKey: HOME_APPRECIATION_HISTORY_QUERY_KEY_PREFIX });
      await refetch();
      showToast("這句感謝已送出。", "success");
      if (completed) {
        showToast("今日連結循環完成，做得很好", "success");
      }
    } catch (err) {
      logClientError("appreciation-create-failed", err);
      showToast("這句感謝這次沒有順利送出。", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <GlassCard className={cn("p-6 md:p-8", className)}>
      <h3 className="mb-2 flex items-center gap-2 font-art text-lg font-semibold text-card-foreground">
        <span className="icon-badge">
          <Heart className="h-5 w-5 text-primary" aria-hidden />
        </span>
        感恩便利貼
      </h3>
      <p className="mb-4 text-caption text-muted-foreground">寫一句具體感謝給對方</p>

      <form onSubmit={handleSubmit} className="mb-4 flex gap-2">
        <label htmlFor="appreciation-text" className="sr-only">
          感恩內容
        </label>
        <input
          id="appreciation-text"
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="例如：謝謝你今天幫我買咖啡"
          maxLength={500}
          className="flex-1 rounded-input border border-input bg-muted/30 px-4 py-2.5 text-foreground placeholder:text-muted-foreground/50 placeholder:font-light transition-all duration-haven ease-haven focus-visible:border-transparent focus-visible:bg-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:shadow-focus-glow"
        />
        <button
          type="submit"
          disabled={submitting || !text.trim()}
          className="rounded-full border-t border-t-white/30 bg-gradient-to-b from-primary to-primary/90 px-5 py-2 text-primary-foreground shadow-satin-button transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
        >
          {submitting ? "送出中..." : "送出"}
        </button>
      </form>

      <div className="section-divider" aria-hidden />
      <div className="mt-3 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-caption font-art font-medium tracking-wide text-muted-foreground">
            {weekList.length > 0 ? "本週感恩回顧" : "近期回顧"}
          </p>
          {isError ? (
            <button
              type="button"
              onClick={() => {
                void refetch();
              }}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-white/82 px-3 py-1.5 text-xs font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden />
              重新載入
            </button>
          ) : null}
        </div>

        {isLoading ? (
          <div className="space-y-2 rounded-[1.4rem] border border-border/55 bg-white/72 p-4 shadow-soft">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden />
              正在整理近期感恩紀錄…
            </div>
            {[1, 2, 3].map((row) => (
              <div
                key={row}
                className="h-10 rounded-2xl bg-[linear-gradient(90deg,rgba(244,238,231,0.55),rgba(255,255,255,0.86),rgba(244,238,231,0.55))] animate-pulse"
              />
            ))}
          </div>
        ) : isError ? (
          <div className="rounded-[1.4rem] border border-amber-200/65 bg-amber-50/70 p-4 text-sm leading-relaxed text-muted-foreground shadow-soft">
            歷史紀錄這次沒有成功同步，這不代表你們沒有感恩便利貼。你仍然可以先寫下今天的新感謝。
          </div>
        ) : historyList.length > 0 ? (
          <ul className="space-y-1.5">
            {historyList.map((item, idx) => (
              <li key={item.id} className="list-item-premium group">
                <span
                  className="mr-1.5 text-sm opacity-60 transition-opacity duration-haven group-hover:opacity-100"
                  aria-hidden
                >
                  {APPRECIATION_EMOJIS[idx % APPRECIATION_EMOJIS.length]}
                </span>
                <span className="text-body text-foreground/90">{item.body_text}</span>
                <span className="ml-auto flex shrink-0 items-center gap-2 pl-2">
                  <span className={cn(
                    "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                    item.is_mine
                      ? "bg-primary/10 text-primary"
                      : "bg-accent/10 text-accent"
                  )}>
                    {item.is_mine ? `你寫給 ${partnerLabel}` : `${partnerLabel} 寫給你`}
                  </span>
                  <span className="text-caption tabular-nums text-muted-foreground">
                    {new Date(item.created_at).toLocaleDateString("zh-TW")}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="rounded-[1.4rem] border border-border/55 bg-white/72 p-4 text-sm leading-relaxed text-muted-foreground shadow-soft">
            寫下第一張感恩便利貼後，這裡就會保留你們最近的感謝。
          </div>
        )}
      </div>

      {loopCompletedToday ? (
        <>
          <div className="section-divider" aria-hidden />
          <div className="mt-3 stat-box animate-scale-in">
            <p className="text-body font-medium text-foreground">今日連結循環已完成</p>
            <p className="text-caption text-muted-foreground">
              你們已完成同步、抽卡回應與欣賞，系統已記錄 daily loop completion。
            </p>
          </div>
        </>
      ) : null}
    </GlassCard>
  );
}
