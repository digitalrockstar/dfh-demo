"""Module 5 seed: wastage entries, a small batch and stock set for near-expiry, markdown suggestions.
Module 4 (inventory) will own batches later; these rows are a thin slice so wastage can be shown end to end."""
import random
from datetime import datetime, date, timedelta
import duckdb
from sqlalchemy import text, insert
from ..schema import metadata

NOW = datetime(2026, 10, 31, 9, 0)
START = datetime(2026, 5, 1)
MIX_STORE = [("EXPIRY", 22), ("RANCID", 6), ("PEST", 4), ("DAMAGE", 14), ("SPILL", 12), ("WEIGHT", 20), ("SAMPLE", 17), ("THEFT", 1), ("CUSTRET", 4)]
MIX_WH = [("EXPIRY", 18), ("RANCID", 10), ("PEST", 12), ("DAMAGE", 24), ("SPILL", 12), ("WEIGHT", 8), ("THEFT", 1), ("QREJECT", 15)]
MIX_F1 = [("EXPIRY", 8), ("RANCID", 5), ("PEST", 6), ("DAMAGE", 22), ("SPILL", 14), ("WEIGHT", 24), ("THEFT", 21)]


def _pick(rng, mix):
    return rng.choices([m[0] for m in mix], [m[1] for m in mix])[0]


