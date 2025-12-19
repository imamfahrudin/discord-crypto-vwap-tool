# notifier/discord_bot.py

import discord
from discord import app_commands
from discord.ext import tasks
import asyncio
from config import DISCORD_BOT_TOKEN, REFRESH_INTERVAL
from typing import Optional

class VWAPBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        # Track per-channel state
        self.channel_states = {}  # channel_id -> {'message': Message, 'running': bool, 'task': Task}
        self.update_callback = None

    async def setup_hook(self):
        """Setup slash commands"""
        self.tree.add_command(self.start_command)
        self.tree.add_command(self.stop_command)
        await self.tree.sync()

    @app_commands.command(name="start", description="Start VWAP scanner and send updates to this channel")
    async def start_command(self, interaction: discord.Interaction):
        channel_id = interaction.channel.id

        # Check if already running in this channel
        if channel_id in self.channel_states and self.channel_states[channel_id]['running']:
            await interaction.response.send_message("🔄 VWAP scanner is already running in this channel!", ephemeral=True)
            return

        # Defer the interaction to give us more time
        await interaction.response.defer()

        try:
            # Send initial message
            embed = discord.Embed(
                title="📊 VWAP Scanner",
                description="🔄 Starting VWAP scanner...",
                color=discord.Color.blue()
            )

            # Send the initial message and get the message object
            message = await interaction.followup.send(embed=embed, wait=True)

            # Initialize channel state
            self.channel_states[channel_id] = {
                'message': message,
                'running': True,
                'task': None
            }

            # Start the update loop for this channel
            task = asyncio.create_task(self.update_loop_for_channel(channel_id))
            self.channel_states[channel_id]['task'] = task

            print(f"✅ VWAP scanner started in channel: {interaction.channel.name} (ID: {channel_id})")

        except Exception as e:
            print(f"❌ Error in start_command: {e}")
            try:
                await interaction.followup.send(f"❌ Error starting scanner: {str(e)[:100]}", ephemeral=True)
            except Exception as followup_error:
                print(f"❌ Failed to send error message: {followup_error}")

    @app_commands.command(name="stop", description="Stop VWAP scanner")
    async def stop_command(self, interaction: discord.Interaction):
        channel_id = interaction.channel.id

        if channel_id not in self.channel_states or not self.channel_states[channel_id]['running']:
            await interaction.response.send_message("❌ VWAP scanner is not running in this channel!", ephemeral=True)
            return

        # Defer the interaction
        await interaction.response.defer()

        try:
            # Stop the scanner for this channel
            self.channel_states[channel_id]['running'] = False

            # Cancel the update task
            if self.channel_states[channel_id]['task']:
                self.channel_states[channel_id]['task'].cancel()

            embed = discord.Embed(
                title="📊 VWAP Scanner",
                description="⏹️ VWAP scanner stopped",
                color=discord.Color.red()
            )

            message = self.channel_states[channel_id]['message']
            try:
                await message.edit(embed=embed)
            except discord.NotFound:
                await interaction.followup.send(embed=embed)

            # Clean up channel state
            del self.channel_states[channel_id]

            await interaction.followup.send("✅ VWAP scanner stopped!", ephemeral=True)
            print(f"⏹️ VWAP scanner stopped in channel: {interaction.channel.name} (ID: {channel_id})")

        except Exception as e:
            print(f"❌ Error in stop_command: {e}")
            try:
                await interaction.followup.send(f"❌ Error stopping scanner: {str(e)[:100]}", ephemeral=True)
            except Exception as followup_error:
                print(f"❌ Failed to send error message: {followup_error}")

    async def update_loop_for_channel(self, channel_id):
        """Update loop for a specific channel"""
        while channel_id in self.channel_states and self.channel_states[channel_id]['running']:
            try:
                # Get updated data from callback
                table_text = await self.update_callback()

                if table_text and channel_id in self.channel_states:
                    embed = discord.Embed(
                        title="📊 VWAP Scanner",
                        description=f"```\n{table_text}\n```",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text=f"Updates every {REFRESH_INTERVAL} seconds • Use /stop to end")

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
                if channel_id in self.channel_states:
                    self.channel_states[channel_id]['running'] = False
                    del self.channel_states[channel_id]
                break

            # Wait before next update
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