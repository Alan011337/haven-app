export type AnalysisBriefTone = 'default' | 'strength' | 'attention' | 'quiet';

export type AnalysisBriefAction = {
  label: string;
  href?: string;
  evidenceId?: string;
};

export type AnalysisBriefCard = {
  key: 'current' | 'strength' | 'attention' | 'direction';
  tone: AnalysisBriefTone;
  question: string;
  title: string;
  description: string;
  sources: string[];
  action: AnalysisBriefAction;
};

export type AnalysisUnderstandingBriefModel = {
  title: string;
  description: string;
  sourceNote: string;
  cards: AnalysisBriefCard[];
};

export type AnalysisUnderstandingBriefInput = {
  hasPartner: boolean;
  pulseScore: number | null;
  syncCompletionPct: number;
  alignmentPct: number;
  journalCount14: number;
  myJournalCount14: number;
  partnerJournalCount14: number;
  highTensionCount14: number;
  appreciationCount: number;
  topTopics: string[];
  currentRead: string | null;
  patternTitle: string | null;
  monthlyTrendSummary: string | null;
  healthSuggestion: string | null;
  todaySyncState: string | null;
  relationshipCompass: {
    identity_statement?: string | null;
    story_anchor?: string | null;
    future_direction?: string | null;
  } | null;
  repairAgreements: {
    protect_what_matters?: string | null;
    avoid_in_conflict?: string | null;
    repair_reentry?: string | null;
  } | null;
  hasHeartCare: boolean;
  weeklyTask: {
    task_label?: string | null;
    completed?: boolean | null;
  } | null;
  storyMomentCount: number;
  wishlistCount: number;
  loveMapAvailable: boolean;
};

