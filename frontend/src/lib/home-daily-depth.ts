import type { DepthLevel } from '@/lib/depth-level';

export type HomeDailyDepthPresentation = {
  level: DepthLevel;
  label: string;
  description: string;
  ctaLabel: string;
};

export const HOME_DAILY_DEPTH_OPTIONS: readonly HomeDailyDepthPresentation[] = [
  {
    level: 1,
    label: '輕鬆聊',
    description: '先用比較不費力的問題，慢慢進到今晚。',
    ctaLabel: '抽一張適合「輕鬆聊」的題目',
  },
  {
    level: 2,
    label: '靠近一點',
    description: '聊近況，也聊到彼此真正想被理解的地方。',
    ctaLabel: '抽一張適合「靠近一點」的題目',
  },
  {
    level: 3,
    label: '深入內心',
    description: '留給今晚願意更坦白、更靠近內在的時刻。',
    ctaLabel: '抽一張適合「深入內心」的題目',
  },
] as const;

export const getHomeDailyDepthPresentation = (
  level: DepthLevel | null | undefined,
): HomeDailyDepthPresentation | null =>
  HOME_DAILY_DEPTH_OPTIONS.find((option) => option.level === level) ?? null;
