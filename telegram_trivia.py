import random
import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

class TelegramTrivia:
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
                "question": "What is the maximum funding cap for a single project from the Matched Rewards pool?",
                "options": {
                    "A": "10%",
                    "B": "15%",
                    "C": "20%",
                    "D": "25%"
                },
                "correct": "C",
                "explanation": "A maximum funding cap of 20% of the total Matched Rewards fund (including Patron mode) ensures balanced distribution. Users can still donate to projects at the cap, but these won't receive additional matching."
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
