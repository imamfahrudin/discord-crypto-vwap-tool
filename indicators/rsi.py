def rsi(closes, period=14):
    # Pure-python (no numpy) to avoid pulling in a heavy array lib for a tiny calc
    window = [closes[i] - closes[i - 1] for i in range(1, len(closes))][-period:]
    ag = sum(d for d in window if d > 0) / len(window)
    al = sum(-d for d in window if d < 0) / len(window)
    if al == 0:
        return 100
    return round(100 - (100 / (1 + ag / al)), 2)
