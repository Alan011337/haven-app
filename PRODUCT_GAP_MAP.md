# Haven Product Gap Map

**Source**: [FEATURE_VERIFICATION_MATRIX.md](FEATURE_VERIFICATION_MATRIX.md)  
**What this is**: For every non-fully-verified feature (9 gaps), actionable breakdown of what exists, what's missing, and next steps

---

## GAP CATEGORY 1: Service Integration Gaps (5 features)
Missing: Frontend service file confirming `api.*()` endpoints actually called

### 1. Love Map

**What Exists Today**:
- ✅ Frontend route: `frontend/src/app/love-map/page.tsx`
- ✅ UI component: `LoveMapPageContent.tsx`
- ✅ Hook file: `useLoveMapQueries.ts` with `useLoveMapCards()`, `useLoveMapNotes()`
- ✅ Backend routes in `/api/routers/love_map.py`:
  - `GET /cards` — fetch safe/medium/deep cards
  - `GET /notes` — fetch partner notes
  - `POST /notes` — create note
  - `PUT /notes/{id}` — update note
- ✅ Route registered in main.py: `(love_map_router, "/love-map", None)`
- ✅ Model: `LoveMapNote` with `layer` (safe/medium/deep)

**What's Missing**:
- ❌ Service file (e.g., `frontend/src/services/love-map-api.ts` or similar) showing explicit `api.get('/api/love-map/cards')` calls
- ❌ Mutation hooks for create/update operations

**Next Step: Verify**:
- [ ] Find where `useLoveMapCards()` hook calls API (grep hooks/queries for fetch function)
- [ ] Confirm `api.get()` or `api.post()` calls to `/love-map/*` endpoints
- [ ] Verify if create/update mutations wired
- **Closure time**: 30 min (read 2-3 files)

**Next Step: Build** (if missing):
- [ ] Create/update service wrapper: `frontend/src/services/love-map-api.ts`
- [ ] Add `api.post('/love-map/notes', ...)` for create
- [ ] Tie hooks to service calls
- **Build time**: 1-2 hours

---

### 2. Blueprint (Wishlist / Couple Goals)

**What Exists Today**:
- ✅ Frontend route: `frontend/src/app/blueprint/page.tsx`
- ✅ UI component: `BlueprintPageContent.tsx`
- ✅ Hook: `useBlueprint()` in queries
- ✅ Backend routes in `/api/routers/blueprint.py`:
  - `GET /` — list items
  - `POST /` — create item
  - `GET /date-suggestions` — AI suggestions
- ✅ Route registered in main.py: `(blueprint_router, "/blueprint", None)`
- ✅ Model: `WishlistItem`

**What's Missing**:
- ❌ Service layer (no explicit `api.post('blueprint', ...)` trace found)
- ❌ Mutation hooks for add/edit/delete

**Next Step: Verify**:
- [ ] Grep `frontend/src/services/` for blueprint service file
- [ ] Confirm `useBlueprint()` hook calls service (likely in hook file directly)
- [ ] Check if TanStack Query mutation exists for POST/PUT/DELETE
- **Closure time**: 30 min

**Next Step: Build** (if missing):
- [ ] Create service: `frontend/src/services/blueprint-api.ts`
- [ ] Add create/update/delete mutations
- [ ] Hook wiring
- **Build time**: 1-2 hours

---

### 3. Daily Sync (3-min mood check-in)

**What Exists Today**:
- ✅ Frontend component: `DailySyncCard.tsx` (renders on home)
- ✅ Hook: `useDailySyncStatus()` (pull status)
- ✅ Backend routes in `/api/routers/daily_sync.py`:
  - `GET /status` — fetch daily sync status
  - `POST /` — create/submit mood
- ✅ Route registered in main.py: `(daily_sync_router, "/daily-sync", None)`
- ✅ Model: `DailySync` with `mood_score` (1-5)

**What's Missing**:
- ❌ No dedicated `daily-sync-api.ts` found (service integration unclear)
- ❌ Mutation hook for submit (only read hook)

