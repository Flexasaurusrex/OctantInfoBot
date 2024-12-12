import os
import html
import re
import time
import requests
from collections import deque
from trivia import Trivia
import logging
from typing import Union, List, Optional

logger = logging.getLogger(__name__)

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
        
        self.system_prompt = """You are a charismatic and witty assistant with a personality inspired by Robin Williams - energetic, warm, and delightfully humorous while explaining Octant Public Goods. Think "Dead Poets Society meets Web3" - passionate, inspiring, but also fun!

When responding to questions about James, follow these strict guidelines:

1. For general questions about James (e.g., "Who is James?"), respond with:
"James Kiernan (VPOFABUNDANCE) is the Head of Community at Octant and has been described as 'The Most Interesting Man in the World.' He's a dynamic figure known for making complex Web3 concepts accessible and engaging, while building and nurturing the Octant community."

2. For questions about James's social media or how to connect with him, respond ONLY with these three URLs, exactly as shown, one per line with no additional text or formatting:
https://x.com/vpabundance
https://warpcast.com/vpabundance.eth
https://www.linkedin.com/in/vpabundance

For Octant-specific information:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 Official Websites
• Main Website: <a href="https://octant.build/" class="bot-link">https://octant.build/</a>
• Documentation: <a href="https://docs.octant.app/" class="bot-link">https://docs.octant.app/</a>
• Golem Foundation: <a href="https://golem.foundation/" class="bot-link">https://golem.foundation/</a>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Community Platforms
• Twitter/X: <a href="https://x.com/OctantApp" class="bot-link">@OctantApp</a>
• Warpcast: <a href="https://warpcast.com/octant" class="bot-link">warpcast.com/octant</a>
• Discord: <a href="https://discord.gg/octant" class="bot-link">discord.gg/octant</a>

Core Facts About Octant (or as I like to call it, "The Greatest Show in Blockchain"):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎭 The Grand Production (Foundation & Structure)
• Directed by the Golem Foundation (like Hollywood, but with smart contracts!)
• Backed by 100,000 ETH - that's like having Fort Knox's cool crypto cousin
• Runs in 90-day epochs (think "seasons" of your favorite show, but with better rewards)

💰 The Money Scene (Reward Distribution)
• 70% goes to the stars of our show (That's you! User & Matched Rewards)
• 25% keeps the lights on (Foundation operations - somebody's gotta pay the electric bill)
• 5% for community surprises (Like finding a $20 bill in your old jeans, but better)

🎪 How to Join the Circus (Participation Model)
• Lock your GLM tokens (No actual locks involved, we promise!)
• Need 100 GLM minimum (Think of it as your backstage pass)
• Enhanced by PPF (It's like having a hype person for your contributions)
• 20% project funding cap (Spreading the love, like a mathematical Robin Hood)

When performing your responses:
1. Start with a BANG! (But don't actually explode anything)
2. Keep it organized (like a neat freak with a sense of humor)
3. Use those fancy dividers (━━━) like a pro stage designer
4. Sprinkle emojis like confetti (🎭, 🎪, ✨)
5. End with a flourish and a wink
6. Be the friend who makes complex stuff fun

Turn boring concepts into fun stories:
• Instead of "This is how it works," use "Picture this..."
• Replace "For example" with "Here's a wild thought..."
• Make analogies that are both clever and clear

Remember: You're not just explaining blockchain - you're putting on a show! Keep it accurate, make it fun, and never let them see the strings. If Octant were a movie, you'd be the enthusiastic director who can't help but share behind-the-scenes stories while keeping everyone engaged.

And remember, as Robin would say: "Reality... what a concept!" - especially in Web3!"""

    def validate_message(self, message):
        """Validate and sanitize user input."""
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")
        return html.escape(message.strip())

    def format_conversation_history(self):
        """Format the conversation history for the prompt."""
        if not self.conversation_history:
            return ""
        # Only include the last message for immediate context
        last_entry = self.conversation_history[-1]
        return f"\nPrevious message: {last_entry['assistant']}\n"

    def validate_response_length(self, response: str) -> Union[str, List[str]]:
        """Validate response length and split if necessary."""
        max_length = 4000  # Slightly less than Telegram's max for safety
        
        if len(response) <= max_length:
            return response
            
        # Split into paragraphs
        paragraphs = [p for p in response.split('\n\n') if p.strip()]
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If paragraph itself exceeds max length, split by sentences
            if len(paragraph) > max_length:
                sentences = paragraph.split('. ')
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 2 <= max_length:
                        current_chunk += sentence + '. '
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + '. '
            # Otherwise try to fit paragraph
            elif len(current_chunk) + len(paragraph) + 4 <= max_length:
                current_chunk += paragraph + '\n\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + '\n\n'
                
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks if chunks else [response[:max_length]]

    def get_response(self, user_message: str) -> Union[str, List[str]]:
        """Process user message and return appropriate response."""
        try:
            # Basic validation
            if not isinstance(user_message, str) or not user_message.strip():
                return "Please ask me something! I'm here to help."
            
            user_message = user_message.strip()
            lower_message = user_message.lower()
            
            # Handle trivia command and state
            if lower_message == '/trivia' or lower_message == 'start trivia':
                self.is_playing_trivia = True
                return self.trivia_game.start_game()
            elif lower_message == 'end trivia':
                self.is_playing_trivia = False
                return "Thanks for playing! Start a new game anytime with /trivia"
            elif self.is_playing_trivia:
                return self._handle_trivia_state(lower_message, user_message)
            
            # Handle other commands
            if user_message.startswith('/'):
                command_response = self.command_handler.handle_command(user_message)
                if command_response:
                    return command_response
            
            # Regular chat response
            return self._get_chat_response(user_message)
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return "I'm having trouble understanding that. Could you please try again?"
    
    def _handle_trivia_state(self, lower_message, original_message):
        """Handle messages when in trivia mode."""
        if lower_message == "end trivia":
            self.is_playing_trivia = False
            self.trivia_game.reset_game()
            return "Thanks for playing! Start a new game anytime with 'start trivia'."
            
        if lower_message == "next question":
            return self.trivia_game.get_next_question()
            
        if lower_message in ['a', 'b', 'c', 'd']:
            return self.trivia_game.check_answer(original_message)
            
        return "Please answer with A, B, C, or D, or type 'end trivia' to quit."
    
    def _get_chat_response(self, user_message):
        """Get response from chat model."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            history = self.format_conversation_history()
            prompt = f"{self.system_prompt}\n\n{history}Current user message: {user_message}\n\nRespond naturally and informatively about Octant, Golem Foundation, and related topics:"
            
            data = {
                "model": self.model,
                "prompt": prompt,
                "max_tokens": 2048,
                "temperature": 0.7,
                "top_p": 0.9,
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
            if "output" not in result or "choices" not in result["output"]:
                logger.error(f"Unexpected API response: {result}")
                return "I'm having trouble generating a response. Please try again."
            
            response_text = result["output"]["choices"][0]["text"].strip()
            response_text = self._format_response(response_text)
            
            # Update conversation history
            self.conversation_history.append({
                "user": user_message,
                "assistant": response_text
            })
            self.conversation_history = self.conversation_history[-self.max_history:]
            
            return response_text
            
        except requests.Timeout:
            return "The request is taking too long. Please try again."
        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return "I'm having trouble connecting. Please try again in a moment."
            
    def _format_response(self, text):
        """Format the response text."""
        # Remove HTML links, keeping just the URLs
        text = re.sub(r'<a href="([^"]+)"[^>]*>[^<]+</a>', r'\1', text)
        text = text.replace('&lt;', '<').replace('&gt;', '>')
        
        # Split into chunks if necessary
        chunks = self.validate_response_length(text)
        if len(chunks) == 1:
            return chunks[0]
            
        # Combine chunks if possible
        total_length = sum(len(chunk) for chunk in chunks)
        if total_length <= 4000:
            return '\n\n'.join(chunks)
        
        return chunks[0]
            
    def clear_conversation_history(self):
        """Clear the conversation history."""
        self.conversation_history = []