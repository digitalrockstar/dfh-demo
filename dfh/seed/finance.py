"""Module 7 seed: chart of accounts, store tender split, day close, gateway settlements, reconciliation exceptions, input tax credit
against GSTR-2B, ledger journals and period locks.
Sales, cost and tax come from the sales history, so every figure ties to the Control Tower. Tender split (cash, UPI, card) is modelled per
store because POS holds only demo bills. Vendor invoices come from Module 3: this seed attributes them to an entity and splits GST for
domestic invoices (rates are assumed, 5 percent for most vendors and 18 percent for a few). Imports carry no input credit here (bill of
entry is out of scope). Planted: F4 (Borivali weekend cash shortage), F5 (three stores that have not closed the last two days),
F8 (Karnataka September books against GSTR-2B)."""
import json, random
from datetime import date, datetime, timedelta, time
import numpy as np, duckdb, pyarrow as pa
from sqlalchemy import text, insert
from ..schema import metadata

START, END = date(2026, 5, 1), date(2026, 10, 31)
D = (END - START).days + 1
CARD_FEE = 0.018
PERIODS = [f"2026-{m:02d}" for m in range(5, 11)]
ACCOUNTS = [("1000", "Cash in hand", "asset"), ("1010", "UPI clearing", "asset"), ("1020", "Card clearing", "asset"), ("1030", "Bank", "asset"),
            ("1050", "Settlement suspense", "asset"), ("1100", "Inventory", "asset"), ("1200", "Input GST credit", "asset"),
            ("2000", "Trade payables", "liability"), ("2100", "Output GST 5 percent", "liability"), ("2101", "Output GST 18 percent", "liability"),
            ("4000", "Sales at 5 percent GST", "income"), ("4001", "Sales at 18 percent GST", "income"), ("5000", "Cost of goods sold", "expense"),
            ("5100", "Wastage and shrink", "expense"), ("5200", "Gateway fees", "expense"), ("5300", "Cash short and over", "expense"),
            ("5400", "Settlement write-offs", "expense"), ("5500", "FX gain and loss", "expense")]
jl = lambda x: json.loads(x) if isinstance(x, str) else x


