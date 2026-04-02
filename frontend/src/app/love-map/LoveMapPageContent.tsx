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
  createOrUpdateLoveMapNote,
  dismissLoveMapSharedFutureSuggestion,
  generateLoveMapSharedFutureCadenceRefinement,
  generateLoveMapSharedFutureRefinement,
  generateLoveMapSharedFutureSuggestions,
  type LoveMapCardSummary,
  type RelationshipKnowledgeSuggestionPublic,
} from '@/services/api-client';
import {
  BASELINE_DIMENSIONS,
  setCoupleGoal,
  upsertBaseline,
} from '@/services/relationship-api';
import LoveMapSkeleton from './LoveMapSkeleton';
import {
  LoveMapFutureComposer,
  LoveMapPromptCard,
  LoveMapRefinementSuggestionCard,
  LoveMapReflectionStudio,
  LoveMapSection,
  LoveMapSuggestedUpdateCard,
  LoveMapStoryCapsuleCard,
  LoveMapStoryMomentCard,
  LoveMapSnapshotCard,
  LoveMapStatePanel,
  LoveMapSystemCover,
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
  // Card and appreciation anchors deep-link to Memory calendar with item-level focus.
  const dateMatch = moment.occurred_at?.match(/^\d{4}-\d{2}-\d{2}/);
  if (dateMatch) {
    return `/memory?date=${dateMatch[0]}&kind=${moment.kind}&id=${moment.source_id}`;
  }
  return null;
}

