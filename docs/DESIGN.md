# DESIGN

Tokens: `frontend/src/theme/tokens.css`. Reference: `docs/skills/apple-design.md`.

- Default tone is DFH (warm ink and amber, sampled from the logo). Mode: light, auto or dark, chosen in the appearance popover along with tone and glass.
- Modes: light and dark. Tones: ops (teal, slate, amber), walnut (brown, sage, saffron), pistachio (forest, pistachio, terracotta), indigo (indigo, plum, gold).
- Each tone is 3 colors plus neutrals. Status colors stay fixed across tones.
- Glass: one slider, `--glass` from 0 to 1, drives blur and surface opacity on shell and cards only. Tables, forms and POS stay solid. Honors prefers-reduced-transparency.
- Materials: heavier surfaces for structure, lighter for interactive; never stack a light translucent surface on another.
- Motion: respond on press, springs for anything touchable, interruptible, reduced-motion honored. Avoid CSS transitions for gesture-driven parts.
- Type: system font stack, tight tracking and leading on large text, rem spacing.
- Density: POS mode 16px base and 48px targets; back office compact with 32px rows.
- Per-module theming later through data-module overrides of tone variables.
- Palette options in the PDF (A walnut, B pistachio, C indigo, D clean ops). Recommended base: D. Brand colors from the DFH logo still to be confirmed.

## Restyle: analytics look on the demo palette
Reference (read-only): `docs/references/analytics/`. Keep: tones, light/dark/auto, glass slider, POS density.
- Layers: tray (recess) -> tile (card) -> raised (control). Tokens `--bg-tray`, `--bg-tile`, `--bg-raised`, `--hair`, `--hi`, `--e0`..`--e3`, radii `--r-sm/md/lg`.
- Charts: thin monotone splines, `--stroke` 1.5px, forecast `--stroke-fc` 1px. Percent-of-100 and part-of-whole use `donut()` (3D extruded, `size` is width in px), never bars.
- Layout: dashboards use `.bento` (12 columns). POS and tables do not.
- Provenance: every KPI carries `prov()` (live, sample, derived, na). Demo data is sample unless computed from other data.
- Shell: rail `.side` (full, number chips under 1024px, bottom nav under 768px), pulse bar `.pulse`, palette `#pal` (Cmd/Ctrl+K), insight panel `#ipanel` (grid column from 1280px, overlay below). Tokens `--rail-w`, `--rail-w-sm`, `--pulse-h`, `--panel-w`, `--nav-h`. Appearance and sign-out live in the pulse bar.
- Motion: `roll()` for KPI changes; easings `--ease-out`, `--ease-inout`, `--ease-spring`; reduced-motion honoured.
- Series palette: tokens `--c0`..`--c5` (donut segments and legends). "Other" uses `--muted`, never a status colour.
- KPI helper pattern (per page): label + `prov()`, value, optional gauge ring for percent figures, sub-line. Call `rollKpis()` after mounting KPI blocks.
- `donutLegend(parts, fmt, size)` in `ui.js`: donut plus legend for any part-of-whole (ageing, mixes). Bucket colours come from series tokens; status colours only where the bucket is a status (ageing: ok to bad). Grid spans `.b3 .b4 .b5 .b6 .b7 .b8 .b12`; below 1100px all but b3/b4 go full width.
