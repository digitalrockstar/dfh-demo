# Dry Fruit House Operations Platform (demo)

Demo of an in-house platform for a 500 store dry fruit retail chain: offline-first POS, OMS and WMS, procurement
and inbound logistics, wastage, finance and tax working data, demand planning, customers, HR and platform.
All data is synthetic. Prices, costs, vendors and volumes are modeled, not real.

## Run the foundation
```
pip install -r requirements.txt
python -m dfh.seed.run          # masters plus 6 months of history (about 10 seconds)
pytest -q tests                 # 11 checks
```
Output: `data/dfh.db` (SQLite masters, 95 tables) and `data/sales_daily/` (Parquet, about 22 MB for 6 months).
Set `DATABASE_URL` for Postgres. Read context in `docs/` first: CONTEXT.md, PLAN.md, UPDATES.md.
