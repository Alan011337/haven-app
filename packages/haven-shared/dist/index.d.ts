/**
 * Haven shared domain types (backend-aligned).
 * Used by both Next.js frontend and future React Native/Expo app.
 */
interface Journal {
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
interface User {
    id: string;
    email: string;
    full_name?: string;
    partner_id?: string;
    avatar_url?: string;
    partner_name?: string;
    partner_nickname?: string;
    mode?: 'solo' | 'paired';
}
declare enum CardCategory {
    DAILY_VIBE = "DAILY_VIBE",
    SOUL_DIVE = "SOUL_DIVE",
    SAFE_ZONE = "SAFE_ZONE",
    MEMORY_LANE = "MEMORY_LANE",
    GROWTH_QUEST = "GROWTH_QUEST",
    AFTER_DARK = "AFTER_DARK",
    CO_PILOT = "CO_PILOT",
    LOVE_BLUEPRINT = "LOVE_BLUEPRINT"
}
interface Card {
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

/**
 * API request/response types (backend contract).
 * Shared so web and native use the same shapes.
 */

declare const MAX_JOURNAL_CONTENT_LENGTH = 4000;
interface PartnerStatus {
    has_partner: boolean;
    latest_journal_at: string | null;
    current_score: number;
    unread_notification_count: number;
}
interface CreateJournalOptions {
    requestId?: string;
    idempotencyKey?: string;
}
interface CreateJournalResponse extends Journal {
    new_savings_score: number;
    score_gained: number;
}
interface CardResponsePayload {
    card_id: string;
    content: string;
}
interface CardResponseData {
    id: string;
    card_id: string;
    user_id: string;
    content: string;
    status: 'PENDING' | 'REVEALED';
    created_at: string;
    session_id?: string | null;
}
interface DeckRespondResult {
    status: string;
    session_status: 'WAITING_PARTNER' | 'COMPLETED';
}
interface DeckHistoryEntry {
    session_id: string;
    card_title: string | null;
    card_question: string;
    category: string;
    depth_level?: number;
    my_answer: string | null;
    partner_answer: string | null;
    revealed_at: string;
}
interface CardSession {
    id: string;
    card_id: string;
    category: string;
    status: 'PENDING' | 'WAITING_PARTNER' | 'COMPLETED';
    created_at: string;
    card: {
        id: string;
        title: string | null;
        question: string;
        category: string;
        depth_level?: number;
        tags?: string[];
    };
    partner_name?: string;
}
interface RespondToDeckOptions {
    idempotencyKey?: string;
}
interface DeckHistorySummary {
    total_records: number;
    this_month_records: number;
    top_category: string | null;
    top_category_count: number;
}

/**
 * TanStack Query key factory. Single source of truth for cache keys.
 * Web and native must use the same keys for consistency if they share cache later.
 */
declare const queryKeys: {
    readonly partnerStatus: () => readonly ["partnerStatus"];
    readonly journals: () => readonly ["journals"];
    readonly partnerJournals: () => readonly ["partnerJournals"];
    readonly gamificationSummary: () => readonly ["gamificationSummary"];
    readonly onboardingQuest: () => readonly ["onboardingQuest"];
    readonly syncNudges: () => readonly ["syncNudges"];
    readonly firstDelight: () => readonly ["firstDelight"];
    readonly deckHistory: (category: string, range: string, sort: string, q: string) => readonly ["deckHistory", string, string, string, string];
    readonly deckHistoryInfinite: (category: string, revealedFrom: string, revealedTo: string) => readonly ["deckHistoryInfinite", string, string, string];
    readonly deckHistorySummary: (category: string, revealedFrom: string, revealedTo: string) => readonly ["deckHistorySummary", string, string, string];
    readonly notifications: (params?: {
        limit?: number;
        offset?: number;
        [key: string]: unknown;
    }) => readonly ["notifications", {
        [key: string]: unknown;
        limit?: number;
        offset?: number;
    }];
    readonly notificationStats: (params?: {
        window_days?: number;
        [key: string]: unknown;
    }) => readonly ["notificationStats", {
        [key: string]: unknown;
        window_days?: number;
    }];
    readonly user: () => readonly ["user"];
    readonly featureFlags: () => readonly ["featureFlags"];
    readonly loveMapCards: () => readonly ["loveMapCards"];
    readonly loveMapNotes: () => readonly ["loveMapNotes"];
    readonly mediationStatus: () => readonly ["mediationStatus"];
    readonly blueprint: () => readonly ["blueprint"];
    readonly cooldownStatus: () => readonly ["cooldownStatus"];
    readonly dailySyncStatus: () => readonly ["dailySyncStatus"];
    readonly dailyStatus: () => readonly ["dailyStatus"];
    readonly deckCardCounts: () => readonly ["deckCardCounts"];
};

interface HavenApiClient {
    getToken(): string | null;
    getDeviceId(): string | null;
    createJournal(content: string, options?: CreateJournalOptions): Promise<CreateJournalResponse>;
    getJournals(): Promise<Journal[]>;
    getPartnerJournals(): Promise<Journal[]>;
    deleteJournal(id: string | number): Promise<void>;
    getPartnerStatus(): Promise<PartnerStatus>;
    getDailyStatus(): Promise<{
        state: string;
        card: Card | null;
        my_content?: string;
        partner_content?: string;
        session_id?: string | null;
    }>;
    drawDailyCard(): Promise<Card>;
    respondDailyCard(cardId: string, content: string, options?: {
        idempotencyKey?: string;
    }): Promise<CardResponseData>;
    drawDeckCard(category: string, forceNew?: boolean): Promise<CardSession>;
    respondToDeckCard(sessionId: string, content: string, options?: {
        idempotencyKey?: string;
    }): Promise<DeckRespondResult>;
    getDeckHistory(params?: {
        category?: string;
        limit?: number;
        offset?: number;
        revealed_from?: string;
        revealed_to?: string;
    }): Promise<DeckHistoryEntry[]>;
    getDeckHistorySummary(params?: {
        category?: string;
        revealed_from?: string;
        revealed_to?: string;
    }): Promise<DeckHistorySummary>;
}

export { type Card, CardCategory, type CardResponseData, type CardResponsePayload, type CardSession, type CreateJournalOptions, type CreateJournalResponse, type DeckHistoryEntry, type DeckHistorySummary, type DeckRespondResult, type HavenApiClient, type Journal, MAX_JOURNAL_CONTENT_LENGTH, type PartnerStatus, type RespondToDeckOptions, type User, queryKeys };
