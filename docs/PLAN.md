# PLAN

Full product plan: `docs/DFH_Product_Plan_v1.pdf` (25 pages; source `docs/build_book.py`).

## Status (5 Nov 2026)
All modules are built and merged to main. 128 tests, 127 pass, 1 skipped (procurement). Seed runs end to end.
Browser smoke has not been run for Inventory, Finance, Control Tower and Platform full (no Chromium in the build sandbox). Run `make smoke` locally before any demo.

Bridges closed on 5 Nov 2026:
- Every ledger movement (GRN, transfers, wastage, POS) now moves the warehouse stock position that Demand reads. Open buy suggestions follow it: less stock raises the quantity, covering stock or orders closes the line ("covered").
- Approved suggestions become draft POs from the Procurement screen (this was already built; the Demand screen copy was stale and is fixed).
- Control Tower shows a Live POS card: bills rung up after the history ends. They are kept apart from the modelled history.
- A store sale lowers store stock only. It reaches the warehouse position when the store indent is dispatched, as in real life.

Known gaps:
- POS returns do not restock; returns and day close are online only.
- Demand does not yet re-run the forecast on live sales; only the position and open suggestions follow stock.
- Entity scope is enforced in Platform only. Approvals cover vendor payment release and SKU price change.
- Simulated: WhatsApp sends, payments, punches, GSP. No payroll.
- POS invoice number is 22 characters; GST allows 16. Shorten before any pilot.

## Build order (module by module, each end to end with tests; numbers below are build sequence, not module numbers)
0. Foundation: schema (95 tables), masters, 6-month seed, theme tokens. DONE.
0b. App shell, Platform thin slice (login, roles, scope, audit), Module 2 SKU master, Control Tower v0. DONE.
1. Module 2 SKU master (API, screens, import, price history).
2. Module 10 Platform, thin slice (login, roles, audit, approvals) because every module needs it.
3. Module 4 Inventory and warehouse (ledger, batches, FEFO, transfers, repack, indents, counts). DONE (browser smoke run in the merge session).
4. Module 3 Procurement and logistics (price book, landed cost, PO, shipment tracker, GRN, three-way match). DONE (GRN posts to the thin stock slice; Module 4 ledger takes over).
5. POS foundation (PWA, IndexedDB, sync with idempotency keys, invoice series per device, day close, returns within 10 days for defective or damaged). DONE (offline first; sales post to the Module 4 ledger).
6. Module 5 Wastage and shrink. DONE (built early on a thin batch and stock slice; Module 4 to take over batches).
7. Module 7 Finance and tax reconciliation (assumed GST rates, GSP on hold). DONE (browser smoke pending).
8. Module 1 Control Tower. DONE (browser smoke steps pending).
9. Module 6 Demand and replenishment. DONE (built early on a modelled stock position; Module 4 and Module 3 replace on hand and on order).
10. Module 8 Customers and WhatsApp. DONE (sends and payments simulated).
11. Module 9 HR basic. DONE (punches simulated, no payroll).
12. Module 10 Platform full (approvals, audit viewer, imports, multi-entity, users, health). DONE (browser smoke pending).

## Definition of done per module
Tables seeded, API with tests, screens in all themes, edge cases listed in the PDF covered or listed as open, entry in UPDATES.md.

## Demo storyline (10 minutes, CEO)
Control Tower exceptions, drill into cash shortage and warehouse shrink, POS offline demo, procurement landed cost compare,
near-expiry action, finance close, WhatsApp order, ownership and pilot path.

## Planted findings (table demo_finding)
F1 high-shrink warehouse (Hyderabad), F2 vendor price creep, F3 Pune stockouts on almonds and cashews, F4 weekend cash shortage
(one Mumbai store), F5 three stores not syncing, F6 dried pineapple expiry in kiosks, F7 Diwali gift box component shortage,
F8 September input credit mismatch (Karnataka).
