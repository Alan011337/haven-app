import type { LucideIcon } from 'lucide-react';
import { Brain, Coffee, Flame, Hourglass, House, Plane, Shield, Sprout } from 'lucide-react';

import { formatDeckCategoryFallback, normalizeDeckCategory } from '@/lib/deck-category';
import type { DepthLevel } from '@/lib/depth-level';
import { CardCategory } from '@/types';

/** Card-back gradient and optional pattern. Uses semantic tokens only (ART-DIRECTION). */
export type DeckCardBackStyle = {
  gradient: string;
  borderClass: string;
  glowClass: string;
  patternKey?: 'pattern-card-dots' | 'pattern-card-lines' | 'pattern-card-grid';
  watermarkIconKey?: 'default' | 'none';
};

export type DeckMeta = {
  id: CardCategory;
  title: string;
  description: string;
  color: string;
  textColor: string;
  iconColor: string;
  badgeClass: string;
  Icon: LucideIcon;
  /** Card back (face-down) gradient and accent for flip/reveal. */
  cardBack: DeckCardBackStyle;
  /** Primary conversation depth: 1=暖身, 2=深入, 3=靈魂深潛. */
  depthIdentity: DepthLevel;
  /** P2-A DoD: primary/secondary for design sync (RN, tokens). */
  primaryColor?: string;
  secondaryColor?: string;
};

/** Deck visuals: semantic tokens only (chart-1..5, depth-1..3, muted). primaryColor/secondaryColor kept for RN/external sync. */
export const DECK_META_MAP: Record<CardCategory, DeckMeta> = {
  [CardCategory.DAILY_VIBE]: {
    id: CardCategory.DAILY_VIBE,
    title: '日常共感',
    description: '輕鬆聊聊生活瑣事，增進默契',
    color: 'from-chart-4/45 to-chart-4/25',
    textColor: 'text-foreground',
    iconColor: 'text-chart-4',
    badgeClass: 'bg-chart-4/15 text-foreground',
    Icon: Coffee,
    depthIdentity: 1,
    cardBack: { gradient: 'bg-chart-4', borderClass: 'border-white/30', glowClass: 'shadow-soft', patternKey: 'pattern-card-dots' },
    primaryColor: '#f97316',
    secondaryColor: '#fbbf24',
  },
  [CardCategory.SOUL_DIVE]: {
    id: CardCategory.SOUL_DIVE,
    title: '靈魂深潛',
    description: '探索價值觀與內心深處的想法',
    color: 'from-chart-1/45 to-chart-1/25',
    textColor: 'text-foreground',
    iconColor: 'text-chart-1',
    badgeClass: 'bg-chart-1/15 text-foreground',
    Icon: Brain,
    depthIdentity: 3,
    cardBack: { gradient: 'bg-chart-1', borderClass: 'border-white/30', glowClass: 'shadow-soft', patternKey: 'pattern-card-lines' },
    primaryColor: '#8b5cf6',
    secondaryColor: '#ec4899',
  },
  [CardCategory.SAFE_ZONE]: {
    id: CardCategory.SAFE_ZONE,
    title: '安全屋',
    description: '修復衝突，在安全感中對話',
    color: 'from-chart-2/45 to-chart-2/25',
    textColor: 'text-foreground',
    iconColor: 'text-chart-2',
    badgeClass: 'bg-chart-2/15 text-foreground',
    Icon: Shield,
    depthIdentity: 2,
    cardBack: { gradient: 'bg-chart-2', borderClass: 'border-white/30', glowClass: 'shadow-soft', patternKey: 'pattern-card-grid' },
    primaryColor: '#10b981',
    secondaryColor: '#14b8a6',
  },
  [CardCategory.MEMORY_LANE]: {
    id: CardCategory.MEMORY_LANE,
    title: '時光機',
    description: '重溫甜蜜回憶與初衷',
    color: 'from-chart-5/45 to-chart-5/25',
    textColor: 'text-foreground',
    iconColor: 'text-chart-5',
    badgeClass: 'bg-chart-5/15 text-foreground',
    Icon: Hourglass,
    depthIdentity: 1,
    cardBack: { gradient: 'bg-chart-5', borderClass: 'border-white/30', glowClass: 'shadow-soft', patternKey: 'pattern-card-dots' },
    primaryColor: '#eab308',
    secondaryColor: '#f59e0b',
  },
  [CardCategory.GROWTH_QUEST]: {
    id: CardCategory.GROWTH_QUEST,
    title: '共同成長',
    description: '規劃未來，一起變成更好的人',
    color: 'from-chart-3/45 to-chart-3/25',
    textColor: 'text-foreground',
    iconColor: 'text-chart-3',
    badgeClass: 'bg-chart-3/15 text-foreground',
    Icon: Sprout,
    depthIdentity: 2,
    cardBack: { gradient: 'bg-chart-3', borderClass: 'border-white/30', glowClass: 'shadow-soft', patternKey: 'pattern-card-lines' },
    primaryColor: '#3b82f6',
    secondaryColor: '#06b6d4',
  },
  [CardCategory.AFTER_DARK]: {
    id: CardCategory.AFTER_DARK,
    title: '深夜話題',
    description: '親密關係與私密對話 (羞)',
    color: 'from-depth-3/45 to-depth-3/25',
    textColor: 'text-foreground',
    iconColor: 'text-depth-3',
    badgeClass: 'bg-depth-3/15 text-foreground',
    Icon: Flame,
    depthIdentity: 3,
    cardBack: { gradient: 'bg-depth-3', borderClass: 'border-white/30', glowClass: 'shadow-soft', patternKey: 'pattern-card-grid' },
    primaryColor: '#f43f5e',
    secondaryColor: '#d946ef',
  },
  [CardCategory.CO_PILOT]: {
    id: CardCategory.CO_PILOT,
    title: '最佳副駕',
    description: '生活分工、旅行習慣與決策風格',
    color: 'from-chart-3/40 to-chart-3/20',
    textColor: 'text-foreground',
    iconColor: 'text-chart-3',
    badgeClass: 'bg-chart-3/15 text-foreground',
    Icon: Plane,
    depthIdentity: 1,
    cardBack: { gradient: 'bg-chart-3', borderClass: 'border-white/30', glowClass: 'shadow-soft', patternKey: 'pattern-card-dots' },
    primaryColor: '#06b6d4',
    secondaryColor: '#3b82f6',
  },
  [CardCategory.LOVE_BLUEPRINT]: {
    id: CardCategory.LOVE_BLUEPRINT,
    title: '愛情藍圖',
    description: '未來規劃、理財觀與家庭期待',
    color: 'from-depth-1/40 to-depth-1/20',
    textColor: 'text-foreground',
    iconColor: 'text-depth-1',
    badgeClass: 'bg-depth-1/15 text-foreground',
    Icon: House,
    depthIdentity: 2,
    cardBack: { gradient: 'bg-depth-1', borderClass: 'border-white/30', glowClass: 'shadow-soft', patternKey: 'pattern-card-lines' },
    primaryColor: '#64748b',
    secondaryColor: '#475569',
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
