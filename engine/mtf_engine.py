# engine/mtf_engine.py

def mtf_bias(tf_signals):
    """
    tf_signals = {
        "15m": "BUY",
        "1h": "BUY",
        "4h": "NEUTRAL"
    }
    """
    score = 0
    for tf, sig in tf_signals.items():
        if "BUY" in sig:
            score += 1
        elif "SELL" in sig:
            score -= 1

    if score >= 2:
        return "BULLISH"
    elif score <= -2:
        return "BEARISH"
    return "NEUTRAL"
