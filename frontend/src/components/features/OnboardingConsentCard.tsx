"use client";

import { useState, useEffect, useCallback } from "react";
import { Shield, Loader2 } from "lucide-react";
import { GlassCard } from "@/components/haven/GlassCard";
import {
  fetchOnboardingConsent,
  upsertOnboardingConsent,
  type OnboardingConsentPublic,
  type OnboardingConsentCreate,
} from "@/services/user";
import { logClientError } from "@/lib/safe-error-log";
import { useToast } from "@/hooks/useToast";

type NotifFreq = "off" | "low" | "normal" | "high";
type AIIntensity = "gentle" | "direct";

export default function OnboardingConsentCard() {
  const [consent, setConsent] = useState<OnboardingConsentPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [privacyScope, setPrivacyScope] = useState(true);
  const [notificationFrequency, setNotificationFrequency] = useState<NotifFreq>("normal");
  const [aiIntensity, setAIIntensity] = useState<AIIntensity>("gentle");
  const { showToast } = useToast();

  const load = useCallback(async () => {
    try {
      const data = await fetchOnboardingConsent();
      setConsent(data);
      if (data) {
        setPrivacyScope(data.privacy_scope_accepted);
        setNotificationFrequency(data.notification_frequency as NotifFreq);
        setAIIntensity(data.ai_intensity as AIIntensity);
      }
    } catch (e) {
      logClientError("onboarding-consent-fetch-failed", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const body: OnboardingConsentCreate = {
        privacy_scope_accepted: privacyScope,
        notification_frequency: notificationFrequency,
        ai_intensity: aiIntensity,
      };
      const updated = await upsertOnboardingConsent(body);
      setConsent(updated);
      showToast("已儲存安全感與通知設定", "success");
    } catch (e) {
      logClientError("onboarding-consent-save-failed", e);
      showToast("儲存失敗，請稍後再試", "error");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <GlassCard className="max-w-4xl mx-auto w-full mb-6 p-6 flex items-center justify-center min-h-[120px]">
        <Loader2 className="w-6 h-6 animate-spin text-primary" aria-hidden />
      </GlassCard>
    );
  }

  return (
    <GlassCard className="max-w-4xl mx-auto w-full mb-6 p-6 relative overflow-hidden">
      <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/30 to-transparent" aria-hidden />
      <h2 className="text-title font-art font-semibold text-foreground mb-2 flex items-center gap-2">
        <span className="icon-badge" aria-hidden><Shield className="w-4 h-4" /></span>
        安全感與通知
      </h2>
      <p className="text-caption text-muted-foreground mb-4">
        隱私範圍、通知頻率與 AI 介入強度（溫和引導或直接點出）。
      </p>
      <div className="space-y-4">
        <label className="flex items-center gap-3 cursor-pointer animate-slide-up-fade">
          <input
            type="checkbox"
            checked={privacyScope}
            onChange={(e) => setPrivacyScope(e.target.checked)}
            className="rounded border-border h-5 w-5 text-primary focus-visible:ring-2 focus-visible:ring-ring"
            aria-describedby="privacy-desc"
          />
          <span id="privacy-desc" className="text-body text-foreground">
            我同意目前的隱私範圍與資料使用方式
          </span>
        </label>
        <div>
          <label htmlFor="notification-frequency" className="block text-body text-foreground font-medium mb-1">
            通知頻率
          </label>
          <select
            id="notification-frequency"
            value={notificationFrequency}
            onChange={(e) => setNotificationFrequency(e.target.value as NotifFreq)}
            className="select-premium w-full max-w-xs"
          >
            <option value="low">較少</option>
            <option value="normal">一般</option>
            <option value="high">較多</option>
            <option value="off">關閉 Email 備援</option>
          </select>
        </div>
        <div>
          <label htmlFor="ai-intensity" className="block text-body text-foreground font-medium mb-1">
            AI 介入強度
          </label>
          <select
            id="ai-intensity"
            value={aiIntensity}
            onChange={(e) => setAIIntensity(e.target.value as AIIntensity)}
            className="select-premium w-full max-w-xs"
          >
            <option value="gentle">溫和引導</option>
            <option value="direct">直接點出</option>
          </select>
        </div>
        {consent?.updated_at && (
          <p className="text-caption text-muted-foreground tabular-nums">
            上次更新：{new Date(consent.updated_at).toLocaleString("zh-TW")}
          </p>
        )}
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="rounded-button bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-t border-t-white/30 px-5 py-2.5 font-medium shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-60"
        >
          {saving ? (
            <span className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
              儲存中...
            </span>
          ) : (
            "儲存設定"
          )}
        </button>
      </div>
    </GlassCard>
  );
}
