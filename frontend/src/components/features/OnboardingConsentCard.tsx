"use client";

import Link from "next/link";
import { useState, useEffect, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  BellRing,
  Bot,
  Database,
  ExternalLink,
  Loader2,
  Shield,
  SlidersHorizontal,
} from "lucide-react";
import { GlassCard } from "@/components/haven/GlassCard";
import Button from "@/components/ui/Button";
import {
  fetchOnboardingConsent,
  upsertOnboardingConsent,
  type OnboardingConsentPublic,
  type OnboardingConsentCreate,
} from "@/services/user";
import { logClientError } from "@/lib/safe-error-log";
import { queryKeys } from "@/lib/query-keys";
import { useToast } from "@/hooks/useToast";

type NotifFreq = "off" | "low" | "normal" | "high";
type AIIntensity = "gentle" | "direct";

type OnboardingConsentCardProps = {
  mode?: "settings" | "onboarding";
};

const TRUST_EXPLAINER_ITEMS = [
  {
    title: "資料範圍",
    description:
      "Haven 會保存帳號資訊、日記與卡片回應、同意紀錄，以及必要的安全與裝置資料。",
    icon: Database,
  },
  {
    title: "使用方式",
    description:
      "這些資料會用來提供核心功能、產生 AI 洞察、保護帳號安全，並以匿名或統計方式改善產品。",
    icon: Shield,
  },
  {
    title: "你的控制權",
    description:
      "你可以調整通知頻率、AI 介入強度，之後也能在設定裡查閱、匯出或刪除自己的資料。",
    icon: SlidersHorizontal,
  },
] as const;

