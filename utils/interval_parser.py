"""
Utility functions for parsing and formatting refresh intervals
"""

def parse_intervals(interval_str: str) -> list[int]:
    """
    Parse comma-separated interval string into list of integers
    
    Args:
        interval_str: String like "120" or "600,1800,3600"
    
    Returns:
        List of integers, e.g., [120] or [600, 1800, 3600]
    
    Examples:
        >>> parse_intervals("120")
        [120]
        >>> parse_intervals("600,1800,3600")
        [600, 1800, 3600]
        >>> parse_intervals("600, 1800, 3600")  # Handles spaces
        [600, 1800, 3600]
    """
    try:
        # Split by comma and strip whitespace
        intervals = [int(x.strip()) for x in interval_str.split(',')]
        
        # Validate intervals (must be positive)
        if any(i <= 0 for i in intervals):
            raise ValueError("All intervals must be positive")
        
        return intervals
    except (ValueError, AttributeError) as e:
        print(f"⚠️ Invalid REFRESH_INTERVAL format: {interval_str}, using default [120]")
        return [120]


def format_interval(seconds: int) -> str:
    """
    Format interval in seconds to human-readable string
    
    Args:
        seconds: Number of seconds
    
    Returns:
        Formatted string like "2m", "10m", "30m", "1h"
    
    Examples:
        >>> format_interval(120)
        '2m'
        >>> format_interval(600)
        '10m'
        >>> format_interval(3600)
        '1h'
        >>> format_interval(7200)
        '2h'
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds / 3600
        if hours == int(hours):
            return f"{int(hours)}h"
        else:
            return f"{hours:.1f}h"
