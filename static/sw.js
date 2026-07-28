const CACHE_NAME = 'entrenador-onirico-v5';
const assets = [
  '/',
  '/static/manifest.json',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/chart.js'
];

// Instalar el Service Worker
self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(assets);
    })
  );
});

// Activar el Service Worker y limpiar cachés viejas
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Peticiones Fetch
self.addEventListener('fetch', e => {
  e.respondWith(
    caches.match(e.request).then(cacheRes => {
      return cacheRes || fetch(e.request);
    })
  );
});

// ==============================================================================
// MANEJO DE NOTIFICACIONES Y REALITY CHECKS
// ==============================================================================

// Escuchar peticiones enviadas desde el cliente (postMessage)
self.addEventListener('message', e => {
  if (e.data && e.data.type === 'MOSTRAR_NOTIFICACION') {
    const { titulo, opciones } = e.data;
    e.waitUntil(
      self.registration.showNotification(titulo, opciones)
    );
  }
});

// Al hacer clic en una notificación enviada por el SW
self.addEventListener('notificationclick', e => {
  e.notification.close();

  // Enfocar la app si ya está abierta, o abrirla si está en segundo plano
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      for (const client of clientList) {
        if ('focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow('/');
      }
    })
  );
});