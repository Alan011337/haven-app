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

export const getDepthPresentation = (level: DepthLevel): DepthPresentation => {
  if (level === 3) {
    return {
      level,
      label: '靈魂深潛',
      guidance: '慢一點、真一點，試著說出你真正害怕或在意的事。',
      badgeClass: 'bg-depth-3/15 text-depth-3 border border-depth-3/30',
      accentFrameClass: 'border-depth-3/30 ring-2 ring-depth-3/10 shadow-soft',
      topAccentClass: 'bg-depth-3',
      questionSurfaceClass: 'bg-depth-3/10 border-border',
    };
  }
  if (level === 2) {
    return {
      level,
      label: '深入交流',
      guidance: '聊近況背後的感受，從事件走到彼此真正的需求。',
      badgeClass: 'bg-depth-2/15 text-depth-2 border border-depth-2/30',
      accentFrameClass: 'border-depth-2/30 ring-1 ring-depth-2/10 shadow-soft',
      topAccentClass: 'bg-depth-2',
      questionSurfaceClass: 'bg-depth-2/10 border-border',
    };
  }
  return {
    level,
    label: '暖身話題',
    guidance: '用輕鬆的方式開場，先建立安全感，再慢慢往深處走。',
    badgeClass: 'bg-depth-1/15 text-depth-1 border border-depth-1/30',
    accentFrameClass: 'border-depth-1/30 shadow-soft',
    topAccentClass: 'bg-depth-1',
    questionSurfaceClass: 'bg-depth-1/10 border-border',
  };
};