def run(engine, seed=42, outdir="data"):
    rng = random.Random(seed + 5)
    T = metadata.tables
    with engine.connect() as c:
        skus = [dict(r._mapping) for r in c.execute(text("select id, code, name, base_uom, procurement_type, std_cost_paise, mrp_paise, shelf_life_days, popularity, bulk_sku_id, status from sku"))]
        locs = [dict(r._mapping) for r in c.execute(text("select id, type, tier, serving_wh_id from location where type in ('store','warehouse')"))]
        vend = {r[0]: r[1] for r in c.execute(text("select sku_id, min(vendor_id) from vendor_sku_cost group by 1"))}
        users = {r[0]: r[1] for r in c.execute(text("select username, id from app_user"))}
        f1 = __import__("json").loads(c.execute(text("select params from demo_finding where code='F1'")).scalar())["warehouse_id"]
        f6 = __import__("json").loads(c.execute(text("select params from demo_finding where code='F6'")).scalar())
        reasons = {r[0] for r in c.execute(text("select code from wastage_reason"))}
    pine, kiosks = list(f6["sku_ids"]), list(f6["store_ids"])
    active = [s for s in skus if s["status"] == "active" and s["procurement_type"] != "kit"]
    loose = [s for s in active if s["base_uom"] == "g"]
    pop = [max(1, s["popularity"] or 1) for s in active]
    popl = [max(1, s["popularity"] or 1) for s in loose]
    byid = {s["id"]: s for s in skus}
    stores = [l for l in locs if l["type"] == "store"]; whs = [l for l in locs if l["type"] == "warehouse"]
    cogs = {r[0]: r[1] for r in duckdb.connect().execute(f"select store_id, sum(cogs_paise) from read_parquet('{outdir}/sales_daily/**/*.parquet', hive_partitioning=true) group by 1").fetchall()}

    # ---- batches and stock: Module 4 owns them. The thin slice below is only used when inventory was not seeded ----
    with engine.connect() as c:
        have = c.execute(text("select count(*) from batch")).scalar() > 0
        brs = [dict(r._mapping) for r in c.execute(text("select id, sku_id from batch"))] if have else []
        mk = c.execute(text("select s.location_id, s.batch_id, s.qty, b.expiry_date from stock_balance s join batch b on b.id=s.batch_id join location l on l.id=s.location_id "
                            "where l.type='store' and s.qty>0 and b.expiry_date between :a and :b"), dict(a=str(NOW.date()), b=str(NOW.date() + timedelta(days=30)))).fetchall() if have else []
    batches, balrows, marks = [], [], []
    if have:
        bysku = {}
        for b in brs: bysku.setdefault(b["sku_id"], []).append(b)
        for loc, bid_, q, ex in mk:
            left = (date.fromisoformat(str(ex)[:10]) - NOW.date()).days
            marks.append(dict(location_id=loc, batch_id=bid_, suggested_pct=40.0 if left <= 7 else 30.0 if left <= 15 else 20.0, reason=f"{left} days to expiry, {q} in stock", created_at=NOW, status="open"))
    else:
        chosen = [byid[i] for i in pine if i in byid] + rng.sample([s for s in active if s["id"] not in pine and (s["shelf_life_days"] or 999) <= 365], 60)
        batches, bal, bid = [], {}, 0
        for s in chosen:
            ages = [105, 80, 70, 40, 15] if s["id"] in pine else [150, 110, 60, 20]
            for a in ages:
                bid += 1; rec = (NOW - timedelta(days=a)).date(); life = s["shelf_life_days"] or 180
                batches.append(dict(id=bid, batch_no=f"B{s['code']}-{rec:%y%m%d}", sku_id=s["id"], vendor_id=vend.get(s["bulk_sku_id"] or s["id"]) or 1, received_on=rec, mfg_date=rec - timedelta(days=10),
                                    expiry_date=rec + timedelta(days=life), mrp_paise=s["mrp_paise"], unit_cost_paise=s["std_cost_paise"], source_doc_type="seed", source_doc_id="m5"))
        bysku = {}
        for b in batches: bysku.setdefault(b["sku_id"], []).append(b)
        big = lambda s, lo, hi: rng.randint(lo, hi) * (1000 if s["base_uom"] == "g" else 1)
        for b in batches:
            s = byid[b["sku_id"]]; left = (b["expiry_date"] - NOW.date()).days
            if s["id"] in pine and s["base_uom"] != "g":
                for st in kiosks:
                    if rng.random() < (0.9 if left < 35 else 0.4): bal[(st, s["id"], b["id"])] = rng.randint(3, 12) if left > 0 else rng.randint(1, 4)
            elif left >= -3:
                for l in rng.sample(whs, 4): bal[(l["id"], s["id"], b["id"])] = big(s, 2, 12) if s["base_uom"] == "g" else rng.randint(5, 60)
                for l in rng.sample(stores, 14): bal[(l["id"], s["id"], b["id"])] = big(s, 1, 3) if s["base_uom"] == "g" else rng.randint(1, 8)
        balrows = [dict(location_id=k[0], sku_id=k[1], batch_id=k[2], qty=q, updated_at=NOW) for k, q in bal.items()]
        bexp = {b["id"]: b["expiry_date"] for b in batches}; store_ids = {l["id"] for l in stores}
        marks = []
        for (loc, sid, b), q in bal.items():
            left = (bexp[b] - NOW.date()).days
            if 0 <= left <= 30 and loc in store_ids:
                marks.append(dict(location_id=loc, batch_id=b, suggested_pct=40.0 if left <= 7 else 30.0 if left <= 15 else 20.0, reason=f"{left} days to expiry, {q} in stock", created_at=NOW, status="open"))

    # ---- wastage entries ----
    ent = []
    uid_wh, uid_sm = users.get("warehouse"), users.get("storemgr")
    boss = [users.get("finance"), users.get("ceo")]

    def mk(loc, ts, reason, sku, qty, is_wh):
        ts = min(ts, NOW - timedelta(minutes=rng.randint(30, 600)))
        s = byid[sku]; cost = round(qty / 1000 * s["std_cost_paise"]) if s["base_uom"] == "g" else qty * s["std_cost_paise"]
        bl = bysku.get(sku); b = rng.choice(bl)["id"] if bl and rng.random() < 0.5 else None
        st = "approved"; ap = rng.choice(boss)
        if cost >= 200000 and ts >= NOW - timedelta(days=7): st, ap = "pending", None
        elif rng.random() < 0.012: st = "rejected"
        ent.append(dict(ts=ts, location_id=loc, sku_id=sku, batch_id=b, qty=qty, reason=reason, cost_paise=cost, entered_by=uid_wh if loc == 1 else uid_sm if loc == 21 else None, status=st, approved_by=ap,
                        photo_ref=f"photo_{rng.randint(1000, 9999)}.jpg" if reason in ("DAMAGE", "PEST", "RANCID", "QREJECT") and rng.random() < 0.6 else None, vendor_claim=reason in ("QREJECT", "PEST", "RANCID") and rng.random() < 0.5))

    def when(is_wh, night=False):
        d = START + timedelta(days=rng.random() * 183.9)
        h = rng.choice([22, 23, 0, 1, 2, 3, 4]) if night else (rng.randint(7, 19) if is_wh else rng.randint(9, 21))
        return d.replace(hour=h, minute=rng.randint(0, 59), second=0, microsecond=0)

    for l in stores:
        n = max(8, int(cogs.get(l["id"], 2e8) * 0.0075 / 45000 * rng.uniform(0.8, 1.25)))
        for _ in range(n):
            r = _pick(rng, MIX_STORE)
            s = rng.choices(loose, popl)[0] if r in ("WEIGHT", "SPILL", "SAMPLE") else rng.choices(active, pop)[0]
            q = rng.randint(30, 600) if s["base_uom"] == "g" else rng.randint(1, 3)
            mk(l["id"], when(False), r, s["id"], q, False)
    for l in whs:
        n = 380
        for i in range(n):
            if l["id"] == f1:
                ts = when(True); copies = {5: 1, 6: 1, 7: 1, 8: 2, 9: 3, 10: 4}[ts.month]
                r = _pick(rng, MIX_F1 if ts.month >= 8 and rng.random() < 0.7 else MIX_WH)
                if r == "THEFT": ts = when(True, night=True)
                for _k in range(copies):
                    s = rng.choices(active, pop)[0]; q = rng.randint(100, 1500) if s["base_uom"] == "g" else rng.randint(1, 8)
                    mk(l["id"], ts if _k == 0 else ts.replace(day=rng.randint(1, 28), hour=rng.randint(7, 19)), r, s["id"], q, True)
            else:
                r = _pick(rng, MIX_WH); s = rng.choices(active, pop)[0]
                q = rng.randint(100, 1500) if s["base_uom"] == "g" else rng.randint(1, 8)
                mk(l["id"], when(True), r, s["id"], q, True)
    pset = [byid[i] for i in pine if i in byid and byid[i]["base_uom"] != "g"]
    for st in kiosks:
        for _ in range(rng.randint(4, 9)):
            ts = START + timedelta(days=rng.randint(84, 183), hours=rng.randint(9, 21), minutes=rng.randint(0, 59))
            s = rng.choice(pset); mk(st, min(ts, NOW - timedelta(hours=2)), "EXPIRY", s["id"], rng.randint(2, 7), False)

    assert all(e["reason"] in reasons for e in ent)
    with engine.begin() as c:
        for name, rows in (("batch", batches), ("stock_balance", balrows), ("wastage_entry", ent), ("markdown_suggestion", marks)):
            for i in range(0, len(rows), 5000): c.execute(insert(T[name]), rows[i:i + 5000])
    return dict(batches=len(batches), stock_rows=len(balrows), entries=len(ent), markdowns=len(marks))
