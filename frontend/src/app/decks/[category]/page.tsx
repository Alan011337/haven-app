'use client';

import dynamic from 'next/dynamic';
import { useDeckRoom } from '@/features/deck-room/useDeckRoom';
import { GlassCard } from '@/components/haven/GlassCard';

const DeckRoomView = dynamic(
  () => import('@/features/deck-room/DeckRoomView').then((m) => m.default),
  {
    loading: () => (
      <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.18),transparent_22%),radial-gradient(circle_at_top_right,rgba(210,223,214,0.25),transparent_26%),linear-gradient(180deg,#faf7f2_0%,#f5f2ec_52%,#f2efe8_100%)] px-4 py-6 sm:px-6">
        <div className="mx-auto max-w-5xl space-y-6">
          <GlassCard className="rounded-[2rem] border-white/55 bg-white/78 p-8">
            <div className="space-y-4">
              <div className="h-4 w-24 animate-pulse rounded-full bg-muted" aria-hidden />
              <div className="h-12 w-56 animate-pulse rounded-[1.5rem] bg-muted" aria-hidden />
              <div className="h-5 w-full animate-pulse rounded-full bg-muted" aria-hidden />
            </div>
          </GlassCard>
          <div className="h-[22rem] animate-pulse rounded-[2rem] bg-white/74 shadow-soft" aria-label="載入中" />
          <div className="h-[18rem] animate-pulse rounded-[2rem] bg-white/74 shadow-soft" aria-hidden />
        </div>
      </div>
    ),
  },
);

export default function DeckRoomPage() {
  const viewModel = useDeckRoom();
  return <DeckRoomView {...viewModel} />;
}
