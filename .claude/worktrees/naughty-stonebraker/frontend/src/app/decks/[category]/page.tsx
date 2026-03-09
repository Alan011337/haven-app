'use client';

import DeckRoomView from '@/features/deck-room/DeckRoomView';
import { useDeckRoom } from '@/features/deck-room/useDeckRoom';

export default function DeckRoomPage() {
  const viewModel = useDeckRoom();
  return <DeckRoomView {...viewModel} />;
}
