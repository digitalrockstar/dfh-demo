import { html, out, num, pct, dmy } from "./ui.js";
import { api, acts, mount, toast } from "./core.js";
import { spark } from "./ui.js";

const st = { tab: "overview", q: "", lt: "", page: 1, adate: "", aloc: "", astat: "", lstat: "pending", loc: "", week: "", jstat: "open", job: null, org: 0 };
let opts = null;
const $ = s => document.querySelector(s);
const fd = t => t ? dmy(String(t).slice(0, 10)) : "";
const ft = t => t ? String(t).replace(" ", "T").slice(11, 16) : "";
const pill = (t, c = "") => html`<span class="pill ${c}">${t}</span>`;
const kpi = (l, v, s) => html`<div class="kpi glass"><div class="l">${l}</div><div class="v">${v}</div><div class="s">${s}</div></div>`;
const seg = (id, act, cur, items) => html`<div class="seg" id="${id}">${items.map(([v, l]) => html`<button data-act="${act}" data-v="${v}" class="${String(cur) === String(v) ? "on" : ""}">${l}</button>`)}</div>`;
const closeAll = () => document.querySelectorAll(".scrim,.drawer,.modal").forEach(n => n.remove());
const drawer = inner => { closeAll(); document.body.insertAdjacentHTML("beforeend", out(html`<div class="scrim" data-act="h-close"></div><div class="drawer glass wide">${inner}</div>`)); };
const modal = inner => { closeAll(); document.body.insertAdjacentHTML("beforeend", out(html`<div class="scrim" data-act="h-close"></div><div class="modal glass">${inner}</div>`)); };
const debounce = (f, ms = 250) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => f(...a), ms); }; };
const SC = { P: "Present", A: "Absent", L: "Leave", H: "Half day", M: "Missing punch" }, SCC = { P: "active", L: "t", H: "t", A: "warn", M: "warn" };
const LS = { pending: "Pending", approved: "Approved", rejected: "Rejected", cancelled: "Cancelled" };
const TABS = o => [["overview", "Overview", 1], ["people", "People", 1], ["attendance", "Attendance", 1], ["roster", "Rosters", 1], ["leave", "Leave", 1], ["onboarding", "Onboarding", 1], ["jobs", "Recruitment", o.is_hr], ["org", "Org and headcount", o.is_hr]].filter(t => t[2]);
const lopts = sel => opts.locations.map(l => html`<option value="${l.id}" ${String(sel) === String(l.id) ? "selected" : ""}>${l.name}</option>`);
const act = (a, body, ok, again) => async el => { try { await api(a(el), { method: "POST", body: body(el) }); toast(ok); again(el); } catch (e) { toast(e.message, true); } };

export async function render(el) {
  opts = await api("/hr/options"); if (!TABS(opts).find(t => t[0] === st.tab)) st.tab = "overview";
  mount(el, html`<div class="head"><div><div class="eyebrow">Module 9</div><h1>People</h1><p class="muted">${opts.assumptions.scope}${opts.scope ? " You see your own location only." : ""}</p></div><div class="row">${seg("htabs", "h-tab", st.tab, TABS(opts).map(t => [t[0], t[1]]))}</div></div><div id="hbody"><div class="card glass"><div class="sk" style="height:120px"></div></div></div>`);
  load();
}
function load() {
  const f = { overview, people, attendance, roster, leave, onboarding, jobs, org }[st.tab];
  f().catch(e => { const b = $("#hbody"); if (b) b.innerHTML = out(html`<div class="card glass"><p class="muted">${e.message}</p></div>`); });
}
acts["h-tab"] = a => { st.tab = a.dataset.v; st.page = 1; document.querySelectorAll("#htabs button").forEach(b => b.classList.toggle("on", b === a)); load(); };
acts["h-close"] = closeAll;
const pager = (total, size, act) => html`<div class="row" style="justify-content:space-between;margin-top:10px"><span class="small muted">${num(total)} found</span><span class="row"><button class="btn sm" data-act="${act}" data-v="-1" ${st.page <= 1 ? "disabled" : ""}>Previous</button><button class="btn sm" data-act="${act}" data-v="1" ${st.page * size >= total ? "disabled" : ""}>Next</button></span></div>`;
const goto = (tab, extra = {}) => { Object.assign(st, extra); st.tab = tab; document.querySelectorAll("#htabs button").forEach(b => b.classList.toggle("on", b.dataset.v === tab)); load(); };

