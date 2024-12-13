import discord
from discord.ext import commands
import random
import html
import logging
import asyncio
from typing import Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DiscordTrivia:
    def __init__(self):
        """Initialize the trivia game with questions."""
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
                "question": "What percentage of Octant's rewards goes to foundation operations?",
                "options": {
                    "A": "15%",
                    "B": "20%",
                    "C": "25%",
                    "D": "30%"
                },
                "correct": "C",
                "explanation": "25% of Octant's rewards are allocated to foundation operations to maintain and develop the platform, while 70% goes to user and matched rewards, and 5% to community initiatives."
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
                "explanation": "Patron mode allows users to boost project funding by allocating their rewards directly to the matched rewards pool, enhancing the support for community projects."
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
                "explanation": "Octant is backed by 100,000 ETH from the Golem Foundation, providing a substantial foundation for its public goods funding initiatives."
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
                "explanation": "After each 90-day epoch, there's a two-week allocation window where users can claim their rewards or choose to donate them to projects."
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
                "explanation": "5% of rewards are allocated to community initiatives, fostering growth and innovation within the Octant ecosystem."
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
                "explanation": "Octant uses a locked staking mechanism where GLM tokens must be locked to participate in the ecosystem and earn rewards."
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
                "explanation": "The Golem Foundation oversees Octant's development, backed by their commitment of 100,000 ETH to support public goods funding."
            },
            {
                "question": "What is the primary goal of Octant's funding model?",
                "options": {
                    "A": "Maximum profit generation",
                    "B": "Token price stability",
                    "C": "Public goods funding",
                    "D": "Network security"
                },
                "correct": "C",
                "explanation": "Octant's primary goal is to support public goods funding through its innovative quadratic funding mechanism and community-driven allocation."
            },
            {
                "question": "How are project funding decisions made in Octant?",
                "options": {
                    "A": "Foundation decides alone",
                    "B": "Community voting only",
                    "C": "Quadratic funding + community",
                    "D": "Random selection"
                },
                "correct": "C",
                "explanation": "Project funding in Octant is determined through a combination of quadratic funding mechanics and community participation, ensuring fair and democratic resource allocation."
            },
            {
                "question": "What happens to GLM tokens during the locking period?",
                "options": {
                    "A": "They're burned",
                    "B": "They're traded freely",
                    "C": "They're locked and illiquid",
                    "D": "They're converted to ETH"
                },
                "correct": "C",
                "explanation": "During the locking period, GLM tokens become illiquid and cannot be transferred or traded, ensuring committed participation in the ecosystem."
            }
        ]
        self.current_games = {}  # Store game state per channel

    async def create_answer_view(self, options: Dict[str, str]) -> discord.ui.View:
        """Create Discord UI View with buttons for options."""
        class AnswerView(discord.ui.View):
            def __init__(self, trivia_game, options):
                super().__init__(timeout=None)
                self.trivia_game = trivia_game
                for key, value in options.items():
                    self.add_item(AnswerButton(key, value))

        class AnswerButton(discord.ui.Button):
            def __init__(self, key: str, value: str):
                super().__init__(
                    label=f"{key}. {value}",
                    custom_id=f"trivia_{key}",
                    style=discord.ButtonStyle.secondary
                )

            async def callback(self, interaction: discord.Interaction):
                try:
                    answer = self.custom_id.split("_")[1]
                    logger.info(f"User {interaction.user} selected answer: {answer}")
                    
                    # Disable all buttons immediately after selection
                    for child in self.view.children:
                        child.disabled = True
                    await interaction.message.edit(view=self.view)
                    
                    # Handle the answer
                    await self.view.trivia_game.handle_answer(interaction, answer)
                except Exception as e:
                    logger.error(f"Error in button callback: {str(e)}", exc_info=True)
                    await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)

        return AnswerView(self, options)

    async def start_game(self, ctx: commands.Context):
        """Start a new trivia game in a channel."""
        channel_id = ctx.channel.id
        self.current_games[channel_id] = {
            'score': 0,
            'questions_asked': 0,
            'current_question': None
        }
        
        await self.send_next_question(ctx)

    async def send_next_question(self, ctx: commands.Context):
        """Send the next question to the channel."""
        channel_id = ctx.channel.id
        game = self.current_games.get(channel_id)
        
        if not game:
            await ctx.send("Please start a new game with /trivia")
            return
            
        if game['questions_asked'] >= len(self.questions):
            # Game finished
            score = game['score']
            percentage = (score / len(self.questions)) * 100
            await ctx.send(
                f"🎮 Game Over!\n\n"
                f"🏆 Final Score: {score}/{len(self.questions)} ({percentage:.1f}%)\n\n"
                f"Want to play again? Use /trivia!"
            )
            del self.current_games[channel_id]
            return
            
        question = self.questions[game['questions_asked']]
        game['current_question'] = question
        
        message = (
            f"🎯 Question {game['questions_asked'] + 1}/{len(self.questions)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📝 {question['question']}\n\n"
            f"Select your answer from the options below:"
        )
        
        view = await self.create_answer_view(question['options'])
        await ctx.send(message, view=view)

    async def handle_answer(self, interaction: discord.Interaction, answer: str):
        """Handle user's answer selection."""
        try:
            channel_id = interaction.channel_id
            game = self.current_games.get(channel_id)
            
            if not game or not game['current_question']:
                logger.warning(f"No active game found for channel {channel_id}")
                await interaction.response.send_message(
                    "No active game found. Start a new game with /trivia",
                    ephemeral=True
                )
                return

            logger.info(f"Processing answer for game in channel {channel_id}")
            logger.info(f"Current game state: {game}")
            
            question = game['current_question']
            is_correct = answer == question['correct']
            
            logger.info(f"Processing answer for channel {channel_id}: Current question {game['questions_asked'] + 1}/{len(self.questions)}")
            logger.info(f"Answer was {is_correct}: {answer} (correct: {question['correct']})")
            
            if is_correct:
                game['score'] += 1
                logger.info(f"Correct answer by {interaction.user}! New score: {game['score']}")
            else:
                logger.info(f"Incorrect answer by {interaction.user}. Score remains: {game['score']}")
            
            # Update game state
            game['questions_asked'] += 1
            logger.info(f"Updated questions asked to: {game['questions_asked']}")

            # Disable the buttons in the current message
            view = discord.ui.View()
            for key, value in question['options'].items():
                button = discord.ui.Button(
                    label=f"{key}. {value}",
                    custom_id=f"trivia_{key}",
                    style=discord.ButtonStyle.secondary,
                    disabled=True
                )
                view.add_item(button)
            
            try:
                await interaction.message.edit(view=view)
            except Exception as button_error:
                logger.error(f"Error disabling buttons: {str(button_error)}", exc_info=True)

            # Send result message
            if is_correct:
                result_message = (
                    f"✨ Correct! Brilliant answer! ✨\n\n"
                    f"📚 Learn More:\n{question['explanation']}\n\n"
                    f"🎯 Score: {game['score']}/{game['questions_asked']} "
                    f"({(game['score']/game['questions_asked']*100):.1f}%)"
                )
            else:
                correct_option = question['options'][question['correct']]
                result_message = (
                    f"❌ Not quite right!\n\n"
                    f"The correct answer was:\n"
                    f"✅ {question['correct']}: {correct_option}\n\n"
                    f"📚 Learn More:\n{question['explanation']}\n\n"
                    f"🎯 Score: {game['score']}/{game['questions_asked']} "
                    f"({(game['score']/game['questions_asked']*100):.1f}%)"
                )
            
            await interaction.response.send_message(result_message)
            
            # Small delay before sending next question
            await asyncio.sleep(1)
            
            # Handle game completion or next question
            if game['questions_asked'] >= len(self.questions):
                # Game is finished
                final_score = game['score']
                total_questions = len(self.questions)
                percentage = (final_score / total_questions) * 100
                final_message = (
                    f"🎮 Game Over!\n\n"
                    f"🏆 Final Score: {final_score}/{total_questions} ({percentage:.1f}%)\n\n"
                    f"Want to play again? Use /trivia!"
                )
                await interaction.followup.send(final_message)
                del self.current_games[channel_id]
            else:
                # Setup and send next question
                try:
                    next_question = self.questions[game['questions_asked']]
                    game['current_question'] = next_question
                    logger.info(f"Setting up next question {game['questions_asked'] + 1}")
                    
                    next_message = (
                        f"🎯 Question {game['questions_asked'] + 1}/{len(self.questions)}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"📝 {next_question['question']}\n\n"
                        f"Select your answer from the options below:"
                    )
                    
                    next_view = await self.create_answer_view(next_question['options'])
                    await interaction.followup.send(next_message, view=next_view)
                    logger.info(f"Successfully sent next question to channel {interaction.channel_id}")
                except Exception as e:
                    logger.error(f"Error sending next question: {str(e)}", exc_info=True)
                    await interaction.followup.send("Error loading next question. Please start a new game.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in handle_answer: {str(e)}", exc_info=True)
            error_message = "An error occurred while processing your answer. Please try again."
            
            if not interaction.response.is_done():
                await interaction.response.send_message(error_message, ephemeral=True)
            else:
                await interaction.followup.send(error_message, ephemeral=True)
