import { html, raw, out, inr, rs, pct, num, spark, esc } from "./ui.js";
import { api, acts, mount, toast, canWrite, S } from "./core.js";

const st = { q: "", cat: "", ptype: "", status: "", sort: "popularity", dir: "desc", page: 1 };
const TYPES = { bulk: "Loose bulk", repacked: "Repacked", finished: "Finished", kit: "Gift kit" };
let root, cats = [], timer, cur = null, tab = "overview";
const unit = s => s.base_uom === "g" ? "₹/kg" : "₹/unit";
const price = s => s.base_uom === "g" ? s.price_per_kg_paise : s.mrp_paise;

export async function render(el, param) {
  root = el; cats = await api("/categories");
  mount(el, html`<div class="head"><div><div class="eyebrow">Module 2</div><h1>SKU master</h1><p class="muted" id="sub">One catalog for packs, tax, shelf life, prices and cost.</p></div>
    <div class="row">${canWrite() ? html`<button class="btn" data-act="sku-import">Import prices</button>` : ""}</div></div>
    <div class="row" style="margin-bottom:12px"><input class="input" id="q" placeholder="Search name, code or barcode" style="width:280px" value="${st.q}">
    <select class="input" id="ptype"><option value="">All sourcing</option>${Object.entries(TYPES).map(([k, v]) => html`<option value="${k}" ${st.ptype === k ? "selected" : ""}>${v}</option>`)}</select>
    <select class="input" id="status"><option value="">Any status</option>${["active", "restricted", "delisted", "draft"].map(s => html`<option ${st.status === s ? "selected" : ""}>${s}</option>`)}</select>
    <select class="input" id="sort">${[["popularity", "Best selling"], ["name", "Name"], ["price", "Price"], ["margin", "Margin"], ["cost", "Cost"]].map(([k, v]) => html`<option value="${k}" ${st.sort === k ? "selected" : ""}>${v}</option>`)}</select>
    <button class="btn" id="dir" data-act="sku-dir">${st.dir === "desc" ? "High to low" : "Low to high"}</button></div>
    <div class="chips" id="cats" style="margin-bottom:14px"></div><div class="solid"><div class="tblwrap" id="list"></div></div><div class="row" id="pager" style="justify-content:space-between;margin-top:12px"></div>`);
  const go = () => { st.page = 1; load(); };
  el.querySelector("#q").oninput = e => { st.q = e.target.value; clearTimeout(timer); timer = setTimeout(go, 220); };
  for (const id of ["ptype", "status", "sort"]) el.querySelector("#" + id).onchange = e => { st[id] = e.target.value; go(); };
  drawCats(); await load();
  if (param) openSku(+param);
}
const drawCats = () => mount(root.querySelector("#cats"), html`<button class="chip ${st.cat === "" ? "on" : ""}" data-act="sku-cat" data-v="">All<small>${num(cats.reduce((a, c) => a + c.skus, 0))}</small></button>${cats.map(c => html`<button class="chip ${st.cat === c.code ? "on" : ""}" data-act="sku-cat" data-v="${c.code}">${c.name}<small>${c.skus}</small></button>`)}`);

async function load() {
  const p = new URLSearchParams({ q: st.q, cat: st.cat, ptype: st.ptype, status: st.status, sort: st.sort, dir: st.dir, page: st.page, size: 50 });
  const r = await api("/skus?" + p);
  root.querySelector("#sub").textContent = `${num(r.total)} SKUs match. Margins are ex tax at standard cost.`;
  mount(root.querySelector("#list"), html`<table class="tbl"><thead><tr><th>SKU</th><th>Category</th><th>Sourcing</th><th>Pack</th><th class="r">Price</th><th class="r">Cost</th><th class="r">Margin</th><th>Status</th></tr></thead><tbody>
    ${r.items.map(s => html`<tr class="click" data-act="sku-open" data-id="${s.id}"><td><b>${s.name}</b><div class="small muted">${s.code} · ${s.barcode}</div></td><td>${s.cat_name}</td><td><span class="pill t">${TYPES[s.procurement_type]}</span></td>
    <td>${s.pack_g ? (s.pack_g >= 1000 ? s.pack_g / 1000 + " kg" : s.pack_g + " g") : "by weight"}</td><td class="r">${rs(price(s) / 100)}<div class="small muted">${unit(s)}</div></td><td class="r">${rs(s.std_cost_paise / 100)}</td>
    <td class="r">${pct(s.gm, 0)}</td><td><span class="pill ${s.status}">${s.status}</span></td></tr>`)}${r.items.length ? "" : html`<tr><td colspan="8" class="muted" style="padding:30px;text-align:center">No SKUs match these filters.</td></tr>`}</tbody></table>`);
  const pages = Math.max(1, Math.ceil(r.total / r.size));
  mount(root.querySelector("#pager"), html`<span class="muted small">Page ${r.page} of ${pages}</span><div class="row"><button class="btn" data-act="sku-pg" data-v="-1" ${r.page <= 1 ? "disabled" : ""}>Previous</button><button class="btn" data-act="sku-pg" data-v="1" ${r.page >= pages ? "disabled" : ""}>Next</button></div>`);
}
acts["sku-cat"] = a => { st.cat = a.dataset.v; st.page = 1; drawCats(); load(); };
acts["sku-dir"] = a => { st.dir = st.dir === "desc" ? "asc" : "desc"; a.textContent = st.dir === "desc" ? "High to low" : "Low to high"; load(); };
acts["sku-pg"] = a => { st.page += +a.dataset.v; load(); };
acts["sku-open"] = a => openSku(+a.dataset.id);

