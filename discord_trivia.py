import discord
from discord.ext import commands
import random
import logging
import asyncio
from typing import Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TriviaButton(discord.ui.Button):
    def __init__(self, option_key: str, option_value: str):
        # Use Discord's button styles
        style_map = {
            'A': discord.ButtonStyle.primary,
            'B': discord.ButtonStyle.primary,
            'C': discord.ButtonStyle.primary,
            'D': discord.ButtonStyle.primary
        }
        super().__init__(
            style=style_map.get(option_key, discord.ButtonStyle.primary),
            label=f"{option_key}. {option_value}",
            custom_id=f"trivia_{option_key}"
        )
        self.option_key = option_key

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if isinstance(view, TriviaView):
            await view.handle_answer(interaction, self.option_key)

class TriviaView(discord.ui.View):
    def __init__(self, trivia_game, question_data: dict):
        super().__init__(timeout=300)  # 5 minute timeout
        self.trivia_game = trivia_game
        self.question = question_data
        self.answered = False

        # Add buttons for each option
        for key, value in question_data['options'].items():
            button = TriviaButton(key, value)
            self.add_item(button)

    async def handle_answer(self, interaction: discord.Interaction, answer: str):
        try:
            if self.answered:
                await interaction.response.send_message(
                    "This question has already been answered!",
                    ephemeral=True
                )
                return

            self.answered = True
            is_correct = answer == self.question['correct']
            
            # Update button styles to show correct/incorrect answers
            for child in self.children:
                if isinstance(child, TriviaButton):
                    child.disabled = True
                    if child.option_key == self.question['correct']:
                        child.style = discord.ButtonStyle.success
                    elif child.option_key == answer and not is_correct:
                        child.style = discord.ButtonStyle.danger

            try:
                await interaction.response.edit_message(view=self)
            except discord.errors.InteractionResponded:
                await interaction.message.edit(view=self)

            await self.trivia_game.handle_answer(interaction, answer)

        except Exception as e:
            logger.error(f"Error in TriviaView handle_answer: {str(e)}")
            try:
                await interaction.response.send_message("An error occurred processing your answer. Please try again.", ephemeral=True)
            except discord.errors.InteractionResponded:
                await interaction.followup.send("An error occurred processing your answer. Please try again.", ephemeral=True)

