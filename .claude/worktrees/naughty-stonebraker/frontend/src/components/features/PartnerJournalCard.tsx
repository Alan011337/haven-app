// frontend/src/components/features/PartnerJournalCard.tsx

import React from 'react';
import { Journal } from '@/types'; 
import ActionCard from "./ActionCard";
import { Sparkles, HeartHandshake, Lightbulb, Lock, ShieldAlert } from 'lucide-react';
import { getJournalSafetyBand } from '@/lib/safety';

interface Props {
  journal: Journal;
}

export default function PartnerJournalCard({ journal }: Props) {
  const date = new Date(journal.created_at).toLocaleDateString('zh-TW', {
    month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  const safetyBand = getJournalSafetyBand(journal);
  const isElevated = safetyBand === 'elevated';
  const isSevere = safetyBand === 'severe';
  const isSafetyConcern = isElevated || isSevere;

  return (
    <div className={`
      relative group overflow-hidden
      bg-white rounded-[2rem] p-8 
      shadow-[0_10px_40px_-10px_rgba(0,0,0,0.05)] 
      border border-gray-100
      transition-all duration-500 hover:shadow-[0_20px_50px_-12px_rgba(0,0,0,0.1)] hover:-translate-y-1
      ${isSevere ? 'ring-2 ring-rose-100' : isElevated ? 'ring-2 ring-amber-100' : ''}
    `}>
      {/* 裝飾背景 */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-b from-rose-50 to-transparent rounded-bl-[100px] opacity-60 pointer-events-none"></div>

      {/* --- Header --- */}
      <div className="relative flex justify-between items-start mb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-rose-100 text-rose-500 flex items-center justify-center text-xl shadow-inner">
             {/* 根據情緒顯示不同 icon，這裡簡化 */}
             😊
          </div>
          <div>
            <div className="text-sm font-medium text-gray-400 mb-0.5">{date}</div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold text-gray-800">
                心情：{journal.mood_label || '平靜'}
              </span>
              {isSafetyConcern && (
                <span
                  className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-bold ${
                    isSevere ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700'
                  }`}
                >
                  <ShieldAlert size={12}/> {isSevere ? '安全優先模式' : '需多加關懷'}
                </span>
              )}
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-1.5 text-xs font-medium text-gray-400 bg-gray-50 px-3 py-1.5 rounded-full border border-gray-100">
          <span>🔒</span>
          <span>原文已隱私保護</span>
        </div>
      </div>

      {/* --- 核心：情感需求 (Quote Style) --- */}
      <div className="relative mb-8 p-6 bg-gradient-to-r from-rose-50/80 to-white rounded-2xl border border-rose-100/50">
        <Sparkles className="absolute -top-3 -left-2 text-rose-300 fill-rose-100 w-8 h-8" />
        <h4 className="text-xs font-bold text-rose-400 uppercase tracking-widest mb-3 ml-1">
          {isSevere ? '安全導航' : '內在需求'}
        </h4>
        <p className="text-xl text-gray-700 font-medium leading-relaxed font-serif italic">
          &quot;{journal.emotional_needs || '希望能被理解與支持'}&quot;
        </p>
      </div>

      {isSevere && (
        <div className="mb-8 bg-rose-50 border border-rose-200 p-5 rounded-2xl">
          <h4 className="text-sm font-bold text-rose-700 mb-2 flex items-center gap-2">
            <ShieldAlert size={16} />
            高風險提醒：先確認安全，再談溝通
          </h4>
          <p className="text-sm text-rose-700/90 leading-relaxed mb-3">
            系統偵測到目前情緒張力偏高。建議先降低刺激、確認彼此安全，暫停深度討論。
          </p>
          <div className="flex flex-wrap gap-2 mb-3">
            <a
              href="tel:1925"
              className="text-xs font-bold text-rose-600 bg-white px-2 py-1 rounded border border-rose-100 hover:bg-rose-100 transition-colors"
            >
              安心專線 1925
            </a>
            <a
              href="tel:113"
              className="text-xs font-bold text-rose-600 bg-white px-2 py-1 rounded border border-rose-100 hover:bg-rose-100 transition-colors"
            >
              保護專線 113
            </a>
          </div>

          {(journal.action_for_partner || journal.advice_for_partner) && (
            <div className="bg-white/80 border border-rose-100 rounded-xl p-4 space-y-2">
              {journal.action_for_partner && (
                <p className="text-sm text-rose-800">
                  <span className="font-bold mr-1">行動：</span>
                  {journal.action_for_partner}
                </p>
              )}
              {journal.advice_for_partner && (
                <p className="text-sm text-rose-800">
                  <span className="font-bold mr-1">建議：</span>
                  {journal.advice_for_partner}
                </p>
              )}
            </div>
          )}

          <div className="mt-3 rounded-xl border border-rose-100 bg-white/80 px-3 py-2 text-xs text-rose-700 flex items-center gap-1.5 font-semibold">
            <Lock size={13} />
            高風險模式已啟用：暫停暖心小行動推薦，優先安全與降壓。
          </div>
        </div>
      )}

      {/* --- Grid Layout for Recommendations --- */}
      {!isSevere && <div className="grid md:grid-cols-2 gap-6">
        
        {/* 左側：AI 推薦行動卡片 */}
        {journal.card_recommendation && (
            <div className="flex flex-col h-full">
              <h4 className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
                <HeartHandshake size={14} /> 暖心小行動
              </h4>
              <div className="flex-1">
                 <ActionCard cardKey={journal.card_recommendation} />
              </div>
            </div>
        )}

        {/* 右側：具體建議文字 */}
        <div className="space-y-4">
            {journal.action_for_partner && (
              <div className="bg-emerald-50/50 p-4 rounded-2xl border border-emerald-100/50">
                <h4 className="flex items-center gap-2 text-sm font-bold text-emerald-800 mb-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
                  具體做法
                </h4>
                <p className="text-emerald-900/80 text-sm leading-relaxed text-justify">
                  {journal.action_for_partner}
                </p>
              </div>
            )}

            {journal.advice_for_partner && (
              <div className="bg-indigo-50/50 p-4 rounded-2xl border border-indigo-100/50">
                <h4 className="flex items-center gap-2 text-sm font-bold text-indigo-800 mb-2">
                  <Lightbulb size={14} className="text-indigo-600"/>
                  理解視角
                </h4>
                <p className="text-indigo-900/80 text-sm leading-relaxed text-justify">
                  {journal.advice_for_partner}
                </p>
              </div>
            )}
        </div>
      </div>}
    </div>
  );
}
