'use client';

import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Heart, Loader2 } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import { useLoveMapCards, useLoveMapNotes } from '@/hooks/queries';
import { queryKeys } from '@/lib/query-keys';
import { createOrUpdateLoveMapNote } from '@/services/api-client';
import { logClientError } from '@/lib/safe-error-log';
import { useToast } from '@/hooks/useToast';
import type { LoveMapNotePublic } from '@/services/api-client';

const LAYERS = ['safe', 'medium', 'deep'] as const;
const LAYER_LABELS: Record<string, string> = { safe: '安全層', medium: '中層', deep: '深層' };

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
      <div className="min-h-[40vh] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" aria-hidden />
      </div>
    );
  }

  return (
    <>
      <h1 className="font-art text-2xl font-bold text-foreground mb-2 flex items-center gap-2.5 animate-slide-up-fade">
        <span className="icon-badge !w-10 !h-10" aria-hidden><Heart className="w-5 h-5" /></span>
        愛情地圖
      </h1>
      <p className="text-body text-muted-foreground mb-8">
        依深度分層的題目與你的筆記，一起更認識彼此。
      </p>

      {LAYERS.map((layer, idx) => (
        <section key={layer} className={`mb-8 animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}`}>
          <h2 className="font-art text-lg font-semibold text-card-foreground mb-3 flex items-center gap-2">
            <span className="icon-badge" aria-hidden><Heart className="w-3.5 h-3.5" /></span>
            {LAYER_LABELS[layer] ?? layer}
          </h2>
          <GlassCard className="p-6 mb-4 relative overflow-hidden">
            <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
            <h3 className="text-body font-art font-medium text-foreground mb-2">題目</h3>
            <ul className="space-y-2">
              {(layer === 'safe' ? cards.safe : layer === 'medium' ? cards.medium : cards.deep).map((c) => (
                <li key={c.id} className="text-caption text-muted-foreground border-l-2 border-primary/30 pl-3">
                  {c.question}
                </li>
              ))}
              {((layer === 'safe' ? cards.safe : layer === 'medium' ? cards.medium : cards.deep).length === 0) && (
                <li className="text-caption text-muted-foreground">暫無題目</li>
              )}
            </ul>
          </GlassCard>
          <GlassCard className="p-6 relative overflow-hidden">
            <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/15 to-transparent" aria-hidden />
            <label htmlFor={`note-${layer}`} className="block text-body font-art font-medium text-foreground mb-2">
              我的筆記
            </label>
            <textarea
              id={`note-${layer}`}
              value={draft[layer] ?? ''}
              onChange={(e) => setDraft((d) => ({ ...d, [layer]: e.target.value }))}
              placeholder="寫下你的想法..."
              className="w-full rounded-input border border-input bg-background px-3 py-2 text-foreground focus-visible:ring-2 focus-visible:ring-ring min-h-[100px] resize-y"
              maxLength={5000}
            />
            <button
              type="button"
              onClick={() => handleSaveNote(layer)}
              disabled={saving === layer}
              className="mt-3 rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-t border-t-white/30 px-5 py-2 text-body font-medium shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
              aria-label={`儲存${LAYER_LABELS[layer]}筆記`}
            >
              {saving === layer ? (
                <Loader2 className="w-4 h-4 animate-spin inline" aria-hidden />
              ) : (
                '儲存'
              )}
            </button>
          </GlassCard>
        </section>
      ))}
    </>
  );
}
