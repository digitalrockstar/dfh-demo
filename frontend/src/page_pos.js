import { html, raw, out, inr, num, esc, dmy } from "./ui.js";
import { S, acts, mount, toast } from "./core.js";
import * as db from "./pos_store.js";

const P = { tab: "bill", cat: "", q: "", cart: [], sim: false, catalog: [], store: null, stores: null, devices: [], dev: null, left: 0, queued: 0, rejected: 0, returnDays: 10, taxNote: "",
  syncing: false, lastSync: null, pay: [], phone: "", wa: false, tab2: null };
let root = null, timer = null;
const MANAGE = () => ["store_manager", "ceo", "admin"].includes(S.user.role), HEALTH = () => ["store_manager", "ceo", "admin", "finance", "procurement"].includes(S.user.role);
const online = () => !P.sim && navigator.onLine;
const paise = v => Math.round(parseFloat(String(v).replace(/,/g, "")) * 100) || 0;
const kg = q => q >= 1000 ? (q / 1000).toFixed(q % 1000 ? 2 : 0).replace(/0$/, "") + " kg" : q + " g";
const qtyTxt = (q, uom) => uom === "g" ? kg(q) : q + (q === 1 ? " pc" : " pcs");
const today = () => { const d = new Date(), p = x => String(x).padStart(2, "0"); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; };
const hm = s => new Date(s.replace(" ", "T")).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

async function net(path, opts = {}) {
  if (!online()) throw new Error("Offline");
  let r;
  try { r = await fetch("/api" + path, { method: opts.method || "GET", headers: { "Content-Type": "application/json", Authorization: "Bearer " + S.token }, body: opts.body ? JSON.stringify(opts.body) : undefined }); }
  catch { throw new Error("Offline"); }
  const j = await r.json().catch(() => ({}));
  if (r.status === 401) throw new Error("Session expired. Sign in again once you are online.");
  if (!r.ok) throw Object.assign(new Error(typeof j.detail === "string" ? j.detail : "Request failed"), { status: r.status });
  return j;
}

// ------------------------------------------------------------------ boot
export async function render(el) {
  root = el; P.cart = []; P.pay = []; P.tab = "bill";
  mount(el, html`<div class="head"><div><div class="eyebrow">Store POS</div><h1>Loading</h1></div></div>`);
  P.dev = await db.getMeta("device"); P.store = await db.getMeta("store"); P.catalog = await db.getCatalog(); P.returnDays = (await db.getMeta("return_days")) || 10; P.taxNote = (await db.getMeta("tax_note")) || "";
  if (online()) { try { await loadBootstrap(); } catch (e) { if (!P.catalog.length) return setup(e.message); } }
  else if (!P.catalog.length) return setup("This device has no catalog yet. Connect once to download it.");
  if (!P.dev) return setup();
  await refreshCounts();
  if (online()) { try { await db.refillSeries(net); await db.flush(net); await refreshCounts(); } catch {} }
  draw(); bindOnce(); clearInterval(timer); timer = setInterval(tick, 20000);
}

async function loadBootstrap(storeId) {
  const b = await net("/pos/bootstrap" + (storeId ? "?store_id=" + storeId : (P.store && S.user.role !== "cashier" && S.user.role !== "store_manager" ? "?store_id=" + P.store.id : "")));
  P.store = b.store; P.devices = b.devices; P.stores = b.stores; P.catalog = b.catalog; P.returnDays = b.return_days; P.taxNote = b.tax_note;
  await db.putCatalog(b.catalog); await db.setMeta("store", b.store); await db.setMeta("return_days", b.return_days); await db.setMeta("tax_note", b.tax_note); await db.setMeta("catalog_at", Date.now());
  if (P.dev && P.dev.store_id !== b.store.id) { P.dev = null; await db.setMeta("device", null); await db.setMeta("series", null); }
}

