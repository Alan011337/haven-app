export type RelationshipSystemAnchorKey =
  | 'identity'
  | 'heart'
  | 'story'
  | 'future'
  | 'pending-review'
  | 'recent-evolution';

export type RelationshipSystemStatusTone = 'saved' | 'pending' | 'evolving';

export interface RelationshipSystemHomeInput {
  hasPartner: boolean;
  compassCueCount: number;
  careCueCount: number;
  repairAgreementCount: number;
  storyAnchorCount: number;
  wishlistCount: number;
  filledLayerCount: number;
  compassPendingCount: number;
  futurePendingCount: number;
  refinementPendingCount: number;
  repairPendingCount: number;
  compassHistoryCount: number;
  repairHistoryCount: number;
  lastActivityLabel?: string | null;
}

export interface RelationshipSystemStatusCardModel {
  key: RelationshipSystemStatusTone;
  eyebrow: string;
  title: string;
  value: string;
  description: string;
  /** When set (e.g. evolving card → `#evolution`), the whole card is a focusable in-page link. */
  href?: string;
}

export interface RelationshipSystemNavItemModel {
  key: RelationshipSystemAnchorKey;
  label: string;
  description: string;
  href: string;
  statusLabel: string;
}

export interface RelationshipSystemNextActionModel {
  label: string;
  description: string;
  href: string;
}

export interface RelationshipSystemHomeModel {
  savedDomainCount: number;
  pendingReviewCount: number;
  evolutionCount: number;
  statusCards: RelationshipSystemStatusCardModel[];
  navItems: RelationshipSystemNavItemModel[];
  nextAction: RelationshipSystemNextActionModel;
}

function safeCount(value: number) {
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
}

function countSavedDomains(input: RelationshipSystemHomeInput) {
  if (!input.hasPartner) return 0;
  const identitySaved = safeCount(input.compassCueCount) > 0;
  const heartSaved = safeCount(input.careCueCount) > 0 || safeCount(input.repairAgreementCount) > 0;
  const storySaved = safeCount(input.storyAnchorCount) > 0;
  const futureSaved = safeCount(input.wishlistCount) > 0;
  return [identitySaved, heartSaved, storySaved, futureSaved].filter(Boolean).length;
}

function formatCount(value: number, unit: string) {
  const count = safeCount(value);
  return count > 0 ? `${count} ${unit}` : '還在累積';
}

function buildPendingHref(input: RelationshipSystemHomeInput) {
  if (safeCount(input.compassPendingCount) > 0) return '#identity';
  if (safeCount(input.repairPendingCount) > 0) return '#heart';
  if (safeCount(input.futurePendingCount) + safeCount(input.refinementPendingCount) > 0) return '#future';
  return '#identity';
}

function buildHistoryHref(input: RelationshipSystemHomeInput, evolutionCount: number) {
  if (evolutionCount > 0) return '#evolution';
  return '#identity';
}

function domainStatus({
  saved,
  pending,
  evolving,
}: {
  saved: boolean;
  pending?: boolean;
  evolving?: boolean;
}) {
  if (pending) return '待審核';
  if (evolving) return '最近有更新';
  if (saved) return '已保存';
  return '還在累積';
}

