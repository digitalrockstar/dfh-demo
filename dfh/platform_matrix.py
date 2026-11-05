"""Role matrix for the Platform screen. Built from the role sets the API modules actually check, so it cannot drift from the code."""


def matrix(k, m, roles):
    W, D, F, C, P, S, I, H = (m[x] for x in "WDFCPSIH")
    allr = {r["code"] for r in roles}
    areas = [("Control Tower", k["CT_ROLES"], set()), ("SKU master", allr, k["SKU_WRITE"]), ("Store POS", S.HEALTH | S.BILL, S.BILL), ("Inventory and warehouse", I.READ, I.WRITE),
             ("Procurement and logistics", P.VIEW, P.PO_WRITE | P.INV_RELEASE), ("Wastage and shrink", W.VIEW, W.ENTER | W.APPROVE), ("Demand and replenishment", D.VIEW, D.APPROVE),
             ("Finance and tax", F.ANY, F.FIN), ("Customers and WhatsApp", C.OPS, C.MKT), ("People", H.HR | H.MGR, H.HR),
             ("Platform: approvals", {"ceo", "finance", "admin", "procurement"}, {"ceo", "finance"}), ("Platform: audit, entities, FX, health", {"ceo", "finance", "admin"}, {"ceo", "finance", "admin"}),
             ("Platform: users, rules", {"ceo", "admin"}, {"ceo", "admin"})]
    rows = [dict(area=a, levels={r["code"]: ("act" if r["code"] in act else "view" if r["code"] in view else "") for r in roles}) for a, view, act in areas]
    return dict(roles=roles, rows=rows, note="Built from the role sets in the API code. Store managers and warehouse users see only their own location. Act means can change or approve, View means read only.")
