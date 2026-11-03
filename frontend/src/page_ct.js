import { html, raw, out, inr, pct, num, deltaPill, trendChart, esc } from "./ui.js";
import { api, acts, mount } from "./core.js";

const PERIODS = [[7, "7 days"], [30, "30 days"], [90, "90 days"], [184, "6 months"]];
const st = { days: 30, region: "", order: "top", tier: "" };
let filters = { regions: [] }, root = null;
const qs = () => `days=${st.days}&region=${encodeURIComponent(st.region)}&tier=${st.tier}`;

const LATER = [];

export async function render(el) {
  root = el; filters = await api("/ct/filters").catch(() => ({ regions: [] }));
  mount(el, html`<div class="head"><div><div class="eyebrow">Module 1 · version 0</div><h1>Control Tower</h1><p id="asof" class="muted">Loading</p></div>
    <div class="row"><div class="seg" id="per">${PERIODS.map(([d, l]) => html`<button data-act="ct-days" data-v="${d}" class="${st.days === d ? "on" : ""}">${l}</button>`)}</div>
    <select class="input" id="reg" data-act="noop"><option value="">All regions</option>${filters.regions.map(r => html`<option ${st.region === r ? "selected" : ""}>${r}</option>`)}</select>
    <select class="input" id="tier"><option value="">All formats</option><option value="A">Flagship</option><option value="B">High street</option><option value="C">Mall kiosk</option></select></div></div>
    <div class="kpis" id="kpis">${[1, 2, 3, 4, 5].map(() => html`<div class="kpi glass"><div class="sk" style="height:70px"></div></div>`)}</div>
    <div class="cols"><div class="card glass"><div class="ct"><h2>Net sales by day</h2><span class="small muted">Thick line is the 7-day average. Dashed lines mark festival peaks.</span></div><div class="chart" id="trend"></div></div>
    <div class="card glass"><div class="ct"><h2>Category mix</h2><span class="small muted">Share of net sales</span></div><div class="bars" id="mix"></div></div></div>
    <div class="cols eq"><div class="card solid"><div class="ct"><h2>Store league</h2><div class="seg" id="ord"><button data-act="ct-ord" data-v="top" class="${st.order === "top" ? "on" : ""}">Top 10</button><button data-act="ct-ord" data-v="bottom" class="${st.order === "bottom" ? "on" : ""}">Bottom 10</button></div></div><div id="league"></div></div>
    <div class="card glass"><div class="ct"><h2>Exceptions</h2><span class="small muted" id="excn"></span></div><div id="exc"></div></div></div>`);
  el.querySelector("#reg").onchange = e => { st.region = e.target.value; refresh(); };
  el.querySelector("#tier").value = st.tier; el.querySelector("#tier").onchange = e => { st.tier = e.target.value; refresh(); };
  addEventListener("resize", () => window.__ctTrend && window.__ctTrend());
  refresh();
}

async function refresh() {
  if (!root || !root.querySelector("#kpis")) return;
  try {
    const f = `region=${encodeURIComponent(st.region)}&tier=${st.tier}`;
    const [s, tr, mix, lg, ex] = await Promise.all([api(`/ct/summary?${qs()}`), api(`/ct/trend?${qs()}`), api(`/ct/categories?${qs()}`), api(`/ct/league?${qs()}&order=${st.order}`), api(`/ct/exceptions?${f}`)]);
    const c = s.current, p = s.previous, dlabel = `vs previous ${s.days} days`;
    root.querySelector("#asof").textContent = `Data through ${new Date(s.end + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}. Synthetic demo data, tax inclusive sales.`;
    const syncN = ex.filter(e => e.type === "sync").length;
    mount(root.querySelector("#kpis"), html`
      <div class="kpi glass"><div class="l">Net sales</div><div class="v">${inr(c.net)}</div><div class="s">${deltaPill(s.delta.net, " " + dlabel)}</div></div>
      <div class="kpi glass"><div class="l">Gross margin</div><div class="v">${pct(c.gm)}</div><div class="s">${s.delta.gm == null ? raw('<span class="d fl">no prior period</span>') : raw(`<span class="d ${s.delta.gm >= 0 ? "up" : "dn"}">${s.delta.gm >= 0 ? "+" : ""}${(s.delta.gm * 100).toFixed(1)} pts</span>`)} ex tax, at standard cost</div></div>
      <div class="kpi glass"><div class="l">Net sales per store per day</div><div class="v">${inr(c.per_store_day)}</div><div class="s">${deltaPill(s.delta.per_store_day, " " + dlabel)}</div></div>
      <div class="kpi glass"><div class="l">Stockout events</div><div class="v">${num(s.stockouts.events)}</div><div class="s">${num(s.stockouts.days)} store-SKU days lost across ${num(s.stockouts.stores)} stores</div></div>
      <div class="kpi glass"><div class="l">Stores not syncing</div><div class="v">${syncN}</div><div class="s">${num(c.stores)} stores selling in this period</div></div>`);
    const draw = () => { const t = root.querySelector("#trend"); if (t) trendChart(t, tr, s.festivals); }; window.__ctTrend = draw; draw();
    mount(root.querySelector("#mix"), html`${mix.map(m => html`<div class="r"><span>${m.name}</span><div class="b"><i style="width:${(m.share / mix[0].share * 100).toFixed(1)}%"></i></div><span class="num r">${pct(m.share)} <span class="muted small">GM ${pct(m.gm, 0)}</span></span></div>`)}`);
    mount(root.querySelector("#league"), html`<div class="tblwrap" style="max-height:420px"><table class="tbl"><thead><tr><th>#</th><th>Store</th><th>City</th><th class="r">Per day</th><th class="r">GM</th><th class="r">Change</th></tr></thead><tbody>
      ${lg.rows.map((r, i) => html`<tr><td class="muted">${i + 1}</td><td><b>${r.name.replace("Dry Fruit House ", "")}</b><div class="small muted">${r.code}${r.new ? " · new store" : ""}</div></td><td>${r.city}</td><td class="r">${inr(r.per_day)}</td><td class="r">${pct(r.gm, 0)}</td><td class="r">${r.vs_prev == null ? raw('<span class="muted">n/a</span>') : deltaPill(r.vs_prev)}</td></tr>`)}</tbody></table></div><p class="small muted" style="margin-top:8px">Ranked on net sales per trading day, ${num(lg.total)} stores in view. New stores are left out of the bottom list.</p>`);
    root.querySelector("#excn").textContent = `${ex.length} open`;
    mount(root.querySelector("#exc"), html`${ex.slice(0, 7).map(e => html`<div class="exc"><span class="dot ${e.severity}"></span><div><b>${e.title}</b><p>${e.detail}</p></div></div>`)}
      ${LATER.map(([t, m]) => html`<div class="exc later"><span class="dot later"></span><div><b>${t}</b><p>Appears when the ${m} module is built.</p></div></div>`)}`);
  } catch (e) { if (root.querySelector("#asof")) root.querySelector("#asof").textContent = "Could not load: " + e.message; }
}
acts["ct-days"] = a => { st.days = +a.dataset.v; document.querySelectorAll("#per button").forEach(b => b.classList.toggle("on", +b.dataset.v === st.days)); refresh(); };
acts["ct-ord"] = a => { st.order = a.dataset.v; document.querySelectorAll("#ord button").forEach(b => b.classList.toggle("on", b.dataset.v === st.order)); refresh(); };
acts.noop = () => { };