function cleanText(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

function clampPct(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

function compactSources(values: Array<string | null | undefined>): string[] {
  const out: string[] = [];
  for (const value of values) {
    if (!value || out.includes(value)) continue;
    out.push(value);
  }
  return out;
}

function countFilled(values: Array<string | null | undefined>): number {
  return values.filter((value) => Boolean(cleanText(value))).length;
}

function truncate(value: string, max = 116): string {
  if (value.length <= max) return value;
  return `${value.slice(0, max - 1)}…`;
}

function currentCard(input: AnalysisUnderstandingBriefInput): AnalysisBriefCard {
  const syncPct = clampPct(input.syncCompletionPct);
  const baseRead =
    cleanText(input.monthlyTrendSummary) ??
    cleanText(input.currentRead) ??
    cleanText(input.patternTitle);

  if (!input.hasPartner) {
    return {
      key: 'current',
      tone: 'quiet',
      question: '我們最近怎麼樣',
      title: '先把自己的節奏讀清楚',
      description:
        baseRead ??
        '伴侶加入前，Analysis 先用你的日記與同步，整理你最近更常從什麼狀態進入關係。',
      sources: compactSources(['Journal', syncPct > 0 ? 'Daily Sync' : null]),
      action: { label: '回到今天同步', href: '/' },
    };
  }

  const title =
    typeof input.pulseScore === 'number'
      ? input.pulseScore >= 80
        ? '最近是穩定靠近的節奏'
        : input.pulseScore >= 60
          ? '整體仍然穩，但需要刻意維持'
          : input.pulseScore >= 40
            ? '最近比較容易錯開彼此的節奏'
            : '先修復安全感，再追求深入'
      : syncPct > 0
        ? '關係讀數還在聚焦，週節奏先回來了'
        : '關係讀數還在等待更多真實痕跡';

  return {
    key: 'current',
    tone: syncPct > 0 && syncPct < 55 ? 'attention' : 'default',
    question: '我們最近怎麼樣',
    title,
    description:
      baseRead ??
      `近兩週共有 ${input.journalCount14} 則可讀痕跡，本週同步 ${syncPct}%。這裡先把節奏讀清楚，不把它膨脹成診斷。`,
    sources: compactSources([
      'Relationship Read',
      syncPct > 0 ? 'Daily Sync' : null,
      input.journalCount14 > 0 ? 'Journal' : null,
      input.monthlyTrendSummary ? 'Memory' : null,
    ]),
    action: {
      label: input.topTopics.length ? '展開雙方模式依據' : '查看節奏依據',
      evidenceId: input.topTopics.length ? 'patterns' : 'sync',
    },
  };
}

function strengthCard(input: AnalysisUnderstandingBriefInput): AnalysisBriefCard {
  const storyAnchor = cleanText(input.relationshipCompass?.story_anchor);

  if (input.appreciationCount > 0) {
    return {
      key: 'strength',
      tone: 'strength',
      question: '什麼正在撐住我們',
      title: '感謝有被說出來，而不是只停在心裡',
      description:
        storyAnchor ??
        `這週有 ${input.appreciationCount} 則被說出口的感謝。Analysis 會把這些當成連結證據，不只是漂亮數字。`,
      sources: compactSources([
        'Appreciation',
        storyAnchor ? 'Relationship Compass' : null,
        input.storyMomentCount > 0 ? 'Story' : null,
      ]),
      action: { label: '查看感謝依據', evidenceId: 'appreciation' },
    };
  }

  if (input.hasPartner && input.myJournalCount14 > 0 && input.partnerJournalCount14 > 0) {
    return {
      key: 'strength',
      tone: 'strength',
      question: '什麼正在撐住我們',
      title: '雙方都還願意留下自己的版本',
      description:
        storyAnchor ??
        `近兩週你 ${input.myJournalCount14} 則、伴侶 ${input.partnerJournalCount14} 則。這代表理解還有雙向入口。`,
      sources: compactSources(['Journal', storyAnchor ? 'Relationship Compass' : null]),
      action: { label: '展開雙方痕跡依據', evidenceId: 'mutual' },
    };
  }

  if (storyAnchor) {
    return {
      key: 'strength',
      tone: 'strength',
      question: '什麼正在撐住我們',
      title: '你們已經留下想一起帶著走的故事',
      description: storyAnchor,
      sources: compactSources(['Relationship Compass', input.storyMomentCount > 0 ? 'Story' : null]),
      action: { label: '回到 Relationship Compass', href: '/love-map#identity' },
    };
  }

  return {
    key: 'strength',
    tone: 'quiet',
    question: '什麼正在撐住我們',
    title: '眼前的好事還比較細小，但已經在累積',
    description:
      '目前還沒有很強的正向訊號。先把感謝、雙向書寫或共同故事留下來，這裡會變得更有根據。',
    sources: compactSources([input.journalCount14 > 0 ? 'Journal' : null, input.loveMapAvailable ? 'Relationship System' : null]),
    action: { label: '回到回憶長廊', href: '/memory' },
  };
}

function attentionCard(input: AnalysisUnderstandingBriefInput): AnalysisBriefCard {
  const repairCount = countFilled([
    input.repairAgreements?.protect_what_matters,
    input.repairAgreements?.avoid_in_conflict,
    input.repairAgreements?.repair_reentry,
  ]);
  const repairCue = repairCount
    ? `你們已經留下 ${repairCount}/3 個 Repair Agreements，可以把對話帶回安全感。`
    : null;

  if (input.highTensionCount14 > 0) {
    return {
      key: 'attention',
      tone: 'attention',
      question: '哪裡需要先照顧',
      title: '最近的情緒張力偏高，先顧安全感再談內容',
      description:
        repairCue ??
        `近兩週有 ${input.highTensionCount14} 則高張力痕跡。這裡先指出需要放慢的地方，不判斷誰對。`,
      sources: compactSources(['Journal', repairCue ? 'Repair Agreements' : null]),
      action: { label: '查看修復依據', evidenceId: 'tension' },
    };
  }

  if (input.syncCompletionPct > 0 && input.syncCompletionPct < 55) {
    return {
      key: 'attention',
      tone: 'attention',
      question: '哪裡需要先照顧',
      title: '日常同步的節奏有點稀薄',
      description:
        repairCue ??
        `本週同步 ${clampPct(input.syncCompletionPct)}%。先恢復小而穩定的接觸，比一次談很深更有用。`,
      sources: compactSources(['Daily Sync', repairCue ? 'Repair Agreements' : null]),
      action: { label: '查看節奏依據', evidenceId: 'sync' },
    };
  }

  return {
    key: 'attention',
    tone: 'quiet',
    question: '哪裡需要先照顧',
    title: repairCue ? '需要照顧時，已經有修復約定可以回來看' : '目前沒有明顯警訊，先維持可回來的節奏',
    description:
      repairCue ??
      cleanText(input.healthSuggestion) ??
      'Analysis 會保留溫和判讀：沒有足夠依據時，不製造問題；有訊號時，再把需要照顧的地方放到前面。',
    sources: compactSources([
      repairCue ? 'Repair Agreements' : null,
      input.healthSuggestion ? 'Memory' : null,
      input.loveMapAvailable ? 'Relationship System' : null,
    ]),
    action: { label: repairCue ? '回到 Heart' : '回看最近痕跡', href: repairCue ? '/love-map#heart' : '/memory' },
  };
}

function directionCard(input: AnalysisUnderstandingBriefInput): AnalysisBriefCard {
  const futureDirection = cleanText(input.relationshipCompass?.future_direction);

  if (futureDirection) {
    return {
      key: 'direction',
      tone: 'default',
      question: '下一步往哪裡靠近',
      title: '先靠近你們自己寫下的未來方向',
      description: truncate(futureDirection, 130),
      sources: compactSources([
        'Relationship Compass',
        input.wishlistCount > 0 ? 'Shared Future' : null,
      ]),
      action: { label: '回到 Relationship Compass', href: '/love-map#identity' },
    };
  }

  if (input.weeklyTask?.task_label && !input.weeklyTask.completed) {
    return {
      key: 'direction',
      tone: 'default',
      question: '下一步往哪裡靠近',
      title: '先完成這週的照顧任務',
      description: input.weeklyTask.task_label,
      sources: compactSources(['Heart Care', input.hasHeartCare ? 'Care Playbook' : null]),
      action: { label: '回到 Heart', href: '/love-map#heart' },
    };
  }

  if (cleanText(input.todaySyncState)) {
    return {
      key: 'direction',
      tone: 'default',
      question: '下一步往哪裡靠近',
      title: '今天先用最小的一格重新對齊',
      description: input.todaySyncState ?? '',
      sources: compactSources(['Daily Sync']),
      action: { label: '回到今天同步', href: '/' },
    };
  }

  return {
    key: 'direction',
    tone: 'quiet',
    question: '下一步往哪裡靠近',
    title: '先留下共同方向，Analysis 才能指向更穩的下一步',
    description:
      '目前還沒有明確的共享方向。先在 Relationship System 裡寫下 Compass 或 Future 片段，這裡會更像 insight center。',
    sources: compactSources([input.loveMapAvailable ? 'Relationship System' : null]),
    action: { label: '前往 Relationship System', href: '/love-map#identity' },
  };
}

export function buildAnalysisV2UnderstandingBrief(
  input: AnalysisUnderstandingBriefInput,
): AnalysisUnderstandingBriefModel {
  const cards = [
    currentCard(input),
    strengthCard(input),
    attentionCard(input),
    directionCard(input),
  ];

  const sourceCount = new Set(cards.flatMap((card) => card.sources)).size;

  return {
    title: '這週的關係讀法',
    description:
      'Analysis V2 先回答四個問題：最近怎麼樣、什麼正在撐住你們、哪裡需要先照顧、下一步往哪裡靠近。',
    sourceNote: input.loveMapAvailable
      ? `目前從 ${sourceCount} 種真實來源整理，不用 AI 補寫關係意義。`
      : `目前從 ${sourceCount} 種已回來的來源整理；Relationship System 暫時沒有回來，所以這份讀法會保守一點。`,
    cards,
  };
}
