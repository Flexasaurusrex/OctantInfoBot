import os
import sys
import logging
import fcntl
import asyncio
import signal
import discord
from discord import app_commands
from discord.ext import commands
from chat_handler import ChatHandler
from discord_trivia import DiscordTrivia

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
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(OctantBot, cls).__new__(cls)
        return cls._instance

    async def ensure_single_instance(self):
        """Ensure only one instance of the bot is running using file-based locking."""
        pid_file = 'discord_bot.lock'
        self._lock_fd = None
        
        # Force cleanup any existing instances
        await self.cleanup_existing_instances()
        
        try:
            # Create new lock file with exclusive access
            self._lock_fd = os.open(pid_file, os.O_CREAT | os.O_RDWR)
            
            try:
                # Try to acquire an exclusive lock
                fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                
                # Write current PID to lock file and flush immediately
                current_pid = str(os.getpid())
                os.write(self._lock_fd, current_pid.encode())
                os.fsync(self._lock_fd)
                
                logger.info(f"""━━━━━━ Bot Instance Lock ━━━━━━
Instance PID: {current_pid}
Lock File: {pid_file}
Status: Lock acquired successfully
━━━━━━━━━━━━━━━━━━━━━━━━""")
                return True
                
            except BlockingIOError:
                try:
                    # Read PID of the running instance
                    os.lseek(self._lock_fd, 0, os.SEEK_SET)
                    existing_pid = int(os.read(self._lock_fd, 32).decode().strip())
                    logger.error(f"Another bot instance is running (PID: {existing_pid})")
                except (ValueError, OSError) as e:
                    logger.error(f"Error reading existing PID: {e}")
                
                if self._lock_fd is not None:
                    os.close(self._lock_fd)
                    self._lock_fd = None
                return False
                
        except (OSError, IOError) as e:
            logger.error(f"Failed to create/acquire lock file: {e}")
            if self._lock_fd is not None:
                try:
                    os.close(self._lock_fd)
                    self._lock_fd = None
                except OSError:
                    pass
            return False
            
    async def cleanup_existing_instances(self):
        """Force cleanup of any existing bot instances."""
        pid_file = 'discord_bot.lock'
        
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    old_pid = int(f.read().strip())
                    
                    try:
                        # Check if process exists and terminate it
                        os.kill(old_pid, signal.SIGTERM)
                        logger.info(f"Sent termination signal to existing instance (PID: {old_pid})")
                        
                        # Wait for process to terminate
                        for _ in range(5):  # Wait up to 5 seconds
                            await asyncio.sleep(1)
                            try:
                                os.kill(old_pid, 0)
                            except OSError:
                                break
                        else:
                            # Force kill if still running
                            try:
                                os.kill(old_pid, signal.SIGKILL)
                                logger.info(f"Force killed existing instance (PID: {old_pid})")
                            except OSError:
                                pass
                                
                    except OSError:
                        logger.info(f"No running instance found for PID: {old_pid}")
                        
            except (ValueError, OSError) as e:
                logger.info(f"Invalid lock file found: {e}")
                
            try:
                os.remove(pid_file)
                logger.info("Removed existing lock file")
            except OSError as e:
                logger.error(f"Error removing lock file: {e}")

    def __init__(self):
        if hasattr(self, 'is_initialized'):
            return
            
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='/',
            intents=intents,
            activity=discord.Activity(type=discord.ActivityType.watching, name="/help for commands")
        )
        
        self.chat_handler = ChatHandler()
        self.trivia = DiscordTrivia()
        self.is_initialized = True
        
        # Remove default help
        self.remove_command('help')
        
    async def setup_hook(self):
        """Setup bot commands and configuration."""
        try:
            logger.info("Initializing Discord bot...")
            await self.register_commands()
            logger.info("Commands registered successfully")
            
        except Exception as e:
            logger.error(f"Setup error: {str(e)}")
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

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"""━━━━━━ Bot Ready ━━━━━━
Logged in as: {self.user.name}
Bot ID: {self.user.id}
Guilds connected: {len(self.guilds)}
━━━━━━━━━━━━━━━━━━━━━━━━""")

    async def on_message(self, message):
        """Handle message events with enhanced thread safety and deduplication."""
        if message.author == self.user:  # Skip self messages immediately
            return

        message_id = str(message.id)
        
        # Initialize thread-safe message cache if needed
        if not hasattr(self, '_message_lock'):
            self._message_lock = asyncio.Lock()
            self._processed_messages = set()
            self._response_cache = {}
            self._last_cleanup = asyncio.get_event_loop().time()
            logger.info("Initialized message tracking system")

        # Early validation before lock
        is_mention = self.user.mentioned_in(message)
        is_reply = (message.reference and 
                   message.reference.resolved and 
                   message.reference.resolved.author == self.user)

        if not (is_mention or is_reply):
            return

        try:
            # Acquire lock for message processing
            async with self._message_lock:
                # Double-check message hasn't been processed
                if message_id in self._processed_messages:
                    logger.debug(f"Skipping duplicate message {message_id}")
                    return

                # Mark message as processed immediately
                self._processed_messages.add(message_id)
                logger.info(f"Processing message {message_id}")

            # Clean message content outside lock
            content = message.content.strip()
            if is_mention:
                for mention_format in [f'<@{self.user.id}>', f'<@!{self.user.id}>', 
                                     self.user.name, f'@{self.user.name}']:
                    content = content.replace(mention_format, '').strip()

            # Process message with timeout protection
            try:
                async with message.channel.typing():
                    # Check if we've already responded to this message
                    async with self._message_lock:
                        if message_id in self._response_cache:
                            logger.info(f"Skipping duplicate response for message {message_id}")
                            return

                    # Generate a unique socket ID for Discord messages
                    discord_socket_id = f"discord_{message.author.id}_{message.id}"
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.chat_handler.get_response,
                            discord_socket_id,
                            content
                        ),
                        timeout=30.0
                    )

                    if response:
                        # Format response
                        # Clean up response text and normalize
                        if isinstance(response, list):
                            response_text = '\n'.join(chunk.strip() for chunk in response if chunk)
                        else:
                            response_text = response.strip()
                                
                        # Remove 'Answer:' prefix if present
                        if response_text.lower().startswith('answer:'):
                            response_text = response_text[7:].strip()

                        # Only send response if we have text
                        if response_text:
                            # Send response and track it immediately
                            sent_message = await message.reply(response_text)
                            async with self._message_lock:
                                self._response_cache[message_id] = sent_message.id
                            logger.info(f"Response {sent_message.id} sent for message {message_id}")

                    else:
                        logger.warning(f"Empty response for message {message_id}")

            except asyncio.TimeoutError:
                logger.error(f"Response timeout for message {message_id}")
                await message.reply("Sorry, I took too long to respond. Please try again.")
                
            except Exception as e:
                logger.error(f"Response error: {str(e)}", exc_info=True)
                await message.reply("I encountered an error. Please try again.")

            # Cleanup old messages periodically
            await self._cleanup_old_messages()

        except Exception as e:
            logger.error(f"Critical error processing message {message_id}: {str(e)}", exc_info=True)

    async def _cleanup_old_messages(self):
        """Clean up old processed messages to prevent memory leaks."""
        try:
            async with self._message_lock:
                current_time = asyncio.get_event_loop().time()
                if current_time - self._last_cleanup > 3600:  # Cleanup every hour
                    self._processed_messages.clear()
                    self._response_cache.clear()
                    self._last_cleanup = current_time
                    logger.info("Message cache cleaned")
        except Exception as e:
            logger.error(f"Cache cleanup error: {str(e)}")

    async def _cleanup_cache(self):
        """Clean up message cache periodically."""
        try:
            current_time = asyncio.get_event_loop().time()
            if (current_time - self.__class__._message_cache['last_cleanup'] > 3600 or 
                len(self.__class__._message_cache['processed']) > 10000):
                
                self.__class__._message_cache['processed'].clear()
                self.__class__._message_cache['responses'].clear()
                self.__class__._message_cache['last_cleanup'] = current_time
                logger.info("Cache cleaned up")
        except Exception as e:
            logger.error(f"Cache cleanup error: {str(e)}")

        finally:
            # 10. Periodic cache cleanup with size limit
            try:
                current_time = asyncio.get_event_loop().time()
                if (current_time - OctantBot._message_cache['last_cleanup'] > 3600 or 
                    len(OctantBot._message_cache['processed']) > 10000):
                    
                    OctantBot._message_cache['processed'].clear()
                    OctantBot._message_cache['responses'].clear()
                    OctantBot._message_cache['last_cleanup'] = current_time
                    logger.info("Cleared message cache")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up message cache: {str(cleanup_error)}")


