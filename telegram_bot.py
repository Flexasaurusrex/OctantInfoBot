import os
import logging
import asyncio
from typing import Optional
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
        self.is_running = False
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
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
            await self._handle_error(update, "Sorry, there was an error. Please try again.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        try:
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
        except Exception as e:
            logger.error(f"Error in help command: {str(e)}", exc_info=True)
            await self._handle_error(update, "Sorry, there was an error. Please try again.")

    async def _handle_error(self, update: Update, message: str) -> None:
        """Handle errors uniformly."""
        try:
            if update and update.message:
                await update.message.reply_text(message)
        except Exception as e:
            logger.error(f"Error sending error message: {str(e)}", exc_info=True)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages."""
        if not update.message or not update.message.text:
            return

        user = update.effective_user
        message_text = update.message.text
        logger.info(f"Message from user {user.id}: {message_text[:50]}...")

        try:
            response = self.chat_handler.get_response(message_text)
            if response:
                await update.message.reply_text(response)
            else:
                await self._handle_error(update, "I couldn't process your request. Please try again. 🔄")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            await self._handle_error(update, "I encountered an issue. Please try again in a moment. 🔧")

    async def health_check(self) -> None:
        """Simple health check to monitor bot status."""
        while self.is_running:
            try:
                if self.application and not self.application.updater.running:
                    logger.error("Bot updater not running - attempting restart")
                    await self.shutdown()
                    await self.initialize()
            except Exception as e:
                logger.error(f"Health check error: {str(e)}", exc_info=True)
            await asyncio.sleep(60)  # Check every minute

    async def initialize(self) -> None:
        """Initialize the bot with basic error handling."""
        try:
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if not token:
                raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set!")

            self.application = Application.builder().token(token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Initialize and start
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            self.is_running = True
            asyncio.create_task(self.health_check())
            
            logger.info("Bot initialized and started successfully!")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}", exc_info=True)
            raise

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        if self.application:
            try:
                self.is_running = False
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