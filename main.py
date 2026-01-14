import requests
import json
import os
from datetime import datetime, timezone
from sheets.sheet_writer import write_range
from data import derivatives
from sheets.sheet_writer import get_service

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
LAST_OI_FILE = "last_oi.json"
SHEET_NAME = "Main"

with open("config.json") as f:
    CONFIG = json.load(f)

# Load previous OI values
if os.path.exists(LAST_OI_FILE):
    with open(LAST_OI_FILE) as f:
        last_oi = json.load(f)
else:
    last_oi = {}

# ----- COINGECKO FUNCTIONS -----
def get_ohlc(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    params = {"vs_currency": "usd", "days": 7}
    return requests.get(url, params=params).json()

def get_price(coin_id):
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": coin_id, "vs_currencies": "usd"}
    return requests.get(url, params=params).json()[coin_id]["usd"]

def calc_trend(ohlc):
    closes = [c[4] for c in ohlc]
    def pct_change(period):
        if period >= len(closes):
            period = len(closes) - 1
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

# ----- AUTOMATIC HEADER WRITE -----
headers = [
    "Timestamp",
    "Token",
    "Price",
    "7D High",
    "7D Low",
    "Range",
    "4H %",
    "1D %",
    "1W %",
    "Bias",
    "Funding Rate",
    "Open Interest",
    "OI Δ",
    "CVD"
]

service = get_service()
service.spreadsheets().values().update(
    spreadsheetId=SPREADSHEET_ID,
    range=f"{SHEET_NAME}!B2",
    valueInputOption="RAW",
    body={"values":[headers]}
).execute()

# ----- BUILD DATA ROWS -----
rows = []

for token, meta in CONFIG.items():
    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # COINGECKO DATA
        ohlc = get_ohlc(meta["coingecko"])
        price = get_price(meta["coingecko"])
        high, low, range_pos = calc_range(price, ohlc)
        trend = calc_trend(ohlc)
        trend_bias = bias(trend)

        # BINANCE DERIVATIVES
        bin_symbol = meta.get("binance")
        funding = derivatives.get_funding_rate(bin_symbol)
        oi = derivatives.get_open_interest(bin_symbol)
        cvd = derivatives.get_cvd_approx(bin_symbol)

        # OI Δ calculation
        last_value = last_oi.get(token)
        if last_value is not None:
            oi_delta = round((oi - last_value) / last_value * 100, 2)
        else:
            oi_delta = "N/A"

        last_oi[token] = oi

        row = [
            ts,
            token,
            price,
            high,
            low,
            range_pos,
            trend["4h"],
            trend["1d"],
            trend["1w"],
            trend_bias,
            funding,
            oi,
            oi_delta,
            cvd
        ]
        rows.append(row)
    except Exception as e:
        print(f"Error processing {token}: {e}")

# ----- WRITE DATA TO B3 -----
write_range(SPREADSHEET_ID, SHEET_NAME, rows)

# Save last OI values
with open(LAST_OI_FILE, "w") as f:
    json.dump(last_oi, f)

print("Update successful", datetime.now(timezone.utc))
