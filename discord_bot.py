import os
import logging
import asyncio
import discord
from discord.ext import tasks, commands
from datetime import datetime, timezone
from chat_handler import ChatHandler
from discord_trivia import DiscordTrivia

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('discord_bot.log')
    ]
)
logger = logging.getLogger(__name__)

class OctantDiscordBot(commands.Bot):
    def __init__(self):
        """Initialize the bot with enhanced monitoring capabilities"""
        try:
            # Set up intents with enhanced permissions
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            intents.guilds = True
            intents.guild_messages = True
            intents.guild_reactions = True
            
            # Initialize the bot with required intents and command prefix
            super().__init__(
                command_prefix='/',
                intents=intents,
                heartbeat_timeout=60
            )

            # Initialize connection state tracking
            self.connection_state = {
                'connected': False,
                'last_heartbeat': None,
                'reconnect_count': 0,
                'last_reconnect_time': None,
                'connection_errors': [],
                'last_error': None,
                'guilds_count': 0,
                'health_check_failures': 0,
                'startup_time': datetime.now(timezone.utc),
                'last_recovery_action': None,
                'memory_usage': 0,
                'cpu_usage': 0
            }
            
            # Initialize recovery thresholds
            self.HEALTH_CHECK_INTERVAL = 30  # seconds
            self.MAX_HEALTH_CHECK_FAILURES = 3
            self.HEARTBEAT_TIMEOUT = 60  # seconds
            self.RECONNECT_BACKOFF_MAX = 300  # seconds
            
            self._setup_handlers()
            logger.info("Bot initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}", exc_info=True)
            raise

    def _setup_handlers(self):
        """Set up event handlers with proper error handling"""
        try:
            self.chat_handler = ChatHandler()
            self.trivia = DiscordTrivia()
            logger.info("Chat and Trivia handlers initialized successfully")
            
            # Remove default help command
            self.remove_command('help')
            
            # Register commands
            @self.command(name='trivia')
            async def trivia_command(ctx):
                """Start a trivia game"""
                try:
                    await self.trivia.start_game(ctx)
                except Exception as e:
                    logger.error(f"Error in trivia command: {str(e)}", exc_info=True)
                    await ctx.send("Sorry, there was an error starting the trivia game. Please try again.")

            @self.command(name='help')
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
                    
        except Exception as e:
            logger.error(f"Failed to initialize handlers: {str(e)}")
            raise

    async def start_health_monitor(self):
        """Start the health monitoring tasks"""
        self.health_check.start()
        self.connection_monitor.start()
        logger.info("Health monitoring tasks started")

    @tasks.loop(seconds=30)
    async def health_check(self):
        """Periodic health check task"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Check last heartbeat
            if self.connection_state['last_heartbeat']:
                heartbeat_age = (current_time - self.connection_state['last_heartbeat']).total_seconds()
                if heartbeat_age > self.HEARTBEAT_TIMEOUT:
                    logger.warning(f"Heartbeat timeout detected. Age: {heartbeat_age}s")
                    self.connection_state['health_check_failures'] += 1
                    await self._handle_health_failure("heartbeat_timeout")
            
            # Check connection status
            if not self.connection_state['connected']:
                logger.warning("Connection check failed - Bot disconnected")
                self.connection_state['health_check_failures'] += 1
                await self._handle_health_failure("disconnected")
            
            # Reset failure count if everything is fine
            if self.connection_state['connected'] and self.latency < 1.0:
                self.connection_state['health_check_failures'] = 0
                
        except Exception as e:
            logger.error(f"Error in health check: {str(e)}", exc_info=True)

    @tasks.loop(minutes=1)
    async def connection_monitor(self):
        """Monitor connection quality and guild status"""
        try:
            self.connection_state.update({
                'guilds_count': len(self.guilds),
                'latency': self.latency,
                'last_check_time': datetime.now(timezone.utc)
            })
            
            logger.info(f"""━━━━━━ Connection Status ━━━━━━
Connected: {self.connection_state['connected']}
Guilds: {self.connection_state['guilds_count']}
Latency: {self.latency * 1000:.2f}ms
Uptime: {(datetime.now(timezone.utc) - self.connection_state['startup_time']).total_seconds() / 3600:.1f}h
Health Failures: {self.connection_state['health_check_failures']}
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
        except Exception as e:
            logger.error(f"Error in connection monitor: {str(e)}", exc_info=True)

    async def _handle_health_failure(self, failure_type: str):
        """Handle health check failures with progressive recovery actions"""
        try:
            failures = self.connection_state['health_check_failures']
            logger.warning(f"Health check failure ({failure_type}). Failure count: {failures}")
            
            if failures >= self.MAX_HEALTH_CHECK_FAILURES:
                logger.critical("Critical health check failure - Initiating full restart")
                await self._emergency_restart()
            elif failures >= 2:
                logger.warning("Multiple health check failures - Attempting reconnection")
                await self.reconnect()
            else:
                logger.info("Single health check failure - Monitoring closely")
                
        except Exception as e:
            logger.error(f"Error handling health failure: {str(e)}", exc_info=True)

    async def _emergency_restart(self):
        """Perform emergency restart of the bot"""
        try:
            logger.critical("Initiating emergency restart sequence")
            
            # Log final state before restart
            logger.info(f"Final state before restart: {self.connection_state}")
            
            # Close existing connection
            try:
                await self.close()
            except:
                pass
            
            # Clear internal state
            self.clear()
            
            # Wait briefly before restart
            await asyncio.sleep(5)
            
            # Reinitialize connection
            await self.start(os.environ.get('DISCORD_BOT_TOKEN'))
            
            # Reset health check failures
            self.connection_state['health_check_failures'] = 0
            self.connection_state['last_recovery_action'] = datetime.now(timezone.utc)
            
            logger.info("Emergency restart completed successfully")
            
        except Exception as e:
            logger.critical(f"Failed to perform emergency restart: {str(e)}", exc_info=True)
            raise

    async def setup_hook(self):
        """Called when the bot is starting up"""
        await self.start_health_monitor()

    async def on_ready(self):
        """Called when the bot is ready."""
        try:
            logger.info(f"""━━━━━━ Bot Ready ━━━━━━
Logged in as: {self.user.name}
Bot ID: {self.user.id}
Guilds connected: {len(self.guilds)}
━━━━━━━━━━━━━━━━━━━━━━━━""")
            self.connection_state['connected'] = True
            self.connection_state['last_heartbeat'] = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error in on_ready: {str(e)}", exc_info=True)

    async def on_message(self, message):
        """Handle incoming messages with enhanced error handling."""
        try:
            if message.author == self.user:
                return

            await self.process_commands(message)

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

    async def on_error(self, event, *args, **kwargs):
        """Global error handler for all events"""
        try:
            error = sys.exc_info()[1]
            logger.error(f"Error in {event}: {str(error)}", exc_info=True)
            self.connection_state['last_error'] = {
                'event': event,
                'error': str(error),
                'timestamp': datetime.now(timezone.utc)
            }
        except Exception as e:
            logger.error(f"Error in error handler: {str(e)}", exc_info=True)

async def main():
    """Main bot execution with enhanced error handling and monitoring."""
    retry_count = 0
    max_retries = 5
    base_delay = 5

    while True:
        try:
            logger.info("Initializing Discord bot with enhanced monitoring")
            bot = OctantDiscordBot()
            
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
    asyncio.run(main())
