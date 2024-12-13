import discord
from discord.ext import commands
import os
import logging
from chat_handler import ChatHandler
from discord_trivia import DiscordTrivia

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OctantDiscordBot(commands.Bot):
    def __init__(self):
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        
        super().__init__(command_prefix='/', intents=intents)
        
        try:
            # Initialize chat handler with verification
            logger.info("Initializing ChatHandler...")
            self.chat_handler = ChatHandler()
            
            # Test chat handler with a simple query
            logger.info("Testing ChatHandler...")
            test_response = self.chat_handler.get_response("What is Octant?")
            
            # Verify the response is valid
            if not test_response:
                logger.error("ChatHandler test failed - empty response")
                raise ValueError("ChatHandler test failed - empty response")
                
            logger.info(f"ChatHandler test response received:\n{test_response[:100]}...")
            logger.info("ChatHandler initialized and verified")
            
            # Initialize trivia handler
            logger.info("Initializing DiscordTrivia...")
            self.trivia = DiscordTrivia()
            logger.info("DiscordTrivia initialized successfully")
            
            logger.info("Bot initialized successfully with all handlers")
            
        except Exception as e:
            logger.error(f"Critical initialization error: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to initialize bot: {str(e)}")

    async def setup_hook(self):
        """Set up the bot's internal cache and add commands."""
        logger.info("Bot is setting up...")
        
        @self.command(name='trivia')
        async def trivia_command(ctx):
            """Start a trivia game"""
            await self.trivia.start_game(ctx)

    async def on_ready(self):
        """Log when the bot is ready."""
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

    async def on_message(self, message):
        """Handle incoming messages."""
        # Ignore own messages
        if message.author == self.user:
            return

        logger.info(f"Received message from {message.author}: {message.content}")

        # Process commands first (for /help, /trivia etc)
        await self.process_commands(message)
        
        # Enhanced logging for message debugging
        logger.info(f"Processing message - Author: {message.author}, Content: {message.content}, Mentions: {message.mentions}")
        
        # Check for bot mention more thoroughly
        is_mentioned = any([
            self.user.mentioned_in(message),  # Standard mention check
            isinstance(message.channel, discord.DMChannel),  # DM check
            f'<@{self.user.id}>' in message.content,  # Raw mention ID check
            f'<@!{self.user.id}>' in message.content  # Nickname mention check
        ])
        
        if is_mentioned:
            logger.info(f"Bot was mentioned by {message.author}")
            
            try:
                # Clean the message content
                content = message.content.strip()
                # Remove all possible forms of bot mentions
                content = content.replace(f'<@{self.user.id}>', '')
                content = content.replace(f'<@!{self.user.id}>', '')
                content = content.replace(self.user.mention, '')
                content = content.strip()
                
                # Use default prompt if empty
                if not content:
                    content = "What is Octant?"
                    logger.info("Using default prompt: What is Octant?")
                
                logger.info(f"Processing query: {content}")
                
                # Get response from chat handler with enhanced error handling
                try:
                    logger.info("Requesting response from chat handler...")
                    response = self.chat_handler.get_response(content)
                    logger.info(f"Received response type: {type(response)}, length: {len(str(response)) if response else 0}")
                    
                    # Handle empty or invalid response
                    if not response:
                        response = "I'm here to help you learn about Octant! What would you like to know?"
                        logger.warning("Using default response due to empty chat handler response")
                    
                    # Send response with improved chunking
                    if isinstance(response, list):
                        logger.info(f"Processing list response with {len(response)} chunks")
                        for i, chunk in enumerate(response, 1):
                            if chunk and chunk.strip():
                                await message.reply(chunk.strip())
                                logger.info(f"Sent chunk {i}/{len(response)}")
                    else:
                        # Split long responses if needed
                        if len(str(response)) > 2000:  # Discord's message length limit
                            chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
                            logger.info(f"Splitting long response into {len(chunks)} chunks")
                            for i, chunk in enumerate(chunks, 1):
                                await message.reply(chunk.strip())
                                logger.info(f"Sent split chunk {i}/{len(chunks)}")
                        else:
                            await message.reply(response)
                            logger.info("Sent complete response")
                    
                    logger.info("Response handling completed successfully")
                    
                except Exception as chat_error:
                    logger.error(f"Error getting/sending response: {str(chat_error)}", exc_info=True)
                    await message.reply("I encountered an issue while processing your request. Please try again.")
                
            except Exception as e:
                logger.error(f"Error handling message: {str(e)}", exc_info=True)
                await message.reply("I apologize, but I encountered an error. Please try asking your question again.")

    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions for trivia."""
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("trivia_"):
                answer = custom_id.split("_")[1]
                await self.trivia.handle_answer(interaction, answer)

async def main():
    """Start the bot."""
    bot = OctantDiscordBot()
    
    discord_token = os.environ.get('DISCORD_BOT_TOKEN')
    if not discord_token:
        logger.error("DISCORD_BOT_TOKEN not found in environment variables")
        raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
    
    try:
        await bot.start(discord_token)
    except discord.LoginFailure:
        logger.error("Failed to login to Discord. Please check your token.")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())