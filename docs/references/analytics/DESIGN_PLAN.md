# DESIGN_PLAN.md — Design System, Visual Direction, UX Principles

Status: Direction APPROVED. Concept screens (v3) in `docs/design/concepts/` (Phase 1), awaiting approval before full development.

## 1. Experience thesis
A calm, intelligent instrument that is always observing. Not a wall of static charts: signals flow in, are processed, connected and surfaced as insights. Premium, modern, operationally alive; no gimmicky sci-fi.

## 2. "Live thinking machine" — meaningful patterns
- **Pulse bar:** global strip showing last ingest, jobs running, data freshness, events/min.
- **Signal stream:** real-time feed (ingest completed, anomaly detected, threshold crossed, insight formed) fed by the SSE event bus.
- **Processing indicators:** subtle skeleton shimmer and progress rings tied to actual jobs, not decoration.
- **Connected insights:** insight cards show a chain (e.g. stock-out risk → sales at risk → PO delay → vendor) with click-through evidence.
- **Live number transitions:** values tween on update; changed tiles briefly highlight; sparklines extend.
- **Drill-downs:** every tile → breakdown → underlying rows, preserving filters.
- **Provenance badges (mandatory):** `LIVE` (solid dot, pulsing only when data truly arrives), `SAMPLE` (hatched/striped tag), `DERIVED` (formula glyph), `UNAVAILABLE` (muted dashed). Sample activity is never styled as live.
- **Motion rules:** 150–250 ms ease-out for state changes; no looping ornamental animation; respects `prefers-reduced-motion`.

## 3. Layout
- **Bento grid:** 12-column responsive grid; tiles span 3/4/6/8/12 cols and 1–3 rows; consistent 16 px gap (12 px mobile).
- **Shell:** left rail (13 systems, grouped), top pulse bar + search/command palette (`⌘K`), right-side collapsible insight/signal panel.
- **Breakpoints:** ≥1440 wide, 1024 desktop, 768 tablet (rail collapses to icons), <768 mobile (bottom nav, single column, priority tiles first).

## 4. Skeuomorphic depth (subtle)
- Layered surfaces: canvas → panel → tile → raised control.
- Tiles: soft inner highlight on top edge, 1 px hairline border, two-layer shadow (ambient + contact).
- Tactile controls: segmented switches and toggles with pressed/raised states; buttons depress 1 px on press.
- Depth is restrained; no glossy textures or heavy bevels.

## 5. Design tokens (central, CSS variables; Light / Dark / Auto)
Auto follows `prefers-color-scheme`; user override stored per user. All components consume tokens only.

| Token | Light | Dark |
|---|---|---|
| `--bg-canvas` | #EEF0F3 | #0B0E13 |
| `--bg-panel` | #F7F8FA | #11151C |
| `--bg-tile` | #FFFFFF | #171C25 |
| `--bg-raised` | #FFFFFF | #1E2430 |
| `--border-hair` | #DDE1E7 | #262D3A |
| `--text-primary` | #11151C | #E8ECF2 |
| `--text-secondary` | #566070 | #98A2B3 |
| `--accent` (almond/amber-brown, brand-warm) | #B7791F | #E0A23B |
| `--accent-signal` (live/intelligence, teal) | #0E9F8E | #2DD4BF |
| `--positive` | #1E9E5A | #34D399 |
| `--warning` | #D97706 | #FBBF24 |
| `--negative` | #D1383D | #F87171 |
| `--info` | #2F6FDB | #60A5FA |

Colours are a proposal; final palette confirmed in concept screens. Chart palette: 8 colour-blind-safe categorical tones + sequential/diverging ramps derived from `--accent` and `--accent-signal`.

- **Typography:** Inter (UI), tabular numerals for figures (`font-variant-numeric: tabular-nums`), JetBrains Mono for IDs/code. Scale: 12/14/16/20/28/40.
- **Spacing:** 4 px base (4, 8, 12, 16, 24, 32, 48). **Radius:** 8 / 14 / 20. **Elevation:** e0–e3. **Motion:** `--dur-fast 150ms`, `--dur-base 250ms`, `--ease-out cubic-bezier(.2,.8,.2,1)`.

## 6. Components
Tile (KPI, chart, table, feed, insight chain), pulse bar, signal feed item, provenance badge, segmented control, toggle, date-range picker, filter chips, command palette, drill-down drawer, data table (sortable, sticky header), empty/error/stale states, toast, theme switcher (Light/Dark/Auto).