function setup(msg) {
  mount(root, html`<div class="head"><div><div class="eyebrow">Store POS</div><h1>Set up this device</h1><p>${msg || "Pick the billing device this browser will act as. Each device bills from its own block of invoice numbers, so two browsers must never share one."}</p></div></div>
    <div class="card solid" style="max-width:560px">${P.stores ? html`<label class="small muted">Store</label><select class="input" id="pstore" style="width:100%;margin-bottom:12px">${P.stores.map(s => html`<option value="${s.id}" ${P.store && P.store.id === s.id ? "selected" : ""}>${s.code} ${s.name}</option>`)}</select>` : ""}
    <div class="stack-list">${P.devices.map(d => html`<div class="pdev"><div><b>${d.code}</b><div class="small muted">Series ${d.prefix}, last seen ${d.last_seen_at ? hm(String(d.last_seen_at)) : "never"}</div></div><button class="btn pri" data-act="pos-pick" data-id="${d.id}">Use this device</button></div>`)}${P.devices.length ? "" : html`<p class="muted">No devices loaded. ${online() ? "" : "You are offline."}</p>`}</div></div>`);
  const sel = root.querySelector("#pstore"); if (sel) sel.onchange = async e => { await loadBootstrap(+e.target.value); setup(); };
}
acts["pos-pick"] = async a => {
  const d = P.devices.find(x => x.id === +a.dataset.id);
  await db.setMeta("device", { id: d.id, code: d.code, store_id: P.store.id, prefix: d.prefix }); await db.setMeta("series", null);
  try { await db.refillSeries(net, true); } catch (e) { toast(e.message, true); }
  render(root);
};

async function refreshCounts() {
  const bs = await db.allBills(); P.queued = bs.filter(b => b.status === "queued").length; P.rejected = bs.filter(b => b.status === "rejected").length; P.left = await db.seriesLeft(); P.bills = bs;
}
async function tick() {
  if (!root || !root.isConnected) return clearInterval(timer);
  if (online()) { try { P.syncing = true; status(); await db.refillSeries(net); await db.flush(net); P.lastSync = new Date(); } catch {} P.syncing = false; }
  await refreshCounts();
  if (root.querySelector("#pstat")) status();
  if (P.tab === "recent" && root.querySelector("#ptab")) renderTab();
}
function bindOnce() {
  if (root._posBound) return; root._posBound = true;
  addEventListener("online", () => { tick(); }); addEventListener("offline", () => { status(); });
  root.addEventListener("input", e => {
    if (!root.querySelector("#ptab")) return;
    const t = e.target;
    if (t.id === "pq") { P.q = t.value; grid(); }
    else if (t.dataset.g != null) { const l = P.cart[+t.dataset.g]; l.qty = Math.max(1, Math.min(50000, Math.round(parseFloat(t.value) * (l.sku.uom === "g" ? 1000 : 1)) || 0)); totals(); }
    else if (t.dataset.d != null) { const l = P.cart[+t.dataset.d]; l.disc = Math.max(0, paise(t.value)); totals(); }
    else if (t.dataset.pa != null) { P.pay[+t.dataset.pa].amount = paise(t.value); payCheck(); }
    else if (t.id === "pph") P.phone = t.value; else if (t.id === "pwa") P.wa = t.checked;
    else if (t.id === "dcn" || t.id === "dco") dcCalc();
  });
  root.addEventListener("keydown", e => {
    if (root.querySelector("#ptab") && e.target.id === "pq" && e.key === "Enter") {
      const q = P.q.trim(); const hit = P.catalog.find(s => s.barcode === q || s.code.toLowerCase() === q.toLowerCase());
      if (hit) { add(hit); P.q = ""; e.target.value = ""; grid(); }
    }
  });
}

