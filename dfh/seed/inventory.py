"""Module 4 seed: batches, stock as at 31 Oct 2026, ledger history, transfers, indents, repack jobs, count plans.
Every balance is the sum of its ledger rows, by construction. Cost per base unit is per kg for loose SKUs, per unit for packed.
Planted: F1 (Hyderabad warehouse shrink and repack loss), F3 (Pune warehouse thin on the hot SKUs), F6 (dried pineapple near expiry
in kiosks), F7 (one shared Diwali gift box component is short)."""
import json, random
from datetime import datetime, date, timedelta, time
import numpy as np
from sqlalchemy import text, insert
from ..schema import metadata

NOW = datetime(2026, 10, 31, 9, 0); TODAY = NOW.date()
dt = lambda d, h=10: datetime.combine(d, time(h, 0))


def run(engine, seed=42):
    rng = np.random.default_rng(seed + 4); rnd = random.Random(seed + 4)
    with engine.connect() as c:
        def q(sql): return [dict(r._mapping) for r in c.execute(text(sql)).fetchall()]
        skus = {r["id"]: r for r in q("select id, base_uom, procurement_type, shelf_life_days, std_cost_paise, bulk_sku_id, pack_g, mrp_paise, name from sku")}
        whs = {r["id"]: r for r in q("select id, code, city, state from location where type='warehouse' order by id")}
        stores = {r["id"]: r for r in q("select id, tier, serving_wh_id, city, code, state from location where type='store'")}
        sa = q("select store_id, sku_id, min_qty, max_qty from store_assortment")
        bom = q("select kit_sku_id, component_sku_id, qty from kit_bom")
        vend = q("select distinct sku_id, vendor_id from vendor_sku_cost")
        binrows = q("select id, warehouse_id from location_bin order by id")
        fnd = {r["code"]: (json.loads(r["params"]) if isinstance(r["params"], str) else r["params"]) for r in q("select code, params from demo_finding")}
    bins = {}
    for b in binrows: bins.setdefault(b["warehouse_id"], []).append(b["id"])
    vend_of = {}
    for v in vend: vend_of.setdefault(v["sku_id"], []).append(v["vendor_id"])
    hyd, pune_st, hot = fnd["F1"]["warehouse_id"], set(fnd["F3"]["store_ids"]), set(fnd["F3"]["sku_ids"])
    pune_wh = {stores[s]["serving_wh_id"] for s in pune_st}
    kiosks, pine = fnd["F6"]["store_ids"], fnd["F6"]["sku_ids"]
    isg = lambda sid: skus[sid]["base_uom"] == "g"
    rq = lambda sid, x: int(round(x / 100.0)) * 100 if isg(sid) else int(round(x))
    mn = lambda sid: 100 if isg(sid) else 1

    # batches: three per SKU, oldest first
    batches, bid_of, bcost, bexp, brec = [], {}, {}, {}, {}
    for i, sid in enumerate(sorted(skus)):
        s = skus[sid]; span = min(80.0, 0.6 * s["shelf_life_days"]); src = s["bulk_sku_id"] or sid
        for k, fr in enumerate((0.9, 0.5, 0.1)):
            bid = i * 3 + k + 1; rec = TODAY - timedelta(days=int(span * fr)); mfg = rec - timedelta(days=rnd.randint(2, 10)); exp = mfg + timedelta(days=s["shelf_life_days"])
            cost = int(s["std_cost_paise"] * rnd.uniform(0.96, 1.06)); bid_of.setdefault(sid, []).append(bid); bcost[bid] = cost; bexp[bid] = exp; brec[bid] = rec
            batches.append(dict(id=bid, batch_no=f"B{sid:04d}-{k + 1}", sku_id=sid, vendor_id=rnd.choice(vend_of[src]) if src in vend_of else None, received_on=rec, mfg_date=mfg, expiry_date=exp,
                                mrp_paise=s["mrp_paise"], unit_cost_paise=cost, source_doc_type="opening_stock", source_doc_id="OPEN"))
    xb = {}                                                       # F6 old batches for dried pineapple
    for j, sid in enumerate(pine):
        bid = 50000 + j; rec = TODAY - timedelta(days=120); exp = TODAY + timedelta(days=rnd.randint(6, 35)); mfg = min(exp - timedelta(days=skus[sid]["shelf_life_days"]), rec - timedelta(days=5))
        xb[sid] = bid; bcost[bid] = skus[sid]["std_cost_paise"]; bexp[bid] = exp; brec[bid] = rec
        batches.append(dict(id=bid, batch_no=f"B{sid:04d}-X", sku_id=sid, vendor_id=None, received_on=rec, mfg_date=mfg, expiry_date=exp, mrp_paise=skus[sid]["mrp_paise"],
                            unit_cost_paise=bcost[bid], source_doc_type="opening_stock", source_doc_id="OPEN"))

    led, bal = [], {}
    def add(ts, loc, sid, bid, qty, mt, dtp, did, bin_id=None):
        led.append(dict(ts=ts, location_id=loc, bin_id=bin_id, sku_id=sid, batch_id=bid, qty=qty, movement_type=mt, doc_type=dtp, doc_id=did, unit_cost_paise=bcost[bid]))
        bal[(loc, sid, bid)] = bal.get((loc, sid, bid), 0) + qty

    # warehouse demand proxy: store max levels, loose demand from packs, kit components from kits
    comps = {}
    for b in bom: comps.setdefault(b["kit_sku_id"], []).append((b["component_sku_id"], b["qty"]))
    proxy, assort = {}, {}
    for r in sa:
        wh, sid, m = stores[r["store_id"]]["serving_wh_id"], r["sku_id"], r["max_qty"]; s = skus[sid]
        assort.setdefault(r["store_id"], {})[sid] = (r["min_qty"], m)
        proxy[(wh, sid)] = proxy.get((wh, sid), 0) + m
        if s["bulk_sku_id"] and s["pack_g"]: proxy[(wh, s["bulk_sku_id"])] = proxy.get((wh, s["bulk_sku_id"]), 0) + m * s["pack_g"]
        for comp, qty in comps.get(sid, []): proxy[(wh, comp)] = proxy.get((wh, comp), 0) + m * qty
    diw = fnd["F7"]["kit_sku_ids"]; cnt = {}
    for k in diw:
        for comp, _ in comps[k]: cnt[comp] = cnt.get(comp, 0) + 1
    short_comp = max(cnt, key=lambda x: (cnt[x], -x))

    # warehouse stock
    for (wh, sid), pv in sorted(proxy.items()):
        t = pv * rng.uniform(1.5, 3.0)
        if wh in pune_wh and sid in hot: t *= 0.04
        if sid == short_comp: t *= 0.08
        binid = bins[wh][sid % len(bins[wh])]
        for k, fr in enumerate((0.2, 0.35, 0.45)):
            bid = bid_of[sid][k]; tq = t * fr
            if tq < mn(sid): continue
            sf = (0.03 if wh == hyd else 0.004) * rng.uniform(0.5, 1.5) if rng.random() < 0.35 else 0.0
            df = rng.uniform(0.3, 0.7); R = rq(sid, tq / (1 - df - sf)); disp = rq(sid, R * df); shr = rq(sid, R * sf)
            if R - disp - shr <= 0: continue
            add(dt(brec[bid]), wh, sid, bid, R, "receipt", "opening_stock", "OPEN", binid)
            add(dt(brec[bid] + timedelta(days=min(5, (TODAY - brec[bid]).days)), 14), wh, sid, bid, -disp, "transfer_out", "history", "DISPATCH-HIST", binid)
            if shr > 0:
                parts = rnd.randint(1, 3); left = shr
                for p in range(parts):
                    a = left if p == parts - 1 else rq(sid, shr / parts)
                    if a <= 0: continue
                    left -= a; d = brec[bid] + timedelta(days=rnd.randint(1, max(1, (TODAY - brec[bid]).days)))
                    reason = rnd.choice(["unexplained"] * 5 + ["weighing_loss", "handling"]) if wh == hyd else rnd.choice(["weighing_loss", "handling", "pest", "spill", "unexplained"])
                    add(dt(min(d, TODAY), 16), wh, sid, bid, -a, "shrink", "shrink_log", reason, binid)

    # store stock
    for r in sa:
        st, sid, mx = r["store_id"], r["sku_id"], r["max_qty"]
        if st in kiosks and sid in xb and rnd.random() < 0.9:
            bid = xb[sid]; qty = rq(sid, mx * rng.uniform(0.7, 1.0))
        else:
            bid = bid_of[sid][2 if rng.random() < 0.6 else 1]; qty = rq(sid, mx * rng.uniform(0.2, 1.0))
            if st in pune_st and sid in hot: qty = 0 if rng.random() < 0.5 else rq(sid, mx * 0.05)
        if qty >= mn(sid): add(dt(min(TODAY, brec[bid] + timedelta(days=3))), st, sid, bid, qty, "transfer_in", "opening_stock", "OPEN")
    for st in kiosks:                                              # F6: kiosks that do not list pineapple still carry old stock
        for sid in pine:
            if sid not in assort.get(st, {}) : add(dt(TODAY - timedelta(days=60)), st, sid, xb[sid], 3000 if isg(sid) else 10, "transfer_in", "opening_stock", "OPEN")

    wh_keys = {w: [k for k, v in bal.items() if k[0] == w and v > 0] for w in whs}
    T, TL, IND, IL, PK = [], [], [], [], []
    ids = dict(t=0, i=0, il=0)
    def lines_for(src, n, st=None, frac=(0.1, 0.25)):
        keys = wh_keys[src]
        if st is not None: keys = [k for k in keys if k[1] in assort.get(st, {})]
        out, used = [], set()
        for k in rnd.sample(keys, min(n * 2, len(keys))):
            if k[1] in used or bal[k] <= 0: continue
            qty = rq(k[1], bal[k] * rnd.uniform(*frac))
            if qty < mn(k[1]): continue
            used.add(k[1]); out.append((k[2], k[1], qty))
            if len(out) == n: break
        return out
    def make_transfer(src, dst, status, days_ago, lines, indent_id=None):
        ids["t"] += 1; tid = ids["t"]; no = f"TR-26{tid:04d}"; disp = NOW - timedelta(days=days_ago, hours=2)
        inter = whs[src]["state"] != (whs[dst]["state"] if dst in whs else stores[dst]["state"])
        T.append(dict(id=tid, transfer_no=no, indent_id=indent_id, from_location_id=src, to_location_id=dst, status=status, created_at=disp - timedelta(hours=5), dispatched_at=disp if status != "draft" else None,
                      received_at=disp + timedelta(hours=30) if status == "received" else None, vehicle_no=f"KA0{rnd.randint(1, 9)}AB{rnd.randint(1000, 9999)}" if status != "draft" else None,
                      eway_ref=f"EW{rnd.randint(10**11, 10**12 - 1)}" if inter and status != "draft" else None))
        for bid, sid, qty in lines:
            recv = None
            if status != "draft": add(disp, src, sid, bid, -qty, "transfer_out", "transfer", no)
            if status == "received":
                recv = qty
                if rnd.random() < 0.15: recv = max(0, qty - max(mn(sid), rq(sid, qty * 0.05)))
                add(disp + timedelta(hours=30), dst, sid, bid, qty, "transfer_in", "transfer", no)
                if recv < qty: add(disp + timedelta(hours=30), dst, sid, bid, recv - qty, "transit_shrink", "transfer", no)
            TL.append(dict(transfer_id=tid, sku_id=sid, batch_id=bid if status != "draft" else None, qty_sent=qty, qty_received=recv))
        return tid
    def make_indent(st, status, days_ago, lines, alloc=None):
        ids["i"] += 1; iid = ids["i"]; wh = stores[st]["serving_wh_id"]; cr = NOW - timedelta(days=days_ago + 1)
        IND.append(dict(id=iid, indent_no=f"IN-26{iid:04d}", store_id=st, warehouse_id=wh, status=status, created_at=cr, needed_by=(cr + timedelta(days=3)).date()))
        for bid, sid, qty in lines:
            ids["il"] += 1; a = qty if status in ("dispatched", "received") else 0
            IL.append(dict(id=ids["il"], indent_id=iid, sku_id=sid, qty_req=qty, qty_alloc=a, qty_dispatched=a))
        return iid
    plan = [("received", rnd.uniform(3, 40)) for _ in range(28)] + [("in_transit", rnd.uniform(0.5, 3)) for _ in range(9)] + [("draft", rnd.uniform(0, 2)) for _ in range(5)]
    wl = sorted(whs)
    for status, ago in plan:
        a = rnd.choice(wl)
        if rnd.random() < 0.6 and status != "draft":
            st = rnd.choice([s for s, v in stores.items() if v["serving_wh_id"] == a]); ls = lines_for(a, rnd.randint(3, 8), st)
            if not ls: continue
            iid = make_indent(st, "received" if status == "received" else "dispatched", ago, ls); make_transfer(a, st, status, ago, ls, iid)
        else:
            b = rnd.choice([w for w in wl if w != a]); ls = lines_for(a, rnd.randint(3, 8))
            if ls: make_transfer(a, b, status, ago, ls)
    for status, n in (("allocated", 6), ("open", 4)):                   # allocated indents hold picks (reservations), open ones hold nothing
        for _ in range(n):
            a = rnd.choice(wl); st = rnd.choice([s for s, v in stores.items() if v["serving_wh_id"] == a]); ls = lines_for(a, rnd.randint(3, 6), st, (0.03, 0.1))
            if not ls: continue
            iid = make_indent(st, status, rnd.uniform(0, 2), ls)
            for (bid, sid, qty), il in zip(ls, IL[-len(ls):]):
                il["qty_req"] = rq(sid, qty * 1.2) or qty
                if status == "allocated": il["qty_alloc"] = qty; PK.append(dict(indent_line_id=il["id"], batch_id=bid, qty=qty, picked_at=None))

    # repack jobs: bulk to packs with yield loss
    RJ, RO, rj = [], [], 0
    bulk_kids = {}
    for sid, s in skus.items():
        if s["bulk_sku_id"] and s["pack_g"]: bulk_kids.setdefault(s["bulk_sku_id"], []).append(sid)
    for _ in range(30):
        a = rnd.choice(wl); cand = [k for k in wh_keys[a] if k[1] in bulk_kids and bal[k] >= 20000 and bexp[k[2]] > TODAY + timedelta(days=15)]
        if not cand: continue
        k = rnd.choice(cand); sid = k[1]; tgt = max(5000, int(bal[k] * rnd.uniform(0.04, 0.15)) // 1000 * 1000); lossr = 0.035 if a == hyd else rnd.uniform(0.004, 0.012)
        kids = rnd.sample(bulk_kids[sid], min(len(bulk_kids[sid]), rnd.randint(1, 3))); w = rng.dirichlet(np.ones(len(kids)) * 3)
        outs = [(p, int(tgt * (1 - lossr) * wi // skus[p]["pack_g"])) for p, wi in zip(kids, w)]; outs = [(p, u) for p, u in outs if u > 0]
        if not outs: continue
        packed = sum(u * skus[p]["pack_g"] for p, u in outs); inp = -(-int(packed / (1 - lossr)) // 100) * 100
        if inp > bal[k] or packed < 3000: continue
        rj += 1; ts = NOW - timedelta(days=rnd.uniform(1, 35)); no = f"RP-26{rj:04d}"
        RJ.append(dict(id=rj, job_no=no, warehouse_id=a, bulk_sku_id=sid, input_batch_id=k[2], input_g=inp, status="done", started_at=ts, finished_at=ts + timedelta(hours=3), operator_id=None, loss_g=inp - packed))
        add(ts, a, sid, k[2], -inp, "repack_out", "repack", no)
        for p, u in outs:
            nb = 60000 + len(batches); exp = min(bexp[k[2]], ts.date() + timedelta(days=skus[p]["shelf_life_days"])); cost = int(bcost[k[2]] / 1000 * skus[p]["pack_g"] * inp / packed)
            batches.append(dict(id=nb, batch_no=f"{'B%04d-%d' % (sid, bid_of[sid].index(k[2]) + 1)}-R{rj}-{p}", sku_id=p, vendor_id=None, received_on=ts.date(), mfg_date=ts.date(), expiry_date=exp, mrp_paise=skus[p]["mrp_paise"],
                                unit_cost_paise=cost, source_doc_type="repack", source_doc_id=no)); bcost[nb] = cost; bexp[nb] = exp
            add(ts, a, p, nb, u, "repack_in", "repack", no); RO.append(dict(job_id=rj, sku_id=p, batch_id=nb, units=u))

    # count plans: one open class A plan per warehouse, plus submitted plans (Hyderabad with real losses)
    CP, CL, cp = [], [], 0
    for a in wl:
        rows = sorted(((k, bal[k] / (1000 if isg(k[1]) else 1) * bcost[k[2]]) for k in bal if k[0] == a and bal[k] > 0), key=lambda x: -x[1])
        top = rows[:max(1, len(rows) // 5)]
        cp += 1; CP.append(dict(id=cp, plan_no=f"CP-26{cp:04d}", location_id=a, abc_class="A", planned_on=TODAY + timedelta(days=rnd.randint(1, 5)), status="planned"))
        for k, _ in rnd.sample(top, min(15, len(top))): CL.append(dict(plan_id=cp, sku_id=k[1], batch_id=k[2], system_qty=bal[k], counted_qty=None, variance_qty=None, approved_by=None))
    for a in [hyd] + rnd.sample([w for w in wl if w != hyd], 3):
        rows = sorted(((k, bal[k] / (1000 if isg(k[1]) else 1) * bcost[k[2]]) for k in bal if k[0] == a and bal[k] > 0), key=lambda x: -x[1])
        cp += 1; CP.append(dict(id=cp, plan_no=f"CP-26{cp:04d}", location_id=a, abc_class="B", planned_on=TODAY - timedelta(days=1), status="submitted"))
        for k, _ in rnd.sample(rows[len(rows) // 5: len(rows) // 2], 15):
            loss = rnd.uniform(0.03, 0.12) if a == hyd else rnd.choice([0, 0, 0, 0.004])
            cq = max(0, rq(k[1], bal[k] * (1 - loss))); CL.append(dict(plan_id=cp, sku_id=k[1], batch_id=k[2], system_qty=bal[k], counted_qty=cq, variance_qty=cq - bal[k], approved_by=None))

    assert min(bal.values()) >= 0, "negative balance in seed"
    when = lambda: NOW
    BAL = [dict(location_id=k[0], sku_id=k[1], batch_id=k[2], qty=v, updated_at=NOW) for k, v in bal.items() if v > 0]
    with engine.begin() as c:
        for name, rows in (("batch", batches), ("stock_ledger", led), ("stock_balance", BAL), ("transfer", T), ("transfer_line", TL), ("indent", IND), ("indent_line", IL), ("pick", PK),
                           ("repack_job", RJ), ("repack_output", RO), ("count_plan", CP), ("count_line", CL)):
            t = metadata.tables[name]
            for i in range(0, len(rows), 8000): c.execute(insert(t), rows[i:i + 8000])
    return dict(batches=len(batches), ledger=len(led), balances=len(BAL), transfers=len(T), indents=len(IND), repack_jobs=len(RJ), count_plans=len(CP), short_component=short_comp)
