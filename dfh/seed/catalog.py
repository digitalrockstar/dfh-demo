"""Catalog generator: ~1200 SKUs across the website's collections plus chocolates and spices.
All names are modeled on public product types. Prices and costs are synthetic."""
import math

CATS = [("NDF","Nuts and Dry Fruits",True),("DAT","Dates",True),("EXC","DFH Exclusives",True),
        ("BER","Berries",True),("SED","Seeds and More",True),("GFT","Gift Boxes",True),
        ("CHO","Chocolates",False),("SPC","Spices",False)]
SHARE = {"NDF":.48,"DAT":.16,"EXC":.07,"BER":.04,"SED":.06,"GFT":.08,"CHO":.07,"SPC":.04}
GM = {"NDF":.30,"DAT":.32,"EXC":.38,"BER":.38,"SED":.40,"GFT":.42,"CHO":.35,"SPC":.40}
FINISHED = {"EXC","CHO","SPC"}
BULK_CATS = {"NDF","DAT","SED","BER"}
DEFAULT_PACKS = {"NDF":[100,200,250,500,1000],"DAT":[250,500,1000,2000],"BER":[100,250,500],
                 "SED":[100,250,500,1000],"EXC":[250,500,1000],"CHO":[100,200]}
PF = {1:1.0,2:.8,5:.6,25:.3,50:.3,100:.7,150:.5,200:.6,250:1.0,300:.5,500:1.0,750:.4,1000:.55,2000:.2}
PADJ = {25:.08,50:.10,100:.07,150:.05,200:.03,250:.02,300:.01,750:-.01,1000:-.02,2000:-.04}
HSN_DESC = {"0801":"Coconuts, Brazil nuts, cashew nuts","0802":"Other nuts, fresh or dried","0804":"Dates, figs, pineapples, mangoes",
 "0806":"Grapes, dried (raisins)","0813":"Dried fruit, other","1204":"Linseed","1206":"Sunflower seeds","1207":"Other oil seeds",
 "1008":"Buckwheat, millet, quinoa","1806":"Chocolate and cocoa preparations","2008":"Fruit and nuts, prepared or preserved",
 "2106":"Food preparations, mixes","0904":"Pepper","0906":"Cinnamon","0907":"Cloves","0908":"Nutmeg, mace, cardamoms",
 "0909":"Seeds of anise, fennel, cumin","0910":"Ginger, saffron, bay leaf","KIT":"Gift boxes (composite supply, assumed)"}

