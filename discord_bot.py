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
            
            # Enhanced token validation
            token = os.getenv('DISCORD_BOT_TOKEN')
            if not token:
                logger.error("DISCORD_BOT_TOKEN environment variable not found")
                raise ValueError("Discord token not found in environment variables")
            
            if len(token.split('.')) != 3:
                logger.error("Malformed Discord token detected")
                raise ValueError("Invalid Discord token format")
            
            logger.info("Token format validated")
            
            # Set connection timeout
            self.connect_timeout = 30.0
            self.max_reconnect_delay = 120.0
            
            # Initialize connection state tracking
            self.connection_state = {
                'last_attempt': datetime.now(timezone.utc),
                'consecutive_failures': 0,
                'last_success': None,
                'current_state': 'initializing'
            }
            
            logger.info("Connection state initialized")
            
            # Initialize commands
            logger.info("Registering commands...")
            await self.register_commands()
            logger.info("Commands registered successfully")
            
            # Start health monitoring
            logger.info("Starting health monitoring...")
            self.health_check.start()
            logger.info("Health monitoring activated")
            
            # Final setup verification
            # Log setup completion with proper string formatting
            app_id = self.application_id if hasattr(self, 'application_id') else 'Pending'
            shard_count = self.shard_count if hasattr(self, 'shard_count') and self.shard_count else 'None'
            cmd_count = len(self.tree.get_commands()) if hasattr(self, 'tree') else 0
            
            logger.info(f"""━━━━━━ Setup Complete ━━━━━━
Application ID: {app_id}
Shard Count: {shard_count}
Command Count: {cmd_count}
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
        except Exception as e:
            logger.error(f"""━━━━━━ Setup Error ━━━━━━
Error Type: {type(e).__name__}
Error Message: {str(e)}
Stack Trace: {traceback.format_exc()}
━━━━━━━━━━━━━━━━━━━━━━━━""")
            raise
        
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

    @tasks.loop(seconds=60)  # Increased interval to reduce unnecessary checks
    async def health_check(self):
        """Enhanced health monitoring with connection verification and auto-recovery."""
        try:
            memory = psutil.Process().memory_percent()
            cpu = psutil.cpu_percent()
            
            # Enhanced connection verification with more resilient checks
            is_connected = False
            try:
                is_connected = (
                    self.is_ready() and 
                    hasattr(self, 'user') and 
                    self.latency is not None and 
                    self.latency < 10.0  # More lenient latency threshold
                )
                # Add grace period for initial connection
                if not is_connected and (datetime.now(timezone.utc) - self.start_time).total_seconds() < 120:
                    logger.info("Bot in startup grace period, skipping connection check")
                    is_connected = True
            except Exception as e:
                logger.warning(f"Error checking connection status: {e}")
                # Don't mark as disconnected immediately on check error
                is_connected = True
            
            # Add grace period for initial connection
            if not is_connected and (datetime.now(timezone.utc) - self.start_time).total_seconds() < 60:
                is_connected = True  # Give 60 seconds grace period for startup
                
            connection_status = "Connected" if is_connected else "Disconnected"
            
            # Calculate uptime
            uptime_hours = (datetime.now(timezone.utc) - self.start_time).total_seconds() / 3600
            
            # Log health status
            logger.info(f"""━━━━━━ Health Check ━━━━━━
Status: {connection_status}
Memory: {memory:.1f}%
CPU: {cpu:.1f}%
Latency: {self.latency*1000:.2f}ms
Guilds: {len(self.guilds)}
Uptime: {uptime_hours:.1f}h
Error Count: {self.error_count}
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
            # Enhanced health checks
            needs_restart = any([
                memory > 90,
                cpu > 90,
                self.latency > 5,
                not is_connected
            ])
            
            if needs_restart:
                self.error_count += 1
                logger.warning(f"Health check failed (attempt {self.error_count}/5)")
                
                if self.error_count >= 5:
                    logger.error("Critical health check failure - initiating restart")
                    try:
                        # Graceful shutdown
                        await self.close()
                        await asyncio.sleep(5)
                        
                        # Reset error count and reconnect
                        self.error_count = 0
                        token = os.getenv('DISCORD_BOT_TOKEN')
                        if not token:
                            raise ValueError("Discord token not found")
                            
                        # Attempt reconnection
                        await self.login(token)
                        await self.connect()
                        
                        logger.info("Successfully reconnected to Discord")
                    except Exception as e:
                        logger.error(f"Failed to restart bot: {str(e)}")
                        # Force a complete restart
                        os._exit(1)
            else:
                if self.error_count > 0:
                    logger.info("Health check recovered - resetting error count")
                self.error_count = 0
                
        except Exception as e:
            logger.error(f"Health check error: {str(e)}")

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
        if message.author == self.user:
            return
            
        # Generate a unique message ID
        message_id = f"{message.channel.id}:{message.id}"
        if message_id in self._last_processed:
            return
            
        # Check for bot mention or reply
        is_mention = self.user.mentioned_in(message)
        is_reply = message.reference and message.reference.resolved and message.reference.resolved.author == self.user
        
        if is_reply or is_mention:
            try:
                # Track this message as processed
                self._last_processed[message_id] = time.time()
                
                # Clean the message content
                content = message.content
                if is_mention:
                    # Remove the bot mention
                    for mention in message.mentions:
                        if mention == self.user:
                            content = content.replace(f'<@{mention.id}>', '').strip()
                async with message.channel.typing():
                    response = self.chat_handler.get_response(content)
                    
                if isinstance(response, list):
                    for chunk in response:
                        if chunk.strip():
                            await message.reply(chunk.strip())
                else:
                    await message.reply(response.strip())
                    
            except Exception as e:
                logger.error(f"Message handling error: {str(e)}")
                await message.reply("I encountered an error. Please try again.")

    async def on_error(self, event, *args, **kwargs):
        error = sys.exc_info()[1]
        logger.error(f"Error in {event}: {str(error)}")

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
        logger.critical(f"Critical error: {str(e)}")
        sys.exit(1)