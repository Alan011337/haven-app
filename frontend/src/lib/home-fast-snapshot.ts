import type { PartnerStatus, OnboardingQuestStepKey } from '@/services/api-client.types';
import type { DailySyncStatusPublic } from '@/services/daily-sync-api';

const PARTNER_STATUS_TTL_MS = 6 * 60 * 60 * 1000;

type StoredSnapshot<T> = {
  savedAt: number;
  payload: T;
};

type DailySyncStatusSnapshot = Omit<
  DailySyncStatusPublic,
  'my_answer_text' | 'partner_answer_text' | 'my_question_id' | 'partner_question_id'
> & {
  my_answer_text: null;
  partner_answer_text: null;
  my_question_id: null;
  partner_question_id: null;
};

function getUtcTodayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function buildKey(scope: 'partner-status' | 'daily-sync', userId: string): string {
  return `haven:home:${scope}:${userId}`;
}

function readSnapshot<T>(key: string): StoredSnapshot<T> | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredSnapshot<T>;
    if (!parsed || typeof parsed !== 'object') return null;
    if (typeof parsed.savedAt !== 'number' || !('payload' in parsed)) return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeSnapshot<T>(key: string, payload: T) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(
      key,
      JSON.stringify({
        savedAt: Date.now(),
        payload,
      } satisfies StoredSnapshot<T>),
    );
  } catch {
    // Ignore storage failures; snapshot is an optimization only.
  }
}

function removeSnapshot(key: string) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Ignore storage failures; snapshot is an optimization only.
  }
}

export function readPartnerStatusSnapshot(userId: string): PartnerStatus | null {
  const snapshot = readSnapshot<PartnerStatus>(buildKey('partner-status', userId));
  if (!snapshot) return null;
  if (Date.now() - snapshot.savedAt > PARTNER_STATUS_TTL_MS) {
    removeSnapshot(buildKey('partner-status', userId));
    return null;
  }
  return snapshot.payload;
}

export function writePartnerStatusSnapshot(userId: string, status: PartnerStatus) {
  writeSnapshot(buildKey('partner-status', userId), status);
}

export function sanitizeDailySyncStatusForSnapshot(
  status: DailySyncStatusPublic,
): DailySyncStatusSnapshot {
  return {
    today: status.today,
    my_filled: status.my_filled,
    partner_filled: status.partner_filled,
    unlocked: status.unlocked,
    my_mood_score: status.my_mood_score,
    my_question_id: null,
    my_answer_text: null,
    partner_mood_score: status.partner_mood_score,
    partner_question_id: null,
    partner_answer_text: null,
    today_question_id: status.today_question_id,
    today_question_label: status.today_question_label,
  };
}

export function readDailySyncStatusSnapshot(userId: string): DailySyncStatusPublic | null {
  const snapshot = readSnapshot<DailySyncStatusSnapshot>(buildKey('daily-sync', userId));
  if (!snapshot) return null;
  if (snapshot.payload.today !== getUtcTodayIso()) {
    removeSnapshot(buildKey('daily-sync', userId));
    return null;
  }
  return snapshot.payload;
}

export function writeDailySyncStatusSnapshot(userId: string, status: DailySyncStatusPublic) {
  writeSnapshot(buildKey('daily-sync', userId), sanitizeDailySyncStatusForSnapshot(status));
}

export function resolveHomeOnboardingStepHref(
  stepKey: OnboardingQuestStepKey,
): '/' | '/settings#onboarding-consent-card' | '/settings' | '/?tab=partner' | '/?tab=card' {
  switch (stepKey) {
    case 'ACCEPT_TERMS':
      return '/settings#onboarding-consent-card';
    case 'BIND_PARTNER':
      return '/settings';
    case 'RESPOND_FIRST_CARD':
    case 'PAIR_CARD_EXCHANGE':
      return '/?tab=card';
    case 'PARTNER_FIRST_JOURNAL':
      return '/?tab=partner';
    case 'CREATE_FIRST_JOURNAL':
    case 'PAIR_STREAK_2_DAYS':
    default:
      return '/';
  }
}

export function resolveOnboardingStepActionLabel(stepKey: OnboardingQuestStepKey): string {
  switch (stepKey) {
    case 'ACCEPT_TERMS':
      return '在這裡完成條款與隱私設定';
    case 'BIND_PARTNER':
      return '前往連結伴侶';
    case 'RESPOND_FIRST_CARD':
      return '前往完成第一張卡片';
    case 'PARTNER_FIRST_JOURNAL':
      return '前往查看伴侶來信';
    case 'PAIR_CARD_EXCHANGE':
      return '前往完成雙向卡片交換';
    case 'CREATE_FIRST_JOURNAL':
      return '前往寫下第一篇日記';
    case 'PAIR_STREAK_2_DAYS':
    default:
      return '回首頁繼續累積互動';
  }
}