PRODUCT_TEXT = """
Almonds California|NDF|USA|880|270|0802|Regular,Premium,Jumbo|10
Almonds Mamra|NDF|IRN,AFG|2400|240|0802|Regular|4
Almonds Australian|NDF|AUS|850|270|0802|Regular,Premium|5
Cashews Whole|NDF|VNM,IND|900|240|0801|W450,W320,W240,W180 Jumbo|10
Cashew Pieces|NDF|VNM,IND|650|240|0801|Regular|3
Pistachios Plain|NDF|USA,IRN,TUR|1700|240|0802|Regular,Jumbo|7
Pistachios Shelled|NDF|USA,IRN|2300|210|0802|Regular|3
Pistachios Roasted Salted|NDF|USA,IRN|1850|180|2008|Regular,Jumbo|6
Walnut Kernels|NDF|USA,CHL,IND|1050|210|0802|Halves,Quarters,Light Halves|8
Walnuts Inshell|NDF|IND,CHL,USA|520|270|0802|Regular,Jumbo|3
Brazil Nuts|NDF|PER|1900|210|0801|Regular|2.5
Hazelnuts|NDF|TUR,CHL|1500|240|0802|Regular|2
Pecans|NDF|USA|2200|210|0802|Regular|2
Macadamia Nuts|NDF|AUS|2900|240|0802|Regular|1.5
Pine Nuts Chilgoza|NDF|AFG|7200|180|0802|Regular|0.8
Peanuts Roasted|NDF|IND|180|180|2008|Regular,Blanched|2
Raisins Black|NDF|IND,AFG|350|270|0806|Regular,Seedless|5
Raisins Golden|NDF|IND,AFG,USA|420|270|0806|Regular,Jumbo|6
Raisins Green|NDF|AFG,IND|480|270|0806|Regular,Premium|4
Kishmish Afghan|NDF|AFG|620|240|0806|Regular|2
Apricots Dried|NDF|TUR,AFG|620|240|0813|Regular,Jumbo|4
Apricots Stuffed Almond|NDF|TUR|1150|180|0813|Regular|1.5
Figs Anjeer Dried|NDF|AFG,TUR|1250|240|0804|Regular,Jumbo,Premium|5
Prunes|NDF|USA,CHL|820|240|0813|Pitted,With Seed|2.5
Dried Mango|NDF|IND|900|180|0804|Regular|2.5
Dried Pineapple|NDF|IND|880|90|0804|Regular|1.5
Dried Kiwi|NDF|CHL|1500|120|0813|Regular|1
Dried Papaya|NDF|IND|700|120|0813|Regular|1
Apple Rings Dried|NDF|IND|1100|120|0813|Regular|1
Coconut Slices|NDF|IND|420|150|0801|Regular|1.5
Makhana Fox Nuts|NDF|IND|1100|180|0802|Regular,Jumbo|5
Mixed Dry Fruits|NDF|IND|900|180|0813|Regular,Premium|4
Breakfast Mix|NDF|IND|820|120|2106|Regular|3|100,250,500
Energy Mix|NDF|IND|880|120|2106|Regular|2.5|100,250,500
Trail Mix Fruit and Nut|NDF|IND|800|120|2106|Regular|3|100,250,500
Party Mix Roasted|NDF|IND|700|90|2106|Regular|2|100,250,500
Roasted Almonds Salted|NDF|USA|960|120|2008|Regular|3.5|100,250,500
Roasted Cashews Salted|NDF|VNM,IND|900|120|2008|Regular|3.5|100,250,500
Roasted Cashews Peri Peri|NDF|VNM,IND|940|120|2008|Regular|2.5|100,250,500
Roasted Almonds Masala|NDF|USA|990|120|2008|Regular|2|100,250,500
Roasted Pista Masala|NDF|USA,IRN|1900|120|2008|Regular|1.5|100,250,500
Smoked Almonds|NDF|USA|1000|120|2008|Regular|1.5|100,250,500
Honey Roasted Cashews|NDF|IND,VNM|960|120|2008|Regular|1.5|100,250,500
Cheese Cashews|NDF|IND,VNM|970|120|2008|Regular|1|100,250,500
Chilli Garlic Cashews|NDF|IND,VNM|950|120|2008|Regular|1|100,250,500
Dates Medjool|DAT|JOR,SAU,ARE|1100|300|0804|Regular,Jumbo,Super Jumbo|8
Dates Ajwa|DAT|SAU|1900|365|0804|Regular|4
Dates Safawi|DAT|SAU|900|300|0804|Regular|3
Dates Khalas|DAT|SAU,ARE|650|300|0804|Regular|3
Dates Sukkari|DAT|SAU|850|300|0804|Regular|4
Dates Mabroom|DAT|SAU|1050|300|0804|Regular|2
Dates Kimia|DAT|IRN,ARE|520|270|0804|Regular|2
Dates Deglet Noor|DAT|TUN|620|300|0804|Regular|3
Dates Zahidi|DAT|IRN,EGY|420|270|0804|Regular|2
Dates Dry Chuara|DAT|IND,SAU|520|300|0804|Regular|1.5
Dates Fresh Tray|DAT|SAU,JOR|980|45|0804|Regular|1.5|250,500
Dates Stuffed Almond|DAT|JOR,ARE|1500|150|2008|Regular|2|250,500
Dates Stuffed Pistachio|DAT|JOR,ARE|1900|150|2008|Regular|1.5|250,500
Dates Stuffed Walnut|DAT|JOR,ARE|1400|150|2008|Regular|1.2|250,500
Cranberries Dried|BER|USA,CHL|760|240|0813|Regular,Sweetened Reduced|3
Blueberries Dried|BER|USA,CHL|1800|240|0813|Regular|2
Goji Berries|BER|CHN|1100|240|0813|Regular|1.5
Dried Strawberries|BER|CHN,USA|1900|180|0813|Regular|1.5
Mulberries Dried|BER|AFG,UZB|950|240|0813|White,Black|1.5
Dried Cherries|BER|USA,TUR|1700|210|0813|Regular|1
Blackcurrant Dried|BER|CHL,UZB|1500|210|0813|Regular|0.8
Raspberries Freeze Dried|BER|USA|3500|270|0813|Regular|0.6
Mixed Berries|BER|USA,CHL|1300|210|0813|Regular|2
Chia Seeds|SED|PER|420|365|1207|Regular|4
Flax Seeds|SED|IND|160|365|1204|Brown,Golden|3
Pumpkin Seeds|SED|CHN,IND|480|270|1207|Regular,Roasted|3.5
Sunflower Seeds|SED|IND,UZB|260|270|1206|Regular,Roasted|3
Watermelon Seeds|SED|IND|520|270|1207|Regular|1.5
Sesame Seeds|SED|IND|220|365|1207|White,Black|2
Hemp Seeds|SED|CHN|1300|270|1207|Regular|0.8
Basil Sabja Seeds|SED|IND|380|365|1207|Regular|1.2
Melon Seeds Magaz|SED|IND|700|270|1207|Regular|1
Mixed Seeds|SED|IND|450|270|2106|Regular,Premium|3
Breakfast Mix Seeds|SED|IND|520|240|2106|Regular|2.5
Poppy Seeds Khus Khus|SED|UZB,IND|1100|365|1207|Regular|0.8
Quinoa|SED|PER|520|365|1008|White,Red|1.2
DFH Select Mamra Almonds|EXC|IRN,AFG|2800|240|0802|Regular|3
DFH Select Plain Pista|EXC|IRN,USA|2000|240|0802|Regular|3
DFH Select Brazil Nuts|EXC|PER|2100|210|0801|Regular|1.5
DFH Select Walnut Kernels|EXC|USA,CHL|1200|210|0802|Regular|2.5
DFH Select Medjool Dates|EXC|JOR,SAU|1500|300|0804|Regular|3
DFH Royal Mix|EXC|IND|1500|180|2106|Regular|3.5
DFH Signature Trail Mix|EXC|IND|1000|150|2106|Regular|2
DFH Breakfast Seeds Mix|EXC|IND|650|240|2106|Regular|2
DFH Roasted Pista Reserve|EXC|IRN,USA|2200|150|2008|Regular|2
DFH Jumbo Cashews|EXC|VNM,IND|1200|240|0801|Regular|3
DFH Premium Figs|EXC|AFG,TUR|1700|240|0804|Regular|1.5
DFH Apricot Reserve|EXC|TUR|950|240|0813|Regular|1
DFH Berry Blend|EXC|USA,CHL|1500|210|0813|Regular|1
DFH Diwali Special Assorted|EXC|IND|1600|150|2106|Regular|2
DFH Mega Nutty Mix|EXC|IND|1100|150|2106|Regular|1.5
DFH Salted Almonds Reserve|EXC|USA|1300|120|2008|Regular|1.5
DFH Sugar Free Mix|EXC|IND|1250|150|2106|Regular|1
DFH Kids Mix|EXC|IND|1000|150|2106|Regular|1
DFH Kesar Almonds|EXC|IND,USA|1700|120|2008|Regular|1
DFH Dark Choco Almonds|EXC|IND|1800|150|1806|Regular|1.5
DFH Choco Dry Fruit Mix|EXC|IND|1900|150|1806|Regular|1
DFH Honey Dates Almond|EXC|JOR|1700|120|2008|Regular|0.8
DFH Immunity Mix|EXC|IND|1100|150|2106|Regular|1
DFH Fasting Mix Vrat|EXC|IND|900|150|2106|Regular|1.5
Saffron Kashmiri Mongra|SPC|IND|260000|540|0910|Regular|2.5|1,2,5
Saffron Iranian Sargol|SPC|IRN|180000|540|0910|Regular|2|1,2,5
Cardamom Green|SPC|IND|2400|540|0908|Regular|3.5|50,100,250
Cloves|SPC|IND|900|540|0907|Regular|1.5|50,100,250
Cinnamon Sticks|SPC|IND|650|540|0906|Regular|1.5|50,100,250
Black Pepper|SPC|IND|750|540|0904|Regular|2|100,250,500
Star Anise|SPC|CHN|1100|540|0909|Regular|1|25,50,100
Nutmeg|SPC|IND|1800|540|0908|Regular|1|25,50,100
Mace Javitri|SPC|IND|3500|540|0908|Regular|0.8|25,50
Bay Leaf|SPC|IND|280|540|0910|Regular|0.6|50,100
Dry Ginger|SPC|IND|520|365|0910|Regular|0.8|100,250
Fennel Saunf|SPC|IND|420|540|0909|Regular|1.2|100,250,500
Cumin Jeera|SPC|IND|480|540|0909|Regular|1.2|100,250,500
Cardamom Black|SPC|IND|1800|540|0908|Regular|0.8|50,100
"""
CHO_TYPES = {"Dark 70":1.05,"Milk":1.0,"White":.98,"Dark Sea Salt":1.08}
CHO_FILL = {"Almond":1300,"Hazelnut":1500,"Cranberry":1250,"Roasted Cashew":1350,"Pistachio":1900,
            "Orange Peel":1200,"Salted Caramel":1250,"Fig":1450,"Date":1350}
