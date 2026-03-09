# N+1 / query batching audit (Batch 2)

Hot-path endpoints and services audited for "session.get / session.exec inside loop". Fixes applied where found.

## Fixes applied

| Location | Issue | Change |
|----------|--------|--------|
| `backend/app/services/active_care.py` | `pairs_with_no_interaction_3_days`: loop over users did `session.get(User, pid)` and `get_last_pair_interaction_at()` (2N+2 queries) | Batch load all partners with one `select(User).where(User.id.in_(partner_ids))`; batch compute last activity per user with two grouped queries (`Journal.user_id, max(created_at)` and `CardResponse.user_id, max(created_at)`); in-loop logic uses preloaded dicts. Total queries: 1 (users) + 1 (partners) + 2 (last activity) = 4. |
| `backend/scripts/run_time_capsule_dispatch.py` | Loop over `users_with_partner` did `session.get(User, partner_id)` per user (N queries) | Collect all `partner_id`s, one `select(User).where(User.id.in_(partner_ids))`, build `partners_by_id` dict; loop uses `partners_by_id.get(partner_id)`. |

## Already batched (no change)

- `backend/app/services/memory_archive.py`: Card and CardResponse loaded in bulk.
- `backend/app/api/routers/card_decks.py`: CardResponse loaded once, keyed by (session_id, user_id); cards loaded by id set.
- `backend/app/api/routers/users/routes.py` (user erase): Batch selects (journals, analyses, sessions, card_responses, notifications) then in-memory delete loop; no per-row DB calls.
- `backend/app/services/data_soft_delete_purge.py`: All candidate/blocked IDs loaded via batch `session.exec(...).all()`; loops are over in-memory lists only.
- Other `session.get` usages: single lookups per request (e.g. get current user's partner once), not in loops.

## Verification

- `pytest backend/tests/` (no dedicated test for active_care; regression via integration if present).
- Manual: run any flow that calls active care (e.g. cron or admin) and confirm no regression.
