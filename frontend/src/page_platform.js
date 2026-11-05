import { html, out, raw, num, pct, dmy, inr, spark } from "./ui.js";
import { S, api, acts, mount, toast } from "./core.js";

const st = { tab: "approvals", view: "queue", page: 1, au: "", aa: "", at: "", aq: "", af: "", ato: "", kind: "vendor_costs", csv: "", file: "", res: null, ent: "", opts: null };
const $ = s => document.querySelector(s);
const role = () => S.user.role;
const ADMIN = () => ["ceo", "admin"].includes(role()), AUD = () => ["ceo", "admin", "finance"].includes(role());
const pill = (t, c = "") => html`<span class="pill ${c}">${t}</span>`;
const kpi = (l, v, s) => html`<div class="kpi glass"><div class="l">${l}</div><div class="v">${v}</div><div class="s">${s}</div></div>`;
const seg = (id, act, cur, items) => html`<div class="seg" id="${id}">${items.map(([v, l]) => html`<button data-act="${act}" data-v="${v}" class="${String(cur) === String(v) ? "on" : ""}">${l}</button>`)}</div>`;
const closeAll = () => document.querySelectorAll(".scrim,.drawer,.modal").forEach(n => n.remove());
const drawer = inner => { closeAll(); document.body.insertAdjacentHTML("beforeend", out(html`<div class="scrim" data-act="p-close"></div><div class="drawer glass wide">${inner}</div>`)); };
const modal = inner => { closeAll(); document.body.insertAdjacentHTML("beforeend", out(html`<div class="scrim" data-act="p-close"></div><div class="modal glass">${inner}</div>`)); };
const fdt = t => t ? dmy(String(t).slice(0, 10)) + " " + String(t).replace(" ", "T").slice(11, 16) : "never";
const ST = { pending: "warn", approved: "active", released: "active", applied: "active", rejected: "delisted", cancelled: "draft" };
const lbl = (t, f) => html`<label class="small muted" style="display:block;margin:10px 0 4px;font-weight:600">${t}</label>${f}`;
const TABS = () => [["approvals", "Approvals", 1], ["audit", "Audit log", AUD()], ["imports", "Imports", 1], ["entities", "Entities and FX", AUD()], ["users", "Users and roles", ADMIN()], ["health", "Sync and jobs", AUD()]].filter(t => t[2]);
const rupee = p => inr(p);
const debounce = (f, ms = 300) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => f(...a), ms); }; };
const act = (fn, ok, again) => async (a, e) => { try { await fn(a, e); if (ok) toast(ok); if (again) again(); } catch (x) { toast(x.message, true); } };
const post = (p, body, method = "POST") => api(p, { method, body });

export async function render(el) {
  if (!TABS().find(t => t[0] === st.tab)) st.tab = "approvals";
  mount(el, html`<div class="head"><div><div class="eyebrow">Module 10</div><h1>Platform</h1><p class="muted">Approvals, audit trail, imports, legal entities, users and system health.</p></div><div class="row">${seg("ptabs", "p-tab", st.tab, TABS().map(t => [t[0], t[1]]))}</div></div><div id="pbody"><div class="card glass"><p class="muted">Loading</p></div></div>`);
  load();
}
function load() {
  const f = { approvals, audit, imports, entities, users, health }[st.tab];
  f().catch(e => { const b = $("#pbody"); if (b) b.innerHTML = out(html`<div class="card glass"><p class="muted">${e.message}</p></div>`); });
}
acts["p-tab"] = a => { st.tab = a.dataset.v; st.page = 1; document.querySelectorAll("#ptabs button").forEach(b => b.classList.toggle("on", b === a)); load(); };
acts["p-close"] = closeAll;
const pager = (total, size, a) => html`<div class="row" style="justify-content:space-between;margin-top:10px"><span class="small muted">${num(total)} found</span><span class="row"><button class="btn sm" data-act="${a}" data-v="-1" ${st.page <= 1 ? "disabled" : ""}>Previous</button><button class="btn sm" data-act="${a}" data-v="1" ${st.page * size >= total ? "disabled" : ""}>Next</button></span></div>`;

