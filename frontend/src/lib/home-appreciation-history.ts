export const HOME_APPRECIATION_HISTORY_QUERY_KEY_PREFIX = [
  'home',
  'appreciations',
  'history',
] as const;

export function getHomeAppreciationWeekRange(referenceDate = new Date()): {
  from: string;
  to: string;
} {
  const day = referenceDate.getDay();
  const monday = new Date(referenceDate);
  monday.setDate(referenceDate.getDate() - (day === 0 ? 6 : day - 1));
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  return {
    from: monday.toISOString().slice(0, 10),
    to: sunday.toISOString().slice(0, 10),
  };
}

export function buildHomeAppreciationHistoryQueryKey(from: string, to: string) {
  return [...HOME_APPRECIATION_HISTORY_QUERY_KEY_PREFIX, from, to] as const;
}
