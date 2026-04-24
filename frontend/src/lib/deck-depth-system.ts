import type { DeckMeta } from '@/lib/deck-meta';
import type { DepthLevel } from '@/lib/depth-level';

export type DeckDepthFilter = DepthLevel | null;

export const DECK_DEPTH_QUERY_KEY = 'depth';

export const parseDeckDepthParam = (
  value?: string | null,
): DeckDepthFilter => {
  if (value === '1') return 1;
  if (value === '2') return 2;
  if (value === '3') return 3;
  return null;
};

export const filterDecksByDepth = <T extends { deck: DeckMeta }>(
  decks: readonly T[],
  depth: DeckDepthFilter,
): T[] => {
  if (!depth) return [...decks];
  return decks.filter((item) => item.deck.depthIdentity === depth);
};

export const getDeckDepthFilterCopy = (depth: DeckDepthFilter) => {
  if (depth === 1) {
    return {
      title: '今晚先從比較輕的入口開始。',
      description:
        '只留下適合「輕鬆聊」的牌組。這不是降低深度，而是先讓對話有一個不費力的開場。',
      emptyTitle: '目前沒有符合「輕鬆聊」的牌組。',
      emptyDescription: '換一個深度節奏或清除篩選，就能重新看見完整館藏。',
    };
  }
  if (depth === 2) {
    return {
      title: '今晚想再靠近一點，就從這些牌組開始。',
      description:
        '這裡保留的是適合把近況慢慢聊到需要與感受的題組，讓關係多靠近一層。',
      emptyTitle: '目前沒有符合「靠近一點」的牌組。',
      emptyDescription: '換一個深度節奏或清除篩選，就能重新看見完整館藏。',
    };
  }
  if (depth === 3) {
    return {
      title: '今晚如果準備好深入內心，這些牌組會留出更安靜的空間。',
      description:
        '這個深度適合慢一點、真一點的對話。Haven 會優先把這類題組放到前排。',
      emptyTitle: '目前沒有符合「深入內心」的牌組。',
      emptyDescription: '換一個深度節奏或清除篩選，就能重新看見完整館藏。',
    };
  }
  return null;
};
