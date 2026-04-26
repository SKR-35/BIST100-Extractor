# BIST100 Extractor

A simple, reproducible pipeline to download OHLCV time series for **BIST 100** tickers
from Yahoo Finance using a clean CLI with configurable `--range` and `--interval`.

## Features
- CLI with `argparse`: set `--range` (e.g., `1mo`, `6mo`, `1y`, `5y`, `max`) and `--interval` (e.g., `1d`, `1h`, `5m`).
- Saves per-ticker CSVs under `data/`.
- Solid repo hygiene (ruff + black), GitHub Actions CI, tests.

## Quickstart (Conda)
```bash
conda create -n bist100 python=3.11 -y
conda activate bist100
python --version                     # verify 3.11.x
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
ruff check .
black .
pytest -q
```

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
