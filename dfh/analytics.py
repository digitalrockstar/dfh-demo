"""Read-side analytics: DuckDB over the Parquet sales history, joined to masters loaded from the app database."""
import threading
from datetime import date, timedelta
import duckdb, pyarrow as pa
from sqlalchemy import text

NOW = None


def _tbl(rows, cols):
    return pa.table({c: [r[i] for r in rows] for i, c in enumerate(cols)})


class Analytics:
    def __init__(self, engine, data_dir="data"):
        self.lock = threading.Lock()
        c = self.con = duckdb.connect()
        with engine.connect() as e:
            st = e.execute(text("select id, code, name, city, region, tier, format, state, country, serving_wh_id from location where type='store'")).fetchall()
            sk = e.execute(text("select s.id, s.name, ca.code, ca.name, s.procurement_type, coalesce(t.rate_packed_pct, 5.0) from sku s join product p on p.id=s.product_id "
                                "join category ca on ca.id=p.category_id left join tax_rate t on t.hsn=s.hsn")).fetchall()
            self.festivals = [dict(name=r[0], peak=str(r[1])[:10]) for r in e.execute(text("select name, peak_date from festival_calendar order by peak_date")).fetchall()]
        c.register("t_store", _tbl(st, ["id", "code", "name", "city", "region", "tier", "format", "state", "country", "serving_wh_id"]))
        c.register("t_sku", _tbl(sk, ["id", "name", "cat", "cat_name", "ptype", "rate"]))
        c.execute("create table dim_store as select * from t_store")
        c.execute("create table dim_sku as select * from t_sku")
        c.execute(f"create view sales as select * from read_parquet('{data_dir}/sales_daily/*/*.parquet', hive_partitioning=true)")
        c.execute("create table stockouts as select * from read_parquet('%s/stockout_events.parquet')" % data_dir)
        c.execute("create table agg as select s.date, s.store_id, k.cat, sum(s.net_paise) net, sum(s.net_paise/(1+k.rate/100.0)) net_ex, "
                  "sum(s.cogs_paise) cogs from sales s join dim_sku k on k.id=s.sku_id group by 1,2,3")
        self.min_date, self.max_date = c.execute("select min(date), max(date) from agg").fetchone()
        self.cats = dict(c.execute("select distinct cat, cat_name from dim_sku").fetchall())

    def q(self, sql, params=()):
        with self.lock:
            return self.con.execute(sql, list(params)).fetchall()

    @staticmethod
    def _where(region=None, tier=None, city=None, store_ids=None, fmt=None):
        w, p = [], []
        if region: w.append("d.region = ?"); p.append(region)
        if tier: w.append("d.tier = ?"); p.append(tier)
        if city: w.append("d.city = ?"); p.append(city)
        if fmt: w.append("d.format = ?"); p.append(fmt)
        if store_ids is not None:
            w.append("d.id in (%s)" % (",".join(str(int(x)) for x in store_ids) or "-1"))
        return (" and " + " and ".join(w)) if w else "", p

    def period(self, days):
        end = self.max_date; start = max(self.min_date, end - timedelta(days=days - 1))
        n = (end - start).days + 1
        pe = start - timedelta(days=1); ps = pe - timedelta(days=n - 1)
        return start, end, ps, pe, (ps >= self.min_date)

    def _sum(self, s, e, f):
        w, p = self._where(**f)
        r = self.q("select coalesce(sum(a.net),0), coalesce(sum(a.net_ex),0), coalesce(sum(a.cogs),0), count(distinct (a.store_id, a.date)), count(distinct a.store_id) "
                   "from agg a join dim_store d on d.id=a.store_id where a.date between ? and ?" + w, [s, e] + p)[0]
        net, ex, cogs, sd, st = r
        return dict(net=int(net), gm=(1 - cogs / ex) if ex else 0, per_store_day=(net / sd) if sd else 0, store_days=sd, stores=st)

    def stockouts(self, s, e, f):
        w, p = self._where(**f)
        r = self.q("select count(*), count(distinct o.store_id), coalesce(sum(date_diff('day', greatest(o.start_date, ?), least(o.end_date, ?)) + 1), 0) "
                   "from stockouts o join dim_store d on d.id=o.store_id where o.start_date <= ? and o.end_date >= ?" + w, [s, e, e, s] + p)[0]
        return dict(events=r[0], stores=r[1], days=int(r[2]))

    def summary(self, days=30, **f):
        s, e, ps, pe, has_prev = self.period(days)
        cur = self._sum(s, e, f); prev = self._sum(ps, pe, f) if has_prev else None
        d = lambda k: ((cur[k] / prev[k] - 1) if prev and prev[k] else None)
        return dict(start=str(s), end=str(e), days=(e - s).days + 1, current=cur, previous=prev,
                    delta=dict(net=d("net"), per_store_day=d("per_store_day"), gm=(cur["gm"] - prev["gm"]) if prev else None),
                    stockouts=self.stockouts(s, e, f), festivals=self.festivals)

    def trend(self, days=30, **f):
        s, e, *_ = self.period(days); w, p = self._where(**f)
        rows = self.q("select a.date, sum(a.net) from agg a join dim_store d on d.id=a.store_id where a.date between ? and ?" + w + " group by 1 order by 1", [s, e] + p)
        vals = [int(r[1]) for r in rows]
        avg = [sum(vals[max(0, i - 6):i + 1]) / len(vals[max(0, i - 6):i + 1]) for i in range(len(vals))]
        return [dict(date=str(r[0]), net=v, avg7=a) for r, v, a in zip(rows, vals, avg)]

    def category_mix(self, days=30, **f):
        s, e, *_ = self.period(days); w, p = self._where(**f)
        rows = self.q("select a.cat, sum(a.net), sum(a.net_ex), sum(a.cogs) from agg a join dim_store d on d.id=a.store_id where a.date between ? and ?" + w + " group by 1 order by 2 desc", [s, e] + p)
        tot = sum(r[1] for r in rows) or 1
        return [dict(code=r[0], name=self.cats[r[0]], net=int(r[1]), share=r[1] / tot, gm=(1 - r[3] / r[2]) if r[2] else 0) for r in rows]

    def league(self, days=30, order="top", limit=10, **f):
        s, e, ps, pe, has_prev = self.period(days); w, p = self._where(**f)
        base = "select d.id, d.code, d.name, d.city, d.region, d.tier, sum(a.net), sum(a.net_ex), sum(a.cogs), count(distinct a.date) from agg a join dim_store d on d.id=a.store_id where a.date between ? and ?" + w + " group by all"
        cur = self.q(base, [s, e] + p)
        prev = {r[0]: r[6] / max(1, r[9]) for r in self.q(base, [ps, pe] + p)} if has_prev else {}
        n = (e - s).days + 1; out = []
        for r in cur:
            pd_ = r[6] / max(1, r[9]); pv = prev.get(r[0])
            out.append(dict(id=r[0], code=r[1], name=r[2], city=r[3], region=r[4], tier=r[5], net=int(r[6]), per_day=pd_, gm=(1 - r[8] / r[7]) if r[7] else 0,
                            vs_prev=(pd_ / pv - 1) if pv else None, new=r[9] < 0.8 * n))
        pool = [x for x in out if not x["new"]] if order == "bottom" else out
        pool.sort(key=lambda x: x["per_day"], reverse=(order == "top"))
        return dict(total=len(out), rows=pool[:limit])

    def stockout_hotspots(self, days=30, **f):
        s, e, *_ = self.period(days); w, p = self._where(**f)
        rows = self.q("select d.city, count(*) ev, count(distinct o.store_id) st, max(c.n) stores_in_city from stockouts o join dim_store d on d.id=o.store_id "
                      "join (select city, count(*) n from dim_store group by 1) c on c.city=d.city where o.start_date <= ? and o.end_date >= ?" + w + " group by 1", [e, s] + p)
        per = sorted(((r[1] / r[3], r) for r in rows), reverse=True)
        if not per: return []
        med = sorted(x[0] for x in per)[len(per) // 2] or 1
        out = []
        for ratio, r in per[:3]:
            if ratio / med >= 2.0:
                top = self.q("select k.name, count(*) c from stockouts o join dim_store d on d.id=o.store_id join dim_sku k on k.id=o.sku_id where d.city=? and o.start_date <= ? and o.end_date >= ? group by 1 order by 2 desc limit 3", [r[0], e, s])
                out.append(dict(city=r[0], events=r[1], stores=r[3], ratio=ratio / med, top_skus=[t[0] for t in top]))
        return out

    def sales_drops(self, **f):
        e = self.max_date; w, p = self._where(**f)
        rows = self.q("select d.id, d.name, d.city, sum(case when a.date > ? then a.net else 0 end)/7.0, sum(case when a.date <= ? and a.date > ? then a.net else 0 end)/28.0 "
                      "from agg a join dim_store d on d.id=a.store_id where a.date > ?" + w + " group by all having sum(case when a.date <= ? and a.date > ? then a.net else 0 end) > 0",
                      [e - timedelta(days=7), e - timedelta(days=7), e - timedelta(days=35), e - timedelta(days=35)] + p + [e - timedelta(days=7), e - timedelta(days=35)])
        bad = sorted(((r[3] / r[4], r) for r in rows if r[4] > 0 and r[3] / r[4] < 0.65))[:5]
        return [dict(id=r[0], name=r[1], city=r[2], ratio=ra) for ra, r in bad]

    def sku_sales(self, sku_id, days=30):
        s = self.max_date - timedelta(days=days - 1)
        r = self.q("select coalesce(sum(qty),0), coalesce(sum(net_paise),0), count(distinct store_id) from sales where sku_id=? and date >= ?", [sku_id, s])[0]
        wk = self.q("select date_trunc('week', date), sum(net_paise) from sales where sku_id=? group by 1 order by 1", [sku_id])
        return dict(days=days, qty=int(r[0]), net=int(r[1]), stores=r[2], weekly=[dict(week=str(x[0])[:10], net=int(x[1])) for x in wk])
