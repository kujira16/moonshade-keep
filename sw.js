// オフラインで遊べるようにファイルをキャッシュ。更新したら VERSION を上げる
const VERSION = "mk-v4-polished-sprites-d504a1a46864";
const FILES = ["./", "index.html", "manifest.webmanifest", "js/sprites.js", "js/audio.js", "js/level.js", "js/game.js",
  "icons/icon-192.png", "icons/icon-512.png", "assets/overrides.json",
  './assets/player_idle.png',
  './assets/player_walk.png',
  './assets/player_jump.png',
  './assets/player_attack.png',
  './assets/player_attack_air.png',
  './assets/bat.png',
  './assets/bat_hang.png',
  './assets/skeleton.png',
  './assets/ghost.png',
  './assets/boss_skull.png',
  './assets/boss_wing.png',
  './assets/candle.png',
  './assets/heart.png',
  './assets/gem.png',
  './assets/bone.png',
  './assets/fireball.png',
  './assets/orb.png',
  './assets/t_brick.png',
  './assets/t_brick_top.png',
  './assets/t_ledge.png',
  './assets/t_spikes.png',
  './assets/t_back.png',
  './assets/t_pillar.png',
  './assets/t_window.png',
];
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
