import { html, out } from "./ui.js";
export const acts = {};
export const S = { token: localStorage.getItem("dfh_token"), user: null,
  theme: Object.assign({ mode: "auto", tone: "dfh", glass: 0.35 }, JSON.parse(localStorage.getItem("dfh_theme") || "{}")) };

export async function api(path, opts = {}) {
  const r = await fetch("/api" + path, { method: opts.method || "GET", headers: { "Content-Type": "application/json", ...(S.token ? { Authorization: "Bearer " + S.token } : {}) }, body: opts.body ? JSON.stringify(opts.body) : undefined });
  if (r.status === 401 && S.token) { logout(); throw new Error("Signed out"); }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : "Request failed");
  return j;
}
export function applyTheme() {
  const t = S.theme, dark = t.mode === "dark" || (t.mode === "auto" && matchMedia("(prefers-color-scheme: dark)").matches), r = document.documentElement;
  r.dataset.mode = dark ? "dark" : "light"; r.dataset.tone = t.tone; r.style.setProperty("--glass", t.glass); r.dataset.glass = +t.glass < .02 ? "off" : "on";
  localStorage.setItem("dfh_theme", JSON.stringify(t));
}
export function logout() { localStorage.removeItem("dfh_token"); localStorage.removeItem("dfh_user"); S.token = null; S.user = null; location.hash = ""; location.reload(); }
export function toast(msg, err = false) {
  const d = document.createElement("div"); d.className = "toast glass" + (err ? " err" : ""); d.textContent = msg; document.body.append(d); setTimeout(() => d.remove(), 3200);
}
export const canWrite = () => ["ceo", "procurement", "admin"].includes(S.user?.role);
document.addEventListener("click", e => { const a = e.target.closest("[data-act]"); if (a && acts[a.dataset.act]) acts[a.dataset.act](a, e); });
export const mount = (el, h) => { el.innerHTML = out(h); };
document.addEventListener("keydown", e => { if (e.key === "Escape") document.querySelectorAll(".scrim,.drawer,.modal,.set").forEach(n => n.remove()); });
