import requests
import json
import os
from datetime import datetime, timezone
from sheets.sheet_writer import write_range

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]

with open("config.json") as f:
    CONFIG = json.load(f)

def get_ohlc(coin_id):
    url = "https://api.coingecko.com/api/v3/coins/{}/ohlc".format(coin_id)
    params = {"vs_currency": "usd", "days": 7}
    return requests.get(url, params=params).json()

def get_price(coin_id):
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": coin_id,
        "vs_currencies": "usd"
    }
    return requests.get(url, params=params).json()[coin_id]["usd"]

def calc_trend(ohlc):
    closes = [c[4] for c in ohlc]

    def pct_change(period):
        return round(((closes[-1] - closes[-period]) / closes[-period]) * 100, 2)

    return {
        "4h": pct_change(4),
        "1d": pct_change(24),
        "1w": pct_change(len(closes) - 1)
    }

def calc_range(price, ohlc):
    highs = [c[2] for c in ohlc]
    lows = [c[3] for c in ohlc]
    high = max(highs)
    low = min(lows)

    pos = (price - low) / (high - low)
    if pos < 0.33:
        label = "Low"
    elif pos < 0.66:
        label = "Mid"
    else:
        label = "High"

    return round(high, 2), round(low, 2), label

def bias(trend):
    bullish = sum(1 for v in trend.values() if v > 0)
    bearish = sum(1 for v in trend.values() if v < 0)

    if bullish >= 2:
        return "Bullish"
    if bearish >= 2:
        return "Bearish"
    return "Neutral"

live_price_rows = []
trend_rows = []

for token, meta in CONFIG.items():
    ohlc = get_ohlc(meta["coingecko"])
    price = get_price(meta["coingecko"])

    high, low, range_pos = calc_range(price, ohlc)
    trend = calc_trend(ohlc)

    live_price_rows.append([
        token,
        price,
        high,
        low,
        range_pos
    ])

    trend_rows.append([
        token,
        trend["4h"],
        trend["1d"],
        trend["1w"],
        bias(trend)
    ])

write_range(SPREADSHEET_ID, "Live_Price", live_price_rows)
write_range(SPREADSHEET_ID, "Trend", trend_rows)

print("Update successful", datetime.now(timezone.utc))
