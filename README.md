# Nifty 50 Terminal — Python edition

Same dashboard as the React artifact — sectorial analysis, an MSCI India
flow-review panel, an index/stock explorer, and a per-stock detail view
with SMC structure, Fair Value Gaps, and Fibonacci retracement overlays —
rebuilt in Python with Streamlit + Plotly, wired to the real Upstox API.

## Requirements

Python 3.10+ (the code uses `X | Y` union type hints, PEP 604).

## Quick start (simulated data, no credentials needed)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`. Everything works immediately on seeded
simulated candles — useful for checking the UI before touching API keys.

## Going live with Upstox

1. `cp .env.example .env` and paste your token into `UPSTOX_ANALYTICS_TOKEN`
   (an extended/analytics token, valid ~1 year — the kind you get from
   your Upstox developer console under "Analytics Token"). A regular daily
   `UPSTOX_ACCESS_TOKEN` works too, it'll just expire every day around
   3:30am IST.
2. Build the symbol → instrument_key mapping (downloads Upstox's published
   NSE instrument master and matches it against the dashboard's 33
   symbols):
   ```bash
   python build_instrument_map.py
   ```
   This writes `instruments.json`. Re-run it any time Upstox's file
   changes or a symbol fails to match.
3. `streamlit run app.py` — the sidebar will show your token pre-filled
   from `.env` and report how many instrument keys loaded. The ticker
   marquee, index card, and stock list all switch to real quotes/candles
   automatically for any symbol with a resolved instrument_key; anything
   unmapped quietly falls back to simulated data rather than breaking the
   page.

### True tick-by-tick streaming

REST polling (candles + quotes, refreshed every 15–30s) is on by default
once you're live — genuinely current, not literal ticks. For the real
tick feed:

- Tick the **"Enable true tick streaming"** box in the sidebar.
- This uses Upstox's official `upstox-python-sdk` (`MarketDataStreamerV3`),
  which handles the Protobuf decoding for you — no manual schema work
  needed, unlike a from-scratch WebSocket client.
- Runs in a background thread; the app polls its latest snapshot on every
  Streamlit rerun (add [`streamlit-autorefresh`](https://pypi.org/project/streamlit-autorefresh/)
  and wire it in near the top of `app.py` if you want the page to refresh
  itself every couple of seconds instead of on user interaction).

## Project layout

```
app.py                          Streamlit entrypoint / UI
build_instrument_map.py         Resolves dashboard symbols -> Upstox instrument_keys
nifty_dashboard/
  config.py                     Stock universe, sectors, timeframe grid
  msci_data.py                  MSCI India Aug-2026 review flow model (from your workbook)
  simulate.py                   Seeded random-walk candle generator (fallback)
  analytics.py                  Trend / support-resistance / SMC / FVG / Fibonacci
  upstox_api.py                 REST client: quotes + historical candles
  upstox_stream.py              True tick streaming via upstox-python-sdk
  data_source.py                Picks live vs. simulated per symbol, unifies both
  charts.py                     Plotly candlestick + overlays, sparkline
```

## Notes

- Every data-fetching function fails soft: if a symbol has no
  instrument_key, or an API call errors, that one symbol silently falls
  back to simulated candles instead of crashing the page.
- Nothing here places orders — read-only market data only.
- Keep `.env` and `instruments.json` out of version control (already
  covered in `.gitignore`).
- SMC/FVG/Fibonacci markers are rule-based heuristics computed from candle
  data, not investment advice.
