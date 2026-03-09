// frontend/src/components/DebugCardDraw.tsx
// Debug-only component; uses semantic tokens only (haven-ui / ART-DIRECTION).

"use client";

import React, { useState } from 'react';
import { cardService, CardResponseData } from '@/services/cardService';
import { Card, CardCategory } from '@/types';

const DebugCardDraw: React.FC = () => {
  const [card, setCard] = useState<Card | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [answer, setAnswer] = useState('');
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'submitting' | 'success'>('idle');
  const [responseData, setResponseData] = useState<CardResponseData | null>(null);

  const handleDraw = async () => {
    setLoading(true);
    setError(null);
    setCard(null);
    setAnswer('');
    setSubmitStatus('idle');
    setResponseData(null);

    try {
      const newCard = await cardService.drawCard(CardCategory.DAILY_VIBE);
      setCard(newCard);
    } catch {
      setError('抽卡失敗！請確認後端是否開啟 (Port 8000)');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!card || !answer.trim()) return;

    setSubmitStatus('submitting');
    try {
      const result = await cardService.respondToCard({
        card_id: String(card.id),
        content: answer,
      });
      setResponseData(result);
      setSubmitStatus('success');
    } catch {
      setError('送出回答失敗，請稍後再試。');
      setSubmitStatus('idle');
    }
  };

  return (
    <div className="p-5 border-2 border-dashed border-border rounded-lg m-5 bg-muted">
      <h3 className="mt-0 text-foreground">🃏 盲盒抽卡測試機</h3>

      <button
        type="button"
        onClick={handleDraw}
        disabled={loading}
        className="px-5 py-2.5 rounded-button border-0 bg-primary text-primary-foreground cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-haven-fast ease-haven"
        aria-label="抽一張卡片"
      >
        {loading ? '🔮 正在感應中...' : '🎲 抽一張卡片'}
      </button>

      {error && <p className="text-destructive mt-2">{error}</p>}

      {card && (
        <div className="mt-5 bg-card p-5 rounded-lg shadow-soft border border-border">
          <div className="text-caption text-muted-foreground uppercase tracking-wide">
            {card.category} | Depth {card.depth_level ?? card.difficulty_level}
          </div>

          <h2 className="my-2.5 text-foreground text-title font-semibold">{card.title}</h2>

          <p className="italic text-muted-foreground text-body">&quot;{card.description}&quot;</p>

          <hr className="border-0 border-t border-border my-4" aria-hidden />

          <div className="font-bold text-lg text-destructive mb-4">
            Q: {card.question}
          </div>

          {submitStatus === 'success' ? (
            <div className="bg-chart-2/10 p-4 rounded-lg border border-border">
              <h4 className="m-0 mb-2.5 text-chart-2 font-semibold">✅ 回答已送出！</h4>
              <p className="text-foreground">你的狀態：<strong>{responseData?.status}</strong></p>

              {responseData?.status === 'PENDING' && (
                <p className="text-sm text-muted-foreground mt-2">
                  ⏳ 正在等待你的伴侶回答... (盲盒鎖定中 🔒)
                </p>
              )}

              {responseData?.status === 'REVEALED' && (
                <p className="text-sm text-destructive mt-2">
                  🎉 恭喜！伴侶也回答了，盲盒已解鎖！ (雙方可見 🔓)
                </p>
              )}
            </div>
          ) : (
            <div>
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="在這裡寫下你的真心話..."
                aria-label="回答內容（真心話）"
                className="w-full min-h-[100px] p-2.5 rounded-input border border-input bg-background text-foreground placeholder:text-muted-foreground mb-2.5 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
              />
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!answer.trim() || submitStatus === 'submitting'}
                className={`w-full py-2.5 rounded-button border-0 text-primary-foreground transition-colors duration-haven-fast ease-haven disabled:opacity-50 disabled:cursor-not-allowed ${answer.trim() ? 'bg-primary cursor-pointer' : 'bg-muted cursor-not-allowed'}`}
                aria-label="送出回答"
              >
                {submitStatus === 'submitting' ? '傳送中...' : '✉️ 送出回答'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DebugCardDraw;
