'use client';

import { logClientError } from '@/lib/safe-error-log';

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i += 1) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

function toApplicationServerKey(base64String: string): ArrayBuffer {
  const bytes = urlBase64ToUint8Array(base64String);
  const copy = Uint8Array.from(bytes);
  return copy.buffer as ArrayBuffer;
}

export function isPushSupported(): boolean {
  return typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window;
}

export async function registerPushServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!isPushSupported()) {
    return null;
  }
  try {
    return await navigator.serviceWorker.register('/sw-push.js', { scope: '/' });
  } catch (error) {
    logClientError('push-register-service-worker-failed', error);
    return null;
  }
}

export async function requestPushPermission(): Promise<NotificationPermission> {
  if (typeof window === 'undefined' || !('Notification' in window)) {
    return 'denied';
  }
  if (Notification.permission !== 'default') {
    return Notification.permission;
  }
  try {
    return await Notification.requestPermission();
  } catch (error) {
    logClientError('push-request-permission-failed', error);
    return 'denied';
  }
}

export async function createBrowserPushSubscription(
  vapidPublicKey: string,
): Promise<PushSubscription | null> {
  if (!vapidPublicKey?.trim()) {
    return null;
  }
  const registration = await registerPushServiceWorker();
  if (!registration) {
    return null;
  }
  const permission = await requestPushPermission();
  if (permission !== 'granted') {
    return null;
  }
  try {
    const existing = await registration.pushManager.getSubscription();
    if (existing) {
      return existing;
    }
    return await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: toApplicationServerKey(vapidPublicKey),
    });
  } catch (error) {
    logClientError('push-create-subscription-failed', error);
    return null;
  }
}

function uint8ArrayToBase64(bytes: Uint8Array): string {
  let binary = '';
  bytes.forEach((b) => {
    binary += String.fromCharCode(b);
  });
  return window.btoa(binary);
}

export function pushSubscriptionToPayload(subscription: PushSubscription): {
  endpoint: string;
  keys: { p256dh: string; auth: string };
  expiration_time?: string | null;
  user_agent?: string;
} {
  const p256dh = subscription.getKey('p256dh');
  const auth = subscription.getKey('auth');
  if (!p256dh || !auth) {
    throw new Error('push_subscription_keys_missing');
  }
  return {
    endpoint: subscription.endpoint,
    keys: {
      p256dh: uint8ArrayToBase64(new Uint8Array(p256dh)),
      auth: uint8ArrayToBase64(new Uint8Array(auth)),
    },
    expiration_time:
      typeof subscription.expirationTime === 'number'
        ? new Date(subscription.expirationTime).toISOString()
        : null,
    user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
  };
}
