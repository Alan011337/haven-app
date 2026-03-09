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
  handleAnswerChange: (value: string) => void;
  handleSubmit: () => Promise<void>;
  handleNextCard: () => void;
  handleBackToDecks: () => void;
  quotaExceeded?: boolean;
  handleUpgrade?: () => void;
}