def run(engine, seed=42, outdir="data"):
    rng = np.random.default_rng(seed + 11); pr = random.Random(seed + 11)
    T = metadata.tables
    days = [START + timedelta(days=i) for i in range(D)]
    with engine.connect() as c:
        st = c.execute(text("select id, entity_id, region from location where type='store' order by id")).fetchall()
        ents = {r[0]: dict(id=r[0], code=r[1], india=r[2] == "India") for r in c.execute(text("select id, code, country from legal_entity"))}
        rates = c.execute(text("select s.id, coalesce(t.rate_packed_pct, 5.0) from sku s left join tax_rate t on t.hsn=s.hsn")).fetchall()
        fx = {(r[0], str(r[1])[:7]): float(r[2]) for r in c.execute(text("select currency, month, rate_to_inr from fx_rate"))}
        fnd = {r[0]: jl(r[1]) for r in c.execute(text("select code, params from demo_finding"))}
        fin = c.execute(text("select id from app_user where username='finance'")).scalar()
        wast = c.execute(text("select l.entity_id, substr(cast(w.ts as text),1,7), sum(w.cost_paise) from wastage_entry w join location l on l.id=w.location_id where w.status='approved' group by 1,2")).fetchall()
        have_dc = {(r[0], str(r[1])[:10]) for r in c.execute(text("select store_id, business_date from day_close"))}
        invs = [dict(r._mapping) for r in c.execute(text(
            "select i.id, i.vendor_id, i.inv_no, i.inv_date, i.amount_minor, i.currency, i.status, v.type vtype, v.gstin, l.entity_id from vendor_invoice i "
            "join vendor v on v.id=i.vendor_id left join purchase_order p on p.id=i.po_id left join location l on l.id=p.dest_location_id order by i.id"))]
        pays = [dict(r._mapping) for r in c.execute(text("select id, invoice_id, paid_on, amount_minor, fx_rate from vendor_payment order by id"))]
        dom_v = [dict(r._mapping) for r in c.execute(text("select id, gstin from vendor where type='domestic' order by id"))]
    for x in invs: x["inv_date"] = date.fromisoformat(str(x["inv_date"])[:10])
    # ---- sales, cost and tax per store and day ----
    con = duckdb.connect(); con.register("rt", pa.table({"id": [r[0] for r in rates], "cls": [18 if r[1] >= 18 else 5 for r in rates]}))
    r = con.execute(f"select s.store_id sid, s.date d, rt.cls cls, sum(s.net_paise)::bigint net, sum(s.cogs_paise)::bigint cogs from read_parquet('{outdir}/sales_daily/*/*.parquet', hive_partitioning=true) s join rt on rt.id=s.sku_id group by 1,2,3").fetchnumpy()
    g = lambda k: np.ma.getdata(r[k])
    sid = np.array([x[0] for x in st]); S = len(sid); ent_of = np.array([x[1] for x in st]); india = np.array([x[2] != "GCC" for x in st])
    row = np.searchsorted(sid, g("sid")); col = (g("d").astype("datetime64[D]") - np.datetime64(START)).astype(int)
    net = {5: np.zeros((S, D), np.int64), 18: np.zeros((S, D), np.int64)}; cogs = np.zeros((S, D), np.int64)
    for cl in (5, 18):
        m = g("cls") == cl; np.add.at(net[cl], (row[m], col[m]), g("net")[m])
    np.add.at(cogs, (row, col), g("cogs")); tot = net[5] + net[18]; has = tot > 0
    # ---- tender split ----
    cs = np.where(india, rng.uniform(.18, .38, S), rng.uniform(.08, .2, S)); us = np.where(india, rng.uniform(.4, .6, S), 0.0)
    cash = np.round(tot * np.clip(cs[:, None] * rng.lognormal(0, .08, (S, D)), .03, .6)).astype(np.int64)
    upi = np.minimum(np.round(tot * us[:, None] * np.clip(rng.lognormal(0, .05, (S, D)), .8, 1.2)).astype(np.int64), tot - cash)
    card = tot - cash - upi
    # ---- day close ----
    opening = rng.integers(30, 81, S) * 10000
    u = rng.random((S, D)); sg = np.where(rng.random((S, D)) < .55, -1, 1)
    var = np.where(u < .55, 0, np.where(u > .97, sg * rng.integers(100, 600, (S, D)) * 100, sg * rng.integers(1, 51, (S, D)) * 100)).astype(np.int64)
    ridx = {int(s): i for i, s in enumerate(sid)}; f4 = ridx[fnd["F4"]["store_id"]]
    wd = np.array([d.weekday() for d in days]); f4cols = [j for j in range(D) if days[j] >= date(2026, 7, 4) and wd[j] >= 5]
    for j in f4cols:
        if rng.random() < .85: var[f4, j] = -int(rng.integers(1800, 6500)) * 100
    stale = [ridx[s] for s in fnd["F5"]["store_ids"]]
    others = [i for i in rng.permutation(S).tolist() if i != f4 and i not in stale][:22]
    for i in others:
        for j in rng.choice(np.arange(90, D), int(rng.integers(1, 4)), replace=False): var[i, j] = -int(rng.integers(1000, 3500)) * 100
    openm = np.zeros((S, D), bool)
    for i in stale: openm[i, D - 2:] = True
    var = np.where(openm | ~has, 0, var)
    dc = []
    for i, j in zip(*[a.tolist() for a in np.nonzero(has)]):
        if (int(sid[i]), str(days[j])) in have_dc: continue
        o = bool(openm[i, j]); e = int(opening[i] + cash[i, j]); v = int(var[i, j])
        dc.append(dict(store_id=int(sid[i]), business_date=days[j], device_id=None, opened_by=None, closed_by=None, opening_cash_paise=int(opening[i]), expected_cash_paise=e,
                       counted_cash_paise=None if o else e + v, variance_paise=None if o else v, status="open" if o else ("variance" if abs(v) > 10000 else "closed"),
                       closed_at=None if o else datetime.combine(days[j], time(22, 30))))
    # ---- settlements and reconciliation items ----
    def sdate(d, lag):
        s = d + timedelta(days=lag)
        return s + timedelta(days={5: 2, 6: 1}.get(s.weekday(), 0)) if lag == 2 else s
    stl, rec, sagg = [], [], {}
    djs = {1: [sdate(d, 1) for d in days], 2: [sdate(d, 2) for d in days]}
    for mode, arr, rate, lag in (("UPI", upi, 0.0, 1), ("CARD", card, CARD_FEE, 2)):
        ii, jj = [a.tolist() for a in np.nonzero(arr)]; n = len(ii); ex = arr[np.nonzero(arr)].tolist()
        shorts = (rng.random(n) < .0016).tolist(); held = ((rng.random(n) < .0006) & (mode == "CARD")).tolist(); pc = rng.uniform(.01, .08, n).tolist()
        for k in range(n):
            i, j, e = ii[k], jj[k], ex[k]; s = djs[lag][j]; f = int(round(e * rate)); sh = int(round(e * pc[k]))
            if s > END: stt, rc, f = "in_transit", 0, 0
            elif held[k] and not shorts[k]: stt, rc = "held", 0
            elif shorts[k]: stt, rc = "short", e - f - sh
            else: stt, rc = "settled", e - f
            ref = f"{mode}-{int(sid[i])}-{days[j]:%y%m%d}"
            stl.append(dict(store_id=int(sid[i]), mode=mode, settle_date=s, business_date=days[j], expected_paise=e, received_paise=rc, fee_paise=f, ref=ref, status=stt))
            if stt != "in_transit":
                a = sagg.setdefault((int(ent_of[i]), s), [0, 0, 0, 0, 0]); a[0 if mode == "UPI" else 1] += e; a[2] += rc; a[3] += f; a[4] += e - f - rc
            if stt in ("short", "held"):
                rec.append(dict(source="settlement", source_ref=ref, store_id=int(sid[i]), business_date=days[j], amount_paise=-(e - f - rc), ent=int(ent_of[i])))
    for i, j in zip(*[a.tolist() for a in np.nonzero(var <= -100000)]):
        rec.append(dict(source="day_close", source_ref=f"DC-{int(sid[i])}-{days[j]:%y%m%d}", store_id=int(sid[i]), business_date=days[j], amount_paise=int(var[i, j]), ent=int(ent_of[i])))
    adj = {}
    for x in rec:
        old = x["business_date"] < date(2026, 10, 1); age = (END - x["business_date"]).days; x["matched_to"] = None; x["note"] = None; x["resolved_by"] = None; x["resolved_at"] = None
        if x["source"] == "settlement": st_ = "open" if (not old and (age <= 10 or pr.random() < .25)) else ("wrote_off" if pr.random() < .2 else "matched")
        else: st_ = "open" if not old else ("wrote_off" if pr.random() < .7 else "matched")
        x["status"] = "wrote_off" if st_ == "wrote_off" else st_
        if st_ != "open":
            ra = min(END, x["business_date"] + timedelta(days=pr.randint(3, 9))); x.update(resolved_by=fin, resolved_at=datetime.combine(ra, time(15, 0)))
            if x["source"] == "settlement":
                x["note"] = "Gateway adjusted the shortfall in a later settlement" if st_ == "matched" else "Small gateway adjustment, written off"; x["matched_to"] = "ADJ-" + x["source_ref"] if st_ == "matched" else None
                adj.setdefault((x["ent"], ra, st_), 0); adj[(x["ent"], ra, st_)] += -x["amount_paise"]
            else: x["note"] = "Recovered from the cashier" if st_ == "matched" else "Written off by the store manager"
        x["status"] = {"wrote_off": "written_off"}.get(x["status"], x["status"])
    for x in rec: x.pop("ent")
    # ---- vendor invoices: entity and GST split ----
    vrate = {v["id"]: (18 if pr.random() < .15 else 5) for v in dom_v}
    ka = fnd["F8"]["entity_id"]; per = fnd["F8"]["period"]
    sep = [x for x in invs if x["vtype"] == "domestic" and str(x["inv_date"])[:7] == per]
    mine = [x for x in sep if x["entity_id"] == ka]
    for x in sep:
        if len(mine) >= 9: break
        if x["entity_id"] != ka: x["entity_id"] = ka; mine.append(x)
    for x in invs:
        if x["entity_id"] is None: x["entity_id"] = 1
        if x["vtype"] == "domestic":
            rt_ = vrate[x["vendor_id"]]; x["taxable"] = int(round(x["amount_minor"] / (1 + rt_ / 100))); x["tax"] = x["amount_minor"] - x["taxable"]
        else: x["taxable"], x["tax"] = x["amount_minor"], 0
        x["fx"] = fx.get((x["currency"], str(x["inv_date"])[:7]), 1.0); x["inr_tax"] = int(round(x["tax"] * x["fx"])); x["inr_base"] = int(round(x["taxable"] * x["fx"]))
    ibyid = {x["id"]: x for x in invs}
    g2b = {}
    for x in invs:
        if x["tax"] > 0 and str(x["inv_date"])[:7] < "2026-10":
            g2b[x["id"]] = dict(entity_id=x["entity_id"], period=str(x["inv_date"])[:7], supplier_gstin=x["gstin"], inv_no=x["inv_no"], taxable_paise=x["taxable"], tax_paise=x["tax"], matched_invoice_id=x["id"], status="matched")
    cands = [x for x in mine if x["tax"] > 0]; pr.shuffle(cands)
    assert len(cands) >= 7, "Karnataka September needs domestic invoices for F8"
    for x in cands[:4]: g2b.pop(x["id"])
    for x in cands[4:6]: g2b[x["id"]]["tax_paise"] = int(round(x["tax"] * .6)); g2b[x["id"]]["status"] = "mismatch"
    extra = []
    for n in range(3):
        v = pr.choice(dom_v); tx = pr.randint(300000, 800000) * 100
        extra.append(dict(entity_id=ka, period=per, supplier_gstin=v["gstin"], inv_no=f"UNB/{per[2:4]}{per[5:]}/{9000 + n}", taxable_paise=tx, tax_paise=int(tx * .05), matched_invoice_id=None, status="unbooked"))
    g2b_rows = list(g2b.values()) + extra
    # ---- journals ----
    jvs, lines = [], []

    def jv(kind, ent, d, ref, narr, ls):
        ls = [l for l in ls if l[1] or l[2]]
        if not ls: return
        jid = len(jvs) + 1
        jvs.append(dict(id=jid, jv_no=f"{ents[ent]['code']}/{kind}/{ref}", date=d, entity_id=ent, source_doc_type=kind.lower(), source_doc_id=str(ref), narration=narr))
        lines.extend(dict(jv_id=jid, account_code=a, debit_paise=int(dr), credit_paise=int(cr), location_id=None) for a, dr, cr in ls)
    ex_ = {cl: np.round(net[cl] / (1 + cl / 100)).astype(np.int64) for cl in (5, 18)}; tx_ = {cl: net[cl] - ex_[cl] for cl in (5, 18)}
    for e in ents:
        m = ent_of == e
        if not m.any(): continue
        A = lambda a: a[m].sum(axis=0)
        cs_, up_, cd_, e5, t5, e18, t18, cg, vr = map(A, (cash, upi, card, ex_[5], tx_[5], ex_[18], tx_[18], cogs, var))
        for j in range(D):
            if not (cs_[j] + up_[j] + cd_[j]): continue
            v = int(vr[j])
            jv("SAL", e, days[j], f"{days[j]:%y%m%d}", "Daily sales, cost of goods and cash variance",
               [("1000", cs_[j], 0), ("1010", up_[j], 0), ("1020", cd_[j], 0), ("4000", 0, e5[j]), ("4001", 0, e18[j]), ("2100", 0, t5[j]), ("2101", 0, t18[j]), ("5000", cg[j], 0), ("1100", 0, cg[j]),
                ("5300", max(-v, 0), max(v, 0)), ("1000", max(v, 0), max(-v, 0))])
    for (e, s), a in sorted(sagg.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        jv("STL", e, s, f"{s:%y%m%d}", "Gateway settlements received", [("1030", a[2], 0), ("5200", a[3], 0), ("1050", a[4], 0), ("1010", 0, a[0]), ("1020", 0, a[1])])
    for (e, d, stt), amt in sorted(adj.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        jv("ADJ", e, d, f"{d:%y%m%d}{'M' if stt == 'matched' else 'W'}", "Settlement shortfall cleared", [("1030" if stt == "matched" else "5400", amt, 0), ("1050", 0, amt)])
    for e, ym, cost in wast:
        y, mo = int(ym[:4]), int(ym[5:]); d = min(END, (date(y + (mo == 12), mo % 12 + 1, 1) - timedelta(days=1)))
        jv("WST", e, d, ym.replace("-", ""), "Approved wastage for the month", [("5100", cost, 0), ("1100", 0, cost)])
    for x in invs:
        tot_ = x["inr_base"] + x["inr_tax"]; x["inr"] = tot_
        jv("PUR", x["entity_id"], x["inv_date"], x["id"], f"Vendor invoice {x['inv_no']}", [("1100", x["inr_base"], 0), ("1200", x["inr_tax"], 0), ("2000", 0, tot_)])
    for p in pays:
        x = ibyid[p["invoice_id"]]; paid = int(round(p["amount_minor"] * p["fx_rate"])); d = p["paid_on"]
        d = d if isinstance(d, date) else date.fromisoformat(str(d)[:10]); diff = x["inr"] - paid
        jv("PAY", x["entity_id"], d, p["id"], f"Payment against {x['inv_no']}", [("2000", x["inr"], 0), ("1030", 0, paid), ("5500", max(-diff, 0), max(diff, 0))])
    # ---- GST periods and locks ----
    gp, lk = [], []
    for e, en in ents.items():
        for p in PERIODS:
            y, mo = int(p[:4]), int(p[5:]); filed = datetime(y + (mo == 12), mo % 12 + 1, 18, 18, 0)
            if en["india"]:
                s_ = "filed" if p <= "2026-08" or (p == per and e != ka) else ("review" if p == per else "open")
                gp.append(dict(entity_id=e, period=p, status=s_, locked_at=filed if s_ == "filed" else None))
            if p <= "2026-08" or (p == per and e != ka and ents[e]["code"] != "DFH-QA"): lk.append(dict(entity_id=e, period=p, locked_at=filed, locked_by=fin))
    with engine.begin() as c:
        for name, rows in (("account", [dict(code=a, name=n, type=t) for a, n, t in ACCOUNTS]), ("day_close", dc), ("settlement", stl), ("recon_item", rec), ("gstr2b_line", g2b_rows),
                           ("journal_entry", jvs), ("journal_line", lines), ("gst_return_period", gp), ("period_lock", lk)):
            for i in range(0, len(rows), 5000): c.execute(insert(T[name]), rows[i:i + 5000])
        for x in invs:
            c.execute(text("update vendor_invoice set entity_id=:e, taxable_minor=:b, tax_minor=:t where id=:i"), dict(e=x["entity_id"], b=x["taxable"], t=x["tax"], i=x["id"]))
    return dict(day_close=len(dc), settlements=len(stl), recon=len(rec), open_recon=sum(1 for x in rec if x["status"] == "open"), journals=len(jvs), lines=len(lines), gstr2b=len(g2b_rows), locks=len(lk))