// ---------- approvals ----------
async function approvals() {
  const [s, r, ru, w] = await Promise.all([api("/platform/summary"), api(`/platform/approvals?view=${st.view}&page=${st.page}`), api("/platform/rules"), api("/platform/waiting")]);
  const views = [["queue", "Waiting for me"], ["mine", "My requests"]].concat(AUD() ? [["all", "All requests"]] : []);
  const unit = r2 => r2.unit === "inr" ? rupee(r2.min_value * 100) : r2.min_value + "%";
  mount($("#pbody"), html`<div class="kpis">${kpi("Waiting on you", num(s.waiting_on_me), "you are the right approver and did not raise them")}${kpi("Open requests", num(s.open_requests), "across the company")}${kpi("Your open requests", num(s.my_pending), "raised by you")}${kpi("Unread notes", num(s.unread), "approvals and decisions")}</div>
    <div class="cols"><div class="card solid"><div class="ct"><h2>Requests</h2></div><div class="row" style="justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:12px">${seg("pv", "p-view", st.view, views)}<button class="btn pri" data-act="p-new">New request</button></div>
    ${r.items.length ? html`<div class="tblwrap"><table class="tbl"><thead><tr><th>Request</th><th>By</th><th>Needs</th><th>Status</th><th></th></tr></thead><tbody>${r.items.map(x => html`<tr><td><b>${x.title || x.label}</b><div class="small muted">${x.label}. ${x.sub || ""}</div><div class="small muted">${x.note ? String(x.note).split(" || ")[0] : ""}</div></td><td>${x.requester}<div class="small muted">${x.age_h}h ago</div></td>
      <td>${x.unit === "inr" ? rupee(x.amount_paise) : (x.amount_paise / 100).toFixed(1) + "% move"}<div class="small muted">${x.need_role}</div></td><td>${pill(x.status, ST[x.status])}${x.approver ? html`<div class="small muted">${x.approver}</div>` : ""}</td>
      <td class="r">${x.can_decide ? html`<button class="btn sm pri" data-act="p-dec" data-id="${x.id}" data-v="approve">Approve</button> <button class="btn sm" data-act="p-dec" data-id="${x.id}" data-v="reject">Reject</button>` : ""}${x.can_cancel ? html` <button class="btn sm" data-act="p-cancel" data-id="${x.id}">Withdraw</button>` : ""}</td></tr>`)}</tbody></table></div>${pager(r.total, r.size, "p-pg")}` : html`<p class="muted">Nothing here.</p>`}</div>
    <div><div class="card glass"><div class="ct"><h2>Waiting in other modules</h2></div>${w.length ? w.map(x => html`<a class="row" href="${x.link}" style="justify-content:space-between;padding:6px 0;text-decoration:none;color:inherit"><span>${x.title}</span><span class="num"><b>${num(x.n)}</b>${x.v ? html`<span class="small muted"> ${rupee(x.v)}</span>` : ""}</span></a>`) : html`<p class="muted small">Nothing assigned to your role.</p>`}<p class="small muted" style="margin-top:8px">These are decided in their own module. Requests above are decided here.</p></div>
    <div class="card glass" style="margin-top:14px"><div class="ct"><h2>Approval rules</h2></div>${ru.items.map(x => html`<div class="row" style="justify-content:space-between;padding:5px 0"><span>${x.label}<div class="small muted">${unit(x)} ${x.max_value == null ? "and above" : "to " + (x.unit === "inr" ? rupee(x.max_value * 100) : x.max_value + "%")}</div></span><span class="row">${pill(x.approver, "t")}${ADMIN() ? html`<button class="btn sm" data-act="p-rule" data-id="${x.id}">Edit</button>` : ""}</span></div>`)}<p class="small muted" style="margin-top:8px">${ru.note}</p></div></div></div>`);
  st.rules = ru.items;
}
acts["p-view"] = a => { st.view = a.dataset.v; st.page = 1; approvals(); };
acts["p-pg"] = a => { st.page += +a.dataset.v; load(); };
acts["p-new"] = act(async () => {
  const o = await api("/platform/approvals/options"); st.opts = o;
  modal(html`<h2>New request</h2><p class="small muted">Price moves under ${o.price_floor_pct}% do not need approval. Change them in SKU master.</p>${lbl("Type", html`<select class="input" id="nt" data-chg="p-nt">${o.types.filter(t => t.allowed).map(t => html`<option value="${t.code}">${t.label}</option>`)}</select>`)}<div id="nf"></div>${lbl("Note", html`<input class="input" id="nn" style="width:100%" placeholder="Why this is needed">`)}<div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-act="p-close">Cancel</button><button class="btn pri" data-act="p-send">Send for approval</button></div>`);
  $("#nt").onchange = nform; nform();
});
function nform() {
  const t = $("#nt").value, o = st.opts;
  $("#nf").innerHTML = out(t === "payment_release" ? lbl("Pending invoice", html`<select class="input" id="nr" style="width:100%">${o.invoices.map(i => html`<option value="${i.id}">${i.vendor}, ${i.inv_no}, ${i.currency} ${(i.amount_minor / 100).toLocaleString("en-IN")}, due ${dmy(String(i.due_date).slice(0, 10))}</option>`)}</select>`)
    : html`${lbl("SKU code", html`<input class="input" id="nr" style="width:100%" placeholder="e.g. a code from SKU master">`)}${lbl("New price, rupees", html`<input class="input" id="nv" type="number" step="0.01" style="width:100%">`)}`);
}
acts["p-send"] = act(async () => { const t = $("#nt").value; const r = await post("/platform/approvals", { doc_type: t, ref: $("#nr").value, value: $("#nv") ? +$("#nv").value : null, note: $("#nn").value }); closeAll(); toast(`Sent to ${r.approver_role}`); }, "", approvals);
acts["p-dec"] = a => {
  const rej = a.dataset.v === "reject", id = a.dataset.id;
  modal(html`<h2>${rej ? "Reject request" : "Approve request"}</h2>${lbl(rej ? "Reason (required)" : "Note (optional)", html`<textarea class="input" id="dn" rows="3" style="width:100%"></textarea>`)}<div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-act="p-close">Cancel</button><button class="btn pri" data-act="p-dec-go" data-id="${id}" data-v="${a.dataset.v}">${rej ? "Reject" : "Approve"}</button></div>`);
};
acts["p-dec-go"] = act(async a => { await post(`/platform/approvals/${a.dataset.id}/decide`, { action: a.dataset.v, note: $("#dn").value }); closeAll(); }, "Done", approvals);
acts["p-cancel"] = act(a => post(`/platform/approvals/${a.dataset.id}/cancel`), "Withdrawn", approvals);
acts["p-rule"] = a => {
  const x = st.rules.find(r => r.id == a.dataset.id), u = x.unit === "inr" ? "rupees" : "percent";
  modal(html`<h2>${x.label} band</h2>${lbl("From, " + u, html`<input class="input" id="rl" type="number" value="${x.min_value}" style="width:100%">`)}${lbl("Up to, " + u + " (empty for no limit)", html`<input class="input" id="rh" type="number" value="${x.max_value ?? ""}" style="width:100%">`)}${lbl("Approver", html`<select class="input" id="ra">${["finance", "ceo"].map(r => html`<option ${r === x.approver ? "selected" : ""}>${r}</option>`)}</select>`)}<div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-act="p-close">Cancel</button><button class="btn pri" data-act="p-rule-go" data-id="${x.id}">Save</button></div>`);
};
acts["p-rule-go"] = act(async a => { const h = $("#rh").value; await post(`/platform/rules/${a.dataset.id}`, { min_value: +$("#rl").value, max_value: h === "" ? null : +h, approver: $("#ra").value }, "PATCH"); closeAll(); }, "Rule saved", approvals);