**Next Step: Verify**:
- [ ] Search `frontend/src/services/` for daily sync service
- [ ] Check `useDailySyncStatus()` implementation — does it call `api.get()`?
- [ ] Search for mutation hooks (e.g., `useSubmitDailySync`)
- **Closure time**: 15 min

**Next Step: Build** (if missing):
- [ ] Create service: `frontend/src/services/daily-sync-api.ts`
- [ ] Add `api.post('/daily-sync', ...)` for submit
- [ ] Create mutation hook: `useSubmitDailySync()`
- **Build time**: 1 hour

---

### 4. Cool-Down SOS (Conflict time-out)

**What Exists Today**:
- ✅ Frontend component: `CooldownSOSCard.tsx` (on home)
- ✅ Hook: `useCooldownStatus()` (pull status)
- ✅ Backend routes in `/api/routers/cooldown.py`:
  - `GET /status` — check if active
  - `POST /start` — initiate cooldown
  - `POST /rewrite-message` — AI message rewrite
- ✅ Route registered in main.py: `(cooldown_router, "/cooldown", None)`
- ✅ Model: `CoolDownSession`

**What's Missing**:
- ❌ Service file not explicitly located
- ❌ Mutation hook for `useCooldownStart()` (possibly missing)
- ⚠️ **Enforcement logic not verified**: Are actions actually rejected during cooldown? Or just visual blocking?

**Next Step: Verify**:
- [ ] Find service layer (grep for cooldown-api.ts or cooldown service)
- [ ] Confirm mutation hook exists and calls `api.post('/cooldown/start')`
- [ ] **Critical**: Trace enforcement — is cooldown checked on card draw? Journal create? (search for `cooldown_active` checks in backend)
- **Closure time**: 45 min

**Next Step: Build** (if missing):
- [ ] Create service: `frontend/src/services/cooldown-api.ts`
- [ ] Add mutation: `useCooldownStart()`
- [ ] **Backend**: Add cooldown enforcement checks to protected endpoints (journals, decks, etc.)
- **Build time**: 2-3 hours (enforcement work)

---

### 5. Admin / Moderation

**What Exists Today**:
- ✅ Frontend page: `frontend/src/app/admin/moderation/page.tsx`
- ✅ Backend routes in `/api/routers/admin.py`:
  - `GET /moderation/queue` — fetch reports
  - `POST /moderation/{id}/resolve` — resolve report
- ✅ Route registered in main.py: `(admin.router, "/admin", ["admin"])`
- ✅ Model: `ContentReport`

**What's Missing**:
- ❌ Service file pattern unclear (may use direct API calls)
- ❌ No confirmation of admin permission guard

**Next Step: Verify**:
- [ ] Check moderation page component — does it use service wrapper or direct API?
- [ ] Grep for `['admin']` scope checks in backend (is moderation endpoint guarded?)
- **Closure time**: 30 min

**Next Step: Build** (if missing):
- [ ] If no service: Create `frontend/src/services/admin-api.ts`
- [ ] Wrap moderation mutations: `useResolveReport()`, `fetchModerationQueue()`
- [ ] Backend: Ensure `['admin']` scope guard on moderation endpoints
- **Build time**: 1-2 hours

---

## GAP CATEGORY 2: Frontend Integration Gaps (2 features)
Missing: Components or data flow unclear; service/hook integration loose

### 6. Mediation (Conflict Repair)

**What Exists Today**:
- ✅ Frontend route: `frontend/src/app/mediation/page.tsx`
- ✅ UI components: `MediationPageContent.tsx`, `MediationEntryBanner.tsx`
- ✅ Hook: `useMediationStatus()`, `useMediationStatusEnabled()` (read status)
- ✅ Backend routes in `/api/routers/mediation.py`:
  - `GET /status` — fetch status
  - `POST /answers` — submit answers to prompt
  - `POST /repair/start` — begin repair sequence
  - `GET /repair/status` — fetch current step
  - `POST /repair/step-complete` — advance step
- ✅ Route registered in main.py: `(mediation.router, "/mediation", ["mediation"])`
- ✅ Models: `MediationSession`, `MediationAnswer`

