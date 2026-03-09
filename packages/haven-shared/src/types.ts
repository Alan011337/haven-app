/**
 * Haven shared domain types (backend-aligned).
 * Used by both Next.js frontend and future React Native/Expo app.
 */

export interface Journal {
  id: string;
  user_id?: string;
  content: string;
  created_at: string;
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

export interface User {
  id: string;
  email: string;
  full_name?: string;
  partner_id?: string;
  avatar_url?: string;
  partner_name?: string;
  partner_nickname?: string;
  mode?: 'solo' | 'paired';
}

export enum CardCategory {
  DAILY_VIBE = 'DAILY_VIBE',
  SOUL_DIVE = 'SOUL_DIVE',
  SAFE_ZONE = 'SAFE_ZONE',
  MEMORY_LANE = 'MEMORY_LANE',
  GROWTH_QUEST = 'GROWTH_QUEST',
  AFTER_DARK = 'AFTER_DARK',
  CO_PILOT = 'CO_PILOT',
  LOVE_BLUEPRINT = 'LOVE_BLUEPRINT',
}

export interface Card {
  id: string;
  category: CardCategory;
  title: string;
  description: string;
  question: string;
  difficulty_level: number;
  depth_level?: number;
  tags?: string[];
  created_at?: string;
}
