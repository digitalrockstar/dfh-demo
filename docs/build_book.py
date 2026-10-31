from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, NextPageTemplate, KeepTogether)
from reportlab.graphics.shapes import Drawing, Rect, String, Line

W, H = landscape(A4)
M = 36
INK = colors.HexColor("#0F172A")
TEAL = colors.HexColor("#0F766E")
AMBER = colors.HexColor("#F59E0B")
BG = colors.HexColor("#F8FAFC")
GREY = colors.HexColor("#64748B")
LINE = colors.HexColor("#E2E8F0")

def S(name, **kw):
    base = dict(fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK, alignment=TA_LEFT)
    base.update(kw)
    return ParagraphStyle(name, **base)

H1 = S("H1", fontName="Helvetica-Bold", fontSize=22, leading=26, spaceAfter=4)
H2 = S("H2", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=TEAL, spaceBefore=6, spaceAfter=3)
BODY = S("BODY")
SMALL = S("SMALL", fontSize=8.5, leading=11.5)
CELL = S("CELL", fontSize=8.5, leading=11.2)
CELLB = S("CELLB", fontName="Helvetica-Bold", fontSize=8.5, leading=11.2)
HEAD = S("HEAD", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.white)
TAG = S("TAG", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=GREY)
BUL = S("BUL", fontSize=8.7, leading=11.6, leftIndent=10, bulletIndent=0, spaceAfter=1.5)

def P(t, st=BODY): return Paragraph(t, st)
def bullets(items): return [Paragraph(i, BUL, bulletText="\u2022") for i in items]

def tbl(data, colw, head=True, zebra=True):
    rows = []
    for ri, r in enumerate(data):
        row = []
        for c in r:
            if isinstance(c, str):
                st = HEAD if (head and ri == 0) else CELL
                row.append(Paragraph(c, st))
            else:
                row.append(c)
        rows.append(row)
    t = Table(rows, colWidths=colw, repeatRows=1 if head else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("GRID", (0, 0), (-1, -1), 0.4, LINE),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
             ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]
    if head:
        style.append(("BACKGROUND", (0, 0), (-1, 0), INK))
    if zebra:
        for i in range(1 if head else 0, len(rows)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), BG))
    t.setStyle(TableStyle(style))
    return t

def page_title(title, sub=None):
    out = [P(title, H1)]
    if sub:
        out.append(P(sub, S("sub", fontSize=10, leading=14, textColor=GREY, spaceAfter=6)))
    out.append(Spacer(1, 4))
    return out

FW = W - 2 * M

def module(num, name, depth, purpose, screens, flows, kpis, edges, replaces=None):
    out = [P(f"{num}. {name}", H1),
           P(f"Demo depth: {depth}" + (f" &nbsp;|&nbsp; {replaces}" if replaces else ""), TAG),
           Spacer(1, 4), P(purpose, BODY), Spacer(1, 8)]
    def box(title, items):
        return [P(title, H2)] + bullets(items)
    grid = [[box("Key screens", screens), box("Core workflows", flows)],
            [box("Metrics it produces", kpis), box("Edge cases covered", edges)]]
    t = Table(grid, colWidths=[FW / 2, FW / 2])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("BOX", (0, 0), (-1, -1), 0.4, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    out.append(t)
    out.append(PageBreak())
    return out

# ---------------- page templates ----------------
def cover_bg(c, doc):
    c.saveState()
    c.setFillColor(INK); c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(AMBER); c.rect(M, H - 150, 90, 5, stroke=0, fill=1)
    c.restoreState()

def main_bg(c, doc):
    c.saveState()
    c.setFont("Helvetica", 8); c.setFillColor(GREY)
    c.drawString(M, H - 24, "Dry Fruit House Operations Platform  |  Product plan, draft v1")
    c.drawRightString(W - M, 18, f"Page {c.getPageNumber()}")
    c.drawString(M, 18, "Demo plan. All figures in the demo are synthetic.")
    c.setStrokeColor(AMBER); c.setLineWidth(1.2); c.line(M, H - 30, W - M, H - 30)
    c.restoreState()

doc = BaseDocTemplate("/mnt/user-data/outputs/DFH_Product_Plan_v1.pdf", pagesize=(W, H),
                      leftMargin=M, rightMargin=M, topMargin=M + 8, bottomMargin=M,
                      title="Dry Fruit House Operations Platform: Product Plan", author="Akshay")
doc.addPageTemplates([
    PageTemplate("cover", [Frame(M, M, FW, H - 2 * M, id="c")], onPage=cover_bg),
    PageTemplate("main", [Frame(M, M, FW, H - 2 * M - 14, id="m")], onPage=main_bg)])

st = []
# ---------------- cover ----------------
white_big = S("wb", fontName="Helvetica-Bold", fontSize=34, leading=40, textColor=colors.white)
white_mid = S("wm", fontSize=14, leading=20, textColor=colors.HexColor("#CBD5E1"))
white_sm = S("ws", fontSize=10, leading=14, textColor=colors.HexColor("#94A3B8"))
st += [Spacer(1, 120), P("Dry Fruit House<br/>Operations Platform", white_big), Spacer(1, 14),
       P("Product plan for an in-house POS, inventory, procurement, finance and analytics stack for a 500 store dry fruit retail chain", white_mid),
       Spacer(1, 60), P("Prepared by Akshay &nbsp;|&nbsp; Draft v1 &nbsp;|&nbsp; 31 October 2026", white_sm),
       Spacer(1, 4), P("This book is the plan. The working demo runs on synthetic data modeled on the public catalog.", white_sm),
       NextPageTemplate("main"), PageBreak()]

# ---------------- context ----------------
st += page_title("Where we start", "What we know, what we assume, and the thesis for the demo")
left = [P("What we know", H2)] + bullets([
    "Multi-store dry fruit and nut retailer based in Bengaluru, with stores across India and a possible Middle East presence.",
    "The public site lists six collections: Nuts and Dry Fruits, Dates, DFH Exclusives, Berries, Seeds and More, and Gift Boxes. It also carries bulk ordering, locations and careers pages. The page title mentions chocolates and spices.",
    "Stores bill on an older POS. Getting reports out of it automatically is hard, so finance reconciles by hand.",
    "No organized WMS. Analytics is manual. Oracle Cloud ERP is under discussion.",
    "Goods are imported and bought domestically from many vendors. The same SKU can come from several vendors at different costs across months.",
    "Round 2 audience is likely the CEO."]) + [P("What we assume for the demo", H2)] + bullets([
    "About 500 stores, 20 warehouses, 1,200 SKUs, shelf lives from a few weeks (fresh and packed) to a year.",
    "Returns are rare for food, so the demo has no returns flow. Wastage is modeled in full.",
    "Store expansion is out of scope."])
right = [P("The thesis", H2), P(
    "The pain looks like three problems: store data is stuck inside a POS, stock is not traceable by batch and expiry, and finance rebuilds the picture by hand every month. A full ERP rollout solves a bigger problem than the one in front of them, and it takes a long time to land.", BODY),
    Spacer(1, 5), P(
    "The proposal is a lean platform they own. It has an offline-first POS for stores, an order and warehouse system with procurement and inbound logistics tracking, finance and GST reconciliation, and analytics on top. Every transaction lands in one database that the CEO and finance can query on day one.", BODY),
    Spacer(1, 5), P("Where Oracle still fits", H2), P(
    "General ledger, payroll and group consolidation are mature ERP territory. The platform exports clean journals and masters, so it works with Oracle, Tally or anything else later. The pitch is to run operations on a system they control now, and to connect an ERP when the business needs one.", BODY),
    Spacer(1, 5), P("What would change this plan", H2), bullets([
    "If their POS vendor can give a nightly database export, Phase 1 can start with analytics before any POS replacement.",
    "If they already have a sound finance stack, the finance module shrinks to reconciliation only."])]
t = Table([[left, right]], colWidths=[FW * 0.52, FW * 0.48])
t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("RIGHTPADDING", (0, 0), (0, 0), 16)]))
st += [t, PageBreak()]

