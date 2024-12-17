import os
import sys
import random
from async_timeout import timeout
import logging
import asyncio
import time
import discord
from discord import app_commands
from discord.ext import tasks, commands
from datetime import datetime, timezone
import psutil
from chat_handler import ChatHandler
from discord_trivia import DiscordTrivia
import traceback

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('discord_bot.log')
    ]
)
logger = logging.getLogger(__name__)

class OctantBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='/',
            intents=intents,
            heartbeat_timeout=60,
            activity=discord.Activity(type=discord.ActivityType.watching, name="/help for commands")
        )
        
        self.chat_handler = ChatHandler()
        self.trivia = DiscordTrivia()
        self.start_time = datetime.now(timezone.utc)
        self.error_count = 0
        self.reconnect_attempts = 0
        
        # Remove default help
        self.remove_command('help')
        
    async def setup_hook(self):
        """Enhanced setup with proper error handling and status verification."""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
            cpu_usage = psutil.cpu_percent()
            logger.info(f"""━━━━━━ Bot Setup Started ━━━━━━
Time: {current_time}
Memory Usage: {memory_usage:.1f}MB
CPU Usage: {cpu_usage}%
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
            # Enhanced token validation with detailed reporting
            token = os.getenv('DISCORD_BOT_TOKEN')
            if not token:
                logger.error("DISCORD_BOT_TOKEN environment variable not found")
                print("[RAILWAY ERROR] Discord token not found", file=sys.stderr)
                raise ValueError("Discord token not found in environment variables")
            
            if len(token.split('.')) != 3:
                logger.error("Malformed Discord token detected")
                print("[RAILWAY ERROR] Invalid Discord token format", file=sys.stderr)
                raise ValueError("Invalid Discord token format")
            
            # Verify token prefix
            token_parts = token.split('.')
            if not token_parts[0].isalnum():
                logger.error("Invalid token prefix format")
                print("[RAILWAY ERROR] Token prefix is invalid", file=sys.stderr)
                raise ValueError("Invalid token prefix format")
            
            logger.info("Token validation successful")
            print("[RAILWAY INFO] Discord token validated successfully", file=sys.stderr)
            
            # Enhanced connection settings
            self.connect_timeout = 30.0
            self.max_reconnect_delay = 120.0
            self.gateway_queue_size = 100
            self.max_ratelimit_timeout = 60.0
            self.connection_retries = 0
            self.max_connection_retries = 5
            
            # Initialize detailed connection state tracking
            self.connection_state = {
                'last_attempt': datetime.now(timezone.utc),
                'consecutive_failures': 0,
                'last_success': None,
                'current_state': 'initializing',
                'gateway_connected': False,
                'heartbeat_latency': None,
                'identify_attempts': 0,
                'session_id': None,
                'resume_gateway_url': None,
                'last_heartbeat_ack': None,
                'detailed_status': 'Starting up'
            }
            
            logger.info("Enhanced connection state initialized")
            print("[RAILWAY INFO] Connection state tracking initialized", file=sys.stderr)
            
            # Initialize commands with verification
            logger.info("Registering commands...")
            await self.register_commands()
            logger.info("Commands registered successfully")
            
            # Start enhanced health monitoring
            logger.info("Starting health monitoring...")
            self.health_check.start()
            logger.info("Health monitoring activated")
            
            # Gateway connection monitoring
            self._gateway_monitor = asyncio.create_task(self._monitor_gateway_connection())
            
            # Final setup verification with enhanced metrics
            app_id = self.application_id if hasattr(self, 'application_id') else 'Pending'
            shard_count = self.shard_count if hasattr(self, 'shard_count') and self.shard_count else 'None'
            cmd_count = len(self.tree.get_commands()) if hasattr(self, 'tree') else 0
            
            startup_status = f"""━━━━━━ Setup Complete ━━━━━━
Application ID: {app_id}
Shard Count: {shard_count}
Command Count: {cmd_count}
Gateway Queue Size: {self.gateway_queue_size}
Connection Settings:
- Timeout: {self.connect_timeout}s
- Max Retries: {self.max_connection_retries}
- Max Ratelimit: {self.max_ratelimit_timeout}s
━━━━━━━━━━━━━━━━━━━━━━━━"""
            
            logger.info(startup_status)
            print(f"[RAILWAY INFO] {startup_status}", file=sys.stderr)
            
        except Exception as e:
            error_msg = f"""━━━━━━ Setup Error ━━━━━━
Error Type: {type(e).__name__}
Error Message: {str(e)}
Stack Trace: {traceback.format_exc()}
Memory Usage: {psutil.Process().memory_percent():.1f}%
CPU Usage: {psutil.cpu_percent()}%
━━━━━━━━━━━━━━━━━━━━━━━━"""
            
            logger.error(error_msg)
            print(f"[RAILWAY ERROR] {error_msg}", file=sys.stderr)
            raise

    async def _monitor_gateway_connection(self):
        """Monitor gateway connection status and handle reconnection."""
        while True:
            try:
                if hasattr(self, '_connection') and self._connection:
                    ws = self._connection.ws
                    if ws is None or ws.closed:
                        logger.warning("Gateway connection lost or not established")
                        print("[RAILWAY WARNING] Discord gateway connection lost", file=sys.stderr)
                        self.connection_state.update({
                            'gateway_connected': False,
                            'detailed_status': 'Gateway disconnected'
                        })
                        
                        # Attempt reconnection if not already in progress
                        if not self.is_closed():
                            logger.info("Attempting gateway reconnection...")
                            print("[RAILWAY INFO] Initiating gateway reconnection", file=sys.stderr)
                            await self.connect_with_backoff()
                    else:
                        self.connection_state.update({
                            'gateway_connected': True,
                            'detailed_status': 'Connected to gateway'
                        })
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Gateway monitoring error: {str(e)}")
                print(f"[RAILWAY ERROR] Gateway monitor: {str(e)}", file=sys.stderr)
                await asyncio.sleep(5)  # Wait before retrying
        
    async def register_commands(self):
        @self.tree.command(name="help", description="Show available commands")
        async def help(interaction: discord.Interaction):
            embed = discord.Embed(
                title="📚 Octant Bot Commands",
                description="Here are all available commands:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🎮 Game Commands",
                value="• `/trivia` - Start a trivia game",
                inline=False
            )
            embed.add_field(
                name="🛠️ Utility Commands",
                value="• `/ping` - Check bot latency\n• `/help` - Show this message",
                inline=False
            )
            embed.add_field(
                name="💬 Chat Features",
                value="Reply to any of my messages to chat about Octant!",
                inline=False
            )
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="ping", description="Check bot latency")
        async def ping(interaction: discord.Interaction):
            latency = round(self.latency * 1000)
            embed = discord.Embed(
                title="🏓 Pong!",
                description=f"Bot latency: {latency}ms",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="trivia", description="Start an Octant trivia game")
        async def trivia(interaction: discord.Interaction):
            await self.trivia.start_game(interaction)
            
        await self.tree.sync()

    @tasks.loop(seconds=30)  # More frequent checks for better responsiveness
    async def health_check(self):
        """Enhanced health monitoring with connection verification and auto-recovery."""
        try:
            memory = psutil.Process().memory_percent()
            cpu = psutil.cpu_percent()
            
            # Enhanced connection verification with more resilient checks
            is_connected = False
            connection_status = {
                'is_ready': self.is_ready(),
                'has_user': hasattr(self, 'user'),
                'has_latency': self.latency is not None,
                'latency_value': f"{self.latency*1000:.2f}ms" if self.latency else "N/A",
                'guilds_count': len(self.guilds) if hasattr(self, 'guilds') else 0,
                'last_heartbeat': getattr(getattr(self, '_connection', None), '_last_heartbeat', None),
                'ws_connected': hasattr(self, 'ws') and self.ws and not self.ws.closed if hasattr(self, 'ws') else False
            }
            
            # Check WebSocket health
            current_time = time.time()
            heartbeat_age = (current_time - connection_status['last_heartbeat']) if connection_status['last_heartbeat'] else float('inf')
            
            is_connected = all([
                connection_status['is_ready'],
                connection_status['has_user'],
                connection_status['has_latency'],
                connection_status['ws_connected'],
                heartbeat_age < 60  # Heartbeat within last minute
            ])
            
            # Enhanced health metrics with improved Railway visibility
            if is_connected:
                if self.latency > 2.0 or heartbeat_age > 30:  # Stricter thresholds
                    warning_msg = f"""
⚠️ [RAILWAY WARNING] Discord Bot Performance Degraded ⚠️
━━━━━━ Performance Alert ━━━━━━
• Current Latency: {connection_status['latency_value']}
• Last Heartbeat Age: {heartbeat_age:.2f}s
• Connected Guilds: {connection_status['guilds_count']}
• Memory Usage: {memory:.1f}%
• CPU Usage: {cpu:.1f}%
• WebSocket State: {'Connected' if connection_status['ws_connected'] else 'Disconnected'}
━━━━━━━━━━━━━━━━━━━━━━━━"""
                    logger.warning(warning_msg)
                    print(warning_msg, file=sys.stderr)
                    sys.stderr.flush()
                    self.error_count += 1
                else:
                    self.error_count = max(0, self.error_count - 1)  # Gradually reduce error count
                    
            # Enhanced startup handling with better visibility
            startup_grace_period = 60
            if not is_connected:
                if (datetime.now(timezone.utc) - self.start_time).total_seconds() < startup_grace_period:
                    startup_msg = f"""
ℹ️ [RAILWAY INFO] Discord Bot Startup Progress
━━━━━━ Startup Status ━━━━━━
• Time Elapsed: {(datetime.now(timezone.utc) - self.start_time).total_seconds():.1f}s
• Status: Initializing
• WebSocket: {'Connected' if connection_status['ws_connected'] else 'Connecting'}
• Memory: {memory:.1f}%
• CPU: {cpu:.1f}%
━━━━━━━━━━━━━━━━━━━━━━━━"""
                    logger.info(startup_msg)
                    print(startup_msg, file=sys.stderr)
                    sys.stderr.flush()
                    is_connected = True  # Grace period
                else:
                    # Log detailed connection failure after grace period
                    failure_msg = f"""
🔴 [RAILWAY ALERT] Discord Bot Connection Failure
━━━━━━ Connection Diagnostics ━━━━━━
• Ready State: {connection_status['is_ready']}
• Has User: {connection_status['has_user']}
• Latency Available: {connection_status['has_latency']}
• WebSocket Connected: {connection_status['ws_connected']}
• Last Heartbeat Age: {heartbeat_age:.2f}s
• Guild Count: {connection_status['guilds_count']}
━━━━━━━━━━━━━━━━━━━━━━━━"""
                    logger.error(failure_msg)
                    print(failure_msg, file=sys.stderr)
                    sys.stderr.flush()
                    
            # Calculate and log enhanced metrics
            uptime_hours = (datetime.now(timezone.utc) - self.start_time).total_seconds() / 3600
            detailed_status = f"""━━━━━━ Health Check ━━━━━━
Status: {"Connected" if is_connected else "Disconnected"}
Memory: {memory:.1f}%
CPU: {cpu:.1f}%
Latency: {connection_status['latency_value']}
Guilds: {connection_status['guilds_count']}
Uptime: {uptime_hours:.1f}h
Error Count: {self.error_count}
Last Heartbeat Age: {heartbeat_age:.2f}s
WebSocket: {'Connected' if connection_status['ws_connected'] else 'Disconnected'}
━━━━━━━━━━━━━━━━━━━━━━━━"""
            
            logger.info(detailed_status)
            if not is_connected or self.error_count > 0:
                print(detailed_status, file=sys.stderr)
                sys.stderr.flush()
            
            # Enhanced health check criteria
            needs_restart = any([
                memory > 90,
                cpu > 90,
                self.latency > 5,
                not is_connected,
                heartbeat_age > 90
            ])
            
            if needs_restart:
                self.error_count += 1
                logger.warning(f"Health check failed (attempt {self.error_count}/3)")
                await self._handle_health_failure()
            else:
                if self.error_count > 0:
                    logger.info("Health check recovered - resetting error count")
                    print("[RAILWAY INFO] Bot health recovered", file=sys.stderr)
                    sys.stderr.flush()
                self.error_count = 0
                
        except Exception as e:
            error_msg = f"""
‼️ [RAILWAY ERROR] Health Check Error
━━━━━━ Error Details ━━━━━━
Error: {str(e)}
Stack Trace: {traceback.format_exc()}
Time: {datetime.now(timezone.utc)}
━━━━━━━━━━━━━━━━━━━━━━━━"""
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
            sys.stderr.flush()
            self.error_count += 1

    async def on_ready(self):
        logger.info(f"""━━━━━━ Bot Ready ━━━━━━
Logged in as: {self.user.name}
Bot ID: {self.user.id}
Guilds: {len(self.guilds)}
━━━━━━━━━━━━━━━━━━━━━━━━""")
        
        # Start message cleanup task
        self.cleanup_messages.start()
        
    @tasks.loop(minutes=5)
    async def cleanup_messages(self):
        """Clean up old processed messages"""
        current_time = time.time()
        self._last_processed = {
            msg_id: timestamp 
            for msg_id, timestamp in self._last_processed.items()
            if current_time - timestamp < 300  # Keep last 5 minutes
        }

    # Track last processed message
    _last_processed = {}
    
    async def on_message(self, message):
        """Handle incoming messages with proper error handling and deduplication."""
        # Ignore our own messages
        if message.author == self.user:
            return
            
        # Generate a unique message ID
        message_id = f"{message.channel.id}:{message.id}"
        
        try:
            # Skip if we've already processed this message
            if message_id in self._last_processed:
                return
                
            # Only respond to mentions or replies to the bot
            is_mention = self.user.mentioned_in(message)
            is_reply = (
                message.reference and 
                message.reference.resolved and 
                message.reference.resolved.author == self.user
            )
            
            if not (is_reply or is_mention):
                return
                
            # Track this message as processed immediately
            self._last_processed[message_id] = time.time()
            
            # Clean the message content
            content = message.content
            if is_mention:
                # Remove all bot mentions from the content
                for mention in message.mentions:
                    if mention == self.user:
                        content = content.replace(f'<@{mention.id}>', '').strip()
                        content = content.replace(f'<@!{mention.id}>', '').strip()
            
            # Get and send the response
            async with message.channel.typing():
                response = self.chat_handler.get_response(content)
                
                # Handle both single string and list responses
                if isinstance(response, list):
                    for chunk in response:
                        if chunk and chunk.strip():
                            await message.reply(chunk.strip())
                elif response and response.strip():
                    await message.reply(response.strip())
                    
        except Exception as e:
            logger.error(f"Error processing message {message_id if 'message_id' in locals() else 'unknown'}: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            try:
                await message.reply("I encountered an error processing your message. Please try again.")
            except:
                logger.error("Failed to send error message to user")

    async def on_error(self, event, *args, **kwargs):
        """Enhanced error handling with Railway visibility"""
        error = sys.exc_info()[1]
        error_trace = traceback.format_exc()
        
        # Format error for Railway's monitoring
        railway_error = f"""
🚨 [RAILWAY ERROR] Discord Bot Event Error 🚨
━━━━━━ Event Error Details ━━━━━━
Event: {event}
Error Type: {type(error).__name__}
Error Message: {str(error)}
Time: {datetime.now(timezone.utc).isoformat()}

Stack Trace:
{error_trace}

System State:
• Memory: {psutil.Process().memory_percent():.1f}%
• CPU: {psutil.cpu_percent()}%
• Uptime: {(datetime.now(timezone.utc) - self.start_time).total_seconds() / 3600:.1f}h
• Connection State: {getattr(self, 'connection_state', {}).get('current_state', 'unknown')}
• Last Success: {getattr(self, 'connection_state', {}).get('last_success', 'never')}
• Consecutive Failures: {getattr(self, 'connection_state', {}).get('consecutive_failures', 0)}
━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        # Enhanced logging for Railway's monitoring
        logger.error(railway_error)
        
        # Ensure Railway sees the error in its logs
        print("\n" + "!"*80, file=sys.stderr)
        print("[RAILWAY ALERT] Discord Bot Error Detected", file=sys.stderr)
        print("-" * 40, file=sys.stderr)
        print(railway_error, file=sys.stderr)
        print("!"*80 + "\n", file=sys.stderr)
        sys.stderr.flush()
        
        # Attempt recovery if appropriate
        if isinstance(error, (discord.ConnectionClosed, discord.GatewayNotFound)):
            print("[RAILWAY ALERT] Connection error detected - attempting recovery", file=sys.stderr)
            try:
                if hasattr(self, '_connection'):
                    self._connection.clear()
                await self.connect_with_backoff()
            except Exception as e:
                print(f"[RAILWAY ALERT] Recovery failed: {str(e)}", file=sys.stderr)
                sys.stderr.flush()

    async def connect_with_backoff(self):
        """Enhanced reconnection logic with proper state management and backoff"""
        try:
            logger.info("Initiating reconnection sequence...")
            print("[RAILWAY ALERT] Initiating bot reconnection sequence", file=sys.stderr)
            sys.stderr.flush()
            
            # Enhanced connection state tracking
            detailed_state = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'memory_usage': f"{psutil.Process().memory_percent():.1f}%",
                'cpu_usage': f"{psutil.cpu_percent()}%",
                'connection_attempts': self.reconnect_attempts,
                'last_error': traceback.format_exc() if sys.exc_info()[0] else None
            }
            
            logger.info(f"Current connection state: {detailed_state}")
            print(f"[RAILWAY DEBUG] Connection state: {detailed_state}", file=sys.stderr)
            sys.stderr.flush()
            
            self.connection_state['current_state'] = 'reconnecting'
            self.connection_state['last_attempt'] = datetime.now(timezone.utc)
            self.connection_state['detailed_state'] = detailed_state
            
            # Close existing connection if active
            if not self.is_closed():
                logger.info("Closing existing connection...")
                await self.close()
            
            # Implement exponential backoff
            retry_count = self.connection_state.get('consecutive_failures', 0)
            max_wait = min(300, (2 ** retry_count))  # Cap at 5 minutes
            wait_time = max_wait + (random.uniform(0, min(max_wait * 0.1, 30)))  # Add jitter
            
            logger.info(f"Waiting {wait_time:.1f} seconds before reconnection attempt...")
            print(f"[RAILWAY ALERT] Waiting {wait_time:.1f}s before reconnection (attempt {retry_count + 1})", 
                  file=sys.stderr)
            await asyncio.sleep(wait_time)
            
            # Verify token and attempt reconnection
            token = os.getenv('DISCORD_BOT_TOKEN')
            if not token:
                raise ValueError("Discord token not found")
            
            # Clear existing state
            if hasattr(self, '_ready'):
                self._ready.clear()
            if hasattr(self, '_connection'):
                self._connection.clear()
            
            # Attempt reconnection with timeout
            async with timeout(60):  # 60 second timeout for reconnection
                await self.login(token)
                await self.connect()
            
            # Update connection state on success
            self.connection_state.update({
                'last_success': datetime.now(timezone.utc),
                'consecutive_failures': 0,
                'current_state': 'connected'
            })
            
            success_msg = f"""━━━━━━ Reconnection Successful ━━━━━━
Bot: {self.user.name if hasattr(self, 'user') else 'Unknown'}
Latency: {self.latency*1000:.2f}ms
Guilds: {len(self.guilds) if hasattr(self, 'guilds') else 0}
Time: {datetime.now(timezone.utc).isoformat()}
━━━━━━━━━━━━━━━━━━━━━━━━"""
            
            logger.info(success_msg)
            print("\n[RAILWAY ALERT] Bot reconnection successful", file=sys.stderr)
            print(success_msg, file=sys.stderr)
            sys.stderr.flush()
            return True
            
        except asyncio.TimeoutError:
            self.connection_state['consecutive_failures'] += 1
            error_msg = f"Reconnection attempt {self.connection_state['consecutive_failures']} timed out"
            logger.error(error_msg)
            print(f"[RAILWAY ALERT] {error_msg}", file=sys.stderr)
            return False
            
        except Exception as e:
            self.connection_state['consecutive_failures'] += 1
            error_msg = f"Reconnection failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            print(f"[RAILWAY ALERT] {error_msg}", file=sys.stderr)
            return False

    async def reconnect(self):
        """Implements proper reconnection logic with state management"""
        try:
            logger.info("Initiating reconnection sequence...")
            print("[RAILWAY ALERT] Initiating reconnection sequence", file=sys.stderr)
            sys.stderr.flush()
            
            # Update connection state
            self.connection_state['current_state'] = 'reconnecting'
            self.connection_state['last_attempt'] = datetime.now(timezone.utc)
            
            # Close existing connection if active
            if not self.is_closed():
                await self.close()
            
            # Clear existing state
            if hasattr(self, '_ready'):
                self._ready.clear()
            if hasattr(self, '_connection'):
                self._connection.clear()
            
            # Get token
            token = os.getenv('DISCORD_BOT_TOKEN')
            if not token:
                raise ValueError("Discord token not found")
            
            # Attempt reconnection with timeout
            async with timeout(30):  # 30 second timeout
                await self.login(token)
                await self.connect()
            
            # Update state on success
            self.connection_state.update({
                'last_success': datetime.now(timezone.utc),
                'consecutive_failures': 0,
                'current_state': 'connected'
            })
            
            logger.info("Reconnection successful")
            print("[RAILWAY ALERT] Bot reconnection successful", file=sys.stderr)
            sys.stderr.flush()
            return True
            
        except Exception as e:
            self.connection_state['consecutive_failures'] += 1
            error_msg = f"Reconnection failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            print(f"[RAILWAY ALERT] {error_msg}", file=sys.stderr)
            sys.stderr.flush()
            return False
    
    async def _handle_health_failure(self):
        """Enhanced health failure handling with proper reconnection and Railway reporting"""
        try:
            # Immediately log health failure to stderr for Railway visibility
            alert_msg = f"""
🔴 [RAILWAY ALERT] Discord Bot Health Check Failure 🔴
Time: {datetime.now(timezone.utc).isoformat()}
Error Count: {self.error_count}
Connection State: {self.connection_state.get('current_state', 'unknown')}
Last Success: {self.connection_state.get('last_success', 'never')}
"""
            print(alert_msg, file=sys.stderr)
            sys.stderr.flush()
            
            if self.error_count >= 3:
                # Enhanced error details for Railway's monitoring
                error_details = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'error_count': self.error_count,
                    'memory_usage': f"{psutil.Process().memory_percent():.1f}%",
                    'cpu_usage': f"{psutil.cpu_percent()}%",
                    'uptime_hours': f"{(datetime.now(timezone.utc) - datetime.fromtimestamp(psutil.Process().create_time(), tz=timezone.utc)).total_seconds() / 3600:.1f}h",
                    'latency': f"{self.latency*1000:.2f}ms" if hasattr(self, 'latency') else "N/A",
                    'connected_guilds': len(self.guilds) if hasattr(self, 'guilds') else 0,
                    'last_error': traceback.format_exc() if sys.exc_info()[0] else "None",
                    'connection_state': self.connection_state
                }
                
                # Railway-formatted critical error report
                railway_error = f"""
🚨 [RAILWAY CRITICAL] Discord Bot Health Failure 🚨
━━━━━━ Critical System Alert ━━━━━━
Service: Discord Bot
Status: CRITICAL FAILURE - Multiple Health Checks Failed
Time: {error_details['timestamp']}

📊 System State:
• Error Count: {self.error_count}
• Memory Usage: {error_details['memory_usage']}
• CPU Usage: {error_details['cpu_usage']}
• Process Uptime: {error_details['uptime_hours']}

🔌 Discord Status:
• Connection: DEGRADED
• Latency: {error_details['latency']}
• Connected Guilds: {error_details['connected_guilds']}
• Connection State: {error_details['connection_state'].get('current_state', 'unknown')}
• Last Success: {error_details['connection_state'].get('last_success', 'never')}
• Consecutive Failures: {error_details['connection_state'].get('consecutive_failures', 0)}

⚠️ CRITICAL ACTION REQUIRED - Service Degraded ⚠️"""
                
                # Enhanced Railway visibility - use both logger and stderr
                logger.critical(railway_error)
                print("\n" + "!"*80, file=sys.stderr)
                print(railway_error, file=sys.stderr)
                print("!"*80 + "\n", file=sys.stderr)
                sys.stderr.flush()
                
                # Attempt reconnection with enhanced logging
                print("[RAILWAY ALERT] Attempting emergency reconnection...", file=sys.stderr)
                sys.stderr.flush()
                
                success = await self.reconnect()
                
                if not success:
                    shutdown_msg = f"""
‼️ [RAILWAY EMERGENCY] Discord Bot Shutdown Required ‼️
━━━━━━ Emergency Shutdown Sequence ━━━━━━
Reason: Critical health check failures & failed reconnection
Time: {datetime.now(timezone.utc)}
Error Count: {self.error_count}
Last Error: {traceback.format_exc() if sys.exc_info()[0] else "None"}
Connection State: {self.connection_state}
Memory Usage: {psutil.Process().memory_percent():.1f}%
CPU Usage: {psutil.cpu_percent()}%
━━━━━━━━━━━━━━━━━━━━━━━━"""
                    
                    # Ensure Railway sees the shutdown
                    logger.critical("EMERGENCY SHUTDOWN INITIATED")
                    logger.critical(shutdown_msg)
                    print("\n" + "!"*80, file=sys.stderr)
                    print("[RAILWAY EMERGENCY] Discord Bot Crash Detected", file=sys.stderr)
                    print(shutdown_msg, file=sys.stderr)
                    print("!"*80 + "\n", file=sys.stderr)
                    sys.stderr.flush()
                    
                    # Force immediate exit for Railway to detect
                    os._exit(1)
            else:
                warning_msg = f"""
━━━━━━ Health Check Warning ━━━━━━
Time: {datetime.now(timezone.utc)}
Error Count: {self.error_count}
Status: Monitoring
Action: Continuing operation
Connection State: {self.connection_state}
━━━━━━━━━━━━━━━━━━━━━━━━"""
                logger.warning(warning_msg)
                print("[RAILWAY WARNING] " + warning_msg, file=sys.stderr)
                sys.stderr.flush()
                
        except Exception as e:
            critical_error = f"""
━━━━━━ Unexpected Error in Health Monitor ━━━━━━
Error: {str(e)}
Stack Trace: {traceback.format_exc()}
Time: {datetime.now(timezone.utc)}
Memory: {psutil.Process().memory_percent():.1f}%
CPU: {psutil.cpu_percent()}%
━━━━━━━━━━━━━━━━━━━━━━━━"""
            
            # Ensure Railway sees the crash
            logger.critical("CRITICAL ERROR: Health monitor failure")
            logger.critical(critical_error)
            print("\n" + "!"*80, file=sys.stderr)
            print("[RAILWAY CRITICAL] Health Monitor Crash", file=sys.stderr)
            print(critical_error, file=sys.stderr)
            print("!"*80 + "\n", file=sys.stderr)
            sys.stderr.flush()
            
            # Force exit for Railway to detect
            os._exit(1)

