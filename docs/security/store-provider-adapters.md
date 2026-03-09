# Store provider adapters (MON-03)

## Scope
Stripe webhook ingestion and state transitions are implemented. This doc describes the adapter interface and intended file locations for **Apple App Store** and **Google Play** provider ingestion so that Stripe + iOS + Android provider ingestion and normalized state transitions can be completed (MON-03 DoD).

## Current state
- **Stripe**: Implemented in `backend/app/api/routers/billing.py` — webhook handlers for `customer.subscription.*`, signature verification, idempotency, state machine (`_ALLOWED_TRANSITIONS`, `_TRANSITION_TO_STATE`). Markers: `customer.subscription.*`.
- **Store docs**: `docs/security/store-compliance-matrix.json` (ios_app_store, google_play); `docs/security/billing-grace-account-hold-policy.json` (stripe, google_play, app_store). Contract scripts and tests expect `googleplay.subscription.*` and `appstore.subscription.*` event types.

## Adapter interface (intended)
Each store provider adapter should:
1. **Receive** webhook payloads from the store (Apple Server Notifications V2, Google Real-time Developer Notifications).
2. **Verify** payload authenticity (signature / signed JWT / shared secret per store docs).
3. **Normalize** to internal events that map to `_TRANSITION_TO_STATE` (e.g. `appstore.subscription.billing_retry` → GRACE_PERIOD, `googleplay.subscription.recovered` → ACTIVE).
4. **Extract** user/customer/subscription identifiers and call the same ledger + binding helpers used by Stripe (`_find_or_create_billing_binding`, `_apply_state_change`, etc.) so state transitions and entitlement updates are consistent.

## Intended file locations
- **Router entry**: New routes under `backend/app/api/routers/billing.py` (or a dedicated `billing_webhooks.py`) for:
  - `POST /api/billing/webhooks/appstore` — Apple Server Notifications V2.
  - `POST /api/billing/webhooks/googleplay` — Google Pub/Sub or direct RTDN endpoint.
- **Adapters**: Optional dedicated modules for parsing and verification, e.g.:
  - `backend/app/services/billing/appstore_webhook.py` — verify Apple JWT, parse notification payload, map to internal event type.
  - `backend/app/services/billing/googleplay_webhook.py` — verify Google RTDN, parse subscription notification, map to internal event type.
- **Shared**: Continue using existing billing state machine, idempotency (e.g. by provider + provider_subscription_id + event_id), and ledger logic in `billing.py`.

## Rollback
- Provider-specific feature flags (e.g. `BILLING_APPSTORE_WEBHOOKS_ENABLED`) so Apple/Google ingestion can be turned off without affecting Stripe.
- Keep Stripe as single provider until adapters are implemented and tested.