export function buildRelationshipSystemHomeModel(
  input: RelationshipSystemHomeInput,
): RelationshipSystemHomeModel {
  const compassPendingCount = safeCount(input.compassPendingCount);
  const futurePendingCount = safeCount(input.futurePendingCount);
  const refinementPendingCount = safeCount(input.refinementPendingCount);
  const repairPendingCount = safeCount(input.repairPendingCount);
  const pendingReviewCount =
    input.hasPartner
      ? compassPendingCount + futurePendingCount + refinementPendingCount + repairPendingCount
      : 0;
  const compassHistoryCount = safeCount(input.compassHistoryCount);
  const repairHistoryCount = safeCount(input.repairHistoryCount);
  const evolutionCount = input.hasPartner ? compassHistoryCount + repairHistoryCount : 0;
  const savedDomainCount = countSavedDomains(input);
  const pendingHref = buildPendingHref(input);
  const historyHref = buildHistoryHref(input, evolutionCount);

  const statusCards: RelationshipSystemStatusCardModel[] = [
    {
      key: 'saved',
      eyebrow: '已保存的共同真相',
      title: input.hasPartner ? `${savedDomainCount}/4 個系統域已有內容` : '等待雙向伴侶連結',
      value: input.hasPartner ? `${savedDomainCount}/4` : '待完成',
      description: input.hasPartner
        ? '這些是你們已經寫下或接受、可以一起回看的關係知識。'
        : '完成配對後，已保存內容才會成為共同真相。',
    },
    {
      key: 'pending',
      eyebrow: 'Haven 建議 · 待審核',
      title: pendingReviewCount > 0 ? `${pendingReviewCount} 則更新等你決定` : '目前沒有待審核的建議',
      value: pendingReviewCount > 0 ? `${pendingReviewCount} 則` : '0 則',
      description: pendingReviewCount > 0
        ? '建議只在你接受後，才會寫入共同真相。'
        : '已保存內容沒有被改動；Haven 會在訊號足夠清楚時再提出建議。',
    },
    {
      key: 'evolving',
      eyebrow: '如何改變',
      title: evolutionCount > 0 ? `${evolutionCount} 次最近修訂脈絡` : '關係知識還在累積',
      value: evolutionCount > 0 ? `${evolutionCount} 次` : '還在累積',
      description: input.lastActivityLabel
        ? `最近活動：${input.lastActivityLabel}。你可以回看哪些內容是手動更新、哪些來自已接受建議。`
        : '當 Compass 或 Repair Agreements 被更新，這裡會保留它們如何改變。',
      ...(evolutionCount > 0 ? { href: '#evolution' as const } : {}),
    },
  ];

  const navItems: RelationshipSystemNavItemModel[] = [
    {
      key: 'identity',
      label: 'Identity',
      description: '我們現在是誰',
      href: '#identity',
      statusLabel: domainStatus({
        saved: input.hasPartner && safeCount(input.compassCueCount) > 0,
        pending: compassPendingCount > 0,
        evolving: compassHistoryCount > 0,
      }),
    },
    {
      key: 'heart',
      label: 'Heart',
      description: '我們如何照顧彼此',
      href: '#heart',
      statusLabel: domainStatus({
        saved: input.hasPartner && (safeCount(input.careCueCount) > 0 || safeCount(input.repairAgreementCount) > 0),
        pending: repairPendingCount > 0,
        evolving: repairHistoryCount > 0,
      }),
    },
    {
      key: 'story',
      label: 'Story',
      description: '我們選擇記得什麼',
      href: '#story',
      statusLabel: domainStatus({
        saved: input.hasPartner && safeCount(input.storyAnchorCount) > 0,
      }),
    },
    {
      key: 'future',
      label: 'Future',
      description: '我們一起往哪裡走',
      href: '#future',
      statusLabel: domainStatus({
        saved: input.hasPartner && safeCount(input.wishlistCount) > 0,
        pending: futurePendingCount + refinementPendingCount > 0,
      }),
    },
  ];

  if (pendingReviewCount > 0) {
    navItems.push({
      key: 'pending-review',
      label: '待審核',
      description: 'Haven 建議更新',
      href: pendingHref,
      statusLabel: `${pendingReviewCount} 則`,
    });
  }

  if (evolutionCount > 0) {
    navItems.push({
      key: 'recent-evolution',
      label: '最近演進',
      description: '共同真相如何改變',
      href: historyHref,
      statusLabel: `${evolutionCount} 次`,
    });
  }

  let nextAction: RelationshipSystemNextActionModel;
  if (!input.hasPartner) {
    nextAction = {
      label: '先完成伴侶連結',
      description: '完成雙向配對後，這裡才會成為真正的共同關係系統。',
      href: '/settings#settings-relationship',
    };
  } else if (pendingReviewCount > 0) {
    nextAction = {
      label: '審核待處理更新',
      description: '先確認哪些 Haven 建議值得寫入共同真相。',
      href: pendingHref,
    };
  } else if (safeCount(input.compassCueCount) < 3) {
    nextAction = {
      label: '補完整 Relationship Compass',
      description: '先把 Identity、Story、Future 的三句共同理解留下來。',
      href: '#identity',
    };
  } else if (safeCount(input.repairAgreementCount) < 3) {
    nextAction = {
      label: '補完整 Repair Agreements',
      description: '讓 Heart 不只知道怎麼照顧，也知道怎麼回到修復。',
      href: '#heart',
    };
  } else if (safeCount(input.wishlistCount) === 0) {
    nextAction = {
      label: '留下第一個 Future 片段',
      description: '把你們想一起靠近的生活畫面放進 Shared Future。',
      href: '#future',
    };
  } else {
    nextAction = {
      label: evolutionCount > 0 ? '回看最近演進' : '回看關係地圖',
      description: evolutionCount > 0
        ? '看看共同真相最近如何被手動更新或由已接受建議帶動。'
        : '從四個系統域回看你們已經整理好的關係知識。',
      href: evolutionCount > 0 ? historyHref : '#identity',
    };
  }

  return {
    savedDomainCount,
    pendingReviewCount,
    evolutionCount,
    statusCards,
    navItems,
    nextAction,
  };
}

export function formatRelationshipSystemCount(value: number, unit: string) {
  return formatCount(value, unit);
}
