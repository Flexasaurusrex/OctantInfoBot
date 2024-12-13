from discord.ext import commands
from discord import ui, ButtonStyle, Interaction, InteractionType, Embed, Color
import discord
import logging
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TriviaButton(ui.Button):
    def __init__(self, option: str, label: str, is_correct: bool = False):
        """Initialize a trivia button with enhanced styling."""
        super().__init__(
            style=ButtonStyle.primary,
            label=f"{option}. {label}",
            custom_id=f"trivia_{option}"
        )
        self.option = option
        self.is_correct = is_correct
        
    async def update_style(self, interaction: Interaction, show_answer: bool = False):
        """Update button style based on correctness."""
        if show_answer:
            self.style = ButtonStyle.success if self.is_correct else ButtonStyle.danger
        self.disabled = True

    async def callback(self, interaction: discord.Interaction):
        """Handle button click interaction."""
        view = self.view
        if not isinstance(view, TriviaView):
            logger.error("Invalid view type in button callback")
            await interaction.response.send_message(
                "An error occurred with the trivia game. Please try starting a new game.",
                ephemeral=True
            )
            return

        try:
            # Check if user is in an active game
            channel_id = interaction.channel_id
            if not view.game.current_games.get(channel_id):
                await interaction.response.send_message(
                    "There's no active game in this channel. Start a new game with /trivia",
                    ephemeral=True
                )
                return

            # Check if question was already answered
            if view.answered:
                await interaction.response.send_message(
                    "This question has already been answered! Wait for the next one.",
                    ephemeral=True
                )
                return

            # Mark question as answered
            view.answered = True

            # Change button styles and disable them
            for child in view.children:
                if isinstance(child, TriviaButton):
                    child.disabled = True
                    if child.option == self.option:
                        child.style = discord.ButtonStyle.primary
                    elif child.is_correct:
                        child.style = discord.ButtonStyle.success
                    else:
                        child.style = discord.ButtonStyle.secondary

            # Process the answer
            await view.handle_answer(interaction, self.option)

            # Update the message with disabled buttons
            try:
                if view.message:
                    await view.message.edit(view=view)
            except discord.errors.NotFound:
                logger.error("Original message not found when updating buttons")
            except Exception as e:
                logger.error(f"Error updating message with disabled buttons: {str(e)}")

        except discord.errors.NotFound:
            logger.error("Message not found when processing button click")
            await interaction.response.send_message(
                "The game message was not found. Please start a new game with /trivia",
                ephemeral=True
            )
        except discord.errors.HTTPException as http_err:
            logger.error(f"Discord HTTP error in button callback: {str(http_err)}")
            await interaction.response.send_message(
                "An error occurred while processing your answer. Please try again.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in button callback: {str(e)}")
            await interaction.response.send_message(
                "An error occurred while processing your answer. Please try starting a new game.",
                ephemeral=True
            )

class TriviaView(ui.View):
    def __init__(self, game, question: dict):
        super().__init__(timeout=30.0)
        self.game = game
        self.answered = False
        self.correct_answer = question['correct']
        self.explanation = question['explanation']
        self.message = None
        self.question = question

        # Add buttons for each option with correct/incorrect info
        for option, text in question['options'].items():
            self.add_item(TriviaButton(
                option=option,
                label=text,
                is_correct=(option == self.correct_answer)
            ))

    async def update_buttons(self, interaction: Interaction, selected_option: str):
        """Update all buttons to show correct/incorrect answers."""
        for child in self.children:
            if isinstance(child, TriviaButton):
                await child.update_style(interaction, show_answer=True)

    async def handle_answer(self, interaction: Interaction, answer: str):
        """Process the user's answer with enhanced feedback."""
        try:
            is_correct = answer == self.correct_answer
            game = self.game
            
            # Update the game score
            if is_correct:
                game.score += 1
            
            # Create a rich embed for the response
            embed = discord.Embed(
                title="✅ Correct!" if is_correct else "❌ Incorrect!",
                color=discord.Color.green() if is_correct else discord.Color.red()
            )
            
            # Add the question field
            embed.add_field(
                name="Question",
                value=self.question['question'],
                inline=False
            )
            
            # Add the answer field
            correct_option = next(
                f"{self.correct_answer}. {btn.label.split('. ')[1]}"
                for btn in self.children
                if isinstance(btn, TriviaButton) and btn.option == self.correct_answer
            )
            embed.add_field(
                name="Correct Answer",
                value=correct_option,
                inline=False
            )
            
            # Add explanation
            embed.add_field(
                name="Explanation",
                value=self.explanation,
                inline=False
            )
            
            # Calculate and add score
            score = game.score
            questions_asked = len(game.asked_questions)
            percentage = (score / questions_asked) * 100 if questions_asked > 0 else 0
            
            embed.add_field(
                name="📊 Score",
                value=f"{score}/{questions_asked} ({percentage:.1f}%)",
                inline=False
            )

            # Disable buttons and update their styles
            await self.update_buttons(interaction, answer)

            # Send the response
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.followup.send(embed=embed)
            
            # Update the message with disabled buttons
            if self.message:
                try:
                    await self.message.edit(view=self)
                except discord.errors.NotFound:
                    logger.error("Original message not found when updating buttons")
            
            # Send next question if available
            await self.game.send_next_question(interaction)
            
        except discord.errors.NotFound:
            logger.error("Message not found when processing answer")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "The original message was not found. Starting a new game...",
                    ephemeral=True
                )
            await self.game.start_game(interaction)
            
        except discord.errors.HTTPException as http_err:
            logger.error(f"Discord HTTP error in handle_answer: {str(http_err)}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An error occurred while processing your answer. Please try again.",
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(f"Error in handle_answer: {str(e)}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An error occurred while processing your answer. The game will end.",
                    ephemeral=True
                )
            await self.game.end_game(interaction)
        try:
            if self.message:
                await self.message.edit(view=self)
            
            # Send next question if available
            await self.game.send_next_question(interaction)
        except Exception as e:
            logger.error(f"Error handling answer: {str(e)}")
            await interaction.followup.send(
                "An error occurred while updating the game. The game will end.",
                ephemeral=True
            )
            await self.game.end_game(interaction)

    async def on_timeout(self):
        """Handle timeout when no answer is received."""
        if not self.answered and self.message:
            timeout_embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"The correct answer was: {self.correct_answer}\n\n{self.explanation}",
                color=discord.Color.orange()
            )
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)
            
            await self.message.reply(embed=timeout_embed)
            await self.game.end_game(self.message)

