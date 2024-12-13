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
            # Verify interaction hasn't been responded to
            if interaction.response.is_done():
                return

            view = self.view
            if not isinstance(view, TriviaView):
                logger.error("Invalid view type in TriviaButton callback")
                await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)
                return

            if view.answered:
                await interaction.response.send_message("This question has already been answered!", ephemeral=True)
                return

            view.answered = True
            is_correct = self.option == view.correct_answer
            logger.info(f"Trivia answer received - Correct: {is_correct}, Option: {self.option}")

            if is_correct:
                view.game.score += 1
                response_embed = discord.Embed(
                    title="✅ Correct!",
                    description=view.explanation,
                    color=discord.Color.green()
                )
            else:
                correct_option = next(btn.label for btn in view.children if btn.option == view.correct_answer)
                response_embed = discord.Embed(
                    title="❌ Incorrect!",
                    description=f"The correct answer was: {correct_option}\n\n{view.explanation}",
                    color=discord.Color.red()
                )

            score = view.game.score
            questions_asked = view.game.questions_asked + 1
            response_embed.add_field(
                name="Score",
                value=f"{score}/{questions_asked} ({(score/questions_asked*100):.1f}%)",
                inline=False
            )

            await interaction.response.send_message(embed=response_embed)
            await view.game.send_next_question(interaction)

        except Exception as e:
            logger.error(f"Error in trivia button callback: {str(e)}", exc_info=True)
            try:
                await interaction.response.send_message(
                    "Sorry, there was an error processing your answer. Please try again.",
                    ephemeral=True
                )
            except:
                pass  # Interaction might have already been responded to

