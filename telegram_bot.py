import os
import time
import asyncio
import logging
import psutil
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from chat_handler import ChatHandler
from telegram_trivia import TelegramTrivia

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize handlers
chat_handler = ChatHandler()
telegram_trivia = TelegramTrivia()

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Restart the bot."""
    await update.message.reply_text("Restarting the bot... Please wait.")
    logger.info(f"Restart command issued by user {update.effective_user.id}")
    try:
        context.application._restart_requested = True
        logger.info("Initiating graceful shutdown...")
    except Exception as e:
        logger.error(f"Error during restart command: {str(e)}")
        await update.message.reply_text("Error occurred during restart. Please try again later.")

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
/restart - Restart the bot

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
    """Handle incoming messages with basic error recovery."""
    try:
        user_message = update.message.text
        logger.info(f"Received message: {user_message}")
        
        # Get response
        response = chat_handler.get_response(user_message)
        
        # Send response with HTML parsing
        await update.message.reply_text(
            response,
            parse_mode='HTML',
            disable_web_page_preview=False
        )
        
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        await update.message.reply_text(
            "I encountered an error processing your message. Please try again in a moment."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Basic error handler with simple recovery."""
    try:
        logger.error(f"Error: {context.error}")
        
        # Basic error handling with retry
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "I encountered a temporary issue. Please try again in a moment."
            )
            
    except Exception as e:
        logger.error(f"Error in error handler: {str(e)}")

def log_system_stats():
    """Basic system statistics logging."""
    try:
        memory = psutil.virtual_memory()
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        cpu_percent = psutil.Process().cpu_percent()
        
        logger.info("━━━━━━ System Health Check ━━━━━━")
        logger.info(f"Memory Usage: {memory_usage:.2f} MB")
        logger.info(f"CPU Usage: {cpu_percent:.1f}%")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
    except Exception as e:
        logger.error(f"Error logging system stats: {str(e)}")

async def main() -> None:
    """Start the bot with basic monitoring and reliability."""
    retry_count = 0
    base_delay = 5
    max_delay = 300
    
    while True:
        try:
            # Log startup
            logger.info("Initializing Telegram bot...")
            
            # Get token
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if not token:
                logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
                return
            
            # Configure application
            application = (
                Application.builder()
                .token(token)
                .connect_timeout(30)
                .read_timeout(30)
                .write_timeout(30)
                .get_updates_read_timeout(30)
                .build()
            )
            
            # Set restart flag
            application._restart_requested = False
            
            # Add handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("help", help_command))
            application.add_handler(CommandHandler("restart", restart_command))
            application.add_handler(CommandHandler("trivia", telegram_trivia.start_game))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            application.add_handler(CallbackQueryHandler(telegram_trivia.handle_answer, pattern="^trivia_"))
            application.add_error_handler(error_handler)
            
            # Log configuration
            logger.info("━━━━━━ Bot Configuration ━━━━━━")
            logger.info(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Bot Version: 1.0.1")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # Initialize and start
            await application.initialize()
            await application.start()
            logger.info("Starting polling...")
            
            # Start polling
            await application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
            # Reset retry count on successful start
            retry_count = 0
            
            # Log initial stats
            log_system_stats()
            
            # Wait for stop signal
            while not getattr(application, '_restart_requested', False):
                await asyncio.sleep(1)
                
            logger.info("Stop signal received, shutting down...")
            
        except Exception as e:
            retry_count += 1
            delay = min(base_delay * (2 ** (retry_count - 1)), max_delay)
            
            logger.error(f"Error: {str(e)}")
            logger.info(f"Retrying in {delay} seconds...")
            
            await asyncio.sleep(delay)
            continue
            
        finally:
            try:
                await application.updater.stop()
                await application.stop()
                await application.shutdown()
            except Exception as e:
                logger.error(f"Error during shutdown: {str(e)}")
            
            if getattr(application, '_restart_requested', False):
                logger.info("Restart requested, reinitializing...")
                continue
                
            logger.info("Bot stopped")

if __name__ == '__main__':
    asyncio.run(main())