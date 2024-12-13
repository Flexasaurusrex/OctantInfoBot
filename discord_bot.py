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
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='/',
            intents=intents,
            help_command=None
        )
        
        self.chat_handler = ChatHandler()
        self.trivia = DiscordTrivia()
        
    async def setup_hook(self):
        """Setup hook for the bot."""
        logger.info("Bot is setting up...")
        
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info('------')

async def main():
    try:
        bot = OctantDiscordBot()
        
        @bot.command(name='trivia')
        async def trivia_command(ctx):
            """Start a trivia game"""
            try:
                logger.info(f"Starting trivia game for {ctx.author.name} in {ctx.channel.name}")
                
                # Check permissions
                if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
                    await ctx.send("I need permission to send messages in this channel!")
                    return
                    
                if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
                    await ctx.send("I need permission to send embeds in this channel!")
                    return

                # Start the game
                await bot.trivia.start_game(ctx)
                    
            except Exception as e:
                logger.error(f"Error in trivia command: {str(e)}")
                await ctx.send("An error occurred while starting the game. Please try again.")

        @bot.command(name='help')
        async def help_command(ctx):
            """Show help message"""
            help_text = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Available Commands
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎮 Game Commands:
• /trivia - Start a trivia game

📋 Information Commands:
• /help - Show this help message

Type /trivia to start playing!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
            await ctx.send(help_text)
            
        discord_token = os.environ.get('DISCORD_BOT_TOKEN')
        if not discord_token:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
            
        await bot.start(discord_token)
            
    except Exception as e:
        logger.error(f"Critical error in main: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())