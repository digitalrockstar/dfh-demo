// Offline store for the POS: IndexedDB for catalog, device, invoice block and the bill queue. Bill math mirrors dfh/pos_calc.py.
const DB = "dfh_pos";
let _db = null;
const open = () => _db || (_db = new Promise((res, rej) => {
  const r = indexedDB.open(DB, 1);
  r.onupgradeneeded = () => { const d = r.result; d.createObjectStore("meta"); d.createObjectStore("catalog", { keyPath: "id" }); const b = d.createObjectStore("bills", { keyPath: "idem_key" }); b.createIndex("status", "status"); };
  r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
}));
const rq = q => new Promise((res, rej) => { q.onsuccess = () => res(q.result); q.onerror = () => rej(q.error); });
async function tx(stores, mode, fn) {
  const d = await open();
  return new Promise((res, rej) => {
    const t = d.transaction(stores, mode); let out;
    Promise.resolve(fn(...[].concat(stores).map(s => t.objectStore(s)))).then(v => { out = v; }, e => { try { t.abort(); } catch {} rej(e); });
    t.oncomplete = () => res(out); t.onerror = () => rej(t.error); t.onabort = () => rej(t.error || new Error("Aborted"));
  });
}
export const getMeta = k => tx("meta", "readonly", m => rq(m.get(k)));
export const setMeta = (k, v) => tx("meta", "readwrite", m => rq(m.put(v, k)));
export const getCatalog = () => tx("catalog", "readonly", c => rq(c.getAll()));
export const putCatalog = list => tx("catalog", "readwrite", async c => { await rq(c.clear()); for (const r of list) c.put(r); });
export const allBills = () => tx("bills", "readonly", b => rq(b.getAll())).then(l => l.sort((a, b) => b.n - a.n));

// ---- bill math (integer paise, half up, tax inside the price) ----
const hud = (a, b) => Math.floor((2 * a + b) / (2 * b));
export function lineCalc(uom, price, qty, disc, rate) {
  const gross = uom === "g" ? hud(price * qty, 1000) : price * qty, net = gross - disc, bp = Math.round(rate * 100);
  return { gross, net, tax: net > 0 ? hud(net * bp, 10000 + bp) : 0 };
}
export function billCalc(ls) {
  const s = k => ls.reduce((a, l) => a + l[k], 0), net = s("net"), total = Math.floor((net + 50) / 100) * 100;
  return { gross: s("gross"), discount: s("discount"), tax: s("tax"), round_off: total - net, total };
}
export const cartCalc = cart => {
  const lines = cart.map(l => ({ ...lineCalc(l.sku.uom, l.sku.price, l.qty, l.disc, l.sku.tax_pct), discount: l.disc }));
  return { lines, ...billCalc(lines) };
};

// ---- invoice series: a block of numbers reserved by the server, used offline ----
export async function seriesLeft() { const s = await getMeta("series"); return s ? Math.max(0, s.end - s.next + 1) : 0; }
export async function refillSeries(net, force = false) {
  const dev = await getMeta("device"); if (!dev) return;
  const left = await seriesLeft(); if (!force && left > 20) return;
  const g = await net("/pos/series", { method: "POST", body: { device_id: dev.id, count: 100 } });
  const s = await getMeta("series");
  await setMeta("series", s && s.next <= s.end && g.start === s.end + 1 ? { ...s, end: g.end } : { prefix: g.prefix, next: g.start, end: g.end });
}

// ---- save a bill: take the next invoice number and write the bill in one transaction, so a crash cannot skip or repeat a number ----
export async function saveBill(cart, payments, extra = {}) {
  const dev = await getMeta("device"); if (!dev) throw new Error("Pick a billing device first");
  const calc = cartCalc(cart);
  if (payments.reduce((a, p) => a + p.amount_paise, 0) !== calc.total) throw new Error("Payments do not add up to the total");
  return tx(["meta", "bills"], "readwrite", async (m, b) => {
    const s = await rq(m.get("series"));
    if (!s || s.next > s.end) throw new Error("NO_SERIES");
    const n = s.next, id = crypto.randomUUID(), now = new Date(), pad = x => String(x).padStart(2, "0");
    const local = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
    const bill = { id, idem_key: `${dev.id}-${id}`, n, invoice_no: `${s.prefix}${String(n).padStart(5, "0")}`, created_at_device: local, business_date: local.slice(0, 10),
      lines: cart.map(l => ({ sku_id: l.sku.id, qty: l.qty, unit_price_paise: l.sku.price, discount_paise: l.disc })), view: cart.map((l, i) => ({ code: l.sku.code, name: l.sku.name, uom: l.sku.uom, qty: l.qty, price: l.sku.price, net: calc.lines[i].net })),
      payments, net_paise: calc.total, totals: { gross: calc.gross, discount: calc.discount, tax: calc.tax, round_off: calc.round_off }, status: "queued", ...extra };
    await rq(m.put({ ...s, next: n + 1 }, "series")); await rq(b.put(bill));
    return bill;
  });
}

// ---- push queued bills ----
let flushing = false;
export async function flush(net) {
  if (flushing) return { sent: 0 }; flushing = true;
  try {
    const dev = await getMeta("device"); if (!dev) return { sent: 0 };
    const q = (await allBills()).filter(b => b.status === "queued").sort((a, b) => a.n - b.n); let sent = 0;
    for (let i = 0; i < q.length; i += 20) {
      const chunk = q.slice(i, i + 20);
      const r = await net("/pos/sync", { method: "POST", body: { device_id: dev.id, queue_depth: q.length, bills: chunk.map(b => ({ id: b.id, idem_key: b.idem_key, invoice_no: b.invoice_no, created_at_device: b.created_at_device, lines: b.lines, payments: b.payments, net_paise: b.net_paise, customer_phone: b.customer_phone || null, consent_wa: !!b.consent_wa })) } });
      await tx("bills", "readwrite", async bs => {
        for (const x of r.results) {
          const b = await rq(bs.get(x.idem_key)); if (!b) continue;
          if (x.status === "rejected") { b.status = "rejected"; b.reason = x.reason; } else { b.status = x.status === "review" ? "review" : "synced"; b.reason = x.reason || null; b.synced_at = Date.now(); }
          await rq(bs.put(b));
        }
      });
      sent += r.results.filter(x => x.status !== "rejected").length;
    }
    // keep two weeks of synced bills on the device
    const cut = Date.now() - 14 * 864e5;
    await tx("bills", "readwrite", async bs => { for (const b of await rq(bs.getAll())) if ((b.status === "synced") && b.synced_at < cut) bs.delete(b.idem_key); });
    return { sent };
  } finally { flushing = false; }
}
