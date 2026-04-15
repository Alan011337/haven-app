// frontend/src/services/user.ts

import api from "@/lib/api";
import { User } from "@/types";

export interface UserMeResponse extends User {
  invite_code?: string;
}

// 定義回傳的資料型別 (必須與後端 Pydantic Schema 一致)
interface InviteCodeResponse {
  code: string;        // 👈 後端給的是 "code"，不是 "invite_code"
  expires_at: string;
}

// 1. 產生邀請碼 (POST /api/users/invite-code)
export const generateInviteCode = async (): Promise<InviteCodeResponse> => {
  const { data } = await api.post<InviteCodeResponse>('/users/invite-code');
  return data;
};

// 2. 進行配對 (POST /users/pair)
// 後端配對成功會回傳更新後的 User 物件 (包含 partner_id)
export const pairWithPartner = async (inviteCode: string): Promise<User> => {
  const { data } = await api.post<User>('/users/pair', {
    invite_code: inviteCode
  });
  return data;
};

// 3. 取得目前使用者資料
export const fetchUserMe = async (): Promise<UserMeResponse> => {
  const { data } = await api.get<UserMeResponse>('/users/me');
  return data;
};

export interface UpdateUserMePayload {
  full_name?: string | null;
  legacy_contact_email?: string | null;
}

export const updateUserMe = async (body: UpdateUserMePayload): Promise<UserMeResponse> => {
  const { data } = await api.patch<UserMeResponse>('/users/me', body);
  return data;
};

// --- Module A1: Onboarding consent ---
export interface OnboardingConsentPublic {
  privacy_scope_accepted: boolean;
  notification_frequency: string;
  ai_intensity: string;
  updated_at: string;
}

export interface OnboardingConsentCreate {
  privacy_scope_accepted: boolean;
  notification_frequency: 'off' | 'low' | 'normal' | 'high';
  ai_intensity: 'gentle' | 'direct';
}

export const fetchOnboardingConsent = async (): Promise<OnboardingConsentPublic | null> => {
  const { data } = await api.get<OnboardingConsentPublic | null>('/users/me/onboarding-consent');
  return data ?? null;
};

export const upsertOnboardingConsent = async (
  body: OnboardingConsentCreate
): Promise<OnboardingConsentPublic> => {
  const { data } = await api.post<OnboardingConsentPublic>('/users/me/onboarding-consent', body);
  return data;
};
