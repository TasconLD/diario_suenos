// BLOQUE: Service Worker PWA con Estrategia Offline y Notificaciones Push
const CACHE_NAME = 'entrenador-onirico-v6';
const STATIC_ASSETS = [
  '/',
  '/offline',
  '/static/manifest.json',
  '/static/sw.js',
  '/static/js/main.js',
  '/static/icon-192.png',
  '/static/icon-512.png',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/chart.js'
];
// Instalar SW y precachear recursos críticos
self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
});

// Activar SW y limpiar cachés obsoletas
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Intercepción de Peticiones HTTP (Estrategia Híbrida)
self.addEventListener('fetch', (e) => {
  // Ignorar peticiones que no sean GET (como POST o PUT)
  if (e.request.method !== 'GET') return;

  const requestUrl = new URL(e.request.url);

  // 1. Estrategia para Navegación de Páginas HTML: Network First -> Cache -> Offline Fallback
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then((response) => {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, responseClone));
          return response;
        })
        .catch(async () => {
          const cachedResponse = await caches.match(e.request);
          if (cachedResponse) return cachedResponse;
          
          // Si no está en caché y no hay red, muestra la página offline
          const offlinePage = await caches.match('/offline');
          return offlinePage || new Response('Sin conexión a Internet', { status: 503, statusText: 'Offline' });
        })
    );
    return;
  }

  // 2. Estrategia para Recursos Estáticos (CSS, JS, Fuentes, Imágenes): Cache First con revalidación
  e.respondWith(
    caches.match(e.request).then((cachedResponse) => {
      if (cachedResponse) {
        // Revalidar en segundo plano
        fetch(e.request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            caches.open(CACHE_NAME).then((cache) => cache.put(e.request, networkResponse));
          }
        }).catch(() => {});
        return cachedResponse;
      }

      return fetch(e.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, responseClone));
        }
        return networkResponse;
      });
    })
  );
});

// ==============================================================================
// MANEJO DE NOTIFICACIONES PUSH Y MENSAJES
// ==============================================================================

self.addEventListener('push', (e) => {
  if (!e.data) return;

  try {
    const data = e.data.json();
    const options = {
      body: data.body || 'Tienes un nuevo recordatorio.',
      icon: data.icon || '/static/icon-192.png',
      badge: data.badge || '/static/icon-192.png',
      vibrate: [200, 100, 200],
      tag: data.tag || 'notificacion-push',
      data: { url: data.url || '/' }
    };

    e.waitUntil(
      self.registration.showNotification(data.title || '👁️ Entrenador Onírico', options)
    );
  } catch (err) {
    console.error('Error procesando evento push:', err);
  }
});

self.addEventListener('message', (e) => {
  if (e.data && e.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  if (e.data && e.data.type === 'MOSTRAR_NOTIFICACION') {
    const { titulo, opciones } = e.data;
    e.waitUntil(
      self.registration.showNotification(titulo, opciones)
    );
  }
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const targetUrl = e.notification.data ? e.notification.data.url : '/';

  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ('focus' in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});