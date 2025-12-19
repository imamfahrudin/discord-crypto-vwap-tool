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
from notifier.discord_webhook import send_table

from config import (
    MAX_SYMBOLS,
    REFRESH_INTERVAL,
    MIN_VOLUME_M
)


async def main():
    symbols = (await get_futures_symbols())[:MAX_SYMBOLS]
    start_ws(symbols)

    async with aiohttp.ClientSession() as session:
        while True:
            session_name, weight = detect_session()
            start_ts = session_start_timestamp()

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
                print("⚠️ Market kosong, skip cycle")
                await asyncio.sleep(REFRESH_INTERVAL)
                continue

            # ============================
            # SCAN & RANK
            # ============================
            ranked = scan(market, session_name, weight)

            # TERMINAL (FULL)
            render_table(ranked[:15], session_name, weight)

            # DISCORD (TOP 15, SATU MESSAGE)
            table_text = render_table(ranked[:15], session_name, weight)
            send_table(table_text)

            await asyncio.sleep(REFRESH_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
