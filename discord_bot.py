import os
import logging
import discord
from discord.ext import commands
from chat_handler import ChatHandler
from discord_trivia import DiscordTrivia

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('discord_bot.log')
    ]
)
logger = logging.getLogger(__name__)

class OctantDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='/',
            intents=intents
        )
        
        self.chat_handler = ChatHandler()
        self.trivia = DiscordTrivia()
        self.remove_command('help')

    async def setup_hook(self):
        """Set up bot commands."""
        @self.command(name='trivia')
        async def trivia_command(ctx):
            """Start a trivia game"""
            try:
                await self.trivia.start_game(ctx)
            except Exception as e:
                logger.error(f"Error in trivia command: {e}")
                await ctx.send("Sorry, there was an error starting the trivia game. Please try again.")

        @self.command(name='help')
        async def help_command(ctx):
            """Show help message"""
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
            
            try:
                await ctx.send(embed=help_embed)
            except Exception as e:
                logger.error(f"Error sending help message: {e}")
                await ctx.send("Sorry, there was an error displaying the help message. Please try again.")

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info("━━━━━━ Bot Ready ━━━━━━")
        logger.info(f"Logged in as: {self.user.name}")
        logger.info(f"Bot ID: {self.user.id}")
        logger.info(f"Guilds connected: {len(self.guilds)}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━")

    async def on_message(self, message):
        """Handle incoming messages."""
        if message.author == self.user:
            return

        try:
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
                if isinstance(response, list):
                    for chunk in response:
                        if chunk and chunk.strip():
                            await message.reply(chunk.strip(), mention_author=True)
                else:
                    await message.reply(response.strip(), mention_author=True)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await message.channel.send("I encountered an error processing your message. Please try again.")

async def main():
    """Main bot execution with simple retry logic."""
    try:
        logger.info("Starting Discord bot")
        bot = OctantDiscordBot()
        
        discord_token = os.environ.get('DISCORD_BOT_TOKEN')
        if not discord_token:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")

        await bot.start(discord_token)
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
