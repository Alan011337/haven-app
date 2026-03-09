"use client";

import { useState, useEffect, useCallback } from "react";
import { Target, Loader2 } from "lucide-react";
import { GlassCard } from "@/components/haven/GlassCard";
import {
  fetchBaseline,
  upsertBaseline,
  fetchCoupleGoal,
  setCoupleGoal,
  BASELINE_DIMENSIONS,
  COUPLE_GOAL_SLUGS,
  type CoupleGoalPublic,
} from "@/services/api-client";
import { logClientError } from "@/lib/safe-error-log";
import { useToast } from "@/hooks/useToast";

const DIMENSION_LABELS: Record<string, string> = {
  intimacy: "親密感",
  conflict: "衝突處理",
  trust: "信任",
  communication: "溝通",
  commitment: "承諾",
};

const GOAL_LABELS: Record<string, string> = {
  reduce_argument: "減少爭吵",
  increase_intimacy: "提升親密感",
  better_communication: "更好溝通",
  more_trust: "更多信任",
  other: "其他",
};

export default function RelationshipRadarCard() {
  const [goal, setGoal] = useState<CoupleGoalPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingBaseline, setSavingBaseline] = useState(false);
  const [savingGoal, setSavingGoal] = useState(false);
  const [scores, setScores] = useState<Record<string, number>>(
    Object.fromEntries(BASELINE_DIMENSIONS.map((d) => [d, 3]))
  );
  const [selectedGoal, setSelectedGoal] = useState<string>("");
  const { showToast } = useToast();

  const load = useCallback(async () => {
    try {
      const [base, g] = await Promise.all([fetchBaseline(), fetchCoupleGoal()]);
      setGoal(g);
      if (base.mine?.scores) setScores(base.mine.scores);
      if (g) setSelectedGoal(g.goal_slug);
    } catch (e) {
      logClientError("relationship-radar-fetch-failed", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSaveBaseline = async () => {
    setSavingBaseline(true);
    try {
      await upsertBaseline(scores);
      showToast("關係雷達已儲存", "success");
    } catch (e) {
      logClientError("relationship-radar-save-failed", e);
      showToast("儲存失敗，請稍後再試", "error");
    } finally {
      setSavingBaseline(false);
    }
  };

  const handleSaveGoal = async () => {
    if (!selectedGoal) return;
    setSavingGoal(true);
    try {
      const next = await setCoupleGoal(selectedGoal);
      setGoal(next);
      showToast("北極星目標已儲存", "success");
    } catch (e) {
      logClientError("couple-goal-save-failed", e);
      showToast("儲存失敗，請稍後再試", "error");
    } finally {
      setSavingGoal(false);
    }
  };

  if (loading) {
    return (
      <GlassCard className="max-w-4xl mx-auto w-full mb-6 p-6 flex items-center justify-center min-h-[120px]">
        <Loader2 className="w-6 h-6 animate-spin text-primary" aria-hidden />
      </GlassCard>
    );
  }

  return (
    <GlassCard className="max-w-4xl mx-auto w-full mb-6 p-6 md:p-8 relative overflow-hidden">
      <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
      <h2 className="text-title font-art font-semibold text-foreground mb-2 flex items-center gap-2">
        <span className="icon-badge">
          <Target className="w-5 h-5 text-primary" aria-hidden />
        </span>
        關係雷達與北極星目標
      </h2>
      <p className="text-caption text-muted-foreground mb-4">
        用 1 分鐘填寫 5 個維度（1–5 分），並共同選擇一個核心目標。
      </p>

      <section className="space-y-3 mb-6 animate-slide-up-fade">
        <h3 className="text-body font-art font-medium text-foreground flex items-center gap-2">五維度短量表</h3>
        {BASELINE_DIMENSIONS.map((dim) => (
          <div key={dim}>
            <label htmlFor={`baseline-${dim}`} className="block text-caption text-muted-foreground mb-1">
              {DIMENSION_LABELS[dim] ?? dim}
            </label>
            <select
              id={`baseline-${dim}`}
              value={scores[dim] ?? 3}
              onChange={(e) => setScores((s) => ({ ...s, [dim]: Number(e.target.value) }))}
              className="select-premium w-full max-w-xs"
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
        ))}
        <button
          type="button"
          onClick={handleSaveBaseline}
          disabled={savingBaseline}
          className="rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground px-5 py-2.5 font-medium border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:pointer-events-none"
        >
          {savingBaseline ? "儲存中..." : "儲存關係雷達"}
        </button>
      </section>

      <div className="section-divider" aria-hidden />

      <section className="space-y-3 animate-slide-up-fade-1">
        <h3 className="text-body font-art font-medium text-foreground flex items-center gap-2">北極星目標</h3>
        <label htmlFor="couple-goal" className="sr-only">
          選擇核心目標
        </label>
        <select
          id="couple-goal"
          value={selectedGoal}
          onChange={(e) => setSelectedGoal(e.target.value)}
          className="select-premium w-full max-w-xs"
        >
          <option value="">請選擇</option>
          {COUPLE_GOAL_SLUGS.map((slug) => (
            <option key={slug} value={slug}>
              {GOAL_LABELS[slug] ?? slug}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={handleSaveGoal}
          disabled={savingGoal || !selectedGoal}
          className="rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground px-5 py-2.5 font-medium border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:pointer-events-none"
        >
          {savingGoal ? "儲存中..." : "儲存目標"}
        </button>
        {goal && (
          <p className="text-caption text-muted-foreground">
            目前目標：{GOAL_LABELS[goal.goal_slug] ?? goal.goal_slug}
          </p>
        )}
      </section>
    </GlassCard>
  );
}
