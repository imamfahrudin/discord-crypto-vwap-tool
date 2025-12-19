"""
Database migration script for multi-interval feature
This script migrates the old single-interval database schema to the new multi-interval schema
"""

import sqlite3
import os

# Database path
DB_PATH = '/app/data/bot_states.db' if os.path.exists('/app') else 'bot_states.db'

def migrate_database():
    """Migrate database from single-interval to multi-interval schema"""
    
    if not os.path.exists(DB_PATH):
        print("ℹ️ No existing database found, skipping migration")
        return
    
    print("🔄 Starting database migration...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if old schema exists (channel_id as PRIMARY KEY)
        cursor.execute("PRAGMA table_info(channel_states)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Check if 'interval' column exists
        if 'interval' not in column_names:
            print("📊 Old schema detected, performing migration...")
            
            # Get existing data from old table
            cursor.execute('SELECT channel_id, message_id, guild_id, running, server_name, channel_name FROM channel_states WHERE running = 1')
            old_data = cursor.fetchall()
            
            print(f"📦 Found {len(old_data)} existing channel states")
            
            # Rename old table
            cursor.execute('ALTER TABLE channel_states RENAME TO channel_states_old')
            
            # Create new table with interval column
            cursor.execute('''
                CREATE TABLE channel_states (
                    channel_id INTEGER NOT NULL,
                    interval INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    guild_id INTEGER,
                    running BOOLEAN NOT NULL DEFAULT 0,
                    server_name TEXT,
                    channel_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (channel_id, interval)
                )
            ''')
            
            # Migrate data with default interval of 120 seconds
            DEFAULT_INTERVAL = 120
            for row in old_data:
                channel_id, message_id, guild_id, running, server_name, channel_name = row
                cursor.execute('''
                    INSERT INTO channel_states 
                    (channel_id, interval, message_id, guild_id, running, server_name, channel_name, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (channel_id, DEFAULT_INTERVAL, message_id, guild_id, running, server_name, channel_name))
                print(f"✅ Migrated channel {channel_id} with default interval {DEFAULT_INTERVAL}s")
            
            # Drop old table
            cursor.execute('DROP TABLE channel_states_old')
            
            conn.commit()
            print(f"✅ Migration complete! Migrated {len(old_data)} channel states")
        else:
            print("ℹ️ Database already using new schema, no migration needed")
    
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
