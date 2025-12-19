from datetime import datetime, timezone as dt_timezone, timedelta
from config import SESSION_WEIGHTS
import pytz

# Session definitions with local times (matching trading session notifier)
SESSIONS_LOCAL = {
    "Sydney":    (9, 18, "Australia/Sydney"),   # 09:00-18:00 AEST/AEDT
    "Tokyo":     (9, 18, "Asia/Tokyo"),        # 09:00-18:00 JST, no DST
    "London":    (8, 17, "Europe/London"),     # 08:00-17:00 GMT/BST
    "New York":  (8, 17, "America/New_York")   # 08:00-17:00 EST/EDT
}

def detect_session():
    """Detect current active session based on UTC time and local session definitions
    
    Priority order (highest weight first when multiple sessions active):
    1. New York (weight 1.2) - 13:00-22:00 UTC
    2. London (weight 1.0) - 07:00-16:00 UTC  
    3. Tokyo (weight 0.8) - 00:00-09:00 UTC
    4. Sydney (weight 0.6) - 23:00-08:00 UTC (overnight)
    """
    now_utc = datetime.now(dt_timezone.utc)
    current_hour_utc = now_utc.hour

    # Check sessions in priority order (highest weight first)
    # This ensures when sessions overlap, we pick the highest weight session
    session_priority = ["New York", "London", "Tokyo", "Sydney"]
    
    for session_name in session_priority:
        start_local, end_local, tz_name = SESSIONS_LOCAL[session_name]
        
        # Calculate UTC hours for this session
        utc_start, utc_end = get_utc_hours_for_session(start_local, end_local, tz_name, now_utc)

        # Check if current UTC hour falls within this session
        if utc_start < utc_end:
            # Same day session
            if utc_start <= current_hour_utc < utc_end:
                return session_name, SESSION_WEIGHTS[session_name]
        else:
            # Overnight session
            if current_hour_utc >= utc_start or current_hour_utc < utc_end:
                return session_name, SESSION_WEIGHTS[session_name]

    # Default fallback
    return "London", SESSION_WEIGHTS["London"]

def get_utc_hours_for_session(start_local, end_local, tz_name, reference_date):
    """Convert local session hours to UTC hours for a given date"""
    tz = pytz.timezone(tz_name)
    local_date = reference_date.astimezone(tz).date()

    # Create local datetime objects
    start_local_dt = tz.localize(datetime.combine(local_date, datetime.min.time().replace(hour=start_local)))
    end_local_dt = tz.localize(datetime.combine(local_date, datetime.min.time().replace(hour=end_local)))

    # Handle overnight sessions
    if end_local_dt <= start_local_dt:
        end_local_dt += timedelta(days=1)

    # Convert to UTC
    start_utc = start_local_dt.astimezone(dt_timezone.utc).hour
    end_utc = end_local_dt.astimezone(dt_timezone.utc).hour

    return start_utc, end_utc

def session_start_timestamp():
    """Get timestamp for current session start (legacy function)"""
    now = datetime.now(dt_timezone.utc)
    session_name, _ = detect_session()

    # For backward compatibility, return a timestamp
    # This is a simplified version - in production you'd want more accurate logic
    if session_name == "Sydney":
        hour = 23  # Approximate UTC start
    elif session_name == "Tokyo":
        hour = 0   # Approximate UTC start
    elif session_name == "London":
        hour = 7   # Approximate UTC start
    else:  # New York
        hour = 13  # Approximate UTC start

    start = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    return int(start.timestamp() * 1000)