// ---------- audit ----------
async function audit() {
  const qs = new URLSearchParams({ user_id: st.au || 0, action: st.aa, table: st.at, q: st.aq, frm: st.af, to: st.ato, page: st.page, size: 30 });
  const [o, s, r] = await Promise.all([api("/platform/audit/options"), api("/platform/audit/stats?days=30"), api("/platform/audit?" + qs)]);
  const sel = (id, cur, items, all) => html`<select class="input" id="${id}"><option value="">${all}</option>${items.map(([v, l]) => html`<option value="${v}" ${String(cur) === String(v) ? "selected" : ""}>${l}</option>`)}</select>`;
  mount($("#pbody"), html`<div class="kpis">${kpi("Events, 30 days", num(s.total), "every write is logged with before and after")}${kpi("Top action", s.by_action[0]?.k || "none", num(s.by_action[0]?.n || 0) + " events")}${kpi("Most active user", s.by_user[0]?.k || "none", num(s.by_user[0]?.n || 0) + " events")}<div class="kpi glass"><div class="l">Daily events</div>${spark(s.daily.map(d => d.n), 200, 44)}<div class="s">last 30 days</div></div></div>
    <div class="card solid"><div class="ct"><h2>Audit log</h2><button class="btn sm" data-act="p-export">Export CSV</button></div><div class="row" style="flex-wrap:wrap;gap:10px;margin-bottom:12px">${sel("au", st.au, o.users.map(u => [u.id, u.name]), "All users")}${sel("aa", st.aa, o.actions.map(x => [x, x]), "All actions")}${sel("at", st.at, o.tables.map(x => [x, x]), "All tables")}<input class="input" id="af" type="date" value="${st.af}" title="From"><input class="input" id="ato" type="date" value="${st.ato}" title="To"><input class="input" id="aq" placeholder="Row id or name" value="${st.aq}"></div>
    <div class="tblwrap"><table class="tbl"><thead><tr><th>Time</th><th>User</th><th>Action</th><th>Record</th><th>Change</th></tr></thead><tbody>${r.items.map(x => html`<tr><td class="num">${fdt(x.ts)}</td><td>${x.user || "system"}<div class="small muted">${x.role || ""}</div></td><td>${pill(x.action, "t")}</td><td>${x.table_name}<div class="small muted">${x.row_id}</div></td><td class="small">${x.changes.slice(0, 3).map(c => html`<div><b>${c.field}</b> ${c.before == null ? "" : String(c.before) + " to "}${c.after == null ? "removed" : String(c.after)}</div>`)}${x.changes.length > 3 ? html`<span class="muted">+${x.changes.length - 3} more</span>` : ""}</td></tr>`)}</tbody></table></div>${r.items.length ? "" : html`<p class="muted">No events match.</p>`}${pager(r.total, r.size, "p-pg")}</div>`);
  const re = debounce(() => { st.page = 1; audit(); });
  ["au", "aa", "at", "af", "ato"].forEach(k => $("#" + k).onchange = e => { st[k] = e.target.value; st.page = 1; audit(); });
  $("#aq").oninput = e => { st.aq = e.target.value; re(); };
}
acts["p-export"] = act(async () => {
  const qs = new URLSearchParams({ user_id: st.au || 0, action: st.aa, table: st.at, q: st.aq, frm: st.af, to: st.ato });
  const r = await fetch("/api/platform/audit/export?" + qs, { headers: { Authorization: "Bearer " + S.token } }); if (!r.ok) throw new Error("Export failed");
  const a = document.createElement("a"); a.href = URL.createObjectURL(await r.blob()); a.download = "dfh-audit.csv"; a.click();
}, "Exported");

