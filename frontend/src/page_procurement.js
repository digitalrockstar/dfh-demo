import { html, raw, out, inr, pct, num, esc, dmy, spark } from "./ui.js";
import { api, acts, mount, toast } from "./core.js";

const st = { sv: "transit", ps: "open", pv: "", pp: 1, mv: "decide", pq: "", pcat: "", pcreep: "", pbp: 1 };
let root = null, opts = null, cur = null;
const dd = s => s ? dmy(String(s).slice(0, 10)) : "n/a";
const qty = (q, u) => u === "g" ? (q >= 1000 ? num(Math.round(q / 100) / 10) + " kg" : q + " g") : num(q) + " units";
const money = (m, c) => (m / 100).toLocaleString("en-IN", { maximumFractionDigits: 0 }) + " " + c;
const rup = p => "₹" + (p / 100).toLocaleString("en-IN", { maximumFractionDigits: p < 10000 ? 2 : 0 });
const PS = { draft: ["", "Draft"], approved: ["t", "Approved"], confirmed: ["t", "Confirmed"], in_transit: ["t", "In transit"], partial: ["warn", "Part received"], received: ["active", "Received"], cancelled: ["", "Cancelled"] };
const pill = s => { const [c, l] = PS[s] || ["", s]; return raw(`<span class="pill ${c}">${esc(l)}</span>`); };
const IS = { pending: ["t", "To decide"], held: ["warn", "On hold"], released: ["active", "Released"], paid: ["active", "Paid"], disputed: ["warn", "Disputed"] };
const ipill = s => { const [c, l] = IS[s] || ["", s]; return raw(`<span class="pill ${c}">${esc(l)}</span>`); };
const COMP = { freight: "Freight", insurance: "Insurance", duty: "Customs duty", sws: "Duty surcharge", clearing: "Clearing agent", port: "Port and CFS", inland: "Haulage to warehouse" };
const TONE = { freight: .55, insurance: .45, duty: .9, sws: .7, clearing: .35, port: .3, inland: .2 };
const dots = (step, n) => raw(`<span class="dots">${Array.from({ length: n }, (_, i) => `<i class="${i < step ? "on" : i === step ? "cur" : ""}"></i>`).join("")}</span>`);
const seg = (id, act, items, on) => html`<div class="seg" id="${id}">${items.map(([v, l]) => html`<button data-act="${act}" data-v="${v}" class="${String(on) === String(v) ? "on" : ""}">${l}</button>`)}</div>`;
const setSeg = (id, v) => root.querySelectorAll(`#${id} button`).forEach(b => b.classList.toggle("on", b.dataset.v === String(v)));
const empty = (n, c = 6) => html`<tr><td colspan="${c}" class="muted" style="padding:24px;text-align:center">${n}</td></tr>`;
const fail = (id, e) => { const n = root && root.querySelector("#" + id); if (n) n.innerHTML = `<p class="muted small" style="padding:16px">Could not load: ${esc(e.message)}</p>`; };

export async function render(el) {
  root = el; opts = await api("/procurement/options");
  mount(el, html`<div class="head"><div><div class="eyebrow">Module 3</div><h1>Procurement and logistics</h1><p class="muted" id="pasof">Synthetic demo data. Landed cost rates and duty are stated assumptions.</p></div>
    <div class="row">${opts.can_po ? html`<button class="btn pri" data-act="p-sug">Create POs from approved buys</button>` : ""}</div></div>
    <div class="kpis" id="pk">${[1, 2, 3, 4, 5].map(() => html`<div class="kpi glass"><div class="sk" style="height:70px"></div></div>`)}</div>
    <div class="card solid" style="margin-bottom:14px"><div class="ct"><h2>Shipment tracker</h2>${seg("psv", "p-sv", [["transit", "In transit"], ["late", "Late"], ["receive", "To receive"], ["all", "All"]], st.sv)}</div><div id="psh"></div></div>
    <div class="card solid" style="margin-bottom:14px"><div class="ct"><h2>Purchase orders</h2><div class="row">${seg("pps", "p-ps", [["open", "Open"], ["received", "Received"], ["", "All"]], st.ps)}
      <select class="input" id="ppv"><option value="">All vendors</option>${opts.vendors.map(v => html`<option value="${v.id}">${v.name}</option>`)}</select></div></div><div id="ppo"></div></div>
    <div class="card solid" style="margin-bottom:14px"><div class="ct"><h2>Price book and landed cost</h2><div class="row"><input class="input" id="ppq" placeholder="Search SKU" autocomplete="off"><select class="input" id="ppc"><option value="">All categories</option>${opts.categories.map(c => html`<option value="${c.code}">${c.name}</option>`)}</select>
      ${seg("ppk", "p-creep", [["", "All SKUs"], ["creep", "Price creep"]], st.pcreep)}</div></div><div id="ppb"></div></div>
    <div class="cols eq"><div class="card solid"><div class="ct"><h2>Vendor scorecard</h2><span class="small muted">Flagged first</span></div><div id="pvd"></div></div>
    <div class="card solid"><div class="ct"><h2>Three-way match</h2>${seg("pmv", "p-mv", [["decide", "Needs decision"], ["ready", "Ready"], ["awaiting", "Awaiting goods"]], st.mv)}</div><div id="pmt"></div></div></div>`);
  el.querySelector("#ppv").onchange = e => { st.pv = e.target.value; st.pp = 1; loadPOs(); };
  let t; el.querySelector("#ppq").oninput = e => { clearTimeout(t); t = setTimeout(() => { st.pq = e.target.value.trim(); st.pbp = 1; loadBook(); }, 250); };
  el.querySelector("#ppc").onchange = e => { st.pcat = e.target.value; st.pbp = 1; loadBook(); };
  loadAll();
}
function loadAll() { loadKpis(); loadShips(); loadPOs(); loadBook(); loadVendors(); loadMatch(); }

