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
    <div className="flex min-h-screen bg-ethereal-mesh">
      <Sidebar />

      <main className="flex-1 pt-14 md:pt-0 md:ml-64 space-page transition-all duration-haven ease-haven w-full">
        <div className="max-w-4xl mx-auto space-y-[var(--space-page)]">
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
          <div
            id="home-tabpanel-mine"
            role="tabpanel"
            aria-labelledby="home-tab-mine"
            hidden={activeTab !== 'mine'}
            className={activeTab === 'mine' ? 'animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-forwards' : undefined}
          >
            <MineTabContent
              myJournals={myJournals}
              loading={loading}
              onJournalCreated={loadData}
              onJournalDeleted={loadData}
            />
          </div>
          <div
            id="home-tabpanel-partner"
            role="tabpanel"
            aria-labelledby="home-tab-partner"
            hidden={activeTab !== 'partner'}
            className={activeTab === 'partner' ? 'animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-forwards' : undefined}
          >
            <PartnerTabContent
              partnerJournals={partnerJournals}
              loading={loading}
              partnerSafetyBanner={partnerSafetyBanner}
              onRefresh={loadData}
              onDismissSafetyBanner={handleDismissPartnerSafetyBanner}
            />
          </div>
          <div
            id="home-tabpanel-card"
            role="tabpanel"
            aria-labelledby="home-tab-card"
            hidden={activeTab !== 'card'}
            className={activeTab === 'card' ? 'animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-forwards' : undefined}
          >
            <CardTabContent />
          </div>
        </div>
      </main>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-muted/40">
          <div className="flex flex-col items-center gap-4 animate-slide-up-fade">
            <div className="relative">
              <div className="absolute inset-0 bg-primary/15 rounded-full blur-xl animate-breathe" aria-hidden />
              <Loader2 className="w-10 h-10 text-primary animate-spin relative z-10" />
            </div>
            <p className="text-muted-foreground font-art font-medium tracking-[0.2em] text-sm uppercase">Loading Haven...</p>
          </div>
        </div>
      }
    >
      <HomeContent />
    </Suspense>
  );
}
