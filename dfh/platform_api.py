"""Module 10 API: platform. Approvals with amount rules, audit log viewer, imports with check then apply, legal entities and FX,
users and roles, device and job health, notifications. Rules below are stated assumptions for the demo."""
import csv, io, json, re
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import text

ADMIN = {"ceo", "admin"}
AUDIT = {"ceo", "admin", "finance"}
OPS = {"ceo", "admin", "finance"}                    # entities, FX, health
APPROVERS = {"ceo", "finance"}
IMPORTERS = {"ceo", "procurement", "admin"}
DOCS = {"payment_release": dict(label="Vendor payment release", unit="inr", who={"procurement", "finance", "ceo", "admin"}),
        "price_change": dict(label="SKU price change", unit="pct", who={"ceo", "procurement", "admin"})}
PCT_FLOOR_BP = 1000                                    # below 10 percent a price change is made directly in SKU master
GSTIN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$")
USERNAME = re.compile(r"^[a-z0-9._-]{3,30}$")
FX_MOVE_LIMIT, COST_MOVE_LIMIT, MAX_ROWS = 0.10, 0.40, 5000
KINDS = {"sku_prices": dict(name="SKU prices", cols="sku_code, mrp_rupees or price_per_kg_rupees, status (optional)", note="Packed SKUs take mrp_rupees, loose SKUs price_per_kg_rupees. Price must stay above cost after tax."),
         "vendor_costs": dict(name="Vendor costs", cols="vendor_code, sku_code, price, effective_from", note="Price is in the vendor's own currency, per the existing price book unit. Only existing vendor and SKU pairs. effective_from must be later than the current line. A move above 40 percent is rejected as a probable unit error."),
         "store_minmax": dict(name="Store min and max", cols="store_code, sku_code, min_qty, max_qty", note="Grams for loose SKUs, units for packs. Updates an existing assortment line or adds one.")}
SAMPLE = {"sku_prices": "sku_code,mrp_rupees,price_per_kg_rupees,status\n", "vendor_costs": "vendor_code,sku_code,price,effective_from\n", "store_minmax": "store_code,sku_code,min_qty,max_qty\n"}


class ReqIn(BaseModel):
    doc_type: str
    ref: str
    value: Optional[float] = None
    note: Optional[str] = None


class DecideIn(BaseModel):
    action: str
    note: Optional[str] = None


class RuleIn(BaseModel):
    min_value: float
    max_value: Optional[float] = None
    approver: str


class ImportIn(BaseModel):
    kind: str
    csv: str
    apply: bool = False
    filename: Optional[str] = "upload.csv"


class EntityIn(BaseModel):
    name: Optional[str] = None
    gstin: Optional[str] = None


class FxIn(BaseModel):
    currency: str
    month: str
    rate: float
    force: bool = False


class UserIn(BaseModel):
    username: str
    name: str
    role: str
    password: str
    scope_code: Optional[str] = None


