"""Run after `python -m dfh.seed.run`. Checks the foundation: schema, masters, price book, 6-month history."""
import os, json
import duckdb, pytest
from sqlalchemy import text
from dfh.db import get_engine
from dfh.schema import metadata

DB = os.getenv("DFH_DB", "sqlite:///data/dfh.db"); DATA = os.getenv("DFH_DATA", "data")
SALES = f"read_parquet('{DATA}/sales_daily/*/*.parquet', hive_partitioning=true)"


@pytest.fixture(scope="module")
def q():
    eng = get_engine(DB)
    def run(sql):
        with eng.connect() as c:
            return c.execute(text(sql)).fetchall()
    return run


def test_schema_builds_clean():
    e = get_engine("sqlite://"); metadata.create_all(e)
    assert len(metadata.tables) >= 90


def test_counts(q):
    assert q("select count(*) from location where type='store'")[0][0] == 500
    assert q("select count(*) from location where type='warehouse'")[0][0] == 20
    assert q("select count(*) from sku")[0][0] == 1200
    assert q("select count(*) from vendor")[0][0] >= 55


def test_fk_integrity(q):
    assert q("pragma foreign_key_check") == []


def test_sku_quality(q):
    assert q("select count(*) from sku where hsn not in (select hsn from tax_rate)")[0][0] == 0
    assert q("select count(*) from sku where procurement_type='repacked' and bulk_sku_id is null")[0][0] == 0
    assert q("select count(*) from sku where procurement_type='bulk' and price_per_kg_paise is null")[0][0] == 0
    assert q("select count(*) from sku where base_uom='ea' and mrp_paise is null")[0][0] == 0
    assert q("select count(*) from sku where mrp_paise is not null and mrp_paise <= std_cost_paise")[0][0] == 0
    cats = {r[0] for r in q("select name from category where site_collection=1")}
    assert {"Nuts and Dry Fruits", "Dates", "DFH Exclusives", "Berries", "Seeds and More", "Gift Boxes"} <= cats
    assert q("select count(*) from kit_bom")[0][0] > 200


def test_many_to_many_price_book(q):
    assert q("select avg(c) from (select sku_id, count(distinct vendor_id) c from vendor_sku_cost group by sku_id)")[0][0] >= 2.0
    assert q("select min(c) from (select sku_id, count(distinct vendor_id) c from vendor_sku_cost group by sku_id)")[0][0] >= 2
    assert q("select count(*) from vendor where id not in (select vendor_id from vendor_sku_cost)")[0][0] == 0
    assert q("select avg(c) from (select vendor_id, count(distinct sku_id) c from vendor_sku_cost group by vendor_id)")[0][0] >= 8
    assert q("select min(c) from (select vendor_id, sku_id, count(*) c from vendor_sku_cost group by vendor_id, sku_id)")[0][0] == 7


def test_planted_vendor_price_creep(q):
    p = json.loads(q("select params from demo_finding where code='F2'")[0][0])
    v, s = p["vendor_id"], p["sku_ids"][0]
    r = q(f"select effective_from, price_minor from vendor_sku_cost where vendor_id={v} and sku_id={s} order by effective_from")
    assert r[-1][1] > r[3][1] * 1.12


def test_stale_stores_planted(q):
    assert q("select count(*) from location where type='store' and last_sync_at < '2026-10-30'")[0][0] == 3


def test_history_window_and_sanity():
    d = duckdb.sql(f"select min(date), max(date), count(*), min(qty), min(net_paise), count(distinct store_id) from {SALES}").fetchall()[0]
    assert str(d[0]) == "2026-05-01" and str(d[1]) == "2026-10-31"
    assert d[2] > 3_000_000 and d[3] > 0 and d[4] >= 0 and d[5] == 500


def test_margin_and_revenue_band():
    r = duckdb.sql(f"select sum(net_paise), sum(cogs_paise) from {SALES}").fetchall()[0]
    gm = 1 - r[1] / (r[0] / 1.05)          # net is tax inclusive at about 5 percent
    assert 0.20 < gm < 0.45
    avg = duckdb.sql(f"select sum(net_paise)/count(distinct (store_id, date))/100 from {SALES}").fetchall()[0][0]
    assert 15_000 < avg < 45_000


def test_festival_uplift_before_diwali():
    r = duckdb.sql(f"select date_trunc('week', date) w, sum(net_paise) n from {SALES} where store_id in (select 1) or true group by 1 order by 1").fetchall()
    vals = [x[1] for x in r]
    assert max(vals[-2:]) > 1.2 * sorted(vals)[len(vals) // 2]


def test_planted_pune_stockouts():
    ev = duckdb.sql(f"select count(*) from read_parquet('{DATA}/stockout_events.parquet') where planted").fetchall()[0][0]
    assert ev > 300