THEMES = [("Classic",1.5),("Premium",1.8),("Royal",1.6),("Celebration",1.4),("Diwali Special",3.0),("Wedding",1.2),
          ("Corporate Elite",1.4),("Healthy Bites",1.2),("Choco Delight",1.3),("Sugar Free",.8),("Festive Hamper",2.0),
          ("Eid Mubarak",1.2),("Rakhi Special",1.5),("Navratri Vrat",1.0),("Thank You",.8),("Housewarming",.6)]


def ean13(n12):
    s = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(n12))
    return n12 + str((10 - s % 10) % 10)


def pack_label(g):
    return f"{g / 1000:g}kg" if g >= 1000 else f"{g}g"


def _products(rng):
    P = []
    for line in PRODUCT_TEXT.strip().splitlines():
        f = line.split("|")
        P.append(dict(name=f[0], cat=f[1], origins=f[2], cost_kg=float(f[3]), shelf=int(f[4]), hsn=f[5],
                      grades=f[6].split(","), pop=float(f[7]),
                      packs=[int(x) for x in f[8].split(",")] if len(f) > 8 else None))
    combos = [(t, fl) for t in CHO_TYPES for fl in CHO_FILL]
    rng.shuffle(combos)
    for t, fl in combos[:28]:
        P.append(dict(name=f"{t} Chocolate with {fl}", cat="CHO", origins="IND",
                      cost_kg=CHO_FILL[fl] * CHO_TYPES[t], shelf=240, hsn="1806", grades=["Regular"],
                      pop=round(rng.uniform(.8, 2.5), 2), packs=None))
    return P


