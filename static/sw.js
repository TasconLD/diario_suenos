// BLOQUE: Service Worker PWA con Precaché Completo de Rutas
const CACHE_NAME = 'entrenador-onirico-v8';

// Todas las rutas de la aplicación para precachear
const STATIC_ASSETS = [
  '/',
  '/offline',
  '/login',
  '/registro',
  '/dashboard',
  '/diario',
  '/objetivos',
  '/estadisticas',
  '/perfil',
  '/suenos',
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
      // 1. Guardar recursos locales y librerías seguras
      for (const asset of STATIC_ASSETS) {
        try {
          await cache.add(asset);
        } catch (err) {
          console.warn(`[SW] No se pudo precachear la ruta: ${asset}`, err);
        }
      }
      
      // 2. Precachear Tailwind CDN en modo no-cors (evita bloqueos CORS)
      try {
        const tailwindReq = new Request('https://cdn.tailwindcss.com', { mode: 'no-cors' });
        const response = await fetch(tailwindReq);
        await cache.put(tailwindReq, response);
      } catch (err) {
        console.warn('[SW] No se pudo precachear Tailwind CDN:', err);
      }
    })
  );
});

// Activar SW y limpiar cachés obsoletas de versiones previas
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

// Intercepción Inteligente de Peticiones HTTP
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;

  // 1. NAVEGACIÓN DE PÁGINAS HTML: Network First -> Cache -> /offline Fallback
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then((response) => {
          // Si hay internet, guarda/actualiza una copia fresca en la caché
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, responseClone));
          return response;
        })
        .catch(async () => {
          // Si NO hay internet, intenta servir la vista desde la caché
          const cachedResponse = await caches.match(e.request);
          if (cachedResponse) return cachedResponse;
          
          // Si la vista específica no está en caché, muestra la pantalla /offline dedicada
          const offlinePage = await caches.match('/offline');
          if (offlinePage) return offlinePage;

          // Respuesta de emergencia si todo falla (Evita el dinosaurio)
          return new Response('<h1>Sin conexión a Internet</h1>', {
            headers: { 'Content-Type': 'text/html; charset=utf-8' }
          });
        })
    );
    return;
  }

  // 2. RECURSOS ESTÁTICOS (CSS, JS, IMÁGENES): Cache First -> Network Fallback
  e.respondWith(
    caches.match(e.request).then((cachedResponse) => {
      if (cachedResponse) {
        // Revalidar en segundo plano si hay red
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

// Escuchador para la actualización inmediata
self.addEventListener('message', (e) => {
  if (e.data && e.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});