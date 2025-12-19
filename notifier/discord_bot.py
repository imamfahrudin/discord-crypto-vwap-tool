# notifier/discord_bot.py

import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta, timezone
import sqlite3
import os
from config import DISCORD_BOT_TOKEN, REFRESH_INTERVAL, TABLE_FOOTER_TEXT, EMBED_FOOTER_TEXT
from typing import Optional
from table_generator import generate_table_image
from utils.interval_parser import parse_intervals, format_interval
from sessions.session_manager import detect_session

def get_session_flag(session_name: str) -> str:
    """Get flag emoji for trading session"""
    flags = {
        'Sydney': '🇦🇺',
        'Tokyo': '🇯🇵',
        'London': '🇬🇧',
        'New York': '🇺🇸',
        'ASIAN': '🌏',
        'LONDON': '🇬🇧',
        'NEW_YORK': '🇺🇸',
        'EUROPE': '🇪🇺',
        'ASIA': '🌏'
    }
    return flags.get(session_name.upper(), '')

def get_next_session_info() -> tuple[str, str]:
    """Get the next trading session name and start time"""
    now = datetime.now(timezone.utc)
    current_hour = now.hour
    
    if current_hour < 8:
        # Currently ASIAN, next is LONDON at 08:00 UTC
        next_session = "LONDON"
        next_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
    elif current_hour < 16:
        # Currently LONDON, next is NEW_YORK at 16:00 UTC
        next_session = "NEW_YORK"
        next_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
    else:
        # Currently NEW_YORK, next is ASIAN at 00:00 UTC (tomorrow)
        next_session = "ASIAN"
        next_time = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
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
            print("🔄 Migrating previous_rankings table structure...")
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
            print("✅ Successfully migrated previous_rankings table")
        elif 'id' not in column_names:
            print("🔄 Creating new previous_rankings table structure...")
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
            print("✅ Created new previous_rankings table")
    except Exception as e:
        print(f"⚠️ Table migration check failed (probably normal): {e}")

    # Add guild_id column if it doesn't exist (migration)
    try:
        cursor.execute("ALTER TABLE channel_states ADD COLUMN guild_id INTEGER")
        print("✅ Added guild_id column to existing database")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    conn.commit()
    conn.close()
    print("✅ Database initialized")

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

    async def setup_hook(self):
        """Setup slash commands"""
        # Note: Using traditional commands instead of slash commands for reliability
        print("✅ Bot setup complete (using traditional commands)")

        # Initialize database
        init_database()

    async def restore_channel_states(self):
        """Restore channel states from database and resume scanning"""
        saved_states = load_channel_states()

        if not saved_states:
            print("ℹ️ No previous channel states to restore")
            return

        total_states = sum(len(intervals) for intervals in saved_states.values())
        print(f"🔄 Restoring {total_states} interval states across {len(saved_states)} channels from database...")

        for channel_id, intervals_data in saved_states.items():
            for interval, state_data in intervals_data.items():
                try:
                    print(f"🔍 Attempting to restore channel {channel_id}, interval {interval}s (guild: {state_data.get('guild_id')}, server: {state_data.get('server_name')})")
                    
                    # Get the channel object - try multiple methods
                    channel = None
                    
                    # First try direct channel lookup
                    channel = self.get_channel(channel_id)
                    
                    # If that fails and we have a guild_id, try guild-specific lookup
                    if not channel and state_data.get('guild_id'):
                        guild = self.get_guild(state_data['guild_id'])
                        if guild:
                            channel = guild.get_channel(channel_id)
                            print(f"✅ Found channel via guild lookup: {guild.name}")
                    
                    if not channel:
                        print(f"⚠️ Could not find channel {channel_id} (guild: {state_data.get('guild_id')}), removing from database")
                        print(f"   Available guilds: {[g.name for g in self.guilds]}")
                        remove_channel_state(channel_id, interval)
                        continue

                    # Try to fetch the message
                    try:
                        message = await channel.fetch_message(state_data['message_id'])
                    except discord.NotFound:
                        print(f"⚠️ Message {state_data['message_id']} not found in channel {channel_id}, skipping")
                        remove_channel_state(channel_id, interval)
                        continue

                    # Check if this channel+interval is already running
                    if (channel_id in self.channel_states and 
                        interval in self.channel_states[channel_id] and 
                        self.channel_states[channel_id][interval]['running']):
                        print(f"ℹ️ Channel {channel_id} interval {interval}s already running, skipping restoration")
                        continue

                    # Initialize channel_states structure if needed
                    if channel_id not in self.channel_states:
                        self.channel_states[channel_id] = {}

                    # Restore the state
                    self.channel_states[channel_id][interval] = {
                        'message': message,
                        'running': True,
                        'task': None
                    }

                    # Resume the update loop
                    task = asyncio.create_task(self.update_loop_for_channel(channel_id, interval))
                    self.channel_states[channel_id][interval]['task'] = task

                    print(f"✅ Restored scanner in {state_data.get('channel_name', f'channel {channel_id}')} [{interval}s] - resuming updates")
                    print(f"🔄 Update loop resumed for channel {channel_id} interval {interval}s - immediate update triggered")
                    
                    # Give a small delay to ensure the update loop starts and performs immediate update
                    await asyncio.sleep(0.1)

                except Exception as e:
                    print(f"❌ Failed to restore state for channel {channel_id} interval {interval}s: {e}")
                    remove_channel_state(channel_id, interval)

        print("✅ Channel state restoration complete")

    async def update_loop_for_channel(self, channel_id, interval):
        """Update loop for a specific channel and interval"""
        print(f"🔄 Update loop started for channel {channel_id} interval {interval}s")
        first_update = True
        
        while (channel_id in self.channel_states and 
               interval in self.channel_states[channel_id] and 
               self.channel_states[channel_id][interval]['running']):
            try:
                if first_update:
                    print(f"🚀 Performing immediate update for channel {channel_id} interval {interval}s (post-restart)")
                    first_update = False
                
                print(f"📊 Getting scanner data for channel {channel_id} interval {interval}s...")
                # Get updated data from callback
                table_text = await self.update_callback()
                print(f"✅ Got scanner data ({len(table_text) if table_text else 0} chars)")

                if table_text and channel_id in self.channel_states and interval in self.channel_states[channel_id]:
                    print(f"📤 Updating message in channel {channel_id} interval {interval}s")
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
                                # Extract session and weight from "Session : ASIAN | Weight : 0.7"
                                parts = line.replace('Session : ', '').split(' | ')
                                if len(parts) >= 2:
                                    session_name = parts[0].strip()
                                    weight_part = parts[1].replace('Weight : ', '').strip()
                                    weight = weight_part
                                break

                    # Import interval formatter
                    interval_str = format_interval(interval)

                    # Calculate next update time
                    next_update = datetime.now() + timedelta(seconds=interval)
                    next_update_str = next_update.strftime('%H:%M:%S WIB')

                    # Generate table image
                    print(f"🎨 Generating table image for channel {channel_id} interval {interval}s...")
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
                    print(f"✅ Table image updated in channel {channel_id} interval {interval}s")
                elif channel_id in self.channel_states and interval in self.channel_states[channel_id]:
                    print(f"⚠️ No data to update in channel {channel_id} interval {interval}s")

            except discord.NotFound:
                print(f"❌ Message not found in channel {channel_id} interval {interval}s, stopping updates")
                if channel_id in self.channel_states and interval in self.channel_states[channel_id]:
                    self.channel_states[channel_id][interval]['running'] = False
                    del self.channel_states[channel_id][interval]
                    # Clean up empty channel entry
                    if not self.channel_states[channel_id]:
                        del self.channel_states[channel_id]
                break
            except Exception as e:
                print(f"❌ Error updating message in channel {channel_id} interval {interval}s: {e}")
                import traceback
                traceback.print_exc()
                if channel_id in self.channel_states and interval in self.channel_states[channel_id]:
                    self.channel_states[channel_id][interval]['running'] = False
                    del self.channel_states[channel_id][interval]
                    # Clean up empty channel entry
                    if not self.channel_states[channel_id]:
                        del self.channel_states[channel_id]
                break

            # Wait before next update
            print(f"⏰ Waiting {interval} seconds before next update...")
            await asyncio.sleep(interval)

    def set_update_callback(self, callback):
        """Set the callback function to get updated data"""
        self.update_callback = callback

    async def close(self):
        """Cleanup when bot is shutting down"""
        # Cancel all running update tasks
        for channel_id, intervals in self.channel_states.items():
            for interval, state in intervals.items():
                if state['task'] and not state['task'].done():
                    state['task'].cancel()
                    print(f"🛑 Cancelled update task for channel {channel_id} interval {interval}s")

        self.channel_states.clear()
        await super().close()

