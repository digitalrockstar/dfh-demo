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
