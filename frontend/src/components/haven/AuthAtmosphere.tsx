import type { ReactNode } from 'react';
import { LockKeyhole } from 'lucide-react';

interface AuthAtmosphereProps {
  headingId: string;
  brandLine: string;
  children: ReactNode;
}

/**
 * AuthAtmosphere — login-only shell.
 *
 * Desktop: asymmetric split (brand panel left ≈ 55%, form panel right ≈ 45%).
 * Mobile: brand zone stacks above form — nothing is hidden.
 *
 * Uses only existing Haven tokens: bg-auth-gradient, text-gradient-gold,
 * shadow-soft, section-divider, blur-hero-orb, animate-float/slide-up-fade.
 */
export function AuthAtmosphere({
  headingId,
  brandLine,
  children,
}: AuthAtmosphereProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-background">
      {/* ── Desktop: asymmetric split | Mobile: stacked ── */}
      <div className="relative z-10 flex min-h-screen flex-col lg:flex-row">

        {/* ═══ Brand panel (left on desktop, top on mobile) ═══ */}
        <div className="relative flex flex-col justify-center overflow-hidden bg-auth-gradient px-6 py-14 sm:px-10 sm:py-16 lg:w-[54%] lg:px-14 lg:py-0 xl:w-[56%] xl:px-20">
          {/* Atmospheric gradient layers */}
          <div
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_72%_52%_at_22%_18%,rgba(214,168,124,0.16),transparent_68%),radial-gradient(ellipse_56%_48%_at_78%_82%,rgba(137,154,141,0.12),transparent_64%)]"
            aria-hidden
          />
          {/* Floating orbs */}
          <div
            className="pointer-events-none absolute left-[10%] top-[16%] h-56 w-56 rounded-full bg-primary/10 blur-hero-orb animate-float"
            aria-hidden
          />
          <div
            className="pointer-events-none absolute bottom-[12%] right-[14%] h-44 w-44 rounded-full bg-accent/10 blur-hero-orb-sm animate-float-delayed"
            aria-hidden
          />
          {/* Top accent line */}
          <div
            className="pointer-events-none absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-primary/25 to-transparent lg:inset-x-14"
            aria-hidden
          />

          {/* Brand content */}
          <div className="relative z-10 mx-auto w-full max-w-lg lg:max-w-xl xl:max-w-2xl">
            {/* Eyebrow pill */}
            <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-primary/12 bg-white/50 px-3.5 py-1.5 text-[0.66rem] uppercase tracking-[0.3em] text-primary/80 shadow-soft backdrop-blur-md sm:mb-10 animate-slide-up-fade">
              <span className="h-1.5 w-1.5 rounded-full bg-primary/60" aria-hidden />
              Invite-only Beta
            </div>

            {/* Wordmark */}
            <h1 className="font-art text-6xl text-gradient-gold tracking-tight sm:text-7xl lg:text-8xl xl:text-[6.5rem] animate-slide-up-fade-1">
              Haven
            </h1>

            {/* Brand line */}
            <p className="mt-5 max-w-md font-art text-lg leading-relaxed text-foreground/60 sm:mt-6 sm:text-xl lg:text-[1.35rem] animate-slide-up-fade-2">
              {brandLine}
            </p>

            {/* Editorial separator — desktop only */}
            <div className="mt-10 hidden lg:block animate-slide-up-fade-3" aria-hidden>
              <div className="section-divider max-w-[12rem]" />
            </div>
          </div>
        </div>

        {/* ═══ Form panel (right on desktop, bottom on mobile) ═══ */}
        <div className="relative flex flex-1 flex-col items-center justify-center px-6 py-10 sm:px-10 sm:py-14 lg:px-12 xl:px-16">
          {/* Subtle background wash for form side */}
          <div
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_0%,rgba(214,168,124,0.05),transparent_70%)]"
            aria-hidden
          />

          <div className="relative z-10 w-full max-w-[26rem]">
            {/* Form heading zone */}
            <div className="mb-8 space-y-2 animate-slide-up-fade">
              <p className="text-[0.68rem] uppercase tracking-[0.32em] text-primary/70">
                Welcome back
              </p>
              <h2 id={headingId} className="font-art text-[1.85rem] leading-tight text-foreground sm:text-[2.1rem]">
                登入你的空間
              </h2>
            </div>

            {/* Form surface */}
            <div className="w-full rounded-[2rem] border border-white/50 bg-white/60 p-6 shadow-soft backdrop-blur-xl sm:p-8 animate-slide-up-fade-1">
              {children}
            </div>

            {/* Trust badge */}
            <div className="mt-6 flex justify-center animate-slide-up-fade-2">
              <div className="inline-flex items-center gap-2 text-[0.7rem] text-muted-foreground/70">
                <LockKeyhole className="h-3 w-3" aria-hidden />
                <span>端對端加密 · 隱私優先</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