# ---------------- scope map ----------------
st += page_title("Scope map", "A POS foundation plus the ten modules agreed earlier. Depth shows how much is live in the demo.")
rows = [["#", "Module", "What it solves", "Demo depth"],
        ["F", "Store POS, offline first", "Replaces dependence on the legacy POS. Bills, cash, GST invoices and stock movement captured in their own database, working without internet.", "Deep"],
        ["1", "Control Tower", "One screen for the CEO: sales, margin, stock, wastage, exceptions, store league table.", "Deep"],
        ["2", "SKU master", "Single catalog with packs, HSN, GST, shelf life, batch MRP, kits, price lists.", "Deep"],
        ["3", "Vendors, procurement and inbound logistics", "Vendor price book, landed cost, PO to shipment to GRN tracking, vendor scorecards.", "Deep"],
        ["4", "Inventory and warehouse (OMS and WMS)", "Batch and expiry stock ledger, FEFO, transfers, repacking, store indents, counts, bulk orders.", "Deep"],
        ["5", "Wastage and shrink", "Reason coded loss capture, near-expiry actions, shrink by location, SKU and vendor.", "Deep"],
        ["6", "Demand and replenishment", "Seasonal forecast, reorder suggestions, festive planning, assortment by store cluster.", "Medium"],
        ["7", "Finance and tax reconciliation", "Day-close reconciliation, GST working data, ITC matching, payables, stock valuation, journal export.", "Deep"],
        ["8", "Customers and WhatsApp commerce", "Customer 360, loyalty, segments, WhatsApp ordering, corporate gifting enquiries.", "Light"],
        ["9", "HR basic", "Org chart, onboarding, attendance, rosters, leave, birthdays, job postings.", "Light"],
        ["10", "Platform", "Roles, audit, approvals, notifications, imports, multi-entity and multi-currency.", "Medium"]]
st += [tbl(rows, [28, 190, FW - 28 - 190 - 70, 70]), Spacer(1, 8),
       P("Order of build follows the depth column. If time runs short, modules 8, 9 and 6 are shown as designed screens with seeded data and the rest of the demo stays intact.", SMALL),
       PageBreak()]

# ---------------- architecture ----------------
st += page_title("Architecture", "One modular backend, one database, a PWA for stores, and an analytics layer on the same data")
arch = [["Layer", "Choice", "Why"],
        ["Store device", "Progressive web app on a tablet or low-cost PC. IndexedDB for local data. Service worker for offline and background sync.", "No app store, quick rollout, works on hardware they already own."],
        ["Sync", "Append-only outbox on the device. Idempotency key per bill. Server acknowledges and dedupes. Pull-only catalog and price versions.", "Bills never edit in place, so conflicts do not arise for sales."],
        ["Backend", "Python 3.12, FastAPI, SQLAlchemy, Pydantic. Modular monolith, one module per domain above.", "Fast to build, easy for a small team to own."],
        ["Database", "PostgreSQL. Stock as an append-only ledger. Money in paise, quantity in grams or units.", "Every rupee and every gram traceable to a document."],
        ["Jobs", "Scheduled jobs for nightly rollups, expiry alerts, forecasts, reconciliation.", "Keeps heavy analytics off the billing path."],
        ["Analytics", "Materialized views for dashboards. DuckDB and Parquet for the large synthetic history.", "Fast drilldowns without a separate warehouse in phase 1."],
        ["Frontend", "React with Vite and Tailwind. Two densities: touch-friendly POS and compact back office.", "One design system, two usage modes."],
        ["Hosting", "Render for app, Neon or managed Postgres for data. Paid tiers for the demo week to avoid cold starts.", "Free tiers sleep and a sleeping demo costs credibility."],
        ["Integration", "CSV and JSON exports, REST API with keys, journal export for Oracle or Tally, GSP hook for e-invoice and e-way bill in phase 2.", "Works alongside any future ERP."]]
