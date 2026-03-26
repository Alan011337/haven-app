'use client';

import { isAxiosError } from 'axios';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useToast } from '@/hooks/useToast';
import useSocket from '@/hooks/useSocket';
import { useAuth } from '@/hooks/use-auth';
import { trackRitualRespond, trackRitualUnlock } from '@/lib/cuj-events';
import { feedback } from '@/lib/feedback';
import { useAppearanceStore } from '@/stores/useAppearanceStore';
import { logClientError } from '@/lib/safe-error-log';
import { isNetworkError } from '@/lib/offline-queue/network';
import { enqueue, generateOperationId } from '@/lib/offline-queue/queue';
import { useDrawDeckCard, useRespondToDeckCard } from '@/hooks/queries';
import { createCheckoutSession, markNotificationsRead } from '@/services/api-client';
import {
  CardSession,
  DeckHistoryEntry,
  fetchCardConversation,
} from '@/services/deckService';
import {
  buildDecksReturnUrl,
  buildHistoryHref,
  isDeckLibraryFilterMode,
  isDeckLibrarySortMode,
  resolveDeckCategory,
  resolvePartnerDisplayName,
} from './room-url-utils';

import type { DeckRoomViewModel, RoomStatus } from './types';

type SocketEvent = {
  event?: string;
  session_id?: string;
  message?: string;
  is_typing?: boolean;
  from_user_id?: string;
};

const WAITING_PARTNER_REFRESH_INTERVAL_MS = 4000;

