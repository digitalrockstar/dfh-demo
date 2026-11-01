"""python -m dfh.demand.run [--db sqlite:///data/dfh.db] [--data data]: rebuild Module 6 (forecast, backtest, suggestions) on an existing database."""
import argparse, time
from ..db import get_engine
from . import model


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--db", default="sqlite:///data/dfh.db"); ap.add_argument("--data", default="data"); ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args(); t = time.time(); print("demand:", model.run(get_engine(a.db), a.data, a.seed), f"{time.time() - t:.1f}s")


if __name__ == "__main__":
    main()
