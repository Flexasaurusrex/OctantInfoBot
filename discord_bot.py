import discord
from discord.ext import commands
import os
import logging
from chat_handler import ChatHandler
from discord_trivia import DiscordTrivia

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
        intents.messages = True
        intents.guilds = True
        super().__init__(command_prefix='/', intents=intents)
        
        # Initialize handlers
        self.chat_handler = ChatHandler()
        self.trivia = DiscordTrivia()
        logger.info("Bot initialized with all handlers")
        
        # Remove default help command to use our custom help
        self.remove_command('help')

    async def setup_hook(self):
        """Set up the bot's internal cache and add commands."""
        logger.info("Bot is setting up...")
        
        # Add commands
        @self.command(name='help')
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
            
        @self.command(name='trivia')
        async def trivia_command(ctx):
            """Start a trivia game"""
            await self.trivia.start_game(ctx)

    async def on_ready(self):
        """Log when the bot is ready."""
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

    async def on_message(self, message):
        """Handle incoming messages."""
        # Debug logging for message processing
        logger.info(f"Received message: {message.content}")
        logger.info(f"Author: {message.author}")
        logger.info(f"Channel: {message.channel}")

        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        try:
            # Get context for command processing
            ctx = await self.get_context(message)

            # Process commands (like /help, /trivia)
            if message.content.startswith('/'):
                await self.process_commands(message)
                return

            # Check for bot mentions and replies
            is_mentioned = self.user.mentioned_in(message)
            is_reply_to_bot = (
                message.reference and 
                message.reference.resolved and 
                message.reference.resolved.author.id == self.user.id
            )

            # Handle mentions and replies
            if is_mentioned or is_reply_to_bot:
                # Clean message content
                content = message.content.strip()
                # Remove both the mention formats
                content = content.replace(f"<@{self.user.id}>", "").strip()
                content = content.replace(f"<@!{self.user.id}>", "").strip()
                logger.info(f"Processing cleaned content: {content}")

                # Handle "start trivia" command
                if content.lower() == "start trivia":
                    await self.trivia.start_game(ctx)
                    return

                # Get chat response for other messages
                try:
                    if content:
                        logger.info(f"Getting chat response for: {content}")
                        response = self.chat_handler.get_response(content)
                        logger.info(f"Chat response received: {response}")
                        
                        if response:
                            if isinstance(response, list):
                                for chunk in response:
                                    if chunk and chunk.strip():
                                        await message.reply(chunk.strip())
                            else:
                                await message.reply(response)
                        else:
                            await message.reply("I'm here to help you learn about Octant! What would you like to know?")
                    else:
                        await message.reply("How can I help you learn about Octant?")
                except Exception as chat_error:
                    logger.error(f"Chat handler error: {str(chat_error)}", exc_info=True)
                    await message.reply("I encountered an error processing your request. Please try again.")

        except Exception as e:
            logger.error(f"Error in message handler: {str(e)}", exc_info=True)
            await message.channel.send("I encountered an error. Please try again.")

    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions for trivia."""
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("trivia_"):
                answer = custom_id.split("_")[1]
                await self.trivia.handle_answer(interaction, answer)

async def main():
    """Start the bot."""
    bot = OctantDiscordBot()
    
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
