# MEMORY (durable facts for the next session)

- Repo: github.com/digitalrockstar/dfh-demo. Local project layout: dfh/ (schema.py, db.py, seed/), tests/, docs/, frontend/.
- Seed: `python -m dfh.seed.run` regenerates everything in about 10 seconds (seed 42). data/ is git-ignored; regenerate on each new machine.
- Numbers: 500 stores, 20 warehouses, 1,200 SKUs (112 bulk, 837 repacked, 166 finished, 85 kits), 60 vendors, 6,580 vendor price rows (Apr to Oct 2026, monthly), 25,000 customers, 2,347 employees, 99k store-assortment rows, 5.36M sales rows (22 MB Parquet), average about Rs 29k per store-day.
- Units: money in paise; quantity in base unit (g for loose, ea for packed). Sales net is tax inclusive, INR equivalent.
- Demo logins (password demo1234): ceo, finance, procurement, warehouse, storemgr, cashier, hr, marketing, admin.
- Assumptions flagged in tax_assumption and festival_calendar (assumed=1). Phone numbers are fake (+00-xxxxxxxx).
- Gotchas: SQLite returns dates as text in raw SQL, parse them. DuckDB relations have no fetchone, use fetchall()[0]. Rows inserted with executemany need identical keys.
- Open items: DFH brand colors (logo values), real POS export format, GSTIN count, whether returns exist beyond the stated 10 day policy.