st += [tbl(arch, [90, 380, FW - 470]), PageBreak()]

# ---------------- POS ----------------
st += [P("Foundation: Store POS, offline first", H1),
       P("Demo depth: Deep &nbsp;|&nbsp; Replaces the legacy POS in pilot stores", TAG), Spacer(1, 4),
       P("The goal is to show that a POS can be built in house, work through internet drops, and give the company direct access to its own sales data. The demo will bill, lose connectivity on stage, keep billing, and sync when the connection returns.", BODY), Spacer(1, 6)]
def box2(title, items): return [P(title, H2)] + bullets(items)
pos1 = [[box2("Billing", [
    "Barcode scan, search and quick keys for top sellers.",
    "Loose items by weight: price per kg, grams entered, live line total.",
    "Packed items by scan. Gift boxes as kits with component deduction.",
    "Hold and recall bills. Line and bill discounts with reason and approval limits.",
    "Coupons and loyalty redemption. Customer lookup by phone.",
    "Split payments across cash, UPI, card.",
    "GST invoice with HSN, tax split and rounding. Print, WhatsApp or SMS receipt."]),
    box2("Control", [
    "Cashier PIN login and roles. Price override limited to managers.",
    "Void and cancel with reason and approval. Full audit trail.",
    "Day open and close with cash count and variance.",
    "X and Z reports. Shift handover. Cash drops and petty cash.",
    "Business date logic for stores that close after midnight."])],
    [box2("Store tasks beyond billing", [
    "Stock lookup for the store and nearby stores.",
    "Receive transfers and deliveries by scan or quantity.",
    "Wastage entry with reason and photo.",
    "Indent to warehouse. Stock count mode.",
    "Sync health shown on the screen at all times."]),
     box2("Hardware plan", [
    "Thermal printer over USB or network (ESC/POS).",
    "Barcode scanner as keyboard input.",
    "Weighing scale: manual entry first, serial or Bluetooth read as a later step.",
    "Cash drawer kick. UPI QR display on a second screen or on paper.",
    "Runs on an Android tablet or a modest Windows PC."])]]
t = Table(pos1, colWidths=[FW / 2, FW / 2])
t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOX", (0, 0), (-1, -1), 0.4, LINE),
                       ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE), ("LEFTPADDING", (0, 0), (-1, -1), 8),
                       ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
st += [t, PageBreak()]

st += [P("POS: offline design and edge cases", H1), Spacer(1, 4)]
pos2 = [[box2("How offline works", [
    "Catalog, price versions, store stock snapshot and recent customers are cached on the device.",
    "Each bill is saved locally first, with a UUID idempotency key. Drafts survive a power cut.",
    "Invoice numbers come from a series reserved per device and financial year, so numbering stays continuous and GST compliant while offline.",
    "A background queue pushes bills when online, with retry and backoff. The server rejects duplicates by key.",
    "Sales are append only. Corrections are a void plus a new bill, never an edit.",
    "Device clock is recorded along with server receive time, and large skew is flagged.",
    "A sync dashboard shows last sync age and queue size per store."]),
    box2("Edge cases covered", [
    "Internet drops mid-bill, and returns mid-bill.",
    "Two billing counters in one store with separate series.",
    "Price changed at head office while a store is offline: sale uses the price version the device held, and the difference is flagged.",
    "Item sells beyond system stock: allowed with a negative stock flag for the manager.",
    "UPI shows success on the phone but not on the terminal: payment pending state with later match.",
    "Customer adds items after payment starts: bill locks and a new bill opens.",
    "Festive peak with long queues: hold, quick keys, keyboard shortcuts.",
    "Store with weak network for days: local retention with a clear warning when the queue grows."])],
    [box2("Where I would be careful", [
    "Cost savings must include hardware, rollout, support and a person who owns uptime. Licence fees are one line of the cost.",
    "Printers, scanners, scales and payment terminals decide how smooth the first week in a store feels. Pilot before promising.",
    "E-invoicing and e-way bill thresholds and rules need confirmation with their CA before any claim in the demo.",
    "Run the new POS next to the old one in 3 to 5 stores for a month and compare day totals before any cutover."]),
     box2("Pilot path", [
    "Phase A: shadow mode in 3 to 5 stores, both POS running, daily totals compared.",
    "Phase B: 25 stores on the new POS for one festive cycle.",
    "Phase C: wave rollout by city with a rollback option per store."])]]
t = Table(pos2, colWidths=[FW / 2, FW / 2])
t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOX", (0, 0), (-1, -1), 0.4, LINE),
                       ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE), ("LEFTPADDING", (0, 0), (-1, -1), 8),
                       ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
st += [t, PageBreak()]

# ---------------- modules ----------------
st += module(1, "Control Tower", "Deep",
    "A single page for the CEO and regional heads that answers one question each morning: what happened yesterday, and what needs attention today. Every number drills down to store, SKU and bill.",
    ["Executive summary with sales, gross margin after wastage, stock value, stock cover, wastage, stockout rate.",
     "Store league table with filters for city, cluster and format.",
     "Exceptions inbox: stores not synced, negative stock, cash variance, near-expiry value, price mismatch.",
     "Drilldown from KPI to store to SKU to bill.",
     "Warehouse view with stock, ageing and dispatch status."],
    ["Daily 7 am snapshot sent to WhatsApp or email for leadership.",
     "Exception to owner assignment with status and due date.",
     "Period compare: week on week, month on month, same festival last year.",
     "Saved views per role."],
    ["Net sales, gross margin, gross margin after wastage.",
     "Average bill value, units per bill, sales per store per day.",
     "Stock cover in days, sell-through, stockout days.",
     "Wastage as percent of sales and of purchase cost.",
     "Cash variance and sync lag by store."],
    ["Stores that sync late show totals as of a timestamp, so the headline never silently understates.",
     "Currency toggle for INR and AED with a stated conversion date.",
     "Stores opened or closed mid-period are handled in like-for-like comparisons.",
     "Festival shifts, such as Ramadan moving by about 11 days a year, are handled in compares."])

