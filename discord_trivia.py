
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
                view.game.active_games[interaction.channel_id]['score'] += 1
                view.game.score = view.game.active_games[interaction.channel_id]['score']
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

            game = view.game.active_games[interaction.channel_id]
            score = game['score']
            total = game['questions_asked']
            embed.add_field(
                name="Score",
                value=f"{score}/{total} ({(score/total*100):.1f}%)" if total > 0 else "0/0 (0%)"
            )

            try:
                await interaction.response.send_message(embed=embed)
                await view.game.next_question(interaction.channel)
            except discord.errors.HTTPException:
                await interaction.channel.send(embed=embed)
                await view.game.next_question(interaction.channel)

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
                "explanation": "25% of rewards go to foundation operations, while 70% goes to user and matched rewards, and 5% to community initiatives."
            },
            {
                "question": "What is the purpose of Patron mode in Octant?",
                "options": {
                    "A": "To increase personal rewards",
                    "B": "To boost project funding",
                    "C": "To skip voting periods",
                    "D": "To reduce fees"
                },
                "correct": "B",
                "explanation": "Patron mode allows users to boost project funding by allocating their rewards directly to the matched rewards pool."
            },
            {
                "question": "How much ETH backs Octant's operations?",
                "options": {
                    "A": "50,000 ETH",
                    "B": "75,000 ETH",
                    "C": "100,000 ETH",
                    "D": "125,000 ETH"
                },
                "correct": "C",
                "explanation": "Octant is backed by 100,000 ETH from the Golem Foundation."
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
                "explanation": "A maximum funding cap of 20% ensures balanced distribution. Users can still donate but won't receive additional matching."
            },
            {
                "question": "What percentage of rewards goes to community initiatives?",
                "options": {
                    "A": "5%",
                    "B": "10%",
                    "C": "15%",
                    "D": "20%"
                },
                "correct": "A",
                "explanation": "5% of rewards are allocated to community initiatives, fostering growth and innovation."
            },
            {
                "question": "What type of staking mechanism does Octant use for GLM tokens?",
                "options": {
                    "A": "Liquid staking",
                    "B": "Locked staking",
                    "C": "Flexible staking",
                    "D": "Delegated staking"
                },
                "correct": "B",
                "explanation": "Octant uses a locked staking mechanism where GLM tokens must be locked to participate."
            },
            {
                "question": "Which organization oversees Octant's development?",
                "options": {
                    "A": "Ethereum Foundation",
                    "B": "Golem Foundation",
                    "C": "Octant DAO",
                    "D": "Decentralized Council"
                },
                "correct": "B",
                "explanation": "The Golem Foundation oversees Octant's development, backed by their commitment of 100,000 ETH."
            },
            {
                "question": "What happens after each 90-day epoch in Octant?",
                "options": {
                    "A": "Immediate reward distribution",
                    "B": "Two-week allocation window",
                    "C": "One-month voting period",
                    "D": "System maintenance"
                },
                "correct": "B",
                "explanation": "After each 90-day epoch, there's a two-week allocation window for claiming or donating rewards."
            }
        ]
        self.active_games = {}

    async def start_game(self, interaction: discord.Interaction):
        try:
            channel = interaction.channel
            game = {
                'score': 0,
                'questions_asked': 0,
                'start_time': datetime.now()
            }
            self.active_games[channel.id] = game
            self.score = game['score']  # Add score to instance for button access

            await interaction.response.send_message("Starting Octant Trivia! Get ready...")
            await self.next_question(channel)
            
        except Exception as e:
            logger.error(f"Game start error: {str(e)}")
            try:
                await interaction.response.send_message("Failed to start game. Please try again.", ephemeral=True)
            except:
                await interaction.channel.send("Failed to start game. Please try again.")

    async def next_question(self, channel):
        try:
            game = self.active_games.get(channel.id)
            if not game:
                return

            if game['questions_asked'] >= len(self.questions):
                await self.end_game(channel)
                return

            question = self.questions[game['questions_asked']]
            game['questions_asked'] += 1

            embed = discord.Embed(
                title=f"Question {game['questions_asked']}/{len(self.questions)}",
                description=question['question'],
                color=discord.Color.blue()
            )

            view = TriviaView(self, question)
            await channel.send(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Question error: {str(e)}")
            await channel.send("Failed to send question. Game ended.")
            if channel.id in self.active_games:
                del self.active_games[channel.id]

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