// ---------- overview ----------
async function overview() {
  const [s, c] = await Promise.all([api("/hr/summary"), api("/hr/celebrations?days=14")]), a = s.att;
  const k = [kpi("On the roll", num(s.headcount), `${num(s.notice)} on notice, ${num(s.joining)} joining`), kpi("Attendance, " + fd(s.att_date), pct(a.pct, 1), `${num(a.present)} present, ${num(a.absent)} absent, ${num(a.late)} late`),
    kpi("Leave waiting", num(s.leave_pending), `${num(s.leave_aged)} older than 3 days`), kpi("Missing punch-outs", num(s.missing_punch), "last 30 days"), kpi("Coverage gaps, 7 days", num(s.cover_gaps), "store days below 2 on shift")];
  if (opts.is_hr) k.push(kpi("Exits, 90 days", num(s.exits90), `${pct(s.attrition, 0)} annualised`), kpi("Open vacancies", num(s.vacancies), "from open job postings"));
  mount($("#hbody"), html`<div class="kpis">${k}</div><div class="cols eq"><div class="card solid"><div class="ct"><h2>Attendance, last 14 days</h2></div>${spark(s.trend.map(t => t.pct ?? 0), 520, 70)}<p class="small muted">Present share of people scheduled, leave excluded. Punches are simulated.</p>
    ${s.worst.length ? html`<div class="ct" style="margin-top:14px"><h2>Lowest attendance, 14 days</h2></div><table class="tbl"><tbody>${s.worst.map(w => html`<tr class="click" data-act="h-attloc" data-id="${w.id}"><td>${w.name}<div class="small muted">${w.city}</div></td><td class="num r">${pct(w.pct, 1)}</td></tr>`)}</tbody></table>` : ""}
    ${opts.is_hr && s.exit_hot.length ? html`<div class="ct" style="margin-top:14px"><h2>Most exits, 90 days</h2></div><table class="tbl"><tbody>${s.exit_hot.map(w => html`<tr><td>${w.name}</td><td class="num r">${w.n}</td></tr>`)}</tbody></table>` : ""}</div>
    <div class="card glass"><div class="ct"><h2>Next 14 days</h2></div><h3 class="small muted">Birthdays</h3>${c.birthdays.slice(0, 6).map(x => html`<div class="row" style="justify-content:space-between;padding:4px 0"><span>${x.name}<span class="small muted"> ${x.loc}</span></span><span class="num">${fd(x.date)}</span></div>`)}${c.birthdays.length ? "" : html`<p class="small muted">None.</p>`}
    <h3 class="small muted" style="margin-top:10px">Work anniversaries</h3>${c.anniversaries.slice(0, 5).map(x => html`<div class="row" style="justify-content:space-between;padding:4px 0"><span>${x.name}</span><span class="num">${x.years} yr, ${fd(x.date)}</span></div>`)}
    <h3 class="small muted" style="margin-top:10px">Joining</h3>${c.joiners.slice(0, 5).map(x => html`<div class="row" style="justify-content:space-between;padding:4px 0"><span>${x.name}<span class="small muted"> ${x.des}</span></span><span class="num">${fd(x.date)}</span></div>`)}${c.joiners.length ? "" : html`<p class="small muted">None.</p>`}</div></div>`);
}
acts["h-attloc"] = a => goto("attendance", { aloc: a.dataset.id, astat: "", page: 1 });

