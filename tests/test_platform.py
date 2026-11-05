import os, shutil, pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from dfh.app import create_app
from dfh.db import get_engine

SRC = os.getenv("DFH_DB", "sqlite:///data/dfh.db").replace("sqlite:///", "")


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    p = str(tmp_path_factory.mktemp("db") / "dfh.db"); shutil.copy(SRC, p); url = "sqlite:///" + p
    return TestClient(create_app(url, os.getenv("DFH_DATA", "data"), serve_frontend=False)), get_engine(url)


def tok(c, user):
    r = c.post("/api/login", json=dict(username=user, password="demo1234")); assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def q(e, sql, **p):
    with e.connect() as c: return c.execute(text(sql), p).fetchall()


def test_seed_shape(env):
    c, e = env
    assert q(e, "select count(*) from approval_rule")[0][0] == 4
    assert q(e, "select count(*) from approval_request where status='pending'")[0][0] == 4
    assert q(e, "select count(*) from approval_request where approver_id=requested_by")[0][0] == 0
    assert q(e, "select count(*) from sync_log")[0][0] > 10000
    assert q(e, "select count(*) from approval_request where status='approved' and approver_id is null")[0][0] == 0


def test_payment_release_flow(env):
    c, e = env
    opts = c.get("/api/platform/approvals/options", headers=tok(c, "procurement")).json()
    inv = opts["invoices"][0]
    r = c.post("/api/platform/approvals", json=dict(doc_type="payment_release", ref=str(inv["id"]), note="Due this week"), headers=tok(c, "procurement")); assert r.status_code == 200, r.text
    rid, need = r.json()["id"], r.json()["approver_role"]
    assert c.post("/api/platform/approvals", json=dict(doc_type="payment_release", ref=str(inv["id"])), headers=tok(c, "procurement")).status_code == 409   # duplicate
    d = lambda who, **b: c.post(f"/api/platform/approvals/{rid}/decide", json=b, headers=tok(c, who))
    assert d("procurement", action="approve").status_code == 403                                   # requester role cannot approve
    assert d("cashier", action="approve").status_code == 403
    other = "ceo" if need == "finance" else "finance"
    if need == "ceo": assert d("finance", action="approve").status_code == 403                     # wrong band
    assert d(need, action="reject").status_code == 422                                              # reason needed
    assert d(need, action="approve").status_code == 200
    assert q(e, "select status from vendor_invoice where id=:i", i=inv["id"])[0][0] == "released"
    assert d(need, action="approve").status_code == 409
    assert q(e, "select count(*) from audit_log where table_name='vendor_invoice' and row_id=:i and action='release'", i=str(inv["id"]))[0][0] == 1
    n = c.get("/api/platform/notifications", headers=tok(c, "procurement")).json()
    assert any(x["ref_id"] == str(rid) for x in n)


def test_self_approval_blocked(env):
    c, e = env
    inv = c.get("/api/platform/approvals/options", headers=tok(c, "finance")).json()["invoices"][0]
    rid = c.post("/api/platform/approvals", json=dict(doc_type="payment_release", ref=str(inv["id"])), headers=tok(c, "finance")).json()["id"]
    assert c.post(f"/api/platform/approvals/{rid}/decide", json=dict(action="approve"), headers=tok(c, "finance")).status_code == 403
    assert c.post(f"/api/platform/approvals/{rid}/cancel", headers=tok(c, "finance")).status_code == 200
    assert q(e, "select status from vendor_invoice where id=:i", i=inv["id"])[0][0] == "pending"