**What's Missing**:
- ❌ **No explicit service file found** (e.g., `mediation-api.ts`) — components may call API directly
- ❌ **No mutation hooks found** for start/answer/step-complete flows
- ❌ **Data flow from page to mutations unclear** — are components using hooks or direct API calls?

**Next Step: Verify**:
- [ ] Open `frontend/src/app/mediation/page.tsx` — what does it import?
- [ ] Check `MediationPageContent.tsx` — does it call service functions or `api.post()` directly?
- [ ] Grep for `useMediation` hooks — find all of them
- [ ] Check if mutations are in hooks/queries or missing entirely
- **Closure time**: 1 hour (need to trace component → service chain)

**Next Step: Build** (if missing):
- [ ] Create service: `frontend/src/services/mediation-api.ts` with:
  - `startRepair()` → `api.post('/mediation/repair/start')`
  - `submitAnswer()` → `api.post('/mediation/answers')`
  - `completeStep()` → `api.post('/mediation/repair/step-complete')`
- [ ] Create mutation hooks: `useStartRepair()`, `useSubmitMediationAnswer()`, `useCompleteRepairStep()`
- [ ] Wire components to use hooks
- **Build time**: 2-3 hours (full flow requires careful UX integration)

---

### 7. Notifications

**What Exists Today**:
- ✅ Frontend page: `frontend/src/app/notifications/page.tsx`
- ✅ Backend models: `NotificationEvent`, `NotificationOutbox`
- ✅ Backend routes (unclear which ones exist — in `users/notification_routes.py`)
- ✅ Route registered in main.py (via users router)

**What's Missing**:
- ❌ **No explicit service file location confirmed** — where is `api.get('/api/notifications')` called?
- ❌ **No hook/service import chain traced** from page
- ❌ **Unclear**: Are notifications fetched on demand or via WebSocket/real-time?
- ❌ **Unclear**: Push notification integration (Firebase? Web Push API?)

**Next Step: Verify**:
- [ ] Open `frontend/src/app/notifications/page.tsx` — what does it import? What hooks?
- [ ] Grep `frontend/src/services/` for notification service
- [ ] Grep `frontend/src/hooks/` for notification hooks
- [ ] Check `backend/app/api/routers/users/notification_routes.py` — what endpoints exist?
- [ ] Confirm route registration in main.py
- **Closure time**: 1 hour

**Next Step: Build** (if missing):
- [ ] Create service: `frontend/src/services/notifications-api.ts` with:
  - `fetchNotifications()` → `api.get('/notifications')`
  - `markAsRead()` → `api.post('/notifications/{id}/mark-read')`
- [ ] Create query hook: `useNotifications()`
- [ ] **Decide**: Real-time via WebSocket or polling?
  - If polling: set up `staleTime` and refetch intervals
  - If WebSocket: implement connection management (out of scope for this gap)
- **Build time**: 2-4 hours (depending on real-time approach)

---

## GAP CATEGORY 3: Unclear Product Intent (2 features)
Missing: Core logic or data pipeline not yet defined

### 8. Gamification (Savings Score + Streaks)

**What Exists Today**:
- ✅ Frontend: Score displayed in `HomeHeader.tsx` via `useGamificationSummary()` hook
- ✅ Hook: `useGamificationSummary()` exists
- ✅ Models: `GamificationScoreEvent`, `UserStreakSummary` exist
- ✅ Frontend displays `savingsScore` somewhere on home

**What's Missing**:
- ❌ **No dedicated `/api/gamification/*` endpoints found**
- ❌ **Unknown**: How is score calculated? Real-time? Cached nightly?
- ❌ **Unknown**: Where is score stored/fetched? User profile? Separate endpoint?
- ❌ **Unknown**: What events increment score? (journal create? card response? daily sync?)

**Next Step: Verify** (requires product + tech conversation):
- [ ] **Product**: Define scoring rules — what actions earn points? How many?
- [ ] **Tech**: Trace where score is calculated — is it in user profile context? Separate computation?
- [ ] Grep backend for "gamification" — find score calculation logic
- [ ] Check if scoring logic exists in `/api/services/` or is it in endpoint handlers?
- **Closure time**: 2-3 hours (discovery + design)

