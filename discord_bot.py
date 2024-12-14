import os
import logging
import discord
from discord import app_commands
from chat_handler import ChatHandler
from discord_trivia import DiscordTrivia

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

class OctantBot(discord.Client):
    def __init__(self):
        try:
            # Set up intents
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            
            # Initialize the client
            super().__init__(intents=intents)
            
            # Create command tree
            self.tree = app_commands.CommandTree(self)
            
            # Initialize handlers
            self.chat_handler = ChatHandler()
            self.trivia = DiscordTrivia()
            
            logger.info("Bot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}", exc_info=True)
            raise

    async def setup_hook(self):
        """Set up the bot's commands."""
        try:
            logger.info("Setting up commands...")
            
            # Register commands
            @self.tree.command(name="ping", description="Check if the bot is responsive")
            async def ping(interaction: discord.Interaction):
                try:
                    await interaction.response.send_message("Pong! 🏓")
                    logger.info(f"Ping command executed by {interaction.user}")
                except Exception as e:
                    logger.error(f"Error in ping command: {str(e)}", exc_info=True)
                    await interaction.response.send_message(
                        "Sorry, there was an error processing your command.",
                        ephemeral=True
                    )

            @self.tree.command(name="help", description="Show available commands")
            async def help_command(interaction: discord.Interaction):
                try:
                    help_embed = discord.Embed(
                        title="📚 Octant Bot Help",
                        description="Welcome to Octant Bot! Here are the available commands:",
                        color=discord.Color.blue()
                    )
                    
                    help_embed.add_field(
                        name="🎮 Game Commands",
                        value="• `/trivia` - Start a trivia game about Octant",
                        inline=False
                    )
                    
                    help_embed.add_field(
                        name="🤖 Utility Commands",
                        value="• `/ping` - Check if the bot is responsive\n• `/help` - Show this help message",
                        inline=False
                    )
                    
                    help_embed.add_field(
                        name="💬 Chat Features",
                        value="• Reply to any of my messages to chat\n• Ask questions about Octant\n• Get help with Octant features",
                        inline=False
                    )
                    
                    help_embed.set_footer(text="Type /trivia to start playing!")
                    
                    await interaction.response.send_message(embed=help_embed)
                    logger.info(f"Help command executed by {interaction.user}")
                except Exception as e:
                    logger.error(f"Error in help command: {str(e)}", exc_info=True)
                    await interaction.response.send_message(
                        "Sorry, there was an error displaying the help message. Please try again.",
                        ephemeral=True
                    )

            @self.tree.command(name="trivia", description="Start a trivia game")
            async def trivia_command(interaction: discord.Interaction):
                try:
                    logger.info(f"Trivia command received from {interaction.user}")
                    await interaction.response.defer()
                    await self.trivia.start_game(interaction)
                except Exception as e:
                    logger.error(f"Error in trivia command: {str(e)}", exc_info=True)
                    await interaction.followup.send(
                        "Sorry, there was an error starting the trivia game. Please try again.",
                        ephemeral=True
                    )

            # Sync commands
            logger.info("Syncing commands...")
            await self.tree.sync()
            logger.info("Commands synced successfully")
            
        except Exception as e:
            logger.error(f"Error in setup_hook: {str(e)}", exc_info=True)
            raise

    async def on_ready(self):
        """Called when the bot is ready."""
        try:
            logger.info(f"Bot is ready! Logged in as {self.user.name} (ID: {self.user.id})")
            logger.info(f"Connected to {len(self.guilds)} guilds")
            for guild in self.guilds:
                logger.info(f"- {guild.name} (ID: {guild.id})")
        except Exception as e:
            logger.error(f"Error in on_ready: {str(e)}", exc_info=True)

    async def on_message(self, message):
        """Handle incoming messages."""
        try:
            # Ignore messages from the bot itself
            if message.author == self.user:
                return

            # Handle message replies
            if message.reference and message.reference.resolved:
                referenced_msg = message.reference.resolved
                if referenced_msg.author == self.user:
                    response = self.chat_handler.get_response(message.content)
                    await message.reply(response, mention_author=True)
                    logger.info(f"Replied to message from {message.author}")

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            await message.channel.send(
                "I encountered an error processing your message. Please try again."
            )

async def main():
    """Main bot execution."""
    try:
        logger.info("Starting Discord bot...")
        bot = OctantBot()
        
        discord_token = os.environ.get('DISCORD_BOT_TOKEN')
        if not discord_token:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")

        logger.info("Connecting to Discord...")
        await bot.start(discord_token)
        
    except Exception as e:
        logger.error(f"Critical error in main: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
