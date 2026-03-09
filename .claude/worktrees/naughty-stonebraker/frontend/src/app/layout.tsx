// frontend/src/app/layout.tsx

import type { Metadata } from "next";
import "./globals.css";

// 引入我們剛做好的 AuthProvider
// 注意：這裡是引用 Provider (Context)，不是引用 Hook
import { AuthProvider } from '@/contexts/AuthContext'; 
import { ToastProvider } from '@/contexts/ToastContext';
import { ConfirmProvider } from '@/contexts/ConfirmContext';

export const metadata: Metadata = {
  title: "Haven",
  description: "Your AI Journal Companion",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-TW">
      <body
        className="antialiased bg-gray-50"
        suppressHydrationWarning={true}
      >
        {/* 👇 關鍵：把整個 App 包在 AuthProvider 裡面 */}
        <ConfirmProvider>
          <ToastProvider>
            <AuthProvider>
              {children}
            </AuthProvider>
          </ToastProvider>
        </ConfirmProvider>
      </body>
    </html>
  );
}