function close() { document.querySelectorAll(".scrim,.drawer,.modal").forEach(n => n.remove()); history.replaceState(null, "", "#/skus"); }
acts["close"] = close;
async function openSku(id, keepTab) {
  if (!keepTab) tab = "overview";
  cur = await api("/skus/" + id); history.replaceState(null, "", "#/skus/" + id);
  let d = document.querySelector(".drawer");
  if (!d) { document.body.insertAdjacentHTML("beforeend", `<div class="scrim" data-act="close"></div><aside class="drawer glass wide"></aside>`); d = document.querySelector(".drawer"); }
  drawSku(d);
}
function drawSku(d) {
  const s = cur, pr = price(s), exTax = pr / (1 + s.tax_pct / 100);
  const tabs = [["overview", "Overview"], ["pricing", "Pricing and vendors"], [s.kit ? "kit" : "packs", s.kit ? "Gift box contents" : s.bulk_parent ? "Source and yield" : "Packs"], ["sales", "Sales"], ["history", "History"]];
  mount(d, html`<div class="row" style="justify-content:space-between;align-items:flex-start"><div><div class="eyebrow">${s.cat_name}</div><h1>${s.name}</h1><p class="muted small" style="margin-top:6px">${s.code} · barcode ${s.barcode}</p></div><button class="icon" data-act="close" aria-label="Close">✕</button></div>
    <div class="stats"><div><b>${rs(pr / 100)}</b><span>${s.base_uom === "g" ? "Price per kg" : "MRP"}</span></div><div><b>${rs(s.std_cost_paise / 100)}</b><span>Standard cost</span></div><div><b>${pct(s.gm, 1)}</b><span>Margin ex tax</span></div>
    <div><b>${s.tax_pct}%</b><span>GST ${s.tax_assumed ? "(assumed)" : ""}</span></div><div><b>${s.shelf_life_days} d</b><span>Shelf life</span></div></div>
    <div class="tabs">${tabs.map(([k, l]) => html`<button class="${tab === k ? "on" : ""}" data-act="sku-tab" data-v="${k}">${l}</button>`)}</div><div id="tabbody"></div>`);
  tabBody();
}
acts["sku-tab"] = a => { tab = a.dataset.v; document.querySelectorAll(".tabs button").forEach(b => b.classList.toggle("on", b.dataset.v === tab)); tabBody(); };
function tabBody() {
  const s = cur, el = document.querySelector("#tabbody"); if (!el) return;
  if (tab === "overview") {
    const moves = { draft: ["active", "delisted"], active: ["restricted", "delisted"], restricted: ["active", "delisted"], delisted: ["active"] }[s.status];
    mount(el, html`<dl class="kv"><dt>Status</dt><dd><span class="pill ${s.status}">${s.status}</span></dd><dt>Sourcing</dt><dd>${TYPES[s.procurement_type]}${s.bulk_parent ? html` from <a href="#/skus/${s.bulk_parent.id}" data-act="sku-jump" data-id="${s.bulk_parent.id}">${s.bulk_parent.name}</a>` : ""}</dd>
      <dt>Grade</dt><dd>${s.grade || "n/a"}</dd><dt>Pack</dt><dd>${s.pack_g ? s.pack_g + " g" : "Sold by weight"}</dd><dt>Unit of measure</dt><dd>${s.base_uom === "g" ? "Grams (loose)" : "Units"}</dd><dt>HSN</dt><dd>${s.hsn}</dd>
      <dt>Origin</dt><dd>${s.origins || "n/a"}</dd><dt>Freshness</dt><dd>${s.is_fresh ? "Short shelf life, fresh or roasted" : "Ambient"}</dd></dl>
      ${canWrite() ? html`<div class="solid" style="padding:16px;margin-top:18px"><h2>Change price or status</h2><p class="small muted" style="margin:4px 0 12px">Every change is written to the audit log. Prices at or below cost after tax are rejected.</p>
      <div class="row"><input class="input num" id="np" type="number" step="0.5" placeholder="New ${s.base_uom === "g" ? "price per kg" : "MRP"} in ₹" style="width:190px"><select class="input" id="ns"><option value="">Keep status</option>${moves.map(m => html`<option>${m}</option>`)}</select>
      <input class="input" id="nr" placeholder="Reason" style="flex:1;min-width:120px"><button class="btn pri" data-act="sku-save">Save</button></div><p class="small muted" id="prev" style="margin-top:8px"></p></div>` : html`<p class="small muted" style="margin-top:16px">Your role can view this SKU but not change it.</p>`}`);
    const np = el.querySelector("#np"); if (np) np.oninput = () => { const v = +np.value * 100; el.querySelector("#prev").textContent = v ? `Margin ex tax would be ${pct(1 - s.std_cost_paise / (v / (1 + s.tax_pct / 100)))} against ${pct(s.gm)} now.` : ""; };
  } else if (tab === "pricing") {
    const best = s.vendors[0];
    mount(el, html`${s.vendor_source_note ? html`<p class="small muted" style="margin-bottom:10px">${s.vendor_source_note}. Prices below are landed in ₹ at each month's exchange rate, before freight and duty.</p>` : ""}
      <table class="tbl"><thead><tr><th>Vendor</th><th>Terms</th><th class="r">Latest</th><th class="r">3 month</th><th>Apr to Oct</th></tr></thead><tbody>${s.vendors.map(v => html`<tr><td><b>${v.name}</b><div class="small muted">${v.type}${v.trader ? " trader" : ""} · ${v.country}</div></td>
      <td class="small">${v.incoterm}, ${v.lead_days} d lead<br>MOQ ${v.unit === "kg" ? num(v.moq / 1000) + " kg" : num(v.moq) + " units"}</td><td class="r">${rs(v.latest)}${v === best ? html`<div><span class="pill active">lowest</span></div>` : ""}</td>
      <td class="r">${v.chg_3m == null ? "n/a" : html`<span class="${v.chg_3m > .05 ? "pill delisted" : ""}">${v.chg_3m >= 0 ? "+" : ""}${(v.chg_3m * 100).toFixed(1)}%</span>`}</td><td>${spark(v.series.map(x => x.inr), 96, 28, v.chg_3m > .05 ? "var(--bad)" : "var(--primary)")}</td></tr>`)}</tbody></table>
      ${s.vendors.length ? "" : html`<p class="muted">No vendor prices on file.</p>`}`);
  } else if (tab === "kit") {
    const k = s.kit, cost = k.component_cost;
    mount(el, html`<p class="small muted" style="margin-bottom:10px">A gift box is assembled from packed SKUs. Stock of each component reduces when a box is sold.</p><table class="tbl"><thead><tr><th>Component</th><th class="r">Qty</th><th class="r">Cost</th><th class="r">MRP</th></tr></thead><tbody>
      ${k.components.map(c => html`<tr><td><b>${c.name}</b></td><td class="r">${c.qty}</td><td class="r">${rs(c.std_cost_paise / 100)}</td><td class="r">${rs(c.mrp_paise / 100)}</td></tr>`)}</tbody></table>
      <p style="margin-top:12px">Components cost <b>${rs(cost / 100)}</b>. Standard cost with the box is <b>${rs(s.std_cost_paise / 100)}</b>, selling at <b>${rs(s.mrp_paise / 100)}</b>.</p>`);
  } else if (tab === "packs") {
    mount(el, s.bulk_parent ? html`<p>This pack is repacked from <a href="#/skus/${s.bulk_parent.id}" data-act="sku-jump" data-id="${s.bulk_parent.id}"><b>${s.bulk_parent.name}</b></a>. Cost follows the bulk price plus packaging. Vendor prices are shown on that parent SKU.</p>`
      : s.packs.length ? html`<table class="tbl"><thead><tr><th>Pack</th><th class="r">MRP</th><th>Status</th></tr></thead><tbody>${s.packs.map(p => html`<tr class="click" data-act="sku-jump" data-id="${p.id}"><td><b>${p.name}</b></td><td class="r">${rs(p.mrp_paise / 100)}</td><td><span class="pill ${p.status}">${p.status}</span></td></tr>`)}</tbody></table>` : html`<p class="muted">This SKU has no repacked variants.</p>`);
  } else if (tab === "sales") {
    const x = s.sales30, w = x.weekly.map(q => q.net);
    mount(el, html`<div class="stats"><div><b>${inr(x.net)}</b><span>Net sales, 30 days</span></div><div><b>${num(x.qty)}${s.base_uom === "g" ? " g" : ""}</b><span>${s.base_uom === "g" ? "Weight sold" : "Units sold"}</span></div><div><b>${num(x.stores)}</b><span>Stores selling</span></div></div>
      <h2 style="margin:6px 0">Weekly net sales</h2>${spark(w, 640, 90)}`);
  } else {
    mount(el, s.history.length ? html`<table class="tbl"><tbody>${s.history.map(h => html`<tr><td class="small">${String(h.ts).slice(0, 16).replace("T", " ")}</td><td><b>${h.action.replace("_", " ")}</b> by ${h.by_user || "system"}<div class="small muted">${h.before} to ${h.after}</div></td></tr>`)}</tbody></table>` : html`<p class="muted">No changes recorded yet.</p>`);
  }
}
acts["sku-jump"] = (a, e) => { e.preventDefault(); openSku(+a.dataset.id, true); };
acts["sku-save"] = async () => {
  const np = document.querySelector("#np").value, ns = document.querySelector("#ns").value, body = { reason: document.querySelector("#nr").value || null };
  if (ns) body.status = ns; if (np) body[cur.base_uom === "g" ? "price_per_kg_paise" : "mrp_paise"] = Math.round(np * 100);
  try { await api("/skus/" + cur.id, { method: "PATCH", body }); toast("Saved and logged"); await openSku(cur.id, true); load(); } catch (e) { toast(e.message, true); }
};

acts["sku-import"] = () => {
  document.body.insertAdjacentHTML("beforeend", `<div class="scrim" data-act="close"></div><div class="modal glass"><div class="row" style="justify-content:space-between"><h1 style="font-size:22px">Import prices</h1><button class="icon" data-act="close">✕</button></div>
  <p class="muted small" style="margin:8px 0 12px">Paste or upload a CSV with <b>sku_code</b> and <b>mrp_rupees</b> (packed) or <b>price_per_kg_rupees</b> (loose), plus an optional <b>status</b>. Nothing is saved until every row passes.</p>
  <input type="file" id="f" accept=".csv,text/csv" class="input" style="margin-bottom:8px"><textarea class="input" id="csv" placeholder="sku_code,mrp_rupees,status"></textarea>
  <div class="row" style="margin-top:12px"><button class="btn" data-act="imp-check">Check</button><button class="btn pri" data-act="imp-apply" id="ia" disabled>Apply</button></div><div id="ir" style="margin-top:14px"></div></div>`);
  document.querySelector("#f").onchange = async e => { document.querySelector("#csv").value = await e.target.files[0].text(); };
};
async function imp(apply) {
  const c = document.querySelector("#csv").value; if (!c.trim()) return toast("Add a CSV first", true);
  try {
    const r = await api("/skus/import", { method: "POST", body: { csv: c, apply } });
    mount(document.querySelector("#ir"), html`<p><b>${r.rows}</b> rows read, <b>${r.ok}</b> pass, <b>${r.errors.length}</b> with errors. ${r.applied ? html`<span class="pill active">Applied</span>` : ""}</p>
      ${r.errors.length ? html`<table class="tbl"><tbody>${r.errors.map(e => html`<tr><td>Row ${e.row}</td><td>${e.code}</td><td style="color:var(--bad)">${e.error}</td></tr>`)}</tbody></table>` : ""}`);
    document.querySelector("#ia").disabled = !(r.ok > 0 && !r.errors.length && !r.applied);
    if (r.applied) { toast("Prices updated and logged"); load(); }
  } catch (e) { toast(e.message, true); }
}
acts["imp-check"] = () => imp(false); acts["imp-apply"] = () => imp(true);