class UserPatch(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    scope_code: Optional[str] = None
    active: Optional[bool] = None


class PwIn(BaseModel):
    password: str


class ReadIn(BaseModel):
    ids: Optional[list] = None


def jl(v):
    for _ in range(2):
        if isinstance(v, str):
            try: v = json.loads(v)
            except Exception: return v
    return v


def dd(s):
    return date.fromisoformat(str(s)[:10])


def attach(app, ctx):
    me, need, many, one, audit, engine, an, NOW = (ctx[k] for k in ("me", "need", "many", "one", "audit", "engine", "an", "NOW"))
    from . import auth, wastage_api as W, demand_api as D, finance_api as F, crm_api as C, procurement_api as P, pos_api as S, inventory as I, hr_api as H
    from .platform_matrix import matrix
    TODAY = NOW.date()

    def notify(c, uids, title, body, ref_id):
        for u in uids:
            c.execute(text("insert into notification(user_id,channel,title,body,ref_type,ref_id,created_at) values (:u,'app',:t,:b,'approval',:i,:c)"), dict(u=u, t=title, b=body, i=str(ref_id), c=NOW))

    def role_users(c, code):
        return [r[0] for r in c.execute(text("select u.id from app_user u join role r on r.id=u.role_id where r.code=:c and u.active=1"), dict(c=code)).fetchall()]

    # ---------------- approvals ----------------
    def rule_for(doc, amount):
        return one("select a.id, a.min_amount_paise lo, a.max_amount_paise hi, r.code role from approval_rule a join role r on r.id=a.approver_role_id where a.doc_type=:d and a.min_amount_paise<=:a and (a.max_amount_paise is null or :a<a.max_amount_paise) order by a.min_amount_paise desc limit 1", d=doc, a=amount)

    def fx_of(cur):
        r = one("select rate_to_inr r from fx_rate where currency=:c order by month desc limit 1", c=cur)
        return r["r"] if r else 1.0

    def parse_doc(r):
        if r["doc_type"] == "price_change":
            s, fld, new = r["doc_id"].split(":"); return int(s), fld, int(new)
        return None

    def enrich(r, u):
        rule = rule_for(r["doc_type"], r["amount_paise"]); need_role = rule["role"] if rule else "ceo"
        det = {}
        if r["doc_type"] == "payment_release":
            i = one("select i.inv_no, i.amount_minor, i.currency, i.status, i.due_date, v.name vendor from vendor_invoice i join vendor v on v.id=i.vendor_id where i.id=:i", i=int(r["doc_id"]))
            if i: det = dict(title=f"Pay {i['vendor']}", sub=f"Invoice {i['inv_no']}, {i['currency']} {i['amount_minor'] / 100:,.0f}, due {str(i['due_date'])[:10]}", live=i["status"])
        else:
            s, fld, new = parse_doc(r)
            k = one("select name, code, mrp_paise, price_per_kg_paise from sku where id=:i", i=s)
            if k: det = dict(title=f"{k['code']} {k['name']}", sub=f"{'MRP' if fld == 'mrp_paise' else 'Price per kg'} {(k[fld] or 0) / 100:,.2f} to {new / 100:,.2f} ({r['amount_paise'] / 100:.1f}%)", live=None)
        pending = r["status"] == "pending"
        ok = pending and u["role"] in APPROVERS and r["requested_by"] != u["id"] and (u["role"] == "ceo" or u["role"] == need_role)
        return dict(r, label=DOCS[r["doc_type"]]["label"], unit=DOCS[r["doc_type"]]["unit"], need_role=need_role, can_decide=ok, can_cancel=pending and (r["requested_by"] == u["id"] or u["role"] in ADMIN),
                    age_h=int((NOW - (r["created_at"] if isinstance(r["created_at"], datetime) else datetime.fromisoformat(str(r["created_at"])))).total_seconds() / 3600), **det)

    SEL = ("select q.id, q.doc_type, q.doc_id, q.status, q.amount_paise, q.created_at, q.decided_at, q.note, q.requested_by, q.approver_id, ru.name requester, au.name approver "
           "from approval_request q left join app_user ru on ru.id=q.requested_by left join app_user au on au.id=q.approver_id")

    @app.get("/api/platform/approvals")
    def approvals(view: str = "queue", status: str = "", page: int = 1, u=Depends(me)):
        w, p = [], {}
        if view == "mine": w.append("q.requested_by=:u"); p["u"] = u["id"]
        elif view == "all":
            if u["role"] not in AUDIT: raise HTTPException(403, "Your role cannot see all requests")
        else: w.append("q.status='pending'")
        if status: w.append("q.status=:s"); p["s"] = status
        wh = (" where " + " and ".join(w)) if w else ""
        rows = [enrich(r, u) for r in many(f"{SEL}{wh} order by (q.status='pending') desc, q.created_at desc limit 400", **p)]
        if view == "queue": rows = [r for r in rows if r["can_decide"] or u["role"] in AUDIT]
        n = 40; tot = len(rows)
        return dict(total=tot, page=page, size=n, items=rows[(page - 1) * n: page * n], mine_waiting=sum(1 for r in rows if r["can_decide"]))

    @app.get("/api/platform/approvals/options")
    def approval_options(u=Depends(me)):
        inv = many("select i.id, i.inv_no, v.name vendor, i.currency, i.amount_minor, i.due_date from vendor_invoice i join vendor v on v.id=i.vendor_id where i.status='pending' and not exists "
                   "(select 1 from approval_request q where q.doc_type='payment_release' and q.doc_id=cast(i.id as text) and q.status='pending') order by i.due_date limit 60")
        return dict(types=[dict(code=k, label=v["label"], unit=v["unit"], allowed=u["role"] in v["who"]) for k, v in DOCS.items()], invoices=inv, price_floor_pct=PCT_FLOOR_BP / 100)

    @app.post("/api/platform/approvals")
    def approval_new(b: ReqIn, u=Depends(me)):
        d = DOCS.get(b.doc_type)
        if not d: raise HTTPException(422, "Unknown request type")
        if u["role"] not in d["who"]: raise HTTPException(403, "Your role cannot raise this request")
        if b.doc_type == "payment_release":
            i = one("select i.id, i.inv_no, i.status, i.amount_minor, i.currency from vendor_invoice i where i.id=:i or i.inv_no=:n", i=int(b.ref) if b.ref.isdigit() else -1, n=b.ref)
            if not i: raise HTTPException(404, "Invoice not found")
            if i["status"] != "pending": raise HTTPException(409, f"Invoice is {i['status']}, only pending invoices go for release")
            doc_id, amt, label = str(i["id"]), int(round(i["amount_minor"] * fx_of(i["currency"]))), "Release " + i["inv_no"]
        else:
            k = one("select s.id, s.code, s.base_uom, s.mrp_paise, s.price_per_kg_paise, s.std_cost_paise, coalesce(t.rate_packed_pct,5.0) tax from sku s left join tax_rate t on t.hsn=s.hsn where s.id=:i or s.code=:c", i=int(b.ref) if b.ref.isdigit() else -1, c=b.ref)
            if not k: raise HTTPException(404, "SKU not found")
            if b.value is None or b.value <= 0: raise HTTPException(422, "Enter the new price in rupees")
            fld = "mrp_paise" if k["base_uom"] == "ea" else "price_per_kg_paise"; old = k[fld]; new = int(round(b.value * 100))
            if not old: raise HTTPException(422, "This SKU has no current price")
            if new / (1 + k["tax"] / 100) <= k["std_cost_paise"]: raise HTTPException(422, "Price is at or below cost after tax")
            bp = int(round(abs(new - old) / old * 10000))
            if bp < PCT_FLOOR_BP: raise HTTPException(422, f"A move under {PCT_FLOOR_BP / 100:.0f}% does not need approval. Change it in SKU master")
            if one("select id from approval_request where doc_type='price_change' and status='pending' and doc_id like :p", p=f"{k['id']}:%"): raise HTTPException(409, "This SKU already has a price request waiting")
            doc_id, amt, label = f"{k['id']}:{fld}:{new}", bp, (b.note or f"Price move on {k['code']}")
        if one("select id from approval_request where doc_type=:d and doc_id=:i and status='pending'", d=b.doc_type, i=doc_id): raise HTTPException(409, "A request for this is already waiting")
        rule = rule_for(b.doc_type, amt); need_role = rule["role"] if rule else "ceo"
        with engine.begin() as c:
            rid = c.execute(text("insert into approval_request(doc_type,doc_id,requested_by,status,amount_paise,created_at,note) values (:d,:i,:u,'pending',:a,:t,:n)"), dict(d=b.doc_type, i=doc_id, u=u["id"], a=amt, t=NOW, n=(b.note or label)[:300])).lastrowid
            notify(c, [x for x in role_users(c, need_role) if x != u["id"]], "Approval waiting", label, rid)
            audit(c, u, "request", "approval_request", rid, None, dict(doc_type=b.doc_type, doc_id=doc_id, amount=amt, approver=need_role))
        return dict(id=rid, approver_role=need_role)

    @app.post("/api/platform/approvals/{rid}/decide")
    def approval_decide(rid: int, b: DecideIn, u=Depends(me)):
        if b.action not in ("approve", "reject"): raise HTTPException(422, "Action must be approve or reject")
        r = one(SEL + " where q.id=:i", i=rid)
        if not r: raise HTTPException(404, "Request not found")
        if r["status"] != "pending": raise HTTPException(409, f"Already {r['status']}")
        e = enrich(r, u)
        if r["requested_by"] == u["id"]: raise HTTPException(403, "You cannot decide your own request")
        if not e["can_decide"]: raise HTTPException(403, f"This needs {e['need_role']} approval")
        if b.action == "reject" and not (b.note or "").strip(): raise HTTPException(422, "Say why you are rejecting")
        new = "approved" if b.action == "approve" else "rejected"
        with engine.begin() as c:
            if new == "approved":
                if r["doc_type"] == "payment_release":
                    n = c.execute(text("update vendor_invoice set status='released' where id=:i and status='pending'"), dict(i=int(r["doc_id"]))).rowcount
                    if not n: raise HTTPException(409, "The invoice is no longer pending")
                    audit(c, u, "release", "vendor_invoice", r["doc_id"], dict(status="pending"), dict(status="released", approval=rid))
                else:
                    s, fld, val = parse_doc(r)
                    k = c.execute(text("select s.id, s.base_uom, s.std_cost_paise, s.mrp_paise, s.price_per_kg_paise, coalesce(t.rate_packed_pct,5.0) tax from sku s left join tax_rate t on t.hsn=s.hsn where s.id=:i"), dict(i=s)).mappings().first()
                    if val / (1 + k["tax"] / 100) <= k["std_cost_paise"]: raise HTTPException(409, "Cost has moved, the price is now at or below cost")
                    c.execute(text(f"update sku set {fld}=:v where id=:i"), dict(v=val, i=s))
                    audit(c, u, "price_change", "sku", s, {fld: k[fld]}, {fld: val, "reason": f"approval {rid}"})
            note = (r["note"] or "").split(" || ")[0] + ((" || " + b.note.strip()) if (b.note or "").strip() else "")
            c.execute(text("update approval_request set status=:s, approver_id=:u, decided_at=:t, note=:n where id=:i"), dict(s=new, u=u["id"], t=NOW, n=note[:400], i=rid))
            notify(c, [r["requested_by"]], f"Your request was {new}", (b.note or "").strip() or (r["note"] or "").split(" || ")[0], rid)
            audit(c, u, b.action, "approval_request", rid, dict(status="pending"), dict(status=new, doc_type=r["doc_type"]))
        return dict(id=rid, status=new)

    @app.post("/api/platform/approvals/{rid}/cancel")
    def approval_cancel(rid: int, u=Depends(me)):
        r = one(SEL + " where q.id=:i", i=rid)
        if not r: raise HTTPException(404, "Request not found")
        if r["status"] != "pending": raise HTTPException(409, f"Already {r['status']}")
        if r["requested_by"] != u["id"] and u["role"] not in ADMIN: raise HTTPException(403, "Only the requester can withdraw this")
        with engine.begin() as c:
            c.execute(text("update approval_request set status='cancelled', decided_at=:t where id=:i"), dict(t=NOW, i=rid))
            audit(c, u, "cancel", "approval_request", rid, dict(status="pending"), dict(status="cancelled"))
        return dict(id=rid, status="cancelled")

    def disp(r):
        d = DOCS[r["doc_type"]]; f = (lambda x: None if x is None else (x / 100 if d["unit"] == "inr" else x / 100))
        return dict(id=r["id"], doc_type=r["doc_type"], label=d["label"], unit=d["unit"], min_value=f(r["lo"]), max_value=f(r["hi"]), approver=r["role"])

    RULES = "select a.id, a.doc_type, a.min_amount_paise lo, a.max_amount_paise hi, r.code role from approval_rule a join role r on r.id=a.approver_role_id order by a.doc_type, a.min_amount_paise"

    @app.get("/api/platform/rules")
    def rules(u=Depends(me)):
        return dict(items=[disp(r) for r in many(RULES)], note="A band starts at its minimum and ends before its maximum. Payment bands are in rupees, price bands in percent move. The CEO can decide in any band. Nobody decides their own request.")

    @app.patch("/api/platform/rules/{rid}")
    def rule_edit(rid: int, b: RuleIn, u=Depends(need(ADMIN))):
        r = one("select id, doc_type, min_amount_paise lo, max_amount_paise hi, approver_role_id from approval_rule where id=:i", i=rid)
        if not r: raise HTTPException(404, "Rule not found")
        if b.approver not in APPROVERS: raise HTTPException(422, "Approver must be finance or ceo")
        lo = int(round(b.min_value * 100)); hi = None if b.max_value is None else int(round(b.max_value * 100))
        if lo < 0 or (hi is not None and hi <= lo): raise HTTPException(422, "Maximum must be above the minimum")
        if r["doc_type"] == "price_change" and lo < PCT_FLOOR_BP: raise HTTPException(422, f"Price bands start at {PCT_FLOOR_BP / 100:.0f}%, below that no approval is used")
        for o in many("select id, min_amount_paise lo, max_amount_paise hi from approval_rule where doc_type=:d and id!=:i", d=r["doc_type"], i=rid):
            if lo < (o["hi"] if o["hi"] is not None else 1 << 60) and (hi if hi is not None else 1 << 60) > o["lo"]: raise HTTPException(422, "This band overlaps another band of the same request type")
        rid_role = one("select id from role where code=:c", c=b.approver)["id"]
        with engine.begin() as c:
            c.execute(text("update approval_rule set min_amount_paise=:l, max_amount_paise=:h, approver_role_id=:r where id=:i"), dict(l=lo, h=hi, r=rid_role, i=rid))
            audit(c, u, "update", "approval_rule", rid, dict(lo=r["lo"], hi=r["hi"]), dict(lo=lo, hi=hi, approver=b.approver))
        return disp(one(RULES.replace("order by", "where a.id=:i order by"), i=rid))

    @app.get("/api/platform/waiting")
    def waiting(u=Depends(me)):
        r, out = u["role"], []
        if r in W.APPROVE: out.append(dict(key="wastage", title="Wastage entries waiting", link="#/wastage", **one("select count(*) n, coalesce(sum(cost_paise),0) v from wastage_entry where status='pending'")))
        if r in D.APPROVE: out.append(dict(key="buy", title="Buy suggestions open", link="#/demand", **one("select count(*) n, coalesce(sum(value_paise),0) v from reorder_suggestion where status='open'")))
        if r in H.HR | H.MGR: out.append(dict(key="leave", title="Leave requests pending", link="#/hr", v=None, **one("select count(*) n from leave_request where status='pending'")))
        if r in I.WRITE: out.append(dict(key="counts", title="Cycle counts submitted", link="#/inventory", v=None, **one("select count(*) n from count_plan where status='submitted'")))
        if r in P.INV_RELEASE: out.append(dict(key="inv", title="Vendor invoices pending", link="#/procurement", **one("select count(*) n, coalesce(sum(amount_minor),0) v from vendor_invoice where status='pending'")))
        return out

    # ---------------- audit ----------------
    def audit_where(user_id, action, table, q, frm, to):
        w, p = [], {}
        if user_id: w.append("a.user_id=:u"); p["u"] = user_id
        if action: w.append("a.action=:a"); p["a"] = action
        if table: w.append("a.table_name=:t"); p["t"] = table
        if q: w.append("(a.row_id=:q or lower(coalesce(u.name,'')) like :ql or lower(a.table_name) like :ql)"); p["q"] = q.strip(); p["ql"] = f"%{q.strip().lower()}%"
        try:
            if frm: w.append("a.ts>=:f"); p["f"] = dd(frm)
            if to: w.append("a.ts<:e"); p["e"] = dd(to) + timedelta(days=1)
        except ValueError: raise HTTPException(422, "Dates must be YYYY-MM-DD")
        return (" where " + " and ".join(w)) if w else "", p

    def changes(b, a):
        b, a = jl(b), jl(a); b = b if isinstance(b, dict) else {}; a = a if isinstance(a, dict) else {}
        return [dict(field=k, before=b.get(k), after=a.get(k)) for k in list(dict.fromkeys(list(b) + list(a)))]

    @app.get("/api/platform/audit")
    def audit_list(user_id: int = 0, action: str = "", table: str = "", q: str = "", frm: str = "", to: str = "", page: int = 1, size: int = 40, u=Depends(need(AUDIT))):
        wh, p = audit_where(user_id, action, table, q, frm, to); size = max(10, min(size, 100))
        base = f"from audit_log a left join app_user u on u.id=a.user_id left join role r on r.id=u.role_id{wh}"
        total = one(f"select count(*) n {base}", **p)["n"]
        rows = many(f"select a.id, a.ts, a.action, a.table_name, a.row_id, a.before, a.after, u.name user, r.code role {base} order by a.ts desc, a.id desc limit :l offset :o", **p, l=size, o=(max(1, page) - 1) * size)
        for x in rows: x["changes"] = changes(x.pop("before"), x.pop("after"))
        return dict(total=total, page=page, size=size, items=rows)

    @app.get("/api/platform/audit/options")
    def audit_options(u=Depends(need(AUDIT))):
        return dict(users=many("select id, name from app_user order by name"), actions=[r["action"] for r in many("select distinct action from audit_log order by 1")], tables=[r["table_name"] for r in many("select distinct table_name from audit_log order by 1")])

    @app.get("/api/platform/audit/stats")
    def audit_stats(days: int = 30, u=Depends(need(AUDIT))):
        days = max(7, min(days, 180)); s = NOW - timedelta(days=days)
        by = lambda col: many(f"select {col} k, count(*) n from audit_log a left join app_user u on u.id=a.user_id where a.ts>=:s group by 1 order by n desc limit 8", s=s)
        daily = many("select substr(cast(ts as text),1,10) d, count(*) n from audit_log where ts>=:s group by 1 order by 1", s=s)
        return dict(days=days, total=sum(x["n"] for x in daily), by_action=by("a.action"), by_table=by("a.table_name"), by_user=by("coalesce(u.name,'system')"), daily=daily)

    @app.get("/api/platform/audit/export")
    def audit_export(user_id: int = 0, action: str = "", table: str = "", q: str = "", frm: str = "", to: str = "", u=Depends(need(AUDIT))):
        wh, p = audit_where(user_id, action, table, q, frm, to)
        rows = many(f"select a.ts, u.name user, a.action, a.table_name, a.row_id, a.before, a.after from audit_log a left join app_user u on u.id=a.user_id{wh} order by a.ts desc, a.id desc limit {MAX_ROWS}", **p)
        o = io.StringIO(); w = csv.writer(o); w.writerow(["time", "user", "action", "table", "row", "field", "before", "after"])
        for r in rows:
            ch = changes(r["before"], r["after"]) or [dict(field="", before="", after="")]
            for c in ch: w.writerow([r["ts"], r["user"], r["action"], r["table_name"], r["row_id"], c["field"], c["before"], c["after"]])
        with engine.begin() as c: audit(c, u, "export", "audit_log", "csv", None, dict(rows=len(rows)))
        return Response(o.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=dfh-audit.csv"})

    # ---------------- imports ----------------
    def read_csv(txt):
        rd = list(csv.DictReader(io.StringIO((txt or "").strip())))
        if not rd: raise HTTPException(422, "The file has no rows")
        if len(rd) > MAX_ROWS: raise HTTPException(422, f"At most {MAX_ROWS} rows per file")
        return [{(k or "").strip().lower(): (v or "").strip() for k, v in r.items()} for r in rd]

    def need_cols(rd, cols):
        miss = [c for c in cols if c not in rd[0]]
        if miss: raise HTTPException(422, "Missing column: " + ", ".join(miss))

    def check_vendor_costs(rd):
        need_cols(rd, ["vendor_code", "sku_code", "price", "effective_from"]); errs, plan, seen = [], [], set()
        for i, r in enumerate(rd, start=2):
            code = f"{r['vendor_code']}/{r['sku_code']}"
            def bad(m): errs.append(dict(row=i, code=code, error=m))
            line = one("select c.*, v.id vid, s.id sid from vendor v join sku s on s.code=:s left join vendor_sku_cost c on c.vendor_id=v.id and c.sku_id=coalesce(s.bulk_sku_id, s.id) where v.code=:v order by c.effective_from desc limit 1", v=r["vendor_code"], s=r["sku_code"])
            if not line: bad("Unknown vendor or SKU"); continue
            if line["id"] is None: bad("No existing price book line for this vendor and SKU"); continue
            try: price = float(r["price"]); eff = dd(r["effective_from"])
            except ValueError: bad("Price or date is not valid (date is YYYY-MM-DD)"); continue
            if price <= 0: bad("Price must be positive"); continue
            if eff <= dd(line["effective_from"]): bad(f"Current line already starts {str(line['effective_from'])[:10]}, use a later date"); continue
            if eff > TODAY + timedelta(days=31): bad("Date is more than a month ahead"); continue
            minor = int(round(price * 100)); mv = abs(minor / line["price_minor"] - 1)
            if mv > COST_MOVE_LIMIT: bad(f"Price moves {mv * 100:.0f}%, above the {COST_MOVE_LIMIT * 100:.0f}% limit. Check the unit"); continue
            if (line["vid"], line["sku_id"]) in seen: bad("Same vendor and SKU appears twice in the file"); continue
            seen.add((line["vid"], line["sku_id"])); plan.append((line, minor, eff))
        return errs, plan

    def apply_vendor_costs(c, plan):
        for line, minor, eff in plan:
            c.execute(text("update vendor_sku_cost set effective_to=:e where id=:i and effective_to is null"), dict(e=eff - timedelta(days=1), i=line["id"]))
            c.execute(text("insert into vendor_sku_cost(vendor_id,sku_id,currency,price_minor,price_per,incoterm,moq_qty,lead_time_days,effective_from) values (:v,:s,:cu,:p,:pp,:ic,:m,:l,:ef)"),
                      dict(v=line["vendor_id"], s=line["sku_id"], cu=line["currency"], p=minor, pp=line["price_per"], ic=line["incoterm"], m=line["moq_qty"], l=line["lead_time_days"], ef=eff))

    def check_minmax(rd):
        need_cols(rd, ["store_code", "sku_code", "min_qty", "max_qty"]); errs, plan, seen = [], [], set()
        for i, r in enumerate(rd, start=2):
            code = f"{r['store_code']}/{r['sku_code']}"
            def bad(m): errs.append(dict(row=i, code=code, error=m))
            st = one("select id from location where code=:c and type='store'", c=r["store_code"]); sk = one("select id, status from sku where code=:c", c=r["sku_code"])
            if not st: bad("Unknown store code"); continue
            if not sk: bad("Unknown SKU code"); continue
            if sk["status"] == "delisted": bad("SKU is delisted"); continue
            try: lo, hi = int(r["min_qty"]), int(r["max_qty"])
            except ValueError: bad("Min and max must be whole numbers"); continue
            if lo < 0 or hi < lo: bad("Max must be at least min, and neither can be negative"); continue
            if (st["id"], sk["id"]) in seen: bad("Same store and SKU appears twice in the file"); continue
            seen.add((st["id"], sk["id"])); plan.append((st["id"], sk["id"], lo, hi))
        return errs, plan

    def apply_minmax(c, plan):
        for s, k, lo, hi in plan:
            n = c.execute(text("update store_assortment set min_qty=:l, max_qty=:h where store_id=:s and sku_id=:k"), dict(l=lo, h=hi, s=s, k=k)).rowcount
            if not n: c.execute(text("insert into store_assortment(store_id,sku_id,min_qty,max_qty,listed_from) values (:s,:k,:l,:h,:d)"), dict(s=s, k=k, l=lo, h=hi, d=TODAY))

    @app.get("/api/platform/imports/kinds")
    def import_kinds(u=Depends(me)):
        return dict(allowed=u["role"] in IMPORTERS, kinds=[dict(code=k, sample=SAMPLE[k], **v) for k, v in KINDS.items()], max_rows=MAX_ROWS)

    @app.get("/api/platform/imports")
    def import_list(u=Depends(me)):
        rows = many("select id, kind, filename, status, rows_ok, rows_err, created_at, report from import_job order by id desc limit 40")
        for r in rows: r["errors"] = (jl(r.pop("report")) or {}).get("errors", [])[:200] if r.get("report") else []
        return rows

    @app.post("/api/platform/imports")
    def import_run(b: ImportIn, u=Depends(need(IMPORTERS))):
        if b.kind not in KINDS: raise HTTPException(422, "Unknown import type")
        if b.kind == "sku_prices":
            res = ctx["sku_import"](ctx["ImportIn"](csv=b.csv, apply=b.apply), u)
            if b.apply and res["errors"]:
                with engine.begin() as c: c.execute(text("insert into import_job(kind,filename,status,rows_ok,rows_err,created_at,report) values ('sku_prices',:f,'rejected',0,:e,:t,:r)"), dict(f=b.filename, e=len(res["errors"]), t=NOW, r=json.dumps(dict(errors=res["errors"]))))
            return res
        rd = read_csv(b.csv)
        errs, plan = (check_vendor_costs if b.kind == "vendor_costs" else check_minmax)(rd)
        applied = False
        if b.apply:
            with engine.begin() as c:
                ok = bool(plan) and not errs
                jid = c.execute(text("insert into import_job(kind,filename,status,rows_ok,rows_err,created_at,report) values (:k,:f,:s,:o,:e,:t,:r)"),
                                dict(k=b.kind, f=(b.filename or "upload.csv")[:200], s="applied" if ok else "rejected", o=len(plan) if ok else 0, e=len(errs), t=NOW, r=json.dumps(dict(errors=errs)) if errs else None)).lastrowid
                if ok:
                    (apply_vendor_costs if b.kind == "vendor_costs" else apply_minmax)(c, plan)
                    audit(c, u, "import", {"vendor_costs": "vendor_sku_cost", "store_minmax": "store_assortment"}[b.kind], f"job:{jid}", None, dict(rows=len(plan), file=b.filename))
                    applied = True
        return dict(rows=len(rd), ok=len(plan), errors=errs, applied=applied)

    # ---------------- entities and FX ----------------
    def entity_sales(days=30):
        end = an.max_date; s = end - timedelta(days=days - 1); ps = s - timedelta(days=days)
        rows = an.q("select d.id, sum(case when a.date>=? then a.net else 0 end), sum(case when a.date<? then a.net else 0 end) from agg a join dim_store d on d.id=a.store_id where a.date>=? and a.date<=? group by 1", [s, s, ps, end])
        m = {r["id"]: r["e"] for r in many("select id, entity_id e from location where type='store'")}; out = {}
        for sid, cur, prev in rows:
            o = out.setdefault(m[sid], [0, 0]); o[0] += int(cur or 0); o[1] += int(prev or 0)
        return out, end

    @app.get("/api/platform/entities")
    def entities(u=Depends(need(OPS))):
        sales, end = entity_sales()
        ents = many("select e.id, e.code, e.name, e.country, e.currency, e.state, e.gstin, e.is_demo, (select count(*) from location l where l.entity_id=e.id and l.type='store' and l.active=1) stores, "
                    "(select count(*) from location l where l.entity_id=e.id and l.type='warehouse' and l.active=1) warehouses, "
                    "(select count(*) from employee x join location l on l.id=x.location_id where l.entity_id=e.id and x.status in ('active','notice')) people from legal_entity e order by e.id")
        pay = {r["e"]: r["v"] for r in many("select i.entity_id e, sum(i.amount_minor*coalesce((select f.rate_to_inr from fx_rate f where f.currency=i.currency order by f.month desc limit 1),1.0)) v from vendor_invoice i where i.status in ('pending','held','released') group by 1")}
        for e in ents:
            cur, prev = sales.get(e["id"], [0, 0]); e["sales30"] = cur; e["growth"] = (cur / prev - 1) if prev else None; e["payables"] = int(pay.get(e["id"], 0) or 0)
            e["local30"] = int(cur / fx_of(e["currency"])) if e["currency"] != "INR" else None
        return dict(items=ents, as_of=str(end), total_sales=sum(e["sales30"] for e in ents), total_payables=sum(e["payables"] for e in ents),
                    note="Sales are in INR equivalent at the history's stated rates. Payables use the latest FX rate. Entity scoping is not yet applied inside the other modules.")

    @app.get("/api/platform/entities/{code}")
    def entity_detail(code: str, u=Depends(need(OPS))):
        e = one("select id, code, name, country, currency, state, gstin, is_demo from legal_entity where code=:c", c=code)
        if not e: raise HTTPException(404, "Entity not found")
        ids = [r["id"] for r in many("select id from location where entity_id=:e and type='store'", e=e["id"])]
        inl = ",".join(str(i) for i in ids) or "-1"
        monthly = [dict(month=str(r[0])[:7], net=int(r[1])) for r in an.q(f"select strftime(date,'%Y-%m'), sum(net) from agg where store_id in ({inl}) group by 1 order by 1")]
        cities = [dict(city=r[0], net=int(r[1]), stores=r[2]) for r in an.q(f"select d.city, sum(a.net), count(distinct d.id) from agg a join dim_store d on d.id=a.store_id where d.id in ({inl}) and a.date>? group by 1 order by 2 desc limit 8", [an.max_date - timedelta(days=29)])]
        fm = many("select format, count(*) n from location where entity_id=:e and type='store' and active=1 group by 1 order by n desc", e=e["id"])
        wh = many("select code, name, city from location where entity_id=:e and type='warehouse' order by name", e=e["id"])
        pay = many("select i.inv_no, v.name vendor, i.status, i.due_date, i.currency, i.amount_minor from vendor_invoice i join vendor v on v.id=i.vendor_id where i.entity_id=:e and i.status in ('pending','held','released') order by i.due_date limit 8", e=e["id"])
        hist = many("select a.ts, a.action, a.after, u.name user from audit_log a left join app_user u on u.id=a.user_id where a.table_name='legal_entity' and a.row_id=:r order by a.id desc limit 5", r=str(e["id"]))
        return dict(entity=e, monthly=monthly, cities=cities, formats=fm, warehouses=wh, payables=pay, history=hist)

    @app.patch("/api/platform/entities/{code}")
    def entity_edit(code: str, b: EntityIn, u=Depends(need(OPS))):
        e = one("select id, code, name, country, gstin from legal_entity where code=:c", c=code)
        if not e: raise HTTPException(404, "Entity not found")
        ch = {}
        if b.name is not None:
            if not b.name.strip(): raise HTTPException(422, "Name cannot be empty")
            ch["name"] = b.name.strip()[:120]
        if b.gstin is not None:
            g = b.gstin.strip().upper()
            if e["country"] != "India" and g: raise HTTPException(422, "GSTIN applies to Indian entities only")
            if g and not GSTIN.match(g): raise HTTPException(422, "GSTIN must be 15 characters in the standard format")
            if g and g[:2] == "00": raise HTTPException(422, "State code cannot be 00")
            ch["gstin"] = g or None
        if not ch: raise HTTPException(422, "Nothing to change")
        with engine.begin() as c:
            c.execute(text("update legal_entity set " + ", ".join(f"{k}=:{k}" for k in ch) + " where id=:i"), dict(ch, i=e["id"]))
            audit(c, u, "update", "legal_entity", e["id"], {k: e[k] for k in ch}, ch)
        return dict(code=code, **ch)

    @app.get("/api/platform/fx")
    def fx_list(u=Depends(need(OPS))):
        rows = many("select currency, month, rate_to_inr rate, assumed from fx_rate where currency!='INR' order by currency, month")
        by = {}
        for r in rows: by.setdefault(r["currency"], []).append(r)
        users = {r["currency"]: r["n"] for r in many("select currency, count(*) n from legal_entity group by 1")}
        vend = {r["currency"]: r["n"] for r in many("select currency, count(*) n from vendor group by 1")}
        out = []
        for cur, rs in by.items():
            last = rs[-1]; prev = rs[-2] if len(rs) > 1 else None
            out.append(dict(currency=cur, month=str(last["month"])[:7], rate=last["rate"], assumed=bool(last["assumed"]), change=(last["rate"] / prev["rate"] - 1) if prev else None, series=[x["rate"] for x in rs], entities=users.get(cur, 0), vendors=vend.get(cur, 0)))
        return dict(items=out, limit_pct=FX_MOVE_LIMIT * 100, note="Rates are assumed monthly averages for the demo. Entering a rate marks it as entered, not assumed.")

    @app.post("/api/platform/fx")
    def fx_set(b: FxIn, u=Depends(need(OPS))):
        cur = b.currency.upper()
        if cur == "INR" or not one("select 1 x from fx_rate where currency=:c limit 1", c=cur): raise HTTPException(422, "Unknown currency")
        try: m = date.fromisoformat(b.month + "-01")
        except ValueError: raise HTTPException(422, "Month is YYYY-MM")
        if b.rate <= 0: raise HTTPException(422, "Rate must be positive")
        if m > TODAY.replace(day=1) + timedelta(days=32) or m < date(2025, 1, 1): raise HTTPException(422, "Month is out of range")
        near = one("select rate_to_inr r from fx_rate where currency=:c and month<:m order by month desc limit 1", c=cur, m=m) or one("select rate_to_inr r from fx_rate where currency=:c order by month limit 1", c=cur)
        if near and abs(b.rate / near["r"] - 1) > FX_MOVE_LIMIT and not b.force: raise HTTPException(409, f"That is {abs(b.rate / near['r'] - 1) * 100:.0f}% away from {near['r']:.4f}. Confirm to save it")
        old = one("select id, rate_to_inr r from fx_rate where currency=:c and month=:m", c=cur, m=m)
        with engine.begin() as c:
            if old: c.execute(text("update fx_rate set rate_to_inr=:r, assumed=0 where id=:i"), dict(r=b.rate, i=old["id"]))
            else: c.execute(text("insert into fx_rate(currency,month,rate_to_inr,assumed) values (:c,:m,:r,0)"), dict(c=cur, m=m, r=b.rate))
            audit(c, u, "update" if old else "create", "fx_rate", f"{cur}:{b.month}", dict(rate=old["r"]) if old else None, dict(rate=b.rate, forced=b.force))
        return dict(currency=cur, month=b.month, rate=b.rate)

    # ---------------- users and roles ----------------
    UQ = ("select u.id, u.username, u.name, r.code role, r.name role_name, u.scope_type, u.scope_id, l.name scope_name, l.code scope_code, u.active, u.last_login from app_user u join role r on r.id=u.role_id left join location l on l.id=u.scope_id")

    def scope_of(role, code):
        if role in ("warehouse", "store_manager", "cashier"):
            typ = "warehouse" if role == "warehouse" else "store"
            l = one("select id from location where code=:c and type=:t", c=(code or "").strip(), t=typ)
            if not l: raise HTTPException(422, f"{role.replace('_', ' ').title()} needs a valid {typ} code")
            return typ, l["id"]
        if code: raise HTTPException(422, "This role covers the whole company, leave the location empty")
        return "all", None

    def guard_last(c, uid):
        left = c.execute(text("select count(*) from app_user u join role r on r.id=u.role_id where u.active=1 and r.code in ('ceo','admin') and u.id!=:i"), dict(i=uid)).scalar()
        if not left: raise HTTPException(409, "At least one active CEO or admin must remain")

    def good_pw(p):
        if len(p) < 8 or not re.search(r"[A-Za-z]", p) or not re.search(r"\d", p): raise HTTPException(422, "Password needs 8 characters with a letter and a digit")

    @app.get("/api/platform/users")
    def users(u=Depends(need(ADMIN))):
        return dict(items=many(UQ + " order by u.active desc, r.id, u.name"), roles=many("select code, name from role order by id"), warehouses=many("select code, name from location where type='warehouse' order by name"))

    @app.get("/api/platform/roles")
    def roles(u=Depends(me)):
        return matrix(ctx["consts"], dict(W=W, D=D, F=F, C=C, P=P, S=S, I=I, H=H), many("select code, name from role order by id"))

    @app.post("/api/platform/users")
    def user_new(b: UserIn, u=Depends(need(ADMIN))):
        un = b.username.strip().lower()
        if not USERNAME.match(un): raise HTTPException(422, "Username is 3 to 30 characters: letters, digits, dot, dash, underscore")
        if one("select id from app_user where username=:n", n=un): raise HTTPException(409, "Username is taken")
        r = one("select id from role where code=:c", c=b.role)
        if not r: raise HTTPException(422, "Unknown role")
        if not b.name.strip(): raise HTTPException(422, "Name is required")
        good_pw(b.password); typ, sid = scope_of(b.role, b.scope_code)
        with engine.begin() as c:
            uid = c.execute(text("insert into app_user(username,name,role_id,scope_type,scope_id,password_hash,active) values (:u,:n,:r,:t,:s,:p,1)"), dict(u=un, n=b.name.strip()[:80], r=r["id"], t=typ, s=sid, p=auth.hash_pw(b.password))).lastrowid
            audit(c, u, "create", "app_user", uid, None, dict(username=un, role=b.role, scope=b.scope_code))
        return one(UQ + " where u.id=:i", i=uid)

    @app.patch("/api/platform/users/{uid}")
    def user_edit(uid: int, b: UserPatch, u=Depends(need(ADMIN))):
        x = one(UQ + " where u.id=:i", i=uid)
        if not x: raise HTTPException(404, "User not found")
        ch, before = {}, {}
        role = b.role or x["role"]
        if b.name is not None:
            if not b.name.strip(): raise HTTPException(422, "Name is required")
            ch["name"] = b.name.strip()[:80]; before["name"] = x["name"]
        if b.role is not None or b.scope_code is not None:
            r = one("select id from role where code=:c", c=role)
            if not r: raise HTTPException(422, "Unknown role")
            code = b.scope_code if b.scope_code is not None else (x["scope_code"] if role == x["role"] else None)
            typ, sid = scope_of(role, code); ch.update(role_id=r["id"], scope_type=typ, scope_id=sid); before.update(role=x["role"], scope=x["scope_code"])
        if b.active is not None: ch["active"] = int(b.active); before["active"] = bool(x["active"])
        if not ch: raise HTTPException(422, "Nothing to change")
        if uid == u["id"] and (ch.get("active") == 0 or role != x["role"]): raise HTTPException(409, "You cannot deactivate yourself or change your own role")
        with engine.begin() as c:
            if (ch.get("active") == 0 or role not in ADMIN) and x["role"] in ADMIN and x["active"]: guard_last(c, uid)
            c.execute(text("update app_user set " + ", ".join(f"{k}=:{k}" for k in ch) + " where id=:i"), dict(ch, i=uid))
            audit(c, u, "update", "app_user", uid, before, {k: v for k, v in dict(b).items() if v is not None})
        return one(UQ + " where u.id=:i", i=uid)

    @app.post("/api/platform/users/{uid}/password")
    def user_pw(uid: int, b: PwIn, u=Depends(need(ADMIN))):
        if not one("select id from app_user where id=:i", i=uid): raise HTTPException(404, "User not found")
        good_pw(b.password)
        with engine.begin() as c:
            c.execute(text("update app_user set password_hash=:p where id=:i"), dict(p=auth.hash_pw(b.password), i=uid))
            audit(c, u, "password_reset", "app_user", uid, None, None)
        return dict(id=uid, ok=True)

    # ---------------- health ----------------
    @app.get("/api/platform/health")
    def health_view(u=Depends(need(OPS))):
        d = many("select d.id, d.code, d.app_version ver, d.last_seen_at seen, l.name store, l.city from device d join location l on l.id=d.store_id where d.active=1")
        age = lambda x: (NOW - (x["seen"] if isinstance(x["seen"], datetime) else datetime.fromisoformat(str(x["seen"])))).total_seconds() / 3600
        for x in d: x["hours"] = round(age(x), 1)
        b = dict(online=sum(1 for x in d if x["hours"] < 6), delayed=sum(1 for x in d if 6 <= x["hours"] < 24), stale=sum(1 for x in d if x["hours"] >= 24))
        vers = {}
        for x in d: vers[x["ver"]] = vers.get(x["ver"], 0) + 1
        since = NOW - timedelta(hours=72)
        sy = one("select count(*) runs, sum(case when status='ok' then 1 else 0 end) ok, sum(case when status='partial' then 1 else 0 end) partial, sum(case when status='failed' then 1 else 0 end) failed, coalesce(sum(bills_pushed),0) pushed, coalesce(sum(bills_rejected),0) rejected, coalesce(max(queue_depth),0) maxq from sync_log where started_at>=:s", s=since)
        worst = many("select l.name store, l.city, count(*) runs, sum(case when s.status='ok' then 0 else 1 end) bad, max(s.queue_depth) q from sync_log s join device d on d.id=s.device_id join location l on l.id=d.store_id where s.started_at>=:s group by l.id order by bad desc, q desc limit 8", s=since)
        jobs = many("select id, kind, filename, status, rows_ok, rows_err, created_at from import_job order by id desc limit 5")
        fc = one("select run_at, method, wape from forecast_run order by id desc limit 1")
        lag = (TODAY - an.max_date).days
        return dict(devices=dict(total=len(d), **b, versions=sorted(vers.items(), key=lambda t: -t[1])), stale=sorted([x for x in d if x["hours"] >= 24], key=lambda x: -x["hours"])[:12], sync=dict(sy, hours=72, ok_pct=(sy["ok"] / sy["runs"]) if sy["runs"] else None), worst=worst, jobs=jobs, forecast=fc,
                    data=dict(through=str(an.max_date), lag_days=lag), note="Sync rows are simulated from device heartbeats. A device is stale after 24 hours without a heartbeat.")

    # ---------------- notifications and summary ----------------
    @app.get("/api/platform/notifications")
    def notes(u=Depends(me)):
        return many("select id, title, body, ref_type, ref_id, created_at, read_at from notification where user_id=:u order by created_at desc limit 40", u=u["id"])

    @app.post("/api/platform/notifications/read")
    def notes_read(b: ReadIn, u=Depends(me)):
        with engine.begin() as c:
            if b.ids: n = c.execute(text("update notification set read_at=:t where user_id=:u and read_at is null and id in (%s)" % ",".join(str(int(i)) for i in b.ids)), dict(t=NOW, u=u["id"])).rowcount
            else: n = c.execute(text("update notification set read_at=:t where user_id=:u and read_at is null"), dict(t=NOW, u=u["id"])).rowcount
        return dict(marked=n)

    @app.get("/api/platform/summary")
    def summary(u=Depends(me)):
        r = u["role"]; q = approvals("queue", "", 1, u)
        out = dict(role=r, waiting_on_me=q["mine_waiting"], open_requests=one("select count(*) n from approval_request where status='pending'")["n"], unread=one("select count(*) n from notification where user_id=:u and read_at is null", u=u["id"])["n"],
                   my_pending=one("select count(*) n from approval_request where status='pending' and requested_by=:u", u=u["id"])["n"])
        if r in AUDIT: out["audit30"] = one("select count(*) n from audit_log where ts>=:s", s=NOW - timedelta(days=30))["n"]
        if r in ADMIN: out["users"] = one("select count(*) n from app_user where active=1")["n"]
        if r in OPS:
            h = health_view(u); out["stale_devices"] = h["devices"]["stale"]; out["sync_ok_pct"] = h["sync"]["ok_pct"]
        return out
