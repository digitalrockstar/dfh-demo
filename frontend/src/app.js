import { html, out, raw, esc, prov } from "./ui.js";
import { S, api, acts, applyTheme, logout, mount, toast } from "./core.js";
import * as ct from "./page_ct.js";
import * as sku from "./page_sku.js";
import * as wastage from "./page_wastage.js";
import * as demand from "./page_demand.js";
import * as proc from "./page_procurement.js";
import * as pos from "./page_pos.js";
import * as inv from "./page_inv.js";
import * as fin from "./page_finance.js";
import * as crm from "./page_crm.js";
import * as hr from "./page_hr.js";
import * as plat from "./page_platform.js";

const NAV = [
  ["Overview", [["control-tower", "Control Tower", 1, 1], ["skus", "SKU master", 2, 1]]],
  ["Operations", [["pos", "Store POS", "P", 1], ["inventory", "Inventory and warehouse", 4, 1], ["procurement", "Procurement and logistics", 3, 1], ["wastage", "Wastage and shrink", 5, 1], ["demand", "Demand and replenishment", 6, 1]]],
  ["Business", [["finance", "Finance and tax", 7, 1], ["customers", "Customers and WhatsApp", 8, 1], ["hr", "People", 9, 1], ["platform", "Platform", 10, 1]]]];
const SOON = {
  inventory: ["A stock ledger by location and batch with expiry, so every kilo has a history.", "Batches, FEFO picking, transfers and in-transit stock", "Store indents, repacking with yield loss, cycle counts", "Bulk and corporate order desk"],
  procurement: ["Vendor price book, landed cost, purchase orders and shipment tracking from booking to receipt.", "Landed cost with freight, duty, clearing and FX", "GRN with batch and expiry, three-way match", "Vendor scorecards and best-vendor suggestions"],
  wastage: ["Reason coded loss capture, near-expiry actions and shrink by location.", "Quick entry in store and warehouse with photo", "Near-expiry list at 60, 30 and 15 days with markdown suggestions", "Wastage by store, SKU and vendor"],
  demand: ["Seasonal forecasts and reorder suggestions that respect import lead times.", "Festival calendar uplift, store and SKU forecasts", "Suggested POs and store indents for approval", "Assortment by store cluster"],
  finance: ["Day-close reconciliation, GST working data and vendor payables. GSP integration is on hold and rates are stated assumptions.", "Settlement reconciliation against bank and gateway files", "Input credit matching and purchase register", "Journal export for Oracle, Tally or CSV"],
  customers: ["Customer record from phone numbers captured at the counter, loyalty and WhatsApp ordering.", "Customer 360 and segments", "WhatsApp order inbox into dispatch", "Corporate gifting quotes"],
  platform: ["Roles, approvals, audit log viewer, imports, multi-entity and multi-currency settings.", "Approval rules by amount", "Audit log viewer", "Sync and job health"]};
const ROLE = { ceo: "CEO", finance: "Finance", procurement: "Procurement", warehouse: "Warehouse", store_manager: "Store manager", cashier: "Cashier", hr: "HR", marketing: "Marketing", admin: "Admin" };
const root = document.getElementById("root");

function login() {
  mount(root, html`<div class="login"><div class="box glass"><img src="/assets/logo.png" alt="Dry Fruit House"><h1 style="text-align:center;font-size:21px">Operations Platform</h1><p class="muted small" style="text-align:center;margin-top:4px">Demo on synthetic data</p>
    <label>Username</label><input class="input" id="u" value="ceo" autocomplete="username"><label>Password</label><input class="input" id="p" type="password" value="demo1234" autocomplete="current-password">
    <button class="btn pri" data-act="do-login">Sign in</button><p class="small muted" style="margin-top:14px">Try: ceo, finance, procurement, warehouse, storemgr, cashier, hr. Password for all is demo1234.</p></div></div>`);
  root.querySelectorAll("input").forEach(i => i.addEventListener("keydown", e => e.key === "Enter" && acts["do-login"]()));
}
acts["do-login"] = async () => {
  try {
    const r = await api("/login", { method: "POST", body: { username: document.querySelector("#u").value, password: document.querySelector("#p").value } });
    S.token = r.token; localStorage.setItem("dfh_token", r.token); location.hash = "#/control-tower"; boot();
if ("serviceWorker" in navigator) addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
  } catch (e) { toast(e.message, true); }
};

