// frontend/src/components/features/ActionCard.tsx

"use client";

import { useEffect, useState, type ComponentType } from "react";
import { fetchCard } from "@/services/api-client"; 
import { Loader2, Sparkles, Coffee, Footprints, HeartHandshake, PenTool, Star } from "lucide-react";

interface CardData {
  key: string;
  title: string;
  description: string;
  category: "comfort" | "action" | "connection";
  difficulty_level: number;
}

const icons = {
  card_hug: HeartHandshake,
  card_walk: Footprints,
  card_tea: Coffee,
  card_write: PenTool,
  default: Sparkles,
};

const defaultCard: CardData = {
  key: "default",
  title: "心靈指引",
  description: "這是一個特別的時刻，AI 建議你們給予彼此多一點的包容與支持。",
  category: "comfort",
  difficulty_level: 1
};

export default function ActionCard({ cardKey }: { cardKey?: string }) {
  const [card, setCard] = useState<CardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      if (!cardKey) {
        setLoading(false);
        return;
      }

      // 防呆：如果 key 包含空白或中文，視為 AI 幻覺，使用預設卡片但保留標題
      if (cardKey.includes(" ") || /[^\x00-\x7F]/.test(cardKey)) {
        setCard({
            ...defaultCard,
            title: cardKey, 
            category: "connection" // 幻覺卡片通常比較浪漫，給它粉紅色系
        });
        setLoading(false);
        return;
      }

      try {
        const data = await fetchCard(cardKey);
        setCard(data);
      } catch {
        setCard(defaultCard);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [cardKey]);

  if (loading) return <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-purple-300 w-8 h-8"/></div>;
  if (!card) return null;

  const iconMap: Record<string, ComponentType<{ size?: number; className?: string }>> = icons;
  const IconComponent = iconMap[card.key] || icons.default;

  // --- 🎨 視覺大升級：使用漸層與深色文字 ---
  const themeStyles = {
    comfort: {
      bg: "bg-gradient-to-br from-amber-100 to-orange-50",
      border: "border-amber-200",
      text: "text-amber-900",
      icon: "text-amber-500/20", // 背景大圖示顏色
      accent: "text-amber-600"
    },
    action: {
      bg: "bg-gradient-to-br from-emerald-100 to-teal-50",
      border: "border-emerald-200",
      text: "text-emerald-900",
      icon: "text-emerald-500/20",
      accent: "text-emerald-600"
    },
    connection: { // "Love Blueprint" 會用到這個
      bg: "bg-gradient-to-br from-pink-100 via-rose-50 to-purple-50",
      border: "border-pink-200",
      text: "text-rose-900",
      icon: "text-rose-500/20",
      accent: "text-rose-600"
    },
  };

  const theme = themeStyles[card.category] || themeStyles.comfort;

  return (
    <div className={`
      relative mt-6 group
      rounded-2xl border-2 ${theme.border} 
      ${theme.bg} 
      p-6 
      shadow-sm hover:shadow-md transition-all duration-300 hover:-translate-y-1
      overflow-hidden text-center
    `}>
      
      {/* 1. 背景裝飾 (巨大的淡化圖示) */}
      <div className={`absolute -right-8 -top-8 ${theme.icon} transition-transform duration-700 group-hover:rotate-12 group-hover:scale-110`}>
        <IconComponent size={140} />
      </div>
      
      {/* 2. 左下角的裝飾圓圈 */}
      <div className={`absolute -left-4 -bottom-4 w-24 h-24 rounded-full ${theme.border} opacity-20 blur-xl`}></div>

      {/* 內容層 */}
      <div className="relative z-10 flex flex-col items-center">
        
        {/* 頂部標籤 */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/60 backdrop-blur-sm border border-white/50 text-[10px] font-bold tracking-widest uppercase mb-3 text-gray-500 shadow-sm">
          <Star className="w-3 h-3 text-yellow-500 fill-yellow-500" />
          AI Action Card
        </div>

        {/* 標題 */}
        <h4 className={`text-xl font-serif font-bold mb-3 flex items-center gap-2 ${theme.text}`}>
          {card.title}
        </h4>
        
        {/* 分隔線 */}
        <div className="w-12 h-1 bg-current opacity-20 rounded-full mb-3"></div>

        {/* 內文 */}
        <p className={`text-sm opacity-90 leading-relaxed max-w-sm ${theme.text} font-medium`}>
          {card.description}
        </p>
        
        {/* 難度顯示 (移到底部，變成小圓點) */}
        <div className="mt-4 flex gap-1 justify-center opacity-40">
           {[...Array(3)].map((_, i) => (
              <div 
                key={i} 
                className={`w-1.5 h-1.5 rounded-full ${i < card.difficulty_level ? 'bg-current' : 'bg-gray-300'}`} 
              />
           ))}
        </div>
      </div>
    </div>
  );
}
