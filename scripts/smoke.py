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
        b = p.chromium.launch(executable_path=os.getenv("CHROME") or None, args=os.getenv("CHROME_ARGS", "").split()); pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "422" not in m.text else None); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{PORT}/"); pg.wait_for_selector("#u"); pg.screenshot(path=f"{OUT}/1_login.png")
        pg.click("[data-act=do-login]"); pg.wait_for_selector(".kpi .v"); pg.wait_for_selector("#league tbody tr"); pg.wait_for_selector("#exc .exc"); pg.wait_for_timeout(700)
        assert pg.locator(".kpi").count() == 5 and pg.locator("#trend svg path").count() >= 3
        pg.screenshot(path=f"{OUT}/2_control_tower.png")
        pg.click("[data-act=ct-days][data-v='7']"); pg.wait_for_timeout(900); pg.click("[data-act=ct-ord][data-v=bottom]"); pg.wait_for_timeout(900)
        pg.click("#league tbody tr.click >> nth=0"); pg.wait_for_selector(".drawer .kpi .v"); pg.click(".drawer tr.click >> nth=0"); pg.wait_for_selector(".drawer h1"); pg.keyboard.press("Escape"); pg.wait_for_timeout(300)   # Control Tower drill (not run in the build sandbox)
        pg.click("[data-act=ct-tab][data-v=inbox]"); pg.wait_for_selector("[data-ct-status]"); pg.click("[data-act=ct-tab][data-v=wh]"); pg.wait_for_selector("#ctbody .tbl tbody tr"); pg.screenshot(path=f"{OUT}/2b_ct_warehouses.png")
        pg.click("[data-act=ct-tab][data-v=overview]"); pg.wait_for_selector("#cmp .tbl")
        pg.goto(f"http://127.0.0.1:{PORT}/#/skus"); pg.wait_for_selector(".tbl tbody tr.click"); pg.screenshot(path=f"{OUT}/3_skus.png")
        assert pg.locator(".tbl tbody tr.click").count() == 50
        pg.fill("#q", "almonds california"); pg.wait_for_timeout(700); n = pg.locator(".tbl tbody tr.click").count(); assert 3 <= n < 50, n
        pg.click(".tbl tbody tr.click >> nth=0"); pg.wait_for_selector(".drawer .stats"); pg.click("[data-act=sku-tab][data-v=pricing]"); pg.wait_for_selector(".drawer .spark"); pg.wait_for_timeout(500)
        pg.screenshot(path=f"{OUT}/4_sku_pricing.png")
        pg.click("[data-act=sku-tab][data-v=overview]"); pg.fill("#np", "1"); pg.click("[data-act=sku-save]"); pg.wait_for_selector(".toast.err"); pg.keyboard.press("Escape"); pg.wait_for_selector(".drawer", state="detached"); pg.goto(f"http://127.0.0.1:{PORT}/#/inventory"); pg.wait_for_selector("#invbody .kpi .v"); pg.wait_for_selector("#invbody .exc"); pg.wait_for_timeout(500); pg.screenshot(path=f"{OUT}/5_inventory.png")
        pg.click("#invbody tbody tr.click >> nth=0"); pg.wait_for_selector("#invbody .tbl tbody tr.click"); pg.click("#invbody .tbl tbody tr.click >> nth=0"); pg.wait_for_selector(".drawer .tbl"); pg.screenshot(path=f"{OUT}/6_inv_sku.png"); pg.keyboard.press("Escape")
        for t in ("expiry", "transfers", "indents", "repack", "counts", "kits"):
            pg.click(f"[data-act=inv-tab][data-v={t}]"); pg.wait_for_selector("#invbody .tbl, #invbody .card"); pg.wait_for_timeout(400)
        pg.click("[data-act=inv-tab][data-v=transfers]"); pg.wait_for_selector("#invbody tr.click"); pg.click("#invbody tr.click >> nth=0"); pg.wait_for_selector(".drawer .tbl"); pg.screenshot(path=f"{OUT}/7_inv_transfer.png"); pg.keyboard.press("Escape")
        pg.click("[data-act=settings]"); pg.click("[data-act=set-mode][data-v=dark]"); pg.fill("#gl", "80"); pg.dispatch_event("#gl", "input"); pg.click("[data-act=set-tone][data-v=ops]")
        pg.goto(f"http://127.0.0.1:{PORT}/#/control-tower"); pg.wait_for_selector("#exc .exc"); pg.wait_for_timeout(900)
        pg.screenshot(path=f"{OUT}/5_dark_ops_glass.png")
        pg.goto(f"http://127.0.0.1:{PORT}/#/wastage"); pg.wait_for_selector("#wk .kpi .v"); pg.wait_for_selector("#wloc tbody tr"); pg.wait_for_selector("#wexp tbody tr"); pg.wait_for_selector("#went tbody tr"); pg.wait_for_timeout(800)
        assert pg.locator("#wk .kpi").count() == 5 and pg.locator("#wtrend svg rect").count() >= 8 and pg.locator("#wreasons .r").count() >= 5
        pg.screenshot(path=f"{OUT}/6_wastage.png", full_page=True)
        pg.click("[data-act=w-kind][data-v=warehouse]"); pg.wait_for_timeout(900); assert "Hyderabad" in pg.inner_text("#wloc tbody tr >> nth=0")
        pg.click("[data-act=w-win][data-v='15']"); pg.wait_for_timeout(700); pg.click("[data-act=w-sr][data-v=EXPIRY]"); pg.wait_for_timeout(700)
        pg.click("[data-act=w-new]"); pg.wait_for_selector(".modal #wf-q"); pg.click("[data-act=w-save]"); pg.wait_for_selector(".toast.err"); pg.keyboard.press("Escape"); pg.wait_for_selector(".modal", state="detached")
        pg.screenshot(path=f"{OUT}/7_wastage_filtered.png")
        pg.goto(f"http://127.0.0.1:{PORT}/#/demand"); pg.wait_for_selector("#dk .kpi .v"); pg.wait_for_selector("#dsug tbody tr"); pg.wait_for_selector("#dkits tbody tr"); pg.wait_for_selector("#dmm tbody tr"); pg.wait_for_selector("#dacc tbody tr"); pg.wait_for_timeout(900)
        assert pg.locator("#dk .kpi").count() == 5 and pg.locator("#dchart svg path").count() >= 3 and pg.locator("#dbeta .b").count() == 8
        pg.screenshot(path=f"{OUT}/8_demand.png", full_page=True)
        pg.select_option("#dscope", "category|GFT"); pg.wait_for_timeout(900); pg.click("[data-act=d-urg][data-v=critical]"); pg.wait_for_timeout(700); assert pg.locator("#dsug tbody tr").count() >= 1
        n0 = pg.locator("#dsug [data-act=d-dec][data-v=approve]").count(); pg.click("#dsug [data-act=d-dec][data-v=approve] >> nth=0"); pg.wait_for_selector(".toast"); pg.wait_for_timeout(700)
        pg.screenshot(path=f"{OUT}/9_demand_filtered.png")
        pg.goto(f"http://127.0.0.1:{PORT}/#/procurement"); pg.wait_for_selector("#pk .kpi .v"); [pg.wait_for_selector(f"{i} tbody tr") for i in ("#psh", "#ppo", "#ppb", "#pvd", "#pmt")]; pg.wait_for_timeout(500)
        assert pg.locator("#pk .kpi").count() == 5
        pg.screenshot(path=f"{OUT}/10_procurement.png", full_page=True)
        pg.click("[data-act=p-sv][data-v=late]"); pg.wait_for_timeout(800); assert pg.locator("#psh tbody tr").count() >= 1
        pg.click("#ppo tbody tr.click >> nth=0"); pg.wait_for_selector(".drawer .stats"); pg.wait_for_timeout(500); pg.screenshot(path=f"{OUT}/11_po_drawer.png"); pg.keyboard.press("Escape"); pg.wait_for_selector(".drawer", state="detached")
        pg.click("[data-act=p-creep][data-v=creep]"); pg.wait_for_timeout(800); pg.click("#ppb tbody tr.click >> nth=0"); pg.wait_for_selector(".drawer .stack"); pg.wait_for_timeout(500); pg.screenshot(path=f"{OUT}/12_compare.png"); pg.keyboard.press("Escape"); pg.wait_for_selector(".drawer", state="detached")
        pg.click("[data-act=p-mv][data-v=ready]"); pg.wait_for_timeout(800); pg.screenshot(path=f"{OUT}/13_procurement_match.png")
        pg.goto(f"http://127.0.0.1:{PORT}/#/finance"); pg.wait_for_selector("#fclose .tbl tbody tr"); pg.wait_for_timeout(500); assert pg.locator(".kpi").count() == 5
        pg.screenshot(path=f"{OUT}/14_finance_close.png", full_page=True)
        pg.click("[data-act=f-tab][data-v=cash]"); pg.wait_for_selector("#frecon .tbl tbody tr"); pg.click("[data-act=f-flag][data-v='1']"); pg.wait_for_selector("tr[data-act=f-store]"); assert pg.locator("tr[data-act=f-store]").count() == 1
        pg.click("tr[data-act=f-store]"); pg.wait_for_selector(".drawer .tbl"); pg.screenshot(path=f"{OUT}/15_finance_cash.png"); pg.keyboard.press("Escape"); pg.wait_for_selector(".drawer", state="detached")
        pg.click("[data-act=f-res] >> nth=0"); pg.wait_for_selector("#fnote"); pg.click(".modal [data-act=f-close] >> nth=0"); pg.wait_for_selector(".modal", state="detached")
        pg.click("[data-act=f-tab][data-v=gst]"); pg.wait_for_selector("tr[data-act=f-gd]"); pg.click("tr[data-act=f-gd][data-p='2026-09']"); pg.wait_for_selector(".drawer .tbl"); pg.screenshot(path=f"{OUT}/16_finance_gst.png"); pg.keyboard.press("Escape")
        pg.click("[data-act=f-tab][data-v=payables]"); pg.wait_for_selector("#fbody .bars"); pg.click("[data-act=f-tab][data-v=journal]"); pg.wait_for_selector("tr[data-act=f-jv]"); pg.click("tr[data-act=f-jv] >> nth=0"); pg.wait_for_selector(".modal .tbl"); pg.screenshot(path=f"{OUT}/17_finance_journal.png"); pg.keyboard.press("Escape")
        pg.set_viewport_size({"width": 1440, "height": 900}); b.close()
    print("console errors:", errs or "none"); assert not errs, errs
    print("smoke ok")
finally:
    srv.terminate()
