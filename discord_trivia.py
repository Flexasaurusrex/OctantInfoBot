
import discord
from discord import ui
import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)

class TriviaButton(ui.Button):
    def __init__(self, option: str, label: str):
        super().__init__(style=discord.ButtonStyle.primary, label=f"{option}. {label}")
        self.option = option

    async def callback(self, interaction: discord.Interaction):
        try:
            view = self.view
            if not isinstance(view, TriviaView):
                return
            
            if view.answered:
                await interaction.response.send_message("This question was already answered!", ephemeral=True)
                return

            view.answered = True
            is_correct = self.option == view.correct_answer

            if is_correct:
                view.game.score += 1
                embed = discord.Embed(
                    title="✅ Correct!",
                    description=view.explanation,
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Incorrect!",
                    description=f"The correct answer was: {view.correct_answer}\n\n{view.explanation}",
                    color=discord.Color.red()
                )

            score = view.game.score
            total = view.game.questions_asked + 1
            embed.add_field(
                name="Score",
                value=f"{score}/{total} ({(score/total*100):.1f}%)"
            )

            await interaction.response.send_message(embed=embed)
            await view.game.next_question(interaction)

        except Exception as e:
            logger.error(f"Button error: {str(e)}")
            await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)

class TriviaView(ui.View):
    def __init__(self, game, question: dict):
        super().__init__(timeout=30.0)
        self.game = game
        self.answered = False
        self.correct_answer = question['correct']
        self.explanation = question['explanation']

        for option, text in question['options'].items():
            self.add_item(TriviaButton(option, text))

    async def on_timeout(self):
        if not self.answered:
            embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"The correct answer was: {self.correct_answer}\n\n{self.explanation}",
                color=discord.Color.orange()
            )
            try:
                await self.message.reply(embed=embed)
                await self.game.end_game(self.message.channel)
            except:
                pass

class DiscordTrivia:
    def __init__(self):
        self.questions = [
            {
                "question": "What is the minimum GLM balance needed for rewards?",
                "options": {
                    "A": "10 GLM",
                    "B": "50 GLM", 
                    "C": "100 GLM",
                    "D": "500 GLM"
                },
                "correct": "C",
                "explanation": "A minimum balance of 100 GLM is required to qualify for rewards."
            },
            {
                "question": "How long is each Octant epoch?",
                "options": {
                    "A": "30 days",
                    "B": "60 days",
                    "C": "90 days", 
                    "D": "120 days"
                },
                "correct": "C",
                "explanation": "Each epoch lasts 90 days, followed by a two-week allocation period."
            }
        ]
        self.active_games = {}

    async def start_game(self, interaction: discord.Interaction):
        try:
            channel = interaction.channel
            self.active_games[channel.id] = {
                'score': 0,
                'questions_asked': 0,
                'start_time': datetime.now()
            }
            
            await self.next_question(interaction)
            
        except Exception as e:
            logger.error(f"Game start error: {str(e)}")
            await interaction.response.send_message("Failed to start game. Please try again.", ephemeral=True)

    async def next_question(self, interaction: discord.Interaction):
        try:
            game = self.active_games.get(interaction.channel_id)
            if not game:
                return

            if game['questions_asked'] >= len(self.questions):
                await self.end_game(interaction.channel)
                return

            question = self.questions[game['questions_asked']]
            game['questions_asked'] += 1

            embed = discord.Embed(
                title=f"Question {game['questions_asked']}/{len(self.questions)}",
                description=question['question'],
                color=discord.Color.blue()
            )

            view = TriviaView(self, question)
            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Question error: {str(e)}")
            await interaction.followup.send("Failed to send question. Game ended.", ephemeral=True)
            if interaction.channel_id in self.active_games:
                del self.active_games[interaction.channel_id]

    async def end_game(self, channel):
        try:
            game = self.active_games.get(channel.id)
            if not game:
                return

            score = game['score']
            total = len(self.questions)
            percentage = (score / total) * 100

            embed = discord.Embed(
                title="🎮 Game Complete!",
                color=discord.Color.green() if percentage >= 60 else discord.Color.blue()
            )

            embed.add_field(
                name="Final Score",
                value=f"{score}/{total} ({percentage:.1f}%)",
                inline=False
            )

            rating = "🌟 Expert!" if percentage >= 80 else "👏 Well Done!" if percentage >= 60 else "📚 Keep Learning!"
            embed.add_field(name="Rating", value=rating)
            
            await channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Game end error: {str(e)}")
        finally:
            if channel.id in self.active_games:
                del self.active_games[channel.id]
