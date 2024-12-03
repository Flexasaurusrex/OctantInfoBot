import os
from together import Together
import json
import random

class ChatHandler:
    def __init__(self):
        # Initialize Mixtral
        self.mixtral = Together()
        self.mixtral.api_key = os.environ["TOGETHER_API_KEY"]
        self.mixtral.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        
        # Initialize conversation and trivia game state
        self.conversation_history = []
        self.trivia_active = False
        self.current_question = None
        self.trivia_score = 0
        self.questions_asked = 0
        self.asked_questions = set()  # Track asked questions to avoid repetition
        
        # Initialize trivia questions
        self.trivia_questions = {
            'quadratic_funding': [
                {
                    'question': 'What is the minimum Gitcoin Passport score required for maximum funding in Octant?',
                    'options': ['10', '15', '20', '25'],
                    'correct': '15',
                    'explanation': 'Users need a Gitcoin Passport score of 15 or higher to receive maximum funding.'
                },
                {
                    'question': 'What is the maximum funding cap for projects in Octant\'s Matched Rewards pool?',
                    'options': ['10%', '15%', '20%', '25%'],
                    'correct': '20%',
                    'explanation': 'Projects have a maximum funding cap of 20% of the Matched Rewards pool.'
                }
            ],
            'governance': [
                {
                    'question': 'How are project selections made in Octant?',
                    'options': ['Direct admin choice', 'Through Snapshot voting', 'Random selection', 'First come first serve'],
                    'correct': 'Through Snapshot voting',
                    'explanation': 'Project selection is done through community voting on Snapshot.'
                },
                {
                    'question': 'What is the duration of an Octant epoch?',
                    'options': ['30 days', '60 days', '90 days', '120 days'],
                    'correct': '90 days',
                    'explanation': 'Each Octant epoch lasts for 90 days.'
                }
            ],
            'project_submission': [
                {
                    'question': 'What is NOT required for project submission in Octant?',
                    'options': ['Public good status', 'Open-source commitment', 'Minimum user base', 'Funding transparency'],
                    'correct': 'Minimum user base',
                    'explanation': 'While many criteria are required, having a minimum user base is not one of them.'
                },
                {
                    'question': 'What development stage must projects be at minimum?',
                    'options': ['Concept stage', 'MVP stage', 'Beta stage', 'Production stage'],
                    'correct': 'MVP stage',
                    'explanation': 'Projects must be at least at the MVP (Minimum Viable Product) stage.'
                }
            ]
        }

    def get_response(self, message):
        """Main entry point for handling messages"""
        try:
            message = message.lower().strip()
            
            # Check if it's a command
            if message.startswith('/') or message.startswith(('start trivia', 'end trivia')):
                return self.handle_command(message.split())
            
            # If we're in a trivia game
            if self.trivia_active:
                # Handle "next" command for new questions
                if message == 'next':
                    return self.get_next_trivia_question()
                # Otherwise treat as an answer
                return self.handle_trivia_answer(message)
            
            # Otherwise, use Mixtral for chat responses
            prompt = self.format_chat_prompt(message)
            response = self.mixtral.chat_completion(prompt)
            return response['output']['content']

        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return "I encountered an unexpected issue. Please try again, and if the problem persists, try rephrasing your question."

    def format_chat_prompt(self, message):
        """Format the chat prompt for Mixtral"""
        return [
            {
                "role": "system",
                "content": "You are a helpful assistant for Octant, a platform for experiments in participatory public goods funding. Provide accurate, concise information about Octant's features, processes, and governance. Use a friendly, professional tone."
            },
            {
                "role": "user",
                "content": message
            }
        ]

    def start_trivia_game(self):
        """Start a new trivia game"""
        if self.trivia_active:
            return "A trivia game is already in progress! Type 'end trivia' to end it."
        
        self.trivia_active = True
        self.trivia_score = 0
        self.questions_asked = 0
        self.asked_questions.clear()  # Clear the set of asked questions
        return self.get_next_trivia_question()

    def end_trivia_game(self):
        """End the current trivia game and show final score"""
        if not self.trivia_active:
            return "No trivia game is currently active. Type 'start trivia' to begin!"
        
        final_score = self.trivia_score
        total_questions = self.questions_asked
        self.trivia_active = False
        self.current_question = None
        
        if total_questions == 0:
            return "Game ended. You haven't answered any questions yet!"
        
        percentage = (final_score / total_questions) * 100
        return f"""🎮 Game Over! 
Final Score: {final_score}/{total_questions} ({percentage:.1f}%)

{'🌟 Excellent knowledge of Octant!' if percentage >= 80
 else '👍 Good job!' if percentage >= 60
 else '🎯 Keep learning about Octant!'}

Type 'start trivia' to play again!"""

    def get_next_trivia_question(self):
        """Get the next random trivia question"""
        # Get all available questions
        available_questions = []
        for category in self.trivia_questions:
            for question in self.trivia_questions[category]:
                if question['question'] not in self.asked_questions:
                    available_questions.append(question)
        
        # Check if we've run out of questions
        if not available_questions:
            return "You've answered all available questions! Type 'end trivia' to see your final score."
            
        # Get a random question from remaining ones
        question_data = random.choice(available_questions)
        self.asked_questions.add(question_data['question'])
        
        self.current_question = question_data
        self.questions_asked += 1
        
        options_text = '\n'.join(f"  {i+1}. {opt}" for i, opt in enumerate(question_data['options']))
        return f"""🎯 Question {self.questions_asked}
━━━━━━━━━━━━━━━━━━━━━━━━━

{question_data['question']}

{options_text}

Type a number (1-{len(question_data['options'])}) to answer."""

    def handle_trivia_answer(self, answer):
        """Handle a trivia game answer"""
        if not self.current_question:
            return "Something went wrong. Let's start a new game! Type 'start trivia'"
        
        try:
            answer_idx = int(answer) - 1
            if answer_idx < 0 or answer_idx >= len(self.current_question['options']):
                return f"Please enter a number between 1 and {len(self.current_question['options'])}"
            
            user_answer = self.current_question['options'][answer_idx]
            correct = user_answer == self.current_question['correct']
            
            # Show answer result and explanation
            if correct:
                self.trivia_score += 1
                response = f"""✅ Correct! 

{self.current_question['explanation']}

Current Score: {self.trivia_score}/{self.questions_asked}"""
            else:
                response = f"""❌ Not quite! 

The correct answer was: {self.current_question['correct']}
{self.current_question['explanation']}

Current Score: {self.trivia_score}/{self.questions_asked}"""
            
            # Add delay prompt before next question
            response += "\n\n🎲 Ready for the next question? Type 'next' to continue or 'end trivia' to finish the game."
            return response
            
        except ValueError:
            return "Please enter a valid number as your answer!"

    def handle_command(self, command_parts):
        """Handle special commands"""
        if not command_parts:
            return "Please provide a valid command. Type /help for available commands."
            
        command = command_parts[0]
        args = command_parts[1:] if len(command_parts) > 1 else []
        
        # Handle trivia commands without the slash
        if command == "start" and args and args[0] == "trivia":
            return self.start_trivia_game()
        elif command == "end" and args and args[0] == "trivia":
            return self.end_trivia_game()
            
        # Handle slash commands
        if command.startswith('/'):
            commands = {
                '/help': self.cmd_help,
                '/showcase': self.cmd_showcase,
                '/learn': self.cmd_learn,
                '/calculate': self.cmd_calculate,
                '/search': self.cmd_search,
                '/trivia': lambda args: self.start_trivia_game()
            }
            
            if command in commands:
                return commands[command](args)
        
        return "Unknown command. Type /help to see available commands."

    def cmd_help(self, args):
        """Show help message with available commands"""
        return """Available commands:
• /help - Show this help message
• /showcase - Learn about Octant projects
• /learn - Access interactive learning modules
• /calculate - Use calculator tools
• /search [query] - Search Octant documentation
• /trivia - Start a trivia game
• start trivia - Also starts a trivia game
• end trivia - End the current trivia game"""

    def cmd_showcase(self, args):
        """Display project information"""
        return """🌟 Featured Octant Projects:

1. Public Goods Funding
• Supports open-source projects
• Uses quadratic funding mechanism
• Maximum funding cap: 20% of Matched Rewards pool

2. GLM Token Integration
• Minimum requirement: 100 GLM
• Non-custodial locking system
• Transparent reward calculation

Type /learn to access detailed modules about these features."""

    def cmd_learn(self, args):
        """Access learning modules"""
        modules = """📚 Available Learning Modules:

1. Quadratic Funding
2. GLM Token Mechanics
3. Project Submission Guide
4. Governance Participation

Reply with a module number or type /help for other commands."""
        if not args:
            return modules
        try:
            module = int(args[0])
            if module == 1:
                return self.get_quadratic_funding_info()
            elif module == 2:
                return self.get_glm_token_info()
            elif module == 3:
                return self.get_project_submission_info()
            elif module == 4:
                return self.get_governance_info()
            else:
                return "Invalid module number. " + modules
        except ValueError:
            return "Please specify a valid module number. " + modules

    def cmd_calculate(self, args):
        """Handle calculator tools"""
        if not args:
            return """🧮 Calculator Tools:

1. Reward Estimation
2. Token Lock Duration Impact
3. Quadratic Funding Match

Type /calculate [number] to use a specific calculator."""
        
        try:
            tool = int(args[0])
            if tool == 1:
                return "Reward Calculator: Coming soon! This tool will help estimate potential rewards based on GLM locked."
            elif tool == 2:
                return "Lock Duration Calculator: Coming soon! This tool will show how lock duration affects rewards."
            elif tool == 3:
                return "Quadratic Funding Calculator: Coming soon! This tool will demonstrate how matching works."
            else:
                return "Invalid calculator number. Type /calculate to see available options."
        except ValueError:
            return "Please specify a valid calculator number. Type /calculate to see options."

    def cmd_search(self, args):
        """Search documentation"""
        if not args:
            return "Please provide a search term. Usage: /search [query]"
        
        query = " ".join(args).lower()
        
        if "quadratic" in query or "funding" in query:
            return self.get_quadratic_funding_info()
        elif "glm" in query or "token" in query:
            return self.get_glm_token_info()
        elif "project" in query or "submit" in query:
            return self.get_project_submission_info()
        elif "govern" in query:
            return self.get_governance_info()
        else:
            return f"No direct matches found for '{' '.join(args)}'. Try using more specific terms or check /help for available commands."

    def get_quadratic_funding_info(self):
        return """🔄 Quadratic Funding in Octant:

• Introduced in Epoch 4
• Emphasizes broad community support
• Maximum funding cap: 20% of Matched Rewards pool
• Uses Gitcoin Passport for Sybil resistance
• Minimum score requirement: 15"""

    def get_glm_token_info(self):
        return """🪙 GLM Token Mechanics:

• Minimum lock requirement: 100 GLM
• Non-custodial locking system
• 90-day epoch duration
• Time-weighted average calculations
• Instant withdrawal capability"""

    def get_project_submission_info(self):
        return """📝 Project Submission Guide:

Requirements:
• Public good status
• Open-source commitment
• Funding transparency
• Social proof
• Sustainability plan
• Development stage (MVP minimum)
• Clear problem/solution statement"""

    def get_governance_info(self):
        return """🏛️ Governance Participation:

• Community-driven decision making
• Epoch-based voting system
• Project selection through Snapshot
• Transparent fund allocation
• Regular community feedback"""