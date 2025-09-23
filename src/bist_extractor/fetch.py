from __future__ import annotations

import random
import time
from typing import Any
from urllib.parse import urlencode

import pandas as pd
import requests

from .session import get_yahoo_session


# ---------- single-ticker fetch ----------
def fetch_yahoo_chart(
    symbol: str,
    rng: str = "12d",
    interval: str = "5m",
    include_prepost: bool = False,
    timeout: int = 20,
    session: requests.Session | None = None,
):
    """
    Robust Yahoo Finance chart fetch with cookie warm-up, retry, and host failover.
    Adds 'ticker' column.
    """
    sess = session or get_yahoo_session()
    headers = {**sess.headers, "Referer": f"https://finance.yahoo.com/quote/{symbol}/chart"}

    # warm-up cookies
    try:
        sess.get(
            f"https://finance.yahoo.com/quote/{symbol}/chart", headers=headers, timeout=timeout
        )
    except Exception:
        pass

    params = {
        "range": rng,
        "interval": interval,
        "includePrePost": str(include_prepost).lower(),
        "events": "history",
        "corsDomain": "finance.yahoo.com",
    }

    hosts = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]
    data = None
    last_exc = None

    for host in hosts * 2:
        url = f"https://{host}/v8/finance/chart/{symbol}?{urlencode(params)}"
        try:
            r = sess.get(url, headers=headers, timeout=timeout)
            if r.status_code == 429:
                time.sleep(1.25 + random.random())
                continue
            r.raise_for_status()
            data = r.json()
            break
        except Exception as e:
            last_exc = e
            time.sleep(0.4 + random.random())

    if data is None:
        raise RuntimeError(f"Failed to fetch {symbol}. Last error: {last_exc}")

    chart = data.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(f"Yahoo API error for {symbol}: {chart['error']}")

    result = (chart.get("result") or [None])[0]
    if not result:
        raise RuntimeError(f"Empty 'result' for {symbol}.")

    meta = result.get("meta", {}) or {}
    tz_name = meta.get("timezone", "UTC")
    timestamps = result.get("timestamp") or []
    if not timestamps:
        raise ValueError(f"No timestamps for {symbol}.")

    indicators = result.get("indicators", {}) or {}
    quote_block = (indicators.get("quote") or [{}])[0] or {}
    adj_block = (indicators.get("adjclose") or [{}])[0] if indicators.get("adjclose") else {}
    adj_list = adj_block.get("adjclose", [])

    # Build frame
    dt_index = pd.to_datetime(pd.Series(timestamps, dtype="int64"), unit="s", utc=True)
    try:
        dt_local = dt_index.tz_convert(tz_name)
    except Exception:
        dt_local = dt_index

    df = pd.DataFrame({"datetime": dt_local})
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(pd.Series(quote_block.get(col, [])), errors="coerce")

    if adj_list and len(adj_list) == len(df):
        df["adjclose"] = pd.to_numeric(pd.Series(adj_list), errors="coerce")
    else:
        df["adjclose"] = pd.NA

    df["ticker"] = symbol
    df["range"] = rng
    df["interval"] = interval

    # Turkish local time
    try:
        df["datetime_tr"] = df["datetime"].dt.tz_convert("Europe/Istanbul")
    except Exception:
        df["datetime_tr"] = pd.to_datetime(df["datetime"], utc=True).dt.tz_convert(
            "Europe/Istanbul"
        )

    df = df.sort_values("datetime").reset_index(drop=True)
    return df, meta


# ---------- batch fetch ----------
def fetch_batch(
    symbols, rng: str = "12d", interval: str = "5m", sleep_min: float = 0.8, sleep_max: float = 1.8
):
    sess = get_yahoo_session()
    frames, metas, errors = [], {}, {}

    for i, sym in enumerate(symbols, 1):
        try:
            df_sym, meta = fetch_yahoo_chart(sym, rng=rng, interval=interval, session=sess)
            frames.append(df_sym)
            metas[sym] = meta
            print(f"[{i}/{len(symbols)}] OK  {sym}  -> {len(df_sym)} rows")
        except Exception as e:
            errors[sym] = str(e)
            print(f"[{i}/{len(symbols)}] ERR {sym} -> {e}")
        time.sleep(random.uniform(sleep_min, sleep_max))

    df_all = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(
            columns=["datetime", "open", "high", "low", "close", "volume", "adjclose", "ticker"]
        )
    )
    return df_all, metas, errors


