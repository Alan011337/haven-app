import { capturePosthogEvent } from '@/lib/posthog';

export const REALTIME_FALLBACK_EVENT = 'haven:realtime-fallback';

export type RealtimeFallbackReason =
  | 'feature_disabled'
  | 'max_reconnect_exceeded'
  | 'max_reconnect_exceeded_server_pressure'
  | 'auth_or_policy'
  | 'socket_recovered';

export interface RealtimeFallbackDetail {
  active: boolean;
  reason: RealtimeFallbackReason | string;
}

export function emitRealtimeFallback(
  active: boolean,
  reason: RealtimeFallbackReason | string,
  extra: Record<string, unknown> = {},
): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(
    new CustomEvent<RealtimeFallbackDetail>(REALTIME_FALLBACK_EVENT, {
      detail: { active, reason },
    }),
  );
  if (active) {
    capturePosthogEvent('realtime_fallback_activated', {
      reason,
      ...extra,
    });
  }
}

