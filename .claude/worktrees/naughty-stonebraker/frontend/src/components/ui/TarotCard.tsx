// frontend/src/components/ui/TarotCard.tsx

"use client";

import { useState } from 'react';

interface TarotCardProps {
  cardName: string;
}

export default function TarotCard({ cardName }: TarotCardProps) {
  const [isFlipped, setIsFlipped] = useState(false);

  return (
    <div 
      className="group w-full h-32 cursor-pointer"
      onClick={() => setIsFlipped(!isFlipped)}
      style={{ perspective: '1000px' }} // 1. 設定 3D 視角
    >
      <div 
        className="relative w-full h-full transition-all duration-700 shadow-md rounded-xl"
        style={{
          transformStyle: 'preserve-3d', // 2. 確保子元素保持 3D 空間
          transform: isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)', // 3. 翻轉邏輯
        }}
      >
        
        {/* === 正面 (還沒翻開時：紫色封面) === */}
        {/* 關鍵：backfaceVisibility: 'hidden' 確保轉過去後看不見它 */}
        <div 
          className="absolute w-full h-full rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center text-white p-4"
          style={{ 
            backfaceVisibility: 'hidden', 
            WebkitBackfaceVisibility: 'hidden', // 支援 Safari
            zIndex: 2 
          }}
        >
          <div className="border-2 border-white/30 w-full h-full rounded-lg flex items-center justify-center border-dashed">
            <div className="text-center">
              <div className="text-2xl mb-1">🔮</div>
              <p className="text-xs font-medium tracking-widest uppercase opacity-90">Click to Reveal</p>
            </div>
          </div>
        </div>

        {/* === 背面 (翻開後：白色內容) === */}
        {/* 關鍵：這張卡片預先旋轉 180 度，這樣當容器轉 180 度時，它剛好轉正！ */}
        <div 
          className="absolute w-full h-full rounded-xl bg-white border-2 border-purple-100 flex items-center justify-center overflow-hidden"
          style={{ 
            backfaceVisibility: 'hidden', 
            WebkitBackfaceVisibility: 'hidden',
            transform: 'rotateY(180deg)' 
          }}
        >
          {/* 裝飾背景 */}
          <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-purple-400 to-pink-400"></div>
          
          <div className="text-center p-4">
            <p className="text-xs text-gray-400 mb-1 uppercase tracking-wider">Today&apos;s Guidance</p>
            <h3 className="text-lg font-bold text-gray-800 font-serif">{cardName}</h3>
          </div>
          
          {/* 右下角裝飾 */}
          <div className="absolute bottom-[-10px] right-[-10px] w-12 h-12 bg-purple-50 rounded-full z-0"></div>
        </div>
        
      </div>
    </div>
  );
}
