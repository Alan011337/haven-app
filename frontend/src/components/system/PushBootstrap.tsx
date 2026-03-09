'use client';

import { useEffect } from 'react';

import { useAuth } from '@/hooks/use-auth';
import { capturePosthogEvent } from '@/lib/posthog';
import {
  createBrowserPushSubscription,
  isPushSupported,
  pushSubscriptionToPayload,
  registerPushServiceWorker,
} from '@/lib/push';
import { upsertPushSubscription } from '@/services/api-client';
import { logClientError } from '@/lib/safe-error-log';

export default function PushBootstrap(): null {
  const { user } = useAuth();

  useEffect(() => {
    void registerPushServiceWorker();
  }, []);

  useEffect(() => {
    if (!user?.id) {
      return;
    }
    const enabledRaw = (process.env.NEXT_PUBLIC_WEBPUSH_ENABLED || '').trim().toLowerCase();
    const enabled = !enabledRaw || !['0', 'false', 'off', 'no'].includes(enabledRaw);
    if (!enabled) {
      return;
    }
    if (!isPushSupported()) {
      capturePosthogEvent('webpush_subscribed', {
        status: 'unsupported',
      });
      return;
    }
    const vapidPublicKey = (process.env.NEXT_PUBLIC_PUSH_VAPID_PUBLIC_KEY || '').trim();
    if (!vapidPublicKey) {
      return;
    }
    let cancelled = false;
    const bootstrap = async () => {
      try {
        const subscription = await createBrowserPushSubscription(vapidPublicKey);
        if (!subscription || cancelled) {
          return;
        }
        const payload = pushSubscriptionToPayload(subscription);
        await upsertPushSubscription(payload);
        capturePosthogEvent('webpush_subscribed', {
          status: 'ok',
        });
      } catch (error) {
        logClientError('push-bootstrap-upsert-failed', error);
        capturePosthogEvent('webpush_subscribed', {
          status: 'failed',
        });
      }
    };
    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  return null;
}
