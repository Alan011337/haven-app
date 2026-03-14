'use client';

import { MoonStar } from 'lucide-react';
import DailyCard from '@/components/features/DailyCard';

export default function CardTabContent() {
  return (
    <div className="flex flex-col gap-10 md:gap-14">

      {/* ═══ 1. Context line ═══ */}
      <section className="space-y-4">
        <div className="flex items-center gap-3 animate-slide-up-fade">
          <MoonStar className="h-4 w-4 shrink-0 text-primary/60" aria-hidden />
          <p className="text-sm text-muted-foreground">今晚的儀式，只留在這裡。</p>
        </div>
      </section>

      {/* ═══ 2. Ritual card — the sole focus ═══ */}
      <div className="relative animate-slide-up-fade-1">
        <div
          className="pointer-events-none absolute inset-x-6 top-4 h-64 rounded-full bg-primary/8 blur-hero-orb"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute inset-x-20 top-16 h-48 rounded-full bg-accent/8 blur-hero-orb-sm"
          aria-hidden
        />

        <div className="home-surface-ritual relative mx-auto w-full max-w-[980px] rounded-[2.8rem] p-4 md:p-7">
          <DailyCard />
        </div>
      </div>
    </div>
  );
}