class DiscordTrivia:
    def __init__(self):
        """Initialize the trivia game."""
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
                "explanation": "25% of Octant's rewards are allocated to foundation operations, while 70% goes to user and matched rewards."
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
            }
        ]
        
        self.current_games = {}  # Store active games
        self.asked_questions = set()  # Track asked questions
        self.score = 0

    async def start_game(self, interaction: discord.Interaction):
        """Start a new trivia game."""
        try:
            channel_id = interaction.channel_id
            self.current_games[channel_id] = {
                'score': 0,
                'start_time': datetime.utcnow(),
                'asked_questions': set()
            }
            self.score = 0
            self.asked_questions = set()
            
            embed = discord.Embed(
                title="🎮 Welcome to Octant Trivia! 🎮",
                description=(
                    "Test your knowledge about Octant's ecosystem!\n\n"
                    "• Answer each question using the buttons below\n"
                    "• You have 30 seconds per question\n"
                    "• Learn interesting facts about Octant!"
                ),
                color=discord.Color.blue()
            )
            
            await interaction.response.send_message(embed=embed)
            await self.send_next_question(interaction)
            
        except Exception as e:
            logger.error(f"Error starting game: {str(e)}")
            await interaction.response.send_message(
                "An error occurred while starting the game. Please try again.",
                ephemeral=True
            )

    async def send_next_question(self, interaction: discord.Interaction):
        """Send the next question to the channel."""
        try:
            # Get available questions
            available_questions = [i for i in range(len(self.questions)) 
                                if i not in self.asked_questions]
            
            if not available_questions:
                await self.end_game(interaction)
                return
            
            # Select random question
            question_index = random.choice(available_questions)
            self.asked_questions.add(question_index)
            question = self.questions[question_index]
            
            embed = discord.Embed(
                title=f"Question {len(self.asked_questions)}/{len(self.questions)}",
                description=question['question'],
                color=discord.Color.blue()
            )
            
            view = TriviaView(self, question)
            
            # Send as followup if this is a button response
            if interaction.response.is_done():
                message = await interaction.followup.send(embed=embed, view=view)
            else:
                message = await interaction.channel.send(embed=embed, view=view)
            
            view.message = message  # Store for timeout handling
            
        except Exception as e:
            logger.error(f"Error sending question: {str(e)}")
            await interaction.followup.send(
                "An error occurred while sending the question. The game will end.",
                ephemeral=True
            )
            await self.end_game(interaction)

    async def end_game(self, interaction: discord.Interaction):
        """Handle game completion and cleanup."""
        try:
            # Get channel ID from interaction or message
            channel_id = getattr(interaction, 'channel_id', None)
            if not channel_id and hasattr(interaction, 'channel'):
                channel_id = interaction.channel.id
            if not channel_id:
                logger.error("Could not determine channel ID for game end")
                return
                
            game = self.current_games.get(channel_id)
            if not game:
                return

            score = self.score
            total_questions = len(self.asked_questions)
            percentage = (score / total_questions) * 100 if total_questions > 0 else 0
            duration = datetime.utcnow() - game['start_time']
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

            # Use the appropriate method to send the message
            if isinstance(interaction, discord.Interaction):
                if interaction.response.is_done():
                    await interaction.followup.send(embed=final_embed)
                else:
                    await interaction.response.send_message(embed=final_embed)
            else:
                await interaction.channel.send(embed=final_embed)

        except Exception as e:
            logger.error(f"Error in end_game: {str(e)}")
        finally:
            if channel_id in self.current_games:
                del self.current_games[channel_id]
