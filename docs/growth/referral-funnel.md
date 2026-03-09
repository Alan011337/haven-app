# Referral Funnel（P1）

## Why
- 建立 `view -> signup -> bind` 的最小可用歸因骨架，先確保資料一致、可去重、可回溯。
- 事件資料只保存 hash 與 UUID，不落地 email / IP / token。

## How
- 新增事件表：`growth_referral_events`
  - 事件型別：`LANDING_VIEW`、`SIGNUP`、`COUPLE_INVITE`、`BIND`
  - 去重鍵：`dedupe_key`（唯一索引）
  - 主要欄位：`invite_code_hash`、`inviter_user_id`、`actor_user_id`、`source`
- 新增 API：
  - `POST /api/users/referrals/landing-view`（public）
  - `POST /api/users/referrals/signup`（authenticated）
  - `POST /api/users/referrals/couple-invite`（authenticated）
- 前端串接：
  - `register` 頁面偵測 `?invite=`，呼叫 `landing-view` 並快取 referral context。
  - `login` 成功後，若本地有 referral context，呼叫 `signup`；成功後清除本地 context，並導向 `/settings` 讓使用者直接完成伴侶綁定。
  - `settings` 頁面複製邀請連結時，呼叫 `couple-invite`，紀錄 `share_channel=link_copy`。
- 既有配對成功流程 `POST /api/users/pair` 追加 `BIND` 事件追蹤（失敗不阻斷主流程）。
- 受 server-side feature flag 與 kill-switch 控制：
  - `growth_referral_enabled`
  - `disable_referral_funnel`
  - `disable_growth_events_ingest`

## What
- Migration：`backend/alembic/versions/d7e8f9a0b1c2_add_growth_referral_events_table.py`
- Model：`backend/app/models/growth_referral_event.py`
- Service：`backend/app/services/referral_funnel.py`
- Router：`backend/app/api/routers/users.py`
- Tests：`backend/tests/test_referral_funnel_api.py`
- Security matrix：`docs/security/endpoint-authorization-matrix.json`
- Frontend tracking：`frontend/src/lib/referral.ts`、`frontend/src/app/register/page.tsx`、`frontend/src/app/login/page.tsx`
- E2E smoke：`frontend/e2e/smoke.spec.ts`

## DoD
- Landing/Signup/CoupleInvite/Bind 四類事件都可落地且可去重。
- Signup 事件不可被 overpost `actor_user_id`（BOLA 防護）。
- CoupleInvite 事件需校驗 `invite_code` 屬於目前登入者，避免冒用他人邀請碼。
- Referral 追蹤關閉時請求仍回應成功語意（降級不阻斷主流程）。
- API inventory + authorization matrix policy 測試維持綠燈。

## Debug Checklist
1. Landing 命中量明顯偏低：
   - 檢查 `growth_referral_enabled` 與 `disable_referral_funnel`。
2. 轉換率異常偏高：
   - 查 `dedupe_key` 生成是否穩定、前端 `event_id` 是否重複使用。
3. Bind 事件缺失：
   - 檢查 `/api/users/pair` 是否成功 commit，以及 log 中 `referral_bind_tracking_failed`。
4. Couple invite 事件缺失：
   - 檢查 `/api/users/referrals/couple-invite` 是否回傳 403（常見為 invite code 不屬於 current user）。