async def main():
        bot = OctantBot()
        retry_count = 0
        max_retries = 10
        last_success = time.time()
        
        async def attempt_connection(token):
            try:
                # Set connection timeout
                async with timeout(30):  # 30 second timeout for initial connection
                    await bot.start(token)
                return True
            except asyncio.TimeoutError:
                logger.error("Connection attempt timed out after 30 seconds")
                return False
            except discord.LoginFailure as e:
                logger.error(f"Login failed: {str(e)}")
                return False
            except Exception as e:
                logger.error(f"Connection error: {str(e)}")
                return False
        
        while True:
            try:
                # Enhanced token validation
                token = os.getenv('DISCORD_BOT_TOKEN')
                if not token:
                    logger.error("DISCORD_BOT_TOKEN not set")
                    raise ValueError("Discord token not found in environment variables")
                
                # Validate token format
                if len(token.split('.')) != 3:
                    logger.error("Invalid Discord token format")
                    raise ValueError("Malformed Discord token")
                
                # Reset retry count if last successful connection was more than 1 hour ago
                if time.time() - last_success > 3600:
                    retry_count = 0
                    logger.info("Reset retry count due to time elapsed since last success")
                
                # Log connection attempt with enhanced diagnostics
                logger.info(f"""━━━━━━ Connection Attempt {retry_count + 1} ━━━━━━
Bot Version: 1.0.1
Token Status: Valid
Retry Count: {retry_count}
Max Retries: {max_retries}
Memory Usage: {psutil.Process().memory_info().rss / 1024 / 1024:.1f}MB
CPU Usage: {psutil.cpu_percent()}%
Last Success: {datetime.fromtimestamp(last_success).strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━""")
                
                # Enhanced connection handling with specific error recovery
                try:
                    await bot.start(token)
                    last_success = time.time()  # Update last successful connection
                    retry_count = 0  # Reset retry count on successful connection
                    
                except discord.LoginFailure as e:
                    logger.error(f"Login Failed: {str(e)}")
                    if "token" in str(e).lower():
                        logger.critical("Invalid token detected - please check your configuration")
                        sys.exit(1)
                    raise
                    
                except discord.ConnectionClosed as e:
                    logger.error(f"Connection Closed: {str(e)}")
                    if e.code == 4014:  # Invalid permissions
                        logger.critical("Bot missing required permissions")
                        sys.exit(1)
                    raise
                    
                except discord.GatewayNotFound as e:
                    logger.error(f"Gateway Error: {str(e)}")
                    await asyncio.sleep(5)  # Short delay for gateway issues
                    continue
                    
                except discord.HTTPException as e:
                    logger.error(f"HTTP Error: {str(e)}")
                    if e.status >= 500:  # Discord server error
                        await asyncio.sleep(10)  # Longer delay for server issues
                        continue
                    raise
                    
                except Exception as e:
                    logger.error(f"Unexpected Error: {str(e)}")
                    raise
                    
            except Exception as e:
                retry_count += 1
                logger.error(f"""━━━━━━ Connection Error ━━━━━━
Error Type: {type(e).__name__}
Error Message: {str(e)}
Retry Count: {retry_count}/{max_retries}
Stack Trace: {traceback.format_exc()}
━━━━━━━━━━━━━━━━━━━━━━━━""")
                
                if retry_count >= max_retries:
                    logger.critical("""━━━━━━ Critical Error ━━━━━━
Max retries reached - attempting recovery restart
Memory Usage: {psutil.Process().memory_info().rss / 1024 / 1024:.1f}MB
CPU Usage: {psutil.cpu_percent()}%
━━━━━━━━━━━━━━━━━━━━━━━━""")
                    
                    # Attempt clean shutdown and restart
                    try:
                        if hasattr(bot, 'is_closed') and not bot.is_closed():
                            await bot.close()
                        # Reset connection state
                        retry_count = 0
                        await asyncio.sleep(30)  # Longer cooldown period
                        continue
                    except:
                        sys.exit(1)  # Force exit if clean shutdown fails
                    
                # Enhanced exponential backoff with jitter
                base_delay = min(30, 2 ** retry_count)
                jitter = random.uniform(0, min(base_delay * 0.1, 5))  # Add up to 5 seconds jitter
                wait_time = base_delay + jitter
                
                logger.info(f"Waiting {wait_time:.1f} seconds before retry...")
                await asyncio.sleep(wait_time)
                continue
                
            finally:
                # Enhanced cleanup on exit
                try:
                    if hasattr(bot, 'is_closed') and not bot.is_closed():
                        logger.info("Performing clean shutdown...")
                        await bot.close()
                except Exception as e:
                    logger.error(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt - shutting down")
    except Exception as e:
        error_msg = f"""
⚠️ RAILWAY FATAL ERROR REPORT ⚠️
━━━━━━ Bot Crash Details ━━━━━━
Time: {datetime.now(timezone.utc)}
Error Type: {type(e).__name__}
Error Message: {str(e)}
Stack Trace:
{traceback.format_exc()}
━━━━━━ System State ━━━━━━
Memory Usage: {psutil.Process().memory_percent():.1f}%
CPU Usage: {psutil.cpu_percent()}%
Process ID: {os.getpid()}
Python Version: {sys.version}
━━━━━━ Last Known State ━━━━━━
Uptime: {(datetime.now(timezone.utc) - datetime.fromtimestamp(psutil.Process().create_time(), tz=timezone.utc)).total_seconds() / 3600:.1f}h
Connected Guilds: Unknown (Crash state)
Last Error Count: Unknown (Crash state)
━━━━━━━━━━━━━━━━━━━━━━━━"""
        # Ensure proper logging hierarchy for Railway
        logger.critical("BOT CRASH DETECTED - See details below")
        logger.critical(error_msg)
        
        # Print to stderr for Railway's monitoring
        print("\n" + "!"*50, file=sys.stderr)
        print("CRITICAL ERROR: Discord Bot Crash Detected", file=sys.stderr)
        print("!"*50, file=sys.stderr)
        print(error_msg, file=sys.stderr)
        print("!"*50 + "\n", file=sys.stderr)
        
        # Force exit for Railway to detect crash
        os._exit(1)