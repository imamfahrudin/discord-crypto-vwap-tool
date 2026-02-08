# engine/scanner_engine.py

import os

# Load config from environment
STRONG_SCORE = int(os.environ.get('STRONG_SCORE', 80))
BUY_SCORE = int(os.environ.get('BUY_SCORE', 25))
SELL_SCORE = int(os.environ.get('SELL_SCORE', -25))
STRONG_SELL_SCORE = int(os.environ.get('STRONG_SELL_SCORE', -80))

def classify_signal(score: float) -> str:
    if score >= STRONG_SCORE:
        return "STRONG BUY"
    if score >= BUY_SCORE:
        return "BUY"
    if score <= STRONG_SELL_SCORE:
        return "STRONG SELL"
    if score <= SELL_SCORE:
        return "SELL"
    return "NEUTRAL"


def scan(market, session_name, weight):
    ranked = []

    for m in market:
        # 🔥 Volume factor (akar supaya tidak ekstrem)
        volume_factor = min((m["volume_m"] ** 0.5), 5)

        score = (
            m["vwap_dev"] *
            volume_factor *
            10 *
            weight
        )

        signal = classify_signal(score)

        ranked.append({
            **m,
            "score": round(score, 2),
            "signal": signal
        })

    # 🔥 Urutkan dari score paling besar absolute
    ranked.sort(key=lambda x: abs(x["score"]), reverse=True)
    return ranked
