# UPDATES (newest first)

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