## 7. Visualisation guidelines
ECharts with token-driven theme. Sparklines in KPIs, line/area for trends, bar for ranking, heatmap for cohorts/availability, Sankey for channel→product→outcome flows, funnel for fulfilment/conversion, treemap for category mix, geo map for sales regions. Every chart: tooltip, legend toggles, zoom where useful, drill-down, provenance + as-of footer, accessible data-table fallback.

## 8. UX principles
1. Honest by default: show source, freshness and mode.
2. Answer first: headline number and "so what" before detail.
3. Exceptions over inventory: surface what changed or needs action.
4. Drill, don't navigate away: context preserved.
5. Consistent patterns across all 13 systems.
6. Accessible: WCAG AA contrast, keyboard navigation, reduced-motion support, screen-reader labels on charts.
7. Fast: server-rendered first paint, partial updates via HTMX/SSE.

## 9. Concept screens to prepare for approval (Phase 1)
1. Executive MIS (light + dark): KPI strip, signal stream, insight chain, trend bento.
2. Sales & Channels: channel Sankey, geo map, growth, returns.
3. Data Management: pipeline flow, quality scores, lineage, freshness.
4. Mobile view of Executive MIS.
All concepts use clearly labelled `SAMPLE` figures.

## 10. Motion and bento conventions (from the bento-ui-motion-grid skill; reference in `docs/reference/`)
Adopted:
- **Layered surfaces:** grey tray holding white inner cards; 2 to 3 dark cards per screen for contrast; one accent colour per theme plus its tint.
- **Three easing curves only:** `spring` (from rest, about 12% overshoot) for things that travel: knobs, gliders, rings, digits, tile entrances; `soft` (critically damped, no overshoot) for crossfades, theme flips, stack pushes; `expo` only for opacity reveals. Never use `expo` on large colour areas, it reads as a flash.
- **No binary swaps:** layer both states and crossfade (icon fills, labels, progress fills, theme change).
- **Rolling tabular digits** (built: `app/static/motion.js`) for KPI changes (per-digit odometer, left to right stagger). Digit-width changes (9 to 10) are acceptable.
- **Staggered spring intro** on first load only (about 1.6 s, delay by position), content rising 6 px. Afterwards motion must be data-driven.
- **Ambient motion only where meaningful:** sparkline scroll on new data, pulse ring on live badge. Respect `prefers-reduced-motion`.
- **Grid discipline:** columns sum to equal heights; mix tall, medium and thin tiles.
Not adopted (does not fit a live product): the video pipeline (120 fps frame rendering, `draw(t)` clock-driven pages, no CSS transitions, no `Date`). Product motion is event-driven from the SSE stream and uses CSS/Web Animations. An optional MD showcase video can reuse that skill later (needs approval).

## 11. v3: system console, depth and part-of-whole (2026-11-19)
- **Framing:** the product is the live core system. The shell shows engine state: Engine running, events per minute, p95 latency, jobs, freshness, and a clock, all badged Simulated in concepts. Rail has icons and four groups (Command, Commerce, Business, Platform) and a stream-status footer.
- **Lines:** smooth monotone-cubic splines (no overshoot; sparklines included), chart strokes 1.4 px (forecast 1.1, plan 1, Now marker 1, sparkline 1), soft gradient area fill, SVG drop shadow to lift the line without weight.
- **Part-of-whole:** anything summing to 100% (channel, region, new vs repeat) is a 3D donut: tilted ring, extruded edge, blurred ground shadow, top sheen. Hover a slice or legend row to lift it and read value and share in the centre. A single percentage (service level, data quality) is a ring gauge of the same build.
- **Depth tokens:** `--sh3` (three-layer tile shadow), recessed tray, dark cards with a teal glow, KPI and donut tiles tilt up to 3.5 degrees toward the pointer with a specular glare. Reduced motion disables tilt and animation.
- **Chart palette tokens:** `--c1` to `--c6` (amber, teal, blue, magenta, violet, slate), light and dark variants.
- **Live sample:** Events per minute scrolls one point per second (Simulated).

