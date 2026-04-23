'use client';

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { CalendarDays, Clock3, Gift } from 'lucide-react';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import { GlassCard } from '@/components/haven/GlassCard';
import { DeckArchiveCard } from '@/features/decks/ui/DeckPrimitives';
import { useMemoryData } from '@/features/memory/useMemoryData';
import {
  fetchAppreciationById,
  type AppreciationPublic,
} from '@/services/appreciations-api';
import {
  fetchDeckHistoryEntry,
  type DeckHistoryEntry,
} from '@/services/deckService';
import type {
  TimeCapsuleMemory,
  TimelineAppreciationItem,
  TimelineAttachmentMeta,
  TimelineCardItem,
  TimelineItem,
  TimelineJournalItem,
  TimelinePhotoItem,
} from '@/services/memoryService';
import { memoryService } from '@/services/memoryService';
import {
  buildMemoryDayRevealModel,
  getMemoryDayRevealArtifactKey,
} from '@/lib/memory-day-reveal';
import MemorySkeleton from './MemorySkeleton';
import {
  type MemoryCardKind,
  MemoryCalendarAtlas,
  MemoryCompanionMemoryCard,
  MemoryCover,
  MemoryDayRevealSummary,
  MemoryArtifactDialog,
  MemoryFeaturedMemoryCard,
  MemoryModeRail,
  MemoryOverviewCard,
  MemoryStatePanel,
  MemoryStreamMemoryCard,
} from './MemoryPrimitives';

type TimelineMemoryModel = {
  kind: MemoryCardKind;
  eyebrow: string;
  title: string;
  description: string;
  dateLabel: string;
  badges: string[];
  detailLines: string[];
  support?: string;
  attachments?: TimelineAttachmentMeta[];
};

const MEMORY_DAY_TIMELINE_LIMIT = 100;
const MEMORY_DAY_STALE_TIME_MS = 60_000;
const DATE_ONLY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

type MemoryArtifactDialogState =
  | {
      kind: 'card';
      sessionId: string;
      date: string;
      previewTitle: string;
    }
  | {
      kind: 'appreciation';
      appreciationId: number | null;
      date: string;
      previewTitle: string;
      isMine: boolean;
    };

function parseMemoryDate(dateString: string) {
  if (DATE_ONLY_PATTERN.test(dateString)) {
    const [year, month, day] = dateString.split('-').map(Number);
    return new Date(year, month - 1, day);
  }

  return new Date(dateString);
}

function formatDateLong(dateString: string) {
  const parsedDate = parseMemoryDate(dateString);
  if (Number.isNaN(parsedDate.getTime())) {
    return dateString;
  }

  return parsedDate.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  });
}

function formatDateShort(dateString: string) {
  const parsedDate = parseMemoryDate(dateString);
  if (Number.isNaN(parsedDate.getTime())) {
    return dateString;
  }

  return parsedDate.toLocaleDateString('zh-TW', {
    month: 'long',
    day: 'numeric',
  });
}

