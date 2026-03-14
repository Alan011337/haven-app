'use client';

import { useCallback, useMemo, useRef, useState } from 'react';
import {
  ArrowRight,
  BookHeart,
  Flame,
  Heart,
  Sparkles,
  User,
  type LucideIcon,
} from 'lucide-react';
import type {
  FirstDelightResponse,
  GamificationSummaryResponse,
  OnboardingQuestResponse,
  SyncNudgeItem,
} from '@/services/api-client';
import Button from '@/components/ui/Button';
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
  onActivateOnboardingStep: () => void;
  onAckSyncNudge: () => void;
  onAckFirstDelight: () => void;
}

type MastheadCopy = {
  eyebrow: string;
  title: string;
  description: string;
  ritualTitle: string;
  ritualDescription: string;
  atmosphereTitle: string;
  atmosphereDescription: string;
  houseRuleTitle: string;
  houseRuleDescription: string;
};

type TabDescriptor = {
  label: string;
  caption: string;
  icon: LucideIcon;
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
      className="rounded-[2.2rem]"
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

function getMastheadButtonClass(isActive: boolean) {
  return cn(
    'group relative flex w-full items-start gap-[var(--space-inline)] rounded-[1.7rem] border px-4 py-4 text-left transition-all duration-haven ease-haven focus-ring-premium',
    isActive
      ? 'border-primary/18 bg-[linear-gradient(180deg,rgba(255,252,248,0.98),rgba(248,243,236,0.92))] text-card-foreground shadow-lift'
      : 'border-white/44 bg-white/58 text-muted-foreground hover:border-primary/10 hover:bg-white/76 hover:text-card-foreground hover:shadow-soft',
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
  const tabRefs = useRef<Record<HomeTabId, HTMLButtonElement | null>>({
    mine: null,
    partner: null,
    card: null,
  });
  const [focusedTab, setFocusedTab] = useState<HomeTabId>(() => activeTab as HomeTabId);

  const mastheadCopy = useMemo<Record<HomeTabId, MastheadCopy>>(
    () => ({
      mine: {
        eyebrow: 'Private Edition',
        title: '把今天先寫成一頁，再讓其他東西慢慢展開。',
        description:
          '首頁不該一開始就要求你處理所有事情。它應該先讓你把今天最真的那一段留下來，再決定什麼值得被看見、被靠近、被延續。',
        ritualTitle: '回來的第一步，不是處理，而是安頓。',
        ritualDescription:
          '先把自己的語氣與感受寫下來，首頁才有資格變成陪伴，而不是另一個吵雜的控制面板。',
        atmosphereTitle: '今天的主場仍然屬於你自己。',
        atmosphereDescription:
          '就算伴侶那邊有新的內容，這一頁也會先保護你的節奏。寫完，再看；先對自己誠實，再對彼此靠近。',
        houseRuleTitle: '先寫自己，再讀彼此。',
        houseRuleDescription:
          '首頁的寫作區不是任務輸入框，而是一張私人的稿頁。它先服務真實，再服務整理。',
      },
      partner: {
        eyebrow: 'Reading Room',
        title: '把對方今天留下的內容，當成一封只屬於你們的來信。',
        description:
          '這裡刻意降低通知感、效率感與回覆壓力。你不是在清訊息，而是在進入一個更安靜、更有閱讀空氣的親密區域。',
        ritualTitle: '閱讀，也是一種靠近的儀式。',
        ritualDescription:
          'Haven 把伴侶內容從提醒邏輯裡抽離，改成一個會被慢慢展開的閱讀節奏。先理解，再回應；先停一下，再更靠近。',
        atmosphereTitle: '這裡只保留真正值得慢慢讀的那幾頁。',
        atmosphereDescription:
          '首頁不是 badge 清單，也不是待辦通知中心。它更像是稿頁架，讓新的內容被妥善放下，而不是被粗暴消耗。',
        houseRuleTitle: '先讀懂，再回答。',
        houseRuleDescription:
          '伴侶來信被排成一段閱讀經驗，而不是推著你快點處理的訊號流。',
      },
      card: {
        eyebrow: 'Night Ritual',
        title: '把今晚最值得一起完成的問題，留在唯一的聚光區。',
        description:
          '當首頁切到每日儀式，它就不應該再像 dashboard。它應該像一個被單獨點亮的 ritual stage，讓你們把注意力集中在今晚真正重要的那一件事。',
        ritualTitle: '一個好的 ritual，需要足夠明確的重心。',
        ritualDescription:
          '抽卡、回答、等待與揭曉，本來就該有自己的節奏。首頁會刻意把周圍聲音降下來，只讓那張卡成為今晚的主角。',
        atmosphereTitle: '不是更多內容，而是更好的聚焦。',
        atmosphereDescription:
          '把 ritual 留在唯一的舞台上，會比把它塞進一堆並列卡片裡更有重量，也更值得完成。',
        houseRuleTitle: '今晚只留一個聚光區。',
        houseRuleDescription:
          'Daily ritual 的價值，不在於它是首頁上的一個元件，而在於它有沒有成為今晚真正的重心。',
      },
    }),
    [],
  );

  const tabDescriptors = useMemo<Record<HomeTabId, TabDescriptor>>(
    () => ({
      mine: {
        label: '我的空間',
        caption: '先把今天寫成一頁',
        icon: User,
      },
      partner: {
        label: '伴侶來信',
        caption: '把對方的內容慢慢讀開',
        icon: BookHeart,
      },
      card: {
        label: '每日儀式',
        caption: '讓今晚只留下唯一重點',
        icon: Sparkles,
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
          eyebrow: 'Gentle Prompt',
          title: primarySyncNudge.title,
          description: primarySyncNudge.description,
          actionLabel: '稍後再提醒',
          onAction: onAckSyncNudge,
        }
      : nextOnboardingStep && !nextOnboardingStep.completed
        ? {
            eyebrow: `Onboarding Day ${nextOnboardingStep.quest_day}`,
            title: nextOnboardingStep.title,
            description: '首頁會保留一條清楚但不吵雜的前進線索，讓你知道下一步在哪裡。',
            actionLabel: '繼續新手引導',
            onAction: onActivateOnboardingStep,
          }
        : {
            eyebrow: 'House Note',
            title: '讓首頁先成為一個會讓人想停留的地方。',
            description: '真正 premium 的首頁，不靠資訊密度取勝，而靠選擇什麼先出現、什麼暫時安靜。',
          };

  const questMeta =
    nextOnboardingStep && !nextOnboardingStep.completed
      ? `新手引導 Day ${nextOnboardingStep.quest_day} · ${nextOnboardingStep.title}`
      : `本週進度 ${onboardingQuest.completed_steps}/${onboardingQuest.total_steps}`;

  return (
    <section className="space-y-6">
      <div className="home-surface-cover relative overflow-hidden rounded-[3.35rem] p-6 md:p-8 xl:p-10">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.76),transparent_36%),radial-gradient(circle_at_86%_12%,rgba(255,255,255,0.32),transparent_24%)]" aria-hidden />
        <div className="pointer-events-none absolute right-[-5rem] top-[-2rem] h-80 w-80 rounded-full bg-primary/10 blur-hero-orb" aria-hidden />
        <div className="pointer-events-none absolute bottom-[-3rem] left-[-2rem] h-72 w-72 rounded-full bg-accent/10 blur-hero-orb-sm" aria-hidden />

        <div className="relative z-10 grid gap-6 2xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="stack-section">
            <div className="flex flex-wrap items-center gap-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/54 bg-white/74 px-4 py-2 shadow-soft">
                <span className="h-2 w-2 rounded-full bg-primary/75" aria-hidden />
                <span className="type-micro uppercase text-primary/82">Today&apos;s Edition</span>
              </div>
              <div className="inline-flex items-center rounded-full border border-white/48 bg-white/66 px-4 py-2 shadow-soft">
                <span className="type-caption text-card-foreground">{questMeta}</span>
              </div>
            </div>

            <div className="stack-block max-w-[58rem]">
              <p className="type-micro uppercase text-primary/80">{activeMasthead.eyebrow}</p>
              <h1 className="max-w-[54rem] type-h1 text-card-foreground">{activeMasthead.title}</h1>
              <p className="max-w-[46rem] type-body-muted text-muted-foreground">{activeMasthead.description}</p>
            </div>

            <div className="flex flex-wrap gap-3">
              <EditorialMetricPill
                icon={Flame}
                label="連續互動"
                value={`${gamificationSummary.streak_days} 天`}
                className="min-w-[156px]"
              />
              <EditorialMetricPill
                icon={Heart}
                label="關係脈搏"
                value={`${savingsScore} 分`}
                tone="sage"
                className="min-w-[150px]"
              />
              <div className="inline-flex items-center gap-3 rounded-full border border-white/50 bg-white/70 px-4 py-3 shadow-soft backdrop-blur-md">
                <span className="type-micro uppercase text-primary/80">Flow</span>
                <span className="type-caption text-card-foreground">
                  {activeTab === 'mine'
                    ? '先寫，再看。'
                    : activeTab === 'partner'
                      ? '先讀，再回應。'
                      : '先專注，再揭曉。'}
                </span>
              </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.08fr)_minmax(280px,0.92fr)]">
              <EditorialPaperCard
                eyebrow="Return Ritual"
                title={activeMasthead.ritualTitle}
                description={activeMasthead.ritualDescription}
                tone="paper"
                className="h-full rounded-[2.35rem]"
              >
                <div className="rounded-[1.6rem] border border-white/46 bg-white/68 p-4 shadow-soft">
                  <p className="type-body-muted text-card-foreground">
                    {activeTab === 'mine'
                      ? '首頁先把一整頁交還給你，不急著把你推進其他提醒。'
                      : activeTab === 'partner'
                        ? '把伴侶的內容讀成來信，而不是看成等待清空的 badge。'
                        : '如果今晚只做一件有份量的事，讓它是被好好完成的一個 ritual。'}
                  </p>
                </div>
              </EditorialPaperCard>

              <EditorialPaperCard
                eyebrow="Atmosphere"
                title={activeMasthead.atmosphereTitle}
                description={activeMasthead.atmosphereDescription}
                tone="mist"
                className="h-full rounded-[2.35rem]"
              >
                <div className="flex flex-wrap gap-2">
                  <span className="inline-flex items-center rounded-full bg-primary/10 px-3 py-1.5 type-caption text-card-foreground">
                    {tabDescriptors[activeTab as HomeTabId].label}
                  </span>
                  <span className="inline-flex items-center rounded-full bg-white/74 px-3 py-1.5 type-caption text-card-foreground">
                    {hasNewPartnerContent ? '有新的 partner content' : '低噪音首頁'}
                  </span>
                  <span className="inline-flex items-center rounded-full bg-accent/12 px-3 py-1.5 type-caption text-card-foreground">
                    {gamificationSummary.streak_days > 0 ? `已連續 ${gamificationSummary.streak_days} 天` : '今天重新開始也可以'}
                  </span>
                </div>
              </EditorialPaperCard>
            </div>
          </div>

          <div className="stack-section 2xl:pt-3">
            <HomeRailNav>
              <div className="stack-block">
                <div className="px-2 stack-block">
                  <p className="type-micro uppercase text-primary/80">Choose the chapter</p>
                  <p className="type-caption text-muted-foreground">
                    首頁不是控制台，而是一個被選擇的進入方式。
                  </p>
                </div>

                <div
                  role="tablist"
                  aria-label="主頁分頁"
                  className="grid gap-2"
                  onFocusCapture={handleTabListFocusCapture}
                  onKeyDown={handleTabListKeyDown}
                >
                  {HOME_TAB_ORDER.map((tabId) => {
                    const descriptor = tabDescriptors[tabId];
                    const isActive = activeTab === tabId;
                    const Icon = descriptor.icon;

                    return (
                      <button
                        key={tabId}
                        ref={(el) => {
                          tabRefs.current[tabId] = el;
                        }}
                        type="button"
                        role="tab"
                        id={`home-tab-${tabId}`}
                        aria-selected={isActive}
                        aria-controls={`home-tabpanel-${tabId}`}
                        tabIndex={focusedTab === tabId ? 0 : -1}
                        onFocus={() => setFocusedTab(tabId)}
                        onClick={() => onTabChange(tabId)}
                        className={getMastheadButtonClass(isActive)}
                      >
                        <span
                          className={cn(
                            'flex h-11 w-11 shrink-0 items-center justify-center rounded-[1.2rem] border bg-white/78 shadow-soft transition-all duration-haven ease-haven',
                            isActive ? 'border-primary/18 text-primary' : 'border-white/48 text-muted-foreground group-hover:text-card-foreground',
                          )}
                        >
                          <Icon className="h-4 w-4" strokeWidth={2.2} aria-hidden />
                        </span>
                        <div className="min-w-0 stack-block">
                          <div className="stack-inline justify-between">
                            <span className="type-section-title text-card-foreground">{descriptor.label}</span>
                            {tabId === 'partner' && hasNewPartnerContent ? (
                              <span className="inline-flex h-2.5 w-2.5 rounded-full bg-primary/75 shadow-[0_0_0_7px_rgba(201,163,100,0.12)]" aria-hidden />
                            ) : null}
                          </div>
                          <p className="type-caption text-muted-foreground">{descriptor.caption}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </HomeRailNav>

            <NoticeCard {...headerNotice} />

            <EditorialPaperCard
              eyebrow="House Rule"
              title={activeMasthead.houseRuleTitle}
              description={activeMasthead.houseRuleDescription}
              tone="mist"
              className="rounded-[2.2rem]"
            >
              <div className="flex flex-wrap gap-2">
                <span className="inline-flex items-center rounded-full bg-white/74 px-3 py-1.5 type-caption text-card-foreground">
                  {activeTab === 'mine' ? 'Writing first' : activeTab === 'partner' ? 'Reading before reacting' : 'One ritual, one focus'}
                </span>
                <span className="inline-flex items-center rounded-full bg-primary/10 px-3 py-1.5 type-caption text-card-foreground">
                  {showFirstDelightCard ? '首頁有新的亮點提醒' : '首頁保留安靜節奏'}
                </span>
              </div>
            </EditorialPaperCard>
          </div>
        </div>
      </div>
    </section>
  );
}
