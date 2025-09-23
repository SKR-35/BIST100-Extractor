from __future__ import annotations

import argparse
from pathlib import Path

from .db import ingest_meta, ingest_prices, init_db
from .fetch import BIST_SUBSET, fetch_batch, metas_to_df
from .io import save_bist


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="BIST100 Extractor CLI")
    p.add_argument(
        "--range", dest="range_", required=True, help="Yahoo Finance range, e.g., 60d, 1y, 10d"
    )
    p.add_argument("--interval", required=True, help="Interval, e.g., 1d, 30m, 5m, 1m")
    p.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/bist100_prices.db"),
        help="SQLite path (created if missing)",
    )
    p.add_argument("--prefix", default="BIST100", help="Output file prefix for CSV/XLSX")
    p.add_argument("--sleep-min", type=float, default=0.8, help="Min sleep between requests")
    p.add_argument("--sleep-max", type=float, default=1.8, help="Max sleep between requests")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    # Load tickers
    symbols = list(BIST_SUBSET)

    # Fetch
    df_all, metas, errs = fetch_batch(
        symbols,
        rng=args.range_,
        interval=args.interval,
        sleep_min=args.sleep_min,
        sleep_max=args.sleep_max,
    )
    print(f"Batch shape: {df_all.shape} | errors: {len(errs)}")
    if errs:
        for k, v in list(errs.items())[:5]:
            print(f"  [WARN] {k} -> {v}")

    # Save CSV/XLSX combined
    csv_path, xlsx_path = save_bist(
        df_all, rng=args.range_, interval=args.interval, prefix=args.prefix, out_dir=Path("data")
    )
    print(f"[OK] CSV:  {csv_path}")
    print(f"[OK] XLSX: {xlsx_path}")

    # DB: init + ingest
    init_db(str(args.db_path))
    df_meta = metas_to_df(metas)
    run_id = ingest_prices(
        df_all,
        rng=args.range_,
        interval=args.interval,
        db_path=str(args.db_path),
        note="version 0.1.0",
    )
    ingest_meta(df_meta, db_path=str(args.db_path), run_id=run_id)
    print(f"[OK] SQLite updated at {args.db_path} (run_id={run_id})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
