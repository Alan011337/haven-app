'use client';

import DailyCard from '@/components/features/DailyCard';

export default function CardTabContent() {
  return (
    <section className="flex flex-col items-center justify-center py-8 min-h-[60vh]">
      <div className="w-full max-w-2xl transform transition-all duration-haven ease-haven hover:scale-[1.01]">
        <DailyCard />
      </div>
      <p className="mt-8 text-muted-foreground text-sm font-art font-light tracking-widest uppercase opacity-60 animate-slide-up-fade">
        Daily Ritual · Connection
      </p>
    </section>
  );
}
