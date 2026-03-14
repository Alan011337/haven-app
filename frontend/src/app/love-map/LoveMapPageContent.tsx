'use client';

import { useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useLoveMapCards, useLoveMapNotes } from '@/hooks/queries';
import { queryKeys } from '@/lib/query-keys';
import { createOrUpdateLoveMapNote } from '@/services/api-client';
import { logClientError } from '@/lib/safe-error-log';
import { useToast } from '@/hooks/useToast';
import type {
  LoveMapCardSummary,
  LoveMapNotePublic,
} from '@/services/api-client';
import Badge from '@/components/ui/Badge';
import LoveMapSkeleton from './LoveMapSkeleton';
import {
  LoveMapChapterNav,
  LoveMapCover,
  LoveMapLayerStage,
  LoveMapOverviewCard,
  LoveMapPromptCard,
  LoveMapReflectionStudio,
  LoveMapStatePanel,
} from './LoveMapPrimitives';

const LAYERS = ['safe', 'medium', 'deep'] as const;
type LoveMapLayer = (typeof LAYERS)[number];

const LAYER_META: Record<
  LoveMapLayer,
  {
    label: string;
    eyebrow: string;
    title: string;
    description: string;
    studioTitle: string;
    studioDescription: string;
    placeholder: string;
    helperText: string;
    emptyPromptTitle: string;
    emptyPromptDescription: string;
    anchor: string;
    tone: LoveMapLayer;
  }
> = {
  safe: {
    label: '安全層',
    eyebrow: 'Outer Edge',
    title: '先從那些讓彼此安心的細節開始。',
    description:
      '這一層不是表面的資料，而是關於偏好、節奏、界線與小習慣的輪廓。當這些細節被好好說出來，兩個人的相處才會開始變得有方向。',
    studioTitle: '把你已經知道，卻很少被完整說出的那一層留下來。',
    studioDescription:
      '寫下彼此喜歡的節奏、容易被照顧到的方式、會讓人放鬆的語氣與細節。這會成為後面兩層的底圖。',
    placeholder: '寫下關於彼此的小喜歡、生活節奏、讓人安心的偏好與界線...',
    helperText: '先記錄日常裡已經被看見的細節，讓這張地圖從安全感開始成形。',
    emptyPromptTitle: '這一層暫時還沒有問題卡。',
    emptyPromptDescription:
      '沒關係，先把你已經知道的偏好與細節寫下來。Love Map 的輪廓仍然會先從這裡開始。',
    anchor: 'layer-safe',
    tone: 'safe',
  },
  medium: {
    label: '中層',
    eyebrow: 'Shared Middle',
    title: '走近那些日常背後真正重要的在意。',
    description:
      '當表面的偏好被確認之後，這一層會開始碰觸價值感、壓力來源、被理解的方式，以及兩個人如何在不安時彼此靠近。',
    studioTitle: '把那些需要被慢慢理解的在意，寫成可以重讀的一段。',
    studioDescription:
      '中層不是快速回答，而是一段讓彼此知道「為什麼這對我重要」的說明。它讓理解不只停在表面資訊。',
    placeholder: '寫下最近在意的事、被理解的方式、壓力來時希望對方如何靠近你...',
    helperText: '這一層適合寫完整一點，讓彼此看見偏好背後真正重要的原因。',
    emptyPromptTitle: '這一層今天很安靜。',
    emptyPromptDescription:
      '如果還沒有新的問題卡，也可以先把最近一段關係中的在意、擔心與期待寫下來。',
    anchor: 'layer-medium',
    tone: 'medium',
  },
  deep: {
    label: '深層',
    eyebrow: 'Inner Terrain',
    title: '把只有在足夠信任時才會說出的核心，也留在地圖裡。',
    description:
      '深層不是更難，而是更需要安全。它關於脆弱、長久期待、過往經驗留下的印記，以及那些真正想被對方理解的核心。',
    studioTitle: '把最核心的那一部分，寫在足夠安靜的地方。',
    studioDescription:
      '這裡不追求完整，也不需要一次說完。只要留下今天願意被看見的一小塊，這張地圖就會更真實一些。',
    placeholder: '寫下那些只有在足夠信任時才會提起的脆弱、核心期待、長久在意或想被理解的事...',
    helperText: '深層適合慢慢寫，不需要一次說完；重要的是讓真實有地方被好好放下。',
    emptyPromptTitle: '深層暫時還沒有展開新的提問。',
    emptyPromptDescription:
      '先把今天願意被看見的一小塊寫下來。真正深的理解，通常就是這樣慢慢長出來的。',
    anchor: 'layer-deep',
    tone: 'deep',
  },
};

