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

def generate_bot_invite_link(client_id: str) -> str:
    """Generate the bot invite link with necessary permissions."""
    permissions = discord.Permissions(
        send_messages=True,
        read_messages=True,
        read_message_history=True,
        add_reactions=True,
        attach_files=True,
        embed_links=True,
        use_external_emojis=True,
        use_external_stickers=True,
        view_channel=True,
        send_messages_in_threads=True,
        create_public_threads=True,
        mention_everyone=True
    )
    return discord.utils.oauth_url(
        client_id,
        permissions=permissions,
        scopes=["bot", "applications.commands"]
    )
class OctantDiscordBot(commands.Bot):
    def __init__(self):
        logger.info("Setting up bot with privileged intents...")
        try:
            # Set up all required intents
            intents = discord.Intents.all()
            
            application_id = os.getenv('DISCORD_APPLICATION_ID')
            logger.info(f"Initializing bot with application ID: {application_id}")
            
            super().__init__(
                command_prefix='/',
                intents=intents,
                description="Octant Information Bot with trivia games and ecosystem knowledge",
                application_id=application_id,
                activity=discord.Activity(
                    type=discord.ActivityType.listening,
                    name="/help | /trivia"
                )
            )
            
            self.chat_handler = ChatHandler()
            self.trivia = DiscordTrivia()
            self.synced = False  # Track if commands have been synced
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}")
            raise

    async def setup_hook(self):
        """Set up the bot's application commands."""
        logger.info("Bot is setting up...")
        try:
            # Log the invite link with all necessary scopes
            app_id = os.getenv('DISCORD_APPLICATION_ID')
            if app_id:
                invite_link = generate_bot_invite_link(app_id)
                logger.info(f"Bot invite link: {invite_link}")
            else:
                logger.warning("No application ID found, cannot generate invite link")

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
            logger.info("Attempting to sync application commands globally...")
            try:
                await self.tree.sync()
                self.synced = True
                logger.info("Successfully synced all commands globally")
            except Exception as e:
                logger.error(f"Failed to sync commands: {str(e)}")
                raise

        except Exception as e:
            logger.error(f"Error in setup_hook: {str(e)}", exc_info=True)
            raise

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'Logged in as {self.user.name} (ID: {self.user.id})')
        
        # Set bot's presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/help | /trivia"
            ),
            status=discord.Status.online
        )
        
        # Sync commands globally if not already synced
        if not self.synced:
            logger.info("Attempting to sync application commands globally...")
            try:
                synced = await self.tree.sync()
                self.synced = True
                logger.info(f"Successfully synced {len(synced)} commands globally")
            except Exception as e:
                logger.error(f"Failed to sync commands: {str(e)}")
        
        logger.info('Bot is fully ready!')
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