def test_price_change_bands(env):
    c, e = env
    s = q(e, "select s.id, s.code, s.mrp_paise from sku s where s.base_uom='ea' and s.status='active' and s.mrp_paise>0 and not exists (select 1 from approval_request a where a.doc_type='price_change' and a.doc_id like s.id||':%') order by s.id limit 2")
    a, b = s
    assert c.post("/api/platform/approvals", json=dict(doc_type="price_change", ref=a[1], value=a[2] * 1.05 / 100), headers=tok(c, "procurement")).status_code == 422   # under 10 percent
    assert c.post("/api/platform/approvals", json=dict(doc_type="price_change", ref=a[1], value=a[2] * 1.15 / 100), headers=tok(c, "finance")).status_code == 403
    r = c.post("/api/platform/approvals", json=dict(doc_type="price_change", ref=a[1], value=a[2] * 1.15 / 100), headers=tok(c, "procurement")); assert r.status_code == 200 and r.json()["approver_role"] == "finance"
    assert c.post(f"/api/platform/approvals/{r.json()['id']}/decide", json=dict(action="approve"), headers=tok(c, "finance")).status_code == 200
    assert q(e, "select mrp_paise from sku where id=:i", i=a[0])[0][0] == int(round(a[2] * 1.15 / 100 * 100)) or abs(q(e, "select mrp_paise from sku where id=:i", i=a[0])[0][0] - a[2] * 1.15) <= 1
    r = c.post("/api/platform/approvals", json=dict(doc_type="price_change", ref=b[1], value=b[2] * 1.4 / 100), headers=tok(c, "procurement")); assert r.json()["approver_role"] == "ceo"
    assert c.post(f"/api/platform/approvals/{r.json()['id']}/decide", json=dict(action="approve"), headers=tok(c, "finance")).status_code == 403
    assert c.post(f"/api/platform/approvals/{r.json()['id']}/decide", json=dict(action="reject", note="Too steep"), headers=tok(c, "ceo")).status_code == 200
    assert q(e, "select mrp_paise from sku where id=:i", i=b[0])[0][0] == b[2]


def test_rules_edit(env):
    c, e = env
    items = c.get("/api/platform/rules", headers=tok(c, "ceo")).json()["items"]; pc = [x for x in items if x["doc_type"] == "payment_release"]
    lo = pc[0]
    assert c.patch(f"/api/platform/rules/{lo['id']}", json=dict(min_value=0, max_value=900000, approver="finance"), headers=tok(c, "ceo")).status_code == 422   # overlaps the next band
    assert c.patch(f"/api/platform/rules/{lo['id']}", json=dict(min_value=0, max_value=lo["max_value"], approver="finance"), headers=tok(c, "finance")).status_code == 403
    assert c.patch(f"/api/platform/rules/{lo['id']}", json=dict(min_value=0, max_value=lo["max_value"], approver="warehouse"), headers=tok(c, "ceo")).status_code == 422


def test_audit_viewer(env):
    c, e = env
    assert c.get("/api/platform/audit", headers=tok(c, "cashier")).status_code == 403
    a = c.get("/api/platform/audit?table=approval_request&size=20", headers=tok(c, "finance")).json()
    assert a["total"] > 20 and all(x["table_name"] == "approval_request" for x in a["items"]) and a["items"][0]["changes"]
    b = c.get("/api/platform/audit?frm=2026-10-01&to=2026-10-31&size=100", headers=tok(c, "ceo")).json()
    assert all("2026-10-01" <= str(x["ts"])[:10] <= "2026-10-31" for x in b["items"])
    assert c.get("/api/platform/audit?frm=bad", headers=tok(c, "ceo")).status_code == 422
    csv = c.get("/api/platform/audit/export?table=app_user", headers=tok(c, "admin")); assert csv.status_code == 200 and csv.text.startswith("time,user,action")
    s = c.get("/api/platform/audit/stats", headers=tok(c, "ceo")).json(); assert s["total"] == sum(d["n"] for d in s["daily"]) and s["by_action"]


