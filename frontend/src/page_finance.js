import { html, raw, out, inr, num, esc, dmy } from "./ui.js";
import { api, acts, mount, toast, S } from "./core.js";

const st = { tab: "overview", days: 30, period: "2026-09", entity: 1, flagged: 0, source: "", page: 1, jperiod: "2026-09", jentity: 1, jpage: 1 };
let root = null, opts = null;
const $ = s => document.querySelector(s);
const MON = p => new Date(p + "-01T00:00:00").toLocaleDateString("en-IN", { month: "short", year: "numeric" });
const TABS = o => [["overview", "Overview", o.can_cash], ["cash", "Cash and settlements", o.can_cash], ["gst", "GST and input credit", o.can_gst], ["payables", "Payables", o.can_pay], ["journal", "Journal", o.can_gst]].filter(t => t[2]);
const pill = (t, c) => html`<span class="pill ${c}">${t}</span>`;
const empty = t => html`<p class="muted small" style="padding:14px 0">${t}</p>`;
const kpi = (l, v, s) => html`<div class="kpi glass"><div class="l">${l}</div><div class="v">${v}</div><div class="s">${s}</div></div>`;
const seg = (id, act, cur, items) => html`<div class="seg" id="${id}">${items.map(([v, l]) => html`<button data-act="${act}" data-v="${v}" class="${String(cur) === String(v) ? "on" : ""}">${l}</button>`)}</div>`;
const flip = (id, v) => document.querySelectorAll(`#${id} button`).forEach(b => b.classList.toggle("on", b.dataset.v === String(v)));
const DAYS = [[7, "7 days"], [30, "30 days"], [60, "60 days"], [90, "90 days"]];

export async function render(el) {
  root = el; opts = await api("/finance/options");
  const tabs = TABS(opts); if (!tabs.find(t => t[0] === st.tab)) st.tab = tabs[0][0];
  mount(el, html`<div class="head"><div><div class="eyebrow">Module 7</div><h1>Finance and tax</h1><p class="muted">Books to ${dmy(opts.end)}. GST rates are assumed at 5 and 18 percent. Filing is tracked here and not sent to the portal.</p></div>
    <div class="row">${seg("ftabs", "f-tab", st.tab, tabs.map(t => [t[0], t[1]]))}</div></div><div id="fbody"><div class="card glass"><div class="sk" style="height:120px"></div></div></div>`);
  load();
}

function load() {
  const f = { overview, cash, gst, payables, journal }[st.tab];
  f().catch(e => { $("#fbody").innerHTML = out(html`<div class="card glass"><p class="muted">${e.message}</p></div>`); });
}

async function overview() {
  const s = await api(`/finance/summary?days=${st.days}`), c = s.cash, t = s.settlements, r = s.recon;
  const k = [kpi("Net cash variance", inr(c.net), `${num(c.big)} shortages of ₹1,000 or more, ${c.not_closed} days not closed`), kpi("Settlement gap", inr(t.gap), `${inr(t.transit)} still in transit`),
    kpi("Open reconciliation items", num(r.n), `${inr(r.v)} unreconciled`)];
  if (s.payables) k.push(kpi("Input credit at risk", inr(s.itc_at_risk), "Books against GSTR-2B"), kpi("Vendor invoices past due", inr(s.payables.overdue), `${inr(s.payables.total)} open in total`));
  mount($("#fbody"), html`<div class="row" style="margin-bottom:12px"><span class="small muted">Window</span>${seg("fdays", "f-days", st.days, DAYS)}</div><div class="kpis">${k}</div>
    ${opts.can_lock ? html`<div class="card solid"><div class="ct"><h2>Month close</h2>${seg("fper", "f-per", st.period, opts.periods.map(p => [p, MON(p)]))}</div><div id="fclose"><div class="sk" style="height:140px"></div></div></div>` : ""}`);
  if (opts.can_lock) closeBoard();
}

