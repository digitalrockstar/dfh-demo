# UPDATES (newest first)

## 2026-11-02 Module 3 Procurement and logistics
- Seed (dfh/seed/procurement.py, runs after demand): about 260 POs over May to Oct (Rs 167 Cr), 250 shipments with event timelines, landed cost actuals once cleared, 200 GRNs, 240 vendor invoices, 177 payments, 46 debit notes for rejects. GRNs from the last 60 days create batches. Own random stream, so earlier module numbers did not move.
- Landed cost (dfh/procurement_costs.py): goods at PO FX, then freight and insurance on FOB prices only (CIF already holds them), customs duty and a 10% surcharge on the assessable value, clearing, port and haulage. Every rate is a row in tax_assumption marked ASSUMED, including duty by category (20 to 35%). Import GST is left out as recoverable. A PO uses recorded actuals when they exist, otherwise the estimate, and says which.
- Three-way match: invoice against goods accepted at PO price, after credit for rejected goods, tolerance 1%. Reasons: billed for the ordered quantity but less accepted, billed above the PO price, billed below goods accepted. Finance, CEO or admin release; a mismatch needs a note. Hold needs a note. Dispute raises a debit note for the over-billing.
- Planted: vendor 3 (F2 price creep) invoices 6% above PO price on about 80% of POs since 20 Jul and is flagged Price creep on the scorecard; a Turkish import vendor ships 9 to 16 days late from July; one domestic vendor delivers 8 to 12% short from September and bills in full; an Australian vendor has 7% moisture rejects on lots from mid July; a Chennai container sits in customs for 10+ days. Control Tower shows the customs hold, late shipments, mismatched invoices and price creep.
- Flow: approved buy suggestions turn into draft POs grouped by vendor and warehouse at the current price book price (the suggestion moves to ordered, cancel puts it back). Approve (above Rs 25 lakh needs CEO, finance or admin), vendor confirmed, book shipment, move it forward one stage at a time, post a GRN (batch and expiry per line, rejects need a reason, 5% over-receipt cap), record the invoice, decide it. Approval adds to on order and a GRN moves it to on hand in stock_position.
- API (dfh/procurement_api.py): options, summary, pos, po detail, from-suggestions, action, shipments, book, event, landed, grn, match, invoice, decision, pricebook, compare, vendors. Warehouse sees and receives only its own POs.
- Screen: KPIs, shipment tracker, POs with a detail drawer (lines, timeline, landed cost, receipts, invoice and match, all forms), price book with creep filter and a per-SKU landed cost compare, vendor scorecard, match queue.
- Tests: 13 new in tests/test_procurement.py (52 total), smoke extended, no console errors. The flow test uses real open suggestions, so it needs a fresh `make setup` after many runs.
- Open: GRN batches have no mfg date and seeded ones for POs older than 60 days have no batch; no partial shipments or split invoices; one invoice per PO; payments run in Module 7; FX is monthly; air freight is a single rate; no vendor ratings workflow; PO approval chain is one step; Module 4 branch (origin/feature/inventory) is not merged and will need a schema merge.

