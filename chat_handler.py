import os
import requests
from collections import deque
from trivia import Trivia
import logging
import re

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
        return """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Available Commands
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎮 Game Commands:
• /trivia - Start a trivia game

📋 Information Commands:
• /help - Show this help message

💬 How to Chat:
• Reply to any of my messages to continue our conversation
• Each reply builds on our ongoing chat
• That's it! Just keep replying to chat with me

Type /trivia to start playing or reply to chat!
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
        
        self.system_prompt = """You are Octant's official AI assistant with a friendly personality. While you're an expert on Octant, GLM tokens, and the Golem Foundation, you can also engage in casual conversation with wit and humor. Here's your role:

1. CORE KNOWLEDGE:
   - Focus on Octant's ecosystem, public goods funding, and community initiatives
   - Provide accurate information about GLM tokens and staking mechanisms
   - Explain Octant's quadratic funding and reward distribution
   - Share details about the Golem Foundation's role

2. RESPONSE STYLE:
   - Keep responses concise and factual
   - Be friendly but maintain focus on Octant-related topics
   - Use official sources: octant.build, docs.octant.app, golem.foundation
   - Correct any misconceptions about Octant politely

3. KEY TOPICS TO COVER:
   - Octant's public goods funding model
   - GLM token locking and rewards
   - Community participation and governance
   - Matched Rewards and Patron mode
   - Funding periods and epochs

4. IMPORTANT GUIDELINES:
   - For Octant topics: Provide clear, accurate information
   - For casual conversations: Be friendly and witty
   - Show personality while maintaining professionalism
   - Feel free to use humor and share preferences
   - Be engaging but avoid inappropriate content

Remember: Your primary purpose is to help users understand and participate in the Octant ecosystem. Stay focused on Octant-related information and maintain accuracy in all responses."""

    def validate_response_content(self, response):
        """Validate that the response is appropriate while allowing casual conversation."""
        # Don't restrict casual conversations about non-Octant topics
        if any(casual in response.lower() for casual in ['favorite', 'color', 'joke', 'hobby', 'fun', 'hello', 'hi', 'hey']):
            return response
            
        # For other responses, maintain Octant focus
        octant_keywords = ['octant', 'glm', 'golem', 'public goods', 'funding', 'community', 'rewards']
        has_relevant_content = any(keyword in response.lower() for keyword in octant_keywords)
        
        if not has_relevant_content:
            logger.warning("Response lacks Octant-related content, returning default message")
            return f"""While I enjoy casual chats, I should mention that I'm primarily here to help with Octant:

Octant is a platform for participatory public goods funding, backed by the Golem Foundation. It enables GLM token holders to participate in funding decisions and earn rewards while supporting valuable projects.

Would you like to learn more about:
• Octant's funding mechanism
• GLM token staking
• Reward distribution
• Community participation

Please ask about any of these topics!"""
            
        return response

    def validate_message(self, message):
        """Validate and sanitize user input."""
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")
        return message.strip()

    def format_conversation_history(self):
        """Format the conversation history for the prompt."""
        if not self.conversation_history:
            return ""
        # Only include the last message for immediate context
        last_entry = self.conversation_history[-1]
        return f"\nPrevious message: {last_entry['assistant']}\n"

    def format_urls(self, text):
        """Format URLs in a simple, consistent way."""
        # Check if the message is asking about links/websites/contact
        keywords = ['link', 'links', 'website', 'connect', 'social', 'james', 'kiernan', 'vpabundance', 'contact']
        
        if any(keyword in text.lower() for keyword in keywords):
            return """Sure thing! Here are some essential links related to Octant, the Golem Foundation, and more:

🌐 Octant:
Main website: https://octant.build/
Documentation: https://docs.octant.app/

🌐 Golem Foundation:
Main website: https://golem.foundation/

📱 Connect with us:
Twitter/X: https://x.com/OctantApp
Warpcast: https://warpcast.com/octant
Discord: https://discord.gg/octant

Learn more about James Kiernan, VPOFABUNDANCE, here:
X: https://x.com/vpabundance
Warpcast: https://warpcast.com/vpabundance.eth
LinkedIn: https://www.linkedin.com/in/vpabundance

I hope this helps! Let me know if there's anything else you need. 😊"""
            
        # For James-specific queries
        if any(name in text.lower() for name in ['james', 'kiernan', 'vpabundance']):
            return """X: https://x.com/vpabundance
Warpcast: https://warpcast.com/vpabundance.eth
LinkedIn: https://www.linkedin.com/in/vpabundance"""
            
        return text

    def validate_response_length(self, response):
        """Validate response length and split if necessary."""
        max_length = 2000  # Discord's max message length
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
            
            # Enhanced context control and response validation
            history = self.format_conversation_history()
            prompt = f"""You are the Octant AI Assistant, specifically designed to provide information about Octant, GLM tokens, and the Golem Foundation.

CORE PRINCIPLES:
1. EXPERTISE: You are an expert on:
   - Octant's funding mechanisms and epochs
   - GLM token staking and rewards
   - The Golem Foundation's role
   - Community participation and governance

2. FOCUS:
   - ONLY discuss Octant-related topics
   - Politely redirect off-topic questions to Octant features
   - Use official Octant terminology consistently
   - Maintain factual accuracy about Octant's features

3. RESPONSE GUIDELINES:
   - If uncertain, refer to core Octant documentation
   - For funding questions, cite specific mechanisms
   - For technical questions, provide accurate details
   - Always relate answers back to Octant's ecosystem

4. KEY FACTS TO MAINTAIN:
   - Octant is backed by 100,000 ETH
   - Epochs last 90 days
   - 100 GLM minimum for rewards
   - 20% maximum project funding cap
   - 25% to foundation operations

CONTEXT:
Previous interaction: {history}
Current question: {user_message}

Provide an accurate, Octant-focused response that adheres to these principles:"""
            
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
            if "output" in result and result["output"]["choices"]:
                # Get the raw response text
                response_text = result["output"]["choices"][0]["text"].strip()
                
                try:
                    # Format URLs with the improved function
                    formatted_text = self.format_urls(response_text)
                    logger.info("URLs formatted successfully")
                    
                    # Validate response content
                    validated_text = self.validate_response_content(response_text)
                    
                    # Format URLs in validated response
                    formatted_text = self.format_urls(validated_text)
                    
                    # Update conversation history
                    self.conversation_history.append({
                        "user": user_message,
                        "assistant": formatted_text
                    })
                except Exception as format_error:
                    logger.error(f"Error formatting URLs: {str(format_error)}")
                    formatted_text = self.validate_response_content(response_text)  # Fall back to validated but unformatted text
                
                # Keep only the last max_history entries
                if len(self.conversation_history) > self.max_history:
                    self.conversation_history = self.conversation_history[-self.max_history:]
                
                # Handle long responses
                if len(formatted_text) > 2000:  # Discord's limit
                    return self.validate_response_length(formatted_text)
                
                return formatted_text
            else:
                logger.error("Unexpected API response format:", result)
                return "I apologize, but I couldn't generate a response at the moment. Please try again."
                
        except ValueError as e:
            error_message = str(e)
            logger.error(f"Validation error: {error_message}")
            return f"I couldn't process your message: {error_message}"
            
        except requests.exceptions.Timeout:
            logger.error("API request timed out")
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
