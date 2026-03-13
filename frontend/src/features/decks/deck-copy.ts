import { CardCategory } from '@/types';
import { normalizeDeckCategory } from '@/lib/deck-category';

export type DeckEditorialCopy = {
  eyebrow: string;
  spotlight: string;
  shortHook: string;
  roomPrompt: string;
  archivePrompt: string;
};

export const DECK_EDITORIAL_COPY: Record<CardCategory, DeckEditorialCopy> = {
  [CardCategory.DAILY_VIBE]: {
    eyebrow: '日常節奏',
    spotlight: '把日常的小事，變成今晚最容易說出口的對話。',
    shortHook: '適合用來輕鬆開場，讓彼此重新回到同一個節奏。',
    roomPrompt: '今晚先從日常切口開始，讓話題自然打開。',
    archivePrompt: '這裡收藏你們把日常說成故事的那些片段。',
  },
  [CardCategory.SOUL_DIVE]: {
    eyebrow: '深度探索',
    spotlight: '把關係往更深一層帶，不靠壓迫，只靠真實。',
    shortHook: '適合在你們準備好慢下來的時候，打開更深的理解。',
    roomPrompt: '先給彼此一點安靜，再往更深的地方走。',
    archivePrompt: '這裡會留下你們曾經認真靠近彼此內心的對話。',
  },
  [CardCategory.SAFE_ZONE]: {
    eyebrow: '安全屋',
    spotlight: '先把安全感放回來，對話才有真正被接住的空間。',
    shortHook: '適合在氣氛有點卡住時，先把防備輕輕放下。',
    roomPrompt: '把節奏放慢一點，先確保彼此都在安全的範圍裡。',
    archivePrompt: '這裡保存的是那些把關係重新接回來的時刻。',
  },
  [CardCategory.MEMORY_LANE]: {
    eyebrow: '回憶收藏',
    spotlight: '把過去的甜與光拿回來，替現在重新點一盞燈。',
    shortHook: '適合在需要暖一下彼此時，回到共同記憶的入口。',
    roomPrompt: '今晚先回到共同記憶，再讓新的話題往前走。',
    archivePrompt: '這裡留下你們把回憶重新翻開的那些片刻。',
  },
  [CardCategory.GROWTH_QUEST]: {
    eyebrow: '共同成長',
    spotlight: '把未來說得更清楚，才能一起長成更穩的關係。',
    shortHook: '適合在想談未來、習慣與成長方向時打開。',
    roomPrompt: '把眼光放到未來，讓今晚的回答慢慢長出方向。',
    archivePrompt: '這裡收著你們曾經一起談過的成長與未來。',
  },
  [CardCategory.AFTER_DARK]: {
    eyebrow: '親密深談',
    spotlight: '把親密感交給更成熟的語氣，而不是更吵的刺激。',
    shortHook: '適合在你們都準備好時，慢慢靠近更私密的對話。',
    roomPrompt: '先確認彼此都在舒服的位置，再往更親密的地方靠近。',
    archivePrompt: '這裡保存你們曾經真誠談過親密與渴望的時刻。',
  },
  [CardCategory.CO_PILOT]: {
    eyebrow: '生活協作',
    spotlight: '把生活裡的配合與決策，整理成更輕盈的默契。',
    shortHook: '適合談分工、習慣與旅行節奏，讓合作感更自然。',
    roomPrompt: '從生活細節開始，看彼此怎麼成為更好的副駕。',
    archivePrompt: '這裡記錄你們在生活協作裡長出的默契。',
  },
  [CardCategory.LOVE_BLUEPRINT]: {
    eyebrow: '愛情藍圖',
    spotlight: '把關係藍圖談清楚，未來就不需要一直靠猜。',
    shortHook: '適合談家庭、理財、未來規劃與長期想像。',
    roomPrompt: '讓今晚的回答替未來留下一張更清楚的草圖。',
    archivePrompt: '這裡留下你們曾經一起描繪未來的對話草圖。',
  },
};

export function getDeckEditorialCopy(category?: string | null): DeckEditorialCopy | null {
  const normalized = normalizeDeckCategory(category);
  if (!normalized) return null;
  return DECK_EDITORIAL_COPY[normalized];
}
