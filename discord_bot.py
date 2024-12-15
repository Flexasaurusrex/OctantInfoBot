
import os
import sys
import random
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
            logger.info("""━━━━━━ Bot Setup Started ━━━━━━
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Memory Usage: {psutil.Process().memory_info().rss / 1024 / 1024:.1f}MB
CPU Usage: {psutil.cpu_percent()}%
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
            # Verify token and application status
            if not self.application_id:
                logger.error("Invalid token detected during setup")
                raise ValueError("Invalid Discord token. Please check your configuration.")
            
            logger.info("Token validated successfully")
            
            # Initialize commands
            logger.info("Registering commands...")
            await self.register_commands()
            logger.info("Commands registered successfully")
            
            # Start health monitoring
            logger.info("Starting health monitoring...")
            self.health_check.start()
            logger.info("Health monitoring activated")
            
            # Final setup verification
            logger.info("""━━━━━━ Setup Complete ━━━━━━
Application ID: {self.application_id}
Shard Count: {self.shard_count if self.shard_count else 'None'}
Command Count: {len(self.tree.get_commands())}
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

    @tasks.loop(seconds=30)
    async def health_check(self):
        """Enhanced health monitoring with connection verification."""
        try:
            memory = psutil.Process().memory_percent()
            cpu = psutil.cpu_percent()
            
            # Check if bot is properly connected
            is_connected = self.is_ready() and hasattr(self, 'user')
            connection_status = "Connected" if is_connected else "Disconnected"
            
            logger.info(f"""━━━━━━ Health Check ━━━━━━
Status: {connection_status}
Memory: {memory:.1f}%
CPU: {cpu:.1f}%
Latency: {self.latency*1000:.2f}ms
Guilds: {len(self.guilds)}
Uptime: {(datetime.now(timezone.utc) - self.start_time).total_seconds()/3600:.1f}h
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
                    await self.close()
                    await asyncio.sleep(5)
                    token = os.getenv('DISCORD_BOT_TOKEN')
                    if not token:
                        raise ValueError("Discord token not found")
                    await self.start(token)
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
        max_retries = 5
        
        while True:
            try:
                # Validate token
                token = os.getenv('DISCORD_BOT_TOKEN')
                if not token:
                    logger.error("DISCORD_BOT_TOKEN not set")
                    raise ValueError("Discord token not found in environment variables")
                
                # Log connection attempt
                logger.info(f"""━━━━━━ Connection Attempt {retry_count + 1} ━━━━━━
Bot Version: 1.0.1
Token Status: Valid
Retry Count: {retry_count}
Max Retries: {max_retries}
━━━━━━━━━━━━━━━━━━━━━━━━""")
                
                # Enhanced connection handling
                try:
                    await bot.start(token)
                except discord.LoginFailure as e:
                    logger.error(f"Login Failed: {str(e)}")
                    raise
                except discord.ConnectionClosed as e:
                    logger.error(f"Connection Closed: {str(e)}")
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
━━━━━━━━━━━━━━━━━━━━━━━━""")
                
                if retry_count >= max_retries:
                    logger.critical("Max retries reached - shutting down")
                    sys.exit(1)
                    
                wait_time = min(30, 2 ** retry_count)  # Exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
                continue
                
            finally:
                # Cleanup on exit
                if hasattr(bot, 'is_closed') and not bot.is_closed():
                    await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt - shutting down")
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}")
        sys.exit(1)
