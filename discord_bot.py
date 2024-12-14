import os
import logging
import discord
from discord.ext import commands
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

class OctantBot(commands.Bot):
    def __init__(self):
        try:
            # Set up basic intents
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True

            # Initialize the bot
            super().__init__(
                command_prefix='/',
                intents=intents
            )

            # Initialize handlers
            self.chat_handler = ChatHandler()
            self.trivia = DiscordTrivia()
            
            # Remove default help command
            self.remove_command('help')
            
            logger.info("Bot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}", exc_info=True)
            raise

    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("Setting up bot...")
        
        @self.command(name='trivia')
        async def trivia_command(ctx):
            """Start a trivia game"""
            try:
                logger.info(f"Trivia command received from {ctx.author}")
                await self.trivia.start_game(ctx)
            except Exception as e:
                logger.error(f"Error in trivia command: {str(e)}", exc_info=True)
                await ctx.send("Sorry, there was an error starting the trivia game. Please try again.")

        @self.command(name='help')
        async def help_command(ctx):
            """Show help message"""
            try:
                logger.info(f"Help command received from {ctx.author}")
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
                    name="💬 Chat Features",
                    value="• Reply to any of my messages to chat\n• Ask questions about Octant\n• Get help with Octant features",
                    inline=False
                )
                
                help_embed.set_footer(text="Type /trivia to start playing!")
                
                await ctx.send(embed=help_embed)
                logger.info("Help message sent successfully")
            except Exception as e:
                logger.error(f"Error sending help message: {str(e)}", exc_info=True)
                await ctx.send("Sorry, there was an error displaying the help message. Please try again.")

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

            logger.info(f"Message received from {message.author}: {message.content[:50]}...")

            # Process commands first
            await self.process_commands(message)

            # Check if message is a reply to bot
            is_reply_to_bot = bool(
                message.reference 
                and message.reference.resolved 
                and message.reference.resolved.author.id == self.user.id
            )

            if not is_reply_to_bot:
                return

            # Get and send response
            response = self.chat_handler.get_response(message.content)
            if response:
                logger.info("Sending response to user")
                if isinstance(response, list):
                    for chunk in response:
                        if chunk and chunk.strip():
                            await message.reply(chunk.strip(), mention_author=True)
                else:
                    await message.reply(response.strip(), mention_author=True)

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            await message.channel.send("I encountered an error processing your message. Please try again.")

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