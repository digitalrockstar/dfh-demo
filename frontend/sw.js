// Service worker: keeps the app shell on the device so the POS opens with no connection. API calls are never cached here; the POS keeps its own data in IndexedDB.
const V = "dfh-shell-v2";
const SHELL = ["/", "/index.html", "/manifest.webmanifest", "/src/theme/tokens.css", "/src/ui.css", "/src/app.js", "/src/core.js", "/src/ui.js", "/src/page_ct.js", "/src/page_sku.js", "/src/page_wastage.js",
  "/src/page_demand.js", "/src/page_procurement.js", "/src/page_pos.js", "/src/page_inv.js", "/src/pos_store.js", "/assets/logo.png", "/assets/icon-192.png", "/assets/icon-512.png", "/assets/fonts/Inter-Regular.ttf", "/assets/fonts/Inter-Medium.ttf", "/assets/fonts/Inter-SemiBold.ttf", "/assets/fonts/Inter-Bold.ttf"];
self.addEventListener("install", e => e.waitUntil(caches.open(V).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== "GET" || u.origin !== location.origin || u.pathname.startsWith("/api/")) return;
  if (r.mode === "navigate") { e.respondWith(fetch(r).catch(() => caches.match("/index.html"))); return; }
  e.respondWith(caches.match(r).then(hit => {
    const fresh = fetch(r).then(res => { if (res.ok) caches.open(V).then(c => c.put(r, res.clone())); return res; }).catch(() => hit);
    return hit || fresh;
  }));
});
