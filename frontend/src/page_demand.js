import { html, raw, out, inr, pct, num, deltaPill, esc, dmy } from "./ui.js";
import { api, acts, mount, toast } from "./core.js";

const st = { scope: "chain", key: "", wh: "", cat: "", urgency: "", page: 1, city: "" };
let root = null, opts = null;
const SIZE = 12;
const qty = (q, uom) => uom === "g" ? (q >= 1000 ? num(Math.round(q / 100) / 10) + " kg" : q + " g") : num(q) + " units";
const lakh = p => inr(p);
const URG = { critical: ["warn", "Critical"], soon: ["t", "This week"], plan: ["", "Plan"] };

export async function render(el) {
  root = el; Object.assign(st, { page: 1 });
  opts = await api("/demand/options");
  mount(el, html`<div class="head"><div><div class="eyebrow">Module 6</div><h1>Demand and replenishment</h1><p id="dasof" class="muted">Loading</p></div>
    <div class="row"><select class="input" id="dscope"><option value="chain|">Whole chain</option>${opts.categories.map(c => html`<option value="category|${c.code}">${c.name}</option>`)}${opts.cities.map(c => html`<option value="city|${c}">${c}</option>`)}</select></div></div>
    <div class="kpis" id="dk">${[1, 2, 3, 4, 5].map(() => html`<div class="kpi glass"><div class="sk" style="height:70px"></div></div>`)}</div>
    <div class="cols"><div class="card glass"><div class="ct"><h2>Sales: last 12 weeks and the next 8</h2><span class="small muted" id="dscl">Weekly, tax inclusive</span></div><div class="chart" id="dchart"></div></div>
    <div class="card glass"><div class="ct"><h2>Festival sensitivity</h2><span class="small muted">Learned from sales</span></div><div class="bars wide" id="dbeta"></div><p class="small muted" style="margin-top:10px" id="dcal"></p></div></div>
    ${opts.can_buy ? html`<div class="card solid" style="margin-bottom:14px"><div class="ct"><h2>Buy suggestions</h2><div class="row"><div class="seg" id="dug"><button data-act="d-urg" data-v="" class="on">All</button><button data-act="d-urg" data-v="critical">Critical</button><button data-act="d-urg" data-v="soon">This week</button><button data-act="d-urg" data-v="plan">Plan</button></div>
    <select class="input" id="dwh"><option value="">All warehouses</option>${opts.warehouses.map(w => html`<option value="${w.id}">${w.name}</option>`)}</select><select class="input" id="dcat"><option value="">All categories</option>${opts.categories.map(c => html`<option value="${c.code}">${c.name}</option>`)}</select></div></div><div id="dsug"></div></div>` : ""}
    <div class="cols eq">${opts.can_buy ? html`<div class="card solid"><div class="ct"><h2>Gift box components</h2><span class="small muted">Next 8 weeks</span></div><div id="dkits"></div></div>` : ""}
    <div class="card glass"><div class="ct"><h2>How accurate is this</h2><span class="small muted">Backtest on the last 4 weeks</span></div><div id="dacc"></div></div></div>
    <div class="card solid"><div class="ct"><h2>Store minimum and maximum</h2><select class="input" id="dcity"><option value="">All cities</option>${opts.cities.map(c => html`<option>${c}</option>`)}</select></div><div id="dmm"></div></div>`);
  el.querySelector("#dscope").onchange = e => { [st.scope, st.key] = e.target.value.split("|"); loadChart(); };
  if (opts.can_buy) {
    el.querySelector("#dwh").onchange = e => { st.wh = e.target.value; st.page = 1; loadSug(); };
    el.querySelector("#dcat").onchange = e => { st.cat = e.target.value; st.page = 1; loadSug(); };
  }
  el.querySelector("#dcity").onchange = e => { st.city = e.target.value; loadMM(); };
  loadTop(); loadChart(); loadMM(); if (opts.can_buy) { loadSug(); loadKits(); }
}

const alive = id => root && root.querySelector(id);

