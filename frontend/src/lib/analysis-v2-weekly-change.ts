const DAY_MS = 24 * 60 * 60 * 1000;

export type AnalysisWeeklyChangeTone = 'default' | 'strength' | 'attention' | 'quiet';

export type AnalysisWeeklyChangeAction = {
  label: string;
  href?: string;
  evidenceId?: string;
};

export type AnalysisWeeklyChangeCard = {
  key: 'closer' | 'fragile' | 'steady' | 'focus';
  tone: AnalysisWeeklyChangeTone;
  question: string;
  title: string;
  description: string;
  movementLabel: string;
  sources: string[];
  action: AnalysisWeeklyChangeAction;
};

export type AnalysisWeeklyChangeBriefModel = {
  title: string;
  description: string;
  sourceNote: string;
  cards: AnalysisWeeklyChangeCard[];
};

export type AnalysisWeeklyChangeJournalSignal = {
  created_at: string | null | undefined;
  owner: 'me' | 'partner' | 'unknown';
  isHighTension: boolean;
};

export type AnalysisWeeklyChangeDatedSignal = {
  created_at?: string | null;
  changed_at?: string | null;
};

export type AnalysisWeeklyChangeBriefInput = {
  nowMs: number;
  hasPartner: boolean;
  journals: AnalysisWeeklyChangeJournalSignal[];
  appreciations: AnalysisWeeklyChangeDatedSignal[];
  relationshipCompassChanges: AnalysisWeeklyChangeDatedSignal[];
  repairAgreementChanges: AnalysisWeeklyChangeDatedSignal[];
  syncCompletionPct: number;
  alignmentPct: number;
  repairAgreementFieldCount: number;
  hasHeartCare: boolean;
  topTopics: string[];
  loveMapAvailable: boolean;
};

type WindowKey = 'current' | 'prior';

type WindowStats = {
  journalCount: number;
  myJournalCount: number;
  partnerJournalCount: number;
  highTensionCount: number;
  appreciationCount: number;
  compassChangeCount: number;
  repairChangeCount: number;
};

type ComparisonStats = {
  current: WindowStats;
  prior: WindowStats;
  comparableCurrent: number;
  comparablePrior: number;
  priorSparse: boolean;
};

function emptyStats(): WindowStats {
  return {
    journalCount: 0,
    myJournalCount: 0,
    partnerJournalCount: 0,
    highTensionCount: 0,
    appreciationCount: 0,
    compassChangeCount: 0,
    repairChangeCount: 0,
  };
}

function timestampOf(signal: AnalysisWeeklyChangeDatedSignal): string | null | undefined {
  return signal.created_at ?? signal.changed_at;
}

function getWindowKey(value: string | null | undefined, nowMs: number): WindowKey | null {
  if (!Number.isFinite(nowMs)) return null;
  if (!value) return null;

  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp) || timestamp > nowMs) return null;

  const currentStart = nowMs - 7 * DAY_MS;
  const priorStart = nowMs - 14 * DAY_MS;

  if (timestamp >= currentStart) return 'current';
  if (timestamp >= priorStart && timestamp < currentStart) return 'prior';
  return null;
}

function compactSources(values: Array<string | null | undefined>): string[] {
  const out: string[] = [];
  for (const value of values) {
    if (!value || out.includes(value)) continue;
    out.push(value);
  }
  return out;
}

function clampCount(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.round(value));
}

