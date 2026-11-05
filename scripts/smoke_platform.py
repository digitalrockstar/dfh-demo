"""Module 10 smoke (Platform): start the server, drive every tab in Chromium, fail on console errors, save screenshots."""
import os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

PORT = int(os.getenv("PORT", "8078")); OUT = os.getenv("SHOTS", "/tmp/shots"); os.makedirs(OUT, exist_ok=True)
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "dfh.app:get_app", "--factory", "--port", str(PORT), "--log-level", "warning"])
try:
    for _ in range(60):
        try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health"); break
        except Exception: time.sleep(0.5)
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.getenv("CHROME") or None, args=os.getenv("CHROME_ARGS", "").split()); pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "40" not in m.text else None); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{PORT}/"); pg.wait_for_selector("#u"); pg.click("[data-act=do-login]"); pg.wait_for_selector(".kpi .v")
        pg.goto(f"http://127.0.0.1:{PORT}/#/platform"); pg.wait_for_selector("#pbody .kpi"); pg.screenshot(path=f"{OUT}/30_platform_approvals.png", full_page=True)
        pg.click("[data-act=p-new]"); pg.wait_for_selector(".modal #nt"); pg.keyboard.press("Escape")
        for tab, sel in [("audit", "#pbody .tbl tbody tr"), ("imports", "#pc"), ("entities", "tr[data-act=p-ent]"), ("users", "[data-act=p-uedit]"), ("health", "#pbody .kpi")]:
            pg.click(f"[data-act=p-tab][data-v={tab}]"); pg.wait_for_selector(sel); pg.screenshot(path=f"{OUT}/31_platform_{tab}.png", full_page=True)
        pg.click("[data-act=p-tab][data-v=entities]"); pg.wait_for_selector("tr[data-act=p-ent]"); pg.click("tr[data-act=p-ent] >> nth=0"); pg.wait_for_selector(".drawer .btn.pri"); pg.screenshot(path=f"{OUT}/32_platform_entity.png")
        b.close()
    print("console errors:", errs or "none"); assert not errs, errs
    print("smoke platform ok")
finally:
    srv.terminate()
