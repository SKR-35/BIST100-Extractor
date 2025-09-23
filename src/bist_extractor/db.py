from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

import pandas as pd

from .fetch import META_FIELDS

DB_PATH = "bist100_prices.db"


def init_db(db_path: str = DB_PATH):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Run log
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        started_at TEXT NOT NULL,
        rng TEXT NOT NULL,
        interval TEXT NOT NULL,
        n_rows INTEGER NOT NULL,
        note TEXT
    );
    """
    )

    # Prices table (unique bar per ticker/datetime_utc/interval)
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS prices (
        ticker TEXT NOT NULL,
        datetime_utc TEXT NOT NULL,
        datetime_local TEXT,
        datetime_tr TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        adjclose REAL,
        range_str TEXT,
        interval TEXT,
        ingested_at TEXT NOT NULL,
        run_id TEXT NOT NULL,
        PRIMARY KEY (ticker, datetime_utc, interval)
    );
    """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_ticker ON prices(ticker);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_dt ON prices(datetime_utc);")

    # Meta table (symbol=PK)
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS meta (
        symbol TEXT PRIMARY KEY,
        currency TEXT,
        exchangeName TEXT,
        fullExchangeName TEXT,
        instrumentType TEXT,
        firstTradeDate INTEGER,
        regularMarketTime INTEGER,
        hasPrePostMarketData INTEGER,
        gmtoffset INTEGER,
        timezone TEXT,
        exchangeTimezoneName TEXT,
        regularMarketPrice REAL,
        fiftyTwoWeekHigh REAL,
        fiftyTwoWeekLow REAL,
        regularMarketDayHigh REAL,
        regularMarketDayLow REAL,
        regularMarketVolume REAL,
        longName TEXT,
        shortName TEXT,
        chartPreviousClose REAL,
        previousClose REAL,
        scale INTEGER,
        priceHint INTEGER,
        ingested_at TEXT,
        run_id TEXT
    );
    """
    )

    con.commit()
    con.close()


def ingest_prices(
    df: pd.DataFrame,
    rng: str,
    interval: str,
    db_path: str = DB_PATH,
    run_id: str | None = None,
    note: str | None = None,
):
    """
    Upsert DataFrame rows into SQLite with run logging.
    Expects df to have at least: ['ticker','datetime', 'open','high','low','close','volume','adjclose']
    Adds: ingested_at (UTC ISO), run_id (uuid4 if None)
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    # Make a working copy and normalize datetime columns
    d = df.copy()

    # Ensure we have UTC & TR & local naive strings for storage
    if "datetime" not in d.columns:
        raise ValueError("DataFrame must include a 'datetime' column (tz-aware).")

    # Build UTC (naive, ISO 8601), local (naive), TR (naive)
    if pd.api.types.is_datetime64tz_dtype(d["datetime"]):
        dt_utc = d["datetime"].dt.tz_convert("UTC").dt.tz_localize(None)
        dt_local = d["datetime"].dt.tz_localize(None)
        dt_tr = d["datetime"].dt.tz_convert("Europe/Istanbul").dt.tz_localize(None)
    else:
        # Assume naive = local; convert to UTC string (best-effort)
        dt_local = d["datetime"]
        dt_utc = pd.to_datetime(d["datetime"], utc=True).dt.tz_localize(None)
        dt_tr = (
            pd.to_datetime(d["datetime"], utc=True)
            .dt.tz_convert("Europe/Istanbul")
            .dt.tz_localize(None)
        )

    d["datetime_utc"] = dt_utc.dt.strftime("%Y-%m-%d %H:%M:%S")
    d["datetime_local"] = dt_local.dt.strftime("%Y-%m-%d %H:%M:%S")
    d["datetime_tr"] = dt_tr.dt.strftime("%Y-%m-%d %H:%M:%S")

    # Rename 'range' -> 'range_str' to avoid SQL keyword weirdness
    if "range" in d.columns:
        d = d.rename(columns={"range": "range_str"})
    # Ensure interval column exists even if not in df (batch function already sets it)
    if "interval" not in d.columns:
        d["interval"] = interval
    if "range_str" not in d.columns:
        d["range_str"] = rng

    # Add ingestion metadata
    ingested_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    d["ingested_at"] = ingested_at
    d["run_id"] = run_id

    # Select/align columns for DB
    cols = [
        "ticker",
        "datetime_utc",
        "datetime_local",
        "datetime_tr",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjclose",
        "range_str",
        "interval",
        "ingested_at",
        "run_id",
    ]
    missing = [
        c for c in ["ticker", "open", "high", "low", "close", "volume"] if c not in d.columns
    ]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    d_db = d[cols].copy()
    d_db = d_db.where(pd.notnull(d_db), None)  # replace NaN/NaT/pd.NA with None
    d_db = d_db.astype(object)  # ensure Python objects, not numpy dtypes

    # Upsert into SQLite
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.executemany(
        """
        INSERT INTO prices (
            ticker, datetime_utc, datetime_local, datetime_tr,
            open, high, low, close, volume, adjclose,
            range_str, interval, ingested_at, run_id
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(ticker, datetime_utc, interval) DO UPDATE SET
            open=excluded.open,
            high=excluded.high,
            low=excluded.low,
            close=excluded.close,
            volume=excluded.volume,
            adjclose=excluded.adjclose,
            range_str=excluded.range_str,
            ingested_at=excluded.ingested_at,
            run_id=excluded.run_id
        ;
    """,
        list(map(tuple, d_db.values)),
    )

    # Log the run
    cur.execute(
        """
        INSERT OR REPLACE INTO runs (run_id, started_at, rng, interval, n_rows, note)
        VALUES (?, ?, ?, ?, ?, ?);
    """,
        (run_id, ingested_at, rng, interval, int(len(d_db)), note),
    )

    con.commit()
    con.close()
    return run_id


