import os
import discord
from discord.ext import commands
from chat_handler import ChatHandler
from discord_trivia import DiscordTrivia
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OctantDiscordBot(commands.Bot):
    def __init__(self):
        try:
            intents = discord.Intents.default()
            intents.message_content = True  # Requires Message Content Intent
            intents.members = True          # Requires Server Members Intent
            intents.presences = True        # Requires Presence Intent
            logger.info("Setting up bot with privileged intents...")
            super().__init__(command_prefix='/', intents=intents)
        except Exception as e:
            logger.error(f"Failed to initialize bot with intents: {str(e)}")
            logger.error("Please ensure all required intents are enabled in the Discord Developer Portal:")
            logger.error("1. PRESENCE INTENT")
            logger.error("2. SERVER MEMBERS INTENT")
            logger.error("3. MESSAGE CONTENT INTENT")
            raise
        
        try:
            self.chat_handler = ChatHandler()
            self.trivia = DiscordTrivia()
        except ValueError as e:
            logger.error(f"Failed to initialize ChatHandler or DiscordTrivia: {str(e)}")
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
            # Process commands first (these start with /)
            if message.content.startswith(self.command_prefix):
                await self.process_commands(message)
                return

            # Check if the message is a direct reply to the bot
            is_reply_to_bot = (
                message.reference 
                and message.reference.resolved 
                and message.reference.resolved.author.id == self.user.id
            )
            
            # Check if the bot is mentioned
            is_mentioned = self.user.mentioned_in(message)
            
            # Check for "start trivia" message with mention
            if message.content.lower() == f"<@{self.user.id}> start trivia" or message.content.lower() == f"<@!{self.user.id}> start trivia":
                await self.trivia.start_game(await self.get_context(message))
                return
                
            # Only respond if the bot is mentioned or it's a reply to the bot
            if is_mentioned or is_reply_to_bot:
                # Remove the mention from the message content
                clean_content = message.clean_content.replace(f"@{self.user.display_name}", "").strip()
                
                response = self.chat_handler.get_response(clean_content)
                # Split long messages if needed
                if isinstance(response, list):
                    for chunk in response:
                        await message.reply(chunk)
                else:
                    await message.reply(response)
                    
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            await message.channel.send("I encountered an error processing your message. Please try again.")

    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions."""
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("trivia_"):
                answer = custom_id.split("_")[1]
                await self.trivia.handle_answer(interaction, answer)

async def main():
    # Create bot instance
    bot = OctantDiscordBot()
    
    # Add commands
    @bot.command(name='trivia')
    async def trivia_command(ctx):
        """Start a trivia game"""
        await bot.trivia.start_game(ctx)

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
