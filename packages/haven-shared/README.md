# haven-shared

Shared logic for Haven: **types**, **API contract**, and **query keys** used by both the Next.js web app and the future React Native/Expo app.

## Contents

- **`types`** – Domain models (Journal, User, Card, CardCategory) aligned with backend.
- **`api-types`** – Request/response shapes (CreateJournalOptions, PartnerStatus, DeckHistoryEntry, etc.).
- **`query-keys`** – TanStack Query key factory so cache keys are consistent across web and native.
- **`HavenApiClient`** – Transport-agnostic interface for Core Flow (journal, daily card, deck). Web implements with axios + localStorage; native implements with fetch + AsyncStorage.

## Usage

**Web (frontend):** Add to `package.json`:

```json
"haven-shared": "file:../packages/haven-shared"
```

Then implement `HavenApiClient` in `frontend/src/lib/haven-api-web.ts` (or keep using existing `api` + `api-client` and map to the interface when migrating). Import types/queryKeys from `haven-shared` once ready.

**Native (Phase 1.5):** Create Expo app, add `haven-shared` as dependency, implement `HavenApiClient` with `fetch` + `AsyncStorage`, reuse same hooks or build thin hooks that call the client.

## Build

```bash
cd packages/haven-shared && npm install && npm run build
```

Output: `dist/` (CJS + ESM + `.d.ts`).