# Global bot instance
bot = VWAPBot()

@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord"""
    print(f"🤖 {bot.user} has connected to Discord!")
    print(f"📊 Bot is in {len(bot.guilds)} servers")
    
    # Now that we're connected, restore previous channel states
    await bot.restore_channel_states()
    
    print("🎯 Ready to receive commands! Use !start in any channel to begin scanning")

# Traditional commands (more reliable than slash commands)
@bot.command(name="start")
async def start_command(ctx):
    """Start VWAP scanner - Usage: !start"""
    print(f"🚀 VWAP BOT v2.0 - !start command received from {ctx.author}")

    channel_id = ctx.channel.id
    print(f"📝 Start command - Channel ID: {channel_id}, Guild: {ctx.guild.name if ctx.guild else 'DM'} (ID: {ctx.guild.id if ctx.guild else 'N/A'})")

    # Parse intervals from config
    intervals = parse_intervals(REFRESH_INTERVAL)
    print(f"📊 Parsed intervals: {intervals} ({', '.join(format_interval(i) for i in intervals)})")

    # Check if already running in this channel
    if channel_id in bot.channel_states:
        existing_intervals = list(bot.channel_states[channel_id].keys())
        if existing_intervals:
            print(f"⚠️ Scanner already running in channel {channel_id} with intervals: {existing_intervals}")
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
            print(f"📤 Creating message for interval {interval}s ({interval_str})...")
            
            # Send initial message
            embed = discord.Embed(
                title=f"VWAP Scanner [{interval_str}]",
                description=f"Starting VWAP scanner with {interval_str} refresh interval...\nLoading data...",
                color=discord.Color.blue()
            )

            # Send the initial message and get the message object
            message = await ctx.send(embed=embed)
            print(f"✅ Initial message sent for {interval_str}, message ID: {message.id}")

            # Initialize interval state
            bot.channel_states[channel_id][interval] = {
                'message': message,
                'running': True,
                'task': None
            }

            # Save state to database
            save_channel_state(channel_id, interval, message.id, True, server_name, ctx.channel.name, guild_id)

            # Start the update loop for this interval
            print(f"🔄 Starting update loop for channel {channel_id} interval {interval}s")
            task = asyncio.create_task(bot.update_loop_for_channel(channel_id, interval))
            bot.channel_states[channel_id][interval]['task'] = task

        intervals_str = ', '.join(format_interval(i) for i in intervals)
        print(f"✅ VWAP scanner started in channel: {ctx.channel.name} (ID: {channel_id}) with {len(intervals)} interval(s): {intervals_str}")

    except Exception as e:
        print(f"❌ Error in start_command: {e}")
        import traceback
        traceback.print_exc()
        try:
            await ctx.message.add_reaction("❌")
            await ctx.send(f"❌ Error starting scanner: {str(e)[:100]}")
        except Exception as followup_error:
            print(f"❌ Failed to send error message: {followup_error}")

@bot.command(name="stop")
async def stop_command(ctx):
    """Stop VWAP scanner - Usage: !stop"""
    print(f"📥 !stop command received from {ctx.author}")
    channel_id = ctx.channel.id

    if channel_id not in bot.channel_states or not bot.channel_states[channel_id]:
        print(f"⚠️ No scanner running in channel {channel_id}")
        await ctx.message.add_reaction("⚠️")
        await ctx.send("❌ VWAP scanner is not running in this channel!")
        return

    try:
        print(f"🛑 Stopping scanner in channel {channel_id}")
        
        # Get list of intervals before we start modifying
        intervals_to_stop = list(bot.channel_states[channel_id].keys())
        
        # Stop all intervals for this channel
        for interval in intervals_to_stop:
            interval_str = format_interval(interval)
            print(f"🛑 Stopping interval {interval}s ({interval_str})")
            
            # Stop the scanner for this interval
            bot.channel_states[channel_id][interval]['running'] = False

            # Cancel the update task
            if bot.channel_states[channel_id][interval]['task']:
                bot.channel_states[channel_id][interval]['task'].cancel()
                print(f"✅ Update task cancelled for {interval_str}")

            # Edit the message to show stopped state without image
            embed = discord.Embed(
                title=f"VWAP Scanner [{interval_str}]",
                description=f"VWAP scanner stopped",
                color=discord.Color.red()
            )

            message = bot.channel_states[channel_id][interval]['message']
            await message.edit(embed=embed, attachments=[])
            print(f"✅ Message edited to stopped state for {interval_str}")

        # React with checkmark to confirm command received
        await ctx.message.add_reaction("✅")

        # Clean up channel state
        del bot.channel_states[channel_id]

        # Remove from database (all intervals)
        remove_channel_state(channel_id)

        intervals_str = ', '.join(format_interval(i) for i in intervals_to_stop)
        print(f"⏹️ VWAP scanner stopped in channel: {ctx.channel.name} (ID: {channel_id}) - {len(intervals_to_stop)} interval(s): {intervals_str}")

    except Exception as e:
        print(f"❌ Error in stop_command: {e}")
        import traceback
        traceback.print_exc()
        try:
            await ctx.message.add_reaction("❌")
            await ctx.send(f"❌ Error stopping scanner: {str(e)[:100]}")
        except Exception as followup_error:
            print(f"❌ Failed to send error message: {followup_error}")

def send_table(table_text: str):
    """Legacy function for backward compatibility - does nothing now"""
    # This function is kept for compatibility but doesn't send anything
    # The bot handles sending/updating messages internally
    pass

async def start_bot():
    """Start the Discord bot"""
    if not DISCORD_BOT_TOKEN or DISCORD_BOT_TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("❌ DISCORD_BOT_TOKEN not set in config.py")
        print("   Please set your Discord bot token from https://discord.com/developers/applications")
        return

    # Basic token format validation
    if not DISCORD_BOT_TOKEN or len(DISCORD_BOT_TOKEN) < 50:
        print("❌ DISCORD_BOT_TOKEN appears to be invalid (too short)")
        return

    try:
        await bot.start(DISCORD_BOT_TOKEN)
    except Exception as e:
        print(f"❌ Failed to start Discord bot: {e}")
        print("   Make sure your bot token is correct and the bot has proper permissions")

def run_bot():
    """Run the bot (blocking)"""
    asyncio.run(start_bot())