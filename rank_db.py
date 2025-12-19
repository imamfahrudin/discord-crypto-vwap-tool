"""
Database utilities for rank tracking
Separated to avoid circular imports
"""

import sqlite3
import os

# Database setup
DB_PATH = '/app/data/bot_states.db' if os.path.exists('/app') else 'bot_states.db'

def init_rankings_table():
    """Initialize the rankings table if it doesn't exist"""
    # Ensure directory exists (only needed for Docker path)
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create previous_rankings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS previous_rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT NOT NULL,
            symbol TEXT NOT NULL,
            rank INTEGER NOT NULL,
            scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(session_name, symbol, scan_time)
        )
    ''')

    conn.commit()
    conn.close()

def save_previous_rankings(session_name: str, rankings: list):
    """Save current rankings for a session to database"""
    init_rankings_table()  # Ensure table exists

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Insert new rankings with current timestamp
    for symbol, rank in rankings:
        cursor.execute('''
            INSERT INTO previous_rankings (session_name, symbol, rank, scan_time)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (session_name, symbol, rank))

    conn.commit()
    conn.close()

def load_previous_rankings(session_name: str) -> list:
    """Load the most recent previous rankings for a session from database"""
    init_rankings_table()  # Ensure table exists

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get the most recent scan for this session
    cursor.execute('''
        SELECT symbol, rank FROM previous_rankings
        WHERE session_name = ?
        AND scan_time = (
            SELECT MAX(scan_time) FROM previous_rankings
            WHERE session_name = ?
        )
    ''', (session_name, session_name))

    rows = cursor.fetchall()
    conn.close()
    return [(symbol, rank) for symbol, rank in rows]