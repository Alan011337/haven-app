# Haven Frontend i18n 架構 (P2-M)

## 目標

為全球化做準備，引入 next-intl，使文案可依語系切換。目前單一語系 zh-TW，日後擴充多語系與路由。

## 目前實作：next-intl 已啟用

- **next-intl** 已安裝並設定（App Router）。
- `app/layout.tsx`：`getMessages()` + `NextIntlClientProvider` 包住 children。
- `src/i18n/request.ts`：`getRequestConfig` 回傳 `locale: 'zh-TW'`、`messages`、`timeZone: 'Asia/Taipei'`。
- 元件內使用 `import { useTranslations } from 'next-intl';` 取得 `t('key')`；Server 使用 `getTranslations`。
- `src/lib/i18n.ts` 仍為過渡層，可逐步改為 next-intl 的 `useTranslations` / `getTranslations`。

## 檔案結構

```
frontend/
  messages/
    zh-TW.json       # 目前語系
  src/
    i18n/request.ts  # getRequestConfig
    app/layout.tsx   # NextIntlClientProvider + getMessages()
    lib/i18n.ts      # 過渡 t()；可遷移至 next-intl
  docs/
    i18n-setup.md    # 本說明
```

## 日後擴充

- 新增 `messages/en.json`；在 `request.ts` 依 pathname / cookie / Accept-Language 決定 `locale`。
- 可選 `[locale]` segment 或 cookie 切換語系；設定頁提供語系切換。

完整架構與擴充步驟見 **`docs/P2-M-i18n.md`**。

## 參考

- [next-intl — App Router](https://next-intl-docs.vercel.app/docs/getting-started/app-router)
