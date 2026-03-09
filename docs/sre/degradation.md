# Degradation Matrix (P1-A)

## Journal
- Normal: write + analysis complete inline/nearline.
- Degraded: write first, analysis async queue, user sees pending indicator.
- Failure UX: show "已儲存，分析稍後送達" and allow manual refresh.

## Card / Ritual
- Normal: draw + full recommendation + unlock flow.
- Degraded: prioritize session consistency (draw/respond/unlock), defer recommendation payload.
- Failure UX: keep session_id contract, show retry affordance.

## Push / WebSocket
- Normal: WS realtime + push/email.
- Degraded: fallback to polling + in-app inbox badge.
- Failure UX: explicit "即時同步暫時延遲" indicator.

## Provider Outage (AI/3rd-party)
- AI outage: accept user write path, enqueue retry, send delayed completion event later.
- Notification outage: persist event for retry; do not block primary CUJ completion.

## Operational Notes
- Degradation mode must be explicit in logs/metrics.
- Recovery path must clear backlog and produce audit evidence.
