'use client';

import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ListTodo, Loader2 } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import { useBlueprint } from '@/hooks/queries';
import { queryKeys } from '@/lib/query-keys';
import { addBlueprintItem } from '@/services/api-client';
import { logClientError } from '@/lib/safe-error-log';
import { useToast } from '@/hooks/useToast';

export default function BlueprintPageContent() {
  const queryClient = useQueryClient();
  const { data: items = [], isLoading: loading } = useBlueprint();
  const [submitting, setSubmitting] = useState(false);
  const [title, setTitle] = useState('');
  const [notes, setNotes] = useState('');
  const { showToast } = useToast();

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const t = title.trim();
    if (!t) {
      showToast('請輸入願望或項目', 'error');
      return;
    }
    setSubmitting(true);
    try {
      await addBlueprintItem(t, notes.trim() || undefined);
      setTitle('');
      setNotes('');
      await queryClient.invalidateQueries({ queryKey: queryKeys.blueprint() });
      showToast('已加入願望清單', 'success');
    } catch (err) {
      logClientError('blueprint-add-failed', err);
      showToast('加入失敗，請稍後再試', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[40vh] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" aria-hidden />
      </div>
    );
  }

  return (
    <>
      <h1 className="font-art text-2xl font-bold text-foreground mb-2 flex items-center gap-2.5 animate-slide-up-fade">
        <span className="icon-badge !w-10 !h-10" aria-hidden><ListTodo className="w-5 h-5" /></span>
        藍圖與願望清單
      </h1>
      <p className="text-body text-muted-foreground mb-8">
        一起寫下想做的事，兩週沒互動時會提醒你們來場小約會。
      </p>

      <GlassCard className="p-6 mb-6 relative overflow-hidden animate-slide-up-fade-1">
        <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/30 to-transparent" aria-hidden />
        <h2 className="font-art text-lg font-semibold text-card-foreground mb-4">新增願望</h2>
        <form onSubmit={handleAdd} className="space-y-4">
          <div>
            <label htmlFor="blueprint-title" className="block text-body font-medium text-foreground mb-1">
              標題
            </label>
            <input
              id="blueprint-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="例如：週末一起去爬山"
              maxLength={500}
              className="w-full rounded-input border border-input bg-background px-3 py-2 text-foreground placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
          <div>
            <label htmlFor="blueprint-notes" className="block text-body font-medium text-foreground mb-1">
              備註（選填）
            </label>
            <textarea
              id="blueprint-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="補充說明..."
              maxLength={2000}
              className="w-full rounded-input border border-input bg-background px-3 py-2 text-foreground placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring min-h-[72px] resize-y"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-t border-t-white/30 px-6 py-2.5 font-medium shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
            aria-label="加入願望清單"
          >
            {submitting ? <Loader2 className="w-5 h-5 animate-spin inline" aria-hidden /> : '加入'}
          </button>
        </form>
      </GlassCard>

      <div className="section-divider mb-4" />
      <h2 className="font-art text-lg font-semibold text-card-foreground mb-3 animate-slide-up-fade-2">願望清單</h2>
      {items.length === 0 ? (
        <GlassCard className="p-8 text-center animate-slide-up-fade-3">
          <p className="text-body text-muted-foreground">還沒有願望，新增一筆吧！</p>
        </GlassCard>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id}>
              <GlassCard className="p-4 list-item-premium">
                <p className="text-body font-medium text-foreground">{item.title}</p>
                {item.notes && (
                  <p className="text-caption text-muted-foreground mt-1">{item.notes}</p>
                )}
                <p className="text-caption text-muted-foreground mt-2">
                  {item.added_by_me ? '我新增' : '伴侶新增'} · {new Date(item.created_at).toLocaleDateString('zh-TW')}
                </p>
              </GlassCard>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
