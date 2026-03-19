'use client';

import { MoonStar, Sparkles, Stars } from 'lucide-react';
import DailyCard from '@/components/features/DailyCard';
import { HomeCoverStage } from '@/features/home/HomePrimitives';

export default function CardTabContent() {
  return (
    <HomeCoverStage
      eyebrow="每日儀式"
      title="今晚，只留一個問題給彼此。"
      description="安靜抽一張，慢慢答。"
      pulse={
        <>
          如果今晚只做一件彼此有感的事，
          <strong className="font-medium text-card-foreground"> 讓它是今天最安靜的一刻。</strong>
        </>
      }
    >
      <div className="relative pt-2">
        <div
          className="pointer-events-none absolute inset-x-6 top-4 h-64 rounded-full bg-primary/12 blur-hero-orb"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute inset-x-20 top-16 h-48 rounded-full bg-accent/12 blur-hero-orb-sm"
          aria-hidden
        />
        <div className="pointer-events-none absolute left-8 top-12 text-primary/20" aria-hidden>
          <Stars className="h-8 w-8" />
        </div>
        <div className="pointer-events-none absolute right-10 top-24 text-accent/25" aria-hidden>
          <Sparkles className="h-8 w-8" />
        </div>
        <div className="pointer-events-none absolute left-1/2 top-0 -translate-x-1/2 text-primary/20" aria-hidden>
          <MoonStar className="h-8 w-8" />
        </div>

        <div className="home-surface-ritual relative mx-auto w-full max-w-[980px] rounded-[2.8rem] p-4 md:p-7">
          <DailyCard />
        </div>
      </div>
    </HomeCoverStage>
  );
}