const flat = () => NAV.flatMap(g => g[1]);
function shell() {
  const u = S.user, open = localStorage.getItem("dfh_panel") === "1";
  mount(root, html`<div class="app" data-panel="${open ? "open" : "shut"}"><aside class="side glass"><div class="brand"><div class="mark">DFH</div><div class="bt"><b>Dry Fruit House</b><span>Operations Platform</span></div></div>
    <nav class="nav" aria-label="Modules">${NAV.map(([g, items]) => html`<div class="grp">${g}</div>${items.map(([id, l, n, built]) => html`<a href="#/${built ? id : "soon/" + id}" data-id="${id}" title="${l}"><span class="n">${n}</span><span class="lb">${l}</span>${built ? "" : html`<span class="soon">SOON</span>`}</a>`)}`)}</nav>
    <div class="me"><div class="av">${u.name[0]}</div><div class="t"><b>${u.name}</b><span>${ROLE[u.role] || u.role}</span></div></div></aside>
    <div class="col"><header class="pulse glass"><h2 id="ptitle">Control Tower</h2>
      <button class="raised pbtn" data-act="pal" aria-haspopup="dialog" aria-label="Search or jump to a page"><span>Search or jump to</span><kbd>⌘K</kbd></button>
      <span class="pstat small muted" role="status"><i class="pdot" id="pdot"></i><span id="pnet">Online</span><span class="num" id="ptime"></span></span>
      <span class="pbtns"><button class="icon" data-act="ip" aria-controls="ipanel" aria-expanded="${open}" aria-label="Insights" title="Insights">◧</button><button class="icon" data-act="settings" aria-label="Appearance" title="Appearance">◐</button><button class="icon" data-act="out" aria-label="Sign out" title="Sign out">⏻</button></span></header>
      <main id="view"></main></div>
    <aside id="ipanel" class="ipanel glass" aria-label="Insights" aria-hidden="${!open}"><div class="iph"><h2>Insights ${prov("sample")}</h2><button class="icon" data-act="ip" aria-label="Close insights">✕</button></div><div id="ipbody" class="ipbody"></div></aside></div>`);
  pulse(); if (open) loadPanel();
}
let clock;
function pulse() {
  const t = document.getElementById("ptime"), net = document.getElementById("pnet"), dot = document.getElementById("pdot");
  const tick = () => { if (t) t.textContent = new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata" }) + " IST"; };
  const st = () => { const on = navigator.onLine; if (net) net.textContent = on ? "Online" : "Offline"; if (dot) dot.dataset.on = on; };
  tick(); st(); clearInterval(clock); clock = setInterval(tick, 30000); addEventListener("online", st); addEventListener("offline", st);
}
async function loadPanel() {
  const b = document.getElementById("ipbody"); if (!b || b.dataset.ok) return;
  try {
    const ex = await api("/ct/exceptions");
    mount(b, html`${ex.length ? ex.slice(0, 8).map(e => html`<div class="ipx"><span class="dot ${e.severity}"></span><div><b>${e.title}</b><p>${e.detail}</p></div></div>`) : html`<p class="muted small">Nothing needs attention.</p>`}<a class="btn" href="#/control-tower" style="margin-top:12px;display:inline-block">Open Control Tower</a>`); b.dataset.ok = 1;
  } catch (e) { mount(b, html`<p class="muted small">Not available for your role.</p>`); }
}
acts.ip = () => {
  const app = document.querySelector(".app"); if (!app) return;
  const open = app.dataset.panel !== "open"; app.dataset.panel = open ? "open" : "shut"; localStorage.setItem("dfh_panel", open ? "1" : "0");
  document.getElementById("ipanel").setAttribute("aria-hidden", !open); document.querySelectorAll("[data-act=ip][aria-expanded]").forEach(x => x.setAttribute("aria-expanded", open));
  if (open) loadPanel();
};
// Command palette (Cmd/Ctrl+K)
const palItems = () => [
  ...flat().map(([id, l, , built]) => ({ t: l, k: "Go to", run: () => { location.hash = built ? "#/" + id : "#/soon/" + id; } })),
  ...[["light", "Light"], ["auto", "Auto"], ["dark", "Dark"]].map(([v, l]) => ({ t: "Theme: " + l, k: "Appearance", run: () => acts["set-mode"]({ dataset: { v } }) })),
  ...["dfh", "ops", "walnut", "pistachio", "indigo"].map(v => ({ t: "Tone: " + v, k: "Appearance", run: () => acts["set-tone"]({ dataset: { v } }) })),
  { t: "Appearance settings", k: "Action", run: () => acts.settings() }, { t: "Toggle insight panel", k: "Action", run: () => acts.ip() }, { t: "Sign out", k: "Action", run: logout }];
let palLast = null;
function palClose() { document.getElementById("pal")?.remove(); palLast?.focus?.(); }
function palOpen() {
  if (!S.user || document.getElementById("pal")) return;
  palLast = document.activeElement; const items = palItems(); let view = [], sel = 0;
  document.body.insertAdjacentHTML("beforeend", out(html`<div class="palwrap" id="pal"><div class="palbox glass" role="dialog" aria-modal="true" aria-label="Command palette"><input class="input" id="palq" placeholder="Go to a page or run an action" autocomplete="off" role="combobox" aria-expanded="true" aria-controls="pall"><ul id="pall" role="listbox"></ul></div></div>`));
  const q = document.getElementById("palq"), ul = document.getElementById("pall");
  const draw = () => {
    const s = q.value.trim().toLowerCase(); view = items.filter(i => !s || (i.t + " " + i.k).toLowerCase().includes(s)).slice(0, 12); if (sel >= view.length) sel = 0;
    ul.innerHTML = view.length ? out(html`${view.map((i, n) => html`<li id="pal-${n}" role="option" aria-selected="${n === sel}" data-n="${n}"><span>${i.t}</span><small>${i.k}</small></li>`)}`) : '<li class="none">No match</li>';
    q.setAttribute("aria-activedescendant", view.length ? "pal-" + sel : "");
  };
  const go = n => { const i = view[n]; if (!i) return; palClose(); i.run(); };
  q.addEventListener("input", () => { sel = 0; draw(); });
  q.addEventListener("keydown", e => {
    if (e.key === "Escape") { e.stopPropagation(); palClose(); } else if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(sel + 1, view.length - 1); draw(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(sel - 1, 0); draw(); } else if (e.key === "Enter") { e.preventDefault(); go(sel); }
  });
  ul.addEventListener("click", e => { const li = e.target.closest("li[data-n]"); if (li) go(+li.dataset.n); });
  document.getElementById("pal").addEventListener("mousedown", e => { if (e.target.id === "pal") palClose(); });
  draw(); q.focus();
}
acts.pal = palOpen;
document.addEventListener("keydown", e => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); document.getElementById("pal") ? palClose() : palOpen(); } });
acts.out = logout;
acts.settings = () => {
  const old = document.querySelector(".set"); if (old) return old.remove();
  const t = S.theme, tones = [["dfh", "#1A0E0E", "#E4A80C"], ["ops", "#334155", "#0F766E", "#F59E0B"], ["walnut", "#7A4B2A", "#7C9A5B", "#E0A526"], ["pistachio", "#2F6B4F", "#A8C686", "#C8643B"], ["indigo", "#2B3A8C", "#6B3FA0", "#D9A441"]];
  document.body.insertAdjacentHTML("beforeend", out(html`<div class="set glass"><h3>Appearance</h3><div class="seg" id="mode">${["light", "auto", "dark"].map(m => html`<button data-act="set-mode" data-v="${m}" class="${t.mode === m ? "on" : ""}">${m[0].toUpperCase() + m.slice(1)}</button>`)}</div>
    <h3>Color tone</h3><div class="tones" id="tones">${tones.map(([k, ...c]) => html`<button data-act="set-tone" data-v="${k}" class="${t.tone === k ? "on" : ""}" title="${k}">${c.map(x => raw(`<i style="background:${x}"></i>`))}</button>`)}</div>
    <h3>Glass effect <span id="gv" style="float:right;text-transform:none;letter-spacing:0">${Math.round(t.glass * 100)}%</span></h3><input class="range" type="range" min="0" max="100" value="${Math.round(t.glass * 100)}" id="gl"><p class="small muted" style="margin-top:6px">Applies to panels and the sidebar. Tables stay solid for legibility.</p></div>`));
  document.querySelector("#gl").oninput = e => { S.theme.glass = e.target.value / 100; document.querySelector("#gv").textContent = e.target.value + "%"; applyTheme(); };
};
const pick = (id, key, a) => { S.theme[key] = a.dataset.v; applyTheme(); document.querySelectorAll(`#${id} button`).forEach(b => b.classList.toggle("on", b === a)); };
acts["set-mode"] = a => pick("mode", "mode", a); acts["set-tone"] = a => pick("tones", "tone", a);
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyTheme);

