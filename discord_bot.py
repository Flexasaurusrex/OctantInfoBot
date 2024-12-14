import os
import logging
import discord
from discord import app_commands
from discord.ext import commands

# Configure logging
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
        super().__init__(
            command_prefix="!",  # This is for backup text commands
            intents=discord.Intents.default(),
            application_id=1316950341954306159  # Your bot's application ID
        )
        self.initial_sync_done = False

    async def setup_hook(self):
        """This is called when the bot starts."""
        try:
            logger.info("Starting command sync...")
            if not self.initial_sync_done:
                # Sync commands globally
                await self.tree.sync()
                self.initial_sync_done = True
                logger.info("Global command sync completed!")
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}", exc_info=True)
            raise

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

async def main():
    """Main entry point for the bot."""
    try:
        # Initialize the bot
        bot = OctantBot()
        
        # Add the ping command
        @bot.tree.command(name="ping", description="Check if the bot is responsive")
        async def ping(interaction: discord.Interaction):
            try:
                await interaction.response.send_message("Pong! 🏓")
                logger.info(f"Ping command executed by {interaction.user}")
            except Exception as e:
                logger.error(f"Error in ping command: {e}")
                try:
                    await interaction.response.send_message("An error occurred", ephemeral=True)
                except:
                    pass

        # Add the help command
        @bot.tree.command(name="help", description="Shows the list of available commands")
        async def help(interaction: discord.Interaction):
            try:
                embed = discord.Embed(
                    title="📚 Bot Commands",
                    description="Here are the available commands:",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="/ping",
                    value="Check if the bot is responsive",
                    inline=False
                )
                embed.add_field(
                    name="/help",
                    value="Shows this help message",
                    inline=False
                )
                await interaction.response.send_message(embed=embed)
                logger.info(f"Help command executed by {interaction.user}")
            except Exception as e:
                logger.error(f"Error in help command: {e}")
                try:
                    await interaction.response.send_message("An error occurred", ephemeral=True)
                except:
                    pass

        # Start the bot
        token = os.environ.get('DISCORD_BOT_TOKEN')
        if not token:
            raise ValueError("No Discord bot token found!")
            
        logger.info("Starting bot...")
        await bot.start(token)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())