def ingest_meta(df_meta: pd.DataFrame, db_path: str = DB_PATH, run_id: str | None = None):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # NaN/NA → None ve Python-native tiplere çevir
    d = df_meta.copy()
    d = d.where(pd.notnull(d), None).astype(object)

    # ingest meta timestamp
    ingested_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    d["ingested_at"] = ingested_at
    d["run_id"] = run_id or "manual"

    cols = META_FIELDS + ["ingested_at", "run_id"]
    tuples = list(map(tuple, d[cols].values))

    cur.executemany(
        f"""
        INSERT INTO meta ({",".join(cols)})
        VALUES ({",".join(["?"]*len(cols))})
        ON CONFLICT(symbol) DO UPDATE SET
            currency=excluded.currency,
            exchangeName=excluded.exchangeName,
            fullExchangeName=excluded.fullExchangeName,
            instrumentType=excluded.instrumentType,
            firstTradeDate=excluded.firstTradeDate,
            regularMarketTime=excluded.regularMarketTime,
            hasPrePostMarketData=excluded.hasPrePostMarketData,
            gmtoffset=excluded.gmtoffset,
            timezone=excluded.timezone,
            exchangeTimezoneName=excluded.exchangeTimezoneName,
            regularMarketPrice=excluded.regularMarketPrice,
            fiftyTwoWeekHigh=excluded.fiftyTwoWeekHigh,
            fiftyTwoWeekLow=excluded.fiftyTwoWeekLow,
            regularMarketDayHigh=excluded.regularMarketDayHigh,
            regularMarketDayLow=excluded.regularMarketDayLow,
            regularMarketVolume=excluded.regularMarketVolume,
            longName=excluded.longName,
            shortName=excluded.shortName,
            chartPreviousClose=excluded.chartPreviousClose,
            previousClose=excluded.previousClose,
            scale=excluded.scale,
            priceHint=excluded.priceHint,
            ingested_at=excluded.ingested_at,
            run_id=excluded.run_id
        ;
    """,
        tuples,
    )

    con.commit()
    con.close()
