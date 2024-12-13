import os
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.error import (
    TelegramError,
    NetworkError,
    TimedOut
)
from chat_handler import ChatHandler

# Configure logging with more detailed format
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    level=logging.INFO,
    filename='telegram_bot.log'
)
logger = logging.getLogger(__name__)

# Initialize chat handler
chat_handler = ChatHandler()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    logger.info(f"Start command received from user {user.id}")
    await update.message.reply_text(
        f'Hello {user.first_name}! I am your AI chatbot. Feel free to ask me anything!'
    )

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check if the bot is functioning properly."""
    user = update.effective_user
    logger.info(f"Health check requested by user {user.id}")
    
    try:
        # Test the chat handler with a simple query
        success, _ = chat_handler.get_response("test")
        status = "🟢 Fully operational" if success else "🟡 Partially operational"
    except Exception:
        status = "🔴 Service degraded"
    
    await update.message.reply_text(f"Status: {status}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages with improved error handling."""
    if not update.message or not update.message.text:
        logger.warning("Received update without message or text")
        return

    user = update.effective_user
    message_text = update.message.text.strip()
    
    if not message_text:
        logger.warning(f"Empty message received from user {user.id}")
        return

    logger.info(f"Processing message from user {user.id}: {message_text[:50]}...")
    
    try:
        # Get response from chat handler
        success, response = chat_handler.get_response(message_text)
        
        if not success:
            logger.error(f"Failed to get response for user {user.id}")
            await update.message.reply_text(
                "I apologize, but I'm having trouble processing your message right now. "
                "Please try again in a moment."
            )
            return
        
        # Send response back to user
        await update.message.reply_text(response)
        logger.info(f"Successfully sent response to user {user.id}")
        
    except NetworkError as e:
        logger.error(f"Network error while processing message: {str(e)}")
        await update.message.reply_text(
            "I'm having connectivity issues. Please try again in a moment."
        )
    except TimedOut as e:
        logger.error(f"Request timed out: {str(e)}")
        await update.message.reply_text(
            "The request took too long to process. Please try again."
        )
    except TelegramError as e:
        logger.error(f"Telegram API error: {str(e)}")
        await update.message.reply_text(
            "I encountered an error while sending the message. Please try again."
        )
    except Exception as e:
        logger.error(f"Unexpected error processing message: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "I encountered an unexpected error. Please try again."
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the telegram-bot-python library."""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
    
    try:
        if isinstance(update, Update) and update.message:
            await update.message.reply_text(
                "I encountered an error while processing your request. Please try again later."
            )
    except Exception as e:
        logger.error(f"Error while sending error message: {str(e)}")

def main() -> None:
    """Start the bot with improved error handling and monitoring."""
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
            return

        # Create application with persistent storage
        application = Application.builder().token(token).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("health", health))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Add error handler
        application.add_error_handler(error_handler)

        # Start polling with improved settings
        logger.info("Starting bot...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            pool_timeout=30,
            read_timeout=30,
            write_timeout=30
        )

    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}", exc_info=True)

if __name__ == '__main__':
    main()
