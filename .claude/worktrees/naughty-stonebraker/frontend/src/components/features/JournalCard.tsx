// frontend/src/components/features/JournalCard.tsx
"use client";

import { useState } from 'react';
import { Journal } from '@/types';
import TarotCard from '@/components/ui/TarotCard';
import { deleteJournal } from '@/services/api-client';
import { useToast } from '@/contexts/ToastContext';
import { useConfirm } from '@/contexts/ConfirmContext';
import { getJournalSafetyBand } from '@/lib/safety';

interface JournalCardProps {
  journal: Journal;
  onDelete?: () => void;
}

export default function JournalCard({ journal, onDelete }: JournalCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const { showToast } = useToast();
  const { confirm } = useConfirm();

  // --- 1. 日期時間格式化 ---
  const dateObj = new Date(journal.created_at);
  const dateStr = dateObj.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
  const timeStr = dateObj.toLocaleTimeString('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
  });

  // --- 2. 安全層級判斷 ---
  const safetyBand = getJournalSafetyBand(journal);
  const isElevated = safetyBand === 'elevated';
  const isCrisis = safetyBand === 'severe';
  const isSevere = isCrisis;

  // --- 3. 刪除邏輯 ---
  const handleDelete = async () => {
    const shouldDelete = await confirm({
      title: '刪除日記',
      message: '確定要刪除這篇日記嗎？刪除後無法復原。',
      confirmText: '刪除',
      cancelText: '取消',
    });
    if (!shouldDelete) return;

    setIsDeleting(true);
    try {
      await deleteJournal(journal.id);
      if (onDelete) onDelete();
    } catch (error) {
      console.error("刪除失敗", error);
      showToast('刪除失敗，請稍後再試', 'error');
      setIsDeleting(false);
    }
  };

  // 刪除中的 Loading 狀態
  if (isDeleting) {
    return (
      <div className="bg-gray-50 border border-gray-100 rounded-xl p-8 text-center animate-pulse flex flex-col items-center justify-center min-h-[200px]">
        <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-500 rounded-full animate-spin mb-2"></div>
        <p className="text-gray-400 text-sm">正在抹去這段記憶...</p>
      </div>
    );
  }

  return (
    <article 
      className={`relative group rounded-2xl shadow-sm border overflow-hidden transition-all duration-300 hover:shadow-md
      ${isCrisis
        ? 'bg-red-50/40 border-red-200'
        : isElevated
          ? 'bg-amber-50/40 border-amber-200'
          : 'bg-white border-gray-100'
      }`}
    >
      {/* 🗑️ 刪除按鈕 */}
      <button
        onClick={handleDelete}
        className="absolute top-4 right-4 z-20 p-2 text-gray-400 bg-white/60 backdrop-blur-md rounded-full 
                   hover:text-red-600 hover:bg-red-50 border border-transparent hover:border-red-100 shadow-sm
                   transition-all opacity-100 md:opacity-0 md:group-hover:opacity-100"
        title="刪除日記"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
          <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
        </svg>
      </button>

      <div className="p-6">
         {/* 頂部資訊列：日期與情緒標籤 */}
         <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 pr-10">
             <div className="flex flex-col">
               <span className={`text-sm font-semibold tracking-wide ${isCrisis ? 'text-red-500' : 'text-gray-600'}`}>
                  {dateStr}
               </span>
               <span className="text-xs text-gray-400 font-medium mt-0.5">
                  {timeStr}
               </span>
             </div>
             
             <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold self-start sm:self-auto shadow-sm
                ${isCrisis
                  ? 'bg-red-100 text-red-700 border border-red-200' 
                  : isElevated
                    ? 'bg-amber-100 text-amber-700 border border-amber-200'
                    : 'bg-indigo-50 text-indigo-600 border border-indigo-100'
                }`}>
                {isCrisis ? '🚨 高風險警示' : isElevated ? '⚠️ 情緒高張' : (journal.mood_label || '隨手記')}
             </span>
         </div>

         {/* 日記內容 */}
         <div className="mb-8">
           <p className="text-gray-700 leading-relaxed text-[15px] whitespace-pre-wrap font-sans">
            {journal.content}
           </p>
         </div>

         {/* --- AI 分析區塊 --- */}
         <div className="space-y-4">
          
          {/* 1. 嚴重警示區 (Crisis Mode) */}
          {isSevere && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-5 animate-pulse">
              <div className="flex items-center text-red-700 mb-2 font-bold text-sm">
                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                請優先照顧自己
              </div>
              <p className="text-sm text-red-600/90 mb-3 leading-relaxed">
                系統偵測到目前的情緒能量較高。建議先暫停與伴侶的同步，給自己一些空間喘息。
              </p>
              <div className="flex gap-2 mt-3">
                <span className="text-xs font-bold text-red-500 bg-white px-2 py-1 rounded border border-red-100">
                  安心專線 1925
                </span>
                <span className="text-xs font-bold text-red-500 bg-white px-2 py-1 rounded border border-red-100">
                  保護專線 113
                </span>
              </div>
            </div>
          )}

          {/* 1.5 高壓提醒區 (Tier 1) */}
          {isElevated && !isSevere && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
              <div className="flex items-center text-amber-700 mb-1 font-bold text-sm">
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M4.93 19h14.14c1.54 0 2.5-1.67 1.73-3L13.73 4c-.77-1.33-2.7-1.33-3.47 0L3.2 16c-.77 1.33.19 3 1.73 3z" />
                </svg>
                先放慢一下
              </div>
              <p className="text-sm text-amber-700/90 leading-relaxed">
                系統判定目前情緒壓力偏高，建議先做短暫安撫，再進行同步溝通。
              </p>
            </div>
          )}

          {/* 2. 深層需求 (EFT) */}
          {journal.emotional_needs && (
            <div className={`rounded-xl p-4 border ${isCrisis ? 'bg-red-50/50 border-red-100' : 'bg-gray-50 border-gray-100'}`}>
              <h4 className={`text-xs font-bold uppercase tracking-wider mb-2 flex items-center gap-2 ${isCrisis ? 'text-red-400' : 'text-gray-400'}`}>
                 {isCrisis ? '🛡️ 安全導航' : '🦁 內心深處的渴望'}
              </h4>
              <p className="text-gray-800 text-sm font-medium leading-relaxed">
                {journal.emotional_needs}
              </p>
            </div>
          )}

          {/* 3. 建議與行動 (Grid 排版) */}
          {!isSevere && (journal.advice_for_user || journal.action_for_user) && (
             <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {journal.advice_for_user && (
                <div className="bg-purple-50/40 p-4 rounded-xl border border-purple-100/60 hover:bg-purple-50 transition-colors">
                  <h4 className="text-xs font-bold text-purple-600 mb-2 uppercase tracking-wide flex items-center gap-1">
                    💡 溫馨建議
                  </h4>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    {journal.advice_for_user}
                  </p>
                </div>
              )}
              
              {journal.action_for_user && (
                <div className="bg-blue-50/40 p-4 rounded-xl border border-blue-100/60 hover:bg-blue-50 transition-colors">
                  <h4 className="text-xs font-bold text-blue-600 mb-2 uppercase tracking-wide flex items-center gap-1">
                    🚀 小小行動
                  </h4>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    {journal.action_for_user}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* 4. 伴侶同步指南 */}
          {(journal.advice_for_partner || journal.action_for_partner) && !isSevere && (
            <div className="mt-4 pt-4 border-t border-gray-100">
               <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                    🤝 伴侶同步指南 
                  </h4>
                  <span className="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full border border-gray-200">
                    僅顯示給對方
                  </span>
               </div>
               
              <div className="bg-gradient-to-r from-orange-50/50 to-amber-50/50 p-4 rounded-xl border border-orange-100/60 space-y-3">
                 {journal.advice_for_partner && (
                   <div className="flex gap-3 items-start">
                     <span className="shrink-0 text-[10px] font-bold bg-white text-orange-600 px-2 py-0.5 rounded border border-orange-100 shadow-sm mt-0.5">
                       建議
                     </span>
                     <p className="text-sm text-gray-700 leading-relaxed">{journal.advice_for_partner}</p>
                   </div>
                 )}
                 {journal.action_for_partner && (
                   <div className="flex gap-3 items-start">
                     <span className="shrink-0 text-[10px] font-bold bg-white text-orange-600 px-2 py-0.5 rounded border border-orange-100 shadow-sm mt-0.5">
                       行動
                     </span>
                     <p className="text-sm text-gray-700 leading-relaxed">{journal.action_for_partner}</p>
                   </div>
                 )}
              </div>
            </div>
          )}

          {/* 5. 推薦牌卡 (優化版：大尺寸展示) */}
          {!isSevere && journal.card_recommendation && (
            <div className="mt-8 pt-4 border-t border-gray-100">
              <div className="bg-gradient-to-br from-[#2e1065] to-[#4c1d95] rounded-2xl p-6 text-white relative overflow-hidden shadow-lg">
                
                {/* 裝飾背景 */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-white opacity-5 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2"></div>
                
                <div className="flex flex-col-reverse md:flex-row items-center gap-6 relative z-10">
                  
                  {/* 左側：文字描述 */}
                  <div className="flex-1 text-center md:text-left">
                    <div className="inline-block px-2 py-0.5 rounded border border-white/20 bg-white/10 text-[10px] font-bold tracking-widest uppercase mb-3">
                      Daily Wisdom
                    </div>
                    <h3 className="text-2xl font-serif font-bold text-white mb-2">
                      {journal.card_recommendation}
                    </h3>
                    <p className="text-sm text-indigo-100 leading-relaxed opacity-90">
                      這張牌象徵著你此刻的內在能量。試著點擊這張牌，翻開它所帶來的深層指引與祝福。
                    </p>
                  </div>

                  {/* 右側：卡片展示區 (修復尺寸與 3D 問題) */}
                  <div className="perspective-1000"> 
                    <div className="w-28 h-44 sm:w-32 sm:h-48 relative transition-transform hover:scale-105 duration-300">
                       <TarotCard cardName={journal.card_recommendation} />
                    </div>
                  </div>

                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </article>
  );
}
