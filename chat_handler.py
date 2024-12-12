import os
import html
import requests
from collections import deque
from trivia import Trivia
import logging

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

    def validate_response_length(self, response):
        """Validate response length and split if necessary."""
        max_length = 4096  # Telegram's max message length
        if len(response) <= max_length:
            return [response]
        
        # Try to find better split points at paragraph boundaries
        paragraphs = response.split('\n\n')
        
        # If we only have one paragraph, fall back to sentence splitting
        if len(paragraphs) <= 1:
            current_chunk = ""
            chunks = []
            sentences = response.split('. ')
            
            for sentence in sentences:
                potential_chunk = current_chunk + sentence + '. '
                if len(potential_chunk) <= max_length:
                    current_chunk = potential_chunk
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + '. '
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            return chunks
        
        # Combine paragraphs into chunks
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
                
            if len(current_chunk) + len(paragraph) + 4 <= max_length:  # +4 for \n\n
                current_chunk += (paragraph + '\n\n')
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                if len(paragraph) > max_length:
                    # If a single paragraph is too long, split it into sentences
                    sentences = paragraph.split('. ')
                    sub_chunk = ""
                    for sentence in sentences:
                        if len(sub_chunk) + len(sentence) + 2 <= max_length:
                            sub_chunk += sentence + '. '
                        else:
                            if sub_chunk:
                                chunks.append(sub_chunk.strip())
                            sub_chunk = sentence + '. '
                    if sub_chunk:
                        chunks.append(sub_chunk.strip())
                else:
                    current_chunk = paragraph + '\n\n'
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

    def get_response(self, user_message):
        try:
            # Basic validation - just check for empty messages
            if not user_message or not user_message.strip():
                return "I couldn't process an empty message. Please try asking something!"
            
            user_message = user_message.strip()
            
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
                # Check for trivia-specific commands first
                if lower_message == "next question":
                    return self.trivia_game.get_next_question()
                elif lower_message in ['a', 'b', 'c', 'd']:
                    return self.trivia_game.check_answer(user_message)
                elif lower_message.startswith('/') or lower_message in ['help', 'stats', 'learn']:
                    # Allow certain commands during trivia
                    command_response = self.command_handler.handle_command(user_message)
                    if command_response:
                        return command_response
                    self.is_playing_trivia = False
                else:
                    # Only exit trivia mode if explicitly requested or after game completion
                    if lower_message != "end trivia":
                        return "You're currently in a trivia game! Please answer with A, B, C, or D, or type 'end trivia' to quit."
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Include minimal context in the prompt
            history = self.format_conversation_history()
            prompt = f"{self.system_prompt}\n\n{history}Current user message: {user_message}\n\nRespond naturally and informatively about Octant, Golem Foundation, and related topics:"
            
            data = {
                "model": self.model,
                "prompt": prompt,
                "max_tokens": 2048,  # Increased for longer responses
                "temperature": 0.7,
                "top_p": 0.9,  # Increased for more diverse responses
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

                def format_urls(text):
                    """Format URLs in text, keeping social media links clean."""
                    # Remove any HTML class attributes
                    text = re.sub(r'class="[^"]*"', '', text)
                    
                    # Handle James's social media response
                    social_urls = [
                        "https://x.com/vpabundance",
                        "https://warpcast.com/vpabundance.eth",
                        "https://www.linkedin.com/in/vpabundance"
                    ]
                    
                    # If it's a social media response, return as is
                    if all(url in text for url in social_urls):
                        return text
                    
                    # Process other URLs
                    def clean_url(match):
                        url = match.group(0).rstrip('.,;:!?)"')
                        url = url.strip('"').strip()
                        
                        # Keep social media links as plain URLs
                        if any(domain in url.lower() for domain in ['x.com', 'warpcast.com', 'linkedin.com']):
                            return url
                        
                        # Format other URLs as HTML links
                        return f'<a href="{url}">{url}</a>'
                    
                    # Find and replace URLs
                    url_pattern = r'https?://(?:www\.)?[^\s<>"\']+?(?=[.,;:!?)\s]|$)'
                    return re.sub(url_pattern, clean_url, text)
                
                # Format the response text
                response_text = format_urls(response_text)
                
                # Clean up any remaining bot-link references
                response_text = re.sub(r'">(?:https?://[^<]+?)</a>', lambda m: '">' + m.group(0)[2:-4] + '</a>', response_text)
                
                # Validate and split response if necessary
                response_chunks = self.validate_response_length(response_text)
                
                # Log formatted response for verification
                print(f"Formatted response ({len(response_chunks)} chunks): {response_text}")
                
                # Update conversation history with the complete response
                self.conversation_history.append({
                    "user": user_message,
                    "assistant": response_text
                })
                
                # Keep only the last max_history entries
                if len(self.conversation_history) > self.max_history:
                    self.conversation_history = self.conversation_history[-self.max_history:]
                
                # Try to combine response chunks if possible
                if len(response_chunks) > 1:
                    # If all chunks combined are under 4000 characters, combine them
                    total_length = sum(len(chunk) for chunk in response_chunks)
                    if total_length <= 4000:
                        return '\n\n'.join(response_chunks)
                return response_chunks[0] if len(response_chunks) == 1 else response_chunks
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
            logger.error(f"API request error: {str(e)}")
            return """I apologize for the temporary issue. I'm here to help you with:

• Octant's ecosystem and features
• GLM token utility and staking
• Governance and funding mechanisms
• Community participation

Please try your question again or ask about any of these topics!"""
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return "I encountered an unexpected issue. Please try again, and if the problem persists, try rephrasing your question."
            
    def clear_conversation_history(self):
        """Clear the conversation history."""
        self.conversation_history = []