'use client';

import { useCallback, useRef, useState } from 'react';
import { Heart, Sparkles, User } from 'lucide-react';
import type { GamificationSummaryResponse, OnboardingQuestResponse, SyncNudgeItem, FirstDelightResponse } from '@/services/api-client';

const HOME_TAB_ORDER = ['mine', 'partner', 'card'] as const;
type HomeTabId = (typeof HOME_TAB_ORDER)[number];

interface HomeHeaderProps {
  savingsScore: number;
  gamificationSummary: GamificationSummaryResponse;
  onboardingQuest: OnboardingQuestResponse;
  syncNudges: { nudges: SyncNudgeItem[]; enabled: boolean };
  firstDelight: FirstDelightResponse;
  nextOnboardingStep: { quest_day: number; title: string; completed: boolean } | undefined;
  primarySyncNudge: SyncNudgeItem | null;
  showFirstDelightCard: boolean;
  activeTab: 'mine' | 'partner' | 'card';
  hasNewPartnerContent: boolean;
  getTabStyle: (tabName: string) => string;
  onTabChange: (tab: 'mine' | 'partner' | 'card') => void;
  onAckSyncNudge: () => void;
  onAckFirstDelight: () => void;
}

const badgeClass =
  'inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/12 backdrop-blur-xl shadow-glass-inset px-3.5 py-1.5 text-[11px] font-medium tracking-wider text-white/95 tabular-nums transition-all duration-haven ease-haven hover:bg-white/20 hover:scale-[1.02]';

