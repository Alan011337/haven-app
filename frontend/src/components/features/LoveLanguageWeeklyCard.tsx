"use client";

import { useState, useEffect, useCallback } from "react";
import { Sparkles, Loader2, Check } from "lucide-react";
import { GlassCard } from "@/components/haven/GlassCard";
import { HOME_OPTIONAL_DATA_TIMEOUT_MS } from "@/lib/home-performance";
import {
  fetchWeeklyTask,
  completeWeeklyTask,
  type WeeklyTaskPublic,
} from "@/services/api-client";
import { logClientError } from "@/lib/safe-error-log";
import { useToast } from "@/hooks/useToast";

export default function LoveLanguageWeeklyCard() {
  const [task, setTask] = useState<WeeklyTaskPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState(false);
  const { showToast } = useToast();

  const load = useCallback(async () => {
    try {
      const t = await fetchWeeklyTask({ timeout: HOME_OPTIONAL_DATA_TIMEOUT_MS });
      setTask(t ?? null);
    } catch (e) {
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
      <GlassCard className="mb-6 p-6 flex items-center justify-center min-h-[80px]">
        <Loader2 className="w-6 h-6 animate-spin text-primary" aria-hidden />
      </GlassCard>
    );
  }
  if (!task) return null;

  return (
    <GlassCard className="mb-6 p-6 md:p-8 relative overflow-hidden">
      <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
      <h3 className="font-art text-lg font-semibold text-card-foreground mb-2 flex items-center gap-2">
        <span className="icon-badge">
          <Sparkles className="w-5 h-5 text-primary" aria-hidden />
        </span>
        本週愛之語小任務
      </h3>
      <p className="text-body text-foreground mb-3 animate-slide-up-fade">{task.task_label}</p>
      {task.completed ? (
        <div className="flex items-center gap-2 animate-scale-in">
          <span className="icon-badge">
            <Check className="w-4 h-4 text-primary" aria-hidden />
          </span>
          <p className="text-caption text-muted-foreground font-medium">已完成</p>
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
