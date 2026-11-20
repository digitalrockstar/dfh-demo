import { html, raw, out, inr, pct, num, deltaPill, esc, dmy, donut, donutLegend, prov, rollKpis, splinePath } from "./ui.js";
import { api, acts, mount, toast } from "./core.js";

const PERIODS = [[7, "7 days"], [30, "30 days"], [90, "90 days"], [184, "6 months"]];
const st = { days: 30, region: "", kind: "store", win: 30, sr: "" };
let root = null, opts = null, regions = [], pick = null;
const qty = (q, uom) => uom === "g" ? (q >= 1000 ? (q / 1000).toFixed(q % 1000 ? 1 : 0) + " kg" : q + " g") : num(q) + " units";
const fdate = s => new Date(s.replace(" ", "T")).toLocaleDateString("en-IN", { day: "numeric", month: "short" }) + ", " + s.slice(11, 16);
const qs = () => `days=${st.days}&region=${encodeURIComponent(st.region)}`;

export async function render(el) {
  root = el;
  [opts, regions] = await Promise.all([api("/wastage/options"), api("/ct/filters").then(f => f.regions).catch(() => [])]);
  mount(el, html`<div class="head"><div><div class="eyebrow">Module 5</div><h1>Wastage and shrink</h1><p id="asof" class="muted">Loading</p></div>
    <div class="row"><div class="seg" id="wper">${PERIODS.map(([d, l]) => html`<button data-act="w-days" data-v="${d}" class="${st.days === d ? "on" : ""}">${l}</button>`)}</div>
    <select class="input" id="wreg"><option value="">All regions</option>${regions.map(r => html`<option ${st.region === r ? "selected" : ""}>${r}</option>`)}</select>
    ${opts.can_enter ? html`<button class="btn pri" data-act="w-new">Record loss</button>` : ""}</div></div>
    <div class="bento"><div class="kpis b12" id="wk">${[1, 2, 3, 4, 5].map(() => html`<div class="kpi glass"><div class="sk" style="height:70px"></div></div>`)}</div>
    <div class="card glass b8"><div class="ct"><h2>Loss at cost over time</h2><span class="small muted">Upper line is total, lower line is controllable loss</span></div><div class="chart" id="wtrend"></div></div>
    <div class="card glass b4"><div class="ct"><h2>By reason</h2><span class="small muted">Share of cost</span></div><div id="wreasons"></div></div>
    <div class="card solid b7"><div class="ct"><h2>Locations</h2><div class="seg" id="wkind"><button data-act="w-kind" data-v="store" class="${st.kind === "store" ? "on" : ""}">Stores</button><button data-act="w-kind" data-v="warehouse" class="${st.kind === "warehouse" ? "on" : ""}">Warehouses</button></div></div><div id="wloc"></div></div>
    <div class="card glass b5"><div class="ct"><h2>Top SKUs by loss</h2><div class="seg" id="wsr"><button data-act="w-sr" data-v="" class="${st.sr === "" ? "on" : ""}">All reasons</button><button data-act="w-sr" data-v="EXPIRY" class="${st.sr === "EXPIRY" ? "on" : ""}">Expiry</button></div></div><div class="bars wide" id="wskus"></div></div>
    <div class="card solid b12"><div class="ct"><h2>Near expiry</h2><div class="seg" id="wwin">${[15, 30, 60].map(d => html`<button data-act="w-win" data-v="${d}" class="${st.win === d ? "on" : ""}">${d} days</button>`)}</div></div><div id="wexp"></div></div>
    <div class="card solid b12"><div class="ct"><h2>Recent entries</h2><span class="small muted">Waiting for approval first</span></div><div id="went"></div></div></div>`);
  el.querySelector("#wreg").onchange = e => { st.region = e.target.value; refresh(); };
  refresh();
}