class DiscordTrivia:
    def __init__(self):
        self.questions = [
            {
                "question": "What is the minimum effective GLM balance required for user rewards?",
                "options": {
                    "A": "10 GLM",
                    "B": "50 GLM",
                    "C": "100 GLM",
                    "D": "500 GLM"
                },
                "correct": "C",
                "explanation": "While you can lock as little as 1 GLM, a minimum effective balance of 100 GLM is required to qualify for user rewards."
            },
            {
                "question": "How long is an Octant epoch?",
                "options": {
                    "A": "30 days",
                    "B": "60 days",
                    "C": "90 days",
                    "D": "120 days"
                },
                "correct": "C",
                "explanation": "Each Octant epoch lasts 90 days, followed by a two-week allocation window where users can claim rewards or donate to projects."
            },
            {
                "question": "What is the maximum funding cap for a single project from the Matched Rewards pool?",
                "options": {
                    "A": "10%",
                    "B": "15%",
                    "C": "20%",
                    "D": "25%"
                },
                "correct": "C",
                "explanation": "A maximum funding cap of 20% ensures balanced distribution. Users can still donate to projects at the cap, but these won't receive additional matching."
            }
        ]
        self.current_games = {}  # Store game state per channel

    async def start_game(self, ctx: commands.Context):
        """Start a new trivia game in a channel."""
        channel_id = ctx.channel.id
        
        # Check for existing game
        if channel_id in self.current_games:
            await ctx.send("❗ There's already an active trivia game in this channel!")
            return

        # Initialize new game
        self.current_games[channel_id] = {
            'score': 0,
            'questions_asked': 0,
            'current_question': None
        }

        # Create welcome message
        welcome_msg = (
            "🎮 **Octant Trivia Time!**\n\n"
            "Test your knowledge about Octant!\n"
            "• Click the buttons to answer\n"
            "• Learn as you play\n\n"
            "*Get ready...*"
        )
        
        try:
            await ctx.send(welcome_msg)
            await asyncio.sleep(2)  # Brief pause for readability
            await self.send_next_question(ctx)
        except Exception as e:
            logger.error(f"Error starting game: {str(e)}")
            del self.current_games[channel_id]  # Cleanup on error
            await ctx.send("❌ There was an error starting the game. Please try again.")

    async def send_next_question(self, ctx: commands.Context):
        """Send the next question to the channel."""
        channel_id = ctx.channel.id
        game = self.current_games.get(channel_id)

        if not game:
            await ctx.send("❗ No active game found! Start a new game with `/trivia`")
            return

        if game['questions_asked'] >= len(self.questions):
            # Game finished
            score = game['score']
            percentage = (score / len(self.questions)) * 100
            
            final_msg = (
                "🎮 **Game Complete!**\n\n"
                f"📊 Final Score: {score}/{len(self.questions)} ({percentage:.1f}%)\n\n"
                f"{('🌟 Expert Level!' if percentage >= 80 else '👏 Well Done!' if percentage >= 60 else '📚 Keep Learning!')}\n\n"
                "Want to play again? Use /trivia"
            )
            
            await ctx.send(final_msg)
            del self.current_games[channel_id]
            return

        # Get next question
        question = self.questions[game['questions_asked']]
        game['current_question'] = question

        # Format question message
        question_msg = (
            f"❓ **Question {game['questions_asked'] + 1}/{len(self.questions)}**\n\n"
            f"{question['question']}\n"
        )
        
        # Add score only for questions after the first one, with better formatting
        if game['questions_asked'] > 0:
            score_percentage = (game['score'] / game['questions_asked']) * 100
            question_msg += f"\n📊 Score so far: {game['score']}/{game['questions_asked']} ({score_percentage:.1f}%)"

        try:
            # Create view with buttons and send
            view = TriviaView(self, question)
            await ctx.send(question_msg, view=view)
        except Exception as e:
            logger.error(f"Error sending question: {str(e)}")
            await ctx.send("❌ There was an error displaying the question. Please try again.")
            del self.current_games[channel_id]  # Cleanup on error

    async def handle_answer(self, interaction: discord.Interaction, answer: str):
        """Handle user's answer selection."""
        channel_id = interaction.channel.id
        game = self.current_games.get(channel_id)

        if not game or not game['current_question']:
            await interaction.response.send_message(
                "❗ No active game found! Start a new game with `/trivia`",
                ephemeral=True
            )
            return

        question = game['current_question']
        is_correct = answer == question['correct']
        
        if is_correct:
            game['score'] += 1

        # Update game state
        game['questions_asked'] += 1

        try:
            # Format result message
            score_percentage = (game['score'] / game['questions_asked']) * 100
            if is_correct:
                result_msg = (
                    "✅ **Correct!**\n\n"
                    f"📚 {question['explanation']}\n\n"
                    f"🎯 Current Score: {game['score']}/{game['questions_asked']} ({score_percentage:.1f}%)"
                )
            else:
                result_msg = (
                    "❌ **Incorrect**\n\n"
                    f"✅ Correct answer: {question['correct']} - {question['options'][question['correct']]}\n\n"
                    f"📚 {question['explanation']}\n\n"
                    f"🎯 Current Score: {game['score']}/{game['questions_asked']} ({score_percentage:.1f}%)"
                )

            # Send result and queue next question
            await interaction.response.send_message(result_msg)
            
            if game['questions_asked'] < len(self.questions):
                await asyncio.sleep(3)
                ctx = await interaction.client.get_context(interaction.message)
                await self.send_next_question(ctx)

        except Exception as e:
            logger.error(f"Error handling answer: {str(e)}")
            await interaction.response.send_message(
                "❌ There was an error processing your answer. Please try again.",
                ephemeral=True
            )
            del self.current_games[channel_id]  # Cleanup on error