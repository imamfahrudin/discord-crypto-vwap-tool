"""
Database migration script for previous_rankings table with interval support
This script migrates the old previous_rankings schema to include interval column
"""

import sqlite3
import os
import logging

# Database path
DB_PATH = '/app/data/bot_states.db' if os.path.exists('/app') else 'bot_states.db'

# Set up custom logging with file details
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)

# Create formatter with file details in brackets
formatter = logging.Formatter('[%(filename)s:%(lineno)d] %(levelname)s: %(message)s')
handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(handler)

def migrate_rankings_table():
    """Migrate previous_rankings table to include interval column"""
    
    if not os.path.exists(DB_PATH):
        logger.info("ℹ️ No existing database found, skipping migration")
        return
    
    logger.info("🔄 Starting previous_rankings table migration...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if old schema exists (without interval column)
        cursor.execute("PRAGMA table_info(previous_rankings)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Check if 'interval' column exists
        if 'interval' not in column_names:
            logger.info("📊 Old previous_rankings schema detected, performing migration...")
            
            # Get existing data from old table
            cursor.execute('SELECT id, session_name, symbol, rank, scan_time FROM previous_rankings')
            old_data = cursor.fetchall()
            
            logger.info(f"📦 Found {len(old_data)} existing ranking records")
            
            # Drop old table
            cursor.execute('DROP TABLE IF EXISTS previous_rankings')
            
            # Create new table with interval column
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
            
            # Migrate data with default interval of 120 seconds
            DEFAULT_INTERVAL = 120
            migrated_count = 0
            
            # Group by session and scan_time, keep only the most recent scan per session
            cursor.execute('''
                SELECT session_name, MAX(scan_time) as latest_time 
                FROM (SELECT DISTINCT session_name, scan_time FROM ?)
                GROUP BY session_name
            ''')
            
            # Migrate only the latest rankings for each session
            for old_id, session_name, symbol, rank, scan_time in old_data:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO previous_rankings 
                        (session_name, interval, symbol, rank, scan_time)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (session_name, DEFAULT_INTERVAL, symbol, rank, scan_time))
                    migrated_count += 1
                except sqlite3.IntegrityError:
                    # Skip duplicates
                    pass
            
            conn.commit()
            logger.info(f"✅ Migration complete! Migrated {migrated_count} ranking records with default interval {DEFAULT_INTERVAL}s")
        else:
            logger.info("ℹ️ Database already using new schema, no migration needed")
    
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_rankings_table()
