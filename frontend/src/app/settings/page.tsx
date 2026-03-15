'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { ArrowLeft, Sparkles, Vibrate, Volume2, Palette } from 'lucide-react';
import SettingsSkeleton from './SettingsSkeleton';
import { useAppearanceStore } from '@/stores/useAppearanceStore';

const SettingsPageBody = dynamic(
  () => import('./SettingsPageBody').then((m) => m.default),
  { loading: () => <SettingsSkeleton /> },
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
  const cardGlowEnabled = useAppearanceStore((s) => s.cardGlowEnabled);
  const setCardGlowEnabled = useAppearanceStore((s) => s.setCardGlowEnabled);
  const hapticsEnabled = useAppearanceStore((s) => s.hapticsEnabled);
  const setHapticsEnabled = useAppearanceStore((s) => s.setHapticsEnabled);
  const hapticStrength = useAppearanceStore((s) => s.hapticStrength);
  const setHapticStrength = useAppearanceStore((s) => s.setHapticStrength);
  const soundEnabled = useAppearanceStore((s) => s.soundEnabled);
  const setSoundEnabled = useAppearanceStore((s) => s.setSoundEnabled);

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.18),transparent_22%),radial-gradient(circle_at_top_right,rgba(210,223,214,0.25),transparent_26%),linear-gradient(180deg,#faf7f2_0%,#f5f2ec_52%,#f2efe8_100%)]">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.72),transparent_62%)]"
        aria-hidden
      />
      <div className="relative mx-auto max-w-3xl space-y-8 px-4 py-6 pb-24 sm:px-6 lg:px-8 md:space-y-10">
        <Link
          href="/"
          className="inline-flex items-center gap-[var(--space-inline)] rounded-button border border-white/60 bg-white/74 px-4 py-2.5 type-label text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
          aria-label="返回首頁"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          回首頁
        </Link>

        {/* Title */}
        <div className="animate-slide-up-fade">
          <h1 className="font-art text-[2rem] leading-[1.05] tracking-tight text-gradient-gold md:text-[2.8rem]">
            偏好設定
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground md:text-base">
            打造屬於你們的 Haven 體驗
          </p>
        </div>

        {/* Appearance section */}
        <section className="animate-slide-up-fade rounded-[2rem] border border-white/50 bg-white/70 p-6 shadow-soft md:p-8">
          <div className="mb-5 flex items-center gap-3">
            <Palette className="h-5 w-5 text-primary/60" aria-hidden />
            <h2 className="font-art text-lg font-medium text-card-foreground">外觀與互動</h2>
          </div>

          <div className="space-y-5">
            {/* Card glow */}
            <div className="flex items-center justify-between">
              <div className="flex items-start gap-3">
                <span className="icon-badge" aria-hidden>
                  <Sparkles className="h-4 w-4" />
                </span>
                <div>
                  <span className="type-section-title text-foreground">卡片解鎖發光效果</span>
                  <p className="type-caption text-muted-foreground">抽卡解鎖時的光暈動畫</p>
                </div>
              </div>
              <Toggle checked={cardGlowEnabled} onChange={setCardGlowEnabled} label="卡片解鎖發光效果" />
            </div>

            <div className="section-divider" />

            {/* Haptics */}
            <div className="flex items-center justify-between">
              <div className="flex items-start gap-3">
                <span className="icon-badge" aria-hidden>
                  <Vibrate className="h-4 w-4" />
                </span>
                <div>
                  <span className="type-section-title text-foreground">觸覺回饋</span>
                  <p className="type-caption text-muted-foreground">互動時的震動反饋</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
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
              <div className="flex items-start gap-3">
                <span className="icon-badge" aria-hidden>
                  <Volume2 className="h-4 w-4" />
                </span>
                <div>
                  <span className="type-section-title text-foreground">音效</span>
                  <p className="type-caption text-muted-foreground">抽卡與解鎖的音效反饋</p>
                </div>
              </div>
              <Toggle checked={soundEnabled} onChange={setSoundEnabled} label="音效" />
            </div>
          </div>
        </section>

        <SettingsPageBody />
      </div>
    </div>
  );
}
