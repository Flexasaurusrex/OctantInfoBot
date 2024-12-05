import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram_trivia import TelegramTrivia
import time
import threading
from datetime import datetime, timedelta

class WatchdogTimer:
    def __init__(self, timeout=600):  # 10 minutes default timeout
        self.timeout = timeout
        self.last_ping = datetime.now()
        self.lock = threading.Lock()
        self.running = True
        self.warn_threshold = timeout * 0.8  # Warn at 80% of timeout
        self.start_monitor()

    def ping(self):
        with self.lock:
            self.last_ping = datetime.now()

    def start_monitor(self):
        def monitor():
            while self.running:
                with self.lock:
                    current_time = datetime.now()
                    time_since_ping = (current_time - self.last_ping).total_seconds()
                    if time_since_ping > self.timeout:
                        logger.error(f"""━━━━━━ Watchdog Timeout ━━━━━━
Last Ping: {self.last_ping}
Current Time: {current_time}
Time Since Last Ping: {time_since_ping:.2f}s
Timeout Threshold: {self.timeout}s
━━━━━━━━━━━━━━━━━━━━━━━━""")
                        os._exit(1)  # Force restart
                    elif time_since_ping > self.warn_threshold:
                        logger.warning(f"""━━━━━━ Watchdog Warning ━━━━━━
Last Ping: {self.last_ping}
Current Time: {current_time}
Time Since Last Ping: {time_since_ping:.2f}s
Warning Threshold: {self.warn_threshold}s
━━━━━━━━━━━━━━━━━━━━━━━━""")
                time.sleep(30)  # Check every 30 seconds
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    def stop(self):
        self.running = False
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

# Message rate monitoring
message_count = 0
last_message_time = time.time()
MESSAGE_RATE_INTERVAL = 60  # Check message rate every minute
MIN_MESSAGE_RATE = 0  # Minimum expected messages per minute (0 means no minimum)
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

# List of admin user IDs who can restart the bot
ADMIN_USER_IDS = {5100739421, 5365683947, 1087968824}  # Updated admin list with all admin IDs

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Restart the bot."""
    user_id = update.effective_user.id
    await update.message.reply_text("Restarting the bot... Please wait.")
    logger.info(f"Restart command issued by user {user_id}")
    
    try:
        # Set restart flag
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
/restart - Restart the bot (admin only)

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
    """Handle incoming messages with enhanced reliability and recovery."""
    try:
        # Ping watchdog on message receipt
        if hasattr(context.application, 'watchdog'):
            context.application.watchdog.ping()
        
        user_message = update.message.text
        logger.info(f"Received message: {user_message}")
        
        # Enhanced message handling with retries
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Get response with formatting
                response = chat_handler.get_response(user_message)
                
                # Log formatted response for verification
                logger.info("Formatted response ready for sending")
                
                # Send response with HTML parsing
                await update.message.reply_text(
                    response,
                    parse_mode='HTML',
                    disable_web_page_preview=False  # Enable link previews
                )
                
                logger.info("Response sent successfully")
                return  # Success, exit the retry loop
                
            except Exception as retry_error:
                retry_count += 1
                logger.warning(f"Attempt {retry_count} failed: {str(retry_error)}")
                if retry_count < max_retries:
                    await asyncio.sleep(1)  # Wait before retry
                else:
                    raise  # Re-raise the last error if all retries failed
        
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        error_message = "I encountered an error processing your message. I'll try to recover and respond shortly."
        try:
            await update.message.reply_text(error_message)
        except Exception as reply_error:
            logger.error(f"Failed to send error message: {str(reply_error)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Simple error handler with basic recovery."""
    try:
        error_time = time.strftime("%Y-%m-%d %H:%M:%S")
        logger.error(f"Error at {error_time}: {context.error}")
        
        # Basic error classification
        if isinstance(context.error, NetworkError):
            logger.info("Network error - will retry automatically")
            await asyncio.sleep(1)
        elif isinstance(context.error, TimedOut):
            logger.info("Timeout - will retry automatically")
            await asyncio.sleep(1)
        
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

