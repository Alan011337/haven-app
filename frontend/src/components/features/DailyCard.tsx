// frontend/src/components/features/DailyCard.tsx

'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { isAxiosError } from 'axios';
import { Loader2, Send, Lock, CheckCircle2, Sparkles, Heart, Quote } from 'lucide-react';
import { trackRitualDraw, trackRitualRespond, trackRitualUnlock } from '@/lib/cuj-events';
import {
  trackCardAnswerSubmitted,
  trackDailyCardRevealed,
} from '@/lib/relationship-events';
import { feedback } from '@/lib/feedback';
import { getDeckDisplayName } from '@/lib/deck-meta';
import { getDepthPresentation, resolveDepthLevel, type DepthLevel } from '@/lib/depth-level';
import {
  getHomeDailyDepthPresentation,
  HOME_DAILY_DEPTH_OPTIONS,
} from '@/lib/home-daily-depth';
import { logClientError } from '@/lib/safe-error-log';
import { cardService, type DailyStatus } from '@/services/cardService';
import { useToast } from '@/hooks/useToast';
import { useDailyStatus } from '@/hooks/queries';
import { isNetworkError } from '@/lib/offline-queue/network';
import { enqueue, generateOperationId } from '@/lib/offline-queue/queue';
import { useAuth } from '@/hooks/use-auth';
import useSocket from '@/hooks/useSocket';
import { useAppearanceStore } from '@/stores/useAppearanceStore';
import { startAdaptivePolling } from '@/lib/adaptive-polling';
import {
  DAILY_CARD_HIDDEN_MULTIPLIER,
  resolveDailyCardPollingIntervalMs,
} from '@/lib/daily-card-polling';

// 小工具：取得名字首字
const getInitial = (name?: string) => name ? name.charAt(0).toUpperCase() : "P";

type SocketEvent = {
  event?: string;
  session_id?: string;
  is_typing?: boolean;
};

