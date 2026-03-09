import type { LucideIcon } from 'lucide-react';
import { Brain, Coffee, Flame, Hourglass, House, Plane, Shield, Sprout } from 'lucide-react';

import { formatDeckCategoryFallback, normalizeDeckCategory } from '@/lib/deck-category';
import { CardCategory } from '@/types';

export type DeckMeta = {
  id: CardCategory;
  title: string;
  description: string;
  color: string;
  textColor: string;
  iconColor: string;
  badgeClass: string;
  Icon: LucideIcon;
};

export const DECK_META_MAP: Record<CardCategory, DeckMeta> = {
  [CardCategory.DAILY_VIBE]: {
    id: CardCategory.DAILY_VIBE,
    title: '日常共感',
    description: '輕鬆聊聊生活瑣事，增進默契',
    color: 'from-orange-100 to-orange-200',
    textColor: 'text-orange-800',
    iconColor: 'text-orange-500',
    badgeClass: 'bg-orange-50 text-orange-700',
    Icon: Coffee,
  },
  [CardCategory.SOUL_DIVE]: {
    id: CardCategory.SOUL_DIVE,
    title: '靈魂深潛',
    description: '探索價值觀與內心深處的想法',
    color: 'from-purple-100 to-purple-200',
    textColor: 'text-purple-800',
    iconColor: 'text-purple-500',
    badgeClass: 'bg-purple-50 text-purple-700',
    Icon: Brain,
  },
  [CardCategory.SAFE_ZONE]: {
    id: CardCategory.SAFE_ZONE,
    title: '安全屋',
    description: '修復衝突，在安全感中對話',
    color: 'from-green-100 to-green-200',
    textColor: 'text-green-800',
    iconColor: 'text-green-500',
    badgeClass: 'bg-green-50 text-green-700',
    Icon: Shield,
  },
  [CardCategory.MEMORY_LANE]: {
    id: CardCategory.MEMORY_LANE,
    title: '時光機',
    description: '重溫甜蜜回憶與初衷',
    color: 'from-yellow-100 to-yellow-200',
    textColor: 'text-yellow-800',
    iconColor: 'text-yellow-500',
    badgeClass: 'bg-yellow-50 text-yellow-700',
    Icon: Hourglass,
  },
  [CardCategory.GROWTH_QUEST]: {
    id: CardCategory.GROWTH_QUEST,
    title: '共同成長',
    description: '規劃未來，一起變成更好的人',
    color: 'from-blue-100 to-blue-200',
    textColor: 'text-blue-800',
    iconColor: 'text-blue-500',
    badgeClass: 'bg-blue-50 text-blue-700',
    Icon: Sprout,
  },
  [CardCategory.AFTER_DARK]: {
    id: CardCategory.AFTER_DARK,
    title: '深夜話題',
    description: '親密關係與私密對話 (羞)',
    color: 'from-rose-100 to-rose-200',
    textColor: 'text-rose-800',
    iconColor: 'text-rose-500',
    badgeClass: 'bg-rose-50 text-rose-700',
    Icon: Flame,
  },
  [CardCategory.CO_PILOT]: {
    id: CardCategory.CO_PILOT,
    title: '最佳副駕',
    description: '生活分工、旅行習慣與決策風格',
    color: 'from-cyan-100 to-cyan-200',
    textColor: 'text-cyan-800',
    iconColor: 'text-cyan-500',
    badgeClass: 'bg-cyan-50 text-cyan-700',
    Icon: Plane,
  },
  [CardCategory.LOVE_BLUEPRINT]: {
    id: CardCategory.LOVE_BLUEPRINT,
    title: '愛情藍圖',
    description: '未來規劃、理財觀與家庭期待',
    color: 'from-slate-100 to-slate-200',
    textColor: 'text-slate-800',
    iconColor: 'text-slate-500',
    badgeClass: 'bg-slate-100 text-slate-700',
    Icon: House,
  },
};

export const DECK_META_LIST: DeckMeta[] = [
  DECK_META_MAP[CardCategory.DAILY_VIBE],
  DECK_META_MAP[CardCategory.SOUL_DIVE],
  DECK_META_MAP[CardCategory.SAFE_ZONE],
  DECK_META_MAP[CardCategory.MEMORY_LANE],
  DECK_META_MAP[CardCategory.GROWTH_QUEST],
  DECK_META_MAP[CardCategory.AFTER_DARK],
  DECK_META_MAP[CardCategory.CO_PILOT],
  DECK_META_MAP[CardCategory.LOVE_BLUEPRINT],
];

export const getDeckMeta = (category?: string | null): DeckMeta | null => {
  const normalizedCategory = normalizeDeckCategory(category);
  if (!normalizedCategory) {
    return null;
  }
  return DECK_META_MAP[normalizedCategory];
};

export const getDeckDisplayName = (category?: string | null): string => {
  return getDeckMeta(category)?.title ?? formatDeckCategoryFallback(category);
};