// ---------- people ----------
async function people() {
  const r = await api("/hr/employees?" + new URLSearchParams({ q: st.q, lt: st.lt, page: st.page, size: 25 }));
  mount($("#hbody"), html`<div class="card solid"><div class="ct"><h2>Directory</h2></div><div class="row" style="flex-wrap:wrap;gap:10px;margin-bottom:12px"><input class="input" id="hq" placeholder="Name or code" value="${st.q}" style="min-width:220px">${seg("hlt", "h-lt", st.lt, [["", "All"], ["office", "Office"], ["store", "Stores"], ["warehouse", "Warehouses"]])}</div>
    <div class="tblwrap"><table class="tbl"><thead><tr><th>Name</th><th>Role</th><th>Location</th><th>Manager</th><th>Joined</th><th>Status</th></tr></thead><tbody>${r.rows.map(e => html`<tr class="click" data-act="h-emp" data-id="${e.id}"><td><b>${e.name}</b><div class="small muted">${e.emp_code}</div></td><td>${e.des}<div class="small muted">${e.dept}</div></td><td>${e.loc}</td><td>${e.manager || ""}</td><td>${fd(e.join_date)}</td><td>${e.status === "active" ? pill("Active", "active") : pill(e.status === "notice" ? "Notice to " + fd(e.exit_date) : "Joining", "warn")}</td></tr>`)}</tbody></table></div>${pager(r.total, 25, "h-pg")}</div>`);
  $("#hq").addEventListener("input", debounce(e => { st.q = e.target.value; st.page = 1; people(); }));
}
acts["h-lt"] = a => { st.lt = a.dataset.v; st.page = 1; people(); }; acts["h-pg"] = a => { st.page += +a.dataset.v; load(); };
acts["h-emp"] = async a => {
  const d = await api("/hr/employees/" + a.dataset.id), p = d.profile, at = d.att30;
  drawer(html`<h1 style="font-size:22px">${p.name}</h1><p class="muted">${p.des}, ${p.dept}. ${p.lname}. ${p.emp_code}</p>${d.manager ? html`<p class="small muted">Reports to ${d.manager.name} (${d.manager.des}). ${d.reports ? d.reports + " direct reports." : ""}</p>` : ""}
    <div class="kpis">${kpi("Present, 30 days", num((at.P || 0) + (at.H || 0)), `${at.A || 0} absent, ${at.M || 0} missing punch`)}${d.balances.map(b => kpi(b.name, `${b.left} left`, `${b.used} used, ${b.pending} pending of ${b.q}`))}</div>
    ${p.email ? html`<p class="small muted">${p.email}. Born ${fd(p.birth_date)}. Joined ${fd(p.join_date)}.</p>` : ""}
    <h2 style="margin-top:12px">Next 7 days</h2><p class="small">${d.roster.length ? d.roster.map(r => `${fd(r.date)} ${r.code.toLowerCase()}`).join(", ") : "Nothing rostered."}</p>
    <h2 style="margin-top:12px">Recent leave</h2><table class="tbl"><tbody>${d.leave.map(l => html`<tr><td>${l.code}</td><td>${fd(l.from_date)} to ${fd(l.to_date)}</td><td class="num r">${l.days} d</td><td>${pill(LS[l.status], l.status === "approved" ? "active" : "")}</td></tr>`)}</tbody></table>
    ${d.onboarding.length ? html`<h2 style="margin-top:12px">Onboarding</h2><p class="small">${d.onboarding.filter(t => t.done_at).length} of ${d.onboarding.length} tasks done.</p>` : ""}
    ${opts.is_hr && p.status === "active" ? html`<div class="row" style="margin-top:14px"><button class="btn" data-act="h-resign" data-id="${p.id}">Put on notice</button></div>` : ""}${opts.is_hr && p.status === "notice" ? html`<div class="row" style="margin-top:14px"><button class="btn" data-act="h-withdraw" data-id="${p.id}">Withdraw resignation</button></div>` : ""}`);
};
acts["h-resign"] = a => modal(html`<h1 style="font-size:22px">Put on notice</h1><p class="small muted">Notice is ${30} days. Shorter needs the CEO or admin. Future roster days after the last day are removed.</p><label class="small muted">Last working day</label><input class="input" id="x-d" type="date" style="width:100%"><label class="small muted" style="display:block;margin-top:10px">Reason</label><input class="input" id="x-r" style="width:100%"><div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-act="h-close">Cancel</button><button class="btn pri" data-act="h-resign-go" data-id="${a.dataset.id}">Save</button></div>`);
acts["h-resign-go"] = act(a => `/hr/employees/${a.dataset.id}/exit`, () => ({ action: "resign", last_day: $("#x-d").value, reason: $("#x-r").value }), "Notice recorded", () => { closeAll(); load(); });
acts["h-withdraw"] = act(a => `/hr/employees/${a.dataset.id}/exit`, () => ({ action: "withdraw" }), "Resignation withdrawn", () => { closeAll(); load(); });

