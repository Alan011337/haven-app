# Haven Feature Truth Map

**Source**: [FEATURE_VERIFICATION_MATRIX.md](FEATURE_VERIFICATION_MATRIX.md)  
**Date**: Current session  
**What this is**: Decision-oriented grouping of all 17 features by implementation completeness

---

## ✅ CONFIRMED END-TO-END (Ready for production)

All 7 layers verified. No gaps. High confidence.

| Feature | Status | What's Wired | Confidence |
|---------|--------|-------------|------------|
| **Authentication** | 🟢 Complete | Login, register, token refresh, partner pairing (invite code + pair endpoints) | High |
| **Home Page** | 🟢 Complete | Root page pulls 6+ data feeds in parallel (journals, partner status, daily sync, appreciations, love languages, gamification) | High |
| **Journals + AI Analysis** | 🟢 Complete | Create/read/delete journals; AI tagging on create; analysis stored and retrievable | High |
| **Decks / Card Rituals** | 🟢 Complete | Draw card → respond → store response; full history view; category filtering | High |
| **Appreciation** | 🟢 Complete | Create/read appreciation items; display on home | High |
| **Memory Archive** | 🟢 Complete | Timeline, calendar, time-capsule, relationship reports (aggregates journals, card responses, analyses) | High |
| **Settings** | 🟢 Complete | Multi-system integration (profile, pairing, billing, notifications, couple goals, baseline setup) | High |
| **Billing (Checkout)** | 🟢 Complete | Create checkout session → Stripe integration; entitlements tracking; webhook handling | High |

**Total**: 8 features fully operational

---

## ⚠️ LIKELY WORKING BUT GAPS REMAIN (Likely operational; needs verification)

6/7 layers confirmed. Minor integration gaps.

| Feature | Status | Gap | What's Wired | What Needs Verification | Confidence |
|---------|--------|-----|-------------|------------------------|------------|
| **Love Map** | 🟡 95% | Service call not traced | Frontend page + hook exist; backend routes ready (GET/POST notes, safety tiers) | Confirm `api.post()` call in service file | Med-High |
| **Mediation** | 🟡 85% | Frontend service integration unclear | Backend repair flow complete (start/answer/step-complete); UI components in place | Find service wrapper; confirm API calls from components | Medium |
| **Daily Sync** | 🟡 85% | Service wrapper location unclear | Component renders on home; hook exists; backend endpoints ready | Find service file; confirm `api.get('/daily-sync/status')` call | Medium |
| **Blueprint** | 🟡 90% | Service call chain not traced | Frontend page + hook exist; backend endpoints ready (GET/POST items, date suggestions) | Confirm `api.post()` call in service file | Med-High |
| **Cool-Down SOS** | 🟡 80% | Service call + enforcement unclear | Component on home; hook exists; backend endpoints ready (status, start, rewrite) | Verify API calls; confirm enforcement (actions blocked during cooldown) | Med-High |
| **Notifications** | 🟡 80% | Frontend service integration unclear | Page exists; backend routes exist; models ready | Find service integration; confirm notification fetch + delivery | Medium |
| **Admin / Moderation** | 🟡 85% | Service pattern not explicit | Page + backend routes exist; models in place | Clarify if direct API calls or service wrapper; verify permission checks | Medium |

**Total**: 7 features likely working; all need 1-2 layers confirmed

---

## 🔴 UNCLEAR / INCOMPLETE (Needs investigation or rework)

Models or routes exist but execution chain is broken or major pieces missing.

| Feature | Status | What Exists | What's Missing | Blocker | Confidence |
|---------|--------|------------|-----------------|---------|------------|
| **Gamification** | 🔴 Partial | Models (`GamificationScoreEvent`, `UserStreakSummary`); frontend displays score in header | No dedicated `/api/gamification/*` endpoint; unclear where score is calculated or fetched | Unknown: Is score calculated real-time in user profile? Cached elsewhere? Need backend clarity | Low |
| **Analysis Dashboard** | 🔴 Partial | Page exists; backend reports routes exist; `RelationshipRadarCard` component exists | No confirmed data pipeline from page → service → backend; unclear what analyses are computed | Unknown: What data should populate dashboard? Which backend reports feed it? Need product clarity | Low |

**Total**: 2 features with unknown or incomplete pipelines

---

## SUMMARY TABLE

| Category | Count | Features |
|----------|-------|----------|
| 🟢 Ready (7/7 layers) | 8 | Auth, Home, Journals, Decks, Appreciation, Memory, Settings, Billing |
| 🟡 Mostly ready (6/7 layers) | 7 | Love Map, Mediation, Daily Sync, Blueprint, Cool-Down, Notifications, Admin |
| 🔴 Unclear/blocked | 2 | Gamification, Analysis |

**Product Readiness**: 8/17 features fully shipable. 7/17 need minor wiring confirmation. 2/17 need investigation.

---

## HOW TO USE THIS

**For Product**:
- 8 features are safe to describe as fully operational
- 7 features should be treated as "likely working but verify" before marketing
- 2 features need product/tech alignment before proceeding

**For Engineering**:
- 7 features marked 🟡 have low-effort closure paths (trace 1-2 missing layers)
- 2 features marked 🔴 need product requirements clarification before coding

**For Prioritization**:
- If goals: Close the 🟡 gaps first (highest ROI — 80% done)
- If uncertain: Investigate the 🔴 features (product clarity needed before tech decisions)
