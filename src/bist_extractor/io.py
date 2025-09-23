from __future__ import annotations
import os
import pandas as pd
from datetime import datetime
from pathlib import Path

def save_bist(df: pd.DataFrame, rng: str, interval: str, prefix: str = "BIST100", out_dir: Path = Path("data")):
    """
    Save DataFrame to CSV and Excel with auto-named file:
    BIST100_<range>_<interval>_<YYYYMMDD_HHMMSS>.csv/xlsx
    - Keeps tz-aware datetime in CSV
    - Converts to tz-naive for Excel
    - Adds datetime_local, datetime_utc, datetime_tr (Turkey local time)
    """
    
    """
    Save a single combined CSV and XLSX for the whole batch under out_dir (default: data/).
    """
    out_dir.mkdir(parents=True, exist_ok=True)    
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{prefix}_{rng}_{interval}_{ts}"

    csv_path = out_dir / f"{stem}.csv"
    xlsx_path = out_dir / f"{stem}.xlsx"

    # --- CSV: keep original DataFrame (tz-aware is OK in CSV) ---
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # --- Excel: must strip tz-awareness ---
    df_xlsx = df.copy()
    if "datetime" in df_xlsx.columns and pd.api.types.is_datetime64tz_dtype(df_xlsx["datetime"]):
        tzname = str(df_xlsx["datetime"].dt.tz)  # e.g., Europe/Istanbul

        # Add timezone info column
        df_xlsx["tz"] = tzname

        # Local (tz-naive)
        df_xlsx["datetime_local"] = df_xlsx["datetime"].dt.tz_localize(None)

        # UTC (tz-naive)
        df_xlsx["datetime_utc"] = df_xlsx["datetime"].dt.tz_convert("UTC").dt.tz_localize(None)

        # Turkish local time (tz-naive)
        df_xlsx["datetime_tr"] = df_xlsx["datetime"].dt.tz_convert("Europe/Istanbul").dt.tz_localize(None)

        # Drop original tz-aware datetime
        df_xlsx = df_xlsx.drop(columns=["datetime"])

        # Reorder columns
        cols = ["datetime_local", "datetime_utc", "datetime_tr", "tz"] + \
               [c for c in df_xlsx.columns if c not in ("datetime_local","datetime_utc","datetime_tr","tz")]
        df_xlsx = df_xlsx[cols]

    # Write Excel
    df_xlsx.to_excel(xlsx_path, index=False, engine="openpyxl")

    print(f"Saved CSV  -> {os.path.abspath(csv_path)}")
    print(f"Saved XLSX -> {os.path.abspath(xlsx_path)}")
    return csv_path, xlsx_path