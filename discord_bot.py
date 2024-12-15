import os
import sys
import random
import logging
import asyncio
import discord
from discord.ext import tasks, commands
from datetime import datetime, timezone
import psutil
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

            # Initialize connection state tracking with enhanced monitoring
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
                'cpu_usage': 0,
                'last_message_time': None,
                'consecutive_timeouts': 0,
                'latency_history': [],
                'error_count': 0
            }
            
            # Optimized recovery thresholds for better stability
            self.HEALTH_CHECK_INTERVAL = 30    # Increased interval for less aggressive checking
            self.MAX_HEALTH_CHECK_FAILURES = 8  # More failures allowed before recovery
            self.HEARTBEAT_TIMEOUT = 120       # Much more lenient heartbeat timeout (2 minutes)
            self.RECONNECT_BACKOFF_MAX = 300   # Increased max backoff for better stability (5 minutes)
            self.MAX_LATENCY = 5000            # More lenient latency threshold (5000ms)
            self.MAX_CONSECUTIVE_TIMEOUTS = 8   # More lenient timeout trigger
            self.MEMORY_THRESHOLD = 98         # Very lenient memory threshold
            self.CPU_THRESHOLD = 95            # Very lenient CPU threshold
            self.IMMEDIATE_RESTART_THRESHOLD = 10  # More attempts before immediate restart
            
            # Initialize latency tracking
            self.latency_samples = []
            self.MAX_LATENCY_SAMPLES = 10
            
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

            @self.command(name='ping')
            async def ping_command(ctx):
                """Check bot's latency"""
                try:
                    latency = round(self.latency * 1000)  # Convert to ms
                    embed = discord.Embed(
                        title="🏓 Pong!",
                        description=f"Latency: {latency}ms",
                        color=discord.Color.green() if latency < 200 else discord.Color.orange()
                    )
                    await ctx.send(embed=embed)
                except Exception as e:
                    logger.error(f"Error in ping command: {str(e)}", exc_info=True)
                    await ctx.send("Sorry, there was an error checking latency. Please try again.")

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
                    name="🛠️ Utility Commands",
                    value="• `/ping` - Check bot's response time\n• `/help` - Show this help message",
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

    @tasks.loop(seconds=15)  # Reduced frequency for better stability
    async def health_check(self):
        """Enhanced periodic health check task with comprehensive monitoring"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Update system metrics
            import psutil
            process = psutil.Process()
            self.connection_state['memory_usage'] = process.memory_percent()
            self.connection_state['cpu_usage'] = process.cpu_percent()
            
            # Check memory and CPU thresholds
            if self.connection_state['memory_usage'] > self.MEMORY_THRESHOLD:
                logger.warning(f"High memory usage: {self.connection_state['memory_usage']}%")
                if self.connection_state['memory_usage'] > self.MEMORY_THRESHOLD + 10:
                    logger.critical("Critical memory usage - Initiating immediate restart")
                    await self._emergency_restart(force=True)
                else:
                    await self._handle_health_failure("high_memory")
            
            if self.connection_state['cpu_usage'] > self.CPU_THRESHOLD:
                logger.warning(f"High CPU usage: {self.connection_state['cpu_usage']}%")
                await self._handle_health_failure("high_cpu")
            
            # Enhanced heartbeat monitoring
            if self.connection_state['last_heartbeat']:
                heartbeat_age = (current_time - self.connection_state['last_heartbeat']).total_seconds()
                if heartbeat_age > self.HEARTBEAT_TIMEOUT:
                    logger.warning(f"Heartbeat timeout detected. Age: {heartbeat_age}s")
                    self.connection_state['consecutive_timeouts'] += 1
                    self.connection_state['health_check_failures'] += 1
                    await self._handle_health_failure("heartbeat_timeout")
                    
                    if self.connection_state['consecutive_timeouts'] >= self.MAX_CONSECUTIVE_TIMEOUTS:
                        logger.critical("Maximum consecutive timeouts reached - Forcing restart")
                        await self._emergency_restart()
                else:
                    self.connection_state['consecutive_timeouts'] = 0
            
            # Latency monitoring
            if self.latency != float('inf'):
                self.connection_state['latency_history'].append(self.latency * 1000)  # Convert to ms
                if len(self.connection_state['latency_history']) > 10:
                    self.connection_state['latency_history'].pop(0)
                
                avg_latency = sum(self.connection_state['latency_history']) / len(self.connection_state['latency_history'])
                if avg_latency > self.MAX_LATENCY:
                    logger.warning(f"High latency detected: {avg_latency}ms")
                    await self._handle_health_failure("high_latency")
            
            # Connection status check
            if not self.connection_state['connected']:
                logger.warning("Connection check failed - Bot disconnected")
                self.connection_state['health_check_failures'] += 1
                await self._handle_health_failure("disconnected")
            
            # Reset failure count if everything is fine
            if (self.connection_state['connected'] and 
                self.latency < self.MAX_LATENCY/1000 and 
                self.connection_state['consecutive_timeouts'] == 0):
                self.connection_state['health_check_failures'] = 0
                logger.info("Health check passed - All systems normal")
                
        except Exception as e:
            logger.error(f"Error in health check: {str(e)}", exc_info=True)
            self.connection_state['error_count'] += 1
            if (self.connection_state['error_count'] > 5 or 
                self.connection_state['consecutive_timeouts'] >= self.MAX_CONSECUTIVE_TIMEOUTS or
                self.connection_state['health_check_failures'] >= self.IMMEDIATE_RESTART_THRESHOLD):
                logger.critical("Critical condition detected - Initiating immediate restart")
                await self._emergency_restart(force=True)  # Force immediate restart

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
                logger.critical(f"""
