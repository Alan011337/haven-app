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
    handleActivateOnboardingStep,
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
    <div className="home-backdrop-cover relative flex min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-ethereal-mesh opacity-40" aria-hidden />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.62),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(228,238,231,0.34),transparent_30%)]" aria-hidden />
      <div className="pointer-events-none absolute -left-20 top-24 h-72 w-72 rounded-full bg-primary/7 blur-hero-orb animate-float" aria-hidden />
      <div className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 rounded-full bg-accent/8 blur-hero-orb animate-float-delayed" aria-hidden />
      <Sidebar variant="home" />

      <main className="relative z-10 flex-1 px-4 pb-14 pt-16 transition-all duration-haven ease-haven md:pl-[7rem] md:pr-10 md:pt-8 xl:pr-16">
        <div className="mx-auto max-w-[1480px] space-y-[var(--space-page)]">
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
              onActivateOnboardingStep={handleActivateOnboardingStep}
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
          <div className="w-full max-w-3xl rounded-[2.9rem] border border-white/45 bg-white/78 p-8 shadow-lift backdrop-blur-xl animate-slide-up-fade md:p-10">
            <div className="mb-5 type-micro uppercase text-primary/80">Home Loading</div>
            <div className="grid items-center gap-5 md:grid-cols-[auto_minmax(0,1fr)]">
              <div className="relative">
                <div className="absolute inset-0 rounded-full bg-primary/15 blur-hero-orb-sm animate-breathe" aria-hidden />
                <Loader2 className="relative z-10 h-10 w-10 animate-spin text-primary" />
              </div>
              <div className="stack-block">
                <p className="type-h3 text-card-foreground">正在準備你的首頁…</p>
                <p className="type-body-muted text-muted-foreground">
                  把今天真正值得被看見的那幾件事，重新排成一個更安靜的順序。
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
