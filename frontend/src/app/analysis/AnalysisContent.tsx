'use client';

import Link from 'next/link';
import {
  Flame,
  Heart,
  Layers,
  MessageCircle,
  Sparkles,
} from 'lucide-react';

import {
  useAnalysisData,
  type MoodEntry,
  type CategoryEntry,
} from '@/features/analysis/useAnalysisData';
import type { WeeklyReportPublic } from '@/services/api-client';
import type { RelationshipReportResponse } from '@/services/memoryService';
import type { GamificationSummaryResponse } from '@/services/api-client.types';
import type { DeckHistorySummary } from '@/services/deckService';
import { getGradientForMood } from '@/lib/mood-background';

/* ── Category display names ── */

const CATEGORY_LABELS: Record<string, string> = {
  DAILY_VIBE: '日常共感',
  SOUL_DIVE: '靈魂深潛',
  SAFE_ZONE: '安全地帶',
  MEMORY_LANE: '回憶小路',
  GROWTH_QUEST: '成長任務',
  AFTER_DARK: '夜語悄悄',
  CO_PILOT: '共同領航',
  LOVE_BLUEPRINT: '愛情藍圖',
};

function getCategoryLabel(key: string): string {
  return CATEGORY_LABELS[key] ?? key;
}

/* ══════════════════════════════════════════════════════════════
   Section 1: Relationship Pulse (hero)
   ══════════════════════════════════════════════════════════════ */

function RelationshipPulseSection({
  report,
  loading,
}: {
  report: RelationshipReportResponse | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div
        className="h-40 animate-pulse rounded-[2rem] bg-white/60 shadow-soft"
        aria-hidden
      />
    );
  }

  const hasTrend = !!report?.emotion_trend_summary;
  const hasSuggestion = !!report?.health_suggestion;
  const hasTopics = (report?.top_topics ?? []).length > 0;

  if (!hasTrend && !hasSuggestion) {
    return (
      <section
        className="animate-slide-up-fade rounded-[2rem] border border-primary/12 bg-[linear-gradient(180deg,rgba(255,250,247,0.92),rgba(250,243,234,0.84))] p-6 shadow-soft md:p-8"
        aria-label="關係脈動"
      >
        <div className="flex items-start gap-3">
          <Sparkles
            className="mt-0.5 h-5 w-5 shrink-0 text-primary/60"
            aria-hidden
          />
          <div>
            <h2 className="font-art text-lg text-card-foreground">
              關係脈動
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              持續記錄日常，Haven 會漸漸看見你們之間的情感脈絡。
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section
      className="animate-slide-up-fade rounded-[2rem] border border-primary/12 bg-[linear-gradient(180deg,rgba(255,250,247,0.92),rgba(250,243,234,0.84))] p-6 shadow-soft md:p-8"
      aria-label="關係脈動"
    >
      <div className="flex items-start gap-3">
        <Sparkles
          className="mt-0.5 h-5 w-5 shrink-0 text-primary/60"
          aria-hidden
        />
        <h2 className="font-art text-lg text-card-foreground">關係脈動</h2>
      </div>

      {hasTrend && (
        <blockquote className="mt-4 border-l-[3px] border-l-primary/40 pl-4 text-sm leading-relaxed text-card-foreground/90 italic">
          {report!.emotion_trend_summary}
        </blockquote>
      )}

      {hasTopics && (
        <div className="mt-4 flex flex-wrap gap-2">
          {report!.top_topics.map((topic) => (
            <span
              key={topic}
              className="rounded-full bg-primary/8 px-3 py-1 text-xs font-medium text-card-foreground/80"
            >
              {topic}
            </span>
          ))}
        </div>
      )}

      {hasSuggestion && (
        <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
          {report!.health_suggestion}
        </p>
      )}

      {report?.from_date && report?.to_date && (
        <p className="mt-3 text-xs tabular-nums text-muted-foreground/60">
          {report.from_date} — {report.to_date}
        </p>
      )}
    </section>
  );
}

/* ══════════════════════════════════════════════════════════════
   Section 2: Connection Rhythm
   ══════════════════════════════════════════════════════════════ */

