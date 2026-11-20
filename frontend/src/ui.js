export class Raw { constructor(s) { this.s = s; } }
export const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const val = v => v instanceof Raw ? v.s : Array.isArray(v) ? v.map(val).join("") : (v == null || v === false) ? "" : esc(v);
export const html = (strs, ...vals) => new Raw(strs.reduce((o, s, i) => o + s + (i < vals.length ? val(vals[i]) : ""), ""));
export const raw = s => new Raw(s);
export const out = v => val(v);

export const inr = (paise, compact = true) => {
  const r = paise / 100, a = Math.abs(r);
  if (compact && a >= 1e7) return "₹" + (r / 1e7).toFixed(2) + " Cr";
  if (compact && a >= 1e5) return "₹" + (r / 1e5).toFixed(1) + " L";
  return "₹" + r.toLocaleString("en-IN", { maximumFractionDigits: a < 100 ? 2 : 0 });
};
export const rs = r => "₹" + Number(r).toLocaleString("en-IN", { maximumFractionDigits: r < 100 ? 2 : 0 });
export const pct = (x, d = 1) => x == null ? "n/a" : (x * 100).toFixed(d) + "%";
export const num = n => Number(n).toLocaleString("en-IN");
export const deltaPill = (x, label = "") => x == null ? raw('<span class="d fl">no prior period</span>')
  : raw(`<span class="d ${x > 0.0005 ? "up" : x < -0.0005 ? "dn" : "fl"}">${x >= 0 ? "+" : ""}${(x * 100).toFixed(1)}%</span>${esc(label)}`);
