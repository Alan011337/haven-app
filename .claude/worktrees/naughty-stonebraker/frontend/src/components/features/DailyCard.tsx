// frontend/src/components/features/DailyCard.tsx

'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { isAxiosError } from 'axios';
import { Loader2, Send, Lock, CheckCircle2, Sparkles, Heart, Quote } from 'lucide-react';
import { getDeckDisplayName } from '@/lib/deck-meta';
import { getDepthPresentation, resolveDepthLevel } from '@/lib/depth-level';
import { cardService, DailyStatus } from '@/services/cardService';
import { useToast } from '@/contexts/ToastContext';
import { useAuth } from '@/hooks/use-auth';
import useSocket from '@/hooks/useSocket';

// 小工具：取得名字首字
const getInitial = (name?: string) => name ? name.charAt(0).toUpperCase() : "P";

// 小工具：根據名字產生固定的背景色
const getAvatarColor = (name: string) => {
  const colors = ['bg-red-500', 'bg-orange-500', 'bg-amber-500', 'bg-green-500', 'bg-emerald-500', 'bg-teal-500', 'bg-cyan-500', 'bg-sky-500', 'bg-blue-500', 'bg-indigo-500', 'bg-violet-500', 'bg-purple-500', 'bg-fuchsia-500', 'bg-pink-500', 'bg-rose-500'];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
};

type SocketEvent = {
  event?: string;
  session_id?: string;
  is_typing?: boolean;
};

