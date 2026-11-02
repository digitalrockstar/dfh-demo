"""POS seed: a few days of real-looking bills for the demo store so returns, day close and sync health have something to show.
Own random stream. Series blocks are reset so the first device claim starts at 1 after the seeded bills."""
import random, uuid
from datetime import datetime, timedelta
from sqlalchemy import text
from ..pos_calc import line_calc, bill_calc

NOW = datetime(2026, 10, 31, 9, 0)


def run(eng, seed=42, data_dir="data"):
    rng = random.Random(seed + 7)
    with eng.begin() as c:
        c.execute(text("update invoice_series set reserved_to=0, next_no=1"))
        u = c.execute(text("select id, scope_id from app_user where username='cashier'")).fetchone()
        store = u[1]
        devs = [r[0] for r in c.execute(text("select d.id from device d where d.store_id=:s order by d.id"), dict(s=store))]
        pre = {r[0]: r[1] for r in c.execute(text("select device_id, prefix from invoice_series"))}
        skus = [dict(r._mapping) for r in c.execute(text(
            "select s.id, s.base_uom uom, coalesce(s.mrp_paise, s.price_per_kg_paise) price, s.hsn, "
            "case when s.base_uom='g' then coalesce(t.rate_loose_pct,5.0) else coalesce(t.rate_packed_pct,5.0) end rate "
            "from sku s left join tax_rate t on t.hsn=s.hsn where s.status='active' and s.popularity is not null order by s.popularity desc limit 120"))]
        n_by = {d: 0 for d in devs}; made = 0; reasons = 0
        for day in range(13, -1, -1):
            for _ in range(rng.randint(2, 5) if day else 4):
                d = rng.choice(devs); n_by[d] += 1
                when = (NOW - timedelta(days=day)).replace(hour=rng.randint(10, 20), minute=rng.randint(0, 59), second=0)
                lines = []
                for _ in range(rng.randint(1, 4)):
                    s = rng.choice(skus)
                    q = rng.choice([100, 250, 500, 750, 1000]) if s["uom"] == "g" else rng.randint(1, 3)
                    g, net, tax = line_calc(s["uom"], s["price"], q, 0, s["rate"])
                    lines.append(dict(sku=s, q=q, gross=g, discount=0, net=net, tax=tax))
                t = bill_calc(lines); sid = str(uuid.UUID(int=rng.getrandbits(128)))
                c.execute(text("insert into sale(id, store_id, device_id, invoice_no, business_date, created_at_device, received_at, cashier_id, customer_id, gross_paise, discount_paise, tax_paise, net_paise, round_off_paise, status, void_reason, price_list_id, idem_key, currency) "
                               "values (:id,:st,:dv,:inv,:bd,:cd,:rc,:cu,null,:g,0,:tx,:nt,:ro,'paid',null,null,:ik,'INR')"),
                          dict(id=sid, st=store, dv=d, inv=f"{pre[d]}{n_by[d]:05d}", bd=when.date(), cd=when, rc=when + timedelta(minutes=1), cu=u[0], g=t["gross"], tx=t["tax"], nt=t["total"], ro=t["round_off"], ik=f"seed-{sid}"))
                for l in lines:
                    c.execute(text("insert into sale_line(sale_id, sku_id, batch_id, qty, unit_price_paise, discount_paise, tax_rate, tax_paise, net_paise, hsn) values (:s,:k,null,:q,:p,0,:r,:t,:n,:h)"),
                              dict(s=sid, k=l["sku"]["id"], q=l["q"], p=l["sku"]["price"], r=l["sku"]["rate"], t=l["tax"], n=l["net"], h=l["sku"]["hsn"]))
                left, mode = t["total"], rng.choices(["cash", "upi", "card"], [.45, .4, .15])[0]
                if mode == "cash" and t["total"] > 100000 and rng.random() < .4:
                    c.execute(text("insert into payment(sale_id, mode, amount_paise, ref, status) values (:s,'cash',:a,null,'ok')"), dict(s=sid, a=50000)); left -= 50000; mode = "upi"
                c.execute(text("insert into payment(sale_id, mode, amount_paise, ref, status) values (:s,:m,:a,null,'ok')"), dict(s=sid, m=mode, a=left)); made += 1
        for d in devs:
            c.execute(text("update invoice_series set reserved_to=:r, next_no=:n where device_id=:d"), dict(r=n_by[d], n=n_by[d] + 1, d=d))
    return {"store_id": store, "bills": made, "devices": n_by}
