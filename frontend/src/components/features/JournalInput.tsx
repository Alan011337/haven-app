// frontend/src/components/features/JournalInput.tsx
"use client";

import { useCallback, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { MAX_JOURNAL_CONTENT_LENGTH } from '@/services/api-client';
import { HomeComposerStage } from '@/features/home/HomePrimitives';
import { cn } from '@/lib/utils';

const JOURNAL_HOME_SEED_STORAGE_KEY = 'haven_journal_home_seed_v1';

interface JournalInputProps {
  className?: string;
  variant?: 'default' | 'cover';
}

export default function JournalInput({
  className,
  variant = 'default',
}: JournalInputProps) {
  const router = useRouter();
  const [content, setContent] = useState('');

  const handoffToStudio = useCallback(() => {
    if (typeof window !== 'undefined') {
      const normalized = content.replace(/\r\n/g, '\n').trimEnd();
      if (normalized.trim()) {
        window.sessionStorage.setItem(JOURNAL_HOME_SEED_STORAGE_KEY, normalized);
      } else {
        window.sessionStorage.removeItem(JOURNAL_HOME_SEED_STORAGE_KEY);
      }
    }
    router.push('/journal?compose=1');
  }, [content, router]);

  const form = (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        handoffToStudio();
      }}
      className="flex flex-col gap-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          <span className="inline-flex items-center rounded-full border border-primary/15 bg-primary/8 px-3 py-1 text-[11px] font-semibold tracking-[0.2em] text-primary uppercase">
            Journal Entry
          </span>
          <span className="inline-flex items-center rounded-full border border-border/80 bg-white/70 px-3 py-1 text-[11px] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
            反思寫作
          </span>
        </div>
        <p className="font-mono text-xs tabular-nums text-muted-foreground/70">
          {content.length}/{MAX_JOURNAL_CONTENT_LENGTH}
        </p>
      </div>

      <label htmlFor="journal-content" className="sr-only">
        日記內容
      </label>
      <div
        className={cn(
          'relative overflow-hidden rounded-[1.85rem] border shadow-soft',
          variant === 'cover'
            ? 'home-surface-paper home-paper-lines border-[rgba(219,204,187,0.5)]'
            : 'border-white/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.82),rgba(250,246,241,0.78))]',
        )}
      >
        {variant !== 'cover' ? (
          <div
            className="absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-primary/22 to-transparent"
            aria-hidden
          />
        ) : null}
        <textarea
          id="journal-content"
          aria-label="日記內容"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="先留下一句、幾行，或只是今天的第一個感受。接下來的標題、圖片與分享邊界，都在 Journal 書房裡慢慢整理。"
          className={cn(
            'relative z-10 w-full resize-none bg-transparent text-[15px] leading-[2] text-foreground outline-none transition-all duration-haven ease-haven placeholder:font-light placeholder:text-muted-foreground/50 md:px-6',
            variant === 'cover' ? 'min-h-[320px] px-6 py-8 md:min-h-[360px] md:px-7' : 'min-h-[220px] px-5 py-6',
            'focus-visible:bg-white/35',
          )}
          maxLength={MAX_JOURNAL_CONTENT_LENGTH}
          suppressHydrationWarning={true}
        />
      </div>

      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="max-w-xl space-y-1.5">
          <p className="text-[0.68rem] uppercase tracking-[0.28em] text-primary/80">反思寫作</p>
          <p className="text-sm leading-7 text-muted-foreground">
            Home 先替你收住今天的第一句；真正更完整的反思寫作，會在 Journal 書房裡慢慢長成一頁。你可以先帶著這段進去，也可以直接開一頁空白 draft，先插圖再慢慢寫。
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/journal?compose=1"
            className="inline-flex items-center justify-center gap-2 rounded-full border border-white/58 bg-white/82 px-5 py-3 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
          >
            進入 Journal 書房
          </Link>
          <button
            type="submit"
            className="inline-flex items-center justify-center gap-2 rounded-full border-t border-t-white/30 bg-gradient-to-b from-primary to-primary/90 px-8 py-3 font-medium text-primary-foreground shadow-satin-button transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            {content.trim() ? '帶著這段進入 Journal 書房' : '開始新的一頁'}
          </button>
        </div>
      </div>
    </form>
  );

  return variant === 'cover' ? (
    <div className={cn('space-y-4', className)}>
      <div className="flex flex-wrap items-center justify-between gap-3 px-1">
        <div className="space-y-1">
          <p className="text-[0.72rem] uppercase tracking-[0.34em] text-primary/80">Cover Story</p>
          <h3 className="font-art text-[1.9rem] leading-tight text-card-foreground md:text-[2.25rem]">
            Home 先收住今天，再把它送進 Journal 書房。
          </h3>
        </div>
        <div className="rounded-full border border-white/50 bg-white/66 px-3 py-2 text-[0.68rem] uppercase tracking-[0.28em] text-primary/75 shadow-soft">
          反思寫作
        </div>
      </div>
      {form}
    </div>
  ) : (
    <HomeComposerStage
      eyebrow="反思寫作"
      title="先留下今天最想帶進 Journal 的那幾句。"
      description="Home 先保留開頭；更完整的反思寫作，會在 Journal 書房裡慢慢完成。"
      className={className}
    >
      {form}
    </HomeComposerStage>
  );
}
