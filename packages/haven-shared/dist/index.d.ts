/**
 * Haven shared domain types (backend-aligned).
 * Used by both Next.js frontend and future React Native/Expo app.
 */
type JournalVisibility = 'PRIVATE' | 'PRIVATE_LOCAL' | 'PARTNER_ORIGINAL' | 'PARTNER_TRANSLATED_ONLY' | 'PARTNER_ANALYSIS_ONLY';
type JournalCurrentVisibility = 'PRIVATE' | 'PARTNER_ORIGINAL' | 'PARTNER_TRANSLATED_ONLY';
type JournalContentFormat = 'markdown';
type JournalTranslationStatus = 'FAILED' | 'NOT_REQUESTED' | 'PENDING' | 'READY';
interface JournalAttachmentPublic {
    id: string;
    file_name: string;
    mime_type: string;
    size_bytes: number;
    created_at: string;
    caption?: string | null;
    url?: string | null;
}
interface Journal {
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

declare const MAX_JOURNAL_CONTENT_LENGTH = 12000;
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
interface JournalDraftPayload {
    is_draft?: boolean;
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
    readonly journalDetail: (journalId: string) => readonly ["journalDetail", string];
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
    readonly loveMapSystem: () => readonly ["loveMapSystem"];
    readonly loveMapSharedFutureSuggestions: () => readonly ["loveMapSharedFutureSuggestions"];
    readonly loveMapSharedFutureRefinements: () => readonly ["loveMapSharedFutureRefinements"];
    readonly mediationStatus: () => readonly ["mediationStatus"];
    readonly blueprint: () => readonly ["blueprint"];
    readonly cooldownStatus: () => readonly ["cooldownStatus"];
    readonly dailySyncStatus: () => readonly ["dailySyncStatus"];
    readonly dailyStatus: () => readonly ["dailyStatus"];
    readonly deckCardCounts: () => readonly ["deckCardCounts"];
};

/**
 * Cross-platform Haven editorial design tokens.
 * Web remains the visual source of truth; native consumes these distilled values.
 */
declare const havenEditorialTokens: {
    readonly color: {
        readonly background: "#F8F3ED";
        readonly backgroundMuted: "#F2EAE1";
        readonly surface: "#FFFBF6";
        readonly surfaceSecondary: "#F7EFE6";
        readonly surfaceElevated: "#FFF8F1";
        readonly foreground: "#352C26";
        readonly foregroundMuted: "#7B6D62";
        readonly foregroundSoft: "#9E9185";
        readonly primary: "#C7A173";
        readonly primaryStrong: "#B78B59";
        readonly primarySoft: "#EFE2D0";
        readonly accent: "#8E9C8D";
        readonly accentSoft: "#E5ECE3";
        readonly border: "#E7DBCF";
        readonly borderStrong: "#D8C7B7";
        readonly danger: "#B86460";
        readonly dangerSoft: "#F7E5E2";
        readonly heroBase: "#4E4036";
        readonly heroGlow: "#E2C198";
        readonly inkInverse: "#FFF8F1";
        readonly overlay: "rgba(53, 44, 38, 0.04)";
    };
    readonly spacing: {
        readonly xxs: 4;
        readonly xs: 8;
        readonly sm: 12;
        readonly md: 16;
        readonly lg: 24;
        readonly xl: 32;
        readonly xxl: 48;
    };
    readonly radius: {
        readonly sm: 12;
        readonly md: 18;
        readonly lg: 24;
        readonly xl: 32;
        readonly pill: 999;
    };
    readonly motion: {
        readonly fast: 180;
        readonly normal: 240;
        readonly slow: 340;
        readonly ritual: 520;
    };
    readonly typography: {
        readonly display: 34;
        readonly title: 24;
        readonly body: 16;
        readonly caption: 13;
        readonly eyebrow: 11;
    };
};
type HavenEditorialTokens = typeof havenEditorialTokens;

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

export { type Card, CardCategory, type CardResponseData, type CardResponsePayload, type CardSession, type CreateJournalOptions, type CreateJournalResponse, type DeckHistoryEntry, type DeckHistorySummary, type DeckRespondResult, type HavenApiClient, type HavenEditorialTokens, type Journal, type JournalAttachmentPublic, type JournalContentFormat, type JournalCurrentVisibility, type JournalDraftPayload, type JournalTranslationStatus, type JournalVisibility, MAX_JOURNAL_CONTENT_LENGTH, type PartnerStatus, type RespondToDeckOptions, type User, havenEditorialTokens, queryKeys };
