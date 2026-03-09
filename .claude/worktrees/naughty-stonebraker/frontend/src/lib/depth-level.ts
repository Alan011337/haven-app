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
      badgeClass: 'bg-violet-100 text-violet-700 border border-violet-200',
      accentFrameClass:
        'border-violet-300 ring-2 ring-violet-100 shadow-[0_18px_40px_-28px_rgba(109,40,217,0.55)]',
      topAccentClass: 'bg-gradient-to-r from-fuchsia-400 via-violet-500 to-indigo-500',
      questionSurfaceClass:
        'bg-gradient-to-br from-violet-50/70 via-white to-fuchsia-50/55 border-violet-200',
    };
  }
  if (level === 2) {
    return {
      level,
      label: '深入交流',
      guidance: '聊近況背後的感受，從事件走到彼此真正的需求。',
      badgeClass: 'bg-amber-100 text-amber-700 border border-amber-200',
      accentFrameClass:
        'border-amber-300 ring-1 ring-amber-100 shadow-[0_18px_40px_-30px_rgba(217,119,6,0.5)]',
      topAccentClass: 'bg-gradient-to-r from-amber-300 via-orange-400 to-rose-400',
      questionSurfaceClass:
        'bg-gradient-to-br from-amber-50/70 via-white to-orange-50/55 border-amber-200',
    };
  }
  return {
    level,
    label: '暖身話題',
    guidance: '用輕鬆的方式開場，先建立安全感，再慢慢往深處走。',
    badgeClass: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    accentFrameClass:
      'border-emerald-200 shadow-[0_18px_40px_-32px_rgba(5,150,105,0.5)]',
    topAccentClass: 'bg-gradient-to-r from-emerald-300 via-teal-400 to-cyan-400',
    questionSurfaceClass:
      'bg-gradient-to-br from-emerald-50/70 via-white to-cyan-50/55 border-emerald-200',
  };
};
