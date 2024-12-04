import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import time
import asyncio
from telegram.error import NetworkError, TimedOut, RetryAfter
from chat_handler import ChatHandler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize chat handler
chat_handler = ChatHandler()

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
Here are the available commands:

/start - Start the bot
/help - Show this help message
/trivia - Start a trivia game

You can also ask me any questions about:
• Octant's ecosystem
• GLM token utility
• Governance process
• Funding mechanisms
• And more!

Just type your question and I'll help you out! 📚
    """
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages."""
    try:
        user_message = update.message.text
        response = chat_handler.get_response(user_message)
        await update.message.reply_text(response, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        await update.message.reply_text("I encountered an error processing your message. Please try again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the telegram bot."""
    try:
        if update:
            logger.error(f"Update {update.update_id} caused error {context.error}")
        else:
            logger.error(f"Error occurred without update: {context.error}")
        
        if isinstance(context.error, NetworkError):
            logger.info("Network error occurred, will retry...")
            await asyncio.sleep(1)
        elif isinstance(context.error, TimedOut):
            logger.info("Request timed out, will retry...")
            await asyncio.sleep(0.5)
        elif isinstance(context.error, RetryAfter):
            logger.info(f"Rate limit hit. Sleeping for {context.error.retry_after} seconds")
            await asyncio.sleep(context.error.retry_after)
        else:
            logger.error("Unknown error occurred")
            logger.error(f"Error details: {str(context.error)}")
            
        if update and update.message:
            await update.message.reply_text(
                "Sorry, I encountered a temporary issue. Please try again in a moment."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {str(e)}")

def main() -> None:
    """Start the bot with enhanced error handling and reconnection logic."""
    retry_count = 0
    max_retries = 5  # Set to -1 for infinite retries
    base_delay = 5
    max_delay = 300  # 5 minutes

    while True:
        try:
            logger.info("Initializing Telegram bot...")
            
            # Get the token from environment variable
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if not token:
                logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
                return

            # Create the Application with detailed configuration
            application = (
                Application.builder()
                .token(token)
                .read_timeout(30)
                .write_timeout(30)
                .connect_timeout(30)
                .pool_timeout(30)
                .build()
            )

            # Add handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("help", help_command))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

            # Configure error handlers
            application.add_error_handler(error_handler)

            logger.info("Starting Telegram bot...")
            
            # Reset retry count on successful start
            retry_count = 0
            
            # Start the bot with persistent configuration
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                pool_timeout=30,
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30
            )
        except Exception as e:
            retry_count += 1
            # Calculate exponential backoff delay
            delay = min(base_delay * (2 ** (retry_count - 1)), max_delay)
            
            logger.error(f"Error in main loop: {str(e)}")
            logger.info(f"Attempt {retry_count}/{max_retries if max_retries > 0 else 'infinite'}")
            logger.info(f"Retrying in {delay} seconds...")
            
            # If max retries reached, log and continue with base delay
            if max_retries > 0 and retry_count >= max_retries:
                logger.warning("Max retries reached, resetting retry count")
                retry_count = 0
            
            time.sleep(delay)

if __name__ == '__main__':
    main()
