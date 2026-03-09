// src/types.ts
var CardCategory = /* @__PURE__ */ ((CardCategory2) => {
  CardCategory2["DAILY_VIBE"] = "DAILY_VIBE";
  CardCategory2["SOUL_DIVE"] = "SOUL_DIVE";
  CardCategory2["SAFE_ZONE"] = "SAFE_ZONE";
  CardCategory2["MEMORY_LANE"] = "MEMORY_LANE";
  CardCategory2["GROWTH_QUEST"] = "GROWTH_QUEST";
  CardCategory2["AFTER_DARK"] = "AFTER_DARK";
  CardCategory2["CO_PILOT"] = "CO_PILOT";
  CardCategory2["LOVE_BLUEPRINT"] = "LOVE_BLUEPRINT";
  return CardCategory2;
})(CardCategory || {});

// src/api-types.ts
var MAX_JOURNAL_CONTENT_LENGTH = 4e3;

// src/query-keys.ts
var queryKeys = {
  partnerStatus: () => ["partnerStatus"],
  journals: () => ["journals"],
  partnerJournals: () => ["partnerJournals"],
  gamificationSummary: () => ["gamificationSummary"],
  onboardingQuest: () => ["onboardingQuest"],
  syncNudges: () => ["syncNudges"],
  firstDelight: () => ["firstDelight"],
  deckHistory: (category, range, sort, q) => ["deckHistory", category, range, sort, q],
  deckHistoryInfinite: (category, revealedFrom, revealedTo) => ["deckHistoryInfinite", category, revealedFrom, revealedTo],
  deckHistorySummary: (category, revealedFrom, revealedTo) => ["deckHistorySummary", category, revealedFrom, revealedTo],
  notifications: (params) => ["notifications", params ?? {}],
  notificationStats: (params) => ["notificationStats", params ?? {}],
  user: () => ["user"],
  featureFlags: () => ["featureFlags"],
  loveMapCards: () => ["loveMapCards"],
  loveMapNotes: () => ["loveMapNotes"],
  mediationStatus: () => ["mediationStatus"],
  blueprint: () => ["blueprint"],
  cooldownStatus: () => ["cooldownStatus"],
  dailySyncStatus: () => ["dailySyncStatus"],
  dailyStatus: () => ["dailyStatus"],
  deckCardCounts: () => ["deckCardCounts"]
};
export {
  CardCategory,
  MAX_JOURNAL_CONTENT_LENGTH,
  queryKeys
};
