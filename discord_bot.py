import os
import sys
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
        self.startup_time = None
        
        # Register commands
        self.setup_commands()

    def setup_commands(self):
        """Register all commands"""
        try:
            # Help command
            @self.tree.command(name="help", description="Shows the list of available commands")
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
                    uptime_str = str(uptime).split('.')[0]
                    
                    embed.add_field(
                        name="Bot Information",
                        value=f"• Uptime: {uptime_str}\n• Connected Servers: {len(self.guilds)}",
                        inline=False
                    )
                    
                    await interaction.response.send_message(embed=embed)
                    logger.info("Help command completed successfully")
                except Exception as e:
                    error_msg = f"Error in help command: {str(e)}"
                    logger.error(f"{error_msg}\n{traceback.format_exc()}")
                    try:
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                f"❌ {error_msg}",
                                ephemeral=True
                            )
                    except Exception as e2:
                        logger.error(f"Failed to send error message: {str(e2)}")

            # Ping command
            @self.tree.command(name="ping", description="Check if the bot is responsive")
            async def ping_command(interaction: discord.Interaction):
                try:
                    logger.info(f"Ping command executed by {interaction.user}")
                    start_time = time.perf_counter()
                    
                    await interaction.response.send_message("🏓 Pinging...")
                    
                    end_time = time.perf_counter()
                    duration = round((end_time - start_time) * 1000)
                    latency = round(self.latency * 1000)
                    
                    response = "**🏓 Pong!**\n"
                    response += f"• Response time: `{duration}ms`\n"
                    response += f"• Websocket latency: `{latency}ms`\n"
                    response += f"• Connection status: `Connected`"
                    
                    await interaction.edit_original_response(content=response)
                    logger.info(f"Ping response sent - Latency: {latency}ms, Response time: {duration}ms")
                except Exception as e:
                    error_msg = f"Error in ping command: {str(e)}"
                    logger.error(f"{error_msg}\n{traceback.format_exc()}")
                    try:
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                f"❌ {error_msg}",
                                ephemeral=True
                            )
                    except Exception as e2:
                        logger.error(f"Failed to send error message: {str(e2)}")

            logger.info("Commands registered successfully")
        except Exception as e:
            logger.error(f"Error registering commands: {str(e)}\n{traceback.format_exc()}")
            raise

    async def setup_hook(self):
        """Initial setup after bot is ready"""
        try:
            logger.info("\n━━━━━━ Initializing Bot Setup ━━━━━━")
            self.startup_time = datetime.now()
            
            # Sync commands with retries
            logger.info("Syncing commands...")
            max_retries = 3
            retry_count = 0
            last_error = None

            while retry_count < max_retries:
                try:
                    logger.info(f"Attempting to sync commands (attempt {retry_count + 1}/{max_retries})")
                    await self.tree.sync()
                    commands = await self.tree.fetch_commands()
                    logger.info(f"Successfully synced {len(commands)} commands:")
                    for cmd in commands:
                        logger.info(f"• /{cmd.name} - {cmd.description}")
                    break
                except Exception as e:
                    last_error = e
                    retry_count += 1
                    logger.warning(f"Sync attempt {retry_count} failed: {str(e)}")
                    if retry_count < max_retries:
                        wait_time = 2 ** retry_count
                        logger.info(f"Waiting {wait_time} seconds before retry...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Failed to sync commands after {max_retries} attempts")
                        raise last_error
                        
        except Exception as e:
            logger.error(f"Critical error in setup_hook: {str(e)}\n{traceback.format_exc()}")
            raise

    async def on_ready(self):
        """Called when the bot is ready and connected"""
        try:
            logger.info(f"━━━━━━ Bot Connected ━━━━━━")
            logger.info(f"Bot: {self.user} (ID: {self.user.id})")
            logger.info(f"Discord.py Version: {discord.__version__}")
            logger.info(f"Python Version: {sys.version}")
            
            # Set bot status
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name="/help for commands"
            )
            await self.change_presence(activity=activity, status=discord.Status.online)
            logger.info("Status set successfully")
            
            # Verify commands
            commands = await self.tree.fetch_commands()
            logger.info(f"Available Commands ({len(commands)}):")
            for cmd in commands:
                logger.info(f"• /{cmd.name} - {cmd.description}")
            
            logger.info("━━━━━━ Bot Ready ━━━━━━")
            
        except Exception as e:
            logger.error(f"Error in on_ready: {str(e)}\n{traceback.format_exc()}")

async def main():
    """Main entry point for the bot"""
    try:
        logger.info("\n━━━━━━ Starting Discord Bot ━━━━━━")
        
        # Verify token first
        token = os.environ.get('DISCORD_BOT_TOKEN')
        if not token or not token.strip():
            raise ValueError("DISCORD_BOT_TOKEN not found or empty")
        token = token.strip()
        
        logger.info("Token verified successfully")
        
        # Initialize bot with retries
        max_retries = 3
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                logger.info(f"Attempting to start bot (attempt {retry_count + 1}/{max_retries})")
                
                bot = OctantBot()
                logger.info("Bot instance created successfully")
                
                logger.info("Attempting to connect to Discord...")
                async with bot:
                    await bot.start(token)
                return  # Success, exit the retry loop
                
            except discord.LoginFailure as e:
                logger.error(f"Failed to login: {str(e)}")
                raise  # Don't retry on authentication failures
                
            except discord.HTTPException as e:
                last_error = e
                retry_count += 1
                logger.warning(f"HTTP error on attempt {retry_count}: {str(e)}")
                
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to start bot after {max_retries} attempts: {str(last_error)}")
                    raise last_error
                
            except Exception as e:
                logger.error(f"Unexpected error starting bot: {str(e)}\n{traceback.format_exc()}")
                raise
                
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown initiated by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}\n{traceback.format_exc()}")
        sys.exit(1)