// ---------- attendance ----------
async function attendance() {
  const r = await api("/hr/attendance?" + new URLSearchParams({ date_: st.adate, location_id: st.aloc, status: st.astat, page: st.page, size: 30 })), c = r.counts;
  mount($("#hbody"), html`<div class="card solid"><div class="ct"><h2>Attendance sheet</h2><span class="small muted">${opts.assumptions.fix}. ${opts.assumptions.late}.</span></div><div class="row" style="flex-wrap:wrap;gap:10px;margin-bottom:12px"><input class="input" id="ad" type="date" value="${r.date}">${opts.scope ? "" : html`<select class="input" id="al"><option value="">All locations</option>${lopts(st.aloc)}</select>`}
    ${seg("ast", "h-ast", st.astat, [["", "All"], ["M", `Missing ${c.M || 0}`], ["A", `Absent ${c.A || 0}`], ["late", "Late"], ["L", `Leave ${c.L || 0}`]])}</div>
    <div class="tblwrap"><table class="tbl"><thead><tr><th>Name</th><th>Shift</th><th>In</th><th>Out</th><th class="r">Hours</th><th>Status</th><th></th></tr></thead><tbody>${r.rows.map(x => html`<tr><td>${x.name}<div class="small muted">${x.des}</div></td><td>${x.shift || ""}</td><td class="num">${ft(x.punch_in)} ${x.late ? pill("Late", "warn") : ""}</td><td class="num">${ft(x.punch_out)}</td><td class="num r">${x.hours ?? ""}</td><td>${pill(SC[x.status], SCC[x.status])}${x.fixed ? pill("Fixed") : ""}</td><td>${x.can_fix ? html`<button class="btn sm" data-act="h-fix" data-id="${x.employee_id}" data-d="${r.date}" data-s="${x.status}">Fix</button>` : ""}</td></tr>`)}</tbody></table></div>${pager(r.total, 30, "h-pg")}</div>`);
  $("#ad").onchange = e => { st.adate = e.target.value; st.page = 1; attendance(); }; const al = $("#al"); if (al) al.onchange = e => { st.aloc = e.target.value; st.page = 1; attendance(); };
}
acts["h-ast"] = a => { st.astat = a.dataset.v; st.page = 1; attendance(); };
acts["h-fix"] = a => modal(html`<h1 style="font-size:22px">Fix punch</h1><p class="small muted">Use 24 hour times like 18:30. An absent day needs both times and HR.</p><label class="small muted">Punch in${a.dataset.s === "A" ? "" : " (optional)"}</label><input class="input" id="f-i" placeholder="09:30" style="width:100%"><label class="small muted" style="display:block;margin-top:10px">Punch out</label><input class="input" id="f-o" placeholder="18:30" style="width:100%"><label class="small muted" style="display:block;margin-top:10px">Reason</label><input class="input" id="f-r" style="width:100%"><div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-act="h-close">Cancel</button><button class="btn pri" data-act="h-fix-go" data-id="${a.dataset.id}" data-d="${a.dataset.d}">Save</button></div>`);
acts["h-fix-go"] = act(() => "/hr/attendance/fix", a => ({ employee_id: +a.dataset.id, date: a.dataset.d, punch_in: $("#f-i").value || null, punch_out: $("#f-o").value, reason: $("#f-r").value }), "Punch corrected", () => { closeAll(); attendance(); });

