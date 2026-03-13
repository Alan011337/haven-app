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
      <div className="mx-auto w-full max-w-4xl stack-section animate-page-enter-delay-1">
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
        transition-colors duration-haven ease-haven focus-ring-premium
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
    <div className="min-h-screen bg-muted/40 px-4 py-[var(--space-page)] md:px-6">
      {/* Back nav + page heading */}
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-[var(--space-section)] animate-page-enter">
        <button
          type="button"
          onClick={() => router.push("/")}
          className="group inline-flex w-fit items-center gap-[var(--space-inline)] rounded-button border border-white/55 bg-card/78 px-4 py-2.5 type-label text-muted-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:border-primary/16 hover:bg-card hover:text-card-foreground hover:shadow-lift focus-ring-premium"
          aria-label="返回首頁"
        >
          <div className="rounded-full border border-border/60 bg-card p-1.5 shadow-soft transition-all duration-haven ease-haven group-hover:border-primary/20" aria-hidden>
            <ArrowLeft className="w-4 h-4" />
          </div>
          回首頁
        </button>

        <div className="stack-inline">
          <span className="icon-badge !w-10 !h-10 !rounded-2xl" aria-hidden>
            <Settings className="w-5 h-5" />
          </span>
          <div className="stack-block">
            <p className="type-micro uppercase text-primary/72">Preference Center</p>
            <h1 className="type-h2 text-card-foreground">設定</h1>
            <p className="type-body-muted text-muted-foreground">把 Haven 的提醒、節奏與陪伴方式調到最適合你們的狀態。</p>
          </div>
        </div>
      </div>

      {/* Appearance section */}
      <GlassCard className="relative mx-auto mb-6 w-full max-w-4xl overflow-hidden p-6 animate-page-enter-delay-1 md:p-7">
        {/* top accent */}
        <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/30 to-transparent" aria-hidden />

        <h2 className="mb-5 stack-inline type-section-title text-foreground">
          <span className="icon-badge" aria-hidden><Sparkles className="w-4 h-4" /></span>
          外觀偏好
        </h2>

        <div className="stack-section">
          {/* Card glow */}
          <div className="flex items-center justify-between">
            <div className="stack-inline items-start">
              <span className="icon-badge" aria-hidden>
                <Sparkles className="w-4 h-4" />
              </span>
              <div className="stack-block">
                <span className="type-section-title text-foreground">卡片解鎖發光效果</span>
                <p className="type-caption text-muted-foreground">抽卡解鎖時的光暈動畫</p>
              </div>
            </div>
            <Toggle checked={cardGlowEnabled} onChange={setCardGlowEnabled} label="卡片解鎖發光效果" />
          </div>

          <div className="section-divider" />

          {/* Haptics */}
          <div className="flex items-center justify-between">
            <div className="stack-inline items-start">
              <span className="icon-badge" aria-hidden>
                <Vibrate className="w-4 h-4" />
              </span>
              <div className="stack-block">
                <span className="type-section-title text-foreground">觸覺回饋</span>
                <p className="type-caption text-muted-foreground">互動時的震動反饋</p>
              </div>
            </div>
            <div className="stack-inline">
              {hapticsEnabled && (
                <select
                  value={hapticStrength}
                  onChange={(e) => setHapticStrength(e.target.value as 'light' | 'medium')}
                  className="select-premium min-w-[5.75rem] text-caption"
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
            <div className="stack-inline items-start">
              <span className="icon-badge" aria-hidden>
                <Volume2 className="w-4 h-4" />
              </span>
              <div className="stack-block">
                <span className="type-section-title text-foreground">音效</span>
                <p className="type-caption text-muted-foreground">抽卡與解鎖的音效反饋</p>
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