const DailyCard = () => {
  const { user } = useAuth();
  const [status, setStatus] = useState<DailyStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [partnerTyping, setPartnerTyping] = useState(false);
  const { showToast } = useToast();
  const statusRef = useRef<DailyStatus | null>(null);
  const typingStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const delayedRefreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const myTypingSentRef = useRef(false);
  const isMountedRef = useRef(true);

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

  // 使用 useCallback 避免依賴循環
  const fetchStatus = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        if (isMountedRef.current) {
          setLoading(false);
        }
        return;
      }
      
      const data = await cardService.getDailyStatus();
      if (!isMountedRef.current) {
        return;
      }
      setStatus(data);
      statusRef.current = data;
    } catch (err) {
      if (isMountedRef.current) {
        console.error("無法取得卡片狀態", err);
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    statusRef.current = status;
  }, [status]);

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
      void fetchStatus();
    },
    [fetchStatus],
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
      void fetchStatus();
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
  }, [fetchStatus]);

  const socketRef = useSocket(user?.id, handleSocketMessage, handlePartnerAction);

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

  // 初始化只跑一次
  useEffect(() => {
    isMountedRef.current = true;
    fetchStatus();
    return () => {
      isMountedRef.current = false;
    };
  }, [fetchStatus]);

  // 智慧輪詢邏輯
  useEffect(() => {
    const isAnswering = status?.card && (status.state === 'IDLE' || status.state === 'PARTNER_STARTED');
    
    // 如果正在作答，不輪詢，避免畫面閃爍
    if (isAnswering) return; 

    // 需要輪詢的情況：等待伴侶回應 OR 還沒開始 (偵測伴侶是否開始)
    const shouldPoll = 
        status?.state === 'WAITING_PARTNER' || 
        (!status?.card); 

    let interval: ReturnType<typeof setInterval> | null = null;

    if (shouldPoll) {
        interval = setInterval(() => {
            void fetchStatus();
        }, 5000); // 5秒檢查一次
    }

    return () => {
        if (interval) clearInterval(interval);
    };
  }, [fetchStatus, status?.state, status?.card]);

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
    if (loading) {
      return;
    }
    setLoading(true);
    try {
      await cardService.drawDailyCard();
      setPartnerTyping(false);
      await fetchStatus();

    } catch (error) {
      console.error("抽卡失敗", error);
      if (isAxiosError(error)) {
        showToast(error.response?.data?.detail || "抽卡失敗，請稍後再試", 'error');
      } else {
        showToast("抽卡失敗，請稍後再試", 'error');
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  };

  const handleSubmit = async () => {
    if (!status?.card || !answer.trim() || submitting) return;
    setSubmitting(true);
    clearTypingStopTimer();
    clearDelayedRefreshTimer();
    sendTypingSignal(false);
    setPartnerTyping(false);
    try {
      // 1. 送出請求
      const res = await cardService.respondDailyCard(status.card.id, answer.trim());

      // 2. 為了防止 Race Condition
      const nextState = res.status === 'REVEALED' ? 'COMPLETED' : 'WAITING_PARTNER';

      setStatus((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          state: nextState, 
          my_content: answer.trim(),
          partner_content: prev.partner_content,
          session_id: res.session_id ?? prev.session_id ?? null,
        };
      });

      setAnswer(''); 

      if (nextState === 'COMPLETED') {
        void fetchStatus();
      } else {
        // 3. 延遲 1.5 秒再背景更新，確保資料庫已經寫入完成
        delayedRefreshTimerRef.current = setTimeout(() => {
          void fetchStatus();
          delayedRefreshTimerRef.current = null;
        }, 1500);
      }

    } catch (error) {
      console.error("送出失敗", error);
      if (isAxiosError(error)) {
        showToast(error.response?.data?.detail || "送出失敗，請檢查網路連線", 'error');
      } else {
        showToast("送出失敗，請檢查網路連線", 'error');
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
    <div className="w-full h-64 flex flex-col items-center justify-center space-y-4">
      <div className="relative">
        <div className="absolute inset-0 bg-purple-200 rounded-full blur animate-pulse"></div>
        <Loader2 className="animate-spin text-purple-600 w-8 h-8 relative z-10"/>
      </div>
      <p className="text-gray-400 text-sm font-medium animate-pulse tracking-wide">正在連結彼此的心靈...</p>
    </div>
  );

  // === 狀態 A: 抽卡介面 (還沒抽卡) ===
  if (!status?.card) {
    return (
      <div className="relative group cursor-pointer transform hover:scale-[1.01] transition-all duration-500" onClick={handleDraw}>
        <div className="absolute -inset-1 bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500 rounded-[2rem] blur opacity-25 group-hover:opacity-60 transition duration-1000"></div>
        <div className="relative bg-white/90 backdrop-blur-xl rounded-[1.8rem] p-8 text-center border border-white/50 shadow-xl overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-pink-300 via-purple-300 to-indigo-300"></div>
          <div className="flex justify-between items-start mb-6">
             <div className="bg-purple-100/50 p-2 rounded-2xl">
                <Sparkles className="text-purple-500 w-5 h-5 animate-pulse" />
             </div>
             <span className="text-xs font-bold tracking-widest text-gray-400 uppercase">Daily Ritual</span>
          </div>
          <div className="mx-auto w-24 h-24 bg-gradient-to-br from-indigo-50 to-purple-50 rounded-full flex items-center justify-center mb-6 shadow-inner border border-white">
            <span className="text-5xl filter drop-shadow-sm transform group-hover:rotate-12 transition-transform duration-500">🃏</span>
          </div>
          <h3 className="text-2xl font-bold text-gray-800 mb-3">今日共感卡片</h3>
          <p className="text-gray-500 mb-8 font-light leading-relaxed">
            抽一張卡片，<br/>開啟與 <span className="font-semibold text-purple-600 bg-purple-50 px-2 py-0.5 rounded-md">{status?.partner_name || '伴侶'}</span> 的深度連結。
          </p>
          <button className="px-8 py-3.5 rounded-full bg-gray-900 text-white font-medium hover:bg-gray-800 transition-all shadow-lg hover:shadow-xl flex items-center gap-2 mx-auto group-hover:gap-3">
            <Sparkles size={16} /> 抽取今日話題
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

    return (
      <div
        className={`bg-white rounded-[2rem] shadow-xl overflow-hidden max-w-lg mx-auto border relative transition-all duration-500 ${depthStyle.accentFrameClass}`}
      >
        <div className={`absolute inset-x-0 top-0 h-1.5 ${depthStyle.topAccentClass}`} />
        {status.state === 'PARTNER_STARTED' && (
          <div className="bg-gradient-to-r from-rose-400 to-pink-500 text-white text-xs font-bold px-4 py-3 text-center flex items-center justify-center gap-2 shadow-sm animate-in slide-in-from-top-4 duration-500">
            <div className={`w-5 h-5 rounded-full ${getAvatarColor(status.partner_name || 'P')} flex items-center justify-center text-[10px] border border-white/40 shadow-inner`}>
              {getInitial(status.partner_name)}
            </div>
            <span>{status.partner_name || '伴侶'} 已經完成回答，等你解鎖！</span>
          </div>
        )}
        <div className="p-8">
          <div className="mb-8 text-center">
            <span className={`inline-block px-3 py-1 text-[10px] font-bold tracking-widest rounded-full mb-4 uppercase ${depthStyle.badgeClass}`}>
              {getDeckDisplayName(status.card.category)} · Depth {depthLevel} · {depthStyle.label}
            </span>
            <p className="text-xs text-slate-500 mb-4 leading-relaxed">{depthStyle.guidance}</p>
            <h2 className="text-2xl font-bold text-gray-800 mb-4 leading-tight">{status.card.title}</h2>
            <div className={`relative p-6 rounded-2xl border shadow-sm text-left group transition-colors ${depthStyle.questionSurfaceClass}`}>
              <Quote className="absolute top-4 right-4 text-indigo-100 w-10 h-10 -z-10 group-hover:text-indigo-200 transition-colors" />
              <p className="text-lg text-gray-700 font-medium leading-relaxed">
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
                      className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200"
                    >
                      #{cleanedTag}
                    </span>
                  );
                })}
              </div>
            )}
          </div>
          <div className="relative group">
            <textarea
              value={answer}
              onChange={(e) => handleAnswerChange(e.target.value)}
              placeholder="在這裡寫下你的想法..."
              maxLength={2000}
              className="w-full h-40 p-5 bg-gray-50 rounded-2xl border-2 border-transparent focus:bg-white focus:border-indigo-200 focus:ring-4 focus:ring-indigo-50 outline-none transition-all resize-none text-gray-700 placeholder:text-gray-400 leading-relaxed shadow-inner"
            />
            <div className="absolute bottom-4 right-4 text-xs text-gray-400 font-mono bg-white/50 px-2 rounded-md">
              {answer.length}/2000
            </div>
          </div>
          {partnerTyping && (
            <div className="mt-3 inline-flex items-center gap-2 text-xs text-slate-500">
              <span className="inline-flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:0ms]" />
                <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:150ms]" />
                <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:300ms]" />
              </span>
              <span>{status.partner_name || '伴侶'} 正在輸入...</span>
            </div>
          )}
          <button
            onClick={handleSubmit}
            disabled={!answer.trim() || submitting}
            className={`mt-6 w-full py-4 rounded-xl font-bold text-white shadow-lg transition-all flex items-center justify-center gap-2 transform active:scale-[0.99]
            ${answer.trim()
              ? 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:shadow-indigo-500/30 hover:-translate-y-0.5'
              : 'bg-gray-200 cursor-not-allowed text-gray-400 shadow-none'}`}
          >
            {submitting ? <Loader2 className="animate-spin"/> : <Send size={18} />}
            {submitting ? '傳送中...' : '送出並解鎖'}
          </button>
        </div>
      </div>
    );
  }

  // === 狀態 C: 等待伴侶 (我已回答，伴侶未回答) ===
  if (status.state === 'WAITING_PARTNER') {
    return (
      <div className="bg-white/80 backdrop-blur-md rounded-[2rem] shadow-xl border border-white/60 p-10 max-w-md mx-auto text-center relative overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-indigo-100 rounded-full blur-3xl -z-10 opacity-60"></div>
        <div className="mb-6 relative inline-block">
          <div className="absolute inset-0 bg-indigo-400 blur-xl opacity-20 animate-pulse rounded-full"></div>
          <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center relative shadow-sm border border-indigo-50">
            <Lock className="text-indigo-400 w-8 h-8" />
          </div>
        </div>
        <h3 className="text-xl font-bold text-gray-800 mb-2">回答已封存</h3>
        <p className="text-gray-500 mb-8 text-sm leading-relaxed">
          等待 <span className="font-semibold text-indigo-600">{status.partner_name || '伴侶'}</span> 回答後，<br/>
          盲盒將會自動解鎖。
        </p>
        <div className="bg-white/60 p-5 rounded-2xl border border-dashed border-indigo-100 text-left relative overflow-hidden group">
           <div className="flex items-center gap-2 mb-2">
              <div className="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center text-[10px] text-indigo-600 font-bold">ME</div>
              <span className="text-xs text-gray-400">Time Capsule</span>
           </div>
           <p className="text-gray-800 font-medium blur-[6px] select-none opacity-50 transition-all duration-700 group-hover:blur-[5px]">
             {status.my_content || "這是一段你看不到的文字..."}
           </p>
           <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xs bg-white/80 px-3 py-1 rounded-full text-indigo-400 font-medium shadow-sm border border-indigo-50 flex items-center gap-1">
                Secret <Lock size={10} />
              </span>
           </div>
        </div>
      </div>
    );
  }

  // === 狀態 D: 完成 (聊天室模式 - 雙方都回答) ===
  if (status.state === 'COMPLETED') {
    return (
      <div className="bg-white rounded-[2rem] shadow-2xl max-w-lg mx-auto overflow-hidden border border-gray-100 animate-in fade-in duration-700">
        <div className="bg-gradient-to-r from-emerald-50 to-teal-50 p-6 border-b border-emerald-100 text-center relative">
          <div className="absolute top-4 right-4 animate-bounce-slow">
             <CheckCircle2 className="text-emerald-400 w-6 h-6" />
          </div>
          <span className="text-[10px] font-bold tracking-widest text-emerald-600 uppercase mb-1 block">Daily Completed</span>
          <h3 className="text-lg font-bold text-gray-800 line-clamp-1">{status.card?.title}</h3>
          <p className="text-sm text-gray-500 mt-1 font-serif italic px-4">&quot;{status.card?.question}&quot;</p>
        </div>
        <div className="p-6 bg-slate-50 min-h-[350px] flex flex-col space-y-6">
          <div className="flex items-end gap-3 animate-in slide-in-from-left-4 duration-500 delay-100">
             <div className={`w-9 h-9 rounded-full ${getAvatarColor(status.partner_name || 'Partner')} flex items-center justify-center text-white text-xs font-bold shrink-0 shadow-sm border-2 border-white`}>
                {getInitial(status.partner_name)}
             </div>
             <div className="flex flex-col max-w-[80%]">
                <span className="text-[10px] text-gray-400 mb-1 ml-1">{status.partner_name}</span>
                <div className="bg-white text-gray-800 p-4 rounded-2xl rounded-bl-none shadow-sm border border-gray-100 text-sm leading-relaxed relative hover:shadow-md transition-shadow">
                   {status.partner_content}
                   <div className="absolute bottom-0 -left-2 w-4 h-4 bg-white border-l border-b border-gray-100 transform rotate-45 z-0 clip-path-polygon"></div> 
                </div>
             </div>
          </div>
          <div className="flex flex-row-reverse items-end gap-3 animate-in slide-in-from-right-4 duration-500 delay-300">
             <div className="w-9 h-9 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold shrink-0 shadow-sm border-2 border-white">
                ME
             </div>
             <div className="flex flex-col items-end max-w-[80%]">
                <span className="text-[10px] text-gray-400 mb-1 mr-1">You</span>
                <div className="bg-indigo-600 text-white p-4 rounded-2xl rounded-br-none shadow-md text-sm leading-relaxed hover:shadow-lg transition-shadow">
                   {status.my_content}
                </div>
             </div>
          </div>
        </div>
        <div className="p-4 bg-white border-t border-gray-100">
          <button className="w-full py-3 rounded-xl text-gray-400 hover:text-pink-500 hover:bg-pink-50 transition-all text-sm flex items-center justify-center gap-2 group">
             <Heart size={16} className="group-hover:fill-current transition-colors" /> 
             <span className="font-medium">喜歡這次的深度對話嗎？</span>
          </button>
        </div>
      </div>
    );
  }

  return null;
};

export default DailyCard;
