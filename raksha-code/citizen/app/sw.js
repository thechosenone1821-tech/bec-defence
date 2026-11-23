/* RAKSHA Citizen — offline shell cache */
const CACHE = "raksha-citizen-v0.4.0-voiceguard";
const ASSETS = ["./", "./index.html", "./styles.css", "./app.js", "./manifest.json"];
self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)));
  self.skipWaiting();
});
self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith("raksha-citizen-") && key !== CACHE).map(key => caches.delete(key))
  )).then(() => clients.claim()));
});
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/api/")) return;
  event.respondWith(caches.match(event.request).then(response => response || fetch(event.request)));
});
