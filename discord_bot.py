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
        self.tree.on_error = self.on_app_command_error

    async def setup_hook(self):
        """Initial setup after bot is ready with enhanced error handling and verification"""
        try:
            logger.info("\n━━━━━━ Initializing Bot Setup ━━━━━━")
            self.startup_time = datetime.now()
            
            logger.info("Phase 1: Registering commands...")
            
            # Help command
            @self.tree.command(
                name="help",
                description="Shows the list of available commands"
            )
            async def help_cmd(interaction: discord.Interaction):
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
                    
                    # Add bot information
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
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            f"❌ {error_msg}",
                            ephemeral=True
                        )

            # Ping command
            @self.tree.command(
                name="ping",
                description="Check if the bot is responsive"
            )
            async def ping_cmd(interaction: discord.Interaction):
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
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            f"❌ {error_msg}",
                            ephemeral=True
                        )

            # Phase 2: Sync commands
            logger.info("Phase 2: Syncing commands...")
            try:
                await self.tree.sync()
                commands = await self.tree.fetch_commands()
                logger.info(f"Successfully synced {len(commands)} commands")
                for cmd in commands:
                    logger.info(f"• /{cmd.name} - {cmd.description}")
            except Exception as e:
                logger.error(f"Failed to sync commands: {str(e)}\n{traceback.format_exc()}")
                raise
            
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

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle command errors"""
        try:
            logger.error(f"Command error: {str(error)}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ An error occurred: {str(error)}",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error handling command error: {str(e)}\n{traceback.format_exc()}")

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
        
        # Initialize bot with error handling
        try:
            bot = OctantBot()
            logger.info("Bot instance created successfully")
            
            logger.info("Attempting to connect to Discord...")
            await bot.start(token)
            
        except discord.LoginFailure as e:
            logger.error(f"Failed to login: {str(e)}")
            raise
        except discord.HTTPException as e:
            logger.error(f"HTTP error connecting to Discord: {str(e)}")
            raise
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

if __name__ == "__main__":
    asyncio.run(main())