st += module(2, "SKU master", "Deep",
    "One clean catalog. A SKU is a product at a grade, origin and pack size. The catalog follows the website structure, with six collections plus chocolates and spices, and extends it with the operating fields stores and finance need.",
    ["Catalog list with search, category tree and status.",
     "SKU detail: attributes, packs, tax, shelf life, barcodes, price history.",
     "Kit builder for gift boxes with a bill of materials.",
     "Price lists by city, cluster and store.",
     "Bulk import with validation and error report."],
    ["Create SKU from a product template across pack sizes.",
     "Approval for new SKUs and price changes.",
     "Lifecycle: draft, active, restricted, delisted.",
     "Barcode and label generation."],
    ["Active SKUs by category, and long-tail share.",
     "Price change log and margin impact.",
     "SKUs with no sale in 60 days by store cluster."],
    ["Bulk to pack conversion: 25 kg sack to 250 g and 500 g packs, with yield loss.",
     "MRP lives on the batch. Old packed stock sells at its printed MRP while new batches carry the new one.",
     "GST rate and HSN with effective dates. Rates stay configurable and are confirmed with their CA.",
     "Duplicate and near-duplicate SKU detection.",
     "Seasonal SKUs that switch on and off by date."])

st += module(3, "Vendors, procurement and inbound logistics", "Deep",
    "Many vendors supply many SKUs, and cost moves by month. This module holds the price book, builds the landed cost, tracks every purchase from order to receipt, and gives finance the paperwork trail it needs for tax.",
    ["Vendor master with documents, currency, payment terms.",
     "Price book: vendor by SKU with effective dates, currency, Incoterm, MOQ, lead time.",
     "Landed cost calculator: price, FX, freight, insurance, duty, clearing, handling, inland transport.",
     "PO list and detail with approval status.",
     "Shipment tracker: booked, at port, in customs, cleared, in transit, received.",
     "GRN screen with batch, expiry, MRP and quality check.",
     "Vendor scorecard and SKU vendor comparison."],
    ["PO from replenishment suggestions or manually.",
     "Approval by value band.",
     "Split shipments across warehouses.",
     "Three-way match: PO, GRN, vendor invoice.",
     "Debit note on quality rejection."],
    ["Landed cost per kg by vendor and month.",
     "Lead time and its spread, fill rate, price variance against PO.",
     "Quality rejection percent by vendor.",
     "Open commitments and payables ageing."],
    ["FX moves between PO date and payment date.",
     "Duty changes while goods are in transit.",
     "Short landing in a container and partial receipts.",
     "Vendor substitution when a SKU is short.",
     "Advance payments and letters of credit.",
     "IGST on imports recorded from the bill of entry for credit claims."])

st += module(4, "Inventory and warehouse (OMS and WMS)", "Deep",
    "The core of the lean ERP replacement. Stock is an append-only ledger by location and batch, so every kilo has a history. Orders move through allocation, picking, dispatch and receipt with status visible to stores and finance.",
    ["Stock by location, batch and expiry. Ageing buckets.",
     "Location tree: country, city, warehouse or store, zone, rack, bin.",
     "Transfer and dispatch board with in-transit state.",
     "Store indent inbox with allocation and picking lists (FEFO).",
     "Repack job screen: input weight, output packs, yield loss.",
     "Cycle count sheets and variance approval.",
     "Bulk and corporate order desk."],
    ["Indent to allocation to pick to dispatch to receive.",
     "Warehouse to warehouse and store to store transfers.",
     "Receiving with variance capture.",
     "Quarantine for damaged or doubtful stock.",
     "Count plan by ABC class."],
    ["Stock value, days of cover, ageing by bucket.",
     "Fill rate on store indents, dispatch time, in-transit value.",
     "Count accuracy and shrink by location.",
     "Repack yield by SKU and operator."],
    ["Weight drift from moisture loss during storage.",
     "Mixed batches and partial batch sales.",
     "In-transit damage and short receipts.",
     "Negative stock from sync delay, resolved on sync.",
     "Cold storage and temperature-sensitive items.",
     "Gift box kits consuming component stock."])

st += module(5, "Wastage and shrink", "Deep",
    "Wastage in food retail is where margin leaks quietly. The module makes loss visible at the point it happens, ties it to cost, and nudges action before stock expires.",
    ["Quick wastage entry in store and warehouse with reason and photo.",
     "Near-expiry list at 60, 30 and 15 days with value at risk.",
     "Markdown and transfer suggestions.",
     "Shrink report: book stock against count by location.",
     "Wastage by store, cluster, SKU and vendor."],
    ["Entry to approval by threshold to ledger posting.",
     "Alert to action: markdown, move to a faster store, add to a mix pack.",
     "Link wastage back to the vendor batch for claims."],
    ["Wastage percent of sales and of cost.",
     "Value at risk by expiry bucket.",
     "Shrink percent by category and location.",
     "Claim recovery from vendors."],
    ["Reason codes: expiry, rancid or moisture, pest, damage, spillage, weighing variance, tasting samples, suspected theft, quality reject.",
     "Tasting samples tracked as a capped expense.",
     "Loose item weight loss separated from true loss.",
     "Reversals with full audit trail."])