async function loadKpis() {
  try {
    const s = await api("/procurement/summary");
    mount(root.querySelector("#pk"), html`
      <div class="kpi glass"><div class="l">Open purchase orders</div><div class="v">${num(s.open_n)}</div><div class="s">${inr(s.open_value)} on order</div></div>
      <div class="kpi glass"><div class="l">Shipments on the way</div><div class="v">${num(s.transit_n)}</div><div class="s">${s.late_n ? html`<span class="pill warn">${s.late_n} late</span> worst ${s.worst_late} days` : "None late"}</div></div>
      <div class="kpi glass"><div class="l">Delivered, not received</div><div class="v">${num(s.awaiting_grn)}</div><div class="s">Waiting for a GRN at the warehouse</div></div>
      <div class="kpi glass"><div class="l">Invoices to decide</div><div class="v">${num(s.decide_n)}</div><div class="s">${inr(s.decide_value)} difference. ${inr(s.overdue_value)} past due</div></div>
      <div class="kpi glass"><div class="l">Landed cost over price</div><div class="v">${s.landed_premium == null ? "n/a" : pct(s.landed_premium, 0)}</div><div class="s">Imports cleared in 90 days (${num(s.landed_n)}). Duty is assumed</div></div>`);
  } catch (e) { fail("pk", e); }
}

async function loadShips() {
  try {
    const r = await api(`/procurement/shipments?view_=${st.sv}&size=10`);
    mount(root.querySelector("#psh"), html`<div class="tblwrap" style="max-height:420px"><table class="tbl"><thead><tr><th>Shipment</th><th>Vendor and PO</th><th>To</th><th>Progress</th><th class="r">ETA</th><th>Status</th></tr></thead><tbody>
      ${r.items.map(x => html`<tr class="click" data-act="p-open" data-id="${x.po_id}"><td><b>${x.ship_no}</b><div class="small muted">${x.mode}${x.container_no ? ", " + x.container_no : ""}</div></td><td>${x.vendor}<div class="small muted">${x.po_no}, ${inr(x.value_inr)}</div></td><td>${x.wh_name}</td>
      <td>${dots(x.step, x.steps)}<div class="small muted">${opts.stage[x.status]}</div></td><td class="r">${dd(x.eta)}${x.late_days > 2 ? html`<div><span class="pill warn">${x.late_days} d late</span></div>` : ""}</td>
      <td>${x.status === "customs" && x.stuck >= 5 ? html`<span class="pill warn">customs ${x.stuck} d</span>` : x.status === "delivered" ? html`<span class="pill t">to receive</span>` : html`<span class="pill">${opts.stage[x.status]}</span>`}</td></tr>`)}
      ${r.items.length ? "" : empty("Nothing here.")}</tbody></table></div><p class="small muted" style="margin-top:8px">${num(r.total)} shipments in this view. Late means more than 2 days past the ETA.</p>`);
  } catch (e) { fail("psh", e); }
}

