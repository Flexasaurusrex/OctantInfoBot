import os
import discord
from discord import app_commands
from discord.ext import commands
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BasicDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix='/',
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        logger.info("Setting up commands...")
        try:
            # Register the basic commands cog
            basic_cog = BasicCommands(self)
            await self.add_cog(basic_cog)
            logger.info("Basic commands cog added")

            # Clear existing commands first
            self.tree.clear_commands(guild=None)
            logger.info("Cleared existing commands")
            
            # Add commands from cogs
            await self.tree.sync()
            logger.info("Commands synced successfully")
            
            # Verify commands were registered
            commands = await self.tree.fetch_commands()
            if not commands:
                logger.error("No commands were registered after sync")
                raise RuntimeError("Failed to register commands")
            logger.info(f"Successfully registered {len(commands)} commands")
            
        except Exception as e:
            logger.error(f"Error in setup: {str(e)}\n{traceback.format_exc()}")
            raise

    async def on_ready(self):
        logger.info(f'Bot Ready: {self.user.name} (ID: {self.user.id})')

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show available commands")
    async def help_command(self, interaction: discord.Interaction):
        """Basic help command"""
        try:
            logger.info(f"Help command invoked by {interaction.user}")
            help_embed = discord.Embed(
                title="Bot Help",
                description="Available Commands:",
                color=discord.Color.blue()
            )
            help_embed.add_field(
                name="Basic Commands",
                value="• `/help` - Show this help message\n• `/trivia` - Start a trivia game",
                inline=False
            )
            
            logger.info("Sending help message...")
            await interaction.response.send_message(embed=help_embed)
            logger.info("Help message sent successfully")
            
        except Exception as e:
            logger.error(f"Error in help command: {str(e)}\n{traceback.format_exc()}")
            try:
                await interaction.response.send_message(
                    "An error occurred while processing your command. Please try again.",
                    ephemeral=True
                )
            except Exception as e2:
                logger.error(f"Failed to send error message: {str(e2)}")

async def main():
    try:
        discord_token = os.environ.get('DISCORD_BOT_TOKEN')
        if not discord_token:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
        
        bot = BasicDiscordBot()
        await bot.start(discord_token)
        
    except Exception as e:
        logger.error(f"Critical error: {str(e)}\n{traceback.format_exc()}")
        raise SystemExit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())