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

/** Percentage: 0.85 -> "85%" */
export function formatPercent(value: number, fractionDigits = 0): string {
  return new Intl.NumberFormat(DEFAULT_LOCALE, {
    style: 'percent',
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value);
}
