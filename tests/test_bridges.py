"""Cross-module bridges: ledger movements move the demand position, open suggestions follow it, POS bills after history show in Control Tower."""
import os, shutil, sqlite3
import pytest
from fastapi.testclient import TestClient
from dfh.app import create_app

SRC = os.getenv("DFH_DB", "sqlite:///data/dfh.db").replace("sqlite:///", "")
TODAY = "2026-10-31"


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    p = str(tmp_path_factory.mktemp("db") / "dfh.db"); shutil.copy(SRC, p)
    c = TestClient(create_app("sqlite:///" + p, os.getenv("DFH_DATA", "data"), serve_frontend=False))
    return c, p


def H(c, user="ceo"):
    return {"Authorization": "Bearer " + c.post("/api/login", json=dict(username=user, password="demo1234")).json()["token"]}


def q(p, sql, *a):
    con = sqlite3.connect(p)
    try: return con.execute(sql, a).fetchall()
    finally: con.close()


def test_transfer_moves_position_and_suggestion(env):
    c, p = env; h = H(c)
    row = q(p, "select r.id, r.location_id, r.sku_id, r.suggested_qty, p.on_hand from reorder_suggestion r join stock_position p on p.location_id=r.location_id and p.sku_id=r.sku_id "
               "join sku s on s.id=r.sku_id join stock_balance b on b.location_id=r.location_id and b.sku_id=r.sku_id and b.qty>=1 join batch bt on bt.id=b.batch_id "
               "where r.status='open' and s.base_uom='ea' and p.on_hand>=5 and bt.expiry_date>=? and r.on_hand=p.on_hand order by r.id limit 1", TODAY)
    assert row, "need an open suggestion with fresh ledger stock"
    sid, loc, sku, sq, oh = row[0]; to = 2 if loc == 1 else 1
    c.get("/api/demand/suggestions?size=1", headers=h)                                   # refresh has nothing to do on a clean seed
    assert q(p, "select suggested_qty from reorder_suggestion where id=?", sid)[0][0] == sq
    t = c.post("/api/inv/transfers", headers=h, json=dict(from_id=loc, to_id=to, lines=[dict(sku_id=sku, qty=1)]))
    assert t.status_code == 200, t.text
    d = c.post(f"/api/inv/transfers/{t.json()['id']}/dispatch", headers=h, json=dict(vehicle_no="KA01AB1234")); assert d.status_code == 200, d.text
    assert q(p, "select on_hand from stock_position where location_id=? and sku_id=?", loc, sku)[0][0] == oh - 1
    c.get("/api/demand/suggestions?size=1", headers=h)
    r = q(p, "select suggested_qty, on_hand, status from reorder_suggestion where id=?", sid)[0]
    assert r[1] == oh - 1 and r[0] >= sq + 1 and r[2] == "open"                            # less stock, more to buy


def test_suggestion_closes_when_covered(env):
    c, p = env; h = H(c)
    row = q(p, "select r.id, r.location_id, r.sku_id, r.suggested_qty, r.on_hand from reorder_suggestion r where r.status='open' and r.on_hand=(select on_hand from stock_position where location_id=r.location_id and sku_id=r.sku_id) order by r.id desc limit 1")
    sid, loc, sku, sq, oh = row[0]
    con = sqlite3.connect(p); con.execute("update stock_position set on_hand=on_hand+? where location_id=? and sku_id=?", (sq * 2, loc, sku)); con.commit(); con.close()
    c.get("/api/demand/suggestions?size=1", headers=h)
    assert q(p, "select status from reorder_suggestion where id=?", sid)[0][0] == "covered"
    assert c.post(f"/api/demand/suggestions/{sid}/decision", headers=h, json=dict(action="approve")).status_code == 409


def test_live_pos_shows_in_control_tower(env):
    c, p = env; h = H(c)
    a = c.get("/api/ct/live-pos", headers=h).json(); since = a["since"]
    con = sqlite3.connect(p)
    con.execute("insert into sale(id, store_id, device_id, invoice_no, business_date, created_at_device, received_at, cashier_id, gross_paise, discount_paise, tax_paise, net_paise, round_off_paise, status, idem_key, currency) "
                "select 'live-test-1', store_id, device_id, 'LIVE-TEST-1', '2026-11-05', created_at_device, '2026-11-05 10:00:00', cashier_id, gross_paise, discount_paise, tax_paise, net_paise, round_off_paise, 'paid', 'live-test-1', currency from sale where status='paid' limit 1")
    nt = con.execute("select net_paise from sale where id='live-test-1'").fetchone()[0]; con.commit(); con.close()
    b = c.get("/api/ct/live-pos", headers=h).json()
    assert b["since"] == since and b["bills"] == a["bills"] + 1 and b["net"] == a["net"] + nt and b["top"]
    hist = c.get("/api/ct/summary?days=30", headers=h).json()
    assert hist["end"] == since                                                           # the modelled history is untouched by live bills
