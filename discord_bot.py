import os
import discord
from discord import app_commands
from discord.ext import commands
import logging
import traceback
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BasicDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True  # Enable guilds intent for slash commands
        intents.guild_messages = True  # Enable guild messages
        super().__init__(
            command_prefix='/',
            intents=intents,
            help_command=None,
            application_id=1316950341954306159  # Add your bot's application ID
        )

    async def setup_hook(self):
        """Set up the bot's commands and cogs."""
        logger.info("=== Bot Setup Process ===")
        try:
            # Wait a moment to ensure connection is stable
            await self.wait_until_ready()
            logger.info(f"Bot connected as {self.user.name} (ID: {self.user.id})")
            
            logger.info("1. Initializing Basic Commands Cog")
            basic_cog = BasicCommands(self)
            await self.add_cog(basic_cog)
            logger.info("✓ Basic commands cog added successfully")
            
            logger.info("2. Preparing Command Sync")
            all_commands = [cmd.name for cmd in self.tree.get_commands()]
            logger.info(f"Commands to sync: {all_commands}")
            
            logger.info("3. Starting Global Command Sync")
            try:
                # Force sync all commands globally
                commands = await self.tree.sync(guild=None)
                logger.info(f"✓ Successfully synced {len(commands)} commands globally")
                logger.info(f"Synced commands: {[cmd.name for cmd in commands]}")
                
                # Verify commands were actually registered
                if not commands:
                    logger.warning("⚠ No commands were synced! This might indicate a registration issue.")
                    logger.warning("Available commands before sync: " + str([cmd.name for cmd in self.tree.get_commands()]))
                
            except discord.errors.Forbidden as e:
                logger.error(f"❌ Failed to sync commands - Missing Permissions: {e}")
                logger.error("Please ensure the bot has the 'applications.commands' scope enabled")
                raise
            except discord.errors.HTTPException as e:
                logger.error(f"❌ Failed to sync commands - HTTP Error: {e}")
                logger.error(f"Response: {e.response}")
                raise
            except Exception as e:
                logger.error(f"❌ Failed to sync commands - Unexpected Error: {e}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Error details: {str(e)}")
                raise
            
            logger.info("=== Setup Complete ===")
            
        except discord.errors.HTTPException as he:
            logger.error(f"HTTP error in setup_hook: {str(he)}\n{traceback.format_exc()}")
            logger.error(f"Status: {he.status}")
            logger.error(f"Code: {he.code}")
            logger.error(f"Response: {he.response}")
            await self.close()
            raise
        except Exception as e:
            logger.error(f"Critical error in setup_hook: {str(e)}\n{traceback.format_exc()}")
            logger.error("Full error context:")
            logger.error(f"Bot state: {self.status}")
            logger.error(f"Available commands: {[cmd.name for cmd in self.tree.get_commands()]}")
            await self.close()
            raise

    async def on_ready(self):
        """Called when the bot is ready and connected."""
        logger.info("=" * 50)
        logger.info(f"Bot Ready: {self.user.name} (ID: {self.user.id})")
        logger.info(f"Discord API Version: {discord.__version__}")
        logger.info(f"Connected to {len(self.guilds)} servers")
        logger.info(f"Registered Commands: {[cmd.name for cmd in self.tree.get_commands()]}")
        logger.info("=" * 50)

class BasicCommands(commands.Cog):
    """Basic commands cog for essential bot functionality."""
    
    def __init__(self, bot):
        self.bot = bot
        logger.info("Basic commands cog initialized")

    @app_commands.command(
        name="help",
        description="Shows the list of available commands"
    )
    async def help_command(self, interaction: discord.Interaction):
        """Displays help information about available commands."""
        try:
            logger.info("=== Help Command Execution ===")
            logger.info(f"Command invoked by: {interaction.user} (ID: {interaction.user.id})")
            
            # Create embed with bot information
            help_embed = discord.Embed(
                title="🤖 Octant Bot Commands",
                description="Here are the available commands:",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # Add command information
            help_embed.add_field(
                name="/help",
                value="Show this help message",
                inline=False
            )
            
            # Add bot status
            help_embed.add_field(
                name="Bot Status",
                value=f"✅ Online | Connected to {len(self.bot.guilds)} servers",
                inline=False
            )
            
            help_embed.set_footer(text=f"Requested by {interaction.user.name}")
            
            logger.info("Sending help message...")
            await interaction.response.send_message(embed=help_embed, ephemeral=True)
            logger.info("Help message sent successfully")
            
        except discord.errors.InteractionResponded:
            logger.warning("Interaction already responded to, sending followup")
            await interaction.followup.send(embed=help_embed)
            
        except Exception as e:
            error_msg = f"Error processing help command: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while showing help. Please try again.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "❌ An error occurred while showing help. Please try again.",
                        ephemeral=True
                    )
            except Exception as e2:
                logger.error(f"Failed to send error message: {str(e2)}\n{traceback.format_exc()}")

async def main():
    try:
        # Verify Discord token
        discord_token = os.environ.get('DISCORD_BOT_TOKEN')
        if not discord_token:
            logger.error("DISCORD_BOT_TOKEN environment variable is missing")
            await ask_secrets(['DISCORD_BOT_TOKEN'], "Please provide your Discord bot token to enable the bot to connect to Discord's servers.")
            discord_token = os.environ.get('DISCORD_BOT_TOKEN')
        
        # Initialize and start bot with detailed logging
        logger.info("Initializing Discord bot...")
        async with BasicDiscordBot() as bot:
            try:
                logger.info("Starting Discord bot...")
                await bot.start(discord_token)
            except discord.LoginFailure:
                logger.error("Failed to login: Invalid Discord token")
                await ask_secrets(['DISCORD_BOT_TOKEN'], "The provided Discord token is invalid. Please provide a valid token.")
                raise SystemExit(1)
            except discord.PrivilegedIntentsRequired:
                logger.error("Bot requires privileged intents to be enabled in Discord Developer Portal")
                raise SystemExit(1)
            except Exception as e:
                logger.error(f"Failed to start bot: {str(e)}\n{traceback.format_exc()}")
                raise
            
    except Exception as e:
        logger.error(f"Critical error: {str(e)}\n{traceback.format_exc()}")
        raise SystemExit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())