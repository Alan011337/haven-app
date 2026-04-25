export type WeeklyReviewPromptKey =
  | 'understood_this_week'
  | 'worth_carrying_forward'
  | 'needs_care'
  | 'next_week_intention';

export type WeeklyReviewPromptModel = {
  key: WeeklyReviewPromptKey;
  title: string;
  helperText: string;
  placeholder: string;
};

export type WeeklyReviewCueModel = {
  key: 'pending-review' | 'evolution' | 'identity' | 'heart' | 'future';
  label: string;
  description: string;
  href: string;
  testId: string;
};

export type RelationshipWeeklyReviewRitualModel = {
  weekLabel: string;
  title: string;
  subtitle: string;
  trustLine: string;
  prompts: WeeklyReviewPromptModel[];
  cues: WeeklyReviewCueModel[];
  emptyNudge: string | null;
};

function safeCount(value: number | null | undefined): number {
  return Number.isFinite(value) && (value as number) > 0 ? Math.floor(value as number) : 0;
}

function formatIsoDate(date: Date): string {
  const yyyy = date.getUTCFullYear();
  const mm = String(date.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(date.getUTCDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function startOfIsoWeekUtc(now: Date): Date {
  // Monday = 1 ... Sunday = 7
  const day = now.getUTCDay() === 0 ? 7 : now.getUTCDay();
  const diff = day - 1;
  const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  start.setUTCDate(start.getUTCDate() - diff);
  return start;
}

export function buildRelationshipWeeklyReviewRitualModel(input: {
  hasPartner: boolean;
  now?: Date;
  pendingReviewCount: number;
  evolutionCount: number;
  compassHistoryCount: number;
  repairHistoryCount: number;
}): RelationshipWeeklyReviewRitualModel | null {
  if (!input.hasPartner) return null;

  const now = input.now ?? new Date();
  const weekStart = startOfIsoWeekUtc(now);
  const weekEnd = new Date(weekStart);
  weekEnd.setUTCDate(weekEnd.getUTCDate() + 6);
  const weekLabel = `${formatIsoDate(weekStart)}–${formatIsoDate(weekEnd)}`;

  const pendingReviewCount = safeCount(input.pendingReviewCount);
  const evolutionCount = safeCount(input.evolutionCount);
  const compassHistoryCount = safeCount(input.compassHistoryCount);
  const repairHistoryCount = safeCount(input.repairHistoryCount);

  const prompts: WeeklyReviewPromptModel[] = [
    {
      key: 'understood_this_week',
      title: '這週我們更理解彼此什麼？',
      helperText: '不需要完整，用一句話也可以。可以是一次新的理解、一次被接住的需要，或一個你想記得的轉折。',
      placeholder: '例如：我更理解你在忙的時候，需要先慢下來再說。',
    },
    {
      key: 'worth_carrying_forward',
      title: '這週有哪些時刻值得保留？',
      helperText: '挑一個你們想帶著走的片刻：一段對話、一個小舉動、或一次靠近。',
      placeholder: '例如：晚餐後散步的那段時間，讓我們又回到同一邊。',
    },
    {
      key: 'needs_care',
      title: '這週有什麼需要照顧或修復？',
      helperText: '這不是檢討。只是把卡住或受傷的地方放在安全的語氣裡，讓它有機會被照顧。',
      placeholder: '例如：週三那次語氣太急，我希望下次先問你需要什麼。',
    },
    {
      key: 'next_week_intention',
      title: '下週我們想一起靠近什麼？',
      helperText: '用一個可實踐的小意圖就好。你們可以之後再決定是否要把它寫進 Compass / Heart / Future。',
      placeholder: '例如：下週固定留一晚散步，先把彼此的需要說完。',
    },
  ];

  const cues: WeeklyReviewCueModel[] = [];
  if (pendingReviewCount > 0) {
    cues.push({
      key: 'pending-review',
      label: `待審核 · ${pendingReviewCount} 則`,
      description: '你們還有 Haven 建議待決定；可以先審核，或把它帶進復盤一起討論。',
      href: '#pending-review',
      testId: 'weekly-review-cue-pending-review',
    });
  }
  if (evolutionCount > 0) {
    cues.push({
      key: 'evolution',
      label: `最近演進 · ${evolutionCount} 次`,
      description: '看看這週哪些內容已被手動更新或由已接受建議帶動。',
      href: '#evolution',
      testId: 'weekly-review-cue-evolution',
    });
  }
  if (repairHistoryCount > 0) {
    cues.push({
      key: 'heart',
      label: 'Heart',
      description: '這週有修復約定的脈絡；可以回看是否有幫助你們靠近。',
      href: '#heart',
      testId: 'weekly-review-cue-heart',
    });
  }
  if (compassHistoryCount > 0) {
    cues.push({
      key: 'identity',
      label: 'Identity',
      description: 'Relationship Compass 有修訂紀錄；如果你們想，也可以回看它如何被調整。',
      href: '#identity',
      testId: 'weekly-review-cue-identity',
    });
  }
  cues.push({
    key: 'future',
    label: 'Future',
    description: '如果你們在復盤裡提到「想一起靠近什麼」，可以之後再把它放進 Shared Future。',
    href: '#future',
    testId: 'weekly-review-cue-future',
  });

  const hasAnyCue = cues.some((cue) => cue.key !== 'future');
  const emptyNudge = hasAnyCue
    ? null
    : '這週還沒有太多片段也沒關係。可以先用 5 分鐘回答一題：這週我們想記得什麼？';

  return {
    weekLabel,
    title: '每週關係復盤',
    subtitle: '用幾分鐘一起回看這週：哪些地方更靠近了，哪些需要照顧，哪些想帶進下週。',
    trustLine: '這不是評分，也不是檢討；只是幫你們把值得記得的理解留下來。Haven 不會自動改寫你們的共同真相。',
    prompts,
    cues,
    emptyNudge,
  };
}

