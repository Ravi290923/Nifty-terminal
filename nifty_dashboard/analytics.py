"""Chart analytics — trend classification, support/resistance, SMC market
structure, Fair Value Gaps, and Fibonacci retracement. Pure functions over a
pandas DataFrame with open/high/low/close columns (RangeIndex), so they work
identically on simulated candles and real Upstox candles.
"""

import numpy as np
import pandas as pd


def classify_trend(df: pd.DataFrame) -> dict:
    closes = df["close"].values
    short_sma = closes[-8:].mean() if len(closes) >= 8 else closes.mean()
    long_sma = closes[-21:].mean() if len(closes) >= 21 else closes.mean()
    pct = (closes[-1] - closes[0]) / closes[0] * 100

    if short_sma > long_sma * 1.006 and pct > 0.8:
        label, tone = "Strong Bullish", "bull"
    elif short_sma > long_sma:
        label, tone = "Bullish", "bull"
    elif short_sma < long_sma * 0.994 and pct < -0.8:
        label, tone = "Strong Bearish", "bear"
    elif short_sma < long_sma:
        label, tone = "Bearish", "bear"
    else:
        label, tone = "Neutral", "flat"
    return {"label": label, "tone": tone, "pct": pct}


def find_levels(df: pd.DataFrame) -> dict:
    recent = df.tail(40).reset_index(drop=True)
    resistance = recent["high"].max()
    support = recent["low"].min()

    pivot_highs, pivot_lows = [], []
    n = len(recent)
    for i in range(2, n - 2):
        h = recent["high"].iloc[i]
        l = recent["low"].iloc[i]
        window_h = recent["high"].iloc[i - 2:i + 3]
        window_l = recent["low"].iloc[i - 2:i + 3]
        if h >= window_h.max():
            pivot_highs.append(h)
        if l <= window_l.min():
            pivot_lows.append(l)

    sorted_highs = sorted([h for h in pivot_highs if h < resistance * 0.999], reverse=True)
    sorted_lows = sorted([l for l in pivot_lows if l > support * 1.001])
    resistance2 = sorted_highs[0] if sorted_highs else resistance * 0.985
    support2 = sorted_lows[0] if sorted_lows else support * 1.015
    return {"support": support, "resistance": resistance, "support2": support2, "resistance2": resistance2}


def get_pivots(df: pd.DataFrame, w: int = 2) -> list:
    pivots = []
    n = len(df)
    highs, lows = df["high"].values, df["low"].values
    for i in range(w, n - w):
        is_high = all(highs[i] >= highs[i - k] and highs[i] >= highs[i + k] for k in range(1, w + 1))
        is_low = all(lows[i] <= lows[i - k] and lows[i] <= lows[i + k] for k in range(1, w + 1))
        if is_high:
            pivots.append({"index": i, "type": "H", "price": highs[i]})
        elif is_low:
            pivots.append({"index": i, "type": "L", "price": lows[i]})
    return pivots


def analyze_smc(df: pd.DataFrame) -> dict:
    pivots = get_pivots(df, 2)
    last_high, last_low = None, None
    labeled = []
    for p in pivots:
        if p["type"] == "H":
            label = "H" if last_high is None else ("HH" if p["price"] > last_high else "LH")
            last_high = p["price"]
        else:
            label = "L" if last_low is None else ("HL" if p["price"] > last_low else "LL")
            last_low = p["price"]
        labeled.append({**p, "label": label})

    last_close = df["close"].iloc[-1]
    highs = [p for p in labeled if p["type"] == "H"]
    lows = [p for p in labeled if p["type"] == "L"]
    last_swing_high = highs[-1] if highs else None
    last_swing_low = lows[-1] if lows else None

    bos = None
    if last_swing_high and last_close > last_swing_high["price"]:
        bos = {"type": "bullish", "level": last_swing_high["price"], "label": "Bullish BOS"}
    elif last_swing_low and last_close < last_swing_low["price"]:
        bos = {"type": "bearish", "level": last_swing_low["price"], "label": "Bearish BOS"}

    if highs and lows:
        if highs[-1]["label"] == "HH" and lows[-1]["label"] == "HL":
            bias = "Bullish structure"
        elif highs[-1]["label"] == "LH" and lows[-1]["label"] == "LL":
            bias = "Bearish structure"
        else:
            bias = "Mixed / ranging"
    else:
        bias = "Forming"

    return {"pivots": labeled[-10:], "bos": bos, "bias": bias}


def find_fvgs(df: pd.DataFrame) -> list:
    fvgs = []
    highs, lows = df["high"].values, df["low"].values
    n = len(df)
    for i in range(2, n):
        a_high, a_low = highs[i - 2], lows[i - 2]
        c_high, c_low = highs[i], lows[i]
        if a_high < c_low:
            fvgs.append({"type": "bull", "from": a_high, "to": c_low, "index": i - 1})
        elif a_low > c_high:
            fvgs.append({"type": "bear", "from": c_high, "to": a_low, "index": i - 1})
    return fvgs[-6:]


def find_fib(df: pd.DataFrame) -> dict:
    recent = df.tail(40).reset_index(drop=True)
    offset = len(df) - len(recent)
    hi_idx = recent["high"].idxmax()
    lo_idx = recent["low"].idxmin()
    hi_price = recent["high"].iloc[hi_idx]
    lo_price = recent["low"].iloc[lo_idx]
    hi_idx += offset
    lo_idx += offset

    uptrend = hi_idx > lo_idx
    top, bottom = hi_price, lo_price
    rng = top - bottom
    if uptrend:
        levels = [
            {"r": 0, "price": top},
            {"r": 0.5, "price": top - 0.5 * rng},
            {"r": 0.618, "price": top - 0.618 * rng},
            {"r": 1, "price": bottom},
        ]
    else:
        levels = [
            {"r": 0, "price": bottom},
            {"r": 0.5, "price": bottom + 0.5 * rng},
            {"r": 0.618, "price": bottom + 0.618 * rng},
            {"r": 1, "price": top},
        ]
    return {"levels": levels, "uptrend": uptrend}


def atr(df: pd.DataFrame, period: int = 14) -> float:
    """Average True Range — a volatility measure used to size the ATR-based
    projected move in targets.py. Simple mean (not Wilder-smoothed) over
    the trailing `period` bars, which is precise enough for a projection
    band rather than a precise indicator value.
    """
    highs, lows, closes = df["high"].values, df["low"].values, df["close"].values
    if len(df) < 2:
        return 0.0
    trs = []
    for i in range(1, len(df)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    window = trs[-period:] if len(trs) >= period else trs
    return float(np.mean(window)) if window else 0.0
