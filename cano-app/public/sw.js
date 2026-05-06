self.addEventListener('push', (event) => {
  if (!event.data) return;

  let data = {};
  try {
    data = event.data.json();
  } catch {
    data = { title: 'CANO4', body: event.data.text() };
  }

  const title   = data.title ?? 'CANO4';
  const options = {
    body: data.body ?? '',
    icon: '/icon.png',
    badge: '/icon.png',
    data: data,
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow('/'));
});
