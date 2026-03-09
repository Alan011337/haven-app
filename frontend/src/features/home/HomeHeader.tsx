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

  return (
    <header className="relative overflow-hidden rounded-card shadow-lift group">
      {/* Background layer: Phase 4 mesh (Champagne Gold + accent hints) */}
      <div className="absolute inset-0 rounded-card hero-mesh-gradient" aria-hidden />
      <div className="absolute top-0 right-0 w-80 h-80 bg-white opacity-10 rounded-full blur-hero-orb -translate-y-1/2 translate-x-1/3 pointer-events-none animate-float" aria-hidden />
      <div className="absolute bottom-0 left-0 w-60 h-60 bg-accent opacity-25 rounded-full blur-hero-orb-sm translate-y-1/3 -translate-x-1/4 pointer-events-none animate-float-delayed" aria-hidden />

      {/* Glass content layer: frosted panel with double border + glass inset */}
      <div className="relative z-10 glass-panel-art rounded-card border border-white/40 shadow-hero-glass p-[var(--space-section)] md:p-[var(--space-page)] text-white">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
          <div className="flex flex-col gap-[var(--space-section)]">
            <div className="space-y-3">
              <div className="flex items-center gap-4">
                <h2 className="font-art text-3xl md:text-4xl font-bold tracking-tight text-white drop-shadow-soft">
                  早安，朋友
                </h2>
                <div className="flex items-center gap-2 bg-white/15 backdrop-blur-md px-4 py-1.5 rounded-full border border-white/20 shadow-soft transition-all duration-haven ease-haven hover:scale-[1.02] hover:bg-white/20 cursor-default select-none">
                  <Heart className="w-4 h-4 text-white/70 fill-white/70" aria-hidden />
                  <span className="text-sm font-bold tracking-wide text-white tabular-nums">{savingsScore}</span>
                </div>
              </div>
              <p className="text-white/85 font-light text-base md:text-lg max-w-lg leading-relaxed">
                今天的你過得好嗎？無論發生什麼，這裡都是你的避風港。
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/15 backdrop-blur-md shadow-glass-inset px-3.5 py-1.5 text-xs font-semibold text-white/95 tabular-nums transition-all duration-haven ease-haven hover:bg-white/20 hover:scale-[1.02] animate-slide-up-fade">
                🔥 連續 {gamificationSummary.streak_days} 天
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/15 backdrop-blur-md shadow-glass-inset px-3.5 py-1.5 text-xs font-semibold text-white/95 tabular-nums transition-all duration-haven ease-haven hover:bg-white/20 hover:scale-[1.02] animate-slide-up-fade-1">
                🏅 Lv.{gamificationSummary.level} · {gamificationSummary.level_title}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/15 backdrop-blur-md shadow-glass-inset px-3.5 py-1.5 text-xs font-semibold text-white/95 tabular-nums transition-all duration-haven ease-haven hover:bg-white/20 hover:scale-[1.02] animate-slide-up-fade-2">
                ⭐ 最佳 {gamificationSummary.best_streak_days} 天
              </span>
            </div>
          <div className="w-full max-w-xs">
            <div className="mb-1.5 flex items-center justify-between text-xs text-white/75 font-medium">
              <span className="tracking-wider uppercase text-[10px]">Love Bar</span>
              <span className="tabular-nums">{Math.round(gamificationSummary.love_bar_percent)}%</span>
            </div>
            <div className="h-2.5 rounded-full bg-white/15 shadow-glass-inset overflow-hidden">
              <div
                className="h-2.5 rounded-full bg-gradient-to-r from-white/90 via-white/70 to-white/50 transition-all duration-haven ease-haven"
                style={{ width: `${gamificationSummary.love_bar_percent}%` }}
                aria-hidden
              />
            </div>
          </div>

          {onboardingQuest.enabled && (
            <div className="w-full max-w-sm rounded-card border border-white/25 bg-white/15 p-4 backdrop-blur-md shadow-glass-inset animate-slide-up-fade-3">
              <div className="mb-2 flex items-center justify-between text-xs font-semibold text-white/90">
                <span>7-Day Quest</span>
                <span className="tabular-nums">
                  {onboardingQuest.completed_steps}/{onboardingQuest.total_steps}
                </span>
              </div>
              <div className="mb-2 h-2 rounded-full bg-white/20 shadow-glass-inset">
                <div
                  className="h-2 rounded-full bg-gradient-to-r from-accent to-accent/70 transition-all duration-haven ease-haven"
                  style={{ width: `${onboardingQuest.progress_percent}%` }}
                  aria-hidden
                />
              </div>
              <p className="text-xs text-white/90">
                {nextOnboardingStep
                  ? `Day ${nextOnboardingStep.quest_day}: ${nextOnboardingStep.title}`
                  : '7-Day Quest 已完成，持續保持互動節奏'}
              </p>
            </div>
          )}

          {showFirstDelightCard && (
            <div className="w-full max-w-sm rounded-card border border-white/25 bg-white/15 p-4 backdrop-blur-md shadow-glass-inset animate-slide-up-fade-4">
              <div className="mb-1 flex items-center justify-between text-xs font-semibold text-white/90">
                <span>First Delight</span>
                <span>milestone</span>
              </div>
              <p className="text-xs text-white/95">{firstDelight.title ?? '你們達成第一個里程碑'}</p>
              <p className="mt-1 text-xs text-white/80">
                {firstDelight.description ?? '已完成首次雙人互動閉環，建議記錄這次成就。'}
              </p>
              <button
                type="button"
                onClick={onAckFirstDelight}
                className="mt-2 inline-flex items-center rounded-full border border-white/40 bg-white/10 backdrop-blur-sm shadow-glass-inset px-3 py-1 text-xs font-semibold text-white transition-all duration-haven ease-haven hover:bg-white/20 hover:scale-[1.02] active:scale-95"
              >
                已看見這個里程碑
              </button>
            </div>
          )}

          {syncNudges.enabled && primarySyncNudge && (
            <div className="w-full max-w-sm rounded-card border border-white/25 bg-white/15 p-4 backdrop-blur-md shadow-glass-inset animate-slide-up-fade-5">
              <div className="mb-1 flex items-center justify-between text-xs font-semibold text-white/90">
                <span>同步提醒</span>
                <span>{primarySyncNudge.nudge_type.replace(/_/g, ' ')}</span>
              </div>
              <p className="text-xs text-white/95">{primarySyncNudge.title}</p>
              <p className="mt-1 text-xs text-white/80">{primarySyncNudge.description}</p>
              <button
                type="button"
                onClick={onAckSyncNudge}
                className="mt-2 inline-flex items-center rounded-full border border-white/40 bg-white/10 backdrop-blur-sm shadow-glass-inset px-3 py-1 text-xs font-semibold text-white transition-all duration-haven ease-haven hover:bg-white/20 hover:scale-[1.02] active:scale-95"
              >
                我知道了
              </button>
            </div>
          )}
        </div>

        <div
          role="tablist"
          aria-label="主頁分頁"
          className="flex flex-wrap gap-1 p-1.5 bg-white/30 backdrop-blur-xl border border-white/40 rounded-full shadow-soft"
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
        </div>
      </div>
    </header>
  );
}
