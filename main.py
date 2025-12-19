import asyncio
import aiohttp

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
from notifier.discord_bot import bot, send_table

from config import (
    MAX_SYMBOLS,
    REFRESH_INTERVAL,
    MIN_VOLUME_M
)


async def get_scanner_data():
    """Callback function for Discord bot to get updated scanner data"""
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


async def main():
    """Main function - now just sets up the bot"""
    # Initialize websocket connection
    symbols = (await get_futures_symbols())[:MAX_SYMBOLS]
    start_ws(symbols)

    # Set up bot callback
    bot.set_update_callback(get_scanner_data)

    print("🤖 VWAP Scanner Discord Bot")
    print("Use /start in Discord to begin scanning")
    print("Use /stop to stop scanning")

    # Start the Discord bot (this will run forever)
    await bot.start_bot()


if __name__ == "__main__":
    asyncio.run(main())
