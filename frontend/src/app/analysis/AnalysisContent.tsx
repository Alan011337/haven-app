'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BookOpen,
  CalendarDays,
  Compass,
  HeartHandshake,
  NotebookPen,
  ShieldCheck,
  Target,
} from 'lucide-react';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import { useAuth } from '@/hooks/use-auth';
import {
  useDailySyncStatus,
  useHomeAppreciationHistory,
  useJournals,
  usePartnerJournals,
  usePartnerStatus,
} from '@/hooks/queries';
import { getJournalSafetyBand } from '@/lib/safety';
import {
  fetchWeeklyReport,
  type AppreciationPublic,
  type WeeklyReportPublic,
} from '@/services/api-client';
import { memoryService, type RelationshipReportResponse } from '@/services/memoryService';
import type { Journal } from '@/types';
import { AnalysisSkeleton } from '@/app/analysis/AnalysisSkeleton';
import {
  AnalysisCover,
  AnalysisEvidenceEntryCard,
  AnalysisEvidencePanel,
  AnalysisEvidenceStudio,
  AnalysisDiagnosticsCard,
  AnalysisLinkAction,
  AnalysisOverviewCard,
  AnalysisPulseCard,
  AnalysisRefreshButton,
  AnalysisReflectionCard,
  AnalysisSection,
  AnalysisSignalCard,
  AnalysisStatePanel,
} from '@/app/analysis/AnalysisPrimitives';

const DAY_MS = 24 * 60 * 60 * 1000;
const ANALYSIS_STALE_MS = 60_000;
const EMPTY_APPRECIATIONS: AppreciationPublic[] = [];
const EMPTY_TOPICS: string[] = [];

type JournalNeedEcho = {
  id: string;
  ownerLabel: string;
  need: string;
  createdAt: string;
};

type AnalysisSignal = {
  key: string;
  tone: 'strength' | 'attention' | 'quiet';
  eyebrow: string;
  title: string;
  description: string;
  meta?: string;
  href?: string;
  actionLabel?: string;
  evidenceId?: string;
};

type ReflectionPrompt = {
  key: string;
  eyebrow: string;
  title: string;
  description: string;
  href: string;
  actionLabel: string;
  evidenceId?: string;
};

type AnalysisWeeklyReport = WeeklyReportPublic & {
  partner_daily_sync_days_filled?: number;
  pair_sync_overlap_days?: number;
  pair_sync_alignment_rate?: number | null;
};

type AnalysisEvidenceStat = {
  label: string;
  value: string;
  hint: string;
};

type AnalysisEvidenceEntry = {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  meta?: string;
  badges?: string[];
};

type AnalysisEvidenceLens = {
  id: string;
  tone: 'strength' | 'attention' | 'quiet';
  eyebrow: string;
  title: string;
  summary: string;
  description: string;
  read: string;
  meta?: string;
  stats: AnalysisEvidenceStat[];
  entries: AnalysisEvidenceEntry[];
  emptyMessage: string;
  href?: string;
  actionLabel?: string;
};

