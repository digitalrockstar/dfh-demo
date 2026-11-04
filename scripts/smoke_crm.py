"""Module 8 smoke (Customers and WhatsApp): start the server, drive the UI in Chromium, fail on console errors, save screenshots."""
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
        b = p.chromium.launch(executable_path=os.getenv("CHROME") or None, args=os.getenv("CHROME_ARGS", "").split()); pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "422" not in m.text else None); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{PORT}/"); pg.wait_for_selector("#u"); pg.screenshot(path=f"{OUT}/1_login.png")

        pg.click("[data-act=do-login]"); pg.wait_for_selector(".kpi .v")
        pg.goto(f"http://127.0.0.1:{PORT}/#/customers"); pg.wait_for_timeout(500); pg.wait_for_selector("#cbody .kpi", state="attached"); assert pg.locator(".kpi").count() >= 6; pg.screenshot(path=f"{OUT}/16_crm_overview.png", full_page=True)
        pg.click("[data-act=c-tab][data-v=customers]"); pg.wait_for_selector("tr[data-act=c-cust]"); pg.click("tr[data-act=c-cust] >> nth=0"); pg.wait_for_selector(".drawer .kpi"); pg.screenshot(path=f"{OUT}/17_crm_customer.png"); pg.keyboard.press("Escape")
        pg.click("[data-act=c-tab][data-v=orders]"); pg.wait_for_selector("tr[data-act=c-order]"); pg.click("[data-act=c-aged]"); pg.wait_for_selector("tr[data-act=c-order]"); pg.click("tr[data-act=c-order] >> nth=0"); pg.wait_for_selector(".drawer [data-act=c-oact]"); pg.screenshot(path=f"{OUT}/18_crm_order.png"); pg.keyboard.press("Escape")
        pg.click("[data-act=c-tab][data-v=inbox]"); pg.wait_for_selector("tr[data-act=c-thread]"); pg.click("tr[data-act=c-thread] >> nth=0"); pg.wait_for_selector("#cthread textarea, #cthread select"); pg.screenshot(path=f"{OUT}/19_crm_inbox.png")
        pg.click("[data-act=c-tab][data-v=campaigns]"); pg.wait_for_selector("#cbody .tbl tbody tr"); pg.screenshot(path=f"{OUT}/20_crm_campaigns.png", full_page=True)
        pg.click("[data-act=c-tab][data-v=quotes]"); pg.wait_for_selector("tr[data-act=c-quote]"); pg.click("tr[data-act=c-quote] >> nth=0"); pg.wait_for_selector(".drawer .tbl"); pg.screenshot(path=f"{OUT}/21_crm_quote.png"); pg.keyboard.press("Escape")
        b.close()
    print("console errors:", errs or "none"); assert not errs, errs
    print("smoke crm ok")
finally:
    srv.terminate()
