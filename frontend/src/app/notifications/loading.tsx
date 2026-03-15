import { NotificationsShell } from '@/app/notifications/NotificationsPrimitives';
import { NotificationsSkeleton } from '@/app/notifications/NotificationsSkeleton';

export default function NotificationsLoading() {
  return (
    <NotificationsShell>
      <NotificationsSkeleton />
    </NotificationsShell>
  );
}