// ---------- imports ----------
async function imports() {
  const [k, h] = await Promise.all([api("/platform/imports/kinds"), api("/platform/imports")]); const cur = k.kinds.find(x => x.code === st.kind);
  if (!st.csv) st.csv = cur.sample;
  const res = st.res;
  mount($("#pbody"), html`<div class="cols"><div class="card solid"><div class="ct"><h2>Bulk import</h2></div>${seg("pk", "p-kind", st.kind, k.kinds.map(x => [x.code, x.name]))}
    <p class="small muted" style="margin-top:10px">Columns: ${cur.cols}. ${cur.note}</p>
    ${k.allowed ? html`<div class="row" style="margin:10px 0;gap:10px"><input type="file" id="pf" accept=".csv,text/csv"><span class="small muted">${st.file}</span></div><textarea class="input" id="pc" rows="8" style="width:100%;font-family:ui-monospace,monospace;font-size:12px">${st.csv}</textarea>
    <div class="row" style="justify-content:flex-end;margin-top:10px"><button class="btn" data-act="p-check">Check file</button><button class="btn pri" data-act="p-apply">Apply</button></div>` : html`<p class="muted">Your role can read import history only.</p>`}
    ${res ? html`<div style="margin-top:12px">${pill(res.applied ? "Applied" : res.errors.length ? "Not applied" : "Checked, ready to apply", res.applied ? "active" : res.errors.length ? "delisted" : "t")} <span class="small muted">${num(res.ok)} of ${num(res.rows)} rows valid. Nothing is written unless every row is valid.</span>${res.errors.length ? html`<div class="tblwrap" style="margin-top:8px"><table class="tbl"><thead><tr><th>Row</th><th>Item</th><th>Problem</th></tr></thead><tbody>${res.errors.slice(0, 50).map(e => html`<tr><td class="num">${e.row}</td><td>${e.code}</td><td>${e.error}</td></tr>`)}</tbody></table></div>` : ""}</div>` : ""}</div>
    <div class="card glass"><div class="ct"><h2>History</h2></div>${h.map(x => html`<div style="padding:6px 0;border-bottom:1px solid var(--line)"><div class="row" style="justify-content:space-between"><b>${x.filename}</b>${pill(x.status, ST[x.status])}</div><div class="small muted">${x.kind}, ${fdt(x.created_at)}, ${num(x.rows_ok)} applied, ${num(x.rows_err)} errors</div>${x.errors.slice(0, 2).map(e => html`<div class="small">Row ${e.row}: ${e.error}</div>`)}</div>`)}</div></div>`);
  if (k.allowed) { $("#pc").oninput = e => { st.csv = e.target.value; }; $("#pf").onchange = async e => { const f = e.target.files[0]; if (f) { st.csv = await f.text(); st.file = f.name; $("#pc").value = st.csv; } }; }
}
acts["p-kind"] = a => { st.kind = a.dataset.v; st.csv = ""; st.res = null; st.file = ""; imports(); };
const runImp = apply => act(async () => { st.res = await post("/platform/imports", { kind: st.kind, csv: $("#pc").value, apply, filename: st.file || "pasted.csv" }); }, "", imports);
acts["p-check"] = runImp(false); acts["p-apply"] = runImp(true);

