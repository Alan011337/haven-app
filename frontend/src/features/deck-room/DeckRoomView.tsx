'use client';

import Link from 'next/link';
import {
  History,
  HeartHandshake,
  LockKeyhole,
  RefreshCw,
  Send,
  Sparkles,
  User,
} from 'lucide-react';

import { getDeckDisplayName } from '@/lib/deck-meta';
import { DEPTH_OPTIONS, getDepthPresentation, resolveDepthLevel } from '@/lib/depth-level';
import { getDeckEditorialCopy } from '@/features/decks/deck-copy';
import {
  DeckRoomStage,
  DeckShell,
  DeckStatePanel,
} from '@/features/decks/ui/DeckPrimitives';
import { routeLinkCtaClasses } from '@/features/decks/ui/routeStyleHelpers';
import Skeleton from '@/components/ui/Skeleton';
import Badge from '@/components/ui/Badge';
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
  selectedDepth,
  handleDepthChange,
  handleNextCard,
  handleBackToDecks,
  quotaExceeded,
  handleUpgrade,
}: DeckRoomViewModel) {
  const categoryDisplayName = getDeckDisplayName(category);
  const editorialCopy = getDeckEditorialCopy(category);
  const depthLevel = resolveDepthLevel(session?.card.depth_level);
  const depthStyles = getDepthPresentation(depthLevel);

  const depthSelector = (
    <div className="stack-block">
      <p className="type-micro uppercase text-muted-foreground/70">下一輪想怎麼聊</p>
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="選擇下一輪話題深度">
        {DEPTH_OPTIONS.map((opt) => {
          const isSelected = selectedDepth === opt.level;
          const style = getDepthPresentation(opt.level);
          return (
            <button
              key={opt.level}
              type="button"
              onClick={() => handleDepthChange(isSelected ? null : opt.level)}
              data-testid={`deck-room-depth-option-${opt.level}`}
              className={`px-4 py-2 rounded-full text-xs font-medium transition-all duration-haven ease-haven
                ${isSelected
                  ? style.badgeClass
                  : 'bg-white/50 text-muted-foreground hover:bg-white/70 border border-transparent'
                }
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`}
              aria-pressed={isSelected}
              aria-label={`${opt.label} — ${opt.description}`}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
      {selectedDepth ? (
        <p className="type-caption text-muted-foreground/70 animate-in fade-in duration-300">
          {DEPTH_OPTIONS.find((o) => o.level === selectedDepth)?.description}
        </p>
      ) : null}
    </div>
  );

  if (loading) {
    return (
      <DeckShell
        eyebrow="牌組現場"
        title={categoryDisplayName}
        subtitle="正在整理這一輪對話的舞台與紀錄。"
        backLabel="回牌組圖書館"
        onBack={handleBackToDecks}
        actions={
          <Link
            href={historyHref}
            className={routeLinkCtaClasses.neutral}
          >
            <History className="h-4 w-4" aria-hidden />
            歷史檔案館
          </Link>
        }
        containerClassName="max-w-5xl"
      >
        <DeckRoomStage
          eyebrow="準備中"
          title="正在為你們整理今晚的題目。"
          description="先把題目、深度與對話舞台整理好，再把這一輪話題交到你們手上。"
        >
          <div className="space-y-4">
            <Skeleton className="h-8 w-48 rounded-full" variant="shimmer" aria-hidden />
            <Skeleton className="h-24 w-full rounded-[1.5rem]" variant="shimmer" aria-hidden />
            <Skeleton className="h-40 w-full rounded-[1.5rem]" variant="shimmer" aria-hidden />
          </div>
        </DeckRoomStage>
      </DeckShell>
    );
  }

  if (!session) {
    return (
      <DeckShell
        eyebrow="牌組現場"
        title={categoryDisplayName}
        subtitle="這一輪題目沒有成功載入，但不代表牌組本身不可用。"
        backLabel="回牌組圖書館"
        onBack={handleBackToDecks}
        actions={
          <Link
            href={historyHref}
            className={routeLinkCtaClasses.neutral}
          >
            <History className="h-4 w-4" aria-hidden />
            歷史檔案館
          </Link>
        }
        containerClassName="max-w-5xl"
      >
        <DeckStatePanel
          eyebrow="暫時無法開啟"
          title="這張卡片沒有成功開啟。"
          description="通常只是一時的連線或同步問題。回到圖書館重新選一次，或稍後再打開，都不會影響既有紀錄。"
          actionLabel="回到牌組圖書館"
          onAction={handleBackToDecks}
        />
      </DeckShell>
    );
  }

  const topActions = (
    <Link
      href={historyHref}
      className={routeLinkCtaClasses.neutral}
    >
      <History className="h-4 w-4" aria-hidden />
      歷史檔案館
    </Link>
  );

  return (
    <DeckShell
      eyebrow={editorialCopy?.eyebrow ?? '牌組現場'}
      title={categoryDisplayName}
      subtitle={editorialCopy?.roomPrompt ?? '把題目留在舞台中央，讓彼此的回應慢慢把這一輪對話完成。'}
      backLabel="回牌組圖書館"
      onBack={handleBackToDecks}
      actions={topActions}
      containerClassName="max-w-5xl"
    >
      {quotaExceeded ? (
        <DeckStatePanel
          eyebrow="方案上限"
          title="今天的抽卡次數已經到上限。"
          description="你們今天的配額已經用完，但這輪對話與所有歷史紀錄都還在。若想繼續抽卡，可以直接升級方案。"
          actionLabel="升級方案，繼續抽卡"
          onAction={() => void handleUpgrade?.()}
          tone="paper"
        />
      ) : null}

        <DeckRoomStage
          eyebrow="本輪題目"
          title={session.card.question}
          description={depthStyles.guidance}
          badge={`本輪節奏 · ${depthStyles.label}`}
        >
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px] lg:items-start">
          <div className="stack-block">
            {session.card.title ? (
              <p className="type-caption font-medium italic text-muted-foreground">—— {session.card.title} ——</p>
            ) : null}
            {session.card.tags && session.card.tags.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {session.card.tags.slice(0, 4).map((tag) => (
                  <Badge
                    key={tag}
                    variant="metadata"
                    size="sm"
                    className="bg-white/72 text-muted-foreground shadow-none"
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
            ) : null}
          </div>
          <GlassCard className={`rounded-[1.6rem] border-white/55 p-5 ${depthStyles.badgeClass}`}>
            <div className="stack-block">
              <p className="type-micro uppercase text-card-foreground/72">場景提示</p>
              <p className="type-body-muted text-card-foreground/88">
                {editorialCopy?.shortHook ?? '讓這張卡片替今晚先打開一個恰到好處的入口。'}
              </p>
            </div>
          </GlassCard>
        </div>
      </DeckRoomStage>

      {roomStatus === 'IDLE' ? (
        <DeckRoomStage
          eyebrow="你的回應"
          title="把第一個真正想說的版本留在這裡。"
          description="不需要一次寫得完整。先把最真實的那一段留下來，這張卡的節奏就會開始動。"
          tone="paper"
          footer={
            partnerTyping ? (
              <div className="stack-inline type-caption text-muted-foreground" role="status">
                <span className="inline-flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:0ms]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:150ms]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:300ms]" />
                </span>
                <span>{partnerDisplayName} 也正在靠近這輪對話。</span>
              </div>
            ) : null
          }
        >
          <div className="stack-section">
            <Textarea
              value={answer}
              onChange={(e) => handleAnswerChange(e.target.value)}
              placeholder={`把想對 ${partnerDisplayName} 說的那一段寫下來…`}
              maxLength={2000}
              className="min-h-[15rem] resize-none border-white/55 bg-white/82 px-5 py-5 text-base leading-8 shadow-glass-inset"
              aria-label="分享給伴侶的回答"
            />
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="type-caption text-muted-foreground">
                這一輪沒有時間壓力，先把最真實的版本留下來。
              </div>
              <Button
                type="button"
                size="lg"
                variant={answer.trim() ? 'primary' : 'secondary'}
                disabled={submitting || !answer.trim()}
                leftIcon={submitting ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                onClick={() => void handleSubmit()}
              >
                {submitting ? '正在封存你的回答' : '送出這張卡片'}
              </Button>
            </div>
          </div>
        </DeckRoomStage>
      ) : null}

      {roomStatus === 'WAITING_PARTNER' ? (
        <DeckRoomStage
          eyebrow="等待對方"
          title="你的回答已封存，現在輪到對方。"
          description={`這一輪對話已經在進行中。等 ${partnerDisplayName} 也完成後，雙方內容會一起揭曉。`}
          tone="mist"
          footer={
            <div className="stack-section">
              {depthSelector}
              <div className="flex flex-wrap gap-3">
                <Button
                  variant="primary"
                  size="lg"
                  leftIcon={<RefreshCw className="h-4 w-4" />}
                  onClick={handleNextCard}
                >
                  先抽下一張
                </Button>
                <Button variant="ghost" size="lg" onClick={handleBackToDecks}>
                  暫時離開，晚點再看
                </Button>
              </div>
            </div>
          }
        >
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-start">
            <GlassCard className="rounded-[1.6rem] border-white/55 bg-white/78 p-5">
              <div className="flex items-start gap-3">
                <span className="mt-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-primary/16 bg-primary/10 shadow-soft" aria-hidden>
                  <LockKeyhole className="h-4 w-4 text-primary" />
                </span>
                <div className="stack-block">
                  <p className="type-micro uppercase text-primary/72">已封存</p>
                  <p className="type-body text-card-foreground">
                    你的版本已經被穩穩收好。現在這張卡暫時不需要再修改，只需要等待它完成雙向交換。
                  </p>
                </div>
              </div>
            </GlassCard>
            <GlassCard className="rounded-[1.6rem] border-white/55 bg-white/74 p-5">
              <div className="stack-block">
                <p className="type-micro uppercase text-primary/72">伴侶狀態</p>
                <Badge variant="status" size="md" className="w-fit bg-white/80 px-3 py-2 text-card-foreground shadow-soft">
                  <HeartHandshake className="h-4 w-4 text-primary" aria-hidden />
                  {partnerDisplayName} 還在這張卡的另一端
                </Badge>
              </div>
            </GlassCard>
          </div>
        </DeckRoomStage>
      ) : null}

      {roomStatus === 'COMPLETED' && resultData && String(resultData.session_id) === String(session.id) ? (
        <DeckRoomStage
          eyebrow="雙向揭曉"
          title="這輪對話已經完整展開。"
          description="現在先好好把彼此的版本讀完，再決定要不要進到下一張卡。"
          tone="ritual"
          footer={
            <div className="stack-section">
              {depthSelector}
              <Button
                variant="primary"
                size="lg"
                leftIcon={<Sparkles className="h-4 w-4" />}
                onClick={handleNextCard}
              >
                聊聊下一個話題
              </Button>
            </div>
          }
        >
          <div className="grid gap-4 md:grid-cols-2">
            <section className="rounded-[1.6rem] border border-primary/12 bg-primary/6 p-5">
              <div className="stack-inline type-micro uppercase text-primary/72">
                <User className="h-4 w-4" aria-hidden />
                我的版本
              </div>
              <p className="mt-4 type-body text-card-foreground">{resultData.my_answer}</p>
            </section>
            <section className="rounded-[1.6rem] border border-white/55 bg-white/76 p-5">
              <div className="stack-inline type-micro uppercase text-muted-foreground">
                <HeartHandshake className="h-4 w-4 text-primary" aria-hidden />
                {partnerDisplayName}
              </div>
              <p className="mt-4 type-body text-card-foreground">{resultData.partner_answer}</p>
            </section>
          </div>
        </DeckRoomStage>
      ) : null}
    </DeckShell>
  );
}
