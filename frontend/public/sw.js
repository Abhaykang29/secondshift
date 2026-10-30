/* SecondShift service worker: app shell only.
 *
 * Caches the static shell (index.html, built JS/CSS, icons, manifest)
 * cache-first under a versioned cache name. API calls (/api/*) are
 * NEVER intercepted for caching - they always go to the network, so
 * reports, videos and anything personal are never stored by the SW.
 * Bump SHELL_VERSION when the shell contract changes. */
const SHELL_VERSION = "v1";
const SHELL_CACHE = `secondshift-shell-${SHELL_VERSION}`;
const SHELL_FILES = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-512-maskable.png",
  "/icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(SHELL_FILES))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith("secondshift-") && key !== SHELL_CACHE)
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  // API, uploads, reports: network only, never cached.
  if (url.pathname.startsWith("/api/")) return;

  event.respondWith(
    caches.match(request, { ignoreSearch: true }).then((hit) => {
      if (hit) return hit;
      return fetch(request)
        .then((response) => {
          // Runtime-cache same-origin static assets (built /assets/*,
          // icons) so repeat visits are instant.
          if (
            response.ok &&
            (url.pathname.startsWith("/assets/") ||
              url.pathname.startsWith("/icons/") ||
              url.pathname === "/manifest.webmanifest")
          ) {
            const copy = response.clone();
            void caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => {
          // Offline navigation: fall back to the cached shell.
          if (request.mode === "navigate") return caches.match("/index.html");
          throw new Error("offline and not cached");
        });
    }),
  );
});
