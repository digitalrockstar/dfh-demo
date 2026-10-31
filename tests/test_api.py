import os, pytest
from fastapi.testclient import TestClient
from dfh.app import create_app

DB = os.getenv("DFH_DB", "sqlite:///data/dfh.db")


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app(DB, os.getenv("DFH_DATA", "data"), serve_frontend=False))


def tok(c, user="ceo"):
    r = c.post("/api/login", json=dict(username=user, password="demo1234")); assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_login_and_guard(client):
    assert client.post("/api/login", json=dict(username="ceo", password="bad")).status_code == 401
    assert client.get("/api/skus").status_code == 401
    assert client.get("/api/me", headers=tok(client)).json()["role"] == "ceo"


def test_sku_list_filters_sort(client):
    h = tok(client)
    r = client.get("/api/skus?size=10", headers=h).json(); assert r["total"] == 1200 and len(r["items"]) == 10
    assert all(0 < i["gm"] < 0.7 for i in r["items"])
    g = client.get("/api/skus?cat=GFT&size=200", headers=h).json(); assert g["total"] == 85
    s = client.get("/api/skus?q=almonds california&sort=price&dir=asc&size=5", headers=h).json()["items"]
    assert s == sorted(s, key=lambda x: x["price"])
    assert client.get("/api/skus?status=draft", headers=h).json()["total"] == 0
    assert client.get("/api/skus/duplicates", headers=h).json() == []


def test_sku_detail_variants(client):
    h = tok(client)
    loose = client.get("/api/skus?ptype=bulk&size=1", headers=h).json()["items"][0]
    d = client.get(f"/api/skus/{loose['id']}", headers=h).json()
    assert len(d["packs"]) >= 1 and len(d["vendors"]) >= 2 and d["vendors"][0]["latest"] <= d["vendors"][-1]["latest"]
    pack = client.get(f"/api/skus/{d['packs'][0]['id']}", headers=h).json()
    assert pack["bulk_parent"]["id"] == loose["id"] and len(pack["vendors"]) >= 2
    kit = client.get("/api/skus?cat=GFT&size=1", headers=h).json()["items"][0]
    k = client.get(f"/api/skus/{kit['id']}", headers=h).json()["kit"]
    assert len(k["components"]) >= 3 and k["component_cost"] > 0
    assert d["sales30"]["net"] > 0
    assert client.get("/api/skus/999999", headers=h).status_code == 404


def test_price_change_rules_and_audit(client):
    h = tok(client)
    s = client.get("/api/skus?ptype=repacked&size=1&sort=code&dir=asc", headers=h).json()["items"][0]
    assert client.patch(f"/api/skus/{s['id']}", json=dict(mrp_paise=100), headers=h).status_code == 422          # below cost
    assert client.patch(f"/api/skus/{s['id']}", json=dict(price_per_kg_paise=99999), headers=h).status_code == 422  # wrong field
    assert client.patch(f"/api/skus/{s['id']}", json=dict(status="draft"), headers=h).status_code == 422          # bad move
    new = s["mrp_paise"] + 500
    r = client.patch(f"/api/skus/{s['id']}", json=dict(mrp_paise=new, reason="test"), headers=h); assert r.status_code == 200 and r.json()["mrp_paise"] == new
    hist = client.get(f"/api/skus/{s['id']}", headers=h).json()["history"]; assert hist and hist[0]["action"] == "price_change"
    client.patch(f"/api/skus/{s['id']}", json=dict(mrp_paise=s["mrp_paise"]), headers=h)                           # restore
    assert client.patch(f"/api/skus/{s['id']}", json=dict(mrp_paise=new), headers=tok(client, "cashier")).status_code == 403


def test_import_validate_then_apply(client):
    h = tok(client, "procurement")
    s = client.get("/api/skus?ptype=repacked&size=2&sort=code&dir=desc", headers=h).json()["items"]
    bad = "sku_code,mrp_rupees,status\nNOPE,100,active\n%s,abc,\n%s,1,\n" % (s[0]["code"], s[1]["code"])
    r = client.post("/api/skus/import", json=dict(csv=bad, apply=True), headers=h).json()
    assert r["applied"] is False and len(r["errors"]) == 3
    ok = "sku_code,mrp_rupees\n%s,%s\n" % (s[0]["code"], (s[0]["mrp_paise"] + 500) / 100)
    assert client.post("/api/skus/import", json=dict(csv=ok), headers=h).json()["applied"] is False
    assert client.post("/api/skus/import", json=dict(csv=ok, apply=True), headers=h).json()["applied"] is True
    client.post("/api/skus/import", json=dict(csv="sku_code,mrp_rupees\n%s,%s\n" % (s[0]["code"], s[0]["mrp_paise"] / 100), apply=True), headers=h)
    assert client.post("/api/skus/import", json=dict(csv=ok, apply=True), headers=tok(client, "hr")).status_code == 403


def test_control_tower(client):
    h = tok(client)
    s = client.get("/api/ct/summary?days=30", headers=h).json()
    assert s["current"]["net"] > 0 and 0.15 < s["current"]["gm"] < 0.5 and s["previous"] and s["current"]["stores"] == 500
    assert s["end"] == "2026-10-31" and s["stockouts"]["events"] > 0
    assert len(client.get("/api/ct/trend?days=90", headers=h).json()) == 90
    mix = client.get("/api/ct/categories", headers=h).json(); assert abs(sum(m["share"] for m in mix) - 1) < 1e-6
    top = client.get("/api/ct/league?order=top", headers=h).json()["rows"]; assert len(top) == 10 and top[0]["per_day"] >= top[-1]["per_day"]
    bot = client.get("/api/ct/league?order=bottom", headers=h).json()["rows"]; assert bot[0]["per_day"] <= bot[-1]["per_day"] and not any(b["new"] for b in bot)
    reg = client.get("/api/ct/summary?region=GCC", headers=h).json(); assert 0 < reg["current"]["stores"] < 500
    ex = client.get("/api/ct/exceptions", headers=h).json()
    assert sum(1 for e in ex if e["type"] == "sync") == 3
    assert any(e["type"] == "stockout" and "Pune" in e["title"] for e in ex)


def test_scope_for_store_manager(client):
    h = tok(client, "storemgr")
    assert client.get("/api/ct/summary", headers=h).json()["current"]["stores"] == 1
    assert client.get("/api/ct/summary", headers=tok(client, "cashier")).status_code == 403