async function closeBoard() {
  const r = await api(`/finance/close?period=${st.period}`);
  mount($("#fclose"), html`<div class="tblwrap"><table class="tbl"><thead><tr><th>Entity</th><th>Status</th><th>What is blocking</th><th></th></tr></thead><tbody>${r.rows.map(x => html`<tr><td>${x.entity.code.replace("DFH-", "")}</td>
    <td>${x.locked ? pill("Locked", "active") : x.ready ? pill("Ready to lock", "t") : pill("Blocked", "warn")}</td>
    <td class="small">${x.locked ? html`<span class="muted">Locked ${dmy(String(x.locked_at).slice(0, 10))}</span>` : x.blockers.map(b => html`<div>${b.label}: <span class="muted">${b.detail}</span></div>`)}</td>
    <td>${!x.locked && x.ready ? html`<button class="btn sm pri" data-act="f-lock" data-e="${x.entity.id}">Lock</button>` : ""}</td></tr>`)}</tbody></table></div>`);
}

async function cash() {
  const [cs, se] = await Promise.all([api(`/finance/cash/stores?days=60&flagged=${st.flagged}`), api(`/finance/settlements?days=${st.days}`)]);
  mount($("#fbody"), html`<div class="row" style="margin-bottom:12px"><span class="small muted">Settlement window</span>${seg("fdays", "f-days", st.days, DAYS)}</div>
    <div class="cols eq"><div class="card solid"><div class="ct"><h2>Cash shortages by store</h2>${seg("fflag", "f-flag", st.flagged, [[0, "Largest"], [1, "Weekend pattern"]])}</div>
    <p class="small muted" style="margin-bottom:8px">Last 60 days. A store is flagged when four or more weekend days are short by ₹1,000 or more and they make up most of its shortages. ${cs.flagged} flagged.</p>
    ${cs.rows.length ? html`<div class="tblwrap" style="max-height:360px"><table class="tbl"><thead><tr><th>Store</th><th class="r">Short days</th><th class="r">Weekend</th><th class="r">Short total</th></tr></thead><tbody>${cs.rows.map(r => html`<tr class="click" data-act="f-store" data-id="${r.id}">
      <td>${r.name.replace("Dry Fruit House ", "")}<div class="small muted">${r.city}</div></td><td class="num r">${r.short_days}</td><td class="num r">${r.weekend_short_days}</td><td class="num r">${inr(r.short_total)} ${r.flag ? pill("Pattern", "warn") : ""}</td></tr>`)}</tbody></table></div>` : empty("No shortages in this window.")}</div>
    <div class="card glass"><div class="ct"><h2>Gateway settlements</h2></div>${se.modes.length ? html`<table class="tbl"><thead><tr><th>Mode</th><th class="r">Expected</th><th class="r">Fees</th><th class="r">Gap</th><th class="r">In transit</th></tr></thead><tbody>${se.modes.map(m => html`<tr><td>${m.mode}</td><td class="num r">${inr(m.expected)}</td><td class="num r">${inr(m.fee)}</td><td class="num r">${inr(m.gap)}<div class="small muted">${m.exceptions} items</div></td><td class="num r">${inr(m.transit)}</td></tr>`)}</tbody></table>
    <p class="small muted" style="margin-top:8px">Card fees are assumed at 1.8 percent. UPI carries no fee. Card settles on the second banking day.</p>` : empty("No settlements in this window.")}</div></div>
    <div class="card solid"><div class="ct"><h2>Reconciliation queue</h2>${seg("fsrc", "f-src", st.source, [["", "All"], ["settlement", "Settlements"], ["day_close", "Cash"]])}</div><div id="frecon"></div></div>`);
  recon();
}