## 2026-11-02 Module 6 Demand and replenishment
- Forecast (dfh/demand/model.py, rebuild alone with `python -m dfh.demand.run`, about 12 s): per store and SKU, 8 weekly buckets from 1 Nov, 795k rows with an 80% band and value at list price. Level is the trailing 56 day average with stockout days and new store ramp removed, each day divided by its festival factor, shrunk toward the same SKU in the same store tier. Festival factor is 1 + category sensitivity x calendar intensity. Sensitivity is learned from chain sales by regression (July onward, with trend and weekday terms), not typed in.
- Learned sensitivity: Gift boxes +300%, Chocolates +199%, Dates +148%, Exclusives +146%, Nuts and dry fruits +118%, Berries +54%, Spices +47%, Seeds +26%. Chain forecast peaks in the week of 1 Nov at about 2x the no-festival level and returns to base after Diwali.
- Backtest (cut at 3 Oct, scored on the last 4 weeks, stockout weeks and 25 new stores left out): error by city and category 7.4% against 18.8% for a flat average; warehouse and SKU 23.0% against 29.7%; store and SKU 49.2% against 51.9%. Store and SKU is mostly Poisson noise at low volume, so do not quote it as a headline. The 80% band covered 86% of cells over Rs 200 on weeks it was not fitted on.
- Known weaknesses: the forecast runs 7% low across the board because it trails a rising trend (no trend term). The festival shape in the model is the same shape the calendar uses, so on real data the score will be worse. No festival is modelled after Diwali, so Christmas and New Year are flat.
- Buying (dfh/demand_api.py): packs roll up to their bulk SKU in grams at 100% yield, gift boxes roll up to components. Order up to demand over (lead time + 21 day order cycle) + safety stock (z 1.65 for the top quarter by value, 1.28 for the rest, error taken from the backtest) against on hand + on order. Cheapest current vendor, MOQ and lead time from the price book. 264 open suggestions worth about Rs 12.9 Cr: 205 critical (stock ends before a new order can land), 32 order this week, 27 plan.
- Stock position is a modelled snapshot (table stock_position), not real. It is the swap point: Module 4 ledger replaces on hand, Module 3 purchase orders replace on order. Vendor cost is before freight and duty until Module 3.
- Planted findings now visible: F3 Pune warehouse is critical on almonds and cashews; F7 gift box components are short at five warehouses, 20 of 85 gift boxes sit below 90% coverage, Pistachios the usual limiter.
- Screen: KPIs, sales with forecast and band, festival sensitivity, buy suggestions with approve and reject (orders above Rs 25 lakh need CEO, finance or admin; you can send an adjusted quantity through the API, the screen approves the suggested one), gift box components, accuracy card with assumptions, store min and max review with accept. Control Tower shows two new exceptions (critical buy lines, gift boxes short).
- Roles: warehouse sees only its own warehouse and cannot approve; store manager sees forecast and min/max for the store only, no buy suggestions; cashier has no access.
- Tests: 11 new in tests/test_demand.py (39 total), smoke extended (demand page, scope switch, approve), no console errors.
- Open: approving does not create a PO yet (Module 3), no Christmas or New Year, no trend term, no repack yield, no transfer suggestions between warehouses, min/max change has no seasonal end date, assortment by store cluster not built, quantity edit is API only.
- Local test note: smoke accepts CHROME=/path/to/chrome when Playwright's own browser is not installed.

## 2026-11-01 Module 5 Wastage and shrink
- Seed (dfh/seed/wastage.py): 38.5k loss entries over 6 months across 500 stores and 20 warehouses, 10 reason codes, 285 batches with 5k stock rows and 811 markdown suggestions. This is a thin slice of batches and stock so near-expiry works before Module 4 exists; Module 4 will own them.
- Planted findings: F1 Hyderabad Warehouse 1 shrink ramps from Aug (about 3x peers in the last 30 days, theft logged at night); F6 dried pineapple expiry in 30 kiosks (top store expiry loss, expired stock still on shelf).
- API (dfh/wastage_api.py): summary, reasons, trend, location league (stores against COGS, warehouses at cost, outlier flag at 2x median), top SKUs (reason and kind filters), near-expiry at 15, 30 and 60 days with buckets, entries list, entry create, approve or reject, markdown accept or dismiss, options.
- Rules: entries from Rs 2,000 at cost wait for approval; you cannot approve your own entry; batch entries deduct stock and a rejection puts it back; quantity limits; roles and store or warehouse scoping; every write is audited.
- Screen: KPIs, loss trend, reasons, locations, top SKUs, near-expiry with markdown actions, recent entries with approve and reject, Record loss form.
- Control Tower now shows two real exceptions from this module (warehouse shrink outlier, expiry risk). The placeholder for expiry risk is gone.
- Tests: 10 new in tests/test_wastage.py (28 total), smoke extended (wastage page, filters, form validation), no console errors. Fixed a resize error in the Control Tower chart when leaving the page.
- Open: photo upload (only a photo reference is stored), markdown acceptance does not change POS price yet (needs POS), vendor claim workflow, cap breach alerts for weighing and samples (caps are in wastage_reason but not enforced), stock deduction only for the seeded batches until Module 4.
- Local test note: smoke needs Playwright matching the installed Chromium; `make setup` should run in a venv on newer Ubuntu (PEP 668).

