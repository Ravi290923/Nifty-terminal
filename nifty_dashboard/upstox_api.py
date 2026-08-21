"""Thin REST client for Upstox's Market Quote and Historical Candle APIs.

Uses plain `requests` calls against the documented v2/v3 endpoints rather
than the official SDK, so it isn't tied to a particular SDK version — only
the streaming client (upstox_stream.py) needs the SDK, for its Protobuf
decoding.
"""

import datetime as dt
import logging

import pandas as pd
import requests

log = logging.getLogger("upstox_api")

BASE = "https://api.upstox.com"


class UpstoxAuthError(Exception):
    pass


class UpstoxREST:
    def __init__(self, access_token: str):
        if not access_token:
            raise UpstoxAuthError("No Upstox access token provided.")
        self.token = access_token
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "Authorization": f"Bearer {access_token}"})

    # ------------------------------------------------------------------ #
    def get_quotes(self, instrument_keys: list[str]) -> dict:
        """Full market quotes for up to 500 instrument_keys in one call.
        Returns {instrument_key: {"ltp": float, "change_pct": float, "raw": {...}}}.
        """
        if not instrument_keys:
            return {}
        out = {}
        # API caps at 500 keys per call; chunk defensively even though our
        # universe is well under that.
        for i in range(0, len(instrument_keys), 500):
            chunk = instrument_keys[i:i + 500]
            r = self.session.get(f"{BASE}/v2/market-quote/quotes", params={"instrument_key": ",".join(chunk)}, timeout=10)
            r.raise_for_status()
            payload = r.json()
            if payload.get("status") != "success":
                log.warning("Unexpected quotes response: %s", payload)
                continue
            for _, q in payload.get("data", {}).items():
                key = q.get("instrument_token")
                ltp = q.get("last_price")
                ohlc = q.get("ohlc") or {}
                prev_close = ohlc.get("close")
                change_pct = ((ltp - prev_close) / prev_close * 100) if (ltp and prev_close) else 0.0
                out[key] = {"ltp": ltp, "change_pct": change_pct, "raw": q}
        return out

    # ------------------------------------------------------------------ #
    def get_historical_candles(self, instrument_key: str, unit: str, interval: str, lookback_days: int) -> pd.DataFrame:
        """V3 historical candle data: /v3/historical-candle/{key}/{unit}/{interval}/{to_date}/{from_date}
        unit in {minutes, hours, days, weeks, months}; interval is the multiplier (e.g. "15", "1", "4").
        Returns a DataFrame indexed by timestamp with open/high/low/close/volume columns, oldest first.
        """
        to_date = dt.date.today().isoformat()
        from_date = (dt.date.today() - dt.timedelta(days=lookback_days)).isoformat()
        url = f"{BASE}/v3/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}"
        r = self.session.get(url, timeout=15)
        r.raise_for_status()
        payload = r.json()
        if payload.get("status") != "success":
            raise RuntimeError(f"Historical candle request failed: {payload}")
        candles = payload.get("data", {}).get("candles", [])
        if not candles:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        # Each candle: [timestamp, open, high, low, close, volume, open_interest]
        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        df = df.set_index("timestamp")[["open", "high", "low", "close", "volume"]]
        return df