async function recon() {
  const r = await api(`/finance/recon?status=open&source=${st.source}&page=${st.page}&size=10`), pages = Math.max(1, Math.ceil(r.total / r.size));
  mount($("#frecon"), r.items.length ? html`<div class="tblwrap" style="max-height:420px"><table class="tbl"><thead><tr><th>Store</th><th>Type</th><th>Business date</th><th class="r">Amount</th><th class="r">Age</th><th></th></tr></thead><tbody>${r.items.map(i => html`<tr><td>${i.name.replace("Dry Fruit House ", "")}<div class="small muted">${i.city}</div></td>
    <td>${i.source === "settlement" ? "Gateway shortfall" : "Cash variance"}<div class="small muted">${i.source_ref}</div></td><td>${dmy(i.business_date)}</td><td class="num r">${inr(-i.amount_paise, false)}</td><td class="num r">${i.age}d</td>
    <td class="r">${opts.can_resolve ? html`<button class="btn sm" data-act="f-res" data-id="${i.id}" data-v="match">${i.source === "settlement" ? "Match" : "Explain"}</button> <button class="btn sm" data-act="f-res" data-id="${i.id}" data-v="write_off">Write off</button>` : ""}</td></tr>`)}</tbody></table></div>
    <div class="row" style="justify-content:space-between;margin-top:10px"><span class="small muted">${num(r.total)} open</span><div class="row"><button class="btn sm" data-act="f-page" data-v="-1" ${st.page <= 1 ? "disabled" : ""}>Previous</button><span class="small muted">Page ${st.page} of ${pages}</span><button class="btn sm" data-act="f-page" data-v="1" ${st.page >= pages ? "disabled" : ""}>Next</button></div></div>` : empty("Nothing open. Every item in this view is reconciled."));
}

async function gst() {
  const o = opts.entities.filter(e => e.state), r = await api(`/finance/gst?entity_id=${st.entity}`);
  mount($("#fbody"), html`<div class="row" style="margin-bottom:12px"><select class="input" id="fent">${o.map(e => html`<option value="${e.id}" ${e.id === st.entity ? "selected" : ""}>${e.name.replace("Dry Fruit House ", "").replace(" (demo)", "")}</option>`)}</select></div>
    <div class="card solid"><div class="ct"><h2>GSTR-3B working</h2><span class="small muted">Output tax less input credit that GSTR-2B supports</span></div><div class="tblwrap"><table class="tbl"><thead><tr><th>Period</th><th class="r">Output tax</th><th class="r">Input credit</th><th class="r">Net payable</th><th class="r">At risk</th><th>Status</th><th>Due</th></tr></thead><tbody>${r.rows.map(g => html`<tr class="click" data-act="f-gd" data-p="${g.period}">
    <td>${MON(g.period)}</td><td class="num r">${inr(g.output_tax)}</td><td class="num r">${inr(g.claimable)}${g.available ? "" : html`<div class="small muted">books, 2B pending</div>`}</td><td class="num r">${inr(g.net_payable)}</td>
    <td class="num r">${g.at_risk ? html`<b>${inr(g.at_risk)}</b><div class="small muted">${g.missing_n} missing, ${g.mismatch_n} differ</div>` : "None"}</td>
    <td>${g.locked ? pill("Locked", "active") : g.status === "review" ? pill("On hold", "warn") : g.status === "filed" ? pill("Filed", "active") : pill("Open", "draft")}</td><td>${dmy(g.due)}</td></tr>`)}</tbody></table></div></div>`);
  $("#fent").onchange = e => { st.entity = +e.target.value; gst(); };
}

const drawer = h => { closeAll(); document.body.insertAdjacentHTML("beforeend", out(html`<div class="scrim" data-act="f-close"></div><div class="drawer glass wide"><div class="row" style="justify-content:space-between"><span></span><button class="icon" data-act="f-close" aria-label="Close">✕</button></div>${h}</div>`)); };
const closeAll = () => document.querySelectorAll(".scrim,.drawer,.modal").forEach(n => n.remove());

