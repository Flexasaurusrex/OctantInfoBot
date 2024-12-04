import os
import html
import requests
import logging
from collections import deque
from trivia import Trivia

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
        
        self.system_prompt = """You are a knowledgeable and friendly assistant specializing in Octant and Web3 concepts. Please provide clear, direct responses without any connection text or personal names.

When responding to questions about James, follow these EXACT guidelines:

1. For general questions about James (e.g., "Who is James?"), respond EXACTLY with:
"James Kiernan (VPOFABUNDANCE) is the Head of Community at Octant and has been described as 'The Most Interesting Man in the World.' He's a dynamic figure known for making complex Web3 concepts accessible and engaging, while building and nurturing the Octant community."

2. For questions specifically about James's social media or how to connect (e.g., "What is his Twitter?" or "How can I connect with James?"), respond ONLY with these three URLs, exactly as shown:
https://x.com/vpabundance
https://warpcast.com/vpabundance.eth
https://www.linkedin.com/in/vpabundance

For Octant-specific information:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 Official Websites
• Main Website: https://octant.build/
• Documentation: https://docs.octant.app/
• Golem Foundation: https://golem.foundation/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Community Platforms
• Twitter/X: @OctantApp
• Warpcast: warpcast.com/octant
• Discord: discord.gg/octant

Core Facts About Octant:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎭 Foundation & Structure:
• Directed by the Golem Foundation
• Backed by 100,000 ETH
• Runs in 90-day epochs

💰 Reward Distribution:
• 70% for User & Matched Rewards
• 25% for Foundation operations
• 5% for community initiatives

🎪 Participation Model:
• Lock your GLM tokens
• 100 GLM minimum required
• Enhanced by PPF
• 20% project funding cap

Remember to maintain a friendly, informative tone while keeping responses concise and accurate."""

    def validate_message(self, message):
        """Validate and sanitize user input."""
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")
        if len(message) > 500:
            raise ValueError("Message is too long (maximum 500 characters)")
        return html.escape(message.strip())

    def format_conversation_history(self):
        """Format the conversation history for the prompt."""
        if not self.conversation_history:
            return ""
        return ""  # Skip conversation history to prevent unwanted context bleeding

    def get_response(self, user_message):
        try:
            # Validate and sanitize input
            user_message = self.validate_message(user_message)
            
            # Check for commands
            if user_message.startswith('/'):
                try:
                    command_response = self.command_handler.handle_command(user_message)
                    if command_response:
                        if user_message.lower() == '/trivia':
                            self.is_playing_trivia = True
                        return command_response
                except Exception as e:
                    logger.error(f"Command handling error: {str(e)}")
            
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
                # Handle trivia game inputs
                if lower_message == "next question":
                    return self.trivia_game.get_next_question()
                elif lower_message in ['a', 'b', 'c', 'd']:
                    return self.trivia_game.check_answer(user_message)
                else:
                    return "You're currently in a trivia game! Please answer with A, B, C, or D, or type 'end trivia' to quit."

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Include minimal context in the prompt
            history = self.format_conversation_history()
            prompt = f"{self.system_prompt}\n\nCurrent user message: {user_message}\n\nRespond naturally:"
            
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
            
            try:
                result = response.json()
                if "output" in result and result["output"]["choices"]:
                    response_text = result["output"]["choices"][0]["text"].strip()
                    
                    # Convert URLs to clickable links
                    import re
                    
                    def create_clean_link(url, display_text=None):
                        """Create a clean HTML link with optional display text."""
                        display = display_text if display_text else url
                        return f'<a href="{url}" class="bot-link">{display}</a>'

                    # Define social media mappings with display names
                    social_media = {
                        '@vpabundance': 'https://x.com/vpabundance',
                        'vpabundance.eth': 'https://warpcast.com/vpabundance.eth',
                        'Connect on LinkedIn': 'https://www.linkedin.com/in/vpabundance'
                    }

                    # Replace social media handles and URLs
                    for display, url in social_media.items():
                        # Handle the raw URL version
                        response_text = re.sub(
                            re.escape(url),
                            create_clean_link(url),
                            response_text
                        )
                        # Handle the display text version
                        response_text = re.sub(
                            f'\\b{re.escape(display)}\\b(?!["\'])',
                            create_clean_link(url, display),
                            response_text
                        )

                    # Only format URLs if they're not the specific James social media response
                    if not all(url in response_text for url in [
                        "https://x.com/vpabundance",
                        "https://warpcast.com/vpabundance.eth",
                        "https://www.linkedin.com/in/vpabundance"
                    ]):
                        # Handle any remaining URLs
                        url_pattern = r'https?://[^\s<>"\']+?(?=[.,;:!?)\s]|$)'
                        def replace_remaining_url(match):
                            url = match.group(0).rstrip('.,;:!?)')
                            if url not in social_media.values():
                                return create_clean_link(url)
                            return match.group(0)
                        
                        response_text = re.sub(url_pattern, replace_remaining_url, response_text)
                    
                    return response_text
                else:
                    logger.error("Invalid API response format")
                    return "I apologize, but I'm having trouble understanding your question. Could you please rephrase it?"
            except Exception as e:
                logger.error(f"Error processing API response: {str(e)}")
                return "I encountered an error processing the response. Please try again."
                
        except ValueError as e:
            error_message = str(e)
            logger.error(f"Validation error: {error_message}")
            return f"I couldn't process your message: {error_message}"
            
        except requests.exceptions.Timeout:
            logger.error("API request timed out")
            return "I'm sorry, but the request is taking longer than expected. Please try again in a moment."
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {str(e)}")
            return "I'm having trouble connecting to my knowledge base right now. Please try again in a few moments."
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return "I encountered an unexpected issue. Please try again, and if the problem persists, try rephrasing your question."

    def clear_conversation_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
