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
        
    def is_bot_mentioned(self, message):
        """Simple and reliable mention detection."""
        try:
            # Basic mention checks
            if self.user.mentioned_in(message):
                logger.info(f"Direct mention detected in message: {message.content}")
                return True

            # Case insensitive text content check
            message_lower = message.content.lower()
            bot_name_lower = self.user.name.lower()

            # Simple mention patterns that must be matched exactly
            mention_patterns = [
                f'<@{self.user.id}>',  # Standard mention
                f'<@!{self.user.id}>', # Nickname mention
                f'@{bot_name_lower}',   # Name with @
                '@octantbot',          # Common format
                'octantbot'            # Name only
            ]

            # Log the mention check attempt
            logger.info("━━━━━━ Checking Message for Mentions ━━━━━━")
            logger.info(f"Message: {message.content}")
            logger.info(f"From: {message.author.name}")
            logger.info(f"Channel: {message.channel.name}")

            # Check each pattern
            for pattern in mention_patterns:
                pattern_lower = pattern.lower()
                if pattern_lower in message_lower:
                    logger.info(f"Mention matched pattern: {pattern}")
                    return True

            logger.info("No mention patterns matched")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            return False

        except Exception as e:
            logger.error(f"Error in mention detection: {str(e)}")
            logger.exception("Full traceback:")
            return False
        
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

            # Check for bot mention and direct replies
            is_mentioned = self.is_bot_mentioned(message)
            is_reply_to_bot = (
                message.reference 
                and message.reference.resolved 
                and message.reference.resolved.author.id == self.user.id
            )

            # Respond to mentions or direct replies
            if is_mentioned or is_reply_to_bot:
                logger.info("━━━━━━ Bot Interaction ━━━━━━")
                logger.info(f"Message Type: {'Reply' if is_reply_to_bot else 'Mention'}")
                logger.info(f"Message: {message.content}")
                logger.info(f"Author: {message.author.name} (ID: {message.author.id})")
                logger.info(f"Channel: {message.channel.name} (ID: {message.channel.id})")
                logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                
                # Clean the message content
                clean_content = message.clean_content
                
                # Remove bot mention if present
                if is_mentioned:
                    mention = f"<@{self.user.id}>"
                    mention_nick = f"<@!{self.user.id}>"
                    clean_content = clean_content.replace(mention, "").replace(mention_nick, "")
                    clean_content = clean_content.replace(f"@{self.user.display_name}", "").strip()
                
                logger.info(f"Processing cleaned message: {clean_content}")
                
                try:
                    response = self.chat_handler.get_response(clean_content)
                    # Split long messages if needed
                    if isinstance(response, list):
                        for chunk in response:
                            if chunk.strip():
                                await message.reply(chunk)
                    else:
                        if response.strip():
                            await message.reply(response)
                except Exception as e:
                    logger.error(f"Error getting response: {str(e)}")
                    await message.reply("I encountered an error processing your message. Please try again.")
                    
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
