import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "👋 Welcome! I'm the Octant Bot. Type /help to see what I can do!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "Here's what I can do:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo the user message."""
    await update.message.reply_text(f"You said: {update.message.text}")

def main():
    """Start the bot."""
    try:
        # Get the token from environment variable
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
            return

        # Create the application
        application = Application.builder().token(token).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Start polling
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    main()