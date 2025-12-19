from datetime import datetime, timezone
from config import SESSION_WEIGHTS

def detect_session():
    h = datetime.now(timezone.utc).hour
    if 0 <= h < 8:
        return "ASIAN", SESSION_WEIGHTS["ASIAN"]
    elif 8 <= h < 16:
        return "LONDON", SESSION_WEIGHTS["LONDON"]
    else:
        return "NEW_YORK", SESSION_WEIGHTS["NEW_YORK"]

def session_start_timestamp():
    now = datetime.now(timezone.utc)
    if 0 <= now.hour < 8:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif 8 <= now.hour < 16:
        start = now.replace(hour=8, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(hour=16, minute=0, second=0, microsecond=0)

    return int(start.timestamp() * 1000)
