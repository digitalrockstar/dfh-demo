"""Store assortments and daily sales history (store x SKU x day) written to Parquet.
Quantities are in the SKU base unit: grams for loose SKUs, units for packed SKUs.
Net sales are tax inclusive, in INR equivalent paise."""
import os
from datetime import date, timedelta
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import text, insert
from ..schema import metadata
from .catalog import SHARE

TARGET_PAISE = 3_000_000          # Rs 30,000 per average store-day, a calibration assumption
SENS = {"NDF": 1.2, "DAT": 1.5, "EXC": 1.5, "BER": .6, "SED": .3, "GFT": 3.0, "CHO": 2.0, "SPC": .5}
MONTH_BASE = {5: .93, 6: .90, 7: .90, 8: .95, 9: 1.0, 10: 1.06}
DOW = np.array([.85, .85, .88, .92, 1.0, 1.25, 1.25]); DOW = DOW / DOW.mean()
ASSORT = {"A": 320, "B": 200, "C": 110}
TIER_MULT = {"A": 1.35, "B": 1.0, "C": .65}
CATS = list(SENS)


def run(engine, months=6, seed=42, outdir="data"):
    rng = np.random.default_rng(seed)
    end = date(2026, 10, 31)
    start = date(2026, 5, 1) if months == 6 else end - timedelta(days=int(months * 30.4) - 1)
    nd = (end - start).days + 1
    days = [start + timedelta(days=i) for i in range(nd)]
    with engine.connect() as c:
        sk = c.execute(text("select s.id, ca.code, s.popularity, s.base_uom, s.price_per_kg_paise, s.mrp_paise, s.std_cost_paise, s.name "
                            "from sku s join product p on p.id=s.product_id join category ca on ca.id=p.category_id order by s.id")).fetchall()
        st = c.execute(text("select id, code, region, tier, opened_on from location where type='store' order by code")).fetchall()
        fest = c.execute(text("select name, peak_date, ramp_days, uplift, regions from festival_calendar")).fetchall()
        f3 = c.execute(text("select params from demo_finding where code='F3'")).scalar()
    import json
    iso = lambda x: x if (x is None or isinstance(x, date)) else date.fromisoformat(str(x)[:10])
    st = [(a, b, c_, d_, iso(e)) for a, b, c_, d_, e in st]
    fest = [(a, iso(b), c_, d_, e) for a, b, c_, d_, e in fest]
    f3 = json.loads(f3) if isinstance(f3, str) else f3
    n = len(sk)
    sku_id = np.array([r[0] for r in sk]); catix = np.array([CATS.index(r[1]) for r in sk]); pop = np.array([r[2] for r in sk])
    loose = np.array([r[3] == "g" for r in sk])
    price = np.array([(r[4] / 1000.0) if r[3] == "g" else r[5] for r in sk], dtype=float)
    cost = np.array([(r[6] / 1000.0) if r[3] == "g" else r[6] for r in sk], dtype=float)
    rev = np.zeros(n)
    for ci, cat in enumerate(CATS):
        m = catix == ci
        rev[m] = SHARE[cat] * pop[m] / pop[m].sum() * TARGET_PAISE
    rate = rev / price                                  # base units per average store-day, full assortment
    logpop = np.log(pop + 1e-9)

    # festival and season factors per category and day, by region group
    def catF(region_ok):
        F = np.ones((len(CATS), nd))
        mb = np.array([MONTH_BASE[d.month] for d in days])
        inten = np.zeros(nd)
        for nm, peak, ramp, up, regs in fest:
            if regs not in region_ok:
                continue
            delta = np.array([(d - peak).days for d in days], dtype=float)
            x = np.where(delta <= 0, np.exp(-(delta / ramp) ** 2), np.exp(-(delta / (ramp * .5)) ** 2))
            inten += up * x
        for ci, cat in enumerate(CATS):
            F[ci] = mb * (1 + inten * SENS[cat])
        return F
    F_IN, F_GCC = catF(("ALL", "IN")), catF(("ALL",))
    dow = np.array([DOW[d.weekday()] for d in days])

    # pass 1: assortments and calibration
    plans = []
    for sid, code, region, tier, opened in st:
        k = int(ASSORT[tier] * rng.uniform(.9, 1.1))
        score = .6 * logpop + rng.gumbel(size=n)
        idx = np.sort(np.argpartition(-score, k)[:k])
        scale = rng.lognormal(0, .35) * TIER_MULT[tier] * (1.05 if region == "GCC" else 1.0)
        plans.append((sid, code, region, tier, opened, idx, scale))
    k_cal = TARGET_PAISE / np.mean([rev[p[5]].sum() * p[6] for p in plans])

    # store_assortment rows
    rows = []
    for sid, code, region, tier, opened, idx, scale in plans:
        lam = rate[idx] * scale * k_cal
        mn = np.maximum(1, np.round(lam * 3)).astype(int); mx = np.maximum(mn + 1, np.round(lam * 10)).astype(int)
        lf = max(opened, date(2012, 1, 1)) if opened else start
        rows += [dict(store_id=sid, sku_id=int(sku_id[i]), min_qty=int(a), max_qty=int(b), listed_from=lf) for i, a, b in zip(idx, mn, mx)]
    with engine.begin() as c:
        for i in range(0, len(rows), 20000):
            c.execute(insert(metadata.tables["store_assortment"]), rows[i:i + 20000])

    # pass 2: daily sales
    base = os.path.join(outdir, "sales_daily")
    os.makedirs(base, exist_ok=True)
    stock_ev, buf, cur_city, total_rows, total_net, store_days = [], [], None, 0, 0.0, 0
    hot_idx = {int(x) for x in f3["sku_ids"]}; pune = set(f3["store_ids"]); f3_start = (date.fromisoformat(f3["start"]) - start).days
    drift = np.array([1 + .004 * ((d.year - 2026) * 12 + d.month - 5) for d in days])
    dts = (np.datetime64(start) + np.arange(nd).astype("timedelta64[D]"))

    def flush(city):
        if not buf:
            return
        cols = [np.concatenate(x) for x in zip(*buf)]
        t = pa.table({"date": pa.array(dts[cols[0]], type=pa.date32()), "store_id": pa.array(cols[1], type=pa.int16()),
                      "sku_id": pa.array(cols[2], type=pa.int16()), "qty": pa.array(cols[3], type=pa.int32()),
                      "net_paise": pa.array(cols[4], type=pa.int32()), "cogs_paise": pa.array(cols[5], type=pa.int32())})
        d = os.path.join(base, f"city={city}"); os.makedirs(d, exist_ok=True)
        pq.write_table(t, os.path.join(d, "part-0.parquet"), compression="zstd")
        buf.clear()

    for sid, code, region, tier, opened, idx, scale in plans:
        city = code.split("-")[1]
        if cur_city and city != cur_city:
            flush(cur_city)
        cur_city = city
        F = F_GCC if region == "GCC" else F_IN
        open_i = (opened - start).days if opened and opened > start else 0
        ramp = np.where(np.arange(nd) < open_i, 0.0, .5 + .5 * np.minimum(1, (np.arange(nd) - open_i) / 60.0))
        noise = rng.lognormal(0, .18, size=nd)
        lam = rate[idx, None] * scale * k_cal * dow[None, :] * F[catix[idx]] * noise[None, :] * ramp[None, :]
        isl = loose[idx][:, None]
        q = np.where(isl, rng.poisson(lam / 100.0) * 100, rng.poisson(lam)).astype(np.int64)
        # stockouts
        for _ in range(rng.poisson(3)):
            r, s0, ln = rng.integers(len(idx)), rng.integers(nd), rng.integers(1, 6)
            q[r, s0:s0 + ln] = 0
            stock_ev.append((sid, int(sku_id[idx[r]]), days[s0], days[min(nd - 1, s0 + ln - 1)], False))
        if sid in pune:
            for r, i in enumerate(idx):
                if int(sku_id[i]) in hot_idx:
                    d0 = f3_start
                    while d0 < nd:
                        ln = int(rng.integers(2, 6))
                        if rng.random() < .55:
                            q[r, d0:d0 + ln] = 0
                            stock_ev.append((sid, int(sku_id[i]), days[d0], days[min(nd - 1, d0 + ln - 1)], True))
                        d0 += ln + int(rng.integers(1, 4))
        promo = 1 - rng.choice([0, .02, .05, .08], p=[.55, .25, .15, .05], size=nd)
        net = np.clip(q * price[idx, None] * promo[None, :], 0, 2**31 - 1)
        cg = np.clip(q * cost[idx, None] * drift[None, :], 0, 2**31 - 1)
        r_, d_ = np.nonzero(q)
        buf.append((d_, np.full(len(r_), sid), sku_id[idx[r_]], q[r_, d_], net[r_, d_].astype(np.int64), cg[r_, d_].astype(np.int64)))
        total_rows += len(r_); total_net += net.sum(); store_days += int((ramp > 0).sum())
    flush(cur_city)
    ev = pa.table({"store_id": pa.array([e[0] for e in stock_ev], pa.int16()), "sku_id": pa.array([e[1] for e in stock_ev], pa.int16()),
                   "start_date": pa.array([e[2] for e in stock_ev], pa.date32()), "end_date": pa.array([e[3] for e in stock_ev], pa.date32()),
                   "planted": pa.array([e[4] for e in stock_ev], pa.bool_())})
    pq.write_table(ev, os.path.join(outdir, "stockout_events.parquet"))
    return dict(rows=total_rows, avg_net_per_store_day_inr=round(total_net / store_days / 100), start=str(start), end=str(end),
                stockout_events=len(stock_ev), assortment_rows=len(rows))