// ---------- entities and FX ----------
async function entities() {
  const [e, f] = await Promise.all([api("/platform/entities"), api("/platform/fx")]);
  mount($("#pbody"), html`<div class="kpis">${kpi("Legal entities", num(e.items.length), "15 Indian states, 5 GCC countries")}${kpi("Net sales, 30 days", rupee(e.total_sales), "INR equivalent, to " + dmy(e.as_of))}${kpi("Payables open", rupee(e.total_payables), "pending, held and released invoices")}${kpi("Currencies", num(f.items.length + 1), "monthly rates, assumed unless entered")}</div>
    <div class="cols"><div class="card solid"><div class="ct"><h2>Entities</h2></div><div class="tblwrap"><table class="tbl"><thead><tr><th>Entity</th><th>Stores</th><th>People</th><th class="r">Sales 30d</th><th class="r">Payables</th></tr></thead><tbody>${e.items.map(x => html`<tr class="click" data-act="p-ent" data-id="${x.code}"><td><b>${x.name.replace("Dry Fruit House ", "").replace(" (demo)", "")}</b><div class="small muted">${x.code}, ${x.currency}${x.gstin ? ", " + x.gstin : ""}</div></td><td class="num">${x.stores}<div class="small muted">${x.warehouses} warehouses</div></td><td class="num">${num(x.people)}</td><td class="num r">${rupee(x.sales30)}<div class="small muted">${x.growth == null ? "" : (x.growth >= 0 ? "+" : "") + pct(x.growth, 1)}</div></td><td class="num r">${rupee(x.payables)}</td></tr>`)}</tbody></table></div><p class="small muted" style="margin-top:8px">${e.note}</p></div>
    <div class="card glass"><div class="ct"><h2>FX rates to INR</h2></div>${f.items.map(x => html`<div class="row" style="justify-content:space-between;padding:6px 0"><span><b>${x.currency}</b> <span class="num">${x.rate.toFixed(4)}</span><div class="small muted">${x.month}, ${x.assumed ? "assumed" : "entered"}, ${x.entities} entities, ${x.vendors} vendors</div></span><span class="row">${spark(x.series, 70, 24)}<span class="small muted num">${x.change == null ? "" : (x.change >= 0 ? "+" : "") + pct(x.change, 1)}</span></span></div>`)}
    <button class="btn" style="margin-top:10px" data-act="p-fx">Enter a rate</button><p class="small muted" style="margin-top:8px">${f.note} Moves above ${f.limit_pct}% need a confirmation.</p></div></div>`);
  st.fx = f.items;
}
acts["p-ent"] = act(async a => {
  const d = await api("/platform/entities/" + a.dataset.id), e = d.entity, mx = Math.max(1, ...d.monthly.map(m => m.net));
  drawer(html`<div class="ct"><h2>${e.name}</h2><button class="btn sm" data-act="p-close">Close</button></div><p class="muted small">${e.code}, ${e.country}, ${e.currency}${e.state ? ", " + e.state : ""}. Synthetic entity.</p>
    <h3 class="small muted" style="margin:12px 0 4px">Net sales by month</h3>${spark(d.monthly.map(m => m.net), 460, 60)}<div class="row small muted" style="justify-content:space-between">${d.monthly.map(m => html`<span>${m.month.slice(5)}</span>`)}</div>
    <h3 class="small muted" style="margin:12px 0 4px">Top cities, 30 days</h3>${d.cities.slice(0, 6).map(c => html`<div class="row" style="justify-content:space-between;padding:3px 0"><span>${c.city} <span class="small muted">${c.stores} stores</span></span><span class="num">${rupee(c.net)}</span></div>`)}
    <h3 class="small muted" style="margin:12px 0 4px">Formats</h3><div class="row" style="flex-wrap:wrap;gap:6px">${d.formats.map(f => pill(`${f.format} ${f.n}`))}</div>
    <h3 class="small muted" style="margin:12px 0 4px">Warehouses</h3>${d.warehouses.map(w => html`<div class="small">${w.name}, ${w.city}</div>`)}${d.warehouses.length ? "" : html`<div class="small muted">None in this entity</div>`}
    <h3 class="small muted" style="margin:12px 0 4px">Open payables</h3>${d.payables.map(p => html`<div class="row small" style="justify-content:space-between"><span>${p.vendor}, ${p.inv_no}</span><span class="num">${p.currency} ${(p.amount_minor / 100).toLocaleString("en-IN")} ${pill(p.status, ST[p.status] || "")}</span></div>`)}
    <h3 class="small muted" style="margin:12px 0 4px">Registration</h3>${lbl("Legal name", html`<input class="input" id="en" value="${e.name}" style="width:100%">`)}${e.country === "India" ? lbl("GSTIN", html`<input class="input" id="eg" value="${e.gstin || ""}" placeholder="15 characters, left empty in the demo" style="width:100%">`) : html`<p class="small muted">GSTIN does not apply outside India.</p>`}
    <div class="row" style="justify-content:flex-end;margin-top:12px"><button class="btn pri" data-act="p-ent-save" data-id="${e.code}">Save</button></div>${d.history.map(h => html`<div class="small muted">${fdt(h.ts)} ${h.user}</div>`)}`);
});
acts["p-ent-save"] = act(async a => { const g = $("#eg"); await post("/platform/entities/" + a.dataset.id, { name: $("#en").value, gstin: g ? g.value : null }, "PATCH"); closeAll(); }, "Saved", entities);
acts["p-fx"] = () => modal(html`<h2>Enter an FX rate</h2>${lbl("Currency", html`<select class="input" id="fc">${st.fx.map(x => html`<option>${x.currency}</option>`)}</select>`)}${lbl("Month", html`<input class="input" id="fm" type="month" value="2026-11">`)}${lbl("Rate to INR", html`<input class="input" id="fr" type="number" step="0.0001" style="width:100%">`)}<div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-act="p-close">Cancel</button><button class="btn pri" data-act="p-fx-go">Save</button></div>`);
acts["p-fx-go"] = async () => {
  const body = { currency: $("#fc").value, month: $("#fm").value, rate: +$("#fr").value };
  try { await post("/platform/fx", body); closeAll(); toast("Rate saved"); entities(); }
  catch (e) { if (e.message.includes("Confirm") && confirm(e.message + ". Save it anyway?")) { await post("/platform/fx", { ...body, force: true }); closeAll(); toast("Rate saved"); entities(); } else toast(e.message, true); }
};

