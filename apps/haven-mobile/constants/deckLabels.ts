import { CardCategory } from 'haven-shared';

export const DECK_CATEGORY_LABELS: Record<CardCategory, string> = {
  [CardCategory.DAILY_VIBE]: '日常共感',
  [CardCategory.SOUL_DIVE]: '靈魂深潛',
  [CardCategory.SAFE_ZONE]: '安全屋',
  [CardCategory.MEMORY_LANE]: '時光機',
  [CardCategory.GROWTH_QUEST]: '共同成長',
  [CardCategory.AFTER_DARK]: '深夜話題',
  [CardCategory.CO_PILOT]: '最佳副駕',
  [CardCategory.LOVE_BLUEPRINT]: '愛情藍圖',
};

export const DECK_CATEGORIES = Object.values(CardCategory);
