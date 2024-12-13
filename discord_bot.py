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
                logger.info(f"Processing command: {message.content}")
                await self.process_commands(message)
                return

            # Check for replies to bot messages
            is_reply_to_bot = bool(
                message.reference 
                and message.reference.resolved 
                and message.reference.resolved.author.id == self.user.id
            )
            
            # Check for mentions using Discord's built-in system
            is_mentioned = self.user.mentioned_in(message)
            
            # Additional mention pattern check for redundancy
            if not is_mentioned:
                mention_patterns = [
                    f'<@{self.user.id}>',  # Standard mention
                    f'<@!{self.user.id}>'  # Nickname mention
                ]
                is_mentioned = any(pattern in message.content for pattern in mention_patterns)
            
            # Log mention status for debugging
            if is_mentioned or is_reply_to_bot:
                logger.info("━━━━━━ Message Detection ━━━━━━")
                logger.info(f"Message Content: {message.content}")
                logger.info(f"Author: {message.author.name}")
                logger.info(f"Channel: {message.channel.name}")
                logger.info(f"Is Mention: {is_mentioned}")
                logger.info(f"Is Reply: {is_reply_to_bot}")
                logger.info("━━━━━━━━━━━━━━━━━━━━━━━━")

            # Only respond to mentions or replies
            if not (is_mentioned or is_reply_to_bot):
                return
                
            logger.info(f"Processing message - Is mentioned: {is_mentioned}, Is reply: {is_reply_to_bot}")

            logger.info("━━━━━━ Bot Interaction ━━━━━━")
            logger.info(f"Interaction Type: {'Reply' if is_reply_to_bot else 'Mention' if is_mentioned else 'Unknown'}")
            logger.info(f"Raw Message: {message.content}")
            logger.info(f"Author: {message.author.name} (ID: {message.author.id})")
            logger.info(f"Channel: {message.channel.name} (ID: {message.channel.id})")
            logger.info(f"Is Mentioned: {is_mentioned}")
            logger.info(f"Is Reply: {is_reply_to_bot}")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                
            # Enhanced message content extraction and cleaning
            try:
                # Get the message content
                content = message.content.strip()
                    
                # Remove all possible mention patterns
                mention_patterns = [
                    f'<@{self.user.id}>',        # Standard mention
                    f'<@!{self.user.id}>',       # Nickname mention
                    f'@{self.user.display_name}', # Display name mention
                    self.user.name,              # Bot name
                ]
                    
                for pattern in mention_patterns:
                    content = content.replace(pattern, '').strip()
                    
                # Log the cleaning process
                logger.info("━━━━━━ Message Processing ━━━━━━")
                logger.info(f"Original: {message.content}")
                logger.info(f"Cleaned: {content}")
                logger.info(f"Is Mention: {is_mentioned}")
                logger.info(f"Is Reply: {is_reply_to_bot}")
                logger.info("━━━━━━━━━━━━━━━━━━━━━━━━")
                    
                # Process message if not empty
                if content.strip():
                    response = self.chat_handler.get_response(content)
                    if isinstance(response, list):
                        for chunk in response:
                            if chunk.strip():
                                await message.reply(chunk, mention_author=True)
                    else:
                        if response.strip():
                            await message.reply(response, mention_author=True)
                else:
                    # If no content after cleaning, provide a helpful response
                    await message.reply("Hi! How can I help you today?", mention_author=True)
                        
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                await message.reply("I encountered an error processing your message. Please try again.", mention_author=True)
            
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
        logger.info("━━━━━━ Trivia Command (via /trivia) ━━━━━━")
        logger.info(f"Initiating trivia game for user: {ctx.author.name}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
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

📋 Information Commands:
• /help - Show this help message

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