# P2-M. 前端 i18n 框架架構

**目標**：引入 next-intl 為全球化做準備，單一語系先行，日後擴充多語系與路由。

---

## 採用框架：next-intl (App Router)

- **next-i18next** 適用 Pages Router；Haven 使用 App Router，採用 **next-intl**。
- 安裝：`npm install next-intl`
- 設定：`next.config.ts` 使用 `createNextIntlPlugin()`；`src/i18n/request.ts` 提供 `getRequestConfig`。

---

## 目前實作（單一語系 zh-TW）

| 項目 | 說明 |
|------|------|
| **語系** | 固定 `zh-TW`（`src/i18n/request.ts` 的 `DEFAULT_LOCALE`）。 |
| **訊息** | `messages/zh-TW.json`；`layout.tsx` 以 `getMessages()` 取得並傳入 `NextIntlClientProvider`。 |
| **時區** | `timeZone: 'Asia/Taipei'`（`i18n/request.ts`）。 |
| **元件** | `import { useTranslations } from 'next-intl';` 取得 `t('key')`；或 `import { getTranslations } from 'next-intl/server';` 於 Server Component。 |
| **過渡** | `src/lib/i18n.ts` 仍提供簡單 `t(key)`，可逐步改為 `useTranslations` / `getTranslations`。 |

---

## 檔案結構

```
frontend/
  messages/
    zh-TW.json           # 目前語系
  src/
    i18n/
      request.ts        # getRequestConfig，locale + messages + timeZone
    app/
      layout.tsx        # NextIntlClientProvider + getMessages()
    lib/
      i18n.ts           # 過渡 t()；可遷移至 next-intl
  docs/
    i18n-setup.md       # 本說明（前端目錄）
```

---

## 日後擴充（多語系與路由）

1. **新增語系**：建立 `messages/en.json` 等；在 `request.ts` 依 pathname / cookie / Accept-Language 決定 `locale`。
2. **路由**：可選 `[locale]` segment（`app/[locale]/layout.tsx`）或 cookie 切換語系（無 path 前綴）。
3. **語系切換**：設定頁或 header 提供切換，寫入 cookie 或導向 `/{locale}/...`。
4. **參考**：[next-intl — App Router](https://next-intl-docs.vercel.app/docs/getting-started/app-router)
