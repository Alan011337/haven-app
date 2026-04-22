'use client';

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Save,
  Sparkles,
} from 'lucide-react';
import Button from '@/components/ui/Button';
import { useConfirm } from '@/hooks/useConfirm';
import {
  useCreateJournal,
  useDeleteJournal,
  useDeleteJournalAttachment,
  useJournalDetail,
  useJournals,
  useUpdateJournal,
  useUploadJournalAttachment,
} from '@/hooks/queries';
import { sortJournalsDesc } from '@/features/home/home-data-utils';
import { useToast } from '@/hooks/useToast';
import type {
  JournalAttachmentPublic,
  JournalTranslationStatus,
  JournalVisibility,
} from '@/types';
import { queryKeys } from '@/lib/query-keys';
import { deriveJournalTitle } from '@/lib/journal-format';
import { logClientError } from '@/lib/safe-error-log';
import { MAX_JOURNAL_CONTENT_LENGTH, updateJournalAttachmentCaption } from '@/services/api-client';
import {
  JournalAssetTray,
  JournalBackLink,
  JournalCanvasFrame,
  JournalDocumentMap,
  JournalLibraryCard,
  JournalMobileDock,
  JournalMobileSheet,
  JournalModeToggle,
  JournalPartnerVisibilityPanel,
  JournalReadSurface,
  JournalRereadingGuide,
  JournalSavePill,
  JournalStatePanel,
  JournalStudioHero,
  JournalTranslationStatusCard,
  JournalTranslationStatusChip,
  JournalVisibilitySwitch,
  type JournalReflectionSectionStarter,
  type JournalSaveState,
  type JournalStudioMode,
} from '@/app/journal/JournalPrimitives';
import { buildJournalSharingDeliveryPresentation } from '@/app/journal/journal-sharing-delivery';
import { buildJournalTranslationStatusPresentation } from '@/app/journal/journal-translation-status';
import JournalLexicalComposer, {
  type JournalEditorBlockAction,
  type JournalEditorInlineFormat,
  type JournalLexicalComposerHandle,
} from '@/features/journal/editor/JournalLexicalComposer';
import {
  deriveJournalAttachmentAlt,
  findInsertedAttachmentIds,
  insertAttachmentMarkdown,
  preserveAttachmentMarkdown,
  stripAttachmentMarkdown,
} from '@/features/journal/editor/journal-attachment-markdown';
import { useJournalAutosave } from '@/features/journal/editor/useJournalAutosave';
import {
  buildCreateJournalPayload,
  buildUpdateJournalPayload,
  hasJournalDraftContent,
  hasJournalSubstantiveContent,
  resolveJournalDraftContent,
} from '@/app/journal/journal-draft-payload';
import {
  buildJournalOutline,
} from '@/lib/journal-outline';
import {
  buildJournalSectionModel,
  type JournalSectionModel,
} from '@/lib/journal-section-model';
import { buildJournalRereadGuide } from '@/lib/journal-reread-guide';

const DEFAULT_VISIBILITY: JournalVisibility = 'PRIVATE';
const JOURNAL_HOME_SEED_STORAGE_KEY = 'haven_journal_home_seed_v1';
const LEGACY_JOURNAL_VISIBILITIES = new Set<JournalVisibility>([
  'PARTNER_ANALYSIS_ONLY',
  'PRIVATE_LOCAL',
]);
const MOBILE_BLOCK_ACTIONS: Array<{ action: JournalEditorBlockAction; label: string; note: string }> = [
  { action: 'paragraph', label: '一般段落', note: '回到最自然的正文節奏。' },
  { action: 'heading-1', label: '主標題', note: '給這一段一個更明顯的重心。' },
  { action: 'heading-2', label: '小節標題', note: '幫長文切出清楚章節。' },
  { action: 'bullet-list', label: '項目清單', note: '把要點一條條排開。' },
  { action: 'ordered-list', label: '編號清單', note: '整理順序與步驟。' },
  { action: 'quote', label: '引用', note: '讓一句話被更安靜地看見。' },
  { action: 'code-block', label: '程式碼區塊', note: '放進格式化片段或範例。' },
  { action: 'link', label: '連結', note: '插入可編輯的連結模板。' },
];
const MOBILE_INLINE_ACTIONS: Array<{ format: JournalEditorInlineFormat; label: string }> = [
  { format: 'bold', label: '粗體' },
  { format: 'italic', label: '斜體' },
  { format: 'code', label: '行內程式碼' },
];
const REFLECTION_SECTION_STARTERS: JournalReflectionSectionStarter[] = [
  {
    description: '先把場景、事件或對話放下來，不急著整理成結論。',
    heading: '發生了什麼',
    id: 'what-happened',
    label: '發生了什麼',
    prompt: '先把場景、事件或對話放在這裡。',
  },
  {
    description: '把表面情緒底下真正被碰到的地方寫清楚。',
    heading: '我真正感受到的是',
    id: 'what-i-felt',
    label: '我真正感受到的是',
    prompt: '我真正感受到的是……',
  },
  {
    description: '把這一頁想帶進關係、對話或下一步的重點留下來。',
    heading: '我想帶進關係的是',
    id: 'bring-forward',
    label: '我想帶進關係的是',
    prompt: '我想帶進關係的是……',
  },
];

function buildSnapshot({
  attachments,
  content,
  isDraft,
  title,
  visibility,
}: {
  attachments: JournalAttachmentPublic[];
  content: string;
  isDraft: boolean;
  title: string;
  visibility: JournalVisibility;
}) {
  return JSON.stringify({
    attachments: attachments.map((attachment) => attachment.id),
    content,
    isDraft,
    title,
    visibility,
  });
}

function appendReflectionSectionMarkdown(
  baseContent: string,
  starter: JournalReflectionSectionStarter,
) {
  const heading = starter.heading.trim();
  const prompt = starter.prompt.trim();
  const sectionMarkdown = prompt ? `## ${heading}\n\n${prompt}` : `## ${heading}`;
  const trimmedBase = baseContent.trimEnd();
  return trimmedBase ? `${trimmedBase}\n\n${sectionMarkdown}` : sectionMarkdown;
}

interface JournalPageContentProps {
  journalId?: string;
}

interface PersistJournalDraftResult {
  content: string;
  isDraft: boolean;
  journalId: string;
}

function isLegacyJournalVisibility(
  visibility: JournalVisibility | null | undefined,
): visibility is 'PARTNER_ANALYSIS_ONLY' | 'PRIVATE_LOCAL' {
  return LEGACY_JOURNAL_VISIBILITIES.has((visibility ?? DEFAULT_VISIBILITY) as JournalVisibility);
}

function buildVisibilityLabel(visibility: JournalVisibility) {
  return visibility === 'PRIVATE'
    ? '私密保存'
    : visibility === 'PRIVATE_LOCAL'
      ? '完全私密（舊版）'
      : visibility === 'PARTNER_ORIGINAL'
        ? '伴侶看原文'
        : visibility === 'PARTNER_ANALYSIS_ONLY'
          ? '伴侶只看分析（舊版）'
          : '伴侶看整理後的版本';
}

function buildPreviewContextMessage(visibility: JournalVisibility) {
  return visibility === 'PRIVATE'
    ? '這一頁只留在你的 Journal 書房裡，伴侶看不到。'
    : visibility === 'PRIVATE_LOCAL'
      ? '這一頁沿用舊版的完全私密設定：不分享，也不送 AI。'
      : visibility === 'PARTNER_ORIGINAL'
        ? '伴侶會看到你寫下的原文，也會看到同一組圖片。'
        : visibility === 'PARTNER_ANALYSIS_ONLY'
          ? '這一頁沿用舊版的分析分享設定：伴侶只會看到分析資訊。'
          : '伴侶只會收到 Haven 為對方整理後的版本；原文和圖片仍只留在你的書房。';
}

