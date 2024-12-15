import os
import logging
import discord
from discord.ext import commands
from chat_handler import ChatHandler
from discord_trivia import DiscordTrivia

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OctantBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='/',
            intents=intents,
            description='Octant Discord Bot'
        )
        
        # Initialize handlers
        self.chat_handler = ChatHandler()
        self.trivia_game = DiscordTrivia()
        self.remove_command('help')

    async def setup_hook(self):
        """Register commands"""
        @self.command(name='trivia')
        async def trivia(ctx):
            """Start a trivia game"""
            try:
                await self.trivia_game.start_game(ctx)
            except Exception as e:
                logger.error(f"Error starting trivia: {e}")
                await ctx.send("Error starting trivia game. Please try again.")

        @self.command(name='help')
        async def help_command(ctx):
            """Show help message"""
            try:
                help_embed = discord.Embed(
                    title="📚 Octant Bot Help",
                    description="Welcome! Here are the available commands:",
                    color=discord.Color.blue()
                )
                help_embed.add_field(
                    name="🎮 Game Commands",
                    value="• `/trivia` - Start a trivia game about Octant",
                    inline=False
                )
                help_embed.add_field(
                    name="💬 Chat Features",
                    value="• Reply to any of my messages to chat\n• Ask questions about Octant",
                    inline=False
                )
                await ctx.send(embed=help_embed)
            except Exception as e:
                logger.error(f"Error showing help: {e}")
                await ctx.send("Error showing help message. Please try again.")

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f"Logged in as: {self.user.name}")
        logger.info(f"Bot ID: {self.user.id}")
        logger.info(f"Connected to {len(self.guilds)} guilds")

    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author == self.user:
            return

        try:
            # Process commands first
            await self.process_commands(message)

            # Handle replies to bot's messages
            if message.reference and message.reference.resolved:
                if message.reference.resolved.author == self.user:
                    response = self.chat_handler.get_response(message.content)
                    if response:
                        if isinstance(response, list):
                            for chunk in response:
                                if chunk and chunk.strip():
                                    await message.reply(chunk.strip())
                        else:
                            await message.reply(response.strip())

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await message.channel.send("I encountered an error processing your message. Please try again.")

async def main():
    """Main entry point"""
    while True:
        try:
            token = os.environ.get('DISCORD_BOT_TOKEN')
            if not token:
                raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
                
            bot = OctantBot()
            async with bot:
                await bot.start(token)
        except Exception as e:
            logger.error(f"Critical error: {e}")
            await asyncio.sleep(60)  # Wait 60 seconds before reconnecting
            logger.info("Attempting to reconnect...")
            continue

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