class TriviaView(ui.View):
    def __init__(self, game, question: dict):
        super().__init__(timeout=30.0)
        self.game = game
        self.answered = False
        self.correct_answer = question['correct']
        self.explanation = question['explanation']
        self.message = None  # Added to store the message for timeout handling

        for option, text in question['options'].items():
            self.add_item(TriviaButton(option, text))

    async def on_timeout(self):
        try:
            if not self.answered and self.message:
                timeout_embed = discord.Embed(
                    title="⏰ Time's Up!",
                    description=f"The correct answer was: {self.correct_answer}\n\n{self.explanation}",
                    color=discord.Color.orange()
                )
                await self.message.reply(embed=timeout_embed)
                await self.game.end_game(self.message)
        except Exception as e:
            logger.error(f"Error in trivia timeout handling: {str(e)}", exc_info=True)

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
                "explanation": "A maximum funding cap of 20% of the total Matched Rewards fund (including Patron mode) ensures balanced distribution."
            }
        ]
        self.current_games = {}

    async def start_game(self, interaction: discord.Interaction):
        """Start a new trivia game."""
        try:
            channel_id = interaction.channel_id
            self.current_games[channel_id] = {
                'score': 0,
                'questions_asked': 0,
                'start_time': discord.utils.utcnow()
            }
            await self.send_next_question(interaction)
        except Exception as e:
            logger.error(f"Error starting trivia game: {str(e)}", exc_info=True)
            await interaction.response.send_message(
                "Sorry, there was an error starting the trivia game. Please try again.",
                ephemeral=True
            )

    async def send_next_question(self, interaction: discord.Interaction):
        """Send the next question to the channel."""
        try:
            channel_id = interaction.channel_id
            game = self.current_games.get(channel_id)

            if not game:
                await interaction.followup.send("No active game found! Start a new game with /trivia")
                return

            if game['questions_asked'] >= len(self.questions):
                await self.end_game(interaction)
                return

            question = self.questions[game['questions_asked']]
            game['questions_asked'] += 1

            embed = discord.Embed(
                title=f"Question {game['questions_asked']}/{len(self.questions)}",
                description=question['question'],
                color=discord.Color.blue()
            )

            view = TriviaView(self, question)
            message = await interaction.followup.send(embed=embed, view=view)
            view.message = message  # Store the message for timeout handling

        except Exception as e:
            logger.error(f"Error sending next question: {str(e)}", exc_info=True)
            await interaction.followup.send(
                "Sorry, there was an error sending the next question. The game has been ended.",
                ephemeral=True
            )
            if channel_id in self.current_games:
                del self.current_games[channel_id]

    async def end_game(self, interaction: discord.Interaction):
        """Handle game completion and cleanup."""
        try:
            channel_id = interaction.channel_id
            if not channel_id:
                return

            game = self.current_games.get(channel_id)
            if not game:
                return

            score = game['score']
            total_questions = len(self.questions)
            percentage = (score / total_questions) * 100
            duration = discord.utils.utcnow() - game['start_time']
            minutes = duration.seconds // 60
            seconds = duration.seconds % 60

            final_embed = discord.Embed(
                title="🎮 Game Complete! 🎮",
                color=discord.Color.green() if percentage >= 60 else discord.Color.blue()
            )

            final_embed.add_field(
                name="📊 Final Score",
                value=f"{score}/{total_questions} ({percentage:.1f}%)",
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

            try:
                await interaction.followup.send(embed=final_embed)
            except:
                ctx = await interaction.client.get_context(interaction.message)
                await ctx.send(embed=final_embed)

        except Exception as e:
            logger.error(f"Error in end_game: {str(e)}", exc_info=True)
        finally:
            if channel_id in self.current_games:
                del self.current_games[channel_id]

    async def handle_answer(self, interaction: discord.Interaction, answer: str):
        """Handle button interaction answers with enhanced error handling."""
        try:
            if not interaction.channel_id:
                logger.error("Channel ID missing from interaction")
                await interaction.response.send_message(
                    "Error: Unable to process answer. Please try again.",
                    ephemeral=True
                )
                return

            channel_id = interaction.channel_id
            game = self.current_games.get(channel_id)
            
            if not game:
                logger.warning(f"No active game found for channel {channel_id}")
                await interaction.response.send_message(
                    "No active game found! Start a new game with /trivia",
                    ephemeral=True
                )
                return

            # Validate game state
            if game['questions_asked'] <= 0 or game['questions_asked'] > len(self.questions):
                logger.error(f"Invalid game state: questions_asked={game['questions_asked']}")
                await interaction.response.send_message(
                    "Error: Game state is invalid. Please start a new game.",
                    ephemeral=True
                )
                return

            # Check if question has already been answered
            try:
                view = interaction.message.view
                if view and hasattr(view, 'answered') and view.answered:
                    logger.info(f"Question already answered in channel {channel_id}")
                    await interaction.response.send_message(
                        "This question has already been answered!",
                        ephemeral=True
                    )
                    return
            except AttributeError as e:
                logger.debug(f"View not available: {str(e)}")

            # Get current question
            current_question = self.questions[game['questions_asked'] - 1]
            is_correct = answer == current_question['correct']
            
            # Update game state
            if is_correct:
                game['score'] += 1
                response_embed = discord.Embed(
                    title="✅ Correct!",
                    description=current_question['explanation'],
                    color=discord.Color.green()
                )
            else:
                response_embed = discord.Embed(
                    title="❌ Incorrect!",
                    description=f"The correct answer was: {current_question['correct']}\n\n{current_question['explanation']}",
                    color=discord.Color.red()
                )
                
            # Calculate and add score
            score = game['score']
            questions_asked = game['questions_asked']
            score_percentage = (score/questions_asked*100) if questions_asked > 0 else 0
            response_embed.add_field(
                name="Score",
                value=f"{score}/{questions_asked} ({score_percentage:.1f}%)",
                inline=False
            )
            
            # Add footer with game progress
            total_questions = len(self.questions)
            response_embed.set_footer(text=f"Question {questions_asked} of {total_questions}")
            
            try:
                await interaction.response.send_message(embed=response_embed)
                await self.send_next_question(interaction)
            except discord.errors.InteractionResponded:
                logger.warning("Interaction already responded to")
            except discord.errors.NotFound:
                logger.error("Interaction not found - message may have been deleted")
            except discord.errors.HTTPException as http_err:
                logger.error(f"HTTP error sending response: {str(http_err)}")
                await interaction.followup.send(
                    "Error sending response. The game will continue with the next question.",
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(f"Error handling trivia answer: {str(e)}", exc_info=True)
            try:
                error_message = "Sorry, there was an error processing your answer. Please try again."
                if not interaction.response.is_done():
                    await interaction.response.send_message(error_message, ephemeral=True)
                else:
                    await interaction.followup.send(error_message, ephemeral=True)
            except Exception as followup_error:
                logger.error(f"Failed to send error message: {str(followup_error)}")