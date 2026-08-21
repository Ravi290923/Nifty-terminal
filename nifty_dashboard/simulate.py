"""Deterministic simulated OHLC candles — the fallback data source when no
Upstox token/instrument mapping is available, or while a real API call is
in flight. Same seeded-PRNG approach as the JS dashboard, so behaviour is
consistent between the two builds.
"""

import hashlib
import pandas as pd


def _seed_from(text: str) -> int:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big")


def _mulberry32(seed: int):
    state = {"a": seed & 0xFFFFFFFF}

    def rand():
        a = (state["a"] + 0x6D2B79F5) & 0xFFFFFFFF
        state["a"] = a
        t = a
        t = ((t ^ (t >> 15)) * (1 | t)) & 0xFFFFFFFF
        t = (t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        t ^= t >> 14
        return (t & 0xFFFFFFFF) / 4294967296.0

    return rand


def gen_candles(symbol: str, base: float, tf_key: str, tf_cfg: dict) -> pd.DataFrame:
    """Return a DataFrame with columns open/high/low/close, `tf_cfg['count']` rows."""
    rand = _mulberry32(_seed_from(symbol + tf_key))
    drift_rand = _mulberry32(_seed_from(symbol + "drift"))
    drift = (drift_rand() - 0.5) * 0.0018
    start_rand = _mulberry32(_seed_from(symbol + "start"))
    price = base * (0.95 + start_rand() * 0.1)

    rows = []
    vol = tf_cfg["vol"]
    for _ in range(tf_cfg["count"]):
        o = price
        shock = (rand() - 0.5) * 2 * vol
        c = o * (1 + shock + drift)
        if c <= 0:
            c = o * 0.99
        h = max(o, c) * (1 + rand() * vol * 0.55)
        l = min(o, c) * (1 - rand() * vol * 0.55)
        rows.append({"open": o, "high": h, "low": l, "close": c})
        price = c

    df = pd.DataFrame(rows)
    df.index = pd.RangeIndex(len(df))
    return df
