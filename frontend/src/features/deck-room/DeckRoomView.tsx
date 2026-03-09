'use client';

import Link from 'next/link';
import { ArrowLeft, History, HeartHandshake, LockKeyhole, RefreshCw, Send, Sparkles, User } from 'lucide-react';

import { getDeckDisplayName, getDeckMeta } from '@/lib/deck-meta';
import { getDepthPresentation, resolveDepthLevel } from '@/lib/depth-level';
import Skeleton from '@/components/ui/Skeleton';
import Button from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Input';
import { GlassCard } from '@/components/haven/GlassCard';
import type { DeckRoomViewModel } from './types';

export default function DeckRoomView({
  category,
  historyHref,
  partnerDisplayName,
  loading,
  session,
  answer,
  submitting,
  partnerTyping,
  roomStatus,
  resultData,
  handleAnswerChange,
  handleSubmit,
  handleNextCard,
  handleBackToDecks,
  quotaExceeded,
  handleUpgrade,
}: DeckRoomViewModel) {
  const deckMeta = getDeckMeta(category);
  const categoryDisplayName = getDeckDisplayName(category);
  const depthLevel = resolveDepthLevel(session?.card.depth_level);
  const depthStyles = getDepthPresentation(depthLevel);

  if (loading) {
    return (
      <div className="min-h-screen bg-muted/40 space-page relative overflow-hidden" role="status" aria-live="polite">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-64 h-64 rounded-full bg-primary/5 blur-hero-orb animate-breathe pointer-events-none" aria-hidden />
        <div className="mx-auto max-w-md space-y-4">
          <Skeleton className="h-8 w-40" variant="shimmer" />
          <Skeleton className="h-64 w-full rounded-card" variant="shimmer" />
          <Skeleton className="h-36 w-full rounded-card" variant="shimmer" />
          <p className="text-center text-caption text-muted-foreground font-medium animate-breathe">正在為你們準備話題...</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-screen bg-muted/40 flex items-center justify-center space-page" role="alert">
        <GlassCard className="p-10 text-center max-w-sm">
          <p className="text-body text-muted-foreground">無法載入卡片，請稍後再試</p>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-muted/40 flex flex-col">
      {/* Premium frosted header */}
      <header className="bg-card/80 backdrop-blur-2xl border-b border-border/60 space-page shadow-soft sticky top-0 z-10">
        <div className="flex items-center justify-between relative max-w-md mx-auto w-full">
          <button
            type="button"
            onClick={handleBackToDecks}
            className="p-2 -ml-2 text-muted-foreground hover:text-card-foreground hover:bg-muted/50 rounded-full transition-all duration-haven ease-haven z-20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            aria-label="返回牌組"
          >
            <ArrowLeft className="w-5 h-5" aria-hidden />
          </button>

          <h1 className="absolute left-0 right-0 text-center font-art font-bold text-card-foreground text-title tracking-tight pointer-events-none">
            <span className="inline-flex items-center gap-2">
              {deckMeta && <deckMeta.Icon className={`w-4 h-4 ${deckMeta.iconColor}`} strokeWidth={2.2} aria-hidden />}
              {categoryDisplayName}
            </span>
          </h1>

          <Link
            href={historyHref}
            className="p-2 -mr-2 text-muted-foreground hover:text-card-foreground hover:bg-muted/50 rounded-full transition-all duration-haven ease-haven z-20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            aria-label="歷史紀錄"
          >
            <History className="w-5 h-5" aria-hidden />
          </Link>
        </div>
      </header>

      {quotaExceeded && (
        <div className="mt-3 max-w-md mx-auto w-full space-page animate-page-enter">
          <Button
            variant="primary"
            size="lg"
            className="w-full"
            leftIcon={<Sparkles className="w-4 h-4" />}
            onClick={() => void handleUpgrade?.()}
          >
            升級方案，繼續抽卡
          </Button>
        </div>
      )}

      <main className="flex-1 space-page flex flex-col items-center max-w-md mx-auto w-full pb-10">
        {/* Question card */}
        <GlassCard
          className={`w-full p-8 flex flex-col items-center text-center relative overflow-hidden mb-8 min-h-[260px] justify-center transition-all duration-haven ease-haven group hover:shadow-lift animate-page-enter ${depthStyles.accentFrameClass}`}
        >
          {/* Top accent bar */}
          <div
            className={`absolute top-0 left-0 w-full h-1 ${depthStyles.topAccentClass} group-hover:h-1.5 transition-all duration-haven ease-haven`}
          />

          <div className="mb-5 flex flex-wrap items-center justify-center gap-2 gap-block">
            <span className="text-caption font-bold tracking-[0.2em] text-muted-foreground/70 uppercase">Topic</span>
            <span className={`text-caption font-bold px-3 py-0.5 rounded-full backdrop-blur-sm ${depthStyles.badgeClass}`}>
              Depth {depthLevel} · {depthStyles.label}
            </span>
          </div>
          <p className="mb-4 text-caption text-muted-foreground/80 leading-relaxed max-w-[28rem]">
            {depthStyles.guidance}
          </p>
          <h2 className="text-title font-art font-bold text-card-foreground tracking-tight leading-relaxed mb-4">{session.card.question}</h2>
          {session.card.title && (
            <p className="text-body text-muted-foreground font-medium mt-2 font-art italic">—— {session.card.title} ——</p>
          )}
          {session.card.tags && session.card.tags.length > 0 && (
            <div className="mt-4 flex flex-wrap items-center justify-center gap-1.5 gap-block">
              {session.card.tags.slice(0, 4).map((tag) => (
                <span
                  key={tag}
                  className="text-caption px-2.5 py-0.5 rounded-full bg-muted/50 text-muted-foreground border border-border/50 backdrop-blur-sm"
                >
                  #{tag}
                </span>
              ))}
            </div>
          )}
        </GlassCard>

        <div className="w-full transition-all duration-haven ease-haven">
          {/* Panel-enter: duration-500 intentional for content reveal; excluded from Haven micro-motion tokens by design. */}
          {roomStatus === 'IDLE' && (
            <div className="relative group animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="relative">
                <Textarea
                  value={answer}
                  onChange={(e) => handleAnswerChange(e.target.value)}
                  placeholder={`分享給 ${partnerDisplayName} 聽...`}
                  maxLength={2000}
                  className="pr-14 resize-none h-36 min-h-[140px]"
                  aria-label="分享給伴侶的回答"
                />
                <Button
                  type="button"
                  size="md"
                  variant={answer.trim() ? 'primary' : 'secondary'}
                  disabled={submitting || !answer.trim()}
                  className="absolute bottom-4 right-4 p-3"
                  leftIcon={submitting ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                  onClick={() => void handleSubmit()}
                />
              </div>
              {partnerTyping && (
                <div className="mt-3 inline-flex items-center gap-2 text-caption text-muted-foreground" role="status">
                  <span className="inline-flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:0ms]" />
                    <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:150ms]" />
                    <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:300ms]" />
                  </span>
                  <span className="font-medium">{partnerDisplayName} 正在輸入...</span>
                </div>
              )}
            </div>
          )}

          {roomStatus === 'WAITING_PARTNER' && (
            <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <GlassCard className="text-center p-10 relative overflow-hidden">
                <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />

                <div className="mb-6 inline-flex p-4 bg-gradient-to-br from-primary/15 to-primary/5 rounded-2xl ring-4 ring-primary/10 animate-breathe">
                  <LockKeyhole className="w-8 h-8 text-primary" />
                </div>

                <h3 className="font-art font-bold text-card-foreground text-title tracking-tight mb-2">答案已上鎖</h3>

                <p className="text-body text-muted-foreground leading-relaxed mb-8">
                  你的回答已保存！
                  <br />
                  <span className="text-muted-foreground">
                    當 <strong className="text-primary font-medium">{partnerDisplayName}</strong> 回答後，
                    <br />
                    雙方的答案將同時揭曉。
                  </span>
                </p>

                <div className="flex flex-col gap-3">
                  <Button
                    variant="primary"
                    size="lg"
                    className="w-full"
                    leftIcon={<RefreshCw className="w-4 h-4" />}
                    onClick={handleNextCard}
                  >
                    不等了，先抽下一張
                  </Button>

                  <Button
                    variant="ghost"
                    size="md"
                    className="w-full text-muted-foreground"
                    onClick={handleBackToDecks}
                  >
                    暫時離開，晚點再看
                  </Button>
                </div>
              </GlassCard>
            </div>
          )}

          {roomStatus === 'COMPLETED' &&
            resultData &&
            String(resultData.session_id) === String(session.id) && (
              <div key={resultData.session_id} className="space-y-6 animate-in fade-in zoom-in-95 duration-500">
                <div className="space-y-5 px-1">
                  {/* My answer (right) */}
                  <div className="flex gap-3 justify-end items-end">
                    <div className="max-w-[85%] flex flex-col items-end">
                      <div className="bg-gradient-to-br from-primary to-primary/85 text-primary-foreground px-5 py-3.5 rounded-2xl rounded-br-md shadow-soft text-body leading-relaxed tracking-wide">
                        {resultData.my_answer}
                      </div>
                      <span className="text-caption text-muted-foreground mt-1.5 pr-1 font-medium">我</span>
                    </div>
                    <span className="icon-badge !w-9 !h-9 shrink-0 mb-6" aria-hidden>
                      <User className="w-4 h-4" />
                    </span>
                  </div>

                  {/* Partner answer (left) */}
                  <div className="flex gap-3 justify-start items-end">
                    <span className="icon-badge !w-9 !h-9 !bg-gradient-to-br !from-accent/12 !to-accent/4 !border-accent/8 shrink-0 mb-6" aria-hidden>
                      <HeartHandshake className="w-4 h-4 text-accent" />
                    </span>
                    <div className="max-w-[85%] flex flex-col items-start">
                      <div className="bg-card border border-border/60 text-card-foreground px-5 py-3.5 rounded-2xl rounded-bl-md shadow-soft text-body leading-relaxed tracking-wide">
                        {resultData.partner_answer}
                      </div>
                      <span className="text-caption text-muted-foreground mt-1.5 pl-1 font-medium">{partnerDisplayName}</span>
                    </div>
                  </div>
                </div>

                <div className="section-divider my-6 mx-4" />

                <Button
                  variant="primary"
                  size="lg"
                  className="w-full"
                  leftIcon={<RefreshCw className="w-5 h-5" />}
                  onClick={handleNextCard}
                >
                  聊聊下一個話題
                </Button>
              </div>
            )}
        </div>
      </main>
    </div>
  );
}
