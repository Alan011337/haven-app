'use client';

import dynamic from 'next/dynamic';
import { useDeckRoom } from '@/features/deck-room/useDeckRoom';
import Skeleton from '@/components/ui/Skeleton';

const DeckRoomView = dynamic(
  () => import('@/features/deck-room/DeckRoomView').then((m) => m.default),
  {
    loading: () => (
      <Skeleton className="min-h-[50vh] w-full rounded-card" aria-label="載入中" />
    ),
  },
);

export default function DeckRoomPage() {
  const viewModel = useDeckRoom();
  return <DeckRoomView {...viewModel} />;
}
