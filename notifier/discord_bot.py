# notifier/discord_bot.py

import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import sqlite3
import os
from config import DISCORD_BOT_TOKEN, REFRESH_INTERVAL
from typing import Optional
from table_generator import generate_table_image

# Database setup
DB_PATH = '/app/data/bot_states.db' if os.path.exists('/app') else 'bot_states.db'

def init_database():
    """Initialize the database and create tables if they don't exist"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create channel_states table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channel_states (
            channel_id INTEGER PRIMARY KEY,
            message_id INTEGER NOT NULL,
            guild_id INTEGER,
            running BOOLEAN NOT NULL DEFAULT 0,
            server_name TEXT,
            channel_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

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

def save_channel_state(channel_id, message_id, running, server_name=None, channel_name=None, guild_id=None):
    """Save or update channel state in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO channel_states
        (channel_id, message_id, guild_id, running, server_name, channel_name, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (channel_id, message_id, guild_id, running, server_name, channel_name))

    conn.commit()
    conn.close()

def load_channel_states():
    """Load all channel states from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT channel_id, message_id, guild_id, running, server_name, channel_name FROM channel_states WHERE running = 1')
    rows = cursor.fetchall()

    conn.close()

    states = {}
    for row in rows:
        channel_id, message_id, guild_id, running, server_name, channel_name = row
        states[channel_id] = {
            'message_id': message_id,
            'guild_id': guild_id,
            'running': bool(running),
            'server_name': server_name,
            'channel_name': channel_name
        }

    return states

def remove_channel_state(channel_id):
    """Remove channel state from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM channel_states WHERE channel_id = ?', (channel_id,))

    conn.commit()
    conn.close()

class VWAPBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        # Track per-channel state
        self.channel_states = {}  # channel_id -> {'message': Message, 'running': bool, 'task': Task}
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

        print(f"🔄 Restoring {len(saved_states)} channel states from database...")

        for channel_id, state_data in saved_states.items():
            try:
                print(f"🔍 Attempting to restore channel {channel_id} (guild: {state_data.get('guild_id')}, server: {state_data.get('server_name')})")
                
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
                    remove_channel_state(channel_id)
                    continue

                # Try to fetch the message
                try:
                    message = await channel.fetch_message(state_data['message_id'])
                except discord.NotFound:
                    print(f"⚠️ Message {state_data['message_id']} not found in channel {channel_id}, skipping")
                    remove_channel_state(channel_id)
                    continue

                # Check if this channel is already running (maybe from a manual !start command)
                if channel_id in self.channel_states and self.channel_states[channel_id]['running']:
                    print(f"ℹ️ Channel {channel_id} already running, skipping restoration")
                    continue

                # Restore the state
                self.channel_states[channel_id] = {
                    'message': message,
                    'running': True,
                    'task': None
                }

                # Resume the update loop
                task = asyncio.create_task(self.update_loop_for_channel(channel_id))
                self.channel_states[channel_id]['task'] = task

                print(f"✅ Restored scanner in {state_data.get('channel_name', f'channel {channel_id}')} - resuming updates")
                print(f"🔄 Update loop resumed for channel {channel_id} - immediate update triggered")
                
                # Give a small delay to ensure the update loop starts and performs immediate update
                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"❌ Failed to restore state for channel {channel_id}: {e}")
                remove_channel_state(channel_id)

        print("✅ Channel state restoration complete")

    async def update_loop_for_channel(self, channel_id):
        """Update loop for a specific channel"""
        print(f"🔄 Update loop started for channel {channel_id}")
        first_update = True
        
        while channel_id in self.channel_states and self.channel_states[channel_id]['running']:
            try:
                if first_update:
                    print(f"🚀 Performing immediate update for channel {channel_id} (post-restart)")
                    first_update = False
                
                print(f"📊 Getting scanner data for channel {channel_id}...")
                # Get updated data from callback
                table_text = await self.update_callback()
                print(f"✅ Got scanner data ({len(table_text) if table_text else 0} chars)")

                if table_text and channel_id in self.channel_states:
                    print(f"📤 Updating message in channel {channel_id}")
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

                    # Generate table image
                    print(f"🎨 Generating table image for channel {channel_id}...")
                    table_image = generate_table_image(table_data, session_name, weight, last_updated)

                    # Create embed with image
                    embed = discord.Embed(
                        title="BYBIT FUTURES VWAP SCANNER",
                        description=f"Session: {session_name} | Weight: {weight} | Last Updated: {last_updated}",
                        color=discord.Color.blue()
                    )

                    # Create file attachment
                    filename = f"vwap_scanner_{datetime.utcnow().strftime('%H%M%S')}.png"
                    file = discord.File(table_image, filename=filename)

                    # Set image in embed
                    embed.set_image(url=f"attachment://{filename}")

                    # Calculate next update time
                    next_update = datetime.now() + timedelta(seconds=REFRESH_INTERVAL)
                    next_update_str = next_update.strftime('%H:%M:%S WIB')

                    # Add footer
                    embed.set_footer(text=f"Next update on {next_update_str}")

                    message = self.channel_states[channel_id]['message']
                    await message.edit(embed=embed, attachments=[file])
                    print(f"✅ Table image updated in channel {channel_id}")
                elif channel_id in self.channel_states:
                    print(f"⚠️ No data to update in channel {channel_id}")

            except discord.NotFound:
                print(f"❌ Message not found in channel {channel_id}, stopping updates")
                if channel_id in self.channel_states:
                    self.channel_states[channel_id]['running'] = False
                    del self.channel_states[channel_id]
                break
            except Exception as e:
                print(f"❌ Error updating message in channel {channel_id}: {e}")
                import traceback
                traceback.print_exc()
                if channel_id in self.channel_states:
                    self.channel_states[channel_id]['running'] = False
                    del self.channel_states[channel_id]
                break

            # Wait before next update
            print(f"⏰ Waiting {REFRESH_INTERVAL} seconds before next update...")
            await asyncio.sleep(REFRESH_INTERVAL)

    def set_update_callback(self, callback):
        """Set the callback function to get updated data"""
        self.update_callback = callback

    async def close(self):
        """Cleanup when bot is shutting down"""
        # Cancel all running update tasks
        for channel_id, state in self.channel_states.items():
            if state['task'] and not state['task'].done():
                state['task'].cancel()
                print(f"🛑 Cancelled update task for channel {channel_id}")

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

    # Check if already running in this channel
    if channel_id in bot.channel_states and bot.channel_states[channel_id]['running']:
        print(f"⚠️ Scanner already running in channel {channel_id}")
        await ctx.send("🔄 VWAP scanner is already running in this channel!")
        return

    try:
        print("📤 Sending initial message...")
        # Send initial message
        embed = discord.Embed(
            title="VWAP Scanner",
            description="Starting VWAP scanner...\nLoading data...",
            color=discord.Color.blue()
        )

        # Send the initial message and get the message object
        message = await ctx.send(embed=embed)
        print(f"✅ Initial message sent, message ID: {message.id}")

        # Initialize channel state
        bot.channel_states[channel_id] = {
            'message': message,
            'running': True,
            'task': None
        }

        # Save state to database
        server_name = ctx.guild.name if ctx.guild else "DM"
        guild_id = ctx.guild.id if ctx.guild else None
        save_channel_state(channel_id, message.id, True, server_name, ctx.channel.name, guild_id)

        # Start the update loop for this channel
        print(f"🔄 Starting update loop for channel {channel_id}")
        task = asyncio.create_task(bot.update_loop_for_channel(channel_id))
        bot.channel_states[channel_id]['task'] = task

        print(f"✅ VWAP scanner started in channel: {ctx.channel.name} (ID: {channel_id})")

    except Exception as e:
        print(f"❌ Error in start_command: {e}")
        import traceback
        traceback.print_exc()
        try:
            await ctx.send(f"❌ Error starting scanner: {str(e)[:100]}")
        except Exception as followup_error:
            print(f"❌ Failed to send error message: {followup_error}")

@bot.command(name="stop")
async def stop_command(ctx):
    """Stop VWAP scanner - Usage: !stop"""
    print(f"📥 !stop command received from {ctx.author}")
    channel_id = ctx.channel.id

    if channel_id not in bot.channel_states or not bot.channel_states[channel_id]['running']:
        print(f"⚠️ No scanner running in channel {channel_id}")
        await ctx.send("❌ VWAP scanner is not running in this channel!")
        return

    try:
        print(f"🛑 Stopping scanner in channel {channel_id}")
        # Stop the scanner for this channel
        bot.channel_states[channel_id]['running'] = False

        # Cancel the update task
        if bot.channel_states[channel_id]['task']:
            bot.channel_states[channel_id]['task'].cancel()
            print("✅ Update task cancelled")

        embed = discord.Embed(
            title="VWAP Scanner",
            description="VWAP scanner stopped",
            color=discord.Color.red()
        )

        message = bot.channel_states[channel_id]['message']
        await message.edit(embed=embed)
        print("✅ Stop message sent")

        # Clean up channel state
        del bot.channel_states[channel_id]

        # Remove from database
        remove_channel_state(channel_id)

        await ctx.send("✅ VWAP scanner stopped!")

        print(f"⏹️ VWAP scanner stopped in channel: {ctx.channel.name} (ID: {channel_id})")

    except Exception as e:
        print(f"❌ Error in stop_command: {e}")
        import traceback
        traceback.print_exc()
        try:
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