async function loadPOs() {
  try {
    const r = await api(`/procurement/pos?status=${st.ps}${st.pv ? "&vendor=" + st.pv : ""}&page=${st.pp}&size=10`), pages = Math.max(1, Math.ceil(r.total / r.size));
    mount(root.querySelector("#ppo"), html`<div class="tblwrap" style="max-height:440px"><table class="tbl"><thead><tr><th>PO</th><th>Vendor</th><th>Destination</th><th class="r">Ordered</th><th class="r">Expected</th><th class="r">Value</th><th>Status</th></tr></thead><tbody>
      ${r.items.map(x => html`<tr class="click" data-act="p-open" data-id="${x.id}"><td><b>${x.po_no}</b><div class="small muted">${x.n_lines} lines</div></td><td>${x.vendor}<div class="small muted">${x.country}</div></td><td>${x.wh_name}</td><td class="r">${dd(x.order_date)}</td><td class="r">${dd(x.expected_date)}</td>
      <td class="r">${inr(x.value_inr)}<div class="small muted">${x.currency === "INR" ? "" : money(x.total_minor, x.currency)}</div></td><td>${pill(x.status)} ${x.late ? raw('<span class="pill warn">late</span>') : ""}</td></tr>`)}${r.items.length ? "" : empty("No purchase orders.", 7)}</tbody></table></div>
      <div class="row" style="justify-content:space-between;margin-top:8px"><span class="small muted">${num(r.total)} POs worth ${inr(r.value)}</span><div class="row"><button class="btn sm" data-act="p-pg" data-v="-1" ${st.pp <= 1 ? "disabled" : ""}>Previous</button><span class="small muted">${st.pp} of ${pages}</span><button class="btn sm" data-act="p-pg" data-v="1" ${st.pp >= pages ? "disabled" : ""}>Next</button></div></div>`);
  } catch (e) { fail("ppo", e); }
}

async function loadBook() {
  try {
    const r = await api(`/procurement/pricebook?q=${encodeURIComponent(st.pq)}&cat=${st.pcat}&only=${st.pcreep}&page=${st.pbp}&size=8`), pages = Math.max(1, Math.ceil(r.total / 8));
    mount(root.querySelector("#ppb"), html`<div class="tblwrap" style="max-height:420px"><table class="tbl"><thead><tr><th>SKU</th><th class="r">Vendors</th><th>Cheapest landed</th><th class="r">Landed cost</th><th class="r">Spread</th><th>Watch</th></tr></thead><tbody>
      ${r.items.map(x => html`<tr class="click" data-act="p-cmp" data-id="${x.id}"><td><b>${x.name}</b><div class="small muted">${x.code}, ${x.cat}</div></td><td class="r">${x.vendors}</td><td>${x.best}</td><td class="r">${rup(x.best_landed)}<div class="small muted">per ${x.uom === "g" ? "kg" : "unit"}</div></td><td class="r">${pct(x.spread, 0)}</td>
      <td>${x.creep.length ? html`<span class="pill warn">${x.creep.length} vendor${x.creep.length > 1 ? "s" : ""} +${Math.round(Math.max(...x.creep.map(c => c.change)) * 100)}%</span>` : ""}</td></tr>`)}${r.items.length ? "" : empty("No SKUs match.")}</tbody></table></div>
      <div class="row" style="justify-content:space-between;margin-top:8px"><span class="small muted">${num(r.total)} SKUs${st.pcreep ? "" : `, ${num(r.creep_skus)} with a vendor up 10% or more since July`}. ${r.unit_note}</span><div class="row"><button class="btn sm" data-act="p-bp" data-v="-1" ${st.pbp <= 1 ? "disabled" : ""}>Previous</button><span class="small muted">${st.pbp} of ${pages}</span><button class="btn sm" data-act="p-bp" data-v="1" ${st.pbp >= pages ? "disabled" : ""}>Next</button></div></div>`);
  } catch (e) { fail("ppb", e); }
}

async function loadVendors() {
  try {
    const r = await api("/procurement/vendors");
    mount(root.querySelector("#pvd"), html`<div class="tblwrap" style="max-height:420px"><table class="tbl"><thead><tr><th>Vendor</th><th class="r">POs</th><th class="r">On time</th><th class="r">Fill</th><th class="r">Price 3m</th><th>Flags</th></tr></thead><tbody>
      ${r.items.map(x => html`<tr><td><b>${x.name}</b><div class="small muted">${inr(x.value)} ordered${x.payable ? ", " + inr(x.payable) + " payable" : ""}</div></td><td class="r">${x.pos}</td><td class="r">${x.on_time == null ? "n/a" : pct(x.on_time, 0)}</td><td class="r">${x.fill == null ? "n/a" : pct(x.fill, 0)}</td>
      <td class="r">${x.price_3m == null ? "n/a" : (x.price_3m >= 0 ? "+" : "") + pct(x.price_3m, 0)}</td><td>${x.flags.map(f => raw(`<span class="pill warn" style="margin:0 4px 4px 0">${esc(f)}</span>`))}</td></tr>`)}</tbody></table></div>
      <p class="small muted" style="margin-top:8px">${r.flagged} of ${r.total} vendors flagged. ${r.note}</p>`);
  } catch (e) { fail("pvd", e); }
}

