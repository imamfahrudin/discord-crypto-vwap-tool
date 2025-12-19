import asyncio
import aiohttp
from datetime import datetime

from bybit.rest import get_futures_symbols, get_session_candles
from bybit.websocket import start_ws, prices

from sessions.session_manager import detect_session, session_start_timestamp
from sessions.vwap import calculate_vwap

from indicators.rsi import rsi
from indicators.macd import macd_hist
from indicators.atr import atr
from indicators.stochastic import stochastic

from engine.scanner_engine import scan
from output.table import render_table
from notifier.discord_bot import bot, send_table, start_bot

from config import (
    MAX_SYMBOLS,
    REFRESH_INTERVAL,
    MIN_VOLUME_M
)

# Global cache for scanner data
scanner_cache = {
    'data': None,
    'last_updated': 0,
    'updating': False
}

async def update_scanner_cache():
    """Update the scanner cache in background"""
    if scanner_cache['updating']:
        return  # Already updating
    
    scanner_cache['updating'] = True
    try:
        print("🔄 Updating scanner cache...")
        data = await get_scanner_data_raw()
        scanner_cache['data'] = data
        scanner_cache['last_updated'] = asyncio.get_event_loop().time()
        print("✅ Scanner cache updated")
    except Exception as e:
        print(f"❌ Failed to update scanner cache: {e}")
    finally:
        scanner_cache['updating'] = False

async def get_scanner_data_raw():
    """Raw scanner data computation (heavy lifting)"""
    symbols = (await get_futures_symbols())[:MAX_SYMBOLS]

    session_name, weight = detect_session()
    start_ts = session_start_timestamp()

    # Create a new session for this request
    async with aiohttp.ClientSession() as session:
        tasks = [
            get_session_candles(session, s, "5", start_ts)
            for s in symbols
        ]
        candle_sets = await asyncio.gather(*tasks)

        market = []

        for s, candles in zip(symbols, candle_sets):
            if not candles or len(candles) < 30:
                continue

            closes = [c["close"] for c in candles]
            highs  = [c["high"] for c in candles]
            lows   = [c["low"] for c in candles]

            price = prices.get(s, closes[-1])
            vwap = calculate_vwap(candles)

            if not price or not vwap:
                continue

            # ============================
            # 🔥 FIX 1 — VOLUME BYBIT BENAR
            # ============================
            volumes = [
                c.get("volume", 0) * c.get("close", 0)
                for c in candles
            ]
            total_volume = sum(volumes)

            if total_volume <= 0:
                continue

            volume_m = total_volume / 1_000_000

            # ============================
            # 🔥 FIX 2 — FILTER AMAN
            # ============================
            if volume_m < MIN_VOLUME_M:
                continue

            market.append({
                "symbol": s,
                "price": price,
                "vwap": vwap,
                "volume_m": round(volume_m, 2),
                "trend": "ABOVE VWAP" if price > vwap else "BELOW VWAP",
                "vwap_dev": round((price - vwap) / vwap * 100, 2),

                "rsi": rsi(closes),
                "macd": macd_hist(closes),
                "atr": atr(highs, lows, closes),
                "stoch": stochastic(highs, lows, closes),
            })

        # ============================
        # 🔥 FIX 3 — FAILSAFE
        # ============================
        if not market:
            return "⚠️ No market data available"

        # ============================
        # SCAN & RANK
        # ============================
        ranked = scan(market, session_name, weight)

        # Return table text for Discord
        return render_table(ranked[:15], session_name, weight)

async def get_scanner_data():
    """Callback function for Discord bot to get updated scanner data"""
    current_time = asyncio.get_event_loop().time()
    
    # Check if cache is fresh (less than 30 seconds old)
    if scanner_cache['data'] and (current_time - scanner_cache['last_updated']) < 30:
        print("✅ Using cached scanner data")
        last_updated = datetime.fromtimestamp(scanner_cache['last_updated']).strftime('%H:%M:%S')
        return scanner_cache['data'], last_updated
    
    # Cache is stale, update it
    await update_scanner_cache()
    
    # Return cached data (might be None if update failed)
    if scanner_cache['data']:
        last_updated = datetime.fromtimestamp(scanner_cache['last_updated']).strftime('%H:%M:%S')
        return scanner_cache['data'], last_updated
    else:
        return "⚠️ Scanner data not available. Please try again in a moment.", "N/A"


async def main():
    """Main function - now sets up the bot first, then websocket"""
    # Set up bot callback FIRST
    bot.set_update_callback(get_scanner_data)

    print("🤖 VWAP Scanner Discord Bot v2.0 - CACHED EDITION")
    print("Use !start in Discord to begin scanning")
    print("Use !stop to stop scanning")

    # Start background cache updater
    cache_task = asyncio.create_task(cache_updater())
    
    # Start the Discord bot FIRST
    bot_task = asyncio.create_task(start_bot())

    # Wait a moment for bot to connect
    await asyncio.sleep(2)

    # THEN initialize websocket connection
    symbols = (await get_futures_symbols())[:MAX_SYMBOLS]
    start_ws(symbols)

    print("✅ WebSocket connection started")

    # Wait for bot task (this will run forever)
    await bot_task

async def cache_updater():
    """Background task to keep scanner cache fresh"""
    while True:
        try:
            await update_scanner_cache()
            await asyncio.sleep(REFRESH_INTERVAL)  # Update every refresh interval
        except Exception as e:
            print(f"❌ Cache updater error: {e}")
            await asyncio.sleep(10)  # Retry in 10 seconds on error


if __name__ == "__main__":
    asyncio.run(main())