def build_catalog(rng, total=1200, n_kits=85):
    P = _products(rng)
    cat_order = {c[0]: i for i, c in enumerate(CATS)}
    groups = []
    for pi, p in enumerate(P):
        for gi, g in enumerate(p["grades"]):
            cost = p["cost_kg"] * (1 + 0.12 * gi) if len(p["grades"]) > 1 else p["cost_kg"]
            groups.append(dict(pi=pi, grade=g, cost_kg=cost, cat=p["cat"], loose=p["cat"] not in FINISHED,
                               pop=p["pop"] / math.sqrt(len(p["grades"])),
                               packs=list(p["packs"] or DEFAULT_PACKS.get(p["cat"], [250, 500]))))
    target = total - n_kits
    count = lambda: sum((1 if g["loose"] else 0) + len(g["packs"]) for g in groups)
    while count() > target:
        g = min((g for g in groups if len(g["packs"]) > 1), key=lambda g: g["pop"])
        g["packs"].remove(min(g["packs"], key=lambda k: PF.get(k, .6)))
    for pk in (750, 50, 200, 300, 150, 2000):
        for g in sorted(groups, key=lambda g: -g["pop"]):
            if count() >= target:
                break
            if g["cat"] in BULK_CATS and pk not in g["packs"]:
                g["packs"].append(pk)
    assert count() == target, count()

    categories = [dict(id=i + 1, code=c, name=n, site_collection=s) for i, (c, n, s) in enumerate(CATS)]
    products = [dict(id=i + 1, code=f"P{i + 1:03d}", name=p["name"], category_id=cat_order[p["cat"]] + 1,
                     origins=p["origins"], hsn=p["hsn"], shelf_life_days=p["shelf"],
                     storage="Cool and dry" if p["shelf"] <= 120 else "Ambient", is_fresh=p["shelf"] <= 120,
                     popularity=p["pop"]) for i, p in enumerate(P)]
    skus, sid = [], 0

    def add(**k):
        nonlocal sid
        sid += 1
        k.update(id=sid, code=f"{k['cat']}{sid:04d}", barcode=ean13("29" + f"{sid:010d}"), status="active")
        skus.append(k)
        return sid

    for g in sorted(groups, key=lambda g: (cat_order[g["cat"]], g["pi"])):
        p, cat = P[g["pi"]], g["cat"]
        nm = p["name"] + ("" if g["grade"] == "Regular" else " " + g["grade"])
        bulk_id = None
        if g["loose"]:
            landed = g["cost_kg"] * 1.12
            ppk = landed / (1 - (GM[cat] - .02))
            bulk_id = add(cat=cat, product_id=g["pi"] + 1, name=nm + " Loose", grade=g["grade"], pack_g=None,
                          base_uom="g", procurement_type="bulk", bulk_sku_id=None, shelf_life_days=p["shelf"],
                          hsn=p["hsn"], mrp_paise=None, price_per_kg_paise=int(round(ppk / 10) * 10 * 100),
                          std_cost_paise=int(round(landed * 100)), popularity=g["pop"] * 1.4 * rng.lognormvariate(0, .2),
                          origins=p["origins"], raw_cost=g["cost_kg"], price_per="kg")
        for pk in sorted(g["packs"]):
            kg = pk / 1000
            cost_pack = g["cost_kg"] * 1.12 * kg + 3 + 0.004 * pk
            mrp = cost_pack / (1 - (GM[cat] + PADJ.get(pk, 0)))
            mrp = math.ceil(mrp / 5) * 5 if mrp >= 50 else math.ceil(mrp)
            add(cat=cat, product_id=g["pi"] + 1, name=f"{nm} {pack_label(pk)}", grade=g["grade"], pack_g=pk,
                base_uom="ea", procurement_type="repacked" if g["loose"] else "finished", bulk_sku_id=bulk_id,
                shelf_life_days=p["shelf"], hsn=p["hsn"], mrp_paise=int(mrp * 100), price_per_kg_paise=None,
                std_cost_paise=int(round(cost_pack * 100)),
                popularity=g["pop"] * PF.get(pk, .6) * (0.9 if g["loose"] else 1.3) * rng.lognormvariate(0, .2),
                origins=p["origins"], raw_cost=g["cost_kg"] * kg, price_per="ea")

    # gift boxes (kits)
    comps = [s for s in skus if s["base_uom"] == "ea" and s["cat"] in ("NDF", "DAT", "CHO", "BER")
             and s["pack_g"] in (100, 200, 250, 500) and s["shelf_life_days"] > 120]
    combos = [(t, w, sz, c) for t, w in THEMES for sz in (250, 500, 750, 1000, 1500)
              for c in ("Gold", "Maroon", "Green", "Ivory", "Blue")]
    rng.shuffle(combos)
    kit_bom, gcount, seen = [], 0, set()
    kit_start = sid
    for t, w, sz, c in combos:
        if gcount >= n_kits:
            break
        pool = rng.sample(comps, 12)
        pick, tot = [], 0
        for s in pool:
            if tot >= sz * .9 or len(pick) >= 6:
                break
            pick.append(s); tot += s["pack_g"]
        if len(pick) < 3:
            continue
        gcount += 1
        pi = len(products) + 1
        name = f"{t} Gift Box {c} {pack_label(sz)}"
        products.append(dict(id=pi, code=f"P{pi:03d}", name=name, category_id=cat_order["GFT"] + 1, origins="IND",
                             hsn="KIT", shelf_life_days=min(s["shelf_life_days"] for s in pick), storage="Ambient",
                             is_fresh=False, popularity=w))
        cost = sum(s["std_cost_paise"] for s in pick) + int((40 + sz * .12) * 100)
        price = math.ceil(cost / (1 - GM["GFT"]) / 100 / 10) * 10
        kid = add(cat="GFT", product_id=pi, name=name, grade=c, pack_g=tot, base_uom="ea", procurement_type="kit",
                  bulk_sku_id=None, shelf_life_days=min(s["shelf_life_days"] for s in pick), hsn="KIT",
                  mrp_paise=price * 100, price_per_kg_paise=None, std_cost_paise=cost, popularity=w * rng.uniform(.7, 1.3),
                  origins="IND", raw_cost=0, price_per="ea")
        kit_bom += [dict(kit_sku_id=kid, component_sku_id=s["id"], qty=1) for s in pick]
    tax = [dict(hsn=h, description=HSN_DESC.get(h, h), rate_loose_pct=18.0 if h in ("1806", "KIT") else 5.0,
                rate_packed_pct=18.0 if h in ("1806", "KIT") else 5.0, assumed=True)
           for h in sorted({s["hsn"] for s in skus})]
    return categories, products, skus, kit_bom, tax
