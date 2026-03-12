'use client';

import { MoonStar, Sparkles, Stars } from 'lucide-react';
import DailyCard from '@/components/features/DailyCard';
import Badge from '@/components/ui/Badge';
import { EditorialPaperCard, HomeCoverStage } from '@/features/home/HomePrimitives';

export default function CardTabContent() {
  return (
    <HomeCoverStage
      eyebrow="Daily Ritual"
      title="把今晚最值得一起回答的問題，留在唯一的聚光區。"
      description="這裡不再像一張卡片被塞進首頁，而是一個獨立的儀式場。抽卡、回答、等待與揭曉，都應該有更安靜的重心。"
      pulse={
        <>
          如果今晚只做一件彼此有感的事，
          <strong className="font-medium text-card-foreground"> 讓它是一個被好好完成的 daily ritual。</strong>
        </>
      }
      note={
        <EditorialPaperCard
          eyebrow="Stage Rule"
          title="把 ritual 放在聚光燈下。"
          description="首頁這一頁會刻意減少周圍噪音，只留下今晚真正需要一起完成的那張卡。"
          tone="paper"
          className="rounded-[2rem]"
        >
          <div className="flex flex-wrap gap-2">
            <Badge variant="success">Ritual Stage</Badge>
            <Badge variant="outline">Focus Mode</Badge>
          </div>
        </EditorialPaperCard>
      }
    >
      <div className="relative pt-2">
        <div
          className="pointer-events-none absolute inset-x-6 top-4 h-64 rounded-full bg-primary/10 blur-hero-orb"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute inset-x-20 top-16 h-48 rounded-full bg-accent/10 blur-hero-orb-sm"
          aria-hidden
        />
        <div className="pointer-events-none absolute left-8 top-12 text-primary/20" aria-hidden>
          <Stars className="h-9 w-9" />
        </div>
        <div className="pointer-events-none absolute right-10 top-24 text-accent/25" aria-hidden>
          <Sparkles className="h-8 w-8" />
        </div>
        <div className="pointer-events-none absolute left-1/2 top-0 -translate-x-1/2 text-primary/16" aria-hidden>
          <MoonStar className="h-10 w-10" />
        </div>

        <div className="relative mx-auto w-full max-w-[980px] rounded-[2.5rem] border border-white/48 bg-[linear-gradient(180deg,rgba(255,253,249,0.74),rgba(249,245,239,0.54))] p-4 shadow-lift backdrop-blur-xl md:p-7">
          <DailyCard />
        </div>
      </div>
    </HomeCoverStage>
  );
}
