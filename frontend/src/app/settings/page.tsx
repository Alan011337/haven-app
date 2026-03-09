// frontend/src/app/settings/page.tsx
"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { ArrowLeft, Settings, Sparkles, Vibrate, Volume2 } from "lucide-react";
import { GlassCard } from "@/components/haven/GlassCard";
import Skeleton from "@/components/ui/Skeleton";
import { useAppearanceStore } from "@/stores/useAppearanceStore";

const SettingsPageBody = dynamic(
  () => import("./SettingsPageBody").then((m) => m.default),
  {
    ssr: false,
    loading: () => (
      <div className="max-w-4xl mx-auto w-full space-y-4 animate-page-enter-delay-1">
        <Skeleton className="h-24 w-full rounded-card" variant="shimmer" aria-hidden />
        <Skeleton className="h-24 w-full rounded-card" variant="shimmer" aria-hidden />
        <Skeleton className="h-32 w-full rounded-card" variant="shimmer" aria-hidden />
      </div>
    ),
  },
);

/* Inline toggle switch — brand-colored pill */
function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`
        relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent
        transition-colors duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background
        ${checked ? 'bg-primary shadow-satin-button' : 'bg-muted-foreground/25'}
      `}
    >
      <span
        className={`
          pointer-events-none block h-4 w-4 rounded-full bg-white shadow-sm ring-0
          transition-transform duration-haven ease-haven-spring
          ${checked ? 'translate-x-5' : 'translate-x-0.5'}
        `}
      />
    </button>
  );
}

export default function SettingsPage() {
  const router = useRouter();
  const cardGlowEnabled = useAppearanceStore((s) => s.cardGlowEnabled);
  const setCardGlowEnabled = useAppearanceStore((s) => s.setCardGlowEnabled);
  const hapticsEnabled = useAppearanceStore((s) => s.hapticsEnabled);
  const setHapticsEnabled = useAppearanceStore((s) => s.setHapticsEnabled);
  const hapticStrength = useAppearanceStore((s) => s.hapticStrength);
  const setHapticStrength = useAppearanceStore((s) => s.setHapticStrength);
  const soundEnabled = useAppearanceStore((s) => s.soundEnabled);
  const setSoundEnabled = useAppearanceStore((s) => s.setSoundEnabled);

  return (
    <div className="min-h-screen bg-muted/40 space-page flex flex-col">
      {/* Back nav + page heading */}
      <div className="max-w-4xl mx-auto w-full mb-8 animate-page-enter">
        <button
          type="button"
          onClick={() => router.push("/")}
          className="group flex items-center text-muted-foreground hover:text-card-foreground transition-all duration-haven ease-haven font-medium px-4 py-2 rounded-button hover:bg-card/80 hover:shadow-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          aria-label="返回首頁"
        >
          <div className="bg-card p-1.5 rounded-full shadow-soft border border-border/60 mr-3 group-hover:border-primary/20 transition-all duration-haven ease-haven" aria-hidden>
            <ArrowLeft className="w-4 h-4" />
          </div>
          回首頁
        </button>

        <div className="mt-6 flex items-center gap-3">
          <span className="icon-badge !w-10 !h-10 !rounded-2xl" aria-hidden>
            <Settings className="w-5 h-5" />
          </span>
          <div>
            <h1 className="text-title font-art font-bold text-card-foreground tracking-tight">設定</h1>
            <p className="text-caption text-muted-foreground">自訂你的 Haven 體驗</p>
          </div>
        </div>
      </div>

      {/* Appearance section */}
      <GlassCard className="max-w-4xl mx-auto w-full mb-6 p-6 relative overflow-hidden animate-page-enter-delay-1">
        {/* top accent */}
        <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/30 to-transparent" aria-hidden />

        <h2 className="text-body font-art font-semibold text-foreground mb-5 flex items-center gap-2">
          <span className="icon-badge" aria-hidden><Sparkles className="w-4 h-4" /></span>
          外觀偏好
        </h2>

        <div className="space-y-5">
          {/* Card glow */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="icon-badge" aria-hidden>
                <Sparkles className="w-4 h-4" />
              </span>
              <div>
                <span className="text-body text-foreground font-medium">卡片解鎖發光效果</span>
                <p className="text-caption text-muted-foreground">抽卡解鎖時的光暈動畫</p>
              </div>
            </div>
            <Toggle checked={cardGlowEnabled} onChange={setCardGlowEnabled} label="卡片解鎖發光效果" />
          </div>

          <div className="section-divider" />

          {/* Haptics */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="icon-badge" aria-hidden>
                <Vibrate className="w-4 h-4" />
              </span>
              <div>
                <span className="text-body text-foreground font-medium">觸覺回饋</span>
                <p className="text-caption text-muted-foreground">互動時的震動反饋</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {hapticsEnabled && (
                <select
                  value={hapticStrength}
                  onChange={(e) => setHapticStrength(e.target.value as 'light' | 'medium')}
                  className="rounded-xl border border-border/60 bg-muted/40 px-3 py-1 text-caption text-foreground transition-all duration-haven ease-haven focus-visible:ring-2 focus-visible:ring-ring focus-visible:shadow-focus-glow"
                >
                  <option value="light">輕</option>
                  <option value="medium">中</option>
                </select>
              )}
              <Toggle checked={hapticsEnabled} onChange={setHapticsEnabled} label="觸覺回饋" />
            </div>
          </div>

          <div className="section-divider" />

          {/* Sound */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="icon-badge" aria-hidden>
                <Volume2 className="w-4 h-4" />
              </span>
              <div>
                <span className="text-body text-foreground font-medium">音效</span>
                <p className="text-caption text-muted-foreground">抽卡與解鎖的音效反饋</p>
              </div>
            </div>
            <Toggle checked={soundEnabled} onChange={setSoundEnabled} label="音效" />
          </div>
        </div>
      </GlassCard>

      <SettingsPageBody />
    </div>
  );
}