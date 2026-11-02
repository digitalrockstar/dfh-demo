"""Landed cost and three-way match rules shared by the seed and the Module 3 API. Every rate here is an ASSUMPTION stated in tax_assumption."""
DEFAULTS = {
    "duty_pct_NDF": ("35", "Basic customs duty on nuts and dry fruits. ASSUMED, confirm with the customs house agent."),
    "duty_pct_DAT": ("35", "Basic customs duty on dates. ASSUMED."),
    "duty_pct_EXC": ("20", "Basic customs duty on DFH exclusives. ASSUMED."),
    "duty_pct_BER": ("30", "Basic customs duty on berries. ASSUMED."),
    "duty_pct_SED": ("20", "Basic customs duty on seeds. ASSUMED."),
    "duty_pct_SPC": ("25", "Basic customs duty on spices. ASSUMED."),
    "duty_pct_CHO": ("30", "Basic customs duty on chocolates. ASSUMED."),
    "duty_pct_GFT": ("30", "Basic customs duty on gift boxes. ASSUMED."),
    "sws_pct_of_duty": ("10", "Social welfare surcharge as a share of duty. ASSUMED."),
    "freight_sea_inr_per_kg": ("9", "Ocean freight per kg before the origin factor. ASSUMED."),
    "freight_air_inr_per_kg": ("140", "Air freight per kg before the origin factor. ASSUMED."),
    "insurance_pct": ("0.3", "Marine insurance as a share of goods value, added only on FOB prices. ASSUMED."),
    "clearing_pct": ("0.6", "Clearing agent fees as a share of assessable value. ASSUMED."),
    "port_inr_per_kg": ("2", "Port and CFS handling per kg. ASSUMED."),
    "inland_inr_per_kg": ("3", "Port or vendor to warehouse haulage per kg. ASSUMED."),
    "match_tolerance_pct": ("1", "Three-way match tolerance between invoice and goods accepted. ASSUMED."),
    "igst_note": ("Import GST is left out of landed cost", "Import GST is recoverable as input credit, so it is not part of landed cost."),
}
ORIGIN = {"USA": 1.4, "CHL": 1.5, "PER": 1.5, "AUS": 1.3, "TUR": .9, "ARE": .5, "SAU": .55, "JOR": .65, "EGY": .7, "TUN": .9, "IRN": .7, "AFG": .8, "UZB": .9, "VNM": .8, "CHN": .8}
COMPONENTS = ("freight", "insurance", "duty", "sws", "clearing", "port", "inland")
WEIGHT_BASED = ("freight", "port", "inland")
FLOW = {"sea": ["booked", "loaded", "in_transit", "at_port", "customs", "cleared", "delivered"],
        "air": ["booked", "loaded", "in_transit", "at_port", "customs", "cleared", "delivered"],
        "road": ["booked", "loaded", "in_transit", "delivered"]}
STAGE = {"booked": "Booked", "loaded": "Loaded", "in_transit": "In transit", "at_port": "At port", "customs": "In customs", "cleared": "Cleared", "delivered": "Delivered"}


class Rates:
    def __init__(self, rows=None):
        r = {k: v[0] for k, v in DEFAULTS.items()}
        r.update(rows or {})
        f = lambda k: float(r[k])
        self.duty = {k[9:]: float(v) for k, v in r.items() if k.startswith("duty_pct_")}
        self.sws, self.sea, self.air, self.ins = f("sws_pct_of_duty"), f("freight_sea_inr_per_kg"), f("freight_air_inr_per_kg"), f("insurance_pct")
        self.clear, self.port, self.inland, self.tol = f("clearing_pct"), f("port_inr_per_kg"), f("inland_inr_per_kg"), f("match_tolerance_pct")


def line_minor(qty, price, uom):
    return int(round(qty / 1000.0 * price)) if uom == "g" else int(round(qty * price))


def weight_kg(qty, uom, pack_g):
    return qty / 1000.0 if uom == "g" else qty * (pack_g or 0) / 1000.0


def components(goods_paise, kg, incoterm, cat, country, mode, domestic, R):
    """Landed cost extras in paise on top of the goods value. CIF prices already hold freight and insurance."""
    if domestic:
        return {"inland": R.inland * kg * 100}
    fr = ins = 0.0
    if incoterm == "FOB":
        fr = (R.air if mode == "air" else R.sea) * ORIGIN.get(country, 1.0) * kg * 100
        ins = goods_paise * R.ins / 100
    cif = goods_paise + fr + ins
    duty = cif * R.duty.get(cat, 30.0) / 100
    out = {"freight": fr, "insurance": ins, "duty": duty, "sws": duty * R.sws / 100, "clearing": cif * R.clear / 100, "port": R.port * kg * 100, "inland": R.inland * kg * 100}
    return {k: v for k, v in out.items() if v}


def allocate(totals, lines):
    """Share shipment component totals over PO lines. lines: dicts with value (paise) and kg. Returns extra paise per line."""
    tv = sum(l["value"] for l in lines) or 1; tk = sum(l["kg"] for l in lines) or 1
    return [sum(t * (l["kg"] / tk if k in WEIGHT_BASED else l["value"] / tv) for k, t in totals.items()) for l in lines]


def match(inv, ordered, accepted, debit, tol):
    """All amounts in the vendor currency minor unit. debit is credit already raised for rejected goods."""
    if accepted <= 0:
        return dict(state="awaiting", expected=0, variance=0, reason="Goods not received yet")
    net = inv - debit; var = net - accepted
    if abs(var) <= accepted * tol / 100:
        return dict(state="matched", expected=accepted, variance=int(var), reason=None)
    hi = inv > ordered * (1 + tol / 100); short = accepted < ordered * (1 - tol / 100)
    if var > 0:
        reason = ("Billed above the PO value and the accepted goods are short" if hi and short else "Billed above the PO price" if hi
                  else "Billed for the ordered quantity but less was accepted" if short else "Billed above the goods accepted")
    else:
        reason = "Billed below the value of goods accepted"
    return dict(state="mismatch", expected=accepted, variance=int(var), reason=reason)
