// recipes service worker: keeps pages you've opened working without signal
// (the grocery store). Pages are network-first with a cached fallback; static
// assets are cache-first (their URLs are versioned). Private pages are never
// cached. __VERSION__ is the build, so each deploy starts a fresh cache.
const CACHE = "recipes-__VERSION__";

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/me") || url.pathname === "/metrics") return;

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(req).then((hit) =>
        hit || fetch(req).then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
      )
    );
    return;
  }

  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
        // Offline: this exact page, else (for the list) the last list you loaded.
        .catch(() =>
          caches.match(req).then(
            (hit) =>
              hit ||
              (url.pathname === "/list" ? caches.match(req, { ignoreSearch: true }) : undefined)
          )
        )
    );
  }
});
