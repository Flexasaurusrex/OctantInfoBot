import discord
from discord.ui import Button, View
import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)

class TriviaButton(Button):
    def __init__(self, option: str, label: str, style: discord.ButtonStyle = discord.ButtonStyle.primary):
        super().__init__(style=style, label=f"{option}. {label}", custom_id=f"trivia_{option}")
        self.option = option

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if view.answered:
            await interaction.response.send_message("This question has already been answered!", ephemeral=True)
            return

        view.answered = True
        is_correct = self.option == view.correct_answer

        # Update button styles
        for child in view.children:
            if isinstance(child, Button):
                child.disabled = True
                if child.custom_id == f"trivia_{view.correct_answer}":
                    child.style = discord.ButtonStyle.success
                elif child.custom_id == self.custom_id and not is_correct:
                    child.style = discord.ButtonStyle.danger

        # Update game state
        game_state = view.trivia_game.active_games.get(interaction.user.id)
        if is_correct and game_state:
            game_state['score'] += 1
            response_title = "✅ Correct!"
            color = discord.Color.green()
        else:
            response_title = "❌ Incorrect!"
            color = discord.Color.red()

        # Create response embed
        embed = discord.Embed(
            title=response_title,
            color=color
        )
        
        if game_state:
            score = game_state['score']
            total = len(game_state['asked_questions'])
            embed.add_field(
                name="Score",
                value=f"{score}/{total} ({(score/total*100):.1f}%)",
                inline=False
            )
            embed.add_field(
                name="Explanation", 
                value=view.explanation,
                inline=False
            )

        await interaction.response.edit_message(view=view)
        await interaction.followup.send(embed=embed)
        
        # Send next question
        await view.trivia_game.send_next_question(interaction)

class TriviaView(View):
    def __init__(self, trivia_game, question: dict):
        super().__init__(timeout=30.0)
        self.trivia_game = trivia_game
        self.answered = False
        self.correct_answer = question['correct']
        self.explanation = question['explanation']
        
        # Add buttons for each option
        for option, text in question['options'].items():
            self.add_item(TriviaButton(option=option, label=text))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        # Message might have been deleted, so we need to handle that case
        try:
            await self.message.edit(view=self)
        except:
            pass

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
            self.active_games[ctx.author.id] = {
                'score': 0,
                'asked_questions': set()
            }
            
            embed = discord.Embed(
                title="🎮 Welcome to Octant Trivia!",
                description="Test your knowledge about Octant's ecosystem!",
                color=discord.Color.blue()
            )
            
            await ctx.send(embed=embed)
            await self.send_next_question(ctx)
            
        except Exception as e:
            logger.error(f"Error starting game: {str(e)}")
            await ctx.send("An error occurred while starting the game. Please try again.")

    async def send_next_question(self, interaction):
        """Send the next question."""
        try:
            user_id = interaction.user.id if isinstance(interaction, discord.Interaction) else interaction.author.id
            game_state = self.active_games.get(user_id)
            
            if not game_state:
                return
            
            available_questions = [i for i in range(len(self.questions)) 
                                if i not in game_state['asked_questions']]
            
            if not available_questions:
                await self.end_game(interaction)
                return
            
            question_idx = random.choice(available_questions)
            game_state['asked_questions'].add(question_idx)
            question = self.questions[question_idx]
            
            embed = discord.Embed(
                title=f"Question {len(game_state['asked_questions'])}/{len(self.questions)}",
                description=question['question'],
                color=discord.Color.blue()
            )
            
            view = TriviaView(self, question)
            
            if isinstance(interaction, discord.Interaction):
                if interaction.response.is_done():
                    msg = await interaction.followup.send(embed=embed, view=view)
                else:
                    msg = await interaction.response.send_message(embed=embed, view=view)
            else:
                msg = await interaction.send(embed=embed, view=view)
            
            # Store message reference in view
            if hasattr(msg, 'message'):
                view.message = msg.message
            else:
                view.message = msg
            
        except Exception as e:
            logger.error(f"Error sending question: {str(e)}")
            error_msg = "An error occurred while sending the question. Please try again."
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
            user_id = interaction.user.id if isinstance(interaction, discord.Interaction) else interaction.author.id
            game_state = self.active_games.get(user_id)
            
            if not game_state:
                return
            
            score = game_state['score']
            total = len(self.questions)
            percentage = (score / total) * 100
            
            embed = discord.Embed(
                title="🎮 Game Complete!",
                description=f"You've completed the Octant Trivia game!",
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
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.response.send_message(embed=embed)
            else:
                await interaction.send(embed=embed)
            
            del self.active_games[user_id]
            
        except Exception as e:
            logger.error(f"Error ending game: {str(e)}")
            error_msg = "An error occurred while ending the game."
            if isinstance(interaction, discord.Interaction):
                if interaction.response.is_done():
                    await interaction.followup.send(error_msg, ephemeral=True)
                else:
                    await interaction.response.send_message(error_msg, ephemeral=True)
            else:
                await interaction.send(error_msg)