st += module(6, "Demand and replenishment", "Medium",
    "Forecasts that respect Indian festival and winter seasonality, and replenishment suggestions that respect import lead times. The first version uses transparent methods that the team can read and trust.",
    ["Seasonality calendar: Diwali, Eid, Ramadan, Navratri, Raksha Bandhan, Holi, Christmas, winter.",
     "Forecast view by store, SKU and week with accuracy shown.",
     "Reorder suggestions with safety stock and lead time.",
     "Festive pre-build plan for gift boxes.",
     "Assortment suggestions by store cluster."],
    ["Nightly forecast job.",
     "Suggested PO and suggested store indent, approved by a human.",
     "Min and max per location reviewed monthly."],
    ["Forecast error (WAPE) and bias.",
     "Stockout days avoided, excess stock value.",
     "Inventory turns by category."],
    ["New SKUs borrow history from similar SKUs.",
     "Sales during stockouts are treated as censored demand.",
     "Lunar calendar festivals shift each year.",
     "Import lead times of 30 to 60 days drive early ordering.",
     "Middle East store calendar differs from India."])

st += module(7, "Finance and tax reconciliation", "Deep",
    "The aim is to track every rupee from vendor invoice to customer bill, and to give finance a clean close. The module prepares reconciled working data. Filing stays with their finance team and CA.",
    ["Daily close dashboard by store: cash, UPI, card against expected.",
     "Settlement reconciliation against payment gateway and bank files, with fees.",
     "GST workbench: output tax by HSN, rate and state. Input credit from purchases.",
     "Purchase register matched against the government portal credit statement upload.",
     "Payables ageing and payment run proposals.",
     "Stock valuation and margin by SKU after wastage.",
     "Journal export for Oracle, Tally or CSV."],
    ["Store day-close to finance review to lock.",
     "Month close with period lock.",
     "Vendor invoice to three-way match to payable.",
     "Inter-state stock transfers with tax invoices.",
     "E-way bill data prepared for transfers, with API integration through a GSP in phase 2."],
    ["Cash variance by store and cashier.",
     "Unreconciled value and age.",
     "Tax liability and credit position by GSTIN.",
     "Days to close, and gross margin by SKU, store and vendor."],
    ["Cash short and excess with approval.",
     "Mixed payment bills and payment fees.",
     "Credit notes and rounding differences.",
     "Stores under different state GSTINs.",
     "Backdated entries blocked after period lock.",
     "Import taxes and customs duty folded into landed cost."])

st += module(8, "Customers and WhatsApp commerce", "Light",
    "The website routes visitors to WhatsApp and phone. This module turns that into a tracked order channel and builds a customer record from phone numbers captured at the billing counter.",
    ["Customer 360: history, favorite categories, basket size, last visit.",
     "Segments by recency, frequency and spend.",
     "WhatsApp order inbox with cart summary and payment link.",
     "Corporate gifting enquiry and quote screen.",
     "Campaign list with consent status."],
    ["Phone captured at POS to customer record.",
     "WhatsApp order to OMS order to dispatch.",
     "Quote to approval to order for bulk and gifting.",
     "Festival and repeat-purchase reminders."],
    ["Repeat rate, active customers, loyalty share of sales.",
     "WhatsApp orders and conversion.",
     "Corporate quote win rate."],
    ["Duplicate customers by phone number.",
     "Consent and opt-out tracking under the data protection rules.",
     "Template approval and rate limits on WhatsApp business messaging.",
     "Gift orders shipped to a different address."])

st += module(9, "HR basic", "Light",
    "A basic people module sized for a retail chain with a large store workforce. Payroll is out of scope, and the module exports hours to whichever payroll provider they use.",
    ["Org chart: head office, region, city, store.",
     "Employee profile and onboarding checklist.",
     "Punch in and punch out with store location check.",
     "Shift roster for stores.",
     "Leave and work-from-home for head office staff.",
     "Birthdays and work anniversaries feed.",
     "Job postings and a basic applicant list that feeds the careers page."],
    ["Offer to onboarding tasks to day one setup.",
     "Missed punch regularization with manager approval.",
     "Leave request to approval to balance.",
     "Requisition to job post to applicant stage."],
    ["Attendance and hours by store.",
     "Overtime, leave balance, open positions.",
     "Time to fill and attrition by region."],
    ["Store staff who log in with a phone number only.",
     "Staff who move between stores.",
     "State-wise holiday calendars.",
     "Location checks have limits and are treated as a guide."])

st += module(10, "Platform", "Medium",
    "The shared layer that every module depends on. It keeps the system safe, auditable and usable across entities, states and currencies.",
    ["User and role management.",
     "Approval rules by amount and type.",
     "Audit log viewer.",
     "Import and export center.",
     "Entity, GSTIN and currency settings.",
     "System health: sync status, job runs, errors."],
    ["Phone OTP login for store staff, email login for head office.",
     "Row-level scope by store and region.",
     "Notifications by in-app, WhatsApp and email.",
     "API keys for other systems."],
    ["Active users by role.",
     "Approval turnaround time.",
     "Job success rate and sync lag."],
    ["One person with roles in several stores.",
     "Multiple legal entities and state registrations.",
     "INR and AED with time zones.",
     "Backups and restore drills.",
     "Every write carries user, device and time."])