export default function JournalPageContent({ journalId }: JournalPageContentProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const readSurfaceRef = useRef<HTMLDivElement | null>(null);
  const titleInputRef = useRef<HTMLInputElement | null>(null);
  const editorRef = useRef<JournalLexicalComposerHandle | null>(null);
  const autoDraftBootstrapRef = useRef(false);
  const hydratedJournalIdRef = useRef<string | null>(null);
  const contentRef = useRef('');
  const titleRef = useRef('');
  const visibilityRef = useRef<JournalVisibility>(DEFAULT_VISIBILITY);
  const suppressBlankEditorSyncRef = useRef(false);
  const hasExplicitVisibilitySelectionRef = useRef(false);
  const persistedVisibilityRef = useRef<JournalVisibility>(DEFAULT_VISIBILITY);
  const homeSeedConsumedRef = useRef(false);
  const savedSnapshotRef = useRef(
    buildSnapshot({
      attachments: [],
      content: '',
      isDraft: false,
      title: '',
      visibility: DEFAULT_VISIBILITY,
    }),
  );

  const journalsQuery = useJournals(true);
  const journalDetailQuery = useJournalDetail(journalId ?? null, !!journalId);

  const createJournalMutation = useCreateJournal();
  const updateJournalMutation = useUpdateJournal();
  const deleteJournalMutation = useDeleteJournal();
  const uploadAttachmentMutation = useUploadJournalAttachment();
  const deleteAttachmentMutation = useDeleteJournalAttachment();

  const journals = sortJournalsDesc(journalsQuery.data);
  const activeJournal = journalId ? journalDetailQuery.data : null;

  const [draftOpen, setDraftOpen] = useState(Boolean(journalId));
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [isDraft, setIsDraft] = useState(false);
  const [visibility, setVisibility] = useState<JournalVisibility>(DEFAULT_VISIBILITY);
  const [attachments, setAttachments] = useState<JournalAttachmentPublic[]>([]);
  const [partnerTranslationStatus, setPartnerTranslationStatus] = useState<JournalTranslationStatus>('NOT_REQUESTED');
  const [partnerTranslationReadyAt, setPartnerTranslationReadyAt] = useState<string | null>(null);
  const [editorSeed, setEditorSeed] = useState(0);
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<JournalSaveState>('draft');
  const [saveError, setSaveError] = useState<string | null>(null);
  const [importWarning, setImportWarning] = useState<string | null>(null);
  const [studioMode, setStudioMode] = useState<JournalStudioMode>('write');
  const [hasExplicitVisibilitySelection, setHasExplicitVisibilitySelection] = useState(false);
  const [canCompare, setCanCompare] = useState(false);
  const [desktopImagesOpen, setDesktopImagesOpen] = useState(false);
  const [desktopShareOpen, setDesktopShareOpen] = useState(false);
  const [mobileSheet, setMobileSheet] = useState<'format' | 'images' | 'share' | null>(null);
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);

  const currentJournalId = activeJournal?.id ?? hydratedJournalIdRef.current ?? journalId ?? null;
  const currentSnapshot = useMemo(
    () => buildSnapshot({ attachments, content, isDraft, title, visibility }),
    [attachments, content, isDraft, title, visibility],
  );
  const hasUnsavedChanges = currentSnapshot !== savedSnapshotRef.current;
  const hasLocalEditingState =
    saveState === 'dirty' || saveState === 'saving' || saveState === 'error';
  const draftHasSubstantiveContent = hasJournalSubstantiveContent(content);
  const paragraphCount = content.trim() ? content.trim().split(/\n{2,}/g).length : 0;
  const insertedAttachmentIds = useMemo(() => findInsertedAttachmentIds(content), [content]);
  const activeTitle = title.trim() || (activeJournal ? deriveJournalTitle(activeJournal) : '未命名的一頁');
  const journalOutline = useMemo(
    () =>
      buildJournalOutline({
        content,
        title,
      }),
    [content, title],
  );
  const titleEntry = useMemo(
    () => journalOutline.find((entry) => entry.kind === 'title') ?? null,
    [journalOutline],
  );
  const headingEntries = useMemo(
    () => journalOutline.filter((entry) => entry.kind === 'heading'),
    [journalOutline],
  );
  const journalSections = useMemo(
    () =>
      buildJournalSectionModel({
        content,
        outlineEntries: journalOutline,
        title,
      }),
    [content, journalOutline, title],
  );
  const titleSection = useMemo(
    () => journalSections.find((entry) => entry.kind === 'title') ?? null,
    [journalSections],
  );
  const rereadGuide = useMemo(
    () =>
      buildJournalRereadGuide({
        content,
        imageCount: attachments.length,
        sections: journalSections,
      }),
    [attachments.length, content, journalSections],
  );
  const showDocumentMap = journalSections.length > 0;
  const showReflectionStarters =
    studioMode !== 'read' &&
    (content.trim().length < 650 ||
      journalSections.filter((section) => section.kind === 'heading').length < 2);
  const showStudio = Boolean(journalId) || draftOpen;
  const draftBootstrapPending = !currentJournalId && createJournalMutation.isPending;
  const editorKey = `${currentJournalId ?? `draft:${draftOpen ? 'open' : 'closed'}`}:${editorSeed}`;
  const currentDateLabel = new Date(
    lastSavedAt ?? activeJournal?.updated_at ?? activeJournal?.created_at ?? Date.now(),
  ).toLocaleDateString('zh-TW', {
    month: 'long',
    day: 'numeric',
  });
  const visibilityLabel = buildVisibilityLabel(visibility);
  const shouldAutoOpenDraft = searchParams.get('compose') === '1';
  const memoryReturnDate = searchParams.get('date');
  const fromMemory = searchParams.get('from') === 'memory';
  const showLegacyVisibilityNotice =
    isLegacyJournalVisibility(persistedVisibilityRef.current) && !hasExplicitVisibilitySelection;
  const legacyVisibilityMessage =
    persistedVisibilityRef.current === 'PRIVATE_LOCAL'
      ? '這一頁沿用較早的「完全私密」設定。只要你不改分享設定，它就會維持不分享、也不送 AI。'
      : persistedVisibilityRef.current === 'PARTNER_ANALYSIS_ONLY'
        ? '這一頁沿用較早的「伴侶只看分析」設定。只要你不改分享設定，它就會維持只分享分析資訊。'
        : null;
  const memoryReturnHref =
    fromMemory && memoryReturnDate && /^\d{4}-\d{2}-\d{2}$/.test(memoryReturnDate)
      ? `/memory?date=${memoryReturnDate}`
      : null;
  const detailBackHref = memoryReturnHref ?? (currentJournalId ? '/journal' : '/');
  const detailErrorBackHref = memoryReturnHref ?? '/journal';

  const commitContentState = useCallback((nextContent: string) => {
    contentRef.current = nextContent;
    setContent(nextContent);
  }, []);

  const commitTitleState = useCallback((nextTitle: string) => {
    titleRef.current = nextTitle;
    setTitle(nextTitle);
  }, []);

  useEffect(() => {
    titleRef.current = title;
  }, [title]);

  useEffect(() => {
    visibilityRef.current = visibility;
  }, [visibility]);

  useEffect(() => {
    setActiveSectionId((current) => {
      if (current && journalSections.some((entry) => entry.id === current)) {
        return current;
      }
      return journalSections[0]?.id ?? null;
    });
  }, [journalSections]);

  useEffect(() => {
    hasExplicitVisibilitySelectionRef.current = hasExplicitVisibilitySelection;
  }, [hasExplicitVisibilitySelection]);

  useEffect(() => {
    if (journalId) {
      setDraftOpen(true);
    }
  }, [journalId]);

  useEffect(() => {
    const media = window.matchMedia('(min-width: 1280px)');
    const syncMode = () => {
      setCanCompare(media.matches);
      setStudioMode((current) => {
        if (!media.matches && current === 'compare') return 'write';
        return current;
      });
    };

    syncMode();
    media.addEventListener('change', syncMode);
    return () => media.removeEventListener('change', syncMode);
  }, []);

  useEffect(() => {
    if (!activeJournal) return;

    const nextAttachments = activeJournal.attachments ?? [];
    const nextContent = activeJournal.content ?? '';
    const nextIsDraft = Boolean(activeJournal.is_draft);
    const nextPartnerTranslationStatus = activeJournal.partner_translation_status ?? 'NOT_REQUESTED';
    const nextPartnerTranslationReadyAt = activeJournal.partner_translation_ready_at ?? null;
    const nextTitle = activeJournal.title?.trim() ?? '';
    const nextVisibility = activeJournal.visibility ?? DEFAULT_VISIBILITY;
    const incomingSnapshot = buildSnapshot({
      attachments: nextAttachments,
      content: nextContent,
      isDraft: nextIsDraft,
      title: nextTitle,
      visibility: nextVisibility,
    });
    const isSameJournal = hydratedJournalIdRef.current === activeJournal.id;
    if (isSameJournal && incomingSnapshot === savedSnapshotRef.current) return;
    if (isSameJournal && hasLocalEditingState) return;

    hydratedJournalIdRef.current = activeJournal.id;
    persistedVisibilityRef.current = nextVisibility;
    savedSnapshotRef.current = incomingSnapshot;
    suppressBlankEditorSyncRef.current = true;
    setDraftOpen(true);
    commitTitleState(nextTitle);
    commitContentState(nextContent);
    setIsDraft(nextIsDraft);
    setVisibility(nextVisibility);
    setAttachments(nextAttachments);
    setPartnerTranslationStatus(nextPartnerTranslationStatus);
    setPartnerTranslationReadyAt(nextPartnerTranslationReadyAt);
    setLastSavedAt(activeJournal.updated_at ?? activeJournal.created_at);
    setSaveState('saved');
    setHasExplicitVisibilitySelection(false);
    setSaveError(null);
    setImportWarning(null);
    setEditorSeed((seed) => seed + 1);
  }, [activeJournal, commitContentState, commitTitleState, hasLocalEditingState]);

  const resetDraftState = useCallback(() => {
    autoDraftBootstrapRef.current = false;
    hydratedJournalIdRef.current = null;
    savedSnapshotRef.current = buildSnapshot({
      attachments: [],
      content: '',
      isDraft: false,
      title: '',
      visibility: DEFAULT_VISIBILITY,
    });
    suppressBlankEditorSyncRef.current = true;
    persistedVisibilityRef.current = DEFAULT_VISIBILITY;
    commitTitleState('');
    commitContentState('');
    setIsDraft(false);
    setVisibility(DEFAULT_VISIBILITY);
    setHasExplicitVisibilitySelection(false);
    setAttachments([]);
    setPartnerTranslationStatus('NOT_REQUESTED');
    setPartnerTranslationReadyAt(null);
    setLastSavedAt(null);
    setSaveState('draft');
    setSaveError(null);
    setImportWarning(null);
    setEditorSeed((seed) => seed + 1);
  }, [commitContentState, commitTitleState]);

  const openDraftStudio = useCallback(() => {
    resetDraftState();
    setDraftOpen(true);
    setStudioMode('write');
  }, [resetDraftState]);

  const markUnsaved = useCallback(
    ({
      nextAttachments = attachments,
      nextContent = content,
      nextIsDraft = isDraft,
      nextTitle = title,
      nextVisibility = visibility,
    }: {
      nextAttachments?: JournalAttachmentPublic[];
      nextContent?: string;
      nextIsDraft?: boolean;
      nextTitle?: string;
      nextVisibility?: JournalVisibility;
    } = {}) => {
      setSaveError(null);
      const nextSnapshot = buildSnapshot({
        attachments: nextAttachments,
        content: nextContent,
        isDraft: nextIsDraft,
        title: nextTitle,
        visibility: nextVisibility,
      });

      if (!currentJournalId && !nextContent.trim() && !nextTitle.trim() && !nextAttachments.length) {
        setSaveState('draft');
        return;
      }

      setSaveState(nextSnapshot === savedSnapshotRef.current ? 'saved' : 'dirty');
    },
    [attachments, content, currentJournalId, isDraft, title, visibility],
  );

  useEffect(() => {
    if (journalId || showStudio || homeSeedConsumedRef.current) {
      return;
    }
    if (typeof window === 'undefined') {
      return;
    }

    const seed = window.sessionStorage.getItem(JOURNAL_HOME_SEED_STORAGE_KEY) ?? '';
    if (!shouldAutoOpenDraft && !seed.trim()) {
      return;
    }

    homeSeedConsumedRef.current = true;
    if (seed) {
      window.sessionStorage.removeItem(JOURNAL_HOME_SEED_STORAGE_KEY);
    }

    resetDraftState();
    setDraftOpen(true);
    setStudioMode('write');
    if (seed) {
      commitContentState(seed);
      setIsDraft(true);
      markUnsaved({ nextContent: seed, nextIsDraft: true });
    }
  }, [
    commitContentState,
    commitTitleState,
    journalId,
    markUnsaved,
    resetDraftState,
    shouldAutoOpenDraft,
    showStudio,
  ]);

  const readCurrentJournalContent = useCallback(() => {
    return preserveAttachmentMarkdown(
      resolveJournalDraftContent({
        editorMarkdown: editorRef.current?.getMarkdown(),
        fallbackContent: contentRef.current,
      }),
      {
        attachments,
        previousContent: contentRef.current,
      },
    );
  }, [attachments]);

  const readCurrentJournalTitle = useCallback(() => {
    const liveValue = titleInputRef.current?.value;
    if (typeof liveValue === 'string') {
      return liveValue;
    }
    return titleRef.current;
  }, []);

  const settleDraftInputs = useCallback(async () => {
    if (typeof window !== 'undefined') {
      await new Promise<void>((resolve) => {
        window.requestAnimationFrame(() => resolve());
      });
    }
  }, []);

  const syncEditorMarkdown = useCallback(
    (nextContent: string) => {
      if (suppressBlankEditorSyncRef.current && !nextContent.trim()) {
        suppressBlankEditorSyncRef.current = false;
        return;
      }
      suppressBlankEditorSyncRef.current = false;
      const stabilizedContent = preserveAttachmentMarkdown(nextContent, {
        attachments,
        previousContent: contentRef.current,
      });
      contentRef.current = stabilizedContent;
      setContent(stabilizedContent);
      markUnsaved({ nextContent: stabilizedContent, nextIsDraft: isDraft });
    },
    [attachments, isDraft, markUnsaved],
  );

  const persistDraft = useCallback(
    async ({
      intent = 'auto',
      navigate = true,
      reason,
      requestAnalysis = false,
      silent,
    }: {
      intent?: 'auto' | 'draft' | 'page';
      navigate?: boolean;
      reason: 'autosave' | 'manual';
      requestAnalysis?: boolean;
      silent: boolean;
    }): Promise<PersistJournalDraftResult | null> => {
      await settleDraftInputs();
      const currentContent = readCurrentJournalContent();
      const currentTitle = readCurrentJournalTitle();
      titleRef.current = currentTitle;
      const substantiveContentPresent = hasJournalSubstantiveContent(currentContent);
      const targetIsDraft =
        intent === 'draft'
          ? true
          : intent === 'page'
            ? false
            : currentJournalId
              ? (isDraft ? !substantiveContentPresent : false)
              : !substantiveContentPresent;

      if (!targetIsDraft && !hasJournalDraftContent(currentContent)) {
        if (!silent) {
          showToast('先留下一段內容，這一頁才能真正收進書房。', 'error');
        }
        setSaveState(currentJournalId ? (isDraft ? 'dirty' : 'error') : 'draft');
        return null;
      }

      try {
        setSaveState('saving');
        setSaveError(null);

        const nextVisibilityForPersist =
          currentJournalId &&
          isLegacyJournalVisibility(persistedVisibilityRef.current) &&
          !hasExplicitVisibilitySelectionRef.current
            ? undefined
            : visibilityRef.current;

        if (currentJournalId) {
          const payload = buildUpdateJournalPayload({
            content: currentContent,
            isDraft: targetIsDraft,
            requestAnalysis,
            title: currentTitle,
            visibility: nextVisibilityForPersist,
          });
          const updated = await updateJournalMutation.mutateAsync({
            id: currentJournalId,
            payload,
          });

          // Use the same fallback values as the hydration useEffect so the
          // savedSnapshot matches what hydration would compute from setQueryData.
          const resolvedAttachments = updated.attachments ?? [];
          const resolvedContent = updated.content ?? '';
          const resolvedIsDraft = Boolean(updated.is_draft);
          const resolvedTitle = updated.title?.trim() ?? '';
          const resolvedVisibility = updated.visibility ?? DEFAULT_VISIBILITY;
          const resolvedTranslationStatus = updated.partner_translation_status ?? 'NOT_REQUESTED';
          const resolvedTranslationReadyAt = updated.partner_translation_ready_at ?? null;

          // Detect concurrent local edits during the async save round-trip
          const latestLocalContent = contentRef.current;
          const latestLocalTitle = titleRef.current;
          const latestLocalVisibility = visibilityRef.current;
          const contentChangedDuringSave = latestLocalContent !== currentContent;
          const titleChangedDuringSave = latestLocalTitle !== currentTitle;
          const visibilityChangedDuringSave = latestLocalVisibility !== visibilityRef.current;
          const hasLocalEditsSinceSubmit =
            contentChangedDuringSave || titleChangedDuringSave || visibilityChangedDuringSave;
          const nextContentState = contentChangedDuringSave ? latestLocalContent : resolvedContent;
          const nextTitleState = titleChangedDuringSave ? latestLocalTitle : resolvedTitle;
          const nextVisibilityState = visibilityChangedDuringSave
            ? latestLocalVisibility
            : resolvedVisibility;

          // Build the saved snapshot using the server-confirmed values so the
          // hydration useEffect (which also builds a snapshot from activeJournal)
          // will see an identical string and skip the unnecessary editor remount.
          savedSnapshotRef.current = buildSnapshot({
            attachments: resolvedAttachments,
            content: resolvedContent,
            isDraft: resolvedIsDraft,
            title: resolvedTitle,
            visibility: resolvedVisibility,
          });
          persistedVisibilityRef.current = resolvedVisibility;
          setAttachments(resolvedAttachments);
          commitContentState(nextContentState);
          setIsDraft(resolvedIsDraft);
          commitTitleState(nextTitleState);
          setVisibility(nextVisibilityState);
          setPartnerTranslationStatus(resolvedTranslationStatus);
          setPartnerTranslationReadyAt(resolvedTranslationReadyAt);
          setHasExplicitVisibilitySelection(false);
          setLastSavedAt(updated.updated_at ?? updated.created_at);
          setSaveState(hasLocalEditsSinceSubmit ? 'dirty' : 'saved');
          if (requestAnalysis) {
            router.push('/');
          }
          return {
            content: nextContentState,
            isDraft: resolvedIsDraft,
            journalId: updated.id,
          };
        }

        const draft = buildCreateJournalPayload({
          content: currentContent,
          isDraft: targetIsDraft,
          title: currentTitle,
          visibility: visibilityRef.current,
        });
        const created = await createJournalMutation.mutateAsync({
          draft,
        });
        suppressBlankEditorSyncRef.current = true;
        hydratedJournalIdRef.current = created.id;
        const resolvedAttachments = created.attachments ?? [];
        const resolvedIsDraft = Boolean(created.is_draft);
        const resolvedTitle = created.title?.trim() ?? '';
        const resolvedContent = created.content ?? '';
        const resolvedVisibility = created.visibility ?? DEFAULT_VISIBILITY;
        const resolvedTranslationStatus = created.partner_translation_status ?? 'NOT_REQUESTED';
        const resolvedTranslationReadyAt = created.partner_translation_ready_at ?? null;
        const latestLocalContent = contentRef.current;
        const latestLocalTitle = titleRef.current;
        const latestLocalVisibility = visibilityRef.current;
        const contentChangedDuringSave = latestLocalContent !== currentContent;
        const titleChangedDuringSave = latestLocalTitle !== currentTitle;
        const visibilityChangedDuringSave = latestLocalVisibility !== visibilityRef.current;
        const nextContentState = contentChangedDuringSave ? latestLocalContent : resolvedContent;
        const nextTitleState = titleChangedDuringSave ? latestLocalTitle : resolvedTitle;
        const nextVisibilityState = visibilityChangedDuringSave
          ? latestLocalVisibility
          : resolvedVisibility;
        const hasLocalEditsSinceSubmit =
          contentChangedDuringSave || titleChangedDuringSave || visibilityChangedDuringSave;

        savedSnapshotRef.current = buildSnapshot({
          attachments: resolvedAttachments,
          content: resolvedContent,
          isDraft: resolvedIsDraft,
          title: resolvedTitle,
          visibility: resolvedVisibility,
        });
        persistedVisibilityRef.current = resolvedVisibility;
        queryClient.setQueryData(queryKeys.journalDetail(created.id), created);
        setAttachments(resolvedAttachments);
        commitContentState(nextContentState);
        setIsDraft(resolvedIsDraft);
        commitTitleState(nextTitleState);
        setVisibility(nextVisibilityState);
        setPartnerTranslationStatus(resolvedTranslationStatus);
        setPartnerTranslationReadyAt(resolvedTranslationReadyAt);
        setHasExplicitVisibilitySelection(false);
        setLastSavedAt(created.updated_at ?? created.created_at);
        setSaveState(hasLocalEditsSinceSubmit ? 'dirty' : 'saved');
        setDraftOpen(true);

        if (navigate) {
          router.push(`/journal/${created.id}`);
        }

        if (!silent && reason === 'manual') {
          showToast(
            resolvedIsDraft ? '新的草稿頁已收進 Journal 書房。' : '這一頁已收進 Journal 書房。',
            'success',
          );
        }
        return {
          content: resolvedContent,
          isDraft: resolvedIsDraft,
          journalId: created.id,
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : '儲存失敗，請稍後再試。';
        setSaveState('error');
        setSaveError(message);
        logClientError('journal_editor_autosave_failed', error);
        if (!silent) {
          showToast(message, 'error');
        }
        return null;
      }
    },
    [
      createJournalMutation,
      currentJournalId,
      commitContentState,
      isDraft,
      commitTitleState,
      queryClient,
      readCurrentJournalTitle,
      readCurrentJournalContent,
      router,
      settleDraftInputs,
      showToast,
      updateJournalMutation,
    ],
  );

  useEffect(() => {
    if (!showStudio || journalId || currentJournalId || autoDraftBootstrapRef.current) {
      return;
    }

    autoDraftBootstrapRef.current = true;
    void persistDraft({
      intent: 'draft',
      navigate: true,
      reason: 'manual',
      silent: true,
    }).then((persisted) => {
      if (!persisted) {
        autoDraftBootstrapRef.current = false;
      }
    });
  }, [currentJournalId, journalId, persistDraft, showStudio]);

  useJournalAutosave({
    enabled:
      Boolean(currentJournalId) &&
      hasUnsavedChanges &&
      saveState !== 'saving' &&
      !uploadAttachmentMutation.isPending &&
      !deleteAttachmentMutation.isPending,
    onAutosave: () =>
      persistDraft({
        intent: isDraft ? 'draft' : 'page',
        reason: 'autosave',
        silent: true,
      }),
    pending: saveState === 'saving',
    snapshot: currentSnapshot,
  });

  useEffect(() => {
    if (!hasUnsavedChanges) return;

    const beforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
      logClientError('journal_beforeunload_unsaved', new Error('unsaved_changes_beforeunload'));
    };

    window.addEventListener('beforeunload', beforeUnload);
    return () => window.removeEventListener('beforeunload', beforeUnload);
  }, [hasUnsavedChanges]);

  useEffect(() => {
    if (!showStudio) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (!(event.metaKey || event.ctrlKey)) return;
      const key = event.key.toLowerCase();

      if (key === 's') {
        event.preventDefault();
        void persistDraft({ intent: 'auto', reason: 'manual', silent: false });
        return;
      }

      if (event.shiftKey && key === 'p') {
        event.preventDefault();
        setStudioMode((current) => {
          if (current === 'write') {
            return canCompare ? 'compare' : 'read';
          }
          return 'write';
        });
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [canCompare, isDraft, persistDraft, showStudio]);

  const saveMessage =
    saveState === 'saving'
      ? '保存中'
      : saveState === 'saved'
        ? (isDraft ? '草稿已收好' : '已收好')
        : saveState === 'error'
          ? '暫時沒收好'
          : saveState === 'dirty'
            ? currentJournalId
              ? (isDraft ? '草稿有新變更' : '未儲存變更')
              : '草稿未保存'
            : '草稿';

  const previewContextMessage = buildPreviewContextMessage(visibility);
  const persistedVisibility = persistedVisibilityRef.current;
  const translationStatusPresentation = useMemo(
    () =>
      buildJournalTranslationStatusPresentation({
        currentVisibility: visibility,
        hasCurrentJournalId: Boolean(currentJournalId),
        hasExplicitVisibilitySelection,
        isDraft,
        partnerTranslationReadyAt,
        partnerTranslationStatus,
        persistedVisibility,
      }),
    [
      currentJournalId,
      hasExplicitVisibilitySelection,
      isDraft,
      partnerTranslationReadyAt,
      partnerTranslationStatus,
      persistedVisibility,
      visibility,
    ],
  );
  const sharingDeliveryPresentation = useMemo(
    () =>
      buildJournalSharingDeliveryPresentation({
        attachmentsCount: attachments.length,
        currentVisibility: visibility,
        hasCurrentJournalId: Boolean(currentJournalId),
        hasExplicitVisibilitySelection,
        hasUnsavedChanges,
        isDraft,
        partnerTranslationReadyAt,
        partnerTranslationStatus,
        persistedVisibility,
        saveState,
      }),
    [
      attachments.length,
      currentJournalId,
      hasExplicitVisibilitySelection,
      hasUnsavedChanges,
      isDraft,
      partnerTranslationReadyAt,
      partnerTranslationStatus,
      persistedVisibility,
      saveState,
      visibility,
    ],
  );

  const insertAttachmentIntoDraft = useCallback(
    ({
      attachment,
      baseContent,
    }: {
      attachment: JournalAttachmentPublic;
      baseContent?: string;
    }) => {
      const alt = deriveJournalAttachmentAlt(attachment.file_name);
      const attachmentToken = `attachment:${attachment.id}`;
      const insertedMarkdown = editorRef.current?.insertImage({
        alt,
        src: attachmentToken,
      });
      const nextMarkdown =
        insertedMarkdown && insertedMarkdown.includes(attachmentToken)
          ? insertedMarkdown
          : insertAttachmentMarkdown(baseContent ?? readCurrentJournalContent(), {
              alt,
              attachmentId: attachment.id,
            });

      return {
        nextMarkdown,
        usedFallback: !insertedMarkdown || !insertedMarkdown.includes(attachmentToken),
      };
    },
    [readCurrentJournalContent],
  );

  const handleAttachmentUpload = useCallback(
    async (files: File[]) => {
      if (!files.length) return;

      try {
        let resolvedJournalId = currentJournalId;
        let nextMarkdown = readCurrentJournalContent() || activeJournal?.content || contentRef.current || '';
        if (!resolvedJournalId) {
          const persisted = await persistDraft({
            intent: 'draft',
            navigate: false,
            reason: 'manual',
            silent: false,
          });
          resolvedJournalId = persisted?.journalId ?? null;
          nextMarkdown = persisted?.content ?? nextMarkdown;
        }

        if (!resolvedJournalId) {
          return;
        }

        let nextAttachments = [...attachments];
        let shouldRehydrateEditor = false;

        for (const file of files) {
          const attachment = await uploadAttachmentMutation.mutateAsync({
            journalId: resolvedJournalId,
            file,
          });
          nextAttachments = [...nextAttachments, attachment];
          const insertionResult = insertAttachmentIntoDraft({
            attachment,
            baseContent: nextMarkdown,
          });
          nextMarkdown = insertionResult.nextMarkdown;
          shouldRehydrateEditor = shouldRehydrateEditor || insertionResult.usedFallback;
        }

        const updated = await updateJournalMutation.mutateAsync({
          id: resolvedJournalId,
          payload: buildUpdateJournalPayload({
            content: nextMarkdown,
            isDraft: true,
            title,
            visibility,
          }),
        });

        const resolvedAttachments = updated.attachments ?? nextAttachments;
        const resolvedIsDraft = Boolean(updated.is_draft ?? true);
        savedSnapshotRef.current = buildSnapshot({
          attachments: resolvedAttachments,
          content: nextMarkdown,
          isDraft: resolvedIsDraft,
          title,
          visibility,
        });
        hydratedJournalIdRef.current = resolvedJournalId;
        queryClient.setQueryData(queryKeys.journalDetail(resolvedJournalId), {
          ...updated,
          attachments: resolvedAttachments,
          content: nextMarkdown,
          is_draft: resolvedIsDraft,
          title,
          visibility,
        });
        setAttachments(resolvedAttachments);
        commitContentState(nextMarkdown);
        setIsDraft(resolvedIsDraft);
        setLastSavedAt(updated.updated_at ?? updated.created_at);
        setSaveState('saved');
        setSaveError(null);
        setDraftOpen(true);
        if (shouldRehydrateEditor) {
          suppressBlankEditorSyncRef.current = true;
          setEditorSeed((seed) => seed + 1);
        }
        setDesktopImagesOpen(true);

        if (!journalId) {
          router.replace(`/journal/${resolvedJournalId}`);
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : '圖片上傳失敗，請稍後再試。';
        setSaveState('error');
        setSaveError(message);
        logClientError('journal_attachment_insert_failed', error);
        showToast(message, 'error');
      } finally {
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }
    },
    [
      attachments,
      activeJournal?.content,
      currentJournalId,
      commitContentState,
      journalId,
      persistDraft,
      queryClient,
      readCurrentJournalContent,
      router,
      showToast,
      title,
      insertAttachmentIntoDraft,
      updateJournalMutation,
      uploadAttachmentMutation,
      visibility,
    ],
  );

  const handleDeleteAttachment = useCallback(
    async (attachment: JournalAttachmentPublic) => {
      if (!currentJournalId) return;

      const shouldDelete = await confirm({
        title: '移除圖片',
        message: '這張圖片會從這一頁和伴侶可見內容中一起移除。',
        confirmText: '移除',
        cancelText: '取消',
      });
      if (!shouldDelete) return;

      try {
        await deleteAttachmentMutation.mutateAsync({
          journalId: currentJournalId,
          attachmentId: attachment.id,
        });

        const nextAttachments = attachments.filter((item) => item.id !== attachment.id);
        const nextContent = stripAttachmentMarkdown(readCurrentJournalContent(), attachment.id);

        const updated = await updateJournalMutation.mutateAsync({
          id: currentJournalId,
          payload: buildUpdateJournalPayload({
            content: nextContent,
            isDraft,
            title,
            visibility,
          }),
        });

        const resolvedAttachments = updated.attachments ?? nextAttachments;
        const resolvedIsDraft = Boolean(updated.is_draft ?? isDraft);
        savedSnapshotRef.current = buildSnapshot({
          attachments: resolvedAttachments,
          content: nextContent,
          isDraft: resolvedIsDraft,
          title,
          visibility,
        });
        setAttachments(resolvedAttachments);
        commitContentState(nextContent);
        setIsDraft(resolvedIsDraft);
        setLastSavedAt(updated.updated_at ?? updated.created_at);
        setSaveState('saved');
        setSaveError(null);
        if (!resolvedAttachments.length) {
          setDesktopImagesOpen(false);
        }
      } catch (error) {
        setSaveState('error');
        setSaveError('這次沒有順利移除這張圖片，稍後再試一次。');
        logClientError('journal_attachment_remove_failed', error);
        showToast('這次沒有順利移除這張圖片，稍後再試一次。', 'error');
      }
    },
    [
      attachments,
      commitContentState,
      confirm,
      currentJournalId,
      deleteAttachmentMutation,
      isDraft,
      readCurrentJournalContent,
      showToast,
      title,
      updateJournalMutation,
      visibility,
    ],
  );

  const handleAttachmentCaptionChange = useCallback(
    async (attachmentId: string, caption: string | null) => {
      if (!currentJournalId) return;
      try {
        const updated = await updateJournalAttachmentCaption(
          currentJournalId,
          attachmentId,
          caption,
        );
        setAttachments((prev) =>
          prev.map((item) => (item.id === updated.id ? updated : item)),
        );
      } catch (error) {
        logClientError('journal_attachment_caption_update_failed', error);
        showToast('這次沒有順利儲存圖片說明，稍後再試一次。', 'error');
      }
    },
    [currentJournalId, showToast],
  );

  const ensureJournalExistsForUpload = useCallback(async () => {
    if (currentJournalId) return currentJournalId;
    const persisted = await persistDraft({
      intent: 'draft',
      navigate: false,
      reason: 'manual',
      silent: false,
    });
    return persisted?.journalId ?? null;
  }, [currentJournalId, persistDraft]);

  const handleDeleteJournal = useCallback(async () => {
    if (!currentJournalId) {
      resetDraftState();
      setDraftOpen(false);
      return;
    }

    const shouldDelete = await confirm({
      title: '刪除這篇 Journal',
      message: '刪除後這一頁會從你的書房與伴侶閱讀室一起消失。',
      confirmText: '刪除',
      cancelText: '取消',
    });
    if (!shouldDelete) return;

    try {
      await deleteJournalMutation.mutateAsync(currentJournalId);
      queryClient.removeQueries({ queryKey: queryKeys.journalDetail(currentJournalId) });
      showToast('這一頁已從 Journal 書房移開。', 'info');
      resetDraftState();
      setDraftOpen(false);
      router.push('/journal');
    } catch {
      showToast('這次沒有順利移開這一頁，稍後再試一次。', 'error');
    }
  }, [
    confirm,
    currentJournalId,
    deleteJournalMutation,
    queryClient,
    resetDraftState,
    router,
    showToast,
  ]);

  const runEditorTask = useCallback((task: () => void) => {
    const execute = () => {
      task();
      editorRef.current?.focus();
    };

    if (studioMode === 'read') {
      setStudioMode(canCompare ? 'compare' : 'write');
      requestAnimationFrame(() => requestAnimationFrame(execute));
      return;
    }

    execute();
  }, [canCompare, studioMode]);

  const handleMobileInlineFormat = useCallback((format: JournalEditorInlineFormat) => {
    runEditorTask(() => {
      editorRef.current?.applyInlineFormat(format);
    });
    setMobileSheet(null);
  }, [runEditorTask]);

  const handleMobileBlockFormat = useCallback((action: JournalEditorBlockAction) => {
    runEditorTask(() => {
      editorRef.current?.applyBlockAction(action);
    });
    setMobileSheet(null);
  }, [runEditorTask]);

  const handleInsertReflectionSection = useCallback(
    (starter: JournalReflectionSectionStarter) => {
      runEditorTask(() => {
        const editorHandle = editorRef.current;
        const insertedMarkdown = editorHandle?.insertReflectionSection({
          heading: starter.heading,
          prompt: starter.prompt,
        });
        const currentEditorMarkdown = editorHandle ? readCurrentJournalContent() : '';
        const nextMarkdown =
          insertedMarkdown && insertedMarkdown.includes(`## ${starter.heading}`)
            ? insertedMarkdown
            : currentEditorMarkdown.includes(`## ${starter.heading}`)
              ? currentEditorMarkdown
              : appendReflectionSectionMarkdown(readCurrentJournalContent(), starter);

        commitContentState(nextMarkdown);
        markUnsaved({ nextContent: nextMarkdown, nextIsDraft: isDraft });

        if (!editorHandle) {
          suppressBlankEditorSyncRef.current = true;
          setEditorSeed((seed) => seed + 1);
        }

        showToast('新的反思小節已放進這一頁。', 'success');
      });
    },
    [
      commitContentState,
      isDraft,
      markUnsaved,
      readCurrentJournalContent,
      runEditorTask,
      showToast,
    ],
  );

  const handleImagePickerRequest = useCallback(async () => {
    if (!currentJournalId && draftBootstrapPending) {
      showToast('草稿正在準備，等這一頁有了編號就能放入圖片。', 'info');
      return;
    }

    const resolvedJournalId = await ensureJournalExistsForUpload();
    if (!resolvedJournalId) return;

    if (studioMode === 'read') {
      setStudioMode(canCompare ? 'compare' : 'write');
      requestAnimationFrame(() => requestAnimationFrame(() => fileInputRef.current?.click()));
      return;
    }

    fileInputRef.current?.click();
  }, [canCompare, currentJournalId, draftBootstrapPending, ensureJournalExistsForUpload, showToast, studioMode]);

  const scrollReadSurfaceToSection = useCallback((sectionId: string) => {
    const container = readSurfaceRef.current;
    if (!container) return false;
    const target = Array.from(
      container.querySelectorAll<HTMLElement>('[data-journal-section-id]'),
    ).find((element) => element.dataset.journalSectionId === sectionId);
    if (!target) return false;
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return true;
  }, []);

  const handleSelectDocumentMapEntry = useCallback((entry: JournalSectionModel) => {
    setActiveSectionId(entry.id);

    if (studioMode === 'read' || studioMode === 'compare') {
      scrollReadSurfaceToSection(entry.id);
      return;
    }

    if (entry.kind === 'title') {
      titleInputRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      titleInputRef.current?.focus();
      return;
    }

    editorRef.current?.scrollToSection(entry.id);
  }, [scrollReadSurfaceToSection, studioMode]);

  const handleSelectRereadGuideSection = useCallback((sectionId: string) => {
    setActiveSectionId(sectionId);
    scrollReadSurfaceToSection(sectionId);
  }, [scrollReadSurfaceToSection]);

  useEffect(() => {
    if (studioMode !== 'read') return;

    const container = readSurfaceRef.current;
    if (!container) return;

    let frame: number | null = null;
    const updateActiveSection = () => {
      frame = null;
      const targets = Array.from(
        container.querySelectorAll<HTMLElement>('[data-journal-section-id]'),
      );
      if (!targets.length) return;

      const viewportAnchor = Math.min(window.innerHeight * 0.5, 360);
      let nextSectionId = targets[0]?.dataset.journalSectionId ?? null;
      let closestDistance = Number.POSITIVE_INFINITY;
      for (const target of targets) {
        const rect = target.getBoundingClientRect();
        if (rect.bottom < 96 || rect.top > window.innerHeight) {
          continue;
        }

        const distance = Math.abs(rect.top - viewportAnchor);
        if (distance < closestDistance) {
          closestDistance = distance;
          nextSectionId = target.dataset.journalSectionId ?? nextSectionId;
        }
      }

      if (nextSectionId) {
        setActiveSectionId((current) => (current === nextSectionId ? current : nextSectionId));
      }
    };

    const scheduleUpdate = () => {
      if (frame !== null) return;
      frame = window.requestAnimationFrame(updateActiveSection);
    };

    scheduleUpdate();
    window.addEventListener('scroll', scheduleUpdate, { passive: true });
    window.addEventListener('resize', scheduleUpdate);
    return () => {
      if (frame !== null) {
        window.cancelAnimationFrame(frame);
      }
      window.removeEventListener('scroll', scheduleUpdate);
      window.removeEventListener('resize', scheduleUpdate);
    };
  }, [journalSections, studioMode]);

  if (journalId && journalDetailQuery.isError) {
    return (
      <JournalStatePanel
        eyebrow="Journal Detail"
        title="這一頁暫時沒有順利打開"
        description="有可能是這篇已被刪除，或這次同步沒有順利完成。你可以先回到 Journal 書房。"
        tone="error"
        actions={
          <>
            <Button
              leftIcon={<Save className="h-4 w-4" aria-hidden />}
              onClick={() => journalDetailQuery.refetch()}
            >
              重新讀取
            </Button>
            <Link
              href={detailErrorBackHref}
              className="inline-flex items-center gap-2 rounded-full border border-white/56 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
            >
              回 Journal 書房
            </Link>
          </>
        }
      />
    );
  }

  if (!showStudio) {
    return (
      <div className="space-y-8">
        <div className="flex flex-wrap items-center gap-3">
          <JournalBackLink href="/" />
          <Link
            href="/love-map#inner-landscape"
            className="inline-flex items-center justify-center gap-2 rounded-full border border-white/58 bg-white/82 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
          >
            Relationship System 反思摘要
          </Link>
        </div>

        <JournalStudioHero
          eyebrow="Journal 書房"
          title="把值得留下來的心事，寫成真正可重讀的一頁。"
          description="Journal 是 Haven 裡更完整的反思書房：Relationship System 的 Inner Landscape 會保留結構化的個人理解，而這裡則讓你把那些感受、語氣、圖像與分享邊界寫成真正可重讀的一頁。"
          actions={
            <>
              <Button
                leftIcon={<Plus className="h-4 w-4" aria-hidden />}
                onClick={openDraftStudio}
              >
                開始新的一頁
              </Button>
              <Link
                href="/love-map#inner-landscape"
                className="inline-flex items-center justify-center gap-2 rounded-full border border-white/58 bg-white/82 px-5 py-3 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
              >
                回 Relationship System 反思摘要
              </Link>
            </>
          }
          aside={
            <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
              <div className="rounded-[1.6rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                <p className="text-[0.68rem] uppercase tracking-[0.26em] text-primary/80">Library</p>
                <p className="mt-3 font-art text-[1.7rem] text-card-foreground">{journals.length} 篇</p>
                <p className="mt-2 text-sm leading-7 text-muted-foreground">
                  所有私人頁面、原文共享與整理版本共享，都回到同一個書房管理。
                </p>
              </div>
              <div className="rounded-[1.6rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                <p className="text-[0.68rem] uppercase tracking-[0.26em] text-primary/80">Writing Model</p>
                <p className="mt-3 font-art text-[1.7rem] text-card-foreground">Writing-first</p>
                <p className="mt-2 text-sm leading-7 text-muted-foreground">
                  真正的寫作畫布、閱讀模式、附件版面與 calm save confidence 都在這裡完成。
                </p>
              </div>
              <div className="rounded-[1.6rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                <p className="text-[0.68rem] uppercase tracking-[0.26em] text-primary/80">Trust</p>
                <p className="mt-3 font-art text-[1.7rem] text-card-foreground">分享邊界</p>
                <p className="mt-2 text-sm leading-7 text-muted-foreground">
                  私密保存、原文共享、整理後版本——你決定伴侶實際會看到哪一種內容。
                </p>
              </div>
            </div>
          }
        />

        <section className="rounded-[2.3rem] border border-white/58 bg-[linear-gradient(180deg,rgba(255,255,255,0.84),rgba(248,243,236,0.76))] p-6 shadow-soft">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-2">
              <p className="text-[0.68rem] uppercase tracking-[0.32em] text-primary/80">Recent Pages</p>
              <h2 className="font-art text-[2rem] leading-tight text-card-foreground">
                最近寫下的頁面
              </h2>
              <p className="max-w-3xl text-sm leading-7 text-muted-foreground">
                這裡是更完整的反思書房，而不是只留摘要的地方。打開任何一頁，都會進入沉浸式書寫空間。
              </p>
            </div>

            <Button
              variant="secondary"
              leftIcon={<Plus className="h-4 w-4" aria-hidden />}
              onClick={openDraftStudio}
            >
              新的一頁
            </Button>
          </div>

          {journalsQuery.isLoading ? (
            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {[1, 2, 3].map((item) => (
                <div
                  key={item}
                  className="min-h-[200px] animate-pulse rounded-[1.8rem] border border-white/52 bg-white/72"
                />
              ))}
            </div>
          ) : journals.length ? (
            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {journals.map((journal) => (
                <JournalLibraryCard key={journal.id} journal={journal} />
              ))}
            </div>
          ) : (
            <div className="mt-6 rounded-[1.8rem] border border-dashed border-border/80 bg-white/62 px-5 py-8 text-sm leading-7 text-muted-foreground">
              這裡還沒有任何頁面。你可以直接在這裡開始新的一頁，或先回到 Relationship System 的 Inner Landscape 留下結構化反思。
            </div>
          )}
        </section>
      </div>
    );
  }

  return (
    <div className="pb-28 md:pb-8">
      <div className="sticky top-4 z-20 rounded-[2rem] border border-white/56 bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(247,241,234,0.88))] px-4 py-3 shadow-soft backdrop-blur-xl md:px-5">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-2.5">
            <Link
              href={detailBackHref}
              className="inline-flex items-center gap-2 rounded-full border border-white/55 bg-white/72 px-3.5 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:bg-white/86 focus-ring-premium"
            >
              返回
            </Link>
            <Link
              href="/love-map#inner-landscape"
              className="inline-flex items-center gap-2 rounded-full border border-white/55 bg-white/72 px-3.5 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:bg-white/86 focus-ring-premium"
            >
              Relationship System 反思摘要
            </Link>
            <JournalSavePill
              state={saveState}
              message={saveMessage}
              lastSavedAt={lastSavedAt}
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <JournalModeToggle
              canCompare={canCompare}
              mode={studioMode}
              onChange={setStudioMode}
            />
            <button
              type="button"
              onClick={() => {
                setDesktopShareOpen((open) => !open);
                setDesktopImagesOpen(false);
              }}
              className="hidden rounded-full border border-white/55 bg-white/72 px-3.5 py-2 text-sm font-medium text-card-foreground shadow-soft transition hover:bg-white/84 md:inline-flex"
            >
              分享設定
            </button>
            <button
              type="button"
              onClick={() => {
                setDesktopImagesOpen((open) => !open);
                setDesktopShareOpen(false);
              }}
              className="hidden rounded-full border border-white/55 bg-white/72 px-3.5 py-2 text-sm font-medium text-card-foreground shadow-soft transition hover:bg-white/84 md:inline-flex"
            >
              圖片素材
              {attachments.length ? ` · ${attachments.length}` : ''}
            </button>
            <Button
              size="sm"
              variant="outline"
              leftIcon={<Save className="h-4 w-4" aria-hidden />}
              loading={saveState === 'saving'}
              onClick={() => void persistDraft({ intent: 'auto', reason: 'manual', silent: false })}
            >
              {currentJournalId
                ? (isDraft ? '保存草稿' : '立即保存')
                : '建立這一頁'}
            </Button>
            {currentJournalId && draftHasSubstantiveContent ? (
              <Button
                size="sm"
                variant="outline"
                leftIcon={<Sparkles className="h-4 w-4" aria-hidden />}
                loading={saveState === 'saving'}
                onClick={() => void persistDraft({
                  intent: 'page',
                  reason: 'manual',
                  requestAnalysis: true,
                  silent: false,
                })}
              >
                AI 分析
              </Button>
            ) : null}
            <button
              type="button"
              onClick={() => {
                router.push('/journal');
                setDraftOpen(false);
                resetDraftState();
              }}
              className="hidden rounded-full px-3 py-2 text-sm font-medium text-muted-foreground transition hover:bg-white/70 hover:text-card-foreground md:inline-flex"
            >
              新的一頁
            </button>
            {currentJournalId ? (
              <button
                type="button"
                onClick={() => void handleDeleteJournal()}
                className="hidden rounded-full px-3 py-2 text-sm font-medium text-muted-foreground transition hover:bg-destructive/8 hover:text-destructive md:inline-flex"
              >
                刪除
              </button>
            ) : null}
          </div>
        </div>
      </div>

      <div className="mx-auto mt-6 max-w-[1180px] space-y-6 md:mt-8">
        {(desktopShareOpen || desktopImagesOpen) ? (
          <div className="hidden gap-4 md:grid lg:grid-cols-[minmax(0,0.82fr)_minmax(0,1.18fr)]">
            {desktopShareOpen ? (
              <section className="rounded-[1.9rem] border border-white/56 bg-[linear-gradient(180deg,rgba(255,255,255,0.82),rgba(248,243,236,0.78))] p-5 shadow-soft">
                <div className="space-y-1">
                  <p className="text-sm font-medium text-card-foreground">分享邊界</p>
                  <p className="text-sm leading-7 text-muted-foreground">{previewContextMessage}</p>
                </div>
                {showLegacyVisibilityNotice && legacyVisibilityMessage ? (
                  <div className="mt-4 rounded-[1.2rem] border border-primary/14 bg-primary/[0.05] px-4 py-3 text-sm leading-7 text-card-foreground">
                    {legacyVisibilityMessage}
                  </div>
                ) : null}
                <div className="mt-4">
                  <JournalVisibilitySwitch
                    value={visibility}
                    onChange={(nextVisibility) => {
                      setHasExplicitVisibilitySelection(true);
                      setVisibility(nextVisibility);
                      markUnsaved({ nextVisibility, nextIsDraft: isDraft });
                    }}
                  />
                </div>
                {translationStatusPresentation ? (
                  <div className="mt-4">
                    <JournalTranslationStatusCard presentation={translationStatusPresentation} />
                  </div>
                ) : null}
                <div className="mt-4">
                  <JournalPartnerVisibilityPanel presentation={sharingDeliveryPresentation} />
                </div>
              </section>
            ) : (
              <div />
            )}

            {desktopImagesOpen ? (
              <JournalAssetTray
                attachments={attachments}
                insertedAttachmentIds={insertedAttachmentIds}
                pending={uploadAttachmentMutation.isPending || deleteAttachmentMutation.isPending}
                onInsert={(attachment) => {
                  const insertionResult = insertAttachmentIntoDraft({
                    attachment,
                    baseContent: content,
                  });
                  const nextMarkdown = insertionResult.nextMarkdown;
                  commitContentState(nextMarkdown);
                  markUnsaved({ nextContent: nextMarkdown, nextIsDraft: isDraft });
                  if (insertionResult.usedFallback) {
                    suppressBlankEditorSyncRef.current = true;
                    setEditorSeed((seed) => seed + 1);
                  }
                }}
                onRemove={(attachment) => void handleDeleteAttachment(attachment)}
              />
            ) : (
              <div />
            )}
          </div>
        ) : null}

        {importWarning ? (
          <div className="mx-auto max-w-[46rem] rounded-[1.5rem] border border-primary/14 bg-primary/[0.055] px-5 py-4 text-sm leading-7 text-card-foreground">
            {importWarning}
          </div>
        ) : null}

        {saveError ? (
          <div className="mx-auto max-w-[46rem] rounded-[1.5rem] border border-destructive/16 bg-destructive/[0.06] px-5 py-4 text-sm leading-7 text-destructive">
            {saveError}
          </div>
        ) : null}

        <section className="mx-auto w-full max-w-[42rem] space-y-4 pt-4 md:space-y-5 md:pt-8">
          <div className="flex flex-wrap items-center gap-2.5 text-sm text-muted-foreground">
            <span>{currentDateLabel}</span>
            <span className="text-border">•</span>
            <span>{visibilityLabel}</span>
            {translationStatusPresentation ? (
              <>
                <span className="text-border">•</span>
                <JournalTranslationStatusChip presentation={translationStatusPresentation} />
              </>
            ) : null}
            <span className="text-border">•</span>
            <span>{paragraphCount} 段</span>
            <span className="text-border">•</span>
            <span>{content.length}/{MAX_JOURNAL_CONTENT_LENGTH}</span>
          </div>

          <div
            id={titleSection ? `journal-write-section-${titleSection.id}` : undefined}
            data-journal-section-id={titleSection?.id ?? undefined}
            data-journal-surface={titleSection ? 'write' : undefined}
            data-testid={titleSection ? `journal-write-section-${titleSection.id}` : undefined}
            className="scroll-mt-32 md:scroll-mt-40"
          >
            <input
              aria-label="Journal title"
              type="text"
              value={title}
              onChange={(event) => {
                const nextTitle = event.target.value;
                titleRef.current = nextTitle;
                setTitle(nextTitle);
                markUnsaved({ nextTitle, nextIsDraft: isDraft });
              }}
              placeholder="這一頁，想被叫作什麼？"
              maxLength={120}
              ref={titleInputRef}
              className="w-full bg-transparent font-art text-[2.8rem] leading-[0.98] tracking-[-0.035em] text-card-foreground outline-none placeholder:text-muted-foreground/42 md:text-[4rem]"
            />
          </div>

          <p className="max-w-[34rem] text-sm leading-7 text-muted-foreground">
            {currentJournalId
              ? 'Journal 會保留更完整的反思寫作；Relationship System 只留下結構化摘要，不會把這一頁直接變成 shared truth。'
              : '你可以先留下文字，也可以先放進圖片。這裡會先幫你建立草稿，慢慢把這一頁寫完整，而 Relationship System 只會保留你願意留下的結構化反思。'}
          </p>
        </section>

        {showDocumentMap ? (
          <div className="mx-auto w-full max-w-[42rem]">
            <JournalDocumentMap
              activeSectionId={activeSectionId}
              entries={journalSections}
              starters={showReflectionStarters ? REFLECTION_SECTION_STARTERS : []}
              onInsertStarter={handleInsertReflectionSection}
              onSelect={handleSelectDocumentMapEntry}
            />
          </div>
        ) : null}

        {studioMode === 'read' ? (
          <div className="mx-auto w-full max-w-[46rem]">
            <JournalRereadingGuide
              activeSectionId={activeSectionId}
              guide={rereadGuide}
              onSelect={handleSelectRereadGuideSection}
            />
          </div>
        ) : null}

        <div
          className={
            studioMode === 'compare' && canCompare
              ? 'grid gap-8 xl:grid-cols-[minmax(0,42rem)_minmax(0,1fr)] xl:items-start xl:gap-12'
              : 'space-y-8'
          }
        >
          {studioMode !== 'read' ? (
            <div className="mx-auto w-full max-w-[42rem]">
              <JournalCanvasFrame>
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/56 px-6 py-4 md:px-8">
                  <p className="text-sm leading-7 text-muted-foreground">
                    用 <span className="font-medium text-card-foreground">/</span> 插入段落結構，選取文字後會浮出精簡格式工具。
                  </p>
                  <button
                    type="button"
                    disabled={draftBootstrapPending}
                    onClick={handleImagePickerRequest}
                    className="hidden rounded-full border border-white/55 bg-white/74 px-3.5 py-2 text-sm font-medium text-card-foreground shadow-soft transition hover:bg-white/84 disabled:cursor-not-allowed disabled:opacity-60 md:inline-flex"
                  >
                    {draftBootstrapPending
                      ? '準備草稿中…'
                      : uploadAttachmentMutation.isPending
                        ? '插圖中…'
                        : '插入圖片'}
                  </button>
                </div>
                <JournalLexicalComposer
                  key={editorKey}
                  ref={editorRef}
                  attachments={attachments}
                  autoFocus
                  headingEntries={headingEntries}
                  initialMarkdown={content}
                  onAttachmentCaptionChange={handleAttachmentCaptionChange}
                  onChange={syncEditorMarkdown}
                  onFilesDropped={handleAttachmentUpload}
                  onImportWarning={(warning) => {
                    if (warning) {
                      logClientError('journal_markdown_import_failed', new Error(warning));
                    }
                    setImportWarning(warning);
                  }}
                  onRequestImage={handleImagePickerRequest}
                />
              </JournalCanvasFrame>
            </div>
          ) : null}

          {studioMode !== 'write' ? (
            <div
              ref={readSurfaceRef}
              className={studioMode === 'compare' ? 'w-full' : 'mx-auto w-full max-w-[46rem]'}
            >
              <JournalReadSurface
                attachments={attachments}
                content={content}
                headingEntries={headingEntries}
                meta={`${currentDateLabel} · ${visibilityLabel}`}
                surface="read"
                title={activeTitle}
                titleSectionId={titleSection?.id ?? titleEntry?.id ?? null}
                variant={studioMode === 'compare' ? 'compare' : 'default'}
              />
            </div>
          ) : null}
        </div>
      </div>

      <input
        data-testid="journal-file-input"
        ref={fileInputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp,image/gif,.png,.jpg,.jpeg,.webp,.gif"
        className="hidden"
        multiple
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          if (!files.length) return;
          void handleAttachmentUpload(files);
        }}
      />

      <JournalMobileDock
        imageCount={attachments.length}
        onFormat={() => setMobileSheet('format')}
        onImages={() => setMobileSheet('images')}
        onVisibility={() => setMobileSheet('share')}
      />

      <JournalMobileSheet
        open={mobileSheet === 'format'}
        onClose={() => setMobileSheet(null)}
        title="格式"
        description="讓手機版也能安靜地整理標題、清單、引用與行內語氣。"
      >
        <div className="space-y-5">
          <div className="space-y-2">
            <p className="text-sm font-medium text-card-foreground">段落結構</p>
            <div className="space-y-2">
              {MOBILE_BLOCK_ACTIONS.map((action) => (
                <button
                  key={action.action}
                  type="button"
                  onClick={() => handleMobileBlockFormat(action.action)}
                  className="flex w-full items-start justify-between gap-4 rounded-[1.3rem] border border-white/56 bg-white/72 px-4 py-3 text-left shadow-soft"
                >
                  <span className="space-y-1">
                    <span className="block text-sm font-medium text-card-foreground">{action.label}</span>
                    <span className="block text-xs leading-6 text-muted-foreground">{action.note}</span>
                  </span>
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium text-card-foreground">文字語氣</p>
            <div className="grid grid-cols-3 gap-2">
              {MOBILE_INLINE_ACTIONS.map((action) => (
                <button
                  key={action.format}
                  type="button"
                  onClick={() => handleMobileInlineFormat(action.format)}
                  className="rounded-full border border-white/56 bg-white/76 px-3 py-2.5 text-sm font-medium text-card-foreground shadow-soft"
                >
                  {action.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </JournalMobileSheet>

      <JournalMobileSheet
        open={mobileSheet === 'share'}
        onClose={() => setMobileSheet(null)}
        title="分享設定"
        description={previewContextMessage}
      >
        {showLegacyVisibilityNotice && legacyVisibilityMessage ? (
          <div className="mb-4 rounded-[1.2rem] border border-primary/14 bg-primary/[0.05] px-4 py-3 text-sm leading-7 text-card-foreground">
            {legacyVisibilityMessage}
          </div>
        ) : null}
        <JournalVisibilitySwitch
          value={visibility}
          onChange={(nextVisibility) => {
            setHasExplicitVisibilitySelection(true);
            setVisibility(nextVisibility);
            markUnsaved({ nextVisibility, nextIsDraft: isDraft });
            setMobileSheet(null);
          }}
        />
        {translationStatusPresentation ? (
          <div className="mt-4">
            <JournalTranslationStatusCard presentation={translationStatusPresentation} />
          </div>
        ) : null}
        <div className="mt-4">
          <JournalPartnerVisibilityPanel presentation={sharingDeliveryPresentation} />
        </div>
      </JournalMobileSheet>

      <JournalMobileSheet
        open={mobileSheet === 'images'}
        onClose={() => setMobileSheet(null)}
        title="圖片素材"
        description="圖片會先收進素材層，再被放進正文節奏裡。"
      >
        <div className="space-y-4">
          <Button
            variant="outline"
            leftIcon={<Plus className="h-4 w-4" aria-hidden />}
            disabled={uploadAttachmentMutation.isPending || draftBootstrapPending}
            onClick={handleImagePickerRequest}
          >
            {draftBootstrapPending
              ? '準備草稿中…'
              : uploadAttachmentMutation.isPending
                ? '上傳中…'
                : '新增圖片'}
          </Button>
          <JournalAssetTray
            attachments={attachments}
            insertedAttachmentIds={insertedAttachmentIds}
            pending={uploadAttachmentMutation.isPending || deleteAttachmentMutation.isPending}
            onInsert={(attachment) => {
              const insertionResult = insertAttachmentIntoDraft({
                attachment,
                baseContent: content,
              });
              const nextMarkdown = insertionResult.nextMarkdown;
              commitContentState(nextMarkdown);
              markUnsaved({ nextContent: nextMarkdown, nextIsDraft: isDraft });
              if (insertionResult.usedFallback) {
                suppressBlankEditorSyncRef.current = true;
                setEditorSeed((seed) => seed + 1);
              }
              setMobileSheet(null);
            }}
            onRemove={(attachment) => void handleDeleteAttachment(attachment)}
          />
        </div>
      </JournalMobileSheet>
    </div>
  );
}
