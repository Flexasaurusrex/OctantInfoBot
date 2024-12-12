import os
import logging
import asyncio
from typing import Optional, NoReturn
import signal
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
        self._shutdown_requested = False
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        try:
            user = update.effective_user
            logger.info(f"Start command from user {user.id} ({user.username or 'no username'})")
            
            welcome_message = (
                "👋 Welcome to the Octant Information Bot!\n\n"
                "I'm here to help you learn about:\n"
                "• Octant's ecosystem\n"
                "• GLM token utility\n"
                "• Governance process\n"
                "• Funding mechanisms\n\n"
                "Just ask me anything about these topics! 🚀"
            )
            await update.message.reply_text(welcome_message)
            
        except Exception as e:
            logger.error(f"Error in start command: {str(e)}", exc_info=True)
            await self._handle_error(update)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        try:
            user = update.effective_user
            logger.info(f"Help command from user {user.id} ({user.username or 'no username'})")
            
            help_text = (
                "📚 How to use this bot:\n\n"
                "1. Ask any question about Octant\n"
                "2. Get detailed information about:\n"
                "   • Ecosystem\n"
                "   • GLM tokens\n"
                "   • Governance\n"
                "   • Funding\n\n"
                "Commands:\n"
                "/start - Start the bot\n"
                "/help - Show this help message\n\n"
                "Need more help? Just ask! 🤝"
            )
            await update.message.reply_text(help_text)
            
        except Exception as e:
            logger.error(f"Error in help command: {str(e)}", exc_info=True)
            await self._handle_error(update)

    async def _handle_error(self, update: Update) -> None:
        """Unified error handling."""
        try:
            if update and update.message:
                await update.message.reply_text(
                    "I encountered an issue. Please try again in a moment. 🔧"
                )
        except Exception as e:
            logger.error(f"Error in error handler: {str(e)}", exc_info=True)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages with improved error handling."""
        if not update.message or not update.message.text:
            return

        user = update.effective_user
        message_text = update.message.text.strip()
        logger.info(f"Message from user {user.id} ({user.username or 'no username'}): {message_text[:50]}...")

        try:
            # Send typing action
            await update.message.chat.send_action(action="typing")
            
            # Get response from chat handler
            success, response = self.chat_handler.get_response(message_text)
            
            if success:
                await update.message.reply_text(response)
                logger.info(f"Successfully sent response to user {user.id}")
            else:
                logger.warning(f"Failed to generate response: {response}")
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            await self._handle_error(update)

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            self._shutdown_requested = True
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def run(self) -> NoReturn:
        """Run the bot with improved error handling and shutdown management."""
        try:
            # Get token from environment
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if not token:
                raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set!")

            # Setup signal handlers
            self._setup_signal_handlers()

            # Build application
            self.application = Application.builder().token(token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            )
            
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            logger.info("Bot initialized and started successfully!")
            
            # Keep the bot running until shutdown is requested
            while not self._shutdown_requested:
                await asyncio.sleep(1)
                
            logger.info("Shutdown requested, stopping bot...")
            await self.application.stop()
            
        except Exception as e:
            logger.error(f"Critical error in run: {str(e)}", exc_info=True)
            raise

async def main() -> None:
    """Main function with improved error handling."""
    bot = TelegramBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {str(e)}", exc_info=True)

if __name__ == '__main__':
    asyncio.run(main())