function bars(rows, key = "cost", label = r => r.name, sub = null) {
  const mx = Math.max(1, ...rows.map(r => r[key]));
  return html`${rows.map(r => html`<div class="r"><span title="${label(r)}">${label(r)}</span><div class="b"><i style="width:${(r[key] / mx * 100).toFixed(1)}%"></i></div><span class="num r">${sub ? sub(r) : inr(r[key])}</span></div>`)}${rows.length ? "" : html`<p class="muted small">Nothing recorded in this period.</p>`}`;
}

function chart(el, data) {
  if (!el) return;
  if (!data.length) { el.innerHTML = '<p class="muted small" style="padding:30px">Nothing recorded in this period.</p>'; return; }
  const W = Math.max(320, el.clientWidth), H = 250, L = 56, R = 8, T = 10, B = 26, n = data.length, mx = Math.max(...data.map(d => d.cost)) * 1.1 || 1;
  const xs = i => L + (i + .5) / n * (W - L - R), y = v => T + (1 - v / mx) * (H - T - B); let g = "";
  for (let i = 0; i <= 4; i++) { const v = mx * i / 4; g += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" stroke-dasharray="3 4"/><text x="${L - 8}" y="${y(v) + 4}" text-anchor="end" font-size="11" fill="var(--muted)">${inr(v).replace(".00", "")}</text>`; }
  const step = Math.max(1, Math.round(n / 6));
  const tot = splinePath(data.map((d, i) => [xs(i), y(d.cost)])), ctl = splinePath(data.map((d, i) => [xs(i), y(d.controllable)]));
  const area = tot ? `<path d="${tot}L${xs(n - 1).toFixed(1)},${H - B}L${xs(0).toFixed(1)},${H - B}Z" fill="var(--primary)" fill-opacity=".12"/>` : "";
  const one = n === 1 ? `<circle cx="${xs(0)}" cy="${y(data[0].cost)}" r="3" fill="var(--primary-text)"/>` : "";
  const hits = data.map((d, i) => `<circle cx="${xs(i)}" cy="${y(d.cost)}" r="9" fill="transparent"><title>${esc(dmy(d.date))}: ${esc(inr(d.cost))} lost, ${esc(inr(d.controllable))} controllable</title></circle>`).join("");
  const xl = data.map((d, i) => i % step ? "" : `<text x="${xs(i)}" y="${H - 8}" text-anchor="middle" font-size="11" fill="var(--muted)">${esc(dmy(d.date))}</text>`).join("");
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" height="${H}">${g}${area}<path d="${tot}" fill="none" stroke="var(--primary-text)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="${ctl}" fill="none" stroke="var(--primary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>${one}${hits}${xl}</svg>`;
}

async function refresh() {
  if (!root || !root.querySelector("#wk")) return;
  try {
    const [s, tr, rs, lc, sk] = await Promise.all([api(`/wastage/summary?${qs()}`), api(`/wastage/trend?${qs()}`), api(`/wastage/reasons?${qs()}`), api(`/wastage/locations?${qs()}&kind=${st.kind}`), api(`/wastage/skus?${qs()}&reason=${st.sr}`)]);
    root.querySelector("#asof").textContent = `Data through ${new Date(s.end + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}. Synthetic demo data. Rejected entries are left out.`;
    const kpi = (l, v, sub, k = "sample", ring = null) => html`<div class="kpi glass"><div class="l">${l}${prov(k)}</div><div class="kpv"><div class="v">${v}</div>${ring == null ? "" : donut(ring, 76)}</div><div class="s">${sub}</div></div>`;
    mount(root.querySelector("#wk"), html`${kpi("Lost stock at cost", inr(s.cost), deltaPill(s.delta, ` vs previous ${s.days} days`))}
      ${kpi("Store loss against COGS", pct(s.store_pct_cogs, 2), `${inr(s.store_cost)} across stores in view`, "derived")}
      ${kpi("Controllable share", pct(s.controllable, 0), s.top_reason ? `Largest reason: ${esc(s.top_reason.name)}` : "No entries", "derived", s.controllable == null ? null : s.controllable * 100)}
      ${kpi("Expired or expiring in 30 days", inr(s.expiry_risk.value), `${num(s.expiry_risk.lines)} batch lines across ${num(s.expiry_risk.skus)} SKUs`, "derived")}
      ${kpi("Awaiting approval", num(s.pending.n), `${inr(s.pending.c)} at cost, entries from ₹${num(opts.approval_limit / 100)}`)}`);
    rollKpis(root.querySelector("#wk"));
    const draw = () => chart(root.querySelector("#wtrend"), tr); window.__wTrend = draw; draw(); addEventListener("resize", () => window.__wTrend && window.__wTrend());
    const rr = rs.filter(r => r.cost > 0).map(r => ({ v: r.cost, n: r.name, sh: r.share, ctl: r.ctl })), top = rr.length > 6 ? rr.slice(0, 5) : rr;
    if (rr.length > 6) { const o = rr.slice(5); top.push({ v: o.reduce((t, x) => t + x.v, 0), n: "Other", sh: o.reduce((t, x) => t + x.sh, 0), ctl: true, color: "var(--muted)" }); }
    mount(root.querySelector("#wreasons"), rr.length ? donutLegend(top, x => html`${pct(x.sh, 0)} ${x.ctl ? "" : raw('<span class="muted small">fixed</span>')}`, 150) : html`<p class="muted small">Nothing recorded in this period.</p>`);
    const mt = st.kind === "store" ? "Loss as share of COGS" : "Loss at cost";
    mount(root.querySelector("#wloc"), html`<div class="tblwrap" style="max-height:380px"><table class="tbl"><thead><tr><th>${st.kind === "store" ? "Store" : "Warehouse"}</th><th class="r">${mt}</th><th class="r">Against peers</th><th>Leads with</th></tr></thead><tbody>
      ${lc.rows.map(r => html`<tr><td><b>${r.name}</b><div class="small muted">${r.city}${r.flag ? "" : ""}</div></td><td class="r">${st.kind === "store" ? pct(r.pct, 1) : inr(r.cost)}<div class="small muted">${inr(r.cost)}</div></td><td class="r">${r.vs_peer == null ? "n/a" : r.vs_peer.toFixed(1) + "x"} ${r.flag ? raw('<span class="pill warn">outlier</span>') : ""}</td><td>${r.lead || raw('<span class="muted">n/a</span>')}</td></tr>`)}</tbody></table></div>
      <p class="small muted" style="margin-top:8px">Worst 15 of ${num(lc.total)} in view. Outlier means at least 2x the median and at least ₹1,000 lost. Median is ${st.kind === "store" ? pct(lc.median, 2) + " of COGS" : inr(lc.median)}.</p>`);
    mount(root.querySelector("#wskus"), bars(sk, "cost", r => r.name, r => html`${inr(r.cost)} <span class="muted small">${pct(r.cost ? r.expiry / r.cost : 0, 0)} expiry</span>`));
    loadExpiry(); loadEntries();
  } catch (e) { const a = root.querySelector("#asof"); if (a) a.textContent = "Could not load: " + e.message; }
}

async function loadExpiry() {
  const r = await api(`/wastage/expiry?window=${st.win}&region=${encodeURIComponent(st.region)}`), b = r.buckets;
  mount(root.querySelector("#wexp"), html`<div class="stats"><div><span class="small muted">Already expired</span><b>${inr(b.expired.value)}</b><span class="small muted">${num(b.expired.n)} lines</span></div><div><span class="small muted">Within 15 days</span><b>${inr(b.d15.value)}</b><span class="small muted">${num(b.d15.n)} lines</span></div>
    <div><span class="small muted">16 to 30 days</span><b>${inr(b.d30.value)}</b><span class="small muted">${num(b.d30.n)} lines</span></div><div><span class="small muted">31 to 60 days</span><b>${inr(b.d60.value)}</b><span class="small muted">${num(b.d60.n)} lines</span></div></div>
    <div class="tblwrap" style="max-height:360px"><table class="tbl"><thead><tr><th>SKU and batch</th><th>Location</th><th class="r">Left</th><th class="r">Stock</th><th class="r">At cost</th><th>Markdown</th></tr></thead><tbody>
    ${r.rows.map(x => html`<tr><td><b>${x.sku}</b><div class="small muted">${x.batch_no}, expires ${dmy(String(x.expiry_date).slice(0, 10))}</div></td><td>${x.lname}<div class="small muted">${x.city}</div></td>
    <td class="r">${x.days_left < 0 ? raw('<span class="pill warn">expired</span>') : x.days_left + " d"}</td><td class="r">${qty(x.qty, x.base_uom)}</td><td class="r">${inr(x.value)}</td>
    <td>${x.mid == null ? raw('<span class="muted small">none</span>') : x.mstatus === "open" ? html`<span class="pill t">${x.suggested_pct}% off</span> ${opts.can_mark ? html`<button class="btn" style="padding:3px 9px" data-act="w-mark" data-id="${x.mid}" data-v="accept">Accept</button> <button class="btn" style="padding:3px 9px" data-act="w-mark" data-id="${x.mid}" data-v="dismiss">Dismiss</button>` : ""}` : html`<span class="pill">${x.mstatus}</span>`}</td></tr>`)}
    ${r.rows.length ? "" : html`<tr><td colspan="6" class="muted" style="padding:26px;text-align:center">Nothing in this window.</td></tr>`}</tbody></table></div>
    <p class="small muted" style="margin-top:8px">${num(r.total)} lines within ${st.win} days worth ${inr(r.value)} at cost, showing the largest 40. Largest SKUs: ${r.top_skus.slice(0, 3).map(t => `${t.sku} (${inr(t.value)})`).join(", ") || "none"}.</p>`);
}

async function loadEntries() {
  const r = await api("/wastage/entries?size=12");
  mount(root.querySelector("#went"), html`<div class="tblwrap" style="max-height:420px"><table class="tbl"><thead><tr><th>When</th><th>Location</th><th>SKU</th><th>Reason</th><th class="r">Qty</th><th class="r">At cost</th><th>Status</th></tr></thead><tbody>
    ${r.items.map(x => html`<tr><td>${fdate(x.ts)}</td><td>${x.lname}</td><td>${x.sku}</td><td>${x.reason_name}${x.photo_ref ? raw(' <span class="muted small">photo</span>') : ""}${x.vendor_claim ? raw(' <span class="pill t">vendor claim</span>') : ""}</td><td class="r">${qty(x.qty, x.base_uom)}</td><td class="r">${inr(x.cost_paise)}</td>
    <td>${x.status === "pending" ? html`<span class="pill warn">pending</span> ${opts.can_approve ? html`<button class="btn" style="padding:3px 9px" data-act="w-decide" data-id="${x.id}" data-v="approve">Approve</button> <button class="btn" style="padding:3px 9px" data-act="w-decide" data-id="${x.id}" data-v="reject">Reject</button>` : ""}` : html`<span class="pill ${x.status === "approved" ? "active" : ""}">${x.status}</span>`}</td></tr>`)}</tbody></table></div><p class="small muted" style="margin-top:8px">${num(r.total)} entries in your view.</p>`);
}

function openForm() {
  pick = null;
  document.body.insertAdjacentHTML("beforeend", out(html`<div class="scrim" data-act="w-close"></div><div class="modal glass"><div class="row" style="justify-content:space-between"><h1 style="font-size:22px">Record a loss</h1><button class="icon" data-act="w-close" aria-label="Close">✕</button></div>
    <p class="small muted" style="margin:6px 0 14px">Entries from ₹${num(opts.approval_limit / 100)} at cost wait for approval. Smaller ones post straight away.</p>
    <label class="small muted">Location</label><select class="input" id="wf-loc" style="width:100%">${opts.locations.map(l => html`<option value="${l.id}">${l.name.replace("Dry Fruit House ", "")}${l.type === "warehouse" ? " (warehouse)" : ""}</option>`)}</select>
    <label class="small muted" style="display:block;margin-top:12px">SKU</label><input class="input" id="wf-q" placeholder="Search by name or code" style="width:100%" autocomplete="off"><div id="wf-res" class="small" style="margin-top:6px"></div>
    <div class="row" style="margin-top:12px;align-items:flex-start"><div style="flex:1"><label class="small muted" id="wf-ql">Quantity</label><input class="input" id="wf-qty" type="number" min="1" style="width:100%"></div>
    <div style="flex:2"><label class="small muted">Reason</label><select class="input" id="wf-rs" style="width:100%">${opts.reasons.map(r => html`<option value="${r.code}">${r.name}</option>`)}</select></div></div>
    <label class="small muted" style="display:block;margin-top:12px">Note (optional)</label><input class="input" id="wf-note" style="width:100%">
    <div class="row" style="justify-content:flex-end;margin-top:18px"><button class="btn" data-act="w-close">Cancel</button><button class="btn pri" data-act="w-save">Save entry</button></div></div>`));
  let t; document.querySelector("#wf-q").oninput = e => { clearTimeout(t); t = setTimeout(async () => {
    const v = e.target.value.trim(); if (v.length < 2) return document.querySelector("#wf-res").innerHTML = "";
    const r = await api(`/skus?q=${encodeURIComponent(v)}&size=6`);
    document.querySelector("#wf-res").innerHTML = out(html`${r.items.map(s => html`<button class="chip" style="margin:0 6px 6px 0" data-act="w-sku" data-id="${s.id}" data-n="${s.name}" data-u="${s.base_uom}">${s.name}</button>`)}`);
  }, 220); };
}
const closeForm = () => document.querySelectorAll(".scrim,.modal").forEach(n => n.remove());
acts["w-close"] = closeForm;
acts["w-sku"] = a => { pick = { id: +a.dataset.id, name: a.dataset.n, uom: a.dataset.u }; document.querySelector("#wf-q").value = pick.name; document.querySelector("#wf-res").textContent = ""; document.querySelector("#wf-ql").textContent = pick.uom === "g" ? "Quantity in grams" : "Quantity in units"; };
acts["w-save"] = async () => {
  if (!pick) return toast("Pick a SKU from the search results", true);
  try {
    const r = await api("/wastage/entries", { method: "POST", body: { location_id: +document.querySelector("#wf-loc").value, sku_id: pick.id, qty: +document.querySelector("#wf-qty").value, reason: document.querySelector("#wf-rs").value, note: document.querySelector("#wf-note").value || null } });
    closeForm(); toast(r.status === "pending" ? `Saved at ${inr(r.cost_paise)}. Waiting for approval.` : `Saved at ${inr(r.cost_paise)}.`); refresh();
  } catch (e) { toast(e.message, true); }
};
acts["w-new"] = openForm;
acts["w-days"] = a => { st.days = +a.dataset.v; document.querySelectorAll("#wper button").forEach(b => b.classList.toggle("on", +b.dataset.v === st.days)); refresh(); };
acts["w-kind"] = a => { st.kind = a.dataset.v; document.querySelectorAll("#wkind button").forEach(b => b.classList.toggle("on", b.dataset.v === st.kind)); refresh(); };
acts["w-sr"] = a => { st.sr = a.dataset.v; document.querySelectorAll("#wsr button").forEach(b => b.classList.toggle("on", b.dataset.v === st.sr)); refresh(); };
acts["w-win"] = a => { st.win = +a.dataset.v; document.querySelectorAll("#wwin button").forEach(b => b.classList.toggle("on", +b.dataset.v === st.win)); loadExpiry(); };
acts["w-decide"] = async a => { try { await api(`/wastage/entries/${a.dataset.id}/decision`, { method: "POST", body: { action: a.dataset.v } }); toast(a.dataset.v === "approve" ? "Approved" : "Rejected"); refresh(); } catch (e) { toast(e.message, true); } };
acts["w-mark"] = async a => { try { await api(`/wastage/markdowns/${a.dataset.id}`, { method: "POST", body: { action: a.dataset.v } }); toast(a.dataset.v === "accept" ? "Markdown accepted" : "Dismissed"); loadExpiry(); } catch (e) { toast(e.message, true); } };
