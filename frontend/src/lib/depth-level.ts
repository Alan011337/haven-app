export type DepthLevel = 1 | 2 | 3;

export type DepthPresentation = {
  level: DepthLevel;
  label: string;
  guidance: string;
  badgeClass: string;
  accentFrameClass: string;
  topAccentClass: string;
  questionSurfaceClass: string;
};

export const resolveDepthLevel = (...candidates: Array<number | null | undefined>): DepthLevel => {
  for (const value of candidates) {
    if (typeof value === 'number' && Number.isFinite(value)) {
      if (value >= 3) return 3;
      if (value >= 2) return 2;
      return 1;
    }
  }
  return 1;
};

export const DEPTH_OPTIONS: readonly { level: DepthLevel; label: string; description: string }[] = [
  { level: 1, label: '輕鬆聊', description: '先用比較不費力的問題，慢慢進到今晚。' },
  { level: 2, label: '靠近一點', description: '聊近況，也聊到彼此真正想被理解的地方。' },
  { level: 3, label: '深入內心', description: '留給今晚願意更坦白、更靠近內在的時刻。' },
];

export const getDepthPresentation = (level: DepthLevel): DepthPresentation => {
  if (level === 3) {
    return {
      level,
      label: '深入內心',
      guidance: '慢一點、真一點，留給今晚願意更坦白、更靠近內在的時刻。',
      badgeClass: 'bg-depth-3/15 text-depth-3 border border-depth-3/30',
      accentFrameClass: 'border-depth-3/30 ring-2 ring-depth-3/10 shadow-soft',
      topAccentClass: 'bg-depth-3',
      questionSurfaceClass: 'bg-depth-3/10 border-border',
    };
  }
  if (level === 2) {
    return {
      level,
      label: '靠近一點',
      guidance: '聊近況背後的感受，也聊到彼此真正想被理解的地方。',
      badgeClass: 'bg-depth-2/15 text-depth-2 border border-depth-2/30',
      accentFrameClass: 'border-depth-2/30 ring-1 ring-depth-2/10 shadow-soft',
      topAccentClass: 'bg-depth-2',
      questionSurfaceClass: 'bg-depth-2/10 border-border',
    };
  }
  return {
    level,
    label: '輕鬆聊',
    guidance: '用比較不費力的問題開場，先建立安全感，再慢慢進到今晚。',
    badgeClass: 'bg-depth-1/15 text-depth-1 border border-depth-1/30',
    accentFrameClass: 'border-depth-1/30 shadow-soft',
    topAccentClass: 'bg-depth-1',
    questionSurfaceClass: 'bg-depth-1/10 border-border',
  };
};