async function loadTop() {
  const [s, a, f] = await Promise.all([api("/demand/summary"), api("/demand/accuracy"), api("/demand/festivals")]);
  if (!alive("#dk")) return;
  root.querySelector("#dasof").textContent = `Forecast built ${new Date(s.run_at.replace(" ", "T")).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })} from sales through ${new Date(s.cutoff + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "long" })}. Synthetic demo data. Stock position is modelled until Module 4.`;
  mount(root.querySelector("#dk"), html`
    <div class="kpi glass"><div class="l">Forecast, next 4 weeks</div><div class="v">${inr(s.next4)}</div><div class="s">${deltaPill(s.delta, " vs last 4 weeks")}</div></div>
    <div class="kpi glass"><div class="l">Festival peak week</div><div class="v">+${(s.peak_lift * 100).toFixed(0)}%</div><div class="s">Week of ${dmy(s.peak_week)} against the same week with no festival</div></div>
    <div class="kpi glass"><div class="l">Accuracy by city and category</div><div class="v">${pct(s.accuracy, 0)}</div><div class="s">A flat average scores ${pct(1 - s.wape_flat, 0)}. Store and SKU level is ${pct(1 - s.wape_store_sku, 0)}</div></div>
    <div class="kpi glass"><div class="l">Open buy suggestions</div><div class="v">${num(s.open)}</div><div class="s">${inr(s.open_value)}. ${num(s.critical)} critical</div></div>
    <div class="kpi glass"><div class="l">Gift boxes at risk</div><div class="v">${num(s.kits_at_risk)}</div><div class="s">of ${num(s.kits_total)} gift boxes in the forecast</div></div>`);
  const mx = Math.max(...a.beta.map(b => b.sensitivity), .01);
  mount(root.querySelector("#dbeta"), html`${a.beta.slice().sort((x, y) => y.sensitivity - x.sensitivity).map(b => html`<div class="r"><span title="${b.name}">${b.name}</span><div class="b"><i style="width:${(b.sensitivity / mx * 100).toFixed(1)}%"></i></div><span class="num r">+${(b.sensitivity * 100).toFixed(0)}%</span></div>`)}`);
  const d = f.calendar.find(x => x.name.startsWith("Diwali"));
  root.querySelector("#dcal").textContent = `Sales lift per unit of calendar intensity. At the Diwali peak the calendar intensity is about ${d ? d.uplift.toFixed(1) : "1"}, so gift boxes are planned at roughly ${((1 + (a.beta.find(b => b.code === "GFT")?.sensitivity || 0)) * 100 - 100).toFixed(0)}% above normal.`;
  mount(root.querySelector("#dacc"), html`<div class="tblwrap"><table class="tbl"><thead><tr><th>Level</th><th class="r">Error</th><th class="r">Flat average</th><th class="r">Bias</th></tr></thead><tbody>
    ${[["city_category_week", "City and category, weekly"], ["warehouse_sku_week", "Warehouse and SKU, weekly"], ["store_sku_week", "Store and SKU, weekly"]].map(([k, l]) => html`<tr><td>${l}</td><td class="r">${pct(a.method.levels[k].wape, 1)}</td><td class="r">${pct(a.method.levels[k].wape_flat, 1)}</td><td class="r">${pct(a.method.levels[k].bias, 1)}</td></tr>`)}</tbody></table></div>
    <p class="small muted" style="margin-top:8px">Error is the sum of absolute misses over the sum of actuals, in rupees at list price. The forecast was built from data up to ${dmy(a.method.cutoff)} and scored on the four weeks after. The forecast runs ${pct(Math.abs(s.bias), 0)} ${s.bias < 0 ? "low" : "high"} overall because it trails a rising trend. The 80% band covered ${pct(a.method.band.coverage, 0)} of cells worth over ₹200.</p>
    <details style="margin-top:8px"><summary class="small">What this rests on</summary><ul class="small muted" style="margin:8px 0 0 18px">${a.assumptions.map(x => html`<li>${x}</li>`)}<li>The festival shape in the model is the same shape the calendar uses, so this score is better than real data would give.</li></ul></details>`);
}

