'use client';

import dynamic from 'next/dynamic';
import Sidebar from '@/components/layout/Sidebar';
import Skeleton from '@/components/ui/Skeleton';

const NotificationsPageContent = dynamic(
  () => import('./NotificationsPageContent').then((m) => m.default),
  {
    loading: () => (
      <div className="max-w-4xl mx-auto space-y-6">
        <Skeleton className="h-32 w-full rounded-card" aria-label="載入中" />
        <Skeleton className="h-24 w-full rounded-card" aria-hidden />
        <Skeleton className="h-48 w-full rounded-card" aria-hidden />
      </div>
    ),
  },
);

export default function NotificationsPage() {
  return (
    <div className="flex min-h-screen bg-muted/40">
      <Sidebar />

      <main className="flex-1 pt-14 md:pt-0 md:ml-64 space-page w-full">
        <NotificationsPageContent />
      </main>
    </div>
  );
}
