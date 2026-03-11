export const DAILY_CARD_IDLE_POLL_MS = 20_000;
export const DAILY_CARD_WAITING_PARTNER_POLL_MS = 12_000;
export const DAILY_CARD_HIDDEN_MULTIPLIER = 4;

type DailyCardPollingStatus = {
  state?: 'IDLE' | 'PARTNER_STARTED' | 'WAITING_PARTNER' | 'COMPLETED' | string | null;
  card?: unknown;
} | null | undefined;

export function resolveDailyCardPollingIntervalMs(status: DailyCardPollingStatus): number | null {
  if (!status?.card) {
    return DAILY_CARD_IDLE_POLL_MS;
  }
  if (status.state === 'WAITING_PARTNER') {
    return DAILY_CARD_WAITING_PARTNER_POLL_MS;
  }
  return null;
}
