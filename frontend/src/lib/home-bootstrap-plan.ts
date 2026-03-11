export type HomeTab = 'mine' | 'partner' | 'card';

export interface HomeBootstrapPlan {
  loadMineJournals: boolean;
  loadPartnerJournals: boolean;
  loadHeaderEnhancements: boolean;
  loadMineSecondaryCards: boolean;
}

export function buildHomeBootstrapPlan(
  activeTab: HomeTab,
  enableNonCriticalData: boolean,
): HomeBootstrapPlan {
  return {
    loadMineJournals: activeTab === 'mine',
    loadPartnerJournals: activeTab === 'partner',
    loadHeaderEnhancements: enableNonCriticalData,
    loadMineSecondaryCards: activeTab === 'mine' && enableNonCriticalData,
  };
}
