/**
 * P2-M: i18n 過渡層。目前固定 zh-TW，從 messages/zh-TW.json 讀取。
 * 日後可替換為 next-intl 的 useTranslations()。
 */

import zhTW from '../../messages/zh-TW.json';

type Messages = Record<string, unknown>;

const cached: Messages = zhTW as Messages;

/**
 * 取得巢狀 key 的值，例如 get(nested, 'common.loading') => nested.common.loading
 */
function get(obj: unknown, path: string): string | undefined {
  const parts = path.split('.');
  let current: unknown = obj;
  for (const p of parts) {
    if (current == null || typeof current !== 'object') return undefined;
    current = (current as Record<string, unknown>)[p];
  }
  return typeof current === 'string' ? current : undefined;
}

const DEFAULT_LOCALE = 'zh-TW';

/**
 * 同步取得翻譯。key 格式為 'common.loading'。
 * 若找不到，回傳 key 本身。
 */
export function t(key: string): string {
  return get(cached, key) ?? key;
}

/**
 * 供 next-intl 遷移時使用：回傳目前語系。
 */
export function getLocale(): string {
  return DEFAULT_LOCALE;
}
