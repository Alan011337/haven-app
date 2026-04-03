'use client';

import Link from 'next/link';
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

        <div className="mx-auto mt-4 max-w-[980px] rounded-[1.75rem] border border-white/48 bg-white/68 px-5 py-4 shadow-soft backdrop-blur-xl">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <p className="text-sm leading-7 text-muted-foreground">
              今天的 ritual 先留在這裡；如果某個節奏值得留下更久，就帶去 Relationship System。
            </p>
            <Link
              href="/love-map"
              className="inline-flex shrink-0 items-center justify-center gap-2 rounded-full border border-white/58 bg-white/82 px-5 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
            >
              進入 Relationship System
            </Link>
          </div>
        </div>
      </div>
    </HomeCoverStage>
  );
}
