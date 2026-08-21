"""Static configuration: the tracked stock universe and timeframe grid.

Kept separate from data-fetching code so the same list drives the
simulator, the instrument-key resolver, and the Upstox REST calls.
"""

STOCKS = [
    {"symbol": "HDFCBANK", "name": "HDFC Bank", "sector": "Banking", "base": 1650},
    {"symbol": "ICICIBANK", "name": "ICICI Bank", "sector": "Banking", "base": 1210},
    {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking", "base": 815},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "Banking", "base": 1780},
    {"symbol": "AXISBANK", "name": "Axis Bank", "sector": "Banking", "base": 1145},
    {"symbol": "INDUSINDBK", "name": "IndusInd Bank", "sector": "Banking", "base": 985},
    {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT", "base": 4120},
    {"symbol": "INFY", "name": "Infosys", "sector": "IT", "base": 1890},
    {"symbol": "HCLTECH", "name": "HCL Technologies", "sector": "IT", "base": 1750},
    {"symbol": "WIPRO", "name": "Wipro", "sector": "IT", "base": 545},
    {"symbol": "TECHM", "name": "Tech Mahindra", "sector": "IT", "base": 1680},
    {"symbol": "RELIANCE", "name": "Reliance Industries", "sector": "Energy", "base": 3020},
    {"symbol": "ONGC", "name": "Oil & Natural Gas Corp", "sector": "Energy", "base": 265},
    {"symbol": "BPCL", "name": "Bharat Petroleum", "sector": "Energy", "base": 335},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "FMCG", "base": 2510},
    {"symbol": "ITC", "name": "ITC Ltd", "sector": "FMCG", "base": 465},
    {"symbol": "NESTLEIND", "name": "Nestle India", "sector": "FMCG", "base": 2385},
    {"symbol": "BRITANNIA", "name": "Britannia Industries", "sector": "FMCG", "base": 5480},
    {"symbol": "MARUTI", "name": "Maruti Suzuki", "sector": "Auto", "base": 12650},
    {"symbol": "TMPV", "name": "Tata Motors Passenger Vehicles", "sector": "Auto", "base": 985},
    {"symbol": "M&M", "name": "Mahindra & Mahindra", "sector": "Auto", "base": 3120},
    {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto", "sector": "Auto", "base": 9450},
    {"symbol": "EICHERMOT", "name": "Eicher Motors", "sector": "Auto", "base": 4890},
    {"symbol": "SUNPHARMA", "name": "Sun Pharma", "sector": "Pharma", "base": 1785},
    {"symbol": "DRREDDY", "name": "Dr Reddy's Labs", "sector": "Pharma", "base": 1245},
    {"symbol": "CIPLA", "name": "Cipla", "sector": "Pharma", "base": 1520},
    {"symbol": "DIVISLAB", "name": "Divi's Laboratories", "sector": "Pharma", "base": 5980},
    {"symbol": "TATASTEEL", "name": "Tata Steel", "sector": "Metals", "base": 165},
    {"symbol": "JSWSTEEL", "name": "JSW Steel", "sector": "Metals", "base": 985},
    {"symbol": "HINDALCO", "name": "Hindalco Industries", "sector": "Metals", "base": 685},
    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement", "sector": "Infra", "base": 11250},
    {"symbol": "LT", "name": "Larsen & Toubro", "sector": "Infra", "base": 3650},
    {"symbol": "ADANIPORTS", "name": "Adani Ports", "sector": "Infra", "base": 1420},
]

NIFTY_SYMBOL = "NIFTY50"
NIFTY_NAME = "Nifty 50 Index"
NIFTY_BASE = 24350

# key -> (label, candle count, simulated volatility per candle, Upstox v3 unit, Upstox v3 interval, lookback days for the REST call)
TIMEFRAMES = {
    "15m": {"label": "15m", "count": 90, "vol": 0.0016, "unit": "minutes", "interval": "15", "lookback_days": 5},
    "30m": {"label": "30m", "count": 90, "vol": 0.0023, "unit": "minutes", "interval": "30", "lookback_days": 10},
    "1h": {"label": "1H", "count": 90, "vol": 0.0036, "unit": "hours", "interval": "1", "lookback_days": 20},
    "4h": {"label": "4H", "count": 90, "vol": 0.0072, "unit": "hours", "interval": "4", "lookback_days": 60},
    "1d": {"label": "1D", "count": 90, "vol": 0.0145, "unit": "days", "interval": "1", "lookback_days": 180},
}