function ConnectionRhythmSection({
  weekly,
  weeklyLoading,
  gamification,
  gamificationLoading,
}: {
  weekly: WeeklyReportPublic | null;
  weeklyLoading: boolean;
  gamification: GamificationSummaryResponse | null;
  gamificationLoading: boolean;
}) {
  const loading = weeklyLoading || gamificationLoading;

  if (loading) {
    return (
      <div
        className="h-44 animate-pulse rounded-[2rem] bg-white/55 shadow-soft"
        aria-hidden
      />
    );
  }

  const daysFilled = weekly?.daily_sync_days_filled ?? 0;
  const appreciations = weekly?.appreciation_count ?? 0;
  const insight = weekly?.insight ?? null;
  const streak = gamification?.streak_days ?? 0;
  const bestStreak = gamification?.best_streak_days ?? 0;

  const isEmpty = daysFilled === 0 && streak === 0 && appreciations === 0;

  return (
    <section
      className="animate-slide-up-fade-1 rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(248,252,250,0.90),rgba(241,247,244,0.82))] p-6 shadow-soft md:p-8"
      aria-label="連結節奏"
    >
      <h2 className="font-art text-lg text-card-foreground">連結節奏</h2>

      {isEmpty ? (
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          這週還沒有同步紀錄。每天花幾分鐘分享心情，就能看到連結的節奏。
        </p>
      ) : (
        <div className="mt-4 space-y-5">
          {/* Weekly sync dot strip */}
          <div>
            <p className="text-xs font-medium text-muted-foreground/70">
              本週每日同步
            </p>
            <div
              className="mt-2 flex items-center gap-2"
              role="img"
              aria-label={`7 天中完成 ${daysFilled} 天`}
            >
              {Array.from({ length: 7 }, (_, i) => (
                <span
                  key={i}
                  className={`h-3 w-3 rounded-full transition-colors duration-haven ${
                    i < daysFilled ? 'bg-primary/60' : 'bg-muted/30'
                  }`}
                  aria-hidden
                />
              ))}
              <span className="ml-1 text-xs tabular-nums text-muted-foreground">
                {daysFilled}/7
              </span>
            </div>
          </div>

          {/* Metrics row */}
          <div className="flex flex-wrap items-center gap-5">
            {appreciations > 0 && (
              <div className="flex items-center gap-1.5">
                <Heart
                  className="h-3.5 w-3.5 text-primary/50"
                  aria-hidden
                />
                <span className="text-sm tabular-nums text-card-foreground">
                  {appreciations}
                </span>
                <span className="text-xs text-muted-foreground">
                  次感謝
                </span>
              </div>
            )}

            {streak > 0 && (
              <div className="flex items-center gap-1.5">
                <Flame
                  className="h-3.5 w-3.5 text-primary/50"
                  aria-hidden
                />
                <span className="text-sm tabular-nums text-card-foreground">
                  {streak}
                </span>
                <span className="text-xs text-muted-foreground">
                  天連續
                </span>
                {bestStreak > streak && (
                  <span className="text-xs tabular-nums text-muted-foreground/60">
                    （最佳 {bestStreak}）
                  </span>
                )}
              </div>
            )}
          </div>

          {/* AI insight */}
          {insight && (
            <blockquote className="border-l-[3px] border-l-primary/30 pl-4 text-sm leading-relaxed text-card-foreground/85 italic">
              {insight}
            </blockquote>
          )}

          {weekly?.period_start && weekly?.period_end && (
            <p className="text-xs tabular-nums text-muted-foreground/60">
              {weekly.period_start} — {weekly.period_end}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

/* ══════════════════════════════════════════════════════════════
   Section 3: Conversation Landscape
   ══════════════════════════════════════════════════════════════ */

function ConversationLandscapeSection({
  summary,
  summaryLoading,
  exploration,
}: {
  summary: DeckHistorySummary | null;
  summaryLoading: boolean;
  exploration: { explored: number; total: number; categories: CategoryEntry[] };
}) {
  if (summaryLoading) {
    return (
      <div
        className="h-32 animate-pulse rounded-[2rem] bg-white/50 shadow-soft"
        aria-hidden
      />
    );
  }

  const totalRecords = summary?.total_records ?? 0;
  const thisMonth = summary?.this_month_records ?? 0;
  const topCategory = summary?.top_category
    ? getCategoryLabel(summary.top_category)
    : null;
  const topCount = summary?.top_category_count ?? 0;

  if (totalRecords === 0) {
    return (
      <section
        className="animate-slide-up-fade-2 rounded-[2rem] border border-white/50 bg-white/70 p-6 shadow-soft md:p-8"
        aria-label="對話版圖"
      >
        <div className="flex items-start gap-3">
          <MessageCircle
            className="mt-0.5 h-5 w-5 shrink-0 text-primary/50"
            aria-hidden
          />
          <div>
            <h2 className="font-art text-lg text-card-foreground">
              對話版圖
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              還沒有對話卡紀錄。試試一起抽卡，開啟新的對話主題。
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section
      className="animate-slide-up-fade-2 rounded-[2rem] border border-white/50 bg-white/70 p-6 shadow-soft md:p-8"
      aria-label="對話版圖"
    >
      <div className="flex items-start gap-3">
        <MessageCircle
          className="mt-0.5 h-5 w-5 shrink-0 text-primary/50"
          aria-hidden
        />
        <h2 className="font-art text-lg text-card-foreground">對話版圖</h2>
      </div>

      <div className="mt-4 space-y-4">
        {/* Stats row */}
        <div className="flex flex-wrap items-center gap-5">
          {topCategory && (
            <div>
              <p className="text-xs font-medium text-muted-foreground/70">
                最常探索
              </p>
              <p className="mt-0.5 text-sm text-card-foreground">
                {topCategory}
                <span className="ml-1.5 text-xs tabular-nums text-muted-foreground">
                  {topCount} 次
                </span>
              </p>
            </div>
          )}
          <div>
            <p className="text-xs font-medium text-muted-foreground/70">
              本月對話
            </p>
            <p className="mt-0.5 text-sm tabular-nums text-card-foreground">
              {thisMonth} 次
            </p>
          </div>
        </div>

        {/* Category exploration */}
        {exploration.total > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground/70">
              探索了 {exploration.explored}/{exploration.total} 個主題
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {exploration.categories.map((cat) => (
                <span
                  key={cat.category}
                  className={`rounded-full px-3 py-1 text-xs font-medium ${
                    cat.answered > 0
                      ? 'bg-primary/8 text-card-foreground/80'
                      : 'bg-muted/20 text-muted-foreground/50'
                  }`}
                >
                  {getCategoryLabel(cat.category)}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

/* ══════════════════════════════════════════════════════════════
   Section 4: Mood Journey (conditional)
   ══════════════════════════════════════════════════════════════ */

function MoodJourneySection({
  moods,
  dateRange,
}: {
  moods: MoodEntry[];
  dateRange: { from: string; to: string } | null;
}) {
  if (moods.length < 3 || !dateRange) return null;

  return (
    <section
      className="animate-slide-up-fade-3 rounded-[2rem] border border-white/50 bg-white/70 p-6 shadow-soft md:p-8"
      aria-label="心情旅程"
    >
      <div className="flex items-start gap-3">
        <Layers
          className="mt-0.5 h-5 w-5 shrink-0 text-primary/50"
          aria-hidden
        />
        <h2 className="font-art text-lg text-card-foreground">心情旅程</h2>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {moods.map((mood) => {
          const gradient = getGradientForMood(mood.label);
          return (
            <span
              key={mood.label}
              className={`inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r ${gradient} px-3 py-1.5 text-xs font-medium text-card-foreground/80`}
            >
              {mood.label}
              <span className="tabular-nums text-muted-foreground/70">
                ×{mood.count}
              </span>
            </span>
          );
        })}
      </div>

      <p className="mt-3 text-xs text-muted-foreground/60">
        {dateRange.from} — {dateRange.to} 的日記心情
      </p>
    </section>
  );
}

/* ══════════════════════════════════════════════════════════════
   Global Empty State
   ══════════════════════════════════════════════════════════════ */

function AnalysisEmptyState() {
  return (
    <div className="animate-slide-up-fade rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] px-6 py-14 text-center shadow-soft">
      <Sparkles className="mx-auto h-8 w-8 text-primary/40" aria-hidden />
      <p className="mt-4 font-art text-lg font-medium text-card-foreground/80">
        開始記錄你們的日常
      </p>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
        Haven 會幫你看見彼此之間美好的模式。
        <br />
        寫下第一篇日記、完成每日同步、或一起抽卡，都是很好的開始。
      </p>
      <Link
        href="/"
        className="mt-6 inline-flex items-center justify-center rounded-button border border-border/70 bg-card/82 px-5 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
      >
        回首頁
      </Link>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   Main Content Orchestrator
   ══════════════════════════════════════════════════════════════ */

export default function AnalysisContent() {
  const {
    weeklyReport,
    weeklyReportLoading,
    relationshipReport,
    relationshipReportLoading,
    gamification,
    gamificationLoading,
    deckSummary,
    deckSummaryLoading,
    moodDistribution,
    moodDateRange,
    categoryExploration,
    isFullyEmpty,
    isLoading,
  } = useAnalysisData();

  return (
    <div className="space-y-8 md:space-y-10">
      {/* ── Page identity ── */}
      <div className="space-y-3 animate-slide-up-fade">
        <h1 className="font-art text-[2rem] leading-[1.05] tracking-tight text-gradient-gold md:text-[2.8rem]">
          關係洞察
        </h1>
        <p className="text-sm leading-relaxed text-muted-foreground">
          看見你們之間的美好模式。
        </p>
      </div>

      {/* ── Global empty state OR sections ── */}
      {!isLoading && isFullyEmpty ? (
        <AnalysisEmptyState />
      ) : (
        <>
          <RelationshipPulseSection
            report={relationshipReport}
            loading={relationshipReportLoading}
          />

          <ConnectionRhythmSection
            weekly={weeklyReport}
            weeklyLoading={weeklyReportLoading}
            gamification={gamification}
            gamificationLoading={gamificationLoading}
          />

          <ConversationLandscapeSection
            summary={deckSummary}
            summaryLoading={deckSummaryLoading}
            exploration={categoryExploration}
          />

          <MoodJourneySection
            moods={moodDistribution}
            dateRange={moodDateRange}
          />
        </>
      )}
    </div>
  );
}
