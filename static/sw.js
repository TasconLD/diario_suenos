// BLOQUE: Service Worker PWA con Estrategia Offline Definitiva
const CACHE_NAME = 'entrenador-onirico-v7';

// Recursos locales y CDN seguros con CORS habilitado
const STATIC_ASSETS = [
  '/',
  '/offline',
  '/static/manifest.json',
  '/static/sw.js',
  '/static/js/main.js',
  '/static/icon-192.png',
  '/static/icon-512.png',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/chart.js'
];

// Instalar SW y precachear de forma tolerante a fallos
self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      // 1. Guardar recursos seguros
      for (const asset of STATIC_ASSETS) {
        try {
          await cache.add(asset);
        } catch (err) {
          console.warn(`No se pudo precachear el recurso: ${asset}`, err);
        }
      }
      
      // 2. Precachear Tailwind CDN explícitamente en modo no-cors para evitar bloqueo CORS
      try {
        const tailwindReq = new Request('https://cdn.tailwindcss.com', { mode: 'no-cors' });
        const response = await fetch(tailwindReq);
        await cache.put(tailwindReq, response);
      } catch (err) {
        console.warn('No se pudo precachear Tailwind CDN:', err);
      }
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

// Intercepción de Peticiones HTTP
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;

  // 1. Navegación HTML (Páginas): Network First -> Cache -> /offline
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
          
          const offlinePage = await caches.match('/offline');
          return offlinePage || new Response('Sin conexión a Internet', { status: 503, statusText: 'Offline' });
        })
    );
    return;
  }

  // 2. Recursos Estáticos: Cache First -> Network Fallback
  e.respondWith(
    caches.match(e.request).then((cachedResponse) => {
      if (cachedResponse) {
        fetch(e.request).then((networkResponse) => {
          if (networkResponse && (networkResponse.status === 200 || networkResponse.type === 'opaque')) {
            caches.open(CACHE_NAME).then((cache) => cache.put(e.request, networkResponse));
          }
        }).catch(() => {});
        return cachedResponse;
      }

      return fetch(e.request).then((networkResponse) => {
        if (networkResponse && (networkResponse.status === 200 || networkResponse.type === 'opaque')) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, responseClone));
        }
        return networkResponse;
      });
    })
  );
});

// Mensajería para SKIP_WAITING
self.addEventListener('message', (e) => {
  if (e.data && e.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});