async function payables() {
  const p = await api("/finance/payables"), B = [["not_due", "Not yet due"], ["d1_30", "1 to 30 days late"], ["d31_60", "31 to 60 days late"], ["d61_90", "61 to 90 days late"], ["d90_plus", "Over 90 days late"]], mx = Math.max(1, ...B.map(([k]) => p.buckets[k].v));
  mount($("#fbody"), html`<div class="kpis">${kpi("Open payables", inr(p.total), "Converted at the invoice month rate")}${kpi("Past due", inr(p.overdue), `${B.slice(1).reduce((a, [k]) => a + p.buckets[k].n, 0)} invoices`)}${kpi("Due in 14 days", inr(p.due_next_14), "Plan cash for this")}</div>
    <div class="cols eq"><div class="card glass"><div class="ct"><h2>Ageing</h2></div><div class="bars wide">${B.map(([k, l]) => html`<div class="r"><span>${l}</span><div class="b"><i style="width:${(p.buckets[k].v / mx * 100).toFixed(1)}%"></i></div><span class="num r">${inr(p.buckets[k].v)}</span></div>`)}</div></div>
    <div class="card solid"><div class="ct"><h2>Largest vendors</h2></div><table class="tbl"><thead><tr><th>Vendor</th><th class="r">Open</th><th class="r">Past due</th></tr></thead><tbody>${p.vendors.map(v => html`<tr><td>${v.vendor}<div class="small muted">${v.n} invoices</div></td><td class="num r">${inr(v.total)}</td><td class="num r">${v.overdue ? inr(v.overdue) : "None"}</td></tr>`)}</tbody></table></div></div>
    <div class="card solid"><div class="ct"><h2>Past due invoices</h2></div>${p.overdue_list.length ? html`<table class="tbl"><thead><tr><th>Invoice</th><th>Vendor</th><th>Due</th><th class="r">Late</th><th class="r">Amount</th><th>Status</th></tr></thead><tbody>${p.overdue_list.map(i => html`<tr><td>${i.inv_no}</td><td>${i.vendor}</td><td>${dmy(i.due_date)}</td><td class="num r">${i.overdue_days}d</td><td class="num r">${inr(i.inr)}</td><td>${i.status === "held" ? pill("On hold", "warn") : pill(i.status, "draft")}</td></tr>`)}</tbody></table>` : empty("Nothing is past due.")}</div>`);
}

async function journal() {
  const q = `entity_id=${st.jentity}&period=${st.jperiod}`, [tb, j] = await Promise.all([api(`/finance/trial-balance?${q}`), api(`/finance/journal?${q}&page=${st.jpage}&size=12`)]), pages = Math.max(1, Math.ceil(j.total / j.size));
  mount($("#fbody"), html`<div class="row" style="margin-bottom:12px"><select class="input" id="jent">${opts.entities.map(e => html`<option value="${e.id}" ${e.id === st.jentity ? "selected" : ""}>${e.name.replace("Dry Fruit House ", "").replace(" (demo)", "")}</option>`)}</select>
    <select class="input" id="jper">${opts.periods.map(p => html`<option value="${p}" ${p === st.jperiod ? "selected" : ""}>${MON(p)}</option>`)}</select><button class="btn" data-act="f-export">Download CSV</button></div>
    <div class="cols eq"><div class="card solid"><div class="ct"><h2>Trial balance</h2><span class="small muted">${tb.debit === tb.credit ? "Debits equal credits" : "Out of balance"}</span></div><table class="tbl"><thead><tr><th>Account</th><th class="r">Debit</th><th class="r">Credit</th></tr></thead><tbody>${tb.rows.filter(r => r.dr || r.cr).map(r => html`<tr><td>${r.code} ${r.name}</td><td class="num r">${r.dr ? inr(r.dr) : ""}</td><td class="num r">${r.cr ? inr(r.cr) : ""}</td></tr>`)}
    <tr><td><b>Total</b></td><td class="num r"><b>${inr(tb.debit)}</b></td><td class="num r"><b>${inr(tb.credit)}</b></td></tr></tbody></table></div>
    <div class="card solid"><div class="ct"><h2>Vouchers</h2><span class="small muted">${num(j.total)} in the period</span></div><table class="tbl"><thead><tr><th>Voucher</th><th>Date</th><th class="r">Amount</th></tr></thead><tbody>${j.items.map(i => html`<tr class="click" data-act="f-jv" data-id="${i.id}"><td>${i.jv_no}<div class="small muted">${i.narration}</div></td><td>${dmy(i.date)}</td><td class="num r">${inr(i.amount)}</td></tr>`)}</tbody></table>
    <div class="row" style="justify-content:flex-end;margin-top:10px"><button class="btn sm" data-act="f-jpage" data-v="-1" ${st.jpage <= 1 ? "disabled" : ""}>Previous</button><span class="small muted">Page ${st.jpage} of ${pages}</span><button class="btn sm" data-act="f-jpage" data-v="1" ${st.jpage >= pages ? "disabled" : ""}>Next</button></div></div></div>`);
  $("#jent").onchange = e => { st.jentity = +e.target.value; st.jpage = 1; journal(); };
  $("#jper").onchange = e => { st.jperiod = e.target.value; st.jpage = 1; journal(); };
}

