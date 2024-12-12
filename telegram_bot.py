import os
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from chat_handler import ChatHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('telegram_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.chat_handler = ChatHandler()
        self.application = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Simple start command handler."""
        try:
            welcome_message = "👋 Welcome to the Octant Information Bot! Ask me anything about Octant's ecosystem, GLM tokens, governance, or funding!"
            await update.message.reply_text(welcome_message)
            logger.info(f"Start command handled for user {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error in start command: {str(e)}")
            await update.message.reply_text("Sorry, there was an error processing your command.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Simple help command handler."""
        try:
            help_text = (
                "📚 Commands:\n"
                "/start - Start the bot\n"
                "/help - Show this help\n\n"
                "Just ask any question about Octant!"
            )
            await update.message.reply_text(help_text)
            logger.info(f"Help command handled for user {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error in help command: {str(e)}")
            await update.message.reply_text("Sorry, there was an error showing the help message.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages."""
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        message_text = update.message.text.strip()
        logger.info(f"Processing message from user {user_id}: {message_text[:50]}...")

        try:
            await update.message.chat.send_action(action="typing")
            success, response = self.chat_handler.get_response(message_text)
            await update.message.reply_text(
                response if success else "I'm having trouble right now. Please try again in a moment."
            )
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            await update.message.reply_text("Sorry, I encountered an error. Please try again.")

def run_bot():
    """Entry point for the bot."""
    try:
        # Get the token from environment
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")

        # Create bot instance
        bot = TelegramBot()
        
        # Build and configure application
        application = Application.builder().token(token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", bot.start))
        application.add_handler(CommandHandler("help", bot.help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
        
        # Start the bot
        logger.info("Starting bot...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    run_bot()