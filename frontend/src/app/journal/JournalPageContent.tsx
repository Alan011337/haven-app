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
import type { JournalAttachmentPublic, JournalVisibility } from '@/types';
import { queryKeys } from '@/lib/query-keys';
import { deriveJournalTitle } from '@/lib/journal-format';
import { logClientError } from '@/lib/safe-error-log';
import { MAX_JOURNAL_CONTENT_LENGTH } from '@/services/api-client';
import {
  JournalAssetTray,
  JournalBackLink,
  JournalCanvasFrame,
  JournalLibraryCard,
  JournalMobileDock,
  JournalMobileSheet,
  JournalModeToggle,
  JournalReadSurface,
  JournalSavePill,
  JournalStatePanel,
  JournalStudioHero,
  JournalVisibilitySwitch,
  type JournalSaveState,
  type JournalStudioMode,
} from '@/app/journal/JournalPrimitives';
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

const DEFAULT_VISIBILITY: JournalVisibility = 'PARTNER_TRANSLATED_ONLY';
const JOURNAL_HOME_SEED_STORAGE_KEY = 'haven_journal_home_seed_v1';
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

interface JournalPageContentProps {
  journalId?: string;
}

interface PersistJournalDraftResult {
  content: string;
  isDraft: boolean;
  journalId: string;
}

