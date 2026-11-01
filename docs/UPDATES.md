# UPDATES (newest first)

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
