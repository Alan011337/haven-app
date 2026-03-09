import { CardCategory } from '@/types';

const DECK_CATEGORY_SET = new Set<string>(Object.values(CardCategory));

export const normalizeDeckCategory = (category?: string | null): CardCategory | null => {
  const normalized = category?.trim().toUpperCase();
  if (!normalized || !DECK_CATEGORY_SET.has(normalized)) {
    return null;
  }
  return normalized as CardCategory;
};

export const formatDeckCategoryFallback = (category?: string | null): string => {
  const normalized = category?.trim();
  if (!normalized) {
    return '未分類牌組';
  }
  return normalized.replace(/_/g, ' ');
};
