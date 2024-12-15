
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
        await self.register_commands()
        self.health_check.start()
        
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
        try:
            memory = psutil.Process().memory_percent()
            cpu = psutil.cpu_percent()
            
            logger.info(f"""━━━━━━ Health Check ━━━━━━
Memory: {memory:.1f}%
CPU: {cpu:.1f}%
Latency: {self.latency*1000:.2f}ms
Guilds: {len(self.guilds)}
Uptime: {(datetime.now(timezone.utc) - self.start_time).total_seconds()/3600:.1f}h
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
            if memory > 90 or cpu > 90 or self.latency > 5:
                self.error_count += 1
                if self.error_count >= 5:
                    await self.close()
                    await asyncio.sleep(5)
                    await self.start(os.getenv('DISCORD_BOT_TOKEN'))
            else:
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
            
        # Generate a unique message ID that includes message content
        message_id = f"{message.channel.id}:{message.id}:{message.content}"
        
        # Skip if message was recently processed (within last 5 seconds)
        current_time = time.time()
        if message_id in self._last_processed:
            last_time = self._last_processed[message_id]
            if current_time - last_time < 5:
                return
                
        # Check for bot mention or reply
        is_mention = self.user.mentioned_in(message)
        is_reply = message.reference and message.reference.resolved and message.reference.resolved.author == self.user
        
        # Only process if either mentioned or replied to, not both
        if is_mention and is_reply:
            return
        
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
    
    while True:
        try:
            token = os.getenv('DISCORD_BOT_TOKEN')
            if not token:
                raise ValueError("DISCORD_BOT_TOKEN not set")
                
            await bot.start(token)
            
        except Exception as e:
            logger.error(f"Bot error: {str(e)}")
            await asyncio.sleep(5)
            continue

if __name__ == "__main__":
    asyncio.run(main())
