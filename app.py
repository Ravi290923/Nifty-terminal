"""Nifty 50 Terminal — Streamlit + Upstox edition.

Run:
    streamlit run app.py

Works with no Upstox credentials at all (falls back to the same seeded
simulator as the JS version of this dashboard). Add an access token in the
sidebar — or in .env — to pull real quotes/candles, and optionally start
true tick-by-tick streaming.
"""

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from nifty_dashboard import analytics, charts, targets
from nifty_dashboard.config import STOCKS, TIMEFRAMES, NIFTY_SYMBOL, NIFTY_NAME, NIFTY_BASE
from nifty_dashboard.data_source import MarketDataProvider
from nifty_dashboard.msci_data import MSCI_FLOWS, METHODOLOGY, match_msci

load_dotenv()

HERE = Path(__file__).resolve().parent
INSTRUMENTS_PATH = HERE / "instruments.json"

st.set_page_config(page_title="Nifty 50 Terminal", page_icon="📈", layout="wide")

# --------------------------------------------------------------------------- #
# Theme
# --------------------------------------------------------------------------- #
BG, PANEL, BORDER = "#0A0E14", "#0F1620", "#232E3D"
BULL, BEAR, AMBER, VIOLET, BLUE, MUTED = "#34D8AE", "#F16B76", "#E8A63D", "#A78BFA", "#5FA8F5", "#7C8B9E"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');
.stApp {{ background: {BG}; color: #E8ECF2; font-family: 'Inter', sans-serif; }}
h1, h2, h3 {{ font-family: 'Sora', sans-serif !important; }}
.mono {{ font-family: 'IBM Plex Mono', monospace; }}
[data-testid="stMetricValue"] {{ font-family: 'IBM Plex Mono', monospace; }}
.badge {{ display:inline-block; padding:3px 9px; border-radius:20px; font-family:'IBM Plex Mono',monospace; font-size:11.5px; font-weight:600; }}
.badge-bull {{ background: rgba(52,216,174,0.12); color: {BULL}; }}
.badge-bear {{ background: rgba(241,107,118,0.12); color: {BEAR}; }}
.badge-flat {{ background: rgba(124,139,158,0.12); color: {MUTED}; }}
.ticker-wrap {{ overflow:hidden; white-space:nowrap; border-top:1px solid {BORDER}; border-bottom:1px solid {BORDER}; padding:7px 0; margin-bottom: 14px; }}
.ticker-move {{ display:inline-block; animation: ticker 40s linear infinite; }}
@keyframes ticker {{ 0% {{ transform: translateX(0); }} 100% {{ transform: translateX(-50%); }} }}
.ticker-item {{ display:inline-block; padding:0 16px; font-family:'IBM Plex Mono',monospace; font-size:12px; border-right:1px solid {BORDER}; }}
div[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 10px; }}
</style>
""", unsafe_allow_html=True)


def badge(tone: str, label: str) -> str:
    return f'<span class="badge badge-{tone}">{label}</span>'


# --------------------------------------------------------------------------- #
# Sidebar — Live Data (Upstox)
# --------------------------------------------------------------------------- #
if "live_ticks_on" not in st.session_state:
    st.session_state.live_ticks_on = False
if "tick_streamer" not in st.session_state:
    st.session_state.tick_streamer = None

with st.sidebar:
    st.markdown("### Live Data · Upstox")
    def _secret(name):
        try:
            return st.secrets.get(name, "")
        except Exception:
            return ""
    default_token = (
        os.getenv("UPSTOX_ANALYTICS_TOKEN") or os.getenv("UPSTOX_ACCESS_TOKEN")
        or _secret("UPSTOX_ANALYTICS_TOKEN") or _secret("UPSTOX_ACCESS_TOKEN") or ""
    )
    token = st.text_input("Access / analytics token", value=default_token, type="password",
                           help="Put it in .env as UPSTOX_ANALYTICS_TOKEN instead of pasting it here when possible.")
    instruments = {}
    if INSTRUMENTS_PATH.exists():
        instruments = json.loads(INSTRUMENTS_PATH.read_text())
        st.caption(f"{len(instruments)} instrument keys loaded from instruments.json")
    else:
        st.caption("instruments.json not found — run `python build_instrument_map.py` for real quotes/candles.")

    st.checkbox("Enable true tick streaming (experimental)", key="live_ticks_on",
                help="Uses Upstox's MarketDataStreamerV3. REST-based candles/quotes work without this.")

    if st.session_state.live_ticks_on and token and instruments:
        if st.session_state.tick_streamer is None:
            try:
                from nifty_dashboard.upstox_stream import TickStreamer
                st.session_state.tick_streamer = TickStreamer(token, list(instruments.values()))
                st.session_state.tick_streamer.start()
                st.success("Tick stream starting…")
            except Exception as e:
                st.error(f"Couldn't start tick stream: {e}")
    elif not st.session_state.live_ticks_on and st.session_state.tick_streamer is not None:
        st.session_state.tick_streamer.stop()
        st.session_state.tick_streamer = None

    st.markdown("---")
    st.caption("Illustrative data where live data isn't available — this dashboard falls back to a seeded simulator per-symbol.")

provider = MarketDataProvider(token or None, instruments)

live_tick_snapshot = {}
if st.session_state.tick_streamer is not None:
    key_to_symbol = {v: k for k, v in instruments.items()}
    raw = st.session_state.tick_streamer.snapshot()
    for key, tick in raw.items():
        sym = key_to_symbol.get(key)
        if sym and tick.get("ltp"):
            live_tick_snapshot[sym] = tick

# --------------------------------------------------------------------------- #
# Cached data access
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=30, show_spinner=False)
def cached_candles(_token, _instr_json, symbol, tf_key):
    p = MarketDataProvider(_token or None, json.loads(_instr_json) if _instr_json else {})
    df, is_live = p.get_candles(symbol, tf_key)
    return df, is_live


@st.cache_data(ttl=15, show_spinner=False)
def cached_quotes(_token, _instr_json, symbols_tuple):
    p = MarketDataProvider(_token or None, json.loads(_instr_json) if _instr_json else {})
    return p.get_quotes(list(symbols_tuple))


instr_json = json.dumps(instruments, sort_keys=True)
all_symbols = [s["symbol"] for s in STOCKS]
quotes = cached_quotes(token, instr_json, tuple(all_symbols))
for sym, tick in live_tick_snapshot.items():
    if sym in quotes:
        quotes[sym] = {"ltp": tick["ltp"], "change_pct": tick.get("change_pct") or quotes[sym]["change_pct"], "live": True}

nifty_candles, nifty_live = cached_candles(token, instr_json, NIFTY_SYMBOL, "1d")
nifty_ltp = nifty_candles["close"].iloc[-1]
nifty_prev = nifty_candles["close"].iloc[-2] if len(nifty_candles) > 1 else nifty_ltp
nifty_chg = (nifty_ltp - nifty_prev) / nifty_prev * 100 if nifty_prev else 0.0

# --------------------------------------------------------------------------- #
# Session state — navigation
# --------------------------------------------------------------------------- #
if "view" not in st.session_state:
    st.session_state.view = "dashboard"
if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = None
if "tf_key" not in st.session_state:
    st.session_state.tf_key = "1h"
if "sector_filter" not in st.session_state:
    st.session_state.sector_filter = "All"


def go_detail(symbol):
    st.session_state.view = "detail"
    st.session_state.selected_symbol = symbol


def go_dashboard():
    st.session_state.view = "dashboard"


# --------------------------------------------------------------------------- #
# Ticker marquee
# --------------------------------------------------------------------------- #
items = "".join(
    f'<span class="ticker-item">{s["symbol"]} '
    f'<span style="color:#E8ECF2">{quotes[s["symbol"]]["ltp"]:.2f}</span> '
    f'<span style="color:{BULL if quotes[s["symbol"]]["change_pct"]>=0 else BEAR}">'
    f'{"▲" if quotes[s["symbol"]]["change_pct"]>=0 else "▼"} {abs(quotes[s["symbol"]]["change_pct"]):.2f}%</span></span>'
    for s in STOCKS
)
st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{items}{items}</div></div>', unsafe_allow_html=True)

# =============================================================================
# DASHBOARD VIEW
# =============================================================================
if st.session_state.view == "dashboard":
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown('<span class="mono" style="color:#E8A63D;letter-spacing:2px;font-size:12px;">NSE · '
                     + ("LIVE UPSTOX FEED" if provider.live_mode else "SIMULATED FEED") + '</span>', unsafe_allow_html=True)
        st.markdown("# Nifty 50 Terminal")
    with c2:
        st.caption("Illustrative where live data isn't wired up for a symbol")

    # Index card
    with st.container(border=True):
        ic1, ic2, ic3 = st.columns([2, 3, 1])
        with ic1:
            st.caption(NIFTY_NAME + (" · LIVE" if nifty_live else ""))
            tone = "bull" if nifty_chg >= 0 else "bear"
            st.markdown(f'<span class="mono" style="font-size:34px;font-weight:700;">{nifty_ltp:,.2f}</span> '
                         + badge(tone, f"{nifty_chg:+.2f}%"), unsafe_allow_html=True)
        with ic2:
            st.plotly_chart(charts.sparkline_figure(nifty_candles["close"].tail(30), tone, height=54, width=380),
                             use_container_width=False, config={"displayModeBar": False})
        with ic3:
            adv = sum(1 for s in STOCKS if quotes[s["symbol"]]["change_pct"] >= 0)
            dec = len(STOCKS) - adv
            st.metric("Advances", adv)
            st.metric("Declines", dec)

    st.write("")

    # Live data status line
    if provider.live_mode:
        n_live = sum(1 for s in STOCKS if quotes[s["symbol"]]["live"])
        st.info(f"Connected to Upstox — {n_live}/{len(STOCKS)} symbols serving live quotes"
                + (", tick stream active" if live_tick_snapshot else " (REST polling; enable tick streaming in the sidebar for true ticks)"))
    else:
        st.warning("No Upstox token configured — showing simulated data. Add a token in the sidebar to go live.")

    # MSCI panel
    st.markdown("## MSCI India Review — Flow Model")
    st.caption(f"{METHODOLOGY['review']} · effective {METHODOLOGY['effective']}")
    st.caption(METHODOLOGY["limitation"] + f" USD/INR {METHODOLOGY['usd_inr']} · published flow ≈ "
               f"{METHODOLOGY['published_total']}, rounded to {METHODOLOGY['rounded_total']} · {METHODOLOGY['calibration']}.")

    mc1, mc2, mc3 = st.columns([1, 1, 2])
    dir_filter = mc1.selectbox("Direction", ["All", "BUY", "SELL", "Neutral"], key="msci_dir")
    sort_by = mc2.selectbox("Sort by", ["Flow (₹ cr)", "Old Wt %", "New Wt %", "Δ pp"], key="msci_sort")
    search = mc3.text_input("Search stock", key="msci_search")

    msci_df = pd.DataFrame(MSCI_FLOWS)
    if dir_filter != "All":
        msci_df = msci_df[msci_df["dir"] == dir_filter]
    if search:
        msci_df = msci_df[msci_df["stock"].str.contains(search, case=False)]
    sort_col = {"Flow (₹ cr)": "inr", "Old Wt %": "ow", "New Wt %": "nw", "Δ pp": "chg"}[sort_by]
    msci_df = msci_df.reindex(msci_df[sort_col].abs().sort_values(ascending=False).index if sort_col == "inr"
                               else msci_df[sort_col].sort_values(ascending=False).index)
    msci_df = msci_df.rename(columns={"stock": "Stock", "ow": "Old Wt %", "nw": "New Wt %", "chg": "Δ pp",
                                       "inr": "Flow (₹ cr)", "dir": "Direction", "status": "Status"})
    st.dataframe(
        msci_df[["Stock", "Old Wt %", "New Wt %", "Δ pp", "Flow (₹ cr)", "Direction", "Status"]],
        use_container_width=True, hide_index=True, height=380,
    )

    st.write("")

    # Sector analysis
    st.markdown("## Sectorial Analysis")
    sector_rows = {}
    for s in STOCKS:
        sector_rows.setdefault(s["sector"], []).append(quotes[s["symbol"]]["change_pct"])
    sector_avg = {sec: sum(v) / len(v) for sec, v in sector_rows.items()}
    sector_df = pd.DataFrame({"Sector": list(sector_avg.keys()), "Avg % Change": list(sector_avg.values())})
    sector_df = sector_df.sort_values("Avg % Change", ascending=False)

    import plotly.graph_objects as go
    fig = go.Figure(go.Bar(
        x=sector_df["Avg % Change"], y=sector_df["Sector"], orientation="h",
        marker_color=[BULL if v >= 0 else BEAR for v in sector_df["Avg % Change"]],
        text=[f"{v:+.2f}%" for v in sector_df["Avg % Change"]], textposition="outside",
    ))
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)",
                       plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#E8ECF2", family="IBM Plex Mono"),
                       xaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=True, zerolinecolor=BORDER),
                       yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    sel_sector = st.selectbox("Filter stock list by sector", ["All"] + sorted(sector_avg.keys()), key="sector_filter")

    st.write("")

    # Stock list
    st.markdown("## Index Constituents" + (f" · {sel_sector}" if sel_sector != "All" else ""))
    query = st.text_input("Search symbol or name…", key="stock_search")

    filtered = [s for s in STOCKS
                if (sel_sector == "All" or s["sector"] == sel_sector)
                and (not query or query.lower() in s["symbol"].lower() or query.lower() in s["name"].lower())]

    hdr = st.columns([2, 1.4, 1, 1.2, 1, 0.8])
    for c, label in zip(hdr, ["Symbol", "Sector", "LTP", "Trend", "Change", ""]):
        c.markdown(f'<span class="mono" style="color:{MUTED};font-size:11px;">{label.upper()}</span>', unsafe_allow_html=True)

    for s in filtered:
        q = quotes[s["symbol"]]
        msci = match_msci(s["name"])
        tone = "bull" if q["change_pct"] >= 0 else "bear"
        row = st.columns([2, 1.4, 1, 1.2, 1, 0.8])
        with row[0]:
            live_dot = ' <span style="color:#34D8AE;">●</span>' if q["live"] else ""
            msci_tag = ""
            if msci:
                mt = "bull" if msci["dir"] == "BUY" else "bear" if msci["dir"] == "SELL" else "flat"
                msci_tag = " " + badge(mt, f"MSCI {msci['dir']}")
            st.markdown(f'<span class="mono" style="font-weight:700;">{s["symbol"]}</span>{live_dot}{msci_tag}<br>'
                         f'<span style="color:{MUTED};font-size:12px;">{s["name"]}</span>', unsafe_allow_html=True)
        with row[1]:
            st.markdown(f'<span style="border:1px solid {BORDER};border-radius:6px;padding:2px 7px;color:{MUTED};font-size:11px;">{s["sector"]}</span>', unsafe_allow_html=True)
        with row[2]:
            st.markdown(f'<span class="mono">{q["ltp"]:.2f}</span>', unsafe_allow_html=True)
        with row[3]:
            df1d, _ = cached_candles(token, instr_json, s["symbol"], "1d")
            st.plotly_chart(charts.sparkline_figure(df1d["close"].tail(20), tone), use_container_width=False,
                             config={"displayModeBar": False}, key=f"spark_{s['symbol']}")
        with row[4]:
            st.markdown(badge(tone, f"{q['change_pct']:+.2f}%"), unsafe_allow_html=True)
        with row[5]:
            st.button("View", key=f"view_{s['symbol']}", on_click=go_detail, args=(s["symbol"],))

# =============================================================================
# DETAIL VIEW
# =============================================================================
else:
    sym = st.session_state.selected_symbol
    stock = next(s for s in STOCKS if s["symbol"] == sym)
    q = quotes[sym]

    st.button("← Back to dashboard", on_click=go_dashboard)

    dc1, dc2 = st.columns([3, 1])
    with dc1:
        st.markdown(f'# {sym} <span style="border:1px solid {BORDER};border-radius:6px;padding:3px 9px;'
                     f'color:{MUTED};font-size:13px;vertical-align:middle;">{stock["sector"]}</span>', unsafe_allow_html=True)
        st.caption(stock["name"])
    with dc2:
        live_tag = ' <span class="mono" style="color:#34D8AE;font-size:11px;">● LIVE</span>' if q["live"] else ""
        st.markdown(f'<div style="text-align:right;"><span class="mono" style="font-size:28px;font-weight:700;">'
                     f'₹{q["ltp"]:.2f}</span>{live_tag}<br>' + badge("bull" if q["change_pct"] >= 0 else "bear",
                     f'{q["change_pct"]:+.2f}% today') + '</div>', unsafe_allow_html=True)

    tf_labels = {k: v["label"] for k, v in TIMEFRAMES.items()}
    tf_key = st.radio("Timeframe", list(tf_labels.keys()), format_func=lambda k: tf_labels[k],
                       horizontal=True, key="tf_key")

    oc1, oc2, oc3 = st.columns(3)
    show_smc = oc1.checkbox("SMC Structure", value=True, key="show_smc")
    show_fvg = oc2.checkbox("Fair Value Gaps", value=True, key="show_fvg")
    show_fib = oc3.checkbox("Fibonacci", value=True, key="show_fib")

    candles, is_live = cached_candles(token, instr_json, sym, tf_key)
    levels = analytics.find_levels(candles)

    with st.container(border=True):
        st.plotly_chart(charts.build_chart(candles, show_smc, show_fvg, show_fib, levels),
                         use_container_width=True, config={"displayModeBar": False})

    p1, p2, p3 = st.columns(3)

    with p1:
        with st.container(border=True):
            st.markdown("#### Trend Analysis — All Timeframes")
            for k, cfg in TIMEFRAMES.items():
                tf_candles, _ = cached_candles(token, instr_json, sym, k)
                t = analytics.classify_trend(tf_candles)
                hl = "font-weight:700;color:#E8A63D;" if k == tf_key else f"color:{MUTED};"
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;'
                    f'border-bottom:1px solid {BORDER};">'
                    f'<span class="mono" style="{hl}width:44px;">{cfg["label"]}</span>'
                    f'<span class="mono" style="color:{BULL if t["tone"]=="bull" else BEAR if t["tone"]=="bear" else MUTED};'
                    f'flex:1;text-align:right;margin-right:10px;">{t["pct"]:+.2f}%</span>'
                    + badge(t["tone"], t["label"]) + '</div>', unsafe_allow_html=True)

    with p2:
        with st.container(border=True):
            st.markdown(f"#### Key Levels · {tf_labels[tf_key]}")
            for label, val, color in [("Resistance 2", levels["resistance2"], AMBER), ("Resistance", levels["resistance"], AMBER),
                                       ("Support", levels["support"], BLUE), ("Support 2", levels["support2"], BLUE)]:
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid {BORDER};">'
                             f'<span style="color:{color};font-size:12.5px;">{label}</span>'
                             f'<span class="mono">₹{val:.2f}</span></div>', unsafe_allow_html=True)
            if show_fib:
                fib = analytics.find_fib(candles)
                st.markdown(f'<div class="mono" style="color:{VIOLET};font-size:11px;margin-top:8px;">'
                             f'FIBONACCI · {"UP-LEG" if fib["uptrend"] else "DOWN-LEG"}</div>', unsafe_allow_html=True)
                for lvl in fib["levels"]:
                    st.markdown(f'<div style="display:flex;justify-content:space-between;padding:3px 0;">'
                                 f'<span class="mono" style="color:{VIOLET};">{lvl["r"]:.3f}</span>'
                                 f'<span class="mono">₹{lvl["price"]:.2f}</span></div>', unsafe_allow_html=True)

    with p3:
        with st.container(border=True):
            st.markdown("#### Strategy Read")
            smc = analytics.analyze_smc(candles)
            st.markdown(f'<div class="mono" style="color:{MUTED};font-size:11px;">SMC MARKET STRUCTURE</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-weight:600;margin-bottom:6px;">{smc["bias"]}</div>', unsafe_allow_html=True)
            if smc["bos"]:
                b = smc["bos"]
                st.markdown(badge("bull" if b["type"] == "bullish" else "bear", f'{b["label"]} @ ₹{b["level"]:.2f}'), unsafe_allow_html=True)
            else:
                st.caption("No recent break of structure")

            fvgs = analytics.find_fvgs(candles)
            st.markdown(f'<div class="mono" style="color:{MUTED};font-size:11px;margin-top:12px;">FAIR VALUE GAPS ({len(fvgs)})</div>', unsafe_allow_html=True)
            if not fvgs:
                st.caption("None detected in visible range")
            for f in reversed(fvgs[-3:]):
                c = BULL if f["type"] == "bull" else BEAR
                st.markdown(f'<div class="mono" style="display:flex;justify-content:space-between;font-size:12px;">'
                             f'<span style="color:{c};">{"Bullish" if f["type"]=="bull" else "Bearish"} FVG</span>'
                             f'<span>₹{min(f["from"],f["to"]):.2f}–{max(f["from"],f["to"]):.2f}</span></div>', unsafe_allow_html=True)

            fib = analytics.find_fib(candles)
            nearest = min(fib["levels"], key=lambda l: abs(l["price"] - q["ltp"]))
            st.markdown(f'<div class="mono" style="color:{MUTED};font-size:11px;margin-top:12px;">NEAREST FIB CONFLUENCE</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="mono" style="color:{VIOLET};">{nearest["r"]:.3f} level at ₹{nearest["price"]:.2f}</div>', unsafe_allow_html=True)

    st.caption("SMC / FVG / Fibonacci markers are rule-based heuristics computed from the candle data above — not investment advice.")

    # --- Price Targets ------------------------------------------------- #
    st.markdown("## Price Targets")
    st.caption("Mechanically derived from the structure above (support/resistance, Fibonacci extensions, ATR) — "
               "not a prediction and not investment advice. No strategy guarantees results; treat this as one input, "
               "check the \u2018method\u2019 line to see exactly how each number was derived, and always size positions "
               "against your own risk tolerance.")

    intraday_df, _ = cached_candles(token, instr_json, sym, "1h")
    swing_df, _ = cached_candles(token, instr_json, sym, "1d")
    positional_df, _ = cached_candles(token, instr_json, sym, "1d")  # same series; see targets.py docstring on lookback

    t_intraday = targets.intraday_targets(intraday_df, q["ltp"])
    t_swing = targets.swing_targets(swing_df)
    t_positional = targets.positional_targets(positional_df)

    tc1, tc2, tc3 = st.columns(3)
    for col, t in zip([tc1, tc2, tc3], [t_intraday, t_swing, t_positional]):
        with col:
            with st.container(border=True):
                tone = "bull" if t["direction"] == "up" else "bear" if t["direction"] == "down" else "flat"
                st.markdown(f'#### {t["horizon"]}')
                st.markdown(badge(tone, f'{t["trend_label"]} ({t["direction"]})'), unsafe_allow_html=True)
                st.write("")
                rows = [("Target 1", t["target1"], AMBER), ("Target 2", t["target2"], AMBER)]
                if t.get("stop") is not None:
                    rows.append(("Stop-loss", t["stop"], BEAR))
                for label, val, color in rows:
                    if val is None:
                        continue
                    st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
                                 f'border-bottom:1px solid {BORDER};"><span style="color:{color};font-size:12.5px;">'
                                 f'{label}</span><span class="mono">\u20b9{val:.2f}</span></div>', unsafe_allow_html=True)
                if t.get("risk_reward") is not None:
                    st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;">'
                                 f'<span style="color:{MUTED};font-size:12.5px;">Risk:Reward</span>'
                                 f'<span class="mono">1 : {t["risk_reward"]:.2f}</span></div>', unsafe_allow_html=True)
                if t.get("atr_band"):
                    lo, hi = t["atr_band"]
                    st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;">'
                                 f'<span style="color:{MUTED};font-size:12.5px;">ATR band</span>'
                                 f'<span class="mono">\u20b9{lo:.2f}\u2013{hi:.2f}</span></div>', unsafe_allow_html=True)
                st.caption(t["method"])
