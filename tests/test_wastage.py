import os, math, pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from dfh.app import create_app
from dfh.db import get_engine

DB = os.getenv("DFH_DB", "sqlite:///data/dfh.db")


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app(DB, os.getenv("DFH_DATA", "data"), serve_frontend=False))


@pytest.fixture(scope="module")
def eng():
    return get_engine(DB)


def tok(c, user="ceo"):
    r = c.post("/api/login", json=dict(username=user, password="demo1234")); assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_seed_shape(eng):
    with eng.connect() as c:
        n = c.execute(text("select count(*) from wastage_entry")).scalar(); assert 30000 < n < 60000
        assert c.execute(text("select count(*) from wastage_entry where reason not in (select code from wastage_reason)")).scalar() == 0
        assert c.execute(text("select count(*) from wastage_entry where cost_paise <= 0 or qty <= 0")).scalar() == 0
        assert c.execute(text("select count(*) from wastage_entry where status='pending' and approved_by is not null")).scalar() == 0
        assert c.execute(text("select count(*) from batch where expiry_date <= received_on")).scalar() == 0
        assert c.execute(text("select count(*) from stock_balance where qty < 0")).scalar() == 0


def test_summary_and_ranges(client):
    h = tok(client); s = client.get("/api/wastage/summary?days=30", headers=h).json()
    assert s["cost"] > 0 and 0.003 < s["store_pct_cogs"] < 0.02, s["store_pct_cogs"]
    assert 0 < s["controllable"] <= 1 and s["pending"]["n"] > 0 and s["expiry_risk"]["value"] > 0
    w = client.get("/api/wastage/summary?days=7", headers=h).json(); assert w["cost"] < s["cost"]
    r = client.get("/api/wastage/reasons?days=30", headers=h).json(); assert abs(sum(x["share"] for x in r) - 1) < 1e-6
    assert r[0]["code"] in ("EXPIRY", "DAMAGE")
    t90 = client.get("/api/wastage/trend?days=90", headers=h).json(); assert 10 <= len(t90) <= 15
    assert all(x["controllable"] <= x["cost"] for x in t90)


def test_planted_f1_shrink_warehouse(client, eng):
    h = tok(client)
    with eng.connect() as c: wid = c.execute(text("select params from demo_finding where code='F1'")).scalar()
    name = "Hyderabad Warehouse 1"; assert "6" in wid
    r = client.get("/api/wastage/locations?kind=warehouse&days=30", headers=h).json()
    top = r["rows"][0]; assert top["name"] == name and top["flag"] and top["vs_peer"] >= 2.5, top
    assert sum(1 for x in r["rows"] if x["flag"]) == 1
    ex = client.get("/api/ct/exceptions", headers=h).json(); assert any(e["type"] == "shrink" and name in e["title"] for e in ex)
    older = client.get("/api/wastage/locations?kind=warehouse&days=184", headers=h).json()["rows"][0]; assert older["name"] == name


def test_planted_f6_pineapple_expiry(client):
    h = tok(client)
    s = client.get("/api/wastage/skus?days=90&reason=EXPIRY&kind=store", headers=h).json(); assert all("Pineapple" in x["name"] for x in s[:3]) and s[0]["expiry"] == s[0]["cost"]
    assert client.get("/api/wastage/skus?days=90&reason=THEFT", headers=h).json()[0]["expiry"] == 0
    e = client.get("/api/wastage/expiry?window=30&kind=store", headers=h).json()
    assert e["rows"] and all(r["days_left"] <= 30 for r in e["rows"]) and "expired" in e["buckets"]
    assert any("Pineapple" in t["sku"] for t in e["top_skus"])
    assert any(e2["type"] == "expiry" and "Pineapple" in e2["detail"] for e2 in client.get("/api/ct/exceptions", headers=h).json())
    assert [r["value"] for r in e["rows"]] == sorted((r["value"] for r in e["rows"]), reverse=True)


def test_store_league_outliers(client):
    r = client.get("/api/wastage/locations?kind=store&days=30", headers=tok(client)).json()
    assert len(r["rows"]) == 15 and r["rows"][0]["pct"] >= r["rows"][-1]["pct"] and r["median"] > 0
    b = client.get("/api/wastage/locations?kind=store&order=best", headers=tok(client)).json(); assert b["rows"][0]["pct"] <= b["rows"][-1]["pct"]


def test_roles_and_scope(client):
    assert client.get("/api/wastage/summary").status_code == 401
    assert client.get("/api/wastage/summary", headers=tok(client, "cashier")).status_code == 403
    assert client.get("/api/wastage/summary", headers=tok(client, "hr")).status_code == 403
    sm = tok(client, "storemgr"); ent = client.get("/api/wastage/entries?size=100", headers=sm).json()
    assert ent["total"] > 0 and {x["lname"] for x in ent["items"]} == {ent["items"][0]["lname"]}
    wh = tok(client, "warehouse"); l = client.get("/api/wastage/locations?kind=warehouse", headers=wh).json(); assert l["total"] == 1
    assert client.post("/api/wastage/entries", headers=sm, json=dict(location_id=1, sku_id=394, qty=100, reason="SPILL")).status_code == 403
    assert client.post("/api/wastage/entries", headers=tok(client, "finance"), json=dict(location_id=21, sku_id=394, qty=100, reason="SPILL")).status_code == 403


