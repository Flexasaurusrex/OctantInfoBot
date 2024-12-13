import discord
from discord.ext import commands
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
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=f"{option_key}. {option_value}",
            custom_id=f"trivia_{option_key}"
        )
        self.option_key = option_key

    async def callback(self, interaction: discord.Interaction):
        try:
            view = self.view
            if isinstance(view, TriviaView):
                if view.answered:
                    await interaction.response.send_message(
                        "This question has already been answered!",
                        ephemeral=True
                    )
                    return
                await view.handle_answer(interaction, self.option_key)
        except Exception as e:
            logger.error(f"Error in button callback: {str(e)}")
            await interaction.response.send_message(
                "❌ There was an error processing your answer. Please try again.",
                ephemeral=True
            )

class TriviaView(discord.ui.View):
    def __init__(self, trivia_game, question_data: dict):
        super().__init__(timeout=120)  # 2 minute timeout
        self.trivia_game = trivia_game
        self.question = question_data
        self.answered = False
        self.message = None

        # Add buttons for each option
        for key, value in question_data['options'].items():
            button = TriviaButton(key, value)
            self.add_item(button)

    async def on_timeout(self):
        """Handle timeout when no answer is received."""
        if self.message and not self.answered:
            try:
                # Disable all buttons
                for item in self.children:
                    item.disabled = True
                
                timeout_embed = discord.Embed(
                    title="⏰ Time's Up!",
                    description=(
                        f"You took too long to answer!\n\n"
                        f"The correct answer was:\n"
                        f"✅ {self.question['correct']}: {self.question['options'][self.question['correct']]}"
                    ),
                    color=discord.Color.orange()
                )
                timeout_embed.add_field(
                    name="📚 Explanation",
                    value=self.question['explanation'],
                    inline=False
                )
                
                await self.message.edit(embed=timeout_embed, view=self)
                
            except Exception as e:
                logger.error(f"Error handling timeout: {str(e)}")

    async def handle_answer(self, interaction: discord.Interaction, answer: str):
        """Handle user's answer selection."""
        try:
            if self.answered:
                await interaction.response.send_message(
                    "This question has already been answered!",
                    ephemeral=True
                )
                return

            self.answered = True
            await self.trivia_game.handle_answer(interaction, answer)

            # Update button states
            for child in self.children:
                if isinstance(child, TriviaButton):
                    child.disabled = True
                    if child.option_key == self.question['correct']:
                        child.style = discord.ButtonStyle.success
                    elif child.option_key == answer and answer != self.question['correct']:
                        child.style = discord.ButtonStyle.danger

            await interaction.message.edit(view=self)

        except Exception as e:
            logger.error(f"Error in handle_answer: {str(e)}")
            await interaction.response.send_message(
                "❌ There was an error processing your answer. Please try again.",
                ephemeral=True
            )