function clampPct(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

function deltaLabel(current: number, prior: number) {
  const delta = current - prior;
  if (delta > 0) return `近 7 天 +${delta}`;
  if (delta < 0) return `近 7 天 ${delta}`;
  return '和前 7 天持平';
}

function buildStats(input: AnalysisWeeklyChangeBriefInput): ComparisonStats {
  const current = emptyStats();
  const prior = emptyStats();

  for (const journal of input.journals) {
    const windowKey = getWindowKey(journal.created_at, input.nowMs);
    if (!windowKey) continue;
    const stats = windowKey === 'current' ? current : prior;
    stats.journalCount += 1;
    if (journal.owner === 'me') stats.myJournalCount += 1;
    if (journal.owner === 'partner') stats.partnerJournalCount += 1;
    if (journal.isHighTension) stats.highTensionCount += 1;
  }

  for (const appreciation of input.appreciations) {
    const windowKey = getWindowKey(timestampOf(appreciation), input.nowMs);
    if (!windowKey) continue;
    const stats = windowKey === 'current' ? current : prior;
    stats.appreciationCount += 1;
  }

  for (const change of input.relationshipCompassChanges) {
    const windowKey = getWindowKey(timestampOf(change), input.nowMs);
    if (!windowKey) continue;
    const stats = windowKey === 'current' ? current : prior;
    stats.compassChangeCount += 1;
  }

  for (const change of input.repairAgreementChanges) {
    const windowKey = getWindowKey(timestampOf(change), input.nowMs);
    if (!windowKey) continue;
    const stats = windowKey === 'current' ? current : prior;
    stats.repairChangeCount += 1;
  }

  const comparableCurrent =
    current.journalCount +
    current.appreciationCount +
    current.compassChangeCount +
    current.repairChangeCount;
  const comparablePrior =
    prior.journalCount +
    prior.appreciationCount +
    prior.compassChangeCount +
    prior.repairChangeCount;

  return {
    current,
    prior,
    comparableCurrent,
    comparablePrior,
    priorSparse: comparablePrior < 2,
  };
}

function closerCard(
  input: AnalysisWeeklyChangeBriefInput,
  stats: ComparisonStats,
): AnalysisWeeklyChangeCard {
  const { current, prior } = stats;

  if (current.appreciationCount > prior.appreciationCount) {
    return {
      key: 'closer',
      tone: 'strength',
      question: '更靠近了什麼',
      title: '感謝比前一週更常被說出口',
      description:
        '這不是把關係變成計分，而是看見好事有沒有被具體留下。被說出的感謝越多，安全感越不需要靠猜。',
      movementLabel: deltaLabel(current.appreciationCount, prior.appreciationCount),
      sources: compactSources(['Appreciation']),
      action: { label: '查看感謝依據', evidenceId: 'appreciation' },
    };
  }

  if (
    input.hasPartner &&
    current.myJournalCount > 0 &&
    current.partnerJournalCount > 0 &&
    (prior.myJournalCount === 0 || prior.partnerJournalCount === 0)
  ) {
    return {
      key: 'closer',
      tone: 'strength',
      question: '更靠近了什麼',
      title: '雙方這週都有留下自己的版本',
      description:
        '相較前一段時間，這週更像是兩邊都願意把自己的狀態留在桌面上。理解有了雙向入口。',
      movementLabel: `你 ${current.myJournalCount} / 伴侶 ${current.partnerJournalCount}`,
      sources: compactSources(['Journal']),
      action: { label: '展開雙方痕跡依據', evidenceId: 'mutual' },
    };
  }

  if (current.compassChangeCount > prior.compassChangeCount) {
    return {
      key: 'closer',
      tone: 'strength',
      question: '更靠近了什麼',
      title: '共同方向最近有被重新校準',
      description:
        'Relationship Compass 有新的手動修訂。這代表你們不只在處理問題，也在重新整理「我們正在往哪裡去」。',
      movementLabel: deltaLabel(current.compassChangeCount, prior.compassChangeCount),
      sources: compactSources(['Relationship Compass']),
      action: { label: '回到 Relationship Compass', href: '/love-map#identity' },
    };
  }

  if (current.repairChangeCount > prior.repairChangeCount) {
    return {
      key: 'closer',
      tone: 'strength',
      question: '更靠近了什麼',
      title: '修復約定這週有被重新帶回桌上',
      description:
        'Repair Agreements 有新的修訂。這裡把它視為一種靠近：你們正在讓衝突後的回來方式更清楚。',
      movementLabel: deltaLabel(current.repairChangeCount, prior.repairChangeCount),
      sources: compactSources(['Repair Agreements']),
      action: { label: '回到 Heart', href: '/love-map#heart' },
    };
  }

  return {
    key: 'closer',
    tone: 'quiet',
    question: '更靠近了什麼',
    title: stats.priorSparse ? '還在累積可比較的靠近節奏' : '靠近的訊號這週沒有明顯放大',
    description: stats.priorSparse
      ? '前 7 天的可比較痕跡還不多，所以 Haven 先保守呈現，不把單週片段誇大成趨勢。'
      : '這不代表沒有變好，只代表目前沒有足夠明確的週對週證據。先把感謝、同步或雙向書寫繼續留下來。',
    movementLabel: stats.priorSparse ? '樣本仍在累積' : '暫無明顯變化',
    sources: compactSources([
      current.journalCount > 0 ? 'Journal' : null,
      current.appreciationCount > 0 ? 'Appreciation' : null,
      input.loveMapAvailable ? 'Relationship System' : null,
    ]),
    action: { label: '回看最近痕跡', href: '/memory' },
  };
}

function fragileCard(
  input: AnalysisWeeklyChangeBriefInput,
  stats: ComparisonStats,
): AnalysisWeeklyChangeCard {
  const { current, prior } = stats;
  const syncPct = clampPct(input.syncCompletionPct);

  if (current.highTensionCount > prior.highTensionCount) {
    return {
      key: 'fragile',
      tone: 'attention',
      question: '變脆弱了什麼',
      title: '高張力片段比前一週更需要先被照顧',
      description:
        '這裡不判斷誰造成張力，只指出這週更需要先顧安全感。越早回到慢一點的修復入口，越不容易讓誤會累積。',
      movementLabel: deltaLabel(current.highTensionCount, prior.highTensionCount),
      sources: compactSources(['Journal', input.repairAgreementFieldCount > 0 ? 'Repair Agreements' : null]),
      action: { label: '查看修復依據', evidenceId: 'tension' },
    };
  }

  if (prior.journalCount >= 2 && current.journalCount < prior.journalCount) {
    return {
      key: 'fragile',
      tone: 'attention',
      question: '變脆弱了什麼',
      title: '可讀痕跡變少，先不要靠猜測補空白',
      description:
        '和前 7 天相比，這週留下的文字比較少。不是問題本身，但容易讓彼此只剩推測，需要一個低壓力入口接回來。',
      movementLabel: deltaLabel(current.journalCount, prior.journalCount),
      sources: compactSources(['Journal', syncPct > 0 ? 'Daily Sync' : null]),
      action: { label: '展開雙方模式依據', evidenceId: 'patterns' },
    };
  }

  if (syncPct > 0 && syncPct < 55) {
    return {
      key: 'fragile',
      tone: 'attention',
      question: '變脆弱了什麼',
      title: '本週同步偏薄，日常節拍需要被接回來',
      description:
        '同步率不是關係分數，但它會影響誤會累積的速度。這週最脆弱的地方可能不是內容，而是接觸節奏。',
      movementLabel: `本週同步 ${syncPct}%`,
      sources: compactSources(['Daily Sync']),
      action: { label: '查看節奏依據', evidenceId: 'sync' },
    };
  }

  return {
    key: 'fragile',
    tone: 'quiet',
    question: '變脆弱了什麼',
    title: '沒有看到比前一週更放大的脆弱訊號',
    description:
      'Haven 目前沒有足夠依據說哪裡正在惡化。這份讀法會保留空白，不用模糊焦慮填滿它。',
    movementLabel: stats.priorSparse ? '保守讀法' : '沒有明顯升高',
    sources: compactSources([
      current.journalCount > 0 ? 'Journal' : null,
      syncPct > 0 ? 'Daily Sync' : null,
      input.repairAgreementFieldCount > 0 ? 'Repair Agreements' : null,
    ]),
    action: { label: '回看最近痕跡', href: '/memory' },
  };
}

function steadyCard(
  input: AnalysisWeeklyChangeBriefInput,
  stats: ComparisonStats,
): AnalysisWeeklyChangeCard {
  const { current, prior } = stats;
  const syncPct = clampPct(input.syncCompletionPct);

  if (input.hasPartner && current.myJournalCount > 0 && current.partnerJournalCount > 0) {
    return {
      key: 'steady',
      tone: 'strength',
      question: '仍然穩定的是什麼',
      title: '雙方書寫入口仍然都在',
      description:
        '不論這週整體感受如何，兩邊都還有留下痕跡，代表理解不是只靠單方解釋在撐。',
      movementLabel: `近 7 天共 ${current.journalCount} 則`,
      sources: compactSources(['Journal']),
      action: { label: '展開雙方痕跡依據', evidenceId: 'mutual' },
    };
  }

  if (current.appreciationCount > 0 && current.appreciationCount === prior.appreciationCount) {
    return {
      key: 'steady',
      tone: 'strength',
      question: '仍然穩定的是什麼',
      title: '感謝節奏沒有消失',
      description:
        '這週和前 7 天一樣，仍然有好事被說出口。這種小而穩定的表達，是關係裡很實際的支撐。',
      movementLabel: '感謝持平',
      sources: compactSources(['Appreciation']),
      action: { label: '查看感謝依據', evidenceId: 'appreciation' },
    };
  }

  if (input.repairAgreementFieldCount > 0) {
    return {
      key: 'steady',
      tone: 'quiet',
      question: '仍然穩定的是什麼',
      title: '需要修復時，仍然有約定可以回來看',
      description:
        'Repair Agreements 不需要每週都修改才有價值。它們穩定存在，代表衝突後的回來方式不是每次都從零開始。',
      movementLabel: `${input.repairAgreementFieldCount}/3 個修復約定`,
      sources: compactSources(['Repair Agreements']),
      action: { label: '回到 Heart', href: '/love-map#heart' },
    };
  }

  if (syncPct >= 55) {
    return {
      key: 'steady',
      tone: 'quiet',
      question: '仍然穩定的是什麼',
      title: '日常同步還保有基本節拍',
      description:
        '這週同步仍有基本密度。先保護這個節拍，再把更難的對話放進來，通常會比較安全。',
      movementLabel: `本週同步 ${syncPct}%`,
      sources: compactSources(['Daily Sync']),
      action: { label: '查看節奏依據', evidenceId: 'sync' },
    };
  }

  return {
    key: 'steady',
    tone: 'quiet',
    question: '仍然穩定的是什麼',
    title: '目前最穩定的是：Haven 不硬下結論',
    description:
      '資料還不夠時，穩定不是假裝一切很好，而是先把可比較的痕跡累積起來，等下週有更清楚的讀法。',
    movementLabel: '等待更多週節奏',
    sources: compactSources([input.loveMapAvailable ? 'Relationship System' : null]),
    action: { label: '回到今天同步', href: '/' },
  };
}

function focusCard(
  input: AnalysisWeeklyChangeBriefInput,
  stats: ComparisonStats,
  fragile: AnalysisWeeklyChangeCard,
  closer: AnalysisWeeklyChangeCard,
): AnalysisWeeklyChangeCard {
  const { current } = stats;

  if (fragile.tone === 'attention') {
    return {
      key: 'focus',
      tone: 'attention',
      question: '現在最值得留意的是什麼',
      title: '先照顧變脆弱的那一段，而不是急著解釋全部',
      description:
        '本週最有用的下一步，是把變脆弱的訊號拆回實際依據：哪一則、哪一天、哪個需要還沒被接住。',
      movementLabel: fragile.movementLabel,
      sources: fragile.sources,
      action: fragile.action,
    };
  }

  if (closer.tone === 'strength') {
    return {
      key: 'focus',
      tone: 'default',
      question: '現在最值得留意的是什麼',
      title: '把這週變靠近的地方變成一個小儀式',
      description:
        '既然已經有一個變好的方向，下一步不是擴大成大計畫，而是把它留成下週也做得到的一個小動作。',
      movementLabel: closer.movementLabel,
      sources: closer.sources,
      action: closer.action,
    };
  }

  if (stats.priorSparse || stats.comparableCurrent < 2) {
    return {
      key: 'focus',
      tone: 'quiet',
      question: '現在最值得留意的是什麼',
      title: '先讓下週真的有東西可以比較',
      description:
        '這週的重點不是追求漂亮洞察，而是留下足夠穩定的 Journal、Daily Sync 或感謝，讓下次回來能看見移動。',
      movementLabel: '建立比較基線',
      sources: compactSources([
        current.journalCount > 0 ? 'Journal' : null,
        input.syncCompletionPct > 0 ? 'Daily Sync' : null,
        current.appreciationCount > 0 ? 'Appreciation' : null,
      ]),
      action: { label: '回到今天同步', href: '/' },
    };
  }

  return {
    key: 'focus',
    tone: 'default',
    question: '現在最值得留意的是什麼',
    title: input.topTopics[0]
      ? `把「${input.topTopics[0]}」拆成一個可以談的小問題`
      : '把穩定留下來，再選一個小地方往前',
    description:
      '這週沒有劇烈移動，反而適合選一個小入口：把需要說清楚、把感謝說具體，或把共同方向帶進一次低壓力對話。',
    movementLabel: '穩定推進',
    sources: compactSources([
      input.topTopics.length > 0 ? 'Memory' : null,
      input.hasHeartCare ? 'Heart Care' : null,
      input.loveMapAvailable ? 'Relationship System' : null,
    ]),
    action: { label: input.topTopics.length ? '展開雙方模式依據' : '前往 Relationship System', evidenceId: input.topTopics.length ? 'patterns' : undefined, href: input.topTopics.length ? undefined : '/love-map' },
  };
}

export function buildAnalysisV2WeeklyChangeBrief(
  input: AnalysisWeeklyChangeBriefInput,
): AnalysisWeeklyChangeBriefModel {
  const stats = buildStats({
    ...input,
    syncCompletionPct: clampPct(input.syncCompletionPct),
    alignmentPct: clampPct(input.alignmentPct),
    repairAgreementFieldCount: clampCount(input.repairAgreementFieldCount),
  });

  const closer = closerCard(input, stats);
  const fragile = fragileCard(input, stats);
  const steady = steadyCard(input, stats);
  const focus = focusCard(input, stats, fragile, closer);
  const comparableCount = stats.comparableCurrent + stats.comparablePrior;

  return {
    title: '上週以來，哪裡有變化',
    description:
      '把最近一週和前一週放在一起看：哪裡更靠近、哪裡變脆弱、什麼仍然穩定，以及現在最值得留意哪一段。',
    sourceNote: stats.priorSparse
      ? '目前用近 7 天 / 前 7 天的可比較痕跡保守判讀；前 7 天樣本較少，所以不製造假趨勢。'
      : `目前用近 7 天 / 前 7 天的 ${comparableCount} 個可比較痕跡判讀，不把單一數字誇大成診斷。`,
    cards: [closer, fragile, steady, focus],
  };
}