// ---------- roster ----------
async function roster() {
  if (!st.loc) st.loc = opts.scope || (opts.locations.find(l => l.type === "store") || opts.locations[0]).id;
  const r = await api(`/hr/roster?location_id=${st.loc}&week=${st.week}`), D = r.cover.map(c => c.date), C = { MORNING: "M", EVENING: "E", GENERAL: "G" };
  mount($("#hbody"), html`<div class="card solid"><div class="ct"><h2>Roster, week of ${fd(r.week)}</h2><span class="small muted">${opts.assumptions.week}. Past days are locked.</span></div><div class="row" style="flex-wrap:wrap;gap:10px;margin-bottom:12px">${opts.scope ? "" : html`<select class="input" id="rl">${lopts(st.loc)}</select>`}<button class="btn" data-act="h-wk" data-v="-7">Previous week</button><button class="btn" data-act="h-wk" data-v="7">Next week</button><button class="btn" data-act="h-copy">Copy last week</button></div>
    <div class="tblwrap"><table class="tbl"><thead><tr><th>Name</th>${D.map(d => html`<th class="r">${new Date(d + "T00:00").toLocaleDateString("en-IN", { weekday: "short", day: "numeric" })}</th>`)}<th class="r">Hours</th></tr></thead><tbody>${r.rows.map(x => html`<tr><td>${x.name}<div class="small muted">${x.des}</div></td>${x.days.map(d => html`<td class="r">${d.locked ? html`<span class="muted">${d.leave ? "L" : C[d.shift] || "-"}</span>` : html`<select class="input" data-act="h-cell" data-e="${x.id}" data-d="${d.date}" style="padding:2px 4px"><option value="">${d.leave ? "Off (leave)" : "Off"}</option>${Object.entries(C).filter(([k]) => (k === "GENERAL") === (opts.locations.find(l => String(l.id) === String(st.loc)).type !== "store")).map(([k, v]) => html`<option value="${k}" ${d.shift === k ? "selected" : ""}>${v}</option>`)}</select>`}</td>`)}<td class="num r">${x.hours}</td></tr>`)}
    <tr><td><b>On shift</b></td>${r.cover.map(c => html`<td class="num r">${c.gap ? pill(c.n, "warn") : c.n}</td>`)}<td></td></tr></tbody></table></div><p class="small muted" style="margin-top:8px">M is morning 09:00 to 17:00, E is evening 13:00 to 21:30, G is general 09:30 to 18:30. Minimum ${r.min_cover || "none"} on shift.</p></div>`);
  const rl = $("#rl"); if (rl) rl.onchange = e => { st.loc = e.target.value; roster(); };
  document.querySelectorAll("select[data-act=h-cell]").forEach(s => s.onchange = async e => { try { const x = await api("/hr/roster", { method: "PUT", body: { employee_id: +s.dataset.e, date: s.dataset.d, shift: e.target.value || null } }); toast(x.warning || "Saved", !!x.warning); roster(); } catch (er) { toast(er.message, true); roster(); } });
}
acts["h-wk"] = a => { const d = new Date((st.week || new Date().toISOString().slice(0, 10)) + "T00:00"); d.setDate(d.getDate() + +a.dataset.v); st.week = d.toISOString().slice(0, 10); roster(); };
acts["h-copy"] = async () => { try { const d = new Date((st.week || new Date().toISOString().slice(0, 10)) + "T00:00"); const x = await api("/hr/roster/copy", { method: "POST", body: { location_id: +st.loc, week: st.week || d.toISOString().slice(0, 10) } }); toast(`Copied ${x.copied} shifts`); roster(); } catch (e) { toast(e.message, true); } };

