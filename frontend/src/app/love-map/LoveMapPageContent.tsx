'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { HeartHandshake, Sparkles } from 'lucide-react';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Input, { Textarea } from '@/components/ui/Input';
import {
  useLoveMapCards,
  useLoveMapSharedFutureRefinements,
  useLoveMapSharedFutureSuggestions,
  useLoveMapSystem,
} from '@/hooks/queries';
import { useToast } from '@/hooks/useToast';
import { queryKeys } from '@/lib/query-keys';
import { logClientError } from '@/lib/safe-error-log';
import { cn } from '@/lib/utils';
import {
  acceptLoveMapSharedFutureSuggestion,
  addBlueprintItem,
  completeWeeklyTask,
  createOrUpdateLoveMapNote,
  dismissLoveMapSharedFutureSuggestion,
  generateLoveMapSharedFutureCadenceRefinement,
  generateLoveMapSharedFutureRefinement,
  generateLoveMapSharedFutureSuggestions,
  generateLoveMapStoryAdjacentRitualSuggestion,
  LOVE_LANGUAGE_OPTIONS,
  normalizeLoveLanguagePreference,
  upsertLoveMapHeartProfile,
  type LoveMapHeartProfileUpsertPayload,
  type LoveLanguagePreferenceKey,
  type LoveLanguagePreferenceRecord,
  type LoveMapCardSummary,
  type RelationshipKnowledgeSuggestionPublic,
} from '@/services/api-client';
import {
  BASELINE_DIMENSIONS,
  setCoupleGoal,
  upsertBaseline,
} from '@/services/relationship-api';
import { updateUserMe } from '@/services/user';
import LoveMapSkeleton from './LoveMapSkeleton';
import {
  LoveMapEssentialField,
  LoveMapFutureComposer,
  LoveMapKnowledgeBlock,
  LoveMapPromptCard,
  LoveMapRefinementSuggestionCard,
  LoveMapReflectionStudio,
  LoveMapSection,
  LoveMapSharedFutureNotesPanel,
  LoveMapSnapshotCard,
  LoveMapStatePanel,
  LoveMapStoryCapsuleCard,
  LoveMapStoryMomentCard,
  LoveMapSuggestedUpdateCard,
  LoveMapSystemCover,
  LoveMapSystemGuide,
  LoveMapSystemGuideCard,
} from './LoveMapPrimitives';

const LAYERS = ['safe', 'medium', 'deep'] as const;
type LoveMapLayer = (typeof LAYERS)[number];

const DEFAULT_BASELINE_SCORES = Object.fromEntries(
  BASELINE_DIMENSIONS.map((dimension) => [dimension, 3]),
) as Record<string, number>;

const DIMENSION_LABELS: Record<string, string> = {
  intimacy: '親密感',
  conflict: '衝突處理',
  trust: '信任',
  communication: '溝通',
  commitment: '承諾',
};

const DIMENSION_HELPERS: Record<string, string> = {
  intimacy: '你們最近有多常感到靠近與願意分享。',
  conflict: '遇到摩擦時，你們有多能回到同一邊。',
  trust: '現在的關係有多讓你感到安心與可依靠。',
  communication: '想法與需求能否被說清楚、聽進去。',
  commitment: '你們是否都在主動照顧這段關係。',
};

const GOAL_OPTIONS = [
  { value: 'reduce_argument', label: '減少爭吵', description: '把情緒升高前的修復做得更早。' },
  { value: 'increase_intimacy', label: '提升親密感', description: '讓溫柔、靠近與分享更容易發生。' },
  { value: 'better_communication', label: '更好溝通', description: '讓彼此更懂得怎麼說、怎麼聽。' },
  { value: 'more_trust', label: '更多信任', description: '把安全感和可依靠感慢慢養厚。' },
  { value: 'other', label: '其他', description: '先訂一個方向，之後再細化。' },
] as const;

const LOVE_LANGUAGE_LABELS: Record<LoveLanguagePreferenceKey, string> = {
  words: '肯定話語',
  acts: '服務行動',
  gifts: '收到禮物',
  time: '專注陪伴',
  touch: '身體接觸',
};

const EMPTY_HEART_PLAYBOOK_DRAFT: LoveMapHeartProfileUpsertPayload = {
  primary: null,
  secondary: null,
  support_me: '',
  avoid_when_stressed: '',
  small_delights: '',
};

type SharedFutureRefinementKind = 'next_step' | 'cadence';

const LAYER_META: Record<
  LoveMapLayer,
  {
    label: string;
    eyebrow: string;
    title: string;
    description: string;
    placeholder: string;
    helperText: string;
  }
> = {
  safe: {
    label: '安全層',
    eyebrow: 'Outer Edge',
    title: '先把安心、偏好與相處節奏留下來。',
    description: '這一層是你怎麼理解這段關係的日常安全感。不是共享真相，而是你此刻讀到的輪廓。',
    placeholder: '寫下你已經知道、但平常不一定會完整說出的安全感細節與相處節奏...',
    helperText: '先記錄那些會讓兩個人比較容易靠近、比較不容易受傷的部分。',
  },
  medium: {
    label: '中層',
    eyebrow: 'Shared Middle',
    title: '把彼此真正正在在意的事寫清楚。',
    description: '這裡適合放那些不是表面偏好，而是價值感、壓力來源、被理解方式的內容。',
    placeholder: '寫下最近真正重要的在意、壓力、需求，或你希望被理解的方式...',
    helperText: '這一層比表面更內一點，但仍然是你的反思，不是 Haven 自動認定的雙方真理。',
  },
  deep: {
    label: '深層',
    eyebrow: 'Inner Terrain',
    title: '替脆弱與核心期待留一個安靜位置。',
    description: '只要寫下今天願意被看見的一小塊就夠了。深層不是更多內容，而是更真實。',
    placeholder: '寫下那些只有在足夠信任時，才願意說出口的核心期待、脆弱或長久在意...',
    helperText: '慢慢寫就好。這裡重點不是完整，而是誠實。',
  },
};

