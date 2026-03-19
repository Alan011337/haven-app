'use client';

import { useCallback, useMemo, useRef, useState } from 'react';
import { ArrowRight, BookHeart, Flame, Heart, Sparkles, User } from 'lucide-react';
import type {
  FirstDelightResponse,
  GamificationSummaryResponse,
  OnboardingQuestResponse,
  SyncNudgeItem,
} from '@/services/api-client';
import Button from '@/components/ui/Button';
import {
  EditorialPaperCard,
  HomeRailNav,
} from '@/features/home/HomePrimitives';
import { cn } from '@/lib/utils';

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
  onActivateOnboardingStep: () => void;
  onAckSyncNudge: () => void;
  onAckFirstDelight: () => void;
}

type GreetingCopy = {
  title: string;
};

function NoticeCard({
  eyebrow,
  title,
  description,
  actionLabel,
  onAction,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <EditorialPaperCard
      eyebrow={eyebrow}
      title={title}
      description={description}
      tone="paper"
      className="rounded-[2rem]"
    >
      {actionLabel && onAction ? (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={onAction}
          rightIcon={<ArrowRight className="h-4 w-4" aria-hidden />}
          className="w-fit"
        >
          {actionLabel}
        </Button>
      ) : null}
    </EditorialPaperCard>
  );
}

function getTabButtonClass(isActive: boolean) {
  return cn(
    'relative inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-4 py-2.5 text-sm font-medium transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
    isActive
      ? 'bg-[linear-gradient(180deg,rgba(255,252,248,0.98),rgba(248,243,236,0.92))] text-card-foreground shadow-lift scale-[1.02] after:absolute after:bottom-0.5 after:inset-x-4 after:h-[2px] after:rounded-full after:bg-gradient-to-r after:from-primary/20 after:via-primary/50 after:to-primary/20'
      : 'text-muted-foreground hover:bg-white/72 hover:text-card-foreground',
  );
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
  onActivateOnboardingStep,
  onAckSyncNudge,
  onAckFirstDelight,
}: HomeHeaderProps) {
  void getTabStyle;
  void syncNudges;
  void onboardingQuest;

  const tabRefs = useRef<Record<HomeTabId, HTMLButtonElement | null>>({
    mine: null,
    partner: null,
    card: null,
  });
  const [focusedTab, setFocusedTab] = useState<HomeTabId>(() => activeTab as HomeTabId);

  const greetingCopy = useMemo<Record<HomeTabId, GreetingCopy>>(() => {
    const hour = new Date().getHours();
    const isMorning = hour >= 5 && hour < 12;
    const isAfternoon = hour >= 12 && hour < 18;

    return {
      mine: {
        title: isMorning
          ? '早安，先寫幾行給自己。'
          : isAfternoon
            ? '午後，把心情寫成一頁。'
            : '晚安，讓今天先被寫成一頁。',
      },
      partner: {
        title: isMorning
          ? '今早有一封等你的信。'
          : isAfternoon
            ? '慢慢讀，再靠近。'
            : '睡前，讀一封來信。',
      },
      card: {
        title: isMorning
          ? '今天的儀式，從這裡開始。'
          : isAfternoon
            ? '下午的儀式，留在這裡。'
            : '今晚的儀式，只留在這裡。',
      },
    };
  }, []);

  const activeGreeting = greetingCopy[activeTab as HomeTabId];

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
      } else {
        return;
      }
      const nextTab = HOME_TAB_ORDER[nextIndex];
      setFocusedTab(nextTab);
      tabRefs.current[nextTab]?.focus();
    },
    [focusedTab, onTabChange],
  );

  /* ── Notice card logic (from A) — one card at most ── */
  const headerNotice = showFirstDelightCard && firstDelight.title
    ? {
        eyebrow: '新亮點',
        title: firstDelight.title,
        description: firstDelight.description ?? '有一個新的亮點等著你。',
        actionLabel: '收起提醒',
        onAction: onAckFirstDelight,
      }
    : primarySyncNudge
      ? {
          eyebrow: '溫柔提醒',
          title: primarySyncNudge.title,
          description: primarySyncNudge.description,
          actionLabel: '稍後再提醒',
          onAction: onAckSyncNudge,
        }
      : nextOnboardingStep && !nextOnboardingStep.completed
        ? {
            eyebrow: `新手引導 第${nextOnboardingStep.quest_day}天`,
            title: nextOnboardingStep.title,
            description: '讓你知道下一步在哪裡。',
            actionLabel: '繼續新手引導',
            onAction: onActivateOnboardingStep,
          }
        : null;

  return (
    <header className="space-y-5">
      {/* ── Greeting + context strip ── */}
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1.5 animate-slide-up-fade">
          <h1 className="max-w-3xl type-h1 text-gradient-gold">
            {activeGreeting.title}
          </h1>
        </div>

        {/* Compact metric strip — quiet context, not a dashboard */}
        <div className="flex items-center gap-3 animate-slide-up-fade-1">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/12 bg-white/55 px-3 py-1.5 text-xs backdrop-blur-md shadow-soft">
            <Flame className="h-3.5 w-3.5 text-primary/70" aria-hidden />
            <span className="tabular-nums text-card-foreground">{gamificationSummary.streak_days} 天</span>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-accent/15 bg-white/55 px-3 py-1.5 text-xs backdrop-blur-md shadow-soft">
            <Heart className="h-3.5 w-3.5 text-accent/70" aria-hidden />
            <span className="tabular-nums text-card-foreground">{savingsScore} 分</span>
          </div>
          {hasNewPartnerContent ? (
            <div className="inline-flex items-center gap-1.5 rounded-full border border-primary/15 bg-primary/6 px-3 py-1.5 text-xs text-primary/80 backdrop-blur-md">
              <span className="h-1.5 w-1.5 rounded-full bg-primary/70 animate-breathe" aria-hidden />
              <span>有新來信</span>
            </div>
          ) : null}
        </div>
      </div>

      {/* ── Tab navigation ── */}
      <div className="flex flex-col gap-4 animate-slide-up-fade-2">
        <HomeRailNav className="max-w-[620px]">
          <div
            role="tablist"
            aria-label="主頁分頁"
            className="flex flex-col gap-1 md:flex-row"
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
              className={getTabButtonClass(activeTab === 'mine')}
            >
              <User size={15} strokeWidth={2.25} />
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
              className={getTabButtonClass(activeTab === 'partner')}
            >
              <BookHeart size={15} strokeWidth={2.25} />
              <span>伴侶來信</span>
              {hasNewPartnerContent ? (
                <span className="h-2 w-2 rounded-full bg-primary/75 shadow-[0_0_0_5px_rgba(201,163,100,0.12)]" aria-hidden />
              ) : null}
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
              className={getTabButtonClass(activeTab === 'card')}
            >
              <Sparkles size={15} strokeWidth={2.25} />
              <span>每日儀式</span>
            </button>
          </div>
        </HomeRailNav>

        {/* Notice card — below tab nav, full width */}
        {headerNotice ? (
          <div className="max-w-lg animate-slide-up-fade-3">
            <NoticeCard {...headerNotice} />
          </div>
        ) : null}
      </div>
    </header>
  );
}
