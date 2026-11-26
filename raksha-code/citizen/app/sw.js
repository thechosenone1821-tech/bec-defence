/* RAKSHA Citizen — offline shell cache.
 *
 * Phase 3 fix. This list had drifted from index.html: panic.js, family.js and
 * both capture modules were missing. Offline, that meant the panic button did
 * nothing at all — the safety feature silently became a dead control on the one
 * screen where it matters.
 *
 * The list below is now kept honest by two mechanisms:
 *   1. `tests/test_part1_phase3.py` derives the required asset set from
 *      index.html and fails if anything is missing here.
 *   2. `CACHE` carries a version; bump it on every asset change so an installed
 *      phone actually re-fetches instead of serving a stale shell forever.
 *
 * Never cache anything under /api/ — verdicts and reports are computed, never
 * stored on a shared cache.
 */

const CACHE = "raksha-citizen-v0.4.0";

const ASSETS = [
  "./",
  "./index.html",
  "./styles.css",
  "./manifest.json",
  "./maya-capture.js",
  "./maya-capture-worklet.js",
  "./panic.js",
  "./queue.js",
  "./family.js",
  "./app.js",
];

/* Install: fetch and cache the whole shell. If ANY asset 404s, the install must
 * fail loudly rather than silently caching a partial shell — a half-cached app
 * is how you get "the panic button does nothing, but only offline". */
self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE).then(async c => {
      await c.addAll(ASSETS);
      self.skipWaiting();
    })
  );
});

/* Activate: delete every previous cache version. Without this, a phone keeps a
 * v0.3 shell forever and the new files never arrive. */
self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);

  /* API responses are never cached: a stale verdict is worse than no verdict. */
  if (url.pathname.startsWith("/api/")) return;

  /* Only same-origin GETs are cacheable. */
  if (e.request.method !== "GET" || url.origin !== self.location.origin) return;

  /* Navigation requests fall back to the cached shell so the app opens with no
   * network at all. */
  if (e.request.mode === "navigate") {
    e.respondWith(
      caches.match("./index.html").then(r => r || fetch(e.request))
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request).catch(() =>
      /* Offline and not cached: fail explicitly so the caller can report it,
       * rather than resolving to an empty 200 that looks like success. */
      new Response("", {status: 504, statusText: "offline and not cached"})
    ))
  );
});
