# bybit/rest.py
import aiohttp
import asyncio

BASE_URL = "https://api.bybit.com"

async def fetch_json(session, url, params):
    async with session.get(url, params=params, timeout=10) as resp:
        return await resp.json()

async def get_futures_symbols():
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/v5/market/instruments-info"
        data = await fetch_json(session, url, {"category": "linear"})
        return [
            s["symbol"]
            for s in data["result"]["list"]
            if s["quoteCoin"] == "USDT" and s["status"] == "Trading"
        ]

async def get_session_candles(session, symbol, interval, start_ts):
    url = f"{BASE_URL}/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": interval,
        "start": start_ts,
        "limit": 200
    }
    data = await fetch_json(session, url, params)
    candles = []
    for c in data["result"]["list"]:
        candles.append({
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4]),
            "volume": float(c[5])
        })
    return candles