def test_entry_validation(client):
    h = tok(client)
    ok = dict(location_id=21, sku_id=394, qty=100, reason="SPILL")
    for bad in (dict(qty=0), dict(qty=-5), dict(reason="NOPE"), dict(sku_id=99999), dict(location_id=999999), dict(qty=10**9)):
        r = client.post("/api/wastage/entries", headers=h, json={**ok, **bad}); assert r.status_code == 422, (bad, r.status_code)
    assert client.post("/api/wastage/entries", headers=h, json={**ok, "batch_id": 1}).status_code == 422


def test_entry_approval_flow_restores_stock(client, eng):
    h, fin = tok(client), tok(client, "finance")
    with eng.connect() as c:
        row = c.execute(text("select b.location_id, b.sku_id, b.batch_id, b.qty, s.std_cost_paise from stock_balance b join sku s on s.id=b.sku_id join location l on l.id=b.location_id "
                             "where l.type='warehouse' and s.base_uom='ea' and b.qty>=10 and s.std_cost_paise>=20000 limit 1")).fetchone()
    loc, sku, batch, bal, cost = row; q = math.ceil(200000 / cost); assert q <= bal
    r = client.post("/api/wastage/entries", headers=h, json=dict(location_id=loc, sku_id=sku, batch_id=batch, qty=q, reason="DAMAGE", note="test")); assert r.status_code == 200, r.text
    eid = r.json()["id"]; assert r.json()["status"] == "pending" and r.json()["cost_paise"] == q * cost
    try:
        bal_of = lambda: eng.connect().execute(text("select qty from stock_balance where location_id=:l and sku_id=:s and batch_id=:b"), dict(l=loc, s=sku, b=batch)).scalar()
        assert bal_of() == bal - q
        assert client.post(f"/api/wastage/entries/{eid}/decision", headers=h, json=dict(action="approve")).status_code == 403   # own entry
        assert client.post(f"/api/wastage/entries/{eid}/decision", headers=fin, json=dict(action="maybe")).status_code == 422
        assert client.post(f"/api/wastage/entries/{eid}/decision", headers=fin, json=dict(action="reject")).json()["status"] == "rejected"
        assert bal_of() == bal
        assert client.post(f"/api/wastage/entries/{eid}/decision", headers=fin, json=dict(action="approve")).status_code == 409
        over = client.post("/api/wastage/entries", headers=h, json=dict(location_id=loc, sku_id=sku, batch_id=batch, qty=bal + 1, reason="DAMAGE")); assert over.status_code == 422 and "Only" in over.json()["detail"]
        r2 = client.post("/api/wastage/entries", headers=h, json=dict(location_id=loc, sku_id=sku, batch_id=batch, qty=q, reason="DAMAGE")); eid2 = r2.json()["id"]
        assert client.post(f"/api/wastage/entries/{eid2}/decision", headers=fin, json=dict(action="approve")).json()["status"] == "approved"
        aud = client.get("/api/wastage/entries?status=approved&size=100", headers=h).json(); assert aud["total"] > 0
        with eng.begin() as c:
            assert c.execute(text("select count(*) from audit_log where table_name='wastage_entry' and row_id in (:a,:b)"), dict(a=str(eid), b=str(eid2))).scalar() >= 4
            c.execute(text("delete from wastage_entry where id in (:a,:b)"), dict(a=eid, b=eid2))
    finally:
        with eng.begin() as c:
            c.execute(text("delete from wastage_entry where id=:a"), dict(a=eid)); c.execute(text("delete from audit_log where table_name='wastage_entry' and row_id=:a"), dict(a=str(eid)))
            c.execute(text("update stock_balance set qty=:q where location_id=:l and sku_id=:s and batch_id=:b"), dict(q=bal, l=loc, s=sku, b=batch))


def test_small_entry_posts_straight_away(client, eng):
    h = tok(client)
    r = client.post("/api/wastage/entries", headers=h, json=dict(location_id=21, sku_id=394, qty=50, reason="SAMPLE")); assert r.status_code == 200 and r.json()["status"] == "approved"
    with eng.begin() as c:
        c.execute(text("delete from wastage_entry where id=:a"), dict(a=r.json()["id"])); c.execute(text("delete from audit_log where table_name='wastage_entry' and row_id=:a"), dict(a=str(r.json()["id"])))


def test_markdown_actions(client, eng):
    h = tok(client)
    with eng.connect() as c: m = c.execute(text("select id, location_id from markdown_suggestion where status='open' order by id limit 1")).fetchone()
    assert client.post(f"/api/wastage/markdowns/{m[0]}", headers=tok(client, "finance"), json=dict(action="accept")).status_code == 403
    assert client.post(f"/api/wastage/markdowns/{m[0]}", headers=h, json=dict(action="bad")).status_code == 422
    try:
        assert client.post(f"/api/wastage/markdowns/{m[0]}", headers=h, json=dict(action="accept")).json()["status"] == "accepted"
        assert client.post(f"/api/wastage/markdowns/{m[0]}", headers=h, json=dict(action="dismiss")).status_code == 409
    finally:
        with eng.begin() as c:
            c.execute(text("update markdown_suggestion set status='open' where id=:i"), dict(i=m[0])); c.execute(text("delete from audit_log where table_name='markdown_suggestion' and row_id=:i"), dict(i=str(m[0])))
