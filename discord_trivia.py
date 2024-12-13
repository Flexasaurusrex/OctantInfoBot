import discord
from discord.ext import commands
import random
import html
import logging
import asyncio
from typing import Dict, Optional
async def get_context_from_interaction(interaction: discord.Interaction) -> Optional[commands.Context]:
    """Helper function to get context from interaction."""
    try:
        return await interaction.client.get_application_context(interaction)
    except Exception as e:
        logger.error(f"Error getting context from interaction: {str(e)}", exc_info=True)
        return None


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
                super().__init__(timeout=300)  # 5 minute timeout
                self.trivia_game = trivia_game
                self.answered = False
                self.timed_out = False
                for key, value in options.items():
                    button = discord.ui.Button(
                        style=discord.ButtonStyle.primary,
                        label=f"{key}. {value}",
                        custom_id=f"trivia_{key}",
                        row=0 if key in ['A', 'B'] else 1
                    )
                    button.callback = self.create_button_callback(key)
                    self.add_item(button)

            def create_button_callback(self, answer_key):
                async def button_callback(interaction: discord.Interaction):
                    try:
                        if self.answered:
                            await interaction.response.send_message("This question has already been answered!", ephemeral=True)
                            return
                            
                        if self.timed_out:
                            await interaction.response.send_message("This question has expired! Start a new game with /trivia", ephemeral=True)
                            return

                        self.answered = True
                        await interaction.response.defer()
                        
                        logger.info(f"User {interaction.user} selected answer: {answer_key}")
                        
                        # Disable all buttons and update their styles
                        for child in self.children:
                            child.disabled = True
                            if isinstance(child, discord.ui.Button):
                                button_key = child.custom_id.split("_")[1]
                                if button_key == self.trivia_game.current_games[interaction.channel_id]['current_question']['correct']:
                                    child.style = discord.ButtonStyle.success
                                elif button_key == answer_key:
                                    child.style = discord.ButtonStyle.danger
                                    
                        await interaction.message.edit(view=self)
                        
                        # Process the answer
                        await self.trivia_game.handle_answer(interaction, answer_key)
                        
                    except Exception as e:
                        logger.error(f"Error in button callback: {str(e)}", exc_info=True)
                        try:
                            await interaction.followup.send("An error occurred. Please try again with /trivia", ephemeral=True)
                        except:
                            pass
                
                return button_callback

            async def on_timeout(self):
                try:
                    self.timed_out = True
                    for child in self.children:
                        child.disabled = True
                    await self.message.edit(view=self)
                    await self.message.reply("⏰ Time's up! This question has expired. Use /trivia to start a new game!")
                    
                    # Clean up game state
                    if hasattr(self, 'message') and self.message.channel.id in self.trivia_game.current_games:
                        del self.trivia_game.current_games[self.message.channel.id]
                except Exception as e:
                    logger.error(f"Error in timeout handling: {str(e)}", exc_info=True)

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)
                await self.message.reply("Time's up! The question has expired. Start a new game with /trivia")

        return AnswerView(self, options)

    async def start_game(self, ctx: commands.Context):
        """Start a new trivia game in a channel."""
        try:
            channel_id = ctx.channel.id
            logger.info(f"Starting new game in channel {channel_id}")
            
            # Check if there's already an active game
            if channel_id in self.current_games:
                logger.info(f"Found existing game in channel {channel_id}")
                await ctx.send("There's already an active game in this channel! Please finish it or type `/trivia` to start a new one.")
                return
                
            # Initialize new game state
            self.current_games[channel_id] = {
                'score': 0,
                'questions_asked': 0,
                'current_question': None,
                'start_time': discord.utils.utcnow()
            }
            logger.info(f"Initialized new game state for channel {channel_id}")
            
            welcome_message = (
                "🎮 **Welcome to Octant Trivia!** 🎮\n\n"
                "Test your knowledge about Octant, GLM tokens, and the ecosystem!\n\n"
                "**Rules:**\n"
                "• Answer each question using the buttons below\n"
                "• You have 5 minutes per question\n"
                "• Learn interesting facts along the way!\n\n"
                "Good luck! Here's your first question..."
            )
            
            await ctx.send(welcome_message)
            logger.info(f"Sent welcome message to channel {channel_id}")
            
            await asyncio.sleep(2)  # Brief pause before first question
            await self.send_next_question(ctx)
            
        except Exception as e:
            logger.error(f"Error starting game in channel {ctx.channel.id}: {str(e)}", exc_info=True)
            await ctx.send("❌ An error occurred while starting the game. Please try again with `/trivia`.")

    async def send_next_question(self, ctx: commands.Context):
        """Send the next question to the channel."""
        try:
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
                    f"🎮 **Game Over!**\n\n"
                    f"🏆 **Final Score:** {score}/{len(self.questions)} ({percentage:.1f}%)\n\n"
                    f"Want to play again? Use /trivia!"
                )
                del self.current_games[channel_id]
                return
                
            question = self.questions[game['questions_asked']]
            game['current_question'] = question
            
            message = (
                f"🎯 **Question {game['questions_asked'] + 1}/{len(self.questions)}**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 {question['question']}\n\n"
                f"Select your answer from the options below:"
            )
            
            view = await self.create_answer_view(question['options'])
            await ctx.send(message, view=view)
            
        except Exception as e:
            logger.error(f"Error in send_next_question: {str(e)}", exc_info=True)
            await ctx.send("An error occurred while sending the next question. Please try starting a new game with /trivia")
            if channel_id in self.current_games:
                del self.current_games[channel_id]

    async def handle_answer(self, interaction: discord.Interaction, answer: str):
        """Handle user's answer selection."""
        try:
            channel_id = interaction.channel.id
            game = self.current_games.get(channel_id)
            
            if not game or not game['current_question']:
                logger.warning(f"No active game found for channel {channel_id}")
                await interaction.followup.send(
                    "No active game found. Start a new game with /trivia",
                    ephemeral=True
                )
                return

            logger.info(f"Processing answer for game in channel {channel_id}")
            
            question = game['current_question']
            is_correct = answer == question['correct']
            
            if is_correct:
                game['score'] += 1
                logger.info(f"Correct answer by {interaction.user}! New score: {game['score']}")
            
            # Update game state
            game['questions_asked'] += 1
            logger.info(f"Updated questions asked to: {game['questions_asked']}")
            
            # Format result message
            if is_correct:
                result_message = (
                    f"✨ **Correct!** Excellent work! ✨\n\n"
                    f"📚 **Learn More:**\n{question['explanation']}\n\n"
                    f"🎯 **Score:** {game['score']}/{game['questions_asked']}"
                )
            else:
                correct_option = question['options'][question['correct']]
                result_message = (
                    f"❌ **Not quite!**\n\n"
                    f"The correct answer was:\n"
                    f"✅ **{question['correct']}:** {correct_option}\n\n"
                    f"📚 **Learn More:**\n{question['explanation']}\n\n"
                    f"🎯 **Score:** {game['score']}/{game['questions_asked']}"
                )
            
            # Send result and check game status
            await interaction.followup.send(result_message)
            await asyncio.sleep(2)  # Brief pause
            
            if game['questions_asked'] >= len(self.questions):
                percentage = (game['score'] / len(self.questions)) * 100
                final_message = (
                    f"🎮 **Game Over!**\n\n"
                    f"🏆 **Final Score:** {game['score']}/{len(self.questions)} ({percentage:.1f}%)\n\n"
                )
                
                if percentage >= 80:
                    final_message += "🌟 Outstanding performance! You really know your stuff!"
                elif percentage >= 60:
                    final_message += "👏 Well done! You've got a good grasp of the concepts!"
                else:
                    final_message += "Keep learning! Every game is a chance to improve! 📚"
                
                final_message += "\n\nWant to play again? Use /trivia!"
                await interaction.followup.send(final_message)
                del self.current_games[channel_id]
            else:
                # Send next question
                context = await get_context_from_interaction(interaction)
                if context:
                    await asyncio.sleep(1)
                    await self.send_next_question(context)
                
        except Exception as e:
            logger.error(f"Error in handle_answer: {str(e)}", exc_info=True)
            await interaction.followup.send(
                "An error occurred while processing your answer. Please try again with /trivia",
                ephemeral=True
            )