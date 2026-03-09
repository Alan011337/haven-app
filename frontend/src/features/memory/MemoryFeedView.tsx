'use client';

import Link from 'next/link';
import { TimelineItem, TimelineJournalItem, TimelineCardItem, TimelinePhotoItem } from '@/services/memoryService';
import { GlassCard } from '@/components/haven/GlassCard';
import { getGradientForMood } from '@/lib/mood-background';
import { BookOpen, MessageCircle, Image as ImageIcon } from 'lucide-react';
import Skeleton from '@/components/ui/Skeleton';

function formatDate(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const isToday =
    d.getDate() === now.getDate() &&
    d.getMonth() === now.getMonth() &&
    d.getFullYear() === now.getFullYear();
  if (isToday) return '今天';
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday =
    d.getDate() === yesterday.getDate() &&
    d.getMonth() === yesterday.getMonth() &&
    d.getFullYear() === yesterday.getFullYear();
  if (isYesterday) return '昨天';
  return d.toLocaleDateString('zh-TW', { month: 'short', day: 'numeric', year: 'numeric' });
}

function JournalCard({ item }: { item: TimelineJournalItem }) {
  const gradient = getGradientForMood(item.mood_label ?? undefined);
  return (
    <GlassCard variant="glass" className="overflow-hidden transition-shadow duration-haven ease-haven hover:shadow-lift">
      <div className={`h-1.5 w-full bg-gradient-to-r ${gradient} opacity-85`} aria-hidden />
      <div className="p-4 flex gap-3">
        <span className="icon-badge shrink-0">
          <BookOpen className="w-4 h-4" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-caption text-muted-foreground tabular-nums">{formatDate(item.created_at)}</p>
          {item.mood_label && (
            <span className="text-xs text-muted-foreground mr-2">{item.mood_label}</span>
          )}
          {item.content_preview && (
            <p className="text-body text-card-foreground mt-1 line-clamp-3">{item.content_preview}</p>
          )}
        </div>
      </div>
    </GlassCard>
  );
}

function CardEntry({ item }: { item: TimelineCardItem }) {
  return (
    <GlassCard variant="glass" className="overflow-hidden transition-shadow duration-haven ease-haven hover:shadow-lift">
      <div className="p-4 flex gap-3">
        <span className="icon-badge shrink-0">
          <MessageCircle className="w-4 h-4" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-caption text-muted-foreground tabular-nums">{formatDate(item.revealed_at)}</p>
          <p className="font-art font-semibold text-card-foreground mt-0.5">{item.card_title}</p>
          {item.my_answer && (
            <p className="text-body text-muted-foreground mt-1 line-clamp-2">我：{item.my_answer}</p>
          )}
          {item.partner_answer && (
            <p className="text-body text-muted-foreground line-clamp-2">伴侶：{item.partner_answer}</p>
          )}
        </div>
      </div>
    </GlassCard>
  );
}

function PhotoCard({ item }: { item: TimelinePhotoItem }) {
  return (
    <GlassCard variant="glass" className="overflow-hidden transition-shadow duration-haven ease-haven hover:shadow-lift">
      <div className="p-4 flex gap-3">
        <span className="icon-badge shrink-0">
          <ImageIcon className="w-4 h-4" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-caption text-muted-foreground tabular-nums">{formatDate(item.created_at)}</p>
          <p className="font-medium text-card-foreground mt-0.5">{item.is_own ? '我的照片' : '伴侶的照片'}</p>
          {item.caption && (
            <p className="text-body text-muted-foreground mt-1 line-clamp-2">{item.caption}</p>
          )}
          {!item.caption && (
            <p className="text-body text-muted-foreground mt-1">照片回憶</p>
          )}
        </div>
      </div>
    </GlassCard>
  );
}

export default function MemoryFeedView({
  items,
  loading,
  loadingMore,
  hasMore,
  onLoadMore,
}: {
  items: TimelineItem[];
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  onLoadMore: () => void;
}) {
  if (loading) {
    return (
      <div className="space-y-4 pb-8" aria-busy="true" aria-live="polite">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-24 w-full rounded-card" aria-hidden />
        ))}
      </div>
    );
  }
  if (!items.length) {
    return (
      <div className="text-center py-16 px-4 text-muted-foreground text-body animate-slide-up-fade">
        <span className="icon-badge !w-16 !h-16 !rounded-2xl mx-auto mb-4" aria-hidden>
          <BookOpen className="w-7 h-7" />
        </span>
        <p className="font-art font-semibold text-foreground text-lg">尚無回憶紀錄</p>
        <p className="text-caption mt-2">寫日記或一起抽卡後，這裡會出現你們的時光軸</p>
        <Link
          href="/"
          className="mt-6 inline-block rounded-full bg-gradient-to-b from-primary to-primary/90 px-6 py-2.5 text-body font-medium text-primary-foreground border-t border-t-white/30 shadow-satin-button transition-all duration-haven ease-haven hover:shadow-lift hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 active:scale-95"
        >
          返回首頁
        </Link>
      </div>
    );
  }
  return (
    <div className="space-y-4 pb-8">
      {items.map((item, idx) => {
        const staggerClass = idx < 6 ? `animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}` : '';
        if (item.type === 'journal') {
          return <div key={`j-${item.id}`} className={staggerClass}><JournalCard item={item} /></div>;
        }
        if (item.type === 'card') {
          return <div key={`c-${item.session_id}`} className={staggerClass}><CardEntry item={item} /></div>;
        }
        if (item.type === 'photo') {
          return <div key={`p-${item.id}`} className={staggerClass}><PhotoCard item={item} /></div>;
        }
        return null;
      })}
      {hasMore && (
        <div className="flex justify-center pt-4">
          <button
            type="button"
            onClick={onLoadMore}
            disabled={loadingMore}
            aria-label="載入更多"
            aria-busy={loadingMore}
            className="px-6 py-2.5 rounded-button bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 text-body font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-all duration-haven ease-haven active:scale-[0.97] disabled:opacity-70"
          >
            {loadingMore ? (
              <span className="inline-block h-5 w-20 animate-pulse rounded-card bg-muted-foreground/20" aria-hidden />
            ) : (
              '載入更多'
            )}
          </button>
        </div>
      )}
    </div>
  );
}
