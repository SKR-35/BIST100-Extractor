"""
BIST100 daily ingestion runner.

Fetches market data and writes directly to SQLite.
No CSV/XLSX export. Designed for Windows Scheduler / BAT execution.

Database path is supplied externally by BAT through BIST_DB_PATH.
"""

import os
from datetime import datetime, timezone

from bist_extractor.db import ingest_meta, ingest_prices, init_db
from bist_extractor.fetch import BIST_SUBSET, fetch_batch, metas_to_df

DB_PATH = os.environ.get("BIST_DB_PATH")

if not DB_PATH:
    raise OSError("BIST_DB_PATH environment variable is missing. " "Set it in the BAT file.")


JOBS = [
    ("1d", "1m"),
    ("1d", "5m"),
    ("1d", "30m"),
    ("1d", "1d"),
    ("1d", "60m"),
    ("1d", "4h"),
]


def run_job(rng: str, interval: str):
    print("=" * 70)
    print(f"START {datetime.now(timezone.utc)}")
    print(f"range={rng} interval={interval}")
    print("=" * 70)

    df_bist, metas, errs = fetch_batch(
        BIST_SUBSET,
        rng=rng,
        interval=interval,
    )

    print(f"Fetched rows: {len(df_bist)}")
    print(f"Errors: {len(errs)}")

    if errs:
        for ticker, error in list(errs.items())[:10]:
            print(f"[ERROR] {ticker}: {error}")

    if df_bist.empty:
        print("[WARN] Empty dataframe. Skipping ingestion.")
        return

    run_id = ingest_prices(
        df_bist,
        rng=rng,
        interval=interval,
        db_path=DB_PATH,
        note="daily ingest v1",
    )

    print(f"Prices ingested. run_id={run_id}")

    df_meta = metas_to_df(metas)

    ingest_meta(
        df_meta,
        db_path=DB_PATH,
        run_id=run_id,
    )

    print("Metadata ingested.")


def main():
    print("BIST100 DAILY INGEST START")
    print(f"Database: {DB_PATH}")

    init_db(DB_PATH)

    for rng, interval in JOBS:
        try:
            run_job(rng, interval)
        except Exception as exc:
            print(f"[FAILED] {rng}/{interval}: {exc}")

    print("BIST100 DAILY INGEST FINISHED")


if __name__ == "__main__":
    main()
