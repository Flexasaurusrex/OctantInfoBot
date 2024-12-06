import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from chat_handler import ChatHandler
from telegram_trivia import TelegramTrivia

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize handlers
chat_handler = ChatHandler()
telegram_trivia = TelegramTrivia()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    welcome_message = """
Welcome to the Octant Information Bot! 🤖

I'm here to help you learn about Octant and answer any questions you have about the ecosystem. Here are some things you can do:

/help - See all available commands
/trivia - Start a fun trivia game about Octant

Feel free to ask me anything about Octant! 🚀
    """
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = """
Available commands:

/start - Start the bot
/help - Show this help message
/trivia - Start a trivia game

You can also ask me any questions about:
• Octant's ecosystem
• GLM token utility
• Governance process
• Funding mechanisms
• And more!
    """
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages."""
    try:
        user_message = update.message.text
        logger.info(f"Received message: {user_message}")
        
        response = chat_handler.get_response(user_message)
        await update.message.reply_text(response, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        await update.message.reply_text(
            "I encountered an error. Please try again."
        )

async def main() -> None:
    """Run the bot."""
    try:
        # Get token from environment
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
            return

        # Build application
        application = Application.builder().token(token).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("trivia", telegram_trivia.start_game))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(telegram_trivia.handle_answer, pattern="^trivia_"))

        # Start the bot
        logger.info("Starting bot...")
        await application.initialize()
        await application.start()
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Bot crashed: {str(e)}")
        raise
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())