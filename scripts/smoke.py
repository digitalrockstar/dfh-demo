"""End-to-end smoke: start the server, drive the UI in Chromium, fail on console errors, save screenshots."""
import os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

PORT = int(os.getenv("PORT", "8077")); OUT = os.getenv("SHOTS", "/tmp/shots"); os.makedirs(OUT, exist_ok=True)
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "dfh.app:get_app", "--factory", "--port", str(PORT), "--log-level", "warning"])
try:
    for _ in range(60):
        try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health"); break
        except Exception: time.sleep(0.5)
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "422" not in m.text else None); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{PORT}/"); pg.wait_for_selector("#u"); pg.screenshot(path=f"{OUT}/1_login.png")
        pg.click("[data-act=do-login]"); pg.wait_for_selector(".kpi .v"); pg.wait_for_selector("#league tbody tr"); pg.wait_for_selector("#exc .exc"); pg.wait_for_timeout(700)
        assert pg.locator(".kpi").count() == 5 and pg.locator("#trend svg path").count() >= 3
        pg.screenshot(path=f"{OUT}/2_control_tower.png")
        pg.click("[data-act=ct-days][data-v='7']"); pg.wait_for_timeout(900); pg.click("[data-act=ct-ord][data-v=bottom]"); pg.wait_for_timeout(900)
        pg.goto(f"http://127.0.0.1:{PORT}/#/skus"); pg.wait_for_selector(".tbl tbody tr.click"); pg.screenshot(path=f"{OUT}/3_skus.png")
        assert pg.locator(".tbl tbody tr.click").count() == 50
        pg.fill("#q", "almonds california"); pg.wait_for_timeout(700); n = pg.locator(".tbl tbody tr.click").count(); assert 3 <= n < 50, n
        pg.click(".tbl tbody tr.click >> nth=0"); pg.wait_for_selector(".drawer .stats"); pg.click("[data-act=sku-tab][data-v=pricing]"); pg.wait_for_selector(".drawer .spark"); pg.wait_for_timeout(500)
        pg.screenshot(path=f"{OUT}/4_sku_pricing.png")
        pg.click("[data-act=sku-tab][data-v=overview]"); pg.fill("#np", "1"); pg.click("[data-act=sku-save]"); pg.wait_for_selector(".toast.err"); pg.keyboard.press("Escape"); pg.wait_for_selector(".drawer", state="detached"); pg.goto(f"http://127.0.0.1:{PORT}/#/soon/inventory"); pg.wait_for_selector(".soonbox")
        pg.click("[data-act=settings]"); pg.click("[data-act=set-mode][data-v=dark]"); pg.fill("#gl", "80"); pg.dispatch_event("#gl", "input"); pg.click("[data-act=set-tone][data-v=ops]")
        pg.goto(f"http://127.0.0.1:{PORT}/#/control-tower"); pg.wait_for_selector("#exc .exc"); pg.wait_for_timeout(900)
        pg.screenshot(path=f"{OUT}/5_dark_ops_glass.png")
        pg.set_viewport_size({"width": 1440, "height": 900}); b.close()
    print("console errors:", errs or "none"); assert not errs, errs
    print("smoke ok")
finally:
    srv.terminate()
