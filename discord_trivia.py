import discord
from discord.ui import Button, View
import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)

class TriviaButton(Button):
    def __init__(self, option: str, label: str, trivia_view: 'TriviaView'):
        """Initialize a trivia button."""
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=f"{option}. {label}",
            custom_id=f"trivia_{option}"
        )
        self.correct_option = None
        self.trivia_view = trivia_view
        self.option = option

    async def callback(self, interaction: discord.Interaction):
        """Handle button press."""
        if self.trivia_view.answered:
            await interaction.response.send_message(
                "This question has already been answered!",
                ephemeral=True
            )
            return

        self.trivia_view.answered = True
        is_correct = self.option == self.trivia_view.correct_answer

        # Update button styles
        for child in self.trivia_view.children:
            child.disabled = True
            if child.option == self.trivia_view.correct_answer:
                child.style = discord.ButtonStyle.success
            elif child.custom_id == self.custom_id and not is_correct:
                child.style = discord.ButtonStyle.danger

        # Update game state
        if is_correct:
            self.trivia_view.trivia_game.score += 1
            title = "✅ Correct!"
            color = discord.Color.green()
        else:
            title = f"❌ Incorrect! The correct answer was: {self.trivia_view.correct_answer}"
            color = discord.Color.red()

        # Create response embed
        embed = discord.Embed(
            title=title,
            description=self.trivia_view.explanation,
            color=color
        )
        
        score = self.trivia_view.trivia_game.score
        questions_asked = len(self.trivia_view.trivia_game.asked_questions)
        embed.add_field(
            name="Score",
            value=f"{score}/{questions_asked} ({(score/questions_asked*100):.1f}%)"
        )

        # Send response and update message
        await interaction.response.edit_message(view=self.trivia_view)
        await interaction.followup.send(embed=embed)
        
        # Send next question
        await self.trivia_view.trivia_game.send_next_question(interaction)

class TriviaView(View):
    def __init__(self, trivia_game: 'DiscordTrivia', question: dict):
        """Initialize the trivia view with buttons."""
        super().__init__(timeout=30.0)
        self.trivia_game = trivia_game
        self.answered = False
        self.correct_answer = question['correct']
        self.explanation = question['explanation']
        
        # Add buttons for each option
        for option, text in question['options'].items():
            button = TriviaButton(option=option, label=text, trivia_view=self)
            self.add_item(button)

class DiscordTrivia:
    def __init__(self):
        """Initialize trivia game with questions."""
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
                "explanation": "A minimum effective balance of 100 GLM is required to qualify for user rewards."
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
                "explanation": "Each Octant epoch lasts 90 days, followed by a two-week allocation window."
            },
            {
                "question": "What percentage of Octant's rewards goes to foundation operations?",
                "options": {
                    "A": "15%",
                    "B": "20%",
                    "C": "25%",
                    "D": "30%"
                },
                "correct": "C",
                "explanation": "25% of Octant's rewards are allocated to foundation operations."
            }
        ]
        self.active_games = {}

    async def start_game(self, ctx):
        """Start a new trivia game."""
        try:
            # Initialize game state for this user
            self.active_games[ctx.author.id] = {
                'score': 0,
                'asked_questions': set()
            }
            
            # Send welcome message
            embed = discord.Embed(
                title="🎮 Welcome to Octant Trivia!",
                description="Test your knowledge about Octant's ecosystem!",
                color=discord.Color.blue()
            )
            
            await ctx.send(embed=embed)
            await self.send_next_question(ctx)
            
        except Exception as e:
            logger.error(f"Error starting game: {str(e)}")
            await ctx.send(
                "An error occurred while starting the game. Please try again."
            )

    async def send_next_question(self, interaction):
        """Send the next question."""
        try:
            # Get user's game state
            if isinstance(interaction, discord.Interaction):
                user_id = interaction.user.id
            else:  # Context from command
                user_id = interaction.author.id
            
            game_state = self.active_games.get(user_id)
            if not game_state:
                return
            
            # Get available questions
            available = [i for i in range(len(self.questions)) 
                        if i not in game_state['asked_questions']]
            
            # Check if game is over
            if not available:
                await self.end_game(interaction)
                return
            
            # Select random question
            question_idx = random.choice(available)
            game_state['asked_questions'].add(question_idx)
            question = self.questions[question_idx]
            
            # Create embed
            embed = discord.Embed(
                title=f"Question {len(game_state['asked_questions'])}/{len(self.questions)}",
                description=question['question'],
                color=discord.Color.blue()
            )
            
            # Create view with buttons
            view = TriviaView(self, question)
            
            # Send question
            if isinstance(interaction, discord.Interaction):
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, view=view)
                else:
                    await interaction.response.send_message(embed=embed, view=view)
            else:  # Context from command
                await interaction.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error sending question: {str(e)}")
            error_msg = "An error occurred while sending the question."
            if isinstance(interaction, discord.Interaction):
                if interaction.response.is_done():
                    await interaction.followup.send(error_msg, ephemeral=True)
                else:
                    await interaction.response.send_message(error_msg, ephemeral=True)
            else:
                await interaction.send(error_msg)

    async def end_game(self, interaction):
        """End the game and show final score."""
        try:
            if isinstance(interaction, discord.Interaction):
                user_id = interaction.user.id
            else:
                user_id = interaction.author.id
                
            game_state = self.active_games.get(user_id)
            if not game_state:
                return
                
            score = game_state['score']
            total = len(self.questions)
            percentage = (score / total) * 100
            
            embed = discord.Embed(
                title="🎮 Game Complete!",
                color=discord.Color.green() if percentage >= 60 else discord.Color.red()
            )
            
            embed.add_field(
                name="Final Score",
                value=f"{score}/{total} ({percentage:.1f}%)",
                inline=False
            )
            
            rating = "🌟 Expert!" if percentage >= 80 else "👏 Well Done!" if percentage >= 60 else "📚 Keep Learning!"
            embed.add_field(name="Rating", value=rating, inline=False)
            embed.set_footer(text="Type /trivia to play again!")
            
            if isinstance(interaction, discord.Interaction):
                await interaction.followup.send(embed=embed)
            else:
                await interaction.send(embed=embed)
            
            # Clean up game state
            del self.active_games[user_id]
            
        except Exception as e:
            logger.error(f"Error ending game: {str(e)}")
            error_msg = "An error occurred while ending the game."
            if isinstance(interaction, discord.Interaction):
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                await interaction.send(error_msg)