async function loadMatch() {
  try {
    const r = await api(`/procurement/match?state=${st.mv}&size=8`), c = r.counts;
    root.querySelectorAll("#pmv button").forEach(b => { const n = c[b.dataset.v]; b.textContent = { decide: "Needs decision", ready: "Ready", awaiting: "Awaiting goods" }[b.dataset.v] + (n != null ? ` (${n})` : ""); });
    mount(root.querySelector("#pmt"), html`<div class="tblwrap" style="max-height:420px"><table class="tbl"><thead><tr><th>Invoice</th><th class="r">Billed</th><th class="r">Difference</th><th style="min-width:190px">Why</th><th></th></tr></thead><tbody>
      ${r.items.map(x => html`<tr><td><b class="click" data-act="p-open" data-id="${x.po_id}" style="cursor:pointer">${x.inv_no}</b><div class="small muted">${x.vendor}, ${x.po_no}</div><div>${ipill(x.status)} ${x.overdue ? raw('<span class="pill warn">past due</span>') : ""}</div></td>
      <td class="r">${inr(x.amount_inr)}<div class="small muted">due ${dd(x.due_date)}</div></td><td class="r">${x.state === "matched" ? raw('<span class="pill active">matched</span>') : x.state === "awaiting" ? raw('<span class="muted">n/a</span>') : (x.variance_inr > 0 ? "+" : "") + inr(x.variance_inr)}</td>
      <td class="small">${x.reason || ""}${x.note ? html`<div class="muted">${x.note}</div>` : ""}</td>
      <td style="white-space:nowrap">${x.state !== "awaiting" && opts.can_release ? html`<button class="btn sm" data-act="p-inv" data-id="${x.id}" data-v="release">Release</button> ` : ""}${opts.can_hold && x.status !== "held" ? html`<button class="btn sm" data-act="p-inv" data-id="${x.id}" data-v="hold">Hold</button> ` : ""}${x.state === "mismatch" && x.variance > 0 && opts.can_hold ? html`<button class="btn sm" data-act="p-inv" data-id="${x.id}" data-v="dispute">Dispute</button>` : ""}</td></tr>`)}${r.items.length ? "" : empty("Nothing in this queue.", 5)}</tbody></table></div>
      <p class="small muted" style="margin-top:8px">Invoice against the PO price on goods accepted, after credit for rejects. Tolerance ${opts.tolerance}%. ${inr(r.at_risk)} of difference is open across all queues.</p>`);
  } catch (e) { fail("pmt", e); }
}

// ---------- drawers and modals ----------
const closeDrawer = () => { document.querySelectorAll(".scrim,.drawer,.modal").forEach(n => n.remove()); };
const closeModal = () => document.querySelectorAll(".modal,.scrim.m2").forEach(n => n.remove());
function drawer(inner) {
  let d = document.querySelector(".drawer");
  if (!d) { document.body.insertAdjacentHTML("beforeend", `<div class="scrim" data-act="p-dclose"></div><aside class="drawer glass wide"></aside>`); d = document.querySelector(".drawer"); }
  d.innerHTML = out(inner); return d;
}
function modal(inner) { document.body.insertAdjacentHTML("beforeend", out(html`<div class="scrim m2" data-act="p-mclose"></div><div class="modal glass">${inner}</div>`)); }
acts["p-dclose"] = closeDrawer; acts["p-mclose"] = closeModal;

