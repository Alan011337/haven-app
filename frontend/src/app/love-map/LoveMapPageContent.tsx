'use client';

import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Textarea } from '@/components/ui/Input';
import Button from '@/components/ui/Button';
import { useLoveMapCards, useLoveMapNotes } from '@/hooks/queries';
import { queryKeys } from '@/lib/query-keys';
import { createOrUpdateLoveMapNote } from '@/services/api-client';
import { logClientError } from '@/lib/safe-error-log';
import { useToast } from '@/hooks/useToast';
import type { LoveMapNotePublic } from '@/services/api-client';

const LAYERS = ['safe', 'medium', 'deep'] as const;

const LAYER_CONFIG: Record<string, {
  label: string;
  depth: number;
  surface: string;
  questionAccent: string;
}> = {
  safe: {
    label: '安全層',
    depth: 1,
    surface: 'bg-[linear-gradient(180deg,rgba(248,252,250,0.90),rgba(241,247,244,0.82))]',
    questionAccent: 'border-l-primary/20',
  },
  medium: {
    label: '中層',
    depth: 2,
    surface: 'bg-[linear-gradient(180deg,rgba(255,252,248,0.90),rgba(248,244,238,0.82))]',
    questionAccent: 'border-l-primary/35',
  },
  deep: {
    label: '深層',
    depth: 3,
    surface: 'bg-[linear-gradient(180deg,rgba(255,250,247,0.90),rgba(250,243,234,0.82))]',
    questionAccent: 'border-l-primary/50',
  },
};

export default function LoveMapPageContent() {
  const queryClient = useQueryClient();
  const cardsQuery = useLoveMapCards();
  const notesQuery = useLoveMapNotes();
  const [saving, setSaving] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const { showToast } = useToast();

  const cards = cardsQuery.data ?? null;
  const loading = cardsQuery.isLoading || notesQuery.isLoading;

  useEffect(() => {
    const raw = notesQuery.data;
    if (!raw || raw.length === 0) return;
    const initial: Record<string, string> = {};
    raw.forEach((n: LoveMapNotePublic) => { initial[n.layer] = n.content; });
    setDraft((d) => ({ ...initial, ...d }));
  }, [notesQuery.data]);

  const handleSaveNote = async (layer: string) => {
    setSaving(layer);
    try {
      await createOrUpdateLoveMapNote(layer as 'safe' | 'medium' | 'deep', draft[layer] ?? '');
      await queryClient.invalidateQueries({ queryKey: queryKeys.loveMapNotes() });
      showToast('已儲存', 'success');
    } catch (e) {
      logClientError('love-map-note-save-failed', e);
      showToast('儲存失敗，請稍後再試', 'error');
    } finally {
      setSaving(null);
    }
  };

  if (loading || !cards) {
    return (
      <div className="space-y-8 md:space-y-10">
        <div className="space-y-3">
          <div className="h-10 w-36 animate-pulse rounded-[1.5rem] bg-muted/60" aria-hidden />
          <div className="h-4 w-56 animate-pulse rounded-full bg-muted/40" aria-hidden />
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-48 animate-pulse rounded-[2rem] bg-white/60 shadow-soft" aria-hidden />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-8 md:space-y-10">

      {/* ── Page identity ── */}
      <div className="space-y-3 animate-slide-up-fade">
        <h1 className="font-art text-[2rem] leading-[1.05] text-gradient-gold md:text-[2.8rem]">
          愛情地圖
        </h1>
        <p className="text-sm text-muted-foreground">
          一起慢慢認識彼此更深的地方。
        </p>
      </div>

      {/* ── Layer sections ── */}
      {LAYERS.map((layer, idx) => {
        const config = LAYER_CONFIG[layer];
        const questions = layer === 'safe' ? cards.safe : layer === 'medium' ? cards.medium : cards.deep;

        return (
          <section
            key={layer}
            className={`rounded-[2rem] border border-white/50 ${config.surface} p-6 shadow-soft md:p-8 animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}`}
          >
            <div className="space-y-6">

              {/* Layer header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/55 bg-white/70 font-art text-sm font-medium text-primary/80 shadow-soft">
                    {config.depth}
                  </span>
                  <h2 className="font-art text-xl text-card-foreground">{config.label}</h2>
                </div>
                <span className="text-xs text-muted-foreground">{questions.length} 題</span>
              </div>

              {/* Questions */}
              {questions.length > 0 ? (
                <div className="space-y-2">
                  {questions.map((q) => (
                    <div
                      key={q.id}
                      className={`rounded-[1.2rem] border-l-[3px] ${config.questionAccent} bg-white/55 px-4 py-3 text-sm leading-relaxed text-card-foreground backdrop-blur-sm`}
                    >
                      {q.question}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">這一層暫時沒有題目。</p>
              )}

              {/* Note area */}
              <div className="space-y-3">
                <Textarea
                  id={`note-${layer}`}
                  label="我的筆記"
                  value={draft[layer] ?? ''}
                  onChange={(e) => setDraft((d) => ({ ...d, [layer]: e.target.value }))}
                  placeholder="寫下你的想法…"
                  maxLength={5000}
                  className="min-h-[120px] border-white/50 bg-white/40 backdrop-blur-xl"
                />
                <div className="flex justify-end">
                  <Button
                    variant="primary"
                    size="sm"
                    loading={saving === layer}
                    onClick={() => handleSaveNote(layer)}
                    aria-label={`儲存${config.label}筆記`}
                  >
                    儲存
                  </Button>
                </div>
              </div>

            </div>
          </section>
        );
      })}
    </div>
  );
}
