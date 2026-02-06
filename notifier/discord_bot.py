# notifier/discord_bot.py

import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta, timezone
import sqlite3
import os
import logging
from config import DISCORD_BOT_TOKEN, REFRESH_INTERVAL, TABLE_FOOTER_TEXT, EMBED_FOOTER_TEXT
from typing import Optional
from table_generator import generate_table_image
from utils.interval_parser import parse_intervals, format_interval
from sessions.session_manager import detect_session

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

def get_session_flag(session_name: str) -> str:
    """Get flag emoji for trading session"""
    flags = {
        'SYDNEY': '🇦🇺',
        'TOKYO': '🇯🇵',
        'LONDON': '🇬🇧',
        'NEW YORK': '🇺🇸',  # Space, not underscore
        'NEW_YORK': '🇺🇸',  # Underscore for backward compatibility
        'ASIAN': '🌏',
        'EUROPE': '🇪🇺',
        'ASIA': '🌏'
    }
    return flags.get(session_name.upper(), '')

def get_next_session_info() -> tuple[str, str]:
    """Get the next trading session name and start time"""
    now = datetime.now(timezone.utc)
    
    # Session order: Sydney -> Tokyo -> London -> New York -> Sydney (next day)
    sessions_order = ["Sydney", "Tokyo", "London", "New York"]
    
    # Find current session index
    current_session, _ = detect_session()
    try:
        current_index = sessions_order.index(current_session)
        next_index = (current_index + 1) % len(sessions_order)
        next_session = sessions_order[next_index]
    except ValueError:
        # Fallback if current session not found
        next_session = "London"
    
    # Calculate approximate next session start time (this is simplified)
    # In production, you'd want more accurate timezone-aware calculation
    if next_session == "Sydney":
        # Sydney typically starts around 23:00 UTC
        next_time = now.replace(hour=23, minute=0, second=0, microsecond=0)
        if now.hour >= 23:
            next_time += timedelta(days=1)
    elif next_session == "Tokyo":
        # Tokyo typically starts around 00:00 UTC
        next_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if now.hour >= 0:
            next_time += timedelta(days=1)
    elif next_session == "London":
        # London typically starts around 07:00 UTC
        next_time = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if now.hour >= 7:
            next_time += timedelta(days=1)
    else:  # New York
        # New York typically starts around 13:00 UTC
        next_time = now.replace(hour=13, minute=0, second=0, microsecond=0)
        if now.hour >= 13:
            next_time += timedelta(days=1)
    
    # Format time as WIB (UTC+7)
    next_time_wib = next_time + timedelta(hours=7)
    time_str = next_time_wib.strftime('%H:%M:%S WIB')
    
    return next_session, time_str

# Database setup
DB_PATH = '/app/data/bot_states.db' if os.path.exists('/app') else 'bot_states.db'

