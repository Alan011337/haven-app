// frontend/src/app/page.tsx

"use client";

import { useEffect, useState, Suspense, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Heart, Sparkles, User, Feather, RefreshCw, Loader2 } from 'lucide-react'; 

import JournalCard from '@/components/features/JournalCard';
import PartnerJournalCard from '@/components/features/PartnerJournalCard';
import PartnerSafetyBanner from '@/components/features/PartnerSafetyBanner';
import JournalInput from '@/components/features/JournalInput';
import Sidebar from '@/components/layout/Sidebar'; 
import DailyCard from '@/components/features/DailyCard'; 

import { getJournalSafetyBand } from '@/lib/safety';
import { fetchJournals, fetchPartnerJournals, fetchPartnerStatus, markNotificationsRead } from '@/services/api-client';
import { Journal } from '@/types';

const PARTNER_SAFETY_BANNER_DISMISSED_KEY = 'partner_safety_banner_dismissed_id';

function HomeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const [activeTab, setActiveTab] = useState<'mine' | 'partner' | 'card'>('mine'); 
  const [myJournals, setMyJournals] = useState<Journal[]>([]);
  const [partnerJournals, setPartnerJournals] = useState<Journal[]>([]);
  const [loading, setLoading] = useState(true);

  // ✨ 情感存款與通知
  const [savingsScore, setSavingsScore] = useState(0);
  const [hasNewPartnerContent, setHasNewPartnerContent] = useState(false);
  const [partnerSafetyBanner, setPartnerSafetyBanner] = useState<{
    latestSevereId: string;
    severeCount: number;
  } | null>(null);

  // 監聽網址參數
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam === 'partner') setActiveTab('partner');
    else if (tabParam === 'card') setActiveTab('card');
  }, [searchParams]);

  // 🔄 核心功能：檢查狀態 (Polling)
  const checkStatus = useCallback(async () => {
    try {
      const status = await fetchPartnerStatus();
      setSavingsScore(status.current_score);
      const unreadCount = Number(status.unread_notification_count ?? 0);

      if (activeTab === 'partner') {
        setHasNewPartnerContent(false);
        return;
      }

      if (unreadCount > 0) {
        setHasNewPartnerContent(true);
        return;
      }

      if (status.latest_journal_at) {
        const lastRead = localStorage.getItem('partner_last_read_at');
        const latestTime = new Date(status.latest_journal_at).getTime();
        const lastReadTime = lastRead ? new Date(lastRead).getTime() : 0;

        // 如果最新日記時間 > 最後閱讀時間，且當前不在伴侶分頁，顯示紅點
        if (latestTime > lastReadTime) {
            setHasNewPartnerContent(true);
            return;
        }
      }

      setHasNewPartnerContent(false);
    } catch (error) {
      console.error("Status check failed", error);
    }
  }, [activeTab]);

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 30000); // 每 30 秒檢查一次紅點狀態
    return () => clearInterval(interval);
  }, [checkStatus]);


  const loadData = useCallback(async () => {
    await checkStatus();

    if (activeTab === 'card') {
      try {
        await markNotificationsRead('card');
        setHasNewPartnerContent(false);
      } catch (error) {
        console.warn('標記卡片通知已讀失敗', error);
      }
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }

      if (activeTab === 'mine') {
        const data = await fetchJournals();
        if (Array.isArray(data)) {
          const sortedData = [...data].sort(
            (a: Journal, b: Journal) =>
              new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
          );
          setMyJournals(sortedData);
        }
      } else if (activeTab === 'partner') {
        const data = await fetchPartnerJournals();
        if (Array.isArray(data)) {
          const sortedData = [...data].sort(
            (a: Journal, b: Journal) =>
              new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
          );
          setPartnerJournals(sortedData);
          if (sortedData.length > 0) {
            const newestDate = sortedData[0].created_at;
            localStorage.setItem('partner_last_read_at', newestDate);
          }

          const severeJournals = sortedData.filter(
            (item) => getJournalSafetyBand(item) === 'severe',
          );
          if (severeJournals.length > 0) {
            const latestSevereId = severeJournals[0].id;
            const dismissedId = localStorage.getItem(PARTNER_SAFETY_BANNER_DISMISSED_KEY);
            if (dismissedId === latestSevereId) {
              setPartnerSafetyBanner(null);
            } else {
              setPartnerSafetyBanner({
                latestSevereId,
                severeCount: severeJournals.length,
              });
            }
          } else {
            setPartnerSafetyBanner(null);
          }

          setHasNewPartnerContent(false);
          try {
            await markNotificationsRead('journal');
          } catch (err) {
            console.warn('標記通知已讀失敗', err);
          }
        }
      }
    } catch (error) {
      console.error("讀取失敗", error);
    } finally {
      setLoading(false);
    }
  }, [activeTab, checkStatus, router]);

  useEffect(() => {
    loadData(); 
  }, [loadData]); 

  const handleDismissPartnerSafetyBanner = useCallback(() => {
    setPartnerSafetyBanner((current) => {
      if (current) {
        localStorage.setItem(PARTNER_SAFETY_BANNER_DISMISSED_KEY, current.latestSevereId);
      }
      return null;
    });
  }, []);

  const handleTabChange = (tab: 'mine' | 'partner' | 'card') => {
    setActiveTab(tab);
    router.push(`/?tab=${tab}`, { scroll: false }); 
  };

  // 定義 Tab 的樣式邏輯
  const getTabStyle = (tabName: string) => {
    const isActive = activeTab === tabName;
    const baseStyle = "relative px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 transition-all duration-300 ease-out";
    
    // 透過顏色區分不同 Tab 的活躍狀態
    if (isActive) {
        if (tabName === 'mine') return `${baseStyle} bg-white text-indigo-600 shadow-md shadow-indigo-900/10 translate-y-[-1px]`;
        if (tabName === 'partner') return `${baseStyle} bg-white text-rose-500 shadow-md shadow-rose-900/10 translate-y-[-1px]`;
        if (tabName === 'card') return `${baseStyle} bg-white text-amber-600 shadow-md shadow-amber-900/10 translate-y-[-1px]`;
    }
    
    return `${baseStyle} text-white/70 hover:bg-white/10 hover:text-white`;
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      
      {/* 側邊欄保持不變 */}
      <Sidebar />

      <main className="flex-1 md:ml-64 p-4 md:p-8 transition-all duration-300 w-full">
        <div className="max-w-4xl mx-auto space-y-8">
          
          {/* === 🌟 Premium Header (修復版) === */}
          {/* 修正重點：將原本的 hex code 改為 standard Tailwind colors (indigo-600 etc.) 確保顏色一定會顯示 */}
          <header className="relative overflow-hidden rounded-[2.5rem] p-8 md:p-10 text-white shadow-2xl shadow-indigo-200 group bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500">
            
            {/* 裝飾性光暈 */}
            <div className="absolute top-0 right-0 w-80 h-80 bg-white opacity-10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/3 pointer-events-none"></div>
            <div className="absolute bottom-0 left-0 w-60 h-60 bg-pink-400 opacity-20 rounded-full blur-[60px] translate-y-1/3 -translate-x-1/4 pointer-events-none"></div>
            
            {/* 內容層 */}
            <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
              
              {/* 左側：歡迎詞與存款 */}
              <div className="space-y-3">
                <div className="flex items-center gap-4">
                    <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white drop-shadow-sm">
                      早安，朋友
                    </h2>
                    
                    {/* 💰 情感存款 (Glassmorphism Badge) */}
                    <div className="flex items-center gap-2 bg-white/20 backdrop-blur-md px-4 py-1.5 rounded-full border border-white/30 shadow-sm transition-transform hover:scale-105 cursor-default select-none">
                        <Heart className="w-4 h-4 text-pink-200 fill-pink-200 animate-pulse" />
                        <span className="text-sm font-bold tracking-wide text-white">{savingsScore}</span>
                    </div>
                </div>
                <p className="text-indigo-50 font-light text-base md:text-lg opacity-90 max-w-lg leading-relaxed">
                  今天的你過得好嗎？無論發生什麼，這裡都是你的避風港。
                </p>
              </div>

              {/* 右側：導航 Tabs (Glassmorphism Container) */}
              <div className="flex flex-wrap gap-1 bg-black/20 backdrop-blur-xl border border-white/10 p-1.5 rounded-2xl">
                <button
                    onClick={() => handleTabChange('mine')}
                    className={getTabStyle('mine')}
                >
                    <User size={16} strokeWidth={2.5} /> 
                    <span>我的空間</span>
                </button>
                  
                <button
                    onClick={() => handleTabChange('partner')}
                    className={getTabStyle('partner')}
                >
                    <Heart size={16} strokeWidth={2.5} className={hasNewPartnerContent ? "animate-bounce" : ""} /> 
                    <span>伴侶心聲</span>
                    
                    {/* 🔴 紅點通知 */}
                    {hasNewPartnerContent && (
                        <span className="absolute top-2 right-2 flex h-2.5 w-2.5">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500 ring-2 ring-white"></span>
                        </span>
                    )}
                </button>
                  
                <button
                    onClick={() => handleTabChange('card')}
                    className={getTabStyle('card')}
                >
                    <Sparkles size={16} strokeWidth={2.5} /> 
                    <span>每日共感</span>
                </button>
              </div>
            </div>
          </header>
          
          {/* === 內容顯示區 === */}
          <div className="animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-forwards">
            
            {/* A: 我的空間 */}
            {activeTab === 'mine' && (
              <>
                <section className="mb-10">
                  <JournalInput onJournalCreated={loadData} />
                </section>
                
                <section>
                  <div className="flex items-center justify-between mb-6 px-2">
                    <h3 className="text-xl font-bold text-slate-700 flex items-center gap-2">
                      <Feather className="w-5 h-5 text-indigo-500" />
                      時光迴廊
                    </h3>
                    <span className="text-xs font-bold text-slate-500 bg-slate-200/60 px-3 py-1 rounded-full">
                      {myJournals.length} 篇日記
                    </span>
                  </div>
                  
                  {loading ? (
                    <div className="space-y-6">
                      {[1,2].map(i => (
                        <div key={i} className="h-32 w-full bg-slate-100 rounded-2xl animate-pulse"/>
                      ))}
                    </div>
                  ) : myJournals.length === 0 ? (
                    // ✨ 保留這個精美的空狀態
                    <div className="flex flex-col items-center justify-center py-20 bg-white rounded-[2rem] border border-dashed border-slate-200 shadow-sm">
                      <div className="w-16 h-16 bg-indigo-50 rounded-full flex items-center justify-center mb-4">
                        <Feather className="w-8 h-8 text-indigo-300" />
                      </div>
                      <p className="text-slate-600 font-medium text-lg">這裡還是一片空白</p>
                      <p className="text-slate-400 text-sm mt-1">寫下第一篇日記，種下回憶的種子吧！🌱</p>
                    </div>
                  ) : (
                    <div className="grid gap-6">
                      {myJournals.map((journal) => (
                        <JournalCard key={journal.id} journal={journal} />
                      ))}
                    </div>
                  )}
                </section>
              </>
            )}

            {/* B: 伴侶空間 */}
            {activeTab === 'partner' && (
              <section>
                <div className="flex items-center justify-between mb-6 px-2">
                   <h3 className="text-xl font-bold text-slate-700 flex items-center gap-2">
                      <span className="flex h-3 w-3 relative">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-rose-500"></span>
                      </span>
                      伴侶的心聲
                   </h3>
                   <button onClick={loadData} className="text-slate-400 hover:text-slate-600 transition-colors p-2 hover:bg-slate-100 rounded-full">
                      <RefreshCw size={18} />
                   </button>
                </div>

                {partnerSafetyBanner && !loading && (
                  <PartnerSafetyBanner
                    severeCount={partnerSafetyBanner.severeCount}
                    onDismiss={handleDismissPartnerSafetyBanner}
                  />
                )}

                {loading ? (
                    <div className="space-y-6">
                      {[1,2].map(i => <div key={i} className="h-40 bg-rose-50 rounded-2xl animate-pulse"/>)}
                    </div>
                ) : partnerJournals.length === 0 ? (
                  // ✨ 保留這個精美的空狀態
                  <div className="flex flex-col items-center justify-center py-24 bg-white/60 backdrop-blur-sm rounded-[2rem] border border-dashed border-rose-200 shadow-sm">
                    <div className="w-20 h-20 bg-rose-50 rounded-full flex items-center justify-center mb-4 animate-bounce-slow">
                        <Heart className="w-10 h-10 text-rose-300 fill-rose-100" />
                    </div>
                    <p className="text-slate-700 font-medium text-lg">靜悄悄的...</p>
                    <p className="text-slate-400 text-sm mt-2 max-w-xs text-center leading-relaxed">
                      當伴侶寫下日記，這裡會出現 AI 溫柔轉譯後的文字。
                    </p>
                  </div>
                ) : (
                  <div className="grid gap-8">
                    {partnerJournals.map((journal) => (
                      <PartnerJournalCard key={journal.id} journal={journal} />
                    ))}
                  </div>
                )}
              </section>
            )}

            {/* C: 每日抽卡 */}
            {activeTab === 'card' && (
               <section className="flex flex-col items-center justify-center py-8 min-h-[60vh]">
                  <div className="w-full max-w-2xl transform transition-all duration-500 hover:scale-[1.01]">
                     <DailyCard />
                  </div>
                  <p className="mt-8 text-slate-400 text-sm font-light tracking-widest uppercase opacity-60">
                    Daily Ritual · Connection
                  </p>
               </section>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={
        <div className="min-h-screen flex items-center justify-center bg-slate-50">
            <div className="flex flex-col items-center gap-4">
                <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
                <p className="text-indigo-400 font-medium tracking-widest text-sm">LOADING HAVEN...</p>
            </div>
        </div>
    }>
      <HomeContent />
    </Suspense>
  );
}
