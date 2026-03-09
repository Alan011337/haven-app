// frontend/src/components/features/JournalInput.tsx
"use client";

import { isAxiosError } from 'axios';
import { useEffect, useState } from 'react';
import { AlertTriangle, PhoneCall, Shield } from 'lucide-react';

import { createJournal } from '@/services/api-client';
import { useToast } from '@/contexts/ToastContext';
import { resolveSafetyBand } from '@/lib/safety';

interface JournalInputProps {
  onJournalCreated: () => void;
}

interface SafetyGuidanceState {
  tier: number;
  adviceForUser?: string;
  actionForUser?: string;
}

const MAX_JOURNAL_CONTENT_LENGTH = 4000;

export default function JournalInput({ onJournalCreated }: JournalInputProps) {
  const [content, setContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [safetyGuidance, setSafetyGuidance] = useState<SafetyGuidanceState | null>(null);
  const { showToast } = useToast();

  useEffect(() => {
    if (!safetyGuidance) {
      return;
    }

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSafetyGuidance(null);
      }
    };
    window.addEventListener('keydown', onKeyDown);

    return () => {
      window.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [safetyGuidance]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    setIsSubmitting(true);

    try {
      const result = await createJournal(content);

      if (result) {
        const safetyTier = Number(result.safety_tier ?? 0);
        const safetyBand = resolveSafetyBand(result.safety_tier);
        setContent('');
        onJournalCreated();

        if (safetyBand === 'severe') {
          setSafetyGuidance({
            tier: safetyTier,
            adviceForUser: result.advice_for_user,
            actionForUser: result.action_for_user,
          });
          showToast('已啟動安全引導模式，先照顧好自己。', 'info');
        } else if (safetyBand === 'elevated') {
          showToast('系統偵測你現在有些緊繃，先慢一點也沒關係。', 'info');
        }
      }
    } catch (error) {
      console.error('發布失敗', error);
      if (isAxiosError(error)) {
        showToast(error.response?.data?.detail || '發布失敗，請稍後再試', 'error');
        return;
      }
      if (error instanceof Error) {
        showToast(error.message, 'error');
      } else {
        showToast('AI 分析服務連線失敗，請確認後端是否啟動', 'error');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="mb-8 bg-white p-4 rounded-xl shadow-sm border border-gray-100">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="今天發生了什麼事？心情如何？（試著寫寫看，AI 會幫你分析喔...）"
          className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none resize-none min-h-[100px] text-gray-700"
          disabled={isSubmitting}
          maxLength={MAX_JOURNAL_CONTENT_LENGTH}
          suppressHydrationWarning={true}
        />
        <p className="mt-2 text-right text-xs text-gray-400">
          {content.length}/{MAX_JOURNAL_CONTENT_LENGTH}
        </p>

        <div className="mt-3 flex justify-end">
          <button
            type="submit"
            disabled={isSubmitting || !content.trim()}
            className={`px-6 py-2 rounded-lg font-medium transition-all duration-200
              ${
                isSubmitting
                  ? 'bg-purple-100 text-purple-400 cursor-not-allowed'
                  : 'bg-purple-600 text-white hover:bg-purple-700 shadow-md hover:shadow-lg'
              }`}
          >
            {isSubmitting ? (
              <span className="flex items-center">
                <svg
                  className="animate-spin -ml-1 mr-2 h-4 w-4 text-purple-500"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                AI 分析中...
              </span>
            ) : (
              '✨ 寫下此刻'
            )}
          </button>
        </div>
      </form>

      {safetyGuidance && (
        <div className="fixed inset-0 z-[130] bg-black/45 backdrop-blur-sm p-4 flex items-center justify-center">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="safety-guidance-title"
            className="w-full max-w-xl bg-white rounded-3xl shadow-2xl border border-rose-100 overflow-hidden"
          >
            <div className="px-6 py-5 bg-gradient-to-r from-rose-500 to-pink-500 text-white">
              <div className="flex items-center gap-2.5">
                <AlertTriangle className="w-5 h-5" />
                <h3 id="safety-guidance-title" className="text-lg font-bold">
                  先把安全放在第一位
                </h3>
              </div>
              <p className="text-sm text-rose-50 mt-2 leading-relaxed">
                系統偵測到你現在承受的情緒張力偏高。先安頓自己，再慢慢處理後續對話。
              </p>
            </div>

            <div className="p-6 space-y-4">
              <div className="rounded-2xl border border-rose-100 bg-rose-50/70 p-4">
                <p className="text-sm font-semibold text-rose-700 mb-2 flex items-center gap-2">
                  <Shield className="w-4 h-4" />
                  安全優先建議（Tier {safetyGuidance.tier}）
                </p>
                <p className="text-sm text-rose-800/90 leading-relaxed">
                  {safetyGuidance.actionForUser || '請先離開高壓情境、深呼吸，優先確認自身安全。'}
                </p>
              </div>

              {safetyGuidance.adviceForUser && (
                <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">AI 引導</p>
                  <p className="text-sm text-gray-700 leading-relaxed">{safetyGuidance.adviceForUser}</p>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <a
                  href="tel:1925"
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700 hover:bg-rose-100 transition-colors"
                >
                  <PhoneCall className="w-4 h-4" />
                  安心專線 1925
                </a>
                <a
                  href="tel:113"
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-700 hover:bg-amber-100 transition-colors"
                >
                  <PhoneCall className="w-4 h-4" />
                  保護專線 113
                </a>
              </div>

              <div className="pt-1 flex justify-end">
                <button
                  type="button"
                  onClick={() => setSafetyGuidance(null)}
                  className="rounded-xl bg-gray-900 text-white px-4 py-2.5 text-sm font-medium hover:bg-gray-800 transition-colors"
                >
                  我知道了
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