async def main():
    bot = None
    try:
        bot = OctantBot()
        
        # Ensure single instance
        if not await bot.ensure_single_instance():
            logger.error("Another bot instance is already running")
            sys.exit(1)
        
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            raise ValueError("Discord token not found in environment variables")
        
        logger.info("Starting bot...")
        
        # Setup signal handlers for graceful shutdown
        def signal_handler():
            asyncio.create_task(cleanup(bot))
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop = asyncio.get_event_loop()
            loop.add_signal_handler(sig, signal_handler)
        
        await bot.start(token)
        
    except Exception as e:
        logger.error(f"Bot error: {str(e)}")
        if bot:
            await cleanup(bot)
        sys.exit(1)

async def cleanup(bot):
    """Cleanup function to handle graceful shutdown"""
    logger.info("━━━━━━ Starting Cleanup ━━━━━━")
    
    if not bot:
        logger.warning("No bot instance provided for cleanup")
        return
        
    try:
        # Close Discord connection
        try:
            await bot.close()
            logger.info("Discord connection closed")
        except Exception as e:
            logger.error(f"Error closing Discord connection: {e}")
            
        # Release file lock
        if hasattr(bot, '_lock_fd') and bot._lock_fd is not None:
            try:
                fcntl.flock(bot._lock_fd, fcntl.LOCK_UN)
                os.close(bot._lock_fd)
                bot._lock_fd = None
                logger.info("File lock released")
            except Exception as e:
                logger.error(f"Error releasing file lock: {e}")
                
        # Remove lock file
        try:
            if os.path.exists('discord_bot.lock'):
                os.remove('discord_bot.lock')
                logger.info("Lock file removed")
        except Exception as e:
            logger.error(f"Error removing lock file: {e}")
            
        logger.info("Cleanup completed successfully")
        
    except Exception as e:
        logger.error(f"Critical error during cleanup: {e}")
        
    finally:
        logger.info("━━━━━━ Cleanup Finished ━━━━━━")

if __name__ == "__main__":
    try:
        # Add signal module import
        import signal
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt - shutting down")
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        sys.exit(1)