export const dmy = s => new Date(s + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short" });

// Monotone cubic (Fritsch-Carlson) path through [x,y] points: no overshoot, so lines never dip below real data.
export function splinePath(p) {
  const n = p.length; if (n < 2) return "";
  if (n === 2) return `M${p[0][0].toFixed(1)},${p[0][1].toFixed(1)}L${p[1][0].toFixed(1)},${p[1][1].toFixed(1)}`;
  const dx = [], m = [], t = [];
  for (let i = 0; i < n - 1; i++) { dx[i] = p[i + 1][0] - p[i][0] || 1e-9; m[i] = (p[i + 1][1] - p[i][1]) / dx[i]; }
  t[0] = m[0]; t[n - 1] = m[n - 2];
  for (let i = 1; i < n - 1; i++) t[i] = m[i - 1] * m[i] <= 0 ? 0 : (m[i - 1] + m[i]) / 2;
  for (let i = 0; i < n - 1; i++) {
    if (m[i] === 0) { t[i] = t[i + 1] = 0; continue; }
    const a = t[i] / m[i], b = t[i + 1] / m[i], h = Math.hypot(a, b);
    if (h > 3) { t[i] = 3 * a / h * m[i]; t[i + 1] = 3 * b / h * m[i]; }
  }
  let d = `M${p[0][0].toFixed(1)},${p[0][1].toFixed(1)}`;
  for (let i = 0; i < n - 1; i++) {
    const c = dx[i] / 3;
    d += `C${(p[i][0] + c).toFixed(1)},${(p[i][1] + t[i] * c).toFixed(1)} ${(p[i + 1][0] - c).toFixed(1)},${(p[i + 1][1] - t[i + 1] * c).toFixed(1)} ${p[i + 1][0].toFixed(1)},${p[i + 1][1].toFixed(1)}`;
  }
  return d;
}

export function spark(vals, w = 90, h = 26, color = "var(--primary)") {
  if (vals.length < 2) return "";
  const mn = Math.min(...vals), mx = Math.max(...vals), sp = mx - mn || 1;
  const pts = vals.map((v, i) => [i / (vals.length - 1) * (w - 4) + 2, h - 3 - (v - mn) / sp * (h - 6)]);
  return raw(`<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><path d="${splinePath(pts)}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`);
}

// Provenance badge. kind: live | sample | derived | na. Demo data is "sample" unless computed from other data ("derived").
export const prov = (kind = "sample") => raw(`<span class="prov ${kind}" title="${{ live: "Live data", sample: "Sample data", derived: "Derived from other figures", na: "Unavailable" }[kind] || "Sample data"}">${{ live: "Live", sample: "Sample", derived: "Derived", na: "n/a" }[kind] || "Sample"}</span>`);

// 3D donut for any percent-of-100 or part-of-whole (extruded ring, squashed to 0.56, soft floor shadow).
// parts: [{v, n?, color?}] or one number 0-100 (gauge, shallower). size = width in px. centre: {big, small}.
let donutId = 0;
export function donut(parts, size = 132, centre = {}) {
  const gauge = typeof parts === "number", g = gauge ? Math.max(0, Math.min(100, parts)) : 0;
  const arr = gauge ? [{ v: g, color: "var(--primary)", n: "Value" }, { v: 100 - g, color: "var(--line)", n: "Rest" }] : parts;
  const tot = arr.reduce((a, x) => a + Math.max(0, x.v), 0) || 1, R = 70, C = 2 * Math.PI * R, gap = gauge ? 0 : 2.5, dep = gauge ? 9 : 14, id = "dn" + (++donutId);
  const pal = ["var(--primary)", "var(--secondary)", "color-mix(in srgb,var(--primary) 55%,var(--secondary))", "color-mix(in srgb,var(--primary) 30%,var(--text))", "var(--ok)", "var(--bad)"];   // dfh has primary = accent, so mixes keep segments distinct
  let off = 0; const arcs = arr.map((x, i) => {
    const l = Math.max(0, x.v) / tot * C, d = Math.max(0, l - gap), o = off; off += l;
    return `<circle r="${R}" fill="none" stroke="${x.color || pal[i % pal.length]}" stroke-width="26" stroke-dasharray="${d.toFixed(2)} ${(C - d).toFixed(2)}" stroke-dashoffset="${(-o).toFixed(2)}" transform="rotate(-90)"/>`;
  });
  let sides = ""; for (let k = dep; k >= 1; k -= 1.5) sides += `<g transform="translate(0 ${(k / .56).toFixed(2)})">${arcs.join("")}</g>`;
  const top = arcs.map(a => `<g class="sg">${a}</g>`).join("");
  const label = arr.map(x => `${x.n || ""} ${Math.round(Math.max(0, x.v) / tot * 1000) / 10}%`).join(", ");
  return raw(`<div class="donut" style="width:${size}px"><svg viewBox="0 20 220 140" role="img" aria-label="${esc(label)}"><defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".34"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".18"/></linearGradient><filter id="${id}b" x="-30%" y="-100%" width="160%" height="300%"><feGaussianBlur stdDeviation="7"/></filter><filter id="${id}d"><feColorMatrix type="matrix" values=".55 0 0 0 0 0 .55 0 0 0 0 0 .55 0 0 0 0 0 1 0"/></filter></defs><ellipse cx="110" cy="${130 + dep}" rx="86" ry="11" fill="#000" opacity=".38" filter="url(#${id}b)"/><g transform="translate(110 76) scale(1 .56)"><g filter="url(#${id}d)">${sides}</g>${top}<circle r="${R}" fill="none" stroke="url(#${id})" stroke-width="26" style="pointer-events:none"/><circle r="${R + 13}" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width="1" style="pointer-events:none"/></g></svg><div class="dc"><b>${esc(centre.big ?? "")}</b><span>${esc(centre.small ?? "")}</span></div></div>`);
}

// Rolling number: animates el's text from its current value to `to` using fmt. Instant under prefers-reduced-motion.
export function roll(el, to, fmt = String, ms = 600) {
  const from = +el.dataset.v || 0; el.dataset.v = to;
  if (matchMedia("(prefers-reduced-motion:reduce)").matches || from === to) { el.textContent = fmt(to); return; }
  const t0 = performance.now();
  const step = t => { const k = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - k, 3); el.textContent = fmt(from + (to - from) * e); if (k < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}

export function trendChart(el, data, festivals) {
  const W = Math.max(320, el.clientWidth), H = 270, L = 58, R = 10, T = 12, B = 28;
  const xs = i => L + i / Math.max(1, data.length - 1) * (W - L - R);
  const mx = Math.max(...data.map(d => d.net)) * 1.08;
  const y = v => T + (1 - v / mx) * (H - T - B);
  const line = k => splinePath(data.map((d, i) => [xs(i), y(d[k])]));
  let g = "";
  for (let i = 0; i <= 4; i++) { const v = mx * i / 4; g += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" stroke-dasharray="3 4"/><text x="${L - 8}" y="${y(v) + 4}" text-anchor="end" font-size="11" fill="var(--muted)">${inr(v, true).replace(".00", "")}</text>`; }
  const step = Math.max(1, Math.round(data.length / 6)); let xl = "";
  data.forEach((d, i) => { if (i % step === 0) xl += `<text x="${xs(i)}" y="${H - 8}" text-anchor="middle" font-size="11" fill="var(--muted)">${dmy(d.date)}</text>`; });
  let fest = "";
  festivals.forEach(f => { const i = data.findIndex(d => d.date === f.peak); if (i >= 0) fest += `<line x1="${xs(i)}" x2="${xs(i)}" y1="${T}" y2="${H - B}" stroke="var(--primary)" stroke-width="1.2" stroke-dasharray="4 3" opacity=".7"/><text x="${xs(i) + 4}" y="${T + 11}" font-size="10.5" fill="var(--primary-text)" font-weight="600">${esc(f.name)}</text>`; });
  const gid = "ar" + (++donutId); el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" height="${H}"><defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--primary)" stop-opacity=".28"/><stop offset="1" stop-color="var(--primary)" stop-opacity="0"/></linearGradient></defs>
  ${g}${xl}${fest}<path d="${line("net")} L${xs(data.length - 1)},${H - B} L${L},${H - B}Z" fill="url(#${gid})"/><path d="${line("net")}" fill="none" stroke="var(--primary)" stroke-opacity=".45" stroke-width="1.2"/>
  <path d="${line("avg7")}" fill="none" stroke="var(--primary-text)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><line id="gd" y1="${T}" y2="${H - B}" stroke="var(--text)" stroke-opacity=".25" style="display:none"/>
  <rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent" id="hit"/></svg><div class="tip glass" style="display:none"></div>`;
  const hit = el.querySelector("#hit"), gd = el.querySelector("#gd"), tip = el.querySelector(".tip");
  hit.addEventListener("mousemove", e => {
    const r = hit.getBoundingClientRect(), i = Math.round((e.clientX - r.left) / r.width * (data.length - 1)), d = data[Math.max(0, Math.min(data.length - 1, i))];
    gd.style.display = "block"; gd.setAttribute("x1", xs(i)); gd.setAttribute("x2", xs(i));
    tip.style.display = "block"; tip.style.left = xs(i) + "px"; tip.style.top = (y(d.net) - 8) + "px";
    tip.innerHTML = `<b>${dmy(d.date)}</b><br>${inr(d.net)} that day<br><span class="muted">7-day average ${inr(d.avg7)}</span>`;
  });
  hit.addEventListener("mouseleave", () => { gd.style.display = "none"; tip.style.display = "none"; });
}
