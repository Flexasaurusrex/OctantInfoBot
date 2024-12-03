import os
import html
import requests
from collections import deque
from trivia import Trivia

class CommandHandler:
    def __init__(self, trivia_game):
        self.trivia_game = trivia_game
        self.commands = {
            '/help': self.help_command,
            '/stats': self.stats_command,
            '/learn': self.learn_command,
            '/funding': self.funding_command,
            '/governance': self.governance_command,
            '/rewards': self.rewards_command,
            '/trivia': self.trivia_command
        }

    def handle_command(self, command):
        command = command.lower().split()[0]  # Get the first word of the command
        if command in self.commands:
            return self.commands[command]()
        return None

    def help_command(self):
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Available Commands
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎮 Game Commands:
• /trivia - Start a trivia game
• start trivia - Also starts trivia game
• end trivia - End current trivia game

📋 Information Commands:
• /help - Show this help message
• /stats - View your chat statistics
• /learn - Access learning modules

📌 Topic-Specific Commands:
• /funding - Learn about Octant's funding
• /governance - Understand governance
• /rewards - Explore reward system

Type any command to get started!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    def stats_command(self):
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Chat Statistics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Coming soon! This feature will show:
• Messages exchanged
• Topics discussed
• Trivia performance
• Learning progress

Stay tuned for updates!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    def learn_command(self):
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Learning Modules
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Choose a topic to learn about:

1. Octant Basics
• What is Octant?
• How it works
• Getting started

2. Token Economics
• GLM token utility
• Staking mechanism
• Reward distribution

3. Participation Guide
• How to contribute
• Community roles
• Decision making

Type /funding, /governance, or /rewards 
for specific topic details.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    def funding_command(self):
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Octant Funding System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Key Components:
• Quadratic Funding mechanism
• Community-driven allocation
• Matched rewards system

📋 Funding Process:
1. Project Submission
2. Community Voting
3. Allocation Period
4. Distribution of Funds

🎯 Important Points:
• 20% maximum funding cap
• Anti-Sybil measures
• Transparent tracking

Want to learn more? Try /learn for 
detailed tutorials!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    def governance_command(self):
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏛️ Octant Governance
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Decision Making Process:
• Community-driven proposals
• Token-weighted voting
• Transparent execution

Key Areas:
1. Project Selection
2. Fund Allocation
3. Protocol Updates
4. Community Initiatives

Participation Methods:
• Submit proposals
• Vote on decisions
• Join discussions

For more details, use /learn command!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    def rewards_command(self):
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌟 Octant Rewards System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Types of Rewards:
• Individual Rewards (IR)
• Matched Rewards (MR)
• Community Incentives

Calculation Factors:
• Locked GLM amount
• Time-weighted average
• Community support level

Distribution Schedule:
• 90-day epochs
• Regular calculations
• Transparent tracking

Use /learn for detailed tutorials!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    def trivia_command(self):
        return self.trivia_game.start_game()

class ChatHandler:
    def __init__(self):
        self.api_key = os.environ.get("TOGETHER_API_KEY")
        if not self.api_key:
            raise ValueError("TOGETHER_API_KEY environment variable is not set")
        self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        self.base_url = "https://api.together.xyz/inference"
        self.conversation_history = []
        self.max_history = 5
        self.trivia_game = Trivia()
        self.is_playing_trivia = False
        self.command_handler = CommandHandler(self.trivia_game)
        
        self.system_prompt = """You are a friendly and clear-speaking assistant focused on explaining Octant Public Goods (https://octant.build/). 
        Your goal is to make complex information easy to understand by:

        1. Breaking down complex topics into simple points
        2. Using short, clear sentences
        3. Adding spacing between paragraphs for readability
        4. Using bullet points for lists
        5. Using emojis sparingly to highlight key sections
        6. Keep paragraphs short (2-3 sentences max)
        7. End with a simple summary if the answer is long

        Remember to format your response in a clear, easy-to-read way."""

    def validate_message(self, message):
        """Validate and sanitize user input."""
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")
        if len(message) > 500:
            raise ValueError("Message is too long (maximum 500 characters)")
        return html.escape(message.strip())

    def format_conversation_history(self):
        """Format the conversation history for the prompt."""
        history_text = ""
        for entry in self.conversation_history[-self.max_history:]:
            history_text += f"\nUser: {entry['user']}\nAssistant: {entry['assistant']}\n"
        return history_text

    def get_response(self, user_message):
        try:
            # Validate and sanitize input
            user_message = self.validate_message(user_message)
            
            # Check for commands
            if user_message.startswith('/'):
                command_response = self.command_handler.handle_command(user_message)
                if command_response:
                    if user_message.lower() == '/trivia':
                        self.is_playing_trivia = True
                    return command_response
            
            # Handle trivia commands
            lower_message = user_message.lower()
            if lower_message == "start trivia":
                self.is_playing_trivia = True
                return self.trivia_game.start_game()
            elif lower_message == "end trivia":
                self.is_playing_trivia = False
                self.trivia_game.reset_game()
                return "Thanks for playing Octant Trivia! Feel free to start a new game anytime by saying 'start trivia'."
            elif self.is_playing_trivia:
                lower_message = user_message.lower()
                if lower_message == "next question":
                    return self.trivia_game.get_next_question()
                return self.trivia_game.check_answer(user_message)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Include conversation history in the prompt
            history = self.format_conversation_history()
            prompt = f"{self.system_prompt}\n\nPrevious conversation:{history}\n\nUser: {user_message}\nAssistant:"
            
            data = {
                "model": self.model,
                "prompt": prompt,
                "max_tokens": 1024,
                "temperature": 0.7,
                "top_p": 0.7,
                "top_k": 50,
                "repetition_penalty": 1.1
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if "output" in result and result["output"]["choices"]:
                response_text = result["output"]["choices"][0]["text"].strip()
                # Convert URLs to clickable links
                import re
                url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
                response_text = re.sub(
                    url_pattern,
                    lambda m: f'<a href="{m.group(0)}" target="_blank" class="bot-link">{m.group(0)}</a>',
                    response_text
                )
                
                # Update conversation history
                self.conversation_history.append({
                    "user": user_message,
                    "assistant": response_text
                })
                
                # Keep only the last max_history entries
                if len(self.conversation_history) > self.max_history:
                    self.conversation_history = self.conversation_history[-self.max_history:]
                
                return response_text
            else:
                print("Unexpected API response format:", result)
                return "I apologize, but I couldn't generate a response at the moment. Please try again."
                
        except ValueError as e:
            error_message = str(e)
            print(f"Validation error: {error_message}")
            return f"I couldn't process your message: {error_message}"
            
        except requests.exceptions.Timeout:
            print("API request timed out")
            return "I'm sorry, but the request is taking longer than expected. Please try again in a moment."
            
        except requests.exceptions.RequestException as e:
            print(f"API request error: {str(e)}")
            return "I'm having trouble connecting to my knowledge base right now. Please try again in a few moments."
            
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return "I encountered an unexpected issue. Please try again, and if the problem persists, try rephrasing your question."
            
    def clear_conversation_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
