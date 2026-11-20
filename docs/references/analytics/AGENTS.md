# AGENTS.md — Working Practices for All Agents

## Project
DFH Analytics: one integrated, real-time BI / MIS / operations-intelligence system for Dry Fruit House. It is the core technology and analytics engine, not a set of dashboards. Single system, not multi-client. Read `MEMORY.md` first, then `MASTER_PLAN.md`, then the tail of `UPDATES.md`.

## Hard rules
1. Work and commit directly to `main`. No feature branches, no PRs.
2. Never invent business data. Every number shown must carry a provenance mode: `live`, `sample`, `derived`, or `unavailable`. Sample data is always visibly labelled.
3. No deployment, infrastructure, tunnel, DNS or systemd changes without explicit user approval.
4. Never commit secrets (PATs, API keys, `.env`). Secrets live in environment files outside the repo and are listed in `.gitignore`. Never write a token into any file, commit message or log.
5. Planning phase gate: no application code until the user approves the plan.
6. Charts: lines are thin (1 to 1.5 px, forecast 1 px) and smooth (monotone cubic spline, never straight segments). Any part-of-whole or percentage-of-100 figure is a donut or ring, never a bar. Depth comes from tokens (`--sh3`, tilt, 3D donut), not ad-hoc shadows.
7. One design system. No ad-hoc colours, spacing or fonts: use tokens from `DESIGN_PLAN.md`.

## Documentation discipline
Update at every meaningful step and substep, in the same commit as the change:
- `UPDATES.md` — append a dated entry (what, why, issues, resolution). Newest at the bottom.
- `MEMORY.md` — durable facts and decisions (add an ADR row when a decision is made).
- `MASTER_PLAN.md` — tick roadmap items, adjust scope.
- `DESIGN_PLAN.md` — any visual/UX decision.
- `SKILLS.md` — new tools, libraries, conventions.

## Commit conventions
Small, focused commits to `main`. Format: `area: imperative summary` (e.g. `docs: add master plan`, `data: add sales staging schema`). Pull/rebase before push. Never force-push.

## Quality bar
Tests for data transforms and metric definitions. Every metric has a documented definition, grain, source and owner. Respect the t3.micro budget (1 GB RAM): no heavy services, no Node build toolchain on the server.

## Handoff
Before ending a session: docs updated, tree clean, last commit pushed, `UPDATES.md` states next step.