# ---------------- data model ----------------
st += page_title("Core data model", "The entities that carry the whole system. Everything else is a view over these.")
dm = [["Entity", "Key fields", "Note"],
      ["location", "id, type (warehouse, store, in-transit), city, state, country, entity, GSTIN", "Tree with parent location for zones and bins."],
      ["sku, sku_pack", "product, grade, origin, pack size, HSN, shelf life, uom, barcode", "Pack conversion rules for repacking."],
      ["vendor, vendor_sku_cost", "vendor, sku, currency, incoterm, moq, lead time, price, effective_from, effective_to", "Cost history is never overwritten."],
      ["purchase_order, po_line, shipment", "vendor, status, expected dates, tracking stages, charges", "Shipment holds freight, duty and clearing."],
      ["grn, grn_line, batch", "po ref, batch no, expiry, MRP, accepted and rejected qty", "Batch is the unit of traceability."],
      ["stock_ledger", "location, batch, qty, movement type, document ref, timestamp, user", "Append only. Stock on hand is a sum."],
      ["transfer, repack_job", "from, to, status, input and output batches, yield loss", "In-transit is a location."],
      ["sale, sale_line, payment", "store, device, invoice no, idempotency key, business date, tax split", "Immutable once synced."],
      ["day_close, settlement", "store, expected and counted cash, gateway files, variance, lock status", "Feeds finance reconciliation."],
      ["wastage_entry", "location, batch, reason, qty, cost, approver, photo", "Posts to the ledger on approval."],
      ["customer, consent", "phone, segments, loyalty points, consent flags", "Phone is the identity key."],
      ["employee, attendance, roster", "role, store, punches, shift, leave", "Light version in the demo."],
      ["journal_entry", "date, account, debit, credit, source document", "Export format for any ERP."]]
st += [tbl(dm, [150, 400, FW - 550]), PageBreak()]

# ---------------- demo data ----------------
st += page_title("Demo data plan", "The demo has to look like their business, so the data is built to behave like it")
left = [P("What gets generated", H2)] + bullets([
    "500 stores across major Indian cities, with a small group of Middle East stores to show multi-currency.",
    "20 warehouses, with a regional hub pattern.",
    "1,200 SKUs built from the public collections, with names and pack sizes that match what stores sell. Prices and costs are modeled, and the demo says so.",
    "About 60 vendors, a mix of import and domestic, with several vendors per SKU and cost that moves by month.",
    "24 months of sales with weekday patterns, winter uplift, Diwali, Eid and Ramadan peaks, and gift box spikes.",
    "Batches with expiry, wastage, transfers, repacking, store indents, day closes and settlements."]) + [
    P("Volume handling", H2)] + bullets([
    "Full-scale history is generated locally into Parquet and DuckDB.",
    "The hosted demo carries a trimmed slice: line-level bills for a subset of live stores, and daily aggregates for the rest.",
    "The final split depends on the hosting tier and is settled on day 1."])
right = [P("Findings planted in the data", H2), P("Each one gives the CEO a concrete story in under a minute.", BODY), Spacer(1, 3)] + bullets([
    "One warehouse with shrink well above its peers.",
    "One vendor whose landed cost rose for three months while a cheaper vendor stayed available.",
    "A cluster of stores with chronic stockouts on fast-moving almonds and cashews.",
    "A store with repeated cash shortage on weekends.",
    "Three stores not syncing for two days.",
    "A fresh dried fruit SKU with heavy expiry loss in smaller stores.",
    "Gift box component shortage ahead of a festival.",
    "A month where GST input credit in the books differs from the portal statement."]) + [
    P("Labeling", H2), P("The app shows a visible demo data label. Nothing in it claims to be their real numbers.", BODY)]
t = Table([[left, right]], colWidths=[FW * 0.52, FW * 0.48])
t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("RIGHTPADDING", (0, 0), (0, 0), 16)]))
st += [t, PageBreak()]

# ---------------- demo story ----------------
st += page_title("The 10 minute demo story", "Built for a CEO. Short, concrete, and ending on ownership and cost.")
ds = [["Minute", "Scene", "What the CEO sees"],
      ["0 to 1", "Control Tower", "Yesterday across 500 stores. Eight exceptions already flagged."],
      ["1 to 3", "Drill into a problem", "Weekend cash shortage in one store, traced to the cashier and shift. Shrink hotspot in one warehouse."],
      ["3 to 5", "POS on a tablet", "Bill loose almonds by weight. Switch off Wi-Fi. Keep billing. Switch on. Watch the queue sync and the sale appear in the dashboard."],
      ["5 to 6", "Procurement", "Same SKU from three vendors, landed cost compared, and the PO suggestion it produces."],
      ["6 to 7", "Inventory and wastage", "Near-expiry stock value at risk and the suggested move to a faster store."],
      ["7 to 8", "Finance", "Month close view, settlement reconciliation, GST working data matched against the portal statement."],
      ["8 to 9", "Customers and WhatsApp", "A WhatsApp order flowing into dispatch."],
      ["9 to 10", "Ownership", "Roadmap, pilot path, and what a first 90 days looks like."]]
st += [tbl(ds, [70, 160, FW - 230]), Spacer(1, 6),
       P("Modules 6, 8, 9 and 10 appear as short moments, since the story is margin, control and speed of finance.", SMALL), PageBreak()]

# ---------------- plan ----------------
st += page_title("One week build plan", "Close to seven days. The plan is tight and the cut list is decided in advance.")
wk = [["Day", "Work", "Output"],
      ["1", "Lock scope. Collect catalog and brand assets from the site. Pick palette. Finalize schema and data volume plan.", "Schema, design tokens, catalog seed"],
      ["2", "Data generator. SKU master. Vendors, price book, landed cost.", "Seeded database with 24 months of history"],
      ["3", "Inventory ledger, GRN, transfers, repack, indents.", "Warehouse flows working end to end"],
      ["4", "POS PWA with offline storage and sync. Day close.", "Billing demo with network drop and sync"],
      ["5", "Wastage, finance reconciliation, Control Tower.", "CEO story running on live data"],
      ["6", "Forecast and replenishment. Light modules. Roles and audit.", "Remaining screens"],
      ["7", "QA, performance, rehearsal, final deck and PDF export.", "Demo script and backup recording"]]
