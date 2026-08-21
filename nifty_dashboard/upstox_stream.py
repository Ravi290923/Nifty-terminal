"""Live tick-by-tick streaming.

Unlike quotes/candles, the tick feed is Protobuf-encoded over a WebSocket.
Rather than hand-decode that (risky to get subtly wrong), this uses
Upstox's official `upstox-python-sdk` package, whose `MarketDataStreamerV3`
handles the Protobuf decoding internally and hands back plain dicts.

Runs the streamer in a background thread and keeps the latest tick per
instrument_key in a thread-safe dict that the Streamlit app polls on each
rerun — Streamlit itself has no persistent event loop to hang a WebSocket
callback off of directly.
"""

import logging
import threading

log = logging.getLogger("upstox_stream")

try:
    import upstox_client
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


def _dig_for(d: dict, keys: tuple) -> dict:
    """Recursively search a nested dict/list for the first sub-dict that
    contains all of `keys`. The v3 feed nests ltpc under a mode-dependent
    path (`fullFeed.marketFF.ltpc`, `firstLevelWithGreeks...`, etc.); rather
    than hard-code one path, we just walk the structure.
    """
    if isinstance(d, dict):
        if all(k in d for k in keys):
            return d
        for v in d.values():
            found = _dig_for(v, keys)
            if found is not None:
                return found
    elif isinstance(d, list):
        for v in d:
            found = _dig_for(v, keys)
            if found is not None:
                return found
    return None


class TickStreamer:
    """Background-thread wrapper. Usage:

        streamer = TickStreamer(access_token, instrument_keys)
        streamer.start()
        ...
        latest = streamer.snapshot()   # {instrument_key: {"ltp": .., "change_pct": ..}}
        ...
        streamer.stop()
    """

    def __init__(self, access_token: str, instrument_keys: list[str]):
        if not SDK_AVAILABLE:
            raise RuntimeError("upstox-python-sdk is not installed. `pip install upstox-python-sdk`.")
        self.instrument_keys = instrument_keys
        self._lock = threading.Lock()
        self._latest: dict[str, dict] = {}
        self._thread = None
        self._streamer = None

        configuration = upstox_client.Configuration()
        configuration.access_token = access_token
        self._streamer = upstox_client.MarketDataStreamerV3(
            upstox_client.ApiClient(configuration), instrument_keys, "full"
        )
        self._streamer.on("message", self._on_message)
        self._streamer.on("error", lambda e: log.error("Upstox stream error: %s", e))

    def _on_message(self, message):
        try:
            feeds = message.get("feeds", {}) if isinstance(message, dict) else {}
            for key, feed in feeds.items():
                node = _dig_for(feed, ("ltp",))
                if not node:
                    continue
                ltp = node.get("ltp")
                cp = node.get("cp")  # previous day's close, per the v3 feed schema
                change_pct = ((ltp - cp) / cp * 100) if (ltp and cp) else None
                with self._lock:
                    self._latest[key] = {"ltp": ltp, "change_pct": change_pct}
        except Exception:
            log.exception("Failed to parse tick message: %r", message)

    def start(self):
        self._thread = threading.Thread(target=self._streamer.connect, daemon=True)
        self._thread.start()

    def stop(self):
        try:
            self._streamer.disconnect()
        except Exception:
            pass

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._latest)