// ---------- leave ----------
async function leave() {
  const r = await api("/hr/leave?" + new URLSearchParams({ status: st.lstat, page: st.page, size: 25 }));
  mount($("#hbody"), html`<div class="card solid"><div class="ct"><h2>Leave and work from home</h2><button class="btn pri" data-act="h-lnew">New request</button></div><div class="row" style="margin-bottom:12px">${seg("hls", "h-ls", st.lstat, [["pending", "Pending"], ["approved", "Approved"], ["rejected", "Rejected"], ["cancelled", "Cancelled"]])}</div><p class="small muted" style="margin-bottom:8px">${opts.assumptions.leave}. ${opts.assumptions.cover}.</p>
    <div class="tblwrap"><table class="tbl"><thead><tr><th>Name</th><th>Type</th><th>Dates</th><th class="r">Days</th><th>Applied</th><th></th></tr></thead><tbody>${r.rows.map(x => html`<tr><td>${x.name}<div class="small muted">${x.loc}</div></td><td>${x.code}</td><td>${fd(x.from_date)} to ${fd(x.to_date)}</td><td class="num r">${x.days}</td><td>${fd(x.applied_on)} ${x.aged ? pill("Waiting", "warn") : ""}${x.risk ? pill("Coverage", "warn") : ""}</td><td>${x.status === "pending" ? html`<button class="btn sm" data-act="h-ld" data-id="${x.id}" data-a="approve">Approve</button> <button class="btn sm" data-act="h-ld" data-id="${x.id}" data-a="reject">Reject</button>` : x.status === "approved" ? html`<button class="btn sm" data-act="h-ld" data-id="${x.id}" data-a="cancel">Cancel</button>` : x.decision_note || ""}</td></tr>`)}</tbody></table></div>${pager(r.total, 25, "h-pg")}</div>`);
}
acts["h-ls"] = a => { st.lstat = a.dataset.v; st.page = 1; leave(); };
acts["h-ld"] = async a => {
  const b = { action: a.dataset.a }; if (b.action === "reject") { b.note = prompt("Reason for rejecting"); if (!b.note) return; }
  try { await api(`/hr/leave/${a.dataset.id}/decide`, { method: "POST", body: b }); toast("Done"); leave(); }
  catch (e) { if (opts.is_hr && /Coverage/.test(e.message) && confirm(e.message + "\n\nApprove with override?")) { await api(`/hr/leave/${a.dataset.id}/decide`, { method: "POST", body: { ...b, force: true } }); toast("Approved with override"); leave(); } else toast(e.message, true); }
};
acts["h-lnew"] = async () => {
  const e = await api("/hr/employees?size=100"), t = opts.leave_types;
  modal(html`<h1 style="font-size:22px">New leave request</h1><label class="small muted">Employee</label><select class="input" id="l-e" style="width:100%">${e.rows.map(x => html`<option value="${x.id}">${x.name} (${x.emp_code})</option>`)}</select><label class="small muted" style="display:block;margin-top:10px">Type</label><select class="input" id="l-t" style="width:100%">${t.map(x => html`<option value="${x.code}">${x.name}</option>`)}</select>
    <div class="frm"><div><label>From</label><input class="input" id="l-f" type="date"></div><div><label>To</label><input class="input" id="l-to" type="date"></div></div><label class="small muted" style="display:block;margin-top:10px">Reason</label><input class="input" id="l-r" style="width:100%"><div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-act="h-close">Cancel</button><button class="btn pri" data-act="h-lgo">Submit</button></div>`);
};
acts["h-lgo"] = act(() => "/hr/leave", () => ({ employee_id: +$("#l-e").value, type: $("#l-t").value, from_date: $("#l-f").value, to_date: $("#l-to").value, reason: $("#l-r").value }), "Request raised", () => { closeAll(); leave(); });

