"""Builds instruments.json: {"RELIANCE": "NSE_EQ|INE...", ...}

Pulls Upstox's official NSE instrument master (documented at
https://upstox.com/developer/api-documentation/instruments/) and matches it
against the dashboard's trading symbols, so instrument_keys are never
hand-typed or guessed.

Run: python build_instrument_map.py
"""

import gzip
import json
import re
from pathlib import Path

import requests

from nifty_dashboard.config import STOCKS, NIFTY_SYMBOL

HERE = Path(__file__).resolve().parent
OUT_PATH = HERE / "instruments.json"
CACHE_PATH = HERE / "NSE.json.gz"

MASTER_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"


def load_master() -> list:
    if CACHE_PATH.exists():
        print(f"Using cached {CACHE_PATH.name} (delete it to force a re-download).")
        raw = CACHE_PATH.read_bytes()
    else:
        print("Downloading NSE instrument master (a few MB)...")
        r = requests.get(MASTER_URL, timeout=60)
        r.raise_for_status()
        raw = r.content
        CACHE_PATH.write_bytes(raw)
    return json.loads(gzip.decompress(raw))


def main():
    instruments = load_master()
    print(f"Loaded {len(instruments)} NSE instruments.")

    mapping = {}

    nifty_idx = next(
        (i for i in instruments if i.get("instrument_type") == "INDEX" and re.search(r"nifty\s*50", i.get("name", ""), re.I)),
        None,
    )
    if nifty_idx:
        mapping[NIFTY_SYMBOL] = nifty_idx["instrument_key"]
    else:
        print("Could not find the Nifty 50 index instrument — add it to instruments.json by hand if needed.")

    symbols = [s["symbol"] for s in STOCKS]
    for sym in symbols:
        hit = next(
            (i for i in instruments if i.get("segment") == "NSE_EQ" and i.get("instrument_type") == "EQ" and i.get("trading_symbol") == sym),
            None,
        )
        if hit:
            mapping[sym] = hit["instrument_key"]
        else:
            print(f'No exact match for "{sym}" — check trading_symbol in NSE.json.gz and add it to instruments.json by hand if needed.')

    OUT_PATH.write_text(json.dumps(mapping, indent=2))
    print(f"\nWrote {OUT_PATH} with {len(mapping)}/{len(symbols) + 1} symbols mapped.")


if __name__ == "__main__":
    main()