function formatShortDateTime(iso?: string | null) {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat('zh-TW', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function formatStoryDate(iso?: string | null) {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat('zh-TW', {
    month: 'numeric',
    day: 'numeric',
  }).format(date);
}

function formatStoryRange(fromDate?: string | null, toDate?: string | null) {
  if (!fromDate || !toDate) return '去年同一段時間';
  const from = new Date(fromDate);
  const to = new Date(toDate);
  if (Number.isNaN(from.getTime()) || Number.isNaN(to.getTime())) {
    return '去年同一段時間';
  }
  return `${new Intl.DateTimeFormat('zh-TW', { month: 'numeric', day: 'numeric' }).format(from)} - ${new Intl.DateTimeFormat('zh-TW', { month: 'numeric', day: 'numeric' }).format(to)}`;
}

function storyMomentHref(moment: { kind: string; source_id?: string | null; occurred_at?: string }): string | null {
  if (!moment.source_id) return null;
  if (moment.kind === 'journal') return `/journal/${moment.source_id}`;
  const dateMatch = moment.occurred_at?.match(/^\d{4}-\d{2}-\d{2}/);
  if (dateMatch) {
    return `/memory?date=${dateMatch[0]}&kind=${moment.kind}&id=${moment.source_id}`;
  }
  return null;
}

function getGoalLabel(goalSlug?: string | null) {
  return GOAL_OPTIONS.find((option) => option.value === goalSlug)?.label ?? '尚未設定';
}

function getLoveLanguageLabel(value?: LoveLanguagePreferenceKey | null) {
  if (!value) return '尚未設定';
  return LOVE_LANGUAGE_LABELS[value];
}

function describeLoveLanguagePreference(
  preference?: LoveLanguagePreferenceRecord | null,
  emptyLabel = '尚未設定',
) {
  if (!preference?.primary) return emptyLabel;
  return preference.secondary
    ? `${getLoveLanguageLabel(preference.primary)} · 次要是 ${getLoveLanguageLabel(preference.secondary)}`
    : getLoveLanguageLabel(preference.primary);
}

function buildHeartPlaybookDraft(
  preference?: LoveLanguagePreferenceRecord | null,
  profile?: {
    support_me?: string | null;
    avoid_when_stressed?: string | null;
    small_delights?: string | null;
  } | null,
): LoveMapHeartProfileUpsertPayload {
  const normalizedPreference = normalizeLoveLanguagePreference(preference);
  return {
    primary: normalizedPreference.primary,
    secondary: normalizedPreference.secondary,
    support_me: profile?.support_me ?? '',
    avoid_when_stressed: profile?.avoid_when_stressed ?? '',
    small_delights: profile?.small_delights ?? '',
  };
}

function countCareCueCompletion(
  preference?: LoveLanguagePreferenceRecord | null,
  profile?: {
    support_me?: string | null;
    avoid_when_stressed?: string | null;
    small_delights?: string | null;
  } | null,
) {
  let count = 0;
  if (preference?.primary) count += 1;
  if (preference?.secondary) count += 1;
  if (profile?.support_me?.trim()) count += 1;
  if (profile?.avoid_when_stressed?.trim()) count += 1;
  if (profile?.small_delights?.trim()) count += 1;
  return count;
}

function formatCareCueCountLabel(count: number) {
  return `已留下 ${count}/5 個 care cues`;
}

function normalizeCadenceEligibilityText(value: string) {
  return value.normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, ' ').replace(/\s+/g, ' ').trim();
}

function supportsCadenceRefinement(title: string, notes: string) {
  const normalized = normalizeCadenceEligibilityText(`${title} ${notes}`);
  if (!normalized) return false;

  const recurrenceCues = [
    '每個月',
    '每月',
    '每週',
    '每周',
    '每年',
    '每百天',
    '每天',
    '每日',
    '固定',
    '定期',
    '習慣',
    '儀式',
    '節奏',
    '週末',
    '周末',
    '衝突後',
    '爭執後',
    '吵架後',
    '摩擦後',
    '修復',
  ];

  return recurrenceCues.some((cue) => normalized.includes(cue));
}

function getRefinementKind(generatorVersion: string): SharedFutureRefinementKind {
  return generatorVersion === 'shared_future_refinement_cadence_v1' ? 'cadence' : 'next_step';
}

function getSharedFutureSuggestionVariant(generatorVersion: string): 'default' | 'story_ritual' {
  return generatorVersion === 'shared_future_story_ritual_v1' ? 'story_ritual' : 'default';
}

function scoreLabel(score?: number | null) {
  if (!score) return '未填寫';
  return `${score} / 5`;
}

export default function LoveMapPageContent() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const systemQuery = useLoveMapSystem();
  const cardsQuery = useLoveMapCards();
  const suggestionQuery = useLoveMapSharedFutureSuggestions({
    enabled: Boolean(systemQuery.data?.has_partner),
  });
  const refinementQuery = useLoveMapSharedFutureRefinements({
    enabled: Boolean(systemQuery.data?.has_partner),
  });

  const [savingLayer, setSavingLayer] = useState<LoveMapLayer | null>(null);
  const [savingBaseline, setSavingBaseline] = useState(false);
  const [savingGoal, setSavingGoal] = useState(false);
  const [savingWishlist, setSavingWishlist] = useState(false);
  const [savingIdentity, setSavingIdentity] = useState(false);
  const [savingHeartPlaybook, setSavingHeartPlaybook] = useState(false);
  const [completingWeeklyTask, setCompletingWeeklyTask] = useState(false);
  const [generatingSuggestions, setGeneratingSuggestions] = useState(false);
  const [generatingStoryRitual, setGeneratingStoryRitual] = useState(false);
  const [generatingRefinement, setGeneratingRefinement] = useState<{
    itemId: string;
    kind: SharedFutureRefinementKind;
  } | null>(null);
  const [reviewingSuggestionId, setReviewingSuggestionId] = useState<string | null>(null);
  const [reviewingAction, setReviewingAction] = useState<'accept' | 'dismiss' | null>(null);
  const [noteDrafts, setNoteDrafts] = useState<Record<LoveMapLayer, string>>({
    safe: '',
    medium: '',
    deep: '',
  });
  const [baselineDraft, setBaselineDraft] = useState<Record<string, number>>(DEFAULT_BASELINE_SCORES);
  const [goalDraft, setGoalDraft] = useState<string>('');
  const [wishTitle, setWishTitle] = useState('');
  const [wishNotes, setWishNotes] = useState('');
  const [displayNameDraft, setDisplayNameDraft] = useState('');
  const [heartPlaybookDraft, setHeartPlaybookDraft] =
    useState<LoveMapHeartProfileUpsertPayload>(EMPTY_HEART_PLAYBOOK_DRAFT);

  useEffect(() => {
    if (!systemQuery.data) {
      return;
    }

    const nextDrafts = LAYERS.reduce<Record<LoveMapLayer, string>>(
      (acc, layer) => {
        acc[layer] = systemQuery.data?.notes.find((note) => note.layer === layer)?.content ?? '';
        return acc;
      },
      { safe: '', medium: '', deep: '' },
    );
    setNoteDrafts(nextDrafts);
    setBaselineDraft({
      ...DEFAULT_BASELINE_SCORES,
      ...(systemQuery.data.baseline.mine?.scores ?? {}),
    });
    setGoalDraft(systemQuery.data.couple_goal?.goal_slug ?? '');
    setDisplayNameDraft(systemQuery.data.me.full_name ?? '');
    setHeartPlaybookDraft(
      buildHeartPlaybookDraft(
        systemQuery.data.essentials?.my_care_preferences,
        systemQuery.data.essentials?.my_care_profile,
      ),
    );
  }, [systemQuery.data]);

  const cardsByLayer = useMemo<Record<LoveMapLayer, LoveMapCardSummary[]>>(
    () => ({
      safe: cardsQuery.data?.safe ?? [],
      medium: cardsQuery.data?.medium ?? [],
      deep: cardsQuery.data?.deep ?? [],
    }),
    [cardsQuery.data],
  );

  const system = systemQuery.data;

  const goToSettings = () => {
    if (typeof window !== 'undefined') {
      window.location.href = '/settings#settings-relationship';
    }
  };

  const handleRefresh = () => {
    void Promise.all([systemQuery.refetch(), cardsQuery.refetch()]);
  };

  const invalidateRelationshipViews = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.loveMapSystem() }),
      queryClient.invalidateQueries({ queryKey: queryKeys.loveMapNotes() }),
      queryClient.invalidateQueries({ queryKey: queryKeys.loveMapSharedFutureSuggestions() }),
      queryClient.invalidateQueries({ queryKey: queryKeys.loveMapSharedFutureRefinements() }),
      queryClient.invalidateQueries({ queryKey: queryKeys.blueprint() }),
      queryClient.invalidateQueries({ queryKey: ['settings', 'relationship'] }),
      queryClient.invalidateQueries({ queryKey: ['settings', 'me'] }),
    ]);
  };

  const handleSaveIdentity = async () => {
    setSavingIdentity(true);
    try {
      const trimmedName = displayNameDraft.trim();
      await updateUserMe({ full_name: trimmedName || null });
      await invalidateRelationshipViews();
      showToast('Identity 已更新。', 'success');
    } catch (error) {
      logClientError('love-map-identity-save-failed', error);
      showToast('這次沒有順利更新你的名稱，稍後再試一次。', 'error');
    } finally {
      setSavingIdentity(false);
    }
  };

  const handleSaveHeartPlaybook = async () => {
    if (!heartPlaybookDraft.primary) {
      showToast('先選一個最主要的 care preference。', 'error');
      return;
    }
    setSavingHeartPlaybook(true);
    try {
      await upsertLoveMapHeartProfile(heartPlaybookDraft);
      await invalidateRelationshipViews();
      showToast('Heart Care Playbook 已更新。', 'success');
    } catch (error) {
      logClientError('love-map-heart-profile-save-failed', error);
      showToast('這次沒有順利更新 Heart Care Playbook，稍後再試一次。', 'error');
    } finally {
      setSavingHeartPlaybook(false);
    }
  };

  const handleCompleteWeeklyCareTask = async () => {
    setCompletingWeeklyTask(true);
    try {
      await completeWeeklyTask();
      await invalidateRelationshipViews();
      showToast('本週 care task 已標記完成。', 'success');
    } catch (error) {
      logClientError('love-map-weekly-care-task-complete-failed', error);
      showToast('這次沒有順利更新本週任務，稍後再試一次。', 'error');
    } finally {
      setCompletingWeeklyTask(false);
    }
  };

  const handleSaveLayer = async (layer: LoveMapLayer) => {
    setSavingLayer(layer);
    try {
      await createOrUpdateLoveMapNote(layer, noteDrafts[layer]);
      await invalidateRelationshipViews();
      showToast(`${LAYER_META[layer].label} 已收好。`, 'success');
    } catch (error) {
      logClientError('love-map-layer-save-failed', error);
      showToast('這一層暫時沒有順利收好，稍後再試一次。', 'error');
    } finally {
      setSavingLayer(null);
    }
  };

  const handleSaveBaseline = async () => {
    setSavingBaseline(true);
    try {
      await upsertBaseline(baselineDraft);
      await invalidateRelationshipViews();
      showToast('關係脈動已重新整理。', 'success');
    } catch (error) {
      logClientError('love-map-baseline-save-failed', error);
      showToast('關係脈動這次沒有順利更新，稍後再試一次。', 'error');
    } finally {
      setSavingBaseline(false);
    }
  };

  const handleSaveGoal = async () => {
    if (!goalDraft) {
      showToast('請先選一個共同方向', 'error');
      return;
    }
    setSavingGoal(true);
    try {
      await setCoupleGoal(goalDraft);
      await invalidateRelationshipViews();
      showToast('共同方向已收好。', 'success');
    } catch (error) {
      logClientError('love-map-goal-save-failed', error);
      showToast('共同方向這次沒有順利收好，稍後再試一次。', 'error');
    } finally {
      setSavingGoal(false);
    }
  };

  const handleAddWishlist = async () => {
    if (!wishTitle.trim()) {
      showToast('請先寫下想一起靠近的未來片段', 'error');
      return;
    }
    setSavingWishlist(true);
    try {
      await addBlueprintItem(wishTitle.trim(), wishNotes.trim() || undefined);
      setWishTitle('');
      setWishNotes('');
      await invalidateRelationshipViews();
      showToast('這段未來片段已放進 Shared Future。', 'success');
    } catch (error) {
      logClientError('love-map-wishlist-add-failed', error);
      showToast('這段未來片段這次沒有順利放進 Shared Future。', 'error');
    } finally {
      setSavingWishlist(false);
    }
  };

  const handleGenerateSuggestions = async () => {
    setGeneratingSuggestions(true);
    try {
      const suggestions = await generateLoveMapSharedFutureSuggestions();
      await queryClient.invalidateQueries({ queryKey: queryKeys.loveMapSharedFutureSuggestions() });
      if (suggestions.length === 0) {
        showToast('目前還沒有足夠清楚的 Shared Future 建議。', 'info');
        return;
      }
      showToast('Haven 已整理出新的 Shared Future 提案。', 'success');
    } catch (error) {
      logClientError('love-map-shared-future-suggestions-generate-failed', error);
      showToast('Haven 暫時還整理不出新的提案，稍後再試一次。', 'error');
    } finally {
      setGeneratingSuggestions(false);
    }
  };

  const handleGenerateStoryRitualSuggestion = async () => {
    setGeneratingStoryRitual(true);
    try {
      const suggestions = await generateLoveMapStoryAdjacentRitualSuggestion();
      await queryClient.invalidateQueries({ queryKey: queryKeys.loveMapSharedFutureSuggestions() });
      if (suggestions.length === 0) {
        showToast('這段故事目前還沒有足夠清楚的 ritual 建議。', 'info');
        return;
      }
      showToast('Haven 已把這段故事的 ritual 提案放進 Shared Future 審核區。', 'success');
    } catch (error) {
      logClientError('love-map-story-ritual-suggestion-generate-failed', error);
      showToast('Haven 暫時還整理不出新的提案，稍後再試一次。', 'error');
    } finally {
      setGeneratingStoryRitual(false);
    }
  };

  const handleGenerateRefinement = async (
    wishlistItemId: string,
    kind: SharedFutureRefinementKind,
  ) => {
    setGeneratingRefinement({ itemId: wishlistItemId, kind });
    try {
      const suggestions =
        kind === 'cadence'
          ? await generateLoveMapSharedFutureCadenceRefinement(wishlistItemId)
          : await generateLoveMapSharedFutureRefinement(wishlistItemId);
      await queryClient.invalidateQueries({ queryKey: queryKeys.loveMapSharedFutureRefinements() });
      if (suggestions.length === 0) {
        showToast(
          kind === 'cadence' ? '目前還沒有足夠清楚的節奏建議。' : '目前還沒有足夠清楚的下一步建議。',
          'info',
        );
        return;
      }
      showToast(
        kind === 'cadence'
          ? 'Haven 已替這個未來片段補上一個可審核的節奏。'
          : 'Haven 已替這個未來片段補上一個可審核的下一步。',
        'success',
      );
    } catch (error) {
      logClientError('love-map-shared-future-refinement-generate-failed', error);
      showToast('Haven 暫時還整理不出新的提案，稍後再試一次。', 'error');
    } finally {
      setGeneratingRefinement(null);
    }
  };

  const handleAcceptSuggestion = async (suggestion: RelationshipKnowledgeSuggestionPublic) => {
    setReviewingSuggestionId(suggestion.id);
    setReviewingAction('accept');
    try {
      await acceptLoveMapSharedFutureSuggestion(suggestion.id);
      await invalidateRelationshipViews();
      showToast(
        suggestion.section === 'shared_future_refinement'
          ? getRefinementKind(suggestion.generator_version) === 'cadence'
            ? '節奏已加入這個 Shared Future 片段。'
            : '下一步已加入這個 Shared Future 片段。'
          : '這則提案已收進 Shared Future。',
        'success',
      );
    } catch (error) {
      logClientError('love-map-shared-future-suggestion-accept-failed', error);
      showToast('這次沒有順利收下這則提案，稍後再試一次。', 'error');
    } finally {
      setReviewingSuggestionId(null);
      setReviewingAction(null);
    }
  };

  const handleDismissSuggestion = async (suggestion: RelationshipKnowledgeSuggestionPublic) => {
    setReviewingSuggestionId(suggestion.id);
    setReviewingAction('dismiss');
    try {
      await dismissLoveMapSharedFutureSuggestion(suggestion.id);
      await queryClient.invalidateQueries({ queryKey: queryKeys.loveMapSharedFutureSuggestions() });
      await queryClient.invalidateQueries({ queryKey: queryKeys.loveMapSharedFutureRefinements() });
      showToast(
        suggestion.section === 'shared_future_refinement'
          ? getRefinementKind(suggestion.generator_version) === 'cadence'
            ? '這則節奏建議已略過。'
            : '這則下一步建議已略過。'
          : '這則提案先略過了。',
        'success',
      );
    } catch (error) {
      logClientError('love-map-shared-future-suggestion-dismiss-failed', error);
      showToast('這次沒有順利略過這則提案，稍後再試一次。', 'error');
    } finally {
      setReviewingSuggestionId(null);
      setReviewingAction(null);
    }
  };

  if (systemQuery.isLoading && !system) {
    return <LoveMapSkeleton />;
  }

  if (systemQuery.isError || !system) {
    return (
      <LoveMapStatePanel
        eyebrow="Relationship System Unavailable"
        title="這張關係地圖暫時打不開。"
        description="Haven 應該在這裡回答它目前知道什麼、還不知道什麼。現在這個讀模型沒有順利載入，重新讀取後我們會把它帶回來。"
        tone="error"
        actionLabel="重新讀取"
        onAction={handleRefresh}
      />
    );
  }

  const filledLayerCount = LAYERS.filter((layer) => noteDrafts[layer].trim().length > 0).length;
  const lastActivityLabel = formatShortDateTime(system.stats.last_activity_at);
  const storyAnchorCount = system.story?.moments.length ?? 0;
  const storyHasCapsule = Boolean(system.story?.time_capsule);
  const pendingSuggestions = Array.isArray(suggestionQuery.data) ? suggestionQuery.data : [];
  const pendingRefinements = Array.isArray(refinementQuery.data) ? refinementQuery.data : [];
  const refinementByItemId = new Map(
    pendingRefinements
      .filter((suggestion) => suggestion.target_wishlist_item_id)
      .map((suggestion) => [suggestion.target_wishlist_item_id as string, suggestion]),
  );
  const aiPendingCount = system.has_partner ? pendingSuggestions.length + pendingRefinements.length : 0;
  const storyRitualActionDisabled =
    generatingStoryRitual || suggestionQuery.isLoading || refinementQuery.isLoading || aiPendingCount > 0;
  const activeGoalLabel = goalDraft ? getGoalLabel(goalDraft) : getGoalLabel(system.couple_goal?.goal_slug);
  const myCarePreferences = normalizeLoveLanguagePreference(system.essentials?.my_care_preferences);
  const partnerCarePreferences = normalizeLoveLanguagePreference(system.essentials?.partner_care_preferences);
  const myCareProfile = system.essentials?.my_care_profile ?? null;
  const partnerCareProfile = system.essentials?.partner_care_profile ?? null;
  const weeklyTask = system.essentials?.weekly_task ?? null;
  const currentHeartPlaybook = buildHeartPlaybookDraft(myCarePreferences, myCareProfile);
  const myCareCueCount = countCareCueCompletion(myCarePreferences, myCareProfile);
  const partnerCareCueCount = countCareCueCompletion(partnerCarePreferences, partnerCareProfile);
  const myCarePlaybookUpdatedAt = formatShortDateTime(
    myCareProfile?.updated_at ?? system.essentials?.my_care_preferences?.updated_at,
  );
  const partnerCarePlaybookUpdatedAt = formatShortDateTime(
    partnerCareProfile?.updated_at ?? system.essentials?.partner_care_preferences?.updated_at,
  );
  const identityMetricValue = system.has_partner
    ? `${system.me.full_name || '你'} × ${system.partner?.partner_name ?? '伴侶'}`
    : '等待雙向配對';
  const identityMetricFootnote = system.has_partner
    ? `目前方向：${activeGoalLabel} · 最近活動 ${lastActivityLabel ?? '尚未建立'}`
    : '先完成雙向伴侶連結，這裡才會變成真正的共享 Relationship System。';
  const heartMetricValue = !system.has_partner
    ? '等待雙向配對'
    : formatCareCueCountLabel(myCareCueCount);
  const heartMetricFootnote = !system.has_partner
    ? '完成配對後，Heart Care Playbook 會變成 pair-visible，本週任務也會開始出現。'
    : weeklyTask?.completed
      ? `${formatCareCueCountLabel(myCareCueCount)}；伴侶目前留下 ${partnerCareCueCount}/5 個。這週的照顧節奏也已完成。`
      : weeklyTask?.task_label
        ? `${formatCareCueCountLabel(myCareCueCount)}；伴侶目前留下 ${partnerCareCueCount}/5 個。本週任務：${weeklyTask.task_label}`
        : `${formatCareCueCountLabel(myCareCueCount)}；伴侶目前留下 ${partnerCareCueCount}/5 個。先把 Heart playbook 留完整，Heart 才會真的變成可維護的照顧系統。`;
  const storyMetricFootnote = storyHasCapsule
    ? 'Time Capsule 已浮現，這段故事已經有可回來看的回聲。'
    : '目前已留下故事錨點，但還沒有形成 Time Capsule 回聲。';
  const sharedFutureMetricFootnote = aiPendingCount > 0
    ? `目前有 ${aiPendingCount} 則待你審核的提案。`
    : '目前沒有待審核提案，已接受的片段仍會留在這裡。';
  const displayNameChanged = displayNameDraft.trim() !== (system.me.full_name?.trim() ?? '');
  const heartPlaybookChanged =
    JSON.stringify(heartPlaybookDraft) !== JSON.stringify(currentHeartPlaybook);

  return (
    <div className="space-y-[clamp(1.75rem,3vw,3rem)]">
      <LoveMapSystemCover
        eyebrow="Relationship System"
        title="把關係的 Identity、Heart、Story 與 Future，放進同一個可維護的系統裡。"
        description="這裡不只是 Love Map，也不只是被導覽得更清楚的長頁。它是 Haven 的 shared relationship knowledge center：把你們是誰、現在怎麼樣、哪些故事值得被記住，以及正在一起靠近的未來，放進同一張系統首頁。"
        pulse={
          system.has_partner
            ? `Haven 現在會用四個長期域來整理你們的關係：Identity、Heart、Story、Future。這裡已經有 ${storyAnchorCount} 個故事錨點、${filledLayerCount}/3 層 Inner Landscape 筆記、${system.stats.wishlist_count} 個 Shared Future 片段；而 Heart Care Playbook 與本週照顧任務也會一起放回 Heart。`
            : '你還沒有完成雙向伴侶連結，所以 Haven 目前只能先保留你的單邊脈動與可編輯 profile。完成連結後，這裡才會變成真正的 shared relationship system。'
        }
        primaryHref={system.has_partner ? '#identity' : '/settings#settings-relationship'}
        primaryLabel={system.has_partner ? '進入 Relationship System' : '先完成伴侶連結'}
        highlights={
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-[1.85rem] border border-white/56 bg-white/74 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/78">Identity</p>
              <p className="mt-2 font-art text-[2rem] leading-none text-card-foreground">
                {system.has_partner ? '已配對' : '等待配對'}
              </p>
              <p className="mt-2 type-caption text-muted-foreground">誰在這個系統裡、目前方向是什麼、管理入口在哪裡，都從這裡開始。</p>
            </div>

            <div className="rounded-[1.85rem] border border-white/56 bg-white/74 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/78">Heart</p>
              <p className="mt-2 font-art text-[2rem] leading-none text-card-foreground">
                {myCareCueCount}/5
              </p>
              <p className="mt-2 type-caption text-muted-foreground">Relationship Pulse、Care Playbook、本週任務與 Inner Landscape 都在這裡對齊。</p>
            </div>

            <div className="rounded-[1.85rem] border border-white/56 bg-white/74 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/78">Story</p>
              <p className="mt-2 font-art text-[2rem] leading-none text-card-foreground">{storyAnchorCount}</p>
              <p className="mt-2 type-caption text-muted-foreground">只引用真的被留下的 shared memory，讓故事能被再次打開，而不是被補寫。</p>
            </div>

            <div className="rounded-[1.85rem] border border-white/56 bg-white/74 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/78">Future</p>
              <p className="mt-2 font-art text-[2rem] leading-none text-card-foreground">{system.stats.wishlist_count}</p>
              <p className="mt-2 type-caption text-muted-foreground">你們真正接受的 Shared Future 片段與待審核提案，都能在這裡回到同一張藍圖。</p>
            </div>
          </div>
        }
        aside={
          <>
            <LoveMapSnapshotCard
              eyebrow="System snapshot"
              title={system.partner?.partner_name ? `${system.me.full_name || '你'} × ${system.partner.partner_name}` : '尚未完成共享配對'}
              description={
                system.has_partner
                  ? '這一頁只展示目前真的有資料支持、而且能被維護的 relationship knowledge。還沒有被看見的部分，Haven 不會假裝自己已經知道。'
                  : '完成伴侶連結後，Haven 才能把這裡從單邊可編輯頁，變成真正的 pair-visible relationship system。'
              }
            >
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <div className="rounded-[1.55rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/80">Identity</p>
                  <p className="mt-2 type-section-title text-card-foreground">{identityMetricValue}</p>
                </div>
                <div className="rounded-[1.55rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/80">Heart</p>
                  <p className="mt-2 type-section-title text-card-foreground">{heartMetricValue}</p>
                </div>
              </div>
            </LoveMapSnapshotCard>

            <LoveMapSnapshotCard
              eyebrow="Trust boundaries"
              title="共享、pair-visible 與私人反思，分開呈現。"
              description="Identity 與 Future 是系統層的共享輪廓；Heart 裡的 Care Playbook 會變成 pair-visible，而 Inner Landscape 仍只屬於你；Story 則只引用已被記住的 shared memory。"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3 rounded-[1.45rem] border border-white/50 bg-white/70 px-4 py-3">
                  <span className="type-section-title text-card-foreground">Identity</span>
                  <Badge variant="success" size="sm">Shared truth</Badge>
                </div>
                <div className="flex items-center justify-between gap-3 rounded-[1.45rem] border border-white/50 bg-white/70 px-4 py-3">
                  <span className="type-section-title text-card-foreground">Heart</span>
                  <Badge variant="status" size="sm">Layered trust</Badge>
                </div>
                <div className="flex items-center justify-between gap-3 rounded-[1.45rem] border border-white/50 bg-white/70 px-4 py-3">
                  <span className="type-section-title text-card-foreground">Story</span>
                  <Badge variant="metadata" size="sm">Memory-backed</Badge>
                </div>
                <div className="flex items-center justify-between gap-3 rounded-[1.45rem] border border-white/50 bg-white/70 px-4 py-3">
                  <span className="type-section-title text-card-foreground">Future</span>
                  <Badge variant="success" size="sm">Shared truth</Badge>
                </div>
              </div>
            </LoveMapSnapshotCard>
          </>
        }
      />

      <LoveMapSystemGuide
        eyebrow="Relationship domains"
        title="Identity / Heart / Story / Future"
        description="Relationship System V1 先把核心 relationship knowledge 固定成四個長期域。每一格都會告訴你它擁有什麼、誰能看見什麼，以及該往哪個更深的 Haven surface 走。"
      >
        <LoveMapSystemGuideCard
          dataTestId="relationship-system-guide-identity"
          eyebrow="Identity"
          title="我們是誰，現在往哪裡走。"
          ownershipLabel="System home"
          ownershipTone="success"
          metricLabel="Relationship identity"
          metricValue={identityMetricValue}
          metricFootnote={identityMetricFootnote}
          belongsHere="關係身份、配對狀態、你在 Haven 裡的名字、目前的共同方向，以及需要去 Settings 管理的關係設定。"
          primaryHref={system.has_partner ? '#identity' : '/settings#settings-relationship'}
          primaryLabel={system.has_partner ? '查看 Identity' : '完成伴侶連結'}
          secondaryHref="/settings#settings-relationship"
          secondaryLabel="打開 Settings"
        />

        <LoveMapSystemGuideCard
          dataTestId="relationship-system-guide-heart"
          eyebrow="Heart"
          title="我們怎麼照顧彼此，現在感覺如何。"
          ownershipLabel="Layered trust"
          ownershipTone="status"
          metricLabel="Heart status"
          metricValue={heartMetricValue}
          metricFootnote={heartMetricFootnote}
          belongsHere="Relationship Pulse、pair-visible Heart Care Playbook、本週 care task，以及只屬於你的 Inner Landscape。"
          primaryHref="#heart"
          primaryLabel="查看 Heart"
          secondaryHref="/journal"
          secondaryLabel="打開 Journal"
        />

        <LoveMapSystemGuideCard
          dataTestId="relationship-system-guide-story"
          eyebrow="Story"
          title="哪些記憶真正定義了我們。"
          ownershipLabel="Memory-backed"
          ownershipTone="metadata"
          metricLabel="Story anchors"
          metricValue={`${storyAnchorCount} 個錨點`}
          metricFootnote={storyMetricFootnote}
          belongsHere="真正被留下、值得回頭重看的 shared memory 與故事回聲，不是 Haven 替你們補寫的總結。"
          primaryHref="#story"
          primaryLabel="查看 Story"
          secondaryHref="/memory"
          secondaryLabel="打開 Memory"
        />

        <LoveMapSystemGuideCard
          dataTestId="relationship-system-guide-future"
          eyebrow="Future"
          title="你們正在一起建造什麼生活。"
          ownershipLabel="Shared truth"
          ownershipTone="success"
          metricLabel="共同未來片段"
          metricValue={`${system.stats.wishlist_count} 個片段`}
          metricFootnote={sharedFutureMetricFootnote}
          belongsHere="真正被接受的共同未來片段，以及那些還在你的 personal review queue 裡等待決定的提案。"
          primaryHref="#future"
          primaryLabel="查看 Future"
          secondaryHref="/blueprint"
          secondaryLabel="打開 Blueprint"
        />
      </LoveMapSystemGuide>

      <LoveMapSection
        id="identity"
        eyebrow="Identity"
        title="把你們是誰、目前在往哪裡走，固定成系統首頁。"
        description="Identity 是 Relationship System 的入口：先把關係身份、配對狀態、你在 Haven 裡的名字，以及現在最值得一起照顧的北極星方向，放進同一個可編輯地方。"
        aside={
          <div className="space-y-3">
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Partner link</p>
              <p className="mt-2 type-section-title text-card-foreground">
                {system.has_partner ? '已完成' : '待完成'}
              </p>
            </div>
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">North star</p>
              <p className="mt-2 type-section-title text-card-foreground">{activeGoalLabel}</p>
            </div>
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Last activity</p>
              <p className="mt-2 type-section-title text-card-foreground">{lastActivityLabel ?? '尚未建立'}</p>
            </div>
          </div>
        }
      >
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.02fr)_minmax(0,0.98fr)]">
          <LoveMapKnowledgeBlock
            dataTestId="relationship-identity-name-card"
            eyebrow="How I appear in Haven"
            title="先固定我在這個系統裡的名字。"
            description="這會更新 Relationship System、Settings，以及 Haven 對你的稱呼。它不是深層 profile schema，而是這個共享系統裡最基本、最值得被維護的識別。"
            badge={<Badge variant="metadata" size="sm">{system.has_partner ? 'Shared context' : 'Personal now'}</Badge>}
          >
            <Input
              id="love-map-identity-display-name"
              label="My name in Haven"
              value={displayNameDraft}
              onChange={(event) => setDisplayNameDraft(event.target.value)}
              placeholder="你希望 Haven 怎麼稱呼你"
              maxLength={120}
              helperText="留空也可以，Haven 會退回 email 前綴。"
            />

            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="type-caption text-muted-foreground">
                這會影響 Relationship System 裡的配對摘要，也讓其他 Haven surfaces 用同一個名字稱呼你。
              </p>
              <Button
                loading={savingIdentity}
                disabled={!displayNameChanged && !savingIdentity}
                onClick={() => void handleSaveIdentity()}
              >
                保存名稱
              </Button>
            </div>
          </LoveMapKnowledgeBlock>

          <LoveMapKnowledgeBlock
            dataTestId="relationship-identity-goal-card"
            eyebrow="North star"
            title="替你們選一個目前最值得一起照顧的方向。"
            description="北極星目標不需要定一輩子，只需要讓 Haven 知道你們最近真正想一起照顧的是哪一塊。"
            badge={<Badge variant="success" size="sm">Shared truth</Badge>}
          >
            {!system.has_partner ? (
              <LoveMapStatePanel
                eyebrow="Partner required"
                title="先完成伴侶連結"
                description="共同方向屬於 shared truth。完成雙向伴侶連結後，這裡才會真正開始累積。"
                tone="quiet"
                actionLabel="去設定完成連結"
                onAction={goToSettings}
              />
            ) : (
              <>
                <div className="grid gap-3">
                  {GOAL_OPTIONS.map((option) => {
                    const selected = goalDraft === option.value;
                    return (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => setGoalDraft(option.value)}
                        className={cn(
                          'rounded-[1.55rem] border px-4 py-4 text-left shadow-soft transition-all duration-haven ease-haven focus-ring-premium',
                          selected
                            ? 'border-primary/22 bg-primary/10'
                            : 'border-white/58 bg-white/78 hover:border-primary/16 hover:bg-white/86',
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="space-y-1">
                            <p className="type-section-title text-card-foreground">{option.label}</p>
                            <p className="type-caption text-muted-foreground">{option.description}</p>
                          </div>
                          {selected ? <Badge variant="success" size="sm">目前選擇</Badge> : null}
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="type-caption text-muted-foreground">目前方向：{getGoalLabel(system.couple_goal?.goal_slug)}</p>
                  <Button loading={savingGoal} disabled={!goalDraft} onClick={() => void handleSaveGoal()}>
                    保存共同方向
                  </Button>
                </div>
              </>
            )}
          </LoveMapKnowledgeBlock>

          <div className="xl:col-span-2">
            <LoveMapKnowledgeBlock
              dataTestId="relationship-identity-snapshot-card"
              eyebrow="Pair snapshot"
              title={system.has_partner ? `${system.me.full_name || '你'} × ${system.partner?.partner_name ?? '伴侶'}` : '這裡還沒有形成完整的 pair snapshot'}
              description={
                system.has_partner
                  ? 'Identity 先把關係最基本的輪廓固定下來，讓其他 Haven surfaces 不會像分散產品，而是像同一個系統在不同深度的工作台。'
                  : '你現在仍然可以維護自己的系統名稱與個人 preferences；完成配對後，這裡才會變成真正的 shared relationship center。'
              }
              footer={
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="type-caption text-muted-foreground">
                    配對管理、邀請碼與關係設定仍然留在 Settings，Relationship System 只負責呈現最重要的摘要與編輯入口。
                  </p>
                  <Link
                    href="/settings#settings-relationship"
                    className="inline-flex items-center gap-2 rounded-full border border-white/58 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
                  >
                    打開 Settings
                    <Sparkles className="h-4 w-4" aria-hidden />
                  </Link>
                </div>
              }
            >
              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-[1.45rem] border border-white/58 bg-white/78 px-4 py-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/80">Connection</p>
                  <p className="mt-2 type-section-title text-card-foreground">{system.has_partner ? 'Paired' : 'Solo'}</p>
                </div>
                <div className="rounded-[1.45rem] border border-white/58 bg-white/78 px-4 py-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/80">Direction</p>
                  <p className="mt-2 type-section-title text-card-foreground">{activeGoalLabel}</p>
                </div>
                <div className="rounded-[1.45rem] border border-white/58 bg-white/78 px-4 py-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/80">Last activity</p>
                  <p className="mt-2 type-section-title text-card-foreground">{lastActivityLabel ?? '尚未建立'}</p>
                </div>
              </div>
            </LoveMapKnowledgeBlock>
          </div>
        </div>
      </LoveMapSection>

      <LoveMapSection
        id="heart"
        eyebrow="Heart"
        title="把關係現在的感受、照顧方式與私人理解，放回同一層。"
        description="Heart 不是單一欄位，而是 Relationship System 裡最常被維護的一層：Relationship Pulse 負責共享狀態，Heart Care Playbook 與每週照顧任務讓這一層更可執行，而 Inner Landscape 仍然保留你的私人反思。"
        aside={
          <div className="space-y-3">
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Pulse coverage</p>
              <p className="mt-2 type-section-title text-card-foreground">
                {system.stats.baseline_ready_mine && system.stats.baseline_ready_partner
                  ? '雙方已建立'
                  : system.stats.baseline_ready_mine
                    ? '我已建立'
                    : '尚未建立'}
              </p>
            </div>
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Care Playbook</p>
              <p className="mt-2 type-section-title text-card-foreground">{formatCareCueCountLabel(myCareCueCount)}</p>
            </div>
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Weekly task</p>
              <p className="mt-2 type-section-title text-card-foreground">{weeklyTask?.completed ? '已完成' : weeklyTask ? '待完成' : '未啟用'}</p>
            </div>
          </div>
        }
      >
        <div id="relationship-pulse" className="scroll-mt-24" />
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.02fr)_minmax(0,0.98fr)]">
          <LoveMapKnowledgeBlock
            dataTestId="relationship-heart-pulse-card"
            eyebrow="Relationship Pulse"
            title="用五個維度，先對現在誠實。"
            description="這不是評分遊戲，而是替現在的關係建立一個可以回來對照的位置。"
            badge={<Badge variant="success" size="sm">Shared truth</Badge>}
            footer={
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="type-caption text-muted-foreground">
                  先對現在誠實，比一次填到完美更重要。
                </p>
                <Button loading={savingBaseline} onClick={() => void handleSaveBaseline()}>
                  保存 Relationship Pulse
                </Button>
              </div>
            }
          >
            <div className="grid gap-3 md:grid-cols-2">
              {BASELINE_DIMENSIONS.map((dimension) => {
                const myScore = baselineDraft[dimension] ?? 3;
                const partnerScore = Number(system.baseline.partner?.scores?.[dimension] ?? 0) || null;
                return (
                  <div
                    key={dimension}
                    className="rounded-[1.55rem] border border-white/58 bg-white/78 p-4 shadow-soft"
                  >
                    <div className="space-y-1">
                      <p className="type-section-title text-card-foreground">{DIMENSION_LABELS[dimension] ?? dimension}</p>
                      <p className="type-caption text-muted-foreground">
                        {DIMENSION_HELPERS[dimension] ?? '用最直覺的感受先評估。'}
                      </p>
                    </div>

                    <div className="mt-3 grid gap-2">
                      <label htmlFor={`love-map-baseline-${dimension}`} className="type-caption text-card-foreground/82">
                        我的感受
                      </label>
                      <select
                        id={`love-map-baseline-${dimension}`}
                        value={myScore}
                        onChange={(event) =>
                          setBaselineDraft((current) => ({
                            ...current,
                            [dimension]: Number(event.target.value),
                          }))
                        }
                        className="select-premium w-full"
                      >
                        {[1, 2, 3, 4, 5].map((score) => (
                          <option key={score} value={score}>
                            {score}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="mt-3 rounded-[1.25rem] border border-primary/10 bg-primary/8 px-3 py-3">
                      <p className="type-caption text-muted-foreground">伴侶最近填寫</p>
                      <p className="mt-1 type-section-title text-card-foreground">{scoreLabel(partnerScore)}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </LoveMapKnowledgeBlock>

          <div className="space-y-4">
            <LoveMapKnowledgeBlock
              dataTestId="relationship-heart-playbook-card"
              eyebrow="Heart Care Playbook"
              title="把真正有用的照顧線索，留成 pair-visible 的 Heart playbook。"
              description="Heart 不只該知道你偏好哪種照顧語言，也該知道當你過載時怎麼先接住你、什麼會讓你更糟，以及哪些小動作最容易真的讓你感到被照顧。"
              badge={<Badge variant={system.has_partner ? 'success' : 'metadata'} size="sm">{system.has_partner ? 'Pair-visible' : 'Starts with you'}</Badge>}
              footer={
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="type-caption text-muted-foreground">
                    {system.has_partner
                      ? '每個人都只能編輯自己的 Heart Care Playbook；伴侶會在同一塊 Heart 裡看到你最新留下的版本。'
                      : '先寫下來也沒關係；完成配對後，它會變成 pair-visible 的 relationship essential。'}
                  </p>
                  <Button
                    loading={savingHeartPlaybook}
                    disabled={savingHeartPlaybook || !heartPlaybookDraft.primary || !heartPlaybookChanged}
                    onClick={() => void handleSaveHeartPlaybook()}
                  >
                    保存 Heart Care Playbook
                  </Button>
                </div>
              }
            >
              <div className="grid gap-4 md:grid-cols-2">
                <div
                  className="space-y-4 rounded-[1.55rem] border border-white/58 bg-white/78 p-4 shadow-soft"
                  data-testid="relationship-heart-playbook-editor-card"
                >
                  <div className="space-y-1">
                    <p className="type-section-title text-card-foreground">我的 Heart Care Playbook</p>
                    <p className="type-caption text-muted-foreground">
                      {formatCareCueCountLabel(myCareCueCount)}
                      {myCarePlaybookUpdatedAt ? ` · 最近更新 ${myCarePlaybookUpdatedAt}` : ''}
                    </p>
                  </div>

                  <div className="grid gap-2">
                    <label htmlFor="love-map-care-primary" className="type-caption text-card-foreground/82">
                      我的主要 care preference
                    </label>
                    <select
                      id="love-map-care-primary"
                      value={heartPlaybookDraft.primary ?? ''}
                      onChange={(event) => {
                        const nextPrimary = (event.target.value || null) as LoveLanguagePreferenceKey | null;
                        setHeartPlaybookDraft((current) => ({
                          primary: nextPrimary,
                          secondary: current.secondary === nextPrimary ? null : current.secondary,
                          support_me: current.support_me,
                          avoid_when_stressed: current.avoid_when_stressed,
                          small_delights: current.small_delights,
                        }));
                      }}
                      className="select-premium w-full"
                    >
                      <option value="">請選擇</option>
                      {LOVE_LANGUAGE_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                          {getLoveLanguageLabel(option)}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="grid gap-2">
                    <label htmlFor="love-map-care-secondary" className="type-caption text-card-foreground/82">
                      我的次要 care preference
                    </label>
                    <select
                      id="love-map-care-secondary"
                      value={heartPlaybookDraft.secondary ?? ''}
                      onChange={(event) =>
                        setHeartPlaybookDraft((current) => ({
                          ...current,
                          secondary: (event.target.value || null) as LoveLanguagePreferenceKey | null,
                        }))
                      }
                      className="select-premium w-full"
                    >
                      <option value="">先留空也可以</option>
                      {LOVE_LANGUAGE_OPTIONS.filter((option) => option !== heartPlaybookDraft.primary).map((option) => (
                        <option key={option} value={option}>
                          {getLoveLanguageLabel(option)}
                        </option>
                      ))}
                    </select>
                  </div>

                  <Textarea
                    id="love-map-heart-support-me"
                    label="當我過載時，先怎麼幫我"
                    value={heartPlaybookDraft.support_me}
                    onChange={(event) =>
                      setHeartPlaybookDraft((current) => ({
                        ...current,
                        support_me: event.target.value,
                      }))
                    }
                    placeholder="例如：先幫我把手機放遠一點，再慢慢陪我整理。"
                    maxLength={500}
                    helperText="留下一個伴侶真的可以照做的版本，不需要寫成完整理論。"
                  />

                  <Textarea
                    id="love-map-heart-avoid-when-stressed"
                    label="我壓力大時，先避免什麼"
                    value={heartPlaybookDraft.avoid_when_stressed}
                    onChange={(event) =>
                      setHeartPlaybookDraft((current) => ({
                        ...current,
                        avoid_when_stressed: event.target.value,
                      }))
                    }
                    placeholder="例如：不要立刻追問、不要先幫我下結論。"
                    maxLength={500}
                    helperText="這會讓 Heart 不只知道你喜歡什麼，也知道什麼會讓情況更糟。"
                  />

                  <Textarea
                    id="love-map-heart-small-delights"
                    label="哪些小動作最能讓我感到被照顧"
                    value={heartPlaybookDraft.small_delights}
                    onChange={(event) =>
                      setHeartPlaybookDraft((current) => ({
                        ...current,
                        small_delights: event.target.value,
                      }))
                    }
                    placeholder="例如：回家時先抱我一下，或是幫我留一杯熱飲。"
                    maxLength={500}
                    helperText="越小、越具體，越容易變成真的可維護關係知識。"
                  />
                </div>

                <div
                  className="space-y-4 rounded-[1.55rem] border border-primary/10 bg-primary/8 p-4 shadow-soft"
                  data-testid="relationship-heart-playbook-partner-card"
                >
                  <div className="space-y-1">
                    <p className="type-section-title text-card-foreground">伴侶目前留下的 Heart Care Playbook</p>
                    <p className="type-caption text-muted-foreground">
                      {system.has_partner
                        ? partnerCareCueCount > 0
                          ? `${formatCareCueCountLabel(partnerCareCueCount)}${partnerCarePlaybookUpdatedAt ? ` · 最近更新 ${partnerCarePlaybookUpdatedAt}` : ''}`
                          : '伴侶還沒有在 Relationship System 裡留下 Heart Care Playbook。'
                        : '完成雙向伴侶連結後，這裡才會顯示 pair-visible 的 partner playbook。'}
                    </p>
                  </div>

                  {system.has_partner && partnerCareCueCount > 0 ? (
                    <div className="space-y-3">
                      <LoveMapEssentialField
                        label="Partner care preference"
                        value={describeLoveLanguagePreference(partnerCarePreferences)}
                        dataTestId="relationship-heart-playbook-partner-preferences"
                      />
                      <LoveMapEssentialField
                        label="當對方過載時，先怎麼幫他/她"
                        value={partnerCareProfile?.support_me}
                        dataTestId="relationship-heart-playbook-partner-support"
                      />
                      <LoveMapEssentialField
                        label="對方壓力大時，先避免什麼"
                        value={partnerCareProfile?.avoid_when_stressed}
                        dataTestId="relationship-heart-playbook-partner-avoid"
                      />
                      <LoveMapEssentialField
                        label="哪些小動作最能讓對方感到被照顧"
                        value={partnerCareProfile?.small_delights}
                        dataTestId="relationship-heart-playbook-partner-delights"
                      />
                    </div>
                  ) : (
                    <LoveMapStatePanel
                      eyebrow="Partner playbook"
                      title="伴侶還沒有留下這一塊。"
                      description="Heart Care Playbook 不是自動生成的 shared truth。對方實際寫下來之前，這裡會保持空白，而不是讓 Haven 假裝自己已經知道。"
                      tone="quiet"
                    />
                  )}

                  <p className="type-caption text-muted-foreground">
                    這是 pair-visible 的 Heart essentials：每個人都只寫自己的版本，但一旦留下來，就會變成伴侶平常能回來看的照顧參考。
                  </p>
                </div>
              </div>
            </LoveMapKnowledgeBlock>

            <LoveMapKnowledgeBlock
              dataTestId="relationship-heart-weekly-task-card"
              eyebrow="Weekly care loop"
              title="把這週最小、最可執行的照顧行動放進系統裡。"
              description="這不是新的獨立功能頁，而是 Heart 的當週操作層。現在它會直接貼著 Heart Care Playbook 出現，讓本週的行動不是抽象習慣，而是有上下文的照顧動作。"
              badge={
                <Badge variant={weeklyTask?.completed ? 'success' : 'metadata'} size="sm">
                  {weeklyTask?.completed ? 'Completed' : 'This week'}
                </Badge>
              }
            >
              {!system.has_partner ? (
                <LoveMapStatePanel
                  eyebrow="Partner required"
                  title="先完成雙向伴侶連結"
                  description="週任務屬於 pair context。完成配對後，Haven 才能替你們生成同一個 weekly care task。"
                  tone="quiet"
                  actionLabel="去設定完成連結"
                  onAction={goToSettings}
                />
              ) : weeklyTask ? (
                <div className="space-y-4 rounded-[1.55rem] border border-white/58 bg-white/78 p-4 shadow-soft">
                  <div className="space-y-2">
                    <p className="type-section-title text-card-foreground">{weeklyTask.task_label}</p>
                    <p className="type-caption text-muted-foreground">
                      {weeklyTask.assigned_at
                        ? `本週任務自 ${formatShortDateTime(weeklyTask.assigned_at) ?? '這週'} 起生效。`
                        : '這個任務屬於本週的 pair care loop。'}
                    </p>
                  </div>

                  {weeklyTask.completed ? (
                    <div className="rounded-[1.35rem] border border-primary/10 bg-primary/8 px-4 py-4">
                      <p className="type-section-title text-card-foreground">本週任務已完成</p>
                      <p className="mt-1 type-caption text-muted-foreground">
                        完成時間：{formatShortDateTime(weeklyTask.completed_at) ?? '剛剛'}
                      </p>
                    </div>
                  ) : (
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="type-caption text-muted-foreground">
                        這一格讓 Relationship System 不只知道你們怎麼想，也知道這週實際做了什麼照顧動作。
                      </p>
                      <Button
                        loading={completingWeeklyTask}
                        onClick={() => void handleCompleteWeeklyCareTask()}
                      >
                        標記本週任務完成
                      </Button>
                    </div>
                  )}
                </div>
              ) : (
                <LoveMapStatePanel
                  eyebrow="Weekly task"
                  title="本週任務還沒有準備好。"
                  description="如果這一格沒有內容，代表這週的 pair task 還沒有成功解析，稍後重新整理即可。"
                  tone="quiet"
                  actionLabel="重新讀取"
                  onAction={handleRefresh}
                />
              )}
            </LoveMapKnowledgeBlock>
          </div>
        </div>

        <div id="inner-landscape" className="scroll-mt-24 space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="space-y-2">
              <Badge variant="status" size="sm">Inner Landscape</Badge>
              <h3 className="type-h3 text-card-foreground">把私人理解留在 Heart 裡，但不把它偽裝成 shared truth。</h3>
              <p className="max-w-[56rem] type-body-muted text-muted-foreground">
                Inner Landscape 仍然是你的私人 reflection layer。它現在被放進 Heart，是為了讓關係的感受、偏好與私人理解屬於同一個可維護層，而不是因為它變成了共享真理。
              </p>
            </div>

            <Link
              href="/journal"
              className="inline-flex items-center gap-2 rounded-full border border-white/58 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
            >
              進入 Journal（完整反思書房）
              <Sparkles className="h-4 w-4" aria-hidden />
            </Link>
          </div>

          {!system.has_partner ? (
            <div className="space-y-4">
              <LoveMapStatePanel
                eyebrow="Partner required"
                title="先完成雙向伴侶連結，Relationship System 才會開始成形。"
                description="現在你仍然可以先看 prompts，但 Haven 不會在沒有 partner pair 的情況下，把這一區當成正式的 Relationship System。"
                tone="quiet"
                actionLabel="去設定完成連結"
                onAction={goToSettings}
              />

              {cardsQuery.isError ? (
                <LoveMapStatePanel
                  eyebrow="Prompt preview"
                  title="Relationship System prompts 暫時沒有順利載入"
                  description="等 prompts 回來後，你至少可以先預覽 Haven 會如何帶你們往更深處走。"
                  tone="quiet"
                  actionLabel="重讀 prompts"
                  onAction={() => {
                    void cardsQuery.refetch();
                  }}
                />
              ) : (
                <div className="grid gap-4 lg:grid-cols-3">
                  {LAYERS.map((layer) => {
                    const prompt = cardsByLayer[layer][0];
                    if (!prompt) {
                      return (
                        <LoveMapStatePanel
                          key={layer}
                          eyebrow={LAYER_META[layer].label}
                          title="這一層今天沒有新的 prompts。"
                          description="沒有關係，等 partner 連結完成後，Relationship System 仍會從這一層開始慢慢長出來。"
                          tone="quiet"
                        />
                      );
                    }
                    return (
                      <LoveMapPromptCard
                        key={layer}
                        index={1}
                        title={prompt.title}
                        description={prompt.description}
                        question={prompt.question}
                      />
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {LAYERS.map((layer) => (
                <div key={layer} className="grid gap-4 xl:grid-cols-[minmax(0,1.08fr)_minmax(300px,0.92fr)]">
                  <LoveMapReflectionStudio
                    eyebrow={LAYER_META[layer].eyebrow}
                    title={LAYER_META[layer].title}
                    description={LAYER_META[layer].description}
                    textareaId={`love-map-note-${layer}`}
                    textareaLabel={`${LAYER_META[layer].label} 筆記`}
                    value={noteDrafts[layer]}
                    onChange={(value) =>
                      setNoteDrafts((current) => ({
                        ...current,
                        [layer]: value,
                      }))
                    }
                    onSave={() => {
                      void handleSaveLayer(layer);
                    }}
                    saving={savingLayer === layer}
                    helperText={LAYER_META[layer].helperText}
                    placeholder={LAYER_META[layer].placeholder}
                    lastUpdated={formatShortDateTime(system.notes.find((note) => note.layer === layer)?.updated_at)}
                    badgeText={`${cardsByLayer[layer].length} 個 prompts`}
                  />

                  <div className="space-y-4">
                    {cardsQuery.isError ? (
                      <LoveMapStatePanel
                        eyebrow={`${LAYER_META[layer].label} prompts`}
                        title="這一層的 prompts 沒有順利載入"
                        description="Relationship System 本身仍可使用，但這一層的 conversation support 需要重新讀取。"
                        tone="quiet"
                        actionLabel="重讀 prompts"
                        onAction={() => {
                          void cardsQuery.refetch();
                        }}
                      />
                    ) : cardsByLayer[layer].length === 0 ? (
                      <LoveMapStatePanel
                        eyebrow={`${LAYER_META[layer].label} prompts`}
                        title="這一層今天沒有新的 prompts。"
                        description="也沒關係，真正重要的是你們留下了什麼理解，而不是系統今天提出了多少問題。"
                        tone="quiet"
                      />
                    ) : (
                      cardsByLayer[layer].slice(0, 3).map((card, index) => (
                        <LoveMapPromptCard
                          key={card.id}
                          index={index + 1}
                          title={card.title}
                          description={card.description}
                          question={card.question}
                        />
                      ))
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </LoveMapSection>

      <LoveMapSection
        id="story"
        eyebrow="Story"
        title="讓真正被留下來的 shared memory，變成可回來看的關係敘事。"
        description="Story 不是 scrapbook，也不是 AI 替你們寫的總結。它是 Relationship System 裡的記憶層，只會指向 Haven 已經真的看見、而且值得你們回到 Memory 裡重新打開的那些故事錨點。"
        aside={
          <div className="space-y-3">
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Story anchors</p>
              <p className="mt-2 type-section-title text-card-foreground">{storyAnchorCount}</p>
            </div>
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Time Capsule</p>
              <p className="mt-2 type-section-title text-card-foreground">{storyHasCapsule ? '有回聲' : '尚未浮現'}</p>
            </div>
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Trust note</p>
              <p className="mt-2 type-caption text-muted-foreground">
                只來自 Haven 已經留下的 shared memory，不替你們發明不存在的關係結論，也不把 Memory 與 Relationship System 變成兩套互不相干的產品。
              </p>
            </div>
          </div>
        }
      >
        {!system.has_partner ? (
          <LoveMapStatePanel
            eyebrow="Partner required"
            title="先完成伴侶連結，故事切片才會長出 shared memory。"
            description="Story 是雙人關係知識的一部分。沒有雙向連結時，Haven 不該假裝它已經看見一段共同的故事。"
            tone="quiet"
            actionLabel="去設定完成連結"
            onAction={goToSettings}
          />
        ) : !system.story.available ? (
          <LoveMapStatePanel
            eyebrow="Story is still quiet"
            title="你們的故事還沒有累積到足夠的記憶錨點。"
            description="等更多 journal、共同卡片或 appreciation 被留下來後，這裡才會開始誠實地長出關係故事。"
            tone="quiet"
            actionLabel="進入 Memory（完整 Shared Archive）"
            onAction={() => {
              if (typeof window !== 'undefined') {
                window.location.href = '/memory';
              }
            }}
          />
        ) : (
          <div className="space-y-4">
            {system.story.time_capsule ? (
              <LoveMapStoryCapsuleCard
                summaryText={system.story.time_capsule.summary_text}
                rangeLabel={formatStoryRange(system.story.time_capsule.from_date, system.story.time_capsule.to_date)}
                journalsCount={system.story.time_capsule.journals_count}
                cardsCount={system.story.time_capsule.cards_count}
                appreciationsCount={system.story.time_capsule.appreciations_count}
              />
            ) : null}

            {system.story.moments.length > 0 ? (
              <div className="grid gap-4 xl:grid-cols-3">
                {system.story.moments.map((moment) => (
                  <LoveMapStoryMomentCard
                    key={`${moment.kind}-${moment.occurred_at}-${moment.title}`}
                    kind={moment.kind}
                    title={moment.title}
                    description={moment.description}
                    occurredAtLabel={formatStoryDate(moment.occurred_at)}
                    badges={moment.badges}
                    whyText={moment.why_text}
                    href={storyMomentHref(moment)}
                  />
                ))}
              </div>
            ) : null}

            {system.story.time_capsule ? (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-[1.55rem] border border-white/58 bg-white/78 px-4 py-4 shadow-soft">
                <p className="type-caption text-muted-foreground">
                  如果這段回聲已經足夠清楚，Haven 可以先提出一個貼著這段故事的 ritual，然後再由你決定要不要把它放進 Shared Future。
                </p>
                <Button
                  variant="secondary"
                  loading={generatingStoryRitual}
                  disabled={storyRitualActionDisabled}
                  onClick={() => {
                    void handleGenerateStoryRitualSuggestion();
                  }}
                >
                  讓 Haven 從這段故事提出 ritual
                </Button>
              </div>
            ) : null}

            <Link
              href="/memory"
              className="inline-flex items-center gap-2 rounded-full border border-white/58 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
            >
              進入 Memory（完整 Story archive）
              <Sparkles className="h-4 w-4" aria-hidden />
            </Link>
          </div>
        )}
      </LoveMapSection>

      <LoveMapSection
        id="future"
        eyebrow="Future"
        title="把你們想一起靠近的生活，留在能持續維護的共享藍圖裡。"
        description="Future 是 Relationship System 裡最面向前方的一層：它保留 Shared Future 的摘要、AI 提案審核與新增入口，但完整片段、備註與工作台仍然留在 Blueprint。"
        aside={
          <div className="space-y-3">
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Shared Future 片段</p>
              <p className="mt-2 type-section-title text-card-foreground">{system.stats.wishlist_count}</p>
            </div>
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">待審核提案</p>
              <p className="mt-2 type-section-title text-card-foreground">{aiPendingCount}</p>
            </div>
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">完整 Shared Future</p>
              <p className="mt-2 type-caption text-muted-foreground">這裡是系統摘要與審核層；完整 Blueprint、備註與整理入口仍在 Blueprint。</p>
            </div>
          </div>
        }
      >
        <div id="shared-future" className="scroll-mt-24" />
        {!system.has_partner ? (
          <LoveMapStatePanel
            eyebrow="Partner required"
            title="共同未來需要先有共同配對。"
            description="連結完成後，Shared Future 才會變成真正可以一起累積、一起回看的關係知識。"
            tone="quiet"
            actionLabel="去設定完成連結"
            onAction={goToSettings}
          />
        ) : (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.02fr)_minmax(0,0.98fr)]">
            <div className="grid gap-4">
              <LoveMapFutureComposer
                eyebrow="AI 提案審核"
                title="先由 Haven 提案，再由你決定什麼能進入 Shared Future。"
                description="這一層是你的 personal review queue，不是 shared truth。只有接受後，提案才會寫進 Shared Future。"
                footer={
                  <div className="rounded-[1.55rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                    <p className="type-caption text-muted-foreground">
                      AI 提案審核只對你可見；伴侶只會看到你接受之後真正進入 Shared Future 的內容。
                    </p>
                  </div>
                }
              >
                <div className="space-y-4">
                  {suggestionQuery.isError ? (
                    <LoveMapStatePanel
                      eyebrow="AI 提案審核"
                      title="提案審核佇列暫時沒有順利載入。"
                      description="目前的 Shared Future 仍然可用，但這一層 personal review queue 需要重新讀取。"
                      tone="quiet"
                      actionLabel="重新讀取提案"
                      onAction={() => {
                        void suggestionQuery.refetch();
                      }}
                    />
                  ) : suggestionQuery.isLoading ? (
                    <LoveMapStatePanel
                      eyebrow="AI 提案審核"
                      title="Haven 正在讀取你的提案審核佇列。"
                      description="如果這裡有待審核的 Shared Future 提案，它們會在幾秒內出現。"
                      tone="quiet"
                    />
                  ) : pendingSuggestions.length === 0 ? (
                    <LoveMapStatePanel
                      eyebrow="AI 提案審核"
                      title="目前沒有待你審核的 Shared Future 提案。"
                      description="當 Haven 能從你留下的 journals、共同卡片與 appreciation 裡看到足夠清楚的方向時，它才會提出提案。"
                      tone="quiet"
                      actionLabel="讓 Haven 提出 Shared Future 提案"
                      onAction={() => {
                        void handleGenerateSuggestions();
                      }}
                    />
                  ) : (
                    pendingSuggestions.map((suggestion) => (
                      <LoveMapSuggestedUpdateCard
                        key={suggestion.id}
                        title={suggestion.proposed_title}
                        notes={suggestion.proposed_notes}
                        variant={getSharedFutureSuggestionVariant(suggestion.generator_version)}
                        evidence={suggestion.evidence}
                        accepting={reviewingSuggestionId === suggestion.id && reviewingAction === 'accept'}
                        dismissing={reviewingSuggestionId === suggestion.id && reviewingAction === 'dismiss'}
                        onAccept={() => {
                          void handleAcceptSuggestion(suggestion);
                        }}
                        onDismiss={() => {
                          void handleDismissSuggestion(suggestion);
                        }}
                      />
                    ))
                  )}

                  <div className="flex flex-wrap items-center justify-between gap-3 rounded-[1.55rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                    <p className="type-caption text-muted-foreground">
                      Haven 只會在 evidence 足夠清楚時提出提案，並且不會直接寫進 shared truth。
                    </p>
                    <Button
                      variant="secondary"
                      loading={generatingSuggestions}
                      disabled={generatingSuggestions || suggestionQuery.isLoading}
                      onClick={() => {
                        void handleGenerateSuggestions();
                      }}
                    >
                      {pendingSuggestions.length > 0 ? '重新整理提案' : '讓 Haven 提案'}
                    </Button>
                  </div>
                </div>
              </LoveMapFutureComposer>

              {system.wishlist_items.length === 0 ? (
                <LoveMapStatePanel
                  eyebrow="Shared Future"
                  title="你們的共同藍圖還是空白的。"
                  description="這不是壞事。第一個未來片段一旦被寫下來，Haven 才會開始真的記得你們想一起去的方向。"
                  tone="quiet"
                />
              ) : (
                system.wishlist_items.map((item) => {
                  const refinementSuggestion = refinementByItemId.get(item.id);
                  const cadenceEligible = supportsCadenceRefinement(item.title, item.notes ?? '');
                  const isGeneratingAnyRefinement = generatingRefinement?.itemId === item.id;
                  const isGeneratingNextStep =
                    generatingRefinement?.itemId === item.id && generatingRefinement.kind === 'next_step';
                  const isGeneratingCadence =
                    generatingRefinement?.itemId === item.id && generatingRefinement.kind === 'cadence';
                  return (
                    <div
                      key={item.id}
                      data-shared-future-item-id={item.id}
                      className="space-y-4 rounded-[1.9rem] border border-white/58 bg-white/80 p-5 shadow-soft"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="space-y-2">
                          <p className="type-section-title text-card-foreground">{item.title}</p>
                          <p className="type-caption text-muted-foreground">
                            {item.added_by_me ? '由你放進共同藍圖' : '由伴侶放進共同藍圖'} ・ {formatShortDateTime(item.created_at) ?? '剛剛'}
                          </p>
                        </div>
                        <Badge variant={item.added_by_me ? 'status' : 'metadata'} size="sm">
                          {item.added_by_me ? 'My contribution' : 'Partner contribution'}
                        </Badge>
                      </div>
                      {item.notes ? <LoveMapSharedFutureNotesPanel notes={item.notes} /> : null}

                      <div className="flex flex-wrap items-center justify-between gap-3 rounded-[1.35rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                        <p className="type-caption text-muted-foreground">
                          這個片段已經是 shared truth。Haven 只能先提出下一步或節奏建議，不能直接改寫它。
                        </p>
                        <div className="flex flex-wrap gap-3">
                          <Button
                            variant="secondary"
                            loading={isGeneratingNextStep}
                            disabled={isGeneratingAnyRefinement || Boolean(refinementSuggestion)}
                            onClick={() => {
                              void handleGenerateRefinement(item.id, 'next_step');
                            }}
                          >
                            {refinementSuggestion ? '已生成 refinement' : '讓 Haven 幫這個片段補下一步'}
                          </Button>
                          {cadenceEligible ? (
                            <Button
                              variant="secondary"
                              loading={isGeneratingCadence}
                              disabled={isGeneratingAnyRefinement || Boolean(refinementSuggestion)}
                              onClick={() => {
                                void handleGenerateRefinement(item.id, 'cadence');
                              }}
                            >
                              {refinementSuggestion ? '已生成 refinement' : '讓 Haven 幫這個片段補節奏'}
                            </Button>
                          ) : null}
                        </div>
                      </div>

                      {refinementSuggestion ? (
                        <LoveMapRefinementSuggestionCard
                          targetTitle={item.title}
                          refinementKind={getRefinementKind(refinementSuggestion.generator_version)}
                          proposedNotes={refinementSuggestion.proposed_notes}
                          evidence={refinementSuggestion.evidence}
                          accepting={reviewingSuggestionId === refinementSuggestion.id && reviewingAction === 'accept'}
                          dismissing={reviewingSuggestionId === refinementSuggestion.id && reviewingAction === 'dismiss'}
                          onAccept={() => {
                            void handleAcceptSuggestion(refinementSuggestion);
                          }}
                          onDismiss={() => {
                            void handleDismissSuggestion(refinementSuggestion);
                          }}
                        />
                      ) : null}
                    </div>
                  );
                })
              )}

              <Link
                href="/blueprint"
                className="inline-flex items-center gap-2 rounded-full border border-white/58 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
              >
                進入 Blueprint（完整 Shared Future）
                <Sparkles className="h-4 w-4" aria-hidden />
              </Link>
            </div>

            <LoveMapFutureComposer
              eyebrow="新增未來片段"
              title="把下一個想一起變成真的片段，放進這張圖裡。"
              description="不需要很大，可以只是一種生活感、一個儀式、一段季節裡想一起完成的畫面。"
              footer={
                <div className="rounded-[1.55rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                  <p className="type-caption text-muted-foreground">
                    Relationship System 會把高價值摘要留在這裡；若要整理完整 Shared Future 片段、備註與新增入口，請進到 Blueprint。
                  </p>
                </div>
              }
            >
              <div className="space-y-4">
                <Input
                  id="love-map-wish-title"
                  label="未來片段標題"
                  value={wishTitle}
                  onChange={(event) => setWishTitle(event.target.value)}
                  placeholder="例如：每個月留一晚只屬於我們，或一起去京都看櫻花"
                  maxLength={500}
                  helperText="先寫最想一起靠近的畫面本身。"
                />

                <Textarea
                  id="love-map-wish-notes"
                  label="補充（選填）"
                  value={wishNotes}
                  onChange={(event) => setWishNotes(event.target.value)}
                  placeholder="補上原因、季節、感受，或你想一起擁有的生活氣味。"
                  maxLength={2000}
                  className="min-h-[8rem]"
                  helperText="留白也可以，讓這個片段先存在。"
                />

                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="type-caption text-muted-foreground">
                    這裡新增的內容會立刻成為 Shared Future 的一部分。
                  </p>
                  <Button
                    loading={savingWishlist}
                    rightIcon={<HeartHandshake className="h-4 w-4" aria-hidden />}
                    onClick={() => void handleAddWishlist()}
                  >
                    放進共同藍圖
                  </Button>
                </div>
              </div>
            </LoveMapFutureComposer>
          </div>
        )}
      </LoveMapSection>
    </div>
  );
}