function chart(el, d) {
  const all = [...d.actual.map(x => ({ ...x, a: 1 })), ...d.forecast.map(x => ({ ...x, a: 0 }))];
  const W = Math.max(320, el.clientWidth), H = 280, L = 60, R = 10, T = 14, B = 28, n = all.length, xs = i => L + (i + .5) / n * (W - L - R);
  const mx = Math.max(...all.map(x => x.upper || x.value)) * 1.08, y = v => T + (1 - v / mx) * (H - T - B);
  let g = ""; for (let i = 0; i <= 4; i++) { const v = mx * i / 4; g += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" stroke-dasharray="3 4"/><text x="${L - 8}" y="${y(v) + 4}" text-anchor="end" font-size="11" fill="var(--muted)">${esc(inr(v))}</text>`; }
  const na = d.actual.length, fx = d.forecast.map((x, i) => xs(na + i));
  const act = d.actual.map((x, i) => `${i ? "L" : "M"}${xs(i).toFixed(1)},${y(x.value).toFixed(1)}`).join("");
  const fl = [d.actual[na - 1] && { x: xs(na - 1), v: d.actual[na - 1].value }, ...d.forecast.map((x, i) => ({ x: fx[i], v: x.value }))].filter(Boolean).map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)},${y(p.v).toFixed(1)}`).join("");
  const band = d.forecast.length ? d.forecast.map((x, i) => `${i ? "L" : "M"}${fx[i].toFixed(1)},${y(x.upper).toFixed(1)}`).join("") + d.forecast.slice().reverse().map((x, i) => `L${fx[d.forecast.length - 1 - i].toFixed(1)},${y(x.lower).toFixed(1)}`).join("") + "Z" : "";
  const step = Math.max(1, Math.round(n / 7)), xl = all.map((x, i) => i % step ? "" : `<text x="${xs(i)}" y="${H - 8}" text-anchor="middle" font-size="11" fill="var(--muted)">${esc(dmy(x.week))}</text>`).join("");
  let lastX = -99; const fest = d.festivals.map(f => { const i = all.findIndex((x, k) => f.peak >= x.week && (k === n - 1 || f.peak < all[k + 1].week)); if (i < 0 || f.peak < all[0].week) return ""; const lab = xs(i) - lastX > 80; if (lab) lastX = xs(i); return `<line x1="${xs(i)}" x2="${xs(i)}" y1="${T}" y2="${H - B}" stroke="var(--primary)" stroke-width="1.2" stroke-dasharray="4 3" opacity=".7"/>${lab ? `<text x="${xs(i) + 4}" y="${T + 11}" font-size="10.5" fill="var(--primary-text)" font-weight="600">${esc(f.name)}</text>` : ""}`; }).join("");
  const sep = `<line x1="${(xs(na - 1) + xs(na)) / 2}" x2="${(xs(na - 1) + xs(na)) / 2}" y1="${T}" y2="${H - B}" stroke="var(--text)" stroke-opacity=".25"/>`;
  const dots = all.map((x, i) => `<circle cx="${xs(i)}" cy="${y(x.value)}" r="9" fill="transparent"><title>${esc(dmy(x.week))}: ${esc(inr(x.value))}${x.a ? " actual" : ` forecast, ${esc(inr(x.lower))} to ${esc(inr(x.upper))}`}</title></circle>`).join("");
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" height="${H}">${g}${xl}${fest}${sep}<path d="${band}" fill="var(--primary)" fill-opacity=".16"/><path d="${act}" fill="none" stroke="var(--primary-text)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/><path d="${fl}" fill="none" stroke="var(--primary)" stroke-width="2.4" stroke-dasharray="6 4" stroke-linecap="round"/>${dots}</svg>`;
}

async function loadChart() {
  const d = await api(`/demand/forecast?scope=${st.scope}&key=${encodeURIComponent(st.key)}`);
  const el = alive("#dchart"); if (!el) return;
  window.__dChart = () => alive("#dchart") && chart(root.querySelector("#dchart"), d); window.__dChart(); addEventListener("resize", () => window.__dChart && window.__dChart());
  root.querySelector("#dscl").textContent = "Solid is actual. Dashed is forecast with an 80% band. Weekly, tax inclusive.";
}

async function loadSug() {
  const r = await api(`/demand/suggestions?wh=${st.wh || 0}&cat=${st.cat}&urgency=${st.urgency}&page=${st.page}&size=${SIZE}`);
  if (!alive("#dsug")) return;
  const pages = Math.max(1, Math.ceil(r.total / SIZE)), c = r.counts;
  mount(root.querySelector("#dsug"), html`<div class="stats"><div><span class="small muted">Critical</span><b>${num(c.critical?.n || 0)}</b><span class="small muted">${inr(c.critical?.value || 0)}</span></div><div><span class="small muted">Order this week</span><b>${num(c.soon?.n || 0)}</b><span class="small muted">${inr(c.soon?.value || 0)}</span></div><div><span class="small muted">Plan</span><b>${num(c.plan?.n || 0)}</b><span class="small muted">${inr(c.plan?.value || 0)}</span></div></div>
    <div class="tblwrap" style="max-height:520px"><table class="tbl"><thead><tr><th>SKU and warehouse</th><th class="r">Stock lasts</th><th class="r">Lead time</th><th class="r">Buy</th><th>Vendor</th><th class="r">Value</th><th></th></tr></thead><tbody>
    ${r.items.map(x => html`<tr><td><b>${x.name}</b><div class="small muted">${x.wh_name}. ${x.reason}</div></td><td class="r"><span class="pill ${URG[x.urgency][0]}">${URG[x.urgency][1]}</span><div class="small muted">${x.cover_days >= 900 ? "no demand" : Math.round(x.cover_days) + " days"}</div></td><td class="r">${x.lead_time_days} d<div class="small muted">order by ${dmy(String(x.order_by).slice(0, 10))}</div></td>
    <td class="r">${qty(x.approved_qty || x.suggested_qty, x.base_uom)}<div class="small muted">have ${qty(x.on_hand, x.base_uom)}${x.on_order ? ", on order " + qty(x.on_order, x.base_uom) : ""}</div></td><td>${x.vendor || ""}<div class="small muted">${x.country || ""}, before freight and duty</div></td><td class="r" style="white-space:nowrap">${inr(x.value_paise)}</td>
    <td>${x.status === "open" ? (opts.can_approve ? html`<button class="btn pri" style="padding:3px 9px" data-act="d-dec" data-id="${x.id}" data-v="approve">Approve</button> <button class="btn" style="padding:3px 9px" data-act="d-dec" data-id="${x.id}" data-v="reject">Reject</button>` : "") : html`<span class="pill ${x.status === "approved" ? "active" : ""}">${x.status}</span>`}</td></tr>`)}
    ${r.items.length ? "" : html`<tr><td colspan="7" class="muted" style="padding:26px;text-align:center">Nothing open for this filter.</td></tr>`}</tbody></table></div>
    <div class="row" style="justify-content:space-between;margin-top:8px"><span class="small muted">${num(r.total)} suggestions worth ${inr(r.value)}. Approving here records the decision. Approved lines become draft POs from the Procurement screen. Suggestions follow live warehouse stock and close when covered. Orders above ₹${num(opts.po_limit / 100)} need the CEO, finance or admin.</span>
    <span class="row"><button class="btn" data-act="d-page" data-v="-1" ${st.page <= 1 ? "disabled" : ""}>Previous</button><span class="small muted">Page ${st.page} of ${pages}</span><button class="btn" data-act="d-page" data-v="1" ${st.page >= pages ? "disabled" : ""}>Next</button></span></div>`);
}

