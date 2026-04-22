import type {
  JournalTranslationStatus,
  JournalVisibility,
} from '@/types';

type JournalDeliverySaveState = 'draft' | 'dirty' | 'error' | 'saved' | 'saving';

export type JournalSharingDeliveryTone =
  | 'dirty'
  | 'original'
  | 'private'
  | 'translated-ready'
  | 'translated-waiting';

export type JournalSharingDeliveryLifecycleState =
  | 'current'
  | 'failed'
  | 'not-shared'
  | 'original'
  | 'refreshing'
  | 'stale-until-save'
  | 'waiting';

export interface JournalSharingDeliveryPresentation {
  boundaryLabel: string;
  lifecycleDescription: string;
  lifecycleLabel: string;
  lifecycleMetaLabel: string;
  lifecycleReadyAt: string | null;
  lifecycleState: JournalSharingDeliveryLifecycleState;
  nextSaveDescription: string;
  nextSaveLabel: string;
  partnerNowDescription: string;
  partnerNowLabel: string;
  tone: JournalSharingDeliveryTone;
}

interface BuildJournalSharingDeliveryPresentationOptions {
  attachmentsCount?: number;
  currentVisibility?: JournalVisibility | null;
  hasCurrentJournalId?: boolean;
  hasExplicitVisibilitySelection?: boolean;
  hasUnsavedChanges?: boolean;
  isDraft?: boolean;
  partnerTranslationReadyAt?: string | null;
  partnerTranslationStatus?: JournalTranslationStatus | null;
  persistedVisibility?: JournalVisibility | null;
  saveState?: JournalDeliverySaveState;
}

function describeAttachmentCount(attachmentsCount: number) {
  return attachmentsCount > 0 ? `，也包含 ${attachmentsCount} 張圖片` : '，目前沒有圖片';
}

function buildPartnerNowDescription({
  attachmentsCount,
  hasCurrentJournalId,
  hasUnsavedChanges,
  isDraft,
  partnerTranslationReadyAt,
  partnerTranslationStatus,
  persistedVisibility,
}: Required<
  Pick<
    BuildJournalSharingDeliveryPresentationOptions,
    'attachmentsCount' | 'hasCurrentJournalId' | 'hasUnsavedChanges' | 'isDraft'
  >
> &
  Pick<
    BuildJournalSharingDeliveryPresentationOptions,
    'partnerTranslationReadyAt' | 'partnerTranslationStatus' | 'persistedVisibility'
  >): Pick<JournalSharingDeliveryPresentation, 'partnerNowDescription' | 'partnerNowLabel' | 'tone'> {
  if (!hasCurrentJournalId || isDraft) {
    return {
      partnerNowLabel: '伴侶現在看不到這一頁',
      partnerNowDescription: '這一頁還是草稿或尚未正式保存，伴侶端不會出現它。',
      tone: 'private',
    };
  }

  if (persistedVisibility === 'PARTNER_ORIGINAL') {
    return {
      partnerNowLabel: '伴侶現在看到上一次保存的原文',
      partnerNowDescription: hasUnsavedChanges
        ? `你剛改的內容還沒送出；伴侶端仍停在上一次保存的原文${describeAttachmentCount(attachmentsCount)}。`
        : `伴侶端現在看到你保存下來的原文${describeAttachmentCount(attachmentsCount)}。`,
      tone: hasUnsavedChanges ? 'dirty' : 'original',
    };
  }

  if (persistedVisibility === 'PARTNER_TRANSLATED_ONLY') {
    if (partnerTranslationStatus === 'READY') {
      return {
        partnerNowLabel: '伴侶現在看到整理後版本',
        partnerNowDescription: hasUnsavedChanges
          ? '伴侶仍看到上一次已整理好的版本；你剛改的原文不會直接送出。'
          : partnerTranslationReadyAt
            ? '伴侶端現在看到的是 Haven 已整理好的版本，不是你的原文或圖片。'
            : '伴侶端現在看到的是 Haven 整理後的版本，不是你的原文或圖片。',
        tone: hasUnsavedChanges ? 'dirty' : 'translated-ready',
      };
    }

    return {
      partnerNowLabel: '伴侶現在看不到這一頁',
      partnerNowDescription:
        partnerTranslationStatus === 'PENDING'
          ? 'Haven 正在準備伴侶可讀的版本；整理完成前，伴侶端不會出現這篇內容。'
          : '這篇目前沒有可交付給伴侶的整理後版本，所以伴侶端不會出現它。',
      tone: 'translated-waiting',
    };
  }

  if (persistedVisibility === 'PARTNER_ANALYSIS_ONLY') {
    return {
      partnerNowLabel: '伴侶現在看到舊版分析資訊',
      partnerNowDescription: '這一頁沿用較早的分享設定；只要你不改分享模式，伴侶仍只看到分析資訊。',
      tone: hasUnsavedChanges ? 'dirty' : 'original',
    };
  }

  return {
    partnerNowLabel: '伴侶現在看不到這一頁',
    partnerNowDescription: '目前保存的分享邊界是私密，伴侶端不會出現這篇 Journal。',
    tone: 'private',
  };
}

