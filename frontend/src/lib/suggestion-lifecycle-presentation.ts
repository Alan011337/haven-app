export type SuggestionEmptyStatePresentation = {
  eyebrow: string;
  title: string;
  description: string;
  ctaLabel: string;
};

export type SuggestionInlineNoticePresentation = {
  title: string;
  description: string;
};

export type SuggestionMutationCopy = {
  acceptingLabel: string;
  dismissingLabel: string;
};

export function buildCompassEmptyStatePresentation(): SuggestionEmptyStatePresentation {
  return {
    eyebrow: 'Compass 建議更新',
    title: '目前沒有待審核的 Compass 建議。',
    description: 'Haven 只會在有足夠清楚、可安全引用的片段時提出建議。你可以稍後再讓 Haven 看看最近的片段。',
    ctaLabel: '讓 Haven 提一版',
  };
}

export function buildCompassInsufficientSignalPresentation(): SuggestionInlineNoticePresentation {
  return {
    title: '目前還沒有足夠清楚的共同訊號可以提出 Compass 建議。',
    description: '這不是錯誤；已保存的 Relationship Compass 沒有被改動。等更多片段被留下來後，再回來讓 Haven 試一次。',
  };
}

export function buildSharedFutureEmptyStatePresentation(): SuggestionEmptyStatePresentation {
  return {
    eyebrow: 'Future 建議更新',
    title: '目前沒有待審核的 Shared Future 建議。',
    description:
      'Haven 只會在有足夠清楚、且雙方可共同看見的片段時提出建議。你可以稍後再讓 Haven 看看最近的片段。',
    ctaLabel: '讓 Haven 提一版',
  };
}

export function buildSharedFutureInsufficientSignalPresentation(): SuggestionInlineNoticePresentation {
  return {
    title: '目前還沒有足夠清楚的共同訊號可以提出 Shared Future 建議。',
    description: 'Future 建議只會使用雙方可共同看見的片段；已保存的 Shared Future 沒有被改動。',
  };
}

export function buildHandledSuggestionNotice(): SuggestionInlineNoticePresentation {
  return {
    title: '這則建議已經處理過了。',
    description: '畫面已更新到最新狀態；已保存內容沒有被改動或重複寫入。',
  };
}

export function buildDismissedSuggestionNotice(): SuggestionInlineNoticePresentation {
  return {
    title: '這則建議已被略過。',
    description: '略過不會改動已保存內容；畫面已更新到最新狀態。',
  };
}

export function buildAcceptedSuggestionNotice(kind: 'compass' | 'future'): SuggestionInlineNoticePresentation {
  if (kind === 'compass') {
    return {
      title: '這則建議已接受並寫入 Compass。',
      description: '已接受的建議會出現在 Compass 歷史中；畫面已更新到最新狀態。',
    };
  }
  return {
    title: '這則提案已收進 Shared Future。',
    description: '它現在屬於已保存的共同未來；畫面已更新到最新狀態。',
  };
}

export function buildMutationCopy(kind: 'compass' | 'future'): SuggestionMutationCopy {
  return kind === 'compass'
    ? { acceptingLabel: '正在寫入 Compass…', dismissingLabel: '正在略過建議…' }
    : { acceptingLabel: '正在寫入 Future…', dismissingLabel: '正在略過建議…' };
}

export function isSharedFutureDuplicateTitle(
  proposedTitle: string,
  savedTitles: readonly string[],
): boolean {
  const normalized = proposedTitle.trim().toLowerCase();
  if (!normalized) return false;
  return savedTitles.some((t) => t.trim().toLowerCase() === normalized);
}