export default function OnboardingConsentCard({
  mode = "settings",
}: OnboardingConsentCardProps) {
  const queryClient = useQueryClient();
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

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const body: OnboardingConsentCreate = {
        privacy_scope_accepted: privacyScope,
        notification_frequency: notificationFrequency,
        ai_intensity: aiIntensity,
      };
      const updated = await upsertOnboardingConsent(body);
      setConsent(updated);
      await queryClient.invalidateQueries({ queryKey: queryKeys.onboardingQuest() });
      showToast("已儲存安全感與通知設定", "success");
    } catch (e) {
      logClientError("onboarding-consent-save-failed", e);
      showToast("儲存失敗，請稍後再試", "error");
    } finally {
      setSaving(false);
    }
  }, [aiIntensity, notificationFrequency, privacyScope, queryClient, showToast]);

  if (loading) {
    return (
      <GlassCard className="max-w-4xl mx-auto w-full mb-6 p-6 flex items-center justify-center min-h-[120px]">
        <Loader2 className="w-6 h-6 animate-spin text-primary" aria-hidden />
      </GlassCard>
    );
  }

  return (
    <GlassCard id="onboarding-consent-card" className="max-w-4xl mx-auto w-full mb-6 p-6 relative overflow-hidden">
      <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/30 to-transparent" aria-hidden />
      <h2 className="mb-2 stack-inline type-h3 text-foreground">
        <span className="icon-badge" aria-hidden><Shield className="w-4 h-4" /></span>
        {mode === "onboarding" ? "隱私、通知與 AI 偏好" : "安全感與通知"}
      </h2>
      <p className="mb-4 type-body-muted text-muted-foreground">
        {mode === "onboarding"
          ? "註冊時已完成最小法遵同意；這一步把隱私範圍、通知節奏與 AI 介入方式講清楚，讓你在正式開始前知道 Haven 會怎麼運作。"
          : "隱私範圍、通知頻率與 AI 介入強度（溫和引導或直接點出）。"}
      </p>

      {mode === "onboarding" ? (
        <div className="mb-5 grid gap-3 md:grid-cols-3">
          {TRUST_EXPLAINER_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.title}
                className="surface-card rounded-[1.3rem] bg-white/70 p-4"
              >
                <div className="stack-inline">
                  <span className="icon-badge" aria-hidden>
                    <Icon className="h-4 w-4" />
                  </span>
                  <p className="type-section-title text-foreground">{item.title}</p>
                </div>
                <p className="mt-3 type-caption text-muted-foreground">
                  {item.description}
                </p>
              </div>
            );
          })}
        </div>
      ) : null}

      <div className="space-y-4">
        {mode === "onboarding" ? (
          <div className="rounded-[1.3rem] border border-primary/12 bg-primary/6 p-4 stack-block">
            <p className="type-micro uppercase text-primary/70">
              你現在確認的是什麼
            </p>
            <ul className="mt-3 space-y-2 type-caption text-foreground">
              <li>1. Haven 可以在目前政策範圍內處理你的帳號、互動與安全資料。</li>
              <li>2. 你希望通知偏向安靜還是積極提醒。</li>
              <li>3. AI 在首頁與互動流程中要採溫和引導，還是更直接的提示方式。</li>
            </ul>
            <div className="mt-4 flex flex-wrap gap-3 text-sm">
              <Link
                href="/legal/privacy"
                className="inline-flex items-center gap-[var(--space-inline)] rounded-button border border-white/60 bg-white/80 px-3 py-2 type-label text-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
              >
                閱讀隱私權政策
                <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              </Link>
              <Link
                href="/legal/terms"
                className="inline-flex items-center gap-[var(--space-inline)] rounded-button border border-white/60 bg-white/80 px-3 py-2 type-label text-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
              >
                閱讀服務條款
                <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              </Link>
            </div>
          </div>
        ) : null}

        <label className="flex items-center gap-3 cursor-pointer animate-slide-up-fade">
          <input
            type="checkbox"
            checked={privacyScope}
            onChange={(e) => setPrivacyScope(e.target.checked)}
            className="rounded border-border h-5 w-5 text-primary focus-visible:ring-2 focus-visible:ring-ring"
            aria-describedby="privacy-desc"
          />
          <span id="privacy-desc" className="type-body text-foreground">
            {mode === "onboarding"
              ? "我已閱讀上方摘要，並同意 Haven 依目前政策範圍處理我的資料與互動紀錄"
              : "我同意目前的隱私範圍與資料使用方式"}
          </span>
        </label>
        <div>
          <label htmlFor="notification-frequency" className="mb-1 block type-section-title text-foreground">
            <span className="inline-flex items-center gap-[var(--space-inline)]">
              <BellRing className="h-4 w-4 text-primary/80" aria-hidden />
              通知頻率
            </span>
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
          {mode === "onboarding" ? (
            <p className="mt-2 type-caption text-muted-foreground">
              「較少」適合想把提醒降到最低的人；「一般」適合大多數使用者；「較多」會更主動提醒你跟上儀式與互動節奏。
            </p>
          ) : null}
        </div>
        <div>
          <label htmlFor="ai-intensity" className="mb-1 block type-section-title text-foreground">
            <span className="inline-flex items-center gap-[var(--space-inline)]">
              <Bot className="h-4 w-4 text-primary/80" aria-hidden />
              AI 介入強度
            </span>
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
          {mode === "onboarding" ? (
            <p className="mt-2 type-caption text-muted-foreground">
              溫和引導會先給你線索與提問；直接點出會更明白地指出模式、盲點與下一步建議。
            </p>
          ) : null}
        </div>
        {consent?.updated_at && (
          <p className="type-caption tabular-nums text-muted-foreground">
            上次更新：{new Date(consent.updated_at).toLocaleString("zh-TW")}
          </p>
        )}
        {mode === "onboarding" ? (
          <p className="type-caption leading-6 text-muted-foreground">
            完整法律條文與資料權利仍以「服務條款」和「隱私權政策」為準；這一頁的角色是先把你真正會碰到的資料使用方式與可調設定講清楚。
          </p>
        ) : null}
        <Button type="button" onClick={handleSave} disabled={saving} loading={saving} className="w-fit">
          {saving ? "儲存中..." : "儲存設定"}
        </Button>
      </div>
    </GlassCard>
  );
}