META_FIELDS = [
    "currency",
    "symbol",
    "exchangeName",
    "fullExchangeName",
    "instrumentType",
    "firstTradeDate",
    "regularMarketTime",
    "hasPrePostMarketData",
    "gmtoffset",
    "timezone",
    "exchangeTimezoneName",
    "regularMarketPrice",
    "fiftyTwoWeekHigh",
    "fiftyTwoWeekLow",
    "regularMarketDayHigh",
    "regularMarketDayLow",
    "regularMarketVolume",
    "longName",
    "shortName",
    "chartPreviousClose",
    "previousClose",
    "scale",
    "priceHint",
]


def metas_to_df(metas: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for sym, m in metas.items():
        row = {k: m.get(k, None) for k in META_FIELDS}
        row["symbol"] = row.get("symbol") or sym
        rows.append(row)
    dfm = pd.DataFrame(rows, columns=META_FIELDS)
    # NaN/NA → None
    dfm = dfm.where(pd.notnull(dfm), None).astype(object)
    return dfm


# ---------- BIST100 ----------
BIST_SUBSET = [
    "BTCIM.IS",
    "KOZAL.IS",
    "VESTL.IS",
    "TCELL.IS",
    "KUYAS.IS",
    "TTKOM.IS",
    "PETKM.IS",
    "MGROS.IS",
    "SISE.IS",
    "ENKAI.IS",
    "ISMEN.IS",
    "AKSEN.IS",
    "TSKB.IS",
    "HALKB.IS",
    "YKBNK.IS",
    "VAKBN.IS",
    "DOAS.IS",
    "ZOREN.IS",
    "DOHOL.IS",
    "SKBNK.IS",
    "GSRAY.IS",
    "KOZAA.IS",
    "TTRAK.IS",
    "FENER.IS",
    "TKFEN.IS",
    "GARAN.IS",
    "AKBNK.IS",
    "CLEBI.IS",
    "TOASO.IS",
    "TUPRS.IS",
    "BIMAS.IS",
    "ANSGR.IS",
    "FROTO.IS",
    "ASELS.IS",
    "KRDMD.IS",
    "CIMSA.IS",
    "BRSAN.IS",
    "ODAS.IS",
    "BSOKE.IS",
    "KCHOL.IS",
    "IPEKE.IS",
    "CCOLA.IS",
    "AEFES.IS",
    "ULKER.IS",
    "EGEEN.IS",
    "BRYAT.IS",
    "OTKAR.IS",
    "THYAO.IS",
    "ALARK.IS",
    "HEKTS.IS",
    "IEYHO.IS",
    "SAHOL.IS",
    "AKSA.IS",
    "TAVHL.IS",
    "PGSUS.IS",
    "ARCLK.IS",
    "SASA.IS",
    "EREGL.IS",
    "ISCTR.IS",
    "EKGYO.IS",
    "GUBRF.IS",
    "MAVI.IS",
    "BERA.IS",
    "AGHOL.IS",
    "ENJSA.IS",
    "MPARK.IS",
    "RALYH.IS",
    "SOKM.IS",
    "OYAKC.IS",
    "TURSG.IS",
    "KONTR.IS",
    "TUREX.IS",
    "CANTE.IS",
    "GENIL.IS",
    "GESAN.IS",
    "YEOTK.IS",
    "MAGEN.IS",
    "MIATK.IS",
    "GRSEL.IS",
    "SMRTG.IS",
    "KCAER.IS",
    "ALFAS.IS",
    "ASTOR.IS",
    "EUPWR.IS",
    "CWENE.IS",
    "KTLEV.IS",
    "PASEU.IS",
    "ENERY.IS",
    "REEDR.IS",
    "TABGD.IS",
    "BINHO.IS",
    "AVPGY.IS",
    "LMKDC.IS",
    "OBAMS.IS",
    "ALTNY.IS",
    "EFORC.IS",
    "GRTHO.IS",
    "GLRMK.IS",
    "DSTKF.IS",
    "BALSU.IS",
]
