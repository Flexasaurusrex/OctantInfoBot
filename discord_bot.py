import discord
from discord.ext import commands
import os
import logging
from chat_handler import ChatHandler
from discord_trivia import DiscordTrivia

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]'
)
logger = logging.getLogger(__name__)

class OctantDiscordBot(commands.Bot):
    def __init__(self):
        logger.info("Initializing OctantDiscordBot...")
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        
        super().__init__(command_prefix='/', intents=intents)
        
        try:
            logger.info("Initializing ChatHandler...")
            self.chat_handler = ChatHandler()
            logger.info("ChatHandler initialized successfully")
            
            logger.info("Initializing DiscordTrivia...")
            self.trivia = DiscordTrivia()
            logger.info("DiscordTrivia initialized successfully")
            
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}", exc_info=True)
            raise

    async def setup_hook(self):
        """Set up the bot's commands."""
        logger.info("Setting up bot commands...")
        
        @self.command(name='trivia')
        async def trivia_command(ctx):
            """Start a trivia game"""
            await self.trivia.start_game(ctx)

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'Bot is ready! Logged in as {self.user} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds')
        for guild in self.guilds:
            logger.info(f'Connected to guild: {guild.name} (ID: {guild.id})')

    async def on_message(self, message):
        """Handle incoming messages."""
        try:
            # Log every message except our own
            if message.author != self.user:
                logger.info(f"""
━━━━━━ Message Received ━━━━━━
From: {message.author} (ID: {message.author.id})
Content: {message.content[:100]}{'...' if len(message.content) > 100 else ''}
Channel: {message.channel.name} (ID: {message.channel.id})
Bot Mentioned: {self.user.mentioned_in(message)}
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
            # Ignore our own messages
            if message.author == self.user:
                return

            # Check if bot is mentioned
            if self.user.mentioned_in(message):
                logger.info("Bot was mentioned - preparing response...")
                
                # Clean the message content (remove mentions)
                content = message.content
                for mention in message.mentions:
                    content = content.replace(f'<@{mention.id}>', '').replace(f'<@!{mention.id}>', '')
                content = content.strip()
                
                # If no content after removing mentions, use default question
                if not content:
                    content = "What is Octant?"
                    logger.info("Using default question: 'What is Octant?'")
                
                try:
                    # Get response from chat handler
                    logger.info(f"Getting response for: {content}")
                    response = self.chat_handler.get_response(content)
                    
                    if response:
                        # Split response if it's too long
                        if len(str(response)) > 2000:
                            chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
                            logger.info(f"Splitting response into {len(chunks)} chunks")
                            for chunk in chunks:
                                await message.reply(chunk.strip())
                        else:
                            await message.reply(response)
                        logger.info("Response sent successfully")
                    else:
                        default_response = "I'm here to help you learn about Octant! What would you like to know?"
                        await message.reply(default_response)
                        logger.info("Sent default response due to empty chat handler response")
                        
                except Exception as e:
                    logger.error(f"Error getting/sending response: {str(e)}", exc_info=True)
                    await message.reply("I encountered an issue while processing your request. Please try again.")
            
            # Process commands if any
            await self.process_commands(message)
            
        except Exception as e:
            logger.error(f"Error in message handler: {str(e)}", exc_info=True)
            try:
                await message.reply("I encountered an unexpected error. Please try again.")
            except:
                pass

    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions for trivia."""
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("trivia_"):
                answer = custom_id.split("_")[1]
                await self.trivia.handle_answer(interaction, answer)

async def main():
    """Start the bot with error handling."""
    try:
        logger.info("Starting Discord bot...")
        bot = OctantDiscordBot()
        
        discord_token = os.environ.get('DISCORD_BOT_TOKEN')
        if not discord_token:
            logger.error("DISCORD_BOT_TOKEN not found in environment variables")
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
        
        await bot.start(discord_token)
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