export default function HomeHeader({
  savingsScore,
  gamificationSummary,
  onboardingQuest,
  syncNudges,
  firstDelight,
  nextOnboardingStep,
  primarySyncNudge,
  showFirstDelightCard,
  activeTab,
  hasNewPartnerContent,
  getTabStyle,
  onTabChange,
  onAckSyncNudge,
  onAckFirstDelight,
}: HomeHeaderProps) {
  const tabRefs = useRef<Record<HomeTabId, HTMLButtonElement | null>>({
    mine: null,
    partner: null,
    card: null,
  });

  const [focusedTab, setFocusedTab] = useState<HomeTabId>(() => activeTab as HomeTabId);

  const handleTabListFocusCapture = useCallback(
    (e: React.FocusEvent<HTMLDivElement>) => {
      const list = e.currentTarget;
      const related = e.relatedTarget as Node | null;
      const enteringFromOutside = !related || !list.contains(related);
      if (enteringFromOutside) {
        setFocusedTab(activeTab as HomeTabId);
        tabRefs.current[activeTab as HomeTabId]?.focus();
      }
    },
    [activeTab],
  );

  const handleTabListKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const currentIndex = HOME_TAB_ORDER.indexOf(focusedTab);
      if (currentIndex === -1) return;
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onTabChange(focusedTab);
        return;
      }
      let nextIndex = currentIndex;
      if (e.key === 'ArrowRight' || e.key === 'Down') {
        e.preventDefault();
        nextIndex = Math.min(currentIndex + 1, HOME_TAB_ORDER.length - 1);
      } else if (e.key === 'ArrowLeft' || e.key === 'Up') {
        e.preventDefault();
        nextIndex = Math.max(currentIndex - 1, 0);
      } else if (e.key === 'Home') {
        e.preventDefault();
        nextIndex = 0;
      } else if (e.key === 'End') {
        e.preventDefault();
        nextIndex = HOME_TAB_ORDER.length - 1;
      } else return;
      const nextTab = HOME_TAB_ORDER[nextIndex];
      setFocusedTab(nextTab);
      tabRefs.current[nextTab]?.focus();
    },
    [focusedTab, onTabChange],
  );

  const showNotificationCards =
    onboardingQuest.enabled || showFirstDelightCard || (syncNudges.enabled && primarySyncNudge);

  return (
    <>
      {/* ── SECTION 1: Compact Hero Banner ── */}
      <header className="relative overflow-hidden rounded-card shadow-lift group hero-gold-accent noise-overlay">
        <div className="absolute inset-0 rounded-card hero-mesh-gradient" aria-hidden />
        <div className="absolute top-0 right-0 w-80 h-80 bg-white opacity-[0.10] rounded-full blur-hero-orb -translate-y-1/2 translate-x-1/3 pointer-events-none animate-float" aria-hidden />
        <div className="absolute bottom-0 left-0 w-60 h-60 bg-primary opacity-[0.15] rounded-full blur-hero-orb-sm translate-y-1/3 -translate-x-1/4 pointer-events-none animate-float-delayed" aria-hidden />

        <div className="relative z-10 rounded-card border border-white/[0.07] px-[var(--space-section)] py-4 md:px-[var(--space-page)] md:py-5 text-white">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            {/* LEFT: Greeting + subtitle */}
            <div className="space-y-1.5 min-w-0">
              <div className="flex items-center gap-3">
                <h2 className="font-art text-3xl md:text-4xl font-bold tracking-tight text-gradient-gold drop-shadow-hero">
                  早安，朋友
                </h2>
                <div className="flex items-center gap-1.5 bg-white/18 backdrop-blur-md px-3 py-1 rounded-full border border-white/20 shadow-soft transition-all duration-haven ease-haven hover:scale-[1.02] hover:bg-white/25 cursor-default select-none">
                  <Heart className="w-3.5 h-3.5 text-white/70 fill-white/70" aria-hidden />
                  <span className="text-sm font-bold tracking-wide text-white tabular-nums">{savingsScore}</span>
                </div>
              </div>
              <p className="text-white/80 font-light text-sm md:text-base max-w-md leading-relaxed tracking-wide">
                今天的你過得好嗎？無論發生什麼，這裡都是你的避風港。
              </p>
            </div>

            {/* RIGHT (desktop): Gamification cluster + love bar */}
            <div className="flex flex-col items-end gap-2.5 shrink-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`${badgeClass} animate-slide-up-fade`}>
                  🔥 連續 {gamificationSummary.streak_days} 天
                </span>
                <span className={`${badgeClass} animate-slide-up-fade-1`}>
                  🏅 Lv.{gamificationSummary.level} · {gamificationSummary.level_title}
                </span>
                <span className={`${badgeClass} animate-slide-up-fade-2`}>
                  ⭐ 最佳 {gamificationSummary.best_streak_days} 天
                </span>
              </div>
              <div className="w-full max-w-[220px]">
                <div className="mb-1 flex items-center justify-between text-xs text-white/75 font-medium">
                  <span className="tracking-wider text-[10px]">愛情值</span>
                  <span className="tabular-nums">{Math.round(gamificationSummary.love_bar_percent)}%</span>
                </div>
                <div className="h-2 rounded-full bg-white/15 shadow-glass-inset overflow-hidden">
                  <div
                    className="h-2 rounded-full bg-gradient-to-r from-primary/90 via-primary/60 to-white/50 transition-all duration-haven ease-haven"
                    style={{ width: `${gamificationSummary.love_bar_percent}%` }}
                    aria-hidden
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* ── SECTION 2: Tab Bar (outside gradient) ── */}
      <nav className="mt-3" aria-label="主頁分頁">
        <div
          role="tablist"
          className="flex gap-1 p-1.5 bg-card/80 backdrop-blur-md border border-border rounded-full shadow-soft"
          onFocusCapture={handleTabListFocusCapture}
          onKeyDown={handleTabListKeyDown}
        >
          <button
            ref={(el) => { tabRefs.current.mine = el; }}
            type="button"
            role="tab"
            id="home-tab-mine"
            aria-selected={activeTab === 'mine'}
            aria-controls="home-tabpanel-mine"
            tabIndex={focusedTab === 'mine' ? 0 : -1}
            onFocus={() => setFocusedTab('mine')}
            onClick={() => onTabChange('mine')}
            className={`${getTabStyle('mine')} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-all duration-haven-fast ease-haven active:scale-95`}
          >
            <User size={16} strokeWidth={2.5} />
            <span>我的空間</span>
          </button>
          <button
            ref={(el) => { tabRefs.current.partner = el; }}
            type="button"
            role="tab"
            id="home-tab-partner"
            aria-selected={activeTab === 'partner'}
            aria-controls="home-tabpanel-partner"
            tabIndex={focusedTab === 'partner' ? 0 : -1}
            onFocus={() => setFocusedTab('partner')}
            onClick={() => onTabChange('partner')}
            className={`${getTabStyle('partner')} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-all duration-haven-fast ease-haven active:scale-95 relative`}
          >
            <Heart
              size={16}
              strokeWidth={2.5}
              className={hasNewPartnerContent ? 'animate-bounce' : ''}
            />
            <span>伴侶心聲</span>
            {hasNewPartnerContent && (
              <span className="absolute top-2 right-2 flex h-2.5 w-2.5" aria-hidden>
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary ring-2 ring-white" />
              </span>
            )}
          </button>
          <button
            ref={(el) => { tabRefs.current.card = el; }}
            type="button"
            role="tab"
            id="home-tab-card"
            aria-selected={activeTab === 'card'}
            aria-controls="home-tabpanel-card"
            tabIndex={focusedTab === 'card' ? 0 : -1}
            onFocus={() => setFocusedTab('card')}
            onClick={() => onTabChange('card')}
            className={`${getTabStyle('card')} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-all duration-haven-fast ease-haven active:scale-95`}
          >
            <Sparkles size={16} strokeWidth={2.5} />
            <span>每日共感</span>
          </button>
        </div>
      </nav>

      {/* ── SECTION 3: Notification Cards (outside gradient) ── */}
      {showNotificationCards && (
        <div className="mt-3 space-y-2">
          {onboardingQuest.enabled && (
            <div className="rounded-card border border-border bg-card p-4 shadow-soft animate-slide-up-fade-3">
              <div className="mb-2 flex items-center justify-between text-xs font-semibold text-card-foreground">
                <span>7 日任務</span>
                <span className="tabular-nums text-muted-foreground">
                  {onboardingQuest.completed_steps}/{onboardingQuest.total_steps}
                </span>
              </div>
              <div className="mb-2 h-2 rounded-full bg-muted shadow-glass-inset">
                <div
                  className="h-2 rounded-full bg-gradient-to-r from-accent to-accent/70 transition-all duration-haven ease-haven"
                  style={{ width: `${onboardingQuest.progress_percent}%` }}
                  aria-hidden
                />
              </div>
              <p className="text-xs text-muted-foreground">
                {nextOnboardingStep
                  ? `Day ${nextOnboardingStep.quest_day}: ${nextOnboardingStep.title}`
                  : '7 日任務已完成，持續保持互動節奏'}
              </p>
            </div>
          )}

          {showFirstDelightCard && (
            <div className="rounded-card border border-border bg-card p-4 shadow-soft animate-slide-up-fade-4">
              <div className="mb-1 flex items-center justify-between text-xs font-semibold text-card-foreground">
                <span>首次驚喜</span>
                <span className="text-muted-foreground">里程碑</span>
              </div>
              <p className="text-xs text-card-foreground">{firstDelight.title ?? '你們達成第一個里程碑'}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {firstDelight.description ?? '已完成首次雙人互動閉環，建議記錄這次成就。'}
              </p>
              <button
                type="button"
                onClick={onAckFirstDelight}
                className="mt-2 inline-flex items-center rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-semibold text-foreground transition-all duration-haven ease-haven hover:bg-primary/10 hover:scale-[1.02] active:scale-95"
              >
                已看見這個里程碑
              </button>
            </div>
          )}

          {syncNudges.enabled && primarySyncNudge && (
            <div className="rounded-card border border-border bg-card p-4 shadow-soft animate-slide-up-fade-5">
              <div className="mb-1 flex items-center justify-between text-xs font-semibold text-card-foreground">
                <span>同步提醒</span>
                <span className="text-muted-foreground">{primarySyncNudge.nudge_type.replace(/_/g, ' ')}</span>
              </div>
              <p className="text-xs text-card-foreground">{primarySyncNudge.title}</p>
              <p className="mt-1 text-xs text-muted-foreground">{primarySyncNudge.description}</p>
              <button
                type="button"
                onClick={onAckSyncNudge}
                className="mt-2 inline-flex items-center rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-semibold text-foreground transition-all duration-haven ease-haven hover:bg-primary/10 hover:scale-[1.02] active:scale-95"
              >
                我知道了
              </button>
            </div>
          )}
        </div>
      )}
    </>
  );
}
