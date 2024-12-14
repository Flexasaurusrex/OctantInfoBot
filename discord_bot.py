import os
import logging
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import time
from datetime import datetime
import traceback

# Configure logging with both file and console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('discord_bot.log')
    ]
)
logger = logging.getLogger(__name__)

class OctantBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        
        super().__init__(
            command_prefix="/",
            intents=intents,
            heartbeat_timeout=60,
            guild_ready_timeout=5
        )
        self.initial_sync_done = False
        self.startup_time = None

    async def setup_hook(self):
        """Initial setup after bot is ready"""
        try:
            logger.info("━━━━━━ Initializing Bot Setup ━━━━━━")
            self.startup_time = datetime.now()
            
            # Register commands
            await self.register_commands()
            
            # Force sync commands
            logger.info("Syncing commands globally...")
            await self.tree.sync()
            logger.info("Commands synced successfully")

        except Exception as e:
            logger.error(f"Critical error in setup_hook: {str(e)}\n{traceback.format_exc()}")
            raise

    async def register_commands(self):
        """Register all slash commands"""
        try:
            logger.info("Registering commands...")
            
            # Clear existing commands first
            self.tree.clear_commands(guild=None)
            
            # Register help command
            @self.tree.command(name="help", description="Shows the list of available commands", guild=None)
            async def help_command(interaction: discord.Interaction):
                try:
                    logger.info(f"Help command executed by {interaction.user}")
                    embed = discord.Embed(
                        title="📚 Available Commands",
                        description="Here are all the commands you can use:",
                        color=discord.Color.blue()
                    )
                    
                    embed.add_field(
                        name="/help",
                        value="Shows this help message",
                        inline=False
                    )
                    embed.add_field(
                        name="/ping",
                        value="Check if the bot is responsive",
                        inline=False
                    )
                    
                    uptime = datetime.now() - self.startup_time if self.startup_time else datetime.now()
                    uptime_str = str(uptime).split('.')[0]  # Format as HH:MM:SS
                    
                    embed.add_field(
                        name="Bot Information",
                        value=f"• Uptime: {uptime_str}\n• Connected Servers: {len(self.guilds)}",
                        inline=False
                    )
                    
                    await interaction.response.send_message(embed=embed)
                    logger.info("Help command completed successfully")
                    
                except Exception as e:
                    logger.error(f"Error in help command: {str(e)}\n{traceback.format_exc()}")
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "❌ Error displaying help message",
                            ephemeral=True
                        )

            # Register ping command
            @self.tree.command(name="ping", description="Check if the bot is responsive", guild=None)
            async def ping_command(interaction: discord.Interaction):
                try:
                    logger.info(f"Ping command executed by {interaction.user}")
                    start_time = time.perf_counter()
                    
                    await interaction.response.send_message("Pinging...")
                    
                    end_time = time.perf_counter()
                    duration = round((end_time - start_time) * 1000)
                    latency = round(self.latency * 1000)
                    
                    response = f"🏓 Pong!\n"
                    response += f"• Response time: {duration}ms\n"
                    response += f"• Websocket latency: {latency}ms\n"
                    response += f"• Connection status: Connected"
                    
                    await interaction.edit_original_response(content=response)
                    logger.info(f"Ping response sent - Latency: {latency}ms, Response time: {duration}ms")
                    
                except Exception as e:
                    logger.error(f"Error in ping command: {str(e)}\n{traceback.format_exc()}")
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "❌ Error processing ping command",
                            ephemeral=True
                        )
            
            logger.info("Commands registered successfully")
            
        except Exception as e:
            logger.error(f"Error registering commands: {str(e)}\n{traceback.format_exc()}")
            raise

            # Force sync commands with Discord with retries
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    logger.info(f"Attempting to sync commands globally (attempt {retry_count + 1}/{max_retries})...")
                    await self.tree.sync()
                    logger.info("Successfully synced commands globally")
                    break
                except Exception as e:
                    retry_count += 1
                    logger.error(f"Failed to sync commands (attempt {retry_count}/{max_retries}): {str(e)}")
                    if retry_count >= max_retries:
                        raise Exception(f"Failed to sync commands after {max_retries} attempts")
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"Error registering commands: {str(e)}\n{traceback.format_exc()}")
            raise

    async def on_ready(self):
        """Called when the bot is ready and connected"""
        try:
            logger.info(f"━━━━━━ Bot Connected ━━━━━━")
            logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
            
            # Log connected guilds
            guilds = [guild.name for guild in self.guilds]
            logger.info(f"Connected to {len(guilds)} guilds: {', '.join(guilds)}")
            
            # Set bot status
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name="/help for commands"
            )
            await self.change_presence(activity=activity)
            logger.info("Bot presence updated successfully")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
        except Exception as e:
            logger.error(f"Error in on_ready: {str(e)}\n{traceback.format_exc()}")

async def main():
    """Main entry point for the bot"""
    try:
        # Initialize bot
        bot = OctantBot()
        
        # Get Discord token from environment
        token = os.environ.get('DISCORD_BOT_TOKEN')
        if not token:
            logger.error("Discord bot token not found in environment variables!")
            raise ValueError("No Discord bot token provided")
        
        # Start the bot with enhanced error handling
        try:
            logger.info("Starting bot with enhanced error handling...")
            async with bot:
                await bot.start(token)
        except discord.LoginFailure as e:
            logger.error(f"Failed to log in: Invalid token or connection issues: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Fatal error starting bot: {str(e)}", exc_info=True)
            raise
            
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
