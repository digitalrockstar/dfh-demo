"""Module 10 seed: approval rules, a six month approval history with a few open requests, audit trail, notifications,
import history and device sync logs. Safe to run on its own: python -m dfh.seed.platform"""
import json, random
from datetime import datetime, timedelta
from sqlalchemy import text
from ..db import get_engine

NOW = datetime(2026, 10, 31, 9, 0)
LAKH = 100 * 100000


def run(eng, seed=42):
    rnd = random.Random(seed + 10)
    with eng.begin() as c:
        for t in ("approval_rule", "approval_request", "notification", "sync_log"):
            c.execute(text(f"delete from {t}"))
        c.execute(text("delete from import_job where id>2"))
        c.execute(text("delete from audit_log where table_name in ('wastage_entry','leave_request','purchase_order','approval_request','app_user')"))
        role = {r[0]: r[1] for r in c.execute(text("select code, id from role")).fetchall()}
        user = {r[0]: r[1] for r in c.execute(text("select username, id from app_user")).fetchall()}
        for dt, lo, hi, who in [("price_change", 1000, 2500, "finance"), ("price_change", 2500, None, "ceo"),
                                ("payment_release", 0, 5 * LAKH, "finance"), ("payment_release", 5 * LAKH, None, "ceo")]:
            c.execute(text("insert into approval_rule(doc_type,min_amount_paise,max_amount_paise,approver_role_id) values (:d,:l,:h,:r)"), dict(d=dt, l=lo, h=hi, r=role[who]))
        inv = c.execute(text("select i.id, i.inv_no, i.status, i.amount_minor*coalesce((select f.rate_to_inr from fx_rate f where f.currency=i.currency order by f.month desc limit 1),1.0) amt from vendor_invoice i order by i.id")).fetchall()
        paid = [r for r in inv if r[2] == "paid"]; pend = [r for r in inv if r[2] == "pending"]
        skus = [r[0] for r in c.execute(text("select id from sku where status='active' order by id limit 200")).fetchall()]
        reqs = []
        for k in range(46):
            when = NOW - timedelta(days=rnd.randint(8, 175), hours=rnd.randint(0, 9))
            if k % 3:
                r = rnd.choice(paid); doc = ("payment_release", str(r[0]), int(r[3]), "Release " + r[1])
                by = user["procurement"] if rnd.random() < .6 else user["finance"]
            else:
                s = rnd.choice(skus); bp = rnd.choice([1200, 1500, 1800, 2200, 2800, 3500])
                doc = ("price_change", f"{s}:mrp_paise:0", bp, f"Move {bp / 100:.0f}% on vendor cost change"); by = user["procurement"]
            big = (doc[0] == "payment_release" and doc[2] >= 5 * LAKH) or (doc[0] == "price_change" and doc[2] >= 2500)
            appr = user["ceo"] if big else user["finance"]
            if appr == by: appr = user["ceo"]
            st = "approved" if rnd.random() < .84 else "rejected"
            reqs.append(dict(dt=doc[0], d=doc[1], by=by, st=st, ap=appr, am=doc[2], cr=when, de=when + timedelta(hours=rnd.randint(1, 30)),
                             n=doc[3] + (" || Looks fine" if st == "approved" else " || Hold until credit note lands")))
        for r in pend[:4]:
            reqs.append(dict(dt="payment_release", d=str(r[0]), by=user["procurement"], st="pending", ap=None, am=int(r[3]), cr=NOW - timedelta(hours=rnd.randint(3, 60)), de=None, n="Release " + r[1]))
        for r in reqs:
            c.execute(text("insert into approval_request(doc_type,doc_id,requested_by,status,approver_id,amount_paise,created_at,decided_at,note) values (:dt,:d,:by,:st,:ap,:am,:cr,:de,:n)"), r)
            if r["ap"]:
                c.execute(text("insert into audit_log(ts,user_id,action,table_name,row_id,before,after) values (:t,:u,:a,'approval_request',:d,:b,:af)"),
                          dict(t=r["de"], u=r["ap"], a=("approve" if r["st"] == "approved" else "reject"), d=r["d"], b=json.dumps(dict(status="pending")), af=json.dumps(dict(status=r["st"], doc_type=r["dt"]))))
        wl = [r[0] for r in c.execute(text("select id from wastage_entry where status='approved' and cost_paise>=200000 limit 80")).fetchall()]
        lv = [r[0] for r in c.execute(text("select id from leave_request where status='approved' limit 60")).fetchall()]
        po = [r[0] for r in c.execute(text("select id from purchase_order where status!='draft' limit 50")).fetchall()]
        acts = [("approve", "wastage_entry", wl, ["warehouse", "finance", "ceo"], dict(status="pending"), dict(status="approved")),
                ("approve", "leave_request", lv, ["hr", "storemgr"], dict(status="pending"), dict(status="approved")),
                ("update", "purchase_order", po, ["procurement", "ceo"], dict(status="draft"), dict(status="approved"))]
        for a, tb, ids, who, b, af in acts:
            for i in ids:
                c.execute(text("insert into audit_log(ts,user_id,action,table_name,row_id,before,after) values (:t,:u,:a,:tb,:r,:b,:af)"),
                          dict(t=NOW - timedelta(days=rnd.randint(1, 180), hours=rnd.randint(0, 9)), u=user[rnd.choice(who)], a=a, tb=tb, r=str(i), b=json.dumps(b), af=json.dumps(af)))
        for u in ("procurement", "finance", "hr", "admin"):
            c.execute(text("insert into audit_log(ts,user_id,action,table_name,row_id,before,after) values (:t,:u,'create','app_user',:r,null,:af)"),
                      dict(t=NOW - timedelta(days=rnd.randint(60, 170)), u=user["admin"], r=str(user[u]), af=json.dumps(dict(username=u, role=u))))
        for r in c.execute(text("select id, requested_by, status, note from approval_request where status!='pending' limit 8")).fetchall():
            c.execute(text("insert into notification(user_id,channel,title,body,ref_type,ref_id,created_at,read_at) values (:u,'app',:t,:b,'approval',:i,:c,:rd)"),
                      dict(u=r[1], t=f"Your request was {r[2]}", b=r[3].split(" || ")[0], i=str(r[0]), c=NOW - timedelta(days=rnd.randint(1, 20)), rd=NOW - timedelta(days=rnd.randint(0, 1))))
        for r in c.execute(text("select id, doc_type, note from approval_request where status='pending'")).fetchall():
            c.execute(text("insert into notification(user_id,channel,title,body,ref_type,ref_id,created_at) values (:u,'app','Approval waiting',:b,'approval',:i,:c)"),
                      dict(u=user["finance"] if r[1] == "payment_release" else user["ceo"], b=r[2], i=str(r[0]), c=NOW - timedelta(hours=rnd.randint(2, 40))))
        for kind, fn, ok, er, d in [("vendor_costs", "cashew_july.csv", 38, 0, 150), ("store_minmax", "tier_a_minmax.csv", 120, 3, 110), ("sku_prices", "diwali_prices.csv", 64, 0, 40),
                                    ("vendor_costs", "dates_aug.csv", 22, 2, 75), ("store_minmax", "new_stores.csv", 25, 0, 20)]:
            rep = dict(errors=[dict(row=4 + j, code="X-%d" % j, error="Unknown SKU code") for j in range(er)]) if er else None
            c.execute(text("insert into import_job(kind,filename,status,rows_ok,rows_err,created_at,report) values (:k,:f,:s,:o,:e,:t,:r)"),
                      dict(k=kind, f=fn, s=("rejected" if er else "applied"), o=(0 if er else ok), e=er, t=NOW - timedelta(days=d), r=json.dumps(rep) if rep else None))
        devs = c.execute(text("select id, last_seen_at from device where active=1")).fetchall()
        rows = []
        for did, seen in devs:
            seen = seen if isinstance(seen, datetime) else datetime.fromisoformat(str(seen))
            t = seen - timedelta(minutes=rnd.randint(0, 40))
            for _ in range(24):
                x = rnd.random(); st = "failed" if x < .012 else "partial" if x < .04 else "ok"
                q = 0 if st == "ok" else rnd.randint(3, 40); n = rnd.randint(8, 70)
                rows.append(dict(d=did, s=t, f=t + timedelta(seconds=rnd.randint(2, 20)), p=0 if st == "failed" else n, r=rnd.randint(0, 2) if st == "partial" else 0, q=q, st=st))
                t -= timedelta(hours=3)
        for i in range(0, len(rows), 5000):
            c.execute(text("insert into sync_log(device_id,started_at,finished_at,bills_pushed,bills_rejected,queue_depth,status) values (:d,:s,:f,:p,:r,:q,:st)"), rows[i:i + 5000])
    return dict(requests=len(reqs), pending=4, sync_rows=len(rows))


if __name__ == "__main__":
    print(run(get_engine("sqlite:///data/dfh.db")))
