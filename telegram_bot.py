import os
import logging
import asyncio
import time
from typing import Optional, Callable, Any
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.error import NetworkError, TimedOut
from chat_handler import ChatHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
        self.health_check_interval = 60  # seconds
        self.last_health_check = time.time()
        self.message_queue = asyncio.Queue()
        self.is_processing = False
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command with simple welcome message."""
        try:
            user = update.effective_user
            logger.info(f"Start command from user {user.id}")
            welcome_message = (
                "Welcome to the Octant Information Bot! 🤖\n\n"
                "I'm here to help you learn about Octant and answer your questions.\n"
                "Just ask me anything about Octant! 🚀"
            )
            await update.message.reply_text(welcome_message)
        except Exception as e:
            logger.error(f"Error in start command: {str(e)}", exc_info=True)
            await self._handle_error(update, "Sorry, there was an error starting the bot. Please try again.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command with simple help message."""
        user = update.effective_user
        logger.info(f"Help command from user {user.id}")
        help_text = (
            "📚 Available Commands:\n"
            "• /start - Start the bot\n"
            "• /help - Show this help message\n\n"
            "💡 You can ask me about:\n"
            "• Octant's ecosystem\n"
            "• GLM token utility\n"
            "• Governance process\n"
            "• Funding mechanisms\n\n"
            "Just type your question! 🤝"
        )
        await update.message.reply_text(help_text)

    async def _handle_error(self, update: Update, message: str) -> None:
        """Handle errors uniformly across the application."""
        try:
            if update and update.message:
                await update.message.reply_text(message)
        except Exception as e:
            logger.error(f"Error sending error message: {str(e)}", exc_info=True)

    async def process_message_queue(self) -> None:
        """Process messages from the queue with rate limiting."""
        while True:
            try:
                if not self.is_processing:
                    self.is_processing = True
                    update = await self.message_queue.get()
                    
                    if update and update.message and update.message.text:
                        user = update.effective_user
                        message_text = update.message.text
                        logger.info(f"Processing message from user {user.id}: {message_text[:50]}...")
                        
                        try:
                            response = self.chat_handler.get_response(message_text)
                            if response:
                                await update.message.reply_text(response)
                            else:
                                await self._handle_error(update, "I couldn't process your request. Please try again. 🔄")
                        except Exception as e:
                            logger.error(f"Error processing message: {str(e)}", exc_info=True)
                            await self._handle_error(update, "I encountered an issue. Please try again in a moment. 🔧")
                            
                    self.message_queue.task_done()
                    self.is_processing = False
                    await asyncio.sleep(1)  # Rate limiting
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in message queue processing: {str(e)}", exc_info=True)
                self.is_processing = False
                await asyncio.sleep(1)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Add messages to queue for processing."""
        if not update.message or not update.message.text:
            return
        
        try:
            await self.message_queue.put(update)
        except Exception as e:
            logger.error(f"Error queueing message: {str(e)}", exc_info=True)
            await self._handle_error(update, "Sorry, I'm having trouble processing messages right now. Please try again later.")

    async def health_check(self) -> None:
        """Enhanced health check system with connection monitoring."""
        consecutive_failures = 0
        max_failures = 3
        
        while True:
            try:
                current_time = time.time()
                if current_time - self.last_health_check >= self.health_check_interval:
                    # Check bot connection
                    if self.application and self.application.updater.running:
                        logger.info("Health check passed - Bot is running normally")
                        consecutive_failures = 0
                    else:
                        logger.warning("Health check warning - Bot updater not running")
                        consecutive_failures += 1
                    
                    # Check message processing
                    queue_size = self.message_queue.qsize()
                    if queue_size > 10:
                        logger.warning(f"Health check warning - Message queue size: {queue_size}")
                    
                    # Monitor processing state
                    if self.is_processing:
                        processing_time = time.time() - self.last_health_check
                        if processing_time > 30:  # 30 seconds threshold
                            logger.warning("Health check warning - Message processing stuck")
                            self.is_processing = False
                    
                    self.last_health_check = current_time
                    
                    # Recovery action if needed
                    if consecutive_failures >= max_failures:
                        logger.error("Health check critical - Attempting bot restart")
                        await self.shutdown()
                        await self.initialize()
                        consecutive_failures = 0
                
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Health check failed: {str(e)}", exc_info=True)
                consecutive_failures += 1
                await asyncio.sleep(5)  # Short delay before retry

    async def initialize(self) -> None:
        """Initialize the bot with enhanced error handling and monitoring."""
        try:
            # Verify environment
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if not token:
                raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set!")

            # Build and configure application
            self.application = Application.builder().token(token).build()
            
            # Add handlers with error catching
            handlers = [
                CommandHandler("start", self.start),
                CommandHandler("help", self.help_command),
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            ]
            
            for handler in handlers:
                self.application.add_handler(handler)
                logger.info(f"Added handler: {handler.__class__.__name__}")

            # Initialize core components
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            # Start background tasks
            asyncio.create_task(self.health_check())
            asyncio.create_task(self.process_message_queue())
            
            logger.info("Bot initialized and started successfully!")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}", exc_info=True)
            raise

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        if self.application:
            try:
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Bot shutdown completed")
            except Exception as e:
                logger.error(f"Error during shutdown: {str(e)}")

async def main():
    """Main function with basic error handling."""
    bot = TelegramBot()
    try:
        await bot.initialize()
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {str(e)}", exc_info=True)
    finally:
        await bot.shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {str(e)}")