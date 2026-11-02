"""POS offline smoke: bill online, go offline, reload the app from the service worker cache, bill offline, come back and check the queue drains with continuous invoice numbers.
Run: CHROME=/path/to/chrome python scripts/smoke_pos.py   (CHROME_ARGS adds launch flags)"""
import json, os, sqlite3, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

PORT = int(os.getenv("PORT", "8078")); OUT = os.getenv("SHOTS", "/tmp/shots_pos"); os.makedirs(OUT, exist_ok=True); URL = f"http://127.0.0.1:{PORT}/"
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "dfh.app:get_app", "--factory", "--port", str(PORT), "--log-level", "warning"])
try:
    for _ in range(60):
        try: urllib.request.urlopen(URL + "api/health"); break
        except Exception: time.sleep(0.5)
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.getenv("CHROME") or None, args=os.getenv("CHROME_ARGS", "").split())
        ctx = b.new_context(viewport={"width": 1366, "height": 860}); pg = ctx.new_page()
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "ERR_INTERNET_DISCONNECTED" not in m.text and "Failed to load resource" not in m.text else None); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL); pg.fill("#u", "cashier"); pg.click("[data-act=do-login]"); pg.wait_for_selector(".nav")
        pg.goto(URL + "#/pos"); pg.wait_for_selector("[data-act=pos-pick]"); pg.screenshot(path=f"{OUT}/1_setup.png")
        pg.click("[data-act=pos-pick] >> nth=0"); pg.wait_for_selector("#pq")
        pg.evaluate("navigator.serviceWorker.ready.then(() => 1)")
        for _ in range(40):
            if pg.evaluate("caches.match('/src/page_pos.js').then(r => !!r)"): break
            time.sleep(.25)
        assert pg.evaluate("caches.match('/src/page_pos.js').then(r => !!r)"), "shell not cached"
        status = lambda: pg.inner_text("#pstat")
        # 1. online bill, one packed item, cash
        pg.fill("#pq", "almonds california 100g"); pg.click(".tile >> nth=0"); pg.wait_for_selector("#pcharge:not([disabled])"); pg.screenshot(path=f"{OUT}/2_bill.png")
        pg.click("#pcharge"); pg.wait_for_selector(".receipt h2"); inv1 = pg.inner_text(".receipt h2"); pg.screenshot(path=f"{OUT}/3_receipt.png"); pg.click(".modal .btn.pri")
        pg.wait_for_function("document.querySelector('#pstat').innerText.includes('0 waiting')", timeout=15000)
        # 2. offline: reload from the service worker and keep billing
        ctx.set_offline(True); pg.reload(); pg.wait_for_selector("#pq", timeout=15000)
        assert "Offline" in status(), status()
        pg.fill("#pq", "almonds california loose"); pg.click(".tile >> nth=0"); pg.fill("[data-g='0']", "0.35"); pg.dispatch_event("[data-g='0']", "input")
        pg.fill("#pq", "cashew"); pg.click(".tile >> nth=0"); pg.wait_for_selector("#pcharge:not([disabled])")
        pg.click("#pcharge"); pg.wait_for_selector(".receipt h2"); inv2 = pg.inner_text(".receipt h2"); assert "this device" in pg.inner_text(".receipt"); pg.screenshot(path=f"{OUT}/4_offline_receipt.png"); pg.click(".modal .btn.pri")
        pg.fill("#pq", "dates"); pg.click(".tile >> nth=0"); pg.click("[data-act=pos-split]"); pg.wait_for_selector("#pcharge:not([disabled])")
        pg.click("#pcharge"); pg.wait_for_selector(".receipt h2"); inv3 = pg.inner_text(".receipt h2"); pg.click(".modal .btn.pri")
        pg.wait_for_function("document.querySelector('#pstat').innerText.includes('2 waiting')"); pg.screenshot(path=f"{OUT}/5_offline_queue.png")
        pg.click("[data-act=pos-tab][data-v=close]"); assert "needs a connection" in pg.inner_text("#ptab")
        # 3. back online: queue drains
        ctx.set_offline(False); pg.evaluate("dispatchEvent(new Event('online'))")
        pg.wait_for_function("document.querySelector('#pstat').innerText.includes('0 waiting')", timeout=20000)
        n = lambda s: int(s.split("/")[-1]); assert n(inv2) == n(inv1) + 1 and n(inv3) == n(inv2) + 1, (inv1, inv2, inv3)
        con = sqlite3.connect("data/dfh.db"); got = [r[0] for r in con.execute("select invoice_no from sale where invoice_no in (?,?,?) order by invoice_no", (inv1, inv2, inv3))]; assert got == [inv1, inv2, inv3], got
        # 4. day close and returns screens
        pg.click("[data-act=pos-tab][data-v=close]"); pg.wait_for_selector("#dcn"); pg.fill("#dcn", "100"); pg.screenshot(path=f"{OUT}/6_day_close.png")
        pg.click("[data-act=pos-tab][data-v=recent]"); pg.wait_for_selector("#pinv"); pg.fill("#pinv", inv1); pg.click("[data-act=pos-find]"); pg.wait_for_selector("[data-rl]"); pg.screenshot(path=f"{OUT}/7_returns.png")
        # 5. dark theme, narrow tablet
        pg.click("[data-act=pos-tab][data-v=bill]"); pg.evaluate("document.documentElement.dataset.mode='dark'"); pg.set_viewport_size({"width": 820, "height": 1100}); pg.fill("#pq", "almonds"); pg.click(".tile >> nth=0"); pg.screenshot(path=f"{OUT}/8_tablet_dark.png")
        b.close()
    assert not errs, errs
    print("POS smoke ok", inv1, inv2, inv3)
finally:
    srv.terminate()