// ---------- users and roles ----------
const LV = { act: "Act", view: "View", "": "" };
async function users() {
  const [u, m] = await Promise.all([api("/platform/users"), api("/platform/roles")]); st.users = u;
  mount($("#pbody"), html`<div class="card solid"><div class="ct"><h2>Users</h2><button class="btn pri sm" data-act="p-unew">Add user</button></div><div class="tblwrap"><table class="tbl"><thead><tr><th>Name</th><th>Role</th><th>Scope</th><th>Last login</th><th>Status</th><th></th></tr></thead><tbody>${u.items.map(x => html`<tr><td><b>${x.name}</b><div class="small muted">${x.username}</div></td><td>${x.role_name}</td><td>${x.scope_name || "Whole company"}</td><td class="num">${fdt(x.last_login)}</td><td>${pill(x.active ? "Active" : "Off", x.active ? "active" : "draft")}</td><td class="r"><button class="btn sm" data-act="p-uedit" data-id="${x.id}">Edit</button> <button class="btn sm" data-act="p-upw" data-id="${x.id}">Password</button></td></tr>`)}</tbody></table></div></div>
    <div class="card solid" style="margin-top:14px"><div class="ct"><h2>Who can do what</h2></div><div class="tblwrap"><table class="tbl"><thead><tr><th>Area</th>${m.roles.map(r => html`<th>${r.name}</th>`)}</tr></thead><tbody>${m.rows.map(r => html`<tr><td>${r.area}</td>${m.roles.map(x => html`<td>${r.levels[x.code] === "act" ? pill("Act", "active") : r.levels[x.code] === "view" ? pill("View") : ""}</td>`)}</tr>`)}</tbody></table></div><p class="small muted" style="margin-top:8px">${m.note}</p></div>`);
}
const needsScope = r => ["warehouse", "store_manager", "cashier"].includes(r);
const uform = (x, whs) => html`${x ? "" : lbl("Username", html`<input class="input" id="uu" style="width:100%" autocomplete="off">`)}${lbl("Name", html`<input class="input" id="un" value="${x?.name || ""}" style="width:100%">`)}${lbl("Role", html`<select class="input" id="ur" style="width:100%">${st.users.roles.map(r => html`<option value="${r.code}" ${x?.role === r.code ? "selected" : ""}>${r.name}</option>`)}</select>`)}${lbl("Location code (store or warehouse roles only)", html`<input class="input" id="us" value="${x?.scope_code || ""}" list="whl" style="width:100%" placeholder="Store or warehouse code"><datalist id="whl">${whs.map(w => html`<option value="${w.code}">${w.name}</option>`)}</datalist>`)}${x ? "" : lbl("Password", html`<input class="input" id="up" type="password" style="width:100%" autocomplete="new-password">`)}`;
acts["p-unew"] = () => modal(html`<h2>Add user</h2>${uform(null, st.users.warehouses)}<div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-act="p-close">Cancel</button><button class="btn pri" data-act="p-unew-go">Create</button></div>`);
acts["p-unew-go"] = act(async () => { await post("/platform/users", { username: $("#uu").value, name: $("#un").value, role: $("#ur").value, password: $("#up").value, scope_code: $("#us").value || null }); closeAll(); }, "User created", users);
acts["p-uedit"] = a => { const x = st.users.items.find(i => i.id == a.dataset.id); modal(html`<h2>${x.name}</h2>${uform(x, st.users.warehouses)}<div class="row" style="justify-content:space-between;margin-top:16px"><button class="btn" data-act="p-uactive" data-id="${x.id}" data-v="${x.active ? 0 : 1}">${x.active ? "Deactivate" : "Reactivate"}</button><span class="row"><button class="btn" data-act="p-close">Cancel</button><button class="btn pri" data-act="p-uedit-go" data-id="${x.id}">Save</button></span></div>`); };
acts["p-uedit-go"] = act(async a => { const x = st.users.items.find(i => i.id == a.dataset.id), r = $("#ur").value; await post("/platform/users/" + x.id, { name: $("#un").value, role: r, scope_code: needsScope(r) ? $("#us").value : null }, "PATCH"); closeAll(); }, "Saved", users);
acts["p-uactive"] = act(async a => { await post("/platform/users/" + a.dataset.id, { active: a.dataset.v === "1" }, "PATCH"); closeAll(); }, "Updated", users);
acts["p-upw"] = a => modal(html`<h2>Reset password</h2>${lbl("New password", html`<input class="input" id="pw" type="password" style="width:100%" autocomplete="new-password">`)}<p class="small muted">8 characters or more, with a letter and a digit. The user is not told automatically.</p><div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-act="p-close">Cancel</button><button class="btn pri" data-act="p-upw-go" data-id="${a.dataset.id}">Reset</button></div>`);
acts["p-upw-go"] = act(async a => { await post(`/platform/users/${a.dataset.id}/password`, { password: $("#pw").value }); closeAll(); }, "Password reset");

