import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

class TelegramTrivia:
    def __init__(self):
        self.questions = [
            {
                "question": "What is Octant's main funding mechanism?",
                "options": {
                    "A": "Traditional Grants",
                    "B": "Quadratic Funding",
                    "C": "Direct Donations",
                    "D": "Private Investment"
                },
                "correct": "B",
                "explanation": "Octant uses Quadratic Funding which considers both the number of unique contributors and the amount donated, giving more weight to projects with broad community support."
            },
            {
                "question": "What percentage of staking yield contributes to Octant's Total Rewards budget?",
                "options": {
                    "A": "50%",
                    "B": "60%",
                    "C": "70%",
                    "D": "80%"
                },
                "correct": "C",
                "explanation": "70% of the staking yield contributes to Octant's Total Rewards budget, split evenly between User Rewards and Matched Rewards."
            },
            {
                "question": "What is the minimum effective GLM balance required to qualify for user rewards?",
                "options": {
                    "A": "1 GLM",
                    "B": "50 GLM",
                    "C": "100 GLM",
                    "D": "500 GLM"
                },
                "correct": "C",
                "explanation": "While you can lock as little as 1 GLM, a minimum effective balance of 100 GLM is required to qualify for user rewards."
            }
        ]
        self.current_games = {}  # Store game state per user
        
    def get_keyboard_markup(self, options):
        """Create Telegram inline keyboard for options."""
        keyboard = []
        for key, value in options.items():
            keyboard.append([InlineKeyboardButton(f"{key}. {value}", callback_data=f"trivia_{key}")])
        return InlineKeyboardMarkup(keyboard)

    async def start_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start a new trivia game for a user."""
        user_id = update.effective_user.id
        self.current_games[user_id] = {
            'score': 0,
            'questions_asked': 0,
            'current_question': None
        }
        
        await self.send_next_question(update, context)

    async def send_next_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send the next question to the user."""
        user_id = update.effective_user.id
        game = self.current_games.get(user_id)
        
        if not game:
            await update.message.reply_text("Please start a new game with /trivia")
            return
            
        if game['questions_asked'] >= len(self.questions):
            # Game finished
            score = game['score']
            percentage = (score / len(self.questions)) * 100
            await update.message.reply_text(
                f"🎮 Game Over!\n\n"
                f"🏆 Final Score: {score}/{len(self.questions)} ({percentage:.1f}%)\n\n"
                f"Want to play again? Use /trivia!"
            )
            del self.current_games[user_id]
            return
            
        question = self.questions[game['questions_asked']]
        game['current_question'] = question
        
        message = (
            f"🎯 Question {game['questions_asked'] + 1}/{len(self.questions)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📝 {question['question']}\n\n"
            f"Select your answer from the options below:"
        )
        
        await update.message.reply_text(
            message,
            reply_markup=self.get_keyboard_markup(question['options'])
        )

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user's answer selection."""
        query = update.callback_query
        user_id = update.effective_user.id
        game = self.current_games.get(user_id)
        
        if not game or not game['current_question']:
            await query.answer("No active game found. Start a new game with /trivia")
            return
            
        answer = query.data.split('_')[1]  # Extract A, B, C, or D from callback_data
        question = game['current_question']
        
        is_correct = answer == question['correct']
        if is_correct:
            game['score'] += 1
        
        # Update game state
        game['questions_asked'] += 1
        
        # Show result
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
        
        await query.answer()  # Clear the "loading" state of the button
        await query.message.reply_text(result_message)
        
        # Check if we still have questions before sending the next one
        if game['questions_asked'] < len(self.questions):
            # Send next question
            question = self.questions[game['questions_asked']]
            game['current_question'] = question
            
            message = (
                f"🎯 Question {game['questions_asked'] + 1}/{len(self.questions)}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 {question['question']}\n\n"
                f"Select your answer from the options below:"
            )
            
            await query.message.reply_text(
                message,
                reply_markup=self.get_keyboard_markup(question['options'])
            )
