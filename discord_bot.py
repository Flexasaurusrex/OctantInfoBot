import os
import sys
import logging
import asyncio
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
    def __init__(self):
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
        """Handle message events."""
        if message.author == self.user:
            return
            
        # Handle bot mentions and replies
        is_mention = self.user.mentioned_in(message)
        is_reply = message.reference and message.reference.resolved and message.reference.resolved.author == self.user
        
        if is_reply or is_mention:
            try:
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

async def main():
    bot = OctantBot()
    
    try:
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            raise ValueError("Discord token not found in environment variables")
        
        logger.info("Starting bot...")
        await bot.start(token)
        
    except Exception as e:
        logger.error(f"Bot error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt - shutting down")
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        sys.exit(1)