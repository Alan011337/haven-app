'use client';

import { useCallback, useMemo, useRef, useState } from 'react';
import { BookHeart, Flame, Heart, Sparkles, Star, User } from 'lucide-react';
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
    'inline-flex min-h-12 items-center justify-center gap-2 rounded-full px-4 py-3 text-sm font-medium transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
    isActive
      ? 'bg-[linear-gradient(180deg,rgba(255,252,248,0.98),rgba(248,243,236,0.92))] text-card-foreground shadow-soft'
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
        title: '首頁現在先服務一件事：把今天寫好。',
        description:
          '這裡不是資訊總覽，而是一張被好好留白的封面。你先寫，其他 flow 會安靜退到第二層。',
      },
      partner: {
        eyebrow: 'Reading Room',
        title: '先慢慢讀，再決定今天要怎麼靠近對方。',
        description:
          '伴侶內容在這一頁不再像通知。它被整理成更像來信的閱讀場景，讓你先理解，再回應。',
      },
      card: {
        eyebrow: 'Night Ritual',
        title: '今晚最值得一起回答的問題，只留在一個舞台上。',
        description:
          'Daily ritual 的周圍噪音被刻意降到最低。抽卡、等待與揭曉，都應該像一場被照亮的儀式。',
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
          description:
            '同步提醒現在不再佔滿首頁。它只留下最輕的一句提示，等你寫完自己的頁面之後再回頭看。',
          actionLabel: '稍後再提醒',
          onAction: onAckSyncNudge,
        }
      : {
          eyebrow: nextOnboardingStep ? `Quest Day ${nextOnboardingStep.quest_day}` : 'Editorial Note',
          title: nextOnboardingStep?.title ?? '把首頁留給今天真正重要的那一段。',
          description: nextOnboardingStep?.completed
            ? '今天的 quest 已完成，首頁會把更多空間還給你的文字。'
            : syncNudges.enabled
              ? `目前還有 ${syncNudges.nudges.length} 則 gentle nudges，但它們會安靜地待在第二層。`
              : '當首頁變得夠安靜，真正有價值的互動自然會留下來。',
      };

  return (
    <section className="space-y-5">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.05fr)_360px] xl:items-start">
        <div className="space-y-4">
          <div className="space-y-3">
            <p className="text-[0.72rem] uppercase tracking-[0.34em] text-primary/80">
              {activeMasthead.eyebrow}
            </p>
            <h1 className="max-w-5xl font-art text-[2rem] leading-[0.98] text-card-foreground md:text-[3rem] xl:text-[3.45rem]">
              {activeMasthead.title}
            </h1>
            <p className="max-w-3xl text-sm leading-7 text-muted-foreground md:text-[0.98rem]">
              {activeMasthead.description}
            </p>
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
            <EditorialMetricPill
              icon={Star}
              label="進度"
              value={`${onboardingQuest.completed_steps}/${onboardingQuest.total_steps}`}
              tone="neutral"
              className="min-w-[118px]"
            />
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
            description={
              activeTab === 'partner'
                ? '在這個分頁裡，新的內容不被設計成要立刻清掉的 badge，而是一封可以慢慢展開的信。'
                : activeTab === 'card'
                  ? '這一頁不追求資訊量。它只留下最值得被一起完成的那張卡與那個節奏。'
                  : hasNewPartnerContent
                    ? '首頁會先把你的文字放到前景；伴侶內容會安靜待在第二層，等你寫完之後再讀。'
                    : '讓首頁先照顧你自己的文字與情緒，其他互動就會自然地排進正確位置。'
            }
            tone="mist"
            className="rounded-[2rem]"
          >
            <div className="flex items-center gap-2 text-sm text-card-foreground">
              {activeTab === 'partner' ? <BookHeart className="h-4 w-4 text-primary" aria-hidden /> : null}
              {activeTab === 'card' ? <Sparkles className="h-4 w-4 text-primary" aria-hidden /> : null}
              {activeTab === 'mine' ? <User className="h-4 w-4 text-primary" aria-hidden /> : null}
              <span>
                {activeTab === 'mine'
                  ? '先寫，再看，最後再進入 ritual。'
                  : activeTab === 'partner'
                    ? '先理解，再回應；先慢下來，再靠近。'
                    : '抽卡、回答、等待與揭曉，都值得被慢慢完成。'}
              </span>
            </div>
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