const DailyCard = () => {
  const { user } = useAuth();
  const isSolo = user?.mode === 'solo' || !user?.partner_id;
  const { data: status, isLoading: loading, refetch } = useDailyStatus(!!user?.id);
  const [answer, setAnswer] = useState('');
  const [selectedDepth, setSelectedDepth] = useState<DepthLevel | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [partnerTyping, setPartnerTyping] = useState(false);
  const [drawing, setDrawing] = useState(false);
  const { showToast } = useToast();
  const hapticsEnabled = useAppearanceStore((s) => s.hapticsEnabled);
  const hapticStrength = useAppearanceStore((s) => s.hapticStrength);
  const soundEnabled = useAppearanceStore((s) => s.soundEnabled);
  const statusRef = useRef<DailyStatus | null>(null);
  const typingStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const delayedRefreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refetchInFlightRef = useRef<Promise<unknown> | null>(null);
  const lastRefetchAtRef = useRef(0);
  const myTypingSentRef = useRef(false);

  useEffect(() => {
    statusRef.current = status ?? null;
  }, [status]);

  const clearTypingStopTimer = useCallback(() => {
    if (typingStopTimerRef.current) {
      clearTimeout(typingStopTimerRef.current);
      typingStopTimerRef.current = null;
    }
  }, []);

  const clearDelayedRefreshTimer = useCallback(() => {
    if (delayedRefreshTimerRef.current) {
      clearTimeout(delayedRefreshTimerRef.current);
      delayedRefreshTimerRef.current = null;
    }
  }, []);

  const refreshDailyStatus = useCallback(
    async (minIntervalMs = 300) => {
      const now = Date.now();
      if (refetchInFlightRef.current) {
        await refetchInFlightRef.current;
        return;
      }
      if (now - lastRefetchAtRef.current < minIntervalMs) {
        return;
      }
      const task = refetch();
      refetchInFlightRef.current = task;
      try {
        await task;
      } finally {
        lastRefetchAtRef.current = Date.now();
        refetchInFlightRef.current = null;
      }
    },
    [refetch],
  );

  const handleSocketMessage = useCallback(
    (payload: Record<string, unknown>) => {
      const data = payload as SocketEvent;
      if (data.event !== 'CARD_REVEALED') {
        return;
      }
      const currentSessionId = statusRef.current?.session_id;
      if (!currentSessionId || String(data.session_id) !== String(currentSessionId)) {
        return;
      }
      setPartnerTyping(false);
      void refreshDailyStatus();
    },
    [refreshDailyStatus],
  );

  const handlePartnerAction = useCallback((payload: Record<string, unknown>) => {
    const data = payload as SocketEvent;
    if (data.event === 'NEW_CARD_PICKED') {
      const currentStatus = statusRef.current;
      if (!currentStatus?.session_id) {
        return;
      }
      if (String(data.session_id) !== String(currentStatus.session_id)) {
        return;
      }
      void refreshDailyStatus();
      return;
    }
    if (data.event !== 'PARTNER_TYPING') {
      return;
    }
    const currentStatus = statusRef.current;
    if (!currentStatus?.session_id) {
      return;
    }
    if (String(data.session_id) !== String(currentStatus.session_id)) {
      return;
    }
    setPartnerTyping(Boolean(data.is_typing) && currentStatus.state === 'IDLE');
  }, [refreshDailyStatus]);

  const socketRef = useSocket(user?.id, handleSocketMessage, handlePartnerAction);
  const pollingIntervalMs = resolveDailyCardPollingIntervalMs(status);

  const sendTypingSignal = useCallback(
    (isTyping: boolean) => {
      const currentStatus = statusRef.current;
      const activeSessionId = currentStatus?.session_id;
      if (!activeSessionId) {
        return;
      }
      if (isTyping && currentStatus?.state !== 'IDLE') {
        return;
      }
      if (myTypingSentRef.current === isTyping) {
        return;
      }

      const socket = socketRef.current;
      if (!socket || socket.readyState !== WebSocket.OPEN) {
        if (!isTyping) {
          myTypingSentRef.current = false;
        }
        return;
      }

      socket.send(
        JSON.stringify({
          event: 'TYPING',
          session_id: activeSessionId,
          is_typing: isTyping,
        }),
      );
      myTypingSentRef.current = isTyping;
    },
    [socketRef],
  );

  // 智慧輪詢邏輯（可見度/離線狀態自動降載）
  useEffect(() => {
    if (!pollingIntervalMs) return undefined;
    return startAdaptivePolling({
      baseIntervalMs: pollingIntervalMs,
      hiddenMultiplier: DAILY_CARD_HIDDEN_MULTIPLIER,
      jitterRatio: 0.2,
      offlineRetryMs: 5000,
      runImmediately: false,
      onTick: async () => {
        await refreshDailyStatus(1000);
      },
      onError: (error) => {
        logClientError('daily-card-polling-failed', error);
      },
    });
  }, [pollingIntervalMs, refreshDailyStatus]);

  useEffect(() => {
    if (status?.state === 'IDLE') {
      return;
    }
    clearTypingStopTimer();
    sendTypingSignal(false);
    setPartnerTyping(false);
  }, [clearTypingStopTimer, sendTypingSignal, status?.state]);

  useEffect(() => {
    return () => {
      clearTypingStopTimer();
      clearDelayedRefreshTimer();
      sendTypingSignal(false);
    };
  }, [clearDelayedRefreshTimer, clearTypingStopTimer, sendTypingSignal]);

  useEffect(() => {
    setAnswer('');
    clearTypingStopTimer();
    clearDelayedRefreshTimer();
    sendTypingSignal(false);
    setPartnerTyping(false);
  }, [clearDelayedRefreshTimer, clearTypingStopTimer, sendTypingSignal, status?.card?.id, status?.session_id]);

  const handleDraw = async () => {
    if (loading || drawing) return;
    setDrawing(true);
    trackRitualDraw(status?.session_id ?? undefined);
    try {
      await cardService.drawDailyCard(selectedDepth ?? undefined);
      trackDailyCardRevealed({
        session_id: status?.session_id ?? undefined,
      });
      setPartnerTyping(false);
      await refreshDailyStatus(0);
      feedback.onDrawSuccess({ hapticsEnabled, hapticStrength, soundEnabled });
    } catch (error) {
      logClientError('daily-card-draw-failed', error);
      if (isAxiosError(error)) {
        showToast(error.response?.data?.detail || '這張卡這次沒有順利翻開，稍後再試一次。', 'error');
      } else {
        showToast('這張卡這次沒有順利翻開，稍後再試一次。', 'error');
      }
    } finally {
      setDrawing(false);
    }
  };

  const handleSubmit = async () => {
    if (!status?.card || !answer.trim() || submitting) return;
    setSubmitting(true);
    clearTypingStopTimer();
    clearDelayedRefreshTimer();
    sendTypingSignal(false);
    setPartnerTyping(false);
    trackRitualRespond(status.session_id ?? undefined);
    const operationId = generateOperationId();
    try {
      const res = await cardService.respondDailyCard(status.card.id, answer.trim(), {
        idempotencyKey: operationId,
      });
      trackCardAnswerSubmitted({
        session_id: status.session_id ?? undefined,
        card_id: status.card.id,
        content_length: answer.trim().length,
      });

      const nextState = res.status === 'REVEALED' ? 'COMPLETED' : 'WAITING_PARTNER';
      if (nextState === 'COMPLETED') {
        trackRitualUnlock(status.session_id ?? undefined);
        feedback.onUnlockSuccess({ hapticsEnabled, hapticStrength, soundEnabled });
      }

      setAnswer('');

      if (nextState === 'COMPLETED') {
        void refreshDailyStatus(0);
      } else {
        delayedRefreshTimerRef.current = setTimeout(() => {
          void refreshDailyStatus();
          delayedRefreshTimerRef.current = null;
        }, 1500);
      }

    } catch (error) {
      logClientError('daily-card-submit-failed', error);
      if (isNetworkError(error)) {
        try {
          await enqueue(operationId, 'card_respond', {
            card_id: String(status.card.id),
            content: answer.trim(),
          });
          setAnswer('');
          showToast('已存到離線，連線後會自動同步', 'info');
        } catch {
          showToast('這次沒有順利送出回答，先檢查網路連線。', 'error');
        }
        return;
      }
      if (isAxiosError(error)) {
        showToast(error.response?.data?.detail || '這次沒有順利送出回答，先檢查網路連線。', 'error');
      } else {
        showToast('這次沒有順利送出回答，先檢查網路連線。', 'error');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleAnswerChange = useCallback(
    (value: string) => {
      const nextValue = value.slice(0, 2000);
      setAnswer(nextValue);

      const hasContent = nextValue.trim().length > 0;
      if (!hasContent) {
        clearTypingStopTimer();
        sendTypingSignal(false);
        return;
      }

      const currentStatus = statusRef.current;
      if (!currentStatus?.session_id || currentStatus.state !== 'IDLE') {
        return;
      }

      sendTypingSignal(true);
      clearTypingStopTimer();
      typingStopTimerRef.current = setTimeout(() => {
        sendTypingSignal(false);
      }, 1200);
    },
    [clearTypingStopTimer, sendTypingSignal],
  );

  if (loading) return (
    <div className="w-full h-64 flex flex-col items-center justify-center space-y-4 animate-in fade-in duration-500">
      <div className="relative">
        <div className="absolute inset-0 bg-primary/15 rounded-full blur-xl animate-breathe" aria-hidden />
        <Loader2 className="animate-spin text-primary w-8 h-8 relative z-10" aria-hidden />
      </div>
      <p className="text-muted-foreground text-sm font-light tracking-wider">正在連結彼此的心靈...</p>
    </div>
  );

  // === State A: Draw card (no card yet) ===
  // Reveal/ritual: long durations (500/700/1000ms) intentional for daily ritual and result reveal; excluded from Haven micro-motion tokens by design.
  if (!status?.card) {
    const selectedDepthOption = getHomeDailyDepthPresentation(selectedDepth);

    return (
      <div className="relative">
        <div className="absolute -inset-2 bg-primary/15 rounded-card blur-xl opacity-60 transition-opacity duration-1000 ease-out" aria-hidden />
        <div className="relative bg-card/95 backdrop-blur-xl rounded-card p-10 text-center border border-foreground/10 shadow-soft overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" aria-hidden />
          <div className="flex justify-between items-start mb-8">
            <span className="icon-badge !rounded-2xl animate-breathe" aria-hidden>
              <Sparkles className="w-4 h-4" />
            </span>
            <span className="text-[10px] font-art font-bold tracking-[0.2em] text-muted-foreground/60 uppercase">每日儀式</span>
          </div>
          <div className="mx-auto w-28 h-28 bg-gradient-to-br from-muted to-muted/60 rounded-full flex items-center justify-center mb-8 border border-border/50 shadow-soft shadow-glass-inset transition-all duration-haven ease-haven">
            <span className="text-5xl" aria-hidden>🃏</span>
          </div>
          <p className="text-[10px] font-art font-bold tracking-[0.15em] text-muted-foreground/60 uppercase text-center mb-3">
            今晚的節奏
          </p>
          <h3 className="text-2xl font-art font-bold text-foreground mb-3">今晚想怎麼聊？</h3>
          <p className="text-muted-foreground mb-8 font-light leading-relaxed max-w-md mx-auto">
            {isSolo
              ? <>先選今晚想靠近自己的方式，<br />再抽一張剛剛好的題目。</>
              : <>先選今晚想和 <span className="font-semibold text-primary">{status?.partner_name || '伴侶'}</span> 靠近的方式，<br />再抽一張剛剛好的題目。</>
            }
          </p>

          <div className="mb-8" data-testid="home-daily-depth-chooser">
            <div className="grid gap-3 md:grid-cols-3" role="group" aria-label="選擇今晚想聊的節奏">
              {HOME_DAILY_DEPTH_OPTIONS.map((opt) => {
                const isSelected = selectedDepth === opt.level;
                const style = getDepthPresentation(opt.level);
                return (
                  <button
                    key={opt.level}
                    type="button"
                    onClick={() => setSelectedDepth(isSelected ? null : opt.level)}
                    data-testid={`home-daily-depth-option-${opt.level}`}
                    className={`rounded-[1.6rem] border px-4 py-4 text-left transition-all duration-haven ease-haven
                      ${isSelected
                        ? `${style.questionSurfaceClass} ${style.accentFrameClass} text-foreground shadow-soft`
                        : 'bg-muted/35 text-muted-foreground hover:bg-muted/55 border-border/60'
                      }
                      focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background`}
                    aria-pressed={isSelected}
                    aria-label={`${opt.label} — ${opt.description}`}
                  >
                    <span className="block text-sm font-semibold text-foreground">{opt.label}</span>
                    <span className="mt-2 block text-sm leading-6 text-muted-foreground">
                      {opt.description}
                    </span>
                  </button>
                );
              })}
            </div>
            <p className="text-[11px] text-muted-foreground/75 text-center mt-3 font-light animate-in fade-in duration-300">
              {selectedDepthOption
                ? selectedDepthOption.description
                : '先選一個今晚想聊的節奏，再抽一張剛剛好的題目。'}
            </p>
          </div>

          <button
            type="button"
            onClick={handleDraw}
            disabled={!selectedDepthOption || drawing || loading}
            data-testid="home-daily-depth-draw-cta"
            className={`px-8 py-3.5 rounded-full font-medium border-t shadow-satin-button transition-all duration-haven ease-haven flex items-center gap-2 mx-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
              selectedDepthOption && !drawing && !loading
                ? 'bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-t-white/30 hover:shadow-lift hover:-translate-y-0.5 active:scale-95'
                : 'bg-muted text-muted-foreground border-t-transparent shadow-none cursor-not-allowed'
            }`}
          >
            {drawing ? <Loader2 size={16} className="animate-spin" aria-hidden /> : <Sparkles size={16} aria-hidden />}
            {drawing
              ? '抽題中...'
              : selectedDepthOption?.ctaLabel ?? '先選今晚想怎麼聊'}
          </button>
        </div>
      </div>
    );
  }

  // === 狀態 B: 作答介面 (已抽卡，未回答) ===
  // 🔥 這裡修復了 TypeScript 報錯
  if (status.state === 'IDLE' || status.state === 'PARTNER_STARTED') {
    const depthLevel = resolveDepthLevel(status.card.depth_level, status.card.difficulty_level);
    const depthStyle = getDepthPresentation(depthLevel);
    const homeDepth = getHomeDailyDepthPresentation(depthLevel);

    return (
      <div
        className={`bg-card rounded-card shadow-soft overflow-hidden max-w-lg mx-auto border relative transition-all duration-haven ease-haven hover:shadow-lift ${depthStyle.accentFrameClass}`}
      >
        <div className={`absolute inset-x-0 top-0 h-1.5 ${depthStyle.topAccentClass}`} aria-hidden />
        {status.state === 'PARTNER_STARTED' && (
          <div className="bg-primary text-primary-foreground text-xs font-bold px-4 py-3 text-center flex items-center justify-center gap-2 shadow-soft animate-in slide-in-from-top-4 duration-500">
            <div className="w-5 h-5 rounded-full bg-primary-foreground/20 flex items-center justify-center text-[10px] border border-primary-foreground/20">
              {getInitial(status.partner_name)}
            </div>
            <span>{status.partner_name || '伴侶'} 已經完成回答，等你解鎖！</span>
          </div>
        )}
        <div className="p-8">
          <div className="mb-8 text-center">
            <span className={`inline-block px-3 py-1 text-[10px] font-bold tracking-widest rounded-full mb-4 uppercase ${depthStyle.badgeClass}`}>
              {getDeckDisplayName(status.card.category)} · {homeDepth?.label ?? depthStyle.label}
            </span>
            <p className="text-xs text-muted-foreground mb-4 leading-relaxed">{depthStyle.guidance}</p>
            <h2 className="text-2xl font-art font-bold text-foreground mb-4 leading-tight">{status.card.title}</h2>
            <div className={`relative p-6 rounded-2xl border shadow-soft shadow-glass-inset text-left group transition-colors duration-haven-fast ease-haven ${depthStyle.questionSurfaceClass}`}>
              <Quote className="absolute top-4 right-4 text-muted-foreground/30 w-10 h-10 -z-10 group-hover:text-muted-foreground/50 transition-colors duration-haven-fast ease-haven" aria-hidden />
              <p className="text-lg text-foreground font-medium leading-relaxed">
                {status.card.question}
              </p>
            </div>
            {status.card.tags && status.card.tags.length > 0 && (
              <div className="mt-4 flex flex-wrap items-center justify-center gap-1.5">
                {status.card.tags.slice(0, 4).map((tag) => {
                  const cleanedTag = tag.replace(/^#+/, '');
                  return (
                    <span
                      key={tag}
                      className="text-[11px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border"
                    >
                      #{cleanedTag}
                    </span>
                  );
                })}
              </div>
            )}
          </div>
          <div className="relative group rounded-2xl transition-all duration-haven ease-haven focus-within:shadow-focus-glow">
            <textarea
              aria-label="在此寫下你的想法（選填）"
              value={answer}
              onChange={(e) => handleAnswerChange(e.target.value)}
              placeholder="在這裡寫下你的想法..."
              maxLength={2000}
              className="w-full h-40 p-5 bg-muted/50 rounded-2xl border border-border/50 focus-visible:bg-card focus-visible:border-primary/30 outline-none transition-all duration-haven ease-haven resize-none text-foreground placeholder:text-muted-foreground/50 placeholder:font-light leading-relaxed"
            />
            <div className="absolute bottom-4 right-4 text-[10px] text-muted-foreground/50 font-mono tabular-nums bg-card/60 px-2 py-0.5 rounded">
              {answer.length}/2000
            </div>
          </div>
          {partnerTyping && (
            <div className="mt-3 inline-flex items-center gap-2 text-xs text-muted-foreground animate-in fade-in duration-300">
              <span className="inline-flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-primary/50 animate-bounce [animation-delay:0ms]" aria-hidden />
                <span className="h-1.5 w-1.5 rounded-full bg-primary/50 animate-bounce [animation-delay:150ms]" aria-hidden />
                <span className="h-1.5 w-1.5 rounded-full bg-primary/50 animate-bounce [animation-delay:300ms]" aria-hidden />
              </span>
              <span className="font-light">{status.partner_name || '伴侶'} 正在輸入...</span>
            </div>
          )}
          <button
            onClick={handleSubmit}
            disabled={!answer.trim() || submitting}
            className={`mt-6 w-full py-4 rounded-xl font-bold transition-all duration-haven ease-haven flex items-center justify-center gap-2 active:scale-[0.98]
            ${answer.trim()
              ? 'bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5'
              : 'bg-muted cursor-not-allowed text-muted-foreground shadow-none'}`}
          >
            {submitting ? <Loader2 className="animate-spin"/> : <Send size={18} />}
            {submitting ? '傳送中...' : '送出並解鎖'}
          </button>
        </div>
      </div>
    );
  }

  if (status.state === 'WAITING_PARTNER') {
    return (
      <div className="bg-card/95 backdrop-blur-xl rounded-card shadow-soft border border-foreground/10 p-10 max-w-md mx-auto text-center relative overflow-hidden animate-in fade-in duration-500">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-72 h-72 bg-primary/8 rounded-full blur-hero-orb -z-10 animate-breathe" aria-hidden />
        <div className="mb-8 relative inline-block">
          <div className="absolute inset-0 bg-primary/15 blur-xl animate-breathe rounded-full" aria-hidden />
          <div className="w-20 h-20 bg-card rounded-full flex items-center justify-center relative shadow-soft border border-border/50">
            <Lock className="text-primary w-7 h-7" aria-hidden />
          </div>
        </div>
        <h3 className="text-xl font-art font-bold text-foreground mb-2">回答已封存</h3>
        <p className="text-muted-foreground mb-8 text-sm leading-relaxed font-light">
          等待 <span className="font-semibold text-primary">{status.partner_name || '伴侶'}</span> 回答後，<br/>
          盲盒將會自動解鎖。
        </p>
        <div className="bg-muted/30 p-5 rounded-2xl border border-dashed border-border/50 text-left relative overflow-hidden group shadow-glass-inset">
           <div className="flex items-center gap-2 mb-2">
              <div className="w-6 h-6 rounded-full bg-primary/15 flex items-center justify-center text-[10px] text-primary font-bold">我</div>
              <span className="text-[10px] text-muted-foreground/60 uppercase tracking-wider font-medium">時間膠囊</span>
           </div>
           <p className="text-foreground font-medium blur-[6px] select-none opacity-40 transition-all duration-haven ease-haven">
             {status.my_content || "這是一段你看不到的文字..."}
           </p>
           <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-[11px] bg-card/90 backdrop-blur-sm px-4 py-1.5 rounded-full text-primary font-medium shadow-soft border border-border/50 flex items-center gap-1.5">
                <Lock size={10} aria-hidden /> 密封中
              </span>
           </div>
        </div>
      </div>
    );
  }

  if (status.state === 'COMPLETED') {
    return (
      <div className="bg-card rounded-card shadow-lift max-w-lg mx-auto overflow-hidden border border-border/50 animate-in fade-in duration-700">
        <div className="bg-accent/8 p-6 md:p-8 border-b border-border/50 text-center relative animate-slide-up-fade">
          <div className="absolute top-5 right-5">
             <CheckCircle2 className="text-accent w-5 h-5" aria-hidden />
          </div>
          <span className="text-[10px] font-art font-bold tracking-[0.2em] text-accent uppercase mb-2 block">今日完成</span>
          <h3 className="text-lg font-art font-bold text-foreground line-clamp-1">{status.card?.title}</h3>
          <p className="text-sm text-muted-foreground mt-1.5 font-art italic px-4 leading-relaxed">&quot;{status.card?.question}&quot;</p>
        </div>
        <div className="p-6 md:p-8 bg-muted/20 min-h-[350px] flex flex-col space-y-6">
          <div className="flex items-end gap-3 animate-in slide-in-from-left-4 duration-500 delay-100">
             <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center text-primary-foreground text-xs font-bold shrink-0 shadow-soft border-2 border-card">
                {getInitial(status.partner_name)}
             </div>
             <div className="flex flex-col max-w-[80%]">
                <span className="text-[10px] text-muted-foreground/60 mb-1 ml-1 font-medium">{status.partner_name}</span>
                <div className="bg-card text-foreground p-4 rounded-2xl rounded-bl-md shadow-soft border border-border/50 text-sm leading-relaxed transition-shadow duration-haven ease-haven hover:shadow-lift">
                   {status.partner_content}
                </div>
             </div>
          </div>
          <div className="flex flex-row-reverse items-end gap-3 animate-in slide-in-from-right-4 duration-500 delay-300">
             <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center text-primary-foreground text-xs font-bold shrink-0 shadow-soft border-2 border-card">
                ME
             </div>
             <div className="flex flex-col items-end max-w-[80%]">
                <span className="text-[10px] text-muted-foreground/60 mb-1 mr-1 font-medium">You</span>
                <div className="bg-gradient-to-br from-primary to-primary/90 text-primary-foreground p-4 rounded-2xl rounded-br-md shadow-soft text-sm leading-relaxed transition-shadow duration-haven ease-haven hover:shadow-lift">
                   {status.my_content}
                </div>
             </div>
          </div>
        </div>
        <div className="p-4 bg-card border-t border-border/50">
          <button type="button" className="w-full py-3 rounded-xl text-muted-foreground hover:text-primary hover:bg-primary/5 transition-all duration-haven ease-haven text-sm flex items-center justify-center gap-2 group active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background">
             <Heart size={16} className="group-hover:fill-primary/20 transition-all duration-haven ease-haven" aria-hidden />
             <span className="font-medium">喜歡這次的深度對話嗎？</span>
          </button>
        </div>
      </div>
    );
  }

  return null;
};

export default DailyCard;
