![Python](https://img.shields.io/badge/Python-3.10-blue) ![License](https://img.shields.io/badge/License-Apache--2.0-orange) ![Data](https://img.shields.io/badge/Data-OHLCV%20Pipeline-green)

# BIST100 Extractor

A simple, reproducible pipeline to download OHLCV time series for **BIST 100** tickers
from Yahoo Finance using a clean CLI with configurable `--range` and `--interval`.

---

## Features
- CLI with `argparse`: set `--range` (e.g., `1mo`, `6mo`, `1y`, `5y`, `max`) and `--interval` (e.g., `1d`, `1h`, `5m`).
- Saves per-ticker CSVs under `data/`.
- Solid repo hygiene (ruff + black), GitHub Actions CI, tests.
- Daily ingestion runner for Windows Task Scheduler
- External SQLite database path via `BIST_DB_PATH` environment variable

---

## Project Structure

```text
BIST100-Extractor/
├── scripts/
│   └── sample_bist100_daily_ingest.bat
├── src/
│   └── bist_extractor/
│       ├── __init__.py
│       ├── cli.py
│       ├── daily_ingest.py
│       ├── db.py
│       ├── fetch.py
│       ├── io.py
│       └── session.py
├── tests/
├── README.md
└── pyproject.toml
```

---

## Quickstart (Conda)
```bash
conda create -n bist100 python=3.11 -y
conda activate bist100
pip install -e ".[dev]"
ruff check .
black .
pytest -q
```

---

## Run
```bash
python -m bist_extractor.cli --range 1y --interval 1d
python -m bist_extractor.cli --range 1y --interval 4h
python -m bist_extractor.cli --range 120d --interval 60m
python -m bist_extractor.cli --range 60d --interval 30m
python -m bist_extractor.cli --range 12d --interval 5m
python -m bist_extractor.cli --range 2d --interval 1m
```

Outputs:
```
BIST100_60d_30m_YYYYMMDD_HHMMSS.csv
BIST100_60d_30m_YYYYMMDD_HHMMSS.xlsx
```
and updates `bist100_prices.db` (tables: `runs`, `prices`, `meta`).

For scheduled database updates:

```bash
python -m bist_extractor.daily_ingest
```

A sample Windows Scheduler batch file is available under:

```text
scripts/bist100_daily_ingest.template.bat
```

---