async function openPO(id) {
  cur = id;
  try {
    const r = await api(`/procurement/pos/${id}`), p = r.po, a = r.actions, L = r.landed, s = r.shipment, inv = r.invoice;
    drawer(html`<div class="row" style="justify-content:space-between"><div><div class="eyebrow">${p.vendor}, ${p.country}</div><h1>${p.po_no}</h1></div><button class="icon" data-act="p-dclose" aria-label="Close">✕</button></div>
      <div style="margin-top:6px">${pill(p.status)} <span class="small muted">to ${p.wh_name}</span></div>
      <div class="stats"><div><span class="small muted">Value</span><b>${inr(p.value_inr)}</b><span class="small muted">${p.currency === "INR" ? "Rupees" : money(p.total_minor, p.currency) + " at " + p.fx_rate.toFixed(2)}</span></div><div><span class="small muted">Ordered</span><b>${dd(p.order_date)}</b><span class="small muted">Expected ${dd(p.expected_date)}</span></div>
      <div><span class="small muted">Landed cost</span><b>${inr(L.total)}</b><span class="small muted">+${pct(L.premium, 0)} over goods, ${L.basis === "actual" ? "actuals" : "estimate"}</span></div><div><span class="small muted">Terms</span><b>${p.payment_terms_days} days</b><span class="small muted">${p.vtype === "import" ? "Import" : "Domestic"}</span></div></div>
      <div class="row" style="flex-wrap:wrap">${a.includes("approve") ? html`<button class="btn pri" data-act="p-act" data-v="approve">Approve PO</button>` : ""}${a.includes("confirm") ? html`<button class="btn pri" data-act="p-act" data-v="confirm">Vendor confirmed</button>` : ""}${a.includes("book") ? html`<button class="btn" data-act="p-book">Book shipment</button>` : ""}
      ${a.includes("receive") ? html`<button class="btn pri" data-act="p-grn">Receive goods</button>` : ""}${a.includes("invoice") ? html`<button class="btn" data-act="p-newinv">Record invoice</button>` : ""}${a.includes("cancel") ? html`<button class="btn" data-act="p-act" data-v="cancel">Cancel PO</button>` : ""}</div>
      ${p.needs_big && a.includes("approve") ? html`<p class="small muted" style="margin-top:8px">This PO is above ₹25 lakh. Your role cannot approve it.</p>` : ""}
      <div class="sec"><h3>Lines</h3><div class="tblwrap"><table class="tbl"><thead><tr><th>SKU</th><th class="r">Ordered</th><th class="r">Accepted</th><th class="r">Price</th><th class="r">Landed per ${"unit"}</th></tr></thead><tbody>
      ${r.lines.map(l => html`<tr><td><b>${l.name}</b><div class="small muted">${l.code}</div></td><td class="r">${qty(l.qty, l.base_uom)}</td><td class="r">${l.received ? qty(l.accepted, l.base_uom) : "n/a"}${l.rejected ? html`<div class="small" style="color:var(--warn)">${qty(l.rejected, l.base_uom)} rejected</div>` : ""}</td>
      <td class="r">${money(l.price_minor, p.currency)}<div class="small muted">per ${l.base_uom === "g" ? "kg" : "unit"}</div></td><td class="r">${l.base_uom === "g" ? rup(l.landed_unit * 1000) + " /kg" : rup(l.landed_unit)}</td></tr>`)}</tbody></table></div></div>
      <div class="sec"><h3>Shipment</h3>${s ? html`<p class="small"><b>${s.ship_no}</b>, ${s.mode}${s.container_no ? ", " + s.container_no : ""}${s.bl_no ? ", " + s.bl_no : ""}. ETD ${dd(s.etd)}, ETA ${dd(s.eta)}${s.ata ? ", arrived " + dd(s.ata) : ""}.</p>
        <ul class="tl">${r.events.map(e => html`<li><div><b>${opts.stage[e.status]}</b> <span>${dd(e.ts)}</span>${e.note ? html`<div class="small muted">${e.note}</div>` : ""}</div></li>`)}</ul>
        ${(() => { const fl = r.flow, nx = fl[fl.indexOf(s.status) + 1]; return nx && opts.can_po ? html`<div class="frm"><div><label>Note</label><input class="input" id="ev-note" placeholder="Optional"></div><div><label>New ETA</label><input class="input" id="ev-eta" type="date"></div><div style="align-self:end"><button class="btn" data-act="p-ev" data-id="${s.id}" data-v="${nx}">Mark ${opts.stage[nx].toLowerCase()}</button></div></div>` : ""; })()}` : html`<p class="muted small">No shipment booked yet.</p>`}</div>
      <div class="sec"><h3>Landed cost, ${L.basis === "actual" ? "recorded actuals" : "estimate from stated assumptions"}</h3><div class="tblwrap"><table class="tbl"><tbody>${Object.entries(L.components).map(([k, v]) => html`<tr><td>${COMP[k] || k}</td><td class="r">${inr(v, false)}</td></tr>`)}
      <tr><td><b>Goods</b></td><td class="r"><b>${inr(L.goods, false)}</b></td></tr><tr><td><b>Landed total</b></td><td class="r"><b>${inr(L.total, false)}</b></td></tr></tbody></table></div>
      ${s && opts.can_landed && Object.keys(L.components).length ? html`<button class="btn sm" style="margin-top:8px" data-act="p-landed" data-id="${s.id}">Record actual costs</button>` : ""}</div>
      <div class="sec"><h3>Receipts</h3>${r.grns.length ? r.grns.map(g => html`<p class="small"><b>${g.grn_no}</b> at ${g.wh_name}, ${dd(g.received_at)}</p><div class="tblwrap"><table class="tbl"><tbody>${g.lines.map(x => html`<tr><td>${x.name}<div class="small muted">${x.batch_no ? x.batch_no + ", expires " + dd(x.expiry_date) : "No batch recorded"}</div></td><td class="r">${qty(x.qty_accepted, x.base_uom)} of ${qty(x.qty_received, x.base_uom)}${x.qty_rejected ? html`<div class="small" style="color:var(--warn)">${x.reject_reason}</div>` : ""}</td></tr>`)}</tbody></table></div>`) : html`<p class="muted small">Nothing received yet.</p>`}
      ${r.debit_notes.length ? html`<p class="small muted" style="margin-top:8px">Debit notes: ${r.debit_notes.map(d => inr(d.amount_paise)).join(", ")} for rejected goods.</p>` : ""}</div>
      <div class="sec"><h3>Invoice and match</h3>${inv ? html`<p class="small"><b>${inv.inv_no}</b>, ${dd(inv.inv_date)}, due ${dd(inv.due_date)} ${ipill(inv.status)}</p>
        <div class="stats"><div><span class="small muted">Billed</span><b>${money(inv.amount_minor, inv.currency)}</b></div><div><span class="small muted">Goods accepted at PO price</span><b>${money(inv.accepted, inv.currency)}</b></div><div><span class="small muted">Credit for rejects</span><b>${money(inv.debit, inv.currency)}</b></div>
        <div><span class="small muted">Result</span><b>${inv.state === "matched" ? "Matched" : inv.state === "awaiting" ? "Awaiting goods" : (inv.variance > 0 ? "+" : "") + inr(inv.variance_inr)}</b></div></div>${inv.reason ? html`<p class="small">${inv.reason}.</p>` : ""}${inv.note ? html`<p class="small muted">${inv.note}</p>` : ""}` : html`<p class="muted small">No invoice recorded.</p>`}</div>`);
  } catch (e) { toast(e.message, true); }
}
acts["p-open"] = a => openPO(+a.dataset.id);

