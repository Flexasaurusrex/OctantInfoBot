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
            # Enhanced connection state tracking
            self.connection_state = {
                'connected': False,
                'reconnect_count': 0,
                'last_heartbeat': None,
                'last_error': None,
                'heartbeat_interval': 0,
                'latency': 0.0,
                'session_id': None,
                'last_reconnect_time': None,
                'connection_errors': []
            }
            
            # Set up intents with enhanced permissions
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            intents.guilds = True
            intents.guild_messages = True
            intents.guild_reactions = True
            
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
        """Handle successful connection with enhanced state tracking"""
        try:
            current_time = discord.utils.utcnow()
            self.connection_state.update({
                'connected': True,
                'last_heartbeat': current_time,
                'last_reconnect_time': current_time if self.connection_state['reconnect_count'] > 0 else None,
                'session_id': self.ws.session_id if hasattr(self, 'ws') else None,
                'latency': self.latency
            })
            
            logger.info("""━━━━━━ Bot Connected ━━━━━━
Connection Details:
- Name: {0}
- ID: {1}
- Latency: {2:.2f}ms
- Session ID: {3}
- Reconnect Count: {4}
━━━━━━━━━━━━━━━━━━━━━━━━""".format(
                self.user.name,
                self.user.id,
                self.latency * 1000,
                self.connection_state['session_id'],
                self.connection_state['reconnect_count']
            ))
            
        except Exception as e:
            logger.error(f"Error in on_connect: {str(e)}", exc_info=True)
            self.connection_state['connection_errors'].append({
                'time': discord.utils.utcnow(),
                'error': str(e),
                'type': 'connect'
            })

    async def on_disconnect(self):
        """Handle disconnection with enhanced reconnection logic and state recovery"""
        try:
            self.connection_state['connected'] = False
            self.connection_state['reconnect_count'] += 1
            current_time = discord.utils.utcnow()
            
            # Calculate time since last reconnect with enhanced tracking
            last_reconnect = self.connection_state['last_reconnect_time']
            time_since_reconnect = (current_time - last_reconnect).total_seconds() if last_reconnect else float('inf')
            
            # Progressive reconnection strategy with state preservation
            max_reconnect_attempts = 5
            backoff_factor = min(2 ** (self.connection_state['reconnect_count'] - 1), 300)  # Max 5 minutes
            
            # Enhanced state tracking
            self.connection_state.update({
                'last_disconnect_time': current_time,
                'disconnect_reason': getattr(self.ws, 'close_code', None),
                'last_sequence': getattr(self.ws, 'sequence', None),
                'resume_gateway_url': getattr(self.ws, 'resume_gateway_url', None)
            })
            
            logger.warning("""━━━━━━ Bot Disconnected ━━━━━━
Reconnection Status:
- Attempt: {0}/{1}
- Time Since Last Reconnect: {2:.1f}s
- Last Session ID: {3}
- Next Retry Delay: {4}s
- Last Known Latency: {5:.2f}ms
━━━━━━━━━━━━━━━━━━━━━━━━""".format(
                self.connection_state['reconnect_count'],
                max_reconnect_attempts,
                time_since_reconnect,
                self.connection_state['session_id'],
                backoff_factor,
                self.latency * 1000 if self.latency else 0
            ))
            
            # Check if we should attempt reconnection
            if self.connection_state['reconnect_count'] <= max_reconnect_attempts:
                try:
                    # Clear any existing error states
                    self.clear()
                    
                    # Wait before reconnecting with exponential backoff
                    await asyncio.sleep(backoff_factor)
                    
                    # Attempt to reconnect
                    await self.connect(reconnect=True)
                    
                except Exception as reconnect_error:
                    logger.error(f"Failed to reconnect: {str(reconnect_error)}", exc_info=True)
                    self.connection_state['connection_errors'].append({
                        'time': discord.utils.utcnow(),
                        'error': str(reconnect_error),
                        'type': 'reconnect_attempt'
                    })
            else:
                logger.critical("Maximum reconnection attempts reached. Manual intervention required.")
                # You might want to implement additional recovery mechanisms here
                
        except Exception as e:
            logger.error(f"Error in on_disconnect: {str(e)}", exc_info=True)
            self.connection_state['connection_errors'].append({
                'time': discord.utils.utcnow(),
                'error': str(e),
                'type': 'disconnect'
            })
            
            # Attempt to clean up and recover
            try:
                await self.close()
            except:
                pass

    async def on_error(self, event, *args, **kwargs):
        """Handle errors in event handlers with enhanced recovery"""
        try:
            error = args[0] if args else "Unknown error"
            self.connection_state['last_error'] = str(error)
            
            # Enhanced error classification
            if isinstance(error, discord.errors.HTTPException):
                if error.status == 429:  # Rate limit error
                    retry_after = error.retry_after
                    logger.warning(f"Rate limit hit, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    return
                
            if isinstance(error, (discord.errors.GatewayNotFound, discord.errors.ConnectionClosed)):
                logger.error("Gateway connection error - attempting recovery")
                await self.close()
                await self.connect(reconnect=True)
                return
                
            logger.error(f"""━━━━━━ Event Error ━━━━━━
Event: {event}
Error Type: {type(error).__name__}
Error: {str(error)}
Args: {args}
Reconnect Count: {self.connection_state['reconnect_count']}
Session ID: {self.connection_state.get('session_id')}
Last Known State: {self.connection_state.get('connected', False)}
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
            # Implement progressive backoff for general errors
            backoff = min(300, (2 ** self.connection_state['reconnect_count']))
            logger.info(f"Implementing backoff of {backoff} seconds")
            await asyncio.sleep(backoff)
            
        except Exception as e:
            logger.error(f"Critical error in error handler: {str(e)}", exc_info=True)
            # Attempt to recover from critical errors
            try:
                await self.close()
                await asyncio.sleep(5)
                await self.connect(reconnect=True)
            except:
                logger.critical("Failed to recover from critical error")

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