async function route() {
  try { await route0(); } catch (e) {
    if (e instanceof TypeError) mount(document.getElementById("view"), html`<div class="head"><div><h1>You are offline</h1><p class="muted">This screen needs the server. <a href="#/pos">Store POS</a> keeps working without a connection.</p></div></div>`);
    else throw e;
  }
}
async function route0() {
  if (!S.user) return;
  const [, page = "control-tower", param] = (location.hash || "#/control-tower").split("/");
  document.querySelectorAll(".nav a").forEach(a => a.classList.toggle("on", a.dataset.id === (page === "soon" ? param : page)));
  const pt = document.getElementById("ptitle"), cur = flat().find(x => x[0] === (page === "soon" ? param : page)); if (pt && cur) pt.textContent = cur[1];
  const v = document.getElementById("view");
  if (page === "skus") { if (!v.dataset.p || v.dataset.p !== "skus") { v.dataset.p = "skus"; await sku.render(v, param); } return; }
  v.dataset.p = page;
  if (page === "control-tower") return ct.render(v);
  if (page === "wastage") return wastage.render(v);
  if (page === "demand") return demand.render(v);
  if (page === "procurement") return proc.render(v);
  if (page === "pos") return pos.render(v);
  if (page === "inventory") return inv.render(v);
  if (page === "finance") return fin.render(v);
  if (page === "customers") return crm.render(v);
  if (page === "hr") return hr.render(v);
  if (page === "platform") return plat.render(v);
  const d = SOON[param] || SOON.platform, label = NAV.flatMap(g => g[1]).find(x => x[0] === param);
  mount(v, html`<div class="head"><div><div class="eyebrow">${label ? "Module " + label[2] : ""}</div><h1>${label ? label[1] : "Coming soon"}</h1></div></div><div class="soonbox glass"><p>${d[0]}</p><ul>${d.slice(1).map(x => html`<li>${x}</li>`)}</ul><p class="small muted" style="margin-top:16px">Built after the modules above it. The plan and order are in the product book.</p></div>`);
}
addEventListener("hashchange", route);

async function boot() {
  applyTheme();
  if (!S.token) return login();
  try { S.user = await api("/me"); localStorage.setItem("dfh_user", JSON.stringify(S.user)); }
  catch (e) {
    const c = localStorage.getItem("dfh_user");
    if (e instanceof TypeError && c) S.user = JSON.parse(c); else return login();
  }
  shell(); route();
}
boot();
if ("serviceWorker" in navigator) addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