function buildNextSaveDescription({
  attachmentsCount,
  currentVisibility,
  hasExplicitVisibilitySelection,
  hasUnsavedChanges,
  saveState,
}: Required<
  Pick<
    BuildJournalSharingDeliveryPresentationOptions,
    'attachmentsCount' | 'hasExplicitVisibilitySelection' | 'hasUnsavedChanges' | 'saveState'
  >
> &
  Pick<BuildJournalSharingDeliveryPresentationOptions, 'currentVisibility'>): Pick<
  JournalSharingDeliveryPresentation,
  'nextSaveDescription' | 'nextSaveLabel'
> {
  if (saveState === 'saving') {
    return {
      nextSaveLabel: '正在保存這次分享狀態',
      nextSaveDescription: 'Haven 正在把這次文字與分享邊界一起收好。',
    };
  }

  if (currentVisibility === 'PARTNER_ORIGINAL') {
    return {
      nextSaveLabel: '保存後伴侶會看到原文',
      nextSaveDescription: hasUnsavedChanges || hasExplicitVisibilitySelection
        ? `下一次保存後，伴侶會看到你保存下來的原文${describeAttachmentCount(attachmentsCount)}。`
        : '如果你之後修改並保存，伴侶會看到最新保存的原文與圖片。',
    };
  }

  if (currentVisibility === 'PARTNER_TRANSLATED_ONLY') {
    return {
      nextSaveLabel: '保存後會準備伴侶版本',
      nextSaveDescription: hasUnsavedChanges || hasExplicitVisibilitySelection
        ? '下一次保存後，Haven 會準備或刷新伴侶可讀的整理後版本；完成前，伴侶看不到新內容。'
        : '如果你之後修改並保存，Haven 會重新準備伴侶版本；原文與圖片仍不會直接送給伴侶。',
    };
  }

  if (currentVisibility === 'PARTNER_ANALYSIS_ONLY') {
    return {
      nextSaveLabel: '保存後維持舊版分析分享',
      nextSaveDescription: '只要你不改分享設定，這一頁仍沿用舊版分析分享，不會送出原文。',
    };
  }

  return {
    nextSaveLabel: '保存後伴侶仍看不到',
    nextSaveDescription: hasUnsavedChanges || hasExplicitVisibilitySelection
      ? '下一次保存後，這一頁會維持私密，伴侶端不會出現它。'
      : '目前是私密保存；如果你之後保存修改，伴侶仍不會看到這一頁。',
  };
}

function buildLifecycleDescription({
  attachmentsCount,
  currentVisibility,
  hasCurrentJournalId,
  hasExplicitVisibilitySelection,
  hasUnsavedChanges,
  isDraft,
  partnerTranslationReadyAt,
  partnerTranslationStatus,
  persistedVisibility,
  saveState,
}: Required<
  Pick<
    BuildJournalSharingDeliveryPresentationOptions,
    | 'attachmentsCount'
    | 'hasCurrentJournalId'
    | 'hasExplicitVisibilitySelection'
    | 'hasUnsavedChanges'
    | 'isDraft'
    | 'saveState'
  >
> &
  Pick<
    BuildJournalSharingDeliveryPresentationOptions,
    | 'currentVisibility'
    | 'partnerTranslationReadyAt'
    | 'partnerTranslationStatus'
    | 'persistedVisibility'
  >): Pick<
  JournalSharingDeliveryPresentation,
  | 'lifecycleDescription'
  | 'lifecycleLabel'
  | 'lifecycleMetaLabel'
  | 'lifecycleReadyAt'
  | 'lifecycleState'