// ------------------------------------------------------------------ layout
function draw() {
  const tabs = [["bill", "Bill"], ["recent", "Bills and returns"], ["close", "Day close"], ...(HEALTH() ? [["health", "Sync health"]] : [])];
  mount(root, html`<div class="head"><div><div class="eyebrow">Store POS</div><h1>${P.store.name}</h1><p id="pstat"></p></div>
    <div class="row"><label class="small muted pswitch"><input type="checkbox" id="psim" ${P.sim ? "checked" : ""}> Simulate offline</label><button class="btn" data-act="pos-sync">Sync now</button></div></div>
    <div class="tabs">${tabs.map(([k, l]) => html`<button data-act="pos-tab" data-v="${k}" class="${P.tab === k ? "on" : ""}">${l}</button>`)}</div><div id="ptab"></div>`);
  root.querySelector("#psim").onchange = e => { P.sim = e.target.checked; status(); if (online()) tick(); };
  status(); renderTab();
}
function status() {
  const el = root && root.querySelector("#pstat"); if (!el) return;
  const on = online();
  el.innerHTML = out(html`<span class="pill ${on ? "active" : "warn"}">${on ? "Online" : "Offline"}</span> <span class="pill ${P.queued ? "t" : ""}">${P.queued} waiting to sync</span> ${P.rejected ? html`<span class="pill delisted">${P.rejected} rejected</span>` : ""} <span class="small muted">${P.dev.code}, ${P.left} invoice numbers left${P.syncing ? ", syncing" : P.lastSync ? ", synced " + P.lastSync.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : ""}</span>`);
}
acts["pos-tab"] = a => { P.tab = a.dataset.v; root.querySelectorAll(".tabs button").forEach(b => b.classList.toggle("on", b === a)); renderTab(); };
acts["pos-sync"] = async () => {
  if (!online()) return toast("Offline. Bills stay on this device and sync when you are back online.", true);
  try { P.syncing = true; status(); const r = await db.flush(net); await db.refillSeries(net); P.lastSync = new Date(); toast(r.sent ? `${r.sent} bills synced` : "Nothing waiting"); } catch (e) { toast(e.message, true); }
  P.syncing = false; await refreshCounts(); status(); if (P.tab === "recent") renderTab();
};
function renderTab() {
  const el = root.querySelector("#ptab");
  if (P.tab === "bill") return billTab(el);
  if (P.tab === "recent") return recentTab(el);
  if (P.tab === "close") return closeTab(el);
  if (P.tab === "health") return healthTab(el);
}

// ------------------------------------------------------------------ bill tab
function billTab(el) {
  const cats = [...new Set(P.catalog.map(s => s.cat))];
  mount(el, html`<div class="posgrid"><div class="posl"><div class="row"><input class="input" id="pq" placeholder="Search name, code or scan barcode" autocomplete="off" value="${P.q}" style="flex:1"></div>
    <div class="chips catbar"><button class="chip ${P.cat === "" ? "on" : ""}" data-act="pos-cat" data-v="">All</button>${cats.map(c => html`<button class="chip ${P.cat === c ? "on" : ""}" data-act="pos-cat" data-v="${c}">${c}</button>`)}</div>
    <div class="tiles" id="ptiles"></div></div>
    <div class="posr card solid"><div class="ct"><h2>Current bill</h2><button class="btn sm" data-act="pos-clear">Clear</button></div><div id="pcart"></div><div id="ptot"></div><div id="ppay"></div></div></div>`);
  grid(); cart();
}
function grid() {
  const el = root.querySelector("#ptiles"); if (!el) return;
  const q = P.q.trim().toLowerCase();
  const rows = P.catalog.filter(s => (!P.cat || s.cat === P.cat) && (!q || s.name.toLowerCase().includes(q) || s.code.toLowerCase().includes(q) || (s.barcode || "").includes(q)));
  el.innerHTML = out(html`${rows.slice(0, 60).map(s => html`<button class="tile" data-act="pos-add" data-id="${s.id}"><span class="tn">${s.name}</span><span class="tp num">${inr(s.price, false)}${s.uom === "g" ? " / kg" : ""}</span>${s.stock <= 0 ? html`<span class="tag">No stock recorded</span>` : ""}</button>`)}${rows.length > 60 ? html`<p class="small muted" style="grid-column:1/-1">Showing 60 of ${rows.length}. Type to narrow it down.</p>` : ""}${rows.length ? "" : html`<p class="muted" style="grid-column:1/-1">Nothing matches.</p>`}`);
}
acts["pos-cat"] = a => { P.cat = a.dataset.v; root.querySelectorAll(".catbar .chip").forEach(c => c.classList.toggle("on", c === a)); grid(); };
function add(s) {
  const ex = P.cart.find(l => l.sku.id === s.id);
  if (ex) ex.qty += s.uom === "g" ? 100 : 1; else P.cart.push({ sku: s, qty: s.uom === "g" ? 250 : 1, disc: 0 });
  P.pay = []; cart();
}
acts["pos-add"] = a => add(P.catalog.find(s => s.id === +a.dataset.id));
acts["pos-clear"] = () => { P.cart = []; P.pay = []; P.phone = ""; P.wa = false; cart(); };
acts["pos-rm"] = a => { P.cart.splice(+a.dataset.i, 1); P.pay = []; cart(); };
acts["pos-step"] = a => { const l = P.cart[+a.dataset.i], d = +a.dataset.d; l.qty = Math.max(1, l.qty + d * (l.sku.uom === "g" ? 50 : 1)); P.pay = []; cart(); };
acts["pos-w"] = a => { const l = P.cart[+a.dataset.i]; l.qty = +a.dataset.v; P.pay = []; cart(); };

