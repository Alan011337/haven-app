const REFERRAL_INVITE_CODE_KEY = 'haven_referral_invite_code';
const REFERRAL_LANDING_EVENT_ID_KEY = 'haven_referral_landing_event_id';
const REFERRAL_SIGNUP_EVENT_ID_KEY = 'haven_referral_signup_event_id';

function canUseStorage(): boolean {
  return typeof window !== 'undefined' && typeof localStorage !== 'undefined';
}

function generateEventId(prefix: string): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function normalizeInviteCode(value: string | null | undefined): string | null {
  const cleaned = (value || '').trim().toUpperCase();
  if (!cleaned) return null;
  if (cleaned.length > 64) return null;
  if (!/^[A-Z0-9_-]+$/.test(cleaned)) return null;
  return cleaned;
}

export function rememberReferralInviteCode(inviteCode: string): void {
  if (!canUseStorage()) return;
  localStorage.setItem(REFERRAL_INVITE_CODE_KEY, inviteCode);
}

export function readReferralInviteCode(): string | null {
  if (!canUseStorage()) return null;
  return normalizeInviteCode(localStorage.getItem(REFERRAL_INVITE_CODE_KEY));
}

export function getOrCreateReferralLandingEventId(): string {
  if (!canUseStorage()) return generateEventId('landing');
  const existing = localStorage.getItem(REFERRAL_LANDING_EVENT_ID_KEY);
  if (existing) return existing;
  const created = generateEventId('landing');
  localStorage.setItem(REFERRAL_LANDING_EVENT_ID_KEY, created);
  return created;
}

export function getOrCreateReferralSignupEventId(): string {
  if (!canUseStorage()) return generateEventId('signup');
  const existing = localStorage.getItem(REFERRAL_SIGNUP_EVENT_ID_KEY);
  if (existing) return existing;
  const created = generateEventId('signup');
  localStorage.setItem(REFERRAL_SIGNUP_EVENT_ID_KEY, created);
  return created;
}

export function clearReferralTrackingContext(): void {
  if (!canUseStorage()) return;
  localStorage.removeItem(REFERRAL_INVITE_CODE_KEY);
  localStorage.removeItem(REFERRAL_LANDING_EVENT_ID_KEY);
  localStorage.removeItem(REFERRAL_SIGNUP_EVENT_ID_KEY);
}

export function createReferralCoupleInviteEventId(): string {
  return generateEventId('couple-invite');
}

export function buildReferralInviteUrl(inviteCode: string, origin?: string | null): string {
  const normalized = normalizeInviteCode(inviteCode) || inviteCode.trim().toUpperCase();
  const path = `/register?invite=${encodeURIComponent(normalized)}`;
  if (!origin) return path;
  return `${origin.replace(/\/$/, '')}${path}`;
}

export const referralStorageKeys = {
  inviteCode: REFERRAL_INVITE_CODE_KEY,
  landingEventId: REFERRAL_LANDING_EVENT_ID_KEY,
  signupEventId: REFERRAL_SIGNUP_EVENT_ID_KEY,
} as const;
