import type {
  JournalTranslationStatus,
  JournalVisibility,
} from '@/types';

export type JournalTranslationReadinessState =
  | 'failed'
  | 'not-ready'
  | 'pending'
  | 'ready';

export interface JournalTranslationStatusPresentation {
  label: string;
  message: string;
  readyAt: string | null;
  shortLabel: string;
  state: JournalTranslationReadinessState;
  tone: 'error' | 'neutral' | 'progress' | 'success';
}

interface BuildJournalTranslationStatusPresentationOptions {
  currentVisibility?: JournalVisibility | null;
  hasCurrentJournalId?: boolean;
  hasExplicitVisibilitySelection?: boolean;
  isDraft?: boolean;
  partnerTranslationReadyAt?: string | null;
  partnerTranslationStatus?: JournalTranslationStatus | null;
  persistedVisibility?: JournalVisibility | null;
}

const PRIVATE_PARTNER_MESSAGE = '你還沒保存這次分享設定。保存前，伴侶仍看不到這一頁。';
const ORIGINAL_PARTNER_MESSAGE = '你還沒保存這次分享設定。保存前，伴侶仍看到原文。';
const LEGACY_ANALYSIS_PARTNER_MESSAGE = '你還沒保存這次分享設定。保存前，伴侶仍看到舊版分析資訊。';
const NOT_READY_MESSAGE = '這一頁設成整理後版本後，保存才會開始準備伴侶可讀的版本。';
const PENDING_MESSAGE = 'Haven 正在準備伴侶可讀的版本。整理完成前，伴侶還看不到這段內容。';
const READY_MESSAGE = '伴侶現在看到的是 Haven 整理後的版本，不是你的原文或圖片。';
const FAILED_MESSAGE = 'Haven 這次還沒整理好伴侶可讀的版本。伴侶目前看不到這段內容；你下次保存這一頁時，Haven 會再試一次。';
const READY_LABEL = '已整理好給伴侶閱讀';

function buildUnsavedPartnerMessage(persistedVisibility: JournalVisibility | null | undefined) {
  if (persistedVisibility === 'PARTNER_ORIGINAL') {
    return ORIGINAL_PARTNER_MESSAGE;
  }
  if (persistedVisibility === 'PARTNER_ANALYSIS_ONLY') {
    return LEGACY_ANALYSIS_PARTNER_MESSAGE;
  }
  return PRIVATE_PARTNER_MESSAGE;
}

export function buildJournalTranslationStatusPresentation({
  currentVisibility,
  hasCurrentJournalId = true,
  hasExplicitVisibilitySelection = false,
  isDraft = false,
  partnerTranslationReadyAt,
  partnerTranslationStatus,
  persistedVisibility,
}: BuildJournalTranslationStatusPresentationOptions): JournalTranslationStatusPresentation | null {
  if (currentVisibility !== 'PARTNER_TRANSLATED_ONLY') {
    return null;
  }

  const normalizedStatus = partnerTranslationStatus ?? 'NOT_REQUESTED';
  const unsavedVisibilitySwitch =
    hasExplicitVisibilitySelection && persistedVisibility !== 'PARTNER_TRANSLATED_ONLY';

  if (unsavedVisibilitySwitch) {
    return {
      state: 'not-ready',
      tone: 'neutral',
      label: '尚未準備好',
      shortLabel: '尚未準備',
      message: buildUnsavedPartnerMessage(persistedVisibility),
      readyAt: null,
    };
  }

  if (isDraft || !hasCurrentJournalId || normalizedStatus === 'NOT_REQUESTED') {
    return {
      state: 'not-ready',
      tone: 'neutral',
      label: '尚未準備好',
      shortLabel: '尚未準備',
      message: NOT_READY_MESSAGE,
      readyAt: null,
    };
  }

  if (normalizedStatus === 'PENDING') {
    return {
      state: 'pending',
      tone: 'progress',
      label: '正在整理給伴侶看的版本',
      shortLabel: '整理中',
      message: PENDING_MESSAGE,
      readyAt: null,
    };
  }

  if (normalizedStatus === 'READY') {
    return {
      state: 'ready',
      tone: 'success',
      label: READY_LABEL,
      shortLabel: '伴侶可讀',
      message: READY_MESSAGE,
      readyAt: partnerTranslationReadyAt ?? null,
    };
  }

  return {
    state: 'failed',
    tone: 'error',
    label: '暫時沒整理好',
    shortLabel: '暫未完成',
    message: FAILED_MESSAGE,
    readyAt: null,
  };
}
