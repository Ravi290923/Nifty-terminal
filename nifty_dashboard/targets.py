"""Rule-based price targets — intraday, swing (short-term), and positional
(long-term) — derived mechanically from the same support/resistance,
Fibonacci, and trend analytics already used elsewhere in this dashboard.

IMPORTANT — read before wiring this into anything real:
No technical method predicts future price with reliability. These are
transparent, explainable projections from current chart structure, not
promises. Every number here can be traced back to a specific rule (a
resistance level, a Fibonacci extension, an ATR band) so you can judge
the reasoning yourself — that transparency is the whole point, not a
claim of accuracy. Always pair with your own risk management; the
risk:reward figure is a ratio, not a probability.
"""

from nifty_dashboard import analytics


def _direction(tone: str) -> str:
    return "up" if tone == "bull" else "down" if tone == "bear" else "neutral"


def _risk_reward(current, target, stop):
    if target is None or stop is None or current == stop:
        return None
    return abs(target - current) / abs(current - stop)


def intraday_targets(df, current_price: float) -> dict:
    """Pass 15m or 1h candles. Targets = next structural level in the
    direction of the short-term trend; stop = the level on the other side;
    ATR band = a volatility-based expected range regardless of direction.
    """
    trend = analytics.classify_trend(df)
    levels = analytics.find_levels(df)
    a = analytics.atr(df, 14)
    direction = _direction(trend["tone"])

    if direction == "up":
        t1, t2, stop = levels["resistance"], levels["resistance2"], levels["support"]
    elif direction == "down":
        t1, t2, stop = levels["support"], levels["support2"], levels["resistance"]
    else:
        t1, t2, stop = levels["resistance"], levels["support"], None

    return {
        "horizon": "Intraday", "direction": direction, "trend_label": trend["label"],
        "target1": t1, "target2": t2, "stop": stop,
        "risk_reward": _risk_reward(current_price, t1, stop),
        "atr": a, "atr_band": (current_price - a, current_price + a),
        "method": "Next support/resistance in trend direction; ATR(14) for expected-move band.",
    }


def swing_targets(df) -> dict:
    """Pass daily (or 4h) candles. Targets = Fibonacci extensions (1.272 /
    1.618) of the most recent swing, projected beyond it in the trend
    direction — distinct from the retracement levels shown on the chart,
    which measure pullbacks within a swing rather than continuation beyond it.
    """
    trend = analytics.classify_trend(df)
    levels = analytics.find_levels(df)
    fib = analytics.find_fib(df)
    current = df["close"].iloc[-1]
    direction = _direction(trend["tone"])

    swing_high = max(l["price"] for l in fib["levels"])
    swing_low = min(l["price"] for l in fib["levels"])
    rng = swing_high - swing_low

    if direction == "up":
        t1, t2, stop = swing_high + 0.272 * rng, swing_high + 0.618 * rng, levels["support"]
    elif direction == "down":
        t1, t2, stop = swing_low - 0.272 * rng, swing_low - 0.618 * rng, levels["resistance"]
    else:
        t1, t2, stop = swing_high, swing_low, None

    return {
        "horizon": "Swing (short-term)", "direction": direction, "trend_label": trend["label"],
        "target1": t1, "target2": t2, "stop": stop,
        "risk_reward": _risk_reward(current, t1, stop),
        "method": "1.272 / 1.618 Fibonacci extension of the latest swing, in the trend direction.",
    }


def positional_targets(df) -> dict:
    """Pass the longest daily history available. Targets = the period's
    own high/low plus a 0.618 extension beyond it. With ~90 daily candles
    this covers roughly 4-5 months, not years — treat "long-term" as
    relative to the data on hand, not a multi-year outlook.
    """
    trend = analytics.classify_trend(df)
    levels = analytics.find_levels(df)
    current = df["close"].iloc[-1]
    period_high, period_low = df["high"].max(), df["low"].min()
    rng = period_high - period_low
    direction = _direction(trend["tone"])

    if direction == "up":
        t1, t2, stop = period_high, period_high + 0.618 * rng, levels["support2"]
    elif direction == "down":
        t1, t2, stop = period_low, period_low - 0.618 * rng, levels["resistance2"]
    else:
        t1, t2, stop = period_high, period_low, None

    return {
        "horizon": "Positional (long-term)", "direction": direction, "trend_label": trend["label"],
        "target1": t1, "target2": t2, "stop": stop,
        "risk_reward": _risk_reward(current, t1, stop),
        "period_high": period_high, "period_low": period_low,
        "method": "Period high/low plus a 0.618 extension beyond it, in the trend direction.",
    }