acts["p-act"] = async a => {
  let note = null, ex = null;
  if (a.dataset.v === "cancel") { note = prompt("Why is this PO cancelled?"); if (!note) return; }
  if (a.dataset.v === "confirm") ex = prompt("Vendor's confirmed delivery date (YYYY-MM-DD), or leave blank to keep the current one") || null;
  try { await api(`/procurement/pos/${cur}/action`, { method: "POST", body: { action: a.dataset.v, note, expected_date: ex } }); toast(`PO ${a.dataset.v === "cancel" ? "cancelled" : a.dataset.v === "approve" ? "approved" : "confirmed"}`); openPO(cur); loadAll(); } catch (e) { toast(e.message, true); }
};

acts["p-book"] = async () => {
  const r = await api(`/procurement/pos/${cur}`), imp = r.po.vtype === "import", d0 = new Date(), iso = n => new Date(d0.getTime() + n * 864e5).toISOString().slice(0, 10);
  modal(html`<h1 style="font-size:22px">Book shipment for ${r.po.po_no}</h1><div class="frm"><div><label>Mode</label><select class="input" id="bk-m">${imp ? html`<option>sea</option><option>air</option>` : html`<option>road</option>`}</select></div>
    ${imp ? html`<div><label>Port of arrival</label><select class="input" id="bk-p">${opts.warehouses.filter(w => w.is_port).map(w => html`<option value="${w.id}">${w.city}</option>`)}</select></div>` : ""}
    <div><label>Departure</label><input class="input" id="bk-e" type="date" value="${iso(imp ? 7 : 1)}"></div><div><label>Arrival</label><input class="input" id="bk-a" type="date" value="${iso(imp ? 45 : 5)}"></div>
    <div><label>${imp ? "Container or AWB" : "Vehicle"}</label><input class="input" id="bk-c"></div><div><label>${imp ? "Bill of lading" : "LR number"}</label><input class="input" id="bk-b"></div></div>
    <div class="row" style="justify-content:flex-end;margin-top:18px"><button class="btn" data-act="p-mclose">Cancel</button><button class="btn pri" data-act="p-book-save">Book</button></div>`);
};
acts["p-book-save"] = async () => {
  const g = i => document.querySelector("#" + i);
  try { await api(`/procurement/pos/${cur}/shipment`, { method: "POST", body: { mode: g("bk-m").value, etd: g("bk-e").value, eta: g("bk-a").value, port_id: g("bk-p") ? +g("bk-p").value : null, container_no: g("bk-c").value || null, bl_no: g("bk-b").value || null } }); closeModal(); toast("Shipment booked"); openPO(cur); loadAll(); } catch (e) { toast(e.message, true); }
};

acts["p-ev"] = async a => {
  try { await api(`/procurement/shipments/${a.dataset.id}/event`, { method: "POST", body: { status: a.dataset.v, note: document.querySelector("#ev-note").value || null, eta: document.querySelector("#ev-eta").value || null } }); toast("Shipment updated"); openPO(cur); loadAll(); } catch (e) { toast(e.message, true); }
};

acts["p-landed"] = async a => {
  const r = await api(`/procurement/pos/${cur}`);
  modal(html`<h1 style="font-size:22px">Actual landed costs</h1><p class="small muted" style="margin:6px 0 0">Enter rupees as billed. Costs you leave unchanged are saved as shown.</p><div class="frm">${Object.entries(r.landed.components).map(([k, v]) => html`<div><label>${COMP[k]}</label><input class="input lc" data-k="${k}" type="number" min="0" step="0.01" value="${(v / 100).toFixed(2)}"></div>`)}</div>
    <div class="row" style="justify-content:flex-end;margin-top:18px"><button class="btn" data-act="p-mclose">Cancel</button><button class="btn pri" data-act="p-landed-save" data-id="${a.dataset.id}">Save</button></div>`);
};
acts["p-landed-save"] = async a => {
  const c = {}; document.querySelectorAll(".lc").forEach(i => c[i.dataset.k] = +i.value || 0);
  try { await api(`/procurement/shipments/${a.dataset.id}/landed`, { method: "POST", body: { components: c } }); closeModal(); toast("Landed cost recorded"); openPO(cur); loadKpis(); } catch (e) { toast(e.message, true); }
};