st += [tbl(wk, [40, 470, FW - 510]), Spacer(1, 8),
       P("Cut list if time runs out, in this order", H2)] + bullets([
    "HR basic and Customers: designed screens with seeded data, no workflow.",
    "Demand and replenishment: suggestions from a simple seasonal average, without accuracy views.",
    "Platform: roles and audit only.",
    "Never cut: POS offline demo, Control Tower, procurement landed cost, wastage, finance close."]) + [
    P("Risks", H2)] + bullets([
    "A one-person week with this scope leaves little room for rework. A recorded backup of the demo is part of the plan.",
    "Hosted data size and cold starts can slow the demo. Paid tiers for the week, and a local fallback.",
    "Real catalog and brand colors from the site help the look, and tax rules in the demo are labeled as configurable and subject to their CA."]) + [PageBreak()]

# ---------------- business case ----------------
st += page_title("Business case frame and open questions", "Numbers to find out in the room, and questions that change the build")
bc = [["Number to find out", "Why it matters"],
      ["POS licence, support and hardware cost per store per year", "Sets the savings line honestly, including what the new setup would cost."],
      ["Finance hours per month spent on reconciliation, and days to close", "Shows the value of automated reconciliation."],
      ["Wastage and shrink as percent of sales, if known", "Gives the size of the prize for module 5."],
      ["Stockout days on top SKUs", "Shows the value of replenishment."],
      ["Number of legal entities and GSTINs", "Shapes finance and invoicing design."],
      ["Oracle quote, scope and timeline", "Frames the lean alternative against a real number."]]
oq = [P("Open questions", H2)] + bullets([
    "The website carries a return policy page. Is there a returns flow in practice, even a small one?",
    "Can the current POS vendor export data nightly, even as CSV?",
    "Do stores sell loose items by weight, and on which scales?",
    "Which payment terminals and UPI setups are in stores?",
    "How are labels and barcodes printed today?",
    "Which Middle East entities exist, and in which currencies?",
    "Is anything in the current stack staying, such as Tally or a payroll provider?"])
t = Table([[tbl(bc, [220, 190]), oq]], colWidths=[FW * 0.55, FW * 0.45])
t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("RIGHTPADDING", (0, 0), (0, 0), 16)]))
st += [t, PageBreak()]

# ---------------- design system ----------------
st += page_title("Design system foundations", "Shared rules across all four palette options")
f1 = [P("Typography", H2)] + bullets([
    "Headings: a serif or a clean sans, depending on palette option. Body and UI: Inter. Numbers and tables: tabular figures.",
    "Scale: 12, 14 (base), 16, 20, 24, 32. Line height 1.4 for text, 1.2 for headings.",
    "POS uses a larger base of 16 and numerals at 28 to 40 for totals."]) + [P("Spacing and shape", H2)] + bullets([
    "4 point grid. Steps 4, 8, 12, 16, 24, 32.",
    "Radius 8 for cards and inputs, 999 for chips.",
    "Light borders over heavy shadows. One elevation level for menus and dialogs."]) + [P("Density modes", H2)] + bullets([
    "POS mode: 48 px minimum touch targets, high contrast, keyboard shortcuts.",
    "Back office mode: compact tables, 32 px rows, sticky headers and filters."])
f2 = [P("Components", H2)] + bullets([
    "App shell with sidebar, top bar, role-based navigation.",
    "KPI card with value, delta and sparkline.",
    "Data table with sort, filter, column picker, export.",
    "Filters bar: date range, city, cluster, category.",
    "Forms with inline validation and unit-aware inputs (kg, g, packs).",
    "Status chips, toasts, empty states, approval dialogs.",
    "Sync indicator for the POS: online, offline, syncing, queue count."]) + [P("Charts", H2)] + bullets([
    "Six series colors per palette, tested for color blind separation.",
    "Direct labels where possible, legends only when needed.",
    "Good and bad use the status colors, never the series colors."]) + [P("Accessibility", H2)] + bullets([
    "Text contrast of 4.5 to 1 or higher. Never rely on color alone for status.",
    "Full keyboard support in the POS and in tables."])
t = Table([[f1, f2]], colWidths=[FW / 2, FW / 2])
t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("RIGHTPADDING", (0, 0), (0, 0), 16)]))
st += [t, PageBreak()]

# ---------------- palettes ----------------
def lum(h):
    c = colors.HexColor(h)
    return 0.2126 * c.red + 0.7152 * c.green + 0.0722 * c.blue

def mock(p):
    d = Drawing(240, 150)
    d.add(Rect(0, 0, 240, 150, fillColor=colors.HexColor(p["bg"]), strokeColor=LINE))
    d.add(Rect(0, 0, 38, 150, fillColor=colors.HexColor(p["primary"]), strokeColor=None))
    for i in range(5):
        d.add(Rect(8, 120 - i * 18, 22, 6, fillColor=colors.HexColor(p["bg"]), strokeColor=None, fillOpacity=0.55))
    d.add(Rect(38, 128, 202, 22, fillColor=colors.HexColor(p["surface"]), strokeColor=LINE))
    d.add(Rect(190, 134, 42, 10, fillColor=colors.HexColor(p["accent"]), strokeColor=None, rx=4, ry=4))
    for i in range(3):
        x = 46 + i * 64
        d.add(Rect(x, 84, 58, 36, fillColor=colors.HexColor(p["surface"]), strokeColor=LINE))
        d.add(Rect(x + 6, 108, 18, 3, fillColor=colors.HexColor(p["accent"]), strokeColor=None))
        d.add(Rect(x + 6, 92, 30, 8, fillColor=colors.HexColor(p["text"]), strokeColor=None, fillOpacity=0.85))
    d.add(Rect(46, 8, 186, 68, fillColor=colors.HexColor(p["surface"]), strokeColor=LINE))
    hs = [30, 44, 26, 52, 38, 46]
    for i, h in enumerate(hs):
        d.add(Rect(56 + i * 28, 14, 18, h, fillColor=colors.HexColor(p["chart"][i]), strokeColor=None))
    return d

