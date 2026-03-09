'use client';

import { isAxiosError } from 'axios';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useToast } from '@/contexts/ToastContext';
import useSocket from '@/hooks/useSocket';
import { useAuth } from '@/hooks/use-auth';
import { normalizeDeckCategory } from '@/lib/deck-category';
import { markNotificationsRead } from '@/services/api-client';
import {
  CardSession,
  DeckHistoryEntry,
  drawDeckCard,
  fetchCardConversation,
  respondToDeckCard,
} from '@/services/deckService';

import type { DeckRoomViewModel, RoomStatus } from './types';

type SocketEvent = {
  event?: string;
  session_id?: string;
  message?: string;
  is_typing?: boolean;
  from_user_id?: string;
};

const DECK_LIBRARY_FILTER_MODES = ['all', 'in_progress', 'not_started', 'completed'] as const;
const DECK_LIBRARY_SORT_MODES = ['recommended', 'progress_desc', 'progress_asc', 'title'] as const;

const isDeckLibraryFilterMode = (value: string): boolean =>
  (DECK_LIBRARY_FILTER_MODES as readonly string[]).includes(value);

const isDeckLibrarySortMode = (value: string): boolean =>
  (DECK_LIBRARY_SORT_MODES as readonly string[]).includes(value);

const DEFAULT_PARTNER_NAME = '親愛的';

export function useDeckRoom(): DeckRoomViewModel {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const { showToast } = useToast();

  const rawCategory = params?.category;
  const category = Array.isArray(rawCategory) ? rawCategory[0] : rawCategory ?? '';
  const normalizedCategory = useMemo(() => normalizeDeckCategory(category), [category]);
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
  const decksReturnUrl = useMemo(() => {
    const nextParams = new URLSearchParams();
    if (libraryFilter && libraryFilter !== 'all') {
      nextParams.set('filter', libraryFilter);
    }
    if (librarySort && librarySort !== 'recommended') {
      nextParams.set('sort', librarySort);
    }

    const nextQuery = nextParams.toString();
    return nextQuery ? `/decks?${nextQuery}` : '/decks';
  }, [libraryFilter, librarySort]);

  const historyHref = useMemo(() => {
    const nextParams = new URLSearchParams();
    if (normalizedCategory) {
      nextParams.set('category', normalizedCategory);
    }
    if (libraryFilter && libraryFilter !== 'all') {
      nextParams.set('library_filter', libraryFilter);
    }
    if (librarySort && librarySort !== 'recommended') {
      nextParams.set('library_sort', librarySort);
    }

    const nextQuery = nextParams.toString();
    return nextQuery ? `/decks/history?${nextQuery}` : '/decks/history';
  }, [libraryFilter, librarySort, normalizedCategory]);

  const partnerDisplayName = useMemo(
    () => user?.partner_nickname || user?.partner_name || DEFAULT_PARTNER_NAME,
    [user?.partner_name, user?.partner_nickname],
  );

  const [session, setSession] = useState<CardSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [roomStatus, setRoomStatus] = useState<RoomStatus>('IDLE');
  const [resultData, setResultData] = useState<DeckHistoryEntry | null>(null);
  const [partnerTyping, setPartnerTyping] = useState(false);

  const sessionRef = useRef<CardSession | null>(null);
  const roomStatusRef = useRef<RoomStatus>('IDLE');
  const invalidCategoryHandledRef = useRef(false);
  const isMountedRef = useRef(true);
  const loadRequestIdRef = useRef(0);
  const resultRequestIdRef = useRef(0);
  const myTypingSentRef = useRef(false);
  const typingStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
        console.error('抓取對話紀錄失敗:', error);
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
        }
        const data = await drawDeckCard(normalizedCategory, forceNew);
        if (!isMountedRef.current || requestId !== loadRequestIdRef.current) {
          return;
        }
        updateSession(data);
        setPartnerTyping(false);
        invalidCategoryHandledRef.current = false;

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
        console.error('抽卡失敗:', error);

        if (isAxiosError(error) && error.response?.status === 404) {
          showToast(
            error.response.data?.detail || '這分類的卡片已經被你抽完囉！快去請伴侶回答吧！',
            'info',
          );
          router.push(decksReturnUrl);
          return;
        }

        showToast('網路連線似乎有點問題，請重新整理試試。', 'error');
      } finally {
        if (isMountedRef.current && requestId === loadRequestIdRef.current) {
          setLoading(false);
        }
      }
    },
    [category, decksReturnUrl, fetchResult, normalizedCategory, router, showToast, updateRoomStatus, updateSession],
  );

  useEffect(() => {
    void loadCard();
  }, [loadCard]);

  useEffect(() => {
    if (!user?.id) {
      return;
    }
    void markNotificationsRead('card').catch((error) => {
      console.warn('標記卡片通知已讀失敗', error);
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

    if (data.message) {
      console.info('伴侶動態:', data.message);
    }
  }, []);

  const socketRef = useSocket(user?.id, handleSocketMessage, handlePartnerAction);

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

    try {
      setSubmitting(true);
      clearTypingStopTimer();
      sendTypingSignal(false);
      setPartnerTyping(false);
      const result = await respondToDeckCard(currentSession.id, answer.trim());
      if (String(sessionRef.current?.id) !== String(currentSession.id)) {
        return;
      }

      if (result.session_status === 'COMPLETED') {
        updateRoomStatus('COMPLETED');
        await fetchResult(currentSession);
      } else {
        updateRoomStatus('WAITING_PARTNER');
      }
      setAnswer('');
    } catch (error: unknown) {
      console.error('回答失敗:', error);
      if (isAxiosError(error)) {
        showToast(error.response?.data?.detail || '提交失敗，請檢查網路連線', 'error');
      } else {
        showToast('提交失敗，請檢查網路連線', 'error');
      }
    } finally {
      setSubmitting(false);
    }
  }, [answer, clearTypingStopTimer, fetchResult, sendTypingSignal, showToast, updateRoomStatus]);

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
    handleAnswerChange,
    handleSubmit,
    handleNextCard,
    handleBackToDecks,
  };
}