acts["p-grn"] = async () => {
  const r = await api(`/procurement/pos/${cur}`), exp = new Date(Date.now() + 240 * 864e5).toISOString().slice(0, 10);
  modal(html`<h1 style="font-size:22px">Receive goods for ${r.po.po_no}</h1><p class="small muted" style="margin:6px 0 10px">Quantities in kg for loose SKUs and units for packs. Accepted goods need an expiry date and become a batch.</p>
    <div style="max-height:52vh;overflow:auto">${r.lines.map(l => { const left = Math.max(0, l.qty - l.received), k = l.base_uom === "g"; return html`<div class="frm gl" data-sku="${l.sku_id}" data-k="${k ? 1 : 0}" style="border-top:1px solid var(--line);padding-top:10px"><div style="grid-column:1/-1"><b>${l.name}</b> <span class="small muted">${qty(left, l.base_uom)} still due</span></div>
      <div><label>Received</label><input class="input g-r" type="number" min="0" step="${k ? .1 : 1}" value="${k ? (left / 1000).toFixed(1) : left}"></div><div><label>Rejected</label><input class="input g-j" type="number" min="0" step="${k ? .1 : 1}" value="0"></div>
      <div><label>Reject reason</label><input class="input g-w" placeholder="If any rejected"></div><div><label>Expiry</label><input class="input g-e" type="date" value="${exp}"></div></div>`; })}</div>
    <div class="row" style="justify-content:flex-end;margin-top:14px"><button class="btn" data-act="p-mclose">Cancel</button><button class="btn pri" data-act="p-grn-save">Post receipt</button></div>`);
};
acts["p-grn-save"] = async () => {
  const lines = [...document.querySelectorAll(".gl")].map(n => { const m = n.dataset.k === "1" ? 1000 : 1, f = c => Math.round((+n.querySelector(c).value || 0) * m);
    return { sku_id: +n.dataset.sku, qty_received: f(".g-r"), qty_rejected: f(".g-j"), reject_reason: n.querySelector(".g-w").value || null, expiry_date: n.querySelector(".g-e").value || null }; }).filter(x => x.qty_received > 0);
  try { const r = await api(`/procurement/pos/${cur}/grn`, { method: "POST", body: { lines } }); closeModal(); toast(`${r.grn_no} posted`); openPO(cur); loadAll(); } catch (e) { toast(e.message, true); }
};

acts["p-newinv"] = async () => {
  const r = await api(`/procurement/pos/${cur}`);
  modal(html`<h1 style="font-size:22px">Record vendor invoice</h1><div class="frm"><div><label>Invoice number</label><input class="input" id="vi-n"></div><div><label>Invoice date</label><input class="input" id="vi-d" type="date" value="${new Date().toISOString().slice(0, 10)}"></div>
    <div><label>Amount in ${r.po.currency}</label><input class="input" id="vi-a" type="number" min="0" step="0.01"></div></div><div class="row" style="justify-content:flex-end;margin-top:18px"><button class="btn" data-act="p-mclose">Cancel</button><button class="btn pri" data-act="p-newinv-save">Save</button></div>`);
};
acts["p-newinv-save"] = async () => {
  try { await api(`/procurement/pos/${cur}/invoice`, { method: "POST", body: { inv_no: document.querySelector("#vi-n").value, inv_date: document.querySelector("#vi-d").value, amount: +document.querySelector("#vi-a").value } }); closeModal(); toast("Invoice recorded"); openPO(cur); loadAll(); } catch (e) { toast(e.message, true); }
};

acts["p-inv"] = async a => {
  const v = a.dataset.v, note = prompt(v === "hold" ? "Why is it on hold?" : v === "dispute" ? "What is being disputed?" : "Note (required if the invoice does not match)");
  if (note === null) return;
  try { await api(`/procurement/invoices/${a.dataset.id}/decision`, { method: "POST", body: { action: v, note: note || null } }); toast(v === "release" ? "Released for payment" : v === "hold" ? "Put on hold" : "Disputed, debit note raised"); loadMatch(); loadKpis(); if (document.querySelector(".drawer")) openPO(cur); } catch (e) { toast(e.message, true); }
};