export default function JournalPageContent({ journalId }: JournalPageContentProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const titleInputRef = useRef<HTMLInputElement | null>(null);
  const editorRef = useRef<JournalLexicalComposerHandle | null>(null);
  const autoDraftBootstrapRef = useRef(false);
  const hydratedJournalIdRef = useRef<string | null>(null);
  const contentRef = useRef('');
  const titleRef = useRef('');
  const visibilityRef = useRef<JournalVisibility>(DEFAULT_VISIBILITY);
  const suppressBlankEditorSyncRef = useRef(false);
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
  const [editorSeed, setEditorSeed] = useState(0);
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<JournalSaveState>('draft');
  const [saveError, setSaveError] = useState<string | null>(null);
  const [importWarning, setImportWarning] = useState<string | null>(null);
  const [studioMode, setStudioMode] = useState<JournalStudioMode>('write');
  const [canCompare, setCanCompare] = useState(false);
  const [desktopImagesOpen, setDesktopImagesOpen] = useState(false);
  const [desktopShareOpen, setDesktopShareOpen] = useState(false);
  const [mobileSheet, setMobileSheet] = useState<'format' | 'images' | 'share' | null>(null);

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
  const showStudio = Boolean(journalId) || draftOpen;
  const draftBootstrapPending = !currentJournalId && createJournalMutation.isPending;
  const editorKey = `${currentJournalId ?? `draft:${draftOpen ? 'open' : 'closed'}`}:${editorSeed}`;
  const currentDateLabel = new Date(
    lastSavedAt ?? activeJournal?.updated_at ?? activeJournal?.created_at ?? Date.now(),
  ).toLocaleDateString('zh-TW', {
    month: 'long',
    day: 'numeric',
  });
  const visibilityLabel =
    visibility === 'PRIVATE'
      ? '只留給自己'
      : visibility === 'PARTNER_ORIGINAL'
        ? '伴侶看原文'
        : '伴侶只看 AI 譯文';
  const shouldAutoOpenDraft = searchParams.get('compose') === '1';

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
    savedSnapshotRef.current = incomingSnapshot;
    suppressBlankEditorSyncRef.current = true;
    setDraftOpen(true);
    commitTitleState(nextTitle);
    commitContentState(nextContent);
    setIsDraft(nextIsDraft);
    setVisibility(nextVisibility);
    setAttachments(nextAttachments);
    setLastSavedAt(activeJournal.updated_at ?? activeJournal.created_at);
    setSaveState('saved');
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
    commitTitleState('');
    commitContentState('');
    setIsDraft(false);
    setVisibility(DEFAULT_VISIBILITY);
    setAttachments([]);
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
      silent,
    }: {
      intent?: 'auto' | 'draft' | 'page';
      navigate?: boolean;
      reason: 'autosave' | 'manual';
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
          showToast('先留下一段內容，這一頁才能真正被保存。', 'error');
        }
        setSaveState(currentJournalId ? (isDraft ? 'dirty' : 'error') : 'draft');
        return null;
      }

      try {
        setSaveState('saving');
        setSaveError(null);

        if (currentJournalId) {
          const payload = buildUpdateJournalPayload({
            content: currentContent,
            isDraft: targetIsDraft,
            title: currentTitle,
            visibility: visibilityRef.current,
          });
          const updated = await updateJournalMutation.mutateAsync({
            id: currentJournalId,
            payload,
          });

          const resolvedAttachments = updated.attachments ?? attachments;
          const resolvedContent = updated.content ?? payload.content ?? currentContent;
          const resolvedIsDraft = Boolean(updated.is_draft ?? targetIsDraft);
          const resolvedTitle = updated.title?.trim() ?? currentTitle;
          const resolvedVisibility = updated.visibility ?? visibilityRef.current;

          savedSnapshotRef.current = buildSnapshot({
            attachments: resolvedAttachments,
            content: resolvedContent,
            isDraft: resolvedIsDraft,
            title: resolvedTitle,
            visibility: resolvedVisibility,
          });
          setAttachments(resolvedAttachments);
          commitContentState(resolvedContent);
          setIsDraft(resolvedIsDraft);
          commitTitleState(resolvedTitle);
          setVisibility(resolvedVisibility);
          setLastSavedAt(updated.updated_at ?? updated.created_at);
          setSaveState('saved');
          return {
            content: resolvedContent,
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
        const resolvedIsDraft = Boolean(created.is_draft ?? targetIsDraft);
        const resolvedTitle = created.title?.trim() ?? currentTitle;
        const resolvedContent = created.content ?? draft.content;
        const resolvedVisibility = created.visibility ?? visibilityRef.current;
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
        queryClient.setQueryData(queryKeys.journalDetail(created.id), created);
        setAttachments(resolvedAttachments);
        commitContentState(nextContentState);
        setIsDraft(resolvedIsDraft);
        commitTitleState(nextTitleState);
        setVisibility(nextVisibilityState);
        setLastSavedAt(created.updated_at ?? created.created_at);
        setSaveState(hasLocalEditsSinceSubmit ? 'dirty' : 'saved');
        setDraftOpen(true);

        if (navigate) {
          router.push(`/journal/${created.id}`);
        }

        if (!silent && reason === 'manual') {
          showToast(
            resolvedIsDraft ? '新的草稿頁已經準備好。' : '新的 Journal page 已經安靜收進書房。',
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
      attachments,
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
        ? (isDraft ? '草稿已保存' : '已保存')
        : saveState === 'error'
          ? '保存失敗'
          : saveState === 'dirty'
            ? currentJournalId
              ? (isDraft ? '草稿有新變更' : '未儲存變更')
              : '草稿未保存'
            : '草稿';

  const previewContextMessage =
    visibility === 'PRIVATE'
      ? '這一頁只留在你自己的書房裡。'
      : visibility === 'PARTNER_ORIGINAL'
        ? '伴侶會看到這份原文與同一組圖片。'
        : '伴侶只會收到 Haven 整理後的譯文與同一組圖片。';

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
        setSaveError('移除圖片失敗，請稍後再試。');
        logClientError('journal_attachment_remove_failed', error);
        showToast('移除失敗，請稍後再試。', 'error');
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
      showToast('這篇 Journal 已刪除。', 'info');
      resetDraftState();
      setDraftOpen(false);
      router.push('/journal');
    } catch {
      showToast('刪除失敗，請稍後再試。', 'error');
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
              href="/journal"
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
        <JournalBackLink href="/" />

        <JournalStudioHero
          eyebrow="Journal Library"
          title="把值得留下來的心事，寫成真正可重讀的一頁。"
          description="Home 還是最好的第一筆，但 Journal V3 現在是一個真正的 writing studio。你可以在這裡整理標題、節奏、圖像、分享邊界，讓一頁日記慢慢長成作品。"
          actions={
            <>
              <Button
                leftIcon={<Plus className="h-4 w-4" aria-hidden />}
                onClick={openDraftStudio}
              >
                開始新的一頁
              </Button>
              <Link
                href="/"
                className="inline-flex items-center justify-center gap-2 rounded-full border border-white/58 bg-white/82 px-5 py-3 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
              >
                回 Home quick capture
              </Link>
            </>
          }
          aside={
            <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
              <div className="rounded-[1.6rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                <p className="text-[0.68rem] uppercase tracking-[0.26em] text-primary/80">Library</p>
                <p className="mt-3 font-art text-[1.7rem] text-card-foreground">{journals.length} 篇</p>
                <p className="mt-2 text-sm leading-7 text-muted-foreground">
                  所有私人頁面、原文共享與 AI 譯文共享，都回到同一個書房管理。
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
                <p className="mt-3 font-art text-[1.7rem] text-card-foreground">3 種分享邊界</p>
                <p className="mt-2 text-sm leading-7 text-muted-foreground">
                  private、partner original、partner translated only 都被拉進同一個寫作決策裡。
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
                這裡是一個真正的書房，不再只是 Home timeline 的延伸。打開任何一頁，都會進入沉浸式 writing studio。
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
              這裡還沒有任何頁面。你可以先從 Home 留下第一段，或直接在這裡開始新的一頁。
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
              href={currentJournalId ? '/journal' : '/'}
              className="inline-flex items-center gap-2 rounded-full border border-white/55 bg-white/72 px-3.5 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:bg-white/86 focus-ring-premium"
            >
              返回
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
                ? (isDraft ? (draftHasSubstantiveContent ? '完成這一頁' : '保存草稿') : '立即保存')
                : '建立這一頁'}
            </Button>
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
                <div className="mt-4">
                  <JournalVisibilitySwitch
                    value={visibility}
                    onChange={(nextVisibility) => {
                      setVisibility(nextVisibility);
                      markUnsaved({ nextVisibility, nextIsDraft: isDraft });
                    }}
                  />
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
            <span className="text-border">•</span>
            <span>{paragraphCount} 段</span>
            <span className="text-border">•</span>
            <span>{content.length}/{MAX_JOURNAL_CONTENT_LENGTH}</span>
          </div>

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

          <p className="max-w-[34rem] text-sm leading-7 text-muted-foreground">
            {currentJournalId
              ? '先把內容寫順，再決定要不要共享。工具會退到後面，讓這一頁自己長出節奏。'
              : '你可以先留下文字，也可以先放進圖片。這裡先幫你建立草稿，之後再慢慢把這一頁寫完整。'}
          </p>
        </section>

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
                  initialMarkdown={content}
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
            <div className={studioMode === 'compare' ? 'w-full' : 'mx-auto w-full max-w-[46rem]'}>
              <JournalReadSurface
                attachments={attachments}
                content={content}
                meta={`${currentDateLabel} · ${visibilityLabel}`}
                title={activeTitle}
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
        <JournalVisibilitySwitch
                    value={visibility}
                    onChange={(nextVisibility) => {
                      setVisibility(nextVisibility);
                      markUnsaved({ nextVisibility, nextIsDraft: isDraft });
                      setMobileSheet(null);
                    }}
                  />
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
