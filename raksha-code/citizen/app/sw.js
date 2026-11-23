/* RAKSHA Citizen — offline shell cache */
const CACHE = "raksha-citizen-v0.3.0";
const ASSETS = ["./", "./index.html", "./styles.css", "./app.js", "./manifest.json"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});
self.addEventListener("activate", e => e.waitUntil(clients.claim()));
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api/")) return; /* never cache verdicts or reports */
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