def test_imports(env):
    c, e = env
    v = q(e, "select v.code, s.code, c.price_minor, c.effective_from from vendor_sku_cost c join vendor v on v.id=c.vendor_id join sku s on s.id=c.sku_id order by c.id desc limit 1")[0]
    price = v[2] / 100 * 1.05; eff = "2026-11-01"
    good = f"vendor_code,sku_code,price,effective_from\n{v[0]},{v[1]},{price},{eff}\n"
    bad = good + f"{v[0]},{v[1]},{price * 3},{eff}\nZZZ,{v[1]},10,{eff}\n"
    H = tok(c, "procurement")
    r = c.post("/api/platform/imports", json=dict(kind="vendor_costs", csv=bad, apply=True), headers=H).json()
    assert r["applied"] is False and len(r["errors"]) >= 2
    n0 = q(e, "select count(*) from vendor_sku_cost")[0][0]; assert n0 == q(e, "select count(*) from vendor_sku_cost")[0][0]
    assert c.post("/api/platform/imports", json=dict(kind="vendor_costs", csv=good), headers=H).json()["applied"] is False         # check only
    assert c.post("/api/platform/imports", json=dict(kind="vendor_costs", csv=good, apply=True, filename="t.csv"), headers=H).json()["applied"] is True
    assert q(e, "select count(*) from vendor_sku_cost")[0][0] == n0 + 1
    assert c.post("/api/platform/imports", json=dict(kind="vendor_costs", csv=good, apply=True), headers=H).json()["applied"] is False   # same date again
    st = q(e, "select l.code, s.code from store_assortment a join location l on l.id=a.store_id join sku s on s.id=a.sku_id limit 1")[0]
    mm = c.post("/api/platform/imports", json=dict(kind="store_minmax", csv=f"store_code,sku_code,min_qty,max_qty\n{st[0]},{st[1]},500,2000\n", apply=True), headers=H).json(); assert mm["applied"] is True
    assert q(e, "select a.min_qty, a.max_qty from store_assortment a join location l on l.id=a.store_id join sku s on s.id=a.sku_id where l.code=:a and s.code=:b", a=st[0], b=st[1])[0] == (500, 2000)
    assert c.post("/api/platform/imports", json=dict(kind="store_minmax", csv=f"store_code,sku_code,min_qty,max_qty\n{st[0]},{st[1]},900,100\n", apply=True), headers=H).json()["errors"]
    assert c.post("/api/platform/imports", json=dict(kind="store_minmax", csv="a,b\n1,2\n"), headers=H).status_code == 422
    assert c.post("/api/platform/imports", json=dict(kind="store_minmax", csv="x"), headers=tok(c, "hr")).status_code == 403
    jobs = c.get("/api/platform/imports", headers=H).json(); assert jobs[0]["kind"] == "store_minmax" or jobs[0]["status"] in ("applied", "rejected")


def test_entities_and_fx(env):
    c, e = env
    H = tok(c, "finance"); r = c.get("/api/platform/entities", headers=H).json()
    assert len(r["items"]) == 20 and r["total_sales"] == sum(x["sales30"] for x in r["items"]) and r["total_sales"] > 0
    assert sum(x["stores"] for x in r["items"]) == q(e, "select count(*) from location where type='store' and active=1")[0][0]
    assert c.get("/api/platform/entities", headers=tok(c, "hr")).status_code == 403
    assert c.get("/api/platform/entities/DFH-KA", headers=H).json()["monthly"]
    assert c.patch("/api/platform/entities/DFH-KA", json=dict(gstin="BAD"), headers=H).status_code == 422
    assert c.patch("/api/platform/entities/DFH-AE", json=dict(gstin="29ABCDE1234F1Z5"), headers=H).status_code == 422
    assert c.patch("/api/platform/entities/DFH-KA", json=dict(gstin="29ABCDE1234F1Z5"), headers=H).status_code == 200
    fx = c.get("/api/platform/fx", headers=H).json()["items"]; usd = [x for x in fx if x["currency"] == "USD"][0]
    assert c.post("/api/platform/fx", json=dict(currency="USD", month="2026-11", rate=usd["rate"] * 1.3), headers=H).status_code == 409
    assert c.post("/api/platform/fx", json=dict(currency="USD", month="2026-11", rate=usd["rate"] * 1.01), headers=H).status_code == 200
    assert c.post("/api/platform/fx", json=dict(currency="XXX", month="2026-11", rate=1), headers=H).status_code == 422
    assert c.post("/api/platform/fx", json=dict(currency="USD", month="2026-11", rate=-1), headers=H).status_code == 422