acts["p-cmp"] = async a => {
  try {
    const r = await api(`/procurement/compare/${a.dataset.id}`), mx = Math.max(...r.vendors.map(v => v.landed)), u = r.unit;
    drawer(html`<div class="row" style="justify-content:space-between"><div><div class="eyebrow">${r.sku.code}, ${r.sku.cat_name}</div><h1>${r.sku.name}</h1></div><button class="icon" data-act="p-dclose" aria-label="Close">✕</button></div>
      <p class="small muted" style="margin-top:6px">Landed cost per ${u}, ranked. The bar shows goods first, then each cost added on top.</p>
      <div class="tblwrap" style="margin-top:12px"><table class="tbl"><thead><tr><th>Vendor</th><th>Landed per ${u}</th><th class="r">Against best</th><th class="r">Price 3m</th><th>Trend</th></tr></thead><tbody>
      ${r.vendors.map(v => html`<tr><td><b>${v.rank}. ${v.vendor}</b><div class="small muted">${v.country}, ${v.incoterm}, MOQ ${qty(v.moq, r.sku.base_uom)}, ${v.lead} d lead</div></td>
      <td><div class="stack" style="width:${Math.max(40, v.landed / mx * 100)}%"><i style="width:${v.goods / v.landed * 100}%;background:var(--primary);opacity:.55"></i>${Object.entries(v.components).map(([k, x]) => raw(`<i title="${esc(COMP[k])}" style="width:${x / v.landed * 100}%;background:var(--primary);opacity:${TONE[k] || .5};filter:hue-rotate(${Math.round((TONE[k] || .5) * 60)}deg)"></i>`))}</div>
      <div class="small">${rup(v.landed)} <span class="muted">goods ${rup(v.goods)}</span></div></td><td class="r">${v.rank === 1 ? "Best" : "+" + pct(v.vs_best, 0)}</td><td class="r">${v.change_3m == null ? "n/a" : (v.change_3m >= 0 ? "+" : "") + pct(v.change_3m, 0)}${v.change_3m >= .1 ? raw(' <span class="pill warn">creep</span>') : ""}</td><td>${spark(v.series)}</td></tr>`)}</tbody></table></div>
      <div class="sec"><h3>Recent purchase orders</h3><div class="tblwrap"><table class="tbl"><tbody>${r.recent.map(x => html`<tr><td>${x.po_no}<div class="small muted">${dd(x.order_date)}</div></td><td>${x.vendor}</td><td class="r">${qty(x.qty, r.sku.base_uom)}</td><td class="r">${money(x.price_minor, x.currency)}</td></tr>`)}${r.recent.length ? "" : empty("No POs for this SKU yet.", 4)}</tbody></table></div></div>
      <p class="small muted" style="margin-top:14px">${r.note}</p>`);
  } catch (e) { toast(e.message, true); }
};

acts["p-sug"] = async () => {
  try {
    const r = await api("/demand/suggestions?status=approved&size=100");
    modal(html`<h1 style="font-size:22px">Approved buy suggestions</h1><p class="small muted" style="margin:6px 0 10px">Lines for the same vendor and warehouse are combined into one draft PO at the current price book price and FX.</p>
      <div class="tblwrap" style="max-height:48vh"><table class="tbl"><thead><tr><th></th><th>SKU</th><th>Warehouse</th><th>Vendor</th><th class="r">Quantity</th></tr></thead><tbody>${r.items.map(x => html`<tr><td><input type="checkbox" class="sg" value="${x.id}" checked></td><td>${x.name}</td><td>${x.wh_name}</td><td>${x.vendor || "none"}</td><td class="r">${qty(x.approved_qty, x.base_uom)}</td></tr>`)}${r.items.length ? "" : empty("No approved suggestions are waiting. Approve some in Demand and replenishment first.", 5)}</tbody></table></div>
      <div class="row" style="justify-content:flex-end;margin-top:14px"><button class="btn" data-act="p-mclose">Cancel</button><button class="btn pri" data-act="p-sug-save">Create draft POs</button></div>`);
  } catch (e) { toast(e.message, true); }
};
acts["p-sug-save"] = async () => {
  const ids = [...document.querySelectorAll(".sg:checked")].map(i => +i.value);
  try { const r = await api("/procurement/pos/from-suggestions", { method: "POST", body: { suggestion_ids: ids } }); closeModal(); toast(`Created ${r.created.length} draft PO${r.created.length > 1 ? "s" : ""}`); st.ps = "open"; st.pp = 1; setSeg("pps", "open"); loadAll(); } catch (e) { toast(e.message, true); }
};

acts["p-sv"] = a => { st.sv = a.dataset.v; setSeg("psv", st.sv); loadShips(); };
acts["p-ps"] = a => { st.ps = a.dataset.v; st.pp = 1; setSeg("pps", st.ps); loadPOs(); };
acts["p-pg"] = a => { st.pp = Math.max(1, st.pp + +a.dataset.v); loadPOs(); };
acts["p-bp"] = a => { st.pbp = Math.max(1, st.pbp + +a.dataset.v); loadBook(); };
acts["p-creep"] = a => { st.pcreep = a.dataset.v; st.pbp = 1; setSeg("ppk", st.pcreep); loadBook(); };
acts["p-mv"] = a => { st.mv = a.dataset.v; setSeg("pmv", st.mv); loadMatch(); };
