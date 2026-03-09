import { apiDelete, apiGet, apiPost } from '@/services/api-transport';
import type {
  NotificationEventItem,
  NotificationFilters,
  NotificationMarkReadResult,
  NotificationRetryResult,
  NotificationStats,
  PushDispatchDryRunResult,
  PushSubscriptionDeleteResult,
  PushSubscriptionItem,
  PushSubscriptionPayload,
  PushSubscriptionUpsertResult,
} from '@/services/api-client.types';

export const markNotificationsRead = async (
  actionType?: 'journal' | 'card'
): Promise<NotificationMarkReadResult> => {
  return apiPost<NotificationMarkReadResult>('/users/notifications/mark-read', null, {
    params: actionType ? { action_type: actionType } : undefined,
  });
};

export const fetchNotifications = async (params?: {
  limit?: number;
  offset?: number;
} & NotificationFilters): Promise<NotificationEventItem[]> => {
  return apiGet<NotificationEventItem[]>('/users/notifications', { params });
};

export const fetchNotificationStats = async (
  params?: {
    window_days?: number;
  } & NotificationFilters
): Promise<NotificationStats> => {
  return apiGet<NotificationStats>('/users/notifications/stats', {
    params,
  });
};

export const markNotificationRead = async (
  notificationId: string
): Promise<NotificationMarkReadResult> => {
  return apiPost<NotificationMarkReadResult>(`/users/notifications/${notificationId}/read`);
};

export const retryNotification = async (
  notificationId: string
): Promise<NotificationRetryResult> => {
  return apiPost<NotificationRetryResult>(`/users/notifications/${notificationId}/retry`);
};

export const listPushSubscriptions = async (
  includeInactive = true
): Promise<PushSubscriptionItem[]> => {
  return apiGet<PushSubscriptionItem[]>('/users/push-subscriptions', {
    params: { include_inactive: includeInactive },
  });
};

export const upsertPushSubscription = async (
  payload: PushSubscriptionPayload
): Promise<PushSubscriptionUpsertResult> => {
  return apiPost<PushSubscriptionUpsertResult>('/users/push-subscriptions', payload);
};

export const deletePushSubscription = async (
  subscriptionId: string
): Promise<PushSubscriptionDeleteResult> => {
  return apiDelete<PushSubscriptionDeleteResult>(`/users/push-subscriptions/${subscriptionId}`);
};

export const runPushDispatchDryRun = async (
  sampleSize?: number
): Promise<PushDispatchDryRunResult> => {
  const payload = sampleSize ? { sample_size: sampleSize } : {};
  return apiPost<PushDispatchDryRunResult>('/users/push-subscriptions/dry-run', payload);
};