## 12. Sales & Channels layout (2026-11-20)
- Row 1: four KPI tiles (c3) with 7-day versus prior-7 deltas. Row 2: net sales against target and forecast (c8, thin splines: actual 1.4 px, forecast 1.1 px dashed, target 1 px dotted grey, Now marker) beside the channel-mix 3D donut (c4). Row 3: net sales by channel (c6 multi-line, one colour token per channel) and region-mix donut (c6). Then the channel scorecard table and a ranked locations bar list (c12).
- Chart axes: three y ticks, x labels at D-30, Now, D+14; legend swatches repeat the line style so dashed means forecast and dotted means target without colour.
- Scoped role (store): KPIs and one trend line only, with a note that company views are hidden.

## 13. Products & Inventory layout (2026-11-20)
- Row 1: four KPI tiles. Row 2: stock value spline (actual solid, projected 1.1 px dashed, Now marker) beside the sales-by-category 3D donut. Row 3: SKU scorecard table (horizontal scroll on narrow screens; a stock-out status reads in the negative colour, a delayed PO carries a badge). Row 4: three tiles: stock-by-category donut, shelf-life donut, lowest-cover bars (the bar turns to the signal colour under 7 days). Seven category slots use `--c1` to `--c6` then `--t2`.

## 14. Customers layout (2026-11-20)
- Row 1: four KPI tiles. Row 2: cohort retention splines (one thin line per weekly cohort, percent axis, week labels) beside the RFM customers donut. Row 3: four equal tiles of 3D donuts. Row 4: segment scorecard table and the cohort retention table, shaded with `color-mix` of `--c2` so depth of colour means retention. Segment colours: Champions `--c2`, Loyal `--c3`, Promising `--c5`, New `--c4`, Needs attention `--c1`, At risk `--neg`, Hibernating `--c6`.

## 12. Executive MIS v1 (2026-11-20)
- Four 30-day KPI tiles (gross margin, operating profit, closing cash, receivables overdue) sit under today's KPIs and use rolling digits. A company scorecard lists one measure per system with value, provenance badge and basis, each row linking to its system page (or placeholder). No traffic-light status until thresholds are defined by the user (never invented). Revenue chart uses the shared spline helper (1.4 px actual, 1.1 px dashed forecast).

## 13. Finance (2026-11-20)
- Same bento build as Sales: four rolling-digit KPIs, a cash line (1.4 px actual, 1.1 px dashed projected, Now marker), dark cash-position tile, P&L and cash-flow tables, two 3D donuts (expense categories, open payables by due date: part-of-whole), receivables as a table (due buckets are small counts). Negative amounts in the P&L show as costs; provenance badge on every tile.

## 14. Procurement (2026-11-20)
- Four rolling-digit KPIs, receipts line (solid actual, 1.1 px dashed scheduled, Now marker), dark replenishment-actions tile, two 3D donuts (spend and open commitment by vendor: part-of-whole) and one on-time ring gauge (single percentage), vendor scorecard and open-PO tables. A delayed PO shows the SKU stock-out it causes, linking procurement to inventory.

## 15. Marketing (2026-11-20)
- Four rolling-digit KPIs, spend-against-plan line (1.4 px actual, 1.1 px dashed plan, Now marker), dark attribution-coverage tile, two 3D donuts (orders by source, spend by campaign: part-of-whole), dense campaign scorecard. Pacing over plan is flagged with the existing negative tone, not a new colour.

## 16. Operations (2026-11-20)
- Four rolling-digit KPIs, on-time spline with percent axis, dark live-queue tile (moves with the replay clock), 3D donuts for carrier and region shares, a ring gauge for the single on-time percentage, carrier and region tables. Late-open count uses the existing negative tone only when non-zero.

## 17. People (2026-11-20)
- Four rolling-digit KPIs (headcount, 30-day attendance, late arrivals, monthly payroll), attendance spline with percent axis, dark on-shift-today tile (moves with the replay clock), rostered-shifts line (1.4 px past, 1.1 px dashed scheduled, Now marker), 3D donuts for headcount, shift status and payroll (part-of-whole), a ring gauge for the single attendance percentage, packing productivity table, unit, role and own-store tables. Staff appear as aggregates only: no names, no per-person pay.

## 18. Growth & Planning (2026-11-20)
- Four rolling-digit KPIs (attainment, week on week, 14-day forecast, run-rate), cumulative line (1.4 px actual, 1.1 px dashed forecast, 1 px dotted target, dotted colour for the scenario, Now marker), 3D donut for forecast by channel (part-of-whole), ring gauge for the single attainment percentage, scenario planner as a plain GET form with number inputs, channel table, gaps and risks and ROAS tables. Scenario results are always labelled as a what-if input.