function formatRelativeMapTime(value: string | null | undefined) {
  if (!value) return null;
  return new Date(value).toLocaleString('zh-TW', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function LoveMapPageContent() {
  const queryClient = useQueryClient();
  const cardsQuery = useLoveMapCards();
  const notesQuery = useLoveMapNotes();
  const [saving, setSaving] = useState<LoveMapLayer | null>(null);
  const [draft, setDraft] = useState<Record<LoveMapLayer, string>>({
    safe: '',
    medium: '',
    deep: '',
  });
  const { showToast } = useToast();
  const cards = cardsQuery.data ?? null;
  const loading = cardsQuery.isLoading || notesQuery.isLoading;
  const notes = useMemo(() => notesQuery.data ?? [], [notesQuery.data]);

  useEffect(() => {
    if (notes.length === 0) return;

    const initial = notes.reduce<Record<LoveMapLayer, string>>(
      (acc, note) => {
        if (note.layer === 'safe' || note.layer === 'medium' || note.layer === 'deep') {
          acc[note.layer] = note.content;
        }
        return acc;
      },
      { safe: '', medium: '', deep: '' },
    );

    setDraft((current) => ({ ...initial, ...current }));
  }, [notes]);

  const cardsByLayer = useMemo<Record<LoveMapLayer, LoveMapCardSummary[]>>(
    () => ({
      safe: cards?.safe ?? [],
      medium: cards?.medium ?? [],
      deep: cards?.deep ?? [],
    }),
    [cards],
  );

  const notesByLayer = useMemo<Record<LoveMapLayer, LoveMapNotePublic | null>>(
    () =>
      notes.reduce<Record<LoveMapLayer, LoveMapNotePublic | null>>(
        (acc, note) => {
          if (note.layer === 'safe' || note.layer === 'medium' || note.layer === 'deep') {
            acc[note.layer] = note;
          }
          return acc;
        },
        { safe: null, medium: null, deep: null },
      ),
    [notes],
  );

  const lastUpdatedByLayer = useMemo<Record<LoveMapLayer, string | null>>(
    () => ({
      safe: formatRelativeMapTime(notesByLayer.safe?.updated_at),
      medium: formatRelativeMapTime(notesByLayer.medium?.updated_at),
      deep: formatRelativeMapTime(notesByLayer.deep?.updated_at),
    }),
    [notesByLayer],
  );

  const filledLayerCount = useMemo(
    () =>
      LAYERS.filter((layer) => {
        const content = draft[layer] ?? notesByLayer[layer]?.content ?? '';
        return content.trim().length > 0;
      }).length,
    [draft, notesByLayer],
  );

  const totalPromptCount = useMemo(
    () => LAYERS.reduce((sum, layer) => sum + cardsByLayer[layer].length, 0),
    [cardsByLayer],
  );

  const firstIncompleteLayer = useMemo(
    () =>
      LAYERS.find((layer) => {
        const content = draft[layer] ?? notesByLayer[layer]?.content ?? '';
        return content.trim().length === 0;
      }) ?? null,
    [draft, notesByLayer],
  );

  const chapterNavItems = useMemo(
    () =>
      LAYERS.map((layer) => ({
        href: `#${LAYER_META[layer].anchor}`,
        label: LAYER_META[layer].label,
        description: LAYER_META[layer].description,
        complete: (draft[layer] ?? notesByLayer[layer]?.content ?? '').trim().length > 0,
      })),
    [draft, notesByLayer],
  );

  const handleSaveNote = async (layer: LoveMapLayer) => {
    setSaving(layer);
    try {
      await createOrUpdateLoveMapNote(layer, draft[layer] ?? notesByLayer[layer]?.content ?? '');
      await queryClient.invalidateQueries({ queryKey: queryKeys.loveMapNotes() });
      showToast('已儲存', 'success');
    } catch (e) {
      logClientError('love-map-note-save-failed', e);
      showToast('儲存失敗，請稍後再試', 'error');
    } finally {
      setSaving(null);
    }
  };

  if (cardsQuery.isError) {
    return (
      <LoveMapStatePanel
        eyebrow="Love Map Unavailable"
        title="這張地圖暫時還打不開。"
        description="Love Map 題目載入失敗了。你的既有筆記不會消失，但現在需要重新載入一次，才能把這張地圖完整展開。"
        tone="error"
        actionLabel="重新載入題目"
        onAction={() => {
          void cardsQuery.refetch();
        }}
      />
    );
  }

  if (loading || !cards) {
    return <LoveMapSkeleton />;
  }

  const nextLayer = firstIncompleteLayer ? LAYER_META[firstIncompleteLayer] : LAYER_META.safe;

  return (
    <div className="space-y-[clamp(1.75rem,3vw,3rem)]">
      <LoveMapCover
        eyebrow="Love Map"
        title="讓理解彼此這件事，擁有一張真正可以一起慢慢展開的地圖。"
        description="Love Map 不該像一份資料表。它更像一張會隨時間長出輪廓的 shared landscape，讓兩個人從安心、在意，到更深的核心，逐步把彼此真正記住。"
        pulse={`目前已寫下 ${filledLayerCount}/3 層，整張地圖共收進 ${totalPromptCount} 個 prompts。先把關係中值得被看見的那一層寫下來，再慢慢往更深的地方走。`}
        ctaHref={`#${nextLayer.anchor}`}
        ctaLabel={firstIncompleteLayer ? '從尚未寫下的下一層開始' : '重新讀這張地圖'}
        highlights={
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-[1.85rem] border border-white/56 bg-white/74 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/78">Written</p>
              <p className="mt-2 font-art text-[2rem] leading-none text-card-foreground">
                {filledLayerCount}
                <span className="ml-1 text-lg text-muted-foreground">/ 3</span>
              </p>
              <p className="mt-2 type-caption text-muted-foreground">已經被寫下來、可供你們重讀的章節。</p>
            </div>

            <div className="rounded-[1.85rem] border border-white/56 bg-white/74 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/78">Prompts</p>
              <p className="mt-2 font-art text-[2rem] leading-none text-card-foreground">{totalPromptCount}</p>
              <p className="mt-2 type-caption text-muted-foreground">這張地圖目前展開的問題卡總數。</p>
            </div>

            <div className="rounded-[1.85rem] border border-white/56 bg-white/74 p-4 shadow-soft">
              <p className="type-micro uppercase text-primary/78">Next Chapter</p>
              <p className="mt-2 font-art text-[1.7rem] leading-tight text-card-foreground">{nextLayer.label}</p>
              <p className="mt-2 type-caption text-muted-foreground">
                {firstIncompleteLayer ? '從這一層開始，讓地圖繼續往內展開。' : '三層都已留下內容，現在適合一起回讀。'}
              </p>
            </div>
          </div>
        }
        aside={
          <>
            <LoveMapOverviewCard
              eyebrow="Map Overview"
              title="這不是整理資訊，而是累積理解。"
              description="Love Map 會把關係中的理解分成三層距離。安全層讓你們認出彼此，中層讓你們開始真正讀懂彼此，深層則讓信任有地方落下來。"
            >
              <div className="space-y-3">
                {LAYERS.map((layer) => (
                  <div
                    key={layer}
                    className="flex items-center justify-between gap-3 rounded-[1.45rem] border border-white/50 bg-white/70 px-4 py-3"
                  >
                    <div className="space-y-1">
                      <p className="type-section-title text-card-foreground">{LAYER_META[layer].label}</p>
                      <p className="type-caption text-muted-foreground">{cardsByLayer[layer].length} 個 prompts</p>
                    </div>
                    <Badge variant={(draft[layer] ?? notesByLayer[layer]?.content ?? '').trim() ? 'success' : 'metadata'} size="sm">
                      {(draft[layer] ?? notesByLayer[layer]?.content ?? '').trim() ? '已寫下' : '待展開'}
                    </Badge>
                  </div>
                ))}
              </div>
            </LoveMapOverviewCard>

            <LoveMapChapterNav items={chapterNavItems} />
          </>
        }
      />

      {LAYERS.map((layer) => {
        const stageMeta = LAYER_META[layer];
        const promptCards = cardsByLayer[layer];
        const currentValue = draft[layer] ?? notesByLayer[layer]?.content ?? '';
        const isFilled = currentValue.trim().length > 0;

        return (
          <LoveMapLayerStage
            key={layer}
            id={stageMeta.anchor}
            eyebrow={stageMeta.eyebrow}
            title={stageMeta.title}
            description={stageMeta.description}
            tone={stageMeta.tone}
            aside={
              <div className="flex flex-wrap gap-2">
                <Badge variant="metadata" size="md" className="bg-white/72 text-card-foreground">
                  {promptCards.length} 個 prompts
                </Badge>
                <Badge variant={isFilled ? 'success' : 'outline'} size="md" className="bg-white/66">
                  {isFilled ? '已寫下這一層' : '這一層仍留白'}
                </Badge>
              </div>
            }
          >
            <LoveMapReflectionStudio
              eyebrow={`${stageMeta.label} Reflection Studio`}
              title={stageMeta.studioTitle}
              description={stageMeta.studioDescription}
              textareaId={`note-${layer}`}
              textareaLabel="這一層的筆記"
              value={currentValue}
              onChange={(value) =>
                setDraft((current) => ({
                  ...current,
                  [layer]: value,
                }))
              }
              onSave={() => {
                void handleSaveNote(layer);
              }}
              saving={saving === layer}
              lastUpdated={lastUpdatedByLayer[layer]}
              helperText={stageMeta.helperText}
              placeholder={stageMeta.placeholder}
              promptCount={promptCards.length}
            />

            {promptCards.length > 0 ? (
              <div className="grid gap-4 lg:grid-cols-2">
                {promptCards.map((card, index) => (
                  <LoveMapPromptCard
                    key={card.id}
                    index={index + 1}
                    title={card.title}
                    description={card.description}
                    question={card.question}
                  />
                ))}
              </div>
            ) : (
              <LoveMapStatePanel
                eyebrow={`${stageMeta.label} Prompts`}
                title={stageMeta.emptyPromptTitle}
                description={stageMeta.emptyPromptDescription}
                tone="quiet"
              />
            )}
          </LoveMapLayerStage>
        );
      })}
    </div>
  );
}