━━━━━━ Critical Health Check Failure ━━━━━━
Failure Count: {failures}
Last Error: {self.connection_state.get('last_error')}
Connection State: {self.connection_state['connected']}
Latency: {self.latency * 1000:.2f}ms
Memory Usage: {self.connection_state['memory_usage']:.1f}%
CPU Usage: {self.connection_state['cpu_usage']:.1f}%
━━━━━━━━━━━━━━━━━━━━━━━━""")
                
                # Try reconnection first
                try:
                    logger.warning("Attempting reconnection before emergency restart...")
                    # Close existing connection
                    await self.close()
                    await asyncio.sleep(5)  # Wait before reconnecting
                    
                    # Attempt to reconnect
                    await self.start(os.environ.get('DISCORD_BOT_TOKEN'))
                    await asyncio.sleep(5)  # Wait for reconnection
                    
                    if self.is_ready() and self.latency != float('inf'):
                        logger.info("Reconnection successful - Resetting failure count")
                        self.connection_state['health_check_failures'] = 0
                        return
                except Exception as e:
                    logger.error(f"Reconnection failed: {e}")
                
                # If reconnection fails, proceed with emergency restart
                logger.critical("Reconnection failed - Initiating emergency restart")
                await self._emergency_restart()
            
            elif failures >= 2:
                logger.warning(f"""
━━━━━━ Multiple Health Check Failures ━━━━━━
Failure Count: {failures}
Attempting reconnection...
━━━━━━━━━━━━━━━━━━━━━━━━""")
                try:
                    await self.close()
                    await asyncio.sleep(2)
                    await self.start(os.environ.get('DISCORD_BOT_TOKEN'))
                except Exception as e:
                    logger.error(f"Reconnection attempt failed: {e}")
            
            else:
                logger.info(f"""
━━━━━━ Minor Health Check Issue ━━━━━━
Failure Count: {failures}
Status: Monitoring
Action: Continuing normal operation
━━━━━━━━━━━━━━━━━━━━━━━━""")
                
        except Exception as e:
            logger.error(f"Error handling health failure: {str(e)}", exc_info=True)

    async def _emergency_restart(self, force=False):
        """Perform emergency restart of the bot with aggressive recovery
        
        Args:
            force (bool): If True, skips graceful shutdown attempts and forces immediate restart
        """
        try:
            current_time = datetime.now(timezone.utc)
            logger.critical(f"""
