import os
import discord
from discord.ext import commands
from chat_handler import ChatHandler
from discord_trivia import DiscordTrivia
import logging
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OctantDiscordBot(commands.Bot):
    def __init__(self):
        try:
            # Set up intents
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            intents.presences = True
            logger.info("Setting up bot with privileged intents...")
            
            # Initialize the bot with intents
            super().__init__(
                command_prefix='/', 
                intents=intents,
                help_command=None
            )
            
            # Initialize handlers
            self._setup_handlers()
            logger.info("Bot initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot with intents: {str(e)}")
            raise
            
    def _setup_handlers(self):
        """Set up event handlers with proper error handling"""
        try:
            self.chat_handler = ChatHandler()
            self.trivia = DiscordTrivia()
            logger.info("Chat and Trivia handlers initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize handlers: {str(e)}")
            raise

    async def setup_hook(self):
        """Setup hook for the bot."""
        logger.info("Bot is setting up...")

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info('------')

    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions."""
        try:
            if interaction.type == discord.InteractionType.component:
                custom_id = interaction.data.get("custom_id", "")
                if custom_id.startswith("trivia_"):
                    # Let the view handle the interaction
                    await interaction.message.view.handle_interaction(interaction)
        except Exception as e:
            logger.error(f"Error in interaction handler: {str(e)}")
            await interaction.response.send_message(
                "An error occurred processing your response. Please try again.",
                ephemeral=True
            )

    async def on_message(self, message):
        """Handle incoming messages."""
        logger.info(f"""