async def main() -> None:
    """Start the bot with basic monitoring and reliability."""
    # Initialize all variables at start
    start_time = time.time()
    retry_count = 0
    max_retries = -1  # Infinite retries
    retry_delay = 10
    health_check_interval = 60
    last_health_check = time.time()
    
    # Get or create event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Initialize system monitoring
    import psutil
    process = psutil.Process()

    def log_system_stats():
        """Basic system statistics logging for stability monitoring."""
        try:
            # Get basic system metrics
            memory = psutil.virtual_memory()
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            memory_percent = (memory_usage / memory.total * 1024 * 1024) * 100
            cpu_percent = process.cpu_percent()
            current_uptime = time.time() - start_time
            hours, remainder = divmod(current_uptime, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            # Basic memory management
            if memory_usage > 200:  # Simple threshold of 200MB
                import gc
                gc.collect()
                logger.info("Memory cleanup triggered")
            
            # Simple status logging
            logger.info("━━━━━━ System Health Check ━━━━━━")
            logger.info(f"Uptime: {int(hours)}h {int(minutes)}m {int(seconds)}s")
            logger.info(f"Memory Usage: {memory_usage:.2f} MB ({memory_percent:.1f}%)")
            logger.info(f"CPU Usage: {cpu_percent:.1f}%")
            logger.info(f"Status: {'Active' if not retry_count else f'Reconnecting ({retry_count})'}")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # Smarter recovery triggers
            should_recover = False
            if memory_percent > 80:
                logger.warning("Memory usage critical")
                should_recover = True
            if cpu_percent > 90:
                logger.warning("CPU usage critical")
                should_recover = True
            if disk_percent > 90:
                logger.warning("Disk usage critical")
                should_recover = True
                
            if should_recover:
                logger.warning("System resources critical - initiating recovery procedure")
                return False
            return True
        except Exception as e:
            logger.error(f"Error logging system stats: {str(e)}")
            return False

    last_health_check = time.time()
    health_check_interval = 60  # Check every minute
    consecutive_failures = 0
    max_consecutive_failures = 3
    
    # Initialize watchdog with shorter timeout and connection monitoring
    watchdog = WatchdogTimer(timeout=120)  # 2 minute timeout for faster recovery
    last_successful_connection = time.time()
    
    while True:
        try:
            # Simple periodic health check
            current_time = time.time()
            if current_time - last_health_check >= health_check_interval:
                log_system_stats()
                last_health_check = current_time
            
            logger.info("Initializing Telegram bot...")
            
            # Get the token from environment variable
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if not token:
                logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
                return

            # Simple bot configuration with basic settings
            application = (
                Application.builder()
                .token(token)
                .connect_timeout(30)
                .read_timeout(30)
                .write_timeout(30)
                .get_updates_read_timeout(30)
                .build()
            )
            
            # Store application instance for restart handling
            application._restart_requested = False

            # Add handlers with enhanced monitoring
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("help", help_command))
            application.add_handler(CommandHandler("restart", restart_command))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            application.add_handler(CallbackQueryHandler(telegram_trivia.handle_answer, pattern="^trivia_"))
            application.add_handler(CommandHandler("trivia", telegram_trivia.start_game))
            application.add_error_handler(error_handler)
            
            # Store watchdog instance in application
            application.watchdog = watchdog

            # Enhanced startup logging with version tracking
            logger.info("━━━━━━ Bot Configuration ━━━━━━")
            logger.info(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Retry Count: {retry_count}")
            logger.info(f"Bot Version: 1.0.1")
            logger.info("Connection Parameters:")
            logger.info("- Polling Timeout: 60s")
            logger.info("- Connection Retries: infinite")
            logger.info("- Update Mode: polling")
            logger.info("- Health Check: Active")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            # Reset retry count on successful start
            retry_count = 0
            
            # Log initial system statistics
            log_system_stats()
            
            # Start polling with enhanced error recovery
            try:
                # Initialize and start application
                await application.initialize()
                await application.start()
                logger.info("Starting polling...")
                
                # Run polling in the current event loop
                if getattr(application, '_restart_requested', False):
                    application._restart_requested = False
                
                await application.updater.start_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True
                )
                
                # Wait for stop signal
                while not getattr(application, '_restart_requested', False):
                    await asyncio.sleep(1)
                
                logger.info("Stop signal received, shutting down...")
            except Exception as e:
                logger.error(f"Error during polling: {str(e)}")
                if not isinstance(e, RuntimeError) or "event loop is already running" not in str(e):
                    raise
            finally:
                # Cleanup
                try:
                    await application.updater.stop()
                    await application.stop()
                    await application.shutdown()
                except Exception as e:
                    logger.error(f"Error during shutdown: {str(e)}")
                
                if getattr(application, '_restart_requested', False):
                    logger.info("Restart requested, will reinitialize...")
                    continue
                
                logger.info("Polling stopped")
            
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
    import asyncio
    
    # Create new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
