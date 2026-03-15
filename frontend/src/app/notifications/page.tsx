import dynamic from 'next/dynamic';
import { NotificationsShell } from '@/app/notifications/NotificationsPrimitives';
import { NotificationsSkeleton } from '@/app/notifications/NotificationsSkeleton';

const NotificationsPageContent = dynamic(
  () => import('./NotificationsPageContent').then((module) => module.default),
  {
    loading: () => <NotificationsSkeleton />,
  },
);

export default function NotificationsPage() {
  return (
    <NotificationsShell>
      <NotificationsPageContent />
    </NotificationsShell>
  );
}
