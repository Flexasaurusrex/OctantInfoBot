import os
import discord
from discord.ext import commands
from chat_handler import ChatHandler
from discord_trivia import DiscordTrivia
import logging
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OctantDiscordBot(commands.Bot):
    def __init__(self):
        logger.info("Setting up bot with privileged intents...")
        try:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            intents.presences = True
            
            super().__init__(
                command_prefix='/',
                intents=intents,
                description="Octant Information Bot with trivia games and ecosystem knowledge",
                application_id=os.getenv('DISCORD_APPLICATION_ID')
            )
            
            self.chat_handler = ChatHandler()
            self.trivia = DiscordTrivia()
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}")
            raise

    async def setup_hook(self):
        """Set up the bot's application commands."""
        logger.info("Bot is setting up...")
        try:
            # Remove any existing commands first
            await self.tree.sync()
            commands = await self.tree.fetch_commands()
            for command in commands:
                await self.tree.remove_command(command.name)
            
            # Register the trivia command
            @self.tree.command(
                name="trivia",
                description="Start a fun trivia game about Octant ecosystem"
            )
            async def trivia(interaction: discord.Interaction):
                await interaction.response.defer()
                await self.trivia.start_game(await self.get_context(interaction))

            # Register the help command
            @self.tree.command(
                name="help",
                description="Show help information about available commands"
            )
            async def help_cmd(interaction: discord.Interaction):
                help_text = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Available Commands
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎮 Game Commands:
• /trivia - Start a trivia game about Octant

📋 Information Commands:
• /help - Show this help message

Type any command to get started!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
                await interaction.response.send_message(help_text)

            # Sync commands globally
            logger.info("Syncing application commands...")
            await self.tree.sync()
            logger.info("Application commands synced successfully")

        except Exception as e:
            logger.error(f"Error in setup_hook: {str(e)}", exc_info=True)
            raise

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info('------')

    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions."""
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("trivia_"):
                answer = custom_id.split("_")[1]
                await self.trivia.handle_answer(interaction, answer)

async def main():
    # Get required environment variables
    discord_token = os.environ.get('DISCORD_BOT_TOKEN')
    if not discord_token:
        logger.error("DISCORD_BOT_TOKEN not found in environment variables")
        raise ValueError("DISCORD_BOT_TOKEN environment variable is required")

    # Create and run bot
    try:
        bot = OctantDiscordBot()
        await bot.start(discord_token)
    except discord.LoginFailure:
        logger.error("Failed to login to Discord. Please check your token.")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