def test_users(env):
    c, e = env
    A = tok(c, "admin"); assert c.get("/api/platform/users", headers=tok(c, "finance")).status_code == 403
    r = c.post("/api/platform/users", json=dict(username="Asha.K", name="Asha K", role="store_manager", password="demo5678", scope_code=q(e, "select code from location where type='store' limit 1")[0][0]), headers=A)
    assert r.status_code == 200, r.text; uid = r.json()["id"]
    assert c.post("/api/platform/users", json=dict(username="asha.k", name="x", role="hr", password="demo5678"), headers=A).status_code == 409
    assert c.post("/api/platform/users", json=dict(username="nolocation", name="x", role="store_manager", password="demo5678"), headers=A).status_code == 422
    assert c.post("/api/platform/users", json=dict(username="weakpw", name="x", role="hr", password="short"), headers=A).status_code == 422
    assert c.post("/api/login", json=dict(username="asha.k", password="demo5678")).status_code == 200
    assert c.post(f"/api/platform/users/{uid}/password", json=dict(password="newpass99"), headers=A).status_code == 200
    assert c.post("/api/login", json=dict(username="asha.k", password="demo5678")).status_code == 401
    assert c.patch(f"/api/platform/users/{uid}", json=dict(active=False), headers=A).status_code == 200
    assert c.post("/api/login", json=dict(username="asha.k", password="newpass99")).status_code == 401
    me = [u for u in c.get("/api/platform/users", headers=A).json()["items"] if u["username"] == "admin"][0]
    assert c.patch(f"/api/platform/users/{me['id']}", json=dict(active=False), headers=A).status_code == 409
    ceo = [u for u in c.get("/api/platform/users", headers=A).json()["items"] if u["username"] == "ceo"][0]
    assert c.patch(f"/api/platform/users/{ceo['id']}", json=dict(active=False), headers=A).status_code == 200      # admin remains
    assert c.patch(f"/api/platform/users/{ceo['id']}", json=dict(active=True), headers=A).status_code == 200
    assert q(e, "select last_login from app_user where username='admin'")[0][0] is not None
    assert q(e, "select count(*) from audit_log where table_name='app_user' and action='password_reset'")[0][0] == 1


def test_roles_health_waiting(env):
    c, e = env
    m = c.get("/api/platform/roles", headers=tok(c, "ceo")).json(); pos = [r for r in m["rows"] if r["area"] == "Store POS"][0]["levels"]
    assert pos["cashier"] == "act" and pos["hr"] == "" and len(m["roles"]) == 9
    h = c.get("/api/platform/health", headers=tok(c, "ceo")).json(); d = h["devices"]
    assert d["total"] == d["online"] + d["delayed"] + d["stale"] and h["sync"]["runs"] > 0
    assert c.get("/api/platform/health", headers=tok(c, "cashier")).status_code == 403
    w = c.get("/api/platform/waiting", headers=tok(c, "ceo")).json(); assert {x["key"] for x in w} >= {"wastage", "buy", "leave"}
    assert c.get("/api/platform/waiting", headers=tok(c, "cashier")).json() == []
    s = c.get("/api/platform/summary", headers=tok(c, "ceo")).json(); assert "waiting_on_me" in s and s["audit30"] >= 0
    n = c.get("/api/platform/notifications", headers=tok(c, "finance")).json(); assert c.post("/api/platform/notifications/read", json={}, headers=tok(c, "finance")).json()["marked"] >= 0


def test_direct_price_gate(env):
    c, e = env
    k = q(e, "select id, mrp_paise from sku where base_uom='ea' and status='active' and mrp_paise>0 order by id limit 1 offset 40")[0]
    H = tok(c, "procurement")
    assert c.patch(f"/api/skus/{k[0]}", json=dict(mrp_paise=int(k[1] * 1.2)), headers=H).status_code == 422
    assert c.patch(f"/api/skus/{k[0]}", json=dict(mrp_paise=int(k[1] * 1.05)), headers=H).status_code == 200
    assert c.patch(f"/api/skus/{k[0]}", json=dict(mrp_paise=int(k[1] * 1.2)), headers=tok(c, "ceo")).status_code == 200
