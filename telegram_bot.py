import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram_trivia import TelegramTrivia
import time
import asyncio
from telegram.error import NetworkError, TimedOut, RetryAfter
from chat_handler import ChatHandler

# Enhanced logging configuration with HTTP request tracking
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configure httpx logging
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.INFO)

# Configure telegram library logging
telegram_logger = logging.getLogger("telegram")
telegram_logger.setLevel(logging.INFO)

# Add file handler for persistent logging with rotation
from logging.handlers import RotatingFileHandler
file_handler = RotatingFileHandler(
    'telegram_bot.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s'
))
logger.addHandler(file_handler)
httpx_logger.addHandler(file_handler)
telegram_logger.addHandler(file_handler)

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
    """Handle errors in the telegram bot with enhanced recovery and monitoring."""
    try:
        error_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Log detailed error information
        if update:
            logger.error(f"[{error_time}] Update {update.update_id} caused error: {context.error}")
            if update.effective_user:
                logger.error(f"User info: ID={update.effective_user.id}, Username={update.effective_user.username}")
        else:
            logger.error(f"[{error_time}] Error occurred without update: {context.error}")
        
        # Enhanced error classification and handling
        if isinstance(context.error, NetworkError):
            logger.warning(f"[{error_time}] Network error detected: {str(context.error)}")
            logger.info("Implementing exponential backoff strategy...")
            retry_delay = min(300, 2 ** context.error_count if hasattr(context, 'error_count') else 1)
            logger.info(f"Waiting {retry_delay} seconds before retry...")
            await asyncio.sleep(retry_delay)
            
        elif isinstance(context.error, TimedOut):
            logger.warning(f"[{error_time}] Request timed out: {str(context.error)}")
            logger.info("Implementing adaptive retry strategy...")
            retry_delay = min(60, 1 + (context.error_count * 0.5) if hasattr(context, 'error_count') else 1)
            logger.info(f"Waiting {retry_delay} seconds before retry...")
            await asyncio.sleep(retry_delay)
            
        elif isinstance(context.error, RetryAfter):
            retry_after = context.error.retry_after
            logger.warning(f"[{error_time}] Rate limit exceeded. Retry after: {retry_after}s")
            logger.info(f"Implementing rate limit cooldown...")
            await asyncio.sleep(retry_after)
            
        else:
            logger.error(f"[{error_time}] Unhandled error type: {type(context.error).__name__}")
            logger.error(f"Error details: {str(context.error)}")
            logger.info("Implementing default error recovery...")
            await asyncio.sleep(5)
        
        # Monitor memory usage during errors
        import psutil
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024
        logger.info(f"Current memory usage: {memory_usage:.2f} MB")
        
        # Provide user feedback if possible
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "I encountered a temporary issue. Please try again in a moment. "
                    "Our system is actively working to resolve this."
                )
            except Exception as reply_error:
                logger.error(f"Failed to send error message to user: {str(reply_error)}")
                
    except Exception as e:
        logger.error(f"Critical error in error handler: {str(e)}")
        logger.error("Error handler failed to process the error properly")

def main() -> None:
    """Start the bot with enhanced monitoring and reconnection logic."""
    retry_count = 0
    max_retries = -1  # Infinite retries for 24/7 uptime
    base_delay = 5
    max_delay = 300  # 5 minutes
    start_time = time.time()
    last_stats_time = time.time()
    stats_interval = 3600  # Log statistics every hour
    
    # Initialize system monitoring
    import psutil
    process = psutil.Process()

    def log_system_stats():
        """Log system statistics."""
        try:
            memory_usage = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            current_uptime = time.time() - start_time
            hours, remainder = divmod(current_uptime, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            logger.info("━━━━━━ System Statistics ━━━━━━")
            logger.info(f"Uptime: {int(hours)}h {int(minutes)}m {int(seconds)}s")
            logger.info(f"Memory Usage: {memory_usage:.2f} MB")
            logger.info(f"CPU Usage: {cpu_percent:.1f}%")
            logger.info(f"Retry Count: {retry_count}")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        except Exception as e:
            logger.error(f"Error logging system stats: {str(e)}")

    while True:
        try:
            logger.info("Initializing Telegram bot...")
            
            # Get the token from environment variable
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if not token:
                logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
                return

            # Create the Application with detailed configuration and health checks
            application = (
                Application.builder()
                .token(token)
                .get_updates_read_timeout(60)
                .get_updates_write_timeout(60)
                .get_updates_connect_timeout(60)
                .get_updates_pool_timeout(None)
                .connect_timeout(60)
                .read_timeout(60)
                .write_timeout(60)
                .pool_timeout(None)
                .build()
            )

            # Add handlers with enhanced monitoring
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("help", help_command))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            application.add_handler(CallbackQueryHandler(telegram_trivia.handle_answer, pattern="^trivia_"))
            application.add_handler(CommandHandler("trivia", telegram_trivia.start_game))
            application.add_error_handler(error_handler)

            # Enhanced startup logging
            logger.info("━━━━━━ Bot Configuration ━━━━━━")
            logger.info(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Retry Count: {retry_count}")
            logger.info("Connection Parameters:")
            logger.info("- Polling Timeout: 60s")
            logger.info("- Connection Retries: infinite")
            logger.info("- Update Mode: polling")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            # Reset retry count on successful start
            retry_count = 0
            
            # Log initial system statistics
            log_system_stats()
            
            # Start polling with enhanced error recovery
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                read_timeout=60,
                write_timeout=60,
                connect_timeout=60,
                pool_timeout=None
            )
            
            logger.info("Polling started successfully")
            
        except Exception as e:
            retry_count += 1
            delay = min(base_delay * (2 ** (retry_count - 1)), max_delay)
            
            # Enhanced error logging
            logger.error("━━━━━━ Error Report ━━━━━━")
            logger.error(f"Error Type: {type(e).__name__}")
            logger.error(f"Error Message: {str(e)}")
            logger.error(f"Retry Count: {retry_count}")
            logger.error(f"Next Retry: {delay} seconds")
            logger.error("━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # Log system statistics on error
            log_system_stats()
            
            # If it's time to log periodic statistics
            current_time = time.time()
            if current_time - last_stats_time >= stats_interval:
                log_system_stats()
                last_stats_time = current_time
            
            # Reset retry count if max retries reached
            if max_retries > 0 and retry_count >= max_retries:
                logger.warning("Max retries reached, resetting retry count")
                retry_count = 0
            
            # Implement exponential backoff
            logger.info(f"Waiting {delay} seconds before retry...")
            time.sleep(delay)

if __name__ == '__main__':
    main()
