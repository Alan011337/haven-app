"use client";

import { useState, useEffect, useCallback } from "react";
import { Sparkles, Loader2, Check, RefreshCw } from "lucide-react";
import { GlassCard } from "@/components/haven/GlassCard";
import { HOME_OPTIONAL_DATA_TIMEOUT_MS } from "@/lib/home-performance";
import {
  fetchWeeklyTask,
  completeWeeklyTask,
  type WeeklyTaskPublic,
} from "@/services/api-client";
import { logClientError } from "@/lib/safe-error-log";
import { useToast } from "@/hooks/useToast";
import { cn } from "@/lib/utils";

export default function LoveLanguageWeeklyCard({ className }: { className?: string }) {
  const [task, setTask] = useState<WeeklyTaskPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [completing, setCompleting] = useState(false);
  const { showToast } = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    setLoadFailed(false);
    try {
      const t = await fetchWeeklyTask({ timeout: HOME_OPTIONAL_DATA_TIMEOUT_MS });
      setTask(t ?? null);
    } catch (e) {
      setTask(null);
      setLoadFailed(true);
      logClientError("weekly-task-fetch-failed", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleComplete = async () => {
    setCompleting(true);
    try {
      const updated = await completeWeeklyTask();
      setTask(updated);
      showToast("已標記本週任務完成", "success");
    } catch (e) {
      logClientError("weekly-task-complete-failed", e);
      showToast("操作失敗，請稍後再試", "error");
    } finally {
      setCompleting(false);
    }
  };

  if (loading) {
    return (
      <GlassCard className={cn("p-6 flex items-center justify-center gap-3 min-h-[80px]", className)}>
        <Loader2 className="w-5 h-5 animate-spin text-primary" aria-hidden />
        <span className="text-caption text-muted-foreground">正在載入本週任務…</span>
      </GlassCard>
    );
  }
  if (!task) {
    if (loadFailed) {
      return (
        <GlassCard className={cn("p-6 md:p-8 relative overflow-hidden", className)}>
          <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" aria-hidden />
          <h3 className="font-art text-lg font-semibold text-card-foreground mb-2 flex items-center gap-2">
            <span className="icon-badge">
              <Sparkles className="w-5 h-5 text-primary" aria-hidden />
            </span>
            本週愛之語小任務
          </h3>
          <p className="text-sm text-muted-foreground/80 leading-relaxed">
            任務資料還在同步，剛剛這次沒有成功載入。這不代表本週沒有任務。
          </p>
          <button
            type="button"
            onClick={load}
            className="mt-4 inline-flex items-center gap-2 rounded-full border border-border bg-white/82 px-4 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift"
          >
            <RefreshCw className="h-4 w-4" aria-hidden />
            重新同步任務
          </button>
        </GlassCard>
      );
    }

    return (
      <GlassCard className={cn("p-6 md:p-8 relative overflow-hidden", className)}>
        <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" aria-hidden />
        <h3 className="font-art text-lg font-semibold text-card-foreground mb-2 flex items-center gap-2">
          <span className="icon-badge animate-breathe">
            <Sparkles className="w-5 h-5 text-primary" aria-hidden />
          </span>
          本週愛之語小任務
        </h3>
        <p className="text-sm text-muted-foreground/70 leading-relaxed">
          完成雙向綁定後，這裡會出現每週愛之語小任務。
        </p>
      </GlassCard>
    );
  }

  return (
    <GlassCard className={cn("p-6 md:p-8 relative overflow-hidden", className)}>
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" aria-hidden />
      <h3 className="font-art text-lg font-semibold text-card-foreground mb-2 flex items-center gap-2">
        <span className="icon-badge">
          <Sparkles className="w-5 h-5 text-primary" aria-hidden />
        </span>
        本週愛之語小任務
      </h3>
      <p className="text-body text-foreground mb-3 leading-relaxed animate-slide-up-fade">{task.task_label}</p>
      {task.completed ? (
        <div className="inline-flex items-center gap-2.5 animate-scale-in rounded-xl bg-primary/6 border border-primary/10 px-3.5 py-2.5">
          <span className="icon-badge !w-6 !h-6">
            <Check className="w-3.5 h-3.5 text-primary" aria-hidden />
          </span>
          <p className="text-caption text-primary font-medium">本週任務已完成 ✓</p>
        </div>
      ) : (
        <button
          type="button"
          onClick={handleComplete}
          disabled={completing}
          className="rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground px-5 py-2.5 font-medium border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:pointer-events-none"
        >
          {completing ? "處理中..." : "標記完成"}
        </button>
      )}
    </GlassCard>
  );
}