function sortJournalsDesc(items: Journal[]) {
  return [...items].sort(
    (left, right) =>
      new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
}

function isWithinDays(value: string | null | undefined, days: number) {
  if (!value) return false;
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return false;
  return Date.now() - timestamp <= days * DAY_MS;
}

function formatShortDate(value: string | null | undefined) {
  if (!value) return '等待更多痕跡';
  return new Date(value).toLocaleDateString('zh-TW', {
    month: 'numeric',
    day: 'numeric',
  });
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return '等待更多痕跡';
  return new Date(value).toLocaleString('zh-TW', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDateRange(from: string | null | undefined, to: string | null | undefined) {
  if (!from || !to) return '最近一段時間';
  return `${formatShortDate(from)} - ${formatShortDate(to)}`;
}

function truncateText(value: string | null | undefined, max = 72) {
  if (!value) return '';
  const normalized = value.trim();
  if (normalized.length <= max) return normalized;
  return `${normalized.slice(0, max - 1)}…`;
}

function percentFromRate(rate: number | null | undefined) {
  if (typeof rate !== 'number' || Number.isNaN(rate)) return 0;
  if (rate <= 1) return Math.round(rate * 100);
  return Math.round(rate);
}

function summarizeMoodLabels(journals: Journal[]) {
  const counts = new Map<string, number>();
  const scores: number[] = [];

  for (const journal of journals) {
    const label = journal.mood_label?.trim();
    if (label) {
      counts.set(label, (counts.get(label) ?? 0) + 1);
    }
    if (typeof journal.mood_score === 'number' && Number.isFinite(journal.mood_score)) {
      scores.push(journal.mood_score);
    }
  }

  const topLabels = Array.from(counts.entries())
    .sort((left, right) => right[1] - left[1])
    .slice(0, 3);

  const averageScore = scores.length
    ? Math.round(scores.reduce((sum, value) => sum + value, 0) / scores.length)
    : null;

  return {
    topLabels,
    averageScore,
  };
}

function buildNeedEchoes(ownerLabel: string, journals: Journal[]): JournalNeedEcho[] {
  return journals
    .filter((journal) => journal.emotional_needs?.trim())
    .slice(0, 2)
    .map((journal) => ({
      id: `${ownerLabel}-${journal.id}`,
      ownerLabel,
      need: truncateText(journal.emotional_needs, 88),
      createdAt: journal.created_at,
    }));
}

function buildJournalEvidenceEntry(ownerLabel: string, journal: Journal): AnalysisEvidenceEntry {
  const badges = [journal.mood_label, journal.emotional_needs ? '提到需要' : null].filter(
    Boolean,
  ) as string[];

  if (getJournalSafetyBand(journal) !== 'normal') {
    badges.push('高張力');
  }

  return {
    id: `${ownerLabel}-${journal.id}`,
    eyebrow: ownerLabel,
    title: journal.mood_label
      ? `${ownerLabel}最近更常從「${journal.mood_label}」進入`
      : `${ownerLabel}留下了一則關鍵痕跡`,
    description:
      truncateText(journal.emotional_needs, 110) ||
      truncateText(journal.content, 118) ||
      '這則紀錄本身就是一段值得慢下來看的訊號。',
    meta: formatDateTime(journal.created_at),
    badges,
  };
}

function buildAppreciationEvidenceEntry(
  appreciation: AppreciationPublic,
  index: number,
): AnalysisEvidenceEntry {
  return {
    id: `appreciation-${appreciation.id}`,
    eyebrow: 'Appreciation',
    title: `被明確說出口的好事 ${index + 1}`,
    description: truncateText(appreciation.body_text, 126),
    meta: formatDateTime(appreciation.created_at),
    badges: ['被說出口', '正向連結'],
  };
}

function getJournalOwnerLabel(journal: Journal, viewerId: string | undefined) {
  if (viewerId && journal.user_id === viewerId) return '你';
  return '伴侶';
}

function buildPatternRead(options: {
  hasPartner: boolean;
  myMoodLabel?: string | null;
  partnerMoodLabel?: string | null;
  myNeed?: string | null;
  partnerNeed?: string | null;
}) {
  const { hasPartner, myMoodLabel, partnerMoodLabel, myNeed, partnerNeed } = options;

  if (!hasPartner) {
    return {
      title: myMoodLabel
        ? `你最近更常從「${myMoodLabel}」進入關係`
        : '你最近的進場方式還在慢慢成形',
      description:
        myNeed ??
        '現在的工作不是替兩個人下結論，而是先讀懂自己通常從什麼狀態開啟對話。',
      read:
        '先把自己的情緒入口讀清楚，未來雙向互動進來時，Analysis 才能更快分辨是節奏問題、需要問題，還是單純太累。',
    };
  }

  if (myMoodLabel && partnerMoodLabel) {
    return {
      title: `你最近更常從「${myMoodLabel}」進入，伴侶更常從「${partnerMoodLabel}」進入`,
      description:
        '這代表你們不一定在談不同的事，而是常常帶著不同的內在狀態走進同一段對話。',
      read:
        myNeed && partnerNeed
          ? `你的近期需要更靠近「${truncateText(myNeed, 28)}」，伴侶則更靠近「${truncateText(partnerNeed, 28)}」。先說狀態，再說立場，會比直接討論對錯更穩。`
          : '當兩邊進場狀態不同，最常見的錯位不是價值觀差異，而是彼此還沒先被安頓。',
    };
  }

  return {
    title: '你們的雙向模式還在慢慢浮出來',
    description:
      '目前已有部分情緒線索，但還不夠密集到讓 Haven 對雙方的互動模式下更細的判讀。',
    read:
      '等兩邊都再多留下幾則日記或同步後，這裡會更清楚看見誰通常先靠近、誰通常先退開，以及哪些需要最容易被漏接。',
  };
}

function getPulseBand(score: number | null, hasPartner: boolean) {
  if (!hasPartner) {
    return {
      label: '先從理解自己的節奏開始',
      summary:
        'Haven 已經能讀到你的筆記與同步節奏。等伴侶加入後，這裡會更完整地看見你們如何靠近、錯開與修復。',
    };
  }

  if (score === null) {
    return {
      label: '關係讀數還在聚焦',
      summary:
        '目前的互動訊號還不夠密集，Haven 先保留柔和的輪廓，等更多日記與同步累積後再給出更細緻的判讀。',
    };
  }

  if (score >= 80) {
    return {
      label: '最近是穩定靠近的節奏',
      summary:
        '你們最近的互動比較連續，適合趁這段穩定期再往更深的理解推進，而不是只停在日常交換。',
    };
  }

  if (score >= 60) {
    return {
      label: '整體仍然穩，但需要刻意維持',
      summary:
        '連結還在，但更仰賴刻意照顧。這時最有用的不是更多資訊，而是更一致的小小靠近。',
    };
  }

  if (score >= 40) {
    return {
      label: '最近比較容易錯開彼此的節奏',
      summary:
        '現在的關鍵不是追求更多輸出，而是先看見哪一種訊號最容易被漏接，然後重新對齊。',
    };
  }

  return {
    label: '先修復安全感，再追求深入',
    summary:
      '最近的脈動比較脆弱。這一頁會先把最需要放慢、補送與安撫的地方帶到前面，而不是催你們快速解決。',
  };
}

function getDailySyncStateText(
  todaySync: ReturnType<typeof useDailySyncStatus>['data'] | null,
  hasPartner: boolean,
) {
  if (!todaySync) {
    return '今天的同步狀態還沒完整回來。';
  }

  if (!hasPartner) {
    return todaySync.my_filled
      ? '你今天已經留下自己的同步痕跡。等伴侶加入後，這裡會開始看見彼此的回應差。'
      : '今天還可以先為自己留下一則同步，讓 Haven 開始讀到你的當下。';
  }

  if (todaySync.unlocked && todaySync.my_filled && todaySync.partner_filled) {
    return '今天的雙向同步已經完成，適合回到彼此的回答，談談那個真正想被理解的部分。';
  }

  if (todaySync.unlocked && !todaySync.my_filled && !todaySync.partner_filled) {
    return '今天的同步還沒開始，現在是用最小成本重新靠近的好入口。';
  }

  if (todaySync.unlocked && !todaySync.my_filled) {
    return '今天還差你的同步。先留下這一側的感受，對話會更不容易只剩回應與防守。';
  }

  if (todaySync.unlocked && !todaySync.partner_filled) {
    return '你已經先留下一格了，現在可以先放著，等對方的節奏跟上，而不是急著追問。';
  }

  return '今天的同步還沒有完全開啟，但 Haven 仍會先用最近的互動痕跡替你整理輪廓。';
}

export default function AnalysisContent() {
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const { user, isLoading: authLoading } = useAuth();
  const partnerStatusQuery = usePartnerStatus();
  const myJournalsQuery = useJournals();
  const partnerJournalsQuery = usePartnerJournals();
  const dailySyncQuery = useDailySyncStatus();
  const appreciationHistoryQuery = useHomeAppreciationHistory();

  const weeklyReportQuery = useQuery<AnalysisWeeklyReport>({
    queryKey: ['analysis', 'weekly-report'],
    queryFn: async () => fetchWeeklyReport() as Promise<AnalysisWeeklyReport>,
    enabled: !!user && !authLoading,
    staleTime: ANALYSIS_STALE_MS,
    retry: false,
  });

  const monthlyReportQuery = useQuery<RelationshipReportResponse>({
    queryKey: ['analysis', 'memory-report', 'month'],
    queryFn: () => memoryService.getReport('month'),
    enabled: !!user && !authLoading,
    staleTime: ANALYSIS_STALE_MS,
    retry: false,
  });

  const myJournals = useMemo(
    () => sortJournalsDesc(myJournalsQuery.data ?? []),
    [myJournalsQuery.data],
  );
  const partnerJournals = useMemo(
    () => sortJournalsDesc(partnerJournalsQuery.data ?? []),
    [partnerJournalsQuery.data],
  );

  const weeklyReport = weeklyReportQuery.data ?? null;
  const monthlyReport = monthlyReportQuery.data ?? null;
  const appreciationHistory = appreciationHistoryQuery.data ?? null;
  const appreciationRecent = appreciationHistory?.recent ?? EMPTY_APPRECIATIONS;
  const appreciationThisWeek = appreciationHistory?.thisWeek ?? EMPTY_APPRECIATIONS;
  const partnerStatus = partnerStatusQuery.data ?? null;
  const todaySync = dailySyncQuery.data ?? null;
  const hasPartner = Boolean(partnerStatus?.has_partner);
  const score = typeof partnerStatus?.current_score === 'number' ? partnerStatus.current_score : null;
  const pulseBand = getPulseBand(score, hasPartner);
  const syncCompletionPct = percentFromRate(weeklyReport?.daily_sync_completion_rate);
  const alignmentPct = percentFromRate(weeklyReport?.pair_sync_alignment_rate);
  const topTopics = monthlyReport?.top_topics ?? EMPTY_TOPICS;

  const allJournals = useMemo(
    () =>
      [...myJournals, ...partnerJournals].sort(
        (left, right) =>
          new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
      ),
    [myJournals, partnerJournals],
  );

  const journalCount14 = allJournals.filter((journal) => isWithinDays(journal.created_at, 14)).length;
  const myJournalCount14 = myJournals.filter((journal) => isWithinDays(journal.created_at, 14)).length;
  const partnerJournalCount14 = partnerJournals.filter((journal) => isWithinDays(journal.created_at, 14)).length;
  const highTensionCount14 = allJournals.filter(
    (journal) =>
      isWithinDays(journal.created_at, 14) &&
      getJournalSafetyBand(journal) !== 'normal',
  ).length;

  const myMoodSummary = summarizeMoodLabels(myJournals.slice(0, 8));
  const partnerMoodSummary = summarizeMoodLabels(partnerJournals.slice(0, 8));
  const latestMyJournal = myJournals[0] ?? null;
  const latestPartnerJournal = partnerJournals[0] ?? null;
  const latestMyNeedJournal =
    myJournals.find((journal) => journal.emotional_needs?.trim()) ?? latestMyJournal;
  const latestPartnerNeedJournal =
    partnerJournals.find((journal) => journal.emotional_needs?.trim()) ?? latestPartnerJournal;
  const needEchoes = [
    ...buildNeedEchoes('你', myJournals),
    ...buildNeedEchoes('伴侶', partnerJournals),
  ]
    .sort(
      (left, right) =>
        new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime(),
    )
    .slice(0, 3);

  const latestTraceAt =
    allJournals[0]?.created_at ??
    partnerStatus?.latest_journal_at ??
    monthlyReport?.generated_at ??
    weeklyReport?.period_end ??
    null;

  const hasJournalData = allJournals.length > 0;
  const hasAppreciationSignal =
    appreciationRecent.length > 0 ||
    appreciationThisWeek.length > 0 ||
    Boolean(weeklyReport?.appreciation_count);
  const hasInsightData =
    Boolean(weeklyReport?.insight) ||
    Boolean(monthlyReport?.emotion_trend_summary) ||
    Boolean(monthlyReport?.health_suggestion) ||
    topTopics.length > 0;
  const hasAnySignal =
    hasJournalData ||
    hasAppreciationSignal ||
    hasInsightData ||
    Boolean(partnerStatus?.has_partner) ||
    Boolean(todaySync?.my_filled) ||
    Boolean(todaySync?.partner_filled) ||
    Boolean(weeklyReport?.daily_sync_days_filled);

  const sourceErrorCount = [
    partnerStatusQuery.isError,
    myJournalsQuery.isError,
    partnerJournalsQuery.isError,
    appreciationHistoryQuery.isError,
    weeklyReportQuery.isError,
    monthlyReportQuery.isError,
    dailySyncQuery.isError,
  ].filter(Boolean).length;

  const showInitialSkeleton =
    (authLoading ||
      partnerStatusQuery.isLoading ||
      myJournalsQuery.isLoading ||
      partnerJournalsQuery.isLoading ||
      weeklyReportQuery.isLoading ||
      monthlyReportQuery.isLoading) &&
    !hasAnySignal;

  const refreshing =
    [
      partnerStatusQuery,
      myJournalsQuery,
      partnerJournalsQuery,
      appreciationHistoryQuery,
      dailySyncQuery,
      weeklyReportQuery,
      monthlyReportQuery,
    ].some((query) => query.isFetching) && !showInitialSkeleton;

  const handleRefresh = async () => {
    await Promise.allSettled([
      partnerStatusQuery.refetch(),
      myJournalsQuery.refetch(),
      partnerJournalsQuery.refetch(),
      appreciationHistoryQuery.refetch(),
      dailySyncQuery.refetch(),
      weeklyReportQuery.refetch(),
      monthlyReportQuery.refetch(),
    ]);
  };

  const currentRead =
    monthlyReport?.emotion_trend_summary ??
    weeklyReport?.insight ??
    getDailySyncStateText(todaySync, hasPartner);

  const patternRead = buildPatternRead({
    hasPartner,
    myMoodLabel: myMoodSummary.topLabels[0]?.[0] ?? null,
    partnerMoodLabel: partnerMoodSummary.topLabels[0]?.[0] ?? null,
    myNeed: latestMyNeedJournal?.emotional_needs ?? null,
    partnerNeed: latestPartnerNeedJournal?.emotional_needs ?? null,
  });

  const attentionSignals: AnalysisSignal[] = [];
  if (highTensionCount14 > 0) {
    attentionSignals.push({
      key: 'tension',
      tone: 'attention',
      eyebrow: 'Recent Tension',
      title: '最近的情緒張力偏高，先顧安全感再談內容',
      description:
        '近兩週有較高張力的日記訊號。這通常代表現在最需要的不是立刻說清楚，而是先把節奏放慢。',
      meta: `近兩週高張力紀錄 ${highTensionCount14} 則`,
      href: '/mediation',
      actionLabel: '前往調解模式',
      evidenceId: 'tension',
    });
  }
  if (syncCompletionPct > 0 && syncCompletionPct < 55) {
    attentionSignals.push({
      key: 'sync-rhythm',
      tone: 'attention',
      eyebrow: 'Rhythm Gap',
      title: '日常同步的節奏有點稀薄',
      description:
        '當日常同步不夠穩定時，誤會會更容易累積。先恢復小而穩定的接觸，比一次談很深更有用。',
      meta: `本週同步完成率 ${syncCompletionPct}%`,
      href: '/',
      actionLabel: '回到今天同步',
      evidenceId: 'sync',
    });
  }
  if ((partnerStatus?.unread_notification_count ?? 0) > 0) {
    attentionSignals.push({
      key: 'unread-signal',
      tone: 'attention',
      eyebrow: 'Unanswered Signals',
      title: '有一些訊號還在等待被接住',
      description:
        '通知不是壓力，但它們通常是對話入口。先讀完還沒接住的提醒，比直接猜測對方狀態更有效。',
      meta: `未接住提醒 ${partnerStatus?.unread_notification_count ?? 0} 則`,
      href: '/notifications',
      actionLabel: '前往通知中心',
      evidenceId: 'signals',
    });
  }
  if (!attentionSignals.length && monthlyReport?.health_suggestion) {
    attentionSignals.push({
      key: 'health-suggestion',
      tone: 'quiet',
      eyebrow: 'Gentle Nudge',
      title: '這一刻沒有明顯警訊，先照顧最需要的細節',
      description: monthlyReport.health_suggestion,
      href: '/memory',
      actionLabel: '回看最近痕跡',
      evidenceId: 'patterns',
    });
  }

  const strengthSignals: AnalysisSignal[] = [];
  if ((weeklyReport?.appreciation_count ?? 0) > 0) {
    strengthSignals.push({
      key: 'appreciation',
      tone: 'strength',
      eyebrow: 'What Is Going Well',
      title: '感謝有被說出來，而不是只停在心裡',
      description:
        '被感謝的次數不是比賽，但它代表你們最近仍然願意把好的感受具體說出來，這會顯著提升安全感。',
      meta: `本週感謝 ${weeklyReport?.appreciation_count ?? 0} 則`,
      href: '/',
      actionLabel: '回首頁延續這個節奏',
      evidenceId: 'appreciation',
    });
  }
  if (hasPartner && myJournalCount14 > 0 && partnerJournalCount14 > 0) {
    strengthSignals.push({
      key: 'both-sides-writing',
      tone: 'strength',
      eyebrow: 'Mutual Trace',
      title: '雙方最近都有留下自己的痕跡',
      description:
        '當兩邊都願意留下情緒與想法，理解會變成共同工作，而不是只有一方不停解釋。',
      meta: `近兩週你 ${myJournalCount14} 則 / 伴侶 ${partnerJournalCount14} 則`,
      href: '/memory',
      actionLabel: '回到回憶長廊',
      evidenceId: 'mutual',
    });
  }
  if (syncCompletionPct >= 70) {
    strengthSignals.push({
      key: 'sync-strong',
      tone: 'strength',
      eyebrow: 'Steady Rhythm',
      title: '你們的日常連結仍然有穩定節拍',
      description:
        '同步並不需要完美，但它一旦穩定，就會讓修復與理解變得容易很多。這是值得保護的基礎設施。',
      meta: `本週同步完成率 ${syncCompletionPct}%`,
      href: '/',
      actionLabel: '維持今天的同步',
      evidenceId: 'sync',
    });
  }
  if (!strengthSignals.length) {
    strengthSignals.push({
      key: 'quiet-strength',
      tone: 'quiet',
      eyebrow: 'Quiet Strength',
      title: '眼前的好事還比較細小，但它們已經在累積',
      description:
        '分析不會只在問題出現時才有用。現在先看到這些細小但穩定的靠近，本身就是一種關係資產。',
      href: '/memory',
      actionLabel: '把最近的痕跡看得更清楚',
      evidenceId: 'patterns',
    });
  }

  const reflectionPrompts: ReflectionPrompt[] = [];
  if (topTopics[0]) {
    reflectionPrompts.push({
      key: 'topic',
      eyebrow: 'Recurring Theme',
      title: `最近你們反覆回到「${topTopics[0]}」`,
      description:
        '如果把這個主題再說深一層，你們真正想被理解的，不一定是事件本身，而是事件底下的需要。',
      href: '/memory',
      actionLabel: '回看最近相關痕跡',
      evidenceId: 'patterns',
    });
  }
  if (todaySync?.unlocked && (!todaySync.my_filled || !todaySync.partner_filled)) {
    reflectionPrompts.push({
      key: 'today-sync',
      eyebrow: 'Today',
      title: '先把今天這一格填滿，再談更難的部分',
      description:
        '當天的同步是最便宜也最不容易防禦的一次靠近。先把今天說清楚，通常比回頭翻舊帳更有效。',
      href: '/',
      actionLabel: '回到今天同步',
      evidenceId: 'sync',
    });
  }
  if (highTensionCount14 > 0) {
    reflectionPrompts.push({
      key: 'repair',
      eyebrow: 'Repair Prompt',
      title: '把最近一段高張力時刻，改寫成「我其實需要…」',
      description:
        '分析真正想帶你們去的地方，不是辯出對錯，而是更快看見彼此保護自己時真正需要的東西。',
      href: '/mediation',
      actionLabel: '前往修復對話',
      evidenceId: 'tension',
    });
  }
  if (reflectionPrompts.length < 3) {
    reflectionPrompts.push({
      key: 'love-map',
      eyebrow: 'Deeper Understanding',
      title: '如果最近很忙，就把對話縮成一個更好的問題',
      description:
        '有時候分析最有用的出口，不是再看更多資料，而是找到一個能讓彼此說深一點的問題。',
      href: '/love-map',
      actionLabel: '前往愛情地圖',
    });
  }
  if (reflectionPrompts.length < 3) {
    reflectionPrompts.push({
      key: 'gratitude',
      eyebrow: 'Small Ritual',
      title: '挑一件最近很小、但你真的有感受到的好事',
      description:
        '當關係想往更深走，最有力量的常常不是大結論，而是那些被具體說出來的小小感謝。',
      href: '/',
      actionLabel: '回首頁寫下一句',
    });
  }

  const primaryAction =
    !hasPartner
      ? { href: '/settings', label: '完成伴侶連結' }
      : todaySync?.unlocked && (!todaySync.my_filled || !todaySync.partner_filled)
        ? { href: '/', label: '回到今天同步' }
        : attentionSignals[0]?.href && attentionSignals[0]?.actionLabel
          ? { href: attentionSignals[0].href, label: attentionSignals[0].actionLabel }
          : { href: '/memory', label: '回看最近痕跡' };

  const sourceSummary = [
    weeklyReport ? `週報 ${formatDateRange(weeklyReport.period_start, weeklyReport.period_end)}` : null,
    monthlyReport ? `月度分析 ${formatDateRange(monthlyReport.from_date, monthlyReport.to_date)}` : null,
    latestTraceAt ? `最近痕跡 ${formatShortDate(latestTraceAt)}` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  const evidenceLenses = useMemo(() => {
    const lenses: AnalysisEvidenceLens[] = [];

    if (highTensionCount14 > 0) {
      const tensionJournals = allJournals
        .filter(
          (journal) =>
            isWithinDays(journal.created_at, 14) &&
            getJournalSafetyBand(journal) !== 'normal',
        )
        .slice(0, 3);
      const tensionEntries = tensionJournals
        .map((journal) =>
          buildJournalEvidenceEntry(getJournalOwnerLabel(journal, user?.id), journal),
        );

      lenses.push({
        id: 'tension',
        tone: 'attention',
        eyebrow: 'Repair Evidence',
        title: '最近需要先照顧安全感的地方',
        summary: '把高張力時刻拆回實際痕跡，避免用抽象焦慮替代真正的需要。',
        description:
          '這裡放的是近兩週張力較高的實際片段。Analysis 想做的不是幫你判斷誰對，而是指出哪裡應該先慢下來。',
        read:
          monthlyReport?.health_suggestion ??
          '當高張力出現時，先回到需要與安全感，通常比立刻解釋立場更能讓對話重新變得可接近。',
        meta: `近兩週高張力紀錄 ${highTensionCount14} 則`,
        stats: [
          {
            label: '高張力片段',
            value: String(highTensionCount14),
            hint: '近兩週被標成需要放慢的紀錄',
          },
          {
            label: '最近一次',
            value: formatShortDate(tensionJournals[0]?.created_at ?? null),
            hint: '最近一次需要修復的時間點',
          },
          {
            label: '本週同步',
            value: `${syncCompletionPct}%`,
            hint: '同步越稀薄，誤會越容易累積',
          },
        ],
        entries: tensionEntries,
        emptyMessage: '等真正需要放慢的片段出現後，這裡會顯示更具體的修復依據。',
        href: '/mediation',
        actionLabel: '前往修復對話',
      });
    }

    if (weeklyReport || todaySync) {
      const syncEntries: AnalysisEvidenceEntry[] = [];
      if (latestMyJournal) {
        syncEntries.push(buildJournalEvidenceEntry('你', latestMyJournal));
      }
      if (latestPartnerJournal) {
        syncEntries.push(buildJournalEvidenceEntry('伴侶', latestPartnerJournal));
      }
      if (todaySync?.partner_answer_text) {
        syncEntries.push({
          id: 'today-sync-partner-answer',
          eyebrow: '今日同步',
          title: '今天對方已經先留下了自己的回答',
          description: truncateText(todaySync.partner_answer_text, 126),
          meta: todaySync.today ?? undefined,
          badges: ['今日同步', '等待被接住'],
        });
      }

      lenses.push({
        id: 'sync',
        tone: syncCompletionPct >= 70 ? 'strength' : 'attention',
        eyebrow: 'Rhythm Evidence',
        title: syncCompletionPct >= 70 ? '穩定的節拍目前還在' : '你們的節拍最近比較容易斷掉',
        summary: '把每週同步、雙向重疊和今天的狀態放在同一個畫面裡看，而不是只看單一百分比。',
        description:
          '關係節奏不是一個抽象分數。它來自誰有留下當下、誰還在等彼此跟上，以及你們是否仍有同天靠近的能力。',
        read: getDailySyncStateText(todaySync, hasPartner),
        meta: weeklyReport ? formatDateRange(weeklyReport.period_start, weeklyReport.period_end) : '今天',
        stats: [
          {
            label: '本週同步',
            value: `${syncCompletionPct}%`,
            hint: `${weeklyReport?.daily_sync_days_filled ?? 0}/7 天留下了回答`,
          },
          {
            label: '雙向重疊',
            value:
              alignmentPct > 0
                ? `${alignmentPct}%`
                : `${weeklyReport?.pair_sync_overlap_days ?? 0}/7`,
            hint: '兩邊在同一天一起留下痕跡的密度',
          },
          {
            label: '今日狀態',
            value:
              todaySync?.unlocked && todaySync.my_filled && todaySync.partner_filled
                ? '已完成'
                : todaySync?.unlocked
                  ? '未完成'
                  : '還沒開啟',
            hint: '今天是否已經形成雙向靠近',
          },
        ],
        entries: syncEntries.slice(0, 3),
        emptyMessage: '等同步與最近日記更穩定後，這裡會把節奏證據整理得更完整。',
        href: '/',
        actionLabel: todaySync?.unlocked ? '回到今天同步' : '回首頁',
      });
    }

    if ((partnerStatus?.unread_notification_count ?? 0) > 0) {
      const signalEntries: AnalysisEvidenceEntry[] = [];
      if (latestPartnerJournal) {
        signalEntries.push(buildJournalEvidenceEntry('伴侶', latestPartnerJournal));
      }
      if (latestMyJournal) {
        signalEntries.push(buildJournalEvidenceEntry('你', latestMyJournal));
      }
      if (todaySync?.partner_answer_text) {
        signalEntries.push({
          id: 'partner-sync-signal',
          eyebrow: '今日同步',
          title: '對方已經釋出一個想被接住的入口',
          description: truncateText(todaySync.partner_answer_text, 120),
          meta: todaySync.today ?? undefined,
          badges: ['尚未回應', '對話入口'],
        });
      }

      lenses.push({
        id: 'signals',
        tone: 'attention',
        eyebrow: 'Unanswered Signals',
        title: '還有一些訊號正在等你們回到彼此身上',
        summary: '通知本身不是洞察，但它經常代表某一邊已經先伸出手，卻還沒被好好接住。',
        description:
          '這裡把尚未被接住的提醒，對照到最近的文字痕跡與今天的同步狀態，幫你看見這些訊號不是憑空出現。',
        read:
          '先讀完還沒接住的提醒，不是為了清空待辦，而是為了回到那個已經先被釋出的對話入口。',
        meta: `未接住提醒 ${partnerStatus?.unread_notification_count ?? 0} 則`,
        stats: [
          {
            label: '未接住提醒',
            value: String(partnerStatus?.unread_notification_count ?? 0),
            hint: '目前仍在通知中心等待的關係訊號',
          },
          {
            label: '最近痕跡',
            value: formatShortDate(partnerStatus?.latest_journal_at ?? latestTraceAt),
            hint: '最近一次對方留下的可讀取訊號',
          },
          {
            label: '今日同步',
            value: todaySync?.partner_filled ? '對方已填' : '還沒看到',
            hint: '今天是否已有新的對話入口',
          },
        ],
        entries: signalEntries.slice(0, 3),
        emptyMessage: '等有更多未接住但具體可讀的訊號時，這裡會更明確指出它們來自哪裡。',
        href: '/notifications',
        actionLabel: '前往通知中心',
      });
    }

    if (hasAppreciationSignal) {
      const appreciationEntries = (appreciationThisWeek.length
        ? appreciationThisWeek
        : appreciationRecent
      )
        .slice(0, 3)
        .map(buildAppreciationEvidenceEntry);

      lenses.push({
        id: 'appreciation',
        tone: 'strength',
        eyebrow: 'Appreciation Evidence',
        title: '好事有被明確說出口，而不是只默默放在心裡',
        summary: '這裡不是樂觀濾鏡，而是具體看見：你們仍然願意把值得珍惜的東西說出來。',
        description:
          '感謝被具體說出口，會直接提升關係裡的安全感與可預測性。這是 Analysis 最想保護的一種連結證據。',
        read:
          appreciationEntries.length > 0
            ? '這些句子之所以重要，不在於它們多動人，而在於它們讓彼此知道：好事沒有被視為理所當然。'
            : '本週的感謝數字已經回來，但更細的文字片段暫時還沒取到。',
        meta: `本週感謝 ${weeklyReport?.appreciation_count ?? appreciationThisWeek.length} 則`,
        stats: [
          {
            label: '本週感謝',
            value: String(weeklyReport?.appreciation_count ?? appreciationThisWeek.length),
            hint: '這週被清楚說出口的好事',
          },
          {
            label: '近期樣本',
            value: String(appreciationEntries.length),
            hint: '目前能展開閱讀的感謝片段',
          },
          {
            label: '最近更新',
            value: formatShortDate(appreciationRecent[0]?.created_at ?? null),
            hint: '最近一次被記下的感謝',
          },
        ],
        entries: appreciationEntries,
        emptyMessage: '等感謝片段開始累積後，這裡會把它們整理成更可回看的連結證據。',
        href: '/',
        actionLabel: '回首頁延續這個節奏',
      });
    }

    if (hasPartner && myJournalCount14 > 0 && partnerJournalCount14 > 0) {
      lenses.push({
        id: 'mutual',
        tone: 'strength',
        eyebrow: 'Mutual Trace',
        title: '雙方都還願意把自己的版本留下來',
        summary: '當兩邊都留下痕跡，理解就不需要只靠猜測或單方解釋運作。',
        description:
          '這裡不是看誰寫得比較多，而是看雙方是否仍願意把自己的感受與需要留下，讓理解變成共同工作。',
        read:
          '只要兩邊都還願意留下文字，關係就還保有重新理解彼此的入口。這通常比表面上的平靜更珍貴。',
        meta: `近兩週你 ${myJournalCount14} 則 / 伴侶 ${partnerJournalCount14} 則`,
        stats: [
          {
            label: '你',
            value: String(myJournalCount14),
            hint: '近兩週你的日記痕跡',
          },
          {
            label: '伴侶',
            value: String(partnerJournalCount14),
            hint: '近兩週伴侶的日記痕跡',
          },
          {
            label: '最近靠近',
            value: formatShortDate(latestTraceAt),
            hint: '最近一次任一方留下痕跡',
          },
        ],
        entries: [latestMyJournal, latestPartnerJournal]
          .filter((journal): journal is Journal => Boolean(journal))
          .map((journal) =>
            buildJournalEvidenceEntry(getJournalOwnerLabel(journal, user?.id), journal),
          ),
        emptyMessage: '等雙方都再多留下一些內容後，這裡會更清楚顯示彼此的雙向痕跡。',
        href: '/memory',
        actionLabel: '回到回憶長廊',
      });
    }

    if (topTopics.length > 0 || needEchoes.length > 0 || latestMyNeedJournal || latestPartnerNeedJournal) {
      lenses.push({
        id: 'patterns',
        tone: 'quiet',
        eyebrow: 'Pattern Read',
        title: patternRead.title,
        summary: patternRead.description,
        description:
          'Haven 把最近的情緒語氣、需要和月度主題放在同一條線上，幫你看見你們是怎麼走進對話的。',
        read: patternRead.read,
        meta: topTopics.length ? `月度主題 · ${topTopics.slice(0, 3).join(' · ')}` : undefined,
        stats: [
          {
            label: '你最近',
            value: myMoodSummary.topLabels[0]?.[0] ?? '—',
            hint: myMoodSummary.averageScore !== null ? `平均情緒分數 ${myMoodSummary.averageScore}` : '等待更多內容',
          },
          {
            label: hasPartner ? '伴侶最近' : '主題數量',
            value: hasPartner ? partnerMoodSummary.topLabels[0]?.[0] ?? '—' : String(topTopics.length),
            hint: hasPartner
              ? partnerMoodSummary.averageScore !== null
                ? `平均情緒分數 ${partnerMoodSummary.averageScore}`
                : '等待更多內容'
              : '月度整理到的重複主題',
          },
          {
            label: '最近需要',
            value: needEchoes[0]?.ownerLabel ?? '—',
            hint: needEchoes[0] ? truncateText(needEchoes[0].need, 22) : '等待更清楚的需要描述',
          },
        ],
        entries: [latestMyNeedJournal, latestPartnerNeedJournal]
          .filter((journal): journal is Journal => Boolean(journal))
          .map((journal) =>
            buildJournalEvidenceEntry(getJournalOwnerLabel(journal, user?.id), journal),
          ),
        emptyMessage: '等情緒語氣與需要更清楚後，這裡會顯示更完整的雙方模式。',
        href: '/memory',
        actionLabel: '回看最近痕跡',
      });
    }

    return lenses;
  }, [
    alignmentPct,
    allJournals,
    appreciationRecent,
    appreciationThisWeek,
    hasAppreciationSignal,
    hasPartner,
    highTensionCount14,
    latestMyJournal,
    latestMyNeedJournal,
    latestPartnerJournal,
    latestPartnerNeedJournal,
    latestTraceAt,
    monthlyReport?.health_suggestion,
    myJournalCount14,
    myMoodSummary.averageScore,
    myMoodSummary.topLabels,
    needEchoes,
    partnerJournalCount14,
    partnerMoodSummary.averageScore,
    partnerMoodSummary.topLabels,
    partnerStatus?.latest_journal_at,
    partnerStatus?.unread_notification_count,
    patternRead.description,
    patternRead.read,
    patternRead.title,
    syncCompletionPct,
    todaySync,
    topTopics,
    user?.id,
    weeklyReport,
  ]);

  const selectedEvidence =
    evidenceLenses.find((lens) => lens.id === selectedEvidenceId) ?? evidenceLenses[0] ?? null;

  const focusEvidenceLens = (lensId: string | undefined) => {
    if (!lensId) return;
    setSelectedEvidenceId(lensId);
    if (typeof window === 'undefined') return;
    window.requestAnimationFrame(() => {
      document.getElementById('analysis-evidence')?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    });
  };

  const renderSignalActions = (signal: AnalysisSignal) => (
    <>
      {signal.href && signal.actionLabel ? (
        <AnalysisLinkAction href={signal.href} label={signal.actionLabel} />
      ) : null}
      {signal.evidenceId ? (
        <Button
          variant="ghost"
          size="sm"
          aria-pressed={selectedEvidence?.id === signal.evidenceId}
          onClick={() => focusEvidenceLens(signal.evidenceId)}
        >
          查看依據
        </Button>
      ) : null}
    </>
  );

  if (showInitialSkeleton) {
    return <AnalysisSkeleton />;
  }

  if (!hasAnySignal && sourceErrorCount >= 4) {
    return (
      <AnalysisStatePanel
        tone="error"
        eyebrow="Analysis Sources"
        title="洞察來源暫時沒有順利回來"
        description="這不是空白，而是分析資料載入失敗。重新整理後，Haven 會把目前最有用的關係訊號重新帶回來。"
        actions={
          <AnalysisRefreshButton
            loading={refreshing}
            onClick={() => void handleRefresh()}
            label="重新整理洞察"
            variant="primary"
          />
        }
      />
    );
  }

  return (
    <div className="space-y-[clamp(1.5rem,3vw,2.75rem)] animate-page-enter">
      <AnalysisCover
        eyebrow="Analysis"
        title={hasPartner ? '把最近的互動，翻成更深的理解。' : '先把自己的情緒節奏，讀得更清楚。'}
        description={
          hasPartner
            ? '這裡不是冷冰冰的圖表頁。Haven 會把你們最近的同步、日記、回憶線索與關係節奏整理成可理解、可回應、可行動的 insight。'
            : '在伴侶加入之前，Analysis 會先幫你讀出自己的情緒節奏與書寫習慣，讓未來的雙向理解有更穩的起點。'
        }
        pulse={currentRead}
        highlights={
          <div className="flex flex-wrap items-center gap-2.5">
            <Badge
              variant={typeof score === 'number' && score > 0 ? 'count' : 'metadata'}
              size="md"
              className={typeof score === 'number' && score > 0 ? '' : 'border-white/54 bg-white/72'}
            >
              關係讀數 {typeof score === 'number' && score > 0 ? score : '—'}
            </Badge>
            <Badge
              variant={syncCompletionPct >= 60 ? 'success' : syncCompletionPct > 0 ? 'warning' : 'metadata'}
              size="md"
            >
              本週同步 {syncCompletionPct}%
            </Badge>
            <Badge variant="metadata" size="md" className="border-white/54 bg-white/72">
              本月主題 {topTopics.length}
            </Badge>
            <Badge variant="metadata" size="md" className="border-white/54 bg-white/72">
              近兩週痕跡 {journalCount14}
            </Badge>
          </div>
        }
        actions={
          <>
            <AnalysisLinkAction href={primaryAction.href} label={primaryAction.label} />
            <AnalysisRefreshButton
              loading={refreshing}
              onClick={() => void handleRefresh()}
              label="重新整理洞察"
            />
          </>
        }
        featured={
          <AnalysisPulseCard
            score={score}
            label={pulseBand.label}
            summary={pulseBand.summary}
            periodLabel={sourceSummary || '最近一段時間'}
            metricRows={
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-[1.65rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <p className="type-caption uppercase tracking-[0.18em] text-primary/76">同步完成</p>
                  <p className="mt-2 text-2xl font-semibold text-card-foreground tabular-nums">
                    {syncCompletionPct}%
                  </p>
                  <p className="mt-1 type-caption text-muted-foreground">
                    {weeklyReport?.daily_sync_days_filled ?? 0}/7 天
                  </p>
                </div>
                <div className="rounded-[1.65rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <p className="type-caption uppercase tracking-[0.18em] text-primary/76">感謝表達</p>
                  <p className="mt-2 text-2xl font-semibold text-card-foreground tabular-nums">
                    {weeklyReport?.appreciation_count ?? 0}
                  </p>
                  <p className="mt-1 type-caption text-muted-foreground">這週被說出的好事</p>
                </div>
                <div className="rounded-[1.65rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <p className="type-caption uppercase tracking-[0.18em] text-primary/76">雙向重疊</p>
                  <p className="mt-2 text-2xl font-semibold text-card-foreground tabular-nums">
                    {alignmentPct > 0 ? `${alignmentPct}%` : `${weeklyReport?.pair_sync_overlap_days ?? 0}/7`}
                  </p>
                  <p className="mt-1 type-caption text-muted-foreground">同天同步的重合度</p>
                </div>
              </div>
            }
            footer={
              <div className="rounded-[1.8rem] border border-white/56 bg-white/72 p-4 shadow-soft backdrop-blur-md">
                <p className="type-caption uppercase tracking-[0.18em] text-primary/76">Today&apos;s Read</p>
                <p className="mt-2 type-body-muted text-card-foreground">
                  {getDailySyncStateText(todaySync, hasPartner)}
                </p>
              </div>
            }
          />
        }
        aside={
          <>
            <AnalysisOverviewCard
              eyebrow="Signal Coverage"
              title="這頁現在握著哪些線索"
              description="Analysis 不假裝全知。它會清楚告訴你目前是從哪些真實互動裡讀出輪廓。"
            >
              <div className="grid gap-3 sm:grid-cols-3 2xl:grid-cols-1">
                <div className="rounded-[1.65rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <div className="flex items-center gap-2 text-card-foreground">
                    <NotebookPen className="h-4 w-4 text-primary" aria-hidden />
                    <p className="type-caption uppercase tracking-[0.18em] text-primary/76">筆記痕跡</p>
                  </div>
                  <p className="mt-2 text-2xl font-semibold text-card-foreground tabular-nums">{journalCount14}</p>
                  <p className="mt-1 type-caption text-muted-foreground">近兩週你 {myJournalCount14} / 對方 {partnerJournalCount14}</p>
                </div>
                <div className="rounded-[1.65rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <div className="flex items-center gap-2 text-card-foreground">
                    <CalendarDays className="h-4 w-4 text-primary" aria-hidden />
                    <p className="type-caption uppercase tracking-[0.18em] text-primary/76">週節奏</p>
                  </div>
                  <p className="mt-2 text-2xl font-semibold text-card-foreground tabular-nums">{syncCompletionPct}%</p>
                  <p className="mt-1 type-caption text-muted-foreground">{formatDateRange(weeklyReport?.period_start, weeklyReport?.period_end)}</p>
                </div>
                <div className="rounded-[1.65rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <div className="flex items-center gap-2 text-card-foreground">
                    <Compass className="h-4 w-4 text-primary" aria-hidden />
                    <p className="type-caption uppercase tracking-[0.18em] text-primary/76">最近更新</p>
                  </div>
                  <p className="mt-2 text-lg font-semibold text-card-foreground tabular-nums">{formatShortDate(latestTraceAt)}</p>
                  <p className="mt-1 type-caption text-muted-foreground">最近一次可讀取的關係痕跡</p>
                </div>
              </div>
            </AnalysisOverviewCard>

            <AnalysisDiagnosticsCard
              eyebrow="Source Note"
              title="這份洞察怎麼來"
              description={
                monthlyReport
                  ? `月度主題生成於 ${formatDateTime(monthlyReport.generated_at)}。`
                  : '目前先使用每週節奏與最近互動線索，等月度分析回來後會更完整。'
              }
              actions={
                sourceErrorCount > 0 && hasAnySignal ? (
                  <Button variant="ghost" size="sm" onClick={() => void handleRefresh()}>
                    部分來源需要重整
                  </Button>
                ) : undefined
              }
            />
          </>
        }
      />

      {sourceErrorCount > 0 && hasAnySignal ? (
        <AnalysisStatePanel
          tone="quiet"
          eyebrow="Partial Insight"
          title="目前先用已經回來的線索幫你整理輪廓"
          description="有些分析來源暫時沒有回來，但這頁仍然可以先提供可用的理解與下一步。重新整理後，細節會更完整。"
          actions={
            <AnalysisRefreshButton
              loading={refreshing}
              onClick={() => void handleRefresh()}
              label="補齊分析來源"
            />
          }
        />
      ) : null}

      {!hasAnySignal ? (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px] xl:gap-8">
          <div className="space-y-6">
            <AnalysisStatePanel
              tone="quiet"
              eyebrow="Getting Started"
              title={hasPartner ? '先累積幾個真實互動，Analysis 才會開始變得有用' : '先讓 Haven 讀到你們的第一批痕跡'}
              description={
                hasPartner
                  ? '這裡不會用空圖表假裝懂你們。先寫幾則日記、完成幾次同步，分析才會真的開始回答你們的問題。'
                  : '你還沒連結伴侶，也還沒有足夠的日記或同步。完成這兩件事後，Analysis 才會從漂亮的空間變成真正有用的理解中心。'
              }
              actions={
                <>
                  <AnalysisLinkAction href={hasPartner ? '/' : '/settings'} label={hasPartner ? '回首頁寫第一則日記' : '完成伴侶連結'} />
                  <AnalysisLinkAction href="/" label="打開今天同步" />
                </>
              }
            />

            <AnalysisSection
              eyebrow="How This Becomes Useful"
              title="當資料開始累積後，這頁會替你們回答這些問題"
              description="不是更多數字，而是更好的理解入口。"
            >
              <div className="grid gap-4 lg:grid-cols-3">
                <AnalysisSignalCard
                  eyebrow="Question 01"
                  title="我們最近到底卡在哪裡？"
                  description="Haven 會把高張力、漏接訊號與同步節奏放在一起看，幫你分辨是需要修復，還是只是需要重新對齊。"
                />
                <AnalysisSignalCard
                  eyebrow="Question 02"
                  title="哪些地方其實正在變好？"
                  description="感謝、穩定同步、雙向書寫與重複主題，都會變成你們正在累積的連結證據。"
                  tone="strength"
                />
                <AnalysisSignalCard
                  eyebrow="Question 03"
                  title="下一次應該從哪裡開始談？"
                  description="Analysis 會把 insight 收斂成可行動的反思提示，而不是只留下漂亮但空洞的總結。"
                  tone="quiet"
                />
              </div>
            </AnalysisSection>
          </div>

          <div className="space-y-4">
            <AnalysisOverviewCard
              eyebrow="What To Feed"
              title="最能讓洞察變清楚的三種輸入"
              description="如果你想讓 Analysis 快速變有用，先把這三件事做起來。"
            >
              <div className="space-y-3">
                <div className="rounded-[1.5rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <p className="type-caption uppercase tracking-[0.18em] text-primary/76">01 日記</p>
                  <p className="mt-2 type-body-muted text-card-foreground">留下內容、情緒標籤與內在需要，Analysis 才能看見真正的情緒紋理。</p>
                </div>
                <div className="rounded-[1.5rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <p className="type-caption uppercase tracking-[0.18em] text-primary/76">02 每日同步</p>
                  <p className="mt-2 type-body-muted text-card-foreground">同步率決定這段關係的節奏是否被持續照顧，而不是只在有事時才開口。</p>
                </div>
                <div className="rounded-[1.5rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <p className="type-caption uppercase tracking-[0.18em] text-primary/76">03 一句感謝</p>
                  <p className="mt-2 type-body-muted text-card-foreground">被明確說出的好事，會成為理解不只圍繞問題運作的重要證據。</p>
                </div>
              </div>
            </AnalysisOverviewCard>
          </div>
        </div>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px] xl:gap-8">
          <div className="space-y-8">
            <AnalysisSection
              eyebrow="Needs Attention"
              title="值得你們優先照看的地方"
              description="這些不是評分扣點，而是現在最值得優先安頓的訊號。"
              badge={<Badge variant={attentionSignals[0]?.tone === 'attention' ? 'warning' : 'metadata'} size="md">{attentionSignals.length} 個焦點</Badge>}
            >
              <div className="grid gap-4 lg:grid-cols-2">
                {attentionSignals.map((signal) => (
                  <AnalysisSignalCard
                    key={signal.key}
                    tone={signal.tone}
                    eyebrow={signal.eyebrow}
                    title={signal.title}
                    description={signal.description}
                    meta={signal.meta ? <p className="type-caption text-card-foreground/72">{signal.meta}</p> : undefined}
                    actions={renderSignalActions(signal)}
                  />
                ))}
              </div>
            </AnalysisSection>

            <AnalysisSection
              eyebrow="What Is Going Well"
              title="正在替你們撐住關係的好事"
              description="Analysis 不只找問題，也會替你們指出那些已經在發揮作用的連結。"
              badge={<Badge variant="success" size="md">{strengthSignals.length} 個優勢</Badge>}
            >
              <div className="grid gap-4 lg:grid-cols-2">
                {strengthSignals.map((signal) => (
                  <AnalysisSignalCard
                    key={signal.key}
                    tone={signal.tone}
                    eyebrow={signal.eyebrow}
                    title={signal.title}
                    description={signal.description}
                    meta={signal.meta ? <p className="type-caption text-card-foreground/72">{signal.meta}</p> : undefined}
                    actions={renderSignalActions(signal)}
                  />
                ))}
              </div>
            </AnalysisSection>

            {selectedEvidence ? (
              <AnalysisEvidenceStudio
                eyebrow="Insight Evidence"
                title="把判讀拆回真正的依據"
                description="這裡不是另一份摘要，而是把 Analysis 的主要判讀拆回實際痕跡、週節奏與具體片段，讓理解有根據。"
                lenses={evidenceLenses.map((lens) => ({
                  id: lens.id,
                  tone: lens.tone,
                  eyebrow: lens.eyebrow,
                  title: lens.title,
                  summary: lens.summary,
                  meta: lens.meta,
                }))}
                activeLensId={selectedEvidence.id}
                onSelectLens={setSelectedEvidenceId}
                panel={
                  <AnalysisEvidencePanel
                    tone={selectedEvidence.tone}
                    eyebrow={selectedEvidence.eyebrow}
                    title={selectedEvidence.title}
                    description={selectedEvidence.description}
                    meta={selectedEvidence.meta}
                    summary={selectedEvidence.read}
                    stats={
                      <div className="grid gap-3 sm:grid-cols-3">
                        {selectedEvidence.stats.map((stat) => (
                          <div
                            key={stat.label}
                            className="rounded-[1.45rem] border border-white/56 bg-white/72 p-4 shadow-soft"
                          >
                            <p className="type-caption uppercase tracking-[0.18em] text-primary/76">
                              {stat.label}
                            </p>
                            <p className="mt-2 text-2xl font-semibold text-card-foreground tabular-nums">
                              {stat.value}
                            </p>
                            <p className="mt-1 type-caption text-muted-foreground">{stat.hint}</p>
                          </div>
                        ))}
                      </div>
                    }
                    actions={
                      selectedEvidence.href && selectedEvidence.actionLabel ? (
                        <AnalysisLinkAction
                          href={selectedEvidence.href}
                          label={selectedEvidence.actionLabel}
                        />
                      ) : undefined
                    }
                  >
                    {selectedEvidence.entries.length ? (
                      <div className="grid gap-3 lg:grid-cols-2">
                        {selectedEvidence.entries.map((entry) => (
                          <AnalysisEvidenceEntryCard
                            key={entry.id}
                            eyebrow={entry.eyebrow}
                            title={entry.title}
                            description={entry.description}
                            meta={entry.meta}
                            badges={entry.badges}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="rounded-[1.6rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                        <p className="type-body-muted text-muted-foreground">
                          {selectedEvidence.emptyMessage}
                        </p>
                      </div>
                    )}
                  </AnalysisEvidencePanel>
                }
              />
            ) : null}

            <AnalysisSection
              eyebrow="Reflection Studio"
              title="下一次對話，可以從哪裡開始"
              description="這些不是作業，而是把 insight 轉成更好 conversation opener 的入口。"
              badge={<Badge variant="count" size="md">3 個提示</Badge>}
            >
              <div className="grid gap-4 lg:grid-cols-3">
                {reflectionPrompts.slice(0, 3).map((prompt) => (
                  <div key={prompt.key} className="space-y-3">
                    <AnalysisReflectionCard
                      eyebrow={prompt.eyebrow}
                      title={prompt.title}
                      description={prompt.description}
                      href={prompt.href}
                      actionLabel={prompt.actionLabel}
                    />
                    {prompt.evidenceId ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full justify-center rounded-full"
                        aria-pressed={selectedEvidence?.id === prompt.evidenceId}
                        onClick={() => focusEvidenceLens(prompt.evidenceId)}
                      >
                        先看這個提示的依據
                      </Button>
                    ) : null}
                  </div>
                ))}
              </div>
            </AnalysisSection>
          </div>

          <div className="space-y-4">
            <AnalysisOverviewCard
              eyebrow="Recurring Topics"
              title="你們反覆回來的主題"
              description="主題不是貼標籤，而是幫你看見：哪些事情其實還在找更深的說法。"
            >
              {topTopics.length ? (
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    {topTopics.map((topic) => (
                      <Badge
                        key={topic}
                        variant="outline"
                        size="md"
                        className="border-white/54 bg-white/70"
                      >
                        {topic}
                      </Badge>
                    ))}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-pressed={selectedEvidence?.id === 'patterns'}
                    onClick={() => focusEvidenceLens('patterns')}
                  >
                    展開這些主題的依據
                  </Button>
                </div>
              ) : (
                <p className="type-body-muted text-muted-foreground">
                  等更多對話與回憶累積後，重複主題會在這裡變得更清楚。
                </p>
              )}
            </AnalysisOverviewCard>

            <AnalysisOverviewCard
              eyebrow="Emotional Climate"
              title="最近常出現的情緒語氣"
              description="不是判斷誰比較好或不好，而是看見各自目前更常從哪種狀態進入關係。"
            >
              <div className="space-y-3">
                <div className="rounded-[1.45rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <p className="type-caption uppercase tracking-[0.18em] text-primary/76">
                    Pattern Read
                  </p>
                  <p className="mt-2 text-base font-semibold text-card-foreground">
                    {patternRead.title}
                  </p>
                  <p className="mt-2 type-body-muted text-muted-foreground">
                    {patternRead.description}
                  </p>
                  <div className="mt-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-pressed={selectedEvidence?.id === 'patterns'}
                      onClick={() => focusEvidenceLens('patterns')}
                    >
                      展開雙方模式依據
                    </Button>
                  </div>
                </div>
                <div className="rounded-[1.5rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <div className="flex items-center gap-2 text-card-foreground">
                    <BookOpen className="h-4 w-4 text-primary" aria-hidden />
                    <p className="type-caption uppercase tracking-[0.18em] text-primary/76">你</p>
                  </div>
                  <p className="mt-2 text-base font-semibold text-card-foreground">
                    {myMoodSummary.topLabels[0]?.[0] ?? '還在累積'}
                  </p>
                  <p className="mt-1 type-caption text-muted-foreground">
                    平均情緒分數 {myMoodSummary.averageScore ?? '—'} · 最近 {myJournals.length} 則
                  </p>
                </div>
                <div className="rounded-[1.5rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <div className="flex items-center gap-2 text-card-foreground">
                    <HeartHandshake className="h-4 w-4 text-primary" aria-hidden />
                    <p className="type-caption uppercase tracking-[0.18em] text-primary/76">伴侶</p>
                  </div>
                  <p className="mt-2 text-base font-semibold text-card-foreground">
                    {partnerMoodSummary.topLabels[0]?.[0] ?? (hasPartner ? '還在累積' : '尚未連結')}
                  </p>
                  <p className="mt-1 type-caption text-muted-foreground">
                    平均情緒分數 {partnerMoodSummary.averageScore ?? '—'} · 最近 {partnerJournals.length} 則
                  </p>
                </div>
              </div>
            </AnalysisOverviewCard>

            <AnalysisOverviewCard
              eyebrow="Need Echoes"
              title="最近比較常浮出的需要"
              description="這些不是完整答案，但它們常常是更深對話最值得先照顧的入口。"
            >
              {needEchoes.length ? (
                <div className="space-y-3">
                  {needEchoes.map((echo) => (
                    <div
                      key={echo.id}
                      className="rounded-[1.45rem] border border-white/56 bg-white/72 p-4 shadow-soft"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <Badge variant="metadata" size="sm">
                          {echo.ownerLabel}
                        </Badge>
                        <span className="type-caption text-muted-foreground">{formatShortDate(echo.createdAt)}</span>
                      </div>
                      <p className="mt-3 type-body-muted text-card-foreground">{echo.need}</p>
                    </div>
                  ))}
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-pressed={selectedEvidence?.id === 'patterns'}
                    onClick={() => focusEvidenceLens('patterns')}
                  >
                    看這些需要如何形成模式
                  </Button>
                </div>
              ) : (
                <p className="type-body-muted text-muted-foreground">
                  當日記裡開始出現更清楚的情緒需要，這裡會先幫你把它們安靜整理出來。
                </p>
              )}
            </AnalysisOverviewCard>

            <AnalysisOverviewCard
              eyebrow="Today&apos;s Practical Read"
              title="今天適合怎麼靠近"
              description="把洞察變成今天就能用的節奏提示。"
            >
              <div className="space-y-3">
                <div className="rounded-[1.45rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <div className="flex items-center gap-2 text-card-foreground">
                    <ShieldCheck className="h-4 w-4 text-primary" aria-hidden />
                    <p className="type-caption uppercase tracking-[0.18em] text-primary/76">Health Suggestion</p>
                  </div>
                  <p className="mt-3 type-body-muted text-card-foreground">
                    {monthlyReport?.health_suggestion ??
                      '如果今天只做一件事，就先完成一次低壓力的同步，讓關係重新回到同一個時區。'}
                  </p>
                </div>
                <div className="rounded-[1.45rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <div className="flex items-center gap-2 text-card-foreground">
                    <Target className="h-4 w-4 text-primary" aria-hidden />
                    <p className="type-caption uppercase tracking-[0.18em] text-primary/76">Immediate Next Step</p>
                  </div>
                  <p className="mt-3 type-body-muted text-card-foreground">
                    {getDailySyncStateText(todaySync, hasPartner)}
                  </p>
                </div>
              </div>
            </AnalysisOverviewCard>
          </div>
        </div>
      )}
    </div>
  );
}
