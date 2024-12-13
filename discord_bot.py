import os
import discord
from discord import app_commands
from discord.ext import commands
from chat_handler import ChatHandler
from discord_trivia import DiscordTrivia
import logging
import asyncio
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OctantDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='/',
            intents=intents,
            help_command=None
        )
        
        self.chat_handler = ChatHandler()
        self.trivia = DiscordTrivia()
        
    async def setup_hook(self):
        """Setup hook for the bot."""
        try:
            logger.info("Bot is setting up...")
            # Add the cog
            await self.add_cog(TriviaCog(self))
            # Sync the command tree globally
            await self.tree.sync(guild=None)
            logger.info("Command tree synced globally")
            
            # Log all registered commands
            commands = await self.tree.fetch_commands()
            logger.info(f"Registered commands: {[cmd.name for cmd in commands]}")
        except Exception as e:
            logger.error(f"Error in setup_hook: {str(e)}\n{traceback.format_exc()}")
            raise

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info('=' * 50)
        logger.info(f'Bot Ready: {self.user.name} (ID: {self.user.id})')
        logger.info(f'Discord.py Version: {discord.__version__}')
        logger.info(f'Connected to {len(self.guilds)} guilds')
        logger.info(f'Command tree synced and operational')
        logger.info(f'Trivia system initialized')
        logger.info('=' * 50)
        
        # Set custom status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name="/trivia | Octant Quiz"
            )
        )

class TriviaCog(commands.Cog):
    def __init__(self, bot: OctantDiscordBot):
        self.bot = bot
        
    async def cog_command_error(self, ctx: discord.Interaction, error: Exception):
        """Handle errors in cog commands."""
        logger.error(f"Error in cog command: {str(error)}\n{traceback.format_exc()}")
        try:
            if not ctx.response.is_done():
                await ctx.response.send_message(
                    "An error occurred while processing your command. Please try again.",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error sending error message: {str(e)}")
        
    @app_commands.command(name="trivia", description="Start a trivia game about Octant")
    @app_commands.guild_only()
    async def trivia_command(self, interaction: discord.Interaction):
        """Start a trivia game"""
        try:
            logger.info(f"Starting trivia game for {interaction.user.name} in channel {interaction.channel.name}")
            
            # Check permissions
            if not interaction.channel.permissions_for(interaction.guild.me).send_messages:
                await interaction.response.send_message(
                    "I need permission to send messages in this channel!",
                    ephemeral=True
                )
                return
                
            if not interaction.channel.permissions_for(interaction.guild.me).embed_links:
                await interaction.response.send_message(
                    "I need permission to send embeds in this channel!",
                    ephemeral=True
                )
                return

            # Send initial response
            embed = discord.Embed(
                title="🎮 Starting Trivia Game",
                description="Preparing your game... Please wait!",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
            
            try:
                # Start the game
                await self.bot.trivia.start_game(interaction)
                logger.info(f"Successfully started game for {interaction.user.name}")
            except Exception as game_error:
                logger.error(f"Error starting game: {str(game_error)}\n{traceback.format_exc()}")
                await interaction.followup.send(
                    "An error occurred while setting up the game. Please try again.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error in trivia command: {str(e)}\n{traceback.format_exc()}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An error occurred. Please try again.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "An error occurred. Please try again.",
                        ephemeral=True
                    )
            except Exception as response_error:
                logger.error(f"Error sending error message: {str(response_error)}")

    @app_commands.command(name="help", description="Show available commands and how to play")
    async def help_command(self, interaction: discord.Interaction):
        """Show help message"""
        try:
            help_embed = discord.Embed(
                title="📚 Octant Trivia Bot Help",
                description="Test your knowledge about Octant with our interactive trivia game!",
                color=discord.Color.blue()
            )
            
            help_embed.add_field(
                name="🎮 Game Commands",
                value="• `/trivia` - Start a new trivia game\n• `/help` - Show this help message",
                inline=False
            )
            
            help_embed.add_field(
                name="📋 How to Play",
                value=(
                    "1. Use `/trivia` to start a game\n"
                    "2. Questions will appear with multiple choice answers\n"
                    "3. Click the buttons to select your answer\n"
                    "4. Try to get the highest score!"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=help_embed)
            
        except Exception as e:
            logger.error(f"Error in help command: {str(e)}\n{traceback.format_exc()}")
            await interaction.response.send_message(
                "An error occurred while showing help. Please try again.",
                ephemeral=True
            )

async def main():
    try:
        bot = OctantDiscordBot()
        
        discord_token = os.environ.get('DISCORD_BOT_TOKEN')
        if not discord_token:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
            
        await bot.start(discord_token)
            
    except Exception as e:
        logger.error(f"Critical error in main: {str(e)}\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