## 2026-10-31 App shell, SKU master (Module 2), Control Tower v0 (Module 1)
- Backend: FastAPI (dfh/app.py), DuckDB analytics over the Parquet history (dfh/analytics.py), signed-token login, role and store/warehouse scoping.
- Frontend: no-build ES modules (frontend/src). Sidebar shell, settings popover (light, auto, dark; 5 tones including the new DFH tone sampled from the logo; glass slider), solid tables, glass panels, Escape closes drawers.
- SKU master: search, category chips, sourcing and status filters, sort, paging; drawer with overview, pricing and vendors (landed INR by month, sparklines, lowest vendor, 3 month change), packs or kit contents, 30 day sales, audit history; price and status edit with cost floor and status moves; CSV price import with check then apply, all-or-nothing.
- Control Tower v0: net sales, gross margin ex tax, per store-day, stockouts, stores not syncing, each with change vs previous period; daily trend with 7 day average and festival markers; category mix; store league (top and bottom 10); exceptions (stale sync, stockout hotspot by city, sales drops) plus placeholders for modules not built.
- Tests: 11 seed + 7 API (login, filters, detail variants, price rules and audit, import, Control Tower, scoping) + browser smoke (no console errors). Screenshots at /tmp/shots when run.
- Open in Module 2: approval step for price changes, barcode label generation, seasonal on/off dates, near-duplicate detection beyond exact names.
- Open in Control Tower: drill from store to SKU and bill, saved views, daily 7am snapshot, exceptions assignment. Needs the other modules for cash, expiry, PO and reconciliation exceptions.
- Frontend choice: plain ES modules, not React and Vite as written in the PDF, to move faster. Porting later is straightforward since the API is separate.

## 2026-10-31 Plan deck v2 (Apple design skill)
- docs/DFH_Product_Plan_v2.pdf: 25 slides, 16:9, Inter text and Inter Display embedded, glass cards on soft color fields, auto-fit sizing.
- Built from the same content as v1: `python tools/story_dump.py docs/build_book.py /tmp/story.json` then `python tools/render_deck.py /tmp/story.json out.pdf` (needs playwright with Chromium). Edit content in docs/build_book.py only.
- Not yet pushed to the repo (PAT use was scoped to the foundation push).

## 2026-10-31 Foundation
- Schema: 95 tables across platform, masters, procurement, inventory, pos, wastage, finance, crm, hr, analytics.
- Masters: 20 legal entities, 20 warehouses with 1,200 bins, 500 stores, 636 devices with invoice series, 60 vendors, 1,200 SKUs, 232 products, 85 gift kits with BOM, tax assumptions, 7 festival windows, 49 FX rows, HR org, 9 demo users.
- History: 6 months store x SKU x day, 5.36M rows, 3,169 stockout events, 8 planted findings.
- Tests: 11 passing (counts, FK integrity, many-to-many price book, planted creep, stale stores, margin and revenue bands, festival uplift, Pune stockouts).
- Theme tokens with glass slider and 4 tones in light and dark.
- Plan PDF v1 (25 pages) and context docs added.
- Decisions: return policy 10 days for defective or damaged; GST and GSP on hold with stated assumptions; 6-month history now, 24 months later.
- Next: Module 2 SKU master end to end.
