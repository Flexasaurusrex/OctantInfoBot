import os
import logging
import discord
from discord.ext import commands
from discord_trivia import DiscordTrivia
from chat_handler import ChatHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class OctantDiscordBot(commands.Bot):
    def __init__(self):
        try:
            # Initialize connection state tracking
            self.connection_state = {
                'connected': False,
                'reconnect_count': 0,
                'last_heartbeat': None,
                'last_error': None
            }
            
            # Set up intents
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            
            # Initialize the bot with required intents
            super().__init__(
                command_prefix='/',
                intents=intents,
                heartbeat_timeout=60,
                activity=discord.Game(name="Octant Trivia | /help")
            )
            
            self._setup_handlers()
            logger.info("Bot initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}", exc_info=True)
            raise

    async def on_ready(self):
        """Called when the bot is ready."""
        try:
            logger.info(f"""━━━━━━ Bot Ready ━━━━━━
Logged in as: {self.user.name}
Bot ID: {self.user.id}
Guilds connected: {len(self.guilds)}
━━━━━━━━━━━━━━━━━━━━━━━━""")
            self.connection_state['connected'] = True
            
        except Exception as e:
            logger.error(f"Error in on_ready: {str(e)}", exc_info=True)

    async def on_connect(self):
        """Handle successful connection"""
        try:
            self.connection_state['connected'] = True
            self.connection_state['last_heartbeat'] = discord.utils.utcnow()
            logger.info("━━━━━━ Bot Connected ━━━━━━")
            logger.info(f"Connected as: {self.user.name}")
            logger.info(f"Bot ID: {self.user.id}")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━")
            
        except Exception as e:
            logger.error(f"Error in on_connect: {str(e)}", exc_info=True)

    async def on_disconnect(self):
        """Handle disconnection"""
        try:
            self.connection_state['connected'] = False
            logger.warning("Bot disconnected - Attempting to reconnect...")
            self.connection_state['reconnect_count'] += 1
            
        except Exception as e:
            logger.error(f"Error in on_disconnect: {str(e)}", exc_info=True)

    async def on_error(self, event, *args, **kwargs):
        """Handle errors in event handlers"""
        try:
            error = args[0] if args else "Unknown error"
            self.connection_state['last_error'] = str(error)
            logger.error(f"""━━━━━━ Event Error ━━━━━━
Event: {event}
Error: {str(error)}
Args: {args}
Reconnect Count: {self.connection_state['reconnect_count']}
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
        except Exception as e:
            logger.error(f"Error in error handler: {str(e)}", exc_info=True)

    def _setup_handlers(self):
        """Set up event handlers with proper error handling"""
        try:
            self.chat_handler = ChatHandler()
            self.trivia = DiscordTrivia()
            logger.info("Chat and Trivia handlers initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize handlers: {str(e)}")
            raise

    async def on_message(self, message):
        """Handle incoming messages with enhanced error handling."""
        try:
            if message.author == self.user:
                return

            logger.info(f"""━━━━━━ Message Received ━━━━━━
Content: {message.content}
Author: {message.author.name}
Channel: {message.channel.name}
Is Command: {message.content.startswith(self.command_prefix)}
━━━━━━━━━━━━━━━━━━━━━━━━""")

            # Process commands first
            if message.content.startswith(self.command_prefix):
                await self.process_commands(message)
                return

            # Check if message is a reply to bot
            is_reply_to_bot = bool(
                message.reference 
                and message.reference.resolved 
                and message.reference.resolved.author.id == self.user.id
            )

            if not is_reply_to_bot:
                return

            # Get and send response
            response = self.chat_handler.get_response(message.content)
            if response:
                if isinstance(response, list):
                    for chunk in response:
                        if chunk and chunk.strip():
                            await message.reply(chunk.strip(), mention_author=True)
                else:
                    await message.reply(response.strip(), mention_author=True)

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            await message.channel.send("I encountered an error processing your message. Please try again.")

    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions with error handling."""
        try:
            if interaction.type == discord.InteractionType.component:
                custom_id = interaction.data.get("custom_id", "")
                if custom_id.startswith("trivia_"):
                    await self.trivia.handle_answer(interaction, custom_id.split("_")[1])
                    
        except Exception as e:
            logger.error(f"Error handling interaction: {str(e)}", exc_info=True)
            try:
                await interaction.response.send_message(
                    "Sorry, there was an error processing your interaction. Please try again.",
                    ephemeral=True
                )
            except:
                pass

async def main():
    """Main bot execution with enhanced error handling and reconnection logic."""
    retry_count = 0
    max_retries = 5
    base_delay = 5

    while True:
        try:
            bot = OctantDiscordBot()
            
            # Remove default help command
            bot.remove_command('help')
            
            # Add commands
            @bot.command(name='trivia')
            async def trivia_command(ctx):
                """Start a trivia game"""
                try:
                    await bot.trivia.start_game(ctx)
                except Exception as e:
                    logger.error(f"Error in trivia command: {str(e)}", exc_info=True)
                    await ctx.send("Sorry, there was an error starting the trivia game. Please try again.")

            @bot.command(name='help')
            async def help_command(ctx):
                """Show help message"""
                help_embed = discord.Embed(
                    title="📚 Octant Bot Help",
                    description="Welcome to Octant Bot! Here are the available commands:",
                    color=discord.Color.blue()
                )
                
                help_embed.add_field(
                    name="🎮 Game Commands",
                    value="• `/trivia` - Start a trivia game about Octant",
                    inline=False
                )
                
                help_embed.add_field(
                    name="💬 Chat Features",
                    value="• Reply to any of my messages to chat\n• Ask questions about Octant\n• Get help with Octant features",
                    inline=False
                )
                
                help_embed.set_footer(text="Type /trivia to start playing!")
                
                try:
                    await ctx.send(embed=help_embed)
                except Exception as e:
                    logger.error(f"Error sending help message: {str(e)}", exc_info=True)
                    await ctx.send("Sorry, there was an error displaying the help message. Please try again.")

            # Get Discord token
            discord_token = os.environ.get('DISCORD_BOT_TOKEN')
            if not discord_token:
                raise ValueError("DISCORD_BOT_TOKEN environment variable is required")

            # Start the bot
            await bot.start(discord_token)
            
        except Exception as e:
            retry_count += 1
            delay = min(base_delay * (2 ** (retry_count - 1)), 300)  # Max 5 minutes delay
            
            logger.error(f"""━━━━━━ Bot Error ━━━━━━
Error: {str(e)}
Retry Count: {retry_count}
Next Retry: {delay}s
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
            if retry_count >= max_retries:
                logger.error("Maximum retries reached, exiting...")
                break
                
            await asyncio.sleep(delay)
            continue

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())