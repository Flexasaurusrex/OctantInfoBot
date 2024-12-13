import os
import discord
from discord.ext import commands
from chat_handler import ChatHandler
import logging

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
        super().__init__(command_prefix='/', intents=intents)
        
        try:
            self.chat_handler = ChatHandler()
        except ValueError as e:
            logger.error(f"Failed to initialize ChatHandler: {str(e)}")
            raise
            
        # Remove default help command
        self.remove_command('help')
        
    async def setup_hook(self):
        """Setup hook for the bot."""
        logger.info("Bot is setting up...")
        
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info('------')
        
    async def on_message(self, message):
        """Handle incoming messages."""
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
            
        try:
            # Process commands first
            await self.process_commands(message)
            
            # If it's not a command, process as regular message
            if not message.content.startswith(self.command_prefix):
                response = self.chat_handler.get_response(message.content)
                # Split long messages if needed
                if isinstance(response, list):
                    for chunk in response:
                        await message.channel.send(chunk)
                else:
                    await message.channel.send(response)
                    
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            await message.channel.send("I encountered an error processing your message. Please try again.")

async def main():
    # Create bot instance
    bot = OctantDiscordBot()
    
    # Add commands
    @bot.command(name='help')
    async def help_command(ctx):
        """Show help message"""
        help_text = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Available Commands
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎮 Game Commands:
• /trivia - Start a trivia game
• start trivia - Also starts trivia game
• end trivia - End current trivia game

📋 Information Commands:
• /help - Show this help message
• /stats - View your chat statistics
• /learn - Access learning modules

📌 Topic-Specific Commands:
• /funding - Learn about Octant's funding
• /governance - Understand governance
• /rewards - Explore reward system

Type any command to get started!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        await ctx.send(help_text)
        
    # Run the bot
    discord_token = os.environ.get('DISCORD_BOT_TOKEN')
    if not discord_token:
        logger.error("DISCORD_BOT_TOKEN not found in environment variables")
        raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
        
    try:
        await bot.start(discord_token)
    except discord.LoginFailure:
        logger.error("Failed to login to Discord. Please check your token.")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