def init_database():
    """Initialize the database and create tables if they don't exist"""
    # Ensure directory exists (only needed for Docker path)
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create channel_states table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channel_states (
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

    # Migrate old table structure if it exists
    try:
        # Check if old table structure exists (without id column)
        cursor.execute("PRAGMA table_info(previous_rankings)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        if 'id' not in column_names and 'updated_at' in column_names:
            logger.info("🔄 Migrating previous_rankings table structure...")
            # Create new table with proper structure
            cursor.execute('''
                CREATE TABLE previous_rankings_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_name, symbol, scan_time)
                )
            ''')

            # Copy data from old table
            cursor.execute('''
                INSERT INTO previous_rankings_new (session_name, symbol, rank, scan_time)
                SELECT session_name, symbol, rank, updated_at FROM previous_rankings
            ''')

            # Replace old table
            cursor.execute('DROP TABLE previous_rankings')
            cursor.execute('ALTER TABLE previous_rankings_new RENAME TO previous_rankings')
            logger.info("✅ Successfully migrated previous_rankings table")
        elif 'id' not in column_names:
            logger.info("🔄 Creating new previous_rankings table structure...")
            # Drop old table and create new one
            cursor.execute('DROP TABLE previous_rankings')

            cursor.execute('''
                CREATE TABLE previous_rankings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_name, symbol, scan_time)
                )
            ''')
            logger.info("✅ Created new previous_rankings table")
    except Exception as e:
        logger.warning(f"⚠️ Table migration check failed (probably normal): {e}")

    # Add guild_id column if it doesn't exist (migration)
    try:
        cursor.execute("ALTER TABLE channel_states ADD COLUMN guild_id INTEGER")
        logger.info("✅ Added guild_id column to existing database")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    conn.commit()
    conn.close()
    logger.info("✅ Database initialized")

def save_channel_state(channel_id, interval, message_id, running, server_name=None, channel_name=None, guild_id=None):
    """Save or update channel state in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO channel_states
        (channel_id, interval, message_id, guild_id, running, server_name, channel_name, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (channel_id, interval, message_id, guild_id, running, server_name, channel_name))

    conn.commit()
    conn.close()

def load_channel_states():
    """Load all channel states from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT channel_id, interval, message_id, guild_id, running, server_name, channel_name FROM channel_states WHERE running = 1')
    rows = cursor.fetchall()

    conn.close()

    states = {}
    for row in rows:
        channel_id, interval, message_id, guild_id, running, server_name, channel_name = row
        
        # Create nested structure: states[channel_id][interval]
        if channel_id not in states:
            states[channel_id] = {}
        
        states[channel_id][interval] = {
            'message_id': message_id,
            'guild_id': guild_id,
            'running': bool(running),
            'server_name': server_name,
            'channel_name': channel_name
        }

    return states

def remove_channel_state(channel_id, interval=None):
    """Remove channel state from database
    
    Args:
        channel_id: Discord channel ID
        interval: Specific interval to remove, or None to remove all intervals
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if interval is None:
        # Remove all intervals for this channel
        cursor.execute('DELETE FROM channel_states WHERE channel_id = ?', (channel_id,))
    else:
        # Remove specific interval
        cursor.execute('DELETE FROM channel_states WHERE channel_id = ? AND interval = ?', (channel_id, interval))

    conn.commit()
    conn.close()

def save_previous_rankings(session_name: str, rankings: list):
    """Save current rankings for a session to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Delete existing rankings for this session
    cursor.execute('DELETE FROM previous_rankings WHERE session_name = ?', (session_name,))

    # Insert new rankings
    for symbol, rank in rankings:
        cursor.execute('''
            INSERT INTO previous_rankings (session_name, symbol, rank, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (session_name, symbol, rank))

    conn.commit()
    conn.close()

def load_previous_rankings(session_name: str) -> list:
    """Load previous rankings for a session from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT symbol, rank FROM previous_rankings WHERE session_name = ? ORDER BY rank', (session_name,))
    rows = cursor.fetchall()

    conn.close()
    return [(symbol, rank) for symbol, rank in rows]

class VWAPBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        # Track per-channel, per-interval state
        # Structure: channel_states[channel_id][interval] = {'message': Message, 'running': bool, 'task': Task}
        self.channel_states = {}
        self.update_callback = None
        self.current_session = None
        self.session_check_task = None

    async def setup_hook(self):
        """Setup slash commands"""
        # Note: Using traditional commands instead of slash commands for reliability
        logger.info("✅ Bot setup complete (using traditional commands)")

        # Initialize database
        init_database()
        
        # Start session change monitoring
        self.session_check_task = asyncio.create_task(self.monitor_session_changes())
        logger.info("✅ Session change monitoring started")

    async def restore_channel_states(self):
        """Restore channel states from database and resume scanning"""
        saved_states = load_channel_states()

        if not saved_states:
            logger.info("ℹ️ No previous channel states to restore")
            return

        total_states = sum(len(intervals) for intervals in saved_states.values())
        logger.info(f"🔄 Restoring {total_states} interval states across {len(saved_states)} channels from database...")

        for channel_id, intervals_data in saved_states.items():
            for interval, state_data in intervals_data.items():
                try:
                    logger.info(f"🔍 Attempting to restore channel {channel_id}, interval {interval}s (guild: {state_data.get('guild_id')}, server: {state_data.get('server_name')})")
                    
                    # Get the channel object - try multiple methods
                    channel = None
                    
                    # First try direct channel lookup
                    channel = self.get_channel(channel_id)
                    
                    # If that fails and we have a guild_id, try guild-specific lookup
                    if not channel and state_data.get('guild_id'):
                        guild = self.get_guild(state_data['guild_id'])
                        if guild:
                            channel = guild.get_channel(channel_id)
                            logger.info(f"✅ Found channel via guild lookup: {guild.name}")
                    
                    if not channel:
                        logger.warning(f"⚠️ Could not find channel {channel_id} (guild: {state_data.get('guild_id')}), removing from database")
                        logger.warning(f"   Available guilds: {[g.name for g in self.guilds]}")
                        remove_channel_state(channel_id, interval)
                        continue

                    # Try to fetch the message
                    try:
                        message = await channel.fetch_message(state_data['message_id'])
                    except discord.NotFound:
                        logger.warning(f"⚠️ Message {state_data['message_id']} not found in channel {channel_id}, skipping")
                        remove_channel_state(channel_id, interval)
                        continue

                    # Check if this channel+interval is already running
                    if (channel_id in self.channel_states and 
                        interval in self.channel_states[channel_id] and 
                        self.channel_states[channel_id][interval]['running']):
                        logger.info(f"ℹ️ Channel {channel_id} interval {interval}s already running, skipping restoration")
                        continue

                    # Initialize channel_states structure if needed
                    if channel_id not in self.channel_states:
                        self.channel_states[channel_id] = {}

                    # Restore the state
                    self.channel_states[channel_id][interval] = {
                        'message': message,
                        'running': True,
                        'task': None,
                        'last_scheduled_update': datetime.now(),  # Initialize with current time
                        'reset_timer_event': asyncio.Event()  # Event to signal timer reset
                    }

                    # Resume the update loop
                    task = asyncio.create_task(self.update_loop_for_channel(channel_id, interval))
                    self.channel_states[channel_id][interval]['task'] = task

                    logger.info(f"✅ Restored scanner in {state_data.get('channel_name', f'channel {channel_id}')} [{interval}s] - resuming updates")
                    logger.info(f"🔄 Update loop resumed for channel {channel_id} interval {interval}s - immediate update triggered")
                    
                    # Give a small delay to ensure the update loop starts and performs immediate update
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"❌ Failed to restore state for channel {channel_id} interval {interval}s: {e}")
                    remove_channel_state(channel_id, interval)

        logger.info("✅ Channel state restoration complete")

    async def update_loop_for_channel(self, channel_id, interval):
        """Update loop for a specific channel and interval"""
        logger.info(f"🔄 Update loop started for channel {channel_id} interval {interval}s")
        first_update = True
        loop_count = 0
        consecutive_failures = 0
        max_consecutive_failures = 5  # Stop after 5 consecutive failures
        
        while (channel_id in self.channel_states and 
               interval in self.channel_states[channel_id] and 
               self.channel_states[channel_id][interval]['running']):
            try:
                loop_count += 1
                logger.debug(f"🔁 Update loop iteration #{loop_count} for channel {channel_id} interval {interval}s")
                
                if first_update:
                    logger.info(f"🚀 Performing immediate update for channel {channel_id} interval {interval}s (post-restart)")
                    first_update = False
                
                logger.debug(f"📊 Getting scanner data for channel {channel_id} interval {interval}s...")
                # Get updated data from callback
                table_text = await self.update_callback()
                logger.debug(f"✅ Got scanner data ({len(table_text) if table_text else 0} chars)")

                if table_text and channel_id in self.channel_states and interval in self.channel_states[channel_id]:
                    logger.debug(f"📤 Updating message in channel {channel_id} interval {interval}s")
                    # Handle both old format (string) and new format (tuple)
                    if isinstance(table_text, tuple):
                        table_data, last_updated = table_text
                    else:
                        table_data = table_text
                        # Container is set to WIB timezone, so datetime.now() gives WIB time
                        wib_time = datetime.now()
                        utc_time = datetime.utcnow()
                        last_updated = f"{wib_time.strftime('%H:%M:%S')} WIB | {utc_time.strftime('%H:%M:%S')} UTC"

                    # Parse session info from table_data
                    session_name = "UNKNOWN"
                    weight = "0.0"
                    if isinstance(table_data, str):
                        lines = table_data.split('\n')
                        for line in lines:
                            if line.startswith('Session :'):
                                # Extract session and weight from "Session : Sydney | Weight : 0.6"
                                parts = line.replace('Session : ', '').split(' | ')
                                if len(parts) >= 2:
                                    session_name = parts[0].strip()
                                    weight_part = parts[1].replace('Weight : ', '').strip()
                                    weight = weight_part
                                break

                    # Import interval formatter
                    interval_str = format_interval(interval)

                    # Update scheduled time and calculate next update
                    self.channel_states[channel_id][interval]['last_scheduled_update'] = datetime.now()
                    next_update = self.channel_states[channel_id][interval]['last_scheduled_update'] + timedelta(seconds=interval)
                    next_update_str = next_update.strftime('%H:%M:%S WIB')

                    # Generate table image
                    logger.debug(f"🎨 Generating table image for channel {channel_id} interval {interval}s...")
                    table_image = generate_table_image(table_data, session_name, weight, last_updated, TABLE_FOOTER_TEXT, interval_str, next_update_str)

                    # Create embed with image
                    # Get flag emoji for session
                    session_flag = get_session_flag(session_name)
                    
                    # Get next session info
                    next_session_name, next_session_time = get_next_session_info()
                    next_session_flag = get_session_flag(next_session_name)
                    
                    embed = discord.Embed(
                        title=f"BYBIT FUTURES VWAP SCANNER - UPDATED EVERY {interval_str.upper()}",
                        description=f"**Current Session:** {session_name} {session_flag}\n**Weight:** {weight}\n**Last Updated:** {last_updated}\n**Next Update:** {next_update_str}\n**Next Session:** {next_session_name} {next_session_flag} at {next_session_time}",
                        color=discord.Color.blue()
                    )

                    # Create file attachment
                    filename = f"vwap_scanner_{interval}s_{datetime.utcnow().strftime('%H%M%S')}.png"
                    file = discord.File(table_image, filename=filename)

                    # Set image in embed
                    embed.set_image(url=f"attachment://{filename}")

                    # Add footer if configured
                    if EMBED_FOOTER_TEXT:
                        embed.set_footer(text=EMBED_FOOTER_TEXT)

                    message = self.channel_states[channel_id][interval]['message']
                    await message.edit(embed=embed, attachments=[file])
                    logger.info(f"✅ Table image updated in channel {channel_id} interval {interval}s")
                    consecutive_failures = 0  # Reset failure counter on success
                elif channel_id in self.channel_states and interval in self.channel_states[channel_id]:
                    logger.warning(f"⚠️ No data to update in channel {channel_id} interval {interval}s")

            except discord.NotFound:
                logger.error(f"❌ Message not found in channel {channel_id} interval {interval}s, stopping updates")
                if channel_id in self.channel_states and interval in self.channel_states[channel_id]:
                    self.channel_states[channel_id][interval]['running'] = False
                    del self.channel_states[channel_id][interval]
                    # Clean up empty channel entry
                    if not self.channel_states[channel_id]:
                        del self.channel_states[channel_id]
                break
            except discord.HTTPException as e:
                consecutive_failures += 1
                error_code = getattr(e, 'code', 'Unknown')
                logger.error(f"❌ Discord HTTP error in channel {channel_id} interval {interval}s (code: {error_code}): {e}")
                
                if error_code == 429:  # Rate limit
                    retry_after = getattr(e, 'retry_after', 60)
                    logger.warning(f"⏰ Rate limited, waiting {retry_after}s before retry")
                    await asyncio.sleep(min(retry_after, 300))  # Cap at 5 minutes
                elif error_code in [500, 502, 503, 504]:  # Server errors
                    logger.warning(f"🌐 Discord server error, retrying in 30s")
                    await asyncio.sleep(30)
                elif consecutive_failures >= max_consecutive_failures:
                    logger.error(f"❌ Too many consecutive failures ({consecutive_failures}), stopping interval {interval}s")
                    if channel_id in self.channel_states and interval in self.channel_states[channel_id]:
                        self.channel_states[channel_id][interval]['running'] = False
                        del self.channel_states[channel_id][interval]
                        # Clean up empty channel entry
                        if not self.channel_states[channel_id]:
                            del self.channel_states[channel_id]
                    break
                else:
                    logger.warning(f"⚠️ HTTP error (attempt {consecutive_failures}/{max_consecutive_failures}), continuing...")
                    await asyncio.sleep(10)  # Brief pause before retry
                continue  # Skip the normal sleep and retry immediately
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"❌ Unexpected error updating message in channel {channel_id} interval {interval}s: {e}")
                import traceback
                traceback.print_exc()
                
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"❌ Too many consecutive failures ({consecutive_failures}), stopping interval {interval}s")
                    if channel_id in self.channel_states and interval in self.channel_states[channel_id]:
                        self.channel_states[channel_id][interval]['running'] = False
                        del self.channel_states[channel_id][interval]
                        # Clean up empty channel entry
                        if not self.channel_states[channel_id]:
                            del self.channel_states[channel_id]
                    break
                else:
                    logger.warning(f"⚠️ Error (attempt {consecutive_failures}/{max_consecutive_failures}), retrying in 30s...")
                    await asyncio.sleep(30)  # Wait before retry
                continue  # Skip the normal sleep and retry immediately

            # Wait before next update - with timer reset support
            logger.debug(f"⏰ Waiting {interval} seconds before next update for channel {channel_id} (next update ~{(datetime.now() + timedelta(seconds=interval)).strftime('%H:%M:%S')} WIB)...")
            
            # Wait for either timeout or reset event
            reset_event = self.channel_states[channel_id][interval]['reset_timer_event']
            try:
                await asyncio.wait_for(reset_event.wait(), timeout=interval)
                # Event was set - timer reset requested (session change)
                logger.info(f"🔄 Timer reset triggered for channel {channel_id} interval {interval}s (session change)")
                reset_event.clear()  # Clear the event for next time
                logger.debug(f"⏰ Timer reset complete, continuing to next update...")
            except asyncio.TimeoutError:
                # Normal timeout - interval elapsed
                logger.debug(f"⏰ Sleep completed for channel {channel_id} interval {interval}s, starting next update...")
                pass

    async def monitor_session_changes(self):
        """Monitor for trading session changes and trigger updates"""
        logger.info("🔍 Session change monitor started")
        
        # Wait a bit for bot to fully initialize
        await asyncio.sleep(5)
        
        # Get initial session
        try:
            self.current_session, _ = detect_session()
            logger.info(f"📊 Initial session detected: {self.current_session}")
        except Exception as e:
            logger.error(f"❌ Failed to detect initial session: {e}")
            self.current_session = "Unknown"
        
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Detect current session
                new_session, new_weight = detect_session()
                logger.debug(f"🔍 Session check: Current={self.current_session}, Detected={new_session}, Weight={new_weight}")
                
                # Check if session changed
                if new_session != self.current_session:
                    logger.info(f"🔄 SESSION CHANGE DETECTED: {self.current_session} → {new_session}")
                    logger.info(f"📊 New session weight: {new_weight}")
                    self.current_session = new_session
                    
                    # Trigger immediate update for all active channels
                    logger.info("🚀 Triggering session change updates for all scanners...")
                    await self.trigger_all_updates()
                else:
                    logger.debug(f"✅ Session unchanged: {self.current_session}")
                    
            except Exception as e:
                logger.error(f"❌ Error in session monitoring: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(60)  # Continue monitoring even if error
    
    async def trigger_all_updates(self):
        """Trigger immediate update for all active channels/intervals"""
        if not self.channel_states:
            logger.info("ℹ️ No active channels to update")
            return
        
        logger.info(f"🚀 Triggering updates for {sum(len(intervals) for intervals in self.channel_states.values())} active scanner(s)")
        
        # Collect all update tasks
        update_tasks = []
        for channel_id, intervals in self.channel_states.items():
            for interval in intervals:
                if self.channel_states[channel_id][interval]['running']:
                    # Signal timer reset for this channel/interval
                    reset_event = self.channel_states[channel_id][interval]['reset_timer_event']
                    reset_event.set()
                    logger.debug(f"🔄 Timer reset signal sent for channel {channel_id} interval {interval}s")
        
        logger.info(f"✅ Timer reset signals sent to all active scanners")

    def set_update_callback(self, callback):
        """Set the callback function to get updated data"""
        self.update_callback = callback

    async def close(self):
        """Cleanup when bot is shutting down"""
        # Cancel session monitoring task
        if self.session_check_task and not self.session_check_task.done():
            self.session_check_task.cancel()
            logger.info("🛑 Cancelled session monitoring task")
        
        # Cancel all running update tasks
        for channel_id, intervals in self.channel_states.items():
            for interval, state in intervals.items():
                if state['task'] and not state['task'].done():
                    state['task'].cancel()
                    logger.info(f"🛑 Cancelled update task for channel {channel_id} interval {interval}s")

        self.channel_states.clear()
        await super().close()

# Global bot instance
bot = VWAPBot()

@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord"""
    logger.info(f"🤖 {bot.user} has connected to Discord!")
    logger.info(f"📊 Bot is in {len(bot.guilds)} servers")
    
    # Now that we're connected, restore previous channel states
    await bot.restore_channel_states()
    
    logger.info("🎯 Ready to receive commands! Use !start in any channel to begin scanning")

# Traditional commands (more reliable than slash commands)
@bot.command(name="start")
async def start_command(ctx):
    """Start VWAP scanner - Usage: !start"""
    logger.info(f"🚀 VWAP BOT v2.0 - !start command received from {ctx.author}")

    channel_id = ctx.channel.id
    logger.info(f"📝 Start command - Channel ID: {channel_id}, Guild: {ctx.guild.name if ctx.guild else 'DM'} (ID: {ctx.guild.id if ctx.guild else 'N/A'})")

    # Parse intervals from config
    intervals = parse_intervals(REFRESH_INTERVAL)
    logger.info(f"📊 Parsed intervals: {intervals} ({', '.join(format_interval(i) for i in intervals)})")

    # Check if already running in this channel
    if channel_id in bot.channel_states:
        existing_intervals = list(bot.channel_states[channel_id].keys())
        if existing_intervals:
            logger.warning(f"⚠️ Scanner already running in channel {channel_id} with intervals: {existing_intervals}")
            await ctx.message.add_reaction("⚠️")
            intervals_str = ', '.join(format_interval(i) for i in existing_intervals)
            await ctx.send(f"🔄 VWAP scanner is already running in this channel!\nActive intervals: {intervals_str}")
            return

    try:
        # React with checkmark to confirm command received
        await ctx.message.add_reaction("✅")

        # Initialize channel state structure
        if channel_id not in bot.channel_states:
            bot.channel_states[channel_id] = {}

        server_name = ctx.guild.name if ctx.guild else "DM"
        guild_id = ctx.guild.id if ctx.guild else None

        # Create a message and start update loop for each interval
        for interval in intervals:
            interval_str = format_interval(interval)
            logger.info(f"📤 Creating message for interval {interval}s ({interval_str})...")
            
            # Send initial message
            embed = discord.Embed(
                title=f"VWAP Scanner [{interval_str}]",
                description=f"Starting VWAP scanner with {interval_str} refresh interval...\nLoading data...",
                color=discord.Color.blue()
            )

            # Send the initial message and get the message object
            message = await ctx.send(embed=embed)
            logger.info(f"✅ Initial message sent for {interval_str}, message ID: {message.id}")

            # Initialize interval state
            bot.channel_states[channel_id][interval] = {
                'message': message,
                'running': True,
                'task': None,
                'last_scheduled_update': datetime.now(),  # Track scheduled update time
                'reset_timer_event': asyncio.Event()  # Event to signal timer reset
            }

            # Save state to database
            save_channel_state(channel_id, interval, message.id, True, server_name, ctx.channel.name, guild_id)

            # Start the update loop for this interval
            logger.info(f"🔄 Starting update loop for channel {channel_id} interval {interval}s")
            task = asyncio.create_task(bot.update_loop_for_channel(channel_id, interval))
            bot.channel_states[channel_id][interval]['task'] = task

        intervals_str = ', '.join(format_interval(i) for i in intervals)
        logger.info(f"✅ VWAP scanner started in channel: {ctx.channel.name} (ID: {channel_id}) with {len(intervals)} interval(s): {intervals_str}")

    except Exception as e:
        logger.error(f"❌ Error in start_command: {e}")
        import traceback
        traceback.print_exc()
        try:
            await ctx.message.add_reaction("❌")
            await ctx.send(f"❌ Error starting scanner: {str(e)[:100]}")
        except Exception as followup_error:
            logger.error(f"❌ Failed to send error message: {followup_error}")

@bot.command(name="stop")
async def stop_command(ctx):
    """Stop VWAP scanner - Usage: !stop"""
    logger.info(f"📥 !stop command received from {ctx.author}")
    channel_id = ctx.channel.id

    if channel_id not in bot.channel_states or not bot.channel_states[channel_id]:
        logger.warning(f"⚠️ No scanner running in channel {channel_id}")
        await ctx.message.add_reaction("⚠️")
        await ctx.send("❌ VWAP scanner is not running in this channel!")
        return

    try:
        logger.info(f"🛑 Stopping scanner in channel {channel_id}")
        
        # Get list of intervals before we start modifying
        intervals_to_stop = list(bot.channel_states[channel_id].keys())
        
        # Stop all intervals for this channel
        for interval in intervals_to_stop:
            interval_str = format_interval(interval)
            logger.info(f"🛑 Stopping interval {interval}s ({interval_str})")
            
            # Stop the scanner for this interval
            bot.channel_states[channel_id][interval]['running'] = False

            # Cancel the update task
            if bot.channel_states[channel_id][interval]['task']:
                bot.channel_states[channel_id][interval]['task'].cancel()
                logger.info(f"✅ Update task cancelled for {interval_str}")

            # Edit the message to show stopped state without image
            embed = discord.Embed(
                title=f"VWAP Scanner [{interval_str}]",
                description=f"VWAP scanner stopped",
                color=discord.Color.red()
            )

            message = bot.channel_states[channel_id][interval]['message']
            await message.edit(embed=embed, attachments=[])
            logger.info(f"✅ Message edited to stopped state for {interval_str}")

        # React with checkmark to confirm command received
        await ctx.message.add_reaction("✅")

        # Clean up channel state
        del bot.channel_states[channel_id]

        # Remove from database (all intervals)
        remove_channel_state(channel_id)

        intervals_str = ', '.join(format_interval(i) for i in intervals_to_stop)
        logger.info(f"⏹️ VWAP scanner stopped in channel: {ctx.channel.name} (ID: {channel_id}) - {len(intervals_to_stop)} interval(s): {intervals_str}")

    except Exception as e:
        logger.error(f"❌ Error in stop_command: {e}")
        import traceback
        traceback.print_exc()
        try:
            await ctx.message.add_reaction("❌")
            await ctx.send(f"❌ Error stopping scanner: {str(e)[:100]}")
        except Exception as followup_error:
            logger.error(f"❌ Failed to send error message: {followup_error}")

@bot.command(name="session")
async def session_command(ctx):
    """Check current session and trigger manual update - Usage: !session"""
    logger.info(f"📊 !session command received from {ctx.author}")
    
    try:
        # Get current session
        current_session, weight = detect_session()
        
        # Get next session info
        next_session_name, next_session_time = get_next_session_info()
        
        # Get session flags
        current_flag = get_session_flag(current_session)
        next_flag = get_session_flag(next_session_name)
        
        # Check monitoring task status
        monitoring_status = "✅ Running" if bot.session_check_task and not bot.session_check_task.done() else "❌ Not running"
        
        # Create info embed
        embed = discord.Embed(
            title="📊 Session Status",
            description=f"**Current Session:** {current_session} {current_flag}\n**Weight:** {weight}\n**Next Session:** {next_session_name} {next_flag} at {next_session_time}\n**Monitoring Task:** {monitoring_status}\n**Tracked Session:** {bot.current_session}",
            color=discord.Color.blue()
        )
        
        # Count active scanners
        active_count = sum(len(intervals) for intervals in bot.channel_states.values())
        embed.add_field(name="Active Scanners", value=f"{active_count} scanner(s) running", inline=False)
        
        await ctx.send(embed=embed)
        
        # Trigger manual update for all scanners
        if active_count > 0:
            await ctx.send("🔄 Triggering manual update for all scanners...")
            await bot.trigger_all_updates()
            await ctx.send("✅ Manual update completed!")
        
    except Exception as e:
        logger.error(f"❌ Error in session_command: {e}")
        import traceback
        traceback.print_exc()
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name="health")
async def health_command(ctx):
    """Check health status of all active scanners - Usage: !health"""
    logger.info(f"🏥 !health command received from {ctx.author}")
    
    try:
        embed = discord.Embed(
            title="🏥 VWAP Scanner Health Status",
            description="Current status of all active scanner intervals",
            color=discord.Color.green()
        )
        
        if not bot.channel_states:
            embed.add_field(name="Status", value="❌ No active scanners", inline=False)
            await ctx.send(embed=embed)
            return
        
        total_scanners = 0
        healthy_scanners = 0
        
        for channel_id, intervals in bot.channel_states.items():
            channel_name = "Unknown"
            try:
                channel = bot.get_channel(channel_id)
                if channel:
                    channel_name = channel.name
            except:
                channel_name = f"ID: {channel_id}"
            
            embed.add_field(
                name=f"📺 Channel: {channel_name}",
                value=f"Active intervals: {len(intervals)}",
                inline=False
            )
            
            for interval in intervals:
                total_scanners += 1
                interval_str = format_interval(interval)
                state = intervals[interval]
                
                # Calculate time since last successful update
                last_update = state.get('last_scheduled_update')
                if last_update:
                    time_since_update = datetime.now() - last_update
                    minutes_since = time_since_update.total_seconds() / 60
                    
                    if minutes_since < interval / 60 * 1.5:  # Within 1.5x the interval
                        status = "✅ Healthy"
                        healthy_scanners += 1
                        color = "🟢"
                    elif minutes_since < interval / 60 * 3:  # Within 3x the interval
                        status = "⚠️ Delayed"
                        color = "🟡"
                    else:
                        status = "❌ Stale"
                        color = "🔴"
                    
                    time_str = f"{minutes_since:.1f}min ago"
                else:
                    status = "❓ Never updated"
                    time_str = "N/A"
                    color = "⚪"
                
                running_status = "▶️ Running" if state['running'] else "⏸️ Stopped"
                
                embed.add_field(
                    name=f"{color} {interval_str} ({running_status})",
                    value=f"Status: {status}\nLast Update: {time_str}",
                    inline=True
                )
        
        # Summary
        embed.add_field(
            name="📊 Summary",
            value=f"Total: {total_scanners} | Healthy: {healthy_scanners} | Issues: {total_scanners - healthy_scanners}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Error in health_command: {e}")
        import traceback
        traceback.print_exc()
        await ctx.send(f"❌ Error checking health: {str(e)}")

def send_table(table_text: str):
    """Legacy function for backward compatibility - does nothing now"""
    # This function is kept for compatibility but doesn't send anything
    # The bot handles sending/updating messages internally
    pass
    """Legacy function for backward compatibility - does nothing now"""
    # This function is kept for compatibility but doesn't send anything
    # The bot handles sending/updating messages internally
    pass

async def start_bot():
    """Start the Discord bot"""
    if not DISCORD_BOT_TOKEN or DISCORD_BOT_TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        logger.error("❌ DISCORD_BOT_TOKEN not set in config.py")
        logger.error("   Please set your Discord bot token from https://discord.com/developers/applications")
        return

    # Basic token format validation
    if not DISCORD_BOT_TOKEN or len(DISCORD_BOT_TOKEN) < 50:
        logger.error("❌ DISCORD_BOT_TOKEN appears to be invalid (too short)")
        return

    max_retries = 5
    retry_delay = 60  # Start with 60 seconds
    for attempt in range(max_retries):
        try:
            logger.info(f"🚀 Starting Discord bot... (attempt {attempt + 1}/{max_retries})")
            await bot.start(DISCORD_BOT_TOKEN)
            break  # Success, exit loop
        except discord.errors.HTTPException as e:
            if e.status == 429:
                logger.warning(f"⚠️ Rate limited (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"❌ HTTP Error: {e}")
                raise
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            raise
    else:
        logger.error(f"❌ Failed to start bot after {max_retries} attempts due to rate limiting.")

def run_bot():
    """Run the bot (blocking)"""
    asyncio.run(start_bot())