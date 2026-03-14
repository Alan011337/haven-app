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
      description="這裡不該像一張卡片被塞進首頁，而應該像一個被單獨打亮的 ritual stage。抽卡、回答、等待與揭曉，都需要更安靜、更有重力的中心。"
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
          tone="mist"
          className="rounded-[2.25rem]"
        >
          <div className="flex flex-wrap gap-2">
            <Badge variant="status">Ritual Stage</Badge>
            <Badge variant="metadata">Focus Mode</Badge>
          </div>
        </EditorialPaperCard>
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
