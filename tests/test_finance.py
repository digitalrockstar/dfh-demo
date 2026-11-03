import os, pytest
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


def tok(c, user="finance"):
    r = c.post("/api/login", json=dict(username=user, password="demo1234")); assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


@pytest.fixture
def restore(eng):
    with eng.connect() as c:
        mark = dict(j=c.execute(text("select coalesce(max(id),0) from journal_entry")).scalar(), a=c.execute(text("select coalesce(max(id),0) from audit_log")).scalar(),
                    r=c.execute(text("select coalesce(max(id),0) from recon_item")).scalar(), snap=[tuple(x) for x in c.execute(text("select id, status, note, resolved_by, resolved_at, matched_to from recon_item"))])
    yield
    with eng.begin() as c:
        c.execute(text("delete from journal_line where jv_id>:j"), dict(j=mark["j"])); c.execute(text("delete from journal_entry where id>:j"), dict(j=mark["j"]))
        c.execute(text("delete from audit_log where id>:a"), dict(a=mark["a"])); c.execute(text("delete from recon_item where id>:r"), dict(r=mark["r"]))
        for i, s, n, rb, ra, mt in mark["snap"]: c.execute(text("update recon_item set status=:s, note=:n, resolved_by=:rb, resolved_at=:ra, matched_to=:mt where id=:i"), dict(i=i, s=s, n=n, rb=rb, ra=ra, mt=mt))
        c.execute(text("delete from period_lock where entity_id=17 and period='2026-09'"))


def test_books_balance_and_tie_to_sales(client, eng):
    import duckdb
    with eng.connect() as c:
        assert c.execute(text("select count(*) from (select jv_id from journal_line group by jv_id having sum(debit_paise)!=sum(credit_paise))")).scalar() == 0
        gl = c.execute(text("select sum(credit_paise - debit_paise) from journal_line where account_code in ('4000','4001','2100','2101')")).scalar()
        s = c.execute(text("select coalesce(sum(case when status!='in_transit' then expected_paise end),0) - sum(received_paise) - sum(fee_paise) - coalesce(sum(case when status in ('short','held') then expected_paise-fee_paise-received_paise end),0) from settlement")).scalar()
    net = duckdb.connect().execute("select sum(net_paise) from read_parquet('data/sales_daily/*/*.parquet', hive_partitioning=true)").fetchone()[0]
    assert gl == net and s == 0


def test_f4_weekend_cash_pattern(client):
    h = tok(client); r = client.get("/api/finance/cash/stores?days=60&flagged=1", headers=h).json()
    assert r["flagged"] == 1 and r["rows"][0]["id"] == 95 and "Borivali" in r["rows"][0]["name"] and r["rows"][0]["weekend_short_days"] >= 4
    assert any(e["type"] == "cash" and "Borivali" in e["title"] for e in client.get("/api/ct/exceptions", headers=h).json())
    d = client.get("/api/finance/cash/store/95?days=60", headers=h).json(); assert d["rows"] and any(x["weekday"] in ("Sat", "Sun") and x["variance_paise"] <= -100000 for x in d["rows"])


def test_f5_open_day_closes(client, eng):
    with eng.connect() as c: n = c.execute(text("select count(*) from day_close where status='open' and business_date>='2026-10-30'")).scalar()
    assert n == 6 and client.get("/api/finance/summary?days=30", headers=tok(client)).json()["cash"]["not_closed"] == 6


def test_f8_input_credit_mismatch(client):
    h = tok(client); rows = {r["period"]: r for r in client.get("/api/finance/gst?entity_id=1", headers=h).json()["rows"]}; s = rows["2026-09"]
    assert (s["missing_n"], s["mismatch_n"], s["unbooked_n"]) == (4, 2, 3) and s["at_risk"] == s["missing_tax"] + s["mismatch_tax"] > 0 and s["status"] == "review" and not s["locked"]
    assert rows["2026-08"]["at_risk"] == 0 and rows["2026-08"]["locked"] and not rows["2026-10"]["available"]
    d = client.get("/api/finance/gst/detail?entity_id=1&period=2026-09", headers=h).json(); assert len(d["missing"]) == 4 and len(d["mismatch"]) == 2 and len(d["unbooked"]) == 3
    assert all(r["at_risk"] == 0 for r in client.get("/api/finance/gst?entity_id=2", headers=h).json()["rows"])
    assert any(e["type"] == "gst" and "DFH-KA" in e["title"] for e in client.get("/api/ct/exceptions", headers=h).json())
    assert client.get("/api/finance/gst?entity_id=17", headers=h).status_code == 404


def test_month_close_and_lock(client, restore):
    h = tok(client); b = {r["entity"]["code"]: r for r in client.get("/api/finance/close?period=2026-09", headers=h).json()["rows"]}
    assert b["DFH-KA"]["blockers"] and b["DFH-KA"]["blockers"][0]["key"] == "gst" and b["DFH-QA"]["ready"] and not b["DFH-QA"]["locked"] and b["DFH-AE"]["locked"]
    r = client.post("/api/finance/close/lock", headers=h, json=dict(entity_id=1, period="2026-09")); assert r.status_code == 422 and "GSTR-2B" in r.json()["detail"]
    assert client.post("/api/finance/close/lock", headers=h, json=dict(entity_id=17, period="2026-10")).status_code == 422
    assert client.post("/api/finance/close/lock", headers=tok(client, "storemgr"), json=dict(entity_id=17, period="2026-09")).status_code == 403
    assert client.post("/api/finance/close/lock", headers=h, json=dict(entity_id=17, period="2026-09")).status_code == 200
    assert client.post("/api/finance/close/lock", headers=h, json=dict(entity_id=17, period="2026-09")).status_code == 409


