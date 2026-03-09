"use client";

import { useState, useEffect, useCallback } from "react";
import { Heart, Loader2 } from "lucide-react";
import { GlassCard } from "@/components/haven/GlassCard";
import {
  fetchAppreciations,
  createAppreciation,
  type AppreciationPublic,
} from "@/services/api-client";
import { logClientError } from "@/lib/safe-error-log";
import { trackAppreciationSent } from "@/lib/relationship-events";
import { capturePosthogEvent } from "@/lib/posthog";
import { useToast } from "@/hooks/useToast";

function getWeekRange(): { from: string; to: string } {
  const now = new Date();
  const day = now.getDay();
  const mon = new Date(now);
  mon.setDate(now.getDate() - (day === 0 ? 6 : day - 1));
  const sun = new Date(mon);
  sun.setDate(mon.getDate() + 6);
  return {
    from: mon.toISOString().slice(0, 10),
    to: sun.toISOString().slice(0, 10),
  };
}

export default function AppreciationCard() {
  const [list, setList] = useState<AppreciationPublic[]>([]);
  const [weekList, setWeekList] = useState<AppreciationPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [loopCompletedToday, setLoopCompletedToday] = useState(false);
  const [text, setText] = useState("");
  const { showToast } = useToast();

  const load = useCallback(async () => {
    try {
      const { from, to } = getWeekRange();
      const [data, weekData] = await Promise.all([
        fetchAppreciations({ limit: 20 }),
        fetchAppreciations({ from_date: from, to_date: to, limit: 50 }),
      ]);
      setList(data);
      setWeekList(weekData);
      capturePosthogEvent("appreciation_viewed", {
        list_count: data.length,
        week_list_count: weekData.length,
      });
    } catch (e) {
      logClientError("appreciation-fetch-failed", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

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
      await load();
      showToast("感恩便利貼已送出", "success");
      if (completed) {
        showToast("今日連結循環完成，做得很好", "success");
      }
    } catch (err) {
      logClientError("appreciation-create-failed", err);
      showToast("送出失敗，請稍後再試", "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <GlassCard className="mb-6 p-6 flex items-center justify-center min-h-[100px]">
        <Loader2 className="w-6 h-6 animate-spin text-primary" aria-hidden />
      </GlassCard>
    );
  }

  return (
    <GlassCard className="mb-6 p-6 md:p-8">
      <h3 className="font-art text-lg font-semibold text-card-foreground mb-2 flex items-center gap-2">
        <span className="icon-badge">
          <Heart className="w-5 h-5 text-primary" aria-hidden />
        </span>
        感恩便利貼
      </h3>
      <p className="text-caption text-muted-foreground mb-4">寫一句具體感謝給對方</p>
      <form onSubmit={handleSubmit} className="flex gap-2 mb-4">
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
          className="flex-1 rounded-input border border-input bg-muted/30 px-4 py-2.5 text-foreground placeholder:text-muted-foreground/50 placeholder:font-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:shadow-focus-glow focus-visible:border-transparent focus-visible:bg-card transition-all duration-haven ease-haven"
        />
        <button
          type="submit"
          disabled={submitting || !text.trim()}
          className="rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground px-5 py-2 font-medium border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:pointer-events-none"
        >
          {submitting ? "送出中..." : "送出"}
        </button>
      </form>
      {(weekList.length > 0 || list.length > 0) && (
        <>
          <div className="section-divider" aria-hidden />
          <div className="space-y-2 mt-3">
            <p className="text-caption font-art font-medium text-muted-foreground tracking-wide">
              {weekList.length > 0 ? "本週感恩回顧" : "近期回顧"}
            </p>
            <ul className="space-y-1.5">
              {(weekList.length > 0 ? weekList : list.slice(0, 5)).map((a) => (
                <li
                  key={a.id}
                  className="list-item-premium"
                >
                  <span className="text-body text-foreground/90">{a.body_text}</span>
                  <span className="text-caption text-muted-foreground ml-2 tabular-nums">
                    {new Date(a.created_at).toLocaleDateString("zh-TW")}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
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
