/**
 * Haven shared domain types (backend-aligned).
 * Used by both Next.js frontend and future React Native/Expo app.
 */

export type JournalVisibility =
  | 'PRIVATE'
  | 'PRIVATE_LOCAL'
  | 'PARTNER_ORIGINAL'
  | 'PARTNER_TRANSLATED_ONLY'
  | 'PARTNER_ANALYSIS_ONLY';

export type JournalCurrentVisibility =
  | 'PRIVATE'
  | 'PARTNER_ORIGINAL'
  | 'PARTNER_TRANSLATED_ONLY';

export type JournalContentFormat = 'markdown';

export type JournalTranslationStatus =
  | 'FAILED'
  | 'NOT_REQUESTED'
  | 'PENDING'
  | 'READY';

export interface JournalAttachmentPublic {
  id: string;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
  caption?: string | null;
  url?: string | null;
}

export interface Journal {
  id: string;
  user_id?: string;
  title?: string | null;
  content: string;
  is_draft?: boolean;
  created_at: string;
  updated_at?: string;
  visibility?: JournalVisibility;
  content_format?: JournalContentFormat;
  partner_translation_status?: JournalTranslationStatus;
  partner_translation_ready_at?: string | null;
  partner_translated_content?: string | null;
  attachments?: JournalAttachmentPublic[];
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
