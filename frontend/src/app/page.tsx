// frontend/src/app/page.tsx

"use client";

import dynamic from 'next/dynamic';
import { Suspense, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import { useHomeData } from '@/features/home/useHomeData';
import HomeHeader from '@/features/home/HomeHeader';
import { useAppearanceStore } from '@/stores/useAppearanceStore';

const MineTabContent = dynamic(
  () => import('@/features/home/MineTabContent').then((m) => m.default),
  { ssr: false, loading: () => <div className="min-h-[40vh] flex items-center justify-center"><div className="relative"><div className="absolute inset-0 bg-primary/10 rounded-full blur-xl animate-breathe" aria-hidden /><Loader2 className="w-8 h-8 animate-spin text-primary relative z-10" /></div></div> },
);

const PartnerTabContent = dynamic(
  () => import('@/features/home/PartnerTabContent').then((m) => m.default),
  { ssr: false, loading: () => <div className="min-h-[40vh] flex items-center justify-center"><div className="relative"><div className="absolute inset-0 bg-primary/10 rounded-full blur-xl animate-breathe" aria-hidden /><Loader2 className="w-8 h-8 animate-spin text-primary relative z-10" /></div></div> },
);

const CardTabContent = dynamic(
  () => import('@/features/home/CardTabContent').then((m) => m.default),
  { ssr: false, loading: () => <div className="min-h-[60vh] flex items-center justify-center"><div className="relative"><div className="absolute inset-0 bg-primary/10 rounded-full blur-xl animate-breathe" aria-hidden /><Loader2 className="w-8 h-8 animate-spin text-primary relative z-10" /></div></div> },
);

function HomeContent() {
  const setLatestMoodLabel = useAppearanceStore((s) => s.setLatestMoodLabel);
  const {
    activeTab,
    myJournals,
    partnerJournals,
    loading,
    mineTimelineUnavailable,
    partnerTimelineUnavailable,
    savingsScore,
    gamificationSummary,
    onboardingQuest,
    syncNudges,
    firstDelight,
    hasNewPartnerContent,
    partnerSafetyBanner,
    nextOnboardingStep,
    primarySyncNudge,
    showFirstDelightCard,
    secondaryContentReady,
    loadData,
    handleTabChange,
    getTabStyle,
    handleDismissPartnerSafetyBanner,
    acknowledgeSyncNudge,
    acknowledgeFirstDelightCard,
  } = useHomeData();

  useEffect(() => {
    if (myJournals?.length) {
      const latest = myJournals[0];
      setLatestMoodLabel(latest?.mood_label ?? null);
    }
  }, [myJournals, setLatestMoodLabel]);

  return (
    <div className="relative flex min-h-screen overflow-hidden bg-[linear-gradient(180deg,rgba(255,252,248,0.98),rgba(248,244,238,0.94))]">
      <div className="pointer-events-none absolute inset-0 bg-ethereal-mesh opacity-55" aria-hidden />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.62),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(228,238,231,0.38),transparent_30%)]" aria-hidden />
      <div className="pointer-events-none absolute -left-20 top-24 h-72 w-72 rounded-full bg-primary/8 blur-hero-orb" aria-hidden />
      <div className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 rounded-full bg-accent/10 blur-hero-orb" aria-hidden />
      <Sidebar variant="home" />

      <main className="relative z-10 flex-1 px-4 pb-10 pt-16 transition-all duration-haven ease-haven md:pl-[7.8rem] md:pr-8 md:pt-8 xl:pr-10">
        <div className="mx-auto max-w-[1420px] space-y-[var(--space-page)]">
          <div className="animate-page-enter">
            <HomeHeader
              savingsScore={savingsScore}
              gamificationSummary={gamificationSummary}
              onboardingQuest={onboardingQuest}
              syncNudges={syncNudges}
              firstDelight={firstDelight}
              nextOnboardingStep={nextOnboardingStep}
              primarySyncNudge={primarySyncNudge ?? null}
              showFirstDelightCard={showFirstDelightCard}
              activeTab={activeTab}
              hasNewPartnerContent={hasNewPartnerContent}
              getTabStyle={getTabStyle}
              onTabChange={handleTabChange}
              onAckSyncNudge={acknowledgeSyncNudge}
              onAckFirstDelight={acknowledgeFirstDelightCard}
            />
          </div>

          {/* Panel-enter/reveal: long duration (700ms) is intentional for tab content reveal; excluded from Haven micro-motion tokens (200–240ms) by design. */}
          {activeTab === 'mine' ? (
            <div
              id="home-tabpanel-mine"
              role="tabpanel"
              aria-labelledby="home-tab-mine"
              className="animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-forwards"
            >
              <MineTabContent
                myJournals={myJournals}
                loading={loading}
                timelineUnavailable={mineTimelineUnavailable}
                secondaryContentReady={secondaryContentReady}
                relationshipPulse={{
                  score: savingsScore,
                  streakDays: gamificationSummary.streak_days,
                  hasNewPartnerContent,
                }}
                onJournalCreated={loadData}
                onJournalDeleted={loadData}
                onRetryTimeline={loadData}
              />
            </div>
          ) : null}
          {activeTab === 'partner' ? (
            <div
              id="home-tabpanel-partner"
              role="tabpanel"
              aria-labelledby="home-tab-partner"
              className="animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-forwards"
            >
              <PartnerTabContent
                partnerJournals={partnerJournals}
                loading={loading}
                timelineUnavailable={partnerTimelineUnavailable}
                partnerSafetyBanner={partnerSafetyBanner}
                onRefresh={loadData}
                onDismissSafetyBanner={handleDismissPartnerSafetyBanner}
              />
            </div>
          ) : null}
          {activeTab === 'card' ? (
            <div
              id="home-tabpanel-card"
              role="tabpanel"
              aria-labelledby="home-tab-card"
              className="animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-forwards"
            >
              <CardTabContent />
            </div>
          ) : null}
        </div>
      </main>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-[linear-gradient(180deg,rgba(255,251,246,0.96),rgba(248,244,238,0.94))] px-4">
          <div className="w-full max-w-2xl rounded-[2.4rem] border border-white/45 bg-white/78 p-8 shadow-lift backdrop-blur-xl animate-slide-up-fade md:p-10">
            <div className="mb-5 text-[0.72rem] uppercase tracking-[0.34em] text-primary/80">Home Loading</div>
            <div className="grid items-center gap-5 md:grid-cols-[auto_minmax(0,1fr)]">
              <div className="relative">
                <div className="absolute inset-0 rounded-full bg-primary/15 blur-hero-orb-sm animate-breathe" aria-hidden />
                <Loader2 className="relative z-10 h-10 w-10 animate-spin text-primary" />
              </div>
              <div className="space-y-2">
                <p className="font-art text-2xl text-card-foreground md:text-[2.4rem]">正在整理今天的首頁舞台</p>
                <p className="max-w-xl text-sm leading-7 text-muted-foreground">
                  先讓寫日記成為前景，再把其餘提醒與儀式安靜地排進第二層。
                </p>
              </div>
            </div>
          </div>
        </div>
      }
    >
      <HomeContent />
    </Suspense>
  );
}
