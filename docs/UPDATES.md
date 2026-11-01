# UPDATES (newest first)

## 2026-11-01 Module 4 Inventory and warehouse
- Seed (dfh/seed/inventory.py, about 7 s): 3,663 batches, 233k ledger rows, 162k balances, 42 transfers, 32 indents, 30 repack jobs, 24 count plans. Every balance equals the sum of its ledger rows (tested). Cost is per kg for loose SKUs, per unit for packs.
- API (dfh/inventory.py): overview with exceptions, stock by location with min/max status, SKU batches and locations, ledger by SKU, location or batch, expiry buckets with suggested action, transfers (draft, dispatch with FEFO, receive with short quantities, cancel), indents (raise, allocate with reservations, dispatch into a transfer, cancel), repack (yield loss flag above 2 percent, block above 5), cycle counts (ABC plans, submit, approve with limits), gift box readiness, shrink by reason.
- Rules: stock moves only through one posting function that refuses negative balances. Expired batches never ship. Loose moves in 100 g steps. Inter-state move above Rs 50,000 needs an e-way reference (stated assumption, GST on hold). Count variance above Rs 5,000 on a line or Rs 10,000 in total needs CEO or admin. Scope: warehouse users act on their own warehouse, store managers see their store.
- Screens (frontend/src/page_inv.js): Overview, Stock, Expiry, Transfers, Indents, Repack, Cycle counts, Gift boxes, with drawers for SKU batches, transfers, indents and counts.
- Planted findings now visible: F1 Hyderabad shrink (about 16x typical, mostly unexplained, plus repack loss), F3 Pune warehouse under store minimums on about 25 SKUs, F6 dried pineapple near expiry in 30 kiosks, F7 Cashews 500g limits two Diwali boxes (festival need assumed at 4x store max).
- Tests: 9 new in tests/test_inventory.py (run on a temp copy of the DB), 27 total passing.
- Schema: transfer.indent_id added, ledger and transfer indexes.
- Not verified: browser smoke for the new screens. Chromium could not be downloaded in the build sandbox. JS syntax and static serving checked only. Run `make smoke` locally.
- Open: count freeze during counting (system quantity refreshes at submit), store to warehouse returns, bin level putaway and pick paths, bulk and corporate order desk, GRN link (receipts are opening stock until Module 3), approvals through the platform approval table, notifications.

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
