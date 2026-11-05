"""Single posting path into the stock ledger for modules outside Module 4 (POS sales, wastage, GRN receipts).
The balance always moves with a ledger row and never goes below zero."""
from fastapi import HTTPException
from sqlalchemy import text


def sync_position(c, loc, sid, delta):
    """Keep the demand stock position (warehouse level) in step with every ledger movement. Only rows that exist are touched."""
    c.execute(text("update stock_position set on_hand=case when on_hand + :d < 0 then 0 else on_hand + :d end where location_id=:l and sku_id=:s"), dict(d=delta, l=loc, s=sid))


def post(c, ts, loc, sid, bid, qty, mt, dtp, did, uid=None, device=None):
    cost = c.execute(text("select unit_cost_paise from batch where id=:b"), dict(b=bid)).scalar()
    cur = c.execute(text("select qty from stock_balance where location_id=:l and sku_id=:s and batch_id=:b"), dict(l=loc, s=sid, b=bid)).scalar()
    new = (cur or 0) + qty
    if new < 0: raise HTTPException(422, "Not enough stock in that batch")
    c.execute(text("insert into stock_ledger(ts, location_id, sku_id, batch_id, qty, movement_type, doc_type, doc_id, unit_cost_paise, user_id, device_id) values (:t,:l,:s,:b,:q,:m,:d,:i,:c,:u,:v)"),
              dict(t=ts, l=loc, s=sid, b=bid, q=qty, m=mt, d=dtp, i=str(did), c=cost, u=uid, v=device))
    if cur is None: c.execute(text("insert into stock_balance(location_id, sku_id, batch_id, qty, updated_at) values (:l,:s,:b,:q,:t)"), dict(l=loc, s=sid, b=bid, q=new, t=ts))
    else: c.execute(text("update stock_balance set qty=:q, updated_at=:t where location_id=:l and sku_id=:s and batch_id=:b"), dict(q=new, t=ts, l=loc, s=sid, b=bid))
    sync_position(c, loc, sid, qty)


def take_fefo(c, ts, loc, sid, qty, today, dtp, did, uid=None, device=None):
    """Sell from the earliest-expiring fresh batch first, then from expired batches if fresh stock runs out.
    A sale has already happened at the counter, so a shortfall is returned, not refused. Returns (list of (batch_id, qty), short_qty)."""
    rows = c.execute(text("select b.batch_id, b.qty, t.expiry_date from stock_balance b join batch t on t.id=b.batch_id where b.location_id=:l and b.sku_id=:s and b.qty>0 "
                          "order by (t.expiry_date<:d), t.expiry_date, b.batch_id"), dict(l=loc, s=sid, d=today)).fetchall()
    used, left = [], qty
    for bid, have, _ in rows:
        if left <= 0: break
        take = min(have, left); post(c, ts, loc, sid, bid, -take, "sale", dtp, did, uid, device); used.append((bid, take)); left -= take
    return used, max(left, 0)