def swatch(label, hexv):
    tc = "#FFFFFF" if lum(hexv) < 0.55 else "#0F172A"
    return Paragraph(f'<font color="{tc}" size="7"><b>{label}</b><br/>{hexv}</font>',
                     ParagraphStyle("sw", fontName="Helvetica", fontSize=7, leading=9))

def palette_block(key, name, tagline, p, fonts, pros):
    tokens = [("Primary", p["primary"]), ("Secondary", p["secondary"]), ("Accent", p["accent"]),
              ("Page bg", p["bg"]), ("Surface", p["surface"]), ("Text", p["text"]),
              ("Success", p["success"]), ("Warning", p["warning"]), ("Danger", p["danger"])]
    r1 = [swatch(a, b) for a, b in tokens]
    r2 = [swatch(f"Chart {i+1}", c) for i, c in enumerate(p["chart"])] + ["", "", ""]
    sw = Table([r1, r2], colWidths=[50] * 9, rowHeights=[34, 34])
    sty = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 4),
           ("BOX", (0, 0), (-1, -1), 0.3, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.white)]
    for i, (_, h) in enumerate(tokens):
        sty.append(("BACKGROUND", (i, 0), (i, 0), colors.HexColor(h)))
    for i, h in enumerate(p["chart"]):
        sty.append(("BACKGROUND", (i, 1), (i, 1), colors.HexColor(h)))
    sw.setStyle(TableStyle(sty))
    right = [P(f"Option {key}: {name}", S("pn", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=TEAL)),
             P(tagline, SMALL), Spacer(1, 4), sw, Spacer(1, 4),
             P(f"<b>Type:</b> {fonts}", SMALL), P(f"<b>Good for:</b> {pros}", SMALL)]
    t = Table([[mock(p), right]], colWidths=[250, FW - 250])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    return t

PA = dict(primary="#3E2A1E", secondary="#7C9A5B", accent="#E0A526", bg="#F6EEE0", surface="#FFFFFF", text="#2B1D14",
          success="#4F7A3A", warning="#C98A0B", danger="#B23A2E",
          chart=["#3E2A1E", "#E0A526", "#7C9A5B", "#B5651D", "#8C6B4F", "#D9C3A0"])
PB = dict(primary="#1F4D3A", secondary="#A8C686", accent="#C8643B", bg="#FAF6EC", surface="#FFFFFF", text="#17261F",
          success="#2F7D4F", warning="#D9922B", danger="#B23A2E",
          chart=["#1F4D3A", "#A8C686", "#C8643B", "#E3B04B", "#5E8C6A", "#8A5A44"])
PC = dict(primary="#1B2447", secondary="#6B3FA0", accent="#D9A441", bg="#FBF8F1", surface="#FFFFFF", text="#141A33",
          success="#2E7D5B", warning="#D9A441", danger="#B3342F",
          chart=["#1B2447", "#D9A441", "#6B3FA0", "#3E7CB1", "#8E9AC7", "#B07A3A"])
PD = dict(primary="#0F172A", secondary="#0F766E", accent="#F59E0B", bg="#F8FAFC", surface="#FFFFFF", text="#0F172A",
          success="#16A34A", warning="#F59E0B", danger="#DC2626",
          chart=["#0F766E", "#F59E0B", "#2563EB", "#7C3AED", "#64748B", "#DB2777"])

st += page_title("Palette options, set 1", "Warm and brand-flavored directions")
st += [palette_block("A", "Walnut and Saffron", "Warm browns, cream and saffron. Reads like the product itself.", PA,
                     "Fraunces for headings, Inter for UI", "Decks, POS receipts, the customer-facing side. Charts need care with the browns."),
       palette_block("B", "Pistachio Fresh", "Deep forest green with pistachio and a terracotta accent.", PB,
                     "Lora for headings, Inter for UI", "A fresh, natural identity. Strong for stores and marketing screens."),
       PageBreak()]
st += page_title("Palette options, set 2", "Premium and operational directions")
st += [palette_block("C", "Royal Indigo", "Indigo with gold. Premium and gifting-led.", PC,
                     "Playfair Display for headings, Inter for UI", "Gift boxes and corporate gifting. Less suited to dense tables."),
       palette_block("D", "Clean Ops", "Slate, teal and amber on a near-white base.", PD,
                     "Inter for headings and UI, JetBrains Mono for figures", "Dashboards, tables and long working sessions. Easiest charts."),
       PageBreak()]

st += page_title("Recommendation and next steps")
st += [P("Recommendation", H2), P(
    "Use Option D as the base for the back office and the POS, and bring in one warm accent from their actual brand once I have the logo values. Dense tables and charts read better on a neutral surface, and the brand shows up through the accent, the logo and the receipt. Options A and B suit the deck cover and customer-facing pages. Option C fits a dedicated gifting page.", BODY),
       Spacer(1, 6), P("Brand colors", H2), P(
    "I could not read the logo colors from the site text. Send a screenshot of the logo or the site header, or I can pick them from the logo file, and the tokens above will be updated in one place.", BODY),
       Spacer(1, 6), P("Next steps", H2)] + bullets([
    "You confirm the palette direction and the cut list.",
    "I collect the catalog and brand assets and generate the seed data.",
    "Build in the order of the week plan, with a recorded backup of the demo.",
    "Final deck and demo script on day 7."])

doc.build(st)
print("ok")