// ---------- onboarding ----------
async function onboarding() {
  const r = await api("/hr/onboarding");
  mount($("#hbody"), html`<div class="card solid"><div class="ct"><h2>New joiners</h2><span class="small muted">${num(r.overdue)} tasks overdue</span></div><div class="tblwrap"><table class="tbl"><thead><tr><th>Name</th><th>Joins</th><th>Progress</th><th>Tasks</th></tr></thead><tbody>${r.rows.map(x => html`<tr><td>${x.name}<div class="small muted">${x.des}, ${x.loc}</div></td><td>${fd(x.join_date)} ${x.joined ? "" : pill("Upcoming", "t")}</td><td class="num">${x.done} of ${x.total} ${x.overdue ? pill(x.overdue + " overdue", "warn") : ""}</td><td>${x.tasks.map(t => html`<label class="small" style="display:inline-block;margin-right:10px"><input type="checkbox" data-act="h-task" data-id="${t.id}" ${t.done_at ? "checked" : ""}> ${t.task}${t.overdue ? " (due " + fd(t.due_date) + ")" : ""}</label>`)}</td></tr>`)}</tbody></table></div></div>`);
}
acts["h-task"] = async a => { try { await api(`/hr/onboarding/tasks/${a.dataset.id}/done`, { method: "POST", body: { done: a.checked } }); toast(a.checked ? "Marked done" : "Reopened"); } catch (e) { toast(e.message, true); a.checked = !a.checked; } };

// ---------- recruitment ----------
async function jobs() {
  if (st.job) return jobView();
  const r = await api("/hr/jobs?status=" + st.jstat);
  mount($("#hbody"), html`<div class="card solid"><div class="ct"><h2>Job postings</h2><button class="btn pri" data-act="h-jnew">New posting</button></div><div class="row" style="margin-bottom:12px">${seg("hjs", "h-js", st.jstat, [["open", "Open"], ["closed", "Closed"]])}</div><div class="tblwrap"><table class="tbl"><thead><tr><th>Role</th><th>Team</th><th class="r">Openings</th><th class="r">In pipeline</th><th class="r">Hired</th><th class="r">Age</th></tr></thead><tbody>${r.rows.map(j => html`<tr class="click" data-act="h-job" data-id="${j.id}"><td>${j.title}</td><td>${j.dept}</td><td class="num r">${j.openings}</td><td class="num r">${j.active} ${j.thin ? pill("Thin", "warn") : ""}</td><td class="num r">${j.hired}</td><td class="num r">${j.age} d</td></tr>`)}</tbody></table></div><p class="small muted" style="margin-top:8px">Thin means fewer than three active candidates per open seat. Open postings are also served at /api/public/careers for the website.</p></div>`);
}
acts["h-js"] = a => { st.jstat = a.dataset.v; jobs(); }; acts["h-job"] = a => { st.job = a.dataset.id; jobs(); };
async function jobView() {
  const r = await api("/hr/jobs/" + st.job), j = r.job;
  mount($("#hbody"), html`<div class="card solid"><div class="ct"><h2>${j.title}</h2><span class="row"><button class="btn" data-act="h-jback">Back</button>${j.status === "open" ? html`<button class="btn" data-act="h-anew">Add candidate</button><button class="btn" data-act="h-jclose">Close posting</button>` : ""}</span></div><table class="tbl"><thead><tr><th>Candidate</th><th>Source</th><th>Applied</th><th>Stage</th><th></th></tr></thead><tbody>${r.applicants.map(a => html`<tr><td>${a.name}<div class="small muted">${a.email}</div></td><td>${a.source}</td><td>${fd(a.applied_on)}</td><td>${pill(a.stage, a.stage === "Hired" ? "active" : a.stage === "Rejected" ? "warn" : "t")}</td><td>${j.status === "open" ? r.next[a.stage].map(n => html`<button class="btn sm" data-act="h-stage" data-id="${a.id}" data-s="${n}">${n === "Rejected" ? "Reject" : "Move to " + n}</button> `) : ""}</td></tr>`)}</tbody></table></div>`);
}
acts["h-jback"] = () => { st.job = null; jobs(); };
acts["h-jclose"] = act(() => `/hr/jobs/${st.job}/close`, () => ({}), "Posting closed", () => jobs());
acts["h-stage"] = async a => {
  const b = { stage: a.dataset.s };
  if (b.stage === "Hired") { b.birth_date = prompt("Date of birth (YYYY-MM-DD)"); if (!b.birth_date) return; b.join_date = prompt("Join date (YYYY-MM-DD), blank for 14 days from today") || null; }
  try { const x = await api(`/hr/applicants/${a.dataset.id}/stage`, { method: "POST", body: b }); toast(x.employee_id ? "Hired. Employee record and onboarding tasks created" : "Stage updated"); jobs(); } catch (e) { toast(e.message, true); }
};
acts["h-anew"] = () => modal(html`<h1 style="font-size:22px">Add candidate</h1><label class="small muted">Name</label><input class="input" id="a-n" style="width:100%"><label class="small muted" style="display:block;margin-top:10px">Email</label><input class="input" id="a-e" style="width:100%"><div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-act="h-close">Cancel</button><button class="btn pri" data-act="h-ago">Add</button></div>`);
acts["h-ago"] = act(() => "/hr/applicants", () => ({ job_id: +st.job, name: $("#a-n").value, email: $("#a-e").value }), "Candidate added", () => { closeAll(); jobs(); });
acts["h-jnew"] = () => modal(html`<h1 style="font-size:22px">New posting</h1><label class="small muted">Title</label><input class="input" id="j-t" style="width:100%"><div class="frm"><div><label>Department</label><select class="input" id="j-d">${opts.departments.map(d => html`<option value="${d.id}">${d.name}</option>`)}</select></div><div><label>Designation</label><select class="input" id="j-g">${opts.designations.map(d => html`<option value="${d.id}">${d.title}</option>`)}</select></div><div><label>Location</label><select class="input" id="j-l"><option value="">Head office</option>${lopts("")}</select></div><div><label>Openings</label><input class="input" id="j-o" type="number" value="1"></div></div><div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn" data-act="h-close">Cancel</button><button class="btn pri" data-act="h-jgo">Create</button></div>`);
acts["h-jgo"] = act(() => "/hr/jobs", () => ({ title: $("#j-t").value, department_id: +$("#j-d").value, designation_id: +$("#j-g").value, location_id: $("#j-l").value ? +$("#j-l").value : null, openings: +$("#j-o").value }), "Posting created", () => { closeAll(); jobs(); });

