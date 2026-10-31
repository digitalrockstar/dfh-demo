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

export function spark(vals, w = 90, h = 26, color = "var(--primary)") {
  if (vals.length < 2) return "";
  const mn = Math.min(...vals), mx = Math.max(...vals), sp = mx - mn || 1;
  const pts = vals.map((v, i) => `${(i / (vals.length - 1) * (w - 4) + 2).toFixed(1)},${(h - 3 - (v - mn) / sp * (h - 6)).toFixed(1)}`).join(" ");
  return raw(`<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`);
}

export function trendChart(el, data, festivals) {
  const W = Math.max(320, el.clientWidth), H = 270, L = 58, R = 10, T = 12, B = 28;
  const xs = i => L + i / Math.max(1, data.length - 1) * (W - L - R);
  const mx = Math.max(...data.map(d => d.net)) * 1.08;
  const y = v => T + (1 - v / mx) * (H - T - B);
  const line = k => data.map((d, i) => `${i ? "L" : "M"}${xs(i).toFixed(1)},${y(d[k]).toFixed(1)}`).join("");
  let g = "";
  for (let i = 0; i <= 4; i++) { const v = mx * i / 4; g += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" stroke-dasharray="3 4"/><text x="${L - 8}" y="${y(v) + 4}" text-anchor="end" font-size="11" fill="var(--muted)">${inr(v, true).replace(".00", "")}</text>`; }
  const step = Math.max(1, Math.round(data.length / 6)); let xl = "";
  data.forEach((d, i) => { if (i % step === 0) xl += `<text x="${xs(i)}" y="${H - 8}" text-anchor="middle" font-size="11" fill="var(--muted)">${dmy(d.date)}</text>`; });
  let fest = "";
  festivals.forEach(f => { const i = data.findIndex(d => d.date === f.peak); if (i >= 0) fest += `<line x1="${xs(i)}" x2="${xs(i)}" y1="${T}" y2="${H - B}" stroke="var(--primary)" stroke-width="1.2" stroke-dasharray="4 3" opacity=".7"/><text x="${xs(i) + 4}" y="${T + 11}" font-size="10.5" fill="var(--primary-text)" font-weight="600">${esc(f.name)}</text>`; });
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" height="${H}"><defs><linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--primary)" stop-opacity=".28"/><stop offset="1" stop-color="var(--primary)" stop-opacity="0"/></linearGradient></defs>
  ${g}${xl}${fest}<path d="${line("net")} L${xs(data.length - 1)},${H - B} L${L},${H - B}Z" fill="url(#ar)"/><path d="${line("net")}" fill="none" stroke="var(--primary)" stroke-opacity=".45" stroke-width="1.2"/>
  <path d="${line("avg7")}" fill="none" stroke="var(--primary-text)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/><line id="gd" y1="${T}" y2="${H - B}" stroke="var(--text)" stroke-opacity=".25" style="display:none"/>
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
