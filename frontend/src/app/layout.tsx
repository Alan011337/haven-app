// frontend/src/app/layout.tsx

import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import "./globals.css";
import { NextIntlClientProvider } from 'next-intl';

import { AuthProvider } from '@/contexts/AuthContext';
import AuthGuard from '@/components/system/AuthGuard';
import { QueryProvider } from '@/providers/QueryProvider';
import PushBootstrap from '@/components/system/PushBootstrap';
import PosthogBootstrap from '@/components/system/PosthogBootstrap';
import OfflineReplayBootstrap from '@/components/system/OfflineReplayBootstrap';
import OfflineQueueBanner from '@/components/system/OfflineQueueBanner';
import DegradationBanner from '@/components/system/DegradationBanner';
import RealtimeFallbackBanner from '@/components/system/RealtimeFallbackBanner';
import DynamicBackgroundWrapper from '@/components/system/DynamicBackgroundWrapper';
import { Toaster } from 'sonner';
import ConfirmModal from '@/components/system/ConfirmModal';
import { getMessages } from 'next-intl/server';

export const metadata: Metadata = {
  title: "Haven",
  description: "Your AI Journal Companion",
  manifest: "/manifest.json",
};

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
  weight: ['400', '500', '600'],
});

const playfairDisplay = Playfair_Display({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-art',
  weight: ['400', '500', '600', '700'],
});

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const messages = await getMessages();
  return (
    <html lang="zh-TW">
      <body
        className={`${inter.variable} ${playfairDisplay.variable} antialiased bg-background font-sans`}
        suppressHydrationWarning={true}
      >
        <NextIntlClientProvider messages={messages}>
          {/* 👇 關鍵：把整個 App 包在 AuthProvider 裡面 */}
          <AuthProvider>
            <AuthGuard>
              <QueryProvider>
                <DynamicBackgroundWrapper>
                  <DegradationBanner />
                  <RealtimeFallbackBanner />
                  <PosthogBootstrap />
                  <OfflineQueueBanner />
                  <PushBootstrap />
                  <OfflineReplayBootstrap />
                  <Toaster richColors position="top-right" />
                  <ConfirmModal />
                  {children}
                </DynamicBackgroundWrapper>
              </QueryProvider>
            </AuthGuard>
          </AuthProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
