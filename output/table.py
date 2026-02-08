# output/table.py
import logging

# Set up custom logging with file details
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# Create console handler
handler = logging.StreamHandler()
handler.setLevel(logging.WARNING)

# Create formatter with file details in brackets
formatter = logging.Formatter('[%(filename)s:%(lineno)d] %(levelname)s: %(message)s')
handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(handler)

def signal_icon(signal):
    return {
        "STRONG BUY": "🟢🔥",
        "BUY": "🟢",
        "NEUTRAL": "⚪",
        "SELL": "🔴",
        "STRONG SELL": "🔴🔥"
    }.get(signal, "")


def render_table(rows, session, weight):
    lines = []
    lines.append("BYBIT FUTURES VWAP SESSION SCANNER")
    lines.append(f"Session : {session} | Weight : {weight}")
    lines.append("=" * 150)
    lines.append(
        "RANK  SYMBOL          SIGNAL               SCORE    PRICE       VWAP        VOL(M)   RSI    MACD     STOCH"
    )
    lines.append("-" * 150)

    for i, r in enumerate(rows, 1):
        sig = f"{signal_icon(r['signal'])} {r['signal']}"
        lines.append(
            f"{i:<5} {r['symbol']:<14} {sig:<20} "
            f"{r['score']:<8.2f} {r['price']:<11.6g} {r['vwap']:<11.6g} "
            f"{r['volume_m']:<7.2f} {r['rsi']:<6.1f} {r['macd']:<7.2f} {r['stoch']:<6.1f}"
        )

    table_text = "\n".join(lines)
    # logger.info(table_text)      # Removed table logging to reduce clutter
    return table_text      # Discord
