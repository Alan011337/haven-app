// frontend/src/components/DebugCardDraw.tsx

"use client"; 

import React, { useState } from 'react';
import { cardService, CardResponseData } from '../services/cardService';
import { Card, CardCategory } from '../types';

const DebugCardDraw: React.FC = () => {
  const [card, setCard] = useState<Card | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 👇 新增狀態：使用者的回答
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
      // 抽一張 "DAILY_VIBE" (日常共感) 的卡片
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
    <div style={{ 
      padding: '20px', 
      border: '2px dashed #666', 
      margin: '20px', 
      borderRadius: '8px',
      backgroundColor: '#f4f4f4' 
    }}>
      <h3 style={{ marginTop: 0 }}>🃏 盲盒抽卡測試機</h3>
      
      <button 
        onClick={handleDraw} 
        disabled={loading}
        style={{
          padding: '10px 20px',
          cursor: loading ? 'not-allowed' : 'pointer',
          backgroundColor: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '4px'
        }}
      >
        {loading ? '🔮 正在感應中...' : '🎲 抽一張卡片'}
      </button>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      {card && (
        <div style={{ 
          marginTop: '20px', 
          background: 'white', 
          padding: '20px', 
          borderRadius: '8px',
          boxShadow: '0 2px 5px rgba(0,0,0,0.1)'
        }}>
          <div style={{ 
            fontSize: '12px', 
            color: '#888', 
            textTransform: 'uppercase', 
            letterSpacing: '1px' 
          }}>
            {card.category} | Depth {card.depth_level ?? card.difficulty_level}
          </div>
          
          <h2 style={{ margin: '10px 0', color: '#333' }}>{card.title}</h2>
          
          <p style={{ fontStyle: 'italic', color: '#555' }}>
            &quot;{card.description}&quot;
          </p>
          
          <hr style={{ border: '0', borderTop: '1px solid #eee', margin: '15px 0' }} />
          
          <div style={{ 
            fontWeight: 'bold', 
            fontSize: '18px', 
            color: '#d32f2f',
            marginBottom: '15px'
          }}>
            Q: {card.question}
          </div>

          {/* 👇 輸入回答區塊 */}
          {submitStatus === 'success' ? (
            <div style={{ 
              backgroundColor: '#e8f5e9', 
              padding: '15px', 
              borderRadius: '8px', 
              border: '1px solid #c8e6c9' 
            }}>
              <h4 style={{ margin: '0 0 10px 0', color: '#2e7d32' }}>✅ 回答已送出！</h4>
              <p>你的狀態：<strong>{responseData?.status}</strong></p>
              
              {responseData?.status === 'PENDING' && (
                <p style={{ fontSize: '14px', color: '#666' }}>
                  ⏳ 正在等待你的伴侶回答... (盲盒鎖定中 🔒)
                </p>
              )}
              
              {responseData?.status === 'REVEALED' && (
                <p style={{ fontSize: '14px', color: '#d32f2f' }}>
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
                style={{
                  width: '100%',
                  height: '100px',
                  padding: '10px',
                  borderRadius: '4px',
                  border: '1px solid #ccc',
                  marginBottom: '10px'
                }}
              />
              <button
                onClick={handleSubmit}
                disabled={!answer.trim() || submitStatus === 'submitting'}
                style={{
                  width: '100%',
                  padding: '10px',
                  backgroundColor: answer.trim() ? '#28a745' : '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: answer.trim() ? 'pointer' : 'not-allowed'
                }}
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
