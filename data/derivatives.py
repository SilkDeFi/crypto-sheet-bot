import requests

BINANCE_API = "https://fapi.binance.com/fapi/v1"

def get_funding_rate(symbol):
    try:
        data = requests.get(f"{BINANCE_API}/premiumIndex", params={"symbol": symbol}).json()
        return float(data["lastFundingRate"])
    except:
        return None

def get_open_interest(symbol):
    try:
        data = requests.get(f"{BINANCE_API}/openInterest", params={"symbol": symbol}).json()
        return float(data["openInterest"])
    except:
        return None

def get_cvd_approx(symbol, limit=500):
    """
    Approximate cumulative volume delta:
    sum(buy_volume - sell_volume) over last 'limit' trades
    """
    try:
        trades = requests.get(f"{BINANCE_API}/trades", params={"symbol": symbol, "limit": limit}).json()
        cvd = 0
        for t in trades:
            qty = float(t["qty"])
            if t["isBuyerMaker"]:
                cvd -= qty
            else:
                cvd += qty
        return round(cvd, 2)
    except:
        return None
