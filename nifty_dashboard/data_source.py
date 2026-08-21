"""Single entry point the Streamlit app uses to get candles/quotes — decides
per-symbol whether it can serve real Upstox data (token + instrument_key
present) and falls back to the seeded simulator otherwise, so the app never
hard-fails just because one symbol's mapping is missing.
"""

import logging

import pandas as pd

from nifty_dashboard import simulate
from nifty_dashboard.config import TIMEFRAMES, STOCKS, NIFTY_SYMBOL, NIFTY_BASE
from nifty_dashboard.upstox_api import UpstoxREST

log = logging.getLogger("data_source")

ALL_BASES = {s["symbol"]: s["base"] for s in STOCKS}
ALL_BASES[NIFTY_SYMBOL] = NIFTY_BASE


class MarketDataProvider:
    def __init__(self, access_token: str | None, instruments: dict[str, str] | None):
        self.instruments = instruments or {}
        self.rest = None
        self.live_mode = False
        if access_token:
            try:
                self.rest = UpstoxREST(access_token)
                self.live_mode = True
            except Exception as e:
                log.warning("Upstox REST client unavailable, using simulated data: %s", e)

    def is_live_for(self, symbol: str) -> bool:
        return self.live_mode and symbol in self.instruments

    def get_candles(self, symbol: str, tf_key: str) -> tuple[pd.DataFrame, bool]:
        """Returns (dataframe, is_live). Falls back to simulated candles on
        any error so a single flaky symbol/timeframe never crashes the page.
        """
        tf_cfg = TIMEFRAMES[tf_key]
        if self.is_live_for(symbol):
            try:
                key = self.instruments[symbol]
                df = self.rest.get_historical_candles(key, tf_cfg["unit"], tf_cfg["interval"], tf_cfg["lookback_days"])
                if len(df) >= 20:
                    return df.tail(tf_cfg["count"]), True
                log.info("Too few live candles for %s/%s (%d) — using simulated fallback.", symbol, tf_key, len(df))
            except Exception as e:
                log.warning("Live candle fetch failed for %s/%s: %s — using simulated fallback.", symbol, tf_key, e)
        base = ALL_BASES.get(symbol, 1000)
        return simulate.gen_candles(symbol, base, tf_key, tf_cfg), False

    def get_quotes(self, symbols: list[str]) -> dict:
        """{symbol: {"ltp": float, "change_pct": float, "live": bool}}"""
        out = {}
        live_symbols = [s for s in symbols if self.is_live_for(s)]
        if live_symbols:
            keys = [self.instruments[s] for s in live_symbols]
            try:
                quotes = self.rest.get_quotes(keys)
                key_to_symbol = {v: k for k, v in self.instruments.items()}
                for key, q in quotes.items():
                    sym = key_to_symbol.get(key)
                    if sym:
                        out[sym] = {"ltp": q["ltp"], "change_pct": q["change_pct"], "live": True}
            except Exception as e:
                log.warning("Live quotes fetch failed: %s — falling back to simulated for this batch.", e)

        for sym in symbols:
            if sym in out:
                continue
            df, _ = self.get_candles(sym, "1d")
            last_close = df["close"].iloc[-1]
            prev_close = df["close"].iloc[-2] if len(df) > 1 else last_close
            change_pct = (last_close - prev_close) / prev_close * 100 if prev_close else 0.0
            out[sym] = {"ltp": last_close, "change_pct": change_pct, "live": False}
        return out