function getGoalLabel(goalSlug?: string | null) {
  return GOAL_OPTIONS.find((option) => option.value === goalSlug)?.label ?? '尚未設定';
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
  const [generatingSuggestions, setGeneratingSuggestions] = useState(false);
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
    ]);
  };

  const handleSaveLayer = async (layer: LoveMapLayer) => {
    setSavingLayer(layer);
    try {
      await createOrUpdateLoveMapNote(layer, noteDrafts[layer]);
      await invalidateRelationshipViews();
      showToast(`${LAYER_META[layer].label} 已保存`, 'success');
    } catch (error) {
      logClientError('love-map-layer-save-failed', error);
      showToast('保存失敗，請稍後再試', 'error');
    } finally {
      setSavingLayer(null);
    }
  };

  const handleSaveBaseline = async () => {
    setSavingBaseline(true);
    try {
      await upsertBaseline(baselineDraft);
      await invalidateRelationshipViews();
      showToast('Relationship Pulse 已更新', 'success');
    } catch (error) {
      logClientError('love-map-baseline-save-failed', error);
      showToast('關係脈動更新失敗，請稍後再試', 'error');
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
      showToast('共同方向已保存', 'success');
    } catch (error) {
      logClientError('love-map-goal-save-failed', error);
      showToast('共同方向保存失敗，請稍後再試', 'error');
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
      showToast('已放進 Shared Future', 'success');
    } catch (error) {
      logClientError('love-map-wishlist-add-failed', error);
      showToast('加入未來片段失敗，請稍後再試', 'error');
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
      showToast('Haven 已經提出新的 Shared Future 建議。', 'success');
    } catch (error) {
      logClientError('love-map-shared-future-suggestions-generate-failed', error);
      showToast('AI 建議暫時無法使用，請稍後再試。', 'error');
    } finally {
      setGeneratingSuggestions(false);
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
      showToast('AI 建議暫時無法使用，請稍後再試。', 'error');
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
          : '建議已接受，現在已進入 Shared Future。',
        'success',
      );
    } catch (error) {
      logClientError('love-map-shared-future-suggestion-accept-failed', error);
      showToast('接受建議失敗，請稍後再試。', 'error');
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
            : '這則 refinement 建議已略過。'
          : '這則建議已略過。',
        'success',
      );
    } catch (error) {
      logClientError('love-map-shared-future-suggestion-dismiss-failed', error);
      showToast('略過建議失敗，請稍後再試。', 'error');
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

  const totalPromptCount = cardsByLayer.safe.length + cardsByLayer.medium.length + cardsByLayer.deep.length;
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

  return (
    <div className="space-y-[clamp(1.75rem,3vw,3rem)]">
      <LoveMapSystemCover
        eyebrow="Love Map / Relationship System"
        title="把 Haven 已經知道、仍在學、以及你們想一起走向的未來，放回同一個地方。"
        description="這裡不是抽象的感情頁，也不是單純的提示卡牆。它應該誠實地告訴你們：目前的關係方向是什麼、你留下了哪些內在地圖、以及你們正一起把什麼未來放進生活裡。"
        pulse={
          system.has_partner
            ? `Haven 目前把你們的關係理解放成四塊：共同方向、被記住的故事、你的內在地圖，以及一起靠近的未來。現在有 ${storyAnchorCount} 個故事錨點、${filledLayerCount}/3 層心內地圖，Shared Future 收著 ${system.stats.wishlist_count} 個片段。`
            : '你還沒有完成雙向伴侶連結，所以 Haven 只能先保留你的單邊脈動。完成連結後，這裡才會變成真正的 shared relationship system。'
        }
        primaryHref={system.has_partner ? '#relationship-pulse' : '/settings#settings-relationship'}
        primaryLabel={system.has_partner ? '先看目前的共同方向' : '先完成伴侶連結'}
        highlights={
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-[1.85rem] border border-white/56 bg-white/74 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/78">Relationship Pulse</p>
              <p className="mt-2 font-art text-[2rem] leading-none text-card-foreground">
                {system.baseline.mine ? '已建立' : '待開始'}
              </p>
              <p className="mt-2 type-caption text-muted-foreground">目前的五維脈動與共同方向會在這裡對齊。</p>
            </div>

            <div className="rounded-[1.85rem] border border-white/56 bg-white/74 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/78">Inner Landscape</p>
              <p className="mt-2 font-art text-[2rem] leading-none text-card-foreground">
                {filledLayerCount}
                <span className="ml-1 text-lg text-muted-foreground">/ 3</span>
              </p>
              <p className="mt-2 type-caption text-muted-foreground">這些是你留下的理解筆記，不會被自動當成共享真相。</p>
            </div>

            <div className="rounded-[1.85rem] border border-white/56 bg-white/74 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/78">Shared Future</p>
              <p className="mt-2 font-art text-[2rem] leading-none text-card-foreground">{system.stats.wishlist_count}</p>
              <p className="mt-2 type-caption text-muted-foreground">已被放進共同藍圖、值得反覆回來看的未來片段。</p>
            </div>
          </div>
        }
        aside={
          <>
            <LoveMapSnapshotCard
              eyebrow="What Haven knows"
              title={system.partner?.partner_name ? `${system.me.full_name || '你'} × ${system.partner.partner_name}` : '尚未完成共享配對'}
              description={
                system.has_partner
                  ? '這一頁只展示目前真的有資料支持的關係知識。沒有被看見的部分，Haven 不會假裝自己已經知道。'
                  : '完成伴侶連結後，Haven 才能把這裡從單邊筆記，變成真正的 shared relationship system。'
              }
            >
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <div className="rounded-[1.55rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/80">共同方向</p>
                  <p className="mt-2 type-section-title text-card-foreground">{getGoalLabel(system.couple_goal?.goal_slug)}</p>
                </div>
                <div className="rounded-[1.55rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/80">最近活動</p>
                  <p className="mt-2 type-section-title text-card-foreground">{lastActivityLabel ?? '尚未建立'}</p>
                </div>
              </div>
            </LoveMapSnapshotCard>

            <LoveMapSnapshotCard
              eyebrow="Trust boundary"
              title="共識、反思、未來，分開呈現。"
              description="Relationship Pulse 與 Shared Future 是共享知識；Inner Landscape 是你自己的理解地圖。這個邊界會讓 Haven 比較值得相信。"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3 rounded-[1.45rem] border border-white/50 bg-white/70 px-4 py-3">
                  <span className="type-section-title text-card-foreground">共同方向</span>
                  <Badge variant="success" size="sm">Shared truth</Badge>
                </div>
                <div className="flex items-center justify-between gap-3 rounded-[1.45rem] border border-white/50 bg-white/70 px-4 py-3">
                  <span className="type-section-title text-card-foreground">故事切片</span>
                  <Badge variant="metadata" size="sm">Memory-backed</Badge>
                </div>
                <div className="flex items-center justify-between gap-3 rounded-[1.45rem] border border-white/50 bg-white/70 px-4 py-3">
                  <span className="type-section-title text-card-foreground">你的內在地圖</span>
                  <Badge variant="metadata" size="sm">Personal reflection</Badge>
                </div>
                <div className="flex items-center justify-between gap-3 rounded-[1.45rem] border border-white/50 bg-white/70 px-4 py-3">
                  <span className="type-section-title text-card-foreground">共同藍圖</span>
                  <Badge variant="success" size="sm">Shared future</Badge>
                </div>
              </div>
            </LoveMapSnapshotCard>
          </>
        }
      />

      <LoveMapSection
        id="relationship-pulse"
        eyebrow="Relationship Pulse"
        title="先把目前的共同方向看清楚。"
        description="Love Map v1 不再只是問題卡頁。它先用最有限但真實的資料，回答目前的關係脈動與北極星方向。"
        aside={
          <div className="space-y-3">
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Mine</p>
              <p className="mt-2 type-section-title text-card-foreground">
                {system.stats.baseline_ready_mine ? '已填寫' : '尚未填寫'}
              </p>
            </div>
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Partner</p>
              <p className="mt-2 type-section-title text-card-foreground">
                {system.stats.baseline_ready_partner ? '已填寫' : '尚未填寫'}
              </p>
            </div>
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">North star</p>
              <p className="mt-2 type-section-title text-card-foreground">{getGoalLabel(system.couple_goal?.goal_slug)}</p>
            </div>
          </div>
        }
      >
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
          <div className="rounded-[2rem] border border-white/58 bg-white/80 p-5 shadow-soft md:p-6">
            <div className="space-y-2">
              <Badge variant="metadata" size="sm">Five-dimensional pulse</Badge>
              <h3 className="type-h3 text-card-foreground">用五個維度，先對現在誠實。</h3>
              <p className="type-body-muted text-muted-foreground">
                這不是評分遊戲，而是替現在的關係建立一個可以回來對照的位置。
              </p>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-2">
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

            <div className="mt-5 flex flex-wrap items-center gap-3">
              <Button loading={savingBaseline} onClick={() => void handleSaveBaseline()}>
                保存 Relationship Pulse
              </Button>
              <p className="type-caption text-muted-foreground">先對現在誠實，比一次填到完美更重要。</p>
            </div>
          </div>

          <div className="rounded-[2rem] border border-white/58 bg-white/80 p-5 shadow-soft md:p-6">
            <div className="space-y-2">
              <Badge variant="metadata" size="sm">Shared direction</Badge>
              <h3 className="type-h3 text-card-foreground">替你們選一個目前最值得靠近的方向。</h3>
              <p className="type-body-muted text-muted-foreground">
                北極星目標不需要定一輩子，只需要讓 Haven 知道你們最近真正想一起照顧的是哪一塊。
              </p>
            </div>

            {!system.has_partner ? (
              <LoveMapStatePanel
                eyebrow="Partner required"
                title="先完成伴侶連結"
                description="共同方向屬於 shared truth。完成雙向伴侶連結後，這裡才會真正開始累積。"
                tone="quiet"
                actionLabel="去設定完成連結"
                onAction={() => {
                  if (typeof window !== 'undefined') {
                    window.location.href = '/settings#settings-relationship';
                  }
                }}
              />
            ) : (
              <>
                <div className="mt-5 grid gap-3">
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

                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <Button loading={savingGoal} disabled={!goalDraft} onClick={() => void handleSaveGoal()}>
                    保存共同方向
                  </Button>
                  <p className="type-caption text-muted-foreground">目前方向：{getGoalLabel(system.couple_goal?.goal_slug)}</p>
                </div>
              </>
            )}
          </div>
        </div>
      </LoveMapSection>

      <LoveMapSection
        id="story"
        eyebrow="Story"
        title="把真正被留下來的 shared memory，放回你們的關係故事裡。"
        description="Story 不是 scrapbook，也不是 AI 替你們寫的總結。它只指向 Haven 已經真的看見、而且值得你們回來重看的那些記憶錨點。"
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
                只來自 Haven 已經留下的 shared memory，不替你們發明不存在的關係結論。
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
            onAction={() => {
              if (typeof window !== 'undefined') {
                window.location.href = '/settings#settings-relationship';
              }
            }}
          />
        ) : !system.story.available ? (
          <LoveMapStatePanel
            eyebrow="Story is still quiet"
            title="你們的故事還沒有累積到足夠的記憶錨點。"
            description="等更多 journal、共同卡片或 appreciation 被留下來後，這裡才會開始誠實地長出關係故事。"
            tone="quiet"
            actionLabel="去 Memory 看看"
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

            <Link
              href="/memory"
              className="inline-flex items-center gap-2 rounded-full border border-white/58 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
            >
              去 Memory 看完整 shared archive
              <Sparkles className="h-4 w-4" aria-hidden />
            </Link>
          </div>
        )}
      </LoveMapSection>

      <LoveMapSection
        id="inner-landscape"
        eyebrow="Inner Landscape"
        title="把你的 relationship reflections 留成可回讀的內在地圖。"
        description="Love Map notes 不是共享檔案，也不是 Haven 自動替兩個人下的結論。它們是你願意留下的理解，會幫 Haven 之後更誠實地知道什麼是 shared truth、什麼只是個人反思。"
        aside={
          <div className="space-y-3">
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Prompts</p>
              <p className="mt-2 type-section-title text-card-foreground">{totalPromptCount}</p>
            </div>
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Trust rule</p>
              <p className="mt-2 type-caption text-muted-foreground">
                這些是你的筆記，不會因為存在於 Love Map 就被自動公開給伴侶。
              </p>
            </div>
          </div>
        }
      >
        {!system.has_partner ? (
          <div className="space-y-4">
            <LoveMapStatePanel
              eyebrow="Partner required"
              title="先完成雙向伴侶連結，Love Map 才會開始成形。"
              description="現在你仍然可以先看 prompts，但 Haven 不會在沒有 partner pair 的情況下，把這一區當成正式 relationship system。"
              tone="quiet"
              actionLabel="去設定完成連結"
              onAction={() => {
                if (typeof window !== 'undefined') {
                  window.location.href = '/settings#settings-relationship';
                }
              }}
            />

            {cardsQuery.isError ? (
              <LoveMapStatePanel
                eyebrow="Prompt preview"
                title="Love Map prompts 暫時沒有順利載入"
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
                        description="沒有關係，等 partner 連結完成後，Love Map 仍會從這一層開始慢慢長出來。"
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
          LAYERS.map((layer) => (
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
          ))
        )}
      </LoveMapSection>

      <LoveMapSection
        id="shared-future"
        eyebrow="Shared Future"
        title="把你們想一起靠近的生活，放進同一張藍圖裡。"
        description="Blueprint 不該孤零零地放在另一個頁面。Love Map v1 會把共同未來帶進關係系統裡，讓 Haven 不只記得你們怎麼想，也記得你們想一起走去哪裡。"
        aside={
          <div className="space-y-3">
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Wishlist count</p>
              <p className="mt-2 type-section-title text-card-foreground">{system.stats.wishlist_count}</p>
            </div>
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">AI pending</p>
              <p className="mt-2 type-section-title text-card-foreground">
                {aiPendingCount}
              </p>
            </div>
            <div className="rounded-[1.55rem] border border-white/56 bg-white/72 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">Blueprint</p>
              <p className="mt-2 type-caption text-muted-foreground">Love Map 在這裡只顯示高價值摘要，完整 future shelf 仍保留在 Blueprint。</p>
            </div>
          </div>
        }
      >
        {!system.has_partner ? (
          <LoveMapStatePanel
            eyebrow="Partner required"
            title="共同未來需要先有共同配對。"
            description="連結完成後，Shared Future 才會變成真正可以一起累積、一起回看的關係知識。"
            tone="quiet"
            actionLabel="去設定完成連結"
            onAction={() => {
              if (typeof window !== 'undefined') {
                window.location.href = '/settings#settings-relationship';
              }
            }}
          />
        ) : (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.02fr)_minmax(0,0.98fr)]">
            <div className="grid gap-4">
              <LoveMapFutureComposer
                eyebrow="AI Suggested Updates"
                title="先讓 Haven 提案，再由你決定什麼值得變成 shared truth。"
                description="這些建議只會出現在你的個人 review queue。接受前，它們都不是共同真相；接受後，才會寫進 Shared Future。"
                footer={
                  <div className="rounded-[1.55rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                    <p className="type-caption text-muted-foreground">
                      Pending AI suggestions 只對你可見，伴侶只會看到你接受之後真正放進 Shared Future 的項目。
                    </p>
                  </div>
                }
              >
                <div className="space-y-4">
                  {suggestionQuery.isError ? (
                    <LoveMapStatePanel
                      eyebrow="AI suggestions"
                      title="建議佇列暫時沒有順利載入。"
                      description="目前的 Shared Future 仍然可用，但這一層 AI review queue 需要重新讀取。"
                      tone="quiet"
                      actionLabel="重新讀取建議"
                      onAction={() => {
                        void suggestionQuery.refetch();
                      }}
                    />
                  ) : suggestionQuery.isLoading ? (
                    <LoveMapStatePanel
                      eyebrow="AI suggestions"
                      title="Haven 正在讀取你的 review queue。"
                      description="如果這裡有待審核的 Shared Future 建議，它們會在幾秒內出現。"
                      tone="quiet"
                    />
                  ) : pendingSuggestions.length === 0 ? (
                    <LoveMapStatePanel
                      eyebrow="AI suggestions"
                      title="目前沒有待你審核的 Shared Future 建議。"
                      description="當 Haven 能從你留下的 journals、共同卡片與 appreciation 裡看到足夠清楚的方向時，它才會提出建議。"
                      tone="quiet"
                      actionLabel="讓 Haven 提出 Shared Future 建議"
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
                      Haven 只會在 evidence 足夠清楚時提出建議，並且不會直接寫進 shared truth。
                    </p>
                    <Button
                      variant="secondary"
                      loading={generatingSuggestions}
                      disabled={generatingSuggestions || suggestionQuery.isLoading}
                      onClick={() => {
                        void handleGenerateSuggestions();
                      }}
                    >
                      {pendingSuggestions.length > 0 ? '重新整理建議' : '讓 Haven 提案'}
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
                      {item.notes ? (
                        <div className="rounded-[1.4rem] border border-primary/10 bg-primary/8 px-4 py-4">
                          <p className="type-body whitespace-pre-line text-card-foreground">{item.notes}</p>
                        </div>
                      ) : null}

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
                前往完整 Blueprint
                <Sparkles className="h-4 w-4" aria-hidden />
              </Link>
            </div>

            <LoveMapFutureComposer
              eyebrow="Add a future fragment"
              title="把下一個想一起變成真的片段，放進這張圖裡。"
              description="不需要很大，可以只是一種生活感、一個儀式、一段季節裡想一起完成的畫面。"
              footer={
                <div className="rounded-[1.55rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                  <p className="type-caption text-muted-foreground">
                    Shared Future 會保留在 Love Map 裡當作關係知識摘要，而完整清單仍在 Blueprint。
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
