"use strict";
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/index.ts
var index_exports = {};
__export(index_exports, {
  CardCategory: () => CardCategory,
  MAX_JOURNAL_CONTENT_LENGTH: () => MAX_JOURNAL_CONTENT_LENGTH,
  queryKeys: () => queryKeys
});
module.exports = __toCommonJS(index_exports);

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
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  CardCategory,
  MAX_JOURNAL_CONTENT_LENGTH,
  queryKeys
});
