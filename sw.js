// オフラインで遊べるようにファイルをキャッシュ。更新したら VERSION を上げる
const VERSION = "mk-v2";
const FILES = ["./", "index.html", "manifest.webmanifest", "js/sprites.js", "js/audio.js", "js/level.js", "js/game.js",
  "icons/icon-192.png", "icons/icon-512.png", "assets/overrides.json"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(VERSION).then((c) => c.addAll(FILES))); self.skipWaiting(); });
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSION).map((k) => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  // ネット優先・失敗したらキャッシュ（開発中でも更新が反映されやすい）
  e.respondWith(fetch(e.request).then((r) => {
    const copy = r.clone(); caches.open(VERSION).then((c) => c.put(e.request, copy)); return r;
  }).catch(() => caches.match(e.request)));
});
