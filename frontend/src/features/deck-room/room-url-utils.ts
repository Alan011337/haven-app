import { normalizeDeckCategory } from '@/lib/deck-category';
import type { DeckDepthFilter } from '@/lib/deck-depth-system';

const DECK_LIBRARY_FILTER_MODES = ['all', 'in_progress', 'not_started', 'completed'] as const;
const DECK_LIBRARY_SORT_MODES = ['recommended', 'progress_desc', 'progress_asc', 'title'] as const;

export const DEFAULT_PARTNER_NAME = '親愛的';

export const isDeckLibraryFilterMode = (value: string): boolean =>
  (DECK_LIBRARY_FILTER_MODES as readonly string[]).includes(value);

export const isDeckLibrarySortMode = (value: string): boolean =>
  (DECK_LIBRARY_SORT_MODES as readonly string[]).includes(value);

export const resolveDeckCategory = (category: string): string | null => normalizeDeckCategory(category);

export const buildDecksReturnUrl = (
  libraryFilter: string | null,
  librarySort: string | null,
  libraryDepth: DeckDepthFilter = null,
): string => {
  const nextParams = new URLSearchParams();
  if (libraryFilter && libraryFilter !== 'all') {
    nextParams.set('filter', libraryFilter);
  }
  if (librarySort && librarySort !== 'recommended') {
    nextParams.set('sort', librarySort);
  }
  if (libraryDepth) {
    nextParams.set('depth', String(libraryDepth));
  }
  const nextQuery = nextParams.toString();
  return nextQuery ? `/decks?${nextQuery}` : '/decks';
};

export const buildHistoryHref = (
  category: string | null,
  libraryFilter: string | null,
  librarySort: string | null,
  libraryDepth: DeckDepthFilter = null,
): string => {
  const nextParams = new URLSearchParams();
  if (category) {
    nextParams.set('category', category);
  }
  if (libraryFilter && libraryFilter !== 'all') {
    nextParams.set('library_filter', libraryFilter);
  }
  if (librarySort && librarySort !== 'recommended') {
    nextParams.set('library_sort', librarySort);
  }
  if (libraryDepth) {
    nextParams.set('library_depth', String(libraryDepth));
  }
  const nextQuery = nextParams.toString();
  return nextQuery ? `/decks/history?${nextQuery}` : '/decks/history';
};

export const resolvePartnerDisplayName = (
  partnerNickname?: string | null,
  partnerName?: string | null,
): string => partnerNickname || partnerName || DEFAULT_PARTNER_NAME;