━━━━━━ Message Received ━━━━━━
Content: {message.content}
Author: {message.author.name} (ID: {message.author.id})
Channel: {message.channel.name}
Is Bot: {message.author.bot}
Has Mention: {self.user.mentioned_in(message)}
Is DM: {isinstance(message.channel, discord.DMChannel)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")
        
        # Ignore messages from the bot itself
        if message.author == self.user:
            logger.info("Message is from bot itself, ignoring")
            return
            
        try:
            # Process commands first (these start with /)
            if message.content.startswith(self.command_prefix):
                logger.info(f"Processing command: {message.content}")
                await self.process_commands(message)
                return

            # Check if message is a reply to bot
            is_reply_to_bot = bool(
                message.reference 
                and message.reference.resolved 
                and message.reference.resolved.author.id == self.user.id
            )
            logger.info(f"Is reply to bot: {is_reply_to_bot}")
            
            # Only process replies to bot messages
            if not is_reply_to_bot:
                logger.info("Message is not a reply to bot, ignoring")
                return
                
            logger.info("━━━━━━ Bot Interaction ━━━━━━")
            logger.info(f"Interaction Type: {'Reply' if is_reply_to_bot else 'Mention'}")
            logger.info(f"Raw Message: {message.content}")
            logger.info(f"Author: {message.author.name} (ID: {message.author.id})")
            logger.info(f"Channel: {message.channel.name} (ID: {message.channel.id})")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                
            # Enhanced message content extraction and cleaning
            try:
                # Get the message content
                content = message.content.strip()
                    
                # Remove all possible mention patterns
                mention_patterns = [
                    f'<@{self.user.id}>',        # Standard mention
                    f'<@!{self.user.id}>',       # Nickname mention
                    f'@{self.user.display_name}', # Display name mention
                    self.user.name,              # Bot name
                ]
                    
                for pattern in mention_patterns:
                    content = content.replace(pattern, '').strip()
                    
                # Process message if not empty
                if content.strip():
                    try:
                        response = self.chat_handler.get_response(content)
                        if not response:
                            await message.reply("I couldn't generate a response. Please try again.", mention_author=True)
                            return
                            
                        # Send only one focused response
                        async def send_chunk(chunk_text, is_last=False):
                            """Helper function to send a chunk of text"""
                            try:
                                if chunk_text.strip():
                                    # Filter out self-introductions and generic responses
                                    if not any(chunk_text.lower().startswith(intro) for intro in [
                                        "i am", "hello", "hi", "hey", "greetings", "as an ai",
                                        "i'm a", "i'm an", "i can", "i will", "let me"
                                    ]):
                                        # Only send substantive responses
                                        await message.reply(chunk_text.strip(), mention_author=True)
                                        if not is_last:
                                            await asyncio.sleep(0.5)  # Rate limiting prevention
                            except discord.errors.HTTPException as he:
                                logger.error(f"Discord HTTP error while sending chunk: {str(he)}")
                                return False
                            except Exception as e:
                                logger.error(f"Error sending chunk: {str(e)}")
                                return False
                            return True

                        try:
                            # Convert response to list if it's a string
                            responses = response if isinstance(response, list) else [response]
                            
                            for resp in responses:
                                if not resp or not resp.strip():
                                    continue
                                    
                                # Enhanced chunking logic that respects word boundaries
                                current_chunk = ""
                                words = resp.split()
                                chunks_sent = 0
                                
                                for i, word in enumerate(words):
                                    # Check if adding the next word would exceed limit
                                    if len(current_chunk) + len(word) + 1 > 1900:
                                        # Send current chunk if it's not empty
                                        if current_chunk.strip():
                                            success = await send_chunk(current_chunk)
                                            if success:
                                                chunks_sent += 1
                                            if chunks_sent >= 5:  # Limit number of chunks
                                                await message.reply("Message was too long. I've sent the first part.", mention_author=True)
                                                break
                                        current_chunk = word
                                    else:
                                        # Add word to current chunk
                                        current_chunk = f"{current_chunk} {word}" if current_chunk else word
                                
                                # Send the last chunk if there's anything left
                                if current_chunk.strip() and chunks_sent < 5:
                                    await send_chunk(current_chunk, is_last=True)
                        except Exception as chunk_error:
                            logger.error(f"Error in chunk processing: {str(chunk_error)}")
                            await message.reply("I encountered an error while sending the response. Please try a shorter query.", mention_author=True)
                    except Exception as resp_error:
                        logger.error(f"Error getting response: {str(resp_error)}")
                        await message.reply("I encountered an error processing your message. Please try again with a simpler query.", mention_author=True)
                else:
                    # If no content after cleaning, provide a helpful response
                    await message.reply("Hi! How can I help you today?", mention_author=True)
                        
            except Exception as e:
                logger.error(f"Error processing message content: {str(e)}")
                await message.reply("I encountered an error processing your message. Please try again.", mention_author=True)
            
        except Exception as e:
            logger.error(f"Error in message handler: {str(e)}")
            await message.channel.send("I encountered an error processing your message. Please try again.")


async def main():
    try:
        # Create bot instance
        bot = OctantDiscordBot()
        logger.info("━━━━━━ Bot Instance Created ━━━━━━")
        
        # Add commands
        @bot.command(name='trivia')
        async def trivia_command(ctx):
            """Start a trivia game"""
            try:
                logger.info(f"Starting trivia game for {ctx.author.name} in {ctx.channel.name}")
                
                # Check permissions
                if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
                    await ctx.send("I need permission to send messages in this channel!")
                    return
                    
                if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
                    await ctx.send("I need permission to send embeds in this channel!")
                    return

                # Start the game
                await bot.trivia.start_game(ctx)
                    
            except Exception as e:
                logger.error(f"Error in trivia command: {str(e)}")
                await ctx.send("An error occurred while starting the game. Please try again.")

        @bot.command(name='help')
        async def help_command(ctx):
            """Show help message"""
            help_text = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Available Commands
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎮 Game Commands:
• /trivia - Start a trivia game

📋 Information Commands:
• /help - Show this help message

Type /trivia to start playing!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
            await ctx.send(help_text)
            
        # Get Discord token
        discord_token = os.environ.get('DISCORD_BOT_TOKEN')
        if not discord_token:
            logger.error("DISCORD_BOT_TOKEN not found in environment variables")
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
            
        # Start the bot
        try:
            await bot.start(discord_token)
        except discord.LoginFailure:
            logger.error("Failed to login to Discord. Please check your token.")
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            
    except Exception as e:
        logger.error(f"Critical error in main: {str(e)}")
        raise
        
if __name__ == "__main__":
    asyncio.run(main())