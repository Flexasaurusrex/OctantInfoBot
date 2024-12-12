import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import asyncio
from telegram.error import NetworkError, TimedOut, RetryAfter
from chat_handler import ChatHandler
from telegram_trivia import TelegramTrivia

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize handlers
chat_handler = ChatHandler()
telegram_trivia = TelegramTrivia()

# List of admin user IDs who can restart the bot
ADMIN_USER_IDS = {5100739421, 5365683947, 1087968824}

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
    if not update.message or not update.message.text:
        return

    try:
        # Get response from chat handler
        response = chat_handler.get_response(update.message.text)
        
        if not response:
            await update.message.reply_text(
                "I couldn't understand that. Could you please rephrase your question?"
            )
            return

        # Handle multi-part responses
        if isinstance(response, list):
            for chunk in response:
                await update.message.reply_text(chunk)
                await asyncio.sleep(0.1)  # Small delay between messages
        else:
            await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        await update.message.reply_text(
            "I encountered an issue. Please try again."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the telegram bot."""
    try:
        error_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        if update:
            logger.error(f"[{error_time}] Update {update.update_id} caused error: {context.error}")
        else:
            logger.error(f"[{error_time}] Error occurred without update: {context.error}")
        
        if isinstance(context.error, (NetworkError, TimedOut, RetryAfter)):
            retry_after = getattr(context.error, 'retry_after', 1)
            logger.info(f"Network-related error, waiting {retry_after}s before retry...")
            await asyncio.sleep(retry_after)
        
        # Provide user feedback if possible
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "I encountered a temporary issue. Please try again in a moment."
            )
            
    except Exception as e:
        logger.error(f"Error in error handler: {str(e)}")

async def main() -> None:
    """Start the bot."""
    try:
        # Get the token from environment variable
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
            return

        # Create the Application with simplified configuration
        application = (
            Application.builder()
            .token(token)
            .connect_timeout(30)
            .read_timeout(30)
            .write_timeout(30)
            .build()
        )

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("trivia", telegram_trivia.start_game))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(telegram_trivia.handle_answer, pattern="^trivia_"))
        application.add_error_handler(error_handler)

        # Start the bot
        await application.initialize()
        await application.start()
        logger.info("Bot started successfully!")
        
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
        # Keep the bot running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Bot startup error: {str(e)}")
        raise
    finally:
        # Cleanup
        if 'application' in locals():
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            logger.info("Bot stopped")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {str(e)}")
        raise