function cart() {
  const el = root.querySelector("#pcart"); if (!el) return;
  if (!P.cart.length) { el.innerHTML = out(html`<p class="muted" style="padding:24px 0;text-align:center">Tap an item or scan a barcode to start a bill.</p>`); totals(); return; }
  el.innerHTML = out(html`${P.cart.map((l, i) => html`<div class="cl"><div class="cn"><b>${l.sku.name}</b><span class="small muted">${inr(l.sku.price, false)}${l.sku.uom === "g" ? " per kg" : " each"}, GST ${l.sku.tax_pct}% included</span>${l.qty > l.sku.stock ? html`<span class="small warn">Store stock shows ${qtyTxt(Math.max(l.sku.stock, 0), l.sku.uom)}. You can still bill it, a manager will see the shortfall.</span>` : ""}</div>
    <div class="cq">${l.sku.uom === "g" ? html`<input class="input num" data-g="${i}" inputmode="decimal" value="${(l.qty / 1000).toFixed(3).replace(/\.?0+$/, "")}" aria-label="Weight in kg"><span class="small muted">kg</span>
      <div class="chips wq">${[100, 250, 500, 1000].map(w => html`<button class="chip" data-act="pos-w" data-i="${i}" data-v="${w}">${w >= 1000 ? "1 kg" : w + " g"}</button>`)}</div>`
      : html`<button class="btn sm" data-act="pos-step" data-i="${i}" data-d="-1" aria-label="Less">-</button><b class="num">${l.qty}</b><button class="btn sm" data-act="pos-step" data-i="${i}" data-d="1" aria-label="More">+</button>`}</div>
    <div class="cr"><span class="num lt" data-lt="${i}"></span><input class="input num disc" data-d="${i}" inputmode="decimal" placeholder="Discount" value="${l.disc ? l.disc / 100 : ""}" aria-label="Line discount in rupees"><button class="btn sm" data-act="pos-rm" data-i="${i}" aria-label="Remove">Remove</button></div></div>`)}`);
  totals();
}
function totals() {
  const t = db.cartCalc(P.cart);
  P.cart.forEach((l, i) => { const e = root.querySelector(`[data-lt="${i}"]`); if (e) e.textContent = inr(t.lines[i].net, false); });
  const el = root.querySelector("#ptot"); if (!el) return;
  el.innerHTML = out(P.cart.length ? html`<div class="tt"><div><span>Items value</span><span class="num">${inr(t.gross, false)}</span></div>${t.discount ? html`<div><span>Discount</span><span class="num">-${inr(t.discount, false)}</span></div>` : ""}
    <div class="small muted"><span>GST included (assumed rates)</span><span class="num">${inr(t.tax, false)}</span></div>${t.round_off ? html`<div class="small muted"><span>Round off</span><span class="num">${t.round_off > 0 ? "+" : ""}${(t.round_off / 100).toFixed(2)}</span></div>` : ""}
    <div class="big"><span>Total</span><span class="num">${inr(t.total, false)}</span></div></div>` : "");
  P.total = t.total; payBox();
}

