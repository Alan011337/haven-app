'use client';

import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Sparkles } from 'lucide-react';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Input';
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

  /* ── Loading ── */

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center" role="status">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />
        <span className="sr-only">載入中</span>
      </div>
    );
  }

  /* ── Content ── */

  return (
    <div className="space-y-8 md:space-y-10">
      {/* Page identity */}
      <div className="space-y-3 animate-slide-up-fade">
        <h1 className="font-art text-[2rem] leading-[1.05] tracking-tight text-gradient-gold md:text-[2.8rem]">
          藍圖與願望清單
        </h1>
        <p className="text-sm leading-relaxed text-muted-foreground">
          寫下你們共同的願望，讓夢想成為兩人之間的約定。
        </p>
      </div>

      {/* Add-wish form */}
      <section className="animate-slide-up-fade-1 rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(248,252,250,0.90),rgba(241,247,244,0.82))] p-6 shadow-soft md:p-8">
        <h2 className="mb-5 font-art text-lg text-card-foreground">
          寫下一個新願望
        </h2>
        <form onSubmit={handleAdd} className="space-y-4">
          <Input
            id="blueprint-title"
            label="願望"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="例如：週末一起去爬山"
            maxLength={500}
          />
          <Textarea
            id="blueprint-notes"
            label="備註（選填）"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="想補充什麼都可以寫在這裡…"
            maxLength={2000}
            className="min-h-[72px]"
          />
          <div className="flex justify-end">
            <Button
              type="submit"
              variant="primary"
              size="md"
              loading={submitting}
              aria-label="加入願望清單"
            >
              許下願望
            </Button>
          </div>
        </form>
      </section>

      {/* Wish collection */}
      {items.length > 0 && (
        <p className="animate-slide-up-fade-2 text-xs tabular-nums text-muted-foreground/70">
          {items.length} 個共同願望
        </p>
      )}
      {items.length === 0 ? (
        <div className="animate-slide-up-fade-2 rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] px-6 py-12 text-center shadow-soft">
          <Sparkles
            className="mx-auto h-8 w-8 text-primary/40"
            aria-hidden
          />
          <p className="mt-4 font-art text-lg text-card-foreground/80">
            還沒有願望
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            寫下第一個願望，開始收集你們的夢想。
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((item, idx) => (
            <li
              key={item.id}
              className={[
                'rounded-[1.5rem] border border-white/50 bg-white/70 px-5 py-4 shadow-soft backdrop-blur-sm',
                'transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift',
                idx < 4 ? `animate-slide-up-fade-${Math.min(idx + 2, 5)}` : '',
              ].join(' ')}
            >
              <div
                className={[
                  'border-l-[3px] pl-4',
                  item.added_by_me ? 'border-l-primary/35' : 'border-l-[rgba(214,181,136,0.45)]',
                ].join(' ')}
              >
                <p className="text-sm font-medium leading-relaxed text-card-foreground">
                  {item.title}
                </p>
                {item.notes && (
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                    {item.notes}
                  </p>
                )}
                <p className="mt-2 text-xs text-muted-foreground/70">
                  {item.added_by_me ? '我' : '伴侶'} · {new Date(item.created_at).toLocaleDateString('zh-TW')}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