acts["f-tab"] = a => { st.tab = a.dataset.v; flip("ftabs", st.tab); load(); };
acts["f-days"] = a => { st.days = +a.dataset.v; load(); };
acts["f-per"] = a => { st.period = a.dataset.v; flip("fper", st.period); closeBoard(); };
acts["f-flag"] = a => { st.flagged = +a.dataset.v; cash(); };
acts["f-src"] = a => { st.source = a.dataset.v; st.page = 1; flip("fsrc", st.source); recon(); };
acts["f-page"] = a => { st.page += +a.dataset.v; recon(); };
acts["f-jpage"] = a => { st.jpage += +a.dataset.v; journal(); };
acts["f-close"] = closeAll;
acts["f-lock"] = async a => { try { await api("/finance/close/lock", { method: "POST", body: { entity_id: +a.dataset.e, period: st.period } }); toast("Period locked"); closeBoard(); } catch (e) { toast(e.message, true); } };
acts["f-store"] = async a => {
  const r = await api(`/finance/cash/store/${a.dataset.id}?days=60`);
  drawer(html`<h1>${r.store.name.replace("Dry Fruit House ", "")}</h1><p class="muted small">${r.store.city}. Day close for the last 60 days.</p><div class="tblwrap" style="max-height:70vh"><table class="tbl"><thead><tr><th>Date</th><th class="r">Expected</th><th class="r">Counted</th><th class="r">Variance</th></tr></thead><tbody>${r.rows.map(x => html`<tr><td>${x.weekday} ${dmy(x.business_date)}</td><td class="num r">${inr(x.expected_cash_paise, false)}</td><td class="num r">${x.counted_cash_paise == null ? pill("Not closed", "warn") : inr(x.counted_cash_paise, false)}</td><td class="num r">${x.variance_paise == null ? "" : x.variance_paise <= -100000 ? html`<b>${inr(x.variance_paise, false)}</b>` : inr(x.variance_paise, false)}</td></tr>`)}</tbody></table></div>`);
};
acts["f-gd"] = async a => {
  const d = await api(`/finance/gst/detail?entity_id=${st.entity}&period=${a.dataset.p}`), tbl = (h, rows) => rows.length ? html`<table class="tbl" style="margin-bottom:18px"><thead><tr>${h.map(x => html`<th>${x}</th>`)}</tr></thead><tbody>${rows}</tbody></table>` : empty("None.");
  drawer(html`<h1>${MON(a.dataset.p)} input credit</h1>${d.available ? "" : html`<p class="muted">GSTR-2B for this month is released after the 14th of next month. Matching starts then.</p>`}
    <h2 style="margin:14px 0 6px">In books, missing in GSTR-2B</h2>${tbl(["Invoice", "Vendor", "Tax"], d.missing.map(m => html`<tr><td>${m.inv_no}<div class="small muted">${dmy(m.inv_date)}</div></td><td>${m.vendor}</td><td class="num r">${inr(m.tax_minor, false)}</td></tr>`))}
    <h2 style="margin:14px 0 6px">Tax value differs</h2>${tbl(["Invoice", "Books", "Portal", "Difference"], d.mismatch.map(m => html`<tr><td>${m.inv_no}<div class="small muted">${m.vendor}</div></td><td class="num r">${inr(m.books, false)}</td><td class="num r">${inr(m.portal, false)}</td><td class="num r">${inr(m.diff, false)}</td></tr>`))}
    <h2 style="margin:14px 0 6px">In GSTR-2B, not booked</h2>${tbl(["Invoice", "Supplier GSTIN", "Tax"], d.unbooked.map(m => html`<tr><td>${m.inv_no}</td><td>${m.supplier_gstin}</td><td class="num r">${inr(m.tax_paise, false)}</td></tr>`))}`);
};
acts["f-jv"] = async a => {
  const j = await api(`/finance/journal/${a.dataset.id}`); closeAll();
  document.body.insertAdjacentHTML("beforeend", out(html`<div class="scrim" data-act="f-close"></div><div class="modal glass"><div class="row" style="justify-content:space-between"><h1 style="font-size:20px">${j.jv_no}</h1><button class="icon" data-act="f-close" aria-label="Close">✕</button></div><p class="small muted">${dmy(j.date)}. ${j.narration}</p>
    <table class="tbl"><thead><tr><th>Account</th><th class="r">Debit</th><th class="r">Credit</th></tr></thead><tbody>${j.lines.map(l => html`<tr><td>${l.account_code} ${l.name}</td><td class="num r">${l.debit_paise ? inr(l.debit_paise, false) : ""}</td><td class="num r">${l.credit_paise ? inr(l.credit_paise, false) : ""}</td></tr>`)}</tbody></table></div>`));
};
acts["f-export"] = async () => {
  const r = await fetch(`/api/finance/journal/export?entity_id=${st.jentity}&period=${st.jperiod}`, { headers: { Authorization: "Bearer " + S.token } });
  if (!r.ok) return toast("Export failed", true);
  const a = document.createElement("a"); a.href = URL.createObjectURL(await r.blob()); a.download = `journal-${st.jentity}-${st.jperiod}.csv`; a.click(); URL.revokeObjectURL(a.href);
};
acts["f-res"] = a => {
  const w = a.dataset.v === "write_off"; closeAll();
  document.body.insertAdjacentHTML("beforeend", out(html`<div class="scrim" data-act="f-close"></div><div class="modal glass" style="width:min(480px,calc(100vw - 28px))"><h1 style="font-size:20px">${w ? "Write off this item" : "Mark as explained"}</h1>
    <p class="small muted" style="margin:6px 0 12px">${w ? `Write-offs above ₹${num(opts.wo_limit / 100)} need the CEO or admin. ` : ""}Say why, in a few words. This goes in the audit log.</p><input class="input" id="fnote" style="width:100%" placeholder="Reason" autocomplete="off">
    <div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-act="f-close">Cancel</button><button class="btn pri" data-act="f-resave" data-id="${a.dataset.id}" data-v="${a.dataset.v}">Save</button></div></div>`));
  $("#fnote").focus();
};
acts["f-resave"] = async a => {
  try { await api(`/finance/recon/${a.dataset.id}/resolve`, { method: "POST", body: { action: a.dataset.v, note: $("#fnote").value } }); closeAll(); toast("Saved"); recon(); }
  catch (e) { toast(e.message, true); }
};