━━━━━━ Emergency Restart Initiated ━━━━━━
Reason: Health check failures exceeded
Time: {current_time}
Uptime: {(current_time - self.connection_state['startup_time']).total_seconds() / 3600:.1f}h
Last Error: {self.connection_state.get('last_error')}
Memory Usage: {self.connection_state['memory_usage']:.1f}%
CPU Usage: {self.connection_state['cpu_usage']:.1f}%
Health Failures: {self.connection_state['health_check_failures']}
Connected Guilds: {self.connection_state['guilds_count']}
Last Message Time: {self.connection_state['last_message_time']}
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
            if not force:
                # Attempt graceful shutdown of tasks
                try:
                    logger.info("Attempting graceful shutdown...")
                    # Stop all background tasks
                    self.health_check.cancel()
                    self.connection_monitor.cancel()
                    
                    # Close voice clients
                    for vc in self.voice_clients:
                        try:
                            await vc.disconnect(force=True)
                        except:
                            pass
                    
                    # Close existing connection
                    await self.close()
                    await asyncio.sleep(2)  # Wait for cleanup
                except Exception as e:
                    logger.error(f"Error during graceful shutdown: {str(e)}")
            else:
                logger.warning("Force restart requested - Skipping graceful shutdown")
                try:
                    # Forceful cleanup
                    for task in asyncio.all_tasks():
                        if task is not asyncio.current_task():
                            task.cancel()
                    
                    # Force close all connections
                    if hasattr(self, '_connection'):
                        self._connection.clear()
                    
                    # Force clear session
                    if hasattr(self, 'session'):
                        await self.session.close()
                        
                except Exception as e:
                    logger.error(f"Error during force shutdown: {str(e)}")
                    
            # Immediate process cleanup
            import gc
            gc.collect()  # Force garbage collection
            
            # Clear internal state and cache
            self.clear()
            for cache_attr in ['_users', '_guilds', '_channels', '_messages']:
                if hasattr(self, cache_attr):
                    getattr(self, cache_attr).clear()
            
            # Reset connection state
            self.connection_state.update({
                'connected': False,
                'last_heartbeat': None,
                'reconnect_count': 0,
                'health_check_failures': 0,
                'consecutive_timeouts': 0,
                'error_count': 0,
                'latency_history': [],
                'last_recovery_action': datetime.now(timezone.utc)
            })
            
            # Enhanced cleanup and wait period
            await asyncio.sleep(10)  # Increased wait time for better cleanup
            
            # Attempt reconnection with improved exponential backoff
            max_retries = 5  # Increased max retries
            base_delay = 5
            
            for attempt in range(max_retries):
                try:
                    # Calculate backoff with jitter
                    delay = min(base_delay * (2 ** attempt) + random.uniform(1, 5), 60)
                    logger.info(f"""
━━━━━━ Restart Attempt {attempt + 1}/{max_retries} ━━━━━━
Delay: {delay:.1f}s
Previous Errors: {self.connection_state.get('last_error')}
Memory Usage: {self.connection_state['memory_usage']:.1f}%
━━━━━━━━━━━━━━━━━━━━━━━━""")
                    
                    # Attempt to start with the token
                    await self.start(os.environ.get('DISCORD_BOT_TOKEN'))
                    
                    # Enhanced stability check
                    stability_check_attempts = 3
                    for _ in range(stability_check_attempts):
                        await asyncio.sleep(5)
                        if self.is_ready() and self.latency != float('inf'):
                            guild_count = len(self.guilds)
                            current_latency = self.latency * 1000
                            
                            logger.info(f"""
━━━━━━ Emergency Restart Completed ━━━━━━
Status: Success
Connected Guilds: {guild_count}
Latency: {current_latency:.2f}ms
Memory Usage: {self.connection_state['memory_usage']:.1f}%
CPU Usage: {self.connection_state['cpu_usage']:.1f}%
Time: {datetime.now(timezone.utc)}
━━━━━━━━━━━━━━━━━━━━━━━━""")
                            
                            # Reset health metrics
                            self.connection_state.update({
                                'health_check_failures': 0,
                                'consecutive_timeouts': 0,
                                'error_count': 0,
                                'reconnect_count': 0
                            })
                            return
                except Exception as e:
                    logger.error(f"Restart attempt {attempt + 1} failed: {str(e)}")
                    await asyncio.sleep(5 * (attempt + 1))  # Exponential backoff
            
            raise Exception("Failed to restart after maximum retries")
            
        except Exception as e:
            logger.critical(f"Emergency restart failed: {str(e)}", exc_info=True)
            # Notify admins or take additional recovery actions
            try:
                # Try one last time with a clean slate
                self.clear()
                await asyncio.sleep(10)
                await self.start(os.environ.get('DISCORD_BOT_TOKEN'))
            except:
                logger.critical("Final restart attempt failed - Manual intervention required")
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

            # Enhanced message handling with improved context and topic detection
            try:
                # Get message context with expanded topic detection
                message_content = message.content.lower()
                is_command = message.content.startswith('/')
                
                # Expanded topic detection with specific categories
                topics = {
                    'funding': ['funding', 'budget', 'allocation', 'invest'],
                    'governance': ['governance', 'voting', 'proposal', 'decision'],
                    'rewards': ['reward', 'distribution', 'earnings', 'payout'],
                    'tokens': ['glm', 'token', 'staking', 'lock'],
                    'platform': ['octant', 'platform', 'system', 'mechanism']
                }
                
                # Detect primary topic
                detected_topic = None
                for topic, keywords in topics.items():
                    if any(keyword in message_content for keyword in keywords):
                        detected_topic = topic
                        break
                
                # Enhanced context management
                context = {
                    'topic': detected_topic,
                    'is_command': is_command,
                    'previous_context': getattr(message.author, 'last_topic', None),
                    'message_history': getattr(message.author, 'message_history', [])[-3:],  # Keep last 3 messages for context
                    'user_id': str(message.author.id),
                    'channel_id': str(message.channel.id),
                    'guild_id': str(message.guild.id) if message.guild else None
                }
                
                # Update message history
                if not hasattr(message.author, 'message_history'):
                    message.author.message_history = []
                message.author.message_history.append(message.content)
                
                # Get response with enhanced context handling
                try:
                    response = await asyncio.wait_for(
                        asyncio.create_task(self.chat_handler.get_response_async(
                            message.content,
                            context=context
                        )),
                        timeout=30.0  # 30 second timeout
                    )
                    
                    if not response or response.isspace():
                        logger.warning(f"Empty response received for message: {message.content[:50]}...")
                        await message.reply(
                            "I apologize, but I couldn't generate a meaningful response. Please try rephrasing your question.", 
                            mention_author=True
                        )
                        return
                        
                except asyncio.TimeoutError:
                    logger.error("Response generation timed out")
                    await message.reply(
                        "I apologize, but the response is taking longer than expected. Please try again.", 
                        mention_author=True
                    )
                    return
                except Exception as e:
                    logger.error(f"Error generating response: {str(e)}", exc_info=True)
                    await message.reply(
                        "I encountered an error while processing your request. Please try again.", 
                        mention_author=True
                    )
                    return
                
                # Format response with improved readability
                if isinstance(response, list):
                    formatted_response = "\n\n".join(
                        chunk.strip() for chunk in response 
                        if chunk and chunk.strip()
                    )
                else:
                    formatted_response = response.strip()
                
                # Create an enhanced embedded response
                embed = discord.Embed(
                    description=formatted_response,
                    color=discord.Color.blue()
                )
                
                # Add context-aware title and formatting
                if detected_topic:
                    topic_icons = {
                        'funding': '💰',
                        'governance': '🏛️',
                        'rewards': '🎁',
                        'tokens': '🪙',
                        'platform': '🔍'
                    }
                    embed.title = f"{topic_icons.get(detected_topic, '🔍')} {detected_topic.title()} Information"
                elif is_command:
                    embed.title = "🤖 Command Response"
                else:
                    embed.title = "💬 Chat Response"
                
                # Store last topic for context maintenance
                setattr(message.author, 'last_topic', detected_topic)
                
                # Send the formatted response
                await message.reply(embed=embed)
                
                # Update connection state
                self.connection_state['last_message_time'] = datetime.now(timezone.utc)
                
            except Exception as e:
                logger.error(f"Error processing message response: {str(e)}", exc_info=True)
                await message.reply("I encountered an error processing your message. Please try again.", mention_author=True)

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