// ---------- health ----------
async function health() {
  const h = await api("/platform/health"), d = h.devices, s = h.sync;
  mount($("#pbody"), html`<div class="kpis">${kpi("Devices", num(d.total), `${num(d.online)} online, ${num(d.delayed)} delayed, ${num(d.stale)} stale`)}${kpi("Sync success, 72h", s.ok_pct == null ? "n/a" : pct(s.ok_pct, 1), `${num(s.partial)} partial, ${num(s.failed)} failed of ${num(s.runs)}`)}${kpi("Bills pushed, 72h", num(s.pushed), `${num(s.rejected)} rejected`)}${kpi("Deepest queue", num(s.maxq), "bills waiting on one device")}${kpi("Data through", dmy(h.data.through), h.data.lag_days + " days behind today")}</div>
    <div class="cols eq"><div class="card solid"><div class="ct"><h2>Stale devices</h2></div>${h.stale.length ? html`<table class="tbl"><tbody>${h.stale.map(x => html`<tr><td>${x.store}<div class="small muted">${x.city}, ${x.code}</div></td><td class="num r">${Math.floor(x.hours / 24)}d ${Math.round(x.hours % 24)}h silent</td></tr>`)}</tbody></table>` : html`<p class="muted">Every device checked in within 24 hours.</p>`}<p class="small muted" style="margin-top:8px">${h.note}</p></div>
    <div class="card solid"><div class="ct"><h2>Stores with most failed or partial syncs</h2></div><table class="tbl"><tbody>${h.worst.map(x => html`<tr><td>${x.store}<div class="small muted">${x.city}</div></td><td class="num r">${x.bad} of ${x.runs}<div class="small muted">queue up to ${x.q}</div></td></tr>`)}</tbody></table></div></div>
    <div class="cols eq"><div class="card glass"><div class="ct"><h2>Recent jobs</h2></div>${h.jobs.map(j => html`<div class="row" style="justify-content:space-between;padding:4px 0"><span>${j.filename}<div class="small muted">${j.kind}, ${fdt(j.created_at)}</div></span>${pill(j.status, ST[j.status])}</div>`)}${h.forecast ? html`<p class="small muted" style="margin-top:8px">Last forecast run ${fdt(h.forecast.run_at)}, ${h.forecast.method}${h.forecast.wape == null ? "" : ", WAPE " + pct(h.forecast.wape, 1)}.</p>` : ""}</div>
    <div class="card glass"><div class="ct"><h2>POS app versions</h2></div>${d.versions.map(([v, n]) => html`<div class="row" style="justify-content:space-between;padding:3px 0"><span>${v}</span><span class="num">${num(n)}</span></div>`)}</div></div>`);
}