// ---------- org and headcount ----------
async function org() {
  const [o, h] = await Promise.all([api("/hr/org?id=" + st.org), api("/hr/headcount")]), n = o.node;
  mount($("#hbody"), html`<div class="cols eq"><div class="card solid"><div class="ct"><h2>Org chart</h2></div><p class="small muted">${o.chain.map(c => html`<a href="#/hr" data-act="h-org" data-id="${c.id}">${c.name}</a> / `)}</p><p><b>${n.name}</b> <span class="muted">${n.des}, ${n.dept}</span></p><table class="tbl"><tbody>${o.reports.map(r => html`<tr class="click" data-act="h-org" data-id="${r.id}"><td>${r.name}<div class="small muted">${r.des}, ${r.loc}</div></td><td class="num r">${r.n ? r.n + " reports" : ""}</td></tr>`)}</tbody></table><p class="small muted" style="margin-top:6px">${o.total > 60 ? `Showing 60 of ${o.total}. ` : ""}Click a row to open that person's team.</p></div>
    <div class="card solid"><div class="ct"><h2>Warehouse exits, 90 days</h2></div><table class="tbl"><tbody>${h.warehouses.slice(0, 6).map(w => html`<tr><td>${w.name}</td><td class="num r">${w.exits90} of ${w.staff + w.exits90}</td><td class="num r">${pct(w.exit_pct, 0)}</td></tr>`)}</tbody></table>
    <div class="ct" style="margin-top:14px"><h2>Stores below standard</h2><span class="small muted">${h.stores_total} stores</span></div><table class="tbl"><tbody>${h.stores.slice(0, 8).map(s => html`<tr><td>${s.name}<div class="small muted">${s.city}, tier ${s.tier}</div></td><td class="num r">${s.active} of ${s.standard}</td><td class="num r">${s.notice ? s.notice + " on notice" : ""}</td></tr>`)}</tbody></table><p class="small muted" style="margin-top:6px">${h.note}</p></div></div>`);
}
acts["h-org"] = a => { st.org = +a.dataset.id; org(); };
