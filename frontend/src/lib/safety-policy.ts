// frontend/src/lib/safety-policy.ts

export type SafetyTierLevel = 0 | 1 | 2 | 3;

export type SafetyTierBehavior = {
  tier: SafetyTierLevel;
  label: string;
  partnerJournalBehavior: 'normal' | 'nudge' | 'hide_with_cooldown' | 'force_lock';
  showCrisisResources: boolean;
  cooldownMinutes: number;
  bannerComponent: 'none' | 'elevated_banner' | 'safety_banner' | 'force_lock_banner';
  description: string;
};

export const CRISIS_HOTLINES = [
  { name: '安心專線', number: '1925', href: 'tel:1925' },
  { name: '保護專線', number: '113', href: 'tel:113' },
] as const;

export const SAFETY_TIER_POLICY: Record<SafetyTierLevel, SafetyTierBehavior> = {
  0: {
    tier: 0,
    label: '正常',
    partnerJournalBehavior: 'normal',
    showCrisisResources: false,
    cooldownMinutes: 0,
    bannerComponent: 'none',
    description: '一切正常，完整顯示所有伴侶日記內容與建議。',
  },
  1: {
    tier: 1,
    label: '需關懷',
    partnerJournalBehavior: 'nudge',
    showCrisisResources: false,
    cooldownMinutes: 0,
    bannerComponent: 'elevated_banner',
    description: '輕度情緒波動。顯示溫和的提醒橫幅，但內容正常呈現。',
  },
  2: {
    tier: 2,
    label: '安全優先',
    partnerJournalBehavior: 'hide_with_cooldown',
    showCrisisResources: true,
    cooldownMinutes: 10,
    bannerComponent: 'safety_banner',
    description: '偵測到自傷/危機訊號。隱藏敏感內容，需點擊才能查看，並顯示危機求助資源。',
  },
  3: {
    tier: 3,
    label: '強制鎖定',
    partnerJournalBehavior: 'force_lock',
    showCrisisResources: true,
    cooldownMinutes: 30,
    bannerComponent: 'force_lock_banner',
    description: '偵測到暴力/嚴重危機。強制鎖定所有內容，30 秒冷靜期後才可解鎖，並醒目顯示緊急求助資源。',
  },
};

export function resolveSafetyTierBehavior(tier: number): SafetyTierBehavior {
  const normalized = Math.max(0, Math.min(3, Math.floor(Number(tier) || 0)));
  return SAFETY_TIER_POLICY[normalized as SafetyTierLevel];
}
