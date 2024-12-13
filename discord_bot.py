import os
import discord
from discord import app_commands
import logging
import traceback
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class BasicBot(discord.Client):
    def __init__(self):
        try:
            logger.info("Initializing bot with intents...")
            intents = discord.Intents.default()
            intents.message_content = True
            super().__init__(intents=intents)
            self.tree = app_commands.CommandTree(self)
            logger.info("Bot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    async def setup_hook(self):
        try:
            logger.info("Setting up bot and syncing commands...")
            await self.tree.sync()
            logger.info("Commands synced successfully")
        except Exception as e:
            logger.error(f"Failed to sync commands: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    async def on_ready(self):
        try:
            logger.info(f"Bot connected as {self.user}")
            logger.info(f"Bot ID: {self.user.id}")
            await self.change_presence(activity=discord.Game(name="/ping"))
            logger.info("Bot is ready and listening for commands")
        except Exception as e:
            logger.error(f"Error in on_ready: {str(e)}")
            logger.error(traceback.format_exc())

client = BasicBot()

@client.tree.command(name="ping", description="Check if bot is responsive")
async def ping(interaction: discord.Interaction):
    try:
        logger.info(f"Ping command received from {interaction.user}")
        await interaction.response.send_message("Pong! 🏓")
        logger.info("Ping command processed successfully")
    except Exception as e:
        logger.error(f"Error processing ping command: {str(e)}")
        logger.error(traceback.format_exc())
        await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)

def main():
    try:
        token = os.environ.get('DISCORD_BOT_TOKEN')
        if not token:
            logger.error("No Discord token found!")
            return

        logger.info("Starting bot...")
        client.run(token, log_handler=None)
    except discord.LoginFailure as e:
        logger.error(f"Failed to login: Invalid token - {str(e)}")
        logger.error(traceback.format_exc())
    except discord.GatewayNotFound as e:
        logger.error(f"Gateway error: {str(e)}")
        logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
