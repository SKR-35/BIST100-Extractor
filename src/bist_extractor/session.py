import time
import random
from urllib.parse import urlencode
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd

# ---------- session builder (works on older urllib3 too) ----------
def _make_retry(max_retries: int, backoff_factor: float) -> Retry:
    try:
        # Newer urllib3
        return Retry(
            total=max_retries,
            read=max_retries,
            connect=max_retries,
            status=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET"]),
            backoff_factor=backoff_factor,
            raise_on_status=False,
        )
    except TypeError:
        # Older urllib3 (uses method_whitelist)
        return Retry(
            total=max_retries,
            read=max_retries,
            connect=max_retries,
            status=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=frozenset(["GET"]),
            backoff_factor=backoff_factor,
            raise_on_status=False,
        )

def get_yahoo_session(max_retries: int = 5, backoff_factor: float = 1.25) -> requests.Session:
    sess = requests.Session()
    retry = _make_retry(max_retries, backoff_factor)
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    sess.headers.update({
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
    })
    return sess