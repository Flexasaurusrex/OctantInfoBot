import os
import logging
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import time
from datetime import datetime

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
            
            # Clear existing commands first
            self.tree.clear_commands(guild=None)
            logger.info("Cleared existing commands")
            
            # Add the commands
            @self.tree.command(name="help", description="Shows the list of available commands")
            async def help_command(interaction: discord.Interaction):
                """Handler for the help command"""
                try:
                    embed = discord.Embed(
                        title="📚 Available Commands",
                        description="Here are all the commands you can use:",
                        color=discord.Color.blue()
                    )
                    
                    # Add command descriptions
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
                    embed.add_field(
                        name="/trivia",
                        value="Start a trivia game",
                        inline=False
                    )
                    
                    # Add bot information
                    uptime = datetime.now() - self.startup_time if self.startup_time else None
                    uptime_str = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m" if uptime else "Unknown"
                    
                    embed.add_field(
                        name="Bot Information",
                        value=f"• Uptime: {uptime_str}\n• Connected Servers: {len(self.guilds)}",
                        inline=False
                    )
                    
                    await interaction.response.send_message(embed=embed)
                    logger.info(f"Help command executed by {interaction.user}")
                    
                except Exception as e:
                    logger.error(f"Error in help command: {str(e)}")
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "❌ Error displaying help message",
                            ephemeral=True
                        )

            @self.tree.command(name="ping", description="Check if the bot is responsive")
            async def ping_command(interaction: discord.Interaction):
                """Handler for the ping command"""
                try:
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
                    logger.info(f"Ping command executed - Latency: {latency}ms, Response time: {duration}ms")
                    
                except Exception as e:
                    logger.error(f"Error in ping command: {str(e)}")
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "❌ Error processing ping command",
                            ephemeral=True
                        )
            
            # Force sync commands with Discord
            logger.info("Syncing commands globally...")
            await self.tree.sync()
            self.initial_sync_done = True
            logger.info("Global command sync completed!")
            
        except Exception as e:
            logger.error(f"Critical error in setup_hook: {str(e)}", exc_info=True)
            await self.close()

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
            logger.error(f"Error in on_ready: {str(e)}", exc_info=True)

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
