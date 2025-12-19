# notifier/discord_bot.py

import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime
from config import DISCORD_BOT_TOKEN, REFRESH_INTERVAL
from typing import Optional

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

    async def update_loop_for_channel(self, channel_id):
        """Update loop for a specific channel"""
        print(f"🔄 Update loop started for channel {channel_id}")
        while channel_id in self.channel_states and self.channel_states[channel_id]['running']:
            try:
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
                        last_updated = datetime.utcnow().strftime('%H:%M:%S UTC')
                    
                    embed = discord.Embed(
                        title="📊 VWAP Scanner",
                        description=f"```\n{table_data}\n```",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text=f"Last updated: {last_updated} • Updates every {REFRESH_INTERVAL}s • Use !stop to end")

                    message = self.channel_states[channel_id]['message']
                    await message.edit(embed=embed)
                    print(f"✅ Message updated in channel {channel_id}")
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

# Traditional commands (more reliable than slash commands)
@bot.command(name="start")
async def start_command(ctx):
    """Start VWAP scanner - Usage: !start"""
    print(f"🚀 VWAP BOT v2.0 - !start command received from {ctx.author}")

    channel_id = ctx.channel.id

    # Check if already running in this channel
    if channel_id in bot.channel_states and bot.channel_states[channel_id]['running']:
        print(f"⚠️ Scanner already running in channel {channel_id}")
        await ctx.send("🔄 VWAP scanner is already running in this channel!")
        return

    try:
        print("📤 Sending initial message...")
        # Send initial message
        embed = discord.Embed(
            title="📊 VWAP Scanner",
            description="🔄 Starting VWAP scanner...\n⏰ Loading data...",
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
            title="📊 VWAP Scanner",
            description="⏹️ VWAP scanner stopped",
            color=discord.Color.red()
        )

        message = bot.channel_states[channel_id]['message']
        await message.edit(embed=embed)
        print("✅ Stop message sent")

        # Clean up channel state
        del bot.channel_states[channel_id]

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