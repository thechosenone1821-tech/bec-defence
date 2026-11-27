/* RAKSHA Citizen — offline shell cache.
 *
 * The asset list is derived from index.html by the Python/Node tests. Bump the
 * cache version whenever that list changes so installed phones re-fetch.
 * Never cache API responses: a stale verdict or audit is worse than none.
 */

const CACHE = "raksha-citizen-v0.4.2";

const ASSETS = [
  "./",
  "./index.html",
  "./styles.css",
  "./manifest.json",
  "./panic.js",
  "./send-state.js",
  "./queue.js",
  "./family.js",
  "./app.js",
  "./phase4.js",
];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE).then(async c => {
      await c.addAll(ASSETS);
      self.skipWaiting();
    })
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE).map(k => caches.delete(k))
      ))
      .then(() => {
        var uncontrolled = typeof self.clients.matchAll === "function"
          ? self.clients.matchAll({ type: "window" })
              .then(clients => clients.some(c => !c.controller))
              .catch(() => false)
          : false;
        return Promise.resolve(uncontrolled).then(anyUncontrolled => {
          if (anyUncontrolled) return self.clients.claim();
          return undefined;
        });
      })
  );
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);

  /* Recovery link: bypass the offline shell entirely when ?nosw=1 is used. */
  if (url.searchParams.has("nosw")) return;

  /* MessageGuard, reporting and VIGIL API responses are never cached. */
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/vigil/api/")) return;

  if (e.request.method !== "GET" || url.origin !== self.location.origin) return;

  if (e.request.mode === "navigate") {
    e.respondWith(
      caches.match("./index.html").then(r => r || fetch(e.request))
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request).catch(() =>
      new Response("", {status: 504, statusText: "offline and not cached"})
    ))
  );
});
