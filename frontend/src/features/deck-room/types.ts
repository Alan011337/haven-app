import type { CardSession, DeckHistoryEntry } from '@/services/deckService';

export type RoomStatus = 'IDLE' | 'WAITING_PARTNER' | 'COMPLETED';

export interface DeckRoomViewModel {
  category: string;
  historyHref: string;
  partnerDisplayName: string;
  loading: boolean;
  session: CardSession | null;
  answer: string;
  submitting: boolean;
  partnerTyping: boolean;
  roomStatus: RoomStatus;
  resultData: DeckHistoryEntry | null;
  selectedDepth: 1 | 2 | 3 | null;
  handleDepthChange: (depth: 1 | 2 | 3 | null) => void;
  handleAnswerChange: (value: string) => void;
  handleSubmit: () => Promise<void>;
  handleNextCard: () => void;
  handleBackToDecks: () => void;
  quotaExceeded?: boolean;
  handleUpgrade?: () => void;
}
