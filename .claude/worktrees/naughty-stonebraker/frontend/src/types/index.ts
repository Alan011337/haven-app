// frontend/src/types/index.ts

// ==========================================
// 1. 原有的定義 (請保留，不要動)
// ==========================================

// 對應後端的 JournalSchema
export interface Journal {
    id: string; // 後端是 UUID
    user_id?: string;
    content: string;
    created_at: string;
    
    // 👇 這些是 AI 分析出來的關鍵欄位 (對應後端 Schema)
    mood_label?: string;
    mood_score?: number;      
    emotional_needs?: string; 
    advice_for_user?: string;
    action_for_user?: string;      
    advice_for_partner?: string;   
    action_for_partner?: string;   
    card_recommendation?: string;
    safety_tier?: number;
}

// 對應後端的 UserSchema
export interface User {
    id: string;
    email: string;
    full_name?: string;
    
    // 👇 從 AuthContext 搬過來的
    partner_id?: string;
    avatar_url?: string;

    // 👇 這次新增的 (為了解決 page.tsx 的報錯)
    partner_name?: string;
    partner_nickname?: string;
}

// ==========================================
// 2. 新增的 Card 定義 (請加入這部分) 👇
// ==========================================

// 卡片分類 (Enum)，必須跟後端完全一致
export enum CardCategory {
  DAILY_VIBE = 'DAILY_VIBE',          // 日常共感
  SOUL_DIVE = 'SOUL_DIVE',            // 靈魂深潛
  SAFE_ZONE = 'SAFE_ZONE',            // 安全屋
  MEMORY_LANE = 'MEMORY_LANE',        // 時光機
  GROWTH_QUEST = 'GROWTH_QUEST',      // 共同成長
  AFTER_DARK = 'AFTER_DARK',          // 深夜話題
  CO_PILOT = "CO_PILOT",              // 最佳副駕
  LOVE_BLUEPRINT = "LOVE_BLUEPRINT"   // 愛情藍圖
}

// 卡片資料結構
export interface Card {
  id: string;
  category: CardCategory;
  title: string;
  description: string;
  question: string;     // 這是卡片最重要的問題
  difficulty_level: number;
  depth_level?: number;
  tags?: string[];
  created_at?: string;  // 可選，因為有時候前端不需要顯示建立時間
}
