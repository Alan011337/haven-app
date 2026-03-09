'use client';

import { useEffect } from 'react';
import { logClientError } from '@/lib/safe-error-log';

/**
 * Next.js App Router global-error boundary.
 *
 * This catches errors thrown in the root layout itself (where error.tsx
 * cannot help because it lives *inside* the layout).  Because the layout
 * is broken, we must provide our own <html>/<body> wrapper and avoid
 * importing any project component that might depend on the layout
 * providers (AuthContext, ToastContext, etc.).
 *
 * Intentionally minimal: inline styles + raw <a> to guarantee rendering
 * even when Tailwind or the CSS pipeline is unavailable.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    logClientError('Haven GlobalError', error);
  }, [error]);

  return (
    <html lang="zh-Hant">
      <body
        style={{
          margin: 0,
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          backgroundColor: '#f9fafb',
          padding: '1rem',
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: '28rem',
            borderRadius: '1rem',
            border: '1px solid #e5e7eb',
            backgroundColor: '#ffffff',
            padding: '2rem',
            textAlign: 'center',
            boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          }}
        >
          <div
            style={{
              margin: '0 auto 1rem',
              width: '3rem',
              height: '3rem',
              borderRadius: '50%',
              backgroundColor: '#fee2e2',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#dc2626',
              fontSize: '1.5rem',
            }}
          >
            !
          </div>

          <h2
            style={{
              marginBottom: '0.5rem',
              fontSize: '1.125rem',
              fontWeight: 700,
              color: '#111827',
            }}
          >
            應用程式發生嚴重錯誤
          </h2>

          <p
            style={{
              marginBottom: '1.5rem',
              fontSize: '0.875rem',
              color: '#6b7280',
            }}
          >
            系統遇到無法恢復的錯誤，請重試或重新載入頁面。
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <button
              type="button"
              onClick={reset}
              aria-label="重試載入應用程式"
              style={{
                width: '100%',
                borderRadius: '0.75rem',
                backgroundColor: '#7c3aed',
                padding: '0.625rem 1rem',
                fontSize: '0.875rem',
                fontWeight: 700,
                color: '#ffffff',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              重試
            </button>

            {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- global-error replaces root layout; <Link> requires router context which is unavailable */}
            <a
              href="/"
              style={{
                display: 'block',
                width: '100%',
                borderRadius: '0.75rem',
                border: '1px solid #e5e7eb',
                padding: '0.625rem 1rem',
                fontSize: '0.875rem',
                fontWeight: 500,
                color: '#4b5563',
                textDecoration: 'none',
                boxSizing: 'border-box',
                textAlign: 'center',
              }}
            >
              回到首頁
            </a>
          </div>
        </div>
      </body>
    </html>
  );
}