**Next Step: Build**:
Decision tree:
- **If score calculated real-time**: Add fetch endpoint `GET /api/gamification/summary` → compute on-the-fly
- **If score cached daily**: Implement batch job that computes scores nightly, store in `UserStreakSummary`
- **If score stored per-event**: Ensure `GamificationScoreEvent` is populated; add fetch to user profile
- **Build time**: 2-4 hours (implementation depends on architecture choice)

---

### 9. Analysis Dashboard

**What Exists Today**:
- ✅ Frontend route: `frontend/src/app/analysis/page.tsx`
- ✅ Component exists: `RelationshipRadarCard.tsx` (likely used for visualization)
- ✅ Backend route stubs: `backend/app/api/routers/reports.py` with:
  - `POST /` — create report
  - `GET /weekly` — fetch weekly report
- ✅ Route registered in main.py

**What's Missing**:
- ❌ **No confirmed data pipeline** — page → service → backend
- ❌ **No confirmed hook/service integration** — `frontend/src/app/analysis/page.tsx` imports unclear
- ❌ **Unknown**: What analyses are computed? What data feeds the dashboard?
- ❌ **Unknown**: Are reports pre-computed (batch) or on-demand?
- ❌ **Unknown**: What time periods? Weekly? Monthly? All-time?

**Next Step: Verify** (requires product + tech conversation):
- [ ] **Product**: Define dashboard content — what visualizations? What metrics? (relationship score? communication patterns? activity heatmap?)
- [ ] **Tech**: Open analysis page component — what should it display?
- [ ] Check if `RadarCard` is being used; what data does it consume?
- [ ] Grep backend for report generation logic — where does it compute?
- **Closure time**: 2-3 hours (product + tech alignment)

**Next Step: Build**:
- [ ] Define report schema (what metrics to compute)
- [ ] Decide: Pre-computed (nightly batch) or on-demand (slow but current)?
- [ ] Implement report generator service (likely in `backend/app/services/report_generator.py`)
- [ ] Create backend endpoint: `GET /api/reports/weekly` → returns computed analysis
- [ ] Create frontend service/hook to fetch and display
- [ ] Wire UI components (charts, metrics)
- **Build time**: 6-8 hours (full feature)

---

## SUMMARY: NEXT STEPS BY ROI

### 🎯 High ROI (Close gaps in 7 features, highest first)

| Effort | Feature | Why | Time |
|--------|---------|-----|------|
| **Low** | Daily Sync | Service integration ~1 hour; impacts home experience | 1-2h |
| **Low** | Love Map | Service trace + wiring ~1 hour | 1-2h |
| **Low** | Blueprint | Service trace + wiring ~1 hour | 1-2h |
| **Low** | Admin | Permission guard + service wrapper | 1-2h |
| **Medium** | Cool-Down | Service + enforcement logic | 2-3h |
| **Medium** | Mediation | Full flow: components → mutations → backend | 2-3h |
| **Medium** | Notifications | Service + (maybe real-time decision) | 2-4h |

**Total for 🟡 gaps**: ~13-19 hours (closure if all wiring exists)

### 🔴 Unknown/Blocked (Needs product clarification first)

| Feature | Blocker | Decision Needed |
|---------|---------|-----------------|
| Gamification | No endpoint found; unclear scoring logic | Define scoring rules + storage strategy |
| Analysis | No confirmed data pipeline; unclear scope | Define dashboard content + report type |

**Time to clarify**: 1-2 hours (product + tech meeting)  
**Time to build (after clarification)**: 4-6 hours each

---

## CHECKLIST: How to use this

**For Engineering Lead**:
- [ ] Assign someone to verify each 🟡 feature (15-30 min per feature)
- [ ] Prioritize Low-effort closes first (Daily Sync, Love Map, Blueprint = 3 hours)
- [ ] Schedule product meeting for Gamification + Analysis design

**For Product**:
- [ ] Confirm gamification scoring rules
- [ ] Define analysis dashboard metrics
- [ ] Prioritize: Close 7 gaps or clarify 2 blockers first?

**For QA**:
- [ ] After each 🟡 closure, add test cases for service layer (fetch + mutation)
- [ ] For 🔴 features: Hold testing until product decision made