class DiscordTrivia:
    def __init__(self):
        """Initialize the Discord trivia game with questions."""
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
                "explanation": "A maximum funding cap of 20% of the total Matched Rewards fund ensures balanced distribution."
            }
        ]
        self.current_games = {}  # Store game state per channel
        self.logger = logging.getLogger(__name__)

    async def start_game(self, ctx: commands.Context):
        """Start a new trivia game in a channel."""
        channel_id = ctx.channel.id
        
        try:
            # Check for existing game
            if channel_id in self.current_games:
                game_state = self.current_games[channel_id]
                current_q = game_state['questions_asked'] + 1
                total_q = len(self.questions)
                
                existing_game_embed = discord.Embed(
                    title="❗ Game Already in Progress",
                    description=(
                        f"A trivia game is already active in this channel!\n"
                        f"Currently on question {current_q}/{total_q}\n\n"
                        "Options:\n"
                        "• Wait for current game to finish\n"
                        "• Type `end trivia` to end the current game\n"
                        "• Join the current game by answering questions"
                    ),
                    color=discord.Color.yellow()
                )
                existing_game_embed.set_footer(text="Only one game can run per channel at a time")
                await ctx.send(embed=existing_game_embed)
                return

            # Initialize new game state
            self.current_games[channel_id] = {
                'score': 0,
                'questions_asked': 0,
                'current_question': None,
                'start_time': discord.utils.utcnow(),
                'last_activity': discord.utils.utcnow(),
                'participants': set(),
                'answered': False,
                'questions': self.questions.copy()  # Make a copy of questions for this game
            }

            # Send welcome message
            welcome_embed = discord.Embed(
                title="🎮 Welcome to Octant Trivia! 🎮",
                description=(
                    "Test your knowledge about Octant's ecosystem and earn points!\n\n"
                    "**📋 Game Rules:**\n"
                    "• Use the buttons below to answer questions\n"
                    "• Each correct answer earns you points\n"
                    "• Learn interesting facts about Octant\n"
                    "• The game has multiple questions\n"
                    "• Try to get the highest score!\n\n"
                    "**🎯 Scoring:**\n"
                    "• Correct Answer: +1 point\n"
                    "• Wrong Answer: 0 points\n\n"
                    "Get ready for your first question..."
                ),
                color=discord.Color.blue()
            )
            welcome_embed.set_footer(text="Your first question will appear in 3 seconds...")
            
            await ctx.send(embed=welcome_embed)
            await asyncio.sleep(3)  # Brief pause for readability
            
            # Start with first question
            await self.send_next_question(ctx)

        except Exception as e:
            self.logger.error(f"Error starting game: {str(e)}")
            if channel_id in self.current_games:
                del self.current_games[channel_id]
            error_embed = discord.Embed(
                title="❌ Error",
                description="There was an error starting the game. Please try again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)

    async def send_next_question(self, ctx: commands.Context):
        """Send the next question to the channel."""
        try:
            channel_id = ctx.channel.id
            game = self.current_games.get(channel_id)

            if not game:
                error_embed = discord.Embed(
                    title="❌ No Active Game",
                    description="No active game found! Start a new game with `/trivia`",
                    color=discord.Color.red()
                )
                await ctx.send(embed=error_embed)
                return

            if game['questions_asked'] >= len(self.questions):
                # Game finished
                score = game['score']
                percentage = (score / len(self.questions)) * 100
                duration = discord.utils.utcnow() - game['start_time']
                minutes = duration.seconds // 60
                seconds = duration.seconds % 60
                
                final_embed = discord.Embed(
                    title="🎮 Game Complete! 🎮",
                    color=discord.Color.green() if percentage >= 60 else discord.Color.blue()
                )
                
                final_embed.add_field(
                    name="📊 Final Score",
                    value=f"{score}/{len(self.questions)} ({percentage:.1f}%)",
                    inline=False
                )
                
                final_embed.add_field(
                    name="⏱️ Time Taken",
                    value=f"{minutes}m {seconds}s",
                    inline=True
                )
                
                rating = "🌟 Expert!" if percentage >= 80 else "👏 Well Done!" if percentage >= 60 else "📚 Keep Learning!"
                final_embed.add_field(
                    name="🏆 Rating",
                    value=rating,
                    inline=True
                )
                
                final_embed.set_footer(text="Type /trivia to play again!")
                
                await ctx.send(embed=final_embed)
                del self.current_games[channel_id]
                return

            # Get next question
            question = self.questions[game['questions_asked']]
            game['current_question'] = question

            # Create embed for question
            question_embed = discord.Embed(
                title=f"🎯 Question {game['questions_asked'] + 1}/{len(self.questions)}",
                description=f"━━━━━━━━━━━━━━━━━━━━━━━\n\n📝 {question['question']}",
                color=discord.Color.blue()
            )

            # Add score if not first question
            if game['questions_asked'] > 0:
                score_percentage = (game['score'] / game['questions_asked']) * 100
                question_embed.add_field(
                    name="📊 Current Score",
                    value=f"{game['score']}/{game['questions_asked']} ({score_percentage:.1f}%)",
                    inline=False
                )

            try:
                view = TriviaView(self, question)
                message = await ctx.send(embed=question_embed, view=view)
                view.message = message
            except Exception as e:
                self.logger.error(f"Error sending question: {str(e)}")
                error_embed = discord.Embed(
                    title="❌ Error",
                    description="There was an error displaying the question. Please try again.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=error_embed)
                if channel_id in self.current_games:
                    del self.current_games[channel_id]

        except Exception as e:
            self.logger.error(f"Error in send_next_question: {str(e)}")
            await ctx.send(
                embed=discord.Embed(
                    title="❌ Error",
                    description="There was an error sending the next question. The game has been reset.",
                    color=discord.Color.red()
                )
            )
            if channel_id in self.current_games:
                del self.current_games[channel_id]

    async def handle_answer(self, interaction: discord.Interaction, answer: str):
        """Handle user's answer selection."""
        try:
            channel_id = interaction.channel.id
            game = self.current_games.get(channel_id)

            if not game or not game['current_question']:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="❌ No Active Game",
                        description="No active game found! Start a new game with `/trivia`",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return

            # Prevent multiple answers to the same question
            if game.get('answered', False):
                await interaction.response.send_message(
                    "This question has already been answered!",
                    ephemeral=True
                )
                return

            game['answered'] = True
            question = game['current_question']
            is_correct = answer == question['correct']
            
            if is_correct:
                game['score'] += 1

            game['questions_asked'] += 1
            game['participants'].add(interaction.user.id)
            game['last_activity'] = discord.utils.utcnow()

            # Create embed for answer result
            score_percentage = (game['score'] / game['questions_asked']) * 100
            result_embed = discord.Embed(
                title="✨ Correct! Brilliant answer! ✨" if is_correct else "❌ Not quite right!",
                description=f"You chose: {answer}. {question['options'][answer]}",
                color=discord.Color.green() if is_correct else discord.Color.red()
            )

            if not is_correct:
                result_embed.add_field(
                    name="✅ Correct Answer",
                    value=f"{question['correct']}: {question['options'][question['correct']]}",
                    inline=False
                )

            result_embed.add_field(
                name="📚 Learn More",
                value=question['explanation'],
                inline=False
            )

            result_embed.add_field(
                name="🎯 Score",
                value=f"{game['score']}/{game['questions_asked']} ({score_percentage:.1f}%)",
                inline=False
            )

            await interaction.response.send_message(embed=result_embed)
            
            # Send next question after a brief pause
            if game['questions_asked'] < len(self.questions):
                await asyncio.sleep(3)
                game['answered'] = False  # Reset answered state for next question
                ctx = await interaction.client.get_context(interaction.message)
                await self.send_next_question(ctx)
            else:
                # Game is complete, show final score
                await self.end_game(ctx)

        except Exception as e:
            self.logger.error(f"Error handling answer: {str(e)}")
            error_embed = discord.Embed(
                title="❌ Error",
                description="There was an error processing your answer. The game has been reset.",
                color=discord.Color.red()
            )
            try:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            except discord.errors.InteractionResponded:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            finally:
                if channel_id in self.current_games:
                    del self.current_games[channel_id]
