'use client';

import { useCallback, useMemo, useRef, useState } from 'react';
import { BookHeart, Flame, Heart, Sparkles, User } from 'lucide-react';
import type {
  FirstDelightResponse,
  GamificationSummaryResponse,
  OnboardingQuestResponse,
  SyncNudgeItem,
} from '@/services/api-client';
import {
  EditorialMetricPill,
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
  onAckSyncNudge: () => void;
  onAckFirstDelight: () => void;
}

type MastheadCopy = {
  eyebrow: string;
  title: string;
  description: string;
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
        <button
          type="button"
          onClick={onAction}
          className="inline-flex items-center gap-2 rounded-full border border-primary/14 bg-primary/8 px-4 py-2 text-sm font-medium text-card-foreground transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-soft"
        >
          {actionLabel}
        </button>
      ) : null}
    </EditorialPaperCard>
  );
}

function getMastheadButtonClass(isActive: boolean) {
  return cn(
    'relative inline-flex min-h-12 items-center justify-center gap-2 rounded-full px-4 py-3 text-sm font-medium transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
    isActive
      ? 'bg-[linear-gradient(180deg,rgba(255,252,248,0.98),rgba(248,243,236,0.92))] text-card-foreground shadow-lift scale-[1.02] after:absolute after:bottom-1 after:inset-x-4 after:h-[2.5px] after:rounded-full after:bg-gradient-to-r after:from-primary/20 after:via-primary/50 after:to-primary/20'
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
  onAckSyncNudge,
  onAckFirstDelight,
}: HomeHeaderProps) {
  void getTabStyle;
  const tabRefs = useRef<Record<HomeTabId, HTMLButtonElement | null>>({
    mine: null,
    partner: null,
    card: null,
  });
  const [focusedTab, setFocusedTab] = useState<HomeTabId>(() => activeTab as HomeTabId);

  const mastheadCopy = useMemo<Record<HomeTabId, MastheadCopy>>(
    () => ({
      mine: {
        eyebrow: 'Cover Story',
        title: '讓今天先被寫成一頁。',
        description: '',
      },
      partner: {
        eyebrow: 'Reading Room',
        title: '慢慢讀，再靠近。',
        description: '',
      },
      card: {
        eyebrow: 'Night Ritual',
        title: '今晚的儀式，只留在這裡。',
        description: '',
      },
    }),
    [],
  );

  const activeMasthead = mastheadCopy[activeTab as HomeTabId];

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

  const headerNotice = showFirstDelightCard && firstDelight.title
    ? {
        eyebrow: 'First Delight',
        title: firstDelight.title,
        description:
          firstDelight.description ??
          '首頁只保留真正值得被看見的亮點，新的互動提醒會被收成一張安靜的小卡。',
        actionLabel: '收起提醒',
        onAction: onAckFirstDelight,
      }
    : primarySyncNudge
      ? {
          eyebrow: 'Gentle Nudge',
          title: '今天適合主動靠近一下。',
          description: '',
          actionLabel: '稍後再提醒',
          onAction: onAckSyncNudge,
        }
      : {
          eyebrow: nextOnboardingStep ? `Quest Day ${nextOnboardingStep.quest_day}` : 'Editorial Note',
          title: nextOnboardingStep?.title ?? '把首頁留給今天真正重要的那一段。',
          description: '',
      };

  const questMeta =
    nextOnboardingStep && !nextOnboardingStep.completed
      ? `Quest Day ${nextOnboardingStep.quest_day} · ${nextOnboardingStep.title}`
      : `本週進度 ${onboardingQuest.completed_steps}/${onboardingQuest.total_steps}`;

  return (
    <section className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px] xl:items-start">
        <div className="space-y-4">
          <div className="space-y-3 rounded-[2rem] border border-white/44 bg-white/48 p-5 shadow-soft backdrop-blur-xl md:p-6">
            <p className="text-[0.72rem] uppercase tracking-[0.34em] text-primary/80">
              {activeMasthead.eyebrow}
            </p>
            <h1 className="max-w-4xl font-art text-[1.9rem] leading-[1.02] text-gradient-gold md:text-[2.7rem] xl:text-[3.05rem]">
              {activeMasthead.title}
            </h1>
            {activeMasthead.description ? (
              <p className="max-w-3xl text-sm leading-7 tracking-wide text-muted-foreground md:text-[0.98rem]">
                {activeMasthead.description}
              </p>
            ) : null}
            <div className="inline-flex max-w-max items-center gap-2 rounded-full border border-white/50 bg-white/74 px-3 py-2 text-[0.68rem] uppercase tracking-[0.24em] text-primary/75 shadow-soft">
              <span className="h-2 w-2 rounded-full bg-primary/70" aria-hidden />
              <span>{questMeta}</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <EditorialMetricPill
              icon={Flame}
              label="連續互動"
              value={`${gamificationSummary.streak_days} 天`}
              className="min-w-[142px]"
            />
            <EditorialMetricPill
              icon={Heart}
              label="關係脈搏"
              value={`${savingsScore} 分`}
              tone="sage"
              className="min-w-[138px]"
            />
            <div className="inline-flex items-center gap-3 rounded-full border border-white/48 bg-white/62 px-4 py-3 text-sm text-muted-foreground shadow-soft backdrop-blur-md">
              <span className="text-[0.66rem] font-semibold uppercase tracking-[0.26em] text-primary/80">Flow</span>
              <span className="leading-none text-card-foreground">
                {activeTab === 'mine'
                  ? '先寫，再看。'
                  : activeTab === 'partner'
                    ? '先讀，再回應。'
                    : '先專注，再揭曉。'}
              </span>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <NoticeCard {...headerNotice} />

          <EditorialPaperCard
            eyebrow={activeTab === 'partner' ? 'Reading Signal' : activeTab === 'card' ? 'Stage Rule' : 'Relationship Pulse'}
            title={
              activeTab === 'partner'
                ? '用閱讀感取代通知感。'
                : activeTab === 'card'
                  ? '把 ritual 留在唯一的聚光區。'
                  : hasNewPartnerContent
                    ? '伴侶那邊有新的內容，但先別急。'
                    : '今天維持低噪音首頁。'
            }
            description=""
            tone="mist"
            className="rounded-[2rem]"
          >
            {null}
          </EditorialPaperCard>
        </div>
      </div>

      <HomeRailNav className="max-w-[760px]">
        <div
          role="tablist"
          aria-label="主頁分頁"
          className="flex flex-col gap-1.5 md:flex-row"
          onFocusCapture={handleTabListFocusCapture}
          onKeyDown={handleTabListKeyDown}
        >
          <button
            ref={(el) => {
              tabRefs.current.mine = el;
            }}
            type="button"
            role="tab"
            id="home-tab-mine"
            aria-selected={activeTab === 'mine'}
            aria-controls="home-tabpanel-mine"
            tabIndex={focusedTab === 'mine' ? 0 : -1}
            onFocus={() => setFocusedTab('mine')}
            onClick={() => onTabChange('mine')}
            className={getMastheadButtonClass(activeTab === 'mine')}
          >
            <User size={16} strokeWidth={2.25} />
            <span>我的空間</span>
          </button>
          <button
            ref={(el) => {
              tabRefs.current.partner = el;
            }}
            type="button"
            role="tab"
            id="home-tab-partner"
            aria-selected={activeTab === 'partner'}
            aria-controls="home-tabpanel-partner"
            tabIndex={focusedTab === 'partner' ? 0 : -1}
            onFocus={() => setFocusedTab('partner')}
            onClick={() => onTabChange('partner')}
            className={getMastheadButtonClass(activeTab === 'partner')}
          >
            <BookHeart size={16} strokeWidth={2.25} />
            <span>伴侶來信</span>
          </button>
          <button
            ref={(el) => {
              tabRefs.current.card = el;
            }}
            type="button"
            role="tab"
            id="home-tab-card"
            aria-selected={activeTab === 'card'}
            aria-controls="home-tabpanel-card"
            tabIndex={focusedTab === 'card' ? 0 : -1}
            onFocus={() => setFocusedTab('card')}
            onClick={() => onTabChange('card')}
            className={getMastheadButtonClass(activeTab === 'card')}
          >
            <Sparkles size={16} strokeWidth={2.25} />
            <span>每日儀式</span>
          </button>
        </div>
      </HomeRailNav>
    </section>
  );
}