// ------------------------------------------------------------------ payment
function payBox() {
  const el = root.querySelector("#ppay"); if (!el) return;
  if (!P.cart.length) { el.innerHTML = ""; return; }
  if (!P.pay.length || P.pay.reduce((a, p) => a + p.amount, 0) !== P.total && P.pay.length === 1) P.pay = [{ mode: P.pay[0]?.mode || "cash", amount: P.total, tender: 0 }];
  el.innerHTML = out(html`<div class="pays">${P.pay.map((p, i) => html`<div class="pr"><div class="seg">${["cash", "upi", "card"].map(m => html`<button data-act="pos-mode" data-i="${i}" data-v="${m}" class="${p.mode === m ? "on" : ""}">${m === "upi" ? "UPI" : m[0].toUpperCase() + m.slice(1)}</button>`)}</div>
    <input class="input num" data-pa="${i}" inputmode="decimal" value="${p.amount / 100}" aria-label="Amount">${P.pay.length > 1 ? html`<button class="btn sm" data-act="pos-prm" data-i="${i}">x</button>` : ""}</div>`)}</div>
    <div class="row" style="margin:8px 0"><button class="btn sm" data-act="pos-split">Split payment</button><span class="small muted" id="pchg"></span></div>
    <div class="row" style="margin-bottom:8px"><input class="input" id="pph" placeholder="Customer phone (optional)" inputmode="tel" value="${P.phone}" style="flex:1"><label class="small muted"><input type="checkbox" id="pwa" ${P.wa ? "checked" : ""}> WhatsApp ok</label></div>
    <button class="btn pri charge" id="pcharge" data-act="pos-charge">Charge</button>`);
  payCheck();
}
function payCheck() {
  const sum = P.pay.reduce((a, p) => a + p.amount, 0), diff = P.total - sum, b = root.querySelector("#pcharge"), c = root.querySelector("#pchg"); if (!b) return;
  b.disabled = diff !== 0; b.textContent = diff === 0 ? `Charge ${inr(P.total, false)}` : diff > 0 ? `${inr(diff, false)} still to allocate` : `${inr(-diff, false)} over the total`;
  if (c) c.textContent = "";
}
acts["pos-mode"] = a => { P.pay[+a.dataset.i].mode = a.dataset.v; a.parentNode.querySelectorAll("button").forEach(b => b.classList.toggle("on", b === a)); };
acts["pos-split"] = () => { const used = P.pay.reduce((a, p) => a + p.amount, 0); P.pay.length === 1 && (P.pay[0].amount = Math.floor(P.total / 2 / 100) * 100); const rest = P.total - P.pay.reduce((a, p) => a + p.amount, 0); P.pay.push({ mode: P.pay[0].mode === "cash" ? "upi" : "cash", amount: Math.max(0, rest) }); payBox(); };
acts["pos-prm"] = a => { P.pay.splice(+a.dataset.i, 1); if (P.pay.length === 1) P.pay[0].amount = P.total; payBox(); };
acts["pos-charge"] = async a => {
  a.disabled = true;
  try {
    const bill = await db.saveBill(P.cart, P.pay.filter(p => p.amount > 0).map(p => ({ mode: p.mode, amount_paise: p.amount })), { customer_phone: P.phone.trim() || null, consent_wa: P.wa, cashier: S.user.name, store: P.store.name });
    P.cart = []; P.pay = []; P.phone = ""; P.wa = false;
    await refreshCounts(); status(); cart(); receipt(bill);
    if (online()) { db.flush(net).then(refreshCounts).then(status).catch(() => {}); if (P.left <= 20) db.refillSeries(net).then(refreshCounts).then(status).catch(() => {}); }
  } catch (e) {
    if (e.message === "NO_SERIES") toast("No invoice numbers left on this device. Connect to the internet to get a new block.", true); else toast(e.message, true);
    a.disabled = false;
  }
};
function receipt(b) {
  document.body.insertAdjacentHTML("beforeend", out(html`<div class="scrim" data-act="pos-close"></div><div class="modal solid receipt"><div class="rc"><img src="/assets/logo.png" alt="Dry Fruit House" height="34"><div class="small muted">${b.store}</div>
    <h2>${b.invoice_no}</h2><div class="small muted">${new Date(b.created_at_device).toLocaleString("en-IN")}, ${b.cashier}</div>
    <table class="tbl" style="margin:12px 0"><tbody>${b.view.map(v => html`<tr><td>${v.name}<div class="small muted">${qtyTxt(v.qty, v.uom)}</div></td><td class="r num">${inr(v.net, false)}</td></tr>`)}</tbody></table>
    <div class="tt"><div><span>Total</span><b class="num">${inr(b.net_paise, false)}</b></div>${b.payments.map(p => html`<div class="small muted"><span>${p.mode.toUpperCase()}</span><span class="num">${inr(p.amount_paise, false)}</span></div>`)}<div class="small muted"><span>GST included</span><span class="num">${inr(b.totals.tax, false)}</span></div></div>
    <p class="small muted" style="margin-top:10px">${online() ? "Sending to the server." : "Saved on this device. It will sync when the connection is back."}</p></div>
    <div class="row" style="margin-top:14px;justify-content:flex-end"><button class="btn" data-act="pos-print">Print</button><button class="btn pri" data-act="pos-close">New bill</button></div></div>`));
  document.querySelector(".modal .btn.pri")?.focus();
}
acts["pos-close"] = () => document.querySelectorAll(".scrim,.modal").forEach(n => n.remove());
acts["pos-print"] = () => print();

