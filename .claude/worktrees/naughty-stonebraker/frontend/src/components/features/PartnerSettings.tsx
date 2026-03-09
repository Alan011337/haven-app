// frontend/src/components/features/PartnerSettings.tsx

"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { isAxiosError } from 'axios';
import { useRouter } from 'next/navigation';
import { Heart, Link2, Copy, Check, Sparkles, Loader2, ArrowRight, Smartphone, QrCode } from 'lucide-react';
import { fetchUserMe, generateInviteCode, pairWithPartner } from '@/services/user';
import { useToast } from '@/contexts/ToastContext';

interface UserData {
  id: string;
  email: string;
  partner_id?: string;
  partner_name?: string; 
  invite_code?: string;
}

export default function PartnerSettings() {
  const router = useRouter();
  const [user, setUser] = useState<UserData | null>(null);
  const [loading, setLoading] = useState(true);
  const [inviteCode, setInviteCode] = useState('');
  const [inputCode, setInputCode] = useState('');
  const [binding, setBinding] = useState(false);
  const [copied, setCopied] = useState(false);
  const { showToast } = useToast();

  // --- 1. 取得使用者資料 ---
  const fetchUser = useCallback(async () => {
    try {
      const me = await fetchUserMe();
      setUser(me);
      // /users/me 未必回傳 invite_code；避免把 user id 當邀請碼顯示。
      setInviteCode(me.invite_code || '');
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  // --- 2. 產生邀請碼 ---
  const handleGenerate = async () => {
    try {
      const result = await generateInviteCode();
      setInviteCode(result.code);
    } catch (error) {
      console.error(error);
      showToast("產生失敗，請稍後再試", 'error');
    }
  };

  // --- 3. 綁定伴侶 ---
  const handleBind = async () => {
    if(!inputCode) return;
    setBinding(true);
    try {
      await pairWithPartner(inputCode);
      await fetchUser(); 
      showToast("綁定成功！", 'success');
    } catch (error) {
      console.error(error);
      if (isAxiosError(error) && error.response?.status === 409) {
        showToast(error.response.data?.detail || "綁定狀態衝突，請稍後再試。", 'error');
      } else if (isAxiosError(error) && error.response?.status === 400) {
        showToast("綁定失敗，邀請碼不存在或已失效。", 'error');
      } else {
        showToast("綁定失敗，請確認代碼是否正確或過期", 'error');
      }
    } finally {
      setBinding(false);
    }
  };

  // --- 4. 複製到剪貼簿 ---
  const copyToClipboard = () => {
    navigator.clipboard.writeText(inviteCode);
    setCopied(true);
    showToast("邀請碼已複製", 'info');
    setTimeout(() => setCopied(false), 2000);
  };

  // 取得姓名首字
  const getInitial = (name?: string) => name ? name.charAt(0).toUpperCase() : "?";

  if (loading) return <div className="p-12 flex justify-center"><Loader2 className="animate-spin text-rose-400 w-8 h-8"/></div>;

  return (
    <div className="w-full max-w-3xl mx-auto py-8">
      
      {/* === 標題區 === */}
      <div className="text-center mb-12 animate-in fade-in slide-in-from-top-4 duration-700">
        <h2 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-rose-500 via-pink-500 to-purple-600 inline-flex items-center gap-3 tracking-tight">
          <Heart className="fill-rose-500 text-rose-500 animate-pulse drop-shadow-lg" size={32} /> 
          伴侶連結
        </h2>
        <p className="text-slate-500 mt-4 text-base font-medium max-w-md mx-auto">
          連結彼此的帳號，讓 AI 成為你們關係的橋樑，<br/>在專屬於你們的雲端日記中相遇。
        </p>
      </div>

      <div className="relative group">
        {/* 背景光暈效果 */}
        <div className="absolute -inset-1 bg-gradient-to-r from-rose-300 via-fuchsia-400 to-indigo-400 rounded-[2.5rem] blur opacity-20 group-hover:opacity-30 transition duration-1000"></div>
        
        {/* 主要卡片容器 */}
        <div className="relative bg-white/90 backdrop-blur-2xl rounded-[2.5rem] p-10 border border-white shadow-[0_8px_40px_rgb(0,0,0,0.04)] overflow-hidden">
          
          {user?.partner_id ? (
            // ==========================
            // === 情境 A: 已連結狀態 ===
            // ==========================
            <div className="flex flex-col items-center animate-in fade-in zoom-in duration-700">
              
              {/* 連線視覺圖 */}
              <div className="flex items-center justify-center gap-8 mb-10 relative w-full max-w-md">
                {/* 我 */}
                <div className="flex flex-col items-center gap-3 relative z-10">
                  <div className="w-24 h-24 rounded-full bg-gradient-to-br from-slate-50 to-slate-100 border-4 border-white shadow-xl flex items-center justify-center">
                    <span className="text-3xl font-black text-slate-700">{getInitial(user.email)}</span>
                  </div>
                  <span className="text-xs font-bold text-slate-400 tracking-widest uppercase bg-slate-100 px-3 py-1 rounded-full">You</span>
                </div>

                {/* 動態連線 */}
                <div className="flex-1 h-[3px] bg-gradient-to-r from-slate-200 via-rose-300 to-rose-200 relative mx-2 rounded-full overflow-hidden">
                   <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/50 to-transparent w-full -translate-x-full animate-[shimmer_2s_infinite]"></div>
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-12 h-12 bg-white rounded-full border-4 border-rose-50 shadow-lg flex items-center justify-center z-20">
                    <Heart className="w-6 h-6 text-rose-500 fill-rose-500 animate-[pulse_3s_ease-in-out_infinite]" />
                  </div>
                </div>

                {/* 伴侶 */}
                <div className="flex flex-col items-center gap-3 relative z-10">
                  <div className="w-24 h-24 rounded-full bg-gradient-to-br from-rose-50 to-pink-50 border-4 border-white shadow-xl shadow-rose-100 flex items-center justify-center">
                    <span className="text-3xl font-black text-rose-500">{getInitial(user.partner_name)}</span>
                  </div>
                  <span className="text-xs font-bold text-rose-300 tracking-widest uppercase bg-rose-50 px-3 py-1 rounded-full">Partner</span>
                </div>
              </div>

              <div className="text-center space-y-3">
                <h3 className="text-3xl font-bold text-slate-800 tracking-tight">
                  已與 <span className="text-transparent bg-clip-text bg-gradient-to-r from-rose-500 to-pink-600">{user.partner_name || '伴侶'}</span> 連結
                </h3>
                
                <div className="flex justify-center">
                  <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-50 text-emerald-600 text-sm font-bold border border-emerald-100 shadow-sm">
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                    </span>
                    關係狀態：活躍中
                  </div>
                </div>

                {/* 按鈕：跳轉到伴侶日記頁面 */}
                <div className="pt-8">
                    <button
                        onClick={() => router.push('/?tab=partner')} 
                        className="
                            group relative inline-flex items-center gap-3 px-10 py-4
                            bg-gradient-to-r from-rose-500 to-pink-600 
                            text-white text-base font-bold tracking-wide
                            rounded-full 
                            shadow-[0_10px_20px_-5px_rgba(244,63,94,0.4)]
                            hover:shadow-[0_20px_30px_-10px_rgba(244,63,94,0.5)] 
                            hover:scale-105 hover:-translate-y-1
                            active:scale-95
                            transition-all duration-300 ease-out
                        "
                    >
                        <span>去看看對方的日記</span>
                        <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        
                        {/* 光澤動畫 */}
                        <div className="absolute inset-0 rounded-full overflow-hidden">
                           <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]"></div>
                        </div>
                    </button>
                </div>
              </div>
            </div>
          ) : (
            // ==========================
            // === 情境 B: 未連結狀態 ===
            // ==========================
            <div className="space-y-10 animate-in slide-in-from-bottom-4 duration-500">
               <div className="text-center">
                  <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm border border-slate-100">
                    <Link2 className="text-slate-400 w-10 h-10" />
                  </div>
                  <h3 className="text-2xl font-bold text-slate-800 mb-2">尚未連結伴侶</h3>
                  <p className="text-slate-500">請產生邀請碼給對方，或是輸入對方的代碼。</p>
               </div>

               <div className="grid md:grid-cols-2 gap-8 relative z-10">
                  {/* 左側：產生代碼 */}
                  <div className="bg-gradient-to-b from-slate-50 to-white p-8 rounded-[1.5rem] border border-slate-100 flex flex-col justify-between shadow-sm hover:shadow-md transition-shadow">
                    <div>
                        <div className="flex items-center gap-2 mb-4">
                           <QrCode className="text-rose-400 w-5 h-5"/>
                           <label className="text-xs font-bold text-rose-400 uppercase tracking-widest">你的邀請碼</label>
                        </div>
                        
                        <div className="flex gap-2 mb-6">
                            <code className="flex-1 bg-white border-2 border-slate-100 p-4 rounded-xl text-xl font-mono text-slate-700 text-center font-bold tracking-widest shadow-inner">
                                {inviteCode || "------"}
                            </code>
                            <button 
                                onClick={copyToClipboard} 
                                disabled={!inviteCode} 
                                className="px-4 bg-white border-2 border-slate-100 rounded-xl hover:bg-slate-50 hover:border-slate-300 transition-all text-slate-400 hover:text-slate-600"
                            >
                                {copied ? <Check size={20} className="text-green-500"/> : <Copy size={20}/>}
                            </button>
                        </div>
                    </div>
                    <button 
                        onClick={handleGenerate} 
                        className="w-full py-3 bg-slate-100 text-slate-600 rounded-xl text-sm font-bold hover:bg-slate-200 transition-colors flex items-center justify-center gap-2"
                    >
                        <Sparkles size={16}/> 產生新代碼
                    </button>
                  </div>

                  {/* 右側：輸入代碼 */}
                  <div className="bg-gradient-to-b from-slate-50 to-white p-8 rounded-[1.5rem] border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-center gap-2 mb-4">
                       <Smartphone className="text-indigo-400 w-5 h-5"/>
                       <label className="text-xs font-bold text-indigo-400 uppercase tracking-widest">輸入伴侶代碼</label>
                    </div>

                    <div className="space-y-4">
                      <input 
                        type="text" 
                        value={inputCode}
                        onChange={(e) => setInputCode(e.target.value.toUpperCase())}
                        placeholder="在此輸入 6 碼"
                        className="w-full bg-white border-2 border-slate-100 p-4 rounded-xl text-lg outline-none focus:border-indigo-300 focus:ring-4 focus:ring-indigo-100 transition-all uppercase font-mono text-center placeholder:text-slate-300"
                        maxLength={6}
                      />
                      <button 
                        onClick={handleBind}
                        disabled={binding || inputCode.length < 6}
                        className={`w-full py-3 rounded-xl text-white font-bold tracking-wide transition-all shadow-lg flex items-center justify-center gap-2
                          ${inputCode.length >= 6 
                            ? 'bg-gradient-to-r from-indigo-500 to-purple-600 hover:shadow-indigo-200 hover:scale-[1.02]' 
                            : 'bg-slate-300 cursor-not-allowed shadow-none'}`}
                      >
                        {binding ? <Loader2 className="animate-spin w-5 h-5"/> : (
                            <>
                                <Link2 className="w-5 h-5"/> 確認綁定
                            </>
                        )}
                      </button>
                    </div>
                  </div>
               </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