async function loadKits() {
  const r = await api("/demand/kits"); if (!alive("#dkits")) return;
  mount(root.querySelector("#dkits"), html`<div class="tblwrap" style="max-height:340px"><table class="tbl"><thead><tr><th>Gift box</th><th class="r">Planned</th><th class="r">Can build</th><th>Limited by</th></tr></thead><tbody>
    ${r.items.map(k => html`<tr><td><b>${k.name}</b></td><td class="r">${num(k.units)}</td><td class="r">${num(k.buildable)} <span class="pill ${k.coverage < .9 ? "warn" : "active"}">${pct(k.coverage, 0)}</span></td><td>${k.coverage < 1 ? k.limiting : raw('<span class="muted">covered</span>')}</td></tr>`)}</tbody></table></div><p class="small muted" style="margin-top:8px">${num(r.at_risk)} of ${num(r.total)} gift boxes are below 90%. ${esc(r.note)}</p>`);
}

async function loadMM() {
  const r = await api(`/demand/minmax?city=${encodeURIComponent(st.city)}&size=15`); if (!alive("#dmm")) return;
  mount(root.querySelector("#dmm"), html`<div class="tblwrap" style="max-height:380px"><table class="tbl"><thead><tr><th>Store and SKU</th><th class="r">Now</th><th class="r">Suggested</th><th class="r">Change</th><th></th></tr></thead><tbody>
    ${r.items.map(x => html`<tr><td><b>${x.sku}</b><div class="small muted">${x.store.replace("Dry Fruit House ", "")}, ${x.city}</div></td><td class="r">${qty(x.min_qty, x.base_uom)} to ${qty(x.max_qty, x.base_uom)}</td><td class="r">${qty(x.new_min, x.base_uom)} to ${qty(x.new_max, x.base_uom)}</td><td class="r">${x.change >= 0 ? "+" : ""}${(x.change * 100).toFixed(0)}%</td>
    <td>${opts.can_minmax ? html`<button class="btn" style="padding:3px 9px" data-act="d-mm" data-s="${x.store_id}" data-k="${x.sku_id}">Accept</button>` : ""}</td></tr>`)}
    ${r.items.length ? "" : html`<tr><td colspan="5" class="muted" style="padding:26px;text-align:center">Limits are close to the forecast.</td></tr>`}</tbody></table></div><p class="small muted" style="margin-top:8px">${num(r.total)} of ${num(r.checked)} store and SKU lines differ by 25% or more, showing the largest 15 by value. ${esc(r.note)}</p>`);
}

acts["d-urg"] = a => { st.urgency = a.dataset.v; st.page = 1; document.querySelectorAll("#dug button").forEach(b => b.classList.toggle("on", b.dataset.v === st.urgency)); loadSug(); };
acts["d-page"] = a => { st.page = Math.max(1, st.page + +a.dataset.v); loadSug(); };
acts["d-dec"] = async a => {
  try { const r = await api(`/demand/suggestions/${a.dataset.id}/decision`, { method: "POST", body: { action: a.dataset.v } }); toast(a.dataset.v === "approve" ? "Approved" : "Rejected"); loadSug(); loadTop(); }
  catch (e) { toast(e.message, true); }
};
acts["d-mm"] = async a => {
  try { await api("/demand/minmax", { method: "POST", body: { store_id: +a.dataset.s, sku_id: +a.dataset.k } }); toast("Limits updated"); loadMM(); }
  catch (e) { toast(e.message, true); }
};