// ------------------------------------------------------------------ recent bills and returns
async function recentTab(el) {
  await refreshCounts();
  const st = { queued: ["Waiting", "t"], synced: ["Synced", "active"], review: ["Review", "restricted"], rejected: ["Rejected", "delisted"] };
  mount(el, html`<div class="cols eq"><div class="card solid"><div class="ct"><h2>On this device</h2><span class="small muted">Newest first</span></div><div class="tblwrap"><table class="tbl"><thead><tr><th>Invoice</th><th>Time</th><th class="r">Total</th><th>State</th></tr></thead><tbody>
    ${P.bills.slice(0, 40).map(b => html`<tr class="${online() && b.status !== "queued" && b.status !== "rejected" ? "click" : ""}" data-act="pos-open" data-v="${b.invoice_no}"><td>${b.invoice_no}</td><td>${new Date(b.created_at_device).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</td><td class="r num">${inr(b.net_paise, false)}</td><td><span class="pill ${st[b.status][1]}" title="${esc(b.reason || "")}">${st[b.status][0]}</span>${b.reason ? html`<div class="small muted">${b.reason}</div>` : ""}</td></tr>`)}
    ${P.bills.length ? "" : html`<tr><td colspan="4" class="muted">No bills on this device yet.</td></tr>`}</tbody></table></div></div>
    <div class="card solid"><div class="ct"><h2>Returns</h2><span class="small muted">Defective or damaged, within ${P.returnDays} days. Needs a connection.</span></div>
    <div class="row"><input class="input" id="pinv" placeholder="Invoice number" style="flex:1"><button class="btn pri" data-act="pos-find">Find bill</button></div><div id="pret" style="margin-top:12px"></div><div id="plist" style="margin-top:14px"></div></div></div>`);
  el.querySelector("#pinv").addEventListener("keydown", e => e.key === "Enter" && acts["pos-find"]());
  if (online()) retList();
}
acts["pos-open"] = a => { if (!online()) return; root.querySelector("#pinv").value = a.dataset.v; acts["pos-find"](); };
acts["pos-find"] = async () => {
  const el = root.querySelector("#pret"), no = root.querySelector("#pinv").value.trim(); if (!no) return;
  if (!online()) { el.innerHTML = out(html`<p class="muted">Returns need the original bill from the server, so they work online only.</p>`); return; }
  try {
    const b = await net("/pos/bills/" + encodeURI(no)); P.ret = b;
    el.innerHTML = out(html`<div class="small"><b>${b.invoice_no}</b>, ${dmy(String(b.business_date).slice(0, 10))}, ${inr(b.net_paise, false)}, ${b.days_since_sale} days ago ${b.returnable ? "" : html`<span class="pill delisted">Not returnable</span>`}</div>
      <table class="tbl" style="margin:8px 0"><tbody>${b.lines.map(l => html`<tr><td>${l.name}<div class="small muted">Sold ${qtyTxt(l.qty, l.uom)}${l.returned ? ", returned " + qtyTxt(l.returned, l.uom) : ""}</div></td><td class="r"><input class="input num" style="width:84px" data-rl="${l.id}" inputmode="decimal" placeholder="${l.uom === "g" ? "grams" : "qty"}" ${b.returnable && l.qty > l.returned ? "" : "disabled"}></td></tr>`)}</tbody></table>
      <div class="row"><select class="input" id="prr"><option value="defective">Defective</option><option value="damaged">Damaged</option></select><input class="input" id="prn" placeholder="Note" style="flex:1"><button class="btn pri" data-act="pos-return" ${b.returnable ? "" : "disabled"}>Submit return</button></div>`);
  } catch (e) { el.innerHTML = out(html`<p class="muted">${e.message}</p>`); }
};
acts["pos-return"] = async () => {
  const lines = [...root.querySelectorAll("[data-rl]")].map(i => ({ sale_line_id: +i.dataset.rl, qty: Math.round(parseFloat(i.value) || 0) })).filter(l => l.qty > 0);
  if (!lines.length) return toast("Enter a quantity to return", true);
  try {
    const r = await net("/pos/returns", { method: "POST", body: { invoice_no: P.ret.invoice_no, reason: root.querySelector("#prr").value, note: root.querySelector("#prn").value, lines } });
    toast(`${r.return_no}: refund ${inr(r.refund_paise, false)}, ${r.status === "pending" ? "waiting for a manager" : "approved"}`); root.querySelector("#pret").innerHTML = ""; retList();
  } catch (e) { toast(e.message, true); }
};
async function retList() {
  const el = root.querySelector("#plist"); if (!el) return;
  try {
    const { returns } = await net("/pos/returns?store_id=" + P.store.id);
    el.innerHTML = out(html`<h3 class="small muted" style="margin-bottom:6px">Recent returns</h3>${returns.slice(0, 8).map(r => html`<div class="rrow"><div><b>${r.return_no}</b> <span class="small muted">${r.invoice_no}, ${r.reason}</span></div><div class="row"><span class="num">${inr(r.refund_paise, false)}</span><span class="pill ${r.status === "approved" ? "active" : r.status === "pending" ? "restricted" : "delisted"}">${r.status}</span>
      ${r.status === "pending" && MANAGE() ? html`<button class="btn sm" data-act="pos-dec" data-id="${r.id}" data-v="approve">Approve</button><button class="btn sm" data-act="pos-dec" data-id="${r.id}" data-v="reject">Reject</button>` : ""}</div></div>`)}${returns.length ? "" : html`<p class="muted small">No returns yet.</p>`}`);
  } catch { el.innerHTML = ""; }
}
acts["pos-dec"] = async a => { try { await net(`/pos/returns/${a.dataset.id}/decision`, { method: "POST", body: { action: a.dataset.v } }); retList(); } catch (e) { toast(e.message, true); } };

// ------------------------------------------------------------------ day close
let dc = null;
async function closeTab(el) {
  await refreshCounts();
  if (!online()) return mount(el, html`<div class="card solid"><h2>Day close</h2><p class="muted" style="margin-top:8px">Day close reads every device in the store from the server, so it needs a connection. Bills on this device are safe and will count once they sync.</p></div>`);
  if (P.queued) return mount(el, html`<div class="card solid"><h2>Sync first</h2><p class="muted" style="margin:8px 0">${P.queued} bills on this device have not reached the server. Closing now would leave them out of the cash count.</p><button class="btn pri" data-act="pos-sync-close">Sync now</button></div>`);
  try { dc = await net(`/pos/day-close?business_date=${today()}&store_id=${P.store.id}`); } catch (e) { return mount(el, html`<div class="card solid"><p class="muted">${e.message}</p></div>`); }
  const closed = dc.close && dc.close.status !== "open", rs = v => (v / 100);
  mount(el, html`<div class="kpis"><div class="kpi solid"><div class="l">Bills today</div><div class="v">${num(dc.bills)}</div><div class="s">${inr(dc.sales, false)} sales</div></div>
    ${["cash", "upi", "card"].map(m => html`<div class="kpi solid"><div class="l">${m === "upi" ? "UPI" : m[0].toUpperCase() + m.slice(1)}</div><div class="v">${inr(dc.by_mode[m] || 0, false)}</div></div>`)}</div>
    <div class="card solid" style="max-width:640px"><div class="ct"><h2>Cash count, ${dmy(today())}</h2>${closed ? html`<span class="pill ${dc.close.status === "variance" ? "restricted" : "active"}">${dc.close.status}</span>` : ""}</div>
    <div class="kv2"><span>Cash sales</span><b class="num">${inr(dc.cash_sales, false)}</b><span>Approved cash refunds</span><b class="num">-${inr(dc.refunds, false)}</b><span>Cash drops</span><b class="num">-${inr(dc.drops, false)}</b></div>
    ${closed ? html`<div class="kv2"><span>Opening cash</span><b class="num">${inr(dc.close.opening_cash_paise, false)}</b><span>Expected</span><b class="num">${inr(dc.close.expected_cash_paise, false)}</b><span>Counted</span><b class="num">${inr(dc.close.counted_cash_paise, false)}</b><span>Variance</span><b class="num">${inr(dc.close.variance_paise, false)}</b></div>`
    : html`<div class="frm"><div><label>Opening cash</label><input class="input num" id="dco" inputmode="decimal" value="${rs(dc.suggested_opening)}"></div><div><label>Counted cash</label><input class="input num" id="dcn" inputmode="decimal" placeholder="0"></div></div>
    <p class="row" style="margin:10px 0"><span class="muted">Expected</span><b class="num" id="dce"></b><span class="muted" style="margin-left:12px">Variance</span><b class="num" id="dcv"></b></p><input class="input" id="dcnote" placeholder="Note (needed if the variance is above ₹100)" style="width:100%;margin-bottom:10px">
    <div class="row"><button class="btn pri" data-act="pos-dclose">Close the day</button><button class="btn" data-act="pos-drop">Record cash drop</button></div>`}</div>`);
  if (!closed) dcCalc();
}
acts["pos-sync-close"] = async () => { await acts["pos-sync"](); closeTab(root.querySelector("#ptab")); };
function dcCalc() {
  if (!dc) return; const o = paise(root.querySelector("#dco")?.value), c = root.querySelector("#dcn")?.value, e = o + dc.cash_sales - dc.refunds - dc.drops;
  const ee = root.querySelector("#dce"), ev = root.querySelector("#dcv"); if (!ee) return;
  ee.textContent = inr(e, false); ev.textContent = c === "" ? "" : inr(paise(c) - e, false);
}
acts["pos-drop"] = async () => {
  const v = prompt("Cash drop amount in rupees"); if (!v) return;
  try { await net("/pos/cash-drop", { method: "POST", body: { amount_paise: paise(v), business_date: today(), store_id: P.store.id } }); toast("Cash drop recorded"); closeTab(root.querySelector("#ptab")); } catch (e) { toast(e.message, true); }
};
acts["pos-dclose"] = async () => {
  try {
    const r = await net("/pos/day-close", { method: "POST", body: { business_date: today(), store_id: P.store.id, opening_cash_paise: paise(root.querySelector("#dco").value), counted_cash_paise: paise(root.querySelector("#dcn").value), note: root.querySelector("#dcnote").value } });
    toast(r.status === "variance" ? "Day closed with a variance" : "Day closed"); closeTab(root.querySelector("#ptab"));
  } catch (e) { toast(e.message, true); }
};

// ------------------------------------------------------------------ sync health
async function healthTab(el) {
  if (!online()) return mount(el, html`<div class="card solid"><p class="muted">Sync health is read from the server. Connect to see it.</p></div>`);
  try {
    const h = await net("/pos/health"), s = h.summary, tone = { ok: "active", late: "restricted", stale: "delisted", never: "delisted" };
    mount(el, html`<div class="kpis">${[["ok", "Syncing"], ["late", "Late (over 1 hour)"], ["stale", "Stale (over 24 hours)"], ["never", "Never synced"]].map(([k, l]) => html`<div class="kpi solid"><div class="l">${l}</div><div class="v">${num(s[k])}</div></div>`)}</div>
      <div class="card solid"><div class="ct"><h2>Devices</h2><span class="small muted">Worst first, ${h.devices.length} of ${h.total}</span></div><div class="tblwrap"><table class="tbl"><thead><tr><th>Device</th><th>Store</th><th>Last sync</th><th class="r">Bills 24h</th><th class="r">Rejected 24h</th><th>State</th></tr></thead><tbody>
      ${h.devices.map(d => html`<tr><td>${d.code}</td><td>${d.store_name}<div class="small muted">${d.city}</div></td><td>${d.minutes_since_sync == null ? "never" : d.minutes_since_sync < 90 ? d.minutes_since_sync + " min ago" : d.minutes_since_sync < 2880 ? Math.round(d.minutes_since_sync / 60) + " h ago" : Math.round(d.minutes_since_sync / 1440) + " days ago"}</td><td class="r num">${d.bills_24h}</td><td class="r num">${d.rejected_24h}</td><td><span class="pill ${tone[d.state]}">${d.state}</span></td></tr>`)}</tbody></table></div></div>`);
  } catch (e) { mount(el, html`<div class="card solid"><p class="muted">${e.message}</p></div>`); }
}
