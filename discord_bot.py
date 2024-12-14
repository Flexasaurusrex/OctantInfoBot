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
            
            # Register commands immediately
            self.register_commands()
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}", exc_info=True)
            raise

    def register_commands(self):
        """Register all slash commands."""
        try:
            logger.info("Registering commands...")
            
            @self.tree.command(
                name="ping",
                description="Check if the bot is online and responsive"
            )
            async def ping(interaction: discord.Interaction):
                try:
                    logger.info(f"Ping command received from {interaction.user}")
                    await interaction.response.send_message("Pong! 🏓 Bot is online and responsive!")
                except Exception as e:
                    logger.error(f"Error in ping command: {str(e)}", exc_info=True)
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "Sorry, there was an error processing your command.",
                            ephemeral=True
                        )

            @self.tree.command(
                name="help",
                description="Display information about available commands"
            )
            async def help_command(interaction: discord.Interaction):
                try:
                    logger.info(f"Help command received from {interaction.user}")
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
                    
                except Exception as e:
                    logger.error(f"Error in help command: {str(e)}", exc_info=True)
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "Sorry, there was an error displaying the help message.",
                            ephemeral=True
                        )

            @self.tree.command(
                name="trivia",
                description="Start an Octant trivia game"
            )
            async def trivia_command(interaction: discord.Interaction):
                try:
                    logger.info(f"Trivia command received from {interaction.user}")
                    await interaction.response.defer()
                    await self.trivia.start_game(interaction)
                except Exception as e:
                    logger.error(f"Error in trivia command: {str(e)}", exc_info=True)
                    await interaction.followup.send(
                        "Sorry, there was an error starting the trivia game.",
                        ephemeral=True
                    )

            logger.info("Commands registered successfully")
            
        except Exception as e:
            logger.error(f"Error registering commands: {str(e)}", exc_info=True)
            raise

    async def setup_hook(self):
        """Sync commands with Discord."""
        try:
            logger.info("Syncing commands with Discord...")
            await self.tree.sync()
            logger.info("Commands synced successfully")
        except Exception as e:
            logger.error(f"Error syncing commands: {str(e)}", exc_info=True)
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
