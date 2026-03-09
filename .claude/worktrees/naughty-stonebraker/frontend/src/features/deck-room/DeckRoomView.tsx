'use client';

import Link from 'next/link';
import { ArrowLeft, History, HeartHandshake, LockKeyhole, RefreshCw, Send, User } from 'lucide-react';

import { getDeckDisplayName, getDeckMeta } from '@/lib/deck-meta';
import { getDepthPresentation, resolveDepthLevel } from '@/lib/depth-level';
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
}: DeckRoomViewModel) {
  const deckMeta = getDeckMeta(category);
  const categoryDisplayName = getDeckDisplayName(category);
  const depthLevel = resolveDepthLevel(session?.card.depth_level);
  const depthStyles = getDepthPresentation(depthLevel);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center animate-pulse">
          <div className="w-16 h-16 bg-gray-200 rounded-full mb-4"></div>
          <p className="text-gray-400 font-medium">正在為你們準備話題...</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return <div className="text-center p-10 mt-10 text-gray-400">無法載入卡片，請稍後再試</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col pb-10">
      <header className="bg-white px-4 py-4 shadow-sm sticky top-0 z-10">
        <div className="flex items-center justify-between relative max-w-md mx-auto w-full">
          <button
            onClick={handleBackToDecks}
            className="p-2 -ml-2 text-gray-600 hover:bg-gray-100 rounded-full transition-colors z-20"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>

          <h1 className="absolute left-0 right-0 text-center font-bold text-gray-800 text-lg tracking-wide pointer-events-none">
            <span className="inline-flex items-center gap-2">
              {deckMeta && <deckMeta.Icon className={`w-4 h-4 ${deckMeta.iconColor}`} strokeWidth={2.2} />}
              {categoryDisplayName}
            </span>
          </h1>

          <Link
            href={historyHref}
            className="p-2 -mr-2 text-gray-600 hover:bg-gray-100 rounded-full transition-colors z-20"
          >
            <History className="w-6 h-6" />
          </Link>
        </div>
      </header>

      <main className="flex-1 p-6 flex flex-col items-center max-w-md mx-auto w-full">
        <div
          className={`w-full bg-white rounded-3xl shadow-xl p-8 flex flex-col items-center text-center border relative overflow-hidden mb-8 min-h-[260px] justify-center transition-all hover:shadow-2xl group ${depthStyles.accentFrameClass}`}
        >
          <div
            className={`absolute top-0 left-0 w-full h-2 ${depthStyles.topAccentClass} group-hover:h-3 transition-all duration-500`}
          ></div>
          <div className="mb-5 flex flex-wrap items-center justify-center gap-2">
            <span className="text-xs font-bold tracking-[0.2em] text-gray-400 uppercase">Topic</span>
            <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${depthStyles.badgeClass}`}>
              Depth {depthLevel} · {depthStyles.label}
            </span>
          </div>
          <p className="mb-4 text-xs text-slate-500 leading-relaxed max-w-[28rem]">
            {depthStyles.guidance}
          </p>
          <h2 className="text-2xl font-bold text-gray-800 leading-relaxed mb-4">{session.card.question}</h2>
          {session.card.title && (
            <p className="text-gray-500 text-sm font-medium opacity-80 mt-2">—— {session.card.title} ——</p>
          )}
          {session.card.tags && session.card.tags.length > 0 && (
            <div className="mt-4 flex flex-wrap items-center justify-center gap-1.5">
              {session.card.tags.slice(0, 4).map((tag) => (
                <span
                  key={tag}
                  className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200"
                >
                  #{tag}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="w-full transition-all duration-500 ease-in-out">
          {roomStatus === 'IDLE' && (
            <div className="relative group animate-in fade-in slide-in-from-bottom-4 duration-500">
              <textarea
                value={answer}
                onChange={(event) => handleAnswerChange(event.target.value)}
                placeholder={`分享給 ${partnerDisplayName} 聽...`}
                maxLength={2000}
                className="w-full p-5 pr-14 rounded-2xl border border-gray-200 focus:ring-4 focus:ring-purple-100 focus:border-purple-400 outline-none resize-none h-36 text-gray-700 bg-white shadow-sm transition-all"
              />
              <button
                onClick={() => void handleSubmit()}
                disabled={submitting || !answer.trim()}
                className={`
                  absolute bottom-4 right-4 p-3 rounded-xl shadow-lg transition-all transform
                  ${answer.trim() ? 'bg-gray-900 text-white hover:scale-105 active:scale-95' : 'bg-gray-200 text-gray-400 cursor-not-allowed'}
                `}
              >
                {submitting ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </button>
              {partnerTyping && (
                <div className="mt-3 inline-flex items-center gap-2 text-xs text-slate-500">
                  <span className="inline-flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:0ms]" />
                    <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:150ms]" />
                    <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:300ms]" />
                  </span>
                  <span>{partnerDisplayName} 正在輸入...</span>
                </div>
              )}
            </div>
          )}

          {roomStatus === 'WAITING_PARTNER' && (
            <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="text-center p-8 bg-white/90 backdrop-blur-md rounded-3xl shadow-lg border border-purple-50">
                <div className="mb-6 inline-flex p-4 bg-purple-50 rounded-full ring-4 ring-purple-50/50 shadow-inner">
                  <LockKeyhole className="w-8 h-8 text-purple-400" />
                </div>

                <h3 className="font-bold text-gray-800 text-lg mb-2">答案已上鎖 🔒</h3>

                <p className="text-gray-500 leading-relaxed mb-8 text-sm">
                  你的回答已保存！
                  <br />
                  <span className="text-gray-400">
                    當 <strong className="text-purple-500 font-medium">{partnerDisplayName}</strong> 回答後，
                    <br />
                    雙方的答案將同時揭曉。
                  </span>
                </p>

                <div className="flex flex-col gap-3">
                  <button
                    onClick={handleNextCard}
                    className="w-full py-3.5 px-4 bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-bold rounded-xl shadow-lg shadow-indigo-200 hover:shadow-xl hover:scale-[1.01] active:scale-95 transition-all duration-300 flex items-center justify-center gap-2 group"
                  >
                    <RefreshCw className="w-4 h-4 group-hover:rotate-180 transition-transform duration-700" />
                    不等了，先抽下一張
                  </button>

                  <button
                    onClick={handleBackToDecks}
                    className="w-full py-3 px-4 bg-transparent text-gray-400 font-medium hover:text-gray-600 transition-colors text-sm"
                  >
                    暫時離開，晚點再看
                  </button>
                </div>
              </div>
            </div>
          )}

          {roomStatus === 'COMPLETED' &&
            resultData &&
            String(resultData.session_id) === String(session.id) && (
              <div key={resultData.session_id} className="space-y-6 animate-in fade-in zoom-in-95 duration-500">
                <div className="space-y-5 px-1">
                  <div className="flex gap-3 justify-end items-end">
                    <div className="max-w-[85%] flex flex-col items-end">
                      <div className="bg-indigo-600 text-white px-5 py-3 rounded-2xl rounded-br-none shadow-md text-[15px] leading-relaxed tracking-wide">
                        {resultData.my_answer}
                      </div>
                      <span className="text-[10px] text-gray-400 mt-1 pr-1 font-medium">我</span>
                    </div>
                    <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center shrink-0 mb-5">
                      <User className="w-4 h-4 text-indigo-600" />
                    </div>
                  </div>

                  <div className="flex gap-3 justify-start items-end">
                    <div className="w-8 h-8 rounded-full bg-pink-100 flex items-center justify-center shrink-0 mb-5">
                      <HeartHandshake className="w-4 h-4 text-pink-500" />
                    </div>
                    <div className="max-w-[85%] flex flex-col items-start">
                      <div className="bg-white border border-gray-200 text-gray-800 px-5 py-3 rounded-2xl rounded-bl-none shadow-sm text-[15px] leading-relaxed tracking-wide">
                        {resultData.partner_answer}
                      </div>
                      <span className="text-[10px] text-gray-400 mt-1 pl-1 font-medium">{partnerDisplayName}</span>
                    </div>
                  </div>
                </div>

                <div className="h-px bg-gray-200/60 my-6 mx-4"></div>

                <button
                  onClick={handleNextCard}
                  className="w-full py-4 bg-gradient-to-r from-gray-900 to-gray-800 text-white rounded-2xl font-bold hover:shadow-xl hover:shadow-gray-200 transition-all flex items-center justify-center gap-2 active:scale-[0.98]"
                >
                  <RefreshCw className="w-5 h-5" />
                  聊聊下一個話題
                </button>
              </div>
            )}
        </div>
      </main>
    </div>
  );
}