export function useDeckRoom(): DeckRoomViewModel {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const { showToast } = useToast();
  const hapticsEnabled = useAppearanceStore((s) => s.hapticsEnabled);
  const hapticStrength = useAppearanceStore((s) => s.hapticStrength);
  const soundEnabled = useAppearanceStore((s) => s.soundEnabled);
  const drawDeckCardMutation = useDrawDeckCard();
  const respondToDeckCardMutation = useRespondToDeckCard();

  const rawCategory = params?.category;
  const category = Array.isArray(rawCategory) ? rawCategory[0] : rawCategory ?? '';
  const normalizedCategory = useMemo(() => resolveDeckCategory(category), [category]);
  const libraryFilterQuery = searchParams.get('filter');
  const librarySortQuery = searchParams.get('sort');
  const libraryFilter = useMemo(
    () =>
      libraryFilterQuery && isDeckLibraryFilterMode(libraryFilterQuery)
        ? libraryFilterQuery
        : null,
    [libraryFilterQuery],
  );
  const librarySort = useMemo(
    () =>
      librarySortQuery && isDeckLibrarySortMode(librarySortQuery) ? librarySortQuery : null,
    [librarySortQuery],
  );
  const decksReturnUrl = useMemo(
    () => buildDecksReturnUrl(libraryFilter, librarySort),
    [libraryFilter, librarySort],
  );
  const autoLoadKey = useMemo(
    () => (user?.id && normalizedCategory ? `${user.id}:${normalizedCategory}` : null),
    [normalizedCategory, user?.id],
  );

  const historyHref = useMemo(
    () => buildHistoryHref(normalizedCategory, libraryFilter, librarySort),
    [libraryFilter, librarySort, normalizedCategory],
  );

  const partnerDisplayName = useMemo(
    () => resolvePartnerDisplayName(user?.partner_nickname, user?.partner_name),
    [user?.partner_name, user?.partner_nickname],
  );

  const [session, setSession] = useState<CardSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [roomStatus, setRoomStatus] = useState<RoomStatus>('IDLE');
  const [resultData, setResultData] = useState<DeckHistoryEntry | null>(null);
  const [partnerTyping, setPartnerTyping] = useState(false);
  const [quotaExceeded, setQuotaExceeded] = useState(false);
  const [upgradeLoading, setUpgradeLoading] = useState(false);
  const [selectedDepth, setSelectedDepth] = useState<1 | 2 | 3 | null>(null);

  const sessionRef = useRef<CardSession | null>(null);
  const roomStatusRef = useRef<RoomStatus>('IDLE');
  const invalidCategoryHandledRef = useRef(false);
  const isMountedRef = useRef(true);
  const loadRequestIdRef = useRef(0);
  const resultRequestIdRef = useRef(0);
  const myTypingSentRef = useRef(false);
  const typingStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const autoLoadKeyRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (typingStopTimerRef.current) {
        clearTimeout(typingStopTimerRef.current);
        typingStopTimerRef.current = null;
      }
    };
  }, []);

  const updateSession = useCallback((nextSession: CardSession | null) => {
    sessionRef.current = nextSession;
    setSession(nextSession);
  }, []);

  const updateRoomStatus = useCallback((nextStatus: RoomStatus) => {
    roomStatusRef.current = nextStatus;
    setRoomStatus(nextStatus);
  }, []);

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  useEffect(() => {
    roomStatusRef.current = roomStatus;
  }, [roomStatus]);

  const fetchResult = useCallback(
    async (targetSession?: CardSession) => {
      const activeSession = targetSession ?? sessionRef.current;
      if (!activeSession || !user?.id) {
        return;
      }
      const requestId = ++resultRequestIdRef.current;

      try {
        const conversations = await fetchCardConversation(activeSession.card.id, activeSession.id);
        if (!isMountedRef.current || requestId !== resultRequestIdRef.current) {
          return;
        }
        if (String(sessionRef.current?.id) !== String(activeSession.id)) {
          return;
        }
        if (!conversations.length) {
          return;
        }

        const currentUserId = String(user.id);
        let myResp: (typeof conversations)[number] | undefined;
        let partnerResp: (typeof conversations)[number] | undefined;
        for (let index = conversations.length - 1; index >= 0; index -= 1) {
          const item = conversations[index];
          if (!myResp && String(item.user_id) === currentUserId) {
            myResp = item;
          } else if (!partnerResp && String(item.user_id) !== currentUserId) {
            partnerResp = item;
          }
          if (myResp && partnerResp) {
            break;
          }
        }

        if (!myResp) {
          return;
        }

        const shouldReveal =
          Boolean(partnerResp) ||
          activeSession.status === 'COMPLETED' ||
          roomStatusRef.current === 'COMPLETED';

        if (!shouldReveal) {
          return;
        }

        if (!isMountedRef.current || String(sessionRef.current?.id) !== String(activeSession.id)) {
          return;
        }

        setResultData({
          session_id: activeSession.id,
          card_title: activeSession.card.title || '',
          card_question: activeSession.card.question,
          category: activeSession.card.category,
          my_answer: myResp.content,
          partner_answer: partnerResp?.content ?? '等待中...',
          revealed_at: new Date().toISOString(),
        });

        if (roomStatusRef.current !== 'COMPLETED') {
          updateRoomStatus('COMPLETED');
        }
      } catch (error) {
        logClientError('deck-room-fetch-conversation-failed', error);
      }
    },
    [updateRoomStatus, user?.id],
  );

  const loadCard = useCallback(
    async (forceNew = false) => {
      const requestId = ++loadRequestIdRef.current;
      if (!category) {
        if (isMountedRef.current && requestId === loadRequestIdRef.current) {
          setLoading(false);
          updateSession(null);
          setPartnerTyping(false);
        }
        return;
      }
      if (!normalizedCategory) {
        if (isMountedRef.current && requestId === loadRequestIdRef.current) {
          setLoading(false);
          updateSession(null);
          setPartnerTyping(false);
        }
        if (!invalidCategoryHandledRef.current) {
          invalidCategoryHandledRef.current = true;
          showToast('無效的牌組分類，已返回牌組大廳。', 'info');
          router.replace(decksReturnUrl);
        }
        return;
      }

      try {
        if (isMountedRef.current && requestId === loadRequestIdRef.current) {
          setLoading(true);
          setQuotaExceeded(false);
        }
        const data = await drawDeckCardMutation.mutateAsync({
          category: normalizedCategory,
          forceNew,
          preferredDepth: selectedDepth ?? undefined,
        });
        if (!isMountedRef.current || requestId !== loadRequestIdRef.current) {
          return;
        }
        updateSession(data);
        setPartnerTyping(false);
        invalidCategoryHandledRef.current = false;
        if (forceNew) feedback.onDrawSuccess({ hapticsEnabled, hapticStrength, soundEnabled });

        if (data.status === 'COMPLETED') {
          updateRoomStatus('COMPLETED');
          await fetchResult(data);
          return;
        }

        if (data.status === 'WAITING_PARTNER') {
          updateRoomStatus('WAITING_PARTNER');
          setResultData(null);
          return;
        }

        updateRoomStatus('IDLE');
        setResultData(null);
      } catch (error: unknown) {
        logClientError('deck-room-draw-card-failed', error);

        if (isAxiosError(error) && error.response?.status === 404) {
          showToast(
            error.response.data?.detail || '這分類的卡片已經被你抽完囉！快去請伴侶回答吧！',
            'info',
          );
          router.push(decksReturnUrl);
          return;
        }

        if (isAxiosError(error) && error.response?.status === 403) {
          setQuotaExceeded(true);
          const d = error.response.data?.detail;
          const message =
            typeof d === 'object' && d !== null && 'message' in d
              ? String((d as { message?: string }).message)
              : typeof d === 'string'
                ? d
                : '今日抽卡次數已達上限，升級方案可繼續使用。';
          showToast(message, 'info');
          return;
        }

        showToast('網路連線似乎有點問題，請重新整理試試。', 'error');
      } finally {
        if (isMountedRef.current && requestId === loadRequestIdRef.current) {
          setLoading(false);
        }
      }
    },
    [
      category,
      decksReturnUrl,
      drawDeckCardMutation,
      fetchResult,
      hapticsEnabled,
      hapticStrength,
      normalizedCategory,
      selectedDepth,
      soundEnabled,
      router,
      showToast,
      updateRoomStatus,
      updateSession,
    ],
  );

  // Only auto-draw when user is authenticated (token in localStorage); avoid 401 storm from draw before auth ready
  useEffect(() => {
    if (!user?.id || !autoLoadKey) return;
    if (autoLoadKeyRef.current === autoLoadKey) return;
    autoLoadKeyRef.current = autoLoadKey;
    void loadCard();
  }, [autoLoadKey, loadCard, user?.id]);

  useEffect(() => {
    if (!user?.id) {
      return;
    }
    void markNotificationsRead('card').catch((error) => {
      logClientError('deck-room-mark-card-notifications-read-failed', error);
    });
  }, [user?.id]);

  const handleSocketMessage = useCallback(
    (payload: Record<string, unknown>) => {
      const data = payload as SocketEvent;
      const currentSession = sessionRef.current;
      if (data.event !== 'CARD_REVEALED') {
        return;
      }
      if (String(data.session_id) !== String(currentSession?.id)) {
        return;
      }

      setPartnerTyping(false);
      updateRoomStatus('COMPLETED');
      void fetchResult(currentSession ?? undefined);
    },
    [fetchResult, updateRoomStatus],
  );

  const handlePartnerAction = useCallback((payload: Record<string, unknown>) => {
    const data = payload as SocketEvent;
    const currentSession = sessionRef.current;
    if (data.event === 'PARTNER_TYPING') {
      if (!currentSession || String(data.session_id) !== String(currentSession.id)) {
        return;
      }
      setPartnerTyping(Boolean(data.is_typing) && roomStatusRef.current === 'IDLE');
      return;
    }

    if (data.event && process.env.NODE_ENV === 'development') {
      console.info(`[deck-room-partner-event] event=${String(data.event)}`);
    }
  }, []);

  const socketRef = useSocket(user?.id, handleSocketMessage, handlePartnerAction);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (roomStatus !== 'WAITING_PARTNER' || !session?.id) {
      return;
    }

    const syncRevealState = () => {
      const activeSession = sessionRef.current ?? session;
      if (!activeSession || roomStatusRef.current !== 'WAITING_PARTNER') {
        return;
      }
      void fetchResult(activeSession);
    };

    syncRevealState();

    const intervalId = window.setInterval(syncRevealState, WAITING_PARTNER_REFRESH_INTERVAL_MS);
    const handleWindowFocus = () => {
      syncRevealState();
    };
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        syncRevealState();
      }
    };

    window.addEventListener('focus', handleWindowFocus);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener('focus', handleWindowFocus);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [fetchResult, roomStatus, session]);

  const clearTypingStopTimer = useCallback(() => {
    if (typingStopTimerRef.current) {
      clearTimeout(typingStopTimerRef.current);
      typingStopTimerRef.current = null;
    }
  }, []);

  const sendTypingSignal = useCallback(
    (isTyping: boolean) => {
      const activeSession = sessionRef.current;
      if (!activeSession) {
        return;
      }
      if (isTyping && roomStatusRef.current !== 'IDLE') {
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
          session_id: activeSession.id,
          is_typing: isTyping,
        }),
      );
      myTypingSentRef.current = isTyping;
    },
    [socketRef],
  );

  useEffect(() => {
    if (roomStatus === 'IDLE') {
      return;
    }
    clearTypingStopTimer();
    sendTypingSignal(false);
    setPartnerTyping(false);
  }, [clearTypingStopTimer, roomStatus, sendTypingSignal]);

  useEffect(() => {
    return () => {
      clearTypingStopTimer();
      sendTypingSignal(false);
    };
  }, [clearTypingStopTimer, sendTypingSignal]);

  const handleSubmit = useCallback(async () => {
    const currentSession = sessionRef.current;
    if (!currentSession || !answer.trim()) {
      return;
    }

    const operationId = generateOperationId();
    try {
      setSubmitting(true);
      clearTypingStopTimer();
      sendTypingSignal(false);
      setPartnerTyping(false);
      trackRitualRespond(String(currentSession.id));
      const result = await respondToDeckCardMutation.mutateAsync({
        sessionId: currentSession.id,
        content: answer.trim(),
        idempotencyKey: operationId,
      });
      if (String(sessionRef.current?.id) !== String(currentSession.id)) {
        return;
      }

      if (result.session_status === 'COMPLETED') {
        trackRitualUnlock(String(currentSession.id));
        feedback.onUnlockSuccess({ hapticsEnabled, hapticStrength, soundEnabled });
        updateRoomStatus('COMPLETED');
        await fetchResult(currentSession);
      } else {
        updateRoomStatus('WAITING_PARTNER');
      }
      setAnswer('');
    } catch (error: unknown) {
      logClientError('deck-room-submit-failed', error);
      if (isNetworkError(error)) {
        try {
          await enqueue(operationId, 'deck_respond', {
            session_id: String(currentSession.id),
            content: answer.trim(),
          });
          setAnswer('');
          showToast('已存到離線，連線後會自動同步', 'info');
        } catch {
          showToast('提交失敗，請檢查網路連線', 'error');
        }
        return;
      }
      if (isAxiosError(error)) {
        showToast(error.response?.data?.detail || '提交失敗，請檢查網路連線', 'error');
      } else {
        showToast('提交失敗，請檢查網路連線', 'error');
      }
    } finally {
      setSubmitting(false);
    }
  }, [answer, clearTypingStopTimer, fetchResult, hapticsEnabled, hapticStrength, respondToDeckCardMutation, sendTypingSignal, showToast, soundEnabled, updateRoomStatus]);

  const handleNextCard = useCallback(() => {
    clearTypingStopTimer();
    sendTypingSignal(false);
    setPartnerTyping(false);
    updateSession(null);
    setResultData(null);
    setAnswer('');
    updateRoomStatus('IDLE');
    void loadCard(true);
  }, [clearTypingStopTimer, loadCard, sendTypingSignal, updateRoomStatus, updateSession]);

  const handleBackToDecks = useCallback(() => {
    clearTypingStopTimer();
    sendTypingSignal(false);
    setPartnerTyping(false);
    router.push(decksReturnUrl);
  }, [clearTypingStopTimer, decksReturnUrl, router, sendTypingSignal]);

  const handleUpgrade = useCallback(async () => {
    if (upgradeLoading) return;
    setUpgradeLoading(true);
    try {
      const { url } = await createCheckoutSession();
      if (url) {
        window.location.href = url;
        return;
      }
    } catch (error) {
      logClientError('deck-room-create-checkout-failed', error);
      showToast('無法開啟付費頁面，請稍後再試。', 'error');
    } finally {
      setUpgradeLoading(false);
    }
  }, [upgradeLoading, showToast]);

  const handleDepthChange = useCallback((depth: 1 | 2 | 3 | null) => {
    setSelectedDepth(depth);
  }, []);

  const handleAnswerChange = useCallback((value: string) => {
    const nextValue = value.slice(0, 2000);
    setAnswer(nextValue);

    const hasContent = nextValue.trim().length > 0;
    if (!hasContent) {
      clearTypingStopTimer();
      sendTypingSignal(false);
      return;
    }

    if (!sessionRef.current || roomStatusRef.current !== 'IDLE') {
      return;
    }

    sendTypingSignal(true);
    clearTypingStopTimer();
    typingStopTimerRef.current = setTimeout(() => {
      sendTypingSignal(false);
    }, 1200);
  }, [clearTypingStopTimer, sendTypingSignal]);

  return {
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
    selectedDepth,
    handleDepthChange,
    quotaExceeded,
    handleAnswerChange,
    handleSubmit,
    handleNextCard,
    handleBackToDecks,
    handleUpgrade,
  };
}