def test_resolve_posts_journal(client, eng, restore):
    h = tok(client)
    with eng.connect() as c: item = c.execute(text("select id from recon_item where status='open' and source='settlement' order by id limit 1")).scalar()
    assert client.post(f"/api/finance/recon/{item}/resolve", headers=h, json=dict(action="match", note="x")).status_code == 422
    assert client.post(f"/api/finance/recon/{item}/resolve", headers=tok(client, "storemgr"), json=dict(action="match", note="Matched to bank credit")).status_code == 403
    before = client.get("/api/finance/summary", headers=h).json()["recon"]["n"]
    assert client.post(f"/api/finance/recon/{item}/resolve", headers=h, json=dict(action="match", note="Matched to bank credit")).status_code == 200
    assert client.post(f"/api/finance/recon/{item}/resolve", headers=h, json=dict(action="match", note="Matched to bank credit")).status_code == 409
    assert client.get("/api/finance/summary", headers=h).json()["recon"]["n"] == before - 1
    with eng.connect() as c:
        assert c.execute(text("select count(*) from journal_entry where jv_no like '%/ADJ/R%'")).scalar() == 1
        assert c.execute(text("select count(*) from audit_log where action='recon.match'")).scalar() >= 1
        assert c.execute(text("select count(*) from (select jv_id from journal_line group by jv_id having sum(debit_paise)!=sum(credit_paise))")).scalar() == 0


def test_write_off_limit(client, eng, restore):
    with eng.begin() as c:
        i = c.execute(text("insert into recon_item(source, source_ref, store_id, business_date, amount_paise, status) values ('day_close','DC-TEST',95,'2026-10-30',-3000000,'open')")).lastrowid
    r = client.post(f"/api/finance/recon/{i}/resolve", headers=tok(client), json=dict(action="write_off", note="Large shortage, approved"))
    assert r.status_code == 403 and "CEO" in r.json()["detail"]
    assert client.post(f"/api/finance/recon/{i}/resolve", headers=tok(client, "ceo"), json=dict(action="write_off", note="Large shortage, approved")).status_code == 200


def test_roles_and_scope(client):
    for u, path, code in (("cashier", "/api/finance/summary", 403), ("procurement", "/api/finance/summary", 403), ("procurement", "/api/finance/payables", 200), ("storemgr", "/api/finance/payables", 403),
                          ("storemgr", "/api/finance/gst?entity_id=1", 403), ("storemgr", "/api/finance/journal?entity_id=1", 403), ("storemgr", "/api/finance/cash/store/95", 403), ("storemgr", "/api/finance/summary", 200), ("ceo", "/api/finance/close?period=2026-09", 200)):
        assert client.get(path, headers=tok(client, u)).status_code == code, (u, path)
    h = tok(client, "storemgr"); s = client.get("/api/finance/summary?days=30", headers=h).json(); assert s["cash"]["closes"] <= 30 and "payables" not in s
    assert len({i["store_id"] for i in client.get("/api/finance/recon?status=", headers=h).json()["items"]}) <= 1


def test_payables_trial_balance_export(client):
    h = tok(client); p = client.get("/api/finance/payables", headers=h).json()
    assert p["total"] == sum(b["v"] for b in p["buckets"].values()) > 0 and p["overdue"] == p["total"] - p["buckets"]["not_due"]["v"] and len(p["vendors"]) <= 12
    tb = client.get("/api/finance/trial-balance?entity_id=1&period=2026-09", headers=h).json(); assert tb["debit"] == tb["credit"] > 0
    r = client.get("/api/finance/journal/export?entity_id=17&period=2026-09", headers=h); assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    import csv, io
    rows = list(csv.DictReader(io.StringIO(r.text))); assert len(rows) > 100 and round(sum(float(x["debit"]) for x in rows), 2) == round(sum(float(x["credit"]) for x in rows), 2)
    j = client.get("/api/finance/journal?entity_id=1&period=2026-09&size=5", headers=h).json(); one = client.get(f"/api/finance/journal/{j['items'][0]['id']}", headers=h).json()
    assert len(j["items"]) == 5 and sum(l["debit_paise"] for l in one["lines"]) == sum(l["credit_paise"] for l in one["lines"])


def test_settlement_views(client):
    h = tok(client); s = client.get("/api/finance/settlements?days=184", headers=h).json(); assert {m["mode"] for m in s["modes"]} == {"CARD", "UPI"}
    for m in s["modes"]: assert m["expected"] == m["received"] + m["fee"] + m["gap"]
    assert s["items"] and all(i["status"] in ("short", "held") for i in s["items"])
    card = next(m for m in s["modes"] if m["mode"] == "CARD"); upi = next(m for m in s["modes"] if m["mode"] == "UPI"); assert upi["fee"] == 0 and 0.017 < card["fee"] / card["expected"] < 0.019
