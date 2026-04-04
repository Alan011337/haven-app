/**
 * P2-M: Date/number formatting — single place to avoid future refactor.
 * Uses Intl with zh-TW; can switch to next-intl useFormatter() when migrating components.
 */

const DEFAULT_LOCALE = 'zh-TW';

/**
 * Format a date for display. Prefer this over toLocaleDateString() ad-hoc.
 */
export function formatDate(
  value: Date | string | number,
  options: Intl.DateTimeFormatOptions = { dateStyle: 'medium' }
): string {
  const date = typeof value === 'object' && value instanceof Date ? value : new Date(value);
  return new Intl.DateTimeFormat(DEFAULT_LOCALE, options).format(date);
}

/**
 * Format a number (e.g. percentage, integer). Prefer this over toLocaleString() ad-hoc.
 */
export function formatNumber(
  value: number,
  options: Intl.NumberFormatOptions = {}
): string {
  return new Intl.NumberFormat(DEFAULT_LOCALE, options).format(value);
}

/**
 * Format a translation-ready timestamp as a calm zh-TW relative time cue.
 * Same day → "今天 14:32", yesterday → "昨天 14:32",
 * same year → "3/28 14:32", other → "2025/3/28 14:32".
 */
export function formatTranslationReadyAt(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const timeStr = new Intl.DateTimeFormat(DEFAULT_LOCALE, {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);

  const isToday =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();
  if (isToday) return `今天 ${timeStr}`;

  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday =
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate();
  if (isYesterday) return `昨天 ${timeStr}`;

  if (date.getFullYear() === now.getFullYear()) {
    return `${date.getMonth() + 1}/${date.getDate()} ${timeStr}`;
  }
  return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()} ${timeStr}`;
}

/** Percentage: 0.85 -> "85%" */
export function formatPercent(value: number, fractionDigits = 0): string {
  return new Intl.NumberFormat(DEFAULT_LOCALE, {
    style: 'percent',
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value);
}