> {
  if (!hasCurrentJournalId || isDraft) {
    return {
      lifecycleLabel: '尚未進入交付流程',
      lifecycleDescription: '這一頁還沒有正式保存；保存後才會依照分享設定處理伴侶可見狀態。',
      lifecycleMetaLabel: '目前沒有伴侶可見版本',
      lifecycleReadyAt: null,
      lifecycleState: 'not-shared',
    };
  }

  if (saveState === 'saving' && currentVisibility === 'PARTNER_TRANSLATED_ONLY') {
    return {
      lifecycleLabel: '正在刷新伴侶版本',
      lifecycleDescription:
        'Haven 正在保存原文並準備伴侶可讀版本；完成前，伴侶端仍以伺服器確認的狀態為準。',
      lifecycleMetaLabel: partnerTranslationReadyAt ? '上一次成功準備' : '尚未成功準備',
      lifecycleReadyAt: partnerTranslationReadyAt ?? null,
      lifecycleState: 'refreshing',
    };
  }

  if (
    currentVisibility === 'PARTNER_TRANSLATED_ONLY' &&
    hasExplicitVisibilitySelection &&
    persistedVisibility !== 'PARTNER_TRANSLATED_ONLY'
  ) {
    return {
      lifecycleLabel: '等待保存後開始準備',
      lifecycleDescription:
        '你已選擇整理後版本，但還沒保存；保存前，伴侶仍依照上一次保存的分享邊界。',
      lifecycleMetaLabel: '這次尚未產生伴侶版本',
      lifecycleReadyAt: null,
      lifecycleState: 'waiting',
    };
  }

  if (persistedVisibility === 'PARTNER_ORIGINAL') {
    return {
      lifecycleLabel: hasUnsavedChanges ? '原文分享等待保存' : '原文分享已保存',
      lifecycleDescription: hasUnsavedChanges
        ? '你正在編輯新內容；保存前，伴侶仍看到上一次保存的原文與圖片。'
        : `伴侶端現在看到的是已保存原文${describeAttachmentCount(attachmentsCount)}，不需要準備整理後版本。`,
      lifecycleMetaLabel: '原文分享不產生整理版',
      lifecycleReadyAt: null,
      lifecycleState: 'original',
    };
  }

  if (persistedVisibility === 'PARTNER_TRANSLATED_ONLY') {
    if (partnerTranslationStatus === 'READY') {
      return {
        lifecycleLabel: hasUnsavedChanges ? '上次整理版仍在使用中' : '整理後版本已交付',
        lifecycleDescription: hasUnsavedChanges
          ? '你正在編輯新內容；保存前，伴侶仍看到上次成功準備的整理後版本。'
          : '目前保存的內容已有伴侶可讀版本；伴侶現在看到這個已準備好的版本。',
        lifecycleMetaLabel: partnerTranslationReadyAt ? '上次成功準備' : '已有可交付版本，時間未記錄',
        lifecycleReadyAt: partnerTranslationReadyAt ?? null,
        lifecycleState: hasUnsavedChanges ? 'stale-until-save' : 'current',
      };
    }

    if (partnerTranslationStatus === 'PENDING') {
      return {
        lifecycleLabel: '正在等待伴侶版本',
        lifecycleDescription: 'Haven 正在準備伴侶可讀版本；完成前，伴侶端看不到這篇 Journal。',
        lifecycleMetaLabel: '尚未成功準備',
        lifecycleReadyAt: null,
        lifecycleState: 'waiting',
      };
    }

    if (partnerTranslationStatus === 'FAILED') {
      return {
        lifecycleLabel: '這次準備沒有完成',
        lifecycleDescription:
          '目前沒有可交付給伴侶的整理後版本；伴侶現在看不到這篇。下次保存會再試一次。',
        lifecycleMetaLabel: '沒有可用的最近交付時間',
        lifecycleReadyAt: null,
        lifecycleState: 'failed',
      };
    }

    return {
      lifecycleLabel: '尚未開始準備伴侶版本',
      lifecycleDescription: '保存為整理後版本後，Haven 才會開始準備伴侶可讀版本。',
      lifecycleMetaLabel: '尚未成功準備',
      lifecycleReadyAt: null,
      lifecycleState: 'waiting',
    };
  }

  return {
    lifecycleLabel: '不在交付中',
    lifecycleDescription: '目前保存的分享邊界不是伴侶可見版本；伴侶端不會出現這篇 Journal。',
    lifecycleMetaLabel: '伴侶現在看不到這一頁',
    lifecycleReadyAt: null,
    lifecycleState: 'not-shared',
  };
}

export function buildJournalSharingDeliveryPresentation({
  attachmentsCount = 0,
  currentVisibility = 'PRIVATE',
  hasCurrentJournalId = true,
  hasExplicitVisibilitySelection = false,
  hasUnsavedChanges = false,
  isDraft = false,
  partnerTranslationReadyAt = null,
  partnerTranslationStatus = 'NOT_REQUESTED',
  persistedVisibility = 'PRIVATE',
  saveState = 'draft',
}: BuildJournalSharingDeliveryPresentationOptions): JournalSharingDeliveryPresentation {
  const current = buildPartnerNowDescription({
    attachmentsCount,
    hasCurrentJournalId,
    hasUnsavedChanges,
    isDraft,
    partnerTranslationReadyAt,
    partnerTranslationStatus,
    persistedVisibility,
  });
  const next = buildNextSaveDescription({
    attachmentsCount,
    currentVisibility,
    hasExplicitVisibilitySelection,
    hasUnsavedChanges,
    saveState,
  });
  const lifecycle = buildLifecycleDescription({
    attachmentsCount,
    currentVisibility,
    hasCurrentJournalId,
    hasExplicitVisibilitySelection,
    hasUnsavedChanges,
    isDraft,
    partnerTranslationReadyAt,
    partnerTranslationStatus,
    persistedVisibility,
    saveState,
  });
  const translatedBoundary =
    currentVisibility === 'PARTNER_TRANSLATED_ONLY' ||
    persistedVisibility === 'PARTNER_TRANSLATED_ONLY';

  return {
    ...current,
    ...next,
    ...lifecycle,
    boundaryLabel: translatedBoundary
      ? '整理後版本只給伴侶閱讀；你仍只會看到自己的原文與準備狀態。'
      : '你可以隨時改分享邊界；未保存前，伴侶端仍依照上一次保存的設定。',
  };
}
