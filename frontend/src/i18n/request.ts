/**
 * P2-M: next-intl request config. Single locale (zh-TW) for now.
 * Locale routing: see docs/P2-M-i18n.md. Future: [locale] segment or cookie.
 */

import { getRequestConfig } from 'next-intl/server';

const DEFAULT_LOCALE = 'zh-TW';

export default getRequestConfig(async () => {
  const locale = DEFAULT_LOCALE;
  const messages = (await import(`../../messages/${locale}.json`)).default as Record<string, unknown>;
  return {
    locale,
    messages,
    timeZone: 'Asia/Taipei',
  };
});