function formatGeneratedLabel(dateString: string) {
  const parsedDate = parseMemoryDate(dateString);
  if (Number.isNaN(parsedDate.getTime())) {
    return dateString;
  }

  return parsedDate.toLocaleDateString('zh-TW', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function buildJournalHref(journalId: string, date: string) {
  const params = new URLSearchParams({
    from: 'memory',
    date,
  });
  return `/journal/${journalId}?${params.toString()}`;
}

function normalizeAppreciationId(rawId: string) {
  const parsedId = Number.parseInt(rawId, 10);
  if (!Number.isSafeInteger(parsedId) || parsedId <= 0) {
    return null;
  }
  return parsedId;
}

function escapeAttributeValue(value: string) {
  return value.replace(/["\\]/g, '\\$&');
}

function buildJournalModel(item: TimelineJournalItem): TimelineMemoryModel {
  const mood = item.mood_label?.trim();
  const attachments = item.attachments ?? [];
  const attachCount = attachments.length || (item.attachment_count ?? 0);

  // Surface photo captions as detail lines
  const captionLines = attachments
    .filter((a) => a.caption?.trim())
    .map((a) => `\u{1F4F7} ${a.caption!.trim()}`);

  return {
    kind: 'journal',
    eyebrow: mood ? 'Journal Memory' : 'Journal Entry',
    title: mood ? `${mood} 的一天` : '一頁被留下的日記',
    description:
      item.content_preview?.trim() ||
      '那天的感受被簡短地留了下來，等你們下次回來時，再把那一刻慢慢讀完整。',
    dateLabel: formatDateLong(item.created_at),
    badges: [
      item.is_own ? '我寫下' : '伴侶寫下',
      ...(mood ? [mood] : []),
      ...(attachCount > 0 ? [`\u{1F4F7} ${attachCount} 張圖片`] : []),
    ],
    detailLines: captionLines,
    attachments,
    support: item.is_own
      ? '你把那天的心情留在了這裡。'
      : '對方把那天的心情留在了這裡。',
  };
}

function buildCardModel(item: TimelineCardItem): TimelineMemoryModel {
  const detailLines = [];

  if (item.my_answer?.trim()) {
    detailLines.push(`我：${item.my_answer.trim()}`);
  }
  if (item.partner_answer?.trim()) {
    detailLines.push(`伴侶：${item.partner_answer.trim()}`);
  }

  const participationLabel = detailLines.length === 2
    ? '雙方都回答了'
    : detailLines.length === 1
      ? item.my_answer?.trim()
        ? '我回答了'
        : '伴侶回答了'
      : '等待回答';

  return {
    kind: 'card',
    eyebrow: 'Conversation Memory',
    title: item.card_title,
    description: item.card_question,
    dateLabel: formatDateLong(item.revealed_at),
    badges: [item.category, participationLabel],
    detailLines,
    support: '這張牌不只是問答，它記住了你們當時怎麼看彼此。',
  };
}

function buildPhotoModel(item: TimelinePhotoItem): TimelineMemoryModel {
  return {
    kind: 'photo',
    eyebrow: 'Photo Memory',
    title: item.is_own ? '我留下的一張照片' : '伴侶留下的一張照片',
    description:
      item.caption?.trim() ||
      '照片把那時候的空氣安靜地留在這裡，即使沒有更多說明，也還是值得回來看。',
    dateLabel: formatDateLong(item.created_at),
    badges: [item.is_own ? '我留下' : '伴侶留下', '照片'],
    detailLines: [],
    support: '即使沒有更多說明，照片也會替當時的空氣作證。',
  };
}

function buildAppreciationModel(item: TimelineAppreciationItem): TimelineMemoryModel {
  return {
    kind: 'appreciation',
    eyebrow: 'Gratitude Memory',
    title: item.is_mine ? '我寫給伴侶的感謝' : '伴侶寫給我的感謝',
    description:
      item.body_text?.trim() ||
      '一段安靜的感謝，被留在了這裡。',
    dateLabel: formatDateLong(item.created_at),
    badges: [item.is_mine ? '我寫的' : '伴侶寫的', '感恩'],
    detailLines: [],
    support: item.is_mine
      ? '你把感謝放在了對方看得見的地方。'
      : '對方把感謝放在了你看得見的地方。',
  };
}

function buildTimelineModel(item: TimelineItem): TimelineMemoryModel {
  if (item.type === 'journal') {
    return buildJournalModel(item);
  }
  if (item.type === 'card') {
    return buildCardModel(item);
  }
  if (item.type === 'appreciation') {
    return buildAppreciationModel(item);
  }
  return buildPhotoModel(item);
}

function buildTimeCapsuleModel(memory: TimeCapsuleMemory): TimelineMemoryModel {
  const badges = [];

  if (memory.journals_count > 0) {
    badges.push(`${memory.journals_count} 則日記`);
  }
  if (memory.cards_count > 0) {
    badges.push(`${memory.cards_count} 次抽卡`);
  }
  if (memory.appreciations_count > 0) {
    badges.push(`${memory.appreciations_count} 則感恩`);
  }
  const isExactDay = memory.from_date === memory.to_date;
  return {
    kind: 'capsule',
    eyebrow: 'Time Capsule',
    title: isExactDay
      ? '一年前的今天，這一刻回來找你們。'
      : '一年前的這幾天，這些記憶回來找你們。',
    description:
      memory.summary_text?.trim() ||
      '這不是最新的一段，而是剛好在今天回頭敲門的一段記錄，提醒你們有些生活值得被重新打開。',
    dateLabel: memory.date,
    badges,
    detailLines: (memory.items ?? [])
      .filter((item) => item.preview_text?.trim())
      .slice(0, 3)
      .map((item) => {
        const icon = item.type === 'journal' ? '📖' : item.type === 'card' ? '🃏' : '💛';
        return `${icon} ${item.preview_text.trim()}`;
      }),
    support: '有些回憶不是最新的，卻最值得在對的時間重新被看見。',
  };
}

function buildEmptyFeaturedModel(): TimelineMemoryModel {
  return {
    kind: 'empty',
    eyebrow: 'Gallery Opening',
    title: '你們的回憶長廊，還在等第一個被留下的瞬間。',
    description:
      '當日記、卡片或照片開始累積，這裡就不再只是功能頁，而會慢慢長成一個值得一再回來看的共同生活畫廊。',
    dateLabel: '',
    badges: ['回憶會慢慢長出來'],
    detailLines: [],
    support: '現在的留白不是空白，而是還沒被寫下的生活。',
  };
}

function renderSourceState(
  eyebrow: string,
  title: string,
  description: string,
  action: ReactNode,
) {
  return (
    <MemoryStatePanel
      tone="error"
      eyebrow={eyebrow}
      title={title}
      description={description}
      action={action}
    />
  );
}

export default function MemoryPageContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [artifactDialog, setArtifactDialog] = useState<MemoryArtifactDialogState | null>(null);
  const {
    view,
    setView,
    items,
    hasMore,
    loadMore,
    timelineLoading,
    timelineFetching,
    timelineError,
    refetchTimeline,
    calendar,
    calendarMonth,
    prevMonth,
    nextMonth,
    calendarLoading,
    calendarError,
    refetchCalendar,
    timeCapsule,
    timeCapsuleLoading,
    timeCapsuleError,
    refetchTimeCapsule,
    report,
    reportLoading,
    reportError,
    refetchReport,
  } = useMemoryData();

  // Deep-link: /memory?date=YYYY-MM-DD&kind=card&id=... switches to calendar
  // view on that date and focuses the matching item.
  const deepLinkDate = searchParams.get('date');
  const focusKind = searchParams.get('kind');
  const focusId = searchParams.get('id');
  const shouldOpenFocusedArtifact = searchParams.get('open') === '1';
  const deepLinkedCalendarDate = useMemo(
    () => (deepLinkDate && DATE_ONLY_PATTERN.test(deepLinkDate) ? deepLinkDate : null),
    [deepLinkDate],
  );
  const [selectedCalendarDate, setSelectedCalendarDate] = useState<string | null>(deepLinkedCalendarDate);
  const dayRevealRef = useRef<HTMLDivElement>(null);
  const pendingRevealScrollDate = useRef<string | null>(null);
  const focusKey = useMemo(
    () =>
      deepLinkDate && focusKind && focusId
        ? `${deepLinkDate}:${focusKind}:${focusId}:${shouldOpenFocusedArtifact ? 'open' : 'focus'}`
        : null,
    [deepLinkDate, focusId, focusKind, shouldOpenFocusedArtifact],
  );
  useEffect(() => {
    if (deepLinkedCalendarDate) {
      setView('calendar');
    }
  }, [deepLinkedCalendarDate, setView]);
  useEffect(() => {
    setSelectedCalendarDate(deepLinkedCalendarDate);
  }, [deepLinkedCalendarDate]);

  const handleSelectCalendarDate = useCallback(
    (date: string) => {
      setSelectedCalendarDate(date);

      const params = new URLSearchParams(searchParams.toString());
      params.set('date', date);
      params.delete('kind');
      params.delete('id');
      params.delete('open');
      pendingRevealScrollDate.current = date;

      const nextQuery = params.toString();
      router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, {
        scroll: false,
      });
    },
    [pathname, router, searchParams],
  );

  const isFocusTarget = useCallback(
    (item: TimelineItem): boolean => {
      if (!focusKind || !focusId) return false;
      if (item.type === 'card') return focusKind === 'card' && item.session_id === focusId;
      return item.type === focusKind && item.id === focusId;
    },
    [focusKind, focusId],
  );

  const focusRef = useRef<HTMLDivElement>(null);
  const hasScrolledToFocus = useRef(false);
  const hasOpenedFocusedArtifact = useRef(false);
  useEffect(() => {
    hasScrolledToFocus.current = false;
    hasOpenedFocusedArtifact.current = false;
  }, [focusKey]);

  const featuredTimelineItem = items[0] ?? null;
  const companionItems = items.slice(1, 3);
  const streamItems = items.slice(3);
  const loadedJournalCount = items.filter((item) => item.type === 'journal').length;
  const loadedCardCount = items.filter((item) => item.type === 'card').length;
  const loadedPhotoCount = items.filter((item) => item.type === 'photo').length;
  const calendarActiveDays =
    calendar?.days.filter((day) => day.journal_count > 0 || day.card_count > 0 || day.appreciation_count > 0 || day.has_photo).length ?? 0;
  const calendarJournalDays = calendar?.days.filter((day) => day.journal_count > 0).length ?? 0;
  const calendarCardDays = calendar?.days.filter((day) => day.card_count > 0).length ?? 0;
  const calendarAppreciationDays = calendar?.days.filter((day) => day.appreciation_count > 0).length ?? 0;
  const calendarPhotoDays = calendar?.days.filter((day) => day.has_photo).length ?? 0;
  const timeCapsuleMemory = timeCapsule?.available ? timeCapsule.memory : null;
  const timeCapsuleAvailable = Boolean(timeCapsuleMemory);
  const featuredFeedModel = featuredTimelineItem ? buildTimelineModel(featuredTimelineItem) : null;
  const featuredMemoryChamber =
    timeCapsuleMemory
      ? buildTimeCapsuleModel(timeCapsuleMemory)
      : featuredTimelineItem
        ? buildTimelineModel(featuredTimelineItem)
        : buildEmptyFeaturedModel();
  const coverUsesTimelineLead = !timeCapsuleAvailable && featuredFeedModel !== null;
  const reportTopics = report?.top_topics.filter(Boolean).slice(0, 4) ?? [];
  const feedLoadingMore = timelineFetching && !timelineLoading;
  const activeCalendarDates = useMemo(
    () =>
      (calendar?.days ?? [])
        .filter((day) => day.journal_count > 0 || day.card_count > 0 || day.appreciation_count > 0 || day.has_photo)
        .map((day) => day.date)
        .sort(),
    [calendar],
  );
  const latestActiveCalendarDate = activeCalendarDates.at(-1) ?? null;
  const activeSelectedCalendarDate =
    selectedCalendarDate && activeCalendarDates.includes(selectedCalendarDate)
      ? selectedCalendarDate
      : latestActiveCalendarDate;
  const selectedDayQuery = useQuery({
    queryKey: ['memory', 'timeline', 'day-spotlight', activeSelectedCalendarDate],
    queryFn: () =>
      memoryService.getTimeline({
        limit: MEMORY_DAY_TIMELINE_LIMIT,
        from_date: activeSelectedCalendarDate ?? undefined,
        to_date: activeSelectedCalendarDate ?? undefined,
        tz_offset_minutes: new Date().getTimezoneOffset(),
      }),
    enabled: view === 'calendar' && Boolean(activeSelectedCalendarDate),
    staleTime: MEMORY_DAY_STALE_TIME_MS,
  });
  const selectedDayItems = useMemo(() => selectedDayQuery.data?.items ?? [], [selectedDayQuery.data?.items]);
  const selectedDayRevealModel = useMemo(
    () =>
      buildMemoryDayRevealModel({
        date: activeSelectedCalendarDate,
        items: selectedDayItems,
      }),
    [activeSelectedCalendarDate, selectedDayItems],
  );
  const selectedDayItemByRevealKey = useMemo(() => {
    const map = new Map<string, TimelineItem>();
    for (const item of selectedDayItems) {
      map.set(getMemoryDayRevealArtifactKey(item), item);
    }
    return map;
  }, [selectedDayItems]);
  const hasFocusedDayItem = useMemo(
    () => Boolean(focusKey) && selectedDayItems.some((item) => isFocusTarget(item)),
    [focusKey, isFocusTarget, selectedDayItems],
  );
  const selectedDayFeaturedModel = selectedDayItems[0] ? buildTimelineModel(selectedDayItems[0]) : null;
  const selectedDayStreamItems = selectedDayItems.slice(1);
  const cardArtifactQuery = useQuery<DeckHistoryEntry>({
    queryKey: ['memory', 'artifact', 'card', artifactDialog?.kind === 'card' ? artifactDialog.sessionId : null],
    queryFn: () => fetchDeckHistoryEntry(artifactDialog?.kind === 'card' ? artifactDialog.sessionId : ''),
    enabled: artifactDialog?.kind === 'card',
    staleTime: MEMORY_DAY_STALE_TIME_MS,
  });
  const appreciationArtifactQuery = useQuery<AppreciationPublic>({
    queryKey: ['memory', 'artifact', 'appreciation', artifactDialog?.kind === 'appreciation' ? artifactDialog.appreciationId : null],
    queryFn: () => fetchAppreciationById(artifactDialog?.kind === 'appreciation' ? artifactDialog.appreciationId ?? -1 : -1),
    enabled: artifactDialog?.kind === 'appreciation' && artifactDialog.appreciationId !== null,
    staleTime: MEMORY_DAY_STALE_TIME_MS,
  });

  const handleOpenJournalArtifact = useCallback(
    (journalId: string, date: string) => {
      router.push(buildJournalHref(journalId, date));
    },
    [router],
  );

  const handleOpenCardArtifact = useCallback((item: TimelineCardItem, date: string) => {
    setArtifactDialog({
      kind: 'card',
      sessionId: item.session_id,
      date,
      previewTitle: item.card_title,
    });
  }, []);

  const handleOpenAppreciationArtifact = useCallback((item: TimelineAppreciationItem, date: string) => {
    setArtifactDialog({
      kind: 'appreciation',
      appreciationId: normalizeAppreciationId(item.id),
      date,
      previewTitle: item.is_mine ? '我寫給伴侶的感謝' : '伴侶寫給我的感謝',
      isMine: item.is_mine,
    });
  }, []);

  const handleJumpToDayArtifact = useCallback((artifactKey: string) => {
    const target = document.querySelector(
      `[data-memory-artifact-key="${escapeAttributeValue(artifactKey)}"]`,
    );
    target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, []);

  const handleOpenDayRevealArtifact = useCallback(
    (artifactKey: string) => {
      if (!activeSelectedCalendarDate) return;
      const item = selectedDayItemByRevealKey.get(artifactKey);
      if (!item) return;

      if (item.type === 'journal') {
        handleOpenJournalArtifact(item.id, activeSelectedCalendarDate);
      } else if (item.type === 'card') {
        handleOpenCardArtifact(item, activeSelectedCalendarDate);
      } else if (item.type === 'appreciation') {
        handleOpenAppreciationArtifact(item, activeSelectedCalendarDate);
      } else {
        handleJumpToDayArtifact(artifactKey);
      }
    },
    [
      activeSelectedCalendarDate,
      handleJumpToDayArtifact,
      handleOpenAppreciationArtifact,
      handleOpenCardArtifact,
      handleOpenJournalArtifact,
      selectedDayItemByRevealKey,
    ],
  );

  const buildDaySpotlightAction = useCallback(
    (item: TimelineItem) => {
      if (!activeSelectedCalendarDate) {
        return null;
      }

      if (item.type === 'journal') {
        return (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleOpenJournalArtifact(item.id, activeSelectedCalendarDate)}
          >
            打開完整日記
          </Button>
        );
      }

      if (item.type === 'card') {
        return (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleOpenCardArtifact(item, activeSelectedCalendarDate)}
          >
            打開完整卡片對話
          </Button>
        );
      }

      if (item.type === 'appreciation') {
        return (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleOpenAppreciationArtifact(item, activeSelectedCalendarDate)}
          >
            打開完整感謝
          </Button>
        );
      }

      return null;
    },
    [activeSelectedCalendarDate, handleOpenAppreciationArtifact, handleOpenCardArtifact, handleOpenJournalArtifact],
  );

  useEffect(() => {
    if (!focusKey || view !== 'calendar' || !hasFocusedDayItem || !focusRef.current || hasScrolledToFocus.current) {
      return;
    }

    hasScrolledToFocus.current = true;
    // Small delay to let the day spotlight section render fully.
    const timer = window.setTimeout(() => {
      focusRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 400);
    return () => window.clearTimeout(timer);
  }, [focusKey, hasFocusedDayItem, view]);
  useEffect(() => {
    if (
      view !== 'calendar' ||
      selectedDayQuery.isLoading ||
      !activeSelectedCalendarDate ||
      pendingRevealScrollDate.current !== activeSelectedCalendarDate ||
      !dayRevealRef.current
    ) {
      return;
    }

    pendingRevealScrollDate.current = null;
    const timer = window.setTimeout(() => {
      dayRevealRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 120);
    return () => window.clearTimeout(timer);
  }, [activeSelectedCalendarDate, selectedDayQuery.isLoading, view]);

  useEffect(() => {
    if (
      !shouldOpenFocusedArtifact ||
      !focusKey ||
      !activeSelectedCalendarDate ||
      view !== 'calendar' ||
      hasOpenedFocusedArtifact.current
    ) {
      return;
    }

    const focusItem = selectedDayItems.find((item) => isFocusTarget(item));
    if (!focusItem) return;

    if (focusItem.type === 'appreciation') {
      hasOpenedFocusedArtifact.current = true;
      handleOpenAppreciationArtifact(focusItem, activeSelectedCalendarDate);
    } else if (focusItem.type === 'card') {
      hasOpenedFocusedArtifact.current = true;
      handleOpenCardArtifact(focusItem, activeSelectedCalendarDate);
    }
  }, [
    activeSelectedCalendarDate,
    focusKey,
    handleOpenAppreciationArtifact,
    handleOpenCardArtifact,
    isFocusTarget,
    selectedDayItems,
    shouldOpenFocusedArtifact,
    view,
  ]);
  useEffect(() => {
    if (shouldOpenFocusedArtifact && focusKey) return;
    setArtifactDialog(null);
  }, [activeSelectedCalendarDate, focusKey, shouldOpenFocusedArtifact]);
  useEffect(() => {
    if (view !== 'calendar') {
      setArtifactDialog(null);
    }
  }, [view]);
  const initialPageLoading =
    items.length === 0 && timelineLoading && timeCapsuleLoading && reportLoading;

  const artifactDialogTitle =
    artifactDialog?.kind === 'card'
      ? '完整卡片對話'
      : artifactDialog?.kind === 'appreciation'
        ? '完整感謝'
        : '';
  const artifactDialogEyebrow =
    artifactDialog?.kind === 'card'
      ? 'Card Archive'
      : artifactDialog?.kind === 'appreciation'
        ? 'Gratitude Archive'
        : '';
  const artifactDialogDescription =
    artifactDialog?.kind === 'card'
      ? `把 ${formatDateLong(artifactDialog.date)} 的卡片真正打開來看，不只看摘要。`
      : artifactDialog?.kind === 'appreciation'
        ? `把 ${formatDateLong(artifactDialog.date)} 留下的感謝完整讀完。`
        : '';

  if (initialPageLoading) {
    return <MemorySkeleton />;
  }

  return (
    <div className="space-y-[clamp(1.5rem,3vw,2.75rem)]">
      <MemoryCover
        eyebrow="Memory / Shared Archive"
        title="把你們一起活過的日子，放進一個值得慢慢回來、重新看見、重新被觸動的回憶畫廊。"
        description="這裡不是檔案庫，也不只是把內容排好。它是 Haven 的完整 Shared Archive；Relationship System 的 Story 只會從這裡挑出真正值得回來重看的故事錨點，而更完整的生活輪廓仍保留在這條長廊裡。"
        pulse={
          timeCapsuleAvailable
            ? '今天最珍貴的那一段，不一定是最新的，而是剛好回來敲門的那一段。'
            : featuredTimelineItem
              ? '當回憶被留在這裡，它就不只屬於那一天，也屬於未來某次你們重新回來看的時刻。'
              : '現在還很安靜也沒關係。真正值得回來看的長廊，總是從第一個被留下的瞬間開始。'
        }
        highlights={
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-[1.7rem] border border-white/54 bg-white/74 px-4 py-4 shadow-soft backdrop-blur-md">
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Gift className="h-4 w-4" aria-hidden />
                </span>
                <div className="space-y-1">
                  <p className="type-micro uppercase text-primary/80">Time Capsule</p>
                  <p className="text-xl font-semibold text-card-foreground">
                    {timeCapsuleMemory ? timeCapsuleMemory.date : '等待回來'}
                  </p>
                  <p className="type-caption text-muted-foreground">
                    {timeCapsuleMemory && timeCapsuleMemory.from_date !== timeCapsuleMemory.to_date
                      ? '一年前的這段時間，回來找你們了。'
                      : '一年前的今天，會在對的時間重新回來。'}
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-[1.7rem] border border-white/54 bg-white/74 px-4 py-4 shadow-soft backdrop-blur-md">
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Clock3 className="h-4 w-4" aria-hidden />
                </span>
                <div className="space-y-1">
                  <p className="type-micro uppercase text-primary/80">目前展開</p>
                  <p className="text-xl font-semibold text-card-foreground">{items.length} 段片段</p>
                  <p className="type-caption text-muted-foreground">
                    不是全部人生，只是這次被重新翻開的部分。
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-[1.7rem] border border-white/54 bg-white/74 px-4 py-4 shadow-soft backdrop-blur-md">
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <CalendarDays className="h-4 w-4" aria-hidden />
                </span>
                <div className="space-y-1">
                  <p className="type-micro uppercase text-primary/80">最近一段</p>
                  <p className="text-xl font-semibold text-card-foreground">
                    {featuredTimelineItem
                      ? formatDateShort(
                          featuredTimelineItem.type === 'card'
                            ? featuredTimelineItem.revealed_at
                            : featuredTimelineItem.created_at,
                        )
                      : '還沒開始'}
                  </p>
                  <p className="type-caption text-muted-foreground">
                    每一段被留下的日子，都會讓這裡更值得回來。
                  </p>
                </div>
              </div>
            </div>
          </div>
        }
        featured={
          <MemoryFeaturedMemoryCard
            kind={featuredMemoryChamber.kind}
            eyebrow={featuredMemoryChamber.eyebrow}
            title={featuredMemoryChamber.title}
            description={featuredMemoryChamber.description}
            dateLabel={featuredMemoryChamber.dateLabel || undefined}
            badges={featuredMemoryChamber.badges}
            detailLines={featuredMemoryChamber.detailLines}
            support={featuredMemoryChamber.support}
            attachments={featuredMemoryChamber.attachments}
          />
        }
        aside={
          <>
            <MemoryOverviewCard
              eyebrow="Shared Archive Overview"
              title="這次回來，哪些片段正在被重新翻開。"
              description="想看更完整的 Shared Archive，就留在 Memory；想回到被整理過的故事層與關係脈動，則回到 Relationship System。"
            >
              <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                <div className="rounded-[1.7rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/80">日記</p>
                  <p className="mt-2 text-2xl font-semibold text-card-foreground">{loadedJournalCount}</p>
                </div>
                <div className="rounded-[1.7rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/80">卡片</p>
                  <p className="mt-2 text-2xl font-semibold text-card-foreground">{loadedCardCount}</p>
                </div>
                <div className="rounded-[1.7rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/80">照片</p>
                  <p className="mt-2 text-2xl font-semibold text-card-foreground">{loadedPhotoCount}</p>
                </div>
              </div>
            </MemoryOverviewCard>

            {reportError ? (
              <MemoryStatePanel
                tone="error"
                eyebrow="Relationship Reflection"
                title="這次沒有順利帶回關係回看。"
                description="週報本來應該替這段時間留下一點整理過的回聲。現在先重試一次，讓這張回看重新回來。"
                action={
                  <Button variant="secondary" onClick={() => void refetchReport()}>
                    重新載入回看
                  </Button>
                }
              />
            ) : (
              <MemoryOverviewCard
                eyebrow="Relationship Reflection"
                title={report ? '這段時間，你們的關係留下了什麼回聲。' : '回看會在累積之後慢慢出現。'}
                description={
                  report?.emotion_trend_summary ||
                  '當這裡累積更多回憶，系統會把這段時間的情緒與主題整理成一段更可回看的反思。'
                }
              >
                {reportLoading ? (
                  <div className="space-y-3">
                    <div className="h-5 w-full animate-pulse rounded-full bg-muted" aria-hidden />
                    <div className="h-5 w-5/6 animate-pulse rounded-full bg-muted" aria-hidden />
                    <div className="h-20 animate-pulse rounded-[1.7rem] bg-white/74 shadow-soft" aria-hidden />
                  </div>
                ) : report ? (
                  <div className="space-y-4">
                    {reportTopics.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {reportTopics.map((topic) => (
                          <Badge
                            key={topic}
                            variant="metadata"
                            size="sm"
                            className="border-white/56 bg-white/72"
                          >
                            {topic}
                          </Badge>
                        ))}
                      </div>
                    ) : null}

                    {report.health_suggestion ? (
                      <div className="rounded-[1.8rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                        <p className="type-body-muted text-card-foreground">{report.health_suggestion}</p>
                      </div>
                    ) : null}

                    <p className="type-caption text-muted-foreground">
                      {report.from_date}～{report.to_date} · 生成於 {formatGeneratedLabel(report.generated_at)}
                    </p>
                  </div>
                ) : (
                  <div className="rounded-[1.8rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                    <p className="type-body-muted text-card-foreground">
                      持續留下日記、卡片與照片後，這裡會開始替你們整理出一段更完整的關係回看。
                    </p>
                  </div>
                )}
              </MemoryOverviewCard>
            )}
          </>
        }
      />

      {timeCapsuleError
        ? renderSourceState(
            'Time Capsule unavailable',
            '時光膠囊這次沒有順利帶回來。',
            '一年前的今天還在，只是這次沒有順利被載入。你可以再試一次，讓那段回來找你們的記錄重新出現。',
            <Button variant="secondary" onClick={() => void refetchTimeCapsule()}>
              重新載入時光膠囊
            </Button>,
          )
        : null}

      <MemoryModeRail
        items={[
          {
            key: 'feed',
            label: 'Memory Reel',
            description: '沿著時間慢慢往回走，看見每一段被留下的片段。',
            meta: items.length > 0 ? `目前展開 ${items.length} 段記錄` : '先從流動的回憶開始',
            active: view === 'feed',
            onClick: () => setView('feed'),
          },
          {
            key: 'calendar',
            label: 'Memory Atlas',
            description: '從月份與日期回看你們在哪些日子留下了痕跡。',
            meta: calendar ? `${calendarActiveDays} 個有痕跡的日子` : '切換後會展開月份視角',
            active: view === 'calendar',
            onClick: () => setView('calendar'),
          },
        ]}
      />

      {view === 'feed' ? (
        <section className="space-y-6">
          <div className="space-y-3 px-1">
            <Badge
              variant="metadata"
              size="sm"
              className="border-white/56 bg-white/72 text-primary/80 shadow-soft"
            >
              Chronological Reel
            </Badge>
            <div className="space-y-2">
              <h2 className="type-h2 text-card-foreground">沿著時間流回去，再看一次你們怎麼活成今天。</h2>
              <p className="max-w-3xl type-body-muted text-muted-foreground">
                {coverUsesTimelineLead
                  ? '這次回看的主記憶已經在上方先被展開，下面這些片段則把那段生活繼續往後接上。這不是內容流，而是一條值得慢慢走的共同生活長廊。'
                  : '先把最上面的一段放大成主角，再讓其他回憶安靜地排在後面。這不是內容流，而是一條值得慢慢走的共同生活長廊。'}
              </p>
            </div>
          </div>

          {timelineError
            ? renderSourceState(
                'Feed unavailable',
                '這條回憶流暫時沒有順利展開。',
                '已經留下的片段沒有消失，只是這次沒有順利被帶回畫面。你可以再試一次，讓它們重新排回這條長廊裡。',
                <Button variant="secondary" onClick={() => void refetchTimeline()}>
                  重新載入回憶流
                </Button>,
              )
            : null}

          {!timelineError && timelineLoading && items.length === 0 ? (
            <div className="space-y-4" aria-busy="true" aria-live="polite">
              <GlassCard className="rounded-[2.95rem] border-white/52 bg-white/76 shadow-soft">
                <div className="h-[26rem]" aria-hidden />
              </GlassCard>
              <div className="grid gap-4 lg:grid-cols-2">
                <GlassCard className="rounded-[2.3rem] border-white/52 bg-white/76 shadow-soft">
                  <div className="h-72" aria-hidden />
                </GlassCard>
                <GlassCard className="rounded-[2.3rem] border-white/52 bg-white/76 shadow-soft">
                  <div className="h-72" aria-hidden />
                </GlassCard>
              </div>
              <div className="grid gap-4">
                {Array.from({ length: 3 }).map((_, index) => (
                  <GlassCard
                    key={index}
                    className="h-44 rounded-[2rem] border-white/52 bg-white/76 shadow-soft"
                  >
                    <div className="h-44" aria-hidden />
                  </GlassCard>
                ))}
              </div>
            </div>
          ) : null}

          {!timelineError && !timelineLoading && items.length === 0 ? (
            <MemoryStatePanel
              tone="quiet"
              eyebrow="Your gallery is waiting"
              title="這條回憶長廊還沒有開始掛上任何片段。"
              description="當你們寫下日記、一起抽卡或留下照片，這裡就會慢慢變成一個值得一再回來看的共同生活畫廊。"
            />
          ) : null}

          {!timelineError && items.length > 0 ? (
            <>
              {featuredFeedModel && !coverUsesTimelineLead ? (
                <MemoryFeaturedMemoryCard
                  kind={featuredFeedModel.kind}
                  eyebrow={featuredFeedModel.eyebrow}
                  title={featuredFeedModel.title}
                  description={featuredFeedModel.description}
                  dateLabel={featuredFeedModel.dateLabel}
                  badges={featuredFeedModel.badges}
                  detailLines={featuredFeedModel.detailLines}
                  support={featuredFeedModel.support}
                  attachments={featuredFeedModel.attachments}
                />
              ) : null}

              {companionItems.length > 0 ? (
                <div className="space-y-4">
                  <div className="space-y-2 px-1">
                    <p className="type-micro uppercase text-primary/80">Companion Memories</p>
                    <h3 className="type-h3 text-card-foreground">
                      {coverUsesTimelineLead ? '從上面那段主記憶往後，這幾段讓回看繼續延伸。' : '接在後面的幾段，讓這次回看更完整。'}
                    </h3>
                  </div>
                  <div className="grid gap-4 lg:grid-cols-2">
                    {companionItems.map((item) => {
                      const model = buildTimelineModel(item);
                      return (
                        <MemoryCompanionMemoryCard
                          key={item.type === 'card' ? `card-${item.session_id}` : `${item.type}-${item.id}`}
                          kind={model.kind}
                          eyebrow={model.eyebrow}
                          title={model.title}
                          description={model.description}
                          dateLabel={model.dateLabel}
                          badges={model.badges}
                          detailLines={model.detailLines}
                          support={model.support}
                          attachments={model.attachments}
                        />
                      );
                    })}
                  </div>
                </div>
              ) : null}

              {streamItems.length > 0 ? (
                <div className="space-y-4">
                  <div className="space-y-2 px-1">
                    <p className="type-micro uppercase text-primary/80">Quiet Stream</p>
                    <h3 className="type-h3 text-card-foreground">其餘的片段，沿著時間安靜地排在後面。</h3>
                  </div>
                  <div className="grid gap-4">
                    {streamItems.map((item) => {
                      const model = buildTimelineModel(item);
                      return (
                        <MemoryStreamMemoryCard
                          key={item.type === 'card' ? `card-${item.session_id}` : `${item.type}-${item.id}`}
                          kind={model.kind}
                          eyebrow={model.eyebrow}
                          title={model.title}
                          description={model.description}
                          dateLabel={model.dateLabel}
                          badges={model.badges}
                          detailLines={model.detailLines}
                          support={model.support}
                          attachments={model.attachments}
                        />
                      );
                    })}
                  </div>
                </div>
              ) : null}

              {coverUsesTimelineLead && items.length === 1 ? (
                <MemoryStatePanel
                  tone="quiet"
                  eyebrow="The gallery keeps going"
                  title="這次回看的主記憶已經在上方展開。"
                  description="當下一段日記、卡片或照片被留下，這條長廊就會繼續往下延伸。現在先讓這一段好好留在中央。"
                />
              ) : null}

              {hasMore ? (
                <div className="flex justify-center pt-2">
                  <Button
                    size="lg"
                    loading={feedLoadingMore}
                    onClick={loadMore}
                    aria-label="載入更多回憶"
                  >
                    載入更多回憶
                  </Button>
                </div>
              ) : null}
            </>
          ) : null}
        </section>
      ) : (
        <section className="space-y-6">
          <div className="space-y-3 px-1">
            <Badge
              variant="metadata"
              size="sm"
              className="border-white/56 bg-white/72 text-primary/80 shadow-soft"
            >
              Calendar Atlas
            </Badge>
            <div className="space-y-2">
              <h2 className="type-h2 text-card-foreground">從月份與日期，重走那些你們曾經留下痕跡的日子。</h2>
              <p className="max-w-3xl type-body-muted text-muted-foreground">
                不是每一天都需要被放大成故事。有些時候，只要看見哪些日子發亮，就足夠想起你們曾經怎麼一起走過。
              </p>
            </div>
          </div>

          {calendarError
            ? renderSourceState(
                'Calendar unavailable',
                '這張月份地圖暫時沒有順利展開。',
                '日期沒有消失，只是這次沒有被順利排回月曆裡。你可以再試一次，讓這張回憶地圖重新攤開。',
                <Button variant="secondary" onClick={() => void refetchCalendar()}>
                  重新載入月份地圖
                </Button>,
              )
            : null}

          {!calendarError ? (
            <div className="space-y-6">
              <MemoryCalendarAtlas
                calendar={calendar}
                year={calendarMonth.year}
                month={calendarMonth.month}
                loading={calendarLoading}
                summary={{
                  activeDays: calendarActiveDays,
                  journalDays: calendarJournalDays,
                  cardDays: calendarCardDays,
                  appreciationDays: calendarAppreciationDays,
                  photoDays: calendarPhotoDays,
                }}
                selectedDate={activeSelectedCalendarDate}
                onSelectDate={handleSelectCalendarDate}
                onPrevMonth={prevMonth}
                onNextMonth={nextMonth}
              />

              {!calendarLoading && !activeSelectedCalendarDate ? (
                <MemoryStatePanel
                  tone="quiet"
                  eyebrow="Choose a day"
                  title="這個月份還沒有哪一天被展開。"
                  description="當月曆上有被點亮的日子時，點一下它，這裡就會把那一天留下的片段攤開來。"
                />
              ) : null}

              {activeSelectedCalendarDate ? (
                <div className="space-y-4">
                  <div className="space-y-2 px-1">
                    <Badge
                      variant="metadata"
                      size="sm"
                      className="border-white/56 bg-white/72 text-primary/80 shadow-soft"
                    >
                      Day Spotlight
                    </Badge>
                    <div className="space-y-2">
                      <h3 className="type-h3 text-card-foreground">{formatDateLong(activeSelectedCalendarDate)}</h3>
                      <p className="max-w-3xl type-body-muted text-muted-foreground">
                        把月份裡的一天打開來看，不只是知道那天有痕跡，而是真的看見那天留下了什麼。
                      </p>
                    </div>
                  </div>

                  {selectedDayQuery.isLoading ? (
                    <div className="space-y-4" aria-busy="true" aria-live="polite">
                      <GlassCard className="rounded-[2.55rem] border-white/52 bg-white/76 shadow-soft">
                        <div className="h-[18rem]" aria-hidden />
                      </GlassCard>
                      <GlassCard className="rounded-[2rem] border-white/52 bg-white/76 shadow-soft">
                        <div className="h-40" aria-hidden />
                      </GlassCard>
                    </div>
                  ) : null}

                  {selectedDayQuery.isError ? (
                    <MemoryStatePanel
                      tone="error"
                      eyebrow="Day Spotlight unavailable"
                      title="這一天的回憶沒有順利展開。"
                      description="月曆知道這一天亮過，但明細這次沒有順利帶回。你可以再試一次，把這一天重新攤開。"
                      action={
                        <Button variant="secondary" onClick={() => void selectedDayQuery.refetch()}>
                          重新載入這一天
                        </Button>
                      }
                    />
                  ) : null}

                  {!selectedDayQuery.isLoading && !selectedDayQuery.isError && selectedDayItems.length > 0 ? (
                    <>
                      <div ref={dayRevealRef} tabIndex={-1}>
                        <MemoryDayRevealSummary
                          model={selectedDayRevealModel}
                          onOpenArtifact={handleOpenDayRevealArtifact}
                          onJumpToArtifact={handleJumpToDayArtifact}
                        />
                      </div>

                      {selectedDayFeaturedModel && selectedDayItems[0] ? (() => {
                        const featuredFocused = isFocusTarget(selectedDayItems[0]);
                        const featuredKey = getMemoryDayRevealArtifactKey(selectedDayItems[0]);
                        const card = (
                          <MemoryFeaturedMemoryCard
                            kind={selectedDayFeaturedModel.kind}
                            eyebrow={selectedDayFeaturedModel.eyebrow}
                            title={selectedDayFeaturedModel.title}
                            description={selectedDayFeaturedModel.description}
                            dateLabel={selectedDayFeaturedModel.dateLabel}
                            badges={selectedDayFeaturedModel.badges}
                            detailLines={selectedDayFeaturedModel.detailLines}
                            support={selectedDayFeaturedModel.support}
                            attachments={selectedDayFeaturedModel.attachments}
                            focused={featuredFocused}
                            footer={buildDaySpotlightAction(selectedDayItems[0])}
                          />
                        );
                        return (
                          <div
                            data-memory-artifact-key={featuredKey}
                            ref={featuredFocused ? focusRef : undefined}
                          >
                            {card}
                          </div>
                        );
                      })() : null}

                      {selectedDayStreamItems.length > 0 ? (
                        <div className="grid gap-4">
                          {selectedDayStreamItems.map((item) => {
                            const model = buildTimelineModel(item);
                            const itemFocused = isFocusTarget(item);
                            const itemKey = item.type === 'card' ? `day-card-${item.session_id}` : `day-${item.type}-${item.id}`;
                            const artifactKey = getMemoryDayRevealArtifactKey(item);
                            const card = (
                              <MemoryStreamMemoryCard
                                kind={model.kind}
                                eyebrow={model.eyebrow}
                                title={model.title}
                                description={model.description}
                                dateLabel={model.dateLabel}
                                badges={model.badges}
                                detailLines={model.detailLines}
                                support={model.support}
                                attachments={model.attachments}
                                focused={itemFocused}
                                footer={buildDaySpotlightAction(item)}
                              />
                            );
                            return (
                              <div
                                key={itemKey}
                                data-memory-artifact-key={artifactKey}
                                ref={itemFocused ? focusRef : undefined}
                              >
                                {card}
                              </div>
                            );
                          })}
                        </div>
                      ) : null}
                    </>
                  ) : null}

                  {!selectedDayQuery.isLoading && !selectedDayQuery.isError && selectedDayItems.length === 0 ? (
                    <MemoryStatePanel
                      tone="quiet"
                      eyebrow="No returned fragments"
                      title="這一天目前沒有可展開的細節。"
                      description="月曆知道這一天曾經被點亮，但這次沒有帶回更多片段。你可以換一天看看，或稍後再回來。"
                    />
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}
        </section>
      )}

      <MemoryArtifactDialog
        open={artifactDialog !== null}
        onOpenChange={(open) => {
          if (!open) {
            setArtifactDialog(null);
          }
        }}
        eyebrow={artifactDialogEyebrow}
        title={artifactDialogTitle}
        description={artifactDialogDescription}
      >
        {artifactDialog?.kind === 'card' ? (
          cardArtifactQuery.isLoading ? (
            <GlassCard className="rounded-[2rem] border-white/56 bg-white/76 shadow-soft">
              <div className="h-72" aria-hidden />
            </GlassCard>
          ) : cardArtifactQuery.isError ? (
            <MemoryStatePanel
              tone="error"
              eyebrow="Card artifact unavailable"
              title="這張卡片對話這次沒有順利打開。"
              description="Day Spotlight 已經帶你回到正確的那一天，但這份完整對話這次沒有順利帶回。你可以再試一次。"
              action={
                <Button variant="secondary" onClick={() => void cardArtifactQuery.refetch()}>
                  重新載入完整卡片
                </Button>
              }
            />
          ) : cardArtifactQuery.data ? (
            <DeckArchiveCard entry={cardArtifactQuery.data} />
          ) : (
            <MemoryStatePanel
              tone="quiet"
              eyebrow="Card artifact unavailable"
              title="這張卡片暫時沒有完整內容。"
              description="目前沒有找到這次卡片揭曉的完整內容。你可以回到 Memory 換一個片段看看。"
            />
          )
        ) : null}

        {artifactDialog?.kind === 'appreciation' ? (
          artifactDialog.appreciationId === null ? (
            <MemoryStatePanel
              tone="error"
              eyebrow="Appreciation artifact unavailable"
              title="這段感謝的編號這次沒有順利對上。"
              description="這個 Day Spotlight 片段有內容，但完整感謝的識別資料不完整，所以 Haven 不會冒險打開錯的內容。"
            />
          ) : appreciationArtifactQuery.isLoading ? (
            <GlassCard className="rounded-[2rem] border-white/56 bg-white/76 shadow-soft">
              <div className="h-56" aria-hidden />
            </GlassCard>
          ) : appreciationArtifactQuery.isError ? (
            <MemoryStatePanel
              tone="error"
              eyebrow="Appreciation artifact unavailable"
              title="這段感謝這次沒有順利打開。"
              description="Day Spotlight 已經帶你回到正確的那一天，但完整感謝內容這次沒有順利帶回。你可以再試一次。"
              action={
                <Button variant="secondary" onClick={() => void appreciationArtifactQuery.refetch()}>
                  重新載入完整感謝
                </Button>
              }
            />
          ) : appreciationArtifactQuery.data ? (
            <GlassCard className="rounded-[2.15rem] border-white/56 bg-[linear-gradient(165deg,rgba(255,249,250,0.95),rgba(244,230,234,0.92))] p-6 shadow-soft">
              <div className="space-y-5">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="default" size="sm">
                    {appreciationArtifactQuery.data.is_mine ? '我寫的' : '伴侶寫的'}
                  </Badge>
                  <Badge variant="metadata" size="sm" className="border-white/56 bg-white/72">
                    {formatGeneratedLabel(appreciationArtifactQuery.data.created_at)}
                  </Badge>
                </div>
                <div className="rounded-[1.8rem] border border-white/56 bg-white/74 p-5 shadow-soft">
                  <p className="type-body whitespace-pre-wrap leading-7 text-card-foreground">
                    {appreciationArtifactQuery.data.body_text}
                  </p>
                </div>
                <p className="type-caption leading-6 text-card-foreground/76">
                  {artifactDialog.isMine
                    ? '這是你當時主動留下的一段感謝。'
                    : '這是對方當時留給你的一段感謝。'}
                </p>
              </div>
            </GlassCard>
          ) : (
            <MemoryStatePanel
              tone="quiet"
              eyebrow="Appreciation artifact unavailable"
              title="這段感謝暫時沒有完整內容。"
              description="目前沒有找到這則感謝的完整版本。你可以回到 Memory 換一個片段看看。"
            />
          )
        ) : null}
      </MemoryArtifactDialog>

    </div>
  );
}