## 19. Insight Engine (2026-11-20)
- A page reached from the Executive MIS Insights tile (not a 14th system). Four rolling-digit counts, one card per cross-domain chain (ordered nodes with domain link and provenance badge, first card dark), a peer-outlier card, a spike table with the group it belongs to, and three small 1.4 px splines for the strongest spikes. No traffic-light colours: strength is a word (moderate or strong).

- Signal stream (2026-11-20): engine events are labelled `(derived)` in the feed, platform events `(live)`, replayed seed events carry no suffix and read as Simulated.

## Reports & Settings (2026-11-20)
Uses existing tokens and tiles only: four KPI tiles, a full-width catalog table with a provenance badge per report and a plain CSV link, access matrix and engine settings side by side, audit log below. No new colours, shadows or chart types. Settings are shown read-only with a note on why; nothing on the page looks editable.

## Data Management: connector tile (2026-11-20)
One full-width tile under the checks and lineage: dataset specs, then the latest 20 runs with lineage (file, raw_files, staging table), counts, status and up to 3 reject reasons per run. Existing tokens, badges (`live`, `derived`) and table style only.

## Sales: source banner (2026-11-20)
When uploads drive the page, a `banner` under the title states the source and what is still seed; badges on seed-sourced sums switch from Sample to Live, the target tile adds a Sample badge for target and forecast, and return figures show `n/a` or a dash. When uploads exist but are not usable, a banner gives the reason. With no uploads the page is unchanged.

## Inventory: source banner (2026-11-20)
Same pattern as Sales: banner states the source and what is unavailable, the chart tile badge turns Live, the at-risk KPI shows `n/a`, the shelf-life tile becomes an Unavailable tile and the trend shows a short note until two full days are uploaded. With no usable upload a banner gives the reason, with none at all the page is unchanged.


## Consumers of uploaded data: banners (2026-11-20)
Uploaded-data banners: any page that consumes uploads shows one `banner` under the title naming what is live and what stays seed, with `?source=seed` to compare, or a one-line reason when uploads are not used. Revenue and chart headings show a Live badge for uploaded actuals and a Sample badge for forecast. Figures with no upload show `n/a` with the Unavailable mode, never a seed value.

## Data Management: connector column (2026-11-20)
The connector run table shows a Connector column (csv_drop, webhook, rest_pull, db_read) and the lineage text starts with it. The note above the dataset table lists the four connector types and says webhook, REST pull and SQLite read are off until the operator configures them. No new tokens or components.

## Report builder and schedules (2026-11-20)
Same tokens, tiles and tables as the rest of Reports & Settings; no new colours, shadows, chart types or scripts. The `/reports` page gains three full-width tiles (Saved reports, Schedules, Snapshots) above the access matrix. Builder and saved-report pages use plain HTML forms (checkboxes, selects, number input) styled by the existing base styles, a table preview of the first 50 rows with the provenance badge in the header text, and the Delete action as a plain button inside a form. Every tile that holds platform records is Live; the badge on a saved report row is the base report's provenance. Notes under each tile say what is and is not done (no delivery, snapshots only, same permissions).

## Backups (2026-11-20)
No visual change. A command-line tool and a design note only. When the nightly job exists, its result appears as a job row in Technology & IT with existing tokens; nothing new is drawn.

## Demo scope (2026-11-20)
No visual change. Sample labelling stays visible on every generated figure; nothing generated is shown as Live.

## Re-seed check (2026-11-20)
No visual change. Inactive findings are history rows and are not drawn as active on any page.

## Local run guide (2026-11-20)
No visual change. Documentation only.

## Demo marker (2026-11-20)
The badge on a figure that comes from uploaded data follows its provenance: Sample badge (existing token) for demo files, Live badge for ordinary files. No new token, colour or component.

## Sample connector files (2026-11-20)
No visual change. Pages that read these files show the existing Sample badge.

## Demo depth review (2026-11-20)
No visual change. Pages to check in the pending visual pass: `/finance`, `/customers`, `/marketing`, `/procurement`, `/operations`, `/people`, `/sales`, `/inventory`, `/growth`, `/exec`, `/data`.
