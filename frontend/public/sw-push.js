self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
  let payload = {
    title: 'Haven',
    body: 'You have a new update.',
    url: '/',
  };
  try {
    if (event.data) {
      const parsed = event.data.json();
      payload = {
        title: parsed?.title || payload.title,
        body: parsed?.body || payload.body,
        url: parsed?.url || payload.url,
      };
    }
  } catch {
    // Ignore malformed payloads and fallback to default content.
  }

  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: '/favicon.ico',
      data: { url: payload.url },
      tag: 'haven-push',
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = event.notification?.data?.url || '/';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ('focus' in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl);
      }
      return Promise.resolve();
    }),
  );
});
