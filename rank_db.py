"""
Database utilities for rank tracking
Separated to avoid circular imports
"""

import sqlite3
import os

# Database setup
DB_PATH = '/app/data/bot_states.db' if os.path.exists('/app') else 'bot_states.db'

def init_rankings_table():
    """Initialize the rankings table if it doesn't exist, or migrate if needed"""
    # Ensure directory exists (only needed for Docker path)
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if table exists and get its schema
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='previous_rankings'")
    table_exists = cursor.fetchone() is not None

    if table_exists:
        # Check if interval column exists
        cursor.execute("PRAGMA table_info(previous_rankings)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'interval' not in column_names:
            print("🔄 Migrating previous_rankings table to add interval column...")
            
            # Get existing data
            cursor.execute('SELECT id, session_name, symbol, rank, scan_time FROM previous_rankings')
            old_data = cursor.fetchall()
            
            # Drop old table
            cursor.execute('DROP TABLE previous_rankings')
            
            # Create new table with interval support
            cursor.execute('''
                CREATE TABLE previous_rankings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_name TEXT NOT NULL,
                    interval INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_name, interval, symbol)
                )
            ''')
            
            # Migrate data with default interval
            DEFAULT_INTERVAL = 120
            for old_id, session_name, symbol, rank, scan_time in old_data:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO previous_rankings 
                        (session_name, interval, symbol, rank, scan_time)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (session_name, DEFAULT_INTERVAL, symbol, rank, scan_time))
                except sqlite3.IntegrityError:
                    pass
            
            print(f"✅ Migrated {len(old_data)} ranking records to new schema")
    else:
        # Create new table with interval support
        cursor.execute('''
            CREATE TABLE previous_rankings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT NOT NULL,
                interval INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                rank INTEGER NOT NULL,
                scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_name, interval, symbol)
            )
        ''')

    conn.commit()
    conn.close()

def save_previous_rankings(session_name: str, rankings: list, interval: int = 120):
    """Save current rankings for a session and interval to database
    
    Args:
        session_name: Trading session name (Sydney, Tokyo, London, New York)
        rankings: List of (symbol, rank) tuples
        interval: Refresh interval in seconds (default: 120)
    """
    init_rankings_table()  # Ensure table exists

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Delete old rankings (keep only last 2 scans for comparison)
    # Keep the most recent scan for next comparison, delete older ones
    cursor.execute('''
        DELETE FROM previous_rankings 
        WHERE session_name = ? AND interval = ? 
        AND scan_time < (
            SELECT MAX(scan_time) 
            FROM previous_rankings 
            WHERE session_name = ? AND interval = ?
        )
    ''', (session_name, interval, session_name, interval))

    # Insert new rankings with current timestamp
    for symbol, rank in rankings:
        cursor.execute('''
            INSERT INTO previous_rankings (session_name, interval, symbol, rank, scan_time)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (session_name, interval, symbol, rank))

    conn.commit()
    conn.close()

def load_previous_rankings(session_name: str, interval: int = 120) -> list:
    """Load the most recent previous rankings for a session and interval from database
    
    Args:
        session_name: Trading session name (Sydney, Tokyo, London, New York)
        interval: Refresh interval in seconds (default: 120)
    
    Returns:
        List of (symbol, rank) tuples from the PREVIOUS scan (not current)
    """
    init_rankings_table()  # Ensure table exists

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get the second-most recent scan_time (the previous one, not current)
    cursor.execute('''
        SELECT DISTINCT scan_time 
        FROM previous_rankings
        WHERE session_name = ? AND interval = ?
        ORDER BY scan_time DESC
        LIMIT 1 OFFSET 1
    ''', (session_name, interval))
    
    previous_scan_time_row = cursor.fetchone()
    
    # If no previous scan exists, return empty list
    if not previous_scan_time_row:
        conn.close()
        return []
    
    previous_scan_time = previous_scan_time_row[0]
    
    # Get rankings from that previous scan
    cursor.execute('''
        SELECT symbol, rank FROM previous_rankings
        WHERE session_name = ? AND interval = ? AND scan_time = ?
        ORDER BY rank
    ''', (session_name, interval, previous_scan_time))

    rows = cursor.fetchall()
    conn.close()
    return [(symbol, rank) for symbol, rank in rows]